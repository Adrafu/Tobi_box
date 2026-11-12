"""Einrichtung der Integration: Medienpfad, Boxen, größte Datei beim Upload; in den Optionen auch die Anzeigenamen der Boxen."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import (
    BOX_ANZEIGE_MAX,
    CONF_BOX_ANZEIGEN,
    CONF_BOXEN,
    CONF_MEDIEN_PFAD,
    CONF_UPLOAD_MAX_MIB,
    DOMAIN,
    RE_BOX,
    UPLOAD_MAX_MIB_VORGABE,
)
from .namen import anzeigename_streng

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


def parse_box_anzeigen(text: str, boxen: list[str] | None = None) -> dict[str, str] | None:
    """``"box1=Box 1, box2=Box 2"`` -> ``{"box1": "Box 1", "box2": "Box 2"}``; leerer Text -> ``{}``.

    ``None``, wenn die Schreibweise nicht stimmt: Name der Box wie bei ``parse_boxen`` (und, wenn ``boxen`` gegeben ist,
    eine der eingerichteten Boxen), kein Name doppelt, jeder Anzeigename 1 bis 40 Zeichen (ohne Steuerzeichen).
    Getrennt wird bei Komma oder Semikolon; der Anzeigename ist der **ganze** Name („Box 1“, „Annas Box“)."""
    ergebnis: dict[str, str] = {}
    for teil in re.split(r"[,;]", text):
        if not teil.strip():
            continue
        box, gleich, name = teil.partition("=")
        box = box.strip()
        anzeige = anzeigename_streng(name, BOX_ANZEIGE_MAX)
        if not gleich or not RE_BOX.match(box) or box in ergebnis or anzeige is None:
            return None
        if boxen is not None and box not in boxen:
            return None
        ergebnis[box] = anzeige
    return ergebnis


def box_anzeigen_text(anzeigen: dict[str, str] | None) -> str:
    """Die Schreibweise fürs Textfeld (Gegenstück zu ``parse_box_anzeigen``)."""
    return ", ".join(f"{box}={name}" for box, name in (anzeigen or {}).items())


async def _pruefe(
    hass: Any, eingabe: dict[str, Any], mit_anzeigen: bool = False
) -> tuple[dict[str, Any] | None, dict[str, str]]:
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
    anzeigen: dict[str, str] = {}
    if mit_anzeigen:
        roh = eingabe.get(CONF_BOX_ANZEIGEN, "")
        anzeigen_neu = parse_box_anzeigen(roh, boxen) if isinstance(roh, str) and boxen is not None else None
        if anzeigen_neu is None and boxen is not None:
            fehler[CONF_BOX_ANZEIGEN] = "box_anzeigen_ungueltig"
        else:
            anzeigen = anzeigen_neu or {}
    if fehler:
        return None, fehler
    daten: dict[str, Any] = {CONF_MEDIEN_PFAD: pfad, CONF_BOXEN: boxen, CONF_UPLOAD_MAX_MIB: mib}
    if anzeigen:  # ohne Anzeigenamen bleibt der Eintrag so, wie er war (kein leeres Feld)
        daten[CONF_BOX_ANZEIGEN] = anzeigen
    return daten, {}


def _schema(vorgabe: dict[str, Any], mit_anzeigen: bool = False) -> Any:
    felder: dict[Any, Any] = {
        vol.Required(CONF_MEDIEN_PFAD, default=vorgabe.get(CONF_MEDIEN_PFAD, "/media/tobibox/medien")): str,
        vol.Required(CONF_BOXEN, default=vorgabe.get(CONF_BOXEN, "box1, box2")): str,
        vol.Required(CONF_UPLOAD_MAX_MIB, default=vorgabe.get(CONF_UPLOAD_MAX_MIB, UPLOAD_MAX_MIB_VORGABE)): int,
    }
    if mit_anzeigen:
        felder[vol.Optional(CONF_BOX_ANZEIGEN, default=vorgabe.get(CONF_BOX_ANZEIGEN, ""))] = str
    return vol.Schema(felder)


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
            daten, fehler = await _pruefe(self.hass, user_input, mit_anzeigen=True)
            if daten is not None:
                return self.async_create_entry(data=daten)
        vorgabe = user_input or {
            **aktuell,
            CONF_BOXEN: ", ".join(aktuell.get(CONF_BOXEN, [])),
            CONF_BOX_ANZEIGEN: box_anzeigen_text(aktuell.get(CONF_BOX_ANZEIGEN)),
        }
        return self.async_show_form(step_id="init", data_schema=_schema(vorgabe, mit_anzeigen=True), errors=fehler)
