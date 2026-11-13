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
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aiohttp import web

from homeassistant.components.http import KEY_HASS, HomeAssistantView

from . import dateien, ffprobe
from .cover import cover_pruefen_und_skalieren
from .const import (
    ARTEN,
    COVER_UPLOAD_MAX_BYTES,
    DOMAIN,
    ENDUNGEN,
    GRUPPE_ANZAHL_MAX,
    RE_UPLOAD_ID,
    SERIE_NAME_MAX,
    UPLOAD_BLOCK_BYTES,
    UPLOAD_ERGEBNIS_ANZAHL,
    UPLOAD_ERGEBNIS_MERKEN_S,
    UPLOAD_PARALLEL,
    UPLOAD_RESERVE_BYTES,
    VERTRAG_V,
    WUNSCH_NAME_MAX_BYTES,
    WUNSCH_ZIELE,
)
from .fehler import TobiboxFehler
from .media import gueltige_serien_id, name_pruefen
from .namen import NamenErschoepft, dateiname_bereinigen, eindeutiger_name, vergleichsschluessel
from .schutz import Nutzer

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

EINGANG_ORDNER_PRAEFIX = "Upload "


@dataclass(eq=False)
class UploadLauf:
    """Ein laufender Upload: was er angekündigt und geschrieben hat (Reserve-Rechnung) und zu welcher Gruppe er gehört."""

    laenge: int | None = None
    geschrieben: int = 0
    gruppe_ordner: str | None = None


def ausstehende_bytes(hub: Hub) -> int:
    """Bytes, die laufende Uploads angekündigt (``Content-Length``), aber noch nicht in die Zwischendatei geschrieben haben.

    Der freie Platz der Freigabe enthält das schon Geschriebene nicht mehr; das Ausstehende muss der nächste Upload
    zusätzlich abziehen (Vertrag W, 5.1 und 14.10)."""
    return sum(max(0, lauf.laenge - lauf.geschrieben) for lauf in hub.upload_laeufe if lauf.laenge is not None)


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
        lauf = UploadLauf()
        try:
            return await _empfange(hub, request, nutzer, lauf)
        finally:
            hub.upload_zaehler -= 1
            hub.upload_laeufe.discard(lauf)
            if lauf.gruppe_ordner:
                hub.eingang.upload_endet(lauf.gruppe_ordner)


def _fsync_und_schliessen(f: Any) -> None:
    f.flush()
    os.fsync(f.fileno())
    f.close()


def _loesche_leise(pfad: Path) -> None:
    with contextlib.suppress(OSError):
        pfad.unlink()


async def _lies_roh(part: Any, max_bytes: int) -> bytes:
    """Liest ein Textfeld im Strom, höchstens ``max_bytes + 1`` Bytes (das eine Byte mehr verrät den Überlauf)."""
    roh = b""
    while len(roh) <= max_bytes:
        block = await part.read_chunk(max_bytes + 1 - len(roh))
        if not block:
            break
        roh += block
    await part.release()
    return roh


async def _lies_feld(part: Any) -> str:
    """Ein kleines Textfeld (höchstens 64 Zeichen, sonst ungültig)."""
    return (await _lies_roh(part, 200)).decode("utf-8", "replace").strip()


