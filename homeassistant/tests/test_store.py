"""Revision und Listen-ID, Veröffentlichen vor Exportieren, Export auf das NAS (Vertrag W, Abschnitt 1 und 13.5)."""

from __future__ import annotations

import json
import re

import pytest

from custom_components.tobibox import hub as hub_modul
from custom_components.tobibox.const import KONFIG_MAX_BYTES, RE_LISTE_ID
from custom_components.tobibox.fehler import TobiboxFehler
from custom_components.tobibox.store import (
    TobiboxStore,
    Ungueltig,
    konfig_zu_mqtt,
    neue_konfig,
    pruefe_konfig,
)

from .conftest import warte_auf

UID1 = "e0040312345678ab"
UID2 = "04a1b2c3"
SERIE = {"typ": "serie", "serie": "rabe"}


async def test_erststart_legt_liste_an_und_veroeffentlicht(hass, integration, box_fabrik, nas):
    hub = integration
    k = hub.store.konfig
    assert hub.store.zustand == "ok"
    assert k["revision"] == 1
    assert RE_LISTE_ID.match(k["liste_id"])
    assert k["zuordnungen"] == {}
    assert k["leise_zeiten"] == {"zeitzone": "Europe/Berlin", "fenster": []}
    assert k["gute_nacht"] == {"timer_min": 30, "ausblenden_s": 60}
    assert k["lesezeichen_tage"] == 14  # Entscheidung N: Vorgabe 14, ohne eigene Bedienung
    box = box_fabrik("box1")
    veroeffentlicht = [e for e in box.veroeffentlicht() if e[0] == "tobibox/config"]
    assert len(veroeffentlicht) == 1
    _thema, nutzlast, qos, retain = veroeffentlicht[0]
    assert (qos, retain) == (1, True)
    msg = json.loads(nutzlast)
    assert msg["schema_version"] == 2
    assert msg["revision"] == 1
    assert msg["liste_id"] == k["liste_id"]
    assert msg["lesezeichen_tage"] == 14
    assert hub.store.veroeffentlicht_stand == [k["liste_id"], 1]
    await warte_auf(hass, lambda: hub.export_ok)
    export = json.loads((nas.export / "config.json").read_text())
    assert export["liste_id"] == k["liste_id"]
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", export["exportiert_am"])


async def test_aenderung_erhoeht_revision_und_behaelt_einstellungen(hass, integration, box_fabrik, nas):
    hub = integration
    nas.serie("rabe", "rabe", "Der kleine Rabe")
    await hub.medien.pruefen()
    liste_id = hub.store.konfig["liste_id"]
    erg = await hub.zuordnung_setzen(UID1, SERIE, name="Rabe aus Holz")
    assert erg["geaendert"] is True
    assert erg["veroeffentlicht"] is True
    assert erg["konfig"]["revision"] == 2
    assert hub.store.konfig["liste_id"] == liste_id  # gleiche Listen-ID, Revision + 1
    msg = box_fabrik("box1").konfigs()[-1]
    assert msg["revision"] == 2
    assert msg["zuordnungen"][UID1] == {"ziel": SERIE, "name": "Rabe aus Holz"}
    assert msg["leise_zeiten"]["zeitzone"] == "Europe/Berlin"
    assert msg["gute_nacht"] == {"timer_min": 30, "ausblenden_s": 60}


async def test_gleiche_zuordnung_aendert_nichts(hass, integration, box_fabrik, nas):
    hub = integration
    nas.serie("rabe", "rabe", "Der kleine Rabe")
    await hub.medien.pruefen()
    await hub.zuordnung_setzen(UID1, SERIE, name="Rabe")
    anzahl = len(box_fabrik("box1").konfigs())
    erg = await hub.zuordnung_setzen(UID1, SERIE, name="Rabe")
    assert erg["geaendert"] is False
    assert erg["veroeffentlicht"] is None
    assert erg["konfig"]["revision"] == 2
    erg = await hub.zuordnung_setzen(UID1, SERIE)  # ohne ``name``: der vorhandene Name bleibt
    assert erg["geaendert"] is False
    assert len(box_fabrik("box1").konfigs()) == anzahl


