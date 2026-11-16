"""Audio-Ansicht und ``audio/bereit`` (Pakete A4c und A4c3; Vertrag W, Befehl 39 und 14.5; Design 11.4.1 und 11.4.2). Zwei getrennte Zweige:
**Original** (unter ``medien/``) und **Kopie** (die Hörkopie unter ``hoerkopien/``, ``hoerkopie.py``).

* ``GET /api/tobibox/audio/{serie_id}/{folge_id}`` (optional ``?track=<n>``): Anmeldung **oder** gültige Signatur
  (``?authSig=``). Es kommt **kein Pfad von außen**: ``serie_id`` muss eine bekannte Serie sein, ``folge_id`` genau
  ein Eintrag in ``serie.folgen``, die Datei eines Ordners kommt aus der eigenen sortierten Trackliste. Der fertige
  Pfad wird aufgelöst (``resolve()``) und muss unter dem aufgelösten Medien-Pfad (und unter dem Ordner der Serie) liegen.
* Antwort: Unterklasse von ``web.FileResponse`` (Range, ETag), die offenen Verbindungen je Benutzer zählt
  (hoch in ``prepare()``, frei im ``finally``). Fehler: 401 (macht HA), 404 ``folge_nicht_gefunden``, 429 ``zu_viele_streams``,
  503 ``medien_nicht_erreichbar``, 503 ``hoerkopie_wartet`` mit ``Retry-After: 60`` (nur Rückfall für Aufrufer ohne ``audio/bereit``).
* **Zweig Kopie (G6):** Braucht der Track nach seinem Codec eine Hörkopie (``hoerkopie.braucht_hoerkopie``) und gibt es ``ffmpeg``, kommt die Datei aus
  ``hoerkopien/<serie_id>/<kennung>.m4a``. Der Pfad entsteht **nur** aus der eigenen ``serie_id`` und der Kennung (nie aus der Anfrage), wird aufgelöst und
  muss unter ``hoerkopien/`` liegen; eine Kopie ist über keine andere ``serie_id`` erreichbar. Antwortkopf ``X-Tobibox-Quelle: kopie``, ``audio/mp4``.
* ``tobibox/audio/bereit`` (``bereit()``): Zustand (``bereit``, ``wird_vorbereitet``, ``fehlt``) und signierter Pfad (24 Stunden). Der WebSocket-Befehl selbst
  steht in ``websocket_api.py``.
* Bricht der Client eine Übertragung ab (Spulen, Folgenwechsel), endet das still: ``AudioAntwort.prepare`` macht aus dem Folgefehler von asyncio
  (``AttributeError`` im ``sslproto`` beim Aufräumen der geschlossenen Verbindung) ein ``ConnectionResetError``, das aiohttp leise ignoriert.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from aiohttp import web

from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.http.auth import async_sign_path

from . import dateien
from .const import (
    AUDIO_BEREIT_JE_MINUTE,
    AUDIO_LINK_GUELTIG_S,
    AUDIO_VERBINDUNGEN_JE_BENUTZER,
    DOMAIN,
    ENDUNGEN,
    VERTRAG_V,
)
from .fehler import TobiboxFehler
from .namen import sortiere_natuerlich
from .schutz import MINUTE_S, Nutzer

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


#: Content-Type der Hörkopie (AAC in M4A, Vertrag W, 14.5)
KOPIE_CONTENT_TYPE = "audio/mp4"


def _fehler(hub: Hub | None, code: str, status: int) -> web.Response:
    """JSON-Fehler wie beim Upload (``{"v", "fehler": {"code", "text"}}``). Der Text nennt nie einen Pfad."""
    text = hub.fehler_text(TobiboxFehler(code)) if hub is not None else code
    return web.json_response({"v": VERTRAG_V, "fehler": {"code": code, "text": text}}, status=status)


def _ist_systemname(name: str) -> bool:
    """Systemordner (``_papierkorb``, ``_upload``, ``eingang``, ``export``, ``releases``, ``hoerkopien``, alles mit ``.``, ``@``, ``#``, ``$``
    am Anfang) sind nie eine Serie, also nie erreichbar (Vertrag W, 14.5, Punkt 6)."""
    return name.startswith((".", "@", "#", "$", "_")) or name.lower() in ("eingang", "export", "releases", "hoerkopien")


#: ``suche_datei``: Ergebnis ohne Datei
NICHT_DA = "nicht_da"
WEG = "weg"


def suche_datei(hub: Hub, serie_id: str, folge_id: str, track: int | None) -> tuple[str, Path | None]:
    """Synchron (Executor): ``("ok", Datei)``, ``(NICHT_DA, None)`` oder ``(WEG, None)`` (die Freigabe ist nicht erreichbar).

    Verlässt nie den Medien-Pfad: die Serie kommt aus dem Index (nie aus einem Pfad), die Folge muss **genau** in ``serie.folgen`` stehen, bei
    einem Ordner kommt die Datei aus der eigenen sortierten Trackliste; der fertige Pfad wird aufgelöst und muss unter dem Medien-Pfad **und**
    unter dem Ordner der Serie liegen (ein Link aus dem Medien-Pfad hinaus ist damit 404)."""
    try:
        wurzel = hub.pfade.medien.resolve()
        if not wurzel.is_dir():
            return WEG, None
    except OSError:
        return WEG, None
    info = hub.medien.serien.get(serie_id)
    if info is None or folge_id not in info.serie.folgen or _ist_systemname(info.ordner):
        return NICHT_DA, None
    try:
        ordner = wurzel / info.ordner
        kandidat = ordner / folge_id
        if kandidat.is_dir():
            tracks = sortiere_natuerlich(dateien.tracks_in_ordner(kandidat))
            nr = 0 if track is None else track
            if not 0 <= nr < len(tracks):
                return NICHT_DA, None
            kandidat = kandidat / tracks[nr]
        elif track not in (None, 0):
            return NICHT_DA, None
        fertig = kandidat.resolve()
        if not fertig.is_relative_to(wurzel) or not fertig.is_relative_to(ordner.resolve()):
            return NICHT_DA, None
        if not fertig.is_file() or fertig.suffix.lstrip(".").lower() not in ENDUNGEN:
            return NICHT_DA, None
    except (OSError, ValueError, RuntimeError):
        return NICHT_DA, None
    return "ok", fertig


def finde_datei(hub: Hub, serie_id: str, folge_id: str, track: int | None) -> Path | None:
    """Wie ``suche_datei``, nur die Datei oder ``None`` (für das Testpanel)."""
    return suche_datei(hub, serie_id, folge_id, track)[1]


def audio_pfad(serie_id: str, folge_id: str, track: int | None = None) -> str:
    """Der Pfad mit Kodierung je Segment (wie ``encodeURIComponent``, Vertrag 14.5)."""
    pfad = f"{AUDIO_URL}/{quote(serie_id, safe='')}/{quote(folge_id, safe='')}"
    return pfad if track is None else f"{pfad}?track={track}"


def _verbindung_weg(request: web.BaseRequest) -> bool:
    """Ist die Verbindung des Clients weg oder wird sie geschlossen? (aiohttp setzt ``transport`` auf ``None``, sobald sie verloren ist.)"""
    transport = request.transport
    return transport is None or transport.is_closing()


class AudioAntwort(web.FileResponse):
    """``FileResponse`` mit Zähler: hoch in ``prepare()``, frei im ``finally`` (der Handler gibt zu früh zurück, ``FileResponse`` sendet erst danach)."""

    def __init__(self, pfad: Path, zaehler: dict[str, int], nutzer_id: str, quelle: str = "original") -> None:
        super().__init__(
            pfad,
            headers={
                "Content-Type": KOPIE_CONTENT_TYPE if quelle == "kopie" else CONTENT_TYPES[pfad.suffix.lstrip(".").lower()],
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "private, max-age=3600",
                "X-Tobibox-Quelle": quelle,
            },
        )
        self._zaehler = zaehler
        self._nutzer_id = nutzer_id

    async def prepare(self, request: web.BaseRequest) -> Any:
        self._zaehler[self._nutzer_id] = self._zaehler.get(self._nutzer_id, 0) + 1
        try:
            return await super().prepare(request)
        except AttributeError as err:
            # Der Client hat abgebrochen (Spulen, Folgenwechsel): ``loop.sendfile`` räumt über ``set_protocol`` auf, die SSL-Verbindung ist schon zu
            # (``'NoneType' object has no attribute '_set_app_protocol'``). Nur dieser Fall, erkannt am toten Transport, endet still; jeder andere
            # ``AttributeError`` (Fehler im Code) bleibt sichtbar.
            if _verbindung_weg(request):
                raise ConnectionResetError("Der Client hat den Abruf abgebrochen") from err
            raise
        finally:
            rest = self._zaehler.get(self._nutzer_id, 1) - 1
            if rest > 0:
                self._zaehler[self._nutzer_id] = rest
            else:
                self._zaehler.pop(self._nutzer_id, None)


class TobiboxAudioView(HomeAssistantView):
    """Audio-Ansicht: Anmeldung oder Signatur, Recht lesen (jeder angemeldete Benutzer). Nur GET (und HEAD)."""

    url = AUDIO_URL + "/{serie_id}/{folge_id}"
    name = "api:tobibox:audio"
    requires_auth = True
    cors_allowed = False

    async def get(self, request: web.Request, serie_id: str, folge_id: str) -> web.StreamResponse:
        hass = request.app[KEY_HASS]
        hub: Hub | None = hass.data.get(DOMAIN)
        if hub is None:
            return _fehler(None, "unknown_error", 500)
        track: int | None = None
        if "track" in request.query:
            roh = request.query["track"]
            if not roh.isascii() or not roh.isdigit() or len(roh) > 6:
                return _fehler(hub, "folge_nicht_gefunden", 404)
            track = int(roh)
        try:
            await hub.medien._stelle_geprueft_sicher()
        except TobiboxFehler:
            return _fehler(hub, "medien_nicht_erreichbar", 503)
        ergebnis, pfad = await hass.async_add_executor_job(suche_datei, hub, serie_id, folge_id, track)
        if ergebnis == WEG:
            return _fehler(hub, "medien_nicht_erreichbar", 503)
        if pfad is None:
            return _fehler(hub, "folge_nicht_gefunden", 404)
        quelle = "original"
        if hub.hoerkopie.verfuegbar:
            nr = track or 0
            if await hub.hoerkopie.braucht_kopie(serie_id, folge_id, nr, pfad):
                kopie = await hub.hoerkopie.kopie_datei(serie_id, folge_id, nr, pfad)  # Zweig Kopie: nur aus ``serie_id`` und Kennung
                if kopie is None:
                    antwort = _fehler(hub, "hoerkopie_wartet", 503)
                    antwort.headers["Retry-After"] = "60"
                    return antwort
                pfad, quelle = kopie, "kopie"
        nutzer_id = request["hass_user"].id
        zaehler: dict[str, int] = hass.data.setdefault(_ZAEHLER, {})
        if zaehler.get(nutzer_id, 0) >= AUDIO_VERBINDUNGEN_JE_BENUTZER:
            return _fehler(hub, "zu_viele_streams", 429)
        return AudioAntwort(pfad, zaehler, nutzer_id, quelle)

    async def head(self, request: web.Request, serie_id: str, folge_id: str) -> web.StreamResponse:
        return await self.get(request, serie_id, folge_id)


async def bereit(
    hub: Hub,
    nutzer: Nutzer,
    refresh_token_id: str | None,
    serie_id: str,
    folge: str,
    track: int | None = None,
    vorbereiten: bool = True,
) -> dict[str, Any]:
    """``tobibox/audio/bereit`` (Vertrag W, Nr. 39): ``bereit`` mit signiertem Pfad (24 Stunden) und ``quelle`` ``original`` oder ``kopie``;
    ``wird_vorbereitet`` (``warte_s``, ``position``), solange die Hörkopie in der Schlange steht; ``fehlt`` mit ``grund``. Fehler:
    ``serie_nicht_gefunden``, ``folge_nicht_gefunden``, ``hoerkopie_warteschlange_voll``, ``zu_viele_aenderungen`` (6 Aufrufe je Minute und
    Benutzer, nicht für Administratoren).

    Braucht der Track eine Hörkopie (nach seinem Codec, ``hoerkopie.braucht_hoerkopie``) und gibt es ``ffmpeg``, stößt ``vorbereiten=True`` sie an (der Bestand
    erst jetzt, auf Anforderung); mit ``vorbereiten=False`` wird nur der Zustand gelesen. Ohne ``ffmpeg`` (keine Fähigkeit ``hoerkopie``) bleibt es beim
    Original: die Seite prüft dann mit ``canPlayType``.

    Jeder Aufruf zählt (auch ein Fehlschlag): die Grenze schützt vor einer Seite, die in einer Schleife fragt."""
    hub.schutz.mengen.pruefe("audio_bereit", nutzer, AUDIO_BEREIT_JE_MINUTE, MINUTE_S)
    hub.schutz.mengen.buche_fuer("audio_bereit", nutzer)
    try:
        await hub.medien._stelle_geprueft_sicher()
    except TobiboxFehler:
        return {"zustand": "fehlt", "grund": "medien_nicht_erreichbar"}
    hub.medien.finde(serie_id)  # serie_nicht_gefunden
    ergebnis, pfad = await hub.hass.async_add_executor_job(suche_datei, hub, serie_id, folge, track)
    if ergebnis == WEG:
        return {"zustand": "fehlt", "grund": "medien_nicht_erreichbar"}
    if pfad is None:
        raise TobiboxFehler("folge_nicht_gefunden")
    quelle = "original"
    if hub.hoerkopie.verfuegbar:
        nr = track or 0
        if await hub.hoerkopie.braucht_kopie(serie_id, folge, nr, pfad):
            erg = await hub.hoerkopie.anfordern(nutzer.id, serie_id, folge, nr, pfad, vorbereiten)
            if erg["zustand"] != "fertig":
                return erg
            quelle = "kopie"
    signiert = async_sign_path(
        hub.hass,
        audio_pfad(serie_id, folge, track),
        timedelta(seconds=AUDIO_LINK_GUELTIG_S),
        refresh_token_id=refresh_token_id,
    )
    # ``async_sign_path`` gibt den Pfad entschlüsselt zurück (ein ``?`` im Namen steht darin als ``?``): der Pfad wird hier je Segment neu
    # kodiert (Namen mit ``#``, ``?`` oder ``%`` bleiben so heil). Die Abfrage (``track``, ``authSig``) steht nach dem **letzten** ``?``;
    # sie enthält selbst nie eines (Zahl und JWT aus ``[A-Za-z0-9._-]``).
    return {"zustand": "bereit", "pfad": f"{audio_pfad(serie_id, folge)}?{signiert.rpartition('?')[2]}", "quelle": quelle}


def async_register_views(hass: Any) -> None:
    """Meldet die Ansicht an (einmal je HA-Lauf; Ansichten lassen sich nicht abmelden)."""
    if hass.data.get(f"{DOMAIN}_audio_angemeldet"):
        return
    hass.http.register_view(TobiboxAudioView())
    hass.data[f"{DOMAIN}_audio_angemeldet"] = True
