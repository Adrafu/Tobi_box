"""Prüfpunkte der Status-Admin-Karte (``core-interface.md``, 12.3, CUJ 11).

Vier Punkte in fester Reihenfolge: Leser, Medien, Netz, Speicher. Die
Bewertung ist reine Logik (``pruefe_*``) und braucht weder pytest noch einen
Leser. Die Prüfroutine ``pruefe`` sammelt die Messwerte und liefert die
Ergebnisse samt Tonfolge (je Punkt ein Ton: ``pruef_ok`` hoch und kurz,
``pruef_fehler`` tief). ``python -m tobibox.selftest MEDIENORDNER`` führt sie aus.
"""

from __future__ import annotations

import logging
import shutil
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from . import events as ev
from . import library

SPEICHER_MIN_FREI_MB = 500
PUNKTE = ("leser", "medien", "netz", "speicher")
TON_OK, TON_FEHLER = "pruef_ok", "pruef_fehler"


@dataclass(frozen=True, slots=True)
class Pruefpunkt:
    name: str
    ok: bool
    detail: str

    @property
    def ton(self) -> str:
        return TON_OK if self.ok else TON_FEHLER


def pruefe_leser(leser: str) -> Pruefpunkt:
    """``leser`` ist der Wert aus 12.2: ``ok``, ``simulation``, ``getrennt`` oder ``fehler``."""
    return Pruefpunkt("leser", leser in ("ok", "simulation"), leser)


def pruefe_medien(serien: Iterable[ev.Serie] | None) -> Pruefpunkt:
    """``None``: Medienordner nicht lesbar."""
    if serien is None:
        return Pruefpunkt("medien", False, "Medienordner nicht lesbar")
    serien = tuple(serien)
    if not any(s.folgen for s in serien):
        return Pruefpunkt("medien", False, "keine Serie mit Folge")
    status = library.ueberraschung_status(serien)
    if status != "ok":
        return Pruefpunkt("medien", False, f"Überraschungs-Serie: {status}")
    return Pruefpunkt("medien", True, f"{len(serien)} Serien")


def pruefe_netz(netz: str, ha_verbunden: bool) -> Pruefpunkt:
    ok = netz in ("home", "hotspot") and bool(ha_verbunden)
    return Pruefpunkt("netz", ok, f"{netz}, Broker {'verbunden' if ha_verbunden else 'nicht verbunden'}")


def pruefe_speicher(frei_mb: int | None, datei_verloren: bool, min_frei_mb: int = SPEICHER_MIN_FREI_MB) -> Pruefpunkt:
    if frei_mb is None:
        return Pruefpunkt("speicher", False, "freier Platz unbekannt")
    if datei_verloren:
        return Pruefpunkt("speicher", False, "Datei verloren seit dem Start")
    return Pruefpunkt("speicher", frei_mb >= min_frei_mb, f"{frei_mb} MB frei (Minimum {min_frei_mb})")


def tonfolge(ergebnisse: Iterable[Pruefpunkt]) -> list[str]:
    """Ein Ton je Prüfpunkt in der gegebenen (festen) Reihenfolge."""
    return [p.ton for p in ergebnisse]


@dataclass(frozen=True, slots=True)
class Pruefbericht:
    punkte: tuple[Pruefpunkt, ...]

    @property
    def toene(self) -> list[str]:
        return tonfolge(self.punkte)

    @property
    def alles_ok(self) -> bool:
        return all(p.ok for p in self.punkte)

    def als_dict(self) -> dict:
        return {"ok": self.alles_ok, "punkte": [{"name": p.name, "ok": p.ok, "detail": p.detail, "ton": p.ton} for p in self.punkte],
                "toene": self.toene}


def freier_platz_mb(pfad: Path) -> int | None:
    try:
        return shutil.disk_usage(pfad).free // (1024 * 1024)
    except OSError:
        return None


def pruefe(
    medien: str | Path,
    *,
    leser: str | None = None,
    netz: str = "offline",
    ha_verbunden: bool = False,
    datei_verloren: bool = False,
    min_frei_mb: int = SPEICHER_MIN_FREI_MB,
) -> Pruefbericht:
    """Eingebaute Prüfroutine. ``leser=None`` (kein Leser konfiguriert/verbunden) gilt als ``simulation``.

    Der Dienst reicht ``leser``, ``netz``, ``ha_verbunden`` und ``datei_verloren`` aus seinem
    Zustand herein; ohne Angabe gilt: Leser Simulation, Netz offline.
    """
    medien = Path(medien)
    log = logging.getLogger("tobibox")
    alte, log.handlers = log.handlers, [logging.NullHandler()]
    try:
        serien = library.lade_bibliothek(medien).serien if medien.is_dir() else None
    except OSError:
        serien = None
    finally:
        log.handlers = alte
    frei = freier_platz_mb(medien if medien.exists() else medien.parent)
    return Pruefbericht((
        pruefe_leser(leser or "simulation"),
        pruefe_medien(serien),
        pruefe_netz(netz, ha_verbunden),
        pruefe_speicher(frei, datei_verloren, min_frei_mb),
    ))


def main(argv: list[str] | None = None) -> int:
    a = sys.argv[1:] if argv is None else argv
    b = pruefe(a[0] if a else ".")
    for p in b.punkte:
        print(f"{p.name:9} {'ok' if p.ok else 'FEHLER':6} {p.detail}  [{p.ton}]")
    return 0 if b.alles_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
