"""Der Strom-Wert aus zwei Quellen (``core-interface.md``, Abschnitt 9, Punkt 9; Ein/Aus, 10.11.).

„Strom“ heißt Strom am Eingang der Box aus jeder Quelle (Netzteil, Sockel, Kabel, Powerbank, Auto). Zwei Quellen liefern ihn:
``pisugar-server`` (``power``) und der Leser (Zeile ``LADER``, ``reader``). **Bei Widerspruch gilt der Leser.** Hängt
``pisugar-server``, liefert der Leser den Wert allein. Eine Quelle, die nach einem bekannten Wert schweigt, behält ihren letzten Wert.

Eine Quelle für ``idle`` (Frist, Andocken), ``led`` (Farbe der Akku-Anzeige), den Statussammler (Feld ``lader``) und ``app`` (Regel des
Syncs): Jeder führt die Werte mit **demselben** Code zusammen, nicht mit einer Kopie.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import events as ev


@dataclass(frozen=True, slots=True)
class StromQuellen:
    """Der letzte Wert je Quelle; ``None``: diese Quelle hat noch nichts geliefert."""

    pisugar: bool | None = None
    leser: bool | None = None

    def mit(self, e: ev.LaderGeaendert) -> StromQuellen:
        if e.quelle == "leser":
            return StromQuellen(self.pisugar, e.am_lader)
        return StromQuellen(e.am_lader, self.leser)

    @property
    def wert(self) -> bool | None:
        """Der zusammengeführte Wert: der des Lesers, solange er einen geliefert hat, sonst der von ``pisugar``; ``None``: unbekannt."""
        return self.leser if self.leser is not None else self.pisugar

    @property
    def widerspruch(self) -> bool:
        return self.pisugar is not None and self.leser is not None and self.pisugar != self.leser
