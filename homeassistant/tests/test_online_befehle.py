"""Online-Suche, Paket OS3: die Befehle 57 bis 64, die Vorschau (HTTP), ``subscribe``, die Ausgabefelder und der Filter (Vertrag W, 3.15, 4.11, 14.2).

Ohne echtes Netz: Die Quellen sind die Attrappen aus ``test_online_dienst.py`` (Fixtures aus ``fixtures/online/``). Der Dienst selbst ist dort geprüft;
hier geht es um die Verdrahtung: Schemata, Rechte, Fehlercodes, Ausgabe.
"""

from __future__ import annotations

import asyncio
import io
from typing import Any
from unittest.mock import patch

import pytest
from PIL import Image

from custom_components.tobibox import online as online_modul
from custom_components.tobibox.const import (
    ART_QUELLEN,
    COVER_KLEIN_PX,
    EREIGNIS_THEMEN,
    FAEHIGKEITEN,
    NUR_ADMIN_THEMEN,
    ONLINE_VORSCHAU_PX,
)
from custom_components.tobibox.fehler import HTTP_STATUS, TobiboxFehler
from custom_components.tobibox.gehoert import Zeile

from .conftest import braucht_ffmpeg
from .test_online_dienst import FOLGE, SID, FakeListe, FakeQuellen, arbeite, lege_bibi, schnapp_wie_einsortiert
from .test_online_dienst import _vorschlag_erzeugen  # noqa: PLC2701
from .test_rechte_schutz import _client
from .test_websocket_api import fehler, ok

pytestmark = braucht_ffmpeg

SID2 = "zwei"
NEUE_CODES = ("treffer_abgelaufen", "vorschlag_nicht_gefunden", "aenderung_nicht_gefunden", "lauf_nicht_gefunden", "lauf_laeuft_schon", "online_nicht_erreichbar")


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
async def hub(starte_integration: Any, nas: Any, lege_mp3: Any) -> Any:
    """Zwei Einträge: „Bibi Blocksberg“ (mit Prüfgründen, Ziel der Suche) und ein zweiter ohne alles (für den Filter)."""
    lege_bibi(nas, lege_mp3, gruende=["tags_fehlen"], serie_gruende=["art_geraten"])
    lege_bibi(nas, lege_mp3, name="Ganz Anderes", ordner="anderes", serie_id=SID2)
    h = await starte_integration()
    h.online.quellen = FakeQuellen()
    h.online.tonie_liste = FakeListe()
    return h


@pytest.fixture
async def admin(hass: Any, hub: Any, hass_ws_client: Any) -> Any:
    return await hass_ws_client(hass)


@pytest.fixture
async def normal(hass: Any, hub: Any, hass_ws_client: Any) -> Any:
    return await _client(hass, hass_ws_client, "Normal")


async def suche(admin: Any, **felder: Any) -> dict[str, Any]:
    return await ok(admin, "online/suchen", serie_id=SID, folge=FOLGE, **felder)


def apple_mit_cover(r: dict[str, Any]) -> dict[str, Any]:
    return next(t for t in r["treffer"] if t["quelle"] == "itunes" and t["hat_cover"])


# --------------------------------------------------------------------------
# Konstanten, Fehlercodes, Fähigkeit
# --------------------------------------------------------------------------


def test_konstanten_stehen_in_const() -> None:
    assert "online" in ART_QUELLEN and "online_suche" in FAEHIGKEITEN and "online" in EREIGNIS_THEMEN
    assert NUR_ADMIN_THEMEN == {"online"} and ONLINE_VORSCHAU_PX == COVER_KLEIN_PX == 192
    assert online_modul.ONLINE_TREFFER_MAX == 10 and online_modul.COVER_ONLINE == "cover-online.jpg"


def test_die_sechs_fehlercodes_und_ihr_http_status() -> None:
    erwartet = {"treffer_abgelaufen": 410, "vorschlag_nicht_gefunden": 404, "aenderung_nicht_gefunden": 404, "lauf_nicht_gefunden": 404, "lauf_laeuft_schon": 409,
                "online_nicht_erreichbar": 503}
    assert {c: HTTP_STATUS[c] for c in NEUE_CODES} == erwartet


