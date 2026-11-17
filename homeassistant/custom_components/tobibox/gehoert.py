"""„Gehört“: die SQLite-Datei ``<config>/tobibox/gehoert.sqlite`` und die Aufnahme der Boxen (Stufe B, Paket B2).

Verträge: ``docs/data-model.md`` Abschnitt 12.1, ``docs/protocol/mqtt-v1.md`` (3.4, 3.7, 4.5), ``docs/protocol/ha-websocket-v1.md`` 15.
Design: ``docs/designs/gehoert.md`` Abschnitte 2, 4 und 11.

* ``GehoertDb``: **eine** Verbindung, ein ``threading.Lock``; alle Methoden sind synchron und laufen im Executor.
* Reine Funktionen (``verarbeite_box_nachricht``, ``bestimme_datum``): prüfen eine Nachricht ``gespielt`` und bestimmen den Beginn.
* ``TechnikBeobachter``: macht aus ``status``, ``online`` und Ereignissen die Zeilen der Tabelle ``technik``.
* ``Gehoert``: die Hülle im ``hub`` (``hub.gehoert``): Start, Aufnahme mit Quittung, Handshake, Aufräumen, Mitschreiben beim Verschieben.
"""

from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    BOX_VERWAIST_S,
    GEHOERT_MEIST_TAGE,
    GEHOERT_AUFRAEUMEN_S,
    GEHOERT_DATUM_FRUEHESTENS,
    GEHOERT_FERTIG_OHNE_DAUER_S,
    GEHOERT_FERTIG_PROZENT,
    GEHOERT_MAL_MIN_S,
    GEHOERT_PAUSE_MAX_S,
    GEHOERT_QUITTUNG_MAX,
    GEHOERT_QUITTUNG_TTL_S,
    GEHOERT_QUITTUNG_VERZOEGERUNG_S,
    GEHOERT_SITZUNGEN_JE_NACHRICHT,
    REINHOEREN_VERWAIST_S,
)
from .fehler import TobiboxFehler
from .util import iso, jetzt, parse_iso

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

SCHEMA_VERSION = 1
#: Obergrenzen gegen absurde Werte (Giftpille): Monotonsekunden einer Box (10 Jahre), Länge einer Folge (7 Tage), Vorsprung des Beginns vor dem Empfang
BOOT_S_MAX = 315_360_000
FOLGE_DAUER_MAX_S = 7 * 86400
BEGINN_VORSPRUNG_MAX_S = 86400
#: ``ende``-Werte der Box (``mqtt-v1.md``, 3.4); ``verwaist`` gibt es nur in HA
ENDEN_BOX = ("ende_der_folge", "wechsel", "pause", "herunterfahren", "dienst_ende", "abbruch", "teilweise")
#: keine Endzeilen: ein Zwischenstand, die Zeile nach Strom weg und eine verwaiste (``data-model.md``, 12.1)
ENDEN_OFFEN = ("teilweise", "abbruch", "verwaist")
_OFFEN_SQL = "('teilweise','abbruch','verwaist')"
RE_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
TECHNIK_ARTEN = ("online", "offline", "lader_an", "lader_aus", "sync_ok", "sync_fehler", "fehler", "verworfen")

_SCHEMA = """
CREATE TABLE sitzungen (
    quelle TEXT NOT NULL,
    sitzung TEXT NOT NULL,
    serie TEXT NOT NULL,
    folge TEXT NOT NULL,
    folge_dauer_s INTEGER,
    beginn INTEGER NOT NULL,
    ende_um INTEGER NOT NULL,
    datum TEXT NOT NULL,
    tag TEXT,
    stunde INTEGER,
    gehoert_s INTEGER NOT NULL,
    ende TEXT NOT NULL,
    grund TEXT,
    neues_mal INTEGER NOT NULL DEFAULT 0,
    mal_zaehlt INTEGER NOT NULL DEFAULT 0,
    fertig INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (quelle, sitzung)
);
CREATE INDEX sitzungen_quelle_serie_folge_beginn ON sitzungen (quelle, serie, folge, beginn);
CREATE INDEX sitzungen_serie_folge_beginn ON sitzungen (serie, folge, beginn);
CREATE INDEX sitzungen_tag ON sitzungen (tag);
CREATE INDEX sitzungen_beginn ON sitzungen (beginn);
CREATE INDEX sitzungen_quelle_beginn ON sitzungen (quelle, beginn);
CREATE TABLE technik (
    box TEXT NOT NULL,
    zeit INTEGER NOT NULL,
    art TEXT NOT NULL,
    wert TEXT
);
CREATE INDEX technik_box_zeit ON technik (box, zeit);
CREATE TABLE loeschmarken (
    quelle TEXT PRIMARY KEY,
    zeit INTEGER NOT NULL
);
"""

_UPSERT = f"""
INSERT INTO sitzungen (quelle, sitzung, serie, folge, folge_dauer_s, beginn, ende_um, datum, tag, stunde, gehoert_s, ende, grund)
VALUES (:quelle, :sitzung, :serie, :folge, :folge_dauer_s, :beginn, :ende_um, :datum, :tag, :stunde, :gehoert_s, :ende, :grund)
ON CONFLICT(quelle, sitzung) DO UPDATE SET
    serie = excluded.serie, folge = excluded.folge, folge_dauer_s = excluded.folge_dauer_s, beginn = excluded.beginn,
    ende_um = excluded.ende_um, datum = excluded.datum, tag = excluded.tag, stunde = excluded.stunde,
    gehoert_s = excluded.gehoert_s, ende = excluded.ende, grund = excluded.grund
WHERE CASE
    WHEN sitzungen.ende IN {_OFFEN_SQL}
        THEN (excluded.ende NOT IN {_OFFEN_SQL} OR excluded.gehoert_s > sitzungen.gehoert_s)
    ELSE (excluded.ende NOT IN {_OFFEN_SQL} AND excluded.gehoert_s > sitzungen.gehoert_s)
END
"""


