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

ZUORDNUNGEN = {
    UID_S1: ev.Zuordnung("serie", "s1"),
    UID_S2: ev.Zuordnung("serie", "s2"),
    UID_FEHLT: ev.Zuordnung("serie", "unbekannte-serie"),
    UID_NACHT: ev.Zuordnung("aktion", None, "gute_nacht"),
    UID_STATUS: ev.Zuordnung("aktion", None, "status"),
}


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

    def __init__(self, serien=(S1, S2, UEB), konfig=True, wirksam=40, zeiger=()) -> None:
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

    def position(self, serie="s1", datei="a.mp3", sek=10.0) -> None:
        self.sende(ev.PlayerPosition(serie, datei, sek, True))


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

    def __init__(self, serien=(S1, S2, UEB), einstellungen=(60, 40, 25), start=True) -> None:
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
