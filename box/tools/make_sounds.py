#!/usr/bin/env python3
"""Erzeugt die Platzhalter-Töne reproduzierbar (nur Standardbibliothek).

    python tools/make_sounds.py [--ziel box/sounds]

Gleiche Eingabe ergibt gleiche Bytes (feste Rate, keine Zufallswerte). Die Töne
sind einfache Sinusfolgen mit weicher Hüllkurve und ersetzen später die echten.
"""

from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path

RATE = 22050
AMPLITUDE = 0.6  # Anteil der Vollaussteuerung; die Lautstärke regelt der Pegel beim Abspielen

# Name -> Folge aus (Frequenz in Hz, Dauer in s); 0 Hz ist eine Pause
TOENE: dict[str, list[tuple[float, float]]] = {
    "start": [(523.25, 0.12), (659.25, 0.12), (783.99, 0.22)],
    "unbekannt": [(392.0, 0.15), (329.63, 0.25)],
    "fehler": [(220.0, 0.18), (0.0, 0.05), (220.0, 0.18), (0.0, 0.05), (220.0, 0.18)],
    "hinweis": [(880.0, 0.10)],
    "lernen_beginn": [(440.0, 0.10), (554.37, 0.10), (659.25, 0.10), (880.0, 0.18)],
    "lernen_ende": [(880.0, 0.10), (659.25, 0.10), (554.37, 0.10), (440.0, 0.18)],
    "akku_leer": [(660.0, 0.2), (0.0, 0.1), (495.0, 0.2), (0.0, 0.1), (330.0, 0.35)],
}


def erzeuge_samples(folge: list[tuple[float, float]], rate: int = RATE) -> bytes:
    daten = bytearray()
    for frequenz, dauer in folge:
        n = int(rate * dauer)
        for i in range(n):
            if frequenz <= 0:
                wert = 0.0
            else:
                rampe = min(1.0, i / (0.01 * rate), (n - 1 - i) / (0.02 * rate))  # 10 ms ein, 20 ms aus
                wert = AMPLITUDE * rampe * math.sin(2 * math.pi * frequenz * i / rate)
            daten += struct.pack("<h", int(round(wert * 32767)))
    return bytes(daten)


def schreibe(pfad: Path, folge: list[tuple[float, float]]) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(erzeuge_samples(folge))


def main(argv: list[str] | None = None) -> int:
    standard = Path(__file__).resolve().parents[1] / "sounds"
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ziel", type=Path, default=standard, help=f"Zielordner (Vorgabe {standard})")
    a = p.parse_args(argv)
    for name, folge in TOENE.items():
        schreibe(a.ziel / f"{name}.wav", folge)
        print(f"{a.ziel / (name + '.wav')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
