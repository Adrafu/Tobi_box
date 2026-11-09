#!/usr/bin/env python3
"""Misst die Lautheit von Audiodateien (EBU R128, integriert, in LUFS) mit ``ffmpeg``.

    python tools/lautheit.py DATEI [DATEI ...]      # Messwert je Datei
    python tools/lautheit.py --ordner box/sounds     # alle WAV und MP3 darin
    python tools/lautheit.py --manifest              # box/lautheit.json neu schreiben (nach make_sounds/make_sprache)
    python tools/lautheit.py --normalisiere DATEI    # Kopie DATEI-normalisiert.mp3 bei -18 LUFS mit ReplayGain-Tags

``box/lautheit.json`` hält je Datei die Prüfsumme (SHA-256) und den Messwert fest. So prüft ein Test
auch dort, wo ``ffmpeg`` fehlt, dass die Dateien noch zu den gemessenen passen.

Zielwert (``ZIEL_LUFS``): -18 LUFS. Das ist der Bezugspegel von ReplayGain 2.0 und der
Zielwert, den ``rsgain`` für die Hörspiele auf dem NAS nutzt (``docs/designs/box-software.md``,
D6 und Entscheidung J). Box-Töne und Testmedien liegen am selben Wert, damit ein Ton so laut
klingt wie ein Hörspiel bei gleicher Lautstärke.

Kurze Töne: Die Messung nach R128 arbeitet mit 400-ms-Blöcken. Eine Datei unter 3 s wird deshalb
vor der Messung bis auf mindestens 3 s wiederholt (``-stream_loop``). Gemessen wird also der Ton,
wie er sich im Dauerbetrieb anhört; die Pausen darin fallen durch das Gate wie bei jeder Datei.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ZIEL_LUFS = -18.0  # ReplayGain 2.0 / rsgain-Vorgabe
TOLERANZ_LU = 1.0  # erlaubte Abweichung der Box-Töne und Testmedien vom Zielwert
MIN_MESSDAUER_S = 3.0

_INTEGRIERT = re.compile(r"lavfi\.r128\.I=(-?\d+(?:\.\d+)?|-inf)")


def ffmpeg_da() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def dauer_s(pfad: Path) -> float:
    aus = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(pfad)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(aus)


def messe(pfad: str | Path) -> float:
    """Integrierte Lautheit in LUFS. Wirft ``RuntimeError``, wenn ``ffmpeg`` nichts messen kann."""
    pfad = Path(pfad)
    d = dauer_s(pfad)
    wiederholungen = max(0, math.ceil(MIN_MESSDAUER_S / d) - 1) if d > 0 else 0
    lauf = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-stream_loop", str(wiederholungen), "-i", str(pfad),
         "-af", "ebur128=metadata=1:framelog=quiet,ametadata=mode=print:key=lavfi.r128.I:file=-",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    if lauf.returncode != 0:
        raise RuntimeError(f"{pfad.name}: ffmpeg-Fehler: {lauf.stderr.strip()[-300:]}")
    treffer = _INTEGRIERT.findall(lauf.stdout + lauf.stderr)
    if not treffer or treffer[-1] == "-inf":
        raise RuntimeError(f"{pfad.name}: keine Lautheit messbar (Stille?)")
    return float(treffer[-1])


def spitze(pfad: str | Path) -> float:
    """Größter Betrag der Abtastwerte als Anteil der Vollaussteuerung (0 bis 1), über ``ffmpeg`` dekodiert."""
    roh = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(pfad), "-f", "s16le", "-ac", "1", "-"],
        check=True, capture_output=True,
    ).stdout
    import array

    a = array.array("h")
    a.frombytes(roh[: len(roh) - len(roh) % 2])
    return max((abs(x) for x in a), default=0) / 32768


#: Ordner (ab ``box/``), deren Audiodateien am Zielwert liegen müssen. Von ``medien-sprache`` nur die
#: erzeugten Serien: eigene Ordner dort bleiben lokal (``.gitignore``) und gehören nicht dazu.
MANIFEST_ORDNER = (
    "sounds",
    "medien-sprache/test-serie",
    "medien-sprache/lange-serie",
    "medien-sprache/track-test",
    "medien-sprache/ueberraschung",
)
WURZEL = Path(__file__).resolve().parents[1]
MANIFEST = WURZEL / "lautheit.json"


def manifest_dateien() -> list[Path]:
    """Alle Audiodateien der ``MANIFEST_ORDNER`` (``sounds`` enthält ``sounds/sprache``)."""
    gefunden: dict[Path, None] = {}
    for o in MANIFEST_ORDNER:
        for d in dateien(WURZEL / o):
            gefunden[d] = None
    return sorted(gefunden)


def sha256(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def schreibe_manifest(ziel: Path = MANIFEST) -> dict:
    daten = {
        "ziel_lufs": ZIEL_LUFS,
        "toleranz_lu": TOLERANZ_LU,
        "dateien": {
            d.relative_to(WURZEL).as_posix(): {"sha256": sha256(d), "lufs": round(messe(d), 2)}
            for d in manifest_dateien()
        },
    }
    ziel.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return daten


def normalisiere(ein: Path, aus: Path) -> float:
    """``ein`` auf ``ZIEL_LUFS`` bringen und als MP3 nach ``aus`` schreiben (für eigene Hörspiele am Mac).

    Die Verstärkung kommt aus der Messung; ein Limiter (Obergrenze 0,95) verhindert Übersteuern. Die MP3
    bekommt ReplayGain-Tags wie von ``rsgain`` (Rest zum Ziel und Spitze), damit MPD sie nicht um
    ``replaygain_missing_preamp`` dämpft. Gibt den Messwert der Kopie zurück.
    """
    gain = ZIEL_LUFS - messe(ein)
    with tempfile.TemporaryDirectory() as t:
        roh = Path(t) / "roh.mp3"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(ein), "-vn", "-map_metadata", "0",
             "-af", f"volume={gain:.2f}dB,alimiter=limit=0.95", "-c:a", "libmp3lame", "-q:a", "2", str(roh)],
            check=True,
        )
        neu = messe(roh)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(roh), "-c", "copy", "-map_metadata", "0", "-id3v2_version", "3",
             "-metadata", f"REPLAYGAIN_TRACK_GAIN={ZIEL_LUFS - neu:+.2f} dB",
             "-metadata", f"REPLAYGAIN_TRACK_PEAK={spitze(roh):.6f}", str(aus)],
            check=True,
        )
    return neu


def dateien(ordner: Path) -> list[Path]:
    return sorted(p for p in ordner.rglob("*") if p.suffix.lower() in (".wav", ".mp3"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dateien", nargs="*", type=Path)
    p.add_argument("--ordner", type=Path, action="append", default=[], help="alle WAV und MP3 darin messen")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON {Pfad: LUFS}")
    p.add_argument("--manifest", action="store_true", help=f"{MANIFEST.name} neu schreiben")
    p.add_argument("--normalisiere", action="store_true",
                   help="von jeder Datei eine Kopie NAME-normalisiert.mp3 bei -18 LUFS mit ReplayGain-Tags schreiben")
    a = p.parse_args(argv)
    if not ffmpeg_da():
        p.error("ffmpeg/ffprobe fehlen")
    if a.manifest:
        daten = schreibe_manifest()
        print(f"{MANIFEST}: {len(daten['dateien'])} Dateien")
        return 0
    if a.normalisiere:
        if not a.dateien:
            p.error("--normalisiere braucht Dateien")
        for d in a.dateien:
            aus = d.with_name(f"{d.stem}-normalisiert.mp3")
            wert = normalisiere(d, aus)
            print(f"{aus}  ({wert:.1f} LUFS)")
        return 0
    liste = list(a.dateien)
    for o in a.ordner:
        liste += dateien(o)
    if not liste:
        p.error("keine Dateien angegeben")
    werte = {str(d): messe(d) for d in liste}
    if a.json:
        print(json.dumps(werte, indent=2, ensure_ascii=False))
    else:
        for d, w in werte.items():
            print(f"{w:7.2f} LUFS  ({w - ZIEL_LUFS:+.2f} LU)  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
