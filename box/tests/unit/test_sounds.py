"""Töne: Kommando, Pegel (``core-interface.md``, 8.1), kein Aufruf ohne Datei."""

from __future__ import annotations

import array
import asyncio
import math
import subprocess
import time
import wave
from pathlib import Path

import pytest

from tobibox.config import (
    KENNLINIE_ALSA_SOFTVOL,
    KENNLINIE_MPD_SOFTWARE,
    STANDARD_TON_KOMMANDO,
    STANDARD_TON_KOMMANDO_PI,
)
from tobibox.sounds import (
    FOLGE_PAUSE_S,
    HINWEIS_MINDEST,
    HINWEIS_PEGEL_VORGABE,
    TON_MINDEST,
    Kennlinie,
    Toene,
    baue_kommando,
    pegel,
    skaliere_wav,
)


@pytest.mark.parametrize(
    ("ton", "grenze", "lautstaerke", "hinweis_pegel", "erwartet"),
    [
        ("start", 100, 40, None, 40),  # der Ton folgt der Lautstärke der Sitzung
        ("start", 100, 20, None, 20),
        ("start", 100, None, None, 100),  # ohne Lautstärke gilt die Grenze
        ("fehler", 100, 60, 99, 60),  # hinweis_pegel betrifft nur den Hinweiston
        ("start", 30, 50, None, 30),  # nie über der wirksamen Grenze
        ("start", 100, 3, None, TON_MINDEST),  # Untergrenze: hörbar
        ("start", 100, 0, None, TON_MINDEST),
        ("start", 5, 3, None, 5),  # die Grenze gilt auch unter der Untergrenze
        ("start", 0, 40, None, 0),
        ("hinweis", 100, 40, None, 15),  # Vorgabe 15
        ("hinweis", 100, 10, None, 10),
        ("hinweis", 100, 12, None, 12),  # nie über der Lautstärke
        ("hinweis", 100, 20, 25, 20),
        ("hinweis", 100, 40, 25, 25),
        ("hinweis", 100, 0, None, HINWEIS_MINDEST),  # unter „stumm“ (Lautstärke 0): Untergrenze
        ("hinweis", 100, 40, 2, HINWEIS_MINDEST),
        ("hinweis", 5, 5, None, 5),  # B7: Kopfhörer-Grenze 5 → der Hinweiston spielt mit 5, nicht mit 10
        ("hinweis", 5, 0, None, 5),
        ("hinweis", 0, 0, None, 0),
        ("hinweis", 10, 0, None, 10),  # die Untergrenze 10 gilt, solange sie unter der Grenze liegt
        ("hinweis", 12, 40, 30, 12),
    ],
)
def test_pegel(ton, grenze, lautstaerke, hinweis_pegel, erwartet):
    assert pegel(ton, grenze, lautstaerke, hinweis_pegel) == erwartet


def test_pegel_regel_gilt_fuer_alle_werte():
    """Ein Ton ist nie über der Grenze und nie unter der Untergrenze (außer die Grenze liegt darunter);
    der Hinweiston ist nie lauter als die Lautstärke (außer durch die Untergrenze)."""
    for grenze in range(0, 101, 5):
        for laut in range(0, grenze + 1, 5):
            for ton in ("start", "fehler", "pruef_ok", "akku_leer"):
                p = pegel(ton, grenze, laut)
                assert p <= grenze
                assert p == min(grenze, max(TON_MINDEST, laut))
            h = pegel("hinweis", grenze, laut)
            assert h <= grenze  # B7: die Grenze gewinnt immer, auch für den Hinweiston
            assert h <= max(laut, HINWEIS_MINDEST)
            assert h == min(grenze, max(HINWEIS_MINDEST, min(HINWEIS_PEGEL_VORGABE, laut)))


def test_konstanten_der_pegelregel():
    assert TON_MINDEST == 10 and HINWEIS_MINDEST == 10 and HINWEIS_PEGEL_VORGABE == 15


# --- Kennlinie (Entscheidung J) -----------------------------------------------------------------------


def mpd_software(p):
    """Unabhängig nachgerechnet: MPD 0.24 ``PercentVolumeToSoftwareVolume``, gerundet auf 1/1024."""
    return 1.0 if p >= 100 else 0.0 if p <= 0 else round((math.exp(p / 25) - 1) / (math.exp(4) - 1) * 1024) / 1024


