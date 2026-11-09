"""Kurze Pause für einen Ton (Entscheidung L) mit echtem ``Player`` und echtem MPD, ohne Attrappen.

Die Fenster der Wettläufe werden mit der Sperre des Players erzwungen: der Test hält ``_lock``, wie es die
Abfrageschleife alle 0,2 s kurz tut und ``abspielen`` bis zu 5 s lang. Alle Aufgaben stellen sich dann in
dieser Reihenfolge an, und der Test gibt die Sperre frei.
"""

from __future__ import annotations

import asyncio

import pytest
from integration.test_player_mpd import Probe, abspielen, warte

from tobibox import events as ev


@pytest.fixture
async def probe(mpd):
    p = Probe(mpd)
    await p.start()
    await p.player.lautstaerke_setzen(20, 50)
    yield p
    await p.stop()


@pytest.fixture
async def probe_mit_zustand(mpd_mit_zustand):
    p = Probe(mpd_mit_zustand)
    await p.start()
    await p.player.lautstaerke_setzen(20, 50)
    yield p
    await p.stop()


async def _zustand(p: Probe) -> str:
    return (await p.status())["state"]


async def _angestellt(*aufgaben: asyncio.Task) -> None:
    """Den Aufgaben Zeit geben, sich an der Sperre anzustellen (sie hängen dort fest)."""
    await asyncio.sleep(0.1)
    assert not any(a.done() for a in aufgaben)


# --- B1: Abheben genau beim Tonbeginn → MPD bleibt pausiert ----------------------------------------------


async def test_abheben_beim_tonbeginn_ton_pause_setzt_danach_nicht_fort(probe):
    p = probe.player
    await p.abspielen(abspielen())
    assert await _zustand(probe) == "play"
    await p._lock.acquire()
    vor = asyncio.create_task(p.ton_pause_beginn())  # Tonspur: Anfang der Tonfolge, wartet auf die Sperre
    await _angestellt(vor)
    paus = asyncio.create_task(p.pausieren(ev.Pausieren("abgehoben")))  # Ausführer: echtes Pausieren
    await _angestellt(vor, paus)
    p._lock.release()
    await asyncio.gather(vor, paus)
    assert await _zustand(probe) == "pause" and p._ton_pause is False
    assert await p.ton_pause_ende(True) is False  # Tonspur: Ton zu Ende
    await asyncio.sleep(0.4)
    assert await _zustand(probe) == "pause"  # das Hörspiel bleibt aus


async def test_echtes_pausieren_nach_gesetzter_ton_pause_beendet_sie(probe):
    p = probe.player
    await p.abspielen(abspielen())
    assert await p.ton_pause_beginn() is True and p._ton_pause
    await p._lock.acquire()
    paus = asyncio.create_task(p.pausieren(ev.Pausieren("abgehoben")))
    await _angestellt(paus)
    ende = asyncio.create_task(p.ton_pause_ende(True))  # Tonspur: Ton zu Ende, während das Pausieren wartet
    await asyncio.sleep(0.1)
    assert not paus.done() and ende.done() and ende.result() is False  # die Pause gilt nicht mehr
    p._lock.release()
    await paus
    await asyncio.sleep(0.4)
    assert await _zustand(probe) == "pause" and p._ton_pause is False


async def test_pausieren_zuerst_dann_ton_pause_beginn_haelt_nichts_an(probe):
    p = probe.player
    await p.abspielen(abspielen())
    await p._lock.acquire()
    paus = asyncio.create_task(p.pausieren(ev.Pausieren("knopf")))
    await _angestellt(paus)
    vor = asyncio.create_task(p.ton_pause_beginn())
    await _angestellt(paus, vor)
    p._lock.release()
    await asyncio.gather(paus, vor)
    assert vor.result() is False and p._ton_pause is False
    assert await _zustand(probe) == "pause"


async def test_neues_abspielen_beendet_die_ton_pause(probe):
    p = probe.player
    await p.abspielen(abspielen())
    await p._lock.acquire()
    vor = asyncio.create_task(p.ton_pause_beginn())
    await _angestellt(vor)
    neu = asyncio.create_task(p.abspielen(abspielen(datei="b.wav", vorgang="v2")))
    await _angestellt(vor, neu)
    p._lock.release()
    await asyncio.gather(vor, neu)
    assert vor.result() is False and p._ton_pause is False
    assert await _zustand(probe) == "play"  # das neue Hörspiel spielt


