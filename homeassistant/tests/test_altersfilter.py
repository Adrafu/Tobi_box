"""Altersfilter, Paket AF1 (Design ``docs/designs/altersfilter.md`` Rev. 2, Abschnitte 2 bis 4 und 6; Vertrag W 14.2, Nr. 66).

* Die reine Regel ``eintrags_alter`` mit allen Fällen aus Abschnitt 6.
* ``serie.json``: ``alter_hand`` als echtes Feld (Prüfung, Roundtrip, Fremdfelder, ``stand`` unverändert).
* ``serien/list``: Eingabe ``alter`` (Zahl und ``"ohne"``), Schema, Zusammenspiel mit den anderen Filtern, Blättern, ``alter_ab``/``alter_hand`` der Kurzform.
* Befehl 66 ``serie/alter_setzen``: setzen, löschen, ungültig, Recht, Überraschungs-Serie, Ereignis.
* Erhalten und Wandern: Umbenennen, Art ändern, Papierkorb, Zusammenführen, Folge verschieben.
* Leistung: 600 Einträge, 2 000 Folgen.
"""

from __future__ import annotations

import time

import pytest

from custom_components.tobibox import const
from custom_components.tobibox.media import eintrags_alter, serie_aus_json
from custom_components.tobibox.websocket_api import BEFEHL_RECHTE

from .test_bibliothek import lege_serie, neu_pruefen
from .test_rechte_schutz import _client
from .test_websocket_api import fehler, ok, senden


@pytest.fixture
async def api(hass, integration, hass_ws_client):
    """Administrator."""
    return await hass_ws_client(hass)


@pytest.fixture
async def normal(hass, integration, hass_ws_client):
    return await _client(hass, hass_ws_client, "Normal")


# --------------------------------------------------------------------------
# Die reine Regel (Design 2. und 6.)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hand", "shop", "erwartet"),
    [
        (None, [3, 5], 3),  # kleinster Shop-Wert
        (None, [5, 3], 3),
        (6, [3], 6),  # Wert von Hand geht vor, auch wenn er größer ist
        (2, [3, 5], 2),
        (4, [4], 4),  # gleich dem Shop-Wert: bleibt
        (None, [], None),  # keins
        (None, [None, None], None),
        (0, [3], 0),  # 0 ist ein Wert, kein „fehlt“
        (None, [0, 3], 0),
        (None, [40], None),  # außerhalb 0 bis 18
        (None, [-1], None),
        (None, [19, 4], 4),
        (None, [True], None),  # bool ist keine Zahl
        (None, [False, 7], 7),
        (None, ["4", 4.0], None),  # Text und Kommazahl zählen nicht
        (True, [5], 5),  # ungültiger Wert von Hand zählt nicht
        ("4", [5], 5),
        (19, [], None),
        (18, [], 18),
    ],
)
def test_eintrags_alter_regel(hand, shop, erwartet):
    assert eintrags_alter(hand, shop) == erwartet


def test_eintrags_alter_nimmt_auch_einen_erzeuger():
    assert eintrags_alter(None, (w for w in [7, None, 5])) == 5


# --------------------------------------------------------------------------
# serie.json: alter_hand als echtes Feld (Design 3.1)
# --------------------------------------------------------------------------


def _roh(**extra):
    return {"schema_version": 1, "id": "rabe", "name": "Rabe", "typ": "normal", "folgen": ["a.mp3"], "angelegt_am": "2026-11-01T10:00:00Z", **extra}


@pytest.mark.parametrize("wert", [0, 1, 12, 18])
def test_serie_aus_json_nimmt_gueltiges_alter_hand(wert):
    s = serie_aus_json(_roh(alter_hand=wert), "rabe")
    assert s.alter_hand == wert and "alter_hand" not in s.extra
    assert s.to_json()["alter_hand"] == wert


@pytest.mark.parametrize("wert", ["4", True, False, -1, 19, 4.0, 4.5, None, [4], {"a": 1}])
def test_serie_aus_json_ungueltiges_alter_hand_gilt_als_fehlend_und_verschwindet(wert):
    s = serie_aus_json(_roh(alter_hand=wert), "rabe")
    assert s.alter_hand is None and "alter_hand" not in s.extra  # nicht in ``extra``: sonst würde es unverändert zurückgeschrieben
    assert "alter_hand" not in s.to_json()