async def test_hello_sagt_online_suche_zu(admin: Any, normal: Any) -> None:
    for client in (admin, normal):
        assert "online_suche" in (await ok(client, "hello", v=1))["faehigkeiten"]


# --------------------------------------------------------------------------
# Nr. 57 online/suchen
# --------------------------------------------------------------------------


async def test_57_suchen_erfolg(admin: Any) -> None:
    r = await suche(admin)
    assert r.keys() == {"treffer", "quellen"} and r["quellen"] == {"itunes": "ok", "tonies": "ok"}
    assert 0 < len(r["treffer"]) <= 10
    t = r["treffer"][0]
    assert {"treffer_id", "quelle", "titel", "reihe", "hat_cover", "frueher_abgelehnt", "felder"} <= t.keys() and len(t["treffer_id"]) == 16
    r2 = await ok(admin, "online/suchen", serie_id=SID, text="Bibi")  # ohne ``folge``: Suche für den Eintrag
    assert r2["treffer"]


async def test_57_fehler(admin: Any, normal: Any, hub: Any) -> None:
    assert await fehler(admin, "online/suchen", serie_id="gibtsnicht") == "serie_nicht_gefunden"
    assert await fehler(admin, "online/suchen", serie_id=SID, folge="gibtsnicht") == "folge_nicht_gefunden"
    assert await fehler(admin, "online/suchen", serie_id=SID, text="x") == "invalid_format"  # 2 bis 100 Zeichen
    assert await fehler(admin, "online/suchen", serie_id=SID, text="x" * 101) == "invalid_format"
    assert await fehler(admin, "online/suchen", serie_id=SID, unbekannt=1) == "invalid_format"
    assert await fehler(admin, "online/suchen") == "invalid_format"
    ueberraschung = (await ok(admin, "serie/create", name="Überraschung", typ="ueberraschung"))["serie"]["id"]
    assert await fehler(admin, "online/suchen", serie_id=ueberraschung) == "invalid_format"  # nur bei ``typ = normal``
    assert await fehler(normal, "online/suchen", serie_id=SID) == "unauthorized"
    # nur wenn **keine** Quelle antwortet; eine Quelle liefert ein Teilergebnis
    hub.online.quellen.itunes_ausfall = True
    teil = await ok(admin, "online/suchen", serie_id=SID, folge=FOLGE)
    assert teil["quellen"] == {"itunes": "fehler", "tonies": "ok"}
    hub.online.tonie_liste.ok = False
    assert await fehler(admin, "online/suchen", serie_id=SID, folge=FOLGE) == "online_nicht_erreichbar"


# --------------------------------------------------------------------------
# Nr. 58 online/treffer
# --------------------------------------------------------------------------


async def test_58_treffer_und_vorschlag(admin: Any, hub: Any) -> None:
    t = apple_mit_cover(await suche(admin))
    r = await ok(admin, "online/treffer", treffer_id=t["treffer_id"])
    assert r["felder"]["cover"]["neu"] is True and r["felder"]["art"] == {"heute": "musik", "neu": "hoerspiel", "sicher": True, "hand": False}
    # die Übersicht eines Vorschlags (Karte „bitte ansehen“)
    await _vorschlag_erzeugen(hub)
    liste = (await ok(admin, "serie/get", serie_id=SID))["online_vorschlaege_liste"]
    v = next(x for x in liste if x["art"] == "felder" and "cover" in x["felder"])
    r2 = await ok(admin, "online/treffer", serie_id=SID, vorschlag_id=v["id"])
    assert "cover" in r2["felder"] and "grund" not in r2  # ``grund`` nur bei Quelle ``claude``


async def test_58_fehler(admin: Any, normal: Any) -> None:
    assert await fehler(admin, "online/treffer", treffer_id="0" * 16) == "treffer_abgelaufen"
    assert await fehler(admin, "online/treffer", serie_id=SID, vorschlag_id="gibtsnicht") == "vorschlag_nicht_gefunden"
    assert await fehler(admin, "online/treffer", serie_id="gibtsnicht", vorschlag_id="x") == "serie_nicht_gefunden"
    # genau eine Quelle: sonst ``invalid_format``
    assert await fehler(admin, "online/treffer") == "invalid_format"
    assert await fehler(admin, "online/treffer", serie_id=SID) == "invalid_format"
    assert await fehler(admin, "online/treffer", treffer_id="0" * 16, serie_id=SID) == "invalid_format"
    assert await fehler(admin, "online/treffer", treffer_id="0" * 16, vorschlag_id="x") == "invalid_format"
    assert await fehler(normal, "online/treffer", treffer_id="0" * 16) == "unauthorized"


