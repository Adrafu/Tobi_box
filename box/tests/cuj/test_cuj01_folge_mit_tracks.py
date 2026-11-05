"""CUJ 1 und 3 für eine Folge mit mehreren Tracks (AP 1.7, Entscheidung F, 05.11.).

Tracks spielen nacheinander ohne Pause, die Pause kommt erst am Ende der ganzen Folge, Resume mitten
im zweiten Track, Vor / Zurück nach Track (Serien-Tobie: letzter Track -> nächste Folge;
Folgen-Tobie: Hinweiston). Echter Kern, echte Bibliothek und echtes ``resume.json`` aus erzeugten Dateien.
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import audio

from tobibox import events as ev

SERIE = "8c21d5e9a0b7"
UID_CD = "04a1b2c5"  # Tobie auf die Folge „CD Schatzinsel“ (drei Tracks)
UID_SERIE = "04a1b2c6"  # Tobie auf die ganze Serie
CD = "CD Schatzinsel"
TRACKS = (f"{CD}/01.wav", f"{CD}/02.wav", f"{CD}/03.wav")


def aufbau(medien):
    ordner = audio.erzeuge_serie(medien, "schatz", ["z.wav"], serie_id=SERIE, name="Schatzinsel", dauer_s=4.0)
    audio.erzeuge_folge_ordner(ordner, CD, ["01.wav", "02.wav", "03.wav"], dauer_s=4.0, dotfiles=True, fremde=["cover.jpg"])
    audio.schreibe_serie_json(ordner, SERIE, "Schatzinsel", [CD, "z.wav"])
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    zuordnungen = {
        UID_CD: ev.Zuordnung("folge", SERIE, CD),
        UID_SERIE: ev.Zuordnung("serie", SERIE),
    }
    return CujBox(tmp_path, zuordnungen, aufbau)


def pausen(box, ab=0):
    return [p.grund for p in box.befehle(ev.Pausieren, ab)]


def test_alle_tracks_der_folge_werden_geladen_dotfiles_und_fremdes_nicht(box):
    box.auflege(UID_CD)
    (a,) = box.befehle(ev.Abspielen)
    assert (a.datei, a.tracks, a.track, a.position_s) == (CD, TRACKS, 0, 0.0)
    assert box.player.warteschlangen == [TRACKS]


def test_tracks_spielen_ohne_pause_die_pause_kommt_erst_am_ende_der_ganzen_folge(box):
    box.auflege(UID_CD)
    box.laufe(3.9)
    assert box.kern.session.track == 0
    box.laufe(0.3)  # 4,2 s: zweiter Track
    assert (box.kern.session.track, box.modus) == (1, "spielt")
    box.laufe(4.0)  # 8,2 s: dritter Track
    assert (box.kern.session.track, box.modus) == (2, "spielt")
    assert pausen(box) == []  # bis hierher keine einzige Pause
    box.laufe(4.0)  # 12,2 s: Folge zu Ende
    assert box.modus == "beendet"
    assert pausen(box) == ["folgenende"]  # genau eine, am Ende der ganzen Folge
    assert not box.player.spielt
    z = box.resume_json()["folgen"][SERIE][CD]
    assert (z["track"], z["position_s"]) == (0, 0.0)  # Folgen-Zeiger springt zurück auf den Anfang


def test_jeder_track_wechsel_wird_im_zeiger_gespeichert(box):
    box.auflege(UID_CD)
    box.laufe(4.2)
    assert box.resume_json()["folgen"][SERIE][CD]["track"] == 1
    box.laufe(4.0)
    assert box.resume_json()["folgen"][SERIE][CD]["track"] == 2
    gruende = [c.grund for c in box.befehle(ev.ZeigerSpeichern)]
    assert gruende.count("trackwechsel") == 2 and "folgenende" not in gruende


def test_resume_mitten_im_zweiten_track_nach_abheben_und_neustart(box):
    box.auflege(UID_CD)
    box.laufe(7.5)  # zweiter Track, 3,5 s
    assert box.kern.session.track == 1
    box.hebe_ab()
    z = box.resume_json()["folgen"][SERIE][CD]
    assert z["track"] == 1 and 3.0 <= z["position_s"] <= 3.6
    box.neustart()
    n = len(box.log)
    box.auflege(UID_CD, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.tracks, a.track) == (CD, TRACKS, 1)
    assert 0.0 <= a.position_s <= 0.7  # gespeicherte Position minus 3 s Rücksprung
    box.laufe(4.0)  # nach dem Rest des zweiten Tracks folgt der dritte
    assert box.kern.session.track == 2 and box.modus == "spielt"


def test_weiter_und_zurueck_nach_track_beim_folgen_tobie(box):
    box.auflege(UID_CD)
    box.laufe(1.0)
    n = len(box.log)
    box.sende(ev.Weiter())
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.track, a.position_s, a.tracks) == (1, 0.0, TRACKS)
    box.laufe(1.0)  # unter 3 s im zweiten Track: Zurück geht zum vorigen Track
    n = len(box.log)
    box.sende(ev.Zurueck())
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.track, a.position_s) == (0, 0.0)
    box.laufe(3.5)  # ab 3 s im Track: Zurück startet den aktuellen Track neu
    n = len(box.log)
    box.sende(ev.Zurueck())
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.track, a.position_s) == (0, 0.0)
    assert box.modus == "spielt"


def test_folgen_tobie_weiter_beim_letzten_track_nur_hinweiston(box):
    box.auflege(UID_CD)
    box.sende(ev.Weiter())
    box.sende(ev.Weiter())
    assert box.kern.session.track == 2
    n = len(box.log)
    box.sende(ev.Weiter())
    wirkung = [b for b in box.log[n:] if isinstance(b, (ev.Abspielen, ev.TonSpielen, ev.ZeigerSpeichern, ev.Pausieren))]
    assert wirkung == [ev.TonSpielen("hinweis")]  # kein Abspielen, kein Speichern, keine Pause
    assert (box.kern.session.track, box.modus) == (2, "spielt")


def test_serien_tobie_weiter_beim_letzten_track_spielt_die_naechste_folge(box):
    box.auflege(UID_SERIE)
    box.sende(ev.Weiter())
    box.sende(ev.Weiter())
    assert box.kern.session.track == 2
    n = len(box.log)
    box.sende(ev.Weiter())
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.tracks, a.track, a.position_s) == ("z.wav", ("z.wav",), 0, 0.0)
    assert box.modus == "spielt"
    assert box.resume_json()["serien"][SERIE]["folge"] == "z.wav"


def test_serien_tobie_folge_mit_tracks_zu_ende_dann_naechste_folge_nach_hauptknopf(box):
    box.auflege(UID_SERIE)
    box.laufe(12.5)
    assert box.modus == "beendet" and pausen(box) == ["folgenende"]
    z = box.resume_json()["serien"][SERIE]
    assert (z["folge"], z["track"], z["position_s"]) == ("z.wav", 0, 0.0)
    n = len(box.log)
    box.sende(ev.Hauptknopf("kurz"))
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.track) == ("z.wav", 0)


def test_zurueck_in_beendet_spielt_die_eben_beendete_folge_mit_allen_tracks_von_vorn(box):
    box.auflege(UID_SERIE)
    box.laufe(12.5)
    assert box.modus == "beendet"
    n = len(box.log)
    box.sende(ev.Zurueck())
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.tracks, a.track, a.position_s) == (CD, TRACKS, 0, 0.0)
    assert [c.grund for c in box.befehle(ev.ZeigerSpeichern, n)] == ["zurueck"]
    assert box.resume_json()["serien"][SERIE]["folge"] == CD
    assert box.resume_json()["serien"][SERIE]["index"] == 0