def test_to_json_schreibt_alter_hand_nur_wenn_gesetzt_und_erhaelt_fremdfelder():
    s = serie_aus_json(_roh(zukunft={"x": 1}, alter_hand=7), "rabe")
    assert s.to_json()["zukunft"] == {"x": 1} and s.to_json()["alter_hand"] == 7
    s.alter_hand = None
    assert "alter_hand" not in s.to_json() and s.to_json()["zukunft"] == {"x": 1}


def test_stand_rechnet_nicht_ueber_alter_hand():
    ohne = serie_aus_json(_roh(), "rabe")
    mit = serie_aus_json(_roh(alter_hand=5), "rabe")
    assert ohne.stand == mit.stand


# --------------------------------------------------------------------------
# Bestand für die Filter
# --------------------------------------------------------------------------

#: Eintrags-Alter des Bestands (ID -> Wert); ``None`` = keins
ERWARTET = {"a_drei_fuenf": 3, "b_hand": 6, "c_ohne": None, "d_zehn": 10, "e_ungueltig": None, "f_einzel": 4, "g_null": 0, "u_ueber": None}


@pytest.fixture
async def bestand(integration, nas):
    lege_serie(nas, "a_drei_fuenf", "Reihe A", ["f1.mp3", "f2.mp3"], art="hoerspiel", art_quelle="manuell")
    lege_serie(nas, "b_hand", "Reihe B", ["b1.mp3", "b2.mp3"], art="hoerspiel", art_quelle="manuell", alter_hand=6)
    lege_serie(nas, "c_ohne", "Reihe C", ["f1.mp3"], art="hoerbuch", art_quelle="manuell")
    lege_serie(nas, "d_zehn", "Reihe D", ["f1.mp3"], art="musik", art_quelle="manuell")
    lege_serie(nas, "e_ungueltig", "Reihe E", ["f1.mp3", "f2.mp3", "f3.mp3"], art="hoerspiel", art_quelle="manuell")
    lege_serie(nas, "f_einzel", "Lied F", ["lied.mp3"], art="musik", art_quelle="manuell", einzeln=True)
    lege_serie(nas, "g_null", "Reihe G", ["f1.mp3"], art="geschichte", art_quelle="manuell", alter_hand=0)
    lege_serie(nas, "u_ueber", "Überraschung", ["u1.mp3"], typ="ueberraschung", art="hoerspiel", art_quelle="manuell")
    await neu_pruefen(integration)
    st = integration.online.store
    st.setze_folge_info("a_drei_fuenf", "f1.mp3", alter_ab=3)
    st.setze_folge_info("a_drei_fuenf", "f2.mp3", alter_ab=5)
    st.setze_folge_info("b_hand", "b1.mp3", alter_ab=3)
    st.setze_folge_info("d_zehn", "f1.mp3", alter_ab=10)
    st.setze_folge_info("e_ungueltig", "f1.mp3", alter_ab=40)
    st.setze_folge_info("e_ungueltig", "f2.mp3", alter_ab=-1)
    st.setze_folge_info("e_ungueltig", "f3.mp3", alter_ab=True)
    st.setze_folge_info("e_ungueltig", "weg.mp3", alter_ab=1)  # die Folge gibt es nicht (mehr): zählt nicht
    st.setze_folge_info("f_einzel", "lied.mp3", alter_ab=4)
    return integration


async def _ids(client, **felder):
    r = await ok(client, "serien/list", **felder)
    return {s["id"] for s in r["serien"]}, r


def _mit(grenze):
    return {sid for sid, w in ERWARTET.items() if w is not None and w <= grenze}


# --------------------------------------------------------------------------
# serien/list: Eingabe alter
# --------------------------------------------------------------------------


