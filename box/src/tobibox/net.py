"""Netz-Klasse und Zeitquelle (``core-interface.md`` 3.6 und 3.7; Design „Netz, Sync, Strom“).

* **Netz-Klasse:** ``home`` (Heim-SSID **und** NAS erreichbar), ``hotspot`` (Hotspot-SSID) oder ``offline``.
  Auf dem Pi fragt ``NmcliSsid`` den NetworkManager nach dem aktiven WLAN; am Mac und im Test steht ``SimSsid``
  an seiner Stelle. Die Namen der WLANs kommen aus ``[netz]`` in ``tobibox.toml``, nie aus dem Repo.
* **Zeitquelle:** ``Zeitquelle`` bewertet RTC (meldet ``power``) und NTP (prüft ``net``): NTP seit dem Start
  synchron ist ``ntp``, sonst eine plausible RTC ``rtc``, sonst ``unbekannt`` (nicht vertrauenswürdig). Am Mac gilt
  die Systemuhr (``system``, immer vertrauenswürdig).

``net`` sendet ``NetzKlasse`` (bei Änderung und einmal beim Start) und ``ZeitquelleGeaendert``. Es führt keine Befehle aus.
Die Verdrahtung in ``app`` macht AP 3.7: ``Netz.lauf()`` als Aufgabe, ``ausgabe`` = Eingang der Ereignisschleife.
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from collections.abc import Callable
from typing import Any, Protocol

from . import events as ev
from .config import NetzKonfig
from .eventlog import logge

NAS_FRIST_S = 2.0  # so lange wartet der Verbindungsversuch zum NAS
NTP_MARKE = Path("/run/systemd/timesync/synchronized")
BEFEHL_FRIST_S = 5.0  # so lange darf ``nmcli`` oder ``timedatectl`` brauchen


# --------------------------------------------------------------------------
# Regel (rein)
# --------------------------------------------------------------------------


def klassifiziere(ssid: str | None, nas_erreichbar: bool, konfig: NetzKonfig) -> ev.NetzKlasse:
    """Die Netz-Klasse aus dem aktiven WLAN und der NAS-Probe.

    ``home`` braucht die Heim-SSID und, falls ``nas_host`` eingetragen ist, einen erreichbaren NAS (über Tailscale).
    Ist die Heim-SSID da, aber der NAS nicht erreichbar, ist die Box ``offline``: Auch der Broker liegt hinter Tailscale.
    Jedes andere oder fehlende WLAN ist ebenfalls ``offline``."""
    if ssid is None:
        return ev.NetzKlasse("offline")
    if konfig.heim_ssid is not None and ssid == konfig.heim_ssid:
        return ev.NetzKlasse("home" if (konfig.nas_host is None or nas_erreichbar) else "offline")
    if konfig.hotspot_ssid is not None and ssid == konfig.hotspot_ssid:
        return ev.NetzKlasse("hotspot")
    return ev.NetzKlasse("offline")


# --------------------------------------------------------------------------
# Quellen: WLAN, NAS, NTP
# --------------------------------------------------------------------------


class SsidQuelle(Protocol):
    async def ssid(self) -> str | None: ...


class NasPruefer(Protocol):
    async def erreichbar(self) -> bool: ...


class NtpQuelle(Protocol):
    async def synchron(self) -> bool: ...


def _teile_nmcli(zeile: str) -> list[str]:
    """``nmcli -t`` trennt mit ``:`` und schreibt ein ``:`` im Namen als ``\\:``."""
    felder, aktuell, i = [], [], 0
    while i < len(zeile):
        c = zeile[i]
        if c == "\\" and i + 1 < len(zeile):
            aktuell.append(zeile[i + 1])
            i += 2
            continue
        if c == ":":
            felder.append("".join(aktuell))
            aktuell = []
        else:
            aktuell.append(c)
        i += 1
    felder.append("".join(aktuell))
    return felder


def parse_nmcli(ausgabe: str) -> str | None:
    """Aus ``nmcli -t -f ACTIVE,SSID dev wifi`` die SSID der Zeile mit ``yes`` (sonst ``None``)."""
    for zeile in ausgabe.splitlines():
        felder = _teile_nmcli(zeile)
        if len(felder) >= 2 and felder[0] == "yes" and felder[1]:
            return felder[1]
    return None


async def _lauf(*argv: str) -> str | None:
    """Ein Programm mit Frist ausführen; ``None`` bei jedem Fehler (kein Programm, Frist, Rückgabewert)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
    except OSError:
        return None
    try:
        aus, _ = await asyncio.wait_for(proc.communicate(), BEFEHL_FRIST_S)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return None
    return aus.decode("utf-8", "replace") if proc.returncode == 0 else None


