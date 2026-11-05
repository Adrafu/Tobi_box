"""Ereignisprotokoll: Python ``logging`` mit JSON-Formatter (``data-model.md``, 8).

Eine JSON-Zeile je Ereignis. Pi: nach stdout (journald). Mac: rotierende Datei
mit fester Obergrenze. Die Vorgangs-ID ist ein Log-Feld. Geheimnisse werden nie
protokolliert: Felder mit verdächtigen Namen werden durch ``***`` ersetzt.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any

from . import events as ev

LOGGER_NAME = "tobibox"
DATEI_MAX_BYTES = 1_000_000  # 1 MB je Datei (data-model.md, 8)
DATEI_ANZAHL = 5  # bis zu 5 Dateien

EBENEN = ("DEBUG", "INFO", "WARNING", "ERROR")
ZEITQUELLEN = ("system", "rtc", "ntp", "unbekannt")

#: Schlüsselnamen, die ganz oder als Endung (``mqtt_passwort``, ``api_key``) als geheim gelten.
_GEHEIM = ("passwort", "password", "token", "secret", "key")
_MAX_TIEFE = 8


def _geheim(name: object) -> bool:
    """Ganzer Schlüsselname oder Endung ``_<name>`` / ``-<name>`` (nicht Teilstrings wie ``monkey``)."""
    n = str(name).lower()
    return any(n == t or n.endswith("_" + t) or n.endswith("-" + t) for t in _GEHEIM)


def _bereinige(wert: Any, tiefe: int = 0) -> Any:
    """Ersetzt Werte geheimer Schlüssel durch ``***``, rekursiv in Objekten und Listen.

    Grenze: Nur Schlüsselnamen werden geprüft. Freitext-Werte (z. B. eine
    Fehlermeldung mit einem Passwort darin) werden nicht durchsucht.
    """
    if tiefe > _MAX_TIEFE:
        return "…"
    if isinstance(wert, Mapping):
        return {k: ("***" if _geheim(k) else _bereinige(v, tiefe + 1)) for k, v in wert.items()}
    if isinstance(wert, (list, tuple)):
        return [_bereinige(v, tiefe + 1) for v in wert]
    return wert


def zeitstempel(wall: float) -> str:
    """ISO 8601, UTC, mit Millisekunden: ``2026-11-05T09:30:00.123Z``."""
    dt = datetime.fromtimestamp(wall, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


class JsonFormatter(logging.Formatter):
    """Formatiert einen ``LogRecord`` als Zeile nach ``data-model.md``, 8.

    Die Felder stehen im Record (``extra``): ``baustein``, ``ereignis``,
    ``ergebnis``, optional ``vorgang``, ``sim``, ``daten``. Zeit, Monotonuhr und
    Zeitquelle kommen aus ``uhr`` (Vorgabe: Systemuhr), damit Tests feste
    Werte setzen können.
    """

    def __init__(self, uhr: Callable[[], tuple[float, float, str]] | None = None) -> None:
        super().__init__()
        self._uhr = uhr

    def format(self, record: logging.LogRecord) -> str:
        try:
            # unpaarige Ersatzzeichen (Dateinamen mit ungültigem UTF-8) lesbar machen
            return self._format(record).encode("utf-8", "backslashreplace").decode("utf-8")
        except Exception:  # Protokollieren darf nie werfen
            try:
                ereignis = str(getattr(record, "ereignis", "meldung"))
            except Exception:
                ereignis = "meldung"
            return json.dumps(
                {"zeit": zeitstempel(time.time()), "ebene": "ERROR", "baustein": "eventlog",
                 "ereignis": "format_fehler", "ergebnis": "fehler", "meldung": ereignis},
                ensure_ascii=False, separators=(",", ":"),
            )

    def _format(self, record: logging.LogRecord) -> str:
        if self._uhr is not None:
            wall, mono, quelle = self._uhr()
        else:
            wall, mono, quelle = record.created, time.monotonic(), "system"
        zeile: dict[str, Any] = {
            "zeit": zeitstempel(wall),
            "mono": round(mono, 3),
            "zeitquelle": getattr(record, "zeitquelle", quelle),
            "ebene": record.levelname if record.levelname in EBENEN else "INFO",
            "baustein": getattr(record, "baustein", record.name.rsplit(".", 1)[-1]),
            "ereignis": getattr(record, "ereignis", "meldung"),
            "ergebnis": getattr(record, "ergebnis", "ok"),
        }
        vorgang = getattr(record, "vorgang", None)
        if vorgang:
            zeile["vorgang"] = vorgang
        if getattr(record, "sim", False):
            zeile["sim"] = True
        text = getattr(record, "meldung", None)
        if text is None and not hasattr(record, "ereignis"):
            text = record.getMessage()
        if text:
            zeile["meldung"] = text
        daten = getattr(record, "daten", None)
        if daten:
            zeile["daten"] = _bereinige(daten)
        return json.dumps(zeile, ensure_ascii=False, separators=(",", ":"), default=str)


def logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def logge(
    baustein: str,
    ebene: str,
    ereignis: str,
    ergebnis: str = "ok",
    vorgang: str | None = None,
    *,
    meldung: str | None = None,
    sim: bool = False,
    zeitquelle: str | None = None,
    daten: Mapping[str, Any] | None = None,
) -> None:
    """Eine Protokollzeile schreiben (Weg für alle Bausteine mit Ein-/Ausgabe).

    ``daten`` ist ein ausdrückliches Objekt (kein ``**``), damit Schlüssel wie
    ``ebene`` oder ``meldung`` nicht mit Parametern kollidieren. Wirft nie.
    """
    try:
        _logge(baustein, ebene, ereignis, ergebnis, vorgang, meldung, sim, zeitquelle, daten)
    except Exception:
        pass


def _logge(baustein, ebene, ereignis, ergebnis, vorgang, meldung, sim, zeitquelle, daten) -> None:  # type: ignore[no-untyped-def]
    extra: dict[str, Any] = {"baustein": baustein, "ereignis": ereignis, "ergebnis": ergebnis}
    if vorgang:
        extra["vorgang"] = vorgang
    if sim:
        extra["sim"] = True
    if meldung:
        extra["meldung"] = meldung
    if zeitquelle:
        extra["zeitquelle"] = zeitquelle
    if daten:
        extra["daten"] = dict(daten)
    logger().log(getattr(logging, ebene, logging.INFO), "%s", ereignis, extra=extra)


def logge_befehl(befehl: ev.Protokoll, *, sim: bool = False, zeitquelle: str | None = None) -> None:
    """Den Kernbefehl ``Protokoll`` ausführen."""
    logge(
        befehl.baustein,
        befehl.ebene,
        befehl.ereignis,
        befehl.ergebnis,
        befehl.vorgang,
        sim=sim,
        zeitquelle=zeitquelle,
        daten=befehl.daten,
    )


def einrichten(
    *,
    ziel: str = "stdout",
    datei: str | Path | None = None,
    ebene: str = "INFO",
    max_bytes: int = DATEI_MAX_BYTES,
    anzahl: int = DATEI_ANZAHL,
    strom: IO[str] | None = None,
    uhr: Callable[[], tuple[float, float, str]] | None = None,
) -> logging.Logger:
    """Handler setzen: ``ziel="stdout"`` (Pi) oder ``ziel="datei"`` (Mac).

    Ersetzt vorhandene Handler des Loggers (mehrfaches Aufrufen ist sicher).
    """
    if ziel not in ("stdout", "datei"):
        raise ValueError(f"unbekanntes Protokollziel: {ziel!r}")
    log = logger()
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    handler: logging.Handler
    if ziel == "stdout":
        handler = logging.StreamHandler(strom if strom is not None else sys.stdout)
    else:
        if datei is None:
            raise ValueError("Protokollziel 'datei' braucht einen Dateinamen")
        pfad = Path(datei)
        pfad.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            pfad, maxBytes=max_bytes, backupCount=max(0, anzahl - 1), encoding="utf-8"
        )
    handler.setFormatter(JsonFormatter(uhr))
    log.addHandler(handler)
    log.setLevel(getattr(logging, ebene, logging.INFO))
    log.propagate = False
    return log