def test_kennlinie_mpd_software_stuetzstellen():
    k = Kennlinie()
    assert k.verstaerkung(0) == 0.0
    assert k.verstaerkung(100) == 1.0
    assert k.verstaerkung(20) == 23 / 1024  # Startlautstärke am Mac
    assert k.verstaerkung(40) == 76 / 1024  # Grenze am Mac
    assert k.verstaerkung(50) == 122 / 1024
    assert k.db(20) == pytest.approx(-33.0, abs=0.1)
    assert k.db(40) == pytest.approx(-22.6, abs=0.1)
    for p in range(0, 101):
        assert k.verstaerkung(p) == mpd_software(p)


def test_kennlinie_ist_steigend_und_geklemmt():
    for art in (KENNLINIE_MPD_SOFTWARE, KENNLINIE_ALSA_SOFTVOL):
        k = Kennlinie(art)
        werte = [k.verstaerkung(p) for p in range(0, 101)]
        assert werte == sorted(werte) and werte[-1] == 1.0
        assert k.verstaerkung(-5) == k.verstaerkung(0) and k.verstaerkung(500) == 1.0


def test_kennlinie_alsa_softvol_nach_volume_mapping():
    k = Kennlinie(KENNLINIE_ALSA_SOFTVOL, 51.0)  # ALSA-Vorgabe -51 dB bis 0 dB
    m = 10 ** (-51 / 60)
    assert k.verstaerkung(100) == 1.0
    assert k.verstaerkung(50) == pytest.approx((m + 0.5 * (1 - m)) ** 3, rel=1e-9)
    assert k.db(20) == pytest.approx(-30.3, abs=0.1)
    assert k.db(40) == pytest.approx(-18.9, abs=0.1)
    assert k.db(0) == pytest.approx(-51.0, abs=1e-9)  # MPD setzt min_dB, das ist praktisch still


def test_kennlinie_alsa_softvol_kleiner_bereich_ist_linear_in_db():
    k = Kennlinie(KENNLINIE_ALSA_SOFTVOL, 20.0)  # höchstens 24 dB: linear in dB (MAX_LINEAR_DB_SCALE)
    assert k.db(50) == pytest.approx(-10.0, abs=1e-9)
    assert k.db(75) == pytest.approx(-5.0, abs=1e-9)


def test_beide_kennlinien_unterscheiden_sich_bei_gleicher_lautstaerke():
    """Darum steht die Kennlinie in der Konfiguration: bei 40 % liegen Mac und Pi rund 3,7 dB auseinander."""
    mac, pi = Kennlinie(), Kennlinie(KENNLINIE_ALSA_SOFTVOL)
    assert pi.db(40) - mac.db(40) == pytest.approx(3.7, abs=0.2)


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
    f = 122 / 1024  # Verstärkung bei 50 % nach der Kennlinie von MPD (nicht 0,5)
    skaliere_wav(q, 50, tmp_path / "z.wav")
    assert lies_samples(tmp_path / "z.wav") == [round(x * f) for x in SAMPLES]
    assert max(lies_samples(tmp_path / "z.wav")) == 3904
    skaliere_wav(q, 100, tmp_path / "z.wav")
    assert lies_samples(tmp_path / "z.wav") == SAMPLES


def test_skaliere_mit_der_kennlinie_des_pi(tmp_path):
    q = schreibe_wav(tmp_path / "q.wav")
    k = Kennlinie(KENNLINIE_ALSA_SOFTVOL)
    skaliere_wav(q, 40, tmp_path / "z.wav", k)
    f = k.verstaerkung(40)
    assert lies_samples(tmp_path / "z.wav") == [round(x * f) for x in SAMPLES]
    assert f > Kennlinie().verstaerkung(40)  # am Pi ist 40 % lauter als am Mac


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
    assert t.spiele("start", 25, 25)
    assert t.spiele("hinweis", 100, 40, hinweis_pegel=20)
    await t.warte()
    assert [k[0] for k in g] == ["afplay", "afplay"]
    assert all(k[1] != str(tmp_path / "start.wav") for k in g)  # Kopie, nicht das Original
    assert t.gesehen[0] == [round(x * mpd_software(25)) for x in SAMPLES]
    assert t.gesehen[1] == [round(x * mpd_software(20)) for x in SAMPLES]
    assert lies_samples(tmp_path / "start.wav") == SAMPLES  # Original unverändert
    import os

    assert not any(os.path.exists(k[1]) for k in g)  # Temp-Dateien aufgeräumt


