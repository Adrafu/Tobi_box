"""Paket A4d „Hörstelle“ (Vertrag W, Befehle 40 bis 42 und 14.6; Design 11.4.5): Store ``tobibox.hoerstellen``, je Benutzer.

* Zwei Benutzer sehen nie die Daten des anderen (Befehle, Kurzform, Folge-Objekt, Sortierung).
* Der Store überlebt den Neustart; auf die Platte wird erst nach 60 Sekunden gesammelt geschrieben.
* Prüfungen von ``hoerstelle/set``, Obergrenzen, Aufräumen beim Start, Sortierung ``angehoert``.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import CLIENT_ID, async_fire_time_changed

from custom_components.tobibox import hoerstelle as hoerstelle_modul
from custom_components.tobibox.const import (
    DOMAIN,
    HOERSTELLE_DAUER_UNBEKANNT_MAX_S,
    HOERSTELLE_SCHREIBEN_JE_MINUTE,
    HOERSTELLE_SPEICHER_VERZOEGERUNG_S,
)
from custom_components.tobibox.hoerstelle import Hoerstellen

from .conftest import fertig
from .test_websocket_api import fehler, ok, senden

KEY = "tobibox.hoerstellen"


async def _client(hass, hass_ws_client, name: str):
    nutzer = await hass.auth.async_create_user(name, group_ids=[GROUP_ID_USER])
    refresh = await hass.auth.async_create_refresh_token(nutzer, CLIENT_ID)
    client = await hass_ws_client(hass, hass.auth.async_create_access_token(refresh))
    client.nutzer = nutzer
    return client


@pytest.fixture
async def bestand(hass, integration, nas, lege_mp3):
    """Serien ``rabe`` (a.mp3, b.mp3, Ordner ``Buch`` mit drei Tracks) und ``zwei`` (c.mp3). Die Dauern sind bekannt (im Store gesetzt)."""
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3", "b.mp3", "Buch"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    for i in (1, 2, 3):
        lege_mp3(pfad / "Buch" / f"{i}.mp3")
    pfad2 = nas.serie("zwei", "zwei", "Zweite Serie", ["c.mp3"])
    lege_mp3(pfad2 / "c.mp3")
    await integration.medien.pruefen()
    await integration.dauer.warte_auf_ende()
    integration.medieninfo.setze_dauer("rabe", "a.mp3", 100)
    integration.medieninfo.setze_dauer("rabe", "b.mp3", 200)
    integration.medieninfo.setze_dauer("rabe", "Buch", 600, [100, 200, 300])
    integration.medieninfo.setze_dauer("zwei", "c.mp3", 50)
    return integration


@pytest.fixture
async def admin(hass, bestand, hass_ws_client):
    ws = await hass_ws_client(hass)
    return ws


@pytest.fixture
async def anna(hass, bestand, hass_ws_client):
    return await _client(hass, hass_ws_client, "Anna")


@pytest.fixture
async def ben(hass, bestand, hass_ws_client):
    return await _client(hass, hass_ws_client, "Ben")


async def setze(client, serie="rabe", folge="a.mp3", position=10, dauer=100, **mehr):
    return await ok(client, "hoerstelle/set", serie_id=serie, folge=folge, position_s=position, dauer_s=dauer, **mehr)


# --------------------------------------------------------------------------
# Schreiben, Lesen
# --------------------------------------------------------------------------


async def test_set_antwortet_sofort_mit_leerem_objekt_und_get_liest_zurueck(anna):
    assert await setze(anna, position=47) == {}
    r = await ok(anna, "hoerstelle/get", serie_id="rabe")
    assert r["weiter"] == {"folge": "a.mp3", "position_s": 47, "track": 0, "anteil": 0.47, "rest_s": 53, "zeit": r["weiter"]["zeit"]}
    assert r["weiter"]["zeit"].endswith("Z")
    assert r["folgen"] == {"a.mp3": {"position_s": 47, "dauer_s": 100, "fertig": False, "zeit": r["weiter"]["zeit"]}}


async def test_get_ohne_hoerstelle(anna):
    assert await ok(anna, "hoerstelle/get", serie_id="rabe") == {"weiter": None, "folgen": {}}
    assert await fehler(anna, "hoerstelle/get", serie_id="gibtsnicht") == "serie_nicht_gefunden"
    assert await fehler(anna, "hoerstelle/get") == "invalid_format"


async def test_weiter_ist_die_zuletzt_gehoerte_folge(anna):
    await setze(anna, folge="a.mp3", position=10)
    await setze(anna, folge="b.mp3", position=50, dauer=200)
    r = await ok(anna, "hoerstelle/get", serie_id="rabe")
    assert r["weiter"]["folge"] == "b.mp3" and r["weiter"]["position_s"] == 50
    assert set(r["folgen"]) == {"a.mp3", "b.mp3"}
    await setze(anna, folge="a.mp3", position=20)  # zurück zur ersten
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["weiter"]["folge"] == "a.mp3"


async def test_zuletzt_gespeichert_gewinnt_je_folge(anna):
    await setze(anna, position=10)
    await setze(anna, position=30)
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["position_s"] == 30


async def test_ordner_folge_stelle_im_track_anteil_ueber_die_ganze_folge(anna):
    await setze(anna, folge="Buch", track=1, position=50, dauer=200)  # Track 2 (200 s), Stelle 50 s: insgesamt 150 von 600 s
    r = (await ok(anna, "hoerstelle/get", serie_id="rabe"))["weiter"]
    assert (r["folge"], r["track"], r["position_s"]) == ("Buch", 1, 50)
    assert r["anteil"] == 0.25 and r["rest_s"] == 450
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["Buch"]["dauer_s"] == 200  # Länge des Tracks, in dem die Stelle liegt


async def test_track_steht_bei_ordner_folgen_in_get_und_serie_get_bei_einzeldateien_nicht(anna):
    await setze(anna, folge="Buch", track=2, position=50, dauer=300)
    await setze(anna, folge="a.mp3", position=10)
    r = await ok(anna, "hoerstelle/get", serie_id="rabe")
    assert r["folgen"]["Buch"]["track"] == 2
    assert "track" not in r["folgen"]["a.mp3"]
    s = await ok(anna, "serie/get", serie_id="rabe")
    h = {f["name"]: f["hoerstelle"] for f in s["folgen"] if "hoerstelle" in f}
    assert h["Buch"] == {"position_s": 50, "fertig": False, "track": 2}
    assert h["a.mp3"] == {"position_s": 10, "fertig": False}


async def test_ordner_folge_ist_erst_am_ende_des_letzten_tracks_fertig(anna):
    await setze(anna, folge="Buch", track=0, position=100, dauer=100)  # Ende von Track 1: noch nicht fertig
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["Buch"]["fertig"] is False
    await setze(anna, folge="Buch", track=2, position=299, dauer=300)  # bis auf 2 Sekunden am Ende des letzten Tracks
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["Buch"]["fertig"] is True


async def test_track_ausserhalb_der_folge_ist_ungueltig(anna):
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="Buch", track=3, position_s=1, dauer_s=100) == "invalid_format"
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", track=1, position_s=1, dauer_s=100) == "invalid_format"
    await ok(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", track=0, position_s=1, dauer_s=100)


# --------------------------------------------------------------------------
# Prüfung von hoerstelle/set
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "felder",
    [
        {"position_s": -1, "dauer_s": 100},
        {"position_s": 103, "dauer_s": 100},  # über Dauer + 2
        {"position_s": 10, "dauer_s": 0},
        {"position_s": 10, "dauer_s": -5},
        {"position_s": True, "dauer_s": 100},
        {"position_s": 10, "dauer_s": True},
        {"position_s": "10", "dauer_s": 100},
        {"position_s": 10, "dauer_s": 100, "fertig": "ja"},
        {"position_s": 10, "dauer_s": 100, "track": -1},
        {"position_s": 10, "dauer_s": 100, "track": 1.5},
        {"position_s": 10, "dauer_s": 100, "user_id": "fremd"},  # eine Benutzerkennung kommt nie aus der Eingabe
        {"position_s": 10},
        {"dauer_s": 100},
    ],
)
async def test_set_ungueltige_eingaben(anna, felder):
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", **felder) == "invalid_format"
    assert await ok(anna, "hoerstelle/get", serie_id="rabe") == {"weiter": None, "folgen": {}}  # nichts gemerkt


async def test_set_unbekannte_serie_und_folge(anna):
    assert await fehler(anna, "hoerstelle/set", serie_id="gibtsnicht", folge="a.mp3", position_s=1, dauer_s=10) == "serie_nicht_gefunden"
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="c.mp3", position_s=1, dauer_s=10) == "folge_nicht_gefunden"
    assert await fehler(anna, "hoerstelle/set", serie_id="zwei", folge="a.mp3", position_s=1, dauer_s=10) == "folge_nicht_gefunden"  # nicht in dieser Serie
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="../a.mp3", position_s=1, dauer_s=10) == "folge_nicht_gefunden"


async def test_bekannte_dauer_gilt_und_der_gesendete_wert_wird_ignoriert(anna, bestand):
    """Der Aufrufer bestimmt die Prüfung nie selbst (G29): ``a.mp3`` ist 100 s lang, egal, was der Browser sagt."""
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=500, dauer_s=1000) == "invalid_format"
    await ok(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=102, dauer_s=5)  # 102 <= 100 + 2: gilt, obwohl der Browser 5 sagt
    r = await ok(anna, "hoerstelle/get", serie_id="rabe")
    assert r["folgen"]["a.mp3"]["dauer_s"] == 100 and r["folgen"]["a.mp3"]["fertig"] is True  # und gespeichert wird die bekannte Dauer


async def test_unbekannte_dauer_gilt_der_gesendete_wert_bis_hoechstens_24_stunden(anna, bestand):
    bestand.medieninfo.loesche_folge("rabe", "b.mp3")
    await ok(anna, "hoerstelle/set", serie_id="rabe", folge="b.mp3", position_s=5000, dauer_s=6000)
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["b.mp3"]["dauer_s"] == 6000
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="b.mp3", position_s=10, dauer_s=HOERSTELLE_DAUER_UNBEKANNT_MAX_S + 1) == "invalid_format"
    await ok(anna, "hoerstelle/set", serie_id="rabe", folge="b.mp3", position_s=10, dauer_s=HOERSTELLE_DAUER_UNBEKANNT_MAX_S)
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="b.mp3", position_s=7000, dauer_s=6000) == "invalid_format"


async def test_fertig_wird_auch_gesetzt_wenn_die_stelle_am_ende_liegt(anna):
    await setze(anna, position=97)
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["fertig"] is False
    await setze(anna, position=98)  # >= Dauer - 2
    r = (await ok(anna, "hoerstelle/get", serie_id="rabe"))
    assert r["folgen"]["a.mp3"]["fertig"] is True
    assert (r["weiter"]["anteil"], r["weiter"]["rest_s"]) == (1.0, 0)
    await setze(anna, position=5)  # noch einmal von vorn: nicht mehr fertig
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["fertig"] is False
    await setze(anna, position=5, fertig=True)  # ausdrücklich fertig
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["fertig"] is True


# --------------------------------------------------------------------------
# hoerstelle/liste
# --------------------------------------------------------------------------


async def test_liste_nur_angefangene_nicht_fertige_zuletzt_angehoert_zuerst(anna, freezer):
    await setze(anna, serie="rabe", folge="a.mp3", position=10)
    freezer.tick(timedelta(seconds=5))
    await setze(anna, serie="zwei", folge="c.mp3", position=10, dauer=50)
    r = await ok(anna, "hoerstelle/liste")
    assert [e["serie_id"] for e in r["eintraege"]] == ["zwei", "rabe"]
    e = r["eintraege"][1]
    assert e.keys() == {"serie_id", "name", "folge", "position_s", "track", "anteil", "rest_s", "zeit"}
    assert (e["name"], e["folge"], e["position_s"], e["anteil"], e["rest_s"]) == ("Der kleine Rabe", "a.mp3", 10, 0.1, 90)
    freezer.tick(timedelta(seconds=5))
    await setze(anna, serie="zwei", folge="c.mp3", position=49, dauer=50)  # fertig: fällt aus der Reihe
    assert [e["serie_id"] for e in (await ok(anna, "hoerstelle/liste"))["eintraege"]] == ["rabe"]


async def test_liste_limit(anna, freezer):
    await setze(anna, serie="rabe", folge="a.mp3", position=10)
    freezer.tick(timedelta(seconds=5))
    await setze(anna, serie="zwei", folge="c.mp3", position=10, dauer=50)
    assert [e["serie_id"] for e in (await ok(anna, "hoerstelle/liste", limit=1))["eintraege"]] == ["zwei"]
    assert await fehler(anna, "hoerstelle/liste", limit=0) == "invalid_format"
    assert await fehler(anna, "hoerstelle/liste", limit=13) == "invalid_format"
    assert len((await ok(anna, "hoerstelle/liste", limit=12))["eintraege"]) == 2


async def test_liste_ohne_hoerstelle_ist_leer(anna):
    assert await ok(anna, "hoerstelle/liste") == {"eintraege": []}


async def test_liste_laesst_gelöschte_serien_und_folgen_weg(anna, admin):
    await setze(anna, serie="rabe", folge="b.mp3", position=10, dauer=200)
    await setze(anna, serie="zwei", folge="c.mp3", position=10, dauer=50)
    await ok(admin, "serie/delete", serie_id="zwei")
    await ok(admin, "folge/delete", serie_id="rabe", folge="b.mp3")
    assert (await ok(anna, "hoerstelle/liste"))["eintraege"] == []
    assert await ok(anna, "hoerstelle/get", serie_id="rabe") == {"weiter": None, "folgen": {}}


# --------------------------------------------------------------------------
# Zwei Benutzer sehen nie die Daten des anderen
# --------------------------------------------------------------------------


async def test_zwei_benutzer_sehen_nie_die_daten_des_anderen(hass, anna, ben, admin):
    await setze(anna, serie="rabe", folge="a.mp3", position=10)
    await setze(ben, serie="zwei", folge="c.mp3", position=20, dauer=50)
    await setze(admin, serie="rabe", folge="b.mp3", position=150, dauer=200)
    # get
    a = await ok(anna, "hoerstelle/get", serie_id="rabe")
    assert set(a["folgen"]) == {"a.mp3"} and a["weiter"]["position_s"] == 10
    b_rabe = await ok(ben, "hoerstelle/get", serie_id="rabe")
    assert b_rabe == {"weiter": None, "folgen": {}}
    assert (await ok(ben, "hoerstelle/get", serie_id="zwei"))["weiter"]["position_s"] == 20
    assert await ok(anna, "hoerstelle/get", serie_id="zwei") == {"weiter": None, "folgen": {}}
    assert set((await ok(admin, "hoerstelle/get", serie_id="rabe"))["folgen"]) == {"b.mp3"}  # auch Administratoren sehen nur ihre eigenen
    assert await ok(admin, "hoerstelle/get", serie_id="zwei") == {"weiter": None, "folgen": {}}
    # liste
    assert [(e["serie_id"], e["position_s"]) for e in (await ok(anna, "hoerstelle/liste"))["eintraege"]] == [("rabe", 10)]
    assert [(e["serie_id"], e["position_s"]) for e in (await ok(ben, "hoerstelle/liste"))["eintraege"]] == [("zwei", 20)]
    assert [(e["serie_id"], e["position_s"]) for e in (await ok(admin, "hoerstelle/liste"))["eintraege"]] == [("rabe", 150)]
    # Kurzform in serien/list und serie/get, Folge-Objekt in serie/get
    for client, erwartet in ((anna, {"rabe"}), (ben, {"zwei"}), (admin, {"rabe"})):
        liste = await ok(client, "serien/list")
        assert {s["id"] for s in liste["serien"] if "hoerstelle" in s} == erwartet
    rabe_anna = await ok(anna, "serie/get", serie_id="rabe")
    rabe_ben = await ok(ben, "serie/get", serie_id="rabe")
    assert "hoerstelle" in rabe_anna and "hoerstelle" not in rabe_ben
    assert {f["name"]: f["hoerstelle"] for f in rabe_anna["folgen"] if "hoerstelle" in f} == {"a.mp3": {"position_s": 10, "fertig": False}}
    assert not any("hoerstelle" in f for f in rabe_ben["folgen"])
    # die eigene Hörstelle des einen ändert die des anderen nie
    await setze(ben, serie="rabe", folge="a.mp3", position=60)
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["position_s"] == 10
    assert (await ok(ben, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["position_s"] == 60


async def test_die_benutzerkennung_kommt_aus_der_verbindung_nie_aus_der_eingabe(hass, anna, ben):
    for befehl, felder in (
        ("hoerstelle/get", {"serie_id": "rabe"}),
        ("hoerstelle/liste", {}),
        ("hoerstelle/set", {"serie_id": "rabe", "folge": "a.mp3", "position_s": 1, "dauer_s": 100}),
    ):
        for schluessel in ("user_id", "benutzer", "nutzer_id", "benutzer_id"):
            assert await fehler(anna, befehl, **felder, **{schluessel: ben.nutzer.id}) == "invalid_format", (befehl, schluessel)
    assert ben.nutzer.id not in hass.data[DOMAIN].hoerstellen.daten


async def test_kurzform_und_sortierung_angehoert_je_benutzer(hass, hass_ws_client, anna, ben, freezer):
    await setze(anna, serie="rabe", folge="a.mp3", position=25)
    freezer.tick(timedelta(seconds=10))
    await setze(anna, serie="zwei", folge="c.mp3", position=10, dauer=50)
    await setze(ben, serie="rabe", folge="b.mp3", position=100, dauer=200)
    liste_anna = await ok(anna, "serien/list", sortierung="angehoert")
    assert [s["id"] for s in liste_anna["serien"]] == ["zwei", "rabe"]  # zuletzt angehört zuerst
    zwei = liste_anna["serien"][0]
    assert zwei["hoerstelle"].keys() == {"anteil", "rest_s", "zeit", "folge"}
    assert (zwei["hoerstelle"]["anteil"], zwei["hoerstelle"]["rest_s"], zwei["hoerstelle"]["folge"]) == (0.2, 40, "c.mp3")
    liste_ben = await ok(ben, "serien/list", sortierung="angehoert")
    assert [s["id"] for s in liste_ben["serien"]] == ["rabe", "zwei"]  # seine eigene Reihenfolge
    assert "hoerstelle" not in liste_ben["serien"][1]  # „nur wenn der Anfragende angefangen hat“
    assert liste_ben["serien"][0]["hoerstelle"]["folge"] == "b.mp3"
    # ein dritter Benutzer hat nichts gehört: alles nach Name, ohne ``hoerstelle``
    admin_liste = await ok(await _client(hass, hass_ws_client, "Cleo"), "serien/list", sortierung="angehoert")
    assert [s["id"] for s in admin_liste["serien"]] == ["rabe", "zwei"] and all("hoerstelle" not in s for s in admin_liste["serien"])
    # mit den anderen Eingaben zusammen
    assert [s["id"] for s in (await ok(anna, "serien/list", sortierung="angehoert", limit=1))["serien"]] == ["zwei"]
    assert [s["id"] for s in (await ok(anna, "serien/list", sortierung="name"))["serien"]] == ["rabe", "zwei"]


# --------------------------------------------------------------------------
# Schreiben: gesammelt nach 60 Sekunden, Neustart
# --------------------------------------------------------------------------


async def _zeit_vor(hass, sekunden: float) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=sekunden))
    await hass.async_block_till_done()


async def test_auf_die_platte_erst_nach_60_sekunden_und_gesammelt(hass, anna, hass_storage):
    assert HOERSTELLE_SPEICHER_VERZOEGERUNG_S == 60
    await setze(anna, position=10)
    await setze(anna, position=20)
    await setze(anna, position=30)
    await hass.async_block_till_done()
    assert KEY not in hass_storage  # im Speicher sofort, auf der Platte noch nichts
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["position_s"] == 30
    await _zeit_vor(hass, 59)
    assert KEY not in hass_storage
    await setze(anna, position=40)  # weitere Aufrufe verschieben den Zeitgeber nicht: bei dauerndem Hören kommt die Platte trotzdem alle 60 s dran
    await _zeit_vor(hass, 61)
    gespeichert = hass_storage[KEY]["data"]
    assert hass_storage[KEY]["version"] == 1
    (nutzer,) = gespeichert.values()
    assert nutzer["rabe"]["folgen"]["a.mp3"]["p"] == 40  # ein Schreibvorgang mit dem letzten Stand
    assert nutzer["rabe"]["folge"] == "a.mp3" and nutzer["rabe"]["zeit"].endswith("Z")
    assert nutzer["rabe"]["folgen"]["a.mp3"].keys() == {"p", "d", "t", "fertig", "track"}  # Form nach Vertrag W, 14.6
    assert nutzer["rabe"]["folgen"]["a.mp3"]["d"] == 100 and nutzer["rabe"]["folgen"]["a.mp3"]["fertig"] is False
    # der nächste Schreibvorgang wird mit der nächsten Änderung geplant
    await setze(anna, position=50)
    await hass.async_block_till_done()
    assert next(iter(hass_storage[KEY]["data"].values()))["rabe"]["folgen"]["a.mp3"]["p"] == 40
    await _zeit_vor(hass, 61)
    assert next(iter(hass_storage[KEY]["data"].values()))["rabe"]["folgen"]["a.mp3"]["p"] == 50


async def test_store_ueberlebt_den_neustart_von_ha(hass, anna, ben, hass_storage, starte_integration):
    await setze(anna, position=33)
    await setze(ben, serie="zwei", folge="c.mp3", position=7, dauer=50)
    hub_alt = hass.data[DOMAIN]
    # HA wird beendet: die Integration schreibt zuletzt (die 60 Sekunden sind noch nicht um)
    assert KEY not in hass_storage
    await hass.config_entries.async_unload(hub_alt.entry.entry_id)
    await hass.async_block_till_done()
    assert KEY in hass_storage
    assert {u: set(s) for u, s in hass_storage[KEY]["data"].items()} == {anna.nutzer.id: {"rabe"}, ben.nutzer.id: {"zwei"}}
    # und beim nächsten Start sind die Stellen wieder da
    assert await hass.config_entries.async_setup(hub_alt.entry.entry_id)
    await hass.async_block_till_done()
    hub_neu = hass.data[DOMAIN]
    assert hub_neu is not hub_alt
    await fertig(hass, hub_neu)
    assert hub_neu.hoerstellen.daten[anna.nutzer.id]["rabe"]["folgen"]["a.mp3"]["p"] == 33
    assert hub_neu.hoerstellen.daten[ben.nutzer.id]["zwei"]["folgen"]["c.mp3"]["p"] == 7


async def test_laden_nimmt_nur_die_form_und_kaputtes_stoert_nicht(hass, bestand):
    neu = Hoerstellen(bestand)
    neu._store = type("S", (), {"async_load": staticmethod(lambda: _roh({
        "u1": {"rabe": {"zeit": "2026-11-14T10:00:00Z", "folge": "a.mp3", "folgen": {
            "a.mp3": {"p": 5, "d": 100, "t": "2026-11-14T10:00:00Z", "fertig": False, "track": 0},
            "kaputt": {"p": "x"}, "b.mp3": {"p": -1, "d": 10, "t": "z", "fertig": False}}},
            "leer": {"zeit": "z", "folge": "x", "folgen": {}}, "nix": 5},
        "u2": "kein objekt", 7: {}}))})()
    await neu.async_laden()
    assert neu.daten == {"u1": {"rabe": {"zeit": "2026-11-14T10:00:00Z", "folge": "a.mp3", "folgen": {
        "a.mp3": {"p": 5, "d": 100, "t": "2026-11-14T10:00:00Z", "fertig": False, "track": 0}}}}}
    neu._store = type("S", (), {"async_load": staticmethod(lambda: _roh(None))})()
    await neu.async_laden()
    assert neu.daten == {}


async def _roh(wert):
    return wert


# --------------------------------------------------------------------------
# Obergrenzen, Aufräumen
# --------------------------------------------------------------------------


async def test_obergrenzen_die_aeltesten_fallen_weg(hass, anna, bestand, monkeypatch, freezer):
    monkeypatch.setattr(hoerstelle_modul, "HOERSTELLE_MAX_FOLGEN", 2)
    await setze(anna, folge="a.mp3", position=1)
    freezer.tick(timedelta(seconds=5))
    await setze(anna, folge="b.mp3", position=1, dauer=200)
    freezer.tick(timedelta(seconds=5))
    await setze(anna, folge="Buch", track=0, position=1, dauer=100)  # die dritte: a.mp3 (die älteste) fällt weg
    r = await ok(anna, "hoerstelle/get", serie_id="rabe")
    assert set(r["folgen"]) == {"b.mp3", "Buch"} and r["weiter"]["folge"] == "Buch"
    monkeypatch.setattr(hoerstelle_modul, "HOERSTELLE_MAX_SERIEN", 1)
    freezer.tick(timedelta(seconds=5))
    await setze(anna, serie="zwei", folge="c.mp3", position=1, dauer=50)  # die zweite Serie: die ältere fällt weg
    assert await ok(anna, "hoerstelle/get", serie_id="rabe") == {"weiter": None, "folgen": {}}
    assert (await ok(anna, "hoerstelle/get", serie_id="zwei"))["weiter"]["folge"] == "c.mp3"


async def test_beim_start_fallen_unbekannte_benutzer_geloeschte_serien_und_folgen_weg(hass, anna, bestand, nas):
    hub = bestand
    await setze(anna, serie="rabe", folge="a.mp3", position=10)
    await setze(anna, serie="rabe", folge="b.mp3", position=10, dauer=200)
    await setze(anna, serie="zwei", folge="c.mp3", position=10, dauer=50)
    jetzt = "2026-11-14T10:00:00Z"
    hub.hoerstellen.daten["geloeschter-benutzer"] = {"rabe": {"zeit": jetzt, "folge": "a.mp3", "folgen": {
        "a.mp3": {"p": 1, "d": 100, "t": jetzt, "fertig": False, "track": 0}}}}
    # Serie ``zwei`` und Folge ``b.mp3`` verschwinden (ohne Befehl, etwa von Hand auf dem NAS)
    import shutil

    shutil.rmtree(nas.medien / "zwei")
    (nas.medien / "rabe" / "b.mp3").unlink()
    nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3", "Buch"])
    # NAS bei der Prüfung nicht erreichbar: nichts wird gelöscht außer unbekannten Benutzern
    hub.medien.geprueft_am = None
    await hub.hoerstellen.bereinige_beim_start()
    assert "geloeschter-benutzer" not in hub.hoerstellen.daten
    assert set(hub.hoerstellen.daten[anna.nutzer.id]) == {"rabe", "zwei"} and set(hub.hoerstellen.daten[anna.nutzer.id]["rabe"]["folgen"]) == {"a.mp3", "b.mp3"}
    # nach gelungener Prüfung der Freigabe
    await hub.medien.pruefen()
    await hub.hoerstellen.bereinige_beim_start()
    assert set(hub.hoerstellen.daten[anna.nutzer.id]) == {"rabe"}
    assert set(hub.hoerstellen.daten[anna.nutzer.id]["rabe"]["folgen"]) == {"a.mp3"}
    assert hub.hoerstellen.daten[anna.nutzer.id]["rabe"]["folge"] == "a.mp3"


# --------------------------------------------------------------------------
# Rechte und Mengen
# --------------------------------------------------------------------------


async def test_rechte_lesen_und_alltag_fuer_jeden_angemeldeten_benutzer(anna):
    assert (await senden(anna, "hoerstelle/get", serie_id="rabe"))["success"] is True
    assert (await senden(anna, "hoerstelle/liste"))["success"] is True
    assert (await senden(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=1, dauer_s=100))["success"] is True


async def test_sechzig_aufrufe_je_minute_fuer_nicht_administratoren(hass, anna, admin, freezer):
    assert HOERSTELLE_SCHREIBEN_JE_MINUTE == 60  # seit 16.11. (Stufe B) 60 statt 30; Vertrag W, Nr. 41 und 15.3
    for i in range(HOERSTELLE_SCHREIBEN_JE_MINUTE):
        await setze(anna, position=i % 90)
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=1, dauer_s=100) == "zu_viele_aenderungen"
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["position_s"] == (HOERSTELLE_SCHREIBEN_JE_MINUTE - 1) % 90  # der abgelehnte zählt nicht
    for _ in range(HOERSTELLE_SCHREIBEN_JE_MINUTE + 3):  # Administratoren sind ausgenommen
        await setze(admin, position=5)
    freezer.tick(timedelta(seconds=61))
    await setze(anna, position=77)
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["position_s"] == 77


async def test_lesen_zaehlt_nicht_zur_menge(anna):
    for _ in range(HOERSTELLE_SCHREIBEN_JE_MINUTE + 5):
        await ok(anna, "hoerstelle/get", serie_id="rabe")
        await ok(anna, "hoerstelle/liste")
    await setze(anna, position=1)  # die Lesezugriffe haben den Zähler nicht berührt


async def test_hello_sagt_reinhoeren_zu(anna):
    h = await ok(anna, "hello", v=1)
    assert "reinhoeren" in h["faehigkeiten"]
