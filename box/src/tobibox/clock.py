"""Uhr als Eingang des Kerns: Wanduhr, monotone Uhr, Zeitquelle.

``Jetzt`` wird in ``events`` definiert (der Kern darf keine Uhr-Module
importieren) und hier wieder angeboten. Im Betrieb liefert ``SystemUhr`` die
Werte, in Tests ``SimUhr``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from .events import Jetzt, ZeitQuelle

__all__ = ["Jetzt", "Uhr", "SystemUhr", "SimUhr"]


class Uhr(Protocol):
    def jetzt(self) -> Jetzt: ...


class SystemUhr:
    """Echte Uhr. Am Mac ist die Systemuhr vertrauenswürdig (Vorgabe)."""

    def __init__(
        self,
        zeit_quelle: ZeitQuelle = "system",
        zeit_ok: bool = True,
        *,
        mono: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ) -> None:
        self._quelle: ZeitQuelle = zeit_quelle
        self._ok = zeit_ok
        self._mono = mono
        self._wall = wall
        self._versatz = 0.0  # Sekunden; ``stelle_wall`` verschiebt die Wanduhr (Simulation der Uhrzeit am Mac)

    def stelle_wall(self, wall: float | None) -> None:
        """Wanduhr auf ``wall`` stellen (Unix-Sekunden); sie läuft von dort weiter. ``None``: wieder die echte Uhr.

        Nur für die Simulation (``tobibox sim time``): Leise-Zeiten lassen sich so ohne Warten prüfen. Die monotone Uhr
        bleibt, Fristen und Timer sind nicht betroffen."""
        self._versatz = 0.0 if wall is None else wall - self._wall()

    def setze_quelle(self, quelle: ZeitQuelle, zeit_ok: bool) -> None:
        self._quelle = quelle
        self._ok = zeit_ok

    def jetzt(self) -> Jetzt:
        return Jetzt(self._mono(), self._wall() + self._versatz, self._quelle, self._ok)


class SimUhr:
    """Simulierte Uhr für Tests: läuft nur, wenn man sie vorstellt."""

    def __init__(
        self,
        mono: float = 1000.0,
        wall: float = 1_700_000_000.0,
        zeit_quelle: ZeitQuelle = "system",
        zeit_ok: bool = True,
    ) -> None:
        self.mono = mono
        self.wall = wall
        self.zeit_quelle: ZeitQuelle = zeit_quelle
        self.zeit_ok = zeit_ok

    def vor(self, sekunden: float) -> Jetzt:
        """Beide Uhren um ``sekunden`` weiter; die monotone läuft nie zurück."""
        if sekunden < 0:
            raise ValueError("die monotone Uhr läuft nicht rückwärts")
        self.mono += sekunden
        self.wall += sekunden
        return self.jetzt()

    def setze_wall(self, wall: float) -> None:
        """Wanduhr springen lassen (z. B. NTP-Korrektur); ``mono`` bleibt."""
        self.wall = wall

    def setze_zeit(self, zeit_quelle: ZeitQuelle, zeit_ok: bool) -> None:
        self.zeit_quelle = zeit_quelle
        self.zeit_ok = zeit_ok

    def jetzt(self) -> Jetzt:
        return Jetzt(self.mono, self.wall, self.zeit_quelle, self.zeit_ok)
