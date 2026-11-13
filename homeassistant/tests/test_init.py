"""Einrichtung: Seite über ``panel_custom``, statische Dateien, Upload-Ansicht, Entladen (Vertrag W, 2.1 und 9)."""

from __future__ import annotations

import logging
import re

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
    assert cfg["name"] == "tobibox-app"  # R17-9: die neue Seite übernimmt /tobibox
    assert re.fullmatch(r"/tobibox_static/tobibox-app\.js\?v=0\.1\.0-[0-9a-f]{12}", cfg["module_url"])  # Version der Integration und Stand der Dateien (B4)
    assert cfg["embed_iframe"] is False and cfg["trust_external"] is False


async def test_statische_dateien_sind_oeffentlich_und_ohne_geheimnisse(hass, integration, hass_client_no_auth, frontend_dir):
    client = await hass_client_no_auth()
    antwort = await client.get("/tobibox_static/tobibox-app.js")
    assert antwort.status == 200
    assert "Attrappe" in await antwort.text()
    assert (await client.get("/tobibox_static/tobibox-panel.js")).status == 200  # alte Komponente bleibt ausgeliefert (Einbettung später)
    assert (await client.get("/tobibox_static/gibtsnicht.js")).status == 404


async def test_statische_dateien_senden_no_cache_und_bleiben_im_ordner(hass, integration, hass_client_no_auth, frontend_dir):
    """B4: der Browser fragt bei jedem Laden nach (ETag, 304); kein Zugriff aus dem Ordner heraus."""
    client = await hass_client_no_auth()
    antwort = await client.get("/tobibox_static/tobibox-app.js")
    assert antwort.headers["Cache-Control"] == "no-cache"
    etag = antwort.headers.get("ETag")
    assert etag
    assert (await client.get("/tobibox_static/tobibox-app.js", headers={"If-None-Match": etag})).status == 304
    (frontend_dir / "seiten").mkdir()
    (frontend_dir / "seiten" / "x.js").write_text("// x\n", encoding="utf-8")
    assert (await client.get("/tobibox_static/seiten/x.js")).status == 200
    assert (await client.get("/tobibox_static/..%2Fsecret.txt")).status in (400, 404)  # HA lehnt Pfade mit .. schon vorher ab
    assert (await client.get("/tobibox_static/seiten")).status == 404


def test_frontend_stand_aendert_sich_mit_dem_inhalt(tmp_path):
    from custom_components.tobibox import frontend_stand

    (tmp_path / "a.js").write_text("eins", encoding="utf-8")
    (tmp_path / "unter").mkdir()
    (tmp_path / "unter" / "b.js").write_text("zwei", encoding="utf-8")
    s1 = frontend_stand(tmp_path)
    assert re.fullmatch(r"[0-9a-f]{12}", s1)
    assert frontend_stand(tmp_path) == s1, "stabil"
    (tmp_path / "unter" / "b.js").write_text("drei", encoding="utf-8")
    assert frontend_stand(tmp_path) != s1
    assert frontend_stand(tmp_path / "gibtsnicht") == "0"


async def test_alte_komponente_hat_keinen_seitenleisten_eintrag(hass, starte_integration, frontend_dir):
    """R17-9: nur ``/tobibox`` (neue Seite) und ``/tobibox-test`` (Testpanel); kein ``/tobibox-neu``, kein Eintrag der alten Komponente."""
    (frontend_dir / "tobibox-testpanel.js").write_text("// Attrappe\n", encoding="utf-8")
    await starte_integration()
    panels = hass.data[frontend.DATA_PANELS]
    tobibox = {k: v for k, v in panels.items() if k.startswith("tobibox")}
    assert set(tobibox) == {"tobibox", "tobibox-test"}
    assert all(p.require_admin is True for p in tobibox.values())
    assert tobibox["tobibox"].config["_panel_custom"]["name"] == "tobibox-app"
    assert tobibox["tobibox-test"].config["_panel_custom"]["name"] == "tobibox-testpanel"
    assert tobibox["tobibox-test"].sidebar_title == "Tobi Box (Test)"
    assert not any((v.config or {}).get("_panel_custom", {}).get("name") == "tobibox-panel" for v in panels.values())


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
    """Der Ordner ``frontend/`` wird nur gelesen; ``__init__.py`` zeigt auf ``frontend/tobibox-app.js``."""
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


# --- Upload-Grenze 2 GiB: der alte Wert 500 wird beim Update angehoben (Vertrag W, 8; Paket A3d) ---


async def test_migration_hebt_500_auf_2048_an_und_laesst_andere_werte(hass, starte_integration, einrichtung_daten):
    from custom_components.tobibox.const import CONF_UPLOAD_MAX_MIB

    assert einrichtung_daten[CONF_UPLOAD_MAX_MIB] == 500  # der gespeicherte Stand vor dem Update
    hub = await starte_integration()
    assert hub.upload_max_bytes == 2048 * 1024 * 1024
    assert hub.entry.version == 2 and hub.entry.data[CONF_UPLOAD_MAX_MIB] == 2048


async def test_migration_anderer_wert_bleibt_und_laeuft_nur_einmal(hass, starte_integration, einrichtung_daten):
    from custom_components.tobibox.const import CONF_UPLOAD_MAX_MIB

    einrichtung_daten[CONF_UPLOAD_MAX_MIB] = 750
    hub = await starte_integration()
    assert hub.upload_max_bytes == 750 * 1024 * 1024 and hub.entry.version == 2
    # Version 2: wer jetzt bewusst 500 einstellt, behält 500 (die Migration läuft nicht noch einmal)
    entry = hub.entry
    await hass.config_entries.async_unload(entry.entry_id)
    hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_UPLOAD_MAX_MIB: 500})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data[DOMAIN].upload_max_bytes == 500 * 1024 * 1024


async def test_migration_hebt_auch_die_optionen_an(hass, nas, enable_custom_integrations, mqtt_broker, hass_storage, frontend_dir):
    from custom_components.tobibox.const import CONF_BOXEN, CONF_MEDIEN_PFAD, CONF_UPLOAD_MAX_MIB

    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=DOMAIN, title="Tobi Box",
        data={CONF_MEDIEN_PFAD: str(nas.medien), CONF_BOXEN: ["box1"], CONF_UPLOAD_MAX_MIB: 300},
        options={CONF_UPLOAD_MAX_MIB: 500},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert dict(entry.options)[CONF_UPLOAD_MAX_MIB] == 2048 and entry.data[CONF_UPLOAD_MAX_MIB] == 300
    assert hass.data[DOMAIN].upload_max_bytes == 2048 * 1024 * 1024
    await hass.config_entries.async_unload(entry.entry_id)
