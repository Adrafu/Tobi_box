"""Ein echter, lokaler Mosquitto für die MQTT-Tests (Vorbild: die MPD-Fixtures in ``integration/conftest.py``).

Der Broker hört nur auf ``127.0.0.1`` an einem freien Port, verlangt ein Konto und wendet die Rechte aus
``mqtt-v1.md`` Abschnitt 7 an (Konten ``box1`` und ``box2``, ``ha`` darf alles). So prüft jeder Test, dass die Box mit
genau diesen Rechten auskommt. Ohne das Programm ``mosquitto`` werden die Tests übersprungen (in der CI wird es installiert).
Die Zugangsdaten hier sind erfundene Testwerte.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

MOSQUITTO = shutil.which("mosquitto") or (p if os.access(p := "/usr/sbin/mosquitto", os.X_OK) else None)
MOSQUITTO_PASSWD = shutil.which("mosquitto_passwd") or (p if os.access(p := "/usr/bin/mosquitto_passwd", os.X_OK) else None)

PASSWOERTER = {"ha": "ha-testwert", "box1": "box1-testwert", "box2": "box2-testwert"}

# ``mqtt-v1.md``, Abschnitt 7, Hauptform (ein Block je Konto), dazu das Konto von HA mit allen Rechten.
# Die „gleichwertige“ Form mit ``pattern`` im Vertrag lässt ``topic read tobibox/config`` und
# ``topic read homeassistant/status`` ohne ``user`` stehen: Mosquitto rechnet sie dann dem letzten ``user`` zu
# (hier wäre das ``ha``) und die Boxen bekämen die Konfiguration nie. Dort müsste ``pattern read …`` stehen.
ACL_BOX = """\
user {box}
topic read tobibox/config
topic read tobibox/{box}/cmd
topic read tobibox/{box}/unknown/+/ack
topic read homeassistant/status
topic write tobibox/{box}/online
topic write tobibox/{box}/status
topic write tobibox/{box}/event
topic write tobibox/{box}/unknown/+
topic write homeassistant/+/tobibox_{box}/+/config
"""
ACL = "user ha\ntopic readwrite #\n\n" + "\n".join(ACL_BOX.format(box=b) for b in ("box1", "box2"))


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestBroker:
    __test__ = False

    def __init__(self, verzeichnis: Path) -> None:
        assert MOSQUITTO is not None and MOSQUITTO_PASSWD is not None
        self.verz = verzeichnis
        verzeichnis.mkdir(parents=True, exist_ok=True)
        self.port = freier_port()
        self.proc: subprocess.Popen | None = None
        passwd = verzeichnis / "passwd"
        for i, (konto, pw) in enumerate(PASSWOERTER.items()):
            subprocess.run([MOSQUITTO_PASSWD, "-b"] + (["-c"] if i == 0 else []) + [str(passwd), konto, pw],
                           check=True, capture_output=True)
        (verzeichnis / "acl").write_text(ACL, encoding="utf-8")
        zeilen = [
            f"listener {self.port} 127.0.0.1",
            "allow_anonymous false",
            f"password_file {passwd}",
            f"acl_file {verzeichnis / 'acl'}",
            f"log_dest file {verzeichnis / 'mosquitto.log'}",
        ]
        if os.geteuid() == 0:
            zeilen.append("user root")  # sonst gibt Mosquitto die Rechte ab und liest die Dateien nicht
        (verzeichnis / "mosquitto.conf").write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    def start(self) -> None:
        assert MOSQUITTO is not None
        self.proc = subprocess.Popen([MOSQUITTO, "-c", str(self.verz / "mosquitto.conf")],
                                     stdout=subprocess.DEVNULL, stderr=open(self.verz / "mosquitto.stderr", "ab"))
        ende = time.monotonic() + 10
        while time.monotonic() < ende:
            if self.proc.poll() is not None:
                raise RuntimeError(f"mosquitto beendet sich: {(self.verz / 'mosquitto.stderr').read_text()}")
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.5).close()
                return
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("mosquitto startet nicht")

    def stop(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc = None


class GegenstelleHa:
    """Spielt Home Assistant: abonniert alles und sendet Konfiguration, Befehle und Bestätigungen.

    Sammelt jede empfangene Nachricht mit ihrem „retained“-Kennzeichen (Reihenfolge wie empfangen)."""

    def __init__(self, port: int, konto: str = "ha", filter_: tuple[str, ...] = ("tobibox/#", "homeassistant/#")) -> None:
        import paho.mqtt.client as mqtt

        self.nachrichten: list[tuple[str, bytes, bool]] = []
        self._sperre = threading.Lock()
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"test-{konto}-{id(self)}", protocol=mqtt.MQTTv311)
        c.username_pw_set(konto, PASSWOERTER[konto])
        self._abonniert = threading.Event()
        c.on_connect = lambda cl, ud, fl, rc, pr=None: cl.subscribe([(f, 1) for f in filter_])
        c.on_subscribe = lambda *a, **k: self._abonniert.set()
        c.on_message = self._on_message
        c.connect("127.0.0.1", port)
        c.loop_start()
        self.c = c
        assert self._abonniert.wait(5), "Gegenstelle konnte nicht abonnieren"

    def _on_message(self, c, ud, msg) -> None:
        with self._sperre:
            self.nachrichten.append((msg.topic, bytes(msg.payload), bool(msg.retain)))

    def auf(self, thema: str) -> list[tuple[bytes, bool]]:
        with self._sperre:
            return [(n, r) for t, n, r in self.nachrichten if t == thema]

    def json_auf(self, thema: str) -> list[dict]:
        return [json.loads(n) for n, _ in self.auf(thema) if n]

    def themen(self) -> set[str]:
        with self._sperre:
            return {t for t, _, _ in self.nachrichten}

    def veroeffentliche(self, thema: str, nutzlast: bytes | dict, retain: bool = False) -> None:
        if not isinstance(nutzlast, bytes):
            nutzlast = json.dumps(nutzlast).encode()
        info = self.c.publish(thema, nutzlast, qos=1, retain=retain)
        info.wait_for_publish(5)

    def stop(self) -> None:
        self.c.disconnect()
        self.c.loop_stop()


async def warte_bis(bedingung: Callable[[], bool], frist_s: float = 8.0, text: str = "") -> None:
    """Prüft ``bedingung`` alle 20 ms (die Ereignisschleife läuft weiter); bricht nach ``frist_s`` mit Text ab."""
    import asyncio

    ende = time.monotonic() + frist_s
    while time.monotonic() < ende:
        if bedingung():
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"Frist von {frist_s} s abgelaufen: {text}")


@pytest.fixture
def broker(tmp_path: Path) -> Iterator[TestBroker]:
    if MOSQUITTO is None or MOSQUITTO_PASSWD is None:
        pytest.skip("mosquitto ist nicht installiert (apt install mosquitto / brew install mosquitto)")
    b = TestBroker(tmp_path / "broker")
    b.start()
    yield b
    b.stop()


@pytest.fixture
def gegenstelle(broker: TestBroker) -> Iterator[GegenstelleHa]:
    g = GegenstelleHa(broker.port)
    yield g
    g.stop()
