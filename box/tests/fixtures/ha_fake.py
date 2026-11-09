"""Hilfen für die Tests von ``ha``: ein Klient ohne Netz und ein Aufbau mit allen Teilen (ohne ``app``)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from tobibox import events as ev
from tobibox.clock import SimUhr
from tobibox.config import MqttKonfig
from tobibox.ha import Ha, PahoKlient, Themen
from tobibox.outbox import Outbox
from tobibox.status import Statussammler
from tobibox.store import KonfigStore

BOX = "box1"
LISTE_A = "a3f9c1e07b2d4856"
LISTE_B = "b3f9c1e07b2d4857"
UID = "04a1b2c3"


def konfig_json(revision: int = 1, liste_id: str = LISTE_A, **zusatz: Any) -> dict[str, Any]:
    """Eine gültige Liste (Version 2) wie sie HA veröffentlicht."""
    roh = {
        "schema_version": 2,
        "revision": revision,
        "liste_id": liste_id,
        "erzeugt_am": "2026-11-05T09:30:00Z",
        "zuordnungen": {
            "e0040312345678ab": {"ziel": {"typ": "serie", "serie": "3f9a1c07b2d4"}},
            UID: {"ziel": {"typ": "folge", "serie": "8c21d5e9a0b7", "folge": "folge-03.mp3"}},
            "04ffeedd": {"ziel": {"typ": "aktion", "aktion": "status"}},
        },
        "leise_zeiten": {"zeitzone": "Europe/Berlin", "fenster": []},
        "gute_nacht": {"timer_min": 30, "ausblenden_s": 60},
    }
    roh.update(zusatz)
    return roh


def als_bytes(d: Any) -> bytes:
    return json.dumps(d).encode("utf-8")


def cmd(befehl: str = "lernen", *, id: str = "6f1c0a7e-3b52-4d1a-9c58-0e2b7a41d9f3", erzeugt: str | None = None,
        ttl_s: int = 60, daten: dict | None = None, **zusatz: Any) -> dict[str, Any]:
    n = {"v": 1, "id": id, "befehl": befehl, "erzeugt": erzeugt or "2023-11-14T22:13:20Z", "ttl_s": ttl_s, "daten": daten or {}}
    n.update(zusatz)
    return n


class FakeKlient:
    """Ein MQTT-Klient ohne Netz. Die Rückrufe ruft der Test auf (``verbinde``, ``eingang``, …)."""

    def __init__(self, auto_abonniert: bool = True, auto_puback: bool = True) -> None:
        self.auto_abonniert = auto_abonniert
        self.auto_puback = auto_puback
        self.bei_verbunden = self.bei_getrennt = self.bei_abonniert = self.bei_nachricht = self.bei_veroeffentlicht = None
        self.gesendet: list[tuple[str, bytes, bool]] = []
        self.abonniert: list[list[tuple[str, int]]] = []
        self.mid = 0
        self.ist_verbunden = False
        self.gestartet = self.gestoppt = False

    # -- Klient ---
    def starten(self) -> None:
        self.gestartet = True

    def abonnieren(self, themen: list[tuple[str, int]]) -> None:
        self.abonniert.append(list(themen))
        if self.auto_abonniert and self.bei_abonniert:
            self.bei_abonniert()

    def veroeffentlichen(self, thema: str, nutzlast: bytes, retain: bool) -> int | None:
        if not self.ist_verbunden:
            return None
        self.mid += 1
        self.gesendet.append((thema, nutzlast, retain))
        if self.auto_puback and self.bei_veroeffentlicht:
            self.bei_veroeffentlicht(self.mid)
        return self.mid

    def stoppen(self) -> None:
        self.gestoppt = True

    # -- Test ---
    def verbinde(self) -> None:
        self.ist_verbunden = True
        assert self.bei_verbunden
        self.bei_verbunden()

    def trenne(self) -> None:
        self.ist_verbunden = False
        assert self.bei_getrennt
        self.bei_getrennt()

    def eingang(self, thema: str, nutzlast: bytes | dict) -> None:
        assert self.bei_nachricht
        self.bei_nachricht(thema, nutzlast if isinstance(nutzlast, bytes) else als_bytes(nutzlast))

    def puback(self, mid: int) -> None:
        assert self.bei_veroeffentlicht
        self.bei_veroeffentlicht(mid)

    def auf(self, thema: str) -> list[tuple[bytes, bool]]:
        """Alles, was auf ``thema`` gesendet wurde: ``(Nutzlast, retained)``."""
        return [(n, r) for t, n, r in self.gesendet if t == thema]

    def json_auf(self, thema: str) -> list[dict]:
        return [json.loads(n) for n, _ in self.auf(thema) if n]


class Aufbau:
    """``Ha`` mit echtem ``KonfigStore`` und ``Outbox`` in ``verz``, simulierter Uhr und einem Klienten ohne Netz."""

    def __init__(self, verz: Path, *, klient: FakeKlient | None = None, serien: list | None = None,
                 frei_mb: int | None = 4096, anzeigename: str = "box1", mqtt: MqttKonfig | None = None) -> None:
        self.verz = verz
        verz.mkdir(parents=True, exist_ok=True)
        self.uhr = SimUhr()
        self.store = KonfigStore(verz)
        self.store.laden()
        self.outbox = Outbox(verz)
        self.outbox.laden()
        self.status = Statussammler()
        if mqtt is not None and klient is None:
            klient = PahoKlient(mqtt, Themen(mqtt.box_id).online)  # echter Klient, z. B. gegen einen lokalen Mosquitto
        self.klient = klient or FakeKlient()
        self.ereignisse: list[ev.Ereignis] = []
        self.bestaetigt_angenommen: list[bool] = []
        self.serien: list = serien if serien is not None else []
        self.frei_mb = frei_mb
        self.ha = Ha(
            mqtt or MqttKonfig(BOX, "localhost", anzeigename=anzeigename),
            konfig_store=self.store, outbox=self.outbox, status=self.status, uhr=self.uhr,
            ausgabe=self._ausgabe, medien=verz, serien=lambda: self.serien, klient=self.klient,
            speicher_frei_mb=lambda: self.frei_mb,
        )

    def _ausgabe(self, e: ev.Ereignis) -> None:
        """Wie ``app``: Bestätigungen gehen zuerst an die Outbox; alles Übrige wird gemerkt."""
        self.ereignisse.append(e)
        self.status.beobachte(e, self.uhr.jetzt())
        if isinstance(e, ev.Bestaetigt):
            self.bestaetigt_angenommen.append(self.outbox.bestaetigt(e.id, e.grund, e.zuletzt, e.art))

    async def start(self, verbunden: bool = True) -> Aufbau:
        await self.ha.start()
        if verbunden:
            await self.verbinde()
        return self

    async def verbinde(self) -> None:
        self.klient.verbinde()
        await self.ha.leere()

    async def stop(self) -> None:
        self.klient.auto_puback = True  # sonst wartet ``stop`` die Frist auf den PUBACK von ``offline`` ab
        await self.ha.stop()

    async def sende(self, thema: str, nutzlast: bytes | dict) -> None:
        self.klient.eingang(thema, nutzlast)
        await self.ha.leere()

    def typen(self, klasse: type) -> list:
        return [e for e in self.ereignisse if isinstance(e, klasse)]


# --------------------------------------------------------------------------
# Fake-HA für die CUJ-Tests mit der echten ``App`` (AP 3.7): spielt Home Assistant über einen echten Mosquitto
# --------------------------------------------------------------------------


class FakeHa:
    """Home Assistant aus Sicht der Box, über ``GegenstelleHa`` (Konto ``ha``, alle Rechte).

    * ``konfig_ausrollen``: veröffentlicht ``tobibox/config`` dauerhaft mit der nächsten Revision (wartet auf den PUBACK).
    * ``bestaetigen``: antwortet auf ``…/unknown/<uid>/ack`` mit ``zuletzt`` und ``art`` der **zuletzt empfangenen** Meldung.
    * ``ordne_zu``: Konfiguration **zuerst**, dann ``ack`` ``zugeordnet`` (``mqtt-v1.md``, 4.2, Schritt 5 und 6; Entscheidung H).
    * ``befehl``: ein Befehl auf ``…/cmd`` (nicht dauerhaft).
    """

    def __init__(self, gegenstelle: Any, box: str = BOX, liste_id: str = LISTE_A) -> None:
        self.g = gegenstelle
        self.box = box
        self.liste_id = liste_id
        self.revision = 0
        self.zuordnungen: dict[str, Any] = {}
        self.gesendet: list[tuple[str, str]] = []  # ("config" | "ack" | "cmd", Beschreibung) in der Reihenfolge des Sendens

    # -- Empfang --------------------------------------------------------------------------------------------

    def meldungen(self, uid: str) -> list[dict]:
        """Alle Meldungen der Box auf ``tobibox/<box>/unknown/<uid>`` (ohne die leeren Löschungen)."""
        return self.g.json_auf(f"tobibox/{self.box}/unknown/{uid}")

    def loeschungen(self, uid: str) -> int:
        """Wie oft die Box die dauerhafte Nachricht gelöscht hat (leere Nutzlast)."""
        return sum(1 for n, _ in self.g.auf(f"tobibox/{self.box}/unknown/{uid}") if not n)

    def ereignisse(self, art: str | None = None) -> list[dict]:
        alle = self.g.json_auf(f"tobibox/{self.box}/event")
        return [e for e in alle if art is None or e["art"] == art]

    def status(self) -> dict | None:
        s = self.g.json_auf(f"tobibox/{self.box}/status")
        return s[-1] if s else None

    # -- Senden ---------------------------------------------------------------------------------------------

    def konfig_ausrollen(self, zuordnungen: dict[str, Any] | None = None, *, revision: int | None = None,
                         liste_id: str | None = None, **zusatz: Any) -> dict:
        """Eine neue Fassung der Liste; ``zuordnungen`` ersetzt die bisherigen (sonst bleiben sie)."""
        if zuordnungen is not None:
            self.zuordnungen = dict(zuordnungen)
        self.revision = revision if revision is not None else self.revision + 1
        if liste_id is not None:
            self.liste_id = liste_id
        roh = konfig_json(revision=self.revision, liste_id=self.liste_id, zuordnungen=self.zuordnungen, **zusatz)
        self.g.veroeffentliche("tobibox/config", roh, retain=True)
        self.gesendet.append(("config", f"revision {self.revision}"))
        return roh

    def bestaetigen(self, uid: str, grund: str = "neu", *, zuletzt: str | None = None, art: str | None = None) -> None:
        m = self.meldungen(uid)
        assert m or zuletzt, f"keine Meldung für {uid} empfangen"
        n = {"v": 1, "ts": "2026-11-09T10:00:00Z", "zuletzt": zuletzt or m[-1]["zuletzt"], "art": art or m[-1]["art"], "grund": grund}
        self.g.veroeffentliche(f"tobibox/{self.box}/unknown/{uid}/ack", n)
        self.gesendet.append(("ack", f"{uid} {grund}"))

    def ordne_zu(self, uid: str, ziel: dict[str, Any], name: str | None = None) -> None:
        """Zuordnung schreiben und veröffentlichen, **danach** bestätigen (Reihenfolge Konfiguration vor ``ack``)."""
        eintrag: dict[str, Any] = {"ziel": ziel}
        if name is not None:
            eintrag["name"] = name
        self.konfig_ausrollen({**self.zuordnungen, uid: eintrag})
        self.bestaetigen(uid, "zugeordnet")

    def befehl(self, befehl: str, *, erzeugt: str | None = None, ttl_s: int = 60, id: str | None = None, daten: dict | None = None) -> str:
        n = cmd(befehl, erzeugt=erzeugt, ttl_s=ttl_s, daten=daten, id=id or str(uuid.uuid4()))  # jede ``id`` neu, sonst gilt sie als doppelt
        self.g.veroeffentliche(f"tobibox/{self.box}/cmd", n)
        self.gesendet.append(("cmd", befehl))
        return n["id"]
