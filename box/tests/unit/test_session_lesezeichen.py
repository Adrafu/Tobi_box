"""Entscheidung N (09.11.): Lesezeichen je Tobie mit Ablauf.

Jeder Zeiger behält seine Stelle. Wurde er länger als ``Konfig.lesezeichen_tage`` (Vorgabe 14, 0 = nie) nicht
benutzt, beginnt beim Fortsetzen dieselbe Folge von vorn (Track 0, Position 0). Die Regel gilt nur bei sicherer Uhr
und nur für Zeiger mit Zeitstempel. Sie greift in ``session._start`` und geht der Restregel (Entscheidung I) voran.
"""

from __future__ import annotations

import pytest
from conftest import UID_CD, UID_FOLGE, UID_S1, UID_S3, UID_UNBEKANNT, ZUORDNUNGEN, SitzungsHarnisch, mk_konfig, ppos, zeiger

from tobibox import events as ev
from tobibox import pointer, session

TAG = 86400.0
W0 = 1_700_000_000.0  # Wanduhr der simulierten Uhr beim Start des Harnischs

S1D = ev.Serie(
    "s1", "Serie 1", "normal", "s1", ("a.mp3", "b.mp3", "c.mp3"),
    dauern={"a.mp3": (123.6,), "b.mp3": (100.0,), "c.mp3": (30.0,)},
)
S3D = ev.Serie(
    "s3", "Serie 3", "normal", "s3", ("cd", "z.mp3"),
    {"cd": ("cd/01.mp3", "cd/02.mp3", "cd/03.mp3"), "z.mp3": ("z.mp3",)},
    {"cd": (50.0, 50.0, 50.0)},
)
UEBD = ev.Serie(
    "ueb", "Überraschung", "ueberraschung", "ueb", ("u1.mp3", "u2.mp3"),
    dauern={"u1.mp3": (90.0,), "u2.mp3": (90.0,)},
)
UID_S4 = "04a1b2d0"
S4D = ev.Serie(
    "s4", "Serie 4", "normal", "s4", ("1.mp3", "2.mp3", "3.mp3"),
    dauern={"1.mp3": (100.0,), "2.mp3": (100.0,), "3.mp3": (100.0,)},
)


def alt(tage: float = 0.0, sekunden: float = 0.0) -> float:
    """Zeitstempel (Wanduhr), der beim Start des Harnischs so viel zurückliegt."""
    return W0 - tage * TAG - sekunden


def z_s1(pos=60.0, benutzt=None, track=0, datei="a.mp3", index=0):
    return zeiger("s1", datei, index, pos, 3, track=track, benutzt_wall=benutzt)


def harnisch(zeiger_liste, lesezeichen_tage=14, **kw) -> SitzungsHarnisch:
    h = SitzungsHarnisch(serien=(S1D, S3D, S4D, UEBD), konfig=False, zeiger=zeiger_liste, **kw)
    h.sende(ev.KonfigGeladen(mk_konfig({**ZUORDNUNGEN, UID_S4: ev.Zuordnung("serie", "s4")}, lesezeichen_tage=lesezeichen_tage)))
    return h


def auflegen(h, uid=UID_S1, v="v2"):
    return h.sende(ev.Aufgelegt(uid, "ntag", False, 5, v))


def start(befehle) -> ev.Abspielen:
    (a,) = [b for b in befehle if isinstance(b, ev.Abspielen)]
    return a


def zeilen(h, name="lesezeichen_abgelaufen") -> list[ev.Protokoll]:
    return [o for o in h.alle if isinstance(o, ev.Protokoll) and o.ereignis == name]


# --- abgelaufen, nicht abgelaufen, Grenze ------------------------------------------------------------


def test_abgelaufen_beginnt_dieselbe_folge_von_vorn():
    h = harnisch([z_s1(60.0, alt(tage=20))])
    a = start(auflegen(h))
    assert (a.datei, a.track, a.position_s) == ("a.mp3", 0, 0.0)  # kein Rücksprung, kein Fortsetzen bei 57 s
    (z,) = zeilen(h)
    assert z.ebene == "INFO" and z.ergebnis == "von_vorn" and z.daten["alter_tage"] == 20.0
    assert z.daten["serie"] == "s1" and z.daten["folge"] == "a.mp3" and z.daten["uid"] == UID_S1
    assert h.modus == "spielt" and h.z.datei == "a.mp3" and h.z.position_s == 0.0


