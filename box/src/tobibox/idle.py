"""Teilautomat Strom / Leerlauf (``core-interface.md``, 5.2 und 9 Punkt 9; Tabelle „Strom / Leerlauf“, CUJ 16).

Reine Funktionen: kein Zugriff auf Dateien, Netz, Uhr oder Zufall. Zustände ``aktiv``, ``leerlauf``
(Zähler für ``LEERLAUF_S`` läuft), ``herunterfahren``. Alle Fristen laufen auf ``jetzt.mono``.

**Was „Leerlauf“ heißt.** Der Vertrag (Tabelle „Strom / Leerlauf“) kennt nur: *keine Wiedergabe und kein Tobie*.
Das steht hier als ``belegt``: Die Sitzung spielt, ein Tobie liegt (auch eine Aktionskarte) oder die Sitzung ist im
Zustand ``unbekannt`` (Leser-Unterbrechung, der Tobie kann noch da sein).

**Bedienung setzt den Zähler zurück** (Entscheidung der Projektleitung, AP 4.8): Hauptknopf (kurz), ``Weiter``, ``Zurueck``,
``LautstaerkeDrehen`` und ``Kopfhoerer``. Wer an der Box spielt, will nicht, dass sie ausgeht. HA-Befehle (Sync, Update) setzen
den Zähler nicht zurück.

**Abschaltung nach ``LEERLAUF_S``.** Läuft der Zähler ab, ist die Abschaltung ``faellig``. Sie wartet, solange

* der Lernmodus läuft,
* ein Sync oder ein Update läuft,
* ein Sync **offen** ist: ``SyncStarten`` ist ausgegeben, die Antwort (``SyncGestartet`` oder ``SyncAbgebrochen``)
  fehlt noch. Das ist die Auslegung von „Sync oder Update noch offen“ (am Lader) aus dem Vertrag; sie gilt hier auch
  ohne Lader, und eine fehlende Antwort hält die Abschaltung höchstens ``SYNC_ANTWORT_FRIST_S`` auf.

Die Wartezeit ist ein Zustand, kein neuer Zähler: Endet der Sync oder das Update und die Box ist noch im Leerlauf,
fährt sie sofort herunter („nach Ende erneut prüfen“). Endet der **Lernmodus**, beginnt der Zähler neu (Lernen ist eine
Handlung von Tobias und der Zähler hatte sie nicht gesehen). Wird die Box wieder belegt, verfällt die Abschaltung.

``Hauptknopf`` lang und ``AkkuTiefstand`` (nicht am Lader) fahren immer herunter, auch während Sync, Update oder
Lernmodus. Beim Tiefstand wird ein laufender oder offener Sync abgebrochen.

**Start am Lader.** Sobald ``Bereit`` da ist und der Lader bekannt ist (``LaderGeaendert`` kann vor oder nach
``Bereit`` kommen), gibt ``idle`` einmal ``SyncStarten("start_lader")`` aus, wenn die Box am Lader hängt.

**Wiederholung am Lader** (Entscheidung der Projektleitung, AP 4.8). Bricht dieser Start-Sync mit ``netz_weg`` oder ``regel`` ab
(Heim-WLAN noch nicht da, Regel verbietet den Sync), versucht ``idle`` es erneut, solange die Box am Lader hängt: alle
``START_WIEDERHOLUNG_S`` (10 min), höchstens ``START_WIEDERHOLUNGEN`` (6) Mal. Während dieser Wartezeit schaltet die Box nicht ab
(wie bei einem laufenden Sync). Danach, oder wenn der Sync gelingt, aus anderem Grund abbricht oder der Lader fehlt, gilt wieder
die 20-min-Regel: Ist der Zähler schon abgelaufen, fährt die Box sofort herunter.

**HA-Befehle ``HaSyncAnstossen`` / ``HaUpdateAnstossen``** prüft ``idle`` (Ablaufzeit, Uhr, beim Update die
Bedingungen) und reicht sie als ``SyncStarten("ha")`` / ``UpdateStarten`` weiter (Punkt 9.9).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from . import events as ev
from .events import Jetzt

#: 20 min Leerlauf bis zur Abschaltung (``core-interface.md``, Konstanten).
LEERLAUF_S = 1200.0
#: So lange hält ein ausgegebenes ``SyncStarten`` ohne Antwort die Abschaltung höchstens auf.
SYNC_ANTWORT_FRIST_S = 60.0
#: Start am Lader: nach ``netz_weg`` oder ``regel`` alle 10 min noch einmal versuchen, höchstens 6-mal.
START_WIEDERHOLUNG_S = 600.0
START_WIEDERHOLUNGEN = 6
_WIEDERHOLEN_BEI = ("netz_weg", "regel")

Ausgabe = tuple[ev.Befehl | ev.InternesEreignis, ...]


@dataclass(frozen=True, slots=True)
class Zustand:
    modus: str = "aktiv"  # "aktiv" | "leerlauf" | "herunterfahren"
    frist_bis: float = 0.0  # mono; nur in ``leerlauf``
    faellig: bool = False  # nur in ``leerlauf``: die 20 min sind um, die Abschaltung wartet auf Sync, Update, Lernmodus
    # was die Sitzung meldet
    spielt: bool = False
    figur_liegt: bool = False
    unbekannt: bool = False  # Sitzung im Zustand ``unbekannt`` (Leser-Unterbrechung)
    # was läuft
    lernt: bool = False
    sync_laeuft: bool = False
    update_laeuft: bool = False
    sync_offen_bis: float | None = None  # mono; ``SyncStarten`` ausgegeben, Antwort fehlt
    # Umgebung
    am_lader: bool | None = None
    klasse: str | None = None
    bereit: bool = False
    start_geprueft: bool = False
    # Wiederholung des Start-Syncs am Lader
    start_wdh: bool = False  # der Start-Sync ist noch nicht gelungen und wird ggf. wiederholt
    wdh_n: int = 0  # bisher gemachte Wiederholungen
    wdh_bei: float | None = None  # mono; nächster Versuch


def neuer_zustand() -> Zustand:
    return Zustand()


def kennzeichen(zustand: Zustand) -> str:
    return zustand.modus


def belegt(z: Zustand) -> bool:
    """Gegenteil von Leerlauf: es spielt etwas oder ein Tobie liegt."""
    return z.spielt or z.figur_liegt or z.unbekannt


def sync_offen(z: Zustand) -> bool:
    return z.sync_offen_bis is not None


def blockiert(z: Zustand) -> bool:
    """Wartet die Abschaltung auf etwas? Lernmodus, Sync, Update, ein offener Sync oder die Wiederholung des Start-Syncs."""
    return z.lernt or z.sync_laeuft or z.update_laeuft or sync_offen(z) or z.wdh_bei is not None


def _prot(ebene: str, ereignis: str, ergebnis: str, **daten: str | int | float | bool | None) -> ev.Protokoll:
    return ev.Protokoll("idle", ebene, ereignis, ergebnis, None, daten)  # type: ignore[arg-type]


def _herunterfahren(z: Zustand, grund: str, *vorher: ev.Befehl | ev.InternesEreignis) -> tuple[Zustand, Ausgabe]:
    neu = replace(z, modus="herunterfahren", faellig=False)
    return neu, (
        *vorher,
        _prot("INFO", "herunterfahren", "angefordert", grund=grund),
        ev.HerunterfahrenAngefordert(grund),  # type: ignore[arg-type]
    )


def _abgelehnt(befehl: str, befehl_id: str, grund: str, detail: str | None = None) -> ev.EreignisSenden:
    daten: dict[str, str | int | bool | None] = {"befehl": befehl, "befehl_id": befehl_id, "grund": grund}
    if detail is not None:
        daten["detail"] = detail
    return ev.EreignisSenden("befehl_abgelehnt", daten)


def _ha_befehl_pruefen(
    z: Zustand, e: ev.HaSyncAnstossen | ev.HaUpdateAnstossen, name: str, jetzt: Jetzt
) -> Ausgabe | None:
    """Ablaufzeit und Uhr (Punkt 9.9). ``None``: der Befehl ist angenommen und wird weiter geprüft."""
    if jetzt.wall > e.gueltig_bis:
        return (_prot("WARNING", f"{name}_befehl", "abgelaufen", befehl_id=e.befehl_id),)
    if not jetzt.zeit_ok:
        return (
            _prot("WARNING", f"{name}_befehl", "abgelehnt", grund="zeit_unsicher", befehl_id=e.befehl_id),
            _abgelehnt(name, e.befehl_id, "zeit_unsicher"),
        )
    return None


def _update_bedingung(z: Zustand) -> str | None:
    """Erste nicht erfüllte Bedingung für ein Update (Text für ``detail``), sonst ``None``."""
    if z.klasse != "home":
        return "Die Box ist nicht im Heimnetz."
    if z.am_lader is not True:
        return "Die Box hängt nicht am Lader."
    if z.spielt:
        return "Es läuft gerade ein Hörspiel."
    if z.sync_laeuft or sync_offen(z):
        return "Es läuft gerade ein Sync."
    if z.update_laeuft:
        return "Es läuft schon ein Update."
    return None


def _start_pruefung(z: Zustand, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Beim Start am Lader: einmal prüfen, ob ein Sync ansteht (``sync`` entscheidet nach der Netz-Regel)."""
    if z.start_geprueft or not z.bereit or z.am_lader is None:
        return z, ()
    z = replace(z, start_geprueft=True)
    if z.am_lader is not True:
        return z, ()
    return replace(z, sync_offen_bis=jetzt.mono + SYNC_ANTWORT_FRIST_S, start_wdh=True), (
        ev.SyncStarten("start_lader"),
        _prot("INFO", "start_sync", "angefordert", grund="start_lader"),
    )


