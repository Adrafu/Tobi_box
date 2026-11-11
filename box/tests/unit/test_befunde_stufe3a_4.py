"""Regressionstests zu den Befunden des Reviews ``docs/egm/software-prototyp/code_review_stufe3a_4.md`` (B1 bis B17, T1 bis T3).

Jeder Test benennt den Befund. Die echten Proben des Prüfers liegen als Vorbild hier: ``probe1.py`` (B14), ``probe2.py`` (B8),
``probe3.py`` (B1), ``test_probe_race.py`` (B7). Die Tests laufen durch die echte ``App`` (ohne MPD, Leser und Tonausgabe).
"""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from conftest import CujBox
from fixtures import stufe4
from fixtures.dienst import BAER, BEKANNT, baue_dienst, netz_strom_abschnitt, sync_abschnitt
from fixtures.stufe4 import BedienBox, wall

from tobibox import app as app_modul
from tobibox import events as ev
from tobibox import lauf, nachfuehrung, power, quiet
from tobibox import config as konfig_modul
from tobibox.app import App
from tobibox.clock import SystemUhr
from tobibox.controls import Bedienung, GpioTreiber
from tobibox.headphones import GpioKopfhoerer
from tobibox.power import HerunterfahrenFehler, PiSugarStrom, Power, SimStrom, parse_taste
from tobibox.sim import Ungueltig

pytestmark = pytest.mark.asyncio

GPIO = '[tasten]\nquelle = "gpio"\npin_vor = 5\npin_zurueck = 6\npin_dreh_a = 12\npin_dreh_b = 13\n'
GPIO_KH = '[kopfhoerer]\nquelle = "gpio"\ngpio_pin = 17\nintervall_s = 0.05\n'


class HaSpion:
    """Ersatz für ``Ha``: sammelt die ``EreignisSenden`` an HA."""

    def __init__(self) -> None:
        self.gesendet: list[ev.EreignisSenden] = []

    def fuehre_aus(self, b: ev.Befehl) -> None:
        self.gesendet.append(b)  # type: ignore[arg-type]

    def melde(self, eintrag) -> None:  # pragma: no cover - nicht gebraucht
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


@pytest.fixture
async def d(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt())
    dienst.app.ha = HaSpion()
    await dienst.app.starte()
    yield dienst
    await dienst.app.beende()


# --------------------------------------------------------------------------------------------------------------
# B1: Ein fehlgeschlagenes Herunterfahren ist nicht endgültig
# --------------------------------------------------------------------------------------------------------------


class KaputtesPoweroff(SimStrom):
    simuliert = False

    async def herunterfahren(self, grund: str) -> None:
        raise HerunterfahrenFehler("systemctl endete mit Rückgabecode 1")


async def test_b1_pisugar_rueckgabecode_ungleich_null_ist_ein_fehler(tmp_path):
    t = PiSugarStrom("127.0.0.1", 1, ("sh", "-c", "exit 3"))
    with pytest.raises(HerunterfahrenFehler, match="Rückgabecode 3"):
        await t.herunterfahren("leerlauf")


async def test_b1_pisugar_fehlendes_kommando_ist_ein_fehler():
    t = PiSugarStrom("127.0.0.1", 1, ("/gibt/es/nicht-poweroff",))
    with pytest.raises(HerunterfahrenFehler, match="nicht startbar"):
        await t.herunterfahren("leerlauf")


async def test_b1_pisugar_zeitueberschreitung_ist_ein_fehler(monkeypatch):
    monkeypatch.setattr(power, "ABSCHALT_FRIST_S", 0.1)
    t = PiSugarStrom("127.0.0.1", 1, ("sleep", "5"))
    with pytest.raises(HerunterfahrenFehler, match="länger"):
        await t.herunterfahren("leerlauf")


async def test_b1_pisugar_erfolg_ist_still():
    await PiSugarStrom("127.0.0.1", 1, ("true",)).herunterfahren("leerlauf")


async def test_b1_power_meldet_den_fehler_als_ereignis_und_bewaffnet_den_tiefstand_neu():
    gesehen: list = []
    jetzt = [100.0]
    p = Power(KaputtesPoweroff(akku=3, lader=False), gesehen.append, mono=lambda: jetzt[0])
    await p.pruefe()
    assert ev.AkkuTiefstand() in gesehen
    gesehen.clear()
    assert await p.fuehre_aus(ev.Herunterfahren("akku_tiefstand")) is False
    assert gesehen == [ev.HerunterfahrenFehlgeschlagen("systemctl endete mit Rückgabecode 1")]
    gesehen.clear()
    await p.pruefe()
    assert ev.AkkuTiefstand() not in gesehen  # noch nicht: kein Dauerfeuer alle 10 s
    jetzt[0] += power.TIEFSTAND_WIEDERHOLEN_S + 1
    await p.pruefe()
    assert ev.AkkuTiefstand() in gesehen  # ein späterer Tiefstand schaltet wieder ab (Probe 3 des Prüfers)


async def test_b1_power_simulation_meldet_simuliert():
    gesehen: list = []
    p = Power(SimStrom(), gesehen.append)
    assert await p.fuehre_aus(ev.Herunterfahren("hauptknopf")) is False
    assert gesehen == [ev.HerunterfahrenFehlgeschlagen("", simuliert=True)]