def test_nicht_abgelaufen_setzt_mit_ruecksprung_fort():
    h = harnisch([z_s1(60.0, alt(tage=3))])
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("a.mp3", 57.0)
    assert zeilen(h) == []


@pytest.mark.parametrize(
    "alter_s, gilt",
    [
        (13 * TAG + 23 * 3600, False),
        (14 * TAG - 1, False),
        (14 * TAG, False),  # genau an der Grenze: noch nicht abgelaufen
        (14 * TAG + 0.5, True),
        (14 * TAG + 1, True),
        (15 * TAG, True),
    ],
)
def test_grenze_bei_14_tagen(alter_s, gilt):
    h = harnisch([z_s1(60.0, alt(sekunden=alter_s))])
    a = start(auflegen(h))
    assert (a.position_s == 0.0) is gilt
    assert (len(zeilen(h)) == 1) is gilt


@pytest.mark.parametrize("tage, alter_tage, gilt", [(7, 8, True), (7, 6, False), (1, 2, True), (30, 29, False), (30, 31, True)])
def test_die_frist_ist_einstellbar(tage, alter_tage, gilt):
    h = harnisch([z_s1(60.0, alt(tage=alter_tage))], lesezeichen_tage=tage)
    a = start(auflegen(h))
    assert (a.position_s == 0.0) is gilt


def test_ohne_feld_in_der_konfiguration_gilt_14():
    k = ev.Konfig(1, "a3f9c1e07b2d4856", dict(ZUORDNUNGEN), ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60))
    assert k.lesezeichen_tage == 14 == session.LESEZEICHEN_TAGE
    for tage, gilt in ((13, False), (15, True)):
        h = SitzungsHarnisch(serien=(S1D, S3D, UEBD), konfig=False, zeiger=[z_s1(60.0, alt(tage=tage))])
        h.sende(ev.KonfigGeladen(k))
        assert (start(auflegen(h)).position_s == 0.0) is gilt


def test_ohne_konfiguration_gilt_ebenfalls_14():
    h = SitzungsHarnisch(serien=(S1D, UEBD), konfig=False, zeiger=[z_s1(60.0, alt(tage=15))])
    assert h.z.konfig is None
    # ohne Konfiguration ist der Tobie unbekannt (Überraschungs-Serie); der Zeiger der Überraschung läuft nach 14 Tagen ab
    h = SitzungsHarnisch(serien=(S1D, UEBD), konfig=False, zeiger=[zeiger("ueb", "u1.mp3", 0, 40.0, 1, benutzt_wall=alt(tage=15))])
    assert start(auflegen(h, UID_UNBEKANNT)).position_s == 0.0


# --- 0 = nie, unsichere Uhr, Zeiger ohne Zeitstempel ------------------------------------------------------


@pytest.mark.parametrize("tage_alt", [15, 400, 5000])
def test_null_heisst_laeuft_nie_ab(tage_alt):
    h = harnisch([z_s1(60.0, alt(tage=tage_alt))], lesezeichen_tage=0)
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("a.mp3", 57.0)
    assert zeilen(h) == []


def test_unsichere_uhr_nichts_laeuft_ab():
    h = harnisch([z_s1(60.0, alt(tage=400))])
    h.uhr.setze_zeit("system", False)
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("a.mp3", 57.0)
    assert zeilen(h) == []


def test_sichere_uhr_danach_gilt_die_regel_wieder():
    h = harnisch([z_s1(60.0, alt(tage=400))])
    h.uhr.setze_zeit("system", False)
    auflegen(h)
    h.sende(ev.Abgehoben(1, "v2"))
    h.uhr.setze_zeit("ntp", True)
    assert start(auflegen(h, UID_S1, "v3")).position_s == 0.0


def test_zeiger_ohne_zeitstempel_laeuft_nie_ab():
    h = harnisch([z_s1(60.0, None)])
    h.uhr.vor(1000 * TAG)
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("a.mp3", 57.0)
    assert zeilen(h) == []


def test_zeitstempel_in_der_zukunft_laeuft_nicht_ab():
    h = harnisch([z_s1(60.0, W0 + 5 * TAG)])  # Uhr wurde zurückgestellt
    assert start(auflegen(h)).position_s == 57.0


# --- Serie gegen Folge ---------------------------------------------------------------------------------