async def test_pegel_nie_ueber_grenze_und_0_ist_still(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    t.spiele("start", 0, 0)
    t.spiele("start", 20, 90)  # die Lautstärke liegt nie über der Grenze: geklemmt
    await t.warte()
    assert t.gesehen[0] == [0] * len(SAMPLES)
    assert max(abs(x) for x in t.gesehen[1]) <= round(32768 * mpd_software(20))


async def test_ton_folgt_der_lautstaerke_wie_das_hoerspiel(tmp_path):
    """Gleiche Lautstärke, gleiche Verstärkung wie MPD: bei 20 % und bei 40 %."""
    g: list = []
    t = mk(tmp_path, g)
    for laut in (20, 40):
        t.spiele("start", 100, laut)
    await t.warte()
    voll = max(abs(x) for x in SAMPLES)
    assert max(abs(x) for x in t.gesehen[0]) == round(voll * 23 / 1024)
    assert max(abs(x) for x in t.gesehen[1]) == round(voll * 76 / 1024)


async def test_untergrenze_haelt_den_ton_hoerbar(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    t.spiele("start", 100, 0)
    await t.warte()
    assert max(abs(x) for x in t.gesehen[0]) == round(32768 * mpd_software(TON_MINDEST))


async def test_toene_mit_kennlinie_des_pi(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    t.kennlinie = Kennlinie(KENNLINIE_ALSA_SOFTVOL)
    t.spiele("start", 100, 40)
    await t.warte()
    assert t.gesehen[0] == [round(x * t.kennlinie.verstaerkung(40)) for x in SAMPLES]


async def test_pi_kommando_ohne_platzhalter_bleibt_leise(tmp_path):
    g: list = []
    t = mk(tmp_path, g, ["aplay", "-q", "{datei}"])
    t.spiele("start", 10, 10)
    await t.warte()
    assert g[0][:2] == ["aplay", "-q"]
    assert max(abs(x) for x in t.gesehen[0]) <= round(32768 * mpd_software(10))


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


async def test_tonfolge_ist_genau_ein_prozess_mit_pausen_in_der_datei(tmp_path):
    """Eine Folge (Status-Karte) wird zu einer Datei zusammengefügt: ein Prozess, keine Lücke durch einen Neustart."""
    g: list = []
    gesehen: list = []

    async def starter(k):
        g.append(list(k))
        gesehen.append(lies_samples(k[-1]))

    laut = [1000, -1000, 2000, -2000]
    leise = [10, -10, 20, -20]
    schreibe_wav(tmp_path / "pruef_ok.wav", laut)
    schreibe_wav(tmp_path / "pruef_fehler.wav", leise)
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter)
    assert t.spiele_folge(["pruef_ok", "pruef_fehler", "pruef_ok", "pruef_fehler"], 100)
    await t.warte()
    assert len(g) == 1  # genau ein Prozess für vier Töne
    luecke = [0] * round(8000 * FOLGE_PAUSE_S)
    assert gesehen[0] == laut + luecke + leise + luecke + laut + luecke + leise  # Reihenfolge wie gegeben
    assert 0 < FOLGE_PAUSE_S <= 0.2  # die Lücke bleibt weit unter den gewünschten 0,3 s
    import os

    assert not any(os.path.exists(k[-1]) for k in g)  # Temp-Datei aufgeräumt
    assert not t._temp


async def test_toene_einer_folge_haben_je_ihren_pegel(tmp_path):
    """``hinweis`` ist leiser als die anderen Töne, auch wenn er in derselben Datei liegt."""
    gesehen: list = []

    async def starter(k):
        gesehen.append(lies_samples(k[-1]))

    schreibe_wav(tmp_path / "start.wav", [10000, -10000])
    schreibe_wav(tmp_path / "hinweis.wav", [10000, -10000])
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter)
    t.spiele_folge(["start", "hinweis"], 100, 100, 20)
    await t.warte()
    assert len(gesehen) == 1
    luecke = round(8000 * FOLGE_PAUSE_S)
    erster, zweiter = gesehen[0][:2], gesehen[0][2 + luecke:]
    assert erster == [10000, -10000]  # 100 %
    assert 0 < zweiter[0] < 10000  # Hinweis bei 20 %


async def test_zeitlimit_einer_folge_ist_das_limit_je_ton(tmp_path):
    """Das Zeitlimit gilt je Ton: eine Folge aus drei Tönen darf höchstens dreimal so lang hängen, dann wird der Prozess beendet."""
    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, ["sleep", "31"], ton_max_s=0.2)
    t0 = time.monotonic()
    t.spiele_folge(["start", "start", "start"], 50)
    await t.warte_leer()
    assert 0.55 <= time.monotonic() - t0 < 3.0
    assert not subprocess.run(["pgrep", "-f", "^sleep 31$"], capture_output=True).returncode == 0


