"""Audiodateien prüfen und Tags lesen mit ``ffprobe`` (Vertrag W, 5.4 und 11.2; D5).

Der Aufruf ist gehärtet (Pflicht, W-16):

* Liste von Argumenten, nie über eine Shell; der Pfad geht als ``file:<absoluter Pfad>`` hinein.
* ``-protocol_whitelist file`` und ein **erzwungenes Format** aus der Endung.
* Zeitlimit 30 s, Speicherlimit ``RLIMIT_AS`` 1 GiB (soweit das System es erlaubt).
* Danach wird ``format_name`` gegen die erlaubte Liste geprüft und mindestens ein Audio-Strom verlangt.

Abweichung vom Wortlaut des Vertrags: ``-nostdin`` kennt ``ffprobe`` nicht (nur ``ffmpeg``;
geprüft mit ffprobe 6.1: „Option not found“). Statt dessen wird die Standardeingabe mit
``stdin=DEVNULL`` geschlossen. ``ffmpeg`` (Probedekodierung) bekommt ``-nostdin``.

Alle Funktionen hier sind synchron und blockieren; HA ruft sie über ``async_add_executor_job``.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from .const import (
    ERLAUBTE_FORMATNAMEN,
    FFPROBE_SPEICHER_BYTES,
    FFPROBE_ZEITLIMIT_S,
    FORMAT_JE_ENDUNG,
)
from .namen import norm_tagwert

_LOGGER = logging.getLogger(__name__)

# Codes des Ergebnisses
OK = "ok"
FFPROBE_FEHLT = "ffprobe_fehlt"
NICHT_LESBAR = "nicht_lesbar"
FORMAT_NICHT_ERLAUBT = "format_nicht_erlaubt"
KOPIERSCHUTZ = "kopierschutz"
PROBEDEKODIERUNG = "probedekodierung_fehlgeschlagen"


@dataclass
class Probe:
    """Ergebnis von ``ffprobe`` für eine Datei."""

    status: str = OK  # OK, FFPROBE_FEHLT, NICHT_LESBAR, FORMAT_NICHT_ERLAUBT
    format_name: str | None = None
    codec: str | None = None
    hat_audio: bool = False
    dauer_s: float | None = None
    #: Tags mit kleingeschriebenen Schlüsseln; ``format.tags`` gewinnt gegen die Tags des ersten Audio-Stroms
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Pruefung:
    """Ergebnis der Prüfung nach D5: Probe, Kopierschutz, Probedekodierung."""

    ergebnis: str  # "ok", "warnung", "nicht_moeglich", "ungueltig"
    hinweis: str | None = None  # Code: kopierschutz, nicht_lesbar, probedekodierung_fehlgeschlagen, ffprobe_fehlt
    probe: Probe = field(default_factory=Probe)


def ffprobe_pfad() -> str | None:
    return shutil.which("ffprobe")


def ffmpeg_pfad() -> str | None:
    return shutil.which("ffmpeg")


def endung_von(name: str) -> str:
    return name.rpartition(".")[2].lower() if "." in name else ""


def baue_ffprobe_befehl(pfad: str | os.PathLike[str], endung: str, programm: str = "ffprobe") -> list[str]:
    """Argumentliste für ``ffprobe`` (Vertrag W, 5.4). Wirft ``KeyError`` bei unbekannter Endung."""
    absolut = os.path.abspath(os.fspath(pfad))
    return [
        programm,
        "-v",
        "error",
        "-protocol_whitelist",
        "file",
        "-f",
        FORMAT_JE_ENDUNG[endung.lower()],
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        f"file:{absolut}",
    ]


def baue_dekodier_befehl(pfad: str | os.PathLike[str], endung: str, programm: str = "ffmpeg") -> list[str]:
    """Probedekodierung von 1 s mit ``ffmpeg``, gleiche Härtung wie ``ffprobe``."""
    absolut = os.path.abspath(os.fspath(pfad))
    return [
        programm,
        "-nostdin",
        "-v",
        "error",
        "-protocol_whitelist",
        "file",
        "-f",
        FORMAT_JE_ENDUNG[endung.lower()],
        "-t",
        "1",
        "-i",
        f"file:{absolut}",
        "-f",
        "null",
        "-",
    ]


def _grenzen_setzen() -> None:  # pragma: no cover - läuft im Kindprozess
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (FFPROBE_SPEICHER_BYTES, FFPROBE_SPEICHER_BYTES))
    except (ImportError, ValueError, OSError):
        pass


def _laufe(args: list[str]) -> subprocess.CompletedProcess[bytes] | None:
    """Startet das Programm mit Zeit- und Speicherlimit. ``None`` bei Zeitüberschreitung."""
    try:
        return subprocess.run(  # noqa: S603
            args,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=FFPROBE_ZEITLIMIT_S,
            check=False,
            preexec_fn=_grenzen_setzen if os.name == "posix" else None,  # noqa: PLW1509
        )
    except subprocess.TimeoutExpired:
        _LOGGER.warning("%s: Zeitlimit überschritten: %s", args[0], args[-1])
        return None
    except OSError as err:
        _LOGGER.warning("%s lässt sich nicht starten: %s", args[0], err)
        return None


def _tags_zusammen(daten: dict[str, Any]) -> dict[str, str]:
    """``format.tags`` und Tags des ersten Audio-Stroms; ein Schlüssel im Format gilt vor dem Strom."""
    tags: dict[str, str] = {}
    audio = next((s for s in daten.get("streams", []) if s.get("codec_type") == "audio"), None)
    for quelle in (audio.get("tags") if audio else None, (daten.get("format") or {}).get("tags")):
        for schluessel, wert in (quelle or {}).items():
            tags[str(schluessel).lower()] = str(wert)
    return tags


def sieht_aus_wie_text(pfad: str | os.PathLike[str]) -> bool:
    """Grobe Prüfung: Textdatei (kein NUL-Byte, fast nur druckbare Zeichen) und kein Audio."""
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(8192)
    except OSError:
        return False
    if not kopf or b"\x00" in kopf:
        return False
    druckbar = sum(1 for b in kopf if b in (9, 10, 13) or 32 <= b < 127 or b >= 0xC2)
    return druckbar / len(kopf) >= 0.95


def probe_datei(pfad: str | os.PathLike[str], endung: str | None = None) -> Probe:
    """Öffnet die Datei mit ``ffprobe`` (gehärtet) und liest Format, Codec, Dauer und Tags."""
    programm = ffprobe_pfad()
    if programm is None:
        return Probe(status=FFPROBE_FEHLT)
    endung = (endung or endung_von(os.fspath(pfad))).lower()
    if endung not in FORMAT_JE_ENDUNG:
        return Probe(status=FORMAT_NICHT_ERLAUBT)
    lauf = _laufe(baue_ffprobe_befehl(pfad, endung, programm))
    if lauf is None or lauf.returncode != 0:
        # Eine Textdatei mit Audio-Endung (oder eine Playlist) ist kein Defekt, sondern das falsche Format.
        return Probe(status=FORMAT_NICHT_ERLAUBT if sieht_aus_wie_text(pfad) else NICHT_LESBAR)
    try:
        daten = json.loads(lauf.stdout.decode("utf-8", "replace"))
    except ValueError:
        return Probe(status=NICHT_LESBAR)
    if not isinstance(daten, dict) or not daten.get("format"):
        return Probe(status=NICHT_LESBAR)
    fmt = daten["format"]
    format_name = str(fmt.get("format_name") or "")
    teile = [t for t in format_name.split(",") if t]
    audio = next((s for s in daten.get("streams", []) if s.get("codec_type") == "audio"), None)
    probe = Probe(
        status=OK,
        format_name=format_name,
        codec=(audio or {}).get("codec_name"),
        hat_audio=audio is not None,
        tags=_tags_zusammen(daten),
    )
    try:
        probe.dauer_s = float(fmt["duration"]) if fmt.get("duration") not in (None, "N/A") else None
    except (TypeError, ValueError):
        probe.dauer_s = None
    # DRM (alte iTunes-Käufe): ffprobe meldet den Codec ``drms``; der Strom zählt dann trotzdem als Audio.
    if probe.codec == "drms":
        probe.hat_audio = True
        return probe
    if not teile or not all(t in ERLAUBTE_FORMATNAMEN for t in teile) or not probe.hat_audio:
        probe.status = FORMAT_NICHT_ERLAUBT
    return probe


def probedekodierung(pfad: str | os.PathLike[str], endung: str) -> bool | None:
    """Dekodiert 1 s. ``True`` = gelungen, ``False`` = fehlgeschlagen, ``None`` = nicht prüfbar (kein ``ffmpeg``)."""
    programm = ffmpeg_pfad()
    if programm is None:
        return None
    lauf = _laufe(baue_dekodier_befehl(pfad, endung, programm))
    return lauf is not None and lauf.returncode == 0


def pruefe_datei(pfad: str | os.PathLike[str], endung: str | None = None) -> Pruefung:
    """Prüfung nach D5 für eine Datei: Format, Kopierschutz (``drms``), Probedekodierung von 1 s.

    * ``ergebnis="ungueltig"``: kein Audio dieses Formats (``format_nicht_erlaubt``).
    * ``ergebnis="warnung"``: ``kopierschutz``, ``nicht_lesbar`` oder ``probedekodierung_fehlgeschlagen``.
    * ``ergebnis="nicht_moeglich"``: ``ffprobe`` fehlt.
    """
    endung = (endung or endung_von(os.fspath(pfad))).lower()
    probe = probe_datei(pfad, endung)
    if probe.status == FFPROBE_FEHLT:
        return Pruefung("nicht_moeglich", FFPROBE_FEHLT, probe)
    if probe.status == FORMAT_NICHT_ERLAUBT:
        return Pruefung("ungueltig", FORMAT_NICHT_ERLAUBT, probe)
    if probe.status == NICHT_LESBAR:
        return Pruefung("warnung", NICHT_LESBAR, probe)
    if probe.codec == "drms":
        return Pruefung("warnung", KOPIERSCHUTZ, probe)
    if probedekodierung(pfad, endung) is False:
        return Pruefung("warnung", PROBEDEKODIERUNG, probe)
    return Pruefung("ok", None, probe)


def pruefsumme(pfad: str | os.PathLike[str]) -> str:
    """SHA-256 des Inhalts in Blöcken (für das Erkennen von Doppelten)."""
    import hashlib

    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        while block := f.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Tags (Vertrag W, 11.2)
# --------------------------------------------------------------------------

#: Aliase in Vorrangfolge (der erste nicht leere gilt). Die Schlüssel sind mit ``ffprobe`` 6.1 an
#: erzeugten Dateien belegt (mp3 ID3v2.3/2.4, m4b mit ``use_metadata_tags``, FLAC, Ogg Vorbis) und um die
#: Namen ergänzt, die ``ffprobe`` für ``TIT1`` (``grouping``) liefert.
TAG_SCHLUESSEL: dict[str, tuple[str, ...]] = {
    "album": ("album",),
    "album_interpret": ("album_artist", "albumartist", "album artist"),
    "interpret": ("artist", "author", "composer"),
    "serien_tag": ("series", "serie", "show", "movement_name", "mvnm", "grouping", "tit1", "content_group"),
    "nummer_tag": ("series_part", "series-part", "seriespart", "part", "movement", "mvin", "episode_sort", "episode_id"),
    "titel": ("title",),
    "track": ("track", "tracknumber"),
    "disc": ("disc", "discnumber", "part_of_set"),
    "datum": ("date", "originaldate", "original_date", "year"),
}


def tag(tags: dict[str, str], feld: str) -> str:
    """Der erste nicht leere (normierte) Wert der Aliase eines Feldes, sonst ``""``."""
    for schluessel in TAG_SCHLUESSEL[feld]:
        wert = norm_tagwert(tags.get(schluessel))
        if wert:
            return wert
    return ""
