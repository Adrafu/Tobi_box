"""Kleine Hilfen: Zeitstempel, Kennungen, Fingerabdruck."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from homeassistant.util import dt as dt_util


def jetzt() -> datetime:
    """Aktuelle Zeit in UTC (über HA, damit Tests die Uhr einfrieren können)."""
    return dt_util.utcnow()


def iso(zeit: datetime, millis: bool = False) -> str:
    """``2026-11-05T09:30:00Z`` (Sekunden) oder mit Millisekunden."""
    zeit = zeit.astimezone(UTC)
    if millis:
        return zeit.strftime("%Y-%m-%dT%H:%M:%S.") + f"{zeit.microsecond // 1000:03d}Z"
    return zeit.strftime("%Y-%m-%dT%H:%M:%SZ")


def jetzt_iso() -> str:
    return iso(jetzt())


def parse_iso(text: Any) -> datetime | None:
    """Liest ``2026-11-05T09:30:00Z`` (auch mit Millisekunden); sonst ``None``."""
    if not isinstance(text, str):
        return None
    try:
        zeit = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return zeit if zeit.tzinfo else zeit.replace(tzinfo=UTC)


def neue_id12() -> str:
    """Zufällige Kennung aus 12 Zeichen ``[0-9a-f]`` (Serien-ID, Papierkorb-Eintrag)."""
    return secrets.token_hex(6)


def neue_liste_id() -> str:
    """Zufällige Listen-ID aus 16 Zeichen ``[0-9a-f]``."""
    return secrets.token_hex(8)


def neue_uuid() -> str:
    return str(uuid.uuid4())


def fingerabdruck(daten: Any) -> str:
    """16 Zeichen ``[0-9a-f]`` über kanonisches JSON (für ``stand``)."""
    text = json.dumps(daten, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
