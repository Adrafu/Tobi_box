"""Stufe 4 (AP 4.8): ``tobibox gui`` und ``tobibox sim`` gegen den echten Dienst mit echtem MPD.

Der Ring ist in der Anzeige sichtbar, der Hauptknopf (lang) fährt die Box herunter (am Mac nur protokolliert), der Kopfhörer senkt die
Lautstärke, Tasten und Drehregler wirken, ``tobibox sim key|knob|headphones|time`` gehen über ``sim.sock``.
"""

from __future__ import annotations

from integration.test_app_e2e import mpd_status, warte
from integration.test_gui import (  # noqa: F401  (Fixtures)
    _kopfhoerer,
    _laut,
    _pausiert,
    anzeige,
    befehl,
    gui,
)
from integration.test_sim_cli import (  # noqa: F401  (Fixtures)
    SERIE,
    UID,
    lauf,
    log_zeilen,
    sim,
    spielt_aus,
    welt,
)


async def ring(srv) -> dict:
    return (await anzeige(srv))["anzeige"]["ring"]


async def _ring_ist(srv, zustand: str) -> bool:
    r = await ring(srv)
    return r is not None and r["zustand"] == zustand


async def test_der_ring_ist_in_der_anzeige_sichtbar_und_folgt_dem_zustand(gui):
    srv, welt_, fr = gui
    port = welt_["mpd"].port
    r = await ring(srv)
    assert r is not None and len(r["farben"]) == 40 and r["deckel"] == 25
    assert all(len(f) == 3 for f in r["farben"])
    fr.place(UID)  # der Tobie liegt auf dem (Fake-)Leser; ein simulierter widerspräche dem Herzschlag des Lesers
    await warte(lambda: spielt_aus(port, "rabe", "folge-01.wav"), 10.0, "(Serie spielt)")
    await warte(lambda: _ring_ist(srv, "laeuft"), 10.0, "(Ring: läuft, nach dem Lauflicht)")  # Aufwachen dauert 2 s
    r = await ring(srv)
    assert 0 < r["helligkeit"] <= 25 and r["farben"][0] == [0, 255, 70]  # Grün, nie heller als der Deckel
    await warte(lambda: "laeuft" in [z["ergebnis"] for z in log_zeilen(welt_, "ring")], 5.0, "(Protokoll: läuft)")
    await befehl(srv, befehl="taste", taste="hauptknopf_kurz")
    await warte(lambda: _pausiert(port), 10.0, "(Pause)")
    await warte(lambda: _ring_ist(srv, "pause"), 5.0, "(Ring: Pause)")
    # dieselben Zustände im Protokoll, nur bei Wechsel
    await warte(lambda: [z["ergebnis"] for z in log_zeilen(welt_, "ring")][-1:] == ["pause"], 5.0, "(Protokoll: pause)")
    zustaende = [z["ergebnis"] for z in log_zeilen(welt_, "ring")]
    assert "laeuft" in zustaende and zustaende[-1] == "pause"
    assert all(a != b for a, b in zip(zustaende, zustaende[1:]))


async def test_kopfhoerer_senkt_die_lautstaerke_und_ziehen_stellt_sie_wieder_her(gui):
    srv, welt_, fr = gui
    port = welt_["mpd"].port
    fr.place(UID)
    await warte(lambda: spielt_aus(port, "rabe", "folge-01.wav"), 10.0, "(spielt)")
    assert (await befehl(srv, befehl="regler", delta=20))["ok"]  # 20 -> 40, Grenze 50
    await warte(lambda: _laut(srv, 40), 5.0, "(Lautstärke 40)")
    assert int((await mpd_status(port))["volume"]) == 40

    assert (await befehl(srv, befehl="kopfhoerer", steckt=True))["ok"]
    await warte(lambda: _kopfhoerer(srv, True), 5.0, "(Kopfhörer steckt)")
    await warte(lambda: _laut(srv, 30), 5.0, "(Lautstärke auf die Kopfhörer-Grenze gesenkt)")
    assert int((await mpd_status(port))["volume"]) == 30
    assert (await anzeige(srv))["anzeige"]["grenze"] == 30

    assert (await befehl(srv, befehl="kopfhoerer", steckt=False))["ok"]
    await warte(lambda: _laut(srv, 40), 5.0, "(Lautstärke wieder 40)")
    assert int((await mpd_status(port))["volume"]) == 40


async def test_hauptknopf_lang_faehrt_herunter_nur_protokolliert(gui):
    srv, welt_, fr = gui
    port = welt_["mpd"].port
    fr.place(UID)
    await warte(lambda: spielt_aus(port, "rabe", "folge-01.wav"), 10.0, "(spielt)")
    a = await befehl(srv, befehl="taste", taste="hauptknopf_lang")
    assert a == {"ok": True}
    await warte(lambda: _pausiert(port), 10.0, "(Pause vor dem Herunterfahren)")
    await warte(lambda: _strom_ist(srv, "herunterfahren"), 5.0, "(Strom: herunterfahren)")
    await warte(lambda: _ring_ist(srv, "aus"), 5.0, "(Ring aus)")
    zeilen = [z for z in log_zeilen(welt_, "herunterfahren") if z["baustein"] == "app"]
    assert len(zeilen) == 1 and "hauptknopf" in str(zeilen[0])
    # am Mac nur protokolliert: der Dienst läuft weiter und antwortet
    assert (await anzeige(srv))["dienst"] == "laeuft"


async def _strom_ist(srv, strom: str) -> bool:
    return (await anzeige(srv))["anzeige"]["strom"] == strom


async def test_sim_key_knob_headphones_und_time_ueber_den_socket(lauf):
    welt_, fr = lauf
    port = welt_["mpd"].port
    code, _, err = await sim(welt_, "headphones", "on")
    assert code == 0, err
    code, _, err = await sim(welt_, "knob", "-3")
    assert code == 0, err
    code, antwort, err = await sim(welt_, "time", "2026-11-09T22:30:00+01:00")
    assert code == 0 and antwort["ok"] and antwort["wall"] > 1.7e9, err
    code, _, err = await sim(welt_, "time", "now")
    assert code == 0, err
    code, _, err = await sim(welt_, "key", "vor")
    assert code == 0, err
    code, _, err = await sim(welt_, "headphones", "off")
    assert code == 0, err
    # ein Tobie liegt auf dem Fake-Leser; haupt pausiert und spielt wieder
    fr.place(UID)
    await warte(lambda: spielt_aus(port, "rabe"), 10.0, "(spielt)")
    code, _, err = await sim(welt_, "key", "haupt")
    assert code == 0, err
    await warte(lambda: _pausiert(port), 10.0, "(haupt pausiert)")
    code, _, err = await sim(welt_, "key", "haupt")
    await warte(lambda: spielt_aus(port, "rabe"), 10.0, "(haupt spielt)")
    code, _, err = await sim(welt_, "key", "haupt-lang")
    assert code == 0, err
    await warte(lambda: _pausiert(port), 10.0, "(haupt-lang pausiert und fährt herunter)")
    assert log_zeilen(welt_, "herunterfahren")


async def test_sim_time_und_knob_lehnen_unsinn_ab(lauf):
    welt_, _ = lauf
    code, _, err = await sim(welt_, "time", "morgen")
    assert code == 2 and "ISO 8601" in err
    code, _, err = await sim(welt_, "knob", "+99")
    assert code == 2
    code, _, err = await sim(welt_, "knob", "0")
    assert code == 2
