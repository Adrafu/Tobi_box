"""Was nach jedem Kern-Schritt nachgeführt wird: Ring, Bedienung und der Pegel der Töne (T1, 09.11.).

Wie ``ausgang.py`` für Stufe 2: ``App`` und der Testaufbau der CUJ-Tests 14 bis 19 (``tests/fixtures/stufe4.py``) benutzen
**denselben Code**. Eine Kopie in den Tests würde grün bleiben, wenn jemand ``app.py`` ändert.

Reine Funktionen ohne eigenen Zustand: Sie lesen den Kern und schreiben in ``led`` und ``bedienung``.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import events as ev
from . import quiet
from .controls import Bedienung
from .core import KernZustand
from .led import LedLogik
from .volume import GRENZE_AUSBLENDEN, GRENZE_GUTE_NACHT, GRENZE_LEISE_ZEIT, klemmen, wirksame_grenze


def led_ausblenden(led: LedLogik, kern: KernZustand) -> None:
    """Stand des Ausblendens von „Gute Nacht“ aus dem Zustand von ``bedtime`` an ``led`` (Glimmen wird schwächer)."""
    b = kern.teil["bedtime"]
    faktor = None
    if b.modus == "ausblenden" and b.von > 0:
        faktor = (b.letzter if b.letzter is not None else b.von) / b.von
    led.setze_ausblenden(faktor)


def stufe_4(
    led: LedLogik, bedienung: Bedienung | None, kern: KernZustand, e: ev.Ereignis, befehle: Sequence[ev.Befehl], mono: float
) -> None:
    """Ring und Bedienung folgen dem Kern: jede ``ZustandMelden`` und die Strom-Ereignisse an ``led``, Lautstärke an ``controls``."""
    led.beobachte(e, mono)  # Bereit, AkkuStand, LaderGeaendert, AkkuTiefstand, LeserHallo, LeserAlarm
    for b in befehle:
        if isinstance(b, (ev.ZustandMelden, ev.AkkuAnzeigen)):
            led.beobachte(b, mono)  # ``AkkuAnzeigen``: Freigabe der Andock- und Abzieh-Anzeige durch ``idle`` (Ein/Aus, 10.11.)
    if any(isinstance(b, ev.Melden) and b.art == "unbekannt" for b in befehle):
        led.unbekannter_tobie(mono)  # ein unbekannter Tobie wurde aufgelegt (auch unter „stumm“); nach dem ``ZustandMelden``: Aufwachen geht vor
    nachfuehren_lautstaerke(bedienung, kern)
    led_ausblenden(led, kern)


def nachfuehren_lautstaerke(bedienung: Bedienung | None, kern: KernZustand) -> None:
    if bedienung is not None:
        bedienung.setze_lautstaerke(kern.wunsch, wirksame_grenze(kern.grenzen))


def ton_pegel(kern: KernZustand) -> tuple[int, int] | None:
    """``(grenze, lautstaerke)`` für die Töne aus dem Zustand des Kerns, oder ``None`` vor dem ersten ``LautstaerkeSetzen``.

    Ohne die Rampen „ausblenden“ und „gute_nacht“ (Entscheidung J, 09.11.; sonst wären Töne nach dem Ausblenden unhörbar).
    Während der Absenkung von „leiser“ (Rampe über ``ausblenden``) gilt schon das **Ziel** der Absenkung als ``leise_zeit``:
    Ein Ton in diesen 3 s klingt nie über der Grenze, die gleich gilt (B13, 09.11.)."""
    if kern.ausgegeben is None:
        return None
    dauerhaft = {n: w for n, w in kern.grenzen.items() if n not in (GRENZE_AUSBLENDEN, GRENZE_GUTE_NACHT)}
    ziel = quiet.ziel_grenze_absenken(kern.teil["quiet"])
    if ziel is not None:
        dauerhaft[GRENZE_LEISE_ZEIT] = min(ziel, dauerhaft.get(GRENZE_LEISE_ZEIT, ziel))
    return wirksame_grenze(dauerhaft), klemmen(kern.wunsch, dauerhaft)
