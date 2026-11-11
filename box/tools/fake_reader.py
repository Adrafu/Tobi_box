#!/usr/bin/env python3
"""Falscher Leser: gibt Protokollzeilen (``reader-v1.md``) auf ein Pseudo-Terminal aus.

Zum Vorführen und Testen ohne Hardware. Das Skript legt ein Pseudo-Terminal an
und verweist mit einem Symlink darauf (Vorgabe ``/tmp/tobibox-fake/ttyACM0``);
der Box-Dienst bekommt diesen Pfad als ``[leser] geraet``.

    python tools/fake_reader.py --link /tmp/tobibox-fake/ttyACM0

Befehle (je eine Zeile auf stdin):

    place <uid> [ntag|iso15693]   Figur auflegen (PLACED)
    lock                          gesperrten Tonie auflegen (LOCKED)
    remove                        Figur abheben (REMOVED)
    err <code> <detail>           Fehlerzeile (ERR)
    hello                         HELLO nochmals senden (setzt seq auf 0)
    haengt                        Firmware hängt: keine Antwort auf PING, kein HB (bis ``neustart``)
    neustart                      Firmware startet neu (wie nach einem USB-Hard-Reset)
    power on|off                  Strom am Eingang der Box (nur mit --strom): sendet LADER in=1|0
    quit

Auf ``PING`` antwortet der Leser wie die Firmware: ``HELLO``, ``seq`` zurück auf 0 und, wenn
ein Tobie liegt, dessen ``PLACED`` (oder ``LOCKED``) erneut mit ``seq=0``. Alle 2 s kommt ``HB``.

Mit ``--strom`` spielt er eine Firmware mit ``caps=strom`` (Ein/Aus, 10.11., Schritt 1): Das ``HELLO`` endet auf ``caps=strom``, und
unmittelbar nach jedem ``HELLO`` folgt ``LADER in=<0|1>`` (vor einer erneuten Meldung der Figur); ``power on|off`` ändert den Wert und sendet ``LADER``.
"""

from __future__ import annotations

import argparse
import os
import select
import sys
import threading
import time
from pathlib import Path

HALLO = "HELLO proto=1 fw=1.0.0 build=fa4e0000 pn5180=4.2"
HALLO_STROM = "HELLO proto=1 fw=1.1.0 build=fa4e0000 pn5180=4.2 caps=strom"
HB_INTERVALL_S = 2.0


