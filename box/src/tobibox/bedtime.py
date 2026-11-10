"""Teilautomat Gute Nacht ``bedtime`` (``core-interface.md``, 5.2 und 9 Punkt 6 und 7; Tabelle „Gute Nacht“).

Reine Funktionen: kein Zugriff auf Dateien, Netz, Uhr oder Zufall. Zustände ``aus``, ``laeuft``, ``ausblenden``.

* Die Karte ist ein Eintrag vom Typ ``aktion`` (``gute_nacht``) in ``config.json``. Die Sitzung meldet das
  Auflegen als ``AktionAusgeloest``. Das funktioniert damit auch am Mac.
* Der Timer läuft auf ``jetzt.mono`` (Dauer ``timer_min`` aus der Konfiguration, Vorschlag 30 min).
* Das Ausblenden senkt die Grenze ``gute_nacht`` in ``ausblenden_s`` (Vorschlag 60 s) linear von ``wirksam``
  auf 0. Bei 0 gibt ``bedtime`` ``GuteNachtEnde`` aus; die Sitzung pausiert und speichert den Zeiger. Die Grenze
  wird in derselben Verarbeitung gelöscht, damit die Lautstärke nicht zurückspringt (Regel 6.2.7).
* ``bedtime`` gibt keine ``Pausieren``-Befehle aus.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from . import events as ev
from .events import Jetzt
from .volume import GRENZE_GUTE_NACHT, rampe

#: Vorgaben, solange noch keine Konfiguration geladen ist
TIMER_MIN_VORGABE = 30
AUSBLENDEN_S_VORGABE = 60

Ausgabe = tuple[ev.Befehl | ev.InternesEreignis, ...]


@dataclass(frozen=True, slots=True)
class Zustand:
    modus: str = "aus"  # "aus" | "laeuft" | "ausblenden"
    timer_min: int = TIMER_MIN_VORGABE
    ausblenden_s: int = AUSBLENDEN_S_VORGABE
    frist_bis: float = 0.0  # mono; nur in ``laeuft``
    #: Startwert und Beginn des Ausblendens (mono); nur in ``ausblenden``
    von: int = 0
    start: float = 0.0
    #: zuletzt ausgegebener Wert der Grenze ``gute_nacht``
    letzter: int | None = None
    #: letzte gemeldete wirksame Lautstärke
    wirksam: int = 100


def neuer_zustand() -> Zustand:
    return Zustand()


def kennzeichen(zustand: Zustand) -> str:
    return zustand.modus


def _prot(ebene: str, ereignis: str, ergebnis: str, vorgang: str | None = None, **daten) -> ev.Protokoll:
    return ev.Protokoll("bedtime", ebene, ereignis, ergebnis, vorgang, daten)  # type: ignore[arg-type]


def step(zustand: Zustand, ereignis: ev.Ereignis | ev.InternesEreignis, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    z = zustand

    if isinstance(ereignis, ev.LautstaerkeGeaendert):
        return replace(z, wirksam=ereignis.wirksam), ()

    if isinstance(ereignis, ev.KonfigGeladen):
        # Ein laufender Timer behält seine Frist; neue Dauern gelten ab dem nächsten Start.
        g = ereignis.konfig.gute_nacht
        return replace(z, timer_min=g.timer_min, ausblenden_s=g.ausblenden_s), ()

    if isinstance(ereignis, ev.AktionAusgeloest):
        if ereignis.aktion != "gute_nacht":
            return z, ()
        if z.modus == "ausblenden":
            return z, (_prot("INFO", "gute_nacht", "ignoriert", ereignis.vorgang, grund="ausblenden"),)
        neu = replace(z, modus="laeuft", frist_bis=jetzt.mono + z.timer_min * 60.0)
        ergebnis = "neu_gestartet" if z.modus == "laeuft" else "gestartet"
        # Entscheidung R (10.11.): Durchsage beim Auflegen; unter „stumm“ streicht ``core`` sie (Regel 2), die Karte wirkt trotzdem
        return neu, (
            ev.TonSpielen("gute_nacht"),
            _prot("INFO", "gute_nacht", ergebnis, ereignis.vorgang, timer_min=z.timer_min),
        )

    if isinstance(ereignis, ev.Abgehoben):
        if z.modus != "ausblenden":
            return z, ()  # im Zustand ``laeuft`` läuft der Timer weiter
        return _aus(z), (
            ev.GrenzeGesetzt(GRENZE_GUTE_NACHT, None),
            _prot("INFO", "gute_nacht", "abgebrochen", grund="abgehoben"),
        )

    if isinstance(ereignis, ev.Takt):
        if z.modus == "laeuft" and jetzt.mono >= z.frist_bis:
            neu = replace(z, modus="ausblenden", von=z.wirksam, start=jetzt.mono)
            return _ausblenden_schritt(neu, jetzt, beginn=True)
        if z.modus == "ausblenden":
            return _ausblenden_schritt(z, jetzt, beginn=False)

    return z, ()


def _aus(z: Zustand) -> Zustand:
    return replace(z, modus="aus", frist_bis=0.0, von=0, start=0.0, letzter=None)


def _ausblenden_schritt(z: Zustand, jetzt: Jetzt, *, beginn: bool) -> tuple[Zustand, Ausgabe]:
    wert = rampe(z.von, 0, z.start, float(z.ausblenden_s), jetzt.mono)
    if z.letzter is not None:
        wert = min(wert, z.letzter)  # nie wieder lauter
    out: list = []
    if beginn:
        out.append(_prot("INFO", "gute_nacht", "ausblenden_beginnt", von=z.von, dauer_s=z.ausblenden_s))
    if wert <= 0:
        out += [
            ev.GrenzeGesetzt(GRENZE_GUTE_NACHT, 0),
            ev.GuteNachtEnde(),
            ev.GrenzeGesetzt(GRENZE_GUTE_NACHT, None),
            _prot("INFO", "gute_nacht", "ende"),
        ]
        return _aus(z), tuple(out)
    if wert != z.letzter:
        out.append(ev.GrenzeGesetzt(GRENZE_GUTE_NACHT, wert))
    return replace(z, letzter=wert), tuple(out)
