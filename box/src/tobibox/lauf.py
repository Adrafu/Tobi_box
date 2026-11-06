"""Marker ``<zustand>/lauf.json``: welcher Tobie lag beim letzten Stand auf der Box.

``{"boot_id": <Kennung des Starts>, "uid": <Kennung des liegenden Tobies oder null>}``.
Geschrieben bei jedem Wechsel des liegenden Tobies und beim Dienst-Ende, gelöscht beim
Herunterfahren der Box. Beim Dienst-Start gilt ein Marker mit **gleicher** Kennung des Starts
als Neustart ohne Ausschalten: Der liegende Tobie startet nicht von selbst (Entscheidung G, 06.11.).
Fehlt der Marker oder ist er unlesbar, gilt Einschalten (CUJ 20).
"""

from __future__ import annotations

import json
from pathlib import Path

from .eventlog import logge

DATEI = "lauf.json"


def lese_neustart_uid(zustand: Path, boot_id: str | None) -> str | None:
    """Die Kennung des Tobies, der beim Neustart auflag; ``None`` bei Einschalten oder ohne Tobie."""
    if boot_id is None:
        return None
    try:
        roh = json.loads((Path(zustand) / DATEI).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(roh, dict) or roh.get("boot_id") != boot_id:
        return None
    uid = roh.get("uid")
    return uid if isinstance(uid, str) and uid else None


def schreibe(zustand: Path, boot_id: str | None, uid: str | None) -> bool:
    """Marker schreiben (einfaches Schreiben genügt). Ohne Kennung des Starts wird nichts geschrieben."""
    if boot_id is None:
        return False
    try:
        ordner = Path(zustand)
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / DATEI).write_text(json.dumps({"boot_id": boot_id, "uid": uid}), encoding="utf-8")
        return True
    except OSError as e:
        logge("app", "WARNING", "lauf_marker", "schreiben_fehlt", daten={"detail": repr(e)})
        return False


def loesche(zustand: Path) -> None:
    try:
        (Path(zustand) / DATEI).unlink(missing_ok=True)
    except OSError as e:
        logge("app", "WARNING", "lauf_marker", "loeschen_fehlt", daten={"detail": repr(e)})


def nachfuehren(zustand: Path, boot_id: str | None, sitzung, bisher: str | None) -> str | None:
    """Marker nachführen, wenn der liegende Tobie wechselt; gibt den neuen Stand von ``bisher`` zurück.

    Solange der Tobie vom Neustart noch erwartet wird (``sitzung.neustart_uid``), bleibt der Marker."""
    if sitzung.neustart_uid is not None:
        return bisher
    uid = sitzung.figur.uid if sitzung.figur is not None else None
    if uid != bisher and schreibe(zustand, boot_id, uid):
        return uid
    return bisher


def dienst_ende(zustand: Path, boot_id: str | None, sitzung) -> None:
    """Dienst-Ende ohne Herunterfahren: letzten Stand festhalten."""
    uid = sitzung.neustart_uid
    if uid is None and sitzung.figur is not None:
        uid = sitzung.figur.uid
    schreibe(zustand, boot_id, uid)
