"""``App`` in Stufe 4 (AP 4.8): Verdrahtung von ``led``, ``controls``, ``headphones`` und ``idle`` ohne MPD.

Die CUJ-Tests 14 bis 19 prüfen die Abläufe am Kern; hier geht es um die Verdrahtung in ``app.py``: Quellen aus der Konfiguration, Reihenfolge
beim Start, Threads, ``sim``-Haken, Herunterfahren über ``power``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest
from fixtures.dienst import BAER, BEKANNT, baue_dienst, netz_strom_abschnitt

from tobibox import events as ev
from tobibox.clock import SystemUhr
from tobibox.controls import GpioTreiber
from tobibox.headphones import Buchse, GpioKopfhoerer, SimKopfhoerer
from tobibox.sim import Ungueltig

pytestmark = pytest.mark.asyncio

GPIO = '[tasten]\nquelle = "gpio"\npin_vor = 5\npin_zurueck = 6\npin_dreh_a = 12\npin_dreh_b = 13\npin_haupt = 26\nlang_s = 1.0\n'
GPIO_KH = '[kopfhoerer]\nquelle = "gpio"\ngpio_pin = 17\nintervall_s = 0.05\n'


@pytest.fixture
async def d(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, netz_strom_abschnitt())
    await dienst.app.starte()
    yield dienst
    await dienst.app.beende()


def hat(a, name: str) -> list[int]:
    return [i for i, n in enumerate(a.gesehen) if n == name]


# --- Aufbau aus der Konfiguration -------------------------------------------------------------------------


async def test_vorgabe_ist_sim_ohne_gpio(tmp_path, kurz, monkeypatch):
    a = baue_dienst(tmp_path, kurz, monkeypatch).app
    assert a.gpio_tasten is None and isinstance(a.kopfhoerer_treiber, SimKopfhoerer) and isinstance(a.buchse, Buchse)
    assert a.sim.kopfhoerer_haken is not None and a.sim.zeit_haken is not None
    assert [n for n, _ in __import__("tobibox.core", fromlist=["x"]).TEILAUTOMATEN] == ["session", "learn", "quiet", "bedtime", "idle"]
    assert a.bedienung.lang_s == 1.5 and a.bedienung.grenze == 50 and a.bedienung.stand == 20  # Konfiguration: max 50, start 20


async def test_gpio_quellen_aus_der_konfiguration(tmp_path, kurz, monkeypatch):
    a = baue_dienst(tmp_path, kurz, monkeypatch, GPIO + GPIO_KH).app
    assert isinstance(a.gpio_tasten, GpioTreiber) and a.gpio_tasten._pins == (5, 6, 12, 13, 26)
    assert a.bedienung.lang_s == 1.0
    assert isinstance(a.kopfhoerer_treiber, GpioKopfhoerer) and a.kopfhoerer_treiber.pin == 17
    assert a.buchse.intervall_s == 0.05
    assert a.sim.kopfhoerer_haken is None  # am Pi kommt der Stecker von der Buchse, nicht von ``sim``


class FakeGpiozero:
    """Attrappe für ``gpiozero``: merkt sich Pins und Rückrufe."""

    geraete: list = []

    class Button:
        def __init__(self, pin, **kw):
            self.pin, self.kw = pin, kw
            self.when_pressed = self.when_held = self.when_released = None
            self.geschlossen = False
            FakeGpiozero.geraete.append(self)

        def close(self):
            self.geschlossen = True

    class RotaryEncoder(Button):
        def __init__(self, a, b, **kw):
            super().__init__(a, **kw)
            self.b = b
            self.when_rotated_clockwise = self.when_rotated_counter_clockwise = None


async def test_gpio_tasten_starten_mit_den_pins_und_senden_in_den_kern(tmp_path, kurz, monkeypatch):
    FakeGpiozero.geraete = []
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, GPIO)
    a = dienst.app
    a.gpio_tasten._fabrik = FakeGpiozero
    await a.starte()
    try:
        assert sorted(g.pin for g in FakeGpiozero.geraete) == [5, 6, 12, 26]
        tasten = {g.pin: g for g in FakeGpiozero.geraete}
        # gpiozero ruft aus einem eigenen Thread: das Ereignis muss sicher in die Schleife kommen
        await asyncio.to_thread(tasten[5].when_pressed)
        await asyncio.to_thread(tasten[6].when_pressed)
        # das Ereignis kommt über ``call_soon_threadsafe``: auf die Schleife warten, nicht nur auf eine leere Schlange (Wettlauf unter Last)
        await dienst.warte(lambda: "Weiter" in a.gesehen and "Zurueck" in a.gesehen, text="Tasten")
        await dienst.ruhe()
        w0 = a.kern.wunsch
        await asyncio.to_thread(tasten[12].when_rotated_clockwise)
        await dienst.warte(lambda: a.kern.wunsch == w0 + 2, text="Drehregler")
        await dienst.ruhe()
        assert a.kern.wunsch == w0 + 2
        assert tasten[26].kw["hold_time"] == 1.0
        await asyncio.to_thread(tasten[26].when_pressed)
        await asyncio.to_thread(tasten[26].when_held)
        await dienst.warte(lambda: a.kern.teil["idle"].modus == "herunterfahren", text="Hauptknopf lang")
        await dienst.ruhe()
        assert a.kern.teil["idle"].modus == "herunterfahren"  # Hauptknopf lang
    finally:
        await a.beende()
    assert all(g.geschlossen for g in FakeGpiozero.geraete)  # stop() am Ende


async def test_fehlt_gpiozero_laeuft_die_box_ohne_tasten_weiter(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, GPIO)
    await dienst.app.starte()  # auf dem Mac gibt es kein gpiozero: Fehler wird protokolliert, die Box läuft
    try:
        assert dienst.app.bereit.is_set()
    finally:
        await dienst.app.beende()


async def test_gpio_kopfhoerer_wird_gemessen_und_gemeldet(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch, GPIO_KH)
    a = dienst.app
    pegel = {"hoch": True}  # aktiv_niedrig: hoch = kein Stecker

    async def lese() -> bool:
        return pegel["hoch"]

    a.kopfhoerer_treiber._lese = lese
    await a.starte()
    try:
        assert a.kern.session.kopfhoerer_steckt is False
        pegel["hoch"] = False
        await dienst.warte(lambda: a.kern.session.kopfhoerer_steckt, 3.0, "Stecker nicht erkannt")
        assert a.kern.grenzen["kopfhoerer"] == 30
    finally:
        await a.beende()


# --- Kopfhörer: erste Messung nach GeraeteEinstellungen --------------------------------------------------------


async def test_erste_messung_kommt_nach_geraete_einstellungen_und_vor_bereit(tmp_path, kurz, monkeypatch):
    dienst = baue_dienst(tmp_path, kurz, monkeypatch)
    a = dienst.app
    a.kopfhoerer_treiber.setze(True)  # der Stecker steckt schon beim Einschalten
    await a.starte()
    try:
        ein, kh, bereit = hat(a, "GeraeteEinstellungen")[0], hat(a, "Kopfhoerer")[0], hat(a, "Bereit")[0]
        assert ein < kh < bereit
        assert a.kern.session.kopfhoerer_steckt and a.kern.grenzen["kopfhoerer"] == 30  # die Grenze gilt
        assert a.kern.session.kopfhoerer_grenze == 30
    finally:
        await a.beende()


async def test_sim_headphones_stellt_den_treiber_und_die_buchse_meldet(d):
    a = d.app
    assert (await d.sim(befehl="kopfhoerer", steckt=True)) == {"ok": True}
    assert a.kopfhoerer_treiber._steckt is True and a.kern.session.kopfhoerer_steckt
    assert a.kern.grenzen["kopfhoerer"] == 30 and a.buchse.steckt is True
    n = len(hat(a, "Kopfhoerer"))
    await d.sim(befehl="kopfhoerer", steckt=True)  # kein Wechsel, kein Ereignis
    assert len(hat(a, "Kopfhoerer")) == n
    assert (await d.sim(befehl="kopfhoerer", steckt=False)) == {"ok": True}
    assert not a.kern.session.kopfhoerer_steckt and "kopfhoerer" not in a.kern.grenzen


# --- Tasten und Drehregler ------------------------------------------------------------------------------------------


async def test_bedienung_folgt_dem_kern_und_sendet_ereignisse(d):
    a = d.app
    await d.auflegen(BEKANNT)
    assert a.bedienung.stand == a.kern.wunsch == 20 and a.bedienung.grenze == 50
    a.bedienung.drehen(2)
    await d.ruhe()
    assert a.kern.wunsch == 24 and a.bedienung.stand == 24
    await d.sim(befehl="kopfhoerer", steckt=True)
    assert a.bedienung.grenze == 30
    a.bedienung.drehen(-1)
    await d.ruhe()
    assert a.kern.wunsch == 22 and a.bedienung.stand == 22


async def test_drehregler_aus_einem_thread_kommt_in_die_ereignisschleife(d):
    a = d.app
    await asyncio.to_thread(a.bedienung.drehen, 1)
    await d.ruhe()
    await d.warte(lambda: a.kern.wunsch == 22, 3.0, "Drehregler nicht angekommen")
    assert a.kern.wunsch == 22 and a.bedienung.stand == 22  # T3: ein eigenes ``assert``, nicht nur die Zeitüberschreitung


async def test_sim_tasten_und_regler_wirken(d):
    a = d.app
    await d.auflegen(BEKANNT)
    assert (await d.sim(befehl="taste", taste="hauptknopf_kurz")) == {"ok": True}
    assert a.kern.session.modus == "pausiert"
    assert (await d.sim(befehl="regler", delta=6)) == {"ok": True}
    assert a.kern.wunsch == 26


# --- Leerlauf, Herunterfahren ---------------------------------------------------------------------------------------


async def test_hauptknopf_lang_geht_als_herunterfahren_an_power(d):
    a = d.app
    gefahren: list = []

    async def fuehre_aus(b):
        gefahren.append(b)

    a.power.fuehre_aus = fuehre_aus
    assert (await d.sim(befehl="taste", taste="hauptknopf_lang")) == {"ok": True}
    assert gefahren == [ev.Herunterfahren("hauptknopf")]
    assert a.kern.teil["idle"].modus == "herunterfahren"


async def test_leerlauf_nach_10_minuten_ohne_strom_geht_als_herunterfahren_an_power(d):
    a = d.app
    gefahren: list = []

    async def fuehre_aus(b):
        gefahren.append(b)

    a.power.fuehre_aus = fuehre_aus
    await d.sim(befehl="strom", lader=False, akku=80)  # ohne Strom am Eingang (Ein/Aus, 10.11.)
    await d.ruhe()
    await d.zeit_vor(590)
    assert gefahren == []
    await d.zeit_vor(20)
    assert gefahren == [ev.Herunterfahren("leerlauf")]


async def test_tobie_haelt_die_box_wach_und_bedienung_setzt_den_zaehler_zurueck(d):
    a = d.app
    gefahren: list = []

    async def fuehre_aus(b):
        gefahren.append(b)

    a.power.fuehre_aus = fuehre_aus
    await d.sim(befehl="strom", lader=False, akku=80)
    await d.ruhe()
    await d.zeit_vor(590)
    a.bedienung.drehen(1)  # Bedienung: der Zähler beginnt neu
    await d.ruhe()
    await d.zeit_vor(100)
    assert gefahren == []
    await d.zeit_vor(520)
    assert gefahren == [ev.Herunterfahren("leerlauf")]


async def test_am_strom_schaltet_die_box_nie_von_selbst_ab_auch_ohne_sync_abschnitt(d):
    """Ohne ``[sync]`` meldet ``app`` ``nicht_eingerichtet``; mit Strom am Eingang gibt es keine Frist (Ein/Aus, 10.11.)."""
    a = d.app
    gefahren: list = []

    async def fuehre_aus(b):
        gefahren.append(b)

    a.power.fuehre_aus = fuehre_aus
    await d.sim(befehl="strom", lader=True, akku=80)
    await d.ruhe()
    await d.zeit_vor(3000)
    assert gefahren == []
    await d.sim(befehl="strom", lader=False)  # abgenommen: 10 min ab jetzt
    await d.ruhe()
    await d.zeit_vor(590)
    assert gefahren == []
    await d.zeit_vor(20)
    assert gefahren == [ev.Herunterfahren("leerlauf")]


# --- Uhr stellen (sim time) -----------------------------------------------------------------------------------------


async def test_sim_zeit_stellt_die_wanduhr_der_simuhr(d):
    antwort = await d.sim(befehl="zeit", iso="2026-11-09T22:30:00+01:00")
    assert antwort["ok"] and d.uhr.wall == antwort["wall"]
    assert d.app.uhr.jetzt().wall == pytest.approx(datetime.fromisoformat("2026-11-09T22:30:00+01:00").timestamp())
    ablehnung = await d.sim(befehl="zeit", iso=None)  # die SimUhr hat keine „echte“ Uhr
    assert ablehnung == {"ok": False, "fehler": "zeit_nicht_verfuegbar"}


async def test_sim_zeit_mit_der_systemuhr_und_leise_zeiten(tmp_path, kurz, monkeypatch):
    from dataclasses import replace

    from fixtures.stufe4 import fenster, wall

    from tobibox import store

    dienst = baue_dienst(tmp_path, kurz, monkeypatch, uhr=SystemUhr())  # type: ignore[arg-type]
    konfig = replace(
        store.parse_konfig(dienst.konfig()),
        leise_zeiten=ev.LeiseZeiten("Europe/Berlin", (fenster("nacht", "stumm", "22:00", "07:00"),)),
    )
    store.schreibe_atomar(dienst.zustand / "config.json", store.konfig_zu_json(konfig))
    await dienst.app.starte()
    try:
        await dienst.sim(befehl="zeit", iso="2026-11-09T12:00:00+01:00")
        await dienst.sende(ev.Takt())
        assert dienst.app.kern.teil["quiet"].modus == "normal"
        await dienst.sim(befehl="zeit", iso="2026-11-09T23:00:00+01:00")
        assert dienst.app.uhr.jetzt().wall == pytest.approx(wall(2026, 11, 9, 23, 0), abs=5)
        await dienst.sende(ev.Takt())
        assert dienst.app.kern.teil["quiet"].modus == "stumm"
        await dienst.sim(befehl="zeit", iso=None)  # echte Uhr zurück
        await dienst.sende(ev.Takt())
        assert abs(dienst.app.uhr.jetzt().wall - SystemUhr().jetzt().wall) < 5
    finally:
        await dienst.app.beende()


async def test_sim_zeit_ungueltig(d):
    for iso in ("morgen", 5, "", "2026-13-01T00:00"):
        with pytest.raises(Ungueltig, match="iso ungueltig"):
            await d.sim(befehl="zeit", iso=iso)
    with pytest.raises(Ungueltig, match="iso fehlt"):
        await d.sim(befehl="zeit")
