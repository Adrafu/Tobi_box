#!/usr/bin/env python3
"""Messt die Dienstzeit ohne Hardware: ``fake_reader`` (PLACED/REMOVED) -> Dienst -> echtes MPD.

Startet ein eigenes MPD (Null-Ausgabe, ``tests/fixtures/mpd.test.conf``), die echte ``App`` und den falschen
Leser und wiederholt Auflegen und Abheben. Je Wiederholung (alle Zeiten in ms, Uhr: ``time.monotonic``):

* ``Zeile -> aufgelegt``      vom Schreiben der Zeile durch den Leser bis zum Protokolleintrag ``aufgelegt``
  (Übertragung am Pseudo-Terminal, Lesen, Zeilenprüfung, Ereignisschlange);
* ``aufgelegt -> abspielen``  Zuordnung, Zeiger laden, Befehl (Protokoll: ``abspielen``);
* ``abspielen -> play``       Befehl ausführen bis MPD ``state: play`` meldet (Abfrage alle 5 ms);
* ``Summe``                   vom Schreiben der Zeile bis ``play``.
Beim Abheben entsprechend ``Zeile -> abgehoben``, ``-> pausieren`` und ``-> pause``.

Das sind Werte aus dem Container oder vom Mac ohne Tonausgabe. Die Grenzen gelten am Ausgang
(``measure_audio_latency.py``); dieses Skript misst nur den Anteil des Dienstes und von MPD.

    python box/tools/measure_service_latency.py --n 20
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path[:0] = [str(HIER), str(HIER.parent / "tests")]

import fake_reader  # noqa: E402
from conftest import app_welt  # noqa: E402
from integration.conftest import MPD, TestMpd  # noqa: E402
from mpd.asyncio import MPDClient  # noqa: E402

from tobibox import config as konfig_modul  # noqa: E402
from tobibox import eventlog  # noqa: E402
from tobibox import events as ev  # noqa: E402
from tobibox.app import App  # noqa: E402

UID = "04a1b2c3"
SERIE = "3f9a1c07b2d4"


class Fang:
    """Merkt sich, wann der Dienst eine Protokollzeile schreibt (Uhr wie ``time.monotonic``)."""

    def __init__(self) -> None:
        import logging

        self.zeiten: dict[str, float] = {}
        fang = self

        class H(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                name = getattr(record, "ereignis", None)
                if name in ("aufgelegt", "abgehoben", "abspielen", "abspielen_fertig", "pausieren", "pausieren_fertig"):
                    fang.zeiten[name] = time.monotonic()

        eventlog.logger().addHandler(H())
        eventlog.logger().setLevel(logging.INFO)
        eventlog.logger().propagate = False


async def warte_zustand(client: MPDClient, soll: str, timeout: float = 5.0) -> float:
    ende = time.monotonic() + timeout
    while time.monotonic() < ende:
        if (await client.status())["state"] == soll:
            return time.monotonic()
        await asyncio.sleep(0.005)
    raise TimeoutError(soll)


async def messe(n: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        mpd = TestMpd(tmp_path / "mpd")
        mpd.start()
        try:
            welt = app_welt(mpd, tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, {"rabe": (SERIE, ["f1.wav", "f2.wav"], 60.0)})
            fang = Fang()
            ergebnis: dict[str, list[float]] = {k: [] for k in (
                "zeile_aufgelegt", "aufgelegt_abspielen", "abspielen_fertig", "abspielen_play", "auflegen_summe",
                "zeile_abgehoben", "abgehoben_pausieren", "pausieren_pause", "abheben_summe")}
            with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
                app = App(konfig_modul.lade(welt["toml"]), melde_bereit=False)
                await app.starte()
                client = MPDClient()
                await client.connect("127.0.0.1", mpd.port)
                try:
                    while "PING" not in fr.empfangen:
                        await asyncio.sleep(0.05)
                    await asyncio.sleep(1.0)
                    for _ in range(n):
                        fang.zeiten.clear()
                        t0 = time.monotonic()
                        fr.place(UID)
                        t_play = await warte_zustand(client, "play")
                        await asyncio.sleep(0.3)
                        z = fang.zeiten
                        ergebnis["zeile_aufgelegt"].append((z["aufgelegt"] - t0) * 1000)
                        ergebnis["aufgelegt_abspielen"].append((z["abspielen"] - z["aufgelegt"]) * 1000)
                        ergebnis["abspielen_fertig"].append((z["abspielen_fertig"] - z["abspielen"]) * 1000)
                        ergebnis["abspielen_play"].append((t_play - z["abspielen"]) * 1000)
                        ergebnis["auflegen_summe"].append((t_play - t0) * 1000)
                        await asyncio.sleep(0.5)
                        fang.zeiten.clear()
                        t0 = time.monotonic()
                        fr.remove()
                        t_pause = await warte_zustand(client, "pause")
                        await asyncio.sleep(0.3)
                        z = fang.zeiten
                        ergebnis["zeile_abgehoben"].append((z["abgehoben"] - t0) * 1000)
                        ergebnis["abgehoben_pausieren"].append((z["pausieren"] - z["abgehoben"]) * 1000)
                        ergebnis["pausieren_pause"].append((t_pause - z["pausieren"]) * 1000)
                        ergebnis["abheben_summe"].append((t_pause - t0) * 1000)
                        await asyncio.sleep(0.2)
                finally:
                    client.disconnect()
                    await app.beende()
        finally:
            mpd.stop()
    return {k: {"n": len(v), "min": round(min(v), 1), "median": round(statistics.median(v), 1), "max": round(max(v), 1)}
            for k, v in ergebnis.items()}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=20, help="Wiederholungen (20)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if MPD is None:
        print("measure_service_latency: mpd ist nicht installiert", file=sys.stderr)
        return 2
    erg = asyncio.run(messe(a.n))
    if a.json:
        print(json.dumps(erg, indent=2))
    else:
        for k, v in erg.items():
            print(f"{k:22} n={v['n']:3} min {v['min']:7.1f}  median {v['median']:7.1f}  max {v['max']:7.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