def test_serie_bleibt_in_derselben_folge_nicht_zurueck_auf_folge_1():
    h = harnisch([zeiger("s1", "b.mp3", 1, 70.0, 3, benutzt_wall=alt(tage=30))])
    a = start(auflegen(h))
    assert (a.datei, a.track, a.position_s) == ("b.mp3", 0, 0.0)
    assert h.z.index == 1
    (z,) = zeilen(h)
    assert z.daten["art"] == "serie" and z.daten["folge"] == "b.mp3"


def test_folgen_tobie_beginnt_dieselbe_folge_von_vorn():
    h = harnisch([zeiger("s1", "b.mp3", None, 70.0, 3, art="folge", benutzt_wall=alt(tage=30))])
    a = start(auflegen(h, UID_FOLGE))
    assert (a.datei, a.track, a.position_s) == ("b.mp3", 0, 0.0)
    (z,) = zeilen(h)
    assert z.daten["art"] == "folge" and h.z.ziel == "folge"


def test_folge_mit_mehreren_tracks_beginnt_bei_track_0():
    h = harnisch([zeiger("s3", "cd", 0, 20.0, 1, track=2, benutzt_wall=alt(tage=15))])
    a = start(auflegen(h, UID_S3))
    assert (a.datei, a.track, a.position_s) == ("cd", 0, 0.0)
    h = harnisch([zeiger("s3", "cd", None, 20.0, 1, track=2, art="folge", benutzt_wall=alt(tage=15))])
    a = start(auflegen(h, UID_CD))
    assert (a.datei, a.track, a.position_s) == ("cd", 0, 0.0)


def test_jeder_zeiger_hat_sein_eigenes_alter():
    # Serie s1 lange nicht benutzt, Serie s4 gestern: nur s1 beginnt von vorn, s4 behält seine Stelle
    h = harnisch([z_s1(60.0, alt(tage=20)), zeiger("s4", "2.mp3", 1, 40.0, 1, benutzt_wall=alt(tage=1))])
    assert start(auflegen(h, UID_S1)).position_s == 0.0
    h.sende(ev.Abgehoben(1, "v2"))
    a = start(auflegen(h, UID_S4, "v3"))
    assert (a.datei, a.position_s) == ("2.mp3", 37.0)


def test_serien_zeiger_und_folgen_zeiger_der_selben_folge_laufen_getrennt_ab():
    h = harnisch([
        zeiger("s1", "b.mp3", 1, 50.0, 1, benutzt_wall=alt(tage=1)),
        zeiger("s1", "b.mp3", None, 50.0, 1, art="folge", benutzt_wall=alt(tage=20)),
    ])
    assert start(auflegen(h, UID_S1)).position_s == 47.0
    h.sende(ev.Abgehoben(1, "v2"))
    assert start(auflegen(h, UID_FOLGE, "v3")).position_s == 0.0


def test_lesezeichen_beim_start_nicht_speichern():
    h = harnisch([z_s1(60.0, alt(tage=20))])
    out = auflegen(h)
    assert not [b for b in out if isinstance(b, ev.ZeigerSpeichern)]
    assert h.z.zeiger[("serie", "s1", "")].position_s == 60.0  # bis zum nächsten Speichern bleibt der alte Stand


# --- Zusammenspiel mit der Restregel (Entscheidung I) --------------------------------------------------------


def test_abgelaufen_geht_der_restregel_voran_serie_bleibt_in_der_folge():
    # Rest 1,6 s: ohne Ablauf spielte die nächste Folge. Abgelaufen: dieselbe Folge von vorn, keine Restregel.
    h = harnisch([z_s1(122.0, alt(tage=20))])
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("a.mp3", 0.0)
    assert len(zeilen(h)) == 1 and zeilen(h, "rest_regel") == []


def test_nicht_abgelaufen_gilt_die_restregel_wie_bisher():
    h = harnisch([z_s1(122.0, alt(tage=2))])
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("b.mp3", 0.0)
    assert zeilen(h) == [] and zeilen(h, "rest_regel")[0].ergebnis == "naechste_folge"


def test_abgelaufen_bei_folgen_tobie_mit_kleinem_rest():
    h = harnisch([zeiger("s1", "b.mp3", None, 95.0, 1, art="folge", benutzt_wall=alt(tage=20))])
    a = start(auflegen(h, UID_FOLGE))
    assert (a.datei, a.position_s) == ("b.mp3", 0.0)
    assert len(zeilen(h)) == 1 and zeilen(h, "rest_regel") == []


