"""CUJ 19: Tasten und Drehregler (AP 4.2 und 4.8).

Die echte ``Bedienung`` (Tasten, Drehregler, Hauptknopf kurz / lang) sendet in einen echten Kern mit simuliertem Player (``BedienBox``).
Vor / Zurück springen nach Track innerhalb der Folge (Entscheidung F, 05.11.); der Drehregler bleibt unter der wirksamen Grenze; der
Hauptknopf kurz ist Play / Pause, in `beendet` die nächste Folge (Entscheidung E); lang speichert den Zeiger und fährt herunter.
Startlautstärke 40, globale Grenze 60, Kopfhörer-Grenze 25.
"""

from __future__ import annotations

import pytest
from fixtures import audio, stufe4
from fixtures.stufe4 import BedienBox

from tobibox import events as ev
from tobibox.controls import LANG_S, RASTER_PROZENT

SERIE = "3f9a1c07b2d4"
UID_SERIE = "04a1b2c3"
UID_FOLGE = "04a1b2c5"  # Folge b.wav
UID_CD = "04a1b2c6"  # Folge „CD“ mit drei Tracks
CD = "CD"
TRACKS = [f"{CD}/01.wav", f"{CD}/02.wav", f"{CD}/03.wav"]


def aufbau(medien):
    ordner = audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav"], serie_id=SERIE, name="Rabe", dauer_s=30.0)
    audio.erzeuge_folge_ordner(ordner, CD, ["01.wav", "02.wav", "03.wav"], dauer_s=10.0)
    audio.schreibe_serie_json(ordner, SERIE, "Rabe", ["a.wav", "b.wav", CD])
    stufe4.ueberraschung(medien)


@pytest.fixture
def box(tmp_path):
    zu = {
        UID_SERIE: ev.Zuordnung("serie", SERIE),
        UID_FOLGE: ev.Zuordnung("folge", SERIE, "b.wav"),
        UID_CD: ev.Zuordnung("folge", SERIE, CD),
    }
    return BedienBox(tmp_path, zu, aufbau)


def abspielen(box, ab=0):
    return box.befehle(ev.Abspielen, ab)


def toene(box, ab=0):
    return [t.ton for t in box.befehle(ev.TonSpielen, ab)]


# --- Vor / Zurück ---------------------------------------------------------------------------------


def test_vor_springt_zum_naechsten_track_der_folge(box):
    box.auflege(UID_CD)
    box.laufe(4.0)
    n = len(box.log)
    box.bedienung.vor()
    (a,) = abspielen(box, n)
    assert (a.datei, a.track, a.position_s) == (CD, 1, 0.0) and box.modus == "spielt"
    assert box.resume_json()["folgen"][SERIE][CD]["track"] == 1


def test_zurueck_in_den_ersten_3_sekunden_springt_zum_vorigen_track(box):
    box.auflege(UID_CD)
    box.laufe(10.5)  # Track 1 (zweiter Track), 0,5 s
    assert box.kern.session.track == 1
    n = len(box.log)
    box.bedienung.zurueck()
    (a,) = abspielen(box, n)
    assert (a.track, a.position_s) == (0, 0.0)


def test_zurueck_nach_3_sekunden_startet_den_track_neu(box):
    box.auflege(UID_CD)
    box.laufe(10.0 + 5.0)
    n = len(box.log)
    box.bedienung.zurueck()
    (a,) = abspielen(box, n)
    assert (a.track, a.position_s) == (1, 0.0)


def test_zurueck_im_ersten_track_startet_ihn_neu(box):
    box.auflege(UID_CD)
    box.laufe(1.0)
    n = len(box.log)
    box.bedienung.zurueck()
    (a,) = abspielen(box, n)
    assert (a.track, a.position_s) == (0, 0.0)


def test_vor_beim_letzten_track_springt_bei_einer_serie_zur_naechsten_folge(box):
    box.auflege(UID_SERIE)
    box.laufe(3.0)
    n = len(box.log)
    box.bedienung.vor()  # a.wav hat einen Track: nächste Folge
    (a,) = abspielen(box, n)
    assert (a.datei, a.track, a.position_s) == ("b.wav", 0, 0.0)


