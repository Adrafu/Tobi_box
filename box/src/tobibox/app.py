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
import dataclasses
import logging
import os
import signal
import sys
import time
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from . import __version__, bootid, core, eventlog, lauf, library, notify, selftest, store
from . import config as konfig_modul
from . import events as ev
from .clock import SystemUhr, Uhr
from .ha_ersatz import HaErsatz
from .outbox import Outbox
from .player import Player
from .reader import Leser
from .sim import Sim
from .sounds import Toene
from .status import Statussammler
from .store import KonfigStore, ResumeStore

TAKT_S = 0.1
VERBINDEN_WARTEN_S = 10.0  # so lange wartet ``starte`` auf MPD, bevor ``Bereit`` kommt
ENDE_WARTEN_S = 5.0
ENV_KONFIG = "TOBIBOX_CONFIG"
STANDARD_KONFIG = "tobibox.toml"
STANDARD_TOENE = Path(__file__).resolve().parents[2] / "sounds"

log = logging.getLogger("tobibox.app")


def _ms(seit: float) -> int:
    return round((time.monotonic() - seit) * 1000)


def _protokolliere_leser(e: ev.Ereignis) -> None:
    """Die Kette des Auflegens und Abhebens ins Ereignisprotokoll (``data-model.md``, 8).

    ``PLACED`` und ``LOCKED`` kommen von der Firmware schon entprellt (``reader-v1.md``); der Dienst
    schreibt deshalb ``aufgelegt`` und ``entprellt`` im selben Augenblick. ``zugeordnet`` und
    ``spielt`` schreibt die Sitzung. Der Zeitstempel von ``aufgelegt`` ist der Startpunkt der
    Messung (``tools/measure_audio_latency.py``).
    """
    if isinstance(e, ev.Aufgelegt):
        eventlog.logge("reader", "INFO", "aufgelegt", "ok", e.vorgang,
                       daten={"uid": e.uid, "typ": e.typ, "tonie": e.tonie, "seq": e.seq})
        eventlog.logge("reader", "INFO", "entprellt", "ok", e.vorgang, daten={"seq": e.seq})
    elif isinstance(e, ev.Gesperrt):
        eventlog.logge("reader", "INFO", "aufgelegt", "ok", e.vorgang, daten={"uid": None, "gesperrt": True, "seq": e.seq})
        eventlog.logge("reader", "INFO", "entprellt", "ok", e.vorgang, daten={"seq": e.seq})
    elif isinstance(e, ev.Abgehoben):
        eventlog.logge("reader", "INFO", "abgehoben", "ok", e.vorgang, daten={"seq": e.seq})