def test_abgelaufen_ohne_bekannte_dauer_keine_restregel_zeile():
    h = harnisch([zeiger("s3", "z.mp3", 1, 500.0, 1, benutzt_wall=alt(tage=20))])
    a = start(auflegen(h, UID_S3))
    assert (a.datei, a.position_s) == ("z.mp3", 0.0)
    assert zeilen(h, "rest_regel") == []


def test_zeiger_schon_vorn_keine_zeile_aber_die_restregel_entfaellt():
    # Zeiger steht auf 0 (zum Beispiel nach dem Folgenende): nichts zu ändern, kein Protokoll
    h = harnisch([z_s1(0.0, alt(tage=20), datei="b.mp3", index=1)])
    a = start(auflegen(h))
    assert (a.datei, a.position_s) == ("b.mp3", 0.0)
    assert zeilen(h) == []


def test_fehlende_folge_und_fehlender_track_haben_keine_messung():
    h = harnisch([zeiger("s1", "weg.mp3", 2, 60.0, 1, benutzt_wall=alt(tage=20))])
    a = start(auflegen(h))
    assert a.datei == "c.mp3" and zeilen(h) == []  # Platz 2 in der Liste, Position 0 wie bisher
    h = harnisch([zeiger("s1", "a.mp3", 0, 60.0, 1, track=5, benutzt_wall=alt(tage=20))])
    a = start(auflegen(h))
    assert (a.datei, a.track, a.position_s) == ("a.mp3", 0, 0.0) and zeilen(h) == []


# --- Alle Wege des Fortsetzens -------------------------------------------------------------------------------


def test_weg_auflegen_nach_abheben():
    h = harnisch([])
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 60.0))
    h.sende(ev.Abgehoben(1, "v2"))
    h.uhr.vor(15 * TAG)
    assert start(auflegen(h, UID_S1, "v3")).position_s == 0.0
    assert len(zeilen(h)) == 1


def test_weg_hauptknopf_nach_pause():
    h = harnisch([])
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 60.0))
    h.sende(ev.Hauptknopf("kurz"))
    assert h.modus == "pausiert"
    h.uhr.vor(15 * TAG)
    a = start(h.sende(ev.Hauptknopf("kurz")))
    assert (a.datei, a.position_s) == ("a.mp3", 0.0)
    assert zeilen(h)[0].daten["alter_tage"] == 15.0


def test_weg_hauptknopf_nach_pause_noch_nicht_abgelaufen():
    h = harnisch([])
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 60.0))
    h.sende(ev.Hauptknopf("kurz"))
    h.uhr.vor(10 * TAG)
    assert start(h.sende(ev.Hauptknopf("kurz"))).position_s == 57.0


def test_weg_einschalten_mit_liegendem_tobie():
    h = harnisch([z_s1(60.0, alt(tage=20))])  # kein Neustart-Marker: Einschalten
    a = start(auflegen(h, UID_S1, "v1"))
    assert (a.datei, a.position_s) == ("a.mp3", 0.0)
    assert h.modus == "spielt"


def test_weg_dienst_neustart_erst_der_hauptknopf():
    h = harnisch([z_s1(60.0, alt(tage=20))], neustart_uid=UID_S1)
    out = auflegen(h)
    assert h.modus == "pausiert" and not [b for b in out if isinstance(b, ev.Abspielen)]
    assert zeilen(h) == []
    a = start(h.sende(ev.Hauptknopf("kurz")))
    assert (a.datei, a.position_s) == ("a.mp3", 0.0)
    assert len(zeilen(h)) == 1


def test_weg_neue_zuordnung_startet_das_neue_ziel_am_zeiger():
    # Ein Tobie ohne Zuordnung spielt die Überraschungs-Serie; dann ordnet HA ihm die Serie s1 zu
    neu = "04a1b2ff"
    h = harnisch([z_s1(60.0, alt(tage=20))])
    auflegen(h, neu)
    assert h.z.serie_id == "ueb"
    konfig = mk_konfig({**ZUORDNUNGEN, neu: ev.Zuordnung("serie", "s1")}, revision=2)
    a = start(h.sende(ev.KonfigGeladen(konfig)))
    assert (a.serie_id, a.datei, a.position_s) == ("s1", "a.mp3", 0.0)
    assert len(zeilen(h)) == 1


