"""Gesprochene Töne und Testmedien (Sprach-Töne für Tests, 09.11.)."""

from __future__ import annotations

import array
import importlib.util
import shutil
import wave
from pathlib import Path

import pytest
from conftest import ZUORDNUNGEN, SitzungsHarnisch, mk_konfig, zeiger

from tobibox import audiodauer, library, selftest, session
from tobibox import events as ev
from tobibox.sounds import TON_MAX_S, Toene, skaliere_wav

WURZEL = Path(__file__).resolve().parents[2]
MELODIE = WURZEL / "sounds"
SPRACHE = WURZEL / "sounds" / "sprache"
MEDIEN = WURZEL / "medien-sprache"
PUNKTE = ("leser", "medien", "netz", "speicher")
PRUEF_NAMEN = {f"pruef_{p}_{z}" for p in PUNKTE for z in ("ok", "fehler")} | {"pruef_leser_simulation"}

# Die versioniert erzeugten Serien: dieselbe Quelle wie tools/make_sprache.py (und .gitignore).
# Eigene Ordner in box/medien-sprache/ (lokal, nicht versioniert) gehören nicht dazu.
_spec = importlib.util.spec_from_file_location("make_sprache", WURZEL / "tools" / "make_sprache.py")
make_sprache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_sprache)
VERSIONIERTE_SERIEN = tuple(make_sprache.SERIEN)


def namen(ordner: Path) -> set[str]:
    return {p.stem for p in ordner.glob("*.wav")}


def versionierte_dateien(pattern: str = "*") -> list[Path]:
    """Dateien der versionierten Serien in box/medien-sprache/ (ohne lokale Zusatzordner)."""
    return [p for s in VERSIONIERTE_SERIEN for p in (MEDIEN / s).rglob(pattern) if p.is_file()]


def test_sprach_ordner_hat_alle_namen_des_melodie_ordners_und_die_pruefpunkte():
    assert namen(MELODIE) <= namen(SPRACHE)
    assert PRUEF_NAMEN <= namen(SPRACHE)
    assert namen(SPRACHE) == namen(MELODIE) | PRUEF_NAMEN


RAND_SCHWELLE_DBFS = -50.0
VORLAUF_S = 0.15  # Stille am Anfang jedes Tons (Befund Mac 11.11.: die Tonausgabe verschluckt den Anfang)
RAND_STILLE_MAX_S = 0.1  # Befund Mac 09.11.: zwischen zwei Ansagen höchstens etwa 0,3 s Stille, davon die Ränder


def rand_stille_s(datei: Path) -> tuple[float, float]:
    """Stille am Anfang und am Ende (Sekunden) unter ``RAND_SCHWELLE_DBFS``."""
    with wave.open(str(datei)) as w:
        s = array.array("h")
        s.frombytes(w.readframes(w.getnframes()))
        rate = w.getframerate()
    schwelle = 32768 * 10 ** (RAND_SCHWELLE_DBFS / 20)
    laut = [i for i, x in enumerate(s) if abs(x) > schwelle]
    assert laut, f"{datei.name}: ganz still"
    return laut[0] / rate, (len(s) - 1 - laut[-1]) / rate


@pytest.mark.parametrize("ordner", [MELODIE, SPRACHE], ids=["melodie", "sprache"])
def test_rand_stille_aller_toene_vorlauf_plus_hoechstens_0_1_s(ordner):
    dateien = sorted(ordner.glob("*.wav"))
    assert dateien
    for d in dateien:
        vorn, hinten = rand_stille_s(d)
        assert VORLAUF_S - 0.01 <= vorn <= VORLAUF_S + RAND_STILLE_MAX_S, (d.name, vorn)  # 0,15 s Vorlauf, dahinter der Einsatz
        assert hinten <= RAND_STILLE_MAX_S, (d.name, hinten)


def test_sprach_toene_haben_das_format_der_melodie_toene(tmp_path):
    with wave.open(str(MELODIE / "start.wav")) as m:
        erwartet = (m.getnchannels(), m.getsampwidth(), m.getframerate())
    for datei in SPRACHE.glob("*.wav"):
        with wave.open(str(datei)) as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == erwartet, datei.name
            untergrenze = 0.35 if datei.stem == "hinweis" else 0.2  # hinweis ist nur ein weicher Zweiklang von ca. 0,4 s (Entscheidung T, 10.11.; Mac-Abnahme 11.11.)
            assert untergrenze < w.getnframes() / w.getframerate() < TON_MAX_S, datei.name
        skaliere_wav(datei, 40, tmp_path / datei.name)  # der Pegel wird in Python skaliert


def test_toene_waehlen_den_sprach_ordner_und_finden_jeden_ton():
    t = Toene(SPRACHE, ["afplay", "{datei}"])
    for n in namen(MELODIE) | PRUEF_NAMEN:
        assert t.kommando_fuer(n, 50) is not None, n
    t._temp.clear()


def test_die_tonfolge_der_karte_findet_im_sprach_ordner_jede_datei():
    bericht = selftest.Pruefbericht((
        selftest.pruefe_leser("simulation"),
        selftest.pruefe_medien(None),
        selftest.pruefe_netz("offline", False),
        selftest.pruefe_speicher(10_000, False),
    ))
    assert bericht.toene == ["pruef_leser_simulation", "pruef_medien_fehler", "pruef_netz_fehler", "pruef_speicher_ok"]
    t = Toene(SPRACHE, ["afplay", "{datei}"])
    for n in bericht.toene:
        assert t.datei(n) == SPRACHE / f"{n}.wav"


