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
    quit

Auf ``PING`` antwortet der Leser mit ``HELLO``; alle 2 s kommt ``HB``.
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
HB_INTERVALL_S = 2.0


class FakeReader:
    """Ein Pseudo-Terminal mit der Firmware-Seite."""

    def __init__(self, link: str | Path, *, hallo: str = HALLO, hb_intervall_s: float | None = HB_INTERVALL_S,
                 antwortet_auf_ping: bool = True) -> None:
        self.link = Path(link)
        self.hallo = hallo
        self.hb_intervall_s = hb_intervall_s
        self.antwortet_auf_ping = antwortet_auf_ping
        self.empfangen: list[str] = []
        self.seq = 0
        self.present = False
        self._start = time.monotonic()
        self._zaehler = {"polls": 0, "hits": 0, "rejected": 0, "errors": 0}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.master, slave = os.openpty()
        self.pfad = os.ttyname(slave)
        os.close(slave)
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
            try:
                os.write(self.master, (zeile + "\n").encode("ascii"))
            except OSError:
                pass

    def hello(self) -> None:
        self.seq = 0
        self.sende_zeile(self.hallo)

    def _naechste_seq(self) -> int:
        s = self.seq
        self.seq = (self.seq + 1) % 4294967296
        return s

    def place(self, uid: str, typ: str = "ntag") -> None:
        tonie = 1 if typ == "iso15693" and uid.startswith("e00403") else 0
        self.present = True
        self._zaehler["hits"] += 1
        self.sende_zeile(f"PLACED uid={uid} type={typ} tonie={tonie} seq={self._naechste_seq()}")

    def lock(self) -> None:
        self.present = True
        self.sende_zeile(f"LOCKED seq={self._naechste_seq()}")

    def remove(self) -> None:
        self.present = False
        self.sende_zeile(f"REMOVED seq={self._naechste_seq()}")

    def err(self, code: str, detail: str) -> None:
        self._zaehler["errors"] += 1
        self.sende_zeile(f"ERR code={code} detail={detail}")

    def herzschlag(self) -> None:
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
                    self.hello()

    # -- Ende ---------------------------------------------------------------

    def schliessen(self) -> None:
        self._stop.set()
        try:
            if self.link.is_symlink():
                self.link.unlink()
        except OSError:
            pass
        try:
            os.close(self.master)
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
    elif wort == "err" and len(args) >= 2:
        leser.err(args[0], " ".join(args[1:]))
    else:
        print(f"unbekannter Befehl: {zeile!r}", file=sys.stderr)
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--link", default="/tmp/tobibox-fake/ttyACM0", help="Pfad des Symlinks auf das Pseudo-Terminal")
    p.add_argument("--kein-hb", action="store_true", help="keinen Herzschlag senden")
    a = p.parse_args(argv)
    with FakeReader(a.link, hb_intervall_s=None if a.kein_hb else HB_INTERVALL_S) as leser:
        print(f"falscher Leser auf {leser.link} -> {leser.pfad}", file=sys.stderr)
        leser.hello()
        for zeile in sys.stdin:
            if not befehl(leser, zeile):
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