# --------------------------------------------------------------------------
# Nr. 59 online/uebernehmen
# --------------------------------------------------------------------------


async def test_59_uebernehmen_erfolg_und_felder_der_ausgabe(admin: Any, normal: Any, hub: Any, nas: Any) -> None:
    t = apple_mit_cover(await suche(admin))
    stand = (await ok(admin, "serie/get", serie_id=SID))["stand"]
    r = await ok(admin, "online/uebernehmen", serie_id=SID, treffer_id=t["treffer_id"], felder=["cover", "art"], stand=stand)
    assert r.keys() == {"aenderung_id", "serie_id", "stand"} and r["aenderung_id"] and r["serie_id"] == SID and r["stand"] == stand  # Art und Cover gehören nicht zum ``stand`` (14.2)
    assert (nas.medien / "bibi" / "cover-online.jpg").is_file()
    # alle sehen den Hinweis „aus der Online-Suche übernommen“ (nur Zeit und Feldnamen), die Art kommt von ``online``
    for client in (admin, normal):
        kurz = (await ok(client, "serien/list"))["serien"]
        bibi = next(s for s in kurz if s["id"] == SID)
        assert bibi["online"].keys() == {"zeit", "felder"} and sorted(bibi["online"]["felder"]) == ["art", "cover"]
        assert bibi["cover_quelle"] == "online" and bibi["art_quelle"] == "online"
        assert next(s for s in kurz if s["id"] == SID2)["online"] is None


async def test_59_anfrage_id_ist_idempotent(admin: Any, hub: Any) -> None:
    t = apple_mit_cover(await suche(admin))
    felder = {"serie_id": SID, "treffer_id": t["treffer_id"], "felder": ["art"], "anfrage_id": "anfrage-0001"}
    r1 = await ok(admin, "online/uebernehmen", **felder)
    r2 = await ok(admin, "online/uebernehmen", **felder)
    assert r1 == r2 and len(hub.online.store.aenderungen(SID)) == 1
    assert await fehler(admin, "online/uebernehmen", **{**felder, "felder": ["cover"]}) == "anfrage_id_konflikt"


async def test_59_fehler(admin: Any, normal: Any, hub: Any) -> None:
    t = apple_mit_cover(await suche(admin))
    tid = t["treffer_id"]
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id="0" * 16, felder=["art"]) == "treffer_abgelaufen"
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, vorschlag_id="gibtsnicht", felder=["art"]) == "vorschlag_nicht_gefunden"
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=["serie_name"], stand="veraltet") == "stand_veraltet"
    assert await fehler(admin, "online/uebernehmen", serie_id="gibtsnicht", treffer_id=tid, felder=["art"]) == "serie_nicht_gefunden"
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=["nummer@gibtsnicht"]) == "folge_nicht_gefunden"
    # ``invalid_format``: Schema und Regeln des Befehls
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, felder=["art"]) == "invalid_format"  # weder Treffer noch Vorschlag
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, vorschlag_id="x", felder=["art"]) == "invalid_format"
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=[]) == "invalid_format"
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=["gibt_es_nicht"]) == "invalid_format"
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=["serie_name"]) == "invalid_format"  # ``stand`` ist Pflicht
    zu_viele = [f"nummer@f{i}" for i in range(8)]  # Zahl der Folgen (1) × 4 + 3 = 7
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=zu_viele) == "invalid_format"
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=["art"], anfrage_id="kurz") == "invalid_format"
    assert await fehler(normal, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=["art"]) == "unauthorized"
    # Freigabe weg und Schreiben schlägt fehl
    with patch.object(type(hub.medien), "_medien_erreichbar", side_effect=TobiboxFehler("medien_nicht_erreichbar")):
        assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=["art"]) == "medien_nicht_erreichbar"
    with patch.object(online_modul, "schreibe_serie", side_effect=OSError("Platte weg")):
        assert await fehler(admin, "online/uebernehmen", serie_id=SID, treffer_id=tid, felder=["art"]) == "medien_schreibfehler"


