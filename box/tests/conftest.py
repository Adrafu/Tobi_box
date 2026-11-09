"""Gemeinsame Hilfen: simulierte Uhr, Beispieldaten, Harnische für Sitzung und Kern."""

from __future__ import annotations

import io
import json
import logging
import shutil
import tempfile
from pathlib import Path

import pytest
from integration.conftest import mpd  # noqa: F401  (Fixture ``mpd``: echtes MPD, übersprungen ohne ``mpd``)

from tobibox import core, eventlog, session
from tobibox import events as ev
from tobibox.clock import SimUhr

# Unix-Sockets: macOS erlaubt höchstens 104 Bytes Pfad (Linux 108), ``tmp_path`` ist dort deutlich länger
# (``/private/var/folders/...``). Tests mit Socket legen ihr Zustandsverzeichnis daher hier an.
_KURZE_VERZEICHNISSE: list[Path] = []


def kurzes_verzeichnis() -> Path:
    """Ein neues, kurzes Verzeichnis (``/tmp/tbXXXXXXXX``), das nach dem Test aufgeräumt wird."""
    pfad = Path(tempfile.mkdtemp(prefix="tb", dir="/tmp"))
    _KURZE_VERZEICHNISSE.append(pfad)
    return pfad


@pytest.fixture(autouse=True)
def _kurze_verzeichnisse_aufraeumen():
    yield
    while _KURZE_VERZEICHNISSE:
        shutil.rmtree(_KURZE_VERZEICHNISSE.pop(), ignore_errors=True)


@pytest.fixture
def kurz() -> Path:
    """Kurzes Verzeichnis für Unix-Sockets (``sim.sock``, ``NOTIFY_SOCKET``)."""
    return kurzes_verzeichnis()


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


def zeiger_speichern(serie_id, datei, index, position_s, grund, track=0, art="serie", wall=None):
    return ev.ZeigerSpeichern(art, serie_id, datei, None if art == "folge" else index, track, position_s, grund, wall)


def zeiger(serie_id, datei, index, position_s, zaehler, track=0, art="serie", benutzt_wall=None):
    return ev.Zeiger(art, serie_id, datei, None if art == "folge" else index, track, position_s, zaehler, benutzt_wall)


def ppos(serie_id, datei, position_s, spielt=True, track=0):
    return ev.PlayerPosition(serie_id, datei, track, position_s, spielt)