def _pruefe_wunsch(felder: dict[str, str], roh_name: bytes | None, serie_id: str | None, gruppe: str | None) -> dict[str, Any] | None:
    """Der Wunsch beim Hochladen (Vertrag W, 14.4): ``None`` ohne Wunsch, sonst ``{ziel, art, name, gruppe_anzahl}``.

    ``auto`` ohne ``gruppe_anzahl`` ist kein Wunsch (genau das bisherige Verhalten). Alles andere Unpassende ist
    ``wunsch_ungueltig``; ``name`` wird bis 400 Bytes gelesen und nach den Namensregeln bereinigt (höchstens 100 Zeichen)."""
    ziel = felder.get("ziel") or "auto"
    if ziel not in WUNSCH_ZIELE:
        raise TobiboxFehler("wunsch_ungueltig")
    art = felder.get("art") or None
    if art is not None and art not in ARTEN:
        raise TobiboxFehler("wunsch_ungueltig")
    anzahl_text = felder.get("gruppe_anzahl") or None
    anzahl: int | None = None
    if anzahl_text is not None:
        if not re.fullmatch(r"[0-9]{1,4}", anzahl_text) or not 2 <= int(anzahl_text) <= GRUPPE_ANZAHL_MAX or not gruppe:
            raise TobiboxFehler("wunsch_ungueltig")  # ohne ``gruppe`` gibt es nichts, worauf der Eingang warten könnte
        anzahl = int(anzahl_text)
    name: str | None = None
    if roh_name:
        if len(roh_name) > WUNSCH_NAME_MAX_BYTES:
            raise TobiboxFehler("wunsch_ungueltig")
        try:
            name = name_pruefen(roh_name.decode("utf-8"), SERIE_NAME_MAX)
        except (TobiboxFehler, UnicodeDecodeError):
            raise TobiboxFehler("wunsch_ungueltig") from None
    if ziel == "auto":
        return {"ziel": "auto", "art": None, "name": None, "gruppe_anzahl": anzahl} if anzahl else None
    if ziel == "neu":
        if art is None or name is None or serie_id:
            raise TobiboxFehler("wunsch_ungueltig")
    elif ziel == "ergaenzen":
        if not serie_id:
            raise TobiboxFehler("wunsch_ungueltig")
        art, name = None, None
    else:  # einzeln: eine Datei je Upload, ohne gemeinsame Gruppe, die Serie gibt es noch nicht
        if anzahl is not None or serie_id:
            raise TobiboxFehler("wunsch_ungueltig")
        art = art or "musik"
    return {"ziel": ziel, "art": art, "name": name, "gruppe_anzahl": anzahl}


async def _verwerfe_rest(part: Any) -> None:
    """Liest den Rest des Teils ``datei`` im Strom und wirft ihn weg (der Client bekommt dann seine Antwort)."""
    while await part.read_chunk(UPLOAD_BLOCK_BYTES):
        pass


async def _empfange(hub: Hub, request: web.Request, nutzer: Nutzer, lauf: UploadLauf) -> web.StreamResponse:
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
        # Reserve 2 GiB; was laufende Uploads angekündigt, aber noch nicht geschrieben haben, ist schon vergeben.
        # Prüfen und Anmelden ohne ``await`` dazwischen, sonst bestehen zwei gleichzeitige Uploads die Prüfung beide.
        if laenge + UPLOAD_RESERVE_BYTES > frei - ausstehende_bytes(hub):
            return _fehler_antwort(hub, "kein_speicher")
        lauf.laenge = laenge
        hub.upload_laeufe.add(lauf)

    try:
        reader = await request.multipart()
    except (AssertionError, KeyError, ValueError):
        return _fehler_antwort(hub, "invalid_format")
    felder: dict[str, str] = {}
    roh_name: bytes | None = None
    part = None
    while True:
        part = await reader.next()
        if part is None:
            return _fehler_antwort(hub, "invalid_format")
        if part.name == "datei":
            break
        if part.name in ("upload_id", "serie_id", "gruppe", "ziel", "art", "gruppe_anzahl"):
            felder[part.name] = await _lies_feld(part)
        elif part.name == "name":
            roh_name = await _lies_roh(part, WUNSCH_NAME_MAX_BYTES)
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

    try:
        wunsch = _pruefe_wunsch(felder, roh_name, serie_id, gruppe)
    except TobiboxFehler as err:
        return _fehler_antwort(hub, err.code)
    # ``neu``/``ergaenzen`` mit mehreren Dateien braucht ``gruppe_anzahl`` (14.4): schon eine zweite Datei ohne die Zusage ist ungültig
    if wunsch and wunsch["ziel"] in ("neu", "ergaenzen") and not wunsch["gruppe_anzahl"] and gruppe:
        if hub.eingang.gruppe_belegt(f"{EINGANG_ORDNER_PRAEFIX}{gruppe[:8]}"):
            return _fehler_antwort(hub, "wunsch_ungueltig")

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
        if wunsch and wunsch["ziel"] == "ergaenzen" and hub.medien.serien[serie_id].serie.einzeln:
            return _fehler_antwort(hub, "wunsch_ungueltig")  # in einen Einzeltitel kommen keine neuen Folgen (14.2)

    if upload_id:
        hub.uploads_laufend.add(upload_id)
    if wunsch and wunsch["gruppe_anzahl"] and gruppe:  # solange eine Datei der Gruppe noch unterwegs ist, wartet der Eingang
        lauf.gruppe_ordner = f"{EINGANG_ORDNER_PRAEFIX}{gruppe[:8]}"
        hub.eingang.upload_beginnt(lauf.gruppe_ordner)
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
            lauf.geschrieben = gesamt
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
        _abschliessen(hub, part_pfad, name, endung, gesamt, upload_id, serie_id, gruppe, nutzer_id, wunsch),
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
    wunsch: dict[str, Any] | None = None,
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
            if wunsch and wunsch["ziel"] in ("neu", "ergaenzen") and not wunsch["gruppe_anzahl"] and gruppe:
                # unter der Sperre noch einmal: eine gleichzeitig angekommene Schwesterdatei zählt (14.4)
                if hub.eingang.gruppe_belegt(f"{EINGANG_ORDNER_PRAEFIX}{gruppe[:8]}"):
                    raise TobiboxFehler("wunsch_ungueltig")
            try:
                rel, zielname = await hass.async_add_executor_job(_in_den_eingang, hub, part_pfad, name, gruppe)
            except NamenErschoepft as err:
                raise TobiboxFehler("medien_schreibfehler") from err
            except OSError as err:
                _LOGGER.error("Datei nicht in den Eingang gebracht: %s", err)
                raise TobiboxFehler("medien_schreibfehler") from err
            hub.eingang.registriere_upload(rel, serie_id, gruppe, wunsch)
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