async def test_b1_app_fehlgeschlagenes_poweroff_idle_zaehlt_neu_und_ha_erfaehrt_es(d):
    a = d.app
    a.power.treiber = KaputtesPoweroff()
    await d.sim(befehl="strom", lader=False, akku=80)  # ohne Strom: die Frist zählt (Ein/Aus, 10.11.)
    await d.ruhe()
    assert (await d.sim(befehl="taste", taste="hauptknopf_lang")) == {"ok": True}
    await d.ruhe()
    assert a.kern.teil["idle"].modus in ("aktiv", "leerlauf")  # nicht mehr endgültig (Probe 3: war „herunterfahren“ für immer)
    fehler = [b for b in a.ha.gesendet if b.art == "fehler"]
    assert len(fehler) == 1 and fehler[0].daten["code"] == "herunterfahren_fehlgeschlagen"
    # das zweite Mal geht wieder (Probe 3: „2. lang“ gab nichts)
    await d.sim(befehl="taste", taste="hauptknopf_lang")
    await d.ruhe()
    assert len([b for b in a.ha.gesendet if b.art == "fehler"]) == 2
    # nach 10 min Leerlauf ohne Strom wieder ein Versuch
    await d.zeit_vor(idle_leerlauf() + 5)
    await d.ruhe()
    assert len([b for b in a.ha.gesendet if b.art == "fehler"]) == 3


def idle_leerlauf() -> float:
    from tobibox.idle import LEERLAUF_S

    return LEERLAUF_S


async def test_b1_app_marker_wird_nach_fehlschlag_wieder_geschrieben(d):
    a = d.app
    a.power.treiber = KaputtesPoweroff()
    await d.auflegen(BEKANNT)
    marker = a.konfig.pfade.zustand / "lauf.json"
    assert marker.exists()
    await d.sim(befehl="taste", taste="hauptknopf_lang")
    await d.ruhe()
    assert a._herunterfahren is False
    await d.abheben()
    await d.auflegen(BEKANNT, "v2")
    assert marker.exists()  # bei Erfolg wäre er gelöscht geblieben


async def test_b1_mac_simulation_kehrt_nach_fester_zeit_zurueck(d):
    a = d.app
    await d.sim(befehl="taste", taste="hauptknopf_lang")
    await d.ruhe()
    assert a.kern.teil["idle"].modus == "herunterfahren"
    await d.zeit_vor(5)
    assert a.kern.teil["idle"].modus == "herunterfahren"
    await d.zeit_vor(6)
    assert a.kern.teil["idle"].modus in ("aktiv", "leerlauf")
    assert not [b for b in a.ha.gesendet if b.art == "fehler"]  # Simulation: kein Hinweis an HA


async def test_b1_app_ohne_strom_abschnitt_ist_auch_simuliert(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch)
    assert dienst.app.power is None
    await dienst.app.starte()
    try:
        await dienst.sim(befehl="taste", taste="hauptknopf_lang")
        await dienst.ruhe()
        assert dienst.app.kern.teil["idle"].modus == "herunterfahren"
        await dienst.zeit_vor(11)
        assert dienst.app.kern.teil["idle"].modus in ("aktiv", "leerlauf")
    finally:
        await dienst.app.beende()


# --------------------------------------------------------------------------------------------------------------
# B2: Hauptknopf über den PiSugar (Abfrage hinter einer Konfiguration, am Pi zu prüfen)
# --------------------------------------------------------------------------------------------------------------


def test_b2_parse_taste():
    assert parse_taste("button_event: long") == "lang"
    assert parse_taste("button_event: single") == "kurz"
    assert parse_taste("button_event: none") is None
    assert parse_taste("button_event: double") is None
    assert parse_taste("") is None


async def test_b2_taste_lauf_fragt_ab_und_sendet_hauptknopf():
    antworten = iter(["x: none", "x: single", "x: long", "x: none"])
    gesehen: list = []

    class T(SimStrom):
        async def taste_abfragen(self, befehl):
            assert befehl == "get taste"
            try:
                return next(antworten)
            except StopIteration:
                raise asyncio.CancelledError from None

    p = Power(T(), gesehen.append, taste_befehl="get taste", taste_intervall_s=0.001)
    with pytest.raises(asyncio.CancelledError):
        await p.taste_lauf()
    assert gesehen == [ev.Hauptknopf("kurz"), ev.Hauptknopf("lang")]


async def test_b2_ohne_taste_befehl_tut_taste_lauf_nichts():
    p = Power(SimStrom(), lambda e: None)
    await asyncio.wait_for(p.taste_lauf(), 1.0)  # kehrt sofort zurück


def test_b2_konfiguration_taste_befehl():
    k = konfig_modul.pruefe({
        "pfade": {"zustand": "/tmp/z", "medien": "/tmp/m"},
        "strom": {"quelle": "sim", "taste_befehl": "get button_event", "taste_intervall_s": 1.0},
    })
    assert k.strom.taste_befehl == "get button_event" and k.strom.taste_intervall_s == 1.0
    k = konfig_modul.pruefe({"pfade": {"zustand": "/tmp/z", "medien": "/tmp/m"}, "strom": {"quelle": "sim"}})
    assert k.strom.taste_befehl is None  # Vorgabe: aus


async def test_b2_app_startet_den_tastendienst_nur_mit_konfiguration(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, '[netz]\nquelle = "sim"\n[strom]\nquelle = "sim"\ntaste_befehl = "get x"\n')
    a = dienst.app
    aufgerufen: list = []

    async def lauf_(self=None):
        aufgerufen.append(1)
        await asyncio.sleep(10)

    a.power.taste_lauf = lauf_
    await a.starte()
    try:
        await asyncio.sleep(0.05)
        assert aufgerufen == [1]
        taste = [t for t in a._aufgaben if t.get_name() == "tobibox-taste"]
        assert len(taste) == 1
    finally:
        await a.beende()


