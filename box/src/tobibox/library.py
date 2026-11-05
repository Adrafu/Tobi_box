"""Serien aus dem Medienordner (``data-model.md``, Abschnitt 5).

Liest ``medien/<ordner>/serie.json`` (nur lesen) und bildet ``events.Serie``.
Die Liste ``folgen`` ist maßgeblich; Dateien außerhalb der Liste werden nicht
gespielt, Namen ohne Datei werden übersprungen. Ein Ordner ohne (gültige)
``serie.json`` wird mit dem Ordnernamen als ID gespielt, in natürlicher
Sortierung.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import events as ev
from .eventlog import logge

#: Endungen, die ein Ordner ohne ``serie.json`` als Folgen zählt (Vertragslücke, siehe Bericht)
AUDIO_ENDUNGEN = frozenset({".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav"})

BEKANNTE_VERSIONEN = frozenset({1})

_ZIFFERN = re.compile(r"([0-9]+)")


# --------------------------------------------------------------------------
# Natürliche Sortierung (data-model.md, Abschnitt 5)
# --------------------------------------------------------------------------


def natuerlicher_schluessel(name: str) -> tuple:
    """Sortierschlüssel nach der Regel des Datenmodells.

    Abschnitte: Ziffernblöcke (ASCII ``0``-``9``) sind kleiner als Textblöcke;
    Ziffernblöcke zählen als Zahl, Textblöcke ohne Groß-/Kleinschreibung
    (``casefold``) nach Codepunkten; kürzere Abschnittsfolge zuerst; bei
    Gleichstand entscheidet der rohe UTF-8-Byte-String.
    """
    abschnitte: list[tuple[int, Any]] = []
    for teil in _ZIFFERN.split(name):
        if teil == "":
            continue
        if teil[0] in "0123456789" and teil.isascii():
            abschnitte.append((0, int(teil)))
        else:
            abschnitte.append((1, teil.casefold()))
    return (tuple(abschnitte), name.encode("utf-8"))


def sortiere_natuerlich(namen: list[str]) -> list[str]:
    return sorted(namen, key=natuerlicher_schluessel)


# --------------------------------------------------------------------------
# Gültigkeit
# --------------------------------------------------------------------------


def serien_id_gueltig(sid: object) -> bool:
    """1 bis 64 Zeichen, ohne ``/``, ohne Steuerzeichen."""
    return (
        isinstance(sid, str)
        and 1 <= len(sid) <= 64
        and "/" not in sid
        and not any(ord(c) < 32 or ord(c) == 127 for c in sid)
    )


def dateiname_gueltig(name: object) -> bool:
    return (
        isinstance(name, str)
        and name not in ("", ".", "..")
        and "/" not in name
        and "\\" not in name
        and "\x00" not in name
        and len(name.encode("utf-8", "surrogateescape")) <= 255
    )


@dataclass(frozen=True, slots=True)
class SerieJson:
    id: str
    name: str
    typ: str
    folgen: tuple[str, ...]
    angelegt_am: str


class SerieJsonUngueltig(ValueError):
    pass


def parse_serie_json(roh: object) -> SerieJson:
    if not isinstance(roh, dict):
        raise SerieJsonUngueltig("kein Objekt")
    v = roh.get("schema_version")
    if isinstance(v, bool) or not isinstance(v, int) or v not in BEKANNTE_VERSIONEN:
        raise SerieJsonUngueltig(f"schema_version {v!r}")
    sid, name, typ, folgen, am = (roh.get(k) for k in ("id", "name", "typ", "folgen", "angelegt_am"))
    if not serien_id_gueltig(sid):
        raise SerieJsonUngueltig("id")
    if not isinstance(name, str) or not 1 <= len(name) <= 100:
        raise SerieJsonUngueltig("name")
    if typ not in ("normal", "ueberraschung"):
        raise SerieJsonUngueltig("typ")
    if not isinstance(folgen, list) or not all(dateiname_gueltig(f) for f in folgen):
        raise SerieJsonUngueltig("folgen")
    if not isinstance(am, str) or not am:
        raise SerieJsonUngueltig("angelegt_am")
    return SerieJson(sid, name, typ, tuple(folgen), am)


# --------------------------------------------------------------------------
# Bibliothek laden
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Bibliothek:
    serien: tuple[ev.Serie, ...]
    #: ``"ok"``, ``"keine"``, ``"mehrere"`` oder ``"leer"``
    ueberraschung_status: str

    def ereignis(self) -> ev.BibliothekGeladen:
        return ev.BibliothekGeladen(self.serien)

    def serie(self, serie_id: str) -> ev.Serie | None:
        for s in self.serien:
            if s.id == serie_id:
                return s
        return None


def ueberraschung_status(serien: tuple[ev.Serie, ...]) -> str:
    kandidaten = [s for s in serien if s.typ == "ueberraschung"]
    if not kandidaten:
        return "keine"
    if len(kandidaten) > 1:
        return "mehrere"
    return "ok" if kandidaten[0].folgen else "leer"


def finde_ueberraschung(serien: tuple[ev.Serie, ...]) -> ev.Serie | None:
    """Die einzige nicht leere Überraschungs-Serie (nur über ``typ``), sonst ``None``."""
    return next((s for s in serien if s.typ == "ueberraschung"), None) if ueberraschung_status(serien) == "ok" else None


def _vorhandene_dateien(ordner: Path) -> set[str]:
    try:
        return {p.name for p in ordner.iterdir() if p.is_file()}
    except OSError:
        return set()


def _lies_serie_json(pfad: Path, ordner_name: str) -> SerieJson | None:
    try:
        raw = pfad.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as e:
        logge("library", "ERROR", "serie_json_unlesbar", "fehler", ordner=ordner_name, detail=str(e))
        return None
    try:
        return parse_serie_json(json.loads(raw.decode("utf-8")))
    except (ValueError, UnicodeDecodeError) as e:
        logge("library", "ERROR", "serie_json_ungueltig", "fehler", ordner=ordner_name, grund=str(e))
        return None


def _serie_aus_ordner(ordner: Path, medien: Path) -> tuple[ev.Serie, str] | None:
    """(Serie, angelegt_am) oder ``None``, wenn der Ordner nicht gespielt wird."""
    dateien = _vorhandene_dateien(ordner)
    sj = _lies_serie_json(ordner / "serie.json", ordner.name)
    rel = ordner.relative_to(medien).as_posix()
    if sj is None:
        if not serien_id_gueltig(ordner.name):
            logge("library", "ERROR", "ordner_name_ungueltig", "uebersprungen", ordner=ordner.name)
            return None
        audio = [n for n in dateien if Path(n).suffix.lower() in AUDIO_ENDUNGEN and dateiname_gueltig(n)]
        folgen = tuple(sortiere_natuerlich(audio))
        return ev.Serie(ordner.name, ordner.name, "normal", rel, folgen), ""
    gesehen: set[str] = set()
    folgen_l: list[str] = []
    for f in sj.folgen:
        if f in gesehen:
            continue
        gesehen.add(f)
        if f in dateien:
            folgen_l.append(f)
        else:
            logge("library", "WARNING", "folge_fehlt", "uebersprungen", serie=sj.id, datei=f)
    return ev.Serie(sj.id, sj.name, sj.typ, rel, tuple(folgen_l)), sj.angelegt_am  # type: ignore[arg-type]


def lade_bibliothek(medien: str | Path) -> Bibliothek:
    """Alle Serien im Medienordner. Fehler einzelner Ordner stoppen die anderen nicht."""
    medien = Path(medien)
    if not medien.is_dir():
        logge("library", "ERROR", "medienordner_fehlt", "fehler", pfad=str(medien))
        return Bibliothek((), "keine")
    kandidaten: list[tuple[ev.Serie, str]] = []
    for ordner in sorted((p for p in medien.iterdir() if p.is_dir() and not p.name.startswith(".")),
                         key=lambda p: natuerlicher_schluessel(p.name)):
        e = _serie_aus_ordner(ordner, medien)
        if e is not None:
            kandidaten.append(e)

    # Doppelte IDs: die ältere Kopie behält die ID, die jüngere wird nicht gespielt
    # (die neue ID vergibt die HA-Integration; Box schreibt nie serie.json).
    kandidaten.sort(key=lambda k: (k[1], natuerlicher_schluessel(k[0].ordner)))
    serien: list[ev.Serie] = []
    ids: set[str] = set()
    for s, _am in kandidaten:
        if s.id in ids:
            logge("library", "ERROR", "serie_id_doppelt", "uebersprungen", serie=s.id, ordner=s.ordner)
            continue
        ids.add(s.id)
        serien.append(s)
    serien.sort(key=lambda s: natuerlicher_schluessel(s.ordner))

    ergebnis = tuple(serien)
    status = ueberraschung_status(ergebnis)
    if status != "ok":
        logge("library", "ERROR", "ueberraschung_ungueltig", "fehler", grund=status)
    return Bibliothek(ergebnis, status)


def abspielpfad(medien: str | Path, serie: ev.Serie, datei: str) -> Path | None:
    """Pfad der Folge, nur wenn sie in ``serie.folgen`` steht (sonst ``None``)."""
    if datei not in serie.folgen or not dateiname_gueltig(datei):
        return None
    return Path(medien) / serie.ordner / datei