async def test_tonfolge_mit_anderem_format_bricht_in_zwei_dateien(tmp_path):
    g: list = []

    async def starter(k):
        g.append(k[-1])

    schreibe_wav(tmp_path / "start.wav")
    with wave.open(str(tmp_path / "hinweis.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(array.array("h", SAMPLES).tobytes())
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter)
    t.spiele_folge(["start", "hinweis"], 50)
    await t.warte()
    assert len(g) == 2  # Rate verschieden: nicht in dieselbe Datei


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
        g.append(lies_samples(k[-1]))

    schreibe_wav(tmp_path / "pruef_ok.wav", [1000, -1000])
    schreibe_wav(tmp_path / "pruef_fehler.wav", [30, -30])
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter)
    assert t.spiele_folge(["pruef_leser_ok", "pruef_medien_fehler", "pruef_netz_ok", "pruef_speicher_fehler"], 100)
    await t.warte()
    assert len(g) == 1
    luecke = [0] * round(8000 * FOLGE_PAUSE_S)
    ok, fehler = [1000, -1000], [30, -30]
    assert g[0] == ok + luecke + fehler + luecke + ok + luecke + fehler  # alle vier, jeder mit dem Rückfall-Ton


# --- Eine Spur: nie zwei Töne gleichzeitig (Entscheidung L, 09.11.) ---------------------------------


async def test_toene_aus_verschiedenen_aufrufen_laufen_nacheinander(tmp_path):
    ereignisse: list[str] = []
    laufend = {"n": 0, "max": 0}

    async def starter(k):
        name = Path(k[-1]).name.split("-")[2]
        laufend["n"] += 1
        laufend["max"] = max(laufend["max"], laufend["n"])
        ereignisse.append(f"{name}:start")
        await asyncio.sleep(0.02)
        ereignisse.append(f"{name}:ende")
        laufend["n"] -= 1

    schreibe_wav(tmp_path / "start.wav")
    schreibe_wav(tmp_path / "hinweis.wav")
    schreibe_wav(tmp_path / "fehler.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter)
    assert not t.beschaeftigt
    t.spiele("start", 50)
    t.spiele_folge(["hinweis", "fehler"], 50)
    t.spiele("start", 50)
    assert t.beschaeftigt
    await t.warte_leer()
    assert not t.beschaeftigt
    assert laufend["max"] == 1
    assert ereignisse == [
        "start:start", "start:ende", "hinweis:start", "hinweis:ende", "start:start", "start:ende"  # hinweis+fehler: ein Prozess
    ]


async def test_dauer_eines_tons_ist_das_ende_des_prozesses(tmp_path):
    """Kein Schätzwert: ``warte_leer`` kehrt erst zurück, wenn das Programm (hier ``sleep``) zu Ende ist."""
    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, ["sleep", "0.4"])
    t0 = time.monotonic()
    t.spiele("start", 50)
    await asyncio.sleep(0.1)
    assert t.beschaeftigt
    await t.warte_leer()
    assert 0.38 <= time.monotonic() - t0 < 1.5


async def test_haengendes_programm_wird_nach_dem_zeitlimit_beendet(tmp_path):
    schreibe_wav(tmp_path / "start.wav")
    schreibe_wav(tmp_path / "hinweis.wav")
    t = Toene(tmp_path, ["sleep", "30"], ton_max_s=0.3)
    t0 = time.monotonic()
    t.spiele("start", 50)
    t.spiele("hinweis", 50)  # der zweite Ton wird nicht vom ersten blockiert, nur verzögert
    await t.warte_leer()
    assert 0.55 <= time.monotonic() - t0 < 3.0  # zweimal das Limit, nicht 30 s
    assert not _sleep30_laeuft()  # das Programm wurde beendet, nicht nur nicht mehr abgewartet


