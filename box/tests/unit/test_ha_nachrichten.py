"""``ha`` ohne Netz: Verbinden, Befehle, Bestätigungen, Status, Discovery (Klient ohne Broker)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fixtures.ha_fake import UID, Aufbau, FakeKlient, cmd

from tobibox import events as ev
from tobibox.ha import STATUS_ALLE_S, STATUS_MIN_ABSTAND_S, baue_discovery, optionen

ERZEUGT = datetime(2026, 11, 5, 9, 11, 50, tzinfo=timezone.utc).timestamp()  # "2026-11-05T09:11:50Z"
CMD = "tobibox/box1/cmd"
EVENT = "tobibox/box1/event"
ACK = f"tobibox/box1/unknown/{UID}/ack"
UNKNOWN = f"tobibox/box1/unknown/{UID}"


@pytest.fixture
async def box(tmp_path):
    a = await Aufbau(tmp_path / "z").start()
    yield a
    await a.stop()


def events(box: Aufbau, art: str | None = None) -> list[dict]:
    return [e for e in box.klient.json_auf(EVENT) if art is None or e["art"] == art]


def jetzt_iso(box: Aufbau) -> str:
    from tobibox.outbox import zeitstempel

    return zeitstempel(box.uhr.wall).replace(".000Z", "Z")


# --- Verbinden (4.4) ------------------------------------------------------------------------


async def test_reihenfolge_beim_verbinden(tmp_path):
    a = Aufbau(tmp_path / "z")
    a.outbox.melden("unbekannt", UID, None, a.uhr.jetzt())
    await a.start()
    k = a.klient
    assert k.abonniert == [[("tobibox/config", 1), (CMD, 1), (f"tobibox/box1/unknown/+/ack", 1), ("homeassistant/status", 1)]]
    themen = [t for t, _, _ in k.gesendet]
    assert themen[0] == "tobibox/box1/online"  # 3. online
    assert k.gesendet[0][1:] == (b"online", True)
    erste_disc = next(i for i, t in enumerate(themen) if t.startswith("homeassistant/"))
    status = themen.index("tobibox/box1/status")
    unknown = themen.index(UNKNOWN)
    assert 0 < erste_disc < status < unknown  # 4. Discovery und Status, 5. offene Einträge
    assert a.typen(ev.HaVerbindung) == [ev.HaVerbindung(True)]
    await a.stop()


async def test_nichts_wird_vor_dem_abonnieren_gesendet(tmp_path):
    k = FakeKlient(auto_abonniert=False)
    a = await Aufbau(tmp_path / "z", klient=k).start()
    assert k.gesendet == []  # SUBACK fehlt noch
    k.bei_abonniert()
    await a.ha.leere()
    assert k.gesendet and k.gesendet[0][0] == "tobibox/box1/online"
    await a.stop()


async def test_verbindung_weg_und_wieder_da(box):
    box.klient.trenne()
    await box.ha.leere()
    assert box.typen(ev.HaVerbindung) == [ev.HaVerbindung(True), ev.HaVerbindung(False)]
    n = len(box.klient.gesendet)
    box.ha.tick()
    assert len(box.klient.gesendet) == n  # ohne Verbindung wird nichts versucht
    await box.verbinde()
    assert box.typen(ev.HaVerbindung)[-1] == ev.HaVerbindung(True)
    assert len(box.klient.auf("tobibox/box1/online")) == 2  # Birth bei jedem Verbinden
    assert len(box.klient.json_auf("tobibox/box1/status")) == 2


async def test_sauberes_beenden_veroeffentlicht_offline(tmp_path):
    a = await Aufbau(tmp_path / "z").start()
    await a.stop()
    assert a.klient.auf("tobibox/box1/online")[-1] == (b"offline", True)
    assert a.klient.gestoppt


async def test_homeassistant_status_online_veroeffentlicht_discovery_erneut(box):
    n = len([t for t, _, _ in box.klient.gesendet if t.startswith("homeassistant/")])
    await box.sende("homeassistant/status", b"online")
    mehr = len([t for t, _, _ in box.klient.gesendet if t.startswith("homeassistant/")])
    assert mehr == 2 * n
    await box.sende("homeassistant/status", b"offline")
    assert len([t for t, _, _ in box.klient.gesendet if t.startswith("homeassistant/")]) == mehr


# --- Befehle (3.7) --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "befehl,klasse",
    [("lernen", ev.HaLernmodus), ("lernen_abbrechen", ev.HaLernmodusAbbruch), ("sync", ev.HaSyncAnstossen)],
)
async def test_befehl_wird_zum_ereignis_mit_ablaufzeit(box, befehl, klasse):
    await box.sende(CMD, cmd(befehl, erzeugt="2026-11-05T09:11:50Z", ttl_s=60))
    (e,) = box.typen(klasse)
    assert e.befehl_id == "6f1c0a7e-3b52-4d1a-9c58-0e2b7a41d9f3"
    assert e.gueltig_bis == ERZEUGT + 60  # erzeugt + ttl_s als UTC-Sekunden


async def test_update_traegt_die_version(box):
    await box.sende(CMD, cmd("update", daten={"version": "1.2.0"}, erzeugt="2026-11-05T09:11:50Z", ttl_s=300))
    (e,) = box.typen(ev.HaUpdateAnstossen)
    assert (e.version, e.gueltig_bis) == ("1.2.0", ERZEUGT + 300)


@pytest.mark.parametrize("daten", [{}, {"version": "1.2"}, {"version": "v1.2.0"}, {"version": 3}, "x"])
async def test_update_mit_ungueltiger_version_wird_abgelehnt(box, daten):
    await box.sende(CMD, cmd("update", daten=daten))
    assert box.typen(ev.HaUpdateAnstossen) == []
    (m,) = events(box, "befehl_abgelehnt")
    assert m["daten"]["befehl"] == "update" and m["daten"]["grund"] == "bedingung" and m["daten"]["detail"]


async def test_abgelaufener_befehl_wird_unveraendert_an_den_kern_gegeben(box):
    """Die Ablaufzeit prüft der Kern (``learn``, ``idle``), nicht ``ha`` (core-interface 9.9)."""
    await box.sende(CMD, cmd("sync", erzeugt="2020-01-01T00:00:00Z", ttl_s=1))
    (e,) = box.typen(ev.HaSyncAnstossen)
    assert e.gueltig_bis < box.uhr.wall
    assert events(box) == []  # keine Meldung an HA für abgelaufene Befehle


async def test_doppelte_id_wirkt_einmal(box):
    for _ in range(3):
        await box.sende(CMD, cmd("sync"))
    assert len(box.typen(ev.HaSyncAnstossen)) == 1
    await box.sende(CMD, cmd("sync", id="eine-andere-id"))
    assert len(box.typen(ev.HaSyncAnstossen)) == 2


async def test_es_werden_die_letzten_50_ids_gemerkt(box):
    for i in range(51):
        await box.sende(CMD, cmd("sync", id=f"id-{i}"))
    await box.sende(CMD, cmd("sync", id="id-50"))  # noch gemerkt
    assert len(box.typen(ev.HaSyncAnstossen)) == 51
    await box.sende(CMD, cmd("sync", id="id-0"))  # herausgefallen
    assert len(box.typen(ev.HaSyncAnstossen)) == 52


async def test_unbekannter_befehl_gibt_fehler_und_keinen_kern_befehl(box):
    await box.sende(CMD, cmd("neustart"))
    (m,) = events(box, "fehler")
    assert m["daten"]["code"] == "befehl_unbekannt" and m["daten"]["baustein"] == "ha"
    assert not [e for e in box.ereignisse if isinstance(e, (ev.HaLernmodus, ev.HaSyncAnstossen))]


async def test_groesseres_v_wird_verworfen_und_gemeldet(box):
    await box.sende(CMD, cmd("sync", v=2))
    assert box.typen(ev.HaSyncAnstossen) == []
    assert [m["daten"]["code"] for m in events(box, "fehler")] == ["v_unbekannt"]


@pytest.mark.parametrize(
    "nutzlast",
    [b"kein json", b"[]", cmd("sync", v="1"), {k: v for k, v in cmd("sync").items() if k != "v"}, cmd("sync", ttl_s=0),
     cmd("sync", ttl_s=3601), cmd("sync", ttl_s=True), cmd("sync", erzeugt="gestern"), cmd("sync", id=""), cmd("sync", id=5)],
)
async def test_ungueltige_befehle_werden_verworfen(box, nutzlast):
    await box.sende(CMD, nutzlast)
    assert box.typen(ev.HaSyncAnstossen) == []
    assert events(box, "fehler")


async def test_zu_grosser_befehl_wird_verworfen(box):
    await box.sende(CMD, cmd("sync", daten={"x": "a" * 70000}))
    assert box.typen(ev.HaSyncAnstossen) == []
    assert events(box, "fehler")[0]["daten"]["code"] == "nachricht_zu_gross"


async def test_ereignis_senden_des_kerns_geht_auf_event(box):
    box.ha.fuehre_aus(ev.EreignisSenden("befehl_abgelehnt", {"befehl": "sync", "befehl_id": "b1", "grund": "zeit_unsicher"}))
    box.ha.fuehre_aus(ev.EreignisSenden("fehler", {"code": "x"}))
    a, f = events(box)
    assert a["art"] == "befehl_abgelehnt" and a["daten"] == {"befehl": "sync", "befehl_id": "b1", "grund": "zeit_unsicher"}
    assert f["daten"] == {"code": "x", "baustein": "kern", "text": ""}
    assert a["id"] != f["id"] and a["v"] == 1
    assert all(r is False for _, r in box.klient.auf(EVENT))  # nicht dauerhaft


# --- Unbekannte Kennungen und Bestätigung (3.5, 3.6, 4.1) -------------------------------------


def melde(box: Aufbau, art="unbekannt", uid=UID, befehl_id=None) -> ev.Eintrag:
    e = box.outbox.melden(art, uid, befehl_id, box.uhr.jetzt())
    box.ha.melde(e)
    return e


def ack(e: ev.Eintrag, grund="neu", **ueber) -> dict:
    return {"v": 1, "ts": "2026-11-05T09:12:05Z", "zuletzt": e.zuletzt, "art": e.art, "grund": grund, **ueber}


async def test_unbekannte_kennung_wird_dauerhaft_je_kennung_veroeffentlicht(box):
    e = melde(box)
    (n,) = box.klient.json_auf(UNKNOWN)
    assert box.klient.auf(UNKNOWN)[0][1] is True  # retained
    assert n == {"v": 1, "uid": UID, "art": "unbekannt", "zuerst": e.zuerst, "zuletzt": e.zuletzt, "anzahl": 1,
                 "zeit_ok": True, "befehl_id": None}
    melde(box, uid="04ffeedd")
    assert len(box.klient.json_auf("tobibox/box1/unknown/04ffeedd")) == 1  # eigenes Thema je Kennung


async def test_gleiche_kennung_ueberschreibt_mit_neuer_zaehlung(box):
    melde(box)
    box.uhr.vor(1)
    e2 = melde(box)
    n = box.klient.json_auf(UNKNOWN)
    assert [x["anzahl"] for x in n] == [1, 2] and n[1]["zuletzt"] == e2.zuletzt


async def test_ohne_verbindung_bleibt_der_eintrag_und_wird_beim_verbinden_veroeffentlicht(tmp_path):
    a = await Aufbau(tmp_path / "z").start(verbunden=False)
    e = melde(a)
    assert a.klient.json_auf(UNKNOWN) == []
    assert a.outbox.offen() == [e]
    await a.verbinde()
    assert len(a.klient.json_auf(UNKNOWN)) == 1
    await a.stop()


async def test_ack_loescht_erst_die_dauerhafte_nachricht_dann_den_eintrag(box):
    box.klient.auto_puback = False
    e = melde(box)
    await box.sende(ACK, ack(e))
    assert box.klient.auf(UNKNOWN)[-1] == (b"", True)  # leere dauerhafte Nachricht
    assert box.outbox.offen() == [e]  # PUBACK der Löschung fehlt noch: der Eintrag bleibt
    assert box.typen(ev.Bestaetigt) == []
    box.klient.puback(box.klient.mid)  # PUBACK des Löschens
    await box.ha.leere()
    assert box.outbox.offen() == []
    (b,) = box.typen(ev.Bestaetigt)
    assert (b.id, b.grund, b.zuletzt, b.art) == (UID, "neu", e.zuletzt, "unbekannt")
    assert box.bestaetigt_angenommen == [True]


async def test_der_puback_der_meldung_loescht_nichts(box):
    """Der Broker hat die Nachricht angenommen, HA hat nicht bestätigt: der Eintrag bleibt (Abnahme AP 3.3)."""
    e = melde(box)  # auto_puback: der Broker bestätigt die Veröffentlichung sofort
    await box.ha.leere()
    assert box.outbox.offen() == [e] and box.typen(ev.Bestaetigt) == []


@pytest.mark.parametrize("grund", ["neu", "bekannt", "zugeordnet", "abgelehnt", "etwas-neues"])
async def test_jeder_grund_loescht_bei_passendem_zuletzt(box, grund):
    e = melde(box, "gelernt", befehl_id="b1")
    await box.sende(ACK, ack(e, grund))
    assert box.outbox.offen() == []
    assert box.typen(ev.Bestaetigt)[0].grund == (grund if grund != "etwas-neues" else "etwas-neues")


async def test_veraltete_bestaetigung_laesst_alles_stehen(box):
    alt = melde(box)
    box.uhr.vor(1)
    neu = melde(box, "gelernt", befehl_id="b1")  # überschreibt: andere Zeit, andere Art
    await box.sende(ACK, ack(alt))
    assert box.outbox.offen() == [neu]
    assert box.klient.auf(UNKNOWN)[-1][0] != b""  # die neuere dauerhafte Nachricht bleibt
    assert box.bestaetigt_angenommen == [False]  # ``outbox`` hat sie als veraltet verworfen
    await box.sende(ACK, ack(neu, "zugeordnet"))
    assert box.outbox.offen() == []


async def test_ack_mit_falscher_art_oder_ohne_zuletzt_loescht_nichts(box):
    e = melde(box)
    await box.sende(ACK, ack(e, art="gelernt"))
    await box.sende(ACK, {k: v for k, v in ack(e).items() if k != "zuletzt"})
    assert box.outbox.offen() == [e]
    assert b"" not in [n for n, _ in box.klient.auf(UNKNOWN)]  # keine Löschung veröffentlicht


async def test_ack_fuer_unbekannte_kennung_ist_wirkungslos(box):
    e = melde(box)
    await box.sende("tobibox/box1/unknown/04aaaaaa/ack", ack(e))
    assert box.outbox.offen() == [e]


async def test_doppelte_bestaetigung_loescht_nur_einmal(box):
    box.klient.auto_puback = False
    e = melde(box)
    await box.sende(ACK, ack(e))
    await box.sende(ACK, ack(e))  # QoS 1: zweite Zustellung, bevor der PUBACK der Löschung da ist
    assert len([n for n, _ in box.klient.auf(UNKNOWN) if n == b""]) == 1
    box.klient.puback(box.klient.mid)
    await box.ha.leere()
    await box.sende(ACK, ack(e))  # und danach noch einmal
    assert len(box.typen(ev.Bestaetigt)) == 2  # die späte geht an ``outbox``, die sie als unbekannt verwirft
    assert box.bestaetigt_angenommen == [True, False]


async def test_eintrag_aendert_sich_waehrend_die_loeschung_laeuft(box):
    """Der Eintrag bleibt und seine dauerhafte Nachricht kommt zurück (4.1, Schritt 4; core-interface 7)."""
    box.klient.auto_puback = False
    e = melde(box)
    await box.sende(ACK, ack(e))
    box.uhr.vor(1)
    neu = melde(box)  # die Box meldet dieselbe Kennung erneut, bevor die Löschung bestätigt ist
    mid = box.klient.mid
    box.klient.puback(mid)
    await box.ha.leere()
    assert box.typen(ev.Bestaetigt) == []
    assert box.outbox.offen() == [neu]
    assert box.klient.json_auf(UNKNOWN)[-1]["zuletzt"] == neu.zuletzt  # wieder veröffentlicht


async def test_ack_wird_nicht_dauerhaft_erwartet_und_leere_nutzlast_ist_keine_bestaetigung(box):
    e = melde(box)
    await box.sende(ACK, b"")
    assert box.outbox.offen() == [e] and events(box, "fehler")


# --- Status (3.3, core-interface 12) -----------------------------------------------------------


def stati(box: Aufbau) -> list[dict]:
    return box.klient.json_auf("tobibox/box1/status")


async def test_status_nach_dem_verbinden_dauerhaft_mit_freiem_speicher(box):
    (s,) = stati(box)
    assert box.klient.auf("tobibox/box1/status")[0][1] is True
    assert s["v"] == 1 and s["speicher_frei_mb"] == 4096 and s["netz"] == "offline" and s["akku_prozent"] is None
    assert set(s) >= {"ts", "zustand", "lernmodus", "serie", "akku_prozent", "lader", "netz", "sync", "speicher_frei_mb",
                      "version", "firmware", "protokoll", "leser", "letzter_fehler", "zeitquelle", "zeit_ok", "konfig", "update"}
    assert s["konfig"] == {"revision": 0, "liste_id": ""}


async def test_status_bei_aenderung_hoechstens_alle_5_s(box):
    box.status.beobachte(ev.AkkuStand(76), box.uhr.jetzt())
    box.ha.tick()
    assert len(stati(box)) == 1  # zu früh: zusammengefasst
    box.uhr.vor(STATUS_MIN_ABSTAND_S - 0.5)
    box.status.beobachte(ev.NetzKlasse("hotspot"), box.uhr.jetzt())
    box.ha.tick()
    assert len(stati(box)) == 1
    box.uhr.vor(0.5)
    box.ha.tick()
    s = stati(box)
    assert len(s) == 2 and s[1]["akku_prozent"] == 76 and s[1]["netz"] == "hotspot"  # beide Änderungen in einer Nachricht


async def test_status_ohne_aenderung_nur_alle_300_s_und_ts_zaehlt_nicht(box):
    box.uhr.vor(STATUS_ALLE_S - 1)  # die Wanduhr läuft, sonst ändert sich nichts
    box.ha.tick()
    assert len(stati(box)) == 1
    box.uhr.vor(1)
    box.ha.tick()
    s = stati(box)
    assert len(s) == 2 and s[1]["ts"] != s[0]["ts"]


async def test_status_folgt_sync_und_freiem_speicher(box):
    box.status.beobachte(ev.SyncGestartet(), box.uhr.jetzt())
    box.frei_mb = 100
    box.uhr.vor(STATUS_MIN_ABSTAND_S)
    box.ha.tick()
    s = stati(box)[-1]
    assert s["sync"]["zustand"] == "laeuft" and s["speicher_frei_mb"] == 100


async def test_status_meldet_konfig_nach_annahme(box):
    from fixtures.ha_fake import konfig_json

    await box.sende("tobibox/config", konfig_json(revision=17))
    box.uhr.vor(STATUS_MIN_ABSTAND_S)
    box.ha.tick()
    assert stati(box)[-1]["konfig"] == {"revision": 17, "liste_id": "a3f9c1e07b2d4856"}


# --- Discovery (6) -------------------------------------------------------------------------------


def disc(box: Aufbau) -> dict[str, dict]:
    return {t: json.loads(n) for t, n, r in box.klient.gesendet if t.startswith("homeassistant/") and r}


async def test_discovery_entitaeten_und_gemeinsame_felder(box):
    d = disc(box)
    namen = {t.split("/")[3]: t.split("/")[1] for t in d}
    assert namen == {
        "zustand": "sensor", "serie": "sensor", "akku": "sensor", "lader": "binary_sensor", "netz": "sensor",
        "sync": "sensor", "speicher_frei": "sensor", "version": "sensor", "letzter_fehler": "sensor",
        "zeitquelle": "sensor", "sync_jetzt": "button", "update": "button", "lernen_abbrechen": "button",
        "lern_serie": "select",
    }
    for t, n in d.items():
        assert t.startswith("homeassistant/") and "/tobibox_box1/" in t and t.endswith("/config")
        objekt = t.split("/")[3]
        assert n["unique_id"] == f"tobibox_box1_{objekt}" and n["has_entity_name"] is True
        assert n["availability_topic"] == "tobibox/box1/online"
        assert (n["payload_available"], n["payload_not_available"]) == ("online", "offline")
        assert n["device"]["identifiers"] == ["tobibox_box1"] and n["device"]["name"] == "Tobi Box box1"
    assert all(r for t, _, r in box.klient.gesendet if t.startswith("homeassistant/"))


async def test_discovery_stimmt_mit_den_beispielen_des_vertrags(box):
    d = disc(box)
    akku = d["homeassistant/sensor/tobibox_box1/akku/config"]
    assert (akku["name"], akku["state_topic"], akku["value_template"], akku["device_class"],
            akku["unit_of_measurement"], akku["state_class"]) == (
        "Akku", "tobibox/box1/status", "{{ value_json.akku_prozent }}", "battery", "%", "measurement")
    knopf = d["homeassistant/button/tobibox_box1/sync_jetzt/config"]
    assert (knopf["command_topic"], knopf["payload_press"]) == ("tobibox/box1/ui/sync", "PRESS")
    assert d["homeassistant/button/tobibox_box1/update/config"]["command_topic"] == "tobibox/box1/ui/update"
    assert d["homeassistant/button/tobibox_box1/lernen_abbrechen/config"]["command_topic"] == "tobibox/box1/ui/lernen_abbrechen"
    lader = d["homeassistant/binary_sensor/tobibox_box1/lader/config"]
    assert "is none" in lader["value_template"] and lader["device_class"] == "battery_charging"
    netz = d["homeassistant/sensor/tobibox_box1/netz/config"]
    assert netz["device_class"] == "enum" and netz["options"] == ["home", "hotspot", "offline"]
    zeit = d["homeassistant/sensor/tobibox_box1/zeitquelle/config"]
    assert zeit["entity_category"] == "diagnostic" and "zeit_ok" in zeit["json_attributes_template"]
    sp = d["homeassistant/sensor/tobibox_box1/speicher_frei/config"]
    assert (sp["unit_of_measurement"], sp["device_class"], sp["state_class"]) == ("MB", "data_size", "measurement")
    assert (sp["suggested_unit_of_measurement"], sp["suggested_display_precision"]) == ("GB", 0)
    sel = d["homeassistant/select/tobibox_box1/lern_serie/config"]
    assert sel["command_topic"] == "tobibox/box1/ui/lern_serie" and sel["optimistic"] is True


def test_auswahl_der_serien():
    s = lambda i, n, t="normal": ev.Serie(i, n, t, i, ())  # noqa: E731
    assert optionen([]) == ["keine Serie"]
    assert optionen([s("a", "Rabe"), s("b", "Fuchs"), s("u", "Überraschung", "ueberraschung")]) == ["Rabe", "Fuchs"]
    assert optionen([s("a", "Rabe"), s("b", "Rabe"), s("c", "Fuchs")]) == ["Rabe (a)", "Rabe (b)", "Fuchs"]


async def test_discovery_wird_erneut_veroeffentlicht_wenn_sich_die_serienliste_aendert(box):
    n = len(box.klient.auf("homeassistant/select/tobibox_box1/lern_serie/config"))
    box.serien.append(ev.Serie("s1", "Der kleine Rabe", "normal", "s1", ("a.mp3",)))
    box.ha.tick()
    sel = box.klient.json_auf("homeassistant/select/tobibox_box1/lern_serie/config")
    assert len(sel) == n + 1 and sel[-1]["options"] == ["Der kleine Rabe"]
    box.ha.tick()
    assert len(box.klient.auf("homeassistant/select/tobibox_box1/lern_serie/config")) == n + 1  # nur bei Änderung


def test_anzeigename_und_version_im_geraet():
    d = dict(baue_discovery("box2", "Küche", "1.2.0", []))
    g = d["homeassistant/sensor/tobibox_box2/zustand/config"]["device"]
    assert g["name"] == "Tobi Box Küche" and g["sw_version"] == "1.2.0" and g["identifiers"] == ["tobibox_box2"]
    assert g["manufacturer"] == "Tobi Box" and g["model"] == "NFC-Audiobox"


async def test_alle_nachrichten_sind_qos1_json_oder_text(box):
    for t, n, _ in box.klient.gesendet:
        if t.endswith("/online"):
            assert n in (b"online", b"offline")
        else:
            assert isinstance(json.loads(n), dict)


def test_themen_ack():
    from tobibox.ha import Themen

    t = Themen("box1")
    assert t.uid_aus_ack(f"tobibox/box1/unknown/{UID}/ack") == UID
    assert t.uid_aus_ack(f"tobibox/box2/unknown/{UID}/ack") is None
    assert t.uid_aus_ack("tobibox/box1/unknown/a/b/ack") is None
    assert t.uid_aus_ack(f"tobibox/box1/unknown/{UID}") is None
