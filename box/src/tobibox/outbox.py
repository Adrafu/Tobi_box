"""Ereignis-Ausgang mit Bestätigung (``core-interface.md`` Abschnitt 7, ``data-model.md`` Abschnitt 4).

Führt ``<zustand>/unknown.json``. Ein Eintrag wird nur gelöscht, wenn ``bestaetigt`` mit passendem
``zuletzt`` und ``art`` kommt; der Broker allein bestätigt nichts. Jede Änderung wird sofort atomar
geschrieben (``store.schreibe_atomar``), so überlebt ein Eintrag einen Neustart.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .eventlog import logge
from .events import Eintrag, Jetzt
from .store import Ungueltig, lade_zustandsdatei, raeume_auf, schreibe_atomar

NAME = "unknown.json"
MAX_EINTRAEGE = 200
_ARTEN = ("unbekannt", "gelernt")


def zeitstempel(wall: float) -> str:
    """ISO 8601 mit Millisekunden und ``Z``: ``2026-11-05T09:12:03.412Z``."""
    t = datetime.fromtimestamp(wall, tz=timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def _parse(roh: Mapping[str, Any]) -> dict[str, Eintrag]:
    eintraege = roh.get("eintraege")
    if not isinstance(eintraege, dict):
        raise Ungueltig("schema_ungueltig", "eintraege fehlt")
    out: dict[str, Eintrag] = {}
    for uid, e in eintraege.items():
        if not isinstance(uid, str) or not uid or not isinstance(e, dict):
            raise Ungueltig("schema_ungueltig", f"Eintrag {uid!r}")
        anzahl = e.get("anzahl")
        bid = e.get("befehl_id")
        if (
            e.get("art") not in _ARTEN
            or not isinstance(e.get("zuerst"), str)
            or not isinstance(e.get("zuletzt"), str)
            or isinstance(anzahl, bool)
            or not isinstance(anzahl, int)
            or anzahl < 1
            or not isinstance(e.get("zeit_ok"), bool)
            or not (bid is None or isinstance(bid, str))
        ):
            raise Ungueltig("schema_ungueltig", f"Eintrag {uid!r}")
        out[uid] = Eintrag(uid, e["art"], e["zuerst"], e["zuletzt"], anzahl, e["zeit_ok"], bid)
    return out


def _zu_json(eintraege: Mapping[str, Eintrag]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "eintraege": {
            uid: {
                "art": e.art,
                "zuerst": e.zuerst,
                "zuletzt": e.zuletzt,
                "anzahl": e.anzahl,
                "zeit_ok": e.zeit_ok,
                "befehl_id": e.befehl_id,
            }
            for uid, e in eintraege.items()
        },
    }


class Outbox:
    def __init__(self, verzeichnis: str | Path) -> None:
        self.pfad = Path(verzeichnis) / NAME
        self._eintraege: dict[str, Eintrag] = {}
        self.quelle = "neu"

    def laden(self) -> None:
        raeume_auf(self.pfad.parent)
        self._eintraege, self.quelle = lade_zustandsdatei(self.pfad, _parse, dict, _zu_json)

    def _speichern(self) -> None:
        schreibe_atomar(self.pfad, _zu_json(self._eintraege))

    def melden(self, art: str, uid: str, befehl_id: str | None, jetzt: Jetzt) -> None:
        if art not in _ARTEN:
            raise ValueError(f"unbekannte Art {art!r}")
        ts = zeitstempel(jetzt.wall)
        alt = self._eintraege.get(uid)
        if alt is None:
            neu = Eintrag(uid, art, ts, ts, 1, jetzt.zeit_ok, befehl_id if art == "gelernt" else None)  # type: ignore[arg-type]
        elif alt.art == "gelernt" and art == "unbekannt":
            neu = Eintrag(uid, "gelernt", alt.zuerst, ts, alt.anzahl + 1, jetzt.zeit_ok, alt.befehl_id)
        else:
            bid = befehl_id if art == "gelernt" else alt.befehl_id
            neu = Eintrag(uid, art, alt.zuerst, ts, alt.anzahl + 1, jetzt.zeit_ok, bid)  # type: ignore[arg-type]
        self._eintraege[uid] = neu
        while len(self._eintraege) > MAX_EINTRAEGE:
            aeltester = min(self._eintraege.values(), key=lambda e: e.zuletzt)
            del self._eintraege[aeltester.uid]
            logge("outbox", "WARNING", "eintrag_verworfen", "voll", daten={"uid": aeltester.uid})
        self._speichern()

    def offen(self) -> list[Eintrag]:
        return list(self._eintraege.values())

    def bestaetigt(self, id: str, grund: str, zuletzt: str, art: str) -> bool:
        e = self._eintraege.get(id)
        if e is None:
            logge("outbox", "INFO", "ack", "unbekannt", daten={"uid": id, "grund": grund})
            return False
        if e.zuletzt != zuletzt or e.art != art:
            logge("outbox", "INFO", "ack_veraltet", "wirkungslos", daten={"uid": id, "grund": grund})
            return False
        del self._eintraege[id]
        self._speichern()
        logge("outbox", "INFO", "ack", "geloescht", daten={"uid": id, "grund": grund})
        return True