class NmcliSsid:
    """Pi: das aktive WLAN laut NetworkManager (``nmcli``). Ohne ``nmcli`` oder bei Fehler: kein WLAN."""

    def __init__(self) -> None:
        self._gewarnt = False

    async def ssid(self) -> str | None:
        aus = await _lauf("nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi")
        if aus is None:
            if not self._gewarnt:
                self._gewarnt = True
                logge("net", "WARNING", "nmcli", "fehlt", daten={"hinweis": "nmcli nicht ausführbar, Netz gilt als offline"})
            return None
        self._gewarnt = False
        return parse_nmcli(aus)


class SimSsid:
    """Mac und Test: das WLAN wird vorgegeben (``tobibox sim`` setzt es in AP 3.7)."""

    def __init__(self, ssid: str | None = None) -> None:
        self.wert = ssid

    def setze(self, ssid: str | None) -> None:
        self.wert = ssid

    async def ssid(self) -> str | None:
        return self.wert


class TcpNas:
    """Der NAS gilt als erreichbar, wenn eine TCP-Verbindung zum rsync-Port klappt (Tailscale ist oben)."""

    def __init__(self, host: str, port: int, frist_s: float = NAS_FRIST_S) -> None:
        self.host, self.port, self.frist_s = host, port, frist_s

    async def erreichbar(self) -> bool:
        try:
            _, w = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), self.frist_s)
        except (OSError, asyncio.TimeoutError):
            return False
        w.close()
        try:
            await w.wait_closed()
        except OSError:
            pass
        return True


class SimNas:
    def __init__(self, erreichbar: bool = True) -> None:
        self.wert = erreichbar

    async def erreichbar(self) -> bool:
        return self.wert


class TimedatectlNtp:
    """Pi: ``timedatectl`` meldet, ob die Uhr per NTP synchron ist."""

    async def synchron(self) -> bool:
        # systemd-timesyncd legt diese Datei an, sobald die Uhr einmal synchron war (B15)
        if await asyncio.to_thread(NTP_MARKE.exists):
            return True
        aus = await _lauf("timedatectl", "show", "-p", "NTPSynchronized", "--value")
        return aus is not None and aus.strip() == "yes"


class SimNtp:
    def __init__(self, synchron: bool = False) -> None:
        self.wert = synchron

    async def synchron(self) -> bool:
        return self.wert


# --------------------------------------------------------------------------
# Zeitquelle
# --------------------------------------------------------------------------


class Zeitquelle:
    """Bewertet die Uhr. Geteilt von ``net`` (NTP) und ``power`` (RTC); jede Änderung ist ein Ereignis.

    ``system=True`` (Mac): die Systemuhr gilt immer. Sonst: NTP seit dem Start synchron → ``ntp`` (bleibt, auch wenn
    NTP später kurz ausfällt: die Uhr läuft weiter); sonst eine beim Start gelesene, plausible RTC → ``rtc``;
    sonst ``unbekannt`` und nicht vertrauenswürdig (Leise-Zeiten gelten dann vorsichtig, Design „Uhr und Zeitquelle“).
    """

    def __init__(self, *, system: bool = False) -> None:
        self._system = system
        self._rtc_ok = False
        self._ntp_ok = False
        self.quelle: ev.ZeitQuelle = "system" if system else "unbekannt"
        self.vertrauenswuerdig = system

    def _bewerte(self) -> tuple[ev.ZeitQuelle, bool]:
        if self._system:
            return "system", True
        if self._ntp_ok:
            return "ntp", True
        if self._rtc_ok:
            return "rtc", True
        return "unbekannt", False

    def _aendere(self) -> ev.ZeitquelleGeaendert | None:
        quelle, ok = self._bewerte()
        if (quelle, ok) == (self.quelle, self.vertrauenswuerdig):
            return None
        self.quelle, self.vertrauenswuerdig = quelle, ok
        logge("net", "INFO", "zeitquelle", quelle, daten={"zeit_ok": ok})
        return ev.ZeitquelleGeaendert(quelle, ok)

    def rtc(self, plausibel: bool) -> ev.ZeitquelleGeaendert | None:
        """``power`` hat die RTC beim Start gelesen."""
        self._rtc_ok = plausibel
        return self._aendere()

    def ntp(self, synchron: bool) -> ev.ZeitquelleGeaendert | None:
        """``net`` hat NTP geprüft. Ein Verlust der Synchronisation nimmt ``ntp`` nicht zurück."""
        self._ntp_ok = self._ntp_ok or synchron
        return self._aendere()

    def setze(self, quelle: ev.ZeitQuelle, vertrauenswuerdig: bool) -> ev.ZeitquelleGeaendert | None:
        """Nur für ``tobibox sim`` und Tests: die Bewertung von Hand vorgeben."""
        if (quelle, vertrauenswuerdig) == (self.quelle, self.vertrauenswuerdig):
            return None
        self.quelle, self.vertrauenswuerdig = quelle, vertrauenswuerdig
        return ev.ZeitquelleGeaendert(quelle, vertrauenswuerdig)


