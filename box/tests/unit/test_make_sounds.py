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
    erwartet = {"start", "unbekannt", "fehler", "hinweis", "lernen_beginn", "lernen_ende", "akku_leer", "akku_warnung", "lader", "gute_nacht", "pruef_ok", "pruef_fehler"}
    assert set(make_sounds.TOENE) == erwartet


def test_sprachfassung_von_hinweis_ist_der_piepser_ohne_sprachtext():
    """Entscheidung T, 10.11.: ``hinweis`` ist auch in der Sprachfassung nur der leise Klang."""
    import importlib.util

    wurzel = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("make_sprache_t", wurzel / "tools" / "make_sprache.py")
    ms = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ms)
    assert "hinweis" not in ms.TOENE
    assert "hinweis" in ms.TOENE_OHNE_SPRACHE
    assert (wurzel / "sounds" / "sprache" / "hinweis.wav").read_bytes() == (wurzel / "sounds" / "hinweis.wav").read_bytes()


def test_hinweis_ist_ein_weicher_zweiklang_von_etwa_0_4_s(tmp_path):
    """Mac-Abnahme 11.11.: 0,1 s waren nicht hörbar; jetzt 660 Hz dann 880 Hz, ca. 0,4 s, ohne Sprache."""
    folge = make_sounds.TOENE["hinweis"]
    assert [f for f, _ in folge] == [660.0, 880.0]
    assert 0.38 <= sum(d for _, d in folge) <= 0.42
    make_sounds.main(["--ziel", str(tmp_path)])
    with wave.open(str(tmp_path / "hinweis.wav")) as w:
        assert 0.38 + make_sounds.VORLAUF_S <= w.getnframes() / w.getframerate() <= 0.42 + make_sounds.VORLAUF_S  # Klang plus Vorlauf


def test_jeder_ton_beginnt_mit_0_15_s_stille(tmp_path):
    """Befund Mac 11.11.: Die Tonausgabe verschluckt den Anfang; deshalb 0,15 s Stille vorn."""
    assert make_sounds.VORLAUF_S == 0.15
    make_sounds.main(["--ziel", str(tmp_path)])
    for datei in tmp_path.glob("*.wav"):
        with wave.open(str(datei)) as w:
            roh = w.readframes(w.getnframes())
            vorlauf = int(w.getframerate() * 0.15)
        assert roh[: 2 * vorlauf] == bytes(2 * vorlauf), datei.name
        assert any(roh[2 * vorlauf : 2 * vorlauf + 400]), datei.name  # danach setzt der Ton ein