def mk_konfig(zuordnungen=None, revision=1, lesezeichen_tage=14) -> ev.Konfig:
    return ev.Konfig(
        revision=revision,
        liste_id="liste-1",
        zuordnungen=dict(ZUORDNUNGEN if zuordnungen is None else zuordnungen),
        leise_zeiten=ev.LeiseZeiten("Europe/Berlin", ()),
        gute_nacht=ev.GuteNacht(30, 60),
        lesezeichen_tage=lesezeichen_tage,
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

    def __init__(self, serien=(S1, S2, UEB, S3), konfig=True, wirksam=40, zeiger=(), neustart_uid=None) -> None:
        self.uhr = SimUhr()
        self.z = session.neuer_zustand()
        self.voll: tuple = ()
        self.alle: list = []
        self.sende(ev.GeraeteEinstellungen(60, 40, 25, neustart_uid))
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
        self.senden(ev.PlayerPosition(self.b.serie_id, self.b.datei, self.track, round(self.elapsed, 3), spielt, self.b.gen))

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
                self.senden(ev.TrackWechsel(b.serie_id, b.datei, self.track, b.gen))
                self._position(True)
            else:
                self.elapsed = dauer
                self.spielt = False
                self._position(False)
                self.senden(ev.FolgeZuEnde(b.serie_id, b.datei))
        elif self._seit_position >= 1.0 - 1e-9:
            self._seit_position = 0.0
            self._position(True)


class LeserSim:
    """Die echte Zeilenverarbeitung von ``reader.Leser`` (``_parse``, ``_verarbeite``: ``seq``-Prüfung,
    Vorgangs-ID, Wiedermeldung) ohne Schnittstelle und Uhr: Textzeilen der Firmware hinein, Ereignisse
    heraus. ``HELLO`` und ``HB`` verarbeitet sonst die Verbindungsschleife des ``Leser``; ihre wenigen
    Zeilen (``_verbindung``) sind hier gespiegelt, ``integration/test_reader_pty.py`` prüft sie am Original.

    Die Firmware-Seite (``seq`` zählt ab ``HELLO`` von 0) steckt in den Hilfen ``placed`` bis ``hello``."""

    def __init__(self, ausgabe) -> None:
        from tobibox import reader

        self._reader = reader
        self._ausgabe = ausgabe
        self._n = 0
        self.leser = reader.Leser(ausgabe, "unbenutzt", vorgang_id=self._neue_id)
        self.seq = 0
        self.zeilen: list[str] = []  # alles, was die „Firmware“ gesendet hat

    def _neue_id(self) -> str:
        self._n += 1
        return f"{self._n:08x}"

    def zeile(self, text: str) -> None:
        """Eine Zeile der Firmware an den Dienst (wie ``Leser._verbindung``)."""
        from tobibox import events as ev

        self.zeilen.append(text)
        z = self.leser._parse(text.encode("ascii"))
        assert z is not None, f"Zeile vom Dienst verworfen: {text!r}"
        if z.typ == "HELLO":
            self.leser._seq_erwartet = 0
            self.leser._wiedermeldung = True
            f = z.felder
            self._ausgabe(ev.LeserHallo(int(f["proto"]), f["fw"], f["build"], f["pn5180"]))
        elif z.typ == "HB":
            self._ausgabe(self._reader._herzschlag(z))
        else:
            self.leser._verarbeite(z)

    def _naechste_seq(self) -> int:
        n = self.seq
        self.seq += 1
        return n

    def hello(self) -> None:
        """Leser (neu) gestartet: ``HELLO``, ``seq`` beginnt wieder bei 0."""
        self.seq = 0
        self.zeile("HELLO proto=1 fw=1.0.0 build=fa4e0000 pn5180=4.2")

    def placed(self, uid: str, typ: str = "ntag", tonie: bool = False) -> None:
        self.zeile(f"PLACED uid={uid} type={typ} tonie={int(tonie)} seq={self._naechste_seq()}")

    def locked(self) -> None:
        self.zeile(f"LOCKED seq={self._naechste_seq()}")

    def removed(self) -> None:
        self.zeile(f"REMOVED seq={self._naechste_seq()}")

    def hb(self, present: bool, up: int = 10) -> None:
        self.zeile(f"HB up={up} present={int(present)} polls=50 hits=10 rejected=0 errors=0 cycle_ms=200")


class CujBox:
    """Der Dienst ohne Ein-/Ausgabe: Kern + Speicher + SimPlayer + simulierte Uhr.

    ``neustart()`` baut Kern und Speicher neu auf und lädt die Dateien, als wäre der Dienst
    neu gestartet worden (Zustandsdateien bleiben)."""

    def __init__(self, tmp_path, zuordnungen, serien_aufbau=None, boot_id="boot-1") -> None:
        from tobibox import lauf, library
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
        self._lauf = lauf
        self.boot_id = boot_id  # Kennung des Starts des Geräts; ``None``: nicht lesbar
        self._marker_uid: str | None = None
        self._ResumeStore = ResumeStore
        self.player = SimPlayer(self.medien, self.sende)
        self.start()

    def start(self) -> None:
        self.kern = core.neuer_zustand()
        self.leser = LeserSim(self.sende)  # neue Verbindung zum Leser: ``seq`` beginnt bei 0
        self.resume = self._ResumeStore(self.zustand)
        self.player.b = None
        self.player.spielt = False
        neustart_uid = self._lauf.lese_neustart_uid(self.zustand, self.boot_id)
        self._marker_uid = neustart_uid
        for e in (
            ev.GeraeteEinstellungen(60, 40, 25, neustart_uid),
            self._lade_konfig(),
            self._library.lade_bibliothek(self.medien).ereignis(),
            self.resume.laden(),
            ev.Bereit(),
        ):
            self.sende(e)

    def _lade_konfig(self) -> ev.KonfigGeladen:
        return ev.KonfigGeladen(mk_konfig(self.zuordnungen))

    neustart = start

    def neustart_nach_einschalten(self, boot_id: str | None = "boot-2") -> None:
        """Wie ``neustart``, aber das Gerät war aus (neue Kennung des Starts)."""
        self.boot_id = boot_id
        self.start()

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
        self._marker_uid = self._lauf.nachfuehren(self.zustand, self.boot_id, self.kern.session, self._marker_uid)
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


class SimBox(CujBox):
    """``CujBox`` mit Ausgang, ``sim`` und HA-Ersatz: dieselbe Klasse ``Ausgang`` wie in ``app.py`` (ohne Socket, ohne MPD).

    * ``Melden`` geht in ``unknown.json`` (``Outbox``); ``Bestaetigt`` löscht dort den Eintrag.
    * ``config.json`` ist echt (``KonfigStore``): ``sim_zeile(befehl="card", …)`` schreibt die Zuordnung.
    * ``sim_zeile(befehl="learn", …)`` startet den Lernmodus; der HA-Ersatz schreibt danach die Zuordnung
      und bestätigt, sobald die Box den gelernten Tobie meldet.
    * Nachlauf: Ereignisse des HA-Ersatzes werden nach dem Befehl, der sie auslöste, verarbeitet.
    """

    def __init__(self, tmp_path, zuordnungen, serien_aufbau=None, boot_id="boot-1") -> None:
        from dataclasses import replace

        from tobibox import store

        self.nachlauf: list = []
        zustand = tmp_path / "var"
        zustand.mkdir(parents=True, exist_ok=True)
        konfig = replace(mk_konfig(zuordnungen), liste_id="a3f9c1e07b2d4856")
        store.schreibe_atomar(zustand / "config.json", store.konfig_zu_json(konfig))
        self.konfig_store = store.KonfigStore(zustand)
        super().__init__(tmp_path, zuordnungen, serien_aufbau, boot_id)

    @property
    def sim(self):
        return self.ausgang.sim

    @property
    def outbox(self):
        return self.ausgang.outbox

    @property
    def ha_ersatz(self):
        return self.ausgang.ha_ersatz

    def _lade_konfig(self) -> ev.KonfigGeladen:
        return self.konfig_store.laden()

    def start(self) -> None:
        from tobibox.ausgang import Ausgang

        self.ausgang = Ausgang(self.zustand, self.uhr, self.nachlauf.append, self.konfig_store)
        self.outbox.laden()
        super().start()

    neustart = start

    def sende(self, e, dt: float = 0.0) -> list:
        sim = self.ausgang.war_sim(e)
        if isinstance(e, ev.Bestaetigt):
            # erst die Outbox; den Kern erreicht nur „gelernt“, von der Outbox angenommen (core-interface.md, Abschnitt 3; Entscheidung H, 07.11.)
            if dt:
                self.uhr.vor(dt)
            angenommen = self.ausgang.bestaetigt(e, sim=sim)
            befehle: list = super().sende(e) if (e.art == "gelernt" and angenommen) else []
            self.ausgang.nach_kern(self.kern)
        else:
            befehle = super().sende(e, dt)
            self.ausgang.nach_kern(self.kern)
        for b in befehle:
            if isinstance(b, ev.Melden):
                self.ausgang.melde(b, self.uhr.jetzt())
        while self.nachlauf:
            self.sende(self.nachlauf.pop(0))
        return befehle

    def sim_zeile(self, **zeile) -> list:
        """Eine Zeile an ``sim`` (wie über ``sim.sock``): das Ereignis geht in den Kern."""
        import json

        return self.sende(self.sim.zeile_zu_ereignis(json.dumps(zeile)))

    def unknown(self) -> dict:
        import json

        pfad = self.zustand / "unknown.json"
        return json.loads(pfad.read_text(encoding="utf-8"))["eintraege"] if pfad.exists() else {}

    def konfig_json(self) -> dict:
        import json

        return json.loads((self.zustand / "config.json").read_text(encoding="utf-8"))

    def lernmodus(self) -> bool:
        """``lernmodus`` der letzten ``ZustandMelden``."""
        return self.befehle(ev.ZustandMelden)[-1].lernmodus

    def toene(self, ab: int = 0) -> list[str]:
        return [b.ton for b in self.befehle(ev.TonSpielen, ab)]


# --- Fang für das Ereignisprotokoll (CUJ-Tests mit echter App) ---------------------------------


class Protokollfang:
    """Fängt die JSON-Zeilen des Ereignisprotokolls (so wie sie in die Datei gehen)."""

    def __init__(self) -> None:
        self.strom = io.StringIO()

    def zeilen(self) -> list[dict]:
        return [json.loads(z) for z in self.strom.getvalue().splitlines() if z.startswith("{")]

    def finde(self, ereignis: str, vorgang: str | None = None, baustein: str | None = None) -> list[dict]:
        return [
            z for z in self.zeilen()
            if z["ereignis"] == ereignis
            and (vorgang is None or z.get("vorgang") == vorgang)
            and (baustein is None or z["baustein"] == baustein)
        ]


@pytest.fixture
def protokoll():
    fang = Protokollfang()
    eventlog.einrichten(ziel="stdout", ebene="DEBUG", strom=fang.strom)
    yield fang
    log = eventlog.logger()
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    log.setLevel(logging.NOTSET)


def app_welt(mpd, tmp_path, zuordnungen: dict, serien: dict | None = None) -> dict:
    """Medien im MPD-Ordner, Zustandsordner, ``config.json`` und ``tobibox.toml`` für eine echte ``App``.

    ``serien``: Name -> (serie_id, Folgen, Dauer); Vorgabe: Serie ``rabe`` (zwei Folgen zu 30 s) und eine
    Überraschungs-Serie (ein Ton zu 2 s)."""
    from fixtures import audio

    from tobibox import store

    for name, (serie_id, folgen, dauer_s) in (serien or {"rabe": ("3f9a1c07b2d4", ["folge-01.wav", "folge-02.wav"], 30.0)}).items():
        audio.erzeuge_serie(mpd.medien, name, folgen, serie_id=serie_id, name=name, dauer_s=dauer_s)
    audio.erzeuge_serie(mpd.medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)
    mpd.aktualisiere()
    zustand = kurzes_verzeichnis() / "var"  # ``sim.sock`` liegt darin: kurzer Pfad (macOS)
    zustand.mkdir()
    k = ev.Konfig(1, "a3f9c1e07b2d4856", dict(zuordnungen), ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60))
    store.schreibe_atomar(zustand / "config.json", {**store.konfig_zu_json(k), "ton_pegel": 40, "hinweis_pegel": 15})
    link = tmp_path / "leser" / "ttyACM0"
    toml = tmp_path / "tobibox.toml"
    toml.write_text(
        f'[pfade]\nzustand = "{zustand}"\nmedien = "{mpd.medien}"\n[leser]\ngeraet = "{link}"\n'
        f'[mpd]\nhost = "127.0.0.1"\nport = {mpd.port}\n[lautstaerke]\nmax = 50\nstart = 20\nkopfhoerer = 30\n'
        '[toene]\nkommando = ["true", "{datei}"]\n'
    )
    return {"zustand": zustand, "link": link, "toml": toml, "mpd": mpd}
