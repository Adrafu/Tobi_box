"""Integration ``tobibox``: Zuordnungen, Medienverwaltung und MQTT-Schnittstelle für die Tobi Boxen.

Sie ist der einzige Schreiber für Zuordnungen und ``serie.json`` (D1, D2). Verträge:
``docs/protocol/ha-websocket-v1.md`` (Seite <-> Backend), ``docs/protocol/mqtt-v1.md`` (Box <-> HA),
``docs/data-model.md``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from . import testpanel, websocket_api
from .const import DOMAIN, TESTPANEL
from .http import TobiboxUploadView
from .hub import Hub
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

#: Ordner der Seite (``frontend/tobibox-panel.js``); in Tests austauschbar
FRONTEND_PFAD = Path(__file__).parent / "frontend"
PANEL_URL = "tobibox"
PANEL_ELEMENT = "tobibox-panel"
STATIC_URL = "/tobibox_static"
PANEL_DATEI = "tobibox-panel.js"

_GEMERKT = f"{DOMAIN}_einmalig"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    websocket_api.async_register(hass)
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    integration = await async_get_integration(hass, DOMAIN)
    hub = Hub(hass, entry)
    hass.data[DOMAIN] = hub
    await hub.async_start(str(integration.version))

    # Upload-Endpunkt und statische Dateien der Seite lassen sich nicht abmelden: einmal je HA-Lauf
    if not hass.data.get(_GEMERKT):
        hass.http.register_view(TobiboxUploadView())
        if FRONTEND_PFAD.is_dir():
            await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, str(FRONTEND_PFAD), cache_headers=False)])
        hass.data[_GEMERKT] = True
    if TESTPANEL:  # Messungen A0b; Schalter in const.py
        testpanel.async_register_views(hass)
        await testpanel.async_register_panel(hass, FRONTEND_PFAD, STATIC_URL, str(integration.version))
    if (FRONTEND_PFAD / PANEL_DATEI).is_file():
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title="Tobi Box",
            sidebar_icon="mdi:speaker-wireless",
            module_url=f"{STATIC_URL}/{PANEL_DATEI}?v={integration.version}",
            embed_iframe=False,
            require_admin=True,
        )
    else:
        _LOGGER.warning("Die Seite %s fehlt; die Seitenleiste zeigt \"Tobi Box\" erst nach der Installation der Seite", FRONTEND_PFAD / PANEL_DATEI)
    entry.async_on_unload(entry.add_update_listener(_neu_laden))
    return True


async def _neu_laden(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub: Hub | None = hass.data.pop(DOMAIN, None)
    if hub is not None:
        await hub.async_stop()
    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    if TESTPANEL:
        testpanel.async_remove_panel(hass)
    return True