async def test_59_name_ungueltig_beim_namensvorschlag_von_claude(admin: Any, hub: Any) -> None:
    serie = hub.medien.serien[SID].serie
    hub.online.store.serie(SID)["vorschlaege"] = [
        {"id": "v123", "art": "felder", "quelle": "claude", "felder": ["serie_name"], "werte": {"serie_name": "   "}, "grund": "g", "name_vorher": serie.name,
         "zeit": "2026-11-19T10:00:00Z"}
    ]
    assert await fehler(admin, "online/uebernehmen", serie_id=SID, vorschlag_id="v123", felder=["serie_name"], stand=serie.stand) == "name_ungueltig"


# --------------------------------------------------------------------------
# Nr. 60 online/zuruecknehmen
# --------------------------------------------------------------------------


async def _uebernommen(admin: Any) -> str:
    t = apple_mit_cover(await suche(admin))
    return (await ok(admin, "online/uebernehmen", serie_id=SID, treffer_id=t["treffer_id"], felder=["art"]))["aenderung_id"]


async def test_60_zuruecknehmen_formen(admin: Any, hub: Any, nas: Any) -> None:
    aid = await _uebernommen(admin)
    r = await ok(admin, "online/zuruecknehmen", serie_id=SID, aenderung_id=aid)
    assert r == {"zurueckgenommen": 1, "uebersprungen": [], "uebersprungen_anzahl": 0}
    assert (await ok(admin, "online/zuruecknehmen", serie_id=SID))["zurueckgenommen"] == 0  # Endzustand gleich
    # Form Lauf: im Hintergrund, Ergebnis über das Ereignis ``online``
    await _uebernommen(admin)
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    lauf_id = hub.online.status()["letzte_laeufe"][0]["lauf_id"]
    assert await ok(admin, "online/zuruecknehmen", lauf_id=lauf_id) == {"gestartet": True}
    await hub.online.warte_auf_rueck()


async def test_60_fehler(admin: Any, normal: Any, hub: Any) -> None:
    aid = await _uebernommen(admin)
    assert await fehler(admin, "online/zuruecknehmen", serie_id=SID, aenderung_id="gibtsnicht") == "aenderung_nicht_gefunden"
    assert await fehler(admin, "online/zuruecknehmen", lauf_id="gibtsnicht") == "lauf_nicht_gefunden"
    assert await fehler(admin, "online/zuruecknehmen", serie_id="gibtsnicht") == "serie_nicht_gefunden"
    assert await fehler(admin, "online/zuruecknehmen") == "invalid_format"
    assert await fehler(admin, "online/zuruecknehmen", aenderung_id=aid) == "invalid_format"
    assert await fehler(admin, "online/zuruecknehmen", serie_id=SID, lauf_id="x") == "invalid_format"
    assert await fehler(normal, "online/zuruecknehmen", serie_id=SID) == "unauthorized"
    with patch.object(type(hub.medien), "_medien_erreichbar", side_effect=TobiboxFehler("medien_nicht_erreichbar")):
        assert await fehler(admin, "online/zuruecknehmen", serie_id=SID, aenderung_id=aid) == "medien_nicht_erreichbar"
    with patch.object(online_modul, "schreibe_serie", side_effect=OSError("Platte weg")):
        assert await fehler(admin, "online/zuruecknehmen", serie_id=SID, aenderung_id=aid) == "medien_schreibfehler"


# --------------------------------------------------------------------------
# Nr. 61 online/vorschlag_verwerfen
# --------------------------------------------------------------------------


