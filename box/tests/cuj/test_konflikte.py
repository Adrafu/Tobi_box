"""Konflikt-Tabelle aus „Kern-Zustände“ (Design) und Abnahme Stufe 4: jede Zeile als Test.

Echter Kern mit allen fünf Teilautomaten (``session``, ``learn``, ``quiet``, ``bedtime``, ``idle``), echte Bibliothek, echter Speicher,
simulierter Player und simulierte Uhr. Die Zeilen der Tabelle stehen als Überschriften über den Tests.

Zusätzlich die Reihenfolge für nicht vorhergesehene Fälle: Herunterfahren auf Anforderung vor stumm, vor Gute Nacht, vor Lernmodus,
vor Wiedergabe.
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import audio, stufe4

from tobibox import core
from tobibox import events as ev
from tobibox.volume import wirksame_grenze

SERIE = "3f9a1c07b2d4"
SERIE_B = "5b6c7d8e9f01"
SERIE_C = "6c7d8e9f0a12"
UID = "04a1b2c3"  # Serie Rabe (Folgen zu 20 s)
UID_B = "04a1b2c4"  # Serie Bär (Folge zu 200 s)
UID_C = "04a1b2c9"  # Serie Fuchs (Folge zu 200 s)
UID_FOLGE = "04a1b2c5"  # Folge b.wav der Serie Rabe
UID_NACHT = "04c0ffee"
UID_NEU = "04ffeedd"  # unbekannt
START = 40
FREI = "frei"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    stufe4.serie(medien, "baer", ["x.wav"], SERIE_B, "Bär", 200.0)
    stufe4.serie(medien, "fuchs", ["y.wav"], SERIE_C, "Fuchs", 200.0)
    stufe4.ueberraschung(medien)


@pytest.fixture
def box(tmp_path):
    zu = {
        UID: ev.Zuordnung("serie", SERIE),
        UID_B: ev.Zuordnung("serie", SERIE_B),
        UID_C: ev.Zuordnung("serie", SERIE_C),
        UID_FOLGE: ev.Zuordnung("folge", SERIE, "b.wav"),
        UID_NACHT: ev.Zuordnung("aktion", aktion="gute_nacht"),
    }
    b = CujBox(tmp_path, zu, aufbau)
    stufe4.setze_konfig(b, gute_nacht=ev.GuteNacht(1, 10))
    return b


def fenster_stumm():
    return (stufe4.fenster("nacht", "stumm", "22:00", "07:00"),)


def stumm_machen(box, h=23, m=0):
    box.uhr.setze_wall(stufe4.wall(2026, 11, 9, h, m))  # erst die Uhr, dann die Konfiguration
    stufe4.setze_konfig(box, gute_nacht=ev.GuteNacht(1, 10), fenster_liste=fenster_stumm(), revision=3)
    box.laufe(0.5)


def tag_vor_stumm(box):
    box.uhr.setze_wall(stufe4.wall(2026, 11, 9, 21, 59, 55))
    stufe4.setze_konfig(box, gute_nacht=ev.GuteNacht(1, 10), fenster_liste=fenster_stumm(), revision=3)
    box.laufe(0.5)


def zeiger(box, art="serien"):
    return box.resume_json()[art][SERIE]


# --- Folge zu Ende, Tobie liegt noch --------------------------------------------------------------


def test_folge_zu_ende_serie_zeiger_auf_naechste_folge_pause_beendet(box):
    box.auflege(UID)
    box.laufe(21.0)
    assert box.modus == "beendet" and box.kern.session.figur is not None and not box.player.spielt
    z = zeiger(box)
    assert (z["folge"], z["track"], z["position_s"]) == ("b.wav", 0, 0.0)
    assert [p.grund for p in box.befehle(ev.Pausieren)][-1] == "folgenende"
    n = len(box.log)
    box.laufe(30.0)  # es passiert nichts, bis abgehoben oder der Hauptknopf gedrückt wird
    assert box.log[n:] == [] or all(isinstance(b, (ev.Protokoll, ev.ZustandMelden)) for b in box.log[n:])
    assert box.modus == "beendet"


def test_folge_zu_ende_nach_der_letzten_folge_zeiger_auf_folge_1(box):
    box.auflege(UID)
    box.laufe(21.0)  # a.wav zu Ende
    box.sende(ev.Hauptknopf("kurz"))
    box.laufe(21.0)  # b.wav zu Ende
    assert zeiger(box)["folge"] == "c.wav"
    box.sende(ev.Hauptknopf("kurz"))
    box.laufe(21.0)  # c.wav zu Ende, auch die letzte Folge
    assert box.modus == "beendet" and zeiger(box)["folge"] == "a.wav"  # nach c.wav wieder Folge 1


def test_folge_zu_ende_folgen_tobie_zeiger_dieser_folge_auf_anfang(box):
    box.auflege(UID_FOLGE)
    box.laufe(21.0)
    assert box.modus == "beendet"
    z = zeiger(box, "folgen")["b.wav"]
    assert (z["track"], z["position_s"]) == (0, 0.0)


def test_nach_dem_letzten_track_nicht_nach_jedem_track(tmp_path):
    def mit_tracks(medien):
        ordner = audio.erzeuge_serie(medien, "rabe", ["a.wav"], serie_id=SERIE, name="Rabe", dauer_s=6.0)
        audio.erzeuge_folge_ordner(ordner, "CD", ["01.wav", "02.wav"], dauer_s=6.0)
        audio.schreibe_serie_json(ordner, SERIE, "Rabe", ["a.wav", "CD"])
        stufe4.ueberraschung(medien)

    b = CujBox(tmp_path, {UID_FOLGE: ev.Zuordnung("folge", SERIE, "CD")}, mit_tracks)
    b.auflege(UID_FOLGE)
    b.laufe(7.0)  # Track 1 zu Ende: weiter mit Track 2, keine Pause
    assert b.modus == "spielt" and b.kern.session.track == 1
    b.laufe(6.0)
    assert b.modus == "beendet"


# --- Hauptknopf kurz bei beendeter Folge -----------------------------------------------------------


def test_hauptknopf_kurz_bei_beendeter_folge_mit_liegendem_tobie_spielt_die_naechste(box):
    box.auflege(UID)
    box.laufe(21.0)
    n = len(box.log)
    box.sende(ev.Hauptknopf("kurz"))
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.track, a.position_s) == ("b.wav", 0, 0.0) and box.modus == "spielt"


def test_hauptknopf_kurz_bei_beendeter_folge_folgen_tobie_dieselbe_folge_von_vorn(box):
    box.auflege(UID_FOLGE)
    box.laufe(21.0)
    n = len(box.log)
    box.sende(ev.Hauptknopf("kurz"))
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0)


def test_hauptknopf_kurz_ohne_tobie_hat_die_normale_funktion_play_pause(box):
    box.auflege(UID)
    box.laufe(10.0)
    box.hebe_ab()
    n = len(box.log)
    box.sende(ev.Hauptknopf("kurz"))  # Play am Zeiger
    assert box.modus == "spielt" and box.befehle(ev.Abspielen, n)[0].datei == "a.wav"
    box.sende(ev.Hauptknopf("kurz"))  # Pause
    assert box.modus == "pausiert" and [p.grund for p in box.befehle(ev.Pausieren, n)] == ["knopf"]


# --- Zurück und Vor ------------------------------------------------------------------------------


def test_zurueck_bei_beendeter_folge_spielt_die_eben_beendete_von_vorn_serie_und_folge(box):
    box.auflege(UID)
    box.laufe(21.0)
    n = len(box.log)
    box.sende(ev.Zurueck())
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.track, a.position_s) == ("a.wav", 0, 0.0)  # a.wav war die eben beendete Folge
    box.neustart()
    box.auflege(UID_FOLGE)
    box.laufe(21.0)
    n = len(box.log)
    box.sende(ev.Zurueck())
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.datei, a.position_s) == ("b.wav", 0.0)


def test_vor_beim_letzten_track_serie_naechste_folge_folgen_tobie_hinweiston(box):
    box.auflege(UID)
    box.laufe(3.0)
    n = len(box.log)
    box.sende(ev.Weiter())
    assert box.befehle(ev.Abspielen, n)[0].datei == "b.wav"  # Serie: erster Track der nächsten Folge
    box.hebe_ab()
    box.auflege(UID_FOLGE, "v2")
    box.laufe(3.0)
    n = len(box.log)
    box.sende(ev.Weiter())
    assert box.befehle(ev.Abspielen, n) == [] and [t.ton for t in box.befehle(ev.TonSpielen, n)] == ["hinweis"]


# --- Stumm gegen Lernmodus -----------------------------------------------------------------------


def test_stumm_gegen_lernmodus_die_box_lernt_bestaetigt_leise_und_spielt_nicht(box):
    stumm_machen(box)
    n = len(box.log)
    box.sende(ev.HaLernmodus("b1", box.uhr.wall + 120))
    assert box.kern.teil["learn"].modus == "lernt"
    # der Beginnton und der Endton sind unter „stumm“ derselbe leise Hinweis (Regel 6.2.2 und 6.2.3)
    toene = [t.ton for t in box.befehle(ev.TonSpielen, n)]
    assert toene and set(toene) == {"hinweis"} and len(toene) == 1
    n = len(box.log)
    box.auflege(UID_NEU, "v1")  # ein Tobie im Lernmodus: gemeldet, nichts gespielt
    assert box.kern.teil["learn"].modus == "aus"
    assert [m.art for m in box.befehle(ev.Melden, n)] == ["gelernt"]
    assert box.befehle(ev.Abspielen, n) == [] and not box.player.spielt
    assert {t.ton for t in box.befehle(ev.TonSpielen, n)} <= {"hinweis"}


# --- Stumm beginnt / endet -------------------------------------------------------------------------


def test_stumm_beginnt_waehrend_ein_tobie_spielt_ausblenden_pause_zeiger_gespeichert(box):
    box.auflege(UID)
    tag_vor_stumm(box)
    box.laufe(10.0)
    assert box.modus == "gehalten" and not box.player.spielt
    assert zeiger(box)["position_s"] > 5
    assert [p.grund for p in box.befehle(ev.Pausieren)][-1] == "stumm"


def test_stumm_endet_waehrend_ein_tobie_liegt_nichts_startet_erst_abheben_und_auflegen(box):
    stumm_machen(box)
    box.auflege(UID)
    assert box.modus == "gehalten"
    n = len(box.log)
    box.uhr.setze_wall(stufe4.wall(2026, 11, 10, 7, 0, 1))
    box.laufe(2.0)
    assert stufe4.zeile(box).ruhe == "normal" and box.modus == "pausiert"
    assert box.befehle(ev.Abspielen, n) == [] and not box.player.spielt
    box.hebe_ab()
    box.auflege(UID, "v2")
    assert box.modus == "spielt" and box.player.spielt


# --- Gute Nacht ---------------------------------------------------------------------------------


def gute_nacht_laeuft(box):
    """Der Bär spielt, Karte nach dem Abheben, Bär wieder auf; die Folge ist mit 200 s lang genug."""
    box.auflege(UID_B, "v1")
    box.laufe(5.0)
    box.hebe_ab("v1")
    box.auflege(UID_NACHT, "v2")
    box.hebe_ab("v2")
    box.auflege(UID_B, "v3")
    assert stufe4.zeile(box).gute_nacht == "laeuft"


def test_gute_nacht_laeuft_ein_anderer_tobie_wird_aufgelegt_timer_laeuft_fuer_den_neuen_weiter(box):
    gute_nacht_laeuft(box)
    box.laufe(30.0)
    box.auflege(UID_C, "v4")
    assert box.kern.session.serie_id == SERIE_C and stufe4.zeile(box).gute_nacht == "laeuft"
    stufe4.gehe_bis(box, lambda: stufe4.zeile(box).gute_nacht == "ausblenden", max_s=60, schritt=0.1)
    box.laufe(11.0)
    assert box.modus == "pausiert" and box.resume_json()["serien"][SERIE_C]["position_s"] > 20
    assert box.resume_json()["serien"][SERIE_B]["position_s"] < 40  # der Bär blieb, wo er war


def test_tobie_wird_beim_ausblenden_abgehoben_pause_zeiger_lautstaerke_zurueck_resume(box):
    gute_nacht_laeuft(box)
    stufe4.gehe_bis(box, lambda: stufe4.zeile(box).gute_nacht == "ausblenden", max_s=80, schritt=0.1)
    box.laufe(5.0)
    assert stufe4.wirksam(box) < START
    n = len(box.log)
    box.hebe_ab("v3")
    assert box.modus == "pausiert" and stufe4.zeile(box).gute_nacht == "aus"
    assert "gute_nacht" not in box.kern.grenzen and stufe4.wirksam(box) == START  # Lautstärke zurückgesetzt
    assert [p.grund for p in box.befehle(ev.Pausieren, n)] == ["abgehoben"] and box.befehle(ev.ZeigerSpeichern, n)
    n = len(box.log)
    box.auflege(UID_B, "v4")  # Resume setzt dort wieder an
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == SERIE_B and a.position_s > 0
    assert stufe4.lautstaerken(box)[-1].prozent == START


# --- Tobie-Wechsel bei Leser-Unterbrechung -------------------------------------------------------------


def test_tobie_wechsel_bei_leser_unterbrechung_frist_endet_alter_zeiger_neue_serie_startet(box):
    box.leser.hello()
    box.leser.placed(UID)
    box.leser.hb(True)
    box.laufe(6.0)
    box.sende(ev.LeserAlarm("kein_herzschlag"))
    assert box.modus == "unbekannt"
    box.laufe(1.0)
    box.leser.hello()
    n = len(box.log)
    box.leser.placed(UID_B)  # HELLO und PLACED mit anderer Kennung
    assert box.kern.session.serie_id == SERIE_B and box.modus == "spielt"
    assert zeiger(box)["position_s"] > 3  # Zeiger der alten Serie gespeichert
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == SERIE_B
    assert box.kern.session.figur.uid == UID_B


# --- Leerlauf gegen Lernmodus, Sync und Update ---------------------------------------------------------


def test_leerlauf_abschaltung_trifft_lernmodus_sync_oder_update_die_box_schaltet_nie_ab(box):
    box.sende(ev.Takt(), dt=19 * 60)
    box.sende(ev.HaLernmodus("b1", box.uhr.wall + 600))
    box.sende(ev.Takt(), dt=119)  # 20 min um, Lernmodus läuft noch (Frist 2 min)
    assert box.befehle(ev.Herunterfahren) == []
    box.sende(ev.SyncGestartet())
    box.sende(ev.Takt(), dt=60 * 60)
    assert box.befehle(ev.Herunterfahren) == []
    box.sende(ev.SyncFertig(0, 0))
    box.sende(ev.UpdateGestartet("1.2.0"))
    box.sende(ev.Takt(), dt=60 * 60)
    assert box.befehle(ev.Herunterfahren) == []
    box.sende(ev.SelbsttestErgebnis(True))
    assert [b.grund for b in box.befehle(ev.Herunterfahren)] == ["leerlauf"]


# --- Tiefstand während Sync ----------------------------------------------------------------------------


def test_tiefstand_waehrend_sync_sync_bricht_ab_zeiger_gespeichert_box_faehrt_herunter(box):
    box.auflege(UID)
    box.laufe(8.0)
    box.sende(ev.SyncGestartet())
    n = len(box.log)
    box.sende(ev.AkkuTiefstand())
    assert [b.grund for b in box.befehle(ev.SyncAbbrechen, n)] == ["akku_tiefstand"]
    assert box.befehle(ev.ZeigerSpeichern, n) and zeiger(box)["position_s"] > 4
    assert [b.grund for b in box.befehle(ev.Herunterfahren, n)] == ["akku_tiefstand"]


# --- Mehrere Lautstärke-Grenzen ----------------------------------------------------------------------------


def test_mehrere_grenzen_gleichzeitig_kopfhoerer_leiser_und_ausblenden_es_gilt_das_minimum(box):
    stufe4.setze_konfig(
        box, gute_nacht=ev.GuteNacht(1, 10), revision=3,
        fenster_liste=(stufe4.fenster("f", "leiser", "00:00", "23:59", 35),),
    )
    box.uhr.setze_wall(stufe4.wall(2026, 11, 9, 12, 0))
    box.laufe(0.5)
    gute_nacht_laeuft(box)
    box.laufe(4.0)
    assert box.kern.grenzen["leise_zeit"] == 35 and stufe4.wirksam(box) == 35  # Grenzen: global 60, leiser 35
    box.sende(ev.Kopfhoerer(True))
    assert box.kern.grenzen["kopfhoerer"] == 25 and stufe4.wirksam(box) == 25
    stufe4.gehe_bis(box, lambda: stufe4.zeile(box).gute_nacht == "ausblenden", max_s=80, schritt=0.1)
    box.laufe(4.0)
    g = box.kern.grenzen
    assert "gute_nacht" in g and g["gute_nacht"] < 25
    assert wirksame_grenze(g) == min(g.values()) == g["gute_nacht"]
    assert stufe4.wirksam(box) <= g["gute_nacht"]
    for b in stufe4.lautstaerken(box):
        assert b.prozent <= b.grenze
    box.sende(ev.Kopfhoerer(False))  # Kopfhörer weg: das Minimum aus den übrigen Grenzen
    g = box.kern.grenzen
    assert "kopfhoerer" not in g and wirksame_grenze(g) == min(g.values())


# --- Reihenfolge für nicht vorhergesehene Fälle -------------------------------------------------------------


def test_herunterfahren_hat_vorrang_vor_gute_nacht_stumm_lernmodus_und_wiedergabe(box):
    stumm_machen(box)
    box.sende(ev.HaLernmodus("b1", box.uhr.wall + 600))
    n = len(box.log)
    box.sende(ev.Hauptknopf("lang"))
    assert [b.grund for b in box.befehle(ev.Herunterfahren, n)] == ["hauptknopf"]
    assert box.befehle(ev.Abspielen, n) == []


def test_herunterfahren_entfernt_ein_abspielen_derselben_verarbeitung(box):
    """Konfliktregel 1: Enthält die Ausgabe ``Herunterfahren``, bleibt kein ``Abspielen``, ``SyncStarten`` oder ``AusgangWaehlen``."""
    aus = core._konflikte(
        [ev.Abspielen(SERIE, "rabe", "a.wav", ("a.wav",), 0, 0.0), ev.SyncStarten("ha"), ev.AusgangWaehlen("kopfhoerer"),
         ev.Herunterfahren("hauptknopf")],
        "normal",
    )
    assert aus == [ev.Herunterfahren("hauptknopf")]


def test_die_fuenf_teilautomaten_stehen_in_der_festen_reihenfolge():
    assert [n for n, _ in core.TEILAUTOMATEN] == ["session", "learn", "quiet", "bedtime", "idle"]
    assert set(core.neuer_zustand().teil) == {"session", "learn", "quiet", "bedtime", "idle"}


def test_lautstaerke_geaendert_erreicht_quiet_und_bedtime(box):
    """Ohne die Meldung der wirksamen Lautstärke startete jede Rampe bei 100."""
    box.auflege(UID)
    assert box.kern.teil["quiet"].wirksam == START and box.kern.teil["bedtime"].wirksam == START
    box.sende(ev.LautstaerkeDrehen(-10))
    assert box.kern.teil["quiet"].wirksam == START - 10 and box.kern.teil["bedtime"].wirksam == START - 10
