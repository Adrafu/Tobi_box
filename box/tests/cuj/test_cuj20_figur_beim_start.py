"""CUJ 20: Tobie liegt beim Start; Dienst-Neustart mit liegendem Tobie (Entscheidung G, 06.11.).

Nach einem echten Einschalten (andere Kennung des Starts) startet ein liegender Tobie sofort.
Nach einem Dienst-Neustart ohne Ausschalten (Update, Absturz, ``systemctl restart``) startet er nie
von selbst: Die Sitzung bleibt ``pausiert``, der Hauptknopf spielt am gespeicherten Zeiger.
Echter Kern, echte Bibliothek, echtes ``resume.json`` und echter Marker ``lauf.json``.
"""

from __future__ import annotations

import json

import pytest
from conftest import CujBox
from fixtures import audio

from tobibox import events as ev
from tobibox import lauf

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"
UID_ANDERS = "04a1b2c4"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    zuordnungen = {UID: ev.Zuordnung("serie", SERIE), UID_ANDERS: ev.Zuordnung("serie", SERIE)}
    return CujBox(tmp_path, zuordnungen, aufbau, boot_id="boot-1")


def marker(box) -> dict:
    return json.loads((box.zustand / "lauf.json").read_text(encoding="utf-8"))


def ohne_wiedergabe(box, n):
    assert box.befehle(ev.Abspielen, n) == []
    assert not box.player.spielt


def spiele_und_merke(box):
    box.auflege(UID)
    box.laufe(10.0)  # Zeiger mitten in Folge 1
    box.laufe(1.0)


def test_cuj20_einschalten_ein_liegender_tobie_startet_sofort(box):
    box.neustart_nach_einschalten()
    n = len(box.log)
    box.auflege(UID, "v9")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.vorgang) == ("a.wav", "v9") and box.modus == "spielt"


def test_dienst_neustart_mit_liegendem_tobie_bleibt_pausiert_und_hauptknopf_spielt_am_zeiger(box):
    spiele_und_merke(box)
    assert marker(box) == {"boot_id": "boot-1", "uid": UID}
    # Dienst-Neustart ohne Abheben (DienstEndet speichert den Zeiger), gleiche Kennung des Starts
    box.sende(ev.DienstEndet())
    gespeichert = box.befehle(ev.ZeigerSpeichern)[-1]
    assert gespeichert.position_s > 3.0
    box.neustart()
    n = len(box.log)
    assert box.kern.session.neustart_uid == UID
    box.auflege(UID, "v2")  # derselbe Tobie liegt noch
    ohne_wiedergabe(box, n)
    assert box.modus == "pausiert" and box.kern.session.figur.uid == UID
    assert [b for b in box.log[n:] if isinstance(b, ev.TonSpielen)] == []
    box.laufe(5.0)
    ohne_wiedergabe(box, n)  # auch nach Wartezeit startet nichts
    box.sende(ev.Hauptknopf("kurz"))
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.datei == "a.wav" and a.position_s == pytest.approx(max(0.0, gespeichert.position_s - 3.0))
    assert box.modus == "spielt"


def test_dienst_neustart_abheben_und_wieder_auflegen_spielt(box):
    spiele_und_merke(box)
    box.neustart()
    box.auflege(UID, "v2")
    n = len(box.log)
    box.hebe_ab("v2")
    box.auflege(UID, "v3")
    assert len(box.befehle(ev.Abspielen, n)) == 1 and box.modus == "spielt"


def test_absturz_ohne_dienst_endet_marker_vom_auflegen_genuegt(box):
    box.auflege(UID)
    box.laufe(3.0)
    # kein DienstEndet, kein Speichern beim Beenden: der Marker stammt vom Auflegen
    assert marker(box) == {"boot_id": "boot-1", "uid": UID}
    box.neustart()
    n = len(box.log)
    box.auflege(UID, "v2")
    ohne_wiedergabe(box, n)
    assert box.modus == "pausiert"


def test_marker_nach_abheben_hat_keinen_tobie_dann_startet_der_neue_normal(box):
    box.auflege(UID)
    box.hebe_ab()
    assert marker(box)["uid"] is None
    box.neustart()
    n = len(box.log)
    box.auflege(UID, "v2")
    assert len(box.befehle(ev.Abspielen, n)) == 1


def test_anderer_tobie_nach_dem_neustart_startet_sofort(box):
    box.auflege(UID)
    box.neustart()
    n = len(box.log)
    box.auflege(UID_ANDERS, "v2")
    assert len(box.befehle(ev.Abspielen, n)) == 1


def test_marker_unlesbar_gilt_einschalten(box):
    box.auflege(UID)
    (box.zustand / "lauf.json").write_text("{kaputt", encoding="utf-8")
    box.neustart()
    n = len(box.log)
    box.auflege(UID, "v2")
    assert len(box.befehle(ev.Abspielen, n)) == 1 and box.modus == "spielt"


def test_marker_ohne_boot_id_der_gleichen_art_gilt_einschalten(box):
    box.auflege(UID)
    (box.zustand / "lauf.json").write_text(json.dumps({"uid": UID}), encoding="utf-8")
    box.neustart()
    assert box.kern.session.neustart_uid is None


def test_kennung_des_starts_nicht_lesbar_gilt_einschalten(box):
    box.auflege(UID)
    box.boot_id = None
    box.neustart()
    assert box.kern.session.neustart_uid is None


def test_herunterfahren_loescht_den_marker_dann_gilt_einschalten(box):
    box.auflege(UID)
    lauf.loesche(box.zustand)  # das Herunterfahren der App tut genau das
    assert not (box.zustand / "lauf.json").exists()
    box.neustart()
    assert box.kern.session.neustart_uid is None
