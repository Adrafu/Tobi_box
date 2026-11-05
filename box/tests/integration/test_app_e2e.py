"""Ende-zu-Ende: App mit ``fake_reader`` (Pseudo-Terminal) und echtem MPD.

Auflegen spielt Folge 1, Abheben pausiert und speichert den Zeiger, erneutes
Auflegen setzt 3 s vor der gespeicherten Stelle fort.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fixtures import audio
from mpd.asyncio import MPDClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader  # noqa: E402

from tobibox import config as konfig_modul  # noqa: E402
from tobibox import events as ev  # noqa: E402
from tobibox import store  # noqa: E402
from tobibox.app import App  # noqa: E402

UID = "04a1b2c3"
SERIE = "3f9a1c07b2d4"
FOLGE = "folge-01.wav"


async def warte(bedingung, timeout: float = 10.0, text: str = "") -> None:
    ende = time.monotonic() + timeout
    while time.monotonic() < ende:
        wert = bedingung()
        if asyncio.iscoroutine(wert):
            wert = await wert
        if wert:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"Bedingung nicht rechtzeitig erfüllt {text}")


async def mpd_status(port: int) -> dict:
    # MPD (Null-Ausgabe) antwortet nach dem Pausieren selten einmal nicht rechtzeitig
    # (auch ohne Änderung der Box-Software beobachtet): einmal wiederholen.
    for versuch in (1, 2):
        c = MPDClient()
        try:
            await c.connect("127.0.0.1", port)
            return dict(await c.status())
        except ConnectionError:
            if versuch == 2:
                raise
        finally:
            c.disconnect()
    raise AssertionError("unerreichbar")


@pytest.fixture
def welt(mpd, tmp_path):
    """Medien (im MPD-Ordner), Zuordnung UID -> Serie, Zustandsordner, Konfiguration."""
    audio.erzeuge_serie(mpd.medien, "rabe", [FOLGE, "folge-02.wav"], serie_id=SERIE, name="Rabe", dauer_s=40.0)
    mpd.aktualisiere()
    zustand = tmp_path / "var"
    zustand.mkdir()
    k = ev.Konfig(
        1, "a3f9c1e07b2d4856", {UID: ev.Zuordnung("serie", SERIE)}, ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60)
    )
    roh = {**store.konfig_zu_json(k), "ton_pegel": 40, "hinweis_pegel": 15}
    store.schreibe_atomar(zustand / "config.json", roh)
    link = tmp_path / "leser" / "ttyACM0"
    toml = tmp_path / "tobibox.toml"
    toml.write_text(
        f"""
[pfade]
zustand = "{zustand}"
medien = "{mpd.medien}"

[leser]
geraet = "{link}"

[mpd]
host = "127.0.0.1"
port = {mpd.port}

[lautstaerke]
max = 50
start = 20
kopfhoerer = 30

[toene]
kommando = ["true", "{{datei}}"]
"""
    )
    return {"zustand": zustand, "link": link, "toml": toml, "mpd": mpd}


def resume_zeiger(zustand: Path) -> dict:
    return json.loads((zustand / "resume.json").read_text())


async def test_auflegen_abheben_wieder_auflegen(welt):
    mpd = welt["mpd"]
    kfg = konfig_modul.lade(welt["toml"])
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(kfg, melde_bereit=False)
        await app.starte()
        try:
            await warte(lambda: "PING" in fr.empfangen, 5.0, "(Leser verbunden)")
            await asyncio.sleep(0.8)  # die Altlast nach dem Öffnen wird verworfen

            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 8.0, "(spielt Folge 1)")
            st = await mpd_status(mpd.port)
            assert int(st["volume"]) == 20  # vor dem ersten Abspielen gesetzt, unter der Grenze 50
            assert st["playlistlength"] == "1"
            assert app.kern.session.datei == FOLGE

            # etwas hören, dann abheben
            await warte(lambda: _elapsed_ab(mpd.port, 5.0), 10.0, "(5 s gespielt)")
            fr.remove()
            await warte(lambda: _zustand_ist(mpd.port, "pause"), 5.0, "(pausiert)")
            await warte(lambda: (welt["zustand"] / "resume.json").exists(), 5.0, "(Zeiger gespeichert)")
            zeiger = _zeiger(welt["zustand"])
            assert zeiger["folge"] == FOLGE
            gespeichert = float(zeiger["position_s"])
            assert gespeichert >= 4.0

            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 8.0, "(spielt wieder)")
            st = await mpd_status(mpd.port)
            erwartet = gespeichert - 3.0  # 3 s Rücksprung
            assert erwartet - 0.3 <= float(st["elapsed"]) <= erwartet + 2.5, (st["elapsed"], erwartet)
            assert st["playlistlength"] == "1"
        finally:
            await app.beende()
    # sauberes Ende: MPD pausiert
    assert (await mpd_status(mpd.port))["state"] == "pause"


def _zeiger(zustand: Path) -> dict:
    roh = resume_zeiger(zustand)
    return roh["serien"][SERIE]


async def _spielt(port: int) -> bool:
    return (await mpd_status(port))["state"] == "play"


async def _zustand_ist(port: int, soll: str) -> bool:
    return (await mpd_status(port))["state"] == soll


async def _elapsed_ab(port: int, sek: float) -> bool:
    st = await mpd_status(port)
    return st["state"] == "play" and float(st.get("elapsed", 0)) >= sek


async def test_dienst_startet_ohne_simulation_und_endet_auf_sigterm(welt):
    mpd = welt["mpd"]
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        proc = subprocess.Popen(
            [sys.executable, "-m", "tobibox", "--config", str(welt["toml"])],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "NOTIFY_SOCKET": ""},
        )
        try:
            await warte(lambda: "PING" in fr.empfangen, 10.0, "(Leser verbunden)")
            await asyncio.sleep(0.8)
            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 10.0, "(spielt)")
            await asyncio.sleep(2.0)
            proc.send_signal(signal.SIGTERM)
            assert proc.wait(10) == 0
        finally:
            if proc.poll() is None:
                proc.kill()
            ausgabe = proc.stdout.read() if proc.stdout else ""
    zeilen = [json.loads(z) for z in ausgabe.splitlines() if z.startswith("{")]
    assert any(z.get("ereignis") == "bereit" for z in zeilen), ausgabe
    assert any(z.get("ereignis") == "ende" for z in zeilen), ausgabe
    assert (await mpd_status(mpd.port))["state"] == "pause"
    assert float(_zeiger(welt["zustand"])["position_s"]) >= 1.0
