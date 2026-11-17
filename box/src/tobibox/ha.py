"""Home Assistant über MQTT (``mqtt-v1.md``, ``core-interface.md`` Abschnitte 7, 9 und 12).

Das Modul ``ha`` ist die Stelle des Dienstes, die MQTT spricht. AP 3.7 tauscht damit den HA-Ersatz der Stufe 2
(``ha_ersatz.py``, ``sim``) aus. Aufgaben:

* **Verbindung:** eigenes Konto je Box, Client-ID ``tobibox-<box>``, dauerhafte Sitzung, QoS 1, Will ``offline``,
  Neuverbinden nach 1, 2, 5, 10, dann 30 s (paho-mqtt 2.x, MQTT 3.1.1). Reihenfolge nach jedem Verbinden: abonnieren,
  ``online``, Discovery, Status, offene Einträge aus ``unknown.json`` (4.4).
* **Konfiguration** (``tobibox/config``): Revisionsregel und Prüfung macht ``KonfigStore.annehmen`` (es ruft
  ``store.validiere_konfig``, die eine Funktion für Migration und Prüfung). Angenommen: ``KonfigGeladen``.
  Abgelehnt: ``event`` ``liste_abgelehnt`` (5.2).
* **Unbekannte Kennungen:** ``melde(eintrag)`` veröffentlicht je Kennung dauerhaft. Das ``…/ack`` von HA wird zu
  ``Bestaetigt``. Der Eintrag bleibt in ``unknown.json``, bis HA bestätigt hat **und** die dauerhafte Nachricht auf dem Broker
  gelöscht ist (4.1, Schritt 4). Der PUBACK des Brokers bestätigt nichts.
* **Befehle** (``…/cmd``): Version, Name und doppelte ``id`` prüft ``ha``; die Ablaufzeit wird als ``gueltig_bis`` mitgegeben,
  geprüft wird sie im Kern (``learn``, ``idle``) mit ``jetzt.wall`` und ``jetzt.zeit_ok``.
* **Status** (``…/status``): Der Statussammler (``status.py``) liefert das JSON; ``ha`` ergänzt den freien Speicher und
  veröffentlicht bei Änderung höchstens alle 5 s und sonst alle 300 s.
* **Discovery:** Entitäten je Box (6.2).

Alle Rückrufe des Netz-Threads gehen über eine Warteschlange in die Ereignisschleife und werden dort nacheinander
abgearbeitet. So hat ``ha`` keine Sperren, und die Reihenfolge der Nachrichten bleibt erhalten.
"""

from __future__ import annotations

import asyncio
import collections
import inspect
import json
import re
import shutil
import threading
import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from . import events as ev
from .clock import Uhr
from .config import MqttKonfig
from . import gehoert as gehoert_modul
from .eventlog import logge
from .gehoert_puffer import GehoertPuffer
from .outbox import Outbox, zeitstempel
from .status import Statussammler
from .store import KonfigStore

QOS = 1
KEEPALIVE_S = 30
WARTEZEITEN_S = (1, 2, 5, 10, 30)  # Neuverbinden (mqtt-v1.md, Abschnitt 1)
STATUS_MIN_ABSTAND_S = 5.0  # höchstens eine Statusnachricht je 5 s bei Änderung
STATUS_ALLE_S = 300.0  # und mindestens alle 300 s
MAX_NACHRICHT = 64 * 1024
MAX_KONFIG = 256 * 1024
NACHRICHT_VERSION = 1  # das ``v`` dieses Vertrags
BEFEHL_IDS_GEMERKT = 50
BEFEHLE = ("lernen", "lernen_abbrechen", "sync", "update")
ARTEN = ("unbekannt", "gelernt")
ACK_GRUENDE = ("neu", "bekannt", "zugeordnet", "abgelehnt")
GEHOERT_STATUS_WARTEN_S = 60.0  # solange die Box auf den Handshake wartet, meldet sie den Status alle 60 s neu (mqtt-v1 3.3)
GEHOERT_SENDEN_ALLE_S = 600.0  # danach alle 10 Minuten alle Zeilen, solange welche da sind (4.5, Punkt 2)
GEHOERT_JE_NACHRICHT = 20  # höchstens 20 Sitzungen je Nachricht
GEHOERT_NACHRICHTEN_JE_TICK = 20  # höchstens 20 Nachrichten je Sekunde (``tick`` läuft jede Sekunde)
MAX_QUITTUNG = 100
STOPP_FRIST_S = 2.0  # so lange wartet ``stop`` auf den PUBACK von ``offline``
_VERSION_MUSTER = re.compile(r"^\d+\.\d+\.\d+$")
_MB = 1024 * 1024


# --------------------------------------------------------------------------
# Themen
# --------------------------------------------------------------------------


class Themen:
    """Alle Themen einer Box (``mqtt-v1.md``, Abschnitt 2)."""

    def __init__(self, box: str) -> None:
        self.box = box
        self.config = "tobibox/config"
        self.online = f"tobibox/{box}/online"
        self.status = f"tobibox/{box}/status"
        self.event = f"tobibox/{box}/event"
        self.cmd = f"tobibox/{box}/cmd"
        self.ha_status = "homeassistant/status"
        self._unknown = f"tobibox/{box}/unknown/"
        self.ack_filter = f"{self._unknown}+/ack"

    def unknown(self, uid: str) -> str:
        return f"{self._unknown}{uid}"

    def uid_aus_ack(self, thema: str) -> str | None:
        """``tobibox/<box>/unknown/<uid>/ack`` -> ``<uid>``, sonst ``None``."""
        if thema.startswith(self._unknown) and thema.endswith("/ack"):
            uid = thema[len(self._unknown) : -len("/ack")]
            if uid and "/" not in uid and "+" not in uid and "#" not in uid:
                return uid
        return None

    def discovery(self, komponente: str, objekt: str) -> str:
        return f"homeassistant/{komponente}/tobibox_{self.box}/{objekt}/config"

    def abonnements(self) -> list[tuple[str, int]]:
        return [(self.config, QOS), (self.cmd, QOS), (self.ack_filter, QOS), (self.ha_status, QOS)]


