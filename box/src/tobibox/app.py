"""Einziger Zusammenbau-Punkt: baut Uhr und Module und verdrahtet sie.

reader / player -> Ereignisschlange -> ``core.step`` -> Befehle -> Ausführer.
Der Takt (``TAKT_S`` = 0,1 s) kommt von hier. Befehle laufen in der gegebenen
Reihenfolge in einer eigenen Aufgabe, damit die Ereignisschleife nie auf MPD
oder die Platte wartet (``core-interface.md``, 6.5).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import os
import signal
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, core, eventlog, library, notify
from . import config as konfig_modul
from . import events as ev
from .clock import SystemUhr, Uhr
from .player import Player
from .reader import Leser
from .sounds import Toene
from .store import KonfigStore, ResumeStore

TAKT_S = 0.1
ENV_KONFIG = "TOBIBOX_CONFIG"
STANDARD_KONFIG = "tobibox.toml"
STANDARD_TOENE = Path(__file__).resolve().parents[2] / "sounds"

log = logging.getLogger("tobibox.app")


class App:
    def __init__(
        self,
        konfig: konfig_modul.BoxKonfig,
        *,
        uhr: Uhr | None = None,
        melde_bereit: bool = True,
    ) -> None:
        self.konfig = konfig
        self.uhr: Uhr = uhr or SystemUhr()
        self._melde_bereit = melde_bereit
        zustand = konfig.pfade.zustand
        self.resume = ResumeStore(zustand)
        self.konfig_store = KonfigStore(zustand)
        self.bibliothek = library.Bibliothek((), "keine")
        self.kern = core.neuer_zustand()
        self.ereignisse: asyncio.Queue[ev.Ereignis] = asyncio.Queue()
        self.befehle: asyncio.Queue[tuple[ev.Befehl, float]] = asyncio.Queue()
        self.player = Player(
            self.ereignisse.put_nowait, konfig.mpd.host, konfig.mpd.port, medien=konfig.pfade.medien
        )
        self.leser = Leser(self.ereignisse.put_nowait, konfig.leser.geraet)
        self.toene = Toene(konfig.toene.ordner or STANDARD_TOENE, konfig.toene.kommando)
        self.grenze = konfig.lautstaerke.max  # zuletzt ausgegebene wirksame Grenze
        self.bereit = asyncio.Event()
        self._stopp = asyncio.Event()
        self._aufgaben: list[asyncio.Task] = []

    # ------------------------------------------------------------------
    # Kern
    # ------------------------------------------------------------------

    def verarbeite(self, e: ev.Ereignis) -> tuple[ev.Befehl, ...]:
        """Ein Ereignis durch den Kern; die Befehle gehen an den Ausführer."""
        jetzt = self.uhr.jetzt()
        self.kern, befehle = core.step(self.kern, e, jetzt)
        for b in befehle:
            self.befehle.put_nowait((b, jetzt.mono))
        return befehle

    async def _ereignisschleife(self) -> None:
        while True:
            e = await self.ereignisse.get()
            try:
                self.verarbeite(e)
            except Exception:  # ein Fehler im Kern darf die Box nicht anhalten
                log.exception("Kern: Ausnahme bei %s", type(e).__name__)
                eventlog.logge("app", "ERROR", "kern_ausnahme", "fehler", ereignis=type(e).__name__)
            finally:
                self.ereignisse.task_done()

    async def _taktgeber(self) -> None:
        loop = asyncio.get_running_loop()
        naechster = loop.time() + TAKT_S
        while True:
            await asyncio.sleep(max(0.0, naechster - loop.time()))
            self.ereignisse.put_nowait(ev.Takt())
            naechster += TAKT_S
            if naechster < loop.time():  # nach langem Stillstand nicht aufholen
                naechster = loop.time() + TAKT_S

    # ------------------------------------------------------------------
    # Befehle ausführen
    # ------------------------------------------------------------------

    def _tonpegel(self) -> tuple[int | None, int | None]:
        """``ton_pegel``/``hinweis_pegel`` aus der Rohkonfiguration (``Konfig`` hat sie nicht)."""
        roh = self.konfig_store.roh

        def zahl(name: str) -> int | None:
            w = roh.get(name)
            return w if isinstance(w, int) and not isinstance(w, bool) and 0 <= w <= 100 else None

        return zahl("ton_pegel"), zahl("hinweis_pegel")

    async def _fuehre_aus(self, b: ev.Befehl, mono: float) -> None:
        if isinstance(b, ev.LautstaerkeSetzen):
            self.grenze = b.grenze
            await self.player.lautstaerke_setzen(b.prozent, b.grenze)
        elif isinstance(b, ev.AusgangWaehlen):
            await self.player.ausgang_waehlen(b.ausgang)
        elif isinstance(b, ev.Pausieren):
            await self.player.pausieren(b)
        elif isinstance(b, ev.Abspielen):
            await self.player.abspielen(b)
        elif isinstance(b, ev.ZeigerSpeichern):
            await asyncio.to_thread(self.resume.speichern, b, mono)
        elif isinstance(b, ev.TonSpielen):
            ton, hinweis = self._tonpegel()
            self.toene.spiele(b.ton, self.grenze, ton, hinweis)
        elif isinstance(b, ev.Protokoll):
            eventlog.logge_befehl(b)
        elif isinstance(b, ev.LeserPing):
            self.leser.ping()
        elif isinstance(b, ev.Herunterfahren):
            eventlog.logge("app", "INFO", "herunterfahren", "angefordert", grund=b.grund)
        elif isinstance(b, ev.ZustandMelden):
            pass  # Anzeige und Statussammler folgen in Stufe 2
        else:  # Melden, EreignisSenden, StatusPruefen, Sync, Update: Stufe 2 bis 3
            eventlog.logge("app", "DEBUG", "befehl_nicht_umgesetzt", "ignoriert", befehl=type(b).__name__)

    async def _ausfuehrer(self) -> None:
        while True:
            b, mono = await self.befehle.get()
            try:
                await self._fuehre_aus(b, mono)
            except Exception as e:  # Ausführung darf die Schlange nicht anhalten
                eventlog.logge("app", "ERROR", "befehl_fehler", "fehler", befehl=type(b).__name__, detail=repr(e))
            finally:
                self.befehle.task_done()

    # ------------------------------------------------------------------
    # Lebenslauf
    # ------------------------------------------------------------------

    def anhalten(self) -> None:
        self._stopp.set()

    async def starte(self) -> None:
        """Daten laden, Kern starten, Leser und Player starten, ``READY=1`` melden."""
        eventlog.logge("app", "INFO", "start", "ok", version=__version__)
        self.bibliothek = await asyncio.to_thread(library.lade_bibliothek, self.konfig.pfade.medien)
        self._aufgaben = [
            asyncio.create_task(self._ausfuehrer(), name="tobibox-ausfuehrer"),
            asyncio.create_task(self._ereignisschleife(), name="tobibox-ereignisse"),
        ]
        self.player.start()
        # Reihenfolge wie im Vertrag (3.3): Einstellungen zuerst (daraus entsteht
        # die erste Lautstärke), Leser-Ereignisse erst nach ``Bereit``.
        start = (
            self.konfig.geraete_einstellungen(),
            self.konfig_store.laden(),
            self.bibliothek.ereignis(),
            self.resume.laden(),
            ev.Bereit(),
        )
        for e in start:
            self.ereignisse.put_nowait(e)
        await self._leere_ereignisse()
        self.leser.start()
        self._aufgaben.append(asyncio.create_task(self._taktgeber(), name="tobibox-takt"))
        self.bereit.set()
        if self._melde_bereit:
            notify.bereit()
        eventlog.logge("app", "INFO", "bereit", "ok")

    async def _leere_ereignisse(self) -> None:
        await self.ereignisse.join()

    async def beende(self) -> None:
        """Sauber beenden: Leser zu, laufende Wiedergabe pausieren und Zeiger sichern."""
        notify.stoppt()
        await self.leser.stop()
        for t in self._aufgaben:
            if t.get_name() == "tobibox-takt":
                t.cancel()
        if self.kern.session.modus == "spielt":
            self.ereignisse.put_nowait(ev.HerunterfahrenAngefordert("hauptknopf"))
            await self._leere_ereignisse()
        await asyncio.wait_for(self.befehle.join(), 5.0)
        for t in self._aufgaben:
            t.cancel()
        for t in self._aufgaben:
            with contextlib.suppress(asyncio.CancelledError):
                await t
        await self.player.stop()
        await self.toene.stop()
        eventlog.logge("app", "INFO", "ende", "ok")

    async def laufe(self) -> None:
        """Starten, auf SIGTERM/SIGINT warten, sauber beenden."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            with contextlib.suppress(NotImplementedError, RuntimeError):
                loop.add_signal_handler(sig, self.anhalten)
        await self.starte()
        await self._stopp.wait()
        with contextlib.suppress(asyncio.TimeoutError):
            await self.beende()


def baue_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tobiboxd", description="Box-Dienst der Tobi Box")
    p.add_argument("--version", action="version", version=f"tobiboxd {__version__}")
    p.add_argument("--config", help=f"tobibox.toml (sonst ${ENV_KONFIG} oder ./{STANDARD_KONFIG})")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = baue_parser().parse_args(argv)
    pfad = Path(args.config or os.environ.get(ENV_KONFIG) or STANDARD_KONFIG)
    try:
        konfig = konfig_modul.lade(pfad)
    except konfig_modul.KonfigFehler as e:
        print(f"tobiboxd: {e}", file=sys.stderr)
        return 2
    p = konfig.protokoll
    eventlog.einrichten(ziel=p.ziel, datei=p.datei, ebene=p.ebene, max_bytes=p.max_bytes, anzahl=p.anzahl)
    konfig.pfade.zustand.mkdir(parents=True, exist_ok=True)
    asyncio.run(App(konfig).laufe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
