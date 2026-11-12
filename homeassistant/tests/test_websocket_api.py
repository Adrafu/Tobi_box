"""Jeder Befehl aus Vertrag W (Abschnitt 3): gültig und ungültig, Rechte, ``anfrage_id``, Ereignisse."""

from __future__ import annotations

import json
from typing import Any

import pytest
from homeassistant.components import mqtt as ha_mqtt
from unittest.mock import ANY, patch

from .conftest import braucht_ffmpeg, erzeuge_audio, warte_auf

UID = "e0040312345678ab"
UID2 = "04a1b2c3"
SERIE = {"typ": "serie", "serie": "rabe"}
FOLGE = {"typ": "folge", "serie": "rabe", "folge": "a.mp3"}
AKTION = {"typ": "aktion", "aktion": "status"}


async def senden(client, befehl: str, /, **felder: Any) -> dict[str, Any]:
    """Sendet einen Befehl und gibt die Antwort zurück; Ereignisse, die vorher kommen, merkt sich ``client.gesammelt``."""
    await client.send_json_auto_id({"type": f"tobibox/{befehl}", **felder})
    while True:
        nachricht = await client.receive_json()
        if nachricht["type"] == "event":
            if not hasattr(client, "gesammelt"):
                client.gesammelt = []
            client.gesammelt.append(nachricht["event"])
            continue
        return nachricht


async def naechstes_ereignis(client) -> dict[str, Any]:
    gesammelt = getattr(client, "gesammelt", [])
    if gesammelt:
        return gesammelt.pop(0)
    return (await client.receive_json())["event"]


async def ok(client, befehl: str, /, **felder: Any) -> Any:
    antwort = await senden(client, befehl, **felder)
    assert antwort["success"] is True, antwort
    return antwort["result"]


async def fehler(client, befehl: str, /, **felder: Any) -> str:
    antwort = await senden(client, befehl, **felder)
    assert antwort["success"] is False, antwort
    assert antwort["error"]["message"]  # Klartext für Eltern
    return antwort["error"]["code"]


@pytest.fixture
async def bestand(integration, nas, lege_mp3, box_fabrik):
    """Serie ``rabe`` mit Folgen ``a.mp3`` und ``b.mp3``, Box ``box1`` online."""
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3", "b.mp3"], folgen_info={"a.mp3": {"anzeige": "Eins", "nummer": 1}})
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    await integration.medien.pruefen()
    await box_fabrik("box1").online()


@pytest.fixture
async def api(hass, bestand, hass_ws_client):
    """Client eines Administrators."""
    return await hass_ws_client(hass)


@pytest.fixture
async def api_lesend(hass, bestand, hass_ws_client, hass_read_only_access_token):
    """Client eines Nutzers ohne Administratorrechte."""
    return await hass_ws_client(hass, hass_read_only_access_token)


# --------------------------------------------------------------------------
# 1 hello, 2 subscribe
# --------------------------------------------------------------------------


async def test_hello(api, api_lesend, integration):
    r = await ok(api, "hello", v=1)
    assert r["v"] == 1
    assert r["version"] == "0.1.0"  # aus manifest.json
    assert r["darf_schreiben"] is True
    assert r["boxen"] == ["box1", "box2"]
    assert r["faehigkeiten"] == [
        "medien", "upload", "zuordnung", "tobie_namen", "neue_tobies", "lernmodus", "boxen", "papierkorb",
        "liste_ausrollen", "konfig_export", "sync", "eingang", "korrektur", "serie_loeschen",
        "einstellungen", "eingang_entfernen", "zuordnung_uid", "konfig_lesen", "upload_fertig_details",  # AP 4.7, Erweiterungen v1.1
        "konfig_staende",  # 12.11., Paket A1: frühere Stände der Liste
        "bibliothek",  # 12.11., Paket A3: Art, Suche, Filter, Blättern
        "einsortier_wunsch",  # 12.11., Paket A3d: Upload mit Wunsch (ohne Befehl 43)
        "cover",  # 12.11., Paket A4: Foto-Upload, Cover-Ansicht, Befehl 44
    ]
    assert r["konfig"]["zustand"] == "ok" and r["konfig"]["revision"] == 1
    g = r["grenzen"]
    # Vertrag W 12.11.: Grenze 2 GiB; der Test-Eintrag speichert noch 500, die Migration hebt ihn an
    assert g["upload_max_bytes"] == 2 * 1024**3 and g["upload_block_bytes"] == 1048576 and g["upload_parallel"] == 2
    assert g["endungen"] == ["mp3", "m4a", "m4b", "aac", "flac", "ogg", "opus", "wav"]
    assert (g["serie_name_max"], g["folge_anzeige_max"], g["tobie_name_max"], g["name_max_bytes"], g["limit_max"]) == (100, 200, 60, 255, 100)
    assert (await ok(api_lesend, "hello", v=1))["darf_schreiben"] is False


async def test_hello_neuere_seite_bekommt_trotzdem_eine_antwort_und_eingaben_sind_streng(api):
    assert (await ok(api, "hello", v=7))["v"] == 1
    assert await fehler(api, "hello") == "invalid_format"
    assert await fehler(api, "hello", v="1") == "invalid_format"
    assert await fehler(api, "hello", v=True) == "invalid_format"
    assert await fehler(api, "hello", v=1, unbekannt=1) == "invalid_format"  # unbekannte Eingabefelder lehnt HA ab


async def test_unbekannter_befehl(api):
    await api.send_json_auto_id({"type": "tobibox/gibtsnicht"})
    assert (await api.receive_json())["error"]["code"] == "unknown_command"


async def test_subscribe_snapshots_und_ende(hass, api, integration):
    await api.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["boxen", "konfig", "eingang"]})
    antwort = await api.receive_json()
    assert antwort["success"] is True and antwort["result"] is None
    abo_id = antwort["id"]
    events = [await api.receive_json() for _ in range(3)]
    assert all(e["type"] == "event" and e["id"] == abo_id for e in events)
    huellen = {e["event"]["thema"]: e["event"] for e in events}
    assert set(huellen) == {"boxen", "konfig", "eingang"}
    for h in huellen.values():
        assert h["v"] == 1 and h["art"] == "snapshot"
    assert {b["box"] for b in huellen["boxen"]["daten"]["boxen"]} == {"box1", "box2"}
    assert huellen["boxen"]["daten"]["boxen"][0].keys() == {"box", "online", "konfig_stand"}
    assert huellen["konfig"]["daten"]["konfig"]["zustand"] == "ok"
    assert huellen["eingang"]["daten"].keys() == {"offen", "blockiert", "sortierung_laeuft", "geprueft_am"}
    # ein Ereignis aus einem abonnierten Thema kommt an, eines aus einem nicht abonnierten nicht
    integration.emit("neue_tobies", "neu", {"eintrag": {}})
    integration.emit("eingang", "geaendert", {})
    e = await api.receive_json()
    assert e["event"]["thema"] == "eingang" and e["event"]["art"] == "geaendert"
    await api.send_json_auto_id({"type": "unsubscribe_events", "subscription": abo_id})
    assert (await api.receive_json())["success"] is True
    assert integration.abos == []


