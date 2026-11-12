"""MQTT-Schicht der Integration (``docs/protocol/mqtt-v1.md``, HA-Seite)."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import ANY, patch

import pytest
from homeassistant.components import mqtt as ha_mqtt
from homeassistant.components import persistent_notification
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_mqtt_message, async_fire_time_changed

from custom_components.tobibox.const import RE_LISTE_ID
from custom_components.tobibox.fehler import TobiboxFehler

from .conftest import ereignis_arten, warte_auf

UID1 = "e0040312345678ab"
UID2 = "04a1b2c3"
SERIE = {"typ": "serie", "serie": "rabe"}


# --- tobibox/config ---


async def test_config_retained_qos1_mit_revision_und_listen_id(hass, integration, box_fabrik, nas):
    nas.serie("rabe", "rabe", "Rabe")
    await integration.medien.pruefen()
    await integration.zuordnung_setzen(UID1, SERIE, name="Rabe aus Holz")
    konfigs = [e for e in box_fabrik("box1").veroeffentlicht() if e[0] == "tobibox/config"]
    assert [(q, r) for _t, _n, q, r in konfigs] == [(1, True), (1, True)]
    erste, zweite = (json.loads(n) for _t, n, _q, _r in konfigs)
    assert erste["liste_id"] == zweite["liste_id"]
    assert RE_LISTE_ID.match(zweite["liste_id"])
    assert (erste["revision"], zweite["revision"]) == (1, 2)
    assert zweite["schema_version"] == 2
    # Vertrag W 12.11., angelegt_am: Anlegen setzt den Zeitstempel (die Box ignoriert ihn)
    assert zweite["zuordnungen"] == {UID1: {"ziel": SERIE, "name": "Rabe aus Holz", "angelegt_am": ANY}}
    assert zweite["zuordnungen"][UID1]["angelegt_am"].endswith("Z")
    assert zweite["erzeugt_am"].endswith("Z")
    assert set(zweite) <= {"schema_version", "revision", "liste_id", "erzeugt_am", "zuordnungen", "leise_zeiten", "gute_nacht", "ton_pegel", "hinweis_pegel", "lesezeichen_tage"}
    assert len(json.dumps(zweite).encode()) < 256 * 1024


async def test_neu_ausrollen_erzeugt_neue_listen_id(hass, integration, box_fabrik, nas):
    nas.serie("rabe", "rabe", "Rabe")
    await integration.medien.pruefen()
    await integration.zuordnung_setzen(UID1, SERIE)
    alt = integration.store.konfig["liste_id"]
    erg = await integration.liste_neu_ausrollen()
    assert erg["veroeffentlicht"] is True
    neu = box_fabrik("box1").konfigs()[-1]
    assert neu["liste_id"] != alt
    assert neu["revision"] == 1  # eine neue Liste beginnt mit Revision 1
    # gleiche Zuordnungen und Einstellungen; Vertrag W 12.11., angelegt_am: Anlegen setzt den Zeitstempel, die neue Liste behält ihn
    assert neu["zuordnungen"] == {UID1: {"ziel": SERIE, "angelegt_am": ANY}}


async def test_ohne_verbindung_gespeichert_und_beim_wiederverbinden_nachgeholt(hass, integration, box_fabrik, nas):
    nas.serie("rabe", "rabe", "Rabe")
    await integration.medien.pruefen()
    box = box_fabrik("box1")
    anzahl = len(box.konfigs())
    with patch.object(ha_mqtt, "is_connected", return_value=False):
        erg = await integration.zuordnung_setzen(UID1, SERIE)
    assert erg["geaendert"] is True
    assert erg["veroeffentlicht"] is False  # gespeichert, wird nachgeholt
    assert len(box.konfigs()) == anzahl
    assert integration.store.konfig["zuordnungen"][UID1]
    async_dispatcher_send(hass, ha_mqtt.MQTT_CONNECTION_STATE, True)
    await warte_auf(hass, lambda: len(box.konfigs()) == anzahl + 1)
    assert box.konfigs()[-1]["revision"] == 2
    assert box.konfigs()[-1]["zuordnungen"][UID1]


async def test_ha_status_online_holt_offene_veroeffentlichung_nach(hass, integration, box_fabrik, nas):
    integration.store.veroeffentlicht_stand = None
    box = box_fabrik("box1")
    anzahl = len(box.konfigs())
    async_fire_mqtt_message(hass, "homeassistant/status", "online", 1, False)
    await warte_auf(hass, lambda: len(box.konfigs()) == anzahl + 1)


# --- unknown/<uid> und ack ---


async def test_unbekannte_kennung_wird_aufgenommen_und_bestaetigt(hass, integration, box_fabrik, ereignisse):
    b1, b2 = box_fabrik("box1"), box_fabrik("box2")
    meldung = await b1.unbekannt(UID1, zuletzt="2026-11-09T10:00:03.412Z")
    ack = b1.acks(UID1)
    assert len(ack) == 1
    assert ack[0]["v"] == 1
    assert ack[0]["grund"] == "neu"
    assert ack[0]["zuletzt"] == meldung["zuletzt"]  # unverändert zurückgegeben, mit Millisekunden
    assert ack[0]["art"] == "unbekannt"
    assert ack[0]["ts"].endswith("Z")
    thema, _n, qos, retain = [e for e in b1.veroeffentlicht() if e[0].endswith("/ack")][0]
    assert (thema, qos, retain) == (f"tobibox/box1/unknown/{UID1}/ack", 1, False)  # nicht retained
    assert ereignis_arten(ereignisse, "neue_tobies") == ["neu"]
    # die andere Box meldet dieselbe Kennung: ein Eintrag, ack "bekannt"
    await b2.unbekannt(UID1, zuletzt="2026-11-09T10:01:00.000Z")
    assert b2.acks(UID1)[0]["grund"] == "bekannt"
    assert len(integration.store.neue_tobies) == 1
    assert ereignis_arten(ereignisse, "neue_tobies")[-1] == "aktualisiert"


async def test_doppelte_zustellung_ist_unschaedlich(hass, integration, box_fabrik):
    b1 = box_fabrik("box1")
    daten = await b1.unbekannt(UID1, anzahl=3, zuletzt="2026-11-09T10:00:03.412Z")
    await b1.unbekannt(UID1, anzahl=3, zuletzt="2026-11-09T10:00:03.412Z")
    assert integration.store.neue_tobies[UID1]["anzahl"] == 3
    assert [a["grund"] for a in b1.acks(UID1)] == ["neu", "bekannt"]  # jede Zustellung wird bestätigt, die Box löscht nur bei passendem Stand
    assert daten["zuletzt"] == b1.acks(UID1)[1]["zuletzt"]


async def test_kennung_in_den_zuordnungen_ist_bekannt_und_kommt_nicht_in_die_liste(hass, integration, box_fabrik, nas):
    nas.serie("rabe", "rabe", "Rabe")
    await integration.medien.pruefen()
    await integration.zuordnung_setzen(UID1, SERIE)
    b1 = box_fabrik("box1")
    await b1.unbekannt(UID1)
    assert b1.acks(UID1)[0]["grund"] == "bekannt"
    assert UID1 not in integration.store.neue_tobies


async def test_leere_nachricht_und_ungueltiges_wird_ignoriert(hass, integration, box_fabrik):
    b1 = box_fabrik("box1")
    async_fire_mqtt_message(hass, f"tobibox/box1/unknown/{UID1}", "", 1, False)  # Löschen der dauerhaften Nachricht
    async_fire_mqtt_message(hass, f"tobibox/box1/unknown/{UID1}", "kein json", 1, False)
    async_fire_mqtt_message(hass, f"tobibox/box1/unknown/{UID1}", json.dumps({"v": 2, "uid": UID1, "art": "unbekannt", "zuerst": "x", "zuletzt": "y", "anzahl": 1}), 1, False)
    async_fire_mqtt_message(hass, f"tobibox/box1/unknown/{UID2}", json.dumps({"v": 1, "uid": UID1, "art": "unbekannt", "zuerst": "x", "zuletzt": "y", "anzahl": 1}), 1, False)
    async_fire_mqtt_message(hass, "tobibox/boxX/unknown/%s" % UID1, json.dumps({"v": 1, "uid": UID1, "art": "unbekannt", "zuerst": "x", "zuletzt": "y", "anzahl": 1}), 1, False)
    await hass.async_block_till_done()
    assert integration.store.neue_tobies == {}
    assert b1.acks(UID1) == [] and b1.acks(UID2) == []


async def test_verwerfen_und_erneute_meldung(hass, integration, box_fabrik):
    b1 = box_fabrik("box1")
    await b1.unbekannt(UID1)
    assert integration.neue_tobies_verwerfen(UID1) == {"entfernt": True}
    assert integration.neue_tobies_verwerfen(UID1) == {"entfernt": False}  # kein Fehler
    assert len(b1.acks(UID1)) == 1  # kein ack beim Verwerfen: die Bestätigung ging schon beim Eintreffen raus
    await b1.unbekannt(UID1)  # eine verworfene Kennung erscheint bei erneuter Meldung wieder
    assert UID1 in integration.store.neue_tobies
    with pytest.raises(TobiboxFehler):
        integration.neue_tobies_verwerfen("ZZ")


# --- Befehle ---


async def test_befehl_felder_und_lebensdauer(hass, integration, box_fabrik):
    await box_fabrik("box1").online()
    erg = await integration.box_sync("box1")
    assert erg["ttl_s"] == 300
    box = box_fabrik("box1")
    cmd = box.befehle("sync")[0]
    assert cmd["v"] == 1
    assert cmd["id"] == erg["befehl_id"]
    assert len(cmd["id"]) == 36  # UUID
    assert cmd["ttl_s"] == 300
    assert cmd["daten"] == {}
    assert dt_util.parse_datetime(cmd["erzeugt"]) is not None
    jetzt = dt_util.utcnow()
    assert abs((dt_util.parse_datetime(cmd["erzeugt"]) - jetzt).total_seconds()) < 5  # Wanduhr von HA
    thema, _n, qos, retain = [e for e in box.veroeffentlicht() if e[0] == "tobibox/box1/cmd"][0]
    assert (qos, retain) == (1, False)  # Befehle sind nicht dauerhaft


async def test_ablaufzeit_der_befehle_60_30_300(hass, integration, box_fabrik, nas):
    nas.serie("rabe", "rabe", "Rabe")
    await integration.medien.pruefen()
    b = box_fabrik("box1")
    await b.online()
    await integration.lernmodus.start("box1", SERIE)
    await integration.lernmodus.abbrechen("box1")
    await integration.box_sync("box1")
    assert [(c["befehl"], c["ttl_s"]) for c in b.befehle()] == [("lernen", 60), ("lernen_abbrechen", 30), ("sync", 300)]
    assert all(c["daten"] == {} for c in b.befehle())  # die Box bekommt das Ziel nicht


async def test_befehl_ohne_verbindung_wird_nicht_gesendet(hass, integration, box_fabrik):
    await box_fabrik("box1").online()
    with patch.object(ha_mqtt, "is_connected", return_value=False), pytest.raises(TobiboxFehler) as err:
        await integration.box_sync("box1")
    assert err.value.code == "mqtt_nicht_verbunden"
    assert box_fabrik("box1").befehle() == []


async def test_befehl_unbekannte_box_und_offline(hass, integration, box_fabrik):
    with pytest.raises(TobiboxFehler) as err:
        await integration.box_sync("box9")
    assert err.value.code == "box_unbekannt"
    with pytest.raises(TobiboxFehler) as err:  # online=null (HA kennt noch keine Nachricht) gilt als offline
        await integration.box_sync("box1")
    assert err.value.code == "box_offline"
    await box_fabrik("box1").online(False)
    with pytest.raises(TobiboxFehler) as err:
        await integration.box_sync("box1")
    assert err.value.code == "box_offline"


# --- ui/* (mqtt-v1.md, 3.8) ---


async def test_ui_sync_setzt_befehl_mit_frischer_ablaufzeit_um(hass, integration, box_fabrik):
    b = box_fabrik("box1")
    await b.online()
    await b.ui("sync")
    assert [c["befehl"] for c in b.befehle()] == ["sync"]
    await b.ui("sync", "irgendwas")  # nur PRESS zählt
    assert len(b.befehle()) == 1


async def test_ui_update_nimmt_die_neueste_version_aus_releases(hass, integration, box_fabrik, nas):
    b = box_fabrik("box1")
    await b.online()
    for n in ("tobibox-1.2.0.tar.gz", "tobibox-1.10.0.tar.gz", "tobibox-1.9.9.tar.gz", "tobibox-1.10.0.tar.gz.minisig", "x.txt"):
        (nas.releases / n).write_bytes(b"x")
    await b.ui("update")
    cmd = b.befehle("update")[0]
    assert cmd["daten"] == {"version": "1.10.0"}  # numerisch, nicht als Text sortiert
    assert cmd["ttl_s"] == 300


async def test_ui_update_ohne_version_zeigt_hinweis(hass, integration, box_fabrik):
    b = box_fabrik("box1")
    await b.online()
    await b.ui("update")
    assert b.befehle("update") == []
    meldungen = persistent_notification._async_get_or_create_notifications(hass)
    assert "tobibox_ui_box1" in meldungen
    assert "Version" in meldungen["tobibox_ui_box1"]["message"]


async def test_ui_lernen_abbrechen_und_lern_serie(hass, integration, box_fabrik):
    b = box_fabrik("box1")
    await b.online()
    await b.ui("lernen_abbrechen")
    assert [(c["befehl"], c["ttl_s"]) for c in b.befehle()] == [("lernen_abbrechen", 30)]
    await b.ui("lern_serie", "Der kleine Rabe")
    assert integration.mqtt.boxen["box1"].lern_serie == "Der kleine Rabe"
    assert len(b.befehle()) == 1  # setzt selbst keinen Befehl ab


# --- online, status, konfig_stand ---


async def test_online_status_und_konfig_stand(hass, integration, box_fabrik, ereignisse):
    b = box_fabrik("box1")
    assert integration.box_objekt("box1")["online"] is None
    assert integration.box_objekt("box1")["konfig_stand"] == "unbekannt"
    await b.online()
    k = integration.store.konfig
    await b.status(konfig={"revision": k["revision"], "liste_id": k["liste_id"]})
    obj = integration.box_objekt("box1")
    assert obj["online"] is True
    assert obj["konfig_stand"] == "aktuell"
    assert obj["status"]["akku_prozent"] == 80  # unverändert
    assert obj["status_empfangen_am"].endswith("Z")
    await b.status(konfig={"revision": k["revision"] - 1, "liste_id": k["liste_id"]})
    assert integration.box_objekt("box1")["konfig_stand"] == "veraltet"
    await b.status(konfig={"revision": 5, "liste_id": "ffffffffffffffff"})
    assert integration.box_objekt("box1")["konfig_stand"] == "veraltet"  # andere Listen-ID
    await b.online(False)
    assert integration.box_objekt("box1")["online"] is False
    assert "geaendert" in ereignis_arten(ereignisse, "boxen")


async def test_box_mit_neuerem_stand_meldet_abweichung(hass, integration, box_fabrik, ereignisse):
    b = box_fabrik("box1")
    k = integration.store.konfig
    await b.status(konfig={"revision": k["revision"] + 4, "liste_id": k["liste_id"]})
    assert integration.box_objekt("box1")["konfig_stand"] == "voraus"
    abw = [e["daten"] for e in ereignisse if e["thema"] == "konfig" and e["art"] == "abweichung"]
    assert abw == [{"box": "box1", "grund": "voraus", "box_liste_id": k["liste_id"], "box_revision": k["revision"] + 4, "ha_revision": k["revision"]}]
    revision = k["revision"]
    await b.status(konfig={"revision": k["revision"] + 4, "liste_id": k["liste_id"]})  # derselbe Stand: nicht noch einmal
    assert len([e for e in ereignisse if e["art"] == "abweichung"]) == 1
    assert integration.store.konfig["revision"] == revision  # die Integration erhöht die Revision nie von selbst


async def test_status_mit_zu_neuer_version_wird_verworfen(hass, integration, box_fabrik):
    async_fire_mqtt_message(hass, "tobibox/box1/status", json.dumps({"v": 2, "zustand": "spielt"}), 1, False)
    await hass.async_block_till_done()
    assert integration.box_objekt("box1")["status"] is None


async def test_discovery_liefert_den_anzeigenamen(hass, integration, box_fabrik):
    await box_fabrik("box1").discovery("Kinderzimmer")
    assert integration.box_objekt("box1")["anzeigename"] == "Kinderzimmer"
    assert integration.box_objekt("box2")["anzeigename"] is None


# --- event ---


async def test_ereignisse_liste_abgelehnt_idempotent_und_text(hass, integration, box_fabrik, ereignisse):
    b = box_fabrik("box1")
    daten = {"liste_id": "a" * 16, "revision": 12, "gespeichert_liste_id": "a" * 16, "gespeichert_revision": 17, "grund": "revision_zu_niedrig"}
    msg = await b.ereignis("liste_abgelehnt", daten, eid="11111111-1111-4111-8111-111111111111")
    async_fire_mqtt_message(hass, "tobibox/box1/event", json.dumps(msg), 1, False)  # doppelte Zustellung
    await hass.async_block_till_done()
    liste = integration.box_objekt("box1")["ereignisse"]
    assert len(liste) == 1  # dieselbe id wird einmal ausgewertet
    assert liste[0]["art"] == "liste_abgelehnt" and liste[0]["daten"] == daten
    assert "abgelehnt" in liste[0]["text"] and "12" in liste[0]["text"]
    neu = [e for e in ereignisse if e["thema"] == "boxen" and e["art"] == "ereignis"]
    assert len(neu) == 1 and neu[0]["daten"]["box"] == "box1"
    # die Box hat einen neueren Stand: Ereignis abweichung
    abw = [e["daten"] for e in ereignisse if e["art"] == "abweichung"]
    assert abw[0]["grund"] == "revision_zu_niedrig" and abw[0]["box_revision"] == 17


async def test_befehl_abgelehnt_zeit_unsicher_wird_zur_benachrichtigung(hass, integration, box_fabrik):
    b = box_fabrik("box1")
    await b.status(zeitquelle="unbekannt", zeit_ok=False)
    await b.ereignis("befehl_abgelehnt", {"befehl": "sync", "befehl_id": "x", "grund": "zeit_unsicher"}, eid="22222222-2222-4222-8222-222222222222")
    meldungen = persistent_notification._async_get_or_create_notifications(hass)
    text = meldungen["tobibox_befehl_22222222-2222-4222-8222-222222222222"]["message"]
    assert "sync" in text and "Uhr" in text and "unbekannt" in text


async def test_befehl_abgelehnt_bedingung_zeigt_detail(hass, integration, box_fabrik):
    b = box_fabrik("box1")
    await b.ereignis("befehl_abgelehnt", {"befehl": "sync", "grund": "bedingung", "detail": "Akku unter 50 Prozent"}, eid="33333333-3333-4333-8333-333333333333")
    meldungen = persistent_notification._async_get_or_create_notifications(hass)
    assert "Akku unter 50 Prozent" in meldungen["tobibox_befehl_33333333-3333-4333-8333-333333333333"]["message"]


async def test_zeit_vergeht_nicht_im_test(hass, integration):
    """Kleine Probe: Die HA-Uhr lässt sich für die Zeitgeber verschieben (Grundlage der Lernmodus-Tests)."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()
