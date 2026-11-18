"""Online-Suche, Abgleich (``online_abgleich.py``): reine Funktionen gegen die Fixtures aus OS1 (kein Netz).

Maßstab ist ``fixtures/online/erwartung.json`` (Spalte ``U``, Vereinigung „Serie im Künstler oder im Album“). Die Datei
ist älter als zwei Nachträge (Projektleitung 18.11.): „???“/„!!!“ in ``woerter`` und T4 (Hörspiel im Albumnamen).
Abweichungen von der Datei sind nur in :data:`AUSNAHMEN` erlaubt und dort begründet. ``erwartung.json`` und die
Fixtures werden nie verändert.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from custom_components.tobibox import online_abgleich as oa

FIX = Path(__file__).parent / "fixtures" / "online"
ERWARTUNG = json.loads((FIX / "erwartung.json").read_text(encoding="utf-8"))
FAELLE = ERWARTUNG["faelle"]

FELDER_EINTRAG = ("cover", "art")
FELDER_FOLGE = ("folge_titel", "nummer", "beschreibung", "alter_ab")

#: Abweichungen von ``erwartung.json``, die genau aus einem der zwei Nachträge folgen (Fall, Feld) -> alt/neu.
AUSNAHMEN: dict[tuple[str, str], dict[str, Any]] = {
    # T4 (Design 0a und 4.7, Tobias 18.11.): Das Hörbuch „Die Muppets (Hörspiel zum Kinofilm)“ trägt „Hörspiel“ im
    # Albumnamen; die Art ist deshalb `hoerspiel` statt `hoerbuch` (Status bleibt sicher).
    ("muppets", "art"): {
        "nachtrag": "T4",
        "alt": {"status": "sicher", "neu": "hoerbuch"},
        "neu": {"status": "sicher", "neu": "hoerspiel"},
    },
}


# --------------------------------------------------------------------------
# Eingaben aus den Fixtures
# --------------------------------------------------------------------------


def _json(pfad: Path) -> Any:
    return json.loads(pfad.read_text(encoding="utf-8"))


def _itunes(dateien: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in dateien:
        out.extend(_json(FIX / "itunes" / f"{d}.json")["results"])
    return out


def _sitemap_pfade() -> set[str]:
    xml = (FIX / "sitemap_auszug.xml").read_text(encoding="utf-8")
    return {re.sub(r"^https://tonies\.com", "", m) for m in re.findall(r"<loc>(.*?)</loc>", xml)}


def _shop_lesen(html: str) -> dict[str, Any] | None:
    """Test-Hilfe (kein Produktionscode): ``__NEXT_DATA__`` -> ``props.pageProps.product`` -> geprüfte Shop-Daten."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    produkt = json.loads(m.group(1))["props"]["pageProps"]["product"]  # type: ignore[union-attr]
    alter = produkt.get("ageMin")
    if isinstance(alter, str) and alter.strip().isdigit():
        alter = int(alter.strip())
    if isinstance(alter, bool) or not isinstance(alter, int) or not 0 <= alter <= 18:
        alter = None
    beschr = produkt.get("description")
    return {
        "salesId": produkt.get("salesId"),
        "beschreibung": oa.html_zu_text(beschr) if isinstance(beschr, str) else None,
        "alter_ab": alter,
    }


def _shop_daten() -> dict[str, Any]:
    """``{model: {...}}`` der echten (nicht künstlichen) Shopseiten; ``salesId`` muss gleich ``model`` sein."""
    out: dict[str, Any] = {}
    for f in sorted((FIX / "shop").glob("*.html")):
        if "kuenstlich" in f.name:
            continue
        d = _shop_lesen(f.read_text(encoding="utf-8"))
        assert d is not None
        model = f.name.split("_")[0]
        assert d["salesId"] == model
        out[model] = {"beschreibung": d["beschreibung"], "alter_ab": d["alter_ab"]}
    return out


@pytest.fixture(scope="module")
def tonies() -> list[dict[str, Any]]:
    return _json(FIX / "tonies_auszug.json")


@pytest.fixture(scope="module")
def tonie_index(tonies: list[dict[str, Any]]) -> dict[str, Any]:
    return oa.tonie_index_bauen(tonies)


@pytest.fixture(scope="module")
def sitemap() -> set[str]:
    return _sitemap_pfade()


@pytest.fixture(scope="module")
def shop() -> dict[str, Any]:
    return _shop_daten()


# --- Ergänzungen, wo die Fixtures für einen Fall unvollständig sind ------------------------------------------------
# Die Fälle wurden in OS1 mit dem **ganzen** Eintrag gemessen (mehrere Folgen) und mit allen Anfragen (auch Hörbuch-
# Suche, Stufe 2, Nachbarfolgen). ``itunes/`` enthält je Fall nur einen Teil. Das Fehlende liegt in
# ``ergaenzung_os2.json`` (Herkunft: README, Abschnitt „Ergänzung OS2“). Im Test erfunden sind nur neutrale Zusatzfolgen.

def _album(cid: int, name: str, kuenstler: str, genre: str, tracks: int, bild: str) -> dict[str, Any]:
    return {
        "wrapperType": "collection",
        "collectionId": cid,
        "collectionName": name,
        "artistName": kuenstler,
        "primaryGenreName": genre,
        "trackCount": tracks,
        "artworkUrl100": bild,
    }


def _buch(cid: int, name: str, kuenstler: str, bild: str, beschreibung: str) -> dict[str, Any]:
    return {
        "wrapperType": "audiobook",
        "collectionId": cid,
        "collectionName": name,
        "artistName": kuenstler,
        "primaryGenreName": "Kinder und Jugend",
        "trackCount": 1,
        "artworkUrl100": bild,
        "description": beschreibung,
    }


ERGAENZUNG = _json(FIX / "ergaenzung_os2.json")


def _fall_aufbauen(fall: str, v: dict[str, Any], tonies: list[dict[str, Any]]) -> tuple[dict[str, Any], list[Any], int, dict[str, Any]]:
    """``(eintrag, apple_ergebnisse, index_der_geprueften_folge, tonie_index)`` für einen Fall."""
    res = _itunes(v["itunes_dateien"])
    folge = {"anzeige": v["folge"], "nummer": v["heutige_nummer"], "tracks": v["unsere_tracks"], "art": "ordner"}
    folgen = [folge]
    ergebnisse: list[Any] = [res]
    pos = 0
    tonies = list(tonies)
    if fall == "hotzenplotz":
        res += ERGAENZUNG["hotzenplotz"]["kuenstliche_alben"] + ERGAENZUNG["hotzenplotz"]["hoerbuch_antwort"]
    elif fall == "olchis_geburtstagsreise":
        # der Eintrag hat drei Folgen; die Antworten der anderen zwei liegen nicht bei: nichts gefunden
        folgen += [
            {"anzeige": "Weitere Folge A", "nummer": None, "tracks": 8, "art": "ordner"},
            {"anzeige": "Weitere Folge B", "nummer": None, "tracks": 8, "art": "ordner"},
        ]
        ergebnisse += [[], []]
    elif fall == "fuenf_freunde_121":
        # Das Cover des Eintrags kommt von der ersten Folge (122), deren Album nicht in itunes/ liegt
        e = ERGAENZUNG["fuenf_freunde_121"]
        folgen = [{"anzeige": e["andere_folge_anzeige"], "nummer": None, "tracks": e["andere_folge_tracks"], "art": "ordner"}, folge]
        ergebnisse = [e["album_andere_folge"], res]
        pos = 1
    elif fall == "toy_story_2":
        # zwei Folgen; die Hörbuch-Antwort und der Tonie „Folge 1 & 2“ (unsichere Nummer 1) fehlen in den Fixtures
        folgen.append({"anzeige": "Weitere Folge", "nummer": None, "tracks": 6, "art": "ordner"})
        res += ERGAENZUNG["toy_story_2"]["hoerbuch_antwort"]
        ergebnisse.append([])
        tonies.append(ERGAENZUNG["toy_story_2"]["tonie"])
    eintrag = {
        "name": v["eintrag"],
        "einzeln": False,
        "cover_quelle": v["cover_heute"],
        "art_quelle": re.search(r"\((.*)\)", v["art_heute"]).group(1),  # type: ignore[union-attr]
        "folgen": folgen,
    }
    return eintrag, ergebnisse, pos, oa.tonie_index_bauen(tonies)


def _bewerten(fall: str, tonies: list[dict[str, Any]], sitemap: set[str], shop: dict[str, Any]) -> tuple[dict[str, Any], int]:
    v = FAELLE[fall]
    eintrag, ergebnisse, pos, index = _fall_aufbauen(fall, v, tonies)
    return oa.bewerte_eintrag(eintrag, index, ergebnisse, shop, sitemap), pos


# --------------------------------------------------------------------------
# Fälle aus erwartung.json (Spalte U)
# --------------------------------------------------------------------------


def _ist_und_soll(fall: str, feld: str, ergebnis: dict[str, Any], pos: int) -> tuple[dict[str, Any], dict[str, Any]]:
    f = ergebnis[feld] if feld in FELDER_EINTRAG else ergebnis["folgen"][pos][feld]
    ist = {"status": f["status"], "neu": f["neu"]}
    soll = FAELLE[fall]["felder_nach_regel"][feld]["U"]
    return ist, {"status": soll["status"], "neu": soll["neu"]}


@pytest.mark.parametrize("fall", list(FAELLE))
@pytest.mark.parametrize("feld", FELDER_EINTRAG + FELDER_FOLGE)
def test_fall_gegen_erwartung(fall, feld, tonies, sitemap, shop):
    ergebnis, pos = _bewerten(fall, tonies, sitemap, shop)
    ist, soll = _ist_und_soll(fall, feld, ergebnis, pos)
    if (fall, feld) in AUSNAHMEN:
        ausnahme = AUSNAHMEN[(fall, feld)]
        assert soll == ausnahme["alt"], "erwartung.json hat sich geändert, die Ausnahme passt nicht mehr"
        assert ist == ausnahme["neu"]
    else:
        assert ist == soll


