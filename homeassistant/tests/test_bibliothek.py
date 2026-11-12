"""Paket A3 „Art und Bibliothek-Backend“ (Vertrag W, 3.12 und 14.2; Design 5.2, 11.2 V-2 und V-8).

* Art-Regeln mit Tag-Fixtures (rein und mit echten Audiodateien beim Einsortieren), ``serie/art_setzen``.
* ``serien/list``: Suche, Filter, Sortieren, Blättern, Einzeltitel; alte Aufrufe ohne ``limit`` bleiben gleich.
* ``folgen/list``, ``zuordnung/list`` mit ``text`` und ``neu``.
* Leistung: 600 Einträge, 2 000 Folgen und 300 Einzeltitel, Suche unter 200 ms.
"""

from __future__ import annotations

import json
import time
from datetime import timedelta

import pytest

from custom_components.tobibox import const
from custom_components.tobibox.bibliothek import ArtDatei, art_vorschlag, suchform, suchworte
from custom_components.tobibox.media import serie_aus_json
from custom_components.tobibox.util import iso, jetzt

from .conftest import braucht_ffmpeg, erzeuge_audio
from .test_rechte_schutz import _client
from .test_websocket_api import fehler, ok, senden

UID = "e0040312345678ab"
UID2 = "04a1b2c3"
UID3 = "04a1b2c4"


@pytest.fixture
async def api(hass, integration, hass_ws_client):
    """Administrator."""
    return await hass_ws_client(hass)


@pytest.fixture
async def normal(hass, integration, hass_ws_client):
    return await _client(hass, hass_ws_client, "Normal")


def leere_datei(pfad, groesse: int = 0):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_bytes(b"\0" * groesse)


def lege_serie(nas, ordner: str, name: str, folgen: list[str], **extra):
    """Eine Serie mit leeren Dateien (die Prüfung ``ffprobe`` läuft nur für neue Dateien, nicht für gelistete)."""
    pfad = nas.serie(ordner, ordner, name, folgen, **extra)
    for f in folgen:
        leere_datei(pfad / f)
    return pfad


async def neu_pruefen(integration):
    await integration.medien.pruefen()


# --------------------------------------------------------------------------
# Suchform
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "erwartet"),
    [
        ("Räuber Hotzenplotz", "rauber hotzenplotz"),
        ("STRASSE", "strasse"),
        ("Straße", "strasse"),
        ("Die drei ???", "die drei"),
        ("Käpt’n Blaubär", "kapt n blaubar"),
        ("Folge 12: Der Mond", "folge 12 der mond"),
    ],
)
def test_suchform(text, erwartet):
    assert suchform(text) == erwartet


def test_suchworte_ohne_buchstaben_suchen_als_ganzes():
    assert suchworte("Rabe  Mond") == ["rabe", "mond"]
    assert suchworte("?!") == ["?!"]
    assert suchworte("   ") == []


# --------------------------------------------------------------------------
# Art-Vorschlag: die Regeln (rein)
# --------------------------------------------------------------------------


def datei(**kw) -> ArtDatei:
    return ArtDatei(**kw)


@pytest.mark.parametrize(
    ("dateien", "erwartet"),
    [
        # Genre „Hörbuch“, „Audiobook“, „Spoken“ oder Endung .m4b -> hoerbuch
        ([datei(genre="Hörbuch")], ("hoerbuch", "tags")),
        ([datei(genre="Audiobook")], ("hoerbuch", "tags")),
        ([datei(genre="Audio Book")], ("hoerbuch", "tags")),
        ([datei(genre="Spoken Word")], ("hoerbuch", "tags")),
        ([datei(genre="Hoerbuch")], ("hoerbuch", "tags")),
        ([datei(endung="m4b")], ("hoerbuch", "tags")),
        ([datei(endung="M4B", genre="Pop")], ("hoerbuch", "tags")),
        # Genre „Hörspiel“, „Audio Drama“, „Radio Play“ -> hoerspiel (Quelle tags, nicht geraten)
        ([datei(genre="Hörspiel")], ("hoerspiel", "tags")),
        ([datei(genre="Kinderhörspiel")], ("hoerspiel", "tags")),
        ([datei(genre="Audio Drama")], ("hoerspiel", "tags")),
        ([datei(genre="Radio Play")], ("hoerspiel", "tags")),
        ([datei(genre="Hörspiel", endung="m4b")], ("hoerspiel", "tags")),  # ein ausdrückliches Genre schlägt die Endung
        # Musikgenre -> musik
        ([datei(genre="Pop")], ("musik", "tags")),
        ([datei(genre="Kinderlieder")], ("musik", "tags")),
        ([datei(genre="Children's Music")], ("musik", "tags")),
        ([datei(genre="Klassik")], ("musik", "tags")),
        ([datei(genre="Schlaflied")], ("musik", "tags")),
        ([datei(genre="Rock/Pop", dauer_s=3000)], ("musik", "tags")),  # das Genre geht vor der Länge
        # Märchen, Geschichten -> geschichte
        ([datei(genre="Märchen")], ("geschichte", "tags")),
        ([datei(genre="Kindergeschichten")], ("geschichte", "tags")),
        ([datei(genre="Fairy Tales")], ("geschichte", "tags")),
        # viele kurze Tracks (Mittel unter 8 Minuten) mit Album-Interpret -> musik
        ([datei(dauer_s=180, album="Lieder", album_interpret="Chor") for _ in range(5)], ("musik", "tags")),
        ([datei(dauer_s=479, album_interpret="Chor") for _ in range(8)], ("musik", "tags")),
        # Einzeldatei unter 30 Minuten ohne Album -> geschichte
        ([datei(dauer_s=600)], ("geschichte", "tags")),
        ([datei(dauer_s=1799.5)], ("geschichte", "tags")),
        # sonst hoerspiel, geraten
        ([datei()], ("hoerspiel", "geraten")),
        ([datei(dauer_s=2400)], ("hoerspiel", "geraten")),  # Einzeldatei, aber 40 Minuten
        ([datei(dauer_s=1800)], ("hoerspiel", "geraten")),  # genau 30 Minuten zählt nicht
        ([datei(dauer_s=600, album="Folge 1")], ("hoerspiel", "geraten")),  # hat ein Album
        ([datei(dauer_s=180, album_interpret="Chor") for _ in range(4)], ("hoerspiel", "geraten")),  # nicht „viele“
        ([datei(dauer_s=600, album_interpret="Chor") for _ in range(5)], ("hoerspiel", "geraten")),  # Mittel 10 Minuten
        ([datei(dauer_s=180) for _ in range(6)], ("hoerspiel", "geraten")),  # kein Album-Interpret
        ([datei(dauer_s=None, album_interpret="Chor") for _ in range(6)], ("hoerspiel", "geraten")),  # Dauer unbekannt
        ([datei(genre="Unbekanntes Genre", dauer_s=2700, album="Folge 1")], ("hoerspiel", "geraten")),
        ([], ("hoerspiel", "geraten")),
    ],
)
def test_art_vorschlag(dateien, erwartet):
    assert art_vorschlag(dateien) == erwartet


