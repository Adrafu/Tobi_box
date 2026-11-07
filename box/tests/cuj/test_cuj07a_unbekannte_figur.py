"""CUJ 7a (AP 2.4): Unbekannten Tobie auflegen, ohne HA.

* Given: Tobie ist keiner Serie zugeordnet.
* When: Er wird aufgelegt.
* Then: Die Box spielt die Überraschungs-Serie, trägt die Kennung in ``unknown.json`` ein und löscht den
  Eintrag **erst**, wenn die Bestätigung kommt (Stufe 2: ``tobibox sim ack``, ab Stufe 3a: HA). Ein Neustart
  ändert nichts daran. Wird der Tobie danach zugeordnet (Stufe 2: ``tobibox sim card``), wechselt er sofort
  auf seine Serie.

Echter Kern, echte Bibliothek, echte ``unknown.json`` und ``config.json`` (``SimBox``).
"""

from __future__ import annotations

import json

import pytest
from conftest import UID_UNBEKANNT, SimBox
from fixtures import audio

from tobibox import events as ev

SERIE = "3f9a1c07b2d4"
UEBERRASCHUNG = "c07d2e91a45b"
UID = "04a1b2c3"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id=UEBERRASCHUNG, typ="ueberraschung", dauer_s=30.0)


@pytest.fixture
def box(tmp_path):
    return SimBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)


def lege_unbekannt(box, vorgang="v1"):
    n = len(box.log)
    box.auflege(UID_UNBEKANNT, vorgang)
    return n


def test_unbekannter_tobie_spielt_die_ueberraschung_und_meldet_sich(box):
    n = lege_unbekannt(box)
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == UEBERRASCHUNG and box.modus == "spielt"
    assert box.toene(n) == ["unbekannt"]
    assert box.befehle(ev.Melden, n) == [ev.Melden("unbekannt", UID_UNBEKANNT, None)]
    e = box.unknown()[UID_UNBEKANNT]
    assert (e["art"], e["anzahl"], e["befehl_id"]) == ("unbekannt", 1, None)
    assert e["zuerst"] == e["zuletzt"] and e["zeit_ok"] is True


def test_der_eintrag_steht_auf_der_platte_im_format_des_vertrags(box):
    lege_unbekannt(box)
    roh = json.loads((box.zustand / "unknown.json").read_text(encoding="utf-8"))
    assert roh["schema_version"] == 1 and list(roh["eintraege"]) == [UID_UNBEKANNT]
    assert set(roh["eintraege"][UID_UNBEKANNT]) == {"art", "zuerst", "zuletzt", "anzahl", "zeit_ok", "befehl_id"}


def test_ohne_bestaetigung_bleibt_der_eintrag_auch_nach_dem_neustart(box):
    lege_unbekannt(box)
    box.laufe(60.0)  # nichts löscht ihn von selbst: weder Zeit noch Abheben
    box.hebe_ab()
    assert UID_UNBEKANNT in box.unknown()
    box.neustart()
    assert [e.uid for e in box.outbox.offen()] == [UID_UNBEKANNT]
    assert UID_UNBEKANNT in box.unknown()


def test_wiederholtes_auflegen_zaehlt_hoch_und_erneuert_zuletzt(box):
    lege_unbekannt(box)
    erste = box.unknown()[UID_UNBEKANNT]["zuletzt"]
    box.hebe_ab()
    box.laufe(2.0)
    lege_unbekannt(box, "v2")
    e = box.unknown()[UID_UNBEKANNT]
    assert e["anzahl"] == 2 and e["zuerst"] == erste and e["zuletzt"] > erste


def test_bestaetigung_loescht_den_eintrag_auch_ueber_den_neustart(box):
    lege_unbekannt(box)
    e = box.unknown()[UID_UNBEKANNT]
    box.sim_zeile(befehl="ack", uid=UID_UNBEKANNT, zuletzt=e["zuletzt"], art="unbekannt", grund="neu")
    assert box.unknown() == {}
    box.neustart()
    assert box.outbox.offen() == [] and box.unknown() == {}


