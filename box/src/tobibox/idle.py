"""Teilautomat Strom / Leerlauf (``core-interface.md``, 5.2 und 9 Punkt 9; Tabelle „Strom / Leerlauf“, CUJ 16, 23 bis 25).

Reine Funktionen: kein Zugriff auf Dateien, Netz, Uhr oder Zufall. Zustände ``aktiv``, ``leerlauf`` (nichts wird gespielt, die Box ist
*Bereit*), ``herunterfahren``. Alle Fristen laufen auf ``jetzt.mono``.

**Strom, Frist und Andocken (Ein/Aus, 10.11.).** „Strom“ heißt Strom am Eingang der Box aus jeder Quelle. Zwei Quellen liefern ihn
(``stromwert.StromQuellen``): ``pisugar-server`` und der Leser (Zeile ``LADER``); bei Widerspruch gilt der Leser, solange seine Verbindung
steht und der Wert aus der aktuellen Verbindung stammt (V2: ``LeserHallo`` und ``LeserAlarm`` löschen ihn).

* **Frist ``LEERLAUF_S`` = 600 s, nur ohne Strom.** Der Zähler läuft nur, wenn nichts gespielt wird (``belegt``: die Sitzung spielt oder ist
  ``unbekannt``; ein liegender Tobie allein zählt nicht, Entscheidung O) **und kein Strom anliegt**. Strom kommt: der Zähler wird verworfen.
  Strom geht: er beginnt **ab diesem Zeitpunkt** neu (R9). Mit Strom schaltet die Box nie von selbst ab.
* **Unbekannt.** Hat noch keine Quelle einen Wert geliefert, ist der Strom unbekannt: der Zähler zählt nicht, nichts wird ausgelöst. Nach
  ``STROM_UNBEKANNT_S`` = 60 s seit dem ersten Aufruf gilt unbekannt als kein Strom (der Zähler beginnt dann). Unbekannt zählt für Tiefstand,
  Update und Netz-Regel wie „kein Strom“ (V15).
* **Erste Messung** (der erste Wert irgendeiner Quelle im laufenden Dienst, auch ein später): Der Zustand folgt dem Wert sofort (V4); die
  Rückmeldung (Ring, Ton) entfällt. Ist er „Strom“, gibt ``idle`` einmal ``SyncStarten("start_lader")`` aus, sobald ``Bereit`` da ist.
* **Andocken / Abziehen** sind ein Wechsel des **zusammengeführten** Werts nach der ersten Messung, ausgelöst durch eine Quelle, die vorher schon
  einen Wert hatte (V3: der erste Wert einer zweiten Quelle und das Löschen des Leser-Werts sind keine Rückmeldung). Die Rückmeldung gibt es nur,
  wenn die Sperre ``LADER_SPERRE_S`` frei ist (seit der letzten Rückmeldung **und** seit ``Bereit``): ``AkkuAnzeigen`` (Ring; 5 s, spielt die
  Sitzung 3 s), beim Andocken dazu der Ton ``lader`` (nur wenn nichts spielt und kein Update läuft; Regel 6.2.2a streicht ihn in Leise-Zeiten,
  bei unsicherer Uhr und im Lernmodus) und ein Sync-Check (einmal, nicht während eines Updates). Im Zustand ``herunterfahren`` gibt es keine
  Rückmeldung (V15).
* **Widerspruch** der Quellen wird erst protokolliert (WARNING), wenn er ``STROM_WIDERSPRUCH_S`` anhält, sonst nur DEBUG (V16).
* Die Wiederholung des Start-Syncs ist entfallen; den nächsten Anstoß geben der Takt, das Andocken und HA.

**Was „Leerlauf“ heißt** (Entscheidung O, 09.11.). Es wird nichts gespielt, **egal ob ein Tobie liegt**. Das steht hier als
``belegt``. Ein liegender Tobie in ``pausiert``, ``beendet`` oder ``gehalten`` hält die Box nicht an (Gute Nacht, „stumm“-Fenster: sonst bliebe
sie die ganze Nacht an). Es gelten weiter die Ausnahmen Sync, Update und Lernmodus; Bedienung setzt den Zähler zurück. Beim
Einschalten spielt ein liegender Tobie wie bisher sofort weiter (Entscheidung G).

**Bedienung setzt den Zähler zurück** (Entscheidung der Projektleitung, AP 4.8): Hauptknopf (kurz), ``Weiter``, ``Zurueck``,
``LautstaerkeDrehen`` und ``Kopfhoerer``. HA-Befehle (Sync, Update) setzen den Zähler nicht zurück.

**Abschaltung nach ``LEERLAUF_S``.** Läuft der Zähler ab, ist die Abschaltung ``faellig``. Sie wartet, solange der Lernmodus läuft, ein Sync
oder ein Update läuft oder ein Sync **offen** ist (``SyncStarten`` ausgegeben, Antwort fehlt noch, höchstens ``SYNC_ANTWORT_FRIST_S``).
Die Wartezeit ist ein Zustand, kein neuer Zähler: Endet der Sync oder das Update und die Box ist noch im Leerlauf ohne Strom, fährt sie sofort
herunter. Endet der **Lernmodus**, beginnt der Zähler neu. Kommt Strom, verfällt die Abschaltung.

``Hauptknopf`` lang und ``AkkuTiefstand`` (nicht am Lader) fahren immer herunter, auch während Sync, Update oder Lernmodus (am Strom ignoriert
``idle`` den Tiefstand). Beim Tiefstand wird ein laufender oder offener Sync abgebrochen und einmal der Ton ``akku_leer`` ausgegeben (B12).

**Ein fehlgeschlagenes Herunterfahren ist nicht endgültig** (B1, 09.11.). Meldet ``power`` ``HerunterfahrenFehlgeschlagen``, verlässt ``idle``
den Zustand ``herunterfahren`` und zählt neu; Protokoll und ``EreignisSenden("fehler")`` an HA. Am Mac (``simuliert=True``) wird das Herunterfahren
nur protokolliert; nach ``SIMULATION_RUECKKEHR_S`` kehrt ``idle`` in den normalen Zustand zurück.

**HA-Befehle ``HaSyncAnstossen`` / ``HaUpdateAnstossen``** prüft ``idle`` (Ablaufzeit, Uhr, beim Update die Bedingungen) und reicht sie als
``SyncStarten("ha")`` / ``UpdateStarten`` weiter (Punkt 9.9).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from . import events as ev
from .events import Jetzt
from .stromwert import StromQuellen

#: 10 min Leerlauf ohne Strom bis zur Abschaltung (``core-interface.md``, Konstanten; vorher 20 min).
LEERLAUF_S = 600.0
#: Sperre für jede Rückmeldung beim Andocken oder Abziehen (Ring, Ton, Sync), gerechnet ab der letzten Rückmeldung oder ab ``Bereit``.
LADER_SPERRE_S = 10.0
#: So lange gilt „Strom unbekannt“; danach „kein Strom“.
STROM_UNBEKANNT_S = 60.0
#: Ein Widerspruch der beiden Strom-Quellen wird erst nach so langer Dauer als WARNING protokolliert (V16).
STROM_WIDERSPRUCH_S = 5.0
#: Dauer der Akku-Anzeige am Ring beim Andocken und Abziehen; spielt die Sitzung, die kürzere.
ANDOCK_RING_S = 5.0
ANDOCK_RING_SPIELT_S = 3.0
#: So lange hält ein ausgegebenes ``SyncStarten`` ohne Antwort die Abschaltung höchstens auf.
SYNC_ANTWORT_FRIST_S = 60.0
#: Am Mac wird das Herunterfahren nur protokolliert; so lange bleibt ``idle`` danach in ``herunterfahren`` (B1).
SIMULATION_RUECKKEHR_S = 10.0

Ausgabe = tuple[ev.Befehl | ev.InternesEreignis, ...]


@dataclass(frozen=True, slots=True)
class Zustand:
    modus: str = "aktiv"  # "aktiv" | "leerlauf" | "herunterfahren"
    frist_bis: float | None = None  # mono; nur in ``leerlauf`` ohne Strom, sonst ``None`` (der Zähler läuft nicht)
    faellig: bool = False  # nur in ``leerlauf``: die Zeit ist um, die Abschaltung wartet auf Sync, Update, Lernmodus
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
    quellen: StromQuellen = StromQuellen()  # Strom: letzter Wert je Quelle
    gemessen: bool = False  # irgendeine Quelle hat schon einen Wert geliefert (die erste Messung ist vorbei)
    start_mono: float | None = None  # mono des ersten Aufrufs (für ``STROM_UNBEKANNT_S``)
    klasse: str | None = None
    bereit: bool = False
    bereit_mono: float | None = None
    rueckmeldung_mono: float | None = None  # letzte Rückmeldung (Ring, Ton, Sync) beim Andocken oder Abziehen
    start_geprueft: bool = False  # der Sync-Check der ersten Messung (oder ein Andocken) ist erledigt
    widerspruch_seit: float | None = None  # mono; die Quellen widersprechen sich seit diesem Zeitpunkt
    widerspruch_gemeldet: bool = False
    # Rückkehr aus ``herunterfahren`` (Simulation): Zeitpunkt auf ``mono``
    ende_bis: float | None = None

    @property
    def am_lader(self) -> bool | None:
        """Der zusammengeführte Strom-Wert (``None``: noch von keiner Quelle geliefert)."""
        return self.quellen.wert


def neuer_zustand() -> Zustand:
    return Zustand()


def kennzeichen(zustand: Zustand) -> str:
    return zustand.modus


def belegt(z: Zustand) -> bool:
    """Gegenteil von Leerlauf: es spielt etwas (ein liegender Tobie allein zählt nicht, Entscheidung O)."""
    return z.spielt or z.unbekannt


def sync_offen(z: Zustand) -> bool:
    return z.sync_offen_bis is not None


def blockiert(z: Zustand) -> bool:
    """Wartet die Abschaltung auf etwas? Lernmodus, Sync, Update oder ein offener Sync."""
    return z.lernt or z.sync_laeuft or z.update_laeuft or sync_offen(z)


def strom(z: Zustand, jetzt: Jetzt) -> bool | None:
    """Strom für die Frist: der zusammengeführte Wert; ohne Wert nach ``STROM_UNBEKANNT_S`` „kein Strom“, davor ``None`` (unbekannt)."""
    w = z.quellen.wert
    if w is not None:
        return w
    if z.start_mono is not None and jetzt.mono - z.start_mono >= STROM_UNBEKANNT_S:
        return False
    return None


def _prot(ebene: str, ereignis: str, ergebnis: str, **daten: str | int | float | bool | None) -> ev.Protokoll:
    return ev.Protokoll("idle", ebene, ereignis, ergebnis, None, daten)  # type: ignore[arg-type]


def _herunterfahren(z: Zustand, grund: str, *vorher: ev.Befehl | ev.InternesEreignis) -> tuple[Zustand, Ausgabe]:
    neu = replace(z, modus="herunterfahren", faellig=False, frist_bis=None)
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
    """Erste nicht erfüllte Bedingung für ein Update (Text für ``detail``), sonst ``None``. Unbekannter Strom zählt als „kein Strom“ (V15)."""
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


def _sync_check(z: Zustand, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Erste bekannte Messung „Strom“: einmal prüfen, ob ein Sync ansteht (``sync`` entscheidet nach der Netz-Regel)."""
    if z.start_geprueft or not z.bereit or z.am_lader is not True:
        return z, ()
    return replace(z, start_geprueft=True, sync_offen_bis=jetzt.mono + SYNC_ANTWORT_FRIST_S), (
        ev.SyncStarten("start_lader"),
        _prot("INFO", "start_sync", "angefordert", grund="start_lader"),
    )