def test_art_vorschlag_nimmt_das_genre_irgendeiner_datei():
    dateien = [datei(album="Folge 1"), datei(album="Folge 2", genre="Hörbuch"), datei(album="Folge 3")]
    assert art_vorschlag(dateien) == ("hoerbuch", "tags")


# --------------------------------------------------------------------------
# serie.json: art, art_quelle, einzeln
# --------------------------------------------------------------------------

JSON_BASIS = {"schema_version": 1, "id": "x", "name": "X", "typ": "normal", "folgen": [], "angelegt_am": "2026-11-01T10:00:00Z"}


def test_serie_json_art_wird_gelesen_und_geschrieben():
    s = serie_aus_json({**JSON_BASIS, "art": "musik", "art_quelle": "tags", "einzeln": True, "frei": 1}, "x")
    assert (s.art, s.art_quelle, s.einzeln) == ("musik", "tags", True)
    aus = s.to_json()
    assert (aus["art"], aus["art_quelle"], aus["einzeln"], aus["frei"]) == ("musik", "tags", True, 1)  # unbekannte Felder bleiben


def test_serie_json_ohne_art_bleibt_ohne_art():
    s = serie_aus_json(JSON_BASIS, "x")
    assert (s.art, s.art_quelle, s.einzeln) == (None, None, False)
    assert {"art", "art_quelle", "einzeln"}.isdisjoint(s.to_json())  # die Datei wird nicht „verbessert“


def test_serie_json_ungueltige_art_gilt_als_fehlend_und_art_ohne_quelle_als_manuell():
    s = serie_aus_json({**JSON_BASIS, "art": "krimi", "art_quelle": "tags", "einzeln": "ja"}, "x")
    assert (s.art, s.art_quelle, s.einzeln) == (None, None, False)
    s = serie_aus_json({**JSON_BASIS, "art": "hoerbuch"}, "x")
    assert (s.art, s.art_quelle) == ("hoerbuch", "manuell")  # von Hand eingetragen: nie überschreiben
    s = serie_aus_json({**JSON_BASIS, "art": "hoerbuch", "art_quelle": "was"}, "x")
    assert s.art_quelle == "manuell"


# --------------------------------------------------------------------------
# Art beim Einsortieren (echte Audiodateien mit Tags)
# --------------------------------------------------------------------------

async def sortiere(hub):
    await hub.eingang.durchlauf_und_warten(sofort=True)
    await hub.hass.async_block_till_done()


def serien_json(nas) -> dict[str, dict]:
    aus = {}
    for d in sorted(nas.medien.iterdir()):
        if d.is_dir() and (d / "serie.json").exists():
            daten = json.loads((d / "serie.json").read_text(encoding="utf-8"))
            aus[daten["name"]] = daten
    return aus


@braucht_ffmpeg
@pytest.mark.parametrize(
    ("datei_name", "tags", "erwartet"),
    [
        ("a.mp3", {"genre": "Hörbuch", "album": "Buch", "album_artist": "Autor A"}, ("hoerbuch", "tags")),
        ("a.mp3", {"genre": "Audiobook", "album": "Buch", "album_artist": "Autor A"}, ("hoerbuch", "tags")),
        ("a.m4b", {"album": "Buch", "album_artist": "Autor A"}, ("hoerbuch", "tags")),
        ("a.mp3", {"genre": "Hörspiel", "album": "Folge 1", "album_artist": "Reihe R"}, ("hoerspiel", "tags")),
        ("a.mp3", {"genre": "Audio Drama", "album": "Folge 1", "album_artist": "Reihe R"}, ("hoerspiel", "tags")),
        ("a.mp3", {"genre": "Kinderlieder", "album": "Lieder", "album_artist": "Chor C"}, ("musik", "tags")),
        ("a.mp3", {"genre": "Pop", "album": "Hits", "album_artist": "Band B"}, ("musik", "tags")),
        ("a.mp3", {"genre": "Märchen", "album": "Märchen 1", "album_artist": "Erzähler E"}, ("geschichte", "tags")),
        # Einzeldatei (1 s) ohne Album und ohne Genre
        ("a.mp3", {"title": "Der Mond", "artist": "Erzähler E"}, ("geschichte", "tags")),
        # Rückfall: Album, aber nichts, woran man die Art erkennt
        ("a.mp3", {"album": "Folge 1", "album_artist": "Reihe R"}, ("hoerspiel", "geraten")),
    ],
)
async def test_einsortieren_schlaegt_die_art_vor(hass, integration, nas, datei_name, tags, erwartet):
    erzeuge_audio(nas.eingang / datei_name, **tags)
    await sortiere(integration)
    (serie,) = serien_json(nas).values()
    assert (serie["art"], serie["art_quelle"]) == erwartet
    if erwartet[1] == "geraten":
        assert serie["pruefen"] is True and "art_geraten" in serie["pruefen_gruende"]
    else:
        assert "art_geraten" not in serie.get("pruefen_gruende", [])
    kurz = next(s for s in (await integration.medien.serien_liste())["serien"] if s["id"] == serie["id"])
    assert (kurz["art"], kurz["art_quelle"], kurz["einzeln"]) == (*erwartet, False)