@pytest.mark.parametrize("x", [0, 2, 3, 4, 5, 6, 9, 10, 12, 18])
async def test_filter_zahl_nur_eintraege_mit_alter_kleiner_gleich_x(api, bestand, x):
    ids, r = await _ids(api, alter=x)
    assert ids == _mit(x) and r["gesamt"] == len(ids)  # Einträge ohne Eintrags-Alter fallen heraus


async def test_filter_ohne_nur_eintraege_ohne_eintrags_alter(api, bestand):
    ids, r = await _ids(api, alter="ohne")
    assert ids == {"c_ohne", "e_ungueltig", "u_ueber"} and r["gesamt"] == 3
    alle, _ = await _ids(api)
    assert alle == set(ERWARTET) and ids | _mit(18) == alle and not ids & _mit(18)


async def test_ohne_filter_kommt_alles(api, bestand):
    ids, r = await _ids(api)
    assert ids == set(ERWARTET) and r["gesamt"] == 8


async def test_filter_verschwundene_folgen_und_ungueltige_shop_werte_zaehlen_nicht(api, bestand):
    r = await ok(api, "serien/list", alter=1)
    assert "e_ungueltig" not in {s["id"] for s in r["serien"]}  # „weg.mp3“ mit Wert 1 zählt nicht
    ids, _ = await _ids(api, alter="ohne")
    assert "e_ungueltig" in ids


async def test_filter_mit_art_filter_und_text(api, bestand):
    ids, r = await _ids(api, alter=18, art="musik")
    assert ids == {"d_zehn", "f_einzel"} and r["gesamt"] == 2
    ids, _ = await _ids(api, alter=5, art="musik")
    assert ids == {"f_einzel"}
    ids, _ = await _ids(api, alter=18, filter=["einzeln"])
    assert ids == {"f_einzel"}
    ids, _ = await _ids(api, alter=18, filter=["sammlung"])
    assert ids == _mit(18) - {"f_einzel"}
    ids, _ = await _ids(api, alter=6, text="Reihe B")
    assert ids == {"b_hand"}
    ids, r = await _ids(api, alter=3, text="Reihe B")  # Alter von Hand 6 geht vor dem Shop-Wert 3
    assert ids == set() and r["gesamt"] == 0
    ids, _ = await _ids(api, alter="ohne", text="Reihe C")
    assert ids == {"c_ohne"}
    ids, _ = await _ids(api, alter="ohne", art="hoerbuch")
    assert ids == {"c_ohne"}
    ids, _ = await _ids(api, alter="ohne", filter=["ohne_tobie"], art="hoerspiel")
    assert ids == {"e_ungueltig", "u_ueber"}


async def test_blaettern_und_gesamt_zaehlen_nach_dem_altersfilter(api, bestand):
    gesehen = []
    for offset, weitere in ((0, True), (2, True), (4, False)):
        r = await ok(api, "serien/list", alter=18, limit=2, offset=offset, sortierung="name")
        assert r["gesamt"] == 5 and r["weitere"] is weitere
        gesehen += [s["id"] for s in r["serien"]]
    assert sorted(gesehen) == sorted(_mit(18)) and len(gesehen) == len(set(gesehen))
    r = await ok(api, "serien/list", alter="ohne", limit=2)
    assert r["gesamt"] == 3 and r["weitere"] is True and len(r["serien"]) == 2


@pytest.mark.parametrize("wert", ["ohne", 0, 18])
async def test_schema_alter_gueltig(api, bestand, wert):
    assert (await senden(api, "serien/list", alter=wert))["success"] is True


@pytest.mark.parametrize("wert", ["Ohne", "OHNE", "", True, False, -1, 19, "4", 4.5, None, [4], {"a": 1}])
async def test_schema_alter_ungueltig(api, bestand, wert):
    assert await fehler(api, "serien/list", alter=wert) == "invalid_format"


async def test_alter_gilt_nicht_fuer_folgen_list(api, bestand):
    assert await fehler(api, "folgen/list", alter=4) == "invalid_format"


async def test_alter_filter_fuer_normalen_benutzer(normal, bestand):
    assert {s["id"] for s in (await ok(normal, "serien/list", alter=3))["serien"]} == _mit(3)


