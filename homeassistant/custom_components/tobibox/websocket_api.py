"""WebSocket-Befehle zwischen Seite und HA-Backend (Vertrag W, Abschnitt 3).

Reihenfolge der Dekoratoren wie in HA-Core: ``require_admin`` außen, dann ``websocket_command``, innen
``async_response``. Die Befehle rufen nur Funktionen des ``Hub``; Fehler (``TobiboxFehler``) werden zu
``connection.send_error(id, code, Klartext)``.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    EREIGNIS_THEMEN,
    RE_ANFRAGE_ID,
)
from .fehler import TobiboxFehler
from .hub import FEHLT, Hub

try:  # HA 2026.10 und neuer: ``probatio``; ältere Versionen: ``voluptuous``
    import probatio as vol
except ImportError:  # pragma: no cover
    import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

_HANDLER: list[Callable[..., Any]] = []


# --------------------------------------------------------------------------
# Schema-Bausteine (strikt: ``bool`` ist keine Zahl, ``bestaetigt`` muss ``true`` sein)
# --------------------------------------------------------------------------


def _ganz(lo: int, hi: int) -> Callable[[Any], int]:
    def pruefe(x: Any) -> int:
        if not isinstance(x, int) or isinstance(x, bool) or not lo <= x <= hi:
            raise vol.Invalid(f"ganze Zahl von {lo} bis {hi} erwartet")
        return x

    return pruefe


def _wahr(x: Any) -> bool:
    if x is not True:
        raise vol.Invalid("muss true sein")
    return True


def _text(x: Any) -> str:
    if not isinstance(x, str):
        raise vol.Invalid("Text erwartet")
    return x


def _wahrheit(x: Any) -> bool:
    if not isinstance(x, bool):
        raise vol.Invalid("true oder false erwartet")
    return x


def _objekt(x: Any) -> dict:
    if not isinstance(x, dict):
        raise vol.Invalid("Objekt erwartet")
    return x


ANFRAGE_ID = {vol.Optional("anfrage_id"): vol.All(_text, vol.Match(RE_ANFRAGE_ID.pattern))}
SERIE_ID = {vol.Required("serie_id"): _text}
STAND = {vol.Optional("stand"): _text}
LISTE_TEXT = vol.All([_text])


def _hub(hass: HomeAssistant) -> Hub:
    hub = hass.data.get(DOMAIN)
    if hub is None:
        raise TobiboxFehler("unknown_error")
    return hub


def befehl(
    name: str,
    schema: dict[Any, Any] | None = None,
    *,
    admin: bool = False,
):
    """Meldet einen Befehl ``tobibox/<name>`` an. Die Funktion bekommt ``(hub, connection, msg)`` und gibt das Ergebnis zurück."""

    def deko(func: Callable[[Hub, Any, dict[str, Any]], Awaitable[Any]]):
        @websocket_api.async_response
        async def handler(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
            try:
                hub = _hub(hass)
                ergebnis = await func(hub, connection, msg)
            except TobiboxFehler as err:
                try:
                    text = _hub(hass).fehler_text(err)
                except TobiboxFehler:
                    text = err.code
                connection.send_error(msg["id"], err.code, text)
                return
            connection.send_result(msg["id"], ergebnis)

        handler.__name__ = f"ws_{name.replace('/', '_')}"
        schema_voll = {vol.Required("type"): f"tobibox/{name}", **(schema or {})}
        gesamt = websocket_api.websocket_command(schema_voll)(handler)
        if admin:
            gesamt = websocket_api.require_admin(gesamt)
        _HANDLER.append(gesamt)
        return gesamt

    return deko


def _felder(msg: dict[str, Any], *ohne: str) -> dict[str, Any]:
    """Die Eingabefelder ohne ``id`` und ``type`` (für den Fingerabdruck der ``anfrage_id``)."""
    return {k: v for k, v in msg.items() if k not in ("id", "type", "anfrage_id", *ohne)}


# --------------------------------------------------------------------------
# 1 und 2: hello, subscribe
# --------------------------------------------------------------------------


@befehl("hello", {vol.Required("v"): _ganz(0, 1_000_000)})
async def ws_hello(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return hub.hello(msg["v"], bool(connection.user and connection.user.is_admin))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tobibox/subscribe",
        vol.Optional("themen"): vol.All([vol.In(EREIGNIS_THEMEN)]),
    }
)
@callback
def ws_subscribe(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    from .hub import Abo

    try:
        hub = _hub(hass)
    except TobiboxFehler:
        connection.send_error(msg["id"], "unknown_error", "Tobi Box ist nicht geladen")
        return
    themen = set(msg.get("themen") or EREIGNIS_THEMEN)
    abo = Abo(connection, msg["id"], themen, connection.user.id if connection.user else None)
    entfernen = hub.abo_hinzu(abo)
    connection.subscriptions[msg["id"]] = entfernen
    connection.send_result(msg["id"])
    for thema in EREIGNIS_THEMEN:
        if thema in themen:
            hub._sende(abo, thema, "snapshot", hub.snapshot(thema))


_HANDLER.append(ws_subscribe)


# --------------------------------------------------------------------------
# 3 bis 9: Serien und Folgen
# --------------------------------------------------------------------------


@befehl("serien/list")
async def ws_serien_list(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.serien_liste()


@befehl("serie/get", {**SERIE_ID})
async def ws_serie_get(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.serie_holen(msg["serie_id"])


@befehl("serie/create", {vol.Required("name"): _text, vol.Optional("typ"): vol.In(["normal", "ueberraschung"]), **ANFRAGE_ID}, admin=True)
async def ws_serie_create(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    async def tu() -> Any:
        return {"serie": await hub.medien.serie_anlegen(msg["name"], msg.get("typ", "normal"))}

    return await hub.mit_anfrage_id(msg.get("anfrage_id"), "serie/create", _felder(msg), tu)


@befehl("serie/rename", {**SERIE_ID, vol.Required("name"): _text}, admin=True)
async def ws_serie_rename(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return {"serie": await hub.medien.serie_umbenennen(msg["serie_id"], msg["name"])}


@befehl("folgen/order", {**SERIE_ID, vol.Required("folgen"): LISTE_TEXT, **STAND}, admin=True)
async def ws_folgen_order(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return {"serie": await hub.medien.folgen_ordnen(msg["serie_id"], msg["folgen"], msg.get("stand"))}


@befehl(
    "folge/delete",
    {**SERIE_ID, vol.Required("folge"): _text, vol.Optional("tobies_bestaetigt"): _wahrheit, **STAND},
    admin=True,
)
async def ws_folge_delete(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.folge_loeschen(msg["serie_id"], msg["folge"], msg.get("tobies_bestaetigt", False), msg.get("stand"))


@befehl("medien/pruefen", admin=True)
async def ws_medien_pruefen(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    await hub.medien._medien_erreichbar()
    gestartet, laeuft = hub.medien.pruefung_starten()
    return {"gestartet": gestartet, "laeuft_bereits": laeuft}


# --------------------------------------------------------------------------
# 10 bis 12: Papierkorb
# --------------------------------------------------------------------------


@befehl("papierkorb/list", {vol.Optional("limit"): _ganz(1, 200), vol.Optional("offset"): _ganz(0, 10_000_000)})
async def ws_papierkorb_list(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.papierkorb_liste(msg.get("limit", 100), msg.get("offset", 0))


@befehl("papierkorb/restore", {vol.Required("eintrag_id"): _text, vol.Optional("serie_id"): _text}, admin=True)
async def ws_papierkorb_restore(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.papierkorb_wiederherstellen(msg["eintrag_id"], msg.get("serie_id"))


@befehl("papierkorb/empty", {vol.Required("bestaetigt"): _wahr, vol.Optional("eintrag_ids"): LISTE_TEXT}, admin=True)
async def ws_papierkorb_empty(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.papierkorb_leeren(msg.get("eintrag_ids"))


# --------------------------------------------------------------------------
# 13 und 14: Neue Tobies
# --------------------------------------------------------------------------


@befehl("neue_tobies/list", {vol.Optional("limit"): _ganz(1, 200), vol.Optional("offset"): _ganz(0, 10_000_000)})
async def ws_neue_tobies_list(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return hub.neue_tobies_liste(msg.get("limit", 100), msg.get("offset", 0))


@befehl("neue_tobies/verwerfen", {vol.Required("uid"): _text}, admin=True)
async def ws_neue_tobies_verwerfen(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return hub.neue_tobies_verwerfen(msg["uid"])


# --------------------------------------------------------------------------
# 15 bis 17: Zuordnungen
# --------------------------------------------------------------------------


@befehl(
    "zuordnung/list",
    {vol.Optional("serie_id"): _text, vol.Optional("limit"): _ganz(1, 100), vol.Optional("offset"): _ganz(0, 10_000_000)},
)
async def ws_zuordnung_list(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.zuordnung_liste(msg.get("serie_id"), msg.get("limit", 100), msg.get("offset", 0))


@befehl(
    "zuordnung/set",
    {
        vol.Required("uid"): _text,
        vol.Required("ziel"): _objekt,
        vol.Optional("name"): vol.Any(None, _text),
        vol.Optional("ueberschreiben"): _wahrheit,
        vol.Optional("erwartet_ziel"): vol.Any(None, _objekt),
    },
    admin=True,
)
async def ws_zuordnung_set(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.zuordnung_setzen(
        msg["uid"],
        msg["ziel"],
        name=msg["name"] if "name" in msg else FEHLT,
        ueberschreiben=msg.get("ueberschreiben", False),
        erwartet_ziel=msg["erwartet_ziel"] if "erwartet_ziel" in msg else FEHLT,
    )


@befehl("zuordnung/remove", {vol.Required("uid"): _text, vol.Optional("erwartet_ziel"): vol.Any(None, _objekt)}, admin=True)
async def ws_zuordnung_remove(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.zuordnung_entfernen(msg["uid"], msg["erwartet_ziel"] if "erwartet_ziel" in msg else FEHLT)


# --------------------------------------------------------------------------
# 18 bis 20: Lernmodus
# --------------------------------------------------------------------------


@befehl(
    "lernmodus/start",
    {vol.Required("box"): _text, vol.Required("ziel"): _objekt, vol.Optional("name"): _text, **ANFRAGE_ID},
    admin=True,
)
async def ws_lernmodus_start(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    async def tu() -> Any:
        return await hub.lernmodus.start(msg["box"], msg["ziel"], msg.get("name"))

    return await hub.mit_anfrage_id(msg.get("anfrage_id"), "lernmodus/start", _felder(msg), tu)


@befehl("lernmodus/antwort", {vol.Required("befehl_id"): _text, vol.Required("ueberschreiben"): _wahrheit}, admin=True)
async def ws_lernmodus_antwort(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.lernmodus.antwort(msg["befehl_id"], msg["ueberschreiben"])


@befehl("lernmodus/abbrechen", {vol.Required("box"): _text}, admin=True)
async def ws_lernmodus_abbrechen(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return {"abgebrochen": await hub.lernmodus.abbrechen(msg["box"])}


# --------------------------------------------------------------------------
# 21 und 22: Boxen
# --------------------------------------------------------------------------


@befehl("boxen/list")
async def ws_boxen_list(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return {"boxen": hub.boxen_liste()}


@befehl("box/sync", {vol.Required("box"): _text, **ANFRAGE_ID}, admin=True)
async def ws_box_sync(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    async def tu() -> Any:
        return await hub.box_sync(msg["box"])

    return await hub.mit_anfrage_id(msg.get("anfrage_id"), "box/sync", _felder(msg), tu)


# --------------------------------------------------------------------------
# 23: Liste neu ausrollen
# --------------------------------------------------------------------------


@befehl("liste/neu_ausrollen", {vol.Required("bestaetigt"): _wahr, **ANFRAGE_ID}, admin=True)
async def ws_liste_neu_ausrollen(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    async def tu() -> Any:
        return await hub.liste_neu_ausrollen()

    return await hub.mit_anfrage_id(msg.get("anfrage_id"), "liste/neu_ausrollen", _felder(msg), tu)


# --------------------------------------------------------------------------
# 24 bis 28: Korrekturen (Entscheidung M)
# --------------------------------------------------------------------------


@befehl("serie/delete", {**SERIE_ID, vol.Optional("tobies_bestaetigt"): _wahrheit, **STAND}, admin=True)
async def ws_serie_delete(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.serie_loeschen(msg["serie_id"], msg.get("tobies_bestaetigt", False), msg.get("stand"))


@befehl("folge/rename", {**SERIE_ID, vol.Required("folge"): _text, vol.Required("name"): _text, **STAND}, admin=True)
async def ws_folge_rename(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.folge_umbenennen(msg["serie_id"], msg["folge"], msg["name"], msg.get("stand"))


@befehl(
    "folge/verschieben",
    {
        **SERIE_ID,
        vol.Required("folge"): _text,
        vol.Required("ziel_serie_id"): _text,
        vol.Optional("tobies_bestaetigt"): _wahrheit,
        **STAND,
    },
    admin=True,
)
async def ws_folge_verschieben(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.folge_verschieben(
        msg["serie_id"], msg["folge"], msg["ziel_serie_id"], msg.get("tobies_bestaetigt", False), msg.get("stand")
    )


@befehl(
    "serien/zusammenfuehren",
    {
        vol.Required("quelle_id"): _text,
        vol.Required("ziel_id"): _text,
        vol.Optional("tobies_bestaetigt"): _wahrheit,
        vol.Optional("stand_quelle"): _text,
        vol.Optional("stand_ziel"): _text,
    },
    admin=True,
)
async def ws_serien_zusammenfuehren(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.medien.serien_zusammenfuehren(
        msg["quelle_id"], msg["ziel_id"], msg.get("tobies_bestaetigt", False), msg.get("stand_quelle"), msg.get("stand_ziel")
    )


@befehl("einsortierung/bestaetigen", {**SERIE_ID, vol.Optional("folgen"): LISTE_TEXT}, admin=True)
async def ws_einsortierung_bestaetigen(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return {"serie": await hub.medien.bestaetigen(msg["serie_id"], msg.get("folgen"))}


# --------------------------------------------------------------------------
# 29 und 30: Eingang
# --------------------------------------------------------------------------


@befehl(
    "eingang/list",
    {
        vol.Optional("filter"): vol.In(["offen", "erledigt", "alle"]),
        vol.Optional("limit"): _ganz(1, 100),
        vol.Optional("offset"): _ganz(0, 10_000_000),
    },
)
async def ws_eingang_list(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.eingang.liste(msg.get("filter", "offen"), msg.get("limit", 50), msg.get("offset", 0))


@befehl("eingang/sortieren", {vol.Optional("eintrag_ids"): LISTE_TEXT, vol.Optional("sofort"): _wahrheit}, admin=True)
async def ws_eingang_sortieren(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.eingang.starte_durchlauf(msg.get("eintrag_ids"), msg.get("sofort", False))


# --------------------------------------------------------------------------
# 31 und 32: Sicherungsnetz der Konfiguration
# --------------------------------------------------------------------------


@befehl("konfig/export_lesen")
async def ws_konfig_export_lesen(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    return await hub.konfig_export_lesen()


@befehl("konfig/aus_export", {vol.Required("bestaetigt"): _wahr, **ANFRAGE_ID}, admin=True)
async def ws_konfig_aus_export(hub: Hub, connection: Any, msg: dict[str, Any]) -> Any:
    async def tu() -> Any:
        return await hub.konfig_aus_export()

    return await hub.mit_anfrage_id(msg.get("anfrage_id"), "konfig/aus_export", _felder(msg), tu)


# --------------------------------------------------------------------------


@callback
def async_register(hass: HomeAssistant) -> None:
    """Meldet alle Befehle bei HA an (einmal)."""
    for handler in _HANDLER:
        websocket_api.async_register_command(hass, handler)
