"""Strom-Schnittstelle (``core-interface.md`` 3.5, 3.6 und 4; Design „Netz, Sync, Strom“).

``Power`` ist die Fassade für den Dienst. Dahinter steht ein Treiber:

* ``SimStrom`` (Mac und Test): Akku und Lader werden vorgegeben (``tobibox sim power --charger on --battery 40``;
  ``sim`` ruft ``SimStrom.setze`` und danach ``Power.pruefe``). „Herunterfahren“ wird nur protokolliert.
* ``PiSugarStrom`` (Pi): spricht mit ``pisugar-server`` (TCP, Text: ``get battery`` -> ``battery: 79.2``).

``power`` sendet ``AkkuStand``, ``LaderGeaendert``, ``AkkuTiefstand``, ``Hauptknopf`` (Taste des PiSugar, als Tastenereignis)
und ``ZeitquelleGeaendert`` (RTC beim Start gelesen). Es führt den Befehl ``Herunterfahren`` aus. Die Regel für den Sync
im Hotspot (Lader oder Akku über 50 %) steht in ``syncregel`` (eine Quelle für ``power`` und ``sync``); ``sync_erlaubt``
wird hier nur wieder angeboten.
"""

from __future__ import annotations

import asyncio
import inspect
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from . import events as ev
from .config import StromKonfig
from .eventlog import logge
from .net import Zeitquelle
from .syncregel import HOTSPOT_AKKU_MIN_PROZENT, sync_erlaubt  # noqa: F401  (die eine Regel, hier nur wieder angeboten)

#: Der Tiefstand gilt wieder als „nicht erreicht“, wenn der Akku um so viel über der Grenze liegt (kein Flattern).
TIEFSTAND_ABSTAND_PROZENT = 3
#: Eine RTC vor diesem Zeitpunkt hat ihre Zeit verloren (leerer Akku): sie gilt nicht als vertrauenswürdig.
RTC_FRUEHESTENS = datetime(2026, 1, 1, tzinfo=timezone.utc)
PISUGAR_FRIST_S = 3.0
#: So lange darf ``systemctl poweroff`` (oder das eingestellte Kommando) höchstens brauchen, bevor es als Fehler gilt (B1).
ABSCHALT_FRIST_S = 60.0
#: Nach einem fehlgeschlagenen Herunterfahren meldet ``power`` einen fortbestehenden Tiefstand frühestens nach so vielen Sekunden
#: wieder (B1: ein Tiefstand darf nicht „verbraucht“ sein; kein Dauerfeuer alle 10 s).
TIEFSTAND_WIEDERHOLEN_S = 60.0


# --------------------------------------------------------------------------
# Treiber
# --------------------------------------------------------------------------


class StromTreiber(Protocol):
    """Was ``Power`` vom Gerät braucht. Alle Werte ``None``, wenn unbekannt."""

    async def akku(self) -> int | None: ...
    async def lader(self) -> bool | None: ...
    async def rtc(self) -> datetime | None: ...
    async def herunterfahren(self, grund: str) -> None:
        """Wirft eine Ausnahme (``OSError``/``HerunterfahrenFehler``), wenn das Herunterfahren nicht gewirkt hat."""
        ...


class HerunterfahrenFehler(OSError):
    """Das Abschalt-Kommando fehlt, endete mit einem Fehler oder brauchte zu lange."""


class SimStrom:
    """Mac und Test. Standard: Lader und Akku unbekannt, bis ``setze`` sie vorgibt."""

    simuliert = True  # „Herunterfahren“ wird nur protokolliert

    def __init__(self, akku: int | None = None, lader: bool | None = None, rtc: datetime | None = None) -> None:
        self._akku, self._lader, self._rtc = akku, lader, rtc
        self.heruntergefahren: list[str] = []  # die Gründe, mit denen „Herunterfahren“ verlangt wurde

    def setze(self, *, akku: int | None = ..., lader: bool | None = ..., rtc: datetime | None = ...) -> None:  # type: ignore[assignment]
        """Nur die angegebenen Werte ändern (``None`` heißt „unbekannt“)."""
        if akku is not ...:
            self._akku = akku
        if lader is not ...:
            self._lader = lader
        if rtc is not ...:
            self._rtc = rtc

    async def akku(self) -> int | None:
        return self._akku

    async def lader(self) -> bool | None:
        return self._lader

    async def rtc(self) -> datetime | None:
        return self._rtc

    async def herunterfahren(self, grund: str) -> None:
        self.heruntergefahren.append(grund)
        logge("power", "INFO", "herunterfahren", "simuliert", sim=True, daten={"grund": grund})


class PiSugarFehler(OSError):
    """``pisugar-server`` ist nicht erreichbar oder antwortet unverständlich."""


