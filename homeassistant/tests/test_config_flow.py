"""Einrichtung der Integration: Medienpfad, Boxen, größte Datei beim Upload."""

from __future__ import annotations

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tobibox.config_flow import box_anzeigen_text, parse_box_anzeigen, parse_boxen
from custom_components.tobibox.const import CONF_BOX_ANZEIGEN, CONF_BOXEN, CONF_MEDIEN_PFAD, CONF_UPLOAD_MAX_MIB, DOMAIN


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


@pytest.mark.parametrize(
    ("text", "boxen", "erwartet"),
    [
        ("box1=Box 1, box2=Box 2", None, {"box1": "Box 1", "box2": "Box 2"}),
        ("box1=Box 1;box2=Box 2", ["box1", "box2"], {"box1": "Box 1", "box2": "Box 2"}),
        ("  box1 =  Meine Box  ,", None, {"box1": "Meine Box"}),  # Leerraum drumherum zählt nicht, Rest-Komma auch nicht
        ("box1=Käpt’n Blaubär 🐻", None, {"box1": "Käpt’n Blaubär 🐻"}),
        ("", None, {}),  # leer = keine Anzeigenamen
        ("   ", ["box1"], {}),
        ("box1=" + "x" * 40, None, {"box1": "x" * 40}),
        ("box1=" + "x" * 41, None, None),  # höchstens 40 Zeichen
        ("box1=", None, None),  # der Name fehlt
        ("box1= \t", None, None),
        ("box1", None, None),  # kein Gleichheitszeichen
        ("=Box 1", None, None),
        ("Box1=Box 1", None, None),  # der Box-Name folgt den Regeln von ``parse_boxen``
        ("b=Box", None, None),
        ("box1=Eins, box1=Zwei", None, None),  # keine Doppelten
        ("box3=Box 3", ["box1", "box2"], None),  # nur eingerichtete Boxen
        ("box1=Box 1, box3=Box 3", ["box1", "box2"], None),
    ],
)
def test_parse_box_anzeigen(text, boxen, erwartet):
    assert parse_box_anzeigen(text, boxen) == erwartet


def test_box_anzeigen_text_ist_das_gegenstueck():
    assert box_anzeigen_text({"box1": "Box 1", "box2": "Box 2"}) == "box1=Box 1, box2=Box 2"
    assert box_anzeigen_text(None) == box_anzeigen_text({}) == ""
    assert parse_box_anzeigen(box_anzeigen_text({"box1": "Box 1", "box2": "Box 2"})) == {"box1": "Box 1", "box2": "Box 2"}


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


async def _optionen(hass, entry, eingabe):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return result, await hass.config_entries.options.async_configure(result["flow_id"], eingabe)


async def _fertig(hass, hub):
    await hub.start_fertig.wait()
    if hub._start_task is not None:
        await hub._start_task
    if hub.eingang._task is not None:
        await hub.eingang._task
    await hass.async_block_till_done()


async def test_optionen_anzeigenamen_der_boxen(hass, nas, einrichtung_daten, frontend_dir):
    entry = MockConfigEntry(domain=DOMAIN, data=einrichtung_daten, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data[DOMAIN].box_anzeigen_optionen == {}
    await _fertig(hass, hass.data[DOMAIN])

    # Das Textfeld gibt es nur in den Optionen, es ist freiwillig und beginnt leer
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert CONF_BOX_ANZEIGEN in [str(k) for k in result["data_schema"].schema]
    grundwerte = {CONF_MEDIEN_PFAD: str(nas.medien), CONF_BOXEN: "box1, box2", CONF_UPLOAD_MAX_MIB: 500}

    # Ungültig: Fehlermeldung am Feld, nichts wird gespeichert
    for falsch in ("box1=" + "x" * 41, "box1", "box3=Box 3", "box1=A, box1=B"):
        r = await hass.config_entries.options.async_configure(result["flow_id"], {**grundwerte, CONF_BOX_ANZEIGEN: falsch})
        assert r["type"] is FlowResultType.FORM and r["errors"] == {CONF_BOX_ANZEIGEN: "box_anzeigen_ungueltig"}, falsch
    assert CONF_BOX_ANZEIGEN not in entry.options

    # Gültig: gespeichert als Zuordnung Box -> ganzer Name, die Integration lädt neu und der Hub kennt die Namen
    r = await hass.config_entries.options.async_configure(result["flow_id"], {**grundwerte, CONF_BOX_ANZEIGEN: "box1=Box 1, box2=Box 2"})
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert r["data"][CONF_BOX_ANZEIGEN] == {"box1": "Box 1", "box2": "Box 2"}
    await hass.async_block_till_done()
    hub = hass.data[DOMAIN]
    assert hub.box_anzeigen_optionen == {"box1": "Box 1", "box2": "Box 2"}
    assert hub.box_anzeige("box1") == "Box 1" and hub.hello(1, False)["box_anzeigen"] == {"box1": "Box 1", "box2": "Box 2"}
    await _fertig(hass, hub)

    # Das Feld zeigt beim nächsten Öffnen den gespeicherten Wert; leer geschickt entfernt es die Namen wieder
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert [k.default() for k in result["data_schema"].schema if str(k) == CONF_BOX_ANZEIGEN] == ["box1=Box 1, box2=Box 2"]
    r = await hass.config_entries.options.async_configure(result["flow_id"], {**grundwerte, CONF_BOX_ANZEIGEN: ""})
    assert r["type"] is FlowResultType.CREATE_ENTRY and CONF_BOX_ANZEIGEN not in r["data"]
    await hass.async_block_till_done()
    hub = hass.data[DOMAIN]
    assert hub.box_anzeigen_optionen == {} and hub.box_anzeige("box1") == "box1"
    await _fertig(hass, hub)
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_optionen_ohne_das_neue_feld_bleiben_gueltig(hass, nas, einrichtung_daten, frontend_dir):
    """Alte Eingaben (drei Felder) funktionieren weiter; das Feld ist freiwillig."""
    entry = MockConfigEntry(domain=DOMAIN, data=einrichtung_daten, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _fertig(hass, hass.data[DOMAIN])
    _, r = await _optionen(hass, entry, {CONF_MEDIEN_PFAD: str(nas.medien), CONF_BOXEN: "box1, box2", CONF_UPLOAD_MAX_MIB: 500})
    assert r["type"] is FlowResultType.CREATE_ENTRY and r["data"] == {CONF_MEDIEN_PFAD: str(nas.medien), CONF_BOXEN: ["box1", "box2"], CONF_UPLOAD_MAX_MIB: 500}
    await hass.async_block_till_done()
    await _fertig(hass, hass.data[DOMAIN])
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_einrichtung_hat_das_feld_nicht(hass, nas):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert CONF_BOX_ANZEIGEN not in [str(k) for k in result["data_schema"].schema]