@braucht_ffmpeg
async def test_einsortieren_viele_kurze_tracks_mit_album_interpret_sind_musik(hass, integration, nas):
    for i in range(1, 7):
        erzeuge_audio(nas.eingang / "Lieder" / f"{i:02d}.mp3", frequenz=300 + i, album="Mitsingen", album_artist="Chor C", track=str(i), title=f"Lied {i}")
    await sortiere(integration)
    (serie,) = serien_json(nas).values()
    assert (serie["art"], serie["art_quelle"]) == ("musik", "tags") and "pruefen" not in serie


@braucht_ffmpeg
async def test_art_geraten_zusammen_mit_schwacher_serie(hass, integration, nas):
    """Eine Datei ohne Tags im Ordner: die Serie ist aus dem Ordnernamen und die Art geraten; beide Gründe stehen da."""
    erzeuge_audio(nas.eingang / "Mondgeschichten" / "x.mp3", frequenz=500)
    erzeuge_audio(nas.eingang / "Mondgeschichten" / "y.mp3", frequenz=501)
    await sortiere(integration)
    (serie,) = serien_json(nas).values()
    assert serie["pruefen"] is True
    assert serie["pruefen_gruende"] == ["serie_aus_ordner", "art_geraten"]


@braucht_ffmpeg
async def test_vorhandenes_art_wird_beim_einsortieren_nie_ueberschrieben(hass, integration, nas):
    """Neue Folgen in eine vorhandene Serie: weder ``manuell`` noch eine fehlende Art ändert sich."""
    manuell = nas.serie("rabe", "rabe", "Der kleine Rabe", [], art="musik", art_quelle="manuell")
    alt = nas.serie("alt", "alt", "Alte Reihe", [])  # alte serie.json ohne art
    await neu_pruefen(integration)
    erzeuge_audio(nas.eingang / "a.mp3", frequenz=311, genre="Hörbuch", album="Folge 1", album_artist="Der kleine Rabe")
    erzeuge_audio(nas.eingang / "b.m4b", frequenz=312, album="Folge 7", album_artist="Alte Reihe")
    await sortiere(integration)
    assert (nas.serie_json("rabe")["art"], nas.serie_json("rabe")["art_quelle"]) == ("musik", "manuell")
    assert nas.serie_json("rabe")["folgen"] == ["a.mp3"]
    assert "art" not in nas.serie_json("alt") and nas.serie_json("alt")["folgen"] == ["b.m4b"]
    assert manuell.exists() and alt.exists()


# --------------------------------------------------------------------------
# serie/art_setzen (Nr. 38)
# --------------------------------------------------------------------------


async def test_art_setzen(api, normal, nas, integration, ereignisse):
    lege_serie(nas, "rabe", "Der kleine Rabe", ["a.mp3"], art="hoerspiel", art_quelle="geraten", pruefen=True, pruefen_gruende=["art_geraten"])
    await neu_pruefen(integration)
    stand = (await ok(api, "serie/get", serie_id="rabe"))["stand"]
    ereignisse.clear()
    r = await ok(normal, "serie/art_setzen", serie_id="rabe", art="hoerbuch")  # Recht alltag
    assert (r["serie"]["art"], r["serie"]["art_quelle"], r["serie"]["pruefen"]) == ("hoerbuch", "manuell", False)
    daten = nas.serie_json("rabe")
    assert (daten["art"], daten["art_quelle"]) == ("hoerbuch", "manuell")
    assert "pruefen" not in daten and "pruefen_gruende" not in daten  # der einzige Grund war art_geraten
    assert r["serie"]["stand"] == stand and (await ok(api, "serie/get", serie_id="rabe"))["stand"] == stand  # art ändert den stand nie
    assert [(e["art"], e["daten"]) for e in ereignisse if e["thema"] == "medien"] == [("serien_geaendert", {"serie_ids": ["rabe"]})]
    # idempotent: gleicher Wert, keine Änderung, kein Ereignis
    ereignisse.clear()
    await ok(api, "serie/art_setzen", serie_id="rabe", art="hoerbuch")
    assert not [e for e in ereignisse if e["thema"] == "medien"]
    # Von Hand umgestellt: wieder wählbar
    r = await ok(api, "serie/art_setzen", serie_id="rabe", art="geschichte")
    assert r["serie"]["art"] == "geschichte"


async def test_art_setzen_loescht_nur_den_grund_art_geraten(api, nas, integration):
    lege_serie(nas, "o", "Ordner V", ["a.mp3"], art="hoerspiel", art_quelle="geraten", pruefen=True, pruefen_gruende=["serie_aus_ordner", "art_geraten"])
    await neu_pruefen(integration)
    r = await ok(api, "serie/art_setzen", serie_id="o", art="musik")
    assert r["serie"]["pruefen"] is True
    assert nas.serie_json("o")["pruefen_gruende"] == ["serie_aus_ordner"]


async def test_art_setzen_fehler(api, nas, integration):
    lege_serie(nas, "rabe", "Der kleine Rabe", ["a.mp3"])
    await neu_pruefen(integration)
    assert await fehler(api, "serie/art_setzen", serie_id="gibtsnicht", art="musik") == "serie_nicht_gefunden"
    assert await fehler(api, "serie/art_setzen", serie_id="rabe", art="krimi") == "invalid_format"
    assert await fehler(api, "serie/art_setzen", serie_id="rabe") == "invalid_format"
    assert await fehler(api, "serie/art_setzen", art="musik") == "invalid_format"


async def test_art_setzen_bei_einem_einzeltitel(api, nas, integration):
    lege_serie(nas, "mond", "Der Mond", ["lied.mp3"], einzeln=True, art="musik", art_quelle="tags")
    await neu_pruefen(integration)
    r = await ok(api, "serie/art_setzen", serie_id="mond", art="geschichte")
    assert (r["serie"]["art"], r["serie"]["einzeln"]) == ("geschichte", True)
    assert nas.serie_json("mond")["einzeln"] is True  # bleibt erhalten


# --------------------------------------------------------------------------
# serien/list
# --------------------------------------------------------------------------


