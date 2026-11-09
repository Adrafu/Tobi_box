"""Gemeinsamer Simulations-Treiber (``box-software.md``, Bausteine und AP 2.2).

Lauscht auf dem Unix-Socket ``<zustand>/sim.sock`` (Rechte 0600), liest JSON-Zeilen und macht
Ereignisse daraus, die er an ``ausgabe`` übergibt. Befehle in Stufe 2 (Schlüssel ``befehl``):

* ``learn``: ``{"befehl":"learn","typ":"serie","serie":"s1","ttl":60}`` oder
  ``{"befehl":"learn","typ":"folge","serie":"s1","folge":"a.mp3","ttl":60}`` -> ``HaLernmodus``
  (``gueltig_bis = jetzt.wall + ttl``). Das Ziel steht nicht im Ereignis (es gehört der Zuordnung
  durch HA); der Treiber merkt es vor und übernimmt es in ``lernziel``, sobald die Box den Befehl
  angenommen hat (``angenommen``). Ein ignorierter oder abgelehnter ``learn`` ändert den laufenden
  Lernlauf nicht. ``"ueberschreiben": true`` erlaubt dem HA-Ersatz, eine schon zugeordnete Kennung
  neu zuzuordnen (HA fragt dort nach, ``mqtt-v1.md`` 4.2).
* ``ack``: ``{"befehl":"ack","uid":…,"zuletzt":…,"art":"unbekannt"|"gelernt"}`` -> ``Bestaetigt``.
* ``card``: ``{"befehl":"card","uid":…,"ziel":{"typ":"serie","serie":…}}`` (auch ``folge``, ``aktion``)
  trägt die Zuordnung in ``config.json`` ein (``store``) -> ``KonfigGeladen``.
* ``learn_abort``: ``{"befehl":"learn_abort"}`` -> ``HaLernmodusAbbruch`` (Ablaufzeit 30 s).
* ``status``: ``{"befehl":"status"}`` -> Antwort mit dem Status des Dienstes (``auskunft``), kein Ereignis.

Seit AP 4.9 (Simulations-Oberfläche im Browser, ``tobibox gui``) kommen dazu: ``taste``, ``regler``, ``kopfhoerer``,
``strom``, ``netz``, ``tobie_auflegen``, ``tobie_gesperrt``, ``tobie_abheben`` und ``anzeige`` (alles Weitere:
``docs/betrieb/mac-prototyp.md``, Abschnitt „Simulations-Oberfläche“). Welche Eingänge wirken, steht in ``VERDRAHTET``:
Ein Eingang, dessen Modul der Dienst noch nicht kennt, wird geprüft und mit ``{"ok": false, "fehler":
"noch_nicht_verdrahtet"}`` beantwortet. AP 3.7 hat ``strom`` und ``netz`` auf ``True`` gesetzt, AP 4.8 den Rest; am Format ändert sich nichts.

Seit AP 4.8 kommt ``zeit`` dazu (``tobibox sim time``): ``{"befehl":"zeit","iso":"2026-11-09T22:30:00+01:00"}`` stellt die Wanduhr
des Dienstes (sie läuft von dort weiter, Timer und Fristen auf der monotonen Uhr bleiben), ``{"befehl":"zeit","iso":null}`` stellt die
echte Uhr wieder her. Das ist für die Leise-Zeiten gedacht.

Seit B9 (09.11.) wirken die Eingänge nur, wenn die jeweilige **Quelle** ``sim`` ist (oder ``[sim] erlauben = true`` gilt). Sonst
antwortet ``sim`` mit ``{"ok": false, "fehler": "quelle_nicht_sim"}``; die Antwort auf ``anzeige`` nennt die gesperrten Eingänge
unter ``quelle_sim`` (die Oberfläche graut sie aus). Das schützt den Pi: Dort stellt ``sim time`` nicht die Uhr, und ``sim key``
tippt keine Tasten. Gruppen: die vier Tasten (je mit eigenem Namen), ``regler``, ``kopfhoerer``, ``strom``, ``netz``, ``zeit``,
``tobie`` (``tobie_auflegen`` und Verwandte) und ``ha`` (``learn``, ``learn_abort``, ``ack``, ``card``: der HA-Ersatz gilt nur ohne ``[mqtt]``).

Wer nach dem Lernen die Zuordnung schreibt und bestätigt, steht in ``ha_ersatz.py``.

Ungültige Zeilen werden protokolliert und ignoriert. Jede Zeile wird mit einer JSON-Zeile beantwortet
(``{"ok": true}`` oder ``{"ok": false, "fehler": …}``).
"""