async def test_b2_warnung_wenn_der_hauptknopf_am_pi_keine_quelle_hat(tmp_path, kurz, monkeypatch, caplog):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, GPIO)
    a = dienst.app
    a.gpio_tasten = None  # keine echte Hardware
    await a.starte()
    try:
        zeilen = [r for r in caplog.records if getattr(r, "ereignis", "") == "hauptknopf" and r.levelname == "WARNING"]
        assert len(zeilen) == 1
    finally:
        await a.beende()


# --------------------------------------------------------------------------------------------------------------
# B3 / Entscheidung P: Kopfhörer-Kontakt nicht lesbar -> Kopfhörer-Grenze
# --------------------------------------------------------------------------------------------------------------


def test_b3_kern_nicht_lesbar_setzt_die_kopfhoerer_grenze_und_meldet_an_ha(tmp_path):
    box = CujBox(tmp_path, {}, None)  # Einstellungen: max 60, start 40, Kopfhörer 25
    assert "kopfhoerer" not in box.kern.grenzen
    aus = box.sende(ev.KopfhoererLesbar(False))
    assert box.kern.grenzen["kopfhoerer"] == 25
    fehler = [b for b in aus if isinstance(b, ev.EreignisSenden)]
    assert len(fehler) == 1 and fehler[0].art == "fehler" and fehler[0].daten["code"] == "kopfhoerer_unlesbar"
    assert not [b for b in aus if isinstance(b, ev.AusgangWaehlen)]  # nur die Ohren schützen, der Ausgang bleibt
    assert box.sende(ev.KopfhoererLesbar(False)) == []  # nur einmal
    box.sende(ev.KopfhoererLesbar(True))
    assert "kopfhoerer" not in box.kern.grenzen


def test_b3_stecker_waehrend_unlesbar_haelt_die_grenze_nach_wieder_lesbar(tmp_path):
    box = CujBox(tmp_path, {}, None)
    box.sende(ev.KopfhoererLesbar(False))
    box.sende(ev.Kopfhoerer(True))
    box.sende(ev.KopfhoererLesbar(True))
    assert box.kern.grenzen["kopfhoerer"] == 25  # Stecker steckt: die Grenze bleibt
    box.sende(ev.Kopfhoerer(False))
    assert "kopfhoerer" not in box.kern.grenzen


def test_b3_einstellungen_nach_dem_ausfall_bekommen_die_grenze(tmp_path):
    box = CujBox(tmp_path, {}, None)
    box.sende(ev.KopfhoererLesbar(False))
    box.sende(ev.GeraeteEinstellungen(60, 40, 30))
    assert box.kern.grenzen["kopfhoerer"] == 30


async def test_b3_app_start_ohne_lesbaren_kontakt_gilt_die_kopfhoerer_grenze(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, GPIO_KH)
    a = dienst.app
    a.ha = HaSpion()

    async def kaputt():
        raise OSError("gpioget nicht lesbar")

    a.kopfhoerer_treiber._lese = kaputt
    await a.starte()
    try:
        await dienst.ruhe()
        assert a.kern.grenzen.get("kopfhoerer") == 30  # Konfiguration: min(30, max)
        assert [b.daten["code"] for b in a.ha.gesendet if b.art == "fehler"] == ["kopfhoerer_unlesbar"]
        await dienst.auflegen(BEKANNT)
        assert a.kern.wunsch == 20 and a.player.aufrufe  # spielt, mit der Grenze
        assert a.kern.ausgegeben.grenze == 30
    finally:
        await a.beende()


# --------------------------------------------------------------------------------------------------------------
# B5 / Entscheidung O: siehe test_idle.py und cuj/test_cuj16_leerlauf.py; hier die Ring-Folge
# --------------------------------------------------------------------------------------------------------------


def test_b5_ring_zeigt_die_pause_auch_im_leerlauf_mit_liegendem_tobie():
    from tobibox import led

    lg = led.LedLogik()
    lg.beobachte(ev.ZustandMelden("pausiert", "leerlauf", "s1", False, "normal", "aus", True), 0.0)
    assert lg.zustand(1.0) == led.PAUSE
    lg.beobachte(ev.ZustandMelden("pausiert", "aktiv", "s1", False, "normal", "aus", True), 2.0)
    assert lg.zustand(2.1) == led.PAUSE  # kein Aufwachen-Lauflicht bei jedem Weiterspielen
    lg.beobachte(ev.ZustandMelden("leer", "leerlauf", None, False, "normal", "aus", False), 3.0)
    assert lg.zustand(3.0) == led.AUS


# --------------------------------------------------------------------------------------------------------------
# B6: Takt-Sync nach dem Entschluss zum Herunterfahren
# --------------------------------------------------------------------------------------------------------------


async def test_b6_kein_takt_sync_nach_herunterfahren(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt() + sync_abschnitt(1))
    a = dienst.app
    zaehler = {"takt": 0}

    async def takt():
        zaehler["takt"] += 1
        return False

    a.sync.takt = takt
    await a.starte()
    try:
        await dienst.zeit_vor(1)
        vorher = zaehler["takt"]
        assert vorher > 0
        await dienst.sim(befehl="taste", taste="hauptknopf_lang")
        assert a.kern.teil["idle"].modus == "herunterfahren"
        zaehler["takt"] = 0
        await dienst.zeit_vor(1)
        await dienst.zeit_vor(1)
        assert a.kern.teil["idle"].modus == "herunterfahren" and zaehler["takt"] == 0
    finally:
        await a.beende()


# --------------------------------------------------------------------------------------------------------------
# B7: Start-Sync am Lader wartet auf die erste Netz-Klasse
# --------------------------------------------------------------------------------------------------------------


