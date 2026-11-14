"""Dauer der Folgen nachholen (Paket A3b; Vertrag W, 14.7; ``data-model.md``, 5a).

* Beim Einsortieren kommt die Dauer aus den Proben, die ohnehin gelaufen sind (``merke_aus_proben``); fehlt sie, holt der Hintergrundlauf sie nach.
* Für den Bestand: **einmal** nach dem Start im Hintergrund, nur Folgen **ohne** ``dauer_s``, **eine Datei nach der anderen**, feste Zeitgrenze
  ``MEDIENINFO_ZEITGRENZE_S`` je Datei, Abbruch bei ``medien_nicht_erreichbar``. **Kein Scan beim Öffnen der Seite**, ``medien/pruefen`` startet nichts.
* Gespeichert wird im Store ``tobibox.medieninfo``, **nie** in ``serie.json``: der Lauf ändert den ``stand`` einer Serie nie und schreibt keine Datei
  auf das NAS (die Boxen synchronisieren ``serie.json``).
* Über ``DAUER_DECKEL_S`` (48 Stunden) wird nichts gespeichert; die Seite zeigt dann „–“.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from . import dateien, ffprobe
from .const import MEDIENINFO_ZEITGRENZE_S
from .namen import sortiere_natuerlich

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

#: ``messe_folge``: die Freigabe ist nicht erreichbar
WEG = "weg"


def _dauer_datei(pfad: Path) -> float | None:
    probe = ffprobe.probe_datei(pfad, zeitlimit=MEDIENINFO_ZEITGRENZE_S)
    if probe.status != ffprobe.OK or not probe.hat_audio or probe.dauer_s is None or probe.dauer_s <= 0:
        return None
    return probe.dauer_s


def messe_folge(medien: Path, serie_pfad: Path, folge: str) -> tuple[int, list[int] | None] | str | None:
    """Synchron (Executor): ``(dauer_s, spuren_s | None)``, ``None`` (nicht messbar: kaputte Datei, Zeitgrenze, kein Audio) oder ``WEG``.

    Bei einer Ordner-Folge wird jeder Track einzeln gemessen (natürliche Reihenfolge wie in der Audio-Ansicht); ist einer nicht messbar,
    gibt es **keine** Dauer (eine halbe Summe wäre falsch). Ganze Sekunden, die Gesamtdauer ist die Summe der gerundeten Tracks."""
    try:
        if not medien.is_dir():
            return WEG
        pfad = serie_pfad / folge
        if pfad.is_dir():
            tracks = sortiere_natuerlich(dateien.tracks_in_ordner(pfad))
            if not tracks:
                return None
            spuren: list[int] = []
            for t in tracks:
                d = _dauer_datei(pfad / t)
                if d is None:
                    return WEG if not medien.is_dir() else None
                spuren.append(int(round(d)))
            return sum(spuren), spuren
        if not pfad.is_file():
            return None
        d = _dauer_datei(pfad)
        if d is None:
            return WEG if not medien.is_dir() else None
        return int(round(d)), None
    except OSError:
        return WEG


class _FreigabeWeg(Exception):
    """Die Freigabe ist nicht erreichbar: der Hintergrundlauf bricht ab."""


class DauerDienst:
    """Nachholen der Dauer im Hintergrund (``hub.dauer``)."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        #: Warteschlange (geordnete Menge von Serien-IDs)
        self._offen: dict[str, None] = {}
        #: in diesem Lauf schon versucht (``(Serien-ID, Folge)``): eine Datei, die nicht messbar ist, wird nicht ständig neu gelesen
        self._versucht: set[tuple[str, str]] = set()
        self._task: asyncio.Task | None = None
        self.beim_start_nachgeholt = False

    # --- Aus den Proben beim Einsortieren ----------------------------------------------------------------

    def merke_aus_proben(self, serie_id: str, folge: str, proben: list[tuple[str, float | None]]) -> None:
        """``proben``: je Datei der Folge ``(Dateiname im Ziel, Dauer aus ``ffprobe``)``. Fehlt eine Dauer, bleibt es dem Nachholen."""
        if not proben or any(d is None or d <= 0 for _, d in proben):
            return
        namen = sortiere_natuerlich([n for n, _ in proben])
        je_name = {n: float(d) for n, d in proben if d is not None}
        spuren = [int(round(je_name[n])) for n in namen]
        if len(proben) == 1:
            self.hub.medieninfo.setze_dauer(serie_id, folge, spuren[0])
        else:
            self.hub.medieninfo.setze_dauer(serie_id, folge, sum(spuren), spuren)

    # --- Hintergrundlauf -----------------------------------------------------------------------------------

    def anstossen(self, serie_ids: list[str]) -> None:
        """Reiht die Einträge ein (nur Folgen ohne Dauer werden gemessen); ein einziger Lauf arbeitet nacheinander."""
        for sid in serie_ids:
            self._offen[sid] = None
            self._versucht = {v for v in self._versucht if v[0] != sid}
        self._starte()

    def _starte(self) -> None:
        if self._offen and (self._task is None or self._task.done()):
            self._task = self.hub.hass.async_create_background_task(self._arbeite(), "tobibox_dauer")

    def nachholen_beim_start(self) -> None:
        """Einmal nach dem Start: alle Einträge. Gemessen werden nur Folgen ohne ``dauer_s``; vorher fallen Werte zu verschwundenen
        Folgen weg (nur nach gelungener Prüfung der Freigabe: bei fehlendem NAS wird nie etwas gelöscht)."""
        if self.beim_start_nachgeholt:
            return
        self.beim_start_nachgeholt = True
        medien = self.hub.medien
        if medien.geprueft_am is not None:
            self.hub.medieninfo.bereinige({sid: list(i.serie.folgen) for sid, i in medien.serien.items()})
        ids = [sid for sid, i in medien.serien.items() if any(not self.hub.medieninfo.hat_dauer(sid, f) for f in i.serie.folgen)]
        if ids:
            self._offen.update(dict.fromkeys(ids))
            self._starte()

    async def warte_auf_ende(self) -> None:
        """Für Tests und das Beenden: wartet, bis die Warteschlange leer ist."""
        while self._task is not None and not self._task.done():
            await asyncio.shield(self._task)

    def abbrechen(self) -> None:
        self._offen.clear()
        if self._task is not None and not self._task.done():
            self._task.cancel()

    async def _arbeite(self) -> None:
        while self._offen:
            sid = next(iter(self._offen))
            del self._offen[sid]
            try:
                await self._serie(sid)
            except _FreigabeWeg:
                _LOGGER.info("Nachholen der Dauer abgebrochen: die Freigabe ist nicht erreichbar")
                self._offen.clear()
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("Dauer für %s nicht ermittelt", sid)

    async def _serie(self, serie_id: str) -> None:
        hub = self.hub
        medien = hub.medien
        geaendert = False
        info = medien.serien.get(serie_id)
        for folge in list(info.serie.folgen) if info else []:
            if hub.medieninfo.hat_dauer(serie_id, folge) or (serie_id, folge) in self._versucht:
                continue
            info = medien.serien.get(serie_id)  # während des Laufs kann die Serie verschwunden oder die Folge fort sein
            if info is None or folge not in info.serie.folgen:
                continue
            self._versucht.add((serie_id, folge))
            ergebnis = await hub.hass.async_add_executor_job(messe_folge, hub.pfade.medien, medien.pfad_serie(info.ordner), folge)
            if ergebnis == WEG:
                raise _FreigabeWeg
            if ergebnis is None:
                continue
            dauer, spuren = ergebnis  # type: ignore[misc]
            jetzt_info = medien.serien.get(serie_id)
            if jetzt_info is None or folge not in jetzt_info.serie.folgen:
                continue
            if hub.medieninfo.setze_dauer(serie_id, folge, dauer, spuren):
                geaendert = True
            else:
                _LOGGER.debug("Dauer von %s/%s über dem Dauerdeckel: nicht gespeichert", serie_id, folge)
        if geaendert:
            hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
