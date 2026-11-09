"""``audiodauer``: Dauer aus den Kopfdaten (Entscheidung I, 09.11.), Dateien entstehen zur Laufzeit."""

from __future__ import annotations

import struct

import pytest
from fixtures import audio

from tobibox import audiodauer, library


def mp3_cbr(pfad, sekunden, xing_frames=None, id3=False):
    """MPEG-1 Layer III, 128 kbit/s, 44,1 kHz, Stereo: Frames zu 417 Bytes (ohne Füllbyte)."""
    kopf = bytes([0xFF, 0xFB, 0x90, 0x00])
    frame = kopf + bytes(413)
    inhalt = b""
    if id3:
        inhalt += b"ID3\x03\x00\x00" + bytes([0, 0, 0, 20]) + bytes(20)
    if xing_frames is not None:
        erster = bytearray(frame)
        erster[36:40] = b"Xing"
        erster[40:44] = struct.pack(">I", 1)
        erster[44:48] = struct.pack(">I", xing_frames)
        inhalt += bytes(erster)
    else:
        n = round(sekunden * 128000 / 8 / 417)
        inhalt += frame * n
    pfad.write_bytes(inhalt)


def test_wav(tmp_path):
    p = audio.schreibe_wav(tmp_path / "a.wav", 12.5, rate=100)
    assert audiodauer.dauer_s(p) == pytest.approx(12.5)


def test_mp3_feste_bitrate(tmp_path):
    p = tmp_path / "a.mp3"
    mp3_cbr(p, 100.0)
    assert audiodauer.dauer_s(p) == pytest.approx(100.0, abs=0.1)


def test_mp3_mit_id3_kopf(tmp_path):
    p = tmp_path / "a.mp3"
    mp3_cbr(p, 50.0, id3=True)
    assert audiodauer.dauer_s(p) == pytest.approx(50.0, abs=0.1)


def test_mp3_xing_kopf_zaehlt_die_frames(tmp_path):
    p = tmp_path / "a.mp3"
    mp3_cbr(p, 0, xing_frames=1000)
    assert audiodauer.dauer_s(p) == pytest.approx(1000 * 1152 / 44100)


def box(typ: bytes, inhalt: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(inhalt), typ) + inhalt


def test_m4a_mvhd(tmp_path):
    mvhd = box(b"mvhd", bytes([0]) + bytes(3) + bytes(8) + struct.pack(">II", 1000, 123600) + bytes(80))
    p = tmp_path / "a.m4a"
    p.write_bytes(box(b"ftyp", b"M4A \x00\x00\x00\x00") + box(b"mdat", bytes(50)) + box(b"moov", mvhd))
    assert audiodauer.dauer_s(p) == pytest.approx(123.6)


def test_flac_streaminfo(tmp_path):
    info = bytearray(34)
    wert = (44100 << 44) | (2 << 41) | (15 << 36) | (44100 * 90)  # 90 s
    info[10:18] = wert.to_bytes(8, "big")
    p = tmp_path / "a.flac"
    p.write_bytes(b"fLaC" + bytes([0x80, 0, 0, 34]) + bytes(info))
    assert audiodauer.dauer_s(p) == pytest.approx(90.0)


@pytest.mark.parametrize("name", ["a.ogg", "a.opus", "a.aac"])
def test_nicht_unterstuetzte_formate_sind_unbekannt(tmp_path, name):
    (tmp_path / name).write_bytes(bytes(100))
    assert audiodauer.dauer_s(tmp_path / name) is None


@pytest.mark.parametrize("name", ["a.wav", "a.mp3", "a.m4a", "a.flac"])
def test_kaputte_oder_leere_dateien_sind_unbekannt(tmp_path, name):
    (tmp_path / name).write_bytes(b"")
    assert audiodauer.dauer_s(tmp_path / name) is None
    (tmp_path / name).write_bytes(b"kein audio")
    assert audiodauer.dauer_s(tmp_path / name) is None


def test_fehlende_datei_ist_unbekannt(tmp_path):
    assert audiodauer.dauer_s(tmp_path / "gibt-es-nicht.mp3") is None


def test_bibliothek_kennt_die_dauer_von_folgen_und_tracks(tmp_path):
    ordner = audio.erzeuge_serie(tmp_path, "rabe", ["a.wav", "b.wav"], serie_id="3f9a1c07b2d4", dauer_s=2.0)
    audio.erzeuge_folge_ordner(ordner, "CD", ["01.wav", "02.wav"], dauer_s=1.0)
    audio.schreibe_serie_json(ordner, "3f9a1c07b2d4", "Rabe", ["a.wav", "CD", "b.wav"])
    audio.erzeuge_serie(tmp_path, "ueb", ["u.wav"], serie_id="c07d2e91a45b", typ="ueberraschung")
    (s,) = [x for x in library.lade_bibliothek(tmp_path, leise=True).serien if x.id == "3f9a1c07b2d4"]
    assert s.dauern["a.wav"] == (pytest.approx(2.0),)
    assert s.dauern["CD"] == (pytest.approx(1.0), pytest.approx(1.0))


def test_bibliothek_ohne_serie_json_kennt_die_dauer(tmp_path):
    audio.erzeuge_serie(tmp_path, "lose", ["a.wav"], mit_serie_json=False, dauer_s=1.5)
    audio.erzeuge_serie(tmp_path, "ueb", ["u.wav"], serie_id="c07d2e91a45b", typ="ueberraschung")
    (s,) = [x for x in library.lade_bibliothek(tmp_path, leise=True).serien if x.id == "lose"]
    assert s.dauern["a.wav"] == (pytest.approx(1.5),)


def test_bibliothek_unbekanntes_format_gibt_none(tmp_path):
    ordner = audio.erzeuge_serie(tmp_path, "rabe", ["a.wav"], serie_id="3f9a1c07b2d4")
    (ordner / "b.ogg").write_bytes(bytes(50))
    audio.schreibe_serie_json(ordner, "3f9a1c07b2d4", "Rabe", ["a.wav", "b.ogg"])
    audio.erzeuge_serie(tmp_path, "ueb", ["u.wav"], serie_id="c07d2e91a45b", typ="ueberraschung")
    (s,) = [x for x in library.lade_bibliothek(tmp_path, leise=True).serien if x.id == "3f9a1c07b2d4"]
    assert s.dauern["b.ogg"] == (None,)