async def _lader_vor_netz(tmp_path, kurz, monkeypatch, warten_s: float | None = None):
    if warten_s is not None:
        monkeypatch.setattr(app_modul, "NETZ_KLASSE_WARTEN_S", warten_s)
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt() + sync_abschnitt(1))
    a = dienst.app
    los = asyncio.Event()
    orig = a.netz.pruefe

    async def lauf():  # die Netz-Messung (nmcli, NAS) dauert länger als der PiSugar-Aufruf
        await los.wait()
        await orig()
        await asyncio.sleep(3600)

    a.netz.lauf = lauf
    starts: list = []

    async def start(grund="ha"):
        starts.append((grund, a.sync.netz_bekannt))
        return True

    a.sync.start = start
    await a.starte()
    return dienst, los, starts


async def test_b7_start_sync_wartet_auf_die_erste_netz_klasse(tmp_path, kurz, monkeypatch):
    dienst, los, starts = await _lader_vor_netz(tmp_path, kurz, monkeypatch)
    a = dienst.app
    try:
        await dienst.sim(befehl="strom", lader=True, akku=80)
        await asyncio.sleep(0.1)
        assert [x for x in starts if x[0] == "start_lader"] == []  # wartet, statt mit ``regel`` abzubrechen (Probe des Prüfers)
        await dienst.sim(befehl="netz", klasse="home")
        await asyncio.sleep(0.1)
        assert [x for x in starts if x[0] == "start_lader"] == [("start_lader", True)]  # erst mit bekannter Netz-Klasse
    finally:
        await a.beende()


async def test_b7_ohne_netz_klasse_startet_der_sync_nach_der_frist(tmp_path, kurz, monkeypatch):
    dienst, los, starts = await _lader_vor_netz(tmp_path, kurz, monkeypatch, warten_s=0.1)
    try:
        await dienst.sim(befehl="strom", lader=True, akku=80)
        await asyncio.sleep(0.4)
        assert [x for x in starts if x[0] == "start_lader"] == [("start_lader", False)]  # ``sync`` antwortet dann selbst (``regel``), ``idle`` wiederholt
    finally:
        await dienst.app.beende()


async def test_b7_echter_sync_antwortet_nicht_mehr_mit_regel_vor_der_netz_klasse(tmp_path, kurz, monkeypatch):
    """Wie ``test_probe_race.py`` des Prüfers, mit dem echten ``Sync``."""
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt() + sync_abschnitt(1))
    a = dienst.app
    los = asyncio.Event()
    orig = a.netz.pruefe

    async def lauf():
        await los.wait()
        await orig()
        await asyncio.sleep(3600)

    a.netz.lauf = lauf
    await a.starte()
    try:
        await dienst.sim(befehl="strom", lader=True, akku=80)
        await asyncio.sleep(0.1)
        assert a.status.sync["grund"] != "regel"
    finally:
        await a.beende()


# --------------------------------------------------------------------------------------------------------------
# B8: Simulationszeit
# --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("iso", [
    "0001-01-01T00:00:00+00:00", "9999-12-31T23:59:59+00:00", "0001-01-01T00:00:00", "9999-12-31T12:00:00",
    "1999-12-31T23:59:59+01:00", "2101-01-01T00:00:00+01:00",
])
async def test_b8_sim_zeit_ausserhalb_2000_bis_2100_ist_ungueltig(d, iso):
    with pytest.raises(Ungueltig, match="iso ungueltig"):
        await d.app.sim.verarbeite(json.dumps({"befehl": "zeit", "iso": iso}))
    assert abs(d.app.uhr.jetzt().wall - datetime.now(timezone.utc).timestamp()) < 3600 * 24 * 365 * 50  # Uhr unverändert


async def test_b8_gueltige_zeit_geht(d):
    a = await d.sim(befehl="zeit", iso="2026-11-09T22:30:00+01:00")
    assert a["ok"] is True


async def test_b8_quiet_wirft_bei_extremer_wanduhr_nicht():
    from tobibox.events import Jetzt

    lz = ev.LeiseZeiten("Europe/Berlin", (stufe4.fenster("a", "stumm", "22:00", "07:00"), stufe4.fenster("b", "leiser", "19:00", "20:00", 20)))
    for wall_ in (-62135596800.0, 253402300799.0, 1e18, float("inf")):
        assert quiet.wirkung_jetzt(lz, Jetzt(1.0, wall_, "system", True)) == ("leiser", 20)  # wie eine unsichere Uhr: nie „stumm“


async def test_b8_haken_fehler_toetet_den_client_nicht(d):
    def kaputt(wall_):
        raise RuntimeError("Uhr kaputt")

    d.app.sim.zeit_haken = kaputt
    leser, schreiber = await asyncio.open_unix_connection(str(d.app.sim.pfad))
    try:
        schreiber.write(b'{"befehl":"zeit","iso":"2026-11-09T12:00:00+01:00"}\n')
        await schreiber.drain()
        a1 = json.loads(await asyncio.wait_for(leser.readline(), 3))
        assert a1["ok"] is False
        schreiber.write(b'{"befehl":"status"}\n')  # die Verbindung lebt noch
        await schreiber.drain()
        a2 = json.loads(await asyncio.wait_for(leser.readline(), 3))
        assert a2["ok"] is True
    finally:
        schreiber.close()


