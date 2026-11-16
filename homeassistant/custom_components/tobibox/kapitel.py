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

from .const import KAPITEL_MAX, KAPITEL_ROH_MAX, KAPITEL_TITEL_MAX
from .namen import anzeigename, trenne_endung



@dataclass
class TrackInfo:
    """Was ``ffprobe`` zu einem Track geliefert hat."""

    name: str  # Dateiname (für den Titel, wenn der Tag fehlt)
    dauer_s: float
    codec: str | None = None
    titel: str = ""  # Tag ``title`` (schon normiert) oder ""
    kapitel: list[tuple[float, str]] = field(default_factory=list)  # eingebettete Kapitel: (start_s, titel)


def titel_aus_dateiname(name: str) -> str:
    """Dateiname ohne Endung, roh (``"03 - Der Wald.mp3"`` -> ``"03 - Der Wald"``); die Nummer fällt erst beim Ausgeben weg (``bereinige_titel``)."""
    stamm, _ = trenne_endung(name)
    return anzeigename(stamm, KAPITEL_ROH_MAX)


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
    """Streng aufsteigend, höchstens ``KAPITEL_MAX``; Titel **roh** (nur Steuerzeichen und Leerraum bereinigt, auf ``KAPITEL_ROH_MAX`` gekürzt),
    ohne Titel ``""`` (die Seite zeigt „Kapitel 3“). Bereinigt wird beim Ausgeben (``bereinige_titel``, AM22). Weniger als zwei Kapitel: keine Liste."""
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
    for e in aus:
        e["titel"] = anzeigename(e["titel"], KAPITEL_ROH_MAX)
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


# --------------------------------------------------------------------------
# Titel bereinigen beim Ausgeben (AM22)
# --------------------------------------------------------------------------

_TRENNER = re.compile(r"\s[-–—|]\s|:\s")
_GANZ_NUMMER = re.compile(r"\d{1,3}")
_NUMMER_TRENNER_TEXT = re.compile(r"(\d{1,3})\s*[-_.:)\]–—]+\s+(\S.*)$", re.S)
_ZAHL_VORN = re.compile(r"(\d{1,3})(?!\d)")
_TRENNER_NACH_NUMMER = re.compile(r"\s*([-_.:)\]–—]+)\s*")


def _ohne_fuehrende_nummer(t: str) -> str:
    """Eine führende Nummer (höchstens drei Ziffern) fällt nur weg, wenn ein Trenner folgt („01 - Intro“, „1. Teil“, „03_Wald“) oder die Nummer mit
    ``0`` beginnt und ein Leerzeichen folgt („01 Eins“); nie vor „%“, Ziffer oder ohne Trenner (``100% Wolf``, ``2019 Live``, ``1.1``, ``7 Zwerge``)."""
    m = _ZAHL_VORN.match(t)
    if not m:
        return t
    rest = t[m.end() :]
    s = _TRENNER_NACH_NUMMER.match(rest)
    if s:
        tail = rest[s.end() :]
        if tail and not tail[0].isdigit() and tail[0] != "%" and (s.group(0)[-1].isspace() or set(s.group(1)) & set("_-–—")):
            return tail.strip()
        return t
    if m.group(1).startswith("0") and len(m.group(1)) >= 2 and rest[:1].isspace() and rest.strip():
        return rest.strip()
    return t


def _gemeinsames_ende(titel: list[str]) -> str:
    s = titel[0]
    for t in titel[1:]:
        n = 0
        while n < min(len(s), len(t)) and s[-1 - n] == t[-1 - n]:
            n += 1
        s = s[len(s) - n :]
        if not s:
            break
    return s


def _ende_weg(titel: list[str]) -> list[str]:
    """Ein Ende, das alle Titel gemeinsam haben und das an einem Trenner beginnt („ - Serie“, „: Serie“), fällt weg. Ein Leerzeichen allein trennt nur,
    wenn davor in jedem Titel nur eine Nummer steht („01 Ela“, „02 Ela“). Es muss in jedem Titel etwas übrig bleiben."""
    if any(not t for t in titel):
        return titel
    s = _gemeinsames_ende(titel)
    if not s:
        return titel
    m = _TRENNER.search(s)
    if m:
        rest = [t[: len(t) - len(s) + m.start()].rstrip() for t in titel]
        if all(rest):
            return rest
        return titel
    m = re.search(r"\s", s)
    if m:
        rest = [t[: len(t) - len(s) + m.start()] for t in titel]
        if all(_GANZ_NUMMER.fullmatch(r) for r in rest):
            return rest
    return titel


def _anfang_weg(titel: list[str]) -> list[str]:
    """Ein Anfang, den alle Titel gemeinsam haben (an einer Wortgrenze), fällt nur weg, wenn danach in jedem Titel entweder nur eine Nummer („Kapitel 01“
    -> ``""``) oder „Nummer Trenner Text“ („Kapitel 01: Einführung“ -> „Einführung“) bleibt."""
    if any(not t for t in titel):
        return titel
    p = titel[0]
    for t in titel[1:]:
        n = 0
        while n < min(len(p), len(t)) and p[n] == t[n]:
            n += 1
        p = p[:n]
        if not p:
            return titel
    while p and p[-1].isalnum() and not all(len(t) == len(p) or not t[len(p)].isalnum() for t in titel):
        p = p[:-1]
    if not p:
        return titel
    aus: list[str] = []
    for t in titel:
        rest = t[len(p) :].strip()
        if _GANZ_NUMMER.fullmatch(rest):
            aus.append("")
            continue
        m = _NUMMER_TRENNER_TEXT.match(rest)
        if not m:
            return titel
        aus.append(m.group(2).strip())
    return aus


def bereinige_titel(titel: list[str]) -> list[str]:
    """Kapiteltitel einer Folge für die Ausgabe (AM22). Gleiche Länge und Reihenfolge; ``""`` heißt „die Seite zeigt Kapitel n“.

    1. Ein gemeinsames Ende an einem Trenner fällt weg, dann ein gemeinsamer Anfang (nur wenn danach eine Nummer bzw. Nummer, Trenner, Text bleibt).
    2. Eine führende Nummer fällt weg (``_ohne_fuehrende_nummer``); bleibt nur eine Nummer, ist der Titel ``""``.
    3. Ein Titel, der in der Folge mehrfach vorkommt, ist ``""``."""
    roh = [anzeigename(t, KAPITEL_ROH_MAX) for t in titel]
    if len(roh) < 2:
        neu = list(roh)
    else:
        neu = _anfang_weg(_ende_weg(roh))
    aus: list[str] = []
    for t in neu:
        t = _ohne_fuehrende_nummer(t.strip()).strip()
        aus.append("" if _GANZ_NUMMER.fullmatch(t) else t)
    zaehler: dict[str, int] = {}
    for t in aus:
        zaehler[t.casefold()] = zaehler.get(t.casefold(), 0) + 1
    return [anzeigename(t, KAPITEL_TITEL_MAX) if t and zaehler[t.casefold()] == 1 else "" for t in aus]


def bereinige_kapitel(kapitel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Kopie der Kapitelliste mit bereinigten Titeln (``serie/get``); der Store behält den Rohtitel."""
    neu = bereinige_titel([k["titel"] for k in kapitel])
    return [{**k, "titel": t} for k, t in zip(kapitel, neu)]
