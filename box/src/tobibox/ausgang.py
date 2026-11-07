"""Ereignis-Ausgang, Simulations-Treiber und HA-Ersatz: die Verdrahtung der Stufe 2 an einer Stelle.

``App`` und der Testaufbau (``tests/conftest.py``, ``SimBox``) benutzen dieselbe Klasse. So prüfen die
CUJ-Tests 7a und 7b diesen Code und keinen Nachbau.

* ``Melden`` -> ``Outbox`` (``unknown.json``); bei ``gelernt`` spielt der HA-Ersatz Home Assistant.
* ``Bestaetigt`` -> ``Outbox``, **nicht** an den Kern (``core-interface.md``, Abschnitt 3).
* Nimmt der Kern den Lernmodus-Befehl an, sagt ``nach_kern`` es ``sim`` (Ziel und Befehls-ID gelten erst dann).
* Ereignisse, die ``sim`` oder der HA-Ersatz erzeugen, werden gemerkt (``war_sim``), damit ``app`` ihre
  Protokollzeilen mit ``sim=true`` schreibt (Abschnitt 6.5, Punkt 4).

Stufe 3a ersetzt ``sim`` und den HA-Ersatz durch MQTT; ``Outbox`` bleibt.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import events as ev
from .clock import Uhr
from .eventlog import logge
from .ha_ersatz import HaErsatz
from .outbox import Outbox
from .sim import Sim
from .store import KonfigStore


class Ausgang:
    def __init__(
        self,
        zustand: str | Path,
        uhr: Uhr,
        ereignisse_ein: Callable[[ev.Ereignis], Any],
        konfig_store: KonfigStore,
        auskunft: Callable[[], dict[str, Any]] | None = None,
        *,
        asynchron: bool = False,
    ) -> None:
        self._ein = ereignisse_ein
        self._sim_ereignisse: set[int] = set()  # ``id`` der Ereignisse von ``sim``, solange sie in der Schlange liegen
        self._lernbefehl: str | None = None  # Befehls-ID des Lernlaufs, den ``sim`` schon kennt
        self.outbox = Outbox(zustand, asynchron=asynchron)
        self.sim = Sim(zustand, self._von_sim, uhr, konfig_store, auskunft)
        self.ha_ersatz = HaErsatz(self.sim, konfig_store, self._von_sim)

    def _von_sim(self, e: ev.Ereignis) -> None:
        self._sim_ereignisse.add(id(e))
        self._ein(e)

    def war_sim(self, e: ev.Ereignis) -> bool:
        """Kommt das Ereignis von ``sim`` oder vom HA-Ersatz? (Einmal fragen, wenn es verarbeitet wird.)"""
        if id(e) in self._sim_ereignisse:
            self._sim_ereignisse.discard(id(e))
            return True
        return False

    # -- Ereignisse ---------------------------------------------------------------

    def bestaetigt(self, e: ev.Bestaetigt, *, sim: bool = False) -> bool:
        """Erst die Bestätigung löscht einen Eintrag (Abschnitt 7); der Broker allein bestätigt nichts."""
        return self.outbox.bestaetigt(e.id, e.grund, e.zuletzt, e.art, sim=sim)

    def nach_kern(self, kern: Any) -> None:
        """Nach jedem ``core.step``: Hat der Kern einen Lernmodus-Befehl angenommen, erfährt es ``sim``."""
        lernen = kern.teil["learn"]
        befehl_id = lernen.befehl_id if lernen.modus == "lernt" else None
        if befehl_id is not None and befehl_id != self._lernbefehl:
            self.sim.angenommen(befehl_id)
        self._lernbefehl = befehl_id

    # -- Befehle ------------------------------------------------------------------

    def _buche(self, b: ev.Melden, jetzt: ev.Jetzt) -> ev.Eintrag:
        eintrag = self.outbox.melden(b.art, b.uid, b.befehl_id, jetzt)
        logge("app", "INFO", "gemeldet", b.art, daten={"uid": b.uid, "befehl_id": b.befehl_id})
        return eintrag

    def melde(self, b: ev.Melden, jetzt: ev.Jetzt) -> None:
        """``Melden`` ausführen (ohne Ereignisschleife: Testaufbau)."""
        eintrag = self._buche(b, jetzt)
        if b.art == "gelernt":
            self.ha_ersatz.gelernt(eintrag)

    async def melde_async(self, b: ev.Melden, jetzt: ev.Jetzt) -> None:
        """``Melden`` ausführen (im Dienst: das Schreiben der Zuordnung blockiert die Schleife nicht)."""
        eintrag = self._buche(b, jetzt)
        if b.art == "gelernt":
            await self.ha_ersatz.gelernt_async(eintrag)