@pytest.fixture
async def bibliothek(nas, integration):
    """Sieben Einträge: drei Hörspiele, ein Hörbuch, ein Album, eine Geschichte und ein Einzeltitel (Lied)."""
    heute = jetzt()
    lege_serie(nas, "rabe", "Der kleine Rabe", ["Folge 1.mp3", "Folge 2.mp3", "Folge 10.mp3"], art="hoerspiel", art_quelle="tags",
               angelegt_am=iso(heute - timedelta(days=30)))
    lege_serie(nas, "raeuber", "Räuber Hotzenplotz", ["a.mp3", "b.mp3"], art="hoerspiel", art_quelle="tags",
               angelegt_am=iso(heute - timedelta(days=3)))
    lege_serie(nas, "strasse", "Straße der Träume", ["x.mp3"], art="hoerspiel", art_quelle="geraten", pruefen=True,
               pruefen_gruende=["art_geraten"], angelegt_am=iso(heute - timedelta(days=60)))
    lege_serie(nas, "buch", "Das große Buch", ["buch.m4b"], art="hoerbuch", art_quelle="tags", angelegt_am=iso(heute - timedelta(days=90)))
    lege_serie(nas, "lieder", "Kinderlieder zum Mitsingen", ["01.mp3", "02.mp3"], art="musik", art_quelle="tags",
               angelegt_am=iso(heute - timedelta(days=100)))
    lege_serie(nas, "maerchen", "Märchenstunde", ["m1.mp3"], art="geschichte", art_quelle="tags", angelegt_am=iso(heute - timedelta(days=1)))
    lege_serie(nas, "mond", "Der Mond und der Fuchs", ["mond.mp3"], art="musik", art_quelle="tags", einzeln=True,
               angelegt_am=iso(heute - timedelta(days=2)))
    await integration.medien.pruefen()
    return integration


def namen(r):
    return [s["name"] for s in r["serien"]]


async def test_serien_list_ohne_eingaben_ist_wie_vorher(api, bibliothek):
    r = await ok(api, "serien/list")
    assert namen(r) == ["Das große Buch", "Der kleine Rabe", "Der Mond und der Fuchs", "Kinderlieder zum Mitsingen", "Märchenstunde",
                        "Räuber Hotzenplotz", "Straße der Träume"]
    # alle bisherigen Felder des Vertrags sind da, dazu nur Neues
    alt = {"serien", "ueberraschung", "geprueft_am", "pruefung_laeuft", "hinweise"}
    assert alt <= r.keys() and r.keys() - alt == {"gesamt", "weitere"}
    assert (r["gesamt"], r["weitere"]) == (7, False)
    kurz = r["serien"][0]
    assert kurz.keys() == {"id", "name", "typ", "ordner", "anzahl_folgen", "anzahl_tobies", "angelegt_am", "stand", "pruefen",
                           "anzahl_pruefen", "hinweise", "art", "art_quelle", "einzeln"}


async def test_serien_list_ohne_limit_liefert_alle_auch_ueber_200(api, nas, integration):
    for i in range(250):
        lege_serie(nas, f"s{i:03d}", f"Serie {i:03d}", ["a.mp3"])
    await neu_pruefen(integration)
    r = await ok(api, "serien/list")
    assert len(r["serien"]) == 250 and (r["gesamt"], r["weitere"]) == (250, False)  # bisheriges Verhalten (SERIEN_OHNE_LIMIT_MAX)
    r = await ok(api, "serien/list", limit=200)
    assert len(r["serien"]) == 200 and (r["gesamt"], r["weitere"]) == (250, True)


async def test_serien_list_alte_serie_json_ohne_art_zeigt_hoerspiel_geraten(api, nas, integration):
    lege_serie(nas, "alt", "Alte Reihe", ["a.mp3"])
    await neu_pruefen(integration)
    s = (await ok(api, "serien/list"))["serien"][0]
    assert (s["art"], s["art_quelle"], s["einzeln"]) == ("hoerspiel", "geraten", False)
    assert "art" not in nas.serie_json("alt")


async def test_serien_list_art(api, bibliothek):
    assert namen(await ok(api, "serien/list", art="hoerspiel")) == ["Der kleine Rabe", "Räuber Hotzenplotz", "Straße der Träume"]
    assert namen(await ok(api, "serien/list", art="musik")) == ["Der Mond und der Fuchs", "Kinderlieder zum Mitsingen"]
    assert namen(await ok(api, "serien/list", art="hoerbuch")) == ["Das große Buch"]
    assert namen(await ok(api, "serien/list", art="geschichte")) == ["Märchenstunde"]
    assert await fehler(api, "serien/list", art="krimi") == "invalid_format"


@pytest.mark.parametrize(
    ("text", "erwartet"),
    [
        ("rabe", ["Der kleine Rabe"]),
        ("RABE", ["Der kleine Rabe"]),
        ("rauber", ["Räuber Hotzenplotz"]),  # Umlaute egal
        ("Räuber", ["Räuber Hotzenplotz"]),
        ("strasse", ["Straße der Träume"]),
        ("STRAßE", ["Straße der Träume"]),
        ("traume", ["Straße der Träume"]),
        ("märchen", ["Märchenstunde"]),
        ("maerchen", []),  # „ae“ ist kein „ä“; nur die Umlaute fallen weg
        ("kleine rabe", ["Der kleine Rabe"]),  # alle Wörter, Reihenfolge egal
        ("rabe kleine", ["Der kleine Rabe"]),
        ("klei rab", ["Der kleine Rabe"]),  # Teile von Wörtern
        ("der", ["Der kleine Rabe", "Der Mond und der Fuchs", "Kinderlieder zum Mitsingen", "Straße der Träume"]),  # Teile von Wörtern
        ("mond fuchs", ["Der Mond und der Fuchs"]),  # der Einzeltitel steht als Eintrag im Index
        ("nichts davon", []),
        ("  rabe  ", ["Der kleine Rabe"]),
        ("a.mp3", []),  # in Folgen sucht nur auch_folgen
    ],
)
async def test_serien_list_text(api, bibliothek, text, erwartet):
    r = await ok(api, "serien/list", text=text)
    assert namen(r) == erwartet and r["gesamt"] == len(erwartet)


