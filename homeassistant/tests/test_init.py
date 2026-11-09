"""Einrichtung: Seite über ``panel_custom``, statische Dateien, Upload-Ansicht, Entladen (Vertrag W, 2.1 und 9)."""

from __future__ import annotations

import logging

import pytest
from homeassistant.components import frontend
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tobibox import FRONTEND_PFAD
from custom_components.tobibox.const import DOMAIN


def panel(hass):
    return hass.data[frontend.DATA_PANELS].get("tobibox")


async def test_panel_nur_fuer_administratoren_mit_version_im_pfad(hass, integration):
    p = panel(hass)
    assert p is not None
    assert p.require_admin is True  # Vorgabe der Projektleitung 09.11.
    assert p.sidebar_title == "Tobi Box"
    assert p.frontend_url_path == "tobibox"
    assert p.component_name == "custom"
    cfg = p.config["_panel_custom"]
    assert cfg["name"] == "tobibox-panel"
    assert cfg["module_url"] == "/tobibox_static/tobibox-panel.js?v=0.1.0"  # die Adresse trägt die Version der Integration
    assert cfg["embed_iframe"] is False and cfg["trust_external"] is False


async def test_statische_dateien_sind_oeffentlich_und_ohne_geheimnisse(hass, integration, hass_client_no_auth, frontend_dir):
    client = await hass_client_no_auth()
    antwort = await client.get("/tobibox_static/tobibox-panel.js")
    assert antwort.status == 200
    assert "Attrappe" in await antwort.text()
    assert (await client.get("/tobibox_static/gibtsnicht.js")).status == 404


async def test_upload_ansicht_ist_registriert(hass, integration, hass_client_no_auth):
    client = await hass_client_no_auth()
    assert (await client.post("/api/tobibox/upload")).status == 401  # mit Anmeldungspflicht, nicht 404


async def test_ohne_seite_wird_nichts_registriert_aber_die_integration_laeuft(hass, mqtt_broker, hass_storage, enable_custom_integrations, nas, einrichtung_daten, monkeypatch, tmp_path, caplog):
    import custom_components.tobibox as paket

    monkeypatch.setattr(paket, "FRONTEND_PFAD", tmp_path / "gibtsnicht")
    entry = MockConfigEntry(domain=DOMAIN, data=einrichtung_daten, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    with caplog.at_level(logging.WARNING):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert panel(hass) is None
    assert "fehlt" in caplog.text
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_der_echte_ordner_der_seite_gehoert_dem_anderen_ap():
    """Der Ordner ``frontend/`` (AP 3.2) wird nur gelesen; ``__init__.py`` zeigt auf ``frontend/tobibox-panel.js``."""
    assert FRONTEND_PFAD.name == "frontend"
    assert FRONTEND_PFAD.parent.name == "tobibox"


async def test_entladen_und_neu_laden(hass, integration):
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert DOMAIN not in hass.data
    assert panel(hass) is None
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(DOMAIN, "loesen", {"uid": "e0040312345678ab"}, blocking=True)
    assert err.value.translation_key == "unknown_error"
    assert await hass.config_entries.async_setup(entry.entry_id)  # Seite und Dienste lassen sich ohne Fehler neu anmelden
    await hass.async_block_till_done()
    hub = hass.data[DOMAIN]
    await hub.start_fertig.wait()
    assert panel(hass) is not None
    if hub._start_task is not None:
        await hub._start_task
    if hub.eingang._task is not None:
        await hub.eingang._task


async def test_dienste_sind_angemeldet(hass, integration):
    namen = set(hass.services.async_services()[DOMAIN])
    assert namen == {
        "zuordnen", "loesen", "lernmodus_starten", "lernmodus_abbrechen", "serie_anlegen", "serie_umbenennen", "serie_loeschen",
        "folge_umbenennen", "folge_verschieben", "serien_zusammenfuehren", "eingang_einsortieren", "folgen_sortieren",
        "folge_loeschen", "papierkorb_leeren", "sync_anstossen", "update_anstossen", "liste_neu_ausrollen",
        "leise_zeiten_setzen", "gute_nacht_setzen", "lesezeichen_tage_setzen",  # AP 4.7
    }
