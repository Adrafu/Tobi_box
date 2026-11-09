"""Nie zwei Dinge gleichzeitig (Entscheidung L, 09.11.): Töne und Wiedergabe in der echten ``App``.

Echte Ereignisschleife, echter Ausführer und echte ``Toene``-Spur; ersetzt sind nur MPD (``AufnahmePlayer``)
und das Abspielprogramm (``TonSteuerung``: der Test bestimmt, wann ein Ton zu Ende ist). Ein gemeinsames
Journal hält die Reihenfolge fest: ``ton:<name>:start`` / ``ton:<name>:ende``, ``abspielen <serie>``,
``pausieren``, ``ton_pause_beginn`` / ``ton_pause_ende``, ``zeiger:<grund>``.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import time
from pathlib import Path

import pytest
from fixtures.audio import erzeuge_medien

from tobibox import app as app_modul
from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox import store
from tobibox.app import App
from tobibox.clock import SimUhr
from tobibox.sounds import Toene

BAER = "8c21d5e9a0b7"
RABE = "3f9a1c07b2d4"
BEKANNT = "04a1b2c3"  # Serie Bär
FOLGEN_TOBIE = "04a1b2c5"  # Folge a.wav der Serie Bär (ein Track)
ANDERER = "04a1b2c4"  # Serie Rabe
NEU = "04ffeedd"  # unbekannt


class TonSteuerung:
    """Ersatz für ``afplay``/``aplay``: ein Ton dauert, bis der Test ihn beendet (oder hängt)."""

    def __init__(self, journal: list[str]) -> None:
        self.journal = journal
        self.offen: list[asyncio.Event] = []
        self.laufend = 0
        self.hoechstens = 0
        self.haengt = False

    async def __call__(self, kommando) -> None:
        ton = Path(kommando[-1]).name.split("-")[2]
        tor = asyncio.Event()
        self.offen.append(tor)
        self.laufend += 1
        self.hoechstens = max(self.hoechstens, self.laufend)
        self.journal.append(f"ton:{ton}:start")
        try:
            if not self.haengt:
                await tor.wait()
            else:
                await asyncio.sleep(3600)
            self.journal.append(f"ton:{ton}:ende")
        except asyncio.CancelledError:
            self.journal.append(f"ton:{ton}:abbruch")
            raise
        finally:
            self.laufend -= 1

    def beende(self, n: int = 0) -> None:
        """Den ``n``-ten gestarteten Ton beenden."""
        self.offen[n].set()


class AufnahmePlayer:
    """Ersatz für den ``Player``: schreibt seine Aufrufe ins Journal."""

    def __init__(self, journal: list[str]) -> None:
        self.journal = journal
        self.spielt = False
        self.ton_pause = False

    def start(self):
        pass

    async def warte_verbunden(self, timeout_s=5.0):
        return True

    async def pausiere_hart(self):
        return True

    async def stop(self):
        pass

    async def lautstaerke_setzen(self, *a):
        pass

    async def ausgang_waehlen(self, a):
        pass

    async def abspielen(self, b):
        self.journal.append(f"abspielen {b.serie_id}")
        self.spielt, self.ton_pause = True, False

    async def pausieren(self, b):
        self.journal.append("pausieren")
        self.spielt, self.ton_pause = False, False

    async def ton_pause_beginn(self):
        """Wie der echte Player: nur anhalten, wenn etwas spielt."""
        if not self.spielt or self.ton_pause:
            return False
        self.ton_pause = True
        self.journal.append("ton_pause_beginn")
        return True

    async def ton_pause_ende(self, fortsetzen=True, halten=None):
        """Wie der echte Player: nur fortsetzen, wenn die kurze Pause noch gilt."""
        if not self.ton_pause:
            return False
        if halten is not None and halten():
            return False
        self.ton_pause = False
        if callable(fortsetzen):
            fortsetzen = fortsetzen()
        if fortsetzen:
            self.journal.append("ton_pause_ende fortsetzen")
        else:
            self.journal.append("ton_pause_ende nicht")
        return fortsetzen


class FakeLeser:
    def start(self):
        pass

    async def stop(self):
        pass

    def ping(self):
        pass


class Welt:
    def __init__(self, a: App, journal: list[str], toene: TonSteuerung, zustand: Path) -> None:
        self.app, self.journal, self.ton, self.zustand = a, journal, toene, zustand

    async def sende(self, *ereignisse) -> None:
        for e in ereignisse:
            self.app.ereignisse.put_nowait(e)
        await self.app._leere_ereignisse()
        await self.app.befehle.join()

    async def warte(self, bedingung, text: str = "", timeout: float = 3.0) -> None:
        ende = time.monotonic() + timeout
        while time.monotonic() < ende:
            if bedingung():
                return
            await asyncio.sleep(0.01)
        raise AssertionError(f"nicht rechtzeitig: {text}\n{self.journal}")

    def hat(self, eintrag: str) -> bool:
        return eintrag in self.journal

    def aufgelegt(self, uid: str, vorgang: str = "v1") -> ev.Aufgelegt:
        return ev.Aufgelegt(uid, "ntag", False, 0, vorgang)

    async def ruhe(self, s: float = 0.15) -> None:
        await asyncio.sleep(s)
        await self.app.befehle.join()

    def spielt(self) -> bool:
        return self.app.kern.session.modus == "spielt"


@pytest.fixture
async def welt(tmp_path, monkeypatch, protokoll):
    medien = erzeuge_medien(tmp_path / "medien")
    zustand = tmp_path / "var"
    zustand.mkdir()
    zuordnungen = {
        BEKANNT: ev.Zuordnung("serie", BAER),
        FOLGEN_TOBIE: ev.Zuordnung("folge", BAER, "a.wav"),
        ANDERER: ev.Zuordnung("serie", RABE),
    }
    k = ev.Konfig(1, "a3f9c1e07b2d4856", zuordnungen, ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60))
    store.schreibe_atomar(zustand / "config.json", store.konfig_zu_json(k))
    toml = tmp_path / "tobibox.toml"
    toml.write_text(f'[pfade]\nzustand = "{zustand}"\nmedien = "{medien}"\n[leser]\ngeraet = "sim"\n', encoding="utf-8")
    monkeypatch.setattr(app_modul.notify, "stoppt", lambda: None)
    journal: list[str] = []
    steuerung = TonSteuerung(journal)
    a = App(konfig_modul.lade(toml), uhr=SimUhr(), melde_bereit=False)
    a.player = AufnahmePlayer(journal)
    a.leser = FakeLeser()
    a.toene = Toene(app_modul.STANDARD_TOENE, ["tonprogramm", "{datei}"], starter=steuerung, vor=a._ton_vor, nach=a._ton_nach)
    gespeichert = a.resume.speichern

    def speichern(b, mono):
        journal.append(f"zeiger:{b.grund}")
        return gespeichert(b, mono)

    monkeypatch.setattr(a.resume, "speichern", speichern)
    await a.starte()
    # der Startton (Bereit) ist ein Ton wie jeder andere: beenden und aus dem Journal nehmen
    await a.befehle.join()
    while a.toene.beschaeftigt:
        for tor in steuerung.offen:
            tor.set()
        await asyncio.sleep(0.01)
    journal.clear()
    steuerung.offen.clear()
    steuerung.hoechstens = 0
    yield Welt(a, journal, steuerung, zustand)
    for tor in steuerung.offen:
        tor.set()
    await a.beende()


def nie_gleichzeitig(journal: list[str]) -> None:
    """Zwischen ``ton:x:start`` und ``ton:x:ende`` (oder ``abbruch``) darf nichts anderes spielen."""
    laeuft = None
    for z in journal:
        if z.startswith("ton:") and z.endswith(":start"):
            assert laeuft is None, journal
            laeuft = z
        elif z.startswith("ton:") and (z.endswith(":ende") or z.endswith(":abbruch")):
            laeuft = None
        elif z.startswith("abspielen"):
            assert laeuft is None, f"Start mitten im Ton: {journal}"


# --- Ton vor Hörspiel ----------------------------------------------------------------------------


async def test_ton_und_abspielen_in_einer_ausgabe_start_erst_nach_dem_ende_des_tons(welt):
    """Unbekannter Tobie: ``unbekannt`` und Überraschungs-Serie kommen aus demselben Kern-Aufruf."""
    welt.app.ereignisse.put_nowait(welt.aufgelegt(NEU))
    await welt.warte(lambda: welt.hat("ton:unbekannt:start"), "Ton beginnt")
    await welt.ruhe(0.3)
    assert not any(z.startswith("abspielen") for z in welt.journal)  # der Ton läuft noch
    assert welt.spielt()  # der Kern hat entschieden; die Ausführung wartet
    welt.ton.beende(0)
    await welt.warte(lambda: any(z.startswith("abspielen") for z in welt.journal), "Start nach dem Ton")
    assert welt.journal == ["ton:unbekannt:start", "ton:unbekannt:ende", "abspielen c07d2e91a45b"]
    nie_gleichzeitig(welt.journal)


async def test_lernmodus_ende_ton_vor_der_folge(welt):
    """Lernmodus: ``lernen_beginn``, dann ``lernen_ende`` und das Lernziel; nie gleichzeitig."""
    e = await welt.app.sim.zeile_zu_ereignis_async(json.dumps({"befehl": "learn", "typ": "serie", "serie": BAER, "ttl": 60}))
    welt.app.sim.ausgabe(e)
    await welt.warte(lambda: welt.hat("ton:lernen_beginn:start"), "Lernton")
    welt.ton.beende(0)
    await welt.warte(lambda: welt.hat("ton:lernen_beginn:ende"))
    welt.app.ereignisse.put_nowait(welt.aufgelegt(NEU))
    await welt.warte(lambda: welt.hat("ton:lernen_ende:start"), "Ende-Ton")
    await welt.ruhe(0.3)
    assert not any(z.startswith("abspielen") for z in welt.journal)
    welt.ton.beende(1)
    await welt.warte(lambda: any(z.startswith("abspielen") for z in welt.journal), "Lernziel startet")
    assert welt.journal[-3:] == ["ton:lernen_ende:start", "ton:lernen_ende:ende", f"abspielen {BAER}"]
    nie_gleichzeitig(welt.journal)


async def test_mehrere_toene_nacheinander_dann_der_start(welt):
    """Töne aus verschiedenen Ausgaben laufen nie gleichzeitig; ein Start wartet auf alle."""
    assert welt.app.toene.spiele("hinweis", 50, 20)
    assert welt.app.toene.spiele_folge(["start", "fehler"], 50, 20)
    welt.app.ereignisse.put_nowait(welt.aufgelegt(BEKANNT))  # bekannter Tobie, aber die Spur ist belegt
    await welt.warte(lambda: welt.hat("ton:hinweis:start"))
    await welt.ruhe(0.2)
    assert welt.journal == ["ton:hinweis:start"]  # nur einer zur Zeit
    for n in range(2):  # hinweis, dann die Folge start+fehler als ein Prozess
        await welt.warte(lambda n=n: len(welt.ton.offen) > n, f"Ton {n} beginnt")
        welt.ton.beende(n)
        await welt.ruhe(0.05)
    await welt.warte(lambda: welt.hat(f"abspielen {BAER}"), "Start nach der Tonfolge")
    assert [z for z in welt.journal if z.endswith(":start")] == ["ton:hinweis:start", "ton:start:start"]  # start+fehler: ein Prozess
    assert welt.journal[-1] == f"abspielen {BAER}"
    assert welt.ton.hoechstens == 1
    nie_gleichzeitig(welt.journal)


def test_toene_stehen_in_der_warteschlange_vor_dem_start():
    """Nur die Töne rücken vor ``Abspielen``; alles andere behält seine Reihenfolge (Rang 6.4)."""
    a = ev.Abspielen("s", "o", "d", ("d",), 0, 0.0, "v", 3)
    z = ev.ZeigerSpeichern("serie", "s", "d", 0, 0, 1.0, "pause")
    p = ev.Pausieren("abgehoben")
    t = ev.TonSpielen("unbekannt")
    m = ev.Melden("unbekannt", "04ff", None)
    s = ev.StatusPruefen("v")
    assert App._toene_vor_start([p, z, a, t, m]) == [p, z, t, a, m]
    assert App._toene_vor_start([a, t, s, m]) == [t, s, a, m]
    ohne_start = [p, t, m]
    assert App._toene_vor_start(ohne_start) == ohne_start
    ohne_ton = [p, z, a, m]
    assert App._toene_vor_start(ohne_ton) == ohne_ton


# --- Ton während das Hörspiel läuft -----------------------------------------------------------------


async def test_ton_waehrend_der_wiedergabe_pausiert_und_setzt_fort_ohne_zeiger(welt):
    await welt.sende(welt.aufgelegt(FOLGEN_TOBIE))
    assert welt.journal == [f"abspielen {BAER}"]  # kein Ton, kein Umweg
    welt.journal.clear()
    # Weiter am letzten Track eines Folgen-Tobies: der Hinweiston, das Hörspiel läuft
    await welt.sende(ev.Weiter())
    await welt.warte(lambda: welt.hat("ton:hinweis:start"), "Hinweiston")
    assert welt.journal == ["ton_pause_beginn", "ton:hinweis:start"]  # erst anhalten, dann der Ton
    assert welt.spielt()  # der Kern kennt keine Pause
    welt.ton.beende(0)
    await welt.warte(lambda: welt.hat("ton_pause_ende fortsetzen"), "Fortsetzen")
    assert welt.journal == ["ton_pause_beginn", "ton:hinweis:start", "ton:hinweis:ende", "ton_pause_ende fortsetzen"]
    await welt.ruhe(0.2)
    assert not any(z.startswith(("abspielen", "pausieren", "zeiger")) for z in welt.journal)  # kein neuer Start, kein Zeiger
    assert welt.spielt()
    assert not (welt.zustand / "resume.json").exists()


async def test_eine_tonfolge_pausiert_nur_einmal(welt):
    await welt.sende(welt.aufgelegt(FOLGEN_TOBIE))
    welt.journal.clear()
    welt.app.toene.spiele("hinweis", 50, 20)
    welt.app.toene.spiele("fehler", 50, 20)
    await welt.warte(lambda: welt.hat("ton:hinweis:start"))
    welt.ton.beende(0)
    await welt.warte(lambda: len(welt.ton.offen) == 2)
    welt.ton.beende(1)
    await welt.warte(lambda: welt.hat("ton_pause_ende fortsetzen"))
    assert welt.journal.count("ton_pause_beginn") == 1 and welt.journal.count("ton_pause_ende fortsetzen") == 1


# --- Abheben und andere Befehle während eines Tons --------------------------------------------------


async def test_abheben_waehrend_des_tons_kein_start_der_ton_laeuft_zu_ende(welt):
    welt.app.ereignisse.put_nowait(welt.aufgelegt(NEU))
    await welt.warte(lambda: welt.hat("ton:unbekannt:start"))
    await welt.sende(ev.Abgehoben(1, "v1"))
    assert "pausieren" in welt.journal
    assert not welt.hat("ton:unbekannt:abbruch")  # der Ton wird nicht abgebrochen
    welt.ton.beende(0)
    await welt.warte(lambda: welt.hat("ton:unbekannt:ende"), "Ton läuft zu Ende")
    await welt.ruhe(0.3)
    assert not any(z.startswith("abspielen") for z in welt.journal)
    assert welt.app._start is None
    assert welt.app.kern.session.modus == "pausiert"


async def test_neuer_start_ersetzt_den_wartenden_start(welt):
    """Anderer Tobie während des Tons: nur der neue Start läuft, der alte ist verworfen."""
    welt.app.ereignisse.put_nowait(welt.aufgelegt(NEU, "v1"))
    await welt.warte(lambda: welt.hat("ton:unbekannt:start"))
    await welt.sende(ev.Abgehoben(1, "v1"), welt.aufgelegt(ANDERER, "v2"))
    welt.ton.beende(0)
    await welt.warte(lambda: any(z.startswith("abspielen") for z in welt.journal))
    await welt.ruhe(0.2)
    assert [z for z in welt.journal if z.startswith("abspielen")] == [f"abspielen {RABE}"]
    nie_gleichzeitig(welt.journal)


async def test_pausieren_ueberholt_keinen_verzoegerten_start(welt):
    """Hauptknopf während des Tons: die Pause gewinnt, der Start wird nie ausgeführt."""
    welt.app.ereignisse.put_nowait(welt.aufgelegt(NEU))
    await welt.warte(lambda: welt.hat("ton:unbekannt:start"))
    await welt.sende(ev.Hauptknopf("kurz"))
    assert welt.hat("pausieren")
    assert welt.app._start is None  # verworfen, nicht nur vertagt
    welt.ton.beende(0)
    await welt.warte(lambda: welt.hat("ton:unbekannt:ende"))
    await welt.ruhe(0.3)
    assert not any(z.startswith("abspielen") for z in welt.journal)
    assert welt.journal.index("pausieren") < welt.journal.index("ton:unbekannt:ende")


async def test_veralteter_start_wird_vor_dem_start_geprueft(welt):
    """Der Kern hat sich geändert, die Pause steckt aber noch in der Warteschlange: der Start gilt nicht mehr.

    ``gen`` allein reicht nicht (Abheben erhöht sie nicht); deshalb prüft der Start auch den Modus."""
    welt.app.ereignisse.put_nowait(welt.aufgelegt(NEU))
    await welt.warte(lambda: welt.hat("ton:unbekannt:start"))
    start = welt.app._start
    assert start is not None and start.befehl.gen == welt.app.kern.session.gen
    assert welt.app._start_gueltig(start.befehl) is None
    # Fall 1: eine neuere Generation (an der Warteschlange vorbei gesetzt)
    teil = {**welt.app.kern.teil, "session": dataclasses.replace(welt.app.kern.session, gen=start.befehl.gen + 1)}
    welt.app.kern = dataclasses.replace(welt.app.kern, teil=teil)
    assert welt.app._start_gueltig(start.befehl) == "gen_veraltet"
    # Fall 2: gleiche Generation, aber der Kern pausiert
    teil = {**welt.app.kern.teil, "session": dataclasses.replace(welt.app.kern.session, gen=start.befehl.gen, modus="pausiert")}
    welt.app.kern = dataclasses.replace(welt.app.kern, teil=teil)
    assert welt.app._start_gueltig(start.befehl) == "nicht_mehr_spielt"
    welt.ton.beende(0)
    await welt.warte(lambda: welt.hat("ton:unbekannt:ende"))
    await welt.ruhe(0.3)
    assert not any(z.startswith("abspielen") for z in welt.journal)


async def test_pause_waehrend_des_tons_wird_nach_dem_ton_nicht_fortgesetzt(welt):
    """Ton während der Wiedergabe, dann Abheben: der Player setzt nicht fort (Haken ``nach``)."""
    await welt.sende(welt.aufgelegt(FOLGEN_TOBIE))
    welt.journal.clear()
    await welt.sende(ev.Weiter())
    await welt.warte(lambda: welt.hat("ton:hinweis:start"))
    await welt.sende(ev.Abgehoben(1, "v1"))
    welt.ton.beende(0)
    await welt.warte(lambda: welt.hat("ton:hinweis:ende"))
    await welt.ruhe(0.2)
    assert "pausieren" in welt.journal
    assert "ton_pause_ende fortsetzen" not in welt.journal
    assert not any(z.startswith("abspielen") for z in welt.journal)


async def test_tobie_wechsel_mit_ton_das_alte_hoerspiel_laeuft_nicht_in_den_ton(welt):
    """Anderer Tobie (unbekannt) legt sich auf, während ein Hörspiel läuft: erst Ruhe, dann Ton, dann der neue Start."""
    await welt.sende(welt.aufgelegt(BEKANNT, "v1"))
    welt.journal.clear()
    welt.app.ereignisse.put_nowait(welt.aufgelegt(NEU, "v2"))
    await welt.warte(lambda: welt.hat("ton:unbekannt:start"))
    ton = welt.journal.index("ton:unbekannt:start")
    assert "pausieren" in welt.journal[:ton] or "ton_pause_beginn" in welt.journal[:ton]  # das alte Hörspiel ist still
    welt.ton.beende(0)
    await welt.warte(lambda: welt.hat("abspielen c07d2e91a45b"))
    assert "ton_pause_ende fortsetzen" not in welt.journal  # das alte Hörspiel kommt nicht zurück
    nie_gleichzeitig(welt.journal)


# --- Zeitlimit --------------------------------------------------------------------------------------


async def test_haengender_ton_blockiert_den_start_nicht_laenger_als_das_zeitlimit(welt):
    welt.ton.haengt = True
    welt.app.toene.ton_max_s = 0.3
    t0 = time.monotonic()
    welt.app.ereignisse.put_nowait(welt.aufgelegt(NEU))
    await welt.warte(lambda: any(z.startswith("abspielen") for z in welt.journal), "Start trotz hängendem Ton")
    dauer = time.monotonic() - t0
    assert 0.25 <= dauer < 1.5, dauer
    assert welt.journal == ["ton:unbekannt:start", "ton:unbekannt:abbruch", "abspielen c07d2e91a45b"]
    assert welt.app.toene.ton_max_s == 0.3
    assert not welt.app.toene.beschaeftigt


def test_zeitlimit_pro_ton_ist_zehn_sekunden():
    from tobibox import sounds

    assert sounds.TON_MAX_S == 10.0
    assert Toene(".", ["x"]).ton_max_s == 10.0


# --- Zeitbudget -------------------------------------------------------------------------------------


async def test_normales_auflegen_ohne_ton_startet_sofort_ohne_umweg(welt):
    """Bekannter Tobie, keine Tonspur belegt: ``Abspielen`` läuft direkt im Ausführer (Ziel unter 1 s)."""
    angelegt: list[asyncio.Task] = []
    loop = asyncio.get_running_loop()
    orig = loop.create_task

    def create_task(coro, **kw):
        t = orig(coro, **kw)
        angelegt.append(t)
        return t

    loop.create_task = create_task  # type: ignore[method-assign]
    try:
        t0 = time.monotonic()
        welt.app.ereignisse.put_nowait(welt.aufgelegt(BEKANNT))
        await welt.warte(lambda: welt.hat(f"abspielen {BAER}"), "Start", timeout=1.0)
        dauer = time.monotonic() - t0
    finally:
        loop.create_task = orig  # type: ignore[method-assign]
    assert welt.journal == [f"abspielen {BAER}"]  # nichts davor, nichts dazwischen
    assert dauer < 0.25, dauer  # nur die Verarbeitung, kein Warten auf eine Spur
    assert not any(t.get_name() == "tobibox-start" for t in angelegt)  # kein verzögerter Start
    assert welt.app._start is None and not welt.app.toene.beschaeftigt and welt.ton.offen == []
