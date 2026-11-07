"""CUJ 7b gegen die echte ``App`` (Befund 11): Lernmodus mit ``sim`` und HA-Ersatz, ohne Nachbau der Verdrahtung.

``test_cuj07b_lernmodus.py`` prüft die Fälle mit ``SimBox`` (dieselbe Klasse ``Ausgang`` wie der Dienst); hier
läuft der Dienst selbst: echte Ereignisschleife, echter Ausführer, echte Dateien, simulierte Uhr, ohne MPD und
ohne Leser. Geprüft werden die Fälle, in denen die Verdrahtung zählt: Frist, Abbruch, zweiter Befehl,
Wiedermeldung, bestehende Zuordnung, ``sim=true`` im Protokoll.

Entscheidung H (07.11.): Zwischen Auflegen und Zuordnung spielt die Box nichts (keine Überraschung, kein Ton
``unbekannt``). „Abgelehnt“ erreicht den Kern über die echte Verdrahtung (``App.verarbeite``).
"""

from __future__ import annotations

import json

import pytest
from fixtures.audio import erzeuge_medien
from unit.test_app import FakeLeser, FakePlayer, FakeToene

from tobibox import app as app_modul
from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox.app import App
from tobibox.clock import SimUhr
from tobibox.learn import LERN_FRIST_S
from tobibox.session import LERN_ANTWORT_FRIST_S

SERIE = "3f9a1c07b2d4"
BAER = "8c21d5e9a0b7"
UEBERRASCHUNG = "c07d2e91a45b"
NEU = "04ffeedd"
BEKANNT = "04a1b2c3"


class PlayerOhneMpd(FakePlayer):
    async def abspielen(self, b):
        self.aufrufe.append(f"abspielen {b.serie_id}")

    async def pausieren(self, b):
        self.aufrufe.append("pausieren")

    async def ausgang_waehlen(self, a):
        pass


class Dienst:
    def __init__(self, a: App, uhr: SimUhr, zustand) -> None:
        self.app, self.uhr, self.zustand = a, uhr, zustand

    async def sende(self, *ereignisse) -> None:
        for e in ereignisse:
            self.app.ereignisse.put_nowait(e)
        for _ in range(3):  # Ereignis -> Befehl -> Ereignis des HA-Ersatzes -> Befehl
            await self.app._leere_ereignisse()
            await self.app.befehle.join()
        await self.app.outbox.warte_gespeichert()

    async def sim(self, **zeile) -> None:
        e = await self.app.sim.zeile_zu_ereignis_async(json.dumps(zeile))
        self.app.sim.ausgabe(e)  # wie ein Client von ``sim.sock``
        await self.sende()

    async def ha_schweigt(self) -> None:
        """Der HA-Ersatz antwortet nicht (Test des Wartens)."""

        async def nichts(eintrag):
            pass

        self.app.ausgang.ha_ersatz.gelernt_async = nichts

    def abgelehnt(self, uid: str) -> ev.Bestaetigt:
        return ev.Bestaetigt(uid, "abgelehnt", self.unknown()[uid]["zuletzt"], "gelernt")

    def lerne(self, **kw):
        return self.sim(befehl="learn", typ="serie", serie=SERIE, ttl=60, **kw)

    def konfig(self) -> dict:
        return json.loads((self.zustand / "config.json").read_text())

    def unknown(self) -> dict:
        p = self.zustand / "unknown.json"
        return json.loads(p.read_text())["eintraege"] if p.exists() else {}

    @property
    def lernt(self) -> bool:
        return self.app.kern.teil["learn"].modus == "lernt"

    def melden(self, uid: str, vorgang: str) -> ev.Aufgelegt:
        return ev.Aufgelegt(uid, "ntag", False, 0, vorgang)


@pytest.fixture
async def dienst(tmp_path, monkeypatch, protokoll):
    from tobibox import store

    medien = erzeuge_medien(tmp_path / "medien")
    zustand = tmp_path / "var"
    zustand.mkdir()
    k = ev.Konfig(1, "a3f9c1e07b2d4856", {BEKANNT: ev.Zuordnung("serie", BAER)}, ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60))
    store.schreibe_atomar(zustand / "config.json", store.konfig_zu_json(k))
    toml = tmp_path / "tobibox.toml"
    toml.write_text(f'[pfade]\nzustand = "{zustand}"\nmedien = "{medien}"\n[leser]\ngeraet = "sim"\n', encoding="utf-8")
    monkeypatch.setattr(app_modul.notify, "stoppt", lambda: None)
    uhr = SimUhr()
    a = App(konfig_modul.lade(toml), uhr=uhr, melde_bereit=False)
    a.player = PlayerOhneMpd()
    a.player.app = a
    a.leser = FakeLeser()
    a.toene = FakeToene()
    a.toene.gespielt = []
    a.toene.spiele = lambda ton, *args, **kw: a.toene.gespielt.append(ton) or True
    a.gesehen = []
    await a.starte()
    a.toene.gespielt.clear()  # ohne den Startton
    yield Dienst(a, uhr, zustand)
    await a.beende()