async def test_61_vorschlag_verwerfen(admin: Any, normal: Any, hub: Any) -> None:
    vorschlaege = await _vorschlag_erzeugen(hub)
    zahl = len(vorschlaege)
    assert (await ok(admin, "serie/get", serie_id=SID))["online_vorschlaege"] == zahl
    erste = vorschlaege[0]["id"]
    assert await fehler(normal, "online/vorschlag_verwerfen", serie_id=SID, vorschlag_id=erste) == "unauthorized"
    assert await ok(admin, "online/vorschlag_verwerfen", serie_id=SID, vorschlag_id=erste) == {}
    assert (await ok(admin, "serie/get", serie_id=SID))["online_vorschlaege"] == zahl - 1
    assert await fehler(admin, "online/vorschlag_verwerfen", serie_id=SID, vorschlag_id=erste) == "vorschlag_nicht_gefunden"  # auch beim zweiten Mal
    assert await fehler(admin, "online/vorschlag_verwerfen", serie_id="gibtsnicht", vorschlag_id=erste) == "serie_nicht_gefunden"
    assert await fehler(admin, "online/vorschlag_verwerfen", serie_id=SID) == "invalid_format"
    assert await fehler(admin, "online/vorschlag_verwerfen", vorschlag_id=erste) == "invalid_format"


async def test_61_loest_serien_geaendert_aus(admin: Any, hub: Any) -> None:
    from custom_components.tobibox.hub import Abo

    vorschlaege = await _vorschlag_erzeugen(hub)
    ereignisse: list[dict[str, Any]] = []
    hub.abo_hinzu(Abo(type("V", (), {"user": None, "send_message": lambda _s, n: ereignisse.append(n["event"])})(), 1, {"medien"}, "a", ist_admin=True))
    await ok(admin, "online/vorschlag_verwerfen", serie_id=SID, vorschlag_id=vorschlaege[0]["id"])
    assert any(e["thema"] == "medien" and e["art"] == "serien_geaendert" for e in ereignisse)


# --------------------------------------------------------------------------
# Nr. 62 online/lauf, Nr. 63 online/status
# --------------------------------------------------------------------------


async def test_62_lauf_start_stop_und_fehler(admin: Any, normal: Any, hub: Any) -> None:
    gate = asyncio.Event()

    async def langsam(*_a: Any, **_k: Any) -> dict[str, Any]:
        await gate.wait()
        return {"geaendert": 0, "vorschlaege": 0, "fehler": False, "pause": None}

    assert await ok(admin, "online/lauf", aktion="stop") == {"lauf": None}  # ohne Lauf kein Fehler
    with patch.object(hub.online, "_arbeite_serie", langsam):
        r = await ok(admin, "online/lauf", aktion="start")
        assert r["lauf"]["zustand"] == "laeuft" and r["lauf"]["gesamt"] >= 1
        assert await fehler(admin, "online/lauf", aktion="start") == "lauf_laeuft_schon"
        assert (await ok(admin, "online/status"))["lauf"]["lauf_id"] == r["lauf"]["lauf_id"]
        assert (await ok(admin, "online/lauf", aktion="stop"))["lauf"]["zustand"] == "wird_angehalten"
        gate.set()
        await hub.online.warte_auf_lauf()
    s = await ok(admin, "online/status")
    assert s["lauf"] is None and s["letzte_laeufe"][0]["zustand"] == "angehalten" and s["letzte_laeufe"][0]["grund"] == "angehalten"
    assert await fehler(admin, "online/lauf", aktion="los") == "invalid_format"
    assert await fehler(admin, "online/lauf") == "invalid_format"
    assert await fehler(normal, "online/lauf", aktion="start") == "unauthorized"
    assert await fehler(normal, "online/lauf", aktion="stop") == "unauthorized"


async def test_63_status(admin: Any, normal: Any, hub: Any) -> None:
    s = await ok(admin, "online/status")
    assert s.keys() == {"lauf", "quellen", "tonie_liste", "letzte_laeufe"} and s["lauf"] is None
    assert set(s["quellen"]) == {"itunes", "tonies", "tonies_shop", "claude"} and s["quellen"]["claude"]["eingerichtet"] is False
    assert s == hub.online.status()
    assert await fehler(normal, "online/status") == "unauthorized"
    assert await fehler(admin, "online/status", x=1) == "invalid_format"


# --------------------------------------------------------------------------
# Nr. 64 online/beschreibung (Recht lesen)
# --------------------------------------------------------------------------