def test_vor_beim_letzten_track_eines_folgen_tobies_nur_der_hinweiston(box):
    box.auflege(UID_FOLGE)
    box.laufe(3.0)
    n = len(box.log)
    box.bedienung.vor()
    assert abspielen(box, n) == [] and toene(box, n) == ["hinweis"]
    assert box.modus == "spielt" and box.player.spielt  # nichts ändert sich


def test_vor_und_zurueck_wirken_auch_in_der_pause(box):
    box.auflege(UID_CD)
    box.laufe(2.0)
    box.sende(ev.Hauptknopf("kurz"))
    assert box.modus == "pausiert"
    n = len(box.log)
    box.bedienung.vor()
    (a,) = abspielen(box, n)
    assert a.track == 1 and box.modus == "spielt"


# --- Drehregler -----------------------------------------------------------------------------------


def test_eine_raste_sind_zwei_prozentpunkte(box):
    box.auflege(UID_SERIE)
    box.bedienung.drehen(1)
    assert stufe4.wirksam(box) == 40 + RASTER_PROZENT
    box.bedienung.drehen(-3)
    assert stufe4.wirksam(box) == 40 + RASTER_PROZENT - 3 * RASTER_PROZENT


def test_drehregler_geht_nie_ueber_die_wirksame_grenze(box):
    box.auflege(UID_SERIE)
    for _ in range(30):
        box.bedienung.drehen(1)
    assert stufe4.wirksam(box) == 60  # globale Grenze
    n = len(box.log)
    box.bedienung.drehen(1)
    assert box.log[n:] == []  # kein Schritt über die Grenze, auch kein Ereignis
    assert all(b.prozent <= 60 for b in stufe4.lautstaerken(box))


def test_drehregler_geht_nie_unter_null(box):
    for _ in range(40):
        box.bedienung.drehen(-1)
    assert stufe4.wirksam(box) == 0 and box.kern.wunsch == 0


def test_drehregler_mit_kopfhoerer_unter_der_kopfhoerer_grenze(box):
    box.auflege(UID_SERIE)
    box.sende(ev.Kopfhoerer(True))
    assert stufe4.wirksam(box) == 25
    for _ in range(10):
        box.bedienung.drehen(1)
    assert stufe4.wirksam(box) == 25
    assert all(b.prozent <= b.grenze for b in stufe4.lautstaerken(box))


def test_drehregler_in_der_ausblendphase_wird_nicht_lauter(box):
    stufe4.setze_konfig(box, gute_nacht=ev.GuteNacht(1, 10))
    box.auflege(UID_SERIE)
    box.sende(ev.AktionAusgeloest("gute_nacht", "v9"))
    stufe4.gehe_bis(box, lambda: stufe4.zeile(box).gute_nacht == "ausblenden", max_s=70, schritt=0.1)
    box.laufe(3.0)
    vorher = stufe4.wirksam(box)
    for _ in range(5):
        box.bedienung.drehen(1)
    assert stufe4.wirksam(box) <= vorher


# --- Hauptknopf -----------------------------------------------------------------------------------


def test_hauptknopf_kurz_ist_play_pause(box):
    box.auflege(UID_SERIE)
    box.laufe(5.0)
    box.bedienung.haupt_runter(box.uhr.mono)
    box.bedienung.haupt_hoch(box.uhr.mono + 0.2)
    assert box.modus == "pausiert" and not box.player.spielt
    n = len(box.log)
    box.bedienung.haupt_runter(box.uhr.mono)
    box.bedienung.haupt_hoch(box.uhr.mono + 0.2)
    assert box.modus == "spielt" and abspielen(box, n)[0].position_s == pytest.approx(2.0, abs=0.2)  # 3 s Rücksprung


