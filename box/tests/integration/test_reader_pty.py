"""Leser über ein Pseudo-Terminal: Trennung, Müllzeilen, Neustart des ESP32, Wächter-Alarm.

Die Gegenseite (``Leitung``) spielt die Firmware: Sie liegt am Master-Ende eines
``os.openpty()``. Der Leser öffnet das Slave-Ende über einen Symlink im
temporären Ordner (so lässt sich „Gerät weg“ und „Gerät wieder da“ nachstellen).
"""

from __future__ import annotations

import asyncio
import os
import re
import select
import threading
import time
from pathlib import Path

import pytest

from tobibox import events as ev
from tobibox import reader
from tobibox.reader import Leser

HALLO = b"HELLO proto=1 fw=1.0.0 build=a1b2c3d pn5180=4.2\n"
HB = b"HB up=10 present=%d polls=50 hits=10 rejected=0 errors=0 cycle_ms=100\n"
UID = "04a1b2c3"
UID2 = "04ffeedd"


def placed(uid, seq):
    return f"PLACED uid={uid} type=ntag tonie=0 seq={seq}\n".encode()


def removed(seq):
    return f"REMOVED seq={seq}\n".encode()


class Leitung:
    """Pseudo-Terminal mit Firmware-Seite; ``auto_hallo`` antwortet auf PING mit HELLO."""

    def __init__(self, ordner: Path, name: str = "ttyACM0", auto_hallo: bool = True) -> None:
        self.link = ordner / name
        self.auto_hallo = auto_hallo
        self.hallo = HALLO
        self.pings = 0
        self.empfangen: list[bytes] = []
        self._stop = threading.Event()
        self.master, slave = os.openpty()
        self.pfad = os.ttyname(slave)
        os.close(slave)
        if self.link.is_symlink():
            self.link.unlink()
        self.link.symlink_to(self.pfad)
        self._thread = threading.Thread(target=self._lauf, daemon=True)
        self._thread.start()

    def _lauf(self) -> None:
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
            except OSError:  # EIO: die Gegenseite hat zu
                time.sleep(0.02)
                continue
            if not daten:
                time.sleep(0.02)
                continue
            puffer += daten
            while b"\n" in puffer:
                zeile, _, puffer = puffer.partition(b"\n")
                self.empfangen.append(zeile)
                if zeile == b"PING":
                    self.pings += 1
                    if self.auto_hallo:
                        self.sende(self.hallo)

    def sende(self, daten: bytes) -> None:
        try:
            os.write(self.master, daten)
        except OSError:
            pass

    def trennen(self) -> None:
        """USB ziehen: Gerät und Verweis verschwinden."""
        self._stop.set()
        if self.link.is_symlink():
            self.link.unlink()
        try:
            os.close(self.master)
        except OSError:
            pass

    close = trennen


async def warte(bedingung, timeout: float = 4.0) -> None:
    ende = time.monotonic() + timeout
    while time.monotonic() < ende:
        if bedingung():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Bedingung nicht rechtzeitig erfüllt")


def zaehle(ereignisse, typ, **felder) -> int:
    return sum(1 for e in ereignisse if isinstance(e, typ) and all(getattr(e, k) == v for k, v in felder.items()))


@pytest.fixture
def leitung(tmp_path):
    l = Leitung(tmp_path)
    yield l
    l.trennen()


@pytest.fixture
async def lauf(tmp_path):
    """Leser mit kurzen Zeiten, noch nicht gestartet; gibt (leser, ereignisse) zurück."""
    ereignisse: list = []
    leser = Leser(
        ereignisse.append,
        str(tmp_path / "ttyACM*"),
        watchdog_s=0.6,
        hello_timeout_s=0.3,
        backoff_s=(0.02, 0.04, 0.08, 0.1),
    )
    yield leser, ereignisse
    await leser.stop()


# --------------------------------------------------------------------------