async def test_b8_unerwartete_ausnahme_wird_beantwortet(d, monkeypatch):
    async def kaputt(zeile):
        raise RuntimeError("unerwartet")

    monkeypatch.setattr(d.app.sim, "verarbeite", kaputt)
    leser, schreiber = await asyncio.open_unix_connection(str(d.app.sim.pfad))
    try:
        schreiber.write(b'{"befehl":"status"}\n')
        await schreiber.drain()
        assert json.loads(await asyncio.wait_for(leser.readline(), 3)) == {"ok": False, "fehler": "intern"}
    finally:
        schreiber.close()


async def test_b8_takt_stirbt_bei_extremer_wanduhr_nicht(d):
    """Auch eine Uhr außerhalb des Bereichs (z. B. vom Gerät) legt den Kern nicht lahm."""
    d.uhr.setze_wall(253402300799.0)
    await d.sende(ev.Takt())
    assert d.app.kern.teil["idle"].modus in ("aktiv", "leerlauf")  # ``verarbeite`` lief durch


# --------------------------------------------------------------------------------------------------------------
# B9: Sim-Eingänge nur mit Quelle ``sim`` oder ``[sim] erlauben``
# --------------------------------------------------------------------------------------------------------------


def test_b9_konfiguration_sim_erlauben():
    roh = {"pfade": {"zustand": "/tmp/z", "medien": "/tmp/m"}}
    assert konfig_modul.pruefe(roh).sim.erlauben is False
    assert konfig_modul.pruefe({**roh, "sim": {"erlauben": True}}).sim.erlauben is True
    with pytest.raises(konfig_modul.KonfigFehler):
        konfig_modul.pruefe({**roh, "sim": {"erlauben": "ja"}})


async def test_b9_am_mac_ist_alles_erlaubt(d):
    q = d.app.sim.quelle_sim
    assert all(q.values()), q


async def test_b9_pi_quellen_sperren_die_eingaenge(tmp_path, kurz, monkeypatch):
    abschnitte = GPIO + GPIO_KH + '[netz]\nquelle = "networkmanager"\nheim_ssid = "heim"\n[strom]\nquelle = "pisugar"\n'
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, abschnitte)
    a = dienst.app
    q = a.sim.quelle_sim
    for k in ("hauptknopf_kurz", "hauptknopf_lang", "weiter", "zurueck", "regler", "kopfhoerer", "strom", "netz", "zeit"):
        assert q[k] is False, k
    for zeile in (
        {"befehl": "zeit", "iso": "2026-11-09T22:30:00+01:00"},
        {"befehl": "taste", "taste": "hauptknopf_kurz"},
        {"befehl": "taste", "taste": "hauptknopf_lang"},
        {"befehl": "regler", "delta": 2},
        {"befehl": "kopfhoerer", "steckt": True},
        {"befehl": "strom", "akku": 3},
        {"befehl": "netz", "klasse": "home"},
    ):
        with pytest.raises(Ungueltig, match="quelle_nicht_sim"):
            await a.sim.verarbeite(json.dumps(zeile))
    assert a.ereignisse.empty()  # nichts ist angekommen
    assert a.uhr.jetzt().wall == pytest.approx(datetime.now(timezone.utc).timestamp(), abs=5)


async def test_b9_antwort_ueber_den_socket_und_anzeige_nennt_die_sperre(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, GPIO)
    a = dienst.app
    a.gpio_tasten = None
    await a.starte()
    try:
        leser, schreiber = await asyncio.open_unix_connection(str(a.sim.pfad))
        try:
            schreiber.write(b'{"befehl":"taste","taste":"weiter"}\n{"befehl":"anzeige"}\n')
            await schreiber.drain()
            assert json.loads(await asyncio.wait_for(leser.readline(), 3)) == {"ok": False, "fehler": "quelle_nicht_sim"}
            anzeige = json.loads(await asyncio.wait_for(leser.readline(), 3))
            assert anzeige["quelle_sim"]["weiter"] is False and anzeige["quelle_sim"]["kopfhoerer"] is True
        finally:
            schreiber.close()
    finally:
        await a.beende()


async def test_b9_erlauben_hebt_die_sperre_auf(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, GPIO + '[sim]\nerlauben = true\n')
    a = dienst.app
    a.gpio_tasten = None
    assert all(a.sim.quelle_sim.values())
    await a.starte()
    try:
        assert (await dienst.sim(befehl="taste", taste="hauptknopf_kurz")) == {"ok": True}
        assert (await dienst.sim(befehl="zeit", iso="2026-11-09T22:30:00+01:00"))["ok"] is True
    finally:
        await a.beende()


async def test_b9_ha_ersatz_nur_ohne_mqtt(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch)
    dienst.app.sim.quelle_sim["ha"] = False
    for zeile in ({"befehl": "learn", "typ": "serie", "serie": "s1"}, {"befehl": "learn_abort"}, {"befehl": "ack", "uid": "04a1b2c3", "zuletzt": "x", "art": "gelernt"}):
        with pytest.raises(Ungueltig, match="quelle_nicht_sim"):
            await dienst.app.sim.verarbeite(json.dumps(zeile))


def test_b9_die_oberflaeche_graut_gesperrte_eingaenge_aus():
    from importlib import resources

    html = resources.files("tobibox.gui").joinpath("seite.html").read_text(encoding="utf-8")
    assert "quelle_sim" in html and "quelle_nicht_sim" in html


# --------------------------------------------------------------------------------------------------------------
# B10: blockierende Dateizugriffe in Threads
# --------------------------------------------------------------------------------------------------------------


async def test_b10_lauf_loesche_laeuft_in_einem_thread(d, monkeypatch):
    namen: list[str] = []
    orig = lauf.loesche

    def merke(pfad):
        namen.append(threading.current_thread().name)
        return orig(pfad)

    monkeypatch.setattr(app_modul.lauf, "loesche", merke)
    await d.app._fuehre_aus(ev.Herunterfahren("hauptknopf"), 0.0)
    assert namen and namen[0] != threading.main_thread().name