async def test_serien_list_text_und_auch_folgen(api, bibliothek):
    # in den Folgentiteln (Anzeige oder Dateiname): nur mit auch_folgen
    assert namen(await ok(api, "serien/list", text="folge 10")) == []
    assert namen(await ok(api, "serien/list", text="folge 10", auch_folgen=True)) == ["Der kleine Rabe"]
    assert namen(await ok(api, "serien/list", text="Lied", auch_folgen=False)) == ["Kinderlieder zum Mitsingen"]
    assert namen(await ok(api, "serien/list", text="buch", auch_folgen=True)) == ["Das große Buch"]
    # der Name des Eintrags findet weiterhin, auch mit auch_folgen
    assert namen(await ok(api, "serien/list", text="rabe", auch_folgen=True)) == ["Der kleine Rabe"]


@pytest.mark.parametrize("text", ["", "a", " a ", "x" * 101, 5, None])
async def test_serien_list_text_laenge(api, bibliothek, text):
    assert await fehler(api, "serien/list", text=text) == "invalid_format"


async def test_serien_list_text_grenzen_sind_gueltig(api, bibliothek):
    assert namen(await ok(api, "serien/list", text="qq")) == []
    assert (await ok(api, "serien/list", text="x" * 100))["gesamt"] == 0


async def test_serien_list_filter_einzeln_und_sammlung(api, bibliothek):
    assert namen(await ok(api, "serien/list", filter=["einzeln"])) == ["Der Mond und der Fuchs"]
    sammlung = namen(await ok(api, "serien/list", filter=["sammlung"]))
    assert "Der Mond und der Fuchs" not in sammlung and len(sammlung) == 6
    assert namen(await ok(api, "serien/list", filter=["sammlung", "einzeln"])) == []  # „und“
    # Musik, nur Alben (Design 5.2: Arten-Zeile „Musik“ plus „Nur Hörspiele, Bücher, Alben“)
    assert namen(await ok(api, "serien/list", art="musik", filter=["sammlung"])) == ["Kinderlieder zum Mitsingen"]
    assert namen(await ok(api, "serien/list", art="musik", filter=["einzeln"])) == ["Der Mond und der Fuchs"]


async def test_serien_list_filter_ohne_tobie_neu_pruefen(api, bibliothek, hass):
    k = bibliothek.store.konfig["zuordnungen"]
    k[UID] = {"ziel": {"typ": "serie", "serie": "rabe"}}
    k[UID2] = {"ziel": {"typ": "folge", "serie": "raeuber", "folge": "a.mp3"}}  # ein Tobie auf eine Folge zählt für den Eintrag
    ohne = namen(await ok(api, "serien/list", filter=["ohne_tobie"]))
    assert "Der kleine Rabe" not in ohne and "Räuber Hotzenplotz" not in ohne and len(ohne) == 5
    assert namen(await ok(api, "serien/list", filter=["neu"])) == ["Der Mond und der Fuchs", "Märchenstunde", "Räuber Hotzenplotz"]  # 14 Tage
    assert namen(await ok(api, "serien/list", filter=["pruefen"])) == ["Straße der Träume"]
    # mehrere Werte = und
    assert namen(await ok(api, "serien/list", filter=["neu", "ohne_tobie"])) == ["Der Mond und der Fuchs", "Märchenstunde"]
    assert namen(await ok(api, "serien/list", filter=["neu", "pruefen"])) == []
    assert namen(await ok(api, "serien/list", filter=["neu", "einzeln", "ohne_tobie"])) == ["Der Mond und der Fuchs"]
    assert namen(await ok(api, "serien/list", filter=[])) == namen(await ok(api, "serien/list"))
    assert await fehler(api, "serien/list", filter=["gibtsnicht"]) == "invalid_format"
    assert await fehler(api, "serien/list", filter="neu") == "invalid_format"


async def test_serien_list_pruefen_schliesst_folgen_zum_pruefen_ein(api, nas, integration):
    lege_serie(nas, "a", "Eins", ["x.mp3", "y.mp3"], folgen_info={"y.mp3": {"pruefen": True, "pruefen_gruende": ["tags_fehlen"]}})
    lege_serie(nas, "b", "Zwei", ["x.mp3"])
    await neu_pruefen(integration)
    assert namen(await ok(api, "serien/list", filter=["pruefen"])) == ["Eins"]


async def test_serien_list_sortierung(api, bibliothek, nas):
    r = await ok(api, "serien/list", sortierung="name")
    assert namen(r) == namen(await ok(api, "serien/list"))
    r = await ok(api, "serien/list", sortierung="neu")  # zuletzt angelegt zuerst
    assert namen(r) == ["Märchenstunde", "Der Mond und der Fuchs", "Räuber Hotzenplotz", "Der kleine Rabe", "Straße der Träume",
                        "Das große Buch", "Kinderlieder zum Mitsingen"]
    assert await fehler(api, "serien/list", sortierung="angehoert") == "invalid_format"  # Fähigkeit reinhoeren: Paket A4d
    assert await fehler(api, "serien/list", sortierung="zufall") == "invalid_format"


async def test_serien_list_name_sortiert_natuerlich(api, nas, integration):
    for n in (10, 2, 1):
        lege_serie(nas, f"f{n}", f"Folge {n}", ["a.mp3"])
    lege_serie(nas, "k", "folge 3", ["a.mp3"])
    await neu_pruefen(integration)
    assert namen(await ok(api, "serien/list")) == ["Folge 1", "Folge 2", "folge 3", "Folge 10"]


async def test_serien_list_blaettern(api, bibliothek):
    alle = namen(await ok(api, "serien/list"))
    seite1 = await ok(api, "serien/list", limit=3)
    seite2 = await ok(api, "serien/list", limit=3, offset=3)
    seite3 = await ok(api, "serien/list", limit=3, offset=6)
    assert namen(seite1) + namen(seite2) + namen(seite3) == alle
    assert [(s["gesamt"], s["weitere"]) for s in (seite1, seite2, seite3)] == [(7, True), (7, True), (7, False)]
    leer = await ok(api, "serien/list", limit=3, offset=7)
    assert (leer["serien"], leer["gesamt"], leer["weitere"]) == ([], 7, False)
    assert (await ok(api, "serien/list", limit=7))["weitere"] is False
    assert (await ok(api, "serien/list", limit=6))["weitere"] is True
    assert (await ok(api, "serien/list", offset=2))["serien"] == (await ok(api, "serien/list"))["serien"][2:]
    # gesamt zählt nach dem Filter, nicht die Seite
    r = await ok(api, "serien/list", art="hoerspiel", limit=2)
    assert (len(r["serien"]), r["gesamt"], r["weitere"]) == (2, 3, True)
    for falsch in (0, 201, -1, "3", True, 1.5):
        assert await fehler(api, "serien/list", limit=falsch) == "invalid_format", falsch
    for falsch in (-1, "0", True):
        assert await fehler(api, "serien/list", offset=falsch) == "invalid_format", falsch


