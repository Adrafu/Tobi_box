"""Gemeinsame Hilfen: simulierte Uhr, Beispieldaten, Harnische für Sitzung und Kern."""

from __future__ import annotations

import pytest

from tobibox import core, session
from tobibox import events as ev
from tobibox.clock import SimUhr

# Kennungen (erfundene Testwerte)
UID_S1 = "04a1b2c3"  # Serie s1
UID_S2 = "04a1b2c4"  # Serie s2
UID_UNBEKANNT = "04ffeedd"
UID_NACHT = "04c0ffee"  # Aktion gute_nacht
UID_STATUS = "04dead01"  # Aktion status
UID_FEHLT = "04bbbb01"  # zugeordnet auf eine Serie, die die Box nicht kennt
UID_TONIE = "e0040312345678ab"

S1 = ev.Serie("s1", "Serie 1", "normal", "s1", ("a.mp3", "b.mp3", "c.mp3"))
S2 = ev.Serie("s2", "Serie 2", "normal", "s2", ("x.mp3", "y.mp3"))
UEB = ev.Serie("ueb", "Überraschung", "ueberraschung", "ueb", ("u1.mp3",))

# Folgen-Tobies (Entscheidung F, 05.11.) und eine Serie mit Folge aus mehreren Tracks
UID_FOLGE = "04a1b2c5"  # Folge b.mp3 der Serie s1
UID_FOLGE_FEHLT = "04a1b2c6"  # Serie s1, aber Folge gibt es nicht
UID_CD = "04a1b2c7"  # Folge "cd" der Serie s3 (drei Tracks)
UID_S3 = "04a1b2c8"  # Serie s3

S3 = ev.Serie(
    "s3", "Serie 3", "normal", "s3", ("cd", "z.mp3"),
    {"cd": ("cd/01.mp3", "cd/02.mp3", "cd/03.mp3"), "z.mp3": ("z.mp3",)},
)

ZUORDNUNGEN = {
    UID_S1: ev.Zuordnung("serie", "s1"),
    UID_S2: ev.Zuordnung("serie", "s2"),
    UID_FEHLT: ev.Zuordnung("serie", "unbekannte-serie"),
    UID_NACHT: ev.Zuordnung("aktion", aktion="gute_nacht"),
    UID_STATUS: ev.Zuordnung("aktion", aktion="status"),
    UID_FOLGE: ev.Zuordnung("folge", "s1", "b.mp3"),
    UID_FOLGE_FEHLT: ev.Zuordnung("folge", "s1", "gibt-es-nicht.mp3"),
    UID_CD: ev.Zuordnung("folge", "s3", "cd"),
    UID_S3: ev.Zuordnung("serie", "s3"),
}


def abspielen(serie_id, ordner, datei, position_s, vorgang=None, track=0, tracks=None):
    """``Abspielen`` für eine Folge aus einer Datei (``tracks=(datei,)``) oder mit ``tracks``."""
    return ev.Abspielen(serie_id, ordner, datei, tracks if tracks is not None else (datei,), track, position_s, vorgang)


def zeiger_speichern(serie_id, datei, index, position_s, grund, track=0, art="serie"):
    return ev.ZeigerSpeichern(art, serie_id, datei, None if art == "folge" else index, track, position_s, grund)


def zeiger(serie_id, datei, index, position_s, zaehler, track=0, art="serie"):
    return ev.Zeiger(art, serie_id, datei, None if art == "folge" else index, track, position_s, zaehler)


def ppos(serie_id, datei, position_s, spielt=True, track=0):
    return ev.PlayerPosition(serie_id, datei, track, position_s, spielt)


def mk_konfig(zuordnungen=None, revision=1) -> ev.Konfig:
    return ev.Konfig(
        revision=revision,
        liste_id="liste-1",
        zuordnungen=dict(ZUORDNUNGEN if zuordnungen is None else zuordnungen),
        leise_zeiten=ev.LeiseZeiten("Europe/Berlin", ()),
        gute_nacht=ev.GuteNacht(30, 60),
    )


def kern(out) -> list:
    """Nur die Befehle und äußeren Folgen: ohne Protokoll und ``SitzungGeaendert``."""
    return [o for o in out if not isinstance(o, (ev.Protokoll, ev.SitzungGeaendert))]


def typen(out) -> list[type]:
    return [type(o) for o in out]


@pytest.fixture
def uhr() -> SimUhr:
    return SimUhr()


