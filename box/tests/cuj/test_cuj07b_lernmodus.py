"""CUJ 7b (AP 2.4): Lernmodus ohne HA.

* Given: Tobias startet den Lernmodus (Stufe 2: ``tobibox sim learn``; ab Stufe 3a: Aktion in HA) mit
  einem Ziel, einer Serie oder einer einzelnen Folge.
* When: Innerhalb von 2 min wird ein Tobie aufgelegt.
* Then: Die Box meldet ihn als ``gelernt`` (mit der ID des Befehls), der Lernmodus endet. Die Zuordnung
  schreibt nicht die Box, sondern HA (Stufe 2: der HA-Ersatz, ``ha_ersatz.py``): ``config.json`` bekommt
  Revision + 1, die Box bestätigt mit ``zugeordnet``, löscht den Eintrag in ``unknown.json``, und der Tobie
  spielt sein Ziel.

Dazu: Frist 2 min, Abbruch, abgelaufener Befehl, unsichere Uhr (``core-interface.md``, Tabelle „Lernmodus“,
Regel 9.9). Echter Kern mit ``learn``, echte ``unknown.json`` und ``config.json`` (``SimBox``).
"""

from __future__ import annotations

import pytest
from conftest import SimBox
from fixtures import audio

from tobibox import events as ev
from tobibox.learn import LERN_FRIST_S

SERIE = "3f9a1c07b2d4"
UEBERRASCHUNG = "c07d2e91a45b"
UID = "04a1b2c3"
NEU = "04ffeedd"  # der Tobie, der gelernt wird
NEU2 = "04ffeede"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id=UEBERRASCHUNG, typ="ueberraschung", dauer_s=30.0)


@pytest.fixture
def box(tmp_path):
    return SimBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)


def lerne_serie(box, ttl=60):
    return box.sim_zeile(befehl="learn", typ="serie", serie=SERIE, ttl=ttl)


def lerne_folge(box, folge="b.wav", ttl=60):
    return box.sim_zeile(befehl="learn", typ="folge", serie=SERIE, folge=folge, ttl=ttl)


def test_lernmodus_beginnt_mit_ton_und_meldet_den_zustand(box):
    n = len(box.log)
    lerne_serie(box)
    assert box.lernmodus() is True
    assert box.toene(n) == ["lernen_beginn"]
    assert [p.ereignis for p in box.protokoll if p.baustein == "learn"] == ["lernmodus_beginn"]


def test_ziel_serie_tobie_wird_gelernt_zugeordnet_bestaetigt_und_spielt_die_serie(box):
    lerne_serie(box)
    n = len(box.log)
    box.auflege(NEU)
    bid = box.sim.lernbefehl_id
    # gemeldet als gelernt mit der ID des Befehls, nicht zusätzlich als unbekannt (Regel 6.2.4)
    assert box.befehle(ev.Melden, n) == [ev.Melden("gelernt", NEU, bid)]
    assert box.lernmodus() is False and box.toene(n)[-1] == "lernen_ende"
    # HA-Ersatz: config.json Revision + 1, Zuordnung im Feld ziel
    k = box.konfig_json()
    assert k["revision"] == 2 and k["zuordnungen"][NEU]["ziel"] == {"typ": "serie", "serie": SERIE}
    # bestätigt mit grund zugeordnet: der Eintrag ist aus unknown.json gelöscht
    assert box.unknown() == {}
    # der Tobie spielt jetzt die Serie (nicht die Überraschung)
    assert box.befehle(ev.Abspielen, n)[-1].serie_id == SERIE and box.modus == "spielt"
    assert box.kern.session.figur.art == "serie"


def test_ziel_folge_der_tobie_spielt_diese_folge(box):
    lerne_folge(box, "b.wav")
    n = len(box.log)
    box.auflege(NEU)
    k = box.konfig_json()
    assert k["zuordnungen"][NEU]["ziel"] == {"typ": "folge", "serie": SERIE, "folge": "b.wav"}
    a = box.befehle(ev.Abspielen, n)[-1]
    assert (a.serie_id, a.datei, a.position_s) == (SERIE, "b.wav", 0.0)
    assert box.kern.session.ziel == "folge"
    assert box.unknown() == {}


