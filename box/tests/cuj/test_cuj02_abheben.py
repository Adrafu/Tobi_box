"""CUJ 2 (AP 1.6): Abheben. Pause, Zeiger (Folge, Track, Position) für das Ziel des Tobies gespeichert.

Bewiesene Schritte von CUJ 2:

* Given: Tobie liegt, sein Ziel spielt. When: ``REMOVED`` (echte Zeilenverarbeitung ``reader.Leser``).
  Then: ``Pausieren("abgehoben")`` im selben Schritt, danach ``ZeigerSpeichern`` (Rang-Reihenfolge:
  erst Pause, dann Platte); MPD/Player steht; ``resume.json`` enthält Folge, Track und Position
  (``test_abheben_pausiert_und_speichert_den_zeiger``, ``..._in_zweiter_folge``).
* Zeigertest der Abnahme Stufe 1: Abheben, Neustart des Dienstes, erneutes Auflegen: weiter an der
  gespeicherten Stelle mit 3 s Rücksprung (``test_abheben_dienst_neustart_auflegen_...``).
* Doppeltes ``REMOVED`` bewirkt nichts (kein zweites Pausieren).
* Echte ``App`` mit echtem MPD: Protokollzeilen ``abgehoben`` -> ``pausieren`` -> ``zeiger_gespeichert``,
  MPD steht in ``pause`` (``test_app_abheben_...``). Abheben/Wiederauflegen mit MPD und Rücksprung
  prüft außerdem ``integration/test_app_e2e.py::test_auflegen_abheben_wieder_auflegen``.

Nicht doppelt geprüft: Abheben eines Folgen-Tobies und das Folgenende (``test_cuj01_folgen_tobie.py``);
Abheben im Folgenende-Zustand und andere Zustände decken ``unit/test_session.py`` ab.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest
from conftest import CujBox, app_welt
from fixtures import audio
from integration.test_app_e2e import _zustand_ist, _spielt, mpd_status, warte

from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox.app import App

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader  # noqa: E402

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    return CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)


def spielend(box):
    box.leser.hello()
    box.leser.placed(UID)
    box.laufe(7.0)
    return len(box.log)


def test_abheben_pausiert_und_speichert_den_zeiger(box):
    n = spielend(box)
    box.leser.removed()
    neu = box.log[n:]
    pause = [b for b in neu if isinstance(b, ev.Pausieren)]
    (sp,) = [b for b in neu if isinstance(b, ev.ZeigerSpeichern)]
    assert [p.grund for p in pause] == ["abgehoben"]  # im selben Schritt wie REMOVED
    assert neu.index(pause[0]) < neu.index(sp)  # erst Pause, dann Zeiger
    assert (sp.art, sp.serie_id, sp.datei, sp.index, sp.track, sp.grund) == ("serie", SERIE, "a.wav", 0, 0, "pause")
    assert sp.position_s == pytest.approx(7.0, abs=0.01)
    assert box.modus == "pausiert" and not box.player.spielt and box.kern.session.figur is None
    gespeichert = box.resume_json()["serien"][SERIE]
    assert (gespeichert["folge"], gespeichert["track"]) == ("a.wav", 0)
    assert gespeichert["position_s"] == pytest.approx(7.0, abs=0.01)


def test_abheben_in_zweiter_folge_speichert_folge_index_und_position(box):
    box.leser.hello()
    box.leser.placed(UID)
    box.laufe(23.0)  # Folge 1 dauert 20 s
    assert box.modus == "beendet"  # Entscheidung E: nach der Folge Pause, der Zeiger steht auf Folge 2
    box.leser.removed()
    box.leser.placed(UID)  # nächstes Auflegen spielt Folge 2
    box.laufe(5.0)
    box.leser.removed()
    gespeichert = box.resume_json()["serien"][SERIE]
    assert gespeichert["folge"] == "b.wav" and gespeichert["index"] == 1
    assert gespeichert["position_s"] == pytest.approx(5.0, abs=0.01)


def test_abheben_dienst_neustart_auflegen_spielt_an_der_gespeicherten_stelle_mit_ruecksprung(box):
    spielend(box)
    box.leser.removed()
    gespeichert = box.resume_json()["serien"][SERIE]["position_s"]
    box.neustart()  # Dienst neu gestartet, der Tobie liegt nicht mehr
    box.leser.hello()
    n = len(box.log)
    box.leser.placed(UID)
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.track) == ("a.wav", 0)
    assert a.position_s == pytest.approx(max(0.0, gespeichert - 3.0), abs=0.01)  # 3 s Rücksprung
    assert box.modus == "spielt"


def test_doppeltes_removed_pausiert_nicht_zweimal(box):
    spielend(box)
    box.leser.removed()
    n = len(box.log)
    box.leser.removed()
    assert box.befehle(ev.Pausieren, n) == [] and box.befehle(ev.ZeigerSpeichern, n) == []


def test_abheben_vor_der_ersten_sekunde_speichert_keinen_unsinn(box):
    box.leser.hello()
    box.leser.placed(UID)
    box.leser.removed()
    assert box.modus == "pausiert" and not box.player.spielt
    box.leser.placed(UID)
    (a, b) = box.befehle(ev.Abspielen)
    assert (b.datei, b.position_s) == ("a.wav", 0.0)  # Rücksprung nie unter 0


async def test_app_abheben_pausiert_mpd_und_protokolliert_die_kette(mpd, tmp_path, protokoll):
    welt = app_welt(mpd, tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, {"rabe": (SERIE, ["folge-01.wav", "folge-02.wav"], 30.0)})
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(welt["toml"]), melde_bereit=False)
        await app.starte()
        try:
            await warte(lambda: "PING" in fr.empfangen, 5.0, "(Leser verbunden)")
            await asyncio.sleep(0.8)
            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 8.0, "(spielt)")
            await asyncio.sleep(2.5)
            t0 = time.monotonic()
            fr.remove()
            await warte(lambda: _zustand_ist(mpd.port, "pause"), 5.0, "(MPD pausiert)")
            bis_pause = time.monotonic() - t0
            await warte(lambda: (welt["zustand"] / "resume.json").exists(), 5.0, "(Zeiger)")
        finally:
            await app.beende()
    assert bis_pause < 1.0, bis_pause  # nur Dienst und MPD (Container); die Zeitgrenze misst timing.md am Ausgang
    namen = [z["ereignis"] for z in protokoll.zeilen()]
    i = namen.index("abgehoben")
    assert namen.index("pausieren", i) < namen.index("zeiger_gespeichert", i)
    (ab,) = protokoll.finde("abgehoben")
    (pa,) = [z for z in protokoll.finde("pausieren") if z["daten"]["grund"] == "abgehoben"]
    assert ab["baustein"] == "reader" and ab["vorgang"] == pa["vorgang"]
    zg = protokoll.finde("zeiger_gespeichert")[0]
    assert zg["daten"]["serie"] == SERIE and zg["daten"]["position_s"] >= 2.0
