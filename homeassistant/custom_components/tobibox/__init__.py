"""Integration ``tobibox``: Zuordnungen, Medienverwaltung und MQTT-Schnittstelle für die Tobi Boxen.

Sie ist der einzige Schreiber für Zuordnungen und ``serie.json`` (D1, D2). Verträge:
``docs/protocol/ha-websocket-v1.md`` (Seite <-> Backend), ``docs/protocol/mqtt-v1.md`` (Box <-> HA),
``docs/data-model.md``.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from . import testpanel, websocket_api
from .const import CONF_UPLOAD_MAX_MIB, DOMAIN, TESTPANEL, UPLOAD_MAX_MIB_ALT, UPLOAD_MAX_MIB_VORGABE
from .http import TobiboxCoverView, TobiboxStaticView, TobiboxUploadView
from .hub import Hub
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

#: Ordner der Seite (``frontend/tobibox-panel.js``); in Tests austauschbar
FRONTEND_PFAD = Path(__file__).parent / "frontend"
#: Die neue Seite (R17-9): übernimmt ``/tobibox``, Element ``tobibox-app``. Die alte Komponente ``tobibox-panel``
#: (Datei bleibt, wird später in „Technik“ eingebettet) hat keinen eigenen Seitenleisten-Eintrag mehr.
PANEL_URL = "tobibox"
PANEL_ELEMENT = "tobibox-app"
STATIC_URL = "/api/tobibox/static"
PANEL_DATEI = "tobibox-app.js"
ALTE_PANEL_DATEI = "tobibox-panel.js"

_GEMERKT = f"{DOMAIN}_einmalig"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    websocket_api.async_register(hass)
    async_setup_services(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Version 1 -> 2: Die Grenze je Datei beim Upload steigt von 500 MiB auf 2 GiB (Vertrag W, Abschnitt 8).

    Nur der alte Vorgabewert 500 wird angehoben, in den Einrichtungsdaten und in den Optionen; ein anderer, bewusst
    gesetzter Wert bleibt. Die Migration läuft einmal: Wer danach 500 einstellt, behält 500."""
    if entry.version < 2:
        daten = dict(entry.data)
        optionen = dict(entry.options)
        for quelle in (daten, optionen):
            if quelle.get(CONF_UPLOAD_MAX_MIB) == UPLOAD_MAX_MIB_ALT:
                quelle[CONF_UPLOAD_MAX_MIB] = UPLOAD_MAX_MIB_VORGABE
        hass.config_entries.async_update_entry(entry, data=daten, options=optionen, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    integration = await async_get_integration(hass, DOMAIN)
    hub = Hub(hass, entry)
    hass.data[DOMAIN] = hub
    await hub.async_start(str(integration.version))
    # Dateisystem-Zugriffe gebündelt im Executor (nicht in der Event-Loop)
    frontend_da, panel_da, stand = await hass.async_add_executor_job(_pruefe_frontend)

    # Upload-Endpunkt und statische Dateien der Seite lassen sich nicht abmelden: einmal je HA-Lauf
    if not hass.data.get(_GEMERKT):
        hass.http.register_view(TobiboxUploadView())
        hass.http.register_view(TobiboxCoverView())
        if frontend_da:
            hass.http.register_view(TobiboxStaticView(FRONTEND_PFAD))  # mit Cache-Control: no-cache (B4), siehe http.py
        hass.data[_GEMERKT] = True
    if TESTPANEL:  # Messungen A0b; Schalter in const.py
        testpanel.async_register_views(hass)
        await testpanel.async_register_panel(hass, FRONTEND_PFAD, STATIC_URL, str(integration.version))
    if panel_da:
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title="Tobi Box",
            sidebar_icon="mdi:speaker-wireless",
            module_url=f"{STATIC_URL}/{PANEL_DATEI}?v={integration.version}-{stand}",  # Stand der Dateien: neue Adresse bei jeder Änderung
            embed_iframe=False,
            require_admin=True,
        )
    else:
        _LOGGER.warning("Die Seite %s fehlt; die Seitenleiste zeigt \"Tobi Box\" erst nach der Installation der Seite", FRONTEND_PFAD / PANEL_DATEI)
    entry.async_on_unload(entry.add_update_listener(_neu_laden))
    return True


def _pruefe_frontend() -> tuple[bool, bool, str]:
    """``(Ordner da, Panel-Datei da, Stand der Dateien)``; läuft im Executor."""
    return FRONTEND_PFAD.is_dir(), (FRONTEND_PFAD / PANEL_DATEI).is_file(), frontend_stand(FRONTEND_PFAD)


def frontend_stand(ordner: Path) -> str:
    """Kurze Prüfsumme über Namen und Inhalt aller Dateien der Seite (12 Hexzeichen); leer ohne Ordner. Läuft im Executor."""
    if not ordner.is_dir():
        return "0"
    h = hashlib.sha256()
    for datei in sorted(p for p in ordner.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(datei.relative_to(ordner).as_posix().encode())
        h.update(datei.read_bytes())
    return h.hexdigest()[:12]


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