# --- Zeilen und Prüfung -------------------------------------------------------------------------------------


@dataclass
class Zeile:
    """Eine Sitzung, wie sie in ``sitzungen`` steht (ohne ``quelle`` und die gerechneten Spalten)."""

    sitzung: str
    serie: str
    folge: str
    folge_dauer_s: int | None
    beginn: int
    ende_um: int
    datum: str
    gehoert_s: int
    ende: str
    grund: str | None = None


def _ganz(x: Any, minimum: int | None = None) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and (minimum is None or x >= minimum)


def _text(x: Any, kleinstens: int, hoechstens: int, *, bytes_: bool = False) -> bool:
    if not isinstance(x, str):
        return False
    n = len(x.encode("utf-8")) if bytes_ else len(x)
    return kleinstens <= n <= hoechstens


def bestimme_datum(zeit_ok: bool, beginn: int, boot_gleich: bool, empfang_s: int, gesendet_boot_s: int, beginn_boot_s: int) -> tuple[int, str]:
    """Der Beginn einer Sitzung in UTC-Sekunden und die Güte des Datums (``mqtt-v1.md``, 4.5, Punkt 6).

    ``beginn`` ist die Wanduhr der Box. Gibt ``(0, "unbekannt")`` zurück, wenn nichts davon zutrifft."""
    if zeit_ok:
        return beginn, "sicher"
    if boot_gleich:
        return max(empfang_s - max(gesendet_boot_s - beginn_boot_s, 0), 0), "sicher"
    if GEHOERT_DATUM_FRUEHESTENS < beginn <= empfang_s:
        return beginn, "ungefaehr"
    return 0, "unbekannt"


def _pruefe_sitzung(
    r: dict[str, Any], boot_id: str, gesendet_boot_s: int, empfang_s: int, dauer_fn: Callable[[str, str], int | None] | None
) -> tuple[Zeile | None, str | None]:
    """``(Zeile, None)`` oder ``(None, Grund)``; der Grund geht ins Protokoll."""
    if not _text(r.get("serie"), 1, 64):
        return None, "serie"
    if not _text(r.get("folge"), 1, 255, bytes_=True):
        return None, "folge"
    dauer_box = r.get("folge_dauer_s")
    if dauer_box is not None and not (_ganz(dauer_box) and dauer_box > 0):
        return None, "folge_dauer_s"
    if dauer_box is not None and dauer_box > FOLGE_DAUER_MAX_S:
        return None, "folge_dauer_s zu gross"
    zeit = parse_iso(r.get("beginn"))
    if zeit is None:
        return None, "beginn"
    if not isinstance(r.get("zeit_ok"), bool):
        return None, "zeit_ok"
    if not _text(r.get("boot_id"), 1, 64):
        return None, "boot_id"
    b, e = r.get("beginn_boot_s"), r.get("ende_boot_s")
    if not _ganz(b, 0) or not _ganz(e) or e < b:
        return None, "beginn_boot_s/ende_boot_s"
    if e > BOOT_S_MAX:
        return None, "boot_s zu gross"
    g = r.get("gehoert_s")
    if not _ganz(g, 1):
        return None, "gehoert_s"
    ende = r.get("ende")
    if ende not in ENDEN_BOX:
        return None, "ende"
    grund = r.get("grund")
    if grund is not None and not _text(grund, 0, 32):
        return None, "grund"
    schranke = e - b + 2
    if g > schranke:
        _LOGGER.warning("gehoert_s %s einer Sitzung auf die Schranke %s gekappt", g, schranke)
        g = schranke
    wand = int(zeit.timestamp())
    if r["zeit_ok"] and wand > empfang_s + BEGINN_VORSPRUNG_MAX_S:
        return None, "beginn liegt in der Zukunft"
    if gesendet_boot_s > BOOT_S_MAX:
        return None, "gesendet_boot_s zu gross"
    beginn, datum = bestimme_datum(r["zeit_ok"], wand, r["boot_id"] == boot_id, empfang_s, gesendet_boot_s, b)
    ende_um = beginn + (e - b) if datum != "unbekannt" else e - b
    dauer = dauer_fn(r["serie"], r["folge"]) if dauer_fn is not None else None
    return Zeile(r["sitzung"], r["serie"], r["folge"], dauer or dauer_box, beginn, ende_um, datum, g, ende, grund), None


def verarbeite_box_nachricht(
    daten: dict[str, Any], empfang_s: int, dauer_fn: Callable[[str, str], int | None] | None = None
) -> tuple[list[Zeile], list[str]]:
    """Prüft ``daten`` einer Nachricht ``gespielt`` (``mqtt-v1.md``, 3.4). Gibt ``(Zeilen, zu quittierende UUIDs)`` zurück.

    Jede Sitzung wird einzeln geprüft. Eine ungültige Sitzung wird nicht gespeichert, aber **quittiert** (sonst wiederholt die Box sie ewig), wenn ihre
    ``sitzung`` eine UUID ist; Zwischenstände (``teilweise``) werden nie quittiert. Doppelte ``sitzung`` in einer Nachricht zählen einmal.
    Mehr als 20 Sitzungen: die ersten 20 gelten (der Rest wird nicht quittiert, die Box sendet ihn wieder)."""
    roh = daten.get("sitzungen")
    if not isinstance(roh, list):
        _LOGGER.warning("gespielt ohne Liste der Sitzungen verworfen")
        return [], []
    if len(roh) > GEHOERT_SITZUNGEN_JE_NACHRICHT:
        _LOGGER.warning("gespielt mit %s Sitzungen: nur die ersten %s gelten", len(roh), GEHOERT_SITZUNGEN_JE_NACHRICHT)
        roh = roh[:GEHOERT_SITZUNGEN_JE_NACHRICHT]
    boot_id, gesendet = daten.get("boot_id"), daten.get("gesendet_boot_s")
    kopf_ok = _text(boot_id, 1, 64) and _ganz(gesendet, 0)
    zeilen: list[Zeile] = []
    quittung: list[str] = []
    gesehen: set[str] = set()
    for r in roh:
        if not isinstance(r, dict):
            _LOGGER.warning("gespielt: Eintrag ist kein Objekt, verworfen")
            continue
        sid = r.get("sitzung")
        sid_ok = isinstance(sid, str) and RE_UUID.match(sid) is not None
        if sid_ok:
            if sid in gesehen:
                continue
            gesehen.add(sid)
        if kopf_ok:
            try:
                zeile, grund = _pruefe_sitzung(r, boot_id, gesendet, empfang_s, dauer_fn)
            except (OverflowError, ValueError, OSError) as err:  # Giftpille: absurde Zahlen oder Zeiten
                zeile, grund = None, f"nicht rechenbar ({type(err).__name__})"
        else:
            zeile, grund = None, "boot_id/gesendet_boot_s der Nachricht"
        if zeile is not None and not sid_ok:
            zeile, grund = None, "sitzung"
        if zeile is not None:
            zeilen.append(zeile)
        else:
            _LOGGER.warning("gespielt: ungültige Sitzung verworfen (%s)", grund)
        if sid_ok and r.get("ende") != "teilweise":
            quittung.append(sid)
    return zeilen, quittung


