"""Erzeugt kurze WAV-Töne und Serienordner mit ``serie.json`` im Test-Verzeichnis.

Es wird kein Audio eingecheckt: alles entsteht zur Laufzeit aus der
Standardbibliothek.
"""

from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path

DEFAULT_DAUER_S = 0.2
RATE = 8000


def schreibe_wav(pfad: str | Path, dauer_s: float = DEFAULT_DAUER_S, frequenz: float = 440.0, rate: int = RATE) -> Path:
    """Mono, 16 Bit, Sinuston bei halber Aussteuerung."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    n = int(rate * dauer_s)
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(
            b"".join(struct.pack("<h", int(16000 * math.sin(2 * math.pi * frequenz * i / rate))) for i in range(n))
        )
    return pfad


def schreibe_serie_json(
    ordner: Path,
    serie_id: str,
    name: str,
    folgen: list[str],
    typ: str = "normal",
    angelegt_am: str = "2026-11-05T09:00:00Z",
    **extra: object,
) -> Path:
    pfad = ordner / "serie.json"
    inhalt = {
        "schema_version": 1,
        "id": serie_id,
        "name": name,
        "typ": typ,
        "folgen": folgen,
        "angelegt_am": angelegt_am,
        **extra,
    }
    pfad.write_text(json.dumps(inhalt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return pfad


def erzeuge_serie(
    medien: str | Path,
    ordner: str,
    folgen: list[str],
    *,
    serie_id: str | None = None,
    name: str | None = None,
    typ: str = "normal",
    mit_serie_json: bool = True,
    dauer_s: float = DEFAULT_DAUER_S,
    **extra: object,
) -> Path:
    """Serienordner mit je einer WAV-Datei je Folge. Gibt den Ordner zurück.

    ``folgen`` gibt die Dateinamen (auch ohne ``.wav``-Endung, der Inhalt ist
    immer WAV) und bei ``mit_serie_json`` die Reihenfolge in ``serie.json`` an.
    """
    wurzel = Path(medien) / ordner
    wurzel.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(folgen):
        schreibe_wav(wurzel / f, dauer_s, 330.0 + 40 * i)
    if mit_serie_json:
        schreibe_serie_json(wurzel, serie_id or ordner, name or ordner, list(folgen), typ, **extra)
    return wurzel


def erzeuge_folge_ordner(
    serie_ordner: str | Path,
    name: str,
    tracks: list[str],
    *,
    dauer_s: float = DEFAULT_DAUER_S,
    dotfiles: bool = False,
    fremde: list[str] | None = None,
) -> Path:
    """Folge aus mehreren Tracks: Unterordner ``name`` im Serien-Ordner (Entscheidung F, 05.11.).

    ``tracks`` sind die Dateinamen (alle als WAV erzeugt, jeder Track mit eigener Tonhöhe).
    ``dotfiles`` legt zusätzlich ``._01.wav`` und ``.versteckt.wav`` an (müssen ignoriert werden),
    ``fremde`` Dateien ohne Audio-Endung (z. B. ``cover.jpg``, ebenfalls ignoriert).
    """
    wurzel = Path(serie_ordner) / name
    wurzel.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(tracks):
        schreibe_wav(wurzel / f, dauer_s, 500.0 + 60 * i)
    if dotfiles:
        schreibe_wav(wurzel / "._01.wav", dauer_s, 900.0)
        schreibe_wav(wurzel / ".versteckt.wav", dauer_s, 950.0)
    for f in fremde or []:
        (wurzel / f).write_bytes(b"kein audio")
    return wurzel


def erzeuge_medien(medien: str | Path) -> Path:
    """Kleine Bibliothek: zwei normale Serien und eine Überraschungs-Serie."""
    medien = Path(medien)
    erzeuge_serie(medien, "rabe", ["folge-01.wav", "folge-02.wav", "folge-03.wav"],
                  serie_id="3f9a1c07b2d4", name="Der kleine Rabe")
    erzeuge_serie(medien, "baer", ["a.wav", "b.wav"], serie_id="8c21d5e9a0b7", name="Bär")
    erzeuge_serie(medien, "ueberraschung", ["ton-01.wav", "ton-02.wav"], serie_id="c07d2e91a45b",
                  name="Überraschung", typ="ueberraschung")
    return medien
