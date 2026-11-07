"""HA-Ersatz für Stufe 2: Zuordnung schreiben und bestätigen, wie Home Assistant es täte.

Nur in Stufe 2 (ohne Broker). Der Kernvertrag kennt für den Lernmodus kein Zielfeld
(``HaLernmodus`` trägt nur Befehls-ID und Ablaufzeit): Das Ziel hält HA, und **HA schreibt die
Zuordnung** (``mqtt-v1.md``, 4.2). Hier spielt ``sim`` die Rolle von HA: ``sim learn`` merkt sich das
Ziel (``Sim.lernziel``), und meldet die Box danach den gelernten Tobie (``Melden("gelernt")``, Eintrag in
``unknown.json``), dann

1. schreibt ``HaErsatz`` die Zuordnung über ``KonfigStore`` in ``config.json`` (Revision + 1),
2. gibt ``KonfigGeladen`` aus (die Box wechselt wie bei einer Liste von HA auf das Ziel, 9.14) und
3. bestätigt mit ``Bestaetigt(grund="zugeordnet")``; ohne passendes Ziel mit ``grund="abgelehnt"``
   (z. B. unbekannter Lernbefehl, ungültige Kennung).

Ist die Kennung schon zugeordnet, fragt HA vor dem Überschreiben nach (``mqtt-v1.md``, 4.2 Punkt 4).
Die Rückfrage ersetzt der Schalter ``sim learn --ueberschreiben``: Ohne ihn lehnt der Ersatz ab
(``grund="abgelehnt"``, die Zuordnung bleibt), mit ihm überschreibt er.

Stufe 3a ersetzt dieses Modul durch MQTT: ``app`` ruft dann ``HaErsatz`` nicht mehr auf. Der Kern, ``learn``
und ``outbox`` bleiben unverändert.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from . import events as ev
from .eventlog import logge as _logge
from .store import KonfigStore


def logge(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """Alle Zeilen des HA-Ersatzes tragen ``sim=true`` (``core-interface.md``, 6.5 Punkt 4)."""
    _logge(*args, sim=True, **kwargs)


#: Listen-ID, solange noch keine Konfiguration von HA da ist (16 Zeichen ``[0-9a-f]``).
LISTE_ID_STUFE_2 = "0000000000000000"


class Abgelehnt(ValueError):
    """Die Zuordnung wurde nicht angenommen (Schema, Revision)."""


#: Lesen, Ändern und Schreiben von ``config.json`` geht nur einzeln (die Aufrufe laufen in Threads).
_SPERRE = threading.Lock()


def schreibe_zuordnung(store: KonfigStore, uid: str, ziel: Mapping[str, Any]) -> ev.KonfigGeladen:
    """``uid`` auf ``ziel`` setzen (Revision + 1, ``data-model.md``, Abschnitt 2). Wirft ``Abgelehnt``."""
    with _SPERRE:
        store.laden()
        roh = dict(store.roh)
        roh["zuordnungen"] = dict(roh["zuordnungen"])
        alt = store.konfig
        roh["liste_id"] = alt.liste_id or LISTE_ID_STUFE_2
        roh["revision"] = alt.revision + 1
        roh["zuordnungen"][uid] = {"ziel": dict(ziel)}
        a = store.annehmen(roh)
        if not a.angenommen:
            raise Abgelehnt(a.grund)
        return ev.KonfigGeladen(store.konfig)


class _Sim(Protocol):
    lernziel: dict[str, str] | None
    lernbefehl_id: str | None
    ueberschreiben: bool


class HaErsatz:
    def __init__(self, sim: _Sim, konfig_store: KonfigStore, ausgabe: Callable[[ev.Ereignis], Any]) -> None:
        self.sim = sim
        self.konfig_store = konfig_store
        self.ausgabe = ausgabe

    def gelernt(self, eintrag: ev.Eintrag) -> None:
        """Die Box hat einen gelernten Tobie gemeldet (Eintrag in ``unknown.json``)."""
        ziel = self._pruefe(eintrag)
        geladen = self._schreibe(eintrag, ziel) if ziel is not None else None
        self._abschluss(eintrag, ziel, geladen)

    async def gelernt_async(self, eintrag: ev.Eintrag) -> None:
        """Wie ``gelernt``; das Schreiben von ``config.json`` (mit ``fsync``) läuft in einem Thread."""
        ziel = self._pruefe(eintrag)
        geladen = await asyncio.to_thread(self._schreibe, eintrag, ziel) if ziel is not None else None
        self._abschluss(eintrag, ziel, geladen)

    def _pruefe(self, eintrag: ev.Eintrag) -> dict[str, str] | None:
        """Das Ziel des Lernlaufs, oder ``None`` (abgelehnt, die Zeile steht schon im Protokoll)."""
        ziel, befehl_id = self.sim.lernziel, self.sim.lernbefehl_id
        if ziel is None or eintrag.befehl_id is None or eintrag.befehl_id != befehl_id:
            logge("ha_ersatz", "WARNING", "zuordnung", "abgelehnt", daten={"uid": eintrag.uid, "grund": "kein_lernziel"})
            return None
        if eintrag.uid in self.konfig_store.konfig.zuordnungen and not self.sim.ueberschreiben:
            logge(
                "ha_ersatz", "WARNING", "zuordnung", "abgelehnt",
                meldung=(
                    f"{eintrag.uid} ist schon zugeordnet und bleibt, wie er ist. "
                    "Zum Überschreiben: tobibox sim learn --ueberschreiben"
                ),
                daten={"uid": eintrag.uid, "grund": "schon_zugeordnet"},
            )
            self.sim.lernziel = None  # der Lernlauf ist zu Ende
            return None
        return ziel

    def _schreibe(self, eintrag: ev.Eintrag, ziel: dict[str, str]) -> ev.KonfigGeladen | None:
        try:
            return schreibe_zuordnung(self.konfig_store, eintrag.uid, ziel)
        except Abgelehnt as e:
            logge("ha_ersatz", "WARNING", "zuordnung", "abgelehnt", daten={"uid": eintrag.uid, "grund": str(e)})
            return None

    def _abschluss(self, eintrag: ev.Eintrag, ziel: dict[str, str] | None, geladen: ev.KonfigGeladen | None) -> None:
        if ziel is not None and geladen is not None:
            logge(
                "ha_ersatz", "INFO", "zuordnung", "ok",
                daten={"uid": eintrag.uid, "typ": ziel["typ"], "serie": ziel["serie"], "folge": ziel.get("folge"),
                       "revision": geladen.konfig.revision},
            )
            self.sim.lernziel = None  # das Ziel gilt für genau einen Lernlauf
            self.ausgabe(geladen)
        grund = "zugeordnet" if geladen is not None else "abgelehnt"
        self.ausgabe(ev.Bestaetigt(eintrag.uid, grund, eintrag.zuletzt, "gelernt"))
