"""Eingang: Einsortieren nach Metadaten (Entscheidung M; Vertrag W, Abschnitt 11 und 5.9).

Tobias legt Ordner oder Dateien in ``tobibox/eingang/``. Ein Durchlauf liest die Tags mit ``ffprobe``
(gehärtet, ``ffprobe.py``), gruppiert zu Alben (Album = Folge), bestimmt die Serie, die Reihenfolge und die
Namen, prüft auf Kopierschutz und Doppelte (SHA-256) und sortiert in ``medien/`` ein. Die Box-Seite bleibt
unverändert: Ergebnis sind Serien-Ordner mit ``serie.json`` und Dateien oder Folgen-Ordnern.

Reihenfolge der Schritte je Gruppe (11.11): berechnen, Serie anlegen, Dateien verschieben, ``serie.json``
schreiben, Index und Protokoll. Gesperrt wird in der Reihenfolge Eingang, dann Serie.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers.storage import Store

from . import dateien, ffprobe
from .const import (
    EINGANG_NACHPLAN_S,
    EINGANG_PROTOKOLL_MAX,
    EINGANG_RUHE_S,
    EINGANG_STILLE_S,
    EINGANG_TIEFE_MAX,
    INDEX_MAX,
    UPLOAD_SAMMELZEIT_S,
)
from .fehler import TobiboxFehler
from .media import (
    Serie,
    einfuege_index,
    lese_serie,
    papierkorb_anlegen,
    schreibe_serie,
)
from .namen import (
    NamenErschoepft,
    album_ohne_cd_zusatz,
    dateiname_bereinigen,
    datum_aus_tag,
    eindeutiger_name,
    ist_platzhalter,
    natuerlicher_schluessel,
    norm,
    nummer_aus_tag,
    nummer_aus_text,
    sortiere_natuerlich,
    trenne_endung,
    vergleichsschluessel,
    zahl_vor_slash,
)
from .util import iso, jetzt, jetzt_iso, neue_id12, neue_uuid, parse_iso

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "tobibox_eingang"
UEBERSPRUNGENE_EINTRAEGE = frozenset({"@recycle", "@eadir", "#recycle", "$recycle.bin", "lost+found", "@recently-snapshot"})

KENNZ_SCHWACH_SERIE = ("serie_aus_interpret", "serie_aus_ordner")


# --------------------------------------------------------------------------
# Datenklassen
# --------------------------------------------------------------------------


@dataclass
class Datei:
    """Eine Audiodatei im Eingang."""

    rel: str  # Pfad im Eintrag (bei losen Dateien der Dateiname)
    pfad: Path
    eintrag: str
    groesse: int
    mtime: float
    endung: str
    # Ergebnis der Analyse
    pruefung: ffprobe.Pruefung | None = None
    sha: str | None = None
    felder: dict[str, Any] = field(default_factory=dict)
    block: str | None = None  # kopierschutz, nicht_lesbar, probedekodierung_fehlgeschlagen
    doppelt: bool = False
    zielname: str = ""

    @property
    def name(self) -> str:
        return self.pfad.name

    @property
    def rel_eingang(self) -> str:
        return f"{self.eintrag}/{self.rel}" if self.rel != self.eintrag else self.eintrag


@dataclass
class ScanEintrag:
    name: str
    art: str  # datei oder ordner
    dateien: list[Datei]
    ignoriert: int
    groesse: int
    neueste_mtime: float
    anzahl_alle: int


@dataclass
class EintragZustand:
    """Was der letzte Durchlauf über einen Eintrag im Eingang weiß."""

    id: str
    name: str
    art: str
    zuerst_gesehen: str
    dateien: int = 0
    ignoriert: int = 0
    groesse_bytes: int = 0
    geaendert_am: str = ""
    status: str = "wartet"
    hinweise: list[dict[str, Any]] = field(default_factory=list)
    ergebnis: list[dict[str, Any]] = field(default_factory=list)
    fertig_am: str | None = None
    #: (Zeit, Anzahl, Größe) der letzten Scans für die Ruhezeit
    scans: list[tuple[float, int, int]] = field(default_factory=list)
    signatur: tuple = ()
    #: ``signatur`` zum Zeitpunkt, als der Eintrag zuletzt blockiert liegen blieb
    sig_bei_block: tuple | None = None

    def zu_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "art": self.art,
            "dateien": self.dateien,
            "ignoriert": self.ignoriert,
            "groesse_bytes": self.groesse_bytes,
            "zuerst_gesehen": self.zuerst_gesehen,
            "geaendert_am": self.geaendert_am,
            "status": self.status,
            "hinweise": list(self.hinweise),
            "ergebnis": list(self.ergebnis),
            "fertig_am": self.fertig_am,
        }


def eintrag_id(name: str) -> str:
    """Anfang der SHA-256 des Namens (stabil über Durchläufe), 12 Zeichen."""
    return hashlib.sha256(name.encode("utf-8", "surrogateescape")).hexdigest()[:12]


@dataclass
class Gruppe:
    """Eine Gruppe wird eine Folge (Vertrag W, 11.3)."""

    schluessel: tuple
    eintrag: str
    eintrag_art: str
    dateien: list[Datei]
    eingangsindex: int = 0
    kennz: list[str] = field(default_factory=list)
    # berechnet
    anzeige: str = ""
    nummer: int | None = None
    datum: str | None = None
    serie_name: str = ""
    serie_schwach: bool = False
    vorgabe_serie_id: str | None = None
    folge_name: str = ""
    ist_ordner: bool = False
    erste_pfad_schluessel: tuple = ()
    sortier: tuple = ()
    zielnamen: dict[str, str] = field(default_factory=dict)

    def merke(self, code: str) -> None:
        if code not in self.kennz:
            self.kennz.append(code)


# --------------------------------------------------------------------------
# Scan (synchron)
# --------------------------------------------------------------------------


def scan_eingang(eingang: Path) -> list[ScanEintrag]:
    """Liest die oberste Ebene von ``eingang/`` und die Audiodateien darin (bis 5 Ebenen tief)."""
    aus: list[ScanEintrag] = []
    eintraege = sorted(os.scandir(eingang), key=lambda e: natuerlicher_schluessel(e.name))
    for e in eintraege:
        if e.name.startswith(".") or e.name.lower() in UEBERSPRUNGENE_EINTRAEGE:
            continue
        pfad = Path(e.path)
        try:
            if e.is_dir():
                aus.append(_scan_ordner(pfad))
            elif e.is_file():
                st = e.stat()
                if dateien.ist_audio(e.name):
                    d = Datei(e.name, pfad, e.name, st.st_size, st.st_mtime, e.name.rpartition(".")[2].lower())
                    aus.append(ScanEintrag(e.name, "datei", [d], 0, st.st_size, st.st_mtime, 1))
                else:
                    aus.append(ScanEintrag(e.name, "datei", [], 1, 0, st.st_mtime, 1))
        except OSError as err:
            _LOGGER.warning("Eintrag %s im Eingang nicht lesbar: %s", e.name, err)
    return aus


def _scan_ordner(pfad: Path) -> ScanEintrag:
    audio: list[Datei] = []
    ignoriert = 0
    alle = 0
    neueste = pfad.stat().st_mtime
    for wurzel, ordner, namen in os.walk(pfad):
        tiefe = len(Path(wurzel).relative_to(pfad).parts)
        ordner[:] = [o for o in sorted(ordner, key=natuerlicher_schluessel) if not o.startswith(".")]
        if tiefe >= EINGANG_TIEFE_MAX:
            ordner[:] = []
        for n in sorted(namen, key=natuerlicher_schluessel):
            voll = Path(wurzel) / n
            try:
                st = voll.stat()
            except OSError:
                continue
            alle += 1
            neueste = max(neueste, st.st_mtime)
            if dateien.ist_audio(n):
                rel = voll.relative_to(pfad).as_posix()
                audio.append(Datei(rel, voll, pfad.name, st.st_size, st.st_mtime, n.rpartition(".")[2].lower()))
            else:
                ignoriert += 1
    audio.sort(key=lambda d: natuerlicher_schluessel(d.rel))
    return ScanEintrag(pfad.name, "ordner", audio, ignoriert, sum(d.groesse for d in audio), neueste, alle)


def analysiere_datei(d: Datei) -> None:
    """Prüft eine Datei nach D5 (``ffprobe`` gehärtet), liest die Tags und bildet die Prüfsumme."""
    p = ffprobe.pruefe_datei(d.pfad, d.endung)
    d.pruefung = p
    if p.probe.tags:  # auch bei Kopierschutz kennt ``ffprobe`` die Tags: die Datei gehört zu ihrem Album
        d.felder = tags_zu_feldern(p.probe.tags)
    if p.ergebnis == "nicht_moeglich":
        d.block = ffprobe.FFPROBE_FEHLT
    elif p.ergebnis == "ungueltig":
        d.block = ffprobe.NICHT_LESBAR
    elif p.ergebnis == "warnung":
        d.block = p.hinweis
    else:
        d.sha = ffprobe.pruefsumme(d.pfad)


def tags_zu_feldern(tags: dict[str, str]) -> dict[str, Any]:
    """Normierte Felder aus den Roh-Tags (Vertrag W, 11.2)."""
    album_roh = ffprobe.tag(tags, "album")
    album, cd = album_ohne_cd_zusatz(album_roh) if album_roh else ("", None)
    interpret = ffprobe.tag(tags, "interpret")
    album_interpret = ffprobe.tag(tags, "album_interpret")
    track_roh = ffprobe.tag(tags, "track")
    disc_roh = ffprobe.tag(tags, "disc")
    nummer_roh = ffprobe.tag(tags, "nummer_tag")
    datum_roh = ffprobe.tag(tags, "datum")
    return {
        "album": album,
        "cd": cd,
        "album_interpret": "" if ist_platzhalter(album_interpret) else album_interpret,
        "interpret": "" if ist_platzhalter(interpret) else interpret,
        "serien_tag": ffprobe.tag(tags, "serien_tag"),
        "nummer_tag": nummer_aus_tag(nummer_roh) if nummer_roh else None,
        "titel": ffprobe.tag(tags, "titel"),
        "track": zahl_vor_slash(track_roh) if track_roh else None,
        "disc": zahl_vor_slash(disc_roh) if disc_roh else None,
        "datum": datum_aus_tag(datum_roh) if datum_roh else None,
    }


# --------------------------------------------------------------------------
# Berechnen (rein)
# --------------------------------------------------------------------------


def mehrheit(werte: list[Any], schluessel=norm) -> tuple[Any | None, int]:
    """Mehrheit nach ``norm``; bei Gleichstand der Wert der ersten Datei. ``(Wert, Anzahl verschiedener Werte)``."""
    zaehler: dict[Any, int] = {}
    erster: dict[Any, Any] = {}
    for w in werte:
        if w in (None, ""):
            continue
        k = schluessel(w) if isinstance(w, str) else w
        zaehler[k] = zaehler.get(k, 0) + 1
        erster.setdefault(k, w)
    if not zaehler:
        return None, 0
    beste = max(zaehler, key=lambda k: (zaehler[k], -list(erster).index(k)))
    return erster[beste], len(zaehler)


def bilde_gruppen(eintraege: list[ScanEintrag], indizes: dict[str, int]) -> list[Gruppe]:
    """Gruppiert die Dateien der bereiten Einträge (Vertrag W, 11.3): Album = Folge."""
    gruppen: dict[tuple, Gruppe] = {}
    reihenfolge: list[tuple] = []

    def dazu(schluessel: tuple, e: ScanEintrag, d: Datei) -> None:
        if schluessel not in gruppen:
            gruppen[schluessel] = Gruppe(schluessel, e.name, e.art, [], eingangsindex=indizes.get(e.name, 0))
            reihenfolge.append(schluessel)
        gruppen[schluessel].dateien.append(d)

    for e in eintraege:
        for d in e.dateien:
            album = d.felder.get("album", "")
            if e.art == "ordner":
                dazu(("ordner", e.name, norm(album) if album else None), e, d)
            elif album:
                dazu(("lose", norm(album)), e, d)
            else:
                dazu(("datei", e.name), e, d)
    return [gruppen[k] for k in reihenfolge]


def berechne_gruppe(g: Gruppe, vorgaben: dict[str, str | None]) -> None:
    """Berechnet Folge, Nummer, Datum, Serie, Track-Reihenfolge und Namen einer Gruppe (11.4 bis 11.8)."""
    dateien_ = g.dateien
    felder = [d.felder for d in dateien_]
    hat_album = any(f.get("album") for f in felder)
    # --- Track-Reihenfolge (11.7) ---
    mit_track = [d for d in dateien_ if d.felder.get("track") is not None]
    hat_track = bool(mit_track)

    def disc_von(d: Datei) -> int:
        f = d.felder
        return f.get("disc") or f.get("cd") or 1

    def schluessel(d: Datei) -> tuple:
        pfad_s = natuerlicher_schluessel(d.rel)
        if hat_track:
            t = d.felder.get("track")
            return (0 if t is not None else 1, disc_von(d), t if t is not None else 0, pfad_s)
        return (0, 0, 0, pfad_s)

    dateien_.sort(key=schluessel)
    if hat_track:
        if len(mit_track) != len(dateien_):
            g.merke("track_teils_leer")
        paare = [(disc_von(d), d.felder["track"]) for d in dateien_ if d.felder.get("track") is not None]
        if len(set(paare)) != len(paare):
            g.merke("track_doppelt")
    # --- Album, Anzeige ---
    album_namen = [f["album"] for f in felder if f.get("album")]
    album = album_namen[0] if album_namen else ""
    g.ist_ordner = len(dateien_) > 1
    einzel = dateien_[0]
    if album:
        g.anzeige = album
    else:
        g.merke("tags_fehlen")
        titel = einzel.felder.get("titel", "") if not g.ist_ordner else ""
        if titel:
            g.anzeige = titel
        elif g.ist_ordner and g.eintrag_art == "ordner":
            g.anzeige = g.eintrag
        else:
            g.anzeige = trenne_endung(einzel.name)[0] if not g.ist_ordner else g.eintrag
    # --- Nummer (11.4, 11.8) ---
    nummer, vielfalt = mehrheit([f.get("nummer_tag") for f in felder], schluessel=lambda x: x)
    if vielfalt > 1:
        g.merke("nummer_widerspruch")
    if nummer is None and album:
        nummer = nummer_aus_text(album_namen[0])
    if nummer is None and not g.ist_ordner:
        titel = einzel.felder.get("titel", "")
        nummer = nummer_aus_text(titel) if titel else None
    g.nummer = nummer
    daten = [f["datum"] for f in felder if f.get("datum")]
    g.datum = min(daten) if daten else None
    # --- Serie (11.5, 11.8) ---
    vorgabe = next((vorgaben.get(d.rel_eingang) for d in dateien_ if vorgaben.get(d.rel_eingang)), None)
    g.vorgabe_serie_id = vorgabe
    serien_wert, n_serien = mehrheit([f.get("serien_tag") for f in felder])
    ai_wert, n_ai = mehrheit([f.get("album_interpret") for f in felder])
    if serien_wert:
        g.serie_name = serien_wert[:100]
        if n_serien > 1:
            g.merke("serie_widerspruch")
    elif ai_wert:
        g.serie_name = ai_wert[:100]
        if n_ai > 1:
            g.merke("serie_widerspruch")
    else:
        interpreten = [f.get("interpret", "") for f in felder]
        if all(interpreten) and len({norm(i) for i in interpreten}) == 1:
            g.serie_name = interpreten[0][:100]
            g.merke("serie_aus_interpret")
            g.serie_schwach = True
        elif g.eintrag_art == "ordner":
            g.serie_name = g.eintrag[:100]
            g.merke("serie_aus_ordner")
            g.serie_schwach = True
        else:
            g.serie_name = "Einzelfolgen"
            g.merke("serie_aus_ordner")
            g.serie_schwach = True
    g.erste_pfad_schluessel = natuerlicher_schluessel(dateien_[0].rel)
    g.sortier = (
        (0, g.nummer) if g.nummer is not None else (1, 0),
        g.datum or "9999-99-99",
        g.eingangsindex,
        g.erste_pfad_schluessel,
    )


def vergebe_namen(g: Gruppe) -> None:
    """Namen im Folgen-Ordner und Name der Folge (11.7, Abschnitt 12)."""
    if not g.ist_ordner:
        d = g.dateien[0]
        name, gekuerzt = dateiname_bereinigen(d.name, mit_endung=True)
        if not name:
            name, gekuerzt = "Unbenannt" + (f".{d.endung}" if d.endung else ""), True
        if gekuerzt:
            g.merke("name_geaendert")
        g.folge_name = name
        g.zielnamen = {d.rel: name}
        return
    ordner, gekuerzt = dateiname_bereinigen(g.anzeige, mit_endung=False)
    if not ordner:
        ordner, gekuerzt = "Unbenannt", True
    if gekuerzt:
        g.merke("name_geaendert")
    g.folge_name = ordner
    bereinigt: list[str] = []
    for d in g.dateien:
        n, k = dateiname_bereinigen(d.name, mit_endung=True)
        if not n:
            n, k = f"Unbenannt.{d.endung}", True
        if k:
            g.merke("name_geaendert")
        bereinigt.append(n)
    eindeutig = len({vergleichsschluessel(n) for n in bereinigt}) == len(bereinigt)
    natuerlich_ok = bereinigt == sortiere_natuerlich(bereinigt)
    if eindeutig and natuerlich_ok:
        namen = bereinigt
    else:
        breite = max(3, len(str(len(bereinigt))))
        namen = [f"{i:0{breite}d} {n}" for i, n in enumerate(bereinigt, start=1)]
    g.zielnamen = {d.rel: n for d, n in zip(g.dateien, namen, strict=True)}


# --------------------------------------------------------------------------
# Der Eingang
# --------------------------------------------------------------------------


class Eingang:
    """Zustand und Durchläufe des Eingangs (``eingang.py``)."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.pfade = hub.pfade
        self._store: Store[dict[str, Any]] = Store(hub.hass, 1, STORAGE_KEY)
        self.sperre = asyncio.Lock()
        self.eintraege: dict[str, EintragZustand] = {}
        self.geprueft_am: str | None = None
        self.laeuft = False
        self._task: asyncio.Task | None = None
        self.protokoll: list[dict[str, Any]] = []
        #: Prüfsumme -> {"p": Pfad unter ``medien/``, "s": Größe}
        self.index: dict[str, dict[str, Any]] = {}
        #: Pfad im Eingang -> {"serie_id", "gruppe"} (Vorgaben aus dem Upload)
        self.vorgaben: dict[str, dict[str, Any]] = {}
        self.upload_eintraege: set[str] = set()
        self._benachrichtigt: set[str] = set()
        self._nachholen: set[str] | None = None
        self._nachplan_abbruch = None
        self._upload_abbruch = None
        self._sofort_naechster = False

    # --- Speicher -----------------------------------------------------------------

    async def async_laden(self) -> None:
        daten = await self._store.async_load()
        if isinstance(daten, dict):
            self.protokoll = list(daten.get("protokoll") or [])
            self.index = dict(daten.get("index") or {})
            self.vorgaben = dict(daten.get("vorgaben") or {})

    def _daten(self) -> dict[str, Any]:
        return {"protokoll": self.protokoll, "index": self.index, "vorgaben": self.vorgaben}

    def speichern(self) -> None:
        self._store.async_delay_save(self._daten, 3.0)

    async def speichern_sofort(self) -> None:
        await self._store.async_save(self._daten())

    # --- Index (Prüfsumme -> Pfad unter medien/) ----------------------------------------

    def index_aufnehmen(self, sha: str, pfad_rel: str, groesse: int) -> None:
        self.index.pop(sha, None)
        self.index[sha] = {"p": pfad_rel, "s": groesse}
        while len(self.index) > INDEX_MAX:
            self.index.pop(next(iter(self.index)))
        self.speichern()

    def index_entferne_praefix(self, praefix: str) -> list[str]:
        """Entfernt Einträge, deren Datei unter ``praefix`` liegt; gibt ihre Prüfsummen zurück (für ``meta.json``)."""
        if praefix.endswith("/"):
            passt = lambda p: p.startswith(praefix)  # noqa: E731
        else:
            passt = lambda p: p == praefix or p.startswith(praefix + "/")  # noqa: E731
        weg = [sha for sha, e in self.index.items() if passt(e["p"])]
        for sha in weg:
            self.index.pop(sha, None)
        if weg:
            self.speichern()
        return weg

    def index_wiederherstellen(self, summen: list[str], praefix: str) -> None:
        """Nimmt die Prüfsummen einer wiederhergestellten Folge wieder in den Index auf (Vertrag W, 11.10)."""
        if not summen:
            return
        self.hub.hass.async_create_background_task(self._index_neu(set(summen), praefix), "tobibox_index")

    async def _index_neu(self, summen: set[str], praefix: str) -> None:
        wurzel = self.pfade.medien / praefix.rstrip("/")

        def lauf() -> list[tuple[str, str, int]]:
            treffer: list[tuple[str, str, int]] = []
            dateien_liste = [wurzel] if wurzel.is_file() else (
                [p for p in wurzel.rglob("*") if p.is_file() and dateien.ist_audio(p.name)] if wurzel.exists() else []
            )
            for p in dateien_liste:
                try:
                    sha = ffprobe.pruefsumme(p)
                except OSError:
                    continue
                if sha in summen:
                    treffer.append((sha, p.relative_to(self.pfade.medien).as_posix(), p.stat().st_size))
            return treffer

        for sha, rel, groesse in await self.hub.hass.async_add_executor_job(lauf):
            self.index_aufnehmen(sha, rel, groesse)

    def _index_treffer(self, sha: str) -> str | None:
        """Pfad der Datei in ``medien/``, wenn der Index sie kennt und sie noch dort liegt (gleiche Größe)."""
        e = self.index.get(sha)
        if not e:
            return None
        try:
            if (self.pfade.medien / e["p"]).stat().st_size == e["s"]:
                return e["p"]
        except OSError:
            pass
        return None

    # --- Liste ------------------------------------------------------------------------

    async def liste(self, filter_: str, limit: int, offset: int) -> dict[str, Any]:
        await self._stelle_gescannt_sicher()
        offen = [e for e in self.eintraege.values() if e.status != "erledigt"]
        offen.sort(key=lambda e: (parse_iso(e.zuerst_gesehen) or jetzt(), natuerlicher_schluessel(e.name)), reverse=True)
        erledigt = [dict(p) for p in reversed(self.protokoll)]
        if filter_ == "offen":
            alle = [e.zu_json() for e in offen]
        elif filter_ == "erledigt":
            alle = erledigt
        else:
            alle = [e.zu_json() for e in offen] + erledigt
        return {
            "eintraege": alle[offset : offset + limit],
            "gesamt": len(alle),
            "sortierung_laeuft": self.laeuft,
            "geprueft_am": self.geprueft_am,
        }

    async def _stelle_gescannt_sicher(self) -> None:
        if self.geprueft_am is not None:
            return
        try:
            scan = await self.hub.hass.async_add_executor_job(scan_eingang, self.pfade.eingang)
        except OSError as err:
            raise TobiboxFehler("medien_nicht_erreichbar") from err
        self._zustaende_aktualisieren(scan)
        self.geprueft_am = jetzt_iso()

    def zaehler_snapshot(self) -> dict[str, Any]:
        offen = [e for e in self.eintraege.values() if e.status != "erledigt"]
        return {
            "offen": len(offen),
            "blockiert": sum(1 for e in offen if e.status in ("blockiert", "teilweise")),
            "sortierung_laeuft": self.laeuft,
            "geprueft_am": self.geprueft_am,
        }

    # --- Zustände und Ruhezeit (Vertrag W, 11.1) --------------------------------------------------

    def _zustaende_aktualisieren(self, scan: list[ScanEintrag], sofort: bool = False) -> None:
        jetzt_s = jetzt().timestamp()
        vorhanden = {e.name for e in scan}
        for name in list(self.eintraege):
            if name not in vorhanden:
                z = self.eintraege.pop(name)
                self.vorgaben = {k: v for k, v in self.vorgaben.items() if not k.startswith(z.name + "/") and k != z.name}
                self.upload_eintraege.discard(name)
                self._benachrichtigt.discard(name)
        for e in scan:
            z = self.eintraege.get(e.name)
            if z is None:
                z = EintragZustand(eintrag_id(e.name), e.name, e.art, jetzt_iso())
                self.eintraege[e.name] = z
            z.art = e.art
            z.dateien = len(e.dateien)
            z.ignoriert = e.ignoriert
            z.groesse_bytes = e.groesse
            z.geaendert_am = iso(datetime.fromtimestamp(e.neueste_mtime, tz=UTC))
            z.scans.append((jetzt_s, len(e.dateien), e.groesse))
            del z.scans[:-20]
            z.signatur = (len(e.dateien), e.groesse, e.neueste_mtime)
            if z.status == "laeuft" or z.status in ("blockiert", "teilweise"):
                continue
            z.status = "bereit" if (self._ist_bereit(e) or sofort) else "wartet"

    def _ist_bereit(self, e: ScanEintrag) -> bool:
        """Ruhezeit (Vertrag W, 11.1): neueste Änderung mindestens 120 s her **und** Anzahl und Größe beim Scan davor gleich."""
        if e.name in self.upload_eintraege:
            return True
        z = self.eintraege[e.name]
        jetzt_s = jetzt().timestamp()
        if jetzt_s - e.neueste_mtime < EINGANG_RUHE_S:
            return False
        vorher = [s for s in z.scans[:-1] if jetzt_s - s[0] >= EINGANG_STILLE_S]
        return bool(vorher) and (vorher[-1][1], vorher[-1][2]) == (len(e.dateien), e.groesse)

    def _bereite(self, scan: list[ScanEintrag], ids: set[str] | None, sofort: bool) -> list[ScanEintrag]:
        aus = []
        for e in scan:
            z = self.eintraege[e.name]
            if ids is not None and z.id not in ids:
                continue
            if sofort:
                aus.append(e)
            elif z.status in ("blockiert", "teilweise"):
                # liegt geblieben: nur wieder anfassen, wenn sich etwas geändert hat oder Tobias es verlangt
                if ids is not None or z.signatur != z.sig_bei_block:
                    aus.append(e)
            elif self._ist_bereit(e):
                aus.append(e)
        return aus

    # --- Durchlauf starten --------------------------------------------------------------------------

    async def starte_durchlauf(self, eintrag_ids: list[str] | None = None, sofort: bool = False) -> dict[str, Any]:
        """Stößt einen Durchlauf an (Vertrag W, Nr. 30). Er läuft im Hintergrund und meldet sich als Ereignis."""
        if self.laeuft:
            if eintrag_ids:
                self._nachholen = (self._nachholen or set()) | set(eintrag_ids)
            if sofort:
                self._sofort_naechster = True
            return {"gestartet": False, "laeuft_bereits": True, "eintraege": 0}
        self.laeuft = True
        try:
            try:
                scan = await self.hub.hass.async_add_executor_job(scan_eingang, self.pfade.eingang)
            except OSError as err:
                raise TobiboxFehler("medien_nicht_erreichbar") from err
            ids = set(eintrag_ids) if eintrag_ids is not None else None
            self._zustaende_aktualisieren(scan, sofort=sofort)
            if ids is not None:
                bekannt = {z.id for z in self.eintraege.values()}
                if not ids <= bekannt:
                    raise TobiboxFehler("eintrag_nicht_gefunden")
            bereit = self._bereite(scan, ids, sofort)
            self.geprueft_am = jetzt_iso()
        except BaseException:
            self.laeuft = False
            raise
        self._task = self.hub.hass.async_create_background_task(self._durchlauf(scan, bereit), "tobibox_eingang")
        self.hub.emit("eingang", "geaendert", {})
        return {"gestartet": True, "laeuft_bereits": False, "eintraege": len(bereit)}

    async def durchlauf_und_warten(self, eintrag_ids: list[str] | None = None, sofort: bool = False) -> dict[str, Any]:
        """Wie ``starte_durchlauf``, wartet aber auf das Ende (Tests, Timer)."""
        erg = await self.starte_durchlauf(eintrag_ids, sofort)
        if erg["gestartet"] and self._task is not None:
            await self._task
        return erg

    @callback
    def plane_nach_upload(self) -> None:
        """20 s nach dem letzten Upload-Abschluss startet ein Durchlauf (Vertrag W, 5.9)."""
        if self._upload_abbruch is not None:
            self._upload_abbruch()

        async def los(_now: Any) -> None:
            self._upload_abbruch = None
            with contextlib.suppress(TobiboxFehler):
                await self.starte_durchlauf()

        self._upload_abbruch = self.hub.plane(UPLOAD_SAMMELZEIT_S, los)

    def _plane_nachlauf(self) -> None:
        if self._nachplan_abbruch is not None:
            self._nachplan_abbruch()
            self._nachplan_abbruch = None
        if not any(z.status == "wartet" for z in self.eintraege.values()):
            return

        async def los(_now: Any) -> None:
            self._nachplan_abbruch = None
            with contextlib.suppress(TobiboxFehler):
                await self.starte_durchlauf()

        self._nachplan_abbruch = self.hub.plane(EINGANG_NACHPLAN_S, los)

    def abbrechen(self) -> None:
        for fn in (self._nachplan_abbruch, self._upload_abbruch):
            if fn is not None:
                fn()
        self._nachplan_abbruch = self._upload_abbruch = None

    # --- Der Durchlauf -------------------------------------------------------------------------------

    async def _durchlauf(self, scan: list[ScanEintrag], bereit: list[ScanEintrag]) -> None:
        zaehler = {"eintraege": len(bereit), "folgen": 0, "serien_neu": 0, "pruefen": 0, "doppelt": 0, "blockiert": 0}
        try:
            async with self.sperre:
                await self._verarbeite(scan, bereit, zaehler)
        except Exception:
            _LOGGER.exception("Durchlauf des Eingangs fehlgeschlagen")
        finally:
            self.laeuft = False
            self.geprueft_am = jetzt_iso()
            for z in self.eintraege.values():
                if z.status == "laeuft":
                    z.status = "bereit"
            self.hub.emit("eingang", "durchlauf_fertig", {"geprueft_am": self.geprueft_am, "zaehler": zaehler})
            self.hub.emit("eingang", "geaendert", {})
            await self.speichern_sofort()
            nachholen, self._nachholen = self._nachholen, None
            sofort, self._sofort_naechster = self._sofort_naechster, False
            if nachholen or sofort:
                with contextlib.suppress(TobiboxFehler):
                    await self.starte_durchlauf(list(nachholen) if nachholen else None, sofort)
            else:
                self._plane_nachlauf()

    async def _verarbeite(self, scan: list[ScanEintrag], bereit: list[ScanEintrag], zaehler: dict[str, int]) -> None:
        hass = self.hub.hass
        if not bereit:
            return
        for e in bereit:
            self.eintraege[e.name].status = "laeuft"
            self.eintraege[e.name].hinweise = []
        self.hub.emit("eingang", "geaendert", {})
        # Ohne ffprobe gibt es keine Tags: der ganze Durchlauf bleibt liegen (11.10)
        if ffprobe.ffprobe_pfad() is None:
            for e in bereit:
                z = self.eintraege[e.name]
                z.status = "blockiert"
                z.hinweise = [self._hinweis("ffprobe_fehlt", None)]
                zaehler["blockiert"] += 1
            return
        # --- Analysieren (Prüfung, Tags, Prüfsumme) ---
        sem = asyncio.Semaphore(4)

        async def analysiere(d: Datei) -> None:
            async with sem:
                await hass.async_add_executor_job(analysiere_datei, d)

        alle_dateien = [d for e in bereit for d in e.dateien]
        await asyncio.gather(*(analysiere(d) for d in alle_dateien))
        # --- Gruppieren und berechnen ---
        indizes = self._eingangsindizes(scan)
        gruppen = bilde_gruppen(bereit, indizes)
        # Blockierte Dateien haben keine Tags und stehen im Ordner-Eintrag in der Gruppe "ohne album": eine
        # Datei, die blockiert ist, hält ihre Gruppe zurück. Gruppen mit blockierter Datei werden nicht berechnet.
        blockierte: list[Gruppe] = [g for g in gruppen if any(d.block for d in g.dateien)]
        gute = [g for g in gruppen if g not in blockierte]
        vorgaben = {k: v.get("serie_id") for k, v in self.vorgaben.items()}
        # Hinweise zu blockierten Dateien (Eintrag, Datei)
        hinweise_je_eintrag: dict[str, list[dict[str, Any]]] = {e.name: [] for e in bereit}
        for g in blockierte:
            for d in g.dateien:
                if d.block:
                    hinweise_je_eintrag[g.eintrag].append(self._hinweis(d.block, d.rel))
                    zaehler["blockiert"] += 1
        # --- Doppelte (Prüfsumme): vor dem Berechnen, damit eine Gruppe mit einer Datei übrig eine Datei-Folge wird ---
        gesehen: dict[str, Datei] = {}
        doppelte_je_eintrag: dict[str, list[Datei]] = {e.name: [] for e in bereit}
        for g in sorted(gute, key=lambda g: (g.eingangsindex, natuerlicher_schluessel(g.dateien[0].rel))):
            rest = []
            for d in g.dateien:
                if d.sha and (self._index_treffer(d.sha) or d.sha in gesehen):
                    d.doppelt = True
                    doppelte_je_eintrag[g.eintrag].append(d)
                else:
                    if d.sha:
                        gesehen[d.sha] = d
                    rest.append(d)
            if len(rest) != len(g.dateien) and rest:
                g.merke("teilweise_doppelt")
            g.dateien = rest
        gute = [g for g in gute if g.dateien]
        for g in gute:
            berechne_gruppe(g, vorgaben)
            vergebe_namen(g)
        # --- Serien bestimmen und einsortieren ---
        await self.hub.medien._stelle_geprueft_sicher()
        ergebnisse: dict[str, list[dict[str, Any]]] = {e.name: [] for e in bereit}
        verschoben_je_eintrag: dict[str, int] = {e.name: 0 for e in bereit}
        await self._sortiere_ein(gute, ergebnisse, verschoben_je_eintrag, hinweise_je_eintrag, zaehler)
        # --- Doppelte in den Papierkorb ---
        for name, liste in doppelte_je_eintrag.items():
            for d in liste:
                try:
                    await hass.async_add_executor_job(self._doppeltes_wegraeumen, d)
                except OSError as err:
                    _LOGGER.error("Doppeltes %s nicht in den Papierkorb gelegt: %s", d.pfad, err)
                    hinweise_je_eintrag[name].append(self._hinweis("verschieben_fehlgeschlagen", d.rel))
                    continue
                zaehler["doppelt"] += 1
                hinweise_je_eintrag[name].append(self._hinweis("doppelt", d.rel))
        # --- Abschluss je Eintrag: Reste, Status, Protokoll, Ereignisse ---
        for e in bereit:
            await self._schliesse_eintrag(e, ergebnisse[e.name], hinweise_je_eintrag[e.name], zaehler)
        self.hub.emit("medien", "papierkorb_geaendert", {})

    def _eingangsindizes(self, scan: list[ScanEintrag]) -> dict[str, int]:
        zustand = [self.eintraege[e.name] for e in scan if e.name in self.eintraege]
        zustand.sort(key=lambda z: (parse_iso(z.zuerst_gesehen) or jetzt(), natuerlicher_schluessel(z.name)))
        return {z.name: i for i, z in enumerate(zustand)}

    def _hinweis(self, code: str, datei: str | None) -> dict[str, Any]:
        return {"code": code, "datei": datei, "text": self.hub.t(f"hinweis_{code}", datei=datei or "", folge=datei or "")}

    # --- Einsortieren ------------------------------------------------------------------------------------

    async def _sortiere_ein(
        self,
        gruppen: list[Gruppe],
        ergebnisse: dict[str, list[dict[str, Any]]],
        verschoben: dict[str, int],
        hinweise: dict[str, list[dict[str, Any]]],
        zaehler: dict[str, int],
    ) -> None:
        medien = self.hub.medien
        # Serienschlüssel (11.5): norm(name) von Anzeigename oder Ordnername einer vorhandenen normalen Serie
        vorhandene: dict[str, list[Any]] = {}
        for info in medien.serien.values():
            if info.serie.typ != "normal":
                continue
            for k in {norm(info.serie.name), norm(info.ordner)}:
                vorhandene.setdefault(k, []).append(info)
        je_serie: dict[str, dict[str, Any]] = {}
        for g in sorted(gruppen, key=lambda g: g.sortier):
            ziel_id: str | None = None
            neue_serie_key: str | None = None
            if g.vorgabe_serie_id:
                if g.vorgabe_serie_id in medien.serien:
                    ziel_id = g.vorgabe_serie_id
                else:
                    g.merke("vorgabe_serie_fehlt")
                    hinweise[g.eintrag].append(self._hinweis("vorgabe_serie_fehlt", g.dateien[0].rel))
                    g.vorgabe_serie_id = None
            if ziel_id is None:
                schluessel = norm(g.serie_name)
                treffer = vorhandene.get(schluessel, [])
                if treffer:
                    treffer = sorted({id(t): t for t in treffer}.values(), key=lambda i: (parse_iso(i.serie.angelegt_am) or jetzt(), i.ordner))
                    ziel_id = treffer[0].serie.id
                    if len(treffer) > 1:
                        g.merke("serie_mehrdeutig")
                else:
                    neue_serie_key = schluessel
            if ziel_id is not None:
                eintrag = je_serie.setdefault(ziel_id, {"id": ziel_id, "neu": False, "gruppen": []})
            else:
                key = f"neu:{neue_serie_key}"
                eintrag = je_serie.setdefault(key, {"id": None, "neu": True, "name": g.serie_name, "gruppen": [], "schwach": []})
            eintrag["gruppen"].append(g)
            if eintrag["neu"] and g.serie_schwach:
                for c in g.kennz:
                    if c in KENNZ_SCHWACH_SERIE and c not in eintrag["schwach"]:
                        eintrag["schwach"].append(c)
        # Serien abarbeiten: eine Sperre nach der anderen, Eingang ist schon gesperrt (Reihenfolge Eingang, Serie)
        for key in sorted(je_serie, key=lambda k: (k.startswith("neu:"), k)):
            eintrag = je_serie[key]
            try:
                await self._serie_abarbeiten(eintrag, ergebnisse, verschoben, hinweise, zaehler)
            except TobiboxFehler as err:
                _LOGGER.warning("Einsortieren in eine Serie fehlgeschlagen: %s", err.code)
                for g in eintrag["gruppen"]:
                    hinweise[g.eintrag].append(self._hinweis("verschieben_fehlgeschlagen", g.dateien[0].rel))

    async def _serie_abarbeiten(
        self,
        eintrag: dict[str, Any],
        ergebnisse: dict[str, list[dict[str, Any]]],
        verschoben: dict[str, int],
        hinweise: dict[str, list[dict[str, Any]]],
        zaehler: dict[str, int],
    ) -> None:
        hass = self.hub.hass
        medien = self.hub.medien
        gruppen: list[Gruppe] = sorted(eintrag["gruppen"], key=lambda g: g.sortier)
        neu = eintrag["neu"]
        if neu:
            name = eintrag["name"]
            ordner_wunsch, _ = dateiname_bereinigen(name, mit_endung=False, fuer_serienordner=True)
            if not ordner_wunsch:
                ordner_wunsch = "Unbenannt"
            sid = neue_id12()
            sperre_id = sid
        else:
            sperre_id = eintrag["id"]
        async with medien.sperren(sperre_id):
            try:
                if neu:
                    ordner = await hass.async_add_executor_job(medien._lege_ordner_an, ordner_wunsch)
                    serie = Serie(id=sid, name=name[:100], typ="normal", angelegt_am=jetzt_iso(), ordner=ordner)
                    if eintrag["schwach"]:
                        serie.pruefen = True
                        serie.pruefen_gruende = list(eintrag["schwach"])
                    pfad = medien.pfad_serie(ordner)
                    await hass.async_add_executor_job(schreibe_serie, pfad, serie)
                else:
                    serie, pfad = await medien._frisch(eintrag["id"])
                    ordner = pfad.name
            except (OSError, NamenErschoepft) as err:
                raise medien._fehler_schreiben(err) from err
            neue_folgen: list[tuple[Gruppe, str]] = []
            for g in gruppen:
                try:
                    endname, index_neu = await hass.async_add_executor_job(self._verschiebe_gruppe, g, pfad, serie)
                    for sha, rel, groesse in index_neu:
                        self.index_aufnehmen(sha, rel, groesse)
                except _GleicherInhalt as gleich:
                    try:
                        await hass.async_add_executor_job(self._doppeltes_wegraeumen, gleich.datei)
                    except OSError:
                        hinweise[g.eintrag].append(self._hinweis("verschieben_fehlgeschlagen", gleich.datei.rel))
                    else:
                        zaehler["doppelt"] += 1
                        hinweise[g.eintrag].append(self._hinweis("doppelt", gleich.datei.rel))
                    continue
                except (OSError, NamenErschoepft, dateien.ZielExistiert) as err:
                    _LOGGER.error("Gruppe %s nicht verschoben: %s", g.anzeige, err)
                    hinweise[g.eintrag].append(self._hinweis("verschieben_fehlgeschlagen", g.dateien[0].rel))
                    continue
                neue_folgen.append((g, endname))
            # Reihenfolge und folgen_info (11.6): neue Serie in Sortierreihenfolge, vorhandene einzeln einfügen
            zahlen_vorher = [serie.info(n).get("nummer") for n in serie.folgen]
            for g, endname in neue_folgen:
                if any(vergleichsschluessel(serie.anzeige(n)) == vergleichsschluessel(g.anzeige) for n in serie.folgen):
                    g.merke("folge_gleicher_name")
            nummern = [z for z in zahlen_vorher if isinstance(z, int)] + [g.nummer for g, _ in neue_folgen if g.nummer is not None]
            for g, _ in neue_folgen:
                if g.nummer is not None and nummern.count(g.nummer) > 1:
                    g.merke("nummer_doppelt")
            for g, endname in neue_folgen:
                info: dict[str, Any] = {"anzeige": g.anzeige[:200]}
                if g.nummer is not None:
                    info["nummer"] = g.nummer
                if g.datum:
                    info["datum"] = g.datum
                if g.kennz:
                    info["pruefen"] = True
                    info["pruefen_gruende"] = list(g.kennz)
                pos = len(serie.folgen) if neu else einfuege_index(serie.folgen, serie.folgen_info, g.nummer)
                serie.folgen.insert(pos, endname)
                serie.folgen_info[endname] = info
            try:
                await hass.async_add_executor_job(schreibe_serie, pfad, serie)
            except OSError as err:
                raise medien._fehler_schreiben(err) from err
            serie.ordner = ordner
            await medien._aktualisiere_cache(serie, ordner)
            for g, endname in neue_folgen:
                tracks = len(g.dateien)
                zaehler["folgen"] += 1
                if g.kennz:
                    zaehler["pruefen"] += 1
                verschoben[g.eintrag] += tracks
                ergebnisse[g.eintrag].append(
                    {
                        "serie_id": serie.id,
                        "serie_name": serie.name,
                        "serie_neu": bool(neu),
                        "folge": endname,
                        "anzeige": g.anzeige[:200],
                        "tracks": tracks,
                        "pruefen": bool(g.kennz),
                        "pruefen_gruende": list(g.kennz),
                    }
                )
            if neu and neue_folgen:
                zaehler["serien_neu"] += 1
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie.id]})

    def _verschiebe_gruppe(self, g: Gruppe, serie_pfad: Path, serie: Serie) -> tuple[str, list[tuple[str, str, int]]]:
        """Verschiebt die Dateien einer Gruppe in den Serien-Ordner (11.11, Schritt 3).

        Läuft im Executor und fasst deshalb den Index nicht an. Gibt ``(Folgen-Name, Index-Einträge)`` zurück,
        die der Aufrufer in der Ereignisschleife aufnimmt."""
        ordner = serie_pfad.name
        if not g.ist_ordner:
            d = g.dateien[0]
            for _ in range(5):
                belegt = {vergleichsschluessel(e.name) for e in os.scandir(serie_pfad)} | {
                    vergleichsschluessel(n) for n in serie.folgen
                }
                name = eindeutiger_name(g.zielnamen[d.rel], belegt, mit_endung=True)
                # gleicher Name, gleicher Inhalt im Ziel: ein Doppeltes (Vertrag W, 11.10 (c))
                gleichnamig = next((e for e in os.scandir(serie_pfad) if vergleichsschluessel(e.name) == vergleichsschluessel(g.zielnamen[d.rel])), None)
                if gleichnamig and gleichnamig.is_file() and d.sha and gleichnamig.stat().st_size == d.groesse:
                    if ffprobe.pruefsumme(gleichnamig.path) == d.sha:
                        d.doppelt = True
                        raise _GleicherInhalt(d)
                try:
                    dateien.verschiebe_ohne_ueberschreiben(d.pfad, serie_pfad / name)
                except dateien.ZielExistiert:
                    continue
                return name, ([(d.sha, f"{ordner}/{name}", d.groesse)] if d.sha else [])
            raise dateien.ZielExistiert(g.zielnamen[d.rel])
        # Folgen-Ordner: zuerst vollständig unter _upload/<zufall>/ aufbauen, dann als Ganzes umbenennen
        staging = self.pfade.upload / dateien.zufall_hex(8)
        staging.mkdir(parents=True)
        verschoben: list[tuple[Path, Path]] = []
        try:
            for d in g.dateien:
                ziel = staging / g.zielnamen[d.rel]
                dateien.verschiebe_ohne_ueberschreiben(d.pfad, ziel)
                verschoben.append((d.pfad, ziel))
            for _ in range(5):
                belegt = {vergleichsschluessel(e.name) for e in os.scandir(serie_pfad)} | {
                    vergleichsschluessel(n) for n in serie.folgen
                }
                name = eindeutiger_name(g.folge_name, belegt, mit_endung=False)
                try:
                    dateien.verschiebe_ohne_ueberschreiben(staging, serie_pfad / name)
                    break
                except dateien.ZielExistiert:
                    continue
            else:
                raise dateien.ZielExistiert(g.folge_name)
        except BaseException:
            for quelle, ziel in reversed(verschoben):
                with contextlib.suppress(OSError):
                    os.rename(ziel, quelle)
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return name, [(d.sha, f"{ordner}/{name}/{g.zielnamen[d.rel]}", d.groesse) for d in g.dateien if d.sha]

    def _doppeltes_wegraeumen(self, d: Datei) -> None:
        papierkorb_anlegen(
            self.pfade.papierkorb,
            d.pfad,
            typ="eingang",
            grund="doppelt",
            serie_id=None,
            serie_name=None,
            serie_ordner=None,
        )

    # --- Eintrag abschließen ----------------------------------------------------------------------------------

    async def _schliesse_eintrag(
        self, e: ScanEintrag, ergebnis: list[dict[str, Any]], hinweise: list[dict[str, Any]], zaehler: dict[str, int]
    ) -> None:
        hass = self.hub.hass
        z = self.eintraege[e.name]
        z.ergebnis = ergebnis
        z.hinweise = hinweise
        pfad = self.pfade.eingang / e.name
        rest = await hass.async_add_executor_job(self._audio_uebrig, pfad)
        if not e.dateien:
            z.hinweise = [self._hinweis("keine_audiodateien", None)]
            z.status = "blockiert"
            zaehler["blockiert"] += 1
        elif rest:
            z.status = "teilweise" if ergebnis else "blockiert"
        else:
            z.status = "erledigt"
        if z.status == "erledigt":
            await hass.async_add_executor_job(self._raeume_rest, e)
            z.fertig_am = jetzt_iso()
            self.protokoll.append(z.zu_json())
            del self.protokoll[:-EINGANG_PROTOKOLL_MAX]
            self.eintraege.pop(e.name, None)
            self._benachrichtigt.discard(e.name)
            self.upload_eintraege.discard(e.name)
            self.vorgaben = {k: v for k, v in self.vorgaben.items() if not k.startswith(e.name + "/") and k != e.name}
        elif ergebnis:
            z.fertig_am = jetzt_iso()
        if z.status in ("blockiert", "teilweise"):
            self.upload_eintraege.discard(e.name)
            z.sig_bei_block = z.signatur
            await self._benachrichtige_blockiert(z)
        if ergebnis or z.status == "erledigt":
            self.hub.emit(
                "eingang",
                "neu_einsortiert",
                {
                    "eintrag_id": z.id,
                    "eintrag_name": z.name,
                    "ergebnis": ergebnis,
                    "hinweise": hinweise,
                    "zaehler": {
                        "folgen": len(ergebnis),
                        "serien_neu": sum(1 for r in ergebnis if r["serie_neu"]),
                        "pruefen": sum(1 for r in ergebnis if r["pruefen"]),
                        "doppelt": sum(1 for h in hinweise if h["code"] == "doppelt"),
                        "blockiert": sum(1 for h in hinweise if h["code"] in ("kopierschutz", "nicht_lesbar", "probedekodierung_fehlgeschlagen")),
                    },
                },
            )
        self.speichern()

    async def _benachrichtige_blockiert(self, z: EintragZustand) -> None:
        if z.name in self._benachrichtigt:
            return
        self._benachrichtigt.add(z.name)
        gruende = ", ".join(sorted({h["code"] for h in z.hinweise})) or "?"
        self.hub.benachrichtige(
            f"tobibox_eingang_{z.id}",
            "benachrichtigung_eingang_blockiert_titel",
            "benachrichtigung_eingang_blockiert",
            name=z.name,
            gruende=gruende,
        )

    @staticmethod
    def _audio_uebrig(pfad: Path) -> bool:
        if pfad.is_file():
            return dateien.ist_audio(pfad.name)
        if not pfad.exists():
            return False
        for _wurzel, ordner, namen in os.walk(pfad):
            ordner[:] = [o for o in ordner if not o.startswith(".")]
            if any(dateien.ist_audio(n) for n in namen):
                return True
        return False

    def _raeume_rest(self, e: ScanEintrag) -> None:
        """Nichts blockiert und nichts mehr zu sortieren: Reste in den Papierkorb, leere Ordner löschen (11.10)."""
        pfad = self.pfade.eingang / e.name
        if not pfad.exists():
            return
        if pfad.is_file():
            if dateien.ist_audio(pfad.name):  # pragma: no cover - kann nach dem Verschieben nicht vorkommen
                return
            papierkorb_anlegen(self.pfade.papierkorb, pfad, typ="eingang", grund="eingang_rest", serie_id=None, serie_name=None, serie_ordner=None)
            return
        # leere Unterordner löschen (von unten nach oben)
        for wurzel, _ordner, _namen in os.walk(pfad, topdown=False):
            with contextlib.suppress(OSError):
                if wurzel != str(pfad):
                    os.rmdir(wurzel)
        wichtig = [p for p in pfad.rglob("*") if p.is_file() and not p.name.startswith(".")]
        if not wichtig:
            shutil.rmtree(pfad, ignore_errors=True)  # nur Dotfiles (``._*``) oder leer: kein Papierkorb-Eintrag
            return
        papierkorb_anlegen(self.pfade.papierkorb, pfad, typ="eingang", grund="eingang_rest", serie_id=None, serie_name=None, serie_ordner=None)

    # --- Upload (http.py) ----------------------------------------------------------------------------------------

    def registriere_upload(self, rel: str, serie_id: str | None, gruppe: str | None) -> None:
        """Hält Vorgaben eines hochgeladenen Eintrags fest und plant das Einsortieren."""
        top = rel.split("/", 1)[0]
        self.upload_eintraege.add(top)
        if serie_id or gruppe:
            self.vorgaben[rel] = {"serie_id": serie_id, "gruppe": gruppe}
        self.speichern()
        self.plane_nach_upload()
        self.hub.emit("eingang", "geaendert", {})


class _GleicherInhalt(Exception):
    """Interner Abbruch: gleichnamige Datei mit gleichem Inhalt im Ziel (ein Doppeltes)."""

    def __init__(self, datei: Datei) -> None:
        super().__init__(datei.name)
        self.datei = datei
