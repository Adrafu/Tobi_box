"""HA-Aktionen der Integration (``services.yaml``).

Die Aktionen rufen **dieselben** Backend-Funktionen wie die WebSocket-Befehle (Vertrag W, Abschnitt 1). Eine
Aktion hat keine Seite und damit keinen Antwortweg: Bei einer Rückfrage gilt Ablehnung, es sei denn das
Aktionsfeld (``ueberschreiben``, ``tobies_bestaetigt``) ist ausdrücklich ``true``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .fehler import TobiboxFehler
from .hub import FEHLT, Hub

try:
    import probatio as vol
except ImportError:  # pragma: no cover
    import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

_RE_ID_SUFFIX = re.compile(r"^(.*) \(([^()]+)\)$")


def _hub(hass: HomeAssistant) -> Hub:
    hub = hass.data.get(DOMAIN)
    if hub is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unknown_error")
    return hub


def _ziel(daten: dict[str, Any]) -> dict[str, Any]:
    typ = daten["typ"]
    if typ == "aktion":
        return {"typ": "aktion", "aktion": daten.get("aktion")}
    ziel: dict[str, Any] = {"typ": typ, "serie": daten.get("serie_id")}
    if typ == "folge":
        ziel["folge"] = daten.get("folge")
    return ziel


def serie_aus_vorbelegung(hub: Hub, text: str) -> str | None:
    """Die Serie zur Auswahl ``lern_serie`` einer Box (Anzeigename, bei doppelten Namen mit `` (<id>)`` am Ende)."""
    m = _RE_ID_SUFFIX.match(text)
    if m and m.group(2) in hub.medien.serien:
        return m.group(2)
    for sid, info in hub.medien.serien.items():
        if info.serie.name == text:
            return sid
    return None


def _wrap(func: Callable[[Hub, ServiceCall], Awaitable[Any]]):
    async def handler(call: ServiceCall) -> None:
        hub = _hub(call.hass)
        try:
            await func(hub, call)
        except TobiboxFehler as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key=err.code, translation_placeholders={k: str(v) for k, v in err.details.items()}
            ) from err

    return handler


def _optional_text(name: str):
    return {vol.Optional(name): cv.string}


TYP = vol.In(["serie", "folge", "aktion"])


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def zuordnen(hub: Hub, call: ServiceCall) -> None:
        d = call.data
        await hub.zuordnung_setzen(
            d["uid"],
            _ziel(d),
            name=d["name"] if "name" in d else FEHLT,
            ueberschreiben=d.get("ueberschreiben", False),
        )

    async def loesen(hub: Hub, call: ServiceCall) -> None:
        await hub.zuordnung_entfernen(call.data["uid"])

    async def lernmodus_starten(hub: Hub, call: ServiceCall) -> None:
        d = dict(call.data)
        if d["typ"] not in ("serie", "folge"):
            raise TobiboxFehler("ziel_ungueltig")
        if not d.get("serie_id"):
            z = hub.mqtt.boxen.get(d["box"])
            vor = serie_aus_vorbelegung(hub, z.lern_serie) if z and z.lern_serie else None
            if vor is None:
                raise TobiboxFehler("serie_nicht_gefunden")
            d["serie_id"] = vor
        await hub.lernmodus.start(d["box"], _ziel(d), d.get("name"), auto_ueberschreiben=d.get("ueberschreiben", False))

    async def lernmodus_abbrechen(hub: Hub, call: ServiceCall) -> None:
        await hub.lernmodus.abbrechen(call.data["box"])

    async def serie_anlegen(hub: Hub, call: ServiceCall) -> None:
        await hub.medien.serie_anlegen(call.data["name"], call.data.get("typ", "normal"))

    async def serie_umbenennen(hub: Hub, call: ServiceCall) -> None:
        await hub.medien.serie_umbenennen(call.data["serie_id"], call.data["name"])

    async def serie_loeschen(hub: Hub, call: ServiceCall) -> None:
        await hub.medien.serie_loeschen(call.data["serie_id"], call.data.get("tobies_bestaetigt", False), None)

    async def folge_umbenennen(hub: Hub, call: ServiceCall) -> None:
        await hub.medien.folge_umbenennen(call.data["serie_id"], call.data["folge"], call.data["name"], None)

    async def folge_verschieben(hub: Hub, call: ServiceCall) -> None:
        d = call.data
        await hub.medien.folge_verschieben(d["serie_id"], d["folge"], d["ziel_serie_id"], d.get("tobies_bestaetigt", False), None)

    async def serien_zusammenfuehren(hub: Hub, call: ServiceCall) -> None:
        d = call.data
        await hub.medien.serien_zusammenfuehren(d["quelle_id"], d["ziel_id"], d.get("tobies_bestaetigt", False), None, None)

    async def eingang_einsortieren(hub: Hub, call: ServiceCall) -> None:
        await hub.eingang.starte_durchlauf(None, call.data.get("sofort", False))

    async def folgen_sortieren(hub: Hub, call: ServiceCall) -> None:
        await hub.medien.folgen_ordnen(call.data["serie_id"], list(call.data["folgen"]), None)

    async def folge_loeschen(hub: Hub, call: ServiceCall) -> None:
        d = call.data
        await hub.medien.folge_loeschen(d["serie_id"], d["folge"], d.get("tobies_bestaetigt", False), None)

    async def papierkorb_leeren(hub: Hub, call: ServiceCall) -> None:
        if call.data.get("bestaetigt") is not True:
            raise TobiboxFehler("invalid_format")
        await hub.medien.papierkorb_leeren(None)

    async def sync_anstossen(hub: Hub, call: ServiceCall) -> None:
        await hub.box_sync(call.data["box"])

    async def update_anstossen(hub: Hub, call: ServiceCall) -> None:
        box = call.data["box"]
        if box not in hub.mqtt.boxen:
            raise TobiboxFehler("box_unbekannt")
        if hub.mqtt.boxen[box].online is not True:
            raise TobiboxFehler("box_offline")
        await hub.mqtt.sende_update(box)

    async def liste_neu_ausrollen(hub: Hub, call: ServiceCall) -> None:
        if call.data.get("bestaetigt") is not True:
            raise TobiboxFehler("invalid_format")
        await hub.liste_neu_ausrollen()

    bool_ = cv.boolean
    texte: list[tuple[str, Any, Any]] = [
        (
            "zuordnen",
            zuordnen,
            vol.Schema(
                {
                    vol.Required("uid"): cv.string,
                    vol.Required("typ"): TYP,
                    vol.Optional("serie_id"): cv.string,
                    vol.Optional("folge"): cv.string,
                    vol.Optional("aktion"): vol.In(["status", "gute_nacht"]),
                    vol.Optional("name"): vol.Any(None, cv.string),
                    vol.Optional("ueberschreiben"): bool_,
                }
            ),
        ),
        ("loesen", loesen, vol.Schema({vol.Required("uid"): cv.string})),
        (
            "lernmodus_starten",
            lernmodus_starten,
            vol.Schema(
                {
                    vol.Required("box"): cv.string,
                    vol.Required("typ"): TYP,
                    vol.Optional("serie_id"): cv.string,
                    vol.Optional("folge"): cv.string,
                    vol.Optional("name"): cv.string,
                    vol.Optional("ueberschreiben"): bool_,
                }
            ),
        ),
        ("lernmodus_abbrechen", lernmodus_abbrechen, vol.Schema({vol.Required("box"): cv.string})),
        ("serie_anlegen", serie_anlegen, vol.Schema({vol.Required("name"): cv.string, vol.Optional("typ"): vol.In(["normal", "ueberraschung"])})),
        ("serie_umbenennen", serie_umbenennen, vol.Schema({vol.Required("serie_id"): cv.string, vol.Required("name"): cv.string})),
        ("serie_loeschen", serie_loeschen, vol.Schema({vol.Required("serie_id"): cv.string, vol.Optional("tobies_bestaetigt"): bool_})),
        (
            "folge_umbenennen",
            folge_umbenennen,
            vol.Schema({vol.Required("serie_id"): cv.string, vol.Required("folge"): cv.string, vol.Required("name"): cv.string}),
        ),
        (
            "folge_verschieben",
            folge_verschieben,
            vol.Schema(
                {
                    vol.Required("serie_id"): cv.string,
                    vol.Required("folge"): cv.string,
                    vol.Required("ziel_serie_id"): cv.string,
                    vol.Optional("tobies_bestaetigt"): bool_,
                }
            ),
        ),
        (
            "serien_zusammenfuehren",
            serien_zusammenfuehren,
            vol.Schema({vol.Required("quelle_id"): cv.string, vol.Required("ziel_id"): cv.string, vol.Optional("tobies_bestaetigt"): bool_}),
        ),
        ("eingang_einsortieren", eingang_einsortieren, vol.Schema({vol.Optional("sofort"): bool_})),
        ("folgen_sortieren", folgen_sortieren, vol.Schema({vol.Required("serie_id"): cv.string, vol.Required("folgen"): [cv.string]})),
        (
            "folge_loeschen",
            folge_loeschen,
            vol.Schema({vol.Required("serie_id"): cv.string, vol.Required("folge"): cv.string, vol.Optional("tobies_bestaetigt"): bool_}),
        ),
        ("papierkorb_leeren", papierkorb_leeren, vol.Schema({vol.Required("bestaetigt"): bool_})),
        ("sync_anstossen", sync_anstossen, vol.Schema({vol.Required("box"): cv.string})),
        ("update_anstossen", update_anstossen, vol.Schema({vol.Required("box"): cv.string})),
        ("liste_neu_ausrollen", liste_neu_ausrollen, vol.Schema({vol.Required("bestaetigt"): bool_})),
    ]
    for name, func, schema in texte:
        hass.services.async_register(DOMAIN, name, _wrap(func), schema=schema)