# --- SQLite -------------------------------------------------------------------------------------------------------


class GehoertDb:
    """Die Datei ``gehoert.sqlite``. Synchron; jeder Aufruf hält das Lock (eine Verbindung, ``check_same_thread=False``)."""

    def __init__(self, pfad: Path) -> None:
        self.pfad = pfad
        self._lock = threading.Lock()
        self._con: sqlite3.Connection | None = None

    # --- Öffnen und Schließen --------------------------------------------------------------------------

    def oeffne(self) -> None:
        """Öffnet (und legt an), prüft die Version und ``integrity_check``. Wirft ``sqlite3.Error`` oder ``TobiboxFehler`` (zu neu)."""
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.pfad, check_same_thread=False, isolation_level=None)
        try:
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA journal_mode=TRUNCATE")
            con.execute("PRAGMA synchronous=FULL")
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise TobiboxFehler("invalid_format", grund="gehoert.sqlite zu neu")
            if version == 0:
                con.execute("BEGIN")
                for befehl in (s.strip() for s in _SCHEMA.split(";")):
                    if befehl:
                        con.execute(befehl)
                con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                con.execute("COMMIT")
            ergebnis = [z[0] for z in con.execute("PRAGMA integrity_check").fetchall()]
            if ergebnis == ["ok"]:
                _LOGGER.info("gehoert.sqlite: integrity_check ok")
            else:
                _LOGGER.error("gehoert.sqlite: integrity_check meldet %s", ergebnis[:5])
        except BaseException:
            con.close()
            raise
        self._con = con

    def schliesse(self) -> None:
        with self._lock:
            if self._con is not None:
                self._con.close()
                self._con = None

    def _c(self) -> sqlite3.Connection:
        if self._con is None:
            raise sqlite3.ProgrammingError("gehoert.sqlite ist nicht offen")
        return self._con

    # --- Aufnahme --------------------------------------------------------------------------------------

    def nimm_auf(self, quelle: str, zeilen: list[Zeile], zone: tzinfo) -> dict[str, int]:
        """Fügt Zeilen einer Quelle ein (ein ``COMMIT`` für alle) und rechnet die betroffenen Gruppen neu.

        Zeilen, deren ``ende_um`` vor der Löschmarke der Quelle liegt (und solche mit unbekanntem Datum, sobald es eine Marke gibt), werden verworfen.
        Gibt ``{"gespeichert": n, "geaendert": n, "marke": n}`` zurück (``geaendert``: die Zeile gab es schon und wurde ersetzt)."""
        erg = {"gespeichert": 0, "geaendert": 0, "marke": 0}
        with self._lock:
            con = self._c()
            con.execute("BEGIN IMMEDIATE")
            try:
                marke = con.execute("SELECT zeit FROM loeschmarken WHERE quelle=?", (quelle,)).fetchone()
                gruppen: set[tuple[str, str, str]] = set()
                for z in zeilen:
                    try:
                        self._nimm_zeile(con, quelle, z, zone, marke, erg, gruppen)
                    except (OverflowError, ValueError, OSError) as err:
                        erg["ungueltig"] = erg.get("ungueltig", 0) + 1
                        _LOGGER.warning("gehoert.sqlite: Zeile %s nicht rechenbar, verworfen (%s)", z.sitzung, type(err).__name__)
                for q, s, f in gruppen:
                    _neu_rechnen(con, q, s, f)
                con.execute("COMMIT")
            except BaseException:
                con.execute("ROLLBACK")
                raise
        return erg

    def _nimm_zeile(self, con: sqlite3.Connection, quelle: str, z: Zeile, zone: tzinfo, marke: Any, erg: dict[str, int], gruppen: set[tuple[str, str, str]]) -> None:
        if marke is not None and (z.datum == "unbekannt" or z.ende_um < marke["zeit"]):
            erg["marke"] += 1
            return
        alt = con.execute("SELECT serie, folge FROM sitzungen WHERE quelle=? AND sitzung=?", (quelle, z.sitzung)).fetchone()
        tag = stunde = None
        if z.datum != "unbekannt":
            d = datetime.fromtimestamp(z.beginn, zone)
            tag, stunde = d.strftime("%Y-%m-%d"), d.hour
        cur = con.execute(
            _UPSERT,
            {
                "quelle": quelle, "sitzung": z.sitzung, "serie": z.serie, "folge": z.folge, "folge_dauer_s": z.folge_dauer_s,
                "beginn": z.beginn, "ende_um": z.ende_um, "datum": z.datum, "tag": tag, "stunde": stunde,
                "gehoert_s": z.gehoert_s, "ende": z.ende, "grund": z.grund,
            },
        )
        if cur.rowcount > 0:
            erg["geaendert" if alt is not None else "gespeichert"] += 1
        gruppen.add((quelle, z.serie, z.folge))
        if alt is not None:
            gruppen.add((quelle, alt["serie"], alt["folge"]))

    # --- Lesen (Tests, B3) -------------------------------------------------------------------------------

    def alle(self, quelle: str | None = None) -> list[dict[str, Any]]:
        """Alle Zeilen in Eingangsreihenfolge (``rowid``)."""
        with self._lock:
            sql = "SELECT * FROM sitzungen" + (" WHERE quelle=?" if quelle is not None else "") + " ORDER BY rowid"
            return [dict(r) for r in self._c().execute(sql, (quelle,) if quelle is not None else ())]

    def technik_alle(self, box: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            sql = "SELECT * FROM technik" + (" WHERE box=?" if box is not None else "") + " ORDER BY rowid"
            return [dict(r) for r in self._c().execute(sql, (box,) if box is not None else ())]

    def marken(self) -> dict[str, int]:
        with self._lock:
            return {r["quelle"]: r["zeit"] for r in self._c().execute("SELECT quelle, zeit FROM loeschmarken")}

    # --- Lesen für die Befehle 50 bis 54 (Paket B3) -----------------------------------------------------------
    # Alle Abfragen bauen ``WHERE`` nur aus festen Bausteinen (Spaltennamen aus einer Liste im Code); Werte gehen als Parameter hinein.

    def quellen(self) -> list[str]:
        """Alle Quellen, zu denen es Zeilen gibt."""
        with self._lock:
            return [r[0] for r in self._c().execute("SELECT DISTINCT quelle FROM sitzungen ORDER BY quelle")]

    def erster_tag(self, wo: str, params: tuple) -> str | None:
        """Der früheste bekannte Tag (``JJJJ-MM-TT``) unter dem Filter; ``None``, wenn es keinen gibt."""
        with self._lock:
            r = self._c().execute(f"SELECT MIN(tag) FROM sitzungen WHERE {wo} AND tag IS NOT NULL", params).fetchone()
            return r[0]

    def fasse_zusammen(
        self, wo: str, params: tuple, spalten: list[str], mit_folgen: bool
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], tuple[int, int, int]]:
        """Befehl 50: ``(Gruppen, Folgen, Summe)`` unter dem Filter, in **einem** Zugriff.

        * Gruppen: je Wert der ``spalten`` Hörzeit, Zahl der „Mal“ (``mal_zaehlt``) und der „fertig“-Sitzungen.
        * Folgen: die verschiedenen (``spalten``, ``folge``), die im Filter mindestens einmal „fertig“ waren (nur mit ``mit_folgen``).
        * Summe: ``(Hörzeit, Mal, fertig)`` über den ganzen Filter."""
        with self._lock:
            con = self._c()
            cols = ", ".join(spalten)
            gruppen = [
                dict(r)
                for r in con.execute(
                    f"SELECT {cols}, SUM(gehoert_s) AS sekunden, SUM(mal_zaehlt) AS mal, SUM(fertig) AS fertig FROM sitzungen WHERE {wo} GROUP BY {cols}",
                    params,
                )
            ]
            folgen = (
                [dict(r) for r in con.execute(f"SELECT DISTINCT {cols}, folge FROM sitzungen WHERE {wo} AND fertig = 1", params)] if mit_folgen else []
            )
            s = con.execute(
                f"SELECT COALESCE(SUM(gehoert_s), 0), COALESCE(SUM(mal_zaehlt), 0), COALESCE(SUM(fertig), 0) FROM sitzungen WHERE {wo}", params
            ).fetchone()
            return gruppen, folgen, (s[0], s[1], s[2])

    def zuletzt_je_serie(self, wo: str, params: tuple) -> list[tuple[str, int, str]]:
        """Befehl 51: je Serie ``(serie, ende_um, quelle)`` der letzten Sitzung mit bekanntem Datum, neueste zuerst."""
        with self._lock:
            return [
                (r[0], r[1], r[2])
                for r in self._c().execute(
                    f"SELECT serie, MAX(ende_um) AS zeit, quelle FROM sitzungen WHERE {wo} AND datum <> 'unbekannt' GROUP BY serie ORDER BY zeit DESC, serie",
                    params,
                )
            ]

    def hoerzeit_ab(self, tag_ab: str) -> dict[str, int]:
        """Zwischenspeicher „meist gehört“: je Serie die Hörzeit (alle Quellen) seit dem Tag ``tag_ab`` (einschließlich)."""
        with self._lock:
            return {
                r[0]: r[1]
                for r in self._c().execute("SELECT serie, SUM(gehoert_s) FROM sitzungen WHERE tag >= ? GROUP BY serie", (tag_ab,))
            }

    def zuletzt_boxen(self) -> dict[str, int]:
        """Zwischenspeicher „zuletzt gehört“: je Serie ``ende_um`` der letzten Sitzung an einer **Box** (bekanntes Datum)."""
        with self._lock:
            return {
                r[0]: r[1]
                for r in self._c().execute(
                    "SELECT serie, MAX(ende_um) FROM sitzungen WHERE substr(quelle, 1, 4) = 'box:' AND datum <> 'unbekannt' GROUP BY serie"
                )
            }

    def zeilen_fuer_export(self, wo: str, params: tuple) -> list[dict[str, Any]]:
        """Befehl 53: alle Zeilen unter dem Filter, nach Beginn (unbekanntes Datum zuletzt, dann Eingang)."""
        with self._lock:
            return [
                dict(r)
                for r in self._c().execute(
                    f"SELECT * FROM sitzungen WHERE {wo} ORDER BY (datum = 'unbekannt'), beginn, rowid", params
                )
            ]

    def zaehle(self, quellen: list[str]) -> int:
        """Zahl der Zeilen der konkreten Quellen (Probelauf von Befehl 54)."""
        if not quellen:
            return 0
        with self._lock:
            marken = ",".join("?" * len(quellen))
            return self._c().execute(f"SELECT COUNT(*) FROM sitzungen WHERE quelle IN ({marken})", tuple(quellen)).fetchone()[0]

    def technik_lies(self, box: str, von_s: int, bis_s: int) -> dict[str, Any]:
        """Befehl 52: die Zeilen der Box mit ``von_s <= zeit < bis_s`` (aufsteigend), dazu den Stand des Ladens **vor** dem Zeitraum
        (``vorher``: ``lader_an``, ``lader_aus`` oder ``None``, mit Zeit) und die erste Zeile ``lader_an``/``offline`` **ab** ``bis_s`` (``danach``)."""
        with self._lock:
            con = self._c()
            zeilen = [
                dict(r)
                for r in con.execute(
                    "SELECT zeit, art, wert FROM technik WHERE box = ? AND zeit >= ? AND zeit < ? ORDER BY zeit, rowid LIMIT ?",
                    (box, von_s, bis_s, 1_000_000),
                )
            ]
            vorher = con.execute(
                "SELECT zeit, art FROM technik WHERE box = ? AND zeit < ? AND art IN ('lader_an', 'lader_aus') ORDER BY zeit DESC, rowid DESC LIMIT 1",
                (box, von_s),
            ).fetchone()
            danach = con.execute(
                "SELECT zeit, art FROM technik WHERE box = ? AND zeit >= ? AND art IN ('lader_an', 'offline') ORDER BY zeit, rowid LIMIT 1",
                (box, bis_s),
            ).fetchone()
            return {"zeilen": zeilen, "vorher": dict(vorher) if vorher else None, "danach": dict(danach) if danach else None}

    # --- Technik -------------------------------------------------------------------------------------------

    def technik_schreibe(self, box: str, zeilen: list[tuple[int, str, str | None]]) -> None:
        with self._lock:
            con = self._c()
            con.execute("BEGIN IMMEDIATE")
            try:
                con.executemany("INSERT INTO technik (box, zeit, art, wert) VALUES (?, ?, ?, ?)", [(box, z, a, w) for z, a, w in zeilen])
                con.execute("COMMIT")
            except BaseException:
                con.execute("ROLLBACK")
                raise

    # --- Aufräumen, Löschen, Umschreiben -------------------------------------------------------------------

    def raeume_auf(self, jetzt_s: int) -> int:
        """Schließt Zwischenstände ohne Abschluss als ``verwaist``: Box nach 24 Stunden (ungefähr/unbekanntes Datum: gleich, die Uhr gilt nichts),
        Reinhören nach 30 Minuten. Gibt die Zahl der geschlossenen Zeilen zurück."""
        with self._lock:
            con = self._c()
            con.execute("BEGIN IMMEDIATE")
            try:
                cur = con.execute(
                    """UPDATE sitzungen SET ende='verwaist' WHERE ende='teilweise' AND (
                           (substr(quelle,1,9)='benutzer:' AND ende_um < ?) OR
                           (substr(quelle,1,4)='box:' AND (ende_um < ? OR datum='unbekannt')))""",
                    (jetzt_s - REINHOEREN_VERWAIST_S, jetzt_s - BOX_VERWAIST_S),
                )
                con.execute("COMMIT")
            except BaseException:
                con.execute("ROLLBACK")
                raise
            return cur.rowcount

    def loesche(self, quellen: list[str], jetzt_s: int) -> int:
        """Löscht alle Zeilen der **konkreten** Quellen und setzt je Quelle die Löschmarke (Befehl 54 ruft das in B3). Gibt die Zahl der Zeilen zurück."""
        with self._lock:
            con = self._c()
            con.execute("BEGIN IMMEDIATE")
            try:
                anzahl = 0
                for q in quellen:
                    anzahl += con.execute("DELETE FROM sitzungen WHERE quelle=?", (q,)).rowcount
                    con.execute("INSERT INTO loeschmarken (quelle, zeit) VALUES (?, ?) ON CONFLICT(quelle) DO UPDATE SET zeit=excluded.zeit", (q, jetzt_s))
                con.execute("COMMIT")
            except BaseException:
                con.execute("ROLLBACK")
                raise
            return anzahl

    def schreibe_um(self, zuordnung: dict[tuple[str, str], tuple[str, str]]) -> int:
        """Schreibt ``(serie, folge)`` der Zeilen um (Verschieben und Zusammenführen) und rechnet die betroffenen Gruppen neu."""
        if not zuordnung:
            return 0
        with self._lock:
            con = self._c()
            con.execute("BEGIN IMMEDIATE")
            try:
                gruppen: set[tuple[str, str, str]] = set()
                anzahl = 0
                for (s, f), (ns, nf) in zuordnung.items():
                    for r in con.execute("SELECT DISTINCT quelle FROM sitzungen WHERE serie=? AND folge=?", (s, f)).fetchall():
                        gruppen.add((r["quelle"], ns, nf))
                    anzahl += con.execute("UPDATE sitzungen SET serie=?, folge=? WHERE serie=? AND folge=?", (ns, nf, s, f)).rowcount
                for q, s, f in gruppen:
                    _neu_rechnen(con, q, s, f)
                con.execute("COMMIT")
            except BaseException:
                con.execute("ROLLBACK")
                raise
            return anzahl


