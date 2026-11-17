"""``ha`` und „Gehört“ (B1): Handshake, Senden, Quittung (``mqtt-v1.md`` 3.3, 3.4, 3.7, 4.5), ohne Netz."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from fixtures.gehoert_harnisch import ANDERE, Box, uuid_nr
from fixtures.ha_fake import Aufbau, cmd

from tobibox import gehoert as g
from tobibox.ha import GEHOERT_STATUS_WARTEN_S, STATUS_MIN_ABSTAND_S

CMD = "tobibox/box1/cmd"
EVENT = "tobibox/box1/event"
STATUS = "tobibox/box1/status"
HA_STATUS = "homeassistant/status"


def eine_folge(h: Box, sekunden: int = 20, folge: str | None = None) -> None:
    h.abspielen(folge) if folge else h.abspielen()
    h.spiele(sekunden)
    h.folge_zu_ende()


async def aufbau(tmp_path, zeilen: int = 3, verbunden: bool = True) -> tuple[Aufbau, Box]:
    """Eine Box mit ``zeilen`` fertigen Sitzungen im Puffer und ``ha`` mit dem Beobachter; Uhr gemeinsam."""
    verz = tmp_path / "z"
    h = Box(verz)
    for _ in range(zeilen):
        eine_folge(h)
    a = Aufbau(verz, gehoert=h.p, uhr=h.uhr)
    await a.start(verbunden)
    return a, h


def gespielt(a: Aufbau) -> list[dict]:
    return [e for e in a.klient.json_auf(EVENT) if e["art"] == "gespielt"]


def status(a: Aufbau) -> dict:
    return a.klient.json_auf(STATUS)[-1]


def ids(nachrichten: list[dict]) -> list[str]:
    return [s["sitzung"] for n in nachrichten for s in n["daten"]["sitzungen"]]


async def quittung(a: Aufbau, sitzungen: list[str], **zusatz) -> None:
    a.klient.eingang(CMD, cmd("gehoert_quittung", daten={"sitzungen": sitzungen}, **zusatz))
    await a.ha.leere()


def tick(a: Aufbau, sekunden: float = 0.0) -> None:
    a.uhr.vor(sekunden)
    a.ha.tick()


async def handshake(a: Aufbau, quittiert: list[str] | None = None) -> None:
    """HA antwortet auf den Status mit einer Quittung (leer); der Status mit ``gehoert_wartet = false`` geht danach hinaus."""
    await quittung(a, quittiert or [])
    tick(a, STATUS_MIN_ABSTAND_S)


# --- Status (3.3) ---------------------------------------------------------------------------------------


async def test_status_meldet_faehigkeit_handshake_und_verworfene(tmp_path):
    a, h = await aufbau(tmp_path)
    s = status(a)
    assert s["box_faehig"] == ["gehoert"] and s["gehoert_wartet"] is True and s["gehoert_verworfen"] == 0
    h.p.z = replace(h.p.z, verworfen=4)
    tick(a, STATUS_MIN_ABSTAND_S)
    assert status(a)["gehoert_verworfen"] == 4
    await a.stop()


async def test_ohne_beobachter_bleibt_der_status_wie_vor_stufe_b(tmp_path):
    a = await Aufbau(tmp_path / "z").start()
    assert not any(k in status(a) for k in ("box_faehig", "gehoert_wartet", "gehoert_verworfen"))
    await a.stop()


# --- Handshake (4.5, Punkt 1) -------------------------------------------------------------------------


async def test_neue_ha_handshake_dann_senden_dann_quittung(tmp_path):
    a, h = await aufbau(tmp_path, 3)
    puffer = h.zeilen()
    tick(a, 5)
    assert gespielt(a) == []  # vor dem Handshake wird nichts gesendet
    await quittung(a, [])  # HA antwortet auf den Status mit leerer Liste
    assert gespielt(a) == []  # erst muss ``gehoert_wartet = false`` im Status stehen
    tick(a, STATUS_MIN_ABSTAND_S)
    assert status(a)["gehoert_wartet"] is False
    (n,) = gespielt(a)  # alle Zeilen in einer Nachricht
    assert n["v"] == 1 and n["daten"]["boot_id"] == "boot-1" and n["daten"]["gesendet_boot_s"] == int(a.uhr.mono)
    assert n["daten"]["sitzungen"] == puffer  # genau die Zeilen des Puffers, ohne Kennung des Tobies
    assert set(n["daten"]) == {"boot_id", "gesendet_boot_s", "sitzungen"}
    assert a.klient.auf(EVENT)[-1][1] is False  # nicht retained
    await quittung(a, ids([n]))
    assert h.zeilen() == []
    tick(a, 700)
    assert len(gespielt(a)) == 1  # nichts wird noch einmal gesendet
    await a.stop()


async def test_alte_ha_antwortet_nie_die_box_sendet_nichts_und_meldet_den_status_alle_60_s(tmp_path):
    a, h = await aufbau(tmp_path, 3)
    a.klient.gesendet.clear()
    for _ in range(10):
        tick(a, 60)
    assert gespielt(a) == [] and len(h.zeilen()) == 3
    stati = a.klient.json_auf(STATUS)
    assert len(stati) >= 10 and all(s["gehoert_wartet"] is True for s in stati)  # alle 60 s neu, auch ohne Änderung
    # neue Sitzungen während des Wartens: weiterhin nichts, auch kein Zwischenstand
    h.abspielen()
    h.spiele(1200)
    tick(a, 1)
    assert gespielt(a) == []
    await a.stop()


async def test_ohne_antwort_gibt_es_den_status_nicht_oefter_als_alle_5_s_und_alle_60_s_bei_wartender_box(tmp_path):
    a, _ = await aufbau(tmp_path, 1)
    n = len(a.klient.json_auf(STATUS))
    tick(a, GEHOERT_STATUS_WARTEN_S - 1)
    assert len(a.klient.json_auf(STATUS)) == n
    tick(a, 1)
    assert len(a.klient.json_auf(STATUS)) == n + 1
    await a.stop()


async def test_ha_neustart_neuer_handshake_und_unquittiertes_wird_noch_einmal_gesendet(tmp_path):
    a, h = await aufbau(tmp_path, 3)
    erste = [r["sitzung"] for r in h.zeilen()]
    await handshake(a)
    assert ids(gespielt(a)) == erste
    await quittung(a, erste[:1])
    # Home Assistant startet neu (Will/Birth ``online``): die Box wartet wieder und sendet nichts
    a.klient.eingang(HA_STATUS, b"online")
    await a.ha.leere()
    assert status(a)["gehoert_wartet"] is True  # sofort, nicht erst nach 5 s
    n = len(gespielt(a))
    tick(a, 5)
    tick(a, 700)
    assert len(gespielt(a)) == n
    await handshake(a, erste[:1])  # die neue HA kennt die eine schon und quittiert sie noch einmal
    zweite = gespielt(a)[n:]
    assert ids(zweite) == erste[1:]  # nur der Rest
    assert status(a)["gehoert_wartet"] is False
    await a.stop()


async def test_ha_status_offline_wird_ignoriert(tmp_path):
    a, _ = await aufbau(tmp_path)
    await handshake(a)
    a.klient.eingang(HA_STATUS, b"offline")
    await a.ha.leere()
    tick(a, 5)
    assert status(a)["gehoert_wartet"] is False
    await a.stop()


async def test_verbindung_weg_und_wieder_da_beginnt_den_handshake_von_vorn(tmp_path):
    a, h = await aufbau(tmp_path)
    await handshake(a)
    n = len(gespielt(a))
    a.klient.trenne()
    await a.ha.leere()
    eine_folge(h)  # offline: die Zeile wartet im Puffer
    tick(a, 5)
    assert len(gespielt(a)) == n
    await a.verbinde()
    assert status(a)["gehoert_wartet"] is True
    tick(a, 700)
    assert len(gespielt(a)) == n  # nichts vor der Quittung
    await handshake(a)
    assert len(ids(gespielt(a)[n:])) == 4
    await a.stop()


async def test_quittung_mit_nicht_leerer_liste_beendet_den_handshake_auch(tmp_path):
    a, h = await aufbau(tmp_path, 3)
    erste = [r["sitzung"] for r in h.zeilen()]
    await handshake(a, erste[:2])
    assert ids(gespielt(a)) == erste[2:]
    await a.stop()


# --- Senden (4.5, Punkt 2) ----------------------------------------------------------------------------


async def test_bei_jedem_sitzungsende_alle_zeilen_danach_alle_10_minuten(tmp_path):
    a, h = await aufbau(tmp_path, 2)
    await handshake(a)
    assert len(gespielt(a)) == 1
    eine_folge(h)  # Sitzungsende: alle Zeilen, auch die zwei schon gesendeten
    tick(a, 1)
    assert [len(n["daten"]["sitzungen"]) for n in gespielt(a)] == [2, 3]
    tick(a, 599)
    assert len(gespielt(a)) == 2
    tick(a, 2)  # 10 Minuten seit dem letzten Senden: solange Zeilen da sind
    assert [len(n["daten"]["sitzungen"]) for n in gespielt(a)] == [2, 3, 3]
    await a.stop()


async def test_doppelzustellung_dieselben_zeilen_kommen_wieder_bis_zur_quittung(tmp_path):
    a, h = await aufbau(tmp_path, 2)
    await handshake(a)
    erste = ids(gespielt(a))
    tick(a, 601)
    assert ids(gespielt(a)) == erste + erste  # dieselben UUIDs, HA dedupliziert über (Quelle, Sitzung)
    assert len({n["id"] for n in gespielt(a)}) == 2  # je Nachricht ist die Hüllen-``id`` neu
    await quittung(a, erste[:1])
    await quittung(a, erste[:1])  # doppelte Quittung: idempotent
    assert [r["sitzung"] for r in h.zeilen()] == erste[1:]
    tick(a, 601)
    assert ids(gespielt(a)[2:]) == erste[1:]
    await a.stop()


async def test_ohne_verbindung_wird_nichts_gesendet_und_nichts_verloren(tmp_path):
    a, h = await aufbau(tmp_path, 2, verbunden=False)
    tick(a, 5)
    assert a.klient.gesendet == [] and len(h.zeilen()) == 2
    await a.verbinde()
    await handshake(a)
    assert len(ids(gespielt(a))) == 2
    await a.stop()


async def test_hoechstens_20_sitzungen_je_nachricht_und_20_nachrichten_je_sekunde(tmp_path):
    a, h = await aufbau(tmp_path, 0)
    vorlage = {
        "sitzung": "", "serie": "s", "folge": "f.mp3", "beginn": "2026-11-16T18:10:57Z", "zeit_ok": True, "boot_id": "b",
        "beginn_boot_s": 100, "ende_boot_s": 200, "gehoert_s": 100, "ende": "pause",
    }
    h.p.z = replace(h.p.z, zeilen=tuple({**vorlage, "sitzung": uuid_nr(i)} for i in range(1, 501)))
    assert all(g.pruefe_zeile(r) == r for r in h.p.z.zeilen)
    await handshake(a)
    erste = gespielt(a)
    assert len(erste) == 20 and all(len(n["daten"]["sitzungen"]) == 20 for n in erste)  # 400 in der ersten Sekunde
    tick(a, 1)
    assert len(gespielt(a)) == 25 and len(gespielt(a)[-1]["daten"]["sitzungen"]) == 20
    assert sorted(ids(gespielt(a))) == sorted(r["sitzung"] for r in h.zeilen())
    tick(a, 1)
    assert len(gespielt(a)) == 25
    await a.stop()


async def test_zeilen_die_waehrend_des_sendens_quittiert_werden_gehen_nicht_mehr_hinaus(tmp_path):
    a, h = await aufbau(tmp_path, 0)
    vorlage = {
        "sitzung": "", "serie": "s", "folge": "f.mp3", "beginn": "2026-11-16T18:10:57Z", "zeit_ok": True, "boot_id": "b",
        "beginn_boot_s": 100, "ende_boot_s": 200, "gehoert_s": 100, "ende": "pause",
    }
    h.p.z = replace(h.p.z, zeilen=tuple({**vorlage, "sitzung": uuid_nr(i)} for i in range(1, 501)))
    await handshake(a)
    await quittung(a, [uuid_nr(i) for i in range(401, 501)])  # die noch nicht gesendeten 100
    tick(a, 1)
    assert sorted(ids(gespielt(a))) == [uuid_nr(i) for i in range(1, 401)]
    await a.stop()


# --- Zwischenstand (4.5, Punkt 3) ----------------------------------------------------------------------


async def test_zwischenstand_nur_nach_dem_handshake_nur_mqtt_und_ohne_quittung(tmp_path):
    a, h = await aufbau(tmp_path, 0)
    h.abspielen()
    h.spiele(1000)
    tick(a, 1)
    assert gespielt(a) == []  # die Box wartet noch
    await handshake(a)
    (n,) = gespielt(a)
    (s,) = n["daten"]["sitzungen"]
    assert s["ende"] == "teilweise" and s["sitzung"] == h.p.z.offen.sitzung
    assert h.zeilen() == [] and h.inhalt()["zeilen"] == []  # nie im Puffer
    tick(a, 100)
    assert len(gespielt(a)) == 1
    h.spiele(900)
    tick(a, 1)
    assert len(gespielt(a)) == 2 and gespielt(a)[1]["daten"]["sitzungen"][0]["sitzung"] == s["sitzung"]
    h.folge_zu_ende()  # der Abschluss trägt dieselbe UUID und kommt als Zeile
    tick(a, 1)
    letzte = gespielt(a)[-1]["daten"]["sitzungen"]
    assert [r["sitzung"] for r in letzte] == [s["sitzung"]] and letzte[0]["ende"] == "ende_der_folge"
    await a.stop()


# --- Quittung als Befehl (3.7) --------------------------------------------------------------------------


async def test_quittung_prueft_weder_ablauf_noch_zeit_ok_und_ist_idempotent(tmp_path):
    a, h = await aufbau(tmp_path, 3)
    erste = [r["sitzung"] for r in h.zeilen()]
    a.uhr.setze_zeit("unbekannt", False)  # die Uhr ist unsicher
    await quittung(a, erste[:1], erzeugt="2020-01-01T00:00:00Z", ttl_s=1, id="immer-dieselbe")  # längst abgelaufen
    assert [r["sitzung"] for r in h.zeilen()] == erste[1:]
    await quittung(a, erste[1:2], erzeugt="2020-01-01T00:00:00Z", ttl_s=1, id="immer-dieselbe")  # gleiche ``id`` zählt nicht als doppelt
    assert [r["sitzung"] for r in h.zeilen()] == erste[2:]
    assert [e for e in a.klient.json_auf(EVENT) if e["art"] in ("befehl_abgelehnt", "fehler")] == []  # nie ``befehl_abgelehnt``
    assert list(a.ha._befehl_ids) == []  # nicht in den 50 gemerkten ``id``s
    await a.stop()


async def test_ungueltige_quittung_wird_ignoriert_ohne_meldung_und_ohne_handshake(tmp_path):
    a, h = await aufbau(tmp_path, 2)
    for daten in ({}, {"sitzungen": "x"}, {"sitzungen": [1, 2]}, {"sitzungen": ["a"] * 101}, None):
        a.klient.eingang(CMD, cmd("gehoert_quittung", daten=daten))
        await a.ha.leere()
    tick(a, 5)
    assert status(a)["gehoert_wartet"] is True and len(h.zeilen()) == 2
    assert [e for e in a.klient.json_auf(EVENT) if e["art"] != "gespielt"] == []
    await a.stop()


async def test_quittung_loescht_nur_genau_die_uuids(tmp_path):
    a, h = await aufbau(tmp_path, 3)
    erste = [r["sitzung"] for r in h.zeilen()]
    await quittung(a, [erste[1], uuid_nr(777), "keine-uuid"])
    assert [r["sitzung"] for r in h.zeilen()] == [erste[0], erste[2]]
    await a.stop()


async def test_befehle_wie_lernen_gehen_weiter_ihren_weg(tmp_path):
    a, _ = await aufbau(tmp_path, 1)
    a.klient.eingang(CMD, cmd("lernen", id="abc"))
    await a.ha.leere()
    assert list(a.ha._befehl_ids) == ["abc"]
    await a.stop()


async def test_quittung_vor_dem_status_mit_true_loest_das_senden_nicht_aus(tmp_path):
    a, h = await aufbau(tmp_path, 2)
    await handshake(a)
    n = len(gespielt(a))
    a.klient.ist_verbunden = False  # der Status nach ``homeassistant/status online`` geht verloren
    a.klient.eingang(HA_STATUS, b"online")
    await a.ha.leere()
    assert a.ha._gehoert_gemeldet is None  # ``true`` ist nie veröffentlicht worden
    await quittung(a, [])  # eine nachgereichte Quittung (z. B. auf den alten Status): beendet den Handshake nicht
    assert a.ha._gehoert_wartet is True
    a.klient.ist_verbunden = True
    tick(a, STATUS_MIN_ABSTAND_S)
    assert status(a)["gehoert_wartet"] is True and len(gespielt(a)) == n  # jetzt steht ``true`` im Status, noch wird nichts gesendet
    await handshake(a)
    assert status(a)["gehoert_wartet"] is False and len(gespielt(a)) == n + 1
    await a.stop()


@pytest.mark.parametrize("folge", [ANDERE])
async def test_sitzung_mit_unbekannter_dauer_hat_kein_dauerfeld_in_der_nachricht(tmp_path, folge):
    a, h = await aufbau(tmp_path, 0)
    eine_folge(h, 20, folge)
    await handshake(a)
    (s,) = gespielt(a)[0]["daten"]["sitzungen"]
    assert "folge_dauer_s" not in s
    await a.stop()
