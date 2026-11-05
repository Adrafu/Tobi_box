"""Kurze Töne über ein konfigurierbares Kommando (``core-interface.md``, 8.1).

Mac: ``afplay -v <0..1> <datei>``; Pi: ``aplay`` (über das ALSA-Gerät, das auch MPD
nutzt). Das Kommando ist eine Liste mit den Platzhaltern ``{datei}``,
``{pegel}`` (0 bis 100) und ``{lautstaerke}`` (0.0 bis 1.0).

Pegel: alle Töne außer ``hinweis``: ``min(ton_pegel, grenze)``; ``hinweis``:
``max(5, min(hinweis_pegel, grenze))``. Vorgaben 40 und 15. Ohne Tondatei wird
nichts gestartet.

TODO (Pi-Probelauf): ``aplay`` kann keinen Pegel setzen – Lösung im Pi-Probelauf.
Bis dahin ignoriert das Pi-Kommando ``{pegel}`` und ``{lautstaerke}``.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from .eventlog import logge

TON_PEGEL_VORGABE = 40
HINWEIS_PEGEL_VORGABE = 15
HINWEIS_MINDEST = 5
TON_MAX_S = 10.0  # ein hängendes Abspielprogramm wird danach beendet

#: Töne, für die es bewusst (noch) keine Datei gibt.
_OHNE_DATEI = frozenset({"pruef_ok", "pruef_fehler"})


def pegel(ton: str, grenze: int, ton_pegel: int | None = None, hinweis_pegel: int | None = None) -> int:
    """Pegel in Prozent (0 bis 100)."""
    grenze = max(0, min(100, int(grenze)))
    if ton == "hinweis":
        h = HINWEIS_PEGEL_VORGABE if hinweis_pegel is None else hinweis_pegel
        return max(HINWEIS_MINDEST, min(h, grenze))
    t = TON_PEGEL_VORGABE if ton_pegel is None else ton_pegel
    return min(t, grenze)


def baue_kommando(vorlage: Sequence[str], datei: Path, pegel_prozent: int) -> list[str]:
    ersetze = {
        "{datei}": str(datei),
        "{pegel}": str(pegel_prozent),
        "{lautstaerke}": f"{pegel_prozent / 100:.2f}",
    }
    ergebnis = []
    for teil in vorlage:
        for k, v in ersetze.items():
            teil = teil.replace(k, v)
        ergebnis.append(teil)
    return ergebnis


Starter = Callable[[Sequence[str]], Awaitable[None]]


async def _starte_prozess(kommando: Sequence[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *kommando, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        rc = await asyncio.wait_for(proc.wait(), TON_MAX_S)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        await proc.wait()
        logge("sounds", "WARNING", "ton", "zeitueberschreitung", daten={"kommando": kommando[0]})
        return
    if rc != 0:
        logge("sounds", "WARNING", "ton", "kommando_fehler", daten={"kommando": kommando[0], "rc": rc})


class Toene:
    """Führt ``TonSpielen`` aus. Spielt im Hintergrund; blockiert nie."""

    def __init__(self, ordner: str | Path, kommando: Sequence[str], *, starter: Starter | None = None) -> None:
        self.ordner = Path(ordner)
        self.kommando = tuple(kommando)
        self._starter = starter or _starte_prozess
        self._aufgaben: set[asyncio.Task] = set()

    def datei(self, ton: str) -> Path:
        return self.ordner / f"{ton}.wav"

    def kommando_fuer(
        self, ton: str, grenze: int, ton_pegel: int | None = None, hinweis_pegel: int | None = None
    ) -> list[str] | None:
        """Das fertige Kommando, oder ``None`` ohne Datei."""
        d = self.datei(ton)
        if not d.is_file():
            logge("sounds", "DEBUG" if ton in _OHNE_DATEI else "WARNING", "ton", "datei_fehlt", daten={"ton": ton, "datei": str(d)})
            return None
        return baue_kommando(self.kommando, d, pegel(ton, grenze, ton_pegel, hinweis_pegel))

    def spiele(self, ton: str, grenze: int, ton_pegel: int | None = None, hinweis_pegel: int | None = None) -> bool:
        """Ton starten (Hintergrundaufgabe). ``False``, wenn nichts gestartet wurde."""
        k = self.kommando_fuer(ton, grenze, ton_pegel, hinweis_pegel)
        if k is None:
            return False
        t = asyncio.get_running_loop().create_task(self._lauf(ton, k), name=f"tobibox-ton-{ton}")
        self._aufgaben.add(t)
        t.add_done_callback(self._aufgaben.discard)
        return True

    async def _lauf(self, ton: str, kommando: list[str]) -> None:
        try:
            await self._starter(kommando)
            logge("sounds", "DEBUG", "ton", "gespielt", daten={"ton": ton, "kommando": kommando[0]})
        except FileNotFoundError:
            logge("sounds", "WARNING", "ton", "programm_fehlt", daten={"ton": ton, "kommando": kommando[0]})
        except OSError as e:
            logge("sounds", "WARNING", "ton", "start_fehler", daten={"ton": ton, "detail": str(e)})

    async def warte(self) -> None:
        """Auf laufende Töne warten (Tests, sauberes Beenden)."""
        if self._aufgaben:
            await asyncio.gather(*list(self._aufgaben), return_exceptions=True)

    async def stop(self) -> None:
        for t in list(self._aufgaben):
            t.cancel()
        await self.warte()
