"""Lernmodus, Weg B (Vertrag W, 3.6 und 6.2; ``mqtt-v1.md`` 4.2)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import ANY, patch

import pytest
from homeassistant.components import mqtt as ha_mqtt
from homeassistant.components import persistent_notification
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.tobibox.fehler import TobiboxFehler

from .conftest import warte_auf

UID = "e0040312345678ab"
UID2 = "04a1b2c3"
SERIE = {"typ": "serie", "serie": "rabe"}
FOLGE = {"typ": "folge", "serie": "rabe", "folge": "a.mp3"}


@pytest.fixture
async def lern(hass, integration, box_fabrik, nas, lege_mp3):
    """Serie ``rabe`` mit Folge ``a.mp3``, Box ``box1`` online."""
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3"])
    lege_mp3(pfad / "a.mp3")
    nas.serie("ue", "ue", "Überraschung", typ="ueberraschung")
    await integration.medien.pruefen()
    box = box_fabrik("box1")
    await box.online()
    return integration, box


async def zeit_vergeht(hass, freezer, sekunden: float) -> None:
    freezer.tick(timedelta(seconds=sekunden))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def lernmodus_ereignisse(ereignisse):
    return [e["daten"] for e in ereignisse if e["thema"] == "lernmodus"]


def zustaende(ereignisse):
    return [d["zustand"] for d in lernmodus_ereignisse(ereignisse)]


async def melde_gelernt(box, v, uid=UID, **kw):
    return await box.unbekannt(uid, art="gelernt", befehl_id=v["befehl_id"], **kw)


# --- Start ---


async def test_start_sendet_lernen_und_merkt_den_vorgang(hass, lern, ereignisse):
    hub, box = lern
    v = await hub.lernmodus.start("box1", SERIE, "Rabe aus Holz")
    cmd = box.befehle("lernen")
    assert len(cmd) == 1
    assert cmd[0]["id"] == v["befehl_id"] and cmd[0]["ttl_s"] == 60 and cmd[0]["daten"] == {}
    beginn = dt_util.parse_datetime(v["beginn"])
    assert dt_util.parse_datetime(v["frist_bis"]) - beginn == timedelta(seconds=180)  # 60 s Befehl + 120 s Lernfrist
    assert v["ziel"] == SERIE and v["box"] == "box1"
    assert hub.box_objekt("box1")["lernmodus"]["zustand"] == "wartet"
    assert zustaende(ereignisse) == ["wartet"]
    daten = lernmodus_ereignisse(ereignisse)[0]
    assert daten["befehl_id"] == v["befehl_id"] and daten["ziel"] == SERIE and daten["uid"] is None
    assert hub.snapshot("lernmodus")["vorgaenge"][0]["befehl_id"] == v["befehl_id"]


async def test_start_gleiches_ziel_liefert_den_laufenden_vorgang_anderes_ziel_verlangt_abbruch(hass, lern):
    hub, box = lern
    v1 = await hub.lernmodus.start("box1", SERIE)
    v2 = await hub.lernmodus.start("box1", SERIE)
    assert v2["befehl_id"] == v1["befehl_id"]
    assert len(box.befehle("lernen")) == 1  # kein zweiter Befehl
    with pytest.raises(TobiboxFehler) as err:
        await hub.lernmodus.start("box1", FOLGE)
    assert err.value.code == "lernmodus_laeuft"
    assert await hub.lernmodus.abbrechen("box1") is True
    v3 = await hub.lernmodus.start("box1", FOLGE)
    assert v3["befehl_id"] != v1["befehl_id"]
    assert len(box.befehle("lernen")) == 2


@pytest.mark.parametrize(
    ("ziel", "name", "code"),
    [
        ({"typ": "aktion", "aktion": "status"}, None, "ziel_ungueltig"),
        ({"typ": "serie", "serie": "ue"}, None, "ziel_ungueltig"),  # die Überraschungs-Serie ist verboten
        ({"typ": "serie", "serie": "gibtsnicht"}, None, "serie_nicht_gefunden"),
        ({"typ": "folge", "serie": "rabe", "folge": "x.mp3"}, None, "folge_nicht_gefunden"),
        ({"typ": "serie"}, None, "ziel_ungueltig"),
        (SERIE, "x" * 61, "name_ungueltig"),
        (SERIE, "   ", "name_ungueltig"),
    ],
)
async def test_start_prueft_ziel_und_name(hass, lern, ziel, name, code):
    hub, box = lern
    with pytest.raises(TobiboxFehler) as err:
        await hub.lernmodus.start("box1", ziel, name)
    assert err.value.code == code
    assert box.befehle() == []


async def test_start_box_unbekannt_offline_und_ohne_broker(hass, lern, box_fabrik):
    hub, box = lern
    with pytest.raises(TobiboxFehler) as err:
        await hub.lernmodus.start("box9", SERIE)
    assert err.value.code == "box_unbekannt"
    with pytest.raises(TobiboxFehler) as err:  # box2 hat noch nie etwas gemeldet: online=null gilt als offline
        await hub.lernmodus.start("box2", SERIE)
    assert err.value.code == "box_offline"
    with patch.object(ha_mqtt, "is_connected", return_value=False), pytest.raises(TobiboxFehler) as err:
        await hub.lernmodus.start("box1", SERIE)
    assert err.value.code == "mqtt_nicht_verbunden"
    hub.store.zustand = "leer_neu"
    with pytest.raises(TobiboxFehler) as err:
        await hub.lernmodus.start("box1", SERIE)
    assert err.value.code == "konfig_nicht_bereit"


# --- erfolgreiche Zuordnung: erst Konfiguration, dann ack ---


async def test_unbekannter_tobie_wird_zugeordnet_erst_config_dann_ack(hass, lern, ereignisse):
    hub, box = lern
    await box.unbekannt(UID)  # liegt schon als "Neuer Tobie" in der Liste
    assert UID in hub.store.neue_tobies
    v = await hub.lernmodus.start("box1", FOLGE, "Rabe aus Holz")
    meldung = await melde_gelernt(box, v, zuletzt="2026-11-09T10:05:00.500Z")
    # Vertrag W 12.11., angelegt_am: Anlegen setzt den Zeitstempel
    assert hub.store.konfig["zuordnungen"][UID] == {"ziel": FOLGE, "name": "Rabe aus Holz", "angelegt_am": ANY}
    assert hub.store.konfig["zuordnungen"][UID]["angelegt_am"].endswith("Z")
    assert hub.store.konfig["revision"] == 2
    ack = box.acks(UID)[-1]
    assert ack["grund"] == "zugeordnet" and ack["zuletzt"] == meldung["zuletzt"] and ack["art"] == "gelernt"
    themen = box.reihenfolge()
    letzte_config = max(i for i, t in enumerate(themen) if t == "tobibox/config")
    letztes_ack = max(i for i, t in enumerate(themen) if t == f"tobibox/box1/unknown/{UID}/ack")
    assert letzte_config < letztes_ack  # Entscheidung H: erst die Konfiguration (PUBACK), danach das ack
    assert box.konfigs()[-1]["zuordnungen"][UID]["ziel"] == FOLGE
    assert UID not in hub.store.neue_tobies  # aus "Neue Tobies" entfernt
    assert any(e["thema"] == "neue_tobies" and e["art"] == "entfernt" and e["daten"] == {"uid": UID, "grund": "zugeordnet"} for e in ereignisse)
    assert zustaende(ereignisse) == ["wartet", "zugeordnet"]
    assert hub.box_objekt("box1")["lernmodus"] is None  # ein beendeter Vorgang verschwindet aus boxen/list
    assert hub.store.lern_verlauf[-1]["befehl_id"] == v["befehl_id"]
    assert hub.store.lern_verlauf[-1]["ergebnis"] == "zugeordnet"


async def test_ohne_puback_kein_ack_und_nachholen_beim_wiederverbinden(hass, lern, ereignisse):
    hub, box = lern
    v = await hub.lernmodus.start("box1", SERIE)
    with patch.object(ha_mqtt, "is_connected", return_value=False):
        await melde_gelernt(box, v)
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == SERIE  # gespeichert
    assert box.acks(UID) == []  # ohne PUBACK kein ack
    assert hub.box_objekt("box1")["lernmodus"]["zustand"] == "wartet"
    async_dispatcher_send(hass, ha_mqtt.MQTT_CONNECTION_STATE, True)
    await warte_auf(hass, lambda: len(box.acks(UID)) == 1)
    assert box.acks(UID)[0]["grund"] == "zugeordnet"
    themen = box.reihenfolge()
    assert max(i for i, t in enumerate(themen) if t == "tobibox/config") < themen.index(f"tobibox/box1/unknown/{UID}/ack")
    assert zustaende(ereignisse)[-1] == "zugeordnet"


async def test_ohne_puback_bis_zur_frist_wird_abgelehnt(hass, lern, freezer, ereignisse):
    hub, box = lern
    v = await hub.lernmodus.start("box1", SERIE)
    with patch.object(ha_mqtt, "is_connected", return_value=False):
        await melde_gelernt(box, v)
        await zeit_vergeht(hass, freezer, 181)
    assert zustaende(ereignisse)[-1] == "abgelehnt"
    assert lernmodus_ereignisse(ereignisse)[-1]["grund"] == "abgelaufen"


# --- gleiches Ziel, Rückfrage ---


async def test_gleiches_ziel_keine_neue_revision_ack_abgelehnt(hass, lern, ereignisse):
    hub, box = lern
    await hub.zuordnung_setzen(UID, SERIE, name="Rabe")
    revision = hub.store.konfig["revision"]
    v = await hub.lernmodus.start("box1", SERIE, "Rabe")
    await melde_gelernt(box, v)
    assert hub.store.konfig["revision"] == revision
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"  # die Box spielt das (gleiche) Ziel ohne 10 s Stille
    letzte = lernmodus_ereignisse(ereignisse)[-1]
    assert (letzte["zustand"], letzte["grund"], letzte["text"]) == ("zugeordnet", "unveraendert", "Der Tobie hat dieses Ziel schon.")


async def test_rueckfrage_bei_anderem_ziel_mit_benachrichtigung(hass, lern, ereignisse, freezer):
    hub, box = lern
    await hub.zuordnung_setzen(UID, FOLGE, name="Rabe aus Holz")
    revision = hub.store.konfig["revision"]
    v = await hub.lernmodus.start("box1", SERIE)
    anzahl_config = len(box.konfigs())
    await melde_gelernt(box, v)
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert d["zustand"] == "rueckfrage"
    assert d["uid"] == UID and d["bisher"] == FOLGE and d["ziel"] == SERIE and d["befehl_id"] == v["befehl_id"]
    # rueckfrage_bis = das spätere von frist_bis und Eingang der Meldung + 60 s
    frist = dt_util.parse_datetime(v["frist_bis"])
    assert dt_util.parse_datetime(d["rueckfrage_bis"]) == frist  # früh gemeldet: die Frist des Vorgangs (180 s) ist später als Meldung + 60 s
    meldungen = persistent_notification._async_get_or_create_notifications(hass)
    nid = f"tobibox_rueckfrage_{v['befehl_id']}"
    assert nid in meldungen
    assert "Rabe aus Holz" in meldungen[nid]["message"] and "Der kleine Rabe" in meldungen[nid]["message"]
    assert len(box.konfigs()) == anzahl_config and box.acks(UID) == []  # noch nichts geändert
    assert hub.box_objekt("box1")["lernmodus"]["zustand"] == "rueckfrage"
    antwort = await hub.lernmodus.antwort(v["befehl_id"], True)
    assert antwort["zustand"] == "zugeordnet"
    assert antwort["konfig"]["revision"] == revision + 1
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == SERIE
    assert hub.store.konfig["zuordnungen"][UID]["name"] == "Rabe aus Holz"  # der Name bleibt
    assert box.acks(UID)[-1]["grund"] == "zugeordnet"
    themen = box.reihenfolge()
    assert max(i for i, t in enumerate(themen) if t == "tobibox/config") < max(i for i, t in enumerate(themen) if t.endswith("/ack"))
    assert nid not in persistent_notification._async_get_or_create_notifications(hass)  # beantwortet: weg
    with pytest.raises(TobiboxFehler) as err:  # eine zweite Antwort
        await hub.lernmodus.antwort(v["befehl_id"], True)
    assert err.value.code == "kein_lernmodus"


async def test_rueckfrage_frist_ist_mindestens_60_sekunden_nach_der_meldung(hass, lern, ereignisse, freezer):
    hub, box = lern
    await hub.zuordnung_setzen(UID, FOLGE)
    v = await hub.lernmodus.start("box1", SERIE)
    await box.status(lernmodus=True)
    freezer.tick(timedelta(seconds=150))  # die Meldung kommt spät, nahe an frist_bis (180 s)
    await melde_gelernt(box, v)
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert d["zustand"] == "rueckfrage"
    beginn = dt_util.parse_datetime(v["beginn"])
    assert dt_util.parse_datetime(d["rueckfrage_bis"]) - beginn >= timedelta(seconds=209)  # 150 s + 60 s
    assert dt_util.parse_datetime(d["rueckfrage_bis"]) > dt_util.parse_datetime(v["frist_bis"])


async def test_rueckfrage_nein_aendert_nichts(hass, lern, ereignisse):
    hub, box = lern
    await hub.zuordnung_setzen(UID, FOLGE)
    revision = hub.store.konfig["revision"]
    v = await hub.lernmodus.start("box1", SERIE)
    await melde_gelernt(box, v)
    antwort = await hub.lernmodus.antwort(v["befehl_id"], False)
    assert antwort["zustand"] == "abgelehnt"
    assert hub.store.konfig["revision"] == revision and hub.store.konfig["zuordnungen"][UID]["ziel"] == FOLGE
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert (d["zustand"], d["grund"]) == ("abgelehnt", "nutzer")


async def test_rueckfrage_ohne_antwort_lehnt_nach_der_frist_ab(hass, lern, ereignisse, freezer):
    hub, box = lern
    await hub.zuordnung_setzen(UID, FOLGE)
    v = await hub.lernmodus.start("box1", SERIE)
    await melde_gelernt(box, v)
    await zeit_vergeht(hass, freezer, 60 + 125)  # auch ohne offene Seite
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert (d["zustand"], d["grund"]) == ("abgelehnt", "abgelaufen")
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == FOLGE
    with pytest.raises(TobiboxFehler) as err:
        await hub.lernmodus.antwort(v["befehl_id"], True)
    assert err.value.code == "rueckfrage_abgelaufen"
    assert f"tobibox_rueckfrage_{v['befehl_id']}" not in persistent_notification._async_get_or_create_notifications(hass)


async def test_antwort_ohne_vorgang(hass, lern):
    hub, box = lern
    with pytest.raises(TobiboxFehler) as err:
        await hub.lernmodus.antwort("00000000-0000-4000-8000-000000000000", True)
    assert err.value.code == "kein_lernmodus"


async def test_aktion_ohne_seite_mit_ueberschreiben_true_antwortet_selbst(hass, lern):
    hub, box = lern
    await hub.zuordnung_setzen(UID, FOLGE)
    v = await hub.lernmodus.start("box1", SERIE, auto_ueberschreiben=True)
    await melde_gelernt(box, v)
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == SERIE
    assert box.acks(UID)[-1]["grund"] == "zugeordnet"


async def test_aktion_ohne_seite_lehnt_standardmaessig_ab(hass, lern):
    hub, box = lern
    await hub.zuordnung_setzen(UID, FOLGE)
    v = await hub.lernmodus.start("box1", SERIE, auto_ueberschreiben=False)
    await melde_gelernt(box, v)
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == FOLGE
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"


# --- abbrechen, ablaufen, späte Meldungen ---


async def test_abbrechen_sendet_immer_lernen_abbrechen_und_lehnt_spaete_meldung_ab(hass, lern, ereignisse):
    hub, box = lern
    assert await hub.lernmodus.abbrechen("box1") is False  # kein offener Vorgang
    assert [c["befehl"] for c in box.befehle()] == ["lernen_abbrechen"]  # wird trotzdem gesendet
    v = await hub.lernmodus.start("box1", SERIE)
    assert await hub.lernmodus.abbrechen("box1") is True
    assert zustaende(ereignisse)[-1] == "abgebrochen"
    revision = hub.store.konfig["revision"]
    await melde_gelernt(box, v)
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"
    assert hub.store.konfig["revision"] == revision


async def test_abbrechen_mit_offener_rueckfrage_sendet_ack_sofort(hass, lern):
    hub, box = lern
    await hub.zuordnung_setzen(UID, FOLGE)
    v = await hub.lernmodus.start("box1", SERIE)
    await melde_gelernt(box, v)
    assert box.acks(UID) == []
    await hub.lernmodus.abbrechen("box1")
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"  # W-24: die Box wartet nicht auf die Frist
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == FOLGE


async def test_abbrechen_fehler(hass, lern):
    hub, box = lern
    with pytest.raises(TobiboxFehler) as err:
        await hub.lernmodus.abbrechen("box9")
    assert err.value.code == "box_unbekannt"
    with patch.object(ha_mqtt, "is_connected", return_value=False), pytest.raises(TobiboxFehler) as err:
        await hub.lernmodus.abbrechen("box1")
    assert err.value.code == "mqtt_nicht_verbunden"
    await box_offline(box)
    await hub.lernmodus.abbrechen("box1")  # kein box_offline: der Abbruch geht auch an eine Box, die nicht antwortet


async def box_offline(box):
    await box.online(False)


async def test_ohne_status_mit_lernmodus_nach_30_sekunden_abgelaufen(hass, lern, ereignisse, freezer):
    hub, box = lern
    await hub.lernmodus.start("box1", SERIE)
    await zeit_vergeht(hass, freezer, 31)
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert (d["zustand"], d["grund"]) == ("abgelaufen", "kein_status")
    assert hub.box_objekt("box1")["lernmodus"] is None


async def test_status_lernmodus_true_haelt_den_vorgang_bis_zur_frist(hass, lern, ereignisse, freezer):
    hub, box = lern
    await hub.lernmodus.start("box1", SERIE)
    await box.status(lernmodus=True)
    await zeit_vergeht(hass, freezer, 31)
    assert zustaende(ereignisse) == ["wartet"]  # lebt weiter
    await zeit_vergeht(hass, freezer, 160)
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert (d["zustand"], d["grund"]) == ("abgelaufen", "frist")


async def test_box_beendet_den_lernmodus_abgelaufen_und_spaete_meldung_wird_trotzdem_angenommen(hass, lern, ereignisse):
    hub, box = lern
    v = await hub.lernmodus.start("box1", SERIE)
    await box.status(lernmodus=True)
    await box.status(lernmodus=False)
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert (d["zustand"], d["grund"]) == ("abgelaufen", "box_beendet")
    # Funkstörung / Statusreihenfolge: die Meldung kommt nach dem Status, aber vor frist_bis
    await melde_gelernt(box, v)
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == SERIE
    assert box.acks(UID)[-1]["grund"] == "zugeordnet"
    assert zustaende(ereignisse)[-1] == "zugeordnet"


async def test_meldung_nach_der_frist_wird_abgelehnt(hass, lern, freezer):
    hub, box = lern
    v = await hub.lernmodus.start("box1", SERIE)
    await zeit_vergeht(hass, freezer, 181)
    revision = hub.store.konfig["revision"]
    await melde_gelernt(box, v)
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"
    assert hub.store.konfig["revision"] == revision
    assert UID not in hub.store.konfig["zuordnungen"]


async def test_unbekannter_befehl_wird_abgelehnt(hass, lern):
    hub, box = lern
    await box.unbekannt(UID, art="gelernt", befehl_id="00000000-0000-4000-8000-000000000001")
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"
    assert UID not in hub.store.konfig["zuordnungen"]


async def test_box_lehnt_den_befehl_ab(hass, lern, ereignisse):
    hub, box = lern
    v = await hub.lernmodus.start("box1", SERIE)
    await box.ereignis("befehl_abgelehnt", {"befehl": "lernen", "befehl_id": v["befehl_id"], "grund": "zeit_unsicher"})
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert (d["zustand"], d["grund"]) == ("box_lehnt_ab", "zeit_unsicher")
    assert "Uhr" in d["text"]
    assert hub.box_objekt("box1")["lernmodus"] is None
    v2 = await hub.lernmodus.start("box1", SERIE)  # ein erneuter Start erzeugt einen neuen Befehl
    assert v2["befehl_id"] != v["befehl_id"]


# --- Fehlerwege (W-07 c) ---


@pytest.mark.parametrize(
    ("grund", "patch_ziel", "wirkung"),
    [
        ("konfig_zu_gross", "custom_components.tobibox.store.konfig_groesse", {"return_value": 10**9}),
        ("speicherfehler", "custom_components.tobibox.store.TobiboxStore.async_speichern", {"side_effect": OSError("voll")}),
    ],
)
async def test_fehlerwege_ack_abgelehnt_nichts_geaendert(hass, lern, ereignisse, grund, patch_ziel, wirkung):
    hub, box = lern
    v = await hub.lernmodus.start("box1", SERIE)
    revision = hub.store.konfig["revision"]
    with patch(patch_ziel, **wirkung):
        await melde_gelernt(box, v)
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"
    assert hub.store.konfig["revision"] == revision and UID not in hub.store.konfig["zuordnungen"]
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert (d["zustand"], d["grund"]) == ("abgelehnt", grund)


async def test_ziel_fehlt_inzwischen(hass, lern, ereignisse):
    hub, box = lern
    v = await hub.lernmodus.start("box1", FOLGE)
    await hub.medien.folge_loeschen("rabe", "a.mp3", True, None)
    await melde_gelernt(box, v)
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"
    d = lernmodus_ereignisse(ereignisse)[-1]
    assert (d["zustand"], d["grund"]) == ("abgelehnt", "ziel_fehlt")


async def test_konfig_nicht_bereit_bei_der_meldung(hass, lern, ereignisse):
    hub, box = lern
    v = await hub.lernmodus.start("box1", SERIE)
    hub.store.zustand = "export_neuer"
    await melde_gelernt(box, v)
    assert box.acks(UID)[-1]["grund"] == "abgelehnt"
    assert lernmodus_ereignisse(ereignisse)[-1]["grund"] == "konfig_nicht_bereit"


# --- nach einem Neustart von HA (W-08) ---


async def test_wiederholte_zustellung_nach_neustart_wiederholt_das_ack(hass, lern):
    hub, box = lern
    v = await hub.lernmodus.start("box1", SERIE)
    meldung = await melde_gelernt(box, v)
    assert box.acks(UID)[-1]["grund"] == "zugeordnet"
    # HA-Neustart: der Vorgang im Arbeitsspeicher ist weg, der Verlauf im HA-Speicher bleibt
    hub.lernmodus.beendet.clear()
    hub.lernmodus.vorgaenge.clear()
    hub.store.veroeffentlicht_stand = None  # und die letzte Veröffentlichung ist nicht bestätigt
    anzahl_config = len(box.konfigs())
    await box.unbekannt(UID, art="gelernt", befehl_id=v["befehl_id"], zuletzt=meldung["zuletzt"])
    assert len(box.acks(UID)) == 2 and box.acks(UID)[-1]["grund"] == "zugeordnet"
    assert len(box.konfigs()) == anzahl_config + 1  # erst sicherstellen, dass die Konfiguration veröffentlicht ist
    themen = box.reihenfolge()
    assert themen[-2] == "tobibox/config" and themen[-1].endswith("/ack")


async def test_wiederholte_zustellung_nach_neustart_abgelehnt_bleibt_abgelehnt(hass, lern):
    hub, box = lern
    await hub.zuordnung_setzen(UID, FOLGE)
    v = await hub.lernmodus.start("box1", SERIE)
    meldung = await melde_gelernt(box, v)
    await hub.lernmodus.antwort(v["befehl_id"], False)
    hub.lernmodus.beendet.clear()
    await box.unbekannt(UID, art="gelernt", befehl_id=v["befehl_id"], zuletzt=meldung["zuletzt"])
    assert [a["grund"] for a in box.acks(UID)] == ["abgelehnt", "abgelehnt"]
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == FOLGE


async def test_verlauf_haelt_die_letzten_20(hass, lern):
    hub, box = lern
    for i in range(23):
        v = await hub.lernmodus.start("box1", SERIE)
        await hub.lernmodus.abbrechen("box1")
        del v
    assert len(hub.store.lern_verlauf) == 20
    assert all(e["ergebnis"] == "abgebrochen" for e in hub.store.lern_verlauf)


# --- K6 (13.11.): ``vorher`` beim Umhängen über den Lernmodus ---


async def test_k6_lernmodus_neu_ohne_vorher_umhaengen_mit_vorher(hass, lern):
    hub, box = lern
    v = await hub.lernmodus.start("box1", FOLGE, "Rabe aus Holz")
    await melde_gelernt(box, v)
    assert UID not in hub.store.vorher  # neu angelegt: kein ``vorher``
    v2 = await hub.lernmodus.start("box1", SERIE)
    await melde_gelernt(box, v2)
    await hub.lernmodus.antwort(v2["befehl_id"], True)  # umhängen
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == SERIE
    assert hub.store.vorher[UID]["ziel"] == FOLGE and hub.store.vorher[UID]["am"].endswith("Z")
    assert "vorher" not in hub.store.konfig["zuordnungen"][UID] and "vorher" not in box.konfigs()[-1]["zuordnungen"][UID]
    erg = await hub.zuordnung_liste(None, 100, 0, UID)
    assert erg["zuordnungen"][0]["vorher"]["ziel"] == FOLGE
    # zurückstellen: der Lernmodus mit dem alten Ziel hebt ``vorher`` wieder auf
    v3 = await hub.lernmodus.start("box1", FOLGE)
    await melde_gelernt(box, v3)
    await hub.lernmodus.antwort(v3["befehl_id"], True)
    assert UID not in hub.store.vorher
