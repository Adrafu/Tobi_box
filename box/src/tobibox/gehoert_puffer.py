"""Anbindung des Beobachters „Gehört“: Puffer ``gehoert.json`` (``data-model.md`` 1.6, 1.7; ``docs/designs/gehoert.md`` 3.4).

``gehoert`` (rein) rechnet, dieses Modul hält den Zustand und schreibt. Muster wie ``outbox``: Im Dienst
(``asynchron=True``, Ereignisschleife läuft) schreibt eine einzige Hintergrundaufgabe in einem Thread (die Schleife wartet nie
auf die SD-Karte), immer den neuesten Stand; ohne Schleife (Tests) wird sofort geschrieben. **Synchron** (``fsync``, in der
Schleife, bevor es weitergeht) schreibt der Beobachter bei ``Herunterfahren`` und ``dienst_ende``.

Eine Sperre und ein Zähler der Stände sorgen dafür, dass eine ältere Fassung nie eine neuere ersetzt, auch wenn ein
synchrones Schreiben den Hintergrund-Thread überholt.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import events as ev
from . import gehoert as g
from .eventlog import logge, logge_befehl
from .store import lade_zustandsdatei, schreibe_atomar

NAME = "gehoert.json"
WIEDERHOLEN_S = 60.0  # scheitert das Schreiben (OSError), versucht es der nächste ``Takt`` frühestens nach so langer Zeit erneut


class GehoertPuffer:
    def __init__(
        self,
        verzeichnis: str | Path,
        *,
        boot_id: Callable[[], str | None] = lambda: None,
        neue_id: Callable[[], str] = lambda: str(uuid.uuid4()),
        dauer: Callable[[str, str], int | None] = lambda serie, folge: None,
        asynchron: bool = False,
    ) -> None:
        self.pfad = Path(verzeichnis) / NAME
        self._boot_id_quelle = boot_id
        self._neue_id = neue_id
        self._dauer = dauer
        self._asynchron = asynchron
        self.kontext = g.Kontext(str(uuid.uuid4()), neue_id, dauer)  # bis ``laden``: zufällige Kennung je Dienststart
        self.z = g.Zustand()
        self.quelle = "neu"
        #: seit dem letzten Senden ist eine Zeile dazugekommen (Sitzungsende): ``ha`` sendet dann alle Zeilen (4.5, Punkt 2)
        self.neue_zeilen = False
        self.schreibungen = 0  # Zahl der Schreibvorgänge auf die Platte (Schreibbudget, Tests)
        self._sperre = threading.Lock()
        self._stand = 0  # Zähler der Stände, die geschrieben werden sollen
        self._geschrieben = 0  # höchster Stand auf der Platte
        self._schmutzig = False
        self._schreiber: asyncio.Task | None = None
        self._wiederholen = False  # das letzte Schreiben ist gescheitert: Stand ist nur im Arbeitsspeicher
        self._mono = 0.0  # ``mono`` des letzten Ereignisses
        self._versuch_ab = 0.0  # frühester ``mono`` des nächsten Versuchs nach einem Fehler

    # -- Laden ------------------------------------------------------------------------

    def laden(self, jetzt: ev.Jetzt) -> None:
        """Beim Start: Datei lesen (Rückfall ``.bak``, dann leer), offene Sitzung zur Zeile ``abbruch`` machen (3.2)."""
        # Ist die Kennung des Geräts nicht lesbar, erzeugt die Box eine zufällige je Dienststart (mqtt-v1 3.4)
        boot = self._boot_id_quelle() or str(uuid.uuid4())
        self.kontext = g.Kontext(boot[: g.MAX_BOOT_ID], self._neue_id, self._dauer)
        geladen, self.quelle = lade_zustandsdatei(self.pfad, g.parse_datei, g.Geladen, g.geladen_zu_json)
        self.z, aus = g.starte(geladen, self.kontext)
        self._fuehre(aus)
        if self.z.zeilen:
            logge("gehoert", "INFO", "start", "zeilen", daten={"anzahl": len(self.z.zeilen), "verworfen": self.z.verworfen})

    # -- Beobachten ---------------------------------------------------------------------

    def beobachte(self, e: ev.Ereignis, befehle: Sequence[ev.Befehl], jetzt: ev.Jetzt) -> None:
        """Ein Ereignis des Kerns und die Befehle, die es ausgelöst hat (in dieser Reihenfolge)."""
        self._mono = jetzt.mono
        if self._wiederholen and jetzt.mono >= self._versuch_ab:
            self._wiederholen = False
            self._schreibe(False)  # ein gescheiterter Schreibvorgang wird nachgeholt (höchstens alle ``WIEDERHOLEN_S``)
        self.z, aus = g.step(self.z, e, jetzt, self.kontext)
        alle = list(aus)
        for b in befehle:
            self.z, mehr = g.step_befehl(self.z, b, jetzt, self.kontext)
            alle += mehr
        self._fuehre(alle)

    def dienst_ende(self, jetzt: ev.Jetzt) -> None:
        """Der Dienst endet: offene Sitzung abschließen und **synchron** schreiben (auch ohne ``DienstEndet`` im Kern)."""
        self.z, aus = g.step(self.z, ev.DienstEndet(), jetzt, self.kontext)
        self._fuehre(aus)

    def quittiere(self, sitzungen: Sequence[str], jetzt: ev.Jetzt) -> int:
        """Die quittierten Zeilen löschen (genau diese UUIDs). Gibt die Zahl der gelöschten Zeilen zurück.

        Geschrieben wird mit dem nächsten Schreibvorgang, spätestens nach 10 Minuten (data-model 1.7)."""
        vorher = len(self.z.zeilen)
        self.z, aus = g.step(self.z, g.Quittung(tuple(sitzungen)), jetzt, self.kontext)
        self._fuehre(aus)
        return vorher - len(self.z.zeilen)

    def zwischenstand(self, jetzt: ev.Jetzt) -> dict[str, Any] | None:
        """Die Zeile für einen fälligen Zwischenstand (nur MQTT, nie im Puffer), sonst ``None``."""
        self.z, zeile = g.zwischenstand(self.z, jetzt)
        return zeile

    @property
    def zeilen(self) -> tuple[Mapping[str, Any], ...]:
        return self.z.zeilen

    @property
    def verworfen(self) -> int:
        return self.z.verworfen

    # -- Ausgaben ausführen ---------------------------------------------------------------

    def _fuehre(self, aus: Sequence[g.Ausgabe]) -> None:
        schreiben: g.Schreiben | None = None
        for a in aus:
            if isinstance(a, ev.Protokoll):
                logge_befehl(a)
            elif isinstance(a, g.ZeileNeu):
                self.neue_zeilen = True
            elif isinstance(a, g.Schreiben):
                schreiben = g.Schreiben(a.sync or (schreiben is not None and schreiben.sync), a.grund)
        if schreiben is not None:
            self._schreibe(schreiben.sync)

    def _schreibe(self, sync: bool) -> None:
        self._stand += 1
        if sync:
            self._schreibe_datei(self._stand, g.zu_json(self.z))
            return
        if self._asynchron:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                self._schmutzig = True
                if self._schreiber is None or self._schreiber.done():
                    self._schreiber = loop.create_task(self._schreibe_hintergrund(), name="tobibox-gehoert")
                return
        self._schreibe_datei(self._stand, g.zu_json(self.z))

    def _schreibe_datei(self, stand: int, daten: dict[str, Any]) -> None:
        with self._sperre:
            if stand <= self._geschrieben:
                return  # ein neuerer Stand ist schon auf der Platte
            try:
                schreibe_atomar(self.pfad, daten)
            except OSError as e:
                logge("gehoert", "ERROR", "speichern", "fehler", daten={"detail": repr(e)})
                self._wiederholen = True  # der nächste ``Takt`` nach ``WIEDERHOLEN_S`` versucht es erneut
                self._versuch_ab = self._mono + WIEDERHOLEN_S
                return
            self._geschrieben = stand
            self.schreibungen += 1

    async def _schreibe_hintergrund(self) -> None:
        while self._schmutzig:
            self._schmutzig = False
            stand, daten = self._stand, g.zu_json(self.z)  # Abzug in der Schleife; der Thread sieht nur die Kopie
            await asyncio.to_thread(self._schreibe_datei, stand, daten)

    async def warte_gespeichert(self) -> None:
        """Wartet, bis der letzte Stand auf der Platte ist."""
        while self._schreiber is not None and not self._schreiber.done():
            await asyncio.shield(self._schreiber)
