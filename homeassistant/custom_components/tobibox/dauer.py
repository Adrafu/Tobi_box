"""Dauer, Kapitel und Codecs der Folgen nachholen (Pakete A3b und A3b3; Vertrag W, 14.7; ``data-model.md``, 5a).

* Beim Einsortieren kommen sie aus den Proben, die ohnehin gelaufen sind (``merke_aus_proben``); fehlt etwas, holt der Hintergrundlauf es nach.
  Ein ``ffprobe``-Lauf je Datei liefert alles (Dauer, ``-show_chapters``, Codec, Tag ``title``): **kein zweiter Lesedurchgang** über das NAS.
* Für den Bestand: **einmal** nach dem Start im Hintergrund, nur Folgen, deren Eintrag **unvollständig** ist (keine ``dauer_s`` **oder** ein älterer
  Stand ``info_v`` ohne Kapitel und Codecs), **eine Datei nach der anderen**, feste Zeitgrenze ``MEDIENINFO_ZEITGRENZE_S`` je Datei, Abbruch bei
  ``medien_nicht_erreichbar``. **Kein Scan beim Öffnen der Seite**, ``medien/pruefen`` startet nichts.
* Gespeichert wird im Store ``tobibox.medieninfo``, **nie** in ``serie.json``: der Lauf ändert den ``stand`` einer Serie nie und schreibt keine Datei
  auf das NAS (die Boxen synchronisieren ``serie.json``).
* Über ``DAUER_DECKEL_S`` (48 Stunden) wird nichts gespeichert; die Seite zeigt dann „–“.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import dateien, ffprobe
from .const import MEDIENINFO_ZEITGRENZE_S
from .kapitel import TrackInfo, baue_kapitel
from .namen import sortiere_natuerlich

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

#: ``messe_folge``: die Freigabe ist nicht erreichbar
WEG = "weg"


@dataclass
class Messung:
    """Was ein Lauf über eine Folge ergibt."""

    dauer_s: int
    spuren_s: list[int] | None = None  # nur bei Ordner-Folgen
    kapitel: list[dict[str, Any]] = field(default_factory=list)
    codecs: list[str | None] = field(default_factory=list)  # je Track, in Folgenreihenfolge


def _track(name: str, probe: ffprobe.Probe | None) -> TrackInfo | None:
    """Aus einer Probe; ``None``, wenn sie nichts Messbares hat (kaputte Datei, Zeitgrenze, kein Audio, keine Dauer)."""
    if probe is None or probe.status != ffprobe.OK or not probe.hat_audio or probe.dauer_s is None or not probe.dauer_s > 0:
        return None
    return TrackInfo(name=name, dauer_s=float(probe.dauer_s), codec=probe.codec, titel=ffprobe.tag(probe.tags, "titel"), kapitel=list(probe.kapitel))


def baue_messung(tracks: list[TrackInfo], ordner: bool) -> Messung:
    """``tracks`` in der Reihenfolge der Folge. Ganze Sekunden; die Gesamtdauer eines Ordners ist die Summe der gerundeten Tracks."""
    spuren = [int(round(t.dauer_s)) for t in tracks]
    return Messung(
        dauer_s=sum(spuren) if ordner else spuren[0],
        spuren_s=spuren if ordner else None,
        kapitel=baue_kapitel(tracks, ordner),
        codecs=[t.codec for t in tracks],
    )


def _messe_datei(pfad: Path) -> TrackInfo | None:
    return _track(pfad.name, ffprobe.probe_datei(pfad, zeitlimit=MEDIENINFO_ZEITGRENZE_S))


def messe_folge(medien: Path, serie_pfad: Path, folge: str) -> Messung | str | None:
    """Synchron (Executor): ``Messung``, ``None`` (nicht messbar: kaputte Datei, Zeitgrenze, kein Audio) oder ``WEG``.

    Bei einer Ordner-Folge wird jeder Track einzeln gemessen (natürliche Reihenfolge wie in der Audio-Ansicht); ist einer nicht messbar,
    gibt es **keine** Dauer (eine halbe Summe wäre falsch). Ganze Sekunden, die Gesamtdauer ist die Summe der gerundeten Tracks."""
    try:
        if not medien.is_dir():
            return WEG
        pfad = serie_pfad / folge
        if pfad.is_dir():
            namen = sortiere_natuerlich(dateien.tracks_in_ordner(pfad))
            if not namen:
                return None
            tracks: list[TrackInfo] = []
            for n in namen:
                t = _messe_datei(pfad / n)
                if t is None:
                    return WEG if not medien.is_dir() else None
                tracks.append(t)
            return baue_messung(tracks, True)
        if not pfad.is_file():
            return None
        t = _messe_datei(pfad)
        if t is None:
            return WEG if not medien.is_dir() else None
        return baue_messung([t], False)
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

    def merke_aus_proben(self, serie_id: str, folge: str, proben: list[tuple[str, ffprobe.Probe | None]]) -> None:
        """``proben``: je Datei der Folge ``(Dateiname im Ziel, Probe aus ``ffprobe``)``. Fehlt bei einer Datei die Probe oder die Dauer, bleibt es
        dem Nachholen. Mehrere Dateien sind eine Ordner-Folge."""
        if not proben:
            return
        je_name = {n: _track(n, p) for n, p in proben}
        if any(t is None for t in je_name.values()):
            return
        tracks = [je_name[n] for n in sortiere_natuerlich(list(je_name))]  # type: ignore[misc]
        m = baue_messung(tracks, len(proben) > 1)
        self.hub.medieninfo.setze_info(serie_id, folge, m.dauer_s, m.spuren_s, m.kapitel, m.codecs)

    # --- Hintergrundlauf -----------------------------------------------------------------------------------

    def anstossen(self, serie_ids: list[str]) -> None:
        """Reiht die Einträge ein (nur Folgen mit unvollständigem Eintrag werden gemessen); ein einziger Lauf arbeitet nacheinander."""
        for sid in serie_ids:
            self._offen[sid] = None
            self._versucht = {v for v in self._versucht if v[0] != sid}
        self._starte()

    def _starte(self) -> None:
        if self._offen and (self._task is None or self._task.done()):
            self._task = self.hub.hass.async_create_background_task(self._arbeite(), "tobibox_dauer")

    def nachholen_beim_start(self) -> None:
        """Einmal nach dem Start: alle Einträge. Gemessen werden nur Folgen mit unvollständigem Eintrag (``hat_info``); vorher fallen Werte zu verschwundenen
        Folgen weg (nur nach gelungener Prüfung der Freigabe: bei fehlendem NAS wird nie etwas gelöscht)."""
        if self.beim_start_nachgeholt:
            return
        self.beim_start_nachgeholt = True
        medien = self.hub.medien
        if medien.geprueft_am is not None:
            self.hub.medieninfo.bereinige({sid: list(i.serie.folgen) for sid, i in medien.serien.items()})
        ids = [sid for sid, i in medien.serien.items() if any(not self.hub.medieninfo.hat_info(sid, f) for f in i.serie.folgen)]
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
            if hub.medieninfo.hat_info(serie_id, folge) or (serie_id, folge) in self._versucht:
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
            jetzt_info = medien.serien.get(serie_id)
            if jetzt_info is None or folge not in jetzt_info.serie.folgen:
                continue
            if hub.medieninfo.setze_info(serie_id, folge, ergebnis.dauer_s, ergebnis.spuren_s, ergebnis.kapitel, ergebnis.codecs):  # type: ignore[union-attr]
                geaendert = True
            else:
                _LOGGER.debug("Dauer von %s/%s über dem Dauerdeckel: nicht gespeichert", serie_id, folge)
        if geaendert:
            hub.emit("medien", "serien_geaendert", {"serie_ids": [serie_id]})
