"""Online-Suche: Abgleich (Design ``docs/designs/online-suche.md`` Abschnitt 4, Regelstand ``docs/egm/online-suche/os1_regeln.md``).

Alles hier ist **reine Funktion**: kein Netz, kein Home Assistant, keine Dateien, kein asyncio. Die Quellen holen andere
Module (``online_quellen.py``); dieses Modul bekommt schon geparste Daten und sagt je Feld, ob der Treffer ``sicher``,
``unsicher`` oder ``keiner`` ist und welcher neue Wert dazugehört. Alle Wortlisten und Schwellen stehen oben als
benannte Konstanten, damit man sie später ändern kann.

Es gilt nur die Vereinigung „Serie im Künstler **oder** im Albumnamen“ (Design 4.3). Den Namen eines Eintrags ändert die
Online-Suche nie automatisch (4.6, R6/R7); dafür gibt es hier keinen Code.

Datenformen
-----------

**Eintrag** (Eingabe von :func:`bewerte_eintrag`)::

    {
        "name": "Bibi Blocksberg",        # Serienname des Eintrags
        "einzeln": False,                 # Einzeltitel (Eintrag mit einer einzigen Geschichte)
        "cover_quelle": "auto" | "eigen" | None,   # heutiges Cover; "eigen" wird nie ersetzt
        "art_quelle": "geraten" | ...,    # nur "geraten" darf die Art ändern
        "folgen": [Folge, ...],
    }

**Folge**::

    {
        "anzeige": "Folge 100: Die große Hexenparty",   # heutiger Titel (ersatzweise "name")
        "nummer": 100 | None,                           # heutige Nummer
        "tracks": 13,                                   # Zahl der Titel (Dateien) der Folge
        "art": "datei" | "ordner",                      # nur zur Anzeige, nicht entscheidend
        "pruefen_gruende": ["tags_fehlen", ...],
    }

**Tonie-Index** (aus :func:`tonie_index_bauen`): ``{"eintraege": [...], "index": {wort: [eintrag, ...]}}``. Ein
Index-Eintrag hat ``model``, ``series``, ``episodes``, ``ep_nummer``, ``ep_rest``, ``tracks`` (Zahl), ``category``,
``release``, ``series_w``, ``zusatz`` (Sprachkurs-Reihe), ``art``, ``art_sicher``.

**Apple-Ergebnisse** (``apple_ergebnisse`` in :func:`bewerte_eintrag`): eine Liste mit **einem Element je Folge**. Jedes
Element ist die Liste der iTunes-Ergebnisse dieser Folge (dicts mit ``wrapperType``, ``collectionId``,
``collectionName``, ``artistName``, ``primaryGenreName``, ``trackCount``, ``releaseDate``, ``artworkUrl100``,
``description``; Stufe 1 und Stufe 2 schon zusammengelegt) oder ``None``, wenn die Antwort fehlt (nicht geholt).

**Shop-Daten** (``shop_daten``): ``{model: {"beschreibung": str | None, "alter_ab": int | None} | None}``, schon geprüft
(``salesId == model``, Text aus HTML, Alter eine ganze Zahl 0 bis 18). Fehlt ein ``model`` ganz, wurde die Seite noch
nicht geholt; steht dort ``None``, wurde sie geholt, ist aber unbrauchbar.

**Feldergebnis** (je Feld)::

    {"status": "sicher" | "unsicher" | "keiner" | "nicht_geholt", "neu": Wert | None, "quelle": {...} | None, ...}

``nicht_geholt`` heißt: Eine nötige Quelle fehlt noch (Apple-Antwort oder Shopseite), das Ergebnis ist nicht endgültig.
Der Cover-Wert ``neu`` ist die ``artworkUrl100`` (100 px); dazu steht ``collection_id`` im Ergebnis. Die Umrechnung auf
600 px macht ``online_quellen.py``.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence
from html.parser import HTMLParser
from typing import Any, Final

# --------------------------------------------------------------------------
# Konstanten (Regelstand OS1, ``os1_regeln.md`` Abschnitt 1)
# --------------------------------------------------------------------------

#: Füllwörter fallen weg (4.1)
FUELLWOERTER: Final = frozenset(
    {
        "am", "an", "and", "auf", "aus", "bei", "das", "dem", "den", "der", "des", "die", "ein", "eine", "einem",
        "einen", "einer", "eines", "es", "fuer", "im", "in", "ins", "ist", "mit", "oder", "of", "sich", "the",
        "und", "vom", "von", "zu", "zum", "zur",
    }
)  # fmt: skip
#: Allerweltswörter fallen weg (4.1)
ALLERWELTSWOERTER: Final = frozenset(
    {
        "band", "folge", "folgen", "hoerbuch", "hoerbuecher", "hoerspiel", "hoerspiele", "original", "teil",
        "ungekuerzt", "vol", "volume",
    }
)  # fmt: skip
#: Drei oder mehr gleiche Satzzeichen werden vor dem Zerlegen zu einem Wort (4.1, Nachtrag Projektleitung)
FOLGE_FRAGEZEICHEN: Final = "fragezeichen"
FOLGE_AUSRUFEZEICHEN: Final = "ausrufezeichen"

#: Ausschluss bei Apple-Alben (4.3), geprüft auf dem normalisierten Albumnamen: ganzes Wort
AUSSCHLUSS_TOKEN: Final = frozenset(
    {"alle", "best", "box", "bundle", "edition", "film", "kino", "komplett", "musical", "single"}
)
#: Ausschluss: Wortteil, irgendwo im normalisierten Namen
AUSSCHLUSS_TEILSTRING: Final = ("sammlung", "collection", "soundtrack", "jubilaeum", "edition", "komplett", "bundle")
#: Ausschluss: Zeichen im Original-Namen
AUSSCHLUSS_ZEICHEN: Final = ("/",)
#: Trackgrenze: ausgeschlossen, wenn mehr als ``TRACK_GRENZE_MIN`` Titel **und** mehr als das ``TRACK_GRENZE_FAKTOR``-Fache
#: der Trackzahl unserer Folge (mindestens 1 gerechnet)
TRACK_GRENZE_FAKTOR: Final = 2
TRACK_GRENZE_MIN: Final = 40

#: Seriennamen-Ähnlichkeit „Serie gestützt“ (4.2)
SERIE_STUETZE_MIN: Final = 0.85
#: Titel-Ähnlichkeit für „unsicher“ (4.2)
TITEL_AEHNLICH_MIN: Final = 0.92
#: Apple „unsicher“: Anteil der Wörter des Folgentitels im Album (4.3)
APPLE_UNSICHER_ANTEIL: Final = 0.80
#: Apple „unsicher“: höchstens so viele Zusatzwörter im Album (4.3)
APPLE_UNSICHER_EXTRA_MAX: Final = 2
#: „Eine Datei bei uns, drei und mehr Tracks beim Tonie“ ist nie sicher (4.2)
TONIE_DATEI_MIN_TRACKS: Final = 3

#: Shopseiten je Folge und Länge der Beschreibung (3.2, 4.9)
SHOP_SEITEN_MAX: Final = 2
BESCHREIBUNG_MAX: Final = 2000
TONIE_SHOP_PFAD: Final = "/de-de/tonies/"

#: Kandidaten je Quelle für den KI-Schritt (3.4) und ihre Mindest-Ähnlichkeit und Textlänge
KI_KANDIDATEN_MAX: Final = 3
KI_AEHNLICH_MIN: Final = 0.8
KI_TEXT_MAX: Final = 120

#: Sprachmerkmale der Tonie-Liste (3.1): fremde Zeichen (polnisch, türkisch, spanisch; bewusst eng: Café, Pokémon bleiben)
FREMDZEICHEN: Final = frozenset("¡¿ñąćęğıłńśşźż")
#: fremde Wörter (ganze Wörter, klein; „los“ bleibt deutsch benutzbar)
FREMDWOERTER: Final = frozenset(
    {
        "altre", "amigos", "avec", "aventures", "contes", "cuentos", "de", "dei", "del", "della", "en", "et", "gli",
        "histoires", "historias", "i", "il", "les", "mes", "muita", "nuevo", "nuova", "nuovo", "och", "otras",
        "petit", "pipsa", "possu", "racconti", "storie", "sus", "tarinoita", "trenino", "une",
    }
)  # fmt: skip
#: Sprachkurs-Reihen (Teilstring im normalisierten ``series``): nie sicher (4.2)
SPRACHKURS_MARKER: Final = (
    "englisch lernen",
    "english",
    "learn english",
    "learning english",
    "deutsch lernen",
    "franzoesisch lernen",
    "spanisch lernen",
)

#: Tonie-``category`` zu Art (4.7). ``None`` = keine Art; ``"unsicher:<art>"`` = höchstens unsicher.
TONIE_KATEGORIE_ART: Final[Mapping[str, str | None]] = {
    "audio-play": "hoerspiel",
    "audio-play-educational": "hoerspiel",
    "audio-book": "hoerbuch",
    "music": "musik",
    "Musik": "musik",
    "audio-play-songs": "unsicher:musik",
    "audio-book-songs": "unsicher:musik",
    "creative-tonie": None,
    "Hörspiele & Hörbücher": None,
}
#: Apple-Genre zu Art-Klasse (4.7): enthält ``hoerspiel`` → Hörspiel-Album; eines der Musikgenres → ``musik`` (nur unsicher)
APPLE_GENRE_HOERSPIEL: Final = ("hoerspiel",)
APPLE_GENRE_MUSIK: Final = (
    "kinderlieder", "kindermusik", "pop", "klassik", "rock", "schlager", "soundtrack", "filmmusik", "musical",
    "weihnachtsmusik", "kinder musik", "children", "world", "jazz", "dance", "hip-hop", "electronic", "singer",
    "folk", "country", "r&b", "alternative", "easy listening",
)  # fmt: skip
#: T4 (Tobias 18.11.): Steht dieses Wort im Albumnamen (normalisiert), ist die Art ``hoerspiel``, auch bei ``audiobook``
T4_HOERSPIEL_WORT: Final = "hoerspiel"

#: Platzhalter-Titel (4.5), auf dem normalisierten Titel ohne Beachtung der Groß-/Kleinschreibung. Das dritte Muster
#: („Track 01.mp3“) steht so in ``os1_regeln.md`` und in ``regeln.py``; sonstige Dateinamen mit Endung („Der Rabe.mp3“)
#: passen auf kein Muster und sind echte Titel.
PLATZHALTER_MUSTER: Final = (
    r"^(track|titel|kapitel|chapter|spur|audio|datei|file|folge|teil|kapitel)[\s_\-\.]*\d{1,3}$",
    r"^\d{1,3}$",
    r"^(track|titel|kapitel|spur|audio|datei)[\s_\-\.]*\d{1,3}\.(mp3|m4a|m4b|flac|ogg|wav|aac)$",
)
_PLATZHALTER_RE: Final = tuple(re.compile(p, re.I) for p in PLATZHALTER_MUSTER)

#: Prüfgründe, die eine Automatik zulassen (6.1)
GRUND_SERIE_NAME: Final = ("serie_aus_interpret", "serie_aus_ordner")
GRUND_FOLGE_TITEL: Final = ("tags_fehlen",)
GRUND_NUMMER: Final = ("tags_fehlen", "nummer_doppelt")

STATUS_SICHER: Final = "sicher"
STATUS_UNSICHER: Final = "unsicher"
STATUS_KEINER: Final = "keiner"
STATUS_NICHT_GEHOLT: Final = "nicht_geholt"


# --------------------------------------------------------------------------
# Wörter (4.1)
# --------------------------------------------------------------------------


def norm(text: Any) -> str:
    """Klein, ``ß`` zu ``ss``, ``ä ö ü`` zu ``ae oe ue``, Akzente weg."""
    t = (text if isinstance(text, str) else "").lower().replace("ß", "ss")
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue")):
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


_RE_FRAGEZEICHEN = re.compile(r"\?{3,}")
_RE_AUSRUFEZEICHEN = re.compile(r"!{3,}")


def woerter(text: str) -> list[str]:
    """Wortliste (4.1): „???“ zu ``fragezeichen``, „!!!“ zu ``ausrufezeichen``, dann klein, ``ss/ae/oe/ue``, Akzente weg,
    nur ``[a-z0-9]``-Folgen, ohne Füllwörter und Allerweltswörter. Einzelne Buchstaben fallen weg, einzelne Ziffern
    bleiben."""
    t = text if isinstance(text, str) else ""
    t = _RE_FRAGEZEICHEN.sub(f" {FOLGE_FRAGEZEICHEN} ", t)
    t = _RE_AUSRUFEZEICHEN.sub(f" {FOLGE_AUSRUFEZEICHEN} ", t)
    out: list[str] = []
    for w in re.findall(r"[a-z0-9]+", norm(t)):
        if len(w) == 1 and w.isalpha():
            continue
        if w in FUELLWOERTER or w in ALLERWELTSWOERTER:
            continue
        out.append(w)
    return out


def ohne_klammern(text: str) -> str:
    """Alle Klammerzusätze ``( … )`` und ``[ … ]`` weg (für Suchwörter)."""
    return re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", text or "").strip()


def klammern_ohne_zahl_weg(text: str) -> str:
    """Klammerzusätze ohne Ziffer fallen beim Titelvergleich weg („(Das Original-Hörspiel zur TV-Serie)“); mit Ziffer
    („(Teil 2)“, „(Neuauflage 2025)“) bleiben sie, dann gibt es meist keinen Treffer (Auslegung 2)."""
    return re.sub(r"\s*[\(\[][^\)\]\d]*[\)\]]", "", text or "").strip()


# --------------------------------------------------------------------------
# Nummern abtrennen (4.1)
# --------------------------------------------------------------------------

_RE_FOLGE = re.compile(r"^\s*(?:folge|teil|band|episode|nr\.?|vol\.?)\s*(\d{1,4})\b\s*[:.\-–—]?\s*(.*)$", re.I | re.S)
# Wie OS1 gemessen: nach „N:“ und „N.“ muss ein Leerzeichen folgen („3:Titel“ wird nicht abgetrennt).
_RE_ZAHL = re.compile(r"^\s*(\d{1,4})\s*[:.]\s+(.*)$", re.S)
_RE_PRAEFIX = re.compile(
    r"^(.{1,60}?)\s*[,\-–:]\s*(?:folge|teil|band)\s*(\d{1,4})\b\s*[:.\-–—]?\s*(\S.*)$", re.I | re.S
)


def nummer_abtrennen(text: str, serienwoerter: Collection[str] = ()) -> tuple[int | None, str]:
    """Eine vorn stehende Nummer abtrennen. Gibt ``(nummer | None, rest)``.

    Formen: „Folge N:“, „Folge N -“, „Teil N“, „Band N“, „Episode N“, „Nr. N“, „Vol. N“ (Zahl mit 1 bis 4 Ziffern, danach
    optional ``:``, ``.``, ``-``), „N:“ und „N. “ am Anfang; dazu „<Text>, Folge N: Rest“ (auch mit ``-``, ``–``, ``:``;
    Text höchstens 60 Zeichen; besteht der Text nur aus Serienwörtern, fällt er weg, sonst bleibt er im Rest). Es muss
    ein Rest folgen („Titel – Teil 1“ wird nicht zerlegt). Andere Zahlen im Text bleiben."""
    t = text if isinstance(text, str) else ""
    m = _RE_FOLGE.match(t)
    if m:
        return int(m.group(1)), m.group(2).strip()
    m = _RE_ZAHL.match(t)
    if m:
        return int(m.group(1)), m.group(2).strip()
    m = _RE_PRAEFIX.match(t)
    if m:
        pw = woerter(m.group(1))
        sw = set(serienwoerter)
        rest = m.group(3).strip()
        if pw and not all(w in sw for w in pw):
            rest = (m.group(1).strip() + " " + rest).strip()
        return int(m.group(2)), rest
    return None, t.strip()


def titel_woerter(text: str, serie_w: Collection[str]) -> tuple[int | None, tuple[str, ...], tuple[str, ...]]:
    """``(nummer, reduziert, voll)``: Klammern ohne Ziffer weg, Nummer abgetrennt; ``voll`` = alle Wörter,
    ``reduziert`` = ohne die Wörter des Seriennamens (2.3)."""
    n, rest = nummer_abtrennen(klammern_ohne_zahl_weg(text), serie_w)
    voll = tuple(woerter(rest))
    sw = set(serie_w)
    red = tuple(w for w in voll if w not in sw)
    return n, red, voll


def titel_gleich(a: str, b: str, serie_w: Collection[str]) -> bool:
    """Folgentitel genau gleich (2.3): Wortlisten nach Abzug der Serienwörter gleich und nicht leer, **oder** die vollen
    Wortlisten gleich (so bleiben Titel vergleichbar, die dem Seriennamen entsprechen)."""
    _, ra, fa = titel_woerter(a, serie_w)
    _, rb, fb = titel_woerter(b, serie_w)
    if ra and ra == rb:
        return True
    return bool(fa) and fa == fb


def aehnlichkeit(a: str, b: str, serie_w: Collection[str]) -> float:
    """``difflib.SequenceMatcher`` auf den mit Leerzeichen verbundenen Wörtern nach dem Abzug der Serienwörter; ist die
    Liste leer, gelten die vollen Wörter (Auslegung 1)."""
    _, ra, fa = titel_woerter(a, serie_w)
    _, rb, fb = titel_woerter(b, serie_w)
    x = ra or fa
    y = rb or fb
    if not x or not y:
        return 0.0
    return difflib.SequenceMatcher(None, " ".join(x), " ".join(y)).ratio()


def serie_aehnlichkeit(a: str, b: str) -> float:
    """Ähnlichkeit zweier Seriennamen (nur ``woerter``, ohne Abzug)."""
    x, y = woerter(a), woerter(b)
    if not x or not y:
        return 0.0
    return difflib.SequenceMatcher(None, " ".join(x), " ".join(y)).ratio()


def ist_platzhalter(anzeige: str) -> bool:
    """Leerer Titel oder Platzhalter-Titel („Track 01“, „Folge 3“, „Kapitel 1“, „7“, „track01.mp3“). Andere Dateinamen
    mit Endung („Der Rabe.mp3“) sind echte Titel und kein Platzhalter."""
    a = (anzeige if isinstance(anzeige, str) else "").strip()
    if not a:
        return True
    n = norm(a).strip()
    return any(p.match(n) for p in _PLATZHALTER_RE)


def kuerzen_text(t: Any, n: int = KI_TEXT_MAX) -> str | None:
    """Leerraum zusammenfassen und auf ``n`` Zeichen kürzen (mit „…“)."""
    if t is None:
        return None
    s = " ".join(str(t).split())
    return s if len(s) <= n else s[: n - 1] + "…"


# --------------------------------------------------------------------------
# Kontext einer Folge
# --------------------------------------------------------------------------


def folge_kontext(serie_name: str, folge: Mapping[str, Any], einzeln: bool = False, n_folgen: int = 1) -> dict[str, Any]:
    """Kontext einer Folge für die Regeln (Form: Abschnitt „Folge“ oben).

    ``nummer_bekannt`` ist die Nummer der Folge, sonst die aus der Anzeige abgetrennte (Auslegung 5)."""
    sw = woerter(serie_name)
    anzeige = folge.get("anzeige") or folge.get("name") or ""
    if not isinstance(anzeige, str):
        anzeige = ""
    nr_text, _ = nummer_abtrennen(anzeige, sw)
    nummer = folge.get("nummer")
    tracks = folge.get("tracks")
    return {
        "serie": serie_name,
        "serie_w": sw,
        "anzeige": anzeige,
        "name": folge.get("name"),
        "nummer": nummer,
        "nummer_text": nr_text,
        "nummer_bekannt": nummer if nummer is not None else nr_text,
        "tracks": tracks if isinstance(tracks, int) and not isinstance(tracks, bool) else 0,
        "gruende": list(folge.get("pruefen_gruende") or []),
        "platzhalter": ist_platzhalter(anzeige),
        "einzeln": einzeln,
        "n_folgen": n_folgen,
    }


# --------------------------------------------------------------------------
# Tonie-Liste (3.1, 4.2)
# --------------------------------------------------------------------------


def _text_feld(wert: Any, liste_erlaubt: bool = False) -> str | None:
    """Text eines Feldes der Tonie-Liste. Fehlt es (``None``), ist es leer; ein falscher Typ gibt ``None`` zurück."""
    if wert is None:
        return ""
    if isinstance(wert, str):
        return wert
    if liste_erlaubt and isinstance(wert, (list, tuple)) and all(isinstance(x, str) for x in wert):
        return " ".join(wert)
    return None


def _track_zahl(tracks: Any) -> int | None:
    """Trackzahl eines Tonies: Liste der Titel (Original und Auszug) oder schon eine Zahl. ``None`` bei falschem Typ."""
    if tracks is None:
        return 0
    if isinstance(tracks, bool):
        return None
    if isinstance(tracks, int):
        return tracks if tracks >= 0 else None
    if isinstance(tracks, (list, tuple)):
        return len(tracks)
    return None


def tonie_benutzbar(eintrag: Any) -> bool:
    """Benutzbar (3.1): ``language == "de-de"``, ``model`` gesetzt und kein Treffer in den Sprachmerkmalen
    (``FREMDZEICHEN``, ``FREMDWOERTER``, geprüft auf ``series``, ``episodes``, ``title``).

    Verträgt rohe Einträge: fehlende Felder und falsche Typen ergeben ``False``, nie eine Ausnahme. ``title`` und
    ``tracks`` dürfen eine Liste sein (Original) oder Text bzw. Zahl (reduziertes Format)."""
    try:
        if not isinstance(eintrag, Mapping):
            return False
        if eintrag.get("language") != "de-de":
            return False
        model = eintrag.get("model")
        if not isinstance(model, str) or not model.strip():
            return False
        teile = [
            _text_feld(eintrag.get("series")),
            _text_feld(eintrag.get("episodes")),
            _text_feld(eintrag.get("title"), liste_erlaubt=True),
        ]
        if any(t is None for t in teile):
            return False
        if _track_zahl(eintrag.get("tracks")) is None:
            return False
        txt = " ".join(t for t in teile if t).lower()
        if any(c in FREMDZEICHEN for c in txt):
            return False
        if set(re.findall(r"[a-zäöüß]+", txt)) & FREMDWOERTER:
            return False
        return True
    except Exception:  # noqa: BLE001  (rohe Daten: nie eine Ausnahme)
        return False


def ist_zusatzreihe(series: str) -> bool:
    """Sprachkurs-Reihe („Englisch lernen“ u. ä.): nie sicher."""
    n = norm(series)
    return any(m in n for m in SPRACHKURS_MARKER)


def tonie_art(category: Any) -> tuple[str | None, bool]:
    """Tonie-``category`` zu ``(art | None, sicher)`` (4.7). ``*-songs`` ergibt eine Art, aber nicht sicher; alles
    Unbekannte ergibt ``(None, False)``."""
    if not isinstance(category, str):
        return None, False
    v = TONIE_KATEGORIE_ART.get(category)
    if v is None:
        return None, False
    if v.startswith("unsicher:"):
        return v.split(":", 1)[1], False
    return v, True


def tonie_index_bauen(tonies: Iterable[Any]) -> dict[str, Any]:
    """Index nur der benutzbaren Tonies (Form: Abschnitt „Tonie-Index“ oben). Unbrauchbare Einträge werden übersprungen."""
    eintraege: list[dict[str, Any]] = []
    index: dict[str, list[dict[str, Any]]] = {}
    for t in tonies:
        if not tonie_benutzbar(t):
            continue
        series = t.get("series") or ""
        sw = woerter(series)
        ep = t.get("episodes") or ""
        nr, rest = nummer_abtrennen(ep, sw)
        e = {
            "model": t["model"],
            "series": series,
            "episodes": ep,
            "ep_nummer": nr,
            "ep_rest": rest,
            "tracks": _track_zahl(t.get("tracks")) or 0,
            "category": t.get("category"),
            "release": t.get("release"),
            "series_w": sw,
            "zusatz": ist_zusatzreihe(series),
        }
        e["art"], e["art_sicher"] = tonie_art(t.get("category"))
        eintraege.append(e)
        for w in set(sw) | set(woerter(rest)):
            index.setdefault(w, []).append(e)
    return {"eintraege": eintraege, "index": index}


def tonie_kandidaten(ctx: Mapping[str, Any], tonie_index: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Tonies, deren ``series``- oder Titelwörter mit den Wörtern unseres Seriennamens oder Folgentitels überlappen."""
    ws = set(ctx["serie_w"]) | set(woerter(nummer_abtrennen(ctx["anzeige"], ctx["serie_w"])[1]))
    gesehen: dict[str, dict[str, Any]] = {}
    for w in ws:
        for e in tonie_index["index"].get(w, []):
            gesehen[e["model"]] = e
    return list(gesehen.values())