async def test_b10_sync_zaehlt_dateien_in_einem_thread(tmp_path, monkeypatch):
    from tobibox.config import SyncKonfig
    from tobibox.sync import Sync

    sy = Sync(SyncKonfig(host="127.0.0.1"), tmp_path / "medien", ausgabe=lambda e: None)
    namen: list[str] = []
    orig_z, orig_v = sy._zaehle_dateien, sy._bereite_vor

    def zaehle():
        namen.append(threading.current_thread().name)
        return orig_z()

    def vor():
        namen.append(threading.current_thread().name)
        return orig_v()

    sy._zaehle_dateien, sy._bereite_vor = zaehle, vor

    async def rsync_lauf(cmd, *, lies=False, je_zeile=None):
        return 0, ["-rw-r--r--          1 2026/11/09 10:00:00 a.wav"], ""

    sy._rsync_lauf = rsync_lauf
    await sy._durchfuehren()
    assert len(namen) == 2 and all(n != threading.main_thread().name for n in namen)


# --------------------------------------------------------------------------------------------------------------
# B11: eine Ausnahme nach core.step verliert die Befehle nicht
# --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("stelle", ["_nachfuehren_stufe_4", "_ton_pegel_nachfuehren"])
async def test_b11_ausnahme_in_der_nachfuehrung_verliert_keine_befehle(d, stelle):
    a = d.app

    def kaputt(*args, **kw):
        raise RuntimeError("kaputt")

    setattr(a, stelle, kaputt)
    await d.auflegen(BEKANNT)
    assert d.abgespielt() == [BAER]  # ``Abspielen`` kam trotz der Ausnahme an


async def test_b11_ausnahme_in_ausgang_nach_kern_verliert_keine_befehle(d):
    a = d.app

    def kaputt(kern):
        raise RuntimeError("kaputt")

    a.ausgang.nach_kern = kaputt
    await d.auflegen(BEKANNT)
    assert d.abgespielt() == [BAER]


async def test_b11_ausnahme_im_herunterfahren_verliert_den_befehl_nicht(d):
    a = d.app

    def kaputt(*args, **kw):
        raise RuntimeError("kaputt")

    a.led.beobachte = kaputt
    gefahren: list = []

    async def fuehre_aus(b):
        gefahren.append(b)
        return True

    a.power.fuehre_aus = fuehre_aus
    await d.sim(befehl="taste", taste="hauptknopf_lang")
    assert gefahren == [ev.Herunterfahren("hauptknopf")]


# --------------------------------------------------------------------------------------------------------------
# B12: Ton akku_leer
# --------------------------------------------------------------------------------------------------------------


async def test_b12_tiefstand_spielt_akku_leer_einmal_dann_herunterfahren(d):
    a = d.app
    gefahren: list = []

    async def fuehre_aus(b):
        gefahren.append((b, list(d.toene)))
        return True

    a.power.fuehre_aus = fuehre_aus
    await d.sim(befehl="strom", lader=False, akku=80)
    await d.sim(befehl="strom", akku=3)
    await d.ruhe()
    assert d.toene.count("akku_leer") == 1
    assert [b for b, _ in gefahren] == [ev.Herunterfahren("akku_tiefstand")]
    assert gefahren[0][1].count("akku_leer") == 1  # der Ton ist vor dem Poweroff ausgegeben


async def test_b12_poweroff_wartet_auf_das_ende_des_tons(d):
    a = d.app
    ton_fertig = asyncio.Event()
    reihenfolge: list[str] = []

    class Toene:
        beschaeftigt = True
        gespielt: list = []

        async def warte_leer(self):
            await ton_fertig.wait()
            reihenfolge.append("ton_fertig")

        def spiele(self, ton, *args, **kw):
            return True

        async def stop(self):
            pass

    async def fuehre_aus(b):
        reihenfolge.append("poweroff")
        return True

    a.toene = Toene()
    a.power.fuehre_aus = fuehre_aus
    t = asyncio.create_task(a._fuehre_aus(ev.Herunterfahren("akku_tiefstand"), 0.0))
    await asyncio.sleep(0.05)
    assert reihenfolge == []
    ton_fertig.set()
    await t
    assert reihenfolge == ["ton_fertig", "poweroff"]


# --------------------------------------------------------------------------------------------------------------
# B13: Töne folgen der „leiser“-Absenkung
# --------------------------------------------------------------------------------------------------------------

UID = "04a1b2c3"
SERIE = "3f9a1c07b2d4"


def _aufbau(medien):
    stufe4.serie(medien, "rabe", ["a.wav", "b.wav"], SERIE, "Rabe", 200.0)
    stufe4.ueberraschung(medien)


def test_b13_ton_pegel_folgt_waehrend_der_absenkung_dem_ziel(tmp_path):
    box = CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, _aufbau)
    stufe4.setze_konfig(box, fenster_liste=(stufe4.fenster("abend", "leiser", "19:30", "21:00", 20),))
    box.uhr.setze_wall(wall(2026, 11, 9, 19, 29, 58))
    box.laufe(0.2)
    box.auflege(UID)
    box.laufe(2.0)
    box.laufe(1.0)  # 19:30 erreicht: die Absenkung beginnt
    assert box.kern.teil["quiet"].absenken is not None
    assert box.kern.grenzen.get("ausblenden", 100) > 20  # die Rampe ist noch oben
    grenze, laut = nachfuehrung.ton_pegel(box.kern)
    assert grenze == 20 and laut <= 20  # B13: Töne klingen nie über der Grenze, die gleich gilt
    box.laufe(4.0)
    assert box.kern.teil["quiet"].absenken is None
    assert nachfuehrung.ton_pegel(box.kern) == (20, 20)


