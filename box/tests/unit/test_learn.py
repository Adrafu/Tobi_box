"""Teilautomat ``learn``: jede Zeile der Tabelle „Lernmodus“ und die Festlegungen aus Punkt 8 und 9."""

from __future__ import annotations

from dataclasses import replace

import pytest

from tobibox import events as ev
from tobibox import learn
from tobibox.clock import SimUhr

UID = "04a1b2c3"


def typen(out):
    return [type(o) for o in out]


def toene(out):
    return [o.ton for o in out if isinstance(o, ev.TonSpielen)]


def cmd(uhr, bid="b1", ttl=60.0):
    return ev.HaLernmodus(bid, uhr.wall + ttl)


def lernt(uhr, bid="b1"):
    z, _ = learn.step(learn.neuer_zustand(), cmd(uhr, bid), uhr.jetzt())
    return z


@pytest.fixture
def uhr():
    return SimUhr()


def test_aus_befehl_startet(uhr):
    z, out = learn.step(learn.neuer_zustand(), cmd(uhr), uhr.jetzt())
    assert learn.kennzeichen(z) == "lernt"
    assert toene(out) == ["lernen_beginn"]
    assert ev.LernenGeaendert(True) in out


def test_aus_abgelaufener_befehl_ignoriert(uhr):
    e = ev.HaLernmodus("b1", uhr.wall - 1)
    z, out = learn.step(learn.neuer_zustand(), e, uhr.jetzt())
    assert learn.kennzeichen(z) == "aus"
    assert typen(out) == [ev.Protokoll]
    assert out[0].ereignis == "lernmodus_befehl" and out[0].ergebnis == "abgelaufen"


def test_befehl_genau_an_der_grenze_gilt(uhr):
    z, _ = learn.step(learn.neuer_zustand(), ev.HaLernmodus("b1", uhr.wall), uhr.jetzt())
    assert learn.kennzeichen(z) == "lernt"


def test_unsichere_uhr_lehnt_ab(uhr):
    uhr.setze_zeit("unbekannt", False)
    z, out = learn.step(learn.neuer_zustand(), cmd(uhr), uhr.jetzt())
    assert learn.kennzeichen(z) == "aus"
    abl = [o for o in out if isinstance(o, ev.EreignisSenden)]
    assert abl == [ev.EreignisSenden("befehl_abgelehnt", {"befehl": "lernen", "befehl_id": "b1", "grund": "zeit_unsicher"})]
    assert not toene(out)


@pytest.mark.parametrize("bekannt", [True, False])
def test_lernt_aufgelegt_meldet_gelernt(uhr, bekannt):
    z = lernt(uhr, "b7")
    z, out = learn.step(z, ev.Aufgelegt(UID, "ntag", False, 1, "v1"), uhr.jetzt())
    assert learn.kennzeichen(z) == "aus"
    assert ev.Melden("gelernt", UID, "b7") in out
    assert toene(out) == ["lernen_ende"]
    assert ev.LernenGeaendert(False) in out


def test_lernt_frist_ohne_tobie(uhr):
    z = lernt(uhr)
    z, out = learn.step(z, ev.Takt(), uhr.vor(learn.LERN_FRIST_S - 0.1))
    assert learn.kennzeichen(z) == "lernt" and not out
    z, out = learn.step(z, ev.Takt(), uhr.vor(0.1))
    assert learn.kennzeichen(z) == "aus"
    assert toene(out) == ["lernen_ende"]
    assert not any(isinstance(o, ev.Melden) for o in out)


def test_frist_laeuft_auf_mono_nicht_wall(uhr):
    z = lernt(uhr)
    uhr.setze_wall(uhr.wall + 10_000)  # Wanduhr springt
    z, out = learn.step(z, ev.Takt(), uhr.jetzt())
    assert learn.kennzeichen(z) == "lernt"


def test_lernt_abbruch(uhr):
    z = lernt(uhr)
    z, out = learn.step(z, ev.HaLernmodusAbbruch("x", uhr.wall + 30), uhr.jetzt())
    assert learn.kennzeichen(z) == "aus"
    assert toene(out) == ["lernen_ende"] and ev.LernenGeaendert(False) in out


def test_abbruch_in_aus_wirkungslos(uhr):
    z, out = learn.step(learn.neuer_zustand(), ev.HaLernmodusAbbruch("x", uhr.wall + 30), uhr.jetzt())
    assert learn.kennzeichen(z) == "aus"
    assert typen(out) == [ev.Protokoll]


def test_abbruch_abgelaufen_ignoriert_bei_sicherer_uhr(uhr):
    z = lernt(uhr)
    z, out = learn.step(z, ev.HaLernmodusAbbruch("x", uhr.wall - 1), uhr.jetzt())
    assert learn.kennzeichen(z) == "lernt"