async def test_serien_list_zaehlt_tobies_wie_bisher(api, bibliothek):
    k = bibliothek.store.konfig["zuordnungen"]
    k[UID] = {"ziel": {"typ": "serie", "serie": "rabe"}}
    k[UID2] = {"ziel": {"typ": "folge", "serie": "rabe", "folge": "Folge 1.mp3"}}
    k[UID3] = {"ziel": {"typ": "aktion", "aktion": "status"}}
    rabe = next(s for s in (await ok(api, "serien/list"))["serien"] if s["id"] == "rabe")
    assert rabe["anzahl_tobies"] == 2
    assert (await ok(api, "serie/get", serie_id="rabe"))["anzahl_tobies"] == 2


async def test_index_folgt_aenderungen(api, bibliothek, nas):
    assert namen(await ok(api, "serien/list", text="zwerg")) == []
    await ok(api, "serie/rename", serie_id="rabe", name="Der Zwerg Nase")
    assert namen(await ok(api, "serien/list", text="zwerg")) == ["Der Zwerg Nase"]
    assert namen(await ok(api, "serien/list", text="rabe")) == []
    await ok(api, "serie/art_setzen", serie_id="rabe", art="geschichte")
    assert namen(await ok(api, "serien/list", art="geschichte")) == ["Der Zwerg Nase", "Märchenstunde"]
    await ok(api, "folge/rename", serie_id="rabe", folge="Folge 1.mp3", name="Der goldene Schlüssel")
    assert namen(await ok(api, "serien/list", text="goldene", auch_folgen=True)) == ["Der Zwerg Nase"]
    await ok(api, "serie/delete", serie_id="rabe")
    assert namen(await ok(api, "serien/list", text="zwerg")) == []
    lege_serie(nas, "neu", "Neues Zwergenland", ["a.mp3"])
    await ok(api, "medien/pruefen")
    await bibliothek.medien._pruefung_task
    assert namen(await ok(api, "serien/list", text="zwerg")) == ["Neues Zwergenland"]


# --------------------------------------------------------------------------
# folgen/list (Nr. 37)
# --------------------------------------------------------------------------


async def test_folgen_list_form_und_einzeltitel_als_folge(api, bibliothek, nas):
    leere_datei(nas.medien / "mond" / "mond.mp3", 3 * 1024 * 1024)  # 3 MiB
    await neu_pruefen(bibliothek)
    k = bibliothek.store.konfig["zuordnungen"]
    k[UID] = {"ziel": {"typ": "folge", "serie": "mond", "folge": "mond.mp3"}, "name": "Fuchs"}
    r = await ok(api, "folgen/list", text="mond")
    assert (r["gesamt"], r["weitere"]) == (1, False)
    (z,) = r["folgen"]
    assert z == {
        "serie_id": "mond", "serie_name": "Der Mond und der Fuchs", "serie_einzeln": True, "art": "musik", "folge": "mond.mp3",
        "anzeige": "mond", "nummer": None, "kapitel": 0, "groesse_mb": 3.0, "tobies": [{"uid": UID, "name": "Fuchs"}], "serie_hat_tobie": False,
    }
    # derselbe Einzeltitel steht auch als Eintrag in serien/list (Serie und Folge)
    assert namen(await ok(api, "serien/list", text="mond")) == ["Der Mond und der Fuchs"]


async def test_folgen_list_text_anzeige_und_dateiname(api, nas, integration):
    lege_serie(nas, "rabe", "Der kleine Rabe", ["a.mp3", "wolfsgeheul.mp3"], folgen_info={"a.mp3": {"anzeige": "Der Räuber im Wald", "nummer": 1}})
    await neu_pruefen(integration)
    assert [f["folge"] for f in (await ok(api, "folgen/list", text="rauber"))["folgen"]] == ["a.mp3"]  # Anzeige, Umlaute egal
    assert [f["folge"] for f in (await ok(api, "folgen/list", text="wald raub"))["folgen"]] == ["a.mp3"]
    assert [f["folge"] for f in (await ok(api, "folgen/list", text="wolfsgeheul"))["folgen"]] == ["wolfsgeheul.mp3"]  # Dateiname
    assert [f["folge"] for f in (await ok(api, "folgen/list", text="wolfsgeheul.mp3"))["folgen"]] == ["wolfsgeheul.mp3"]  # auch mit Endung
    assert (await ok(api, "folgen/list", text="rabe"))["gesamt"] == 0  # der Name der Serie zählt nicht, nur der Titel der Folge
    a = (await ok(api, "folgen/list", text="wald"))["folgen"][0]
    assert (a["anzeige"], a["nummer"], a["serie_einzeln"], a["art"]) == ("Der Räuber im Wald", 1, False, "hoerspiel")


async def test_folgen_list_art_filter_und_sortierung(api, bibliothek):
    r = await ok(api, "folgen/list")
    assert r["gesamt"] == 3 + 2 + 1 + 1 + 2 + 1 + 1 == 11
    titel = [f["anzeige"] for f in r["folgen"]]
    assert titel == ["01", "02", "a", "b", "buch", "Folge 1", "Folge 2", "Folge 10", "m1", "mond", "x"]  # natürliche Sortierung nach Titel
    assert [f["anzeige"] for f in r["folgen"] if f["serie_id"] == "rabe"] == ["Folge 1", "Folge 2", "Folge 10"]
    assert {f["serie_id"] for f in (await ok(api, "folgen/list", art="musik"))["folgen"]} == {"lieder", "mond"}
    assert [f["serie_id"] for f in (await ok(api, "folgen/list", art="hoerbuch"))["folgen"]] == ["buch"]
    assert [f["serie_id"] for f in (await ok(api, "folgen/list", filter=["einzeln"]))["folgen"]] == ["mond"]
    assert "mond" not in {f["serie_id"] for f in (await ok(api, "folgen/list", filter=["sammlung"]))["folgen"]}
    assert {f["serie_id"] for f in (await ok(api, "folgen/list", filter=["neu"]))["folgen"]} == {"raeuber", "maerchen", "mond"}
    assert {f["serie_id"] for f in (await ok(api, "folgen/list", filter=["pruefen"]))["folgen"]} == {"strasse"}
    neu = [f["serie_id"] for f in (await ok(api, "folgen/list", sortierung="neu"))["folgen"]]
    assert neu[:4] == ["maerchen", "mond", "raeuber", "raeuber"]  # zuletzt angelegte Einträge zuerst, Folgen in Titelreihenfolge
    assert await fehler(api, "folgen/list", sortierung="name") == "invalid_format"