def test_ausnahmen_nur_aus_den_zwei_nachtraegen():
    assert {a["nachtrag"] for a in AUSNAHMEN.values()} <= {"T4", "woerter"}
    assert set(AUSNAHMEN) == {("muppets", "art")}


@pytest.mark.parametrize("fall", list(FAELLE))
def test_beschreibung_und_alter_nie_unsicher(fall, tonies, sitemap, shop):
    ergebnis, _ = _bewerten(fall, tonies, sitemap, shop)
    for f in ergebnis["folgen"]:
        assert f["beschreibung"]["status"] in ("sicher", "keiner", "nicht_geholt")
        assert f["alter_ab"]["status"] in ("sicher", "keiner", "nicht_geholt")


def test_eigenes_cover_und_art_schutz_markiert(tonies, sitemap, shop):
    # Mulan: eigenes Cover (wird nie ersetzt, der Status bleibt trotzdem sicher: Urteil von Tobias, T3)
    mulan, _ = _bewerten("mulan", tonies, sitemap, shop)
    assert mulan["cover"]["status"] == "sicher" and mulan["cover"]["geschuetzt"] is True
    assert mulan["cover"]["collection_id"] is not None
    # Fünf Freunde: Art ist von Hand gesetzt (`manuell`), nur „geraten“ darf sich ändern
    fuenf, _ = _bewerten("fuenf_freunde_121", tonies, sitemap, shop)
    assert fuenf["art"]["geschuetzt"] is True
    assert fuenf["cover"]["geschuetzt"] is False
    bibi, _ = _bewerten("bibi_folge100", tonies, sitemap, shop)
    assert bibi["art"]["geschuetzt"] is False


def test_bibi_shop_fehlt_ist_nicht_geholt_aber_ungueltige_seite_ist_keiner(tonies, sitemap, shop):
    v = FAELLE["bibi_folge100"]
    eintrag, ergebnisse, _, index = _fall_aufbauen("bibi_folge100", v, tonies)
    # Seite noch nicht geholt: das Modell fehlt in den Shop-Daten. Das Hörbuch hat keine Beschreibung (200-Zeichen-Auszug
    # steht in der Datei), die Beschreibung des Hörbuchs zählt hier aber nicht, weil mehrere ``collectionId`` passen.
    ohne = oa.bewerte_eintrag(eintrag, index, ergebnisse, {}, sitemap)["folgen"][0]
    assert ohne["alter_ab"]["status"] == "nicht_geholt"
    # Seite geholt, aber unbrauchbar (z. B. falsche ``salesId``): endgültig keiner
    kaputt = oa.bewerte_eintrag(eintrag, index, ergebnisse, {"01-0030": None}, sitemap)["folgen"][0]
    assert kaputt["alter_ab"]["status"] == "keiner"
    # Seite ohne Felder: kein Alter; die Beschreibung fällt auf das Hörbuch zurück (wie ohne Shop)
    leer = oa.bewerte_eintrag(eintrag, index, ergebnisse, {"01-0030": {"beschreibung": None, "alter_ab": None}}, sitemap)["folgen"][0]
    assert leer["alter_ab"]["status"] == "keiner"
    # Ohne Sitemap kennt der Abgleich keine Seite: kein „nicht geholt“ ...
    keine_sitemap = oa.bewerte_eintrag(eintrag, index, ergebnisse, {}, None)["folgen"][0]
    assert keine_sitemap["alter_ab"]["status"] == "keiner"
    assert keine_sitemap["shop_pfade"] == []
    # ... aber vorhandene Shop-Daten zum Tonie-Kandidaten zählen trotzdem
    mit_daten = oa.bewerte_eintrag(eintrag, index, ergebnisse, shop, None)["folgen"][0]
    assert mit_daten["alter_ab"]["neu"] == 4 and mit_daten["beschreibung"]["quelle"]["typ"] == "tonies_shop"
    assert ohne["shop_pfade"] == ["/de-de/tonies/bibi-blocksberg/die-grosse-hexenparty/"]


def test_alter_als_text_und_falsche_werte(shop):
    # künstliche Seiten: ``ageMin`` als Text wird zur Zahl (Test-Hilfe), ``alter_ab`` außerhalb 0..18 oder Text verworfen
    html = (FIX / "shop" / "01-0030_alter_als_text_kuenstlich.html").read_text(encoding="utf-8")
    assert _shop_lesen(html)["alter_ab"] == 4  # type: ignore[index]
    d = _shop_lesen((FIX / "shop" / "01-0030_ohne_felder_kuenstlich.html").read_text(encoding="utf-8"))
    assert d["beschreibung"] is None and d["alter_ab"] is None  # type: ignore[index]
    # das Modul prüft den Wert noch einmal
    ctx_eintrag = {
        "name": "Bibi Blocksberg",
        "folgen": [{"anzeige": "Folge 100: Die große Hexenparty", "nummer": 100, "tracks": 13}],
    }
    idx = oa.tonie_index_bauen(_json(FIX / "tonies_auszug.json"))
    res = [_itunes(["bibi_folge100_album_mit_jubilaeum", "bibi_folge100_buch"])]
    for roh, erwartet in ((4, 4), (19, None), (-1, None), (True, None), ("4", None)):
        f = oa.bewerte_eintrag(ctx_eintrag, idx, res, {"01-0030": {"beschreibung": "Text", "alter_ab": roh}}, _sitemap_pfade())["folgen"][0]
        assert f["alter_ab"]["neu"] == erwartet
        assert f["beschreibung"] == {"status": "sicher", "neu": "Text", "quelle": {"typ": "tonies_shop", "model": "01-0030"}}


# --------------------------------------------------------------------------
# Wörter (4.1)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "erwartet"),
    [
        ("Der Räuber Hotzenplotz", ["raeuber", "hotzenplotz"]),
        ("Die Olchis und der schwarze Pirat", ["olchis", "schwarze", "pirat"]),  # Füllwörter fallen weg
        ("Das Hörspiel Folge 3 Teil Band Original ungekürzt Vol Volume", ["3"]),  # Allerweltswörter fallen weg
        ("Straße", ["strasse"]),
        ("Café Pokémon", ["cafe", "pokemon"]),  # Akzente weg
        ("Bibi & Tina", ["bibi", "tina"]),
        ("Bibi und Tina", ["bibi", "tina"]),
        ("Ein a b 7 c", ["7"]),  # einzelne Buchstaben fallen weg, einzelne Ziffern bleiben
        ("Peppa Pig Hörspiele", ["peppa", "pig"]),
        ("Die drei ???", ["drei", "fragezeichen"]),
        ("Die drei !!!", ["drei", "ausrufezeichen"]),
        ("Die drei ??????", ["drei", "fragezeichen"]),  # drei oder mehr
        ("Was?? Oh!", ["was", "oh"]),  # zwei Zeichen bleiben Satzzeichen
        ("Die drei ??? Kids", ["drei", "fragezeichen", "kids"]),
        ("", []),
    ],
)
def test_woerter(text, erwartet):
    assert oa.woerter(text) == erwartet


def test_drei_fragezeichen_ungleich_drei_ausrufezeichen():
    assert oa.woerter("Die drei ???") != oa.woerter("Die drei !!!")
    assert oa.serie_aehnlichkeit("Die drei ???", "Die drei !!!") < oa.SERIE_STUETZE_MIN


def test_woerter_nimmt_nur_text():
    assert oa.woerter(None) == []  # type: ignore[arg-type]
    assert oa.norm(None) == ""


# --------------------------------------------------------------------------
# Nummer abtrennen (4.1, „Muster für Nummern“)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "erwartet"),
    [
        ("Folge 12: Der Rabe", (12, "Der Rabe")),
        ("folge 12 - Der Rabe", (12, "Der Rabe")),
        ("Folge 12. Der Rabe", (12, "Der Rabe")),
        ("Teil 2 Der Rabe", (2, "Der Rabe")),
        ("Band 3: Die Burg", (3, "Die Burg")),
        ("Episode 5: Die Burg", (5, "Die Burg")),
        ("Nr. 4 Die Burg", (4, "Die Burg")),
        ("Vol. 2: Die Burg", (2, "Die Burg")),
        ("Band 3", (3, "")),
        ("12: Der Rabe", (12, "Der Rabe")),
        ("12. Der Rabe", (12, "Der Rabe")),
        ("Teil 1: Geheimnisvolle Verwandlung", (1, "Geheimnisvolle Verwandlung")),
        ("Der Rabe", (None, "Der Rabe")),
        ("Der 3. Mann", (None, "Der 3. Mann")),  # andere Zahlen bleiben
        ("Toy Story 2", (None, "Toy Story 2")),
        ("12.Der Rabe", (None, "12.Der Rabe")),  # nach „N.“ muss ein Leerzeichen folgen
        ("Folge 12345: Der Rabe", (None, "Folge 12345: Der Rabe")),  # höchstens vier Ziffern
        ("Titel – Teil 1", (None, "Titel – Teil 1")),  # es muss ein Rest folgen
        ("Hexenball - Folge 3", (None, "Hexenball - Folge 3")),
        ("", (None, "")),
    ],
)
def test_nummer_abtrennen(text, erwartet):
    assert oa.nummer_abtrennen(text) == erwartet