def test_veraltete_bestaetigung_loescht_nichts(box):
    lege_unbekannt(box)
    alt = box.unknown()[UID_UNBEKANNT]["zuletzt"]
    box.hebe_ab()
    box.laufe(1.0)
    lege_unbekannt(box, "v2")  # neuere Meldung überschreibt den Eintrag
    box.sim_zeile(befehl="ack", uid=UID_UNBEKANNT, zuletzt=alt, art="unbekannt")
    assert box.unknown()[UID_UNBEKANNT]["anzahl"] == 2
    box.sim_zeile(befehl="ack", uid=UID_UNBEKANNT, zuletzt=box.unknown()[UID_UNBEKANNT]["zuletzt"], art="gelernt")
    assert UID_UNBEKANNT in box.unknown()  # falsche Art


def test_doppelte_bestaetigung_schadet_nicht(box):
    lege_unbekannt(box)
    z = box.unknown()[UID_UNBEKANNT]["zuletzt"]
    for _ in range(2):
        box.sim_zeile(befehl="ack", uid=UID_UNBEKANNT, zuletzt=z, art="unbekannt")
    assert box.unknown() == {}


def test_zuordnung_wechselt_den_liegenden_tobie_sofort_auf_die_serie(box):
    lege_unbekannt(box)
    box.laufe(5.0)
    n = len(box.log)
    box.sim_zeile(befehl="card", uid=UID_UNBEKANNT, ziel={"typ": "serie", "serie": SERIE})
    (a,) = box.befehle(ev.Abspielen, n)
    assert (a.serie_id, a.datei, a.position_s) == (SERIE, "a.wav", 0.0) and box.modus == "spielt"
    assert box.kern.session.figur.uid == UID_UNBEKANNT and box.kern.session.figur.art == "serie"
    # config.json: Revision + 1, Zuordnung im Feld ziel (Version 2)
    k = box.konfig_json()
    assert k["schema_version"] == 2 and k["revision"] == 2 and k["liste_id"] == "a3f9c1e07b2d4856"
    assert k["zuordnungen"][UID_UNBEKANNT]["ziel"] == {"typ": "serie", "serie": SERIE}
    assert k["zuordnungen"][UID]["ziel"] == {"typ": "serie", "serie": SERIE}  # die alten Zuordnungen bleiben
    # die Überraschung hat ihren Zeiger gespeichert; die Zuordnung allein löscht den Eintrag nicht
    assert UID_UNBEKANNT in box.unknown()


def test_nach_der_zuordnung_spielt_der_tobie_beim_naechsten_auflegen_seine_serie(box):
    lege_unbekannt(box)
    box.sim_zeile(befehl="card", uid=UID_UNBEKANNT, ziel={"typ": "serie", "serie": SERIE})
    box.hebe_ab()
    n = len(box.log)
    box.auflege(UID_UNBEKANNT, "v2")
    assert [x.serie_id for x in box.befehle(ev.Abspielen, n)] == [SERIE]
    assert box.befehle(ev.Melden, n) == [] and box.toene(n) == []  # kein Unbekannt-Ton, keine Meldung mehr


def test_zuordnung_auf_eine_folge(box):
    lege_unbekannt(box)
    box.sim_zeile(befehl="card", uid=UID_UNBEKANNT, ziel={"typ": "folge", "serie": SERIE, "folge": "b.wav"})
    assert box.kern.session.ziel == "folge" and box.kern.session.datei == "b.wav"
    assert box.konfig_json()["zuordnungen"][UID_UNBEKANNT]["ziel"] == {"typ": "folge", "serie": SERIE, "folge": "b.wav"}


def test_ungueltige_zuordnung_wird_abgelehnt_config_bleibt(box):
    lege_unbekannt(box)
    vorher = box.konfig_json()
    with pytest.raises(Exception, match="card abgelehnt"):
        box.sim_zeile(befehl="card", uid="kein-uid", ziel={"typ": "serie", "serie": SERIE})
    assert box.konfig_json() == vorher
