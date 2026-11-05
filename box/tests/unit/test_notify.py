"""``READY=1`` über ``NOTIFY_SOCKET``."""

from __future__ import annotations

import socket

from tobibox import notify


def test_ohne_socket_ohne_wirkung(monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    assert notify.bereit() is False


def test_sendet_ready(tmp_path, monkeypatch):
    pfad = str(tmp_path / "notify.sock")
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as srv:
        srv.bind(pfad)
        monkeypatch.setenv("NOTIFY_SOCKET", pfad)
        assert notify.bereit() is True
        assert srv.recv(64) == b"READY=1"


def test_toter_socket_gibt_false(tmp_path):
    assert notify.sd_notify("READY=1", socket_pfad=str(tmp_path / "weg.sock")) is False
