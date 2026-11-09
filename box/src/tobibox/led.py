"""LED-Ring: Zustand der Box -> Bild des Rings (reine Logik, keine Ein-/Ausgabe).

Quellen: Projektplan 5.5.2 (Zustände läuft, Pause, Akku, unbekannte Karte, Aufwachen),
Design CUJ 18, ``core-interface.md`` (``ZustandMelden`` ist die Anzeige-Eingabe des Rings).
Der echte APA102-Treiber und die Browser-Simulation bekommen dasselbe Bild:

* ``Ring.als_dict()``: JSON-fähig, für Simulation, Terminal und Protokoll.
* ``Ring.apa102_rahmen()``: die Bytes für den echten Ring.

Das Bild ist eine Funktion der Zeit (Atmen, Blinken, Lauflicht). Wer es zeichnet, ruft
``LedLogik.ring(jetzt_mono)`` im eigenen Takt auf (z. B. alle 50 ms).

Der Helligkeitsdeckel gilt immer: ``Ring`` klemmt seine Helligkeit selbst auf ``DECKEL_PROZENT``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from . import events as ev

ANZAHL = 40  # LEDs im Ring (APA102)
DECKEL_PROZENT = 25  # Helligkeit nie darüber (Plan 5.5.3)
APA102_MAX = 31  # 5 Bit globale Helligkeit
# größter 5-Bit-Wert, der noch unter dem Deckel liegt (abgerundet): 7 von 31 = 22,6 %
APA102_DECKEL = APA102_MAX * DECKEL_PROZENT // 100

# Zustandsnamen (Kennungen für Simulation und Protokoll)
AUS = "aus"
LAEUFT = "laeuft"
PAUSE = "pause"
AKKU = "akku"
UNBEKANNTE_KARTE = "unbekannte_karte"
AUFWACHEN = "aufwachen"
ZUSTAENDE = (AUS, LAEUFT, PAUSE, AKKU, UNBEKANNTE_KARTE, AUFWACHEN)

# Zeiten in Sekunden
AUFWACHEN_S = 2.0  # Lauflicht beim Aufwachen
AKKU_ANZEIGE_S = 5.0  # Akku-Anzeige nach Anforderung oder Laderwechsel
ATMEN_S = 6.0  # Periode beim Atmen (läuft)
BLINK_UNBEKANNT_S = 1.0  # Periode Blinken (unbekannte Karte)
BLINK_TIEFSTAND_S = 0.5  # Periode Blinken (Akku-Tiefstand)
KOMET_LAENGE = 10  # LEDs im Schweif des Lauflichts
KOMET_RUNDEN = 2

Farbe = tuple[int, int, int]
SCHWARZ: Farbe = (0, 0, 0)
GRUEN: Farbe = (0, 255, 70)
BERNSTEIN: Farbe = (255, 110, 0)
MAGENTA: Farbe = (255, 0, 120)
GELB: Farbe = (255, 190, 0)
ROT: Farbe = (255, 0, 0)
BLAU: Farbe = (0, 150, 255)
WARMWEISS: Farbe = (255, 200, 120)


def _byte(x: float) -> int:
    return max(0, min(255, int(round(x))))


@dataclass(frozen=True, slots=True)
class Ring:
    """Ein Bild des Rings: Farbe je LED und eine gemeinsame Helligkeit in Prozent (0 bis 25)."""

    zustand: str
    leds: tuple[Farbe, ...]
    helligkeit: float

    def __post_init__(self) -> None:
        if len(self.leds) != ANZAHL:
            raise ValueError(f"Ring braucht genau {ANZAHL} LEDs")
        # Deckel: wird hier erzwungen, egal was die Logik rechnet
        object.__setattr__(self, "helligkeit", max(0.0, min(float(DECKEL_PROZENT), float(self.helligkeit))))

    def sichtbar(self) -> list[Farbe]:
        """Farben, wie sie leuchten (Farbe mal Helligkeit / 100); für das Zeichnen im Browser."""
        f = self.helligkeit / 100.0
        return [(_byte(r * f), _byte(g * f), _byte(b * f)) for r, g, b in self.leds]

    def als_dict(self) -> dict[str, Any]:
        """JSON-fähige Form: ``{"zustand", "helligkeit", "deckel", "leds": [[r, g, b] * 40]}``."""
        return {
            "zustand": self.zustand,
            "helligkeit": round(self.helligkeit, 2),
            "deckel": DECKEL_PROZENT,
            "leds": [list(c) for c in self.leds],
        }

    def apa102_rahmen(self) -> bytes:
        """Bytes für den echten Ring: Startrahmen, je LED ``0xE0|hell, B, G, R``, Endrahmen."""
        hell = min(APA102_DECKEL, int(self.helligkeit * APA102_MAX / 100.0))
        daten = bytearray(4)
        for r, g, b in self.leds:
            daten += bytes((0xE0 | hell, b, g, r))
        daten += bytes((ANZAHL // 16 + 1) * [0xFF])  # Endrahmen: mindestens ANZAHL/2 Taktflanken
        return bytes(daten)


def _einfarbig(zustand: str, farbe: Farbe, helligkeit: float) -> Ring:
    return Ring(zustand, (farbe,) * ANZAHL, helligkeit)


def _aus() -> Ring:
    return _einfarbig(AUS, SCHWARZ, 0)


def _laeuft(t: float) -> Ring:
    # ruhiges Atmen zwischen 12 % und 25 %
    welle = 0.5 - 0.5 * math.cos(2 * math.pi * t / ATMEN_S)
    return _einfarbig(LAEUFT, GRUEN, 12 + 13 * welle)


def _pause() -> Ring:
    return _einfarbig(PAUSE, BERNSTEIN, 10)


def _unbekannt(t: float) -> Ring:
    an = (t % BLINK_UNBEKANNT_S) < BLINK_UNBEKANNT_S / 2
    return _einfarbig(UNBEKANNTE_KARTE, MAGENTA, DECKEL_PROZENT if an else 0)


def _akku_farbe(prozent: int) -> Farbe:
    return GRUEN if prozent > 50 else GELB if prozent > 20 else ROT


def _akku(prozent: int | None, am_lader: bool, tiefstand: bool, t: float) -> Ring:
    if tiefstand:
        an = (t % BLINK_TIEFSTAND_S) < BLINK_TIEFSTAND_S / 2
        return _einfarbig(AKKU, ROT, DECKEL_PROZENT if an else 0)
    p = max(0, min(100, prozent if prozent is not None else 0))
    n = int(round(p / 100 * ANZAHL))
    farbe = BLAU if am_lader else _akku_farbe(p)
    return Ring(AKKU, (farbe,) * n + (SCHWARZ,) * (ANZAHL - n), 15)


def _aufwachen(t_seit: float) -> Ring:
    # Lauflicht: ein Kopf mit abklingendem Schweif, KOMET_RUNDEN Runden in AUFWACHEN_S
    kopf = int(t_seit / AUFWACHEN_S * ANZAHL * KOMET_RUNDEN) % ANZAHL
    leds = [SCHWARZ] * ANZAHL
    for i in range(KOMET_LAENGE):
        f = 1.0 - i / KOMET_LAENGE
        r, g, b = WARMWEISS
        leds[(kopf - i) % ANZAHL] = (_byte(r * f), _byte(g * f), _byte(b * f))
    return Ring(AUFWACHEN, tuple(leds), DECKEL_PROZENT)


class LedLogik:
    """Hält die Eingaben des Rings und liefert das Bild zu einer Zeit.

    Rangfolge (oben gewinnt): Aufwachen, Akku (Tiefstand oder Anzeige), unbekannte Karte,
    läuft, Pause, aus.
    """

    def __init__(self) -> None:
        self.zustand_melden: ev.ZustandMelden | None = None
        self.akku_prozent: int | None = None
        self.am_lader = False
        self.tiefstand = False
        self._aufwachen_ab: float | None = None
        self._akku_bis: float | None = None

    # -- Eingaben ---------------------------------------------------------------------

    def aufwachen(self, jetzt_mono: float) -> None:
        """Lauflicht ``AUFWACHEN_S`` lang starten."""
        self._aufwachen_ab = jetzt_mono

    def akku_zeigen(self, jetzt_mono: float) -> None:
        """Akkustand ``AKKU_ANZEIGE_S`` lang zeigen."""
        self._akku_bis = jetzt_mono + AKKU_ANZEIGE_S

    def beobachte(self, e: object, jetzt_mono: float) -> None:
        """Nimmt ``ZustandMelden`` und die Strom-Ereignisse an; anderes wird ignoriert."""
        if isinstance(e, ev.ZustandMelden):
            alt = self.zustand_melden
            # aus dem Leerlauf zurück in den Betrieb: Aufwachen zeigen
            if alt is not None and alt.strom == "leerlauf" and e.strom == "aktiv":
                self.aufwachen(jetzt_mono)
            self.zustand_melden = e
            if e.strom == "herunterfahren":
                self._aufwachen_ab = None
        elif isinstance(e, ev.Bereit):
            self.aufwachen(jetzt_mono)  # Start der Box fertig
        elif isinstance(e, ev.AkkuStand):
            self.akku_prozent = max(0, min(100, e.prozent))
        elif isinstance(e, ev.LaderGeaendert):
            self.am_lader = e.am_lader
            if e.am_lader:
                self.tiefstand = False
            self.akku_zeigen(jetzt_mono)
        elif isinstance(e, ev.AkkuTiefstand):
            self.tiefstand = True

    # -- Ausgabe ----------------------------------------------------------------------

    def zustand(self, jetzt_mono: float) -> str:
        if self._aufwachen_ab is not None:
            if jetzt_mono - self._aufwachen_ab < AUFWACHEN_S:
                return AUFWACHEN
            self._aufwachen_ab = None
        if self.tiefstand:
            return AKKU
        if self._akku_bis is not None:
            if jetzt_mono < self._akku_bis and self.akku_prozent is not None:
                return AKKU
            if jetzt_mono >= self._akku_bis:
                self._akku_bis = None
        z = self.zustand_melden
        if z is None or z.strom != "aktiv":
            return AUS
        if z.sitzung == "unbekannt":
            return UNBEKANNTE_KARTE
        if z.sitzung == "spielt":
            return LAEUFT
        if z.sitzung in ("pausiert", "gehalten", "beendet"):
            return PAUSE
        return AUS  # ``leer``

    def ring(self, jetzt_mono: float) -> Ring:
        return ring_fuer(self.zustand(jetzt_mono), jetzt_mono, self)

    def ring_dict(self, jetzt_mono: float) -> dict[str, Any]:
        """Kurzform für die Simulation: ``ring(...).als_dict()``."""
        return self.ring(jetzt_mono).als_dict()


def ring_fuer(zustand: str, t: float, logik: LedLogik | None = None) -> Ring:
    """Bild für einen Zustandsnamen zur Zeit ``t`` (Sekunden, ``mono``).

    Ohne ``logik`` gelten Vorgaben: Aufwachen läuft ab ``t = 0``, Akku zeigt 50 %.
    """
    if zustand == LAEUFT:
        return _laeuft(t)
    if zustand == PAUSE:
        return _pause()
    if zustand == UNBEKANNTE_KARTE:
        return _unbekannt(t)
    if zustand == AKKU:
        if logik is None:
            return _akku(50, False, False, t)
        return _akku(logik.akku_prozent, logik.am_lader, logik.tiefstand, t)
    if zustand == AUFWACHEN:
        ab = logik._aufwachen_ab if logik is not None and logik._aufwachen_ab is not None else 0.0
        return _aufwachen(t - ab)
    if zustand == AUS:
        return _aus()
    raise ValueError(f"unbekannter Ring-Zustand: {zustand}")
