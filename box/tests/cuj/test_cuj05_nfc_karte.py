"""CUJ 5 (AP 1.6): NFC-Karte. Eine NTAG-Karte verhält sich wie ein Tonie (CUJ 1 bis 4).

Bewiesene Schritte von CUJ 5 (Given: Karte ist einem Ziel zugeordnet; When: Karte auflegen;
Then: Verhalten wie CUJ 1 bis 4). Jeder Test läuft mit der Karte (``type=ntag tonie=0``, 7-Byte-Kennung)
und mit einem entsperrten Tonie (``type=iso15693 tonie=1``, 8-Byte-Kennung) und beweist, dass der Dienst
beide gleich behandelt:

* CUJ 1: Folge 1 ohne Zeiger, mit Vorgangs-ID.
* CUJ 2: Abheben pausiert, Zeiger gespeichert.
* CUJ 3: Wieder auflegen setzt mit 3 s Rücksprung fort.
* CUJ 4: Anderer Tobie (Karte <-> Tonie): Zeiger von A bleibt, B läuft an seinem Zeiger weiter.
* Karte und Tonie derselben Serie teilen den Serien-Zeiger (der Zeiger hängt am Ziel, nicht an der Kennung).
* Eine Karte auf eine einzelne Folge (Folgen-Tobie) hat einen eigenen Folgen-Zeiger (Entscheidung F).

Nicht doppelt geprüft: Details der Folgen-Tobies (``test_cuj01_folgen_tobie.py``).
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import audio

from tobibox import events as ev

SERIE = "3f9a1c07b2d4"
SERIE_B = "5b6c7d8e9f01"
KARTE = "04a1b2c3d4e5f6"  # NTAG, 7 Byte
TONIE = "e0040312345678ab"  # ISO 15693, 8 Byte
KARTE_B = "04ffeedd112233"  # Karte auf die zweite Serie
KARTE_FOLGE = "04a1b2c3d4e5f7"  # Karte auf die Folge b.wav der ersten Serie

ARTEN = {
    "karte": (KARTE, "ntag", False),
    "tonie": (TONIE, "iso15693", True),
}


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    audio.erzeuge_serie(medien, "baer", ["x.wav", "y.wav"], serie_id=SERIE_B, name="Bär", dauer_s=20.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    zuordnungen = {
        KARTE: ev.Zuordnung("serie", SERIE),
        TONIE: ev.Zuordnung("serie", SERIE),
        KARTE_B: ev.Zuordnung("serie", SERIE_B),
        KARTE_FOLGE: ev.Zuordnung("folge", SERIE, "b.wav"),
    }
    b = CujBox(tmp_path, zuordnungen, aufbau)
    b.leser.hello()
    return b


@pytest.fixture(params=sorted(ARTEN))
def art(request):
    return ARTEN[request.param]


def lege(box, art):
    uid, typ, tonie = art
    box.leser.placed(uid, typ, tonie)


def test_cuj1_auflegen_ohne_zeiger_spielt_folge_1(box, art):
    lege(box, art)
    (a,) = box.befehle(ev.Abspielen)
    assert (a.serie_id, a.datei, a.track, a.position_s) == (SERIE, "a.wav", 0, 0.0)
    assert box.kern.session.figur.uid == art[0] and a.vorgang == box.kern.session.figur.vorgang
    assert box.modus == "spielt"
    z = next(p for p in box.protokoll if p.ereignis == "zugeordnet")
    assert (z.ergebnis, z.daten["uid"]) == ("ok", art[0])


def test_cuj2_abheben_pausiert_und_speichert_den_zeiger(box, art):
    lege(box, art)
    box.laufe(8.0)
    box.leser.removed()
    assert [p.grund for p in box.befehle(ev.Pausieren)] == ["abgehoben"] and not box.player.spielt
    z = box.resume_json()["serien"][SERIE]
    assert z["folge"] == "a.wav" and z["position_s"] == pytest.approx(8.0, abs=0.01)


def test_cuj3_wieder_auflegen_setzt_mit_ruecksprung_fort(box, art):
    lege(box, art)
    box.laufe(8.0)
    box.leser.removed()
    n = len(box.log)
    lege(box, art)
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.track) == ("a.wav", 0) and a.position_s == pytest.approx(5.0, abs=0.01)


def test_cuj3_nach_dienst_neustart_und_leerem_akku_auch_mit_karte(box, art):
    lege(box, art)
    box.laufe(8.0)
    box.leser.removed()
    box.neustart_nach_einschalten()  # Gerät war aus
    box.leser.hello()
    n = len(box.log)
    lege(box, art)
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.position_s == pytest.approx(5.0, abs=0.01)


def test_cuj4_wechsel_von_karte_zu_tonie_derselben_serie_und_zu_anderer_serie(box, art):
    uid, typ, tonie = art
    lege(box, art)
    box.laufe(8.0)
    box.leser.removed()
    # anderer Tobie, andere Serie: B ohne Zeiger beginnt vorn, der Zeiger von A bleibt gespeichert
    n = len(box.log)
    box.leser.placed(KARTE_B)
    (b,) = box.befehle(ev.Abspielen, n)
    assert (b.serie_id, b.datei, b.position_s) == (SERIE_B, "x.wav", 0.0)
    box.laufe(4.0)
    box.leser.removed()
    assert box.resume_json()["serien"][SERIE]["position_s"] == pytest.approx(8.0, abs=0.01)  # A bleibt
    assert box.resume_json()["serien"][SERIE_B]["position_s"] == pytest.approx(4.0, abs=0.01)


def test_karte_und_tonie_derselben_serie_teilen_den_serien_zeiger(box):
    box.leser.placed(KARTE, "ntag", False)
    box.laufe(8.0)
    box.leser.removed()
    n = len(box.log)
    box.leser.placed(TONIE, "iso15693", True)
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("a.wav", pytest.approx(5.0, abs=0.01))


def test_karte_auf_einzelne_folge_hat_eigenen_folgen_zeiger_neben_dem_serien_zeiger(box):
    box.leser.placed(KARTE, "ntag", False)
    box.laufe(8.0)
    box.leser.removed()
    n = len(box.log)
    box.leser.placed(KARTE_FOLGE)
    (f,) = box.befehle(ev.Abspielen, n)
    assert (f.datei, f.tracks, f.position_s) == ("b.wav", ("b.wav",), 0.0)  # Folge b.wav, nicht Serien-Zeiger
    box.laufe(6.0)
    box.leser.removed()
    roh = box.resume_json()
    assert roh["folgen"][SERIE]["b.wav"]["position_s"] == pytest.approx(6.0, abs=0.01)
    assert roh["serien"][SERIE]["folge"] == "a.wav"  # Serien-Zeiger unberührt