async def test_subscribe_alle_themen_und_ungueltiges_thema(hass, api):
    await api.send_json_auto_id({"type": "tobibox/subscribe"})
    assert (await api.receive_json())["success"] is True
    themen = [(await api.receive_json())["event"]["thema"] for _ in range(7)]
    assert themen == ["boxen", "neue_tobies", "lernmodus", "medien", "eingang", "konfig", "upload"]
    assert await fehler(api, "subscribe", themen=["quatsch"]) == "invalid_format"


# --------------------------------------------------------------------------
# Rechte (Abschnitt 2.1)
# --------------------------------------------------------------------------

ADMIN_BEFEHLE = [
    ("serie/create", {"name": "X"}),
    ("folgen/order", {"serie_id": "rabe", "folgen": ["a.mp3", "b.mp3"]}),
    ("papierkorb/restore", {"eintrag_id": "0123456789ab"}),
    ("papierkorb/empty", {"bestaetigt": True}),
    ("box/sync", {"box": "box1"}),
    ("liste/neu_ausrollen", {"bestaetigt": True}),
    ("serien/zusammenfuehren", {"quelle_id": "rabe", "ziel_id": "z"}),
    ("konfig/export_lesen", {}),  # seit 12.11. nur Administratoren (vorher lesen)
    ("konfig/aus_export", {"bestaetigt": True}),
]
#: seit 12.11. (Paket A1) „alltag“: für jeden angemeldeten Nutzer erlaubt (bisher Administratoren); Schutzregeln: test_rechte_schutz.py
ALLTAG_BEFEHLE = [
    ("serie/rename", {"serie_id": "rabe", "name": "X"}),
    ("folge/delete", {"serie_id": "rabe", "folge": "a.mp3"}),
    ("medien/pruefen", {}),
    ("neue_tobies/verwerfen", {"uid": UID}),
    ("zuordnung/set", {"uid": UID, "ziel": SERIE}),
    ("zuordnung/remove", {"uid": UID, "erwartet_ziel": None}),
    ("lernmodus/start", {"box": "box1", "ziel": SERIE}),
    ("lernmodus/antwort", {"befehl_id": "x", "ueberschreiben": True}),
    ("lernmodus/abbrechen", {"box": "box1"}),
    ("serie/delete", {"serie_id": "rabe"}),
    ("folge/rename", {"serie_id": "rabe", "folge": "a.mp3", "name": "X"}),
    ("folge/verschieben", {"serie_id": "rabe", "folge": "a.mp3", "ziel_serie_id": "z"}),
    ("einsortierung/bestaetigen", {"serie_id": "rabe"}),
    ("eingang/sortieren", {}),
]
LESE_BEFEHLE = [
    ("hello", {"v": 1}),
    ("serien/list", {}),
    ("serie/get", {"serie_id": "rabe"}),
    ("papierkorb/list", {}),
    ("neue_tobies/list", {}),
    ("zuordnung/list", {}),
    ("boxen/list", {}),
    ("eingang/list", {}),
]


