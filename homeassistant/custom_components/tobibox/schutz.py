"""Rechte und Schutz für Nicht-Administratoren (Vertrag W, Abschnitte 2.1 und 2.4).

* ``Nutzer``: wer ruft (aus der WebSocket-Verbindung oder der HTTP-Anfrage). ``None`` heißt in den Funktionen des ``Hub``:
  kein Benutzer (HA-Aktionen, Eingangs-Lauf, Tests); das gilt wie ein Administrator, ohne Schutzregeln.
* ``Mengen``: gleitende Zeitfenster je Benutzer und Art (``zu_viele_aenderungen``). Administratoren sind ausgenommen.
  Die Zähler leben im Arbeitsspeicher; ein Neustart von HA vergisst sie (wie bei ``anfrage_id``).
* Papierkorb: Protokollzeile (2.4, Punkt „Papierkorb für Alltag“); die Mitteilung an Administratoren ist entfallen (AC3), die Seite zeigt das Neue.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from . import const
from .fehler import TobiboxFehler
from .util import jetzt

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

#: Zeitfenster in Sekunden
MINUTE_S = 60
ZEHN_MINUTEN_S = 600
STUNDE_S = 3600


@dataclass(frozen=True)
class Nutzer:
    """Der aufrufende HA-Benutzer."""

    id: str | None
    name: str | None
    ist_admin: bool

    @classmethod
    def aus_verbindung(cls, connection: Any) -> Nutzer:
        user = getattr(connection, "user", None)
        return cls.aus_user(user)

    @classmethod
    def aus_user(cls, user: Any) -> Nutzer:
        if user is None:
            return cls(None, None, False)
        return cls(getattr(user, "id", None), getattr(user, "name", None), bool(getattr(user, "is_admin", False)))

    @property
    def geloescht_von(self) -> dict[str, Any] | None:
        """``geloescht_von`` für ``meta.json`` und den Papierkorb-Eintrag (3.3); ohne Kennung ``None``."""
        if not self.id:
            return None
        return {"id": self.id, "name": self.name or ""}


def ist_admin(nutzer: Nutzer | None) -> bool:
    """``None`` (kein Benutzer: Aktion, System) gilt wie Administrator."""
    return nutzer is None or nutzer.ist_admin


class Mengen:
    """Gleitende Fenster: je (Art, Benutzer) die Zeitpunkte und Mengen der letzten Zeit."""

    def __init__(self) -> None:
        self._gebucht: dict[tuple[str, str], deque[tuple[float, int]]] = {}

    @staticmethod
    def _jetzt() -> float:
        return jetzt().timestamp()

    def _bereinige(self, art: str, nutzer_id: str, fenster_s: float) -> deque[tuple[float, int]]:
        d = self._gebucht.setdefault((art, nutzer_id), deque())
        grenze = self._jetzt() - fenster_s
        while d and d[0][0] <= grenze:
            d.popleft()
        if not d:
            self._gebucht.pop((art, nutzer_id), None)
        return d

    def summe(self, art: str, nutzer_id: str, fenster_s: float = STUNDE_S) -> int:
        return sum(m for _t, m in self._bereinige(art, nutzer_id, fenster_s))

    def buche(self, art: str, nutzer_id: str, menge: int = 1) -> None:
        self._gebucht.setdefault((art, nutzer_id), deque()).append((self._jetzt(), menge))

    def rest(self, art: str, nutzer_id: str, grenze: int, fenster_s: float) -> int:
        return max(0, grenze - self.summe(art, nutzer_id, fenster_s))

    def pruefe(self, art: str, nutzer: Nutzer | None, grenze: int, fenster_s: float, menge: int = 1) -> None:
        """``zu_viele_aenderungen``, wenn ``menge`` die Grenze im Fenster überschreiten würde. Bucht nichts; Administratoren sind ausgenommen."""
        if ist_admin(nutzer) or nutzer is None or not nutzer.id:
            return
        if self.summe(art, nutzer.id, fenster_s) + menge > grenze:
            raise TobiboxFehler("zu_viele_aenderungen")

    def buche_fuer(self, art: str, nutzer: Nutzer | None, menge: int = 1) -> None:
        if not ist_admin(nutzer) and nutzer is not None and nutzer.id:
            self.buche(art, nutzer.id, menge)


class Schutz:
    """Die Schutzregeln des Hubs."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.mengen = Mengen()

    # --- Rechte -----------------------------------------------------------------------------------------

    @staticmethod
    def nur_admin(nutzer: Nutzer | None) -> None:
        if not ist_admin(nutzer):
            raise TobiboxFehler("unauthorized")

    # --- Mengen (2.4) -------------------------------------------------------------------------------------

    def liste_pruefen(self, nutzer: Nutzer | None) -> None:
        """Vor einer Änderung der Liste (``zuordnung/set``, ``zuordnung/remove``, ``einstellungen/set``)."""
        self.mengen.pruefe("liste", nutzer, const.AENDERUNGEN_JE_MINUTE, MINUTE_S)

    def liste_gebucht(self, nutzer: Nutzer | None) -> None:
        """Nach einer Änderung, die nicht an einer Prüfung scheiterte (Konflikte zählen nicht)."""
        self.mengen.buche_fuer("liste", nutzer)

    def warteschlange_pruefen(self, nutzer: Nutzer | None) -> None:
        """Vor ``warteschlange/set`` und ``warteschlange/abbrechen`` (zusammen, Vertrag W, 3.13, Regel 14); Administratoren sind ausgenommen."""
        self.mengen.pruefe("warteschlange", nutzer, const.WARTESCHLANGE_AENDERUNGEN_JE_MINUTE, MINUTE_S)

    def warteschlange_gebucht(self, nutzer: Nutzer | None) -> None:
        self.mengen.buche_fuer("warteschlange", nutzer)

    def papierkorb_pruefen(self, nutzer: Nutzer | None) -> None:
        self.mengen.pruefe("papierkorb", nutzer, const.PAPIERKORB_AKTIONEN_JE_10_MIN, ZEHN_MINUTEN_S)

    def upload_rest(self, nutzer: Nutzer | None) -> int | None:
        """Wie viele Bytes der Benutzer in dieser Stunde noch hochladen darf; ``None`` = unbegrenzt (Administrator)."""
        if ist_admin(nutzer) or nutzer is None or not nutzer.id:
            return None
        return self.mengen.rest("upload_bytes", nutzer.id, const.UPLOAD_BYTES_JE_STUNDE, STUNDE_S)

    def upload_gebucht(self, nutzer: Nutzer | None, menge: int) -> None:
        if not ist_admin(nutzer) and nutzer is not None and nutzer.id:
            self.mengen.buche("upload_bytes", nutzer.id, menge)

    def cover_pruefen(self, nutzer: Nutzer | None) -> None:
        """Vor einem Foto-Upload: höchstens ``COVER_JE_STUNDE`` je Benutzer (``zu_viele_aenderungen``); Administratoren sind ausgenommen."""
        self.mengen.pruefe("cover", nutzer, const.COVER_JE_STUNDE, STUNDE_S)

    def cover_gebucht(self, nutzer: Nutzer | None) -> None:
        self.mengen.buche_fuer("cover", nutzer)

    # --- Papierkorb: Protokoll (2.4) -------------------------------------------------------

    def papierkorb_gebucht(self, nutzer: Nutzer | None, eintrag: dict[str, Any], tobies: list[dict[str, Any]]) -> None:
        """Nach jeder Papierkorb-Aktion: Zähler für die Grenze und Protokollzeile.

        Keine HA-Mitteilung (AC3): die Seite zeigt Administratoren das Neue aus ``papierkorb/list`` (``geloescht_von``, ``geloescht_am``).
        """
        self.mengen.buche_fuer("papierkorb", nutzer)
        _LOGGER.info(
            "Papierkorb: %s (%s) legt %s „%s“ in den Papierkorb (Eintrag %s, %s, %d Tobies)",
            (nutzer.name if nutzer else None) or "ohne Benutzer",
            (nutzer.id if nutzer else None) or "-",
            eintrag.get("typ"),
            eintrag.get("folge") or eintrag.get("anzeige"),
            eintrag.get("id"),
            eintrag.get("geloescht_am"),
            len(tobies),
        )