def test_nummer_abtrennen_mit_praefix():
    sw = oa.woerter("Bibi Blocksberg")
    # Text nur aus Serienwörtern fällt weg
    assert oa.nummer_abtrennen("Bibi Blocksberg, Folge 89: Die Junghexenbande", sw) == (89, "Die Junghexenbande")
    assert oa.nummer_abtrennen("Bibi Blocksberg - Folge 89: Die Junghexenbande", sw) == (89, "Die Junghexenbande")
    assert oa.nummer_abtrennen("Bibi Blocksberg: Teil 7 Die Hexe", sw) == (7, "Die Hexe")
    # sonst bleibt der Text im Titel
    assert oa.nummer_abtrennen("Gute-Nacht-Geschichten, Folge 15: Der Mond", sw) == (15, "Gute-Nacht-Geschichten Der Mond")
    assert oa.nummer_abtrennen("Gute-Nacht-Geschichten, Folge 15: Der Mond") == (15, "Gute-Nacht-Geschichten Der Mond")
    # Text länger als 60 Zeichen: kein Präfix
    lang = "x" * 70 + ", Folge 3: Rest"
    assert oa.nummer_abtrennen(lang) == (None, lang)


def test_klammerregel_beim_titelvergleich():
    sw = oa.woerter("Bibi Blocksberg")
    # Klammerzusätze ohne Ziffer fallen weg ...
    assert oa.titel_gleich("Ausgehext! (Das Original-Hörspiel zur TV-Serie)", "Ausgehext!", sw)
    assert oa.titel_gleich("Ausgehext!", "Ausgehext! [Hörspiel]", sw)
    # ... mit Ziffer bleiben sie, dann gibt es keinen Treffer
    assert not oa.titel_gleich("Ausgehext! (Teil 2)", "Ausgehext!", sw)
    assert not oa.titel_gleich("Ausgehext! (Neuauflage 2025)", "Ausgehext!", sw)
    assert oa.klammern_ohne_zahl_weg("Titel (Teil 2) (Hörspiel)") == "Titel (Teil 2)"


def test_titel_gleich_serienwoerter_abziehen():
    sw = oa.woerter("Fünf Freunde")
    assert oa.titel_gleich("Folge 121: Fünf Freunde und die verlassene Jagdhütte", "Folge 121: und die verlassene Jagdhütte", sw)
    # Titel gleich Serienname bleibt vergleichbar (volle Wörter)
    sw2 = oa.woerter("Der Räuber Hotzenplotz")
    assert oa.titel_gleich("Der Räuber Hotzenplotz", "1: Der Räuber Hotzenplotz", sw2)
    assert not oa.titel_gleich("Der Räuber Hotzenplotz", "Neues vom Räuber Hotzenplotz", sw2)
    # nur Wörter des Seriennamens und sonst nichts: leere Liste zählt nie als gleich
    assert not oa.titel_gleich("Folge 3", "Folge 4", [])


def test_aehnlichkeit_difflib():
    sw: list[str] = []
    assert oa.aehnlichkeit("Der Rabe", "Der Rabe", sw) == 1.0
    assert oa.aehnlichkeit("Der Rabe", "", sw) == 0.0
    a = oa.aehnlichkeit("Die verlassene Jagdhütte", "Die verlassene Jagdhutte", sw)
    assert 0.9 < a < 1.0


# --------------------------------------------------------------------------
# Platzhalter (4.5)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("titel", ["", "   ", "Track 01", "track_3", "Titel-12", "Kapitel 12", "Chapter 7", "Spur.04", "Audio 9", "Datei 2", "File 5", "Folge 3", "Teil 2", "7", "123"])
def test_platzhalter(titel):
    assert oa.ist_platzhalter(titel)


@pytest.mark.parametrize("titel", ["Der Rabe", "Der Rabe.mp3", "Folge 3: Der Rabe", "Kapitel 1000", "Track", "1234", "Track 01 Intro", "Die 7 Zwerge"])
def test_kein_platzhalter(titel):
    assert not oa.ist_platzhalter(titel)


def test_platzhalter_muster_mit_endung():
    # Das dritte Muster steht so in os1_regeln.md und regeln.py („Track 01.mp3“ ist Platzhalter); echte Dateinamen
    # („Der Rabe.mp3“) sind keine (siehe oben). Die Regeldatei sagt zugleich „Dateinamen mit Endung sind kein
    # Platzhalter“ (Widerspruch im Text, im Bericht gemeldet).
    assert oa.ist_platzhalter("track01.mp3")
    assert oa.ist_platzhalter("Titel 3.m4a")
    assert not oa.ist_platzhalter("Mein Lied.mp3")


# --------------------------------------------------------------------------
# Ausschluss bei Apple-Alben (4.3)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "tracks", "folge_tracks", "grund"),
    [
        ("Der Hexenball Box", 14, 14, "wort:box"),
        ("Der Hexenball - Sammlung", 14, 14, "wort:sammlung"),
        ("Hexenball Collection", 14, 14, "wort:collection"),
        ("Hexenball Soundtrack", 14, 14, "wort:soundtrack"),
        ("Ich hex für dich! Jubiläumsedition 1", 26, 14, "wort:jubilaeum"),  # Wortteil
        ("Limitededition", 14, 14, "wort:edition"),
        ("Komplettausgabe", 14, 14, "wort:komplett"),
        ("Der Film", 10, 10, "wort:film"),  # ganzes Wort
        ("Im Kino", 10, 10, "wort:kino"),
        ("Alle Hörspiele", 10, 10, "wort:alle"),
        ("Best of Bibi", 10, 10, "wort:best"),
        ("Das Musical", 10, 10, "wort:musical"),
        ("Der Räuber Hotzenplotz - Single", 1, 4, "wort:single"),
        ("Bundle", 5, 5, "wort:bundle"),
        ("Der Hexenball / Die große Hexenparty", 20, 14, "zeichen:/"),
        ("Der Rabe", 45, 4, "tracks:45"),  # mehr als 40 und mehr als das Doppelte
        ("Der Rabe", 41, 0, "tracks:41"),  # Folgen-Trackzahl zählt mindestens 1
    ],
)
def test_ausschluss_gruende(name, tracks, folge_tracks, grund):
    assert oa.apple_ausschluss(name, tracks, folge_tracks) == grund


@pytest.mark.parametrize(
    ("name", "tracks", "folge_tracks"),
    [
        ("Mulan (Hörspiel zum Kinofilm)", 12, 6),  # „Kinofilm“ ist kein ganzes Wort „kino“ oder „film“ (T3)
        ("Der Boxer", 10, 10),  # Wortteil von „box“ zählt nicht
        ("Bestseller", 10, 10),
        ("Der Rabe", 40, 4),  # genau 40: nicht mehr als 40
        ("Der Rabe", 45, 30),  # mehr als 40, aber nicht mehr als das Doppelte
        ("Der Rabe", 60, 30),  # genau das Doppelte: nicht mehr als das Doppelte
        ("Der Rabe", None, 4),
    ],
)
def test_ausschluss_nicht(name, tracks, folge_tracks):
    assert oa.apple_ausschluss(name, tracks, folge_tracks) is None


# --------------------------------------------------------------------------
# Sprachmerkmale und Tonie-Liste (3.1)
# --------------------------------------------------------------------------


def _tonie(**kw: Any) -> dict[str, Any]:
    basis = {
        "model": "01-0001",
        "series": "Bibi Blocksberg",
        "episodes": "Ausgehext!",
        "tracks": ["a", "b"],
        "category": "audio-play",
        "language": "de-de",
    }
    basis.update(kw)
    return basis


def test_tonie_benutzbar_normal():
    assert oa.tonie_benutzbar(_tonie())
    assert oa.tonie_benutzbar(_tonie(tracks=[]))
    assert oa.tonie_benutzbar(_tonie(tracks=5))  # schon eine Zahl
    assert oa.tonie_benutzbar(_tonie(tracks=None, episodes=None))
    assert oa.tonie_benutzbar(_tonie(title=["Bibi Blocksberg", "Ausgehext!"]))  # Original: ``title`` als Liste
    assert oa.tonie_benutzbar(_tonie(title="Bibi Blocksberg - Ausgehext!"))


@pytest.mark.parametrize(
    "aenderung",
    [
        {"language": "pl-pl"},
        {"language": None},
        {"language": "DE-DE"},
        {"model": ""},
        {"model": None},
        {"model": 12345},
        {"series": "Świnka Peppa"},  # polnisch
        {"episodes": "Pipsa Possu ja ystävät"},  # finnisch
        {"episodes": "Il Nuovo Trenino"},  # italienisch
        {"series": "Peppa Pig", "episodes": "Una casa nuova"},  # italienisch: „nuova“
    ],
)
def test_tonie_nicht_benutzbar(aenderung):
    assert not oa.tonie_benutzbar(_tonie(**aenderung))


@pytest.mark.parametrize("zeichen", list("¡¿ñąćęğıłńśşźż"))
def test_fremde_zeichen(zeichen):
    assert not oa.tonie_benutzbar(_tonie(episodes=f"Titel {zeichen} Text"))
    assert not oa.tonie_benutzbar(_tonie(title=[f"Titel {zeichen}"]))  # auch im Titel (Liste)


@pytest.mark.parametrize("wort", sorted(oa.FREMDWOERTER))
def test_fremde_woerter_ganze_woerter(wort):
    assert not oa.tonie_benutzbar(_tonie(episodes=f"Ein {wort.upper()} Abenteuer"))
    # als Wortteil bleibt der Eintrag benutzbar
    assert oa.tonie_benutzbar(_tonie(episodes=f"Ein {wort}xyz Abenteuer"))


@pytest.mark.parametrize("episodes", ["Café Royal", "Pokémon Abenteuer", "Los geht's", "Der Räuber Hotzenplotz", "Die Olchis"])
def test_deutsche_titel_bleiben_benutzbar(episodes):
    assert oa.tonie_benutzbar(_tonie(episodes=episodes))


