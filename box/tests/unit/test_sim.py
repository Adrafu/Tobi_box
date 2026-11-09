"""``sim``: JSON-Zeilen über den Unix-Socket werden zu Ereignissen; ungültige Zeilen werden ignoriert."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import stat

import pytest

from tobibox import events as ev
from tobibox.clock import SimUhr
from tobibox.sim import Sim
from tobibox.store import KonfigStore

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def sim(kurz):
    got: list = []
    s = Sim(kurz, got.append, SimUhr())
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


async def test_socket_rechte_0600(sim):
    assert stat.S_IMODE(os.stat(sim.pfad).st_mode) == 0o600


async def test_learn_serie(sim):
    (a,) = await sende(sim, {"befehl": "learn", "typ": "serie", "serie": "s1", "ttl": 60})
    assert a == {"ok": True}
    (e,) = sim.got
    assert isinstance(e, ev.HaLernmodus) and e.befehl_id
    assert e.gueltig_bis == SimUhr().wall + 60
    assert sim.lernziel is None  # gilt erst, wenn die Box den Befehl angenommen hat
    sim.angenommen(e.befehl_id)
    assert sim.lernziel == {"typ": "serie", "serie": "s1"}


async def test_learn_folge(sim):
    await sende(sim, {"befehl": "learn", "typ": "folge", "serie": "s1", "folge": "a.mp3"})
    assert isinstance(sim.got[0], ev.HaLernmodus)
    sim.angenommen(sim.got[0].befehl_id)
    assert sim.lernziel == {"typ": "folge", "serie": "s1", "folge": "a.mp3"}


async def test_ack(sim):
    await sende(sim, {"befehl": "ack", "uid": "04a1b2c3", "zuletzt": "2026-11-05T09:12:03.412Z", "art": "unbekannt"})
    assert sim.got == [ev.Bestaetigt("04a1b2c3", "sim", "2026-11-05T09:12:03.412Z", "unbekannt")]


async def test_card_schreibt_config_und_meldet(sim, kurz):
    (a,) = await sende(sim, {"befehl": "card", "uid": "04a1b2c3", "ziel": {"typ": "aktion", "aktion": "status"}})
    assert a == {"ok": True}
    (e,) = sim.got
    assert isinstance(e, ev.KonfigGeladen)
    assert e.konfig.zuordnungen["04a1b2c3"] == ev.Zuordnung("aktion", aktion="status")
    k = KonfigStore(kurz)
    k.laden()
    assert k.konfig.revision == 1 and "04a1b2c3" in k.konfig.zuordnungen
    # zweite Karte: Revision steigt, erste bleibt
    await sende(sim, {"befehl": "card", "uid": "04a1b2c4", "ziel": {"typ": "serie", "serie": "s1"}})
    assert set(sim.got[-1].konfig.zuordnungen) == {"04a1b2c3", "04a1b2c4"}
    assert sim.got[-1].konfig.revision == 2


@pytest.mark.parametrize(
    "zeile",
    [
        "kein json",
        "[1,2]",
        {"befehl": "unbekannt"},
        {"befehl": "learn", "typ": "x", "serie": "s1"},
        {"befehl": "learn", "typ": "folge", "serie": "s1"},
        {"befehl": "learn", "typ": "serie", "serie": "s1", "ttl": 0},
        {"befehl": "ack", "uid": "u", "zuletzt": "z", "art": "falsch"},
        {"befehl": "ack", "uid": "u", "art": "gelernt"},
        {"befehl": "card", "uid": "KEINE UID", "ziel": {"typ": "serie", "serie": "s1"}},
        {"befehl": "card", "uid": "04a1b2c3"},
    ],
)
async def test_ungueltige_zeile_wird_ignoriert(sim, zeile, caplog):
    with caplog.at_level(logging.WARNING, logger="tobibox"):
        (a,) = await sende(sim, zeile)
    assert a["ok"] is False
    assert sim.got == []
    # protokolliert (AP 2.2): Warnung "zeile ungueltig" von sim, mit sim=true
    treffer = [r for r in caplog.records if getattr(r, "ereignis", "") == "zeile" and getattr(r, "ergebnis", "") == "ungueltig"]
    assert len(treffer) == 1 and treffer[0].levelname == "WARNING"
    assert getattr(treffer[0], "baustein", "") == "sim" and getattr(treffer[0], "sim", False) is True
    # Verbindung und Server leben weiter
    (b,) = await sende(sim, {"befehl": "ack", "uid": "u", "zuletzt": "z", "art": "gelernt"})
    assert b == {"ok": True} and len(sim.got) == 1


async def test_mehrere_zeilen_und_leerzeilen(sim):
    r, w = await asyncio.open_unix_connection(str(sim.pfad))
    w.write(b'\n{"befehl":"ack","uid":"a","zuletzt":"z","art":"gelernt"}\n{"befehl":"ack","uid":"b","zuletzt":"z","art":"gelernt"}\n')
    await w.drain()
    await r.readline(); await r.readline()
    w.close()
    assert [e.id for e in sim.got] == ["a", "b"]


async def test_async_ausgabe_und_alter_socket(kurz):
    got = []

    async def aus(e):
        got.append(e)

    (kurz / "sim.sock").write_text("alt")
    s = Sim(kurz, aus, SimUhr())
    await s.start()
    try:
        await sende(s, {"befehl": "ack", "uid": "a", "zuletzt": "z", "art": "gelernt"})
        assert len(got) == 1
    finally:
        await s.stop()
    assert not s.pfad.exists()


async def test_learn_merkt_ziel_und_befehls_id_erst_wenn_die_box_angenommen_hat(sim):
    await sende(sim, {"befehl": "learn", "typ": "serie", "serie": "s1"})
    assert sim.lernbefehl_id is None and sim.lernziel is None
    sim.angenommen(sim.got[0].befehl_id)
    assert sim.lernbefehl_id == sim.got[0].befehl_id
    assert sim.lernziel == {"typ": "serie", "serie": "s1"}


async def test_zweiter_learn_den_die_box_ignoriert_laesst_den_ersten_lernlauf_unveraendert(sim):
    await sende(sim, {"befehl": "learn", "typ": "serie", "serie": "s1"})
    sim.angenommen(sim.got[0].befehl_id)
    await sende(sim, {"befehl": "learn", "typ": "serie", "serie": "s2"})  # die Box ignoriert ihn: nie angenommen
    assert sim.lernbefehl_id == sim.got[0].befehl_id != sim.got[1].befehl_id
    assert sim.lernziel == {"typ": "serie", "serie": "s1"}


async def test_nicht_angenommene_befehle_wachsen_nicht_unbegrenzt(sim):
    for _ in range(20):
        await sende(sim, {"befehl": "learn", "typ": "serie", "serie": "s1"})
    assert len(sim._vorgemerkt) <= 8


async def test_learn_ueberschreiben_wird_gemerkt_und_muss_ein_bool_sein(sim):
    await sende(sim, {"befehl": "learn", "typ": "serie", "serie": "s1", "ueberschreiben": True})
    sim.angenommen(sim.got[0].befehl_id)
    assert sim.ueberschreiben is True
    (a,) = await sende(sim, {"befehl": "learn", "typ": "serie", "serie": "s1", "ueberschreiben": "ja"})
    assert a["ok"] is False


async def test_learn_abort(sim):
    (a,) = await sende(sim, {"befehl": "learn_abort"})
    assert a == {"ok": True}
    (e,) = sim.got
    assert isinstance(e, ev.HaLernmodusAbbruch) and e.befehl_id and e.gueltig_bis == SimUhr().wall + 30


async def test_status_antwortet_mit_der_auskunft_des_dienstes_und_macht_kein_ereignis(kurz):
    got: list = []
    s = Sim(kurz, got.append, SimUhr(), auskunft=lambda: {"status": {"zustand": "leer"}, "offen": []})
    await s.start()
    try:
        (a,) = await sende(s, {"befehl": "status"})
    finally:
        await s.stop()
    assert a == {"ok": True, "status": {"zustand": "leer"}, "offen": []} and got == []


async def test_status_ohne_auskunft_ist_ungueltig(sim):
    (a,) = await sende(sim, {"befehl": "status"})
    assert a["ok"] is False and sim.got == []


async def test_card_nutzt_den_gemeinsamen_konfig_store(kurz):
    k = KonfigStore(kurz)
    s = Sim(kurz, lambda e: None, SimUhr(), k)
    await s.start()
    try:
        await sende(s, {"befehl": "card", "uid": "04a1b2c3", "ziel": {"typ": "folge", "serie": "s1", "folge": "a.mp3"}})
    finally:
        await s.stop()
    assert k.konfig.zuordnungen["04a1b2c3"] == ev.Zuordnung("folge", "s1", "a.mp3")  # derselbe Store sieht es sofort


async def test_socket_wird_ohne_umask_aenderung_mit_0600_angelegt(kurz):
    vorher = os.umask(0o022)
    try:
        s = Sim(kurz, lambda e: None, SimUhr())
        await s.start()
        try:
            assert stat.S_IMODE(os.stat(s.pfad).st_mode) == 0o600
            assert os.umask(0o022) == 0o022  # die Prozess-umask blieb, wie sie war
        finally:
            await s.stop()
    finally:
        os.umask(vorher)


async def test_zu_langer_pfad_wirft_oserror_und_hinterlaesst_nichts(kurz):
    s = Sim(kurz / ("x" * 100), lambda e: None, SimUhr())
    with pytest.raises(OSError):
        await s.start()
    await s.stop()  # darf nichts werfen


async def test_zu_langer_pfad_nennt_laenge_grenze_und_abhilfe(kurz):
    s = Sim(kurz / ("x" * 100), lambda e: None, SimUhr())
    with pytest.raises(OSError, match=r"Socket-Pfad zu lang \(\d+ Bytes, erlaubt höchstens \d+") as info:
        await s.start()
    assert "zustand" in str(info.value)


async def test_stop_ohne_start_laesst_ein_fremdes_sock_in_ruhe(kurz):
    (kurz / "sim.sock").write_text("fremd")
    await Sim(kurz, lambda e: None, SimUhr()).stop()
    assert (kurz / "sim.sock").exists()


async def test_card_laeuft_in_einem_thread_und_schreibt_trotzdem_die_zuordnung(sim, kurz):
    await sende(sim, {"befehl": "card", "uid": "04a1b2c3", "ziel": {"typ": "serie", "serie": "s1"}})
    assert isinstance(sim.got[0], ev.KonfigGeladen)