@pytest.mark.parametrize(("typ", "felder"), ADMIN_BEFEHLE, ids=[b[0] for b in ADMIN_BEFEHLE])
async def test_schreibende_befehle_nur_fuer_administratoren(api_lesend, typ, felder):
    antwort = await senden(api_lesend, typ, **felder)
    assert antwort["success"] is False
    assert antwort["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(("typ", "felder"), ALLTAG_BEFEHLE, ids=[b[0] for b in ALLTAG_BEFEHLE])
async def test_alltagsbefehle_sind_nicht_mehr_nur_fuer_administratoren(api_lesend, typ, felder):
    """Ob der Befehl gelingt, hängt von den Schutzregeln und vom Bestand ab; ``unauthorized`` wegen der Rolle gibt es nicht mehr."""
    antwort = await senden(api_lesend, typ, **felder)
    assert antwort["success"] is True or antwort["error"]["code"] != "unauthorized", antwort


@pytest.mark.parametrize(("typ", "felder"), LESE_BEFEHLE, ids=[b[0] for b in LESE_BEFEHLE])
async def test_lesende_befehle_fuer_jeden_angemeldeten_nutzer(api_lesend, nas, typ, felder):
    antwort = await senden(api_lesend, typ, **felder)
    assert antwort["success"] is True, antwort


async def test_admin_befehle_sind_vollstaendig_aufgelistet():
    """Jeder Befehl der Übersicht (Nr. 1 bis 32 ohne ``subscribe``) ist in einer der beiden Listen."""
    erwartet = {
        "hello", "serien/list", "serie/get", "serie/create", "serie/rename", "folgen/order", "folge/delete", "medien/pruefen",
        "papierkorb/list", "papierkorb/restore", "papierkorb/empty", "neue_tobies/list", "neue_tobies/verwerfen", "zuordnung/list",
        "zuordnung/set", "zuordnung/remove", "lernmodus/start", "lernmodus/antwort", "lernmodus/abbrechen", "boxen/list", "box/sync",
        "liste/neu_ausrollen", "serie/delete", "folge/rename", "folge/verschieben", "serien/zusammenfuehren", "einsortierung/bestaetigen",
        "eingang/list", "eingang/sortieren", "konfig/export_lesen", "konfig/aus_export",
    }
    assert {b[0] for b in ADMIN_BEFEHLE} | {b[0] for b in ALLTAG_BEFEHLE} | {b[0] for b in LESE_BEFEHLE} == erwartet


# --------------------------------------------------------------------------
# 3 bis 9: Serien und Folgen
# --------------------------------------------------------------------------


async def test_serien_list_und_serie_get(hass, api, nas, integration):
    nas.serie("anfang", "anfang", "Anfang")
    nas.serie("ue", "ue", "Überraschung", typ="ueberraschung")
    await ok(api, "medien/pruefen")
    await integration.medien._pruefung_task  # die Prüfung läuft im Hintergrund
    r = await ok(api, "serien/list")
    assert [s["name"] for s in r["serien"]] == ["Anfang", "Der kleine Rabe", "Überraschung"]
    assert r["ueberraschung"] == "leer"
    assert r["pruefung_laeuft"] is False and r["geprueft_am"]
    rabe = next(s for s in r["serien"] if s["id"] == "rabe")
    assert rabe.keys() == {"id", "name", "typ", "ordner", "anzahl_folgen", "anzahl_tobies", "angelegt_am", "stand", "pruefen", "anzahl_pruefen", "hinweise",
                           "art", "art_quelle", "einzeln", "cover_stand", "cover_quelle"}  # seit 12.11. (Pakete A3, A4)
    assert (rabe["anzahl_folgen"], rabe["typ"], rabe["ordner"], rabe["pruefen"], rabe["anzahl_pruefen"]) == (2, "normal", "rabe", False, 0)
    assert (rabe["art"], rabe["art_quelle"], rabe["einzeln"]) == ("hoerspiel", "geraten", False)  # alte serie.json ohne art
    assert (r["gesamt"], r["weitere"]) == (3, False)
    s = await ok(api, "serie/get", serie_id="rabe")
    assert s["stand"] == rabe["stand"] and s["zuordnungen"] == []
    a, b = s["folgen"]
    assert a.keys() == {"name", "anzeige", "nummer", "datum", "art", "tracks", "groesse_bytes", "pruefung", "hinweis", "pruefen", "pruefen_gruende", "tobies"}
    assert (a["name"], a["anzeige"], a["nummer"], a["art"], a["tracks"]) == ("a.mp3", "Eins", 1, "datei", 1)
    assert (b["anzeige"], b["nummer"], b["datum"]) == ("b", None, None)  # Dateiname ohne Endung
    assert await fehler(api, "serie/get", serie_id="gibtsnicht") == "serie_nicht_gefunden"
    assert await fehler(api, "serie/get") == "invalid_format"


async def test_serie_create_mit_anfrage_id(api, nas):
    r = await ok(api, "serie/create", name="Neue Serie", anfrage_id="anfrage-0001")
    assert r["serie"]["name"] == "Neue Serie" and r["serie"]["ordner"] == "Neue Serie"
    r2 = await ok(api, "serie/create", name="Neue Serie", anfrage_id="anfrage-0001")
    assert r2 == r  # dieselbe Antwort, die Wirkung nicht wiederholt
    assert not (nas.medien / "Neue Serie (2)").exists()
    assert await fehler(api, "serie/create", name="Andere Serie", anfrage_id="anfrage-0001") == "anfrage_id_konflikt"
    r3 = await ok(api, "serie/create", name="Neue Serie")  # ohne anfrage_id: nicht idempotent, eine zweite Serie
    assert r3["serie"]["ordner"] == "Neue Serie (2)"


async def test_anfrage_id_nur_erfolge_werden_gemerkt(api, box_fabrik):
    with patch.object(ha_mqtt, "is_connected", return_value=False):
        assert await fehler(api, "box/sync", box="box1", anfrage_id="sync-00001") == "mqtt_nicht_verbunden"
    r = await ok(api, "box/sync", box="box1", anfrage_id="sync-00001")  # derselbe Versuch gelingt jetzt und wird neu ausgeführt
    assert r["ttl_s"] == 300
    assert len(box_fabrik("box1").befehle("sync")) == 1
    assert await ok(api, "box/sync", box="box1", anfrage_id="sync-00001") == r
    assert len(box_fabrik("box1").befehle("sync")) == 1


@pytest.mark.parametrize("anfrage_id", ["kurz", "x" * 65, "mit leerzeichen", "ümlaut-0001", 12345678])
async def test_anfrage_id_format(api, anfrage_id):
    assert await fehler(api, "serie/create", name="X", anfrage_id=anfrage_id) == "invalid_format"


async def test_serie_create_fehler(api):
    assert await fehler(api, "serie/create", name="") == "name_ungueltig"
    assert await fehler(api, "serie/create", name="x" * 101) == "name_ungueltig"
    assert await fehler(api, "serie/create") == "invalid_format"
    assert await fehler(api, "serie/create", name="X", typ="quatsch") == "invalid_format"
    await ok(api, "serie/create", name="U", typ="ueberraschung")
    assert await fehler(api, "serie/create", name="U2", typ="ueberraschung") == "ueberraschung_existiert"


async def test_serie_rename(api, nas):
    r = await ok(api, "serie/rename", serie_id="rabe", name="Der große Rabe")
    assert r["serie"]["name"] == "Der große Rabe" and r["serie"]["ordner"] == "rabe"
    assert nas.serie_json("rabe")["id"] == "rabe"
    assert await ok(api, "serie/rename", serie_id="rabe", name="Der große Rabe")  # gleicher Name: nichts geschrieben
    assert await fehler(api, "serie/rename", serie_id="gibtsnicht", name="X") == "serie_nicht_gefunden"
    assert await fehler(api, "serie/rename", serie_id="rabe", name="  ") == "name_ungueltig"


async def test_folgen_order(api, nas):
    s = await ok(api, "serie/get", serie_id="rabe")
    r = await ok(api, "folgen/order", serie_id="rabe", folgen=["b.mp3", "a.mp3"], stand=s["stand"])
    assert nas.serie_json("rabe")["folgen"] == ["b.mp3", "a.mp3"]
    assert r["serie"]["stand"] != s["stand"]
    assert await fehler(api, "folgen/order", serie_id="rabe", folgen=["b.mp3", "a.mp3"], stand=s["stand"]) == "stand_veraltet"
    assert await fehler(api, "folgen/order", serie_id="rabe", folgen=["b.mp3"]) == "reihenfolge_ungueltig"
    assert await fehler(api, "folgen/order", serie_id="gibtsnicht", folgen=[]) == "serie_nicht_gefunden"
    assert await fehler(api, "folgen/order", serie_id="rabe", folgen="a.mp3") == "invalid_format"
    assert await ok(api, "folgen/order", serie_id="rabe", folgen=["a.mp3", "b.mp3"])  # ohne stand: letzter Schreiber gewinnt


async def test_folge_delete_mit_und_ohne_tobies(api, nas):
    await ok(api, "zuordnung/set", uid=UID, ziel=FOLGE, name="Rabe aus Holz", erwartet_ziel=None)
    s = await ok(api, "serie/get", serie_id="rabe")
    assert await fehler(api, "folge/delete", serie_id="rabe", folge="a.mp3", stand=s["stand"]) == "tobies_betroffen"
    r = await ok(api, "folge/delete", serie_id="rabe", folge="a.mp3", tobies_bestaetigt=True, stand=s["stand"])
    assert r["eintrag"]["typ"] == "folge" and r["eintrag"]["grund"] == "manuell" and r["eintrag"]["folge"] == "a.mp3"
    assert r["betroffene_tobies"] == [{"uid": UID, "name": "Rabe aus Holz"}]
    assert await fehler(api, "folge/delete", serie_id="rabe", folge="a.mp3") == "folge_nicht_gefunden"  # zweiter Aufruf
    assert await fehler(api, "folge/delete", serie_id="gibtsnicht", folge="a.mp3") == "serie_nicht_gefunden"
    assert await fehler(api, "folge/delete", serie_id="rabe", folge="b.mp3", stand="0" * 16) == "stand_veraltet"
    assert await fehler(api, "folge/delete", serie_id="rabe", folge="b.mp3", tobies_bestaetigt="ja") == "invalid_format"
    assert (await ok(api, "zuordnung/list"))["zuordnungen"][0]["folge_vorhanden"] is False  # die Zuordnung bleibt


async def test_medien_pruefen_im_hintergrund(hass, api, nas, lege_mp3):
    await api.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["medien"]})
    assert (await api.receive_json())["success"] is True
    assert (await api.receive_json())["event"]["art"] == "snapshot"
    lege_mp3(nas.medien / "rabe" / "c.mp3")
    r = await ok(api, "medien/pruefen")
    assert r == {"gestartet": True, "laeuft_bereits": False}
    arten = []
    for _ in range(5):
        e = (await api.receive_json())["event"]
        arten.append(e["art"])
        if e["art"] == "pruefung_fertig":
            assert e["daten"]["neue_folgen"] == 1 and e["daten"]["neue_serien"] == 0
            break
    assert "pruefung_fertig" in arten
    assert nas.serie_json("rabe")["folgen"][-1] == "c.mp3"


