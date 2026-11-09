#!/usr/bin/env python3
"""Erzeugt die gesprochenen Box-Töne und die gesprochenen Testmedien reproduzierbar.

    python tools/make_sprache.py [--stimme PFAD.onnx | --engine espeak] [--nur toene|medien]

Ergebnis (wird committet, nur freie Stimme, keine fremden Inhalte):

* ``box/sounds/sprache/``  WAV, mono, 16 Bit, 22050 Hz, gleiche Namen wie ``box/sounds/``
  plus die Prüfpunkt-Töne ``pruef_<punkt>_ok|fehler`` und ``pruef_leser_simulation``.
* ``box/medien-sprache/``  vier Serien als MP3 (mono, 48 kbit/s) mit ``serie.json``.

Stimme (Vorgabe): Piper mit ``de_DE-thorsten-medium`` (Thorsten-Voice, CC0). Fehlt die Modelldatei,
lädt das Skript sie von Hugging Face (``rhasspy/piper-voices``) in ``--cache``. Ersatz: ``--engine espeak``
(Programm ``espeak-ng``, Stimme ``de``). Mit Piper (Rauschen auf 0) und ``ffmpeg -bitexact`` ergibt
gleiche Eingabe gleiche Bytes. Nötig: ``pip install piper-tts`` und ``ffmpeg``.

Die Texte stehen unten als Tabellen. Das Skript läuft im Container, nicht am Mac.
"""

from __future__ import annotations

import argparse
import array
import json
import math
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import wave
from pathlib import Path

RATE = 22050
WURZEL = Path(__file__).resolve().parents[1]
STIMME = "de_DE-thorsten-medium"
STIMME_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/"
SPITZE = 0.7  # Spitzenpegel der Sprache (Anteil der Vollaussteuerung); die Box skaliert beim Abspielen herunter
ANGELEGT_AM = "2026-11-09T09:00:00Z"

# --------------------------------------------------------------------------
# Texte: Box-Töne (gleiche Namen wie box/sounds/ plus Prüfpunkte)
# --------------------------------------------------------------------------

TOENE: dict[str, str] = {
    "start": "Tobi Box ist bereit.",
    "unbekannt": "Diesen Tobie kenne ich noch nicht. Hier ist eine Überraschung.",
    "fehler": "Da ist etwas schiefgegangen.",
    "hinweis": "Hinweis.",
    "lernen_beginn": "Lernmodus an. Leg den neuen Tobie auf.",
    "lernen_ende": "Lernmodus beendet.",
    "akku_leer": "Mein Akku ist fast leer. Ich gehe gleich aus.",
    "pruef_ok": "In Ordnung.",
    "pruef_fehler": "Fehler.",
    "pruef_leser_ok": "Leser in Ordnung.",
    "pruef_leser_fehler": "Leser: Fehler.",
    "pruef_leser_simulation": "Leser: Simulation.",
    "pruef_medien_ok": "Medien in Ordnung.",
    "pruef_medien_fehler": "Medien: Fehler.",
    "pruef_netz_ok": "Netz in Ordnung.",
    "pruef_netz_fehler": "Netz: Fehler.",
    "pruef_speicher_ok": "Speicher in Ordnung.",
    "pruef_speicher_fehler": "Speicher: Fehler.",
}

# --------------------------------------------------------------------------
# Texte: Testmedien
# --------------------------------------------------------------------------

ZAHLWORT = {1: "eins", 2: "zwei", 3: "drei"}
EINER = {1: "ein", 2: "zwei", 3: "drei", 4: "vier", 5: "fünf", 6: "sechs", 7: "sieben", 8: "acht", 9: "neun"}
ZEHNER = {2: "zwanzig", 3: "dreißig", 4: "vierzig", 5: "fünfzig", 6: "sechzig", 7: "siebzig", 8: "achtzig", 9: "neunzig"}
SONDER = {5: "fünf", 10: "zehn", 15: "fünfzehn"}

LANGE_DAUER_S = 90
LANGE_TAKT_S = 5
HINTERGRUND_HZ = 220.0
HINTERGRUND_PEGEL = 0.03  # leise und gleichmäßig
TEST_STILLE_S = 4.0
TRACK_DAUER_S = 8.0
UEBERRASCHUNG_MIN_S = 4.0

# Serie: Ordner, feste ID, Name, Typ
SERIEN = {
    "test-serie": ("5e1a0c7d9b31", "Test-Serie", "normal"),
    "lange-serie": ("7b3f2a6e8c14", "Lange Serie", "normal"),
    "track-test": ("9d4c1e5a2f68", "Track-Test", "normal"),
    "ueberraschung": ("e2a8b6d0c397", "Überraschung", "ueberraschung"),
}