def test_b13_gute_nacht_und_stumm_rampen_bleiben_ausgenommen(tmp_path):
    box = CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, _aufbau)
    box.auflege(UID)
    box.laufe(1.0)
    box.kern = box.kern.__class__(**{**{f: getattr(box.kern, f) for f in box.kern.__dataclass_fields__}, "grenzen": {**box.kern.grenzen, "ausblenden": 3}})
    grenze, _ = nachfuehrung.ton_pegel(box.kern)
    assert grenze == 60  # die Rampe „ausblenden“ zählt für Töne nicht (Entscheidung J)


async def test_b13_app_nutzt_dieselbe_funktion(d):
    a = d.app
    await d.auflegen(BEKANNT)
    assert (a.grenze, a.lautstaerke) == nachfuehrung.ton_pegel(a.kern)


# --------------------------------------------------------------------------------------------------------------
# B14: sim regler wie die Hardware
# --------------------------------------------------------------------------------------------------------------


async def test_b14_sim_regler_ueber_der_kopfhoerer_grenze_aendert_den_wunsch_nicht(d):
    a = d.app
    await d.sim(befehl="regler", delta=20)  # 20 -> 40, Grenze 50
    assert a.kern.wunsch == 40
    await d.sim(befehl="kopfhoerer", steckt=True)  # Grenze 30
    assert a.kern.grenzen["kopfhoerer"] == 30
    assert (await d.sim(befehl="regler", delta=2)) == {"ok": True}
    assert a.kern.wunsch == 40  # wie die Hardware (Probe 1 des Prüfers: Wunsch wurde 25)
    await d.sim(befehl="kopfhoerer", steckt=False)
    assert a.kern.ausgegeben.prozent == 40


async def test_b14_sim_regler_runter_wie_die_hardware(d):
    a = d.app
    await d.sim(befehl="regler", delta=-6)
    assert a.kern.wunsch == 14
    await d.sim(befehl="regler", delta=-20)
    assert a.kern.wunsch == 0


async def test_b14_bedienung_drehen_prozent_gleich_drehen():
    gesendet: list = []
    b = Bedienung(gesendet.append, stand=40, grenze=30)
    b.drehen_prozent(2)
    assert gesendet == []
    b.drehen_prozent(-4)
    assert gesendet == [ev.LautstaerkeDrehen(-10)]  # von 40 auf die Grenze 30, wie ``drehen(-2)``


# --------------------------------------------------------------------------------------------------------------
# B15: Systemuhr ohne [netz]/[strom] auf dem Pi
# --------------------------------------------------------------------------------------------------------------


class FesteNtp:
    def __init__(self, wert: bool) -> None:
        self.wert = wert

    async def synchron(self) -> bool:
        return self.wert


async def test_b15_pi_ohne_netz_und_strom_traut_der_systemuhr_nur_mit_ntp(tmp_path, kurz, monkeypatch, caplog):
    monkeypatch.setattr(App, "_systemuhr_pruefen_noetig", lambda self: True)
    monkeypatch.setattr(app_modul, "SYSTEMUHR_PRUEFEN_S", 0.05)
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, uhr=SystemUhr())  # type: ignore[arg-type]
    a = dienst.app
    ntp = FesteNtp(False)
    a._systemuhr_ntp = ntp  # type: ignore[assignment]
    assert a.uhr.jetzt().zeit_ok is False and a.uhr.jetzt().zeit_quelle == "unbekannt"
    assert any(getattr(r, "ereignis", "") == "systemuhr" for r in caplog.records)
    assert a.sim.quelle_sim["zeit"] is False  # die Uhr hängt an NTP: ``sim time`` stellt sie nicht
    await a.starte()
    try:
        await dienst.ruhe()
        assert a.uhr.jetzt().zeit_ok is False
        ntp.wert = True
        await dienst.warte(lambda: a.uhr.jetzt().zeit_ok, 3.0, "NTP-Wechsel nicht übernommen")
        assert a.uhr.jetzt().zeit_quelle == "ntp"
    finally:
        await a.beende()


async def test_b15_am_mac_bleibt_die_systemuhr_sicher(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, uhr=SystemUhr())  # type: ignore[arg-type]
    assert dienst.app.uhr.jetzt().zeit_ok is True and dienst.app._systemuhr_ntp is None
    assert dienst.app.sim.quelle_sim["zeit"] is True


async def test_b15_nur_mit_der_echten_uhr_und_linux(monkeypatch):
    """Ohne die Test-Hilfe gilt: Linux und ``SystemUhr`` -> Prüfung; mit ``SimUhr`` nie; ``[uhr] ntp_pflicht`` überstimmt."""
    from tobibox.clock import SimUhr
    from tobibox.config import UhrKonfig

    monkeypatch.undo()  # die Hilfe ``_systemuhr_wie_am_mac`` zurücknehmen

    def app(uhr, pflicht=None):
        return SimpleNamespace(uhr=uhr, konfig=SimpleNamespace(uhr=UhrKonfig(pflicht)))

    pruefen = App._systemuhr_pruefen_noetig
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    assert pruefen(app(SystemUhr())) is True  # type: ignore[arg-type]
    assert pruefen(app(SystemUhr(), False)) is False  # type: ignore[arg-type]
    monkeypatch.setattr(sys, "platform", "darwin", raising=False)
    assert pruefen(app(SystemUhr())) is False  # type: ignore[arg-type]
    assert pruefen(app(SystemUhr(), True)) is True  # type: ignore[arg-type]
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    assert pruefen(app(SimUhr())) is False  # type: ignore[arg-type]


