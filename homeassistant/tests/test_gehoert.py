"""Paket B2 „Gehört“ (HA-Speicher) mit Home Assistant: Aufnahme von ``gespielt`` mit Quittung und Handshake, Technik-Zeilen,
Reinhören als Sitzungen (Befehl 41 ``spieler``, ``spielt``), Favoriten und das Mitschreiben beim Verschieben und Zusammenführen.

Die Zählregel selbst (Mal, fertig, Pausen, Zeitzonen, Ersetzen) steht in ``test_gehoert_regeln.py``.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import CLIENT_ID, async_fire_time_changed

from custom_components.tobibox import favoriten as favoriten_modul
from custom_components.tobibox import gehoert as gehoert_modul
from custom_components.tobibox.const import (
    GEHOERT_QUITTUNG_VERZOEGERUNG_S,
    HOERSTELLE_SCHREIBEN_JE_MINUTE,
    REINHOEREN_SCHREIBEN_S,
    REINHOEREN_SPIELER_MAX,
)
from custom_components.tobibox.fehler import TobiboxFehler
from custom_components.tobibox.favoriten import Favoriten

from .test_websocket_api import fehler, ok, senden

U1 = "e3a8b1c4-52d7-4f09-b6a1-{:012d}"


def utc(j: int, m: int, t: int, h: int = 0, mi: int = 0, s: int = 0) -> int:
    return int(datetime(j, m, t, h, mi, s, tzinfo=UTC).timestamp())


def sitz(n: int = 1, **ueber: Any) -> dict[str, Any]:
    s = {
        "sitzung": U1.format(n), "serie": "rabe", "folge": "a.mp3", "folge_dauer_s": 100, "beginn": "2026-11-16T18:10:57Z", "zeit_ok": True,
        "boot_id": "boot-a", "beginn_boot_s": 50400, "ende_boot_s": 50500, "gehoert_s": 100, "ende": "pause",
    }
    s.update(ueber)
    return s


def nachricht(*sitzungen: dict[str, Any], boot: str = "boot-a", gesendet: int = 51915) -> dict[str, Any]:
    return {"boot_id": boot, "gesendet_boot_s": gesendet, "sitzungen": list(sitzungen)}


async def zeit_vergeht(hass, sekunden: float) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=sekunden))
    await hass.async_block_till_done()


def quittungen(box) -> list[list[str]]:
    return [b["daten"]["sitzungen"] for b in box.befehle("gehoert_quittung")]


async def zeilen(hub, quelle: str | None = None) -> list[dict[str, Any]]:
    return await hub.hass.async_add_executor_job(hub.gehoert.db.alle, quelle)


@pytest.fixture
async def bestand(hass, integration, nas, lege_mp3):
    """Serien ``rabe`` (a.mp3, b.mp3, Ordner ``Buch`` mit drei Tracks) und ``zwei`` (c.mp3, d.mp3); Dauern bekannt."""
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3", "b.mp3", "Buch"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    for i in (1, 2, 3):
        lege_mp3(pfad / "Buch" / f"{i}.mp3")
    pfad2 = nas.serie("zwei", "zwei", "Zweite Serie", ["c.mp3", "d.mp3"])
    lege_mp3(pfad2 / "c.mp3")
    lege_mp3(pfad2 / "d.mp3")
    await integration.medien.pruefen()
    await integration.dauer.warte_auf_ende()
    integration.medieninfo.setze_dauer("rabe", "a.mp3", 100)
    integration.medieninfo.setze_dauer("rabe", "b.mp3", 200)
    integration.medieninfo.setze_dauer("rabe", "Buch", 600, [100, 200, 300])
    integration.medieninfo.setze_dauer("zwei", "c.mp3", 50)
    return integration


async def _client(hass, hass_ws_client, name: str):
    nutzer = await hass.auth.async_create_user(name, group_ids=[GROUP_ID_USER])
    refresh = await hass.auth.async_create_refresh_token(nutzer, CLIENT_ID)
    client = await hass_ws_client(hass, hass.auth.async_create_access_token(refresh))
    client.nutzer = nutzer
    return client


# --------------------------------------------------------------------------------------------
# Start
# --------------------------------------------------------------------------------------------


async def test_start_oeffnet_die_datenbank_unter_config_tobibox(hass, integration):
    assert integration.gehoert.verfuegbar
    assert integration.gehoert.db.pfad == Path(hass.config.config_dir) / "tobibox" / "gehoert.sqlite"
    assert await hass.async_add_executor_job(integration.gehoert.db.pfad.is_file)


async def test_sqlite_laeuft_im_executor_nicht_in_der_schleife(hass, integration, box_fabrik):
    threads: list[int] = []
    echt = gehoert_modul.GehoertDb.nimm_auf

    def spion(self, *a, **k):
        threads.append(threading.get_ident())
        return echt(self, *a, **k)

    with patch.object(gehoert_modul.GehoertDb, "nimm_auf", spion):
        await box_fabrik("box1").ereignis("gespielt", nachricht(sitz()))
    assert threads and threading.get_ident() not in threads


async def test_datenbank_nicht_zu_oeffnen_start_ohne_faehigkeit(hass, starte_integration, box_fabrik):
    with patch.object(gehoert_modul.GehoertDb, "oeffne", side_effect=sqlite3.OperationalError("kaputt")):
        hub = await starte_integration()
    assert hub.gehoert.verfuegbar is False and hub.gehoert.db is None
    box = box_fabrik("box1")
    await box.status(box_faehig=["gehoert"], gehoert_wartet=True)
    assert box.befehle("gehoert_quittung") == []  # kein Handshake: die Box puffert
    await box.ereignis("gespielt", nachricht(sitz()))
    assert box.befehle("gehoert_quittung") == []
    assert hub.store.box_ereignisse.get("box1", []) == []  # trotzdem nicht in der Liste der Meldungen
    await hub.reinhoeren.melde("u", "spieler-12345", "rabe", "a.mp3", 5, 100, None, True, False)  # ohne Datenbank: still ignoriert
    assert hub.reinhoeren.offen == {}


async def test_datenbank_zu_neu_start_ohne_faehigkeit(hass, starte_integration):
    pfad = Path(hass.config.config_dir) / "tobibox" / "gehoert.sqlite"
    pfad.parent.mkdir(parents=True)
    con = sqlite3.connect(pfad)
    con.execute("PRAGMA user_version=42")
    con.execute("CREATE TABLE x (a)")
    con.commit()
    con.close()
    hub = await starte_integration()
    assert hub.gehoert.verfuegbar is False


# --------------------------------------------------------------------------------------------
# Aufnahme und Quittung
# --------------------------------------------------------------------------------------------


async def test_gespielt_wird_gespeichert_und_quittiert_nicht_in_der_liste_der_meldungen(hass, integration, box_fabrik, ereignisse):
    box = box_fabrik("box1")
    await box.ereignis("gespielt", nachricht(sitz(1), sitz(2, folge="b.mp3", ende="ende_der_folge")))
    rows = await zeilen(integration)
    assert [(r["quelle"], r["sitzung"], r["serie"], r["folge"], r["datum"], r["gehoert_s"], r["ende"]) for r in rows] == [
        ("box:box1", U1.format(1), "rabe", "a.mp3", "sicher", 100, "pause"),
        ("box:box1", U1.format(2), "rabe", "b.mp3", "sicher", 100, "ende_der_folge"),
    ]
    assert (rows[0]["tag"], rows[0]["beginn"], rows[0]["ende_um"]) == ("2026-11-16", utc(2026, 11, 16, 18, 10, 57), utc(2026, 11, 16, 18, 10, 57) + 100)
    # nie in ``boxen/list.ereignisse`` und nie als Ereignis ``ereignis`` an die Seite
    assert integration.store.box_ereignisse.get("box1", []) == []
    assert [e for e in ereignisse if e["thema"] == "boxen" and e["art"] == "ereignis"] == []
    # die Quittung läuft nachlaufend: nicht sofort, höchstens ``GEHOERT_QUITTUNG_VERZOEGERUNG_S`` danach
    assert quittungen(box) == []
    await zeit_vergeht(hass, GEHOERT_QUITTUNG_VERZOEGERUNG_S + 1)
    assert quittungen(box) == [[U1.format(1), U1.format(2)]]
    q = box.befehle("gehoert_quittung")[0]
    assert (q["v"], q["ttl_s"]) == (1, 3600) and q["erzeugt"].endswith("Z")
    topic, _n, qos, retain = [e for e in box.veroeffentlicht() if e[0] == "tobibox/box1/cmd"][-1]
    assert (qos, retain) == (1, False)


async def test_quittung_kommt_erst_nach_dem_commit(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    db = integration.gehoert.db
    sichtbar: list[int] = []
    echt = integration.mqtt.sende_befehl

    def lies_mit_eigener_verbindung() -> int:
        con = sqlite3.connect(db.pfad)  # eine zweite, eigene Verbindung: sieht nur, was wirklich committet ist
        try:
            return con.execute("SELECT count(*) FROM sitzungen").fetchone()[0]
        finally:
            con.close()

    async def spion(b, befehl, ttl, daten=None):
        sichtbar.append(await hass.async_add_executor_job(lies_mit_eigener_verbindung))
        return await echt(b, befehl, ttl, daten)

    integration.mqtt.sende_befehl = spion
    await box.ereignis("gespielt", nachricht(sitz()))
    await zeit_vergeht(hass, 3)
    assert sichtbar == [1]


async def test_zwischenstand_wird_nicht_quittiert_der_abschluss_ersetzt_ihn(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    await box.ereignis("gespielt", nachricht(sitz(1, ende="teilweise", gehoert_s=50, ende_boot_s=50450)))
    await zeit_vergeht(hass, 3)
    assert quittungen(box) == []
    rows = await zeilen(integration)
    assert [(r["ende"], r["gehoert_s"]) for r in rows] == [("teilweise", 50)]
    await box.ereignis("gespielt", nachricht(sitz(1, ende="pause", gehoert_s=100)))
    await zeit_vergeht(hass, 3)
    assert quittungen(box) == [[U1.format(1)]]
    assert [(r["ende"], r["gehoert_s"]) for r in await zeilen(integration)] == [("pause", 100)]


async def test_doppelzustellung_eine_zeile_und_die_quittung_wird_wiederholt(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    await box.ereignis("gespielt", nachricht(sitz()), eid="aaaaaaaa-0000-4000-8000-000000000001")
    await box.ereignis("gespielt", nachricht(sitz()), eid="aaaaaaaa-0000-4000-8000-000000000001")  # dieselbe ``id`` der Hülle
    await box.ereignis("gespielt", nachricht(sitz()))  # andere ``id``, dieselbe Sitzung
    await zeit_vergeht(hass, 3)
    assert len(await zeilen(integration)) == 1
    assert quittungen(box) == [[U1.format(1)]]  # gesammelt, ohne Doppelte
    await box.ereignis("gespielt", nachricht(sitz()))  # die Box hat die Quittung nicht bekommen und sendet noch einmal
    await zeit_vergeht(hass, 6)
    assert quittungen(box) == [[U1.format(1)], [U1.format(1)]]  # „schon kannte“ wird quittiert


async def test_ungueltige_zeile_nicht_gespeichert_aber_quittiert(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    await box.ereignis("gespielt", nachricht(sitz(1, gehoert_s=0), sitz(2), sitz(3, ende="gibts_nicht")))
    await zeit_vergeht(hass, 3)
    assert [r["sitzung"] for r in await zeilen(integration)] == [U1.format(2)]
    assert quittungen(box) == [[U1.format(1), U1.format(2), U1.format(3)]]


async def test_gespielt_unbekannter_box_wird_ignoriert(hass, integration, box_fabrik):
    fremd = box_fabrik("fremd")
    await fremd.ereignis("gespielt", nachricht(sitz()))
    await zeit_vergeht(hass, 3)
    assert await zeilen(integration) == [] and fremd.befehle() == []


async def test_quittung_hoechstens_hundert_uuids_je_nachricht(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    uuids = [U1.format(n) for n in range(250)]
    integration.gehoert._merke_quittung("box1", uuids)
    await hass.async_block_till_done()
    assert [len(q) for q in quittungen(box)] == [100, 100, 50]
    assert [u for q in quittungen(box) for u in q] == uuids


async def test_quittung_ohne_verbindung_wird_nicht_gesendet_die_zeile_bleibt(hass, integration, box_fabrik):
    from homeassistant.components import mqtt as ha_mqtt

    box = box_fabrik("box1")
    with patch.object(ha_mqtt, "is_connected", return_value=False):
        await box.ereignis("gespielt", nachricht(sitz()))
        await zeit_vergeht(hass, 3)
    assert quittungen(box) == [] and len(await zeilen(integration)) == 1


async def test_dauer_aus_der_medieninfo_geht_vor(hass, bestand, box_fabrik):
    await box_fabrik("box1").ereignis("gespielt", nachricht(sitz(1, folge_dauer_s=555), sitz(2, serie="unbekannt", folge="x.mp3", folge_dauer_s=555)))
    rows = await zeilen(bestand)
    assert [r["folge_dauer_s"] for r in rows] == [100, 555]  # a.mp3 ist in der Medieninfo bekannt (100), x.mp3 nicht


async def test_tag_und_stunde_in_der_zeitzone_von_ha(hass, integration, box_fabrik):
    await hass.config.async_set_time_zone("Europe/Berlin")
    await box_fabrik("box1").ereignis("gespielt", nachricht(sitz(1, beginn="2026-10-25T00:30:00Z"), sitz(2, beginn="2026-11-10T22:50:00Z")))
    assert [(r["tag"], r["stunde"]) for r in await zeilen(integration)] == [("2026-10-25", 2), ("2026-11-10", 23)]


async def test_beginn_ohne_gute_uhr_gleiche_boot_id_rechnet_vom_empfang(hass, integration, box_fabrik, freezer):
    freezer.move_to("2026-11-16 18:36:02+00:00")
    await box_fabrik("box1").ereignis("gespielt", nachricht(sitz(1, zeit_ok=False, beginn="1970-01-02T00:00:00Z", beginn_boot_s=50400, ende_boot_s=50500), gesendet=51915))
    r = (await zeilen(integration))[0]
    assert r["datum"] == "sicher" and r["beginn"] == utc(2026, 11, 16, 18, 36, 2) - (51915 - 50400)


# --------------------------------------------------------------------------------------------
# Handshake
# --------------------------------------------------------------------------------------------


async def test_handshake_antwortet_auf_jeden_status_mit_gehoert_wartet_mit_leerer_liste(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    await box.status(box_faehig=["gehoert"], gehoert_wartet=True)
    assert quittungen(box) == [[]]  # sofort, nicht nachlaufend
    await box.status(box_faehig=["gehoert"], gehoert_wartet=True)  # alle 60 s neu
    await box.status(box_faehig=["gehoert"], gehoert_wartet=True, gespeichert=True)  # auch ein alter retained status: harmlos
    assert quittungen(box) == [[], [], []]


async def test_handshake_nicht_ohne_wartet_oder_ohne_box_faehig(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    await box.status()  # Box ohne Stufe B
    await box.status(box_faehig=["gehoert"], gehoert_wartet=False)
    await box.status(gehoert_wartet=True)  # ohne ``box_faehig``
    await box.status(box_faehig=["etwas_anderes"], gehoert_wartet=True)
    await box.status(box_faehig="gehoert", gehoert_wartet=True)  # falscher Typ
    assert box.befehle("gehoert_quittung") == []
    await box.status(box_faehig=["etwas_anderes", "gehoert"], gehoert_wartet=True)  # unbekannte Werte werden ignoriert
    assert quittungen(box) == [[]]


async def test_handshake_antwort_ist_ein_befehl_der_hoechstens_100_uuids_und_ohne_pflicht_zu_zeit(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    await box.status(box_faehig=["gehoert"], gehoert_wartet=True)
    b = box.befehle("gehoert_quittung")[0]
    assert b["daten"] == {"sitzungen": []} and b["ttl_s"] == 3600 and b["id"]


# --------------------------------------------------------------------------------------------
# Technik
# --------------------------------------------------------------------------------------------


async def technik(hub, box: str | None = None) -> list[tuple[str, str | None]]:
    return [(r["art"], r["wert"]) for r in await hub.hass.async_add_executor_job(hub.gehoert.db.technik_alle, box)]


async def test_technik_erster_status_wird_nur_verglichen_wechsel_werden_geschrieben(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    await box.status(lader=False)
    assert await technik(integration) == []
    await box.status(lader=False)
    assert await technik(integration) == []  # kein Wechsel
    await box.status(lader=True)
    await box.status(lader=True)
    await box.status(lader=False)
    assert await technik(integration, "box1") == [("lader_an", None), ("lader_aus", None)]


async def test_technik_online_offline_nur_bei_echtem_wechsel(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    await box.online(True)  # der erste Stand nach dem Start von HA: nur verglichen
    assert await technik(integration) == []
    await box.online(True)
    await box.online(False)
    await box.online(True)
    assert await technik(integration, "box1") == [("offline", None), ("online", None)]
    assert await technik(integration, "box2") == []


async def test_technik_sync_ergebnis_verworfen_und_fehler(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    sync0 = {"zustand": "idle", "letzter_ende": "2026-11-09T07:00:00Z", "ergebnis": "ok", "grund": None, "neu": 0}
    await box.status(sync=sync0, gehoert_verworfen=0)
    await box.status(sync=sync0, gehoert_verworfen=0)
    assert await technik(integration) == []
    await box.status(sync={**sync0, "letzter_ende": "2026-11-09T08:00:00Z"}, gehoert_verworfen=0)
    await box.status(sync={**sync0, "letzter_ende": "2026-11-09T09:00:00Z", "ergebnis": "abgebrochen", "grund": "kein_netz"}, gehoert_verworfen=3)
    await box.status(sync={**sync0, "letzter_ende": "2026-11-09T09:00:00Z", "ergebnis": "abgebrochen", "grund": "kein_netz"}, gehoert_verworfen=3)
    await box.ereignis("fehler", {"baustein": "kopfhoerer", "code": "kopfhoerer_unlesbar", "text": "…"})
    assert await technik(integration, "box1") == [("sync_ok", None), ("sync_fehler", "kein_netz"), ("verworfen", "3"), ("fehler", "kopfhoerer_unlesbar")]


async def test_technik_zeit_ist_ts_der_box_bei_zeit_ok_sonst_empfangszeit(hass, integration, box_fabrik, freezer):
    freezer.move_to("2026-11-16 18:36:02+00:00")
    box = box_fabrik("box1")
    await box.status(lader=False)
    await box.status(lader=True, ts="2026-11-16T10:00:00Z", zeit_ok=True)
    await box.status(lader=False, ts="1999-01-01T00:00:00Z", zeit_ok=False)
    zeiten = [r["zeit"] for r in await hass.async_add_executor_job(integration.gehoert.db.technik_alle, "box1")]
    assert zeiten == [utc(2026, 11, 16, 10), utc(2026, 11, 16, 18, 36, 2)]


async def test_fehler_ereignis_bleibt_in_der_liste_der_meldungen(hass, integration, box_fabrik):
    await box_fabrik("box1").ereignis("fehler", {"baustein": "kopfhoerer", "code": "kopfhoerer_unlesbar", "text": "x"})
    assert [e["art"] for e in integration.store.box_ereignisse["box1"]] == ["fehler"]


# --------------------------------------------------------------------------------------------
# Reinhören als Sitzungen
# --------------------------------------------------------------------------------------------


class Uhr:
    """Gefälschte Uhren für ``hub.reinhoeren`` (Monotonzeit und Wanduhr laufen gleich schnell)."""

    def __init__(self, hub) -> None:
        self.m = 1000.0
        self.w = utc(2026, 11, 16, 12)
        hub.reinhoeren.mono = lambda: self.m
        hub.reinhoeren.wall = lambda: int(self.w)

    def tick(self, s: float) -> None:
        self.m += s
        self.w += s


@pytest.fixture
def uhr(bestand) -> Uhr:
    return Uhr(bestand)


async def spiele(hub, uhr: Uhr, schritte: list[tuple[float, float]], *, nutzer="u1", spieler="spieler-0001", folge="a.mp3", dauer=100, spielt=True, serie="rabe", **mehr):
    """Sendet je Schritt ``(Sekunden seit dem vorigen Aufruf, Position)``."""
    for dt, pos in schritte:
        uhr.tick(dt)
        await hub.reinhoeren.melde(nutzer, spieler, serie, folge, pos, dauer, mehr.get("track"), spielt, False)


async def reihen(hub, quelle="benutzer:u1"):
    return [(r["ende"], r["gehoert_s"], r["fertig"], r["neues_mal"]) for r in await zeilen(hub, quelle)]


async def test_reinhoeren_hoerzeit_aus_dem_fortschritt_ende_der_folge_durch_fertig(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10), (10, 20), (10, 30), (10, 40)])
    assert await reihen(bestand) == []  # noch offen, nichts geschrieben
    uhr.tick(10)
    await bestand.reinhoeren.melde("u1", "spieler-0001", "rabe", "a.mp3", 50, 100, None, True, True)
    assert await reihen(bestand) == [("ende_der_folge", 50, 0, 1)]  # 50 von 100 s: nicht fertig (80 %)
    r = (await zeilen(bestand, "benutzer:u1"))[0]
    assert (r["serie"], r["folge"], r["folge_dauer_s"], r["datum"], r["beginn"], r["ende_um"]) == ("rabe", "a.mp3", 100, "sicher", utc(2026, 11, 16, 12), utc(2026, 11, 16, 12, 0, 50))
    assert not bestand.reinhoeren.offen


async def test_reinhoeren_fertig_ab_achtzig_prozent_ueber_mehrere_portionen(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10), (10, 20), (10, 30), (10, 40)])  # 40 s
    uhr.tick(3600)  # Pause über 30 Minuten: die Sitzung endet als ``pause``
    await bestand.reinhoeren.takt()
    await spiele(bestand, uhr, [(0, 40), (10, 50), (10, 60), (10, 70), (10, 80), (10, 90)])  # weitere 50 s
    uhr.tick(5)
    await bestand.reinhoeren.melde("u1", "spieler-0001", "rabe", "a.mp3", 99, 100, None, True, True)
    assert await reihen(bestand) == [("pause", 40, 0, 1), ("ende_der_folge", 59, 1, 1)]  # 40 + 59 = 99 >= 80


async def test_reinhoeren_kappung_zwei_mal_dt_plus_zwei(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 90)])  # Sprung um 90 s in 10 s: gekappt auf 22
    await bestand.reinhoeren.schliesse_alle()
    assert await reihen(bestand) == [("dienst_ende", 22, 0, 1)]


async def test_reinhoeren_rueckwaerts_springen_setzt_die_basislinie_neu(bestand, uhr):
    await spiele(bestand, uhr, [(0, 50), (10, 60), (10, 20), (10, 30)])  # 10 s, Rücksprung (zählt nicht), wieder 10 s
    await bestand.reinhoeren.schliesse_alle()
    assert (await reihen(bestand))[0][1] == 20


async def test_reinhoeren_wiederholter_aufruf_zaehlt_nicht_doppelt(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10), (0, 10), (0, 10), (10, 20)])
    await bestand.reinhoeren.schliesse_alle()
    assert (await reihen(bestand))[0][1] == 20


async def test_reinhoeren_spulen_in_der_pause_zaehlt_nicht(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10)])  # 10 s gehört
    await spiele(bestand, uhr, [(5, 10)], spielt=False)  # Pause
    await spiele(bestand, uhr, [(5, 40), (5, 70)], spielt=False)  # in der Pause gespult: zählt nicht
    await spiele(bestand, uhr, [(5, 70)], spielt=True)  # weiter
    await spiele(bestand, uhr, [(10, 80)], spielt=True)  # 10 s
    await bestand.reinhoeren.schliesse_alle()
    assert (await reihen(bestand))[0][1] == 20


async def test_reinhoeren_pause_aufruf_schliesst_den_letzten_abschnitt_ein(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10), (7, 17)], spielt=True)
    await spiele(bestand, uhr, [(3, 20)], spielt=False)  # der Aufruf bei „Pause“: der Abschnitt davor lief noch
    await bestand.reinhoeren.schliesse_alle()
    assert (await reihen(bestand))[0][1] == 20


async def test_reinhoeren_eingefrorene_seite_zaehlt_mit_kappung_anderthalb_dt_plus_zwei(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (120, 120)], dauer=1000)  # 2 Minuten kein Aufruf, Ton lief (``spielt`` beim vorigen Aufruf)
    await bestand.reinhoeren.schliesse_alle()
    assert (await reihen(bestand))[0][1] == 120
    await spiele(bestand, uhr, [(0, 0), (120, 400)], dauer=1000, spieler="spieler-0002")
    await bestand.reinhoeren.schliesse_alle()
    assert (await reihen(bestand))[1][1] == int(1.5 * 120 + 2)  # 182, nicht 242


async def test_reinhoeren_eingefroren_aber_nicht_spielend_zaehlt_nicht(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10)])
    await spiele(bestand, uhr, [(1, 10)], spielt=False)
    await spiele(bestand, uhr, [(100, 90)], spielt=True)  # vorher nicht ``spielt``: neue Basislinie, nichts zählt
    await bestand.reinhoeren.schliesse_alle()
    assert (await reihen(bestand))[0][1] == 10


async def test_reinhoeren_andere_folge_beendet_die_sitzung_als_wechsel(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10), (10, 20)])
    await spiele(bestand, uhr, [(5, 0), (10, 10)], folge="b.mp3", dauer=200)
    assert await reihen(bestand) == [("wechsel", 20, 0, 1)]
    await bestand.reinhoeren.schliesse_alle()
    r = await zeilen(bestand, "benutzer:u1")
    assert [(x["folge"], x["ende"], x["gehoert_s"]) for x in r] == [("a.mp3", "wechsel", 20), ("b.mp3", "dienst_ende", 10)]


async def test_reinhoeren_dreissig_minuten_ohne_fortschritt_pause_mit_ende_um_des_letzten_fortschritts(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10), (10, 20)])
    uhr.tick(1799)
    await bestand.reinhoeren.takt()
    assert [r[0] for r in await reihen(bestand)] == ["teilweise"]  # noch offen (der letzte Fortschritt liegt 1799 s zurück), nur der Zwischenstand steht da
    uhr.tick(2)
    await bestand.reinhoeren.takt()
    r = (await zeilen(bestand, "benutzer:u1"))[0]
    assert (r["ende"], r["gehoert_s"], r["ende_um"]) == ("pause", 20, utc(2026, 11, 16, 12, 0, 20))
    assert not bestand.reinhoeren.offen


async def test_reinhoeren_aufruf_nach_dreissig_minuten_beginnt_eine_neue_sitzung(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10), (10, 20)])
    await spiele(bestand, uhr, [(1801, 21), (10, 31)])  # die Aufräumschleife lief nicht: der Aufruf selbst trennt
    await bestand.reinhoeren.schliesse_alle()
    assert [(x["ende"], x["gehoert_s"], x["neues_mal"]) for x in await zeilen(bestand, "benutzer:u1")] == [("pause", 20, 1), ("dienst_ende", 10, 1)]


async def test_reinhoeren_pause_bis_dreissig_minuten_bleibt_eine_sitzung_ein_mal(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10), (10, 20)])
    uhr.tick(1500)
    await bestand.reinhoeren.takt()
    await spiele(bestand, uhr, [(0, 20), (10, 30), (10, 40)])
    await bestand.reinhoeren.schliesse_alle()
    assert await reihen(bestand) == [("dienst_ende", 40, 0, 1)]


async def test_reinhoeren_teilweise_alle_fuenf_minuten_dann_ersetzt_der_abschluss(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10), (10, 20)])
    await bestand.reinhoeren.takt()
    assert [r["ende"] for r in await zeilen(bestand, "benutzer:u1")] == ["teilweise"]  # die erste Zeile gleich beim ersten Takt mit Hörzeit
    sitzung = (await zeilen(bestand, "benutzer:u1"))[0]["sitzung"]
    await spiele(bestand, uhr, [(10, 30)])
    uhr.tick(REINHOEREN_SCHREIBEN_S - 20)
    await bestand.reinhoeren.takt()
    assert (await zeilen(bestand, "benutzer:u1"))[0]["gehoert_s"] == 20  # noch nicht fünf Minuten seit dem Schreiben
    uhr.tick(25)
    await spiele(bestand, uhr, [(1, 60)], dauer=100)
    await bestand.reinhoeren.takt()
    rows = await zeilen(bestand, "benutzer:u1")
    assert len(rows) == 1 and rows[0]["sitzung"] == sitzung and rows[0]["ende"] == "teilweise" and rows[0]["gehoert_s"] > 20
    uhr.tick(5)
    await bestand.reinhoeren.melde("u1", "spieler-0001", "rabe", "a.mp3", 99, 100, None, True, True)
    rows = await zeilen(bestand, "benutzer:u1")
    assert len(rows) == 1 and rows[0]["sitzung"] == sitzung and rows[0]["ende"] == "ende_der_folge"  # dieselbe UUID: der Abschluss ersetzt


async def test_reinhoeren_ohne_hoerzeit_keine_zeile(bestand, uhr):
    await spiele(bestand, uhr, [(0, 5), (2, 5)])
    await bestand.reinhoeren.takt()
    await bestand.reinhoeren.schliesse_alle()
    assert await zeilen(bestand) == []


async def test_reinhoeren_zwei_spieler_zaehlen_doppelt_hoechstens_fuenf_je_benutzer(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10)], spieler="spieler-0001")
    await spiele(bestand, uhr, [(0, 0), (10, 10)], spieler="spieler-0002")
    await bestand.reinhoeren.schliesse_alle()
    assert [r[1] for r in await reihen(bestand)] == [10, 10]  # zwei Fenster mit derselben Folge: beides zählt
    # sechs Spieler: der älteste endet als ``wechsel``
    for i in range(REINHOEREN_SPIELER_MAX + 1):
        uhr.tick(1)
        await spiele(bestand, uhr, [(0, 0), (5, 5)], spieler=f"neuer-spieler-{i}", nutzer="u2")
    assert len([k for k in bestand.reinhoeren.offen if k[0] == "u2"]) == REINHOEREN_SPIELER_MAX
    ersetzt = await zeilen(bestand, "benutzer:u2")
    assert [(r["ende"], r["gehoert_s"]) for r in ersetzt] == [("wechsel", 5)]


async def test_reinhoeren_ohne_spieler_eine_sitzung_je_benutzer(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10)], spieler=None)
    await spiele(bestand, uhr, [(10, 20)], spieler=None)
    assert len(bestand.reinhoeren.offen) == 1
    await bestand.reinhoeren.schliesse_alle()
    assert (await reihen(bestand))[0][1] == 20


async def test_reinhoeren_ordner_folge_mit_spuren_zaehlt_ueber_trackgrenzen(bestand, uhr):
    # Spuren [100, 200, 300]: Ende von Track 1 (95 s) und Anfang von Track 2 (5 s) sind in der Folge 10 s auseinander
    for dt, track, pos in [(0, 0, 90), (5, 0, 95), (5, 1, 5), (5, 1, 10)]:
        uhr.tick(dt)
        await bestand.reinhoeren.melde("u1", "spieler-0001", "rabe", "Buch", pos, 100 if track == 0 else 200, track, True, False)
    await bestand.reinhoeren.schliesse_alle()
    r = (await zeilen(bestand, "benutzer:u1"))[0]
    assert (r["folge"], r["gehoert_s"], r["folge_dauer_s"]) == ("Buch", 20, 600)


async def test_reinhoeren_ordner_folge_ohne_bekannte_spuren_neue_basislinie_beim_trackwechsel(bestand, uhr):
    bestand.medieninfo.setze_dauer("rabe", "Buch", 600)  # ohne Spuren
    for dt, track, pos in [(0, 0, 90), (5, 0, 95), (5, 1, 5), (5, 1, 10)]:
        uhr.tick(dt)
        await bestand.reinhoeren.melde("u1", "spieler-0001", "rabe", "Buch", pos, 100, track, True, False)
    await bestand.reinhoeren.schliesse_alle()
    assert (await reihen(bestand))[0][1] == 10  # 5 s im Track 0, der Wechsel zählt nicht, 5 s im Track 1


async def test_reinhoeren_verwaist_nach_neustart_von_ha_nach_dreissig_minuten(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10)])
    await bestand.reinhoeren.takt()  # schreibt ``teilweise``
    bestand.reinhoeren.offen.clear()  # HA wird neu gestartet: der Arbeitsspeicher ist weg
    jetzt_s = utc(2026, 11, 16, 12, 0, 10)
    assert await bestand.gehoert.raeume_auf(jetzt_s + 1799) == 0
    assert await bestand.gehoert.raeume_auf(jetzt_s + 1801) == 1
    assert [r["ende"] for r in await zeilen(bestand, "benutzer:u1")] == ["verwaist"]


async def test_reinhoeren_beenden_von_ha_schliesst_offene_sitzungen_als_dienst_ende(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10)])
    pfad = bestand.gehoert.db.pfad
    await bestand.async_stop()
    con = sqlite3.connect(pfad)
    assert con.execute("SELECT ende, gehoert_s FROM sitzungen WHERE quelle='benutzer:u1'").fetchall() == [("dienst_ende", 10)]
    con.close()
    assert bestand.gehoert.db is None


async def test_reinhoeren_quelle_ist_der_benutzer_nie_eine_box(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10)], nutzer="abc-123")
    await bestand.reinhoeren.schliesse_alle()
    assert {r["quelle"] for r in await zeilen(bestand)} == {"benutzer:abc-123"}


async def test_reinhoeren_loeschmarke_gilt_auch_hier(hass, bestand, uhr):
    await hass.async_add_executor_job(bestand.gehoert.db.loesche, ["benutzer:u1"], utc(2026, 11, 16, 12, 0, 30))
    await spiele(bestand, uhr, [(0, 0), (10, 10)])
    await bestand.reinhoeren.schliesse_alle()  # ``ende_um`` 12:00:10 liegt vor der Löschung: verworfen
    assert await zeilen(bestand, "benutzer:u1") == []
    uhr.tick(100)
    await spiele(bestand, uhr, [(0, 0), (10, 10)])
    await bestand.reinhoeren.schliesse_alle()  # danach gehört: gilt
    assert [r["ende_um"] for r in await zeilen(bestand, "benutzer:u1")] == [utc(2026, 11, 16, 12, 2, 0)]


# --- Befehl 41 -------------------------------------------------------------------------------------------


async def test_befehl_41_nimmt_spieler_und_spielt_an_und_zaehlt_hoerzeit(hass, bestand, hass_ws_client, uhr):
    anna = await _client(hass, hass_ws_client, "Anna")
    u = anna.nutzer.id
    for dt, pos in [(0, 0), (10, 10), (10, 20)]:
        uhr.tick(dt)
        assert await ok(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=pos, dauer_s=100, spieler="abcdefgh-ijkl_1", spielt=True) == {}
    uhr.tick(5)
    await ok(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=30, dauer_s=100, spieler="abcdefgh-ijkl_1", spielt=True, fertig=True)
    rows = await zeilen(bestand, f"benutzer:{u}")
    assert [(r["ende"], r["gehoert_s"]) for r in rows] == [("ende_der_folge", 30)]
    # die Hörstelle (Weiterhören) arbeitet wie bisher
    assert (await ok(anna, "hoerstelle/get", serie_id="rabe"))["folgen"]["a.mp3"]["position_s"] == 30


@pytest.mark.parametrize("spieler", ["kurz", "x" * 65, "mit leerzeichen!", "ümlaut-spieler", 5])
async def test_befehl_41_ungueltiger_spieler(hass, bestand, hass_ws_client, spieler):
    anna = await _client(hass, hass_ws_client, "Anna")
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=1, dauer_s=100, spieler=spieler) == "invalid_format"
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=1, dauer_s=100, spielt="ja") == "invalid_format"


async def test_befehl_41_alte_seite_ohne_spieler_und_spielt_geht_weiter(hass, bestand, hass_ws_client, uhr):
    anna = await _client(hass, hass_ws_client, "Anna")
    for dt, pos in [(0, 0), (10, 10), (10, 20)]:
        uhr.tick(dt)
        await ok(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=pos, dauer_s=100)
    assert len(bestand.reinhoeren.offen) == 1  # eine Sitzung je Benutzer


async def test_befehl_41_ist_nicht_idempotent_aber_eine_wiederholung_zaehlt_nichts_doppelt(hass, bestand, hass_ws_client, uhr):
    anna = await _client(hass, hass_ws_client, "Anna")
    for dt, pos in [(0, 0), (10, 10), (0, 10), (0, 10)]:
        uhr.tick(dt)
        await ok(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=pos, dauer_s=100, spieler="abcdefgh", spielt=True)
    await bestand.reinhoeren.schliesse_alle()
    assert (await zeilen(bestand, f"benutzer:{anna.nutzer.id}"))[0]["gehoert_s"] == 10


async def test_befehl_41_sechzig_aufrufe_je_minute(hass, bestand, hass_ws_client, freezer):
    assert HOERSTELLE_SCHREIBEN_JE_MINUTE == 60
    anna = await _client(hass, hass_ws_client, "Anna")
    for i in range(60):
        await ok(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=i % 90, dauer_s=100, spieler="abcdefgh", spielt=True)
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=1, dauer_s=100) == "zu_viele_aenderungen"
    freezer.tick(timedelta(seconds=61))
    await ok(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=1, dauer_s=100)


async def test_befehl_41_pruefung_bleibt_wie_bisher_und_zaehlt_dann_nichts(hass, bestand, hass_ws_client, uhr):
    anna = await _client(hass, hass_ws_client, "Anna")
    assert await fehler(anna, "hoerstelle/set", serie_id="gibts-nicht", folge="a.mp3", position_s=1, dauer_s=100, spieler="abcdefgh", spielt=True) == "serie_nicht_gefunden"
    assert await fehler(anna, "hoerstelle/set", serie_id="rabe", folge="a.mp3", position_s=500, dauer_s=100, spieler="abcdefgh", spielt=True) == "invalid_format"
    assert bestand.reinhoeren.offen == {}


# --------------------------------------------------------------------------------------------
# Favoriten
# --------------------------------------------------------------------------------------------


async def test_favoriten_setzen_wiederholen_und_wegnehmen(bestand):
    f = bestand.favoriten
    assert f.setze("u1", "rabe", None, True) is True
    assert f.setze("u2", "rabe", None, True) is False  # Wiederholung: ohne Fehler und ohne Wirkung, der erste „gesetzt_von“ bleibt
    assert f.setze("u1", "rabe", "a.mp3", True) is True
    assert [(e["serie_id"], e["folge"], e["gesetzt_von"]) for e in f.liste()] == [("rabe", None, "u1"), ("rabe", "a.mp3", "u1")]
    assert f.liste()[0]["gesetzt_am"].endswith("Z")
    assert f.ist_favorit("rabe") and f.ist_favorit("rabe", "a.mp3") and not f.ist_favorit("rabe", "b.mp3")
    assert f.menge() == {("rabe", None), ("rabe", "a.mp3")}
    assert f.setze("u1", "rabe", "a.mp3", False) is True
    assert f.setze("u1", "rabe", "a.mp3", False) is False
    assert not f.ist_favorit("rabe", "a.mp3")


async def test_favoriten_fehler(bestand):
    f = bestand.favoriten
    with pytest.raises(TobiboxFehler) as e:
        f.setze("u1", "gibtsnicht", None, True)
    assert e.value.code == "serie_nicht_gefunden"
    with pytest.raises(TobiboxFehler) as e:
        f.setze("u1", "rabe", "x.mp3", True)
    assert e.value.code == "folge_nicht_gefunden"
    assert f.liste() == []


async def test_favoriten_hoechstens_1000(bestand, monkeypatch):
    monkeypatch.setattr(favoriten_modul, "FAVORITEN_MAX", 2)
    f = bestand.favoriten
    f.setze("u", "rabe", None, True)
    f.setze("u", "rabe", "a.mp3", True)
    with pytest.raises(TobiboxFehler) as e:
        f.setze("u", "rabe", "b.mp3", True)
    assert e.value.code == "zu_viele_favoriten"
    assert f.setze("u", "rabe", "a.mp3", True) is False  # Wiederholung ist auch am Limit kein Fehler
    f.setze("u", "rabe", "a.mp3", False)
    f.setze("u", "rabe", "b.mp3", True)


def test_favoriten_konstante_1000():
    from custom_components.tobibox.const import FAVORITEN_MAX

    assert FAVORITEN_MAX == 1000


async def test_favoriten_gelöschte_eintraege_fallen_beim_lesen_weg_nicht_im_speicher(hass, bestand, hass_ws_client):
    admin = await hass_ws_client(hass)
    bestand.favoriten.setze("u", "rabe", "b.mp3", True)
    bestand.favoriten.setze("u", "zwei", None, True)
    bestand.favoriten.setze("u", "rabe", None, True)
    await ok(admin, "folge/delete", serie_id="rabe", folge="b.mp3")
    await ok(admin, "serie/delete", serie_id="zwei")
    assert [(e["serie_id"], e["folge"]) for e in bestand.favoriten.liste()] == [("rabe", None)]
    assert len(bestand.favoriten.eintraege) == 3  # der Speicher wird nicht sofort bereinigt


async def test_favoriten_store_ueberlebt_den_neustart_und_schreibt_gesammelt(hass, bestand, hass_storage):
    bestand.favoriten.setze("u1", "rabe", "a.mp3", True)
    assert "tobibox.favoriten" not in hass_storage  # auf der Platte gesammelt
    await zeit_vergeht(hass, 30)
    gespeichert = hass_storage["tobibox.favoriten"]
    assert gespeichert["version"] == 1
    assert gespeichert["data"]["eintraege"][0]["serie_id"] == "rabe" and gespeichert["data"]["eintraege"][0]["folge"] == "a.mp3"
    neu = Favoriten(bestand)
    await neu.async_laden()
    assert neu.eintraege == bestand.favoriten.eintraege


async def test_favoriten_laden_verwirft_ungueltiges_und_doppeltes(hass, bestand, hass_storage):
    gut = {"serie_id": "rabe", "folge": None, "gesetzt_von": "u", "gesetzt_am": "2026-11-16T10:00:00Z"}
    hass_storage["tobibox.favoriten"] = {
        "version": 1,
        "key": "tobibox.favoriten",
        "data": {"eintraege": [gut, dict(gut), {"serie_id": 5}, "text", {**gut, "folge": ""}, {**gut, "folge": "a.mp3", "extra": 1}]},
    }
    neu = Favoriten(bestand)
    await neu.async_laden()
    assert neu.eintraege == [gut, {**gut, "folge": "a.mp3"}]


async def test_favoriten_ohne_geprueftes_nas_blenden_nichts_aus(bestand):
    bestand.favoriten.setze("u", "rabe", "a.mp3", True)
    bestand.favoriten.eintraege.append({"serie_id": "weg", "folge": None, "gesetzt_von": "u", "gesetzt_am": "2026-11-16T10:00:00Z"})
    bestand.medien.geprueft_am = None
    assert len(bestand.favoriten.liste()) == 2


# --------------------------------------------------------------------------------------------
# Verschieben und Zusammenführen
# --------------------------------------------------------------------------------------------


async def test_verschieben_schreibt_hoerdaten_und_favoriten_mit(hass, bestand):
    nutzer = {"serie": "rabe", "folge": "a.mp3"}
    await bestand.gehoert.nimm_zeilen_auf("box:box1", [gehoert_modul.Zeile(U1.format(1), "rabe", "a.mp3", 100, utc(2026, 11, 16, 12), utc(2026, 11, 16, 12, 1), "sicher", 60, "pause")])
    await bestand.gehoert.nimm_zeilen_auf("benutzer:u1", [gehoert_modul.Zeile(U1.format(2), "rabe", "b.mp3", 200, utc(2026, 11, 16, 12), utc(2026, 11, 16, 12, 1), "sicher", 60, "pause")])
    bestand.favoriten.setze("u1", "rabe", "a.mp3", True)
    bestand.favoriten.setze("u1", "rabe", "b.mp3", True)
    assert nutzer
    erg = await bestand.medien.folge_verschieben("rabe", "a.mp3", "zwei", False, None)
    neuer = erg["folge"]
    rows = {r["sitzung"]: (r["serie"], r["folge"]) for r in await zeilen(bestand)}
    assert rows == {U1.format(1): ("zwei", neuer), U1.format(2): ("rabe", "b.mp3")}
    assert bestand.favoriten.menge() == {("zwei", neuer), ("rabe", "b.mp3")}


async def test_verschieben_in_eine_serie_mit_gleichem_namen_neuer_name_wird_mitgeschrieben(hass, bestand, nas, lege_mp3):
    lege_mp3(nas.medien / "zwei" / "a.mp3")
    await bestand.medien.pruefen()
    await bestand.gehoert.nimm_zeilen_auf("box:box1", [gehoert_modul.Zeile(U1.format(1), "rabe", "a.mp3", 100, utc(2026, 11, 16, 12), utc(2026, 11, 16, 12, 1), "sicher", 60, "pause")])
    await bestand.gehoert.nimm_zeilen_auf("box:box1", [gehoert_modul.Zeile(U1.format(3), "zwei", "a.mp3", 100, utc(2026, 11, 16, 13), utc(2026, 11, 16, 13, 1), "sicher", 60, "pause")])
    erg = await bestand.medien.folge_verschieben("rabe", "a.mp3", "zwei", False, None)
    assert erg["folge"] == "a (2).mp3"
    rows = {r["sitzung"]: (r["serie"], r["folge"]) for r in await zeilen(bestand)}
    assert rows == {U1.format(1): ("zwei", "a (2).mp3"), U1.format(3): ("zwei", "a.mp3")}  # die alten Zeilen am Ziel gehören weiter zur alten Datei


async def test_zusammenfuehren_schreibt_alle_folgen_und_den_stern_der_serie_mit(hass, bestand):
    h = bestand.gehoert
    z = gehoert_modul.Zeile
    await h.nimm_zeilen_auf("box:box1", [z(U1.format(1), "zwei", "c.mp3", 50, utc(2026, 11, 16, 12), utc(2026, 11, 16, 12, 1), "sicher", 40, "pause")])
    await h.nimm_zeilen_auf("box:box1", [z(U1.format(2), "zwei", "d.mp3", None, utc(2026, 11, 16, 13), utc(2026, 11, 16, 13, 1), "sicher", 40, "pause")])
    await h.nimm_zeilen_auf("box:box1", [z(U1.format(3), "rabe", "a.mp3", 100, utc(2026, 11, 16, 14), utc(2026, 11, 16, 14, 1), "sicher", 40, "pause")])
    bestand.favoriten.setze("u1", "zwei", None, True)
    bestand.favoriten.setze("u1", "zwei", "d.mp3", True)
    bestand.favoriten.setze("u1", "rabe", None, True)
    erg = await bestand.medien.serien_zusammenfuehren("zwei", "rabe", False, None, None)
    assert erg["verschoben"] == 2
    rows = {r["sitzung"]: (r["serie"], r["folge"]) for r in await zeilen(bestand)}
    assert rows == {U1.format(1): ("rabe", "c.mp3"), U1.format(2): ("rabe", "d.mp3"), U1.format(3): ("rabe", "a.mp3")}
    assert bestand.favoriten.menge() == {("rabe", None), ("rabe", "d.mp3")}  # der Stern an der Serie war am Ziel schon: bleibt einer
    assert [e["serie_id"] for e in bestand.favoriten.eintraege].count("zwei") == 0


async def test_zusammenfuehren_rechnet_die_gruppe_neu_wiederholte_namen_mit_suffix(hass, bestand, nas, lege_mp3):
    lege_mp3(nas.medien / "rabe" / "c.mp3")
    await bestand.medien.pruefen()
    z = gehoert_modul.Zeile
    await bestand.gehoert.nimm_zeilen_auf("box:box1", [z(U1.format(1), "zwei", "c.mp3", None, utc(2026, 11, 16, 12), utc(2026, 11, 16, 12, 1), "sicher", 40, "pause")])
    await bestand.medien.serien_zusammenfuehren("zwei", "rabe", False, None, None)
    rows = await zeilen(bestand)
    assert [(r["serie"], r["folge"]) for r in rows] == [("rabe", "c (2).mp3")]


async def test_verschieben_ohne_datenbank_geht_trotzdem(hass, starte_integration, nas, lege_mp3):
    with patch.object(gehoert_modul.GehoertDb, "oeffne", side_effect=sqlite3.OperationalError("kaputt")):
        hub = await starte_integration()
    pfad = nas.serie("rabe", "rabe", "Rabe", ["a.mp3"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(nas.serie("zwei", "zwei", "Zwei", ["c.mp3"]) / "c.mp3")
    await hub.medien.pruefen()
    erg = await hub.medien.folge_verschieben("rabe", "a.mp3", "zwei", False, None)
    assert erg["folge"] == "a.mp3"


async def test_verschieben_datenbankfehler_bricht_das_verschieben_nicht_ab(hass, bestand):
    with patch.object(gehoert_modul.GehoertDb, "schreibe_um", side_effect=sqlite3.OperationalError("voll")):
        erg = await bestand.medien.folge_verschieben("rabe", "a.mp3", "zwei", False, None)
    assert erg["folge"] == "a.mp3"


# --------------------------------------------------------------------------------------------
# Löschmarke über den Manager
# --------------------------------------------------------------------------------------------


async def test_nachgelieferte_zeile_nach_loeschung_wird_verworfen_und_trotzdem_quittiert(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    await integration.gehoert.loesche(["box:box1"])  # Marke: jetzt
    await box.ereignis("gespielt", nachricht(sitz(1, beginn="2026-01-02T10:00:00Z")))  # lange vor der Löschung
    await zeit_vergeht(hass, 3)
    assert await zeilen(integration) == []
    assert quittungen(box) == [[U1.format(1)]]


async def test_loeschen_entfernt_nur_die_gewaehlte_quelle(hass, integration, box_fabrik):
    await box_fabrik("box1").ereignis("gespielt", nachricht(sitz(1)))
    await box_fabrik("box2").ereignis("gespielt", nachricht(sitz(2)))
    assert await integration.gehoert.loesche(["box:box1"]) == 1
    assert [r["quelle"] for r in await zeilen(integration)] == ["box:box2"]


async def test_aufraeumen_laeuft_ueber_den_manager(hass, integration, box_fabrik):
    await box_fabrik("box1").ereignis("gespielt", nachricht(sitz(1, ende="teilweise", beginn="2026-01-02T10:00:00Z")))
    assert await integration.gehoert.raeume_auf() == 1
    assert [r["ende"] for r in await zeilen(integration)] == ["verwaist"]


def test_json_beispiel_des_vertrags_ist_gueltig():
    """Das Beispiel aus ``mqtt-v1.md`` 3.4 (eine Sitzung am Ende der Folge) wird angenommen."""
    daten = json.loads(
        """{"boot_id": "7c1f9a52-0d3e-4b86-a1c4-5e92d0b8f317", "gesendet_boot_s": 51915, "sitzungen": [{"sitzung": "e3a8b1c4-52d7-4f09-b6a1-0c9d84e7f215",
        "serie": "3f9a1c07b2d4", "folge": "folge-02.mp3", "folge_dauer_s": 1520, "beginn": "2026-11-16T18:10:57Z", "zeit_ok": true,
        "boot_id": "7c1f9a52-0d3e-4b86-a1c4-5e92d0b8f317", "beginn_boot_s": 50400, "ende_boot_s": 51910, "gehoert_s": 1500, "ende": "ende_der_folge"}]}"""
    )
    zeilen_, quittung = gehoert_modul.verarbeite_box_nachricht(daten, utc(2026, 11, 16, 18, 36, 2))
    assert len(zeilen_) == 1 and quittung == ["e3a8b1c4-52d7-4f09-b6a1-0c9d84e7f215"]


# --------------------------------------------------------------------------------------------
# Nacharbeit nach dem Review
# --------------------------------------------------------------------------------------------


async def test_ha_stop_ereignis_schliesst_reinhoeren_als_dienst_ende_und_die_datenbank(hass, bestand, uhr):
    from homeassistant.const import EVENT_HOMEASSISTANT_STOP

    await spiele(bestand, uhr, [(0, 0), (10, 10)])
    pfad = bestand.gehoert.db.pfad
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)  # nicht ``async_stop()``: das echte Ereignis beim Herunterfahren
    await hass.async_block_till_done()
    con = sqlite3.connect(pfad)
    assert con.execute("SELECT ende, gehoert_s FROM sitzungen WHERE quelle='benutzer:u1'").fetchall() == [("dienst_ende", 10)]
    con.close()
    assert bestand.gehoert.db is None and not bestand.reinhoeren.offen
    await bestand.async_stop()  # danach das Entladen: doppelt schadet nichts


async def test_giftpille_wird_ungueltig_quittiert_der_rest_der_nachricht_gespeichert(hass, integration, box_fabrik):
    box = box_fabrik("box1")
    gift = [
        sitz(1, ende_boot_s=10**30, gehoert_s=5),
        sitz(2, folge_dauer_s=10**30),
        sitz(3, beginn="9999-12-31T23:59:59Z"),
        sitz(4, beginn_boot_s=10**30, ende_boot_s=10**30),
        sitz(5, gehoert_s=10**30),
    ]
    await box.ereignis("gespielt", nachricht(*gift, sitz(6), gesendet=10**30))
    await box.ereignis("gespielt", nachricht(*gift, sitz(6)))
    await zeit_vergeht(hass, 3)
    rows = await zeilen(integration)
    assert [(r["sitzung"], r["gehoert_s"]) for r in rows] == [(U1.format(5), 102), (U1.format(6), 100)]  # zu große Hörzeit wird gekappt, nicht verworfen
    assert set(quittungen(box)[0]) == {U1.format(n) for n in range(1, 7)}


def test_giftpille_in_der_pruefung_und_in_der_datenbank(tmp_path):
    from custom_components.tobibox.gehoert import GehoertDb, Zeile, verarbeite_box_nachricht
    from zoneinfo import ZoneInfo

    jetzt = utc(2026, 11, 16, 18, 36, 2)
    zeilen_, quittung = verarbeite_box_nachricht(nachricht(sitz(1, beginn="2026-11-18T10:00:00Z"), sitz(2)), jetzt)
    assert [z.sitzung for z in zeilen_] == [U1.format(2)] and len(quittung) == 2  # Beginn in der Zukunft bei guter Uhr: ungültig
    d = GehoertDb(tmp_path / "g.sqlite")
    d.oeffne()
    schlecht = Zeile(U1.format(1), "s", "f", None, 10**20, 10**20, "sicher", 5, "pause")
    gut = Zeile(U1.format(2), "s", "f", None, jetzt, jetzt + 5, "sicher", 5, "pause")
    erg = d.nimm_auf("box:box1", [schlecht, gut], ZoneInfo("UTC"))
    assert erg["gespeichert"] == 1 and erg["ungueltig"] == 1
    assert [r["sitzung"] for r in d.alle()] == [U1.format(2)]
    d.schliesse()


async def test_reinhoeren_eine_ausnahme_bei_einem_benutzer_haelt_die_anderen_nicht_auf(bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10)], nutzer="u1")
    await spiele(bestand, uhr, [(0, 0), (10, 10)], nutzer="u2", spieler="spieler-0002")
    echt = bestand.gehoert.nimm_zeilen_auf

    async def kaputt(quelle, zeilen_):
        if quelle == "benutzer:u1":
            raise RuntimeError("kaputt")
        return await echt(quelle, zeilen_)

    bestand.gehoert.nimm_zeilen_auf = kaputt
    await bestand.reinhoeren.takt()
    uhr.tick(3600)
    await bestand.reinhoeren.takt()
    await bestand.reinhoeren.schliesse_alle()
    bestand.gehoert.nimm_zeilen_auf = echt
    assert [r["ende"] for r in await zeilen(bestand, "benutzer:u2")] in (["pause"], ["teilweise"], ["dienst_ende"])
    assert await zeilen(bestand, "benutzer:u2") != []


async def test_verschieben_schreibt_mit_auch_wenn_serie_json_nicht_zu_schreiben_ist(hass, bestand):
    z = gehoert_modul.Zeile
    await bestand.gehoert.nimm_zeilen_auf("box:box1", [z(U1.format(1), "rabe", "a.mp3", 100, utc(2026, 11, 16, 12), utc(2026, 11, 16, 12, 1), "sicher", 60, "pause")])
    bestand.favoriten.setze("u1", "rabe", "a.mp3", True)
    with patch("custom_components.tobibox.media.schreibe_serie", side_effect=OSError("voll")), pytest.raises(TobiboxFehler):
        await bestand.medien.folge_verschieben("rabe", "a.mp3", "zwei", False, None)
    assert [(r["serie"], r["folge"]) for r in await zeilen(bestand)] == [("zwei", "a.mp3")]
    assert bestand.favoriten.eintraege[0]["serie_id"] == "zwei"


async def test_zusammenfuehren_schreibt_mit_auch_wenn_serie_json_nicht_zu_schreiben_ist(hass, bestand):
    z = gehoert_modul.Zeile
    await bestand.gehoert.nimm_zeilen_auf("box:box1", [z(U1.format(1), "zwei", "c.mp3", 50, utc(2026, 11, 16, 12), utc(2026, 11, 16, 12, 1), "sicher", 40, "pause")])
    with patch("custom_components.tobibox.media.schreibe_serie", side_effect=OSError("voll")), pytest.raises(TobiboxFehler):
        await bestand.medien.serien_zusammenfuehren("zwei", "rabe", False, None, None)
    assert [(r["serie"], r["folge"]) for r in await zeilen(bestand)] == [("rabe", "c.mp3")]


async def test_verschieben_zieht_offene_reinhoer_sitzungen_mit(hass, bestand, uhr):
    await spiele(bestand, uhr, [(0, 0), (10, 10)])
    await bestand.medien.folge_verschieben("rabe", "a.mp3", "zwei", False, None)
    lauf = next(iter(bestand.reinhoeren.offen.values()))
    assert (lauf.serie, lauf.folge) == ("zwei", "a.mp3")
    await bestand.reinhoeren.schliesse_alle()
    assert [(r["serie"], r["folge"]) for r in await zeilen(bestand, "benutzer:u1")] == [("zwei", "a.mp3")]


def test_technik_fehlendes_sync_im_status_behaelt_den_alten_stand():
    from custom_components.tobibox.gehoert import TechnikBeobachter

    t = TechnikBeobachter()
    sync = {"letzter_ende": "2026-11-09T07:00:00Z", "ergebnis": "ok", "grund": None}
    assert t.status("box1", {"sync": sync}, 5) == []
    assert t.status("box1", {}, 6) == []  # ``sync`` fehlt
    assert t.status("box1", {"sync": sync}, 7) == []  # gleiches ``letzter_ende``: kein Wechsel
