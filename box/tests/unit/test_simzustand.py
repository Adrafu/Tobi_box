"""Sim-Werte über den Neustart (Mac-Test 12.11.): ``simzustand`` und die Verdrahtung in ``App``."""

from __future__ import annotations

import json
import logging

import pytest
from fixtures.dienst import BEKANNT, baue_dienst, netz_strom_abschnitt

from tobibox import simzustand
from tobibox.simzustand import SimWerte

# -- Modul ---------------------------------------------------------------------------------------------------------


def test_schreiben_und_lesen(tmp_path):
    w = SimWerte(pisugar=True, leser=False, akku=42, netz="home")
    simzustand.speichere(tmp_path, w)
    assert simzustand.lade(tmp_path) == w
    roh = json.loads((tmp_path / "sim_zustand.json").read_text(encoding="utf-8"))
    assert roh["strom"] == {"pisugar": True, "leser": False} and roh["akku"] == 42 and roh["netz"] == "home"
    assert not list(tmp_path.glob("*.tmp"))


def test_fehlende_datei_ist_leer_und_ohne_warnung(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        assert simzustand.lade(tmp_path) == SimWerte()
    assert not caplog.records


@pytest.mark.parametrize(
    "inhalt",
    [b"{kaputt", b"[]", b'{"akku": 5}', b'{"strom": {"pisugar": 1}}', b'{"strom": {}, "akku": 101}',
     b'{"strom": {}, "akku": true}', b'{"strom": {}, "netz": "mars"}', b"\xff\xfe"],
)
def test_kaputte_datei_ist_leer_mit_warnung(tmp_path, inhalt, monkeypatch):
    gelogt = []
    monkeypatch.setattr(simzustand, "logge", lambda *a, **kw: gelogt.append(a))
    (tmp_path / "sim_zustand.json").write_bytes(inhalt)
    assert simzustand.lade(tmp_path) == SimWerte()
    assert gelogt and gelogt[0][1] == "WARNING" and gelogt[0][3] == "kaputt"


# -- App -----------------------------------------------------------------------------------------------------------


async def _lauf(d, *, vorher=None):
    await d.app.starte()
    try:
        if vorher:
            await vorher(d)
    finally:
        await d.app.beende()


@pytest.mark.asyncio
async def test_werte_bleiben_ueber_den_neustart(tmp_path, kurz, monkeypatch):
    d = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt())

    async def setzen(d):
        await d.sim(befehl="strom", lader=True, akku=64)
        await d.sim(befehl="strom", lader=False, quelle="leser")
        await d.sim(befehl="netz", klasse="hotspot")

    await _lauf(d, vorher=setzen)
    gespeichert = json.loads((d.zustand / "sim_zustand.json").read_text(encoding="utf-8"))
    assert gespeichert["strom"] == {"pisugar": True, "leser": False} and gespeichert["akku"] == 64 and gespeichert["netz"] == "hotspot"

    d.neustart()
    a = d.app
    # schon vor dem Start stehen die Werte in den Sim-Treibern
    assert (a.power.treiber._lader, a.power.treiber._akku) == (True, 64)
    assert await a.netz._ssid.ssid() == a.netz.konfig.hotspot_ssid
    await a.starte()
    try:
        await d.warte(lambda: (a.status.akku, a.status.netz) == (64, "hotspot"), text="Akku und Netz wiederhergestellt")
        await d.ruhe()
        assert a.status.lader is False  # bei Widerspruch gilt der Leser
        assert a.kern.session.strom.pisugar is True and a.kern.session.strom.leser is False
        # erste Messung: weder Ring-Anzeige „andocken“ noch Lader-Ton
        assert "lader" not in d.toene
        assert "AkkuAnzeigen" not in a.gesehen
        # Sync-Regel kennt Netz und Akku sofort
        assert a.sync is None or (a.sync._netz == "hotspot" and a.sync._akku == 64)
    finally:
        await a.beende()


@pytest.mark.asyncio
async def test_sim_werte_werden_ueber_mehrere_neustarts_fortgeschrieben(tmp_path, kurz, monkeypatch):
    d = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt())
    await _lauf(d, vorher=lambda d: d.sim(befehl="strom", lader=True, akku=80))
    d.neustart()
    await _lauf(d, vorher=lambda d: d.sim(befehl="netz", klasse="home"))
    d.neustart()
    await d.app.starte()
    try:
        a = d.app
        await d.warte(lambda: (a.status.lader, a.status.akku, a.status.netz) == (True, 80, "home"), text="alle Werte wiederhergestellt")
    finally:
        await d.app.beende()