def tonie_pruefen(
    ctx: Mapping[str, Any], tonie_index: Mapping[str, Any], sitemap_pfade: Collection[str] | None = None
) -> dict[str, Any]:
    """Tonie-Treffer einer Folge (4.2, 2.5).

    Ergebnis: ``status`` (``sicher``/``unsicher``/``keiner``), ``sichere`` und ``unsichere`` (Index-Einträge), ``art``,
    ``art_sicher``, ``nummer`` (abgetrennt aus ``episodes``), ``flags`` (``dublette_widerspruch``, ``dubletten:<models>``),
    ``shop_kandidaten`` (bei Dubletten nur der Kandidat mit gleicher Trackzahl größer 0; höchstens 2), ``rep`` (der
    erste Treffer) und ``shop_pfade`` (Liste ``(pfad, model)``, höchstens 2). Ohne ``sitemap_pfade`` ist der ``pfad``
    ``None`` (der Abgleich kennt dann keine Seiten und meldet keine fehlende Seite als „nicht geholt“, benutzt aber
    Shop-Daten, die zu einem Kandidaten vorliegen)."""
    sw = ctx["serie_w"]
    ours = ctx["tracks"]
    sichere: list[dict[str, Any]] = []
    unsichere: list[dict[str, Any]] = []
    for e in tonie_kandidaten(ctx, tonie_index):
        if not e["episodes"]:
            continue
        gleich = titel_gleich(ctx["anzeige"], e["episodes"], sw)
        aehnl = aehnlichkeit(ctx["anzeige"], e["episodes"], sw)
        if not gleich and aehnl < TITEL_AEHNLICH_MIN:
            continue
        tt = e["tracks"]
        tracks_gleich = tt == 0 or tt == ours
        datei_drei = ours == 1 and tt >= TONIE_DATEI_MIN_TRACKS
        stuetze = serie_aehnlichkeit(ctx["serie"], e["series"]) >= SERIE_STUETZE_MIN and not e["zusatz"]
        if gleich and stuetze and tracks_gleich and not datei_drei:
            sichere.append(e)
        elif (aehnl >= TITEL_AEHNLICH_MIN and tracks_gleich and tt > 0) or (gleich and not tracks_gleich):
            unsichere.append(e)
        elif gleich and tracks_gleich:
            unsichere.append(e)  # Titel gleich, aber Serie nicht gestützt
    res: dict[str, Any] = {"sichere": sichere, "unsichere": unsichere, "flags": []}
    status = STATUS_KEINER
    art: str | None = None
    art_sicher = False
    nummer: int | None = None
    if sichere:
        # Dubletten (Auslegung 7): nur Kandidaten mit einem Wert zählen; Widerspruch gibt „keiner“
        arts = {e["art"] for e in sichere if e["art"]}
        nrs = {e["ep_nummer"] for e in sichere if e["ep_nummer"] is not None}
        if len(arts) > 1 or len(nrs) > 1:
            res["flags"].append("dublette_widerspruch")
        else:
            status = STATUS_SICHER
            art = next(iter(arts)) if arts else None
            art_sicher = any(e["art_sicher"] for e in sichere if e["art"] == art) if art else False
            nummer = next(iter(nrs)) if nrs else None
        if len(sichere) > 1:
            res["flags"].append("dubletten:" + ",".join(e["model"] for e in sichere))
    elif unsichere:
        status = STATUS_UNSICHER
        arts = {e["art"] for e in unsichere if e["art"]}
        nrs = {e["ep_nummer"] for e in unsichere if e["ep_nummer"] is not None}
        art = next(iter(arts)) if len(arts) == 1 else None
        nummer = next(iter(nrs)) if len(nrs) == 1 else None
    res.update(status=status, art=art, art_sicher=art_sicher, nummer=nummer)
    # Shopseiten (3.2): bei Dubletten nur der Kandidat mit gleicher Trackzahl (größer 0), ein einzelner immer
    shop: list[dict[str, Any]] = []
    if status == STATUS_SICHER:
        shop = list(sichere) if len(sichere) == 1 else [e for e in sichere if e["tracks"] == ours and ours > 0]
    res["shop_kandidaten"] = shop[:SHOP_SEITEN_MAX]
    res["rep"] = (sichere or unsichere or [None])[0]
    pfade: list[tuple[str | None, str]] = []
    if sitemap_pfade is not None:
        for e in res["shop_kandidaten"]:
            for p in shop_pfade(e, sitemap_pfade):
                if (p, e["model"]) not in pfade:
                    pfade.append((p, e["model"]))
    else:
        # ohne Sitemap kennt der Abgleich keine Pfade; die Shop-Daten der Kandidaten zählen trotzdem
        pfade = [(None, e["model"]) for e in res["shop_kandidaten"]]
    res["shop_pfade"] = pfade[:SHOP_SEITEN_MAX]
    res["sitemap_bekannt"] = sitemap_pfade is not None
    return res


