"""Statussammler der Stufe 2 (``core-interface.md``, Abschnitt 12; ``mqtt-v1.md``, 3.3).

Kein Teilautomat und kein Teil des Kerns: Er hält nur die zuletzt gesehenen Werte. ``app`` füttert ihn als
Beobachter mit Kopien der Ereignisse und der ausgegebenen Befehle. In Stufe 2 gibt es keinen Broker; der
Status geht an ``tobibox status`` (über ``sim.sock``) und an die Status-Admin-Karte (Prüfpunkt Leser,
Netz). Stufe 3a zieht diese Klasse in das Modul ``ha`` und veröffentlicht den Status per MQTT.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from . import __version__
from . import events as ev
from .events import Jetzt
from .outbox import zeitstempel
from .protocol import PROTO_UNTERSTUETZT
from .stromwert import StromQuellen
from .sync import SyncFortschritt

LESER_FEHLER_FENSTER_S = 10.0  # 12.2: ein ``LeserFehler`` mit schwere ``fehler`` zählt so lange
_GETRENNT = ("getrennt", "kein_herzschlag", "hello_timeout")


class Statussammler:
    def __init__(self, *, leser_simulation: bool = False) -> None:
        self.leser_simulation = leser_simulation  # 12.2: Ereignisse des Lesers kommen aus ``sim``
        self.hallo: ev.LeserHallo | None = None
        self.ausfall: str | None = None  # Grund des letzten ``LeserAlarm`` seit dem letzten gültigen ``LeserHallo``
        self.fehler_mono: float | None = None  # Zeitpunkt des letzten ``LeserFehler`` mit schwere ``fehler``
        self.netz = "offline"
        self.ha_verbunden = False
        self.akku: int | None = None
        self.strom_quellen = StromQuellen()  # Strom am Eingang: ``pisugar-server`` und Leser, bei Widerspruch der Leser (Ein/Aus, 10.11.)
        self.zustand: ev.ZustandMelden | None = None
        self.konfig: ev.Konfig | None = None
        self.letzter_fehler: dict[str, Any] | None = None
        # 12.1: ``sync`` aus ``SyncGestartet`` / ``SyncFertig`` / ``SyncAbgebrochen``, ``update`` aus ``UpdateGestartet`` / ``SelbsttestErgebnis``
        self.sync: dict[str, Any] = {"zustand": "idle", "letzter_ende": None, "ergebnis": None, "grund": None, "neu": 0}
        self.update: dict[str, Any] = {"zustand": "ok", "version": __version__, "grund": None}
        #: Zwischenstand eines laufenden Syncs (``SyncFortschritt`` aus ``sync``); **kein** Feld des Status-JSON (``mqtt-v1.md`` 3.3
        #: bleibt Version 1). Nur für ``tobibox status`` und die Simulations-Oberfläche. ``None``, wenn kein Sync läuft.
        self.sync_fortschritt: dict[str, int] | None = None
        self.jetzt: Jetzt | None = None

    @property
    def lader(self) -> bool | None:
        """Strom am Eingang der Box, aus jeder Quelle (Ein/Aus, 10.11.); ``None`` bis eine Quelle einen Wert geliefert hat."""
        return self.strom_quellen.wert

    # -- füttern ---------------------------------------------------------------------

    def beobachte(self, e: ev.Ereignis, jetzt: Jetzt) -> None:
        self.jetzt = jetzt
        if isinstance(e, ev.LeserHallo):
            self.hallo, self.ausfall = e, None
        elif isinstance(e, ev.LeserAlarm):
            self.ausfall = e.grund
            self.hallo = None  # Firmware unbekannt (``null``), bis ein neues ``LeserHallo`` kommt (12.1)
        elif isinstance(e, ev.LeserFehler) and e.schwere == "fehler":
            self.fehler_mono = jetzt.mono
        elif isinstance(e, ev.NetzKlasse):
            self.netz = e.klasse
        elif isinstance(e, ev.HaVerbindung):
            self.ha_verbunden = e.ok
        elif isinstance(e, ev.AkkuStand):
            self.akku = e.prozent
        elif isinstance(e, ev.LaderGeaendert):
            self.strom_quellen = self.strom_quellen.mit(e)
        elif isinstance(e, ev.KonfigGeladen):
            self.konfig = e.konfig
        elif isinstance(e, ev.SyncGestartet):
            self.sync = {**self.sync, "zustand": "laeuft"}
            self.sync_fortschritt = None
        elif isinstance(e, SyncFortschritt):
            self.sync_fortschritt = {"prozent": e.prozent, "dateien": e.dateien}
        elif isinstance(e, ev.SyncFertig):
            self.sync_fortschritt = None
            self.sync = {"zustand": "idle", "letzter_ende": zeitstempel(jetzt.wall), "ergebnis": "ok", "grund": None, "neu": e.neu}
        elif isinstance(e, ev.SyncAbgebrochen):
            self.sync_fortschritt = None
            # ``regel``: die Regel hat den Sync nicht zugelassen, ``nicht_eingerichtet``: kein ``[sync]``; beides ist kein Fehler (12.1)
            zustand = "idle" if e.grund in ("regel", "nicht_eingerichtet") else "fehler"
            self.sync = {**self.sync, "zustand": zustand, "letzter_ende": zeitstempel(jetzt.wall), "ergebnis": "abgebrochen", "grund": e.grund}
        elif isinstance(e, ev.UpdateGestartet):
            self.update = {"zustand": "testing", "version": e.version, "grund": None}
        elif isinstance(e, ev.SelbsttestErgebnis):
            self.update = {**self.update, "zustand": "ok" if e.bestanden else "failed", "grund": None if e.bestanden else e.grund}

    def befehl(self, b: ev.Befehl, jetzt: Jetzt) -> None:
        """Die vom Kern ausgegebenen Befehle: ``ZustandMelden`` und ``Protokoll`` mit Ebene ERROR."""
        if isinstance(b, ev.ZustandMelden):
            self.zustand = b
        elif isinstance(b, ev.Protokoll) and b.ebene == "ERROR":
            self.letzter_fehler = {"zeit": zeitstempel(jetzt.wall), "text": f"{b.ereignis} {b.ergebnis}".strip()}

    # -- Abbildung --------------------------------------------------------------------

    def leser(self, mono: float) -> str:
        """Prüfpunkt Leser nach 12.2 (erste zutreffende Zeile)."""
        if self.leser_simulation:
            return "simulation"
        # ``proto_unbekannt`` ist nur als Zeile „fehler“ sinnvoll; es steht vor „noch kein Hallo“
        if self.ausfall == "proto_unbekannt":
            return "fehler"
        if self.hallo is None or self.ausfall in _GETRENNT:
            return "getrennt"
        if self.fehler_mono is not None and mono - self.fehler_mono <= LESER_FEHLER_FENSTER_S:
            return "fehler"
        return "ok"

    def als_dict(self, jetzt: Jetzt, serien: Sequence[ev.Serie], frei_mb: int | None) -> dict[str, Any]:
        """Status-JSON nach ``mqtt-v1.md`` 3.3 (``sync`` und ``update`` folgen den Ereignissen von ``sync`` und ``update``; ohne sie: kein Sync, kein Update)."""
        z = self.zustand
        serie = None
        if z is not None and z.serie_id is not None:
            name = next((s.name for s in serien if s.id == z.serie_id), z.serie_id)
            serie = {"id": z.serie_id, "name": name}
        folge = {"name": z.folge, "track": z.track or 0} if z is not None and z.folge is not None else None
        zustand = "leer" if z is None else ("herunterfahren" if z.strom == "herunterfahren" else z.sitzung)
        k = self.konfig
        return {
            "v": 1,
            "ts": zeitstempel(jetzt.wall),
            "zustand": zustand,
            "lernmodus": bool(z.lernmodus) if z is not None else False,
            "serie": serie,
            "folge": folge,
            "akku_prozent": self.akku,
            "lader": self.lader,
            "netz": self.netz,
            "sync": dict(self.sync),
            "speicher_frei_mb": frei_mb,
            "version": __version__,
            "firmware": self.hallo.fw if self.hallo is not None else None,
            "protokoll": max(PROTO_UNTERSTUETZT),
            "leser": self.leser(jetzt.mono),
            "letzter_fehler": self.letzter_fehler,
            "zeitquelle": jetzt.zeit_quelle,
            "zeit_ok": jetzt.zeit_ok,
            "konfig": {"revision": k.revision, "liste_id": k.liste_id} if k is not None else {"revision": 0, "liste_id": ""},
            "update": dict(self.update),
        }

