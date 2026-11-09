"""Nie zwei Dinge gleichzeitig (Entscheidung L, 09.11.) mit echtem MPD, ``fake_reader`` und echter ``App``.

Das Ton-Kommando ist eine Attrappe: ``sleep 1.5`` (``[toene] kommando``). Die Dauer eines Tons ist das
Ende dieses Prozesses; so steuert der Test, wie lange ein Ton dauert.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import app_welt
from integration.test_app_e2e import _spielt, mpd_status, warte

from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox.app import App

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader  # noqa: E402

SERIE = "3f9a1c07b2d4"
UEBERRASCHUNG = "c07d2e91a45b"
UID_FOLGE = "04a1b2c3"  # Folge-Tobie: folge-01.wav der Serie rabe (ein Track)
UID_NEU = "04ffeedd"  # unbekannt: Ton ``unbekannt`` und Überraschungs-Serie
TON_S = 1.5


@pytest.fixture
def welt(mpd, tmp_path):
    w = app_welt(mpd, tmp_path, {UID_FOLGE: ev.Zuordnung("folge", SERIE, "folge-01.wav")})
    toml = w["toml"]
    text = toml.read_text()
    assert '[toene]\nkommando = ["true", "{datei}"]\n' in text
    toml.write_text(text.replace('kommando = ["true", "{datei}"]', f'kommando = ["sleep", "{TON_S}"]'))
    return w


async def _bereit(app: App, fr) -> None:
    await warte(lambda: "PING" in fr.empfangen, 5.0, "(Leser verbunden)")
    await asyncio.sleep(0.8)  # die Altlast nach dem Öffnen wird verworfen
    await warte(lambda: not app.toene.beschaeftigt, 6.0, "(Startton zu Ende)")


async def _zustand(port: int) -> str:
    return (await mpd_status(port))["state"]


async def test_ton_vor_dem_hoerspiel_start_erst_nach_dem_ende_des_tons(welt):
    mpd = welt["mpd"]
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(welt["toml"]), melde_bereit=False)
        await app.starte()
        try:
            await _bereit(app, fr)
            fr.place(UID_NEU)
            t0 = time.monotonic()
            await warte(lambda: app.toene.beschaeftigt, 3.0, "(Ton beginnt)")
            while time.monotonic() - t0 < TON_S - 0.4:  # mitten im Ton: MPD spielt nicht
                assert await _zustand(mpd.port) != "play"
                await asyncio.sleep(0.1)
            await warte(lambda: _spielt(mpd.port), 6.0, "(Überraschung spielt)")
            assert time.monotonic() - t0 >= TON_S - 0.1  # erst nach dem Ende des Tons
            assert (await mpd_status(mpd.port))["playlistlength"] == "1"
            assert app.kern.session.serie_id == UEBERRASCHUNG
        finally:
            await app.beende()


async def test_abheben_waehrend_des_tons_startet_die_wiedergabe_nie(welt):
    mpd = welt["mpd"]
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(welt["toml"]), melde_bereit=False)
        await app.starte()
        try:
            await _bereit(app, fr)
            fr.place(UID_NEU)
            await warte(lambda: app.toene.beschaeftigt, 3.0, "(Ton beginnt)")
            await asyncio.sleep(0.3)
            fr.remove()
            await warte(lambda: app.kern.session.modus == "pausiert", 3.0, "(abgehoben)")
            ende = time.monotonic() + TON_S + 1.2  # über das Ende des Tons hinaus
            while time.monotonic() < ende:
                assert await _zustand(mpd.port) != "play"
                await asyncio.sleep(0.1)
            assert not app.toene.beschaeftigt  # der Ton lief zu Ende
        finally:
            await app.beende()


async def test_ton_waehrend_der_wiedergabe_pausiert_und_setzt_an_derselben_stelle_fort(welt):
    mpd = welt["mpd"]
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(welt["toml"]), melde_bereit=False)
        gespeichert: list[str] = []
        orig = app.resume.speichern
        app.resume.speichern = lambda b, mono: gespeichert.append(b.grund) or orig(b, mono)  # type: ignore[method-assign]
        await app.starte()
        try:
            await _bereit(app, fr)
            fr.place(UID_FOLGE)
            await warte(lambda: _spielt(mpd.port), 8.0, "(spielt Folge 1)")
            await asyncio.sleep(0.2)  # kein Ton beim Auflegen eines bekannten Tobies
            assert not app.toene.beschaeftigt
            await warte(lambda: _elapsed_ab(mpd.port, 4.0), 10.0, "(4 s gespielt)")
            app.ereignisse.put_nowait(ev.Weiter())  # letzter Track eines Folgen-Tobies: Hinweiston
            await warte(lambda: app.toene.beschaeftigt, 3.0, "(Hinweiston)")
            await warte(lambda: _zustand_ist(mpd.port, "pause"), 2.0, "(MPD für den Ton angehalten)")
            vor = float((await mpd_status(mpd.port))["elapsed"])
            await asyncio.sleep(0.5)
            assert await _zustand(mpd.port) == "pause" and app.toene.beschaeftigt  # während des Tons still
            assert app.kern.session.modus == "spielt"  # der Kern kennt keine Pause
            await warte(lambda: _spielt(mpd.port), TON_S + 3.0, "(nach dem Ton fortgesetzt)")
            nach = float((await mpd_status(mpd.port))["elapsed"])
            assert vor - 0.05 <= nach <= vor + 0.8, (vor, nach)  # genau dort, kein Rücksprung von 3 s
            assert (await mpd_status(mpd.port))["playlistlength"] == "1"  # kein neues Abspielen
            assert "pause" not in gespeichert and not (welt["zustand"] / "resume.json").exists()
            assert app.kern.session.modus == "spielt"
        finally:
            await app.beende()


async def test_abheben_waehrend_des_tons_bei_laufender_wiedergabe_setzt_nicht_fort(welt):
    mpd = welt["mpd"]
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(welt["toml"]), melde_bereit=False)
        await app.starte()
        try:
            await _bereit(app, fr)
            fr.place(UID_FOLGE)
            await warte(lambda: _elapsed_ab(mpd.port, 2.0), 10.0, "(2 s gespielt)")
            app.ereignisse.put_nowait(ev.Weiter())
            await warte(lambda: _zustand_ist(mpd.port, "pause"), 3.0, "(MPD für den Ton angehalten)")
            fr.remove()
            await warte(lambda: app.kern.session.modus == "pausiert", 3.0, "(abgehoben)")
            await warte(lambda: not app.toene.beschaeftigt, TON_S + 2.0, "(Ton zu Ende)")
            await asyncio.sleep(0.5)
            assert await _zustand(mpd.port) == "pause"  # echte Pause, nichts wurde fortgesetzt
            await warte(lambda: (welt["zustand"] / "resume.json").exists(), 3.0, "(Zeiger der echten Pause)")
        finally:
            await app.beende()


async def test_haengender_ton_blockiert_die_wiedergabe_nicht(welt):
    mpd = welt["mpd"]
    toml = welt["toml"]
    toml.write_text(toml.read_text().replace(f'["sleep", "{TON_S}"]', '["sleep", "60"]'))
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(toml), melde_bereit=False)
        app.toene.ton_max_s = 0.6
        await app.starte()
        try:
            await warte(lambda: "PING" in fr.empfangen, 5.0, "(Leser verbunden)")
            await asyncio.sleep(0.8)
            await warte(lambda: not app.toene.beschaeftigt, 4.0, "(Startton abgebrochen)")
            fr.place(UID_NEU)
            t0 = time.monotonic()
            await warte(lambda: _spielt(mpd.port), 6.0, "(Überraschung spielt trotz hängendem Ton)")
            assert 0.5 <= time.monotonic() - t0 < 4.0
        finally:
            await app.beende()
    assert subprocess.run(["pgrep", "-f", "^sleep 60$"], capture_output=True).returncode != 0  # beendet, nicht liegengelassen


async def _zustand_ist(port: int, soll: str) -> bool:
    return (await mpd_status(port))["state"] == soll


async def _elapsed_ab(port: int, sek: float) -> bool:
    st = await mpd_status(port)
    return st["state"] == "play" and float(st.get("elapsed", 0)) >= sek
