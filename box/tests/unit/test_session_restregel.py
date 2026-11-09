"""Entscheidung I (09.11.): Ein kleiner Rest gilt als fertig gehört.

Beim Fortsetzen an einem gespeicherten Zeiger (Auflegen, Hauptknopf in ``pausiert``, Dienst-Neustart,
Einschalten) gilt die Folge als fertig, wenn bis zum Ende der **ganzen Folge** (alle Tracks) weniger als
``REST_FERTIG_S`` fehlen. Folgen unter ``REST_REGEL_MIN_FOLGE_S`` und Folgen mit unbekannter Dauer sind ausgenommen.
"""

from __future__ import annotations

import pytest
from conftest import UID_CD, UID_FOLGE, UID_S1, UID_S3, UID_UNBEKANNT, UEB, SitzungsHarnisch, ppos, zeiger

from tobibox import events as ev
from tobibox import session

# s1: a 123,6 s (der Fall aus dem Test am Mac), b 100 s, c nur 30 s (unter 60 s)
S1D = ev.Serie(
    "s1", "Serie 1", "normal", "s1", ("a.mp3", "b.mp3", "c.mp3"),
    dauern={"a.mp3": (123.6,), "b.mp3": (100.0,), "c.mp3": (30.0,)},
)
# s3: Folge „cd“ mit drei Tracks zu je 50 s (zusammen 150 s), z.mp3 ohne bekannte Dauer
S3D = ev.Serie(
    "s3", "Serie 3", "normal", "s3", ("cd", "z.mp3"),
    {"cd": ("cd/01.mp3", "cd/02.mp3", "cd/03.mp3"), "z.mp3": ("z.mp3",)},
    {"cd": (50.0, 50.0, 50.0)},
)
# Serie mit drei gleich langen Folgen (für Mitte und Ende)
S4D = ev.Serie(
    "s4", "Serie 4", "normal", "s4", ("1.mp3", "2.mp3", "3.mp3"),
    dauern={"1.mp3": (100.0,), "2.mp3": (100.0,), "3.mp3": (100.0,)},
)
UEBD = ev.Serie(
    "ueb", "Überraschung", "ueberraschung", "ueb", ("u1.mp3", "u2.mp3"),
    dauern={"u1.mp3": (90.0,), "u2.mp3": (90.0,)},
)
UID_S4 = "04a1b2d0"


def konfig():
    from conftest import ZUORDNUNGEN, mk_konfig

    return mk_konfig({**ZUORDNUNGEN, UID_S4: ev.Zuordnung("serie", "s4")})


def harnisch(zeiger_liste, **kw) -> SitzungsHarnisch:
    h = SitzungsHarnisch(serien=(S1D, S3D, S4D, UEBD), konfig=False, zeiger=zeiger_liste, **kw)
    h.sende(ev.KonfigGeladen(konfig()))
    return h


def auflegen(h, uid=UID_S1, v="v2"):
    return h.sende(ev.Aufgelegt(uid, "ntag", False, 5, v))


def start(befehle) -> ev.Abspielen:
    (a,) = [b for b in befehle if isinstance(b, ev.Abspielen)]
    return a


def regel_zeilen(h) -> list[ev.Protokoll]:
    return [o for o in h.alle if isinstance(o, ev.Protokoll) and o.ereignis == "rest_regel"]


# --- Rest unter, an und über der Grenze -------------------------------------------------------------


def test_der_fall_vom_mac_122_von_123_6_spielt_die_naechste_folge_von_vorn():
    h = harnisch([zeiger("s1", "a.mp3", 0, 122.0, 3)])
    a = start(auflegen(h))
    assert (a.datei, a.track, a.position_s) == ("b.mp3", 0, 0.0)
    (z,) = regel_zeilen(h)
    assert z.ergebnis == "naechste_folge" and z.ebene == "INFO"
    assert z.daten["rest_s"] == 1.6 and z.daten["folge"] == "a.mp3" and z.daten["naechste"] == "b.mp3"
    assert z.daten["serie"] == "s1" and z.daten["uid"] == UID_S1
    assert h.modus == "spielt" and h.z.datei == "b.mp3" and h.z.index == 1


