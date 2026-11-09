"""Ereignisse, Befehle und Hilfstypen des Kerns.

Einziger Eigentümer dieser Typen (``docs/protocol/core-interface.md``).
Alle Werte sind unveränderlich; Feldnamen sind ASCII. Dieses Modul macht keine
Ein-/Ausgabe. ``Jetzt`` steht hier (und wird von ``clock`` wieder angeboten),
damit der Kern keine Uhr-Module importieren muss.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

ZeitQuelle = Literal["system", "rtc", "ntp", "unbekannt"]


@dataclass(frozen=True, slots=True)
class Jetzt:
    """Zeit als Parameter (Abschnitt 2)."""

    mono: float
    wall: float
    zeit_quelle: ZeitQuelle = "system"
    zeit_ok: bool = True


# --------------------------------------------------------------------------
# Hilfstypen (Abschnitt 3.8)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Serie:
    """Eine Serie mit ihren Folgen (Datei oder Ordner) und deren Tracks.

    ``tracks`` bildet den Namen einer Folge auf die Pfade ihrer Tracks relativ zum
    Serien-Ordner ab; eine Folge aus einer Datei hat genau einen Track, nämlich
    ihren eigenen Namen. Fehlt ein Eintrag, ergänzt ``__post_init__`` ihn so
    (Entscheidung F, 05.11.).
    """

    id: str
    name: str
    typ: Literal["normal", "ueberraschung"]
    ordner: str
    folgen: tuple[str, ...]
    tracks: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    #: Dauer je Track in Sekunden, parallel zu ``tracks`` (Entscheidung I, 09.11.); ``None``: unbekannt.
    #: Fehlt der Eintrag einer Folge, ist ihre Dauer unbekannt.
    dauern: Mapping[str, tuple[float | None, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        fehlend = [f for f in self.folgen if f not in self.tracks]
        if fehlend:
            voll = dict(self.tracks)
            for f in fehlend:
                voll[f] = (f,)
            object.__setattr__(self, "tracks", voll)


@dataclass(frozen=True, slots=True)
class Zeiger:
    """Resume-Zustand: Serien-Zeiger (``art="serie"``) oder Folgen-Zeiger (``art="folge"``)."""

    art: Literal["serie", "folge"]
    serie_id: str
    datei: str  # Name der Folge
    index: int | None  # Nummer der Folge in ``Serie.folgen``; ``None`` bei ``art="folge"``
    track: int
    position_s: float  # Sekunden im Track, ohne Rücksprung
    zaehler: int
    #: Wanduhr (Unix-Sekunden) der letzten Benutzung (Entscheidung N, 09.11.); ``None``: unbekannt, der Zeiger läuft nie ab
    benutzt_wall: float | None = None


@dataclass(frozen=True, slots=True)
class Zuordnung:
    typ: Literal["serie", "folge", "aktion"]
    serie_id: str | None = None
    folge: str | None = None  # Name der Folge bei ``typ="folge"``
    aktion: Literal["status", "gute_nacht"] | None = None


@dataclass(frozen=True, slots=True)
class Fenster:
    id: str
    tage: tuple[int, ...]
    von: str
    bis: str
    wirkung: Literal["leiser", "stumm"]
    grenze: int | None = None


@dataclass(frozen=True, slots=True)
class LeiseZeiten:
    zeitzone: str
    fenster: tuple[Fenster, ...]


@dataclass(frozen=True, slots=True)
class GuteNacht:
    timer_min: int
    ausblenden_s: int


@dataclass(frozen=True, slots=True)
class Konfig:
    revision: int
    liste_id: str
    zuordnungen: Mapping[str, Zuordnung]
    leise_zeiten: LeiseZeiten
    gute_nacht: GuteNacht
    #: Lesezeichen laufen nach so vielen Tagen ohne Benutzung ab; 0 = nie (Entscheidung N, 09.11.)
    lesezeichen_tage: int = 14


@dataclass(frozen=True, slots=True)
class Eintrag:
    uid: str
    art: Literal["unbekannt", "gelernt"]
    zuerst: str
    zuletzt: str
    anzahl: int
    zeit_ok: bool
    befehl_id: str | None = None


# --------------------------------------------------------------------------
# Basisklassen
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Ereignis:
    """Basis aller äußeren Ereignisse."""


@dataclass(frozen=True, slots=True)
class InternesEreignis:
    """Basis der Ereignisse zwischen Teilautomaten (verlassen den Kern nie)."""


@dataclass(frozen=True, slots=True)
class Befehl:
    """Basis aller Befehle."""


# --------------------------------------------------------------------------
# 3.1 Leser
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LeserHallo(Ereignis):
    proto: int
    fw: str
    build: str
    pn5180: str


@dataclass(frozen=True, slots=True)
class Aufgelegt(Ereignis):
    uid: str
    typ: Literal["ntag", "iso15693"]
    tonie: bool
    seq: int
    vorgang: str


@dataclass(frozen=True, slots=True)
class Gesperrt(Ereignis):
    seq: int
    vorgang: str


@dataclass(frozen=True, slots=True)
class Abgehoben(Ereignis):
    seq: int
    vorgang: str | None


@dataclass(frozen=True, slots=True)
class LeserHerzschlag(Ereignis):
    present: bool
    up_s: int
    polls: int
    hits: int
    rejected: int
    errors: int
    cycle_ms: int


@dataclass(frozen=True, slots=True)
class LeserAlarm(Ereignis):
    grund: Literal["kein_herzschlag", "getrennt", "hello_timeout", "proto_unbekannt"]


@dataclass(frozen=True, slots=True)
class LeserFehler(Ereignis):
    code: str
    detail: str
    schwere: Literal["fehler", "warnung", "hinweis"]


# --------------------------------------------------------------------------
# 3.2 Player
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrackWechsel(Ereignis):
    """MPD spielt innerhalb der Folge mit dem nächsten Track weiter (keine Pause)."""

    serie_id: str
    datei: str
    track: int
    gen: int | None = field(default=None, compare=False)  # Generation des letzten ``Abspielen`` (``None``: nicht geprüft)


@dataclass(frozen=True, slots=True)
class FolgeZuEnde(Ereignis):
    """MPD hat den letzten Track der Folge zu Ende gespielt und gestoppt."""

    serie_id: str
    datei: str
    gen: int | None = field(default=None, compare=False)  # Generation des letzten ``Abspielen``


@dataclass(frozen=True, slots=True)
class PlayerPosition(Ereignis):
    serie_id: str
    datei: str
    track: int
    position_s: float
    spielt: bool
    gen: int | None = field(default=None, compare=False)  # Generation des letzten ``Abspielen``


@dataclass(frozen=True, slots=True)
class PlayerFehler(Ereignis):
    serie_id: str | None
    datei: str | None
    art: Literal["datei_fehlt", "datei_unlesbar", "mpd_fehler"]
    detail: str


@dataclass(frozen=True, slots=True)
class PlayerVerbindung(Ereignis):
    ok: bool


# --------------------------------------------------------------------------
# 3.3 Start und Daten
# --------------------------------------------------------------------------


#: Platzhalter für „ein gesperrter Tobie lag“ (er hat keine Kennung); keine gültige Kennung eines Tobies
NEUSTART_GESPERRT = "gesperrt"


@dataclass(frozen=True, slots=True)
class GeraeteEinstellungen(Ereignis):
    lautstaerke_max: int
    lautstaerke_start: int
    lautstaerke_kopfhoerer: int
    #: Kennung des Tobies, der beim Dienst-Neustart (ohne Ausschalten) auflag, sonst ``None``
    #: (Entscheidung G, 06.11.): Er startet nicht von selbst. Lag ein gesperrter Tobie (keine Kennung),
    #: steht hier ``NEUSTART_GESPERRT``.
    neustart_uid: str | None = None


@dataclass(frozen=True, slots=True)
class KonfigGeladen(Ereignis):
    konfig: Konfig


@dataclass(frozen=True, slots=True)
class BibliothekGeladen(Ereignis):
    serien: tuple[Serie, ...]


@dataclass(frozen=True, slots=True)
class ResumeGeladen(Ereignis):
    zeiger: tuple[Zeiger, ...]


@dataclass(frozen=True, slots=True)
class Bereit(Ereignis):
    pass


# --------------------------------------------------------------------------
# 3.4 Home Assistant
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HaLernmodus(Ereignis):
    befehl_id: str
    gueltig_bis: float


@dataclass(frozen=True, slots=True)
class HaLernmodusAbbruch(Ereignis):
    befehl_id: str
    gueltig_bis: float


@dataclass(frozen=True, slots=True)
class HaSyncAnstossen(Ereignis):
    befehl_id: str
    gueltig_bis: float


@dataclass(frozen=True, slots=True)
class HaUpdateAnstossen(Ereignis):
    befehl_id: str
    version: str
    gueltig_bis: float


@dataclass(frozen=True, slots=True)
class HaVerbindung(Ereignis):
    ok: bool


@dataclass(frozen=True, slots=True)
class Bestaetigt(Ereignis):
    id: str
    grund: str
    zuletzt: str
    art: Literal["unbekannt", "gelernt"]


# --------------------------------------------------------------------------
# 3.5 Bedienung und Kopfhörer
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Hauptknopf(Ereignis):
    art: Literal["kurz", "lang"]


@dataclass(frozen=True, slots=True)
class Weiter(Ereignis):
    pass


@dataclass(frozen=True, slots=True)
class Zurueck(Ereignis):
    pass


@dataclass(frozen=True, slots=True)
class LautstaerkeDrehen(Ereignis):
    delta: int


@dataclass(frozen=True, slots=True)
class Kopfhoerer(Ereignis):
    steckt: bool


# --------------------------------------------------------------------------
# 3.6 Strom, Netz, Sync, Update
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LaderGeaendert(Ereignis):
    am_lader: bool


@dataclass(frozen=True, slots=True)
class AkkuStand(Ereignis):
    prozent: int


@dataclass(frozen=True, slots=True)
class AkkuTiefstand(Ereignis):
    pass


@dataclass(frozen=True, slots=True)
class NetzKlasse(Ereignis):
    klasse: Literal["home", "hotspot", "offline"]


@dataclass(frozen=True, slots=True)
class SyncGestartet(Ereignis):
    pass


@dataclass(frozen=True, slots=True)
class SyncFertig(Ereignis):
    neu: int
    geloescht: int


@dataclass(frozen=True, slots=True)
class SyncAbgebrochen(Ereignis):
    grund: str


@dataclass(frozen=True, slots=True)
class UpdateGestartet(Ereignis):
    version: str


@dataclass(frozen=True, slots=True)
class SelbsttestErgebnis(Ereignis):
    bestanden: bool
    grund: str | None = None


# --------------------------------------------------------------------------
# 3.7 Zeit
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Takt(Ereignis):
    pass


@dataclass(frozen=True, slots=True)
class ZeitquelleGeaendert(Ereignis):
    quelle: ZeitQuelle
    vertrauenswuerdig: bool


# --------------------------------------------------------------------------
# 3.9 Interne Ereignisse
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SitzungGeaendert(InternesEreignis):
    zustand: str
    figur_liegt: bool
    spielt: bool
    serie_id: str | None


@dataclass(frozen=True, slots=True)
class AktionAusgeloest(InternesEreignis):
    aktion: Literal["status", "gute_nacht"]
    vorgang: str


@dataclass(frozen=True, slots=True)
class LernenGeaendert(InternesEreignis):
    aktiv: bool


@dataclass(frozen=True, slots=True)
class StummBeginnt(InternesEreignis):
    pass


@dataclass(frozen=True, slots=True)
class StummEndet(InternesEreignis):
    pass


@dataclass(frozen=True, slots=True)
class GrenzeGesetzt(InternesEreignis):
    name: str
    prozent: int | None


@dataclass(frozen=True, slots=True)
class LautstaerkeGeaendert(InternesEreignis):
    wirksam: int


@dataclass(frozen=True, slots=True)
class GuteNachtEnde(InternesEreignis):
    pass


@dataclass(frozen=True, slots=True)
class HerunterfahrenAngefordert(InternesEreignis):
    grund: Literal["leerlauf", "hauptknopf", "akku_tiefstand"]


@dataclass(frozen=True, slots=True)
class DienstEndet(InternesEreignis):
    """Der Dienst wird beendet (SIGTERM). Pausieren und Zeiger sichern, **kein** ``Herunterfahren``."""


# --------------------------------------------------------------------------
# 4. Befehle
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LautstaerkeSetzen(Befehl):
    prozent: int
    grenze: int


@dataclass(frozen=True, slots=True)
class AusgangWaehlen(Befehl):
    ausgang: Literal["lautsprecher", "kopfhoerer"]


@dataclass(frozen=True, slots=True)
class Abspielen(Befehl):
    serie_id: str
    ordner: str
    datei: str  # Name der Folge
    tracks: tuple[str, ...]  # Pfade der Tracks relativ zu ``ordner``, in Reihenfolge
    track: int
    position_s: float  # im Track, mit Rücksprung
    vorgang: str | None = None
    #: Wiedergabe-Generation, von der Sitzung bei jedem ``Abspielen`` um 1 erhöht; der Player
    #: trägt sie in ``PlayerPosition``, ``TrackWechsel`` und ``FolgeZuEnde`` ein. Gehört nicht
    #: zum Vergleich (Tests prüfen sie gezielt).
    gen: int = field(default=0, compare=False)


@dataclass(frozen=True, slots=True)
class Pausieren(Befehl):
    grund: Literal[
        "abgehoben",
        "folgenende",
        "knopf",
        "stumm",
        "gute_nacht",
        "leser_unbekannt",
        "fehler",
        "herunterfahren",
    ]


@dataclass(frozen=True, slots=True)
class ZeigerSpeichern(Befehl):
    art: Literal["serie", "folge"]
    serie_id: str
    datei: str
    index: int | None
    track: int
    position_s: float
    grund: Literal[
        "pause", "folgenende", "trackwechsel", "zurueck", "figurwechsel", "periodisch", "herunterfahren"
    ]
    #: Wanduhr (Unix-Sekunden) der Benutzung; ``None``, wenn die Uhr unsicher ist (Entscheidung N, 09.11.)
    wall: float | None = None


@dataclass(frozen=True, slots=True)
class TonSpielen(Befehl):
    ton: Literal[
        "start",
        "unbekannt",
        "fehler",
        "hinweis",
        "lernen_beginn",
        "lernen_ende",
        "akku_leer",
        "pruef_ok",
        "pruef_fehler",
    ]


@dataclass(frozen=True, slots=True)
class StatusPruefen(Befehl):
    vorgang: str | None = None


@dataclass(frozen=True, slots=True)
class Melden(Befehl):
    art: Literal["unbekannt", "gelernt"]
    uid: str
    befehl_id: str | None = None


@dataclass(frozen=True, slots=True)
class EreignisSenden(Befehl):
    art: Literal["fehler", "befehl_abgelehnt"]
    daten: Mapping[str, str | int | bool | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ZustandMelden(Befehl):
    sitzung: str
    strom: Literal["aktiv", "leerlauf", "herunterfahren"]
    serie_id: str | None
    lernmodus: bool
    ruhe: Literal["normal", "leiser", "stumm"]
    gute_nacht: Literal["aus", "laeuft", "ausblenden"]
    figur_liegt: bool
    folge: str | None = None  # Name der aktuellen Folge (Statusfeld ``folge``, optional)
    track: int | None = None


@dataclass(frozen=True, slots=True)
class LeserPing(Befehl):
    pass


@dataclass(frozen=True, slots=True)
class SyncStarten(Befehl):
    grund: Literal["ha", "start_lader"]


@dataclass(frozen=True, slots=True)
class SyncAbbrechen(Befehl):
    grund: Literal["akku_tiefstand"]


@dataclass(frozen=True, slots=True)
class UpdateStarten(Befehl):
    befehl_id: str
    version: str


@dataclass(frozen=True, slots=True)
class Herunterfahren(Befehl):
    grund: Literal["leerlauf", "hauptknopf", "akku_tiefstand"]


@dataclass(frozen=True, slots=True)
class Protokoll(Befehl):
    baustein: str
    ebene: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    ereignis: str
    ergebnis: str
    vorgang: str | None = None
    daten: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)