_ANTWORT = re.compile(r"^([a-z_0-9]+):\s*(.*)$")


def parse_antwort(zeile: str, name: str) -> str:
    """``battery: 79.2`` -> ``79.2`` (prüft den Namen). Wirft ``PiSugarFehler``."""
    m = _ANTWORT.match(zeile.strip())
    if m is None or m.group(1) != name:
        raise PiSugarFehler(f"unerwartete Antwort auf 'get {name}': {zeile.strip()[:80]!r}")
    return m.group(2).strip()


def parse_rtc(text: str) -> datetime | None:
    """``2026-11-05T09:30:00.000+01:00`` -> ``datetime`` mit Zeitzone; ``None``, wenn nicht lesbar."""
    try:
        t = datetime.fromisoformat(text.strip())
    except ValueError:
        return None
    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)


class PiSugarStrom:
    """Pi: ``pisugar-server`` auf ``127.0.0.1:8423``. **Auf dem Pi zu prüfen** (Befehlsnamen und Antworten).

    Bis PiSugar da ist, ist dieser Treiber nur gegen eine Attrappe getestet (``tests/unit/test_power.py``).
    """

    def __init__(self, host: str, port: int, abschalt_kommando: tuple[str, ...], frist_s: float = PISUGAR_FRIST_S) -> None:
        self.host, self.port, self.frist_s = host, port, frist_s
        self.abschalt_kommando = abschalt_kommando

    async def _frage(self, befehl: str) -> str:
        """Eine Frage, eine Antwortzeile. Jede Frage öffnet eine neue Verbindung (selten, einfach, robust)."""
        try:
            leser, schreiber = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), self.frist_s)
        except (OSError, asyncio.TimeoutError) as e:
            raise PiSugarFehler(f"pisugar-server nicht erreichbar: {e!r}") from e
        try:
            schreiber.write((befehl + "\n").encode())
            await asyncio.wait_for(schreiber.drain(), self.frist_s)
            zeile = await asyncio.wait_for(leser.readline(), self.frist_s)
        except (OSError, asyncio.TimeoutError) as e:
            raise PiSugarFehler(f"pisugar-server antwortet nicht: {e!r}") from e
        finally:
            schreiber.close()
        if not zeile:
            raise PiSugarFehler("pisugar-server hat die Verbindung ohne Antwort geschlossen")
        return zeile.decode("utf-8", "replace")

    async def _hole(self, name: str) -> str:
        return parse_antwort(await self._frage(f"get {name}"), name)

    async def akku(self) -> int | None:
        try:
            return max(0, min(100, round(float(await self._hole("battery")))))
        except ValueError:
            return None

    async def lader(self) -> bool | None:
        # „Netzteil steckt“ ist richtig, auch wenn der Akku voll ist und nicht mehr lädt
        try:
            wert = await self._hole("battery_power_plugged")
        except PiSugarFehler:
            wert = await self._hole("battery_charging")
        return {"true": True, "false": False}.get(wert.lower())

    async def rtc(self) -> datetime | None:
        return parse_rtc(await self._hole("rtc_time"))

    async def uhr_aus_rtc_setzen(self) -> None:
        """Lässt ``pisugar-server`` die Systemuhr aus der RTC setzen (er läuft mit den nötigen Rechten)."""
        await self._frage("rtc_rtc2pi")

    async def taste_abfragen(self, befehl: str) -> str:
        """Die Antwort des ``pisugar-server`` auf einen frei einstellbaren Befehl (``[strom] taste_befehl``). **Am Pi zu prüfen.**"""
        return await self._frage(befehl)

    async def herunterfahren(self, grund: str) -> None:
        """Abschalt-Kommando ausführen und prüfen (B1): Rückgabecode 0 und innerhalb ``ABSCHALT_FRIST_S``.

        Fehlendes Kommando, Rückgabecode ungleich 0 und Zeitüberschreitung sind ``HerunterfahrenFehler``."""
        logge("power", "INFO", "herunterfahren", "ausgefuehrt", daten={"grund": grund})
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.abschalt_kommando, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
        except OSError as e:
            raise HerunterfahrenFehler(f"{self.abschalt_kommando[0]} nicht startbar: {e!r}") from e
        try:
            code = await asyncio.wait_for(proc.wait(), ABSCHALT_FRIST_S)
        except asyncio.TimeoutError as e:
            raise HerunterfahrenFehler(f"{self.abschalt_kommando[0]} brauchte länger als {ABSCHALT_FRIST_S:g} s") from e
        if code != 0:
            raise HerunterfahrenFehler(f"{self.abschalt_kommando[0]} endete mit Rückgabecode {code}")


# --------------------------------------------------------------------------
# Fassade
# --------------------------------------------------------------------------


