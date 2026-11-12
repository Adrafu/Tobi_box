"""Cover der Einträge (Vertrag W, 14.3; Design V-1 und 5.5; ``data-model.md``, Abschnitt 5).

Zwei Teile:

* **Reine Funktionen** (laufen im Executor, nie in der Event-Loop): ``cover_pruefen_und_skalieren`` ist **die eine** Prüfung für
  jedes Bild, das ein Cover werden soll (Foto-Upload, aus den Tags gezogenes Bild, mitgelieferte Datei). Reihenfolge: (1) Größe,
  (2) Typ aus den Kopfbytes, (3) Maße aus dem Kopf **ohne ein Pixel zu dekodieren** und Grenzen für Kante, Pixelzahl und Quadrat,
  (4) erst dann dekodieren, auf 512 und 192 px herunterrechnen und neu als JPEG kodieren. Das Original wird nie gespeichert;
  Metadaten (EXIF, Profile) gehen dabei verloren.
* ``CoverDienst``: Speichern, Lesen, Suchen im Hintergrund (Marke „schon gesucht“ im Store ``tobibox.medieninfo``).
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import logging
import os
import secrets
import signal
import stat
import struct
import subprocess
import threading
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageOps

from . import dateien, ffprobe
from .const import (
    COVER_AUTO,
    COVER_EIGEN,
    COVER_GROSS_PX,
    COVER_JPEG_QUALITAET,
    COVER_KANTE_MAX_PX,
    COVER_KLEIN_CACHE_ANZAHL,
    COVER_KLEIN_PX,
    COVER_QUADRAT_TOLERANZ,
    COVER_QUELLEN,
    COVER_SUCHE_DATEIEN_MAX,
    COVER_SUCHE_ZEITGRENZE_S,
    COVER_UPLOAD_MAX_BYTES,
    FORMAT_JE_ENDUNG,
)
from .fehler import TobiboxFehler

if TYPE_CHECKING:
    from .hub import Hub
    from .media import Serie

_LOGGER = logging.getLogger(__name__)

#: Dateinamen, die im Eingangs-Ordner als mitgeliefertes Cover gelten (in dieser Reihenfolge; Groß-/Kleinschreibung egal)
MITGELIEFERT_IM_EINGANG = (COVER_AUTO, "folder.jpg", "cover.png")
PNG_KOPF = b"\x89PNG\r\n\x1a\n"
#: Marken ohne Breite/Höhe im Kopf: ``SOF`` heißt 0xC0 bis 0xCF ohne diese
_JPEG_KEIN_SOF = frozenset({0xC4, 0xC8, 0xCC})


# --------------------------------------------------------------------------
# Kopf lesen: Typ und Maße, ohne ein Pixel zu dekodieren
# --------------------------------------------------------------------------


def _ungueltig() -> TobiboxFehler:
    return TobiboxFehler("cover_ungueltig")


def _jpeg_masse(daten: bytes) -> tuple[int, int]:
    """Breite und Höhe aus dem ersten ``SOF``-Segment. ``cover_ungueltig``, wenn keines kommt oder der Aufbau nicht stimmt."""
    laenge = len(daten)
    i = 2
    while i + 4 <= laenge:
        if daten[i] != 0xFF:
            raise _ungueltig()
        marke = daten[i + 1]
        if marke == 0xFF:  # Füllbyte
            i += 1
            continue
        if marke in (0x01, *range(0xD0, 0xD8)):  # Marken ohne Länge
            i += 2
            continue
        if marke in (0xD8, 0xD9, 0xDA):  # Anfang, Ende, Bilddaten: kein ``SOF`` davor
            raise _ungueltig()
        segment = struct.unpack(">H", daten[i + 2 : i + 4])[0]
        if segment < 2:
            raise _ungueltig()
        if 0xC0 <= marke <= 0xCF and marke not in _JPEG_KEIN_SOF:
            if segment < 8 or i + 4 + 5 > laenge:
                raise _ungueltig()
            hoehe, breite = struct.unpack(">HH", daten[i + 5 : i + 9])
            return breite, hoehe
        i += 2 + segment
    raise _ungueltig()


def _png_masse(daten: bytes) -> tuple[int, int]:
    if len(daten) < 24 or daten[12:16] != b"IHDR":
        raise _ungueltig()
    breite, hoehe = struct.unpack(">II", daten[16:24])
    return breite, hoehe


def bildkopf(daten: bytes) -> tuple[str, int, int]:
    """``(typ, breite, hoehe)`` aus den Kopfbytes: ``jpeg`` oder ``png``. Die Dateiendung zählt nie."""
    if daten[:3] == b"\xff\xd8\xff":
        breite, hoehe = _jpeg_masse(daten)
        return "jpeg", breite, hoehe
    if daten[:8] == PNG_KOPF:
        breite, hoehe = _png_masse(daten)
        return "png", breite, hoehe
    raise _ungueltig()


# --------------------------------------------------------------------------
# Die eine Prüf- und Skalierfunktion
# --------------------------------------------------------------------------


def _als_rgb(bild: Image.Image) -> Image.Image:
    if bild.mode in ("RGBA", "LA") or (bild.mode == "P" and "transparency" in bild.info):
        bild = bild.convert("RGBA")
        grund = Image.new("RGB", bild.size, (255, 255, 255))
        grund.paste(bild, mask=bild.getchannel("A"))
        return grund
    return bild if bild.mode == "RGB" else bild.convert("RGB")  # auch CMYK und Graustufen


def _jpeg(bild: Image.Image, kante: int) -> bytes:
    kopie = bild.copy()
    if max(kopie.size) > kante:
        kopie.thumbnail((kante, kante), Image.Resampling.LANCZOS)
    puffer = io.BytesIO()
    kopie.save(puffer, "JPEG", quality=COVER_JPEG_QUALITAET, optimize=True)  # ohne EXIF und Profile
    return puffer.getvalue()


def cover_pruefen_und_skalieren(
    daten: bytes, *, erlaubt: tuple[str, ...] = ("jpeg",), quadrat: bool = True
) -> tuple[bytes, bytes]:
    """Prüft ein Bild und gibt ``(gross, klein)`` als JPEG zurück (höchstens 512 und 192 px je Seite, nie vergrößert).

    ``erlaubt``: Typen, die der Aufrufer annimmt. Das Foto aus der Seite ist ``("jpeg",)``; ein Bild aus den Tags oder eine
    mitgelieferte Datei darf auch ``png`` sein. ``quadrat=False`` nur für eine Datei, die schon im Serien-Ordner liegt.
    Fehler: ``datei_zu_gross`` (über ``COVER_UPLOAD_MAX_BYTES``), ``cover_ungueltig`` (Typ, Kopf, Maße, Quadrat, kaputte Bilddaten).
    Läuft im Executor."""
    if len(daten) > COVER_UPLOAD_MAX_BYTES:
        raise TobiboxFehler("datei_zu_gross")
    typ, breite, hoehe = bildkopf(daten)
    if typ not in erlaubt:
        raise _ungueltig()
    if not 1 <= breite <= COVER_KANTE_MAX_PX or not 1 <= hoehe <= COVER_KANTE_MAX_PX:
        raise _ungueltig()
    if breite * hoehe > COVER_KANTE_MAX_PX * COVER_KANTE_MAX_PX:  # (folgt aus den Kanten; die Pixelzahl bleibt eigene Grenze)
        raise _ungueltig()
    if quadrat and abs(breite - hoehe) > COVER_QUADRAT_TOLERANZ * max(breite, hoehe):
        raise _ungueltig()
    # erst jetzt wird dekodiert; die Maße des Kopfes müssen zum Bild passen
    try:
        with Image.open(io.BytesIO(daten), formats=["JPEG", "PNG"]) as bild:
            if bild.size != (breite, hoehe):
                raise _ungueltig()
            bild.load()
            bild = ImageOps.exif_transpose(bild)
            bild = _als_rgb(bild)
            return _jpeg(bild, COVER_GROSS_PX), _jpeg(bild, COVER_KLEIN_PX)
    except TobiboxFehler:
        raise
    except Exception as err:  # kaputte oder abgeschnittene Bilddaten, Zerlegungsfehler von Pillow
        _LOGGER.debug("Bild nicht lesbar: %s", err)
        raise _ungueltig() from err


def cover_klein(gross: bytes) -> bytes:
    """Die kleine Ansicht (192 px) aus der gespeicherten Datei. ``cover_ungueltig``, wenn die Datei kein brauchbares Bild ist."""
    return cover_pruefen_und_skalieren(gross, erlaubt=("jpeg", "png"), quadrat=False)[1]


# --------------------------------------------------------------------------
# Dateien im Serien-Ordner
# --------------------------------------------------------------------------


def stand_aus(name: str, st: os.stat_result) -> str:
    """Fingerabdruck der angezeigten Datei: 8 Zeichen ``[0-9a-f]`` über Name, Größe und Änderungszeit."""
    return hashlib.sha1(f"{name}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:8]  # noqa: S324 - kein Sicherheitsmerkmal


def _regulaer(pfad: Path) -> os.stat_result | None:
    """``lstat`` einer regulären Datei; ein Link oder ein Ordner zählt nicht."""
    try:
        st = os.lstat(pfad)
    except OSError:
        return None
    return st if stat.S_ISREG(st.st_mode) else None


def cover_zustand(ordner: Path) -> tuple[str | None, str | None]:
    """``(cover_stand, cover_quelle)`` des Serien-Ordners: ``cover-eigen.jpg`` gilt vor ``cover.jpg``; ohne beide ``(None, None)``."""
    for name, quelle in ((COVER_EIGEN, "eigen"), (COVER_AUTO, "auto")):
        st = _regulaer(ordner / name)
        if st is not None:
            return stand_aus(name, st), quelle
    return None, None


def lese_cover_datei(ordner: Path) -> tuple[str, bytes] | None:
    """``(Stand, Bytes)`` der angezeigten Datei oder ``None`` (kein Cover, oder die Datei ist größer als 3 MiB)."""
    for name in (COVER_EIGEN, COVER_AUTO):
        pfad = ordner / name
        st = _regulaer(pfad)
        if st is None:
            continue
        if st.st_size > COVER_UPLOAD_MAX_BYTES:
            return None
        with open(pfad, "rb") as f:
            return stand_aus(name, st), f.read(COVER_UPLOAD_MAX_BYTES + 1)
    return None


def schreibe_bytes_atomar(pfad: Path, daten: bytes) -> None:
    """Datei mit Punkt-Namen schreiben, ``fsync``, umbenennen (der Sync der Boxen sieht nie eine halbe Datei)."""
    tmp = pfad.with_name(f".{pfad.name}.{secrets.token_hex(4)}.tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(daten)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, pfad)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    dateien.fsync_verzeichnis(pfad.parent)


def loesche_datei(pfad: Path) -> bool:
    """Löscht eine reguläre Datei; ``True``, wenn es sie gab."""
    if _regulaer(pfad) is None:
        return False
    try:
        pfad.unlink()
    except FileNotFoundError:
        return False
    return True


def uebernimm_cover(quelle: Path, ziel: Path) -> bool:
    """Zusammenführen: Hat die Ziel-Serie kein Cover, werden die Cover-Dateien der Quelle **kopiert** (die Quelle geht danach als
    Ganzes in den Papierkorb und behält ihre Kopie). ``True``, wenn etwas kopiert wurde."""
    if cover_zustand(ziel)[0] is not None:
        return False
    kopiert = False
    for name in (COVER_EIGEN, COVER_AUTO):
        st = _regulaer(quelle / name)
        if st is None or st.st_size > COVER_UPLOAD_MAX_BYTES:
            continue
        with open(quelle / name, "rb") as f:
            schreibe_bytes_atomar(ziel / name, f.read(COVER_UPLOAD_MAX_BYTES + 1))
        kopiert = True
    return kopiert


# --------------------------------------------------------------------------
# Mitgelieferte Bilddateien und Bilder aus den Tags
# --------------------------------------------------------------------------


def finde_mitgeliefert(ordner_liste: list[Path], namen: tuple[str, ...]) -> bytes | None:
    """Das erste brauchbare mitgelieferte Bild (``cover.jpg``, ``folder.jpg``, ``cover.png``), geprüft und verkleinert (512 px).

    Die Ordner werden in der Reihenfolge der Liste durchsucht, die Namen in der Reihenfolge von ``namen`` (Groß-/Kleinschreibung
    egal). Ein Bild, das die Prüfung nicht besteht, zählt nicht. Die Datei selbst wird nie verändert. Läuft im Executor."""
    for ordner in ordner_liste:
        try:
            vorhanden = {e.name.lower(): e.name for e in os.scandir(ordner)}
        except OSError:
            continue
        for name in namen:
            echt = vorhanden.get(name)
            st = _regulaer(ordner / echt) if echt else None
            if echt is None or st is None or st.st_size > COVER_UPLOAD_MAX_BYTES:
                continue
            try:
                with open(ordner / echt, "rb") as f:
                    roh = f.read(COVER_UPLOAD_MAX_BYTES + 1)
                return cover_pruefen_und_skalieren(roh, erlaubt=("jpeg", "png"))[0]
            except (OSError, TobiboxFehler):
                continue
    return None


def _kind_grenzen() -> None:  # pragma: no cover - läuft im Kindprozess
    ffprobe._grenzen_setzen()
    with contextlib.suppress(OSError, AttributeError):
        os.nice(10)


def bild_aus_tags(pfad: Path, endung: str) -> bytes | None:
    """Das eingebettete Bild (ID3 ``APIC``, MP4 ``covr``, FLAC ``PICTURE``) einer Audiodatei, roh, höchstens 3 MiB.

    ``ffmpeg`` mit den gleichen Härtungen wie ``ffprobe`` (Liste von Argumenten, nur ``file``, Speichergrenze), feste Zeitgrenze
    ``COVER_SUCHE_ZEITGRENZE_S`` für die ganze Datei (der Prozess samt Gruppe wird beendet) und höchstens 3 MiB gelesen.
    ``None``: kein Bild, Zeitgrenze, Fehler. Wirft ``FileNotFoundError``, wenn ``ffmpeg`` fehlt. Läuft im Executor."""
    programm = ffprobe.ffmpeg_pfad()
    if programm is None:
        raise FileNotFoundError("ffmpeg")
    format_ = FORMAT_JE_ENDUNG.get(endung.lower())
    if format_ is None:
        return None
    absolut = os.path.abspath(os.fspath(pfad))
    args = [
        programm, "-nostdin", "-v", "error", "-protocol_whitelist", "file", "-f", format_, "-i", f"file:{absolut}",
        "-map", "0:v:0", "-an", "-sn", "-frames:v", "1", "-c:v", "copy", "-f", "image2pipe", "pipe:1",
    ]  # fmt: skip
    try:
        proc = subprocess.Popen(  # noqa: S603
            args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            start_new_session=True, preexec_fn=_kind_grenzen if os.name == "posix" else None,  # noqa: PLW1509
        )  # fmt: skip
    except OSError as err:
        _LOGGER.warning("ffmpeg lässt sich nicht starten: %s", err)
        return None

    abgelaufen = threading.Event()

    def beende() -> None:
        abgelaufen.set()
        _beende_gruppe(proc)

    zeitgeber = threading.Timer(COVER_SUCHE_ZEITGRENZE_S, beende)
    zeitgeber.start()
    try:
        daten = proc.stdout.read(COVER_UPLOAD_MAX_BYTES + 1) if proc.stdout else b""
        if len(daten) > COVER_UPLOAD_MAX_BYTES:
            _beende_gruppe(proc)
            return None
    finally:
        zeitgeber.cancel()
        if proc.poll() is None:
            _beende_gruppe(proc)
        if proc.stdout:
            proc.stdout.close()
        proc.wait()
    if abgelaufen.is_set():
        _LOGGER.warning("Cover aus den Tags: Zeitgrenze (%s s) bei %s", COVER_SUCHE_ZEITGRENZE_S, pfad.name)
        return None
    return daten if proc.returncode == 0 and daten else None


def _beende_gruppe(proc: subprocess.Popen[bytes]) -> None:
    with contextlib.suppress(OSError, ProcessLookupError):
        os.killpg(proc.pid, signal.SIGKILL)
    with contextlib.suppress(OSError):
        proc.kill()


def _erste_datei(ordner: Path, folge: str) -> Path | None:
    """Die Datei, in der das Bild einer Folge stehen kann: die Datei selbst oder der erste Track eines Folgen-Ordners."""
    pfad = ordner / folge
    if pfad.is_dir():
        tracks = sorted(dateien.tracks_in_ordner(pfad), key=str.lower)
        return pfad / tracks[0] if tracks else None
    return pfad if dateien.ist_audio(pfad.name) and pfad.is_file() else None


def suche_in_serie(ordner: Path, folgen: list[str]) -> tuple[str, bytes | None]:
    """Sucht das Cover eines Eintrags: ``(ergebnis, gross)``. ``ergebnis``: ``datei`` (``folder.jpg``/``cover.png`` im Serien-Ordner),
    ``tags`` (Bild der ersten Folge, die eines hat), ``keine`` oder ``ohne_ffmpeg`` (nichts gefunden und das Lesen aus Tags nicht
    möglich: keine Marke). Wirft ``OSError``, wenn der Ordner nicht erreichbar ist. Läuft im Executor."""
    os.stat(ordner)  # OSError: Freigabe weg
    gross = finde_mitgeliefert([ordner], COVER_QUELLEN)
    if gross is not None:
        return "datei", gross
    if ffprobe.ffmpeg_pfad() is None:
        return "ohne_ffmpeg", None
    versucht = 0
    for folge in folgen:
        datei = _erste_datei(ordner, folge)
        if datei is None:
            continue
        if versucht >= COVER_SUCHE_DATEIEN_MAX:
            break
        versucht += 1
        roh = bild_aus_tags(datei, ffprobe.endung_von(datei.name))
        if roh is None:
            continue
        try:
            return "tags", cover_pruefen_und_skalieren(roh, erlaubt=("jpeg", "png"))[0]
        except TobiboxFehler:
            continue  # ein kaputtes oder zu großes Bild: die nächste Folge versuchen
    return "keine", None


# --------------------------------------------------------------------------
# Der Dienst
# --------------------------------------------------------------------------


class _FreigabeWeg(Exception):
    """Die Freigabe ist nicht erreichbar: der Hintergrundlauf bricht ab."""


class CoverDienst:
    """Speichern, Lesen und Suchen im Hintergrund (``hub.cover``)."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self._klein: OrderedDict[tuple[str, str], bytes] = OrderedDict()
        #: Warteschlange der Suche (geordnete Menge von Serien-IDs)
        self._offen: dict[str, None] = {}
        self._task: asyncio.Task | None = None
        self.beim_start_nachgeholt = False

    # --- Lesen ------------------------------------------------------------------------------------------

    async def lies(self, serie_id: str, groesse: str) -> tuple[str, bytes]:
        """``(Stand, Bytes)`` für ``GET``. ``cover_nicht_gefunden``, wenn der Eintrag kein (brauchbares) Cover hat."""
        medien = self.hub.medien
        info = medien.finde(serie_id)
        roh = await self.hub.hass.async_add_executor_job(lese_cover_datei, medien.pfad_serie(info.ordner))
        if roh is None:
            raise TobiboxFehler("cover_nicht_gefunden")
        stand, gross = roh
        if groesse == "gross":
            return stand, gross
        klein = self._klein.get((serie_id, stand))
        if klein is None:
            try:
                klein = await self.hub.hass.async_add_executor_job(cover_klein, gross)
            except TobiboxFehler as err:
                raise TobiboxFehler("cover_nicht_gefunden") from err
            self._merke_klein(serie_id, stand, klein)
        else:
            self._klein.move_to_end((serie_id, stand))
        return stand, klein

    def _merke_klein(self, serie_id: str, stand: str, klein: bytes) -> None:
        self._klein[(serie_id, stand)] = klein
        while len(self._klein) > COVER_KLEIN_CACHE_ANZAHL:
            self._klein.popitem(last=False)

    # --- Foto aus der Seite ---------------------------------------------------------------------------

    async def setze_eigen(self, serie_id: str, gross: bytes, klein: bytes) -> dict[str, Any]:
        medien = self.hub.medien
        async with medien.sperren(serie_id):
            serie, pfad = await medien._frisch(serie_id)
            try:
                await self.hub.hass.async_add_executor_job(schreibe_bytes_atomar, pfad / COVER_EIGEN, gross)
            except OSError as err:
                raise medien._fehler_schreiben(err) from err
            info = await medien._aktualisiere_cache(serie, pfad.name)
        if info.cover_stand:
            self._merke_klein(serie_id, info.cover_stand, klein)
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
        return {"cover_stand": info.cover_stand, "cover_quelle": info.cover_quelle}

    async def entferne_eigen(self, serie_id: str) -> dict[str, Any]:
        """Zurück zum automatischen Cover. Gab es kein eigenes, ändert sich nichts (kein Fehler)."""
        medien = self.hub.medien
        async with medien.sperren(serie_id):
            serie, pfad = await medien._frisch(serie_id)
            try:
                weg = await self.hub.hass.async_add_executor_job(loesche_datei, pfad / COVER_EIGEN)
            except OSError as err:
                raise medien._fehler_schreiben(err) from err
            info = await medien._aktualisiere_cache(serie, pfad.name)
        if weg:
            self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
            if info.cover_quelle is None and self.hub.medieninfo.cover_suche(serie_id) is None:
                self.suche_anstossen([serie_id])
        return {"cover_stand": info.cover_stand, "cover_quelle": info.cover_quelle}

    # --- Einsortieren, Zusammenführen ------------------------------------------------------------------

    async def beim_einsortieren(self, serie: Serie, pfad: Path, eingang_ordner: list[Path]) -> None:
        """Nach dem Einsortieren neuer Folgen (der Aufrufer hält die Sperre der Serie). Ein mitgeliefertes ``cover.jpg`` (sonst
        ``folder.jpg``, ``cover.png``) im Eingangs-Eintrag wird **kopiert**; die Datei im Eingang folgt der alten Regel
        (Papierkorb). Ohne Bild und mit Marke ``keine`` oder ohne Marke startet genau eine Suche in den Tags."""
        hass = self.hub.hass
        medieninfo = self.hub.medieninfo
        ist_auto = await hass.async_add_executor_job(lambda: _regulaer(pfad / COVER_AUTO) is not None)
        if not ist_auto:
            gross = await hass.async_add_executor_job(finde_mitgeliefert, eingang_ordner, MITGELIEFERT_IM_EINGANG)
            if gross is not None:
                await hass.async_add_executor_job(schreibe_bytes_atomar, pfad / COVER_AUTO, gross)
                medieninfo.setze_cover_suche(serie.id, "datei")
                ist_auto = True
        if not ist_auto:
            marke = medieninfo.cover_suche(serie.id)
            if marke is None or marke["ergebnis"] == "keine":
                self.suche_anstossen([serie.id])

    def nach_neuen_folgen(self, serie_id: str) -> None:
        """Neue Folgen in einem Eintrag ohne Cover und mit Marke ``keine``: genau eine neue Suche."""
        info = self.hub.medien.serien.get(serie_id)
        marke = self.hub.medieninfo.cover_suche(serie_id)
        if info is not None and info.cover_quelle is None and marke is not None and marke["ergebnis"] == "keine":
            self.suche_anstossen([serie_id])

    def nach_zusammenfuehren(self, quelle_id: str, ziel_id: str, kopiert: bool) -> None:
        """Hat das Ziel das Cover der Quelle bekommen, übernimmt es auch deren Marke; sonst gilt ``nach_neuen_folgen``."""
        medieninfo = self.hub.medieninfo
        if kopiert:
            marke = medieninfo.cover_suche(quelle_id)
            medieninfo.setze_cover_suche(ziel_id, marke["ergebnis"] if marke else "tags")
        else:
            self.nach_neuen_folgen(ziel_id)

    # --- Suche im Hintergrund ------------------------------------------------------------------------------

    def suche_anstossen(self, serie_ids: list[str]) -> None:
        """Reiht die Einträge in die Suche ein; ein einziger Hintergrundlauf arbeitet sie nacheinander ab."""
        for sid in serie_ids:
            self._offen[sid] = None
        if self._offen and (self._task is None or self._task.done()):
            self._task = self.hub.hass.async_create_background_task(self._arbeite(), "tobibox_cover_suche")

    async def warte_auf_ende(self) -> None:
        """Für Tests und das Beenden: wartet, bis die Warteschlange leer ist."""
        while self._task is not None and not self._task.done():
            await asyncio.shield(self._task)

    def abbrechen(self) -> None:
        self._offen.clear()
        if self._task is not None and not self._task.done():
            self._task.cancel()

    def nachholen_beim_start(self) -> None:
        """Einmal nach dem Start: alle Einträge **ohne Marke**. Kein Dauer-Scan, ``medien/pruefen`` startet nie eine Suche."""
        if self.beim_start_nachgeholt:
            return
        self.beim_start_nachgeholt = True
        ids = [sid for sid in self.hub.medien.serien if self.hub.medieninfo.cover_suche(sid) is None]
        if ids:
            self.suche_anstossen(ids)

    async def _arbeite(self) -> None:
        while self._offen:
            sid = next(iter(self._offen))
            del self._offen[sid]
            try:
                await self._suche(sid)
            except _FreigabeWeg:
                _LOGGER.info("Cover-Suche abgebrochen: die Freigabe ist nicht erreichbar")
                self._offen.clear()
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("Cover-Suche für %s fehlgeschlagen", sid)

    async def _suche(self, serie_id: str) -> None:
        hass = self.hub.hass
        medien = self.hub.medien
        async with medien.sperren(serie_id):  # (beim Einsortieren hält der Aufrufer die Sperre noch: erst danach ist die Serie im Zwischenspeicher)
            try:
                serie, pfad = await medien._frisch(serie_id)
            except TobiboxFehler as err:
                if err.code == "serie_nicht_gefunden":
                    return
                raise _FreigabeWeg from err
            if await hass.async_add_executor_job(lambda: _regulaer(pfad / COVER_AUTO) is not None):
                if self.hub.medieninfo.cover_suche(serie_id) is None:
                    self.hub.medieninfo.setze_cover_suche(serie_id, "tags")  # schon da (Store verloren): nichts zu suchen
                return
            try:
                ergebnis, gross = await hass.async_add_executor_job(suche_in_serie, pfad, list(serie.folgen))
            except OSError as err:
                raise _FreigabeWeg from err
            if ergebnis == "ohne_ffmpeg":
                return  # ohne ffmpeg gibt es keine Tags zu lesen und keine Marke (später erneut)
            if gross is not None:
                try:
                    await hass.async_add_executor_job(schreibe_bytes_atomar, pfad / COVER_AUTO, gross)
                except OSError as err:
                    raise _FreigabeWeg from err
            self.hub.medieninfo.setze_cover_suche(serie_id, ergebnis)
            if gross is not None:
                await medien._aktualisiere_cache(serie, pfad.name)
        if gross is not None:
            self.hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})

    # --- Befehl 44 ------------------------------------------------------------------------------------------

    async def neu_suchen(self, serie_id: str | None) -> dict[str, Any]:
        """``cover/neu_suchen``: löscht ``cover.jpg`` und die Marke und startet die Suche neu. Berührt nie ``cover-eigen.jpg``."""
        medien = self.hub.medien
        await medien._stelle_geprueft_sicher()
        await medien._medien_erreichbar()
        if serie_id is not None:
            medien.finde(serie_id)
            ids = [serie_id]
        else:
            ids = list(medien.serien)
        geaendert: list[str] = []
        for sid in ids:
            async with medien.sperren(sid):
                try:
                    serie, pfad = await medien._frisch(sid)
                except TobiboxFehler as err:
                    if serie_id is not None or err.code != "serie_nicht_gefunden":
                        raise
                    continue
                try:
                    await self.hub.hass.async_add_executor_job(loesche_datei, pfad / COVER_AUTO)
                except OSError as err:
                    raise medien._fehler_schreiben(err) from err
                self.hub.medieninfo.loesche_cover_suche(sid)
                await medien._aktualisiere_cache(serie, pfad.name)
                geaendert.append(sid)
        if geaendert:
            self.hub.emit("medien", "serien_geaendert", {"serie_ids": geaendert})
            self.suche_anstossen(geaendert)
        return {"gestartet": bool(geaendert), "eintraege": len(geaendert)}