async def test_64_beschreibung_fuer_jeden_angemeldeten_benutzer(admin: Any, normal: Any, hub: Any) -> None:
    for client in (admin, normal):
        assert await ok(client, "online/beschreibung", serie_id=SID, folge=FOLGE) == {"beschreibung": None, "quelle": None}
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    for client in (admin, normal):
        r = await ok(client, "online/beschreibung", serie_id=SID, folge=FOLGE)
        assert r["quelle"] == "tonies_shop" and r["alter_ab"] == 4 and r["beschreibung"].startswith("Ein neues hexisches")
        assert await fehler(client, "online/beschreibung", serie_id=SID, folge="gibtsnicht") == "folge_nicht_gefunden"
        assert await fehler(client, "online/beschreibung", serie_id="gibtsnicht", folge=FOLGE) == "serie_nicht_gefunden"
        assert await fehler(client, "online/beschreibung", serie_id=SID) == "invalid_format"


# --------------------------------------------------------------------------
# Ausgabefelder: Folge, Kurzform, Liste der Vorschläge (14.2, 3.2)
# --------------------------------------------------------------------------


async def test_serie_get_folgenfelder_fuer_alle_und_vorschlagsliste_nur_fuer_admins(admin: Any, normal: Any, hub: Any) -> None:
    await _vorschlag_erzeugen(hub)  # schnapp + Lauf: Beschreibung und Alter kommen, Cover und Art nur als Vorschlag
    a = await ok(admin, "serie/get", serie_id=SID)
    n = await ok(normal, "serie/get", serie_id=SID)
    for r in (a, n):
        f = next(x for x in r["folgen"] if x["name"] == FOLGE)
        assert f["alter_ab"] == 4 and f["beschreibung_quelle"] == "tonies_shop" and isinstance(f["beschreibung_gekuerzt"], bool)
        assert 0 < len(f["beschreibung"]) <= 301
    assert a["online_vorschlaege"] >= 1 and a["online_vorschlaege_liste"]
    e = a["online_vorschlaege_liste"][0]
    assert {"id", "art", "quelle", "zeit"} <= e.keys() and e["art"] == "felder" and e["quelle"] in ("itunes", "tonies") and e["felder"]
    assert "werte" not in e  # Werte holt die Seite mit Nr. 58
    assert "online_vorschlaege" not in n and "online_vorschlaege_liste" not in n and "online" in n
    # eine Folge ohne Beschreibung hat die Felder nicht
    z = await ok(admin, "serie/get", serie_id=SID2)
    f2 = z["folgen"][0]
    assert not {"beschreibung", "beschreibung_gekuerzt", "alter_ab", "beschreibung_quelle"} & f2.keys()
    assert z["online_vorschlaege_liste"] == [] and z["online_vorschlaege"] == 0


async def test_serien_list_online_vorschlaege_nur_fuer_admins(admin: Any, normal: Any, hub: Any) -> None:
    await _vorschlag_erzeugen(hub)
    a = {s["id"]: s for s in (await ok(admin, "serien/list"))["serien"]}
    n = {s["id"]: s for s in (await ok(normal, "serien/list"))["serien"]}
    assert a[SID]["online_vorschlaege"] >= 1 and a[SID2]["online_vorschlaege"] == 0
    assert all("online_vorschlaege" not in s and "online" in s for s in n.values())
    assert "online_vorschlaege_liste" not in a[SID]  # nur in ``serie/get``


async def test_antworten_ohne_vorschlagszahl_haben_nur_online(admin: Any, hub: Any) -> None:
    r = await ok(admin, "serie/rename", serie_id=SID2, name="Noch Anderes")
    assert "online_vorschlaege" not in r["serie"] and r["serie"]["online"] is None


async def test_51_zuletzt_hat_online_vorschlaege_nur_fuer_admins(admin: Any, normal: Any, hub: Any) -> None:
    await _vorschlag_erzeugen(hub)
    await hub.gehoert.nimm_zeilen_auf("box:box1", [Zeile("00000000-0000-4000-8000-000000000001", SID, FOLGE, 100, 1_790_000_000, 1_790_000_100, "sicher", 100, "pause")])
    a = (await ok(admin, "gehoert/zuletzt"))["eintraege"]
    n = (await ok(normal, "gehoert/zuletzt"))["eintraege"]
    assert a and n and a[0]["id"] == SID and a[0]["online_vorschlaege"] >= 1 and "online" in a[0]
    assert "online_vorschlaege" not in n[0] and "online" in n[0]


