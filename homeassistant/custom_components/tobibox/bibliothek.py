"""Bibliothek: Art, Suche, Filter, Sortieren und Blättern (Vertrag W, 14.2; Design 5.2 und 11.2, V-2 und V-8).

Zwei Teile, beide ohne Dateizugriff (reine Rechnung im Speicher der Integration):

* ``art_vorschlag``: die Art eines neuen Eintrags aus den Tags beim Einsortieren.
* ``Bibliothek``: ein Index über Einträge und Folgen für ``serien/list``, ``folgen/list`` und ``zuordnung/list``.
  Ein Einzeltitel ist eine normale Serie mit genau einer Folge und steht damit **als Serie und als Folge** im Index.

Der Index hängt an ``Medien.serien``. Er merkt sich je Eintrag das ``SerieInfo``-Objekt, aus dem er gebaut wurde; jede
Änderung (Prüfung, Umbenennen, Einsortieren …) legt ein neues ``SerieInfo`` an, so baut der nächste Aufruf genau diese
Einträge neu auf. Damit muss keine Stelle im Code „Index ändern“ rufen (Aktualisierung bei ``serien_geaendert``, nur ohne
eigene Meldung).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from .const import (
    ART_GESCHICHTE_MAX_S,
    ART_KURZE_TRACKS_MITTEL_S,
    ART_VIELE_TRACKS,
    ART_VORGABE,
    NEU_TAGE,
    SERIEN_OHNE_LIMIT_MAX,
)
from .namen import natuerlicher_schluessel
from .util import jetzt, parse_iso

if TYPE_CHECKING:
    from .media import Medien, SerieInfo

_WORTTEIL = re.compile(r"[^\W_]+")


# --------------------------------------------------------------------------
# Suchform
# --------------------------------------------------------------------------


def suchform(text: str) -> str:
    """Text zum Suchen: ohne Groß-/Kleinschreibung, ohne Akzente und Umlaute (``ä`` = ``a``, ``ß`` = ``ss``), nur Wörter."""
    zerlegt = unicodedata.normalize("NFKD", text).casefold()
    ohne_zeichen = "".join(c for c in zerlegt if not unicodedata.combining(c))
    return " ".join(_WORTTEIL.findall(ohne_zeichen))


def suchworte(text: str) -> list[str]:
    """Die Wörter einer Suche. Ein Text ganz ohne Buchstaben und Ziffern („?!“) sucht als Ganzes."""
    worte = suchform(text).split()
    if worte:
        return worte
    rest = unicodedata.normalize("NFKD", text).casefold().strip()
    return [rest] if rest else []


def passt(worte: list[str], heu: str) -> bool:
    """Jedes Wort der Suche kommt irgendwo im Heu vor (``suchform``)."""
    return all(w in heu for w in worte)


# --------------------------------------------------------------------------
# Art-Vorschlag beim Einsortieren (Vertrag W, 14.2)
# --------------------------------------------------------------------------

#: je Art: (Stichworte, die irgendwo im Genre stehen dürfen; Stichworte, die ein Wort des Genres anfangen)
_GENRE_HOERBUCH = (("horbuch", "hoerbuch", "audiobook", "audio book"), ("spoken",))
_GENRE_HOERSPIEL = (("horspiel", "hoerspiel", "audio drama", "audiodrama", "radio play", "radioplay", "radio drama"), ())
_GENRE_MUSIK = (
    ("kinderlied", "kindermusik", "schlaflied", "wiegenlied", "volkslied"),
    (
        "pop", "rock", "jazz", "folk", "klassik", "classic", "children", "kids", "lullab", "musik", "music", "lieder", "song",
        "soundtrack", "electronic", "hip", "schlager", "blues", "country", "reggae", "metal", "soul",
    ),
)
_GENRE_GESCHICHTE = (("marchen", "maerchen", "geschicht"), ("fairy", "story", "stories", "vorlese"))


@dataclass(frozen=True)
class ArtDatei:
    """Was der Art-Vorschlag von einer Datei wissen will."""

    endung: str = ""
    genre: str = ""
    dauer_s: float | None = None
    album: str = ""
    album_interpret: str = ""


def _genre_passt(genres: list[str], stichworte: tuple[tuple[str, ...], tuple[str, ...]]) -> bool:
    """Ein Stichwort steht im Genre („Kinderhörspiel“ passt auf ``horspiel``) oder fängt ein Wort darin an („Popular“ auf ``pop``)."""
    inhalt, anfang = stichworte
    for genre in genres:
        form = suchform(genre)
        mit_anfang = f" {form}"
        if any(s in form for s in inhalt) or any(f" {s}" in mit_anfang for s in anfang):
            return True
    return False


def art_vorschlag(dateien: list[ArtDatei]) -> tuple[str, str]:
    """``(art, art_quelle)`` für einen **neuen** Eintrag aus allen seinen Dateien.

    Reihenfolge: Genre „Hörbuch“ → Genre „Hörspiel“ → Endung ``.m4b`` → Musikgenre → Genre „Märchen/Geschichten“ → viele kurze
    Tracks mit Album-Interpret (Musik) → Einzeldatei unter 30 Minuten ohne Album (Geschichte) → sonst ``hoerspiel`` und
    ``geraten``. Ein ausdrückliches Genre schlägt die Endung. Treffer der Regeln haben die Quelle ``tags``; nur der
    Rückfall ist ``geraten`` (dann hängt der Aufrufer den Grund ``art_geraten`` an)."""
    genres = [d.genre for d in dateien if d.genre]
    if _genre_passt(genres, _GENRE_HOERBUCH):
        return "hoerbuch", "tags"
    if _genre_passt(genres, _GENRE_HOERSPIEL):
        return "hoerspiel", "tags"
    if any(d.endung.lower() == "m4b" for d in dateien):
        return "hoerbuch", "tags"
    if _genre_passt(genres, _GENRE_MUSIK):
        return "musik", "tags"
    if _genre_passt(genres, _GENRE_GESCHICHTE):
        return "geschichte", "tags"
    dauern = [d.dauer_s for d in dateien if d.dauer_s is not None and d.dauer_s > 0]
    if dauern and len(dateien) >= ART_VIELE_TRACKS and any(d.album_interpret for d in dateien):
        if sum(dauern) / len(dauern) < ART_KURZE_TRACKS_MITTEL_S:
            return "musik", "tags"
    if len(dateien) == 1 and not dateien[0].album and dauern and dauern[0] < ART_GESCHICHTE_MAX_S:
        return "geschichte", "tags"
    return ART_VORGABE, "geraten"


# --------------------------------------------------------------------------
# Index
# --------------------------------------------------------------------------


@dataclass
class _FolgeZeile:
    name: str
    anzeige: str
    heu: str
    sortier: tuple
    objekt: dict[str, Any]


@dataclass
class _SerieZeile:
    info: SerieInfo  # Gültigkeit: gebaut aus genau diesem Objekt
    art: str
    einzeln: bool
    heu: str
    sortier: tuple
    angelegt: float
    pruefen: bool
    folgen: list[_FolgeZeile] = field(default_factory=list)


def _serie_zeile(info: SerieInfo) -> _SerieZeile:
    s = info.serie
    angelegt = parse_iso(s.angelegt_am)
    zeile = _SerieZeile(
        info=info,
        art=s.art or ART_VORGABE,
        einzeln=bool(s.einzeln),
        heu=suchform(s.name),
        sortier=natuerlicher_schluessel(s.name),
        angelegt=angelegt.timestamp() if angelegt else 0.0,
        pruefen=bool(s.pruefen) or any(s.info(n).get("pruefen") for n in s.folgen),
    )
    for name, objekt in zip(s.folgen, info.folgen_objekte, strict=False):
        anzeige = objekt.get("anzeige") or name
        stamm, _, _ = name.rpartition(".")
        zeile.folgen.append(
            _FolgeZeile(
                name=name,
                anzeige=anzeige,
                heu=f"{suchform(anzeige)} {suchform(stamm or name)} {suchform(name)}",  # Titel, Dateiname ohne und mit Endung
                sortier=natuerlicher_schluessel(anzeige),
                objekt=objekt,
            )
        )
    return zeile


class Bibliothek:
    """Suche, Filter, Sortierung und Blättern über ``Medien.serien``."""

    def __init__(self, medien: Medien) -> None:
        self.medien = medien
        self._zeilen: dict[str, _SerieZeile] = {}

    # --- Aufbau ---------------------------------------------------------------------------------------

    def zeilen(self) -> list[_SerieZeile]:
        """Alle Einträge; nur die geänderten werden neu aufgebaut."""
        aktuell = self.medien.serien
        for sid in [sid for sid in self._zeilen if sid not in aktuell]:
            del self._zeilen[sid]
        aus: list[_SerieZeile] = []
        for sid, info in aktuell.items():
            z = self._zeilen.get(sid)
            if z is None or z.info is not info:
                z = self._zeilen[sid] = _serie_zeile(info)
            aus.append(z)
        return aus

    # --- Tobies (einmal je Anfrage, nicht je Eintrag) ---------------------------------------------------

    def tobie_zaehler(self) -> dict[str, int]:
        """Serien-ID -> Zahl der Tobies, deren Ziel auf den Eintrag oder eine Folge zeigt (``anzahl_tobies``)."""
        zaehler: dict[str, int] = {}
        for z in self._zuordnungen().values():
            ziel = z["ziel"]
            if ziel["typ"] in ("serie", "folge"):
                zaehler[ziel.get("serie")] = zaehler.get(ziel.get("serie"), 0) + 1
        return zaehler

    def _zuordnungen(self) -> dict[str, dict[str, Any]]:
        konfig = self.medien.hub.store.konfig
        return konfig["zuordnungen"] if konfig else {}

    def tobies_je_ziel(self) -> tuple[dict[str, bool], dict[tuple[str, str], list[dict[str, Any]]]]:
        """``(Serien-ID -> hat ganzen Tobie, (Serien-ID, Folge) -> Tobie-Kurzform)``, Tobies nach Kennung sortiert."""
        ganze: dict[str, bool] = {}
        je_folge: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for uid, z in sorted(self._zuordnungen().items()):
            ziel = z["ziel"]
            if ziel["typ"] == "serie":
                ganze[ziel["serie"]] = True
            elif ziel["typ"] == "folge":
                je_folge.setdefault((ziel["serie"], ziel["folge"]), []).append({"uid": uid, "name": z.get("name")})
        return ganze, je_folge

    # --- Gemeinsame Bedingungen -----------------------------------------------------------------------------

    @staticmethod
    def _neu_grenze() -> float:
        return (jetzt() - timedelta(days=NEU_TAGE)).timestamp()

    # --- serien/list ----------------------------------------------------------------------------------

    def serien(
        self,
        *,
        art: str | None = None,
        text: str | None = None,
        auch_folgen: bool = False,
        filter_: list[str] | None = None,
        sortierung: str = "name",
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[SerieInfo], int, bool, dict[str, int]]:
        """``(Einträge dieser Seite, gesamt nach Filter, weitere, Tobie-Zähler)``.

        Ohne ``limit`` kommt alles (``SERIEN_OHNE_LIMIT_MAX``), wie bis 11.11."""
        filter_ = filter_ or []
        worte = suchworte(text) if text else []
        zaehler = self.tobie_zaehler()
        grenze = self._neu_grenze() if "neu" in filter_ else 0.0
        treffer: list[_SerieZeile] = []
        for z in self.zeilen():
            if art is not None and z.art != art:
                continue
            if "sammlung" in filter_ and z.einzeln:
                continue
            if "einzeln" in filter_ and not z.einzeln:
                continue
            if "ohne_tobie" in filter_ and zaehler.get(z.info.serie.id, 0) > 0:
                continue
            if "neu" in filter_ and z.angelegt < grenze:
                continue
            if "pruefen" in filter_ and not z.pruefen:
                continue
            if worte and not (passt(worte, z.heu) or (auch_folgen and any(passt(worte, f.heu) for f in z.folgen))):
                continue
            treffer.append(z)
        if sortierung == "neu":
            treffer.sort(key=lambda z: z.sortier)
            treffer.sort(key=lambda z: z.angelegt, reverse=True)
        else:
            treffer.sort(key=lambda z: z.sortier)
        gesamt = len(treffer)
        if limit is None:
            limit = SERIEN_OHNE_LIMIT_MAX
        seite = treffer[offset:] if limit is None else treffer[offset : offset + limit]
        weitere = offset + len(seite) < gesamt
        return [z.info for z in seite], gesamt, weitere, zaehler

    # --- folgen/list ----------------------------------------------------------------------------------

    def folgen(
        self,
        *,
        art: str | None = None,
        text: str | None = None,
        filter_: list[str] | None = None,
        sortierung: str = "titel",
        limit: int = 60,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int, bool]:
        """``(Zeilen dieser Seite, gesamt, weitere)``; Zeilenform: Vertrag W, Befehl 37."""
        filter_ = filter_ or []
        worte = suchworte(text) if text else []
        ganze, je_folge = self.tobies_je_ziel()
        grenze = self._neu_grenze() if "neu" in filter_ else 0.0
        treffer: list[tuple[_SerieZeile, _FolgeZeile]] = []
        for z in self.zeilen():
            if art is not None and z.art != art:
                continue
            if "sammlung" in filter_ and z.einzeln:
                continue
            if "einzeln" in filter_ and not z.einzeln:
                continue
            if "neu" in filter_ and z.angelegt < grenze:
                continue
            sid = z.info.serie.id
            hat_ganzen = ganze.get(sid, False)
            for f in z.folgen:
                if worte and not passt(worte, f.heu):
                    continue
                if "ohne_tobie" in filter_ and (hat_ganzen or je_folge.get((sid, f.name))):
                    continue
                if "pruefen" in filter_ and not (z.info.serie.pruefen or f.objekt.get("pruefen")):
                    continue
                treffer.append((z, f))
        if sortierung == "neu":
            treffer.sort(key=lambda t: (t[0].sortier, t[1].sortier))
            treffer.sort(key=lambda t: t[0].angelegt, reverse=True)
        else:
            treffer.sort(key=lambda t: (t[1].sortier, t[0].sortier))
        gesamt = len(treffer)
        seite = treffer[offset : offset + limit]
        zeilen = []
        for z, f in seite:
            s = z.info.serie
            zeilen.append(
                {
                    "serie_id": s.id,
                    "serie_name": s.name,
                    "serie_einzeln": z.einzeln,
                    "art": z.art,
                    "folge": f.name,
                    "anzeige": f.anzeige,
                    "nummer": f.objekt.get("nummer"),
                    "kapitel": 0,  # die Kapitelliste kommt mit Paket A3b3; bis dahin „keine Liste“
                    "groesse_mb": round(f.objekt.get("groesse_bytes", 0) / (1024 * 1024), 1),
                    "tobies": list(je_folge.get((s.id, f.name), [])),
                    "serie_hat_tobie": ganze.get(s.id, False),
                }
            )
        return zeilen, gesamt, offset + len(seite) < gesamt