def test_melodie_ordner_bleibt_gueltig_durch_den_rueckfall():
    t = Toene(MELODIE, ["afplay", "{datei}"])
    assert t.datei("pruef_leser_simulation") == MELODIE / "pruef_ok.wav"
    assert t.datei("pruef_speicher_fehler") == MELODIE / "pruef_fehler.wav"


# --- Testmedien --------------------------------------------------------------------------------------


@pytest.fixture
def bib(tmp_path):
    """Lädt nur die versionierten Serien: sie werden in ein tmp_path kopiert, lokale Ordner bleiben außen vor."""
    import logging

    zeilen: list[logging.LogRecord] = []

    class H(logging.Handler):
        def emit(self, record):
            zeilen.append(record)

    kopie = tmp_path / "medien-sprache"
    for s in VERSIONIERTE_SERIEN:
        shutil.copytree(MEDIEN / s, kopie / s)

    log = logging.getLogger("tobibox")
    alt, level = log.handlers[:], log.level
    log.handlers = [H()]
    log.setLevel(logging.DEBUG)
    try:
        b = library.lade_bibliothek(kopie)
    finally:
        log.handlers = alt
        log.setLevel(level)
    return b, zeilen


def test_medien_sprache_laedt_ohne_warnung(bib):
    b, zeilen = bib
    assert [r for r in zeilen if r.levelno >= 30] == []
    assert {s.id: s.name for s in b.serien} == {
        "5e1a0c7d9b31": "Test-Serie",
        "7b3f2a6e8c14": "Lange Serie",
        "9d4c1e5a2f68": "Track-Test",
        "e2a8b6d0c397": "Überraschung",
    }
    assert b.ueberraschung_status == "ok"


def test_alle_dauern_sind_bekannt(bib):
    b, _ = bib
    for s in b.serien:
        for folge in s.folgen:
            d = s.dauern.get(folge)
            assert d is not None and len(d) == len(s.tracks[folge]) and all(x and x > 0 for x in d), (s.id, folge)


def test_aufbau_der_serien(bib):
    b, _ = bib
    s = {x.id: x for x in b.serien}
    test = s["5e1a0c7d9b31"]
    assert test.folgen == ("folge-01.mp3", "folge-02.mp3", "folge-03.mp3")
    assert all(sum(test.dauern[f]) <= 10.0 for f in test.folgen)
    lang = s["7b3f2a6e8c14"]
    assert len(lang.folgen) == 2 and all(88 < sum(lang.dauern[f]) < 92 for f in lang.folgen)
    track = s["9d4c1e5a2f68"]
    assert track.folgen == ("folge-01",) and len(track.tracks["folge-01"]) == 3
    assert all(7.5 < d < 8.5 for d in track.dauern["folge-01"])
    ueb = s["e2a8b6d0c397"]
    assert ueb.typ == "ueberraschung" and 3.5 < sum(ueb.dauern["ton-01.mp3"]) < 5.0


def test_mp3_sind_mono_und_klein():
    for mp3 in versionierte_dateien("*.mp3"):
        roh = mp3.read_bytes()
        start = 0
        if roh[:3] == b"ID3":  # ID3-Kopf überspringen (Größe als 4 x 7 Bit)
            start = 10 + ((roh[6] & 0x7F) << 21 | (roh[7] & 0x7F) << 14 | (roh[8] & 0x7F) << 7 | (roh[9] & 0x7F))
        kopf = roh[start:start + 4]
        assert kopf[0] == 0xFF and (kopf[1] & 0xE0) == 0xE0 and (kopf[3] >> 6) == 3, mp3  # Kanalmodus 3 = mono
        assert audiodauer.dauer_s(mp3) is not None
    assert sum(p.stat().st_size for p in versionierte_dateien()) < 2_000_000


def test_die_lange_serie_faellt_unter_die_restregel(bib):
    b, _ = bib
    lang = next(s for s in b.serien if s.id == "7b3f2a6e8c14")
    gesamt = sum(lang.dauern["folge-01.mp3"])
    assert gesamt >= session.REST_REGEL_MIN_FOLGE_S  # ab 60 s gilt die Regel
    uid = "04a1b2d7"

    def start(pos: float) -> ev.Abspielen:
        h = SitzungsHarnisch(serien=b.serien, konfig=False, zeiger=[zeiger(lang.id, "folge-01.mp3", 0, pos, 1)])
        h.sende(ev.KonfigGeladen(mk_konfig({**ZUORDNUNGEN, uid: ev.Zuordnung("serie", lang.id)})))
        (a,) = [x for x in h.sende(ev.Aufgelegt(uid, "ntag", False, 5, "v2")) if isinstance(x, ev.Abspielen)]
        return a

    a = start(gesamt - session.REST_FERTIG_S + 1.0)  # Rest knapp unter 15 s: fertig gehört, nächste Folge von vorn
    assert (a.datei, a.position_s) == ("folge-02.mp3", 0.0)
    a = start(30.0)  # mitten drin: 3 s Rücksprung
    assert (a.datei, a.position_s) == ("folge-01.mp3", 27.0)