async def test_medien_pruefen_laeuft_bereits(hass, api, integration):
    integration.medien.pruefung_laeuft = True
    assert await ok(api, "medien/pruefen") == {"gestartet": False, "laeuft_bereits": True}
    integration.medien.pruefung_laeuft = False


async def test_medien_nicht_erreichbar(hass, api, nas):
    import shutil

    shutil.rmtree(nas.medien)
    assert await fehler(api, "medien/pruefen") == "medien_nicht_erreichbar"
    assert await fehler(api, "papierkorb/list") == "medien_nicht_erreichbar"
    assert await fehler(api, "serie/create", name="X") == "medien_nicht_erreichbar"


# --------------------------------------------------------------------------
# 10 bis 12: Papierkorb
# --------------------------------------------------------------------------


async def test_papierkorb_list_restore_empty(api, nas):
    e1 = (await ok(api, "folge/delete", serie_id="rabe", folge="a.mp3"))["eintrag"]
    e2 = (await ok(api, "folge/delete", serie_id="rabe", folge="b.mp3"))["eintrag"]
    liste = await ok(api, "papierkorb/list")
    assert [e["id"] for e in liste["eintraege"]] == [e2["id"], e1["id"]]  # neueste zuerst
    assert liste["gesamt"] == 2 and liste["gesamt_bytes"] > 0
    assert liste["eintraege"][0].keys() == {"id", "typ", "serie_id", "serie_name", "folge", "anzeige", "art", "tracks", "groesse_bytes", "grund", "geloescht_am", "geloescht_von"}
    assert (await ok(api, "papierkorb/list", limit=1, offset=1))["eintraege"][0]["id"] == e1["id"]
    assert await fehler(api, "papierkorb/list", limit=201) == "invalid_format"
    assert await fehler(api, "papierkorb/list", offset=-1) == "invalid_format"
    r = await ok(api, "papierkorb/restore", eintrag_id=e1["id"])
    assert r["folge"] == "a.mp3" and r["serie"]["id"] == "rabe"
    assert await fehler(api, "papierkorb/restore", eintrag_id=e1["id"]) == "eintrag_nicht_gefunden"
    assert await fehler(api, "papierkorb/empty") == "invalid_format"
    assert await fehler(api, "papierkorb/empty", bestaetigt=False) == "invalid_format"
    assert await fehler(api, "papierkorb/empty", bestaetigt="ja") == "invalid_format"
    r = await ok(api, "papierkorb/empty", bestaetigt=True)
    assert r["geloescht"] == 1 and r["freigegeben_bytes"] > 0
    assert (await ok(api, "papierkorb/empty", bestaetigt=True))["geloescht"] == 0


# --------------------------------------------------------------------------
# 13 und 14: Neue Tobies
# --------------------------------------------------------------------------


async def test_neue_tobies_list_und_verwerfen(hass, api, box_fabrik):
    b1, b2 = box_fabrik("box1"), box_fabrik("box2")
    await b1.unbekannt(UID, anzahl=2, zuletzt="2026-11-09T10:00:01.000Z", zuerst="2026-11-09T09:00:00Z")
    await b2.unbekannt(UID, anzahl=1, zuletzt="2026-11-09T10:05:00.000Z", zuerst="2026-11-09T09:30:00Z")
    await b1.unbekannt(UID2, anzahl=1, zuletzt="2026-11-09T11:00:00.000Z")
    r = await ok(api, "neue_tobies/list")
    assert r["gesamt"] == 2
    assert [e["uid"] for e in r["eintraege"]] == [UID2, UID]  # nach zuletzt absteigend
    e = r["eintraege"][1]
    assert e.keys() == {"uid", "zuerst", "zuletzt", "anzahl", "boxen"}
    assert e["anzahl"] == 3 and e["zuerst"] == "2026-11-09T09:00:00Z" and e["zuletzt"] == "2026-11-09T10:05:00.000Z"
    assert e["boxen"]["box2"] == {"zuerst": "2026-11-09T09:30:00Z", "zuletzt": "2026-11-09T10:05:00.000Z", "anzahl": 1, "zeit_ok": True}
    assert (await ok(api, "neue_tobies/list", limit=1, offset=1))["eintraege"][0]["uid"] == UID
    assert await ok(api, "neue_tobies/verwerfen", uid=UID) == {"entfernt": True}
    assert await ok(api, "neue_tobies/verwerfen", uid=UID) == {"entfernt": False}
    assert await fehler(api, "neue_tobies/verwerfen", uid="ABC") == "kennung_ungueltig"
    assert await fehler(api, "neue_tobies/list", limit=0) == "invalid_format"


