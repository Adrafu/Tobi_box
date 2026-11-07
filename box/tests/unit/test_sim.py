"""``sim``: JSON-Zeilen über den Unix-Socket werden zu Ereignissen; ungültige Zeilen werden ignoriert."""

from __future__ import annotations

import asyncio
import json
import os
import stat

import pytest

from tobibox import events as ev
from tobibox.clock import SimUhr
from tobibox.sim import Sim
from tobibox.store import KonfigStore

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def sim(tmp_path):
    got: list = []
    s = Sim(tmp_path, got.append, SimUhr())
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
    assert sim.lernziel == {"typ": "serie", "serie": "s1"}


async def test_learn_folge(sim):
    await sende(sim, {"befehl": "learn", "typ": "folge", "serie": "s1", "folge": "a.mp3"})
    assert isinstance(sim.got[0], ev.HaLernmodus)
    assert sim.lernziel == {"typ": "folge", "serie": "s1", "folge": "a.mp3"}


async def test_ack(sim):
    await sende(sim, {"befehl": "ack", "uid": "04a1b2c3", "zuletzt": "2026-11-05T09:12:03.412Z", "art": "unbekannt"})
    assert sim.got == [ev.Bestaetigt("04a1b2c3", "sim", "2026-11-05T09:12:03.412Z", "unbekannt")]


async def test_card_schreibt_config_und_meldet(sim, tmp_path):
    (a,) = await sende(sim, {"befehl": "card", "uid": "04a1b2c3", "ziel": {"typ": "aktion", "aktion": "status"}})
    assert a == {"ok": True}
    (e,) = sim.got
    assert isinstance(e, ev.KonfigGeladen)
    assert e.konfig.zuordnungen["04a1b2c3"] == ev.Zuordnung("aktion", aktion="status")
    k = KonfigStore(tmp_path)
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
    (a,) = await sende(sim, zeile)
    assert a["ok"] is False
    assert sim.got == []
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


async def test_async_ausgabe_und_alter_socket(tmp_path):
    got = []

    async def aus(e):
        got.append(e)

    (tmp_path / "sim.sock").write_text("alt")
    s = Sim(tmp_path, aus, SimUhr())
    await s.start()
    try:
        await sende(s, {"befehl": "ack", "uid": "a", "zuletzt": "z", "art": "gelernt"})
        assert len(got) == 1
    finally:
        await s.stop()
    assert not s.pfad.exists()
