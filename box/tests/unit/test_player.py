"""Player gegen einen Fake-Client: Fehlerpfade, die ein echtes MPD kaum auslöst."""

from __future__ import annotations

import pytest
from mpd import CommandError

from tobibox import events as ev
from tobibox import player as player_modul
from tobibox.player import Player


class FakeClient:
    def __init__(self, zustaende=("play",), pause_fehler=False, setvol_fehler=False, connect_fehler=None, volume=50):
        self.zustaende = list(zustaende)
        self.pause_fehler = pause_fehler
        self.setvol_fehler = setvol_fehler
        self.connect_fehler = connect_fehler
        self.volume = volume
        self.aufrufe: list[str] = []
        self.getrennt = 0

    async def connect(self, host, port):
        self.aufrufe.append("connect")
        if self.connect_fehler:
            raise self.connect_fehler

    def disconnect(self):
        self.getrennt += 1

    async def status(self):
        z = self.zustaende[0] if len(self.zustaende) == 1 else self.zustaende.pop(0)
        return {"state": z, "volume": str(self.volume), "elapsed": "3.0", "duration": "30.0"}

    async def pause(self, n):
        self.aufrufe.append("pause")
        if self.pause_fehler:
            raise CommandError("boom")

    async def stop(self):
        self.aufrufe.append("stop")

    async def setvol(self, v):
        self.aufrufe.append(f"setvol {v}")
        if self.setvol_fehler:
            raise CommandError("setvol kaputt")
        self.volume = v

    async def repeat(self, n): ...
    async def random(self, n): ...
    async def single(self, n): ...
    async def consume(self, n): ...


def mk(client, **kw):
    e: list = []
    p = Player(e.append, **kw)
    p._client = client
    p._verbunden = True
    p._serie, p._datei, p._phase = "s", "a.wav", "spielt"
    return p, e


async def test_pause_fehler_und_gestoppt_ist_folgenende():
    c = FakeClient(zustaende=("play", "stop"), pause_fehler=True)
    p, e = mk(c)
    await p._pausieren()
    assert any(isinstance(x, ev.FolgeZuEnde) for x in e)
    assert not any(isinstance(x, ev.PlayerFehler) for x in e)


async def test_pause_fehler_und_weiter_spielend_bleibt_fehler():
    c = FakeClient(zustaende=("play", "play"), pause_fehler=True)
    p, e = mk(c)
    await p.pausieren(ev.Pausieren("knopf"))
    assert [x.art for x in e if isinstance(x, ev.PlayerFehler)] == ["mpd_fehler"]


async def test_klemmung_scheitert_loggt_einmal_und_pausiert(caplog):
    c = FakeClient(setvol_fehler=True, volume=90)
    p, e = mk(c)
    p._prozent, p._grenze = 20, 30
    for _ in range(3):
        await p._abfrage_schritt()
    assert c.aufrufe.count("pause") == 3
    fehler = [r for r in caplog.records if r.levelname == "ERROR" and getattr(r, "ereignis", "") == "lautstaerke_geklemmt"]
    assert len(fehler) == 1


async def test_fehlgeschlagenes_verbinden_trennt_den_client(monkeypatch):
    c = FakeClient(connect_fehler=ConnectionError("nein"))
    monkeypatch.setattr(player_modul, "MPDClient", lambda: c)
    p = Player(lambda e: None)
    with pytest.raises(ConnectionError):
        await p._verbinde()
    assert c.getrennt >= 1 and p._client is None and not p.verbunden


async def test_fehlgeschlagene_sicherung_beim_verbinden_trennt_ebenfalls(monkeypatch):
    c = FakeClient(zustaende=("pause",), setvol_fehler=True)
    monkeypatch.setattr(player_modul, "MPDClient", lambda: c)
    p = Player(lambda e: None)
    with pytest.raises(CommandError):
        await p._verbinde()
    assert c.getrennt >= 1 and not p.verbunden


async def test_verbinden_pausiert_zuerst_und_setzt_lautstaerke_0_ohne_grenze(monkeypatch):
    c = FakeClient(zustaende=("play",))
    monkeypatch.setattr(player_modul, "MPDClient", lambda: c)
    p = Player(lambda e: None)
    await p._verbinde()
    assert c.aufrufe[:3] == ["connect", "pause", "setvol 0"]
