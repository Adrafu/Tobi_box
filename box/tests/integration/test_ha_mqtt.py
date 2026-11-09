"""``ha`` gegen einen echten lokalen Mosquitto (AP 3.3).

Der Broker verlangt ein Konto und wendet die Rechte aus ``mqtt-v1.md`` Abschnitt 7 an. Eine Gegenstelle spielt
Home Assistant. Ohne ``mosquitto`` werden die Tests übersprungen.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fixtures.ha_fake import BOX, LISTE_A, LISTE_B, UID, Aufbau, cmd, konfig_json
from fixtures.mosquitto import PASSWOERTER, GegenstelleHa, TestBroker, broker, gegenstelle, warte_bis  # noqa: F401

from tobibox import events as ev
from tobibox.config import MqttKonfig
from tobibox.outbox import zeitstempel

ONLINE = f"tobibox/{BOX}/online"
STATUS = f"tobibox/{BOX}/status"
EVENT = f"tobibox/{BOX}/event"
CMD = f"tobibox/{BOX}/cmd"
UNKNOWN = f"tobibox/{BOX}/unknown/{UID}"


def mqtt_konfig(b: TestBroker, konto: str = BOX) -> MqttKonfig:
    return MqttKonfig(konto, "127.0.0.1", b.port, passwort=PASSWOERTER[konto])


async def box(tmp_path: Path, b: TestBroker, name: str = "z") -> Aufbau:
    """Ein Dienst mit echtem Klienten; wartet, bis er sich angemeldet und veröffentlicht hat."""
    a = Aufbau(tmp_path / name, mqtt=mqtt_konfig(b))
    await a.start(verbunden=False)
    await warte_bis(lambda: a.ha._bereit, text="Box hat sich nicht verbunden")
    return a


def jetzt_utc() -> str:
    return zeitstempel(time.time())[:-5] + "Z"  # 2026-11-05T09:11:50Z


async def test_verbinden_birth_discovery_und_status(tmp_path, broker, gegenstelle):
    a = await box(tmp_path, broker)
    try:
        await warte_bis(lambda: gegenstelle.auf(STATUS) and len(gegenstelle.themen()) >= 16, text="Veröffentlichungen fehlen")
        assert gegenstelle.auf(ONLINE)[0][0] == b"online"  # live zugestellt: das Kennzeichen „retained“ prüft der spätere Leser
        s = gegenstelle.json_auf(STATUS)[0]
        assert s["v"] == 1 and isinstance(s["speicher_frei_mb"], int) and s["speicher_frei_mb"] > 0  # echter Platz
        discovery = {t for t in gegenstelle.themen() if t.startswith("homeassistant/")}
        assert len(discovery) == 14 and all(f"/tobibox_{BOX}/" in t for t in discovery)
        assert a.typen(ev.HaVerbindung) == [ev.HaVerbindung(True)]
        # ein später hinzukommender Leser (neuer Abonnent) bekommt alles dauerhaft zugestellt
        spaeter = GegenstelleHa(broker.port)
        try:
            await warte_bis(lambda: len(spaeter.themen()) >= 16, text="dauerhafte Nachrichten fehlen")
            assert all(r for t, _, r in spaeter.nachrichten)
            assert {ONLINE, STATUS} <= spaeter.themen() and discovery <= spaeter.themen()
        finally:
            spaeter.stop()
    finally:
        await a.stop()


async def test_sauberes_beenden_zeigt_offline(tmp_path, broker, gegenstelle):
    a = await box(tmp_path, broker)
    await a.stop()
    await warte_bis(lambda: gegenstelle.auf(ONLINE) and gegenstelle.auf(ONLINE)[-1][0] == b"offline", text="offline fehlt")
    leser2 = GegenstelleHa(broker.port, filter_=(ONLINE,))
    try:
        await warte_bis(lambda: leser2.auf(ONLINE), text="offline nicht dauerhaft")
        assert leser2.auf(ONLINE) == [(b"offline", True)]  # dauerhaft
    finally:
        leser2.stop()


async def test_konfiguration_wird_geholt_und_beim_neustart_nicht_wiederholt(tmp_path, broker, gegenstelle):
    gegenstelle.veroeffentliche("tobibox/config", konfig_json(revision=17), retain=True)
    a = await box(tmp_path, broker)
    try:
        await warte_bis(lambda: a.typen(ev.KonfigGeladen), text="Konfiguration kam nicht an")
        assert a.typen(ev.KonfigGeladen)[0].konfig.revision == 17
        assert json.loads((a.verz / "config.json").read_text())["revision"] == 17
    finally:
        await a.stop()
    # Neustart mit derselben Platte: der Broker liefert dieselbe Fassung erneut, die Box tut nichts und meldet nichts
    b = await box(tmp_path, broker)
    try:
        time.sleep(0.5)
        await b.ha.leere()
        assert b.typen(ev.KonfigGeladen) == []
        assert [e for e in gegenstelle.json_auf(EVENT) if e["art"] == "liste_abgelehnt"] == []
        assert b.store.konfig.revision == 17
    finally:
        await b.stop()


async def test_niedrigere_revision_wird_abgelehnt_und_an_ha_gemeldet(tmp_path, broker, gegenstelle):
    a = await box(tmp_path, broker)
    try:
        gegenstelle.veroeffentliche("tobibox/config", konfig_json(revision=17), retain=True)
        await warte_bis(lambda: a.typen(ev.KonfigGeladen), text="erste Liste")
        gegenstelle.veroeffentliche("tobibox/config", konfig_json(revision=12), retain=True)
        await warte_bis(lambda: gegenstelle.json_auf(EVENT), text="Meldung liste_abgelehnt fehlt")
        (m,) = [e for e in gegenstelle.json_auf(EVENT) if e["art"] == "liste_abgelehnt"]
        assert m["daten"]["grund"] == "revision_zu_niedrig"
        assert (m["daten"]["revision"], m["daten"]["gespeichert_revision"]) == (12, 17)
        assert a.store.konfig.revision == 17
        # neue Listen-ID: gewinnt auch mit niedriger Revision
        gegenstelle.veroeffentliche("tobibox/config", konfig_json(revision=1, liste_id=LISTE_B), retain=True)
        await warte_bis(lambda: len(a.typen(ev.KonfigGeladen)) == 2, text="neue Listen-ID")
        assert a.store.konfig.liste_id == LISTE_B and a.store.konfig.revision == 1
    finally:
        await a.stop()


async def test_befehl_mit_ablaufzeit(tmp_path, broker, gegenstelle):
    a = await box(tmp_path, broker)
    try:
        gegenstelle.veroeffentliche(CMD, cmd("lernen", id="b-1", erzeugt=jetzt_utc(), ttl_s=60))
        await warte_bis(lambda: a.typen(ev.HaLernmodus), text="Befehl kam nicht an")
        (e,) = a.typen(ev.HaLernmodus)
        assert e.befehl_id == "b-1" and time.time() < e.gueltig_bis <= time.time() + 61
        # derselbe Befehl noch einmal (QoS 1 kann doppelt zustellen): wirkt einmal
        gegenstelle.veroeffentliche(CMD, cmd("lernen", id="b-1", erzeugt=jetzt_utc(), ttl_s=60))
        # ein abgelaufener Befehl wird mit seiner Ablaufzeit weitergegeben; der Kern ignoriert ihn
        gegenstelle.veroeffentliche(CMD, cmd("sync", id="b-2", erzeugt="2020-01-01T00:00:00Z", ttl_s=60))
        await warte_bis(lambda: a.typen(ev.HaSyncAnstossen), text="abgelaufener Befehl kam nicht an")
        assert a.typen(ev.HaSyncAnstossen)[0].gueltig_bis < time.time()
        assert len(a.typen(ev.HaLernmodus)) == 1
        # Befehle an eine andere Box lesen wir nicht (und dürften es auch nicht)
        gegenstelle.veroeffentliche("tobibox/box2/cmd", cmd("sync", id="b-3", erzeugt=jetzt_utc()))
        gegenstelle.veroeffentliche(CMD, cmd("update", id="b-4", erzeugt=jetzt_utc(), daten={"version": "1.2.0"}))
        await warte_bis(lambda: a.typen(ev.HaUpdateAnstossen), text="update")
        assert [e.befehl_id for e in a.typen(ev.HaSyncAnstossen)] == ["b-2"]
    finally:
        await a.stop()


async def test_befehl_waehrend_die_box_aus_ist_kommt_ueber_die_dauerhafte_sitzung(tmp_path, broker, gegenstelle):
    a = await box(tmp_path, broker)
    await a.stop()  # sauber beendet; die Sitzung bleibt im Broker (clean_session=False)
    gegenstelle.veroeffentliche(CMD, cmd("sync", id="b-offline", erzeugt=jetzt_utc(), ttl_s=300))
    b = await box(tmp_path, broker)
    try:
        await warte_bis(lambda: b.typen(ev.HaSyncAnstossen), text="der Broker hat den Befehl nicht nachgeliefert")
        assert b.typen(ev.HaSyncAnstossen)[0].befehl_id == "b-offline"
    finally:
        await b.stop()


async def test_kennung_bleibt_in_unknown_json_bis_ha_bestaetigt(tmp_path, broker, gegenstelle):
    """Abnahme AP 3.3: Auch wenn der Broker die Nachricht schon angenommen hat, löscht nur das ``ack`` von HA den Eintrag."""
    a = await box(tmp_path, broker)
    try:
        e = a.outbox.melden("unbekannt", UID, None, a.uhr.jetzt())
        a.ha.melde(e)
        await warte_bis(lambda: gegenstelle.auf(UNKNOWN), text="Meldung kam nicht an")
        n, _ = gegenstelle.auf(UNKNOWN)[0]
        assert json.loads(n)["zuletzt"] == e.zuletzt
        leser = GegenstelleHa(broker.port, filter_=("tobibox/+/unknown/#",))
        try:
            await warte_bis(lambda: leser.auf(UNKNOWN), text="Meldung ist nicht dauerhaft")
            assert leser.auf(UNKNOWN)[0][1] is True  # „retained“
        finally:
            leser.stop()
        time.sleep(0.4)  # der Broker hat angenommen (PUBACK), HA hat nichts bestätigt
        await a.ha.leere()
        assert a.outbox.offen() == [e] and a.typen(ev.Bestaetigt) == []
        assert (a.verz / "unknown.json").exists() and UID in json.loads((a.verz / "unknown.json").read_text())["eintraege"]

        # ein ack zu einer älteren Fassung ändert nichts
        gegenstelle.veroeffentliche(f"{UNKNOWN}/ack", {"v": 1, "ts": "2026-11-05T09:12:05Z", "zuletzt": "2020-01-01T00:00:00.000Z",
                                                          "art": "unbekannt", "grund": "neu"})
        await warte_bis(lambda: a.typen(ev.Bestaetigt), text="ack kam nicht an")
        assert a.outbox.offen() == [e] and a.bestaetigt_angenommen == [False]

        # das richtige ack: erst wird die dauerhafte Nachricht gelöscht, dann der Eintrag
        gegenstelle.veroeffentliche(f"{UNKNOWN}/ack", {"v": 1, "ts": "2026-11-05T09:12:05Z", "zuletzt": e.zuletzt,
                                                          "art": "unbekannt", "grund": "neu"})
        await warte_bis(lambda: a.bestaetigt_angenommen == [False, True], text="Eintrag wurde nicht gelöscht")
        assert a.outbox.offen() == []
        assert json.loads((a.verz / "unknown.json").read_text())["eintraege"] == {}
        await warte_bis(lambda: gegenstelle.auf(UNKNOWN)[-1][0] == b"", text="die dauerhafte Nachricht wurde nicht gelöscht")
        spaeter = GegenstelleHa(broker.port, filter_=("tobibox/+/unknown/#",))
        try:
            time.sleep(0.4)
            assert spaeter.auf(UNKNOWN) == []  # ein neuer Abonnent sieht nichts mehr
        finally:
            spaeter.stop()
    finally:
        await a.stop()


async def test_offener_eintrag_wird_nach_neustart_erneut_veroeffentlicht(tmp_path, broker, gegenstelle):
    """Die Box stürzt ab, bevor HA bestätigt hat: Der Eintrag steht noch in ``unknown.json`` und geht beim Verbinden erneut raus."""
    a = await box(tmp_path, broker)
    e = a.outbox.melden("gelernt", UID, "b-lern", a.uhr.jetzt())
    a.ha.melde(e)
    await a.stop()
    gegenstelle.nachrichten.clear()
    b = await box(tmp_path, broker)
    try:
        assert b.outbox.offen() == [e]
        await warte_bis(lambda: gegenstelle.auf(UNKNOWN), text="nicht erneut veröffentlicht")
        n = json.loads(gegenstelle.auf(UNKNOWN)[-1][0])
        assert (n["art"], n["befehl_id"], n["zuletzt"]) == ("gelernt", "b-lern", e.zuletzt)
    finally:
        await b.stop()


async def test_verbindung_verloren_will_und_neuverbinden(tmp_path, broker, gegenstelle):
    a = await box(tmp_path, broker)
    try:
        await warte_bis(lambda: gegenstelle.auf(ONLINE), text="online")
        gegenstelle.nachrichten.clear()
        a.ha.klient.trenne_hart()  # ohne DISCONNECT: der Broker sendet den Will
        await warte_bis(lambda: [n for n, _ in gegenstelle.auf(ONLINE)] == [b"offline"], text="Will (offline) fehlt")
        await warte_bis(lambda: [n for n, _ in gegenstelle.auf(ONLINE)] == [b"offline", b"online"], frist_s=10,
                        text="Box hat sich nicht neu verbunden")
        await warte_bis(lambda: gegenstelle.auf(STATUS), text="Status nach dem Neuverbinden fehlt")
        await warte_bis(lambda: [v.ok for v in a.typen(ev.HaVerbindung)] == [True, False, True], text="HaVerbindung")
        assert a.ha._bereit
    finally:
        await a.stop()


async def test_ha_neustart_discovery_erneut(tmp_path, broker, gegenstelle):
    a = await box(tmp_path, broker)
    try:
        await warte_bis(lambda: len(gegenstelle.themen()) >= 16)
        n = len([t for t, _, _ in gegenstelle.nachrichten if t.startswith("homeassistant/") and t.endswith("/config")])
        gegenstelle.veroeffentliche("homeassistant/status", b"online")
        await warte_bis(lambda: len([t for t, _, _ in gegenstelle.nachrichten
                                     if t.startswith("homeassistant/") and t.endswith("/config")]) >= 2 * n, text="Discovery fehlt")
    finally:
        await a.stop()


async def test_status_wird_bei_aenderung_nachgefuehrt(tmp_path, broker, gegenstelle):
    a = await box(tmp_path, broker)
    try:
        await warte_bis(lambda: gegenstelle.auf(STATUS))
        a.status.beobachte(ev.AkkuStand(76), a.uhr.jetzt())
        a.status.beobachte(ev.NetzKlasse("hotspot"), a.uhr.jetzt())
        a.uhr.vor(10)  # simulierte Uhr: das 5-s-Fenster ist um (die Statusschleife der Box tickt jede Sekunde)
        await warte_bis(lambda: len(gegenstelle.json_auf(STATUS)) >= 2, text="Statusänderung kam nicht an")
        s = gegenstelle.json_auf(STATUS)[-1]
        assert (s["akku_prozent"], s["netz"]) == (76, "hotspot")
    finally:
        await a.stop()


async def test_falsches_passwort_verbindet_nicht(tmp_path, broker):
    schlecht = MqttKonfig(BOX, "127.0.0.1", broker.port, passwort="falsch")
    a = Aufbau(tmp_path / "z", mqtt=schlecht)
    await a.start(verbunden=False)
    try:
        time.sleep(1.0)
        await a.ha.leere()
        assert not a.ha._bereit and a.typen(ev.HaVerbindung) == []
    finally:
        await a.stop()


def test_kontorechte_aus_dem_vertrag(broker, gegenstelle):
    """Das Konto ``box1`` darf nur seine Themen schreiben (``mqtt-v1.md`` 7); die Vorlage der Tests setzt das um."""
    import paho.mqtt.client as mqtt

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="tobibox-box1-rechte", protocol=mqtt.MQTTv311)
    c.username_pw_set("box1", PASSWOERTER["box1"])
    c.connect("127.0.0.1", broker.port)
    c.loop_start()
    try:
        verboten = ["tobibox/config", f"tobibox/{BOX}/cmd", f"tobibox/{BOX}/unknown/{UID}/ack", "tobibox/box2/status",
                    "homeassistant/status", f"tobibox/{BOX}/ui/sync", "homeassistant/sensor/tobibox_box2/akku/config"]
        erlaubt = [ONLINE, STATUS, EVENT, UNKNOWN, f"homeassistant/sensor/tobibox_{BOX}/akku/config"]
        for t in verboten + erlaubt:
            c.publish(t, b"{}", qos=1).wait_for_publish(5)
        time.sleep(0.5)
        gesehen = gegenstelle.themen()
        assert not (set(verboten) & gesehen)
        assert set(erlaubt) <= gesehen
    finally:
        c.disconnect()
        c.loop_stop()