def _sleep30_laeuft() -> bool:
    return subprocess.run(["pgrep", "-f", "^sleep 30$"], capture_output=True).returncode == 0


async def test_haken_vor_und_nach_einmal_je_tonfolge(tmp_path):
    haken: list[str] = []

    async def vor():
        haken.append("vor")

    async def nach():
        haken.append("nach")

    async def starter(k):
        haken.append("ton")
        await asyncio.sleep(0.01)

    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter, vor=vor, nach=nach)
    t.spiele("start", 50)
    t.spiele("start", 50)
    await t.warte_leer()
    assert haken == ["vor", "ton", "ton", "nach"]
    t.spiele("start", 50)  # eine neue Folge: wieder vor und nach
    await t.warte_leer()
    assert haken[4:] == ["vor", "ton", "nach"]


async def test_fehler_im_haken_halten_die_spur_nicht_an(tmp_path):
    gespielt: list[int] = []

    async def kaputt():
        raise RuntimeError("player kaputt")

    async def starter(k):
        gespielt.append(1)

    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter, vor=kaputt, nach=kaputt)
    t.spiele("start", 50)
    await t.warte_leer()
    assert gespielt == [1] and not t.beschaeftigt


async def test_stop_bricht_ab_und_ruft_keinen_haken(tmp_path):
    """Beim Beenden darf nichts fortsetzen (``nach`` würde MPD wieder starten)."""
    haken: list[str] = []

    async def nach():
        haken.append("nach")

    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, ["sleep", "30"], nach=nach)
    t.spiele("start", 50)
    t.spiele("start", 50)
    await asyncio.sleep(0.1)
    await t.stop()
    assert haken == [] and not t.beschaeftigt
    assert not _sleep30_laeuft()


# --- B3: Die Tonspur stirbt an keiner Ausnahme -----------------------------------------------------------


async def test_unerwartete_ausnahme_beim_start_haelt_die_spur_nicht_an(tmp_path):
    """B3: ``ValueError`` statt ``OSError``: ``nach`` läuft, der nächste Ton spielt, ``warte_leer`` kehrt zurück."""
    haken: list[str] = []
    gespielt: list[str] = []

    async def vor():
        haken.append("vor")

    async def nach():
        haken.append("nach")

    async def starter(k):
        gespielt.append(Path(k[-1]).name)
        if len(gespielt) == 1:
            raise ValueError("unerwartet")

    schreibe_wav(tmp_path / "start.wav")
    schreibe_wav(tmp_path / "hinweis.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter, vor=vor, nach=nach)
    t.spiele("start")
    t.spiele("hinweis")
    await asyncio.wait_for(t.warte_leer(), 2.0)
    assert len(gespielt) == 2  # auch der zweite Ton spielt
    assert haken == ["vor", "nach"]
    assert not t.beschaeftigt and t._leer.is_set() and not t._eintraege
    assert not t._temp  # keine Temp-Dateien liegengeblieben


async def test_nach_haken_laeuft_auch_wenn_die_spur_unerwartet_abbricht(tmp_path):
    """B3: Der Haken ``nach`` liegt in ``finally``; ``_leer`` wird nur bei leerer Spur gesetzt."""
    haken: list[str] = []

    async def nach():
        haken.append("nach")

    async def starter(k):
        pass

    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter, nach=nach)

    async def kaputt(gruppe):
        raise RuntimeError("Fehler in der Spur selbst")

    t._lauf = kaputt  # type: ignore[method-assign]
    t.spiele_folge(["start", "start", "start"])
    await asyncio.wait_for(t.warte_leer(), 2.0)
    assert haken == ["nach"]  # trotz der Ausnahme
    assert not t.beschaeftigt and not t._eintraege and t._leer.is_set()


async def test_warte_leer_blockiert_den_event_loop_nie(tmp_path):
    """B3: Auch bei gesetztem ``_leer`` und wartenden Einträgen blockiert ``warte_leer`` den Loop nicht."""
    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO)
    t._eintraege.append(("start", None))  # künstlicher Zustand: beschäftigt, aber kein Arbeiter, ``_leer`` gesetzt
    assert t.beschaeftigt and t._leer.is_set()
    lief = []

    async def anderer():
        await asyncio.sleep(0.05)
        lief.append(1)
        t._eintraege.clear()

    a = asyncio.create_task(anderer())
    await asyncio.wait_for(t.warte_leer(), 2.0)  # früher: Endlosschleife ohne ``await``
    await a
    assert lief == [1]


