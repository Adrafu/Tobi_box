"""Namensregeln, Vergleichsschlüssel und natürliche Sortierung (Vertrag W, Abschnitte 11.2 und 12).

Alles hier ist reine Funktion ohne Dateizugriff und deshalb einzeln testbar.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Collection
from typing import Any

from .const import GERAETENAMEN, NAME_MAX_BYTES

#: Platz für das Suffix `` (99)`` (Vertrag W, Abschnitt 12, Regel 5)
SUFFIX_PLATZ = 5
#: Obergrenze für Bytes und UTF-16-Einheiten eines Namens, ohne Suffix-Platz
NAME_LIMIT = NAME_MAX_BYTES - SUFFIX_PLATZ

_VERBOTEN_UNTERSTRICH = str.maketrans({c: "_" for c in '/\\*?"<>|'})
_ZIFFERN = re.compile(r"([0-9]+)")
_LEERRAUM = re.compile(r"\s+")
_DOPPELPUNKT = re.compile(r"\s*:\s*")


class NamenErschoepft(Exception):
    """Alle Suffixe `` (2)`` bis `` (98)`` sind vergeben (``medien_schreibfehler``)."""


# --------------------------------------------------------------------------
# Hilfen
# --------------------------------------------------------------------------


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def ohne_steuerzeichen(text: str) -> str:
    """Entfernt Steuerzeichen (U+0000 bis U+001F, U+007F bis U+009F)."""
    return "".join(c for c in text if not (ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F))


def anzeigename(text: Any, max_zeichen: int) -> str:
    """Anzeigename (Regel 8): Steuerzeichen entfernt, Leerraum gekürzt, ``:`` bleibt. Leer, wenn nichts bleibt."""
    if not isinstance(text, str):
        return ""
    text = nfc(ohne_steuerzeichen(text)).strip()
    return text[:max_zeichen].strip()


def vergleichsschluessel(name: str) -> str:
    """Namensgleichheit auf der SMB-Freigabe: nach NFC, ohne Groß-/Kleinschreibung (Regel 7)."""
    return nfc(name).lower()


def utf16_einheiten(text: str) -> int:
    return len(text.encode("utf-16-le", "surrogatepass")) // 2


def _passt(text: str, limit: int) -> bool:
    return len(text.encode("utf-8", "surrogatepass")) <= limit and utf16_einheiten(text) <= limit


def kuerze_an_zeichengrenze(text: str, limit: int) -> str:
    """Kürzt auf höchstens ``limit`` Bytes (UTF-8) und ``limit`` UTF-16-Einheiten, nie mitten im Zeichen."""
    if _passt(text, limit):
        return text
    aus: list[str] = []
    for zeichen in text:
        if not _passt("".join(aus) + zeichen, limit):
            break
        aus.append(zeichen)
    return "".join(aus)


def trenne_endung(name: str) -> tuple[str, str]:
    """``("Folge 1", ".mp3")``; ohne gültige Endung ``(name, "")``."""
    stamm, punkt, endung = name.rpartition(".")
    if punkt and stamm and 1 <= len(endung) <= 8 and endung.isalnum():
        return stamm, "." + endung
    return name, ""


# --------------------------------------------------------------------------
# Dateinamen (Abschnitt 12)
# --------------------------------------------------------------------------


def dateiname_bereinigen(roh: str, *, mit_endung: bool = True, fuer_serienordner: bool = False) -> tuple[str, bool]:
    """Bereinigt einen Datei- oder Ordnernamen für die SMB-Freigabe (Regeln 1 bis 5).

    Gibt ``(name, stark_geaendert)`` zurück. ``stark_geaendert`` ist ``True``, wenn der Name
    gekürzt werden musste (Kennzeichen ``name_geaendert``). Ist nach allem nichts übrig,
    kommt ``""`` zurück; der Aufrufer entscheidet dann (``name_ungueltig`` oder ``Unbenannt``).

    ``fuer_serienordner``: Ein Serien-Ordner darf nicht mit ``_`` beginnen (reserviert, Abschnitt 12,
    Ende); ein Gerätename erhält deshalb ein ``_`` am Ende statt davor.
    """
    if not isinstance(roh, str):
        return "", False
    name = nfc(roh)
    name = ohne_steuerzeichen(name)
    if name.strip() in (".", ".."):
        return ("_" if not fuer_serienordner else "_ordner"), False
    name = _DOPPELPUNKT.sub(" - ", name)
    name = name.translate(_VERBOTEN_UNTERSTRICH)
    name = _LEERRAUM.sub(" ", name).strip()
    name = name.lstrip("._ ").rstrip(". ")
    name = _LEERRAUM.sub(" ", name).strip()
    if not name:
        return "", False

    stamm, endung = trenne_endung(name) if mit_endung else (name, "")
    if stamm.lower() in GERAETENAMEN:
        stamm = f"{stamm}_" if fuer_serienordner else f"_{stamm}"
    gekuerzt = False
    if not _passt(stamm + endung, NAME_LIMIT):
        gekuerzt = True
        stamm = kuerze_an_zeichengrenze(stamm, NAME_LIMIT - len(endung.encode("utf-8")))
        stamm = stamm.rstrip(". ")
        while stamm and not _passt(stamm + endung, NAME_LIMIT):
            stamm = stamm[:-1].rstrip(". ")
    if not stamm:
        return "", False
    return stamm + endung, gekuerzt


def eindeutiger_name(name: str, belegt: Collection[str], *, mit_endung: bool = True) -> str:
    """Hängt `` (2)``, `` (3)`` … vor die Endung (bei Ordnern ans Ende), bis der Name frei ist.

    ``belegt`` enthält Namen im Vergleichsschlüssel (``vergleichsschluessel``). Ab `` (99)`` gibt es
    ``NamenErschoepft``.
    """
    if vergleichsschluessel(name) not in belegt:
        return name
    stamm, endung = trenne_endung(name) if mit_endung else (name, "")
    for n in range(2, 99):
        kandidat = f"{stamm} ({n}){endung}"
        if vergleichsschluessel(kandidat) not in belegt:
            return kandidat
    raise NamenErschoepft(name)


# --------------------------------------------------------------------------
# Natürliche Sortierung (``data-model.md``, Abschnitt 5; gleiche Regel wie ``box/src/tobibox/library.py``)
# --------------------------------------------------------------------------


def natuerlicher_schluessel(name: str) -> tuple:
    abschnitte: list[tuple[int, Any]] = []
    for teil in _ZIFFERN.split(name):
        if teil == "":
            continue
        if teil[0] in "0123456789" and teil.isascii():
            abschnitte.append((0, int(teil)))
        else:
            abschnitte.append((1, teil.casefold()))
    return (tuple(abschnitte), name.encode("utf-8", "surrogateescape"))


def sortiere_natuerlich(namen: Collection[str]) -> list[str]:
    return sorted(namen, key=natuerlicher_schluessel)


# --------------------------------------------------------------------------
# Vergleich und Tag-Werte (Abschnitt 11.2)
# --------------------------------------------------------------------------


def norm(text: str) -> str:
    """``norm(x)``: NFKC, ``casefold``, alle Zeichen entfernen, die kein Buchstabe und keine Ziffer sind.

    Ergibt das leer, gilt der gekürzte ``casefold``-Wert."""
    k = unicodedata.normalize("NFKC", text).casefold()
    r = "".join(c for c in k if c.isalnum())
    return r if r else k.strip()


def norm_tagwert(wert: Any) -> str:
    """Tag-Wert normieren: NFC, Steuerzeichen weg, Leerraum zu einem Leerzeichen, auf 200 Zeichen gekürzt.

    Ein Wert ohne Buchstaben und Ziffern gilt als leer (``""``)."""
    if wert is None:
        return ""
    text = nfc(ohne_steuerzeichen(str(wert)))
    text = _LEERRAUM.sub(" ", text).strip()[:200].strip()
    if not any(c.isalnum() for c in text):
        return ""
    return text


PLATZHALTER_INTERPRETEN = frozenset(
    norm(x)
    for x in (
        "various artists",
        "various",
        "verschiedene",
        "verschiedene interpreten",
        "diverse",
        "va",
        "unknown",
        "unbekannt",
        "n/a",
    )
)


def ist_platzhalter(text: str) -> bool:
    return norm(text) in PLATZHALTER_INTERPRETEN


_CD_KLAMMER = re.compile(
    r"\s*[\(\[]\s*(?:cd|disc|disk)\s*\.?\s*(\d{1,3})(?:\s*/\s*\d{1,3})?\s*[\)\]]\s*$", re.IGNORECASE
)
_CD_STRICH = re.compile(r"\s*[-–—]\s*(?:cd|disc|disk)\s*\.?\s*(\d{1,3})(?:\s*/\s*\d{1,3})?\s*$", re.IGNORECASE)


def album_ohne_cd_zusatz(album: str) -> tuple[str, int | None]:
    """Entfernt einen Zusatz wie ``(CD 2)``, ``[Disc 1]``, ``- CD 3``, ``CD 2/4`` am Ende (nicht ``Teil``)."""
    for muster in (_CD_KLAMMER, _CD_STRICH):
        m = muster.search(album)
        if m and album[: m.start()].strip():
            return album[: m.start()].strip(), int(m.group(1))
    return album, None


_ZAHL = r"0*(\d{1,4})(?!\d)"
_R1 = re.compile(
    r"(?<![^\W_])(?:folge|teil|band|episode|ep|nr|nummer|volume|vol)[.:#]*\s*" + _ZAHL, re.IGNORECASE
)
_R2 = re.compile(r"^\s*" + _ZAHL + r"\s*[-–—:._)]\s*\S")
_R3 = re.compile(r"#\s*" + _ZAHL)
_R4 = re.compile(r"\(\s*" + _ZAHL + r"\s*\)\s*$")
_NUMMER_TAG = re.compile(r"^\s*0*(\d{1,4})")


def nummer_aus_text(text: str) -> int | None:
    """Folgen-Nummer aus einem Text nach den Regeln R1 bis R4 (Abschnitt 11.2)."""
    for muster in (_R1, _R2, _R3, _R4):
        m = muster.search(text)
        if m:
            return int(m.group(1))
    return None


def nummer_aus_tag(wert: str) -> int | None:
    """``nummer_tag``: die erste ganze Zahl am Anfang."""
    m = _NUMMER_TAG.match(wert)
    return int(m.group(1)) if m else None


_DATUM = re.compile(r"^\s*(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?")


def zahl_vor_slash(wert: str) -> int | None:
    """``3`` oder ``3/12`` -> 3; sonst ``None``."""
    return nummer_aus_tag(wert)


def datum_aus_tag(wert: str) -> str | None:
    """``YYYY``, ``YYYY-MM``, ``YYYY-MM-DD`` (Jahr 1900 bis 2100) -> ``YYYY-MM-DD``; sonst ``None``."""
    m = _DATUM.match(wert)
    if not m:
        return None
    jahr = int(m.group(1))
    if not 1900 <= jahr <= 2100:
        return None
    monat = int(m.group(2)) if m.group(2) else 1
    tag = int(m.group(3)) if m.group(3) else 1
    if not 1 <= monat <= 12 or not 1 <= tag <= 31:
        return None
    return f"{jahr:04d}-{monat:02d}-{tag:02d}"