@pytest.mark.parametrize(
    "pos, gilt",
    [
        (50.0, False),  # Rest 70 s
        (104.9, False),  # Rest 15,1 s
        (105.0, False),  # Rest genau 15 s: noch nicht fertig (weniger als 15 s)
        (105.1, True),  # Rest 14,9 s
        (119.9, True),
        (120.0, True),  # Rest 0
    ],
)
def test_grenze_bei_15_sekunden(pos, gilt):
    s = ev.Serie("s5", "S5", "normal", "s5", ("a.mp3", "b.mp3"), dauern={"a.mp3": (120.0,), "b.mp3": (120.0,)})
    from conftest import ZUORDNUNGEN, mk_konfig

    h = SitzungsHarnisch(serien=(s, UEB), konfig=False, zeiger=[zeiger("s5", "a.mp3", 0, pos, 1)])
    h.sende(ev.KonfigGeladen(mk_konfig({**ZUORDNUNGEN, "04a1b2d5": ev.Zuordnung("serie", "s5")})))
    a = start(auflegen(h, "04a1b2d5"))
    if gilt:
        assert (a.datei, a.position_s) == ("b.mp3", 0.0)
        assert len(regel_zeilen(h)) == 1
    else:
        assert (a.datei, a.position_s) == ("a.mp3", pos - 3.0)
        assert regel_zeilen(h) == []


def test_gemessen_wird_vor_dem_ruecksprung():
    # Der Rest zählt am gespeicherten Zeiger. Der Rücksprung von 3 s darf die Regel weder auslösen noch verhindern.
    h = harnisch([zeiger("s1", "b.mp3", 1, 85.0, 1)])  # Rest 15,0 s, nach Rücksprung Rest 18 s
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("b.mp3", 82.0)
    h = harnisch([zeiger("s1", "b.mp3", 1, 85.1, 1)])  # Rest 14,9 s: greift am Zeiger, nicht an 82,1
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("c.mp3", 0.0)


def test_regel_aendert_das_speichern_nicht():
    h = harnisch([zeiger("s1", "a.mp3", 0, 122.0, 3)])
    out = auflegen(h)
    assert not [b for b in out if isinstance(b, ev.ZeigerSpeichern)]  # beim Start wird nichts gespeichert
    assert h.z.zeiger[("serie", "s1", "")].position_s == 122.0  # der gespeicherte Zeiger bleibt bis zum nächsten Speichern


# --- Ausnahmen --------------------------------------------------------------------------------------


def test_folge_unter_60_sekunden_ist_ausgenommen():
    h = harnisch([zeiger("s1", "c.mp3", 2, 29.0, 1)])  # c: 30 s, Rest 1 s
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("c.mp3", 26.0)
    assert regel_zeilen(h) == []


def test_folge_von_genau_60_sekunden_zaehlt_mit():
    s = ev.Serie("s6", "S6", "normal", "s6", ("a.mp3", "b.mp3"), dauern={"a.mp3": (60.0,), "b.mp3": (60.0,)})
    from conftest import ZUORDNUNGEN, mk_konfig

    h = SitzungsHarnisch(serien=(s, UEB), konfig=False, zeiger=[zeiger("s6", "a.mp3", 0, 55.0, 1)])
    h.sende(ev.KonfigGeladen(mk_konfig({**ZUORDNUNGEN, "04a1b2d6": ev.Zuordnung("serie", "s6")})))
    assert start(auflegen(h, "04a1b2d6")).datei == "b.mp3"


def test_unbekannte_dauer_ist_ausgenommen_und_kommt_ins_protokoll():
    h = harnisch([zeiger("s3", "z.mp3", 1, 500.0, 1)])
    a = start(auflegen(h, UID_S3))
    assert (a.datei, a.position_s) == ("z.mp3", 497.0)
    (z,) = regel_zeilen(h)
    assert z.ergebnis == "dauer_unbekannt" and z.ebene == "INFO" and z.daten["folge"] == "z.mp3"


@pytest.mark.parametrize("pos, gilt", [(125.5, True), (125.6, True), (125.7, False), (300.0, False)])
def test_position_hinter_der_trackdauer_wendet_die_regel_nicht_an(pos, gilt):
    """B9: Ist die Dauer falsch (zum Beispiel zu klein geschätzt), liegt die Position hinter dem Ende des Tracks.
    Mehr als 2 s darüber: wie „Dauer unbekannt“, die Folge wird nicht übersprungen."""
    h = harnisch([zeiger("s1", "a.mp3", 0, pos, 3)])  # a.mp3: 123,6 s
    a = start(auflegen(h))
    (z,) = regel_zeilen(h)
    if gilt:
        assert (a.datei, a.position_s) == ("b.mp3", 0.0) and z.ergebnis == "naechste_folge"
    else:
        assert (a.datei, a.position_s) == ("a.mp3", pos - 3.0)
        assert z.ergebnis == "dauer_unbekannt" and z.daten["grund"] == "position_hinter_dauer"


def test_position_hinter_dem_track_im_mehrtrack_zeiger_wird_je_track_gemessen():
    # Folge „cd“: 3 Tracks zu 50 s. Track 1 bei 52,5 s (2,5 s über seiner Dauer): keine Regel, auch wenn der Rest klein wäre
    h = harnisch([zeiger("s3", "cd", 0, 52.5, 1, track=1)])
    a = start(auflegen(h, UID_S3))
    assert (a.datei, a.track) == ("cd", 1)
    assert regel_zeilen(h)[0].ergebnis == "dauer_unbekannt"


