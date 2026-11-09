"""Die Vorlage ``mosquitto/accesscontrollist.example`` gegen einen echten Mosquitto (2.0.x) prüfen.

Das Add-on 7.1.3 verbindet die Rechte über ``/share/mosquitto/acl.conf`` (``acl_file``) mit der Datei
``/share/mosquitto/accesscontrollist``; die Anmeldung übernimmt dort das Add-on. Hier genügt eine Passwortdatei: Es geht um
die Themenrechte (``mqtt-v1.md``, Abschnitt 7, korrigierte Fassung)."""

from __future__ import annotations

import os
import queue
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

paho = pytest.importorskip("paho.mqtt.client")

MOSQUITTO = shutil.which("mosquitto")
PASSWD = shutil.which("mosquitto_passwd")
VORLAGEN = Path(__file__).resolve().parents[1] / "mosquitto"

pytestmark = pytest.mark.skipif(MOSQUITTO is None or PASSWD is None, reason="mosquitto fehlt")


def pattern_form(text: str) -> str:
    """Die gleichwertige Form mit ``pattern``: Blöcke der Boxen weg, auskommentierte ``pattern``-Zeilen an."""
    zeilen = text.splitlines()
    aus: list[str] = []
    in_box = False
    for z in zeilen:
        if z.startswith("user "):
            in_box = z.split()[1] in ("box1", "box2")
        if in_box and not z.startswith("#"):
            continue
        aus.append(z[2:] if z.startswith("# pattern ") else z)
    return "\n".join(aus)