# --------------------------------------------------------------------------
# Discovery (6)
# --------------------------------------------------------------------------


def optionen(serien: Sequence[ev.Serie]) -> list[str]:
    """Anzeigenamen der Serien für die Auswahl „Serie für Lernmodus“ (6.2).

    Nur normale Serien (die Überraschungs-Serie ist kein Ziel). Bei doppelten Namen hängt die Box ` (<id>)` an.
    Ohne Serie steht ein Platzhalter da, weil Home Assistant eine leere Liste nicht annimmt."""
    normal = [s for s in serien if s.typ == "normal"]
    zaehler = collections.Counter(s.name for s in normal)
    namen = [f"{s.name} ({s.id})" if zaehler[s.name] > 1 else s.name for s in normal]
    return namen or ["keine Serie"]


def baue_discovery(box: str, anzeigename: str, version: str, serien: Sequence[ev.Serie]) -> list[tuple[str, dict[str, Any]]]:
    """Alle Discovery-Nachrichten einer Box: ``(Thema, Nutzlast)``. Rein, ohne MQTT."""
    t = Themen(box)
    geraet = {
        "identifiers": [f"tobibox_{box}"],
        "name": f"Tobi Box {anzeigename}",
        "manufacturer": "Tobi Box",
        "model": "NFC-Audiobox",
        "sw_version": version,
    }
    verfuegbar = {
        "availability_topic": t.online,
        "payload_available": "online",
        "payload_not_available": "offline",
    }

    def entitaet(komponente: str, objekt: str, name: str, **zusatz: Any) -> tuple[str, dict[str, Any]]:
        n: dict[str, Any] = {
            "name": name,
            "unique_id": f"tobibox_{box}_{objekt}",
            "has_entity_name": True,
            **zusatz,
            **verfuegbar,
            "device": geraet,
        }
        return t.discovery(komponente, objekt), n

    def sensor(objekt: str, name: str, wert: str, **zusatz: Any) -> tuple[str, dict[str, Any]]:
        return entitaet("sensor", objekt, name, state_topic=t.status, value_template=wert, **zusatz)

    def knopf(objekt: str, name: str, ui: str) -> tuple[str, dict[str, Any]]:
        return entitaet("button", objekt, name, command_topic=f"tobibox/{box}/ui/{ui}", payload_press="PRESS")

    lader = (
        "{% if value_json.lader is none %}None{% else %}{{ 'ON' if value_json.lader else 'OFF' }}{% endif %}"
    )
    return [
        sensor("zustand", "Zustand", "{{ value_json.zustand }}"),
        sensor("serie", "Läuft gerade", "{{ value_json.serie.name if value_json.serie else 'keine' }}"),
        sensor("akku", "Akku", "{{ value_json.akku_prozent }}",
               device_class="battery", unit_of_measurement="%", state_class="measurement"),
        entitaet("binary_sensor", "lader", "Lader", state_topic=t.status, value_template=lader,
                 payload_on="ON", payload_off="OFF", device_class="battery_charging"),
        sensor("netz", "Netz", "{{ value_json.netz }}", device_class="enum", options=["home", "hotspot", "offline"]),
        sensor("sync", "Sync-Stand", "{{ value_json.sync.zustand }}",
               json_attributes_topic=t.status, json_attributes_template="{{ value_json.sync | tojson }}"),
        sensor("speicher_frei", "Freier Speicher", "{{ value_json.speicher_frei_mb }}",
               unit_of_measurement="MB", device_class="data_size", state_class="measurement",
               suggested_unit_of_measurement="GB", suggested_display_precision=0),
        sensor("version", "Version", "{{ value_json.version }}", entity_category="diagnostic"),
        sensor("letzter_fehler", "Letzter Fehler",
               "{{ value_json.letzter_fehler.text if value_json.letzter_fehler else 'kein Fehler' }}",
               json_attributes_topic=t.status,
               json_attributes_template="{{ {'zeit': value_json.letzter_fehler.zeit} | tojson if value_json.letzter_fehler else '{}' }}"),
        sensor("zeitquelle", "Zeitquelle", "{{ value_json.zeitquelle }}", entity_category="diagnostic",
               json_attributes_topic=t.status,
               json_attributes_template="{{ {'zeit_ok': value_json.zeit_ok} | tojson }}"),
        knopf("sync_jetzt", "Sync jetzt", "sync"),
        knopf("update", "Update", "update"),
        knopf("lernen_abbrechen", "Lernmodus abbrechen", "lernen_abbrechen"),
        entitaet("select", "lern_serie", "Serie für Lernmodus", command_topic=f"tobibox/{box}/ui/lern_serie",
                 options=optionen(serien), optimistic=True),
    ]


# --------------------------------------------------------------------------
# MQTT-Klient
# --------------------------------------------------------------------------