@pytest.mark.parametrize("roh", [None, 5, "text", [], [1, 2], {}, {"model": "x"}, _tonie(series=5), _tonie(episodes=["a"]), _tonie(title=5),
                                 _tonie(tracks="abc"), _tonie(tracks=-1), _tonie(tracks=True), _tonie(tracks={"a": 1})])
def test_tonie_benutzbar_nie_ausnahme(roh):
    assert oa.tonie_benutzbar(roh) is False


def test_tonie_index_ueberspringt_muell(tonies):
    index = oa.tonie_index_bauen([None, 5, {}, _tonie(language="fi-fi"), _tonie(model="x", tracks="abc"), _tonie()])
    assert [e["model"] for e in index["eintraege"]] == ["01-0001"]
    # der Auszug der Fixtures: 47 Einträge, davon bleiben die benutzbaren
    voll = oa.tonie_index_bauen(tonies)
    assert 0 < len(voll["eintraege"]) < len(tonies)
    assert all(oa.tonie_benutzbar(t) for t in tonies if t["model"] in {e["model"] for e in voll["eintraege"]})


def test_tonie_index_tracks_zahl():
    e = oa.tonie_index_bauen([_tonie(tracks=["a", "b", "c"]), _tonie(model="x", tracks=7), _tonie(model="y", tracks=[])])["eintraege"]
    assert [x["tracks"] for x in e] == [3, 7, 0]


# --------------------------------------------------------------------------
# Tonie-Kategorien und Treffer (4.2, 4.7)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kategorie", "erwartet"),
    [
        ("audio-play", ("hoerspiel", True)),
        ("audio-play-educational", ("hoerspiel", True)),
        ("audio-book", ("hoerbuch", True)),
        ("music", ("musik", True)),
        ("Musik", ("musik", True)),
        ("audio-play-songs", ("musik", False)),  # höchstens unsicher
        ("audio-book-songs", ("musik", False)),
        ("creative-tonie", (None, False)),
        ("Hörspiele & Hörbücher", (None, False)),
        ("system", (None, False)),
        ("Wissen", (None, False)),
        ("JAKO-O", (None, False)),
        ("Tonie", (None, False)),
        ("", (None, False)),
        (None, (None, False)),
        (5, (None, False)),
    ],
)
def test_tonie_kategorie(kategorie, erwartet):
    assert oa.tonie_art(kategorie) == erwartet


def _ctx(serie: str, anzeige: str, tracks: int = 1, nummer: int | None = None) -> dict[str, Any]:
    return oa.folge_kontext(serie, {"anzeige": anzeige, "tracks": tracks, "nummer": nummer})


def test_tonie_dubletten_gleich_bleibt_sicher(tonie_index):
    # Hotzenplotz: 01-0033 (Tracks unbekannt) und 10000693 (4 Tracks)
    tp = oa.tonie_pruefen(_ctx("Der Räuber Hotzenplotz", "Der Räuber Hotzenplotz", 4), tonie_index)
    assert tp["status"] == "sicher"
    assert {e["model"] for e in tp["sichere"]} == {"01-0033", "10000693"}
    assert any(f.startswith("dubletten:") for f in tp["flags"])
    # Shopseite bei Dubletten: nur der Kandidat mit gleicher Trackzahl (größer 0)
    assert {e["model"] for e in tp["shop_kandidaten"]} == {"10000693"}
    # Bibi „Ausgehext!“: beide Kandidaten haben 14 Tracks
    tp = oa.tonie_pruefen(_ctx("Bibi Blocksberg", "Ausgehext!", 14), tonie_index)
    assert tp["status"] == "sicher"
    assert {e["model"] for e in tp["sichere"]} == {"11002078", "2000000144"}
    assert {e["model"] for e in tp["shop_kandidaten"]} == {"11002078", "2000000144"}


def test_tonie_eine_datei_gegen_drei_tracks_nie_sicher(tonie_index):
    # „Eine Datei bei uns, drei und mehr Tracks beim Tonie“: der Tonie mit 4 Tracks ist nicht sicher
    tp = oa.tonie_pruefen(_ctx("Der Räuber Hotzenplotz", "Der Räuber Hotzenplotz", 1), tonie_index)
    assert {e["model"] for e in tp["sichere"]} == {"01-0033"}  # Tracks unbekannt passt
    assert {e["model"] for e in tp["shop_kandidaten"]} == {"01-0033"}  # ein einzelner sicherer zählt immer
    assert "10000693" in {e["model"] for e in tp["unsichere"]}  # Titel gleich, andere Trackzahl: unsicher


def test_tonie_dubletten_mit_widerspruch_ergibt_keiner():
    a = _tonie(model="A1", series="Die Serie", episodes="Der Rabe", category="audio-play", tracks=["x"] * 3)
    b = _tonie(model="B1", series="Die Serie", episodes="Der Rabe", category="audio-book", tracks=["x"] * 3)
    tp = oa.tonie_pruefen(_ctx("Die Serie", "Der Rabe", 3), oa.tonie_index_bauen([a, b]))
    assert tp["status"] == "keiner" and "dublette_widerspruch" in tp["flags"]
    assert tp["art"] is None and tp["shop_kandidaten"] == []
    # Widerspruch in der Nummer
    c = _tonie(model="C1", series="Die Serie", episodes="Folge 4: Der Rabe", tracks=["x"] * 3)
    d = _tonie(model="D1", series="Die Serie", episodes="Folge 5: Der Rabe", tracks=["x"] * 3)
    tp = oa.tonie_pruefen(_ctx("Die Serie", "Der Rabe", 3), oa.tonie_index_bauen([c, d]))
    assert tp["status"] == "keiner" and "dublette_widerspruch" in tp["flags"]
    # nur Kandidaten mit einem Wert zählen: einer ohne Nummer widerspricht nicht
    e = _tonie(model="E1", series="Die Serie", episodes="Der Rabe", tracks=["x"] * 3)
    tp = oa.tonie_pruefen(_ctx("Die Serie", "Der Rabe", 3), oa.tonie_index_bauen([c, e]))
    assert tp["status"] == "sicher" and tp["nummer"] == 4 and tp["art"] == "hoerspiel"


def test_tonie_sprachkurs_reihe_nie_sicher():
    kurs = _tonie(model="K1", series="Bibi Blocksberg - Englisch lernen", episodes="Ausgehext!", tracks=["x"] * 14)
    plain = oa.tonie_pruefen(_ctx("Bibi Blocksberg - Englisch lernen", "Ausgehext!", 14), oa.tonie_index_bauen([kurs]))
    # Serie gleich, Titel gleich, Trackzahl gleich: trotzdem höchstens unsicher
    assert plain["status"] == "unsicher" and plain["sichere"] == []
    assert oa.ist_zusatzreihe("English for Kids") and oa.ist_zusatzreihe("Deutsch lernen mit Bibi")
    assert not oa.ist_zusatzreihe("Bibi Blocksberg")
    # und die normale Reihe daneben bleibt sicher
    normal = _tonie(model="K2", series="Bibi Blocksberg", episodes="Ausgehext!", tracks=["x"] * 14)
    tp = oa.tonie_pruefen(_ctx("Bibi Blocksberg", "Ausgehext!", 14), oa.tonie_index_bauen([kurs, normal]))
    assert tp["status"] == "sicher" and {e["model"] for e in tp["sichere"]} == {"K2"}


def test_tonie_serie_nicht_gestuetzt_ist_unsicher(tonie_index):
    # Toy Story 2 gibt es nur unter „Disney“: Titel gleich, Serie nicht gestützt
    tp = oa.tonie_pruefen(_ctx("Toy Story", "Toy Story 2", 4), tonie_index)
    assert tp["status"] == "unsicher"
    assert tp["art"] == "hoerspiel"


def test_tonie_nummer_aus_episodes():
    t = _tonie(model="N1", series="Sternenschweif", episodes="Teil 7: Der Zauber", tracks=["x"] * 5)
    tp = oa.tonie_pruefen(_ctx("Sternenschweif", "Der Zauber", 5), oa.tonie_index_bauen([t]))
    assert tp["status"] == "sicher" and tp["nummer"] == 7


def test_tonie_aehnlichkeit_92_prozent_unsicher():
    t = _tonie(model="S1", series="Die Serie", episodes="Die verlassene Jagdhuette am Meer", tracks=["x"] * 4)
    ctx = _ctx("Die Serie", "Die verlassene Jagdhutte am Meer", 4)
    tp = oa.tonie_pruefen(ctx, oa.tonie_index_bauen([t]))
    assert tp["status"] == "unsicher"
    # andere Trackzahl: bei bloßer Ähnlichkeit kein Treffer
    tp = oa.tonie_pruefen(_ctx("Die Serie", "Die verlassene Jagdhutte am Meer", 9), oa.tonie_index_bauen([t]))
    assert tp["status"] == "keiner"


# --------------------------------------------------------------------------
# Shopseiten in der Sitemap (3.2, 2.12)
# --------------------------------------------------------------------------


def test_slug():
    assert oa.slug("Die große Hexenparty!") == "die-grosse-hexenparty"
    assert oa.slug("Fünf Freunde & Co.") == "fuenf-freunde-co"
    assert oa.slug("") == ""


def test_shop_pfade_genau_und_als_endung():
    tonie = {"series": "Bibi Blocksberg", "episodes": "Die große Hexenparty", "ep_rest": "Die große Hexenparty"}
    genau = {"/de-de/tonies/bibi-blocksberg/die-grosse-hexenparty/", "/de-de/tonies/bibi-blocksberg/anderes/"}
    assert oa.shop_pfade(tonie, genau) == ["/de-de/tonies/bibi-blocksberg/die-grosse-hexenparty/"]
    # als Endung, wenn es keinen genauen Pfad gibt
    endung = {"/de-de/tonies/bibi-blocksberg/folge-100-die-grosse-hexenparty/", "/de-de/tonies/anderes/die-grosse-hexenparty/"}
    assert oa.shop_pfade(tonie, endung) == ["/de-de/tonies/bibi-blocksberg/folge-100-die-grosse-hexenparty/"]
    # episodes mit Nummer, Seite ohne Nummer
    mit_nr = {"series": "Bibi Blocksberg", "episodes": "Folge 100: Die große Hexenparty", "ep_rest": "Die große Hexenparty"}
    assert oa.shop_pfade(mit_nr, genau) == ["/de-de/tonies/bibi-blocksberg/die-grosse-hexenparty/"]
    assert oa.shop_pfade(tonie, set()) == []