# --------------------------------------------------------------------------
# Cover (Vertrag W, 14.3)
# --------------------------------------------------------------------------

COVER_LESEBLOCK = 65536
COVER_CACHE_KONTROLLE = "private, max-age=86400"


def _etag_passt(kopf: str | None, stand: str) -> bool:
    """``If-None-Match``: eine Liste von ETags (mit oder ohne ``W/``, in Anführungszeichen) oder ``*``."""
    if not kopf:
        return False
    for teil in kopf.split(","):
        teil = teil.strip()
        if teil == "*":
            return True
        if teil.startswith("W/"):
            teil = teil[2:]
        if teil.strip('"') == stand:
            return True
    return False


class TobiboxStaticView(HomeAssistantView):
    """``/tobibox_static/<Datei>``: die Dateien der Seite, immer mit ``Cache-Control: no-cache`` (B4).

    Die Seite besteht aus vielen ES-Modulen, die einander ohne ``?v=`` laden. Eine Version in jeder Import-Adresse ließe
    dasselbe Modul unter zwei Adressen doppelt laufen und müsste in jeder Datei stehen. Darum bleiben die Adressen
    gleich und der Browser fragt bei jedem Laden nach (``ETag`` und ``Last-Modified`` bringt ``FileResponse`` mit:
    unverändert = ``304``, ohne Inhalt). Ohne Anmeldung, wie bisher die statischen Pfade: die Dateien enthalten keine Geheimnisse."""

    url = "/tobibox_static/{pfad:.+}"
    name = "tobibox:static"
    requires_auth = False
    cors_allowed = False

    def __init__(self, ordner: Path) -> None:
        self._ordner = ordner

    async def get(self, request: web.Request, pfad: str) -> web.StreamResponse:
        hass = request.app[KEY_HASS]
        datei = await hass.async_add_executor_job(self._finde, pfad)
        if datei is None:
            return web.Response(status=404)
        return web.FileResponse(datei, headers={"Cache-Control": "no-cache"})

    def _finde(self, pfad: str) -> Path | None:
        """Läuft im Executor. Nur Dateien unterhalb des Ordners, keine ``..``."""
        try:
            wurzel = self._ordner.resolve()
            datei = (wurzel / pfad).resolve()
        except (OSError, ValueError):
            return None
        if wurzel not in datei.parents or not datei.is_file():
            return None
        return datei