# --------------------------------------------------------------------------
# Kurzform: alter_ab und alter_hand
# --------------------------------------------------------------------------


async def test_kurzform_alter_ab_ist_das_eintrags_alter_und_alter_hand_nur_wenn_gesetzt(api, bestand):
    r = await ok(api, "serien/list")
    for s in r["serien"]:
        erwartet = ERWARTET[s["id"]]
        if erwartet is None:
            assert "alter_ab" not in s, s["id"]
        else:
            assert s["alter_ab"] == erwartet, s["id"]  # auch 0
        if s["id"] in ("b_hand", "g_null"):
            assert s["alter_hand"] == (6 if s["id"] == "b_hand" else 0)
        else:
            assert "alter_hand" not in s, s["id"]


async def test_serie_get_zeigt_dasselbe_und_das_folge_objekt_behaelt_sein_eigenes(api, bestand):
    s = await ok(api, "serie/get", serie_id="a_drei_fuenf")
    assert s["alter_ab"] == 3 and "alter_hand" not in s
    s = await ok(api, "serie/get", serie_id="b_hand")
    assert (s["alter_ab"], s["alter_hand"]) == (6, 6)
    s = await ok(api, "serie/get", serie_id="f_einzel")
    assert s["alter_ab"] == 4 and s["einzeln"] is True  # Einzeltitel: ein Wert oben
    s = await ok(api, "serie/get", serie_id="e_ungueltig")
    assert "alter_ab" not in s


async def test_filter_und_anzeige_laufen_nie_auseinander(api, bestand):
    """Der Shop-Wert ändert sich nur im Store: die nächste Anfrage sieht es in Filter und Kurzform (nichts steht im Index)."""
    assert "c_ohne" not in (await _ids(api, alter=2))[0]
    bestand.online.store.setze_folge_info("c_ohne", "f1.mp3", alter_ab=2)
    ids, r = await _ids(api, alter=2)
    assert "c_ohne" in ids and {s["id"]: s for s in r["serien"]}["c_ohne"]["alter_ab"] == 2
    bestand.online.store.setze_folge_info("c_ohne", "f1.mp3", alter_ab=None)  # zurückgenommen
    ids, r = await _ids(api, alter="ohne")
    assert "c_ohne" in ids and "alter_ab" not in {s["id"]: s for s in r["serien"]}["c_ohne"]


@pytest.mark.parametrize("kaputt", [None, "kaputt", ["x"], {"f1.mp3": None, "f2.mp3": "x"}])
async def test_kaputter_store_eintrag_stoppt_serien_list_nicht(api, bestand, kaputt):
    bestand.online.store.daten["serien"]["a_drei_fuenf"]["folgen"] = kaputt
    r = await ok(api, "serien/list")
    a = {s["id"]: s for s in r["serien"]}["a_drei_fuenf"]
    assert "alter_ab" not in a  # die Folgen zählen als ohne Alter
    assert (await _ids(api, alter="ohne"))[0] >= {"a_drei_fuenf"}


async def test_hello_meldet_alter(api, bestand):
    assert "alter" in const.FAEHIGKEITEN
    assert "alter" in (await ok(api, "hello", v=1))["faehigkeiten"]


# --------------------------------------------------------------------------
# Befehl 66 serie/alter_setzen
# --------------------------------------------------------------------------


def test_befehl_66_braucht_das_recht_alltag_nicht_lesen():
    assert BEFEHL_RECHTE["serie/alter_setzen"] == "alltag"


