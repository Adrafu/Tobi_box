"""Einrichtung der Integration: Medienpfad, Boxen, größte Datei beim Upload."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import (
    CONF_BOXEN,
    CONF_MEDIEN_PFAD,
    CONF_UPLOAD_MAX_MIB,
    DOMAIN,
    RE_BOX,
    UPLOAD_MAX_MIB_VORGABE,
)

try:
    import probatio as vol
except ImportError:  # pragma: no cover
    import voluptuous as vol


def parse_boxen(text: str) -> list[str] | None:
    """``"box1, box2"`` -> ``["box1", "box2"]``; ``None``, wenn ein Name nicht zu ``[a-z0-9][a-z0-9_-]{1,23}`` passt."""
    namen = [n for n in re.split(r"[\s,;]+", text.strip()) if n]
    if not namen or len(set(namen)) != len(namen) or not all(RE_BOX.match(n) for n in namen):
        return None
    return namen


async def _pruefe(hass: Any, eingabe: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, str]]:
    fehler: dict[str, str] = {}
    pfad = str(eingabe.get(CONF_MEDIEN_PFAD, "")).strip()
    if pfad and not await hass.async_add_executor_job(Path(pfad).is_dir):
        fehler[CONF_MEDIEN_PFAD] = "medien_pfad_fehlt"
    elif not pfad:
        fehler[CONF_MEDIEN_PFAD] = "medien_pfad_fehlt"
    boxen = parse_boxen(str(eingabe.get(CONF_BOXEN, "")))
    if boxen is None:
        fehler[CONF_BOXEN] = "boxen_ungueltig"
    mib = eingabe.get(CONF_UPLOAD_MAX_MIB, UPLOAD_MAX_MIB_VORGABE)
    if not isinstance(mib, int) or isinstance(mib, bool) or not 1 <= mib <= 100_000:
        fehler[CONF_UPLOAD_MAX_MIB] = "upload_ungueltig"
    if fehler:
        return None, fehler
    return {CONF_MEDIEN_PFAD: pfad, CONF_BOXEN: boxen, CONF_UPLOAD_MAX_MIB: mib}, {}


def _schema(vorgabe: dict[str, Any]) -> Any:
    return vol.Schema(
        {
            vol.Required(CONF_MEDIEN_PFAD, default=vorgabe.get(CONF_MEDIEN_PFAD, "/media/tobibox/medien")): str,
            vol.Required(CONF_BOXEN, default=vorgabe.get(CONF_BOXEN, "box1, box2")): str,
            vol.Required(CONF_UPLOAD_MAX_MIB, default=vorgabe.get(CONF_UPLOAD_MAX_MIB, UPLOAD_MAX_MIB_VORGABE)): int,
        }
    )


class TobiboxConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fehler: dict[str, str] = {}
        if user_input is not None:
            daten, fehler = await _pruefe(self.hass, user_input)
            if daten is not None:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Tobi Box", data=daten)
        return self.async_show_form(step_id="user", data_schema=_schema(user_input or {}), errors=fehler)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return TobiboxOptionsFlow()


class TobiboxOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fehler: dict[str, str] = {}
        aktuell = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            daten, fehler = await _pruefe(self.hass, user_input)
            if daten is not None:
                return self.async_create_entry(data=daten)
        vorgabe = user_input or {**aktuell, CONF_BOXEN: ", ".join(aktuell.get(CONF_BOXEN, []))}
        return self.async_show_form(step_id="init", data_schema=_schema(vorgabe), errors=fehler)