# --------------------------------------------------------------------------
# 15 bis 17: Zuordnungen
# --------------------------------------------------------------------------


async def test_zuordnung_set_list_remove(api, box_fabrik, nas):
    r = await ok(api, "zuordnung/set", uid=UID, ziel=SERIE, name="Rabe aus Holz", erwartet_ziel=None)
    assert r["geaendert"] is True and r["veroeffentlicht"] is True
    assert r["konfig"].keys() == {"revision", "liste_id", "zustand", "export_ok", "export_geschrieben_am"}
    assert r["konfig"]["revision"] == 2 and r["konfig"]["zustand"] == "ok"
    r = await ok(api, "zuordnung/set", uid=UID, ziel=SERIE, erwartet_ziel=SERIE)  # gleiches Ziel, Name bleibt
    assert r["geaendert"] is False and r["veroeffentlicht"] is None
    await ok(api, "zuordnung/set", uid=UID2, ziel=AKTION, erwartet_ziel=None)
    await ok(api, "zuordnung/set", uid="0123456789abcdef", ziel=FOLGE, erwartet_ziel=None)
    liste = await ok(api, "zuordnung/list")
    assert liste["gesamt"] == 3
    assert [z["uid"] for z in liste["zuordnungen"]] == ["0123456789abcdef", UID2, UID]  # sortiert nach uid (Text)
    z = {x["uid"]: x for x in liste["zuordnungen"]}
    # Vertrag W 12.11., angelegt_am: Anlegen setzt den Zeitstempel
    assert z[UID] == {"uid": UID, "name": "Rabe aus Holz", "ziel": SERIE, "serie_name": "Der kleine Rabe", "folge_anzeige": None, "folge_vorhanden": None, "angelegt_am": ANY}
    assert z["0123456789abcdef"]["folge_anzeige"] == "Eins" and z["0123456789abcdef"]["folge_vorhanden"] is True
    assert z[UID2]["serie_name"] is None
    assert (await ok(api, "zuordnung/list", serie_id="rabe"))["gesamt"] == 2
    assert len((await ok(api, "zuordnung/list", limit=1, offset=2))["zuordnungen"]) == 1
    assert await fehler(api, "zuordnung/list", limit=101) == "invalid_format"
    # name null löscht den Namen, ein neuer Name ändert nur den Namen (und erhöht die Revision)
    r = await ok(api, "zuordnung/set", uid=UID, ziel=SERIE, name=None)
    assert r["geaendert"] is True
    assert "name" not in box_fabrik("box1").konfigs()[-1]["zuordnungen"][UID]
    r = await ok(api, "zuordnung/remove", uid=UID, erwartet_ziel=SERIE)
    assert r["geaendert"] is True
    assert UID not in box_fabrik("box1").konfigs()[-1]["zuordnungen"]
    r = await ok(api, "zuordnung/remove", uid=UID)
    assert r["geaendert"] is False and r["veroeffentlicht"] is None


async def test_zuordnung_set_fehler(api, nas):
    ue = (await ok(api, "serie/create", name="Überraschung", typ="ueberraschung"))["serie"]["id"]
    assert await fehler(api, "zuordnung/set", uid="ZZ", ziel=SERIE) == "kennung_ungueltig"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel={"typ": "serie", "serie": "gibtsnicht"}) == "serie_nicht_gefunden"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel={"typ": "folge", "serie": "rabe", "folge": "x.mp3"}) == "folge_nicht_gefunden"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel={"typ": "serie", "serie": ue}) == "ziel_ungueltig"  # Überraschung verboten
    assert await fehler(api, "zuordnung/set", uid=UID, ziel={"typ": "folge", "folge": "a.mp3"}) == "ziel_ungueltig"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel={"typ": "aktion", "aktion": "update"}) == "ziel_ungueltig"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel={"typ": "quatsch"}) == "ziel_ungueltig"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel=SERIE, name="") == "name_ungueltig"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel=SERIE, name="x" * 61) == "name_ungueltig"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel=SERIE, unbekannt=1) == "invalid_format"
    assert await fehler(api, "zuordnung/set", uid=UID) == "invalid_format"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel="serie") == "invalid_format"
    # Überschreiben
    await ok(api, "zuordnung/set", uid=UID, ziel=SERIE)
    assert await fehler(api, "zuordnung/set", uid=UID, ziel=AKTION) == "zuordnung_existiert"
    assert (await ok(api, "zuordnung/set", uid=UID, ziel=AKTION, ueberschreiben=True))["geaendert"] is True
    # erwartet_ziel (W-12): eine Abweichung lehnt ab, ``ueberschreiben`` entfällt dann
    assert await fehler(api, "zuordnung/set", uid=UID, ziel=SERIE, erwartet_ziel=SERIE) == "zuordnung_geaendert"
    assert await fehler(api, "zuordnung/set", uid=UID, ziel=SERIE, erwartet_ziel=None) == "zuordnung_geaendert"
    assert (await ok(api, "zuordnung/set", uid=UID, ziel=SERIE, erwartet_ziel=AKTION))["geaendert"] is True
    assert await fehler(api, "zuordnung/remove", uid=UID, erwartet_ziel=AKTION) == "zuordnung_geaendert"
    assert await fehler(api, "zuordnung/remove", uid="ZZ") == "kennung_ungueltig"


async def test_zuordnung_entfernt_eintrag_aus_neue_tobies(hass, api, box_fabrik):
    await box_fabrik("box1").unbekannt(UID)
    await api.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["neue_tobies"]})
    await api.receive_json()
    await api.receive_json()
    await ok(api, "zuordnung/set", uid=UID, ziel=SERIE, erwartet_ziel=None)
    e = await naechstes_ereignis(api)
    assert (e["thema"], e["art"], e["daten"]) == ("neue_tobies", "entfernt", {"uid": UID, "grund": "zugeordnet"})
    assert (await ok(api, "neue_tobies/list"))["gesamt"] == 0


