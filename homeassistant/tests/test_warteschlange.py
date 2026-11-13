"""Paket A9c: Warteschlange „nächster neuer Tobie“ (Vertrag W, 3.13, 4.8; A0-Q, 13.11.).

Eine Gruppe von Tests je Regel (1 bis 14 aus 3.13), dazu zwei Boxen gleichzeitig, Neustart, ``als_neu``, Rechte und Mengen.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import timedelta

import pytest
from homeassistant.auth.const import GROUP_ID_USER
from pytest_homeassistant_custom_component.common import CLIENT_ID

from custom_components.tobibox import const
from custom_components.tobibox import store as store_modul
from custom_components.tobibox.fehler import TobiboxFehler
from custom_components.tobibox.schutz import Nutzer
from custom_components.tobibox.store import neue_konfig

from .conftest import ereignis_arten, gespeicherte_konfig, warte_auf
from .test_websocket_api import fehler, ok, senden

UID = "e0040312345678ab"
UID2 = "04a1b2c3"
UID3 = "04a1b2c4"
UID4 = "04a1b2c5"
SERIE = {"typ": "serie", "serie": "rabe"}
SERIE_ZWEI = {"typ": "serie", "serie": "zwei"}
FOLGE = {"typ": "folge", "serie": "rabe", "folge": "a.mp3"}
AKTION = {"typ": "aktion", "aktion": "status"}
AKTION_NACHT = {"typ": "aktion", "aktion": "gute_nacht"}


@pytest.fixture
async def ws(integration, nas, lege_mp3, box_fabrik):
    """Serien ``rabe`` (a.mp3, b.mp3) und ``zwei`` (c.mp3), Boxen ``box1`` und ``box2`` online."""
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3", "b.mp3"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    pfad2 = nas.serie("zwei", "zwei", "Zweite Serie", ["c.mp3"])
    lege_mp3(pfad2 / "c.mp3")
    nas.serie("ue", "ue", "Überraschung", typ="ueberraschung")
    await integration.medien.pruefen()
    boxen = {}
    for name in ("box1", "box2"):
        boxen[name] = box_fabrik(name)
        await boxen[name].online()
        await boxen[name].status()
    integration.boxen_fake = boxen
    return integration


@pytest.fixture
def box1(ws):
    return ws.boxen_fake["box1"]


@pytest.fixture
def box2(ws):
    return ws.boxen_fake["box2"]


async def _client(hass, hass_ws_client, name: str):
    nutzer = await hass.auth.async_create_user(name, group_ids=[GROUP_ID_USER])
    refresh = await hass.auth.async_create_refresh_token(nutzer, CLIENT_ID)
    client = await hass_ws_client(hass, hass.auth.async_create_access_token(refresh))
    client.nutzer = nutzer
    return client


@pytest.fixture
async def admin(hass, ws, hass_ws_client):
    return await hass_ws_client(hass)


@pytest.fixture
async def normal(hass, ws, hass_ws_client):
    return await _client(hass, hass_ws_client, "Normal")


@pytest.fixture
async def normal2(hass, ws, hass_ws_client):
    return await _client(hass, hass_ws_client, "Zweiter")


def ziele(hub) -> dict:
    return {u: z["ziel"] for u, z in hub.store.konfig["zuordnungen"].items()}


def warten(hub) -> list[tuple]:
    """(box, ziel) der wartenden Vormerkungen in der Reihenfolge der Anlage."""
    return [(e["box"], e["ziel"]) for e in sorted(hub.store.warteschlange, key=lambda e: e["nr"])]


# --------------------------------------------------------------------------
# Befehle 47 bis 49 und das Objekt „Vormerkung“
# --------------------------------------------------------------------------


async def test_set_list_abbrechen_und_ereignisse(ws, admin, normal, ereignisse):
    r = await ok(normal, "warteschlange/set", box="box1", ziel=FOLGE)
    e = r["eintrag"]
    assert r["gesamt"] == 1
    assert len(e["id"]) == 12 and all(c in "0123456789abcdef" for c in e["id"])
    assert (e["box"], e["ziel"], e["position"]) == ("box1", FOLGE, 1)
    assert (e["serie_name"], e["folge_vorhanden"]) == ("Der kleine Rabe", True)
    assert e["folge_anzeige"] and e["angelegt_am"]
    assert e["angelegt_von"] == {"id": normal.nutzer.id, "name": "Normal"}
    r2 = await ok(admin, "warteschlange/set", box=None, ziel=AKTION)
    assert r2["eintrag"]["position"] == 2 and r2["eintrag"]["box"] is None and r2["eintrag"]["serie_name"] is None
    assert r2["eintrag"]["folge_anzeige"] is None and r2["eintrag"]["folge_vorhanden"] is None
    liste = await ok(normal, "warteschlange/list")
    assert liste["gesamt"] == 2 and [x["id"] for x in liste["eintraege"]] == [e["id"], r2["eintrag"]["id"]]
    assert [x["position"] for x in liste["eintraege"]] == [1, 2]
    assert ereignis_arten(ereignisse, "warteschlange") == ["angelegt", "angelegt"]
    # Abbrechen: jeder Benutzer darf auch Einträge anderer abbrechen; die Positionen rücken nach
    assert await ok(admin, "warteschlange/abbrechen", eintrag_id=e["id"]) == {"abgebrochen": True}
    assert (await ok(normal, "warteschlange/list"))["eintraege"][0]["position"] == 1
    assert await ok(admin, "warteschlange/abbrechen", eintrag_id=e["id"]) == {"abgebrochen": False}  # kein Fehler
    abgebrochen = [x["daten"] for x in ereignisse if x["thema"] == "warteschlange" and x["art"] == "abgebrochen"]
    assert abgebrochen == [{"id": e["id"], "grund": "nutzer"}]  # nur der echte Abbruch meldet ein Ereignis


async def test_set_fehler_und_pruefreihenfolge(ws, admin):
    assert await fehler(admin, "warteschlange/set", box="box9", ziel=SERIE) == "box_unbekannt"
    assert await fehler(admin, "warteschlange/set", box="box1", ziel={"typ": "quatsch"}) == "ziel_ungueltig"
    assert await fehler(admin, "warteschlange/set", box="box1", ziel={"typ": "serie", "serie": "ue"}) == "ziel_ungueltig"  # nie die Überraschungs-Serie
    assert await fehler(admin, "warteschlange/set", box="box1", ziel={"typ": "serie", "serie": "gibtsnicht"}) == "serie_nicht_gefunden"
    assert await fehler(admin, "warteschlange/set", box="box1", ziel={"typ": "folge", "serie": "rabe", "folge": "x.mp3"}) == "folge_nicht_gefunden"
    assert await fehler(admin, "warteschlange/set", ziel=SERIE) == "invalid_format"  # ``box`` ist Pflicht (``null`` = irgendeine)
    assert ws.store.warteschlange == []


async def test_set_ist_idempotent_mit_anfrage_id(ws, admin):
    a = await ok(admin, "warteschlange/set", box="box1", ziel=SERIE, anfrage_id="anfrage-0001")
    b = await ok(admin, "warteschlange/set", box="box1", ziel=SERIE, anfrage_id="anfrage-0001")
    assert a == b and len(ws.store.warteschlange) == 1
    assert await fehler(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI, anfrage_id="anfrage-0001") == "anfrage_id_konflikt"
    assert await fehler(admin, "warteschlange/set", box="box1", ziel=SERIE) == "warteschlange_doppelt"  # ohne ``anfrage_id``


async def test_set_braucht_eine_bereite_konfiguration(ws, admin):
    ws.store.zustand = "leer_neu"
    assert await fehler(admin, "warteschlange/set", box="box1", ziel=AKTION) == "konfig_nicht_bereit"
    assert ws.store.warteschlange == []


async def test_set_auch_fuer_ausgeschaltete_box(ws, admin, box2):
    await box2.online(False)
    await ok(admin, "warteschlange/set", box="box2", ziel=SERIE)  # die Warteschlange liegt in HA


async def test_snapshot_und_hello(ws, admin):
    assert ws.snapshot("warteschlange") == {"gesamt": 0}
    await ok(admin, "warteschlange/set", box=None, ziel=SERIE)
    assert ws.snapshot("warteschlange") == {"gesamt": 1}
    await admin.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["warteschlange"]})
    assert (await admin.receive_json())["success"] is True
    e = (await admin.receive_json())["event"]
    assert (e["thema"], e["art"], e["daten"]) == ("warteschlange", "snapshot", {"gesamt": 1})
    h = await ok(admin, "hello", v=1)
    assert h["grenzen"]["warteschlange_max"] == 5 == const.WARTESCHLANGE_MAX
    assert {"warteschlange", "zuordnung_rueckgaengig"} <= set(h["faehigkeiten"])


# --------------------------------------------------------------------------
# Regel 1: nur unbekannte Tobies, nie umhängen
# --------------------------------------------------------------------------


async def test_regel_1_unbekannter_tobie_wird_zugeordnet(ws, admin, box1, ereignisse):
    r = await ok(admin, "warteschlange/set", box="box1", ziel=FOLGE)
    rev = ws.store.konfig["revision"]
    await box1.unbekannt(UID)
    assert ziele(ws) == {UID: FOLGE}
    assert ws.store.konfig["revision"] == rev + 1
    assert ws.store.warteschlange == []
    assert [k["revision"] for k in box1.konfigs()][-1] == rev + 1  # ``tobibox/config`` veröffentlicht
    assert ws.store.neue_tobies == {}  # keine Karte „Neuer Tobie“
    assert ereignis_arten(ereignisse, "neue_tobies") == []
    assert [a["grund"] for a in box1.acks(UID)] == ["bekannt"]
    abg = [x["daten"] for x in ereignisse if x["thema"] == "warteschlange" and x["art"] == "abgearbeitet"]
    assert abg == [
        {
            "id": r["eintrag"]["id"], "uid": UID, "box": "box1", "ziel": FOLGE, "serie_name": "Der kleine Rabe",
            "folge_anzeige": ws.medien.serien["rabe"].serie.anzeige("a.mp3"), "angelegt_von": r["eintrag"]["angelegt_von"],
        }
    ]
    assert ws.store.konfig["zuordnungen"][UID].get("angelegt_am")  # wie ``zuordnung/set`` ohne Namen


async def test_regel_1_bekannter_tobie_wird_nie_umgehaengt(ws, admin, box1):
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE_ZWEI)
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    rev = ws.store.konfig["revision"]
    await box1.unbekannt(UID)  # die Box meldet ihn (zum Beispiel veraltete Liste) noch einmal als unbekannt
    assert ziele(ws) == {UID: SERIE_ZWEI} and ws.store.konfig["revision"] == rev
    assert len(ws.store.warteschlange) == 1  # der Eintrag bleibt
    assert [a["grund"] for a in box1.acks(UID)] == ["bekannt"]


async def test_regel_1_gelernt_beruehrt_die_warteschlange_nie(ws, admin, box1):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    await box1.unbekannt(UID, art="gelernt", befehl_id="unbekannte-id")
    assert ziele(ws) == {} and len(ws.store.warteschlange) == 1
    assert [a["grund"] for a in box1.acks(UID)] == ["abgelehnt"]  # Weg des Lernmodus (6.2)


async def test_regel_1_ziel_kommt_zwischendurch_unter_der_konfig_sperre(ws, admin, box1):
    """Zwischen Abgleich und Schreiben bekommt die Kennung ein Ziel: „es gibt noch kein Ziel“ wird unter der Sperre geprüft."""
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    eintrag = ws.store.warteschlange[0]
    await ws.zuordnung_setzen(UID, SERIE_ZWEI)
    rev = ws.store.konfig["revision"]
    async with ws.warteschlange.sperre:
        assert await ws.warteschlange._zuordnen("box1", UID, eintrag) is True  # erledigt, nichts geschrieben
    assert ziele(ws) == {UID: SERIE_ZWEI} and ws.store.konfig["revision"] == rev
    assert len(ws.store.warteschlange) == 1


# --------------------------------------------------------------------------
# Regel 2 und 3: welcher Eintrag, zweimal dieselbe Box
# --------------------------------------------------------------------------


async def test_regel_2_aeltester_gewinnt_beispiel_aus_dem_vertrag(ws, admin, box1, box2):
    a = await ok(admin, "warteschlange/set", box=None, ziel=SERIE)  # A „irgendeine Box“
    b = await ok(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)  # B „Box 1“
    await box1.unbekannt(UID)
    assert ziele(ws) == {UID: SERIE}  # der erste Tobie auf Box 1 nimmt A, auch wenn B genauer passt
    assert warten(ws) == [("box1", SERIE_ZWEI)]
    await box1.unbekannt(UID2)
    assert ziele(ws)[UID2] == SERIE_ZWEI and warten(ws) == []
    assert a["eintrag"]["id"] != b["eintrag"]["id"]


async def test_regel_2_box_zwei_nimmt_a_und_danach_wartet_nichts_fuer_box_zwei(ws, admin, box1, box2):
    await ok(admin, "warteschlange/set", box=None, ziel=SERIE)
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)
    await box2.unbekannt(UID)
    assert ziele(ws) == {UID: SERIE}
    await box2.unbekannt(UID2)  # für Box 2 wartet nichts mehr (B gilt nur für Box 1): normaler Weg A
    assert UID2 not in ziele(ws) and UID2 in ws.store.neue_tobies
    assert [a["grund"] for a in box2.acks(UID2)] == ["neu"]
    assert warten(ws) == [("box1", SERIE_ZWEI)]


async def test_regel_2_eintrag_fuer_andere_box_wird_nicht_genommen(ws, admin, box2):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    await box2.unbekannt(UID)
    assert ziele(ws) == {} and UID in ws.store.neue_tobies and len(ws.store.warteschlange) == 1


async def test_regel_3_zweimal_dieselbe_box_der_reihe_nach_und_doppelt(ws, admin, box1):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)  # andere Ziele für dieselbe Box: erlaubt
    assert await fehler(admin, "warteschlange/set", box="box1", ziel=SERIE) == "warteschlange_doppelt"
    await ok(admin, "warteschlange/set", box=None, ziel=SERIE)  # „irgendeine“ und „Box 1“ mit gleichem Ziel sind verschieden
    await ok(admin, "warteschlange/set", box="box2", ziel=SERIE)
    await box1.unbekannt(UID)
    await box1.unbekannt(UID2)
    assert ziele(ws) == {UID: SERIE, UID2: SERIE_ZWEI}


# --------------------------------------------------------------------------
# Regel 4: Höchstzahl, Prüfreihenfolge
# --------------------------------------------------------------------------


async def test_regel_4_hoechstens_fuenf_und_pruefreihenfolge(ws, admin):
    assert const.WARTESCHLANGE_MAX == 5
    for ziel in (SERIE, SERIE_ZWEI, FOLGE, AKTION, AKTION_NACHT):
        await ok(admin, "warteschlange/set", box="box1", ziel=ziel)
    assert await fehler(admin, "warteschlange/set", box="box2", ziel=SERIE) == "warteschlange_voll"
    assert await fehler(admin, "warteschlange/set", box=None, ziel=SERIE) == "warteschlange_voll"  # über alle Boxen
    # ein doppelter Eintrag bei voller Warteschlange meldet „doppelt“; ungültige Eingabe vor beidem
    assert await fehler(admin, "warteschlange/set", box="box1", ziel=SERIE) == "warteschlange_doppelt"
    assert await fehler(admin, "warteschlange/set", box="box9", ziel=SERIE) == "box_unbekannt"
    assert len(ws.store.warteschlange) == 5
    eintrag = (await ok(admin, "warteschlange/list"))["eintraege"][0]
    await ok(admin, "warteschlange/abbrechen", eintrag_id=eintrag["id"])
    await ok(admin, "warteschlange/set", box="box2", ziel=SERIE)  # wieder Platz


# --------------------------------------------------------------------------
# Regel 5: kein Höchstalter
# --------------------------------------------------------------------------


async def test_regel_5_kein_hoechstalter(hass, ws, admin, box1, freezer):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    freezer.tick(timedelta(days=60))
    await hass.async_block_till_done()
    assert len(ws.store.warteschlange) == 1
    await box1.unbekannt(UID)
    assert ziele(ws) == {UID: SERIE}


# --------------------------------------------------------------------------
# Regel 6: jede Meldung „unbekannt“ zählt, auch eine schon gemeldete Kennung
# --------------------------------------------------------------------------


async def test_regel_6_schon_gemeldete_kennung_kann_den_eintrag_nehmen(ws, admin, box1, ereignisse):
    await box1.unbekannt(UID)  # liegt schon in „Neue Tobies“
    assert UID in ws.store.neue_tobies
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    await box1.unbekannt(UID)  # liegt erneut auf
    assert ziele(ws) == {UID: SERIE} and ws.store.neue_tobies == {}
    entfernt = [x["daten"] for x in ereignisse if x["thema"] == "neue_tobies" and x["art"] == "entfernt"]
    assert entfernt == [{"uid": UID, "grund": "zugeordnet"}]  # Regel 7c


async def test_regel_6_ohne_eintrag_aendert_sich_nichts(ws, box1):
    await box1.unbekannt(UID)
    assert UID in ws.store.neue_tobies and ziele(ws) == {}
    assert [a["grund"] for a in box1.acks(UID)] == ["neu"]


# --------------------------------------------------------------------------
# Regel 7: Ablauf bei einem Treffer
# --------------------------------------------------------------------------


async def test_regel_7a_ziel_fehlt_verwerfen_und_naechsten_pruefen(hass, ws, admin, box1, nas, ereignisse):
    erster = await ok(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    shutil.rmtree(nas.medien / "zwei")
    await ws.medien.pruefen()
    liste = (await ok(admin, "warteschlange/list"))["eintraege"]  # Regel 10: die Liste zeigt, dass das Ziel fehlt
    assert liste[0]["serie_name"] is None
    await box1.unbekannt(UID)
    assert ziele(ws) == {UID: SERIE} and ws.store.warteschlange == []
    abgebrochen = [x["daten"] for x in ereignisse if x["thema"] == "warteschlange" and x["art"] == "abgebrochen"]
    assert abgebrochen == [{"id": erster["eintrag"]["id"], "grund": "ziel_fehlt"}]
    assert ereignis_arten(ereignisse, "warteschlange") == ["angelegt", "angelegt", "abgebrochen", "abgearbeitet"]


async def test_regel_7a_kein_weiterer_eintrag_normaler_weg_mit_karte(ws, admin, box1, nas, ereignisse):
    e = await ok(admin, "warteschlange/set", box="box1", ziel={"typ": "folge", "serie": "zwei", "folge": "c.mp3"})
    shutil.rmtree(nas.medien / "zwei")
    await ws.medien.pruefen()
    await box1.unbekannt(UID)
    assert ziele(ws) == {} and ws.store.warteschlange == []
    assert UID in ws.store.neue_tobies  # die normale Karte „Neuer Tobie“
    assert [a["grund"] for a in box1.acks(UID)] == ["neu"]
    assert [x["daten"] for x in ereignisse if x["thema"] == "warteschlange" and x["art"] == "abgebrochen"] == [
        {"id": e["eintrag"]["id"], "grund": "ziel_fehlt"}
    ]


async def test_regel_7a_aktion_braucht_keine_freigabe(ws, admin, box1):
    await ok(admin, "warteschlange/set", box="box1", ziel=AKTION)
    await box1.unbekannt(UID)
    assert ziele(ws) == {UID: AKTION}


async def test_regel_7b_zuordnung_und_austragen_in_einem_schreibvorgang(hass, ws, admin, box1, hass_storage):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)
    gesichert = []
    echt = ws.store._store.async_save

    async def beobachte(daten):
        gesichert.append((sorted(daten["konfig"]["zuordnungen"]), [e["ziel"] for e in daten["warteschlange"]]))
        return await echt(daten)

    ws.store._store.async_save = beobachte
    await box1.unbekannt(UID)
    # genau **ein** Schreibvorgang mit beidem: Zuordnung drin, Eintrag draußen
    assert [g for g in gesichert if g[0] == [UID]] == [([UID], [SERIE_ZWEI])]
    assert gespeicherte_konfig(hass_storage)["zuordnungen"][UID]["ziel"] == SERIE
    assert [e["ziel"] for e in hass_storage["tobibox"]["data"]["warteschlange"]] == [SERIE_ZWEI]


async def test_regel_7b_scheitert_das_speichern_gilt_beides_nicht(ws, admin, box1, caplog):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    rev = ws.store.konfig["revision"]

    async def kaputt(daten):
        raise OSError("Platte voll")

    echt = ws.store._store.async_save
    ws.store._store.async_save = kaputt
    with caplog.at_level(logging.WARNING):
        await box1.unbekannt(UID)
    ws.store._store.async_save = echt
    assert ziele(ws) == {} and ws.store.konfig["revision"] == rev  # nichts geändert
    assert len(ws.store.warteschlange) == 1  # der Eintrag bleibt
    assert UID in ws.store.neue_tobies  # Weg A
    assert [a["grund"] for a in box1.acks(UID)] == ["neu"]
    assert any(r.levelno == logging.WARNING and "Warteschlange" in r.getMessage() for r in caplog.records)  # Regel 7f


async def test_regel_7d_ack_kommt_nach_der_veroeffentlichten_konfiguration(ws, admin, box1):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    n = len(box1.veroeffentlicht())
    await box1.unbekannt(UID)
    neu = box1.reihenfolge()[n:]
    assert neu.index("tobibox/config") < neu.index(f"tobibox/box1/unknown/{UID}/ack")


async def test_regel_7f_konfig_zu_gross_eintrag_bleibt(ws, admin, box1, monkeypatch):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    monkeypatch.setattr(store_modul, "KONFIG_MAX_BYTES", 10)
    await box1.unbekannt(UID)
    assert ziele(ws) == {} and len(ws.store.warteschlange) == 1
    assert UID in ws.store.neue_tobies and [a["grund"] for a in box1.acks(UID)] == ["neu"]


# --------------------------------------------------------------------------
# Regel 8: doppelte Meldung, zwei Boxen gleichzeitig
# --------------------------------------------------------------------------


async def test_regel_8_doppelte_meldung_eine_zuordnung_ein_eintrag(ws, admin, box1):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)
    await box1.unbekannt(UID)
    rev = ws.store.konfig["revision"]
    await box1.unbekannt(UID, zuletzt="2026-11-09T10:00:59.123Z")  # Prellen, erneute Zustellung
    assert ziele(ws) == {UID: SERIE} and ws.store.konfig["revision"] == rev
    assert warten(ws) == [("box1", SERIE_ZWEI)]
    assert [a["grund"] for a in box1.acks(UID)] == ["bekannt", "bekannt"]


async def test_zwei_boxen_gleichzeitig_melden_dieselbe_kennung(hass, ws, admin, box1, box2):
    await ok(admin, "warteschlange/set", box=None, ziel=SERIE)
    await ok(admin, "warteschlange/set", box=None, ziel=SERIE_ZWEI)
    d1 = {"v": 1, "uid": UID, "art": "unbekannt", "zuerst": "2026-11-09T10:00:00Z", "zuletzt": "2026-11-09T10:00:01.000Z", "anzahl": 1, "zeit_ok": True}
    d2 = {**d1, "zuletzt": "2026-11-09T10:00:01.500Z"}
    await asyncio.gather(ws.neue_kennung("box1", UID, d1), ws.neue_kennung("box2", UID, d2))
    await hass.async_block_till_done()
    assert ziele(ws) == {UID: SERIE}  # kein doppeltes Zuordnen
    assert warten(ws) == [(None, SERIE_ZWEI)]  # genau ein Eintrag verbraucht
    assert ws.store.neue_tobies == {}
    assert [a["grund"] for a in box1.acks(UID)] == ["bekannt"] and [a["grund"] for a in box2.acks(UID)] == ["bekannt"]


async def test_zwei_boxen_gleichzeitig_zwei_verschiedene_kennungen(hass, ws, admin, box1, box2):
    await ok(admin, "warteschlange/set", box=None, ziel=SERIE)
    await ok(admin, "warteschlange/set", box=None, ziel=SERIE_ZWEI)
    d = {"v": 1, "art": "unbekannt", "zuerst": "2026-11-09T10:00:00Z", "zuletzt": "2026-11-09T10:00:01.000Z", "anzahl": 1, "zeit_ok": True}
    await asyncio.gather(ws.neue_kennung("box1", UID, {**d, "uid": UID}), ws.neue_kennung("box2", UID2, {**d, "uid": UID2}))
    await hass.async_block_till_done()
    assert ziele(ws) == {UID: SERIE, UID2: SERIE_ZWEI}  # jeder Eintrag genau einmal
    assert ws.store.warteschlange == []


# --------------------------------------------------------------------------
# Regel 9: Lernmodus hat Vorrang
# --------------------------------------------------------------------------


async def test_regel_9_lernmodus_auf_der_box_hat_vorrang(ws, admin, box1, box2):
    await ok(admin, "warteschlange/set", box=None, ziel=SERIE)
    v = await ok(admin, "lernmodus/start", box="box1", ziel=SERIE_ZWEI)
    # eine Meldung ``unbekannt`` für die Box im Lernmodus: die Warteschlange nimmt sie nicht, es gilt Weg A
    await box1.unbekannt(UID)
    assert ziele(ws) == {} and UID in ws.store.neue_tobies and len(ws.store.warteschlange) == 1
    # ``gelernt`` geht an den Lernmodus, die Vormerkung bleibt
    await box1.unbekannt(UID2, art="gelernt", befehl_id=v["befehl_id"])
    assert ziele(ws) == {UID2: SERIE_ZWEI} and len(ws.store.warteschlange) == 1
    # eine andere Box ohne Lernmodus bedient die Vormerkung weiter
    await box2.unbekannt(UID3)
    assert ziele(ws)[UID3] == SERIE and ws.store.warteschlange == []


async def test_regel_9_nach_dem_lernmodus_ist_es_wieder_normal(ws, admin, box1):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    await ok(admin, "lernmodus/start", box="box1", ziel=SERIE_ZWEI)
    assert (await ok(admin, "lernmodus/abbrechen", box="box1")) == {"abgebrochen": True}
    await box1.unbekannt(UID)
    assert ziele(ws) == {UID: SERIE}
    # und ``lernmodus/start`` wird durch Vormerkungen nicht verhindert
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)
    await ok(admin, "lernmodus/start", box="box1", ziel=SERIE)


# --------------------------------------------------------------------------
# Regel 10: Ziel oder Box ist weg
# --------------------------------------------------------------------------


async def test_regel_10_serie_kommt_zurueck_eintrag_gilt_weiter(ws, admin, box1, nas, lege_mp3):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)
    ordner = nas.medien / "zwei"
    schatten = nas.basis / "weg"
    shutil.move(ordner, schatten)
    await ws.medien.pruefen()
    liste = (await ok(admin, "warteschlange/list"))["eintraege"]
    assert liste[0]["serie_name"] is None
    shutil.move(schatten, ordner)  # „aus dem Papierkorb zurück“, bevor ein Tobie aufliegt
    await ws.medien.pruefen()
    assert (await ok(admin, "warteschlange/list"))["eintraege"][0]["serie_name"] == "Zweite Serie"
    await box1.unbekannt(UID)
    assert ziele(ws) == {UID: SERIE_ZWEI}


async def test_regel_10_folge_fehlt_zeigt_die_liste(ws, admin, nas):
    await ok(admin, "warteschlange/set", box="box1", ziel=FOLGE)
    (nas.medien / "rabe" / "a.mp3").unlink()
    await ws.medien.pruefen()
    e = (await ok(admin, "warteschlange/list"))["eintraege"][0]
    assert (e["folge_vorhanden"], e["folge_anzeige"]) == (False, None)


async def test_regel_10_box_nicht_mehr_eingerichtet_wird_beim_start_verworfen(hass, starte_integration, vorab_speicher, caplog):
    k = neue_konfig({})
    eintrag = {"nr": 3, "angelegt_von": None, "angelegt_am": "2026-11-09T10:00:00Z"}
    vorab_speicher(
        {
            "konfig": k,
            "warteschlange_nr": 3,
            "warteschlange": [
                {"id": "aaaaaaaaaaaa", "box": "box9", "ziel": SERIE, **eintrag},
                {"id": "bbbbbbbbbbbb", "box": "box1", "ziel": SERIE, **{**eintrag, "nr": 2}},
                {"id": "cccccccccccc", "box": None, "ziel": AKTION, **{**eintrag, "nr": 1}},
            ],
        }
    )
    with caplog.at_level(logging.INFO):
        hub = await starte_integration()
    assert [e["id"] for e in sorted(hub.store.warteschlange, key=lambda e: e["nr"])] == ["cccccccccccc", "bbbbbbbbbbbb"]
    assert any("aaaaaaaaaaaa" in r.getMessage() for r in caplog.records)


# --------------------------------------------------------------------------
# Regel 11: Neustart
# --------------------------------------------------------------------------


async def test_regel_11_jede_aenderung_wird_sofort_gespeichert(ws, admin, box1, hass_storage):
    r = await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    gesichert = hass_storage["tobibox"]["data"]  # ohne auf den verzögerten Zeitgeber zu warten
    assert [e["id"] for e in gesichert["warteschlange"]] == [r["eintrag"]["id"]] and gesichert["warteschlange_nr"] == 1
    await ok(admin, "warteschlange/abbrechen", eintrag_id=r["eintrag"]["id"])
    assert hass_storage["tobibox"]["data"]["warteschlange"] == []
    assert hass_storage["tobibox"]["data"]["warteschlange_nr"] == 1  # die laufende Nummer geht nie zurück


async def test_regel_11_eintraege_ueberleben_den_neustart(hass, starte_integration, vorab_speicher, box_fabrik):
    vorab_speicher(
        {
            "konfig": neue_konfig({}),
            "warteschlange_nr": 7,
            "warteschlange": [
                {"id": "aaaaaaaaaaaa", "box": "box1", "ziel": AKTION_NACHT, "nr": 6, "angelegt_von": {"id": "u1", "name": "Mama"}, "angelegt_am": "2026-11-09T10:00:00Z"},
                {"id": "bbbbbbbbbbbb", "box": None, "ziel": AKTION, "nr": 7, "angelegt_von": None, "angelegt_am": "2026-11-09T10:01:00Z"},
                {"kaputt": True},
            ],
        }
    )
    hub = await starte_integration()
    assert [e["id"] for e in hub.store.warteschlange] == ["aaaaaaaaaaaa", "bbbbbbbbbbbb"]  # Kaputtes fällt weg
    liste = hub.warteschlange.liste()
    assert [(e["id"], e["position"], e["angelegt_von"]) for e in liste["eintraege"]] == [
        ("aaaaaaaaaaaa", 1, {"id": "u1", "name": "Mama"}),
        ("bbbbbbbbbbbb", 2, None),
    ]
    box = box_fabrik("box1")
    await box.online()
    await box.unbekannt(UID)  # es läuft auch nach dem Neustart
    assert hub.store.konfig["zuordnungen"][UID]["ziel"] == AKTION_NACHT  # der ältere Eintrag (Nr. 6) gewinnt
    e = await hub.warteschlange.setzen("box1", AKTION)
    assert e["eintrag"]["position"] == 2 and hub.store.warteschlange_nr == 8  # bbbbbbbbbbbb wartet noch


async def test_regel_11_neustart_der_integration_mit_denselben_daten(hass, ws, admin, hass_storage, starte_integration):
    from custom_components.tobibox.const import DOMAIN

    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    await ok(admin, "warteschlange/set", box=None, ziel=AKTION)
    ids = [e["id"] for e in ws.store.warteschlange]
    eintrag = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_unload(eintrag.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    neu = hass.data[DOMAIN]
    assert neu is not ws and [e["id"] for e in neu.store.warteschlange] == ids


# --------------------------------------------------------------------------
# Regel 12: Rückgängig und ``als_neu``
# --------------------------------------------------------------------------


async def test_regel_12_rueckgaengig_mit_als_neu_bringt_die_karte_zurueck(ws, admin, box1, ereignisse):
    await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
    await box1.unbekannt(UID)
    assert ws.store.neue_tobies == {}
    r = await ok(admin, "zuordnung/remove", uid=UID, erwartet_ziel=SERIE, als_neu={"box": "box1"})
    assert r["geaendert"] is True and ziele(ws) == {}
    eintrag = ws.store.neue_tobies[UID]
    assert set(eintrag["boxen"]) == {"box1"}
    b = eintrag["boxen"]["box1"]
    assert b["zuerst"] == b["zuletzt"] and b["anzahl"] == 1 and b["zeit_ok"] is True
    neu = [x["daten"] for x in ereignisse if x["thema"] == "neue_tobies" and x["art"] == "neu"]
    assert len(neu) == 1 and neu[0]["eintrag"]["uid"] == UID
    assert [a for a in box1.acks(UID)] and box1.acks(UID)[-1]["grund"] == "bekannt"  # die Box bekommt keine Nachricht dazu
    # meldet die Box ihn später selbst, gilt es als ``aktualisiert``
    await box1.unbekannt(UID)
    assert [x["art"] for x in ereignisse if x["thema"] == "neue_tobies"][-1] == "aktualisiert"


async def test_als_neu_ohne_aenderung_und_ohne_das_feld(ws, admin):
    r = await ok(admin, "zuordnung/remove", uid=UID, als_neu={"box": "box1"})  # gab es nicht
    assert r["geaendert"] is False and ws.store.neue_tobies == {}
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE)
    await ok(admin, "zuordnung/remove", uid=UID)  # ohne das Feld bleibt alles wie bisher
    assert ws.store.neue_tobies == {}


async def test_als_neu_unbekannte_box_aendert_nichts(ws, admin):
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE)
    assert await fehler(admin, "zuordnung/remove", uid=UID, als_neu={"box": "box9"}) == "box_unbekannt"
    assert ziele(ws) == {UID: SERIE}
    assert await fehler(admin, "zuordnung/remove", uid=UID, als_neu={"box": 5}) == "invalid_format"
    assert await fehler(admin, "zuordnung/remove", uid=UID, als_neu={}) == "invalid_format"


async def test_als_neu_nicht_admin_mit_erwartet_ziel(ws, admin, normal):
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE)
    assert await fehler(normal, "zuordnung/remove", uid=UID, als_neu={"box": "box1"}) == "unauthorized"
    await ok(normal, "zuordnung/remove", uid=UID, erwartet_ziel=SERIE, als_neu={"box": "box1"})
    assert UID in ws.store.neue_tobies


# --------------------------------------------------------------------------
# Regel 13: Protokoll, keine Mitteilung
# --------------------------------------------------------------------------


async def test_regel_13_protokollzeilen_und_keine_mitteilung(hass, ws, normal, admin, box1, caplog):
    from homeassistant.components import persistent_notification

    mitteilungen_vorher = set(persistent_notification._async_get_or_create_notifications(hass))
    with caplog.at_level(logging.INFO, logger="custom_components.tobibox.warteschlange"):
        r = await ok(normal, "warteschlange/set", box="box1", ziel=FOLGE)
        await ok(admin, "warteschlange/abbrechen", eintrag_id=r["eintrag"]["id"])
        await ok(admin, "warteschlange/set", box="box1", ziel=SERIE)
        await box1.unbekannt(UID)
    zeilen = [rec.getMessage() for rec in caplog.records if rec.levelno == logging.INFO]
    anlegen = [z for z in zeilen if "legt an" in z]
    assert len(anlegen) == 2 and "Normal" in anlegen[0] and "box1" in anlegen[0] and r["eintrag"]["id"] in anlegen[0]
    abbrechen = [z for z in zeilen if "bricht ab" in z]
    assert len(abbrechen) == 1 and r["eintrag"]["id"] in abbrechen[0]
    treffer = [z for z in zeilen if "Treffer" in z]
    assert len(treffer) == 1 and UID in treffer[0] and "box1" in treffer[0]
    assert set(persistent_notification._async_get_or_create_notifications(hass)) == mitteilungen_vorher  # keine Mitteilung


# --------------------------------------------------------------------------
# Regel 14: Rechte und Mengen
# --------------------------------------------------------------------------


async def test_regel_14_rechte_alle_drei_befehle_fuer_jeden_lernmodus_nur_admin(ws, admin, normal):
    for client in (admin, normal):
        r = await ok(client, "warteschlange/set", box="box2", ziel=SERIE)
        await ok(client, "warteschlange/list")
        assert await ok(client, "warteschlange/abbrechen", eintrag_id=r["eintrag"]["id"]) == {"abgebrochen": True}
    # Lernmodus: nur Administratoren, ein Benutzer bekommt ``unauthorized``
    assert await fehler(normal, "lernmodus/start", box="box1", ziel=SERIE) == "unauthorized"
    assert await fehler(normal, "lernmodus/antwort", befehl_id="x", ueberschreiben=True) == "unauthorized"
    assert await fehler(normal, "lernmodus/abbrechen", box="box1") == "unauthorized"
    assert ws.lernmodus.offener_vorgang("box1") is None
    await ok(admin, "lernmodus/start", box="box1", ziel=SERIE)
    # jeder darf Einträge anderer abbrechen
    r = await ok(admin, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)
    assert await ok(normal, "warteschlange/abbrechen", eintrag_id=r["eintrag"]["id"]) == {"abgebrochen": True}


async def test_regel_14_mengen_set_und_abbrechen_zusammen(hass, ws, admin, normal, normal2, freezer):
    assert const.WARTESCHLANGE_AENDERUNGEN_JE_MINUTE == 30
    for _ in range(15):
        r = await ok(normal, "warteschlange/set", box="box1", ziel=SERIE)
        await ok(normal, "warteschlange/abbrechen", eintrag_id=r["eintrag"]["id"])
    assert await fehler(normal, "warteschlange/set", box="box1", ziel=SERIE) == "zu_viele_aenderungen"
    assert await fehler(normal, "warteschlange/abbrechen", eintrag_id="0123456789ab") == "zu_viele_aenderungen"
    await ok(normal, "warteschlange/list")  # Lesen zählt nicht
    # je Benutzer: ein zweiter Benutzer und der Administrator sind frei
    await ok(normal2, "warteschlange/set", box="box1", ziel=SERIE)
    for _ in range(31):
        r = await ok(admin, "warteschlange/set", box="box2", ziel=SERIE_ZWEI)
        await ok(admin, "warteschlange/abbrechen", eintrag_id=r["eintrag"]["id"])
    freezer.tick(timedelta(seconds=61))
    await hass.async_block_till_done()
    await ok(normal, "warteschlange/set", box="box2", ziel=AKTION)


async def test_regel_14_ein_treffer_zaehlt_nicht_und_konflikte_auch_nicht(ws, normal, box1):
    await ok(normal, "warteschlange/set", box="box1", ziel=SERIE)
    await ok(normal, "warteschlange/set", box="box1", ziel=SERIE_ZWEI)
    assert await fehler(normal, "warteschlange/set", box="box1", ziel=SERIE_ZWEI) == "warteschlange_doppelt"  # Konflikte buchen nichts
    await box1.unbekannt(UID)  # ein Treffer ist keine Handlung eines Benutzers
    assert ziele(ws) == {UID: SERIE}
    assert ws.schutz.mengen.summe("warteschlange", normal.nutzer.id, 60) == 2


async def test_hub_ohne_benutzer_ist_frei(ws):
    for _ in range(40):
        e = await ws.warteschlange.setzen("box1", SERIE)
        await ws.warteschlange.abbrechen(e["eintrag"]["id"])
    with pytest.raises(TobiboxFehler):
        await ws.warteschlange.setzen("box9", SERIE)
    assert Nutzer(None, None, True).geloescht_von is None


# --------------------------------------------------------------------------
# Mengen: wie viel passt in die Liste
# --------------------------------------------------------------------------


async def test_mengen_fuenf_eintraege_fuenf_tobies_nacheinander(ws, admin, box1, box2):
    ziel_liste = [SERIE, SERIE_ZWEI, FOLGE, AKTION, AKTION_NACHT]
    for z in ziel_liste:
        await ok(admin, "warteschlange/set", box=None, ziel=z)
    for uid, box in zip((UID, UID2, UID3, UID4, "04a1b2c6"), (box1, box2, box1, box2, box1), strict=True):
        await box.unbekannt(uid)
    assert list(ziele(ws).values()) == ziel_liste
    assert ws.store.warteschlange == [] and ws.store.neue_tobies == {}
    assert ws.store.konfig["revision"] == 1 + 5
