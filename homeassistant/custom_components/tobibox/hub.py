"""Der gemeinsame Zustand der Integration (``Hub``).

Hier laufen die Fäden zusammen: Speicher, Medien, Eingang, MQTT und Lernmodus; die Ereignisse für die Seite
(Abos); der Export auf das NAS; die Prüfung beim Start (Vertrag W, Abschnitt 13); die Zuordnungen.
Die WebSocket-Befehle, die HA-Aktionen und die Eingaben auf ``tobibox/<box>/ui/…`` rufen alle **dieselben**
Funktionen (Vertrag W, Abschnitt 1).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.components import mqtt as ha_mqtt
from homeassistant.components import persistent_notification
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .const import (
    ANFRAGE_ID_ANZAHL,
    ANFRAGE_ID_DAUER_S,
    CONF_BOXEN,
    CONF_MEDIEN_PFAD,
    CONF_UPLOAD_MAX_MIB,
    EREIGNIS_BUENDEL_S,
    EXPORT_WIEDERHOLUNG_DANACH_S,
    EXPORT_WIEDERHOLUNG_S,
    FAEHIGKEITEN,
    FOLGE_ANZEIGE_MAX,
    LIMIT_MAX,
    ORDNER_EINGANG,
    ORDNER_EXPORT,
    ORDNER_PAPIERKORB,
    ORDNER_RELEASES,
    ORDNER_UPLOAD,
    PRUEF_INTERVALL_S,
    RE_UID,
    SERIE_NAME_MAX,
    START_WARTEZEIT_S,
    SYNC_TTL_S,
    TOBIE_NAME_MAX,
    UPLOAD_BLOCK_BYTES,
    UPLOAD_MAX_MIB_VORGABE,
    UPLOAD_PARALLEL,
    VERTRAG_V,
    ENDUNGEN,
)
from .eingang import Eingang
from .fehler import TobiboxFehler
from .lernmodus import Lernmodus
from .media import Medien, name_pruefen
from .mqtt import MqttSchicht
from .schutz import Nutzer, Schutz, ist_admin
from .store import (
    ZUSTAND_EXPORT_NEUER,
    ZUSTAND_LEER_NEU,
    ZUSTAND_OK,
    TobiboxStore,
    einstellungen_aus,
    export_ist_neuer,
    lese_export,
    lese_staende,
    neue_konfig,
    pruefe_gute_nacht,
    pruefe_leise_zeiten,
    pruefe_lesezeichen_tage,
    pruefe_ziel,
    schreibe_export,
    Ungueltig,
)
from .util import jetzt_iso

_LOGGER = logging.getLogger(__name__)

#: Wartezeiten des Exports nach einem Fehler (Vertrag W, 13.5); in Tests kürzbar
EXPORT_WARTEN: tuple[float, ...] = EXPORT_WIEDERHOLUNG_S
EXPORT_WARTEN_DANACH: float = EXPORT_WIEDERHOLUNG_DANACH_S
#: Wartezeit auf die dauerhaften ``status``-Nachrichten beim Start (Vertrag W, 13.2); in Tests kürzbar
START_WARTEN: float = START_WARTEZEIT_S

#: „Feld fehlt“ (anders als ``None``)
FEHLT: Any = object()


@dataclass(frozen=True)
class Pfade:
    """Die Ordner der Freigabe. ``eingang``, ``export`` und ``releases`` liegen **neben** ``medien`` (Vertrag W, 11.1)."""

    medien: Path

    @property
    def basis(self) -> Path:
        return self.medien.parent

    @property
    def eingang(self) -> Path:
        return self.basis / ORDNER_EINGANG

    @property
    def export(self) -> Path:
        return self.basis / ORDNER_EXPORT

    @property
    def releases(self) -> Path:
        return self.basis / ORDNER_RELEASES

    @property
    def papierkorb(self) -> Path:
        return self.medien / ORDNER_PAPIERKORB

    @property
    def upload(self) -> Path:
        return self.medien / ORDNER_UPLOAD


@dataclass
class Abo:
    """Ein Abo einer Seite (``tobibox/subscribe``)."""

    connection: Any
    msg_id: int
    themen: set[str]
    nutzer_id: str | None


class _Sicher(dict):
    def __missing__(self, key: str) -> str:
        return ""


class Hub:
    """Alles, was die Integration zur Laufzeit braucht."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        einstellung = {**entry.data, **entry.options}
        self.pfade = Pfade(Path(einstellung[CONF_MEDIEN_PFAD]))
        self.boxen: list[str] = list(einstellung.get(CONF_BOXEN, []))
        mib = einstellung.get(CONF_UPLOAD_MAX_MIB, UPLOAD_MAX_MIB_VORGABE)
        self.upload_max_bytes = int(mib) * 1024 * 1024
        self.version = "0"
        self.texte: dict[str, str] = {}
        self.abos: list[Abo] = []
        self.store = TobiboxStore(hass)
        self.schutz = Schutz(self)
        self.medien = Medien(self)
        self.eingang = Eingang(self)
        self.mqtt = MqttSchicht(self)
        self.lernmodus = Lernmodus(self)
        self.export_ok = False
        self._export_task: asyncio.Task | None = None
        self._export_neu = False
        self._export_fehler_seit: str | None = None
        self.start_fertig = asyncio.Event()
        self._start_task: asyncio.Task | None = None
        self._abmelden: list[Callable[[], None]] = []
        self._buendel: dict[tuple, dict[str, Any]] = {}
        self._anfragen: OrderedDict[str, tuple[str, str, Any, float]] = OrderedDict()
        self._anfragen_laufend: dict[str, asyncio.Task] = {}
        #: Upload-Zustand (``http.py``)
        self.uploads_laufend: set[str] = set()
        self.upload_zaehler = 0
        self.upload_ergebnisse: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._nachholen_sperre = asyncio.Lock()
        self._timer: set[Callable[[], None]] = set()

    # --- Start und Ende --------------------------------------------------------------------

    async def async_start(self, version: str) -> None:
        self.version = version
        self.texte = await self.hass.async_add_executor_job(_lade_texte)
        await self.store.async_laden()
        await self.eingang.async_laden()
        await self.mqtt.async_start()
        self._start_task = self.hass.async_create_background_task(self._start_pruefung(), "tobibox_start")
        self._abmelden.append(
            async_track_time_interval(self.hass, self._timer_pruefung, timedelta(seconds=PRUEF_INTERVALL_S))
        )

    def plane(self, sekunden: float, fn: Callable[[Any], Awaitable[None]]) -> Callable[[], None]:
        """Ein Zeitgeber, der beim Beenden der Integration sicher abgemeldet wird. Gibt die Abmeldefunktion zurück."""

        async def lauf(jetzt_: Any) -> None:
            self._timer.discard(abbruch)
            await fn(jetzt_)

        abbruch = async_call_later(self.hass, sekunden, lauf)
        self._timer.add(abbruch)
        return abbruch

    async def async_stop(self) -> None:
        for fn in self._abmelden:
            fn()
        self._abmelden.clear()
        for fn in list(self._timer):
            fn()
        self._timer.clear()
        for v in list(self.lernmodus.vorgaenge.values()):
            self.lernmodus._timer_loeschen(v)
        self.mqtt.async_stop()
        self.eingang.abbrechen()
        for t in (self._start_task, self._export_task):
            if t is not None and not t.done():
                t.cancel()
        for t in (self._start_task, self._export_task):
            if t is not None:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await t
        with contextlib.suppress(Exception):
            await self.store.async_speichern()
            await self.eingang.speichern_sofort()

    async def _timer_pruefung(self, _now: Any) -> None:
        """Alle 10 min: Freigabe prüfen, danach den Eingang (Vertrag W, Nr. 9 und 30)."""
        try:
            await self.medien.pruefen()
        except TobiboxFehler as err:
            _LOGGER.warning("Prüfung der Freigabe nicht möglich: %s", err.code)
            return
        except Exception:
            _LOGGER.exception("Prüfung der Freigabe fehlgeschlagen")
            return
        with contextlib.suppress(TobiboxFehler):
            await self.eingang.starte_durchlauf()

    # --- Texte ---------------------------------------------------------------------------------

    def t(self, key: str, **kw: Any) -> str:
        text = self.texte.get(key)
        if text is None:
            return key
        try:
            return text.format_map(_Sicher(kw))
        except (ValueError, IndexError):
            return text

    def fehler_text(self, err: TobiboxFehler) -> str:
        return self.t(err.code, **err.details)

    def benachrichtige(self, nid: str, titel_key: str, text_key: str | None, **kw: Any) -> None:
        text = kw["text"] if text_key is None else self.t(text_key, **kw)
        persistent_notification.async_create(self.hass, text, self.t(titel_key), nid)

    def benachrichtigung_entfernen(self, nid: str) -> None:
        persistent_notification.async_dismiss(self.hass, nid)

    # --- Ereignisse für die Seite (Vertrag W, Abschnitt 4) ---------------------------------------------

    def abo_hinzu(self, abo: Abo) -> Callable[[], None]:
        self.abos.append(abo)

        def entfernen() -> None:
            with contextlib.suppress(ValueError):
                self.abos.remove(abo)

        return entfernen

    def _sende(self, abo: Abo, thema: str, art: str, daten: dict[str, Any]) -> None:
        nachricht = {"v": VERTRAG_V, "thema": thema, "art": art, "daten": daten}
        try:
            abo.connection.send_message(websocket_api.event_message(abo.msg_id, nachricht))
        except Exception:  # eine kaputte Verbindung darf andere Abos nicht stören
            _LOGGER.debug("Ereignis an Abo %s nicht gesendet", abo.msg_id, exc_info=True)

    def emit(self, thema: str, art: str, daten: dict[str, Any] | None = None, *, nutzer_id: str | None = None) -> None:
        """Sendet ein Ereignis an alle Abos, die das Thema abonniert haben (bei ``nutzer_id`` nur dessen Abos)."""
        for abo in list(self.abos):
            if thema in abo.themen and (nutzer_id is None or abo.nutzer_id == nutzer_id):
                self._sende(abo, thema, art, daten or {})

    def emit_gebuendelt(self, schluessel: tuple, thema: str, art: str, daten_fn: Callable[[], dict[str, Any]]) -> None:
        """Höchstens ein Ereignis je Schlüssel und Sekunde: das erste sofort, weitere zusammengefasst (Abschnitt 4)."""
        z = self._buendel.get(schluessel)
        if z is None:
            self._buendel[schluessel] = {"wartet": False}
            self.emit(thema, art, daten_fn())

            async def frei(_now: Any) -> None:
                z2 = self._buendel.pop(schluessel, None)
                if z2 and z2["wartet"]:
                    self.emit_gebuendelt(schluessel, thema, art, daten_fn)

            self.plane(EREIGNIS_BUENDEL_S, frei)
        else:
            z["wartet"] = True

    def snapshot(self, thema: str) -> dict[str, Any]:
        if thema == "boxen":
            return {"boxen": [{"box": b, "online": z.online, "konfig_stand": self.mqtt.konfig_stand_von(z)} for b, z in self.mqtt.boxen.items()]}
        if thema == "neue_tobies":
            return {"gesamt": len(self.store.neue_tobies)}
        if thema == "lernmodus":
            return {"vorgaenge": self.lernmodus.zu_snapshot()}
        if thema == "medien":
            return {"pruefung_laeuft": self.medien.pruefung_laeuft, "geprueft_am": self.medien.geprueft_am}
        if thema == "eingang":
            return self.eingang.zaehler_snapshot()
        if thema == "konfig":
            return {"konfig": self.konfig_stand()}
        return {}

    def box_geaendert(self, box: str) -> None:
        self.emit_gebuendelt(("boxen", box), "boxen", "geaendert", lambda: self.box_objekt(box, mit_ereignisse=False))

    def konfig_geaendert(self) -> None:
        self.emit_gebuendelt(("konfig",), "konfig", "geaendert", lambda: {"konfig": self.konfig_stand()})

    # --- Boxen -----------------------------------------------------------------------------------

    def box_objekt(self, box: str, mit_ereignisse: bool = True) -> dict[str, Any]:
        z = self.mqtt.boxen[box]
        v = self.lernmodus.offener_vorgang(box)
        aus: dict[str, Any] = {
            "box": box,
            "anzeigename": z.anzeigename,
            "online": z.online,
            "status": z.status,
            "status_empfangen_am": z.status_empfangen_am,
            "konfig_stand": self.mqtt.konfig_stand_von(z),
            "lernmodus": v.zu_daten() if v else None,
        }
        if mit_ereignisse:
            aus["ereignisse"] = list(self.store.box_ereignisse.get(box, []))
        return aus

    def boxen_liste(self, mit_ereignisse: bool = True) -> list[dict[str, Any]]:
        """``mit_ereignisse=False`` für Nicht-Administratoren: das Feld ``ereignisse`` ist seit 12.11. nur Administratoren erlaubt."""
        return [self.box_objekt(b, mit_ereignisse) for b in self.boxen]

    async def box_sync(self, box: str) -> dict[str, Any]:
        z = self.mqtt.boxen.get(box)
        if z is None:
            raise TobiboxFehler("box_unbekannt")
        if z.online is not True:
            raise TobiboxFehler("box_offline")
        befehl_id = await self.mqtt.sende_befehl(box, "sync", SYNC_TTL_S)
        return {"befehl_id": befehl_id, "ttl_s": SYNC_TTL_S}

    async def ui_sync(self, box: str) -> None:
        try:
            await self.box_sync(box)
        except TobiboxFehler as err:
            self.benachrichtige(f"tobibox_ui_{box}", "benachrichtigung_ui_titel", None, text=f"{box}: {self.fehler_text(err)}")

    async def ui_update(self, box: str) -> None:
        try:
            if self.mqtt.boxen[box].online is not True:
                raise TobiboxFehler("box_offline")
            await self.mqtt.sende_update(box)
        except TobiboxFehler as err:
            self.benachrichtige(f"tobibox_ui_{box}", "benachrichtigung_ui_titel", None, text=f"{box}: {self.fehler_text(err)}")

    async def ui_lernen_abbrechen(self, box: str) -> None:
        try:
            await self.lernmodus.abbrechen(box)
        except TobiboxFehler as err:
            self.benachrichtige(f"tobibox_ui_{box}", "benachrichtigung_ui_titel", None, text=f"{box}: {self.fehler_text(err)}")

    # --- Hilfen: Tobies, Ziele -------------------------------------------------------------------

    def tobies(self, pred: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
        """Tobie-Kurzform (``uid``, ``name``) aller Zuordnungen, deren ``ziel`` zum Prädikat passt."""
        k = self.store.konfig
        if not k:
            return []
        return [
            {"uid": uid, "name": z.get("name")}
            for uid, z in sorted(k["zuordnungen"].items())
            if pred(z["ziel"])
        ]

    def ziel_text(self, ziel: dict[str, Any]) -> str:
        if ziel.get("typ") == "aktion":
            return self.t(f"ziel_aktion_{ziel.get('aktion')}")
        info = self.medien.serien.get(ziel.get("serie", ""))
        serie_name = info.serie.name if info else ziel.get("serie", "?")
        if ziel.get("typ") == "folge":
            anzeige = info.serie.anzeige(ziel["folge"]) if info else ziel.get("folge", "?")
            return self.t("ziel_folge", folge=anzeige, serie=serie_name)
        return self.t("ziel_serie", serie=serie_name)

    # --- Konfiguration: ändern, veröffentlichen, exportieren ---------------------------------------------------

    def konfig_stand(self) -> dict[str, Any]:
        return self.store.stand(self.export_ok)

    async def aendere_konfig(self, mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Konfiguration ändern: speichern (Revision + 1), **dann veröffentlichen, dann exportieren** (Vertrag W, Abschnitt 1)."""
        geaendert, _konfig = await self.store.async_aendere(mutator)
        if not geaendert:
            return {"geaendert": False, "konfig": self.konfig_stand(), "veroeffentlicht": None}
        veroeffentlicht = await self.mqtt.veroeffentliche_konfig()
        self.export_planen()
        self.konfig_geaendert()
        return {"geaendert": True, "konfig": self.konfig_stand(), "veroeffentlicht": veroeffentlicht}

    async def stelle_veroeffentlicht_sicher(self) -> bool:
        """Ist die aktuelle Konfiguration mit PUBACK veröffentlicht? Sonst jetzt veröffentlichen."""
        k = self.store.konfig
        if self.store.zustand != ZUSTAND_OK or k is None:
            return False
        if self.store.veroeffentlicht_stand == [k["liste_id"], k["revision"]]:
            return True
        return await self.mqtt.veroeffentliche_konfig()

    async def nachholen(self) -> None:
        """Broker wieder da: offene Veröffentlichung und offene ``ack`` nachholen (Vertrag W, 13.6)."""
        async with self._nachholen_sperre:
            if not self.start_fertig.is_set():
                return
            if self.store.zustand == ZUSTAND_OK:
                await self.stelle_veroeffentlicht_sicher()
            await self.lernmodus.nachholen()

    def export_planen(self) -> None:
        """Startet (oder verlängert) den Export im Hintergrund. Nur im Zustand ``ok`` (sonst würde ein neuerer Export überschrieben)."""
        if self.store.zustand != ZUSTAND_OK or self.store.konfig is None:
            return
        self.export_ok = False
        if self._export_task is not None and not self._export_task.done():
            self._export_neu = True
            return
        self._export_task = self.hass.async_create_background_task(self._export_lauf(), "tobibox_export")

    async def _export_lauf(self) -> None:
        versuch = 0
        while True:
            if self.store.zustand != ZUSTAND_OK or self.store.konfig is None:
                return
            konfig = self.store.konfig
            am = jetzt_iso()
            self._export_neu = False
            try:
                await self.hass.async_add_executor_job(schreibe_export, self.pfade.export, konfig, am)
            except (OSError, ValueError) as err:
                versuch += 1
                self.export_ok = False
                if self._export_fehler_seit is None:
                    self._export_fehler_seit = jetzt_iso()
                    _LOGGER.warning("Export auf das NAS fehlgeschlagen: %s", err)
                    self.emit("konfig", "export_fehler", {"seit": self._export_fehler_seit, "text": self.t("export_fehler", fehler=str(err))})
                    self.konfig_geaendert()
                    self.benachrichtige("tobibox_export", "benachrichtigung_export_fehler_titel", "benachrichtigung_export_fehler", fehler=str(err))
                warten = EXPORT_WARTEN[versuch - 1] if versuch <= len(EXPORT_WARTEN) else EXPORT_WARTEN_DANACH
                await asyncio.sleep(warten)
                continue
            self.store.export_geschrieben_am = am
            self.store.speichern_verzoegert(1.0)
            if self.store.konfig is not konfig or self._export_neu:
                versuch = 0
                continue  # inzwischen gab es eine neuere Revision
            self.export_ok = True
            if self._export_fehler_seit is not None:
                self._export_fehler_seit = None
                self.benachrichtigung_entfernen("tobibox_export")
                self.emit("konfig", "export_ok", {"export_geschrieben_am": am})
            self.konfig_geaendert()
            return

    # --- Start: Zustand der Konfiguration (Vertrag W, Abschnitt 13) ---------------------------------------------------

    async def _warte_auf_status(self, wartezeit: float) -> None:
        """Wartet auf die dauerhaften ``status``-Nachrichten aller Boxen (höchstens ``wartezeit``)."""
        ende = self.hass.loop.time() + wartezeit
        while self.hass.loop.time() < ende:
            if all(z.status is not None for z in self.mqtt.boxen.values()):
                return
            await asyncio.sleep(min(0.05, max(0.0, ende - self.hass.loop.time())))

    async def _start_pruefung(self) -> None:
        try:
            await self._bestimme_zustand()
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Prüfung des Speichers beim Start fehlgeschlagen")
            if self.store.zustand != ZUSTAND_OK:
                self.store.zustand = ZUSTAND_LEER_NEU
        finally:
            self.start_fertig.set()
        if self.store.zustand == ZUSTAND_OK:
            await self.nachholen()
            if not self.export_ok:
                self.export_planen()
        # die erste Prüfung der Freigabe und des Eingangs
        with contextlib.suppress(Exception):
            await self._timer_pruefung(None)

    async def _bestimme_zustand(self) -> None:
        store = self.store
        export = await self.hass.async_add_executor_job(lese_export, self.pfade.export)
        if store.konfig is None:
            if self.mqtt.ist_verbunden() or self.mqtt.boxen:
                with contextlib.suppress(Exception):
                    await ha_mqtt.async_wait_for_mqtt_client(self.hass)
            await self._warte_auf_status(START_WARTEN)
            box_hat_liste = any(
                ((z.status or {}).get("konfig") or {}).get("liste_id") for z in self.mqtt.boxen.values()
            )
            if export.status == "fehlt" and not box_hat_liste and not store.war_konfiguriert:
                # Erststart: neue Liste anlegen und veröffentlichen
                store.setze_liste(neue_konfig())
                store.zustand = ZUSTAND_OK
                await store.async_speichern()
                await self.mqtt.veroeffentliche_konfig()
                self.export_planen()
                self.konfig_geaendert()
                return
            store.zustand = ZUSTAND_LEER_NEU
            self.konfig_geaendert()
            return
        self.export_ok = (
            export.status == "ok"
            and export.konfig is not None
            and (export.konfig["liste_id"], export.konfig["revision"]) == (store.konfig["liste_id"], store.konfig["revision"])
        )
        if export_ist_neuer(export, store.konfig, store.export_geschrieben_am):
            store.zustand = ZUSTAND_EXPORT_NEUER
        else:
            store.zustand = ZUSTAND_OK
        self.konfig_geaendert()

    # --- Wege aus leer_neu und export_neuer -------------------------------------------------------------------

    async def konfig_export_lesen(self, stand: int | None = None) -> dict[str, Any]:
        """``stand``: ein früherer Stand der Liste (``export/config.<stand>.json``, Vertrag W, 2.4); ``None`` = der aktuelle Export."""
        export = await self.hass.async_add_executor_job(lese_export, self.pfade.export, stand)
        if export.status == "unerreichbar":
            raise TobiboxFehler("medien_nicht_erreichbar")
        if stand is not None and export.status == "fehlt":
            raise TobiboxFehler("export_nicht_gefunden")
        aus: dict[str, Any] = {
            "vorhanden": False,
            "liste_id": None,
            "revision": None,
            "exportiert_am": None,
            "anzahl_zuordnungen": None,
            "anzahl_fenster": None,
            "neuer_als_ha": False,
            "konfig": self.konfig_stand(),
        }
        if export.status == "ok" and export.konfig is not None:
            k = export.konfig
            aus.update(
                {
                    "vorhanden": True,
                    "liste_id": k["liste_id"],
                    "revision": k["revision"],
                    "exportiert_am": export.exportiert_am,
                    "anzahl_zuordnungen": len(k["zuordnungen"]),
                    "anzahl_fenster": len(k["leise_zeiten"]["fenster"]),
                    "neuer_als_ha": stand is None
                    and (True if self.store.konfig is None else export_ist_neuer(export, self.store.konfig, self.store.export_geschrieben_am)),
                }
            )
        aus["staende"] = await self.hass.async_add_executor_job(lese_staende, self.pfade.export)
        return aus

    async def konfig_aus_export(self, stand: int | None = None) -> dict[str, Any]:
        """Holt die Konfiguration aus dem Export zurück: neue Listen-ID, Revision 1, ``zustand=ok`` (Vertrag W, Nr. 32).

        Mit ``stand`` aus einem früheren Stand der Liste (2.4)."""
        export = await self.hass.async_add_executor_job(lese_export, self.pfade.export, stand)
        if export.status == "unerreichbar":
            raise TobiboxFehler("medien_nicht_erreichbar")
        if export.status == "fehlt":
            raise TobiboxFehler("export_nicht_gefunden")
        if export.status != "ok" or export.konfig is None:
            raise TobiboxFehler("export_ungueltig")
        alt = export.konfig
        einstellungen = {k: alt[k] for k in ("leise_zeiten", "gute_nacht", "ton_pegel", "hinweis_pegel", "lesezeichen_tage") if k in alt}
        async with self.store.sperre:
            neu = neue_konfig(alt["zuordnungen"], einstellungen)
            await self._setze_neue_liste(neu)
        veroeffentlicht = await self.mqtt.veroeffentliche_konfig()
        self.export_planen()
        self.konfig_geaendert()
        return {
            "konfig": self.konfig_stand(),
            "veroeffentlicht": veroeffentlicht,
            "uebernommen": {"zuordnungen": len(neu["zuordnungen"]), "fenster": len(neu["leise_zeiten"]["fenster"])},
        }

    async def liste_neu_ausrollen(self) -> dict[str, Any]:
        """Neue Listen-ID, Revision 1, gleiche Zuordnungen und Einstellungen; in jedem Zustand erlaubt (Vertrag W, Nr. 23)."""
        async with self.store.sperre:
            alt = self.store.konfig
            if alt is not None:
                einstellungen = {k: alt[k] for k in ("leise_zeiten", "gute_nacht", "ton_pegel", "hinweis_pegel", "lesezeichen_tage") if k in alt}
                neu = neue_konfig(alt["zuordnungen"], einstellungen)
            else:
                neu = neue_konfig()
            await self._setze_neue_liste(neu)
        veroeffentlicht = await self.mqtt.veroeffentliche_konfig()
        self.export_planen()
        self.konfig_geaendert()
        return {"konfig": self.konfig_stand(), "veroeffentlicht": veroeffentlicht}

    async def _setze_neue_liste(self, neu: dict[str, Any]) -> None:
        """Unter ``store.sperre`` aufrufen."""
        store = self.store
        alt_konfig, alt_zustand = store.konfig, store.zustand
        store.setze_liste(neu)
        store.zustand = ZUSTAND_OK
        store.veroeffentlicht_stand = None
        try:
            await store.async_speichern()
        except Exception:
            store.konfig, store.zustand = alt_konfig, alt_zustand
            raise

    # --- Neue Tobies (Weg A) -----------------------------------------------------------------------------------

    async def neue_kennung(self, box: str, uid: str, daten: dict[str, Any]) -> None:
        """Eine Kennung wurde auf ``tobibox/<box>/unknown/<uid>`` gemeldet (Vertrag W, 3.4 und 6.1)."""
        store = self.store
        zuletzt, art = daten["zuletzt"], daten["art"]
        if art == "gelernt":
            await self.lernmodus.on_gelernt(box, uid, daten)
            return
        bekannt_in_liste = store.konfig is not None and uid in store.konfig["zuordnungen"]
        if bekannt_in_liste:
            await self.mqtt.sende_ack(box, uid, zuletzt, art, "bekannt")
            return
        ereignis, eintrag = store.neue_tobies_melden(box, uid, daten)
        self.emit("neue_tobies", ereignis, {"eintrag": eintrag})
        await self.mqtt.sende_ack(box, uid, zuletzt, art, "neu" if ereignis == "neu" else "bekannt")

    def kennung_bekannt(self, uid: str) -> bool:
        """Ist die Kennung gemeldet (``neue_tobies``), schon zugeordnet oder Ergebnis eines Lernmodus? (Vertrag W, 2.4)"""
        k = self.store.konfig
        if uid in self.store.neue_tobies or (k is not None and uid in k["zuordnungen"]):
            return True
        if any(e.get("uid") == uid for e in self.store.lern_verlauf):
            return True
        return any(v.uid == uid for v in self.lernmodus.vorgaenge.values())

    def kennung_zugeordnet(self, uid: str) -> None:
        if self.store.neue_tobies_entfernen(uid):
            self.emit("neue_tobies", "entfernt", {"uid": uid, "grund": "zugeordnet"})

    def neue_tobies_liste(self, limit: int, offset: int) -> dict[str, Any]:
        alle = self.store.neue_tobies_liste()
        return {"eintraege": alle[offset : offset + limit], "gesamt": len(alle)}

    def neue_tobies_verwerfen(self, uid: str) -> dict[str, Any]:
        if not RE_UID.match(uid):
            raise TobiboxFehler("kennung_ungueltig")
        entfernt = self.store.neue_tobies_entfernen(uid)
        if entfernt:
            self.emit("neue_tobies", "entfernt", {"uid": uid, "grund": "verworfen"})
        return {"entfernt": entfernt}

    # --- Zuordnungen -------------------------------------------------------------------------------------------------

    async def pruefe_ziel(self, roh: Any, *, lernmodus: bool = False) -> dict[str, Any]:
        """Prüft ein ``ziel`` (Vertrag W, 3.5): Struktur, Serie, Folge, Aktion; die Überraschungs-Serie ist verboten."""
        try:
            ziel = pruefe_ziel(roh, "ziel")
        except Ungueltig as err:
            raise TobiboxFehler("ziel_ungueltig") from err
        if ziel["typ"] == "aktion":
            return ziel
        await self.medien._stelle_geprueft_sicher()
        info = self.medien.serien.get(ziel["serie"])
        if info is None:
            raise TobiboxFehler("serie_nicht_gefunden")
        if info.serie.typ == "ueberraschung":
            raise TobiboxFehler("ziel_ungueltig")
        if ziel["typ"] == "folge" and ziel["folge"] not in info.serie.folgen:
            raise TobiboxFehler("folge_nicht_gefunden")
        return ziel

    async def zuordnung_setzen(
        self,
        uid: str,
        ziel_roh: Any,
        name: Any = FEHLT,
        ueberschreiben: bool = False,
        erwartet_ziel: Any = FEHLT,
        nutzer: Nutzer | None = None,
    ) -> dict[str, Any]:
        if not ist_admin(nutzer) and ueberschreiben and erwartet_ziel is FEHLT:  # Schutz, Vertrag W, 2.4
            raise TobiboxFehler("unauthorized")
        if not isinstance(uid, str) or not RE_UID.match(uid):
            raise TobiboxFehler("kennung_ungueltig")
        if not ist_admin(nutzer) and not self.kennung_bekannt(uid):
            raise TobiboxFehler("kennung_ungueltig")
        if self.store.zustand != ZUSTAND_OK:
            raise TobiboxFehler("konfig_nicht_bereit")
        self.schutz.liste_pruefen(nutzer)
        ziel = await self.pruefe_ziel(ziel_roh)
        name_neu: Any = FEHLT
        if name is None:
            name_neu = None
        elif name is not FEHLT:
            name_neu = name_pruefen(name, TOBIE_NAME_MAX)
        erwartet: Any = FEHLT
        if erwartet_ziel is not FEHLT:
            if erwartet_ziel is None:
                erwartet = None
            else:
                try:
                    erwartet = pruefe_ziel(erwartet_ziel, "erwartet_ziel")
                except Ungueltig as err:
                    raise TobiboxFehler("ziel_ungueltig") from err

        def setze(k: dict[str, Any]) -> None:
            bestehend = k["zuordnungen"].get(uid)
            aktuell = bestehend["ziel"] if bestehend else None
            if erwartet is not FEHLT:
                if erwartet != aktuell:
                    raise TobiboxFehler("zuordnung_geaendert")
            elif aktuell is not None and aktuell != ziel and not ueberschreiben:
                raise TobiboxFehler("zuordnung_existiert")
            eintrag: dict[str, Any] = {"ziel": dict(ziel)}
            alter_name = (bestehend or {}).get("name")
            neuer = alter_name if name_neu is FEHLT else name_neu
            if neuer:
                eintrag["name"] = neuer
            k["zuordnungen"][uid] = eintrag

        erg = await self.aendere_konfig(setze)
        self.schutz.liste_gebucht(nutzer)
        self.kennung_zugeordnet(uid)
        return erg

    async def zuordnung_entfernen(self, uid: str, erwartet_ziel: Any = FEHLT, nutzer: Nutzer | None = None) -> dict[str, Any]:
        if not ist_admin(nutzer) and erwartet_ziel is FEHLT:  # Schutz, Vertrag W, 2.4
            raise TobiboxFehler("unauthorized")
        if not isinstance(uid, str) or not RE_UID.match(uid):
            raise TobiboxFehler("kennung_ungueltig")
        if self.store.zustand != ZUSTAND_OK:
            raise TobiboxFehler("konfig_nicht_bereit")
        self.schutz.liste_pruefen(nutzer)
        erwartet: Any = FEHLT
        if erwartet_ziel is not FEHLT:
            try:
                erwartet = None if erwartet_ziel is None else pruefe_ziel(erwartet_ziel, "erwartet_ziel")
            except Ungueltig as err:
                raise TobiboxFehler("ziel_ungueltig") from err

        def entferne(k: dict[str, Any]) -> None:
            bestehend = k["zuordnungen"].get(uid)
            if erwartet is not FEHLT and erwartet != (bestehend["ziel"] if bestehend else None):
                raise TobiboxFehler("zuordnung_geaendert")
            k["zuordnungen"].pop(uid, None)

        erg = await self.aendere_konfig(entferne)
        self.schutz.liste_gebucht(nutzer)
        return erg

    async def zuordnung_liste(self, serie_id: str | None, limit: int, offset: int, uid: str | None = None) -> dict[str, Any]:
        if self.medien.geprueft_am is None:
            with contextlib.suppress(TobiboxFehler):
                await self.medien._stelle_geprueft_sicher()
        k = self.store.konfig
        eintraege: list[dict[str, Any]] = []
        for z_uid, z in sorted((k["zuordnungen"] if k else {}).items()):
            ziel = z["ziel"]
            if uid is not None and z_uid != uid:  # Filter ``uid``: genau eine Zuordnung (Erweiterung v1.1, 09.11.)
                continue
            if serie_id is not None and not (ziel["typ"] in ("serie", "folge") and ziel.get("serie") == serie_id):
                continue
            info = self.medien.serien.get(ziel.get("serie", "")) if ziel["typ"] in ("serie", "folge") else None
            eintrag = {
                "uid": z_uid,
                "name": z.get("name"),
                "ziel": ziel,
                "serie_name": info.serie.name if info else None,
                "folge_anzeige": None,
                "folge_vorhanden": None,
            }
            if ziel["typ"] == "folge":
                vorhanden = bool(info) and ziel["folge"] in info.serie.folgen
                eintrag["folge_vorhanden"] = vorhanden
                eintrag["folge_anzeige"] = info.serie.anzeige(ziel["folge"]) if vorhanden else None
            eintraege.append(eintrag)
        return {"konfig": self.konfig_stand(), "zuordnungen": eintraege[offset : offset + limit], "gesamt": len(eintraege)}

    # --- Einstellungen (AP 4.7) und Konfig-Stand lesen (Erweiterung v1.1) --------------------------------------------

    def konfig_lesen(self) -> dict[str, Any]:
        """``tobibox/konfig/get``: nur der Konfig-Stand (Erweiterung v1.1, 09.11.)."""
        return {"konfig": self.konfig_stand()}

    def einstellungen_lesen(self) -> dict[str, Any]:
        """``tobibox/einstellungen/get``: Leise-Zeiten, Gute Nacht, ``lesezeichen_tage`` (und ``hinweis_pegel``, wenn gesetzt)."""
        k = self.store.konfig
        if k is None:  # leerer Speicher (Zustand ``leer_neu``): es gibt noch nichts zu zeigen
            raise TobiboxFehler("konfig_nicht_bereit")
        return {**einstellungen_aus(k), "konfig": self.konfig_stand()}

    async def einstellungen_setzen(
        self,
        leise_zeiten: Any = FEHLT,
        gute_nacht: Any = FEHLT,
        lesezeichen_tage: Any = FEHLT,
        *,
        teilweise: bool = False,
        nutzer: Nutzer | None = None,
        erwartet_revision: int | None = None,
    ) -> dict[str, Any]:
        """``tobibox/einstellungen/set``: setzt ganze Objekte und/oder ``lesezeichen_tage``.

        Die Prüfung ist die der Box (``store.pruefe_*``); ist irgendein Teil ungültig, wird **nichts** geändert
        (``einstellung_ungueltig``, der Pfad steht im Klartext). ``teilweise`` (HA-Aktionen): Felder, die fehlen,
        bleiben wie sie sind, statt dass die Aktion das ganze Objekt ersetzt. Eine Änderung erhöht die Revision
        und geht an ``tobibox/config``; dieselben Werte wie schon gespeichert ergeben ``geaendert=false``.

        Schutz (Vertrag W, 2.4): ``lesezeichen_tage`` nur für Administratoren (sonst ``unauthorized``); für Nicht-Administratoren
        bleibt die gespeicherte ``leise_zeiten.zeitzone`` (der Wert im Objekt wird ignoriert); ``erwartet_revision`` muss die
        aktuelle Revision sein (``stand_veraltet``)."""
        if leise_zeiten is FEHLT and gute_nacht is FEHLT and lesezeichen_tage is FEHLT:
            raise TobiboxFehler("invalid_format")
        if not ist_admin(nutzer) and lesezeichen_tage is not FEHLT:
            raise TobiboxFehler("unauthorized")
        if self.store.zustand == ZUSTAND_OK:
            self.schutz.liste_pruefen(nutzer)

        def setze(k: dict[str, Any]) -> None:
            if erwartet_revision is not None and erwartet_revision != k["revision"]:
                raise TobiboxFehler("stand_veraltet")
            try:
                if leise_zeiten is not FEHLT:
                    lz = leise_zeiten
                    if not ist_admin(nutzer) and isinstance(lz, dict):
                        lz = {**lz, "zeitzone": k["leise_zeiten"]["zeitzone"]}
                    neu = {**k["leise_zeiten"], **lz} if teilweise and isinstance(lz, dict) else lz
                    k["leise_zeiten"] = pruefe_leise_zeiten(neu)
                if gute_nacht is not FEHLT:
                    neu = {**k["gute_nacht"], **gute_nacht} if teilweise and isinstance(gute_nacht, dict) else gute_nacht
                    k["gute_nacht"] = pruefe_gute_nacht(neu)
                if lesezeichen_tage is not FEHLT:
                    k["lesezeichen_tage"] = pruefe_lesezeichen_tage(lesezeichen_tage)
            except Ungueltig as err:
                raise TobiboxFehler("einstellung_ungueltig", pfad=err.pfad) from err

        erg = await self.aendere_konfig(setze)
        self.schutz.liste_gebucht(nutzer)
        assert self.store.konfig is not None  # aendere_konfig hat sonst konfig_nicht_bereit geworfen
        return {**erg, **einstellungen_aus(self.store.konfig)}

    # --- hello -------------------------------------------------------------------------------------------------------

    def hello(self, v: int, ist_admin: bool) -> dict[str, Any]:
        return {
            "v": VERTRAG_V,
            "version": self.version,
            "darf_schreiben": ist_admin,
            "faehigkeiten": list(FAEHIGKEITEN),
            "boxen": list(self.boxen),
            "konfig": self.konfig_stand(),
            "grenzen": {
                "upload_max_bytes": self.upload_max_bytes,
                "upload_block_bytes": UPLOAD_BLOCK_BYTES,
                "upload_parallel": UPLOAD_PARALLEL,
                "endungen": list(ENDUNGEN),
                "serie_name_max": SERIE_NAME_MAX,
                "folge_anzeige_max": FOLGE_ANZEIGE_MAX,
                "tobie_name_max": TOBIE_NAME_MAX,
                "name_max_bytes": 255,
                "limit_max": LIMIT_MAX,
            },
        }

    # --- anfrage_id (Vertrag W, 2.2) ---------------------------------------------------------------------------------

    async def mit_anfrage_id(
        self, anfrage_id: str | None, befehl: str, felder: dict[str, Any], func: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Führt ``func`` höchstens einmal je ``anfrage_id`` aus; nur Erfolge werden gemerkt (10 min, 100 Stück)."""
        if not anfrage_id:
            return await func()
        jetzt_s = self.hass.loop.time()
        for k in [k for k, v in self._anfragen.items() if jetzt_s - v[3] > ANFRAGE_ID_DAUER_S]:
            del self._anfragen[k]
        fingerabdruck = json.dumps(felder, sort_keys=True, default=str)
        gemerkt = self._anfragen.get(anfrage_id)
        if gemerkt is not None:
            if gemerkt[0] != befehl or gemerkt[1] != fingerabdruck:
                raise TobiboxFehler("anfrage_id_konflikt")
            return gemerkt[2]
        laufend = self._anfragen_laufend.get(anfrage_id)
        if laufend is None:
            laufend = self.hass.async_create_task(func(), f"tobibox_{befehl}")
            self._anfragen_laufend[anfrage_id] = laufend
            laufend.add_done_callback(lambda _t: self._anfragen_laufend.pop(anfrage_id, None))
        erg = await asyncio.shield(laufend)  # nur Erfolge werden gemerkt (Fehler werfen oben)
        if anfrage_id not in self._anfragen:
            self._anfragen[anfrage_id] = (befehl, fingerabdruck, erg, jetzt_s)
            while len(self._anfragen) > ANFRAGE_ID_ANZAHL:
                self._anfragen.popitem(last=False)
        return erg


def _lade_texte() -> dict[str, str]:
    """Die Klartexte aus ``translations/de.json`` (Bereich ``exceptions``)."""
    pfad = Path(__file__).parent / "translations" / "de.json"
    with open(pfad, encoding="utf-8") as f:
        daten = json.load(f)
    return {k: v["message"] for k, v in daten.get("exceptions", {}).items()}
