"""Die eine Regel, ob ein Medien-Sync laufen darf (Design „Netz, Sync, Strom“, Entscheidung C, CUJ 12).

Es gibt sie **nur hier**. ``power`` (``sync_erlaubt``) und ``sync`` (``regel_erlaubt``) benutzen diese Funktion;
keiner von beiden hat eine eigene Fassung. Das Modul importiert nichts aus dem Dienst, damit ``sync`` weiter
ohne ``net`` und ``power`` auskommt.

Regel:

* ``home``: erlaubt.
* ``hotspot``: nur mit Lader **oder** Akku über ``HOTSPOT_AKKU_MIN_PROZENT`` (genau 50 % reicht nicht). Ist der
  Lader unbekannt und der Akku unbekannt oder zu niedrig, ist der Sync nicht erlaubt: lieber kein Sync als ein leerer Akku.
* ``offline`` (und jede unbekannte oder noch nicht gemessene Klasse): nie.
"""

from __future__ import annotations

#: Im Hotspot läuft der Sync nur, wenn der Lader dran ist oder der Akku **über** diesem Wert liegt.
HOTSPOT_AKKU_MIN_PROZENT = 50


def sync_erlaubt(klasse: str | None, am_lader: bool | None, akku_prozent: int | None) -> tuple[bool, str]:
    """Darf ein Sync laufen? Gibt ``(erlaubt, grund)``; ``grund`` ist ``"ok"``, ``"regel"`` (Hotspot ohne Lader und
    ohne genug Akku) oder ``"netz_weg"`` (offline).

    Ein Sync, der von der Regel nicht zugelassen wird, meldet ``SyncAbgebrochen("regel")`` (``core-interface.md``);
    ``"netz_weg"`` ist der Grund, wenn das Netz während eines laufenden Syncs wegfällt."""
    if klasse == "home":
        return True, "ok"
    if klasse == "hotspot":
        if am_lader is True or (akku_prozent is not None and akku_prozent > HOTSPOT_AKKU_MIN_PROZENT):
            return True, "ok"
        return False, "regel"
    return False, "netz_weg"