from __future__ import annotations

import asyncio
import errno
import inspect
import json
import os
import re
import secrets
import socket
import sys
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import events as ev
from .clock import Uhr
from .eventlog import logge as _logge
from .ha_ersatz import Abgelehnt, schreibe_zuordnung
from .store import KonfigStore

SOCKET_NAME = "sim.sock"

# Längster Unix-Socket-Pfad in Bytes: macOS/BSD 104, Linux 108 (jeweils mit abschließendem Nullbyte)
SOCKET_PFAD_MAX = 103 if sys.platform != "linux" else 107


class SocketPfadZuLang(OSError):
    """Der Pfad von ``sim.sock`` passt nicht in ``sockaddr_un``; die Meldung nennt Länge, Grenze und Abhilfe."""


def pruefe_socket_pfad(pfad: Path) -> None:
    n = len(os.fsencode(pfad))
    if n > SOCKET_PFAD_MAX:
        raise SocketPfadZuLang(
            errno.ENAMETOOLONG,
            f"Socket-Pfad zu lang ({n} Bytes, erlaubt höchstens {SOCKET_PFAD_MAX} für Unix-Sockets): {pfad}; "
            "ein kürzeres Zustandsverzeichnis wählen ([pfade] zustand in tobibox.toml)",
        )
MAX_ZEILE = 64 * 1024

NOCH_NICHT_VERDRAHTET = "noch_nicht_verdrahtet"

#: Wirkt der Eingang heute im Dienst? ``False``: der Befehl wird geprüft und mit ``noch_nicht_verdrahtet`` beantwortet.
#: ``taste``: ``hauptknopf_lang`` gehört dem Teilautomat ``idle``; alle Eingänge wirken seit AP 4.8.
#: ``strom`` und ``netz``: wirken seit AP 3.7. Im Dienst setzt ``sim`` Akku und Lader am Treiber ``SimStrom`` und das WLAN an
#: ``SimSsid`` und lässt ``power`` und ``net`` sofort messen; die Ereignisse kommen dann von diesen Modulen. Fehlt das Modul
#: (kein ``[strom]`` oder ``[netz]`` in der Konfiguration), gibt ``sim`` die Ereignisse selbst aus.
VERDRAHTET: dict[str, bool] = {
    "hauptknopf_kurz": True,
    "weiter": True,
    "zurueck": True,
    "hauptknopf_lang": True,
    "regler": True,
    "kopfhoerer": True,
    "strom": True,
    "netz": True,
}

TASTEN = ("hauptknopf_kurz", "hauptknopf_lang", "weiter", "zurueck")
ANZEIGE_KARENZ_S = 2.0
REGLER_MAX = 20  # Prozentpunkte je Befehl; eine Raste sind in der Oberfläche 2
_UID_RE = re.compile(r"^(?:[0-9a-f]{8}|[0-9a-f]{14}|[0-9a-f]{16}|[0-9a-f]{20})$")
MAX_VORGEMERKT = 8  # ``learn``-Befehle, die die Box noch nicht angenommen hat
QUELLE_NICHT_SIM = "quelle_nicht_sim"
#: Die Simulationszeit muss gültig sein (B8): ein Jahr in diesem Bereich, sonst ``iso ungueltig``.
ZEIT_JAHR_MIN = 2000
ZEIT_JAHR_MAX = 2100


