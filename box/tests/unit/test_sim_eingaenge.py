"""``sim``: Eingänge der Simulations-Oberfläche (AP 4.9): Tasten, Regler, Kopfhörer, Strom, Netz, Tobies, ``anzeige``."""

from __future__ import annotations

import asyncio
import json
import re

import pytest

from tobibox import events as ev
from tobibox import sim as sim_modul
from tobibox.clock import SimUhr
from tobibox.sim import Sim

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def sim(kurz):
    got: list = []
    s = Sim(kurz, got.append, SimUhr(), anzeige=lambda: {"status": {}, "anzeige": {"figur": None}})
    s.got = got
    await s.start()
    yield s
    await s.stop()


async def sende(sim, *zeilen: str | dict):
    r, w = await asyncio.open_unix_connection(str(sim.pfad))
    antworten = []
    for z in zeilen:
        w.write((z if isinstance(z, str) else json.dumps(z)).encode() + b"\n")
        await w.drain()
        antworten.append(json.loads(await asyncio.wait_for(r.readline(), 2)))
    w.close()
    return antworten


async def eins(sim, **zeile):
    (a,) = await sende(sim, zeile)
    return a


# -- Tobies ----------------------------------------------------------------------------


async def test_auflegen_macht_aufgelegt_mit_vorgangs_id_und_seq(sim):
    a = await eins(sim, befehl="tobie_auflegen", uid="04a1b2c3")
    assert a["ok"] and a["uid"] == "04a1b2c3" and re.fullmatch(r"[0-9a-f]{8}", a["vorgang"])
    (e,) = sim.got
    assert e == ev.Aufgelegt("04a1b2c3", "ntag", False, 0, a["vorgang"])


async def test_tonie_kennung_ist_iso15693_und_tonie(sim):
    await eins(sim, befehl="tobie_auflegen", uid="e004031234567890")
    assert sim.got[0].typ == "iso15693" and sim.got[0].tonie is True


async def test_zufallskennung_ist_gueltig_und_jedes_mal_neu(sim):
    a = await eins(sim, befehl="tobie_auflegen", zufall=True)
    b = await eins(sim, befehl="tobie_auflegen", zufall=True)
    assert re.fullmatch(r"04[0-9a-f]{12}", a["uid"]) and a["uid"] != b["uid"]


async def test_wechsel_meldet_erst_abgehoben_dann_aufgelegt_mit_neuer_id(sim):
    a = await eins(sim, befehl="tobie_auflegen", uid="04a1b2c3")
    b = await eins(sim, befehl="tobie_auflegen", uid="04a1b2c4")
    assert [type(e) for e in sim.got] == [ev.Aufgelegt, ev.Abgehoben, ev.Aufgelegt]
    assert sim.got[1].vorgang == a["vorgang"] and sim.got[2].vorgang == b["vorgang"] != a["vorgang"]
    assert [e.seq for e in sim.got] == [0, 1, 2]


async def test_derselbe_tobie_ist_eine_wiedermeldung_ohne_ereignis(sim):
    a = await eins(sim, befehl="tobie_auflegen", uid="04a1b2c3")
    b = await eins(sim, befehl="tobie_auflegen", uid="04a1b2c3")
    assert b["ok"] and b["hinweis"] == "liegt_schon" and b["vorgang"] == a["vorgang"]
    assert len(sim.got) == 1


async def test_abheben_traegt_die_vorgangs_id_und_danach_gibt_es_eine_neue(sim):
    a = await eins(sim, befehl="tobie_auflegen", uid="04a1b2c3")
    assert (await eins(sim, befehl="tobie_abheben"))["ok"]
    assert sim.got[1] == ev.Abgehoben(1, a["vorgang"])
    b = await eins(sim, befehl="tobie_auflegen", uid="04a1b2c3")
    assert b["vorgang"] != a["vorgang"]


async def test_abheben_ohne_simulierten_tobie_ist_abgelehnt(sim):
    assert await eins(sim, befehl="tobie_abheben") == {"ok": False, "fehler": "kein_simulierter_tobie"}
    assert sim.got == []


async def test_gesperrt_und_wiedermeldung_und_wechsel(sim):
    a = await eins(sim, befehl="tobie_gesperrt")
    assert sim.got == [ev.Gesperrt(0, a["vorgang"])]
    assert (await eins(sim, befehl="tobie_gesperrt"))["hinweis"] == "liegt_schon"
    await eins(sim, befehl="tobie_auflegen", uid="04a1b2c3")
    assert [type(e) for e in sim.got] == [ev.Gesperrt, ev.Abgehoben, ev.Aufgelegt]