# --- B4: Pausieren ist nicht wirkungslos, solange der erste Start die Sperre noch nicht hat ------------------


async def test_pausieren_hinter_dem_allerersten_start_pausiert(probe):
    p = probe.player
    assert p._serie is None  # erster Start nach dem Dienststart
    await p._lock.acquire()
    start = asyncio.create_task(p.abspielen(abspielen()))
    await _angestellt(start)
    paus = asyncio.create_task(p.pausieren(ev.Pausieren("abgehoben")))
    await _angestellt(start, paus)
    p._lock.release()
    await asyncio.gather(start, paus)
    await asyncio.sleep(0.4)
    assert await _zustand(probe) == "pause"


# --- B5: Verbindungsverlust während des Tons ----------------------------------------------------------


async def test_mpd_neustart_waehrend_des_tons_ton_ende_setzt_nichts_fort(mpd_mit_zustand, probe_mit_zustand):
    mpd, probe = mpd_mit_zustand, probe_mit_zustand
    p = probe.player
    await p.abspielen(abspielen())
    assert await p.ton_pause_beginn() is True
    mpd.stop()  # MPD fällt während des Tons aus (schreibt state_file) ...
    await warte(lambda: probe.alle(ev.PlayerVerbindung), 6.0, "(Verbindung weg)")
    assert p._ton_pause is False  # der Verlust beendet die kurze Pause
    mpd.start()  # ... und ist wieder da, bevor der Ton zu Ende ist
    await warte(lambda: len(probe.alle(ev.PlayerVerbindung)) == 2, 8.0, "(Verbindung zurück)")
    assert await p.ton_pause_ende(True) is False
    await asyncio.sleep(0.4)
    assert await _zustand(probe) != "play"  # nichts spielt ungemeldet


async def test_ton_pause_ende_setzt_nur_in_der_phase_spielt_fort(probe):
    p = probe.player
    await p.abspielen(abspielen())
    assert await p.ton_pause_beginn() is True
    p._phase = "aus"  # der Player kennt kein spielendes Hörspiel mehr (zum Beispiel nach einer Klemmung)
    p._ton_pause = True
    assert await p.ton_pause_ende(True) is False
    assert await _zustand(probe) == "pause" and p._ton_pause is False


# --- B8: Ton während eines Starts ------------------------------------------------------------------------


async def test_ton_waehrend_ein_start_laeuft_wartet_auf_den_start_und_haelt_ihn_an(probe):
    p = probe.player
    tor = asyncio.Event()
    echt = p._abspielen

    async def langsam(b, vorhanden):
        await tor.wait()  # der Start hält die Sperre, die Phase ist „aus“
        await echt(b, vorhanden)

    p._abspielen = langsam  # type: ignore[method-assign]
    start = asyncio.create_task(p.abspielen(abspielen()))
    await warte(lambda: p._phase == "aus" and p._lock.locked(), 2.0, "(Start in Gang)")
    vor = asyncio.create_task(p.ton_pause_beginn())  # Tonfolge beginnt mitten im Start
    await _angestellt(start, vor)
    assert not vor.done()  # der Ton wartet; er überlagert den Start nicht
    tor.set()
    await asyncio.gather(start, vor)
    assert vor.result() is True
    assert await _zustand(probe) == "pause"  # das Hörspiel hört beim Ton still zu
    assert await p.ton_pause_ende(True) is True
    assert await _zustand(probe) == "play"


async def test_weiterer_ton_haelt_die_pause_und_ein_neuer_start_verhindert_das_fortsetzen(probe):
    p = probe.player
    await p.abspielen(abspielen())
    assert await p.ton_pause_beginn() is True
    # gleich folgt ein weiterer Ton: nichts wird fortgesetzt, die Pause bleibt
    assert await p.ton_pause_ende(True, halten=lambda: True) is False
    assert p._ton_pause is True and await _zustand(probe) == "pause"
    assert await p.ton_pause_beginn() is False  # eine Tonfolge pausiert nur einmal
    # ein neuer Start kam unterdessen: die Funktion wird erst unter der Sperre befragt
    assert await p.ton_pause_ende(lambda: False) is False
    assert p._ton_pause is False and await _zustand(probe) == "pause"