async def test_lernen_ordnet_zu_bestaetigt_und_spielt_das_ziel(dienst):
    await dienst.lerne()
    assert dienst.lernt
    await dienst.sende(dienst.melden(NEU, "v1"))
    assert not dienst.lernt
    assert dienst.konfig()["revision"] == 2
    assert dienst.konfig()["zuordnungen"][NEU]["ziel"] == {"typ": "serie", "serie": SERIE}
    assert dienst.unknown() == {}
    assert dienst.app.kern.session.figur.art == "serie" and f"abspielen {SERIE}" in dienst.app.player.aufrufe
    # Entscheidung H: nie die Überraschung und nie der Ton ``unbekannt`` dazwischen, nur der Lernton
    assert not any(a.startswith("abspielen") and a != f"abspielen {SERIE}" for a in dienst.app.player.aufrufe)
    assert dienst.app.toene.gespielt == ["lernen_beginn", "lernen_ende"]


async def test_wartet_still_bis_die_zuordnung_kommt(dienst):
    await dienst.ha_schweigt()
    await dienst.lerne()
    await dienst.sende(dienst.melden(NEU, "v1"))
    assert dienst.app.kern.session.lern_wartet_bis is not None
    assert not [a for a in dienst.app.player.aufrufe if a.startswith("abspielen")]
    assert dienst.app.toene.gespielt == ["lernen_beginn", "lernen_ende"]
    # die Zuordnung trifft ein (wie von HA): das Ziel startet sofort
    from tobibox.ha_ersatz import schreibe_zuordnung

    geladen = schreibe_zuordnung(dienst.app.konfig_store, NEU, {"typ": "serie", "serie": SERIE})
    await dienst.sende(geladen)
    assert f"abspielen {SERIE}" in dienst.app.player.aufrufe and dienst.app.kern.session.lern_wartet_bis is None
    assert "unbekannt" not in dienst.app.toene.gespielt


async def test_abgelehnt_aus_der_verdrahtung_beendet_das_warten_und_die_ueberraschung_spielt(dienst):
    await dienst.ha_schweigt()
    await dienst.lerne()
    await dienst.sende(dienst.melden(NEU, "v1"))
    assert not [a for a in dienst.app.player.aufrufe if a.startswith("abspielen")]
    await dienst.sende(dienst.abgelehnt(NEU))  # ``App.verarbeite`` reicht „gelernt“ an den Kern weiter
    assert dienst.app.kern.session.lern_wartet_bis is None
    assert f"abspielen {UEBERRASCHUNG}" in dienst.app.player.aufrufe
    assert dienst.app.toene.gespielt == ["lernen_beginn", "lernen_ende", "unbekannt"]
    assert dienst.unknown() == {}  # die Bestätigung hat auch die Outbox erreicht


async def test_keine_antwort_nach_10_s_wie_abgelehnt(dienst):
    await dienst.ha_schweigt()
    await dienst.lerne()
    await dienst.sende(dienst.melden(NEU, "v1"))
    dienst.uhr.vor(LERN_ANTWORT_FRIST_S - 1)
    await dienst.sende(ev.Takt())
    assert not [a for a in dienst.app.player.aufrufe if a.startswith("abspielen")]
    dienst.uhr.vor(2)
    await dienst.sende(ev.Takt())
    assert f"abspielen {UEBERRASCHUNG}" in dienst.app.player.aufrufe
    assert dienst.app.toene.gespielt[-1] == "unbekannt"
    assert dienst.unknown()[NEU]["art"] == "gelernt"  # bleibt offen, bis HA bestätigt


async def test_abheben_waehrend_des_wartens_und_tasten(dienst):
    await dienst.ha_schweigt()
    await dienst.lerne()
    await dienst.sende(dienst.melden(NEU, "v1"))
    await dienst.sende(ev.Hauptknopf("kurz"), ev.Weiter(), ev.Zurueck())
    assert not [a for a in dienst.app.player.aufrufe if a.startswith("abspielen")]
    await dienst.sende(ev.Abgehoben(1, "v1"))
    dienst.uhr.vor(LERN_ANTWORT_FRIST_S + 1)
    await dienst.sende(ev.Takt())
    assert not [a for a in dienst.app.player.aufrufe if a.startswith("abspielen")]
    assert dienst.app.kern.session.figur is None


async def test_zweiter_lernbefehl_wird_ignoriert_und_der_erste_lernlauf_gelingt(dienst):
    await dienst.lerne()
    await dienst.sim(befehl="learn", typ="serie", serie=BAER, ttl=60)  # die Box ignoriert ihn
    await dienst.sende(dienst.melden(NEU, "v1"))
    assert dienst.konfig()["zuordnungen"][NEU]["ziel"] == {"typ": "serie", "serie": SERIE}
    assert dienst.unknown() == {}