async def test_ungueltige_kennung(sim):
    a = await eins(sim, befehl="tobie_auflegen", uid="XYZ")
    assert a == {"ok": False, "fehler": "uid ungueltig"} and sim.got == []


# -- Tasten, Regler, Kopfhörer ------------------------------------------------------------


@pytest.mark.parametrize(
    ("taste", "erwartet"),
    [("hauptknopf_kurz", ev.Hauptknopf("kurz")), ("weiter", ev.Weiter()), ("zurueck", ev.Zurueck())],
)
async def test_tasten_gehen_als_ereignis_in_den_dienst(sim, taste, erwartet):
    assert await eins(sim, befehl="taste", taste=taste) == {"ok": True}
    assert sim.got == [erwartet]


async def test_hauptknopf_lang_ist_seit_ap_4_8_verdrahtet(sim):
    assert await eins(sim, befehl="taste", taste="hauptknopf_lang") == {"ok": True}
    assert sim.got == [ev.Hauptknopf("lang")]


async def test_taste_ungueltig(sim):
    assert (await eins(sim, befehl="taste", taste="blau"))["ok"] is False
    assert (await eins(sim, befehl="taste"))["ok"] is False


async def test_regler(sim):
    assert (await eins(sim, befehl="regler", delta=-2))["ok"]
    assert sim.got == [ev.LautstaerkeDrehen(-2)]
    for schlecht in (0, 99, "2", 1.5, True, None):
        assert (await eins(sim, befehl="regler", delta=schlecht))["ok"] is False
    assert len(sim.got) == 1


async def test_kopfhoerer(sim):
    assert (await eins(sim, befehl="kopfhoerer", steckt=True))["ok"]
    assert sim.got == [ev.Kopfhoerer(True)]
    assert (await eins(sim, befehl="kopfhoerer", steckt="ja"))["ok"] is False


# -- Strom und Netz (seit AP 3.7 verdrahtet) --------------------------------------------------


async def test_strom_und_netz_ohne_haken_geben_die_ereignisse_selbst_aus(sim):
    """Ohne ``[strom]`` und ``[netz]`` im Dienst (keine Haken) gibt ``sim`` die Ereignisse selbst aus."""
    assert (await eins(sim, befehl="strom", lader=True, akku=55))["ok"]
    assert (await eins(sim, befehl="netz", klasse="hotspot"))["ok"]
    assert sim.got == [ev.LaderGeaendert(True), ev.AkkuStand(55), ev.NetzKlasse("hotspot")]


async def test_strom_und_netz_werden_weiter_geprueft(sim):
    assert (await eins(sim, befehl="strom", akku=101))["fehler"] == "akku ungueltig"
    assert (await eins(sim, befehl="strom", lader="ja"))["fehler"] == "lader ungueltig"
    assert (await eins(sim, befehl="strom"))["ok"] is False
    assert (await eins(sim, befehl="netz", klasse="MeinWLAN"))["fehler"] == "klasse ungueltig"
    assert sim.got == []


async def test_mit_haken_stellt_sim_den_treiber_ein_und_gibt_selbst_nichts_aus(sim):
    aufrufe: list = []

    async def strom(lader, akku):
        aufrufe.append(("strom", lader, akku))

    async def netz(klasse):
        aufrufe.append(("netz", klasse))

    sim.strom_haken, sim.netz_haken = strom, netz
    assert (await eins(sim, befehl="strom", lader=False))["ok"]
    assert (await eins(sim, befehl="strom", akku=40))["ok"]
    assert (await eins(sim, befehl="netz", klasse="home"))["ok"]
    assert aufrufe == [("strom", False, None), ("strom", None, 40), ("netz", "home")]
    assert sim.got == []  # die Ereignisse kommen von ``power`` und ``net``


async def test_hauptknopf_lang_wird_verdrahtet_kommen_die_ereignisse(sim, monkeypatch):
    monkeypatch.setitem(sim_modul.VERDRAHTET, "hauptknopf_lang", True)
    assert (await eins(sim, befehl="taste", taste="hauptknopf_lang"))["ok"]
    assert sim.got == [ev.Hauptknopf("lang")]


