"""Kern in Stufe 3a (AP 3.7): Ereignisse aus HA, Netz, Strom und Sync.

Bis ``idle`` in AP 4.8 eingetragen ist, leitet der Kern ``HaSyncAnstossen`` und ``AkkuTiefstand`` an ``sync`` weiter
(``core._uebergang_3a``). Steht ``idle`` in ``TEILAUTOMATEN``, ist der Übergangsweg stumm (kein doppelter ``SyncStarten``).
"""

from __future__ import annotations

import pytest
from conftest import KernHarnisch

from tobibox import core, idle
from tobibox import events as ev


def befehle(h, typ):
    return [b for b in h.voll if isinstance(b, typ)]


def test_ha_sync_befehl_wird_zu_syncstarten_ha():
    h = KernHarnisch()
    h.sende(ev.HaSyncAnstossen("b1", h.uhr.wall + 60))
    assert befehle(h, ev.SyncStarten) == [ev.SyncStarten("ha")]
    assert any(p.ereignis == "sync_befehl" and p.ergebnis == "angenommen" for p in befehle(h, ev.Protokoll))


def test_abgelaufener_sync_befehl_wird_ignoriert_nur_protokoll():
    h = KernHarnisch()
    h.sende(ev.HaSyncAnstossen("b1", h.uhr.wall - 1))
    assert befehle(h, ev.SyncStarten) == [] and befehle(h, ev.EreignisSenden) == []
    assert any(p.ereignis == "sync_befehl" and p.ergebnis == "abgelaufen" for p in befehle(h, ev.Protokoll))


def test_unsichere_uhr_lehnt_den_sync_befehl_ab_und_meldet_es_ha():
    h = KernHarnisch()
    h.uhr.setze_zeit("unbekannt", False)
    h.sende(ev.HaSyncAnstossen("b1", h.uhr.wall + 60))
    assert befehle(h, ev.SyncStarten) == []
    (m,) = befehle(h, ev.EreignisSenden)
    assert m.art == "befehl_abgelehnt" and m.daten == {"befehl": "sync", "befehl_id": "b1", "grund": "zeit_unsicher"}


def test_akku_tiefstand_bricht_den_sync_ab():
    h = KernHarnisch()
    h.sende(ev.AkkuTiefstand())
    assert befehle(h, ev.SyncAbbrechen) == [ev.SyncAbbrechen("akku_tiefstand")]


def test_syncstarten_wird_nicht_von_herunterfahren_gefolgt_in_stufe_3a():
    """Das Herunterfahren bei Tiefstand und lang gedrücktem Knopf gehört ``idle`` (AP 4.8)."""
    h = KernHarnisch()
    h.sende(ev.AkkuTiefstand())
    assert befehle(h, ev.Herunterfahren) == []


@pytest.mark.parametrize(
    "e",
    [
        ev.NetzKlasse("home"), ev.NetzKlasse("hotspot"), ev.NetzKlasse("offline"),
        ev.LaderGeaendert(True), ev.LaderGeaendert(False), ev.AkkuStand(40),
        ev.SyncGestartet(), ev.SyncFertig(3, 0), ev.SyncAbgebrochen("regel"), ev.SyncAbgebrochen("netz_weg"),
        ev.HaVerbindung(True), ev.HaVerbindung(False), ev.ZeitquelleGeaendert("ntp", True),
        ev.UpdateGestartet("1.2.0"), ev.SelbsttestErgebnis(True),
    ],
)
def test_diese_ereignisse_stoeren_den_kern_nicht_und_erzeugen_keine_befehle(e):
    h = KernHarnisch()
    modus = h.modus
    out = h.sende(e)
    assert [b for b in out if not isinstance(b, (ev.Protokoll, ev.ZustandMelden))] == []
    assert h.modus == modus


def test_netz_und_sync_waehrend_der_wiedergabe_aendern_nichts_am_hoerspiel():
    h = KernHarnisch()
    h.sende(ev.Aufgelegt("04a1b2c3", "ntag", False, 0, "v1"))
    assert h.modus == "spielt"
    for e in (ev.NetzKlasse("home"), ev.SyncGestartet(), ev.SyncFertig(2, 0), ev.NetzKlasse("offline"), ev.HaVerbindung(False)):
        out = h.sende(e)
        assert not [b for b in out if isinstance(b, (ev.Pausieren, ev.Abspielen))]
    assert h.modus == "spielt"


def test_mit_idle_im_kern_ist_der_uebergangsweg_stumm(monkeypatch):
    monkeypatch.setattr(core, "TEILAUTOMATEN", core.TEILAUTOMATEN + (("idle", idle),))
    h = KernHarnisch()
    h.sende(ev.HaSyncAnstossen("b1", h.uhr.wall + 60))
    assert befehle(h, ev.SyncStarten) == [ev.SyncStarten("ha")]  # genau einer, von ``idle``
    h.sende(ev.AkkuTiefstand())
    assert len(befehle(h, ev.SyncAbbrechen)) <= 1
    assert core._uebergang_3a(ev.HaSyncAnstossen("b2", 1e12), h.uhr.jetzt()) == []
