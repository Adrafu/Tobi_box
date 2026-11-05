"""Reine Zeigerregeln (``core-interface.md``, 6.3) und ihr Zusammenspiel mit ``session``."""

from __future__ import annotations

import pytest
from conftest import UID_S1, SitzungsHarnisch, in_zustand

from tobibox import events as ev
from tobibox import pointer

SERIE = ev.Serie("s", "S", "normal", "s", ("a.mp3", "b.mp3", "c.mp3"))


def zg(datei="b.mp3", index=1, pos=100.0, zaehler=4) -> ev.Zeiger:
    return ev.Zeiger("s", datei, index, pos, zaehler)


def test_kein_zeiger_folge_1_position_0():
    assert pointer.ort_am_zeiger(SERIE, None) == pointer.Ort("a.mp3", 0, 0.0, False)


def test_ruecksprung_3_s():
    assert pointer.ort_am_zeiger(SERIE, zg(pos=100.0)) == pointer.Ort("b.mp3", 1, 97.0, False)


def test_ruecksprung_nie_unter_null():
    assert pointer.ort_am_zeiger(SERIE, zg(pos=1.5)).position_s == 0.0


def test_position_null_kein_ruecksprung():
    assert pointer.ort_am_zeiger(SERIE, zg(pos=0.0)).position_s == 0.0


def test_leere_serie_kein_ort():
    leer = ev.Serie("s", "S", "normal", "s", ())
    assert pointer.ort_am_zeiger(leer, zg()) is None


@pytest.mark.parametrize(
    "datei,index,erwartet",
    [
        ("geloescht.mp3", 1, ("b.mp3", 1)),  # Folge gelöscht/umbenannt: Platz des Index
        ("geloescht.mp3", 2, ("c.mp3", 2)),
        ("geloescht.mp3", 3, ("a.mp3", 0)),  # Index hinter der Liste: Folge 1
        ("geloescht.mp3", 99, ("a.mp3", 0)),
    ],
)
def test_zeiger_auf_fehlende_folge(datei, index, erwartet):
    ort = pointer.ort_am_zeiger(SERIE, zg(datei=datei, index=index, pos=50.0))
    assert (ort.datei, ort.index) == erwartet
    assert ort.position_s == 0.0
    assert ort.folge_fehlte is True


def test_nach_der_letzten_folge_wieder_folge_1():
    assert pointer.naechste_folge(SERIE, "c.mp3") == ("a.mp3", 0)
    assert pointer.naechste_folge(SERIE, "a.mp3") == ("b.mp3", 1)


def test_naechste_folge_bei_fehlender_datei_nimmt_hinweis():
    assert pointer.naechste_folge(SERIE, "weg.mp3", 1) == ("c.mp3", 2)


def test_springen_zyklisch_beide_richtungen():
    assert pointer.springe(SERIE, 0, -1) == ("c.mp3", 2)
    assert pointer.springe(SERIE, 2, +1) == ("a.mp3", 0)


@pytest.mark.parametrize("x,erwartet", [(412.56, 412.5), (0.99, 0.9), (0.0, 0.0), (7.0, 7.0), (0.3, 0.3), (-1.0, 0.0)])
def test_abrunden(x, erwartet):
    assert pointer.abrunden(x) == erwartet


def test_unveraendert_vergleicht_abgerundete_position():
    alt = zg(pos=100.5)
    assert pointer.unveraendert(alt, "b.mp3", 1, 100.59)
    assert not pointer.unveraendert(alt, "b.mp3", 1, 100.6)
    assert not pointer.unveraendert(alt, "c.mp3", 1, 100.5)
    assert not pointer.unveraendert(alt, "b.mp3", 2, 100.5)
    assert not pointer.unveraendert(None, "b.mp3", 1, 100.5)


def test_neuer_zeiger_erhoeht_zaehler():
    assert pointer.neuer_zeiger(None, "s", "a.mp3", 0, 5.55).zaehler == 1
    assert pointer.neuer_zeiger(zg(zaehler=4), "s", "b.mp3", 1, 5.55) == ev.Zeiger("s", "b.mp3", 1, 5.5, 5)


def test_periodisch_faellig_ab_30_s():
    assert not pointer.periodisch_faellig(0.0, 29.9)
    assert pointer.periodisch_faellig(0.0, 30.0)


# --- im Zusammenspiel mit der Sitzung ---------------------------------------