async def test_setzen_und_loeschen(api, normal, bestand, nas, ereignisse):
    stand = (await ok(api, "serie/get", serie_id="c_ohne"))["stand"]
    ereignisse.clear()
    r = await ok(normal, "serie/alter_setzen", serie_id="c_ohne", alter_hand=4)  # Recht alltag
    assert (r["serie"]["alter_hand"], r["serie"]["alter_ab"]) == (4, 4) and r["serie"]["stand"] == stand  # ``stand`` unverändert
    assert nas.serie_json("c_ohne")["alter_hand"] == 4
    assert [(e["art"], e["daten"]) for e in ereignisse if e["thema"] == "medien"] == [("serien_geaendert", {"serie_ids": ["c_ohne"]})]
    assert "c_ohne" in (await _ids(api, alter=4))[0] and "c_ohne" not in (await _ids(api, alter=3))[0]
    assert "c_ohne" not in (await _ids(api, alter="ohne"))[0]
    # idempotent: gleicher Wert, keine Änderung, kein Ereignis
    ereignisse.clear()
    await ok(api, "serie/alter_setzen", serie_id="c_ohne", alter_hand=4)
    assert not [e for e in ereignisse if e["thema"] == "medien"]
    # löschen mit null: danach wieder ohne Alter
    r = await ok(api, "serie/alter_setzen", serie_id="c_ohne", alter_hand=None)
    assert "alter_hand" not in r["serie"] and "alter_ab" not in r["serie"]
    assert "alter_hand" not in nas.serie_json("c_ohne")
    assert "c_ohne" in (await _ids(api, alter="ohne"))[0]
    assert [e["art"] for e in ereignisse if e["thema"] == "medien"] == ["serien_geaendert"]


async def test_loeschen_laesst_den_shop_wert_wieder_gelten(api, bestand, nas):
    r = await ok(api, "serie/alter_setzen", serie_id="a_drei_fuenf", alter_hand=8)
    assert r["serie"]["alter_ab"] == 8
    assert "a_drei_fuenf" not in (await _ids(api, alter=5))[0]
    r = await ok(api, "serie/alter_setzen", serie_id="a_drei_fuenf", alter_hand=None)
    assert r["serie"]["alter_ab"] == 3 and "alter_hand" not in r["serie"]
    assert "a_drei_fuenf" in (await _ids(api, alter=3))[0]
    # löschen, wo nichts ist: keine Änderung, kein Fehler
    assert "alter_hand" not in (await ok(api, "serie/alter_setzen", serie_id="c_ohne", alter_hand=None))["serie"]


async def test_setzen_null_ist_gueltig_und_geht_vor(api, bestand):
    r = await ok(api, "serie/alter_setzen", serie_id="d_zehn", alter_hand=0)
    assert (r["serie"]["alter_hand"], r["serie"]["alter_ab"]) == (0, 0)
    assert "d_zehn" in (await _ids(api, alter=0))[0]


@pytest.mark.parametrize("wert", ["4", "ohne", True, False, -1, 19, 4.5, [4], {"a": 1}])
async def test_setzen_ungueltig(api, bestand, nas, wert):
    assert await fehler(api, "serie/alter_setzen", serie_id="c_ohne", alter_hand=wert) == "invalid_format"
    assert "alter_hand" not in nas.serie_json("c_ohne")


async def test_setzen_fehler(api, bestand):
    assert await fehler(api, "serie/alter_setzen", serie_id="gibtsnicht", alter_hand=4) == "serie_nicht_gefunden"
    assert await fehler(api, "serie/alter_setzen", serie_id="c_ohne") == "invalid_format"  # alter_hand ist Pflicht (auch null)
    assert await fehler(api, "serie/alter_setzen", alter_hand=4) == "invalid_format"


async def test_setzen_bei_der_ueberraschungs_serie(normal, bestand, nas):
    r = await ok(normal, "serie/alter_setzen", serie_id="u_ueber", alter_hand=3)  # auch hier Recht alltag (AF-6)
    assert (r["serie"]["typ"], r["serie"]["alter_ab"]) == ("ueberraschung", 3)
    assert nas.serie_json("u_ueber")["alter_hand"] == 3


async def test_setzen_bei_einem_einzeltitel(api, bestand, nas):
    r = await ok(api, "serie/alter_setzen", serie_id="f_einzel", alter_hand=2)
    assert (r["serie"]["einzeln"], r["serie"]["alter_ab"], r["serie"]["alter_hand"]) == (True, 2, 2)
    assert nas.serie_json("f_einzel")["einzeln"] is True


