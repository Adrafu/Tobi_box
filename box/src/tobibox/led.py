"""LED-Ring: Zustand der Box -> Bild des Rings (reine Logik, keine Ein-/Ausgabe).

Quellen: Projektplan 5.5.2 (Zustände läuft, Pause, Akku, unbekannte Karte, Aufwachen),
Design CUJ 18, ``core-interface.md`` (``ZustandMelden`` ist die Anzeige-Eingabe des Rings).
Der echte APA102-Treiber und die Browser-Simulation bekommen dasselbe Bild:

* ``Ring.als_dict()``: JSON-fähig, für Simulation, Terminal und Protokoll.
* ``Ring.apa102_rahmen()``: die Bytes für den echten Ring.

Bestätigt (Entscheidung V, 10.11.): Lernmodus als blaues Atmen, Gute Nacht als Glimmen, das mit dem Ausblenden schwächer wird.
„stumm“ zeigt dunkelrot und geht aus (Entscheidung U, 10.11.), die Pause geht nach ``PAUSE_ANZEIGE_S`` aus (Entscheidung V).
Farben, Muster und Zeiten stehen als benannte Konstanten unten und lassen sich dort ohne Änderung der Logik anpassen.

Das Bild ist eine Funktion der Zeit (Atmen, Blinken, Lauflicht). Wer es zeichnet, ruft
``LedLogik.ring(jetzt_mono)`` im eigenen Takt auf (z. B. alle 50 ms).

Der Helligkeitsdeckel gilt immer: ``Ring`` klemmt seine Helligkeit selbst auf ``DECKEL_PROZENT``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from . import events as ev
from .stromwert import StromQuellen

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
LERNEN = "lernen"
STUMM = "stumm"  # Entscheidung U (10.11.): Pause wegen „stumm“ oder Tobie unter „stumm“ erkannt, ganz dunkelrot
GUTE_NACHT = "gute_nacht"
LESER_UNTERBROCHEN = "leser_unterbrochen"  # Entscheidung V (10.11.): Sitzung „unbekannt“, rot langsam blinkend
ZUSTAENDE = (AUS, LAEUFT, PAUSE, AKKU, UNBEKANNTE_KARTE, AUFWACHEN, LERNEN, GUTE_NACHT, STUMM, LESER_UNTERBROCHEN)

# Zeiten in Sekunden
AUFWACHEN_S = 2.0  # Lauflicht beim Aufwachen
AKKU_ANZEIGE_S = 5.0  # Akku-Anzeige nach Anforderung, beim Start mit Strom und beim Andocken oder Abziehen
AKKU_ENTPRELL_S = 1.0  # eine zweite Anforderung der Akku-Anzeige so kurz nach der ersten startet sie nicht neu
ATMEN_S = 6.0  # Periode beim Atmen (läuft)
PAUSE_HELLIGKEIT = 10  # Prozent, Pause
BLINK_UNBEKANNT_S = 1.0  # Periode Blinken magenta (Rückfall ohne Zeitpunkt des Auflegens)
BLINK_LESER_S = 2.0  # Entscheidung V (10.11.): Periode des langsamen roten Blinkens, wenn der Leser unterbrochen ist (Sitzung „unbekannt“)
PAUSE_ANZEIGE_S = 10.0  # Entscheidung V (10.11.): so lange leuchtet die Pause bernstein, danach ist der Ring aus
BLINK_UNBEKANNT_ANZEIGE_S = 1.0  # so lange blinkt der Ring, wenn ein unbekannter Tobie aufgelegt wird (CUJ 18)
BLINK_UNBEKANNT_NEU_S = 0.5  # Periode dieses Blinkens: zwei Blinker in einer Sekunde
BLINK_TIEFSTAND_S = 0.5  # Periode Blinken (Akku-Tiefstand)
KOMET_LAENGE = 10  # LEDs im Schweif des Lauflichts
KOMET_RUNDEN = 2
STUMM_ANZEIGE_S = 5.0  # Entscheidung U (10.11.): so lange leuchtet der Ring dunkelrot, danach bleibt er unter „stumm“ aus

# --- Lernmodus, Gute Nacht (bestätigt, Entscheidung V, 10.11.), stumm (Entscheidung U, 10.11.) ---
LERNEN_ATMEN_S = 3.0  # Periode des blauen Atmens im Lernmodus (schneller als „läuft“: die Box wartet auf einen Tobie)
LERNEN_HELL_MIN = 8  # Prozent, unterer Punkt des Atmens
LERNEN_HELL_MAX = 25  # Prozent, oberer Punkt (nie über dem Deckel)
GUTE_NACHT_GLIMMEN_S = 4.0  # Periode des Glimmens
GUTE_NACHT_HELL_MIN = 3  # Prozent, unterer Punkt des Glimmens
GUTE_NACHT_HELL_MAX = 8  # Prozent, oberer Punkt; beim Ausblenden wird alles mit dem Ausblenden-Faktor multipliziert
# Akku-Anzeige (Ein/Aus, 10.11.): eigene Helligkeiten. Mindestens Stufe 1 der 31 Stufen.
AKKU_HELL = 15  # Prozent, normal
AKKU_HELL_LEISER = 5  # Prozent, in einem Fenster „leiser“ und solange „Gute Nacht“ läuft
AKKU_HELL_STUMM = 3  # Prozent, in einem Fenster „stumm“
STUMM_HELLIGKEIT = 3  # Prozent: kleinste sichtbare Stufe (``apa102_rahmen`` rundet auf mindestens Stufe 1 von 31)

Farbe = tuple[int, int, int]
SCHWARZ: Farbe = (0, 0, 0)
GRUEN: Farbe = (0, 255, 70)
BERNSTEIN: Farbe = (255, 110, 0)
MAGENTA: Farbe = (255, 0, 120)
GELB: Farbe = (255, 190, 0)
ROT: Farbe = (255, 0, 0)
BLAU: Farbe = (0, 150, 255)
WARMWEISS: Farbe = (255, 200, 120)
FARBE_LERNEN: Farbe = (0, 70, 255)  # Lernmodus: Blau, deutlich anders als der Akku im Laden (BLAU)
FARBE_GUTE_NACHT: Farbe = (255, 90, 10)  # Gute Nacht: warmes, dunkles Orange, wie Glut
STUMM_FARBE: Farbe = ROT  # Entscheidung U (10.11.): Pause wegen „stumm“ oder Tobie unter „stumm“ erkannt


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
        if self.helligkeit > 0:
            hell = max(1, hell)  # was leuchten soll, bekommt mindestens Stufe 1 (3 % ergäben gerundet Stufe 0, Ein/Aus, 10.11.)
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
    return _einfarbig(PAUSE, BERNSTEIN, PAUSE_HELLIGKEIT)


def _stumm() -> Ring:
    return _einfarbig(STUMM, STUMM_FARBE, STUMM_HELLIGKEIT)


def _lernen(t: float) -> Ring:
    welle = 0.5 - 0.5 * math.cos(2 * math.pi * t / LERNEN_ATMEN_S)
    return _einfarbig(LERNEN, FARBE_LERNEN, LERNEN_HELL_MIN + (LERNEN_HELL_MAX - LERNEN_HELL_MIN) * welle)


def _gute_nacht(t: float, faktor: float) -> Ring:
    """Glimmen; ``faktor`` (1 bis 0) ist der Stand des Ausblendens und macht es schwächer."""
    welle = 0.5 - 0.5 * math.cos(2 * math.pi * t / GUTE_NACHT_GLIMMEN_S)
    hell = GUTE_NACHT_HELL_MIN + (GUTE_NACHT_HELL_MAX - GUTE_NACHT_HELL_MIN) * welle
    return _einfarbig(GUTE_NACHT, FARBE_GUTE_NACHT, hell * max(0.0, min(1.0, faktor)))


def _unbekannt(t: float, periode: float = BLINK_UNBEKANNT_S) -> Ring:
    an = (t % periode) < periode / 2
    return _einfarbig(UNBEKANNTE_KARTE, MAGENTA, DECKEL_PROZENT if an else 0)


def _leser_unterbrochen(t: float) -> Ring:
    an = (t % BLINK_LESER_S) < BLINK_LESER_S / 2
    return _einfarbig(LESER_UNTERBROCHEN, ROT, DECKEL_PROZENT if an else 0)


def _akku_farbe(prozent: int) -> Farbe:
    return GRUEN if prozent > 50 else GELB if prozent > 20 else ROT


def _akku(prozent: int | None, am_lader: bool, tiefstand: bool, t: float, helligkeit: float = AKKU_HELL) -> Ring:
    if tiefstand:
        an = (t % BLINK_TIEFSTAND_S) < BLINK_TIEFSTAND_S / 2
        return _einfarbig(AKKU, ROT, DECKEL_PROZENT if an else 0)
    p = max(0, min(100, prozent if prozent is not None else 0))
    n = int(round(p / 100 * ANZAHL))
    farbe = BLAU if am_lader else _akku_farbe(p)
    return Ring(AKKU, (farbe,) * n + (SCHWARZ,) * (ANZAHL - n), helligkeit)


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

    Rangfolge (oben gewinnt): Aufwachen, Akku (Tiefstand oder Anzeige), unbekannte Karte
    (Blinken beim Auflegen eines unbekannten Tobies, ``BLINK_UNBEKANNT_ANZEIGE_S`` lang), Leser unterbrochen (Sitzung „unbekannt“,
    rot langsam blinkend, Entscheidung V), Lernmodus, „stumm“ (dunkelrot, dann aus), Gute Nacht (nur während die Wiedergabe läuft), läuft, Pause (bernstein, nach ``PAUSE_ANZEIGE_S`` aus, Entscheidung V), aus.
    Unter „stumm“ (``ruhe``, Entscheidung U, 10.11.): Beginnt „stumm“, während ein Tobie spielt (Ausblenden), oder wird unter „stumm“ ein
    Tobie aufgelegt (Sitzung ``gehalten``), leuchtet der Ring ``STUMM_ANZEIGE_S`` lang ganz dunkelrot (``STUMM``) und bleibt dann aus,
    solange „stumm“ gilt. Die 5 s beginnen mit der ``ZustandMelden``, die ``spielt`` oder ``gehalten`` unter „stumm“ zum ersten Mal zeigt
    (der Übergang ``spielt`` zu ``gehalten`` startet nicht neu; Abheben und erneutes Auflegen schon). Akku-Anzeige, Tiefstand,
    Unbekannt-Blinken, Aufwachen und Lernmodus gehen vor und bleiben unverändert. Es gibt keinen Dimm-Faktor mehr.
    """

    def __init__(self) -> None:
        self.zustand_melden: ev.ZustandMelden | None = None
        self.akku_prozent: int | None = None
        self.quellen = StromQuellen()  # Strom am Eingang aus zwei Quellen (nur für die Farbe der Anzeige: blau mit Strom)
        self.tiefstand = False
        self._bereit = False
        self._start_anzeige = False  # erste bekannte Messung war „Strom“: Ladestand nach ``Bereit`` zeigen (CUJ 25, Start-Anzeige)
        self._akku_ab: float | None = None
        self._aufwachen_ab: float | None = None
        self._akku_bis: float | None = None
        self._unbekannt_ab: float | None = None  # ein unbekannter Tobie wurde aufgelegt: Magenta blinkt ab diesem Zeitpunkt
        self._pause_ab: float | None = None  # Entscheidung V: Beginn der Pause-Anzeige
        self._stumm_ab: float | None = None  # Entscheidung U: Beginn der dunkelroten Anzeige unter „stumm“
        self.ausblenden_faktor: float | None = None  # Gute Nacht: 1 bis 0 während des Ausblendens, sonst ``None``

    @property
    def am_lader(self) -> bool:
        return self.quellen.wert is True

    # -- Eingaben ---------------------------------------------------------------------

    def aufwachen(self, jetzt_mono: float) -> None:
        """Lauflicht ``AUFWACHEN_S`` lang starten."""
        self._aufwachen_ab = jetzt_mono

    def akku_zeigen(self, jetzt_mono: float, dauer_s: float = AKKU_ANZEIGE_S) -> None:
        """Akkustand ``dauer_s`` lang zeigen (Anforderung, Start mit Strom, Andocken, Abziehen).

        Entprellt: Eine zweite Anforderung innerhalb von ``AKKU_ENTPRELL_S`` nach dem Beginn einer laufenden Anzeige startet sie nicht neu.
        Läuft gerade das Lauflicht des Aufwachens, beginnt die Anzeige danach (das Lauflicht geht vor)."""
        if (
            self._akku_ab is not None and self._akku_bis is not None
            and jetzt_mono < self._akku_bis and jetzt_mono - self._akku_ab < AKKU_ENTPRELL_S
        ):
            return
        beginn = jetzt_mono
        if self._aufwachen_ab is not None:
            beginn = max(beginn, self._aufwachen_ab + AUFWACHEN_S)
        self._akku_ab = jetzt_mono
        self._akku_bis = beginn + dauer_s

    def unbekannter_tobie(self, jetzt_mono: float) -> None:
        """Ein unbekannter Tobie wurde aufgelegt: ``BLINK_UNBEKANNT_ANZEIGE_S`` lang magenta blinken, danach der normale Zustand."""
        ab = jetzt_mono
        if self._aufwachen_ab is not None:
            ab = max(ab, self._aufwachen_ab + AUFWACHEN_S)  # erst das Lauflicht des Aufwachens, dann das Blinken
        self._unbekannt_ab = ab

    def setze_ausblenden(self, faktor: float | None) -> None:
        """Stand des Ausblendens von „Gute Nacht“ (1 = Anfang, 0 = Ende), ``None`` außerhalb des Ausblendens."""
        self.ausblenden_faktor = None if faktor is None else max(0.0, min(1.0, float(faktor)))

    def beobachte(self, e: object, jetzt_mono: float) -> None:
        """Nimmt ``ZustandMelden`` und die Strom-Ereignisse an; anderes wird ignoriert."""
        if isinstance(e, ev.ZustandMelden):
            alt = self.zustand_melden
            # aus dem Leerlauf zurück in den Betrieb: Aufwachen zeigen
            # (nicht, wenn ein Tobie lag: mit Entscheidung O zählt auch die Pause mit liegendem Tobie als Leerlauf)
            if alt is not None and alt.strom == "leerlauf" and e.strom == "aktiv" and not alt.figur_liegt:
                self.aufwachen(jetzt_mono)
            self._stumm_pruefen(alt, e, jetzt_mono)
            self._pause_pruefen(alt, e, jetzt_mono)
            self.zustand_melden = e
            if e.strom == "herunterfahren":
                self._aufwachen_ab = None
        elif isinstance(e, ev.Bereit):
            self._bereit = True
            self.aufwachen(jetzt_mono)  # Start der Box fertig
            self._start_pruefen(jetzt_mono)
        elif isinstance(e, ev.AkkuStand):
            self.akku_prozent = max(0, min(100, e.prozent))
        elif isinstance(e, ev.LaderGeaendert):
            erste = self.quellen.wert is None
            self.quellen = self.quellen.mit(e)
            if self.quellen.wert is True:
                self.tiefstand = False
            if erste and self.quellen.wert is True:
                self._start_anzeige = True  # Start-Anzeige: keine Andock-Rückmeldung, ohne Sperre (``core-interface.md``, 9.9 Nr. 4)
                self._start_pruefen(jetzt_mono)
        elif isinstance(e, (ev.LeserHallo, ev.LeserAlarm)):
            self.quellen = StromQuellen(self.quellen.pisugar, None)  # der Leser-Wert gilt nur für die aktuelle Verbindung (V2)
        elif isinstance(e, ev.AkkuAnzeigen):
            # Freigabe durch ``idle`` (Andocken, Abziehen): erste Messung und Sperre hat ``idle`` schon geprüft (V6)
            self.akku_zeigen(jetzt_mono, e.dauer_s)
        elif isinstance(e, ev.AkkuTiefstand):
            self.tiefstand = True

    @staticmethod
    def _pausiert(m: ev.ZustandMelden | None) -> bool:
        return m is not None and m.sitzung in ("pausiert", "gehalten", "beendet")

    def _pause_pruefen(self, alt: ev.ZustandMelden | None, neu: ev.ZustandMelden, jetzt_mono: float) -> None:
        """Entscheidung V: Die 10 s der Pause beginnen, wenn die Sitzung in eine Pause wechselt (nicht bei jeder Wiederholung der Meldung)."""
        if not self._pausiert(neu):
            self._pause_ab = None
        elif not self._pausiert(alt):
            ab = jetzt_mono
            if self._aufwachen_ab is not None:
                ab = max(ab, self._aufwachen_ab + AUFWACHEN_S)
            self._pause_ab = ab

    @staticmethod
    def _wegen_stumm(m: ev.ZustandMelden | None) -> bool:
        """„Wegen stumm pausiert“ (Ausblenden oder ``gehalten``) oder „Tobie unter stumm erkannt“ (``gehalten``): beides zeigt die Sitzung so."""
        return m is not None and m.ruhe == "stumm" and m.sitzung in ("spielt", "gehalten")

    def _stumm_pruefen(self, alt: ev.ZustandMelden | None, neu: ev.ZustandMelden, jetzt_mono: float) -> None:
        if not self._wegen_stumm(neu):
            self._stumm_ab = None
        elif not self._wegen_stumm(alt):
            ab = jetzt_mono
            if self._aufwachen_ab is not None:
                ab = max(ab, self._aufwachen_ab + AUFWACHEN_S)  # erst das Lauflicht des Aufwachens
            self._stumm_ab = ab

    def _start_pruefen(self, jetzt_mono: float) -> None:
        if self._bereit and self._start_anzeige:
            self._start_anzeige = False
            self.akku_zeigen(jetzt_mono)

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
        if z is None or z.strom == "herunterfahren":
            return AUS
        if self._unbekannt_ab is not None:
            if jetzt_mono - self._unbekannt_ab < BLINK_UNBEKANNT_ANZEIGE_S:
                return UNBEKANNTE_KARTE
            self._unbekannt_ab = None
        if z.sitzung == "unbekannt":
            return LESER_UNTERBROCHEN
        if z.lernmodus:
            return LERNEN  # auch im Leerlauf: Lernen wartet auf einen Tobie, der Ring zeigt es
        if z.ruhe == "stumm":
            if (
                self._stumm_ab is not None and self._wegen_stumm(z) and jetzt_mono - self._stumm_ab < STUMM_ANZEIGE_S
                and (z.strom == "aktiv" or z.figur_liegt)
            ):
                return STUMM
            if z.sitzung in ("pausiert", "gehalten", "beendet"):
                return AUS  # Entscheidung U: danach bleibt der Ring unter „stumm“ dunkel
        if z.strom != "aktiv" and not (z.strom == "leerlauf" and (z.figur_liegt or self._pause_laeuft(z, jetzt_mono))):
            return AUS  # Leerlauf ohne Tobie; mit liegendem Tobie zeigt der Ring die Pause weiter (Entscheidung O), nach dem Abheben die 10 s (V)
        if z.sitzung == "spielt":
            return GUTE_NACHT if z.gute_nacht != "aus" else LAEUFT
        if z.sitzung in ("pausiert", "gehalten", "beendet"):
            if self._pause_ab is not None and jetzt_mono - self._pause_ab >= PAUSE_ANZEIGE_S:
                return AUS  # Entscheidung V: nach 10 s dunkel
            return PAUSE
        return AUS  # ``leer``

    def _pause_laeuft(self, z: ev.ZustandMelden, jetzt_mono: float) -> bool:
        """Die 10 s der Pause-Anzeige (Entscheidung V) laufen noch. Nach dem Abheben meldet der Kern sofort ``leerlauf`` ohne
        liegenden Tobie; die Pause-Anzeige darf trotzdem nicht sofort enden."""
        return (
            z.sitzung in ("pausiert", "gehalten", "beendet")
            and self._pause_ab is not None
            and jetzt_mono - self._pause_ab < PAUSE_ANZEIGE_S
        )

    def akku_helligkeit(self) -> float:
        """Helligkeit der Akku-Anzeige: normal 15 %, „leiser“ und „Gute Nacht“ 5 %, „stumm“ 3 % (Ein/Aus, 10.11.)."""
        z = self.zustand_melden
        if z is None:
            return AKKU_HELL
        if z.ruhe == "stumm":
            return AKKU_HELL_STUMM
        if z.ruhe == "leiser" or z.gute_nacht != "aus":
            return AKKU_HELL_LEISER
        return AKKU_HELL

    def ring(self, jetzt_mono: float) -> Ring:
        r = ring_fuer(self.zustand(jetzt_mono), jetzt_mono, self)
        if r.zustand == AKKU:
            z = self.zustand_melden
            if not self.tiefstand:
                return Ring(r.zustand, r.leds, self.akku_helligkeit())  # eigene Helligkeiten
            if z is not None and z.ruhe == "stumm":
                return Ring(r.zustand, r.leds, AKKU_HELL_STUMM * (r.helligkeit > 0))  # Tiefstand-Blinken unter „stumm“: kleinste Stufe
        return r

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
        if logik is not None and logik._unbekannt_ab is not None:
            return _unbekannt(t - logik._unbekannt_ab, BLINK_UNBEKANNT_NEU_S)
        return _unbekannt(t)
    if zustand == LESER_UNTERBROCHEN:
        return _leser_unterbrochen(t)
    if zustand == STUMM:
        return _stumm()
    if zustand == LERNEN:
        return _lernen(t)
    if zustand == GUTE_NACHT:
        faktor = logik.ausblenden_faktor if logik is not None and logik.ausblenden_faktor is not None else 1.0
        return _gute_nacht(t, faktor)
    if zustand == AKKU:
        if logik is None:
            return _akku(50, False, False, t)
        return _akku(logik.akku_prozent, logik.am_lader, logik.tiefstand, t, logik.akku_helligkeit())
    if zustand == AUFWACHEN:
        ab = logik._aufwachen_ab if logik is not None and logik._aufwachen_ab is not None else 0.0
        return _aufwachen(t - ab)
    if zustand == AUS:
        return _aus()
    raise ValueError(f"unbekannter Ring-Zustand: {zustand}")
