"""Einziger Zusammenbau-Punkt: baut Uhr und Module und verdrahtet sie.

reader / player -> Ereignisschlange -> ``core.step`` -> Befehle -> Ausführer.
Der Takt (``TAKT_S`` = 0,1 s) kommt von hier. Befehle laufen in der gegebenen
Reihenfolge in einer eigenen Aufgabe, damit die Ereignisschleife nie auf MPD
oder die Platte wartet (``core-interface.md``, 6.5).

Nie zwei Dinge gleichzeitig (Entscheidung L, 09.11.; ``core-interface.md``, 8.1 und 6.5):

* **Ton vor Hörspiel.** Enthält eine Ausgabe Töne und ``Abspielen``, geben die Töne zuerst an die Tonspur
  (``verarbeite`` stellt sie in der Warteschlange vor das ``Abspielen``). Das Hörspiel startet erst, wenn die
  Spur leer ist, also nach dem Ende des letzten Tons. Läuft kein Ton, startet es sofort und ohne Umweg.
* **Der Ausführer wartet nie auf einen Ton.** Ein verzögerter Start ist eine eigene Aufgabe (``_Start``). Ein
  späteres ``Pausieren`` oder ``Abspielen`` verwirft ihn, solange er noch wartet; zusätzlich prüft er vor dem
  Start, ob die Wiedergabe-Generation ``gen`` und der Zustand des Kerns noch zu ihm passen.
* **Ton während das Hörspiel läuft.** Die Tonspur hält MPD kurz an und setzt es danach fort
  (``Player.ton_pause_beginn`` / ``ton_pause_ende``), ohne dass der Kern es erfährt.

Stufe 3a (AP 3.7): HA, Netz, Strom und Sync hängen hier im Dienst.

* ``[mqtt]`` da: ``Ha`` spricht MQTT. Es veröffentlicht die Meldungen (``Ausgang.melde_async``, danach ``ha.melde``), führt
  ``EreignisSenden`` aus und gibt Konfiguration, Befehle und ``Bestaetigt`` in die Ereignisschleife. Der HA-Ersatz der Stufe 2
  schweigt dann. Ohne ``[mqtt]`` bleibt er aktiv (Mac ohne Broker).
* ``[netz]`` und ``[strom]``: ``Netz`` und ``Power`` messen und senden ``NetzKlasse``, ``AkkuStand``, ``LaderGeaendert`` und
  die Zeitquelle (geteiltes ``Zeitquelle``-Objekt). ``ZeitquelleGeaendert`` stellt die Uhr (``setze_quelle``).
* ``[sync]``: ``Sync`` bekommt Netz-Klasse, Lader und Akku, ``Takt`` für den zeitgesteuerten Start, ``SyncStarten`` und
  ``SyncAbbrechen`` aus dem Kern. Nach einem Sync lädt ``app`` die Bibliothek neu (``BibliothekGeladen``).
* ``SyncFortschritt`` (Ereignis von ``sync``, nicht im Vertrag) geht nur an den Statussammler und die Anzeige, nie in den Kern.

Stufe 4 (AP 4.8): Hardware-Funktionen, am Mac mit Simulation hinter derselben Schnittstelle.

* **LED-Ring:** ``LedLogik`` bekommt jedes ``ZustandMelden`` und die Strom-Ereignisse (``beobachte``). Alle ``LED_TAKT_S`` rechnet
  ``_led_lauf`` das Bild: in die Anzeige (``anzeige.ring``, Feld ``farben``), ins Protokoll (nur bei Wechsel des Ring-Zustands)
  und als eine Zeile ins Terminal (nur wenn ``stderr`` ein Terminal ist oder ``ring_ausgabe`` gesetzt ist).
* **Tasten und Drehregler:** ``Bedienung`` (``[tasten]``). Am Pi hängt ``GpioTreiber`` daran (``quelle = "gpio"``); am Mac kommen die
  Eingänge von ``tobibox sim``. ``setze_lautstaerke`` führt Wunsch und Grenze des Kerns nach jedem Schritt nach.
* **Kopfhörer:** ``Buchse`` (``[kopfhoerer]``) mit ``SimKopfhoerer`` oder ``GpioKopfhoerer``. Die erste Messung kommt nach
  ``GeraeteEinstellungen`` (die Kopfhörer-Grenze ist dann bekannt) und vor ``Bereit`` (der Startton klingt schon mit der richtigen Grenze).
* **Leerlauf:** ``HerunterfahrenAngefordert`` bleibt im Kern; der Befehl ``Herunterfahren`` geht wie in AP 3.7 an ``power.fuehre_aus``.
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
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from . import __version__, bootid, core, eventlog, fruehton, lauf, library, nachfuehrung, notify, selftest, store, uhrregel
from . import config as konfig_modul
from . import events as ev
from .clock import SystemUhr, Uhr
from .ausgang import Ausgang
from .controls import Bedienung, GpioTreiber
from .ha import Ha
from .headphones import Buchse, GpioKopfhoerer, SimKopfhoerer
from .led import DECKEL_PROZENT, LedLogik
from .net import Netz, SimSsid, TimedatectlNtp, Zeitquelle
from .player import Player
from .power import Power, SimStrom
from .reader import Leser
from .sounds import Kennlinie, Toene
from .status import Statussammler
from .sync import MpdHaken, Sync, SyncFortschritt
from .volume import wirksame_grenze
from .store import KonfigStore, ResumeStore, raeume_auf

TAKT_S = 0.1
LED_TAKT_S = 0.1  # Ring neu rechnen und zeigen (Atmen, Blinken, Lauflicht)
VERBINDEN_WARTEN_S = 10.0  # so lange wartet ``starte`` auf MPD, bevor ``Bereit`` kommt
ENDE_WARTEN_S = 5.0
ABBRUCH_SYNC_WARTEN_S = 15.0  # ``sync`` wartet nach SIGTERM bis zu 10 s auf rsync
#: ``[netz] quelle = "sim"`` ohne eigene Namen: Mit diesen WLAN-Namen bildet ``tobibox sim net`` die Klassen ab.
SIM_HEIM_SSID = "sim-heim"
SIM_HOTSPOT_SSID = "sim-hotspot"
#: Start-Sync am Lader, solange die Netz-Klasse noch unbekannt ist: so lange wartet ``App`` auf die erste ``NetzKlasse`` (B7).
NETZ_KLASSE_WARTEN_S = 30.0
#: Pi ohne ``[netz]`` und ``[strom]``: so oft prüft ``App`` die NTP-Synchronisierung der Systemuhr (B15).
SYSTEMUHR_PRUEFEN_S = 10.0
#: Steht die Marke des Frühtons auf ``start``, wartet ``App`` mit jedem Ton des Kerns bis ``fertig``, höchstens so lange ab ``Bereit`` (Ein/Aus, 10.11.).
FRUEHTON_WARTEN_S = 3.0
FRUEHTON_PRUEFEN_S = 0.1
#: Vor dem Herunterfahren wartet ``App`` höchstens so lange auf den Ton ``akku_leer`` (B12).
TON_VOR_HERUNTERFAHREN_S = 5.0
UPDATE_NOCH_NICHT_TEXT = "Update kommt mit Stufe 3b."
ENV_KONFIG = "TOBIBOX_CONFIG"
STANDARD_KONFIG = "tobibox.toml"
STANDARD_TOENE = Path(__file__).resolve().parents[2] / "sounds"

log = logging.getLogger("tobibox.app")


@dataclass(slots=True)
class _Start:
    """Ein ``Abspielen``, das auf das Ende der Töne wartet (Entscheidung L)."""

    befehl: ev.Abspielen
    task: asyncio.Task | None = None
    wartet: bool = True  # ``False``, sobald der Start wirklich beginnt: dann nicht mehr abbrechen


def _ring_zeile(r) -> str:  # type: ignore[no-untyped-def]
    """Der Ring als eine Zeile: Zustand, Helligkeit und zehn Farbpunkte (ANSI-Truecolor), gerundet auf ganze Prozent."""
    # Farben auf den Deckel bezogen (volle Farbe bei 25 %), sonst wären die Punkte im Terminal kaum zu sehen
    f = min(1.0, r.helligkeit / DECKEL_PROZENT)
    punkte = "".join(
        f"\x1b[38;2;{round(c[0] * f)};{round(c[1] * f)};{round(c[2] * f)}m\u25cf" for c in r.leds[::4]
    )
    return f"Ring: {r.zustand:<16} {round(r.helligkeit):3d} %  {punkte}\x1b[0m"


def _terminal_zeile(text: str) -> None:
    """Eine Zeile im Terminal, die sich selbst überschreibt (``stderr``, nur wenn ein Terminal dranhängt)."""
    sys.stderr.write("\r\x1b[2K" + text if text else "\r\x1b[2K\n")
    sys.stderr.flush()


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
        ring_ausgabe: Callable[[str], None] | None = None,
        marken: Path | str | None = None,
    ) -> None:
        self.konfig = konfig
        self.uhr: Uhr = uhr or SystemUhr()
        self._melde_bereit = melde_bereit
        self._boot_id = boot_id
        self._marken = Path(marken) if marken is not None else fruehton.MARKEN_VERZEICHNIS  # Marke des Frühtons (``fruehton.py``)
        self._fruehton_wort: str | None = None  # ``start``, solange der Frühton noch läuft und ``app`` auf ihn wartet
        self._fruehton_bis = 0.0
        self._marker_uid: str | None = None  # zuletzt in ``lauf.json`` festgehaltener Tobie
        self._letzter_vorgang: str | None = None
        self._herunterfahren = False  # nach Herunterfahren kein Marker mehr
        zustand = konfig.pfade.zustand
        self.resume = ResumeStore(zustand)
        self.konfig_store = KonfigStore(zustand)
        self.bibliothek = library.Bibliothek((), "keine")
        # ``leser.geraet = "sim"``: kein Leser, die Leser-Ereignisse kommen aus ``sim`` (12.2: ``simulation``)
        self.status = Statussammler(leser_simulation=konfig.leser.simulation)
        self.ausgang = Ausgang(
            zustand, self.uhr, self.ereignisse_ein, self.konfig_store, self.status_auskunft, self.anzeige_auskunft,
            asynchron=True
        )
        self.outbox = self.ausgang.outbox
        self.sim = self.ausgang.sim
        self.ha_ersatz = self.ausgang.ha_ersatz
        self._baue_stufe_3a()
        self._baue_stufe_4(ring_ausgabe)
        self._verloren_basis = len(store.verlorene_dateien)  # ``datei_verloren`` zählt erst seit dem Start
        self.kern = core.neuer_zustand()
        self.ereignisse: asyncio.Queue[ev.Ereignis] = asyncio.Queue()
        self.befehle: asyncio.Queue[tuple[ev.Befehl, float]] = asyncio.Queue()
        self.player = Player(
            self.ereignisse.put_nowait, konfig.mpd.host, konfig.mpd.port, medien=konfig.pfade.medien
        )
        self.leser = Leser(self.ereignisse.put_nowait, konfig.leser.geraet)
        self.toene = Toene(
            konfig.toene.ordner or STANDARD_TOENE,
            konfig.toene.kommando,
            kennlinie=Kennlinie(konfig.toene.kennlinie, konfig.toene.softvol_bereich_db),
            vor=self._ton_vor,
            nach=self._ton_nach,
            pegel_quelle=self._ton_pegel,
            bevor=self._warte_fruehton,
        )
        self._start: _Start | None = None  # verzögerter Start, solange er auf die Töne wartet
        # Pegel der Töne (Entscheidung J, 09.11.): die **dauerhafte** wirksame Grenze und Lautstärke des Kerns, ohne die
        # Rampen „ausblenden“ und „gute_nacht“ (sonst wären Töne nach dem Ausblenden unhörbar, B2). Sie werden nach
        # jedem Kern-Schritt nachgeführt (``_ton_pegel_nachfuehren``); vor dem ersten Befehl gilt die Konfiguration.
        self.grenze = konfig.lautstaerke.max
        self.lautstaerke = min(konfig.lautstaerke.start, konfig.lautstaerke.max)
        self.bereit = asyncio.Event()
        self._stopp = asyncio.Event()
        self._aufgaben: list[asyncio.Task] = []
        self._hintergrund: set[asyncio.Task] = set()  # kurze Aufgaben (Sync abbrechen, Bibliothek neu laden)
        self._bibliothek_laedt = False

    def _baue_stufe_3a(self) -> None:
        """HA, Netz, Strom und Sync aus der Konfiguration (jeder Abschnitt ist optional)."""
        k = self.konfig
        self.zeitquelle: Zeitquelle | None = None
        self.netz: Netz | None = None
        self.power: Power | None = None
        self.ha: Ha | None = None
        self.sync: Sync | None = None
        self._systemuhr_ntp: TimedatectlNtp | None = None
        self._netz_bekannt = asyncio.Event()  # erste ``NetzKlasse`` ist angekommen (B7)
        if k.netz is None and k.strom is None and self._systemuhr_pruefen_noetig():
            # Pi ohne ``[netz]`` und ``[strom]`` (B15): Die Systemuhr gilt nur mit NTP-Synchronisierung als sicher.
            self.zeitquelle = Zeitquelle(system=False)
            self._systemuhr_ntp = TimedatectlNtp()
            self._uebernimm_zeitquelle(self.zeitquelle.quelle, self.zeitquelle.vertrauenswuerdig)
            eventlog.logge(
                "app", "WARNING", "systemuhr", "ntp_pflicht",
                meldung="Ohne [netz] und [strom] gilt die Systemuhr nur mit NTP-Synchronisierung als sicher.",
            )
        if k.netz is not None or k.strom is not None:
            # Am Mac (alles ``sim``) gilt die Systemuhr; sonst bewerten NTP (``net``) und RTC (``power``) die Uhr.
            system = uhrregel.alle_sim(k.netz, k.strom)
            self.zeitquelle = Zeitquelle(system=system)
            self._uebernimm_zeitquelle(self.zeitquelle.quelle, self.zeitquelle.vertrauenswuerdig)
        if k.netz is not None:
            netz_k = k.netz
            if netz_k.simulation:
                netz_k = replace(
                    netz_k, heim_ssid=netz_k.heim_ssid or SIM_HEIM_SSID, hotspot_ssid=netz_k.hotspot_ssid or SIM_HOTSPOT_SSID
                )
            self.netz = Netz.aus_konfig(netz_k, self.zeitquelle, self.ereignisse_ein)
            if isinstance(self.netz._ssid, SimSsid):
                self.sim.netz_haken = self._sim_netz
        if k.strom is not None:
            self.power = Power.aus_konfig(k.strom, self.zeitquelle, self.ereignisse_ein)
            if isinstance(self.power.treiber, SimStrom):
                self.sim.strom_haken = self._sim_strom
        if k.mqtt is not None:
            self.ha = Ha(
                k.mqtt, konfig_store=self.konfig_store, outbox=self.outbox, status=self.status, uhr=self.uhr,
                ausgabe=self.ereignisse_ein, medien=k.pfade.medien, serien=lambda: self.bibliothek.serien,
            )
            self.ausgang.ha = self.ha  # ab jetzt bestätigt HA, nicht der HA-Ersatz
        if k.sync is not None:
            haken = MpdHaken(k.mpd.host, k.mpd.port)
            self.sync = Sync(
                k.sync, k.pfade.medien, ausgabe=self.ereignisse_ein,
                aktuelle_datei=haken.aktuelle_datei, einlesen=haken.einlesen,
            )

    def _systemuhr_pruefen_noetig(self) -> bool:
        """Echte Systemuhr auf Linux (Pi): ohne NTP ist die Zeit unsicher. Am Mac (und mit Test-Uhr) gilt sie als sicher.

        ``[uhr] ntp_pflicht`` überstimmt die Vorgabe nach dem Betriebssystem (es gibt keine Abfrage „bin ich am Mac?“ im Dienst)."""
        if not isinstance(self.uhr, SystemUhr):
            return False
        return uhrregel.systemuhr_pruefen_noetig(self.konfig.uhr.ntp_pflicht)

    def _baue_stufe_4(self, ring_ausgabe: Callable[[str], None] | None) -> None:
        """LED-Ring, Tasten und Drehregler, Kopfhörer-Buchse (AP 4.8). Ohne Abschnitt in der Konfiguration gilt ``sim``."""
        k = self.konfig
        self._loop: asyncio.AbstractEventLoop | None = None
        self.led = LedLogik()
        self._ring_zustand: str | None = None
        self._ring_text = ""
        self._ring_ausgabe = ring_ausgabe if ring_ausgabe is not None else (_terminal_zeile if sys.stderr.isatty() else None)
        self._ring_zeile_offen = False
        self.bedienung = Bedienung(
            self._bedienung_ein,
            lang_s=k.tasten.lang_s,
            stand=min(k.lautstaerke.start, k.lautstaerke.max),
            grenze=k.lautstaerke.max,
        )
        self.gpio_tasten: GpioTreiber | None = None
        if not k.tasten.simulation:
            t = k.tasten
            self.gpio_tasten = GpioTreiber(
                self.bedienung, pin_vor=t.pin_vor, pin_zurueck=t.pin_zurueck,  # type: ignore[arg-type]
                pin_dreh_a=t.pin_dreh_a, pin_dreh_b=t.pin_dreh_b, pin_haupt=t.pin_haupt,  # type: ignore[arg-type]
            )
        kh = k.kopfhoerer
        self.kopfhoerer_treiber: SimKopfhoerer | GpioKopfhoerer = (
            SimKopfhoerer() if kh.simulation else GpioKopfhoerer(kh.gpio_pin, aktiv_niedrig=kh.aktiv_niedrig)  # type: ignore[arg-type]
        )
        self.buchse = Buchse(self.kopfhoerer_treiber, self.ereignisse_ein, intervall_s=kh.intervall_s)
        if kh.simulation:
            self.sim.kopfhoerer_haken = self._sim_kopfhoerer
        self.sim.zeit_haken = self._sim_zeit
        self.sim.regler_haken = self._sim_regler
        self.sim.quelle_sim = self._sim_quellen()

    def _sim_quellen(self) -> dict[str, bool]:
        """Welche Eingänge darf ``sim`` bedienen (B9)? Nur die, deren Quelle ``sim`` ist, oder alle mit ``[sim] erlauben = true``.

        Ohne ``[netz]``/``[strom]`` gibt ``sim`` ``NetzKlasse``, ``AkkuStand`` und ``LaderGeaendert`` selbst aus (Mac): erlaubt.
        Die Zeit stellt ``sim`` nur, wenn die Systemuhr nicht von NTP abhängt (Mac, ``[netz]``/``[strom]`` auf ``sim``)."""
        k = self.konfig

        def ok(quelle_sim: bool) -> bool:
            return k.sim.erlauben or quelle_sim

        tasten = ok(k.tasten.simulation)
        return {
            "hauptknopf_kurz": tasten, "hauptknopf_lang": tasten, "weiter": tasten, "zurueck": tasten, "regler": tasten,
            "kopfhoerer": ok(k.kopfhoerer.simulation),
            "strom": ok(k.strom is None or k.strom.simulation),
            "netz": ok(k.netz is None or k.netz.simulation),
            "zeit": ok(
                (k.netz is None or k.netz.simulation) and (k.strom is None or k.strom.simulation)
                and self._systemuhr_ntp is None
            ),
            "ha": ok(k.mqtt is None),
        }

    async def _sim_regler(self, delta: int) -> None:
        """``tobibox sim regler``: wie der Drehregler über ``Bedienung`` (kein Hochdrehen über die Grenze, B14)."""
        self.bedienung.drehen_prozent(delta)

    def _bedienung_ein(self, e: ev.Ereignis) -> None:
        """Eingang der ``Bedienung``. gpiozero ruft aus eigenen Threads: dann über die Ereignisschleife."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is not None and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self.ereignisse.put_nowait, e)
                return
        self.ereignisse.put_nowait(e)

    async def _sim_kopfhoerer(self, steckt: bool) -> None:
        """``tobibox sim headphones``: Stecker am simulierten Schaltkontakt, ``Buchse`` meldet sofort (ohne Entprellen)."""
        assert isinstance(self.kopfhoerer_treiber, SimKopfhoerer)
        self.kopfhoerer_treiber.setze(steckt)
        await self.buchse.melde(steckt)

    def _sim_zeit(self, wall: float | None) -> bool:
        """``tobibox sim time``: Wanduhr stellen. ``SystemUhr.stelle_wall`` (Mac), im Test ``SimUhr.setze_wall``."""
        stelle = getattr(self.uhr, "stelle_wall", None)
        if stelle is not None:
            stelle(wall)
            return True
        if wall is not None and hasattr(self.uhr, "setze_wall"):
            self.uhr.setze_wall(wall)  # type: ignore[attr-defined]
            return True
        return False

    def _uebernimm_zeitquelle(self, quelle: ev.ZeitQuelle, vertrauenswuerdig: bool) -> None:
        """``ZeitquelleGeaendert`` stellt die Uhr: ``SystemUhr.setze_quelle`` (im Test ``SimUhr.setze_zeit``)."""
        for name in ("setze_quelle", "setze_zeit"):
            stelle = getattr(self.uhr, name, None)
            if stelle is not None:
                stelle(quelle, vertrauenswuerdig)
                return

    async def _sim_strom(self, lader: bool | None, akku: int | None) -> None:
        """``tobibox sim power``: Treiber einstellen, ``power`` sofort messen lassen."""
        assert self.power is not None and isinstance(self.power.treiber, SimStrom)
        werte: dict = {}
        if lader is not None:
            werte["lader"] = lader
        if akku is not None:
            werte["akku"] = akku
        self.power.treiber.setze(**werte)
        await self.power.pruefe()

    async def _sim_netz(self, klasse: str) -> None:
        """``tobibox sim net``: das simulierte WLAN passend setzen, ``net`` sofort messen lassen."""
        assert self.netz is not None and isinstance(self.netz._ssid, SimSsid)
        ssid = {"home": self.netz.konfig.heim_ssid, "hotspot": self.netz.konfig.hotspot_ssid}.get(klasse)
        self.netz._ssid.setze(ssid)
        await self.netz.pruefe()

    def _spawn(self, coro, name: str) -> None:
        t = asyncio.get_running_loop().create_task(coro, name=name)
        self._hintergrund.add(t)
        t.add_done_callback(self._hintergrund.discard)

    # ------------------------------------------------------------------
    # Kern
    # ------------------------------------------------------------------

    def ereignisse_ein(self, e: ev.Ereignis) -> None:
        """Eingang für ``sim`` und den HA-Ersatz (später: MQTT)."""
        self.ereignisse.put_nowait(e)

    def verarbeite(self, e: ev.Ereignis) -> tuple[ev.Befehl, ...]:
        """Ein Ereignis durch den Kern; die Befehle gehen an den Ausführer."""
        if isinstance(e, ev.ZeitquelleGeaendert):
            self._uebernimm_zeitquelle(e.quelle, e.vertrauenswuerdig)  # vor ``jetzt``: schon dieses Ereignis sieht die neue Uhr
        jetzt = self.uhr.jetzt()
        sim = self.ausgang.war_sim(e)
        self._sicher(lambda: _protokolliere_leser(e), "protokoll_leser")
        self._sicher(lambda: self.status.beobachte(e, jetzt), "status")
        if not sim and self.sim.liegt is not None:
            # Ein Tobie liegt nur in der Simulation. Der echte Leser darf parallel laufen (``mac-prototyp.md``): Er meldet
            # „nichts da“, was für den simulierten Tobie nichts heißt. Der Kern kennt die Herkunft nicht, deshalb filtert
            # die Schale: Ein echter Tobie löst den simulierten ab, sonst erreicht den Kern nichts vom Leser.
            if isinstance(e, (ev.Aufgelegt, ev.Gesperrt)):
                self.sim.liegt = None
            elif isinstance(e, (ev.LeserHallo, ev.LeserHerzschlag, ev.LeserAlarm, ev.Abgehoben)):
                eventlog.logge("app", "DEBUG", "leser", "ignoriert_sim_tobie_liegt", daten={"ereignis": type(e).__name__})
                return ()
        if isinstance(e, SyncFortschritt):
            return ()  # nur Anzeige (Statussammler); der Kern kennt das Ereignis nicht
        self._sicher(lambda: self._melde_an_sync(e), "sync_eingabe")
        if isinstance(e, ev.Bestaetigt):
            # Zuerst die Outbox (``core-interface.md``, Abschnitt 3 und 7). Den Kern erreicht nur eine
            # Bestätigung für einen gelernten Tobie, die die Outbox angenommen hat (offener Eintrag, passendes
            # ``zuletzt``): Das Warten im Lernmodus endet bei „abgelehnt“ (Entscheidung H, 07.11.).
            angenommen = self.ausgang.bestaetigt(e, sim=sim)
            if e.art != "gelernt" or not angenommen:
                return ()
        if isinstance(e, (ev.Aufgelegt, ev.Gesperrt)) or (isinstance(e, ev.Abgehoben) and e.vorgang):
            self._letzter_vorgang = e.vorgang
        war_unten = self.kern.teil["idle"].modus == "herunterfahren"
        self.kern, befehle = core.step(self.kern, e, jetzt)
        if war_unten and self.kern.teil["idle"].modus != "herunterfahren":
            # Das Herunterfahren hat nicht gewirkt (B1) oder war simuliert: Das Gerät läuft weiter, der Marker in ``lauf.json`` gilt wieder
            self._herunterfahren = False
            self._marker_uid = None
        # Ab hier darf keine Ausnahme die Befehle dieses Schritts verlieren: der Kern ist schon weiter (B11)
        self._sicher(self._ton_pegel_nachfuehren, "ton_pegel")
        self._sicher(lambda: self._nachfuehren_stufe_4(e, befehle, jetzt), "stufe_4")
        self._sicher(lambda: self.ausgang.nach_kern(self.kern), "ausgang")
        auszufuehren: list[ev.Befehl] = []
        for b in befehle:
            try:
                self.status.befehl(b, jetzt)
                if isinstance(b, ev.Protokoll):
                    # Protokollzeilen sofort schreiben: Sie halten die Entscheidung fest (zugeordnet, spielt) und
                    # gehören vor die Ausführung der Befehle derselben Verarbeitung (Kette von CUJ 1, Messung).
                    eventlog.logge_befehl(b, sim=sim)
            except Exception:  # noqa: BLE001
                self._ausnahme("befehl_vorbereiten", b)
            if not isinstance(b, ev.Protokoll):
                auszufuehren.append(b)
        try:
            geordnet = self._toene_vor_start(auszufuehren)
        except Exception:  # noqa: BLE001
            self._ausnahme("toene_ordnen")
            geordnet = auszufuehren
        for b in geordnet:
            self.befehle.put_nowait((b, jetzt.mono))
        self._sicher(self._marker_nachfuehren, "marker")
        return befehle

    def _ausnahme(self, stelle: str, b: ev.Befehl | None = None) -> None:
        log.exception("Kern: Ausnahme bei %s", stelle)
        eventlog.logge("app", "ERROR", "nachfuehrung", "fehler", daten={"stelle": stelle, "befehl": type(b).__name__ if b else None})

    def _sicher(self, aufruf: Callable[[], object], stelle: str) -> None:
        """Eine Nachführung, die fehlschlagen darf, ohne den Schritt des Kerns zu stoppen (B11)."""
        try:
            aufruf()
        except Exception:  # noqa: BLE001
            self._ausnahme(stelle)

    def _nachfuehren_stufe_4(self, e: ev.Ereignis, befehle: Sequence[ev.Befehl], jetzt: ev.Jetzt) -> None:
        """Ring und Bedienung folgen dem Kern (derselbe Code wie im Testaufbau: ``nachfuehrung``)."""
        nachfuehrung.stufe_4(self.led, self.bedienung, self.kern, e, befehle, jetzt.mono)

    def _melde_an_sync(self, e: ev.Ereignis) -> None:
        """Netz-Klasse, Lader und Akku für die Regel des Syncs (``setze_*``); ein Netzverlust bricht einen laufenden Sync ab."""
        sy = self.sync
        if sy is None:
            return
        if isinstance(e, ev.NetzKlasse):
            sy.setze_netz(e.klasse)
            self._netz_bekannt.set()
        elif isinstance(e, ev.LaderGeaendert):
            if self.status.lader is not None:
                sy.setze_lader(self.status.lader)  # der zusammengeführte Wert beider Quellen (Ein/Aus, 10.11.); ``status`` hat ``e`` schon gesehen
        elif isinstance(e, ev.AkkuStand):
            sy.setze_akku(e.prozent)
        elif isinstance(e, ev.SyncFertig) and (e.neu or e.geloescht):
            self._spawn(self._bibliothek_neu_laden(), "tobibox-bibliothek")  # neue Folgen sind auf der Platte

    async def _bibliothek_neu_laden(self) -> None:
        """Nach einem Sync: Medienordner neu lesen und als ``BibliothekGeladen`` in die Ereignisschleife geben."""
        if self._bibliothek_laedt:
            return  # läuft schon; sie liest den Stand von jetzt
        self._bibliothek_laedt = True
        try:
            self.bibliothek = await asyncio.to_thread(library.lade_bibliothek, self.konfig.pfade.medien)
            self.ereignisse.put_nowait(self.bibliothek.ereignis())
            eventlog.logge("app", "INFO", "bibliothek", "neu_geladen", daten={"serien": len(self.bibliothek.serien)})
        finally:
            self._bibliothek_laedt = False

    def _ton_pegel_nachfuehren(self) -> None:
        """``grenze`` und ``lautstaerke`` für Töne aus dem Zustand des Kerns (``nachfuehrung.ton_pegel``)."""
        werte = nachfuehrung.ton_pegel(self.kern)
        if werte is not None:  # sonst gelten die Werte aus der Konfiguration
            self.grenze, self.lautstaerke = werte

    def _ton_pegel(self) -> tuple[int, int, int | None]:
        """Die Werte für den Pegel eines Tons, im Augenblick, in dem er an der Reihe ist (B6)."""
        return self.grenze, self.lautstaerke, self._hinweis_pegel()

    @staticmethod
    def _toene_vor_start(befehle: Sequence[ev.Befehl]) -> list[ev.Befehl]:
        """Töne einer Ausgabe vor das ``Abspielen`` stellen (Entscheidung L, Ton vor Hörspiel).

        Der Kern gibt ``Abspielen`` (Rang 5) vor ``TonSpielen`` (Rang 6) aus (``core-interface.md``, 6.4). Der Ausführer
        übergibt einen Ton nur an die Tonspur und wartet nicht; damit der Start die Töne derselben Ausgabe
        schon in der Spur findet und auf sie wartet, steht der Ton in der Warteschlange vor dem Start. Alle anderen
        Befehle behalten ihre Reihenfolge.
        """
        toene = [b for b in befehle if isinstance(b, (ev.TonSpielen, ev.StatusPruefen))]
        if not toene or not any(isinstance(b, ev.Abspielen) for b in befehle):
            return list(befehle)
        rest = [b for b in befehle if not isinstance(b, (ev.TonSpielen, ev.StatusPruefen))]
        i = next(n for n, b in enumerate(rest) if isinstance(b, ev.Abspielen))
        return rest[:i] + toene + rest[i:]

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
                if (
                    isinstance(e, ev.Takt) and self.sync is not None
                    and self.kern.teil["idle"].modus != "herunterfahren"  # nach dem Entschluss zum Herunterfahren startet kein Sync mehr (B6)
                ):
                    await self.sync.takt()  # zeitgesteuerter Sync: startet nur, wenn Intervall und Regel es erlauben
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

    def _hinweis_pegel(self) -> int | None:
        """``hinweis_pegel`` aus der Rohkonfiguration (``Konfig`` hat das Feld nicht).

        ``ton_pegel`` wird seit Entscheidung J (09.11.) nicht mehr gelesen: Töne folgen ``self.lautstaerke``.
        """
        w = self.konfig_store.roh.get("hinweis_pegel")
        return w if isinstance(w, int) and not isinstance(w, bool) and 0 <= w <= 100 else None

    async def _fuehre_aus(self, b: ev.Befehl, mono: float) -> None:
        if isinstance(b, ev.LautstaerkeSetzen):
            await self.player.lautstaerke_setzen(b.prozent, b.grenze)
        elif isinstance(b, ev.AusgangWaehlen):
            await self.player.ausgang_waehlen(b.ausgang)
        elif isinstance(b, ev.Pausieren):
            self._verwirf_start("pausieren")  # eine Pause gewinnt gegen einen noch wartenden Start
            vorgang = self._vorgang()
            eventlog.logge("app", "INFO", "pausieren", "gesendet", vorgang, daten={"grund": b.grund})
            t0 = time.monotonic()
            await self.player.pausieren(b)
            eventlog.logge("app", "INFO", "pausieren_fertig", "ok", vorgang, daten={"dauer_ms": _ms(t0)})
        elif isinstance(b, ev.Abspielen):
            await self._abspielen(b)
        elif isinstance(b, ev.ZeigerSpeichern):
            await asyncio.to_thread(self.resume.speichern, b, mono)
        elif isinstance(b, ev.TonSpielen):
            self.toene.spiele(b.ton)
        elif isinstance(b, ev.Protokoll):
            eventlog.logge_befehl(b)  # normalerweise schon in ``verarbeite`` geschrieben
        elif isinstance(b, ev.LeserPing):
            self.leser.ping()
        elif isinstance(b, ev.Herunterfahren):
            self._herunterfahren = True
            await asyncio.to_thread(lauf.loesche, self.konfig.pfade.zustand)
            eventlog.logge("app", "INFO", "herunterfahren", "angefordert", daten={"grund": b.grund})
            await self._warte_ton_ende()  # ``akku_leer`` soll noch zu hören sein (B12)
            if self.power is not None:
                # Pi: pisugar/systemctl poweroff. Schlägt es fehl (oder ist es simuliert), sendet ``power`` ``HerunterfahrenFehlgeschlagen``
                await self.power.fuehre_aus(b)
            else:  # kein ``[strom]``: nichts, was herunterfährt (Mac)
                self.ereignisse.put_nowait(ev.HerunterfahrenFehlgeschlagen("", simuliert=True))
        elif isinstance(b, ev.AkkuAnzeigen):
            pass  # setzt ``led`` um (``nachfuehrung.stufe_4``), kein Ausführer
        elif isinstance(b, ev.ZustandMelden):
            pass  # der Statussammler hat sie in ``verarbeite`` schon gesehen
        elif isinstance(b, ev.Melden):
            await self._melde(b)
        elif isinstance(b, ev.EreignisSenden):
            eventlog.logge("app", "INFO", "ereignis_senden", b.art, daten=dict(b.daten))
            if self.ha is not None:
                self.ha.fuehre_aus(b)  # ``tobibox/<box>/event``
        elif isinstance(b, ev.StatusPruefen):
            self._status_pruefen(b)
        elif isinstance(b, ev.SyncStarten):
            await self._sync_starten(b)
        elif isinstance(b, ev.SyncAbbrechen):
            if self.sync is not None:  # ``abbrechen`` wartet auf rsync: nicht im Ausführer, sonst steht die Wiedergabe
                self._spawn(self.sync.abbrechen(b.grund), "tobibox-sync-abbrechen")
        elif isinstance(b, ev.UpdateStarten):
            # Bis Stufe 3b gibt es kein Update: HA bekommt eine ehrliche Ablehnung statt Schweigen (B16)
            eventlog.logge("app", "WARNING", "update", "nicht_eingerichtet", daten={"befehl_id": b.befehl_id, "version": b.version})
            await self._fuehre_aus(
                ev.EreignisSenden("befehl_abgelehnt", {
                    "befehl": "update", "befehl_id": b.befehl_id, "grund": "bedingung", "detail": UPDATE_NOCH_NICHT_TEXT,
                }),
                mono,
            )
        else:
            eventlog.logge("app", "DEBUG", "befehl_nicht_umgesetzt", "ignoriert", daten={"befehl": type(b).__name__})

    async def _warte_ton_ende(self) -> None:
        """Vor dem Herunterfahren den laufenden Ton (``akku_leer``) ausspielen lassen, höchstens ``TON_VOR_HERUNTERFAHREN_S``."""
        warte = getattr(self.toene, "warte_leer", None)
        if warte is None or not self._toene_laufen():
            return
        try:
            await asyncio.wait_for(warte(), TON_VOR_HERUNTERFAHREN_S)
        except (asyncio.TimeoutError, Exception) as e:  # noqa: BLE001 - das Herunterfahren hat Vorrang
            eventlog.logge("app", "WARNING", "herunterfahren", "ton_wartet_nicht", daten={"detail": repr(e)[:100]})

    async def _start_sync_nach_netz(self, b: ev.SyncStarten) -> None:
        """Start-Sync am Lader, bevor die erste Netz-Klasse da ist (B7): auf sie warten, mit Frist, dann starten."""
        assert self.sync is not None
        try:
            await asyncio.wait_for(self._netz_bekannt.wait(), NETZ_KLASSE_WARTEN_S)
        except asyncio.TimeoutError:
            eventlog.logge("app", "WARNING", "sync", "netz_klasse_fehlt", daten={"frist_s": NETZ_KLASSE_WARTEN_S})
        try:
            await self.sync.start(b.grund)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            eventlog.logge("app", "ERROR", "befehl_fehler", "fehler", daten={"befehl": "SyncStarten", "detail": repr(e)})
            self.ereignisse.put_nowait(ev.SyncAbgebrochen("rsync_fehler"))

    async def _sync_starten(self, b: ev.SyncStarten) -> None:
        if self.sync is not None:
            if b.grund == "start_lader" and self.netz is not None and not self.sync.netz_bekannt:
                # Die Netz-Klasse wird noch gemessen (``nmcli``, NAS): nicht mit ``regel`` abbrechen, sondern kurz warten.
                # Eigene Aufgabe, damit der Ausführer (Pause, Zeiger) nicht wartet.
                self._spawn(self._start_sync_nach_netz(b), "tobibox-sync-start")
                return
            await self.sync.start(b.grund)  # die Regel (Heim / Hotspot und Akku) prüft ``sync``; sonst ``SyncAbgebrochen("regel")``
            return
        # ohne ``[sync]`` gibt es nichts zu holen; die Antwort verhindert, dass ein Sync „offen“ bleibt (``idle``)
        eventlog.logge("app", "INFO", "sync", "nicht_eingerichtet", daten={"grund": b.grund})
        # ein eigener Grund, damit ``idle`` den Start-Sync am Lader nicht ständig wiederholt (nur ``netz_weg`` und ``regel``)
        self.ereignisse.put_nowait(ev.SyncAbgebrochen("nicht_eingerichtet"))

    # ------------------------------------------------------------------
    # Wiedergabestart und Töne (Entscheidung L, 09.11.)
    # ------------------------------------------------------------------

    def _toene_laufen(self) -> bool:
        """Läuft oder wartet ein Ton? (Attrappen ohne Tonspur gelten als still.)"""
        return bool(getattr(self.toene, "beschaeftigt", False))

    async def _abspielen_jetzt(self, b: ev.Abspielen) -> None:
        eventlog.logge(
            "app", "INFO", "abspielen", "gesendet", b.vorgang,
            daten={"serie": b.serie_id, "folge": b.datei, "track": b.track, "position_s": b.position_s},
        )
        t0 = time.monotonic()
        await self.player.abspielen(b)
        eventlog.logge("app", "INFO", "abspielen_fertig", "ok", b.vorgang, daten={"dauer_ms": _ms(t0)})

    async def _abspielen(self, b: ev.Abspielen) -> None:
        """Start jetzt, wenn kein Ton läuft; sonst erst nach dem Ende der Töne (Ton vor Hörspiel)."""
        self._verwirf_start("neuer_start")
        if not self._toene_laufen():
            await self._abspielen_jetzt(b)  # normales Auflegen ohne Ton: kein Umweg, kein Verzug
            return
        start = _Start(b)
        start.task = asyncio.get_running_loop().create_task(self._start_nach_toenen(start), name="tobibox-start")
        self._start = start
        eventlog.logge("app", "INFO", "abspielen", "wartet_auf_toene", b.vorgang, daten={"gen": b.gen})

    def _start_gueltig(self, b: ev.Abspielen) -> str | None:
        """``None`` wenn der Start noch gilt, sonst der Grund. ``gen`` allein reicht nicht: Abheben erhöht sie nicht."""
        s = self.kern.session
        if s.gen != b.gen:
            return "gen_veraltet"
        if s.modus not in ("spielt", "unbekannt"):
            return "nicht_mehr_spielt"
        return None

    async def _start_nach_toenen(self, start: _Start) -> None:
        b = start.befehl
        try:
            await self.toene.warte_leer()  # type: ignore[attr-defined]
            # Ab hier kein ``await`` bis zum Aufruf des Players: nichts kann dazwischenkommen.
            grund = self._start_gueltig(b)
            if grund is not None:
                eventlog.logge("app", "INFO", "abspielen", "verworfen", b.vorgang, daten={"grund": grund, "gen": b.gen})
                return
            start.wartet = False
            await self._abspielen_jetzt(b)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # darf die Box nicht anhalten
            eventlog.logge("app", "ERROR", "befehl_fehler", "fehler", daten={"befehl": "Abspielen", "detail": repr(e)})
        finally:
            if self._start is start:
                self._start = None

    def _verwirf_start(self, grund: str) -> None:
        """Einen noch wartenden Start verwerfen. Ein Start, der schon läuft, bleibt (der Player ordnet ihn vor)."""
        s = self._start
        if s is None or not s.wartet or s.task is None:
            return
        s.task.cancel()
        self._start = None
        eventlog.logge("app", "INFO", "abspielen", "verworfen", s.befehl.vorgang, daten={"grund": grund, "gen": s.befehl.gen})

    async def _ton_vor(self) -> None:
        """Anfang einer Tonfolge: spielt MPD gerade, kurz anhalten (kein Zeiger, kein Status)."""
        await self.player.ton_pause_beginn()

    async def _ton_nach(self) -> None:
        """Ende einer Tonfolge: an derselben Stelle fortsetzen, außer ein neuer Start wartet schon."""
        # Beides wird erst unter der Sperre des Players befragt, kurz vor dem Fortsetzen (B8): kommt ein neuer Start
        # oder ein weiterer Ton in diesem Augenblick, blitzt das alte Hörspiel nicht noch einmal auf.
        await self.player.ton_pause_ende(
            fortsetzen=lambda: not (self._start is not None and self._start.wartet),
            halten=lambda: bool(getattr(self.toene, "folge_wartet", False)),
        )
        if not getattr(self.toene, "folge_wartet", False):
            self.ereignisse.put_nowait(ev.TonFolgeEnde())  # ``idle`` wartet nach ``akku_leer`` darauf (Entscheidung Z, 11.11.)

    async def _melde(self, b: ev.Melden) -> None:
        """Unbekannten oder gelernten Tobie in ``unknown.json`` eintragen (``outbox``)."""
        # Stufe 2: ``sim`` spielt HA; Stufe 3a: Veröffentlichung per MQTT
        await self.ausgang.melde_async(b, self.uhr.jetzt())

    def pruefbericht(self, jetzt: ev.Jetzt) -> selftest.Pruefbericht:
        """Die vier Prüfpunkte der Status-Karte (12.3). Netz, Leser und Speicher kennt der Dienst, nicht ``selftest``."""
        return selftest.pruefe(
            self.konfig.pfade.medien,
            leser=self.status.leser(jetzt.mono),
            netz=self.status.netz,
            ha_verbunden=self.status.ha_verbunden,
            datei_verloren=len(store.verlorene_dateien) > self._verloren_basis,
            bibliothek=self.bibliothek,
        )

    def _status_pruefen(self, b: ev.StatusPruefen) -> None:
        """Status-Admin-Karte (CUJ 11): je Prüfpunkt ein Ton, nacheinander."""
        bericht = self.pruefbericht(self.uhr.jetzt())
        eventlog.logge(
            "selftest", "INFO" if bericht.alles_ok else "WARNING", "status_geprueft",
            "ok" if bericht.alles_ok else "fehler", b.vorgang,
            daten={p.name: ("ok" if p.ok else f"FEHLER {p.detail}") for p in bericht.punkte},
        )
        self.toene.spiele_folge(bericht.toene)

    def status_auskunft(self) -> dict:
        """Antwort auf ``sim`` ``status`` (für ``tobibox status``): Status-JSON, Prüfpunkte, offene Meldungen."""
        jetzt = self.uhr.jetzt()
        frei = selftest.messe(self.konfig.pfade.medien, self.bibliothek).frei_mb
        return {
            "status": self.status.als_dict(jetzt, self.bibliothek.serien, frei),
            "pruefpunkte": self.pruefbericht(jetzt).als_dict(),
            "offen": [dataclasses.asdict(e) for e in self.outbox.offen()],
            "verbindungen": self.verbindungen(),
        }

    def verbindungen(self) -> dict:
        """Was ``tobibox status`` zusätzlich zeigt (AP 3.7): HA-Verbindung, Netz, Akku, Sync samt Zwischenstand."""
        st = self.status
        return {
            "ha": {"eingerichtet": self.ha is not None, "verbunden": st.ha_verbunden},
            "netz": {"eingerichtet": self.netz is not None, "klasse": st.netz},
            "strom": {"eingerichtet": self.power is not None, "akku_prozent": st.akku, "lader": st.lader},
            "sync": {"eingerichtet": self.sync is not None, **st.sync, "fortschritt": st.sync_fortschritt},
        }

    def anzeige_auskunft(self) -> dict:
        """Antwort auf ``sim`` ``anzeige`` (Oberfläche, AP 4.9): leicht genug für eine Abfrage alle 300 ms.

        ``status`` wie ``status_auskunft`` (ohne freien Speicher und Prüfpunkte) und ``anzeige`` mit Lautstärke,
        Grenzen, Position, Kopfhörer, dem liegenden Tobie und dem Ring (``ring``: ``ring_dict`` von ``led`` plus ``farben``).
        """
        jetzt = self.uhr.jetzt()
        k = self.kern
        z = k.session
        figur = None if z.figur is None else {"uid": z.figur.uid, "vorgang": z.figur.vorgang, "art": z.figur.art}
        zeile = k.gemeldet
        return {
            "status": self.status.als_dict(jetzt, self.bibliothek.serien, None),
            "offen": [dataclasses.asdict(e) for e in self.outbox.offen()],
            "anzeige": {
                "lautstaerke": k.wirksam_gemeldet if k.wirksam_gemeldet is not None else self.lautstaerke,
                "wunsch": k.wunsch,
                "grenze": wirksame_grenze(k.grenzen),
                "grenzen": dict(k.grenzen),
                "serie_id": z.serie_id,
                "folge": z.datei,
                "track": z.track,
                "position_s": round(z.position_s, 1),
                "kopfhoerer": z.kopfhoerer_steckt,
                "stumm": z.stumm,
                "ruhe": zeile.ruhe if zeile is not None else "normal",
                "gute_nacht": zeile.gute_nacht if zeile is not None else "aus",
                "strom": zeile.strom if zeile is not None else "aktiv",
                # Strom am Eingang je Quelle (die Seite schreibt jeden Haken aus seiner Quelle; ``status.lader`` ist der zusammengeführte Wert)
                "strom_quellen": {"pisugar": self.status.strom_quellen.pisugar, "leser": self.status.strom_quellen.leser},
                "figur": figur,
                "sync_fortschritt": self.status.sync_fortschritt,
                "ring": self.ring_anzeige(),
            },
        }

    # ------------------------------------------------------------------
    # LED-Ring (AP 4.8)
    # ------------------------------------------------------------------

    def _led_ausblenden(self) -> None:
        """Stand des Ausblendens von „Gute Nacht“ aus dem Zustand von ``bedtime`` an ``led`` (Glimmen wird schwächer)."""
        nachfuehrung.led_ausblenden(self.led, self.kern)

    def ring_anzeige(self) -> dict:
        """Das Bild des Rings jetzt: ``led.ring_dict`` und dieselben Farben als ``farben`` (Format der Oberfläche)."""
        self._led_ausblenden()
        d = self.led.ring_dict(self.uhr.jetzt().mono)
        d["farben"] = d["leds"]
        return d

    def _zeige_ring(self) -> None:
        """Ein Schritt: Ring rechnen; bei Wechsel des Zustands ins Protokoll, bei geänderter Zeile ins Terminal."""
        self._led_ausblenden()
        r = self.led.ring(self.uhr.jetzt().mono)
        if r.zustand != self._ring_zustand:
            self._ring_zustand = r.zustand
            eventlog.logge("led", "INFO", "ring", r.zustand, daten={"helligkeit": round(r.helligkeit, 1)})
        if self._ring_ausgabe is not None:
            text = _ring_zeile(r)
            if text != self._ring_text:
                self._ring_text = text
                self._ring_ausgabe(text)
                self._ring_zeile_offen = True

    async def _led_lauf(self) -> None:
        while True:
            try:
                self._zeige_ring()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - die Anzeige darf die Box nie anhalten
                eventlog.logge("led", "ERROR", "ring", "fehler", daten={"detail": repr(e)})
            await asyncio.sleep(LED_TAKT_S)

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
        raeume_auf(self.konfig.pfade.zustand)  # Reste halber Schreibvorgänge: nur hier, nie zur Laufzeit
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
        self._loop = asyncio.get_running_loop()
        # Kopfhörer: erste Messung nach ``GeraeteEinstellungen`` (sie stehen vorn in der Schlange), vor ``Bereit``
        await self.buchse.start()
        self.ereignisse.put_nowait(ev.Bereit(fruehton=self._fruehton_auswerten()))
        await self._leere_ereignisse()
        if not self.konfig.leser.simulation:
            self.leser.start()
        try:
            await self.sim.start()
        except OSError as e:  # ein Hilfs-Treiber darf die Box nicht verhindern
            eventlog.logge(
                "app", "ERROR", "sim_start", "fehler",
                meldung="sim.sock konnte nicht geöffnet werden; die Box läuft ohne Simulations-Treiber weiter",
                daten={"pfad": str(self.sim.pfad), "detail": str(e) or repr(e)},
            )
        self._aufgaben.append(asyncio.create_task(self._taktgeber(), name="tobibox-takt"))
        await self._starte_stufe_3a()
        self._starte_stufe_4()
        self.bereit.set()
        if self._melde_bereit:
            notify.bereit()
        eventlog.logge("app", "INFO", "bereit", "ok")

    def _fruehton_auswerten(self) -> bool:
        """Die Marke des Frühtons **bei ``Bereit``** lesen (V1, Ein/Aus, 10.11.) und die Gegenmarke setzen.

        Gibt es noch keine Marke, legt ``app`` ``uebernommen`` an: Ein später startender Frühdienst darf dann nicht mehr spielen
        (nie zwei Töne). War eine Marke da, spielt der Kern keinen ``start`` (``Bereit.fruehton``). Bei einem Dienst-Neustart ohne Ausschalten
        (gleiche Boot-Kennung wie in ``lauf.json``) wird die Marke ignoriert."""
        neustart = lauf.gleicher_start(self.konfig.pfade.zustand, self._boot_id())
        wort = fruehton.uebernimm_marke(self._marken, neustart=neustart)
        eventlog.logge("app", "INFO", "fruehton", wort or ("neustart" if neustart else "keiner_da"))
        if wort == fruehton.START:
            self._fruehton_wort = wort
            self._fruehton_bis = time.monotonic() + FRUEHTON_WARTEN_S
        elif wort is not None:
            fruehton.loesche_marke(self._marken)  # ``keiner`` oder ``fertig``: erledigt
        return wort is not None

    async def _warte_fruehton(self) -> None:
        """Vor jedem Ton des Kerns: Läuft der Frühton noch (Marke ``start``), warten bis ``fertig``, höchstens ``FRUEHTON_WARTEN_S`` ab ``Bereit``."""
        if self._fruehton_wort != fruehton.START:
            return
        while time.monotonic() < self._fruehton_bis and fruehton.lese_marke(self._marken) == fruehton.START:
            await asyncio.sleep(FRUEHTON_PRUEFEN_S)
        if fruehton.lese_marke(self._marken) == fruehton.START:
            eventlog.logge("app", "WARNING", "fruehton", "frist_um", daten={"frist_s": FRUEHTON_WARTEN_S})
        self._fruehton_wort = None
        fruehton.loesche_marke(self._marken)

    async def _starte_stufe_3a(self) -> None:
        """HA, Netz und Strom starten, nachdem ``Bereit`` verarbeitet ist (ihre Ereignisse treffen einen bereiten Kern)."""
        if self.ha is not None:
            await self.ha.start()  # verbindet im Hintergrund; ohne Broker läuft die Box offline weiter
        if self.netz is not None:
            self._aufgaben.append(asyncio.create_task(self.netz.lauf(), name="tobibox-netz"))
        if self._systemuhr_ntp is not None:
            self._aufgaben.append(asyncio.create_task(self._systemuhr_lauf(), name="tobibox-systemuhr"))
        if self.power is not None:
            self._aufgaben.append(asyncio.create_task(self._strom_lauf(), name="tobibox-strom"))
            if self.power.taste_befehl is not None:  # B2: Hauptknopf über den PiSugar, **am Pi zu prüfen**
                self._aufgaben.append(asyncio.create_task(self.power.taste_lauf(), name="tobibox-taste"))

    def _starte_stufe_4(self) -> None:
        """Ring, Kopfhörer-Messung und (am Pi) Tasten starten."""
        self._aufgaben.append(asyncio.create_task(self._led_lauf(), name="tobibox-led"))
        self._aufgaben.append(asyncio.create_task(self.buchse.lauf(), name="tobibox-kopfhoerer"))
        k = self.konfig
        if not k.tasten.simulation and k.tasten.pin_haupt is None and (self.power is None or self.power.taste_befehl is None):
            eventlog.logge(
                "app", "WARNING", "hauptknopf", "ohne_quelle",
                meldung="Der Hauptknopf hat keine Quelle: [tasten] pin_haupt fehlt und [strom] taste_befehl ist nicht gesetzt "
                        "(Pause, Weiter und Abschalten per Hauptknopf gehen nicht; docs/betrieb/pisugar-wecker.md).",
            )
        if self.gpio_tasten is not None:
            try:
                self.gpio_tasten.start()
            except Exception as e:  # noqa: BLE001 - ohne Tasten läuft die Box weiter (kein gpiozero, Pin belegt)
                eventlog.logge("app", "ERROR", "tasten_start", "fehler", daten={"detail": repr(e)})
            else:
                eventlog.logge("app", "INFO", "tasten", "gpio")

    async def _systemuhr_lauf(self) -> None:
        """Pi ohne ``[netz]`` und ``[strom]`` (B15): NTP-Synchronisierung prüfen; ein Wechsel stellt die Zeitquelle."""
        assert self._systemuhr_ntp is not None and self.zeitquelle is not None
        while True:
            try:
                z = self.zeitquelle.ntp(await self._systemuhr_ntp.synchron())
                if z is not None:
                    self.ereignisse.put_nowait(z)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                eventlog.logge("app", "ERROR", "systemuhr", "fehler", daten={"detail": repr(e)})
            await asyncio.sleep(SYSTEMUHR_PRUEFEN_S)

    async def _strom_lauf(self) -> None:
        """RTC lesen und erste Messung (``Power.start``), dann dauernd messen (``Power.lauf``)."""
        assert self.power is not None
        try:
            await self.power.start()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - ein Fehler beim Start darf die Messung nicht verhindern
            eventlog.logge("app", "ERROR", "strom_start", "fehler", daten={"detail": repr(e)})
        await self.power.lauf()

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
        if self._start is not None and self._start.task is not None:
            self._start.task.cancel()
            self._aufgaben.append(self._start.task)
            self._start = None
        for t in (*self._aufgaben, *self._hintergrund):
            t.cancel()
        for t in (*self._aufgaben, *self._hintergrund):
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t
        if self.sync is not None:
            await self._warte(self.sync.beenden(), "sync", ABBRUCH_SYNC_WARTEN_S)  # rsync-Kindprozess beenden
        await self._warte(self.player.pausiere_hart(), "pause_hart")
        await self._warte(self.player.stop(), "player")
        await self._warte(self.toene.stop(), "toene")
        await self._warte(self.sim.stop(), "sim")
        await self._warte(self.leser.stop(), "leser")
        if self.gpio_tasten is not None:
            with contextlib.suppress(Exception):
                self.gpio_tasten.stop()
        schliesse = getattr(self.kopfhoerer_treiber, "schliesse", None)
        if schliesse is not None:
            with contextlib.suppress(Exception):
                schliesse()
        if self._ring_zeile_offen and self._ring_ausgabe is not None:
            self._ring_ausgabe("")  # Zeile beenden
            self._ring_zeile_offen = False
        await self._warte(self.outbox.warte_gespeichert(), "outbox")
        if self.ha is not None:
            await self._warte(self.ha.stop(), "ha")  # zuerst ``offline`` veröffentlichen, dann trennen

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
            await self._warte(self.outbox.warte_gespeichert(), "outbox")
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