class TobiboxCoverView(HomeAssistantView):
    """``/api/tobibox/cover/<serie_id>``: GET (lesen), POST (Foto-Upload) und DELETE ``?quelle=eigen`` (alltag).

    Jeder angemeldete Benutzer (Vertrag W, 2.1); die Anmeldung kommt im ``Authorization``-Kopf, die Seite lädt mit ``fetchWithAuth``."""

    url = "/api/tobibox/cover/{serie_id}"
    name = "api:tobibox:cover"
    requires_auth = True
    cors_allowed = False

    @staticmethod
    def _hub(request: web.Request) -> Hub | None:
        return request.app[KEY_HASS].data.get(DOMAIN)

    async def _serie_pruefen(self, hub: Hub, serie_id: str) -> web.Response | None:
        """Antwort mit Fehler, wenn die Serie unbekannt ist oder die Freigabe nicht antwortet; sonst ``None``."""
        if not gueltige_serien_id(serie_id):
            return _fehler_antwort(hub, "serie_nicht_gefunden")
        try:
            await hub.medien._stelle_geprueft_sicher()
        except TobiboxFehler as err:
            return _fehler_antwort(hub, err.code)
        if serie_id not in hub.medien.serien:
            return _fehler_antwort(hub, "serie_nicht_gefunden")
        return None

    async def get(self, request: web.Request, serie_id: str) -> web.StreamResponse:
        hub = self._hub(request)
        if hub is None:
            return web.json_response({"v": VERTRAG_V, "fehler": {"code": "unknown_error", "text": "nicht geladen"}}, status=500)
        groesse = request.query.get("groesse", "gross")
        if groesse not in ("klein", "gross"):
            return _fehler_antwort(hub, "invalid_format")
        if (fehler := await self._serie_pruefen(hub, serie_id)) is not None:
            return fehler
        stand = hub.medien.serien[serie_id].cover_stand
        if stand is None:
            return _fehler_antwort(hub, "cover_nicht_gefunden")
        kopf = {"ETag": f'"{stand}"', "Cache-Control": COVER_CACHE_KONTROLLE}
        if _etag_passt(request.headers.get("If-None-Match"), stand):
            return web.Response(status=304, headers=kopf)
        try:
            stand, daten = await hub.cover.lies(serie_id, groesse)
        except TobiboxFehler as err:
            return _fehler_antwort(hub, err.code)
        except OSError:
            return _fehler_antwort(hub, "medien_nicht_erreichbar")
        return web.Response(body=daten, content_type="image/jpeg", headers={**kopf, "ETag": f'"{stand}"'})

    async def post(self, request: web.Request, serie_id: str) -> web.StreamResponse:
        hub = self._hub(request)
        if hub is None:
            return web.json_response({"v": VERTRAG_V, "fehler": {"code": "unknown_error", "text": "nicht geladen"}}, status=500)
        nutzer = Nutzer.aus_user(request["hass_user"])
        try:
            hub.schutz.cover_pruefen(nutzer)
        except TobiboxFehler as err:
            return _fehler_antwort(hub, err.code)
        if request.content_length is not None and request.content_length > COVER_UPLOAD_MAX_BYTES:
            return _fehler_antwort(hub, "datei_zu_gross")
        if (fehler := await self._serie_pruefen(hub, serie_id)) is not None:
            return fehler
        # Der Rumpf wird in Blöcken gelesen und gezählt: die Grenze gilt auch ohne ``Content-Length`` (Transfer-Encoding: chunked)
        daten = bytearray()
        async for block in request.content.iter_chunked(COVER_LESEBLOCK):
            daten += block
            if len(daten) > COVER_UPLOAD_MAX_BYTES:
                return _fehler_antwort(hub, "datei_zu_gross")
        if not daten:
            return _fehler_antwort(hub, "cover_ungueltig")
        hub.schutz.cover_gebucht(nutzer)
        hass = hub.hass
        try:
            gross, klein = await hass.async_add_executor_job(cover_pruefen_und_skalieren, bytes(daten))
            ergebnis = await hub.cover.setze_eigen(serie_id, gross, klein)
        except TobiboxFehler as err:
            return _fehler_antwort(hub, err.code)
        return web.json_response({"v": VERTRAG_V, "serie_id": serie_id, **ergebnis})

    async def delete(self, request: web.Request, serie_id: str) -> web.StreamResponse:
        hub = self._hub(request)
        if hub is None:
            return web.json_response({"v": VERTRAG_V, "fehler": {"code": "unknown_error", "text": "nicht geladen"}}, status=500)
        if request.query.get("quelle") != "eigen":
            return _fehler_antwort(hub, "invalid_format")
        if (fehler := await self._serie_pruefen(hub, serie_id)) is not None:
            return fehler
        try:
            ergebnis = await hub.cover.entferne_eigen(serie_id)
        except TobiboxFehler as err:
            return _fehler_antwort(hub, err.code)
        return web.json_response({"v": VERTRAG_V, "serie_id": serie_id, **ergebnis})