# --------------------------------------------------------------------------
# Shopseite (3.2): Pfade in der Sitemap finden
# --------------------------------------------------------------------------


def slug(text: str) -> str:
    """Slug wie auf ``tonies.com``: klein, ``ae/oe/ue/ss``, alles andere ``-``."""
    return re.sub(r"[^a-z0-9]+", "-", norm(text)).strip("-")


def shop_pfade(tonie: Mapping[str, Any], sitemap_pfade: Collection[str]) -> list[str]:
    """Pfade ``/de-de/tonies/<serie-slug>/<folge-slug>/`` zu einem Tonie (Index-Eintrag) aus den Pfaden der Sitemap.

    Slug aus ``series`` und ``episodes`` (auch ``episodes`` ohne Nummer); erst genau, dann als Endung; höchstens
    ``SHOP_SEITEN_MAX`` (2) Pfade."""
    ss = slug(tonie.get("series") or "")
    varianten: list[str] = []
    for txt in (tonie.get("episodes"), tonie.get("ep_rest")):
        s = slug(txt or "")
        if s and s not in varianten:
            varianten.append(s)
    treffer: list[str] = []
    for v in varianten:
        p = f"{TONIE_SHOP_PFAD}{ss}/{v}/"
        if p in sitemap_pfade and p not in treffer:
            treffer.append(p)
    if not treffer:
        for v in varianten:
            for p in sorted(sitemap_pfade):
                if p.startswith(f"{TONIE_SHOP_PFAD}{ss}/") and p.rstrip("/").endswith(v) and p not in treffer:
                    treffer.append(p)
    return treffer[:SHOP_SEITEN_MAX]


