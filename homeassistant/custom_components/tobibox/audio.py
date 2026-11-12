"""Audio-Ansicht und ``audio/bereit`` (Vertrag W, 14.5; Design 11.4). Paket A0b: Original-Zweig, Hörkopien folgen in A-3.

* ``GET /api/tobibox/audio/{serie_id}/{folge_id}`` (optional ``?track=<n>``): Anmeldung **oder** gültige Signatur
  (``?authSig=``). Es kommt **kein Pfad von außen**: ``serie_id`` muss eine bekannte Serie sein, ``folge_id`` genau
  ein Eintrag in ``serie.folgen``, die Datei eines Ordners kommt aus der eigenen sortierten Trackliste. Der fertige
  Pfad wird aufgelöst (``resolve()``) und muss unter dem aufgelösten Medien-Pfad liegen.
* Antwort: Unterklasse von ``web.FileResponse`` (Range, ETag), die offenen Verbindungen je Benutzer zählt
  (hoch in ``prepare()``, frei im ``finally``).
* ``tobibox/audio/bereit``: in A0b eine Attrappe, die immer ``bereit`` sagt und den signierten Pfad liefert.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from aiohttp import web

from homeassistant.components import websocket_api
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant

from . import dateien
from .const import AUDIO_LINK_GUELTIG_S, AUDIO_VERBINDUNGEN_JE_BENUTZER, DOMAIN, ENDUNGEN, VERTRAG_V
from .fehler import TobiboxFehler
from .namen import sortiere_natuerlich

try:  # HA 2026.10 und neuer: ``probatio``; ältere Versionen: ``voluptuous``
    import probatio as vol
except ImportError:  # pragma: no cover
    import voluptuous as vol

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

AUDIO_URL = "/api/tobibox/audio"
_ZAEHLER = f"{DOMAIN}_audio_zaehler"

#: eigene Tabelle der Content-Types (Vertrag 14.5), nicht ``mimetypes``
CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "m4b": "audio/mp4",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
    "opus": "audio/ogg",
    "wav": "audio/wav",
}


def _fehler(code: str, text: str, status: int) -> web.Response:
    return web.json_response({"v": VERTRAG_V, "fehler": {"code": code, "text": text}}, status=status)


def _nicht_gefunden() -> web.Response:
    return _fehler("folge_nicht_gefunden", "Die Datei wurde nicht gefunden.", 404)


def _ist_systemname(name: str) -> bool:
    return name.startswith((".", "@", "#", "$", "_")) or name.lower() in ("eingang", "export", "releases", "hoerkopien")


def finde_datei(hub: Hub, serie_id: str, folge_id: str, track: int | None) -> Path | None:
    """Synchron (Executor): die Datei zu ``(serie_id, folge_id, track)`` oder ``None``. Verlässt nie den Medien-Pfad."""
    info = hub.medien.serien.get(serie_id)
    if info is None or folge_id not in info.serie.folgen or _ist_systemname(info.ordner):
        return None
    try:
        wurzel = hub.pfade.medien.resolve()
        ordner = wurzel / info.ordner
        kandidat = ordner / folge_id
        if kandidat.is_dir():
            tracks = sortiere_natuerlich(dateien.tracks_in_ordner(kandidat))
            nr = 0 if track is None else track
            if not 0 <= nr < len(tracks):
                return None
            kandidat = kandidat / tracks[nr]
        elif track not in (None, 0):
            return None
        fertig = kandidat.resolve()
        if not fertig.is_relative_to(wurzel) or not fertig.is_relative_to(ordner.resolve()):
            return None
        if not fertig.is_file() or fertig.suffix.lstrip(".").lower() not in ENDUNGEN:
            return None
    except (OSError, ValueError, RuntimeError):
        return None
    return fertig


def audio_pfad(serie_id: str, folge_id: str, track: int | None = None) -> str:
    """Der Pfad mit Kodierung je Segment (wie ``encodeURIComponent``, Vertrag 14.5)."""
    pfad = f"{AUDIO_URL}/{quote(serie_id, safe='')}/{quote(folge_id, safe='')}"
    return pfad if track is None else f"{pfad}?track={track}"


class AudioAntwort(web.FileResponse):
    """``FileResponse`` mit Zähler: hoch in ``prepare()``, frei im ``finally`` (der Handler gibt zu früh zurück)."""

    def __init__(self, pfad: Path, zaehler: dict[str, int], nutzer_id: str) -> None:
        super().__init__(
            pfad,
            headers={
                "Content-Type": CONTENT_TYPES[pfad.suffix.lstrip(".").lower()],
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, max-age=3600",
                "X-Tobibox-Quelle": "original",
            },
        )
        self._zaehler = zaehler
        self._nutzer_id = nutzer_id

    async def prepare(self, request: web.BaseRequest) -> Any:
        self._zaehler[self._nutzer_id] = self._zaehler.get(self._nutzer_id, 0) + 1
        try:
            return await super().prepare(request)
        finally:
            rest = self._zaehler.get(self._nutzer_id, 1) - 1
            if rest > 0:
                self._zaehler[self._nutzer_id] = rest
            else:
                self._zaehler.pop(self._nutzer_id, None)


class TobiboxAudioView(HomeAssistantView):
    """Audio-Ansicht: Anmeldung oder Signatur, Recht lesen (jeder angemeldete Benutzer)."""

    url = AUDIO_URL + "/{serie_id}/{folge_id}"
    name = "api:tobibox:audio"
    requires_auth = True
    cors_allowed = False

    async def get(self, request: web.Request, serie_id: str, folge_id: str) -> web.StreamResponse:
        hass = request.app[KEY_HASS]
        hub: Hub | None = hass.data.get(DOMAIN)
        if hub is None:
            return _fehler("unknown_error", "Die Integration ist nicht geladen.", 500)
        track: int | None = None
        if "track" in request.query:
            roh = request.query["track"]
            if not roh.isascii() or not roh.isdigit() or len(roh) > 6:
                return _nicht_gefunden()
            track = int(roh)
        try:
            await hub.medien._stelle_geprueft_sicher()
        except TobiboxFehler:
            return _fehler("medien_nicht_erreichbar", "Die Medien-Freigabe (NAS) ist gerade nicht erreichbar.", 503)
        pfad = await hass.async_add_executor_job(finde_datei, hub, serie_id, folge_id, track)
        if pfad is None:
            return _nicht_gefunden()
        nutzer_id = request["hass_user"].id
        zaehler: dict[str, int] = hass.data.setdefault(_ZAEHLER, {})
        if zaehler.get(nutzer_id, 0) >= AUDIO_VERBINDUNGEN_JE_BENUTZER:
            return _fehler("zu_viele_streams", "Es laufen schon zu viele Wiedergaben.", 429)
        return AudioAntwort(pfad, zaehler, nutzer_id)

    async def head(self, request: web.Request, serie_id: str, folge_id: str) -> web.StreamResponse:
        return await self.get(request, serie_id, folge_id)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tobibox/audio/bereit",
        vol.Required("serie_id"): str,
        vol.Required("folge_id"): str,
        vol.Optional("track"): vol.All(int, vol.Range(min=0, max=100000)),
    }
)
@websocket_api.async_response
async def ws_audio_bereit(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Attrappe (A0b): prüft, dass es die Datei gibt, und liefert den signierten Pfad (24 Stunden). Hörkopien: A-3."""
    hub: Hub | None = hass.data.get(DOMAIN)
    if hub is None:
        connection.send_error(msg["id"], "unknown_error", "Die Integration ist nicht geladen.")
        return
    try:
        await hub.medien._stelle_geprueft_sicher()
        track = msg.get("track")
        pfad = await hass.async_add_executor_job(finde_datei, hub, msg["serie_id"], msg["folge_id"], track)
        if pfad is None:
            raise TobiboxFehler("folge_nicht_gefunden")
    except TobiboxFehler as err:
        connection.send_error(msg["id"], err.code, hub.fehler_text(err))
        return
    signiert = async_sign_path(
        hass,
        audio_pfad(msg["serie_id"], msg["folge_id"], track),
        timedelta(seconds=AUDIO_LINK_GUELTIG_S),
        refresh_token_id=connection.refresh_token_id,
    )
    # ``async_sign_path`` gibt den Pfad entschlüsselt zurück; der Pfad wird hier je Segment neu kodiert
    # (Namen mit ``#``, ``?`` oder ``%`` bleiben so heil), die Abfrage mit der Signatur bleibt, wie sie ist.
    basis = audio_pfad(msg["serie_id"], msg["folge_id"])
    connection.send_result(
        msg["id"],
        {
            "v": VERTRAG_V,
            "zustand": "bereit",
            "pfad": f"{basis}?{signiert.partition('?')[2]}",
            "gueltig_s": AUDIO_LINK_GUELTIG_S,
            "quelle": "original",
        },
    )


def async_register(hass: HomeAssistant) -> None:
    """Meldet Ansicht und Befehl an (einmal je HA-Lauf)."""
    if hass.data.get(f"{DOMAIN}_audio_angemeldet"):
        return
    hass.http.register_view(TobiboxAudioView())
    websocket_api.async_register_command(hass, ws_audio_bereit)
    hass.data[f"{DOMAIN}_audio_angemeldet"] = True
