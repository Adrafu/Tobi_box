"""Lautstärke-Regel: wirksame Grenze = Minimum aller aktiven Grenzen.

Reine Funktionen, keine Ein-/Ausgabe (``core-interface.md``, Abschnitt 8).
Weitere Grenzen kommen ohne Änderung dieser Datei hinzu: ``grenzen`` ist eine
Liste benannter Werte, ``None`` heißt „nicht aktiv“.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

GRENZE_GLOBAL = "global"
GRENZE_LEISE_ZEIT = "leise_zeit"
GRENZE_KOPFHOERER = "kopfhoerer"
GRENZE_GUTE_NACHT = "gute_nacht"
GRENZE_AUSBLENDEN = "ausblenden"


def wirksame_grenze(grenzen: Mapping[str, int | None]) -> int:
    """Minimum aller Werte, die nicht ``None`` sind; ohne Werte 100."""
    werte = [w for w in grenzen.values() if w is not None]
    return min(werte) if werte else 100


def klemmen(wunsch: int, grenzen: Mapping[str, int | None]) -> int:
    """``min(wunsch, wirksame_grenze)``, nie unter 0."""
    return max(0, min(wunsch, wirksame_grenze(grenzen)))


def rampe(von: int, nach: int, start_mono: float, dauer_s: float, jetzt_mono: float) -> int:
    """Lineare Rampe von ``von`` nach ``nach``, auf ganze Prozent gerundet.

    Vor ``start_mono`` gilt ``von``, ab ``start_mono + dauer_s`` gilt ``nach``.
    """
    if dauer_s <= 0:
        return nach
    anteil = (jetzt_mono - start_mono) / dauer_s
    anteil = min(1.0, max(0.0, anteil))
    wert = von + (nach - von) * anteil
    rund = math.floor(wert + 0.5)
    return max(min(von, nach), min(max(von, nach), rund))
