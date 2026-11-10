"""Die Uhr-Regel der Box, an einer Stelle (Ein/Aus, 10.11.; AP E1-5, kein Asyncio).

Wann ist die Wanduhr vertrauenswürdig (``zeit_ok``)? Die Regel brauchen der Box-Dienst (``net.Zeitquelle``, ``power``, ``app``) und der
Frühdienst (``fruehton``) gleich. Früher stand sie nur im Dienst; eine Kopie im Frühdienst würde grün bleiben, wenn jemand sie im Dienst ändert.

* ``system``: Die Systemuhr gilt immer (Mac, alle Quellen ``sim``).
* Sonst: NTP seit dem Start synchron → ``ntp``; sonst eine beim Start gelesene, plausible RTC → ``rtc``; sonst ``unbekannt`` und nicht
  vertrauenswürdig (Leise-Zeiten gelten dann vorsichtig, nie „stumm“).
* Ohne ``[netz]`` und ``[strom]`` gilt die Systemuhr auf Linux (Pi) nur mit NTP als sicher; ``[uhr] ntp_pflicht`` überstimmt die Vorgabe.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from . import events as ev

#: Eine RTC vor diesem Zeitpunkt hat ihre Zeit verloren (leerer Akku): sie gilt nicht als vertrauenswürdig.
RTC_FRUEHESTENS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def rtc_plausibel(t: datetime | None) -> bool:
    return t is not None and t >= RTC_FRUEHESTENS


def bewerte(*, system: bool, ntp_ok: bool, rtc_ok: bool) -> tuple[ev.ZeitQuelle, bool]:
    """Quelle der Uhr und ob sie vertrauenswürdig ist."""
    if system:
        return "system", True
    if ntp_ok:
        return "ntp", True
    if rtc_ok:
        return "rtc", True
    return "unbekannt", False


def alle_sim(*abschnitte) -> bool:  # type: ignore[no-untyped-def]
    """Alle vorhandenen Abschnitte ``[netz]`` / ``[strom]`` haben die Quelle ``sim`` (Mac): dann gilt die Systemuhr."""
    return all(a.simulation for a in abschnitte if a is not None)


def systemuhr_pruefen_noetig(ntp_pflicht: bool | None, linux: bool | None = None) -> bool:
    """Linux (Pi) ohne ``[netz]`` und ``[strom]``: Ohne NTP ist die Zeit unsicher. ``ntp_pflicht`` überstimmt die Vorgabe nach dem System."""
    if ntp_pflicht is not None:
        return ntp_pflicht
    return sys.platform.startswith("linux") if linux is None else linux


def fruehdienst_uhr(konfig, rtc: datetime | None, linux: bool | None = None) -> tuple[ev.ZeitQuelle, bool]:  # type: ignore[no-untyped-def]
    """Die Uhr für den Frühdienst: er hat keinen NTP-Stand und keinen laufenden Dienst.

    Mac (alle Quellen ``sim``) und eine Systemuhr ohne NTP-Pflicht: ``system``, sicher. Sonst sicher nur mit einer plausiblen RTC,
    die ``pisugar-server`` geliefert hat (``rtc``). Ohne sie (``pisugar-server`` läuft noch nicht, Fehler): unsicher, es gelten die
    Regeln wie bei unsicherer Uhr (kleinste „leiser“-Grenze, nie „stumm“)."""
    hat_abschnitt = konfig.netz is not None or konfig.strom is not None
    if hat_abschnitt:
        if alle_sim(konfig.netz, konfig.strom):
            return "system", True
    elif not systemuhr_pruefen_noetig(konfig.uhr.ntp_pflicht, linux):
        return "system", True
    return bewerte(system=False, ntp_ok=False, rtc_ok=rtc_plausibel(rtc))
