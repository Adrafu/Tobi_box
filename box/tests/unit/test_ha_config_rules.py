"""Revisionsregel für ``tobibox/config`` (``mqtt-v1.md`` 5.2; Design „Revisionsregel“).

Neue Listen-ID gewinnt, höhere Revision bei gleicher Listen-ID gewinnt, alles andere wird abgelehnt und gemeldet.
Geprüft wird mit ``store.validiere_konfig`` (über ``KonfigStore.annehmen``), nicht mit einer eigenen Prüfung.
"""

from __future__ import annotations

import json

import pytest
from fixtures.ha_fake import LISTE_A, LISTE_B, UID, Aufbau, als_bytes, konfig_json

from tobibox import events as ev

CONFIG = "tobibox/config"


@pytest.fixture
async def box(tmp_path):
    a = await Aufbau(tmp_path / "zustand").start()
    yield a
    await a.stop()


def abgelehnt(box: Aufbau) -> list[dict]:
    return [e for e in box.klient.json_auf("tobibox/box1/event") if e["art"] == "liste_abgelehnt"]


async def test_erste_liste_wird_angenommen(box):
    await box.sende(CONFIG, konfig_json(revision=1))
    (geladen,) = box.typen(ev.KonfigGeladen)
    assert (geladen.konfig.revision, geladen.konfig.liste_id) == (1, LISTE_A)
    assert (box.verz / "config.json").exists()  # auf der Platte, nicht nur im Speicher
    assert box.store.konfig.zuordnungen[UID].folge == "folge-03.mp3"
    assert abgelehnt(box) == []


async def test_hoehere_revision_gleiche_liste_gewinnt(box):
    await box.sende(CONFIG, konfig_json(revision=5))
    await box.sende(CONFIG, konfig_json(revision=6))
    assert [e.konfig.revision for e in box.typen(ev.KonfigGeladen)] == [5, 6]
    assert abgelehnt(box) == []


async def test_gleiche_revision_gleiche_liste_tut_nichts_und_meldet_nichts(box):
    """Die dauerhafte Nachricht kommt bei jedem Verbinden erneut (5.2)."""
    await box.sende(CONFIG, konfig_json(revision=5))
    await box.sende(CONFIG, konfig_json(revision=5))
    assert len(box.typen(ev.KonfigGeladen)) == 1
    assert abgelehnt(box) == []


async def test_niedrigere_revision_gleiche_liste_wird_abgelehnt_und_gemeldet(box):
    await box.sende(CONFIG, konfig_json(revision=17))
    await box.sende(CONFIG, konfig_json(revision=12))
    assert box.store.konfig.revision == 17  # die Kopie der Box bleibt
    assert len(box.typen(ev.KonfigGeladen)) == 1
    (m,) = abgelehnt(box)
    assert m["v"] == 1 and m["id"] and m["ts"]
    assert m["daten"] == {
        "liste_id": LISTE_A, "revision": 12, "gespeichert_liste_id": LISTE_A, "gespeichert_revision": 17,
        "grund": "revision_zu_niedrig",
    }


async def test_neue_liste_id_gewinnt_auch_bei_niedrigerer_revision(box):
    """HA-Wiederherstellung oder „Liste neu ausrollen“ (5.3)."""
    await box.sende(CONFIG, konfig_json(revision=17, liste_id=LISTE_A))
    await box.sende(CONFIG, konfig_json(revision=1, liste_id=LISTE_B))
    assert [(e.konfig.revision, e.konfig.liste_id) for e in box.typen(ev.KonfigGeladen)] == [(17, LISTE_A), (1, LISTE_B)]
    assert abgelehnt(box) == []
    # und danach gilt die Regel für die neue Liste
    await box.sende(CONFIG, konfig_json(revision=1, liste_id=LISTE_A))  # alte Liste, neue ID für die Box: wieder „neu“
    assert box.store.konfig.liste_id == LISTE_A


async def test_alte_sicherung_mit_alter_liste_id_wird_abgelehnt(box):
    """Wird HA aus einer Sicherung mit der alten Listen-ID wiederhergestellt, hilft nur „Liste neu ausrollen“ (5.3)."""
    await box.sende(CONFIG, konfig_json(revision=17))
    await box.sende(CONFIG, konfig_json(revision=3))
    assert [m["daten"]["grund"] for m in abgelehnt(box)] == ["revision_zu_niedrig"]


