"""Konfiguration im HA-Speicher (Vertrag W, Abschnitt 13; ``data-model.md`` Abschnitt 2).

Die Konfiguration (Zuordnungen mit optionalem ``name``, Leise-Zeiten, Gute-Nacht-Einstellungen) liegt
mit **einer** Revision und **einer** Listen-ID im HA-Speicher (``.storage/tobibox``). Dazu kommen
der Zustand (``ok``, ``leer_neu``, ``export_neuer``), die Liste „Neue Tobies“, die letzten 20
Box-Meldungen je Box und die letzten 20 Lernmodus-Vorgänge.

Das Veröffentlichen auf MQTT und das Schreiben des Exports übernimmt ``hub.py``; dieses Modul
hält den Zustand und prüft Konfigurationen mit derselben Strenge wie die Box (``validiere_konfig``
in ``box/src/tobibox/store.py``).
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import dateien
from .const import (
    BOX_EREIGNISSE_MAX,
    EXPORT_DATEI,
    KONFIG_MAX_BYTES,
    KONFIG_STAENDE_ANZAHL,
    LERN_VERLAUF_MAX,
    LESEZEICHEN_TAGE_MAX,
    LESEZEICHEN_TAGE_VORGABE,
    RE_LISTE_ID,
    RE_UID,
    SCHEMA_KONFIG,
    STANDARD_ZEITZONE,
    TOBIE_NAME_MAX,
)
from .fehler import TobiboxFehler
from .namen import anzeigename
from .util import iso, jetzt, jetzt_iso, neue_liste_id, parse_iso

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "tobibox"

ZUSTAND_OK = "ok"
ZUSTAND_LEER_NEU = "leer_neu"
ZUSTAND_EXPORT_NEUER = "export_neuer"

_FENSTER_ID_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
_ZEIT_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_ZIEL_AKTIONEN = ("status", "gute_nacht")
#: höchstens so viele Fenster der Leise-Zeiten (``data-model.md``, Abschnitt 2; wie die Box)
FENSTER_MAX = 32


class Ungueltig(ValueError):
    """Eine Konfiguration ist nach ``data-model.md`` ungültig; ``pfad`` nennt die Stelle."""

    def __init__(self, pfad: str, grund: str = "schema_ungueltig") -> None:
        super().__init__(f"{grund}: {pfad}")
        self.pfad = pfad
        self.grund = grund


def _ganz(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


# --------------------------------------------------------------------------
# Konfiguration: Aufbau und Prüfung
# --------------------------------------------------------------------------


def standard_einstellungen() -> dict[str, Any]:
    """Leise-Zeiten und Gute-Nacht-Einstellungen, die ``config.json`` als Pflicht verlangt (Vertrag W, Abschnitt 10)."""
    return {
        "leise_zeiten": {"zeitzone": STANDARD_ZEITZONE, "fenster": []},
        "gute_nacht": {"timer_min": 30, "ausblenden_s": 60},
        "lesezeichen_tage": LESEZEICHEN_TAGE_VORGABE,
    }


def neue_konfig(zuordnungen: dict[str, Any] | None = None, einstellungen: dict[str, Any] | None = None) -> dict[str, Any]:
    """Neue Liste: neue Listen-ID, Revision 1 (``data-model.md`` Abschnitt 2)."""
    k: dict[str, Any] = {
        "revision": 1,
        "liste_id": neue_liste_id(),
        "erzeugt_am": jetzt_iso(),
        "zuordnungen": copy.deepcopy(zuordnungen or {}),
    }
    k.update(copy.deepcopy(einstellungen) if einstellungen else standard_einstellungen())
    return k


def pruefe_ziel(ziel: Any, wo: str) -> dict[str, Any]:
    """Prüft ein ``ziel`` und gibt es in Normalform zurück."""
    if not isinstance(ziel, dict):
        raise Ungueltig(wo)
    typ = ziel.get("typ")
    if typ in ("serie", "folge"):
        sid = ziel.get("serie")
        if not isinstance(sid, str) or not 1 <= len(sid) <= 64 or "/" in sid:
            raise Ungueltig(f"{wo}.serie")
        if typ == "serie":
            return {"typ": "serie", "serie": sid}
        folge = ziel.get("folge")
        if (
            not isinstance(folge, str)
            or folge in ("", ".", "..")
            or "/" in folge
            or "\\" in folge
            or len(folge.encode("utf-8")) > 255
        ):
            raise Ungueltig(f"{wo}.folge")
        return {"typ": "folge", "serie": sid, "folge": folge}
    if typ == "aktion":
        akt = ziel.get("aktion")
        if akt not in _ZIEL_AKTIONEN:
            raise Ungueltig(f"{wo}.aktion")
        return {"typ": "aktion", "aktion": akt}
    raise Ungueltig(f"{wo}.typ")


def pruefe_leise_zeiten(lz: Any) -> dict[str, Any]:
    """Prüft ``leise_zeiten`` (``data-model.md``, Abschnitt 2) und gibt die Normalform zurück.

    **Dieselben Regeln und Grenzen wie ``parse_konfig`` der Box** (``box/src/tobibox/store.py``): Zeitzone aus der
    Zeitzonendatenbank (Vorgabe ``Europe/Berlin``), höchstens 32 Fenster, ``id`` 1 bis 32 Zeichen ``[a-z0-9_-]`` und
    eindeutig, ``tage`` nicht leer, ohne Doppelte, 1 bis 7, ``von``/``bis`` ``HH:MM`` und nicht gleich, ``wirkung``
    ``leiser`` (mit ``grenze`` 0 bis 100) oder ``stumm`` (ohne ``grenze``). Wirft ``Ungueltig`` mit dem Pfad der Stelle."""
    if not isinstance(lz, dict):
        raise Ungueltig("leise_zeiten")
    zone = lz.get("zeitzone", STANDARD_ZEITZONE)
    if not isinstance(zone, str):
        raise Ungueltig("leise_zeiten.zeitzone")
    try:
        ZoneInfo(zone)
    except Exception as err:
        raise Ungueltig(f"leise_zeiten.zeitzone {zone!r}") from err
    fenster_roh = lz.get("fenster")
    if not isinstance(fenster_roh, list) or len(fenster_roh) > FENSTER_MAX:
        raise Ungueltig("leise_zeiten.fenster")
    fenster: list[dict[str, Any]] = []
    ids: set[str] = set()
    for i, f in enumerate(fenster_roh):
        if not isinstance(f, dict):
            raise Ungueltig(f"fenster[{i}]")
        fid = f.get("id")
        if not isinstance(fid, str) or not _FENSTER_ID_RE.match(fid) or fid in ids:
            raise Ungueltig(f"fenster[{i}].id")
        ids.add(fid)
        tage = f.get("tage")
        if (
            not isinstance(tage, list)
            or not tage
            or not all(_ganz(t) and 1 <= t <= 7 for t in tage)
            or len(set(tage)) != len(tage)
        ):
            raise Ungueltig(f"fenster[{i}].tage")
        von, bis = f.get("von"), f.get("bis")
        if not isinstance(von, str) or not _ZEIT_RE.match(von):
            raise Ungueltig(f"fenster[{i}].von")
        if not isinstance(bis, str) or not _ZEIT_RE.match(bis) or bis == von:
            raise Ungueltig(f"fenster[{i}].bis")
        wirkung = f.get("wirkung")
        neu: dict[str, Any] = {"id": fid, "tage": list(tage), "von": von, "bis": bis, "wirkung": wirkung}
        if wirkung == "leiser":
            grenze = f.get("grenze")
            if not _ganz(grenze) or not 0 <= grenze <= 100:
                raise Ungueltig(f"fenster[{i}].grenze")
            neu["grenze"] = grenze
        elif wirkung != "stumm":
            raise Ungueltig(f"fenster[{i}].wirkung")
        fenster.append(neu)
    return {"zeitzone": zone, "fenster": fenster}


def pruefe_gute_nacht(gn: Any) -> dict[str, Any]:
    """Prüft ``gute_nacht``: ``timer_min`` ganze Zahl 1 bis 240, ``ausblenden_s`` ganze Zahl 5 bis 600 (wie die Box)."""
    if not isinstance(gn, dict):
        raise Ungueltig("gute_nacht")
    timer, aus = gn.get("timer_min"), gn.get("ausblenden_s")
    if not _ganz(timer) or not 1 <= timer <= 240:
        raise Ungueltig("gute_nacht.timer_min")
    if not _ganz(aus) or not 5 <= aus <= 600:
        raise Ungueltig("gute_nacht.ausblenden_s")
    return {"timer_min": timer, "ausblenden_s": aus}


def pruefe_lesezeichen_tage(tage: Any) -> int:
    """Prüft ``lesezeichen_tage``: ganze Zahl 0 bis 365, ``0`` = läuft nie ab (Entscheidung N, 09.11.; wie die Box)."""
    if not _ganz(tage) or not 0 <= tage <= LESEZEICHEN_TAGE_MAX:
        raise Ungueltig("lesezeichen_tage")
    return tage


def pruefe_konfig(roh: Any) -> dict[str, Any]:
    """Prüft eine Konfiguration (Export oder Liste) und gibt die Normalform zurück.

    Entspricht ``validiere_konfig`` der Box (Migration Version 1 nach 2, dann Prüfung) plus der Prüfung
    des optionalen Tobie-Namens. Wirft ``Ungueltig``; ist irgendein Teil ungültig, wird nichts übernommen.
    """
    if not isinstance(roh, dict):
        raise Ungueltig("(Datei)")
    version = roh.get("schema_version")
    if not _ganz(version):
        raise Ungueltig("schema_version")
    if version > SCHEMA_KONFIG:
        raise Ungueltig("schema_version", "schema_zu_neu")
    if version not in (1, SCHEMA_KONFIG):
        raise Ungueltig("schema_version")
    rev, lid = roh.get("revision"), roh.get("liste_id")
    if not _ganz(rev) or rev < 1:
        raise Ungueltig("revision")
    if not isinstance(lid, str) or not RE_LISTE_ID.match(lid):
        raise Ungueltig("liste_id")
    zuo_roh = roh.get("zuordnungen")
    if not isinstance(zuo_roh, dict):
        raise Ungueltig("zuordnungen")
    zuordnungen: dict[str, Any] = {}
    for uid, z in zuo_roh.items():
        if not RE_UID.match(uid) or not isinstance(z, dict):
            raise Ungueltig(f"zuordnungen.{uid}")
        if version == 1:  # Migration: { "typ": …, … } wird zu { "ziel": { "typ": …, … } }
            ziel = pruefe_ziel({k: v for k, v in z.items() if k in ("typ", "serie", "folge", "aktion")}, f"zuordnungen.{uid}.ziel")
        else:
            ziel = pruefe_ziel(z.get("ziel"), f"zuordnungen.{uid}.ziel")
        eintrag: dict[str, Any] = {"ziel": ziel}
        if "name" in z and z["name"] is not None:
            name = z["name"]
            if not isinstance(name, str) or anzeigename(name, TOBIE_NAME_MAX) != name or not name:
                raise Ungueltig(f"zuordnungen.{uid}.name")
            eintrag["name"] = name
        if isinstance(z.get("angelegt_am"), str) and parse_iso(z["angelegt_am"]) is not None:  # V-5: bleibt erhalten (die Box ignoriert es)
            eintrag["angelegt_am"] = z["angelegt_am"]
        zuordnungen[uid] = eintrag

    leise = pruefe_leise_zeiten(roh.get("leise_zeiten"))
    gute_nacht = pruefe_gute_nacht(roh.get("gute_nacht"))

    k: dict[str, Any] = {
        "revision": rev,
        "liste_id": lid,
        "zuordnungen": zuordnungen,
        "leise_zeiten": leise,
        "gute_nacht": gute_nacht,
    }
    if isinstance(roh.get("erzeugt_am"), str):
        k["erzeugt_am"] = roh["erzeugt_am"]
    for opt in ("ton_pegel", "hinweis_pegel"):
        if opt in roh:
            if not _ganz(roh[opt]) or not 0 <= roh[opt] <= 100:
                raise Ungueltig(opt)
            k[opt] = roh[opt]
    # fehlt das Feld, gilt 14 (Entscheidung N, 09.11.)
    k["lesezeichen_tage"] = pruefe_lesezeichen_tage(roh.get("lesezeichen_tage", LESEZEICHEN_TAGE_VORGABE))
    return k


def einstellungen_aus(k: dict[str, Any]) -> dict[str, Any]:
    """Die Einstellungen einer Konfiguration (AP 4.7): Leise-Zeiten, Gute Nacht, ``lesezeichen_tage``; ``hinweis_pegel`` nur, wenn gesetzt."""
    aus: dict[str, Any] = {
        "leise_zeiten": copy.deepcopy(k["leise_zeiten"]),
        "gute_nacht": copy.deepcopy(k["gute_nacht"]),
        "lesezeichen_tage": k.get("lesezeichen_tage", LESEZEICHEN_TAGE_VORGABE),
    }
    if "hinweis_pegel" in k:
        aus["hinweis_pegel"] = k["hinweis_pegel"]
    return aus


def konfig_zu_mqtt(k: dict[str, Any]) -> dict[str, Any]:
    """Inhalt der Nachricht ``tobibox/config`` (= Schema von ``config.json``, Version 2)."""
    aus: dict[str, Any] = {
        "schema_version": SCHEMA_KONFIG,
        "revision": k["revision"],
        "liste_id": k["liste_id"],
        "erzeugt_am": k.get("erzeugt_am") or jetzt_iso(),
        "zuordnungen": k["zuordnungen"],
        "leise_zeiten": k["leise_zeiten"],
        "gute_nacht": k["gute_nacht"],
    }
    for opt in ("ton_pegel", "hinweis_pegel"):
        if opt in k:
            aus[opt] = k[opt]
    aus["lesezeichen_tage"] = k.get("lesezeichen_tage", LESEZEICHEN_TAGE_VORGABE)
    return aus


def konfig_zu_export(k: dict[str, Any], exportiert_am: str) -> dict[str, Any]:
    aus = konfig_zu_mqtt(k)
    aus["exportiert_am"] = exportiert_am
    return aus


def konfig_groesse(k: dict[str, Any]) -> int:
    return len(json.dumps(konfig_zu_mqtt(k), ensure_ascii=False).encode("utf-8"))


# --------------------------------------------------------------------------
# Export lesen (NAS)
# --------------------------------------------------------------------------


class ExportLesen:
    """Ergebnis von ``lese_export``."""

    def __init__(self, status: str, konfig: dict[str, Any] | None = None, exportiert_am: str | None = None,
                 fehler: str | None = None) -> None:
        #: "fehlt" (Ordner erreichbar, keine Datei), "ok", "ungueltig", "unerreichbar"
        self.status = status
        self.konfig = konfig
        self.exportiert_am = exportiert_am
        self.fehler = fehler


def stand_datei(n: int) -> str:
    """Dateiname eines früheren Standes: ``config.<n>.json`` (``n`` = 1 ist der jüngste frühere Stand)."""
    return f"config.{n}.json"


def lese_export(export_ordner: Path, stand: int | None = None) -> ExportLesen:
    """Liest ``export/config.json`` oder, mit ``stand``, ``export/config.<stand>.json`` (synchron, im Executor aufrufen)."""
    if not export_ordner.is_dir():
        return ExportLesen("unerreichbar")
    datei = export_ordner / (EXPORT_DATEI if stand is None else stand_datei(stand))
    if not datei.exists():
        return ExportLesen("fehlt")
    try:
        roh = dateien.lese_json(datei)
    except (OSError, ValueError) as err:
        return ExportLesen("ungueltig", fehler=str(err))
    try:
        k = pruefe_konfig(roh)
    except Ungueltig as err:
        return ExportLesen("ungueltig", fehler=str(err))
    am = roh.get("exportiert_am") if isinstance(roh.get("exportiert_am"), str) else None
    return ExportLesen("ok", k, am)


def lese_staende(export_ordner: Path) -> list[dict[str, Any]]:
    """Die vorhandenen früheren Stände (Vertrag W, 2.4): ``stand``, ``exportiert_am``, ``anzahl_zuordnungen``; nur lesbare Dateien."""
    aus: list[dict[str, Any]] = []
    for n in range(1, KONFIG_STAENDE_ANZAHL + 1):
        export = lese_export(export_ordner, n)
        if export.status == "ok" and export.konfig is not None:
            aus.append({"stand": n, "exportiert_am": export.exportiert_am, "anzahl_zuordnungen": len(export.konfig["zuordnungen"])})
    return aus


def _lege_stand_ab(aktuell: Path, ziel: Path) -> None:
    """``config.json`` als früheren Stand ablegen: wenn die Freigabe es kann, als harte Verknüpfung (schnell, ohne Lücke), sonst als Kopie.

    Der neue ``config.json`` ersetzt die Datei atomar durch eine neue; die Verknüpfung behält den alten Inhalt."""
    try:
        os.link(aktuell, ziel)
    except OSError:
        dateien.schreibe_json_atomar(ziel, dateien.lese_json(aktuell))


def _schiebe_staende(export_ordner: Path, k: dict[str, Any]) -> None:
    """Legt den bisherigen ``config.json`` als ``config.1.json`` ab, wenn er ein anderer Stand ist als der neue (alles eine Stelle weiter)."""
    aktuell = export_ordner / EXPORT_DATEI
    if not aktuell.exists():
        return
    try:
        alt = pruefe_konfig(dateien.lese_json(aktuell))
    except (OSError, ValueError, Ungueltig):
        return  # unlesbar: kein Stand, den man später zurückholen könnte
    if (alt["liste_id"], alt["revision"]) == (k["liste_id"], k["revision"]):
        return  # derselbe Stand wird nur neu geschrieben
    try:
        for n in range(KONFIG_STAENDE_ANZAHL - 1, 0, -1):
            try:
                os.replace(export_ordner / stand_datei(n), export_ordner / stand_datei(n + 1))
            except FileNotFoundError:
                continue
        _lege_stand_ab(aktuell, export_ordner / stand_datei(1))
    except (OSError, ValueError) as err:  # ein verlorener früherer Stand ist besser als kein neuer Export
        _LOGGER.warning("Früherer Stand der Liste nicht abgelegt: %s", err)


def schreibe_export(export_ordner: Path, k: dict[str, Any], exportiert_am: str) -> None:
    """Schreibt ``export/config.json`` atomar; der bisherige Stand wird ``config.1.json`` (synchron, im Executor aufrufen)."""
    export_ordner.mkdir(parents=True, exist_ok=True)
    _schiebe_staende(export_ordner, k)
    dateien.schreibe_json_atomar(export_ordner / EXPORT_DATEI, konfig_zu_export(k, exportiert_am))


def export_ist_neuer(export: ExportLesen, k: dict[str, Any], export_geschrieben_am: str | None) -> bool:
    """Vertrag W, 13.2 Punkt 2: Ist der Export neuer als der HA-Speicher?"""
    if export.status != "ok" or export.konfig is None:
        return False
    if export.konfig["liste_id"] == k["liste_id"]:
        return export.konfig["revision"] > k["revision"]
    ex = parse_iso(export.exportiert_am)
    if ex is None:
        return False
    eigen = parse_iso(export_geschrieben_am)
    return eigen is None or ex > eigen


# --------------------------------------------------------------------------
# Speicher
# --------------------------------------------------------------------------


class TobiboxStore:
    """Alles, was die Integration im HA-Speicher hält (außer dem Eingang, siehe ``eingang.py``)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.konfig: dict[str, Any] | None = None
        #: Zeitpunkt des Exports, den **dieser Speicher** zuletzt geschrieben hat (Vertrag W, 13.2)
        self.export_geschrieben_am: str | None = None
        self.neue_tobies: dict[str, dict[str, Any]] = {}
        self.box_ereignisse: dict[str, list[dict[str, Any]]] = {}
        self.lern_verlauf: list[dict[str, Any]] = []
        #: Warteschlange „nächster neuer Tobie“ (Vertrag W, 3.13): Vormerkungen in der Reihenfolge der Anlage, dazu die laufende Nummer
        self.warteschlange: list[dict[str, Any]] = []
        self.warteschlange_nr = 0
        #: K6 (13.11.): vorheriges Ziel je Kennung, ``{uid: {"ziel": …, "am": …}}``. Nur HA-Seite, **nicht** in der Konfiguration:
        #: nicht auf MQTT, nicht im Export (Vertrag W, 3.5)
        self.vorher: dict[str, dict[str, Any]] = {}
        #: ``[liste_id, revision]`` der zuletzt mit PUBACK veröffentlichten Konfiguration
        self.veroeffentlicht_stand: list[Any] | None = None
        self.war_konfiguriert = False
        #: Speicher war beim Laden leer (kein Eintrag oder ohne Konfiguration)
        self.leer_geladen = True
        self.zustand = ZUSTAND_LEER_NEU
        #: Sperre für die Konfiguration (Vertrag W, Abschnitt 1: Eingang, dann Serien, dann Konfiguration)
        self.sperre = asyncio.Lock()

    # --- Laden und Speichern -----------------------------------------------

    async def async_laden(self) -> None:
        daten = await self._store.async_load()
        self.leer_geladen = not isinstance(daten, dict) or not daten.get("konfig")
        if not isinstance(daten, dict):
            return
        if daten.get("konfig"):
            try:
                self.konfig = pruefe_konfig({"schema_version": SCHEMA_KONFIG, **daten["konfig"]})
            except Ungueltig as err:
                _LOGGER.error("Gespeicherte Konfiguration ungültig (%s); der Speicher gilt als leer", err)
                self.konfig = None
                self.leer_geladen = True
        self.export_geschrieben_am = daten.get("export_geschrieben_am")
        self.neue_tobies = daten.get("neue_tobies") or {}
        self.box_ereignisse = daten.get("box_ereignisse") or {}
        self.lern_verlauf = daten.get("lernmodus_verlauf") or []
        self._lade_warteschlange(daten.get("warteschlange"), daten.get("warteschlange_nr"))
        self._lade_vorher(daten.get("vorher"))
        self.veroeffentlicht_stand = daten.get("veroeffentlicht_stand")
        self.war_konfiguriert = bool(daten.get("war_konfiguriert")) or self.konfig is not None

    def _lade_warteschlange(self, roh: Any, nr: Any) -> None:
        """Übernimmt nur gültige Vormerkungen (Aufbau wie in Vertrag W, 3.13); Kaputtes wird verworfen."""
        liste: list[dict[str, Any]] = []
        for e in roh if isinstance(roh, list) else []:
            try:
                if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not _ganz(e.get("nr")):
                    continue
                box = e.get("box")
                if box is not None and not isinstance(box, str):
                    continue
                von = e.get("angelegt_von")
                if von is not None and not (isinstance(von, dict) and isinstance(von.get("id"), str)):
                    continue
                liste.append(
                    {
                        "id": e["id"],
                        "nr": e["nr"],
                        "box": box,
                        "ziel": pruefe_ziel(e.get("ziel"), "warteschlange.ziel"),
                        "angelegt_von": {"id": von["id"], "name": str(von.get("name") or "")} if von else None,
                        "angelegt_am": e["angelegt_am"] if isinstance(e.get("angelegt_am"), str) else jetzt_iso(),
                        # K7 (13.11.): optionaler Name des Tobies; Alteinträge haben keinen
                        "name": e["name"] if isinstance(e.get("name"), str) and e["name"] else None,
                    }
                )
            except Ungueltig:
                continue
        liste.sort(key=lambda e: e["nr"])
        self.warteschlange = liste
        hoechste = liste[-1]["nr"] if liste else 0
        self.warteschlange_nr = max(nr if _ganz(nr) else 0, hoechste)

    def _lade_vorher(self, roh: Any) -> None:
        """K6: übernimmt nur gültige Einträge (``ziel`` und ``am``); Kaputtes wird verworfen."""
        neu: dict[str, dict[str, Any]] = {}
        for uid, v in roh.items() if isinstance(roh, dict) else []:
            try:
                if isinstance(uid, str) and isinstance(v, dict) and isinstance(v.get("am"), str):
                    neu[uid] = {"ziel": pruefe_ziel(v.get("ziel"), "vorher.ziel"), "am": v["am"]}
            except Ungueltig:
                continue
        self.vorher = neu

    def _daten(self) -> dict[str, Any]:
        k = None
        if self.konfig is not None:
            k = {key: v for key, v in self.konfig.items()}
        return {
            "konfig": k,
            "export_geschrieben_am": self.export_geschrieben_am,
            "neue_tobies": self.neue_tobies,
            "box_ereignisse": self.box_ereignisse,
            "lernmodus_verlauf": self.lern_verlauf,
            "warteschlange": self.warteschlange,
            "warteschlange_nr": self.warteschlange_nr,
            "vorher": self.vorher,
            "veroeffentlicht_stand": self.veroeffentlicht_stand,
            "war_konfiguriert": self.war_konfiguriert,
        }

    async def async_speichern(self) -> None:
        """Sofort schreiben (nach jeder Änderung der Konfiguration)."""
        await self._store.async_save(self._daten())

    def speichern_verzoegert(self, sekunden: float = 5.0) -> None:
        """Später schreiben (Neue Tobies, Meldungen): geht bei einem Neustart höchstens kurz verloren."""
        self._store.async_delay_save(self._daten, sekunden)

    # --- Konfiguration -------------------------------------------------------

    @property
    def revision(self) -> int | None:
        return self.konfig["revision"] if self.konfig else None

    @property
    def liste_id(self) -> str | None:
        return self.konfig["liste_id"] if self.konfig else None

    def setze_liste(self, konfig: dict[str, Any]) -> None:
        """Ersetzt die ganze Konfiguration (Erststart, neu ausrollen, aus Export). Speichern macht der Aufrufer."""
        self.konfig = konfig
        self.vorher = {}  # K6: gehört zur alten Liste
        self.war_konfiguriert = True

    async def async_aendere(
        self,
        mutator: Callable[[dict[str, Any]], None],
        mit_warteschlange: Callable[[], None] | None = None,
        mit_vorher: Callable[[dict[str, dict[str, Any]]], None] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Ändert die Konfiguration unter der Sperre; erhöht die Revision nur bei einer echten Änderung.

        Der Mutator ändert eine Kopie; er darf ``TobiboxFehler`` werfen. Rückgabe: ``(geaendert, konfig)``.
        Gespeichert wird vor der Rückkehr; scheitert das Speichern, bleibt der alte Stand (Fehler ``speicherfehler``).

        ``mit_warteschlange``: ändert bei einer echten Änderung der Konfiguration die Warteschlange (``self.warteschlange``)
        im **selben** Schreibvorgang (Vertrag W, 3.13, Regel 7b): Nach einem Absturz oder einem Speicherfehler gilt beides oder nichts.

        ``mit_vorher``: ändert bei einer echten Änderung eine Kopie von ``self.vorher`` (K6, Vertrag W, 3.5), ebenfalls im selben Schreibvorgang.
        """
        async with self.sperre:
            if self.zustand != ZUSTAND_OK or self.konfig is None:
                raise TobiboxFehler("konfig_nicht_bereit")
            neu = copy.deepcopy(self.konfig)
            mutator(neu)
            vergleich_alt = {k: v for k, v in self.konfig.items() if k not in ("revision", "erzeugt_am")}
            vergleich_neu = {k: v for k, v in neu.items() if k not in ("revision", "erzeugt_am")}
            if vergleich_alt == vergleich_neu:
                return False, self.konfig
            neu["revision"] = self.konfig["revision"] + 1
            neu["erzeugt_am"] = jetzt_iso()
            if konfig_groesse(neu) > KONFIG_MAX_BYTES:
                raise TobiboxFehler("konfig_zu_gross")
            alt = self.konfig
            alt_warteschlange = (self.warteschlange, self.warteschlange_nr)
            alt_vorher = self.vorher
            try:
                if mit_vorher is not None:
                    self.vorher = copy.deepcopy(self.vorher)
                    mit_vorher(self.vorher)
                if mit_warteschlange is not None:
                    self.warteschlange = copy.deepcopy(self.warteschlange)
                    mit_warteschlange()
                self.konfig = neu
                await self.async_speichern()
            except Exception:
                self.konfig = alt
                self.warteschlange, self.warteschlange_nr = alt_warteschlange
                self.vorher = alt_vorher
                raise
            return True, self.konfig

    def stand(self, export_ok: bool) -> dict[str, Any]:
        """Konfig-Stand für die Seite (Vertrag W, „Gemeinsame Objekte“)."""
        leer = self.zustand == ZUSTAND_LEER_NEU or self.konfig is None
        return {
            "revision": None if leer else self.konfig["revision"],  # type: ignore[index]
            "liste_id": None if leer else self.konfig["liste_id"],  # type: ignore[index]
            "zustand": self.zustand,
            "export_ok": export_ok,
            "export_geschrieben_am": self.export_geschrieben_am,
        }

    # --- Neue Tobies ---------------------------------------------------------

    def neue_tobies_melden(self, box: str, uid: str, meldung: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Nimmt eine Meldung auf. Ersetzt den Wert dieser Box (die Zahl in der Nachricht ist schon die Summe der Box).

        Gibt ``("neu" | "aktualisiert", eintrag)`` zurück.
        """
        art = "aktualisiert" if uid in self.neue_tobies else "neu"
        eintrag = self.neue_tobies.setdefault(uid, {"uid": uid, "boxen": {}})
        eintrag["boxen"][box] = {
            "zuerst": meldung["zuerst"],
            "zuletzt": meldung["zuletzt"],
            "anzahl": meldung["anzahl"],
            "zeit_ok": bool(meldung.get("zeit_ok", True)),
        }
        self._neu_berechnen(eintrag)
        self.speichern_verzoegert()
        return art, eintrag

    @staticmethod
    def _neu_berechnen(eintrag: dict[str, Any]) -> None:
        boxen = eintrag["boxen"].values()
        eintrag["zuerst"] = min((b["zuerst"] for b in boxen), key=lambda s: parse_iso(s) or jetzt())
        eintrag["zuletzt"] = max((b["zuletzt"] for b in boxen), key=lambda s: parse_iso(s) or jetzt())
        eintrag["anzahl"] = sum(int(b["anzahl"]) for b in boxen)

    def neue_tobies_entfernen(self, uid: str) -> bool:
        if self.neue_tobies.pop(uid, None) is None:
            return False
        self.speichern_verzoegert()
        return True

    def neue_tobies_liste(self) -> list[dict[str, Any]]:
        return sorted(self.neue_tobies.values(), key=lambda e: parse_iso(e["zuletzt"]) or iso(jetzt()), reverse=True)

    # --- Box-Meldungen und Lernmodus-Verlauf --------------------------------------

    def box_ereignis_hinzu(self, box: str, ereignis: dict[str, Any]) -> bool:
        """Merkt die Meldung (neueste zuerst, höchstens 20 je Box). ``False``, wenn die ``id`` schon bekannt ist."""
        liste = self.box_ereignisse.setdefault(box, [])
        if any(e["id"] == ereignis["id"] for e in liste):
            return False
        liste.insert(0, ereignis)
        del liste[BOX_EREIGNISSE_MAX:]
        self.speichern_verzoegert()
        return True

    def lern_verlauf_hinzu(self, eintrag: dict[str, Any]) -> None:
        self.lern_verlauf = [e for e in self.lern_verlauf if e.get("befehl_id") != eintrag["befehl_id"]]
        self.lern_verlauf.append(eintrag)
        del self.lern_verlauf[:-LERN_VERLAUF_MAX]
        self.speichern_verzoegert()
