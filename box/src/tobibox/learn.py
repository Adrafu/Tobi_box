"""Teilautomat Lernmodus (``core-interface.md``, 5.2 und 9 Punkt 8 und 9; Tabelle „Lernmodus“).

Reine Funktionen: kein Zugriff auf Dateien, Netz, Uhr oder Zufall. Zustände ``aus`` und ``lernt``.
Die Frist 2 min läuft auf ``jetzt.mono`` ab Annahme des Befehls (``LERN_FRIST_S``), die Ablaufzeit des
Befehls ``jetzt.wall > gueltig_bis`` auf der Wanduhr. Bei unsicherer Uhr wird ``HaLernmodus`` abgelehnt;
``HaLernmodusAbbruch`` nie (die Ablaufzeit wird dann nicht geprüft).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from . import events as ev
from .events import Jetzt

LERN_FRIST_S = 120.0

Ausgabe = tuple[ev.Befehl | ev.InternesEreignis, ...]


@dataclass(frozen=True, slots=True)
class Zustand:
    modus: str = "aus"  # "aus" | "lernt"
    frist_bis: float = 0.0  # mono; nur in ``lernt``
    befehl_id: str | None = None


def neuer_zustand() -> Zustand:
    return Zustand()


def kennzeichen(zustand: Zustand) -> str:
    return zustand.modus


def _prot(ebene: str, ereignis: str, ergebnis: str, **daten: str | int | float | bool | None) -> ev.Protokoll:
    return ev.Protokoll("learn", ebene, ereignis, ergebnis, None, daten)  # type: ignore[arg-type]


def _ende(z: Zustand, grund: str) -> tuple[Zustand, Ausgabe]:
    return Zustand(), (
        ev.TonSpielen("lernen_ende"),
        ev.LernenGeaendert(False),
        _prot("INFO", "lernmodus_ende", grund, befehl_id=z.befehl_id),
    )


def step(zustand: Zustand, ereignis: ev.Ereignis | ev.InternesEreignis, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    z = zustand

    if isinstance(ereignis, ev.HaLernmodus):
        if z.modus == "lernt":
            return z, (_prot("INFO", "lernmodus_befehl", "ignoriert", grund="laeuft_schon", befehl_id=ereignis.befehl_id),)
        if jetzt.wall > ereignis.gueltig_bis:
            return z, (_prot("WARNING", "lernmodus_befehl", "abgelaufen", befehl_id=ereignis.befehl_id),)
        if not jetzt.zeit_ok:
            return z, (
                _prot("WARNING", "lernmodus_befehl", "abgelehnt", grund="zeit_unsicher", befehl_id=ereignis.befehl_id),
                ev.EreignisSenden(
                    "befehl_abgelehnt",
                    {"befehl": "lernen", "befehl_id": ereignis.befehl_id, "grund": "zeit_unsicher"},
                ),
            )
        neu = Zustand("lernt", jetzt.mono + LERN_FRIST_S, ereignis.befehl_id)
        return neu, (
            ev.TonSpielen("lernen_beginn"),
            ev.LernenGeaendert(True),
            _prot("INFO", "lernmodus_beginn", "ok", befehl_id=ereignis.befehl_id),
        )

    if isinstance(ereignis, ev.HaLernmodusAbbruch):
        if z.modus != "lernt":
            return z, (_prot("INFO", "lernmodus_abbruch", "wirkungslos", befehl_id=ereignis.befehl_id),)
        if jetzt.zeit_ok and jetzt.wall > ereignis.gueltig_bis:
            return z, (_prot("WARNING", "lernmodus_abbruch", "abgelaufen", befehl_id=ereignis.befehl_id),)
        return _ende(z, "abbruch")

    if z.modus != "lernt":
        return z, ()

    if isinstance(ereignis, ev.Aufgelegt):
        neu, aus = _ende(z, "aufgelegt")
        return neu, (ev.Melden("gelernt", ereignis.uid, z.befehl_id),) + aus
    if isinstance(ereignis, ev.Takt):
        if jetzt.mono >= z.frist_bis:
            return _ende(z, "frist")
        return z, ()
    # ``Gesperrt`` (keine Kennung) und alles Übrige ändern nichts.
    return z, ()
