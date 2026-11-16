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


# Wörter, die vor einer Nummer stehen und mit ihr zusammen „nur eine Nummer“ ergeben („Track #02“, „Kapitel 01“, „Teil 03“).
_NUMMERNWORT = r"(?:kapitel|track|titel|teil|lied|spur|folge|nr\.?|nummer|part|chapter)"
_NUR_NUMMER = re.compile(rf"(?:{_NUMMERNWORT}\s*#?\s*)?(\d{{1,3}})", re.I)
_NUMMERNWORT_ENDE = re.compile(rf"(?:^|(?<=\s[-–—|]\s)|(?<=:\s)){_NUMMERNWORT}\s*#?\s*", re.I)
_ZIFFERN_VORN = re.compile(r"\d{1,3}")


def _toleranz(n: int) -> int:
    """Wie viele Ausreißer (Intro, Titelsong, Lied …) ein gemeinsamer Anfang oder ein gemeinsames Ende vertragen (AM23): ein Fünftel der Titel,
    mindestens einer, höchstens fünf. Zusätzlich müssen **mindestens zwei** Titel den gemeinsamen Teil haben (``_mindestens``)."""
    return min(5, max(1, n // 5))


def _mindestens(n: int) -> int:
    return max(2, n - _toleranz(n))


def _ende_kandidaten(t: str) -> list[tuple[str, str]]:
    """Mögliche Enden eines Titels als ``(Ende, Art)``: ``"t"`` ab einem Trenner („ - Serie“, „: Serie“), ``"n"`` direkt nach einer führenden Nummer
    („1Trim-… .mp3“, „01 Ela“; das Ende muss mindestens drei Zeichen haben)."""
    aus = [(t[m.start() :], "t") for m in _TRENNER.finditer(t)]
    m = _ZIFFERN_VORN.match(t)
    if m and len(t) > m.end() and not t[m.end()].isdigit() and len(t[m.end() :].strip()) >= 3:
        aus.append((t[m.end() :], "n"))
    return aus


def _ende_weg(titel: list[str]) -> list[str]:
    """Ein Ende, das (fast) alle Titel gemeinsam haben, fällt weg. Es beginnt an einem Trenner („ - Serie“, „: Serie“) oder direkt hinter einer führenden
    Nummer (dann bleibt von jedem Titel nur diese Nummer). Es muss in jedem betroffenen Titel etwas übrig bleiben.

    Ausreißer (AM23): Haben es nur die meisten Titel (siehe ``_mindestens``), fällt es bei diesen weg; die anderen bleiben unverändert. Gewählt wird
    das Ende mit den meisten Titeln, bei Gleichstand das längste. Haben es alle, ist das Ergebnis wie in AM22."""
    n = len(titel)
    kand: dict[tuple[str, str], None] = {}
    for t in titel:
        for k in _ende_kandidaten(t):
            kand[k] = None
    beste: tuple[int, int, list[tuple[int, str]]] | None = None
    for ende, art in kand:
        treffer: list[tuple[int, str]] = []
        for i, t in enumerate(titel):
            if not t.endswith(ende) or len(t) == len(ende):
                continue
            kopf = t[: len(t) - len(ende)]
            if art == "t":
                kopf = kopf.rstrip()
                if kopf:
                    treffer.append((i, kopf))
            elif _GANZ_NUMMER.fullmatch(kopf):
                treffer.append((i, kopf))
        if len(treffer) >= _mindestens(n) and (beste is None or (len(treffer), len(ende)) > beste[:2]):
            beste = (len(treffer), len(ende), treffer)
    if beste is None:
        return titel
    aus = list(titel)
    for i, kopf in beste[2]:
        aus[i] = kopf
    return aus


def _rest_nach_anfang(rest: str) -> str | None:
    """Was nach einem gemeinsamen Anfang bleiben darf: nur eine Nummer (bleibt als Nummer stehen) oder „Nummer Trenner Text“ (der Text); sonst ``None``."""
    rest = rest.strip()
    if _GANZ_NUMMER.fullmatch(rest):
        return rest
    m = _NUMMER_TRENNER_TEXT.match(rest)
    return m.group(2).strip() if m else None


def _anfang_weg(titel: list[str]) -> list[str]:
    """Ein Anfang, den alle Titel gemeinsam haben (an einer Wortgrenze), fällt nur weg, wenn danach in jedem Titel entweder nur eine Nummer („Kapitel 01“
    -> ``"01"``) oder „Nummer Trenner Text“ („Kapitel 01: Einführung“ -> „Einführung“) bleibt. Die Nummer bleibt stehen, damit ``bereinige_titel`` sie
    als „Kapitel n“ ausgeben kann."""
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
        r = _rest_nach_anfang(t[len(p) :])
        if r is None:
            return titel
        aus.append(r)
    return aus


def _anfang_weg_ausreisser(titel: list[str]) -> list[str]:
    """Wie ``_anfang_weg``, aber mit Ausreißern (AM23). Weil ein Anfang wie „Alles vermurkst “ vor „1“ ein sprechender Titel sein kann, gilt das
    nur für Anfänge, die auf ein Nummernwort enden, das am Titelanfang oder hinter einem Trenner steht („Kapitel “, „Track #“, „… - Track #“, nicht „…, Teil “). Mindestens ``_mindestens`` Titel müssen den Anfang
    haben, und bei **allen** diesen muss danach nur eine Nummer oder „Nummer Trenner Text“ bleiben. Die Ausreißer bleiben unverändert."""
    n = len(titel)
    kand: set[str] = set()
    for t in titel:
        for m in _NUMMERNWORT_ENDE.finditer(t):
            if m.end() < len(t) and t[m.end()].isdigit():
                kand.add(t[: m.end()])
    geordnet = sorted(kand, key=lambda p: (sum(t.startswith(p) for t in titel), len(p)), reverse=True)
    for p in geordnet:
        mitglieder = [i for i, t in enumerate(titel) if t.startswith(p)]
        if len(mitglieder) < _mindestens(n):
            continue
        reste = [_rest_nach_anfang(titel[i][len(p) :]) for i in mitglieder]
        if any(r is None for r in reste):
            continue
        aus = list(titel)
        for i, r in zip(mitglieder, reste):
            aus[i] = r or ""
        return aus
    return titel


def _nummer(t: str) -> int | None:
    """Die Nummer, wenn der Titel nur eine Nummer ist („3“, „03“, „Track #02“, „Kapitel 01“, „Teil 03“), sonst ``None``."""
    m = _NUR_NUMMER.fullmatch(t)
    return int(m.group(1)) if m else None


def bereinige_titel(titel: list[str]) -> list[str]:
    """Kapiteltitel einer Folge für die Ausgabe (AM22, AM23). Gleiche Länge und Reihenfolge; ``""`` heißt „die Seite zeigt Kapitel <Position>“.

    1. Ein gemeinsames Ende fällt weg, dann ein gemeinsamer Anfang (nur wenn danach eine Nummer bzw. Nummer, Trenner, Text bleibt). Beides auch,
       wenn einzelne Ausreißer (Intro, Titelsong) es nicht haben: Schwelle ``_toleranz``/``_mindestens`` (höchstens ein Fünftel, mindestens
       einer, höchstens fünf Ausreißer; mindestens zwei Titel mit dem gemeinsamen Teil). Beim Anfang gilt das nur für Nummernwörter („Kapitel “,
       „Track #“), sonst wären „Alles vermurkst 1“, „Alles vermurkst 2“ in Gefahr. Lieber ein Fall zu wenig bereinigt als ein sprechender Titel kaputt.
    2. Eine führende Nummer fällt weg (``_ohne_fuehrende_nummer``).
    3. Ist ein Titel nur eine Nummer („Track #02“, „Kapitel 01“, „03“), zeigt er „Kapitel n“ mit der Nummer aus dem Titel ohne führende Null.
       Ist die Nummer gleich der Position (1-basiert), bleibt es ``""`` (gleiche Anzeige). Kommt dieselbe Nummer in der Folge mehrfach vor (zwei
       Alben im Ordner), ist **jede** reine Nummer ``""`` (Position); so gibt es nie zwei gleiche „Kapitel n“.
    4. Ein sprechender Titel, der in der Folge mehrfach vorkommt, ist ``""``."""
    roh = [anzeigename(t, KAPITEL_ROH_MAX) for t in titel]
    if len(roh) < 2:
        neu = list(roh)
    else:
        mitte = _ende_weg(roh)
        neu = _anfang_weg(mitte)
        if neu == mitte:
            neu = _anfang_weg_ausreisser(mitte)
        # Was ein Anfang als Text übrig ließ („Teil 3“ aus „Kapitel 03: Teil 3“), ist ein sprechender Titel, keine reine Nummer.
        text_aus_anfang = [a != b and not _GANZ_NUMMER.fullmatch(a) for a, b in zip(neu, mitte)]
    text: list[str | int] = []
    for t, geschuetzt in zip(neu, text_aus_anfang):
        t = t.strip()
        z = None if geschuetzt else _nummer(t)
        if z is None:
            t = _ohne_fuehrende_nummer(t).strip()
            z = _nummer(t) if not geschuetzt or _GANZ_NUMMER.fullmatch(t) else None
        text.append(t if z is None else z)
    nummern = [x for x in text if isinstance(x, int)]
    eindeutig = len(nummern) == len(set(nummern))
    zaehler: dict[str, int] = {}
    for x in text:
        if isinstance(x, str) and x:
            zaehler[x.casefold()] = zaehler.get(x.casefold(), 0) + 1
    aus: list[str] = []
    for pos, x in enumerate(text, 1):
        if isinstance(x, int):
            aus.append(f"Kapitel {x}" if eindeutig and x != pos else "")
        else:
            aus.append(anzeigename(x, KAPITEL_TITEL_MAX) if x and zaehler[x.casefold()] == 1 else "")
    return aus


def bereinige_kapitel(kapitel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Kopie der Kapitelliste mit bereinigten Titeln (``serie/get``); der Store behält den Rohtitel."""
    neu = bereinige_titel([k["titel"] for k in kapitel])
    return [{**k, "titel": t} for k, t in zip(kapitel, neu)]
