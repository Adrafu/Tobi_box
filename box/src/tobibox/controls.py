"""Tasten und Drehregler -> Ereignisse für den Kern (``core-interface.md``, 3.5).

``Bedienung`` ist die reine Logik (ohne Hardware, ohne Uhr): Sie bekommt Tastenereignisse
und gibt ``Hauptknopf``, ``Weiter``, ``Zurueck`` und ``LautstaerkeDrehen`` an eine
Ausgabe-Funktion. Die Simulation (``sim``) ruft die Methoden direkt; ``GpioTreiber`` ruft sie
von gpiozero aus. Entprellen macht gpiozero (``bounce_time``), nicht diese Logik.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from . import events as ev

LANG_S = 1.5  # Hauptknopf so lange gehalten = lang (Vorgabe; im Vertrag steht kein Wert)
RASTER_PROZENT = 2  # Lautstärke-Schritt je Raster des Drehreglers

Ausgabe = Callable[[ev.Ereignis], None]


class Bedienung:
    """Wandelt Tasten und Drehregler in Ereignisse um.

    ``stand`` und ``grenze`` bilden die Lautstärke nach: ``stand`` ist der Wunsch,
    ``grenze`` die wirksame Grenze (``volume.wirksame_grenze``). Der Kern klemmt
    selbst ein zweites Mal; hier wird nur kein Schritt gesendet, der darüber hinausginge.
    """

    def __init__(
        self,
        ausgabe: Ausgabe,
        *,
        lang_s: float = LANG_S,
        raster_prozent: int = RASTER_PROZENT,
        stand: int = 0,
        grenze: int = 100,
    ) -> None:
        self._aus = ausgabe
        self.lang_s = lang_s
        self.raster_prozent = raster_prozent
        self.stand = stand
        self.grenze = grenze
        self._haupt_ab: float | None = None  # Zeit des Herunterdrückens, None: nicht gedrückt
        self._lang_gesendet = False
        self._sperre = threading.Lock()

    # -- Lautstärke nachführen (aus ``LautstaerkeGeaendert`` / ``GrenzeGesetzt`` / Start) --

    def setze_lautstaerke(self, stand: int, grenze: int) -> None:
        with self._sperre:
            self.stand, self.grenze = stand, grenze

    # -- Vor / Zurück ---------------------------------------------------------------------

    def vor(self) -> None:
        self._aus(ev.Weiter())

    def zurueck(self) -> None:
        self._aus(ev.Zurueck())

    # -- Hauptknopf -----------------------------------------------------------------------

    def haupt_runter(self, mono: float) -> None:
        with self._sperre:
            self._haupt_ab = mono
            self._lang_gesendet = False

    def haupt_hoch(self, mono: float) -> None:
        """Loslassen: kurz, wenn nicht schon lang gesendet wurde und die Zeit unter der Schwelle liegt."""
        with self._sperre:
            ab, self._haupt_ab = self._haupt_ab, None
            schon_lang = self._lang_gesendet
            self._lang_gesendet = False
        if ab is None or schon_lang:
            return
        self._aus(ev.Hauptknopf("lang" if mono - ab >= self.lang_s else "kurz"))

    def tick(self, mono: float) -> None:
        """Während der Knopf unten ist: nach ``lang_s`` sofort ``lang`` senden (ohne Loslassen)."""
        with self._sperre:
            faellig = self._haupt_ab is not None and not self._lang_gesendet and mono - self._haupt_ab >= self.lang_s
            if faellig:
                self._lang_gesendet = True
        if faellig:
            self._aus(ev.Hauptknopf("lang"))

    def haupt_gehalten(self) -> None:
        """Für Treiber mit eigenem Halte-Timer (gpiozero ``when_held``): lang, einmal je Druck."""
        with self._sperre:
            if self._haupt_ab is None or self._lang_gesendet:
                return
            self._lang_gesendet = True
        self._aus(ev.Hauptknopf("lang"))

    # -- Drehregler -----------------------------------------------------------------------

    def drehen(self, raster: int) -> None:
        """``raster`` Raster im Uhrzeigersinn (positiv, lauter) oder dagegen (negativ)."""
        self.drehen_prozent(raster * self.raster_prozent)

    def drehen_prozent(self, prozent: int) -> None:
        """Wie ``drehen``, aber in Prozentpunkten (``tobibox sim regler``: derselbe Weg wie die Hardware, B14)."""
        if prozent == 0:
            return
        with self._sperre:
            if prozent > 0 and self.stand >= self.grenze:
                return  # lauter geht nicht über die Grenze
            neu = max(0, min(self.stand + prozent, self.grenze))
            delta = neu - self.stand
            if delta == 0:
                return  # schon an der Grenze (oder bei 0)
            self.stand = neu
        self._aus(ev.LautstaerkeDrehen(delta))


class GpioTreiber:
    """Echte Hardware über gpiozero hinter derselben ``Bedienung``.

    ``fabrik`` ist das Modul ``gpiozero`` (oder eine Attrappe mit ``Button`` und
    ``RotaryEncoder``); ohne Angabe wird ``gpiozero`` erst beim Start geladen. Die Pins sind
    BCM-Nummern. Der Hauptknopf kommt auf dem Pi über den PiSugar (Plan, Punkt 4); hier steht
    der Anschluss für einen Knopf direkt am GPIO, sonst bleibt ``pin_haupt`` leer.
    """

    def __init__(
        self,
        bedienung: Bedienung,
        *,
        pin_vor: int,
        pin_zurueck: int,
        pin_dreh_a: int,
        pin_dreh_b: int,
        pin_haupt: int | None = None,
        fabrik: Any = None,
        uhr: Callable[[], float] | None = None,
    ) -> None:
        self.b = bedienung
        self._pins = (pin_vor, pin_zurueck, pin_dreh_a, pin_dreh_b, pin_haupt)
        self._fabrik = fabrik
        if uhr is None:
            import time

            uhr = time.monotonic
        self._uhr = uhr
        self.geraete: list[Any] = []

    def start(self) -> None:
        g = self._fabrik
        if g is None:
            import gpiozero as g  # nur auf dem Pi vorhanden
        vor, zurueck, a, b, haupt = self._pins
        erzeugt: list[Any] = []
        try:
            # bounce_time: Entprellen im Treiber
            tv = g.Button(vor, pull_up=True, bounce_time=0.03)
            erzeugt.append(tv)
            tv.when_pressed = self.b.vor
            tz = g.Button(zurueck, pull_up=True, bounce_time=0.03)
            erzeugt.append(tz)
            tz.when_pressed = self.b.zurueck
            dreh = g.RotaryEncoder(a, b, max_steps=0)
            erzeugt.append(dreh)
            dreh.when_rotated_clockwise = lambda: self.b.drehen(1)
            dreh.when_rotated_counter_clockwise = lambda: self.b.drehen(-1)
            if haupt is not None:
                th = g.Button(haupt, pull_up=True, bounce_time=0.03, hold_time=self.b.lang_s)
                erzeugt.append(th)
                th.when_pressed = lambda: self.b.haupt_runter(self._uhr())
                th.when_held = self.b.haupt_gehalten
                th.when_released = lambda: self.b.haupt_hoch(self._uhr())
        except BaseException:
            # Teilfehler (Pin belegt, fehlendes Recht): schon erzeugte Geräte schließen, sonst bleiben ihre Pins belegt (B17)
            for g_ in erzeugt:
                try:
                    g_.close()
                except Exception:  # noqa: BLE001
                    pass
            self.geraete = []
            raise
        self.geraete = erzeugt

    def stop(self) -> None:
        for g in self.geraete:
            g.close()
        self.geraete = []