class Power:
    """Fragt den Treiber und sendet nur Änderungen (und die erste Messung). Eine Aufgabe ``lauf()`` in ``app``."""

    def __init__(
        self,
        treiber: StromTreiber,
        ausgabe: Callable[[ev.Ereignis], Any] | None = None,
        zeit: Zeitquelle | None = None,
        *,
        tiefstand_prozent: int = 5,
        intervall_s: float = 10.0,
        taste_befehl: str | None = None,
        taste_intervall_s: float = 0.5,
        mono: Callable[[], float] = time.monotonic,
    ) -> None:
        self.treiber = treiber
        self._ausgabe = ausgabe
        self.zeit = zeit
        self.tiefstand_prozent = tiefstand_prozent
        self.intervall_s = intervall_s
        self.akku: int | None = None  # letzter bekannter Akkustand
        self.am_lader: bool | None = None
        self._tiefstand_gemeldet = False
        self._tiefstand_wieder_ab: float | None = None  # mono; nach einem fehlgeschlagenen Herunterfahren
        self.taste_befehl = taste_befehl
        self.taste_intervall_s = taste_intervall_s
        self._mono = mono

    @classmethod
    def aus_konfig(
        cls, konfig: StromKonfig, zeit: Zeitquelle | None = None, ausgabe: Callable[[ev.Ereignis], Any] | None = None
    ) -> Power:
        treiber: StromTreiber = (
            SimStrom()
            if konfig.simulation
            else PiSugarStrom(konfig.pisugar_host, konfig.pisugar_port, konfig.abschalt_kommando)
        )
        return cls(
            treiber, ausgabe, zeit, tiefstand_prozent=konfig.tiefstand_prozent, intervall_s=konfig.intervall_s,
            taste_befehl=konfig.taste_befehl, taste_intervall_s=konfig.taste_intervall_s,
        )

    async def _gib(self, e: ev.Ereignis, neu: list[ev.Ereignis]) -> None:
        neu.append(e)
        if self._ausgabe is not None:
            r = self._ausgabe(e)
            if inspect.isawaitable(r):
                await r

    # -- Start ---------------------------------------------------------------------

    async def start(self) -> list[ev.Ereignis]:
        """Beim Dienststart: RTC lesen (Zeitquelle melden), dann die erste Messung von Lader und Akku."""
        neu: list[ev.Ereignis] = []
        plausibel = False
        try:
            t = await self.treiber.rtc()
            plausibel = t is not None and t >= RTC_FRUEHESTENS
            logge("power", "INFO", "rtc", "plausibel" if plausibel else "unbrauchbar",
                  daten={"rtc": t.isoformat() if t else None})
            if plausibel and hasattr(self.treiber, "uhr_aus_rtc_setzen"):
                await self.treiber.uhr_aus_rtc_setzen()  # type: ignore[attr-defined]
        except PiSugarFehler as e:
            logge("power", "WARNING", "rtc", "fehler", daten={"detail": str(e)})
        if self.zeit is not None:
            z = self.zeit.rtc(plausibel)
            if z is not None:
                await self._gib(z, neu)
        neu.extend(await self.pruefe())
        return neu

    # -- laufende Messung ----------------------------------------------------------

    async def pruefe(self) -> list[ev.Ereignis]:
        """Ein Durchgang. Gibt die neuen Ereignisse zurück und sendet sie an ``ausgabe``."""
        neu: list[ev.Ereignis] = []
        try:
            lader = await self.treiber.lader()
            akku = await self.treiber.akku()
        except PiSugarFehler as e:
            logge("power", "WARNING", "messen", "fehler", daten={"detail": str(e)})
            return neu
        if lader is not None and lader != self.am_lader:
            self.am_lader = lader
            await self._gib(ev.LaderGeaendert(lader), neu)
        if akku is not None and akku != self.akku:
            self.akku = akku
            await self._gib(ev.AkkuStand(akku), neu)
        if await self._tiefstand_pruefen():
            await self._gib(ev.AkkuTiefstand(), neu)
        return neu

    async def _tiefstand_pruefen(self) -> bool:
        """``True`` genau einmal, wenn der Akku die Grenze erreicht und die Box sicher nicht am Lader ist.

        Ist der Lader unbekannt (``None``), meldet ``power`` keinen Tiefstand: ein Fühler-Fehler schaltet keine Box ab."""
        if self.am_lader is not False or self.akku is None:
            self._tiefstand_gemeldet = False  # am Lader oder unbekannt: neu bewaffnen
            return False
        if self._tiefstand_gemeldet and self._tiefstand_wieder_ab is not None and self._mono() >= self._tiefstand_wieder_ab:
            self._tiefstand_gemeldet = False  # das Herunterfahren hat nicht gewirkt: noch einmal melden (B1)
            self._tiefstand_wieder_ab = None
        if self.akku <= self.tiefstand_prozent:
            if not self._tiefstand_gemeldet:
                self._tiefstand_gemeldet = True
                logge("power", "WARNING", "akku_tiefstand", "erreicht", daten={"akku": self.akku})
                return True
            return False
        if self.akku > self.tiefstand_prozent + TIEFSTAND_ABSTAND_PROZENT:
            self._tiefstand_gemeldet = False
        return False

    async def lauf(self) -> None:
        """Dauerlauf (eine Aufgabe in ``app``)."""
        while True:
            try:
                await self.pruefe()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - der Dauerlauf darf nie stehen bleiben
                logge("power", "ERROR", "pruefen", "fehler", daten={"detail": repr(e)})
            await asyncio.sleep(self.intervall_s)

    # -- Taste und Befehl ----------------------------------------------------------

    async def taste(self, art: Literal["kurz", "lang"]) -> list[ev.Ereignis]:
        """Die Taste des PiSugar wurde gedrückt: ein ``Hauptknopf`` (kurz: Pause/Weiter, lang: Herunterfahren, CUJ 19)."""
        if art not in ("kurz", "lang"):
            raise ValueError(f"unbekannte Tastenart {art!r}")
        neu: list[ev.Ereignis] = []
        await self._gib(ev.Hauptknopf(art), neu)
        return neu

    async def taste_lauf(self) -> None:
        """Dauerlauf (nur mit ``[strom] taste_befehl``): fragt den ``pisugar-server`` nach der Taste und ruft ``taste`` auf.

        **Am Pi zu prüfen (B2):** In der Dokumentation des ``pisugar-server`` ist kein Befehl belegt, der Tastenereignisse liefert
        (Abfrage oder Abonnement). Dieser Weg ist deshalb ausgeschaltet, bis am Gerät ein Befehl gefunden ist, dessen Antwort
        ``parse_taste`` versteht. Siehe ``docs/betrieb/pisugar-wecker.md``, Abschnitt „Hauptknopf“."""
        abfrage = getattr(self.treiber, "taste_abfragen", None)
        if self.taste_befehl is None or abfrage is None:
            return
        while True:
            try:
                art = parse_taste(await abfrage(self.taste_befehl))
                if art is not None:
                    await self.taste(art)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - der Dauerlauf darf nie stehen bleiben
                logge("power", "WARNING", "taste", "fehler", daten={"detail": repr(e)[:200]})
                await asyncio.sleep(max(self.taste_intervall_s, 5.0))  # bei Fehlern seltener fragen
            await asyncio.sleep(self.taste_intervall_s)

    async def fuehre_aus(self, befehl: ev.Befehl) -> bool:
        """Führt ``Herunterfahren`` aus (in der Simulation nur protokolliert). Andere Befehle: nicht seine Sache.

        Gibt ``True`` zurück, wenn das Kommando gewirkt hat. Sonst sendet ``power`` ``HerunterfahrenFehlgeschlagen`` (B1;
        ``simuliert=True`` am Mac, sonst mit dem Fehlertext) und gibt ``False`` zurück."""
        if not isinstance(befehl, ev.Herunterfahren):
            return True
        simuliert = bool(getattr(self.treiber, "simuliert", False))
        neu: list[ev.Ereignis] = []
        try:
            await self.treiber.herunterfahren(befehl.grund)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - jeder Fehler heißt: nicht heruntergefahren
            logge("power", "ERROR", "herunterfahren", "fehler", daten={"grund": befehl.grund, "detail": repr(e)[:200]})
            self._tiefstand_wieder_ab = self._mono() + TIEFSTAND_WIEDERHOLEN_S
            await self._gib(ev.HerunterfahrenFehlgeschlagen(str(e) or repr(e)), neu)
            return False
        if simuliert:
            self._tiefstand_wieder_ab = self._mono() + TIEFSTAND_WIEDERHOLEN_S
            await self._gib(ev.HerunterfahrenFehlgeschlagen("", simuliert=True), neu)
            return False
        return True


def parse_taste(text: str) -> Literal["kurz", "lang"] | None:
    """Antwort des ``pisugar-server`` auf die Tasten-Abfrage als ``kurz`` / ``lang``; ``None``: keine Taste. **Am Pi zu prüfen.**

    Verstanden werden die Wörter ``long`` / ``lang`` und ``single`` / ``short`` / ``kurz`` hinter dem Doppelpunkt der Antwortzeile
    (``name: wert``). Alles andere (auch ``double``) ist keine Taste."""
    t = text.strip().lower()
    wert = t.split(":", 1)[1].strip() if ":" in t else t
    if wert in ("long", "lang"):
        return "lang"
    if wert in ("single", "short", "kurz"):
        return "kurz"
    return None
