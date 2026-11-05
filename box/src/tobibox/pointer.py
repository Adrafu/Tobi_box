"""Reine Zeigerregeln (``core-interface.md``, Abschnitt 6.3, und ``data-model.md``, 3).

Keine Ein-/Ausgabe, keine Uhr. ``session`` benutzt diese Funktionen; die
Bibliothek liefert ``Serie.folgen`` nur mit vorhandenen Dateien, deshalb ist
„fehlende Folge -> nächste vorhandene“ hier: die Folge, die jetzt am Platz
``Zeiger.index`` steht.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .events import Serie, Zeiger

RUECKSPRUNG_S = 3.0
SPEICHERN_PERIODISCH_S = 30.0

_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class Ort:
    """Wo eine Serie beim Auflegen weiterspielt."""

    datei: str
    index: int
    position_s: float
    folge_fehlte: bool = False


def abrunden(x: float) -> float:
    """Auf 1 Nachkommastelle abrunden (nie weiter vorn als die Wirklichkeit)."""
    return math.floor(x * 10 + _EPS) / 10 if x > 0 else 0.0


def ruecksprung(position_s: float) -> float:
    """Position nach dem Rücksprung von ``RUECKSPRUNG_S``; nie unter 0."""
    return max(0.0, position_s - RUECKSPRUNG_S)


def index_am_zeiger(serie: Serie, zeiger: Zeiger | None) -> int:
    """Index der Folge, auf die der Zeiger zeigt (Fallback: Hinweis ``index``, sonst 0)."""
    n = len(serie.folgen)
    if zeiger is None or n == 0:
        return 0
    if zeiger.datei in serie.folgen:
        return serie.folgen.index(zeiger.datei)
    return zeiger.index if 0 <= zeiger.index < n else 0


def ort_am_zeiger(serie: Serie, zeiger: Zeiger | None) -> Ort | None:
    """Start-Ort beim Auflegen; ``None`` bei leerer Serie."""
    folgen = serie.folgen
    if not folgen:
        return None
    if zeiger is None:
        return Ort(folgen[0], 0, 0.0)
    if zeiger.datei in folgen:
        return Ort(zeiger.datei, folgen.index(zeiger.datei), ruecksprung(zeiger.position_s))
    i = index_am_zeiger(serie, zeiger)
    return Ort(folgen[i], i, 0.0, True)


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


def unveraendert(alt: Zeiger | None, datei: str, index: int, position_s: float) -> bool:
    """Gleiche Datei, gleicher Index, gleiche abgerundete Position."""
    return (
        alt is not None
        and alt.datei == datei
        and alt.index == index
        and alt.position_s == abrunden(position_s)
    )


def neuer_zeiger(alt: Zeiger | None, serie_id: str, datei: str, index: int, position_s: float) -> Zeiger:
    """Zeiger mit abgerundeter Position und um 1 erhöhtem Zähler."""
    return Zeiger(serie_id, datei, index, abrunden(position_s), (alt.zaehler if alt else 0) + 1)


def periodisch_faellig(letzte_speicherung: float, jetzt_mono: float) -> bool:
    return jetzt_mono - letzte_speicherung >= SPEICHERN_PERIODISCH_S - _EPS
