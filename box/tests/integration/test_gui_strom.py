"""Fehler der Mac-Abnahme (11.11.): „Strom am Eingang“ abhaken, Akku-Regler ziehen -> Warnung, Strom bleibt aus.

Der echte Weg: HTTP der Seite (``/api/befehl``) -> ``sim.sock`` -> ``App`` -> ``idle``, mit ``[strom]`` auf Simulation
(``SimStrom``), wie auf dem Mac.
"""

from __future__ import annotations

import pytest

from integration.test_app_e2e import warte
from integration.test_gui import anzeige, befehl, gui  # noqa: F401  (Fixtures)
from integration.test_sim_cli import lauf, log_zeilen  # noqa: F401  (Fixtures)
from integration.test_sim_cli import welt as welt_basis  # noqa: F401


@pytest.fixture
def welt(welt_basis):  # noqa: F811
    with open(welt_basis["toml"], "a", encoding="utf-8") as f:
        f.write('[netz]\nquelle = "sim"\n[strom]\nquelle = "sim"\nintervall_s = 1\n')
    return welt_basis


async def _status(srv) -> dict:
    return (await anzeige(srv))["status"]


async def test_strom_abziehen_und_akku_senken_gibt_die_warnung_und_der_strom_bleibt_aus(gui):
    srv, welt_, _ = gui
    assert (await befehl(srv, befehl="strom", lader=True, akku=80))["ok"]
    await warte(lambda: _ist(srv, True, 80), 5.0, "(am Lader, 80 %)")

    assert (await befehl(srv, befehl="strom", lader=False))["ok"]
    await warte(lambda: _ist(srv, False, 80), 5.0, "(ohne Strom)")
    assert (await befehl(srv, befehl="strom", akku=9))["ok"]
    await warte(lambda: _ist(srv, False, 9), 5.0, "(ohne Strom, 9 %)")

    # über mehrere Messungen von ``power`` (intervall_s = 1) bleibt der Strom aus
    import asyncio

    await asyncio.sleep(3.0)
    s = await _status(srv)
    assert s["lader"] is False and s["akku_prozent"] == 9
    assert [z for z in log_zeilen(welt_, "rueckmeldung_gesperrt") if z["daten"].get("strom") is True] == []
    assert "ausgegeben" in [z["ergebnis"] for z in log_zeilen(welt_, "akku_warnung")]


async def _ist(srv, lader, akku) -> bool:
    s = await _status(srv)
    return s["lader"] is lader and s["akku_prozent"] == akku


async def test_die_anzeige_nennt_beide_strom_quellen_getrennt(gui):
    """Die Seite schreibt jeden Haken aus seiner eigenen Quelle, nicht den zusammengeführten Wert in den Haken von ``pisugar``."""
    srv, _, _ = gui
    assert (await befehl(srv, befehl="strom", lader=False))["ok"]
    assert (await befehl(srv, befehl="strom", lader=True, quelle="leser"))["ok"]

    async def beide() -> bool:
        return (await anzeige(srv))["anzeige"].get("strom_quellen") == {"pisugar": False, "leser": True}

    await warte(beide, 5.0, "(pisugar aus, Leser an)")
    assert (await _status(srv))["lader"] is True  # zusammengeführt: der Leser gilt