class SitzungsHarnisch:
    """Treibt den Teilautomaten ``session`` mit simulierter Uhr."""

    def __init__(self, serien=(S1, S2, UEB, S3), konfig=True, wirksam=40, zeiger=()) -> None:
        self.uhr = SimUhr()
        self.z = session.neuer_zustand()
        self.voll: tuple = ()
        self.alle: list = []
        self.sende(ev.GeraeteEinstellungen(60, 40, 25))
        self.sende(ev.BibliothekGeladen(tuple(serien)))
        if konfig:
            self.sende(ev.KonfigGeladen(mk_konfig()))
        self.sende(ev.ResumeGeladen(tuple(zeiger)))
        self.sende(ev.LautstaerkeGeaendert(wirksam))

    @property
    def modus(self) -> str:
        return session.kennzeichen(self.z)

    def sende(self, e, dt: float = 0.0) -> list:
        if dt:
            self.uhr.vor(dt)
        self.z, self.voll = session.step(self.z, e, self.uhr.jetzt())
        self.alle.extend(self.voll)
        return kern(self.voll)

    def takt(self, sekunden: float, schritt: float = 0.1) -> list:
        """Takte im Abstand ``schritt`` für ``sekunden``; gibt alle Befehle zurück."""
        gesammelt: list = []
        n = round(sekunden / schritt)
        for _ in range(n):
            gesammelt += self.sende(ev.Takt(), dt=schritt)
        return gesammelt

    # --- Hilfen zum Herstellen der sechs Zustände -------------------------

    def auflegen(self, uid=UID_S1, vorgang="v1", typ="ntag") -> list:
        return self.sende(ev.Aufgelegt(uid, typ, False, 0, vorgang))  # type: ignore[arg-type]

    def position(self, serie="s1", datei="a.mp3", sek=10.0, track=0) -> None:
        self.sende(ppos(serie, datei, sek, True, track))


def in_zustand(name: str, **kw) -> SitzungsHarnisch:
    """Harnisch im gewünschten Zustand. Figur ``v1`` (Serie s1) wo eine liegt."""
    h = SitzungsHarnisch(**kw)
    if name == "leer":
        pass
    elif name == "spielt":
        h.auflegen()
        h.position()
    elif name == "pausiert":  # Figur liegt
        h.auflegen()
        h.position()
        h.sende(ev.Hauptknopf("kurz"))
    elif name == "pausiert_ohne_figur":
        h.auflegen()
        h.position()
        h.sende(ev.Abgehoben(1, "v1"))
    elif name == "beendet":
        h.auflegen()
        h.position()
        h.sende(ev.FolgeZuEnde("s1", "a.mp3"))
    elif name == "gehalten":
        h.sende(ev.StummBeginnt())
        h.auflegen()
    elif name == "unbekannt":
        h.auflegen()
        h.position()
        h.sende(ev.LeserAlarm("kein_herzschlag"))
    else:
        raise ValueError(name)
    assert h.modus == name.replace("_ohne_figur", ""), (name, h.modus)
    return h


class KernHarnisch:
    """Treibt ``core.step`` mit simulierter Uhr."""

    def __init__(self, serien=(S1, S2, UEB, S3), einstellungen=(60, 40, 25), start=True) -> None:
        self.uhr = SimUhr()
        self.z = core.neuer_zustand()
        self.voll: tuple = ()
        if start:
            self.sende(ev.GeraeteEinstellungen(*einstellungen))
            self.sende(ev.KonfigGeladen(mk_konfig()))
            self.sende(ev.BibliothekGeladen(tuple(serien)))
            self.sende(ev.ResumeGeladen(()))
            self.sende(ev.Bereit())

    def sende(self, e, dt: float = 0.0) -> tuple:
        if dt:
            self.uhr.vor(dt)
        self.z, self.voll = core.step(self.z, e, self.uhr.jetzt())
        return self.voll

    @property
    def modus(self) -> str:
        return self.z.session.modus


# ==========================================================================
# CUJ-Harnisch (tests/cuj): echter Kern, echte Bibliothek aus erzeugten Dateien,
# echter Speicher (resume.json) und ein simulierter Player, der Tracks nach ihrer
# echten Länge abspielt. Kein MPD, keine Hardware.
# ==========================================================================


