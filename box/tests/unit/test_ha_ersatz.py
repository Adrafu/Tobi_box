"""HA-Ersatz (Stufe 2): schreibt die Zuordnung nach dem Lernen und bestätigt wie HA (``mqtt-v1.md``, 4.2)."""

from __future__ import annotations

import asyncio
import logging
import os
import time

import pytest

from tobibox import events as ev
from tobibox import store
from tobibox.ha_ersatz import LISTE_ID_STUFE_2, Abgelehnt, HaErsatz, schreibe_zuordnung

UID = "04ffeedd"
ZUERST = "2026-11-07T09:12:03.412Z"


class FakeSim:
    def __init__(self, ziel=None, befehl_id=None, ueberschreiben=False) -> None:
        self.lernziel = ziel
        self.lernbefehl_id = befehl_id
        self.ueberschreiben = ueberschreiben


def eintrag(uid=UID, befehl_id="b1", zuletzt=ZUERST):
    return ev.Eintrag(uid, "gelernt", ZUERST, zuletzt, 1, True, befehl_id)


@pytest.fixture
def ks(tmp_path):
    return store.KonfigStore(tmp_path)


def baue(ks, **kw):
    aus: list = []
    sim = FakeSim(**kw)
    return HaErsatz(sim, ks, aus.append), sim, aus


def test_schreibe_zuordnung_ohne_vorherige_datei_setzt_liste_und_revision_1(ks):
    g = schreibe_zuordnung(ks, UID, {"typ": "serie", "serie": "s1"})
    assert g.konfig.revision == 1 and g.konfig.liste_id == LISTE_ID_STUFE_2
    assert g.konfig.zuordnungen[UID] == ev.Zuordnung("serie", "s1")


def test_schreibe_zuordnung_erhoeht_die_revision_und_behaelt_die_anderen(ks):
    schreibe_zuordnung(ks, "04a1b2c3", {"typ": "serie", "serie": "s1"})
    g = schreibe_zuordnung(ks, UID, {"typ": "folge", "serie": "s1", "folge": "a.mp3"})
    assert g.konfig.revision == 2 and set(g.konfig.zuordnungen) == {"04a1b2c3", UID}
    assert g.konfig.zuordnungen[UID] == ev.Zuordnung("folge", "s1", "a.mp3")


def test_schreibe_zuordnung_liest_die_datei_neu_ein(ks, tmp_path):
    """Eine Änderung von außen (anderer Prozess) geht nicht verloren."""
    schreibe_zuordnung(ks, "04a1b2c3", {"typ": "serie", "serie": "s1"})
    anderer = store.KonfigStore(tmp_path)
    schreibe_zuordnung(anderer, "04a1b2c4", {"typ": "serie", "serie": "s2"})
    g = schreibe_zuordnung(ks, UID, {"typ": "serie", "serie": "s1"})
    assert g.konfig.revision == 3 and "04a1b2c4" in g.konfig.zuordnungen


def test_schreibe_zuordnung_ungueltige_kennung_wird_abgelehnt(ks):
    with pytest.raises(Abgelehnt):
        schreibe_zuordnung(ks, "keine-uid", {"typ": "serie", "serie": "s1"})
    assert not ks.pfad.exists()


def test_gelernt_schreibt_gibt_konfig_geladen_und_bestaetigt_zugeordnet(ks):
    ha, sim, aus = baue(ks, ziel={"typ": "serie", "serie": "s1"}, befehl_id="b1")
    ha.gelernt(eintrag())
    assert [type(e) for e in aus] == [ev.KonfigGeladen, ev.Bestaetigt]  # erst die Liste, dann die Bestätigung
    assert aus[0].konfig.zuordnungen[UID] == ev.Zuordnung("serie", "s1") and aus[0].konfig.revision == 1
    assert aus[1] == ev.Bestaetigt(UID, "zugeordnet", ZUERST, "gelernt")
    assert sim.lernziel is None  # das Ziel gilt für genau einen Lernlauf


def test_gelernt_ziel_folge(ks):
    ha, _, aus = baue(ks, ziel={"typ": "folge", "serie": "s1", "folge": "b.mp3"}, befehl_id="b1")
    ha.gelernt(eintrag())
    assert aus[0].konfig.zuordnungen[UID] == ev.Zuordnung("folge", "s1", "b.mp3")


def test_bestaetigung_traegt_zuletzt_der_meldung(ks):
    ha, _, aus = baue(ks, ziel={"typ": "serie", "serie": "s1"}, befehl_id="b1")
    ha.gelernt(eintrag(zuletzt="2026-11-07T09:12:09.001Z"))
    assert aus[-1].zuletzt == "2026-11-07T09:12:09.001Z" and aus[-1].art == "gelernt"