def test_entscheidung_q_hauptknopf_kurz_ohne_tobie_startet_nichts(box):
    """Entscheidung Q (10.11.): ohne aufliegenden Tobie nur der Hinweiston, auch nicht für Vor und Zurück."""
    box.auflege(UID_SERIE)
    box.laufe(5.0)
    box.hebe_ab()
    assert box.modus == "pausiert"
    for taste in ("haupt", "vor", "zurueck"):
        n = len(box.log)
        if taste == "haupt":
            box.bedienung.haupt_runter(0.0)
            box.bedienung.haupt_hoch(0.1)
        elif taste == "vor":
            box.bedienung.vor()
        else:
            box.bedienung.zurueck()
        assert box.modus == "pausiert" and abspielen(box, n) == [] and toene(box, n) == ["hinweis"], taste


def test_entscheidung_e_hauptknopf_nach_dem_ende_der_folge_spielt_die_naechste(box):
    box.auflege(UID_SERIE)
    box.laufe(31.0)
    assert box.modus == "beendet" and box.kern.session.figur is not None
    n = len(box.log)
    box.bedienung.haupt_runter(0.0)
    box.bedienung.haupt_hoch(0.1)
    (a,) = abspielen(box, n)
    assert (a.datei, a.track, a.position_s) == ("b.wav", 0, 0.0)
    assert stufe4.lautstaerken(box)[-1].prozent == 40  # Lautstärke wird vor dem Abspielen gesetzt


def test_entscheidung_e_folgen_tobie_spielt_dieselbe_folge_von_vorn(box):
    box.auflege(UID_FOLGE)
    box.laufe(31.0)
    assert box.modus == "beendet"
    n = len(box.log)
    box.bedienung.haupt_runter(0.0)
    box.bedienung.haupt_hoch(0.1)
    (a,) = abspielen(box, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0)


def test_hauptknopf_kurz_im_stumm_fenster_startet_nichts(box):
    stufe4.setze_konfig(box, fenster_liste=(stufe4.fenster("n", "stumm", "22:00", "07:00"),))
    box.uhr.setze_wall(stufe4.wall(2026, 11, 9, 23, 0))
    box.laufe(0.5)
    box.auflege(UID_SERIE)
    n = len(box.log)
    box.bedienung.haupt_runter(0.0)
    box.bedienung.haupt_hoch(0.1)
    box.bedienung.vor()
    assert abspielen(box, n) == [] and not box.player.spielt
    assert "hinweis" in toene(box, n)


def test_hauptknopf_lang_speichert_den_zeiger_und_faehrt_herunter(box):
    box.auflege(UID_SERIE)
    box.laufe(8.0)
    n = len(box.log)
    box.bedienung.haupt_runter(10.0)
    box.bedienung.tick(10.0 + LANG_S - 0.1)
    assert [b for b in box.log[n:] if isinstance(b, ev.Herunterfahren)] == []
    box.bedienung.tick(10.0 + LANG_S + 0.1)
    assert [b.grund for b in box.befehle(ev.Herunterfahren, n)] == ["hauptknopf"]
    assert box.befehle(ev.ZeigerSpeichern, n) and box.resume_json()["serien"][SERIE]["position_s"] > 0
    box.bedienung.haupt_hoch(10.0 + LANG_S + 0.3)  # Loslassen nach lang: kein kurzer Druck mehr
    assert [b.grund for b in box.befehle(ev.Herunterfahren)] == ["hauptknopf"]
    assert stufe4.zeile(box).strom == "herunterfahren"


def test_hauptknopf_lang_beim_loslassen_ohne_tick(box):
    box.auflege(UID_SERIE)
    box.bedienung.haupt_runter(0.0)
    box.bedienung.haupt_hoch(LANG_S + 0.2)
    assert [b.grund for b in box.befehle(ev.Herunterfahren)] == ["hauptknopf"]


def test_die_bedienung_folgt_dem_kern_nach_jedem_schritt(box):
    box.auflege(UID_SERIE)
    box.sende(ev.Kopfhoerer(True))
    assert box.bedienung.grenze == 25
    box.sende(ev.Kopfhoerer(False))
    assert box.bedienung.grenze == 60
