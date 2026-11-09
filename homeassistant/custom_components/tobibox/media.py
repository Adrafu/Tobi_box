"""Medienverwaltung auf der NAS-Freigabe (Vertrag W, 3.2, 3.3, Abschnitt 12; ``data-model.md`` Abschnitte 5 und 9).

Die Integration ist der **einzige Schreiber** von ``serie.json`` (D1, D2). Dieses Modul

* liest und schreibt ``serie.json`` (atomar, mit ``folgen_info``, ``pruefen`` und unbekannten Feldern),
* prüft die Freigabe (neue Ordner und Dateien, fehlende Folgen, doppelte IDs, Kopierschutz nach D5),
* legt Serien an und ändert sie (umbenennen, ordnen, löschen, verschieben, zusammenführen),
* verwaltet den Papierkorb mit ``meta.json`` (Löschen, Wiederherstellen, Leeren).

Alle Dateizugriffe laufen über ``hass.async_add_executor_job``. Sperren: eine je Serie (Schlüssel = Serien-ID),
Reihenfolge beim Nehmen mehrerer Sperren nach Serien-ID aufsteigend (Vertrag W, Abschnitt 1).
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import dateien, ffprobe
from .const import (
    ENDUNGEN,
    FOLGE_ANZEIGE_MAX,
    ORDNER_EINGANG,
    ORDNER_PAPIERKORB,
    ORDNER_UPLOAD,
    PART_MAX_ALTER_S,
    RE_ID12,
    SERIE_JSON,
    SERIE_NAME_MAX,
)
from .fehler import TobiboxFehler
from .namen import (
    NamenErschoepft,
    anzeigename,
    anzeigename_streng,
    dateiname_bereinigen,
    eindeutiger_name,
    natuerlicher_schluessel,
    sortiere_natuerlich,
    vergleichsschluessel,
)
from .util import fingerabdruck, jetzt, jetzt_iso, neue_id12, parse_iso

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

SERIE_SCHEMA = 1
FOLGE_INFO_FELDER = ("anzeige", "nummer", "datum", "pruefen", "pruefen_gruende")


# --------------------------------------------------------------------------
# Reservierte Namen
# --------------------------------------------------------------------------


def name_pruefen(text: Any, max_zeichen: int) -> str:
    """Anzeigename prüfen (Regel 8): Steuerzeichen entfernt, Leerraum gekürzt; leer oder zu lang: ``name_ungueltig``."""
    name = anzeigename_streng(text, max_zeichen)
    if name is None:
        raise TobiboxFehler("name_ungueltig")
    return name


def ist_reserviert(ordnername: str) -> bool:
    """Ordner mit ``_`` am Anfang und der Name ``eingang`` sind keine Serien (Vertrag W, Abschnitt 12)."""
    return ordnername.startswith("_") or ordnername.lower() == ORDNER_EINGANG


def ist_systemordner(ordnername: str) -> bool:
    return ordnername in (ORDNER_PAPIERKORB, ORDNER_UPLOAD)


def gueltige_serien_id(x: Any) -> bool:
    return isinstance(x, str) and 1 <= len(x) <= 64 and "/" not in x and not any(ord(c) < 32 or ord(c) == 127 for c in x)


# --------------------------------------------------------------------------
# serie.json
# --------------------------------------------------------------------------


@dataclass
class Serie:
    """Inhalt einer ``serie.json`` (``data-model.md`` Abschnitt 5)."""

    id: str
    name: str
    typ: str
    angelegt_am: str
    folgen: list[str] = field(default_factory=list)
    pruefen: bool = False
    pruefen_gruende: list[str] = field(default_factory=list)
    folgen_info: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: unbekannte Felder der Datei, die beim Schreiben erhalten bleiben (data-model.md, 1.4)
    extra: dict[str, Any] = field(default_factory=dict)
    ordner: str = ""

    def bereinige(self) -> None:
        """Doppelte Namen in ``folgen`` zählen einmal; ``folgen_info`` nur für vorhandene Namen."""
        gesehen: set[str] = set()
        self.folgen = [n for n in self.folgen if not (n in gesehen or gesehen.add(n))]
        self.folgen_info = {n: i for n, i in self.folgen_info.items() if n in gesehen}

    def to_json(self) -> dict[str, Any]:
        self.bereinige()
        aus: dict[str, Any] = {
            "schema_version": SERIE_SCHEMA,
            "id": self.id,
            "name": self.name,
            "typ": self.typ,
            "folgen": list(self.folgen),
            "angelegt_am": self.angelegt_am,
        }
        if self.pruefen:
            aus["pruefen"] = True
            aus["pruefen_gruende"] = list(self.pruefen_gruende)
        if self.folgen_info:
            aus["folgen_info"] = {n: self.folgen_info[n] for n in self.folgen if n in self.folgen_info}
        aus.update(self.extra)
        return aus

    @property
    def stand(self) -> str:
        """Fingerabdruck von ``name``, ``folgen`` und ``folgen_info`` (16 Zeichen)."""
        self.bereinige()
        return fingerabdruck({"name": self.name, "folgen": self.folgen, "folgen_info": self.folgen_info})

    def info(self, name: str) -> dict[str, Any]:
        return self.folgen_info.get(name, {})

    def anzeige(self, name: str) -> str:
        return self.info(name).get("anzeige") or anzeige_aus_name(name)

    def setze_info(self, name: str, **felder: Any) -> None:
        info = dict(self.folgen_info.get(name, {}))
        for k, v in felder.items():
            if v is None or v is False or v == []:
                info.pop(k, None)
                if k == "pruefen":
                    info.pop("pruefen_gruende", None)
            else:
                info[k] = v
        if info:
            self.folgen_info[name] = info
        else:
            self.folgen_info.pop(name, None)

    def loesche_pruefen(self, name: str) -> None:
        self.setze_info(name, pruefen=None)


def anzeige_aus_name(name: str) -> str:
    """Anzeigename ohne Endung (Vertrag W, 3.2, Folge-Objekt)."""
    stamm, _, endung = name.rpartition(".")
    return stamm if stamm and endung.lower() in ENDUNGEN else name


def _bereinige_info(roh: Any) -> dict[str, Any]:
    if not isinstance(roh, dict):
        return {}
    info = dict(roh)
    if "anzeige" in info and not (isinstance(info["anzeige"], str) and 1 <= len(info["anzeige"]) <= FOLGE_ANZEIGE_MAX):
        info.pop("anzeige")
    if "nummer" in info and not (isinstance(info["nummer"], int) and not isinstance(info["nummer"], bool) and info["nummer"] >= 0):
        info.pop("nummer")
    if "datum" in info and not isinstance(info["datum"], str):
        info.pop("datum")
    if "pruefen" in info and not isinstance(info["pruefen"], bool):
        info.pop("pruefen")
    if "pruefen_gruende" in info and not (
        isinstance(info["pruefen_gruende"], list) and all(isinstance(g, str) for g in info["pruefen_gruende"])
    ):
        info.pop("pruefen_gruende")
    return info


def serie_aus_json(roh: Any, ordner: str) -> Serie | None:
    """Prüft eine gelesene ``serie.json``. ``None``, wenn sie ungültig ist (die Box behandelt sie dann wie fehlend)."""
    if not isinstance(roh, dict) or roh.get("schema_version") != SERIE_SCHEMA:
        return None
    sid, name, typ, folgen, am = roh.get("id"), roh.get("name"), roh.get("typ"), roh.get("folgen"), roh.get("angelegt_am")
    if not gueltige_serien_id(sid) or not isinstance(name, str) or not 1 <= len(name) <= SERIE_NAME_MAX:
        return None
    if typ not in ("normal", "ueberraschung") or not isinstance(folgen, list) or parse_iso(am) is None:
        return None
    if not all(isinstance(n, str) and n and "/" not in n and "\\" not in n and n not in (".", "..") for n in folgen):
        return None
    bekannt = {"schema_version", "id", "name", "typ", "folgen", "angelegt_am", "pruefen", "pruefen_gruende", "folgen_info"}
    s = Serie(
        id=sid,
        name=name,
        typ=typ,
        angelegt_am=am,
        folgen=list(folgen),
        pruefen=roh.get("pruefen") is True,
        pruefen_gruende=[g for g in roh.get("pruefen_gruende", []) if isinstance(g, str)]
        if isinstance(roh.get("pruefen_gruende"), list)
        else [],
        folgen_info={n: _bereinige_info(i) for n, i in (roh.get("folgen_info") or {}).items() if isinstance(n, str)}
        if isinstance(roh.get("folgen_info"), dict)
        else {},
        extra={k: v for k, v in roh.items() if k not in bekannt},
        ordner=ordner,
    )
    s.bereinige()
    return s


def lese_serie(ordner_pfad: Path) -> tuple[Serie | None, bool]:
    """``(Serie, vorhanden)``: ``vorhanden`` ist ``True``, wenn die Datei da ist (auch ungültig)."""
    datei = ordner_pfad / SERIE_JSON
    if not datei.exists():
        return None, False
    try:
        roh = dateien.lese_json(datei)
    except (OSError, ValueError):
        return None, True
    return serie_aus_json(roh, ordner_pfad.name), True


def schreibe_serie(ordner_pfad: Path, serie: Serie) -> None:
    dateien.schreibe_json_atomar(ordner_pfad / SERIE_JSON, serie.to_json())


# --------------------------------------------------------------------------
# Folgen auf der Platte
# --------------------------------------------------------------------------


def stat_folge(ordner_pfad: Path, name: str) -> tuple[str, int, int, bool]:
    """``(art, tracks, groesse_bytes, vorhanden)`` einer Folge."""
    pfad = ordner_pfad / name
    try:
        if pfad.is_dir():
            tracks = dateien.tracks_in_ordner(pfad)
            groesse = 0
            for t in tracks:
                with contextlib.suppress(OSError):
                    groesse += (pfad / t).stat().st_size
            return "ordner", max(len(tracks), 1), groesse, bool(tracks)
        st = pfad.stat()
        return "datei", 1, st.st_size, True
    except OSError:
        return "datei", 1, 0, False


def liste_auf_platte(ordner_pfad: Path) -> list[str]:
    """Audiodateien und Unterordner mit mindestens einem Track (kein Dotfile), natürlich sortiert."""
    namen: list[str] = []
    try:
        eintraege = list(os.scandir(ordner_pfad))
    except OSError:
        return []
    for e in eintraege:
        if e.name.startswith(".") or e.name == SERIE_JSON:
            continue
        try:
            if e.is_file() and dateien.ist_audio(e.name):
                namen.append(e.name)
            elif e.is_dir() and dateien.tracks_in_ordner(Path(e.path)):
                namen.append(e.name)
        except OSError:
            continue
    return sortiere_natuerlich(namen)


def pruefung_signatur(pfad: Path) -> tuple:
    try:
        if pfad.is_dir():
            return tuple(sorted((t, (pfad / t).stat().st_mtime_ns, (pfad / t).stat().st_size) for t in dateien.tracks_in_ordner(pfad)))
        st = pfad.stat()
        return ((pfad.name, st.st_mtime_ns, st.st_size),)
    except OSError:
        return ()


def pruefe_folge_pfad(pfad: Path) -> tuple[str, str | None]:
    """D5 für eine Datei oder einen Folgen-Ordner: ``("ok" | "warnung" | "nicht_moeglich", Code)``."""
    dateien_liste = [pfad] if pfad.is_file() else [pfad / t for t in dateien.tracks_in_ordner(pfad)]
    schlimmster: tuple[str, str | None] = ("ok", None)
    for d in dateien_liste:
        p = ffprobe.pruefe_datei(d)
        if p.ergebnis == "nicht_moeglich":
            return "nicht_moeglich", "pruefung_nicht_moeglich"
        if p.ergebnis in ("warnung", "ungueltig") and schlimmster[0] == "ok":
            schlimmster = ("warnung", p.hinweis if p.ergebnis == "warnung" else ffprobe.NICHT_LESBAR)
    return schlimmster


# --------------------------------------------------------------------------
# Papierkorb (data-model.md, Abschnitt 9)
# --------------------------------------------------------------------------


def papierkorb_anlegen(
    papierkorb: Path,
    quelle: Path,
    *,
    typ: str,
    grund: str,
    serie_id: str | None,
    serie_name: str | None,
    serie_ordner: str | None,
    folge_info: dict[str, Any] | None = None,
    serie_json: dict[str, Any] | None = None,
    pruefsummen: list[str] | None = None,
) -> dict[str, Any]:
    """Verschiebt ``quelle`` in einen neuen Papierkorb-Eintrag ``_papierkorb/<id>/`` und gibt den Eintrag zurück.

    Aufbau: ``meta.json`` zuerst (atomar), dann ``inhalt/<name>`` (Umbenennen auf derselben Freigabe).
    Scheitert das Verschieben, wird alles zurückgebaut.
    """
    papierkorb.mkdir(parents=True, exist_ok=True)
    while True:
        eid = neue_id12()
        eintrag_pfad = papierkorb / eid
        try:
            eintrag_pfad.mkdir()
            break
        except FileExistsError:
            continue
    ist_ordner = quelle.is_dir()
    anzahl, groesse = dateien.ordner_groesse(quelle) if ist_ordner else (1, quelle.stat().st_size)
    meta: dict[str, Any] = {
        "schema_version": 1,
        "id": eid,
        "typ": typ,
        "grund": grund,
        "geloescht_am": jetzt_iso(),
        "serie_id": serie_id,
        "serie_name": serie_name,
        "serie_ordner": serie_ordner,
        "name": quelle.name,
        "art": "ordner" if ist_ordner else "datei",
        "dateien": anzahl,
        "groesse_bytes": groesse,
        "folge_info": folge_info,
        "serie_json": serie_json,
    }
    if pruefsummen:
        meta["index_pruefsummen"] = pruefsummen
    try:
        dateien.schreibe_json_atomar(eintrag_pfad / "meta.json", meta)
        (eintrag_pfad / "inhalt").mkdir()
        os.rename(quelle, eintrag_pfad / "inhalt" / quelle.name)
    except BaseException:
        shutil.rmtree(eintrag_pfad, ignore_errors=True)
        raise
    return meta


def lese_papierkorb(papierkorb: Path) -> list[dict[str, Any]]:
    """Alle vollständigen Einträge (``meta.json`` und ``inhalt/``), neueste zuerst."""
    aus: list[dict[str, Any]] = []
    try:
        eintraege = list(os.scandir(papierkorb))
    except OSError:
        return aus
    for e in eintraege:
        if not e.is_dir() or not RE_ID12.match(e.name):
            continue
        pfad = Path(e.path)
        try:
            meta = dateien.lese_json(pfad / "meta.json")
        except (OSError, ValueError):
            _LOGGER.warning("papierkorb_unvollstaendig: %s (meta.json fehlt oder ist ungültig)", e.name)
            continue
        if not (pfad / "inhalt").is_dir() or not isinstance(meta, dict) or meta.get("id") != e.name:
            _LOGGER.warning("papierkorb_unvollstaendig: %s", e.name)
            continue
        aus.append(meta)
    aus.sort(key=lambda m: (parse_iso(m.get("geloescht_am")) or jetzt(), m.get("id", "")), reverse=True)
    return aus


def eintrag_fuer_seite(meta: dict[str, Any]) -> dict[str, Any]:
    """Papierkorb-Eintrag in der Form des Vertrags W (3.3)."""
    typ = meta.get("typ")
    if typ == "folge":
        info = meta.get("folge_info") or {}
        anzeige = info.get("anzeige") or anzeige_aus_name(meta.get("name", ""))
    elif typ == "serie":
        anzeige = meta.get("serie_name") or meta.get("name", "")
    else:
        anzeige = meta.get("name", "")
    return {
        "id": meta["id"],
        "typ": typ,
        "serie_id": meta.get("serie_id"),
        "serie_name": meta.get("serie_name"),
        "folge": meta.get("name") if typ == "folge" else None,
        "anzeige": anzeige,
        "art": meta.get("art", "datei"),
        "tracks": meta.get("dateien", 1),
        "groesse_bytes": meta.get("groesse_bytes", 0),
        "grund": meta.get("grund", "manuell"),
        "geloescht_am": meta.get("geloescht_am"),
    }


# --------------------------------------------------------------------------
# Reihenfolge einfügen (Vertrag W, 11.6)
# --------------------------------------------------------------------------


def einfuege_index(folgen: list[str], infos: dict[str, dict[str, Any]], nummer: int | None) -> int:
    """Wo eine neue Folge mit ``nummer`` in die vorhandene Reihenfolge kommt, ohne diese zu ändern."""
    if nummer is None:
        return len(folgen)
    mit_nummer = [(i, infos.get(n, {}).get("nummer")) for i, n in enumerate(folgen)]
    mit_nummer = [(i, z) for i, z in mit_nummer if isinstance(z, int)]
    for i, z in mit_nummer:
        if z > nummer:
            return i
    kleiner = [i for i, z in mit_nummer if z <= nummer]
    return kleiner[-1] + 1 if kleiner else len(folgen)


# --------------------------------------------------------------------------
# Zwischenspeicher
# --------------------------------------------------------------------------


@dataclass
class SerieInfo:
    """Eine Serie im Zwischenspeicher der letzten Prüfung."""

    serie: Serie
    ordner: str
    folgen_objekte: list[dict[str, Any]] = field(default_factory=list)
    hinweise: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PruefErgebnis:
    neue_serien: int = 0
    neue_folgen: int = 0
    entfernte_folgen: int = 0
    hinweise: int = 0
    geaenderte: set[str] = field(default_factory=set)


class Medien:
    """Medienverwaltung (``media.py``)."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.pfade = hub.pfade
        self.serien: dict[str, SerieInfo] = {}
        self.reservierte_hinweise: list[dict[str, Any]] = []
        self.geprueft_am: str | None = None
        self.pruefung_laeuft = False
        self._pruefung_task: asyncio.Task | None = None
        self._sperren: dict[str, asyncio.Lock] = {}
        #: (ordner, name) -> {"sig": …, "ergebnis": …, "hinweis": …}
        self._pruefergebnisse: dict[tuple[str, str], dict[str, Any]] = {}

    # --- Hilfen ---------------------------------------------------------------

    def _executor(self, func, *args):
        return self.hub.hass.async_add_executor_job(func, *args)

    def sperre(self, serie_id: str) -> asyncio.Lock:
        return self._sperren.setdefault(serie_id, asyncio.Lock())

    @contextlib.asynccontextmanager
    async def sperren(self, *serien_ids: str):
        """Nimmt die Sperren der Serien in aufsteigender Serien-ID (Vertrag W, Abschnitt 1)."""
        locks = [self.sperre(i) for i in sorted(set(serien_ids))]
        for lock in locks:
            await lock.acquire()
        try:
            yield
        finally:
            for lock in reversed(locks):
                lock.release()

    def pfad_serie(self, ordner: str) -> Path:
        return self.pfade.medien / ordner

    async def _medien_erreichbar(self) -> None:
        ok = await self._executor(self.pfade.medien.is_dir)
        if not ok:
            raise TobiboxFehler("medien_nicht_erreichbar")

    def _fehler_schreiben(self, err: BaseException) -> TobiboxFehler:
        _LOGGER.error("Schreiben auf die Freigabe fehlgeschlagen: %s", err)
        if isinstance(err, NamenErschoepft):
            return TobiboxFehler("medien_schreibfehler")
        return TobiboxFehler("medien_schreibfehler")

    def tobies_der_serie(self, serie_id: str) -> list[dict[str, Any]]:
        """Tobies, deren Ziel auf die Serie oder eine ihrer Folgen zeigt."""
        return self.hub.tobies(lambda z: z.get("serie") == serie_id and z["typ"] in ("serie", "folge"))

    def tobies_der_folge(self, serie_id: str, folge: str) -> list[dict[str, Any]]:
        return self.hub.tobies(lambda z: z["typ"] == "folge" and z.get("serie") == serie_id and z.get("folge") == folge)

    def tobies_der_ganzen_serie(self, serie_id: str) -> list[dict[str, Any]]:
        return self.hub.tobies(lambda z: z["typ"] == "serie" and z.get("serie") == serie_id)

    # --- Serie-Kurzform und Folge-Objekt -------------------------------------------

    def kurzform(self, info: SerieInfo) -> dict[str, Any]:
        s = info.serie
        anzahl_pruefen = sum(1 for n in s.folgen if s.info(n).get("pruefen"))
        return {
            "id": s.id,
            "name": s.name,
            "typ": s.typ,
            "ordner": info.ordner,
            "anzahl_folgen": len(s.folgen),
            "anzahl_tobies": len(self.tobies_der_serie(s.id)),
            "angelegt_am": s.angelegt_am,
            "stand": s.stand,
            "pruefen": bool(s.pruefen),
            "anzahl_pruefen": anzahl_pruefen,
            "hinweise": list(info.hinweise),
        }

    def _folge_objekt(self, s: Serie, ordner: str, name: str) -> dict[str, Any]:
        pfad = self.pfad_serie(ordner)
        art, tracks, groesse, vorhanden = stat_folge(pfad, name)
        info = s.info(name)
        cache = self._pruefergebnisse.get((ordner, name))
        if not vorhanden:
            pruefung, hinweis = "nicht_geprueft", "datei_fehlt"
        elif cache and cache["sig"] == pruefung_signatur(pfad / name):
            pruefung = cache["ergebnis"]
            hinweis = cache["hinweis"]
        else:
            pruefung, hinweis = "nicht_geprueft", None
        if pruefung == "ok":
            hinweis = None
        return {
            "name": name,
            "anzeige": info.get("anzeige") or anzeige_aus_name(name),
            "nummer": info.get("nummer"),
            "datum": info.get("datum"),
            "art": art,
            "tracks": tracks,
            "groesse_bytes": groesse,
            "pruefung": pruefung,
            "hinweis": hinweis,
            "pruefen": bool(info.get("pruefen")),
            "pruefen_gruende": list(info.get("pruefen_gruende", [])) if info.get("pruefen") else [],
            "tobies": self.tobies_der_folge(s.id, name),
        }

    def _baue_info(self, s: Serie, ordner: str, hinweise: list[dict[str, Any]]) -> SerieInfo:
        info = SerieInfo(serie=s, ordner=ordner, hinweise=list(hinweise))
        info.folgen_objekte = [self._folge_objekt(s, ordner, n) for n in s.folgen]
        return info

    def _hinweis(self, code: str, folge: str | None = None) -> dict[str, Any]:
        return {"code": code, "folge": folge, "text": self.hub.t(f"hinweis_{code}", folge=folge or "", datei=folge or "")}

    # --- Prüfung der Freigabe (Vertrag W, Nr. 9) ---------------------------------------

    def pruefung_starten(self) -> tuple[bool, bool]:
        """``(gestartet, laeuft_bereits)``: Die Prüfung läuft im Hintergrund."""
        if self.pruefung_laeuft:
            return False, True
        self.pruefung_laeuft = True
        self._pruefung_task = self.hub.hass.async_create_background_task(self._pruefung_hintergrund(), "tobibox_pruefung")
        return True, False

    async def _pruefung_hintergrund(self) -> None:
        try:
            await self.pruefen()
        except TobiboxFehler as err:
            _LOGGER.warning("Prüfung der Freigabe nicht möglich: %s", err.code)
        except Exception:
            _LOGGER.exception("Prüfung der Freigabe fehlgeschlagen")
        finally:
            self.pruefung_laeuft = False

    async def pruefen(self) -> PruefErgebnis:
        """Prüft die Freigabe: neue Ordner und Dateien, fehlende Folgen, doppelte IDs, Format und Kopierschutz (D5)."""
        self.pruefung_laeuft = True
        ergebnis = PruefErgebnis()
        try:
            await self._medien_erreichbar()
            ordner, reserviert = await self._executor(self._liste_ordner)
            await self._executor(self._raeume_part_dateien)
            alt = {sid: i.serie.stand for sid, i in self.serien.items()}
            neu: dict[str, SerieInfo] = {}
            ids_gesehen: dict[str, list[tuple[str, Serie]]] = {}
            for name in ordner:
                try:
                    schnell_id = await self._executor(self._schnelle_id, name)
                    async with self.sperren(schnell_id):
                        info = await self._executor(self._pruefe_ordner, name)
                except OSError as err:
                    _LOGGER.warning("Ordner %s nicht lesbar: %s", name, err)
                    continue
                if info is None:
                    continue
                s, hinweise, delta = info
                ergebnis.neue_serien += delta["neue_serie"]
                ergebnis.neue_folgen += delta["neue_folgen"]
                ergebnis.entfernte_folgen += delta["entfernte_folgen"]
                ids_gesehen.setdefault(s.id, []).append((name, s))
                neu[name] = self._baue_info(s, name, hinweise)  # vorläufig, nach Ordnername
            # Doppelte IDs: die jüngere Kopie bekommt eine neue ID (data-model.md, Abschnitt 5)
            for sid, kopien in ids_gesehen.items():
                if len(kopien) < 2:
                    continue
                kopien.sort(key=lambda k: (parse_iso(k[1].angelegt_am) or jetzt(), k[0]))
                for name, s in kopien[1:]:
                    async with self.sperren(sid):
                        s.id = neue_id12()
                        await self._executor(schreibe_serie, self.pfad_serie(name), s)
                    neu[name] = self._baue_info(s, name, [*neu[name].hinweise, self._hinweis("doppelte_id_korrigiert")])
                    ergebnis.hinweise += 1
            self.serien = {i.serie.id: i for i in neu.values()}
            self.reservierte_hinweise = [
                self._hinweis("reservierter_ordner", folge=r) for r in reserviert if not ist_systemordner(r)
            ]
            ergebnis.hinweise += sum(len(i.hinweise) for i in self.serien.values()) + len(self.reservierte_hinweise)
            self.geprueft_am = jetzt_iso()
            ergebnis.geaenderte = {sid for sid, i in self.serien.items() if alt.get(sid) != i.serie.stand} | (
                set(alt) - set(self.serien)
            )
            if ergebnis.geaenderte:
                self.hub.emit("medien", "serien_geaendert", {"serie_ids": sorted(ergebnis.geaenderte)})
            self.hub.emit(
                "medien",
                "pruefung_fertig",
                {
                    "geprueft_am": self.geprueft_am,
                    "neue_serien": ergebnis.neue_serien,
                    "neue_folgen": ergebnis.neue_folgen,
                    "entfernte_folgen": ergebnis.entfernte_folgen,
                    "hinweise": ergebnis.hinweise,
                },
            )
            return ergebnis
        finally:
            self.pruefung_laeuft = False

    def _liste_ordner(self) -> tuple[list[str], list[str]]:
        ordner: list[str] = []
        reserviert: list[str] = []
        for e in sorted(os.scandir(self.pfade.medien), key=lambda e: e.name):
            if e.name.startswith(".") or not e.is_dir():
                continue
            (reserviert if ist_reserviert(e.name) else ordner).append(e.name)
        return ordner, reserviert

    def _raeume_part_dateien(self) -> None:
        """Reste ``*.part`` älter als 24 h in ``_upload/`` löschen (Vertrag W, 5.2)."""
        upload = self.pfade.upload
        if not upload.is_dir():
            return
        jetzt_s = jetzt().timestamp()
        for e in os.scandir(upload):
            if e.name.endswith(".part"):
                with contextlib.suppress(OSError):
                    if jetzt_s - e.stat().st_mtime > PART_MAX_ALTER_S:
                        os.unlink(e.path)

    def _schnelle_id(self, ordner: str) -> str:
        """Die ID, die ``_pruefe_ordner`` für diesen Ordner verwenden wird (für die Sperre)."""
        pfad = self.pfad_serie(ordner)
        datei = pfad / SERIE_JSON
        try:
            roh = dateien.lese_json(datei)
            if isinstance(roh, dict) and gueltige_serien_id(roh.get("id")):
                return roh["id"]
        except (OSError, ValueError):
            pass
        return ordner if gueltige_serien_id(ordner) else f"ordner:{ordner}"

    def _pruefe_ordner(self, ordner: str) -> tuple[Serie, list[dict[str, Any]], dict[str, int]] | None:
        """Prüft einen Serien-Ordner und schreibt ``serie.json`` bei Bedarf (läuft im Executor, unter der Sperre)."""
        pfad = self.pfad_serie(ordner)
        hinweise: list[dict[str, Any]] = []
        delta = {"neue_serie": 0, "neue_folgen": 0, "entfernte_folgen": 0}
        serie, vorhanden = lese_serie(pfad)
        geaendert = False
        if serie is None:
            if vorhanden:
                hinweise.append(self._hinweis("serie_json_ungueltig_repariert"))
            else:
                delta["neue_serie"] = 1
            roh_id = None
            roh_name = None
            roh_typ = "normal"
            if vorhanden:
                try:
                    roh = dateien.lese_json(pfad / SERIE_JSON)
                    if isinstance(roh, dict):
                        roh_id = roh.get("id") if gueltige_serien_id(roh.get("id")) else None
                        if isinstance(roh.get("name"), str) and 1 <= len(roh["name"]) <= SERIE_NAME_MAX:
                            roh_name = roh["name"]
                        roh_typ = roh.get("typ") if roh.get("typ") in ("normal", "ueberraschung") else "normal"
                except (OSError, ValueError):
                    pass
            # Ordner ohne serie.json: ID = Ordnername (Zeiger und Zuordnungen bleiben, data-model.md, Abschnitt 5)
            sid = roh_id or (ordner if gueltige_serien_id(ordner) else neue_id12())
            serie = Serie(
                id=sid,
                name=(roh_name or anzeigename(ordner, SERIE_NAME_MAX) or ordner[:SERIE_NAME_MAX]),
                typ=roh_typ,
                angelegt_am=jetzt_iso(),
                ordner=ordner,
            )
            geaendert = True
        alt_folgen = list(serie.folgen)
        auf_platte = liste_auf_platte(pfad)
        platte_set = set(auf_platte)
        fehlend = [n for n in serie.folgen if n not in platte_set]
        for n in fehlend:
            hinweise.append(self._hinweis("datei_fehlt", n))
        delta["entfernte_folgen"] = len(fehlend)
        serie.folgen = [n for n in serie.folgen if n in platte_set]
        neue = [n for n in auf_platte if n not in set(serie.folgen)]
        delta["neue_folgen"] = len(neue)
        serie.folgen.extend(neue)  # neue Dateien und Folgen-Ordner hinten (Entscheidung F)
        serie.bereinige()
        if serie.folgen != alt_folgen:
            geaendert = True
        if geaendert:
            schreibe_serie(pfad, serie)
        serie.ordner = ordner
        # Format- und Kopierschutz-Prüfung (D5): neue Dateien immer, bekannte nur, wenn sie sich geändert haben
        for n in serie.folgen:
            sig = pruefung_signatur(pfad / n)
            cache = self._pruefergebnisse.get((ordner, n))
            if cache and cache["sig"] == sig:
                continue
            if n in neue or cache is not None:
                ergebnis, code = pruefe_folge_pfad(pfad / n)
                self._pruefergebnisse[(ordner, n)] = {"sig": sig, "ergebnis": ergebnis, "hinweis": code}
        for n in serie.folgen:
            c = self._pruefergebnisse.get((ordner, n))
            if c and c["ergebnis"] in ("warnung", "nicht_moeglich") and c["hinweis"]:
                hinweise.append(self._hinweis(c["hinweis"], n))
        return serie, hinweise, delta

    # --- Lesen ----------------------------------------------------------------------

    async def _stelle_geprueft_sicher(self) -> None:
        if self.geprueft_am is None:
            await self._medien_erreichbar()
            try:
                async with asyncio.timeout(8):
                    await self.pruefen()
            except TimeoutError as err:
                raise TobiboxFehler("medien_nicht_erreichbar") from err

    async def serien_liste(self) -> dict[str, Any]:
        await self._stelle_geprueft_sicher()
        infos = sorted(self.serien.values(), key=lambda i: natuerlicher_schluessel(i.serie.name))
        return {
            "serien": [self.kurzform(i) for i in infos],
            "ueberraschung": self.ueberraschung_status(),
            "geprueft_am": self.geprueft_am,
            "pruefung_laeuft": self.pruefung_laeuft,
            "hinweise": list(self.reservierte_hinweise),
        }

    def ueberraschung_status(self) -> str:
        ue = [i for i in self.serien.values() if i.serie.typ == "ueberraschung"]
        if not ue:
            return "fehlt"
        if len(ue) > 1:
            return "mehrere"
        return "ok" if ue[0].serie.folgen else "leer"

    def finde(self, serie_id: str) -> SerieInfo:
        info = self.serien.get(serie_id)
        if info is None:
            raise TobiboxFehler("serie_nicht_gefunden")
        return info

    async def _frisch(self, serie_id: str) -> tuple[Serie, Path]:
        """Liest ``serie.json`` frisch von der Freigabe (der Ordner kommt aus dem Zwischenspeicher)."""
        await self._stelle_geprueft_sicher()
        info = self.finde(serie_id)
        pfad = self.pfad_serie(info.ordner)
        try:
            serie, vorhanden = await self._executor(lese_serie, pfad)
        except OSError as err:
            raise TobiboxFehler("medien_nicht_erreichbar") from err
        if serie is None:
            if not vorhanden and not await self._executor(pfad.is_dir):
                self.serien.pop(serie_id, None)
                raise TobiboxFehler("serie_nicht_gefunden")
            raise TobiboxFehler("medien_schreibfehler")
        if serie.id != serie_id:
            raise TobiboxFehler("serie_nicht_gefunden")
        serie.ordner = info.ordner
        return serie, pfad

    async def _aktualisiere_cache(self, serie: Serie, ordner: str, hinweise: list[dict[str, Any]] | None = None) -> SerieInfo:
        alt = self.serien.get(serie.id)
        info = await self._executor(self._baue_info, serie, ordner, hinweise if hinweise is not None else (alt.hinweise if alt else []))
        self.serien[serie.id] = info
        return info

    async def serie_holen(self, serie_id: str) -> dict[str, Any]:
        serie, pfad = await self._frisch(serie_id)
        info = await self._aktualisiere_cache(serie, pfad.name)
        aus = self.kurzform(info)
        aus["folgen"] = info.folgen_objekte
        aus["zuordnungen"] = self.tobies_der_ganzen_serie(serie_id)
        return aus

    def _pruefe_stand(self, serie: Serie, stand: str | None) -> None:
        if stand is not None and stand != serie.stand:
            raise TobiboxFehler("stand_veraltet")

    # --- Schreiben: Serien --------------------------------------------------------------

    async def serie_anlegen(self, name: Any, typ: str = "normal") -> dict[str, Any]:
        anzeige = name_pruefen(name, SERIE_NAME_MAX)
        await self._stelle_geprueft_sicher()
        if typ == "ueberraschung" and any(i.serie.typ == "ueberraschung" for i in self.serien.values()):
            raise TobiboxFehler("ueberraschung_existiert")
        roh_ordner, _ = dateiname_bereinigen(anzeige, mit_endung=False, fuer_serienordner=True)
        if not roh_ordner:
            raise TobiboxFehler("name_ungueltig")
        sid = neue_id12()
        async with self.sperren(sid):
            try:
                ordner = await self._executor(self._lege_ordner_an, roh_ordner)
                serie = Serie(id=sid, name=anzeige, typ=typ, angelegt_am=jetzt_iso(), ordner=ordner)
                await self._executor(schreibe_serie, self.pfad_serie(ordner), serie)
            except (OSError, NamenErschoepft) as err:
                raise self._fehler_schreiben(err) from err
            info = await self._aktualisiere_cache(serie, ordner, [])
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": [sid]})
        return self.kurzform(info)

    def _lege_ordner_an(self, wunsch: str) -> str:
        """Legt den Ordner an (``mkdir`` ist atomar); bei Namensgleichheit ` (2)`, ` (3)` … (Abschnitt 12)."""
        while True:
            belegt = {vergleichsschluessel(e.name) for e in os.scandir(self.pfade.medien)} | {ORDNER_EINGANG}
            name = eindeutiger_name(wunsch, belegt, mit_endung=False)
            try:
                (self.pfade.medien / name).mkdir()
                return name
            except FileExistsError:
                continue

    async def serie_umbenennen(self, serie_id: str, name: Any) -> dict[str, Any]:
        anzeige = name_pruefen(name, SERIE_NAME_MAX)
        async with self.sperren(serie_id):
            serie, pfad = await self._frisch(serie_id)
            if serie.name != anzeige or serie.pruefen:
                serie.name = anzeige
                serie.pruefen = False
                serie.pruefen_gruende = []
                try:
                    await self._executor(schreibe_serie, pfad, serie)
                except OSError as err:
                    raise self._fehler_schreiben(err) from err
            info = await self._aktualisiere_cache(serie, pfad.name)
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
        return self.kurzform(info)

    async def folgen_ordnen(self, serie_id: str, folgen: list[str], stand: str | None) -> dict[str, Any]:
        async with self.sperren(serie_id):
            serie, pfad = await self._frisch(serie_id)
            self._pruefe_stand(serie, stand)
            if len(set(folgen)) != len(folgen) or set(folgen) != set(serie.folgen):
                raise TobiboxFehler("reihenfolge_ungueltig")
            if folgen != serie.folgen:
                serie.folgen = list(folgen)
                try:
                    await self._executor(schreibe_serie, pfad, serie)
                except OSError as err:
                    raise self._fehler_schreiben(err) from err
            info = await self._aktualisiere_cache(serie, pfad.name)
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
        return self.kurzform(info)

    async def folge_umbenennen(self, serie_id: str, folge: str, name: Any, stand: str | None) -> dict[str, Any]:
        anzeige = name_pruefen(name, FOLGE_ANZEIGE_MAX)
        async with self.sperren(serie_id):
            serie, pfad = await self._frisch(serie_id)
            self._pruefe_stand(serie, stand)
            if folge not in serie.folgen:
                raise TobiboxFehler("folge_nicht_gefunden")
            if serie.info(folge).get("anzeige") != anzeige or serie.info(folge).get("pruefen"):
                serie.setze_info(folge, anzeige=anzeige)
                serie.loesche_pruefen(folge)
                try:
                    await self._executor(schreibe_serie, pfad, serie)
                except OSError as err:
                    raise self._fehler_schreiben(err) from err
            info = await self._aktualisiere_cache(serie, pfad.name)
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
        objekt = next(o for o in info.folgen_objekte if o["name"] == folge)
        return {"serie": self.kurzform(info), "folge": objekt}

    async def bestaetigen(self, serie_id: str, folgen: list[str] | None) -> dict[str, Any]:
        async with self.sperren(serie_id):
            serie, pfad = await self._frisch(serie_id)
            geaendert = False
            if folgen is not None:
                for n in folgen:
                    if n not in serie.folgen:
                        raise TobiboxFehler("folge_nicht_gefunden")
                ziel = list(folgen)
            else:
                ziel = list(serie.folgen)
                if serie.pruefen:
                    serie.pruefen = False
                    serie.pruefen_gruende = []
                    geaendert = True
            for n in ziel:
                if serie.info(n).get("pruefen"):
                    serie.loesche_pruefen(n)
                    geaendert = True
            if geaendert:
                try:
                    await self._executor(schreibe_serie, pfad, serie)
                except OSError as err:
                    raise self._fehler_schreiben(err) from err
            info = await self._aktualisiere_cache(serie, pfad.name)
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
        return self.kurzform(info)

    # --- Löschen (Papierkorb) -----------------------------------------------------------------

    def _index_pruefsummen(self, praefix: str) -> list[str]:
        return self.hub.eingang.index_entferne_praefix(praefix)

    async def folge_loeschen(self, serie_id: str, folge: str, tobies_bestaetigt: bool, stand: str | None) -> dict[str, Any]:
        async with self.sperren(serie_id):
            serie, pfad = await self._frisch(serie_id)
            self._pruefe_stand(serie, stand)
            if folge not in serie.folgen:
                raise TobiboxFehler("folge_nicht_gefunden")
            tobies = self.tobies_der_folge(serie_id, folge)
            if tobies and not tobies_bestaetigt:
                raise TobiboxFehler("tobies_betroffen")
            quelle = pfad / folge
            if not await self._executor(os.path.lexists, quelle):
                raise TobiboxFehler("folge_nicht_gefunden")
            summen = self._index_pruefsummen(f"{pfad.name}/{folge}")
            try:
                meta = await self._executor(
                    lambda: papierkorb_anlegen(
                        self.pfade.papierkorb,
                        quelle,
                        typ="folge",
                        grund="manuell",
                        serie_id=serie.id,
                        serie_name=serie.name,
                        serie_ordner=pfad.name,
                        folge_info=copy.deepcopy(serie.folgen_info.get(folge)),
                        pruefsummen=summen,
                    )
                )
            except OSError as err:
                self.hub.eingang.index_wiederherstellen(summen, f"{pfad.name}/{folge}")
                raise self._fehler_schreiben(err) from err
            serie.folgen = [n for n in serie.folgen if n != folge]
            serie.folgen_info.pop(folge, None)
            self._pruefergebnisse.pop((pfad.name, folge), None)
            try:
                await self._executor(schreibe_serie, pfad, serie)
            except OSError as err:
                raise self._fehler_schreiben(err) from err
            await self._aktualisiere_cache(serie, pfad.name)
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
        self.hub.emit("medien", "papierkorb_geaendert", {})
        return {"eintrag": eintrag_fuer_seite(meta), "betroffene_tobies": tobies}

    async def serie_loeschen(self, serie_id: str, tobies_bestaetigt: bool, stand: str | None) -> dict[str, Any]:
        async with self.sperren(serie_id):
            serie, pfad = await self._frisch(serie_id)
            self._pruefe_stand(serie, stand)
            tobies = self.tobies_der_serie(serie_id)
            if tobies and not tobies_bestaetigt:
                raise TobiboxFehler("tobies_betroffen")
            summen = self._index_pruefsummen(f"{pfad.name}/")
            try:
                meta = await self._executor(
                    lambda: papierkorb_anlegen(
                        self.pfade.papierkorb,
                        pfad,
                        typ="serie",
                        grund="manuell",
                        serie_id=serie.id,
                        serie_name=serie.name,
                        serie_ordner=pfad.name,
                        serie_json=serie.to_json(),
                        pruefsummen=summen,
                    )
                )
            except OSError as err:
                self.hub.eingang.index_wiederherstellen(summen, f"{pfad.name}/")
                raise self._fehler_schreiben(err) from err
            self.serien.pop(serie_id, None)
            for k in [k for k in self._pruefergebnisse if k[0] == pfad.name]:
                self._pruefergebnisse.pop(k, None)
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
        self.hub.emit("medien", "papierkorb_geaendert", {})
        return {
            "eintrag": eintrag_fuer_seite(meta),
            "betroffene_tobies": tobies,
            "ueberraschung": self.ueberraschung_status(),
        }

    # --- Verschieben und Zusammenführen (Entscheidung M) ---------------------------------------

    def _brauche_konfig_bereit(self, tobies: list[dict[str, Any]]) -> None:
        if tobies and self.hub.store.zustand != "ok":
            raise TobiboxFehler("konfig_nicht_bereit")

    async def folge_verschieben(
        self, serie_id: str, folge: str, ziel_serie_id: str, tobies_bestaetigt: bool, stand: str | None
    ) -> dict[str, Any]:
        if ziel_serie_id == serie_id:
            raise TobiboxFehler("ziel_ungueltig")
        await self._stelle_geprueft_sicher()
        self.finde(serie_id)
        self.finde(ziel_serie_id)
        async with self.hub.eingang.sperre, self.sperren(serie_id, ziel_serie_id):
            quelle_serie, quelle_pfad = await self._frisch(serie_id)
            ziel_serie, ziel_pfad = await self._frisch(ziel_serie_id)
            self._pruefe_stand(quelle_serie, stand)
            if folge not in quelle_serie.folgen:
                raise TobiboxFehler("folge_nicht_gefunden")
            tobies = self.tobies_der_folge(serie_id, folge)
            if tobies and not tobies_bestaetigt:
                raise TobiboxFehler("tobies_betroffen")
            self._brauche_konfig_bereit(tobies)
            quelle = quelle_pfad / folge
            if not await self._executor(os.path.lexists, quelle):
                raise TobiboxFehler("folge_nicht_gefunden")
            try:
                neuer_name = await self._executor(self._verschiebe_folge, quelle_pfad, ziel_pfad, quelle_serie, ziel_serie, folge)
            except (OSError, NamenErschoepft) as err:
                raise self._fehler_schreiben(err) from err
            self.hub.eingang.index_entferne_praefix(f"{quelle_pfad.name}/{folge}")
            info_alt = copy.deepcopy(quelle_serie.folgen_info.get(folge, {}))
            info_alt.pop("pruefen", None)
            info_alt.pop("pruefen_gruende", None)
            # Ziel zuerst schreiben, dann die Quelle (Vertrag W, Nr. 26: bricht es ab, findet die nächste Prüfung die Folge)
            pos = einfuege_index(ziel_serie.folgen, ziel_serie.folgen_info, info_alt.get("nummer"))
            ziel_serie.folgen.insert(pos, neuer_name)
            if info_alt:
                ziel_serie.folgen_info[neuer_name] = info_alt
            quelle_serie.folgen = [n for n in quelle_serie.folgen if n != folge]
            quelle_serie.folgen_info.pop(folge, None)
            try:
                await self._executor(schreibe_serie, ziel_pfad, ziel_serie)
                await self._executor(schreibe_serie, quelle_pfad, quelle_serie)
            except OSError as err:
                raise self._fehler_schreiben(err) from err
            for sp in ((quelle_pfad.name, folge), (ziel_pfad.name, neuer_name)):
                self._pruefergebnisse.pop(sp, None)
            konfig = None
            veroeffentlicht = None
            if tobies:
                uids = {t["uid"] for t in tobies}

                def schreibe_um(k: dict[str, Any]) -> None:
                    for uid in uids:
                        z = k["zuordnungen"].get(uid, {}).get("ziel")
                        if z and z["typ"] == "folge" and z.get("serie") == serie_id and z.get("folge") == folge:
                            z["serie"] = ziel_serie_id
                            z["folge"] = neuer_name

                erg = await self.hub.aendere_konfig(schreibe_um)
                konfig, veroeffentlicht = erg["konfig"], erg["veroeffentlicht"]
            qinfo = await self._aktualisiere_cache(quelle_serie, quelle_pfad.name)
            zinfo = await self._aktualisiere_cache(ziel_serie, ziel_pfad.name)
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": sorted({serie_id, ziel_serie_id})})
        return {
            "quelle": self.kurzform(qinfo),
            "ziel": self.kurzform(zinfo),
            "folge": neuer_name,
            "betroffene_tobies": tobies,
            "konfig": konfig,
            "veroeffentlicht": veroeffentlicht,
        }

    def _verschiebe_folge(self, quelle_pfad: Path, ziel_pfad: Path, quelle_serie: Serie, ziel_serie: Serie, folge: str) -> str:
        """Verschiebt eine Folge in den Zielordner und gibt ihren (eventuell mit Suffix versehenen) Namen zurück."""
        ist_ordner = (quelle_pfad / folge).is_dir()
        belegt = {vergleichsschluessel(e.name) for e in os.scandir(ziel_pfad)} | {
            vergleichsschluessel(n) for n in ziel_serie.folgen
        }
        name = eindeutiger_name(folge, belegt, mit_endung=not ist_ordner)
        dateien.verschiebe_ohne_ueberschreiben(quelle_pfad / folge, ziel_pfad / name)
        return name

    async def serien_zusammenfuehren(
        self, quelle_id: str, ziel_id: str, tobies_bestaetigt: bool, stand_quelle: str | None, stand_ziel: str | None
    ) -> dict[str, Any]:
        if quelle_id == ziel_id:
            raise TobiboxFehler("ziel_ungueltig")
        await self._stelle_geprueft_sicher()
        qinfo0 = self.finde(quelle_id)
        zinfo0 = self.finde(ziel_id)
        if qinfo0.serie.typ != "normal" or zinfo0.serie.typ != "normal":
            raise TobiboxFehler("ziel_ungueltig")
        async with self.hub.eingang.sperre, self.sperren(quelle_id, ziel_id):
            quelle, quelle_pfad = await self._frisch(quelle_id)
            ziel, ziel_pfad = await self._frisch(ziel_id)
            self._pruefe_stand(quelle, stand_quelle)
            self._pruefe_stand(ziel, stand_ziel)
            tobies = self.tobies_der_serie(quelle_id)
            if tobies and not tobies_bestaetigt:
                raise TobiboxFehler("tobies_betroffen")
            self._brauche_konfig_bereit(tobies)
            umbenannt: list[dict[str, str]] = []
            neue_namen: dict[str, str] = {}
            verschoben = 0
            fehler: BaseException | None = None
            for folge in list(quelle.folgen):
                try:
                    if not await self._executor(os.path.lexists, quelle_pfad / folge):
                        continue
                    neuer = await self._executor(self._verschiebe_folge, quelle_pfad, ziel_pfad, quelle, ziel, folge)
                except (OSError, NamenErschoepft) as err:
                    fehler = err
                    break
                info = copy.deepcopy(quelle.folgen_info.get(folge, {}))
                pos = einfuege_index(ziel.folgen, ziel.folgen_info, info.get("nummer"))
                ziel.folgen.insert(pos, neuer)
                if info:
                    ziel.folgen_info[neuer] = info
                self.hub.eingang.index_entferne_praefix(f"{quelle_pfad.name}/{folge}")
                neue_namen[folge] = neuer
                quelle.folgen = [n for n in quelle.folgen if n != folge]
                quelle.folgen_info.pop(folge, None)
                verschoben += 1
                if neuer != folge:
                    umbenannt.append({"von": folge, "nach": neuer})
            try:
                await self._executor(schreibe_serie, ziel_pfad, ziel)
                await self._executor(schreibe_serie, quelle_pfad, quelle)
            except OSError as err:
                raise self._fehler_schreiben(err) from err
            if fehler is not None:
                await self._aktualisiere_cache(ziel, ziel_pfad.name)
                await self._aktualisiere_cache(quelle, quelle_pfad.name)
                self.hub.emit("medien", "serien_geaendert", {"serie_ids": sorted({quelle_id, ziel_id})})
                raise self._fehler_schreiben(fehler) from fehler
            try:
                meta = await self._executor(
                    lambda: papierkorb_anlegen(
                        self.pfade.papierkorb,
                        quelle_pfad,
                        typ="serie",
                        grund="zusammengefuehrt",
                        serie_id=quelle.id,
                        serie_name=quelle.name,
                        serie_ordner=quelle_pfad.name,
                        serie_json=quelle.to_json(),
                        pruefsummen=self.hub.eingang.index_entferne_praefix(f"{quelle_pfad.name}/"),
                    )
                )
            except OSError as err:
                raise self._fehler_schreiben(err) from err
            self.serien.pop(quelle_id, None)
            for k in [k for k in self._pruefergebnisse if k[0] == quelle_pfad.name]:
                self._pruefergebnisse.pop(k, None)
            konfig = None
            veroeffentlicht = None
            if tobies:
                uids = {t["uid"] for t in tobies}

                def schreibe_um(k: dict[str, Any]) -> None:
                    for uid in uids:
                        z = k["zuordnungen"].get(uid, {}).get("ziel")
                        if z and z.get("serie") == quelle_id and z["typ"] in ("serie", "folge"):
                            z["serie"] = ziel_id
                            if z["typ"] == "folge":
                                z["folge"] = neue_namen.get(z["folge"], z["folge"])

                erg = await self.hub.aendere_konfig(schreibe_um)
                konfig, veroeffentlicht = erg["konfig"], erg["veroeffentlicht"]
            zinfo = await self._aktualisiere_cache(ziel, ziel_pfad.name)
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": sorted({quelle_id, ziel_id})})
        self.hub.emit("medien", "papierkorb_geaendert", {})
        return {
            "ziel": self.kurzform(zinfo),
            "verschoben": verschoben,
            "umbenannt": umbenannt,
            "betroffene_tobies": tobies,
            "eintrag": eintrag_fuer_seite(meta),
            "konfig": konfig,
            "veroeffentlicht": veroeffentlicht,
        }

    # --- Papierkorb (Vertrag W, 3.3) ---------------------------------------------------------------

    async def papierkorb_liste(self, limit: int, offset: int) -> dict[str, Any]:
        await self._medien_erreichbar()
        alle = await self._executor(lese_papierkorb, self.pfade.papierkorb)
        return {
            "eintraege": [eintrag_fuer_seite(m) for m in alle[offset : offset + limit]],
            "gesamt": len(alle),
            "gesamt_bytes": sum(int(m.get("groesse_bytes", 0)) for m in alle),
        }

    async def _meta(self, eintrag_id: str) -> dict[str, Any]:
        if not RE_ID12.match(eintrag_id):
            raise TobiboxFehler("eintrag_nicht_gefunden")
        alle = await self._executor(lese_papierkorb, self.pfade.papierkorb)
        for m in alle:
            if m["id"] == eintrag_id:
                return m
        raise TobiboxFehler("eintrag_nicht_gefunden")

    async def papierkorb_wiederherstellen(self, eintrag_id: str, serie_id: str | None) -> dict[str, Any]:
        await self._medien_erreichbar()
        meta = await self._meta(eintrag_id)
        typ = meta.get("typ")
        eintrag_pfad = self.pfade.papierkorb / eintrag_id
        inhalt = eintrag_pfad / "inhalt" / str(meta.get("name"))
        if typ == "eingang":
            async with self.hub.eingang.sperre:
                try:
                    await self._executor(self._stelle_in_eingang_wieder_her, inhalt, eintrag_pfad)
                except (OSError, NamenErschoepft) as err:
                    raise self._fehler_schreiben(err) from err
            self.hub.emit("eingang", "geaendert", {})
            self.hub.emit("medien", "papierkorb_geaendert", {})
            return {"serie": None, "folge": None}
        if typ == "folge":
            ziel_id = serie_id or meta.get("serie_id")
            await self._stelle_geprueft_sicher()
            if not ziel_id or ziel_id not in self.serien:
                raise TobiboxFehler("serie_nicht_gefunden")
            async with self.sperren(ziel_id):
                serie, pfad = await self._frisch(ziel_id)
                name = str(meta.get("name"))
                belegt = {vergleichsschluessel(e.name) for e in await self._executor(lambda: list(os.scandir(pfad)))}
                belegt |= {vergleichsschluessel(n) for n in serie.folgen}
                if vergleichsschluessel(name) in belegt:
                    raise TobiboxFehler("datei_existiert")
                try:
                    await self._executor(dateien.verschiebe_ohne_ueberschreiben, inhalt, pfad / name)
                except dateien.ZielExistiert as err:
                    raise TobiboxFehler("datei_existiert") from err
                except OSError as err:
                    raise self._fehler_schreiben(err) from err
                serie.folgen.append(name)  # hinten, die alte Position wird nicht gemerkt
                if isinstance(meta.get("folge_info"), dict):
                    serie.folgen_info[name] = _bereinige_info(meta["folge_info"])
                try:
                    await self._executor(schreibe_serie, pfad, serie)
                    await self._executor(shutil.rmtree, eintrag_pfad, True)
                except OSError as err:
                    raise self._fehler_schreiben(err) from err
                self.hub.eingang.index_wiederherstellen(meta.get("index_pruefsummen") or [], f"{pfad.name}/{name}")
                info = await self._aktualisiere_cache(serie, pfad.name)
            self.hub.emit("medien", "serien_geaendert", {"serie_ids": [ziel_id]})
            self.hub.emit("medien", "papierkorb_geaendert", {})
            return {"serie": self.kurzform(info), "folge": name}
        if typ == "serie":
            sid = meta.get("serie_id")
            await self._stelle_geprueft_sicher()
            if sid in self.serien:
                raise TobiboxFehler("serie_existiert")
            wunsch = str(meta.get("serie_ordner") or meta.get("name"))
            async with self.sperren(str(sid)):
                try:
                    ordner = await self._executor(self._stelle_serie_wieder_her, inhalt, wunsch)
                except (OSError, NamenErschoepft) as err:
                    raise self._fehler_schreiben(err) from err
                pfad = self.pfad_serie(ordner)
                serie, _ = await self._executor(lese_serie, pfad)
                if serie is None:
                    raise TobiboxFehler("medien_schreibfehler")
                serie.ordner = ordner
                await self._executor(shutil.rmtree, eintrag_pfad, True)
                self.hub.eingang.index_wiederherstellen(meta.get("index_pruefsummen") or [], f"{ordner}/")
                info = await self._aktualisiere_cache(serie, ordner, [])
            self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie.id]})
            self.hub.emit("medien", "papierkorb_geaendert", {})
            return {"serie": self.kurzform(info), "folge": None}
        raise TobiboxFehler("eintrag_nicht_gefunden")

    def _stelle_in_eingang_wieder_her(self, inhalt: Path, eintrag_pfad: Path) -> None:
        self.pfade.eingang.mkdir(parents=True, exist_ok=True)
        belegt = {vergleichsschluessel(e.name) for e in os.scandir(self.pfade.eingang)}
        name = eindeutiger_name(inhalt.name, belegt, mit_endung=not inhalt.is_dir())
        dateien.verschiebe_ohne_ueberschreiben(inhalt, self.pfade.eingang / name)
        shutil.rmtree(eintrag_pfad, ignore_errors=True)

    def _stelle_serie_wieder_her(self, inhalt: Path, wunsch: str) -> str:
        belegt = {vergleichsschluessel(e.name) for e in os.scandir(self.pfade.medien)} | {ORDNER_EINGANG}
        name = eindeutiger_name(wunsch, belegt, mit_endung=False)
        dateien.verschiebe_ohne_ueberschreiben(inhalt, self.pfade.medien / name)
        return name

    async def papierkorb_leeren(self, eintrag_ids: list[str] | None) -> dict[str, Any]:
        await self._medien_erreichbar()
        alle = await self._executor(lese_papierkorb, self.pfade.papierkorb)
        if eintrag_ids is not None:
            auswahl = [m for m in alle if m["id"] in set(eintrag_ids)]
        else:
            auswahl = alle
        geloescht = 0
        frei = 0
        try:
            for m in auswahl:
                frei += int(m.get("groesse_bytes", 0))
                await self._executor(shutil.rmtree, self.pfade.papierkorb / m["id"])
                geloescht += 1
            if eintrag_ids is None:  # auch unvollständige Reste mitnehmen
                await self._executor(self._raeume_papierkorb_reste)
        except OSError as err:
            _LOGGER.error("Papierkorb leeren fehlgeschlagen: %s", err)
            raise TobiboxFehler("medien_schreibfehler", geloescht=geloescht) from err
        finally:
            if geloescht:
                self.hub.emit("medien", "papierkorb_geaendert", {})
        return {"geloescht": geloescht, "freigegeben_bytes": frei}

    def _raeume_papierkorb_reste(self) -> None:
        for e in os.scandir(self.pfade.papierkorb):
            if e.is_dir() and RE_ID12.match(e.name):
                pfad = Path(e.path)
                if not (pfad / "meta.json").exists() or not (pfad / "inhalt").is_dir():
                    shutil.rmtree(pfad, ignore_errors=True)