async def test_roundtrip_mit_fremdfeldern_und_ungueltigem_wert(api, bestand, nas):
    lege_serie(nas, "h_fremd", "Reihe H", ["f1.mp3"], alter_hand="4", zukunft={"x": [1, 2]}, art="hoerspiel", art_quelle="manuell")
    await neu_pruefen(bestand)
    s = await ok(api, "serie/get", serie_id="h_fremd")
    assert "alter_hand" not in s and "alter_ab" not in s  # Text gilt als fehlend
    assert nas.serie_json("h_fremd")["alter_hand"] == "4"  # noch nicht geschrieben
    r = await ok(api, "serie/alter_setzen", serie_id="h_fremd", alter_hand=5)
    daten = nas.serie_json("h_fremd")
    assert daten["alter_hand"] == 5 and daten["zukunft"] == {"x": [1, 2]} and r["serie"]["alter_hand"] == 5
    # ungültiger Wert verschwindet beim nächsten Schreiben, egal durch welchen Befehl
    lege_serie(nas, "i_alt", "Reihe I", ["f1.mp3"], alter_hand=99, art="hoerspiel", art_quelle="manuell")
    await neu_pruefen(bestand)
    await ok(api, "serie/rename", serie_id="i_alt", name="Reihe I neu")
    assert "alter_hand" not in nas.serie_json("i_alt")


# --------------------------------------------------------------------------
# Erhalten und Wandern (Design 3.1, 3.3)
# --------------------------------------------------------------------------


async def test_umbenennen_und_art_aendern_erhalten_alter_hand(api, bestand, nas):
    await ok(api, "serie/rename", serie_id="b_hand", name="Reihe B neu")
    assert nas.serie_json("b_hand")["alter_hand"] == 6
    await ok(api, "serie/art_setzen", serie_id="b_hand", art="hoerbuch")
    daten = nas.serie_json("b_hand")
    assert daten["alter_hand"] == 6 and daten["art"] == "hoerbuch"
    r = await ok(api, "serie/get", serie_id="b_hand")
    assert r["alter_hand"] == 6 and r["name"] == "Reihe B neu"


async def test_papierkorb_und_wiederherstellen_behalten_das_feld(api, bestand, nas):
    r = await ok(api, "serie/delete", serie_id="b_hand")
    kopie = nas.papierkorb / r["eintrag"]["id"] / "inhalt" / "b_hand" / "serie.json"
    import json

    assert json.loads(kopie.read_text(encoding="utf-8"))["alter_hand"] == 6
    assert "b_hand" not in (await _ids(api))[0]
    wieder = await ok(api, "papierkorb/restore", eintrag_id=r["eintrag"]["id"])
    assert wieder["serie"]["alter_hand"] == 6
    assert nas.serie_json("b_hand")["alter_hand"] == 6 and "b_hand" in (await _ids(api, alter=6))[0]


async def test_zusammenfuehren_ziel_ohne_wert_uebernimmt_den_der_quelle(api, bestand, nas):
    r = await ok(api, "serien/zusammenfuehren", quelle_id="b_hand", ziel_id="c_ohne")
    assert r["ziel"]["alter_hand"] == 6 and r["ziel"]["alter_ab"] == 6
    assert nas.serie_json("c_ohne")["alter_hand"] == 6
    assert "b_hand" not in (await _ids(api))[0] and "c_ohne" in (await _ids(api, alter=6))[0]


async def test_zusammenfuehren_ziel_mit_wert_behaelt_seinen(api, bestand, nas):
    r = await ok(api, "serien/zusammenfuehren", quelle_id="b_hand", ziel_id="g_null")
    assert r["ziel"]["alter_hand"] == 0 and nas.serie_json("g_null")["alter_hand"] == 0


async def test_zusammenfuehren_ohne_wert_in_der_quelle_aendert_das_ziel_nicht(api, bestand, nas):
    await ok(api, "serien/zusammenfuehren", quelle_id="c_ohne", ziel_id="b_hand")
    assert nas.serie_json("b_hand")["alter_hand"] == 6
    await ok(api, "serien/zusammenfuehren", quelle_id="d_zehn", ziel_id="e_ungueltig")  # beide ohne Hand-Wert
    assert "alter_hand" not in nas.serie_json("e_ungueltig")


