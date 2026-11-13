"""Erweiterungen v1.1 des Vertrags W (Abschnitt 10, 09.11.) und Folgen daraus.

* ``tobibox/eingang/entfernen``
* ``tobibox/zuordnung/list`` mit Filter ``uid``
* ``tobibox/konfig/get``
* Ereignis „Upload fertig“ mit ``datei`` und ``pruefung``
* neue Werte in ``hello.faehigkeiten``
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import ANY, patch

import pytest

from custom_components.tobibox import ffprobe

from .conftest import braucht_ffmpeg, ereignis_arten, erzeuge_audio
from .test_upload import formular
from .test_websocket_api import fehler, ok, senden

UID = "e0040312345678ab"
UID2 = "04a1b2c3"
SERIE = {"typ": "serie", "serie": "rabe"}
FOLGE = {"typ": "folge", "serie": "rabe", "folge": "a.mp3"}
AKTION = {"typ": "aktion", "aktion": "status"}

NEUE_FAEHIGKEITEN = ["einstellungen", "eingang_entfernen", "zuordnung_uid", "konfig_lesen", "upload_fertig_details"]


@pytest.fixture
async def api(hass, integration, nas, lege_mp3, box_fabrik, hass_ws_client):
    """Administrator; Serie ``rabe`` mit Folgen ``a.mp3`` und ``b.mp3``, Box ``box1`` online."""
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3", "b.mp3"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    await integration.medien.pruefen()
    await box_fabrik("box1").online()
    return await hass_ws_client(hass)


@pytest.fixture
async def api_lesend(hass, integration, hass_ws_client, hass_read_only_access_token):
    return await hass_ws_client(hass, hass_read_only_access_token)


async def test_hello_sagt_die_neuen_faehigkeiten_zu(api, api_lesend):
    for client in (api, api_lesend):
        f = (await ok(client, "hello", v=1))["faehigkeiten"]
        assert f[-11:-6] == NEUE_FAEHIGKEITEN  # am Ende folgen ``konfig_staende`` (A1), ``bibliothek`` (A3), ``einsortier_wunsch`` (A3d), ``cover`` (A4) und seit 13.11. ``warteschlange`` und ``zuordnung_rueckgaengig`` (A9c)
        assert len(set(f)) == len(f)
    assert (await ok(api, "hello", v=1))["v"] == 1  # additiv: die Version bleibt


# --------------------------------------------------------------------------
# konfig/get
# --------------------------------------------------------------------------


async def test_konfig_get_liefert_den_konfig_stand(api, api_lesend, integration):
    for client in (api, api_lesend):  # Lesen dürfen alle
        r = await ok(client, "konfig/get")
        assert r == {"konfig": integration.konfig_stand()}
        assert r["konfig"].keys() == {"revision", "liste_id", "zustand", "export_ok", "export_geschrieben_am"}
    await ok(api, "zuordnung/set", uid=UID, ziel=SERIE, erwartet_ziel=None)
    assert (await ok(api_lesend, "konfig/get"))["konfig"]["revision"] == 2
    integration.store.zustand = "export_neuer"
    assert (await ok(api_lesend, "konfig/get"))["konfig"]["zustand"] == "export_neuer"  # auch außerhalb von ``ok``
    assert await fehler(api, "konfig/get", x=1) == "invalid_format"


# --------------------------------------------------------------------------
# zuordnung/list mit uid
# --------------------------------------------------------------------------


async def test_zuordnung_list_filter_uid(api):
    await ok(api, "zuordnung/set", uid=UID, ziel=SERIE, name="Rabe aus Holz", erwartet_ziel=None)
    await ok(api, "zuordnung/set", uid=UID2, ziel=FOLGE, erwartet_ziel=None)
    await ok(api, "zuordnung/set", uid="04ffeedd", ziel=AKTION, erwartet_ziel=None)
    r = await ok(api, "zuordnung/list", uid=UID)
    assert r["gesamt"] == 1
    # Vertrag W 12.11., angelegt_am: Anlegen setzt den Zeitstempel
    assert r["zuordnungen"] == [{"uid": UID, "name": "Rabe aus Holz", "ziel": SERIE, "serie_name": "Der kleine Rabe", "folge_anzeige": None, "folge_vorhanden": None, "angelegt_am": ANY, "vorher": None, "cover_stand": None}]  # K6 (13.11.); K8 (13.11.): cover_stand (ohne Cover null)
    assert r["konfig"]["revision"] == 4
    z = (await ok(api, "zuordnung/list", uid=UID2))["zuordnungen"][0]
    assert z["folge_vorhanden"] is True and z["ziel"] == FOLGE
    # unbekannte Kennung und andere Schreibweise: leere Liste, kein Fehler (genau eine Zuordnung oder keine)
    assert (await ok(api, "zuordnung/list", uid="0123456789abcdef")) | {"konfig": None} == {"konfig": None, "zuordnungen": [], "gesamt": 0}
    assert (await ok(api, "zuordnung/list", uid=UID.upper()))["gesamt"] == 0
    # zusammen mit den anderen Filtern gilt „und“
    assert (await ok(api, "zuordnung/list", uid=UID, serie_id="rabe"))["gesamt"] == 1
    assert (await ok(api, "zuordnung/list", uid="04ffeedd", serie_id="rabe"))["gesamt"] == 0
    assert (await ok(api, "zuordnung/list", uid=UID, limit=1, offset=1))["zuordnungen"] == []
    # ohne uid wie bisher
    assert (await ok(api, "zuordnung/list"))["gesamt"] == 3
    assert await fehler(api, "zuordnung/list", uid=5) == "invalid_format"


# --------------------------------------------------------------------------
# eingang/entfernen
# --------------------------------------------------------------------------


async def blockierter_eintrag(integration, nas) -> dict:
    (nas.eingang / "Nur Bilder").mkdir()
    (nas.eingang / "Nur Bilder" / "cover.jpg").write_bytes(b"x")
    await integration.eingang.durchlauf_und_warten(None, True)
    liste = (await integration.eingang.liste("offen", 50, 0))["eintraege"]
    assert [e["status"] for e in liste] == ["blockiert"]
    return liste[0]


async def test_eingang_entfernen_legt_den_eintrag_in_den_papierkorb(hass, api, integration, nas, ereignisse):
    eintrag = await blockierter_eintrag(integration, nas)
    r = await ok(api, "eingang/entfernen", eintrag_id=eintrag["id"], bestaetigt=True)
    assert r["eintrag"]["typ"] == "eingang" and r["eintrag"]["grund"] == "manuell" and r["eintrag"]["anzeige"] == "Nur Bilder"
    assert r["eintrag"]["art"] == "ordner" and r["eintrag"]["serie_id"] is None
    assert not (nas.eingang / "Nur Bilder").exists()
    assert (await ok(api, "eingang/list"))["eintraege"] == []
    korb = (await ok(api, "papierkorb/list"))["eintraege"]
    assert [e["id"] for e in korb] == [r["eintrag"]["id"]]
    assert (nas.papierkorb / r["eintrag"]["id"] / "inhalt" / "Nur Bilder" / "cover.jpg").exists()
    await hass.async_block_till_done()
    assert "geaendert" in ereignis_arten(ereignisse, "eingang") and "papierkorb_geaendert" in ereignis_arten(ereignisse, "medien")
    # zweiter Aufruf: der Eintrag ist weg
    assert await fehler(api, "eingang/entfernen", eintrag_id=eintrag["id"], bestaetigt=True) == "eintrag_nicht_gefunden"
    # Weg zurück: wiederherstellen legt ihn wieder in den Eingang
    await ok(api, "papierkorb/restore", eintrag_id=r["eintrag"]["id"])
    assert (nas.eingang / "Nur Bilder" / "cover.jpg").exists()


async def test_eingang_entfernen_einzelne_datei_und_beim_neuen_durchlauf_nicht_wieder_da(api, integration, nas):
    (nas.eingang / "notiz.txt").write_text("x")
    await integration.eingang.durchlauf_und_warten(None, True)
    e = (await ok(api, "eingang/list"))["eintraege"][0]
    r = await ok(api, "eingang/entfernen", eintrag_id=e["id"], bestaetigt=True)
    assert r["eintrag"]["art"] == "datei" and not (nas.eingang / "notiz.txt").exists()
    await integration.eingang.durchlauf_und_warten(None, True)
    assert (await ok(api, "eingang/list"))["eintraege"] == []


async def test_eingang_entfernen_fehler_und_rechte(api, api_lesend, integration, nas):
    eintrag = await blockierter_eintrag(integration, nas)
    assert await fehler(api, "eingang/entfernen", eintrag_id=eintrag["id"]) == "invalid_format"  # bestaetigt fehlt
    assert await fehler(api, "eingang/entfernen", eintrag_id=eintrag["id"], bestaetigt=False) == "invalid_format"
    assert await fehler(api, "eingang/entfernen", bestaetigt=True) == "invalid_format"
    assert await fehler(api, "eingang/entfernen", eintrag_id=eintrag["id"], bestaetigt=True, x=1) == "invalid_format"
    assert await fehler(api_lesend, "eingang/entfernen", eintrag_id=eintrag["id"], bestaetigt=True) == "unauthorized"
    assert await fehler(api, "eingang/entfernen", eintrag_id="000000000000", bestaetigt=True) == "eintrag_nicht_gefunden"
    assert await fehler(api, "eingang/entfernen", eintrag_id="../../etc", bestaetigt=True) == "eintrag_nicht_gefunden"
    assert (nas.eingang / "Nur Bilder" / "cover.jpg").exists()  # nichts wurde angefasst


async def test_eingang_entfernen_waehrend_des_einsortierens_geht_nicht(api, integration, nas):
    eintrag = await blockierter_eintrag(integration, nas)
    integration.eingang.laeuft = True
    try:
        assert await fehler(api, "eingang/entfernen", eintrag_id=eintrag["id"], bestaetigt=True) == "sortierung_laeuft"
    finally:
        integration.eingang.laeuft = False
    assert (nas.eingang / "Nur Bilder").exists()


@braucht_ffmpeg
async def test_eingang_entfernen_entfernt_die_benachrichtigung_und_vorgaben(hass, api, integration, nas):
    from homeassistant.components import persistent_notification

    erzeuge_audio_ordner = nas.eingang / "Kaputt"
    erzeuge_audio_ordner.mkdir()
    erzeuge_audio(erzeuge_audio_ordner / "a.mp3", album="X", album_artist="Autor")
    with patch("custom_components.tobibox.eingang.ffprobe.pruefe_datei", return_value=ffprobe.Pruefung("warnung", ffprobe.KOPIERSCHUTZ)):
        await integration.eingang.durchlauf_und_warten(None, True)  # Kopierschutz: bleibt blockiert im Eingang liegen
    e = (await ok(api, "eingang/list"))["eintraege"][0]
    assert e["status"] == "blockiert"
    nid = f"tobibox_eingang_{e['id']}"
    await hass.async_block_till_done()
    assert nid in persistent_notification._async_get_or_create_notifications(hass)
    await ok(api, "eingang/entfernen", eintrag_id=e["id"], bestaetigt=True)
    await hass.async_block_till_done()
    assert nid not in persistent_notification._async_get_or_create_notifications(hass)
    assert "Kaputt" not in integration.eingang.eintraege and not (nas.eingang / "Kaputt").exists()


# --------------------------------------------------------------------------
# Upload fertig: datei und pruefung im Ereignis
# --------------------------------------------------------------------------


@pytest.fixture
def mp3(tmp_path) -> Path:
    return erzeuge_audio(tmp_path / "quelle.mp3", frequenz=333, album="Folge 1", album_artist="Upload-Serie", title="Folge 1: Der Anfang")


async def fortschritte(ws, anzahl: int) -> list[dict]:
    aus: list[dict] = []
    for _ in range(10):
        e = (await ws.receive_json())["event"]
        if e["thema"] == "upload":
            aus.append(e["daten"])
        if len(aus) == anzahl:
            break
    return aus


@braucht_ffmpeg
async def test_upload_fertig_traegt_dateiname_und_pruefung(hass, integration, hass_ws_client, hass_client, mp3):
    client = await hass_client()
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["upload"]})
    assert (await ws.receive_json())["success"] is True
    await ws.receive_json()  # Snapshot
    antwort = await client.post("/api/tobibox/upload", data=formular(mp3, "Meine Folge.mp3", upload_id="v11-ereignis-0001"))
    assert antwort.status == 200
    pruefe, fertig = await fortschritte(ws, 2)
    assert pruefe["zustand"] == "pruefe" and "datei" not in pruefe and "pruefung" not in pruefe  # nur das Ende trägt die Angaben
    assert fertig["zustand"] == "fertig" and fertig["upload_id"] == "v11-ereignis-0001" and fertig["code"] is None
    assert fertig["datei"] == "Meine Folge.mp3" and fertig["pruefung"] == "ok"
    assert fertig["bytes"] == mp3.stat().st_size
    # die HTTP-Antwort und das Ereignis nennen dasselbe
    daten = await antwort.json()
    assert (daten["eingang_name"], daten["pruefung"]) == (fertig["datei"], fertig["pruefung"])


@braucht_ffmpeg
async def test_upload_fertig_mit_suffix_und_warnung(hass, integration, hass_ws_client, hass_client, mp3, nas):
    client = await hass_client()
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["upload"]})
    await ws.receive_json()
    await ws.receive_json()
    (nas.eingang / "doppelt.mp3").write_bytes(b"da")
    with patch("custom_components.tobibox.http.ffprobe.pruefe_datei", return_value=ffprobe.Pruefung("warnung", ffprobe.KOPIERSCHUTZ)):
        antwort = await client.post("/api/tobibox/upload", data=formular(mp3, "doppelt.mp3", upload_id="v11-ereignis-0002"))
    assert antwort.status == 200
    _pruefe, fertig = await fortschritte(ws, 2)
    assert fertig["datei"] == "doppelt (2).mp3"  # der Name im Eingang, nicht der gesendete
    assert fertig["pruefung"] == "warnung"


@braucht_ffmpeg
async def test_upload_fehler_hat_keine_fertig_angaben(hass, integration, hass_ws_client, hass_client, mp3):
    client = await hass_client()
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["upload"]})
    await ws.receive_json()
    await ws.receive_json()
    with patch("custom_components.tobibox.http.ffprobe.pruefe_datei", return_value=ffprobe.Pruefung("ungueltig", None)):
        antwort = await client.post("/api/tobibox/upload", data=formular(mp3, "x.mp3", upload_id="v11-ereignis-0003"))
    assert antwort.status == 415
    _pruefe, ende = await fortschritte(ws, 2)
    assert ende["zustand"] == "fehler" and ende["code"] == "format_nicht_erlaubt"
    assert "datei" not in ende and "pruefung" not in ende


# --------------------------------------------------------------------------
# Namen: Serien-Ordner „.“ und „..“ (Fix 09.11., AP 4.7)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", [".", "..", " . ", "...", "_"])
async def test_serie_mit_punktnamen_ergibt_keinen_reservierten_ordner(api, nas, name):
    antwort = await senden(api, "serie/create", name=name)
    assert antwort["success"] is False and antwort["error"]["code"] == "name_ungueltig"
    assert sorted(p.name for p in nas.medien.iterdir() if p.is_dir() and not p.name.startswith("_")) == ["rabe"]
    assert not (nas.medien / "_ordner").exists()


async def test_serie_mit_geraetename_bekommt_den_unterstrich_hinten(api, nas):
    r = await ok(api, "serie/create", name="CON.txt")
    assert r["serie"]["ordner"] == "CON_.txt"
    assert (nas.medien / "CON_.txt" / "serie.json").exists()
    assert json.loads((nas.medien / "CON_.txt" / "serie.json").read_text("utf-8"))["name"] == "CON.txt"
