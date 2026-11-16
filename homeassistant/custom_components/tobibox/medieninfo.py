"""Store ``tobibox.medieninfo`` (``data-model.md``, Abschnitt 5a; Vertrag W, 14.7).

Abgeleitete Werte, die ein Hintergrundlauf berechnet und jederzeit neu berechnen kann. Sie liegen **nicht** in ``serie.json``
(ein Hintergrundlauf darf den ``stand`` einer Serie nie ändern und keine Datei auf das NAS schreiben, die die Boxen mitsynchronisieren),
sondern im HA-``Store`` (``.storage/``, gespeichert mit ``async_delay_save``). Schlüssel ``serie_id``, dann das Feld.

Geschrieben werden ``<serie_id>.cover_suche`` (die Marke „schon gesucht“, A4) und ``<serie_id>.folgen.<Folge>.dauer_s`` / ``.spuren_s``
(A3b, A-2) sowie ``.kapitel``, ``.codecs`` und ``.info_v`` (A3b3, A-3: ``info_v`` ist der Stand der Messung, damit der Bestand mit Dauer, aber ohne
Kapitel und Codecs im Hintergrund noch einmal gelesen wird) und ``.hoerkopie`` (A3c: der Zustand je Track, siehe ``hoerkopie.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .const import DAUER_DECKEL_S, KAPITEL_MAX, KAPITEL_ROH_MAX, MEDIENINFO_VERSION
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

    # --- Dauer und Spuren (Vertrag W, 14.7; ``data-model.md``, 5a) ---------------------------------------

    def _folge(self, serie_id: str, folge: str) -> dict[str, Any] | None:
        folgen = (self.daten.get(serie_id) or {}).get("folgen")
        eintrag = folgen.get(folge) if isinstance(folgen, dict) else None
        return eintrag if isinstance(eintrag, dict) else None

    def dauer_s(self, serie_id: str, folge: str) -> int | None:
        """Die gespeicherte Dauer der Folge in ganzen Sekunden; ``None``, solange unbekannt (oder über dem Dauerdeckel)."""
        wert = (self._folge(serie_id, folge) or {}).get("dauer_s")
        return wert if isinstance(wert, int) and not isinstance(wert, bool) and 0 < wert <= DAUER_DECKEL_S else None

    def spuren_s(self, serie_id: str, folge: str) -> list[int] | None:
        """Die Länge jedes Tracks einer Ordner-Folge (in Folgenreihenfolge); ``None`` bei Einzeldateien oder unbekannt."""
        wert = (self._folge(serie_id, folge) or {}).get("spuren_s")
        if isinstance(wert, list) and wert and all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in wert):
            return list(wert)
        return None

    def setze_dauer(self, serie_id: str, folge: str, dauer_s: float, spuren_s: list[float] | None = None) -> bool:
        """Speichert Dauer (ganze Sekunden) und bei Ordner-Folgen die Spuren. **Über ``DAUER_DECKEL_S`` wird nichts gespeichert**
        (Rückgabe ``False``); ebenso nichts bei Dauer 0 oder unsinnigen Werten."""
        try:
            gesamt = int(round(dauer_s))
            spuren = None if spuren_s is None else [int(round(x)) for x in spuren_s]
        except (TypeError, ValueError, OverflowError):
            return False
        if gesamt <= 0 or gesamt > DAUER_DECKEL_S or (spuren is not None and (not spuren or any(x < 0 or x > DAUER_DECKEL_S for x in spuren))):
            return False
        eintrag = self.daten.setdefault(serie_id, {}).setdefault("folgen", {}).setdefault(folge, {})
        vorher = dict(eintrag)
        eintrag["dauer_s"] = gesamt
        if spuren is None:
            eintrag.pop("spuren_s", None)
        else:
            eintrag["spuren_s"] = spuren
        if eintrag != vorher:
            self._speichern()
        return True

    def hat_info(self, serie_id: str, folge: str) -> bool:
        """Dauer **und** der Stand der Messung (``info_v``) sind da: sonst holt der Hintergrundlauf die Folge nach (Vertrag W, 14.7)."""
        wert = (self._folge(serie_id, folge) or {}).get("info_v")
        return self.hat_dauer(serie_id, folge) and isinstance(wert, int) and not isinstance(wert, bool) and wert >= MEDIENINFO_VERSION

    def setze_info(
        self,
        serie_id: str,
        folge: str,
        dauer_s: float,
        spuren_s: list[float] | None = None,
        kapitel: list[dict[str, Any]] | None = None,
        codecs: list[str | None] | None = None,
    ) -> bool:
        """Wie ``setze_dauer``, dazu Kapitel und Codecs (je Track) und der Stand der Messung. Über dem Dauerdeckel wird **nichts** gespeichert
        (``False``). Kapitel und Codecs werden beim Lesen noch einmal geprüft."""
        if not self.setze_dauer(serie_id, folge, dauer_s, spuren_s):
            return False
        eintrag = self.daten[serie_id]["folgen"][folge]
        vorher = dict(eintrag)
        sauber = _kapitel_pruefen(kapitel)
        if sauber:
            eintrag["kapitel"] = sauber
        else:
            eintrag.pop("kapitel", None)
        if isinstance(codecs, list) and codecs and all(c is None or isinstance(c, str) for c in codecs):
            eintrag["codecs"] = [(c or "").lower() for c in codecs]  # ``""``: der Codec war unbekannt (zählt wie „alles Unbekannte“)
        else:
            eintrag.pop("codecs", None)
        eintrag["info_v"] = MEDIENINFO_VERSION
        if eintrag != vorher:
            self._speichern()
        return True

    def kapitel(self, serie_id: str, folge: str) -> list[dict[str, Any]] | None:
        """Die Kapitel der Folge (Vertrag W, 14.2); ``None``, wenn es keine Liste gibt (weniger als zwei, unbekannt)."""
        sauber = _kapitel_pruefen((self._folge(serie_id, folge) or {}).get("kapitel"))
        return [dict(k) for k in sauber] if len(sauber) >= 2 else None

    def kapitel_anzahl(self, serie_id: str, folgen: list[str]) -> int:
        """Summe der Kapitel aller Folgen (``kapitel_anzahl`` der Kurzform); 0 = keine Liste."""
        return sum(len(self.kapitel(serie_id, f) or ()) for f in folgen)

    def codecs(self, serie_id: str, folge: str) -> list[str] | None:
        """Der Codec je Track (in Folgenreihenfolge); ``None``, solange unbekannt."""
        wert = (self._folge(serie_id, folge) or {}).get("codecs")
        return list(wert) if isinstance(wert, list) and wert and all(isinstance(c, str) for c in wert) else None

    # --- Hörkopie: Zustand je Track (``hoerkopie.py``) ----------------------------------------------------

    def hoerkopie_tracks(self, serie_id: str, folge: str) -> dict[str, dict[str, Any]]:
        """``{"<track>": {"zustand": "fertig"|"fehler", "kennung", "zeit", "grund"?}}``; nur gültige Einträge."""
        roh = (self._folge(serie_id, folge) or {}).get("hoerkopie")
        tracks = roh.get("tracks") if isinstance(roh, dict) else None
        if not isinstance(tracks, dict):
            return {}
        return {
            k: v
            for k, v in tracks.items()
            if isinstance(k, str) and k.isdigit() and isinstance(v, dict) and v.get("zustand") in ("fertig", "fehler") and isinstance(v.get("kennung"), str)
        }

    def setze_hoerkopie(self, serie_id: str, folge: str, track: int, zustand: str, kennung: str, grund: str | None = None) -> None:
        if zustand not in ("fertig", "fehler"):
            raise ValueError(zustand)
        eintrag = self.daten.setdefault(serie_id, {}).setdefault("folgen", {}).setdefault(folge, {})
        tracks = eintrag.setdefault("hoerkopie", {}).setdefault("tracks", {})
        neu: dict[str, Any] = {"zustand": zustand, "kennung": kennung, "zeit": jetzt_iso()}
        if grund:
            neu["grund"] = grund
        tracks[str(track)] = neu
        self._speichern()

    def loesche_hoerkopie(self, serie_id: str, folge: str, track: int | None = None) -> None:
        """Vergisst den Zustand (``track=None``: aller Tracks der Folge). Die Dateien räumt ``hoerkopie.py`` weg."""
        eintrag = self._folge(serie_id, folge)
        roh = eintrag.get("hoerkopie") if eintrag is not None else None
        if eintrag is None or not isinstance(roh, dict):
            return
        tracks = roh.get("tracks")
        if track is not None and isinstance(tracks, dict):
            tracks.pop(str(track), None)
        if track is None or not tracks:
            eintrag.pop("hoerkopie", None)
        if not eintrag:
            self.loesche_folge(serie_id, folge)  # nichts mehr übrig (speichert selbst)
        else:
            self._speichern()

    def hoerkopie_folgen(self) -> list[tuple[str, str]]:
        """Alle ``(serie_id, folge)`` mit gespeichertem Zustand der Hörkopie."""
        aus = []
        for sid, e in self.daten.items():
            folgen = e.get("folgen")
            if isinstance(folgen, dict):
                aus += [(sid, f) for f, v in folgen.items() if isinstance(v, dict) and isinstance(v.get("hoerkopie"), dict)]
        return aus

    def hoerkopie_kennungen(self, serie_id: str) -> set[str]:
        """Alle Kennungen, die der Store zu dieser Serie kennt (für das Aufräumen verwaister Dateien)."""
        aus: set[str] = set()
        folgen = (self.daten.get(serie_id) or {}).get("folgen")
        for f in folgen if isinstance(folgen, dict) else ():
            aus |= {v["kennung"] for v in self.hoerkopie_tracks(serie_id, f).values()}
        return aus

    def serie_dauer(self, serie_id: str, folgen: list[str]) -> int | None:
        """Summe der **bekannten** Dauern der Folgen; ``None``, wenn keine bekannt ist (Vertrag W, 14.2: ``dauer_s`` der Kurzform)."""
        bekannt = [d for d in (self.dauer_s(serie_id, f) for f in folgen) if d is not None]
        return sum(bekannt) if bekannt else None

    def hat_dauer(self, serie_id: str, folge: str) -> bool:
        return self.dauer_s(serie_id, folge) is not None

    def loesche_folge(self, serie_id: str, folge: str) -> None:
        eintrag = self.daten.get(serie_id)
        folgen = eintrag.get("folgen") if eintrag else None
        if isinstance(folgen, dict) and folgen.pop(folge, None) is not None:
            self._aufraeumen(serie_id)
            self._speichern()

    def loesche_serie_folgen(self, serie_id: str) -> None:
        """Entfernt alle Werte der Folgen einer Serie (die Marke ``cover_suche`` bleibt)."""
        eintrag = self.daten.get(serie_id)
        if eintrag is not None and eintrag.pop("folgen", None) is not None:
            self._aufraeumen(serie_id)
            self._speichern()

    def uebertrage_folge(self, quelle_id: str, folge: str, ziel_id: str, ziel_folge: str) -> None:
        """Ein Verschieben von Folgen zwischen Serien nimmt die Dauer mit (sonst käme sie erst beim nächsten Nachholen wieder)."""
        eintrag = self._folge(quelle_id, folge)
        if eintrag is None:
            return
        kopie = dict(eintrag)
        kopie.pop("hoerkopie", None)  # die Kopie hängt an ``serie_id`` und Kennung: unter der neuen ID wird sie bei Bedarf neu gemacht
        self.daten.setdefault(ziel_id, {}).setdefault("folgen", {})[ziel_folge] = kopie
        self.loesche_folge(quelle_id, folge)
        self._speichern()

    def bereinige(self, bekannt: dict[str, list[str]]) -> int:
        """Entfernt Werte zu Serien und Folgen, die es nicht mehr gibt (``bekannt``: Serien-ID -> Folgen). Gibt die Zahl der entfernten
        Folgen zurück. Der Aufrufer ruft das **nur nach einer gelungenen Prüfung der Freigabe** auf (nie, wenn das NAS fehlt)."""
        entfernt = 0
        for serie_id in list(self.daten):
            eintrag = self.daten[serie_id]
            folgen = eintrag.get("folgen")
            if not isinstance(folgen, dict):
                continue
            vorhanden = set(bekannt.get(serie_id, ()))
            for name in [n for n in folgen if n not in vorhanden]:
                del folgen[name]
                entfernt += 1
            if not folgen:
                eintrag.pop("folgen", None)
            if not eintrag:
                self.daten.pop(serie_id, None)
        if entfernt:
            self._speichern()
        return entfernt

    def _aufraeumen(self, serie_id: str) -> None:
        eintrag = self.daten.get(serie_id)
        if eintrag is None:
            return
        if not eintrag.get("folgen"):
            eintrag.pop("folgen", None)
        if not eintrag:
            self.daten.pop(serie_id, None)


def _kapitel_pruefen(roh: Any) -> list[dict[str, Any]]:
    """Gültige Kapitel: ``titel`` (Text), ``start_s`` (Zahl ab 0, streng aufsteigend), optional ``track`` (ganze Zahl ab 0); höchstens ``KAPITEL_MAX``."""
    aus: list[dict[str, Any]] = []
    if not isinstance(roh, list):
        return aus
    letzter = -1.0
    for k in roh:
        if not isinstance(k, dict) or not isinstance(k.get("titel"), str):
            continue
        start = k.get("start_s")
        if not isinstance(start, (int, float)) or isinstance(start, bool) or not 0 <= start <= DAUER_DECKEL_S or start <= letzter:
            continue
        neu: dict[str, Any] = {"titel": k["titel"][:KAPITEL_ROH_MAX], "start_s": start}
        track = k.get("track")
        if isinstance(track, int) and not isinstance(track, bool) and track >= 0:
            neu["track"] = track
        aus.append(neu)
        letzter = start
        if len(aus) >= KAPITEL_MAX:
            break
    return aus
