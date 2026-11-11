#!/usr/bin/env python3
"""Erzeugt die Platzhalter-Töne reproduzierbar (nur Standardbibliothek).

    python tools/make_sounds.py [--ziel box/sounds]

Gleiche Eingabe ergibt gleiche Bytes (feste Rate, keine Zufallswerte). Die Töne
sind einfache Sinusfolgen mit weicher Hüllkurve und ersetzen später die echten.

Lautheit (Entscheidung J, 09.11.): Jeder Ton liegt bei -18 LUFS, dem Zielwert von ReplayGain
für die Hörspiele. ``PEGEL_DB`` gleicht den Ton von der Grundamplitude ``AMPLITUDE`` auf diesen
Wert an. Die Zahlen stammen aus einer Messung mit ``tools/lautheit.py``
(``python tools/lautheit.py --ordner box/sounds``; gemessen mit dem Vorlauf von ``VORLAUF_S``); das Skript selbst braucht kein ``ffmpeg``.
Ändert sich ein Ton, muss seine Zahl neu bestimmt werden (der Test ``test_lautheit.py`` prüft es).
"""

from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path

RATE = 22050
VORLAUF_S = 0.15  # Stille am Anfang jedes Tons: die Tonausgabe am Mac verschluckt den Anfang (Befund 11.11.); gilt auch für ``make_sprache.py``
AMPLITUDE = 0.6  # Grundamplitude (Anteil der Vollaussteuerung), bevor ``PEGEL_DB`` greift
# Anpassung je Ton in dB auf -18 LUFS (gemessen mit tools/lautheit.py; Zielwert wie rsgain/ReplayGain 2.0)
PEGEL_DB: dict[str, float] = {
    "start": -8.3,
    "unbekannt": -8.0,
    "fehler": -7.56,
    "hinweis": -8.41,  # neu gemessen (Zweiklang und Vorlauf, 11.11.)
    "lernen_beginn": -8.17,
    "lernen_ende": -8.1,
    "pruef_ok": -6.35,
    "pruef_fehler": -8.06,
    "akku_leer": -7.91,
    "akku_warnung": -7.33,  # gemessen mit tools/lautheit.py (-18,0 LUFS)
    "lader": -6.93,  # gemessen mit tools/lautheit.py (-18,0 LUFS)
    "gute_nacht": -8.57,  # gemessen mit tools/lautheit.py (-18,0 LUFS)
}

# Name -> Folge aus (Frequenz in Hz, Dauer in s); 0 Hz ist eine Pause
TOENE: dict[str, list[tuple[float, float]]] = {
    "start": [(523.25, 0.12), (659.25, 0.12), (783.99, 0.22)],
    "unbekannt": [(392.0, 0.15), (329.63, 0.25)],
    "fehler": [(220.0, 0.18), (0.0, 0.05), (220.0, 0.18), (0.0, 0.05), (220.0, 0.18)],
    "hinweis": [(660.0, 0.18), (880.0, 0.22)],  # weicher Zweiklang, ca. 0,4 s (Befund Mac-Abnahme 11.11.)
    "lernen_beginn": [(440.0, 0.10), (554.37, 0.10), (659.25, 0.10), (880.0, 0.18)],
    "lernen_ende": [(880.0, 0.10), (659.25, 0.10), (554.37, 0.10), (440.0, 0.18)],
    "pruef_ok": [(1046.5, 0.12)],
    "pruef_fehler": [(196.0, 0.40)],
    "akku_leer": [(660.0, 0.2), (0.0, 0.1), (495.0, 0.2), (0.0, 0.1), (330.0, 0.35)],
    # Akku-Warnung (Entscheidung Z, zweite Stufe, 11.11.): sanfter als ``akku_leer``, zweimal derselbe Ton, dann ein Schritt abwärts
    "akku_warnung": [(660.0, 0.15), (0.0, 0.1), (660.0, 0.15), (0.0, 0.1), (495.0, 0.25)],
    # Strom ist da (Ein/Aus, 10.11., R4): kurz, aufwärts, freundlich; spielt mit dem leisen Pegel von ``hinweis``
    "lader": [(698.46, 0.07), (1046.5, 0.12)],
    # Gute Nacht (Entscheidung R, 10.11.): Karte aufgelegt; ruhig, abwärts, etwas länger als ``hinweis``
    "gute_nacht": [(783.99, 0.14), (659.25, 0.14), (523.25, 0.28)],
}


def erzeuge_samples(folge: list[tuple[float, float]], rate: int = RATE, pegel_db: float = 0.0) -> bytes:
    daten = bytearray(2 * int(round(rate * VORLAUF_S)))  # Vorlauf: Stille (16 Bit mono)
    amplitude = AMPLITUDE * 10 ** (pegel_db / 20)
    for frequenz, dauer in folge:
        n = int(rate * dauer)
        for i in range(n):
            if frequenz <= 0:
                wert = 0.0
            else:
                rampe = min(1.0, i / (0.01 * rate), (n - 1 - i) / (0.02 * rate))  # 10 ms ein, 20 ms aus
                wert = amplitude * rampe * math.sin(2 * math.pi * frequenz * i / rate)
            daten += struct.pack("<h", int(round(wert * 32767)))
    return bytes(daten)


def schreibe(pfad: Path, folge: list[tuple[float, float]], pegel_db: float = 0.0) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(erzeuge_samples(folge, pegel_db=pegel_db))


def main(argv: list[str] | None = None) -> int:
    standard = Path(__file__).resolve().parents[1] / "sounds"
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ziel", type=Path, default=standard, help=f"Zielordner (Vorgabe {standard})")
    a = p.parse_args(argv)
    for name, folge in TOENE.items():
        schreibe(a.ziel / f"{name}.wav", folge, PEGEL_DB[name])
        print(f"{a.ziel / (name + '.wav')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
