"""CUJ 6 (AP 1.6): Gesperrter Tonie (Passwort unbekannt).

Bewiesene Schritte von CUJ 6:

* When: Die Firmware sendet ``LOCKED`` (echte Zeilenverarbeitung ``reader.Leser``, Vorgangs-ID ohne Kennung).
  Then: Die Überraschungs-Serie spielt, von vorn, mit der Vorgangs-ID der Zeile; Protokollzeile
  ``zugeordnet`` mit Ergebnis ``ueberraschung``.
* "Nicht zuordenbar (keine Kennung)": kein ``Melden`` (nichts landet in ``unknown.json``), kein Ton
  ``unbekannt``, keine Aktion.
* "Kurze Aussetzer starten sie nicht neu": Eine zweite ``LOCKED``-Zeile ohne ``REMOVED`` dazwischen (Lesung
  setzt aus, Firmware meldet erneut), eine Wiedermeldung nach ``HELLO`` mit derselben Vorgangs-ID und eine
  Leser-Unterbrechung (Alarm, dann ``HELLO``, ``LOCKED``) innerhalb der Frist lassen den Ton weiterlaufen;
  es gibt kein zweites ``Abspielen``. (Lücken bis 1,0 s erzeugen bei der Firmware gar keine Zeile, siehe
  CUJ 8.)
* Das Abheben (>= 1,1 s, ``REMOVED``) pausiert; ein neues Auflegen ist ein neues Auflegen und startet die
  Überraschung wieder.
* Ein gesperrter Tonie ersetzt keinen Tobie mit Kennung: erst ``LOCKED``, dann ein bekannter Tobie wechselt.

Nicht doppelt geprüft: Fallbacks bei fehlender Überraschungs-Serie (``unit/test_session.py``).
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import audio

from tobibox import events as ev

SERIE = "3f9a1c07b2d4"
UEB = "c07d2e91a45b"
UID = "04a1b2c3"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id=UEB, typ="ueberraschung", dauer_s=8.0)


@pytest.fixture
def box(tmp_path):
    b = CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)
    b.leser.hello()
    return b


def test_locked_startet_die_ueberraschung_von_vorn_ohne_melden_und_ohne_unbekannt_ton(box):
    n = len(box.log)
    box.leser.locked()
    (a,) = box.befehle(ev.Abspielen)
    assert (a.serie_id, a.datei, a.position_s) == (UEB, "ton.wav", 0.0)
    assert a.vorgang == box.kern.session.figur.vorgang and box.kern.session.figur.uid is None
    assert box.modus == "spielt"
    assert box.befehle(ev.Melden) == [] and box.befehle(ev.TonSpielen, n) == []
    z = next(p for p in box.protokoll if p.ereignis == "zugeordnet")
    assert (z.ergebnis, z.daten["serie"], z.daten["uid"]) == ("ueberraschung", UEB, None)


def test_zweite_locked_zeile_ohne_removed_startet_nicht_neu(box):
    box.leser.locked()
    box.laufe(3.0)
    n = len(box.log)
    box.leser.locked()  # Aussetzer: Firmware meldet gesperrt erneut
    box.laufe(1.0)
    assert box.befehle(ev.Abspielen, n) == [] and box.befehle(ev.Pausieren, n) == []
    assert box.modus == "spielt" and box.player.spielt
    assert box.player.elapsed == pytest.approx(4.0, abs=0.01)  # der Ton lief ohne Unterbrechung weiter


def test_leser_neustart_mit_locked_innerhalb_der_frist_startet_nicht_neu(box):
    box.leser.locked()
    vorgang = box.kern.session.figur.vorgang
    box.laufe(3.0)
    n = len(box.log)
    box.leser.hello()  # ESP32 startet neu: seq 0
    box.laufe(0.5)
    box.leser.locked()  # derselbe gesperrte Tonie, seq=0 -> gleiche Vorgangs-ID
    assert box.kern.session.figur.vorgang == vorgang
    box.laufe(1.0)
    assert box.befehle(ev.Abspielen, n) == [] and box.befehle(ev.Pausieren, n) == []
    assert box.modus == "spielt"


def test_abheben_pausiert_und_neues_auflegen_startet_die_ueberraschung_wieder(box):
    box.leser.locked()
    box.laufe(3.0)
    box.leser.removed()
    assert box.modus == "pausiert" and not box.player.spielt
    n = len(box.log)
    box.leser.locked()
    assert len(box.befehle(ev.Abspielen, n)) == 1 and box.modus == "spielt"


def test_ueberraschung_spielt_bis_zum_ende_und_haelt_dann_an(box):
    box.leser.locked()
    box.laufe(8.5)  # Ton dauert 8 s
    assert box.modus == "beendet" and not box.player.spielt
    assert [p.grund for p in box.befehle(ev.Pausieren)] == ["folgenende"]


def test_bekannter_tobie_nach_gesperrtem_ersetzt_die_ueberraschung(box):
    box.leser.locked()
    box.laufe(2.0)
    box.leser.removed()
    n = len(box.log)
    box.leser.placed(UID)
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == SERIE and box.modus == "spielt"


def test_gesperrter_tonie_waehrend_serie_spielt_wechselt_auf_ueberraschung(box):
    """Firmware meldet bei Wechsel REMOVED + LOCKED; geht REMOVED verloren, wechselt es trotzdem."""
    box.leser.placed(UID)
    box.laufe(4.0)
    n = len(box.log)
    box.leser.locked()
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.serie_id == UEB
    assert box.resume_json()["serien"][SERIE]["position_s"] == pytest.approx(4.0, abs=0.01)  # Serie gespeichert
