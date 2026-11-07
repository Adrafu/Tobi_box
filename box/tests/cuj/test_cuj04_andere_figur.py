"""CUJ 4: Anderen Tobie auflegen, Abnahme AP 2.1.

Der Zeiger der alten Serie (oder Folge) bleibt gespeichert; die neue Serie läuft an ihrem Zeiger weiter
oder beginnt bei Folge 1; eine Folge ohne Zeiger beginnt am Anfang (Entscheidung F, 05.11.).
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import audio

from tobibox import events as ev

S_RABE = "3f9a1c07b2d4"
S_BAER = "5b7e9d11c0a2"
UID_RABE = "04a1b2c3"
UID_BAER = "04a1b2c4"
UID_RABE_FOLGE = "04a1b2c5"  # Folge b.wav der Serie Rabe
UID_BAER_FOLGE = "04a1b2c6"  # Folge y.wav der Serie Bär
UID_UNBEKANNT = "04ffeedd"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=S_RABE, name="Rabe", dauer_s=10.0)
    audio.erzeuge_serie(medien, "baer", ["x.wav", "y.wav"], serie_id=S_BAER, name="Bär", dauer_s=10.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    zuordnungen = {
        UID_RABE: ev.Zuordnung("serie", S_RABE),
        UID_BAER: ev.Zuordnung("serie", S_BAER),
        UID_RABE_FOLGE: ev.Zuordnung("folge", S_RABE, "b.wav"),
        UID_BAER_FOLGE: ev.Zuordnung("folge", S_BAER, "y.wav"),
    }
    return CujBox(tmp_path, zuordnungen, aufbau)


def serie(box, sid) -> dict:
    return box.resume_json()["serien"][sid]


def test_wechsel_waehrend_der_wiedergabe_speichert_den_zeiger_der_alten_serie_neue_beginnt_bei_folge_1(box):
    box.auflege(UID_RABE)
    box.laufe(6.0)
    n = len(box.log)
    box.sende(ev.Abgehoben(1, "v1"))
    box.auflege(UID_BAER, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.serie_id, a.datei, a.position_s) == (S_BAER, "x.wav", 0.0)  # kein Zeiger: Folge 1
    z = serie(box, S_RABE)
    assert (z["folge"], z["position_s"]) == ("a.wav", 6.0)  # Zeiger der alten Serie bleibt
    assert box.modus == "spielt"


def test_wechsel_ohne_abheben_zwischendurch_speichert_die_alte_position(box):
    # Tobie A wird durch Tobie B ersetzt, ohne dass ein Abheben gemeldet wurde (Aufgelegt ersetzt)
    box.auflege(UID_RABE)
    box.laufe(6.0)
    box.auflege(UID_BAER, "v2")
    assert serie(box, S_RABE)["position_s"] >= 5.0
    assert box.kern.session.serie_id == S_BAER


def test_zurueck_zur_alten_serie_setzt_an_ihrem_zeiger_fort(box):
    box.auflege(UID_RABE)
    box.laufe(6.0)
    box.hebe_ab()
    box.auflege(UID_BAER, "v2")
    box.laufe(5.0)
    box.hebe_ab("v2")
    n = len(box.log)
    box.auflege(UID_RABE, "v3")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.serie_id, a.datei, a.position_s) == (S_RABE, "a.wav", 3.0)
    # auch der Zeiger der zweiten Serie blieb
    assert serie(box, S_BAER)["position_s"] == 5.0
    n = len(box.log)
    box.hebe_ab("v3")
    box.auflege(UID_BAER, "v4")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.serie_id, a.datei, a.position_s) == (S_BAER, "x.wav", 2.0)


def test_neue_serie_nach_beendeter_folge_laeuft_an_der_naechsten_folge(box):
    box.auflege(UID_BAER)
    box.laufe(10.5)
    assert box.modus == "beendet" and serie(box, S_BAER)["folge"] == "y.wav"
    box.hebe_ab()
    box.auflege(UID_RABE, "v2")
    box.laufe(2.0)
    box.hebe_ab("v2")
    n = len(box.log)
    box.auflege(UID_BAER, "v3")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.serie_id, a.datei, a.position_s) == (S_BAER, "y.wav", 0.0)  # die nächste Folge


def test_serie_zu_folgen_tobie_alter_serien_zeiger_bleibt_folge_ohne_zeiger_beginnt_am_anfang(box):
    box.auflege(UID_RABE)
    box.laufe(6.0)
    n = len(box.log)
    box.auflege(UID_RABE_FOLGE, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.tracks, a.track, a.position_s) == ("b.wav", ("b.wav",), 0, 0.0)
    z = serie(box, S_RABE)
    assert (z["folge"], z["position_s"]) == ("a.wav", 6.0)
    box.laufe(4.0)
    box.hebe_ab("v2")
    assert serie(box, S_RABE)["position_s"] == 6.0  # Serien-Zeiger unberührt
    assert box.resume_json()["folgen"][S_RABE]["b.wav"]["position_s"] == 4.0


def test_folgen_tobie_zu_folgen_tobie_beide_zeiger_bleiben(box):
    box.auflege(UID_RABE_FOLGE)
    box.laufe(5.0)
    box.auflege(UID_BAER_FOLGE, "v2")
    box.laufe(2.0)
    box.hebe_ab("v2")
    folgen = box.resume_json()["folgen"]
    assert folgen[S_RABE]["b.wav"]["position_s"] >= 4.0
    assert folgen[S_BAER]["y.wav"]["position_s"] == 2.0
    n = len(box.log)
    box.auflege(UID_RABE_FOLGE, "v3")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.serie_id, a.datei) == (S_RABE, "b.wav") and a.position_s >= 1.0


def test_folgen_tobie_nach_ihrem_ende_beim_wechsel_zurueck_von_vorn(box):
    box.auflege(UID_RABE_FOLGE)
    box.laufe(10.5)
    assert box.modus == "beendet"
    box.hebe_ab()
    box.auflege(UID_BAER, "v2")
    box.laufe(2.0)
    box.hebe_ab("v2")
    n = len(box.log)
    box.auflege(UID_RABE_FOLGE, "v3")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0)


def test_wechsel_nach_neustart_beide_zeiger_sind_da(box):
    box.auflege(UID_RABE)
    box.laufe(6.0)
    box.auflege(UID_BAER, "v2")
    box.laufe(5.0)
    box.hebe_ab("v2")
    box.neustart_nach_einschalten()
    n = len(box.log)
    box.auflege(UID_RABE, "v3")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.serie_id, a.position_s) == (S_RABE, 3.0)
    box.auflege(UID_BAER, "v4")
    a = box.befehle(ev.Abspielen, n)[-1]
    assert (a.serie_id, a.position_s) == (S_BAER, 2.0)


def test_unbekannter_tobie_beruehrt_die_zeiger_nicht(box):
    box.auflege(UID_RABE)
    box.laufe(6.0)
    box.hebe_ab()
    vorher = dict(serie(box, S_RABE))
    box.auflege(UID_UNBEKANNT, "v2")
    box.laufe(1.0)
    box.hebe_ab("v2")
    assert serie(box, S_RABE) == vorher
