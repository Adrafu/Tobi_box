"""Dateizugriffe auf die NAS-Freigabe: atomar schreiben, ohne Überschreiben verschieben (Vertrag W, 5.2, 11.11).

Alles synchron; HA ruft es über ``hass.async_add_executor_job``.
"""

from __future__ import annotations

import errno
import json
import os
import secrets
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .const import ENDUNGEN


class ZielExistiert(FileExistsError):
    """Das Ziel gibt es schon; nichts wurde überschrieben."""


def serialisiere(inhalt: Mapping[str, Any]) -> bytes:
    """JSON nach ``data-model.md`` 1.1: UTF-8, 2 Leerzeichen, ``schema_version`` zuerst (falls vorhanden)."""
    obj = dict(inhalt)
    kopf = {"schema_version": obj.pop("schema_version")} if "schema_version" in obj else {}
    text = json.dumps({**kopf, **obj}, indent=2, ensure_ascii=False, allow_nan=False)
    return (text + "\n").encode("utf-8")


def fsync_verzeichnis(pfad: Path) -> None:
    try:
        fd = os.open(pfad, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def schreibe_json_atomar(pfad: Path, inhalt: Mapping[str, Any]) -> None:
    """``.tmp`` -> ``fsync`` -> umbenennen (auf dem NAS genügt das, ``data-model.md`` Abschnitt 5)."""
    daten = serialisiere(inhalt)
    tmp = pfad.with_name(f"{pfad.name}.{secrets.token_hex(4)}.tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(daten)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, pfad)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    fsync_verzeichnis(pfad.parent)


def lese_json(pfad: Path) -> Any:
    """Liest JSON; wirft ``OSError`` oder ``ValueError``."""
    with open(pfad, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def verschiebe_ohne_ueberschreiben(quelle: Path, ziel: Path) -> None:
    """Verschiebt eine Datei oder einen Ordner auf derselben Freigabe, **ohne** etwas zu überschreiben.

    Dateien: ``os.link`` und danach die Quelle löschen (atomar, scheitert mit ``FileExistsError``). Bietet das
    Dateisystem keine harten Verweise (SMB), wird unter dem Aufruferschutz (Sperre des Eingangs) geprüft und
    dann umbenannt. Ordner: prüfen und umbenennen. ``ZielExistiert``, wenn das Ziel schon da ist.
    """
    if os.path.lexists(ziel):
        raise ZielExistiert(str(ziel))
    if quelle.is_file() and not quelle.is_symlink():
        try:
            os.link(quelle, ziel)
        except FileExistsError as err:
            raise ZielExistiert(str(ziel)) from err
        except OSError as err:
            if err.errno not in (errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EXDEV, errno.EACCES, errno.EMLINK, errno.ENOSYS):
                raise
        else:
            try:
                quelle.unlink()
            except OSError:
                # Quelle bleibt: Ziel ist vollständig, die Quelle wird beim nächsten Durchlauf als Doppeltes erkannt
                pass
            return
    if os.path.lexists(ziel):  # pragma: no cover - Wettlauf zwischen Prüfung und Umbenennen
        raise ZielExistiert(str(ziel))
    os.rename(quelle, ziel)


def ordner_groesse(pfad: Path) -> tuple[int, int]:
    """``(Anzahl Dateien, Summe der Bytes)`` unterhalb von ``pfad`` (ohne Dotfiles)."""
    anzahl = 0
    summe = 0
    for wurzel, ordner, dateien in os.walk(pfad):
        ordner[:] = [o for o in ordner if not o.startswith(".")]
        for d in dateien:
            if d.startswith("."):
                continue
            try:
                summe += os.stat(os.path.join(wurzel, d)).st_size
            except OSError:
                continue
            anzahl += 1
    return anzahl, summe


def zaehle_audio(pfad: Path) -> int:
    """Anzahl der Audiodateien unterhalb von ``pfad`` (ohne Dotfiles)."""
    anzahl = 0
    for _wurzel, ordner, namen in os.walk(pfad):
        ordner[:] = [o for o in ordner if not o.startswith(".")]
        anzahl += sum(1 for n in namen if ist_audio(n))
    return anzahl


def ist_audio(name: str) -> bool:
    """Kein Dotfile und eine erlaubte Endung (``data-model.md`` Abschnitt 5)."""
    return not name.startswith(".") and name.rpartition(".")[2].lower() in ENDUNGEN and "." in name


def tracks_in_ordner(pfad: Path) -> list[str]:
    """Die Audiodateien direkt im Ordner (ein Folgen-Ordner hat keine weitere Verschachtelung)."""
    try:
        return [e.name for e in os.scandir(pfad) if e.is_file() and ist_audio(e.name)]
    except OSError:
        return []


def loesche_baum(pfad: Path) -> int:
    """Löscht Datei oder Ordner endgültig; gibt die Bytes zurück."""
    groesse = 0
    if pfad.is_dir() and not pfad.is_symlink():
        groesse = ordner_groesse(pfad)[1]
        shutil.rmtree(pfad)
    else:
        try:
            groesse = pfad.stat().st_size
        except OSError:
            groesse = 0
        pfad.unlink(missing_ok=True)
    return groesse


def freier_platz(pfad: Path) -> int:
    return shutil.disk_usage(pfad).free


def zufall_hex(n: int = 8) -> str:
    return secrets.token_hex(n)