def test_b15_konfiguration_uhr_ntp_pflicht():
    roh = {"pfade": {"zustand": "/tmp/z", "medien": "/tmp/m"}}
    assert konfig_modul.pruefe(roh).uhr.ntp_pflicht is None
    assert konfig_modul.pruefe({**roh, "uhr": {"ntp_pflicht": False}}).uhr.ntp_pflicht is False
    with pytest.raises(konfig_modul.KonfigFehler):
        konfig_modul.pruefe({**roh, "uhr": {"ntp_pflicht": "nein"}})


async def test_b15_ntp_quelle_liest_die_marke_von_systemd(tmp_path, monkeypatch):
    from tobibox import net

    marke = tmp_path / "synchronized"
    monkeypatch.setattr(net, "NTP_MARKE", marke)

    async def kein_timedatectl(*argv):
        return None

    monkeypatch.setattr(net, "_lauf", kein_timedatectl)
    assert await net.TimedatectlNtp().synchron() is False
    marke.write_text("")
    assert await net.TimedatectlNtp().synchron() is True


# --------------------------------------------------------------------------------------------------------------
# B16: UpdateStarten wird beantwortet
# --------------------------------------------------------------------------------------------------------------


async def test_b16_update_starten_antwortet_mit_befehl_abgelehnt(d):
    a = d.app
    await d.sim(befehl="strom", lader=True, akku=80)
    await d.sim(befehl="netz", klasse="home")
    await d.sende(ev.HaUpdateAnstossen("u1", "0.2.0", a.uhr.jetzt().wall + 60))
    abgelehnt = [b for b in a.ha.gesendet if b.art == "befehl_abgelehnt"]
    assert len(abgelehnt) == 1
    assert dict(abgelehnt[0].daten) == {
        "befehl": "update", "befehl_id": "u1", "grund": "bedingung", "detail": "Update kommt mit Stufe 3b.",
    }


# --------------------------------------------------------------------------------------------------------------
# B17: GpioTreiber räumt bei einem Teilfehler auf
# --------------------------------------------------------------------------------------------------------------


async def test_b17_teilfehler_schliesst_die_schon_erzeugten_geraete():
    erzeugt: list = []

    class Gv:
        def __init__(self, *a, **kw):
            self.zu = False
            erzeugt.append(self)

        def close(self):
            self.zu = True

    class Fabrik:
        Button = Gv

        @staticmethod
        def RotaryEncoder(*a, **kw):  # noqa: N802
            raise RuntimeError("Pin belegt")

    t = GpioTreiber(Bedienung(lambda e: None), pin_vor=5, pin_zurueck=6, pin_dreh_a=12, pin_dreh_b=13, fabrik=Fabrik)
    with pytest.raises(RuntimeError):
        t.start()
    assert len(erzeugt) == 2 and all(g.zu for g in erzeugt)
    assert t.geraete == []


async def test_b17_dritter_button_fehlt_auch():
    erzeugt: list = []

    class Gv:
        def __init__(self, pin, *args, **kw):
            if pin == 26:
                raise RuntimeError("Pin belegt")
            self.zu = False
            erzeugt.append(self)

        def close(self):
            self.zu = True

    class Dreh(Gv):
        pass

    class Fabrik:
        Button = Gv
        RotaryEncoder = Dreh

    t = GpioTreiber(Bedienung(lambda e: None), pin_vor=5, pin_zurueck=6, pin_dreh_a=12, pin_dreh_b=13, pin_haupt=26, fabrik=Fabrik)
    with pytest.raises(RuntimeError):
        t.start()
    assert len(erzeugt) == 3 and all(g.zu for g in erzeugt)


# --------------------------------------------------------------------------------------------------------------
# T1: ``BedienBox`` benutzt denselben Code wie ``App``
# --------------------------------------------------------------------------------------------------------------


def test_t1_testaufbau_und_app_teilen_die_nachfuehrung():
    import inspect

    assert "nachfuehrung.stufe_4" in inspect.getsource(BedienBox._fuehre_nach)
    assert "nachfuehrung.stufe_4" in inspect.getsource(App._nachfuehren_stufe_4)
    assert "nachfuehrung.led_ausblenden" in inspect.getsource(App._led_ausblenden)
    assert "nachfuehrung.ton_pegel" in inspect.getsource(App._ton_pegel_nachfuehren)
    assert not hasattr(BedienBox, "_led_ausblenden")  # die Kopie ist weg


# --------------------------------------------------------------------------------------------------------------
# GUI-Ring: normierte Farbe, Helligkeit als Zahl und Balken
# --------------------------------------------------------------------------------------------------------------


def test_gui_ring_zeigt_echt_oder_volle_farbe_und_helligkeitsbalken():
    from importlib import resources

    html = resources.files("tobibox.gui").joinpath("seite.html").read_text(encoding="utf-8")
    assert 'id="ring-balken"' in html and 'id="ring-deckel"' in html
    # „Farben voll“: Stärke 1 (volle Deckkraft); „echt“: Stärke aus ringStaerke (relativ zum Deckel, Wahrnehmungskurve)
    assert 'ringModus === "echt" ? ringStaerke(h, deckel) : 1' in html and "farbe(f, st)" in html
    assert "farbe(f, h)" not in html  # nie roh mit der Helligkeit (höchstens 25 %) multipliziert