async def test_folgen_list_tobies_und_ohne_tobie(api, bibliothek):
    k = bibliothek.store.konfig["zuordnungen"]
    k[UID] = {"ziel": {"typ": "folge", "serie": "rabe", "folge": "Folge 2.mp3"}, "name": "Hase"}
    k[UID2] = {"ziel": {"typ": "folge", "serie": "rabe", "folge": "Folge 2.mp3"}}
    k[UID3] = {"ziel": {"typ": "serie", "serie": "raeuber"}}
    r = {(f["serie_id"], f["folge"]): f for f in (await ok(api, "folgen/list"))["folgen"]}
    zwei = r[("rabe", "Folge 2.mp3")]
    assert zwei["tobies"] == [{"uid": UID2, "name": None}, {"uid": UID, "name": "Hase"}]  # nach Kennung sortiert
    assert zwei["serie_hat_tobie"] is False
    assert r[("rabe", "Folge 1.mp3")]["tobies"] == []
    assert r[("raeuber", "a.mp3")]["tobies"] == [] and r[("raeuber", "a.mp3")]["serie_hat_tobie"] is True  # der Tobie gilt der ganzen Serie
    ohne = {(f["serie_id"], f["folge"]) for f in (await ok(api, "folgen/list", filter=["ohne_tobie"]))["folgen"]}
    assert ("rabe", "Folge 2.mp3") not in ohne and ("raeuber", "a.mp3") not in ohne and ("raeuber", "b.mp3") not in ohne
    assert ("rabe", "Folge 1.mp3") in ohne and len(ohne) == 11 - 1 - 2


async def test_folgen_list_blaettern_vorgabe_und_grenzen(api, nas, integration):
    for i in range(130):
        lege_serie(nas, f"s{i:03d}", f"Serie {i:03d}", [f"{i:03d}.mp3"])
    await neu_pruefen(integration)
    r = await ok(api, "folgen/list")
    assert (len(r["folgen"]), r["gesamt"], r["weitere"]) == (60, 130, True)  # Vorgabe 60
    r = await ok(api, "folgen/list", limit=100, offset=100)
    assert (len(r["folgen"]), r["weitere"]) == (30, False)
    seite = [f["folge"] for p in (0, 50, 100) for f in (await ok(api, "folgen/list", limit=50, offset=p))["folgen"]]
    assert seite == [f"{i:03d}.mp3" for i in range(130)]
    for falsch in (0, 101):
        assert await fehler(api, "folgen/list", limit=falsch) == "invalid_format"
    assert await fehler(api, "folgen/list", text="a") == "invalid_format"
    assert await fehler(api, "folgen/list", auch_folgen=True) == "invalid_format"


async def test_folgen_list_fuer_normale_benutzer(normal, bibliothek):
    r = await ok(normal, "folgen/list", limit=5)
    assert len(r["folgen"]) == 5 and (await ok(normal, "serien/list", text="rabe"))["gesamt"] == 1


# --------------------------------------------------------------------------
# zuordnung/list: text und neu
# --------------------------------------------------------------------------


async def test_zuordnung_list_text_und_neu(api, bibliothek):
    k = bibliothek.store.konfig["zuordnungen"]
    k[UID] = {"ziel": {"typ": "serie", "serie": "rabe"}, "name": "Gelber Hase", "angelegt_am": "2026-11-01T10:00:00Z"}
    k[UID2] = {"ziel": {"typ": "folge", "serie": "raeuber", "folge": "b.mp3"}, "angelegt_am": "2026-11-10T10:00:00Z"}
    k[UID3] = {"ziel": {"typ": "aktion", "aktion": "gute_nacht"}}  # ohne Zeitstempel (vor dem 12.11. angelegt)
    alle = await ok(api, "zuordnung/list")
    assert [z["uid"] for z in alle["zuordnungen"]] == [UID2, UID3, UID] and alle["gesamt"] == 3  # wie bisher nach Kennung
    uids = lambda r: [z["uid"] for z in r["zuordnungen"]]  # noqa: E731
    assert uids(await ok(api, "zuordnung/list", text="hase")) == [UID]  # Name des Tobies
    assert uids(await ok(api, "zuordnung/list", text="GELBER")) == [UID]
    assert uids(await ok(api, "zuordnung/list", text="kleine rabe")) == [UID]  # Ziel: Name des Eintrags
    assert uids(await ok(api, "zuordnung/list", text="rauber")) == [UID2]  # Ziel einer Folge: Eintrag, Umlaute egal
    assert uids(await ok(api, "zuordnung/list", text="hotzenplotz")) == [UID2]
    assert uids(await ok(api, "zuordnung/list", text="nichts davon")) == []
    r = await ok(api, "zuordnung/list", text="hase")
    assert r["gesamt"] == 1 and r["zuordnungen"][0]["angelegt_am"] == "2026-11-01T10:00:00Z"
    # neu: zuletzt angelegt zuerst, ohne Zeitstempel zuletzt
    assert uids(await ok(api, "zuordnung/list", neu=True)) == [UID2, UID, UID3]
    assert uids(await ok(api, "zuordnung/list", neu=False)) == uids(alle)
    assert "angelegt_am" not in next(z for z in alle["zuordnungen"] if z["uid"] == UID3)  # fehlt, wenn es keinen gibt
    assert uids(await ok(api, "zuordnung/list", neu=True, limit=1, offset=1)) == [UID]
    assert await fehler(api, "zuordnung/list", text="a") == "invalid_format"
    assert await fehler(api, "zuordnung/list", neu="ja") == "invalid_format"


