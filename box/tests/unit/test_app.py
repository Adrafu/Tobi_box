"""``App``: Start wartet auf MPD, Beenden ist robust (Fake-Player, kein MPD nötig)."""

from __future__ import annotations

import asyncio
import dataclasses
import logging

import pytest
from fixtures.audio import erzeuge_medien

from tobibox import app as app_modul
from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox.app import App


class FakePlayer:
    def __init__(self, verbunden=True, stop_fehler=False):
        self.verbunden = verbunden
        self.stop_fehler = stop_fehler
        self.aufrufe: list[str] = []
        self.beim_warten: list[str] = []
        self.app: App | None = None

    def start(self):
        self.aufrufe.append("start")

    async def warte_verbunden(self, timeout_s=5.0):
        self.aufrufe.append(f"warte {timeout_s}")
        await asyncio.sleep(0.05)  # die Ereignisschleife kommt zum Zug
        self.beim_warten = list(self.app.gesehen)  # type: ignore[union-attr]
        return self.verbunden

    async def pausiere_hart(self):
        self.aufrufe.append("pause_hart")
        return True

    async def stop(self):
        self.aufrufe.append("stop")
        if self.stop_fehler:
            raise RuntimeError("player kaputt")

    async def lautstaerke_setzen(self, *a):
        pass


class FakeLeser:
    def __init__(self, stop_fehler=False):
        self.stop_fehler = stop_fehler
        self.gestoppt = False

    def start(self):
        pass

    async def stop(self):
        self.gestoppt = True
        if self.stop_fehler:
            raise RuntimeError("leser kaputt")

    def ping(self):
        pass


class FakeToene:
    def __init__(self):
        self.gestoppt = False

    async def stop(self):
        self.gestoppt = True


@pytest.fixture
def app(tmp_path, monkeypatch):
    medien = erzeuge_medien(tmp_path / "medien")
    zustand = tmp_path / "var"
    zustand.mkdir()
    toml = tmp_path / "tobibox.toml"
    toml.write_text(f'[pfade]\nzustand = "{zustand}"\nmedien = "{medien}"\n', encoding="utf-8")
    monkeypatch.setattr(app_modul.notify, "stoppt", lambda: None)
    a = App(konfig_modul.lade(toml), melde_bereit=False)
    a.player = FakePlayer()
    a.player.app = a
    a.leser = FakeLeser()
    a.toene = FakeToene()
    a.gesehen = []
    orig = a.verarbeite

    def verarbeite(e):
        a.gesehen.append(type(e).__name__)
        return orig(e)

    a.verarbeite = verarbeite
    return a


def setze_modus(a: App, modus: str) -> None:
    teil = {**a.kern.teil, "session": dataclasses.replace(a.kern.session, modus=modus)}
    a.kern = dataclasses.replace(a.kern, teil=teil)


async def test_starte_wartet_auf_mpd_vor_bereit(app):
    await app.starte()
    try:
        assert app.player.aufrufe[1] == f"warte {app_modul.VERBINDEN_WARTEN_S}"
        assert app_modul.VERBINDEN_WARTEN_S == 10.0
        assert "GeraeteEinstellungen" in app.player.beim_warten
        assert "Bereit" not in app.player.beim_warten
        assert "Bereit" in app.gesehen
    finally:
        await app.beende()


async def test_starte_ohne_mpd_startet_trotzdem_mit_warnung(app, caplog):
    app.player.verbunden = False
    with caplog.at_level(logging.WARNING, logger="tobibox"):
        await app.starte()
    try:
        assert "Bereit" in app.gesehen and app.bereit.is_set()
        assert any(r.levelname == "WARNING" and getattr(r, "ereignis", "") == "start" for r in caplog.records)
    finally:
        await app.beende()


async def test_starte_fehler_raeumt_auf(app, monkeypatch):
    def kaputt(*a, **k):
        raise RuntimeError("medien kaputt")

    monkeypatch.setattr(app_modul.library, "lade_bibliothek", kaputt)
    with pytest.raises(RuntimeError):
        await app.starte()
    assert "stop" in app.player.aufrufe and "pause_hart" in app.player.aufrufe
    assert app.toene.gestoppt and app.leser.gestoppt


@pytest.mark.parametrize("modus", ["spielt", "unbekannt"])
async def test_beende_sendet_dienst_endet_nicht_herunterfahren(app, modus):
    setze_modus(app, modus)
    verarbeitet: list = []
    app.verarbeite = lambda e: verarbeitet.append(e) or ()
    app._aufgaben = [asyncio.create_task(app._ereignisschleife())]
    await app.beende()
    assert verarbeitet == [ev.DienstEndet()]
    assert not any(isinstance(e, (ev.HerunterfahrenAngefordert, ev.Herunterfahren)) for e in verarbeitet)
    assert "pause_hart" in app.player.aufrufe


@pytest.mark.parametrize("modus", ["leer", "pausiert"])
async def test_beende_sendet_hart_pause_auch_ohne_wiedergabe(app, modus):
    setze_modus(app, modus)
    await app.beende()
    assert "pause_hart" in app.player.aufrufe and "stop" in app.player.aufrufe


async def test_beende_schritte_laufen_unabhaengig(app):
    app.leser = FakeLeser(stop_fehler=True)
    app.player = FakePlayer(stop_fehler=True)
    await app.beende()
    assert "pause_hart" in app.player.aufrufe
    assert "stop" in app.player.aufrufe
    assert app.toene.gestoppt
