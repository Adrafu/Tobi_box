"""Kennung des aktuellen Starts des Geräts (nicht des Dienstes).

Sie ändert sich nur bei einem echten Einschalten (auch nach leerem Akku oder Stromausfall),
nicht bei ``systemctl restart``, Update oder Absturz des Dienstes (Entscheidung G, 06.11.).
Linux: ``/proc/sys/kernel/random/boot_id``. Mac: Startzeit des Systems (``sysctl -n kern.boottime``).
Nicht lesbar: ``None`` (dann gilt Einschalten). Tests setzen die Quelle über ``App(boot_id=...)``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

BOOT_ID_DATEI = Path("/proc/sys/kernel/random/boot_id")

BootId = Callable[[], "str | None"]


def parse_kern_boottime(text: str) -> str | None:
    """``{ sec = 1730000000, usec = 123456 } Wed Nov  6 ...`` -> ``"mac-1730000000-123456"``."""
    m = re.search(r"sec\s*=\s*(\d+)\s*,\s*usec\s*=\s*(\d+)", text)
    return f"mac-{m.group(1)}-{m.group(2)}" if m else None


def lese(datei: Path = BOOT_ID_DATEI) -> str | None:
    """Die Kennung dieses Starts, oder ``None``."""
    try:
        if sys.platform == "darwin":
            aus = subprocess.run(
                ["sysctl", "-n", "kern.boottime"], capture_output=True, text=True, timeout=2.0, check=True
            ).stdout
            return parse_kern_boottime(aus)
        kennung = datei.read_text(encoding="ascii").strip()
        return kennung or None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
