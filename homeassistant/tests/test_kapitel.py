"""Paket A3b3 „Kapitel und Codecs“ (Vertrag W, 14.7 und 14.2; Design 11.4.4 und 11.4.8)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from custom_components.tobibox import dauer as dauer_modul
from custom_components.tobibox import ffprobe
from custom_components.tobibox.const import KAPITEL_MAX, KAPITEL_ROH_MAX, KAPITEL_TITEL_MAX
from custom_components.tobibox.dauer import DauerDienst
from custom_components.tobibox.kapitel import TrackInfo, baue_kapitel, bereinige_titel, titel_aus_dateiname

from .conftest import braucht_ffmpeg, erzeuge_audio
from .test_websocket_api import ok


def t(name="a.mp3", dauer=60.0, titel="", kapitel=None, codec="mp3"):
    return TrackInfo(name=name, dauer_s=dauer, codec=codec, titel=titel, kapitel=kapitel or [])


# --------------------------------------------------------------------------
# Reine Logik
# --------------------------------------------------------------------------


def test_titel_aus_dateiname():
    # roh: die Nummer fällt erst beim Ausgeben weg (AM22)
    assert titel_aus_dateiname("03 - Der Wald.mp3") == "03 - Der Wald"
    assert titel_aus_dateiname("100% Wolf - Track #01.mp3") == "100% Wolf - Track #01"
    assert titel_aus_dateiname("Der Wald.mp3") == "Der Wald"
    assert titel_aus_dateiname("01.mp3") == "01"


def test_ordner_folge_jeder_track_ein_kapitel():
    tracks = [t("01 Eins.mp3", 10.4, "Der Anfang"), t("02 Zwei.mp3", 20.0), t("03.mp3", 5.0)]
    k = baue_kapitel(tracks, True)
    assert k == [
        {"titel": "Der Anfang", "start_s": 0, "track": 0},
        {"titel": "02 Zwei", "start_s": 10, "track": 1},  # roh, bereinigt wird beim Ausgeben
        {"titel": "03", "start_s": 30, "track": 2},
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
    roh = [(float(i), "x" * 600) for i in range(800)]
    k = baue_kapitel([t(dauer=1000, kapitel=roh)], False)
    assert len(k) == KAPITEL_MAX
    assert len(k[0]["titel"]) == KAPITEL_ROH_MAX  # roh gespeichert, die Ausgabe kürzt auf KAPITEL_TITEL_MAX


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


# --------------------------------------------------------------------------
# AM22: Titel bereinigen (echte Fälle aus dem Bestand)
# --------------------------------------------------------------------------


def _folge(vorn, n, hinten="", breite=2):
    return [f"{vorn}{i:0{breite}d}{hinten}" for i in range(1, n + 1)]


@pytest.mark.parametrize(
    "roh",
    [
        _folge("100% Wolf - Track #", 12),
        _folge("Affenzahn Utopia - Die Abenteuer von Affenzahn - Track #", 25),
        _folge("Alea Aquarius - Die Magie der Nixen - Track #", 10),
        [f"{i:02d} Ela das All eroberte" for i in range(1, 11)],
        [f"Kapitel {i:02d}: Aristocats" for i in range(1, 5)],
        ["Trim-It´s gettin´ HARD in here #063.mp3"] * 3,
        ["1", "2", "3"],
        ["01", "02", "03"],
    ],
)
def test_bereinigen_nur_nummern_wird_kapitel_n(roh):
    assert bereinige_titel(roh) == [""] * len(roh)  # "" = die Seite zeigt „Kapitel n“


def test_bereinigen_wundervolle_welt_der_tiere():
    roh = [
        "Kapitel 01: Der Wal, der Elefant und das Krokodil - Wundervolle Welt der Tiere",
        "Kapitel 02: Der Hai, die Giraffe und das Nashorn - Wundervolle Welt der Tiere",
        "Kapitel 03: Der Wolf - Wundervolle Welt der Tiere",
    ]
    assert bereinige_titel(roh) == ["Der Wal, der Elefant und das Krokodil", "Der Hai, die Giraffe und das Nashorn", "Der Wolf"]


def test_bereinigen_dinosaurier():
    s = " - Wundervolle Welt der Dinosaurier und der Urzeit"
    roh = [f"Kapitel 01: Einführung, Erdaltertum{s}", f"Kapitel 02: Erdaltertum{s}"] + [f"Kapitel {i:02d}: Teil {i}{s}" for i in range(3, 39)]
    aus = bereinige_titel(roh)
    assert aus[:3] == ["Einführung, Erdaltertum", "Erdaltertum", "Teil 3"]
    assert aus[-1] == "Teil 38"


def test_bereinigen_conni_behaelt_kapitelangaben():
    s = " - Conni & Co 1: Conni & Co"
    roh = [f"Kapitel 1 & Kapitel 2.1{s}", f"Kapitel 2.2{s}", f"Kapitel 2.3 & Kapitel 3.1{s}", f"Kapitel 3.2{s}"]
    assert bereinige_titel(roh) == ["Kapitel 1 & Kapitel 2.1", "Kapitel 2.2", "Kapitel 2.3 & Kapitel 3.1", "Kapitel 3.2"]


def test_bereinigen_zippel():
    s = " - Zippel, das wirklich wahre Schlossgespenst"
    roh = [f"Kapitel 1.1{s}", f"Kapitel 1.2 & Kapitel 2.1{s}", f"Kapitel 2.2{s}", f"Kapitel 3.1{s}"] + [f"Kapitel {i}.1{s}" for i in range(4, 12)]
    assert bereinige_titel(roh)[:3] == ["Kapitel 1.1", "Kapitel 1.2 & Kapitel 2.1", "Kapitel 2.2"]


def test_bereinigen_sprechende_titel_bleiben():
    lieder = ["Fredrik Vahle - Lied vom Wecken (Anne Kaffeekanne)", "Fredrik Vahle - Vom Laufenlernen (Anne Kaffeekanne)", "Das Katzentatzentanzspiel"]
    assert bereinige_titel(lieder) == lieder
    schule = ["Schulschluss", "Benny fährt Fahrrad", "Schein! Schein! Schein!"]
    assert bereinige_titel(schule) == schule


def test_bereinigen_einzelne_titel_gegenproben():
    assert bereinige_titel(["100% Wolf", "Der Fuchs"]) == ["100% Wolf", "Der Fuchs"]
    assert bereinige_titel(["01 - Intro", "02 - Ende"]) == ["Intro", "Ende"]
    assert bereinige_titel(["1. Teil", "Der Rest"]) == ["Teil", "Der Rest"]
    assert bereinige_titel(["2019 Live", "Zugabe"]) == ["2019 Live", "Zugabe"]
    assert bereinige_titel(["7 Zwerge", "Schneewittchen"]) == ["7 Zwerge", "Schneewittchen"]
    assert bereinige_titel(["Eins", "Zwei", "Eins"]) == ["", "Zwei", ""]  # mehrfach: Kapitel n


def test_bereinigen_kuerzt_erst_nach_dem_bereinigen():
    s = " - " + "Serie " * 30
    assert bereinige_titel([f"Anfang{s}", f"Ende{s}"]) == ["Anfang", "Ende"]


# --------------------------------------------------------------------------
# AM23: Ausreißer, „nur eine Nummer“, gemeinsames Ende ohne Trenner
# --------------------------------------------------------------------------


def _sicht(aus):
    """Wie die Seite es zeigt: ``""`` wird zu „Kapitel <Position>“."""
    return [t or f"Kapitel {i}" for i, t in enumerate(aus, 1)]


def test_am23_ausreisser_lied_am_anfang_baggerfahrer():
    s = " - als Baggerfahrer (Folge 109)"
    roh = ["Benjamin Blümchen Lied"] + [f"Kapitel {i:02d}{s}" for i in range(1, 38)]
    aus = bereinige_titel(roh)
    assert aus[0] == "Benjamin Blümchen Lied"
    assert aus[1:4] == ["Kapitel 1", "Kapitel 2", "Kapitel 3"]  # Nummer aus dem Titel, nicht die Position (2, 3, 4)


def test_am23_ausreisser_schlafliedchen():
    s = ": Der kleine Hirsch und die Prinzessin (GNG Folge 15)"
    roh = ["Schlafliedchen"] + [f"Kapitel {i:02d}{s}" for i in range(1, 33)]
    aus = bereinige_titel(roh)
    assert aus[:2] == ["Schlafliedchen", "Kapitel 1"]
    assert aus[2] == "Kapitel 2"  # Nummer 2 steht an Position 3


def test_am23_ausreisser_spidey_titellied():
    roh = ["Marvels Spidey und seine Super-Freunde - Titellied"] + [f"Kapitel {i:02d}: Das Spidey-Team" for i in range(1, 13)]
    aus = bereinige_titel(roh)
    assert aus[0] == "Marvels Spidey und seine Super-Freunde - Titellied"
    assert aus[1:3] == ["Kapitel 1", "Kapitel 2"]


def test_am23_ausreisser_intro_perle():
    roh = ["Intro"] + [f"Kapitel {i:02d} - Die magische Perle (Folge 001)" for i in range(1, 15)]
    aus = bereinige_titel(roh)
    assert aus[:3] == ["Intro", "Kapitel 1", "Kapitel 2"]


def test_am23_ausreisser_am_ende():
    roh = [f"Kapitel {i:02d} - Der Wald (Folge 7)" for i in range(1, 11)] + ["Abspann"]
    aus = bereinige_titel(roh)
    assert aus[-1] == "Abspann"
    assert _sicht(aus)[:2] == ["Kapitel 1", "Kapitel 2"]


def test_am23_nummer_titelsong_dann_kapitel():
    assert bereinige_titel(["Titelsong", "Kapitel 01", "Kapitel 02"]) == ["Titelsong", "Kapitel 1", "Kapitel 2"]


def test_am23_princess_adventure():
    roh = ["20 Princess Adventure"] + [f"Track #{i:02d}" for i in range(2, 21)]
    aus = bereinige_titel(roh)
    assert aus[0] == "20 Princess Adventure"
    assert _sicht(aus)[1:4] == ["Kapitel 2", "Kapitel 3", "Kapitel 4"]


def test_am23_yakari_track_ab_zwei():
    roh = [f"Yakari - Best of Kleiner Donner - Track #{i:02d}" for i in range(2, 12)]
    assert bereinige_titel(roh) == [f"Kapitel {i}" for i in range(2, 12)]


def test_am23_raeuber_ratte():
    roh = [f"Räuber Ratte - Räuber Ratte - Track #{i:02d}" for i in range(1, 9)]
    assert _sicht(bereinige_titel(roh)) == [f"Kapitel {i}" for i in range(1, 9)]


def test_am23_conni_zwei_alben_nie_doppeltes_kapitel_1():
    roh = [f"Conni auf dem Bauernhof - Track #{i:02d}" for i in range(1, 4)] + [f"Conni und das neue Baby - Track #{i:02d}" for i in range(1, 4)]
    aus = bereinige_titel(roh)
    assert len(aus) == 6
    assert aus.count("Kapitel 1") <= 1
    assert aus == roh or aus == [""] * 6


def test_am23_gleiche_nummer_mehrfach_wird_position():
    roh = [f"Track #{i:02d}" for i in range(1, 4)] * 2
    assert bereinige_titel(roh) == [""] * 6


def test_am23_gemeinsames_ende_ohne_trenner():
    roh = [f"{i}Trim-It´s gettin´ HARD in here #063.mp3" for i in range(1, 4)]
    assert _sicht(bereinige_titel(roh)) == ["Kapitel 1", "Kapitel 2", "Kapitel 3"]


def test_am23_nur_nummer_formen():
    assert bereinige_titel(["Track 02", "Teil 03", "Kapitel 05"]) == ["Kapitel 2", "Kapitel 3", "Kapitel 5"]
    assert bereinige_titel(["Intro", "01", "02"]) == ["Intro", "Kapitel 1", "Kapitel 2"]


def test_am23_gegenproben_sprechende_titel_bleiben():
    schule = ["Schulschluss", "Benny fährt Fahrrad", "Schein! Schein! Schein!", "Der Brief", "Das Gespräch"]
    assert bereinige_titel(schule) == schule
    for roh in (
        ["Alles vermurkst 1", "Alles vermurkst 2", "Alles vermurkst 3", "Zum Schluss"],
        ["Aller Anfang ist schwer, Teil 1", "Aller Anfang ist schwer, Teil 2", "Das Ende"],
        ["01-02 Die Unbesiegbaren", "03-04 Ich bin der Beste", "05-06 Die Speckröllchen"],
        ["7 Zwerge", "Schneewittchen", "Der Wolf"],
    ):
        assert bereinige_titel(roh) == roh


def test_am23_zippel_und_conni_kapitelangaben_bleiben_mit_ausreisser():
    s = " - Zippel, das wirklich wahre Schlossgespenst"
    roh = ["Titellied"] + [f"Kapitel 1.1{s}", f"Kapitel 1.2 & Kapitel 2.1{s}", f"Kapitel 2.2{s}", f"Kapitel 3.1{s}"] + [f"Kapitel {i}.1{s}" for i in range(4, 12)]
    aus = bereinige_titel(roh)
    assert aus[:4] == ["Titellied", "Kapitel 1.1", "Kapitel 1.2 & Kapitel 2.1", "Kapitel 2.2"]