async def test_zuordnung_set_behaelt_den_zeitstempel(api, bibliothek):
    k = bibliothek.store.konfig["zuordnungen"]
    k[UID] = {"ziel": {"typ": "serie", "serie": "rabe"}, "angelegt_am": "2026-11-01T10:00:00Z"}
    await ok(api, "zuordnung/set", uid=UID, ziel={"typ": "serie", "serie": "raeuber"}, ueberschreiben=True, name="Hase")
    assert bibliothek.store.konfig["zuordnungen"][UID] == {
        "ziel": {"typ": "serie", "serie": "raeuber"}, "name": "Hase", "angelegt_am": "2026-11-01T10:00:00Z",
    }


def test_pruefe_konfig_behaelt_angelegt_am_und_verwirft_ungueltiges():
    from custom_components.tobibox.store import neue_konfig, pruefe_konfig

    k = neue_konfig({UID: {"ziel": {"typ": "serie", "serie": "x"}, "angelegt_am": "2026-11-01T10:00:00Z"},
                     UID2: {"ziel": {"typ": "serie", "serie": "x"}, "angelegt_am": "gestern"}})
    k = pruefe_konfig({**k, "schema_version": 2})
    assert k["zuordnungen"][UID]["angelegt_am"] == "2026-11-01T10:00:00Z"
    assert "angelegt_am" not in k["zuordnungen"][UID2]


# --------------------------------------------------------------------------
# Fähigkeit
# --------------------------------------------------------------------------


async def test_hello_sagt_bibliothek_zu(api, normal):
    for client in (api, normal):
        f = (await ok(client, "hello", v=1))["faehigkeiten"]
        assert f[-2:] == ["konfig_staende", "bibliothek"]
        for spaeter in ("cover", "einsortier_wunsch", "reinhoeren", "hoerkopie"):
            assert spaeter not in f
    assert const.FAEHIGKEITEN[-1] == "bibliothek"


# --------------------------------------------------------------------------
# Leistung (Design 5.2 und V-2): 600 Einträge, 2 000 Folgen, dazu 300 Einzeltitel
# --------------------------------------------------------------------------

LEISTUNG_GRENZE_S = 0.2


async def test_leistung_600_eintraege_2000_folgen_300_einzeltitel(api, nas, integration):
    arten = ("hoerspiel", "hoerbuch", "musik", "geschichte")
    zeile = 0
    for i in range(600):
        folgen = [f"Folge {j:02d}.mp3" for j in range(1, (4 if i < 200 else 3) + 1)]  # 200 Einträge mit 4 Folgen, 400 mit 3: 2 000 Folgen
        lege_serie(nas, f"s{i:04d}", f"Hörspielreihe {i:04d} {'Räuber' if i % 7 == 0 else 'Mond'}", folgen, art=arten[i % 4], art_quelle="tags",
                   angelegt_am=iso(jetzt() - timedelta(days=i % 60)),
                   folgen_info={f: {"anzeige": f"Geschichte {i:04d}-{n} vom Fuchs {'und Hasen' if n % 2 else ''}"} for n, f in enumerate(folgen, 1)})
        zeile += len(folgen)
    assert zeile == 200 * 4 + 400 * 3 == 2000
    for i in range(300):
        lege_serie(nas, f"e{i:04d}", f"Lied Nummer {i:04d}", ["lied.mp3"], art="musik", art_quelle="tags", einzeln=True,
                   angelegt_am=iso(jetzt() - timedelta(days=i % 90)))
    await neu_pruefen(integration)
    assert len(integration.medien.serien) == 900
    # 300 Tobies, wie in einer gut gefüllten Bibliothek
    k = integration.store.konfig["zuordnungen"]
    for i in range(300):
        k[f"04{i:06x}"] = {"ziel": {"typ": "folge", "serie": f"s{i:04d}", "folge": "Folge 01.mp3"} if i % 2 else {"typ": "serie", "serie": f"s{i:04d}"}}

    def messe(befehl, **felder):
        async def lauf():
            t0 = time.perf_counter()
            antwort = await senden(api, befehl, **felder)
            return time.perf_counter() - t0, antwort

        return lauf

    # Kalt: der erste Aufruf baut den Index auf (900 Einträge, 2 300 Folgen)
    dauer, antwort = await messe("serien/list", text="räuber", limit=60)()
    assert antwort["success"] and antwort["result"]["gesamt"] == 86  # jeder siebte von 600: 0, 7, …, 595
    kalt = dauer
    messungen: dict[str, float] = {"serien/list Suche (kalt, mit Indexaufbau)": kalt}
    faelle = {
        "serien/list Suche": dict(text="räuber", limit=60),
        "serien/list Suche + Art + Filter": dict(text="mond", art="musik", filter=["ohne_tobie", "sammlung"], limit=60),
        "serien/list Suche in Folgen": dict(text="fuchs hasen", auch_folgen=True, limit=60),
        "serien/list Blättern": dict(limit=60, offset=600),
        "serien/list Sortierung neu": dict(sortierung="neu", filter=["neu"], limit=60),
        "serien/list Einzeltitel": dict(filter=["einzeln"], text="lied", limit=60),
    }
    for name, felder in faelle.items():
        beste = min([(await messe("serien/list", **felder)())[0] for _ in range(5)])
        messungen[name] = beste
    for name, felder in {
        "folgen/list Suche": dict(text="fuchs hasen", limit=60),
        "folgen/list Suche + Filter": dict(text="lied", filter=["einzeln", "ohne_tobie"], sortierung="neu", limit=100),
    }.items():
        beste = min([(await messe("folgen/list", **felder)())[0] for _ in range(5)])
        messungen[name] = beste
    for name, sekunden in messungen.items():
        print(f"LEISTUNG {name}: {sekunden * 1000:.1f} ms")
        assert sekunden < LEISTUNG_GRENZE_S, f"{name}: {sekunden * 1000:.0f} ms"
    # Einzeltitel stehen als Serie und als Folge im Index
    r = await ok(api, "serien/list", filter=["einzeln"], limit=1)
    assert r["gesamt"] == 300
    assert (await ok(api, "folgen/list", filter=["einzeln"], limit=1))["gesamt"] == 300
