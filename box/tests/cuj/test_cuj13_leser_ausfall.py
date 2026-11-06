"""CUJ 13 (AP 1.6): Leser fällt aus und kommt wieder.

Die Zeilen der Firmware gehen durch die echte Verarbeitung von ``reader.Leser`` (``seq``-Prüfung,
Vorgangs-ID, Wiedermeldung); Alarm und ``HELLO`` kommen wie von der Verbindungsschleife. Zeit läuft simuliert.

**Fristen nach dem Vertrag** (``core-interface.md``, 9.1: Vertragswerte gelten vor dem Design-Text):
Die Karenzzeit ist ``LESER_FRIST_S`` = 3,0 s, die Pause kommt spätestens 3,1 s nach dem ersten Ereignis
(Alarm oder ``HELLO``) (bewusste Ausnahme von der 1,5-s-Regel des Designs). Wurde der Tobie im Ausfall
abgehoben und meldet der erste Herzschlag nach ``HELLO`` ``present=0``, pausiert die Box sofort.

Bewiesene Schritte von CUJ 13:

* "``HELLO`` setzt ``seq`` zurück und versetzt den Kern in Leser-Zustand unbekannt": nach Alarm bzw.
  ``HELLO`` ist der Modus ``unbekannt``; ``PLACED seq=0`` gilt als Wiedermeldung (gleiche Vorgangs-ID).
* "Kommt derselbe Tobie wieder, läuft die Serie weiter, ohne neu zu starten": kein ``Abspielen``, kein
  ``Pausieren``, der Player läuft durch (Alarm -> ``HELLO`` -> ``PLACED`` sowie nur ``HELLO``).
* "Wurde der Tobie abgehoben, pausiert die Box": erster Herzschlag ``present=0`` nach ``HELLO`` pausiert
  sofort; ohne jede Meldung pausiert sie nach 3,0 bis 3,1 s; der Zeiger ist gespeichert.
* Anderer Tobie nach dem Ausfall: Pause und Zeiger der alten Serie, dann der neue wie ein Auflegen.
* Nach Ablauf der Frist startet ein zurückkehrender Tobie nichts von selbst (Hauptknopf spielt).
* ``seq``-Rücksetzen ohne ``HELLO`` (verlorenes ``HELLO``) wird wie eine Wiedermeldung behandelt.
* Alarm in ``pausiert`` ändert nichts. Leser-Ausfall startet nie eine Wiedergabe.
* Echte ``App`` mit ``fake_reader`` und echtem MPD: Leser-Neustart mit liegendem Tobie (MPD spielt weiter,
  ein einziges ``Abspielen``) und Leser-Neustart mit Abheben (MPD pausiert, Zeiger gespeichert).
* Abnahme Stufe 1: "USB-Kabel ziehen und stecken", einmal mit liegendem Tobie, einmal mit Abheben in der
  Unterbrechung: beide Abläufe unten.

Nicht doppelt geprüft: Alarm-Zeitverhalten des Wächters (5 s Herzschlag-Frist, Neuverbinden mit Backoff)
am Pseudo-Terminal: ``integration/test_reader_pty.py``; Eintritt in ``unbekannt`` und Fristrand:
``unit/test_session.py``.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from conftest import CujBox, app_welt
from fixtures import audio
from integration.test_app_e2e import _spielt, _zustand_ist, mpd_status, warte

from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox.app import App
from tobibox.session import LESER_FRIST_S

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader  # noqa: E402

SERIE = "3f9a1c07b2d4"
SERIE_B = "5b6c7d8e9f01"
UID = "04a1b2c3"
UID_B = "04a1b2c4"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav"], serie_id=SERIE, name="Rabe", dauer_s=40.0)
    audio.erzeuge_serie(medien, "baer", ["x.wav"], serie_id=SERIE_B, name="Baer", dauer_s=40.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    b = CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE), UID_B: ev.Zuordnung("serie", SERIE_B)}, aufbau)
    b.leser.hello()
    b.leser.placed(UID)
    b.leser.hb(True)
    b.laufe(6.0)
    return b


def ausfall(box, grund="kein_herzschlag"):
    box.sende(ev.LeserAlarm(grund))


def laeuft_unveraendert(box, n):
    assert box.befehle(ev.Abspielen, n) == [] and box.befehle(ev.Pausieren, n) == []
    assert box.modus == "spielt" and box.player.spielt


def test_frist_und_pausengrenze_entsprechen_dem_vertrag():
    assert LESER_FRIST_S == 3.0  # nicht 1,5 s (Design); Pause <= 3,1 s nach dem Ereignis


def test_alarm_versetzt_in_unbekannt_der_ton_laeuft_weiter(box):
    ausfall(box)
    assert box.modus == "unbekannt" and box.player.spielt
    assert box.kern.session.figur is not None  # der Tobie gilt weiter als liegend


def test_kabel_gesteckt_derselbe_tobie_laeuft_ohne_neustart_weiter(box):
    """Abnahme Stufe 1, erster Versuch: Kabel ziehen, nach etwa 5 s stecken - hier 1,5 s Unterbrechung."""
    vorgang = box.kern.session.figur.vorgang
    n = len(box.log)
    ausfall(box)
    box.laufe(1.0)
    box.leser.hello()  # nach dem Stecken: HELLO, seq beginnt bei 0
    box.laufe(0.3)
    box.leser.placed(UID)  # PLACED seq=0: Wiedermeldung
    assert box.kern.session.figur.vorgang == vorgang  # gleiche Vorgangs-ID trotz seq=0
    box.leser.hb(True)
    box.laufe(1.0)
    laeuft_unveraendert(box, n)
    assert box.player.elapsed == pytest.approx(8.3, abs=0.01)  # ohne Lücke weitergelaufen
    assert [a.vorgang for a in box.befehle(ev.Abspielen)] == [vorgang]  # nur das erste Auflegen


def test_esp32_neustart_ohne_usb_abbruch_nur_hello_und_placed(box):
    n = len(box.log)
    box.leser.hello()
    assert box.modus == "unbekannt"
    box.laufe(0.5)
    box.leser.placed(UID)
    box.laufe(1.0)
    laeuft_unveraendert(box, n)


def test_abgehoben_waehrend_der_unterbrechung_erster_herzschlag_present_0_pausiert_sofort(box):
    """Abnahme Stufe 1, zweiter Versuch: Kabel gezogen, Tobie abgehoben, Kabel gesteckt."""
    n = len(box.log)
    ausfall(box)
    box.laufe(1.0)
    box.leser.hello()
    box.leser.hb(False)  # erster Herzschlag nach HELLO: nichts liegt
    pausen = box.befehle(ev.Pausieren, n)
    assert [p.grund for p in pausen] == ["abgehoben"]
    assert box.modus == "pausiert" and not box.player.spielt and box.kern.session.figur is None
    sp = box.befehle(ev.ZeigerSpeichern, n)
    assert len(sp) == 1 and sp[0].position_s == pytest.approx(7.0, abs=0.01)
    assert box.resume_json()["serien"][SERIE]["position_s"] == pytest.approx(7.0, abs=0.01)


def test_abgehoben_und_keine_meldung_pausiert_nach_3_0_bis_3_1_s(box):
    n = len(box.log)
    ausfall(box)
    t0 = box.uhr.mono
    pause_nach = None
    for _ in range(40):
        box.laufe(0.1)
        if box.befehle(ev.Pausieren, n):
            pause_nach = box.uhr.mono - t0
            break
    assert pause_nach is not None
    assert 3.0 - 1e-6 <= pause_nach <= 3.1 + 1e-6, pause_nach  # LESER_FRIST_S + TAKT_S
    assert [p.grund for p in box.befehle(ev.Pausieren, n)] == ["leser_unbekannt"]
    assert box.modus == "pausiert" and not box.player.spielt
    assert box.resume_json()["serien"][SERIE]["position_s"] == pytest.approx(9.0, abs=0.01)  # gespeichert


def test_frist_beginnt_mit_dem_ersten_ereignis_und_wird_vom_hello_nicht_verlaengert(box):
    n = len(box.log)
    ausfall(box)
    box.laufe(2.0)
    box.leser.hello()  # zweites Ereignis
    box.laufe(1.2)  # 3,2 s nach dem Alarm
    assert [p.grund for p in box.befehle(ev.Pausieren, n)] == ["leser_unbekannt"]


def test_tobie_kommt_nach_der_frist_zurueck_nichts_startet_von_selbst(box):
    ausfall(box)
    box.laufe(3.2)
    assert box.modus == "pausiert" and box.kern.session.figur is not None  # Tobie gilt weiter als liegend
    n = len(box.log)
    box.leser.hello()
    box.leser.placed(UID)  # Wiedermeldung, gleiche Vorgangs-ID
    box.leser.hb(True)
    box.laufe(2.0)
    assert box.befehle(ev.Abspielen, n) == [] and box.modus == "pausiert"
    box.sende(ev.Hauptknopf("kurz"))
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.position_s == pytest.approx(6.0, abs=0.01)  # 9 s - 3 s Rücksprung


def test_anderer_tobie_nach_dem_ausfall_speichert_die_alte_serie_und_spielt_den_neuen(box):
    ausfall(box)
    box.laufe(0.5)
    box.leser.hello()
    n = len(box.log)
    box.leser.placed(UID_B)  # neue Kennung nach dem Neustart des Lesers
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == SERIE_B and box.modus == "spielt"
    assert box.resume_json()["serien"][SERIE]["position_s"] == pytest.approx(6.0, abs=0.01)  # letzte gemeldete Position (jede Sekunde)


def test_seq_ruecksetzen_ohne_hello_gilt_als_wiedermeldung(box):
    vorgang = box.kern.session.figur.vorgang
    n = len(box.log)
    box.leser.seq = 0  # das HELLO ging verloren, die Firmware zählt von vorn
    box.leser.placed(UID)
    assert box.kern.session.figur.vorgang == vorgang
    laeuft_unveraendert(box, n)


def test_alarm_in_pausiert_hat_keine_wirkung_und_startet_nie(box):
    box.leser.removed()
    n = len(box.log)
    ausfall(box)
    box.leser.hello()
    box.laufe(4.0)
    assert box.modus == "pausiert"
    assert all(not isinstance(b, (ev.Abspielen, ev.Pausieren)) for b in box.log[n:])
    assert not box.player.spielt


def test_alarm_mit_liegendem_tobie_in_pausiert_nach_knopf_bleibt_liegend(box):
    box.sende(ev.Hauptknopf("kurz"))  # Pause per Knopf, Tobie liegt
    ausfall(box)
    box.leser.hello()
    box.leser.placed(UID)
    box.laufe(1.0)
    assert box.modus == "pausiert" and box.kern.session.figur is not None and not box.player.spielt


async def _app_mit_spielendem_tobie(mpd, tmp_path):
    welt = app_welt(mpd, tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, {"rabe": (SERIE, ["folge-01.wav", "folge-02.wav"], 40.0)})
    return welt


async def test_app_leser_neustart_mit_liegendem_tobie_mpd_spielt_ohne_neustart_weiter(mpd, tmp_path, protokoll):
    welt = await _app_mit_spielendem_tobie(mpd, tmp_path)
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
            fr.hello()  # ESP32 startet neu: HELLO, seq beginnt bei 0
            await warte(lambda: app.kern.session.modus == "unbekannt", 2.0, "(Leser-Zustand unbekannt)")
            await asyncio.sleep(0.3)
            fr.place(UID)  # seq=0, derselbe Tobie
            await warte(lambda: app.kern.session.modus == "spielt", 3.0, "(zurück in spielt)")
            await asyncio.sleep(1.0)
            st = await mpd_status(mpd.port)
            assert st["state"] == "play" and float(st["elapsed"]) > vor + 1.0  # durchgelaufen, kein Neustart
        finally:
            await app.beende()
    assert len(protokoll.finde("abspielen")) == 1
    assert [z["daten"]["grund"] for z in protokoll.finde("pausieren")] == ["herunterfahren"]  # nur das Dienst-Ende
    vorgaenge = {z["vorgang"] for z in protokoll.finde("aufgelegt")}
    assert len(vorgaenge) == 1  # seq=0 nach HELLO: gleiche Vorgangs-ID


async def test_app_leser_neustart_mit_abheben_in_der_unterbrechung_pausiert_und_speichert(mpd, tmp_path, protokoll):
    welt = await _app_mit_spielendem_tobie(mpd, tmp_path)
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(welt["toml"]), melde_bereit=False)
        await app.starte()
        try:
            await warte(lambda: "PING" in fr.empfangen, 5.0, "(Leser verbunden)")
            await asyncio.sleep(0.8)
            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 8.0, "(spielt)")
            await asyncio.sleep(2.0)
            fr.present = False  # im Ausfall abgehoben; das REMOVED kam nie an
            fr.hello()
            await warte(lambda: _zustand_ist(mpd.port, "pause"), 3.0, "(pausiert nach dem ersten Herzschlag)")
            assert app.kern.session.figur is None and app.kern.session.modus == "pausiert"
            await warte(lambda: (welt["zustand"] / "resume.json").exists(), 5.0, "(Zeiger)")
        finally:
            await app.beende()
    assert [z["daten"]["grund"] for z in protokoll.finde("pausieren")] == ["abgehoben"]
    assert protokoll.finde("zeiger_gespeichert")[0]["daten"]["position_s"] >= 1.0