# --------------------------------------------------------------------------
# Filter ``online_vorschlag``
# --------------------------------------------------------------------------


async def test_filter_online_vorschlag(admin: Any, normal: Any, hub: Any) -> None:
    assert (await ok(admin, "serien/list", filter=["online_vorschlag"]))["serien"] == []
    await _vorschlag_erzeugen(hub)
    r = await ok(admin, "serien/list", filter=["online_vorschlag"])
    assert [s["id"] for s in r["serien"]] == [SID] and r["gesamt"] == 1
    r2 = await ok(admin, "serien/list", filter=["online_vorschlag", "neu"])  # mehrere Werte: „und“
    assert r2["gesamt"] <= 1
    assert await fehler(normal, "serien/list", filter=["online_vorschlag"]) == "unauthorized"
    assert await fehler(admin, "folgen/list", filter=["online_vorschlag"]) == "invalid_format"  # ``folgen/list`` kennt den Wert nicht


# --------------------------------------------------------------------------
# subscribe: das Thema ``online`` nur für Administratoren
# --------------------------------------------------------------------------


async def abonniere(client: Any, **felder: Any) -> list[dict[str, Any]]:
    client.gesammelt = []
    await ok(client, "subscribe", **felder)
    await ok(client, "hello", v=1)  # eine Antwort danach: die Schnappschüsse davor sind angekommen
    return list(client.gesammelt)


def themen(ereignisse: list[dict[str, Any]]) -> set[str]:
    return {e["thema"] for e in ereignisse}


async def test_subscribe_online_fuer_nicht_admin_still_gestrichen(normal: Any, hub: Any) -> None:
    assert themen(await abonniere(normal, themen=["online"])) == set()  # leer, **nicht** „alle“
    assert hub.abos[-1].themen == set() and hub.abos[-1].ist_admin is False
    e = await abonniere(normal, themen=["online", "medien"])
    assert themen(e) == {"medien"}
    alle = await abonniere(normal)
    assert "online" not in themen(alle) and {"boxen", "medien", "konfig"} <= themen(alle) and hub.abos[-1].themen == {t for t in EREIGNIS_THEMEN if t != "online"}


async def test_subscribe_online_fuer_admin(admin: Any, hub: Any) -> None:
    e = await abonniere(admin, themen=["online"])
    assert [x["art"] for x in e] == ["snapshot"] and e[0]["thema"] == "online" and e[0]["daten"] == hub.online.status()
    assert hub.abos[-1].ist_admin is True
    assert "online" in themen(await abonniere(admin))


async def test_online_ereignisse_nur_an_admins(admin: Any, normal: Any, hub: Any) -> None:
    await abonniere(admin)
    await abonniere(normal)
    admin.gesammelt.clear()
    normal.gesammelt.clear()
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    await ok(admin, "hello", v=1)
    await ok(normal, "hello", v=1)
    assert {"stand", "fertig"} <= {e["art"] for e in admin.gesammelt if e["thema"] == "online"}
    assert not [e for e in normal.gesammelt if e["thema"] == "online"]


# --------------------------------------------------------------------------
# HTTP: Vorschau
# --------------------------------------------------------------------------


@pytest.fixture
async def client(hass: Any, hub: Any, hass_client: Any) -> Any:
    return await hass_client()


@pytest.fixture
async def client_normal(hass: Any, hub: Any, hass_client: Any, hass_read_only_access_token: Any) -> Any:
    return await hass_client(hass_read_only_access_token)


async def test_vorschau_liefert_192_px_jpeg(admin: Any, client: Any) -> None:
    t = apple_mit_cover(await suche(admin))
    antwort = await client.get(f"/api/tobibox/online/vorschau/{t['treffer_id']}")
    assert antwort.status == 200 and antwort.headers["Content-Type"] == "image/jpeg" and antwort.headers["Cache-Control"] == "no-store"
    bild = Image.open(io.BytesIO(await antwort.read()))
    assert bild.format == "JPEG" and bild.size == (192, 192)  # das gehaltene Bild ist 600 px groß


