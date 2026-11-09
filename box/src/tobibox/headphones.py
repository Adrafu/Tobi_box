"""Kopfhörer-Buchse: Ereignis „Stecker erkannt / gezogen“ (``core-interface.md``, 3.5; CUJ 17).

``Buchse`` ist die Fassade für den Dienst. Dahinter steht ein Treiber mit **einer** Schnittstelle:

* ``SimKopfhoerer`` (Mac und Test): ``setze(True/False)`` steckt oder zieht den Stecker.
  Der Eingang in ``sim`` und ``cli`` (``tobibox sim headphones on|off``) kommt mit AP 4.8.
* ``GpioKopfhoerer`` (Pi): liest den Schaltkontakt der Buchse an einem GPIO-Pin. Viele Klinkenbuchsen haben einen
  Öffner, der beim Einstecken schaltet; ob der Pegel dann hoch oder tief ist, steht in ``aktiv_niedrig``.
  **Auf dem Pi zu prüfen** (Pin, Pegel, Pull-up). Bis die Buchse da ist, ist der Treiber nur gegen eine Attrappe
  getestet (``tests/unit/test_headphones.py``).

  **Wahl der Lesemethode (B4, 09.11.).** Vorrang hat ``gpiozero.DigitalInputDevice`` (dieselbe Bibliothek wie bei den Tasten):
  Der Pull-up (bei ``aktiv_niedrig``, sonst Pull-down) wird ausdrücklich gesetzt, es gibt keinen Prozessstart je Messung, und die
  Version von libgpiod spielt keine Rolle (gpiozero nimmt auf dem Pi je nach System lgpio oder RPi.GPIO). Fehlt ``gpiozero``,
  fällt der Treiber auf ``gpioget`` zurück: mit ``--bias=pull-up`` bzw. ``pull-down``, die Syntax je nach libgpiod-Version erkannt
  (1.x: ``gpioget <chip> <pin>``, 2.x: ``gpioget -c <chip> <pin>``). Weil dort jede Messung einen Prozess startet,
  misst die Buchse dann höchstens einmal je ``GPIOGET_INTERVALL_MIN_S``.

``Buchse`` meldet außerdem, wenn der Kontakt **nicht lesbar** ist (``KopfhoererLesbar``, Entscheidung P): Dann gilt die
Kopfhörer-Grenze, bis er wieder lesbar ist. Das gilt auch beim Start, wenn die erste Messung scheitert.

``Buchse`` sendet ``Kopfhoerer(steckt)`` bei jeder Änderung und einmal bei der ersten Messung. Das Ereignis entprellt sie:
Ein neuer Wert gilt erst, wenn ihn ``entprellen`` Messungen hintereinander zeigen (Wackelkontakt beim Einstecken).
Was danach geschieht (erst Grenze, dann Ausgang), regeln ``session`` und ``player``; ``headphones`` kennt weder
Lautstärke noch Ausgang.
"""

from __future__ import annotations

import asyncio
import inspect
import re
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from . import events as ev
from .eventlog import logge

MESS_INTERVALL_S = 0.2
ENTPRELLEN_MESSUNGEN = 2
LESE_FRIST_S = 2.0
#: Rückfall ``gpioget``: Ein Prozessstart je Messung ist teuer (Pi 3A+); darum höchstens einmal je Sekunde.
GPIOGET_INTERVALL_MIN_S = 1.0


class KopfhoererTreiber(Protocol):
    """Was ``Buchse`` vom Gerät braucht."""

    async def steckt(self) -> bool:
        """``True``, wenn ein Stecker in der Buchse steckt. Wirft ``OSError``, wenn das Gerät nicht lesbar ist."""
        ...


class KopfhoererFehler(OSError):
    """Der Schaltkontakt ist nicht lesbar oder liefert Unverständliches."""


class SimKopfhoerer:
    """Mac und Test. Standard: kein Stecker."""

    def __init__(self, steckt: bool = False) -> None:
        self._steckt = steckt

    def setze(self, steckt: bool) -> None:
        self._steckt = steckt

    async def steckt(self) -> bool:
        return self._steckt


def parse_pegel(text: str) -> bool:
    """Antwort eines GPIO-Werkzeugs als Pegel: ``1``/``0`` (libgpiod 1.x) oder ``"17"=active`` (2.x). ``True`` = hoch/aktiv."""
    t = text.strip().lower()
    if t.endswith("inactive"):
        return False
    if t.endswith("active"):
        return True
    if t in ("1", "0"):
        return t == "1"
    raise KopfhoererFehler(f"unverständlicher GPIO-Wert: {text.strip()[:60]!r}")


_versionen: dict[str, int] = {}


