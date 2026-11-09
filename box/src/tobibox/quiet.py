"""Teilautomat Leise-Zeiten ``quiet`` (``core-interface.md``, 5.2, 8 und 9; Tabelle „Leise-Zeiten“).

Reine Funktionen: kein Zugriff auf Dateien, Netz, Uhr oder Zufall. Zustände ``normal``, ``leiser``, ``stumm``.

* Die Fenster kommen mit ``KonfigGeladen`` (die lokale Kopie der Konfiguration gilt offline, das lädt ``app``).
* Zeitpunkte: ``jetzt.wall`` in der Zeitzone der Konfiguration (``data-model.md``, Abschnitt 2). Bei einem
  Fenster über Mitternacht endet es am Tag nach dem Starttag. Sommerzeit: eine nicht vorhandene Ortszeit gilt
  als die nächste gültige Minute, eine doppelte als ihr erstes Auftreten.
* Mehrere aktive Fenster: „stumm“ gewinnt, sonst „leiser“ mit der kleinsten Grenze.
* Ist ``jetzt.zeit_ok`` falsch, gilt die kleinste „leiser“-Grenze aller Fenster, nie „stumm“.
* ``quiet`` gibt keine ``Pausieren``-Befehle aus. Bei „stumm“ pausiert die Sitzung (``StummBeginnt``).
  Endet „stumm“, kommt nur ``StummEndet``: nichts startet von selbst (Entscheidung B).
* „leiser“: Ist die Wiedergabe lauter als die Grenze (``wirksam`` aus ``LautstaerkeGeaendert``), sinkt die
  Grenze ``ausblenden`` in ``LEISER_ABSENKEN_S`` linear auf die Fenster-Grenze; danach gilt ``leise_zeit``
  und ``ausblenden`` wird gelöscht. Sonst wird ``leise_zeit`` sofort gesetzt.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import events as ev
from .events import Jetzt
from .volume import GRENZE_AUSBLENDEN, GRENZE_LEISE_ZEIT, rampe

LEISER_ABSENKEN_S = 3.0

Ausgabe = tuple[ev.Befehl | ev.InternesEreignis, ...]

_UTC = timezone.utc
_VORGABE_ZONE = "Europe/Berlin"


@dataclass(frozen=True, slots=True)
class Zustand:
    modus: str = "normal"  # "normal" | "leiser" | "stumm"
    konfig: ev.LeiseZeiten | None = None
    #: zuletzt ausgegebener Wert der Grenze ``leise_zeit`` (``None``: nicht gesetzt)
    gesetzt: int | None = None
    #: Absenk-Rampe: (von, ziel, start_mono) oder ``None``
    absenken: tuple[int, int, float] | None = None
    #: letzte gemeldete wirksame Lautstärke
    wirksam: int = 100
    #: zuletzt gesehene Vertrauenswürdigkeit der Zeit (für den Hinweis bei Wechsel)
    zeit_ok: bool = True


def neuer_zustand() -> Zustand:
    return Zustand()


def kennzeichen(zustand: Zustand) -> str:
    return zustand.modus


def _prot(ebene: str, ereignis: str, ergebnis: str, **daten) -> ev.Protokoll:
    return ev.Protokoll("quiet", ebene, ereignis, ergebnis, None, daten)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Fenster und Uhrzeit (rein)
# --------------------------------------------------------------------------


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:  # pragma: no cover - die Prüfung in ``store`` lässt nur bekannte Namen zu
        return ZoneInfo(_VORGABE_ZONE)


def _ortszeit_zu_utc(tag: date, hhmm: str, zone: ZoneInfo, plus_tage: int = 0) -> datetime:
    """Wanduhrzeit ``hhmm`` am Tag ``tag + plus_tage`` als UTC-Zeitpunkt.

    Nicht vorhandene Ortszeit: nächste gültige Minute. Doppelte Ortszeit: erstes Auftreten (``fold=0``).
    """
    h, m = int(hhmm[:2]), int(hhmm[3:5])
    naiv = datetime.combine(tag + timedelta(days=plus_tage), time(h, m))
    for _ in range(24 * 60):
        lokal = naiv.replace(tzinfo=zone, fold=0)
        utc = lokal.astimezone(_UTC)
        if utc.astimezone(zone).replace(tzinfo=None) == naiv:
            return utc
        naiv += timedelta(minutes=1)
    return naiv.replace(tzinfo=zone).astimezone(_UTC)  # pragma: no cover


def _fenster_aktiv(f: ev.Fenster, zone: ZoneInfo, jetzt_utc: datetime, lokal_tag: date) -> bool:
    # Das Fenster kann am Vortag begonnen haben (über Mitternacht).
    for zurueck in (0, 1):
        d = lokal_tag - timedelta(days=zurueck)
        if d.isoweekday() not in f.tage:
            continue
        ueber_nacht = f.bis <= f.von  # "22:00" bis "07:00"; ``von == bis`` lässt die Prüfung nicht zu
        start = _ortszeit_zu_utc(d, f.von, zone)
        ende = _ortszeit_zu_utc(d, f.bis, zone, 1 if ueber_nacht else 0)
        if start <= jetzt_utc < ende:
            return True
    return False


def wirkung_jetzt(lz: ev.LeiseZeiten | None, jetzt: Jetzt) -> tuple[str, int | None]:
    """Wirkung zur Zeit ``jetzt``: ``("normal", None)``, ``("leiser", grenze)`` oder ``("stumm", None)``."""
    if lz is None or not lz.fenster:
        return "normal", None
    leiser_alle = [f.grenze for f in lz.fenster if f.wirkung == "leiser" and f.grenze is not None]
    if not jetzt.zeit_ok:
        # Uhr nicht vertrauenswürdig: kleinste „leiser“-Grenze aller Fenster, nie „stumm“.
        return ("leiser", min(leiser_alle)) if leiser_alle else ("normal", None)
    zone = _zone(lz.zeitzone)
    try:
        jetzt_utc = datetime.fromtimestamp(jetzt.wall, _UTC)
        lokal_tag = jetzt_utc.astimezone(zone).date()
        aktiv = [f for f in lz.fenster if _fenster_aktiv(f, zone, jetzt_utc, lokal_tag)]
    except (OverflowError, ValueError, OSError):
        # Wanduhr außerhalb des Rechenbereichs (B8): wie eine unsichere Uhr, nie „stumm“, kein Absturz des Kerns
        return ("leiser", min(leiser_alle)) if leiser_alle else ("normal", None)
    if any(f.wirkung == "stumm" for f in aktiv):
        return "stumm", None
    grenzen = [f.grenze for f in aktiv if f.wirkung == "leiser" and f.grenze is not None]
    if grenzen:
        return "leiser", min(grenzen)
    return "normal", None


# --------------------------------------------------------------------------
# Übergänge
# --------------------------------------------------------------------------


def _auswerten(z: Zustand, jetzt: Jetzt) -> tuple[Zustand, list]:
    ziel_modus, ziel_grenze = wirkung_jetzt(z.konfig, jetzt)
    out: list = []

    # Hinweis bei Wechsel der Vertrauenswürdigkeit (an HA geht er über das Protokoll und den Status).
    if jetzt.zeit_ok != z.zeit_ok:
        if jetzt.zeit_ok:
            out.append(_prot("INFO", "zeit", "wieder_vertrauenswuerdig"))
        else:
            out.append(_prot("WARNING", "zeit", "unsicher", quelle=jetzt.zeit_quelle, wirkung=ziel_modus))
        z = replace(z, zeit_ok=jetzt.zeit_ok)

    alt = z.modus

    if ziel_modus == "stumm":
        if alt != "stumm":
            # Eine laufende Absenk-Rampe endet sofort; die Sitzung blendet danach selbst aus (Grenze ``ausblenden``).
            if z.absenken is not None:
                out.append(ev.GrenzeGesetzt(GRENZE_AUSBLENDEN, None))
                if z.gesetzt != z.absenken[1]:
                    out.append(ev.GrenzeGesetzt(GRENZE_LEISE_ZEIT, z.absenken[1]))
                    z = replace(z, gesetzt=z.absenken[1])
                z = replace(z, absenken=None)
            out.append(ev.StummBeginnt())
            out.append(_prot("INFO", "ruhe", "stumm", von=alt))
            z = replace(z, modus="stumm")
        # Die Grenze ``leise_zeit`` bleibt unter „stumm“ unverändert.
        return z, out

    if alt == "stumm":
        out.append(ev.StummEndet())

    if ziel_modus == "leiser":
        assert ziel_grenze is not None
        z, extra = _leiser(z, ziel_grenze, jetzt, aus_stumm=(alt == "stumm"))
        out.extend(extra)
        if alt != "leiser":
            out.append(_prot("INFO", "ruhe", "leiser", von=alt, grenze=ziel_grenze))
        return replace(z, modus="leiser"), out

    # normal: Fenster-Grenze aus
    if z.absenken is not None:
        out.append(ev.GrenzeGesetzt(GRENZE_AUSBLENDEN, None))
    if z.gesetzt is not None:
        out.append(ev.GrenzeGesetzt(GRENZE_LEISE_ZEIT, None))
    if alt != "normal":
        out.append(_prot("INFO", "ruhe", "normal", von=alt))
    return replace(z, modus="normal", gesetzt=None, absenken=None), out


def _leiser(z: Zustand, grenze: int, jetzt: Jetzt, *, aus_stumm: bool) -> tuple[Zustand, list]:
    out: list = []
    if z.absenken is not None:
        if z.absenken[1] == grenze:
            return z, out  # Rampe läuft schon zu diesem Ziel
    elif z.gesetzt == grenze:
        return z, out  # nichts zu tun
    if z.wirksam > grenze and not aus_stumm:
        # laute Wiedergabe: sanft absenken (von = wirksam)
        # (der erste Wert der Rampe ist ``von``; ``_rampe_weiter`` gibt ihn beim nächsten ``Takt`` aus)
        return replace(z, absenken=(z.wirksam, grenze, jetzt.mono)), out
    # nicht laut genug für eine Rampe (oder aus „stumm“ heraus): sofort setzen
    if z.absenken is not None:
        out.append(ev.GrenzeGesetzt(GRENZE_AUSBLENDEN, None))
    out.append(ev.GrenzeGesetzt(GRENZE_LEISE_ZEIT, grenze))
    return replace(z, gesetzt=grenze, absenken=None), out


def ziel_grenze_absenken(z: Zustand) -> int | None:
    """Das Ziel einer laufenden „leiser“-Absenkung, sonst ``None``. Töne richten sich schon während der Rampe danach (B13)."""
    return z.absenken[1] if z.absenken is not None else None


def _rampe_weiter(z: Zustand, jetzt: Jetzt) -> tuple[Zustand, list]:
    if z.absenken is None:
        return z, []
    von, ziel, start = z.absenken
    wert = rampe(von, ziel, start, LEISER_ABSENKEN_S, jetzt.mono)
    if jetzt.mono - start >= LEISER_ABSENKEN_S:
        return replace(z, absenken=None, gesetzt=ziel), [
            ev.GrenzeGesetzt(GRENZE_LEISE_ZEIT, ziel),
            ev.GrenzeGesetzt(GRENZE_AUSBLENDEN, None),
        ]
    return z, [ev.GrenzeGesetzt(GRENZE_AUSBLENDEN, wert)]


def step(zustand: Zustand, ereignis: ev.Ereignis | ev.InternesEreignis, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    z = zustand

    if isinstance(ereignis, ev.LautstaerkeGeaendert):
        return replace(z, wirksam=ereignis.wirksam), ()

    if isinstance(ereignis, ev.KonfigGeladen):
        z = replace(z, konfig=ereignis.konfig.leise_zeiten)
        z, out = _auswerten(z, jetzt)
        return z, tuple(out)

    if isinstance(ereignis, (ev.Takt, ev.ZeitquelleGeaendert)):
        z, out = _auswerten(z, jetzt)
        z, mehr = _rampe_weiter(z, jetzt)
        return z, tuple(out + mehr)

    return z, ()
