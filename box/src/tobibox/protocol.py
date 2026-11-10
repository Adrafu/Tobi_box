"""Zeilen-Parser nach ``docs/protocol/reader-v1.md`` (Abschnitte 2, 3, 4, 7, 11).

Reine Funktionen ohne Ein-/Ausgabe. ``parse_zeile`` bekommt eine Zeile als
``str`` (ohne ``\\n``; ein ``\\r`` am Ende wird entfernt). Wer Bytes liest,
dekodiert mit ``latin-1``, damit jedes Byte außerhalb 0x20 bis 0x7E als
``not_ascii`` erkannt wird.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PROTO_UNTERSTUETZT = frozenset({1})
MAX_ZEILE = 200
MAX_DETAIL = 80

TYPEN = ("HELLO", "PLACED", "LOCKED", "REMOVED", "HB", "LADER", "ERR")

#: Pflichtfelder je Zeilentyp in der Reihenfolge der Zeilentabelle.
FELDER: dict[str, tuple[str, ...]] = {
    "HELLO": ("proto", "fw", "build", "pn5180"),
    "PLACED": ("uid", "type", "tonie", "seq"),
    "LOCKED": ("seq",),
    "REMOVED": ("seq",),
    "HB": ("up", "present", "polls", "hits", "rejected", "errors", "cycle_ms"),
    "LADER": ("in",),
    "ERR": ("code", "detail"),
}

#: Optionale Felder am Ende bekannter Zeilen (Ein/Aus, 10.11.). Fehlt eines, fehlt es auch in ``Zeile.felder``. Ist sein Wert ungültig,
#: wird es wie ein fehlendes behandelt (V9): Die Zeile bleibt gültig, ``Zeile.verworfen`` nennt das Feld.
OPTIONAL: dict[str, tuple[str, ...]] = {"HELLO": ("caps",)}

#: Feste Zuordnung Fehlercode -> Schwere (Abschnitt 7). Unbekannt: ``warnung``.
SCHWERE: dict[str, str] = {
    "pn5180_no_response": "fehler",
    "pn5180_timeout": "fehler",
    "bad_response": "warnung",
    "uid_invalid": "warnung",
    "unlock_failed": "hinweis",
    "bad_command": "hinweis",
    "internal": "fehler",
}

_SCHLUESSEL = re.compile(r"[a-z][a-z0-9_]*")
_UINT = re.compile(r"0|[1-9][0-9]{0,9}")
_UID = re.compile(r"[0-9a-f]{8}|[0-9a-f]{14}|[0-9a-f]{20}|[0-9a-f]{16}")
_FW = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?")
_BUILD = re.compile(r"([0-9a-f]{7,12}(-dirty)?)|unknown")
_PN5180 = re.compile(r"([0-9]+\.[0-9]+)|unknown")
_CAPS_NAME = re.compile(r"[a-z][a-z0-9_]{0,15}")
MAX_CAPS = 5
_CODE = re.compile(r"[a-z][a-z0-9_]{0,31}")


class ZeilenFehler(ValueError):
    """Ungültige Zeile; ``grund`` ist einer der Gründe aus ``reader-v1-examples.txt``."""

    def __init__(self, grund: str) -> None:
        super().__init__(grund)
        self.grund = grund


@dataclass(frozen=True, slots=True)
class Zeile:
    """Eine gültige Zeile.

    ``felder`` enthält genau die bekannten Felder in der Reihenfolge der
    Zeilentabelle; ``unbekannt`` nennt Zusatzfelder, die ignoriert wurden.
    """

    typ: str
    felder: dict[str, str]
    unbekannt: tuple[str, ...] = ()
    #: optionale Felder mit ungültigem Wert; sie fehlen in ``felder`` (V9, Ein/Aus, 10.11.)
    verworfen: tuple[str, ...] = ()


def _uint(wert: str, maximum: int = 4294967295, minimum: int = 0) -> bool:
    return _UINT.fullmatch(wert) is not None and minimum <= int(wert) <= maximum


def _pruefe_wert(typ: str, name: str, wert: str) -> str | None:
    """``None`` wenn gültig, sonst der Grund (``bad_value`` oder ``bad_uid``)."""
    if name == "uid":
        return None if _UID.fullmatch(wert) else "bad_uid"
    ok: bool
    if name == "proto":
        ok = _uint(wert, minimum=1)
    elif name == "fw":
        ok = len(wert) <= 24 and _FW.fullmatch(wert) is not None
    elif name == "build":
        ok = _BUILD.fullmatch(wert) is not None
    elif name == "pn5180":
        ok = _PN5180.fullmatch(wert) is not None
    elif name == "in":
        ok = wert in ("0", "1")
    elif name == "caps":
        namen = wert.split(",")
        ok = len(namen) <= MAX_CAPS and all(_CAPS_NAME.fullmatch(n) for n in namen)
    elif name == "type":
        ok = wert in ("ntag", "iso15693")
    elif name == "tonie" or name == "present":
        ok = wert in ("0", "1")
    elif name == "cycle_ms":
        ok = _uint(wert, 65535)
    elif name == "code":
        ok = _CODE.fullmatch(wert) is not None
    elif name == "detail":
        ok = 1 <= len(wert) <= MAX_DETAIL and "|" not in wert and ";" not in wert
    else:  # seq, up, polls, hits, rejected, errors
        ok = _uint(wert)
    return None if ok else "bad_value"


def _passt_zusammen(uid: str, typ: str, tonie: str) -> bool:
    if typ == "ntag":
        return len(uid) in (8, 14, 20) and tonie == "0"
    return len(uid) == 16 and tonie == ("1" if uid.startswith("e00403") else "0")


def parse_zeile(zeile: str) -> Zeile:
    """Zeile prüfen und zerlegen; bei Fehler ``ZeilenFehler`` mit dem Grund."""
    if zeile.endswith("\r"):
        zeile = zeile[:-1]
    if zeile == "":
        raise ZeilenFehler("empty_line")
    if len(zeile) > MAX_ZEILE:
        raise ZeilenFehler("too_long")
    if any(not 0x20 <= ord(c) <= 0x7E for c in zeile):
        raise ZeilenFehler("not_ascii")
    if zeile[0] == " ":
        raise ZeilenFehler("bad_syntax")
    typ = zeile.split(" ", 1)[0]
    if typ not in TYPEN:
        raise ZeilenFehler("unknown_type")

    # ERR: detail= ist der Rest der Zeile (auch mit Leerzeichen und '=')
    detail: str | None = None
    kopf = zeile
    if typ == "ERR":
        i = zeile.find(" detail=")
        if i >= 0:
            detail = zeile[i + len(" detail="):]
            kopf = zeile[:i]
            if detail == "":
                raise ZeilenFehler("bad_syntax")

    woerter = kopf.split(" ")
    if any(w == "" for w in woerter):
        raise ZeilenFehler("bad_syntax")
    gefunden: dict[str, str] = {}
    for wort in woerter[1:]:
        if "=" not in wort:
            raise ZeilenFehler("bad_syntax")
        schluessel, wert = wort.split("=", 1)
        if _SCHLUESSEL.fullmatch(schluessel) is None:
            raise ZeilenFehler("bad_syntax")
        if wert == "":
            if schluessel in OPTIONAL.get(typ, ()):
                continue  # leeres optionales Feld: wie fehlend (V9)
            raise ZeilenFehler("bad_syntax")
        if schluessel in gefunden or (detail is not None and schluessel == "detail"):
            raise ZeilenFehler("duplicate_key")
        gefunden[schluessel] = wert
    if detail is not None:
        gefunden["detail"] = detail

    pflicht = FELDER[typ]
    if any(f not in gefunden for f in pflicht):
        raise ZeilenFehler("missing_field")
    for f in pflicht:
        grund = _pruefe_wert(typ, f, gefunden[f])
        if grund is not None:
            raise ZeilenFehler(grund)
    if typ == "PLACED" and not _passt_zusammen(gefunden["uid"], gefunden["type"], gefunden["tonie"]):
        raise ZeilenFehler("uid_type_mismatch")

    felder = {f: gefunden[f] for f in pflicht}
    verworfen: list[str] = []
    for f in OPTIONAL.get(typ, ()):
        if f in gefunden:
            if _pruefe_wert(typ, f, gefunden[f]) is None:
                felder[f] = gefunden[f]
            else:
                verworfen.append(f)
    bekannt = set(felder) | set(verworfen)
    unbekannt = tuple(k for k in gefunden if k not in bekannt)
    return Zeile(typ, felder, unbekannt, tuple(verworfen))


def schwere(code: str) -> str:
    """Schwere eines Fehlercodes (``fehler``, ``warnung``, ``hinweis``)."""
    return SCHWERE.get(code, "warnung")


def pruefe_befehl(zeile: str) -> str:
    """Befehls-Parser der Firmware-Seite (Abschnitt 8); gibt ``"PING"`` zurück.

    Fehler: ``ZeilenFehler`` mit ``empty_line``, ``too_long``, ``not_ascii`` oder
    ``bad_command``. Der Box-Dienst selbst sendet nur ``PING``.
    """
    if zeile.endswith("\r"):
        zeile = zeile[:-1]
    if zeile == "":
        raise ZeilenFehler("empty_line")
    if len(zeile) > MAX_ZEILE:
        raise ZeilenFehler("too_long")
    if any(not 0x20 <= ord(c) <= 0x7E for c in zeile):
        raise ZeilenFehler("not_ascii")
    if zeile == "PING":
        return "PING"
    raise ZeilenFehler("bad_command")


PING_ZEILE = b"PING\n"
