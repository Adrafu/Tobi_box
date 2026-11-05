"""Startet und beendet ein echtes ``mpd`` mit ``fixtures/mpd.test.conf``.

Ohne ``mpd`` im Pfad werden die MPD-Tests übersprungen (Grund steht in der Meldung).
In der CI wird ``mpd`` installiert (``apt install mpd``, Systemdienst aus).
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fixtures import audio

VORLAGE = Path(__file__).resolve().parents[1] / "fixtures" / "mpd.test.conf"
MPD = shutil.which("mpd")


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _kommando(*teile: str) -> bytes:
    return ("\n".join(teile) + "\n").encode()


class TestMpd:
    """Ein MPD-Prozess in einem eigenen Verzeichnis."""

    __test__ = False

    def __init__(self, verzeichnis: Path) -> None:
        self.verz = verzeichnis
        self.medien = verzeichnis / "medien"
        self.port = freier_port()
        self.proc: subprocess.Popen | None = None
        self.medien.mkdir(parents=True, exist_ok=True)
        (verzeichnis / "playlists").mkdir(exist_ok=True)
        self.konf = verzeichnis / "mpd.conf"
        self.konf.write_text(
            VORLAGE.read_text(encoding="utf-8").replace("@VERZ@", str(verzeichnis)).replace("@PORT@", str(self.port)),
            encoding="utf-8",
        )

    def _frage(self, *zeilen: str, timeout: float = 2.0) -> str:
        with socket.create_connection(("127.0.0.1", self.port), timeout=timeout) as s:
            s.settimeout(timeout)
            s.recv(256)  # OK MPD x.y.z
            s.sendall(_kommando(*zeilen))
            antwort = b""
            while not antwort.rstrip().endswith((b"OK", b"ACK")) and b"\nACK" not in antwort:
                teil = s.recv(4096)
                if not teil:
                    break
                antwort += teil
        return antwort.decode("utf-8", "replace")

    def start(self) -> None:
        assert MPD is not None
        self.proc = subprocess.Popen(
            [MPD, "--no-daemon", "--stderr", str(self.konf)],
            stdout=subprocess.DEVNULL,
            stderr=open(self.verz / "mpd.stderr", "ab"),
        )
        ende = time.monotonic() + 10
        while time.monotonic() < ende:
            if self.proc.poll() is not None:
                raise RuntimeError(f"mpd beendet sich: {(self.verz / 'mpd.stderr').read_text()}")
            try:
                self._frage("ping")
                return
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("mpd startet nicht")

    def aktualisiere(self) -> None:
        """Medienordner einlesen und warten, bis MPD fertig ist."""
        self._frage("update")
        ende = time.monotonic() + 10
        while time.monotonic() < ende:
            if "updating_db" not in self._frage("status"):
                return
            time.sleep(0.05)
        raise RuntimeError("mpd-Update dauert zu lange")

    def stop(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc = None


@pytest.fixture
def mpd(tmp_path: Path) -> Iterator[TestMpd]:
    if MPD is None:
        pytest.skip("mpd ist nicht installiert (apt install mpd / brew install mpd)")
    m = TestMpd(tmp_path / "mpd")
    # Medien: lange Folgen für Positionstests, kurze für das Folgenende
    audio.erzeuge_serie(m.medien, "lang", ["a.wav", "b.wav"], serie_id="lang", dauer_s=30.0)
    audio.erzeuge_serie(m.medien, "kurz", ["a.wav", "b.wav"], serie_id="kurz", dauer_s=1.0)
    m.start()
    m.aktualisiere()
    yield m
    m.stop()