@pytest.mark.asyncio
async def test_ohne_datei_bleibt_alles_unbekannt(tmp_path, kurz, monkeypatch):
    d = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt())
    await d.app.starte()
    try:
        await d.ruhe()
        a = d.app
        assert (a.status.lader, a.status.akku, a.status.netz) == (None, None, "offline") or a.status.lader is None
        assert a.status.akku is None
        assert not (d.zustand / "sim_zustand.json").exists()  # geschrieben wird erst, wenn jemand etwas setzt
        assert a.sim.leser_strom_haken is not None
    finally:
        await d.app.beende()


@pytest.mark.asyncio
async def test_kaputte_datei_verhaelt_sich_wie_ohne_datei(tmp_path, kurz, monkeypatch):
    d = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt())
    (d.zustand / "sim_zustand.json").write_text("{kaputt", encoding="utf-8")
    gelogt = []
    monkeypatch.setattr(simzustand, "logge", lambda *a, **kw: gelogt.append(a))
    d.neustart()
    await d.app.starte()
    try:
        await d.ruhe()
        assert d.app.status.lader is None and d.app.status.akku is None
        assert any(g[1] == "WARNING" for g in gelogt)
        await d.sim(befehl="strom", akku=10)  # überschreibt die kaputte Datei
        assert simzustand.lade(d.zustand).akku == 10
    finally:
        await d.app.beende()


@pytest.mark.asyncio
async def test_ohne_sim_quellen_wird_nichts_gelesen_oder_geschrieben(tmp_path, kurz, monkeypatch):
    """Echte Treiber nie: ``[strom]``/``[netz]`` mit echter Quelle lesen die Datei nicht und der Treiber bleibt unberührt."""
    abschnitte = '[netz]\nquelle = "networkmanager"\nheim_ssid = "x"\n[strom]\nquelle = "pisugar"\n'
    d = baue_dienst(tmp_path, kurz, monkeypatch, abschnitte)
    simzustand.speichere(d.zustand, SimWerte(pisugar=True, leser=True, akku=50, netz="home"))
    d.neustart()
    a = d.app
    assert a._sim_werte == SimWerte(leser=True)  # nur der simulierte Leser (hier ``sim``) darf wiederherstellen
    assert not hasattr(a.power.treiber, "_lader")
    assert a.sim.strom_haken is None and a.sim.netz_haken is None


@pytest.mark.asyncio
async def test_start_durch_strom_hw8_mit_wiederhergestelltem_strom(tmp_path, kurz, monkeypatch):
    """HW8: Mit gemerktem Strom bleibt der beim Start liegende Tobie still (``Bereit.strom_warten``); ohne Datei spielt er wie bisher."""
    d = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt())
    await _lauf(d, vorher=lambda d: d.sim(befehl="strom", lader=True, akku=90))
    d.neustart()
    await d.app.starte()
    try:
        await d.auflegen(BEKANNT)
        await d.ruhe()
        assert d.abgespielt() == [] and "lader" not in d.toene, "Start mit Strom: der Tobie bleibt still"
        assert d.app.kern.session.strom_warten is True
    finally:
        await d.app.beende()


@pytest.mark.asyncio
async def test_start_ohne_gemerkten_strom_spielt_der_tobie_wie_bisher(tmp_path, kurz, monkeypatch):
    d = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt())
    await d.app.starte()
    try:
        await d.auflegen(BEKANNT)
        await d.ruhe()
        assert d.abgespielt() != [] and d.app.kern.session.strom_warten is False
    finally:
        await d.app.beende()


@pytest.mark.asyncio
async def test_start_durch_strom_hw8_mit_gemerktem_leser_strom(tmp_path, kurz, monkeypatch):
    d = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt())
    await _lauf(d, vorher=lambda d: d.sim(befehl="strom", lader=True, quelle="leser"))
    d.neustart()
    await d.app.starte()
    try:
        await d.auflegen(BEKANNT)
        await d.ruhe()
        assert d.abgespielt() == [] and "lader" not in d.toene
        assert d.app.kern.session.strom.leser is True
    finally:
        await d.app.beende()
