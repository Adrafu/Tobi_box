"""``tools/fake_reader.py`` spricht Protokoll v1: der echte ``Leser`` versteht ihn."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader  # noqa: E402

from tobibox import events as ev  # noqa: E402
from tobibox.protocol import parse_zeile  # noqa: E402
from tobibox.reader import Leser  # noqa: E402

UID = "04a1b2c3"


async def warte(bedingung, timeout: float = 4.0) -> None:
    ende = time.monotonic() + timeout
    while time.monotonic() < ende:
        if bedingung():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Bedingung nicht rechtzeitig erfüllt")


@pytest.fixture
async def lauf(tmp_path):
    ereignisse: list = []
    with fake_reader.FakeReader(tmp_path / "ttyACM0", hb_intervall_s=0.1) as fr:
        leser = Leser(ereignisse.append, str(tmp_path / "ttyACM*"), watchdog_s=1.0, hello_timeout_s=0.5,
                      backoff_s=(0.02, 0.05))
        leser.start()
        yield fr, ereignisse
        await leser.stop()


async def test_hallo_auf_ping_und_herzschlag(lauf):
    fr, e = lauf
    await warte(lambda: any(isinstance(x, ev.LeserHallo) for x in e))
    await warte(lambda: any(isinstance(x, ev.LeserHerzschlag) for x in e))
    assert "PING" in fr.empfangen


async def test_auflegen_sperren_abheben(lauf):
    fr, e = lauf
    await warte(lambda: any(isinstance(x, ev.LeserHallo) for x in e))
    assert fake_reader.befehl(fr, f"place {UID}")
    assert fake_reader.befehl(fr, "remove")
    assert fake_reader.befehl(fr, "lock")
    assert fake_reader.befehl(fr, "err pn5180_timeout busy")
    await warte(lambda: any(isinstance(x, ev.Gesperrt) for x in e) and any(isinstance(x, ev.LeserFehler) for x in e))
    a = next(x for x in e if isinstance(x, ev.Aufgelegt))
    assert (a.uid, a.typ, a.tonie, a.seq) == (UID, "ntag", False, 0)
    assert next(x for x in e if isinstance(x, ev.Abgehoben)).seq == 1
    assert next(x for x in e if isinstance(x, ev.Gesperrt)).seq == 2
    assert not any(isinstance(x, ev.LeserAlarm) for x in e)


def test_tonie_kennung_setzt_tonie_flag(tmp_path):
    with fake_reader.FakeReader(tmp_path / "t", hb_intervall_s=None) as fr:
        geschrieben: list[str] = []
        fr.sende_zeile = geschrieben.append  # type: ignore[method-assign]
        fr.place("e0040312345678ab", "iso15693")
        fr.place("04a1b2c3", "ntag")
    z = [parse_zeile(x) for x in geschrieben]
    assert [x.felder["tonie"] for x in z] == ["1", "0"]
    assert [x.felder["seq"] for x in z] == ["0", "1"]


def test_unbekannter_befehl_und_quit(tmp_path, capsys):
    with fake_reader.FakeReader(tmp_path / "t", hb_intervall_s=None) as fr:
        assert fake_reader.befehl(fr, "tanzen")
        assert fake_reader.befehl(fr, "")
        assert not fake_reader.befehl(fr, "quit")
    assert "unbekannter Befehl" in capsys.readouterr().err


async def test_ping_meldet_liegenden_tobie_erneut_mit_seq_null(lauf):
    fr, e = lauf
    await warte(lambda: any(isinstance(x, ev.LeserHallo) for x in e))
    fake_reader.befehl(fr, f"place {UID}")
    fake_reader.befehl(fr, "remove")
    fake_reader.befehl(fr, f"place {UID}")  # seq 2
    await warte(lambda: sum(isinstance(x, ev.Aufgelegt) for x in e) == 2)
    fr.empfangen.clear()
    fr.ping()  # wie ein PING des Dienstes nach einem Neustart
    await warte(lambda: sum(isinstance(x, ev.Aufgelegt) for x in e) == 3)
    a = [x for x in e if isinstance(x, ev.Aufgelegt)][-1]
    assert (a.uid, a.seq) == (UID, 0)


def test_ping_meldet_gesperrten_und_nichts_nach_remove(tmp_path):
    with fake_reader.FakeReader(tmp_path / "t", hb_intervall_s=None) as fr:
        fr.lock()
        fr.ping()
        fr.remove()
        fr.ping()
        gelesen = b""
        ende = time.monotonic() + 1.0
        while time.monotonic() < ende and gelesen.count(b"\n") < 5:
            try:
                gelesen += os.read(fr._slave, 4096)
            except OSError:
                time.sleep(0.01)
        zeilen = gelesen.decode().replace("\r", "").split("\n")
        assert [z.split()[0] for z in zeilen if z] == ["LOCKED", "HELLO", "LOCKED", "REMOVED", "HELLO"]
        assert "LOCKED seq=0" in zeilen