def _neu_rechnen(con: sqlite3.Connection, quelle: str, serie: str, folge: str) -> None:
    """``neues_mal``, ``mal_zaehlt`` und ``fertig`` einer Gruppe (Quelle, Serie, Folge) neu rechnen (Vertrag W, 15.1; Design Abschnitt 2 und 11).

    * **Mal:** bekannte Daten nach Beginn; ein neues Mal beginnt, wenn die vorige Sitzung mehr als 30 Minuten vor dem Beginn endete oder am Ende der
      Folge endete. Unbekanntes Datum: je Sitzung ein eigenes Mal. ``neues_mal`` trägt die erste Sitzung, ``mal_zaehlt`` gilt bei Summe ≥ 10 s.
    * **fertig:** in der Reihenfolge unbekannt (Eingang), dann bekannt (Beginn); die Hörzeit seit dem letzten „fertig“ wird summiert; eine Sitzung mit
      ``ende_der_folge`` ist fertig, wenn die Summe mindestens 80 % der Dauer (ohne Dauer 60 s) erreicht.
    """
    rows = con.execute(
        "SELECT rowid AS rid, beginn, ende_um, datum, gehoert_s, ende, folge_dauer_s, neues_mal, mal_zaehlt, fertig FROM sitzungen WHERE quelle=? AND serie=? AND folge=?",
        (quelle, serie, folge),
    ).fetchall()
    if not rows:
        return
    unbekannt = sorted((r for r in rows if r["datum"] == "unbekannt"), key=lambda r: r["rid"])
    bekannt = sorted((r for r in rows if r["datum"] != "unbekannt"), key=lambda r: (r["beginn"], r["rid"]))
    mals: list[list[int]] = []  # [rid der ersten Sitzung, Summe der Hörzeit]
    vorige = None
    for r in bekannt:
        if vorige is not None and r["beginn"] - vorige["ende_um"] <= GEHOERT_PAUSE_MAX_S and vorige["ende"] != "ende_der_folge":
            mals[-1][1] += r["gehoert_s"]
        else:
            mals.append([r["rid"], r["gehoert_s"]])
        # „vorige“ ist die Sitzung mit dem bisher spätesten Ende (zwei Fenster überlappen sich: nicht nur die unmittelbar vorige nach Beginn)
        if vorige is None or r["ende_um"] >= vorige["ende_um"]:
            vorige = r
    for r in unbekannt:
        mals.append([r["rid"], r["gehoert_s"]])
    neu: dict[int, list[int]] = {r["rid"]: [0, 0, 0] for r in rows}
    for rid, summe in mals:
        neu[rid][0] = 1
        neu[rid][1] = 1 if summe >= GEHOERT_MAL_MIN_S else 0
    dauer_gruppe = next((r["folge_dauer_s"] for r in sorted(rows, key=lambda r: -r["rid"]) if r["folge_dauer_s"]), None)
    summe = 0
    for r in unbekannt + bekannt:
        summe += r["gehoert_s"]
        if r["ende"] == "ende_der_folge":
            dauer = r["folge_dauer_s"] or dauer_gruppe
            ok = summe * 100 >= GEHOERT_FERTIG_PROZENT * dauer if dauer else summe >= GEHOERT_FERTIG_OHNE_DAUER_S
            if ok:
                neu[r["rid"]][2] = 1
                summe = 0
    for r in rows:
        n = neu[r["rid"]]
        if (r["neues_mal"], r["mal_zaehlt"], r["fertig"]) != tuple(n):
            con.execute("UPDATE sitzungen SET neues_mal=?, mal_zaehlt=?, fertig=? WHERE rowid=?", (*n, r["rid"]))


