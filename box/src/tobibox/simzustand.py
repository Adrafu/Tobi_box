"""Die Simulation merkt sich ihre Werte über einen Dienst-Neustart (Mac-Test 12.11.).

Der echte PiSugar meldet laufend; die Simulation kennt nur, was ``sim`` zuletzt gesetzt hat, und vergaß es beim Neustart. Jetzt schreibt
der Dienst die zuletzt gesetzten Werte nach ``<zustand>/sim_zustand.json`` und stellt sie beim Start wieder her, **bevor** ``Bereit``
bzw. die erste Messung kommt (sie gelten als erste Messung: keine Andock-Rückmeldung). Nur Sim-Quellen schreiben und lesen die Datei,
echte Treiber nie. Zurücksetzen: Datei löschen.

Format: ``{"strom": {"pisugar": bool|null, "leser": bool|null}, "akku": int|null, "netz": "home"|"hotspot"|"offline"|null}``.
Fehlt die Datei, gilt „nichts gemerkt“; ist sie kaputt, gibt es eine Warnung im Protokoll und es gilt ebenfalls „nichts gemerkt“.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from .eventlog import logge
from .store import schreibe_atomar

DATEI = "sim_zustand.json"
NETZ_KLASSEN = ("home", "hotspot", "offline")


@dataclass(frozen=True, slots=True)
class SimWerte:
    """Die gemerkten Werte; ``None``: nie gesetzt."""

    pisugar: bool | None = None
    leser: bool | None = None
    akku: int | None = None
    netz: str | None = None

    @property
    def leer(self) -> bool:
        return self == SimWerte()

    def mit(self, **kw) -> SimWerte:  # type: ignore[no-untyped-def]
        return replace(self, **kw)


def pfad(zustand: str | Path) -> Path:
    return Path(zustand) / DATEI


def lade(zustand: str | Path) -> SimWerte:
    """Gemerkte Werte lesen. Fehlende Datei: leer. Kaputte oder unsinnige Datei: WARNING und leer."""
    p = pfad(zustand)
    try:
        roh = p.read_bytes()
    except FileNotFoundError:
        return SimWerte()
    except OSError as e:
        logge("app", "WARNING", "sim_zustand", "unlesbar", daten={"detail": str(e)})
        return SimWerte()
    try:
        d = json.loads(roh.decode("utf-8"))
        strom = d["strom"]
        w = SimWerte(pisugar=strom.get("pisugar"), leser=strom.get("leser"), akku=d.get("akku"), netz=d.get("netz"))
        if not all(x is None or isinstance(x, bool) for x in (w.pisugar, w.leser)):
            raise ValueError("strom muss true, false oder null sein")
        if w.akku is not None and (isinstance(w.akku, bool) or not isinstance(w.akku, int) or not 0 <= w.akku <= 100):
            raise ValueError("akku muss 0..100 sein")
        if w.netz is not None and w.netz not in NETZ_KLASSEN:
            raise ValueError("netz unbekannt")
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        logge("app", "WARNING", "sim_zustand", "kaputt", daten={"detail": str(e) or repr(e)})
        return SimWerte()
    return w


def speichere(zustand: str | Path, w: SimWerte) -> None:
    """Atomar schreiben (``store.schreibe_atomar``). Ein Fehler wird protokolliert und ist nie tödlich."""
    try:
        schreibe_atomar(
            pfad(zustand),
            {"strom": {"pisugar": w.pisugar, "leser": w.leser}, "akku": w.akku, "netz": w.netz},
        )
    except OSError as e:
        logge("app", "WARNING", "sim_zustand", "schreiben_fehlt", daten={"detail": str(e)})
