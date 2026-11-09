"""Töne: Kommando, Pegel (``core-interface.md``, 8.1), kein Aufruf ohne Datei."""

from __future__ import annotations

import array
import asyncio
import wave
from pathlib import Path

import pytest

from tobibox.config import STANDARD_TON_KOMMANDO, STANDARD_TON_KOMMANDO_PI
from tobibox.sounds import Toene, baue_kommando, pegel, skaliere_wav


@pytest.mark.parametrize(
    ("ton", "grenze", "ton_pegel", "hinweis_pegel", "erwartet"),
    [
        ("start", 100, None, None, 40),  # Vorgabe 40
        ("start", 30, None, None, 30),  # nie über der Grenze
        ("fehler", 100, 60, None, 60),
        ("start", 0, 40, None, 0),
        ("hinweis", 100, None, None, 15),  # Vorgabe 15
        ("hinweis", 10, None, None, 10),
        ("hinweis", 3, None, None, 5),  # Untergrenze 5
        ("hinweis", 100, None, 2, 5),
        ("hinweis", 100, None, 25, 25),
    ],
)
def test_pegel(ton, grenze, ton_pegel, hinweis_pegel, erwartet):
    assert pegel(ton, grenze, ton_pegel, hinweis_pegel) == erwartet


def test_kommando_mac_und_pi(tmp_path):
    d = tmp_path / "start.wav"
    assert baue_kommando(STANDARD_TON_KOMMANDO, d, 40) == ["afplay", str(d)]
    assert baue_kommando(STANDARD_TON_KOMMANDO_PI, d, 40) == ["aplay", "-q", str(d)]
    assert baue_kommando(["x", "--pegel={pegel}", "{datei}"], d, 7)[1] == "--pegel=7"
    assert baue_kommando(["x", "-v", "{lautstaerke}", "{datei}"], d, 40)[2] == "0.40"


SAMPLES = [0, 1000, -1000, 32767, -32768, 20000]


def schreibe_wav(pfad, samples=SAMPLES, breite=2):
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(breite)
        w.setframerate(8000)
        if breite == 2:
            w.writeframes(array.array("h", samples).tobytes())
        else:
            w.writeframes(bytes(len(samples) * breite))
    return pfad


def lies_samples(pfad):
    with wave.open(str(pfad), "rb") as r:
        a = array.array("h")
        a.frombytes(r.readframes(r.getnframes()))
        return list(a)


def test_skaliere_pegel_0_ist_still(tmp_path):
    q = schreibe_wav(tmp_path / "q.wav")
    skaliere_wav(q, 0, tmp_path / "z.wav")
    assert lies_samples(tmp_path / "z.wav") == [0] * len(SAMPLES)


def test_skaliere_verkleinert_proportional(tmp_path):
    q = schreibe_wav(tmp_path / "q.wav")
    skaliere_wav(q, 50, tmp_path / "z.wav")
    assert lies_samples(tmp_path / "z.wav") == [0, 500, -500, 16384, -16384, 10000]
    skaliere_wav(q, 100, tmp_path / "z.wav")
    assert lies_samples(tmp_path / "z.wav") == SAMPLES


def test_skaliere_lehnt_andere_formate_ab(tmp_path):
    q = schreibe_wav(tmp_path / "q.wav", breite=3)
    with pytest.raises(ValueError):
        skaliere_wav(q, 50, tmp_path / "z.wav")


def mk(tmp_path, gespielt, kommando=STANDARD_TON_KOMMANDO):
    gesehen = []

    async def starter(k):
        gespielt.append(list(k))
        gesehen.append(lies_samples(k[-1]))  # die Datei existiert, solange der Ton läuft

    schreibe_wav(tmp_path / "start.wav")
    schreibe_wav(tmp_path / "hinweis.wav")
    t = Toene(tmp_path, kommando, starter=starter)
    t.gesehen = gesehen
    return t