# --- Speichern des Zeitstempels (Wanduhr nur über ``jetzt``) ------------------------------------------------------


def test_speichern_traegt_die_wanduhr_ein():
    h = harnisch([])
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 60.0))
    (sp,) = [b for b in h.sende(ev.Hauptknopf("kurz")) if isinstance(b, ev.ZeigerSpeichern)]
    assert sp.wall == h.uhr.wall
    assert h.z.zeiger[("serie", "s1", "")].benutzt_wall == h.uhr.wall


def test_speichern_bei_unsicherer_uhr_traegt_nichts_ein_und_behaelt_den_alten_stempel():
    h = harnisch([z_s1(10.0, alt(tage=1))])
    h.uhr.setze_zeit("system", False)
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 60.0))
    (sp,) = [b for b in h.sende(ev.Hauptknopf("kurz")) if isinstance(b, ev.ZeigerSpeichern)]
    assert sp.wall is None
    assert h.z.zeiger[("serie", "s1", "")].benutzt_wall == alt(tage=1)


def test_speichern_bei_unsicherer_uhr_ohne_stempel_bleibt_ohne_stempel():
    h = harnisch([])
    h.uhr.setze_zeit("system", False)
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 60.0))
    h.sende(ev.Hauptknopf("kurz"))
    assert h.z.zeiger[("serie", "s1", "")].benutzt_wall is None


def test_unveraenderter_zeiger_mit_altem_stempel_wird_neu_gestempelt():
    # Benutzung heißt auch Abheben, ohne dass sich die Position ändert (zum Beispiel sofort nach dem Auflegen)
    h = harnisch([z_s1(60.0, alt(tage=5))])
    auflegen(h)  # Start bei 57,0
    h.sende(ppos("s1", "a.mp3", 60.0))
    out = h.sende(ev.Abgehoben(1, "v2"))
    (sp,) = [b for b in out if isinstance(b, ev.ZeigerSpeichern)]
    assert sp.wall == h.uhr.wall and h.z.zeiger[("serie", "s1", "")].benutzt_wall == h.uhr.wall


def test_unveraenderter_zeiger_mit_frischem_stempel_wird_nicht_neu_geschrieben():
    h = harnisch([z_s1(60.0, alt(sekunden=60))])
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 60.0))
    out = h.sende(ev.Abgehoben(1, "v2"))
    assert not [b for b in out if isinstance(b, ev.ZeigerSpeichern)]


def test_unveraenderter_zeiger_ohne_stempel_bekommt_einen():
    h = harnisch([z_s1(60.0, None)])
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 60.0))
    out = h.sende(ev.Abgehoben(1, "v2"))
    (sp,) = [b for b in out if isinstance(b, ev.ZeigerSpeichern)]
    assert sp.wall == h.uhr.wall


def test_abgelaufener_zeiger_wird_nach_dem_spielen_neu_gestempelt():
    h = harnisch([z_s1(60.0, alt(tage=20))])
    auflegen(h)
    h.sende(ppos("s1", "a.mp3", 12.0))
    h.sende(ev.Abgehoben(1, "v2"))
    z = h.z.zeiger[("serie", "s1", "")]
    assert (z.position_s, z.benutzt_wall) == (12.0, h.uhr.wall)
    h.uhr.vor(2 * TAG)
    assert start(auflegen(h, UID_S1, "v3")).position_s == 9.0  # nicht mehr abgelaufen


# --- pointer: die reinen Funktionen -------------------------------------------------------------------------------


def test_pointer_hilfen():
    z = zeiger("s1", "a.mp3", 0, 1.0, 1, benutzt_wall=1000.0)
    assert pointer.lesezeichen_alter_s(z, 1500.0, True) == 500.0
    assert pointer.lesezeichen_alter_s(z, 1500.0, False) is None
    assert pointer.lesezeichen_alter_s(None, 1500.0, True) is None
    assert pointer.lesezeichen_alter_s(zeiger("s1", "a.mp3", 0, 1.0, 1), 1500.0, True) is None
    assert pointer.lesezeichen_abgelaufen(14 * TAG, 14) is False
    assert pointer.lesezeichen_abgelaufen(14 * TAG + 0.1, 14) is True
    assert pointer.lesezeichen_abgelaufen(10**9, 0) is False
    assert pointer.lesezeichen_abgelaufen(None, 14) is False