class App:
    def __init__(
        self,
        konfig: konfig_modul.BoxKonfig,
        *,
        uhr: Uhr | None = None,
        melde_bereit: bool = True,
        boot_id: bootid.BootId = bootid.lese,
    ) -> None:
        self.konfig = konfig
        self.uhr: Uhr = uhr or SystemUhr()
        self._melde_bereit = melde_bereit
        self._boot_id = boot_id
        self._marker_uid: str | None = None  # zuletzt in ``lauf.json`` festgehaltener Tobie
        self._letzter_vorgang: str | None = None
        self._herunterfahren = False  # nach Herunterfahren kein Marker mehr
        zustand = konfig.pfade.zustand
        self.resume = ResumeStore(zustand)
        self.konfig_store = KonfigStore(zustand)
        self.bibliothek = library.Bibliothek((), "keine")
        self.outbox = Outbox(zustand)
        self.status = Statussammler()
        self.sim = Sim(zustand, self.ereignisse_ein, self.uhr, self.konfig_store, self.status_auskunft)
        self.ha_ersatz = HaErsatz(self.sim, self.konfig_store, self.ereignisse_ein)
        self._verloren_basis = len(store.verlorene_dateien)  # ``datei_verloren`` zählt erst seit dem Start
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

    def ereignisse_ein(self, e: ev.Ereignis) -> None:
        """Eingang für ``sim`` und den HA-Ersatz (später: MQTT)."""
        self.ereignisse.put_nowait(e)

    def verarbeite(self, e: ev.Ereignis) -> tuple[ev.Befehl, ...]:
        """Ein Ereignis durch den Kern; die Befehle gehen an den Ausführer."""
        jetzt = self.uhr.jetzt()
        _protokolliere_leser(e)
        self.status.beobachte(e, jetzt)
        if isinstance(e, ev.Bestaetigt):
            # Der Broker allein bestätigt nichts; erst ``Bestaetigt`` löscht den Eintrag (Abschnitt 7)
            self.outbox.bestaetigt(e.id, e.grund, e.zuletzt, e.art)
        if isinstance(e, (ev.Aufgelegt, ev.Gesperrt)) or (isinstance(e, ev.Abgehoben) and e.vorgang):
            self._letzter_vorgang = e.vorgang
        self.kern, befehle = core.step(self.kern, e, jetzt)
        for b in befehle:
            self.status.befehl(b, jetzt)
            if isinstance(b, ev.Protokoll):
                # Protokollzeilen sofort schreiben: Sie halten die Entscheidung fest (zugeordnet, spielt) und
                # gehören vor die Ausführung der Befehle derselben Verarbeitung (Kette von CUJ 1, Messung).
                eventlog.logge_befehl(b)
            else:
                self.befehle.put_nowait((b, jetzt.mono))
        self._marker_nachfuehren()
        return befehle

    def _marker_nachfuehren(self) -> None:
        """``lauf.json`` bei jedem Wechsel des liegenden Tobies (Entscheidung G, 06.11.)."""
        if not self._herunterfahren:
            self._marker_uid = lauf.nachfuehren(
                self.konfig.pfade.zustand, self._boot_id(), self.kern.session, self._marker_uid
            )

    async def _ereignisschleife(self) -> None:
        while True:
            e = await self.ereignisse.get()
            try:
                self.verarbeite(e)
            except Exception:  # ein Fehler im Kern darf die Box nicht anhalten
                log.exception("Kern: Ausnahme bei %s", type(e).__name__)
                eventlog.logge("app", "ERROR", "kern_ausnahme", "fehler", daten={"ereignis": type(e).__name__})
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
            vorgang = self._vorgang()
            eventlog.logge("app", "INFO", "pausieren", "gesendet", vorgang, daten={"grund": b.grund})
            t0 = time.monotonic()
            await self.player.pausieren(b)
            eventlog.logge("app", "INFO", "pausieren_fertig", "ok", vorgang, daten={"dauer_ms": _ms(t0)})
        elif isinstance(b, ev.Abspielen):
            eventlog.logge(
                "app", "INFO", "abspielen", "gesendet", b.vorgang,
                daten={"serie": b.serie_id, "folge": b.datei, "track": b.track, "position_s": b.position_s},
            )
            t0 = time.monotonic()
            await self.player.abspielen(b)
            eventlog.logge("app", "INFO", "abspielen_fertig", "ok", b.vorgang, daten={"dauer_ms": _ms(t0)})
        elif isinstance(b, ev.ZeigerSpeichern):
            await asyncio.to_thread(self.resume.speichern, b, mono)
        elif isinstance(b, ev.TonSpielen):
            ton, hinweis = self._tonpegel()
            self.toene.spiele(b.ton, self.grenze, ton, hinweis)
        elif isinstance(b, ev.Protokoll):
            eventlog.logge_befehl(b)  # normalerweise schon in ``verarbeite`` geschrieben
        elif isinstance(b, ev.LeserPing):
            self.leser.ping()
        elif isinstance(b, ev.Herunterfahren):
            self._herunterfahren = True
            lauf.loesche(self.konfig.pfade.zustand)
            eventlog.logge("app", "INFO", "herunterfahren", "angefordert", daten={"grund": b.grund})
        elif isinstance(b, ev.ZustandMelden):
            pass  # der Statussammler hat sie in ``verarbeite`` schon gesehen
        elif isinstance(b, ev.Melden):
            self._melde(b)
        elif isinstance(b, ev.EreignisSenden):
            # Stufe 3a veröffentlicht auf ``tobibox/<box>/event``; bis dahin nur ins Protokoll
            eventlog.logge("app", "INFO", "ereignis_senden", b.art, daten=dict(b.daten))
        elif isinstance(b, ev.StatusPruefen):
            self._status_pruefen(b)
        else:  # Sync, Update: Stufe 3
            eventlog.logge("app", "DEBUG", "befehl_nicht_umgesetzt", "ignoriert", daten={"befehl": type(b).__name__})

    def _melde(self, b: ev.Melden) -> None:
        """Unbekannten oder gelernten Tobie in ``unknown.json`` eintragen (``outbox``)."""
        jetzt = self.uhr.jetzt()
        self.outbox.melden(b.art, b.uid, b.befehl_id, jetzt)
        eventlog.logge("app", "INFO", "gemeldet", b.art, daten={"uid": b.uid, "befehl_id": b.befehl_id})
        if b.art == "gelernt":
            eintrag = next(e for e in self.outbox.offen() if e.uid == b.uid)
            self.ha_ersatz.gelernt(eintrag)  # Stufe 2: ``sim`` spielt HA; Stufe 3a: Veröffentlichung per MQTT

    def pruefbericht(self, jetzt: ev.Jetzt) -> selftest.Pruefbericht:
        """Die vier Prüfpunkte der Status-Karte (12.3). Netz, Leser und Speicher kennt der Dienst, nicht ``selftest``."""
        medien = self.konfig.pfade.medien
        serien = self.bibliothek.serien if medien.is_dir() else None
        frei = selftest.freier_platz_mb(medien if medien.exists() else medien.parent)
        verloren = len(store.verlorene_dateien) > self._verloren_basis
        return selftest.Pruefbericht((
            selftest.pruefe_leser(self.status.leser(jetzt.mono)),
            selftest.pruefe_medien(serien),
            selftest.pruefe_netz(self.status.netz, self.status.ha_verbunden),
            selftest.pruefe_speicher(frei, verloren),
        ))

    def _status_pruefen(self, b: ev.StatusPruefen) -> None:
        """Status-Admin-Karte (CUJ 11): je Prüfpunkt ein Ton, nacheinander."""
        bericht = self.pruefbericht(self.uhr.jetzt())
        eventlog.logge(
            "selftest", "INFO" if bericht.alles_ok else "WARNING", "status_geprueft",
            "ok" if bericht.alles_ok else "fehler", b.vorgang,
            daten={p.name: ("ok" if p.ok else f"FEHLER {p.detail}") for p in bericht.punkte},
        )
        ton, hinweis = self._tonpegel()
        self.toene.spiele_folge(bericht.toene, self.grenze, ton, hinweis)

    def status_auskunft(self) -> dict:
        """Antwort auf ``sim`` ``status`` (für ``tobibox status``): Status-JSON, Prüfpunkte, offene Meldungen."""
        jetzt = self.uhr.jetzt()
        medien = self.konfig.pfade.medien
        frei = selftest.freier_platz_mb(medien if medien.exists() else medien.parent)
        return {
            "status": self.status.als_dict(jetzt, self.bibliothek.serien, frei),
            "pruefpunkte": self.pruefbericht(jetzt).als_dict(),
            "offen": [dataclasses.asdict(e) for e in self.outbox.offen()],
        }

    def _vorgang(self) -> str | None:
        """Vorgangs-ID des letzten Auflegens oder Abhebens (für Zeilen von Befehlen ohne eigene ID)."""
        return self._letzter_vorgang

    async def _ausfuehrer(self) -> None:
        while True:
            b, mono = await self.befehle.get()
            try:
                await self._fuehre_aus(b, mono)
            except Exception as e:  # Ausführung darf die Schlange nicht anhalten
                eventlog.logge("app", "ERROR", "befehl_fehler", "fehler", daten={"befehl": type(b).__name__, "detail": repr(e)})
            finally:
                self.befehle.task_done()

    # ------------------------------------------------------------------
    # Lebenslauf
    # ------------------------------------------------------------------

    def anhalten(self) -> None:
        self._stopp.set()

    async def starte(self) -> None:
        """Daten laden, Kern starten, Leser und Player starten, ``READY=1`` melden."""
        try:
            await self._starte()
        except BaseException:
            eventlog.logge("app", "ERROR", "start", "fehler")
            await self._raeume_auf()
            raise

    async def _starte(self) -> None:
        eventlog.logge("app", "INFO", "start", "ok", daten={"version": __version__})
        self.bibliothek = await asyncio.to_thread(library.lade_bibliothek, self.konfig.pfade.medien)
        self.outbox.laden()  # offene Meldungen (unknown.json) bleiben über den Neustart
        if self.outbox.offen():
            eventlog.logge("app", "INFO", "start", "offene_meldungen", daten={"anzahl": len(self.outbox.offen())})
        self._aufgaben = [
            asyncio.create_task(self._ausfuehrer(), name="tobibox-ausfuehrer"),
            asyncio.create_task(self._ereignisschleife(), name="tobibox-ereignisse"),
        ]
        self.player.start()
        # Reihenfolge wie im Vertrag (3.3): Einstellungen zuerst (daraus entsteht
        # die erste Lautstärke), Leser-Ereignisse erst nach ``Bereit``.
        # Marker mit gleicher Kennung des Starts: Neustart ohne Ausschalten (Entscheidung G, 06.11.)
        neustart_uid = lauf.lese_neustart_uid(self.konfig.pfade.zustand, self._boot_id())
        self._marker_uid = neustart_uid
        if neustart_uid is not None:
            eventlog.logge("app", "INFO", "start", "dienst_neustart", daten={"uid": neustart_uid})
        for e in (
            replace(self.konfig.geraete_einstellungen(), neustart_uid=neustart_uid),
            self.konfig_store.laden(),
            self.bibliothek.ereignis(),
            self.resume.laden(),
        ):
            self.ereignisse.put_nowait(e)
        # Erst wenn MPD verbunden ist (und damit die Lautstärke gilt), kommt ``Bereit``;
        # ohne MPD startet die Box trotzdem (Wiedergabe meldet dann PlayerFehler).
        if not await self.player.warte_verbunden(VERBINDEN_WARTEN_S):
            eventlog.logge("app", "WARNING", "start", "mpd_nicht_verbunden", daten={"timeout_s": VERBINDEN_WARTEN_S})
        self.ereignisse.put_nowait(ev.Bereit())
        await self._leere_ereignisse()
        self.leser.start()
        await self.sim.start()
        self._aufgaben.append(asyncio.create_task(self._taktgeber(), name="tobibox-takt"))
        self.bereit.set()
        if self._melde_bereit:
            notify.bereit()
        eventlog.logge("app", "INFO", "bereit", "ok")

    async def _leere_ereignisse(self) -> None:
        await self.ereignisse.join()

    async def _warte(self, aufruf, name: str, timeout_s: float = ENDE_WARTEN_S) -> None:
        """Einen Schritt des Beendens mit Zeitgrenze; Fehler stoppen die übrigen Schritte nicht."""
        try:
            await asyncio.wait_for(aufruf, timeout_s)
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            eventlog.logge("app", "WARNING", "beende", "zeitueberschreitung", daten={"schritt": name})
        except Exception as e:
            eventlog.logge("app", "ERROR", "beende", "fehler", daten={"schritt": name, "detail": repr(e)})

    async def _raeume_auf(self) -> None:
        """Alles stoppen, jeder Schritt unabhängig: Aufgaben, Player, Töne, Leser."""
        for t in self._aufgaben:
            t.cancel()
        for t in self._aufgaben:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t
        await self._warte(self.player.pausiere_hart(), "pause_hart")
        await self._warte(self.player.stop(), "player")
        await self._warte(self.toene.stop(), "toene")
        await self._warte(self.sim.stop(), "sim")
        await self._warte(self.leser.stop(), "leser")

    async def beende(self) -> None:
        """Sauber beenden: Leser zu, laufende Wiedergabe pausieren und Zeiger sichern.

        Danach geht immer ein harter Pause-Befehl direkt an MPD (auch ohne Serie).
        Auf dem Pi ergänzt die systemd-Unit (AP P.1) ``ExecStopPost`` mit Pause,
        falls der Dienst abstürzt oder diesen Weg nicht mehr erreicht.
        """
        notify.stoppt()
        try:
            await self._warte(self.leser.stop(), "leser")
            await self._warte(self.sim.stop(), "sim")
            for t in self._aufgaben:
                if t.get_name() == "tobibox-takt":
                    t.cancel()
            if self.kern.session.modus in ("spielt", "unbekannt"):
                # Dienst-Ende, nicht Herunterfahren des Geräts
                self.ereignisse.put_nowait(ev.DienstEndet())
                await self._warte(self._leere_ereignisse(), "ereignisse")
            await self._warte(self.befehle.join(), "befehle")
            # Ereignisse aus den letzten Befehlen (frische Position) noch verarbeiten,
            # danach die daraus entstandenen Befehle (Zeiger speichern).
            await self._warte(self._leere_ereignisse(), "ereignisse_nach")
            await self._warte(self.befehle.join(), "befehle_nach")
            self._dienst_ende_marker()
        finally:
            await self._raeume_auf()
            eventlog.logge("app", "INFO", "ende", "ok")

    def _dienst_ende_marker(self) -> None:
        if not self._herunterfahren:
            lauf.dienst_ende(self.konfig.pfade.zustand, self._boot_id(), self.kern.session)

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
