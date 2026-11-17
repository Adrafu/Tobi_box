"""Export der Hördaten als Tabelle: Befehl 53 und die Ansicht für den Abruf (Stufe B, Paket B3; Vertrag W, Nr. 53).

* ``tobibox/gehoert/exportieren`` (Recht admin) prüft ``quelle`` und gibt einen **signierten Pfad** zurück: ``/api/tobibox/export/<Benutzer-ID>/<quelle>`` mit
  ``?authSig=…`` (10 Minuten, an die Anmeldung des Anfragenden gebunden, wie bei der Audio-Ansicht).
* ``GET /api/tobibox/export/<Benutzer-ID>/<quelle>``: Anmeldung oder gültige Signatur (macht HA, abgelaufen: 401). Die Ansicht prüft **zusätzlich**, dass der
  Benutzer Administrator ist und derselbe wie im Pfad (also wie beim Befehl). Die Datei entsteht **beim Abruf**: CSV, UTF-8 mit BOM, Trenner ``;``.

B3-OFFEN: Der Vertrag nennt nur „``GET /api/tobibox/export/<pfad>``“; die Form des Pfades (Benutzer-ID und Quelle als zwei Segmente) ist die naheliegende Wahl.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any
from urllib.parse import quote

from aiohttp import web

from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.http.auth import async_sign_path

from .const import DOMAIN, GEHOERT_EXPORT_LINK_S, VERTRAG_V
from .fehler import TobiboxFehler

_LOGGER = logging.getLogger(__name__)

EXPORT_URL = "/api/tobibox/export"
_ANGEMELDET = f"{DOMAIN}_export_angemeldet"


def export_pfad(nutzer_id: str, quelle: str) -> str:
    """Der Pfad mit Kodierung je Segment (``:`` in ``box:box1`` wird ``%3A``)."""
    return f"{EXPORT_URL}/{quote(nutzer_id, safe='')}/{quote(quelle, safe='')}"


def signierter_export_pfad(hass: Any, nutzer_id: str, quelle: str, refresh_token_id: str | None) -> str:
    """Der Pfad mit ``authSig`` (``GEHOERT_EXPORT_LINK_S`` gültig). ``async_sign_path`` gibt den Pfad entschlüsselt zurück: Die Abfrage nach dem letzten ``?``
    wird an den selbst kodierten Pfad gehängt (wie bei ``audio/bereit``)."""
    signiert = async_sign_path(hass, export_pfad(nutzer_id, quelle), timedelta(seconds=GEHOERT_EXPORT_LINK_S), refresh_token_id=refresh_token_id)
    return f"{export_pfad(nutzer_id, quelle)}?{signiert.rpartition('?')[2]}"


def _fehler(hub: Any, code: str, status: int) -> web.Response:
    text = code
    if hub is not None:
        try:
            text = hub.fehler_text(TobiboxFehler(code))
        except Exception:  # pragma: no cover
            text = code
    return web.json_response({"v": VERTRAG_V, "code": code, "message": text}, status=status)


class TobiboxExportView(HomeAssistantView):
    """Abruf der Tabelle: Administrator und derselbe Benutzer wie beim Befehl; nur GET."""

    url = EXPORT_URL + "/{nutzer_id}/{quelle}"
    name = "api:tobibox:export"
    requires_auth = True
    cors_allowed = False

    async def get(self, request: web.Request, nutzer_id: str, quelle: str) -> web.StreamResponse:
        hass = request.app[KEY_HASS]
        hub = hass.data.get(DOMAIN)
        benutzer = request.get("hass_user")
        if benutzer is None or not benutzer.is_admin or benutzer.id != nutzer_id:
            return _fehler(hub, "unauthorized", 401)
        if hub is None or not hub.gehoert.verfuegbar:
            return _fehler(hub, "unknown_error", 503)
        try:
            inhalt, dateiname = await hub.gehoert.abfrage.export_csv(quelle)
        except TobiboxFehler as err:
            return _fehler(hub, err.code, err.http_status)
        return web.Response(
            body=inhalt,
            headers={
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": f'attachment; filename="{dateiname}"',
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )


def async_register_views(hass: Any) -> None:
    """Meldet die Ansicht an (einmal je HA-Lauf; Ansichten lassen sich nicht abmelden)."""
    if hass.data.get(_ANGEMELDET):
        return
    hass.http.register_view(TobiboxExportView())
    hass.data[_ANGEMELDET] = True
