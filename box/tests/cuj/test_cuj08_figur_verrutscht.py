"""CUJ 8 (AP 1.6): Tobie am Rand oder kurz verrutscht, aus Sicht des Dienstes.

Die Firmware entprellt und prüft die Kennung (Lücke bis 1,0 s, ``REMOVE_AFTER_MS`` = 1100 ms,
mehrfach gleiche Lesung); die verfälschte Kennung prüfen die nativen Firmware-Tests (AP 1.1). Der Dienst
sieht deshalb nur: **keine Zeile** während der Lücke, danach höchstens dieselbe Kennung wieder.

Bewiesene Schritte von CUJ 8 (Then: keine Pause, kein Neustart, kein falsches Hörspiel):

* Lücke ohne Zeile (1,0 s, bei laufendem Takt und Herzschlägen): weder ``Pausieren`` noch ``Abspielen``;
  der Ton läuft ohne Unterbrechung.
* Herzschlag mit ``present=0`` einmal (kurzer Aussetzer in der Anzeige): keine Pause; erst zwei
  abweichende Herzschläge in Folge lösen einen ``LeserPing`` aus, auch dann pausiert nichts.
* Dieselbe Kennung wieder (``PLACED`` mit neuer Vorgangs-ID, weil ein ``REMOVED`` verloren ging): nichts
  geschieht, die Wiedergabe läuft weiter (Vertrag 9.4); die Vorgangs-ID wird nachgeführt.
* ``seq``-Lücke (verlorene Zeile) ändert nichts am Verhalten.
* Erst eine andere Kennung, nach ``REMOVED`` gemeldet, gilt: Wechsel mit gespeichertem Zeiger der alten Serie.
* Nach allem ist das Abheben weiterhin sofort wirksam (kein hängender Zustand).
* Im Protokoll fehlt ``abgehoben`` für den Vorgang (``test_protokoll_...`` mit echter ``App``, die Zeilen
  gehen durch ``fake_reader`` und MPD).

Nicht doppelt geprüft: die Firmware-Entprellung (PlatformIO ``native``) und die Zeilenprüfung von
``reader.py`` (``unit/test_protocol.py``, ``integration/test_reader_pty.py``).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from conftest import CujBox, app_welt
from fixtures import audio
from integration.test_app_e2e import _spielt, mpd_status, warte

from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox.app import App

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader  # noqa: E402

SERIE = "3f9a1c07b2d4"
SERIE_B = "5b6c7d8e9f01"
UID = "04a1b2c3"
UID_B = "04a1b2c4"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav"], serie_id=SERIE, name="Rabe", dauer_s=30.0)
    audio.erzeuge_serie(medien, "baer", ["x.wav"], serie_id=SERIE_B, name="Baer", dauer_s=30.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    b = CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE), UID_B: ev.Zuordnung("serie", SERIE_B)}, aufbau)
    b.leser.hello()
    b.leser.placed(UID)
    b.leser.hb(True)  # erster Herzschlag nach HELLO: die Firmware sieht den Tobie (sonst gälte 9.3 „abgehoben im Ausfall“)
    b.laufe(5.0)
    return b


def unveraendert(box, n, elapsed):
    assert box.befehle(ev.Abspielen, n) == [] and box.befehle(ev.Pausieren, n) == []
    assert box.modus == "spielt" and box.player.spielt
    assert box.player.elapsed == pytest.approx(elapsed, abs=0.01)


def test_luecke_von_einer_sekunde_ohne_zeile_aendert_nichts(box):
    n = len(box.log)
    box.laufe(1.0)  # nur Takt, keine Zeile der Firmware
    unveraendert(box, n, 6.0)


def test_lucke_mit_herzschlaegen_present_1_aendert_nichts(box):
    n = len(box.log)
    for _ in range(5):
        box.laufe(0.4)
        box.leser.hb(True)
    unveraendert(box, n, 7.0)


def test_ein_herzschlag_present_0_pausiert_nicht(box):
    n = len(box.log)
    box.leser.hb(False)
    box.laufe(1.0)
    box.leser.hb(True)  # der nächste Herzschlag stimmt wieder
    box.laufe(1.0)
    unveraendert(box, n, 7.0)
    assert box.befehle(ev.LeserPing, n) == []


def test_zwei_abweichende_herzschlaege_loesen_nur_einen_ping_aus_und_pausieren_nicht(box):
    n = len(box.log)
    box.leser.hb(False)
    box.laufe(2.0)
    box.leser.hb(False)
    box.laufe(1.0)
    assert len(box.befehle(ev.LeserPing, n)) == 1
    unveraendert(box, n, 8.0)


def test_dieselbe_kennung_wieder_ohne_removed_startet_nicht_neu(box):
    vorher = box.kern.session.figur.vorgang
    n = len(box.log)
    box.laufe(1.0)
    box.leser.placed(UID)  # REMOVED ging verloren, die Firmware meldet erneut (seq lief weiter)
    box.laufe(1.0)
    unveraendert(box, n, 7.0)
    assert box.kern.session.figur.vorgang != vorher  # neue ID gemerkt; spätere REMOVED passt zu ihr
    box.leser.removed()
    assert box.modus == "pausiert" and not box.player.spielt


def test_verlorene_zeile_seq_luecke_aendert_nichts(box):
    n = len(box.log)
    box.leser.seq += 3  # drei Zeilen der Firmware gingen unterwegs verloren
    box.leser.placed(UID)
    box.laufe(1.0)
    unveraendert(box, n, 6.0)


def test_andere_kennung_nach_removed_gilt_und_die_alte_serie_bleibt_gespeichert(box):
    box.leser.removed()
    n = len(box.log)
    box.leser.placed(UID_B)
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == SERIE_B and a.position_s == 0.0
    assert box.resume_json()["serien"][SERIE]["position_s"] == pytest.approx(5.0, abs=0.01)


def test_nach_der_luecke_wirkt_das_abheben_sofort(box):
    box.laufe(1.0)
    box.leser.placed(UID)
    box.leser.removed()
    assert [p.grund for p in box.befehle(ev.Pausieren)] == ["abgehoben"]


async def test_protokoll_zeigt_wiedermeldung_ohne_abgehoben_und_mpd_spielt_weiter(mpd, tmp_path, protokoll):
    welt = app_welt(mpd, tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, {"rabe": (SERIE, ["folge-01.wav", "folge-02.wav"], 30.0)})
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(welt["toml"]), melde_bereit=False)
        await app.starte()
        try:
            await warte(lambda: "PING" in fr.empfangen, 5.0, "(Leser verbunden)")
            await asyncio.sleep(0.8)
            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 8.0, "(spielt)")
            await asyncio.sleep(1.5)
            vor = float((await mpd_status(mpd.port))["elapsed"])
            fr.place(UID)  # Aussetzer: dieselbe Kennung ohne REMOVED
            await asyncio.sleep(1.2)
            st = await mpd_status(mpd.port)
            assert st["state"] == "play" and float(st["elapsed"]) > vor + 0.8  # kein Neustart, keine Pause
            assert st["playlistlength"] == "1"
        finally:
            await app.beende()
    assert protokoll.finde("abgehoben") == []  # im Protokoll fehlt „abgehoben“
    assert len(protokoll.finde("abspielen")) == 1
    assert [z["daten"]["grund"] for z in protokoll.finde("pausieren")] == ["herunterfahren"]  # nur das Dienst-Ende