def test_shop_pfade_hoechstens_zwei():
    tonie = {"series": "Serie", "episodes": "Titel", "ep_rest": "Titel"}
    viele = {f"/de-de/tonies/serie/{i}-titel/" for i in range(5)}
    assert len(oa.shop_pfade(tonie, viele)) == oa.SHOP_SEITEN_MAX == 2


def test_shop_pfade_aus_der_fixture_sitemap(tonie_index, sitemap):
    bibi = next(e for e in tonie_index["eintraege"] if e["model"] == "01-0030")
    assert oa.shop_pfade(bibi, sitemap) == ["/de-de/tonies/bibi-blocksberg/die-grosse-hexenparty/"]


# --------------------------------------------------------------------------
# Apple: Suchwörter, Treffer, Nummer (T2)
# --------------------------------------------------------------------------


def test_apple_suchwoerter():
    # Serienwörter schon im Titel: nicht doppeln; Nummer weg
    ctx = _ctx("Fünf Freunde", "Folge 121: Fünf Freunde und die verlassene Jagdhütte")
    assert oa.apple_suchwoerter(ctx) == ("Fünf Freunde und die verlassene Jagdhütte", "Fünf Freunde")
    # sonst Serienname + Titel; Klammerzusätze weg
    ctx = _ctx("Bibi Blocksberg", "Ausgehext! (Das Original-Hörspiel)")
    assert oa.apple_suchwoerter(ctx) == ("Bibi Blocksberg Ausgehext!", "Bibi Blocksberg")
    # Platzhalter-Titel und Titel gleich Serienname gehen gleich zu Stufe 2
    assert oa.apple_suchwoerter(_ctx("Benjamin Blümchen", "Track 01")) == (None, "Benjamin Blümchen")
    assert oa.apple_suchwoerter(_ctx("Der Räuber Hotzenplotz", "Der Räuber Hotzenplotz")) == (None, "Der Räuber Hotzenplotz")
    assert oa.apple_suchwoerter(_ctx("Benjamin Blümchen", "")) == (None, "Benjamin Blümchen")
    # höchstens 100 Zeichen (am Wortende)
    lang = oa.apple_suchwoerter(_ctx("Bibi", "Wort " * 40))[0]
    assert lang is not None and len(lang) <= 100 and not lang.endswith(" ")


def test_apple_stufe2_nur_wenn_stufe1_ohne_treffer():
    ctx = _ctx("Fünf Freunde", "Folge 121: Fünf Freunde und die verlassene Jagdhütte", 40)
    treffer = _itunes(["fuenf_freunde_121_album_gekuerzter_titel"])
    assert oa.apple_hat_treffer(ctx, treffer)
    assert not oa.apple_hat_treffer(ctx, [])
    assert not oa.apple_hat_treffer(_ctx("Die Olchis", "Die Olchis auf Geburtstagsreise", 9), _itunes(["olchis_geburtstagsreise_album_ohne_treffer"]))


def test_apple_entdoppeln():
    a = {"wrapperType": "collection", "collectionId": 1}
    b = {"wrapperType": "audiobook", "collectionId": 1}
    assert oa.apple_entdoppeln([a, dict(a), b, "kein dict", None]) == [a, b]  # type: ignore[list-item]


def _album_ergebnis(name: str, kuenstler: str, genre: str = "Hörspiele", tracks: int = 10, cid: int = 1, typ: str = "collection") -> dict[str, Any]:
    r = _album(cid, name, kuenstler, genre, tracks, f"https://x/{cid}/100x100bb.jpg")
    r["wrapperType"] = typ
    return r


def test_t2_nummer_nur_aus_der_eigenen_reihe():
    # A: Die Reihe steht im Künstler
    ctx = _ctx("Bibi Blocksberg", "Die Junghexenbande", 10)
    a = oa.apple_bewerten(ctx, [_album_ergebnis("89: Die Junghexenbande", "Bibi Blocksberg")])["sichere_alben"][0]
    assert a["nummer"] == 89 and a["nummer_stuetze"] is True
    # B: Die Serienwörter stehen im Albumnamen außerhalb des Teils, der dem Folgentitel entspricht
    b = oa.apple_bewerten(ctx, [_album_ergebnis("Bibi Blocksberg, Folge 89: Die Junghexenbande", "Kiddinx")])["sichere_alben"][0]
    assert b["nummer"] == 89 and b["nummer_stuetze"] is True
    # weder noch: Die Reihe steht nur im Titel selbst
    ctx2 = _ctx("Der kleine König", "Eine Weihnachtsgeschichte", 10)
    c = oa.apple_bewerten(ctx2, [_album_ergebnis("Der kleine König, Folge 16: Eine Weihnachtsgeschichte", "Kiddinx")])["sichere_alben"][0]
    assert c["nummer"] == 16 and c["nummer_stuetze"] is True  # Reihe außerhalb des Titelteils: gestützt
    # Titel gleich Serienname: B stützt die Nummer nie („Eine Weihnachtsgeschichte“ → 16 aus fremder Reihe)
    ctx3 = _ctx("Eine Weihnachtsgeschichte", "Eine Weihnachtsgeschichte", 10)
    d = oa.apple_bewerten(ctx3, [_album_ergebnis("16: Eine Weihnachtsgeschichte", "Der kleine König")])["sichere_alben"][0]
    assert d["nummer"] == 16 and d["nummer_stuetze"] is False
    # (ein Album „Der kleine König, Folge 16: Eine Weihnachtsgeschichte“ ist wegen des Zusatzes vorn gar kein sicherer Treffer)
    assert oa.apple_bewerten(ctx3, [_album_ergebnis("Der kleine König, Folge 16: Eine Weihnachtsgeschichte", "Kiddinx")])["sichere_alben"] == []


def test_t2_titel_gleich_serienname_stuetzt_b_nie_im_ergebnis():
    eintrag = {"name": "Der kleine Prinz", "folgen": [{"anzeige": "Der kleine Prinz", "tracks": 10}]}
    treffer = [_album_ergebnis("1: Der kleine Prinz", "Antoine de Saint-Exupéry")]  # Reihe nicht im Künstler
    f = oa.bewerte_eintrag(eintrag, oa.tonie_index_bauen([]), [treffer])["folgen"][0]
    assert f["nummer"]["status"] == "keiner"  # die Nummer kommt nicht aus fremder Zählung
    assert f["cover"]["status"] == "sicher"  # Cover, Art, Titel bleiben gültig
    assert f["art"]["status"] == "sicher"
    # mit der Reihe im Künstler ist die Nummer gestützt
    treffer = [_album_ergebnis("1: Der kleine Prinz", "Der kleine Prinz")]
    f = oa.bewerte_eintrag(eintrag, oa.tonie_index_bauen([]), [treffer])["folgen"][0]
    assert f["nummer"] == {"status": "sicher", "neu": 1, "quelle": {"typ": "apple"}}


def test_apple_sicher_unsicher_und_genre():
    ctx = _ctx("Bibi Blocksberg", "Ausgehext!", 14)
    sicher = _album_ergebnis("Ausgehext!", "Bibi Blocksberg", cid=1)
    pop = _album_ergebnis("Ausgehext!", "Bibi Blocksberg", genre="Pop", cid=2)
    buch = _album_ergebnis("Ausgehext!", "Bibi Blocksberg", genre="Kinder und Jugend", cid=3, typ="audiobook")
    bew = oa.apple_bewerten(ctx, [sicher, pop, buch])
    assert [x["collectionId"] for x in bew["sichere_alben"]] == [1]
    assert [x["collectionId"] for x in bew["sichere_buecher"]] == [3]
    assert [(x["collectionId"], x["grund"]) for x in bew["unsichere"]] == [(2, "genre:Pop")]
    # Nummernkonflikt: bekannte Nummer und Albumnummer verschieden: höchstens unsicher
    ctx_nr = _ctx("Bibi Blocksberg", "Ausgehext!", 14, nummer=7)
    konflikt = oa.apple_bewerten(ctx_nr, [_album_ergebnis("8: Ausgehext!", "Bibi Blocksberg")])
    assert konflikt["sichere_alben"] == [] and konflikt["unsichere"][0]["grund"] == "nummer"
    # Serie nirgends: kein Treffer
    assert oa.apple_bewerten(ctx, [_album_ergebnis("Ausgehext!", "Anderer")]) == {"sichere_alben": [], "sichere_buecher": [], "unsichere": []}
    # ausgeschlossene Alben zählen nirgends
    assert oa.apple_bewerten(ctx, [_album_ergebnis("Ausgehext! Box", "Bibi Blocksberg")])["sichere_alben"] == []
    # Müll in der Antwort schadet nicht
    assert oa.apple_bewerten(ctx, [None, 5, {"wrapperType": "track"}, {"wrapperType": "collection", "collectionName": 5}])["unsichere"] == []  # type: ignore[list-item]


