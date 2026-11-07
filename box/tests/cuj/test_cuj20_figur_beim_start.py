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
UID_FOLGE = "04a1b2c5"  # Folge b.wav
UID_UNBEKANNT = "04ffeedd"
UEBERRASCHUNG = "c07d2e91a45b"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    zuordnungen = {
        UID: ev.Zuordnung("serie", SERIE),
        UID_ANDERS: ev.Zuordnung("serie", SERIE),
        UID_FOLGE: ev.Zuordnung("folge", SERIE, "b.wav"),
    }
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


# --- AP 2.1: Tobie liegt beim Start ----------------------------------------------------------


def test_einschalten_bekannter_tobie_liegt_schon_spielt_am_gespeicherten_zeiger(box):
    spiele_und_merke(box)
    box.hebe_ab()
    gespeichert = box.resume_json()["serien"][SERIE]["position_s"]
    box.neustart_nach_einschalten()  # Gerät war aus; der Tobie lag die ganze Zeit
    n = len(box.log)
    box.auflege(UID, "v2")  # der Leser meldet ihn nach dem Start
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("a.wav", pytest.approx(max(0.0, gespeichert - 3.0)))
    assert box.modus == "spielt"


def test_einschalten_unbekannter_tobie_liegt_schon_spielt_die_ueberraschung(box):
    box.neustart_nach_einschalten()
    n = len(box.log)
    box.auflege(UID_UNBEKANNT, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == UEBERRASCHUNG and a.datei == "ton.wav"
    assert box.modus == "spielt"


def test_einschalten_ohne_zeiger_beginnt_bei_folge_1(box):
    box.neustart_nach_einschalten()
    n = len(box.log)
    box.auflege(UID, "v2")
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("a.wav", 0.0)


def test_dienst_neustart_unbekannter_tobie_bleibt_pausiert_ohne_ueberraschung(box):
    box.auflege(UID_UNBEKANNT)
    box.laufe(1.0)
    assert box.modus == "spielt"
    box.neustart()
    n = len(box.log)
    box.auflege(UID_UNBEKANNT, "v2")
    ohne_wiedergabe(box, n)
    assert box.modus == "pausiert"
    box.sende(ev.Hauptknopf("kurz"))  # Hauptknopf spielt die Überraschung
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == UEBERRASCHUNG


def test_dienst_neustart_folgen_tobie_pausiert_hauptknopf_spielt_am_folgen_zeiger(box):
    box.auflege(UID_FOLGE)
    box.laufe(9.0)
    box.sende(ev.DienstEndet())
    gespeichert = box.befehle(ev.ZeigerSpeichern)[-1].position_s
    box.neustart()
    n = len(box.log)
    box.auflege(UID_FOLGE, "v2")
    ohne_wiedergabe(box, n)
    assert box.modus == "pausiert"
    box.sende(ev.Hauptknopf("kurz"))
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("b.wav", pytest.approx(gespeichert - 3.0))


def test_dienst_neustart_nach_folgenende_hauptknopf_spielt_die_naechste_folge(box):
    box.auflege(UID)
    box.laufe(20.5)  # a.wav zu Ende: Zeiger auf b.wav
    assert box.modus == "beendet"
    box.neustart()
    n = len(box.log)
    box.auflege(UID, "v2")
    ohne_wiedergabe(box, n)
    assert box.modus == "pausiert"
    box.sende(ev.Hauptknopf("kurz"))
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0)


def test_dienst_neustart_zweiter_neustart_bleibt_pausiert(box):
    spiele_und_merke(box)
    box.neustart()
    box.auflege(UID, "v2")
    assert box.modus == "pausiert"
    box.sende(ev.DienstEndet())
    box.neustart()  # Tobie liegt weiter, der Marker nennt ihn weiter
    n = len(box.log)
    box.auflege(UID, "v3")
    ohne_wiedergabe(box, n)
    assert box.modus == "pausiert"


def test_dienst_neustart_tobie_war_inzwischen_abgehoben_und_anderer_liegt_startet_sofort(box):
    spiele_und_merke(box)
    box.neustart()
    n = len(box.log)
    box.auflege(UID_FOLGE, "v2")  # nicht der Tobie aus dem Marker
    assert len(box.befehle(ev.Abspielen, n)) == 1 and box.modus == "spielt"


# --- gesperrter Tobie (Befund 1 des Probelaufs) ----------------------------------------------


def test_dienst_neustart_gesperrter_tobie_bleibt_pausiert_auf_der_ueberraschung(box):
    box.sende(ev.Gesperrt(0, "v1"))
    box.laufe(0.5)
    assert box.modus == "spielt"
    assert marker(box) == {"boot_id": "boot-1", "uid": None, "gesperrt": True}
    box.neustart()
    n = len(box.log)
    assert box.kern.session.neustart_uid == ev.NEUSTART_GESPERRT
    box.sende(ev.Gesperrt(0, "v2"))  # der Leser meldet ihn nach dem Start erneut
    ohne_wiedergabe(box, n)
    assert box.modus == "pausiert" and box.kern.session.figur.art == "gesperrt"
    assert [b for b in box.log[n:] if isinstance(b, ev.TonSpielen)] == []
    box.laufe(5.0)
    ohne_wiedergabe(box, n)  # auch nach Wartezeit startet nichts
    box.sende(ev.Hauptknopf("kurz"))  # der Hauptknopf spielt die Überraschung
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == UEBERRASCHUNG


def test_einschalten_gesperrter_tobie_spielt_die_ueberraschung(box):
    box.sende(ev.Gesperrt(0, "v1"))
    box.neustart_nach_einschalten()
    assert box.kern.session.neustart_uid is None
    n = len(box.log)
    box.sende(ev.Gesperrt(0, "v2"))
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == UEBERRASCHUNG and box.modus == "spielt"


def test_dienst_neustart_gesperrt_lag_aber_jetzt_liegt_ein_anderer_startet_sofort(box):
    box.sende(ev.Gesperrt(0, "v1"))
    box.neustart()
    n = len(box.log)
    box.auflege(UID, "v2")
    assert len(box.befehle(ev.Abspielen, n)) == 1 and box.modus == "spielt"