def zahlwort(n: int) -> str:
    """Zahlen 1 bis 99 als Wort (für die Sekundenansagen)."""
    if n in SONDER:
        return SONDER[n]
    if n < 10:
        return EINER[n] if n != 1 else "eins"
    if n < 20:
        raise ValueError(n)
    z, e = divmod(n, 10)
    return ZEHNER[z] if e == 0 else f"{EINER[e]}und{ZEHNER[z]}"


# --------------------------------------------------------------------------
# Sprachsynthese
# --------------------------------------------------------------------------


class Stimme:
    def __init__(self, engine: str, modell: Path | None) -> None:
        self.engine = engine
        self.modell = modell
        self._cache: dict[str, array.array] = {}

    def beschreibung(self) -> str:
        return f"piper {STIMME}" if self.engine == "piper" else "espeak-ng de"

    def _roh(self, text: str, ziel: Path) -> None:
        if self.engine == "piper":
            subprocess.run(
                [sys.executable, "-m", "piper", "-m", str(self.modell), "--noise-scale", "0", "--noise-w-scale", "0",
                 "-f", str(ziel)],
                input=text.encode("utf-8"), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.run(["espeak-ng", "-v", "de", "-s", "150", "-w", str(ziel), text], check=True)

    def sprich(self, text: str) -> array.array:
        """Text -> Samples (mono, 16 Bit, RATE), vorn und hinten von Stille befreit, auf SPITZE normiert."""
        if text in self._cache:
            return self._cache[text]
        with tempfile.TemporaryDirectory() as t:
            roh, norm = Path(t) / "roh.wav", Path(t) / "norm.wav"
            self._roh(text, roh)
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(roh), "-ar", str(RATE), "-ac", "1", "-sample_fmt", "s16",
                 "-bitexact", str(norm)],
                check=True,
            )
            with wave.open(str(norm), "rb") as w:
                s = array.array("h")
                s.frombytes(w.readframes(w.getnframes()))
        s = _trimme(s)
        s = _normiere(s)
        self._cache[text] = s
        return s


def _trimme(s: array.array, schwelle: int = 300) -> array.array:
    """Stille vorn und hinten weg: der Einsatz liegt (5 ms Rand) am Anfang, hinten bleiben 30 ms."""
    laut = [i for i, x in enumerate(s) if abs(x) > schwelle]
    if not laut:
        return s
    return s[max(0, laut[0] - int(RATE * 0.005)): laut[-1] + 1 + int(RATE * 0.03)]


def _normiere(s: array.array) -> array.array:
    spitze = max((abs(x) for x in s), default=0)
    if spitze == 0:
        return s
    f = SPITZE * 32767 / spitze
    return array.array("h", (int(round(x * f)) for x in s))


def stille(sekunden: float) -> array.array:
    return array.array("h", bytes(2 * int(round(RATE * sekunden))))


def schreibe_wav(pfad: Path, samples: array.array) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(samples.tobytes())


def schreibe_mp3(pfad: Path, samples: array.array) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        wav = Path(t) / "x.wav"
        schreibe_wav(wav, samples)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-map_metadata", "-1", "-fflags", "+bitexact",
             "-flags:a", "+bitexact", "-c:a", "libmp3lame", "-b:a", "48k", "-ac", "1", "-ar", str(RATE), str(pfad)],
            check=True,
        )


def auf_laenge(s: array.array, sekunden: float) -> array.array:
    n = int(round(RATE * sekunden))
    if len(s) > n:
        raise ValueError(f"Sprache ({len(s) / RATE:.1f} s) länger als {sekunden} s")
    return s + array.array("h", bytes(2 * (n - len(s))))


def lege_auf(ziel: array.array, s: array.array, sekunde: float) -> None:
    """``s`` ab ``sekunde`` in ``ziel`` einmischen."""
    start = int(round(RATE * sekunde))
    if start + len(s) > len(ziel):
        raise ValueError("Ansage ragt über das Ende hinaus")
    for i, x in enumerate(s):
        ziel[start + i] = max(-32768, min(32767, ziel[start + i] + x))


def hintergrund(sekunden: float) -> array.array:
    n = int(round(RATE * sekunden))
    a = HINTERGRUND_PEGEL * 32767
    return array.array("h", (int(round(a * math.sin(2 * math.pi * HINTERGRUND_HZ * i / RATE))) for i in range(n)))


# --------------------------------------------------------------------------
# Erzeugen
# --------------------------------------------------------------------------