async def test_konfig_nicht_bereit_sperrt_aenderungen(hass, api, integration):
    integration.store.zustand = "leer_neu"
    for typ, felder in (
        ("zuordnung/set", {"uid": UID, "ziel": SERIE}),
        ("zuordnung/remove", {"uid": UID}),
        ("lernmodus/start", {"box": "box1", "ziel": SERIE}),
    ):
        assert await fehler(api, typ, **felder) == "konfig_nicht_bereit"
    assert (await ok(api, "zuordnung/list"))["konfig"]["zustand"] == "leer_neu"  # Lesen geht weiter
    assert (await ok(api, "serien/list"))["serien"]


# --------------------------------------------------------------------------
# 18 bis 20: Lernmodus
# --------------------------------------------------------------------------


async def test_lernmodus_start_antwort_abbrechen(hass, api, box_fabrik):
    box = box_fabrik("box1")
    r = await ok(api, "lernmodus/start", box="box1", ziel=SERIE, name="Rabe", anfrage_id="lernen-0001")
    assert r.keys() == {"befehl_id", "box", "ziel", "beginn", "frist_bis"}
    assert await ok(api, "lernmodus/start", box="box1", ziel=SERIE, name="Rabe", anfrage_id="lernen-0001") == r
    assert len(box.befehle("lernen")) == 1
    assert await fehler(api, "lernmodus/start", box="box1", ziel=FOLGE) == "lernmodus_laeuft"
    assert await fehler(api, "lernmodus/antwort", befehl_id=r["befehl_id"], ueberschreiben=True) == "kein_lernmodus"  # keine Rückfrage offen
    assert await fehler(api, "lernmodus/antwort", befehl_id=r["befehl_id"]) == "invalid_format"
    await box.unbekannt(UID, art="gelernt", befehl_id=r["befehl_id"])
    assert box.acks(UID)[-1]["grund"] == "zugeordnet"
    assert (await ok(api, "zuordnung/list"))["zuordnungen"][0]["name"] == "Rabe"
    assert await ok(api, "lernmodus/abbrechen", box="box1") == {"abgebrochen": False}
    assert [c["befehl"] for c in box.befehle()] == ["lernen", "lernen_abbrechen"]


async def test_lernmodus_rueckfrage_ueber_den_websocket(hass, api, box_fabrik):
    box = box_fabrik("box1")
    await ok(api, "zuordnung/set", uid=UID, ziel=AKTION, erwartet_ziel=None)
    await api.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["lernmodus"]})
    await api.receive_json()
    await api.receive_json()
    r = await ok(api, "lernmodus/start", box="box1", ziel=SERIE)
    assert (await naechstes_ereignis(api))["daten"]["zustand"] == "wartet"
    await box.unbekannt(UID, art="gelernt", befehl_id=r["befehl_id"])
    frage = (await naechstes_ereignis(api))["daten"]
    assert frage["zustand"] == "rueckfrage" and frage["bisher"] == AKTION and frage["uid"] == UID
    a = await ok(api, "lernmodus/antwort", befehl_id=r["befehl_id"], ueberschreiben=True)
    assert a["zustand"] == "zugeordnet" and a["konfig"]["revision"] == 3
    assert (await naechstes_ereignis(api))["daten"]["zustand"] == "zugeordnet"


async def test_lernmodus_start_fehler(api, box_fabrik):
    assert await fehler(api, "lernmodus/start", box="box9", ziel=SERIE) == "box_unbekannt"
    assert await fehler(api, "lernmodus/start", box="box2", ziel=SERIE) == "box_offline"
    assert await fehler(api, "lernmodus/start", box="box1", ziel=AKTION) == "ziel_ungueltig"
    assert await fehler(api, "lernmodus/start", box="box1", ziel={"typ": "serie", "serie": "x"}) == "serie_nicht_gefunden"
    assert await fehler(api, "lernmodus/start", box="box1", ziel={"typ": "folge", "serie": "rabe", "folge": "x"}) == "folge_nicht_gefunden"
    assert await fehler(api, "lernmodus/start", box="box1", ziel=SERIE, name="") == "name_ungueltig"
    with patch.object(ha_mqtt, "is_connected", return_value=False):
        assert await fehler(api, "lernmodus/start", box="box1", ziel=SERIE) == "mqtt_nicht_verbunden"
        assert await fehler(api, "lernmodus/abbrechen", box="box1") == "mqtt_nicht_verbunden"
    assert await fehler(api, "lernmodus/abbrechen", box="box9") == "box_unbekannt"


# --------------------------------------------------------------------------
# 21 bis 23: Boxen, Liste neu ausrollen
# --------------------------------------------------------------------------


async def test_boxen_list(hass, api, box_fabrik, integration):
    b = box_fabrik("box1")
    await b.discovery("Kinderzimmer")
    await b.status()
    await b.ereignis("fehler", {"baustein": "sync", "code": "x", "text": "kaputt"}, eid="aaaaaaaa-0000-4000-8000-000000000001")
    r = await ok(api, "boxen/list")
    assert [x["box"] for x in r["boxen"]] == ["box1", "box2"]  # Reihenfolge der Einrichtung
    x = r["boxen"][0]
    assert x.keys() == {"box", "anzeigename", "anzeige", "online", "status", "status_empfangen_am", "konfig_stand", "lernmodus", "ereignisse"}
    assert x["anzeigename"] == "Kinderzimmer" and x["anzeige"] == "Kinderzimmer" and x["online"] is True and x["status"]["version"] == "1.0.0"
    assert x["ereignisse"][0].keys() == {"id", "ts", "art", "daten", "text"}
    assert r["boxen"][1]["online"] is None and r["boxen"][1]["status"] is None and r["boxen"][1]["konfig_stand"] == "unbekannt"
    assert r["boxen"][1]["anzeige"] == "box2"  # weder Option noch Discovery: der Box-Name
    assert json.dumps(r)  # serialisierbar