@pytest.fixture(params=["user", "pattern"])
def broker(request, tmp_path, socket_enabled):
    regeln = (VORLAGEN / "accesscontrollist.example").read_text(encoding="utf-8")
    if request.param == "pattern":
        regeln = pattern_form(regeln)
        regeln += "\nuser box1\n\nuser box2\n"  # die Konten existieren weiterhin (nur mit %u-Regeln)
    # Bei der Pattern-Form gelten die %u-Regeln für jedes Konto; die Konten selbst legt die Passwortdatei an.
    (tmp_path / "acl").write_text(regeln, encoding="utf-8")
    passwd = tmp_path / "passwd"
    for i, user in enumerate(("homeassistant", "addons", "box1", "box2")):
        subprocess.run([PASSWD, "-b"] + (["-c"] if i == 0 else []) + [str(passwd), user, f"pw-{user}"], check=True, capture_output=True)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    als_root = "user root\n" if os.geteuid() == 0 else ""  # sonst gibt Mosquitto die Rechte ab und liest die Dateien nicht
    (tmp_path / "mosquitto.conf").write_text(
        f"{als_root}listener {port} 127.0.0.1\nallow_anonymous false\npassword_file {passwd}\nacl_file {tmp_path / 'acl'}\npersistence false\n"
    )
    prozess = subprocess.Popen([MOSQUITTO, "-c", str(tmp_path / "mosquitto.conf")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
            break
        except OSError:
            time.sleep(0.05)
    else:
        prozess.kill()
        raise AssertionError("Mosquitto startet nicht: " + (prozess.stdout.read().decode() if prozess.stdout else ""))
    yield port
    prozess.terminate()
    prozess.wait(timeout=5)
    if prozess.stdout:
        prozess.stdout.close()


class Teilnehmer:
    def __init__(self, port: int, user: str) -> None:
        self.eingang: queue.Queue[tuple[str, bytes]] = queue.Queue()
        self.client = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=f"test-{user}", protocol=paho.MQTTv311)
        self.client.username_pw_set(user, f"pw-{user}")
        self.client.on_message = lambda _c, _u, m: self.eingang.put((m.topic, m.payload))
        self.client.connect("127.0.0.1", port)
        self.client.loop_start()
        self.user = user

    def abonniere(self, *themen: str) -> None:
        for t in themen:
            self.client.subscribe(t, qos=1)
        time.sleep(0.3)

    def sende(self, thema: str, nutzlast: str | bytes = "x", retain: bool = False) -> None:
        self.client.publish(thema, nutzlast, qos=1, retain=retain).wait_for_publish(timeout=3)

    def empfangen(self, wartezeit: float = 0.4) -> list[tuple[str, bytes]]:
        time.sleep(wartezeit)
        aus = []
        while not self.eingang.empty():
            aus.append(self.eingang.get())
        return aus

    def ende(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()


@pytest.fixture
def netz(broker):
    teilnehmer: list[Teilnehmer] = []

    def neu(user: str) -> Teilnehmer:
        t = Teilnehmer(broker, user)
        teilnehmer.append(t)
        return t

    yield neu
    for t in teilnehmer:
        t.ende()


def test_box_bekommt_konfiguration_cmd_ack_und_ha_status(netz):
    ha, box = netz("homeassistant"), netz("box1")
    ha.sende("tobibox/config", '{"revision": 1}', retain=True)
    ha.sende("homeassistant/status", "online", retain=True)
    box.abonniere("tobibox/config", "homeassistant/status", "tobibox/box1/cmd", "tobibox/box1/unknown/+/ack")
    erster = dict(box.empfangen())
    assert erster == {"tobibox/config": b'{"revision": 1}', "homeassistant/status": b"online"}  # beide Leserechte wirken
    ha.sende("tobibox/box1/cmd", "lernen")
    ha.sende("tobibox/box1/unknown/04a1b2c3/ack", "ack")
    assert sorted(box.empfangen()) == [("tobibox/box1/cmd", b"lernen"), ("tobibox/box1/unknown/04a1b2c3/ack", b"ack")]


def test_box_liest_keine_themen_anderer_boxen(netz):
    ha, box = netz("homeassistant"), netz("box1")
    box.abonniere("tobibox/box2/cmd", "tobibox/box2/status", "tobibox/box2/unknown/+/ack", "tobibox/box1/status")
    ha.sende("tobibox/box2/cmd", "lernen")
    ha.sende("tobibox/box2/status", "{}")
    ha.sende("tobibox/box2/unknown/04a1b2c3/ack", "ack")
    assert box.empfangen() == []  # Rechte zum Lesen: nur tobibox/config, eigenes cmd und eigene ack
    ha.sende("tobibox/box1/status", "{}")
    assert box.empfangen() == []  # auch das eigene status liest die Box nicht (sie schreibt es nur)


ERLAUBT = [
    ("tobibox/box1/online", b"online"),
    ("tobibox/box1/status", b"{}"),
    ("tobibox/box1/event", b"{}"),
    ("tobibox/box1/unknown/04a1b2c3", b"{}"),
    ("homeassistant/sensor/tobibox_box1/akku/config", b"{}"),
    ("homeassistant/button/tobibox_box1/sync_jetzt/config", b"{}"),
]
VERBOTEN = [
    ("tobibox/config", b"boese"),
    ("tobibox/box1/cmd", b"boese"),
    ("tobibox/box1/unknown/04a1b2c3/ack", b"boese"),
    ("tobibox/box1/ui/sync", b"PRESS"),
    ("tobibox/box2/online", b"boese"),
    ("tobibox/box2/status", b"boese"),
    ("tobibox/box2/unknown/04a1b2c3", b"boese"),
    ("homeassistant/sensor/tobibox_box2/akku/config", b"boese"),
    ("homeassistant/switch/fremd/schalter/config", b"boese"),
    ("homeassistant/status", b"offline"),
]


def test_box_schreibt_nur_ihre_eigenen_themen(netz):
    ha, box = netz("homeassistant"), netz("box1")
    ha.abonniere("#")
    for thema, nutzlast in ERLAUBT + VERBOTEN:
        box.sende(thema, nutzlast)
    angekommen = dict(ha.empfangen(0.6))
    assert angekommen == dict(ERLAUBT)
    for thema, _n in VERBOTEN:
        assert thema not in angekommen


def test_box_loescht_die_dauerhafte_nachricht_einer_kennung(netz):
    ha, box = netz("homeassistant"), netz("box1")
    ha.abonniere("tobibox/box1/unknown/+")
    box.sende("tobibox/box1/unknown/04a1b2c3", b"{}", retain=True)
    box.sende("tobibox/box1/unknown/04a1b2c3", b"", retain=True)  # leere Nutzlast, retained
    assert ha.empfangen() == [("tobibox/box1/unknown/04a1b2c3", b"{}"), ("tobibox/box1/unknown/04a1b2c3", b"")]


def test_homeassistant_und_addons_sind_unbeschraenkt(netz):
    ha, addons, box = netz("homeassistant"), netz("addons"), netz("box1")
    box.abonniere("tobibox/config")
    ha.sende("tobibox/box2/irgendwas", "x")
    addons.sende("tobibox/config", "von addons")
    assert box.empfangen() == [("tobibox/config", b"von addons")]


def test_zweite_box_hat_ihre_eigenen_rechte(netz):
    ha, box2 = netz("homeassistant"), netz("box2")
    ha.abonniere("#")
    box2.abonniere("tobibox/box2/cmd", "tobibox/box1/cmd")
    ha.sende("tobibox/box1/cmd", "fuer box1")
    ha.sende("tobibox/box2/cmd", "fuer box2")
    assert [t for t, _n in box2.empfangen() if t.endswith("/cmd")] == ["tobibox/box2/cmd"]
    box2.sende("tobibox/box2/status", b"{}")
    box2.sende("tobibox/box1/status", b"boese")
    assert [t for t, _n in ha.empfangen() if "status" in t] == ["tobibox/box2/status"]


def test_vorlagen_sind_vollstaendig():
    regeln = (VORLAGEN / "accesscontrollist.example").read_text(encoding="utf-8")
    assert re.search(r"^user homeassistant\ntopic readwrite #$", regeln, re.MULTILINE)
    assert re.search(r"^user addons\ntopic readwrite #$", regeln, re.MULTILINE)
    conf = (VORLAGEN / "acl.conf.example").read_text(encoding="utf-8")
    assert "acl_file /share/mosquitto/accesscontrollist" in conf
    assert not re.search(r"^(user|topic|pattern) ", conf, re.MULTILINE)  # in der *.conf stehen keine Regeln
    yaml_text = (VORLAGEN / "mosquitto-addon.example.yaml").read_text(encoding="utf-8")
    assert "customize:\n  active: true\n  folder: mosquitto" in yaml_text
    assert "username: box1" in yaml_text and "username: box2" in yaml_text
    assert "homeassistant" not in re.findall(r"username: (\S+)", yaml_text)