def serie_json(ordner: Path, key: str, folgen: list[str]) -> None:
    sid, name, typ = SERIEN[key]
    daten = {"schema_version": 1, "id": sid, "name": name, "typ": typ, "folgen": folgen, "angelegt_am": ANGELEGT_AM}
    (ordner / "serie.json").write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def erzeuge_toene(stimme: Stimme, ziel: Path) -> list[Path]:
    aus = []
    for name, text in TOENE.items():
        p = ziel / f"{name}.wav"
        schreibe_wav(p, stimme.sprich(text))
        aus.append(p)
    return aus


def erzeuge_medien(stimme: Stimme, ziel: Path) -> list[Path]:
    aus: list[Path] = []

    def mp3(pfad: Path, samples: array.array) -> None:
        schreibe_mp3(pfad, samples)
        aus.append(pfad)

    # Test-Serie: Ansage, dann Stille (Ende hörbar), höchstens 10 s
    o = ziel / "test-serie"
    namen = []
    for n in (1, 2, 3):
        s = stimme.sprich(f"Test-Serie, Folge {ZAHLWORT[n]}.")
        gesamt = len(s) / RATE + TEST_STILLE_S
        assert gesamt <= 10.0, gesamt
        namen.append(f"folge-{n:02d}.mp3")
        mp3(o / namen[-1], s + stille(TEST_STILLE_S))
    serie_json(o, "test-serie", namen)

    # Lange Serie: Ansage bei 0 s, dann alle 5 s "Folge N, Sekunde X" auf die volle Sekunde, leiser Grundton
    o = ziel / "lange-serie"
    namen = []
    for n in (1, 2):
        folge = ZAHLWORT[n]
        s = hintergrund(LANGE_DAUER_S)
        lege_auf(s, stimme.sprich(f"Lange Serie, Folge {folge}."), 0.0)
        for sek in range(LANGE_TAKT_S, LANGE_DAUER_S, LANGE_TAKT_S):
            lege_auf(s, stimme.sprich(f"Folge {folge}, Sekunde {zahlwort(sek)}"), float(sek))
        namen.append(f"folge-{n:02d}.mp3")
        mp3(o / namen[-1], s)
    serie_json(o, "lange-serie", namen)

    # Track-Test: eine Folge als Ordner aus drei Tracks
    o = ziel / "track-test"
    for n in (1, 2, 3):
        s = auf_laenge(stimme.sprich(f"Track {ZAHLWORT[n]} von drei."), TRACK_DAUER_S)
        mp3(o / "folge-01" / f"track-{n:02d}.mp3", s)
    serie_json(o, "track-test", ["folge-01"])

    # Überraschungs-Serie
    o = ziel / "ueberraschung"
    s = stimme.sprich("Überraschung! Das ist die Überraschungs-Serie.")
    mp3(o / "ton-01.mp3", s + stille(max(0.0, UEBERRASCHUNG_MIN_S - len(s) / RATE)))
    serie_json(o, "ueberraschung", ["ton-01.mp3"])
    return aus


# --------------------------------------------------------------------------
# Stimme beschaffen
# --------------------------------------------------------------------------


def hole_modell(cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    for endung in (".onnx", ".onnx.json"):
        d = cache / f"{STIMME}{endung}"
        if not d.is_file():
            print(f"lade {d.name} ...", file=sys.stderr)
            urllib.request.urlretrieve(STIMME_URL + d.name, d)
    return cache / f"{STIMME}.onnx"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--engine", choices=("piper", "espeak"), default="piper")
    p.add_argument("--stimme", type=Path, help="Piper-Modelldatei (.onnx); ohne Angabe Download nach --cache")
    p.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "tobibox-piper")
    p.add_argument("--nur", choices=("toene", "medien"))
    p.add_argument("--toene-ziel", type=Path, default=WURZEL / "sounds" / "sprache")
    p.add_argument("--medien-ziel", type=Path, default=WURZEL / "medien-sprache")
    a = p.parse_args(argv)
    if shutil.which("ffmpeg") is None:
        p.error("ffmpeg fehlt")
    if a.engine == "espeak" and shutil.which("espeak-ng") is None:
        p.error("espeak-ng fehlt (apt-get install -y espeak-ng)")
    modell = None
    if a.engine == "piper":
        modell = a.stimme or hole_modell(a.cache)
    stimme = Stimme(a.engine, modell)
    print(f"Stimme: {stimme.beschreibung()}")
    dateien: list[Path] = []
    if a.nur in (None, "toene"):
        dateien += erzeuge_toene(stimme, a.toene_ziel)
    if a.nur in (None, "medien"):
        dateien += erzeuge_medien(stimme, a.medien_ziel)
    for d in dateien:
        print(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