async def test_anzeige_reihenfolge_der_rueckfaelle(hass, api, box_fabrik, integration):
    """Vertrag W, 14.9: Name aus den Optionen, sonst ``anzeigename`` der Discovery, sonst der Box-Name; nie ``null``."""
    box = box_fabrik("box1")
    anzeigen = lambda r: {b["box"]: b["anzeige"] for b in r["boxen"]}  # noqa: E731
    assert anzeigen(await ok(api, "boxen/list")) == {"box1": "box1", "box2": "box2"}  # 3. Rückfall: der Box-Name
    await box.discovery("Kinderzimmer")
    assert anzeigen(await ok(api, "boxen/list")) == {"box1": "Kinderzimmer", "box2": "box2"}  # 2. Rückfall: Discovery
    integration.box_anzeigen_optionen = {"box1": "Box 1", "box2": "Box 2"}
    assert anzeigen(await ok(api, "boxen/list")) == {"box1": "Box 1", "box2": "Box 2"}  # 1. die Optionen gewinnen
    hello = await ok(api, "hello", v=1)
    assert hello["box_anzeigen"] == {"box1": "Box 1", "box2": "Box 2"}
    integration.box_anzeigen_optionen = {"box2": "Box 2"}
    assert (await ok(api, "hello", v=1))["box_anzeigen"] == {"box1": "Kinderzimmer", "box2": "Box 2"}  # je Box einzeln
    assert all(a for a in anzeigen(await ok(api, "boxen/list")).values())  # nie leer


async def test_box_sync(api, box_fabrik):
    r = await ok(api, "box/sync", box="box1")
    assert r["ttl_s"] == 300 and box_fabrik("box1").befehle("sync")[0]["id"] == r["befehl_id"]
    assert await fehler(api, "box/sync", box="box9") == "box_unbekannt"
    assert await fehler(api, "box/sync", box="box2") == "box_offline"
    assert await fehler(api, "box/sync") == "invalid_format"


async def test_liste_neu_ausrollen(api, box_fabrik, integration):
    assert await fehler(api, "liste/neu_ausrollen") == "invalid_format"
    assert await fehler(api, "liste/neu_ausrollen", bestaetigt=False) == "invalid_format"
    alt = integration.store.konfig["liste_id"]
    r = await ok(api, "liste/neu_ausrollen", bestaetigt=True, anfrage_id="ausrollen-01")
    assert r["konfig"]["revision"] == 1 and r["konfig"]["liste_id"] != alt and r["veroeffentlicht"] is True
    assert await ok(api, "liste/neu_ausrollen", bestaetigt=True, anfrage_id="ausrollen-01") == r  # nur einmal ausgeführt
    assert len([k for k in box_fabrik("box1").konfigs() if k["revision"] == 1]) == 2  # Erststart und genau ein Ausrollen


# --------------------------------------------------------------------------
# 24 bis 28: Korrekturen
# --------------------------------------------------------------------------


async def test_serie_delete_mit_tobies(api, nas):
    await ok(api, "zuordnung/set", uid=UID, ziel=SERIE, name="Rabe", erwartet_ziel=None)
    s = await ok(api, "serie/get", serie_id="rabe")
    assert s["zuordnungen"] == [{"uid": UID, "name": "Rabe"}]
    assert await fehler(api, "serie/delete", serie_id="rabe", stand=s["stand"]) == "tobies_betroffen"
    assert await fehler(api, "serie/delete", serie_id="rabe", tobies_bestaetigt=True, stand="0" * 16) == "stand_veraltet"
    r = await ok(api, "serie/delete", serie_id="rabe", tobies_bestaetigt=True, stand=s["stand"])
    assert r["eintrag"]["typ"] == "serie" and r["betroffene_tobies"] == [{"uid": UID, "name": "Rabe"}]
    assert r["ueberraschung"] == "fehlt"
    assert not (nas.medien / "rabe").exists()
    assert await fehler(api, "serie/delete", serie_id="rabe") == "serie_nicht_gefunden"


async def test_folge_rename(api, nas):
    r = await ok(api, "folge/rename", serie_id="rabe", folge="b.mp3", name="Zwei: Der Wald")
    assert r["folge"]["anzeige"] == "Zwei: Der Wald" and r["folge"]["name"] == "b.mp3"
    assert r["serie"]["id"] == "rabe"
    assert nas.serie_json("rabe")["folgen_info"]["b.mp3"]["anzeige"] == "Zwei: Der Wald"
    assert await fehler(api, "folge/rename", serie_id="rabe", folge="x.mp3", name="X") == "folge_nicht_gefunden"
    assert await fehler(api, "folge/rename", serie_id="rabe", folge="a.mp3", name="x" * 201) == "name_ungueltig"
    assert await fehler(api, "folge/rename", serie_id="rabe", folge="a.mp3", name="X", stand="0" * 16) == "stand_veraltet"


