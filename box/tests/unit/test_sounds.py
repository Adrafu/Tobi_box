"""Töne: Kommando, Pegel (``core-interface.md``, 8.1), kein Aufruf ohne Datei."""

from __future__ import annotations

import pytest

from tobibox.config import STANDARD_TON_KOMMANDO
from tobibox.sounds import Toene, baue_kommando, pegel


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
    assert baue_kommando(STANDARD_TON_KOMMANDO, d, 40) == ["afplay", "-v", "0.40", str(d)]
    assert baue_kommando(["aplay", "-q", "-D", "softvol", "{datei}"], d, 40) == ["aplay", "-q", "-D", "softvol", str(d)]
    assert baue_kommando(["x", "--pegel={pegel}", "{datei}"], d, 7)[1] == "--pegel=7"


def mk(tmp_path, gespielt):
    async def starter(k):
        gespielt.append(list(k))

    (tmp_path / "start.wav").write_bytes(b"RIFF")
    (tmp_path / "hinweis.wav").write_bytes(b"RIFF")
    return Toene(tmp_path, STANDARD_TON_KOMMANDO, starter=starter)


async def test_spielt_mit_pegel_unter_grenze(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    assert t.spiele("start", 25)
    assert t.spiele("hinweis", 100, hinweis_pegel=20)
    await t.warte()
    assert g == [
        ["afplay", "-v", "0.25", str(tmp_path / "start.wav")],
        ["afplay", "-v", "0.20", str(tmp_path / "hinweis.wav")],
    ]


async def test_kein_aufruf_ohne_datei(tmp_path):
    g: list = []
    t = mk(tmp_path, g)
    assert not t.spiele("fehler", 50)  # fehler.wav fehlt
    assert not t.spiele("pruef_ok", 50)
    await t.warte()
    assert g == []


async def test_fehlendes_programm_wirft_nicht(tmp_path):
    (tmp_path / "start.wav").write_bytes(b"RIFF")
    t = Toene(tmp_path, ["gibt-es-nicht-xyz", "{datei}"])
    assert t.spiele("start", 50)
    await t.warte()  # kein Fehler
