"""Die Test-Erzeuger: WAV-Dateien und Serienordner."""

from __future__ import annotations

import json
import wave

from fixtures.audio import erzeuge_medien, erzeuge_serie, schreibe_wav


def test_wav_ist_lesbar_und_kurz(tmp_path):
    p = schreibe_wav(tmp_path / "a" / "ton.wav", dauer_s=0.25, rate=8000)
    with wave.open(str(p)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 8000, 2000)
    assert p.stat().st_size < 10_000


def test_serie_mit_serie_json(tmp_path):
    o = erzeuge_serie(tmp_path, "rabe", ["f1.wav", "f2.wav"], serie_id="3f9a1c07b2d4", name="Rabe")
    d = json.loads((o / "serie.json").read_text())
    assert d["schema_version"] == 1 and d["folgen"] == ["f1.wav", "f2.wav"] and d["typ"] == "normal"
    assert sorted(p.name for p in o.iterdir()) == ["f1.wav", "f2.wav", "serie.json"]


def test_serie_ohne_serie_json(tmp_path):
    o = erzeuge_serie(tmp_path, "lose", ["x.wav"], mit_serie_json=False)
    assert not (o / "serie.json").exists()


def test_beispielmedien(tmp_path):
    erzeuge_medien(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["baer", "rabe", "ueberraschung"]
