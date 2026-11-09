"""Während eines Syncs laufen die Kern-Ereignisse weiter (Design „Netz, Sync, Strom“, CUJ 9).

Der Test prüft nur, dass die Ereignisschleife nicht blockiert: Der Sync ist ein Kindprozess, alle Lese-
und Wartevorgänge sind asynchron. Die Latenz beim Auflegen unter echter Last misst die Abnahme Stufe 3a
am Pi (Zeitgrenze 1,0 s), nicht dieser Test.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time

import pytest
from conftest import UID_S1, KernHarnisch
from sync_helfer import Ereignisse, dateien, rsync_daemon, schreibe  # noqa: F401  (Fixture)

from tobibox import core
from tobibox import events as ev
from tobibox import sync as s

pytestmark = pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync nicht installiert")

MB = 1024 * 1024
GRENZE_S = 0.25  # Test-Grenze für die Verzögerung der Schleife (am Pi gilt die Abnahme-Grenze 1,0 s)


async def test_auflegen_wird_waehrend_des_syncs_verarbeitet(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "s1" / "gross.mp3", os.urandom(4 * MB))
    schreibe(d.quelle / "s1" / "a.mp3", b"a")

    kern = KernHarnisch()
    warteschlange: asyncio.Queue = asyncio.Queue()
    befehle: list[tuple[float, ev.Befehl]] = []
    verzoegerung: list[float] = []

    async def kern_schleife():
        """Wie der Dienst: ein Ereignis nach dem anderen durch ``core.step``."""
        while True:
            e, eingang = await warteschlange.get()
            if e is None:
                return
            verzoegerung.append(time.monotonic() - eingang)
            for b in kern.sende(e):
                befehle.append((time.monotonic(), b))

    def ausgabe(e):  # Sync-Ereignisse gehen wie alle anderen in den Kern
        warteschlange.put_nowait((e, time.monotonic()))

    sy = s.Sync(d.konfig(), d.box, ausgabe=ausgabe, partial_dir=d.partial, zusatz=["--bwlimit=500"])
    sy.setze_netz("home")

    tick_max = 0.0

    async def tick():
        nonlocal tick_max
        letzte = time.monotonic()
        while True:
            await asyncio.sleep(0.02)
            jetzt = time.monotonic()
            tick_max = max(tick_max, jetzt - letzte - 0.02)
            letzte = jetzt

    aufgaben = [asyncio.create_task(kern_schleife()), asyncio.create_task(tick())]
    try:
        assert await sy.start("ha")
        assert sy.laeuft
        # Übertragung läuft (halbe Datei außerhalb des Medienordners)
        ende = time.monotonic() + 15
        while not any(p.is_file() and p.stat().st_size > 0 for p in d.partial.parent.rglob("*") if d.box not in p.parents):
            assert time.monotonic() < ende
            await asyncio.sleep(0.05)
        assert sy.laeuft

        # Kind legt mitten im Sync einen Tobie auf: der Kern startet das Hörspiel ohne Wartezeit.
        t0 = time.monotonic()
        warteschlange.put_nowait((ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1"), t0))
        while not any(isinstance(b, ev.Abspielen) for _, b in befehle):
            assert time.monotonic() - t0 < 1.0, "Auflegen wurde während des Syncs nicht verarbeitet"
            await asyncio.sleep(0.01)
        assert sy.laeuft, "der Sync sollte beim Auflegen noch laufen"
        auflegen_s = next(t for t, b in befehle if isinstance(b, ev.Abspielen)) - t0
        assert auflegen_s < GRENZE_S

        # Der Sync hat den Kern nicht blockiert; Sync-Ereignisse kamen beim Kern an.
        await sy.abbrechen("akku_tiefstand")
        await asyncio.sleep(0.05)
    finally:
        warteschlange.put_nowait((None, 0.0))
        await aufgaben[0]
        aufgaben[1].cancel()

    assert max(verzoegerung) < GRENZE_S
    assert tick_max < GRENZE_S
    assert not sy.laeuft
    assert dateien(d.box) == set()  # abgebrochen: nichts Halbes im Medienordner


async def test_core_nimmt_sync_ereignisse_an_ohne_zu_stolpern():
    """Die drei Sync-Ereignisse des Vertrags gehen durch ``core.step`` (auch ohne ``idle``)."""
    kern = KernHarnisch()
    for e in (ev.SyncGestartet(), ev.SyncFertig(3, 1), ev.SyncAbgebrochen("regel")):
        out = kern.sende(e)
        assert not [o for o in out if isinstance(o, ev.Protokoll) and o.ebene == "ERROR"]


async def test_sync_ereignisse_in_der_vorgesehenen_reihenfolge(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3", b"x")
    aus = Ereignisse()
    sy = s.Sync(d.konfig(), d.box, ausgabe=aus, partial_dir=d.partial)
    sy.setze_netz("home")
    assert await sy.start("ha")
    assert sy.laeuft  # sofort nach dem Start (für ``idle``: keine Abschaltung, für das Update: Sperre)
    await sy.warte_ende()
    assert not sy.laeuft
    assert aus.typen[0] is ev.SyncGestartet and aus.typen[-1] is ev.SyncFertig
    assert aus.typen.count(ev.SyncGestartet) == 1


async def test_async_ausgabe_wird_abgewartet(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3", b"x")
    gesehen: list = []

    async def ausgabe(e):
        await asyncio.sleep(0.01)
        gesehen.append(type(e))

    sy = s.Sync(d.konfig(), d.box, ausgabe=ausgabe, partial_dir=d.partial)
    sy.setze_netz("home")
    await sy.start()
    await sy.warte_ende()
    assert [g for g in gesehen if g is not s.SyncFortschritt] == [ev.SyncGestartet, ev.SyncFertig]