async def test_erst_veroeffentlichen_dann_exportieren(hass, integration, box_fabrik, nas, monkeypatch):
    hub = integration
    nas.serie("rabe", "rabe", "Der kleine Rabe")
    await hub.medien.pruefen()
    await warte_auf(hass, lambda: hub.export_ok)
    box = box_fabrik("box1")
    gesehen: list[tuple[int, int]] = []
    echt = hub_modul.schreibe_export

    def beobachte(ordner, konfig, am):
        veroeffentlicht = [json.loads(n)["revision"] for t, n, *_ in box.veroeffentlicht() if t == "tobibox/config"]
        gesehen.append((konfig["revision"], max(veroeffentlicht)))
        return echt(ordner, konfig, am)

    monkeypatch.setattr(hub_modul, "schreibe_export", beobachte)
    await hub.zuordnung_setzen(UID1, SERIE)
    await warte_auf(hass, lambda: hub.export_ok)
    assert gesehen, "der Export lief nicht"
    revision, veroeffentlicht = gesehen[-1]
    assert revision == 2
    assert veroeffentlicht >= revision  # beim Schreiben des Exports war die Revision schon veröffentlicht


async def test_export_enthaelt_namen_und_alle_einstellungen(hass, integration, nas):
    hub = integration
    nas.serie("rabe", "rabe", "Der kleine Rabe")
    await hub.medien.pruefen()
    await hub.zuordnung_setzen(UID1, SERIE, name="Rabe aus Holz")
    await hub.zuordnung_setzen(UID2, {"typ": "aktion", "aktion": "status"})
    await warte_auf(hass, lambda: hub.export_ok)
    export = json.loads((nas.export / "config.json").read_text())
    assert export["schema_version"] == 2
    assert export["revision"] == 3
    assert export["zuordnungen"][UID1]["name"] == "Rabe aus Holz"
    assert export["zuordnungen"][UID2] == {"ziel": {"typ": "aktion", "aktion": "status"}}
    assert export["leise_zeiten"]["fenster"] == []
    assert export["lesezeichen_tage"] == 14
    assert list(export)[0] == "schema_version"  # data-model.md 1.1: schema_version als erstes Feld
    assert not list(nas.export.glob("*.tmp"))  # atomar: keine Reste


async def test_konfig_zu_gross(hass, integration, nas):
    hub = integration
    nas.serie("rabe", "rabe", "Der kleine Rabe")
    await hub.medien.pruefen()
    zuordnungen = hub.store.konfig["zuordnungen"]
    i = 0
    while len(json.dumps(konfig_zu_mqtt(hub.store.konfig)).encode()) < KONFIG_MAX_BYTES - 300:
        zuordnungen[f"{i:016x}"] = {"ziel": {"typ": "serie", "serie": "rabe"}, "name": "N" * 40}
        i += 1
    assert len(json.dumps(konfig_zu_mqtt(hub.store.konfig)).encode()) < KONFIG_MAX_BYTES
    revision = hub.store.konfig["revision"]
    with pytest.raises(TobiboxFehler) as err:
        for n in range(10):  # spätestens der dritte Eintrag sprengt die Grenze
            await hub.zuordnung_setzen(f"ffffffffffffff{n:02x}", SERIE, name="N" * 60)
    assert err.value.code == "konfig_zu_gross"
    assert hub.store.konfig["revision"] <= revision + 3
    assert len(json.dumps(konfig_zu_mqtt(hub.store.konfig)).encode()) <= KONFIG_MAX_BYTES  # nie größer gespeichert


def test_pruefe_konfig_gueltig_und_migration_v1():
    k = pruefe_konfig(
        {
            "schema_version": 1,
            "revision": 3,
            "liste_id": "a3f9c1e07b2d4856",
            "zuordnungen": {UID1: {"typ": "serie", "serie": "rabe"}},
            "leise_zeiten": {"fenster": []},
            "gute_nacht": {"timer_min": 30, "ausblenden_s": 60},
        }
    )
    assert k["zuordnungen"][UID1] == {"ziel": {"typ": "serie", "serie": "rabe"}}
    assert k["leise_zeiten"]["zeitzone"] == "Europe/Berlin"
    assert k["lesezeichen_tage"] == 14


