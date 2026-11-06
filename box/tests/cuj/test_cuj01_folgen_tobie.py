"""CUJ 1 und 3 für einen Tobie auf eine einzelne Folge (AP 1.7, Entscheidung F, 05.11.).

Der Tobie spielt genau seine Folge; am Ende Pause und der Folgen-Zeiger springt auf den Anfang;
erneutes Auflegen spielt von vorn; der Serien-Zeiger derselben Serie bleibt unberührt.
Echter Kern, echte Bibliothek und echtes ``resume.json`` aus erzeugten Dateien (kein Audio im Repo).
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import audio

from tobibox import events as ev

SERIE = "3f9a1c07b2d4"
UID_FOLGE = "04a1b2c3"  # Tobie auf Folge „b.wav“
UID_SERIE = "04a1b2c4"  # Tobie auf die ganze Serie
UID_UNBEKANNT = "04ffeedd"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=6.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    zuordnungen = {
        UID_FOLGE: ev.Zuordnung("folge", SERIE, "b.wav"),
        UID_SERIE: ev.Zuordnung("serie", SERIE),
    }
    return CujBox(tmp_path, zuordnungen, aufbau)


def abspielen_ab(box, n=0):
    return box.befehle(ev.Abspielen, n)


def test_folgen_tobie_spielt_genau_seine_folge_mit_vorgangs_id(box):
    box.auflege(UID_FOLGE, "abc12345")
    (a,) = abspielen_ab(box)
    assert (a.serie_id, a.datei, a.tracks, a.track, a.position_s, a.vorgang) == (
        SERIE, "b.wav", ("b.wav",), 0, 0.0, "abc12345",
    )
    assert box.modus == "spielt"
    assert box.player.warteschlangen == [("b.wav",)]  # nur diese Folge


def test_am_ende_pause_und_folgen_zeiger_zurueck_auf_den_anfang(box):
    box.auflege(UID_FOLGE)
    box.laufe(3.0)
    box.hebe_ab()
    gespeichert = box.resume_json()["folgen"][SERIE]["b.wav"]
    assert (gespeichert["track"], gespeichert["position_s"]) == (0, 3.0)  # mitten in der Folge
    box.auflege(UID_FOLGE, "v2")  # 3,0 s gespeichert, 3 s Rücksprung: beginnt bei 0,0 s
    box.laufe(6.2)
    assert box.modus == "beendet"
    assert [p.grund for p in box.befehle(ev.Pausieren)].count("folgenende") == 1
    assert not box.player.spielt  # MPD ist gestoppt, nichts spielt weiter
    z = box.resume_json()["folgen"][SERIE]["b.wav"]
    assert (z["track"], z["position_s"]) == (0, 0.0)
    assert box.kern.session.figur is not None  # der Tobie liegt noch


def test_erneutes_auflegen_nach_dem_ende_spielt_von_vorn_ohne_ruecksprung(box):
    box.auflege(UID_FOLGE)
    box.laufe(6.5)
    assert box.modus == "beendet"
    box.hebe_ab()
    n = len(box.log)
    box.auflege(UID_FOLGE, "v2")
    (a,) = abspielen_ab(box, n)
    assert (a.datei, a.track, a.position_s) == ("b.wav", 0, 0.0)
    assert box.modus == "spielt"


def test_hauptknopf_nach_dem_ende_spielt_dieselbe_folge_von_vorn(box):
    box.auflege(UID_FOLGE)
    box.laufe(6.5)
    n = len(box.log)
    box.sende(ev.Hauptknopf("kurz"))
    (a,) = abspielen_ab(box, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0) and box.modus == "spielt"


def test_serien_zeiger_derselben_serie_bleibt_unberuehrt(box):
    box.auflege(UID_SERIE)
    box.laufe(2.0)
    box.hebe_ab()
    serien_zeiger = dict(box.resume_json()["serien"][SERIE])
    assert serien_zeiger["folge"] == "a.wav" and serien_zeiger["position_s"] == 2.0

    # Folgen-Tobie: Folge b.wav durchspielen, mehrfach auflegen
    box.auflege(UID_FOLGE, "v2")
    box.laufe(6.5)
    assert box.modus == "beendet"
    box.hebe_ab("v2")
    box.auflege(UID_FOLGE, "v3")
    box.laufe(1.0)
    box.hebe_ab("v3")
    assert box.resume_json()["serien"][SERIE] == serien_zeiger  # Wort für Wort unverändert, auch der Zähler

    # der Serien-Tobie macht an seinem eigenen Zeiger weiter (a.wav, 3 s Rücksprung)
    n = len(box.log)
    box.auflege(UID_SERIE, "v4")
    (a,) = abspielen_ab(box, n)
    assert (a.datei, a.position_s) == ("a.wav", 0.0)  # 2,0 - 3,0 -> 0


def test_resume_im_folgen_tobie_nach_neustart_des_dienstes(box):
    box.auflege(UID_FOLGE)
    box.laufe(4.5)
    box.hebe_ab()
    box.neustart()
    assert box.modus == "leer"
    n = len(box.log)
    box.auflege(UID_FOLGE, "v2")
    (a,) = abspielen_ab(box, n)
    assert (a.datei, a.track, a.position_s) == ("b.wav", 0, 1.0)  # 4,0 s gespeichert (Position höchstens 1 s alt), 3 s Rücksprung


def test_folge_nach_dem_ende_und_neustart_beginnt_der_folgen_tobie_von_vorn(box):
    box.auflege(UID_FOLGE)
    box.laufe(6.5)
    box.neustart_nach_einschalten()  # Gerät war aus (CUJ 20: liegender Tobie startet); „beendet“ wird nicht gespeichert
    assert box.modus == "leer"
    box.auflege(UID_FOLGE, "v2")
    (a,) = abspielen_ab(box, len(box.log) - 2)
    assert (a.datei, a.position_s) == ("b.wav", 0.0)


def test_folgen_tobie_auf_fehlende_folge_spielt_die_ueberraschung_ohne_melden(tmp_path):
    zuordnungen = {UID_FOLGE: ev.Zuordnung("folge", SERIE, "gibt-es-nicht.wav")}
    box = CujBox(tmp_path, zuordnungen, aufbau)
    box.auflege(UID_FOLGE)
    (a,) = abspielen_ab(box)
    assert a.datei == "ton.wav" and a.serie_id == "c07d2e91a45b"
    assert not box.befehle(ev.Melden)
    assert any(p.ereignis == "folge_fehlt" for p in box.protokoll)


def test_unbekannter_tobie_spielt_die_ueberraschung_wie_ein_serien_tobie(box):
    box.auflege(UID_UNBEKANNT)
    (a,) = abspielen_ab(box)
    assert a.serie_id == "c07d2e91a45b" and box.kern.session.ziel == "serie"
    box.laufe(2.5)
    assert box.modus == "beendet"
    z = box.resume_json()["serien"]["c07d2e91a45b"]
    assert z["folge"] == "ton.wav" and z["position_s"] == 0.0  # einzige Folge: zyklisch wieder Folge 1
