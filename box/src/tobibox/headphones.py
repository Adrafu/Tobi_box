"""Kopfhörer-Buchse: Ereignis „Stecker erkannt / gezogen“ (``core-interface.md``, 3.5; CUJ 17).

``Buchse`` ist die Fassade für den Dienst. Dahinter steht ein Treiber mit **einer** Schnittstelle:

* ``SimKopfhoerer`` (Mac und Test): ``setze(True/False)`` steckt oder zieht den Stecker.
  Der Eingang in ``sim`` und ``cli`` (``tobibox sim headphones on|off``) kommt mit AP 4.8.
* ``GpioKopfhoerer`` (Pi): liest den Schaltkontakt der Buchse an einem GPIO-Pin. Viele Klinkenbuchsen haben einen
  Öffner, der beim Einstecken schaltet; ob der Pegel dann hoch oder tief ist, steht in ``aktiv_niedrig``.
  **Auf dem Pi zu prüfen** (Pin, Pegel, Pull-up). Bis die Buchse da ist, ist der Treiber nur gegen eine Attrappe
  getestet (``tests/unit/test_headphones.py``).

``Buchse`` sendet ``Kopfhoerer(steckt)`` bei jeder Änderung und einmal bei der ersten Messung. Das Ereignis entprellt sie:
Ein neuer Wert gilt erst, wenn ihn ``entprellen`` Messungen hintereinander zeigen (Wackelkontakt beim Einstecken).
Was danach geschieht (erst Grenze, dann Ausgang), regeln ``session`` und ``player``; ``headphones`` kennt weder
Lautstärke noch Ausgang.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from . import events as ev
from .eventlog import logge

MESS_INTERVALL_S = 0.2
ENTPRELLEN_MESSUNGEN = 2
LESE_FRIST_S = 2.0


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


async def lese_mit_gpioget(chip: str, pin: int, frist_s: float = LESE_FRIST_S) -> bool:
    """Liest den Pegel eines Pins mit ``gpioget`` (Paket ``gpiod``/``libgpiod-tools``). ``True`` = hoch."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "gpioget", chip, str(pin), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        aus, _ = await asyncio.wait_for(proc.communicate(), frist_s)
    except (OSError, asyncio.TimeoutError) as e:
        raise KopfhoererFehler(f"gpioget nicht lesbar: {e!r}") from e
    if proc.returncode != 0:
        raise KopfhoererFehler(f"gpioget endete mit {proc.returncode}")
    return parse_pegel(aus.decode("utf-8", "replace"))


class GpioKopfhoerer:
    """Pi: Schaltkontakt der Buchse an einem GPIO-Pin (Standard: Kontakt schließt nach Masse, Pull-up, ``aktiv_niedrig``).

    ``lese`` liest den Pegel (``True`` = hoch) und ist austauschbar; Vorgabe ist ``gpioget``.
    """

    def __init__(
        self,
        pin: int,
        *,
        aktiv_niedrig: bool = True,
        chip: str = "gpiochip0",
        lese: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        self.pin, self.aktiv_niedrig, self.chip = pin, aktiv_niedrig, chip
        self._lese = lese if lese is not None else (lambda: lese_mit_gpioget(self.chip, self.pin))

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
            return neu
        self._kandidat, self._zaehler = steckt, 0
        await self._uebernimm(steckt, neu)
        return neu

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
            return neu
        if self._fehler_gemeldet:
            self._fehler_gemeldet = False
            logge("headphones", "INFO", "messen", "wieder_lesbar")
        if steckt == self._kandidat:
            self._zaehler += 1
        else:
            self._kandidat, self._zaehler = steckt, 1
        if steckt != self.steckt and self._zaehler >= self.entprellen:
            await self._uebernimm(steckt, neu)
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
            await asyncio.sleep(self.intervall_s)