@pytest.mark.parametrize(
    "ziel, sim_id, eintrag_id",
    [
        (None, None, "b1"),  # kein Lernziel
        ({"typ": "serie", "serie": "s1"}, "b2", "b1"),  # Eintrag gehört zu einem anderen Lernbefehl
        ({"typ": "serie", "serie": "s1"}, "b1", None),  # Eintrag ohne Befehls-ID
    ],
)
def test_ohne_passendes_ziel_wird_nichts_geschrieben_und_abgelehnt(ks, ziel, sim_id, eintrag_id):
    ha, _, aus = baue(ks, ziel=ziel, befehl_id=sim_id)
    ha.gelernt(eintrag(befehl_id=eintrag_id))
    assert aus == [ev.Bestaetigt(UID, "abgelehnt", ZUERST, "gelernt")]
    assert not ks.pfad.exists()


def test_ungueltige_kennung_wird_abgelehnt(ks):
    ha, _, aus = baue(ks, ziel={"typ": "serie", "serie": "s1"}, befehl_id="b1")
    ha.gelernt(eintrag(uid="keine-uid"))
    assert aus == [ev.Bestaetigt("keine-uid", "abgelehnt", ZUERST, "gelernt")]


# --- schon zugeordnet: nur mit ``--ueberschreiben`` -----------------------------------------------


def test_schon_zugeordnete_kennung_wird_ohne_ueberschreiben_abgelehnt_und_bleibt(ks, caplog):
    schreibe_zuordnung(ks, UID, {"typ": "serie", "serie": "alt"})
    ha, sim, aus = baue(ks, ziel={"typ": "serie", "serie": "s1"}, befehl_id="b1")
    with caplog.at_level(logging.WARNING, logger="tobibox"):
        ha.gelernt(eintrag())
    assert aus == [ev.Bestaetigt(UID, "abgelehnt", ZUERST, "gelernt")]
    assert ks.konfig.revision == 1 and ks.konfig.zuordnungen[UID] == ev.Zuordnung("serie", "alt")
    (r,) = [r for r in caplog.records if getattr(r, "ereignis", "") == "zuordnung"]
    assert "--ueberschreiben" in r.meldung and UID in r.meldung and r.sim is True
    assert sim.lernziel is None  # der Lernlauf ist zu Ende


def test_schon_zugeordnete_kennung_wird_mit_ueberschreiben_ersetzt(ks):
    schreibe_zuordnung(ks, UID, {"typ": "serie", "serie": "alt"})
    ha, _, aus = baue(ks, ziel={"typ": "serie", "serie": "s1"}, befehl_id="b1", ueberschreiben=True)
    ha.gelernt(eintrag())
    assert [type(e) for e in aus] == [ev.KonfigGeladen, ev.Bestaetigt] and aus[1].grund == "zugeordnet"
    assert ks.konfig.zuordnungen[UID] == ev.Zuordnung("serie", "s1") and ks.konfig.revision == 2


async def test_gelernt_async_schreibt_und_bestaetigt_wie_gelernt(ks):
    ha, sim, aus = baue(ks, ziel={"typ": "serie", "serie": "s1"}, befehl_id="b1")
    await ha.gelernt_async(eintrag())
    assert [type(e) for e in aus] == [ev.KonfigGeladen, ev.Bestaetigt] and sim.lernziel is None


async def test_zwei_zuordnungen_gleichzeitig_in_threads_gehen_nicht_verloren(ks):
    await asyncio.gather(
        asyncio.to_thread(schreibe_zuordnung, ks, "04a1b2c3", {"typ": "serie", "serie": "s1"}),
        asyncio.to_thread(schreibe_zuordnung, ks, "04a1b2c4", {"typ": "serie", "serie": "s2"}),
    )
    assert ks.konfig.revision == 2 and set(ks.konfig.zuordnungen) == {"04a1b2c3", "04a1b2c4"}


# --- Befund 1: Aufräumen darf kein laufendes Zeiger-Schreiben treffen ------------------------------


async def test_zuordnung_waehrend_eines_laufenden_zeiger_schreibens_loescht_dessen_temp_datei_nicht(ks, tmp_path, monkeypatch):
    """Ein Thread schreibt ``resume.json`` (``fsync`` dauert auf der SD-Karte); ``schreibe_zuordnung`` läuft dazwischen."""
    orig = os.fsync

    def langsam(fd):
        time.sleep(0.3)
        return orig(fd)

    monkeypatch.setattr(store.os, "fsync", langsam)
    schreiben = asyncio.create_task(asyncio.to_thread(store.schreibe_atomar, tmp_path / "resume.json", {"schema_version": 1}))
    await asyncio.sleep(0.1)  # der Thread steht im ``fsync``, die Temp-Datei existiert
    assert (tmp_path / "resume.json.tmp").exists()
    schreibe_zuordnung(ks, UID, {"typ": "serie", "serie": "s1"})  # ruft ``KonfigStore.laden()``
    await schreiben  # wirft ``FileNotFoundError``, wenn jemand die Temp-Datei gelöscht hat
    assert (tmp_path / "resume.json").exists()
