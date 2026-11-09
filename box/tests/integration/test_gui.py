"""Simulations-Oberfläche (AP 4.9) gegen den echten Dienst: GUI-Server in diesem Prozess, Dienst mit ``fake_reader`` und echtem MPD.

Ein Klick auf „auflegen“ geht als ``POST /api/befehl`` an den Server, von dort über ``sim.sock`` an den Dienst und
startet die Wiedergabe im MPD. Der echte (Fake-)Leser läuft parallel.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from integration.test_app_e2e import mpd_status, warte
from integration.test_sim_cli import (  # noqa: F401  (Fixtures)
    KARTE,
    NEU,
    SERIE,
    UID,
    aktuelle_datei,
    lauf,
    spielt_aus,
    unknown,
    welt,
)
from tobibox import config as konfig_modul
from tobibox.gui import server


@pytest.fixture
async def gui(lauf):  # noqa: F811
    welt_, fr = lauf
    kfg = konfig_modul.lade(welt_["toml"])
    ober = server.Oberflaeche(
        server.unix_frage(kfg.pfade.zustand / "sim.sock"), kfg.pfade.zustand, kfg.pfade.medien, kfg.protokoll.datei
    )
    srv = server.Server(ober, "127.0.0.1", 0)
    await srv.start()
    yield srv, welt_, fr
    await srv.stop()


async def http(srv, methode, pfad, koerper=None):
    r, w = await asyncio.open_connection("127.0.0.1", srv.port)
    daten = b"" if koerper is None else json.dumps(koerper).encode()
    kopf = f"{methode} {pfad} HTTP/1.1\r\nHost: 127.0.0.1:{srv.port}\r\n"
    if koerper is not None:
        kopf += f"Content-Type: application/json\r\nContent-Length: {len(daten)}\r\n"
    w.write(kopf.encode() + b"\r\n" + daten)
    await w.drain()
    roh = await asyncio.wait_for(r.read(), 10)
    w.close()
    return json.loads(roh.partition(b"\r\n\r\n")[2])


async def anzeige(srv) -> dict:
    return await http(srv, "GET", "/api/anzeige")


async def befehl(srv, **zeile) -> dict:
    return await http(srv, "POST", "/api/befehl", zeile)


async def test_auflegen_ueber_die_api_startet_die_wiedergabe_und_abheben_pausiert(gui):
    srv, welt_, _ = gui
    port = welt_["mpd"].port
    d = await anzeige(srv)
    assert d["dienst"] == "laeuft" and d["anzeige"]["ring"] is None
    assert {t["uid"] for t in d["tobies"]} == {UID} and SERIE in {s["id"] for s in d["serien"]}

    a = await befehl(srv, befehl="tobie_auflegen", uid=UID)
    assert a["ok"] and a["uid"] == UID
    await warte(lambda: spielt_aus(port, "rabe", "folge-01.wav"), 10.0, "(Serie spielt)")

    d = await anzeige(srv)
    assert d["status"]["zustand"] == "spielt" and d["status"]["serie"]["id"] == SERIE
    assert d["anzeige"]["figur"] == {"uid": UID, "vorgang": a["vorgang"], "art": "serie"}
    assert d["simuliert"] == {"uid": UID, "vorgang": a["vorgang"]}  # simuliert, nicht echt
    assert d["anzeige"]["lautstaerke"] is not None and d["anzeige"]["grenze"] == 50

    assert (await befehl(srv, befehl="tobie_abheben"))["ok"]
    await warte(lambda: _pausiert(port), 10.0, "(Pause nach Abheben)")
    d = await anzeige(srv)
    assert d["anzeige"]["figur"] is None and d["simuliert"] is None


async def _pausiert(port: int) -> bool:
    return (await mpd_status(port))["state"] == "pause"


async def test_echter_leser_laeuft_parallel_und_gilt_als_echt(gui):
    srv, welt_, fr = gui
    port = welt_["mpd"].port
    fr.place(UID)
    await warte(lambda: spielt_aus(port, "rabe"), 10.0, "(echter Tobie spielt)")
    d = await anzeige(srv)
    assert d["anzeige"]["figur"]["uid"] == UID and d["simuliert"] is None  # liegt echt

    a = await befehl(srv, befehl="tobie_auflegen", uid=UID)  # derselbe Tobie, aber neuer Vorgang: Wechsel
    assert a["ok"]
    d = await anzeige(srv)
    assert d["simuliert"] is not None
    await warte(lambda: _vorgang_ist(srv, a["vorgang"]), 5.0, "(simulierter Vorgang liegt)")
    assert (await befehl(srv, befehl="tobie_abheben"))["ok"]
    await warte(lambda: _pausiert(port), 10.0, "(Pause)")


async def _vorgang_ist(srv, vorgang) -> bool:
    f = (await anzeige(srv))["anzeige"]["figur"]
    return f is not None and f["vorgang"] == vorgang


async def test_tasten_regler_und_kopfhoerer(gui):
    srv, welt_, _ = gui
    port = welt_["mpd"].port
    await befehl(srv, befehl="tobie_auflegen", uid=UID)
    await warte(lambda: spielt_aus(port, "rabe", "folge-01.wav"), 10.0, "(spielt)")

    assert (await befehl(srv, befehl="taste", taste="hauptknopf_kurz"))["ok"]
    await warte(lambda: _pausiert(port), 10.0, "(Hauptknopf kurz pausiert)")
    assert (await befehl(srv, befehl="taste", taste="hauptknopf_kurz"))["ok"]
    await warte(lambda: spielt_aus(port, "rabe", "folge-01.wav"), 10.0, "(Hauptknopf kurz spielt)")

    vorher = (await anzeige(srv))["anzeige"]["lautstaerke"]
    assert (await befehl(srv, befehl="regler", delta=-2))["ok"]
    await warte(lambda: _laut(srv, vorher - 2), 5.0, "(zwei Prozent leiser)")

    assert (await befehl(srv, befehl="kopfhoerer", steckt=True))["ok"]
    await warte(lambda: _kopfhoerer(srv, True), 5.0, "(Kopfhörer steckt)")
    d = await anzeige(srv)
    assert d["anzeige"]["grenze"] == 30  # [lautstaerke] kopfhoerer = 30
    assert (await befehl(srv, befehl="kopfhoerer", steckt=False))["ok"]
    await warte(lambda: _kopfhoerer(srv, False), 5.0, "(Kopfhörer raus)")

    assert (await befehl(srv, befehl="taste", taste="weiter"))["ok"]
    await warte(lambda: spielt_aus(port, "rabe", "folge-02.wav"), 10.0, "(Vor springt zur nächsten Folge)")


async def _status_ist(srv, **felder) -> bool:
    st = (await anzeige(srv))["status"]
    return all(st[k] == v for k, v in felder.items())


async def _laut(srv, wert) -> bool:
    return (await anzeige(srv))["anzeige"]["lautstaerke"] == wert


async def _kopfhoerer(srv, steckt) -> bool:
    return (await anzeige(srv))["anzeige"]["kopfhoerer"] is steckt


async def test_noch_nicht_verdrahtete_eingaenge_antworten_klar(gui):
    srv, _, _ = gui
    nv = {"ok": False, "fehler": "noch_nicht_verdrahtet"}
    assert await befehl(srv, befehl="taste", taste="hauptknopf_lang") == nv
    d = (await anzeige(srv))["verdrahtet"]
    assert d["netz"] is True and d["strom"] is True and d["hauptknopf_lang"] is False  # strom und netz seit AP 3.7


async def test_strom_und_netz_wirken_auch_ohne_netz_und_strom_abschnitt(gui):
    """Die Test-Konfiguration hat kein ``[netz]`` und kein ``[strom]``: ``sim`` gibt die Ereignisse selbst aus."""
    srv, _, _ = gui
    assert (await befehl(srv, befehl="strom", lader=True, akku=61))["ok"]
    assert (await befehl(srv, befehl="netz", klasse="hotspot"))["ok"]
    await warte(lambda: _status_ist(srv, akku_prozent=61, lader=True, netz="hotspot"), 5.0, "(Status zeigt Akku und Netz)")


async def test_unbekannter_tobie_wird_gemeldet_und_ueber_die_api_bestaetigt(gui):
    srv, welt_, _ = gui
    port = welt_["mpd"].port
    a = await befehl(srv, befehl="tobie_auflegen", zufall=True)
    assert a["ok"]
    await warte(lambda: spielt_aus(port, "ueberraschung"), 10.0, "(Überraschung spielt)")
    await warte(lambda: a["uid"] in unknown(welt_), 5.0, "(Eintrag in unknown.json)")
    d = await anzeige(srv)
    (m,) = [m for m in d["offen"] if m["uid"] == a["uid"]]
    assert (await befehl(srv, befehl="ack", uid=m["uid"], zuletzt=m["zuletzt"], art=m["art"]))["ok"]
    await warte(lambda: a["uid"] not in unknown(welt_), 5.0, "(Eintrag gelöscht)")
    g = await befehl(srv, befehl="tobie_gesperrt")
    assert g["ok"]
    await warte(lambda: _vorgang_ist(srv, g["vorgang"]), 5.0, "(Gesperrter liegt)")


async def test_lernmodus_ueber_die_api(gui):
    srv, _, _ = gui
    assert (await befehl(srv, befehl="learn", typ="serie", serie=SERIE, ttl=60))["ok"]
    await warte(lambda: _lernmodus(srv, True), 5.0, "(Lernmodus an)")
    assert (await befehl(srv, befehl="learn_abort"))["ok"]
    await warte(lambda: _lernmodus(srv, False), 5.0, "(Lernmodus aus)")


async def _lernmodus(srv, an) -> bool:
    return (await anzeige(srv))["status"]["lernmodus"] is an
