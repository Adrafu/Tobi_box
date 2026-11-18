"""Naht ``online_quellen.parse_itunes`` -> ``online_abgleich.bewerte_eintrag`` (Review GO2-1): Der Cover-Wert muss auf ``bild_url`` (600 px) abbildbar sein."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.tobibox import online_abgleich as ab
from custom_components.tobibox.online_ki import baue_eingabe, baue_instructions
from custom_components.tobibox.online_quellen import parse_itunes, parse_shop, parse_sitemap, parse_tonie_liste

ITUNES = Path(__file__).parent / "fixtures" / "online" / "itunes"


def laden(name: str) -> list[dict[str, Any]]:
    return parse_itunes((ITUNES / name).read_bytes())


def test_parse_itunes_behaelt_artwork_und_bild_url() -> None:
    for datei in sorted(ITUNES.glob("*.json")):
        for e in parse_itunes(datei.read_bytes()):
            if "bild_url" in e:
                assert e["artworkUrl100"].endswith("/100x100bb.jpg")
                assert e["bild_url"] == e["artworkUrl100"].rsplit("/", 1)[0] + "/600x600bb.jpg"
            else:
                assert "artworkUrl100" not in e


@pytest.mark.parametrize(
    ("datei", "serie", "folge", "tracks"),
    [
        ("mulan_album.json", "Mulan", "Mulan", 11),
        ("bibi_folge100_album_mit_jubilaeum.json", "Bibi Blocksberg", "Die große Hexenparty", 8),
        ("peppa_das_neue_haus_album.json", "Peppa Pig", "Das neue Haus", 3),
        ("blumchen_in_italien_album.json", "Benjamin Blümchen", "Benjamin Blümchen in Italien", 8),
    ],
)
def test_abgleich_cover_wert_bildet_auf_bild_url_ab(datei: str, serie: str, folge: str, tracks: int) -> None:
    ergebnisse = laden(datei)
    eintrag = {"name": serie, "ordner": serie, "art": "hoerspiel", "art_quelle": "geraten", "cover_quelle": "auto", "folgen": [{"anzeige": folge, "nummer": None, "tracks": tracks}]}
    res = ab.bewerte_eintrag(eintrag, {"eintraege": [], "index": {}}, [ergebnisse])
    for feld in (res["cover"], res["folgen"][0]["cover"]):
        assert feld["status"] == "sicher" and feld["neu"]
        passend = [e for e in ergebnisse if e.get("artworkUrl100") == feld["neu"]]
        assert passend, "Cover-Wert stammt nicht aus dem parse_itunes-Ergebnis"
        assert passend[0]["bild_url"] == feld["neu"].rsplit("/", 1)[0] + "/600x600bb.jpg"
        assert passend[0]["collectionId"] == feld["collection_id"]


# --------------------------------------------------------------------------
# Naht 1 bis 3 (Bibi Folge 100, Fixtures wie ``test_online_abgleich._fall_aufbauen``)
# --------------------------------------------------------------------------

FIX = Path(__file__).parent / "fixtures" / "online"
FALL = json.loads((FIX / "erwartung.json").read_text(encoding="utf-8"))["faelle"]["bibi_folge100"]
SITEMAP = parse_sitemap((FIX / "sitemap_auszug.xml").read_bytes())
MODEL = "01-0030"


def roh_itunes() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in FALL["itunes_dateien"]:
        out.extend(json.loads((FIX / "itunes" / f"{d}.json").read_text(encoding="utf-8"))["results"])
    return out


def bibi_eintrag() -> dict[str, Any]:
    return {
        "name": FALL["eintrag"],
        "einzeln": False,
        "cover_quelle": FALL["cover_heute"],
        "art_quelle": "geraten",
        "folgen": [{"anzeige": FALL["folge"], "nummer": FALL["heutige_nummer"], "tracks": FALL["unsere_tracks"], "art": "ordner"}],
    }


def tonies_roh() -> list[dict[str, Any]]:
    return json.loads((FIX / "tonies_auszug.json").read_text(encoding="utf-8"))


def test_naht_shop_parse_shop_in_den_abgleich() -> None:
    index = ab.tonie_index_bauen(tonies_roh())
    seite = parse_shop((FIX / "shop" / "01-0030_bibi_hexenparty.html").read_bytes(), MODEL)
    assert set(seite) == {"beschreibung", "alter_ab"}  # genau die Form von ``shop_daten[model]``
    folge = ab.bewerte_eintrag(bibi_eintrag(), index, [roh_itunes()], {MODEL: seite}, SITEMAP)["folgen"][0]
    assert folge["alter_ab"] == {"status": "sicher", "neu": 4, "quelle": {"typ": "tonies_shop", "model": MODEL}}
    assert folge["beschreibung"]["status"] == "sicher" and folge["beschreibung"]["neu"] == seite["beschreibung"]
    assert folge["beschreibung"]["quelle"]["typ"] == "tonies_shop"
    # nur eines der beiden Felder (die andere Angabe fehlt auf der Seite): geht ebenfalls
    nur_alter = {k: v for k, v in seite.items() if k == "alter_ab"}
    f2 = ab.bewerte_eintrag(bibi_eintrag(), index, [roh_itunes()], {MODEL: nur_alter}, SITEMAP)["folgen"][0]
    assert f2["alter_ab"]["status"] == "sicher" and f2["alter_ab"]["neu"] == 4


def test_naht_shop_falsche_sales_id_ist_geholt_aber_unbrauchbar() -> None:
    """``parse_shop`` gibt bei falscher ``salesId`` ``None``: genau der Wert, den der Abgleich für „geholt, unbrauchbar“ erwartet."""
    index = ab.tonie_index_bauen(tonies_roh())
    seite = parse_shop((FIX / "shop" / "01-0030_salesid_anders_kuenstlich.html").read_bytes(), MODEL)
    assert seite is None
    ohne = ab.bewerte_eintrag(bibi_eintrag(), index, [roh_itunes()], {}, SITEMAP)["folgen"][0]
    assert ohne["alter_ab"]["status"] == "nicht_geholt"  # Seite fehlt noch
    kaputt = ab.bewerte_eintrag(bibi_eintrag(), index, [roh_itunes()], {MODEL: seite}, SITEMAP)["folgen"][0]
    assert kaputt["alter_ab"]["status"] == "keiner"  # endgültig, nicht mehr „nicht geholt“


def test_naht_tonie_liste_parse_index_pruefen_wie_mit_rohdaten() -> None:
    roh = tonies_roh()
    reduziert = parse_tonie_liste(json.dumps(roh).encode())  # Standard: online_abgleich.tonie_benutzbar
    assert reduziert
    ctx = ab.folge_kontext(FALL["eintrag"], bibi_eintrag()["folgen"][0], False, 1)
    mit_roh = ab.tonie_pruefen(ctx, ab.tonie_index_bauen(roh), SITEMAP)
    mit_reduziert = ab.tonie_pruefen(ctx, ab.tonie_index_bauen(reduziert), SITEMAP)
    assert mit_roh["status"] == mit_reduziert["status"] == FALL["tonie_status"] == "sicher"
    assert [e["model"] for e in mit_roh["sichere"]] == [e["model"] for e in mit_reduziert["sichere"]] == [MODEL]
    for feld in ("art", "art_sicher", "nummer", "shop_pfade"):
        assert mit_roh[feld] == mit_reduziert[feld]
    # und nach dem Ablegen und Zurücklesen (JSON) bleibt es gleich
    zurueck = json.loads(json.dumps(reduziert))
    assert ab.tonie_pruefen(ctx, ab.tonie_index_bauen(zurueck), SITEMAP)["status"] == "sicher"


def test_naht_kandidaten_in_die_ki_eingabe() -> None:
    index = ab.tonie_index_bauen(parse_tonie_liste((FIX / "tonies_auszug.json").read_bytes()))
    eintrag = bibi_eintrag()
    res = ab.bewerte_eintrag(eintrag, index, [parse_itunes(json.dumps({"results": roh_itunes()}).encode())], {}, SITEMAP, mit_kandidaten=True)
    folge = res["folgen"][0]
    kand = folge["kandidaten"]
    assert kand["tonies"] and kand["apple"]
    eingabe = baue_eingabe(
        "Bibi Blocksberg",
        "Bibi Blocksberg",
        [{"anzeige": eintrag["folgen"][0]["anzeige"], "nummer": 100, "tracks": 13, "pruefen_gruende": [], **kand}],
    )
    f = eingabe["folgen"][0]
    # die Schlüssel passen: nichts ging beim Übernehmen verloren, nichts Fremdes kam dazu
    assert f["tonies"] == [{"series": t["series"], "episodes": t["episodes"], "tracks": t["tracks"], "category": t["category"]} for t in kand["tonies"]]
    assert f["apple"] == [
        {"collectionName": a["collectionName"], "artistName": a["artistName"], "genre": a["genre"], "trackCount": a["trackCount"], "wrapperType": a["wrapperType"]}
        for a in kand["apple"]
    ]
    assert all(t["series"] and t["episodes"] for t in f["tonies"]) and all(a["collectionName"] for a in f["apple"])
    verboten = {"model", "collectionId", "serie_id", "id", "pic", "artworkUrl100", "bild_url"}
    assert not (_schluessel(eingabe) & verboten)
    text = baue_instructions(eingabe)
    assert MODEL not in text and "serie_id" not in text
    block = text[text.rindex("<<<DATEN\n") + len("<<<DATEN\n") : text.rindex("\nDATEN>>>\n")]
    assert json.loads(block) == eingabe
    for a in f["apple"]:
        assert str(1069118023) not in json.dumps(a)  # keine collectionId


def _schluessel(x: Any) -> set[str]:
    if isinstance(x, dict):
        return set(x) | {k for v in x.values() for k in _schluessel(v)}
    if isinstance(x, list):
        return {k for v in x for k in _schluessel(v)}
    return set()