async def test_vorschau_fehler(admin: Any, hub: Any, client: Any, client_normal: Any, hass_client_no_auth: Any) -> None:
    r = await suche(admin)
    tid = apple_mit_cover(r)["treffer_id"]
    ohne_bild = next(t for t in r["treffer"] if not t["hat_cover"])
    a = await client.get(f"/api/tobibox/online/vorschau/{ohne_bild['treffer_id']}")
    assert a.status == 404 and (await a.json())["fehler"]["code"] == "cover_nicht_gefunden"
    a = await client.get("/api/tobibox/online/vorschau/" + "0" * 16)
    assert a.status == 410 and (await a.json())["fehler"]["code"] == "treffer_abgelaufen" and (await a.json())["fehler"]["text"]
    for falsch in ("xyz", "0" * 15, "0" * 17, "A" * 16, "g" * 16):
        a = await client.get(f"/api/tobibox/online/vorschau/{falsch}")
        assert a.status == 404, falsch
    a = await client_normal.get(f"/api/tobibox/online/vorschau/{tid}")
    assert a.status == 403 and (await a.json())["fehler"]["code"] == "unauthorized"
    a = await (await hass_client_no_auth()).get(f"/api/tobibox/online/vorschau/{tid}")
    assert a.status == 401
    # ein Treffer, der nach 15 Minuten verfallen ist
    hub.online.quellen.treffer_speicher._ttl = -1  # noqa: SLF001
    a = await client.get(f"/api/tobibox/online/vorschau/{tid}")
    assert a.status == 410 and (await a.json())["fehler"]["code"] == "treffer_abgelaufen"


async def test_delete_cover_online_fuer_nicht_admin_403(client: Any, client_normal: Any, nas: Any) -> None:
    (nas.medien / "bibi" / "cover-online.jpg").write_bytes(b"x")
    a = await client_normal.delete(f"/api/tobibox/cover/{SID}?quelle=online")
    assert a.status == 403 and (await a.json())["fehler"]["code"] == "unauthorized"
    assert (nas.medien / "bibi" / "cover-online.jpg").is_file()
    assert (await client.delete(f"/api/tobibox/cover/{SID}?quelle=online")).status == 200


async def test_60_lauf_ruecknahme_laeuft_schon_ist_idempotent(admin: Any, hub: Any) -> None:
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    lauf_id = hub.online.status()["letzte_laeufe"][0]["lauf_id"]
    gate = asyncio.Event()
    aufrufe: list[str] = []

    async def langsam(lid: str) -> None:
        aufrufe.append(lid)
        await gate.wait()

    with patch.object(hub.online, "_lauf_zuruecknehmen", langsam):
        assert await ok(admin, "online/zuruecknehmen", lauf_id=lauf_id) == {"gestartet": True}
        assert await ok(admin, "online/zuruecknehmen", lauf_id=lauf_id) == {"gestartet": True}  # kein Fehler, keine zweite Rücknahme
        gate.set()
        await hub.online.warte_auf_rueck()
    assert aufrufe == [lauf_id]


async def test_60_ruecknahme_eines_anderen_laufs_wird_hinten_angestellt(admin: Any, hub: Any) -> None:
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    erster = hub.online.status()["letzte_laeufe"][0]["lauf_id"]
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    zweiter = hub.online.status()["letzte_laeufe"][0]["lauf_id"]
    assert erster != zweiter
    gate = asyncio.Event()
    aufrufe: list[str] = []

    async def langsam(lid: str) -> None:
        aufrufe.append(lid)
        await gate.wait()

    with patch.object(hub.online, "_lauf_zuruecknehmen", langsam):
        assert await ok(admin, "online/zuruecknehmen", lauf_id=erster) == {"gestartet": True}
        assert await ok(admin, "online/zuruecknehmen", lauf_id=zweiter) == {"gestartet": True}  # kein Fehler: hinten angestellt
        assert await ok(admin, "online/zuruecknehmen", lauf_id=zweiter) == {"gestartet": True}  # doppelt angestellt zählt einmal
        gate.set()
        await hub.online.warte_auf_rueck()
    assert aufrufe == [erster, zweiter]