def test_apple_unsicher_schwellen():
    ctx = _ctx("Die Serie", "Der große rote Drache fliegt weit", 5)
    # 80 % der Titelwörter (4 von 5), höchstens zwei Zusatzwörter, keine zusätzliche Zahl
    ok = _album_ergebnis("Der große rote Drache fliegt", "Die Serie")
    zahl = _album_ergebnis("Der große rote Drache fliegt weit 2", "Die Serie", cid=2)
    drei = _album_ergebnis("Der große rote Drache fliegt weit breit wald hoch", "Die Serie", cid=3)  # drei Zusatzwörter
    wenig = _album_ergebnis("Der große Drache", "Die Serie", cid=4)
    bew = oa.apple_bewerten(ctx, [ok, zahl, drei, wenig])
    assert [x["collectionId"] for x in bew["unsichere"]] == [1]
    assert bew["sichere_alben"] == []


def test_art_klasse_und_t4():
    assert oa.genre_klasse({"wrapperType": "audiobook", "primaryGenreName": "Hörspiele"}) == "hoerbuch"
    assert oa.genre_klasse({"wrapperType": "collection", "primaryGenreName": "Hörspiele"}) == "hoerspiel"
    assert oa.genre_klasse({"wrapperType": "collection", "primaryGenreName": "Kinderlieder"}) == "musik"
    assert oa.genre_klasse({"wrapperType": "collection", "primaryGenreName": "Pop"}) == "musik"
    assert oa.genre_klasse({"wrapperType": "collection", "primaryGenreName": "Krimi"}) == "sonst"
    assert oa.genre_klasse({"wrapperType": "collection"}) == "sonst"
    # T4: „Hörspiel“ im Albumnamen schlägt den Hörbuch-Typ
    assert oa.name_hat_hoerspiel("Die Muppets (Hörspiel zum Kinofilm)")
    assert oa.name_hat_hoerspiel("Die Häschenschule - Das Hörspiel")
    assert not oa.name_hat_hoerspiel("Die Muppets")
    assert not oa.name_hat_hoerspiel("Hörspiele für alle")  # nur das Wort „hoerspiel“
    assert not oa.name_hat_hoerspiel(None)
    buch = {"wrapperType": "audiobook", "primaryGenreName": "Kinder und Jugend"}
    assert oa.apple_art(dict(buch, collectionName="Die Muppets (Hörspiel zum Kinofilm)")) == "hoerspiel"
    assert oa.apple_art(dict(buch, collectionName="Die Muppets")) == "hoerbuch"
    assert oa.apple_art({"wrapperType": "collection", "primaryGenreName": "Pop", "collectionName": "X"}) == "musik"
    assert oa.apple_art({"wrapperType": "collection", "primaryGenreName": "Krimi", "collectionName": "X"}) is None


def test_art_hoerbuch_nur_ohne_album_der_folge():
    idx = oa.tonie_index_bauen([])
    eintrag = {"name": "Der Rabe", "folgen": [{"anzeige": "Der Rabe", "tracks": 3}]}
    buch = _album_ergebnis("Der Rabe", "Der Rabe", genre="Kinder und Jugend", cid=3, typ="audiobook")
    album = _album_ergebnis("Der Rabe", "Der Rabe", genre="Hörspiele", cid=1)
    pop = _album_ergebnis("Der Rabe", "Der Rabe", genre="Pop", cid=2)
    # nur ein Hörbuch: Art hoerbuch, sicher
    f = oa.bewerte_eintrag(eintrag, idx, [[buch]])
    assert (f["art"]["status"], f["art"]["neu"]) == ("sicher", "hoerbuch")
    # Hörbuch und Hörspiel-Album derselben Folge: das Album bestimmt die Art
    f = oa.bewerte_eintrag(eintrag, idx, [[buch, album]])
    assert (f["art"]["status"], f["art"]["neu"]) == ("sicher", "hoerspiel")
    # ein Hörbuch und ein Pop-Album mit gleichem Titel: ein Album wurde gefunden, das Hörbuch zählt nicht, Pop widerspricht
    f = oa.bewerte_eintrag(eintrag, idx, [[buch, pop]])
    assert f["art"]["status"] == "unsicher"
    # ein Hörspiel-Album und ein Pop-Album mit gleichem Titel: Widerspruch, nur unsicher
    f = oa.bewerte_eintrag(eintrag, idx, [[album, pop]])
    assert f["art"]["status"] == "unsicher"
    # T4: Hörbuch mit „Hörspiel“ im Namen gibt hoerspiel
    mit_t4 = _album_ergebnis("Der Rabe - Das Hörspiel", "Der Rabe", genre="Kinder und Jugend", cid=4, typ="audiobook")
    f = oa.bewerte_eintrag(eintrag, idx, [[buch, mit_t4]])
    assert (f["art"]["status"], f["art"]["neu"]) == ("sicher", "hoerspiel")


def test_art_aus_tonie_kategorie_und_widerspruch():
    t = _tonie(model="T1", series="Der Rabe", episodes="Der Rabe", category="audio-book", tracks=["x"] * 3)
    idx = oa.tonie_index_bauen([t])
    eintrag = {"name": "Der Rabe", "folgen": [{"anzeige": "Der Rabe", "tracks": 3}]}
    f = oa.bewerte_eintrag(eintrag, idx, [[]])
    assert (f["art"]["status"], f["art"]["neu"]) == ("sicher", "hoerbuch")
    # Songs-Kategorie ist nur unsicher
    s = _tonie(model="T2", series="Der Rabe", episodes="Der Rabe", category="audio-play-songs", tracks=["x"] * 3)
    f = oa.bewerte_eintrag(eintrag, oa.tonie_index_bauen([s]), [[]])
    assert (f["art"]["status"], f["art"]["neu"]) == ("unsicher", "musik")
    # Tonie sagt Hörbuch, Apple-Album Hörspiel: sicher_art mit zwei Werten: unsicher
    album = _album_ergebnis("Der Rabe", "Der Rabe", cid=1)
    f = oa.bewerte_eintrag(eintrag, idx, [[album]])
    assert f["art"]["status"] == "unsicher"


def test_art_mehrheit():
    assert oa.mehrheit(["a", "a", "b"], 3) == "a"
    assert oa.mehrheit(["a", "b"], 2) is None  # nicht mehr als 50 %
    assert oa.mehrheit(["a"], 2) == "a"  # mindestens die Hälfte der Folgen
    assert oa.mehrheit(["a"], 3) is None
    assert oa.mehrheit([], 1) is None
    assert oa.mehrheit(["a", "a", "b", "b"], 4) is None


def test_art_des_eintrags_mehrheit_der_folgen():
    idx = oa.tonie_index_bauen([])
    folgen = [{"anzeige": n, "tracks": 3} for n in ("Der Rabe", "Die Eule", "Der Fuchs")]

    def tr(n: str, cid: int, genre: str = "Hörspiele") -> dict[str, Any]:
        return _album_ergebnis(n, "Die Tiere", genre=genre, cid=cid)

    eintrag = {"name": "Die Tiere", "folgen": folgen}
    # drei Folgen mit Hörspiel-Album: sicher
    a = oa.bewerte_eintrag(eintrag, idx, [[tr("Der Rabe", 1)], [tr("Die Eule", 2)], [tr("Der Fuchs", 3)]])
    assert (a["art"]["status"], a["art"]["neu"]) == ("sicher", "hoerspiel")
    # zwei von drei: sicher (mehr als 50 %, mindestens die Hälfte)
    b = oa.bewerte_eintrag(eintrag, idx, [[tr("Der Rabe", 1)], [tr("Die Eule", 2)], []])
    assert (b["art"]["status"], b["art"]["neu"]) == ("sicher", "hoerspiel")
    # eine von drei: unsicher
    c = oa.bewerte_eintrag(eintrag, idx, [[tr("Der Rabe", 1)], [], []])
    assert (c["art"]["status"], c["art"]["neu"]) == ("unsicher", "hoerspiel")
    # nichts gefunden: keiner
    d = oa.bewerte_eintrag(eintrag, idx, [[], [], []])
    assert d["art"]["status"] == "keiner"


# --------------------------------------------------------------------------
# Cover mit Reihen-Album (2.7)
# --------------------------------------------------------------------------


def test_cover_einzelne_folge_mehrere_sichere_alben_unsicher():
    idx = oa.tonie_index_bauen([])
    eintrag = {"name": "Ausgehext", "folgen": [{"anzeige": "Ausgehext!", "tracks": 3}]}
    eins = _album_ergebnis("Ausgehext!", "Ausgehext", cid=1)
    zwei = _album_ergebnis("Ausgehext!", "Ausgehext", cid=2)
    assert oa.bewerte_eintrag(eintrag, idx, [[eins]])["cover"]["status"] == "sicher"
    assert oa.bewerte_eintrag(eintrag, idx, [[eins, dict(eins)]])["cover"]["status"] == "sicher"  # gleiche collectionId
    f = oa.bewerte_eintrag(eintrag, idx, [[eins, zwei]])["cover"]
    assert f["status"] == "unsicher" and f["grund"] == "mehrere_alben"


