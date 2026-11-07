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

Stufe 3a ersetzt dieses Modul durch MQTT: ``app`` ruft dann ``HaErsatz`` nicht mehr auf. Der Kern, ``learn``
und ``outbox`` bleiben unverändert.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from . import events as ev
from .eventlog import logge
from .store import KonfigStore

#: Listen-ID, solange noch keine Konfiguration von HA da ist (16 Zeichen ``[0-9a-f]``).
LISTE_ID_STUFE_2 = "0000000000000000"


class Abgelehnt(ValueError):
    """Die Zuordnung wurde nicht angenommen (Schema, Revision)."""


def schreibe_zuordnung(store: KonfigStore, uid: str, ziel: Mapping[str, Any]) -> ev.KonfigGeladen:
    """``uid`` auf ``ziel`` setzen (Revision + 1, ``data-model.md``, Abschnitt 2). Wirft ``Abgelehnt``."""
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


class HaErsatz:
    def __init__(self, sim: _Sim, konfig_store: KonfigStore, ausgabe: Callable[[ev.Ereignis], Any]) -> None:
        self.sim = sim
        self.konfig_store = konfig_store
        self.ausgabe = ausgabe

    def gelernt(self, eintrag: ev.Eintrag) -> None:
        """Die Box hat einen gelernten Tobie gemeldet (Eintrag in ``unknown.json``)."""
        ziel, befehl_id = self.sim.lernziel, self.sim.lernbefehl_id
        grund = "zugeordnet"
        if ziel is None or eintrag.befehl_id is None or eintrag.befehl_id != befehl_id:
            logge("ha_ersatz", "WARNING", "zuordnung", "abgelehnt", daten={"uid": eintrag.uid, "grund": "kein_lernziel"})
            grund = "abgelehnt"
        else:
            try:
                geladen = schreibe_zuordnung(self.konfig_store, eintrag.uid, ziel)
            except Abgelehnt as e:
                logge("ha_ersatz", "WARNING", "zuordnung", "abgelehnt", daten={"uid": eintrag.uid, "grund": str(e)})
                grund = "abgelehnt"
            else:
                logge(
                    "ha_ersatz", "INFO", "zuordnung", "ok",
                    daten={"uid": eintrag.uid, "typ": ziel["typ"], "serie": ziel["serie"], "folge": ziel.get("folge"),
                           "revision": geladen.konfig.revision},
                )
                self.sim.lernziel = None  # das Ziel gilt für genau einen Lernlauf
                self.ausgabe(geladen)
        self.ausgabe(ev.Bestaetigt(eintrag.uid, grund, eintrag.zuletzt, "gelernt"))