async def test_verbindung_ping_hallo_und_zeilen(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    assert leitung.empfangen[0] == b"PING"
    assert e[0] == ev.LeserHallo(1, "1.0.0", "a1b2c3d", "4.2")

    leitung.sende(HB % 0)
    leitung.sende(placed(UID, 0))
    leitung.sende(HB % 1)
    leitung.sende(removed(1))
    leitung.sende(b"LOCKED seq=2\n")
    leitung.sende(b"ERR code=unlock_failed detail=privacy mode active\n")
    leitung.sende(b"ERR code=pn5180_timeout detail=busy\n")
    leitung.sende(b"ERR code=future_thing detail=neu\n")
    await warte(lambda: zaehle(e, ev.LeserFehler) == 3)

    herz = [x for x in e if isinstance(x, ev.LeserHerzschlag)]
    assert [h.present for h in herz] == [False, True]
    a = next(x for x in e if isinstance(x, ev.Aufgelegt))
    assert (a.uid, a.typ, a.tonie, a.seq) == (UID, "ntag", False, 0)
    assert re.fullmatch(r"[0-9a-f]{8}", a.vorgang)
    ab = next(x for x in e if isinstance(x, ev.Abgehoben))
    assert ab == ev.Abgehoben(1, a.vorgang)
    g = next(x for x in e if isinstance(x, ev.Gesperrt))
    assert g.seq == 2 and g.vorgang != a.vorgang  # PLACED nach REMOVED: neue ID
    assert [(f.code, f.schwere) for f in e if isinstance(f, ev.LeserFehler)] == [
        ("unlock_failed", "hinweis"),
        ("pn5180_timeout", "fehler"),
        ("future_thing", "warnung"),
    ]
    assert zaehle(e, ev.LeserAlarm) == 0


async def test_muellzeilen_werden_verworfen_und_stoeren_nicht(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    muell = [
        b"ESP-ROM:esp32s3-20210327\n",
        b"\xff\xfe\x00 kaputt\n",
        b"\n",
        b"\r\n",
        b"A" * 500 + b"\n",
        b"PLACED uid=zz type=ntag tonie=0 seq=1\n",
        b"PLACED  uid=04a1b2c3 type=ntag tonie=0 seq=1\n",
        b"HB up=1 present=7 polls=1 hits=1 rejected=0 errors=0 cycle_ms=1\n",
        b"PLACED uid=04a1b2c3 type=iso15693 tonie=0 seq=1\n",
        b"x" * 9000 + b"\n",  # länger als der Puffer: bis zum nächsten \n verworfen
    ]
    for zeile in muell:
        leitung.sende(zeile)
    leitung.sende(b"HB up=3 present=0 polls=2 hits=0 rejected=0 errors=0 cycle_ms=9\r\n")
    await warte(lambda: zaehle(e, ev.LeserHerzschlag) == 1)
    assert zaehle(e, ev.LeserHerzschlag) == 1
    assert zaehle(e, ev.Aufgelegt) == 0
    assert [type(x) for x in e] == [ev.LeserHallo, ev.LeserHerzschlag]  # nichts sonst


async def test_seq_luecke_wird_trotzdem_verarbeitet(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    leitung.sende(placed(UID, 0))
    leitung.sende(removed(5))  # Lücke: Zeilen gingen verloren
    await warte(lambda: zaehle(e, ev.Abgehoben) == 1)
    assert zaehle(e, ev.Aufgelegt) == 1


async def test_ping_loest_hallo_und_wiedermeldung_mit_gleicher_vorgang_id_aus(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    leitung.sende(placed(UID, 0))
    await warte(lambda: zaehle(e, ev.Aufgelegt) == 1)
    leser.ping()
    await warte(lambda: leitung.pings == 2 and zaehle(e, ev.LeserHallo) == 2)
    leitung.sende(placed(UID, 0))  # die Firmware meldet die liegende Figur erneut (seq 0)
    await warte(lambda: zaehle(e, ev.Aufgelegt) == 2)
    a1, a2 = [x for x in e if isinstance(x, ev.Aufgelegt)]
    assert a1.vorgang == a2.vorgang


async def test_neustart_des_esp32_hello_und_seq_bei_null(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    leitung.sende(placed(UID, 0))
    leitung.sende(b"HB up=9 present=1 polls=5 hits=3 rejected=0 errors=0 cycle_ms=60\n")
    await warte(lambda: zaehle(e, ev.Aufgelegt) == 1 and zaehle(e, ev.LeserHerzschlag) == 1)
    # Neustart: HELLO von selbst, seq beginnt wieder bei 0, dieselbe Figur liegt
    leitung.sende(HALLO)
    leitung.sende(placed(UID, 0))
    await warte(lambda: zaehle(e, ev.Aufgelegt) == 2)
    assert zaehle(e, ev.LeserHallo) == 2
    assert zaehle(e, ev.LeserAlarm) == 0
    a1, a2 = [x for x in e if isinstance(x, ev.Aufgelegt)]
    assert a2.seq == 0 and a2.vorgang == a1.vorgang
    # danach zählt die Erwartung ab 1 weiter, ohne Alarm und ohne Verwerfen
    leitung.sende(removed(1))
    await warte(lambda: zaehle(e, ev.Abgehoben) == 1)
    assert [x for x in e if isinstance(x, ev.Abgehoben)][0].vorgang == a1.vorgang
    # andere Figur nach dem nächsten Neustart: neue Vorgangs-ID
    leitung.sende(HALLO)
    leitung.sende(placed(UID2, 0))
    await warte(lambda: zaehle(e, ev.Aufgelegt) == 3)
    assert [x for x in e if isinstance(x, ev.Aufgelegt)][2].vorgang != a1.vorgang


async def test_seq_zurueck_ohne_hello_behaelt_die_vorgang_id(lauf, leitung):
    """Das HELLO ging verloren: erste Meldung mit seq=0 oder nach seq_reset ist eine Wiedermeldung."""
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    leitung.sende(placed(UID, 0))
    leitung.sende(removed(1))
    leitung.sende(placed(UID, 2))
    await warte(lambda: zaehle(e, ev.Aufgelegt) == 2)
    a1, a2 = [x for x in e if isinstance(x, ev.Aufgelegt)]
    assert a1.vorgang != a2.vorgang  # nach REMOVED: neue ID
    leitung.sende(placed(UID, 0))  # seq fällt zurück (Neustart, HELLO verloren), gleiche Figur
    await warte(lambda: zaehle(e, ev.Aufgelegt) == 3)
    a3 = [x for x in e if isinstance(x, ev.Aufgelegt)][2]
    assert a3.vorgang == a2.vorgang
    # jetzt wird 1 erwartet; 5 ist eine Lücke (kein Reset, kein seq=0): neue ID
    leitung.sende(placed(UID, 5))
    await warte(lambda: zaehle(e, ev.Aufgelegt) == 4)
    assert [x for x in e if isinstance(x, ev.Aufgelegt)][3].vorgang != a3.vorgang


async def test_seq_reset_mit_seq_groesser_null_behaelt_die_id(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    for s in range(0, 6):
        leitung.sende(placed(UID2, s) if s == 0 else b"HB up=1 present=1 polls=1 hits=1 rejected=0 errors=0 cycle_ms=1\n")
    leitung.sende(removed(1))
    leitung.sende(placed(UID, 2))
    leitung.sende(placed(UID, 1))  # erwartet 3, erhalten 1: seq_reset, gleiche Kennung
    await warte(lambda: zaehle(e, ev.Aufgelegt) == 3)
    a = [x for x in e if isinstance(x, ev.Aufgelegt)]
    assert a[2].vorgang == a[1].vorgang


async def test_abgehoben_ohne_bekannte_vorgang_id(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    leitung.sende(removed(0))
    await warte(lambda: zaehle(e, ev.Abgehoben) == 1)
    assert e[-1] == ev.Abgehoben(0, None)


async def test_waechter_alarm_ein_alarm_je_ausfall(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    t0 = time.monotonic()
    await warte(lambda: zaehle(e, ev.LeserAlarm) == 1)
    assert 0.5 <= time.monotonic() - t0 <= 1.5  # ~0,6 s ohne HB
    assert e[-1] == ev.LeserAlarm("kein_herzschlag")
    # weitere Fehlschläge im selben Ausfall: kein weiterer Alarm
    leitung.auto_hallo = False
    pings_vorher = leitung.pings
    await asyncio.sleep(1.8)  # mehrere Verbindungsversuche mit hello_timeout
    assert leitung.pings > pings_vorher
    assert zaehle(e, ev.LeserAlarm) == 1
    # das nächste gültige HELLO beendet den Ausfall; mit Herzschlägen kommt kein Alarm mehr
    leitung.auto_hallo = True
    await warte(lambda: zaehle(e, ev.LeserHallo) == 2)
    for _ in range(8):
        leitung.sende(HB % 0)
        await asyncio.sleep(0.2)
    assert zaehle(e, ev.LeserAlarm) == 1
    # ein neuer Ausfall bringt wieder genau einen Alarm
    await warte(lambda: zaehle(e, ev.LeserAlarm) == 2)
    assert e[-1] == ev.LeserAlarm("kein_herzschlag")


async def test_herzschlaege_halten_den_waechter_ruhig(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    for _ in range(10):
        leitung.sende(HB % 0)
        await asyncio.sleep(0.2)  # 2 s > watchdog_s 0,6 s
    assert zaehle(e, ev.LeserAlarm) == 0
    assert zaehle(e, ev.LeserHerzschlag) == 10


async def test_kein_hello_nach_ping_tries_gibt_hello_timeout(lauf, leitung):
    leitung.auto_hallo = False
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserAlarm) == 1)
    assert e == [ev.LeserAlarm("hello_timeout")]
    assert leitung.pings >= reader.PING_TRIES
    await asyncio.sleep(1.0)
    assert zaehle(e, ev.LeserAlarm) == 1 and zaehle(e, ev.LeserHallo) == 0


async def test_proto_unbekannt_alarm_ohne_hallo(lauf, leitung):
    leitung.hallo = b"HELLO proto=2 fw=2.0.0 build=a1b2c3d pn5180=4.2\n"
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserAlarm) == 1)
    assert e == [ev.LeserAlarm("proto_unbekannt")]
    await asyncio.sleep(0.6)
    assert zaehle(e, ev.LeserHallo) == 0 and zaehle(e, ev.LeserAlarm) == 1
    leitung.hallo = HALLO  # passende Firmware: der nächste Versuch klappt
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    assert zaehle(e, ev.LeserAlarm) == 1


async def test_trennung_ein_alarm_dann_wiederverbinden(tmp_path, lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    leitung.trennen()  # USB gezogen
    await warte(lambda: zaehle(e, ev.LeserAlarm) == 1)
    assert e[-1] == ev.LeserAlarm("getrennt")
    await asyncio.sleep(0.8)  # viele Versuche ohne Gerät
    assert zaehle(e, ev.LeserAlarm) == 1
    neu = Leitung(tmp_path)  # USB wieder eingesteckt
    try:
        await warte(lambda: zaehle(e, ev.LeserHallo) == 2)
        assert neu.pings >= 1
        neu.sende(HB % 0)
        await warte(lambda: zaehle(e, ev.LeserHerzschlag) == 1)
        assert zaehle(e, ev.LeserAlarm) == 1
    finally:
        neu.trennen()


async def test_geraet_beim_start_nicht_da_ein_alarm_getrennt(tmp_path):
    e: list = []
    leser = Leser(e.append, str(tmp_path / "ttyACM*"), backoff_s=(0.02, 0.04))
    leser.start()
    try:
        await warte(lambda: zaehle(e, ev.LeserAlarm) == 1)
        await asyncio.sleep(0.3)
        assert e == [ev.LeserAlarm("getrennt")]
        l = Leitung(tmp_path)
        try:
            await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
        finally:
            l.trennen()
    finally:
        await leser.stop()


async def test_stop_beendet_thread_und_task(lauf, leitung):
    leser, e = lauf
    leser.start()
    await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
    await leser.stop()
    assert not any(t.name == "tobibox-reader" and t.is_alive() for t in threading.enumerate())
    anzahl = len(e)
    leitung.sende(HB % 0)
    await asyncio.sleep(0.3)
    assert len(e) == anzahl


# --------------------------------------------------------------------------
# Öffnen ohne DTR/RTS, Suchmuster
# --------------------------------------------------------------------------


def test_serielle_wird_ohne_dtr_und_rts_geoeffnet(monkeypatch):
    protokoll: list = []

    class Attrappe:
        def __setattr__(self, name, wert):
            protokoll.append(("set", name, wert))
            object.__setattr__(self, name, wert)

        def open(self):
            protokoll.append(("open",))

    monkeypatch.setattr(reader.serial, "Serial", Attrappe)
    reader.oeffne_seriell("/dev/cu.usbmodemX")
    i_open = protokoll.index(("open",))
    vorher = {(n, w) for art, *r in protokoll[:i_open] if art == "set" for n, w in [tuple(r)]}
    assert {("dtr", False), ("rts", False), ("dsrdtr", False), ("rtscts", False), ("baudrate", 115200)} <= vorher
    assert protokoll[-1] == ("open",)


def test_standard_suchmuster_ist_das_mac_muster():
    assert reader.MAC_SUCHMUSTER == "/dev/cu.usbmodem*"
    assert reader.WATCHDOG_S == 5 and reader.HELLO_TIMEOUT_S == 2 and reader.PING_TRIES == 3
    assert reader.RECONNECT_BACKOFF_S == (0.25, 0.5, 1.0, 2.0)


def test_suchmuster_nimmt_den_ersten_treffer(tmp_path):
    (tmp_path / "cu.usbmodem2").touch()
    (tmp_path / "cu.usbmodem1").touch()
    (tmp_path / "cu.other").touch()
    leser = Leser(lambda e: None, str(tmp_path / "cu.usbmodem*"))
    assert leser._finde_pfad() == str(tmp_path / "cu.usbmodem1")
    assert Leser(lambda e: None, str(tmp_path / "gibtsnicht*"))._finde_pfad() is None


async def test_backoff_folge_0_25_verdoppelt_bis_2_und_wird_durch_hello_zurueckgesetzt(tmp_path):
    pausen: list[float] = []
    echt = asyncio.sleep

    async def schlafen(s):
        pausen.append(s)
        await echt(0.002)

    e: list = []
    leser = Leser(e.append, str(tmp_path / "ttyACM*"), schlafen=schlafen)  # Standard-Backoff
    leser.start()
    try:
        await warte(lambda: len(pausen) >= 7)
        assert pausen[:7] == [0.25, 0.5, 1.0, 2.0, 2.0, 2.0, 2.0]
        assert zaehle(e, ev.LeserAlarm) == 1
        l = Leitung(tmp_path)
        await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
        n = len(pausen)
        l.trennen()
        await warte(lambda: len(pausen) > n)
        assert pausen[n] == 0.25  # ein gültiges HELLO hat die Folge zurückgesetzt
        assert zaehle(e, ev.LeserAlarm) == 2
    finally:
        await leser.stop()


async def test_alte_zeilen_vor_dem_ping_erreichen_den_kern_nicht(tmp_path):
    """Alter Puffer (HELLO, PLACED seq=0, REMOVED) wird verworfen; nur die Antwort auf PING zählt."""
    leitung = Leitung(tmp_path, auto_hallo=False)
    e: list = []
    leser = Leser(e.append, str(tmp_path / "ttyACM*"), watchdog_s=0.6, hello_timeout_s=0.5, backoff_s=(0.02,))
    try:
        alt = HALLO + placed(UID2, 0) + removed(1)
        leitung.sende(alt)  # schon im Puffer, bevor der Leser öffnet
        leser.start()
        await asyncio.sleep(0.1)
        leitung.sende(alt)  # und noch einmal während des Verwerfens
        await warte(lambda: leitung.pings >= 1)
        await asyncio.sleep(0.05)
        assert e == []
        leitung.sende(HALLO)
        await warte(lambda: zaehle(e, ev.LeserHallo) == 1)
        leitung.sende(placed(UID, 0))
        await warte(lambda: zaehle(e, ev.Aufgelegt) == 1)
        assert [type(x) for x in e] == [ev.LeserHallo, ev.Aufgelegt]
        assert e[1].uid == UID
    finally:
        await leser.stop()
        leitung.trennen()


async def test_ausnahme_im_rueckruf_beendet_die_aufgabe_nicht(tmp_path):
    leitung = Leitung(tmp_path)
    e: list = []
    aufrufe = {"n": 0}

    def rueckruf(x):
        aufrufe["n"] += 1
        if aufrufe["n"] == 1:
            raise RuntimeError("Rückruf kaputt")
        e.append(x)

    leser = Leser(rueckruf, str(tmp_path / "ttyACM*"), watchdog_s=0.6, hello_timeout_s=0.3, backoff_s=(0.02, 0.04))
    try:
        task = leser.start()
        await warte(lambda: zaehle(e, ev.LeserHallo) == 1)  # nach Alarm und neuem Verbinden
        assert zaehle(e, ev.LeserAlarm, grund="getrennt") == 1
        assert not task.done()
    finally:
        await leser.stop()
        leitung.trennen()