async def test_folge_verschieben_und_zusammenfuehren(api, nas, lege_mp3, integration):
    z = nas.serie("ziel", "ziel", "Ziel-Serie")
    await ok(api, "medien/pruefen")
    await integration.medien._pruefung_task
    await ok(api, "zuordnung/set", uid=UID, ziel=FOLGE, erwartet_ziel=None)
    assert await fehler(api, "folge/verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id="ziel") == "tobies_betroffen"
    assert await fehler(api, "folge/verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id="rabe") == "ziel_ungueltig"
    assert await fehler(api, "folge/verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id="gibtsnicht") == "serie_nicht_gefunden"
    assert await fehler(api, "folge/verschieben", serie_id="rabe", folge="x.mp3", ziel_serie_id="ziel") == "folge_nicht_gefunden"
    r = await ok(api, "folge/verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id="ziel", tobies_bestaetigt=True)
    assert r.keys() == {"quelle", "ziel", "folge", "betroffene_tobies", "konfig", "veroeffentlicht"}
    assert r["folge"] == "a.mp3" and r["quelle"]["anzahl_folgen"] == 1 and r["ziel"]["anzahl_folgen"] == 1
    assert r["konfig"]["revision"] == 3 and r["veroeffentlicht"] is True
    assert (z / "a.mp3").exists()
    assert (await ok(api, "zuordnung/list"))["zuordnungen"][0]["ziel"] == {"typ": "folge", "serie": "ziel", "folge": "a.mp3"}
    assert await fehler(api, "folge/verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id="ziel") == "folge_nicht_gefunden"
    # zusammenführen
    m = await ok(api, "serien/zusammenfuehren", quelle_id="rabe", ziel_id="ziel")
    assert m.keys() == {"ziel", "verschoben", "umbenannt", "betroffene_tobies", "eintrag", "konfig", "veroeffentlicht"}
    assert m["verschoben"] == 1 and m["konfig"] is None and m["ziel"]["anzahl_folgen"] == 2
    assert await fehler(api, "serien/zusammenfuehren", quelle_id="rabe", ziel_id="ziel") == "serie_nicht_gefunden"
    assert await fehler(api, "serien/zusammenfuehren", quelle_id="ziel", ziel_id="ziel") == "ziel_ungueltig"


async def test_einsortierung_bestaetigen(api, nas, integration):
    nas.serie("p", "p", "P", ["a.mp3"], pruefen=True, pruefen_gruende=["tags_fehlen"], folgen_info={"a.mp3": {"pruefen": True, "pruefen_gruende": ["tags_fehlen"]}})
    (nas.medien / "p" / "a.mp3").write_bytes((nas.medien / "rabe" / "a.mp3").read_bytes())
    await ok(api, "medien/pruefen")
    await integration.medien._pruefung_task
    assert (await ok(api, "serie/get", serie_id="p"))["folgen"][0]["pruefen"] is True
    r = await ok(api, "einsortierung/bestaetigen", serie_id="p")
    assert r["serie"]["pruefen"] is False and r["serie"]["anzahl_pruefen"] == 0
    assert await fehler(api, "einsortierung/bestaetigen", serie_id="p", folgen=["x.mp3"]) == "folge_nicht_gefunden"
    assert await fehler(api, "einsortierung/bestaetigen", serie_id="gibtsnicht") == "serie_nicht_gefunden"


# --------------------------------------------------------------------------
# 29 und 30: Eingang
# --------------------------------------------------------------------------


@braucht_ffmpeg
async def test_eingang_list_und_sortieren(hass, api, nas, ereignisse, integration):
    erzeuge_audio(nas.eingang / "a.mp3", album="Folge 1", album_artist="Neue Serie")
    erzeuge_audio(nas.eingang / "Ordner" / "x.mp3", frequenz=500, album="Anderes", album_artist="Neue Serie")
    assert await fehler(api, "eingang/sortieren", eintrag_ids=["0123456789ab"]) == "eintrag_nicht_gefunden"
    r = await ok(api, "eingang/sortieren")
    assert r["gestartet"] is True and r["laeuft_bereits"] is False and r["eintraege"] == 0  # noch in der Ruhezeit
    await hass.async_block_till_done()
    liste = await ok(api, "eingang/list")
    assert liste["gesamt"] == 2 and {e["status"] for e in liste["eintraege"]} == {"wartet"}
    assert liste.keys() == {"eintraege", "gesamt", "sortierung_laeuft", "geprueft_am"}
    eintrag = next(e for e in liste["eintraege"] if e["name"] == "a.mp3")
    assert eintrag.keys() == {"id", "name", "art", "dateien", "ignoriert", "groesse_bytes", "zuerst_gesehen", "geaendert_am", "status", "hinweise", "ergebnis", "fertig_am", "wunsch", "quelle", "pruefen"}  # "wunsch": Vertrag W 12.11. (A3d), "quelle"/"pruefen": Nacharbeit A3d
    assert eintrag["wunsch"] is None  # ohne Wunsch
    r = await ok(api, "eingang/sortieren", eintrag_ids=[eintrag["id"]], sofort=True)
    assert r["eintraege"] == 1
    await hass.async_block_till_done()
    await warte_auf(hass, lambda: not integration.eingang.laeuft)
    erledigt = await ok(api, "eingang/list", filter="erledigt")
    assert [e["name"] for e in erledigt["eintraege"]] == ["a.mp3"]
    assert erledigt["eintraege"][0]["ergebnis"][0]["serie_name"] == "Neue Serie"
    assert (await ok(api, "eingang/list", filter="alle"))["gesamt"] == 2
    assert await fehler(api, "eingang/list", filter="quatsch") == "invalid_format"
    assert await fehler(api, "eingang/list", limit=101) == "invalid_format"
    assert await fehler(api, "eingang/sortieren", sofort="ja") == "invalid_format"
    assert any(e["thema"] == "eingang" and e["art"] == "neu_einsortiert" for e in ereignisse)
    assert (await ok(api, "serien/list"))["serien"]


async def test_eingang_nicht_erreichbar(api, nas):
    import os

    os.rmdir(nas.eingang)
    assert await fehler(api, "eingang/sortieren") == "medien_nicht_erreichbar"


# --------------------------------------------------------------------------
# 31 und 32: Export
# --------------------------------------------------------------------------


async def test_export_lesen_und_aus_export(hass, api, nas, integration, box_fabrik):
    await warte_auf(hass, lambda: integration.export_ok)
    await ok(api, "zuordnung/set", uid=UID, ziel=SERIE, name="Rabe aus Holz", erwartet_ziel=None)
    await warte_auf(hass, lambda: integration.export_ok)
    r = await ok(api, "konfig/export_lesen")
    assert r.keys() == {"vorhanden", "liste_id", "revision", "exportiert_am", "anzahl_zuordnungen", "anzahl_fenster", "neuer_als_ha", "konfig", "staende"}
    assert r["vorhanden"] is True and r["revision"] == 2 and r["anzahl_zuordnungen"] == 1 and r["anzahl_fenster"] == 0
    assert r["neuer_als_ha"] is False and r["konfig"]["zustand"] == "ok"
    assert await fehler(api, "konfig/aus_export") == "invalid_format"
    assert await fehler(api, "konfig/aus_export", bestaetigt=False) == "invalid_format"
    alt = integration.store.konfig["liste_id"]
    a = await ok(api, "konfig/aus_export", bestaetigt=True, anfrage_id="export-0001")
    assert a["uebernommen"] == {"zuordnungen": 1, "fenster": 0}
    assert a["konfig"]["revision"] == 1 and a["konfig"]["liste_id"] != alt and a["konfig"]["zustand"] == "ok"
    assert a["veroeffentlicht"] is True
    assert box_fabrik("box1").konfigs()[-1]["zuordnungen"][UID]["name"] == "Rabe aus Holz"  # Namen kommen mit
    assert await ok(api, "konfig/aus_export", bestaetigt=True, anfrage_id="export-0001") == a
    await warte_auf(hass, lambda: integration.export_ok)  # der Export nach aus_export läuft im Hintergrund; sonst schreibt er config.json nach dem Löschen neu
    (nas.export / "config.json").unlink()
    assert (await ok(api, "konfig/export_lesen"))["vorhanden"] is False
    assert await fehler(api, "konfig/aus_export", bestaetigt=True) == "export_nicht_gefunden"
    (nas.export / "config.json").write_text('{"schema_version": 2, "revision": 1}')
    assert (await ok(api, "konfig/export_lesen"))["vorhanden"] is False
    assert await fehler(api, "konfig/aus_export", bestaetigt=True) == "export_ungueltig"
    assert integration.store.konfig["liste_id"] == a["konfig"]["liste_id"]  # nichts übernommen