class SimPlayer:
    """Spielt die Tracks eines ``Abspielen`` nach ihrer Länge ab und sendet dieselben
    Ereignisse wie ``player.py``: ``PlayerPosition`` (Track, jede Sekunde), ``TrackWechsel``
    mit sofortiger Position, am Ende Endposition und ``FolgeZuEnde``; danach steht er still."""

    def __init__(self, medien, senden) -> None:
        self.medien = medien
        self.senden = senden
        self.b: ev.Abspielen | None = None
        self.track = 0
        self.elapsed = 0.0
        self.spielt = False
        self._seit_position = 0.0
        self.warteschlangen: list[tuple[str, ...]] = []

    @staticmethod
    def laenge(pfad) -> float:
        import wave

        with wave.open(str(pfad)) as w:
            return w.getnframes() / w.getframerate()

    def abspielen(self, b: ev.Abspielen) -> None:
        self.b = b
        self.track = b.track
        self.elapsed = b.position_s
        self.spielt = True
        self._seit_position = 0.0
        self.warteschlangen.append(b.tracks)
        self._position(True)

    def pausieren(self) -> None:
        if self.b is not None and self.spielt:
            self.spielt = False
            self._position(False)

    def _position(self, spielt: bool) -> None:
        assert self.b is not None
        self.senden(ev.PlayerPosition(self.b.serie_id, self.b.datei, self.track, round(self.elapsed, 3), spielt))

    def vor(self, dt: float) -> None:
        """Die Zeit läuft ``dt`` Sekunden weiter (höchstens ein Wechsel je Aufruf)."""
        if not self.spielt or self.b is None:
            return
        b = self.b
        self.elapsed += dt
        self._seit_position += dt
        dauer = self.laenge(self.medien / b.ordner / b.tracks[self.track])
        if self.elapsed >= dauer - 1e-9:
            if self.track + 1 < len(b.tracks):
                self.track += 1
                self.elapsed = 0.0
                self._seit_position = 0.0
                self.senden(ev.TrackWechsel(b.serie_id, b.datei, self.track))
                self._position(True)
            else:
                self.elapsed = dauer
                self.spielt = False
                self._position(False)
                self.senden(ev.FolgeZuEnde(b.serie_id, b.datei))
        elif self._seit_position >= 1.0 - 1e-9:
            self._seit_position = 0.0
            self._position(True)


class CujBox:
    """Der Dienst ohne Ein-/Ausgabe: Kern + Speicher + SimPlayer + simulierte Uhr.

    ``neustart()`` baut Kern und Speicher neu auf und lädt die Dateien, als wäre der Dienst
    neu gestartet worden (Zustandsdateien bleiben)."""

    def __init__(self, tmp_path, zuordnungen, serien_aufbau=None) -> None:
        from tobibox import library
        from tobibox.store import ResumeStore

        self.medien = tmp_path / "medien"
        self.zustand = tmp_path / "var"
        self.zustand.mkdir(parents=True, exist_ok=True)
        self.zuordnungen = dict(zuordnungen)
        if serien_aufbau is not None:
            serien_aufbau(self.medien)
        self.uhr = SimUhr()
        self.log: list = []  # alle Befehle in Reihenfolge
        self.protokoll: list = []
        self._library = library
        self._ResumeStore = ResumeStore
        self.player = SimPlayer(self.medien, self.sende)
        self.start()

    def start(self) -> None:
        self.kern = core.neuer_zustand()
        self.resume = self._ResumeStore(self.zustand)
        self.player.b = None
        self.player.spielt = False
        for e in (
            ev.GeraeteEinstellungen(60, 40, 25),
            ev.KonfigGeladen(mk_konfig(self.zuordnungen)),
            self._library.lade_bibliothek(self.medien).ereignis(),
            self.resume.laden(),
            ev.Bereit(),
        ):
            self.sende(e)

    neustart = start

    def sende(self, e, dt: float = 0.0) -> list:
        if dt:
            self.uhr.vor(dt)
        self.kern, befehle = core.step(self.kern, e, self.uhr.jetzt())
        for b in befehle:
            self.log.append(b)
            if isinstance(b, ev.Abspielen):
                self.player.abspielen(b)
            elif isinstance(b, ev.Pausieren):
                self.player.pausieren()
            elif isinstance(b, ev.ZeigerSpeichern):
                self.resume.speichern(b, self.uhr.mono)
            elif isinstance(b, ev.Protokoll):
                self.protokoll.append(b)
        return list(befehle)

    def laufe(self, sekunden: float) -> None:
        """Die Zeit läuft (Takt alle 0,1 s, Player und Kern gemeinsam)."""
        for _ in range(round(sekunden / 0.1)):
            self.uhr.vor(0.1)
            self.player.vor(0.1)
            self.sende(ev.Takt())

    # --- Bedienung wie am Leser --------------------------------------------------

    def auflege(self, uid: str, vorgang: str = "v1") -> list:
        return self.sende(ev.Aufgelegt(uid, "ntag", False, 0, vorgang))

    def hebe_ab(self, vorgang: str = "v1") -> list:
        return self.sende(ev.Abgehoben(1, vorgang))

    # --- Abfragen ---------------------------------------------------------------------

    def befehle(self, typ: type, ab: int = 0) -> list:
        return [b for b in self.log[ab:] if isinstance(b, typ)]

    @property
    def modus(self) -> str:
        return self.kern.session.modus

    def resume_json(self) -> dict:
        import json

        return json.loads((self.zustand / "resume.json").read_text(encoding="utf-8"))
