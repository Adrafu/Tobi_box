"""Reinhören als Sitzungen (Stufe B, Paket B2; Vertrag W, 15.1 und 15.3; Design Abschnitt 5).

Befehl 41 ``hoerstelle/set`` ruft ``Reinhoeren.melde``. Je (Benutzer, ``spieler``) führt HA eine offene Sitzung **im Arbeitsspeicher**
(höchstens ``REINHOEREN_SPIELER_MAX`` je Benutzer). Die Hörzeit kommt aus dem Fortschritt der **ungerundeten** Position:

* Zuwachs ``dp`` seit dem letzten Aufruf zählt, wenn ``0 < dp``; er wird auf ``2 × dt + 2`` gekappt (``dt`` Monotonzeit). War beim vorigen Aufruf
  ``spielt`` wahr und ist ``dt`` über 30 s (die Seite war eingefroren, der Ton lief), gilt die Kappung ``1,5 × dt + 2``.
* Bei ``dp ≤ 0`` (Rücksprung) wird die Basislinie neu gesetzt; ebenso bei Wechsel von Track (nur, wenn die Spuren nicht bekannt sind, sonst
  läuft die Position über die ganze Folge) und von Folge.
* Es zählt nur Fortschritt seit einem Aufruf mit ``spielt`` wahr (Spulen in der Pause zählt nicht).
* Ende: ``fertig`` -> ``ende_der_folge``; andere Folge im selben ``spieler`` -> ``wechsel``; 30 Minuten ohne Fortschritt -> ``pause``;
  Beenden von HA -> ``dienst_ende``. Alle 5 Minuten schreibt HA offene Sitzungen als ``teilweise``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.event import async_track_time_interval

from .const import (
    GEHOERT_PAUSE_MAX_S,
    REINHOEREN_SCHREIBEN_S,
    REINHOEREN_SPIELER_MAX,
    REINHOEREN_TAKT_S,
)
from .gehoert import Zeile
from .util import jetzt, neue_uuid

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

#: ab dieser Zeit zwischen zwei Aufrufen gilt (bei ``spielt``) die Kappung für eine eingefrorene Seite
EINGEFROREN_AB_S = 30


@dataclass
class Lauf:
    """Eine offene Reinhör-Sitzung."""

    sitzung: str
    nutzer_id: str
    serie: str
    folge: str
    folge_dauer_s: int | None
    beginn: int
    #: Basislinie: ``(Track oder None, Position)``
    basis: tuple[int | None, float]
    letzter_aufruf: float
    spielt: bool
    gehoert: float = 0.0
    #: Monotonzeit und Wanduhr des letzten Fortschritts (Beginn zählt als Fortschritt)
    fortschritt_mono: float = 0.0
    fortschritt_wall: int = 0
    #: Stand der letzten ``teilweise``-Zeile: Monotonzeit, ``None`` = noch keine geschrieben
    geschrieben_mono: float | None = None
    geschrieben_gehoert: int = -1

    def hoerzeit(self) -> int:
        return int(self.gehoert + 0.5)


class Reinhoeren:
    """``hub.reinhoeren``."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.offen: dict[tuple[str, str], Lauf] = {}
        #: Uhren (in Tests ersetzbar): Monotonzeit und Wanduhr (UTC-Sekunden)
        self.mono = time.monotonic
        self.wall = lambda: int(jetzt().timestamp())

    def start(self) -> None:
        self.hub._abmelden.append(async_track_time_interval(self.hub.hass, self._takt, timedelta(seconds=REINHOEREN_TAKT_S)))

    # --- Aufruf von Befehl 41 ------------------------------------------------------------------------------

    def _ort(self, serie_id: str, folge: str, track: int | None, position_s: float) -> tuple[int | None, float]:
        """``(Schlüssel des Tracks, Position)``: bei Ordner-Folgen mit bekannten Spuren die Sekunde der **ganzen Folge** (Schlüssel ``None``),
        sonst die Position im Track (Schlüssel = Track, ein Wechsel setzt die Basislinie neu)."""
        info = self.hub.medien.serien.get(serie_id)
        tracks = 1
        if info is not None:
            tracks = int(next((o.get("tracks", 1) for o in info.folgen_objekte if o.get("name") == folge), 1) or 1)
        nr = track or 0
        if tracks > 1:
            spuren = self.hub.medieninfo.spuren_s(serie_id, folge)
            if spuren is not None and len(spuren) >= tracks:
                return None, float(sum(spuren[:nr])) + position_s
            return nr, position_s
        return None, position_s

    def _dauer(self, serie_id: str, folge: str, dauer_s: float, tracks_mehr: bool) -> int | None:
        bekannt = self.hub.medieninfo.dauer_s(serie_id, folge)
        if bekannt:
            return bekannt
        if tracks_mehr:
            return None
        return int(round(dauer_s)) if dauer_s and dauer_s > 0 else None

    async def melde(
        self,
        nutzer_id: str,
        spieler: str | None,
        serie_id: str,
        folge: str,
        position_s: float,
        dauer_s: float,
        track: int | None = None,
        spielt: bool | None = None,
        fertig: bool = False,
    ) -> None:
        """Verbucht einen Aufruf von ``hoerstelle/set`` (Serie und Folge sind schon geprüft). Schreibt nur beim Schließen einer Sitzung."""
        if not self.hub.gehoert.verfuegbar:
            return
        jetzt_m = self.mono()
        wall = self.wall()
        schluessel = (nutzer_id, spieler or "")
        ort_schluessel, pos = self._ort(serie_id, folge, track, position_s)
        spielt_jetzt = True if spielt is None else bool(spielt)  # B2-OFFEN: alte Seite ohne ``spielt``: gilt als spielend
        zu_schreiben: list[Zeile] = []
        lauf = self.offen.get(schluessel)
        if lauf is not None and (lauf.serie != serie_id or lauf.folge != folge):
            zu_schreiben += self._schliesse(schluessel, "wechsel")
            lauf = None
        if lauf is not None and jetzt_m - lauf.fortschritt_mono > GEHOERT_PAUSE_MAX_S:
            # Die Aufräumschleife läuft nur je Minute; ein Aufruf nach mehr als 30 Minuten ohne Fortschritt beginnt in jedem Fall eine neue Sitzung.
            zu_schreiben += self._schliesse(schluessel, "pause")
            lauf = None
        if lauf is None:
            if sum(1 for k in self.offen if k[0] == nutzer_id) >= REINHOEREN_SPIELER_MAX:
                aelteste = min((k for k in self.offen if k[0] == nutzer_id), key=lambda k: self.offen[k].letzter_aufruf)
                zu_schreiben += self._schliesse(aelteste, "wechsel")
            dauer = self._dauer(serie_id, folge, dauer_s, ort_schluessel is not None or self._ist_ordner(serie_id, folge))
            lauf = Lauf(
                sitzung=neue_uuid(), nutzer_id=nutzer_id, serie=serie_id, folge=folge, folge_dauer_s=dauer, beginn=wall,
                basis=(ort_schluessel, pos), letzter_aufruf=jetzt_m, spielt=spielt_jetzt, fortschritt_mono=jetzt_m, fortschritt_wall=wall,
            )
            self.offen[schluessel] = lauf
        else:
            dt = jetzt_m - lauf.letzter_aufruf
            alt_schluessel, alt_pos = lauf.basis
            dp = pos - alt_pos
            if alt_schluessel != ort_schluessel or dp <= 0:
                pass  # Basislinie neu (Track-Wechsel, Rücksprung, Wiederholung): nichts zählt
            elif lauf.spielt:
                kappung = 1.5 * dt + 2 if dt > EINGEFROREN_AB_S else 2 * dt + 2
                zuwachs = min(dp, kappung)
                lauf.gehoert += zuwachs
                lauf.fortschritt_mono = jetzt_m
                lauf.fortschritt_wall = wall
            lauf.basis = (ort_schluessel, pos)
            lauf.letzter_aufruf = jetzt_m
            lauf.spielt = spielt_jetzt
        if fertig:
            zu_schreiben += self._schliesse(schluessel, "ende_der_folge")
        if zu_schreiben:
            await self.hub.gehoert.nimm_zeilen_auf(f"benutzer:{nutzer_id}", zu_schreiben)

    def _ist_ordner(self, serie_id: str, folge: str) -> bool:
        info = self.hub.medien.serien.get(serie_id)
        return info is not None and any(o.get("name") == folge and int(o.get("tracks") or 1) > 1 for o in info.folgen_objekte)

    # --- Schließen und Schreiben -------------------------------------------------------------------------------

    @staticmethod
    def _zeile(lauf: Lauf, ende: str) -> Zeile | None:
        """Die Zeile einer Sitzung; ``None`` bei Hörzeit 0 (wird verworfen)."""
        g = lauf.hoerzeit()
        if g < 1:
            return None
        return Zeile(
            lauf.sitzung, lauf.serie, lauf.folge, lauf.folge_dauer_s, lauf.beginn, max(lauf.fortschritt_wall, lauf.beginn), "sicher", g, ende, None
        )

    def _schliesse(self, schluessel: tuple[str, str], ende: str) -> list[Zeile]:
        lauf = self.offen.pop(schluessel, None)
        if lauf is None:
            return []
        z = self._zeile(lauf, ende)
        return [z] if z is not None else []

    async def _takt(self, _now: Any) -> None:
        await self.takt()

    async def takt(self) -> None:
        """Je Minute: Sitzungen ohne Fortschritt seit 30 Minuten als ``pause`` schließen; offene alle 5 Minuten als ``teilweise`` schreiben."""
        if not self.hub.gehoert.verfuegbar:
            return
        jetzt_m = self.mono()
        je_nutzer: dict[str, list[Zeile]] = {}
        for k in list(self.offen):
            lauf = self.offen[k]
            if jetzt_m - lauf.fortschritt_mono > GEHOERT_PAUSE_MAX_S:
                je_nutzer.setdefault(lauf.nutzer_id, []).extend(self._schliesse(k, "pause"))
            elif lauf.hoerzeit() >= 1 and lauf.hoerzeit() != lauf.geschrieben_gehoert and (
                lauf.geschrieben_mono is None or jetzt_m - lauf.geschrieben_mono >= REINHOEREN_SCHREIBEN_S
            ):
                z = self._zeile(lauf, "teilweise")
                if z is not None:
                    je_nutzer.setdefault(lauf.nutzer_id, []).append(z)
                    lauf.geschrieben_mono = jetzt_m
                    lauf.geschrieben_gehoert = lauf.hoerzeit()
        await self._schreibe(je_nutzer)

    async def _schreibe(self, je_nutzer: dict[str, list[Zeile]]) -> None:
        """Eine Ausnahme bei einem Benutzer darf die anderen nicht aufhalten (Protokoll)."""
        for nutzer_id, zeilen in je_nutzer.items():
            try:
                await self.hub.gehoert.nimm_zeilen_auf(f"benutzer:{nutzer_id}", zeilen)
            except Exception:
                _LOGGER.exception("Reinhören: Sitzungen von Benutzer %s nicht geschrieben", nutzer_id)

    def schreibe_um(self, zuordnung: dict[tuple[str, str], tuple[str, str]]) -> None:
        """Verschieben und Zusammenführen: offene Sitzungen ziehen mit."""
        for lauf in self.offen.values():
            neu = zuordnung.get((lauf.serie, lauf.folge))
            if neu is not None:
                lauf.serie, lauf.folge = neu

    async def schliesse_alle(self) -> None:
        """HA fährt herunter: alle offenen Sitzungen enden als ``dienst_ende``."""
        je_nutzer: dict[str, list[Zeile]] = {}
        for k in list(self.offen):
            nutzer_id = self.offen[k].nutzer_id
            je_nutzer.setdefault(nutzer_id, []).extend(self._schliesse(k, "dienst_ende"))
        await self._schreibe(je_nutzer)
