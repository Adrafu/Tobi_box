"""Kapitel einer Folge (Paket A3b3; Vertrag W, 14.7; Design 11.4.8). Reine Funktionen ohne Dateizugriff.

Quellen, in dieser Reihenfolge:

1. **Eingebettete Kapitel** einer Datei (``ffprobe -show_chapters``: M4B-Kapitelspur, MP3 ID3v2 ``CHAP``).
2. Bei einer **Ordner-Folge** ist jeder Track ein Kapitel (Titel aus dem Tag ``title``, sonst Dateiname ohne Endung und ohne führende
   Nummer; Start = Summe der vorigen ``spuren_s``).
3. Sonst keine. Eine Liste gibt es nur bei **mindestens zwei** Kapiteln.

Auslegung des Vertrags bei Ordner-Folgen: Eingebettete Kapitel gewinnen **je Track**. Hat ein Track mindestens zwei eingebettete Kapitel, stehen
diese (mit ``track`` und dem Start in der Zeitleiste der ganzen Folge); sonst steht der Track als ein Kapitel. So geht bei einem Ordner aus
mehreren M4B-Dateien mit Kapiteln nichts verloren, und ein Ordner aus lauter MP3-Dateien ohne Kapitel bleibt „ein Track, ein Kapitel“.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .const import KAPITEL_MAX, KAPITEL_TITEL_MAX
from .namen import anzeigename, trenne_endung

#: führende Nummer samt Trenner: „01 “, „01 - “, „1. “, „03_“, „2) “
_FUEHRENDE_NUMMER = re.compile(r"^\s*\d+\s*(?:[-_.:)\]–—]+\s*)?")


@dataclass
class TrackInfo:
    """Was ``ffprobe`` zu einem Track geliefert hat."""

    name: str  # Dateiname (für den Titel, wenn der Tag fehlt)
    dauer_s: float
    codec: str | None = None
    titel: str = ""  # Tag ``title`` (schon normiert) oder ""
    kapitel: list[tuple[float, str]] = field(default_factory=list)  # eingebettete Kapitel: (start_s, titel)


def titel_aus_dateiname(name: str) -> str:
    """Dateiname ohne Endung und ohne führende Nummer (``"03 - Der Wald.mp3"`` -> ``"Der Wald"``); ``""``, wenn nichts bleibt."""
    stamm, _ = trenne_endung(name)
    return anzeigename(_FUEHRENDE_NUMMER.sub("", stamm, count=1), KAPITEL_TITEL_MAX)


def _eingebettet(roh: list[tuple[float, str]], ende_s: float | None) -> list[tuple[float, str]]:
    """Eingebettete Kapitel einer Datei: Start auf Tausendstel gerundet, nur gültige Starts (``0 <= start < ende_s``); **streng aufsteigend**:
    doppelte Startzeiten und Rückwärtssprünge (gegen den zuletzt behaltenen Start) fallen weg."""
    aus: list[tuple[float, str]] = []
    letzter = -1.0
    for start, titel in roh:
        start = round(float(start), 3)
        if start < 0 or (ende_s is not None and start >= ende_s):
            continue
        if start <= letzter:
            continue
        aus.append((start, titel))
        letzter = start
    return aus


def _fertig(eintraege: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Streng aufsteigend, höchstens ``KAPITEL_MAX``, Titel gekürzt; ohne Titel steht die laufende Nummer (die Seite zeigt „Kapitel 3“).
    Weniger als zwei Kapitel: keine Liste."""
    aus: list[dict[str, Any]] = []
    letzter = -1.0
    for e in eintraege:
        if e["start_s"] <= letzter:
            continue
        letzter = e["start_s"]
        aus.append(e)
        if len(aus) >= KAPITEL_MAX:
            break
    if len(aus) < 2:
        return []
    for nr, e in enumerate(aus, 1):
        e["titel"] = anzeigename(e["titel"], KAPITEL_TITEL_MAX) or str(nr)
    return aus


def baue_kapitel(tracks: list[TrackInfo], ordner: bool) -> list[dict[str, Any]]:
    """Die Kapitelliste einer Folge: ``[{"titel", "start_s", "track"?}]``. ``tracks`` in der Reihenfolge der Folge.

    ``ordner``: Ordner-Folge (mit Feld ``track``, 0-basiert); sonst eine einzelne Datei (nur eingebettete Kapitel)."""
    if not tracks:
        return []
    if not ordner:
        eing = _eingebettet(tracks[0].kapitel, tracks[0].dauer_s)
        return _fertig([{"titel": t, "start_s": s} for s, t in eing])
    eintraege: list[dict[str, Any]] = []
    versatz = 0
    for nr, t in enumerate(tracks):
        eing = _eingebettet(t.kapitel, t.dauer_s)
        if len(eing) >= 2:
            eintraege += [{"titel": titel, "start_s": round(versatz + s, 3), "track": nr} for s, titel in eing]
        else:
            eintraege.append({"titel": t.titel or titel_aus_dateiname(t.name), "start_s": versatz, "track": nr})
        versatz += int(round(t.dauer_s))  # wie ``spuren_s``: die Summe der gerundeten Längen
    return _fertig(eintraege)
