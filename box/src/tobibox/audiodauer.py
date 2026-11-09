"""Dauer einer Audiodatei in Sekunden, nur aus den Kopfdaten (Entscheidung I, 09.11.).

Nur Standardbibliothek, kein MPD. ``dauer_s(pfad)`` liefert die Dauer oder ``None``, wenn die Box sie
nicht sicher kennt (Format nicht unterstützt, Datei kaputt oder nicht lesbar). Unterstützt: WAV, MP3, M4A/M4B
(MP4-Container) und FLAC. Bei MP3 ohne Xing-/Info-Kopf wird mit der festen Bitrate der ersten Frame gerechnet;
das stimmt bei Dateien mit fester Bitrate genau und bei variabler Bitrate ohne Kopf nur ungefähr.
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path

# MPEG-Audio: Bitraten (kbit/s) und Abtastraten
_BITRATEN = {
    (1, 1): (0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448),
    (1, 2): (0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384),
    (1, 3): (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
    (2, 1): (0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
    (2, 2): (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
    (2, 3): (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
}
_RATEN = {1: (44100, 48000, 32000), 2: (22050, 24000, 16000), 3: (11025, 12000, 8000)}


def dauer_s(pfad: str | Path) -> float | None:
    """Dauer in Sekunden oder ``None`` (unbekannt)."""
    pfad = Path(pfad)
    endung = pfad.suffix.lower()
    try:
        if endung == ".wav":
            return _wav(pfad)
        if endung == ".mp3":
            return _mp3(pfad)
        if endung in (".m4a", ".m4b"):
            return _mp4(pfad)
        if endung == ".flac":
            return _flac(pfad)
    except (OSError, EOFError, wave.Error, struct.error, ValueError, ZeroDivisionError):
        return None
    return None


def _positiv(x: float) -> float | None:
    return x if x > 0 else None


def _wav(pfad: Path) -> float | None:
    with wave.open(str(pfad), "rb") as w:
        rate = w.getframerate()
        return _positiv(w.getnframes() / rate) if rate else None


def _mp3(pfad: Path) -> float | None:
    groesse = pfad.stat().st_size
    with open(pfad, "rb") as f:
        kopf = f.read(10)
        start = 0
        if kopf[:3] == b"ID3" and len(kopf) == 10:
            start = 10 + ((kopf[6] & 0x7F) << 21 | (kopf[7] & 0x7F) << 14 | (kopf[8] & 0x7F) << 7 | (kopf[9] & 0x7F))
        f.seek(start)
        puffer = f.read(64 * 1024)
        f.seek(max(0, groesse - 128))
        id3v1 = f.read(128)[:3] == b"TAG" and groesse >= 128
    i = 0
    while i + 4 <= len(puffer):
        if puffer[i] == 0xFF and (puffer[i + 1] & 0xE0) == 0xE0:
            b1, b2, b3 = puffer[i + 1], puffer[i + 2], puffer[i + 3]
            version = {3: 1, 2: 2, 0: 3}.get((b1 >> 3) & 3)  # 1 = MPEG1, 2 = MPEG2, 3 = MPEG2.5
            schicht = {3: 1, 2: 2, 1: 3}.get((b1 >> 1) & 3)
            bi, ri = b2 >> 4, (b2 >> 2) & 3
            if version and schicht and 0 < bi < 15 and ri < 3:
                tabelle = _BITRATEN[(1 if version == 1 else 2, schicht)]
                rate = _RATEN[version][ri]
                kbit = tabelle[bi]
                samples = 384 if schicht == 1 else (1152 if (schicht == 2 or version == 1) else 576)
                mono = (b3 >> 6) == 3
                if version == 1:
                    versatz = 4 + (17 if mono else 32)
                else:
                    versatz = 4 + (9 if mono else 17)
                kopf_x = puffer[i + versatz : i + versatz + 12]
                if kopf_x[:4] in (b"Xing", b"Info") and kopf_x[7] & 1:
                    frames = struct.unpack(">I", kopf_x[8:12])[0]
                    return _positiv(frames * samples / rate)
                ende = groesse - (128 if id3v1 else 0)
                return _positiv((ende - (start + i)) * 8 / (kbit * 1000))
        i += 1
    return None


def _mp4(pfad: Path) -> float | None:
    """``moov/mvhd`` lesen (Zeitskala und Dauer)."""
    groesse = pfad.stat().st_size
    with open(pfad, "rb") as f:

        def kisten(von: int, bis: int):
            pos = von
            while pos + 8 <= bis:
                f.seek(pos)
                kopf = f.read(8)
                if len(kopf) < 8:
                    return
                laenge, typ = struct.unpack(">I4s", kopf)
                if laenge == 1:
                    laenge = struct.unpack(">Q", f.read(8))[0]
                    nutz = pos + 16
                elif laenge == 0:
                    laenge = bis - pos
                    nutz = pos + 8
                else:
                    nutz = pos + 8
                if laenge < 8:
                    return
                yield typ, nutz, pos + laenge
                pos += laenge

        for typ, nutz, ende in kisten(0, groesse):
            if typ != b"moov":
                continue
            for typ2, nutz2, _ende2 in kisten(nutz, ende):
                if typ2 != b"mvhd":
                    continue
                f.seek(nutz2)
                version = f.read(1)[0]
                f.read(3)
                if version == 1:
                    f.read(16)
                    zeitskala, dauer = struct.unpack(">IQ", f.read(12))
                else:
                    f.read(8)
                    zeitskala, dauer = struct.unpack(">II", f.read(8))
                return _positiv(dauer / zeitskala)
    return None


def _flac(pfad: Path) -> float | None:
    with open(pfad, "rb") as f:
        if f.read(4) != b"fLaC":
            return None
        kopf = f.read(4)
        if len(kopf) < 4 or (kopf[0] & 0x7F) != 0:  # erster Block muss STREAMINFO sein
            return None
        info = f.read(34)
    v = int.from_bytes(info[10:18], "big")
    rate = v >> 44
    gesamt = v & ((1 << 36) - 1)
    return _positiv(gesamt / rate) if rate and gesamt else None
