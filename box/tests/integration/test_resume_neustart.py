"""Resume nach hartem Ende des Dienstes (SIGKILL), AP 2.1.

Echter Dienst als eigener Prozess (``python -m tobibox``) mit ``fake_reader`` und echtem MPD. Der Dienst
wird mitten in der Wiedergabe mit SIGKILL beendet (Stromausfall-Ersatz: kein Abheben, kein Speichern
beim Beenden) und neu gestartet. Der Zeiger ist da, höchstens 30 s Wiedergabe sind verloren
(``data-model.md``: Zeiger alle 30 s während der Wiedergabe, Entscheidung zur Stromausfall-Grenze).
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import app_welt

from integration.test_app_e2e import mpd_status, warte

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader

from tobibox import events as ev

UID = "04a1b2c3"
SERIE = "3f9a1c07b2d4"
GRENZE_S = 30.0


@pytest.fixture
def welt(mpd, tmp_path):
    return app_welt(mpd, tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, {"rabe": (SERIE, ["folge-01.wav", "folge-02.wav"], 120.0)})


def starte_dienst(welt) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "tobibox", "--config", str(welt["toml"])],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "NOTIFY_SOCKET": ""},
    )


def beende_hart(proc: subprocess.Popen) -> None:
    proc.send_signal(signal.SIGKILL)
    assert proc.wait(10) == -signal.SIGKILL


def zeiger(welt) -> dict | None:
    try:
        return json.loads((welt["zustand"] / "resume.json").read_text())["serien"][SERIE]
    except (OSError, KeyError, ValueError):
        return None


async def _spielt(port: int) -> bool:
    return (await mpd_status(port))["state"] == "play"


async def _elapsed_ab(port: int, sek: float) -> bool:
    st = await mpd_status(port)
    return st["state"] == "play" and float(st.get("elapsed", 0)) >= sek


async def leser_bereit(fr) -> None:
    await warte(lambda: "PING" in fr.empfangen, 10.0, "(Leser verbunden)")
    await asyncio.sleep(0.8)


def aufraeumen(proc: subprocess.Popen) -> str:
    if proc.poll() is None:
        proc.kill()
    return proc.stdout.read() if proc.stdout else ""


async def test_sigkill_waehrend_der_wiedergabe_zeiger_da_hoechstens_30_s_verloren(welt):
    mpd = welt["mpd"]
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        proc = starte_dienst(welt)
        proc2 = None
        try:
            await leser_bereit(fr)
            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 10.0, "(spielt)")
            # die periodische Speicherung (alle 30 s) schreibt den Zeiger, ohne dass abgehoben wird
            await warte(lambda: zeiger(welt) is not None, 45.0, "(Zeiger ohne Abheben gespeichert)")
            await warte(lambda: _elapsed_ab(mpd.port, 33.0), 20.0, "(33 s gespielt)")
            vor_kill = float((await mpd_status(mpd.port))["elapsed"])
            beende_hart(proc)

            z = zeiger(welt)
            assert z is not None and z["folge"] == "folge-01.wav"
            gespeichert = float(z["position_s"])
            assert gespeichert > 0.0
            verloren = vor_kill - gespeichert
            assert 0.0 <= verloren <= GRENZE_S, (vor_kill, gespeichert)

            # Neustart des Dienstes; derselbe Tobie liegt noch (Leser meldet ihn nach dem PING erneut)
            proc2 = starte_dienst(welt)
            n = len(fr.empfangen)
            await warte(lambda: "PING" in fr.empfangen[n:], 10.0, "(Leser verbunden, Neustart)")
            await asyncio.sleep(1.5)
            # Dienst-Neustart mit liegendem Tobie: nichts startet von selbst (Entscheidung G)
            assert (await mpd_status(mpd.port))["state"] == "pause"  # der alte Ton läuft nicht weiter
            # Abheben und wieder Auflegen: Wiedergabe setzt am Zeiger fort, 3 s zurück
            fr.remove()
            await asyncio.sleep(0.5)
            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 10.0, "(spielt nach dem Neustart)")
            st = await mpd_status(mpd.port)
            nach_hebe = zeiger(welt)
            assert nach_hebe is not None
            ziel = float(nach_hebe["position_s"]) - 3.0
            assert ziel - 0.5 <= float(st["elapsed"]) <= ziel + 3.0, (st["elapsed"], ziel)
            assert vor_kill - float(st["elapsed"]) <= GRENZE_S + 3.0 + 2.0  # verloren: Intervall plus Rücksprung
            assert st["song"] == "0"
            beende_hart(proc2)
        finally:
            aufraeumen(proc)
            if proc2 is not None:
                aufraeumen(proc2)


async def test_sigkill_nach_abheben_und_auflegen_zeiger_ist_da(welt):
    """Kurz gehört, abgehoben (Zeiger gespeichert), wieder aufgelegt, dann hart beendet."""
    mpd = welt["mpd"]
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        proc = starte_dienst(welt)
        try:
            await leser_bereit(fr)
            fr.place(UID)
            await warte(lambda: _elapsed_ab(mpd.port, 5.0), 15.0, "(5 s gespielt)")
            fr.remove()
            await warte(lambda: zeiger(welt) is not None, 5.0, "(Zeiger gespeichert)")
            gespeichert = float(zeiger(welt)["position_s"])
            assert gespeichert >= 4.0
            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 8.0, "(spielt wieder)")
            beende_hart(proc)
            z = zeiger(welt)
            assert z is not None and float(z["position_s"]) == pytest.approx(gespeichert)  # Zeiger unverändert da
        finally:
            aufraeumen(proc)
