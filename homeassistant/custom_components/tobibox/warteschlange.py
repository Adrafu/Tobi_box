"""Warteschlange „nächster neuer Tobie“ (Vertrag W, 3.13 und 4.8; Fähigkeit ``warteschlange``).

Man merkt am Handy vorab, was der **nächste unbekannte Tobie** spielen soll („Vormerkung“). Meldet eine Box danach eine
unbekannte Kennung (``tobibox/<box>/unknown/<uid>`` mit ``art="unbekannt"``), ordnet HA sie selbst zu. Box und MQTT bleiben
unverändert.

* Die Einträge liegen im HA-Speicher (``store.warteschlange``), getrennt von der Konfiguration, und werden bei jeder
  Änderung **sofort** gespeichert (Regel 11).
* Eine eigene Sperre; Reihenfolge der Sperren: Eingang, Serien, **Warteschlange**, Konfiguration (Abschnitt 1). Darum wird die
  Freigabe **vor** dieser Sperre geprüft und nicht in ihr.
* Ein Treffer schreibt Zuordnung und Austragen in **einem** Schreibvorgang (``async_aendere(…, mit_warteschlange=…)``).
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import logging
import secrets
from typing import TYPE_CHECKING, Any

from .const import TOBIE_NAME_MAX, WARTESCHLANGE_MAX
from .fehler import TobiboxFehler
from .media import name_pruefen
from .schutz import Nutzer
from .store import ZUSTAND_OK
from .util import jetzt_iso

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)


class _SchonZugeordnet(Exception):
    """Die Kennung hat inzwischen ein Ziel (Regel 1): nichts schreiben."""


class Warteschlange:
    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.sperre = asyncio.Lock()

    # --- Hilfen ------------------------------------------------------------------------------------------

    @property
    def eintraege(self) -> list[dict[str, Any]]:
        return self.hub.store.warteschlange

    def _reihenfolge(self) -> list[dict[str, Any]]:
        return sorted(self.eintraege, key=lambda e: e["nr"])

    def _ziel_info(self, ziel: dict[str, Any]) -> tuple[str | None, str | None, bool | None]:
        """``(serie_name, folge_anzeige, folge_vorhanden)`` wie bei ``zuordnung/list``, aus dem Zwischenspeicher der Serien."""
        if ziel["typ"] == "aktion":
            return None, None, None
        info = self.hub.medien.serien.get(ziel["serie"])
        serie_name = info.serie.name if info else None
        if ziel["typ"] != "folge":
            return serie_name, None, None
        vorhanden = bool(info) and ziel["folge"] in info.serie.folgen
        return serie_name, (info.serie.anzeige(ziel["folge"]) if vorhanden else None), vorhanden

    def _ziel_fehlt(self, ziel: dict[str, Any]) -> bool:
        if ziel["typ"] == "aktion":
            return False
        info = self.hub.medien.serien.get(ziel["serie"])
        return info is None or (ziel["typ"] == "folge" and ziel["folge"] not in info.serie.folgen)

    def eintrag_objekt(self, e: dict[str, Any]) -> dict[str, Any]:
        """Die „Vormerkung“ des Vertrags (3.13)."""
        serie_name, folge_anzeige, folge_vorhanden = self._ziel_info(e["ziel"])
        reihe = self._reihenfolge()
        position = next((i for i, x in enumerate(reihe, 1) if x["id"] == e["id"]), len(reihe) + 1)
        return {
            "id": e["id"],
            "box": e["box"],
            "ziel": copy.deepcopy(e["ziel"]),
            "serie_name": serie_name,
            "folge_anzeige": folge_anzeige,
            "folge_vorhanden": folge_vorhanden,
            "angelegt_von": copy.deepcopy(e["angelegt_von"]),
            "angelegt_am": e["angelegt_am"],
            "name": e.get("name"),
            "position": position,
        }

    def _ziel_text(self, ziel: dict[str, Any]) -> str:
        with contextlib.suppress(Exception):
            return self.hub.ziel_text(ziel)
        return str(ziel)

    @staticmethod
    def _benutzer(nutzer: Nutzer | None) -> str:
        return f"{(nutzer.name if nutzer else None) or 'ohne Benutzer'} ({(nutzer.id if nutzer else None) or '-'})"

    async def _aendern(self, aenderung: Any) -> None:
        """Ändert ``store.warteschlange`` und speichert sofort; scheitert das Speichern, bleibt der alte Stand."""
        store = self.hub.store
        alt = (store.warteschlange, store.warteschlange_nr)
        store.warteschlange = copy.deepcopy(store.warteschlange)
        try:
            aenderung()
            await store.async_speichern()
        except Exception:
            store.warteschlange, store.warteschlange_nr = alt
            raise

    # --- Start (Regel 10, 11) -----------------------------------------------------------------------------

    async def beim_start(self) -> None:
        """Verwirft Einträge mit einer Box, die in der Einrichtung nicht mehr vorkommt (``box_unbekannt``)."""
        weg = [e for e in self.eintraege if e["box"] is not None and e["box"] not in self.hub.boxen]
        if not weg:
            return
        ids = {e["id"] for e in weg}

        def entfernen() -> None:
            self.hub.store.warteschlange[:] = [e for e in self.hub.store.warteschlange if e["id"] not in ids]

        await self._aendern(entfernen)
        for e in weg:
            _LOGGER.info("Warteschlange: Eintrag %s verworfen (Box %s ist nicht mehr eingerichtet, Ziel %s)", e["id"], e["box"], self._ziel_text(e["ziel"]))
            self.hub.emit("warteschlange", "abgebrochen", {"id": e["id"], "grund": "box_unbekannt"})

    # --- Befehle 47 bis 49 ---------------------------------------------------------------------------------

    def liste(self) -> dict[str, Any]:
        """``warteschlange/list`` (Nr. 48): aus dem Speicher und dem Zwischenspeicher der Serien."""
        reihe = self._reihenfolge()
        return {"eintraege": [self.eintrag_objekt(e) for e in reihe], "gesamt": len(reihe)}

    async def setzen(self, box: str | None, ziel_roh: Any, nutzer: Nutzer | None = None, name: Any = None) -> dict[str, Any]:
        """``warteschlange/set`` (Nr. 47). ``name`` (K7): optional, geprüft wie bei ``zuordnung/set`` (``name_ungueltig``)."""
        hub = self.hub
        if hub.store.zustand != ZUSTAND_OK:  # ein Treffer könnte nichts zuordnen
            raise TobiboxFehler("konfig_nicht_bereit")
        hub.schutz.warteschlange_pruefen(nutzer)
        if box is not None and box not in hub.boxen:
            raise TobiboxFehler("box_unbekannt")
        ziel = await hub.pruefe_ziel(ziel_roh)  # ``ziel_ungueltig``, ``serie_nicht_gefunden``, ``folge_nicht_gefunden``
        name_neu = None if name is None else name_pruefen(name, TOBIE_NAME_MAX)
        async with self.sperre:
            if any(e["box"] == box and e["ziel"] == ziel for e in self.eintraege):
                raise TobiboxFehler("warteschlange_doppelt")
            if len(self.eintraege) >= WARTESCHLANGE_MAX:
                raise TobiboxFehler("warteschlange_voll")
            store = hub.store
            eintrag = {
                "id": secrets.token_hex(6),
                "nr": store.warteschlange_nr + 1,
                "box": box,
                "ziel": ziel,
                "angelegt_von": nutzer.geloescht_von if nutzer else None,
                "angelegt_am": jetzt_iso(),
                "name": name_neu,
            }

            def anlegen() -> None:
                store.warteschlange.append(eintrag)
                store.warteschlange_nr = eintrag["nr"]

            await self._aendern(anlegen)
        hub.schutz.warteschlange_gebucht(nutzer)
        _LOGGER.info(
            "Warteschlange: %s legt an: Box %s, Ziel %s (Eintrag %s, %s)",
            self._benutzer(nutzer),
            box if box is not None else "irgendeine",
            self._ziel_text(ziel),
            eintrag["id"],
            eintrag["angelegt_am"],
        )
        objekt = self.eintrag_objekt(eintrag)
        hub.emit("warteschlange", "angelegt", {"eintrag": objekt})
        return {"eintrag": objekt, "gesamt": len(self.eintraege)}

    async def abbrechen(self, eintrag_id: str, nutzer: Nutzer | None = None) -> dict[str, Any]:
        """``warteschlange/abbrechen`` (Nr. 49): ``abgebrochen=false`` ist kein Fehler."""
        hub = self.hub
        hub.schutz.warteschlange_pruefen(nutzer)
        async with self.sperre:
            eintrag = next((e for e in self.eintraege if e["id"] == eintrag_id), None)
            if eintrag is not None:
                await self._aendern(lambda: hub.store.warteschlange.remove(next(e for e in hub.store.warteschlange if e["id"] == eintrag_id)))
        hub.schutz.warteschlange_gebucht(nutzer)
        if eintrag is None:
            return {"abgebrochen": False}
        _LOGGER.info(
            "Warteschlange: %s bricht ab: Box %s, Ziel %s (Eintrag %s)",
            self._benutzer(nutzer),
            eintrag["box"] if eintrag["box"] is not None else "irgendeine",
            self._ziel_text(eintrag["ziel"]),
            eintrag["id"],
        )
        hub.emit("warteschlange", "abgebrochen", {"id": eintrag["id"], "grund": "nutzer"})
        return {"abgebrochen": True}

    # --- Abgleich beim Auflegen (Regeln 1, 2, 6 bis 9) --------------------------------------------------------

    async def abgleich(self, box: str, uid: str) -> bool:
        """Eine Meldung ``unbekannt`` von ``box``. ``True``: erledigt (zugeordnet, oder die Kennung hat schon ein Ziel); die Box
        bekommt ``bekannt`` und die Kennung kommt **nicht** in „Neue Tobies“. ``False``: der normale Weg A gilt."""
        hub = self.hub
        if not self.eintraege or hub.store.zustand != ZUSTAND_OK:
            return False
        if hub.lernmodus.offener_vorgang(box) is not None:  # Regel 9: der Lernmodus hat Vorrang
            return False
        if any(e["ziel"]["typ"] != "aktion" for e in self.eintraege):
            try:
                await hub.medien._stelle_geprueft_sicher()  # vor der Sperre (Reihenfolge der Sperren)
            except TobiboxFehler:
                _LOGGER.warning("Warteschlange: Freigabe nicht erreichbar; die Meldung von %s läuft den normalen Weg", box)
                return False
        try:
            async with self.sperre:
                return await self._abgleich_unter_sperre(box, uid)
        except Exception:  # ein Fehler hier darf die Meldung nicht verschlucken: der normale Weg A gilt
            _LOGGER.warning("Warteschlange: Abgleich für %s auf %s fehlgeschlagen; die Meldung läuft den normalen Weg", uid, box, exc_info=True)
            return False

    async def _abgleich_unter_sperre(self, box: str, uid: str) -> bool:
        hub = self.hub
        while True:
            k = hub.store.konfig
            if k is not None and uid in k["zuordnungen"]:  # Regel 1 und 8: schon ein Ziel (zweite Box, doppelte Meldung)
                return True
            kandidaten = [e for e in self._reihenfolge() if e["box"] in (box, None)]
            if not kandidaten:
                return False
            eintrag = kandidaten[0]  # Regel 2: der älteste passende Eintrag
            if self._ziel_fehlt(eintrag["ziel"]):  # Regel 7a: verwerfen, nächsten prüfen
                await self._verwerfen(eintrag)
                continue
            return await self._zuordnen(box, uid, eintrag)

    async def _verwerfen(self, eintrag: dict[str, Any]) -> None:
        hub = self.hub
        await self._aendern(lambda: hub.store.warteschlange.remove(next(e for e in hub.store.warteschlange if e["id"] == eintrag["id"])))
        _LOGGER.info("Warteschlange: Eintrag %s verworfen, das Ziel fehlt (Box %s)", eintrag["id"], eintrag["box"] if eintrag["box"] is not None else "irgendeine")
        hub.emit("warteschlange", "abgebrochen", {"id": eintrag["id"], "grund": "ziel_fehlt"})

    async def _zuordnen(self, box: str, uid: str, eintrag: dict[str, Any]) -> bool:
        """Regel 7b bis 7f. Unter ``self.sperre``."""
        hub = self.hub
        ziel = eintrag["ziel"]
        eintrag_id = eintrag["id"]

        def setze(k: dict[str, Any]) -> None:
            if uid in k["zuordnungen"]:  # Regel 1, unter der Sperre der Konfiguration: „es gibt noch kein Ziel“
                raise _SchonZugeordnet
            neu: dict[str, Any] = {"ziel": dict(ziel)}
            if eintrag.get("name"):  # K7: der Name der Vormerkung wird der Name des Tobies
                neu["name"] = eintrag["name"]
            neu["angelegt_am"] = jetzt_iso()
            k["zuordnungen"][uid] = neu

        def austragen() -> None:
            hub.store.warteschlange[:] = [e for e in hub.store.warteschlange if e["id"] != eintrag_id]

        try:
            await hub.aendere_konfig(setze, austragen)
        except _SchonZugeordnet:
            return True
        except TobiboxFehler as err:  # ``konfig_nicht_bereit``, ``konfig_zu_gross``: nichts geändert, Eintrag bleibt (Regel 7f)
            _LOGGER.warning("Warteschlange: Zuordnung von %s nicht möglich (%s); die Meldung läuft den normalen Weg", uid, err.code)
            return False
        except Exception:
            _LOGGER.warning("Warteschlange: Zuordnung von %s fehlgeschlagen; die Meldung läuft den normalen Weg", uid, exc_info=True)
            return False
        hub.kennung_zugeordnet(uid)  # Regel 7c: stand sie schon in „Neue Tobies“, wird sie entfernt
        _LOGGER.info(
            "Warteschlange: Treffer: Tobie %s auf %s, Ziel %s (Eintrag %s, angelegt von %s)",
            uid,
            box,
            self._ziel_text(ziel),
            eintrag_id,
            (eintrag["angelegt_von"] or {}).get("name") or "ohne Benutzer",
        )
        serie_name, folge_anzeige, _vorhanden = self._ziel_info(ziel)
        hub.emit(
            "warteschlange",
            "abgearbeitet",
            {
                "id": eintrag_id,
                "uid": uid,
                "box": box,
                "ziel": copy.deepcopy(ziel),
                "serie_name": serie_name,
                "folge_anzeige": folge_anzeige,
                "angelegt_von": copy.deepcopy(eintrag["angelegt_von"]),
                "name": eintrag.get("name"),
            },
        )
        return True