# -- anzeige --------------------------------------------------------------------------------


async def test_anzeige_nennt_verdrahtung_und_simulierten_tobie(sim):
    a = await eins(sim, befehl="anzeige")
    assert a["ok"] and a["simuliert"] is None
    assert a["verdrahtet"]["hauptknopf_kurz"] is True and a["verdrahtet"]["netz"] is True and a["verdrahtet"]["strom"] is True and a["verdrahtet"]["hauptknopf_lang"] is True
    t = await eins(sim, befehl="tobie_auflegen", uid="04a1b2c3")
    a = await eins(sim, befehl="anzeige")
    assert a["simuliert"] == {"uid": "04a1b2c3", "vorgang": t["vorgang"]}  # innerhalb der Karenz bleibt er


async def test_anzeige_vergisst_den_tobie_wenn_der_kern_einen_anderen_zeigt(kurz):
    uhr = SimUhr()
    figur = {"vorgang": None}
    s = Sim(kurz, lambda e: None, uhr, anzeige=lambda: {"anzeige": {"figur": figur if figur["vorgang"] else None}})
    await s.start()
    try:
        t = await eins(s, befehl="tobie_auflegen", uid="04a1b2c3")
        figur["vorgang"] = "echt0000"  # ein echter Leser hat gewechselt
        uhr.vor(10)
        a = await eins(s, befehl="anzeige")
        assert a["simuliert"] is None
        assert t["vorgang"] != "echt0000"
    finally:
        await s.stop()


async def test_anzeige_ohne_quelle_ist_ungueltig(kurz):
    s = Sim(kurz, lambda e: None, SimUhr())
    await s.start()
    try:
        assert (await eins(s, befehl="anzeige")) == {"ok": False, "fehler": "anzeige nicht verfuegbar"}
    finally:
        await s.stop()


# -- AP 4.8: Haken für Kopfhörer und Uhr, ``zeit`` ---------------------------------------------------------------


async def test_kopfhoerer_haken_ersetzt_das_eigene_ereignis(sim):
    gerufen = []
    sim.kopfhoerer_haken = gerufen.append
    assert await eins(sim, befehl="kopfhoerer", steckt=True) == {"ok": True}
    assert gerufen == [True] and sim.got == []  # das Ereignis kommt von der Buchse, nicht von ``sim``


async def test_alle_eingaenge_sind_verdrahtet(sim):
    assert all(sim_modul.VERDRAHTET.values())
    a = await eins(sim, befehl="anzeige")
    assert all(a["verdrahtet"].values())


async def test_zeit_ohne_haken_ist_nicht_verfuegbar(sim):
    assert await eins(sim, befehl="zeit", iso="2026-11-09T22:30:00+01:00") == {"ok": False, "fehler": "zeit_nicht_verfuegbar"}


async def test_zeit_stellt_ueber_den_haken(sim):
    gerufen = []
    sim.zeit_haken = lambda wall: gerufen.append(wall) or True
    a = await eins(sim, befehl="zeit", iso="2026-11-09T22:30:00+01:00")
    assert a["ok"] and gerufen == [a["wall"]] and a["wall"] == __import__("datetime").datetime.fromisoformat("2026-11-09T22:30:00+01:00").timestamp()
    assert (await eins(sim, befehl="zeit", iso=None))["ok"] and gerufen[-1] is None
    sim.zeit_haken = lambda wall: False
    assert await eins(sim, befehl="zeit", iso=None) == {"ok": False, "fehler": "zeit_nicht_verfuegbar"}


@pytest.mark.parametrize("zeile", [{"befehl": "zeit"}, {"befehl": "zeit", "iso": 5}, {"befehl": "zeit", "iso": "gestern"}, {"befehl": "zeit", "iso": " "}])
async def test_zeit_ungueltig(sim, zeile):
    sim.zeit_haken = lambda wall: True
    a = await eins(sim, **zeile)
    assert a["ok"] is False and a["fehler"] in ("iso fehlt", "iso ungueltig")


async def test_zeit_ohne_zone_gilt_die_ortszeit_des_rechners(sim):
    gerufen = []
    sim.zeit_haken = lambda wall: gerufen.append(wall) or True
    await eins(sim, befehl="zeit", iso="2026-11-09T22:30:00")
    from datetime import datetime

    assert gerufen == [datetime(2026, 11, 9, 22, 30).astimezone().timestamp()]
