"""Leser: serielle Verbindung zum ESP32, Wächter, Neuverbinden (``reader-v1.md``, 6 und 12).

pyserial läuft in einem eigenen Thread (alle Ein- und Ausgaben der Serielle);
die Zeilen gehen über eine ``asyncio.Queue`` an die Ereignisschleife. Die
Serielle wird ohne DTR/RTS geöffnet, damit das Öffnen keinen Reset auslöst.

Aufgaben von ``reader`` laut ``core-interface.md``: Vorgangs-ID erzeugen
(8 Zeichen ``[0-9a-f]``), ``seq`` prüfen, Schwere der ``ERR``-Codes setzen,
**einen** ``LeserAlarm`` je Ausfall senden und sich selbst neu verbinden.
"""

from __future__ import annotations

import asyncio
import glob
import logging
import queue
import secrets
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import serial  # pyserial

from . import events as ev
from .protocol import PING_ZEILE, PROTO_UNTERSTUETZT, Zeile, ZeilenFehler, parse_zeile, schwere

log = logging.getLogger("tobibox.reader")

WATCHDOG_S = 5.0
HELLO_TIMEOUT_S = 2.0
PING_TRIES = 3
RECONNECT_BACKOFF_S: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0)
BAUD = 115200
VERWERFEN_S = 0.3  # nach dem Öffnen: alles Alte lesen und wegwerfen
MAC_SUCHMUSTER = "/dev/cu.usbmodem*"

_SEQ_MODUL = 2**32
_PUFFER_MAX = 4096  # Zeilen ohne \n über dieser Länge werden bis zum nächsten \n verworfen


def oeffne_seriell(pfad: str) -> serial.Serial:
    """Serielle ohne DTR/RTS öffnen (Abschnitt 1): beide vor dem Öffnen auf „aus“."""
    ser = serial.Serial()
    ser.port = pfad
    ser.baudrate = BAUD
    ser.timeout = 0.05
    ser.write_timeout = 1.0
    ser.dsrdtr = False
    ser.rtscts = False
    ser.xonxoff = False
    ser.dtr = False
    ser.rts = False
    ser.open()
    return ser


# Meldungen des Threads an die Ereignisschleife
_OFFEN = "offen"
_FEHLER = "fehler"
_ZEILE = "zeile"
_ZU_LANG = "zu_lang"
_ENDE = "ende"
_PING = "ping"  # der Thread hat PING geschrieben; davor Gelesenes ist alt


class _SerielleThread(threading.Thread):
    """Liest Zeilen, schreibt Befehle; alles an der Serielle geschieht hier."""

    def __init__(self, pfad: str, loop: asyncio.AbstractEventLoop, ausgang: asyncio.Queue) -> None:
        super().__init__(name="tobibox-reader", daemon=True)
        self._pfad = pfad
        self._loop = loop
        self._ausgang = ausgang
        self._stop_flag = threading.Event()
        self._schreiben: queue.Queue[bytes] = queue.Queue()

    def schreibe(self, daten: bytes) -> None:
        self._schreiben.put(daten)

    def stoppe(self) -> None:
        self._stop_flag.set()

    def _melde(self, art: str, wert: Any = None) -> None:
        try:
            self._loop.call_soon_threadsafe(self._ausgang.put_nowait, (art, wert))
        except RuntimeError:
            pass  # Ereignisschleife ist schon geschlossen

    def run(self) -> None:
        try:
            ser = oeffne_seriell(self._pfad)
        except Exception as exc:  # Gerät fehlt, keine Rechte, ...
            self._melde(_FEHLER, exc)
            return
        try:
            ser.reset_input_buffer()
            ende = time.monotonic() + VERWERFEN_S
            while time.monotonic() < ende and not self._stop_flag.is_set():
                ser.read(max(1, ser.in_waiting))
        except Exception as exc:
            self._melde(_FEHLER, exc)
            try:
                ser.close()
            except Exception:
                pass
            return
        self._melde(_OFFEN)
        puffer = bytearray()
        verwerfen = False
        try:
            while not self._stop_flag.is_set():
                try:
                    while True:
                        daten = self._schreiben.get_nowait()
                        ser.write(daten)
                        ser.flush()
                        if daten == PING_ZEILE:
                            self._melde(_PING)
                except queue.Empty:
                    pass
                daten = ser.read(max(1, ser.in_waiting))
                if not daten:
                    continue
                for byte in daten:
                    if byte == 0x0A:
                        if verwerfen:
                            verwerfen = False
                        else:
                            self._melde(_ZEILE, bytes(puffer))
                        puffer.clear()
                    elif not verwerfen:
                        puffer.append(byte)
                        if len(puffer) > _PUFFER_MAX:
                            self._melde(_ZU_LANG)
                            puffer.clear()
                            verwerfen = True
        except Exception as exc:  # Gerät weg, Lese- oder Schreibfehler
            if not self._stop_flag.is_set():
                self._melde(_ENDE, exc)
        finally:
            try:
                ser.close()
            except Exception:
                pass