def test_der_gelernte_eintrag_bleibt_ohne_den_ha_ersatz_bis_zur_bestaetigung(box):
    """Der Kern allein bestätigt nichts: Ohne HA-Ersatz bleibt der Eintrag mit ``befehl_id`` stehen."""
    lerne_serie(box)
    box.ha_ersatz.gelernt = lambda eintrag: None  # HA antwortet nicht
    box.auflege(NEU)
    e = box.unknown()[NEU]
    assert (e["art"], e["befehl_id"]) == ("gelernt", box.sim.lernbefehl_id)
    box.neustart()
    assert NEU in box.unknown()
    box.sim_zeile(befehl="ack", uid=NEU, zuletzt=e["zuletzt"], art="gelernt", grund="zugeordnet")
    assert box.unknown() == {}


def test_nach_der_zuordnung_ist_der_lernmodus_vorbei_der_naechste_tobie_ist_unbekannt(box):
    lerne_serie(box)
    box.auflege(NEU)
    box.hebe_ab()
    n = len(box.log)
    box.auflege(NEU2, "v2")
    assert box.befehle(ev.Melden, n) == [ev.Melden("unbekannt", NEU2, None)]
    assert box.befehle(ev.Abspielen, n)[-1].serie_id == UEBERRASCHUNG


def test_bereits_zugeordneter_tobie_wird_neu_zugeordnet(box):
    lerne_folge(box, "c.wav")
    box.auflege(UID)  # war auf die Serie zugeordnet
    assert box.konfig_json()["zuordnungen"][UID]["ziel"] == {"typ": "folge", "serie": SERIE, "folge": "c.wav"}
    assert box.unknown() == {}


# --- Frist, Abbruch ---------------------------------------------------------------------------


def test_frist_zwei_minuten_dann_endet_der_lernmodus_von_selbst(box):
    lerne_serie(box)
    n = len(box.log)
    box.laufe(LERN_FRIST_S - 1.0)
    assert box.lernmodus() is True
    box.laufe(1.5)
    assert box.lernmodus() is False and box.toene(n) == ["lernen_ende"]
    m = len(box.log)
    box.auflege(NEU)  # nach Ablauf: ein ganz normaler unbekannter Tobie
    assert box.befehle(ev.Melden, m) == [ev.Melden("unbekannt", NEU, None)]
    assert box.befehle(ev.Abspielen, m)[-1].serie_id == UEBERRASCHUNG
    assert box.konfig_json()["revision"] == 1  # nichts zugeordnet


def test_frist_laeuft_auf_der_monotonen_uhr_ein_sprung_der_wanduhr_aendert_nichts(box):
    lerne_serie(box)
    box.laufe(30.0)
    box.uhr.setze_wall(box.uhr.wall + 3600)
    box.laufe(60.0)
    assert box.lernmodus() is True  # erst 90 s vergangen
    box.laufe(31.0)
    assert box.lernmodus() is False


def test_abbruch_beendet_den_lernmodus_mit_ton(box):
    lerne_serie(box)
    n = len(box.log)
    box.sim_zeile(befehl="learn_abort")
    assert box.lernmodus() is False and box.toene(n) == ["lernen_ende"]
    m = len(box.log)
    box.auflege(NEU)
    assert box.befehle(ev.Melden, m) == [ev.Melden("unbekannt", NEU, None)]
    assert NEU not in box.konfig_json()["zuordnungen"]


def test_abbruch_ohne_lernmodus_ist_wirkungslos(box):
    n = len(box.log)
    box.sim_zeile(befehl="learn_abort")
    assert box.toene(n) == [] and box.befehle(ev.EreignisSenden, n) == []
    assert [p.ergebnis for p in box.protokoll if p.ereignis == "lernmodus_abbruch"] == ["wirkungslos"]


