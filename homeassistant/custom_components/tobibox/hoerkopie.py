"""Hörkopien (Paket A3c; Vertrag W, 14.8, 14.10 und Befehl 45; Design 11.4.7).

Ein Track, den nicht jeder Browser spielt (OGG, Opus, FLAC, ALAC, WAV, alles Unbekannte), bekommt **einmal** eine Kopie: AAC in M4A, 96 kbit/s, Stereo,
mit ``ffmpeg``, auf der NAS-Freigabe unter ``hoerkopien/<serie_id>/<kennung>.m4a`` **neben** ``medien/``. Abgespielt wird immer eine fertige Datei
(Springen per Range wie beim Original); die **Box bekommt immer das Original** und kennt den Ordner nicht.

* **Wann:** neu Einsortiertes sofort im Hintergrund (``neu_einsortiert``); der Bestand erst, wenn jemand ihn hören will (``anfordern``, aufgerufen von
  ``audio/bereit``). **Kein** Hintergrundlauf über den Bestand.
* **Harte Grenzen** (alle in ``const.py``): Dauerdeckel, feste Zeitgrenze je Datei, ``-t``, ``-fs``, Plausibilität Größe zu Dauer, Schlangenlimit
  (Dateien und Quellbytes), Kontingent des Ordners, eine Datei zugleich mit ``nice``, je Benutzer eine vorgezogene Datei.
* **Zustand** im Store ``tobibox.medieninfo`` (``folgen.<Folge>.hoerkopie.tracks.<n>``: ``zustand`` ``fertig`` oder ``fehler``, ``kennung``, ``zeit``,
  ``grund``); ``wartet`` steht nur im Arbeitsspeicher (die Schlange). **Ein Versuch je Datei und Start der Integration.**
* ``braucht_hoerkopie(codec)`` ist die **einzige** Stelle, die entscheidet, ob ein Track eine Kopie braucht.
"""

from __future__ import annotations

import asyncio
import contextlib
import errno
import hashlib
import logging
import math
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import dateien, ffprobe
from .const import (
    DAUER_DECKEL_S,
    FORMAT_JE_ENDUNG,
    HOERKOPIE_BYTES_JE_S,
    HOERKOPIE_FS_FAKTOR,
    HOERKOPIE_FS_SOCKEL_BYTES,
    HOERKOPIE_KBIT,
    HOERKOPIE_KONTINGENT_BYTES,
    HOERKOPIE_NICE,
    HOERKOPIE_PARALLEL,
    HOERKOPIE_PLAUSIBEL_FAKTOR,
    HOERKOPIE_SCHAETZ_FAKTOR,
    HOERKOPIE_SCHAETZ_UNBEKANNT_S,
    HOERKOPIE_SCHLANGE_BYTES,
    HOERKOPIE_SCHLANGE_DATEIEN,
    HOERKOPIE_SPEICHER_BYTES,
    HOERKOPIE_T_ZUGABE_S,
    HOERKOPIE_VORZIEHEN_JE_BENUTZER,
    HOERKOPIE_ZEITGRENZE_S,
    MEDIENINFO_ZEITGRENZE_S,
)
from .fehler import TobiboxFehler

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

#: Codecs, die jeder Browser spielt: **Original** (Vertrag W, 14.8). Alles andere, auch Unbekanntes, bekommt eine Kopie.
_OHNE_KOPIE = frozenset({"mp3", "aac"})

#: Gründe (``audio/bereit`` ``fehlt.grund`` und ``hoerkopie.grund``)
ZU_LANG = "zu_lang"
ZEITGRENZE = "zeitgrenze"
UNPLAUSIBEL = "unplausibel"
KODIEREN_FEHLGESCHLAGEN = "kodieren_fehlgeschlagen"
KEIN_SPEICHER = "kein_speicher"
FFMPEG_FEHLT = "ffmpeg_fehlt"
NICHT_ANGELEGT = "nicht_angelegt"

#: Ergebnis von ``erzeuge_kopie``: die Freigabe ist weg (die Schlange pausiert, nichts wird als Fehler gemerkt)
WEG = "weg"


def braucht_hoerkopie(codec: str | None) -> bool:
    """Braucht ein Track mit diesem Codec eine Hörkopie? ``mp3`` und ``aac`` spielen überall (Original); ``vorbis``, ``opus``, ``alac``, ``flac``,
    ``pcm_*`` und alles Unbekannte (auch ``None`` und ``""``) bekommen eine Kopie. **Die** eine Stelle dieser Regel (Vertrag W, 14.8)."""
    return (codec or "").strip().lower() not in _OHNE_KOPIE


def kennung(folge: str, track: int, groesse: int, mtime_ns: int) -> str:
    """Die ersten 16 Zeichen von ``sha1(folge|track|größe|Änderungszeit)``: ändert sich das Original, entsteht eine neue Kopie."""
    return hashlib.sha1(f"{folge}|{track}|{groesse}|{mtime_ns}".encode("utf-8", "surrogatepass")).hexdigest()[:16]  # noqa: S324 - keine Sicherheitsfunktion