def _sperre_frei(z: Zustand, jetzt: Jetzt) -> bool:
    if not z.bereit or z.bereit_mono is None:
        return False
    ab = z.bereit_mono if z.rueckmeldung_mono is None else max(z.bereit_mono, z.rueckmeldung_mono)
    return jetzt.mono >= ab + LADER_SPERRE_S


def _bedient(z: Zustand, jetzt: Jetzt) -> Zustand:
    """Bedienung (Taste, Drehregler, Kopfhörer): der Zähler beginnt neu (nur wenn er läuft, also ohne Strom)."""
    if z.modus == "leerlauf" and z.frist_bis is not None:
        return replace(z, faellig=False, frist_bis=jetzt.mono + LEERLAUF_S)
    return z


def _widerspruch(z: Zustand, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Widerspruch der Quellen: DEBUG beim Beginn, WARNING erst nach ``STROM_WIDERSPRUCH_S`` (V16), einmal je Widerspruch."""
    if not z.quellen.widerspruch:
        if z.widerspruch_seit is None:
            return z, ()
        return replace(z, widerspruch_seit=None, widerspruch_gemeldet=False), ()
    if z.widerspruch_seit is None:
        return replace(z, widerspruch_seit=jetzt.mono), (
            _prot("DEBUG", "strom", "widerspruch_beginnt", pisugar=z.quellen.pisugar, leser=z.quellen.leser),
        )
    if not z.widerspruch_gemeldet and jetzt.mono - z.widerspruch_seit >= STROM_WIDERSPRUCH_S:
        return replace(z, widerspruch_gemeldet=True), (
            _prot("WARNING", "strom", "widerspruch", pisugar=z.quellen.pisugar, leser=z.quellen.leser, gilt="leser"),
        )
    return z, ()


def _auswerten(z: Zustand, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Zähler und Abschaltung nach jedem Ereignis nachführen."""
    if z.modus == "herunterfahren":
        return z, ()
    out: list[ev.Befehl | ev.InternesEreignis] = []

    if z.sync_offen_bis is not None and jetzt.mono >= z.sync_offen_bis:
        z = replace(z, sync_offen_bis=None)
        out.append(_prot("WARNING", "sync_antwort", "fehlt"))

    z, w = _widerspruch(z, jetzt)
    out.extend(w)

    if z.modus == "aktiv" and not belegt(z):
        z = replace(z, modus="leerlauf", frist_bis=None, faellig=False)
        out.append(_prot("DEBUG", "leerlauf", "bereit"))
    elif z.modus == "leerlauf" and belegt(z):
        z = replace(z, modus="aktiv", faellig=False, frist_bis=None)
        out.append(_prot("DEBUG", "leerlauf", "zaehler_verworfen"))

    if z.modus == "leerlauf":
        s = strom(z, jetzt)
        if s is not False:
            # mit Strom oder noch unbekannt: der Zähler läuft nicht (Strom verwirft ihn)
            if z.frist_bis is not None or z.faellig:
                out.append(_prot("DEBUG", "leerlauf", "zaehler_verworfen", grund="strom" if s else "unbekannt"))
            z = replace(z, frist_bis=None, faellig=False)
        elif z.frist_bis is None:
            z = replace(z, frist_bis=jetzt.mono + LEERLAUF_S, faellig=False)
            out.append(_prot("DEBUG", "leerlauf", "zaehler_gestartet", frist_s=LEERLAUF_S))
        if z.frist_bis is not None:
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


def _strom_geaendert(z: Zustand, e: ev.LaderGeaendert, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Ein Strom-Wert einer Quelle. Der Zustand folgt dem zusammengeführten Wert sofort (V4); Rückmeldungen nur bei Andocken und Abziehen."""
    vorher_quelle = z.quellen.leser if e.quelle == "leser" else z.quellen.pisugar
    alt = z.quellen.wert
    z = replace(z, quellen=z.quellen.mit(e))
    neu = z.quellen.wert
    erste = not z.gemessen
    z = replace(z, gemessen=True)
    if erste or vorher_quelle is None:
        # erste Messung, oder erster Wert einer zweiten Quelle (V3): nur der Sync-Check, nie Ring oder Ton
        return _sync_check(z, jetzt)
    if neu == alt or alt is None or neu is None:
        return z, ()
    z = replace(z, start_geprueft=True)  # ein richtiges Andocken oder Abziehen ersetzt den Sync-Check der ersten Messung
    if z.modus == "herunterfahren" or not _sperre_frei(z, jetzt):
        return z, (_prot("DEBUG", "strom", "rueckmeldung_gesperrt", strom=neu),)
    z = replace(z, rueckmeldung_mono=jetzt.mono)
    belegt_jetzt = belegt(z)
    dauer = ANDOCK_RING_SPIELT_S if belegt_jetzt else ANDOCK_RING_S
    out: list[ev.Befehl | ev.InternesEreignis] = [
        _prot("INFO", "strom", "andocken" if neu else "abziehen", pisugar=z.quellen.pisugar, leser=z.quellen.leser),
        ev.AkkuAnzeigen("andocken" if neu else "abziehen", dauer),
    ]
    if neu:
        if not belegt_jetzt and not z.update_laeuft:
            out.append(ev.TonSpielen("lader"))  # Regel 6.2.2a des Kerns streicht ihn in Leise-Zeiten, bei unsicherer Uhr, im Lernmodus
        if not z.update_laeuft and not z.sync_laeuft and not sync_offen(z):
            z = replace(z, sync_offen_bis=jetzt.mono + SYNC_ANTWORT_FRIST_S)
            out += [ev.SyncStarten("start_lader"), _prot("INFO", "start_sync", "angefordert", grund="andocken")]
    return z, tuple(out)


def _leser_verbindung(z: Zustand, jetzt: Jetzt, grund: str) -> tuple[Zustand, Ausgabe]:
    """Neues ``HELLO`` oder Ausfall des Lesers: sein Strom-Wert gilt nicht mehr (V2), es gilt ``pisugar``. Keine Rückmeldung (V3)."""
    if z.quellen.leser is None:
        return z, ()
    return replace(z, quellen=StromQuellen(z.quellen.pisugar, None)), (_prot("DEBUG", "strom", "leser_wert_verfallen", grund=grund),)


def _verarbeite(z: Zustand, e: ev.Ereignis | ev.InternesEreignis, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if isinstance(e, ev.SitzungGeaendert):
        return replace(z, spielt=e.spielt, figur_liegt=e.figur_liegt, unbekannt=e.zustand == "unbekannt"), ()

    if isinstance(e, ev.LernenGeaendert):
        z = replace(z, lernt=e.aktiv)
        if not e.aktiv and z.modus == "leerlauf" and z.frist_bis is not None:
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
        z = replace(z, sync_laeuft=False, sync_offen_bis=None)
        return _herunterfahren(z, "akku_tiefstand", *abbrechen, ev.TonSpielen("akku_leer"))

    if isinstance(e, ev.LaderGeaendert):
        return _strom_geaendert(z, e, jetzt)

    if isinstance(e, (ev.LeserHallo, ev.LeserAlarm)):
        return _leser_verbindung(z, jetzt, "hello" if isinstance(e, ev.LeserHallo) else "ausfall")

    if isinstance(e, ev.Bereit):
        return _sync_check(replace(z, bereit=True, bereit_mono=jetzt.mono), jetzt)

    if isinstance(e, ev.NetzKlasse):
        return replace(z, klasse=e.klasse), ()

    if isinstance(e, ev.SyncGestartet):
        return replace(z, sync_laeuft=True, sync_offen_bis=None), ()
    if isinstance(e, (ev.SyncFertig, ev.SyncAbgebrochen)):
        return replace(z, sync_laeuft=False, sync_offen_bis=None), ()
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


def _zurueck_aus_herunterfahren(z: Zustand, jetzt: Jetzt, *vorher: ev.Befehl) -> tuple[Zustand, Ausgabe]:
    """Das Herunterfahren hat nicht gewirkt: wieder ``aktiv``, der Leerlauf-Zähler beginnt neu (ohne Strom)."""
    z = replace(z, modus="aktiv", faellig=False, frist_bis=None, ende_bis=None)
    z, mehr = _auswerten(z, jetzt)
    return z, (*vorher, *mehr)


def _im_herunterfahren(z: Zustand, e: ev.Ereignis | ev.InternesEreignis, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """``herunterfahren`` ist beschlossen: nur das Ergebnis des Befehls und der Zustand der Umgebung zählen (keine Rückmeldung, V15)."""
    if isinstance(e, ev.HerunterfahrenFehlgeschlagen):
        if e.simuliert:
            if z.ende_bis is not None:
                return z, ()
            return replace(z, ende_bis=jetzt.mono + SIMULATION_RUECKKEHR_S), (
                _prot("INFO", "herunterfahren", "simuliert", rueckkehr_in_s=SIMULATION_RUECKKEHR_S),
            )
        text = f"Herunterfahren fehlgeschlagen: {e.detail}"[:200] if e.detail else "Herunterfahren fehlgeschlagen."
        return _zurueck_aus_herunterfahren(
            z, jetzt,
            _prot("ERROR", "herunterfahren", "fehlgeschlagen", detail=e.detail[:200]),
            ev.EreignisSenden("fehler", {"baustein": "power", "code": "herunterfahren_fehlgeschlagen", "text": text}),
        )
    if z.ende_bis is not None and jetzt.mono >= z.ende_bis:
        return _zurueck_aus_herunterfahren(z, jetzt, _prot("INFO", "herunterfahren", "simulation_zurueck"))
    # Umgebung nachführen, damit die Rückkehr auf dem richtigen Stand beginnt (keine Befehle)
    if isinstance(e, ev.SitzungGeaendert):
        z = replace(z, spielt=e.spielt, figur_liegt=e.figur_liegt, unbekannt=e.zustand == "unbekannt")
    elif isinstance(e, ev.LernenGeaendert):
        z = replace(z, lernt=e.aktiv)
    elif isinstance(e, ev.LaderGeaendert):
        z = replace(z, quellen=z.quellen.mit(e), gemessen=True)
    elif isinstance(e, (ev.LeserHallo, ev.LeserAlarm)):
        z = replace(z, quellen=StromQuellen(z.quellen.pisugar, None))
    elif isinstance(e, ev.NetzKlasse):
        z = replace(z, klasse=e.klasse)
    return z, ()


def step(zustand: Zustand, ereignis: ev.Ereignis | ev.InternesEreignis, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if zustand.start_mono is None:
        zustand = replace(zustand, start_mono=jetzt.mono)
    if zustand.modus == "herunterfahren":
        return _im_herunterfahren(zustand, ereignis, jetzt)
    z, out = _verarbeite(zustand, ereignis, jetzt)
    z, mehr = _auswerten(z, jetzt)
    return z, out + mehr
