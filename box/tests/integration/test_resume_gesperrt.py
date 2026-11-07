"""Dienst-Neustart mit gesperrtem Tobie (Entscheidung G, 06.11.): echter Dienst, ``fake_reader lock``.

Der Dienst wird sanft beendet (SIGINT, schreibt ``lauf.json``) und neu gestartet; die Kennung des Starts bleibt.
Die Überraschung läuft beim ersten Auflegen, nach dem Neustart bleibt es still.
"""

from __future__ import annotations

import asyncio
import json
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import app_welt

from integration.test_app_e2e import mpd_status, warte
from integration.test_resume_neustart import SERIE, aufraeumen, leser_bereit, starte_dienst

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader

from tobibox import events as ev


@pytest.fixture
def welt(mpd, tmp_path):
    w = app_welt(mpd, tmp_path, {"04a1b2c3": ev.Zuordnung("serie", SERIE)}, {"rabe": (SERIE, ["folge-01.wav"], 30.0)})
    w["log"] = tmp_path / "log" / "tobibox.log"
    with open(w["toml"], "a", encoding="utf-8") as f:
        f.write(f'[protokoll]\nziel = "datei"\ndatei = "{w["log"]}"\nebene = "DEBUG"\n')
    return w


async def _state(port: int) -> str:
    return (await mpd_status(port))["state"]


async def _ist(port: int, wert: str) -> bool:
    return await _state(port) == wert


async def test_gesperrt_dienst_neustart_bleibt_pausiert(welt):
    mpd = welt["mpd"]
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        proc = starte_dienst(welt)
        proc2 = None
        try:
            await leser_bereit(fr)
            fr.lock()
            await warte(lambda: _ist(mpd.port, "play"), 10.0, "(Überraschung spielt)")
            proc.send_signal(signal.SIGINT)
            assert proc.wait(15) is not None
            marker = json.loads((welt["zustand"] / "lauf.json").read_text())
            assert marker["uid"] is None and marker["gesperrt"] is True

            proc2 = starte_dienst(welt)
            n = len(fr.empfangen)
            await warte(lambda: "PING" in fr.empfangen[n:], 10.0, "(Leser verbunden, Neustart)")
            await asyncio.sleep(2.0)
            assert await _state(mpd.port) != "play"  # nichts startet von selbst
            zeilen = welt["log"].read_text(encoding="utf-8").splitlines()
            i = max(k for k, z in enumerate(zeilen) if "dienst_neustart" in z and "pausiert" in z)
            assert not any("spielt" in z for z in zeilen[i:])  # nach dem Neustart startet keine Wiedergabe
        finally:
            aufraeumen(proc)
            if proc2 is not None:
                aufraeumen(proc2)