def ffmpeg_programm(hass: HomeAssistant) -> str | None:
    """Erstwahl ``get_ffmpeg_manager(hass).binary``, wenn die Integration ``ffmpeg`` geladen ist, sonst ``shutil.which("ffmpeg")``; ``None``, wenn es
    keines gibt. Blockiert (``which``): im Executor aufrufen."""
    try:
        from homeassistant.components.ffmpeg import get_ffmpeg_manager

        binary = get_ffmpeg_manager(hass).binary
        if binary and shutil.which(binary):
            return shutil.which(binary)
    except (ImportError, ValueError, KeyError, AttributeError):
        pass
    return ffprobe.ffmpeg_pfad()


def fs_grenze(dauer_s: float) -> int:
    """``-fs``: Dauer × 12 KB/s × 1,2, dazu ein fester Sockel für den Behälter (``ftyp`` und ``moov``; sonst scheiterten sehr kurze Dateien)."""
    return int(dauer_s * HOERKOPIE_BYTES_JE_S * HOERKOPIE_FS_FAKTOR) + HOERKOPIE_FS_SOCKEL_BYTES


def t_grenze(dauer_s: float) -> int:
    """``-t``: Dauer + Zugabe, nie über dem Dauerdeckel."""
    return min(int(math.ceil(dauer_s)) + HOERKOPIE_T_ZUGABE_S, DAUER_DECKEL_S)


def baue_ffmpeg_befehl(programm: str, quelle: str | os.PathLike[str], endung: str, ziel_part: str | os.PathLike[str], dauer_s: float) -> list[str]:
    """Die Argumentliste (Design 11.4.7). Nie über eine Shell; ``-map 0:a:0`` nimmt genau einen Audiostrom, ``-ac 2`` mischt Mehrkanal auf Stereo,
    ``-t`` und ``-fs`` begrenzen die Ausgabe, ``+faststart`` legt den Index nach vorn (Range ab der ersten Anfrage). Wirft ``KeyError`` bei unbekannter Endung."""
    return [
        programm,
        "-nostdin",
        "-v",
        "error",
        "-protocol_whitelist",
        "file",
        "-f",
        FORMAT_JE_ENDUNG[endung.lower()],
        "-i",
        f"file:{os.path.abspath(os.fspath(quelle))}",
        "-map",
        "0:a:0",
        "-vn",
        "-ac",
        "2",
        "-map_metadata",
        "-1",
        "-t",
        str(t_grenze(dauer_s)),
        "-fs",
        str(fs_grenze(dauer_s)),
        "-c:a",
        "aac",
        "-b:a",
        f"{HOERKOPIE_KBIT}k",
        "-movflags",
        "+faststart",
        "-f",
        "mp4",
        f"file:{os.path.abspath(os.fspath(ziel_part))}",
    ]


def ist_unplausibel(dauer_s: float, groesse_bytes: int) -> bool:
    """Plausibilität Größe zu Dauer: Würde die Kopie (Dauer × 12 KB/s) mehr als ``HOERKOPIE_PLAUSIBEL_FAKTOR`` mal größer als die Quelle, ist die Dauer
    im Dateikopf verdächtig (FLAC-Stille: 2 Stunden in 1,1 MB). Keine Kopie."""
    return dauer_s * HOERKOPIE_BYTES_JE_S > max(groesse_bytes, 1) * HOERKOPIE_PLAUSIBEL_FAKTOR


@dataclass
class Auftrag:
    """Ein Track in der Schlange."""

    serie_id: str
    folge: str
    track: int
    quelle: Path
    groesse: int
    nutzer_id: str | None = None
    vorgezogen: bool = False
    dauer_s: float | None = None  # nur für die Schätzung der Wartezeit
    laeuft: bool = False

    @property
    def schluessel(self) -> tuple[str, str, int]:
        return (self.serie_id, self.folge, self.track)


@dataclass
class Ergebnis:
    """Ausgang von ``erzeuge_kopie``: ``zustand`` ``fertig``, ``fehler`` oder ``WEG``."""

    zustand: str
    grund: str | None = None
    kennung: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def sicherer_name(serie_id: str) -> bool:
    """Die Serien-ID wird ein Ordnername unter ``hoerkopien/``: nie ein Pfad."""
    return bool(serie_id) and serie_id not in (".", "..") and not any(c in serie_id for c in "/\\\0") and not serie_id.startswith(".")


def kopie_pfad(wurzel: Path, serie_id: str, kenn: str) -> Path:
    """``hoerkopien/<serie_id>/<kennung>.m4a``: entsteht **nur** aus ``serie_id`` und ``kennung``, beide vom Backend (nie aus der Anfrage)."""
    return wurzel / serie_id / f"{kenn}.m4a"


def finde_kopie(wurzel: Path, serie_id: str, kenn: str) -> Path | None:
    """Zweig „Kopie“ der Audio-Ansicht (Vertrag W, 14.5, Punkt 4b): der Pfad wird aufgelöst und muss unter dem aufgelösten ``hoerkopien/`` **und**
    unter dem Ordner der eigenen Serie liegen; nur Dateien. Synchron (Executor). ``None``, wenn es sie nicht gibt."""
    if not sicherer_name(serie_id) or len(kenn) != 16 or not all(c in "0123456789abcdef" for c in kenn):
        return None
    try:
        basis = wurzel.resolve()
        fertig = kopie_pfad(basis, serie_id, kenn).resolve()
        if not fertig.is_relative_to(basis) or not fertig.is_relative_to((basis / serie_id).resolve()):
            return None
        return fertig if fertig.is_file() and fertig.stat().st_size > 0 else None
    except (OSError, ValueError, RuntimeError):
        return None