@pytest.mark.parametrize(
    "aenderung",
    [
        {"schema_version": 3},
        {"revision": 0},
        {"liste_id": "XYZ"},
        {"zuordnungen": []},
        {"zuordnungen": {"ABC": {"ziel": {"typ": "serie", "serie": "x"}}}},
        {"zuordnungen": {UID1: {"ziel": {"typ": "folge", "serie": "x"}}}},
        {"zuordnungen": {UID1: {"ziel": {"typ": "aktion", "aktion": "unbekannt"}}}},
        {"zuordnungen": {UID1: {"ziel": {"typ": "tobie"}}}},
        {"zuordnungen": {UID1: {"ziel": {"typ": "serie", "serie": "x"}, "name": ""}}},
        {"zuordnungen": {UID1: {"ziel": {"typ": "serie", "serie": "x"}, "name": "x" * 61}}},
        {"leise_zeiten": {"zeitzone": "Mars/Olympus", "fenster": []}},
        {"leise_zeiten": {"fenster": [{"id": "a", "tage": [1], "von": "10:00", "bis": "10:00", "wirkung": "stumm"}]}},
        {"leise_zeiten": {"fenster": [{"id": "a", "tage": [8], "von": "10:00", "bis": "11:00", "wirkung": "stumm"}]}},
        {"leise_zeiten": {"fenster": [{"id": "a", "tage": [1], "von": "10:00", "bis": "11:00", "wirkung": "leiser"}]}},
        {"gute_nacht": {"timer_min": 0, "ausblenden_s": 60}},
        {"gute_nacht": {"timer_min": 30, "ausblenden_s": 4}},
        {"hinweis_pegel": 101},
        {"lesezeichen_tage": -1},
        {"lesezeichen_tage": 366},
        {"lesezeichen_tage": True},
    ],
)
def test_pruefe_konfig_ungueltig(aenderung):
    basis = {
        "schema_version": 2,
        "revision": 3,
        "liste_id": "a3f9c1e07b2d4856",
        "zuordnungen": {},
        "leise_zeiten": {"zeitzone": "Europe/Berlin", "fenster": []},
        "gute_nacht": {"timer_min": 30, "ausblenden_s": 60},
    }
    pruefe_konfig(basis)
    with pytest.raises(Ungueltig):
        pruefe_konfig({**basis, **aenderung})


def test_pruefe_konfig_lesezeichen_tage_grenzen():
    basis = neue_konfig()
    for tage in (0, 14, 365):
        k = pruefe_konfig({"schema_version": 2, **basis, "lesezeichen_tage": tage})
        assert k["lesezeichen_tage"] == tage


async def test_neue_tobies_zaehlen_je_box_ersetzen_nicht_addieren(hass, integration, box_fabrik):
    hub = integration
    b1, b2 = box_fabrik("box1"), box_fabrik("box2")
    await b1.unbekannt(UID1, anzahl=2, zuletzt="2026-11-09T10:00:01.100Z", zuerst="2026-11-09T09:00:00Z")
    await b1.unbekannt(UID1, anzahl=3, zuletzt="2026-11-09T10:00:05.200Z", zuerst="2026-11-09T09:00:00Z")
    await b2.unbekannt(UID1, anzahl=4, zuletzt="2026-11-09T10:00:03.000Z", zuerst="2026-11-09T09:30:00Z")
    eintrag = hub.store.neue_tobies[UID1]
    assert eintrag["anzahl"] == 3 + 4  # je Box die letzte Nachricht, nie bei jeder Nachricht addiert
    assert eintrag["zuerst"] == "2026-11-09T09:00:00Z"
    assert eintrag["zuletzt"] == "2026-11-09T10:00:05.200Z"
    assert set(eintrag["boxen"]) == {"box1", "box2"}
    assert len(hub.store.neue_tobies) == 1  # gleiche Kennung = ein Eintrag


async def test_letzte_20_box_meldungen_im_speicher(hass, integration, box_fabrik, hass_storage):
    hub = integration
    box = box_fabrik("box1")
    for i in range(25):
        await box.ereignis("fehler", {"baustein": "update", "code": "x", "text": f"Fehler {i}"}, eid=f"id-{i:04d}")
    liste = hub.store.box_ereignisse["box1"]
    assert len(liste) == 20
    assert liste[0]["id"] == "id-0024"  # neueste zuerst
    assert liste[-1]["id"] == "id-0005"
    await hub.store.async_speichern()
    assert len(hass_storage["tobibox"]["data"]["box_ereignisse"]["box1"]) == 20


def test_store_klasse_ist_importierbar():
    assert TobiboxStore
