"""Zwei Strom-Quellen im Rest des Dienstes: Statussammler, Sync-Regel und ``LeserSim`` (Ein/Aus, 10.11.)."""

from __future__ import annotations

from conftest import LeserSim

from tobibox import events as ev
from tobibox.clock import SimUhr
from tobibox.status import Statussammler


def test_status_lader_ist_der_zusammengefuehrte_wert_leser_gewinnt():
    s = Statussammler()
    j = SimUhr().jetzt()
    assert s.lader is None
    s.beobachte(ev.LaderGeaendert(False, "pisugar"), j)
    assert s.lader is False
    s.beobachte(ev.LaderGeaendert(True, "leser"), j)
    assert s.lader is True  # bei Widerspruch der Leser
    s.beobachte(ev.LaderGeaendert(True, "pisugar"), j)
    s.beobachte(ev.LaderGeaendert(False, "leser"), j)
    assert s.lader is False
    assert s.als_dict(j, (), None)["lader"] is False


def test_leser_sim_hello_mit_strom_gibt_caps_und_lader_in_dieser_reihenfolge():
    aus: list = []
    sim = LeserSim(aus.append)
    sim.hello(strom=True)
    assert aus == [ev.LeserHallo(1, "1.1.0", "fa4e0000", "4.2", "strom"), ev.LaderGeaendert(True, "leser")]
    sim.lader(False)
    assert aus[-1] == ev.LaderGeaendert(False, "leser")
    sim.placed("04a1b2c3")
    assert isinstance(aus[-1], ev.Aufgelegt)  # seq zählt nicht mit LADER: die Figur hat seq=0


def test_leser_sim_firmware_1x_ohne_caps():
    aus: list = []
    sim = LeserSim(aus.append)
    sim.hello()
    assert aus == [ev.LeserHallo(1, "1.0.0", "fa4e0000", "4.2", "")]