class _TextSammler(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.teile: list[str] = []

    def handle_data(self, data: str) -> None:
        self.teile.append(data)

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in ("p", "br", "li", "div", "h1", "h2", "h3", "h4"):
            self.teile.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("p", "li", "div", "h1", "h2", "h3", "h4"):
            self.teile.append("\n")


def html_zu_text(h: Any, maxlen: int = BESCHREIBUNG_MAX) -> str:
    """Text aus einer Beschreibung (HTML oder schon Text). Für Apples Hörbuch-Beschreibung (4.9, Fall 2); Absätze
    bleiben, höchstens ``maxlen`` Zeichen. Shop-Texte sind schon geprüft und kommen als Text an."""
    p = _TextSammler()
    try:
        p.feed(h if isinstance(h, str) else "")
        p.close()
    except Exception:  # noqa: BLE001
        return ""
    t = "".join(p.teile)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    t = "".join(c for c in t if c == "\n" or (ord(c) >= 32 and ord(c) != 127))
    return t[:maxlen]


# --------------------------------------------------------------------------
# Apple (3.3, 4.3)
# --------------------------------------------------------------------------


def _kuerzen_suche(t: str, n: int = 100) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= n:
        return t
    return t[:n].rsplit(" ", 1)[0] if " " in t[:n] else t[:n]


def apple_suchwoerter(ctx: Mapping[str, Any]) -> tuple[str | None, str]:
    """Suchwörter der zwei Stufen (3.3, Auslegung 11): ``(stufe1 | None, stufe2)``.

    Stufe 1: Serienname + Folgentitel (ohne Nummer und Klammern, Serienname nicht doppeln, höchstens 100 Zeichen).
    Platzhalter-Titel und Titel gleich Serienname geben ``None`` (gleich zu Stufe 2). Stufe 2: nur der Serienname (je
    Eintrag einmal), wenn Stufe 1 weder sicher noch unsicher traf (siehe :func:`apple_hat_treffer`)."""
    serie = ohne_klammern(ctx["serie"])
    s2 = _kuerzen_suche(serie)
    if ctx["platzhalter"]:
        return None, s2
    _, rest = nummer_abtrennen(ohne_klammern(ctx["anzeige"]), ctx["serie_w"])
    rest = rest.strip()
    if not rest:
        return None, s2
    sw = ctx["serie_w"]
    t1 = rest if sw and set(sw) <= set(woerter(rest)) else serie + " " + rest
    t1 = _kuerzen_suche(t1)
    # Wie OS1 gemessen: „Titel gleich Serienname“ ist ein Vergleich der Zeichenketten („Bibi und Tina“ gegen „Bibi & Tina“
    # ergibt zwei Anfragen).
    if t1 == s2:
        return None, s2
    return t1, s2


def genre_klasse(r: Mapping[str, Any]) -> str:
    """Klasse eines Apple-Treffers: ``hoerbuch`` (``wrapperType = audiobook``), ``hoerspiel`` (Genre enthält Hörspiel),
    ``musik`` (nur unsicher) oder ``sonst``."""
    if r.get("wrapperType") == "audiobook":
        return "hoerbuch"
    g = norm(r.get("primaryGenreName") or "")
    if any(x in g for x in APPLE_GENRE_HOERSPIEL):
        return "hoerspiel"
    if any(x in g for x in APPLE_GENRE_MUSIK):
        return "musik"
    return "sonst"


def name_hat_hoerspiel(name: Any) -> bool:
    """T4: Steht ``hoerspiel`` als Wort im (normalisierten) Albumnamen? Geprüft auf den Wörtern **vor** dem Entfernen der
    Allerweltswörter, denn ``woerter`` wirft ``hoerspiel`` weg."""
    return T4_HOERSPIEL_WORT in re.findall(r"[a-z0-9]+", norm(name))


def apple_art(r: Mapping[str, Any]) -> str | None:
    """Art, die ein Apple-Treffer liefert (4.7): Klasse ``hoerspiel``/``hoerbuch``/``musik``, sonst ``None``. T4: Ein
    Hörbuch-Typ mit ``hoerspiel`` im Albumnamen ergibt ``hoerspiel``."""
    k = genre_klasse(r)
    if k == "hoerbuch" and name_hat_hoerspiel(r.get("collectionName")):
        return "hoerspiel"
    return k if k in ("hoerspiel", "hoerbuch", "musik") else None


def apple_ausschluss(name: Any, track_count: Any, folge_tracks: Any) -> str | None:
    """Ausschluss vorab (4.3): Grund oder ``None``. Ganzes Wort (``AUSSCHLUSS_TOKEN``), Wortteil
    (``AUSSCHLUSS_TEILSTRING``), „/“ im Namen, oder mehr als 40 Titel und mehr als das Doppelte der Folgen-Trackzahl
    (mindestens 1 gerechnet; bei Reihen-Alben die Summe der Tracks des Eintrags)."""
    name = name if isinstance(name, str) else ""
    n = norm(name)
    toks = set(re.findall(r"[a-z0-9]+", n))
    if toks & AUSSCHLUSS_TOKEN:
        return "wort:" + sorted(toks & AUSSCHLUSS_TOKEN)[0]
    for s in AUSSCHLUSS_TEILSTRING:
        if s in n:
            return "wort:" + s
    for z in AUSSCHLUSS_ZEICHEN:
        if z in name:
            return "zeichen:" + z
    tc = track_count if isinstance(track_count, int) and not isinstance(track_count, bool) else 0
    ft = folge_tracks if isinstance(folge_tracks, int) and not isinstance(folge_tracks, bool) else 0
    if tc > TRACK_GRENZE_MIN and tc > TRACK_GRENZE_FAKTOR * max(ft, 1):
        return f"tracks:{tc}"
    return None


def _unsicher_passt(titel: str, name: str, serie_w: Collection[str]) -> bool:
    """Apple „unsicher“ (4.3): mindestens 80 % der Wörter des Folgentitels im Album, höchstens zwei Zusatzwörter, keine
    zusätzliche Zahl (nach Abtrennen der Nummer und Abzug der Serienwörter)."""
    _, ra, fa = titel_woerter(titel, serie_w)
    _, rb, fb = titel_woerter(name, serie_w)
    a = list(ra or fa)
    b = list(rb or fb)
    if not a or not b:
        return False
    sb = set(b)
    treffer = sum(1 for w in a if w in sb)
    if treffer / len(a) < APPLE_UNSICHER_ANTEIL:
        return False
    sa = set(a)
    extra = [w for w in b if w not in sa]
    if len(extra) > APPLE_UNSICHER_EXTRA_MAX:
        return False
    return not any(w.isdigit() for w in extra)


def apple_bewerten(ctx: Mapping[str, Any], results: Iterable[Any]) -> dict[str, list[dict[str, Any]]]:
    """Bewertet die Apple-Ergebnisse einer Folge (4.3, Vereinigung „Serie im Künstler oder im Album“).

    Gibt ``{"sichere_alben": [...], "sichere_buecher": [...], "unsichere": [...]}``. Ein Eintrag hat ``typ`` (``album``
    oder ``hoerbuch``), ``album``, ``kuenstler``, ``genre``, ``tracks``, ``bild`` (100 px), ``collectionId``, ``klasse``,
    ``art`` (mit T4), ``nummer`` (aus dem Albumnamen), ``nummer_stuetze`` (T2: darf eine Nummer liefern),
    ``beschreibung``, ``fassung`` (``A``/``B``/``AB``) und bei „unsicher“ den ``grund``."""
    sw = ctx["serie_w"]
    ssw = set(sw)
    sichere_alben: list[dict[str, Any]] = []
    sichere_buecher: list[dict[str, Any]] = []
    unsichere: list[dict[str, Any]] = []
    voll_unser = Counter(titel_woerter(ctx["anzeige"], sw)[2])
    for r in results:
        if not isinstance(r, Mapping) or r.get("wrapperType") not in ("collection", "audiobook"):
            continue
        name = r.get("collectionName") or ""
        if not isinstance(name, str):
            continue
        wa = set(woerter(r.get("artistName") or ""))
        wn = set(woerter(name))
        in_a = bool(ssw) and ssw <= wa
        in_b = bool(ssw) and ssw <= wn
        passt = in_a or in_b
        if apple_ausschluss(name, r.get("trackCount"), ctx["tracks"]):
            continue
        klasse = genre_klasse(r)
        nr_album, _, _ = titel_woerter(name, sw)
        gleich = titel_gleich(ctx["anzeige"], name, sw)
        # Nummernkonflikt: bekannte Nummer und Nummer des Albums verschieden -> höchstens unsicher
        bek = ctx["nummer_bekannt"]
        nr_konflikt = bek is not None and nr_album is not None and bek != nr_album
        # T2: Die Nummer stützt A (Reihe im Künstler) oder B (Serienwörter im Albumnamen außerhalb des Teils, der unserem
        # Folgentitel entspricht; enthält unser Titel alle Serienwörter, stützt B nie)
        b_aus = bool(ssw) and not (ssw <= set(voll_unser)) and ssw <= set((Counter(woerter(name)) - voll_unser).elements())
        eintrag = {
            "nummer_stuetze": in_a or b_aus,
            "typ": "hoerbuch" if r.get("wrapperType") == "audiobook" else "album",
            "album": name,
            "kuenstler": r.get("artistName"),
            "genre": r.get("primaryGenreName"),
            "tracks": r.get("trackCount"),
            "bild": r.get("artworkUrl100"),
            "collectionId": r.get("collectionId"),
            "klasse": klasse,
            "art": apple_art(r),
            "nummer": nr_album,
            "beschreibung": r.get("description"),
            "fassung": "".join(k for k, v in (("A", in_a), ("B", in_b)) if v),
        }
        if passt and gleich and not nr_konflikt:
            if klasse == "hoerspiel" and eintrag["typ"] == "album":
                sichere_alben.append(eintrag)
                continue
            if klasse == "hoerbuch":
                sichere_buecher.append(eintrag)
                continue
            unsichere.append(dict(eintrag, grund="genre:" + str(r.get("primaryGenreName"))))
        elif passt and (gleich or _unsicher_passt(ctx["anzeige"], name, sw)):
            unsichere.append(dict(eintrag, grund="nummer" if nr_konflikt else "aehnlich"))
    return {"sichere_alben": sichere_alben, "sichere_buecher": sichere_buecher, "unsichere": unsichere}


def apple_hat_treffer(ctx: Mapping[str, Any], results: Iterable[Any]) -> bool:
    """Für Stufe 2 (3.3): Stufe 1 hatte einen Treffer, wenn es einen sicheren oder unsicheren gibt."""
    b = apple_bewerten(ctx, results)
    return bool(b["sichere_alben"] or b["sichere_buecher"] or b["unsichere"])


def apple_entdoppeln(results: Iterable[Any]) -> list[dict[str, Any]]:
    """Ergebnisse mehrerer Anfragen zusammenlegen, gleiche Treffer (``wrapperType``, ``collectionId``, ``trackId``) nur einmal."""
    gesehen: set[tuple[Any, Any, Any]] = set()
    out: list[dict[str, Any]] = []
    for r in results:
        if not isinstance(r, Mapping):
            continue
        k = (r.get("wrapperType"), r.get("collectionId"), r.get("trackId"))
        if k in gesehen:
            continue
        gesehen.add(k)
        out.append(dict(r))
    return out


def reihen_alben(serie_name: str, pool: Iterable[Any], summe_tracks: int) -> list[dict[str, Any]]:
    """Reihen-Album (4.3): ein Album, dessen Name (nach ``woerter``) genau dem Seriennamen entspricht, Genre Hörspiele,
    nicht ausgeschlossen. Je ``collectionId`` höchstens eines. ``summe_tracks`` = Summe der Tracks des Eintrags."""
    sw = woerter(serie_name)
    out: dict[Any, dict[str, Any]] = {}
    if not sw:
        return []
    for r in pool:
        if not isinstance(r, Mapping) or r.get("wrapperType") != "collection":
            continue
        name = r.get("collectionName") or ""
        if not isinstance(name, str) or woerter(name) != sw:
            continue
        if apple_ausschluss(name, r.get("trackCount"), summe_tracks):
            continue
        if genre_klasse(r) != "hoerspiel":
            continue
        in_a = set(sw) <= set(woerter(r.get("artistName") or ""))
        out[r.get("collectionId")] = {
            "typ": "album",
            "album": name,
            "kuenstler": r.get("artistName"),
            "genre": r.get("primaryGenreName"),
            "tracks": r.get("trackCount"),
            "bild": r.get("artworkUrl100"),
            "collectionId": r.get("collectionId"),
            "klasse": "hoerspiel",
            "fassung": "A" if in_a else "B",
            "reihe": True,
        }
    return list(out.values())


# --------------------------------------------------------------------------
# Folgentitel (4.5, T1)
# --------------------------------------------------------------------------

_RE_NR_PRAEFIX = re.compile(r"^\s*(?:(?:folge|episode)\s*)?(\d{1,4})\s*(?:[:._]|\s[-–—])\s*(\S.*)$", re.I | re.S)
_RE_ENDE_HOERSPIEL = re.compile(
    r"\s*[.\-–:,]?\s*(?:das\s+|ein\s+)?(?:original[\s-]*)?h(?:ö|oe)rspiel(?:\s+(?:zu|zum|zur|nach)\b.*)?\s*$",
    re.I | re.S,
)
_RE_TEIL_VORN = re.compile(r"^\s*(?:teil|band)\s*(\d{1,4})\s*(?::|\s[-–—])\s*\S", re.I)
_RE_TEIL_ENDE = re.compile(r"\S\s*[-–—]\s*(?:teil|band)\s*(\d{1,4})\s*$", re.I)


def teil_band_nummer(anzeige: str) -> int | None:
    """Nummer N, wenn der Titel „Teil N“ oder „Band N“ vorn (mit ``:`` oder `` - ``) oder am Ende (nach ``-``/``–``/``—``) trägt."""
    m = _RE_TEIL_VORN.match(anzeige or "") or _RE_TEIL_ENDE.search(anzeige or "")
    return int(m.group(1)) if m else None


def titel_neu_bekannt(anzeige: str, nummer: int | None) -> str:
    """Neuer Titel im Normalfall (T1): der heutige Titel Wort für Wort, davor „Folge N: “ bei bekannter Nummer. Ein
    vorhandenes Nummernpräfix („Folge 121:“, „121_“, „03_“, „3 - “) wird vereinheitlicht, nicht verdoppelt. Ohne Nummer,
    bei „Teil N“/„Band N“ im Titel und bei „<Text>, Folge N: …“ bleibt der Titel unverändert."""
    a = (anzeige or "").strip()
    if nummer is None or teil_band_nummer(a) is not None:
        return a
    m = _RE_NR_PRAEFIX.match(a)
    if not m and re.search(r"\b(?:folge|episode)\s*\d{1,4}\s*[:.\-–—]", a, re.I):
        return a  # „<Text>, Folge 15: Titel“: die Nummer steht schon im Titel
    rest = m.group(2).strip() if m else a
    return f"Folge {nummer}: {rest}"


def titel_neu(ctx: Mapping[str, Any], apple_eintrag: Mapping[str, Any], nummer: int | None) -> str:
    """Neuer Titel nur bei Platzhaltern (T1, 4.5 Fall 2): Apples Albumtitel, Klammerzusätze ohne Ziffer und „. Das
    Hörspiel“ u. ä. am Ende weg; der Serienname vorn fällt nur weg, wenn danach ein Trennzeichen (`` - ``, ``: ``,
    ``. ``, ``, ``) kommt; davor „Folge N: “ bei bekannter Nummer."""
    _, rest = nummer_abtrennen(klammern_ohne_zahl_weg(apple_eintrag["album"]), ctx["serie_w"])
    rest = rest.strip()
    rest = _RE_ENDE_HOERSPIEL.sub("", rest).strip() or rest
    teile = [t.strip() for t in (ctx["serie"] or "").split(" - ") if t.strip()]
    kandidaten = [ctx["serie"] or ""]
    for i in range(len(teile)):
        kandidaten.append(" - ".join(teile[i:]))
        kandidaten.append(" ".join(teile[i:]))
    for k in sorted({k for k in kandidaten if k.strip()}, key=len, reverse=True):
        mm = re.match(r"^\s*" + re.escape(k) + r"(?:\s+-\s+|\s+–\s+|:\s+|\.\s+|,\s+)(\S.*)$", rest, re.I | re.S)
        if mm:
            rest = mm.group(1).strip()
            break
    return f"Folge {nummer}: {rest}" if nummer is not None else rest


def mehrheit(werte: Sequence[Any], gesamt: int) -> Any:
    """Art des Eintrags (4.7): Mehrheit (mehr als 50 %) der Folgen mit sicherer Art, mindestens die Hälfte aller Folgen."""
    if not werte or len(werte) * 2 < gesamt:
        return None
    w, n = Counter(werte).most_common(1)[0]
    return w if n * 2 > len(werte) else None


# --------------------------------------------------------------------------
# Kandidaten für den KI-Schritt (3.4)
# --------------------------------------------------------------------------


def ki_kandidaten(
    ctx: Mapping[str, Any], tonie_index: Mapping[str, Any], apple_ergebnisse: Iterable[Any] | None
) -> dict[str, list[dict[str, Any]]]:
    """Bis zu 3 Kandidaten je Quelle für eine Folge (3.4), sortiert nach „Titel gleich“, gleicher Trackzahl bzw. Typ und
    Ähnlichkeit. Tonies: ``series``, ``episodes``, ``tracks``, ``category``. Apple: ``collectionName``, ``artistName``,
    ``genre``, ``trackCount``, ``wrapperType``. Keine Bibliotheks-IDs, keine Tobie-Namen. Texte auf 120 Zeichen gekürzt."""
    sw = ctx["serie_w"]
    tonies: list[tuple[Any, ...]] = []
    gesehen_t: set[tuple[str, str]] = set()
    for t in tonie_kandidaten(ctx, tonie_index):
        if not t["episodes"]:
            continue
        gleich = titel_gleich(ctx["anzeige"], t["episodes"], sw)
        a = aehnlichkeit(ctx["anzeige"], t["episodes"], sw)
        if not gleich and a < KI_AEHNLICH_MIN:
            continue
        k = (t["series"], t["episodes"])
        if k in gesehen_t:
            continue
        gesehen_t.add(k)
        tonies.append((0 if gleich else 1, 0 if t["tracks"] == ctx["tracks"] else 1, -a, t["model"], t))
    tonies.sort(key=lambda x: x[:4])
    apple: list[tuple[Any, ...]] = []
    gesehen_a: set[Any] = set()
    for r in apple_ergebnisse or ():
        if not isinstance(r, Mapping) or r.get("wrapperType") not in ("collection", "audiobook"):
            continue
        name = r.get("collectionName") or ""
        if not isinstance(name, str) or apple_ausschluss(name, r.get("trackCount"), ctx["tracks"]):
            continue
        gleich = titel_gleich(ctx["anzeige"], name, sw)
        a = aehnlichkeit(ctx["anzeige"], name, sw)
        if not gleich and a < KI_AEHNLICH_MIN:
            continue
        cid = r.get("collectionId")
        if cid in gesehen_a:
            continue
        gesehen_a.add(cid)
        apple.append(
            (
                0 if gleich else 1,
                0 if r.get("wrapperType") == "collection" else 1,
                0 if genre_klasse(r) == "hoerspiel" else 1,
                -a,
                str(cid),
                r,
            )
        )
    apple.sort(key=lambda x: x[:5])
    return {
        "tonies": [
            {
                "series": kuerzen_text(t["series"]),
                "episodes": kuerzen_text(t["episodes"]),
                "tracks": t["tracks"],
                "category": t["category"],
            }
            for *_, t in tonies[:KI_KANDIDATEN_MAX]
        ],
        "apple": [
            {
                "collectionName": kuerzen_text(r.get("collectionName")),
                "artistName": kuerzen_text(r.get("artistName")),
                "genre": r.get("primaryGenreName"),
                "trackCount": r.get("trackCount"),
                "wrapperType": r.get("wrapperType"),
            }
            for *_, r in apple[:KI_KANDIDATEN_MAX]
        ],
    }


# --------------------------------------------------------------------------
# Felder je Folge (4.4, 4.5, 4.7, 4.9)
# --------------------------------------------------------------------------


def _feld(status: str, neu: Any = None, quelle: Any = None, **extra: Any) -> dict[str, Any]:
    return {"status": status, "neu": neu, "quelle": quelle, **extra}


def _apple_quelle(x: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "typ": "apple_" + x["typ"],
        "collectionId": x.get("collectionId"),
        "album": x.get("album"),
        "kuenstler": x.get("kuenstler"),
        "genre": x.get("genre"),
    }


def _tonie_quelle(rep: Mapping[str, Any] | None) -> dict[str, Any]:
    return {"typ": "tonies", "model": rep["model"] if rep else None}


def _alter_gueltig(alter: Any) -> int | None:
    if isinstance(alter, bool) or not isinstance(alter, int) or not 0 <= alter <= 18:
        return None
    return alter


def _shop_info(
    tp: Mapping[str, Any], shop_daten: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, bool]:
    """Erste brauchbare Shopseite der Kandidaten. ``(daten | None, ausstehend)``; ausstehend = eine nötige Seite fehlt noch."""
    offen = False
    for _pfad, model in tp.get("shop_pfade", ()):
        if model not in shop_daten:
            offen = offen or bool(tp.get("sitemap_bekannt"))
            continue
        daten = shop_daten[model]
        if isinstance(daten, Mapping):
            return {"model": model, **daten}, False
    return None, offen


def bewerte_folge(
    ctx: Mapping[str, Any],
    res: Sequence[Any] | None,
    tp: Mapping[str, Any],
    shop_daten: Mapping[str, Any],
) -> dict[str, Any]:
    """Alle Felder einer Folge. ``res`` = Apple-Ergebnisse der Folge (``None`` = nicht geholt), ``tp`` = Ergebnis von
    :func:`tonie_pruefen`. Gibt ``{"cover", "art", "folge_titel", "nummer", "beschreibung", "alter_ab", "apple"}``."""
    ab = (
        apple_bewerten(ctx, res)
        if res is not None
        else {"sichere_alben": [], "sichere_buecher": [], "unsichere": []}
    )
    alben = ab["sichere_alben"]
    buecher = ab["sichere_buecher"]
    uns = ab["unsichere"]
    sicher_apple = alben + buecher
    f: dict[str, Any] = {}

    # --- Nummer (4.4, T2)
    nr_s: set[int] = set()
    nr_typen: list[str] = []
    if tp["status"] == STATUS_SICHER and tp["nummer"] is not None:
        nr_s.add(tp["nummer"])
        nr_typen.append("tonies")
    for x in sicher_apple:
        if x["nummer"] is not None and x["nummer_stuetze"]:
            nr_s.add(x["nummer"])
            if "apple" not in nr_typen:
                nr_typen.append("apple")
    if len(nr_s) == 1:
        f["nummer"] = _feld(STATUS_SICHER, next(iter(nr_s)), {"typ": "+".join(nr_typen)})
    elif len(nr_s) > 1:
        f["nummer"] = _feld(STATUS_UNSICHER, None, None, grund="widerspruch")
    else:
        un = {x["nummer"] for x in uns if x["nummer"] is not None and x["nummer_stuetze"]}
        if tp["status"] == STATUS_UNSICHER and tp["nummer"] is not None:
            un.add(tp["nummer"])
        if len(un) == 1:
            f["nummer"] = _feld(STATUS_UNSICHER, next(iter(un)))
        else:
            f["nummer"] = _feld(STATUS_KEINER)

    # --- Folgentitel (4.5): Abgleich nur über Apple, neuer Wert nach T1
    nr_fuer_titel = f["nummer"]["neu"] if f["nummer"]["status"] == STATUS_SICHER else ctx["nummer_bekannt"]

    def _neu(x: Mapping[str, Any]) -> str:
        if ctx["platzhalter"]:
            return titel_neu(ctx, x, nr_fuer_titel)
        return titel_neu_bekannt(ctx["anzeige"], nr_fuer_titel)

    if sicher_apple:
        titel = {_neu(x) for x in sicher_apple}
        x = sicher_apple[0]
        f["folge_titel"] = _feld(
            STATUS_SICHER if len(titel) == 1 else STATUS_UNSICHER, _neu(x), _apple_quelle(x)
        )
    elif uns:
        f["folge_titel"] = _feld(STATUS_UNSICHER, _neu(uns[0]), _apple_quelle(uns[0]))
    else:
        f["folge_titel"] = _feld(STATUS_KEINER)
    ft = f["folge_titel"]
    # Wie OS1 gemessen: Nur „Teil/Band N“ mit anderer Nummer macht den Titel unsicher; bei „…, Folge N: …“ bleibt er
    # unverändert, aber ohne Prüfung gegen die Nummer.
    tb = teil_band_nummer(ctx["anzeige"])
    if (
        tb is not None
        and not ctx["platzhalter"]
        and nr_fuer_titel is not None
        and tb != nr_fuer_titel
        and ft["status"] == STATUS_SICHER
    ):
        ft["status"] = STATUS_UNSICHER  # Titel bleibt unverändert, aber die Nummer widerspricht „Teil/Band N“
        ft["grund"] = f"Teil/Band {tb} im Titel, Nummer {nr_fuer_titel}"
    neu_titel = ft["neu"]
    ft["aenderung"] = (
        None
        if neu_titel is None or neu_titel == ctx["anzeige"]
        else ("woerter" if ctx["platzhalter"] else "form")
    )

    # --- Art je Folge (4.7, T4)
    sicher_art: dict[str, Any] = {}
    unsicher_art: dict[str, Any] = {}
    if tp["status"] == STATUS_SICHER and tp["art"]:
        (sicher_art if tp["art_sicher"] else unsicher_art).setdefault(tp["art"], _tonie_quelle(tp["rep"]))
    elif tp["status"] == STATUS_UNSICHER and tp["art"]:
        unsicher_art.setdefault(tp["art"], _tonie_quelle(tp["rep"]))
    if alben:
        sicher_art.setdefault("hoerspiel", _apple_quelle(alben[0]))
    album_gefunden = bool(alben) or any(x["typ"] == "album" for x in uns)
    if buecher and not album_gefunden:
        # T4: „Hörspiel“ im Albumnamen schlägt den Hörbuch-Typ: Ist darunter ein solcher Treffer, gilt ``hoerspiel``
        b = next((b for b in buecher if b["art"] == "hoerspiel"), buecher[0])
        sicher_art.setdefault(b["art"] or "hoerbuch", _apple_quelle(b))
    # Wie OS1 gemessen: Nur Treffer mit gleichem Titel und einem Genre der Musik-Klasse, Hörspiel- oder Hörbuch-Klasse
    # widersprechen; ein anderes Genre („Comedy“, Klasse „sonst“) liefert keine Art und widerspricht nicht.
    widerspruch: dict[str, Any] = {}
    for x in uns:
        a = x["art"]
        if a:
            if x.get("grund", "").startswith("genre:"):
                widerspruch.setdefault(a, x)
            unsicher_art.setdefault(a, _apple_quelle(x))
    if (
        len(sicher_art) == 1
        and not (set(widerspruch) - set(sicher_art))
        and not (set(unsicher_art) - set(sicher_art) and any(k in widerspruch for k in unsicher_art))
    ):
        a = next(iter(sicher_art))
        f["art"] = _feld(STATUS_SICHER, a, sicher_art[a])
    elif sicher_art or unsicher_art:
        a = next(iter(sicher_art or unsicher_art))
        f["art"] = _feld(STATUS_UNSICHER, a, (sicher_art or unsicher_art)[a])
    else:
        f["art"] = _feld(STATUS_KEINER)

    # --- Cover je Folge (4.3)
    ids = {x["collectionId"] for x in alben}
    if len(ids) == 1:
        f["cover"] = _feld(STATUS_SICHER, alben[0]["bild"], _apple_quelle(alben[0]), collection_id=alben[0]["collectionId"])
    elif len(ids) > 1:
        f["cover"] = _feld(
            STATUS_UNSICHER, alben[0]["bild"], _apple_quelle(alben[0]), collection_id=alben[0]["collectionId"],
            grund="mehrere_alben",
        )  # fmt: skip
    elif buecher or uns:
        x = (buecher + uns)[0]
        f["cover"] = _feld(STATUS_UNSICHER, x["bild"], _apple_quelle(x), collection_id=x["collectionId"])
    else:
        f["cover"] = _feld(STATUS_KEINER, collection_id=None)

    # --- Beschreibung und Alter (4.9)
    si, ausstehend = _shop_info(tp, shop_daten) if tp["status"] == STATUS_SICHER else (None, False)
    f["shop_pfade"] = [p for p, _m in tp.get("shop_pfade", ()) if p] if tp["status"] == STATUS_SICHER else []
    shop_text = si.get("beschreibung") if si else None
    shop_alter = _alter_gueltig(si.get("alter_ab")) if si else None
    if isinstance(shop_text, str) and shop_text.strip():
        f["beschreibung"] = _feld(
            STATUS_SICHER, shop_text[:BESCHREIBUNG_MAX], {"typ": "tonies_shop", "model": si["model"]}  # type: ignore[index]
        )
    else:
        # Wie OS1 gemessen: Der Apple-Zweig steht vor der Prüfung „Seite aussteht“; ein sicheres Hörbuch mit Beschreibung
        # wird auch dann „sicher“, wenn die Shopseite des Tonies noch fehlt (nur Alter bleibt dann „nicht_geholt“).
        bids = {x["collectionId"] for x in buecher if x.get("beschreibung")}
        if len(bids) == 1:
            x = next(b for b in buecher if b.get("beschreibung"))
            text = html_zu_text(x["beschreibung"])
            if text:
                f["beschreibung"] = _feld(STATUS_SICHER, text, _apple_quelle(x))
            else:
                f["beschreibung"] = _feld(STATUS_KEINER)
        elif ausstehend or res is None:
            f["beschreibung"] = _feld(STATUS_NICHT_GEHOLT)
        else:
            f["beschreibung"] = _feld(STATUS_KEINER)
    if shop_alter is not None:
        f["alter_ab"] = _feld(STATUS_SICHER, shop_alter, {"typ": "tonies_shop", "model": si["model"]})  # type: ignore[index]
    elif ausstehend:
        f["alter_ab"] = _feld(STATUS_NICHT_GEHOLT)
    else:
        f["alter_ab"] = _feld(STATUS_KEINER)
    f["apple"] = ab
    return f


# --------------------------------------------------------------------------
# Felder je Eintrag (Cover, Art) und Gesamtfunktion
# --------------------------------------------------------------------------


def bewerte_eintrag(
    eintrag: Mapping[str, Any],
    tonie_index: Mapping[str, Any],
    apple_ergebnisse: Sequence[Sequence[Any] | None],
    shop_daten: Mapping[str, Any] | None = None,
    sitemap_pfade: Collection[str] | None = None,
    *,
    mit_kandidaten: bool = False,
) -> dict[str, Any]:
    """Bewertet einen Eintrag (Formen: Modul-Docstring).

    ``apple_ergebnisse``: je Folge die iTunes-Ergebnisse oder ``None`` (nicht geholt). ``shop_daten``: geprüfte Daten
    der Shopseiten je ``model``. ``sitemap_pfade``: Pfade der Sitemap (``/de-de/tonies/<serie>/<folge>/``); damit weiß
    der Abgleich, welche Seiten er erwartet (``nicht_geholt``, solange eine fehlt) und gibt sie je Folge als
    ``shop_pfade`` heraus. Ohne Sitemap werden Shop-Daten zu den Tonie-Kandidaten trotzdem benutzt, eine fehlende
    Seite bleibt aber unbemerkt (``keiner``). ``mit_kandidaten``
    fügt je Folge ``kandidaten`` für den KI-Schritt hinzu (:func:`ki_kandidaten`).

    Ergebnis::

        {
          "cover": Feldergebnis (je Eintrag, 4.3; mit "geschuetzt": True bei eigenem Cover),
          "art": Feldergebnis (je Eintrag, 4.7; mit "geschuetzt": True, wenn die Art nicht „geraten“ ist),
          "folgen": [ {"cover", "art", "folge_titel", "nummer", "beschreibung", "alter_ab",
                       "shop_pfade", "tonie": {...}, "kandidaten"?}, ... ],
        }

    Ein Feld je Folge hat ``status``, ``neu``, ``quelle`` und je nach Feld weitere Angaben (``collection_id``,
    ``grund``, ``aenderung`` beim Folgentitel). ``nicht_geholt`` steht bei Cover (ganzer Eintrag), Beschreibung und
    Alter, solange eine nötige Quelle fehlt."""
    shop_daten = shop_daten or {}
    name = eintrag.get("name") or ""
    folgen_roh = list(eintrag.get("folgen") or [])
    n = len(folgen_roh)
    einzeln = bool(eintrag.get("einzeln"))
    if len(apple_ergebnisse) != n:
        raise ValueError("apple_ergebnisse braucht ein Element je Folge")
    ctxs = [folge_kontext(name, f, einzeln, n) for f in folgen_roh]
    summe_tracks = sum(c["tracks"] for c in ctxs)
    alle_ok = all(r is not None for r in apple_ergebnisse)
    pool = apple_entdoppeln(r for res in apple_ergebnisse for r in (res or ()))

    folgen: list[dict[str, Any]] = []
    for c, res in zip(ctxs, apple_ergebnisse):
        tp = tonie_pruefen(c, tonie_index, sitemap_pfade)
        f = bewerte_folge(c, res, tp, shop_daten)
        f["tonie"] = {
            "status": tp["status"],
            "art": tp["art"],
            "nummer": tp["nummer"],
            "flags": list(tp["flags"]),
            "modelle": [e["model"] for e in (tp["sichere"] or tp["unsichere"])],
        }
        if mit_kandidaten:
            f["kandidaten"] = ki_kandidaten(c, tonie_index, res)
        folgen.append(f)

    # --- Cover des Eintrags (4.3, 2.7)
    if not alle_ok:
        cover = _feld(STATUS_NICHT_GEHOLT, collection_id=None)
    elif n >= 2 and not einzeln:
        ra = reihen_alben(name, pool, summe_tracks)
        if len(ra) == 1:
            cover = _feld(STATUS_SICHER, ra[0]["bild"], _apple_quelle(ra[0]), collection_id=ra[0]["collectionId"])
        elif len(ra) > 1:
            cover = _feld(
                STATUS_UNSICHER, ra[0]["bild"], _apple_quelle(ra[0]), collection_id=ra[0]["collectionId"],
                grund="mehrere_reihen_alben",
            )  # fmt: skip
        else:
            kand = [f["cover"] for f in folgen if f["cover"]["status"] in (STATUS_SICHER, STATUS_UNSICHER)]
            if kand:
                cover = _feld(
                    STATUS_UNSICHER, kand[0]["neu"], kand[0]["quelle"], collection_id=kand[0]["collection_id"],
                    grund="nur_folgen_cover",
                )  # fmt: skip
            else:
                cover = _feld(STATUS_KEINER, collection_id=None)
    elif folgen:
        cover = dict(folgen[0]["cover"])
    else:
        cover = _feld(STATUS_KEINER, collection_id=None)
    cover["geschuetzt"] = eintrag.get("cover_quelle") == "eigen"

    # --- Art des Eintrags (4.7)
    sicher_werte = [f["art"]["neu"] for f in folgen if f["art"]["status"] == STATUS_SICHER]
    mw = mehrheit(sicher_werte, n)
    if mw:
        q = next(f["art"]["quelle"] for f in folgen if f["art"]["status"] == STATUS_SICHER and f["art"]["neu"] == mw)
        art = _feld(STATUS_SICHER, mw, q, stimmen=f"{sicher_werte.count(mw)} von {n} Folgen")
    else:
        irgendeine = [f["art"]["neu"] for f in folgen if f["art"]["status"] in (STATUS_SICHER, STATUS_UNSICHER)]
        art = _feld(STATUS_UNSICHER, irgendeine[0]) if irgendeine else _feld(STATUS_KEINER)
    art["geschuetzt"] = eintrag.get("art_quelle") not in (None, "geraten")

    return {"cover": cover, "art": art, "folgen": folgen}
