"""CUJ 3: Tobie wieder auflegen (Resume), Abnahme AP 2.1.

Resume mit 3-s-Rücksprung (auch nach Neustart und leerem Akku), Pause nach jeder Folge bei liegendem
Tobie (Entscheidung A), Zeiger auf die nächste Folge und nach der letzten auf Folge 1, Resume mitten im
zweiten Track, Folgen-Tobie spielt nach dem Ende von vorn (Entscheidung F, 05.11.).
Echter Kern, echte Bibliothek und echtes ``resume.json`` aus erzeugten Dateien.
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import audio

from tobibox import events as ev

SERIE = "3f9a1c07b2d4"
UID_SERIE = "04a1b2c3"
UID_SERIE_2 = "04a1b2c4"  # zweiter Tobie derselben Serie
UID_FOLGE = "04a1b2c5"  # Folge b.wav
UID_CD = "04a1b2c6"  # Folge „CD“ mit zwei Tracks
CD = "CD"
TRACKS = (f"{CD}/01.wav", f"{CD}/02.wav")


def aufbau(medien):
    ordner = audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=10.0)
    audio.erzeuge_folge_ordner(ordner, CD, ["01.wav", "02.wav"], dauer_s=6.0)
    audio.schreibe_serie_json(ordner, SERIE, "Rabe", ["a.wav", "b.wav", "c.wav", CD])
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    zuordnungen = {
        UID_SERIE: ev.Zuordnung("serie", SERIE),
        UID_SERIE_2: ev.Zuordnung("serie", SERIE),
        UID_FOLGE: ev.Zuordnung("folge", SERIE, "b.wav"),
        UID_CD: ev.Zuordnung("folge", SERIE, CD),
    }
    return CujBox(tmp_path, zuordnungen, aufbau)


def pausen(box, ab=0):
    return [p.grund for p in box.befehle(ev.Pausieren, ab)]


def serien_zeiger(box) -> dict:
    return box.resume_json()["serien"][SERIE]


# --- Resume mit Rücksprung ------------------------------------------------------------------


def test_resume_nach_abheben_springt_drei_sekunden_zurueck(box):
    box.auflege(UID_SERIE)
    box.laufe(6.0)
    box.hebe_ab()
    z = serien_zeiger(box)
    assert z["folge"] == "a.wav" and z["position_s"] == 6.0
    n = len(box.log)
    box.auflege(UID_SERIE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.track, a.position_s, a.vorgang) == ("a.wav", 0, 3.0, "v2")
    assert box.modus == "spielt"


def test_resume_nahe_am_anfang_springt_nicht_unter_null(box):
    box.auflege(UID_SERIE)
    box.laufe(2.0)
    box.hebe_ab()
    n = len(box.log)
    box.auflege(UID_SERIE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.position_s == 0.0


def test_resume_nach_neustart_des_dienstes_mit_ruecksprung(box):
    box.auflege(UID_SERIE)
    box.laufe(7.0)
    box.hebe_ab()
    box.neustart()
    assert box.modus == "leer"
    n = len(box.log)
    box.auflege(UID_SERIE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("a.wav", 4.0)


def test_resume_nach_leerem_akku_hoechstens_30_sekunden_verloren(tmp_path):
    zuordnungen = {UID_SERIE: ev.Zuordnung("serie", SERIE)}

    def lang(medien):
        audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav"], serie_id=SERIE, name="Rabe", dauer_s=120.0)
        audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)

    box = CujBox(tmp_path, zuordnungen, lang)
    box.auflege(UID_SERIE)
    box.laufe(75.0)  # Strom weg mitten in der Wiedergabe: kein Abheben, kein Speichern beim Beenden
    gespeichert = serien_zeiger(box)["position_s"]
    assert 75.0 - 30.0 <= gespeichert <= 75.0
    box.neustart_nach_einschalten()
    n = len(box.log)
    box.auflege(UID_SERIE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.datei == "a.wav" and a.position_s == pytest.approx(gespeichert - 3.0)
    assert 75.0 - a.position_s <= 33.0  # höchstens 30 s verloren, dazu der Rücksprung


def test_resume_gilt_fuer_jeden_tobie_derselben_serie(box):
    box.auflege(UID_SERIE)
    box.laufe(6.0)
    box.hebe_ab()
    n = len(box.log)
    box.auflege(UID_SERIE_2, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("a.wav", 3.0)


# --- Folge zu Ende: Pause trotz liegendem Tobie (Entscheidung A) -----------------------------


def test_folge_zu_ende_pause_zeiger_auf_naechste_folge_und_nichts_passiert(box):
    box.auflege(UID_SERIE)
    box.laufe(10.5)
    assert box.modus == "beendet"
    assert pausen(box) == ["folgenende"] and not box.player.spielt
    assert box.kern.session.figur is not None  # der Tobie liegt noch
    z = serien_zeiger(box)
    assert (z["folge"], z["index"], z["track"], z["position_s"]) == ("b.wav", 1, 0, 0.0)
    n = len(box.log)
    box.laufe(30.0)  # auch lange Wartezeit: nichts startet von selbst
    assert box.befehle(ev.Abspielen, n) == [] and box.modus == "beendet" and not box.player.spielt


def test_nach_folgenende_spielt_erst_abheben_und_auflegen_die_naechste_folge(box):
    box.auflege(UID_SERIE)
    box.laufe(10.5)
    assert box.modus == "beendet"
    n = len(box.log)
    box.hebe_ab()
    assert box.befehle(ev.Abspielen, n) == [] and serien_zeiger(box)["folge"] == "b.wav"
    box.auflege(UID_SERIE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.track, a.position_s) == ("b.wav", 0, 0.0)  # Anfang der nächsten Folge, kein Rücksprung
    assert box.modus == "spielt"


def test_nach_folgenende_hauptknopf_kurz_spielt_die_naechste_folge(box):
    box.auflege(UID_SERIE)
    box.laufe(10.5)
    n = len(box.log)
    box.sende(ev.Hauptknopf("kurz"))
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0) and box.modus == "spielt"


def test_nach_folgenende_wechselt_ein_anderer_tobie_derselben_serie_auf_die_naechste_folge(box):
    box.auflege(UID_SERIE)
    box.laufe(10.5)
    box.hebe_ab()
    n = len(box.log)
    box.auflege(UID_SERIE_2, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0)


def test_pause_nach_jeder_folge_durch_die_ganze_serie_und_nach_der_letzten_zeiger_auf_folge_1(box):
    box.auflege(UID_SERIE)
    box.laufe(10.5)  # a.wav zu Ende
    assert serien_zeiger(box)["folge"] == "b.wav"
    box.sende(ev.Hauptknopf("kurz"))
    box.laufe(10.5)  # b.wav zu Ende
    assert box.modus == "beendet" and serien_zeiger(box)["folge"] == "c.wav"
    box.sende(ev.Hauptknopf("kurz"))
    box.laufe(10.5)  # c.wav zu Ende
    assert box.modus == "beendet" and serien_zeiger(box)["folge"] == CD
    box.sende(ev.Hauptknopf("kurz"))
    box.laufe(12.5)  # CD (zwei Tracks) zu Ende: letzte Folge der Serie
    assert box.modus == "beendet"
    z = serien_zeiger(box)
    assert (z["folge"], z["index"], z["track"], z["position_s"]) == ("a.wav", 0, 0, 0.0)  # Folge 1
    assert pausen(box) == ["folgenende"] * 4  # genau eine Pause je Folge
    assert not box.player.spielt
    n = len(box.log)
    box.hebe_ab()
    box.auflege(UID_SERIE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("a.wav", 0.0)


def test_zeiger_nach_folgenende_ueberlebt_den_neustart(box):
    box.auflege(UID_SERIE)
    box.laufe(10.5)
    box.neustart_nach_einschalten()
    n = len(box.log)
    box.auflege(UID_SERIE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0)


# --- Folge mit mehreren Tracks -----------------------------------------------------------------


def test_resume_mitten_im_zweiten_track_auch_nach_neustart(box):
    box.auflege(UID_CD)
    box.laufe(9.0)  # zweiter Track, 3 s
    assert box.kern.session.track == 1
    box.hebe_ab()
    z = box.resume_json()["folgen"][SERIE][CD]
    assert z["track"] == 1 and z["position_s"] == 3.0
    box.neustart()
    n = len(box.log)
    box.auflege(UID_CD, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.tracks, a.track, a.position_s) == (CD, TRACKS, 1, 0.0)  # 3,0 - 3 s Rücksprung
    box.laufe(7.0)  # Rest des zweiten Tracks, dann Folgenende
    assert box.modus == "beendet"


def test_serien_tobie_resume_mitten_im_zweiten_track_einer_folge(box):
    # Serie mit CD-Folge als vierter Folge: über Weiter dorthin springen
    box.auflege(UID_SERIE)
    for _ in range(3):
        box.sende(ev.Weiter())
    assert box.kern.session.datei == CD
    box.laufe(1.0)
    box.sende(ev.Weiter())  # zweiter Track
    box.laufe(5.0)
    assert box.kern.session.track == 1
    box.hebe_ab()
    z = serien_zeiger(box)
    assert (z["folge"], z["track"], z["position_s"]) == (CD, 1, 5.0)
    box.neustart()
    n = len(box.log)
    box.auflege(UID_SERIE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.tracks, a.track, a.position_s) == (CD, TRACKS, 1, 2.0)


# --- Folgen-Tobie: von vorn nach dem Ende (Entscheidung F, 05.11.) ---------------------------


def test_folgen_tobie_resume_mitten_in_der_folge(box):
    box.auflege(UID_FOLGE)
    box.laufe(7.0)
    box.hebe_ab()
    n = len(box.log)
    box.auflege(UID_FOLGE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.track, a.position_s) == ("b.wav", 0, 4.0)


def test_folgen_tobie_spielt_nach_dem_ende_von_vorn_nicht_die_naechste_folge(box):
    box.auflege(UID_FOLGE)
    box.laufe(10.5)
    assert box.modus == "beendet" and pausen(box) == ["folgenende"]
    z = box.resume_json()["folgen"][SERIE]["b.wav"]
    assert (z["track"], z["position_s"]) == (0, 0.0)
    n = len(box.log)
    box.laufe(20.0)
    assert box.befehle(ev.Abspielen, n) == []  # Pause, nichts startet von selbst
    box.hebe_ab()
    box.auflege(UID_FOLGE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.tracks, a.track, a.position_s) == ("b.wav", ("b.wav",), 0, 0.0)  # von vorn, kein Rücksprung
    assert box.modus == "spielt"
    assert SERIE not in box.resume_json().get("serien", {})  # der Serien-Zeiger wurde nie angelegt


def test_folgen_tobie_ende_nach_neustart_dann_von_vorn(box):
    box.auflege(UID_FOLGE)
    box.laufe(10.5)
    box.neustart_nach_einschalten()
    n = len(box.log)
    box.auflege(UID_FOLGE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0)
