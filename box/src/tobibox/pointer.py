"""Reine Zeigerregeln (``core-interface.md``, Abschnitt 6.3, und ``data-model.md``, 3).

Keine Ein-/Ausgabe, keine Uhr. ``session`` benutzt diese Funktionen. Ein Zeiger
ist (Folge, Track, Position im Track) (Entscheidung F, 05.11.). Es gibt den
**Serien-Zeiger** (``art="serie"``, ein Zeiger je Serie) und den
**Folgen-Zeiger** (``art="folge"``, ein Zeiger je Serie und Folge).

Die Bibliothek liefert ``Serie.folgen`` nur mit vorhandenen Folgen, deshalb ist
„fehlende Folge -> nächste vorhandene“ hier: die Folge, die jetzt am Platz
``Zeiger.index`` steht.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from .events import Serie, Zeiger

RUECKSPRUNG_S = 3.0
ZURUECK_NEU_S = 3.0
SPEICHERN_PERIODISCH_S = 30.0
#: Ist ein Zeiger unverändert, wird sein Zeitstempel erst nach dieser Zeit neu geschrieben (Entscheidung N, 09.11.)
STEMPEL_ERNEUERN_S = 3600.0
TAG_S = 86400.0

_EPS = 1e-9

Art = Literal["serie", "folge"]
Schluessel = tuple[str, str, str]


def schluessel(art: Art, serie_id: str, datei: str) -> Schluessel:
    """Schlüssel eines Zeigers im Zustand: Serien-Zeiger je Serie, Folgen-Zeiger je (Serie, Folge)."""
    return (art, serie_id, datei if art == "folge" else "")


def schluessel_von(z: Zeiger) -> Schluessel:
    return schluessel(z.art, z.serie_id, z.datei)


@dataclass(frozen=True, slots=True)
class Ort:
    """Wo ein Ziel beim Auflegen weiterspielt."""

    datei: str
    index: int
    track: int
    position_s: float
    folge_fehlte: bool = False
    track_fehlte: bool = False


def abrunden(x: float) -> float:
    """Auf 1 Nachkommastelle abrunden (nie weiter vorn als die Wirklichkeit)."""
    if not math.isfinite(x):
        return 0.0
    return math.floor(x * 10 + _EPS) / 10 if x > 0 else 0.0


def ruecksprung(position_s: float) -> float:
    """Position nach dem Rücksprung von ``RUECKSPRUNG_S``; nie unter 0."""
    return max(0.0, position_s - RUECKSPRUNG_S)


def tracks_von(serie: Serie, datei: str) -> tuple[str, ...]:
    """Track-Pfade (relativ zum Serien-Ordner) der Folge; eine Datei ist ein Track."""
    return serie.tracks.get(datei) or (datei,)


def index_am_zeiger(serie: Serie, zeiger: Zeiger | None) -> int:
    """Index der Folge, auf die der Zeiger zeigt (Fallback: Hinweis ``index``, sonst 0)."""
    n = len(serie.folgen)
    if zeiger is None or n == 0:
        return 0
    if zeiger.datei in serie.folgen:
        return serie.folgen.index(zeiger.datei)
    return zeiger.index if zeiger.index is not None and 0 <= zeiger.index < n else 0


def _track_und_position(serie: Serie, datei: str, zeiger: Zeiger) -> tuple[int, float, bool]:
    """(Track, Position mit Rücksprung, Track fehlte). Fehlender Track: Track 0, Position 0."""
    if zeiger.track >= len(tracks_von(serie, datei)):
        return 0, 0.0, True
    return zeiger.track, ruecksprung(zeiger.position_s), False


def ort_am_zeiger(serie: Serie, zeiger: Zeiger | None) -> Ort | None:
    """Start-Ort für ein Ziel ``serie`` (Serien-Zeiger); ``None`` bei leerer Serie."""
    folgen = serie.folgen
    if not folgen:
        return None
    if zeiger is None:
        return Ort(folgen[0], 0, 0, 0.0)
    if zeiger.datei in folgen:
        track, pos, fehlte = _track_und_position(serie, zeiger.datei, zeiger)
        return Ort(zeiger.datei, folgen.index(zeiger.datei), track, pos, False, fehlte)
    i = index_am_zeiger(serie, zeiger)
    return Ort(folgen[i], i, 0, 0.0, True)


def ort_der_folge(serie: Serie, folge: str, zeiger: Zeiger | None) -> Ort | None:
    """Start-Ort für ein Ziel ``folge`` (Folgen-Zeiger); ``None``, wenn die Folge fehlt."""
    if folge not in serie.folgen:
        return None
    index = serie.folgen.index(folge)
    if zeiger is None:
        return Ort(folge, index, 0, 0.0)
    track, pos, fehlte = _track_und_position(serie, folge, zeiger)
    return Ort(folge, index, track, pos, False, fehlte)


def aktueller_index(serie: Serie, datei: str | None, index_hinweis: int) -> int:
    """Platz von ``datei`` in der Serie; fehlt sie, der Hinweis (begrenzt)."""
    n = len(serie.folgen)
    if datei is not None and datei in serie.folgen:
        return serie.folgen.index(datei)
    return max(0, min(index_hinweis, n - 1))


def springe(serie: Serie, von_index: int, delta: int) -> tuple[str, int]:
    """Folge ``delta`` Plätze weiter, zyklisch (nach der letzten Folge 1)."""
    n = len(serie.folgen)
    ziel = (von_index + delta) % n
    return serie.folgen[ziel], ziel


def naechste_folge(serie: Serie, datei: str, index_hinweis: int = 0) -> tuple[str, int]:
    """Nach einem Folgenende: nächste Folge, nach der letzten Folge 1."""
    return springe(serie, aktueller_index(serie, datei, index_hinweis), 1)


@dataclass(frozen=True, slots=True)
class Sprung:
    """Ziel von Vor / Zurück: Folge, Track (Position ist immer 0) und Speichergrund."""

    datei: str
    index: int
    track: int
    grund: Literal["trackwechsel", "folgenende"]


def weiter(serie: Serie, art: Art, datei: str, index: int, track: int) -> Sprung | None:
    """``Weiter``: nächster Track; beim letzten Track Ziel ``serie`` -> nächste Folge,
    Ziel ``folge`` -> ``None`` (nur Hinweiston)."""
    if track + 1 < len(tracks_von(serie, datei)):
        return Sprung(datei, index, track + 1, "trackwechsel")
    if art == "folge" or not serie.folgen:
        return None
    nxt, nxt_index = springe(serie, aktueller_index(serie, datei, index), 1)
    return Sprung(nxt, nxt_index, 0, "folgenende")


def zurueck(datei: str, index: int, track: int, position_s: float) -> Sprung:
    """``Zurueck``: in den ersten ``ZURUECK_NEU_S`` s und mit vorigem Track -> voriger Track,
    sonst derselbe Track von vorn (auch im ersten Track)."""
    if position_s < ZURUECK_NEU_S - _EPS and track > 0:
        return Sprung(datei, index, track - 1, "trackwechsel")
    return Sprung(datei, index, track, "trackwechsel")


def unveraendert(
    alt: Zeiger | None, art: Art, datei: str, index: int | None, track: int, position_s: float
) -> bool:
    """Gleiche Art, Folge, Index, Track und abgerundete Position."""
    return (
        alt is not None
        and alt.art == art
        and alt.datei == datei
        and alt.index == index
        and alt.track == track
        and alt.position_s == abrunden(position_s)
    )


def stempel_faellig(alt: Zeiger | None, wall: float | None) -> bool:
    """Ein unveränderter Zeiger wird trotzdem geschrieben, wenn sein Zeitstempel fehlt oder veraltet ist
    (Entscheidung N, 09.11.). Bei unsicherer Uhr (``wall=None``) nie."""
    if alt is None or wall is None:
        return False
    return alt.benutzt_wall is None or wall - alt.benutzt_wall >= STEMPEL_ERNEUERN_S


def neuer_zeiger(
    alt: Zeiger | None,
    art: Art,
    serie_id: str,
    datei: str,
    index: int | None,
    track: int,
    position_s: float,
    wall: float | None = None,
) -> Zeiger:
    """Zeiger mit abgerundeter Position und um 1 erhöhtem Zähler.

    ``wall``: Wanduhr der Benutzung (nur bei sicherer Uhr). Ohne ``wall`` bleibt der alte Zeitstempel."""
    stempel = wall if wall is not None else (alt.benutzt_wall if alt else None)
    return Zeiger(art, serie_id, datei, index, track, abrunden(position_s), (alt.zaehler if alt else 0) + 1, stempel)


def lesezeichen_alter_s(zeiger: Zeiger | None, wall: float, zeit_ok: bool) -> float | None:
    """Alter des Lesezeichens in Sekunden; ``None`` bei unsicherer Uhr, ohne Zeiger oder ohne Zeitstempel."""
    if not zeit_ok or zeiger is None or zeiger.benutzt_wall is None:
        return None
    return wall - zeiger.benutzt_wall


def lesezeichen_abgelaufen(alter_s: float | None, tage: int) -> bool:
    """Länger als ``tage`` Tage nicht benutzt (genau an der Grenze: noch nicht); ``tage=0``: nie."""
    return alter_s is not None and tage > 0 and alter_s > tage * TAG_S


def periodisch_faellig(letzte_speicherung: float, jetzt_mono: float) -> bool:
    return jetzt_mono - letzte_speicherung >= SPEICHERN_PERIODISCH_S - _EPS
