"""Früher Start-Ton in der echten ``App`` (Ein/Aus, 10.11.; AP E1-2, E1-7): Marke bei ``Bereit`` lesen, Gegenmarke, Wartereihenfolge.

Fälle der Doppel-Ton-Tabelle (Entwurf 6.3), soweit sie die ``App`` betreffen: Der Frühdienst spielt, der Kern spielt keinen zweiten ``start``;
läuft der Frühton noch, wartet jeder Ton des Kerns (nie zwei Töne); ist der Frühdienst zu spät, spielt er nicht mehr (V1); nach einem
Dienst-Neustart gilt die Marke nicht. Echte Ereignisschleife, echte ``Toene``-Spur mit gesteuertem Abspielprogramm.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from fixtures.audio import erzeuge_medien
from unit.test_app_toene import AufnahmePlayer, FakeLeser, TonSteuerung, nie_gleichzeitig

from tobibox import app as app_modul
from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox import fruehton, lauf, store
from tobibox.app import App
from tobibox.clock import SimUhr
from tobibox.sounds import Toene

BAER = "8c21d5e9a0b7"
BEKANNT = "04a1b2c3"
NEU = "04ffeedd"
BOOT = "boot-1"


class Welt:
    def __init__(self, a, journal, ton, zustand, marken):
        self.app, self.journal, self.ton, self.zustand, self.marken = a, journal, ton, zustand, marken

    async def warte(self, bedingung, text: str = "", timeout: float = 3.0) -> None:
        ende = time.monotonic() + timeout
        while time.monotonic() < ende:
            if bedingung():
                return
            await asyncio.sleep(0.01)
        raise AssertionError(f"nicht rechtzeitig: {text}\n{self.journal}")

    async def ruhe(self, s: float = 0.15) -> None:
        await asyncio.sleep(s)
        await self.app.befehle.join()

    def toene(self) -> list[str]:
        return [z.split(":")[1] for z in self.journal if z.startswith("ton:") and z.endswith(":start")]

    async def starte(self) -> None:
        await self.app.starte()
        await self.ruhe(0.1)


@pytest.fixture
def baue(tmp_path, monkeypatch, _marken_verzeichnis):
    """Baut die Welt, startet sie aber nicht: der Test legt vorher die Marke."""
    medien = erzeuge_medien(tmp_path / "medien")
    zustand = tmp_path / "var"
    zustand.mkdir()
    k = ev.Konfig(1, "a3f9c1e07b2d4856", {BEKANNT: ev.Zuordnung("serie", BAER)}, ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60))
    store.schreibe_atomar(zustand / "config.json", store.konfig_zu_json(k))
    toml = tmp_path / "tobibox.toml"
    toml.write_text(f'[pfade]\nzustand = "{zustand}"\nmedien = "{medien}"\n[leser]\ngeraet = "sim"\n', encoding="utf-8")
    monkeypatch.setattr(app_modul.notify, "stoppt", lambda: None)
    monkeypatch.setattr(app_modul, "FRUEHTON_WARTEN_S", 0.4)
    def maker(boot_id=BOOT) -> Welt:
        journal: list[str] = []
        steuerung = TonSteuerung(journal)
        a = App(konfig_modul.lade(toml), uhr=SimUhr(), melde_bereit=False, boot_id=lambda: boot_id)
        a.player = AufnahmePlayer(journal)
        a.leser = FakeLeser()
        a.toene = Toene(app_modul.STANDARD_TOENE, ["tonprogramm", "{datei}"], starter=steuerung, vor=a._ton_vor, nach=a._ton_nach,
                        bevor=a._warte_fruehton)
        w = Welt(a, journal, steuerung, zustand, _marken_verzeichnis)
        return w

    yield maker


async def abraeumen(w: Welt) -> None:
    for tor in w.ton.offen:
        tor.set()
    await w.app.beende()


async def test_marke_fertig_der_kern_spielt_keinen_start(baue):
    w = baue()
    assert fruehton.lege_marke_an(fruehton.START, w.marken) and fruehton.ersetze_marke(fruehton.FERTIG, w.marken)
    await w.starte()
    try:
        assert w.toene() == []  # kein zweiter Start-Ton
        assert not fruehton.pfad(w.marken).exists()  # app hat die Marke gelöscht
    finally:
        await abraeumen(w)


async def test_marke_keiner_unter_stumm_kein_ton_auch_kein_hinweis(baue):
    w = baue()
    fruehton.lege_marke_an(fruehton.KEINER, w.marken)
    await w.starte()
    try:
        assert w.toene() == []
        assert not fruehton.pfad(w.marken).exists()
    finally:
        await abraeumen(w)


async def test_ohne_marke_spielt_der_kern_start_und_setzt_die_gegenmarke(baue):
    """V1: Der Frühdienst kam nicht (oder zu spät): ``app`` legt ``uebernommen`` an, der Kern spielt ``start``."""
    w = baue()
    await w.starte()
    try:
        await w.warte(lambda: w.toene() == ["start"], "Kern-Start")
        assert fruehton.lese_marke(w.marken) == fruehton.UEBERNOMMEN
        # der Frühdienst kommt jetzt: er darf seine Marke nicht mehr anlegen und spielt nicht (nie zwei Töne)
        assert fruehton.lege_marke_an(fruehton.START, w.marken) is False
        assert fruehton.lese_marke(w.marken) == fruehton.UEBERNOMMEN
    finally:
        await abraeumen(w)


async def test_frueher_frueh_dienst_spielt_in_der_kurzen_zeit_vor_bereit_der_kern_schweigt(baue):
    """Der Frühdienst schreibt seine Marke, **bevor** ``app`` bei ``Bereit`` liest (auch lange nach dem Dienststart): Der Kern schweigt."""
    w = baue()
    task = asyncio.create_task(w.app.starte())
    await asyncio.sleep(0)  # der Dienst läuft an, ``Bereit`` ist noch nicht verarbeitet
    fruehton.lege_marke_an(fruehton.START, w.marken)
    await task
    try:
        await w.ruhe(0.1)
        assert w.toene() == []
        assert fruehton.lese_marke(w.marken) == fruehton.START  # läuft noch: app wartet mit Tönen darauf
    finally:
        fruehton.ersetze_marke(fruehton.FERTIG, w.marken)
        await abraeumen(w)


async def test_fruehton_laeuft_noch_hinweis_des_kerns_wartet_auf_fertig(baue):
    """Doppel-Ton-Tabelle, letzte Zeile: Frühton läuft noch, der Kern will einen Ton (unbekannter Tobie)."""
    w = baue()
    fruehton.lege_marke_an(fruehton.START, w.marken)
    await w.starte()
    try:
        w.app.ereignisse.put_nowait(ev.Aufgelegt(NEU, "ntag", False, 0, "v1"))
        await w.ruhe(0.2)
        assert w.toene() == []  # wartet: der Frühton läuft ja noch
        assert fruehton.ersetze_marke(fruehton.FERTIG, w.marken)  # Frühdienst ist fertig
        await w.warte(lambda: "unbekannt" in w.toene(), "Ton nach dem Frühton")
        w.ton.beende(0)
        await w.warte(lambda: any(z.startswith("abspielen") for z in w.journal), "Hörspiel nach dem Ton")
        nie_gleichzeitig(w.journal)
        assert not fruehton.pfad(w.marken).exists()
    finally:
        await abraeumen(w)


async def test_fruehton_haengt_der_kern_wartet_hoechstens_die_frist(baue):
    w = baue()
    fruehton.lege_marke_an(fruehton.START, w.marken)
    await w.starte()
    try:
        t0 = time.monotonic()
        w.app.ereignisse.put_nowait(ev.Aufgelegt(NEU, "ntag", False, 0, "v1"))
        await w.warte(lambda: "unbekannt" in w.toene(), "Ton nach der Frist")
        assert time.monotonic() - t0 >= 0.2  # gewartet, aber nicht ewig (0,4 s ab ``Bereit``)
        assert not fruehton.pfad(w.marken).exists()
    finally:
        await abraeumen(w)


async def test_dienst_neustart_marke_wird_ignoriert_der_kern_spielt_start(baue):
    """Gleiche Boot-Kennung wie in ``lauf.json``: kein Einschalten, die Marke gilt nicht (Entscheidung G)."""
    w = baue()
    lauf.schreibe(w.zustand, BOOT, None)
    fruehton.lege_marke_an(fruehton.FERTIG, w.marken)
    await w.starte()
    try:
        await w.warte(lambda: w.toene() == ["start"], "Kern-Start nach Dienst-Neustart")
        assert fruehton.lese_marke(w.marken) == fruehton.UEBERNOMMEN
    finally:
        await abraeumen(w)


async def test_andere_boot_kennung_ist_einschalten_die_marke_gilt(baue):
    w = baue(boot_id="boot-2")
    lauf.schreibe(w.zustand, BOOT, None)
    fruehton.lege_marke_an(fruehton.FERTIG, w.marken)
    await w.starte()
    try:
        assert w.toene() == []
    finally:
        await abraeumen(w)


async def test_marke_fehler_oder_unbekannt_der_kern_spielt_start_wie_heute(baue):
    w = baue()
    fruehton.lege_marke_an(fruehton.FEHLER, w.marken)
    await w.starte()
    try:
        await w.warte(lambda: w.toene() == ["start"], "Kern-Start")
    finally:
        await abraeumen(w)


async def test_kaputte_marke_der_kern_spielt_start(baue, _marken_verzeichnis):
    fruehton.pfad(_marken_verzeichnis).write_text("quatsch\n")
    w = baue()
    await w.starte()
    try:
        await w.warte(lambda: w.toene() == ["start"], "Kern-Start")
    finally:
        await abraeumen(w)


async def test_ohne_marken_verzeichnis_spielt_der_kern_start(baue, tmp_path):
    w = baue()
    w.app._marken = tmp_path / "gibt-es-nicht"
    await w.starte()
    try:
        await w.warte(lambda: w.toene() == ["start"], "Kern-Start")
    finally:
        await abraeumen(w)


async def test_stumm_ohne_fruehdienst_der_kern_spielt_auch_keinen_hinweis(baue):
    """V5: Fällt der Frühdienst aus und die Box steht unter „stumm“, bleibt der Start still (kein Hinweiston als Ersatz)."""
    w = baue()
    from datetime import datetime
    from zoneinfo import ZoneInfo

    w.app.uhr = SimUhr(wall=datetime(2026, 11, 9, 23, 0, tzinfo=ZoneInfo("Europe/Berlin")).timestamp())
    k = ev.Konfig(
        1, "a3f9c1e07b2d4856", {BEKANNT: ev.Zuordnung("serie", BAER)},
        ev.LeiseZeiten("Europe/Berlin", (ev.Fenster("n", (1, 2, 3, 4, 5, 6, 7), "22:00", "07:00", "stumm", None),)), ev.GuteNacht(30, 60),
    )
    store.schreibe_atomar(w.zustand / "config.json", store.konfig_zu_json(k))
    await w.starte()
    try:
        await w.ruhe(0.3)
        assert w.toene() == []
    finally:
        await abraeumen(w)
