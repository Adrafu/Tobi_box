"""CUJ 14: Gute-Nacht-Karte (AP 4.6 und 4.8).

Eine Serie spielt, die Gute-Nacht-Karte ist als Aktion zugeordnet, die Dauern kommen aus der Konfiguration (hier 1 min und 10 s,
damit der Test kurz bleibt). Tobias nimmt die Serie weg, legt die Karte auf, danach die Serie wieder. Mit der Karte startet der Timer,
die Serie spielt weiter; nach Ablauf blendet die Lautstärke aus, dann endet die Wiedergabe (Pause mit gespeichertem Zeiger).

Echter Kern mit ``bedtime``, ``quiet`` und ``idle``; ``LautstaerkeGeaendert`` erreicht ``bedtime``: Das Ausblenden beginnt bei der
wirksamen Lautstärke (40) und nicht bei 100.
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import stufe4

from tobibox import events as ev

SERIE = "3f9a1c07b2d4"
SERIE_B = "5b6c7d8e9f01"
UID = "04a1b2c3"
UID_B = "04a1b2c4"
UID_NACHT = "04c0ffee"
START = 40  # Startlautstärke in ``CujBox`` (``GeraeteEinstellungen(60, 40, 25)``)


def aufbau(medien):
    stufe4.serie(medien, "rabe", ["a.wav", "b.wav"], SERIE, "Rabe", 200.0)
    stufe4.serie(medien, "baer", ["x.wav"], SERIE_B, "Baer", 200.0)
    stufe4.ueberraschung(medien)


@pytest.fixture
def box(tmp_path):
    zuordnungen = {
        UID: ev.Zuordnung("serie", SERIE),
        UID_B: ev.Zuordnung("serie", SERIE_B),
        UID_NACHT: ev.Zuordnung("aktion", aktion="gute_nacht"),
    }
    b = CujBox(tmp_path, zuordnungen, aufbau)
    stufe4.setze_konfig(b, gute_nacht=ev.GuteNacht(1, 10))
    return b


def karte_nach_abheben(box) -> None:
    """Die Schritte von CUJ 14: Serie läuft, abheben, Karte auflegen, abheben, Serie wieder auflegen."""
    box.auflege(UID, "v1")
    box.laufe(10.0)
    box.hebe_ab("v1")
    assert box.modus == "pausiert"
    box.auflege(UID_NACHT, "v2")
    box.laufe(2.0)
    box.hebe_ab("v2")
    box.auflege(UID, "v3")


def bis_ausblenden(box) -> float:
    return stufe4.gehe_bis(box, lambda: stufe4.zeile(box).gute_nacht == "ausblenden", schritt=0.1)


def test_karte_nach_abheben_startet_den_timer_und_die_serie_spielt_weiter(box):
    box.auflege(UID, "v1")
    box.laufe(10.0)
    box.hebe_ab("v1")
    n = len(box.log)
    box.auflege(UID_NACHT, "v2")
    z = stufe4.zeile(box)
    assert z.gute_nacht == "laeuft" and z.sitzung == "pausiert" and z.figur_liegt  # die Karte ist ein Tobie, aber keine Serie
    assert box.befehle(ev.Abspielen, n) == [] and not box.player.spielt
    box.laufe(2.0)
    box.hebe_ab("v2")
    box.auflege(UID, "v3")
    assert box.modus == "spielt" and box.player.spielt
    assert stufe4.zeile(box).gute_nacht == "laeuft"  # der Timer läuft mit der wieder aufgelegten Serie weiter
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == SERIE and a.position_s == pytest.approx(7.0, abs=0.2)  # Resume mit 3 s Rücksprung


def test_vor_ablauf_passiert_nichts_am_ton(box):
    karte_nach_abheben(box)
    n = len(box.log)
    box.laufe(55.0)  # Karte lag vor 2 s + 55 s: Timer (60 s) noch nicht um
    assert stufe4.zeile(box).gute_nacht == "laeuft"
    assert stufe4.lautstaerken(box, n) == []
    assert box.modus == "spielt"


def test_nach_ablauf_blendet_die_lautstaerke_von_der_wirksamen_aus_und_nie_darueber(box):
    karte_nach_abheben(box)
    bis_ausblenden(box)
    n = len(box.log)
    box.laufe(10.5)
    werte = stufe4.prozente(box, n)
    assert werte, "es muss Lautstärke-Befehle geben"
    assert max(werte) <= START  # nie über der wirksamen Grenze
    assert werte[0] >= START - 5  # beginnt bei 40 (LautstaerkeGeaendert kam bei ``bedtime`` an), nicht bei 100 oder 60
    assert werte == sorted(werte, reverse=True)  # fällt nur
    assert werte[-1] <= 2
    for b in stufe4.lautstaerken(box, n):
        assert b.prozent <= b.grenze <= 60


def test_ausblenden_dauert_so_lange_wie_in_der_konfiguration(box):
    karte_nach_abheben(box)
    bis_ausblenden(box)
    n = len(box.log)
    box.laufe(9.0)
    assert box.modus == "spielt"  # 10 s Ausblenden: nach 9 s noch nicht zu Ende
    box.laufe(1.5)
    assert box.modus == "pausiert"
    assert len(box.befehle(ev.Pausieren, n)) == 1


def test_dauer_des_timers_kommt_aus_der_konfiguration(box):
    stufe4.setze_konfig(box, gute_nacht=ev.GuteNacht(2, 20), revision=3)
    box.auflege(UID, "v1")
    box.laufe(1.0)
    box.hebe_ab("v1")
    box.auflege(UID_NACHT, "v2")
    box.hebe_ab("v2")
    box.auflege(UID, "v3")
    box.laufe(118.0)
    assert stufe4.zeile(box).gute_nacht == "laeuft"
    box.laufe(3.0)
    assert stufe4.zeile(box).gute_nacht == "ausblenden"


def test_ende_pausiert_speichert_den_zeiger_und_die_lautstaerke_springt_nicht_zurueck(box):
    karte_nach_abheben(box)
    bis_ausblenden(box)
    n = len(box.log)
    box.laufe(11.0)
    assert box.modus == "pausiert" and not box.player.spielt
    pausen = box.befehle(ev.Pausieren, n)
    assert [p.grund for p in pausen] == ["gute_nacht"]
    speichern = box.befehle(ev.ZeigerSpeichern, n)
    assert speichern and speichern[-1].serie_id == SERIE
    z = box.resume_json()["serien"][SERIE]
    assert z["folge"] == "a.wav" and z["position_s"] > 60  # mitten in der Folge, nicht am Anfang
    assert stufe4.zeile(box).gute_nacht == "aus" and stufe4.zeile(box).figur_liegt
    # Regel 6.2.7: Beim Ende kein LautstaerkeSetzen zurück auf 40
    assert max(stufe4.prozente(box, n)) < START
    assert max(box.befehle(ev.ZeigerSpeichern, n), key=lambda b: b.position_s).position_s > 60


def test_nach_dem_ende_setzt_das_naechste_auflegen_die_lautstaerke_wieder_auf_den_wunsch(box):
    karte_nach_abheben(box)
    bis_ausblenden(box)
    box.laufe(11.0)
    box.hebe_ab("v3")
    n = len(box.log)
    box.auflege(UID, "v4")
    assert box.modus == "spielt"
    spiel = [b for b in box.log[n:] if isinstance(b, (ev.LautstaerkeSetzen, ev.Abspielen))]
    assert isinstance(spiel[0], ev.LautstaerkeSetzen) and spiel[0].prozent == START  # Regel 6: vor dem Abspielen
    assert isinstance(spiel[1], ev.Abspielen)


def test_anderer_tobie_waehrend_des_timers_der_timer_laeuft_fuer_den_neuen_weiter(box):
    karte_nach_abheben(box)
    box.laufe(20.0)
    box.auflege(UID_B, "v4")  # Wechsel auf eine andere Serie, der Timer bleibt
    assert box.modus == "spielt" and box.kern.session.serie_id == SERIE_B
    assert stufe4.zeile(box).gute_nacht == "laeuft"
    stufe4.gehe_bis(box, lambda: stufe4.zeile(box).gute_nacht == "ausblenden", schritt=0.1)
    box.laufe(11.0)
    assert box.modus == "pausiert" and box.resume_json()["serien"][SERIE_B]["position_s"] > 20


def test_abheben_waehrend_des_ausblendens_normale_pause_lautstaerke_zurueckgesetzt(box):
    karte_nach_abheben(box)
    bis_ausblenden(box)
    box.laufe(4.0)
    n = len(box.log)
    box.hebe_ab("v3")
    assert box.modus == "pausiert"
    assert stufe4.zeile(box).gute_nacht == "aus" and "gute_nacht" not in box.kern.grenzen
    assert box.befehle(ev.Pausieren, n)[0].grund == "abgehoben"
    assert box.befehle(ev.ZeigerSpeichern, n)
    # Resume setzt dort wieder an, mit der vollen Lautstärke
    box.auflege(UID, "v4")
    assert box.player.spielt
    assert stufe4.lautstaerken(box)[-1].prozent == START


def test_gute_nacht_karte_waehrend_des_ausblendens_wird_ignoriert(box):
    karte_nach_abheben(box)
    bis_ausblenden(box)
    box.laufe(2.0)
    box.hebe_ab("v3")  # Pause, Ausblenden ist damit abgebrochen
    box.auflege(UID_NACHT, "v4")
    assert stufe4.zeile(box).gute_nacht == "laeuft"  # neuer Timer, weil das Ausblenden schon beendet war


def test_zweite_karte_im_timer_startet_den_timer_neu(box):
    karte_nach_abheben(box)
    box.laufe(40.0)
    box.hebe_ab("v3")
    box.auflege(UID_NACHT, "v4")
    box.hebe_ab("v4")
    box.auflege(UID, "v5")
    box.laufe(40.0)  # 40 + 40 s: ohne Neustart wäre der Timer schon um
    assert stufe4.zeile(box).gute_nacht == "laeuft"
    box.laufe(25.0)
    assert stufe4.zeile(box).gute_nacht == "ausblenden"


def test_gute_nacht_ohne_wiedergabe_blendet_aus_und_pausiert_nichts_neues(box):
    """Karte liegt, nichts spielt: Der Timer läuft ab, nichts geht kaputt, die Box wird still."""
    box.auflege(UID_NACHT, "v1")
    n = len(box.log)
    box.laufe(75.0)
    assert stufe4.zeile(box).gute_nacht == "aus"
    assert box.befehle(ev.Abspielen, n) == []
    assert box.modus == "pausiert" or box.modus == "leer"