# --- Technik-Zeilen -----------------------------------------------------------------------------------------------


class TechnikBeobachter:
    """Erkennt **echte Wechsel** (``data-model.md``, 12.1, Tabelle ``technik``). Der erste ``status`` einer Box nach dem Start von HA wird nur verglichen."""

    def __init__(self) -> None:
        self._stand: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _zeit(daten: dict[str, Any], empfang_s: int) -> int:
        """``ts`` der Box bei ``zeit_ok``, sonst die Empfangszeit."""
        if daten.get("zeit_ok") is True:
            t = parse_iso(daten.get("ts"))
            if t is not None:
                return int(t.timestamp())
        return empfang_s

    def status(self, box: str, daten: dict[str, Any], empfang_s: int) -> list[tuple[int, str, str | None]]:
        zeit = self._zeit(daten, empfang_s)
        lader = daten.get("lader") if isinstance(daten.get("lader"), bool) else None
        sync = daten.get("sync") if isinstance(daten.get("sync"), dict) else {}
        sync_ende = sync.get("letzter_ende") if isinstance(sync.get("letzter_ende"), str) else None
        verworfen = daten.get("gehoert_verworfen") if _ganz(daten.get("gehoert_verworfen"), 0) else None
        alt = self._stand.get(box)
        self._stand[box] = {"lader": lader, "sync_ende": sync_ende, "verworfen": verworfen}
        if alt is None:
            return []
        zeilen: list[tuple[int, str, str | None]] = []
        if lader is not None and alt["lader"] is not None and lader != alt["lader"]:
            zeilen.append((zeit, "lader_an" if lader else "lader_aus", None))
        if sync_ende is not None and sync_ende != alt["sync_ende"]:
            if sync.get("ergebnis") == "ok":
                zeilen.append((zeit, "sync_ok", None))
            else:
                zeilen.append((zeit, "sync_fehler", str(sync.get("grund") or sync.get("ergebnis") or "")[:64] or None))
        if verworfen is not None and alt["verworfen"] is not None and verworfen > alt["verworfen"]:
            zeilen.append((zeit, "verworfen", str(verworfen)))
        # Ein Feld, das vorher fehlte oder unbekannt war, behält seinen neuen Wert als Ausgangspunkt (kein Wechsel).
        for k in ("lader", "sync_ende", "verworfen"):
            if self._stand[box][k] is None:
                self._stand[box][k] = alt[k]
        return zeilen

    @staticmethod
    def online(alt: bool | None, neu: bool, zeit_s: int) -> list[tuple[int, str, str | None]]:
        """``alt`` ist der vorige Stand der Box (``None``: noch nichts gesehen seit dem Start von HA: nur verglichen)."""
        if alt is None or alt == neu:
            return []
        return [(zeit_s, "online" if neu else "offline", None)]

    @staticmethod
    def fehler(daten: dict[str, Any], zeit_s: int) -> list[tuple[int, str, str | None]]:
        code = daten.get("code")
        return [(zeit_s, "fehler", code[:64] if isinstance(code, str) and code else None)]


