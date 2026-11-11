"""CUJ 23: Box steht am Sockel bereit, CUJ 24: Pause ohne Sockel, nach 10 min aus (Ein/Aus, 10.11.; AP E1-7).

Echter Kern mit ``idle``; die Zeit springt in Takten. Das Wecken durch den Leser (Schritt 2) ist nicht Teil dieser Tests.
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import stufe4

from tobibox import events as ev

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"
MIN = 60.0


def aufbau(medien):
    stufe4.serie(medien, "rabe", ["a.wav", "b.wav"], SERIE, "Rabe", 200.0)
    stufe4.ueberraschung(medien)


@pytest.fixture
def box(tmp_path):
    return CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)


def warte(box, s):
    return box.sende(ev.Takt(), dt=s)


def fahren(box, ab=0):
    return box.befehle(ev.Herunterfahren, ab)


# --- CUJ 23 -----------------------------------------------------------------------------------------------


def test_am_sockel_bereit_ohne_frist_nie_von_selbst_aus(box):
    box.sende(ev.LaderGeaendert(True))
    for _ in range(10):
        warte(box, 60 * MIN)
    assert fahren(box) == [] and stufe4.zeile(box).strom == "leerlauf"


def test_am_sockel_ein_aufgelegter_tobie_spielt(box):
    box.sende(ev.LaderGeaendert(True))
    warte(box, 3 * 60 * MIN)
    n = len(box.log)
    box.auflege(UID)
    assert box.befehle(ev.Abspielen, n) and box.modus == "spielt"


def test_pisugar_server_haengt_der_leser_liefert_den_wert_allein(box):
    """Nur ``LaderGeaendert(quelle="leser")``, von ``pisugar-server`` kommt nie etwas: die Box bleibt am Sockel bereit."""
    box.sende(ev.LaderGeaendert(True, "leser"))
    warte(box, 100 * MIN)
    assert fahren(box) == []


def test_keine_quelle_liefert_einen_wert_nach_60_s_kein_strom_dann_10_min(box):
    warte(box, 59)
    assert fahren(box) == []
    warte(box, 2)  # 61 s: „unbekannt“ gilt als „kein Strom“, der Zähler beginnt
    warte(box, 10 * MIN - 5)
    assert fahren(box) == []
    warte(box, 10)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_hauptknopf_lang_am_sockel_faehrt_herunter(box):
    box.sende(ev.LaderGeaendert(True))
    box.sende(ev.Hauptknopf("lang"))
    assert [b.grund for b in fahren(box)] == ["hauptknopf"]


def test_strom_kommt_waehrend_die_box_herunterfaehrt_kein_ton_kein_zweites_herunterfahren(box):
    """Das Wiederanlaufen folgt mit Schritt 2 (Leser); hier: keine Rückmeldung, der Zustand bleibt ``herunterfahren``."""
    box.sende(ev.LaderGeaendert(False))
    warte(box, 30)
    box.sende(ev.Hauptknopf("lang"))
    n = len(box.log)
    box.sende(ev.LaderGeaendert(True))
    assert not box.befehle(ev.TonSpielen, n) and not box.befehle(ev.SyncStarten, n) and not fahren(box, n)
    assert stufe4.zeile(box).strom == "herunterfahren"


def test_akku_tiefstand_am_sockel_wird_ignoriert(box):
    box.sende(ev.LaderGeaendert(True))
    n = len(box.log)
    box.sende(ev.AkkuTiefstand())
    assert fahren(box, n) == []


# --- CUJ 24 -----------------------------------------------------------------------------------------------


@pytest.fixture
def ohne_sockel(box):
    box.sende(ev.LaderGeaendert(False))
    return box


def test_pause_ohne_sockel_nach_10_min_herunterfahren_zeiger_gespeichert(ohne_sockel):
    box = ohne_sockel
    box.auflege(UID)
    box.laufe(8.0)
    box.sende(ev.Hauptknopf("kurz"))  # Pause, der Tobie liegt
    assert box.modus == "pausiert"
    warte(box, 10 * MIN - 5)
    assert fahren(box) == []
    n = len(box.log)
    warte(box, 10)
    assert [b.grund for b in fahren(box, n)] == ["leerlauf"]
    assert box.resume_json()["serien"][SERIE]["position_s"] > 0  # der Zeiger wurde bei der Pause gespeichert


def test_in_den_10_min_wird_ein_tobie_aufgelegt_die_box_spielt_und_die_frist_beginnt_danach_neu(ohne_sockel):
    box = ohne_sockel
    warte(box, 9 * MIN)
    box.auflege(UID)
    assert box.modus == "spielt"
    box.laufe(30)
    box.hebe_ab()  # Abnehmen: die Frist beginnt ab hier
    warte(box, 10 * MIN - 5)
    assert fahren(box) == []
    warte(box, 10)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_in_den_10_min_wird_etwas_bedient_die_frist_beginnt_neu(ohne_sockel):
    box = ohne_sockel
    warte(box, 9 * MIN)
    box.sende(ev.LautstaerkeDrehen(2))
    warte(box, 9 * MIN)
    assert fahren(box) == []
    warte(box, MIN + 1)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


@pytest.mark.parametrize(
    "anfang, ende",
    [
        (ev.SyncGestartet(), ev.SyncFertig(1, 0)),
        (ev.UpdateGestartet("1.2.0"), ev.SelbsttestErgebnis(True)),
    ],
)
def test_sync_und_update_halten_die_abschaltung_auf(ohne_sockel, anfang, ende):
    box = ohne_sockel
    box.sende(anfang)
    warte(box, 3 * 10 * MIN)
    assert fahren(box) == []
    box.sende(ende)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_lernmodus_haelt_die_abschaltung_auf(ohne_sockel):
    box = ohne_sockel
    warte(box, 9 * MIN)
    box.sende(ev.HaLernmodus("b1", box.uhr.wall + 600))
    warte(box, 3 * MIN)  # Lernmodus ohne Tobie läuft nach 2 min ab, der Zähler beginnt neu
    assert fahren(box) == []
    warte(box, 10 * MIN + 1)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


# --- Start durch Strom (HW8, 11.11.) ---------------------------------------------------------------------


def test_hw8_start_am_sockel_liegender_tobie_bleibt_still_dann_spielt_ein_neu_aufgelegter(box):
    """CUJ 23 mit CUJ 20: Die Box startet am Sockel (Strom), der Tobie liegt schon: still bereit. Neu auflegen oder Hauptknopf startet."""
    box.neustart_nach_einschalten()
    n = len(box.log)
    box.sende(ev.LaderGeaendert(True, "leser"))
    box.auflege(UID, "v2")
    assert box.befehle(ev.Abspielen, n) == [] and box.modus == "pausiert"
    warte(box, 3 * 60 * MIN)
    assert fahren(box) == [] and box.befehle(ev.Abspielen, n) == []  # am Sockel bleibt sie bereit
    box.hebe_ab("v2")
    box.auflege(UID, "v3")
    assert box.befehle(ev.Abspielen, n) and box.modus == "spielt"


def test_hw8_start_ohne_strom_messung_keine_quelle_der_tobie_spielt(box):
    """Liefert keine Quelle einen Wert (``pisugar-server`` hängt, kein ``LADER``), gilt „ohne Strom“: der Tobie spielt wie bisher."""
    box.neustart_nach_einschalten()
    n = len(box.log)
    box.auflege(UID, "v2")
    assert box.befehle(ev.Abspielen, n) and box.modus == "spielt"
