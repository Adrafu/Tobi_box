"""Paket A3b3 „Kapitel und Codecs“ (Vertrag W, 14.7 und 14.2; Design 11.4.4 und 11.4.8)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from custom_components.tobibox import dauer as dauer_modul
from custom_components.tobibox import ffprobe
from custom_components.tobibox.const import KAPITEL_MAX, KAPITEL_TITEL_MAX
from custom_components.tobibox.dauer import DauerDienst
from custom_components.tobibox.kapitel import TrackInfo, baue_kapitel, titel_aus_dateiname

from .conftest import braucht_ffmpeg, erzeuge_audio
from .test_websocket_api import ok


def t(name="a.mp3", dauer=60.0, titel="", kapitel=None, codec="mp3"):
    return TrackInfo(name=name, dauer_s=dauer, codec=codec, titel=titel, kapitel=kapitel or [])


# --------------------------------------------------------------------------
# Reine Logik
# --------------------------------------------------------------------------


def test_titel_aus_dateiname():
    assert titel_aus_dateiname("03 - Der Wald.mp3") == "Der Wald"
    assert titel_aus_dateiname("1. Anfang.flac") == "Anfang"
    assert titel_aus_dateiname("Der Wald.mp3") == "Der Wald"
    assert titel_aus_dateiname("01.mp3") == ""


def test_ordner_folge_jeder_track_ein_kapitel():
    tracks = [t("01 Eins.mp3", 10.4, "Der Anfang"), t("02 Zwei.mp3", 20.0), t("03.mp3", 5.0)]
    k = baue_kapitel(tracks, True)
    assert k == [
        {"titel": "Der Anfang", "start_s": 0, "track": 0},
        {"titel": "Zwei", "start_s": 10, "track": 1},
        {"titel": "3", "start_s": 30, "track": 2},  # ohne Titel: die Nummer, die Seite zeigt „Kapitel 3“
    ]


def test_eine_datei_ohne_kapitel_und_ein_track_haben_keine_liste():
    assert baue_kapitel([t()], False) == []
    assert baue_kapitel([t()], True) == []
    assert baue_kapitel([t(kapitel=[(0.0, "Nur eins")])], False) == []  # unter zwei


def test_eingebettete_kapitel_gewinnen_je_track():
    tracks = [t("a.m4b", 100, kapitel=[(0, "A1"), (50, "A2")]), t("b.mp3", 30, "B")]
    k = baue_kapitel(tracks, True)
    assert [(x["titel"], x["start_s"], x["track"]) for x in k] == [("A1", 0, 0), ("A2", 50, 0), ("B", 100, 1)]


def test_doppelte_startzeiten_und_rueckspruenge_fallen_weg():
    roh = [(0, "a"), (10, "b"), (10, "doppelt"), (5, "zurueck"), (20, "c"), (-3, "negativ"), (999, "hinter dem Ende")]
    k = baue_kapitel([t(dauer=100, kapitel=roh)], False)
    assert [x["titel"] for x in k] == ["a", "b", "c"]
    assert [x["start_s"] for x in k] == sorted({x["start_s"] for x in k})


def test_hoechstens_500_kapitel_und_titel_gekuerzt():
    roh = [(float(i), "x" * 300) for i in range(800)]
    k = baue_kapitel([t(dauer=1000, kapitel=roh)], False)
    assert len(k) == KAPITEL_MAX
    assert len(k[0]["titel"]) <= KAPITEL_TITEL_MAX


# --------------------------------------------------------------------------
# ffprobe und Nachholen mit echten Dateien
# --------------------------------------------------------------------------

pytestmark_ff = braucht_ffmpeg


@braucht_ffmpeg
@pytest.mark.parametrize("endung", ["m4b", "mp3"])
def test_ffprobe_liest_eingebettete_kapitel(tmp_path, endung):
    erzeuge_audio(tmp_path / f"b.{endung}", dauer=3.0, kapitel=["Eins", "Zwei", "Drei"])
    p = ffprobe.probe_datei(tmp_path / f"b.{endung}")
    assert [titel for _, titel in p.kapitel] == ["Eins", "Zwei", "Drei"]
    assert [s for s, _ in p.kapitel] == [0.0, 0.5, 1.0]
    assert "-show_chapters" in ffprobe.baue_ffprobe_befehl(tmp_path / "b.mp3", "mp3")


@pytest.fixture
async def ohne_nachholen(monkeypatch, starte_integration):
    async def starte():
        with monkeypatch.context() as m:
            m.setattr(DauerDienst, "nachholen_beim_start", lambda self: None)
            return await starte_integration()

    return starte


def bestand(nas):
    erzeuge_audio(nas.medien / "Buch" / "hoerbuch.m4b", dauer=3.0, kapitel=["Eins", "Zwei", "Drei"])
    erzeuge_audio(nas.medien / "Buch" / "Ordner" / "01 Anfang.mp3", dauer=2.0)
    erzeuge_audio(nas.medien / "Buch" / "Ordner" / "02 Ende.mp3", dauer=3.0, title="Das Ende")
    erzeuge_audio(nas.medien / "Buch" / "ohne.mp3", dauer=1.0)
    nas.serie("Buch", serie_id="b1", name="Buch", folgen=["hoerbuch.m4b", "Ordner", "ohne.mp3"])


@braucht_ffmpeg
async def test_nachholen_liest_kapitel_und_codecs_auch_bei_vorhandener_dauer(hass, hass_ws_client, ohne_nachholen, nas):
    bestand(nas)
    hub = await ohne_nachholen()
    # Bestand aus A3b: Dauer da, aber weder Kapitel noch Codecs noch Stand
    for f in ("hoerbuch.m4b", "Ordner", "ohne.mp3"):
        hub.medieninfo.setze_dauer("b1", f, 5)
    ws = await hass_ws_client(hass)
    vorher = await ok(ws, "serie/get", serie_id="b1")
    json_pfad = nas.medien / "Buch" / "serie.json"
    roh_vorher = json_pfad.read_bytes()
    with patch.object(dauer_modul, "messe_folge", wraps=dauer_modul.messe_folge) as messe:
        hub.dauer.nachholen_beim_start()
        await hub.dauer.warte_auf_ende()
        assert messe.call_count == 3
    nachher = await ok(ws, "serie/get", serie_id="b1")
    buch, ordner, ohne = nachher["folgen"]
    assert [k["titel"] for k in buch["kapitel"]] == ["Eins", "Zwei", "Drei"] and "track" not in buch["kapitel"][0]
    assert [(k["titel"], k["track"]) for k in ordner["kapitel"]] == [("Anfang", 0), ("Das Ende", 1)]
    assert ordner["kapitel"][1]["start_s"] == ordner["spuren_s"][0]
    assert "kapitel" not in ohne
    assert nachher["kapitel_anzahl"] == 5
    assert hub.medieninfo.codecs("b1", "hoerbuch.m4b") == ["aac"] and hub.medieninfo.codecs("b1", "Ordner") == ["mp3", "mp3"]
    # die Box liest serie.json unverändert; der Lauf ändert den stand nicht
    assert json_pfad.read_bytes() == roh_vorher
    assert nachher["stand"] == vorher["stand"]
    assert "kapitel" not in json.dumps(json.loads(json_pfad.read_text()))
    # ein zweiter Lauf liest nichts mehr
    hub.dauer.beim_start_nachgeholt = False
    with patch.object(dauer_modul, "messe_folge") as messe:
        hub.dauer.nachholen_beim_start()
        await hub.dauer.warte_auf_ende()
        messe.assert_not_called()


@braucht_ffmpeg
async def test_serien_list_und_folgen_list_zeigen_die_kapitelzahl(hass, hass_ws_client, starte_integration, nas):
    bestand(nas)
    hub = await starte_integration()
    await hub.dauer.warte_auf_ende()
    ws = await hass_ws_client(hass)
    assert (await ok(ws, "serien/list"))["serien"][0]["kapitel_anzahl"] == 5
    zeilen = {z["folge"]: z["kapitel"] for z in (await ok(ws, "folgen/list"))["folgen"]}
    assert zeilen == {"hoerbuch.m4b": 3, "Ordner": 2, "ohne.mp3": 0}


@braucht_ffmpeg
async def test_beim_einsortieren_kommen_kapitel_und_codecs_aus_den_proben(hass, integration, nas):
    from .test_eingang import sortiere

    erzeuge_audio(nas.eingang / "Kapitelbuch.m4b", dauer=3.0, kapitel=["A", "B", "C"], album="Kapitelbuch", album_artist="Autor")
    with patch.object(dauer_modul, "messe_folge", wraps=dauer_modul.messe_folge) as messe:
        await sortiere(integration)
        await integration.dauer.warte_auf_ende()
        assert messe.call_count == 0  # ein ffprobe-Lauf je Datei genügt
    sid = next(s for s, i in integration.medien.serien.items() if any(n.startswith("Kapitelbuch") for n in i.serie.folgen))
    name = next(n for n in integration.medien.serien[sid].serie.folgen if n.startswith("Kapitelbuch"))
    assert [k["titel"] for k in integration.medieninfo.kapitel(sid, name)] == ["A", "B", "C"]
    assert integration.medieninfo.codecs(sid, name) == ["aac"]