def test_abbruch_bei_unsicherer_uhr_wird_ausgefuehrt(uhr):
    z = lernt(uhr)
    uhr.setze_zeit("unbekannt", False)
    z, out = learn.step(z, ev.HaLernmodusAbbruch("x", uhr.wall - 1), uhr.jetzt())
    assert learn.kennzeichen(z) == "aus"
    assert not any(isinstance(o, ev.EreignisSenden) for o in out)


def test_gesperrt_aendert_nichts(uhr):
    z = lernt(uhr)
    z2, out = learn.step(z, ev.Gesperrt(1, "v1"), uhr.jetzt())
    assert replace(z2, liegt=None) == z and z2.liegt == "v1" and not out  # nur die liegende Vorgangs-ID wird geführt


def test_zweiter_befehl_in_lernt_ignoriert(uhr):
    z = lernt(uhr, "b1")
    z2, out = learn.step(z, cmd(uhr, "b2"), uhr.vor(30))
    assert z2 == z and not toene(out)


def test_unbekannte_ereignisse_in_aus_und_lernt(uhr):
    for z in (learn.neuer_zustand(), lernt(uhr)):
        for e in (ev.Takt(), ev.Abgehoben(1, None), ev.Hauptknopf("kurz"), ev.SyncGestartet()):
            z2, out = learn.step(z, e, uhr.jetzt())
            assert z2 == z and not out


def test_aufgelegt_in_aus_aendert_nichts(uhr):
    z, out = learn.step(learn.neuer_zustand(), ev.Aufgelegt(UID, "ntag", False, 1, "v1"), uhr.jetzt())
    assert learn.kennzeichen(z) == "aus" and not out


def test_wiedermeldung_des_liegenden_tobies_beendet_den_lernmodus_nicht(uhr):
    """Gleiche Vorgangs-ID wie der liegende Tobie (3.1, 9.1): kein ``Melden``, kein Ende, keine Zustandsänderung."""
    z, _ = learn.step(learn.neuer_zustand(), ev.Aufgelegt(UID, "ntag", False, 0, "v1"), uhr.jetzt())  # liegt schon
    z, _ = learn.step(z, cmd(uhr), uhr.jetzt())
    z2, out = learn.step(z, ev.Aufgelegt(UID, "ntag", False, 1, "v1"), uhr.jetzt())
    assert z2 == z and not out and learn.kennzeichen(z2) == "lernt"


def test_wiedermeldung_eines_gesperrten_tobies_aendert_nichts(uhr):
    z, _ = learn.step(learn.neuer_zustand(), ev.Gesperrt(0, "v1"), uhr.jetzt())
    z, _ = learn.step(z, cmd(uhr), uhr.jetzt())
    z2, out = learn.step(z, ev.Gesperrt(1, "v1"), uhr.jetzt())
    assert z2 == z and not out


def test_nach_dem_abheben_ist_dieselbe_kennung_mit_neuer_vorgangs_id_ein_neues_auflegen(uhr):
    z, _ = learn.step(learn.neuer_zustand(), ev.Aufgelegt(UID, "ntag", False, 0, "v1"), uhr.jetzt())
    z, _ = learn.step(z, cmd(uhr), uhr.jetzt())
    z, _ = learn.step(z, ev.Abgehoben(1, "v1"), uhr.jetzt())
    z, out = learn.step(z, ev.Aufgelegt(UID, "ntag", False, 2, "v2"), uhr.jetzt())
    assert ev.Melden("gelernt", UID, "b1") in out and learn.kennzeichen(z) == "aus"


def test_anderer_tobie_waehrend_ein_anderer_liegt_wird_gelernt(uhr):
    z, _ = learn.step(learn.neuer_zustand(), ev.Aufgelegt("04aaaaaa", "ntag", False, 0, "v1"), uhr.jetzt())
    z, _ = learn.step(z, cmd(uhr), uhr.jetzt())
    z, out = learn.step(z, ev.Aufgelegt(UID, "ntag", False, 1, "v2"), uhr.jetzt())
    assert ev.Melden("gelernt", UID, "b1") in out and z.liegt == "v2"


def test_bestaetigt_aendert_den_lernmodus_nicht(uhr):
    """Entscheidung H: Das Warten der Sitzung ist nicht Sache von ``learn``; ``Bestaetigt`` ändert hier nichts."""
    z = lernt(uhr)
    z2, out = learn.step(z, ev.Bestaetigt(UID, "abgelehnt", "z", "gelernt"), uhr.jetzt())
    assert z2 == z and not out


def test_aufgelegt_gibt_nur_den_endeton_und_die_meldung_keine_wiedergabe(uhr):
    """Entscheidung H: ``learn`` selbst gibt nur Ton, Meldung, Ende; ``unbekannt`` und Abspielen warten in ``session``."""
    z = lernt(uhr)
    _, out = learn.step(z, ev.Aufgelegt(UID, "ntag", False, 0, "v1"), uhr.jetzt())
    assert toene(out) == ["lernen_ende"]
    assert [type(o) for o in out if isinstance(o, (ev.Melden, ev.Abspielen))] == [ev.Melden]
