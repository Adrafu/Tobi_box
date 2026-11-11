"""Strom-Schnittstelle: Akku, Lader, Tiefstand, Taste, RTC beim Start, Hotspot-/Akku-Regel (``power.py``)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from tobibox import events as ev
from tobibox.config import StromKonfig
from tobibox.net import Zeitquelle
from tobibox.power import (
    HOTSPOT_AKKU_MIN_PROZENT,
    PiSugarFehler,
    PiSugarStrom,
    Power,
    SimStrom,
    parse_antwort,
    parse_rtc,
    sync_erlaubt,
)

GUT = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)


class Sammler:
    def __init__(self) -> None:
        self.liste: list[ev.Ereignis] = []

    def __call__(self, e: ev.Ereignis) -> None:
        self.liste.append(e)


def mk(akku=None, lader=None, rtc=None, **kw):
    sim = SimStrom(akku, lader, rtc)
    aus = Sammler()
    zeit = Zeitquelle()
    return Power(sim, aus, zeit, **kw), sim, aus, zeit


# --- Akku und Lader --------------------------------------------------------------------------


async def test_erste_messung_meldet_lader_und_akku():
    p, sim, aus, _ = mk(akku=76, lader=False)
    assert await p.pruefe() == [ev.LaderGeaendert(False), ev.AkkuStand(76)]
    assert await p.pruefe() == []  # unverändert: still


async def test_unbekannte_werte_werden_nicht_gemeldet():
    p, sim, aus, _ = mk()
    assert await p.pruefe() == []
    sim.setze(akku=40)
    assert await p.pruefe() == [ev.AkkuStand(40)]


async def test_lader_aendert_sich():
    p, sim, aus, _ = mk(akku=40, lader=False)
    await p.pruefe()
    sim.setze(lader=True)
    assert await p.pruefe() == [ev.LaderGeaendert(True)]
    sim.setze(lader=False, akku=39)
    assert await p.pruefe() == [ev.LaderGeaendert(False), ev.AkkuStand(39)]
    assert aus.liste[-1] == ev.AkkuStand(39)


# --- Tiefstand -------------------------------------------------------------------------------


async def test_tiefstand_einmal_nicht_am_lader():
    p, sim, aus, _ = mk(akku=20, lader=False, tiefstand_prozent=5)
    await p.pruefe()
    sim.setze(akku=6)
    assert await p.pruefe() == [ev.AkkuStand(6), ev.AkkuWarnung()]  # bei 10 % ist die Warnung schon dran (Entscheidung Z, 11.11.)
    sim.setze(akku=5)
    assert await p.pruefe() == [ev.AkkuStand(5), ev.AkkuTiefstand()]
    sim.setze(akku=4)
    assert await p.pruefe() == [ev.AkkuStand(4)]  # nur einmal
    assert ev.AkkuTiefstand() in aus.liste and aus.liste.count(ev.AkkuTiefstand()) == 1


async def test_kein_tiefstand_am_lader():
    p, sim, *_ = mk(akku=3, lader=True)
    assert ev.AkkuTiefstand() not in await p.pruefe()


async def test_tiefstand_kommt_wenn_der_lader_bei_leerem_akku_abgezogen_wird():
    p, sim, *_ = mk(akku=3, lader=True)
    await p.pruefe()
    sim.setze(lader=False)
    assert await p.pruefe() == [ev.LaderGeaendert(False), ev.AkkuTiefstand()]


async def test_kein_tiefstand_wenn_der_lader_unbekannt_ist():
    """Ein ausgefallener Fühler schaltet keine Box ab."""
    p, sim, *_ = mk(akku=2, lader=None)
    assert ev.AkkuTiefstand() not in await p.pruefe()


async def test_tiefstand_wird_nach_dem_laden_neu_bewaffnet():
    p, sim, aus, _ = mk(akku=4, lader=False)
    assert ev.AkkuTiefstand() in await p.pruefe()
    sim.setze(lader=True, akku=30)
    await p.pruefe()
    sim.setze(lader=False, akku=4)
    assert ev.AkkuTiefstand() in await p.pruefe()


async def test_kein_flattern_an_der_grenze():
    p, sim, aus, _ = mk(akku=5, lader=False, tiefstand_prozent=5)
    await p.pruefe()
    for prozent in (6, 5, 7, 5):  # um die Grenze, nicht deutlich darüber
        sim.setze(akku=prozent)
        await p.pruefe()
    assert aus.liste.count(ev.AkkuTiefstand()) == 1


# --- Warnung (Entscheidung Z, zweite Stufe, 11.11.) ------------------------------------------


async def test_warnung_einmal_bei_10_prozent_nicht_am_lader():
    p, sim, aus, _ = mk(akku=30, lader=False)
    await p.pruefe()
    sim.setze(akku=11)
    assert await p.pruefe() == [ev.AkkuStand(11)]
    sim.setze(akku=10)
    assert await p.pruefe() == [ev.AkkuStand(10), ev.AkkuWarnung()]
    sim.setze(akku=9)
    assert await p.pruefe() == [ev.AkkuStand(9)]  # nur einmal
    assert aus.liste.count(ev.AkkuWarnung()) == 1


async def test_warnung_dann_tiefstand_nacheinander():
    p, sim, aus, _ = mk(akku=10, lader=False)
    assert await p.pruefe() == [ev.LaderGeaendert(False), ev.AkkuStand(10), ev.AkkuWarnung()]
    sim.setze(akku=5)
    assert await p.pruefe() == [ev.AkkuStand(5), ev.AkkuTiefstand()]


async def test_keine_warnung_wenn_schon_der_tiefstand_erreicht_ist():
    """Springt der Akku unter die Tiefstand-Grenze (oder ist er beim Start so leer), gilt nur der Tiefstand."""
    p, sim, aus, _ = mk(akku=4, lader=False)
    assert ev.AkkuWarnung() not in await p.pruefe()
    sim.setze(akku=30, lader=True)
    await p.pruefe()
    sim.setze(lader=False, akku=9)
    assert ev.AkkuWarnung() in await p.pruefe()


async def test_keine_warnung_am_lader_oder_bei_unbekanntem_lader():
    p, sim, *_ = mk(akku=8, lader=True)
    assert ev.AkkuWarnung() not in await p.pruefe()
    p2, *_ = mk(akku=8, lader=None)
    assert ev.AkkuWarnung() not in await p2.pruefe()


async def test_warnung_kein_flattern_und_neu_ueber_grenze_plus_3():
    p, sim, aus, _ = mk(akku=10, lader=False)
    await p.pruefe()
    for prozent in (11, 10, 12, 13, 10):  # bis einschließlich warnung_prozent + 3 bleibt sie still
        sim.setze(akku=prozent)
        await p.pruefe()
    assert aus.liste.count(ev.AkkuWarnung()) == 1
    sim.setze(akku=14)
    await p.pruefe()
    sim.setze(akku=10)
    assert ev.AkkuWarnung() in await p.pruefe()
    assert aus.liste.count(ev.AkkuWarnung()) == 2


async def test_warnung_wird_nach_strom_am_eingang_neu_bewaffnet():
    p, sim, aus, _ = mk(akku=10, lader=False)
    await p.pruefe()
    sim.setze(lader=True)
    await p.pruefe()
    sim.setze(lader=False)
    assert await p.pruefe() == [ev.LaderGeaendert(False), ev.AkkuWarnung()]


async def test_warnung_nach_dem_tiefstand_nicht_erneut_ohne_ueberschreiten():
    """Ein fehlgeschlagenes Herunterfahren wiederholt den Tiefstand (B1), aber nicht die Warnung."""
    p, sim, aus, _ = mk(akku=4, lader=False)
    await p.pruefe()
    sim.setze(akku=8)  # Messschwankung nach oben, aber nicht über 13
    await p.pruefe()
    assert ev.AkkuWarnung() not in aus.liste


async def test_warnung_prozent_aus_der_konfiguration():
    p = Power.aus_konfig(StromKonfig(warnung_prozent=15))
    assert p.warnung_prozent == 15
    assert Power.aus_konfig(StromKonfig()).warnung_prozent == 10


# --- Taste und Herunterfahren ------------------------------------------------------------------


@pytest.mark.parametrize("art", ["kurz", "lang"])
async def test_tastenereignis_wird_zum_hauptknopf(art):
    p, _, aus, _ = mk()
    assert await p.taste(art) == [ev.Hauptknopf(art)]
    assert aus.liste == [ev.Hauptknopf(art)]


async def test_unbekannte_taste_ist_ein_fehler():
    p, *_ = mk()
    with pytest.raises(ValueError):
        await p.taste("doppelt")  # type: ignore[arg-type]


async def test_herunterfahren_wird_in_der_simulation_nur_protokolliert():
    p, sim, *_ = mk()
    await p.fuehre_aus(ev.Herunterfahren("leerlauf"))
    await p.fuehre_aus(ev.Herunterfahren("akku_tiefstand"))
    await p.fuehre_aus(ev.LeserPing())  # nicht seine Sache
    assert sim.heruntergefahren == ["leerlauf", "akku_tiefstand"]


# --- RTC beim Start und Zeitquelle -----------------------------------------------------------


async def test_start_mit_guter_rtc_meldet_zeitquelle_rtc():
    p, sim, aus, zeit = mk(akku=80, lader=True, rtc=GUT)
    neu = await p.start()
    assert neu[0] == ev.ZeitquelleGeaendert("rtc", True)
    assert ev.LaderGeaendert(True) in neu and ev.AkkuStand(80) in neu
    assert (zeit.quelle, zeit.vertrauenswuerdig) == ("rtc", True)


@pytest.mark.parametrize("rtc", [None, datetime(2000, 1, 1, tzinfo=timezone.utc), datetime(1970, 1, 1, tzinfo=timezone.utc)])
async def test_start_mit_verlorener_rtc_bleibt_unbekannt(rtc):
    p, sim, aus, zeit = mk(akku=80, lader=True, rtc=rtc)
    neu = await p.start()
    assert not any(isinstance(e, ev.ZeitquelleGeaendert) for e in neu)  # unverändert „unbekannt, unsicher“
    assert (zeit.quelle, zeit.vertrauenswuerdig) == ("unbekannt", False)


async def test_ntp_nach_rtc_gewinnt():
    p, sim, aus, zeit = mk(rtc=GUT)
    await p.start()
    assert zeit.ntp(True) == ev.ZeitquelleGeaendert("ntp", True)


# --- Regel für den Sync (Design „Netz, Sync, Strom“) -------------------------------------------


@pytest.mark.parametrize(
    "klasse,lader,akku,erlaubt,grund",
    [
        ("home", False, 5, True, "ok"),  # zu Hause immer
        ("home", None, None, True, "ok"),
        ("hotspot", True, 5, True, "ok"),  # Lader dran
        ("hotspot", False, 51, True, "ok"),  # Akku > 50 %
        ("hotspot", False, 50, False, "regel"),  # genau 50 reicht nicht
        ("hotspot", False, 10, False, "regel"),
        ("hotspot", None, None, False, "regel"),  # unbekannt gilt als nicht erfüllt
        ("hotspot", None, 80, True, "ok"),
        ("hotspot", False, None, False, "regel"),
        ("offline", True, 100, False, "netz_weg"),
    ],
)
def test_sync_regel(klasse, lader, akku, erlaubt, grund):
    assert sync_erlaubt(klasse, lader, akku) == (erlaubt, grund)


def test_grenze_ist_50_prozent():
    assert HOTSPOT_AKKU_MIN_PROZENT == 50


async def test_sync_regel_mit_der_simulation_im_hotspot():
    """Die Regel mit Werten aus ``power``: Akku 40 % ohne Lader sperrt, mit Lader erlaubt; 60 % erlaubt."""
    p, sim, *_ = mk(akku=40, lader=False)
    await p.pruefe()
    assert sync_erlaubt("hotspot", p.am_lader, p.akku)[0] is False
    sim.setze(lader=True)
    await p.pruefe()
    assert sync_erlaubt("hotspot", p.am_lader, p.akku)[0] is True
    sim.setze(lader=False, akku=60)
    await p.pruefe()
    assert sync_erlaubt("hotspot", p.am_lader, p.akku)[0] is True


# --- Fassade aus der Konfiguration -----------------------------------------------------------


def test_aus_konfig():
    p = Power.aus_konfig(StromKonfig(tiefstand_prozent=8, intervall_s=3))
    assert isinstance(p.treiber, SimStrom) and p.tiefstand_prozent == 8 and p.intervall_s == 3
    p2 = Power.aus_konfig(StromKonfig(quelle="pisugar", pisugar_port=9999))
    assert isinstance(p2.treiber, PiSugarStrom) and p2.treiber.port == 9999


async def test_lauf_ruft_pruefe_und_haelt_bei_fehlern_nicht_an():
    p, sim, aus, _ = mk(akku=50, lader=False, intervall_s=0.01)
    aufrufe = []
    original = p.pruefe

    async def pruefe():
        aufrufe.append(1)
        if len(aufrufe) == 1:
            raise RuntimeError("kaputt")
        return await original()

    p.pruefe = pruefe  # type: ignore[method-assign]
    t = asyncio.create_task(p.lauf())
    await asyncio.sleep(0.1)
    t.cancel()
    assert len(aufrufe) >= 2 and ev.AkkuStand(50) in aus.liste


# --- PiSugar-Treiber gegen eine Attrappe des pisugar-server ----------------------------------


class AttrappePiSugar:
    """Ein TCP-Server, der antwortet wie ``pisugar-server`` (eine Zeile je Frage)."""

    def __init__(self, antworten: dict[str, str]) -> None:
        self.antworten = antworten
        self.fragen: list[str] = []
        self.server: asyncio.AbstractServer | None = None
        self.port = 0

    async def __aenter__(self):
        async def bedienen(r, w):
            zeile = (await r.readline()).decode().strip()
            self.fragen.append(zeile)
            antwort = self.antworten.get(zeile)
            if antwort is not None:
                w.write((antwort + "\n").encode())
                await w.drain()
            w.close()

        self.server = await asyncio.start_server(bedienen, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *a):
        self.server.close()
        await self.server.wait_closed()


async def test_pisugar_liest_akku_lader_und_rtc():
    antworten = {
        "get battery": "battery: 79.23",
        "get battery_power_plugged": "battery_power_plugged: true",
        "get rtc_time": "rtc_time: 2026-11-05T09:30:00.000+01:00",
        "rtc_rtc2pi": "rtc_rtc2pi: done",
    }
    async with AttrappePiSugar(antworten) as srv:
        t = PiSugarStrom("127.0.0.1", srv.port, ("true",))
        p = Power(t, Sammler(), Zeitquelle())
        neu = await p.start()
    assert ev.ZeitquelleGeaendert("rtc", True) in neu
    assert ev.AkkuStand(79) in neu and ev.LaderGeaendert(True) in neu
    assert "rtc_rtc2pi" in srv.fragen  # die Systemuhr wird aus der guten RTC gesetzt


async def test_pisugar_lader_faellt_auf_battery_charging_zurueck():
    async with AttrappePiSugar({"get battery_charging": "battery_charging: false"}) as srv:
        # ``get battery_power_plugged`` wird nicht beantwortet (Verbindung zu): Fehler -> Rückfall
        assert await PiSugarStrom("127.0.0.1", srv.port, ("true",)).lader() is False


async def test_pisugar_nicht_erreichbar_meldet_nichts_und_stoppt_nicht():
    t = PiSugarStrom("127.0.0.1", 1, ("true",), frist_s=0.5)  # Port 1: niemand lauscht
    p = Power(t, Sammler(), Zeitquelle())
    assert await p.start() == []
    with pytest.raises(PiSugarFehler):
        await t.akku()


def test_antworten_lesen():
    assert parse_antwort("battery: 79.2\n", "battery") == "79.2"
    with pytest.raises(PiSugarFehler):
        parse_antwort("anderes: 1", "battery")
    with pytest.raises(PiSugarFehler):
        parse_antwort("", "battery")
    assert parse_rtc("2026-11-05T09:30:00.000+01:00") == datetime(2026, 11, 5, 8, 30, tzinfo=timezone.utc)
    assert parse_rtc("2026-11-05T09:30:00") == datetime(2026, 11, 5, 9, 30, tzinfo=timezone.utc)
    assert parse_rtc("kaputt") is None


async def test_pisugar_herunterfahren_fuehrt_das_kommando_aus(tmp_path):
    marke = tmp_path / "aus"
    t = PiSugarStrom("127.0.0.1", 1, ("touch", str(marke)))
    await t.herunterfahren("leerlauf")
    assert marke.exists()