@dataclass(slots=True)
class _Offen:
    kennung: str | None  # uid, None bei „gesperrt“
    vorgang: str


class Leser:
    """Verbindet sich mit dem Leser, überwacht ihn und gibt Ereignisse aus.

    ``ausgabe`` bekommt jedes Ereignis (``LeserHallo``, ``Aufgelegt``, ...).
    ``port`` ist ein Pfad oder ein Suchmuster (Mac: ``/dev/cu.usbmodem*``).
    """

    def __init__(
        self,
        ausgabe: Callable[[ev.Ereignis], None],
        port: str = MAC_SUCHMUSTER,
        *,
        watchdog_s: float = WATCHDOG_S,
        hello_timeout_s: float = HELLO_TIMEOUT_S,
        ping_tries: int = PING_TRIES,
        backoff_s: tuple[float, ...] = RECONNECT_BACKOFF_S,
        vorgang_id: Callable[[], str] = lambda: secrets.token_hex(4),
        schlafen: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._ausgabe = ausgabe
        self._port = port
        self._watchdog_s = watchdog_s
        self._hello_timeout_s = hello_timeout_s
        self._ping_tries = ping_tries
        self._backoff = backoff_s
        self._neue_id = vorgang_id
        self._schlafen = schlafen
        self._task: asyncio.Task | None = None
        self._thread: _SerielleThread | None = None
        self._stopp = False
        self._backoff_i = 0
        self._ausfall = False  # ein Alarm je Ausfall
        self._seq_erwartet = 0
        self._offen: _Offen | None = None
        self._wiedermeldung = False  # erste PLACED/LOCKED nach HELLO
        self._log_zeiten: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Steuerung
    # ------------------------------------------------------------------

    def start(self) -> asyncio.Task:
        self._stopp = False
        self._task = asyncio.get_running_loop().create_task(self._lauf(), name="tobibox-reader")
        return self._task

    async def stop(self) -> None:
        self._stopp = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._trenne_warten()

    def ping(self) -> None:
        """``PING`` an den Leser senden (Befehl ``LeserPing``)."""
        if self._thread is not None:
            self._thread.schreibe(PING_ZEILE)

    # ------------------------------------------------------------------
    # Hilfen
    # ------------------------------------------------------------------

    def _trenne(self) -> None:
        if self._thread is not None:
            self._thread.stoppe()
            self._thread = None

    async def _trenne_warten(self) -> None:
        """Thread beenden und abwarten, damit er dem neuen keine Bytes wegliest."""
        thread = self._thread
        self._trenne()
        if thread is not None:
            await asyncio.get_running_loop().run_in_executor(None, thread.join, 2.0)

    def _finde_pfad(self) -> str | None:
        treffer = sorted(glob.glob(self._port))
        if treffer:
            return treffer[0]
        return None

    def _begrenzt_loggen(self, ebene: int, schluessel: str, text: str, *args: object) -> None:
        """Höchstens eine Protokollzeile je Schlüssel und Sekunde."""
        jetzt = time.monotonic()
        if jetzt - self._log_zeiten.get(schluessel, -10.0) >= 1.0:
            self._log_zeiten[schluessel] = jetzt
            log.log(ebene, text, *args)

    def _alarm(self, grund: str) -> None:
        if self._ausfall:
            log.debug("weiterer Fehlschlag im selben Ausfall: %s", grund)
            return
        self._ausfall = True
        log.warning("Leser-Ausfall: %s", grund)
        self._ausgabe(ev.LeserAlarm(grund))  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Hauptschleife
    # ------------------------------------------------------------------

    async def _lauf(self) -> None:
        """Die Aufgabe darf nie still sterben: jeder Durchlauf fängt Ausnahmen ab."""
        try:
            while not self._stopp:
                try:
                    await self._verbindung()
                except Exception:
                    log.exception("Fehler in der Leser-Schleife")
                    try:
                        self._alarm("getrennt")
                    except Exception:
                        log.exception("Alarm konnte nicht zugestellt werden")
                try:
                    await self._trenne_warten()
                except Exception:
                    log.exception("Trennen fehlgeschlagen")
                if self._stopp:
                    break
                warte = self._backoff[min(self._backoff_i, len(self._backoff) - 1)]
                self._backoff_i += 1
                try:
                    await self._schlafen(warte)
                except Exception:
                    log.exception("Warten fehlgeschlagen")
                    await asyncio.sleep(warte)
        finally:
            if self._thread is not None:
                self._thread.stoppe()  # `stop()` wartet danach auf das Ende des Threads

    async def _verbindung(self) -> None:
        """Eine Verbindung vom Öffnen bis zum Ausfall; meldet den Ausfall."""
        pfad = self._finde_pfad()
        if pfad is None:
            self._alarm("getrennt")
            return
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        thread = _SerielleThread(pfad, loop, q)
        self._thread = thread
        thread.start()
        art, wert = await q.get()
        if art != _OFFEN:
            log.debug("Öffnen von %s gescheitert: %s", pfad, wert)
            self._alarm("getrennt")
            return

        hallo = False
        ping_da = False  # erst HELLO nach unserem PING zählt
        versuche = 1
        thread.schreibe(PING_ZEILE)
        frist = loop.time() + self._hello_timeout_s
        while True:
            warte = max(0.0, frist - loop.time())
            try:
                art, wert = await asyncio.wait_for(q.get(), timeout=warte)
            except asyncio.TimeoutError:
                if hallo:
                    self._alarm("kein_herzschlag")
                    return
                if versuche >= self._ping_tries:
                    self._alarm("hello_timeout")
                    return
                versuche += 1
                thread.schreibe(PING_ZEILE)
                frist = loop.time() + self._hello_timeout_s
                continue

            if art == _ENDE or art == _FEHLER:
                self._alarm("getrennt")
                return
            if art == _PING:
                ping_da = True
                continue
            if art == _ZU_LANG:
                self._begrenzt_loggen(logging.WARNING, "too_long", "Zeile verworfen: too_long")
                continue
            # art == _ZEILE
            zeile = self._parse(wert)
            if zeile is None:
                continue
            if not ping_da:
                log.debug("Zeile vor dem PING verworfen: %s", zeile.typ)
                continue
            if zeile.typ == "HELLO":
                if int(zeile.felder["proto"]) not in PROTO_UNTERSTUETZT:
                    self._alarm("proto_unbekannt")
                    return
                hallo = True
                self._ausfall = False
                self._backoff_i = 0
                self._seq_erwartet = 0
                self._wiedermeldung = True
                log.info(
                    "Leser verbunden",
                    extra={"baustein": "reader", "ereignis": "leser_verbunden", "ergebnis": "ok",
                           "daten": {"fw": zeile.felder["fw"], "proto": int(zeile.felder["proto"])}},
                )
                self._ausgabe(hallo_ereignis(zeile))
                if zeile.verworfen:
                    self._begrenzt_loggen(logging.WARNING, "caps", "HELLO: ungültiges caps wie fehlend behandelt")
                frist = loop.time() + self._watchdog_s
                continue
            if not hallo:
                log.debug("Zeile vor HELLO verworfen: %s", zeile.typ)
                continue
            if zeile.typ == "HB":
                self._ausgabe(_herzschlag(zeile))
                frist = loop.time() + self._watchdog_s
                continue
            self._verarbeite(zeile)

    # ------------------------------------------------------------------
    # Zeilen
    # ------------------------------------------------------------------

    def _parse(self, roh: bytes) -> Zeile | None:
        try:
            zeile = parse_zeile(roh.decode("latin-1"))
        except ZeilenFehler as fehler:
            grund = fehler.grund
            if grund == "empty_line":
                return None
            if grund == "unknown_type":
                self._begrenzt_loggen(logging.DEBUG, grund, "Zeile verworfen: %s", grund)
            else:
                self._begrenzt_loggen(logging.WARNING, grund, "Zeile verworfen: %s", grund)
            return None
        for name in zeile.unbekannt:
            self._begrenzt_loggen(logging.DEBUG, f"{zeile.typ}.{name}", "Zusatzfeld ignoriert: %s.%s", zeile.typ, name)
        return zeile

    def _pruefe_seq(self, seq: int) -> bool:
        """Prüft ``seq`` (Abschnitt 5); gibt ``True`` bei erkanntem ``seq_reset`` zurück."""
        reset = False
        if seq != self._seq_erwartet:
            if seq > self._seq_erwartet:
                log.warning("seq_gap: erwartet %d, erhalten %d", self._seq_erwartet, seq)
            else:
                log.warning("seq_reset: erwartet %d, erhalten %d", self._seq_erwartet, seq)
                reset = True
        self._seq_erwartet = (seq + 1) % _SEQ_MODUL
        return reset

    def _verarbeite(self, zeile: Zeile) -> None:
        f = zeile.felder
        if zeile.typ == "LADER":
            # Strom am Eingang der Box (Ein/Aus, 10.11.): ein Pegel, kein ``seq``; auch eine Wiederholung nach ``HELLO`` geht weiter
            self._ausgabe(ev.LaderGeaendert(f["in"] == "1", "leser"))
            return
        if zeile.typ == "ERR":
            self._ausgabe(ev.LeserFehler(f["code"], f["detail"], schwere(f["code"])))  # type: ignore[arg-type]
            return
        seq = int(f["seq"])
        reset = self._pruefe_seq(seq)
        if zeile.typ == "REMOVED":
            vorgang = self._offen.vorgang if self._offen is not None else None
            self._offen = None
            self._ausgabe(ev.Abgehoben(seq, vorgang))
            return
        # PLACED oder LOCKED: Vorgangs-ID (core-interface.md, 3.1)
        kennung = f["uid"] if zeile.typ == "PLACED" else None
        wieder = self._wiedermeldung or seq == 0 or reset
        self._wiedermeldung = False
        if wieder and self._offen is not None and self._offen.kennung == kennung:
            vorgang = self._offen.vorgang
        else:
            vorgang = self._neue_id()
        self._offen = _Offen(kennung, vorgang)
        if zeile.typ == "PLACED":
            self._ausgabe(ev.Aufgelegt(f["uid"], f["type"], f["tonie"] == "1", seq, vorgang))  # type: ignore[arg-type]
        else:
            self._ausgabe(ev.Gesperrt(seq, vorgang))


def hallo_ereignis(zeile: Zeile) -> ev.LeserHallo:
    """``LeserHallo`` aus einer gültigen ``HELLO``-Zeile (``caps`` fehlt: ``""``)."""
    f = zeile.felder
    return ev.LeserHallo(int(f["proto"]), f["fw"], f["build"], f["pn5180"], f.get("caps", ""))


def _herzschlag(zeile: Zeile) -> ev.LeserHerzschlag:
    f = zeile.felder
    return ev.LeserHerzschlag(
        present=f["present"] == "1",
        up_s=int(f["up"]),
        polls=int(f["polls"]),
        hits=int(f["hits"]),
        rejected=int(f["rejected"]),
        errors=int(f["errors"]),
        cycle_ms=int(f["cycle_ms"]),
    )