def logge(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """Alle Zeilen von ``sim`` tragen ``sim=true`` (``core-interface.md``, 6.5 Punkt 4)."""
    _logge(*args, sim=True, **kwargs)


class Ungueltig(ValueError):
    pass


def _text(d: dict[str, Any], schluessel: str) -> str:
    x = d.get(schluessel)
    if not isinstance(x, str) or not x:
        raise Ungueltig(f"{schluessel} fehlt")
    return x


class Sim:
    def __init__(
        self,
        zustand: str | Path,
        ausgabe: Callable[[ev.Ereignis], Any],
        uhr: Uhr,
        konfig_store: KonfigStore | None = None,
        auskunft: Callable[[], dict[str, Any]] | None = None,
        anzeige: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.zustand = Path(zustand)
        self.pfad = self.zustand / SOCKET_NAME
        self.ausgabe = ausgabe
        self.uhr = uhr
        self.lernziel: dict[str, str] | None = None  # Ziel des Lernlaufs, den die Box angenommen hat
        self.lernbefehl_id: str | None = None  # ID dieses Lernlaufs; der HA-Ersatz prüft sie
        self.ueberschreiben = False  # darf der HA-Ersatz eine bestehende Zuordnung ersetzen?
        self._vorgemerkt: dict[str, tuple[dict[str, str], bool]] = {}  # befehl_id -> (Ziel, ueberschreiben)
        self.auskunft = auskunft  # Antwort auf ``status`` (der Dienst gibt sie herein)
        self.anzeige = anzeige  # Antwort auf ``anzeige`` (leicht genug für 300 ms; Vorgabe: ``auskunft``)
        # Der Tobie, den ``sim`` aufgelegt hat (wie der Entpreller des Lesers: ID bis zum Abheben, ``reader-v1.md`` 9)
        self.liegt: dict[str, Any] | None = None
        self._seq = 0
        self._konfig = konfig_store or KonfigStore(self.zustand)
        #: Haken des Dienstes (AP 3.7). ``strom_haken(lader, akku)`` und ``netz_haken(klasse)`` stellen den Treiber ein und lassen
        #: ``power`` bzw. ``net`` sofort messen. ``None``: ``sim`` gibt ``LaderGeaendert``, ``AkkuStand`` und ``NetzKlasse`` selbst aus.
        self.strom_haken: Callable[[bool | None, int | None], Any] | None = None
        self.netz_haken: Callable[[str], Any] | None = None
        #: Haken des Dienstes (AP 4.8). ``kopfhoerer_haken(steckt)`` stellt den Treiber der ``Buchse`` ein und lässt sie melden.
        #: ``zeit_haken(wall)`` stellt die Wanduhr (``None``: echte Uhr zurück) und gibt ``False`` zurück, wenn die Uhr das nicht kann.
        #: ``None``: ``sim`` gibt ``Kopfhoerer`` selbst aus; ``zeit`` ist dann nicht verfügbar.
        self.kopfhoerer_haken: Callable[[bool], Any] | None = None
        self.zeit_haken: Callable[[float | None], Any] | None = None
        #: Haken des Dienstes (B14): ``regler_haken(delta)`` dreht über ``Bedienung`` wie der Drehregler (Wunsch ändert sich nie durch
        #: „lauter“ über der Grenze). ``None``: ``sim`` gibt ``LautstaerkeDrehen`` selbst aus.
        self.regler_haken: Callable[[int], Any] | None = None
        #: Eingangsgruppe -> darf ``sim`` sie bedienen? Fehlt ein Name, gilt ``True``. Der Dienst setzt es nach den Quellen der
        #: Konfiguration (B9). Ohne Dienst (Tests) ist alles erlaubt.
        self.quelle_sim: dict[str, bool] = {}
        self._server: asyncio.AbstractServer | None = None

    def _quelle(self, gruppe: str) -> None:
        """Wirft ``Ungueltig("quelle_nicht_sim")``, wenn die Quelle der Gruppe nicht ``sim`` ist (B9)."""
        if not self.quelle_sim.get(gruppe, True):
            logge("sim", "WARNING", "eingang", QUELLE_NICHT_SIM, daten={"gruppe": gruppe})
            raise Ungueltig(QUELLE_NICHT_SIM)

    # -- Zeile -> Ereignis ---------------------------------------------------

    def zeile_zu_ereignis(self, zeile: str | bytes) -> ev.Ereignis:
        """Wirft ``Ungueltig`` bei jeder ungültigen Zeile."""
        return self._ereignis(self._lies(zeile))

    async def zeile_zu_ereignis_async(self, zeile: str | bytes) -> ev.Ereignis:
        """Wie ``zeile_zu_ereignis``; das Schreiben der Zuordnung (``card``) läuft in einem Thread."""
        d = self._lies(zeile)
        if d.get("befehl") == "card":
            self._quelle("ha")
            return await asyncio.to_thread(self._card, d)
        return self._ereignis(d)

    def _lies(self, zeile: str | bytes) -> dict[str, Any]:
        try:
            text = zeile.decode("utf-8") if isinstance(zeile, bytes) else zeile
            d = json.loads(text)
        except ValueError as e:
            raise Ungueltig("kein_json") from e
        if not isinstance(d, dict):
            raise Ungueltig("kein_objekt")
        return d

    def _ereignis(self, d: dict[str, Any]) -> ev.Ereignis:
        befehl = d.get("befehl")
        if befehl in ("learn", "ack", "card", "learn_abort"):
            self._quelle("ha")
        if befehl == "learn":
            return self._learn(d)
        if befehl == "ack":
            art = d.get("art")
            if art not in ("unbekannt", "gelernt"):
                raise Ungueltig("art ungueltig")
            return ev.Bestaetigt(_text(d, "uid"), str(d.get("grund") or "sim"), _text(d, "zuletzt"), art)
        if befehl == "card":
            return self._card(d)
        if befehl == "learn_abort":
            return ev.HaLernmodusAbbruch(str(uuid.uuid4()), self.uhr.jetzt().wall + 30)
        raise Ungueltig(f"befehl unbekannt: {befehl!r}")

    def _learn(self, d: dict[str, Any]) -> ev.Ereignis:
        typ = d.get("typ")
        if typ not in ("serie", "folge"):
            raise Ungueltig("typ ungueltig")
        ziel = {"typ": typ, "serie": _text(d, "serie")}
        if typ == "folge":
            ziel["folge"] = _text(d, "folge")
        ttl = d.get("ttl", 60)
        if isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= 3600:
            raise Ungueltig("ttl ungueltig")
        ueberschreiben = d.get("ueberschreiben", False)
        if not isinstance(ueberschreiben, bool):
            raise Ungueltig("ueberschreiben ungueltig")
        befehl_id = str(uuid.uuid4())
        self._vorgemerkt[befehl_id] = (ziel, ueberschreiben)
        while len(self._vorgemerkt) > MAX_VORGEMERKT:
            del self._vorgemerkt[next(iter(self._vorgemerkt))]
        logge("sim", "INFO", "lernen", "gesendet", daten={"befehl_id": befehl_id, "ueberschreiben": ueberschreiben, **ziel})
        return ev.HaLernmodus(befehl_id, self.uhr.jetzt().wall + ttl)

    def angenommen(self, befehl_id: str) -> None:
        """Die Box hat den Lernmodus-Befehl angenommen (Lernmodus hat begonnen): Ziel und ID gelten ab jetzt."""
        vorgemerkt = self._vorgemerkt.pop(befehl_id, None)
        if vorgemerkt is None:
            return
        self.lernziel, self.ueberschreiben = vorgemerkt
        self.lernbefehl_id = befehl_id
        self._vorgemerkt.clear()  # ältere, nie angenommene Befehle sind erledigt
        logge("sim", "INFO", "lernen", "angenommen", daten={"befehl_id": befehl_id, **self.lernziel})

    def _card(self, d: dict[str, Any]) -> ev.Ereignis:
        uid = _text(d, "uid")
        ziel = d.get("ziel")
        if not isinstance(ziel, dict):
            raise Ungueltig("ziel fehlt")
        try:
            return schreibe_zuordnung(self._konfig, uid, ziel)
        except Abgelehnt as e:
            raise Ungueltig(f"card abgelehnt: {e}") from e

    # -- Eingänge der Oberfläche (AP 4.9) ---------------------------------------------

    def _naechste_seq(self) -> int:
        n = self._seq
        self._seq += 1
        return n

    def _merke(self, uid: str | None, vorgang: str) -> None:
        self.liegt = {"uid": uid, "vorgang": vorgang, "mono": self.uhr.jetzt().mono}

    def _tobie_auflegen(self, d: dict[str, Any]) -> tuple[dict[str, Any], list[ev.Ereignis]]:
        """Wie ``PLACED``: neue Vorgangs-ID. Wechsel: erst ``Abgehoben``, dann ``Aufgelegt`` (``core-interface.md``, 9.4).

        Derselbe Tobie liegt schon: Wiedermeldung, kein Ereignis (9.1; Entprellen: ein Tobie liegt oder nicht).
        """
        uid = d.get("uid")
        if d.get("zufall") is True:
            uid = "04" + secrets.token_hex(6)  # 7 Bytes wie eine NTAG-Karte; nicht in der Zuordnung
        if not isinstance(uid, str) or not _UID_RE.match(uid):
            raise Ungueltig("uid ungueltig")
        if self.liegt is not None and self.liegt["uid"] == uid:
            return {"ok": True, "uid": uid, "vorgang": self.liegt["vorgang"], "hinweis": "liegt_schon"}, []
        aus: list[ev.Ereignis] = []
        if self.liegt is not None:
            aus.append(ev.Abgehoben(self._naechste_seq(), self.liegt["vorgang"]))
        iso = len(uid) == 16
        vorgang = secrets.token_hex(4)
        aus.append(ev.Aufgelegt(uid, "iso15693" if iso else "ntag", iso and uid.startswith("e004"), self._naechste_seq(), vorgang))
        self._merke(uid, vorgang)
        return {"ok": True, "uid": uid, "vorgang": vorgang}, aus

    def _tobie_gesperrt(self) -> tuple[dict[str, Any], list[ev.Ereignis]]:
        if self.liegt is not None and self.liegt["uid"] is None:
            return {"ok": True, "vorgang": self.liegt["vorgang"], "hinweis": "liegt_schon"}, []
        aus: list[ev.Ereignis] = []
        if self.liegt is not None:
            aus.append(ev.Abgehoben(self._naechste_seq(), self.liegt["vorgang"]))
        vorgang = secrets.token_hex(4)
        aus.append(ev.Gesperrt(self._naechste_seq(), vorgang))
        self._merke(None, vorgang)
        return {"ok": True, "vorgang": vorgang}, aus

    def _tobie_abheben(self) -> tuple[dict[str, Any], list[ev.Ereignis]]:
        if self.liegt is None:
            return {"ok": False, "fehler": "kein_simulierter_tobie"}, []
        vorgang, self.liegt = self.liegt["vorgang"], None
        return {"ok": True, "vorgang": vorgang}, [ev.Abgehoben(self._naechste_seq(), vorgang)]

    def _eingang(self, d: dict[str, Any]) -> tuple[dict[str, Any], list[ev.Ereignis], Callable[[], Any] | None] | None:
        """Befehle der Oberfläche. ``None``: kein solcher Befehl. Wirft ``Ungueltig``.

        Dritter Wert: ein Aufruf, den ``verarbeite`` nach den Ereignissen ausführt (``strom`` und ``netz`` mit Haken: Treiber
        einstellen und messen lassen; dann gibt es keine Ereignisse von ``sim``)."""
        befehl = d.get("befehl")
        if befehl in ("tobie_auflegen", "tobie_gesperrt", "tobie_abheben"):
            self._quelle("tobie")
        if befehl == "tobie_auflegen":
            return (*self._tobie_auflegen(d), None)
        if befehl == "tobie_gesperrt":
            return (*self._tobie_gesperrt(), None)
        if befehl == "tobie_abheben":
            return (*self._tobie_abheben(), None)
        if befehl == "taste":
            taste = d.get("taste")
            if taste not in TASTEN:
                raise Ungueltig("taste ungueltig")
            self._quelle(taste)
            if not VERDRAHTET[taste]:
                return {"ok": False, "fehler": NOCH_NICHT_VERDRAHTET}, [], None
            e: ev.Ereignis = {
                "hauptknopf_kurz": ev.Hauptknopf("kurz"),
                "hauptknopf_lang": ev.Hauptknopf("lang"),
                "weiter": ev.Weiter(),
                "zurueck": ev.Zurueck(),
            }[taste]
            return {"ok": True}, [e], None
        if befehl == "regler":
            delta = d.get("delta")
            if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0 or abs(delta) > REGLER_MAX:
                raise Ungueltig("delta ungueltig")
            self._quelle("regler")
            if not VERDRAHTET["regler"]:
                return {"ok": False, "fehler": NOCH_NICHT_VERDRAHTET}, [], None
            if self.regler_haken is not None:
                return {"ok": True}, [], lambda: self.regler_haken(delta)  # type: ignore[misc]
            return {"ok": True}, [ev.LautstaerkeDrehen(delta)], None
        if befehl == "kopfhoerer":
            steckt = d.get("steckt")
            if not isinstance(steckt, bool):
                raise Ungueltig("steckt ungueltig")
            self._quelle("kopfhoerer")
            if not VERDRAHTET["kopfhoerer"]:
                return {"ok": False, "fehler": NOCH_NICHT_VERDRAHTET}, [], None
            if self.kopfhoerer_haken is not None:
                return {"ok": True}, [], lambda: self.kopfhoerer_haken(steckt)  # type: ignore[misc]
            return {"ok": True}, [ev.Kopfhoerer(steckt)], None
        if befehl == "zeit":
            return self._zeit(d)
        if befehl == "strom":
            lader, akku = d.get("lader"), d.get("akku")
            if lader is None and akku is None:
                raise Ungueltig("lader oder akku fehlt")
            if lader is not None and not isinstance(lader, bool):
                raise Ungueltig("lader ungueltig")
            if akku is not None and (isinstance(akku, bool) or not isinstance(akku, int) or not 0 <= akku <= 100):
                raise Ungueltig("akku ungueltig")
            self._quelle("strom")
            if not VERDRAHTET["strom"]:
                return {"ok": False, "fehler": NOCH_NICHT_VERDRAHTET}, [], None
            if self.strom_haken is not None:
                return {"ok": True}, [], lambda: self.strom_haken(lader, akku)  # type: ignore[misc]
            aus: list[ev.Ereignis] = []
            if lader is not None:
                aus.append(ev.LaderGeaendert(lader))
            if akku is not None:
                aus.append(ev.AkkuStand(akku))
            return {"ok": True}, aus, None
        if befehl == "netz":
            klasse = d.get("klasse")
            if klasse not in ("home", "hotspot", "offline"):
                raise Ungueltig("klasse ungueltig")
            self._quelle("netz")
            if not VERDRAHTET["netz"]:
                return {"ok": False, "fehler": NOCH_NICHT_VERDRAHTET}, [], None
            if self.netz_haken is not None:
                return {"ok": True}, [], lambda: self.netz_haken(klasse)  # type: ignore[misc]
            return {"ok": True}, [ev.NetzKlasse(klasse)], None
        return None

    def _zeit(self, d: dict[str, Any]) -> tuple[dict[str, Any], list[ev.Ereignis], Callable[[], Any] | None]:
        """``zeit``: ``iso`` ist ein Zeitpunkt (ISO 8601; ohne Zone gilt die Ortszeit des Rechners) oder ``null`` (echte Uhr)."""
        if "iso" not in d:
            raise Ungueltig("iso fehlt")
        iso = d["iso"]
        wall: float | None = None
        if iso is not None:
            if not isinstance(iso, str) or not iso.strip():
                raise Ungueltig("iso ungueltig")
            try:
                dt = datetime.fromisoformat(iso.strip())
                if not ZEIT_JAHR_MIN <= dt.year <= ZEIT_JAHR_MAX:
                    raise Ungueltig("iso ungueltig")
                wall = dt.astimezone().timestamp()  # ohne Zone: Ortszeit des Rechners
                if not ZEIT_JAHR_MIN <= datetime.fromtimestamp(wall, timezone.utc).year <= ZEIT_JAHR_MAX:
                    raise Ungueltig("iso ungueltig")
            except Ungueltig:
                raise
            except (ValueError, OverflowError, OSError) as e:  # ``astimezone`` und ``timestamp`` laufen bei Extremwerten über
                raise Ungueltig("iso ungueltig") from e
        self._quelle("zeit")
        try:
            gestellt = self.zeit_haken is not None and self.zeit_haken(wall) is not False
        except Exception as e:  # noqa: BLE001 - die Uhr darf an einer Eingabe nicht scheitern
            logge("sim", "ERROR", "eingang", "zeit_fehler", daten={"detail": repr(e)[:200]})
            raise Ungueltig("iso ungueltig") from e
        if not gestellt:
            return {"ok": False, "fehler": "zeit_nicht_verfuegbar"}, [], None
        logge("sim", "INFO", "eingang", "zeit", daten={"wall": wall})
        return {"ok": True, "wall": wall}, [], None

    def _anzeige(self) -> dict[str, Any]:
        quelle = self.anzeige or self.auskunft
        if quelle is None:
            raise Ungueltig("anzeige nicht verfuegbar")
        a = quelle()
        # Hat ein echter Leser den Tobie gewechselt, gehört der gemerkte Vorgang nicht mehr zu uns.
        # Kurz nach dem Auflegen kennt der Kern den Tobie noch nicht (Ereignis in der Schlange): kurze Karenz.
        figur = (a.get("anzeige") or {}).get("figur")
        if self.liegt is not None and (figur is None or figur.get("vorgang") != self.liegt["vorgang"]):
            if self.uhr.jetzt().mono - self.liegt["mono"] > ANZEIGE_KARENZ_S:
                self.liegt = None
        simuliert = {k: v for k, v in self.liegt.items() if k != "mono"} if self.liegt is not None else None
        return {
            "ok": True, **a, "verdrahtet": dict(VERDRAHTET), "simuliert": simuliert,
            "quelle_sim": {k: v for k, v in self.quelle_sim.items()},
        }

    async def verarbeite(self, zeile: str | bytes) -> dict[str, Any]:
        """Eine Zeile bearbeiten und die Antwort liefern (Ereignisse gehen an ``ausgabe``). Wirft ``Ungueltig``."""
        d = self._lies(zeile)
        befehl = d.get("befehl")
        if befehl == "status":
            if self.auskunft is None:
                raise Ungueltig("status nicht verfuegbar")
            return {"ok": True, **self.auskunft()}
        if befehl == "anzeige":
            return self._anzeige()
        eingang = self._eingang(d)
        if eingang is not None:
            antwort, ereignisse, danach = eingang
            for e in ereignisse:
                logge("sim", "INFO", "eingang", str(befehl), daten={"ereignis": type(e).__name__})
                await self._abliefern(e)
            if danach is not None:
                logge("sim", "INFO", "eingang", str(befehl), daten={"ueber": "treiber"})
                await self._abliefern_haken(danach)
            return antwort
        await self._abliefern(await self.zeile_zu_ereignis_async(zeile))
        return {"ok": True}

    # -- Server --------------------------------------------------------------

    async def _abliefern_haken(self, haken: Callable[[], Any]) -> None:
        r = haken()
        if inspect.isawaitable(r):
            await r

    async def _abliefern(self, e: ev.Ereignis) -> None:
        r = self.ausgabe(e)
        if inspect.isawaitable(r):
            await r

    async def _client(self, leser: asyncio.StreamReader, schreiber: asyncio.StreamWriter) -> None:
        try:
            while True:
                try:
                    zeile = await leser.readline()
                except (asyncio.LimitOverrunError, ValueError):
                    logge("sim", "WARNING", "zeile", "zu_lang")
                    break
                if not zeile:
                    break
                if not zeile.strip():
                    continue
                try:
                    antwort = await self.verarbeite(zeile)
                except Ungueltig as ex:
                    logge("sim", "WARNING", "zeile", "ungueltig", daten={"grund": str(ex)})
                    antwort = {"ok": False, "fehler": str(ex)}
                except Exception as ex:  # noqa: BLE001 - ein Fehler in einer Zeile darf die Verbindung nicht beenden (B8)
                    logge("sim", "ERROR", "zeile", "fehler", daten={"detail": repr(ex)[:200]})
                    antwort = {"ok": False, "fehler": "intern"}
                try:
                    schreiber.write((json.dumps(antwort) + "\n").encode())
                    await schreiber.drain()
                except (ConnectionError, OSError):
                    break
        finally:
            schreiber.close()

    async def start(self) -> None:
        """Socket öffnen. Wirft ``OSError`` (Pfad zu lang, keine Rechte, Verzeichnis nicht beschreibbar)."""
        pruefe_socket_pfad(self.pfad)
        self.zustand.mkdir(parents=True, exist_ok=True)
        try:
            self.pfad.unlink()
        except FileNotFoundError:
            pass
        # Rechte ohne ``umask`` (die gilt für den ganzen Prozess): binden, ``chmod``, erst dann lauschen.
        # Vor dem Lauschen weist der Kern jede Verbindung ab, es gibt kein Zeitfenster mit offenen Rechten.
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.setblocking(False)
            sock.bind(str(self.pfad))
            os.chmod(self.pfad, 0o600)
            self._server = await asyncio.start_unix_server(self._client, sock=sock, limit=MAX_ZEILE)
        except BaseException:
            sock.close()
            try:
                self.pfad.unlink()
            except OSError:
                pass
            raise
        logge("sim", "INFO", "socket", "offen", daten={"pfad": str(self.pfad)})

    async def stop(self) -> None:
        if self._server is None:
            return  # nie geöffnet: ein fremdes ``sim.sock`` bleibt unberührt
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        try:
            self.pfad.unlink()
        except FileNotFoundError:
            pass