class FakeReader:
    """Ein Pseudo-Terminal mit der Firmware-Seite."""

    def __init__(self, link: str | Path, *, hallo: str = HALLO, hb_intervall_s: float | None = HB_INTERVALL_S,
                 antwortet_auf_ping: bool = True, strom: bool | None = None) -> None:
        self.link = Path(link)
        #: ``None``: Firmware ohne ``caps``; ``True``/``False``: Firmware mit ``caps=strom`` und diesem Wert von ``STROM_IN``
        self.strom = strom
        self.hallo = HALLO_STROM if strom is not None and hallo == HALLO else hallo
        self.hb_intervall_s = hb_intervall_s
        self.antwortet_auf_ping = antwortet_auf_ping
        self.empfangen: list[str] = []
        self.seq = 0
        self._haengt = False
        self.present = False
        self._belegung: tuple[str, str, str] | None = None  # ("PLACED" oder "LOCKED", uid, typ)
        self._start = time.monotonic()
        self._zaehler = {"polls": 0, "hits": 0, "rejected": 0, "errors": 0}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.master, self._slave = os.openpty()  # Slave offen halten (macOS: sonst EIO beim Lesen)
        self.pfad = os.ttyname(self._slave)
        os.set_blocking(self.master, False)
        self.link.parent.mkdir(parents=True, exist_ok=True)
        if self.link.is_symlink() or self.link.exists():
            self.link.unlink()
        self.link.symlink_to(self.pfad)
        self._threads = [threading.Thread(target=self._lesen, daemon=True)]
        if hb_intervall_s:
            self._threads.append(threading.Thread(target=self._herzschlag, daemon=True))
        for t in self._threads:
            t.start()

    # -- Ausgabe ------------------------------------------------------------

    def sende_zeile(self, zeile: str) -> None:
        with self._lock:
            daten = (zeile + "\n").encode("ascii")
            try:
                os.write(self.master, daten)
            except BlockingIOError:  # Puffer voll (niemand liest): verwerfen statt hängen
                print(f"fake_reader: Puffer voll, Zeile verworfen: {zeile!r}", file=sys.stderr)
            except OSError:
                pass

    def hello(self) -> None:
        self.seq = 0
        self.sende_zeile(self.hallo)
        if self.strom is not None:
            self.sende_zeile(f"LADER in={int(self.strom)}")  # unmittelbar nach jedem HELLO (reader-v1.md, Abschnitt 3)

    def setze_strom(self, an: bool) -> None:
        """``STROM_IN`` hat sich (entprellt) geändert: ``LADER`` senden."""
        self.strom = an
        self.sende_zeile(f"LADER in={int(an)}")

    def ping(self) -> None:
        """Wie die Firmware: HELLO, seq auf 0 und eine liegende Figur erneut melden."""
        self.hello()
        if self.present and self._belegung is not None:
            art, uid, typ = self._belegung
            if art == "LOCKED":
                self.sende_zeile(f"LOCKED seq={self._naechste_seq()}")
            else:
                self._sende_placed(uid, typ)

    def haengen(self) -> None:
        """Firmware hängt (11.11.): keine Antwort auf ``PING``, kein ``HB``."""
        self.antwortet_auf_ping = False
        self._haengt = True

    def neustart(self) -> None:
        """Hard-Reset über USB: die Firmware startet neu (``HELLO``, ``seq`` 0, Tobie weg wie nach dem Einschalten)."""
        self.antwortet_auf_ping = True
        self._haengt = False
        self.present = False
        self._belegung = None
        self.hello()

    def _naechste_seq(self) -> int:
        s = self.seq
        self.seq = (self.seq + 1) % 4294967296
        return s

    def place(self, uid: str, typ: str = "ntag") -> None:
        self.present = True
        self._belegung = ("PLACED", uid, typ)
        self._zaehler["hits"] += 1
        self._sende_placed(uid, typ)

    def _sende_placed(self, uid: str, typ: str) -> None:
        tonie = 1 if typ == "iso15693" and uid.startswith("e00403") else 0
        self.sende_zeile(f"PLACED uid={uid} type={typ} tonie={tonie} seq={self._naechste_seq()}")

    def lock(self) -> None:
        self.present = True
        self._belegung = ("LOCKED", "", "")
        self.sende_zeile(f"LOCKED seq={self._naechste_seq()}")

    def remove(self) -> None:
        self.present = False
        self._belegung = None
        self.sende_zeile(f"REMOVED seq={self._naechste_seq()}")

    def err(self, code: str, detail: str) -> None:
        self._zaehler["errors"] += 1
        self.sende_zeile(f"ERR code={code} detail={detail}")

    def herzschlag(self) -> None:
        if self._haengt:
            return
        z = self._zaehler
        z["polls"] += 10
        up = int(time.monotonic() - self._start)
        self.sende_zeile(
            f"HB up={up} present={int(self.present)} polls={z['polls']} hits={z['hits']} "
            f"rejected={z['rejected']} errors={z['errors']} cycle_ms=100"
        )

    # -- Threads ------------------------------------------------------------

    def _herzschlag(self) -> None:
        assert self.hb_intervall_s
        while not self._stop.wait(self.hb_intervall_s):
            self.herzschlag()

    def _lesen(self) -> None:
        puffer = b""
        while not self._stop.is_set():
            try:
                bereit, _, _ = select.select([self.master], [], [], 0.05)
            except (OSError, ValueError):
                return
            if not bereit:
                continue
            try:
                daten = os.read(self.master, 1024)
            except OSError:
                time.sleep(0.02)
                continue
            if not daten:
                time.sleep(0.02)
                continue
            puffer += daten
            while b"\n" in puffer:
                zeile, _, puffer = puffer.partition(b"\n")
                text = zeile.decode("ascii", "replace").rstrip("\r")
                self.empfangen.append(text)
                if text == "PING" and self.antwortet_auf_ping:
                    self.ping()

    # -- Ende ---------------------------------------------------------------

    def schliessen(self) -> None:
        self._stop.set()
        try:
            if self.link.is_symlink():
                self.link.unlink()
        except OSError:
            pass
        for fd in (self.master, self._slave):
            try:
                os.close(fd)
            except OSError:
                pass

    def __enter__(self) -> FakeReader:
        return self

    def __exit__(self, *_: object) -> None:
        self.schliessen()


def befehl(leser: FakeReader, zeile: str) -> bool:
    """Eine Eingabezeile ausführen. ``False`` bei ``quit``."""
    teile = zeile.split()
    if not teile:
        return True
    wort, args = teile[0], teile[1:]
    if wort == "quit":
        return False
    if wort == "place" and args:
        leser.place(args[0], args[1] if len(args) > 1 else "ntag")
    elif wort == "lock":
        leser.lock()
    elif wort == "remove":
        leser.remove()
    elif wort == "hello":
        leser.hello()
    elif wort == "haengt":
        leser.haengen()
    elif wort == "neustart":
        leser.neustart()
    elif wort == "power" and args in (["on"], ["off"]) and leser.strom is not None:
        leser.setze_strom(args[0] == "on")
    elif wort == "err" and len(args) >= 2:
        leser.err(args[0], " ".join(args[1:]))
    else:
        print(f"unbekannter Befehl: {zeile!r}", file=sys.stderr)
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--link", default="/tmp/tobibox-fake/ttyACM0", help="Pfad des Symlinks auf das Pseudo-Terminal")
    p.add_argument("--kein-hb", action="store_true", help="keinen Herzschlag senden")
    p.add_argument("--strom", choices=("an", "aus"), help="Firmware mit caps=strom spielen; Anfangswert von LADER")
    a = p.parse_args(argv)
    strom = None if a.strom is None else a.strom == "an"
    with FakeReader(a.link, hb_intervall_s=None if a.kein_hb else HB_INTERVALL_S, strom=strom) as leser:
        print(f"falscher Leser auf {leser.link} -> {leser.pfad}", file=sys.stderr)
        leser.hello()
        for zeile in sys.stdin:
            if not befehl(leser, zeile):
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