class Klient(Protocol):
    """Was ``Ha`` vom MQTT-Klienten braucht. Die Rückrufe laufen im Netz-Thread des Klienten."""

    bei_verbunden: Callable[[], None] | None
    bei_getrennt: Callable[[], None] | None
    bei_abonniert: Callable[[], None] | None
    bei_nachricht: Callable[[str, bytes], None] | None
    bei_veroeffentlicht: Callable[[int], None] | None

    def starten(self) -> None: ...
    def abonnieren(self, themen: list[tuple[str, int]]) -> None: ...
    def veroeffentlichen(self, thema: str, nutzlast: bytes, retain: bool) -> int | None:
        """Gibt die Nachrichten-Nummer (für den PUBACK) zurück, ``None`` ohne Verbindung."""
        ...
    def stoppen(self) -> None: ...


class PahoKlient:
    """``paho-mqtt`` 2.x. Ein Überwacher-Thread verbindet und wartet die Neuverbindung nach ``WARTEZEITEN_S`` ab."""

    def __init__(self, konfig: MqttKonfig, will_thema: str) -> None:
        import paho.mqtt.client as mqtt

        self._konfig = konfig
        self._mqtt = mqtt
        self.bei_verbunden: Callable[[], None] | None = None
        self.bei_getrennt: Callable[[], None] | None = None
        self.bei_abonniert: Callable[[], None] | None = None
        self.bei_nachricht: Callable[[str, bytes], None] | None = None
        self.bei_veroeffentlicht: Callable[[int], None] | None = None
        # Dauerhafte Sitzung (clean_session=False), MQTT 3.1.1; paho verbindet nicht selbst neu (das tut der Überwacher)
        c = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"tobibox-{konfig.box_id}",
            protocol=mqtt.MQTTv311,
            clean_session=False,
            reconnect_on_failure=False,
        )
        c.username_pw_set(konfig.benutzer, konfig.passwort)
        c.will_set(will_thema, b"offline", qos=QOS, retain=True)
        c.max_queued_messages_set(500)
        c.on_connect = self._on_connect
        c.on_disconnect = self._on_disconnect
        c.on_subscribe = self._on_subscribe
        c.on_message = self._on_message
        c.on_publish = self._on_publish
        self._c = c
        self._verbunden = False
        self._stufe = 0
        self._stopp = threading.Event()
        self._getrennt = threading.Event()
        self._thread: threading.Thread | None = None

    # -- Rückrufe von paho (Netz-Thread) -------------------------------------------

    def _on_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        if reason_code.is_failure:
            logge("ha", "WARNING", "verbinden", "abgelehnt", daten={"grund": str(reason_code)})
            return
        self._verbunden = True
        self._stufe = 0
        if self.bei_verbunden:
            self.bei_verbunden()

    def _on_disconnect(self, client: Any, userdata: Any, flags: Any, reason_code: Any = None, properties: Any = None) -> None:
        war = self._verbunden
        self._verbunden = False
        self._getrennt.set()
        if war and self.bei_getrennt:
            self.bei_getrennt()

    def _on_subscribe(self, client: Any, userdata: Any, mid: Any, reason_codes: Any, properties: Any = None) -> None:
        for rc in reason_codes:
            if getattr(rc, "is_failure", False):
                logge("ha", "ERROR", "abonnieren", "abgelehnt", daten={"grund": str(rc)})
        if self.bei_abonniert:
            self.bei_abonniert()

    def _on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        if self.bei_nachricht:
            self.bei_nachricht(msg.topic, bytes(msg.payload))

    def _on_publish(self, client: Any, userdata: Any, mid: int, reason_code: Any = None, properties: Any = None) -> None:
        if self.bei_veroeffentlicht:
            self.bei_veroeffentlicht(mid)

    # -- Klient --------------------------------------------------------------------

    def starten(self) -> None:
        self._stopp.clear()
        self._thread = threading.Thread(target=self._lauf, name="tobibox-mqtt", daemon=True)
        self._thread.start()

    def _lauf(self) -> None:
        c, k = self._c, self._konfig
        while not self._stopp.is_set():
            self._getrennt.clear()
            laeuft = False
            try:
                c.connect(k.host, k.port, keepalive=KEEPALIVE_S)
                c.loop_start()
                laeuft = True
            except Exception as e:  # noqa: BLE001 - Broker aus, Name unbekannt, Netz weg: später wieder versuchen
                logge("ha", "WARNING", "verbinden", "fehler", daten={"detail": repr(e)})
            if laeuft:
                while not self._stopp.is_set() and not self._getrennt.wait(0.2):
                    pass
                c.loop_stop()
            if self._stopp.is_set():
                break
            wartezeit = WARTEZEITEN_S[min(self._stufe, len(WARTEZEITEN_S) - 1)]
            self._stufe += 1
            logge("ha", "INFO", "neu_verbinden", "wartet", daten={"sekunden": wartezeit})
            self._stopp.wait(wartezeit)

    def abonnieren(self, themen: list[tuple[str, int]]) -> None:
        self._c.subscribe(themen)

    def veroeffentlichen(self, thema: str, nutzlast: bytes, retain: bool) -> int | None:
        if not self._verbunden:
            return None
        info = self._c.publish(thema, nutzlast, qos=QOS, retain=retain)
        return info.mid if info.rc == self._mqtt.MQTT_ERR_SUCCESS else None

    def stoppen(self) -> None:
        self._stopp.set()
        with suppress(Exception):
            self._c.disconnect()
        if self._thread is not None:
            self._thread.join(5)
            self._thread = None

    def trenne_hart(self) -> None:
        """Nur für Tests: die Verbindung ohne DISCONNECT kappen (der Broker sendet dann den Will)."""
        import socket

        s = self._c.socket()
        if s is not None:
            with suppress(OSError):
                s.shutdown(socket.SHUT_RDWR)


