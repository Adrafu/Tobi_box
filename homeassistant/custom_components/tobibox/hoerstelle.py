"""Hörstelle (Weiterhören), je Benutzer in HA (Paket A4d; Vertrag W, Befehle 40 bis 42 und 14.6; Design 11.4.5).

* Store ``tobibox.hoerstellen`` (Version 1, ``.storage/``), gespeichert mit ``async_delay_save`` und **60 Sekunden Verzögerung**: im Speicher
  sofort, auf der Platte gesammelt (die Seite meldet alle 10 Sekunden; ohne Sammeln wären das viele Schreibvorgänge auf der SD-Karte).
  Beim Beenden der Integration schreibt ``Hub.async_stop`` zuletzt.
* Form: ``{ "<user_id>": { "<serie_id>": { "zeit", "folge", "folgen": { "<Name>": { "p", "d", "t", "fertig", "track" } } } } }``.
* **Kein Zugriff auf fremde Hörstellen:** jede Funktion hier bekommt die Benutzerkennung **von außen** (der Befehl nimmt sie aus der Verbindung,
  nie aus der Eingabe). Es gibt keine Funktion, die über Benutzer hinweg liest.
* Die Hörstelle der Box (``resume.json``) ist ein anderes System und wird hier nie berührt.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .const import (
    HOERSTELLE_DAUER_UNBEKANNT_MAX_S,
    HOERSTELLE_FERTIG_REST_S,
    HOERSTELLE_MAX_FOLGEN,
    HOERSTELLE_MAX_SERIEN,
    HOERSTELLE_SPEICHER_VERZOEGERUNG_S,
)
from .fehler import TobiboxFehler
from .util import jetzt_iso

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .hub import Hub

STORAGE_KEY = "tobibox.hoerstellen"
STORAGE_VERSION = 1


def _zahl(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _folge_ok(f: Any) -> bool:
    return (
        isinstance(f, dict)
        and _zahl(f.get("p"))
        and f["p"] >= 0
        and _zahl(f.get("d"))
        and f["d"] > 0
        and isinstance(f.get("t"), str)
        and isinstance(f.get("fertig"), bool)
        and isinstance(f.get("track", 0), int)
        and not isinstance(f.get("track", 0), bool)
    )


def _bereinige_form(roh: Any) -> dict[str, dict[str, dict[str, Any]]]:
    """Übernimmt nur, was die Form hat (eine kaputte Datei darf die Integration nicht aufhalten)."""
    aus: dict[str, dict[str, dict[str, Any]]] = {}
    if not isinstance(roh, dict):
        return aus
    for uid, serien in roh.items():
        if not isinstance(uid, str) or not isinstance(serien, dict):
            continue
        for sid, e in serien.items():
            if not isinstance(sid, str) or not isinstance(e, dict) or not isinstance(e.get("folgen"), dict):
                continue
            folgen = {n: f for n, f in e["folgen"].items() if isinstance(n, str) and _folge_ok(f)}
            if not folgen or not isinstance(e.get("zeit"), str):
                continue
            aus.setdefault(uid, {})[sid] = {"zeit": e["zeit"], "folge": e.get("folge") if e.get("folge") in folgen else max(folgen, key=lambda n: folgen[n]["t"]), "folgen": folgen}
    return aus


class Hoerstellen:
    """Der Store ``tobibox.hoerstellen`` und die Rechnung darum (``hub.hoerstellen``)."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self._store: Store[dict[str, Any]] = Store(hub.hass, STORAGE_VERSION, STORAGE_KEY)
        self.daten: dict[str, dict[str, dict[str, Any]]] = {}
        #: Ein Schreibvorgang ist schon geplant. ``Store.async_delay_save`` **verschiebt** den Zeitgeber bei jedem Aufruf (entprellt): bei
        #: dauerndem Hören käme die Platte nie dran. Darum wird nur beim ersten Aufruf geplant: höchstens ein Schreibvorgang je 60 Sekunden.
        self._geplant = False

    # --- Laden, Speichern, Aufräumen -------------------------------------------------------------------

    async def async_laden(self) -> None:
        self.daten = _bereinige_form(await self._store.async_load())

    def _speichern(self) -> None:
        if self._geplant:
            return
        self._geplant = True
        self._store.async_delay_save(self._daten_fuer_die_platte, HOERSTELLE_SPEICHER_VERZOEGERUNG_S)

    def _daten_fuer_die_platte(self) -> dict[str, Any]:
        self._geplant = False  # der Zeitgeber ist abgelaufen: die nächste Änderung plant den nächsten Schreibvorgang
        return self.daten

    async def async_speichern(self) -> None:
        """Sofort schreiben (Beenden der Integration)."""
        self._geplant = False
        await self._store.async_save(self.daten)

    async def bereinige_beim_start(self) -> None:
        """Einträge unbekannter Benutzer fallen weg; gelöschte Serien und nicht mehr vorhandene Folgen **nur nach gelungener Prüfung der
        Freigabe** (fehlt das NAS, wird nichts gelöscht)."""
        geaendert = False
        medien = self.hub.medien
        geprueft = medien.geprueft_am is not None
        for uid in list(self.daten):
            if await self.hub.hass.auth.async_get_user(uid) is None:
                del self.daten[uid]
                geaendert = True
                continue
            if not geprueft:
                continue
            serien = self.daten[uid]
            for sid in list(serien):
                info = medien.serien.get(sid)
                if info is None:
                    del serien[sid]
                    geaendert = True
                    continue
                folgen = serien[sid]["folgen"]
                for name in [n for n in folgen if n not in info.serie.folgen]:
                    del folgen[name]
                    geaendert = True
                if not folgen:
                    del serien[sid]
                    geaendert = True
                elif serien[sid]["folge"] not in folgen:
                    serien[sid]["folge"] = max(folgen, key=lambda n: folgen[n]["t"])
            if not serien:
                del self.daten[uid]
        if geaendert:
            self._speichern()

    # --- Schreiben (Befehl 41) -----------------------------------------------------------------------------

    def setze(
        self,
        nutzer_id: str,
        serie_id: str,
        folge: str,
        position_s: float,
        dauer_s: float,
        track: int | None = None,
        fertig: bool | None = None,
    ) -> None:
        """Prüft und merkt die Stelle (nur im Speicher; die Platte folgt nach 60 s). Fehler: ``serie_nicht_gefunden``,
        ``folge_nicht_gefunden``, ``invalid_format``."""
        medien = self.hub.medien
        info = medien.finde(serie_id)
        if folge not in info.serie.folgen:
            raise TobiboxFehler("folge_nicht_gefunden")
        medieninfo = self.hub.medieninfo
        tracks = next((o.get("tracks", 1) for o in info.folgen_objekte if o.get("name") == folge), 1)
        nr = 0 if track is None else track
        if nr >= max(int(tracks or 1), 1):
            raise TobiboxFehler("invalid_format")
        spuren = medieninfo.spuren_s(serie_id, folge)
        if spuren is not None and tracks and tracks > 1:
            bekannt = spuren[nr] if nr < len(spuren) else None
        elif tracks and tracks > 1:
            bekannt = None
        else:
            bekannt = medieninfo.dauer_s(serie_id, folge)
        if bekannt is None and dauer_s > HOERSTELLE_DAUER_UNBEKANNT_MAX_S:
            raise TobiboxFehler("invalid_format")
        # Ist die Dauer bekannt, bestimmt allein das Backend die Prüfung: der gesendete Wert wird ignoriert (Vertrag W, Nr. 41)
        dauer = float(bekannt) if bekannt is not None else float(dauer_s)
        if not 0 <= position_s <= dauer + HOERSTELLE_FERTIG_REST_S:
            raise TobiboxFehler("invalid_format")
        letzter_track = not (tracks and tracks > 1) or nr >= int(tracks) - 1
        ist_fertig = bool(fertig) or (letzter_track and position_s >= dauer - HOERSTELLE_FERTIG_REST_S)
        jetzt = jetzt_iso()
        serien = self.daten.setdefault(nutzer_id, {})
        e = serien.setdefault(serie_id, {"zeit": jetzt, "folge": folge, "folgen": {}})
        e["zeit"] = jetzt
        e["folge"] = folge
        e["folgen"][folge] = {"p": int(round(position_s)), "d": int(round(dauer)) or 1, "t": jetzt, "fertig": ist_fertig, "track": nr}
        # Obergrenzen: die ältesten fallen weg (die gerade gesetzte nie)
        if len(e["folgen"]) > HOERSTELLE_MAX_FOLGEN:
            for name in sorted((n for n in e["folgen"] if n != folge), key=lambda n: e["folgen"][n]["t"])[: len(e["folgen"]) - HOERSTELLE_MAX_FOLGEN]:
                del e["folgen"][name]
        if len(serien) > HOERSTELLE_MAX_SERIEN:
            for sid in sorted((s for s in serien if s != serie_id), key=lambda s: serien[s]["zeit"])[: len(serien) - HOERSTELLE_MAX_SERIEN]:
                del serien[sid]
        self._speichern()

    # --- Lesen (Befehle 40 und 42, Kurzform, Folge-Objekt) --------------------------------------------------

    def _eintrag(self, nutzer_id: str | None, serie_id: str) -> dict[str, Any] | None:
        if not nutzer_id:
            return None
        return (self.daten.get(nutzer_id) or {}).get(serie_id)

    def _vorhandene(self, serie_id: str, e: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Die Folgen des Eintrags, die es in der Serie (noch) gibt."""
        info = self.hub.medien.serien.get(serie_id)
        if info is None:
            return {}
        return {n: f for n, f in e["folgen"].items() if n in info.serie.folgen}

    def _masse(self, serie_id: str, folge: str, f: dict[str, Any]) -> tuple[float, float]:
        """``(Stelle, Länge)`` in Sekunden: bei Ordner-Folgen mit bekannten Spuren über die ganze Folge, sonst im Track."""
        d = float(f["d"])
        p = min(float(f["p"]), d)
        spuren = self.hub.medieninfo.spuren_s(serie_id, folge)
        gesamt = self.hub.medieninfo.dauer_s(serie_id, folge)
        track = f.get("track", 0)
        if spuren and gesamt and len(spuren) > 1 and track < len(spuren):
            return float(sum(spuren[:track])) + min(p, float(spuren[track])), float(gesamt)
        return p, d

    def _anteil(self, serie_id: str, folge: str, f: dict[str, Any]) -> tuple[float, int]:
        if f["fertig"]:
            return 1.0, 0
        p, gesamt = self._masse(serie_id, folge, f)
        anteil = 0.0 if gesamt <= 0 else min(max(p / gesamt, 0.0), 1.0)
        return round(anteil, 4), max(0, int(round(gesamt - p)))

    def _weiter_name(self, e: dict[str, Any], vorhanden: dict[str, dict[str, Any]]) -> str | None:
        if e.get("folge") in vorhanden:
            return e["folge"]
        return max(vorhanden, key=lambda n: vorhanden[n]["t"]) if vorhanden else None

    def _weiter(self, serie_id: str, e: dict[str, Any], vorhanden: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        name = self._weiter_name(e, vorhanden)
        if name is None:
            return None
        f = vorhanden[name]
        anteil, rest = self._anteil(serie_id, name, f)
        return {"folge": name, "position_s": f["p"], "track": f.get("track", 0), "anteil": anteil, "rest_s": rest, "zeit": f["t"]}

    def hole(self, nutzer_id: str, serie_id: str) -> dict[str, Any]:
        """Befehl 40: ``weiter`` und ``folgen`` **des Anfragenden**."""
        self.hub.medien.finde(serie_id)
        e = self._eintrag(nutzer_id, serie_id)
        if e is None:
            return {"weiter": None, "folgen": {}}
        vorhanden = self._vorhandene(serie_id, e)
        return {
            "weiter": self._weiter(serie_id, e, vorhanden),
            "folgen": {n: {"position_s": f["p"], "dauer_s": f["d"], "fertig": f["fertig"], "zeit": f["t"]} for n, f in vorhanden.items()},
        }

    def liste(self, nutzer_id: str, limit: int) -> list[dict[str, Any]]:
        """Befehl 42: angefangene, nicht fertige Einträge des Anfragenden, zuletzt angehört zuerst (je Serie die zuletzt gehörte Folge)."""
        zeilen: list[dict[str, Any]] = []
        for sid, e in (self.daten.get(nutzer_id) or {}).items():
            info = self.hub.medien.serien.get(sid)
            if info is None:
                continue
            vorhanden = self._vorhandene(sid, e)
            weiter = self._weiter(sid, e, vorhanden)
            if weiter is None or vorhanden[weiter["folge"]]["fertig"]:
                continue
            zeilen.append({"serie_id": sid, "name": info.serie.name, **weiter})
        zeilen.sort(key=lambda z: z["zeit"], reverse=True)
        return zeilen[:limit]

    def kurz(self, nutzer_id: str | None, serie_id: str) -> dict[str, Any] | None:
        """Feld ``hoerstelle`` der Serie-Kurzform: nur wenn der Anfragende angefangen hat (``anteil``, ``rest_s``, ``zeit``, ``folge``)."""
        e = self._eintrag(nutzer_id, serie_id)
        if e is None:
            return None
        weiter = self._weiter(serie_id, e, self._vorhandene(serie_id, e))
        if weiter is None:
            return None
        return {"anteil": weiter["anteil"], "rest_s": weiter["rest_s"], "zeit": weiter["zeit"], "folge": weiter["folge"]}

    def je_folge(self, nutzer_id: str | None, serie_id: str) -> dict[str, dict[str, Any]]:
        """Feld ``hoerstelle`` je Folge von ``serie/get``: ``position_s``, ``fertig`` (nur des Anfragenden)."""
        e = self._eintrag(nutzer_id, serie_id)
        if e is None:
            return {}
        return {n: {"position_s": f["p"], "fertig": f["fertig"]} for n, f in self._vorhandene(serie_id, e).items()}

    def zeiten(self, nutzer_id: str | None) -> dict[str, str]:
        """Serien-ID -> Zeit der letzten Wiedergabe des Anfragenden (für die Sortierung ``angehoert``)."""
        if not nutzer_id:
            return {}
        return {sid: e["zeit"] for sid, e in (self.daten.get(nutzer_id) or {}).items()}