def test_ein_track_mit_unbekannter_dauer_macht_die_ganze_folge_unbekannt():
    s = ev.Serie("s7", "S7", "normal", "s7", ("a.mp3",), {"a.mp3": ("a/1.mp3", "a/2.mp3")}, {"a.mp3": (100.0, None)})
    from conftest import ZUORDNUNGEN, mk_konfig

    h = SitzungsHarnisch(serien=(s, UEB), konfig=False, zeiger=[zeiger("s7", "a.mp3", 0, 40.0, 1, track=1)])
    h.sende(ev.KonfigGeladen(mk_konfig({**ZUORDNUNGEN, "04a1b2d7": ev.Zuordnung("serie", "s7")})))
    a = start(auflegen(h, "04a1b2d7"))
    assert (a.track, a.position_s) == (1, 37.0)
    assert regel_zeilen(h)[0].ergebnis == "dauer_unbekannt"


def test_ohne_zeiger_keine_regel_und_kein_protokoll():
    h = harnisch([])
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("a.mp3", 0.0)
    assert regel_zeilen(h) == []


def test_lange_folge_mit_rest_ueber_15_s_wird_normal_fortgesetzt():
    h = harnisch([zeiger("s1", "a.mp3", 0, 100.0, 1)])  # Rest 23,6 s
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("a.mp3", 97.0)
    assert regel_zeilen(h) == []


# --- Mehrere Tracks: Rest über alle Tracks ----------------------------------------------------------


@pytest.mark.parametrize(
    "track, pos, gilt",
    [
        (2, 40.0, True),  # Rest 10 s im letzten Track
        (2, 35.0, False),  # Rest genau 15 s
        (2, 30.0, False),  # Rest 20 s
        (0, 49.0, False),  # Track 0 fast zu Ende, aber 101 s fehlen noch: keine Folge-Ende-Regel pro Track
        (1, 49.9, False),
        (2, 49.0, True),
    ],
)
def test_mehrere_tracks_rest_ueber_alle_tracks(track, pos, gilt):
    h = harnisch([zeiger("s3", "cd", 0, pos, 1, track=track)])
    a = start(auflegen(h, UID_S3))
    if gilt:
        assert (a.datei, a.track, a.position_s) == ("z.mp3", 0, 0.0)
    else:
        assert (a.datei, a.track) == ("cd", track)
        assert a.position_s == max(0.0, pos - 3.0)


def test_folgen_tobie_mit_mehreren_tracks_beginnt_von_vorn_bei_track_0():
    h = harnisch([zeiger("s3", "cd", None, 45.0, 1, track=2, art="folge")])
    a = start(auflegen(h, UID_CD))
    assert (a.datei, a.track, a.position_s) == ("cd", 0, 0.0)
    assert a.tracks == ("cd/01.mp3", "cd/02.mp3", "cd/03.mp3")
    assert regel_zeilen(h)[0].ergebnis == "von_vorn"


# --- Serie: Mitte, Ende --------------------------------------------------------------------------


def test_serie_in_der_mitte_spielt_die_naechste_folge():
    h = harnisch([zeiger("s4", "1.mp3", 0, 95.0, 1)])
    a = start(auflegen(h, UID_S4))
    assert (a.datei, a.track, a.position_s) == ("2.mp3", 0, 0.0)
    assert h.z.index == 1


def test_serie_am_ende_wechselt_auf_folge_1():
    h = harnisch([zeiger("s4", "3.mp3", 2, 99.0, 1)])
    a = start(auflegen(h, UID_S4))
    assert (a.datei, a.track, a.position_s) == ("1.mp3", 0, 0.0)
    assert h.z.index == 0
    assert regel_zeilen(h)[0].daten["naechste"] == "1.mp3"


def test_serie_mit_einer_folge_beginnt_dieselbe_folge_von_vorn():
    s = ev.Serie("s8", "S8", "normal", "s8", ("a.mp3",), dauern={"a.mp3": (100.0,)})
    from conftest import ZUORDNUNGEN, mk_konfig

    h = SitzungsHarnisch(serien=(s, UEB), konfig=False, zeiger=[zeiger("s8", "a.mp3", 0, 98.0, 1)])
    h.sende(ev.KonfigGeladen(mk_konfig({**ZUORDNUNGEN, "04a1b2d8": ev.Zuordnung("serie", "s8")})))
    a = start(auflegen(h, "04a1b2d8"))
    assert (a.datei, a.position_s) == ("a.mp3", 0.0)