def _statistik(quelle: Path) -> tuple[int, int] | None:
    """``(Größe, Änderungszeit in ns)`` oder ``None``."""
    try:
        st = quelle.stat()
    except OSError:
        return None
    return st.st_size, st.st_mtime_ns


def _kind_grenzen() -> None:  # pragma: no cover - läuft im Kindprozess
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (HOERKOPIE_SPEICHER_BYTES, HOERKOPIE_SPEICHER_BYTES))
    except (ImportError, ValueError, OSError):
        pass
    with contextlib.suppress(OSError, AttributeError):
        os.nice(HOERKOPIE_NICE)


def _laufe_ffmpeg(args: list[str], halter: dict[str, Any]) -> int | None:
    """Startet ``ffmpeg`` (Liste von Argumenten, keine Shell, ``RLIMIT_AS``, ``nice``) mit **fester** Zeitgrenze ``HOERKOPIE_ZEITGRENZE_S``.
    Rückgabe: Rückgabewert; ``None`` bei Zeitüberschreitung (der Prozess ist dann beendet). Wirft ``OSError``, wenn es sich nicht starten lässt.
    ``halter['prozess']`` hält den laufenden Prozess, damit ``abbrechen()`` ihn beenden kann."""
    proc = subprocess.Popen(  # noqa: S603
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        preexec_fn=_kind_grenzen if os.name == "posix" else None,  # noqa: PLW1509
    )
    halter["prozess"] = proc
    try:
        _aus, fehler = proc.communicate(timeout=HOERKOPIE_ZEITGRENZE_S)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        _LOGGER.warning("ffmpeg: feste Zeitgrenze überschritten (%s s)", HOERKOPIE_ZEITGRENZE_S)
        return None
    finally:
        halter["prozess"] = None
    if proc.returncode:
        _LOGGER.warning("ffmpeg (Hörkopie) endet mit %s: %s", proc.returncode, (fehler or b"")[-300:].decode("utf-8", "replace").strip())
    return proc.returncode


def erzeuge_kopie(auftrag: Auftrag, programm: str, medien: Path, wurzel: Path, halter: dict[str, Any]) -> Ergebnis:
    """Synchron (Executor): prüft, kodiert nach ``<kennung>.m4a.part`` und benennt um. Alle Grenzen aus Vertrag W, 14.8 gelten hier.

    ``fertig`` auch, wenn die Kopie schon da ist. ``WEG``, wenn die Freigabe nicht erreichbar ist (kein Fehlerzustand, die Schlange pausiert)."""
    try:
        if not medien.is_dir():
            return Ergebnis(WEG)
        stat = _statistik(auftrag.quelle)
        if stat is None:
            return Ergebnis("fehler", KODIEREN_FEHLGESCHLAGEN)
        groesse, mtime_ns = stat
        kenn = kennung(auftrag.folge, auftrag.track, groesse, mtime_ns)
        ziel = kopie_pfad(wurzel, auftrag.serie_id, kenn)
        if ziel.is_file() and ziel.stat().st_size > 0:
            return Ergebnis("fertig", kennung=kenn)
        endung = ffprobe.endung_von(auftrag.quelle.name)
        probe = ffprobe.probe_datei(auftrag.quelle, endung, zeitlimit=MEDIENINFO_ZEITGRENZE_S)
        if probe.status != ffprobe.OK or not probe.hat_audio or probe.dauer_s is None or not probe.dauer_s > 0:
            return Ergebnis(WEG) if not medien.is_dir() else Ergebnis("fehler", KODIEREN_FEHLGESCHLAGEN, kenn)
        dauer = float(probe.dauer_s)
        if dauer > DAUER_DECKEL_S:
            return Ergebnis("fehler", ZU_LANG, kenn)
        if ist_unplausibel(dauer, groesse):
            return Ergebnis("fehler", UNPLAUSIBEL, kenn)
        grenze = fs_grenze(dauer)
        if wurzel.is_dir() and dateien.ordner_groesse(wurzel)[1] >= HOERKOPIE_KONTINGENT_BYTES:
            return Ergebnis("fehler", KEIN_SPEICHER, kenn)
        try:
            ziel.parent.mkdir(parents=True, exist_ok=True)
            if dateien.freier_platz(ziel.parent) < grenze:
                return Ergebnis("fehler", KEIN_SPEICHER, kenn)
        except OSError as err:
            return _ergebnis_aus_oserror(err, medien, kenn)
        part = ziel.with_name(ziel.name + ".part")
        try:
            with contextlib.suppress(FileNotFoundError):
                part.unlink()
            try:
                rc = _laufe_ffmpeg(baue_ffmpeg_befehl(programm, auftrag.quelle, endung, part, dauer), halter)
            except OSError as err:
                _LOGGER.warning("ffmpeg lässt sich nicht starten: %s", err)
                return Ergebnis("fehler", FFMPEG_FEHLT, kenn)
            if rc is None:
                return Ergebnis("fehler", ZEITGRENZE, kenn)
            if halter.get("abgebrochen"):
                return Ergebnis(WEG)
            if not medien.is_dir():
                return Ergebnis(WEG)
            groesse_aus = part.stat().st_size if part.is_file() else 0
            if rc != 0 or groesse_aus <= 0:
                return Ergebnis("fehler", KODIEREN_FEHLGESCHLAGEN, kenn)
            if groesse_aus >= grenze:  # ``-fs`` hat die Ausgabe abgeschnitten
                return Ergebnis("fehler", KODIEREN_FEHLGESCHLAGEN, kenn)
            os.replace(part, ziel)
            return Ergebnis("fertig", kennung=kenn)
        except OSError as err:
            return _ergebnis_aus_oserror(err, medien, kenn)
        finally:
            with contextlib.suppress(OSError):
                part.unlink()
    except OSError:
        return Ergebnis(WEG)