def test_cover_reihen_album_bei_zwei_und_mehr_folgen():
    idx = oa.tonie_index_bauen([])
    folgen = [{"anzeige": "Der Rabe", "tracks": 3}, {"anzeige": "Die Eule", "tracks": 4}]
    eintrag = {"name": "Die Tiere", "folgen": folgen}
    folge_cover = _album_ergebnis("Der Rabe", "Die Tiere", cid=10)
    reihe = _album_ergebnis("Die Tiere", "Die Tiere", tracks=20, cid=11)
    reihe2 = _album_ergebnis("Die Tiere", "Sonstwer", tracks=20, cid=12)
    # Reihen-Album vorhanden: genau eine collectionId: sicher, Cover ist das Reihen-Album
    r = oa.bewerte_eintrag(eintrag, idx, [[folge_cover, reihe], []])["cover"]
    assert r["status"] == "sicher" and r["collection_id"] == 11 and r["neu"] == "https://x/11/100x100bb.jpg"
    # mehrere Reihen-Alben: unsicher
    m = oa.bewerte_eintrag(eintrag, idx, [[reihe, reihe2], []])["cover"]
    assert m["status"] == "unsicher" and m["grund"] == "mehrere_reihen_alben"
    # ohne Reihen-Album ist ein Folgen-Cover höchstens unsicher
    o = oa.bewerte_eintrag(eintrag, idx, [[folge_cover], []])["cover"]
    assert o["status"] == "unsicher" and o["grund"] == "nur_folgen_cover" and o["collection_id"] == 10
    # Reihen-Album mit Musik-Genre zählt nicht
    pop = _album_ergebnis("Die Tiere", "Die Tiere", genre="Pop", cid=13)
    assert oa.bewerte_eintrag(eintrag, idx, [[pop], []])["cover"]["status"] == "keiner"
    # Einzeltitel (``einzeln``) mit mehreren Folgen: das Folgen-Cover gilt
    einzeln = dict(eintrag, einzeln=True)
    assert oa.bewerte_eintrag(einzeln, idx, [[folge_cover], []])["cover"]["status"] == "sicher"
    # ein Reihen-Album wird auf Ausschluss geprüft (Summe der Tracks des Eintrags)
    gross = _album_ergebnis("Die Tiere", "Die Tiere", tracks=50, cid=14)
    assert oa.bewerte_eintrag(eintrag, idx, [[gross], []])["cover"]["status"] == "keiner"
    assert [a["collectionId"] for a in oa.reihen_alben("Die Tiere", [gross], 30)] == [14]  # 50 ≤ 2 * 30 → nicht ausgeschlossen


def test_cover_nicht_geholt_wenn_apple_fehlt():
    idx = oa.tonie_index_bauen([])
    eintrag = {"name": "Die Tiere", "folgen": [{"anzeige": "Der Rabe", "tracks": 3}, {"anzeige": "Die Eule", "tracks": 4}]}
    erg = oa.bewerte_eintrag(eintrag, idx, [[_album_ergebnis("Der Rabe", "Die Tiere")], None])
    assert erg["cover"]["status"] == "nicht_geholt"
    assert erg["folgen"][1]["beschreibung"]["status"] == "nicht_geholt"
    assert erg["folgen"][1]["cover"]["status"] == "keiner"
    assert erg["folgen"][0]["beschreibung"]["status"] == "keiner"  # geholt, nichts da


def test_bewerte_eintrag_prueft_laenge():
    with pytest.raises(ValueError):
        oa.bewerte_eintrag({"name": "X", "folgen": [{"anzeige": "a"}]}, oa.tonie_index_bauen([]), [])


# --------------------------------------------------------------------------
# Folgentitel (T1, 4.5)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("anzeige", "nummer", "erwartet"),
    [
        ("Der Rabe", 3, "Folge 3: Der Rabe"),  # Präfix dazu
        ("121_Fünf Freunde und die verlassene Jagdhütte", 121, "Folge 121: Fünf Freunde und die verlassene Jagdhütte"),
        ("03_Der Rabe", 3, "Folge 3: Der Rabe"),
        ("3 - Der Rabe", 3, "Folge 3: Der Rabe"),
        ("3. Der Rabe", 3, "Folge 3: Der Rabe"),
        ("Folge 3: Der Rabe", 3, "Folge 3: Der Rabe"),  # nicht verdoppelt
        ("Folge 3 - Der Rabe", 3, "Folge 3: Der Rabe"),  # vereinheitlicht
        ("Episode 3: Der Rabe", 3, "Folge 3: Der Rabe"),
        ("Der Rabe", None, "Der Rabe"),  # ohne Nummer kein neuer Wert
        ("  Der Rabe ", None, "Der Rabe"),
        ("Teil 1: Geheimnisvolle Verwandlung", 1, "Teil 1: Geheimnisvolle Verwandlung"),  # Teil/Band bleibt
        ("Band 2 - Die Burg", 2, "Band 2 - Die Burg"),
        ("Die Burg - Teil 2", 2, "Die Burg - Teil 2"),
        ("Die Burg – Band 4", 4, "Die Burg – Band 4"),
        ("Gute-Nacht-Geschichten, Folge 15: Der Mond", 15, "Gute-Nacht-Geschichten, Folge 15: Der Mond"),  # Text vor „Folge“
        ("Toy Story 2", 2, "Folge 2: Toy Story 2"),  # nur eine Zahl am Ende ist keine Nummer-Angabe
    ],
)
def test_titel_neu_bekannt(anzeige, nummer, erwartet):
    assert oa.titel_neu_bekannt(anzeige, nummer) == erwartet


def test_teil_band_nummer():
    assert oa.teil_band_nummer("Teil 3: Der Rabe") == 3
    assert oa.teil_band_nummer("Band 3 - Der Rabe") == 3
    assert oa.teil_band_nummer("Der Rabe - Teil 3") == 3
    assert oa.teil_band_nummer("Der Rabe – Band 12") == 12
    assert oa.teil_band_nummer("Der Rabe") is None
    assert oa.teil_band_nummer("Teil 3") is None  # es muss ein Titel folgen
    assert oa.teil_band_nummer("Der Rabe Teil 3") is None  # am Ende nur nach Strich


def _titel_eintrag(anzeige: str, nummer: int | None = None, serie: str = "Sternenschweif", tracks: int = 5) -> dict[str, Any]:
    return {"name": serie, "folgen": [{"anzeige": anzeige, "nummer": nummer, "tracks": tracks}]}


def test_folgentitel_neuer_wert_bei_sicherem_album():
    idx = oa.tonie_index_bauen([])
    album = [_album_ergebnis("Geheimnisvolle Verwandlung", "Sternenschweif", tracks=5)]
    # Nummer bekannt: „Folge N: “ davor, sicher
    f = oa.bewerte_eintrag(_titel_eintrag("Geheimnisvolle Verwandlung", 3), idx, [album])["folgen"][0]["folge_titel"]
    assert (f["status"], f["neu"], f["aenderung"]) == ("sicher", "Folge 3: Geheimnisvolle Verwandlung", "form")
    # Nummer nur im Titel bekannt („Folge 7 - …“): vereinheitlicht zu „Folge 7: …“
    f = oa.bewerte_eintrag(_titel_eintrag("Folge 7 - Geheimnisvolle Verwandlung"), idx, [album])["folgen"][0]["folge_titel"]
    assert f["status"] == "sicher" and f["neu"] == "Folge 7: Geheimnisvolle Verwandlung"
    # ohne Nummer: bestätigt, kein neuer Wert
    f = oa.bewerte_eintrag(_titel_eintrag("Geheimnisvolle Verwandlung"), idx, [album])["folgen"][0]["folge_titel"]
    assert (f["status"], f["neu"], f["aenderung"]) == ("sicher", "Geheimnisvolle Verwandlung", None)
    # gleiches N: bestätigt (Titel bleibt)
    f = oa.bewerte_eintrag(_titel_eintrag("Teil 2: Geheimnisvolle Verwandlung", 2), idx, [album])["folgen"][0]["folge_titel"]
    assert (f["status"], f["neu"], f["aenderung"]) == ("sicher", "Teil 2: Geheimnisvolle Verwandlung", None)
    # anderes N: Titel bleibt unverändert, Zeile ist unsicher
    f = oa.bewerte_eintrag(_titel_eintrag("Teil 2: Geheimnisvolle Verwandlung", 3), idx, [album])["folgen"][0]["folge_titel"]
    assert f["status"] == "unsicher" and f["neu"] == "Teil 2: Geheimnisvolle Verwandlung" and "Teil/Band 2" in f["grund"]
    # kein Album: keiner
    f = oa.bewerte_eintrag(_titel_eintrag("Geheimnisvolle Verwandlung", 3), idx, [[]])["folgen"][0]["folge_titel"]
    assert (f["status"], f["neu"]) == ("keiner", None)
    # nur ein ähnliches Album: unsicher, mit neuem Wert
    aehnlich = [_album_ergebnis("Geheimnisvolle Verwandlung Neuauflage", "Sternenschweif")]
    f = oa.bewerte_eintrag(_titel_eintrag("Geheimnisvolle Verwandlung", 3), idx, [aehnlich])["folgen"][0]["folge_titel"]
    assert f["status"] == "unsicher"


def test_folgentitel_apples_wortlaut_aendert_kein_wort():
    # Apple kürzt oft („Folge 121: und die verlassene Jagdhütte“): der heutige Wortlaut bleibt
    idx = oa.tonie_index_bauen([])
    eintrag = _titel_eintrag("Fünf Freunde und die verlassene Jagdhütte", 121, serie="Fünf Freunde", tracks=40)
    album = [_album_ergebnis("Folge 121: und die verlassene Jagdhütte", "Fünf Freunde", tracks=40)]
    f = oa.bewerte_eintrag(eintrag, idx, [album])["folgen"][0]["folge_titel"]
    assert f["status"] == "sicher" and f["neu"] == "Folge 121: Fünf Freunde und die verlassene Jagdhütte"