async def test_frist_zwei_minuten_der_naechste_tobie_ist_dann_unbekannt(dienst):
    await dienst.lerne()
    dienst.uhr.vor(LERN_FRIST_S + 1)
    await dienst.sende(ev.Takt())
    assert not dienst.lernt
    await dienst.sende(dienst.melden(NEU, "v1"))
    assert NEU not in dienst.konfig()["zuordnungen"]
    assert dienst.unknown()[NEU]["art"] == "unbekannt"  # wartet auf HA
    assert f"abspielen {UEBERRASCHUNG}" in dienst.app.player.aufrufe


async def test_abbruch_beendet_den_lernmodus(dienst):
    await dienst.lerne()
    await dienst.sim(befehl="learn_abort")
    assert not dienst.lernt
    await dienst.sende(dienst.melden(NEU, "v1"))
    assert NEU not in dienst.konfig()["zuordnungen"]


async def test_schon_zugeordneter_tobie_bleibt_ohne_ueberschreiben_wie_er_ist(dienst):
    await dienst.lerne()
    await dienst.sende(dienst.melden(BEKANNT, "v1"))
    assert dienst.konfig()["revision"] == 1
    assert dienst.konfig()["zuordnungen"][BEKANNT]["ziel"] == {"typ": "serie", "serie": BAER}
    assert dienst.unknown() == {}  # ``abgelehnt`` bestätigt und löscht


async def test_schon_zugeordneter_tobie_wird_mit_ueberschreiben_ersetzt(dienst):
    await dienst.lerne(ueberschreiben=True)
    await dienst.sende(dienst.melden(BEKANNT, "v1"))
    assert dienst.konfig()["zuordnungen"][BEKANNT]["ziel"] == {"typ": "serie", "serie": SERIE}


async def test_wiedermeldung_des_liegenden_tobies_beendet_den_lernmodus_nicht(dienst):
    await dienst.sende(dienst.melden(BEKANNT, "v1"))
    await dienst.lerne()
    await dienst.sende(dienst.melden(BEKANNT, "v1"))  # gleiche Vorgangs-ID: Wiedermeldung
    assert dienst.lernt and dienst.konfig()["revision"] == 1
    await dienst.sende(ev.Abgehoben(1, "v1"), dienst.melden(NEU, "v2"))
    assert dienst.konfig()["zuordnungen"][NEU]["ziel"] == {"typ": "serie", "serie": SERIE}


async def test_protokollzeilen_von_sim_tragen_sim_true_echte_nicht(dienst, protokoll):
    await dienst.lerne()
    await dienst.sende(dienst.melden(NEU, "v1"))
    von_sim = {z["ereignis"] for z in protokoll.zeilen() if z.get("sim")}
    assert {"lernen", "lernmodus_beginn", "zuordnung"} <= von_sim  # sim, Kern-Zeile zu einem Ereignis von sim, HA-Ersatz
    ohne = {z["ereignis"] for z in protokoll.zeilen() if not z.get("sim")}
    assert "aufgelegt" in ohne and "lernmodus_ende" in ohne  # der Tobie kam vom Leser, nicht von sim


async def test_bestaetigung_fuer_unbekannte_geht_nicht_an_den_kern(dienst):
    vorher = dienst.app.kern
    assert dienst.app.verarbeite(ev.Bestaetigt("04aaaaaa", "neu", "2026-11-07T00:00:00.000Z", "unbekannt")) == ()
    assert dienst.app.kern is vorher


async def test_bestaetigung_fuer_gelernte_geht_auch_an_den_kern(dienst):
    """Entscheidung H: ``art="gelernt"`` erreicht die Sitzung (sie beendet damit das Warten bei „abgelehnt“)."""
    vorher = dienst.app.kern
    dienst.app.verarbeite(ev.Bestaetigt("04aaaaaa", "abgelehnt", "2026-11-07T00:00:00.000Z", "gelernt"))
    assert dienst.app.kern is not vorher


async def test_leser_prueffpunkt_zeigt_simulation_ohne_leser_geraet(dienst):
    assert dienst.app.status.leser(0.0) == "simulation"
    assert dienst.app.status_auskunft()["status"]["leser"] == "simulation"
    punkt = dienst.app.pruefbericht(dienst.uhr.jetzt()).punkte[0]
    assert (punkt.name, punkt.ok) == ("leser", True)


async def test_201_ter_eintrag_bei_stehender_uhr_laesst_den_dienst_nicht_stolpern(dienst, protokoll):
    from dataclasses import replace

    spaeter = replace(dienst.uhr.jetzt(), wall=dienst.uhr.wall + 1e6)
    for i in range(200):
        dienst.app.outbox.melden("unbekannt", f"05{i:06x}", None, spaeter)
    await dienst.sende(dienst.melden(NEU, "v1"))  # unbekannt, die Uhr liegt hinter allen alten Einträgen
    assert NEU in dienst.unknown() and len(dienst.unknown()) == 200
    assert not protokoll.finde("befehl_fehler")