def test_sitzung_legt_auf_und_spielt_mit_3_s_ruecksprung():
    h = SitzungsHarnisch(zeiger=[ev.Zeiger("s1", "b.mp3", 1, 100.0, 2)])
    ab = [b for b in h.auflegen(UID_S1) if isinstance(b, ev.Abspielen)]
    assert [(a.datei, a.position_s) for a in ab] == [("b.mp3", 97.0)]


def test_sitzung_zeiger_auf_geloeschte_folge_spielt_platz_des_index_und_protokolliert():
    h = SitzungsHarnisch(zeiger=[ev.Zeiger("s1", "alt.mp3", 2, 100.0, 2)])
    h.auflegen(UID_S1)
    abspielen = [b for b in h.alle if isinstance(b, ev.Abspielen)]
    assert [(a.datei, a.position_s) for a in abspielen] == [("c.mp3", 0.0)]
    assert any(isinstance(b, ev.Protokoll) and b.ereignis == "zeiger_folge_fehlt" for b in h.alle)


def test_sitzung_folge_zu_ende_bei_liegender_figur_pause_und_zeiger_auf_naechste_folge():
    h = in_zustand("spielt")
    out = h.sende(ev.FolgeZuEnde("s1", "a.mp3"))
    assert h.modus == "beendet"
    sp = next(b for b in out if isinstance(b, ev.ZeigerSpeichern))
    assert (sp.datei, sp.index, sp.position_s, sp.grund) == ("b.mp3", 1, 0.0, "folgenende")
    assert next(b for b in out if isinstance(b, ev.Pausieren)).grund == "folgenende"
    assert not any(isinstance(b, ev.Abspielen) for b in out)


def test_sitzung_nach_der_letzten_folge_zeiger_auf_folge_1():
    h = in_zustand("spielt")
    h.sende(ev.FolgeZuEnde("s1", "a.mp3"))
    h.sende(ev.Hauptknopf("kurz"))  # spielt b
    h.sende(ev.FolgeZuEnde("s1", "b.mp3"))
    h.sende(ev.Hauptknopf("kurz"))  # spielt c
    out = h.sende(ev.FolgeZuEnde("s1", "c.mp3"))
    sp = next(b for b in out if isinstance(b, ev.ZeigerSpeichern))
    assert (sp.datei, sp.index, sp.position_s) == ("a.mp3", 0, 0.0)
    assert h.modus == "beendet"


def test_sitzung_zurueck_in_beendet_spielt_die_eben_beendete_folge():
    h = in_zustand("beendet")  # a.mp3 lief zu Ende, Zeiger steht auf b.mp3
    out = h.sende(ev.Zurueck())
    ab = [b for b in out if isinstance(b, ev.Abspielen)]
    assert [(a.datei, a.position_s) for a in ab] == [("a.mp3", 0.0)]
    assert h.modus == "spielt"


def test_sitzung_speichert_nur_bei_aenderung_und_alle_30_s():
    """Die Drosselung liegt allein in der Sitzung: genau alle 30 s, nie dazwischen."""
    h = in_zustand("spielt")
    h.position(sek=12.0)
    start = h.uhr.mono
    assert h.z.letzte_speicherung == start
    zeiten, grund = [], []
    for _ in range(100):  # 100 s Wiedergabe, Position wandert jede Sekunde mit
        for b in h.takt(1.0):
            if isinstance(b, ev.ZeigerSpeichern):
                zeiten.append(round(h.uhr.mono - start))
                grund.append(b.grund)
        h.position(sek=h.z.position_s + 1.0)
    assert zeiten == [30, 60, 90]
    assert grund == ["periodisch"] * 3


def test_sitzung_speichert_nicht_periodisch_wenn_die_position_stehen_bleibt():
    h = in_zustand("spielt")
    h.position(sek=12.0)
    h.takt(1.0)
    erste = [b for b in h.takt(31.0) if isinstance(b, ev.ZeigerSpeichern)]
    assert len(erste) == 1
    assert not [b for b in h.takt(61.0) if isinstance(b, ev.ZeigerSpeichern)]  # Position unverändert


def test_sitzung_unveraenderter_zeiger_wird_nicht_erneut_gespeichert():
    h = in_zustand("spielt")
    h.position(sek=5.0)
    assert [b for b in h.sende(ev.Hauptknopf("kurz")) if isinstance(b, ev.ZeigerSpeichern)]
    h.sende(ev.Hauptknopf("kurz"))  # weiter ab Zeiger
    h.position(sek=5.0)  # gleiche Stelle (nach Rücksprung 2.0 -> wieder 5.0)
    out = h.sende(ev.Hauptknopf("kurz"))
    assert not [b for b in out if isinstance(b, ev.ZeigerSpeichern)]
