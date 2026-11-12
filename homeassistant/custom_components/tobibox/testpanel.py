"""Testpanel und Messungen (Paket A0b, Design 15 Zeile A0b). Alles hier verschwindet mit ``const.TESTPANEL = False``.

* Mess-Endpunkt ``POST /api/tobibox/testpanel/messung``: nur Administratoren; zählt die Bytes des Körpers und
  **verwirft** sie (nichts wird gespeichert); Grenze ``MESS_UPLOAD_MAX_BYTES``.
* Befehl ``tobibox/testpanel/ffmpeg_messen``: nur Administratoren; ``ffmpeg -version``, AAC-Encoder und das Umwandeln
  von 10 Minuten einer Bibliotheksdatei nach AAC 96 kbit/s nach ``/dev/null``, im Executor mit Zeitgrenzen.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aiohttp import web

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.http.decorators import require_admin
from homeassistant.core import HomeAssistant

from . import audio
from .const import (
    DOMAIN,
    FFPROBE_SPEICHER_BYTES,
    FORMAT_JE_ENDUNG,
    MESS_FFMPEG_AUDIO_S,
    MESS_FFMPEG_KURZ_ZEITGRENZE_S,
    MESS_FFMPEG_ZEITGRENZE_S,
    MESS_UPLOAD_MAX_BYTES,
    VERTRAG_V,
)
from .fehler import TobiboxFehler

try:  # HA 2026.10 und neuer: ``probatio``; ältere Versionen: ``voluptuous``
    import probatio as vol
except ImportError:  # pragma: no cover
    import voluptuous as vol

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

PANEL_URL = "tobibox-neu"
PANEL_ELEMENT = "tobibox-testpanel"
PANEL_DATEI = "tobibox-testpanel.js"
MESS_URL = "/api/tobibox/testpanel/messung"


# --------------------------------------------------------------------------
# Mess-Endpunkt: Bytes zählen und verwerfen
# --------------------------------------------------------------------------


class TobiboxMessView(HomeAssistantView):
    url = MESS_URL
    name = "api:tobibox:testpanel:messung"
    requires_auth = True
    cors_allowed = False

    @require_admin
    async def post(self, request: web.Request) -> web.Response:
        laenge = request.content_length
        if laenge is not None and laenge > MESS_UPLOAD_MAX_BYTES:
            return _zu_gross()
        start = time.monotonic()
        gesamt = 0
        async for block in request.content.iter_chunked(1024 * 1024):
            gesamt += len(block)
            if gesamt > MESS_UPLOAD_MAX_BYTES:
                return _zu_gross()
        return web.json_response({"v": VERTRAG_V, "bytes": gesamt, "sekunden": round(time.monotonic() - start, 3)})


def _zu_gross() -> web.Response:
    return web.json_response(
        {"v": VERTRAG_V, "fehler": {"code": "datei_zu_gross", "text": "Die Datei ist größer als 2 GiB."}}, status=413
    )


# --------------------------------------------------------------------------
# ffmpeg-Messung
# --------------------------------------------------------------------------


def ffmpeg_programm(hass: HomeAssistant) -> tuple[str | None, str]:
    """``(Pfad, Quelle)``: Erstwahl ``get_ffmpeg_manager(hass).binary`` (nur wenn die Integration ``ffmpeg`` geladen ist),
    sonst ``shutil.which("ffmpeg")``. Pfad ``None``, wenn es kein ``ffmpeg`` gibt."""
    try:
        from homeassistant.components.ffmpeg import get_ffmpeg_manager

        binary = get_ffmpeg_manager(hass).binary
        if binary and shutil.which(binary):
            return shutil.which(binary), "ffmpeg-Integration"
    except (ImportError, ValueError, KeyError, AttributeError):
        pass
    gefunden = shutil.which("ffmpeg")
    return gefunden, "PATH"


def _speichergrenze() -> None:  # pragma: no cover - läuft im Kindprozess
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (FFPROBE_SPEICHER_BYTES * 2, FFPROBE_SPEICHER_BYTES * 2))
    except (ImportError, ValueError, OSError):
        pass


def _lauf(args: list[str], zeit_s: int) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(  # noqa: S603
            args,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=zeit_s,
            check=False,
            preexec_fn=_speichergrenze if os.name == "posix" else None,  # noqa: PLW1509
        )
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return None


def messe_ffmpeg(programm: str, quelle: str, datei: Path | None) -> dict[str, Any]:
    """Synchron (Executor). Alle Aufrufe mit Liste von Argumenten, Zeitgrenze und ohne Shell."""
    aus: dict[str, Any] = {"ffmpeg": True, "quelle": quelle, "version": None, "aac_encoder": [], "umwandlung": None}
    r = _lauf([programm, "-hide_banner", "-version"], MESS_FFMPEG_KURZ_ZEITGRENZE_S)
    if r is None or r.returncode != 0:
        aus["meldung"] = "ffmpeg lässt sich nicht starten."
        return aus
    aus["version"] = (r.stdout.splitlines() or [""])[0]
    r = _lauf([programm, "-hide_banner", "-encoders"], MESS_FFMPEG_KURZ_ZEITGRENZE_S)
    if r is not None and r.returncode == 0:
        aus["aac_encoder"] = [z.strip() for z in r.stdout.splitlines() if "aac" in z.lower() and z.startswith(" ")]
    if datei is None:
        return aus
    endung = datei.suffix.lstrip(".").lower()
    args = [
        programm, "-nostdin", "-y", "-v", "error", "-nostats", "-progress", "pipe:1",
        "-protocol_whitelist", "file", "-f", FORMAT_JE_ENDUNG[endung],
        "-t", str(MESS_FFMPEG_AUDIO_S), "-i", f"file:{datei}",
        "-vn", "-c:a", "aac", "-b:a", "96k", "-f", "adts", "/dev/null",
    ]  # fmt: skip
    start = time.monotonic()
    r = _lauf(args, MESS_FFMPEG_ZEITGRENZE_S)
    sekunden = time.monotonic() - start
    if r is None:
        aus["umwandlung"] = {"zustand": "zeitgrenze", "sekunden": round(sekunden, 1)}
        return aus
    if r.returncode != 0:
        letzte = (r.stderr.strip().splitlines() or ["?"])[-1].replace(str(datei), "<Datei>")
        aus["umwandlung"] = {"zustand": "fehler", "sekunden": round(sekunden, 1), "text": letzte[:200]}
        return aus
    audio_s = 0.0
    for zeile in r.stdout.splitlines():
        if zeile.startswith("out_time_us="):
            try:
                audio_s = max(audio_s, int(zeile.partition("=")[2]) / 1_000_000)
            except ValueError:
                pass
    aus["umwandlung"] = {
        "zustand": "ok",
        "sekunden": round(sekunden, 2),
        "audio_s": round(audio_s, 1),
        "faktor": round(audio_s / sekunden, 1) if sekunden > 0 and audio_s > 0 else None,
    }
    return aus


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "tobibox/testpanel/ffmpeg_messen",
        vol.Optional("serie_id"): str,
        vol.Optional("folge_id"): str,
        vol.Optional("track"): vol.All(int, vol.Range(min=0, max=100000)),
    }
)
@websocket_api.async_response
async def ws_ffmpeg_messen(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    hub: Hub | None = hass.data.get(DOMAIN)
    if hub is None:
        connection.send_error(msg["id"], "unknown_error", "Die Integration ist nicht geladen.")
        return
    programm, quelle = ffmpeg_programm(hass)
    if programm is None:
        connection.send_result(msg["id"], {"v": VERTRAG_V, "ffmpeg": False, "meldung": "ffmpeg wurde nicht gefunden."})
        return
    datei: Path | None = None
    if "serie_id" in msg or "folge_id" in msg:
        try:
            await hub.medien._stelle_geprueft_sicher()
            datei = await hass.async_add_executor_job(
                audio.finde_datei, hub, msg.get("serie_id", ""), msg.get("folge_id", ""), msg.get("track")
            )
            if datei is None:
                raise TobiboxFehler("folge_nicht_gefunden")
        except TobiboxFehler as err:
            connection.send_error(msg["id"], err.code, hub.fehler_text(err))
            return
    ergebnis = await hass.async_add_executor_job(messe_ffmpeg, programm, quelle, datei)
    connection.send_result(msg["id"], {"v": VERTRAG_V, **ergebnis})


# --------------------------------------------------------------------------
# Anmeldung
# --------------------------------------------------------------------------


def async_register_views(hass: HomeAssistant) -> None:
    """Ansichten und Befehle (einmal je HA-Lauf; sie lassen sich nicht abmelden)."""
    if hass.data.get(f"{DOMAIN}_testpanel_angemeldet"):
        return
    audio.async_register(hass)
    hass.http.register_view(TobiboxMessView())
    websocket_api.async_register_command(hass, ws_ffmpeg_messen)
    hass.data[f"{DOMAIN}_testpanel_angemeldet"] = True


async def async_register_panel(hass: HomeAssistant, frontend_pfad: Path, static_url: str, version: str) -> None:
    """Die Seite ``/tobibox-neu`` (nur Administratoren). Die alte Seite bleibt unberührt."""
    if not (frontend_pfad / PANEL_DATEI).is_file():
        _LOGGER.warning("Das Testpanel %s fehlt", frontend_pfad / PANEL_DATEI)
        return
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="Tobi Box (Test)",
        sidebar_icon="mdi:flask-outline",
        module_url=f"{static_url}/{PANEL_DATEI}?v={version}",
        embed_iframe=False,
        require_admin=True,
    )


def async_remove_panel(hass: HomeAssistant) -> None:
    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
