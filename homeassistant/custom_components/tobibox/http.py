"""Upload in den Eingang (Vertrag W, Abschnitt 5).

``POST /api/tobibox/upload``, ``multipart/form-data``, eine Datei je Anfrage. Der Körper wird **nie ganz
gelesen**: nur im Strom (``request.multipart()`` und ``part.read_chunk``), weil HA normale Anfragen auf 16 MiB
begrenzt. Zwei Phasen mit verschiedenem Verhalten bei Abbruch (W-03):

* **Phase A, Empfang:** Blöcke zu 1 MiB in eine Zwischendatei ``medien/_upload/<Zufall>.part``. Bricht die
  Verbindung ab, wird die Zwischendatei sofort gelöscht, es ist nichts entstanden.
* **Phase B, Abschluss:** eigene Aufgabe, die der Handler mit ``asyncio.shield`` abwartet. Ein Abbruch des
  Handlers halbiert den Abschluss nie: Prüfung, Umbenennen ohne Überschreiben (unter der Sperre des Eingangs),
  Ergebnis merken, Ereignis, Einsortieren anstoßen.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aiohttp import web

from homeassistant.components.http import KEY_HASS, HomeAssistantView

from . import dateien, ffprobe
from .const import (
    DOMAIN,
    ENDUNGEN,
    RE_UPLOAD_ID,
    UPLOAD_BLOCK_BYTES,
    UPLOAD_ERGEBNIS_ANZAHL,
    UPLOAD_ERGEBNIS_MERKEN_S,
    UPLOAD_PARALLEL,
    UPLOAD_RESERVE_BYTES,
    VERTRAG_V,
)
from .fehler import TobiboxFehler
from .schutz import Nutzer
from .namen import NamenErschoepft, dateiname_bereinigen, eindeutiger_name, vergleichsschluessel

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

EINGANG_ORDNER_PRAEFIX = "Upload "


def _fehler_antwort(hub: Hub, code: str, status: int | None = None) -> web.Response:
    err = TobiboxFehler(code)
    return web.json_response(
        {"v": VERTRAG_V, "fehler": {"code": code, "text": hub.fehler_text(err)}},
        status=status or err.http_status,
    )


class TobiboxUploadView(HomeAssistantView):
    """Der Upload-Endpunkt (jeder angemeldete Benutzer; Recht „alltag“, Vertrag W, 2.1; Schutzgrenzen in 2.4)."""

    url = "/api/tobibox/upload"
    name = "api:tobibox:upload"
    requires_auth = True
    cors_allowed = False

    async def post(self, request: web.Request) -> web.StreamResponse:
        hass = request.app[KEY_HASS]
        hub: Hub | None = hass.data.get(DOMAIN)
        if hub is None:
            return web.json_response({"v": VERTRAG_V, "fehler": {"code": "unknown_error", "text": "nicht geladen"}}, status=500)
        nutzer = Nutzer.aus_user(request["hass_user"])
        # (a) höchstens zwei Uploads gleichzeitig
        if hub.upload_zaehler >= UPLOAD_PARALLEL:
            return _fehler_antwort(hub, "zu_viele_uploads")
        hub.upload_zaehler += 1
        try:
            return await _empfange(hub, request, nutzer)
        finally:
            hub.upload_zaehler -= 1


def _fsync_und_schliessen(f: Any) -> None:
    f.flush()
    os.fsync(f.fileno())
    f.close()


def _loesche_leise(pfad: Path) -> None:
    with contextlib.suppress(OSError):
        pfad.unlink()


async def _lies_feld(part: Any) -> str:
    """Ein kleines Textfeld (höchstens 64 Zeichen, sonst ungültig)."""
    daten = await part.read_chunk(200)
    await part.release()
    return daten.decode("utf-8", "replace").strip()


async def _verwerfe_rest(part: Any) -> None:
    """Liest den Rest des Teils ``datei`` im Strom und wirft ihn weg (der Client bekommt dann seine Antwort)."""
    while await part.read_chunk(UPLOAD_BLOCK_BYTES):
        pass


async def _empfange(hub: Hub, request: web.Request, nutzer: Nutzer) -> web.StreamResponse:
    hass = hub.hass
    nutzer_id = nutzer.id
    # Menge je Stunde (Vertrag W, 2.4): Administratoren sind ausgenommen (``rest`` ist dann ``None``)
    rest = hub.schutz.upload_rest(nutzer)
    # (b) vor dem Körper: Größe und Platz
    laenge = request.content_length
    if laenge is not None and laenge > hub.upload_max_bytes:
        return _fehler_antwort(hub, "datei_zu_gross")
    if rest is not None and laenge is not None and laenge > rest:
        return _fehler_antwort(hub, "zu_viele_aenderungen")
    if not await hass.async_add_executor_job(hub.pfade.eingang.is_dir) or not await hass.async_add_executor_job(
        hub.pfade.medien.is_dir
    ):
        return _fehler_antwort(hub, "medien_nicht_erreichbar")
    if laenge is not None:
        try:
            frei = await hass.async_add_executor_job(dateien.freier_platz, hub.pfade.eingang)
        except OSError:
            return _fehler_antwort(hub, "medien_nicht_erreichbar")
        if laenge + UPLOAD_RESERVE_BYTES > frei:
            return _fehler_antwort(hub, "kein_speicher")

    try:
        reader = await request.multipart()
    except (AssertionError, KeyError, ValueError):
        return _fehler_antwort(hub, "invalid_format")
    felder: dict[str, str] = {}
    part = None
    while True:
        part = await reader.next()
        if part is None:
            return _fehler_antwort(hub, "invalid_format")
        if part.name == "datei":
            break
        if part.name in ("upload_id", "serie_id", "gruppe"):
            felder[part.name] = await _lies_feld(part)
        else:
            await part.release()
    upload_id = felder.get("upload_id") or None
    serie_id = felder.get("serie_id") or None
    gruppe = felder.get("gruppe") or None
    if upload_id is not None and not RE_UPLOAD_ID.match(upload_id):
        return _fehler_antwort(hub, "invalid_format")
    if gruppe is not None and not RE_UPLOAD_ID.match(gruppe):
        return _fehler_antwort(hub, "invalid_format")

    # Wiederholung mit gleicher upload_id: das alte Ergebnis (Vertrag W, 5.6)
    _alte_ergebnisse_aufraeumen(hub)
    if upload_id and upload_id in hub.uploads_laufend:
        return _fehler_antwort(hub, "upload_laeuft")
    if upload_id and upload_id in hub.upload_ergebnisse:
        await _verwerfe_rest(part)
        return web.json_response({**hub.upload_ergebnisse[upload_id][1], "wiederholt": True})

    # Endung und Name, bevor ein Byte der Datei gelesen wird
    dateiname = part.filename
    if not isinstance(dateiname, str) or not dateiname:
        return _fehler_antwort(hub, "invalid_format")
    endung = ffprobe.endung_von(dateiname)
    if endung not in ENDUNGEN:
        return _fehler_antwort(hub, "format_nicht_erlaubt")
    name, _stark = dateiname_bereinigen(dateiname)
    if not name:
        return _fehler_antwort(hub, "name_ungueltig")
    if ffprobe.endung_von(name) not in ENDUNGEN:  # z. B. ".mp3": die Bereinigung entfernt den führenden Punkt, die Endung bleibt
        name = f"{name}.{endung}"
    if serie_id is not None:
        try:
            await hub.medien._stelle_geprueft_sicher()
        except TobiboxFehler as err:
            return _fehler_antwort(hub, err.code)
        if serie_id not in hub.medien.serien:
            return _fehler_antwort(hub, "serie_nicht_gefunden")

    if upload_id:
        hub.uploads_laufend.add(upload_id)
    part_pfad = hub.pfade.upload / f"{secrets.token_hex(8)}.part"
    # --- Phase A: Empfang ---
    try:
        await hass.async_add_executor_job(lambda: hub.pfade.upload.mkdir(parents=True, exist_ok=True))
        datei = await hass.async_add_executor_job(open, part_pfad, "wb")
    except OSError as err:
        _LOGGER.error("Zwischendatei nicht angelegt: %s", err)
        if upload_id:
            hub.uploads_laufend.discard(upload_id)
        return _fehler_antwort(hub, "medien_schreibfehler")
    gesamt = 0
    try:
        while True:
            block = await part.read_chunk(UPLOAD_BLOCK_BYTES)
            if not block:
                break
            gesamt += len(block)
            if gesamt > hub.upload_max_bytes:
                await hass.async_add_executor_job(datei.close)
                await asyncio.shield(hass.async_add_executor_job(_loesche_leise, part_pfad))
                if upload_id:
                    hub.uploads_laufend.discard(upload_id)
                return _fehler_antwort(hub, "datei_zu_gross")
            if rest is not None and gesamt > rest:
                await hass.async_add_executor_job(datei.close)
                await asyncio.shield(hass.async_add_executor_job(_loesche_leise, part_pfad))
                if upload_id:
                    hub.uploads_laufend.discard(upload_id)
                return _fehler_antwort(hub, "zu_viele_aenderungen")
            await hass.async_add_executor_job(datei.write, block)
        await hass.async_add_executor_job(_fsync_und_schliessen, datei)
    except BaseException:  # Abbruch des Clients (CancelledError) oder Fehler beim Schreiben: nichts bleibt
        with contextlib.suppress(Exception):
            datei.close()
        await asyncio.shield(hass.async_add_executor_job(_loesche_leise, part_pfad))
        if upload_id:
            hub.uploads_laufend.discard(upload_id)
        raise

    hub.schutz.upload_gebucht(nutzer, gesamt)

    # --- Phase B: Abschluss als eigene Aufgabe, vom Handler mit shield abgewartet ---
    aufgabe = hass.async_create_background_task(
        _abschliessen(hub, part_pfad, name, endung, gesamt, upload_id, serie_id, gruppe, nutzer_id),
        "tobibox_upload_abschluss",
    )
    try:
        ergebnis = await asyncio.shield(aufgabe)
    except TobiboxFehler as err:
        return _fehler_antwort(hub, err.code)
    return web.json_response(ergebnis)


def _alte_ergebnisse_aufraeumen(hub: Hub) -> None:
    jetzt_s = hub.hass.loop.time()
    for k in [k for k, (t, _e) in hub.upload_ergebnisse.items() if jetzt_s - t > UPLOAD_ERGEBNIS_MERKEN_S]:
        del hub.upload_ergebnisse[k]


async def _abschliessen(
    hub: Hub,
    part_pfad: Path,
    name: str,
    endung: str,
    groesse: int,
    upload_id: str | None,
    serie_id: str | None,
    gruppe: str | None,
    nutzer_id: str | None,
) -> dict[str, Any]:
    """Prüfen, in den Eingang bringen (ohne Überschreiben), Ergebnis merken, Einsortieren anstoßen (5.2, Phase B)."""
    hass = hub.hass

    def melde(zustand: str, code: str | None = None, **mehr: Any) -> None:
        hub.emit(
            "upload",
            "fortschritt",
            {"upload_id": upload_id, "zustand": zustand, "bytes": groesse, "code": code, **mehr},
            nutzer_id=nutzer_id,
        )

    try:
        melde("pruefe")
        pruefung = await hass.async_add_executor_job(ffprobe.pruefe_datei, part_pfad, endung)
        if pruefung.ergebnis == "ungueltig":
            raise TobiboxFehler("format_nicht_erlaubt")
        if pruefung.ergebnis == "nicht_moeglich":
            ergebnis_pruefung, hinweis = "nicht_moeglich", ffprobe.FFPROBE_FEHLT
        elif pruefung.ergebnis == "warnung":
            ergebnis_pruefung, hinweis = "warnung", pruefung.hinweis
        else:
            ergebnis_pruefung, hinweis = "ok", None
        async with hub.eingang.sperre:
            try:
                rel, zielname = await hass.async_add_executor_job(_in_den_eingang, hub, part_pfad, name, gruppe)
            except NamenErschoepft as err:
                raise TobiboxFehler("medien_schreibfehler") from err
            except OSError as err:
                _LOGGER.error("Datei nicht in den Eingang gebracht: %s", err)
                raise TobiboxFehler("medien_schreibfehler") from err
            hub.eingang.registriere_upload(rel, serie_id, gruppe)
        antwort = {
            "v": VERTRAG_V,
            "upload_id": upload_id,
            "eingang_name": zielname,
            "serie_id": serie_id,
            "groesse_bytes": groesse,
            "pruefung": ergebnis_pruefung,
            "hinweis": hinweis,
            "wiederholt": False,
        }
        if upload_id:
            hub.upload_ergebnisse[upload_id] = (hass.loop.time(), antwort)
            while len(hub.upload_ergebnisse) > UPLOAD_ERGEBNIS_ANZAHL:
                hub.upload_ergebnisse.popitem(last=False)
        # „Upload fertig“ trägt Dateiname im Eingang und Ergebnis der Prüfung (Erweiterung v1.1, 09.11.)
        melde("fertig", datei=zielname, pruefung=ergebnis_pruefung)
        return antwort
    except TobiboxFehler as err:
        melde("fehler", err.code)
        raise
    except Exception:
        _LOGGER.exception("Upload-Abschluss fehlgeschlagen")
        melde("fehler", "unknown_error")
        raise TobiboxFehler("unknown_error") from None
    finally:
        if upload_id:
            hub.uploads_laufend.discard(upload_id)
        await hass.async_add_executor_job(_loesche_leise, part_pfad)


def _in_den_eingang(hub: Hub, part_pfad: Path, name: str, gruppe: str | None) -> tuple[str, str]:
    """Bringt die Zwischendatei ohne Überschreiben in den Eingang (unter der Sperre des Eingangs)."""
    eingang = hub.pfade.eingang
    ordner = eingang
    rel_ordner = ""
    if gruppe:
        rel_ordner = f"{EINGANG_ORDNER_PRAEFIX}{gruppe[:8]}"
        ordner = eingang / rel_ordner
        ordner.mkdir(exist_ok=True)
    for _ in range(5):
        belegt = {vergleichsschluessel(e.name) for e in os.scandir(ordner)}
        ziel = eindeutiger_name(name, belegt, mit_endung=True)
        try:
            dateien.verschiebe_ohne_ueberschreiben(part_pfad, ordner / ziel)
        except dateien.ZielExistiert:
            continue
        return (f"{rel_ordner}/{ziel}" if rel_ordner else ziel), ziel
    raise NamenErschoepft(name)