def _ergebnis_aus_oserror(err: OSError, medien: Path, kenn: str) -> Ergebnis:
    if err.errno in (errno.ENOSPC, errno.EDQUOT):
        return Ergebnis("fehler", KEIN_SPEICHER, kenn)
    return Ergebnis(WEG) if not medien.is_dir() else Ergebnis("fehler", KODIEREN_FEHLGESCHLAGEN, kenn)


def raeume_auf(wurzel: Path, bekannte: dict[str, set[str]], geschuetzt: set[str], nur_part: bool) -> tuple[int, int]:
    """Synchron (Executor). Löscht ``*.part`` immer. Mit ``nur_part=False`` zusätzlich verwaiste Kopien:

    * ein Ordner einer Serie, die es nicht mehr gibt (nicht in ``bekannte`` und nicht in ``geschuetzt``): ganz;
    * in einer bekannten Serie eine ``.m4a``, deren Kennung der Store nicht (mehr) kennt (veraltet, Folge gelöscht): die Datei.

    ``geschuetzt``: Serien mit einem Eintrag im Papierkorb (Papierkorb und Umbenennen berühren Kopien nicht). Gibt ``(Teile, Dateien)`` zurück."""
    teile = dateien_geloescht = 0
    try:
        ordner = [e for e in os.scandir(wurzel) if e.is_dir(follow_symlinks=False)]
    except OSError:
        return 0, 0
    for e in ordner:
        pfad = Path(e.path)
        try:
            inhalt = list(os.scandir(pfad))
        except OSError:
            continue
        for f in inhalt:
            if f.name.endswith(".part") and f.is_file(follow_symlinks=False):
                with contextlib.suppress(OSError):
                    os.unlink(f.path)
                    teile += 1
        if nur_part or e.name in geschuetzt:
            continue
        if e.name not in bekannte:
            with contextlib.suppress(OSError):
                n = dateien.loesche_baum(pfad)
                dateien_geloescht += 1 if n else 0
            continue
        kennungen = bekannte[e.name]
        for f in inhalt:
            if f.name.endswith(".m4a") and f.is_file(follow_symlinks=False) and f.name[:-4] not in kennungen:
                with contextlib.suppress(OSError):
                    os.unlink(f.path)
                    dateien_geloescht += 1
    return teile, dateien_geloescht


