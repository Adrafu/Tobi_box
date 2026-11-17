"""Favoriten (Stufe B, Paket B2; ``docs/data-model.md`` 12.2, Vertrag W Befehle 55 und 56).

Store ``tobibox.favoriten`` (Version 1, ``.storage/``) **für die ganze Familie**: je Eintrag ein Stern an einer Serie (``folge`` = ``None``) oder an einer
Folge. Im Speicher sofort, auf der Platte gesammelt. Einträge, deren Serie oder Folge es nicht mehr gibt, fallen **beim Lesen** weg (der Speicher
wird nicht sofort bereinigt) – aber nur nach gelungener Prüfung der Freigabe: fehlt das NAS, wird nichts ausgeblendet.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .const import FAVORITEN_MAX, FAVORITEN_SPEICHER_VERZOEGERUNG_S
from .fehler import TobiboxFehler
from .util import jetzt_iso

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "tobibox.favoriten"
STORAGE_VERSION = 1


def _eintrag_ok(e: Any) -> bool:
    return (
        isinstance(e, dict)
        and isinstance(e.get("serie_id"), str)
        and bool(e["serie_id"])
        and (e.get("folge") is None or (isinstance(e["folge"], str) and bool(e["folge"])))
        and isinstance(e.get("gesetzt_von"), str)
        and isinstance(e.get("gesetzt_am"), str)
    )


def _bereinige_form(roh: Any) -> list[dict[str, Any]]:
    """Ungültige und doppelte Einträge fallen weg; höchstens ``FAVORITEN_MAX``."""
    aus: list[dict[str, Any]] = []
    gesehen: set[tuple[str, str | None]] = set()
    liste = roh.get("eintraege") if isinstance(roh, dict) else None
    for e in liste if isinstance(liste, list) else []:
        if not _eintrag_ok(e) or (e["serie_id"], e["folge"]) in gesehen:
            continue
        gesehen.add((e["serie_id"], e["folge"]))
        aus.append({k: e[k] for k in ("serie_id", "folge", "gesetzt_von", "gesetzt_am")})
    return aus[:FAVORITEN_MAX]


class Favoriten:
    """``hub.favoriten``."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self._store: Store[dict[str, Any]] = Store(hub.hass, STORAGE_VERSION, STORAGE_KEY)
        self.eintraege: list[dict[str, Any]] = []
        self._geplant = False

    # --- Laden und Speichern -----------------------------------------------------------------------------

    async def async_laden(self) -> None:
        self.eintraege = _bereinige_form(await self._store.async_load())

    def _speichern(self) -> None:
        if self._geplant:
            return
        self._geplant = True
        self._store.async_delay_save(self._daten_fuer_die_platte, FAVORITEN_SPEICHER_VERZOEGERUNG_S)

    def _daten_fuer_die_platte(self) -> dict[str, Any]:
        self._geplant = False
        return {"eintraege": self.eintraege}

    async def async_speichern(self) -> None:
        self._geplant = False
        await self._store.async_save({"eintraege": self.eintraege})

    # --- Schreiben -----------------------------------------------------------------------------------------

    def _finde(self, serie_id: str, folge: str | None) -> dict[str, Any] | None:
        return next((e for e in self.eintraege if e["serie_id"] == serie_id and e["folge"] == folge), None)

    def setze(self, nutzer_id: str, serie_id: str, folge: str | None, an: bool) -> bool:
        """Setzt oder nimmt einen Stern. Gibt ``True`` zurück, wenn sich etwas geändert hat (eine Wiederholung ist kein Fehler).

        Fehler: ``serie_nicht_gefunden``, ``folge_nicht_gefunden`` (nur beim Setzen), ``zu_viele_favoriten``."""
        vorhanden = self._finde(serie_id, folge)
        if not an:
            if vorhanden is None:
                return False
            self.eintraege.remove(vorhanden)
            self._speichern()
            return True
        info = self.hub.medien.finde(serie_id)
        if folge is not None and folge not in info.serie.folgen:
            raise TobiboxFehler("folge_nicht_gefunden")
        if vorhanden is not None:
            return False
        if len(self.eintraege) >= FAVORITEN_MAX:
            raise TobiboxFehler("zu_viele_favoriten")
        self.eintraege.append({"serie_id": serie_id, "folge": folge, "gesetzt_von": nutzer_id, "gesetzt_am": jetzt_iso()})
        self._speichern()
        return True

    # --- Lesen ----------------------------------------------------------------------------------------------

    def _existiert(self, e: dict[str, Any]) -> bool:
        medien = self.hub.medien
        if medien.geprueft_am is None:
            return True
        info = medien.serien.get(e["serie_id"])
        return info is not None and (e["folge"] is None or e["folge"] in info.serie.folgen)

    def liste(self) -> list[dict[str, Any]]:
        """Die Einträge, deren Serie und Folge es gibt (Befehl 56); älteste zuerst."""
        return [dict(e) for e in self.eintraege if self._existiert(e)]

    def menge(self) -> set[tuple[str, str | None]]:
        """``(serie_id, folge)`` aller sichtbaren Einträge (für das Feld ``favorit`` und den Filter)."""
        return {(e["serie_id"], e["folge"]) for e in self.eintraege if self._existiert(e)}

    def ist_favorit(self, serie_id: str, folge: str | None = None) -> bool:
        e = self._finde(serie_id, folge)
        return e is not None and self._existiert(e)

    # --- Verschieben und Zusammenführen --------------------------------------------------------------------

    def schreibe_um(self, zuordnung: dict[tuple[str, str], tuple[str, str]], serie_um: tuple[str, str] | None = None) -> None:
        """Zieht Sterne mit: ``(serie, folge)`` -> ``(neue serie, neue folge)``; ``serie_um = (alt, neu)`` zieht außerdem den Stern an der Serie selbst
        um (Zusammenführen). Steht der Stern am Ziel schon, bleibt einer (der ältere)."""
        geaendert = False
        for e in self.eintraege:
            neu: tuple[str, str | None] | None = None
            if e["folge"] is not None and (e["serie_id"], e["folge"]) in zuordnung:
                neu = zuordnung[(e["serie_id"], e["folge"])]
            elif serie_um is not None and e["folge"] is None and e["serie_id"] == serie_um[0]:
                neu = (serie_um[1], None)
            if neu is not None:
                e["serie_id"], e["folge"] = neu
                geaendert = True
        if not geaendert:
            return
        gesehen: set[tuple[str, str | None]] = set()
        rest: list[dict[str, Any]] = []
        for e in sorted(self.eintraege, key=lambda x: x["gesetzt_am"]):
            if (e["serie_id"], e["folge"]) in gesehen:
                continue
            gesehen.add((e["serie_id"], e["folge"]))
            rest.append(e)
        self.eintraege = rest
        self._speichern()
