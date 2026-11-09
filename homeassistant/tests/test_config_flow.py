"""Einrichtung der Integration: Medienpfad, Boxen, größte Datei beim Upload."""

from __future__ import annotations

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tobibox.config_flow import parse_boxen
from custom_components.tobibox.const import CONF_BOXEN, CONF_MEDIEN_PFAD, CONF_UPLOAD_MAX_MIB, DOMAIN


@pytest.mark.parametrize(
    ("text", "erwartet"),
    [
        ("box1, box2", ["box1", "box2"]),
        ("box1 box2;box3", ["box1", "box2", "box3"]),
        ("  tobi-box_1  ", ["tobi-box_1"]),
        ("", None),
        ("Box1", None),  # Großbuchstaben sind nicht erlaubt
        ("b", None),  # mindestens 2 Zeichen
        ("-box", None),
        ("box1, box1", None),  # keine Doppelten
        ("x" * 25, None),
        ("box 1.2", None),
    ],
)
def test_parse_boxen(text, erwartet):
    assert parse_boxen(text) == erwartet


@pytest.fixture(autouse=True)
def _brauche_integration(enable_custom_integrations, mqtt_broker, hass_storage):
    return None


async def test_einrichtung(hass, nas):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MEDIEN_PFAD: str(nas.medien), CONF_BOXEN: "box1, box2", CONF_UPLOAD_MAX_MIB: 200}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_MEDIEN_PFAD: str(nas.medien), CONF_BOXEN: ["box1", "box2"], CONF_UPLOAD_MAX_MIB: 200}
    await hass.async_block_till_done()
    hub = hass.data[DOMAIN]
    assert hub.boxen == ["box1", "box2"] and hub.upload_max_bytes == 200 * 1024 * 1024
    assert hub.pfade.eingang == nas.eingang and hub.pfade.export == nas.export  # neben ``medien/``
    await hub.start_fertig.wait()
    if hub._start_task is not None:
        await hub._start_task
    if hub.eingang._task is not None:
        await hub.eingang._task
    await hass.config_entries.async_unload(hass.config_entries.async_entries(DOMAIN)[0].entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("eingabe", "feld", "fehler"),
    [
        ({CONF_MEDIEN_PFAD: "/gibt/es/nicht", CONF_BOXEN: "box1", CONF_UPLOAD_MAX_MIB: 500}, CONF_MEDIEN_PFAD, "medien_pfad_fehlt"),
        ({CONF_BOXEN: "Box 1", CONF_UPLOAD_MAX_MIB: 500}, CONF_BOXEN, "boxen_ungueltig"),
        ({CONF_BOXEN: "box1", CONF_UPLOAD_MAX_MIB: 0}, CONF_UPLOAD_MAX_MIB, "upload_ungueltig"),
        ({CONF_BOXEN: "box1", CONF_UPLOAD_MAX_MIB: 10**9}, CONF_UPLOAD_MAX_MIB, "upload_ungueltig"),
    ],
)
async def test_fehler(hass, nas, eingabe, feld, fehler):
    eingabe = {CONF_MEDIEN_PFAD: str(nas.medien), **eingabe}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], eingabe)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {feld: fehler}


async def test_nur_eine_einrichtung(hass, nas, einrichtung_daten):
    MockConfigEntry(domain=DOMAIN, data=einrichtung_daten, unique_id=DOMAIN).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT


async def test_optionen_aendern_upload_grenze(hass, nas, einrichtung_daten, frontend_dir):
    entry = MockConfigEntry(domain=DOMAIN, data=einrichtung_daten, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_MEDIEN_PFAD: str(nas.medien), CONF_BOXEN: "box1, box2, box3", CONF_UPLOAD_MAX_MIB: 750}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    hub = hass.data[DOMAIN]  # die Integration wurde neu geladen
    assert hub.upload_max_bytes == 750 * 1024 * 1024 and hub.boxen == ["box1", "box2", "box3"]
    await hub.start_fertig.wait()
    if hub._start_task is not None:
        await hub._start_task
    if hub.eingang._task is not None:
        await hub.eingang._task
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
