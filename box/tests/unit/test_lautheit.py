"""Lautheit der Box-Töne und Testmedien (Entscheidung J, 09.11.): alle bei -18 LUFS, ±1 LU.

Gemessen wird mit ``tools/lautheit.py`` über ``ffmpeg``. Fehlt ``ffmpeg`` (z. B. im CI), prüft der Test
stattdessen die beim Erzeugen festgehaltenen Werte in ``box/lautheit.json`` samt Prüfsumme der Datei.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import struct
import wave
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("lautheit", WURZEL / "tools" / "lautheit.py")
lautheit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lautheit)

ohne_ffmpeg = pytest.mark.skipif(not lautheit.ffmpeg_da(), reason="ffmpeg/ffprobe fehlen")
DATEIEN = lautheit.manifest_dateien()
MANIFEST = json.loads(lautheit.MANIFEST.read_text(encoding="utf-8"))
REPO = WURZEL.parent


def rel(d: Path) -> str:
    return d.relative_to(WURZEL).as_posix()


def test_zielwert_ist_der_von_rsgain_und_steht_im_design():
    assert lautheit.ZIEL_LUFS == -18.0 and lautheit.TOLERANZ_LU == 1.0
    design = (REPO / "docs" / "designs" / "box-software.md").read_text(encoding="utf-8")
    assert re.search(r"Ziel\s+−18 LUFS", design), "D6 nennt den Zielwert"
    assert "−18 LUFS" in design.split("Entscheidung J — Die Töne folgen")[1]


def test_alle_erzeugten_ordner_sind_im_manifest():
    namen = {rel(d) for d in DATEIEN}
    assert len([n for n in namen if n.startswith("sounds/sprache/")]) == 21
    assert len([n for n in namen if n.startswith("sounds/") and "/sprache/" not in n]) == 12
    assert len([n for n in namen if n.startswith("medien-sprache/") and n.endswith(".mp3")]) == 9


# --- ohne ffmpeg: festgehaltene Werte ------------------------------------------------------------------


def test_manifest_gehoert_zu_den_dateien():
    assert MANIFEST["ziel_lufs"] == lautheit.ZIEL_LUFS
    assert set(MANIFEST["dateien"]) == {rel(d) for d in DATEIEN}, "tools/lautheit.py --manifest ausführen"
    for d in DATEIEN:
        eintrag = MANIFEST["dateien"][rel(d)]
        assert eintrag["sha256"] == lautheit.sha256(d), f"{rel(d)} wurde geändert: tools/lautheit.py --manifest"


@pytest.mark.parametrize("datei", DATEIEN, ids=rel)
def test_festgehaltener_wert_liegt_am_zielwert(datei):
    lufs = MANIFEST["dateien"][rel(datei)]["lufs"]
    assert abs(lufs - lautheit.ZIEL_LUFS) <= lautheit.TOLERANZ_LU, f"{rel(datei)}: {lufs} LUFS"


MP3 = [d for d in DATEIEN if d.suffix == ".mp3"]


def id3_tag(datei: Path, name: str) -> str:
    """Wert eines TXXX-Rahmens (ID3v2.3) lesen, ohne ``ffmpeg``."""
    roh = datei.read_bytes()
    assert roh[:3] == b"ID3", f"{datei.name}: kein ID3-Kopf"
    groesse = ((roh[6] & 0x7F) << 21) | ((roh[7] & 0x7F) << 14) | ((roh[8] & 0x7F) << 7) | (roh[9] & 0x7F)
    pos, ende = 10, 10 + groesse
    while pos + 10 <= ende and roh[pos] != 0:
        kennung = roh[pos:pos + 4]
        (laenge,) = struct.unpack(">I", roh[pos + 4:pos + 8])
        inhalt = roh[pos + 10:pos + 10 + laenge]
        if kennung == b"TXXX":
            kodierung = inhalt[0]
            text = inhalt[1:].decode("latin-1" if kodierung == 0 else "utf-16")
            schluessel, _, wert = text.partition("\x00")
            if schluessel.upper() == name:
                return wert.rstrip("\x00")
        pos += 10 + laenge
    raise AssertionError(f"{datei.name}: Tag {name} fehlt")


@pytest.mark.parametrize("datei", MP3, ids=rel)
def test_testmedien_tragen_replaygain_tags(datei):
    """Ohne Tags dämpft MPD um ``replaygain_missing_preamp`` (-6 dB): die Tags gleichen den Rest zum Ziel aus."""
    gain = float(id3_tag(datei, "REPLAYGAIN_TRACK_GAIN").removesuffix(" dB"))
    peak = float(id3_tag(datei, "REPLAYGAIN_TRACK_PEAK"))
    assert gain == pytest.approx(lautheit.ZIEL_LUFS - MANIFEST["dateien"][rel(datei)]["lufs"], abs=0.06)
    assert abs(gain) <= lautheit.TOLERANZ_LU
    assert 0.1 < peak <= 1.0


def test_mpd_wendet_replaygain_an_und_dafuer_sind_die_tags_noetig():
    conf = (WURZEL / "config" / "mpd.mac.example.conf").read_text(encoding="utf-8")
    assert re.search(r'^replaygain\s+"track"', conf, re.M)
    assert re.search(r'^replaygain_missing_preamp\s+"-6"', conf, re.M)


# --- mit ffmpeg: echte Messung -------------------------------------------------------------------------


@ohne_ffmpeg
@pytest.mark.parametrize("datei", DATEIEN, ids=rel)
def test_gemessene_lautheit_liegt_innerhalb_1_lu_am_zielwert(datei):
    gemessen = lautheit.messe(datei)
    assert abs(gemessen - lautheit.ZIEL_LUFS) <= lautheit.TOLERANZ_LU, f"{rel(datei)}: {gemessen:.2f} LUFS"
    assert gemessen == pytest.approx(MANIFEST["dateien"][rel(datei)]["lufs"], abs=0.06)


@ohne_ffmpeg
def test_toene_und_testmedien_liegen_untereinander_eng_beieinander():
    werte = [lautheit.messe(d) for d in DATEIEN]
    assert max(werte) - min(werte) <= 2 * lautheit.TOLERANZ_LU


def schreibe_sinus(pfad: Path, amplitude: float, sekunden: float, rate: int = 22050, hz: float = 997.0) -> Path:
    n = int(rate * sekunden)
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(
            struct.pack("<h", round(amplitude * 32767 * math.sin(2 * math.pi * hz * i / rate))) for i in range(n)
        ))
    return pfad


@ohne_ffmpeg
@pytest.mark.parametrize("sekunden", [0.15, 1.0, 5.0])
def test_messhelfer_am_sinus_auch_bei_kurzen_dateien(tmp_path, sekunden):
    """Ein Sinus mit Spitze 0,1 hat -23,01 dBFS Effektivwert; bei 997 Hz gilt LUFS = dBFS (mono)."""
    d = schreibe_sinus(tmp_path / "s.wav", 0.1, sekunden)
    assert lautheit.messe(d) == pytest.approx(20 * math.log10(0.1 / math.sqrt(2)), abs=0.15)


@ohne_ffmpeg
def test_messhelfer_meldet_stille(tmp_path):
    d = schreibe_sinus(tmp_path / "still.wav", 0.0, 1.0)
    with pytest.raises(RuntimeError):
        lautheit.messe(d)
