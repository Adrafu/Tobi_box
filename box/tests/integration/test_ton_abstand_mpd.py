"""Abstand zwischen Tonende und Hörspiel mit echtem MPD (Befund Mac, 09.11.).

Gemessen wird vom Ende des Abspielprogramms eines Tons (Rückkehr des Starters in ``Toene``) bis zu dem
Augenblick, in dem MPD ``play`` meldet. Das Ton-Kommando ist eine Attrappe (``sleep``), die Zeit des
Abspielprogramms selbst (``afplay``/``aplay`` starten) steckt also nicht darin; sie gehört nicht zur Software der Box.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from integration.test_toene_mpd import UID_NEU, _bereit
from integration.test_toene_mpd import welt  # noqa: F401  (Fixture)
from mpd.asyncio import MPDClient

from tobibox import config as konfig_modul
from tobibox.app import App

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader  # noqa: E402

# Schranke: Weg Tonende -> `play` in MPD. Gemessen (Container, Null-Ausgabe, 09.11.) sind es 3 ms
# (Warteschlange leeren, `add`, `play`). Auf dem Pi 3A+ und bei einer vollen CI rechnen wir mit dem
# Zehn- bis Dreißigfachen; 0,25 s lässt dafür Raum und bleibt unter den gewünschten 0,3 s Gesamtabstand.
# Ein fest eingebautes Warten (zum Beispiel 0,5 s) würde der Test sicher fangen.
SCHRANKE_S = 0.25


async def test_hoerspiel_startet_kurz_nach_dem_tonende(welt):  # noqa: F811
    mpd = welt["mpd"]
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(welt["toml"]), melde_bereit=False)
        await app.starte()
        c = MPDClient()
        try:
            await _bereit(app, fr)
            ende: list[float] = []
            orig = app.toene._starter

            async def starter(k):
                await orig(k)
                ende.append(time.monotonic())

            app.toene._starter = starter
            await c.connect("127.0.0.1", mpd.port)
            fr.place(UID_NEU)  # Ton `unbekannt`, danach die Überraschungs-Serie
            beginn = None
            ende_zeit = time.monotonic() + 8.0
            while time.monotonic() < ende_zeit:
                if (await c.status())["state"] == "play":
                    beginn = time.monotonic()
                    break
                await asyncio.sleep(0.002)
            assert beginn is not None and ende, "Hörspiel startet nicht"
            abstand = beginn - ende[-1]
            print(f"\nABSTAND Tonende -> play: {abstand * 1000:.0f} ms")
            assert 0 <= abstand < SCHRANKE_S, abstand
        finally:
            c.disconnect()
            await app.beende()
