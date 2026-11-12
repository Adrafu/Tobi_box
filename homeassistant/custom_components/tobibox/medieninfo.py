"""Store ``tobibox.medieninfo`` (``data-model.md``, Abschnitt 5a; Vertrag W, 14.7).

Abgeleitete Werte, die ein Hintergrundlauf berechnet und jederzeit neu berechnen kann. Sie liegen **nicht** in ``serie.json``
(ein Hintergrundlauf darf den ``stand`` einer Serie nie ändern und keine Datei auf das NAS schreiben, die die Boxen mitsynchronisieren),
sondern im HA-``Store`` (``.storage/``, gespeichert mit ``async_delay_save``). Schlüssel ``serie_id``, dann das Feld.

Dieses Paket (A4) schreibt nur ``<serie_id>.cover_suche`` (die Marke „schon gesucht“); Dauer, Kapitel, Codecs und Hörkopie folgen in A-2
und A-3 und brauchen dieselbe Klasse.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .util import jetzt_iso

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

STORAGE_KEY = "tobibox.medieninfo"
STORAGE_VERSION = 1
#: Ergebnisse der Cover-Suche (``cover_suche.ergebnis``)
COVER_ERGEBNISSE = ("tags", "datei", "keine")
SPEICHER_VERZOEGERUNG_S = 10.0


class MedienInfo:
    """Der Store ``tobibox.medieninfo``."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.daten: dict[str, dict[str, Any]] = {}

    async def async_laden(self) -> None:
        roh = await self._store.async_load()
        self.daten = {}
        if isinstance(roh, dict):
            for serie_id, eintrag in roh.items():
                if isinstance(serie_id, str) and isinstance(eintrag, dict):
                    self.daten[serie_id] = eintrag

    def _speichern(self) -> None:
        self._store.async_delay_save(lambda: self.daten, SPEICHER_VERZOEGERUNG_S)

    async def async_speichern(self) -> None:
        await self._store.async_save(self.daten)

    # --- Marke „schon gesucht“ -------------------------------------------------------------------------

    def cover_suche(self, serie_id: str) -> dict[str, Any] | None:
        marke = (self.daten.get(serie_id) or {}).get("cover_suche")
        if isinstance(marke, dict) and marke.get("ergebnis") in COVER_ERGEBNISSE:
            return marke
        return None

    def setze_cover_suche(self, serie_id: str, ergebnis: str) -> None:
        if ergebnis not in COVER_ERGEBNISSE:
            raise ValueError(ergebnis)
        self.daten.setdefault(serie_id, {})["cover_suche"] = {"ergebnis": ergebnis, "zeit": jetzt_iso()}
        self._speichern()

    def loesche_cover_suche(self, serie_id: str) -> None:
        eintrag = self.daten.get(serie_id)
        if eintrag is not None and eintrag.pop("cover_suche", None) is not None:
            if not eintrag:
                self.daten.pop(serie_id, None)
            self._speichern()