# --- Die Hülle im Hub ---------------------------------------------------------------------------------------------


@dataclass
class Zwischenspeicher:
    """Zwischenspeicher im Arbeitsspeicher (Vertrag W, 4.9; ``data-model.md``, 12.1): je Serie ``ende_um`` der letzten Sitzung an einer Box und die Hörzeit der
    letzten 365 Kalendertage (alle Quellen)."""

    stand: int
    heute: date
    zuletzt: dict[str, int]
    meist: dict[str, int]


class Gehoert:
    """``hub.gehoert``: öffnet die Datenbank, nimmt Sitzungen der Boxen auf, quittiert und beantwortet den Handshake."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.db: GehoertDb | None = None
        #: ``True``, wenn die Datenbank offen ist: die Fähigkeit ``gehoert`` (B3 trägt sie in ``hello`` ein)
        self.verfuegbar = False
        self.technik = TechnikBeobachter()
        #: zählt jede Änderung der Hördaten: der Zwischenspeicher verfällt, das Ereignis ``gehoert`` kommt (B3)
        self.stand = 0
        #: Zwischenspeicher für ``zuletzt_gehoert_am`` und ``meist_gehoert`` (Vertrag W, 4.9); verfällt, wenn sich ``stand`` oder der Tag ändert
        self._zs: Zwischenspeicher | None = None
        self._zs_sperre = asyncio.Lock()
        #: die Abfragen der Befehle 50 bis 54 (``gehoert_abfrage.py``)
        from .gehoert_abfrage import GehoertAbfragen

        self.abfrage = GehoertAbfragen(self)
        self._sperre = asyncio.Lock()  # ein Zugriff nach dem anderen, in der Reihenfolge der Nachrichten
        self._quittung: dict[str, list[str]] = {}
        self._quittung_timer: dict[str, Callable[[], None]] = {}

    # --- Start und Ende ------------------------------------------------------------------------------------

    async def async_start(self, pfad: Path | None = None) -> None:
        pfad = pfad or Path(self.hub.hass.config.path("tobibox", "gehoert.sqlite"))
        db = GehoertDb(pfad)
        try:
            await self.hub.hass.async_add_executor_job(db.oeffne)
        except (sqlite3.Error, OSError, TobiboxFehler) as err:
            _LOGGER.error("gehoert.sqlite nicht zu öffnen (%s): „Gehört“ startet ohne die Fähigkeit", err)
            return
        self.db = db
        self.verfuegbar = True
        await self.raeume_auf()
        self.hub._abmelden.append(async_track_time_interval(self.hub.hass, self._timer_aufraeumen, _sekunden(GEHOERT_AUFRAEUMEN_S)))

    async def async_stop(self) -> None:
        for abbruch in list(self._quittung_timer.values()):
            abbruch()
        self._quittung_timer.clear()
        if self.db is not None:
            db, self.db, self.verfuegbar = self.db, None, False
            await self.hub.hass.async_add_executor_job(db.schliesse)

    async def _timer_aufraeumen(self, _now: Any) -> None:
        await self.raeume_auf()

    # --- Zugriff im Executor (je Aufruf eine Sperre: die Reihenfolge bleibt wie die der Nachrichten) ---------------

    async def _lauf(self, fn: Callable[..., Any], *args: Any) -> Any:
        async with self._sperre:
            return await self.hub.hass.async_add_executor_job(fn, *args)

    async def nimm_zeilen_auf(self, quelle: str, zeilen: list[Zeile]) -> dict[str, int] | None:
        """Schreibt Zeilen (Box oder Reinhören). ``None``, wenn die Datenbank fehlt oder ein Datenbankfehler auftrat (Protokoll)."""
        if self.db is None or not zeilen:
            return {"gespeichert": 0, "geaendert": 0, "marke": 0} if self.db is not None else None
        try:
            erg = await self._lauf(self.db.nimm_auf, quelle, zeilen, dt_util.get_default_time_zone())
        except (sqlite3.Error, OverflowError, ValueError):
            _LOGGER.exception("gehoert.sqlite: Schreiben fehlgeschlagen")
            return None
        if erg["gespeichert"] or erg["geaendert"]:
            self._geaendert()
        return erg

    def _geaendert(self) -> None:
        """Die Hördaten haben sich geändert: Zwischenspeicher verfällt (``stand``), Ereignis ``gehoert`` gebündelt (Vertrag W, 4.9)."""
        self.stand += 1
        self.hub.gehoert_geaendert()

    # --- Boxen: gespielt, Quittung, Handshake ------------------------------------------------------------

    async def nimm_box_auf(self, box: str, daten: dict[str, Any], empfang_s: int) -> None:
        """Nimmt ``gespielt`` einer **bekannten** Box ab: prüfen, speichern (``COMMIT``), **danach** quittieren."""
        if self.db is None:
            return
        medieninfo = self.hub.medieninfo
        zeilen, quittung = verarbeite_box_nachricht(daten, empfang_s, medieninfo.dauer_s)
        if zeilen:
            if await self.nimm_zeilen_auf(f"box:{box}", zeilen) is None:
                return  # nichts quittiert: die Box sendet die Zeilen wieder
        self._merke_quittung(box, quittung)

    def _merke_quittung(self, box: str, uuids: list[str]) -> None:
        if not uuids:
            return
        liste = self._quittung.setdefault(box, [])
        liste.extend(u for u in uuids if u not in liste)
        if len(liste) >= GEHOERT_QUITTUNG_MAX:
            self.hub.hass.async_create_task(self._sende_quittung(box), "tobibox_gehoert_quittung")
        elif box not in self._quittung_timer:
            self._quittung_timer[box] = self.hub.plane(GEHOERT_QUITTUNG_VERZOEGERUNG_S, lambda _n, b=box: self._sende_quittung(b))

    async def _sende_quittung(self, box: str) -> None:
        abbruch = self._quittung_timer.pop(box, None)
        if abbruch is not None:
            abbruch()
        liste = self._quittung.pop(box, [])
        for i in range(0, len(liste), GEHOERT_QUITTUNG_MAX):
            await self._sende(box, liste[i : i + GEHOERT_QUITTUNG_MAX])

    async def _sende(self, box: str, uuids: list[str]) -> bool:
        try:
            await self.hub.mqtt.sende_befehl(box, "gehoert_quittung", GEHOERT_QUITTUNG_TTL_S, {"sitzungen": uuids})
        except TobiboxFehler as err:
            _LOGGER.warning("Quittung an %s nicht gesendet (%s); die Box sendet die Zeilen wieder", box, err.code)
            return False
        return True

    async def handshake(self, box: str) -> None:
        """Antwort auf einen ``status`` mit ``gehoert_wartet = true``: eine Quittung mit leerer Liste (``mqtt-v1.md``, 4.5, Punkt 1)."""
        if self.db is not None:
            await self._sende(box, [])

    # --- Zwischenspeicher für ``zuletzt_gehoert_am`` und ``meist_gehoert`` -------------------------------------------

    async def zwischenspeicher(self) -> Zwischenspeicher | None:
        """Lädt den Zwischenspeicher neu, wenn er veraltet ist (``stand`` oder Tag geändert); ``None`` ohne Datenbank."""
        if self.db is None:
            return None
        zone = dt_util.get_default_time_zone()
        heute = jetzt().astimezone(zone).date()
        async with self._zs_sperre:
            zs = self._zs
            if zs is not None and zs.stand == self.stand and zs.heute == heute:
                return zs
            stand = self.stand
            tag_ab = (heute - timedelta(days=GEHOERT_MEIST_TAGE - 1)).isoformat()
            try:
                zuletzt = await self._lauf(self.db.zuletzt_boxen)
                meist = await self._lauf(self.db.hoerzeit_ab, tag_ab)
            except sqlite3.Error:
                _LOGGER.exception("gehoert.sqlite: Zwischenspeicher nicht gelesen")
                return self._zs
            self._zs = Zwischenspeicher(stand, heute, zuletzt, meist)
            return self._zs

    def zuletzt_gehoert_am(self, serie_id: str) -> str | None:
        """``ende_um`` der letzten Sitzung an einer Box als Zeitstempel (Vertrag W, 14.2); ``None``: noch nie. Liest den **zuletzt geladenen** Zwischenspeicher
        (die Befehle, die Listen liefern, laden ihn vorher mit ``zwischenspeicher()``)."""
        if self._zs is None:
            return None
        zeit = self._zs.zuletzt.get(serie_id)
        return None if zeit is None else iso(datetime.fromtimestamp(zeit, UTC))

    def hoerzeit_jahr(self, serie_id: str) -> int:
        return 0 if self._zs is None else self._zs.meist.get(serie_id, 0)

    def zuletzt_alle(self) -> dict[str, int]:
        return {} if self._zs is None else self._zs.zuletzt

    def meist_alle(self) -> dict[str, int]:
        return {} if self._zs is None else self._zs.meist

    # --- Technik ---------------------------------------------------------------------------------------

    async def technik_schreibe(self, box: str, zeilen: list[tuple[int, str, str | None]]) -> None:
        if self.db is None or not zeilen:
            return
        try:
            await self._lauf(self.db.technik_schreibe, box, zeilen)
        except sqlite3.Error:
            _LOGGER.exception("gehoert.sqlite: Technik-Zeile nicht geschrieben")

    # --- Aufräumen, Löschen, Umschreiben --------------------------------------------------------------------------

    async def raeume_auf(self, jetzt_s: int | None = None) -> int:
        if self.db is None:
            return 0
        jetzt_s = int(dt_util.utcnow().timestamp()) if jetzt_s is None else jetzt_s
        try:
            anzahl = await self._lauf(self.db.raeume_auf, jetzt_s)
        except sqlite3.Error:
            _LOGGER.exception("gehoert.sqlite: Aufräumen fehlgeschlagen")
            return 0
        if anzahl:
            self._geaendert()
        return anzahl

    async def loesche(self, quellen: list[str]) -> int:
        """Löscht die Zeilen konkreter Quellen und setzt die Löschmarken (Befehl 54)."""
        if self.db is None:
            return 0
        anzahl = await self._lauf(self.db.loesche, quellen, int(dt_util.utcnow().timestamp()))
        self._geaendert()
        return anzahl

    async def schreibe_um(self, zuordnung: dict[tuple[str, str], tuple[str, str]]) -> None:
        """Verschieben und Zusammenführen: ``(serie, folge)`` -> ``(neue serie, neue folge)``. Ein Fehler hier bricht das Verschieben nicht ab (Protokoll)."""
        if not zuordnung:
            return
        # Offene Reinhör-Sitzungen im Arbeitsspeicher ziehen mit (sonst schrieben sie beim Abschluss den alten Namen zurück).
        # Box-Zeilen, die erst **nach** dem Verschieben nachgeliefert werden, zählen am alten Namen: so gewollt (PL).
        self.hub.reinhoeren.schreibe_um(zuordnung)
        if self.db is None:
            return
        try:
            if await self._lauf(self.db.schreibe_um, zuordnung):
                self._geaendert()
        except sqlite3.Error:
            _LOGGER.exception("gehoert.sqlite: Umschreiben nach dem Verschieben fehlgeschlagen")


def _sekunden(s: float) -> timedelta:
    return timedelta(seconds=s)
