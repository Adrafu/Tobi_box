"""MQTT-Schicht der Integration (``docs/protocol/mqtt-v1.md``, HA-Seite).

* veröffentlicht ``tobibox/config`` (retained, QoS 1) und wartet auf den PUBACK,
* sendet Befehle auf ``tobibox/<box>/cmd`` (nicht retained) mit ``id``, ``erzeugt`` und ``ttl_s``,
* bestätigt Kennungen auf ``tobibox/<box>/unknown/<uid>/ack``,
* empfängt ``online``, ``status``, ``event``, ``unknown/<uid>``, ``ui/<objekt>`` und die Discovery-Namen,
* verarbeitet alles idempotent (doppelte Zustellung schadet nicht).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components import mqtt
from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    PUBACK_ZEITLIMIT_S,
    RE_UID,
    THEMA_CONFIG,
    THEMA_HA_STATUS,
    UPDATE_TTL_S,
    VERTRAG_V,
)
from .fehler import TobiboxFehler
from .store import konfig_zu_mqtt
from .util import jetzt_iso, neue_uuid

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

_RE_RELEASE = re.compile(r"^tobibox-(\d+)\.(\d+)\.(\d+)\.tar\.gz$")
MAX_NACHRICHT = 64 * 1024


@dataclass
class BoxZustand:
    """Was HA über eine Box weiß."""

    box: str
    anzeigename: str | None = None
    online: bool | None = None
    status: dict[str, Any] | None = None
    status_empfangen_am: str | None = None
    #: zuletzt gemeldete Abweichung (damit ``abweichung`` nur bei einer Änderung kommt)
    abweichung_gemeldet: tuple | None = None
    lern_serie: str | None = None


def _json(payload: Any) -> dict[str, Any] | None:
    """Liest eine JSON-Nachricht der Box. ``None`` bei leerer, zu großer oder ungültiger Nachricht."""
    if payload in ("", b"", None):
        return None
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if len(payload) > MAX_NACHRICHT:
        return None
    try:
        daten = json.loads(payload)
    except ValueError:
        return None
    return daten if isinstance(daten, dict) else None


def _version_ok(daten: dict[str, Any]) -> bool:
    """Ein Empfänger, der ein größeres ``v`` sieht als er kennt, verwirft die Nachricht (``mqtt-v1.md`` Abschnitt 8)."""
    v = daten.get("v", VERTRAG_V)
    return isinstance(v, int) and not isinstance(v, bool) and v <= VERTRAG_V


class MqttSchicht:
    """Verbindung der Integration zum Broker."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.hass = hub.hass
        self.boxen: dict[str, BoxZustand] = {b: BoxZustand(b) for b in hub.boxen}
        self._abmelden: list[CALLBACK_TYPE] = []
        self._pub_sperre = asyncio.Lock()
        self._status_gesehen = asyncio.Event()

    # --- Start und Ende --------------------------------------------------------------

    async def async_start(self) -> None:
        h = self.hass
        for thema, fn in (
            ("tobibox/+/online", self._on_online),
            ("tobibox/+/status", self._on_status),
            ("tobibox/+/event", self._on_event),
            ("tobibox/+/unknown/+", self._on_unknown),
            ("tobibox/+/ui/+", self._on_ui),
            ("homeassistant/+/+/+/config", self._on_discovery),
            (THEMA_HA_STATUS, self._on_ha_status),
        ):
            self._abmelden.append(await mqtt.async_subscribe(h, thema, fn, 1))
        self._abmelden.append(async_dispatcher_connect(h, mqtt.MQTT_CONNECTION_STATE, self._on_verbindung))

    def async_stop(self) -> None:
        for fn in self._abmelden:
            fn()
        self._abmelden.clear()

    def ist_verbunden(self) -> bool:
        try:
            return mqtt.is_connected(self.hass)
        except Exception:
            return False

    @callback
    def _on_verbindung(self, verbunden: bool) -> None:
        if verbunden:
            self.hass.async_create_background_task(self.hub.nachholen(), "tobibox_nachholen")

    @callback
    def _on_ha_status(self, msg: Any) -> None:
        if str(msg.payload).strip() == "online":
            self.hass.async_create_background_task(self.hub.nachholen(), "tobibox_nachholen")

    # --- Senden ----------------------------------------------------------------------------

    async def _sende(self, thema: str, payload: str, retain: bool) -> bool:
        """Veröffentlicht mit QoS 1 und wartet auf den PUBACK. ``False`` ohne Verbindung oder bei Zeitüberschreitung."""
        if not self.ist_verbunden():
            return False
        try:
            async with asyncio.timeout(PUBACK_ZEITLIMIT_S):
                await mqtt.async_publish(self.hass, thema, payload, 1, retain)
        except (TimeoutError, HomeAssistantError, OSError) as err:
            _LOGGER.warning("Veröffentlichen auf %s fehlgeschlagen: %s", thema, err)
            return False
        return True

    async def veroeffentliche_konfig(self) -> bool:
        """``tobibox/config`` (retained, QoS 1). ``True`` erst nach dem PUBACK.

        Veröffentlicht wird nur im Zustand ``ok`` (Vertrag W, 13.3). Vermerkt den Stand im Speicher."""
        store = self.hub.store
        async with self._pub_sperre:
            if store.zustand != "ok" or store.konfig is None:
                return False
            konfig = store.konfig
            payload = json.dumps(konfig_zu_mqtt(konfig), ensure_ascii=False, separators=(",", ":"))
            ok = await self._sende(THEMA_CONFIG, payload, True)
            if ok:
                store.veroeffentlicht_stand = [konfig["liste_id"], konfig["revision"]]
                store.speichern_verzoegert(1.0)
            return ok

    async def sende_befehl(self, box: str, befehl: str, ttl_s: int, daten: dict[str, Any] | None = None) -> str:
        """Befehl an genau eine Box, nicht retained, mit Ablaufzeit (``mqtt-v1.md`` 3.7). Gibt die ``id`` zurück."""
        if box not in self.boxen:
            raise TobiboxFehler("box_unbekannt")
        if not self.ist_verbunden():
            raise TobiboxFehler("mqtt_nicht_verbunden")
        befehl_id = neue_uuid()
        nachricht = {
            "v": VERTRAG_V,
            "id": befehl_id,
            "befehl": befehl,
            "erzeugt": jetzt_iso(),
            "ttl_s": ttl_s,
            "daten": daten or {},
        }
        ok = await self._sende(f"tobibox/{box}/cmd", json.dumps(nachricht, ensure_ascii=False), False)
        if not ok:
            raise TobiboxFehler("mqtt_nicht_verbunden")
        return befehl_id

    async def sende_ack(self, box: str, uid: str, zuletzt: str, art: str, grund: str) -> bool:
        nachricht = {"v": VERTRAG_V, "ts": jetzt_iso(), "zuletzt": zuletzt, "art": art, "grund": grund}
        return await self._sende(f"tobibox/{box}/unknown/{uid}/ack", json.dumps(nachricht), False)

    # --- Empfangen -----------------------------------------------------------------------------

    @staticmethod
    def _box_aus_thema(thema: str) -> str:
        return thema.split("/")[1]

    def _box(self, thema: str) -> BoxZustand | None:
        zustand = self.boxen.get(self._box_aus_thema(thema))
        if zustand is None:
            _LOGGER.debug("Nachricht einer unbekannten Box ignoriert: %s", thema)
        return zustand

    @callback
    def _on_online(self, msg: Any) -> None:
        z = self._box(msg.topic)
        if z is None:
            return
        text = str(msg.payload).strip()
        if text not in ("online", "offline"):
            return
        online = text == "online"
        if z.online != online:
            z.online = online
            self.hub.box_geaendert(z.box)

    def konfig_stand_von(self, z: BoxZustand) -> str:
        """``status.konfig`` gegen den Stand in HA (Vertrag W, 3.7)."""
        k = (z.status or {}).get("konfig") if z.status else None
        ha = self.hub.store.konfig
        if not isinstance(k, dict) or ha is None or self.hub.store.zustand == "leer_neu":
            return "unbekannt"
        liste, rev = k.get("liste_id"), k.get("revision")
        if not isinstance(rev, int):
            return "unbekannt"
        if liste == ha["liste_id"]:
            if rev == ha["revision"]:
                return "aktuell"
            return "voraus" if rev > ha["revision"] else "veraltet"
        return "veraltet"

    @callback
    def _on_status(self, msg: Any) -> None:
        z = self._box(msg.topic)
        daten = _json(msg.payload)
        if z is None or daten is None or not _version_ok(daten):
            return
        z.status = daten
        z.status_empfangen_am = jetzt_iso()
        self._status_gesehen.set()
        self.hub.box_geaendert(z.box)
        self.pruefe_abweichung(z)
        self.hub.lernmodus.on_status(z.box, daten)

    def pruefe_abweichung(self, z: BoxZustand) -> None:
        """Eine Box mit neuerem Stand als HA meldet das Ereignis ``konfig`` ``abweichung`` (Vertrag W, 13.4)."""
        if self.konfig_stand_von(z) != "voraus" or self.hub.store.konfig is None:
            z.abweichung_gemeldet = None if self.konfig_stand_von(z) != "voraus" else z.abweichung_gemeldet
            return
        k = z.status["konfig"]  # type: ignore[index]
        schluessel = ("voraus", k["liste_id"], k["revision"], self.hub.store.konfig["revision"])
        if z.abweichung_gemeldet == schluessel:
            return
        z.abweichung_gemeldet = schluessel
        self.hub.emit(
            "konfig",
            "abweichung",
            {
                "box": z.box,
                "grund": "voraus",
                "box_liste_id": k["liste_id"],
                "box_revision": k["revision"],
                "ha_revision": self.hub.store.konfig["revision"],
            },
        )

    @callback
    def _on_event(self, msg: Any) -> None:
        z = self._box(msg.topic)
        daten = _json(msg.payload)
        if z is None or daten is None or not _version_ok(daten):
            return
        eid, art, ts = daten.get("id"), daten.get("art"), daten.get("ts")
        if not isinstance(eid, str) or not isinstance(art, str):
            return
        inhalt = daten.get("daten") if isinstance(daten.get("daten"), dict) else {}
        ereignis = {
            "id": eid,
            "ts": ts if isinstance(ts, str) else jetzt_iso(),
            "art": art,
            "daten": inhalt,
            "text": self._ereignis_text(z, art, inhalt),
        }
        if not self.hub.store.box_ereignis_hinzu(z.box, ereignis):
            return  # doppelte Zustellung: dieselbe ``id`` wird nur einmal ausgewertet
        self.hub.emit("boxen", "ereignis", {"box": z.box, "ereignis": ereignis})
        if art == "liste_abgelehnt":
            self._liste_abgelehnt(z, inhalt)
        elif art == "befehl_abgelehnt":
            self._befehl_abgelehnt(z, eid, inhalt)

    def _ereignis_text(self, z: BoxZustand, art: str, d: dict[str, Any]) -> str:
        t = self.hub.t
        name = z.anzeigename or z.box
        if art == "liste_abgelehnt":
            return t(
                "ereignis_liste_abgelehnt",
                box=name,
                revision=d.get("revision", "?"),
                grund=t(f"grund_{d.get('grund')}") if d.get("grund") else "?",
            )
        if art == "befehl_abgelehnt":
            return self._befehl_text(z, d)
        if art == "fehler":
            return t("ereignis_fehler", box=name, baustein=d.get("baustein", "?"), text=d.get("text", ""))
        return t("ereignis_unbekannt", box=name, art=art)

    def _befehl_text(self, z: BoxZustand, d: dict[str, Any]) -> str:
        t = self.hub.t
        name = z.anzeigename or z.box
        if d.get("grund") == "zeit_unsicher":
            return t(
                "ereignis_befehl_zeit_unsicher",
                box=name,
                befehl=d.get("befehl", "?"),
                zeitquelle=(z.status or {}).get("zeitquelle", "unbekannt"),
            )
        return t("ereignis_befehl_bedingung", box=name, befehl=d.get("befehl", "?"), detail=d.get("detail") or "")

    def _liste_abgelehnt(self, z: BoxZustand, d: dict[str, Any]) -> None:
        ha = self.hub.store.konfig
        if d.get("grund") == "revision_zu_niedrig" and ha is not None:
            self.hub.emit(
                "konfig",
                "abweichung",
                {
                    "box": z.box,
                    "grund": "revision_zu_niedrig",
                    "box_liste_id": d.get("gespeichert_liste_id"),
                    "box_revision": d.get("gespeichert_revision"),
                    "ha_revision": ha["revision"],
                },
            )

    def _befehl_abgelehnt(self, z: BoxZustand, eid: str, d: dict[str, Any]) -> None:
        self.hub.benachrichtige(
            f"tobibox_befehl_{eid}", "benachrichtigung_befehl_abgelehnt_titel", None, text=self._befehl_text(z, d)
        )
        if d.get("befehl") == "lernen":
            self.hub.lernmodus.on_befehl_abgelehnt(z.box, d.get("befehl_id"), d.get("grund"))

    @callback
    def _on_unknown(self, msg: Any) -> None:
        parts = msg.topic.split("/")
        z = self._box(msg.topic)
        daten = _json(msg.payload)  # eine leere Nachricht (Löschen durch die Box) ist keine Meldung
        if z is None or daten is None or not _version_ok(daten) or len(parts) != 4:
            return
        uid = parts[3]
        if not RE_UID.match(uid) or daten.get("uid") != uid:
            return
        zuletzt, art = daten.get("zuletzt"), daten.get("art")
        if not isinstance(zuletzt, str) or art not in ("unbekannt", "gelernt") or not isinstance(daten.get("anzahl"), int):
            return
        if not isinstance(daten.get("zuerst"), str):
            return
        self.hass.async_create_task(self.hub.neue_kennung(z.box, uid, daten))

    @callback
    def _on_ui(self, msg: Any) -> None:
        z = self._box(msg.topic)
        if z is None:
            return
        objekt = msg.topic.split("/")[3]
        text = str(msg.payload).strip()
        if objekt == "lern_serie":
            z.lern_serie = text
            return
        if text != "PRESS":
            return
        if objekt == "sync":
            self.hass.async_create_task(self.hub.ui_sync(z.box))
        elif objekt == "update":
            self.hass.async_create_task(self.hub.ui_update(z.box))
        elif objekt == "lernen_abbrechen":
            self.hass.async_create_task(self.hub.ui_lernen_abbrechen(z.box))

    @callback
    def _on_discovery(self, msg: Any) -> None:
        """Der Gerätename aus der Discovery der Box (``Tobi Box <anzeigename>``)."""
        parts = msg.topic.split("/")
        if len(parts) != 5 or not parts[2].startswith("tobibox_"):
            return
        box = parts[2][len("tobibox_") :]
        z = self.boxen.get(box)
        daten = _json(msg.payload)
        if z is None or daten is None:
            return
        name = (daten.get("device") or {}).get("name")
        if isinstance(name, str) and name:
            neu = name.removeprefix("Tobi Box ").strip() or None
            if neu != z.anzeigename:
                z.anzeigename = neu
                self.hub.box_geaendert(box)

    # --- Releases (ui/update) ----------------------------------------------------------------------------

    def neueste_version(self) -> str | None:
        """Die neueste Version aus ``releases/`` (synchron, im Executor aufrufen)."""
        try:
            namen = [e.name for e in self.hub.pfade.releases.iterdir()]
        except OSError:
            return None
        versionen = []
        for n in namen:
            m = _RE_RELEASE.match(n)
            if m:
                versionen.append(tuple(int(x) for x in m.groups()))
        if not versionen:
            return None
        return ".".join(str(x) for x in max(versionen))

    async def sende_update(self, box: str) -> str:
        version = await self.hass.async_add_executor_job(self.neueste_version)
        if version is None:
            raise TobiboxFehler("keine_version")
        return await self.sende_befehl(box, "update", UPDATE_TTL_S, {"version": version})
