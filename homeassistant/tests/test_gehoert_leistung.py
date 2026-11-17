"""Paket B3: Messung von Befehl 50 ``gehoert/zusammenfassung`` bei 30 000 Zeilen (Ziel des Vertrags: Gesamtzeit unter 300 ms, auch während einer Aufnahme).

Die Datenbank wird mit erzeugten Sitzungen gefüllt (fester Zufallswert, 600 Serien zu je 20 Folgen, 2 Boxen und 3 Personen, 400 Tage). Gemessen wird die
Gesamtzeit des Befehls an der WebSocket-Schnittstelle (Schema, Abfrage im Executor, Zeilen in der Event-Loop, Antwort), am Mac. Mit ``-s`` zeigt der Test die Zahlen.
Die Messung auf der echten HA macht die Projektleitung (B3).
"""

from __future__ import annotations

import asyncio
import random
import statistics
import time
from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.util import dt as dt_util

from custom_components.tobibox.gehoert import Zeile
from custom_components.tobibox.media import Serie, SerieInfo

from .test_websocket_api import ok

ZEILEN = 30_000
SERIEN = 600
FOLGEN = 20
WIEDERHOLUNGEN = 7
#: Ziel aus dem Vertrag; die Prüfung hat Luft, damit ein ausgelasteter Rechner den Test nicht kippt (die Zahlen stehen mit ``-s`` in der Ausgabe)
GRENZE_S = 0.3


def erzeuge(n: int, ende_tag: datetime, tage: int, seed: int = 42) -> dict[str, list[Zeile]]:
    zufall = random.Random(seed)
    je_quelle: dict[str, list[Zeile]] = {q: [] for q in ("box:box1", "box:box2", "benutzer:p1", "benutzer:p2", "benutzer:p3")}
    quellen = list(je_quelle)
    ende_s = int(ende_tag.timestamp())
    for i in range(n):
        q = quellen[zufall.randrange(len(quellen))]
        serie = f"serie{zufall.randrange(SERIEN):04d}"
        folge = f"f{zufall.randrange(FOLGEN):02d}.mp3"
        beginn = ende_s - zufall.randrange(tage * 86400)
        dauer = zufall.randrange(30, 3000)
        je_quelle[q].append(
            Zeile(f"00000000-0000-4000-8000-{i:012d}", serie, folge, 1800, beginn, beginn + dauer, "sicher", dauer, zufall.choice(["pause", "pause", "ende_der_folge", "wechsel"]))
        )
    return je_quelle


def lege_serien(hub) -> None:
    hub.medien.serien.clear()
    for s in range(SERIEN):
        sid = f"serie{s:04d}"
        folgen = [f"f{k:02d}.mp3" for k in range(FOLGEN)]
        serie = Serie(id=sid, name=f"Hörspiel {s:04d}", typ="normal", angelegt_am="2026-01-01T00:00:00Z", folgen=folgen)
        hub.medien.serien[sid] = SerieInfo(serie=serie, ordner=sid, folgen_objekte=[{"name": n, "anzeige": n[:-4]} for n in folgen])


@pytest.fixture
async def gross(hass, integration):
    lege_serien(integration)
    # 30 000 Sitzungen in den letzten 400 Tagen (echte Uhr: gemessen wird die Zeit, die Uhr wird nicht eingefroren)
    je_quelle = erzeuge(ZEILEN, datetime.now(UTC), 400)
    for quelle, liste in je_quelle.items():
        await hass.async_add_executor_job(integration.gehoert.db.nimm_auf, quelle, liste, dt_util.get_default_time_zone())
    assert sum(len(v) for v in je_quelle.values()) == ZEILEN
    return integration


HEUTE = datetime.now(dt_util.get_default_time_zone()).date()
FORMEN = {
    "Rangliste nach Serie, alles": {"nach": ["serie"], "zeitraum": "alles"},
    "Rangliste nach Serie, Jahr": {"nach": ["serie"], "zeitraum": "jahr"},
    "Rangliste nach Serie, Woche": {"nach": ["serie"], "zeitraum": "woche"},
    "Rangliste nach Quelle": {"nach": ["wer"], "zeitraum": "alles"},
    "Aufteilung einer Serie nach Folgen": {"nach": ["folge"], "serie_id": "serie0007", "zeitraum": "alles"},
    "Tage des Jahres": {"nach": ["tag"], "zeitraum": "jahr"},
    "Tage mal Quellen (395 Zeilen)": {"nach": ["tag", "wer"], "von": (HEUTE - timedelta(days=78)).isoformat(), "bis": HEUTE.isoformat()},
    "Wochen, alles": {"nach": ["woche"], "zeitraum": "alles"},
    "Monate, alles": {"nach": ["monat"], "zeitraum": "alles"},
    "Stunden, alles": {"nach": ["stunde"], "zeitraum": "alles"},
    "Tage einer Serie mal Folge": {"nach": ["tag", "folge"], "serie_id": "serie0007", "zeitraum": "monat"},
}


async def messe(client, felder: dict) -> list[float]:
    zeiten = []
    for _ in range(WIEDERHOLUNGEN):
        t0 = time.perf_counter()
        antwort = await ok(client, "gehoert/zusammenfassung", **felder)
        zeiten.append(time.perf_counter() - t0)
        assert antwort["summe"]["sekunden"] >= 0
    return zeiten


async def test_befehl_50_unter_300_ms_bei_30000_zeilen(hass, gross, hass_ws_client):
    client = await hass_ws_client(hass)
    n = await hass.async_add_executor_job(lambda: len(gross.gehoert.db.alle()))
    assert n == ZEILEN
    await messe(client, {"nach": ["serie"], "zeitraum": "alles"})  # Aufwärmen
    ergebnisse = {}
    for name, felder in FORMEN.items():
        zeiten = await messe(client, felder)
        ergebnisse[name] = (statistics.median(zeiten), max(zeiten))
    print("\nBefehl 50 bei 30 000 Zeilen (Median / größter Wert von 7 Aufrufen, in ms)")
    for name, (med, groesst) in ergebnisse.items():
        print(f"  {name:40s} {med * 1000:7.1f} / {groesst * 1000:7.1f}")
    # keine Form darf das Ziel im Median verfehlen
    assert all(med < GRENZE_S for med, _ in ergebnisse.values()), ergebnisse


async def test_befehl_50_waehrend_einer_aufnahme(hass, gross, hass_ws_client):
    client = await hass_ws_client(hass)
    laufend = True
    zaehler = 0

    async def aufnahme():
        nonlocal zaehler
        while laufend:
            zaehler += 1
            z = Zeile(f"11111111-0000-4000-8000-{zaehler:012d}", "serie0001", "f01.mp3", 1800, 1_790_000_000 + zaehler, 1_790_000_100 + zaehler, "sicher", 100, "pause")
            await gross.gehoert.nimm_zeilen_auf("box:box1", [z])
            await asyncio.sleep(0)

    task = hass.async_create_background_task(aufnahme(), "test_aufnahme")
    try:
        await asyncio.sleep(0.05)
        zeiten = await messe(client, {"nach": ["serie"], "zeitraum": "alles"})
        zeiten += await messe(client, FORMEN["Tage mal Quellen (395 Zeilen)"])
    finally:
        laufend = False
        await task
    print(f"\nBefehl 50 während der Aufnahme ({zaehler} Zeilen geschrieben): Median {statistics.median(zeiten) * 1000:.1f} ms, größter Wert {max(zeiten) * 1000:.1f} ms")
    assert zaehler > 10  # die Aufnahme lief wirklich
    assert statistics.median(zeiten) < GRENZE_S
