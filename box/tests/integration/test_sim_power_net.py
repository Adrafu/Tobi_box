"""``tobibox sim power`` und ``tobibox sim net`` als eigene Prozesse gegen den laufenden Dienst (AP 3.7).

Echter Dienst (``python -m tobibox``) mit ``[netz]`` und ``[strom]`` (Simulation), echtem MPD und ``fake_reader``.
``tobibox status`` zeigt danach HA-Verbindung, Netz, Akku und Sync.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from integration.test_app_e2e import warte
from integration.test_sim_cli import beende, cli, dienst_bereit, sim, starte_dienst, welt  # noqa: F401  (Fixtures)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader  # noqa: E402


@pytest.fixture
async def lauf_mit_strom_und_netz(welt):  # noqa: F811
    with open(welt["toml"], "a", encoding="utf-8") as f:
        f.write('[netz]\nquelle = "sim"\n[strom]\nquelle = "sim"\n')
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        proc = starte_dienst(welt)
        try:
            await dienst_bereit(welt, fr)
            yield welt
        finally:
            beende(proc)


async def live(welt) -> dict:
    import json

    code, out, _ = await cli(welt, "status", "--json")
    return json.loads(out)["live"]


async def test_sim_power_und_net_wirken_im_dienst_und_status_zeigt_sie(lauf_mit_strom_und_netz):
    welt = lauf_mit_strom_und_netz
    code, antwort, _ = await sim(welt, "power", "--charger", "on", "--battery", "40")
    assert code == 0 and antwort == {"ok": True}
    code, antwort, _ = await sim(welt, "net", "hotspot")
    assert code == 0 and antwort == {"ok": True}

    async def angekommen() -> bool:
        s = (await live(welt))["status"]
        return (s["lader"], s["akku_prozent"], s["netz"]) == (True, 40, "hotspot")

    await warte(angekommen, 10.0, "(Status zeigt Lader, Akku und Netz)")
    v = (await live(welt))["verbindungen"]
    assert v["strom"] == {"eingerichtet": True, "akku_prozent": 40, "lader": True}
    assert v["netz"] == {"eingerichtet": True, "klasse": "hotspot"}
    assert v["ha"] == {"eingerichtet": False, "verbunden": False}
    assert v["sync"]["eingerichtet"] is False  # kein [sync] in dieser Konfiguration

    code, text, _ = await cli(welt, "status")
    assert "HA: nicht eingerichtet ([mqtt] fehlt); Netz: hotspot; Akku: 40 %, am Lader" in text
    assert "Sync: nicht eingerichtet ([sync] fehlt)" in text

    assert (await sim(welt, "power", "--charger", "off"))[0] == 0
    assert (await sim(welt, "net", "offline"))[0] == 0
    await warte(lambda: _netz_ist(welt, "offline"), 10.0, "(Netz offline)")


async def _netz_ist(welt, klasse: str) -> bool:
    return (await live(welt))["status"]["netz"] == klasse


async def test_sim_net_ohne_abschnitt_netz_gibt_dennoch_die_klasse(welt):
    """Ohne ``[netz]`` im Dienst gibt ``sim`` das Ereignis selbst aus (Mac-Prototyp ohne Zusätze)."""
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        proc = starte_dienst(welt)
        try:
            await dienst_bereit(welt, fr)
            assert (await sim(welt, "net", "home"))[0] == 0
            await warte(lambda: _netz_ist(welt, "home"), 10.0, "(Netz home)")
        finally:
            beende(proc)