class HoerkopieDienst:
    """Die Schlange der Hörkopien (``hub.hoerkopie``)."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        #: Pfad zu ``ffmpeg`` (``None``: keine Fähigkeit ``hoerkopie``); gesetzt in ``async_start``
        self.programm: str | None = None
        self._schlange: list[Auftrag] = []
        self._laeuft: Auftrag | None = None
        #: in diesem Start schon versucht (``(Serie, Folge, Track)``): ein Fehler wird nicht ständig neu versucht
        self._versucht: set[tuple[str, str, int]] = set()
        self._task: asyncio.Task | None = None
        self._pausiert = False
        self._halter: dict[str, Any] = {"prozess": None}
        #: Codecs, die ein Lauf von ``ffprobe`` gelesen hat, solange der Store sie nicht kennt: ``(Serie, Folge, Track, Größe, mtime)`` -> Codec
        self._codec_zwischen: dict[tuple, str | None] = {}  # ``None``: nicht lesbar

    # --- Start und Ende -----------------------------------------------------------------------------------

    async def async_start(self) -> None:
        self.programm = await self.hub.hass.async_add_executor_job(ffmpeg_programm, self.hub.hass)

    @property
    def verfuegbar(self) -> bool:
        """Fähigkeit ``hoerkopie``: nur, wenn ``ffmpeg`` da ist (Vertrag W, 14.1)."""
        return self.programm is not None

    def beim_start(self) -> None:
        """Einmal nach dem Start, im Hintergrund: ``*.part`` löschen und verwaiste Kopien wegräumen (nur nach gelungener Prüfung der Freigabe)."""
        self.hub.hass.async_create_background_task(self._raeume_auf(), "tobibox_hoerkopie_aufraeumen")

    async def _raeume_auf(self, nur_part: bool | None = None) -> None:
        hub = self.hub
        wurzel = hub.pfade.hoerkopien
        if nur_part is None:
            nur_part = hub.medien.geprueft_am is None  # NAS beim Start nicht erreichbar: es wird nie etwas gelöscht
        try:
            if not nur_part:
                bekannte = {sid: hub.medieninfo.hoerkopie_kennungen(sid) for sid in hub.medien.serien}
                geschuetzt = await hub.hass.async_add_executor_job(self._serien_im_papierkorb)
            else:
                bekannte, geschuetzt = {}, set()
            teile, geloescht = await hub.hass.async_add_executor_job(raeume_auf, wurzel, bekannte, geschuetzt, nur_part)
            if teile or geloescht:
                _LOGGER.info("Hörkopien aufgeräumt: %s halbe Dateien, %s verwaiste Kopien", teile, geloescht)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Aufräumen der Hörkopien fehlgeschlagen")

    def _serien_im_papierkorb(self) -> set[str]:
        from .media import lese_papierkorb

        aus: set[str] = set()
        for meta in lese_papierkorb(self.hub.pfade.papierkorb):
            sid = meta.get("serie_id")
            if isinstance(sid, str):
                aus.add(sid)
            sj = meta.get("serie_json")
            if isinstance(sj, dict) and isinstance(sj.get("id"), str):
                aus.add(sj["id"])
        return aus

    def abbrechen(self) -> None:
        """Beim Beenden der Integration: Schlange leeren, laufenden ``ffmpeg`` beenden."""
        self._schlange.clear()
        self._halter["abgebrochen"] = True
        proc = self._halter.get("prozess")
        if proc is not None:
            with contextlib.suppress(OSError, ProcessLookupError):
                proc.kill()
        if self._task is not None and not self._task.done():
            self._task.cancel()

    async def warte_auf_ende(self) -> None:
        """Für Tests: wartet, bis die Schlange leer ist (oder pausiert)."""
        while self._task is not None and not self._task.done():
            await asyncio.shield(self._task)

    def fortsetzen(self) -> None:
        """Die Freigabe ist wieder da (nach einer gelungenen Prüfung): eine pausierte Schlange läuft weiter."""
        if self._pausiert:
            self._pausiert = False
            self._starte()

    # --- Zustand (nur Arbeitsspeicher und Store, nie die Platte: läuft in der Event-Loop) ------------------

    def in_schlange(self, serie_id: str, folge: str, track: int | None = None) -> bool:
        return any(a.serie_id == serie_id and a.folge == folge and (track is None or a.track == track) for a in self._alle())

    def _alle(self) -> list[Auftrag]:
        return ([self._laeuft] if self._laeuft is not None else []) + self._schlange

    def schlange_zaehler(self) -> dict[str, int]:
        """``hello.grenzen.hoerkopie_schlange``: der Zähler für „Technik“ (Design 5.9)."""
        alle = self._alle()
        return {
            "dateien": len(alle),
            "dateien_max": HOERKOPIE_SCHLANGE_DATEIEN,
            "bytes": sum(a.groesse for a in alle),
            "bytes_max": HOERKOPIE_SCHLANGE_BYTES,
        }

    def folge_zustand(self, serie_id: str, folge: str) -> dict[str, Any] | None:
        """``hoerkopie`` des Folge-Objekts von ``serie/get`` (Vertrag W, 14.2): ``{"zustand": original|nicht_angelegt|wartet|fertig|fehler, "grund"?}``.
        ``None``, solange die Codecs unbekannt sind und kein Zustand vorliegt. Läuft in der Event-Loop: nur Store und Schlange."""
        medieninfo = self.hub.medieninfo
        codecs = medieninfo.codecs(serie_id, folge)
        gespeichert = medieninfo.hoerkopie_tracks(serie_id, folge)
        wartet = self.in_schlange(serie_id, folge)
        if codecs is None:
            if wartet:
                return {"zustand": "wartet"}
            fehler = next((v for v in gespeichert.values() if v["zustand"] == "fehler"), None)
            if fehler is not None:
                return {"zustand": "fehler", **({"grund": fehler["grund"]} if fehler.get("grund") else {})}
            return {"zustand": "fertig"} if gespeichert else None
        noetig = [i for i, c in enumerate(codecs) if braucht_hoerkopie(c)]
        if not noetig:
            return {"zustand": "original"}
        fehler = next((gespeichert[str(i)] for i in noetig if gespeichert.get(str(i), {}).get("zustand") == "fehler"), None)
        if fehler is not None:
            return {"zustand": "fehler", **({"grund": fehler["grund"]} if fehler.get("grund") else {})}
        if wartet:
            return {"zustand": "wartet"}
        if all(gespeichert.get(str(i), {}).get("zustand") == "fertig" for i in noetig):
            return {"zustand": "fertig"}
        return {"zustand": "nicht_angelegt"}

    # --- Codec eines Tracks -------------------------------------------------------------------------------

    async def braucht_kopie(self, serie_id: str, folge: str, track: int, quelle: Path) -> bool:
        """Braucht dieser Track eine Hörkopie? Nach seinem Codec (``braucht_hoerkopie``): aus dem Store (``codecs``), sonst ein Lauf von ``ffprobe``
        (Executor, feste Zeitgrenze ``MEDIENINFO_ZEITGRENZE_S``), solange das Nachholen im Hintergrund die Folge noch nicht erreicht hat.

        Eine Datei, die ``ffprobe`` gar nicht lesen kann, bekommt **keine** Kopie (auch ``ffmpeg`` könnte sie nicht lesen): sie bleibt beim Original und
        scheitert im Browser wie bisher."""
        codecs = self.hub.medieninfo.codecs(serie_id, folge)
        if codecs is not None and track < len(codecs):
            return braucht_hoerkopie(codecs[track])
        stat = await self.hub.hass.async_add_executor_job(_statistik, quelle)
        schluessel = (serie_id, folge, track, *(stat or (0, 0)))
        if schluessel not in self._codec_zwischen:
            probe = await self.hub.hass.async_add_executor_job(lambda: ffprobe.probe_datei(quelle, zeitlimit=MEDIENINFO_ZEITGRENZE_S))
            if len(self._codec_zwischen) > 256:
                self._codec_zwischen.clear()
            self._codec_zwischen[schluessel] = (probe.codec or "") if probe.status == ffprobe.OK and probe.hat_audio else None
        codec = self._codec_zwischen[schluessel]
        return codec is not None and braucht_hoerkopie(codec)

    async def kopie_datei(self, serie_id: str, folge: str, track: int, quelle: Path) -> Path | None:
        """Die fertige Kopie dieses Tracks (aufgelöst, unter ``hoerkopien/``) oder ``None``; für die Audio-Ansicht. Nur eine Kopie, die zum
        **aktuellen** Original passt (Kennung aus Größe und Änderungszeit)."""
        stat = await self.hub.hass.async_add_executor_job(_statistik, quelle)
        if stat is None:
            return None
        kenn = kennung(folge, track, *stat)
        return await self.hub.hass.async_add_executor_job(finde_kopie, self.hub.pfade.hoerkopien, serie_id, kenn)

    # --- Anfordern ------------------------------------------------------------------------------------------

    def _position_und_warten(self, auftrag: Auftrag) -> tuple[int, int]:
        """``(Platz in der Schlange ab 1, geschätzte Wartezeit in Sekunden)``: das, was vor ihm liegt, und er selbst, je mit 15 mal Echtzeit."""
        alle = self._alle()
        platz = next((i for i, a in enumerate(alle) if a.schluessel == auftrag.schluessel), len(alle) - 1)
        summe = sum(a.dauer_s or HOERKOPIE_SCHAETZ_UNBEKANNT_S for a in alle[: platz + 1])
        return platz + 1, max(1, int(math.ceil(summe / HOERKOPIE_SCHAETZ_FAKTOR)))

    def _antwort_wartet(self, schluessel: tuple[str, str, int]) -> dict[str, Any]:
        auftrag = next(a for a in self._alle() if a.schluessel == schluessel)
        position, warte_s = self._position_und_warten(auftrag)
        return {"zustand": "wird_vorbereitet", "warte_s": warte_s, "position": position}

    async def anfordern(
        self, nutzer_id: str | None, serie_id: str, folge: str, track: int, quelle: Path, vorbereiten: bool = True
    ) -> dict[str, Any]:
        """Der Kern von ``audio/bereit`` für einen Track, der eine Kopie braucht. Antwort:

        * ``{"zustand": "fertig"}``: die Kopie ist da (``audio/bereit`` macht daraus ``bereit`` mit ``quelle="kopie"``);
        * ``{"zustand": "wird_vorbereitet", "warte_s", "position"}``: sie steht in der Schlange (neu oder schon vorher; idempotent);
        * ``{"zustand": "fehlt", "grund"}``: Fehler dieses Starts, ``nicht_angelegt`` (nur mit ``vorbereiten=False``) oder ``ffmpeg_fehlt``.

        Wirft ``hoerkopie_warteschlange_voll``, wenn die Schlange ihre Grenze hat."""
        hub = self.hub
        schluessel = (serie_id, folge, track)
        if self.programm is None:
            return {"zustand": "fehlt", "grund": FFMPEG_FEHLT}
        stat = await hub.hass.async_add_executor_job(_statistik, quelle)
        if stat is None:
            return {"zustand": "fehlt", "grund": "medien_nicht_erreichbar"}
        groesse, mtime_ns = stat
        kenn = kennung(folge, track, groesse, mtime_ns)
        eintrag = hub.medieninfo.hoerkopie_tracks(serie_id, folge).get(str(track))
        if eintrag is not None and eintrag["kennung"] != kenn:
            hub.medieninfo.loesche_hoerkopie(serie_id, folge, track)  # das Original hat sich geändert: die alte Kopie gilt nicht mehr
            eintrag = None
        if eintrag is not None and eintrag["zustand"] == "fertig":
            if await hub.hass.async_add_executor_job(finde_kopie, hub.pfade.hoerkopien, serie_id, kenn) is not None:
                return {"zustand": "fertig"}
            hub.medieninfo.loesche_hoerkopie(serie_id, folge, track)  # die Datei fehlt: neu machen
            eintrag = None
        if eintrag is None and await hub.hass.async_add_executor_job(finde_kopie, hub.pfade.hoerkopien, serie_id, kenn) is not None:
            hub.medieninfo.setze_hoerkopie(serie_id, folge, track, "fertig", kenn)  # Store verloren, Datei da: wiedergefunden
            return {"zustand": "fertig"}
        if any(a.schluessel == schluessel for a in self._alle()):
            return self._antwort_wartet(schluessel)
        if eintrag is not None and eintrag["zustand"] == "fehler" and schluessel in self._versucht:
            return {"zustand": "fehlt", "grund": eintrag.get("grund") or KODIEREN_FEHLGESCHLAGEN}  # ein Versuch je Datei und Start
        if not vorbereiten:
            if eintrag is not None and eintrag["zustand"] == "fehler":
                return {"zustand": "fehlt", "grund": eintrag.get("grund") or KODIEREN_FEHLGESCHLAGEN}
            return {"zustand": "fehlt", "grund": NICHT_ANGELEGT}
        self._einreihen(Auftrag(serie_id, folge, track, quelle, groesse, nutzer_id, dauer_s=hub.medieninfo.dauer_s(serie_id, folge)), mit_vorziehen=True)
        return self._antwort_wartet(schluessel)

    def _einreihen(self, auftrag: Auftrag, mit_vorziehen: bool) -> None:
        """Wirft ``hoerkopie_warteschlange_voll``, wenn die Schlange ihre Grenze hat (Dateien oder Quellbytes)."""
        alle = self._alle()
        if len(alle) >= HOERKOPIE_SCHLANGE_DATEIEN or sum(a.groesse for a in alle) + auftrag.groesse > HOERKOPIE_SCHLANGE_BYTES:
            raise TobiboxFehler("hoerkopie_warteschlange_voll")
        if mit_vorziehen and auftrag.nutzer_id is not None:
            schon = sum(1 for a in alle if a.nutzer_id == auftrag.nutzer_id and a.vorgezogen)
            if schon < HOERKOPIE_VORZIEHEN_JE_BENUTZER:
                auftrag.vorgezogen = True
        if auftrag.vorgezogen:
            pos = 0
            while pos < len(self._schlange) and self._schlange[pos].vorgezogen:
                pos += 1  # hinter die schon vorgezogenen (Ankunftsreihenfolge), vor alles andere
            self._schlange.insert(pos, auftrag)
        else:
            self._schlange.append(auftrag)
        self._pausiert = False
        self._starte()

    # --- Neu einsortiert, neu erzeugen --------------------------------------------------------------------------

    def neu_einsortiert(self, serie_id: str, folgen: list[str]) -> None:
        """Neu Einsortiertes bekommt **sofort** seine Kopien, im Hintergrund (Vertrag W, 14.8 a). Die Meldung „fertig“ wartet nicht darauf. Läuft
        ohne ``ffmpeg`` gar nicht; ein Fehler hier hält das Einsortieren nie auf."""
        if self.programm is None or not folgen:
            return
        self.hub.hass.async_create_background_task(self._neu_einsortiert(serie_id, folgen), "tobibox_hoerkopie_neu")

    async def _neu_einsortiert(self, serie_id: str, folgen: list[str]) -> None:
        try:
            for folge in folgen:
                codecs = self.hub.medieninfo.codecs(serie_id, folge)
                if codecs is None:
                    continue
                for nr, codec in enumerate(codecs):
                    if not braucht_hoerkopie(codec):
                        continue
                    quelle = await self._quelle(serie_id, folge, nr)
                    if quelle is None:
                        continue
                    await self._einreihen_wenn_noetig(serie_id, folge, nr, quelle, None)
        except TobiboxFehler as err:
            _LOGGER.info("Hörkopie für neu Einsortiertes nicht eingereiht: %s (der Bestand wird beim Reinhören angefordert)", err.code)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Hörkopien für neu Einsortiertes nicht eingereiht")

    async def _quelle(self, serie_id: str, folge: str, track: int) -> Path | None:
        from .audio import suche_datei

        ergebnis, pfad = await self.hub.hass.async_add_executor_job(suche_datei, self.hub, serie_id, folge, track)
        return pfad if ergebnis == "ok" else None

    async def _einreihen_wenn_noetig(self, serie_id: str, folge: str, track: int, quelle: Path, nutzer_id: str | None) -> None:
        stat = await self.hub.hass.async_add_executor_job(_statistik, quelle)
        if stat is None or self.in_schlange(serie_id, folge, track):
            return
        kenn = kennung(folge, track, *stat)
        if await self.hub.hass.async_add_executor_job(finde_kopie, self.hub.pfade.hoerkopien, serie_id, kenn) is not None:
            self.hub.medieninfo.setze_hoerkopie(serie_id, folge, track, "fertig", kenn)
            return
        self._einreihen(Auftrag(serie_id, folge, track, quelle, stat[0], nutzer_id, dauer_s=self.hub.medieninfo.dauer_s(serie_id, folge)), mit_vorziehen=False)

    async def neu_erzeugen(self, serie_id: str | None) -> int:
        """Befehl 45: Löscht Kopie und Zustand und stellt die Folge neu in die Schlange. Ohne ``serie_id``: alle Folgen mit Zustand ``fehler``; mit: alle
        Folgen dieser Serie mit gespeichertem Zustand (``fertig`` oder ``fehler``). Gibt die Zahl der eingereihten **Folgen** zurück. Wirft
        ``hoerkopie_warteschlange_voll``; was bis dahin eingereiht ist, bleibt."""
        hub = self.hub
        if self.programm is None:
            return 0
        if serie_id is not None:
            hub.medien.finde(serie_id)
        ziele: list[tuple[str, str]] = []
        for sid, folge in hub.medieninfo.hoerkopie_folgen():
            if serie_id is not None and sid != serie_id:
                continue
            info = hub.medien.serien.get(sid)
            if info is None or folge not in info.serie.folgen:
                continue
            tracks = hub.medieninfo.hoerkopie_tracks(sid, folge)
            if serie_id is None and not any(v["zustand"] == "fehler" for v in tracks.values()):
                continue
            ziele.append((sid, folge))
        eingereiht = 0
        for sid, folge in ziele:
            tracks = hub.medieninfo.hoerkopie_tracks(sid, folge)
            neu = 0
            for nr_text in sorted(tracks, key=int):
                nr = int(nr_text)
                quelle = await self._quelle(sid, folge, nr)
                if quelle is None:
                    continue
                stat = await hub.hass.async_add_executor_job(_statistik, quelle)
                if stat is None:
                    continue
                alt = tracks[nr_text]
                await hub.hass.async_add_executor_job(self._loesche_datei, sid, alt["kennung"])
                hub.medieninfo.loesche_hoerkopie(sid, folge, nr)
                self._versucht.discard((sid, folge, nr))
                if not self.in_schlange(sid, folge, nr):
                    self._einreihen(Auftrag(sid, folge, nr, quelle, stat[0], None, dauer_s=hub.medieninfo.dauer_s(sid, folge)), mit_vorziehen=False)
                neu += 1
            eingereiht += 1 if neu else 0
        return eingereiht

    def _loesche_datei(self, serie_id: str, kenn: str) -> None:
        pfad = finde_kopie(self.hub.pfade.hoerkopien, serie_id, kenn)
        if pfad is not None:
            with contextlib.suppress(OSError):
                pfad.unlink()

    # --- Arbeit ---------------------------------------------------------------------------------------------------

    def _starte(self) -> None:
        if self._schlange and not self._pausiert and (self._task is None or self._task.done()):
            self._halter["abgebrochen"] = False
            self._task = self.hub.hass.async_create_background_task(self._arbeite(), "tobibox_hoerkopie")

    async def _arbeite(self) -> None:
        """Eine Datei zugleich (``HOERKOPIE_PARALLEL`` = 1)."""
        assert HOERKOPIE_PARALLEL == 1  # die Schlange arbeitet nacheinander
        hub = self.hub
        while self._schlange and not self._pausiert:
            auftrag = self._schlange.pop(0)
            auftrag.laeuft = True
            self._laeuft = auftrag
            try:
                ergebnis = await hub.hass.async_add_executor_job(
                    erzeuge_kopie, auftrag, self.programm, hub.pfade.medien, hub.pfade.hoerkopien, self._halter
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("Hörkopie für %s/%s nicht erzeugt", auftrag.serie_id, auftrag.folge)
                ergebnis = Ergebnis("fehler", KODIEREN_FEHLGESCHLAGEN)
            finally:
                self._laeuft = None
                auftrag.laeuft = False
            if ergebnis.zustand == WEG:
                if self._halter.get("abgebrochen"):
                    return
                _LOGGER.info("Hörkopien pausiert: die Freigabe ist nicht erreichbar")
                self._schlange.insert(0, auftrag)  # bleibt vorn; ``fortsetzen()`` oder das nächste Anfordern nimmt sie wieder auf
                self._pausiert = True
                return
            self._versucht.add(auftrag.schluessel)
            info = hub.medien.serien.get(auftrag.serie_id)
            if info is None or auftrag.folge not in info.serie.folgen:
                continue  # die Folge ist inzwischen weg: nichts merken (das Aufräumen entfernt die Datei)
            kenn = ergebnis.kennung or ""
            if ergebnis.zustand == "fertig":
                hub.medieninfo.setze_hoerkopie(auftrag.serie_id, auftrag.folge, auftrag.track, "fertig", kenn)
            else:
                _LOGGER.warning("Hörkopie für %s/%s (Track %s) fehlgeschlagen: %s", auftrag.serie_id, auftrag.folge, auftrag.track, ergebnis.grund)
                hub.medieninfo.setze_hoerkopie(auftrag.serie_id, auftrag.folge, auftrag.track, "fehler", kenn or "0" * 16, ergebnis.grund)
            hub.emit("medien", "serien_geaendert", {"serie_ids": [auftrag.serie_id]})