async def test_ausnahme_der_pegel_quelle_wird_aufgefangen(tmp_path):
    gespielt: list = []

    async def starter(k):
        gespielt.append(k)

    def kaputt():
        raise RuntimeError("quelle kaputt")

    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter, pegel_quelle=kaputt)
    t.spiele("start")
    await asyncio.wait_for(t.warte_leer(), 2.0)
    assert gespielt == [] and not t.beschaeftigt


# --- B6: Der Pegel entsteht erst beim Abspielen ----------------------------------------------------------


async def test_pegel_wird_erst_beim_abspielen_berechnet(tmp_path):
    """B6: Ein wartender Ton hört auf die Lautstärke von jetzt, nicht auf die vom Einreihen."""
    gesehen: list[list[int]] = []
    tor = asyncio.Event()
    werte = {"grenze": 60, "laut": 60}

    async def starter(k):
        gesehen.append(lies_samples(k[-1]))
        if len(gesehen) == 1:
            await tor.wait()  # der erste Ton läuft; die anderen warten

    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter, pegel_quelle=lambda: (werte["grenze"], werte["laut"], None))
    t.spiele("start")
    t.spiele_folge(["start", "start"])
    await asyncio.sleep(0.05)
    assert len(gesehen) == 1
    werte.update(grenze=20, laut=20)  # Kopfhörer gesteckt, während die Töne warten
    tor.set()
    await asyncio.wait_for(t.warte_leer(), 2.0)
    assert len(gesehen) == 2  # der einzelne Ton, dann die Folge als eine Datei
    hoch = max(abs(x) for x in gesehen[0])
    assert hoch == round(max(abs(x) for x in SAMPLES) * mpd_software(60))
    assert max(abs(x) for x in gesehen[1]) == round(max(abs(x) for x in SAMPLES) * mpd_software(20))
    assert len(gesehen[1]) == 2 * len(SAMPLES) + round(8000 * FOLGE_PAUSE_S)


async def test_feste_werte_gelten_weiter_und_haben_vorrang_vor_der_quelle(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    t._pegel_quelle = lambda: (100, 100, None)
    t.spiele("start", 25, 25)
    await t.warte()
    assert t.gesehen[0] == [round(x * mpd_software(25)) for x in SAMPLES]


# --- B7: Die Grenze gewinnt immer ------------------------------------------------------------------------


async def test_hinweis_spielt_unter_der_grenze_auch_wenn_sie_unter_der_untergrenze_liegt(tmp_path):
    """Kopfhörer-Grenze 5: der Hinweiston spielt mit 5, nicht mit 10."""
    g: list = []
    t = mk(tmp_path, g)
    t.spiele("hinweis", 5, 0)
    await t.warte()
    assert t.gesehen[0] == [round(x * mpd_software(5)) for x in SAMPLES]


async def test_folge_wartet_zeigt_weitere_toene(tmp_path):
    """B8: ``folge_wartet`` sagt dem Player, dass gleich noch ein Ton kommt (die Pause bleibt)."""
    tor = asyncio.Event()

    async def starter(k):
        await tor.wait()

    schreibe_wav(tmp_path / "start.wav")
    t = Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter)
    assert not t.folge_wartet
    t.spiele("start", 50)
    await asyncio.sleep(0.02)
    assert not t.folge_wartet  # der einzige Ton läuft
    t.spiele("start", 50)
    assert t.folge_wartet
    tor.set()
    await t.warte_leer()
    assert not t.folge_wartet


def test_lader_hat_den_pegel_von_hinweis_ein_aus_10_11():
    """Der Ton ``lader`` (Ein/Aus, 10.11.) klingt wie der Hinweiston: ``min(grenze, max(10, min(hinweis_pegel, lautstaerke)))``."""
    from tobibox.sounds import pegel

    for grenze, laut, hp in [(50, 40, None), (50, 0, None), (50, 40, 30), (5, 40, None), (50, 8, 15), (30, 100, 90)]:
        assert pegel("lader", grenze, laut, hp) == pegel("hinweis", grenze, laut, hp)
    assert pegel("lader", 50, 40) == 15 and pegel("lader", 50, 0) == 10 and pegel("lader", 5, 40) == 5
