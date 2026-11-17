"""Hilfen für die Tests von „Gehört“ (Stufe B, B1): eine Box, die Wiedergabe simuliert, mit echtem Puffer ``gehoert.json``."""

from __future__ import annotations

import json
from pathlib import Path

from tobibox import events as ev
from tobibox.clock import SimUhr
from tobibox.gehoert_puffer import GehoertPuffer

SERIE = "3f9a1c07b2d4"
FOLGE = "folge-02.mp3"
ANDERE = "folge-03.mp3"
ANFANG_WALL = 1_790_000_000.0  # 2026-09-21, eine plausible Wanduhr


def uuid_nr(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


class Box:
    """Beobachter „Gehört“ mit simulierter Uhr. ``spiele`` läuft jede Sekunde mit einer ``PlayerPosition`` und einem ``Takt``."""

    def __init__(self, verz: Path, *, boot: str | None = "boot-1", uhr: SimUhr | None = None, nummer: int = 0, asynchron: bool = False) -> None:
        self.verz = verz
        self.uhr = uhr or SimUhr(mono=5000.0, wall=ANFANG_WALL)
        self.nummer = nummer
        self.boot = boot
        self.asynchron = asynchron
        self.p = GehoertPuffer(
            verz, boot_id=lambda: self.boot, neue_id=self._id, asynchron=asynchron,
            dauer=lambda serie, folge: 1520 if folge == FOLGE else None,
        )
        self.p.laden(self.uhr.jetzt())
        self.gen = 0
        self.serie, self.folge, self.track, self.pos = SERIE, FOLGE, 0, 0.0

    def _id(self) -> str:
        self.nummer += 1
        return uuid_nr(self.nummer)

    @property
    def datei(self) -> Path:
        return self.verz / "gehoert.json"

    def inhalt(self) -> dict:
        return json.loads(self.datei.read_text(encoding="utf-8"))

    def ein(self, e: ev.Ereignis, *befehle: ev.Befehl) -> None:
        self.p.beobachte(e, befehle, self.uhr.jetzt())

    def abspielen(self, folge: str = FOLGE, position_s: float = 0.0, serie: str = SERIE, track: int = 0) -> None:
        """Wie ``session``: ein neues ``Abspielen`` mit neuer Generation (Start, Fortsetzen, Springen)."""
        self.gen += 1
        self.serie, self.folge, self.track, self.pos = serie, folge, track, position_s
        self.ein(ev.Takt(), ev.Abspielen(serie, "ordner", folge, (folge,), track, position_s, None, self.gen))

    def position(self, *, spielt: bool = True, gen: int | None = None) -> None:
        self.ein(ev.PlayerPosition(self.serie, self.folge, self.track, round(self.pos, 3), spielt, self.gen if gen is None else gen))

    def spiele(self, sekunden: int, *, tempo: float = 1.0) -> None:
        """So viele Sekunden Wiedergabe: Uhr, Position und eine Meldung je Sekunde."""
        for _ in range(sekunden):
            self.uhr.vor(1.0)
            self.pos += tempo
            self.position()
            self.ein(ev.Takt())

    def pause(self, grund: str = "knopf") -> None:
        self.position(spielt=False)
        self.ein(ev.Takt(), ev.Pausieren(grund))  # type: ignore[arg-type]

    def vergehen(self, sekunden: float) -> None:
        self.uhr.vor(sekunden)
        self.ein(ev.Takt())

    def folge_zu_ende(self) -> None:
        self.ein(ev.FolgeZuEnde(self.serie, self.folge, self.gen), ev.Pausieren("folgenende"))

    def zeilen(self) -> list[dict]:
        return [dict(r) for r in self.p.zeilen]

    def neu_starten(self, *, boot: str | None = ..., nummer: int | None = None) -> Box:  # type: ignore[assignment]
        """Dienst-Start (oder Neustart des Geräts mit anderer ``boot``) auf demselben Verzeichnis und derselben Uhr."""
        return Box(self.verz, boot=self.boot if boot is ... else boot, uhr=self.uhr, nummer=self.nummer if nummer is None else nummer,
                   asynchron=self.asynchron)
