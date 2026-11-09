"""``App`` in Stufe 3a (AP 3.7): Verdrahtung von ``net``, ``power``, ``sync`` und ``ha`` ohne Broker und ohne MPD.

Die Tests mit Mosquitto und rsync stehen in ``cuj/test_cuj07_ha.py``, ``cuj/test_cuj09_sync.py`` und ``cuj/test_cuj12_unterwegs.py``.
"""

from __future__ import annotations

import pytest
from fixtures.dienst import BAER, BEKANNT, NEU, baue_dienst, mqtt_abschnitt, netz_strom_abschnitt, sync_abschnitt

from tobibox import events as ev
from tobibox.clock import SimUhr
from tobibox.net import Netz, SimSsid
from tobibox.power import SimStrom
from tobibox.sync import SyncFortschritt

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def d(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt() + sync_abschnitt(1))
    await dienst.app.starte()
    yield dienst
    await dienst.app.beende()


async def test_ohne_mqtt_bleibt_der_ha_ersatz_aktiv(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch)
    a = dienst.app
    assert a.ha is None and a.ausgang.ha is None and a.netz is None and a.power is None and a.sync is None
    assert a.zeitquelle is None


async def test_mit_mqtt_gehen_meldungen_an_ha_und_nicht_an_den_ersatz(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, mqtt_abschnitt(1))
    a = dienst.app
    assert a.ha is not None and a.ausgang.ha is a.ha
    gemeldet, ersatz = [], []
    a.ha.melde = gemeldet.append
    async def ersatz_async(eintrag):
        ersatz.append(eintrag)
    a.ausgang.ha_ersatz.gelernt_async = ersatz_async
    await a.ausgang.melde_async(ev.Melden("gelernt", NEU, "b1"), a.uhr.jetzt())
    await a.ausgang.melde_async(ev.Melden("unbekannt", "04ffeede"), a.uhr.jetzt())
    assert [e.uid for e in gemeldet] == [NEU, "04ffeede"] and ersatz == []
    assert set(a.outbox.offen()[i].uid for i in range(2)) == {NEU, "04ffeede"}


async def test_netz_und_strom_teilen_sich_ein_zeitquelle_objekt(d):
    a = d.app
    assert a.netz.zeit is a.zeitquelle and a.power.zeit is a.zeitquelle
    assert a.zeitquelle.quelle == "system" and a.zeitquelle.vertrauenswuerdig  # Mac: alles ``sim``


async def test_zeitquelle_geaendert_stellt_die_uhr(tmp_path, kurz, monkeypatch):
    uhr = SimUhr()
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt(), uhr=uhr)
    await dienst.app.starte()
    try:
        assert uhr.jetzt().zeit_quelle == "system"
        await dienst.sende(ev.ZeitquelleGeaendert("unbekannt", False))
        j = uhr.jetzt()
        assert (j.zeit_quelle, j.zeit_ok) == ("unbekannt", False)
        await dienst.sende(ev.ZeitquelleGeaendert("ntp", True))
        assert (uhr.jetzt().zeit_quelle, uhr.jetzt().zeit_ok) == ("ntp", True)
        assert dienst.app.status.als_dict(uhr.jetzt(), (), None)["zeitquelle"] == "ntp"
    finally:
        await dienst.app.beende()


async def test_pi_konfiguration_startet_mit_unbekannter_uhr_bis_ntp_oder_rtc_sie_bewerten(tmp_path, kurz, monkeypatch):
    abschnitte = '[netz]\nquelle = "networkmanager"\nheim_ssid = "x"\n[strom]\nquelle = "sim"\n'
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, abschnitte)
    j = dienst.app.uhr.jetzt()
    assert (j.zeit_quelle, j.zeit_ok) == ("unbekannt", False)


async def test_sim_strom_stellt_den_treiber_und_power_meldet(d):
    a = d.app
    assert isinstance(a.power.treiber, SimStrom)
    assert (await d.sim(befehl="strom", lader=True, akku=40)) == {"ok": True}
    assert a.power.treiber._lader is True and a.power.treiber._akku == 40
    assert (a.status.lader, a.status.akku) == (True, 40)
    assert a.sync._am_lader is True and a.sync._akku == 40  # ``Sync`` hat Lader und Akku bekommen
    await d.sim(befehl="strom", akku=70)
    assert (a.status.lader, a.status.akku) == (True, 70) and a.sync._akku == 70


async def test_sim_netz_setzt_das_wlan_und_net_klassifiziert(d):
    a = d.app
    assert isinstance(a.netz._ssid, SimSsid)
    for klasse in ("home", "hotspot", "offline"):
        assert (await d.sim(befehl="netz", klasse=klasse)) == {"ok": True}
        assert a.status.netz == klasse and a.sync._netz == klasse
    assert a.netz.konfig.heim_ssid == "sim-heim" and a.netz.konfig.hotspot_ssid == "sim-hotspot"  # Vorgaben am Mac ohne eigene Namen


