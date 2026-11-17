"""``App`` und „Gehört“ (B1): Start (Abbruch), Herunterfahren und Dienst-Ende schreiben synchron, Status."""

from __future__ import annotations

import json

from fixtures.gehoert_harnisch import FOLGE, SERIE, uuid_nr
from test_app import app  # noqa: F401  (Fixture ``app``: ``App`` mit Fake-Player, ohne MPD)

from tobibox import events as ev


def sitzung_offen(a, sekunden: int = 30) -> None:
    """Eine Sitzung beginnen und ``sekunden`` lang hören, am Beobachter vorbei am Kern (der Fake-Player spielt nichts)."""
    a.gehoert.beobachte(ev.Takt(), [ev.Abspielen(SERIE, "ordner", FOLGE, (FOLGE,), 0, 0.0, None, 1)], a.uhr.jetzt())
    pos = 0.0
    for _ in range(sekunden):
        pos += 1.0
        a.uhr.mono += 1.0  # type: ignore[attr-defined]
        a.gehoert.beobachte(ev.PlayerPosition(SERIE, FOLGE, 0, pos, True, 1), [], a.uhr.jetzt())


def datei(a) -> dict:
    return json.loads((a.konfig.pfade.zustand / "gehoert.json").read_text())


def abgesetzt(a):
    """Die Uhr der App ist die Systemuhr: für den Test eine, die wir vorstellen können."""
    from tobibox.clock import SimUhr

    a.uhr = SimUhr(mono=9000.0, wall=1_790_000_000.0)
    return a


async def test_start_macht_aus_der_offenen_sitzung_die_zeile_abbruch(app):
    zustand = app.konfig.pfade.zustand
    zustand.mkdir(parents=True, exist_ok=True)
    offen = {
        "sitzung": uuid_nr(5), "serie": SERIE, "folge": FOLGE, "beginn": "2026-11-16T18:10:57Z", "zeit_ok": True,
        "boot_id": "alt", "beginn_boot_s": 100, "ende_boot_s": 400, "gehoert_s": 280, "ende": "teilweise",
    }
    (zustand / "gehoert.json").write_text(json.dumps({"schema_version": 1, "verworfen": 0, "offen": offen, "zeilen": []}))
    await app.starte()
    try:
        (z,) = app.gehoert.zeilen
        assert z["ende"] == "abbruch" and z["sitzung"] == uuid_nr(5) and z["gehoert_s"] == 280
        await app.gehoert.warte_gespeichert()
        assert datei(app)["offen"] is None and datei(app)["zeilen"][0]["ende"] == "abbruch"
    finally:
        await app.beende()


async def test_herunterfahren_schreibt_die_zeile_bevor_der_befehl_ausgefuehrt_wird(app):
    abgesetzt(app)
    await app.starte()
    try:
        sitzung_offen(app, 30)
        befehle = app.verarbeite(ev.HerunterfahrenAngefordert("hauptknopf"))
        assert any(isinstance(b, ev.Herunterfahren) for b in befehle)
        # ``verarbeite`` ist fertig, der Ausführer hat den Befehl noch nicht angerührt (kein ``await`` dazwischen)
        (z,) = datei(app)["zeilen"]
        assert z["ende"] == "herunterfahren" and z["gehoert_s"] == 29 and datei(app)["offen"] is None
    finally:
        await app.beende()


async def test_dienst_ende_schreibt_auch_bei_pausiertem_kern(app):
    abgesetzt(app)
    await app.starte()
    sitzung_offen(app, 30)  # der Kern selbst steht auf „leer“: ``DienstEndet`` käme dort nicht an
    await app.beende()
    (z,) = datei(app)["zeilen"]
    assert z["ende"] == "dienst_ende" and z["gehoert_s"] == 29


async def test_ohne_mqtt_gibt_es_keine_zusatzfelder_im_status_und_der_puffer_laeuft_trotzdem(app):
    await app.starte()
    try:
        assert app.ha is None
        assert "gehoert_wartet" not in app.status_auskunft()["status"]
        assert app.gehoert.verworfen == 0
    finally:
        await app.beende()


def test_dauer_der_folge_kommt_aus_der_bibliothek(app):
    from tobibox import library

    s = ev.Serie("s9", "S", "normal", "s9", ("a.mp3", "cd"), {"cd": ("cd/1.mp3", "cd/2.mp3")},
                 {"a.mp3": (100.4,), "cd": (10.0, 20.6)})
    app.bibliothek = library.Bibliothek((s,), "x")
    assert app._folge_dauer_s("s9", "a.mp3") == 100
    assert app._folge_dauer_s("s9", "cd") == 31
    assert app._folge_dauer_s("s9", "gibt-es-nicht") is None
    assert app._folge_dauer_s("andere", "a.mp3") is None
    app.bibliothek = library.Bibliothek((replace_dauer(s),), "x")
    assert app._folge_dauer_s("s9", "a.mp3") is None  # ein Track mit unbekannter Dauer


def replace_dauer(s):
    import dataclasses

    return dataclasses.replace(s, dauern={"a.mp3": (None,)})