async def gpiod_hauptversion(frist_s: float = LESE_FRIST_S) -> int:
    """Hauptversion von libgpiod laut ``gpioget --version`` (``1`` oder ``2``), einmal erkannt und gemerkt.

    Wirft ``KopfhoererFehler``, wenn ``gpioget`` fehlt oder die Ausgabe unverständlich ist."""
    if "gpioget" in _versionen:
        return _versionen["gpioget"]
    try:
        proc = await asyncio.create_subprocess_exec(
            "gpioget", "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        aus, _ = await asyncio.wait_for(proc.communicate(), frist_s)
    except (OSError, asyncio.TimeoutError) as e:
        raise KopfhoererFehler(f"gpioget nicht startbar: {e!r}") from e
    m = re.search(r"(\d+)\.\d+", aus.decode("utf-8", "replace"))
    if m is None:
        raise KopfhoererFehler("gpioget --version unverständlich")
    _versionen["gpioget"] = int(m.group(1))
    return _versionen["gpioget"]


def gpioget_befehl(version: int, chip: str, pin: int, *, pull_up: bool) -> list[str]:
    """Die Befehlszeile für ``gpioget`` mit ausdrücklichem Bias (B4). Pull-up bei ``pull_up``, sonst Pull-down.

    libgpiod 1.x (ab 1.5): ``gpioget --bias=pull-up <chip> <pin>``. libgpiod 2.x: ``gpioget --bias=pull-up -c <chip> <pin>``."""
    bias = "--bias=pull-up" if pull_up else "--bias=pull-down"
    if version >= 2:
        return ["gpioget", bias, "-c", chip, str(pin)]
    return ["gpioget", bias, chip, str(pin)]


async def lese_mit_gpioget(chip: str, pin: int, frist_s: float = LESE_FRIST_S, *, pull_up: bool = True) -> bool:
    """Liest den Pegel eines Pins mit ``gpioget`` (Paket ``gpiod``/``libgpiod-tools``). ``True`` = hoch."""
    version = await gpiod_hauptversion(frist_s)
    try:
        proc = await asyncio.create_subprocess_exec(
            *gpioget_befehl(version, chip, pin, pull_up=pull_up),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        aus, _ = await asyncio.wait_for(proc.communicate(), frist_s)
    except (OSError, asyncio.TimeoutError) as e:
        raise KopfhoererFehler(f"gpioget nicht lesbar: {e!r}") from e
    if proc.returncode != 0:
        raise KopfhoererFehler(f"gpioget endete mit {proc.returncode}")
    return parse_pegel(aus.decode("utf-8", "replace"))


class GpioKopfhoerer:
    """Pi: Schaltkontakt der Buchse an einem GPIO-Pin (Standard: Kontakt schließt nach Masse, Pull-up, ``aktiv_niedrig``).

    ``lese`` liest den Pegel (``True`` = hoch) und ist austauschbar. Vorgabe: ``gpiozero.DigitalInputDevice`` mit
    ausdrücklichem Pull-up / Pull-down (kein Prozess je Messung); ohne ``gpiozero`` ``gpioget`` mit ``--bias``.
    ``fabrik`` ist das Modul ``gpiozero`` (oder eine Attrappe mit ``DigitalInputDevice``).
    """

    def __init__(
        self,
        pin: int,
        *,
        aktiv_niedrig: bool = True,
        chip: str = "gpiochip0",
        lese: Callable[[], Awaitable[bool]] | None = None,
        fabrik: Any = None,
    ) -> None:
        self.pin, self.aktiv_niedrig, self.chip = pin, aktiv_niedrig, chip
        self._fabrik = fabrik
        self._geraet: Any = None
        self._lese = lese if lese is not None else self._lese_vorgabe
        self._gpioget = False  # ``True``: Rückfall ohne gpiozero, die Buchse misst seltener

    @property
    def dauerhaft(self) -> bool:
        """``True``: Lesen kostet nichts (kein Prozess je Messung)."""
        return not self._gpioget

    def _gpiozero(self) -> Any:
        if self._fabrik is not None:
            return self._fabrik
        try:
            import gpiozero  # nur auf dem Pi vorhanden
        except ImportError:
            return None
        return gpiozero

    async def _lese_vorgabe(self) -> bool:
        g = self._gpiozero()
        if g is None:
            self._gpioget = True
            return await lese_mit_gpioget(self.chip, self.pin, pull_up=self.aktiv_niedrig)
        try:
            if self._geraet is None:
                # Pull-up bei „Stecker = tief“, sonst Pull-down; ``bounce_time`` aus: entprellt wird in ``Buchse``
                self._geraet = g.DigitalInputDevice(self.pin, pull_up=self.aktiv_niedrig, bounce_time=None)
            return self._pegel_hoch()
        except Exception as e:  # noqa: BLE001 - gpiozero wirft eigene Fehlerklassen (Pin belegt, keine Rechte, …)
            self.schliesse()
            raise KopfhoererFehler(f"gpiozero nicht lesbar: {e!r}") from e

    def _pegel_hoch(self) -> bool:
        """``DigitalInputDevice.value`` ist ``1`` bei aktivem Pegel; mit Pull-up ist „aktiv“ = Pin tief."""
        aktiv = bool(self._geraet.value)
        return (not aktiv) if self.aktiv_niedrig else aktiv

    def schliesse(self) -> None:
        g, self._geraet = self._geraet, None
        if g is not None:
            try:
                g.close()
            except Exception:  # noqa: BLE001
                pass

    async def steckt(self) -> bool:
        hoch = await self._lese()
        return (not hoch) if self.aktiv_niedrig else hoch


class Buchse:
    """Fragt den Treiber, entprellt und sendet nur Änderungen (und die erste Messung). Eine Aufgabe ``lauf()`` in ``app``."""

    def __init__(
        self,
        treiber: KopfhoererTreiber,
        ausgabe: Callable[[ev.Ereignis], Any] | None = None,
        *,
        intervall_s: float = MESS_INTERVALL_S,
        entprellen: int = ENTPRELLEN_MESSUNGEN,
    ) -> None:
        if entprellen < 1:
            raise ValueError("entprellen muss mindestens 1 sein")
        self.treiber = treiber
        self._ausgabe = ausgabe
        self.intervall_s = intervall_s
        self.entprellen = entprellen
        self.steckt: bool | None = None  # zuletzt gemeldeter Wert; ``None``: noch nichts gemeldet
        self._kandidat: bool | None = None
        self._zaehler = 0
        self._fehler_gemeldet = False
        self.unlesbar = False  # dem Kern als ``KopfhoererLesbar(False)`` gemeldet (Entscheidung P)

    async def _gib(self, e: ev.Ereignis, neu: list[ev.Ereignis]) -> None:
        neu.append(e)
        if self._ausgabe is not None:
            r = self._ausgabe(e)
            if inspect.isawaitable(r):
                await r

    async def melde(self, steckt: bool) -> list[ev.Ereignis]:
        """Einen Wert **ohne Entprellen** übernehmen (Simulation: ``tobibox sim headphones``). Sendet nur bei Änderung."""
        neu: list[ev.Ereignis] = []
        self._kandidat, self._zaehler = steckt, 0
        if steckt != self.steckt:
            await self._uebernimm(steckt, neu)
        return neu

    async def _uebernimm(self, steckt: bool, neu: list[ev.Ereignis]) -> None:
        erste = self.steckt is None
        self.steckt = steckt
        logge("headphones", "INFO", "kopfhoerer", "steckt" if steckt else "gezogen", daten={"erste_messung": erste})
        await self._gib(ev.Kopfhoerer(steckt), neu)

    async def start(self) -> list[ev.Ereignis]:
        """Erste Messung beim Dienststart: gilt sofort (ohne Entprellen) und wird immer gemeldet."""
        neu: list[ev.Ereignis] = []
        try:
            steckt = await self.treiber.steckt()
        except OSError as e:
            logge("headphones", "WARNING", "messen", "fehler", daten={"detail": str(e)})
            self._fehler_gemeldet = True
            await self._melde_unlesbar(neu)  # Entscheidung P: ohne erste Messung gilt die Kopfhörer-Grenze
            return neu
        self._kandidat, self._zaehler = steckt, 0
        await self._uebernimm(steckt, neu)
        return neu

    async def _melde_unlesbar(self, neu: list[ev.Ereignis]) -> None:
        if not self.unlesbar:
            self.unlesbar = True
            await self._gib(ev.KopfhoererLesbar(False), neu)

    async def pruefe(self) -> list[ev.Ereignis]:
        """Eine Messung. Gibt die neuen Ereignisse zurück und sendet sie an ``ausgabe``."""
        neu: list[ev.Ereignis] = []
        try:
            steckt = await self.treiber.steckt()
        except OSError as e:
            if not self._fehler_gemeldet:  # einmal je Störung, nicht alle 0,2 s
                self._fehler_gemeldet = True
                logge("headphones", "WARNING", "messen", "fehler", daten={"detail": str(e)})
            self._kandidat, self._zaehler = None, 0
            await self._melde_unlesbar(neu)
            return neu
        if self._fehler_gemeldet:
            self._fehler_gemeldet = False
            logge("headphones", "INFO", "messen", "wieder_lesbar")
        if steckt == self._kandidat:
            self._zaehler += 1
        else:
            self._kandidat, self._zaehler = steckt, 1
        stabil = self._zaehler >= self.entprellen
        if steckt != self.steckt and stabil:
            await self._uebernimm(steckt, neu)
        if stabil and self.unlesbar:  # erst nach einem stabilen Wert und nach dem ``Kopfhoerer``-Ereignis wieder lesbar
            self.unlesbar = False
            await self._gib(ev.KopfhoererLesbar(True), neu)
        return neu

    async def lauf(self) -> None:
        """Dauerlauf (eine Aufgabe in ``app``)."""
        while True:
            try:
                await self.pruefe()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - der Dauerlauf darf nie stehen bleiben
                logge("headphones", "ERROR", "pruefen", "fehler", daten={"detail": repr(e)})
            teuer = getattr(self.treiber, "dauerhaft", True) is False  # gpioget: ein Prozess je Messung
            await asyncio.sleep(max(self.intervall_s, GPIOGET_INTERVALL_MIN_S) if teuer else self.intervall_s)