async def test_zusammenfuehren_shop_werte_wandern_mit_den_folgen(api, bestand, nas):
    r = await ok(api, "serien/zusammenfuehren", quelle_id="d_zehn", ziel_id="c_ohne")
    assert r["ziel"]["alter_ab"] == 10 and "alter_hand" not in r["ziel"]


async def test_folge_verschieben_alter_hand_bleibt_beim_eintrag_shop_wert_wandert(api, bestand, nas):
    await ok(api, "folge/verschieben", serie_id="b_hand", folge="b1.mp3", ziel_serie_id="c_ohne")
    c = await ok(api, "serie/get", serie_id="c_ohne")
    assert "alter_hand" not in c and c["alter_ab"] == 3  # Shop-Wert 3 der Folge ist mitgezogen, Hand-Wert nicht
    assert "alter_hand" not in nas.serie_json("c_ohne")
    b = await ok(api, "serie/get", serie_id="b_hand")
    assert b["alter_hand"] == 6 and b["alter_ab"] == 6 and nas.serie_json("b_hand")["alter_hand"] == 6


# --------------------------------------------------------------------------
# Leistung (Design 4.2): 600 Einträge, 2 000 Folgen
# --------------------------------------------------------------------------

#: Design-Ziel der Suche: unter 200 ms (gemessen wenige ms)
LEISTUNG_GRENZE_S = 0.2


async def test_leistung_600_eintraege_2000_folgen(api, nas, integration):
    for i in range(600):
        folgen = [f"Folge {j:02d}.mp3" for j in range(1, (4 if i < 200 else 3) + 1)]  # 200 Einträge mit 4 Folgen, 400 mit 3: 2 000 Folgen
        extra = {"alter_hand": i % 13} if i % 5 == 0 else {}
        lege_serie(nas, f"s{i:04d}", f"Hörspielreihe {i:04d}", folgen, art=("hoerspiel", "musik")[i % 2], art_quelle="tags", **extra)
    await neu_pruefen(integration)
    assert len(integration.medien.serien) == 600 and sum(len(i.serie.folgen) for i in integration.medien.serien.values()) == 2000
    st = integration.online.store
    for i in range(600):
        if i % 3 == 0:  # ein Drittel hat Shop-Werte an allen Folgen
            for n, f in enumerate(integration.medien.serien[f"s{i:04d}"].serie.folgen):
                st.setze_folge_info(f"s{i:04d}", f, alter_ab=(i + n) % 12)

    def erwartet(i):
        hand = i % 13 if i % 5 == 0 else None
        shop = [(i + n) % 12 for n in range(4 if i < 200 else 3)] if i % 3 == 0 else []
        return eintrags_alter(hand, shop)

    soll = {f"s{i:04d}": erwartet(i) for i in range(600)}

    async def messe(**felder):
        t0 = time.perf_counter()
        antwort = await senden(api, "serien/list", **felder)
        return time.perf_counter() - t0, antwort

    await messe(limit=60)  # kalt: baut den Index auf
    faelle = {
        "alter=5": dict(alter=5, limit=60),
        "alter=ohne": dict(alter="ohne", limit=60),
        "alter=5 + art + Suche": dict(alter=5, art="musik", text="reihe", limit=60),
        "alter=18 ohne limit": dict(alter=18),
        "kein Filter (Kurzform mit alter_ab)": dict(limit=60),
    }
    for name, felder in faelle.items():
        beste = min([(await messe(**felder))[0] for _ in range(5)])
        print(f"LEISTUNG {name}: {beste * 1000:.1f} ms")
        assert beste < LEISTUNG_GRENZE_S, f"{name}: {beste * 1000:.0f} ms"
    # und richtig gerechnet
    _, a = await messe(alter=5)
    assert a["success"] and a["result"]["gesamt"] == sum(1 for w in soll.values() if w is not None and w <= 5)
    for s in a["result"]["serien"]:
        assert s["alter_ab"] == soll[s["id"]] <= 5
    _, o = await messe(alter="ohne")
    assert o["result"]["gesamt"] == sum(1 for w in soll.values() if w is None)