@pytest.mark.parametrize(
    ("album", "nummer", "erwartet"),
    [
        ("Bibi Blocksberg - Die große Hexenparty", 100, "Folge 100: Die große Hexenparty"),  # Serienname vor „ - “ fällt weg
        ("Bibi Blocksberg: Die große Hexenparty", 100, "Folge 100: Die große Hexenparty"),
        ("Bibi Blocksberg. Die große Hexenparty", 100, "Folge 100: Die große Hexenparty"),
        ("Bibi Blocksberg, Die große Hexenparty", 100, "Folge 100: Die große Hexenparty"),
        ("Bibi Blocksberg und die Hexe", 100, "Folge 100: Bibi Blocksberg und die Hexe"),  # ohne Trennzeichen bleibt er
        ("Die große Hexenparty (Das Original-Hörspiel zur TV-Serie)", 100, "Folge 100: Die große Hexenparty"),
        ("Die große Hexenparty. Das Hörspiel", 100, "Folge 100: Die große Hexenparty"),
        ("Die große Hexenparty - Hörspiel", 100, "Folge 100: Die große Hexenparty"),
        ("Die große Hexenparty - Original-Hörspiel zur TV-Serie", 100, "Folge 100: Die große Hexenparty"),
        ("100: Die große Hexenparty", 100, "Folge 100: Die große Hexenparty"),
        ("Die große Hexenparty (Teil 2)", 100, "Folge 100: Die große Hexenparty (Teil 2)"),  # Klammer mit Ziffer bleibt
        ("Die große Hexenparty", None, "Die große Hexenparty"),
    ],
)
def test_titel_neu_fuer_platzhalter(album, nummer, erwartet):
    ctx = _ctx("Bibi Blocksberg", "Track 01", 13)
    assert oa.titel_neu(ctx, {"album": album}, nummer) == erwartet


def test_platzhalter_wird_bei_echten_alben_nie_sicher():
    idx = oa.tonie_index_bauen([])
    eintrag = {"name": "Benjamin Blümchen", "folgen": [{"anzeige": "Track 01", "nummer": 154, "tracks": 31}]}
    # Ein Platzhalter ist nie wortgleich mit einem echten Album: Titel gleich gibt es nicht
    res = [_itunes(["blumchen_in_italien_album", "blumchen_in_italien_buch"])]
    f = oa.bewerte_eintrag(eintrag, idx, res)["folgen"][0]["folge_titel"]
    assert f["status"] != "sicher"


def test_platzhalter_mit_aehnlichem_album_nimmt_apples_titel():
    idx = oa.tonie_index_bauen([])
    eintrag = {"name": "Benjamin Blümchen", "folgen": [{"anzeige": "Track 01", "nummer": 154, "tracks": 31}]}
    # Album mit den Platzhalter-Wörtern plus einem Zusatzwort: nur Vorschlag, mit Apples Titel und der heutigen Nummer
    album = [_album_ergebnis("Benjamin Blümchen - Track 01 Extra", "Benjamin Blümchen", tracks=31)]
    f = oa.bewerte_eintrag(eintrag, idx, [album])["folgen"][0]["folge_titel"]
    assert f["status"] == "unsicher" and f["neu"] == "Folge 154: Track 01 Extra" and f["aenderung"] == "woerter"


# --------------------------------------------------------------------------
# Nummer (4.4)
# --------------------------------------------------------------------------


def test_nummer_sicher_unsicher_widerspruch():
    # Tonie sicher mit Nummer, Apple (A) nennt dieselbe: sicher
    t = _tonie(model="N1", series="Sternenschweif", episodes="Teil 7: Der Zauber", tracks=["x"] * 5)
    idx = oa.tonie_index_bauen([t])
    eintrag = {"name": "Sternenschweif", "folgen": [{"anzeige": "Der Zauber", "tracks": 5}]}
    f = oa.bewerte_eintrag(eintrag, idx, [[_album_ergebnis("7: Der Zauber", "Sternenschweif", tracks=5)]])["folgen"][0]["nummer"]
    assert (f["status"], f["neu"]) == ("sicher", 7) and f["quelle"]["typ"] == "tonies+apple"
    # nur Tonie: sicher
    f = oa.bewerte_eintrag(eintrag, idx, [[]])["folgen"][0]["nummer"]
    assert (f["status"], f["neu"], f["quelle"]) == ("sicher", 7, {"typ": "tonies"})
    # Tonie und Apple nennen verschiedene Nummern: unsicher, kein Wert
    f = oa.bewerte_eintrag(eintrag, idx, [[_album_ergebnis("8: Der Zauber", "Sternenschweif", tracks=5)]])["folgen"][0]["nummer"]
    assert f["status"] == "unsicher" and f["neu"] is None
    # nur unsichere Quellen: unsicher mit Wert
    u = _tonie(model="N2", series="Andere Serie", episodes="Teil 7: Der Zauber", tracks=["x"] * 5)
    f = oa.bewerte_eintrag(eintrag, oa.tonie_index_bauen([u]), [[]])["folgen"][0]["nummer"]
    assert (f["status"], f["neu"]) == ("unsicher", 7)
    # nichts: keiner
    f = oa.bewerte_eintrag(eintrag, oa.tonie_index_bauen([]), [[]])["folgen"][0]["nummer"]
    assert f["status"] == "keiner"


# --------------------------------------------------------------------------
# Beschreibung (4.9)
# --------------------------------------------------------------------------


def test_beschreibung_hoerbuch_nur_bei_genau_einer_collection_id():
    idx = oa.tonie_index_bauen([])
    eintrag = {"name": "Der Rabe", "folgen": [{"anzeige": "Der Rabe", "tracks": 1}]}
    eins = _buch(1, "Der Rabe", "Der Rabe", "https://x/1/100x100bb.jpg", "<p>Erster <b>Text</b></p>")
    zwei = _buch(2, "Der Rabe", "Der Rabe", "https://x/2/100x100bb.jpg", "Zweiter Text")
    ohne = _buch(3, "Der Rabe", "Der Rabe", "https://x/3/100x100bb.jpg", "")
    f = oa.bewerte_eintrag(eintrag, idx, [[eins, ohne]])["folgen"][0]["beschreibung"]
    assert (f["status"], f["neu"]) == ("sicher", "Erster Text")
    # gleiche collectionId zweimal zählt einmal
    assert oa.bewerte_eintrag(eintrag, idx, [[eins, dict(eins)]])["folgen"][0]["beschreibung"]["status"] == "sicher"
    # zwei verschiedene collectionIds mit Beschreibung: keine Beschreibung
    f = oa.bewerte_eintrag(eintrag, idx, [[eins, zwei]])["folgen"][0]["beschreibung"]
    assert (f["status"], f["neu"]) == ("keiner", None)
    # ein Hörspiel-Album hat keine Beschreibung; Alter gibt es nur vom Shop
    alb = _album_ergebnis("Der Rabe", "Der Rabe")
    alb["description"] = "Text"
    g = oa.bewerte_eintrag(eintrag, idx, [[alb]])["folgen"][0]
    assert g["beschreibung"]["status"] == "keiner" and g["alter_ab"]["status"] == "keiner"


def test_beschreibung_shop_hat_vorrang_und_ist_hoechstens_2000_zeichen(tonie_index, sitemap):
    eintrag = {"name": "Bibi Blocksberg", "folgen": [{"anzeige": "Folge 100: Die große Hexenparty", "nummer": 100, "tracks": 13}]}
    res = [_itunes(["bibi_folge100_album_mit_jubilaeum", "bibi_folge100_buch"])]
    lang = "x" * 2500
    f = oa.bewerte_eintrag(eintrag, tonie_index, res, {"01-0030": {"beschreibung": lang, "alter_ab": 4}}, sitemap)["folgen"][0]
    assert len(f["beschreibung"]["neu"]) == oa.BESCHREIBUNG_MAX == 2000
    assert f["beschreibung"]["quelle"]["typ"] == "tonies_shop"
    assert f["alter_ab"] == {"status": "sicher", "neu": 4, "quelle": {"typ": "tonies_shop", "model": "01-0030"}}


def test_html_zu_text():
    assert oa.html_zu_text("<p>Ein Satz.</p><p>Zwei.</p>") == "Ein Satz.\n\nZwei."  # Absätze bleiben
    assert oa.html_zu_text("<b>Fett</b><br /><br />Text &amp; mehr") == "Fett\n\nText & mehr"
    assert oa.html_zu_text("a\r\nb") == "a\nb"
    assert oa.html_zu_text("x" * 50, maxlen=10) == "x" * 10
    assert oa.html_zu_text(None) == ""


# --------------------------------------------------------------------------
# Kandidaten für den KI-Schritt (3.4)
# --------------------------------------------------------------------------


def test_kandidaten_fuer_ki(tonie_index, sitemap):
    v = FAELLE["bibi_folge100"]
    eintrag, ergebnisse, _, index = _fall_aufbauen("bibi_folge100", v, _json(FIX / "tonies_auszug.json"))
    f = oa.bewerte_eintrag(eintrag, index, ergebnisse, {}, sitemap, mit_kandidaten=True)["folgen"][0]
    k = f["kandidaten"]
    assert set(k) == {"tonies", "apple"}
    assert 1 <= len(k["tonies"]) <= 3 and 1 <= len(k["apple"]) <= 3
    for t in k["tonies"]:
        assert set(t) == {"series", "episodes", "tracks", "category"}
    for a in k["apple"]:
        assert set(a) == {"collectionName", "artistName", "genre", "trackCount", "wrapperType"}
    # Ausgeschlossene Alben (Jubiläumsedition) und Alben mit anderem Titel kommen nicht vor
    assert not any("Jubiläum" in (a["collectionName"] or "") for a in k["apple"])
    # ohne Wunsch keine Kandidaten
    assert "kandidaten" not in oa.bewerte_eintrag(eintrag, index, ergebnisse, {}, sitemap)["folgen"][0]


def test_kandidaten_hoechstens_drei_und_gekuerzt():
    idx = oa.tonie_index_bauen([])
    ctx = _ctx("Die Serie", "Der Rabe", 3)
    viele = [_album_ergebnis("Der Rabe", "Die Serie " + "x" * 200, cid=i) for i in range(1, 8)]
    k = oa.ki_kandidaten(ctx, idx, viele)
    assert len(k["apple"]) == 3 and k["tonies"] == []
    assert all(len(a["artistName"]) <= oa.KI_TEXT_MAX for a in k["apple"])
    assert oa.ki_kandidaten(ctx, idx, None) == {"tonies": [], "apple": []}
    assert oa.kuerzen_text("  a   b ") == "a b"
    assert oa.kuerzen_text(None) is None
