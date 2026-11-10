"""Platzhalter-Töne: reproduzierbar und im Repo vorhanden."""

from __future__ import annotations

import importlib.util
import wave
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_sounds", WURZEL / "tools" / "make_sounds.py")
make_sounds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_sounds)


def test_reproduzierbar_und_wie_eingecheckt(tmp_path):
    make_sounds.main(["--ziel", str(tmp_path)])
    for name in make_sounds.TOENE:
        neu = (tmp_path / f"{name}.wav").read_bytes()
        assert neu == (WURZEL / "sounds" / f"{name}.wav").read_bytes(), name
        with wave.open(str(tmp_path / f"{name}.wav")) as w:
            assert (w.getnchannels(), w.getsampwidth()) == (1, 2)
            assert 0.05 < w.getnframes() / w.getframerate() < 2.0


def test_alle_vertragstoene_haben_eine_datei():
    erwartet = {"start", "unbekannt", "fehler", "hinweis", "lernen_beginn", "lernen_ende", "akku_leer", "lader", "gute_nacht", "pruef_ok", "pruef_fehler"}
    assert set(make_sounds.TOENE) == erwartet
