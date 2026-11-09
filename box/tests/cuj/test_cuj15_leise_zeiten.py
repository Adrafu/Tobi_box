"""CUJ 15: Leise-Zeiten (AP 4.5 und 4.8).

Die Einstellung kommt wie von HA als neue Konfiguration (``KonfigGeladen``). Die Wanduhr der ``SimUhr`` wird gestellt, der Takt läuft.
Fenster: ``abend`` (leiser, 19:30 bis 21:00, Grenze 25) und ``nacht`` (stumm, 22:00 bis 07:00). Startlautstärke 40.
2026-11-09 ist ein Montag.
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import stufe4
from fixtures.stufe4 import wall

from tobibox import events as ev

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"
UID_B = "04a1b2c4"
FENSTER = (
    stufe4.fenster("abend", "leiser", "19:30", "21:00", 25),
    stufe4.fenster("nacht", "stumm", "22:00", "07:00"),
)


def aufbau(medien):
    stufe4.serie(medien, "rabe", ["a.wav", "b.wav"], SERIE, "Rabe", 200.0)
    stufe4.ueberraschung(medien)


@pytest.fixture
def box(tmp_path):
    b = CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE), UID_B: ev.Zuordnung("serie", SERIE)}, aufbau)
    stufe4.setze_konfig(b, fenster_liste=FENSTER)
    b.uhr.setze_wall(wall(2026, 11, 9, 18, 0))
    b.laufe(0.2)
    return b


def um(box, h, m, s=0, dauer=3.5):
    """Wanduhr stellen und laufen lassen (ein Absenken wegen „leiser“ dauert 3 s)."""
    box.uhr.setze_wall(wall(2026, 11, 9, h, m, s))
    box.laufe(dauer)


def test_ausserhalb_der_fenster_gilt_die_normale_grenze(box):
    z = stufe4.zeile(box)
    assert z.ruhe == "normal" and "leise_zeit" not in box.kern.grenzen


def test_leiser_fenster_beginnt_laute_wiedergabe_wird_sanft_abgesenkt(box):
    box.auflege(UID)
    box.laufe(5.0)
    um(box, 19, 29, 59, dauer=0.2)
    n = len(box.log)
    box.laufe(1.0)  # 19:30:00 erreicht
    assert stufe4.zeile(box).ruhe == "leiser"
    box.laufe(4.0)
    werte = stufe4.prozente(box, n)
    assert werte and werte[0] > 25 and werte[-1] == 25  # sanft: Zwischenwerte, kein Sprung
    assert len(set(werte)) > 3 and werte == sorted(werte, reverse=True)
    assert stufe4.wirksam(box) == 25
    assert box.modus == "spielt" and box.player.spielt  # die Wiedergabe läuft weiter, nur leiser


def test_leiser_fenster_auflegen_im_fenster_startet_mit_der_fenster_grenze(box):
    um(box, 20, 0)
    assert stufe4.zeile(box).ruhe == "leiser"
    n = len(box.log)
    box.auflege(UID)
    vor_abspielen = [b for b in box.log[n:] if isinstance(b, (ev.LautstaerkeSetzen, ev.Abspielen))]
    assert isinstance(vor_abspielen[0], ev.LautstaerkeSetzen) and vor_abspielen[0].prozent == 25
    assert isinstance(vor_abspielen[1], ev.Abspielen)


def test_drehregler_im_leiser_fenster_geht_nie_ueber_die_fenster_grenze(box):
    um(box, 20, 0)
    box.auflege(UID)
    for _ in range(5):
        box.sende(ev.LautstaerkeDrehen(+10))
    assert stufe4.wirksam(box) == 25
    assert max(stufe4.prozente(box)) <= 40  # Startwert; nach dem Fenster nie darüber


def test_nach_dem_fenster_gilt_wieder_die_normale_grenze(box):
    box.auflege(UID)
    um(box, 20, 0)
    assert stufe4.wirksam(box) == 25
    um(box, 21, 0, 1, dauer=0.5)
    assert stufe4.zeile(box).ruhe == "normal"
    assert stufe4.wirksam(box) == 40
    assert stufe4.lautstaerken(box)[-1].prozent == 40


def test_stumm_beginnt_waehrend_der_wiedergabe_ausblenden_pause_zeiger_gespeichert(box):
    box.auflege(UID)
    um(box, 21, 59, 58, dauer=0.2)
    n = len(box.log)
    box.laufe(1.0)
    assert box.modus == "spielt"  # 21:59:59, noch nichts
    box.laufe(5.0)
    assert stufe4.zeile(box).ruhe == "stumm"
    assert box.modus == "gehalten" and not box.player.spielt
    werte = stufe4.prozente(box, n)
    assert werte and werte == sorted(werte, reverse=True) and werte[-1] < 40  # sanft ausgeblendet
    assert [p.grund for p in box.befehle(ev.Pausieren, n)] == ["stumm"]
    assert box.resume_json()["serien"][SERIE]["position_s"] > 0


def test_auflegen_im_stumm_fenster_nur_hinweiston_nichts_spielt(box):
    um(box, 23, 0)
    n = len(box.log)
    box.auflege(UID)
    assert box.modus == "gehalten"
    assert box.befehle(ev.Abspielen, n) == [] and not box.player.spielt
    assert [t.ton for t in box.befehle(ev.TonSpielen, n)] == ["hinweis"]


def test_im_stumm_fenster_tasten_starten_nichts(box):
    um(box, 23, 0)
    box.auflege(UID)
    n = len(box.log)
    for e in (ev.Hauptknopf("kurz"), ev.Weiter(), ev.Zurueck()):
        box.sende(e)
    assert box.befehle(ev.Abspielen, n) == [] and not box.player.spielt


def test_stumm_endet_bei_liegendem_tobie_nichts_startet_von_selbst(box):
    um(box, 23, 0)
    box.auflege(UID)
    n = len(box.log)
    box.uhr.setze_wall(wall(2026, 11, 10, 7, 0, 1))
    box.laufe(1.0)
    assert stufe4.zeile(box).ruhe == "normal"
    assert box.modus == "pausiert" and box.befehle(ev.Abspielen, n) == []
    box.hebe_ab()
    box.auflege(UID, "v2")  # erst Abheben und erneutes Auflegen startet
    assert box.player.spielt


def test_unsichere_uhr_kleinste_leiser_grenze_nie_stumm(box):
    box.uhr.setze_wall(wall(2026, 11, 9, 23, 0))  # eigentlich stumm
    box.uhr.setze_zeit("unbekannt", False)
    box.laufe(3.5)
    z = stufe4.zeile(box)
    assert z.ruhe == "leiser"
    assert stufe4.wirksam(box) == 25 and box.kern.grenzen["leise_zeit"] == 25
    n = len(box.log)
    box.auflege(UID)
    assert box.modus == "spielt" and box.player.spielt  # nie stumm
    assert box.befehle(ev.Abspielen, n)
    assert stufe4.wirksam(box) <= 25


def test_unsichere_uhr_ohne_leiser_fenster_gilt_die_normale_grenze(box):
    stufe4.setze_konfig(box, fenster_liste=(FENSTER[1],), revision=3)
    box.uhr.setze_zeit("unbekannt", False)
    box.laufe(0.5)
    assert stufe4.zeile(box).ruhe == "normal"


def test_zeit_wieder_vertrauenswuerdig_wirkung_nach_uhrzeit(box):
    box.uhr.setze_wall(wall(2026, 11, 9, 23, 0))
    box.uhr.setze_zeit("unbekannt", False)
    box.laufe(0.5)
    assert stufe4.zeile(box).ruhe == "leiser"
    box.uhr.setze_zeit("ntp", True)
    box.laufe(0.5)
    assert stufe4.zeile(box).ruhe == "stumm"


def test_aenderung_der_konfiguration_gilt_sofort(box):
    um(box, 20, 0)
    assert stufe4.zeile(box).ruhe == "leiser"
    stufe4.setze_konfig(box, fenster_liste=(), revision=3)  # HA hat alle Fenster gelöscht
    assert stufe4.zeile(box).ruhe == "normal" and "leise_zeit" not in box.kern.grenzen


def test_wochentage_gelten_nur_an_den_eingestellten_tagen(box):
    nur_dienstag = stufe4.fenster("di", "stumm", "20:00", "21:00", tage=(2,))
    stufe4.setze_konfig(box, fenster_liste=(nur_dienstag,), revision=3)
    um(box, 20, 30)  # Montag
    assert stufe4.zeile(box).ruhe == "normal"
    box.uhr.setze_wall(wall(2026, 11, 10, 20, 30))
    box.laufe(0.2)
    assert stufe4.zeile(box).ruhe == "stumm"