async def test_sim_netz_benutzt_die_namen_aus_der_konfiguration(tmp_path, kurz, monkeypatch):
    abschnitte = '[netz]\nquelle = "sim"\nheim_ssid = "Daheim"\nhotspot_ssid = "Handy"\n'
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, abschnitte)
    await dienst.app.starte()
    try:
        await dienst.sim(befehl="netz", klasse="hotspot")
        assert await dienst.app.netz._ssid.ssid() == "Handy" and dienst.app.status.netz == "hotspot"
        await dienst.sim(befehl="netz", klasse="home")
        assert await dienst.app.netz._ssid.ssid() == "Daheim" and dienst.app.status.netz == "home"
    finally:
        await dienst.app.beende()


async def test_ohne_netz_und_strom_gibt_sim_die_ereignisse_selbst_aus(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch)
    await dienst.app.starte()
    try:
        assert dienst.app.sim.strom_haken is None and dienst.app.sim.netz_haken is None
        await dienst.sim(befehl="strom", lader=False, akku=33)
        await dienst.sim(befehl="netz", klasse="hotspot")
        a = dienst.app
        assert (a.status.lader, a.status.akku, a.status.netz) == (False, 33, "hotspot")
    finally:
        await dienst.app.beende()


async def test_tiefstand_vom_simulierten_akku_bricht_den_sync_ab_befehl_geht_an_sync(d):
    a = d.app
    abgebrochen = []

    async def abbrechen(grund):
        abgebrochen.append(grund)

    a.sync.abbrechen = abbrechen
    await d.sende(ev.SyncGestartet())  # ein Sync läuft; nur dann bricht ``idle`` ihn ab
    await d.sim(befehl="strom", lader=False, akku=80)
    await d.sim(befehl="strom", akku=4)  # unter 5 %, nicht am Lader: ``AkkuTiefstand``
    await d.ruhe()
    import asyncio

    await asyncio.sleep(0.05)
    assert abgebrochen == ["akku_tiefstand"]


async def test_syncstarten_ohne_sync_abschnitt_wird_beantwortet_und_bleibt_nicht_offen(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch)
    await dienst.app.starte()
    try:
        await dienst.sende(ev.HaSyncAnstossen("b1", dienst.uhr.jetzt().wall + 60))
        await dienst.ruhe()
        assert dienst.app.status.sync["grund"] == "nicht_eingerichtet" and dienst.app.status.sync["zustand"] == "idle"
    finally:
        await dienst.app.beende()


async def test_syncfortschritt_geht_nur_an_statussammler_und_anzeige_nicht_in_den_kern(d, monkeypatch):
    a = d.app
    kern_gesehen = []
    from tobibox import core

    orig = core.step
    monkeypatch.setattr(core, "step", lambda z, e, j: kern_gesehen.append(type(e).__name__) or orig(z, e, j))
    await d.sende(ev.SyncGestartet(), SyncFortschritt(40, 2))
    assert "SyncFortschritt" not in kern_gesehen and "SyncGestartet" in kern_gesehen
    assert a.status.sync_fortschritt == {"prozent": 40, "dateien": 2}
    assert a.anzeige_auskunft()["anzeige"]["sync_fortschritt"] == {"prozent": 40, "dateien": 2}
    assert a.status_auskunft()["verbindungen"]["sync"]["fortschritt"] == {"prozent": 40, "dateien": 2}
    assert "fortschritt" not in str(a.status.als_dict(a.uhr.jetzt(), (), None))  # Status-JSON bleibt Version 1
    await d.sende(ev.SyncFertig(0, 0))
    assert a.status.sync_fortschritt is None


async def test_herunterfahren_geht_an_power_in_der_simulation_nur_protokolliert(d):
    a = d.app
    await d.sende(ev.HerunterfahrenAngefordert("hauptknopf"))  # der Kern macht daraus den Befehl ``Herunterfahren``
    await d.ruhe()
    assert a.power.treiber.heruntergefahren == ["hauptknopf"]


async def test_status_auskunft_nennt_ha_netz_akku_und_sync(d):
    await d.sim(befehl="strom", lader=True, akku=76)
    await d.sim(befehl="netz", klasse="hotspot")
    v = d.app.status_auskunft()["verbindungen"]
    assert v["ha"] == {"eingerichtet": False, "verbunden": False}
    assert v["netz"] == {"eingerichtet": True, "klasse": "hotspot"}
    assert v["strom"] == {"eingerichtet": True, "akku_prozent": 76, "lader": True}
    assert v["sync"]["eingerichtet"] is True and v["sync"]["zustand"] in ("idle", "laeuft", "fehler")


async def test_netz_aus_der_konfiguration_ist_das_modul_net(d):
    assert isinstance(d.app.netz, Netz)