def _wdh_ende(z: Zustand) -> Zustand:
    """Keine weitere Wiederholung (gelungen, anderer Abbruchgrund, Lader weg, aufgebraucht)."""
    return replace(z, start_wdh=False, wdh_bei=None)


def _bedient(z: Zustand, jetzt: Jetzt) -> Zustand:
    """Bedienung (Taste, Drehregler, Kopfhörer): der Zähler beginnt neu."""
    if z.modus == "leerlauf":
        return replace(z, faellig=False, frist_bis=jetzt.mono + LEERLAUF_S)
    return z


def _auswerten(z: Zustand, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Zähler und Abschaltung nach jedem Ereignis nachführen."""
    if z.modus == "herunterfahren":
        return z, ()
    out: list[ev.Befehl | ev.InternesEreignis] = []

    if z.sync_offen_bis is not None and jetzt.mono >= z.sync_offen_bis:
        z = replace(z, sync_offen_bis=None)
        out.append(_prot("WARNING", "sync_antwort", "fehlt"))

    if z.wdh_bei is not None and jetzt.mono >= z.wdh_bei:
        if z.am_lader is not True:
            z = _wdh_ende(z)
        elif not z.sync_laeuft and not sync_offen(z):
            z = replace(z, wdh_bei=None, wdh_n=z.wdh_n + 1, sync_offen_bis=jetzt.mono + SYNC_ANTWORT_FRIST_S)
            out += [
                ev.SyncStarten("start_lader"),
                _prot("INFO", "start_sync", "wiederholt", grund="start_lader", versuch=z.wdh_n),
            ]

    if z.modus == "aktiv" and not belegt(z):
        z = replace(z, modus="leerlauf", frist_bis=jetzt.mono + LEERLAUF_S, faellig=False)
        out.append(_prot("DEBUG", "leerlauf", "zaehler_gestartet", frist_s=LEERLAUF_S))
    elif z.modus == "leerlauf" and belegt(z):
        z = replace(z, modus="aktiv", faellig=False)
        out.append(_prot("DEBUG", "leerlauf", "zaehler_verworfen"))

    if z.modus == "leerlauf":
        if not z.faellig and jetzt.mono >= z.frist_bis:
            z = replace(z, faellig=True)
            if blockiert(z):
                out.append(_prot(
                    "INFO", "leerlauf", "wartet",
                    lernmodus=z.lernt, sync=z.sync_laeuft or sync_offen(z), update=z.update_laeuft,
                ))
        if z.faellig and not blockiert(z):
            z, aus = _herunterfahren(z, "leerlauf")
            out.extend(aus)
    return z, tuple(out)


def _verarbeite(z: Zustand, e: ev.Ereignis | ev.InternesEreignis, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if isinstance(e, ev.SitzungGeaendert):
        return replace(z, spielt=e.spielt, figur_liegt=e.figur_liegt, unbekannt=e.zustand == "unbekannt"), ()

    if isinstance(e, ev.LernenGeaendert):
        z = replace(z, lernt=e.aktiv)
        if not e.aktiv and z.modus == "leerlauf":
            z = replace(z, faellig=False, frist_bis=jetzt.mono + LEERLAUF_S)  # der Zähler beginnt neu
        return z, ()

    if isinstance(e, ev.Hauptknopf):
        if e.art == "lang":
            return _herunterfahren(z, "hauptknopf")
        return _bedient(z, jetzt), ()

    if isinstance(e, (ev.Weiter, ev.Zurueck, ev.LautstaerkeDrehen, ev.Kopfhoerer)):
        return _bedient(z, jetzt), ()

    if isinstance(e, ev.AkkuTiefstand):
        if z.am_lader is True:
            return z, (_prot("WARNING", "akku_tiefstand", "ignoriert", grund="am_lader"),)
        abbrechen: tuple[ev.Befehl, ...] = ()
        if z.sync_laeuft or sync_offen(z):
            abbrechen = (ev.SyncAbbrechen("akku_tiefstand"),)
        z = _wdh_ende(replace(z, sync_laeuft=False, sync_offen_bis=None))
        return _herunterfahren(z, "akku_tiefstand", *abbrechen)

    if isinstance(e, ev.LaderGeaendert):
        z = replace(z, am_lader=e.am_lader)
        if not e.am_lader:
            z = _wdh_ende(z)
        return _start_pruefung(z, jetzt)

    if isinstance(e, ev.Bereit):
        return _start_pruefung(replace(z, bereit=True), jetzt)

    if isinstance(e, ev.NetzKlasse):
        return replace(z, klasse=e.klasse), ()

    if isinstance(e, ev.SyncGestartet):
        return replace(z, sync_laeuft=True, sync_offen_bis=None), ()
    if isinstance(e, ev.SyncFertig):
        return _wdh_ende(replace(z, sync_laeuft=False, sync_offen_bis=None)), ()
    if isinstance(e, ev.SyncAbgebrochen):
        z = replace(z, sync_laeuft=False, sync_offen_bis=None)
        if not z.start_wdh:
            return z, ()
        if e.grund not in _WIEDERHOLEN_BEI or z.am_lader is not True or z.wdh_n >= START_WIEDERHOLUNGEN:
            return _wdh_ende(z), ()
        if z.wdh_bei is not None:
            return z, ()  # ein anderer Sync ist abgebrochen, der nächste Versuch steht schon
        return replace(z, wdh_bei=jetzt.mono + START_WIEDERHOLUNG_S), (
            _prot("INFO", "start_sync", "wiederholung_geplant", grund=e.grund, versuch=z.wdh_n + 1, in_s=START_WIEDERHOLUNG_S),
        )
    if isinstance(e, ev.UpdateGestartet):
        return replace(z, update_laeuft=True), ()
    if isinstance(e, ev.SelbsttestErgebnis):
        return replace(z, update_laeuft=False), ()

    if isinstance(e, ev.HaSyncAnstossen):
        abgelehnt = _ha_befehl_pruefen(z, e, "sync", jetzt)
        if abgelehnt is not None:
            return z, abgelehnt
        if z.sync_laeuft or sync_offen(z):
            return z, (_prot("INFO", "sync_befehl", "ignoriert", grund="laeuft_schon", befehl_id=e.befehl_id),)
        return replace(z, sync_offen_bis=jetzt.mono + SYNC_ANTWORT_FRIST_S), (
            ev.SyncStarten("ha"),
            _prot("INFO", "sync_befehl", "angenommen", befehl_id=e.befehl_id),
        )

    if isinstance(e, ev.HaUpdateAnstossen):
        abgelehnt = _ha_befehl_pruefen(z, e, "update", jetzt)
        if abgelehnt is not None:
            return z, abgelehnt
        detail = _update_bedingung(z)
        if detail is not None:
            return z, (
                _prot("WARNING", "update_befehl", "abgelehnt", grund="bedingung", detail=detail, befehl_id=e.befehl_id),
                _abgelehnt("update", e.befehl_id, "bedingung", detail),
            )
        return z, (
            ev.UpdateStarten(e.befehl_id, e.version),
            _prot("INFO", "update_befehl", "angenommen", befehl_id=e.befehl_id, version=e.version),
        )

    return z, ()  # ``Takt`` und alles Übrige: nur der Zähler (``_auswerten``)


def step(zustand: Zustand, ereignis: ev.Ereignis | ev.InternesEreignis, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if zustand.modus == "herunterfahren":
        return zustand, ()
    z, out = _verarbeite(zustand, ereignis, jetzt)
    z, mehr = _auswerten(z, jetzt)
    return z, out + mehr