@pytest.mark.parametrize(
    "roh",
    [
        konfig_json(revision=0),  # Revision muss ab 1 sein
        konfig_json(liste_id="zu-kurz"),
        konfig_json(zuordnungen={"keine-kennung": {"ziel": {"typ": "serie", "serie": "s"}}}),
        konfig_json(zuordnungen={UID: {"ziel": {"typ": "aktion", "aktion": "unsinn"}}}),
        konfig_json(gute_nacht="kaputt"),
        {"revision": 3, "liste_id": LISTE_A},  # schema_version fehlt
        {"schema_version": 2},
    ],
)
async def test_ungueltiges_schema_wird_abgelehnt(box, roh):
    await box.sende(CONFIG, roh)
    assert box.typen(ev.KonfigGeladen) == []
    (m,) = abgelehnt(box)
    assert m["daten"]["grund"] == "schema_ungueltig"
    assert m["daten"]["gespeichert_revision"] == 0 and m["daten"]["gespeichert_liste_id"] == ""
    assert not (box.verz / "config.json").exists()  # nichts Halbes auf der Platte


@pytest.mark.parametrize("nutzlast", [b"das ist kein json", b"[1, 2]", b'"text"', b"\xff\xfe"])
async def test_nutzlast_ohne_objekt_wird_abgelehnt(box, nutzlast):
    await box.sende(CONFIG, nutzlast)
    (m,) = abgelehnt(box)
    assert m["daten"]["grund"] == "schema_ungueltig" and m["daten"]["liste_id"] == "" and m["daten"]["revision"] == 0


async def test_zu_grosse_liste_wird_abgelehnt(box):
    roh = konfig_json()
    roh["zuordnungen"]["x"] = "a" * (256 * 1024)
    await box.sende(CONFIG, als_bytes(roh))
    assert [m["daten"]["grund"] for m in abgelehnt(box)] == ["schema_ungueltig"]


async def test_schema_zu_neu_wird_abgelehnt(box):
    await box.sende(CONFIG, konfig_json(revision=2))
    await box.sende(CONFIG, konfig_json(revision=3, schema_version=3))
    (m,) = abgelehnt(box)
    assert m["daten"]["grund"] == "schema_zu_neu" and m["daten"]["revision"] == 3
    assert box.store.konfig.revision == 2


async def test_liste_der_version_1_wird_migriert_und_als_version_2_gespeichert(box):
    roh = konfig_json(revision=4, schema_version=1)
    roh["zuordnungen"] = {UID: {"typ": "serie", "serie": "3f9a1c07b2d4"}}  # Version 1: ohne ``ziel``
    await box.sende(CONFIG, roh)
    (geladen,) = box.typen(ev.KonfigGeladen)
    assert geladen.konfig.zuordnungen[UID] == ev.Zuordnung("serie", "3f9a1c07b2d4")
    gespeichert = json.loads((box.verz / "config.json").read_text())
    assert gespeichert["schema_version"] == 2
    assert gespeichert["zuordnungen"][UID] == {"ziel": {"typ": "serie", "serie": "3f9a1c07b2d4"}}


async def test_dieselbe_abgelehnte_liste_wird_nur_einmal_gemeldet(box):
    """Die dauerhafte Nachricht kommt bei jedem Verbinden wieder; HA soll nicht jedes Mal benachrichtigen."""
    await box.sende(CONFIG, konfig_json(revision=17))
    for _ in range(3):
        await box.sende(CONFIG, konfig_json(revision=12))
    assert len(abgelehnt(box)) == 1
    await box.sende(CONFIG, konfig_json(revision=11))  # eine andere abgelehnte Fassung: neue Meldung
    assert len(abgelehnt(box)) == 2


async def test_leere_nachricht_aendert_nichts(box):
    """HA löscht die dauerhafte Nachricht: die Box behält ihre letzte Kopie (4.3, Punkt 5)."""
    await box.sende(CONFIG, konfig_json(revision=2))
    await box.sende(CONFIG, b"")
    assert box.store.konfig.revision == 2 and abgelehnt(box) == []


async def test_neustart_der_box_behaelt_die_gespeicherte_revision(tmp_path):
    verz = tmp_path / "zustand"
    a = await Aufbau(verz).start()
    await a.sende(CONFIG, konfig_json(revision=9))
    await a.stop()
    b = await Aufbau(verz).start()  # neuer Dienst, gleiche Platte
    assert b.store.konfig.revision == 9
    await b.sende(CONFIG, konfig_json(revision=9))  # dieselbe dauerhafte Nachricht: still
    await b.sende(CONFIG, konfig_json(revision=8))
    assert [m["daten"]["grund"] for m in abgelehnt(b)] == ["revision_zu_niedrig"]
    await b.stop()