# --------------------------------------------------------------------------
# Netz
# --------------------------------------------------------------------------


class Netz:
    """Fragt in jedem Durchgang WLAN, NAS und NTP und sendet, was sich geändert hat."""

    def __init__(
        self,
        konfig: NetzKonfig,
        ssid: SsidQuelle,
        nas: NasPruefer | None = None,
        ntp: NtpQuelle | None = None,
        zeit: Zeitquelle | None = None,
        ausgabe: Callable[[ev.Ereignis], Any] | None = None,
    ) -> None:
        self.konfig = konfig
        self._ssid, self._nas, self._ntp = ssid, nas, ntp
        self.zeit = zeit if zeit is not None else Zeitquelle(system=konfig.simulation)
        self._ausgabe = ausgabe
        self.klasse: ev.NetzKlasse | None = None  # noch nie gemessen

    @classmethod
    def aus_konfig(
        cls, konfig: NetzKonfig, zeit: Zeitquelle | None = None, ausgabe: Callable[[ev.Ereignis], Any] | None = None
    ) -> Netz:
        """Die echten Quellen (Pi) oder die Simulation (Mac), je nach ``[netz] quelle``."""
        nas = None
        if konfig.nas_host is not None:
            nas = SimNas() if konfig.simulation else TcpNas(konfig.nas_host, konfig.nas_port)
        if konfig.simulation:
            return cls(konfig, SimSsid(), nas, SimNtp(), zeit, ausgabe)
        return cls(konfig, NmcliSsid(), nas, TimedatectlNtp(), zeit, ausgabe)

    async def pruefe(self) -> list[ev.Ereignis]:
        """Ein Durchgang. Gibt die neuen Ereignisse zurück und sendet sie an ``ausgabe``."""
        neu: list[ev.Ereignis] = []
        ssid = await self._ssid.ssid()
        nas_ok = True
        if self._nas is not None and ssid is not None and ssid == self.konfig.heim_ssid:
            nas_ok = await self._nas.erreichbar()  # nur im Heim-WLAN fragen (sonst kostet es nur Zeit)
        klasse = klassifiziere(ssid, nas_ok, self.konfig)
        if klasse != self.klasse:
            logge("net", "INFO", "netz_klasse", klasse.klasse, daten={"vorher": self.klasse.klasse if self.klasse else None})
            self.klasse = klasse
            neu.append(klasse)
        if self._ntp is not None:
            z = self.zeit.ntp(await self._ntp.synchron())
            if z is not None:
                neu.append(z)
        for e in neu:
            await self._gib(e)
        return neu

    async def _gib(self, e: ev.Ereignis) -> None:
        if self._ausgabe is None:
            return
        r = self._ausgabe(e)
        if inspect.isawaitable(r):
            await r

    async def lauf(self) -> None:
        """Dauerlauf (eine Aufgabe in ``app``). Ein Fehler in einem Durchgang beendet ihn nicht."""
        while True:
            try:
                await self.pruefe()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - der Dauerlauf darf nie stehen bleiben
                logge("net", "ERROR", "pruefen", "fehler", daten={"detail": repr(e)})
            await asyncio.sleep(self.konfig.intervall_s)
