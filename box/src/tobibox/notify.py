"""``READY=1`` an systemd melden (``NOTIFY_SOCKET``), reines Python ohne ``python-systemd``.

Am Mac ist ``NOTIFY_SOCKET`` nicht gesetzt: ohne Wirkung.
"""

from __future__ import annotations

import os
import socket

ENV_SOCKET = "NOTIFY_SOCKET"


def sd_notify(nachricht: str, *, socket_pfad: str | None = None) -> bool:
    """Eine Nachricht an systemd senden. ``True``, wenn sie abgeschickt wurde."""
    pfad = socket_pfad if socket_pfad is not None else os.environ.get(ENV_SOCKET)
    if not pfad:
        return False
    if pfad.startswith("@"):  # abstrakter Socket
        pfad = "\0" + pfad[1:]
    elif not pfad.startswith("/"):
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM | getattr(socket, "SOCK_CLOEXEC", 0)) as s:
            s.connect(pfad)
            s.sendall(nachricht.encode("utf-8"))
    except OSError:
        return False
    return True


def bereit(*, socket_pfad: str | None = None) -> bool:
    return sd_notify("READY=1", socket_pfad=socket_pfad)


def stoppt(*, socket_pfad: str | None = None) -> bool:
    return sd_notify("STOPPING=1", socket_pfad=socket_pfad)
