"""CUJ 17: Kopfhörer (AP 4.4 und 4.8).

Eine Serie spielt über den Lautsprecher, ein Stecker wird erkannt (am Mac simuliert über ``SimKopfhoerer`` und ``Buchse``). Zuerst gilt
die Kopfhörer-Grenze (25), dann schaltet der Ausgang um. Beim Ziehen gilt wieder Lautsprecher mit der normalen Grenze.

Die ``Buchse`` ist die echte; sie sendet in einen echten Kern (``CujBox``). Wie ``app.py`` sie startet, prüft ``unit/test_app_stufe4.py``.
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import stufe4

from tobibox import events as ev
from tobibox.headphones import Buchse, SimKopfhoerer

pytestmark = pytest.mark.asyncio

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"
KOPFHOERER_GRENZE = 25  # ``GeraeteEinstellungen(60, 40, 25)`` in ``CujBox``
START = 40


def aufbau(medien):
    stufe4.serie(medien, "rabe", ["a.wav", "b.wav"], SERIE, "Rabe", 60.0)
    stufe4.ueberraschung(medien)


@pytest.fixture
def box(tmp_path):
    return CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)


@pytest.fixture
def buchse(box):
    treiber = SimKopfhoerer()
    return treiber, Buchse(treiber, box.sende, intervall_s=0.01, entprellen=2)


def reihenfolge(befehle):
    return [type(b).__name__ for b in befehle if isinstance(b, (ev.LautstaerkeSetzen, ev.AusgangWaehlen))]


async def test_einstecken_erst_die_grenze_dann_der_ausgang(box, buchse):
    treiber, b = buchse
    box.auflege(UID)
    box.laufe(3.0)
    n = len(box.log)
    treiber.setze(True)
    await b.melde(True)
    neu = box.log[n:]
    assert reihenfolge(neu) == ["LautstaerkeSetzen", "AusgangWaehlen"]  # nie umgekehrt
    laut = next(x for x in neu if isinstance(x, ev.LautstaerkeSetzen))
    assert (laut.prozent, laut.grenze) == (KOPFHOERER_GRENZE, KOPFHOERER_GRENZE)
    assert next(x for x in neu if isinstance(x, ev.AusgangWaehlen)).ausgang == "kopfhoerer"
    assert box.modus == "spielt" and box.player.spielt  # die Wiedergabe läuft weiter
    assert stufe4.wirksam(box) == KOPFHOERER_GRENZE


async def test_ziehen_wieder_lautsprecher_mit_der_normalen_grenze(box, buchse):
    treiber, b = buchse
    box.auflege(UID)
    await b.melde(True)
    n = len(box.log)
    await b.melde(False)
    neu = box.log[n:]
    assert next(x for x in neu if isinstance(x, ev.AusgangWaehlen)).ausgang == "lautsprecher"
    assert stufe4.wirksam(box) == START  # der Wunsch (40) gilt wieder, die globale Grenze ist 60
    assert stufe4.lautstaerken(box)[-1].grenze == 60
    assert "kopfhoerer" not in box.kern.grenzen


async def test_ausgang_wird_nur_bei_aenderung_gewechselt(box, buchse):
    treiber, b = buchse
    await b.melde(True)
    n = len(box.log)
    await b.melde(True)
    assert box.log[n:] == []


async def test_drehregler_geht_mit_stecker_nie_ueber_die_kopfhoerer_grenze(box, buchse):
    _, b = buchse
    box.auflege(UID)
    await b.melde(True)
    for _ in range(6):
        box.sende(ev.LautstaerkeDrehen(+5))
    assert stufe4.wirksam(box) <= KOPFHOERER_GRENZE
    assert all(x.prozent <= x.grenze for x in stufe4.lautstaerken(box))


async def test_start_mit_stecker_gilt_die_kopfhoerer_grenze_vor_dem_ersten_abspielen(tmp_path):
    """Die erste Messung kommt nach ``GeraeteEinstellungen``; steckt schon ein Stecker, spielt nichts lauter als 25."""
    box = CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)
    box.neustart()
    b = Buchse(SimKopfhoerer(True), box.sende)
    await b.start()
    n = len(box.log)
    box.auflege(UID)
    assert all(x.prozent <= KOPFHOERER_GRENZE for x in stufe4.lautstaerken(box, n))


async def test_wackelkontakt_wird_entprellt(box, buchse):
    """Ein einzelner Ausreißer der Messung ändert nichts; erst zwei gleiche Werte nacheinander gelten."""
    treiber, b = buchse
    await b.start()
    n = len(box.log)
    treiber.setze(True)
    await b.pruefe()
    treiber.setze(False)
    await b.pruefe()
    assert box.log[n:] == []
    treiber.setze(True)
    await b.pruefe()
    await b.pruefe()
    assert [x.ausgang for x in box.log[n:] if isinstance(x, ev.AusgangWaehlen)] == ["kopfhoerer"]


async def test_stecker_waehrend_gute_nacht_und_leiser_es_gilt_das_minimum(box, buchse):
    """Mehrere Grenzen (Kopfhörer, „leiser“, Ausblenden) zugleich: das Minimum gewinnt (siehe auch ``test_konflikte``)."""
    _, b = buchse
    stufe4.setze_konfig(box, gute_nacht=ev.GuteNacht(1, 10), fenster_liste=(stufe4.fenster("f", "leiser", "00:00", "23:59", 30),))
    box.uhr.setze_wall(stufe4.wall(2026, 11, 9, 12, 0))
    box.auflege(UID)
    box.laufe(4.0)
    assert stufe4.wirksam(box) == 30
    await b.melde(True)
    assert stufe4.wirksam(box) == KOPFHOERER_GRENZE  # Kopfhörer 25 < leiser 30
