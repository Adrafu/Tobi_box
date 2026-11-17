"""Paket B3 „Gehört“: die Befehle 50 bis 56, Felder, Sortierungen, Filter, Ereignisse, Export, Löschen und die Reste aus Stufe A (Backend).

Verträge: ``docs/protocol/ha-websocket-v1.md`` 3.14, 4.9, 4.10, 15; Design ``docs/designs/gehoert.md`` 6 und 11. Die Hördaten werden direkt in die Datenbank
geschrieben (die Aufnahme selbst und die Zählregel prüfen ``test_gehoert.py`` und ``test_gehoert_regeln.py``).

Die Uhr steht auf dem 17.11.2026, 12:00 UTC; die Zeitzone von HA ist Europe/Berlin (Winterzeit, +1 Stunde).
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.tobibox.const import FAVORITEN_JE_MINUTE
from custom_components.tobibox.gehoert import Zeile

from .conftest import ereignis_arten
from .test_gehoert import _client, nachricht, quittungen, sitz, zeit_vergeht, zeilen
from .test_websocket_api import fehler, ok


def utc(j: int, m: int, t: int, h: int = 0, mi: int = 0, s: int = 0) -> int:
    return int(datetime(j, m, t, h, mi, s, tzinfo=UTC).timestamp())


def z(n: int, beginn: int, dauer: int = 100, *, serie: str = "rabe", folge: str = "a.mp3", ende: str = "pause", folge_dauer: int | None = 100, datum: str = "sicher") -> Zeile:
    """Eine Sitzung ``n``; ``dauer`` ist Hörzeit und Länge zugleich. Bei unbekanntem Datum ist ``ende_um`` relativ (Dauer)."""
    return Zeile(f"00000000-0000-4000-8000-{n:012d}", serie, folge, folge_dauer, beginn, beginn + dauer if datum != "unbekannt" else dauer, datum, dauer, ende)


async def fuelle(hub, quelle: str, *liste: Zeile) -> None:
    await hub.gehoert.nimm_zeilen_auf(quelle, list(liste))


@pytest.fixture
async def bestand(hass, integration, nas, lege_mp3, freezer):
    """Serien ``rabe`` (a.mp3 „Eins“, b.mp3, c.mp3) und ``zwei`` (d.mp3, e.mp3); Boxen ``box1`` und ``box2``."""
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3", "b.mp3", "c.mp3"], folgen_info={"a.mp3": {"anzeige": "Eins", "nummer": 1}})
    for n in ("a.mp3", "b.mp3", "c.mp3"):
        lege_mp3(pfad / n)
    pfad2 = nas.serie("zwei", "zwei", "Zweite Serie", ["d.mp3", "e.mp3"])
    for n in ("d.mp3", "e.mp3"):
        lege_mp3(pfad2 / n)
    await integration.medien.pruefen()
    await integration.dauer.warte_auf_ende()
    await hass.config.async_set_time_zone("Europe/Berlin")  # erst jetzt: die Uhr einzufrieren, bevor die Integration läuft, hält ihre Zeitgeber an
    freezer.move_to("2026-11-17 12:00:00+00:00")
    return integration


@pytest.fixture
async def api(hass, bestand, hass_ws_client):
    return await hass_ws_client(hass)


@pytest.fixture
async def anna(hass, bestand, hass_ws_client):
    return await _client(hass, hass_ws_client, "Anna")


@pytest.fixture
async def daten(bestand, anna):
    """Gemischte Hördaten: zwei Boxen, eine Person, eine gelöschte Serie."""
    b1, b2, a = "box:box1", "box:box2", f"benutzer:{anna.nutzer.id}"
    await fuelle(bestand, b1, z(1, utc(2026, 11, 16, 10), 100, folge="a.mp3"), z(2, utc(2026, 11, 17, 8), 100, folge="a.mp3", ende="ende_der_folge"))
    await fuelle(bestand, b1, z(3, utc(2026, 11, 15, 9), 50, folge="b.mp3", folge_dauer=200))
    await fuelle(bestand, b2, z(4, utc(2026, 11, 10, 9), 300, serie="zwei", folge="d.mp3", ende="ende_der_folge", folge_dauer=300))
    await fuelle(bestand, a, z(5, utc(2026, 11, 17, 7), 60, serie="zwei", folge="e.mp3", folge_dauer=None))
    await fuelle(bestand, b1, z(6, utc(2026, 11, 12, 9), 40, serie="weg1", folge="x.mp3"))
    await fuelle(bestand, b2, z(7, utc(2026, 11, 12, 10), 20, serie="weg2", folge="y.mp3"))
    return bestand


def zeilen_nach(antwort: dict[str, Any], schluessel: str) -> dict[Any, dict[str, Any]]:
    return {r[schluessel]: r for r in antwort["zeilen"]}


# --------------------------------------------------------------------------------------------
# Fähigkeiten und Themen
# --------------------------------------------------------------------------------------------


async def test_hello_sagt_gehoert_und_favoriten_zu(api, bestand):
    f = (await ok(api, "hello", v=1))["faehigkeiten"]
    assert "gehoert" in f and "favoriten" in f


async def test_ohne_datenbank_keine_faehigkeit_und_befehle_50_bis_54_unbekannt(hass, api, bestand):
    gehoert = bestand.gehoert
    db, gehoert.db, gehoert.verfuegbar = gehoert.db, None, False
    try:
        f = (await ok(api, "hello", v=1))["faehigkeiten"]
        assert "gehoert" not in f and "favoriten" in f
        assert await fehler(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles") == "unknown_command"
        assert await fehler(api, "gehoert/zuletzt") == "unknown_command"
        assert await fehler(api, "technik/verlauf", box="box1", von="2026-11-01", bis="2026-11-02") == "unknown_command"
        assert await fehler(api, "gehoert/exportieren", quelle="alle") == "unknown_command"
        assert await fehler(api, "gehoert/loeschen", quelle="alle", trocken=True) == "unknown_command"
        # Listen gehen weiter, ohne das Feld
        liste = await ok(api, "serien/list")
        assert "zuletzt_gehoert_am" not in liste["serien"][0] and "favorit" in liste["serien"][0]
        # Standard-Abo ohne das Thema ``gehoert``
        await api.send_json_auto_id({"type": "tobibox/subscribe"})
        assert (await api.receive_json())["success"] is True
        themen = [(await api.receive_json())["event"]["thema"] for _ in range(9)]
        assert "gehoert" not in themen and "favoriten" in themen
    finally:
        gehoert.db, gehoert.verfuegbar = db, True


# --------------------------------------------------------------------------------------------
# Befehl 50: Eingabe
# --------------------------------------------------------------------------------------------

NACH_EIN = [["wer"], ["serie"], ["tag"], ["woche"], ["monat"], ["stunde"]]
NACH_ZWEI = [["wer", "tag"], ["tag", "wer"], ["serie", "wer"], ["wer", "serie"], ["serie", "tag"], ["woche", "serie"], ["monat", "wer"], ["stunde", "serie"], ["stunde", "wer"]]


@pytest.mark.parametrize("nach", NACH_EIN + NACH_ZWEI, ids=lambda n: "+".join(n))
async def test_50_erlaubte_nach_kombinationen(api, daten, nach):
    r = await ok(api, "gehoert/zusammenfassung", nach=nach, zeitraum="woche")
    assert r["zeilen"] and set(nach) <= set(r["zeilen"][0])
    assert r["summe"]["sekunden"] == sum(x["sekunden"] for x in r["zeilen"])  # ohne limit: die Summe ist die Summe der Zeilen
    assert (r["zeitzone"], r["bis"]) == ("Europe/Berlin", "2026-11-17")


async def test_50_folge_nur_mit_serie_id(api, daten):
    r = await ok(api, "gehoert/zusammenfassung", nach=["folge"], serie_id="rabe", zeitraum="alles")
    assert {x["folge"] for x in r["zeilen"]} == {"a.mp3", "b.mp3"}
    r = await ok(api, "gehoert/zusammenfassung", nach=["folge", "tag"], serie_id="rabe", zeitraum="alles")
    assert all(set(x) >= {"folge", "tag"} for x in r["zeilen"])


@pytest.mark.parametrize(
    "felder",
    [
        {"nach": ["serie", "serie"], "zeitraum": "woche"},  # doppelt
        {"nach": ["tag", "woche"], "zeitraum": "woche"},  # zwei Zeitschlüssel
        {"nach": ["tag", "stunde"], "zeitraum": "woche"},
        {"nach": ["monat", "woche"], "zeitraum": "jahr"},
        {"nach": ["serie", "folge"], "zeitraum": "woche", "serie_id": "rabe"},  # nie zusammen
        {"nach": ["folge"], "zeitraum": "woche"},  # folge ohne serie_id
        {"nach": ["folge", "wer"], "zeitraum": "woche"},
        {"nach": ["wer", "serie", "tag"], "zeitraum": "woche"},  # drei
        {"nach": [], "zeitraum": "woche"},
        {"nach": ["quatsch"], "zeitraum": "woche"},
        {"nach": "serie", "zeitraum": "woche"},
        {"zeitraum": "woche"},  # ohne nach
        {"nach": ["serie"]},  # ohne Zeitraum
        {"nach": ["serie"], "zeitraum": "woche", "von": "2026-11-01", "bis": "2026-11-05"},  # beides
        {"nach": ["serie"], "von": "2026-11-01"},  # nur eines
        {"nach": ["serie"], "bis": "2026-11-05"},
        {"nach": ["serie"], "von": "2026-11-05", "bis": "2026-11-01"},  # bis vor von
        {"nach": ["serie"], "von": "2026-11-01", "bis": "2029-11-18"},  # länger als 3 Jahre
        {"nach": ["serie"], "von": "2026-13-01", "bis": "2026-13-02"},  # kein Datum
        {"nach": ["serie"], "von": "2026-1-1", "bis": "2026-1-2"},  # falsches Format
        {"nach": ["serie"], "zeitraum": "quartal"},
        {"nach": ["tag"], "zeitraum": "woche", "sortierung": "sekunden"},  # Sortierung mit Zeitschlüssel
        {"nach": ["tag"], "zeitraum": "woche", "limit": 5},  # limit mit Zeitschlüssel
        {"nach": ["serie"], "zeitraum": "woche", "limit": 0},
        {"nach": ["serie"], "zeitraum": "woche", "limit": 201},
        {"nach": ["serie"], "zeitraum": "woche", "sortierung": "name"},
        {"nach": ["serie"], "zeitraum": "woche", "unbekannt": 1},
    ],
)
async def test_50_verbotene_eingaben_sind_invalid_format(api, daten, felder):
    assert await fehler(api, "gehoert/zusammenfassung", **felder) == "invalid_format"


async def test_50_drei_jahre_genau_gehen(api, daten):
    r = await ok(api, "gehoert/zusammenfassung", nach=["monat"], von="2026-11-01", bis="2029-11-01")
    assert len(r["zeilen"]) == 37


async def test_50_wer_ungueltig(api, daten, anna):
    for wer in ("quatsch", "boxen", "reinhoeren", "box:", "box:box9", "box:BOX 1", "benutzer:", "benutzer:gibtsnicht", "benutzer:a b", "alle_boxen "):
        assert await fehler(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", wer=wer) == "wer_ungueltig", wer
    assert await fehler(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", wer=5) == "invalid_format"
    for wer in ("alle", "alle_boxen", "box:box1", "box:box2", f"benutzer:{anna.nutzer.id}"):
        await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", wer=wer)


async def test_50_benutzer_ohne_daten_aber_in_ha_ist_gueltig_mit_nullen(api, daten, hass):
    neu = await hass.auth.async_create_user("Ben", group_ids=["system-users"])
    r = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", wer=f"benutzer:{neu.id}")
    assert r["zeilen"] == [] and r["summe"] == {"sekunden": 0, "mal": 0, "fertig": 0}


async def test_50_serie_nicht_gefunden(api, daten):
    assert await fehler(api, "gehoert/zusammenfassung", nach=["tag"], zeitraum="woche", serie_id="gibtsnicht") == "serie_nicht_gefunden"
    assert await fehler(api, "gehoert/zusammenfassung", nach=["folge"], zeitraum="woche", serie_id="weg1") == "serie_nicht_gefunden"  # gelöschte Serien haben keine Aufteilung


# --------------------------------------------------------------------------------------------
# Befehl 50: Rangliste
# --------------------------------------------------------------------------------------------


async def test_50_rangliste_nach_serie_mit_mal_fertig_und_gesamt(api, daten):
    r = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles")
    nach_serie = {x["serie"]: x for x in r["zeilen"]}
    rabe = nach_serie["rabe"]
    assert (rabe["name"], rabe["geloescht"]) == ("Der kleine Rabe", False)
    # a.mp3: zwei Mal (Pause über 30 Minuten), 200 s, an der zweiten fertig; b.mp3: 50 s
    assert (rabe["sekunden"], rabe["mal"], rabe["fertig"]) == (250, 3, 1)
    assert (rabe["folgen_fertig"], rabe["folgen_gesamt"]) == (1, 3)
    zwei = nach_serie["zwei"]
    assert (zwei["sekunden"], zwei["mal"], zwei["fertig"], zwei["folgen_fertig"], zwei["folgen_gesamt"]) == (360, 2, 1, 1, 2)
    # alle gelöschten Serien in einer Zeile mit serie = null
    weg = nach_serie[None]
    assert (weg["geloescht"], weg["name"], weg["sekunden"], weg["mal"], weg["folgen_fertig"], weg["folgen_gesamt"]) == (True, "Gelöscht", 60, 2, 0, 0)
    assert [x["serie"] for x in r["zeilen"]] == ["zwei", "rabe", None]  # nach Hörzeit absteigend
    assert r["summe"] == {"sekunden": 670, "mal": 7, "fertig": 2}
    assert r["weitere"] is False
    assert (r["von"], r["bis"], r["zeitzone"]) == ("2026-11-10", "2026-11-17", "Europe/Berlin")


async def test_50_sortierung_mal_gleichstand_nach_name_limit_und_weitere(api, daten):
    r = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", sortierung="mal")
    assert [x["serie"] for x in r["zeilen"]] == ["rabe", None, "zwei"]  # 3, 2, 2 Mal; Gleichstand nach Name: „Gelöscht“ vor „Zweite Serie“
    r = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", limit=1)
    assert [x["serie"] for x in r["zeilen"]] == ["zwei"] and r["weitere"] is True
    assert r["summe"]["sekunden"] == 670  # die Summe gilt für den ganzen Filter, nicht nur für die gelieferten Zeilen
    r = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", limit=3)
    assert r["weitere"] is False


async def test_50_gleichstand_nach_name(api, bestand, anna):
    await fuelle(bestand, "box:box1", z(1, utc(2026, 11, 16, 10), 100, serie="zwei", folge="d.mp3"), z(2, utc(2026, 11, 16, 12), 100, serie="rabe", folge="a.mp3"))
    r = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles")
    assert [x["name"] for x in r["zeilen"]] == ["Der kleine Rabe", "Zweite Serie"]


async def test_50_aufteilung_einer_serie_nach_folgen_und_fertig_nur_heute_vorhandene_folgen(api, daten, bestand, nas):
    r = await ok(api, "gehoert/zusammenfassung", nach=["folge"], serie_id="rabe", zeitraum="alles")
    assert [(x["folge"], x["sekunden"], x["mal"], x["fertig"]) for x in r["zeilen"]] == [("a.mp3", 200, 2, 1), ("b.mp3", 50, 1, 0)]
    assert "folgen_fertig" not in r["zeilen"][0]  # mit ``folge`` in ``nach`` nie
    # eine fertig gehörte Folge, die es nicht mehr gibt, zählt in „17/20“ nicht mit
    await fuelle(bestand, "box:box1", z(30, utc(2026, 11, 14, 9), 100, serie="rabe", folge="alt.mp3", ende="ende_der_folge"))
    r = await ok(api, "gehoert/zusammenfassung", nach=["serie"], serie_id="rabe", zeitraum="alles")
    assert (r["zeilen"][0]["fertig"], r["zeilen"][0]["folgen_fertig"], r["zeilen"][0]["folgen_gesamt"]) == (2, 1, 3)


async def test_50_serie_id_im_zeitverlauf_traegt_folgen_fertig_und_gesamt(api, daten):
    r = await ok(api, "gehoert/zusammenfassung", nach=["tag"], serie_id="rabe", zeitraum="woche")
    heute = r["zeilen"][-1]
    assert (heute["tag"], heute["sekunden"], heute["folgen_fertig"], heute["folgen_gesamt"]) == ("2026-11-17", 100, 1, 3)
    assert r["zeilen"][0]["folgen_fertig"] == 0 and r["zeilen"][0]["folgen_gesamt"] == 3  # auch in Zeilen ohne Daten


async def test_50_wer_filter_und_wer_auswahl(api, daten, anna, hass):
    alle = await ok(api, "gehoert/zusammenfassung", nach=["wer"], zeitraum="alles")
    assert {x["wer"]: x["sekunden"] for x in alle["zeilen"]} == {"box:box1": 290, "box:box2": 320, "benutzer:" + anna.nutzer.id: 60}
    boxen = await ok(api, "gehoert/zusammenfassung", nach=["wer"], zeitraum="alles", wer="alle_boxen")
    assert {x["wer"] for x in boxen["zeilen"]} == {"box:box1", "box:box2"}
    eine = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", wer="box:box1")
    assert {x["serie"]: x["sekunden"] for x in eine["zeilen"]} == {"rabe": 250, None: 40}
    person = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", wer="benutzer:" + anna.nutzer.id)
    assert [(x["serie"], x["sekunden"]) for x in person["zeilen"]] == [("zwei", 60)]
    assert person["summe"]["sekunden"] == 60
    # wer_auswahl: unabhängig vom Filter; erst Boxen (Anzeigename), dann Personen
    assert alle["wer_auswahl"] == person["wer_auswahl"] == [
        {"wer": "box:box1", "name": "box1", "art": "box"},
        {"wer": "box:box2", "name": "box2", "art": "box"},
        {"wer": "benutzer:" + anna.nutzer.id, "name": "Anna", "art": "person"},
    ]


async def test_50_geloeschter_benutzer_ist_frueherer_benutzer_und_bleibt_in_alle(api, daten, bestand, hass):
    zoe = await hass.auth.async_create_user("Zoe", group_ids=["system-users"])
    await fuelle(bestand, f"benutzer:{zoe.id}", z(20, utc(2026, 11, 17, 6), 33, serie="zwei", folge="e.mp3"))
    assert {"wer": f"benutzer:{zoe.id}", "name": "Zoe", "art": "person"} in (await ok(api, "gehoert/zusammenfassung", nach=["wer"], zeitraum="alles"))["wer_auswahl"]
    await hass.auth.async_remove_user(zoe)
    r = await ok(api, "gehoert/zusammenfassung", nach=["wer"], zeitraum="alles")
    assert {"wer": f"benutzer:{zoe.id}", "name": "Früherer Benutzer", "art": "person"} in r["wer_auswahl"]
    assert r["summe"]["sekunden"] == 670 + 33  # gelöschte Benutzer bleiben in „Alle“
    await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles", wer=f"benutzer:{zoe.id}")  # zu ihm gibt es Daten: gültig


async def test_50_box_mit_alten_daten_ist_gueltig_und_in_der_auswahl(api, daten, bestand):
    await fuelle(bestand, "box:alt", z(40, utc(2026, 11, 1, 9), 10))
    r = await ok(api, "gehoert/zusammenfassung", nach=["wer"], zeitraum="alles", wer="box:alt")
    assert [x["wer"] for x in r["zeilen"]] == ["box:alt"]
    assert "box:alt" in [a["wer"] for a in r["wer_auswahl"]]


# --------------------------------------------------------------------------------------------
# Befehl 50: Zeiträume
# --------------------------------------------------------------------------------------------


async def test_50_woche_monat_jahr_sind_kalendertage_einschliesslich_heute(api, bestand):
    heute = utc(2026, 11, 17, 8)
    zeitpunkte = {1: heute, 2: heute - 6 * 86400, 3: heute - 7 * 86400, 4: heute - 29 * 86400, 5: heute - 30 * 86400, 6: heute - 364 * 86400, 7: heute - 365 * 86400}
    await fuelle(bestand, "box:box1", *(z(n, t, 10 * n, folge=f"{n}.mp3") for n, t in zeitpunkte.items()))
    for zeitraum, erwartet in (("woche", {1, 2}), ("monat", {1, 2, 3, 4}), ("jahr", {1, 2, 3, 4, 5, 6}), ("alles", set(zeitpunkte))):
        r = await ok(api, "gehoert/zusammenfassung", nach=["folge"], serie_id="rabe", zeitraum=zeitraum)
        assert {int(x["folge"][0]) for x in r["zeilen"]} == erwartet, zeitraum
    r = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="jahr")
    assert (r["von"], r["bis"]) == ("2025-11-18", "2026-11-17")


async def test_50_zeitraum_in_der_zeitzone_von_ha_mit_sommerzeit(hass, api, bestand, freezer):
    freezer.move_to("2026-03-29 22:30:00+00:00")  # in Berlin schon der 30. März, 00:30 (Sommerzeit seit 01:00 UTC am 29.)
    await fuelle(
        bestand, "box:box1",
        z(1, utc(2026, 3, 23, 22, 30), 10, folge="1.mp3"),  # 23:30 am 23.: sieben Tage vor „heute“, nicht mehr in der Woche
        z(2, utc(2026, 3, 23, 23, 30), 20, folge="2.mp3"),  # 00:30 am 24.: der erste Tag der Woche
        z(3, utc(2026, 3, 29, 21, 30), 30, folge="3.mp3"),  # 23:30 am 29. (Sommerzeit)
        z(4, utc(2026, 3, 29, 22, 20), 40, folge="4.mp3"),  # 00:20 am 30.
    )
    r = await ok(api, "gehoert/zusammenfassung", nach=["tag"], zeitraum="woche")
    assert (r["von"], r["bis"]) == ("2026-03-24", "2026-03-30")
    assert [(x["tag"], x["sekunden"]) for x in r["zeilen"]] == [
        ("2026-03-24", 20), ("2026-03-25", 0), ("2026-03-26", 0), ("2026-03-27", 0), ("2026-03-28", 0), ("2026-03-29", 30), ("2026-03-30", 40)
    ]
    st = await ok(api, "gehoert/zusammenfassung", nach=["stunde"], zeitraum="woche")
    assert {x["stunde"]: x["sekunden"] for x in st["zeilen"] if x["sekunden"]} == {0: 20 + 40, 23: 30}  # 00:30 und 00:20 Ortszeit; 23:30 CEST, nicht 21 (UTC)


async def test_50_von_bis_einschliesslich_und_ohne_unbekanntes_datum(api, daten, bestand):
    await fuelle(bestand, "box:box1", z(50, 0, 77, folge="u.mp3", datum="unbekannt"))
    r = await ok(api, "gehoert/zusammenfassung", nach=["serie"], von="2026-11-10", bis="2026-11-10")
    assert [(x["serie"], x["sekunden"]) for x in r["zeilen"]] == [("zwei", 300)]
    assert r["summe"]["sekunden"] == 300 and (r["von"], r["bis"]) == ("2026-11-10", "2026-11-10")
    woche = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="woche")
    assert woche["summe"]["sekunden"] == 370  # 100+100+50+60+40+20: ohne die 77 s unbekannten Datums
    # „Alles“ zählt das unbekannte Datum, auch in der Rangliste
    alles = await ok(api, "gehoert/zusammenfassung", nach=["serie"], zeitraum="alles")
    assert alles["summe"]["sekunden"] == 670 + 77
    # eine Zeitreihe braucht ein Datum: das unbekannte fällt heraus
    reihe = await ok(api, "gehoert/zusammenfassung", nach=["tag"], zeitraum="alles")
    assert reihe["summe"]["sekunden"] == 670 and sum(x["sekunden"] for x in reihe["zeilen"]) == 670


# --------------------------------------------------------------------------------------------
# Befehl 50: Zeitreihen
# --------------------------------------------------------------------------------------------


async def test_50_tag_lueckenlos_aufsteigend(api, daten):
    r = await ok(api, "gehoert/zusammenfassung", nach=["tag"], zeitraum="monat")
    assert [x["tag"] for x in r["zeilen"]] == [(datetime(2026, 10, 19) + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]
    d = {x["tag"]: x for x in r["zeilen"]}
    assert (d["2026-11-17"]["sekunden"], d["2026-11-17"]["mal"], d["2026-11-17"]["fertig"]) == (160, 2, 1)
    assert (d["2026-11-16"]["sekunden"], d["2026-11-16"]["mal"]) == (100, 1)
    assert d["2026-11-13"] == {"tag": "2026-11-13", "sekunden": 0, "mal": 0, "fertig": 0}


async def test_50_tag_ueber_400_tage_ist_invalid_format_alles_ab_dem_ersten_tag(api, bestand):
    await fuelle(bestand, "box:box1", z(1, utc(2025, 9, 1, 9), 10), z(2, utc(2026, 11, 1, 9), 10))
    assert await fehler(api, "gehoert/zusammenfassung", nach=["tag"], zeitraum="alles") == "invalid_format"  # 442 Tage
    assert await fehler(api, "gehoert/zusammenfassung", nach=["tag"], von="2025-01-01", bis="2026-02-05") == "invalid_format"  # 401 Tage
    ok401 = await ok(api, "gehoert/zusammenfassung", nach=["tag"], von="2025-01-01", bis="2026-02-04")  # 400 Tage
    assert len(ok401["zeilen"]) == 400
    w = await ok(api, "gehoert/zusammenfassung", nach=["woche"], zeitraum="alles")
    assert w["zeilen"][0]["woche"] == "2025-W36" and w["von"] == "2025-09-01"
    m = await ok(api, "gehoert/zusammenfassung", nach=["monat"], zeitraum="alles")
    assert [x["monat"] for x in m["zeilen"]] == [f"2025-{i:02d}" for i in (9, 10, 11, 12)] + [f"2026-{i:02d}" for i in range(1, 12)]
    assert m["zeilen"][0]["sekunden"] == 10 and m["zeilen"][-1]["sekunden"] == 10


async def test_50_alles_ohne_daten_ist_heute(api, bestand):
    r = await ok(api, "gehoert/zusammenfassung", nach=["tag"], zeitraum="alles")
    assert (r["von"], r["bis"]) == ("2026-11-17", "2026-11-17") and r["zeilen"] == [{"tag": "2026-11-17", "sekunden": 0, "mal": 0, "fertig": 0}]


async def test_50_woche_und_monat_schluessel_iso_woche_und_kalendermonat(api, bestand):
    await fuelle(
        bestand, "box:box1",
        z(1, utc(2026, 12, 27, 9), 10, folge="1.mp3"),  # Sonntag, ISO-Woche 52
        z(2, utc(2026, 12, 28, 9), 20, folge="2.mp3"),  # Montag, ISO-Woche 53
        z(3, utc(2027, 1, 3, 9), 30, folge="3.mp3"),  # Sonntag, noch Woche 53 des Jahres 2026
        z(4, utc(2027, 1, 4, 9), 40, folge="4.mp3"),  # Montag, Woche 1 des Jahres 2027
    )
    r = await ok(api, "gehoert/zusammenfassung", nach=["woche"], von="2026-12-21", bis="2027-01-10")
    assert [(x["woche"], x["sekunden"]) for x in r["zeilen"]] == [("2026-W52", 10), ("2026-W53", 50), ("2027-W01", 40)]
    m = await ok(api, "gehoert/zusammenfassung", nach=["monat"], von="2026-12-01", bis="2027-01-31")
    assert [(x["monat"], x["sekunden"]) for x in m["zeilen"]] == [("2026-12", 30), ("2027-01", 70)]


async def test_50_stunde_immer_24_zeilen(api, daten):
    r = await ok(api, "gehoert/zusammenfassung", nach=["stunde"], zeitraum="alles")
    assert [x["stunde"] for x in r["zeilen"]] == list(range(24))
    d = {x["stunde"]: x["sekunden"] for x in r["zeilen"] if x["sekunden"]}
    assert d == {8: 60, 9: 100, 10: 50 + 300 + 40, 11: 100 + 20}  # Ortszeit (Winterzeit): 09:00 UTC ist 10 Uhr
    leer = await ok(api, "gehoert/zusammenfassung", nach=["stunde"], von="2020-01-01", bis="2020-01-02")
    assert len(leer["zeilen"]) == 24 and not any(x["sekunden"] for x in leer["zeilen"])


async def test_50_zeit_mal_wer_volles_raster_mit_nullen_und_400er_grenze(api, daten, anna):
    r = await ok(api, "gehoert/zusammenfassung", nach=["tag", "wer"], zeitraum="woche")
    quellen = [a["wer"] for a in r["wer_auswahl"]]
    assert len(r["zeilen"]) == 7 * 3
    assert [(x["tag"], x["wer"]) for x in r["zeilen"]][:3] == [("2026-11-11", q) for q in quellen]  # erst die Zeit, dann die Quellen
    assert next(x for x in r["zeilen"] if (x["tag"], x["wer"]) == ("2026-11-17", "box:box1"))["sekunden"] == 100
    assert next(x for x in r["zeilen"] if (x["tag"], x["wer"]) == ("2026-11-17", "box:box2")) == {"tag": "2026-11-17", "wer": "box:box2", "sekunden": 0, "mal": 0, "fertig": 0}
    # die Reihenfolge der Schlüssel folgt ``nach``
    r2 = await ok(api, "gehoert/zusammenfassung", nach=["wer", "tag"], zeitraum="woche")
    assert list(r2["zeilen"][0])[:2] == ["wer", "tag"]
    # 3 Quellen × 134 Tage = 402 Zeilen: zu viel
    assert await fehler(api, "gehoert/zusammenfassung", nach=["tag", "wer"], von="2026-01-01", bis="2026-05-14") == "invalid_format"
    ok_ = await ok(api, "gehoert/zusammenfassung", nach=["tag", "wer"], von="2026-01-01", bis="2026-05-13")  # 133 × 3 = 399
    assert len(ok_["zeilen"]) == 399
    # nur eine Box gewählt: nur diese Quelle im Raster
    eine = await ok(api, "gehoert/zusammenfassung", nach=["tag", "wer"], zeitraum="woche", wer="box:box2")
    assert {x["wer"] for x in eine["zeilen"]} == {"box:box2"} and len(eine["zeilen"]) == 7


async def test_50_zeit_mal_serie_nur_vorhandene_kombinationen_sortiert(api, daten):
    r = await ok(api, "gehoert/zusammenfassung", nach=["tag", "serie"], zeitraum="woche")
    assert [(x["tag"], x["serie"], x["sekunden"]) for x in r["zeilen"]] == [
        ("2026-11-12", None, 60),
        ("2026-11-15", "rabe", 50),
        ("2026-11-16", "rabe", 100),
        ("2026-11-17", "rabe", 100),
        ("2026-11-17", "zwei", 60),
    ]
    assert r["zeilen"][0]["geloescht"] is True and r["zeilen"][1]["name"] == "Der kleine Rabe"


async def test_50_zeit_mal_serie_ueber_400_zeilen_ist_invalid_format(api, bestand):
    # 201 Tage mit je zwei Folgen: das Raster (201 Tage) ist klein genug, aber es gibt 402 Kombinationen
    await fuelle(bestand, "box:box1", *(z(2 * i + k, utc(2026, 1, 1, 9) + i * 86400, 10, folge=f"{k}.mp3") for i in range(201) for k in (1, 2)))
    assert await fehler(api, "gehoert/zusammenfassung", nach=["tag", "folge"], serie_id="rabe", von="2026-01-01", bis="2026-07-20") == "invalid_format"
    r = await ok(api, "gehoert/zusammenfassung", nach=["tag", "folge"], serie_id="rabe", von="2026-01-01", bis="2026-07-19")  # 200 Tage: 400 Zeilen
    assert len(r["zeilen"]) == 400


# --------------------------------------------------------------------------------------------
# Befehl 51
# --------------------------------------------------------------------------------------------


async def test_51_zuletzt_je_serie_neueste_zuerst_nur_boxen(api, daten, anna, bestand):
    r = await ok(api, "gehoert/zuletzt")
    assert [(e["id"], e["wer"], e["zeit"]) for e in r["eintraege"]] == [("rabe", "box:box1", "2026-11-17T08:01:40Z"), ("zwei", "box:box2", "2026-11-10T09:05:00Z")]
    e = r["eintraege"][0]
    assert e["name"] == "Der kleine Rabe" and e["anzahl_folgen"] == 3 and e["favorit"] is False  # die Felder der Serie-Kurzform
    assert e["zuletzt_gehoert_am"] == "2026-11-17T08:01:40Z"
    # Reinhören zählt für „alle_boxen“ nicht, für „alle“ schon
    alle = await ok(api, "gehoert/zuletzt", wer="alle")
    assert [(x["id"], x["wer"]) for x in alle["eintraege"]] == [("rabe", "box:box1"), ("zwei", "benutzer:" + anna.nutzer.id)]
    eine = await ok(api, "gehoert/zuletzt", wer="box:box2")
    assert [x["id"] for x in eine["eintraege"]] == ["zwei"]
    person = await ok(api, "gehoert/zuletzt", wer="benutzer:" + anna.nutzer.id, limit=1)
    assert [x["id"] for x in person["eintraege"]] == ["zwei"]


async def test_51_limit_grenzen_wer_und_gelöschte_serien_fehlen(api, daten, bestand):
    assert len((await ok(api, "gehoert/zuletzt", limit=1))["eintraege"]) == 1
    assert await fehler(api, "gehoert/zuletzt", limit=0) == "invalid_format"
    assert await fehler(api, "gehoert/zuletzt", limit=21) == "invalid_format"
    assert await fehler(api, "gehoert/zuletzt", wer="boxen") == "wer_ungueltig"
    assert await fehler(api, "gehoert/zuletzt", wer="box:box9") == "wer_ungueltig"
    assert await fehler(api, "gehoert/zuletzt", wer=3) == "invalid_format"
    await fuelle(bestand, "box:box1", z(60, utc(2026, 11, 17, 11), 10, serie="weg3", folge="x.mp3"), z(61, 0, 10, serie="zwei", folge="d.mp3", datum="unbekannt"))
    r = await ok(api, "gehoert/zuletzt")
    assert [x["id"] for x in r["eintraege"]] == ["rabe", "zwei"]  # keine gelöschte Serie, und ein unbekanntes Datum zählt nie als „zuletzt“
    assert r["eintraege"][1]["wer"] == "box:box2"


# --------------------------------------------------------------------------------------------
# serien/list und Zwischenspeicher
# --------------------------------------------------------------------------------------------


async def test_serien_list_zuletzt_gehoert_und_meist_gehoert_und_feld(api, daten, bestand, anna):
    r = await ok(api, "serien/list", sortierung="zuletzt_gehoert")
    assert [s["id"] for s in r["serien"]] == ["rabe", "zwei"]  # rabe am 17., zwei an einer Box am 10.; die Reinhör-Sitzung von zwei am 17. zählt nicht
    assert r["serien"][0]["zuletzt_gehoert_am"] == "2026-11-17T08:01:40Z" and r["serien"][1]["zuletzt_gehoert_am"] == "2026-11-10T09:05:00Z"
    r = await ok(api, "serien/list", sortierung="meist_gehoert")
    assert [s["id"] for s in r["serien"]] == ["zwei", "rabe"]  # 360 s gegen 250 s, alle Quellen
    await fuelle(bestand, "box:box1", z(70, utc(2026, 11, 17, 9), 500, serie="rabe", folge="c.mp3"))
    r = await ok(api, "serien/list", sortierung="meist_gehoert")
    assert [s["id"] for s in r["serien"]] == ["rabe", "zwei"]  # der Zwischenspeicher verfällt mit den neuen Daten
    # „nie gespielt“ steht am Ende, nach Name
    nas_serie = await ok(api, "serie/create", name="Aaa Neue")
    r = await ok(api, "serien/list", sortierung="zuletzt_gehoert")
    assert [s["name"] for s in r["serien"]] == ["Der kleine Rabe", "Zweite Serie", "Aaa Neue"]
    assert r["serien"][-1]["zuletzt_gehoert_am"] is None
    assert nas_serie["serie"]["zuletzt_gehoert_am"] is None


async def test_meist_gehoert_zaehlt_die_letzten_365_kalendertage(api, bestand):
    await fuelle(bestand, "box:box1", z(1, utc(2025, 11, 17, 9), 9999, serie="rabe", folge="a.mp3"))  # 2025-11-17: der 366. Tag
    await fuelle(bestand, "box:box1", z(2, utc(2025, 11, 18, 9), 100, serie="zwei", folge="d.mp3"))  # 2025-11-18: der 365. Tag
    r = await ok(api, "serien/list", sortierung="meist_gehoert")
    assert [s["id"] for s in r["serien"]] == ["zwei", "rabe"]
    r = await ok(api, "serien/list", sortierung="zuletzt_gehoert")  # (aber „zuletzt“ kennt keine Grenze)
    assert [s["id"] for s in r["serien"]] == ["zwei", "rabe"]


async def test_serie_get_traegt_zuletzt_gehoert_am(api, daten):
    s = await ok(api, "serie/get", serie_id="rabe")
    assert s["zuletzt_gehoert_am"] == "2026-11-17T08:01:40Z"


# --------------------------------------------------------------------------------------------
# Befehl 52: technik/verlauf
# --------------------------------------------------------------------------------------------


def technik_zeilen() -> list[tuple[int, str, str | None]]:
    t = lambda h, m=0: utc(2026, 11, 10, h, m)  # noqa: E731
    return [
        (t(7), "online", None), (t(8), "lader_an", None), (t(9), "lader_aus", None), (t(10), "sync_ok", None), (t(10, 30), "sync_fehler", "kein_netz"),
        (t(11), "fehler", "sd_voll"), (t(12), "verworfen", "5"), (t(13), "lader_an", None), (t(14), "lader_aus", None), (t(15), "offline", None),
    ]


def zs(sekunden: int) -> str:
    return datetime.fromtimestamp(sekunden, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def test_52_verlauf_einer_box(api, bestand):
    await bestand.gehoert.technik_schreibe("box1", technik_zeilen())
    await bestand.gehoert.technik_schreibe("box2", [(utc(2026, 11, 10, 8), "lader_an", None)])
    r = await ok(api, "technik/verlauf", box="box1", von="2026-11-10", bis="2026-11-10")
    t = lambda h, m=0: utc(2026, 11, 10, h, m)  # noqa: E731
    assert r["ladevorgaenge"] == [{"beginn": zs(t(8)), "ende": zs(t(9)), "dauer_s": 3600}, {"beginn": zs(t(13)), "ende": zs(t(14)), "dauer_s": 3600}]
    assert r["laufzeiten"] == [{"von": zs(t(9)), "bis": zs(t(13)), "dauer_s": 14400}, {"von": zs(t(14)), "bis": zs(t(15)), "dauer_s": 3600}]
    assert r["verbindung"] == [{"zeit": zs(t(7)), "online": True}, {"zeit": zs(t(15)), "online": False}]
    assert r["syncs"] == [{"zeit": zs(t(10)), "ok": True, "code": None}, {"zeit": zs(t(10, 30)), "ok": False, "code": "kein_netz"}]
    assert r["fehler"] == [{"zeit": zs(t(11)), "code": "sd_voll"}]
    assert r["verworfen"] == [{"zeit": zs(t(12)), "gesamt": 5}]
    assert r["weitere"] is False


async def test_52_zeitraum_in_der_zeitzone_von_ha_und_offene_ladung(api, bestand):
    # 23:30 UTC am 9. ist 00:30 am 10. in Berlin; 22:59 UTC am 10. ist 23:59 am 10.; 23:00 UTC am 10. gehört schon zum 11.
    await bestand.gehoert.technik_schreibe("box1", [(utc(2026, 11, 9, 22, 59), "fehler", "davor"), (utc(2026, 11, 9, 23, 0), "fehler", "erste"), (utc(2026, 11, 10, 22, 59), "fehler", "letzte"), (utc(2026, 11, 10, 23, 0), "fehler", "danach")])
    r = await ok(api, "technik/verlauf", box="box1", von="2026-11-10", bis="2026-11-10")
    assert [f["code"] for f in r["fehler"]] == ["erste", "letzte"]
    # Laden ohne Ende: ``ende`` und ``dauer_s`` sind null; Laden, das vor dem Zeitraum begann, beginnt früher
    await bestand.gehoert.technik_schreibe("box2", [(utc(2026, 11, 10, 20), "lader_an", None), (utc(2026, 11, 11, 1), "lader_aus", None), (utc(2026, 11, 11, 5), "lader_an", None)])
    r = await ok(api, "technik/verlauf", box="box2", von="2026-11-11", bis="2026-11-11")
    assert r["ladevorgaenge"] == [{"beginn": zs(utc(2026, 11, 10, 20)), "ende": zs(utc(2026, 11, 11, 1)), "dauer_s": 18000}, {"beginn": zs(utc(2026, 11, 11, 5)), "ende": None, "dauer_s": None}]
    assert r["laufzeiten"] == [{"von": zs(utc(2026, 11, 11, 1)), "bis": zs(utc(2026, 11, 11, 5)), "dauer_s": 14400}]
    # eine Laufzeit ohne Ende
    await bestand.gehoert.technik_schreibe("box1", [(utc(2026, 11, 12, 8), "lader_aus", None)])
    r = await ok(api, "technik/verlauf", box="box1", von="2026-11-12", bis="2026-11-12")
    assert r["laufzeiten"] == [{"von": zs(utc(2026, 11, 12, 8)), "bis": None, "dauer_s": None}]


async def test_52_fehler_und_grenzen(api, bestand):
    assert await fehler(api, "technik/verlauf", box="box9", von="2026-11-01", bis="2026-11-02") == "box_unbekannt"
    assert await fehler(api, "technik/verlauf", box="box1", von="2026-11-05", bis="2026-11-04") == "invalid_format"
    assert await fehler(api, "technik/verlauf", box="box1", von="2026-01-01", bis="2027-02-05") == "invalid_format"  # 401 Tage
    await ok(api, "technik/verlauf", box="box1", von="2026-01-01", bis="2027-02-04")  # 400 Tage
    assert await fehler(api, "technik/verlauf", box="box1", von="gestern", bis="2026-11-02") == "invalid_format"
    assert await fehler(api, "technik/verlauf", box="box1", von="2026-11-01") == "invalid_format"
    leer = await ok(api, "technik/verlauf", box="box1", von="2026-11-01", bis="2026-11-02")
    assert leer == {"ladevorgaenge": [], "laufzeiten": [], "verbindung": [], "syncs": [], "fehler": [], "verworfen": [], "weitere": False}


async def test_52_listen_bei_2000_eintraegen_gekuerzt(api, bestand):
    await bestand.gehoert.technik_schreibe("box1", [(utc(2026, 11, 10, 8) + i, "fehler", "x") for i in range(2005)])
    r = await ok(api, "technik/verlauf", box="box1", von="2026-11-10", bis="2026-11-10")
    assert len(r["fehler"]) == 2000 and r["weitere"] is True


# --------------------------------------------------------------------------------------------
# Befehl 53: gehoert/exportieren
# --------------------------------------------------------------------------------------------


def lies_csv(inhalt: bytes) -> list[list[str]]:
    assert inhalt.startswith("﻿".encode())  # UTF-8 mit BOM
    return list(csv.reader(io.StringIO(inhalt.decode("utf-8-sig")), delimiter=";"))


@pytest.fixture
async def http(hass, hass_client):
    return await hass_client()


async def test_53_export_signierter_pfad_und_csv(hass, api, daten, http, anna):
    pfad = (await ok(api, "gehoert/exportieren", quelle="boxen"))["pfad"]
    assert pfad.startswith("/api/tobibox/export/") and "authSig=" in pfad and "box%3Aboxen" not in pfad and pfad.split("?")[0].endswith("/boxen")
    antwort = await http.get(pfad)
    assert antwort.status == 200
    assert antwort.headers["Content-Type"] == "text/csv; charset=utf-8"
    assert antwort.headers["Content-Disposition"] == 'attachment; filename="gehoert-boxen-2026-11-17.csv"'
    zeilen_ = lies_csv(await antwort.read())
    assert zeilen_[0] == ["Beginn", "Ende", "Quelle", "Serie", "Folge", "Hörzeit (s)", "Ende der Sitzung", "Mal neu", "fertig", "Datum"]
    assert len(zeilen_) == 1 + 6  # alle Boxen: box1 vier Zeilen (1, 2, 3, 6), box2 zwei (4, 7); die Person nicht
    # nach Beginn aufsteigend; Zeiten in der Zeitzone von HA (Winterzeit, +1 Stunde)
    assert zeilen_[1] == ["2026-11-10 10:00:00", "2026-11-10 10:05:00", "box2", "Zweite Serie", "d", "300", "ende_der_folge", "ja", "ja", "sicher"]  # „d“: der Titel der Folge ohne Endung
    assert zeilen_[-1][:7] == ["2026-11-17 09:00:00", "2026-11-17 09:01:40", "box1", "Der kleine Rabe", "Eins", "100", "ende_der_folge"]  # „Eins“: der Titel der Folge
    assert zeilen_[-1][7:] == ["ja", "ja", "sicher"]
    assert [r[3] for r in zeilen_[1:]].count("Gelöscht") == 2
    assert all(len(r) == 10 for r in zeilen_)


async def test_53_quellen_dateiname_und_unbekanntes_datum(hass, api, daten, http, anna, bestand):
    await fuelle(bestand, "box:box1", z(80, 0, 12, folge="b.mp3", datum="unbekannt"))
    pfad = (await ok(api, "gehoert/exportieren", quelle="box:box1"))["pfad"]
    antwort = await http.get(pfad)
    assert antwort.headers["Content-Disposition"] == 'attachment; filename="gehoert-box-box1-2026-11-17.csv"'
    zeilen_ = lies_csv(await antwort.read())
    assert [r[2] for r in zeilen_[1:]] == ["box1"] * 5
    unbekannt = zeilen_[-1]  # unbekanntes Datum zuletzt, Zeiten leer
    assert unbekannt[0] == "" and unbekannt[1] == "" and unbekannt[9] == "unbekannt" and unbekannt[5] == "12"
    pfad = (await ok(api, "gehoert/exportieren", quelle="reinhoeren"))["pfad"]
    zeilen_ = lies_csv(await (await http.get(pfad)).read())
    assert [(r[2], r[3], r[4]) for r in zeilen_[1:]] == [("Anna", "Zweite Serie", "e")]
    pfad = (await ok(api, "gehoert/exportieren", quelle="alle"))["pfad"]
    assert len(lies_csv(await (await http.get(pfad)).read())) == 1 + 8
    pfad = (await ok(api, "gehoert/exportieren", quelle="benutzer:" + anna.nutzer.id))["pfad"]
    assert len(lies_csv(await (await http.get(pfad)).read())) == 2


async def test_53_zellen_mit_formelanfang_werden_entschaerft(hass, api, bestand, http, nas, lege_mp3):
    pfad = nas.serie("formel", "formel", "=SUMME(A1)", ["f.mp3"], folgen_info={"f.mp3": {"anzeige": "@befehl"}})
    lege_mp3(pfad / "f.mp3")
    await bestand.medien.pruefen()
    await fuelle(bestand, "box:box1", z(1, utc(2026, 11, 16, 10), 5, serie="formel", folge="f.mp3"), z(2, utc(2026, 11, 16, 11), 5, serie="rabe", folge="-minus.mp3"))
    zeilen_ = lies_csv(await (await http.get((await ok(api, "gehoert/exportieren", quelle="alle"))["pfad"])).read())
    assert zeilen_[1][3:5] == ["'=SUMME(A1)", "'@befehl"]
    assert zeilen_[2][4] == "'-minus.mp3"


async def test_53_fehler_rechte_und_abruf_nur_fuer_den_anfragenden(hass, api, daten, http, anna, hass_client):
    assert await fehler(api, "gehoert/exportieren", quelle="quatsch") == "wer_ungueltig"
    assert await fehler(api, "gehoert/exportieren", quelle="alle_boxen") == "wer_ungueltig"  # bei 53 und 54 heißt es boxen, reinhoeren, alle
    assert await fehler(api, "gehoert/exportieren", quelle="box:box9") == "wer_ungueltig"
    assert await fehler(api, "gehoert/exportieren", quelle="benutzer:gibtsnicht") == "wer_ungueltig"
    assert await fehler(anna, "gehoert/exportieren", quelle="alle") == "unauthorized"
    pfad = (await ok(api, "gehoert/exportieren", quelle="alle"))["pfad"]
    # ohne Signatur und ohne Anmeldung: HA lehnt ab
    ohne = await http.get(pfad.split("?")[0], headers={"Authorization": ""})
    assert ohne.status == 401
    # ein anderer Administrator mit eigener Anmeldung (ohne Signatur) ist nicht der Anfragende
    admin2 = await hass.auth.async_create_user("Admin2", group_ids=["system-admin"])
    refresh = await hass.auth.async_create_refresh_token(admin2, "https://example.org")
    fremd = await hass_client(hass.auth.async_create_access_token(refresh))
    assert (await fremd.get(pfad.split("?")[0])).status == 401
    # ein Benutzer ohne Administratorrechte auch nicht, selbst mit eigenem Pfad
    normal = await hass.auth.async_create_user("Normal", group_ids=["system-users"])
    refresh = await hass.auth.async_create_refresh_token(normal, "https://example.org")
    n = await hass_client(hass.auth.async_create_access_token(refresh))
    assert (await n.get(f"/api/tobibox/export/{normal.id}/alle")).status == 401
    # der Anfragende selbst mit Anmeldung und ohne Signatur: gültig (die Datei entsteht beim Abruf)
    assert (await http.get(pfad.split("?")[0])).status == 200


async def test_53_signatur_laeuft_nach_10_minuten_ab(hass, api, daten, http, freezer):
    pfad = (await ok(api, "gehoert/exportieren", quelle="alle"))["pfad"]
    freezer.tick(timedelta(seconds=590))
    assert (await http.get(pfad, headers={"Authorization": ""})).status == 200  # mit Signatur, ohne Kopf
    freezer.tick(timedelta(seconds=20))
    assert (await http.get(pfad, headers={"Authorization": ""})).status == 401


async def test_53_je_aufruf_ein_neuer_pfad(api, daten, freezer):
    a = (await ok(api, "gehoert/exportieren", quelle="alle"))["pfad"]
    freezer.tick(timedelta(seconds=2))
    b = (await ok(api, "gehoert/exportieren", quelle="alle"))["pfad"]
    assert a != b


# --------------------------------------------------------------------------------------------
# Befehl 54: gehoert/loeschen
# --------------------------------------------------------------------------------------------


async def test_54_trocken_zaehlt_nur(api, daten, bestand):
    assert await ok(api, "gehoert/loeschen", quelle="boxen", trocken=True) == {"anzahl": 6}
    assert await ok(api, "gehoert/loeschen", quelle="reinhoeren", trocken=True) == {"anzahl": 1}
    assert await ok(api, "gehoert/loeschen", quelle="alle", trocken=True) == {"anzahl": 7}
    assert await ok(api, "gehoert/loeschen", quelle="box:box2", trocken=True, bestaetigung="egal") == {"anzahl": 2}
    assert len(await zeilen(bestand)) == 7 and bestand.gehoert.db.marken() == {}


async def test_54_bestaetigung_wort(api, daten, bestand):
    for felder in ({}, {"bestaetigung": "loeschen"}, {"bestaetigung": "Löschen"}, {"bestaetigung": "JA"}, {"bestaetigung": ""}, {"trocken": False}, {"trocken": False, "bestaetigung": "LÖSCHEN "}):
        assert await fehler(api, "gehoert/loeschen", quelle="box:box1", **felder) == "invalid_format", felder
    assert len(await zeilen(bestand)) == 7
    assert (await ok(api, "gehoert/loeschen", quelle="box:box1", bestaetigung="LOESCHEN"))["anzahl"] == 4
    assert (await ok(api, "gehoert/loeschen", quelle="box:box2", bestaetigung="LÖSCHEN", trocken=False))["anzahl"] == 2
    assert (await ok(api, "gehoert/loeschen", quelle="box:box2", bestaetigung="LÖSCHEN"))["anzahl"] == 0  # idempotent: Endzustand
    # dasselbe Wort mit getrenntem Umlaut (O + kombinierendes Trema) gilt auch
    assert (await ok(api, "gehoert/loeschen", quelle="reinhoeren", bestaetigung="LÖSCHEN"))["anzahl"] == 1
    assert await zeilen(bestand) == []


async def test_54_sammelquellen_setzen_marken_fuer_jede_betroffene_quelle(api, daten, bestand, anna):
    await ok(api, "gehoert/loeschen", quelle="boxen", bestaetigung="LÖSCHEN")
    assert {q for q in bestand.gehoert.db.marken()} == {"box:box1", "box:box2"}
    assert [r["quelle"] for r in await zeilen(bestand)] == ["benutzer:" + anna.nutzer.id]
    await ok(api, "gehoert/loeschen", quelle="reinhoeren", bestaetigung="LÖSCHEN")
    assert set(bestand.gehoert.db.marken()) == {"box:box1", "box:box2", "benutzer:" + anna.nutzer.id}
    assert await zeilen(bestand) == []


async def test_54_alle_loescht_boxen_und_personen_aber_nicht_die_technik(api, daten, bestand, anna):
    await bestand.gehoert.technik_schreibe("box1", technik_zeilen())
    assert (await ok(api, "gehoert/loeschen", quelle="alle", bestaetigung="LÖSCHEN"))["anzahl"] == 7
    assert await zeilen(bestand) == []
    assert len(await bestand.hass.async_add_executor_job(bestand.gehoert.db.technik_alle, "box1")) == 10


async def test_54_fehler(api, daten, anna):
    for quelle in ("quatsch", "alle_boxen", "box:box9", "benutzer:gibtsnicht", "box:"):
        assert await fehler(api, "gehoert/loeschen", quelle=quelle, trocken=True) == "wer_ungueltig", quelle
    assert await fehler(anna, "gehoert/loeschen", quelle="alle", trocken=True) == "unauthorized"


async def test_54_loeschmarke_verwirft_alte_nachlieferung_quittiert_sie_aber(hass, api, daten, bestand, box_fabrik):
    box = box_fabrik("box1")
    await ok(api, "gehoert/loeschen", quelle="box:box1", bestaetigung="LÖSCHEN")  # Marke: 17.11., 12:00:00 UTC
    alt = sitz(1, sitzung="00000000-0000-4000-8000-0000000000aa", beginn="2026-11-17T10:00:00Z", ende_boot_s=50500, gehoert_s=100)
    neu = sitz(2, sitzung="00000000-0000-4000-8000-0000000000bb", beginn="2026-11-17T12:30:00Z")
    await box.ereignis("gespielt", nachricht(alt, neu, gesendet=51915))
    await zeit_vergeht(hass, 3)
    assert [r["sitzung"] for r in await zeilen(bestand, "box:box1")] == ["00000000-0000-4000-8000-0000000000bb"]
    assert sorted(u for q in quittungen(box) for u in q) == ["00000000-0000-4000-8000-0000000000aa", "00000000-0000-4000-8000-0000000000bb"]


async def test_54_zeilen_die_nach_trocken_ankommen_werden_mitgeloescht(api, daten, bestand):
    probe = (await ok(api, "gehoert/loeschen", quelle="box:box2", trocken=True))["anzahl"]
    await fuelle(bestand, "box:box2", z(90, utc(2026, 11, 17, 9), 10, folge="d.mp3"))
    assert (await ok(api, "gehoert/loeschen", quelle="box:box2", bestaetigung="LÖSCHEN"))["anzahl"] == probe + 1


async def test_54_offene_reinhoer_sitzungen_der_geloeschten_person_fallen_weg(hass, api, daten, bestand, anna):
    await bestand.reinhoeren.melde(anna.nutzer.id, "spieler-0001", "rabe", "a.mp3", 0, 100, None, True, False)
    assert len(bestand.reinhoeren.offen) == 1
    await ok(api, "gehoert/loeschen", quelle="benutzer:" + anna.nutzer.id, bestaetigung="LÖSCHEN")
    assert bestand.reinhoeren.offen == {}


# --------------------------------------------------------------------------------------------
# Ereignis ``gehoert``
# --------------------------------------------------------------------------------------------


async def test_ereignis_gehoert_hoechstens_alle_5_sekunden_und_ohne_inhalt(hass, bestand, ereignisse):
    ereignisse.clear()
    for n in range(1, 4):
        await fuelle(bestand, "box:box1", z(n, utc(2026, 11, 17, 6, n), 10, folge=f"{n}.mp3"))
    assert [e for e in ereignisse if e["thema"] == "gehoert"] == [{"v": 1, "thema": "gehoert", "art": "geaendert", "daten": {}}]  # das erste sofort
    await zeit_vergeht(hass, 3)
    assert ereignis_arten(ereignisse, "gehoert") == ["geaendert"]  # noch im Fenster
    await zeit_vergeht(hass, 5.5)
    assert ereignis_arten(ereignisse, "gehoert") == ["geaendert", "geaendert"]  # die übrigen zusammengefasst
    await zeit_vergeht(hass, 12)
    assert ereignis_arten(ereignisse, "gehoert") == ["geaendert", "geaendert"]
    await fuelle(bestand, "box:box1", z(9, utc(2026, 11, 17, 6, 30), 10, folge="9.mp3"))
    assert ereignis_arten(ereignisse, "gehoert") == ["geaendert"] * 3  # nach dem Fenster wieder sofort


async def test_ereignis_gehoert_nach_loeschen_und_nicht_bei_nachlieferung_ohne_aenderung(hass, api, daten, bestand, ereignisse):
    for _ in range(3):  # das Fenster der Ereignisse der Fixture leeren (bei Bedarf kommt ein zusammengefasstes Ereignis nach)
        await zeit_vergeht(hass, 20)
    ereignisse.clear()
    await fuelle(bestand, "box:box1", z(1, utc(2026, 11, 16, 10), 100))  # dieselbe Zeile noch einmal: nichts geändert
    assert ereignis_arten(ereignisse, "gehoert") == []
    await ok(api, "gehoert/loeschen", quelle="box:box1", bestaetigung="LÖSCHEN")
    assert ereignis_arten(ereignisse, "gehoert") == ["geaendert"]


# --------------------------------------------------------------------------------------------
# Favoriten: Befehle 55 und 56, Feld, Filter, Ereignis
# --------------------------------------------------------------------------------------------


async def test_55_stern_setzen_wiederholen_nehmen_und_ereignis(api, bestand, ereignisse):
    ereignisse.clear()
    assert await ok(api, "favorit/set", serie_id="rabe", an=True) == {"an": True}
    assert await ok(api, "favorit/set", serie_id="rabe", an=True) == {"an": True}  # Wiederholung ohne Fehler und ohne Wirkung
    assert await ok(api, "favorit/set", serie_id="rabe", folge="a.mp3", an=True) == {"an": True}
    assert [e["daten"] for e in ereignisse if e["thema"] == "favoriten"] == [
        {"serie_id": "rabe", "folge": None, "an": True},
        {"serie_id": "rabe", "folge": "a.mp3", "an": True},
    ]
    assert len(bestand.favoriten.eintraege) == 2
    assert await ok(api, "favorit/set", serie_id="rabe", folge="a.mp3", an=False) == {"an": False}
    assert await ok(api, "favorit/set", serie_id="rabe", folge="a.mp3", an=False) == {"an": False}  # nichts mehr zu nehmen: kein Fehler
    assert [e["daten"]["an"] for e in ereignisse if e["thema"] == "favoriten"] == [True, True, False]
    assert [e["art"] for e in ereignisse if e["thema"] == "favoriten"] == ["geaendert"] * 3


async def test_55_fehler(api, bestand):
    assert await fehler(api, "favorit/set", serie_id="gibtsnicht", an=True) == "serie_nicht_gefunden"
    assert await fehler(api, "favorit/set", serie_id="rabe", folge="nix.mp3", an=True) == "folge_nicht_gefunden"
    assert await fehler(api, "favorit/set", serie_id="rabe") == "invalid_format"
    assert await fehler(api, "favorit/set", serie_id="rabe", an="ja") == "invalid_format"
    assert await fehler(api, "favorit/set", an=True) == "invalid_format"
    assert await fehler(api, "favorit/set", serie_id="rabe", an=True, x=1) == "invalid_format"
    assert bestand.favoriten.eintraege == []


async def test_55_zu_viele_favoriten(api, bestand):
    with patch("custom_components.tobibox.favoriten.FAVORITEN_MAX", 2):
        await ok(api, "favorit/set", serie_id="rabe", an=True)
        await ok(api, "favorit/set", serie_id="rabe", folge="a.mp3", an=True)
        assert await fehler(api, "favorit/set", serie_id="zwei", an=True) == "zu_viele_favoriten"
        await ok(api, "favorit/set", serie_id="rabe", an=True)  # schon gesetzt: kein Fehler, auch an der Grenze
        await ok(api, "favorit/set", serie_id="rabe", folge="a.mp3", an=False)
        await ok(api, "favorit/set", serie_id="zwei", an=True)


async def test_55_mengen_nicht_fuer_administratoren_eigener_zaehler(api, anna, bestand, freezer):
    assert FAVORITEN_JE_MINUTE == 30
    for i in range(30):
        await ok(anna, "favorit/set", serie_id="rabe", an=i % 2 == 0)
    assert await fehler(anna, "favorit/set", serie_id="rabe", an=True) == "zu_viele_aenderungen"
    await ok(anna, "hoerstelle/get", serie_id="rabe")  # andere Befehle haben eigene Zähler
    freezer.tick(timedelta(seconds=61))
    await ok(anna, "favorit/set", serie_id="rabe", an=True)
    for _ in range(40):
        await ok(api, "favorit/set", serie_id="zwei", an=True)  # Administratoren sind ausgenommen


async def test_56_liste_neueste_zuerst_mit_namen_und_ohne_verwaiste(hass, api, bestand, freezer):
    anna = await hass.auth.async_create_user("Anna", group_ids=["system-users"])
    bert = await hass.auth.async_create_user("Bert", group_ids=["system-users"])
    bestand.favoriten.setze(anna.id, "rabe", None, True)
    freezer.tick(timedelta(seconds=10))
    bestand.favoriten.setze(bert.id, "zwei", "d.mp3", True)
    freezer.tick(timedelta(seconds=10))
    bestand.favoriten.setze(anna.id, "rabe", "b.mp3", True)
    r = await ok(api, "favoriten/list")
    assert [(e["serie_id"], e["folge"], e["gesetzt_von"]["name"], e["gesetzt_am"]) for e in r["eintraege"]] == [
        ("rabe", "b.mp3", "Anna", "2026-11-17T12:00:20Z"),
        ("zwei", "d.mp3", "Bert", "2026-11-17T12:00:10Z"),
        ("rabe", None, "Anna", "2026-11-17T12:00:00Z"),
    ]
    assert r["eintraege"][0]["gesetzt_von"]["id"] == anna.id
    # ein gelöschter Benutzer heißt „unbekannt“
    await hass.auth.async_remove_user(anna)
    r = await ok(api, "favoriten/list")
    assert r["eintraege"][0]["gesetzt_von"] == {"id": anna.id, "name": "unbekannt"}
    # Einträge, deren Serie oder Folge es nicht mehr gibt, fehlen
    await ok(api, "folge/delete", serie_id="rabe", folge="b.mp3")
    r = await ok(api, "favoriten/list")
    assert [(e["serie_id"], e["folge"]) for e in r["eintraege"]] == [("zwei", "d.mp3"), ("rabe", None)]
    assert len(bestand.favoriten.eintraege) == 3  # im Speicher bleibt er, bis aufgeräumt wird


async def test_favorit_feld_und_filter_bei_serien_und_folgen(api, bestand):
    await ok(api, "favorit/set", serie_id="rabe", folge="a.mp3", an=True)
    r = await ok(api, "serien/list")
    assert {s["id"]: s["favorit"] for s in r["serien"]} == {"rabe": False, "zwei": False}  # ein Stern an einer Folge macht die Serie nicht zum Favoriten
    assert (await ok(api, "serien/list", filter=["favorit"]))["serien"] == []
    await ok(api, "favorit/set", serie_id="zwei", an=True)
    r = await ok(api, "serien/list", filter=["favorit"])
    assert [s["id"] for s in r["serien"]] == ["zwei"] and r["serien"][0]["favorit"] is True and r["gesamt"] == 1
    r = await ok(api, "serien/list", filter=["favorit", "sammlung"])
    assert [s["id"] for s in r["serien"]] == ["zwei"]
    s = await ok(api, "serie/get", serie_id="rabe")
    assert {f["name"]: f["favorit"] for f in s["folgen"]} == {"a.mp3": True, "b.mp3": False, "c.mp3": False} and s["favorit"] is False
    f = await ok(api, "folgen/list")
    assert {(x["serie_id"], x["folge"]): x["favorit"] for x in f["folgen"]}[("rabe", "a.mp3")] is True
    assert {x["favorit"] for x in f["folgen"] if x["folge"] != "a.mp3"} == {False}
    f = await ok(api, "folgen/list", filter=["favorit"])
    assert [(x["serie_id"], x["folge"]) for x in f["folgen"]] == [("rabe", "a.mp3")] and f["gesamt"] == 1


async def test_stern_zieht_mit_beim_verschieben_wie_im_vertrag(api, bestand):
    await ok(api, "favorit/set", serie_id="rabe", folge="a.mp3", an=True)
    await ok(api, "folge/verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id="zwei")
    r = await ok(api, "favoriten/list")
    assert [(e["serie_id"], e["folge"]) for e in r["eintraege"]] == [("zwei", "a.mp3")]


# --------------------------------------------------------------------------------------------
# boxen/list: akku_entitaet
# --------------------------------------------------------------------------------------------


async def test_boxen_list_akku_entitaet_aus_der_registry(hass, api, bestand):
    r = await ok(api, "boxen/list")
    assert {b["box"]: b["akku_entitaet"] for b in r["boxen"]} == {"box1": None, "box2": None}
    er.async_get(hass).async_get_or_create("sensor", "mqtt", "tobibox_box1_akku", suggested_object_id="tobi_box_box1_akku")
    er.async_get(hass).async_get_or_create("sensor", "mqtt", "tobibox_box2_lader_zeit", suggested_object_id="anderes")  # ein anderer Sensor
    r = await ok(api, "boxen/list")
    assert {b["box"]: b["akku_entitaet"] for b in r["boxen"]} == {"box1": "sensor.tobi_box_box1_akku", "box2": None}


# --------------------------------------------------------------------------------------------
# Reste aus Stufe A (Backend): eingang/list und einsortierung/bestaetigen
# --------------------------------------------------------------------------------------------


async def test_einsortierung_bestaetigen_setzt_pruefen_im_protokoll_zurueck(hass, api, bestand, ereignisse):
    erg = lambda sid, folge: {"serie_id": sid, "serie_name": "x", "serie_neu": False, "folge": folge, "anzeige": folge, "tracks": 1, "pruefen": True, "pruefen_gruende": ["tags_fehlen"]}  # noqa: E731
    bestand.eingang.protokoll.extend(
        [
            {"id": "1" * 12, "name": "e1", "art": "datei", "status": "erledigt", "pruefen": True, "ergebnis": [erg("rabe", "a.mp3"), erg("rabe", "b.mp3"), erg("zwei", "d.mp3")]},
            {"id": "2" * 12, "name": "e2", "art": "datei", "status": "erledigt", "pruefen": True, "ergebnis": [erg("rabe", "c.mp3")]},
        ]
    )
    ereignisse.clear()
    await ok(api, "einsortierung/bestaetigen", serie_id="rabe", folgen=["a.mp3"])  # mit ``folgen``: nur diese Elemente
    liste = (await ok(api, "eingang/list", filter="erledigt"))["eintraege"]
    por = {e["name"]: e for e in liste}
    assert [r["pruefen"] for r in por["e1"]["ergebnis"]] == [False, True, True] and por["e1"]["ergebnis"][0]["pruefen_gruende"] == [] and por["e1"]["pruefen"] is True
    assert ereignis_arten(ereignisse, "eingang") == ["geaendert"]
    await ok(api, "einsortierung/bestaetigen", serie_id="rabe")  # ohne ``folgen``: alle Elemente der Serie
    por = {e["name"]: e for e in (await ok(api, "eingang/list", filter="erledigt"))["eintraege"]}
    assert [r["pruefen"] for r in por["e1"]["ergebnis"]] == [False, False, True] and por["e1"]["pruefen"] is True  # ``zwei`` bleibt
    assert por["e2"]["pruefen"] is False and por["e2"]["ergebnis"][0]["pruefen"] is False
    ereignisse.clear()
    await ok(api, "einsortierung/bestaetigen", serie_id="rabe")  # nichts mehr zu ändern: kein Ereignis
    assert ereignis_arten(ereignisse, "eingang") == []
    await ok(api, "einsortierung/bestaetigen", serie_id="zwei")
    por = {e["name"]: e for e in (await ok(api, "eingang/list", filter="erledigt"))["eintraege"]}
    assert por["e1"]["pruefen"] is False


async def test_serie_rename_setzt_das_protokoll_nicht_zurueck(api, bestand):
    bestand.eingang.protokoll.append({"id": "1" * 12, "name": "e1", "art": "datei", "status": "erledigt", "pruefen": True, "ergebnis": [{"serie_id": "rabe", "folge": "a.mp3", "pruefen": True, "pruefen_gruende": ["x"]}]})
    await ok(api, "serie/rename", serie_id="rabe", name="Anders")
    assert bestand.eingang.protokoll[-1]["ergebnis"][0]["pruefen"] is True


async def test_eingang_list_dateinamen_und_gruppe_anzahl(hass, api, bestand, nas, lege_mp3):
    pfad = nas.eingang / "Hörbuch"
    for i in range(1, 4):
        lege_mp3(pfad / f"{i:02d} Kapitel.mp3")
    lege_mp3(nas.eingang / "Einzel.mp3")
    await ok(api, "eingang/sortieren")  # ein Durchlauf liest den Eingang (noch in der Ruhezeit: nichts wird einsortiert)
    await hass.async_block_till_done()
    liste = await ok(api, "eingang/list")
    e = {x["name"]: x for x in liste["eintraege"]}
    assert e["Hörbuch"]["dateinamen"] == ["01 Kapitel.mp3", "02 Kapitel.mp3", "03 Kapitel.mp3"] and e["Hörbuch"]["dateien"] == 3
    assert "dateien_weitere" not in e["Hörbuch"]
    assert e["Einzel.mp3"]["dateinamen"] == ["Einzel.mp3"]
    # mit Wunsch und Gruppe: ``gruppe_anzahl``; ohne Gruppe fehlt es
    jetzt = "2026-11-17T12:00:00Z"
    bestand.eingang.vorgaben["Hörbuch/01 Kapitel.mp3"] = {"serie_id": None, "gruppe": "gruppe-0001", "wunsch": {"ziel": "neu", "art": "hoerbuch", "name": "Buch", "gruppe_anzahl": 3}, "am": jetzt}
    bestand.eingang.vorgaben["Einzel.mp3"] = {"serie_id": None, "gruppe": None, "wunsch": {"ziel": "einzeln", "art": "musik", "name": None, "gruppe_anzahl": None}, "am": jetzt}
    e = {x["name"]: x for x in (await ok(api, "eingang/list"))["eintraege"]}
    assert e["Hörbuch"]["wunsch"] == {"ziel": "neu", "art": "hoerbuch", "gruppe_anzahl": 3}
    assert e["Einzel.mp3"]["wunsch"] == {"ziel": "einzeln", "art": "musik"}


async def test_eingang_list_mehr_als_50_dateien_dateien_weitere(hass, api, bestand, nas, lege_mp3):
    for i in range(1, 56):
        lege_mp3(nas.eingang / "Viele" / f"{i:02d}.mp3")
    await ok(api, "eingang/sortieren")
    await hass.async_block_till_done()
    e = next(x for x in (await ok(api, "eingang/list"))["eintraege"] if x["name"] == "Viele")
    assert e["dateien"] == 55 and len(e["dateinamen"]) == 50 and e["dateien_weitere"] == 5
    assert e["dateinamen"][0] == "01.mp3" and e["dateinamen"][-1] == "50.mp3"


async def test_eingang_protokoll_traegt_dateinamen(hass, api, bestand, nas, lege_mp3):
    lege_mp3(nas.eingang / "Neu.mp3")
    await bestand.eingang.durchlauf_und_warten(sofort=True)
    await hass.async_block_till_done()
    erledigt = (await ok(api, "eingang/list", filter="erledigt"))["eintraege"]
    assert erledigt[0]["name"] == "Neu.mp3" and erledigt[0]["dateinamen"] == ["Neu.mp3"]
    bestand.eingang.protokoll.append({"id": "0" * 12, "name": "alt", "art": "datei", "status": "erledigt", "ergebnis": []})  # Protokoll aus der Zeit davor
    assert (await ok(api, "eingang/list", filter="erledigt"))["eintraege"][0]["dateinamen"] == []


# --------------------------------------------------------------------------------------------
# Abo: Themen ``gehoert`` und ``favoriten``
# --------------------------------------------------------------------------------------------


async def test_subscribe_themen_gehoert_und_favoriten_snapshot_leer_und_ereignisse(hass, api, bestand):
    await api.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["gehoert", "favoriten"]})
    assert (await api.receive_json())["success"] is True
    snapshots = {e["event"]["thema"]: e["event"] for e in [await api.receive_json(), await api.receive_json()]}
    assert snapshots["gehoert"] == {"v": 1, "thema": "gehoert", "art": "snapshot", "daten": {}}
    assert snapshots["favoriten"] == {"v": 1, "thema": "favoriten", "art": "snapshot", "daten": {}}
    await fuelle(bestand, "box:box1", z(1, utc(2026, 11, 17, 6), 10))
    assert (await api.receive_json())["event"] == {"v": 1, "thema": "gehoert", "art": "geaendert", "daten": {}}
    await api.send_json_auto_id({"type": "tobibox/favorit/set", "serie_id": "rabe", "an": True})
    nachrichten = [await api.receive_json(), await api.receive_json()]
    ereignis = next(n for n in nachrichten if n["type"] == "event")
    assert ereignis["event"]["daten"] == {"serie_id": "rabe", "folge": None, "an": True}


# --------------------------------------------------------------------------------------------
# Nacharbeit B3 (Review)
# --------------------------------------------------------------------------------------------


async def test_csv_entschaerfung_tab_und_cr_am_zellenanfang():
    from custom_components.tobibox.gehoert_abfrage import csv_zelle

    assert csv_zelle("\tx") == "'\tx"
    assert csv_zelle("\rx") == "'\rx"
    assert csv_zelle("x\ty") == "x\ty"  # nur der Anfang zählt
    assert csv_zelle(None) == "" and csv_zelle(5) == "5"


async def test_54_loeschen_alle_und_reinhoeren_erfasst_offene_sitzung_ohne_zeile(hass, api, bestand, anna, ereignisse):
    """Eine Reinhör-Sitzung unter 5 Minuten hat noch keine Zeile: ``alle`` und ``reinhoeren`` verwerfen sie trotzdem und setzen die Löschmarke."""
    uhr = {"t": 1000.0}
    bestand.reinhoeren.mono = lambda: uhr["t"]
    quelle = "benutzer:" + anna.nutzer.id
    for befehl_quelle in ("alle", "reinhoeren"):
        await bestand.reinhoeren.melde(anna.nutzer.id, "spieler-0001", "rabe", "a.mp3", 0, 100, None, True, False)
        uhr["t"] += 30
        await bestand.reinhoeren.melde(anna.nutzer.id, "spieler-0001", "rabe", "a.mp3", 30, 100, None, True, False)
        assert len(bestand.reinhoeren.offen) == 1
        assert await zeilen(bestand, quelle) == []  # noch keine Zeile in der Datenbank
        assert (await ok(api, "gehoert/loeschen", quelle=befehl_quelle, trocken=True))["anzahl"] == 0
        await ok(api, "gehoert/loeschen", quelle=befehl_quelle, bestaetigung="LÖSCHEN")
        assert bestand.reinhoeren.offen == {}
        uhr["t"] += 400
        await bestand.reinhoeren.takt()  # schreibt nichts von vor der Löschung
        assert await zeilen(bestand, quelle) == []
    marken = await hass.async_add_executor_job(bestand.gehoert.db.marken)
    assert quelle in marken


async def test_55_grenze_zaehlt_keine_unsichtbaren_sterne(bestand):
    f = bestand.favoriten
    with patch("custom_components.tobibox.favoriten.FAVORITEN_MAX", 2):
        f.setze("u", "rabe", None, True)
        f.eintraege.append({"serie_id": "weg", "folge": None, "gesetzt_von": "u", "gesetzt_am": "2026-11-16T10:00:00Z"})  # Serie gelöscht: unsichtbar
        assert f.setze("u", "rabe", "a.mp3", True) is True  # der verwaiste Stern wird erst bereinigt, dann geprüft
        assert [(e["serie_id"], e["folge"]) for e in f.eintraege] == [("rabe", None), ("rabe", "a.mp3")]
        with pytest.raises(Exception) as e:  # zwei sichtbare Sterne: die Grenze gilt weiter
            f.setze("u", "rabe", "b.mp3", True)
        assert e.value.code == "zu_viele_favoriten"


async def test_55_grenze_ohne_geprueftes_nas_bereinigt_nichts(bestand):
    f = bestand.favoriten
    with patch("custom_components.tobibox.favoriten.FAVORITEN_MAX", 2):
        f.setze("u", "rabe", None, True)
        f.eintraege.append({"serie_id": "weg", "folge": None, "gesetzt_von": "u", "gesetzt_am": "2026-11-16T10:00:00Z"})
        bestand.medien.geprueft_am = None
        with pytest.raises(Exception) as e:
            f.setze("u", "rabe", "a.mp3", True)
        assert e.value.code == "zu_viele_favoriten"
        assert len(f.eintraege) == 2


async def test_stern_beim_verschieben_loest_ereignis_aus(api, bestand, ereignisse):
    await ok(api, "favorit/set", serie_id="rabe", folge="a.mp3", an=True)
    ereignisse.clear()
    await ok(api, "folge/verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id="zwei")
    assert [e["daten"] for e in ereignisse if e["thema"] == "favoriten"] == [
        {"serie_id": "rabe", "folge": "a.mp3", "an": False},
        {"serie_id": "zwei", "folge": "a.mp3", "an": True},
    ]
    ereignisse.clear()
    bestand.favoriten.schreibe_um({("rabe", "gibtsnicht"): ("zwei", "x")})  # nichts betroffen: kein Ereignis
    assert [e for e in ereignisse if e["thema"] == "favoriten"] == []


async def test_stern_beim_zusammenfuehren_loest_ereignis_aus(bestand, ereignisse):
    bestand.favoriten.setze("u", "rabe", None, True)
    ereignisse.clear()
    bestand.favoriten.schreibe_um({}, ("rabe", "zwei"))
    assert [e["daten"] for e in ereignisse if e["thema"] == "favoriten"] == [
        {"serie_id": "rabe", "folge": None, "an": False},
        {"serie_id": "zwei", "folge": None, "an": True},
    ]


async def test_kurzform_nach_aenderung_hat_zuletzt_gehoert_am_auch_beim_ersten_aufruf(daten):
    bestand = daten
    bestand.gehoert._zs = None  # wie nach dem Start: noch nie geladen
    antwort = await bestand.medien.bestaetigen("rabe", None)
    assert antwort["zuletzt_gehoert_am"] == "2026-11-17T08:01:40Z"
    bestand.gehoert._zs = None
    antwort = await bestand.medien.serie_umbenennen("zwei", "Zweite Serie neu")
    assert antwort["zuletzt_gehoert_am"] == "2026-11-10T09:05:00Z"


async def test_52_verlauf_kuerzt_die_gelesenen_zeilen_und_meldet_weitere(api, bestand):
    from custom_components.tobibox import gehoert as gehoert_modul

    await bestand.gehoert.technik_schreibe("box1", [(utc(2026, 11, 10, 8) + i, "fehler", "x") for i in range(30)])
    with patch.object(gehoert_modul, "TECHNIK_ZEILEN_MAX", 20), patch("custom_components.tobibox.gehoert_abfrage.TECHNIK_ZEILEN_MAX", 20):
        r = await ok(api, "technik/verlauf", box="box1", von="2026-11-10", bis="2026-11-10")
    assert len(r["fehler"]) == 20 and r["weitere"] is True
    r = await ok(api, "technik/verlauf", box="box1", von="2026-11-10", bis="2026-11-10")
    assert len(r["fehler"]) == 30 and r["weitere"] is False
