"""Prüfpunkte und Tonfolge der Status-Admin-Karte (core-interface.md, 12.3)."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from tobibox import events as ev
from tobibox import selftest as st

SOUNDS = Path(__file__).resolve().parents[2] / "sounds"


def serie(sid="a", typ="normal", folgen=("1.mp3",)):
    return ev.Serie(id=sid, name=sid, typ=typ, ordner=sid, folgen=tuple(folgen))


GUT = (serie(), serie("u", "ueberraschung", ("x.mp3",)))


@pytest.mark.parametrize("wert,ok", [("ok", True), ("simulation", True), ("getrennt", False), ("fehler", False)])
def test_leser(wert, ok):
    assert st.pruefe_leser(wert).ok is ok


@pytest.mark.parametrize("serien,ok", [
    (GUT, True),
    (None, False),
    ((), False),
    ((serie(folgen=()), serie("u", "ueberraschung", ())), False),
    ((serie(),), False),  # keine Überraschung
    ((serie(), serie("u", "ueberraschung", ("x",)), serie("v", "ueberraschung", ("y",))), False),
    ((serie(), serie("u", "ueberraschung", ())), False),  # leere Überraschung
])
def test_medien(serien, ok):
    assert st.pruefe_medien(serien).ok is ok


@pytest.mark.parametrize("netz,ha,ok", [
    ("home", True, True), ("hotspot", True, True), ("home", False, False), ("offline", True, False), ("offline", False, False),
])
def test_netz(netz, ha, ok):
    assert st.pruefe_netz(netz, ha).ok is ok


@pytest.mark.parametrize("frei,verloren,ok", [
    (500, False, True), (499, False, False), (5000, True, False), (None, False, False),
])
def test_speicher(frei, verloren, ok):
    assert st.pruefe_speicher(frei, verloren).ok is ok


def test_tonfolge_reihenfolge_und_toene():
    ps = [st.Pruefpunkt("leser", True, ""), st.Pruefpunkt("medien", False, ""),
          st.Pruefpunkt("netz", True, ""), st.Pruefpunkt("speicher", False, "")]
    assert st.tonfolge(ps) == ["pruef_ok", "pruef_fehler", "pruef_ok", "pruef_fehler"]


def test_pruefroutine_ohne_leser_ist_simulation(tmp_path):
    (tmp_path / "leer").mkdir()
    b = st.pruefe(tmp_path / "leer")
    assert [p.name for p in b.punkte] == list(st.PUNKTE)
    assert b.punkte[0].ok and b.punkte[0].detail == "simulation"
    assert not b.punkte[1].ok and not b.punkte[2].ok  # leere Medien, offline
    assert b.toene[:3] == ["pruef_ok", "pruef_fehler", "pruef_fehler"]
    assert b.als_dict()["ok"] is False


def test_pruefroutine_medienordner_fehlt(tmp_path):
    b = st.pruefe(tmp_path / "nix", leser="getrennt", netz="home", ha_verbunden=True)
    assert b.toene[:3] == ["pruef_fehler", "pruef_fehler", "pruef_ok"]


def test_pruefroutine_speicher_grenze(tmp_path):
    b = st.pruefe(tmp_path, min_frei_mb=10**9)
    assert b.punkte[3].ok is False


@pytest.mark.parametrize("name", ["pruef_ok", "pruef_fehler"])
def test_wavs_vorhanden(name):
    with wave.open(str(SOUNDS / f"{name}.wav")) as w:
        assert w.getnframes() > 0
