"""Hilfen für die Sync-Tests: ein echter rsync-Daemon auf einem freien Port (``rsync --daemon --no-detach``)."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from tobibox import events as ev
from tobibox.config import SyncKonfig

BENUTZER = "tester"
PASSWORT = "geheim-nur-im-test"


@dataclass
class Daemon:
    port: int
    quelle: Path
    box: Path  # Medienordner der Box
    partial: Path  # neben dem Medienordner, nicht darin
    passwort_datei: Path

    def konfig(self, modul: str = "medien", **kw) -> SyncKonfig:
        werte = dict(host="127.0.0.1", port=self.port, modul=modul, reserve_mb=0)
        if modul == "gesichert":
            werte.update(benutzer=BENUTZER, passwort_datei=self.passwort_datei)
        werte.update(kw)
        return SyncKonfig(**werte)


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def schreibe(pfad: Path, inhalt: bytes | str = b"x") -> Path:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_bytes(inhalt if isinstance(inhalt, bytes) else inhalt.encode())
    return pfad


def dateien(ordner: Path) -> set[str]:
    return {str(p.relative_to(ordner)) for p in ordner.rglob("*") if p.is_file()}


@pytest.fixture
def rsync_daemon(tmp_path):
    """Startet einen lokalen rsync-Daemon. Module: ``medien`` (offen), ``gesichert`` (mit Anmeldung),
    ``fehlt`` (Pfad existiert nicht), ``leer`` (leerer Ordner). Alle nur lesend."""
    if shutil.which("rsync") is None:
        pytest.skip("rsync nicht installiert")
    quelle = tmp_path / "nas" / "medien"
    quelle.mkdir(parents=True)
    leer = tmp_path / "nas" / "leer"
    leer.mkdir()
    box = tmp_path / "box" / "medien"
    box.mkdir(parents=True)
    partial = tmp_path / "box" / ".rsync-partial"
    secrets = tmp_path / "secrets"
    secrets.write_text(f"{BENUTZER}:{PASSWORT}\n")
    secrets.chmod(0o600)
    pw = tmp_path / "passwort"
    pw.write_text(PASSWORT + "\n")
    pw.chmod(0o600)
    port = freier_port()
    ids = "uid = 0\ngid = 0\n" if os.geteuid() == 0 else ""
    conf = tmp_path / "rsyncd.conf"
    conf.write_text(
        f"""pid file = {tmp_path}/rsyncd.pid
log file = {tmp_path}/rsyncd.log
use chroot = no
address = 127.0.0.1
{ids}read only = yes
[medien]
    path = {quelle}
[gesichert]
    path = {quelle}
    auth users = {BENUTZER}
    secrets file = {secrets}
[fehlt]
    path = {tmp_path}/gibt-es-nicht
[leer]
    path = {leer}
"""
    )
    proc = subprocess.Popen(
        ["rsync", "--daemon", "--no-detach", f"--config={conf}", f"--port={port}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ende = time.monotonic() + 10
        while True:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                break
            except OSError:
                if proc.poll() is not None or time.monotonic() > ende:
                    raise RuntimeError("rsync-Daemon startet nicht")
                time.sleep(0.05)
        yield Daemon(port, quelle, box, partial, pw)
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()


class Ereignisse:
    """Sammelt die Ereignisse eines Syncs (der Haken ``ausgabe``)."""

    def __init__(self) -> None:
        self.liste: list[ev.Ereignis] = []

    def __call__(self, e: ev.Ereignis) -> None:
        self.liste.append(e)

    @property
    def typen(self) -> list[type]:
        return [type(e) for e in self.liste]

    def abbruch(self) -> str | None:
        for e in self.liste:
            if isinstance(e, ev.SyncAbgebrochen):
                return e.grund
        return None

    def fertig(self) -> ev.SyncFertig | None:
        for e in self.liste:
            if isinstance(e, ev.SyncFertig):
                return e
        return None
