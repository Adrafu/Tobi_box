"""Die Hotspot- und Akku-Regel gibt es nur einmal (``syncregel``); beide Wege müssen übereinstimmen (AP 3.7).

Vorher gab es sie doppelt: ``power.sync_erlaubt`` und ``sync.regel_erlaubt``. Jetzt benutzen beide ``syncregel.sync_erlaubt``.
Die Tabelle gilt für beide Wege und für den laufenden Aufbau: ``Power`` misst, die Ereignisse gehen an ``Sync.setze_*``.

Regel: Heim erlaubt; Hotspot nur mit Lader oder Akku über 50 %; unbekannter Akku ohne Lader nicht erlaubt; offline nie.
"""

from __future__ import annotations

import itertools

import pytest

from tobibox import events as ev
from tobibox import power, sync, syncregel
from tobibox.config import SyncKonfig
from tobibox.power import Power, SimStrom

# (Netz-Klasse, Lader, Akku) -> erlaubt?
TABELLE = [
    ("home", None, None, True),
    ("home", False, 0, True),
    ("home", True, 100, True),
    ("hotspot", True, None, True),  # Lader gewinnt, auch bei unbekanntem Akku
    ("hotspot", True, 5, True),
    ("hotspot", False, 51, True),
    ("hotspot", None, 51, True),  # Lader unbekannt, aber Akku reicht
    ("hotspot", False, 50, False),  # genau 50 % reicht nicht
    ("hotspot", False, 30, False),
    ("hotspot", False, None, False),  # Akku unbekannt, kein Lader
    ("hotspot", None, None, False),  # beides unbekannt: lieber kein Sync
    ("hotspot", None, 50, False),
    ("offline", True, 100, False),  # offline nie, auch mit Lader und vollem Akku
    ("offline", None, None, False),
    (None, True, 100, False),  # Netz noch nicht gemeldet
]


def test_es_gibt_nur_eine_regel():
    assert power.sync_erlaubt is syncregel.sync_erlaubt
    assert power.HOTSPOT_AKKU_MIN_PROZENT is syncregel.HOTSPOT_AKKU_MIN_PROZENT == 50
    assert sync.AKKU_GRENZE_HOTSPOT == syncregel.HOTSPOT_AKKU_MIN_PROZENT


@pytest.mark.parametrize("klasse, lader, akku, erwartet", TABELLE)
def test_weg_power(klasse, lader, akku, erwartet):
    assert power.sync_erlaubt(klasse, lader, akku)[0] is erwartet


@pytest.mark.parametrize("klasse, lader, akku, erwartet", TABELLE)
def test_weg_sync(klasse, lader, akku, erwartet):
    assert sync.regel_erlaubt(klasse, lader, akku) is erwartet


@pytest.mark.parametrize("klasse, lader, akku, erwartet", TABELLE)
async def test_weg_sync_objekt_mit_eingaben(tmp_path, klasse, lader, akku, erwartet):
    sy = sync.Sync(SyncKonfig(host="h"), tmp_path / "m", ausgabe=lambda e: None)
    if klasse is not None:
        sy.setze_netz(klasse)
    if lader is not None:
        sy.setze_lader(lader)
    if akku is not None:
        sy.setze_akku(akku)
    assert sy.erlaubt() is erwartet


@pytest.mark.parametrize("klasse, lader, akku, erwartet", [t for t in TABELLE if t[0] is not None])
async def test_weg_power_misst_sync_bekommt_die_ereignisse(tmp_path, klasse, lader, akku, erwartet):
    """Der Dienst: ``Power`` misst Lader und Akku (SimStrom), ``app`` reicht die Ereignisse an ``Sync`` weiter."""
    sy = sync.Sync(SyncKonfig(host="h"), tmp_path / "m", ausgabe=lambda e: None)

    def an_sync(e: ev.Ereignis) -> None:
        if isinstance(e, ev.LaderGeaendert):
            sy.setze_lader(e.am_lader)
        elif isinstance(e, ev.AkkuStand):
            sy.setze_akku(e.prozent)

    p = Power(SimStrom(akku=akku, lader=lader), an_sync)
    await p.pruefe()
    sy.setze_netz(klasse)
    assert sy.erlaubt() is erwartet
    assert power.sync_erlaubt(klasse, p.am_lader, p.akku)[0] is erwartet  # beide Wege sehen dieselben Werte


def test_beide_wege_stimmen_fuer_jede_kombination_ueberein():
    for klasse, lader, akku in itertools.product(
        ("home", "hotspot", "offline", None), (None, False, True), (None, 0, 49, 50, 51, 100)
    ):
        assert power.sync_erlaubt(klasse, lader, akku)[0] is sync.regel_erlaubt(klasse, lader, akku), (klasse, lader, akku)


@pytest.mark.parametrize(
    "klasse, lader, akku, grund",
    [("home", None, None, "ok"), ("hotspot", False, 50, "regel"), ("hotspot", None, None, "regel"), ("offline", True, 100, "netz_weg")],
)
def test_grund_fuer_syncabgebrochen(klasse, lader, akku, grund):
    assert syncregel.sync_erlaubt(klasse, lader, akku)[1] == grund


async def test_nicht_erlaubter_start_meldet_immer_regel_auch_offline(tmp_path):
    """Vertrag: ``SyncStarten`` ohne Erlaubnis -> ``SyncAbgebrochen("regel")`` (``netz_weg`` ist nur der Abbruchgrund eines laufenden Syncs)."""
    aus: list = []
    sy = sync.Sync(SyncKonfig(host="h"), tmp_path / "m", ausgabe=aus.append, rsync="/gibt/es/nicht")
    sy.setze_netz("offline")
    assert await sy.start("ha") is False
    assert aus == [ev.SyncAbgebrochen("regel")]