def test_nach_dem_abbruch_gilt_ein_alter_lernbefehl_nicht(box):
    """Ein späterer Tobie wird nicht aus einem früheren Lernlauf zugeordnet."""
    lerne_serie(box)
    box.sim_zeile(befehl="learn_abort")
    box.auflege(NEU)
    assert NEU not in box.konfig_json()["zuordnungen"]


def test_zweiter_lernbefehl_im_lernmodus_wird_ignoriert(box):
    lerne_serie(box)
    n = len(box.log)
    lerne_serie(box)
    assert box.toene(n) == []
    assert any(p.ereignis == "lernmodus_befehl" and p.ergebnis == "ignoriert" for p in box.protokoll)


def test_gesperrter_tobie_im_lernmodus_aendert_nichts(box):
    lerne_serie(box)
    n = len(box.log)
    box.sende(ev.Gesperrt(0, "v1"))
    assert box.lernmodus() is True
    assert box.befehle(ev.Melden, n) == []
    box.hebe_ab("v1")
    box.auflege(NEU, "v2")  # der Lernmodus lief weiter und nimmt den nächsten Tobie
    assert box.befehle(ev.Melden, n)[-1] == ev.Melden("gelernt", NEU, box.sim.lernbefehl_id)


# --- abgelaufener Befehl, unsichere Uhr -----------------------------------------------------------


def test_abgelaufener_befehl_wird_ignoriert_nur_protokoll(box):
    e = box.sim.zeile_zu_ereignis('{"befehl":"learn","typ":"serie","serie":"%s","ttl":1}' % SERIE)
    box.uhr.vor(5.0)  # der Befehl kommt zu spät an (Broker war weg)
    n = len(box.log)
    box.sende(e)
    assert box.lernmodus() is False and box.toene(n) == []
    assert box.befehle(ev.EreignisSenden, n) == []  # keine Meldung an HA
    assert [p.ergebnis for p in box.protokoll if p.ereignis == "lernmodus_befehl"] == ["abgelaufen"]


def test_unsichere_uhr_lehnt_den_lernbefehl_ab_und_meldet_den_grund(box):
    box.uhr.setze_zeit("unbekannt", False)
    n = len(box.log)
    lerne_serie(box)
    assert box.lernmodus() is False
    (m,) = box.befehle(ev.EreignisSenden, n)
    assert m.art == "befehl_abgelehnt"
    assert m.daten == {"befehl": "lernen", "befehl_id": box.sim.lernbefehl_id, "grund": "zeit_unsicher"}
    assert box.toene(n) == []


def test_abbruch_geht_auch_bei_unsicherer_uhr(box):
    lerne_serie(box)
    box.uhr.setze_zeit("unbekannt", False)
    n = len(box.log)
    box.sim_zeile(befehl="learn_abort")
    assert box.lernmodus() is False and box.toene(n) == ["lernen_ende"]
    assert box.befehle(ev.EreignisSenden, n) == []  # der Abbruch wird nie mit befehl_abgelehnt beantwortet


def test_lernen_wird_wieder_angenommen_sobald_die_uhr_sicher_ist(box):
    box.uhr.setze_zeit("unbekannt", False)
    lerne_serie(box)
    box.uhr.setze_zeit("ntp", True)
    lerne_serie(box)
    assert box.lernmodus() is True


# --- HA-Ersatz lehnt ab, wenn er kein Ziel kennt ----------------------------------------------------


def test_ohne_lernziel_lehnt_der_ha_ersatz_ab_der_eintrag_ist_trotzdem_weg(box):
    """Ein gelernter Tobie ohne Ziel (z. B. der Dienst lief zwischendurch neu): ``abgelehnt``, nichts zugeordnet."""
    lerne_serie(box)
    box.sim.lernziel = None
    box.auflege(NEU)
    assert NEU not in box.konfig_json()["zuordnungen"] and box.konfig_json()["revision"] == 1
    assert box.unknown() == {}  # ``abgelehnt`` löscht den Eintrag wie jeder Grund (mqtt-v1, 3.6)
    assert box.befehle(ev.Abspielen)[-1].serie_id == UEBERRASCHUNG