async def test_spielt_skalierte_kopie_unter_grenze(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    assert t.spiele("start", 25)
    assert t.spiele("hinweis", 100, hinweis_pegel=20)
    await t.warte()
    assert [k[0] for k in g] == ["afplay", "afplay"]
    assert all(k[1] != str(tmp_path / "start.wav") for k in g)  # Kopie, nicht das Original
    assert t.gesehen[0] == [round(x * 0.25) for x in SAMPLES]
    assert t.gesehen[1] == [round(x * 0.20) for x in SAMPLES]
    assert lies_samples(tmp_path / "start.wav") == SAMPLES  # Original unverändert
    import os

    assert not any(os.path.exists(k[1]) for k in g)  # Temp-Dateien aufgeräumt


async def test_pegel_nie_ueber_grenze_und_0_ist_still(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    t.spiele("start", 0)
    t.spiele("start", 10, ton_pegel=90)
    await t.warte()
    assert t.gesehen[0] == [0] * len(SAMPLES)
    assert max(abs(x) for x in t.gesehen[1]) <= round(32768 * 0.10)


async def test_pi_kommando_ohne_platzhalter_bleibt_leise(tmp_path):
    g: list = []
    t = mk(tmp_path, g, ["aplay", "-q", "{datei}"])
    t.spiele("start", 10)
    await t.warte()
    assert g[0][:2] == ["aplay", "-q"]
    assert max(abs(x) for x in t.gesehen[0]) <= round(32768 * 0.10)


async def test_nicht_skalierbare_datei_wird_nicht_gespielt(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    (tmp_path / "start.wav").write_bytes(b"RIFF")
    assert not t.spiele("start", 50)
    await t.warte()
    assert g == []


async def test_kein_aufruf_ohne_datei(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    assert not t.spiele("fehler", 50)  # fehler.wav fehlt
    assert not t.spiele("pruef_ok", 50)
    await t.warte()
    assert g == []


async def test_fehlendes_programm_wirft_nicht(tmp_path):
    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, ["gibt-es-nicht-xyz", "{datei}"])
    assert t.spiele("start", 50)
    await t.warte()  # kein Fehler


async def test_spiele_folge_spielt_nacheinander_in_der_gegebenen_reihenfolge(tmp_path):
    g: list = []
    laufend = {"n": 0, "max": 0}

    async def starter(k):
        laufend["n"] += 1
        laufend["max"] = max(laufend["max"], laufend["n"])
        g.append(k[-1])
        await asyncio.sleep(0.01)
        laufend["n"] -= 1

    schreibe_wav(tmp_path / "pruef_ok.wav")
    schreibe_wav(tmp_path / "pruef_fehler.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter)
    assert t.spiele_folge(["pruef_ok", "pruef_fehler", "pruef_ok", "pruef_fehler"], 50)
    await t.warte()
    assert len(g) == 4 and laufend["max"] == 1  # nie zwei Töne gleichzeitig
    assert [Path(x).name.split("-")[2] for x in g] == ["pruef_ok", "pruef_fehler", "pruef_ok", "pruef_fehler"]


async def test_spiele_folge_leer_und_mit_fehlender_datei(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    assert not t.spiele_folge([], 50)
    assert t.spiele_folge(["gibt_es_nicht", "start"], 50)  # die fehlende Datei stoppt die Folge nicht
    await t.warte()
    assert len(g) == 1


# --- Rückfall der Prüfpunkt-Töne (Sprach-Töne, 09.11.) -------------------------------------------------


@pytest.mark.parametrize(
    ("ton", "allgemein"),
    [
        ("pruef_leser_ok", "pruef_ok"),
        ("pruef_leser_simulation", "pruef_ok"),
        ("pruef_medien_ok", "pruef_ok"),
        ("pruef_netz_fehler", "pruef_fehler"),
        ("pruef_speicher_fehler", "pruef_fehler"),
    ],
)
def test_pruefpunkt_ton_ohne_datei_faellt_auf_den_allgemeinen_ton_zurueck(tmp_path, ton, allgemein):
    schreibe_wav(tmp_path / "pruef_ok.wav")
    schreibe_wav(tmp_path / "pruef_fehler.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO)
    assert t.datei(ton) == tmp_path / f"{allgemein}.wav"
    k = t.kommando_fuer(ton, 50)
    assert k is not None  # die Datei des allgemeinen Tons wurde gefunden und skaliert


def test_pruefpunkt_ton_mit_eigener_datei_wird_bevorzugt(tmp_path):
    for n in ("pruef_ok", "pruef_netz_ok"):
        schreibe_wav(tmp_path / f"{n}.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO)
    assert t.datei("pruef_netz_ok") == tmp_path / "pruef_netz_ok.wav"
    assert t.datei("pruef_medien_ok") == tmp_path / "pruef_ok.wav"


def test_rueckfall_nur_fuer_pruefpunkt_toene(tmp_path):
    schreibe_wav(tmp_path / "pruef_ok.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO)
    assert t.datei("fehler") == tmp_path / "fehler.wav"
    assert t.kommando_fuer("fehler", 50) is None
    assert t.kommando_fuer("pruef_unsinn", 50) is None
    assert t.kommando_fuer("pruef_leser_ok", 50) is not None


async def test_spiele_folge_mit_rueckfall_spielt_jeden_punkt(tmp_path):
    g: list = []

    async def starter(k):
        g.append(Path(k[-1]).name.split("-")[2])

    schreibe_wav(tmp_path / "pruef_ok.wav")
    schreibe_wav(tmp_path / "pruef_fehler.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter)
    assert t.spiele_folge(["pruef_leser_ok", "pruef_medien_fehler", "pruef_netz_ok", "pruef_speicher_fehler"], 50)
    await t.warte()
    assert g == ["pruef_leser_ok", "pruef_medien_fehler", "pruef_netz_ok", "pruef_speicher_fehler"]  # alle vier gespielt