# --------------------------------------------------------------------------
# Ha
# --------------------------------------------------------------------------


def _parse_zeit(text: Any) -> float | None:
    """``2026-11-05T09:11:50Z`` (auch mit Millisekunden) -> UTC-Sekunden, sonst ``None``."""
    if not isinstance(text, str):
        return None
    try:
        t = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)).timestamp()


def freier_speicher_mb(pfad: str | Path) -> int | None:
    """Freier Platz auf dem Dateisystem des Medienordners in ganzen MB (abgerundet), ``None`` bei Fehler."""
    try:
        return shutil.disk_usage(pfad).free // _MB
    except OSError:
        return None


class Ha:
    """MQTT-Seite des Dienstes. Eine Instanz je Dienst; ``start()`` und ``stop()`` in der Ereignisschleife."""

    def __init__(
        self,
        konfig: MqttKonfig,
        *,
        konfig_store: KonfigStore,
        outbox: Outbox,
        status: Statussammler,
        uhr: Uhr,
        ausgabe: Callable[[ev.Ereignis], Any],
        medien: str | Path,
        serien: Callable[[], Sequence[ev.Serie]] = lambda: (),
        klient: Klient | None = None,
        speicher_frei_mb: Callable[[], int | None] | None = None,
        gehoert: GehoertPuffer | None = None,
    ) -> None:
        self.konfig = konfig
        self.themen = Themen(konfig.box_id)
        self.konfig_store = konfig_store
        self.outbox = outbox
        self.status = status
        self.uhr = uhr
        self._ausgabe = ausgabe
        self._serien = serien
        self._frei = speicher_frei_mb or (lambda: freier_speicher_mb(medien))
        self.klient: Klient = klient if klient is not None else PahoKlient(konfig, self.themen.online)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[tuple[Any, ...]] | None = None
        self._aufgaben: list[asyncio.Task[None]] = []
        self.verbunden = False  # CONNACK erhalten
        self._bereit = False  # abonniert und Hallo gesendet (Status und Discovery dürfen raus)
        self._puback: dict[int, Callable[[], Awaitable[None]]] = {}
        self._befehl_ids: collections.deque[str] = collections.deque(maxlen=BEFEHL_IDS_GEMERKT)
        self._letzte_ablehnung: tuple[Any, ...] | None = None
        self._loeschungen: set[tuple[str, str, str]] = set()
        self._status_letzt: dict[str, Any] | None = None
        self._status_mono: float | None = None
        self._discovery_stand: tuple[str, tuple[str, ...]] | None = None
        # Stufe B „Gehört“ (mqtt-v1 4.5): Handshake über den Zustand, Senden, Quittung
        self.gehoert = gehoert
        self._gehoert_wartet = True  # ab jedem Verbinden und bei jedem ``homeassistant/status online``, bis eine Quittung kommt
        self._gehoert_gemeldet: bool | None = None  # ``gehoert_wartet`` im zuletzt veröffentlichten Status
        self._gehoert_los = False  # nach dem Handshake: alle Zeilen senden
        self._gehoert_zuletzt: float | None = None  # ``mono`` des letzten Sendens aller Zeilen
        self._gehoert_lauf: list[Mapping[str, Any]] = []  # Zeilen, die noch zu senden sind (höchstens 20 Nachrichten je Sekunde)
        if gehoert is not None:
            status.zusatz = self.gehoert_status

    # -- Lebenslauf ----------------------------------------------------------------

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        k = self.klient
        k.bei_verbunden = lambda: self._von_netz("verbunden")
        k.bei_getrennt = lambda: self._von_netz("getrennt")
        k.bei_abonniert = lambda: self._von_netz("abonniert")
        k.bei_nachricht = lambda thema, nutzlast: self._von_netz("nachricht", thema, nutzlast)
        k.bei_veroeffentlicht = lambda mid: self._von_netz("puback", mid)
        self._aufgaben = [
            asyncio.create_task(self._verarbeiter(), name="tobibox-ha"),
            asyncio.create_task(self._status_schleife(), name="tobibox-ha-status"),
        ]
        k.starten()
        logge("ha", "INFO", "start", "ok", daten={"host": self.konfig.host, "port": self.konfig.port, "box": self.konfig.box_id})

    async def stop(self) -> None:
        """Sauber beenden: erst ``offline`` (der Will greift bei sauberem Trennen nicht), dann trennen."""
        if self.verbunden and self._bereit:
            fertig = asyncio.Event()

            async def erledigt() -> None:
                fertig.set()

            if self._veroeffentliche(self.themen.online, b"offline", True, erledigt) is not None:
                with suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(fertig.wait(), STOPP_FRIST_S)
        for a in self._aufgaben:
            a.cancel()
        for a in self._aufgaben:
            with suppress(asyncio.CancelledError):
                await a
        self._aufgaben = []
        await asyncio.to_thread(self.klient.stoppen)
        self.verbunden = self._bereit = False

    async def leere(self) -> None:
        """Wartet, bis alle bisher eingegangenen Rückrufe verarbeitet sind (für Tests)."""
        if self._queue is None:
            return
        while True:
            await asyncio.sleep(0)  # Rückrufe aus dem Netz-Thread (``call_soon_threadsafe``) laufen lassen
            if self._queue.empty():
                await self._queue.join()
                await asyncio.sleep(0)
                if self._queue.empty():
                    return
            else:
                await self._queue.join()

    # -- Brücke vom Netz-Thread in die Ereignisschleife ----------------------------

    def _von_netz(self, art: str, *args: Any) -> None:
        loop, q = self._loop, self._queue
        if loop is None or q is None:
            return
        with suppress(RuntimeError):  # Schleife schon geschlossen
            loop.call_soon_threadsafe(q.put_nowait, (art, *args))

    async def _verarbeiter(self) -> None:
        assert self._queue is not None
        while True:
            art, *args = await self._queue.get()
            try:
                await self._bearbeite(art, *args)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - eine fehlerhafte Nachricht darf den Verarbeiter nicht beenden
                logge("ha", "ERROR", "verarbeiten", "fehler", daten={"art": art, "detail": repr(e)})
            finally:
                self._queue.task_done()

    async def _bearbeite(self, art: str, *args: Any) -> None:
        if art == "nachricht":
            await self.verarbeite(*args)
        elif art == "verbunden":
            await self._verbunden_gesetzt()
        elif art == "abonniert":
            self._hallo()
        elif art == "getrennt":
            await self._getrennt()
        elif art == "puback":
            erledigt = self._puback.pop(args[0], None)
            if erledigt is not None:
                await erledigt()

    async def _gib(self, e: ev.Ereignis) -> None:
        r = self._ausgabe(e)
        if inspect.isawaitable(r):
            await r

    # -- Verbindung ----------------------------------------------------------------

    async def _verbunden_gesetzt(self) -> None:
        self.verbunden = True
        logge("ha", "INFO", "verbunden", "ok")
        await self._gib(ev.HaVerbindung(True))
        self.klient.abonnieren(self.themen.abonnements())  # weiter mit ``abonniert``

    async def _getrennt(self) -> None:
        if not self.verbunden:
            return
        self.verbunden = self._bereit = False
        self._gehoert_neu_warten()  # B1-OFFEN: auch beim Trennen (nicht erst beim Verbinden), damit nach einer Lücke nie ohne neuen Handshake gesendet wird
        logge("ha", "WARNING", "verbunden", "getrennt")
        await self._gib(ev.HaVerbindung(False))

    def _hallo(self) -> None:
        """Nach dem Abonnieren (4.4): ``online``, Discovery, Status, offene Einträge. ``tobibox/config`` kommt von selbst."""
        self._bereit = True
        self._gehoert_neu_warten()  # jedes Verbinden: Handshake von vorn, nichts senden (4.5, Punkt 1)
        self._veroeffentliche(self.themen.online, b"online", True)
        self._discovery_senden()
        self._status_letzt = self._status_mono = None
        self._status_senden()
        for eintrag in self.outbox.offen():
            self.melde(eintrag)

    # -- Veröffentlichen -----------------------------------------------------------

    def _veroeffentliche(
        self, thema: str, nutzlast: bytes, retain: bool, bei_puback: Callable[[], Awaitable[None]] | None = None
    ) -> int | None:
        """Gibt die Nachrichten-Nummer zurück, ``None`` ohne Verbindung (dann wird sie beim nächsten Verbinden nachgeholt)."""
        mid = self.klient.veroeffentlichen(thema, nutzlast, retain)
        if mid is None:
            return None
        if bei_puback is not None:
            self._puback[mid] = bei_puback  # der PUBACK kommt über die Warteschlange, also erst nach diesem Schritt
        return mid

    def _veroeffentliche_json(self, thema: str, daten: Mapping[str, Any], retain: bool) -> int | None:
        return self._veroeffentliche(thema, json.dumps(daten, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), retain)

    def gehoert_status(self) -> dict[str, Any]:
        """Die Felder des Status für „Gehört“ (mqtt-v1 3.3): Fähigkeit, Handshake, verworfene Zeilen."""
        if self.gehoert is None:
            return {}
        return {"box_faehig": ["gehoert"], "gehoert_wartet": self._gehoert_wartet, "gehoert_verworfen": self.gehoert.verworfen}

    def _discovery_senden(self) -> None:
        d = self.status.als_dict(self.uhr.jetzt(), self._serien(), None)
        version = str(d["version"])
        serien = tuple(optionen(self._serien()))
        for thema, nutzlast in baue_discovery(self.konfig.box_id, self.konfig.anzeigename, version, self._serien()):
            self._veroeffentliche_json(thema, nutzlast, True)
        self._discovery_stand = (version, serien)

    def _status_senden(self) -> None:
        jetzt = self.uhr.jetzt()
        d = self.status.als_dict(jetzt, self._serien(), self._frei())
        if self._veroeffentliche_json(self.themen.status, d, True) is not None:
            self._status_letzt = {k: v for k, v in d.items() if k != "ts"}
            self._status_mono = jetzt.mono
            self._gehoert_gemeldet = d.get("gehoert_wartet")

    def tick(self) -> None:
        """Status und Discovery nachführen. Die Schleife ruft es jede Sekunde; Tests rufen es von Hand."""
        if not self._bereit:
            return
        jetzt = self.uhr.jetzt()
        serien = self._serien()
        d = self.status.als_dict(jetzt, serien, self._frei())
        if self._discovery_stand != (str(d["version"]), tuple(optionen(serien))):
            self._discovery_senden()  # Version oder Serienliste haben sich geändert (6)
        seit = float("inf") if self._status_mono is None else jetzt.mono - self._status_mono
        geaendert = self._status_letzt != {k: v for k, v in d.items() if k != "ts"}
        wartet = self.gehoert is not None and self._gehoert_wartet
        if seit >= STATUS_ALLE_S or (geaendert and seit >= STATUS_MIN_ABSTAND_S) or (wartet and seit >= GEHOERT_STATUS_WARTEN_S):
            self._status_senden()
        self._gehoert_tick(jetzt)

    # -- Gehört melden (mqtt-v1 4.5) -----------------------------------------------

    def _gehoert_neu_warten(self) -> None:
        if self.gehoert is not None:
            self._gehoert_wartet = True
            self._gehoert_gemeldet = None  # erst ein veröffentlichter Status mit ``true``/``false`` zählt
            self._gehoert_los = False
            self._gehoert_lauf = []
            self._gehoert_zuletzt = None

    def _gehoert_tick(self, jetzt: ev.Jetzt) -> None:
        """Senden nach dem Handshake: alle Zeilen, bei jedem Sitzungsende, danach alle 10 Minuten; Zwischenstand alle 15 Minuten."""
        g = self.gehoert
        if g is None or not self._bereit or self._gehoert_wartet:
            return  # kein Zwischenstand und keine Zeile, solange die Box wartet (Auflage Kurzprüfung)
        if self._gehoert_gemeldet is not False:
            # B1-OFFEN: Der Vertrag sagt „danach meldet die Box ``gehoert_wartet = false`` und sendet“: Die Box wartet darum, bis der Status mit
            # ``false`` hinausgegangen ist (höchstens 5 s nach der Quittung, Mindestabstand des Status); erst dann gehen die Zeilen hinaus.
            return  # erst muss ``gehoert_wartet = false`` im Status stehen ("danach meldet die Box ... und sendet")
        zwischen = g.zwischenstand(jetzt)
        if zwischen is not None:
            self.sende_event("gespielt", gehoert_modul.baue_nachricht([zwischen], g.kontext.boot_id, jetzt))
        faellig = (
            self._gehoert_los
            or g.neue_zeilen
            or (self._gehoert_zuletzt is not None and jetzt.mono - self._gehoert_zuletzt >= GEHOERT_SENDEN_ALLE_S)
        )
        if faellig and not self._gehoert_lauf:
            self._gehoert_los = False
            g.neue_zeilen = False
            self._gehoert_lauf = list(g.zeilen)
            self._gehoert_zuletzt = jetzt.mono if self._gehoert_lauf else None
        for _ in range(GEHOERT_NACHRICHTEN_JE_TICK):
            if not self._gehoert_lauf:
                return
            noch = {r["sitzung"] for r in g.zeilen}  # inzwischen quittierte Zeilen nicht mehr senden
            self._gehoert_lauf = [r for r in self._gehoert_lauf if r["sitzung"] in noch]
            teil = self._gehoert_lauf[:GEHOERT_JE_NACHRICHT]
            if not teil:
                return
            if not self.sende_event("gespielt", gehoert_modul.baue_nachricht(teil, g.kontext.boot_id, jetzt)):
                self._gehoert_los = True  # nicht verbunden: beim nächsten Mal wieder von vorn
                self._gehoert_lauf = []
                return
            self._gehoert_lauf = self._gehoert_lauf[GEHOERT_JE_NACHRICHT:]

    def _quittung(self, d: Mapping[str, Any]) -> None:
        """``gehoert_quittung`` (mqtt-v1 3.7): selbst behandelt, ohne Ablaufzeit und ``zeit_ok``, idempotent, nie ``befehl_abgelehnt``.

        # B1-OFFEN: Von der Hülle prüft die Box nur ``v`` (Größe, JSON, Version wie bei jeder Nachricht); ``id``, ``erzeugt`` und ``ttl_s``
        # werden nicht verlangt (der Vertrag sagt nur, Ablauf und ``zeit_ok`` zählen nicht). Eine ungültige Liste wird ignoriert und beendet den Handshake nicht."""
        daten = d.get("daten")
        liste = daten.get("sitzungen") if isinstance(daten, dict) else None
        if (
            self.gehoert is None
            or not isinstance(liste, list)
            or len(liste) > MAX_QUITTUNG
            or not all(isinstance(x, str) and len(x) <= 64 for x in liste)
        ):
            logge("ha", "WARNING", "quittung", "ungueltig" if self.gehoert is not None else "ohne_gehoert")
            return
        n = self.gehoert.quittiere(liste, self.uhr.jetzt())
        logge("ha", "INFO", "quittung", "angenommen", daten={"anzahl": len(liste), "geloescht": n})
        # jede Quittung beendet den Handshake, auch eine nicht leere; aber nur, wenn HA ``gehoert_wartet = true`` schon gesehen haben kann
        # (sonst wäre es eine nachgereichte Quittung auf einen älteren Status)
        if self._gehoert_wartet and self._gehoert_gemeldet is True:
            self._gehoert_wartet = False
            self._gehoert_los = True

    async def _status_schleife(self) -> None:
        while True:
            try:
                self.tick()
            except Exception as e:  # noqa: BLE001 - der Dauerlauf darf nie stehen bleiben
                logge("ha", "ERROR", "status", "fehler", daten={"detail": repr(e)})
            await asyncio.sleep(1.0)

    def sende_event(self, art: str, daten: Mapping[str, Any]) -> bool:
        """Eine Meldung auf ``…/event`` (nicht dauerhaft). Ohne Verbindung geht sie verloren; das Protokoll hat sie."""
        n = {"v": NACHRICHT_VERSION, "id": str(uuid.uuid4()), "ts": zeitstempel(self.uhr.jetzt().wall), "art": art, "daten": dict(daten)}
        gesendet = self._veroeffentliche_json(self.themen.event, n, False) is not None
        if not gesendet:
            logge("ha", "WARNING", "event", "nicht_gesendet", daten={"art": art})
        return gesendet

    def _fehler(self, code: str, text: str) -> None:
        self.sende_event("fehler", {"baustein": "ha", "code": code, "text": text})

    def fuehre_aus(self, b: ev.Befehl) -> None:
        """``EreignisSenden`` des Kerns (``befehl_abgelehnt``, ``fehler``) auf ``…/event`` veröffentlichen."""
        if isinstance(b, ev.EreignisSenden):
            daten = dict(b.daten)
            if b.art == "fehler":
                daten.setdefault("baustein", "kern")
                daten.setdefault("code", "unbekannt")
                daten.setdefault("text", "")
            self.sende_event(b.art, daten)

    # -- Unbekannte Kennungen ------------------------------------------------------

    def melde(self, e: ev.Eintrag) -> None:
        """Einen Eintrag aus ``unknown.json`` dauerhaft auf seinem Thema veröffentlichen (4.1, Schritt 2).

        Ohne Verbindung tut es nichts: Beim nächsten Verbinden werden alle offenen Einträge veröffentlicht."""
        if not self._bereit:
            return
        n = {
            "v": NACHRICHT_VERSION, "uid": e.uid, "art": e.art, "zuerst": e.zuerst, "zuletzt": e.zuletzt,
            "anzahl": e.anzahl, "zeit_ok": e.zeit_ok, "befehl_id": e.befehl_id,
        }
        self._veroeffentliche_json(self.themen.unknown(e.uid), n, True)

    def _offener(self, uid: str, zuletzt: str, art: str) -> ev.Eintrag | None:
        for e in self.outbox.offen():
            if e.uid == uid and e.zuletzt == zuletzt and e.art == art:
                return e
        return None

    async def _ack(self, uid: str, nutzlast: bytes) -> None:
        d = await self._lies_json(nutzlast, MAX_NACHRICHT, "ack")
        if d is None:
            return
        zuletzt, art, grund = d.get("zuletzt"), d.get("art"), d.get("grund")
        if not isinstance(grund, str) or grund not in ACK_GRUENDE:
            logge("ha", "WARNING", "ack_grund", "unbekannt", daten={"uid": uid, "grund": str(grund)[:40]})  # wirkt wie ``bekannt``
        if not isinstance(zuletzt, str) or art not in ARTEN:
            logge("ha", "WARNING", "ack_veraltet", "unpassend", daten={"uid": uid})  # Version 1 verlangt ``zuletzt`` und ``art``
            return
        grund_text = grund if isinstance(grund, str) else "unbekannt"
        if self._offener(uid, zuletzt, art) is None:
            # Gehört zu einer älteren Fassung oder zu nichts: ``outbox`` protokolliert und löscht nichts.
            await self._gib(ev.Bestaetigt(uid, grund_text, zuletzt, art))
            return
        schluessel = (uid, zuletzt, art)
        if schluessel in self._loeschungen:
            logge("ha", "INFO", "ack", "doppelt", daten={"uid": uid})
            return

        async def geloescht() -> None:
            await self._nach_loeschung(uid, grund_text, zuletzt, art)

        # Erst die dauerhafte Nachricht löschen (leere Nutzlast), nach deren PUBACK den Eintrag (4.1, Schritt 4)
        if self._veroeffentliche(self.themen.unknown(uid), b"", True, geloescht) is None:
            logge("ha", "WARNING", "ack", "nicht_verbunden", daten={"uid": uid})  # Eintrag bleibt, HA bestätigt nach dem Verbinden erneut
            return
        self._loeschungen.add(schluessel)

    async def _nach_loeschung(self, uid: str, grund: str, zuletzt: str, art: str) -> None:
        self._loeschungen.discard((uid, zuletzt, art))
        if self._offener(uid, zuletzt, art) is not None:
            await self._gib(ev.Bestaetigt(uid, grund, zuletzt, art))  # ``outbox`` löscht den Eintrag
            return
        # Der Eintrag hat sich inzwischen geändert: Er bleibt, und seine dauerhafte Nachricht kommt zurück
        for e in self.outbox.offen():
            if e.uid == uid:
                logge("ha", "INFO", "ack", "eintrag_geaendert", daten={"uid": uid})
                self.melde(e)

    # -- Eingehende Nachrichten ----------------------------------------------------

    async def verarbeite(self, thema: str, nutzlast: bytes) -> None:
        """Eine Nachricht des Brokers behandeln (Eingang für den Netz-Thread und für Tests)."""
        t = self.themen
        uid = t.uid_aus_ack(thema)
        if thema == t.config:
            await self._config(nutzlast)
        elif thema == t.cmd:
            await self._cmd(nutzlast)
        elif uid is not None:
            await self._ack(uid, nutzlast)
        elif thema == t.ha_status:
            if nutzlast.strip() == b"online" and self._bereit:
                self._discovery_senden()  # HA ist (neu) gestartet und kennt die Entitäten nicht mehr
                if self.gehoert is not None:
                    self._gehoert_neu_warten()  # neuer Handshake; der Status mit ``gehoert_wartet = true`` geht gleich hinaus
                    self._status_senden()
        else:
            logge("ha", "WARNING", "thema", "unbekannt", daten={"thema": thema[:80]})

    async def _lies_json(self, nutzlast: bytes, grenze: int, wo: str) -> dict[str, Any] | None:
        if len(nutzlast) > grenze:
            logge("ha", "WARNING", "nachricht", "zu_gross", daten={"wo": wo, "bytes": len(nutzlast)})
            self._fehler("nachricht_zu_gross", f"{wo}: Nachricht größer als {grenze // 1024} KiB verworfen")
            return None
        try:
            d = json.loads(nutzlast)
        except (ValueError, UnicodeDecodeError):
            d = None
        if not isinstance(d, dict):
            logge("ha", "WARNING", "nachricht", "kein_json_objekt", daten={"wo": wo})
            self._fehler("nachricht_ungueltig", f"{wo}: kein JSON-Objekt")
            return None
        v = d.get("v")
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            logge("ha", "WARNING", "nachricht", "v_fehlt", daten={"wo": wo})
            self._fehler("nachricht_ungueltig", f"{wo}: v fehlt oder ist ungültig")
            return None
        if v > NACHRICHT_VERSION:
            logge("ha", "WARNING", "nachricht", "v_unbekannt", daten={"wo": wo, "v": v})
            self._fehler("v_unbekannt", f"{wo}: Nachrichtenversion {v} ist neuer als {NACHRICHT_VERSION}")
            return None
        return d

    # -- Konfiguration (5.2) -------------------------------------------------------

    async def _config(self, nutzlast: bytes) -> None:
        if not nutzlast:
            return  # leere dauerhafte Nachricht: HA hat sie gelöscht, die Box behält ihre Kopie (4.3, Punkt 5)
        roh: Any = None
        if len(nutzlast) <= MAX_KONFIG:
            try:
                roh = json.loads(nutzlast)
            except (ValueError, UnicodeDecodeError):
                roh = None
        if not isinstance(roh, dict):
            self._liste_abgelehnt({}, "schema_ungueltig")
            return
        store = self.konfig_store
        # ``annehmen`` prüft mit ``store.validiere_konfig`` und wendet die Revisionsregel an; es schreibt mit ``fsync``
        angenommen = await asyncio.to_thread(store.annehmen, roh)
        if angenommen.angenommen:
            logge("ha", "INFO", "konfig", "angenommen",
                  daten={"revision": store.konfig.revision, "liste_id": store.konfig.liste_id})
            await self._gib(ev.KonfigGeladen(store.konfig))
        elif angenommen.grund != "gleich":  # gleich: dieselbe Fassung noch einmal (dauerhafte Nachricht), nichts zu tun
            self._liste_abgelehnt(roh, angenommen.grund)

    def _liste_abgelehnt(self, roh: Mapping[str, Any], grund: str) -> None:
        liste_id = roh.get("liste_id")
        revision = roh.get("revision")
        daten = {
            "liste_id": liste_id if isinstance(liste_id, str) else "",
            "revision": revision if isinstance(revision, int) and not isinstance(revision, bool) else 0,
            "gespeichert_liste_id": self.konfig_store.konfig.liste_id,
            "gespeichert_revision": self.konfig_store.konfig.revision,
            "grund": grund,
        }
        schluessel = tuple(daten.values())
        if schluessel == self._letzte_ablehnung:
            return  # dieselbe Liste kommt bei jedem Verbinden wieder: HA bekommt die Meldung nur einmal
        self._letzte_ablehnung = schluessel
        logge("ha", "WARNING", "liste_abgelehnt", grund, daten=daten)
        self.sende_event("liste_abgelehnt", daten)

    # -- Befehle (3.7) -------------------------------------------------------------

    async def _cmd(self, nutzlast: bytes) -> None:
        d = await self._lies_json(nutzlast, MAX_NACHRICHT, "cmd")
        if d is None:
            return
        befehl, bid = d.get("befehl"), d.get("id")
        if befehl == "gehoert_quittung":
            self._quittung(d)
            return
        if befehl not in BEFEHLE:
            logge("ha", "WARNING", "befehl", "unbekannt", daten={"befehl": str(befehl)[:40]})
            self._fehler("befehl_unbekannt", f"unbekannter Befehl {str(befehl)[:40]!r}")
            return
        if not isinstance(bid, str) or not bid or len(bid) > 64:
            self._fehler("befehl_ungueltig", f"{befehl}: id fehlt")
            return
        if bid in self._befehl_ids:
            logge("ha", "INFO", "befehl", "doppelt", bid, daten={"befehl": befehl})
            return
        erzeugt, ttl = _parse_zeit(d.get("erzeugt")), d.get("ttl_s")
        if erzeugt is None or isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= 3600:
            logge("ha", "WARNING", "befehl", "ungueltig", bid, daten={"befehl": befehl})
            self._fehler("befehl_ungueltig", f"{befehl}: erzeugt oder ttl_s ungültig")
            return
        bis = erzeugt + ttl
        daten = d.get("daten")
        version = daten.get("version") if isinstance(daten, dict) else None
        if befehl == "update" and not (isinstance(version, str) and _VERSION_MUSTER.match(version)):
            self._befehl_ids.append(bid)
            logge("ha", "WARNING", "befehl", "version_ungueltig", bid)
            self.sende_event("befehl_abgelehnt", {"befehl": "update", "befehl_id": bid, "grund": "bedingung",
                                                  "detail": "Die Version im Update-Befehl ist ungültig."})
            return
        self._befehl_ids.append(bid)
        logge("ha", "INFO", "befehl", "angenommen", bid, daten={"befehl": befehl, "gueltig_bis": bis})
        if befehl == "lernen":
            await self._gib(ev.HaLernmodus(bid, bis))
        elif befehl == "lernen_abbrechen":
            await self._gib(ev.HaLernmodusAbbruch(bid, bis))
        elif befehl == "sync":
            await self._gib(ev.HaSyncAnstossen(bid, bis))
        else:
            await self._gib(ev.HaUpdateAnstossen(bid, str(version), bis))