def test_die_naechste_folge_wird_nicht_noch_einmal_geprueft():
    # Folge 2 ist 100 s lang und startet von vorn: kein zweiter Sprung
    h = harnisch([zeiger("s4", "1.mp3", 0, 99.0, 1), zeiger("s4", "2.mp3", None, 99.0, 1, art="folge")])
    a = start(auflegen(h, UID_S4))
    assert a.datei == "2.mp3" and a.position_s == 0.0
    assert len(regel_zeilen(h)) == 1


# --- Folgen-Tobie -----------------------------------------------------------------------------------


def test_folgen_tobie_beginnt_von_vorn():
    h = harnisch([zeiger("s1", "b.mp3", None, 90.0, 1, art="folge")])  # b: 100 s, Rest 10 s
    a = start(auflegen(h, UID_FOLGE))
    assert (a.datei, a.track, a.position_s) == ("b.mp3", 0, 0.0)
    (z,) = regel_zeilen(h)
    assert z.ergebnis == "von_vorn" and z.daten["rest_s"] == 10.0 and z.daten["art"] == "folge"
    assert h.z.ziel == "folge" and h.z.datei == "b.mp3"


def test_folgen_tobie_mit_grossem_rest_setzt_fort():
    h = harnisch([zeiger("s1", "b.mp3", None, 50.0, 1, art="folge")])
    a = start(auflegen(h, UID_FOLGE))
    assert a.position_s == 47.0


def test_folgen_tobie_nutzt_den_folgen_zeiger_nicht_den_serien_zeiger():
    # Serien-Zeiger steht kurz vor dem Ende von a, der Folgen-Zeiger von b mitten drin
    h = harnisch([zeiger("s1", "a.mp3", 0, 122.0, 1), zeiger("s1", "b.mp3", None, 50.0, 1, art="folge")])
    a = start(auflegen(h, UID_FOLGE))
    assert (a.datei, a.position_s) == ("b.mp3", 47.0)


# --- Hauptknopf, Dienst-Neustart, Einschalten ----------------------------------------------------------


def test_hauptknopf_nach_pause_gilt_die_regel_am_gespeicherten_zeiger():
    h = harnisch([])
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 118.0))
    h.sende(ev.Hauptknopf("kurz"))  # Pause, Zeiger 118,0 gespeichert
    assert h.modus == "pausiert"
    out = h.sende(ev.Hauptknopf("kurz"))
    a = start(out)
    assert (a.datei, a.track, a.position_s) == ("b.mp3", 0, 0.0)
    assert regel_zeilen(h)[0].daten["rest_s"] == 5.6
    assert h.modus == "spielt"


def test_hauptknopf_nach_pause_mitten_in_der_folge_setzt_fort():
    h = harnisch([])
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 60.0))
    h.sende(ev.Hauptknopf("kurz"))
    a = start(h.sende(ev.Hauptknopf("kurz")))
    assert (a.datei, a.position_s) == ("a.mp3", 57.0)
    assert regel_zeilen(h) == []


def test_dienst_neustart_bleibt_pausiert_und_erst_der_hauptknopf_wendet_die_regel_an():
    h = harnisch([zeiger("s1", "a.mp3", 0, 122.0, 3)], neustart_uid=UID_S1)
    out = auflegen(h)
    assert h.modus == "pausiert" and not [b for b in out if isinstance(b, ev.Abspielen)]
    assert regel_zeilen(h) == []
    a = start(h.sende(ev.Hauptknopf("kurz")))
    assert (a.datei, a.position_s) == ("b.mp3", 0.0)
    assert len(regel_zeilen(h)) == 1


def test_fortsetzen_nach_einschalten_mit_liegendem_tobie():
    h = harnisch([zeiger("s1", "a.mp3", 0, 122.0, 3)])  # kein Neustart-Marker: Einschalten
    a = start(auflegen(h, UID_S1, "v1"))
    assert (a.datei, a.position_s) == ("b.mp3", 0.0)
    assert h.modus == "spielt"


# --- Überraschungs-Serie ----------------------------------------------------------------------------


def test_ueberraschungs_serie_wie_eine_serie():
    h = harnisch([zeiger("ueb", "u1.mp3", 0, 85.0, 1)])
    out = auflegen(h, UID_UNBEKANNT)
    a = start(out)
    assert (a.serie_id, a.datei, a.position_s) == ("ueb", "u2.mp3", 0.0)


def test_ueberraschungs_serie_am_ende_wechselt_auf_folge_1():
    h = harnisch([zeiger("ueb", "u2.mp3", 1, 89.0, 1)])
    a = start(auflegen(h, UID_UNBEKANNT))
    assert (a.datei, a.position_s) == ("u1.mp3", 0.0)


# --- Konstanten -------------------------------------------------------------------------------------


def test_konstanten():
    assert session.REST_FERTIG_S == 15.0
    assert session.REST_REGEL_MIN_FOLGE_S == 60.0
