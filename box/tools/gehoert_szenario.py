#!/usr/bin/env python3
"""Szenario-Werkzeug für „Gehört“ (Stufe B, Paket B5; ``docs/designs/gehoert.md`` Abschnitt 9, Festlegung G-B14/G-L6/G-H8).

Erzeugt Hördaten über Wochen in kurzer Zeit und legt sie in den Puffer ``gehoert.json`` der Test-Box (``boxsim``,
``docs/betrieb/test-box-am-mac.md``). Beim nächsten Start verbindet sich die Box mit Home Assistant, macht den Handshake,
sendet die Zeilen (je Nachricht höchstens 20) und löscht sie nach der Quittung: Die echte Sende- und Quittungslogik
(``ha.py``, ``gehoert_puffer.py``) läuft also genau so wie nach einer langen Zeit ohne Verbindung.

Warum der Puffer und nicht MQTT direkt? ``gehoert.json`` ist das, was eine Box nach Wochen ohne Verbindung wirklich hält.
Alles, was danach geschieht, ist Box-Code und nicht die Nachbildung davon: Handshake mit ``gehoert_wartet``, Senden in
Päckchen, Wiederholen alle 10 Minuten, Quittung über die UUIDs, Löschen, ``status.gehoert_verworfen``, die Zeilen mit
``zeit_ok = false`` und die Korrektur der Uhr. Direkte MQTT-Nachrichten würden das alles umgehen (und gerade die
Quittung nicht üben). Der Preis: Es passen höchstens 500 Zeilen hinein (das ist der Überlauf, siehe Szenario ``ueberlauf``).

Die Zeilen entstehen **nicht von Hand**, sondern durch den echten Beobachter ``tobibox.gehoert`` mit simulierter Uhr
(``SimUhr``): Das Werkzeug spielt ``Abspielen``, ``PlayerPosition``, ``Takt``, ``FolgeZuEnde``, ``Pausieren``,
``Herunterfahren`` und ``DienstEndet`` ein, wie der Kern sie ausgibt, und lässt den Puffer (``GehoertPuffer``) laden, wie
die Box es beim Start tut (offene Sitzung wird ``abbruch``). Die Platte wird dabei nur im Arbeitsspeicher nachgeführt
(``_SchnellPuffer``) und nur bei Neustarts und am Ende geschrieben.

Aufruf (im Ordner ``box/``, Test-Box **gestoppt**)::

    ../.venv/bin/python tools/gehoert_szenario.py --konfig config/boxsim.toml --tage 40 --seed 1 --trocken
    ../.venv/bin/python tools/gehoert_szenario.py --konfig config/boxsim.toml --tage 40 --seed 1 --szenario alle

Szenarien (``--szenario``, Komma-Liste oder mehrfach; ``alle`` = alle; Vorgabe ohne ``ueberlauf`` und ``uhr_nie_gut``):

* ``alltag``      tägliches Hören (morgens, nachmittags, abends), Folgen weiter oder von vorn, mal bis zum Ende, mal
                  abgebrochen, Folgenwechsel, die Box wird oft ausgeschaltet (``herunterfahren``, neue ``boot_id``)
* ``wiederholen`` dieselbe Folge mehrmals hintereinander bis zum Ende (jedes Mal ein neues „Mal“) an drei Abenden
* ``hoerbuch``    ein langes Hörbuch in Portionen über mehrere Abende (Fertig zählt über die Portionen, 80 %)
* ``neustart``    Neustart der Box-Software mitten im Hören (``dienst_ende``) und ein Absturz ohne Abmelden (``abbruch``)
* ``strom_weg``   Strom weg mitten im Hören: ``abbruch`` im nächsten Gerätestart, bis zu 2 Minuten fehlen
* ``ueberlauf``   mehr als 500 kurze Sitzungen an einem Tag (Tobie-Wechsel-Spiel): die ältesten Zeilen fallen weg,
                  ``verworfen`` zählt
* ``offline``     die Box ist ein paar Tage unterwegs: jedes Mal frisch eingeschaltet, nie verbunden (viele ``boot_id``)
* ``uhr_nie_gut`` Gerätestarts mit falscher Uhr (``zeit_ok = false``, Datum unbekannt), einer davon mit später guter Uhr

Gleicher ``--seed`` und gleiches ``--jetzt``: gleiche Datei (bis auf nichts: auch die UUIDs kommen aus dem Seed).
"""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
import tempfile
import tomllib
import uuid
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from random import Random
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tobibox import events as ev  # noqa: E402
from tobibox import eventlog  # noqa: E402
from tobibox import gehoert as g  # noqa: E402
from tobibox.clock import SimUhr  # noqa: E402
from tobibox.gehoert_puffer import NAME, GehoertPuffer  # noqa: E402
from tobibox.library import lade_bibliothek  # noqa: E402
from tobibox.store import schreibe_atomar  # noqa: E402

SZENARIEN = ("alltag", "wiederholen", "hoerbuch", "neustart", "strom_weg", "ueberlauf", "offline", "uhr_nie_gut")
VORGABE_SZENARIEN = ("alltag", "wiederholen", "hoerbuch", "neustart", "strom_weg", "offline")
SCHRITT_S = 5  # so oft meldet der Player die Position (Sekunden); ``dp`` bleibt weit unter der Kappung
VIRTUELLE_DAUER_S = 1500  # Folgen, die in Wirklichkeit nur Sekunden dauern (Testmedien), gelten als so lang
HOERBUCH_DAUER_S = 3 * 3600
UHR_FALSCH_BASIS = datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()  # Pi ohne Uhr: der letzte gesicherte Stand
ENDE_PUFFER_S = 3 * 3600  # die letzte Sitzung beginnt spätestens so lange vor „jetzt“


class SzenarioFehler(Exception):
    pass


# --------------------------------------------------------------------------
# Katalog (Serien und Folgen)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Folge:
    serie: str
    folge: str
    dauer_s: int  # Länge in der Simulation (und in der Zeile ``folge_dauer_s``)
    echt_s: int | None = None  # Länge der Datei, wenn bekannt

    @property
    def schluessel(self) -> tuple[str, str]:
        return (self.serie, self.folge)


@dataclass(frozen=True)
class Katalog:
    serien: dict[str, tuple[Folge, ...]]  # ohne Hörbuch
    hoerbuch: Folge
    quelle: str

    @property
    def alle(self) -> list[Folge]:
        return [f for fs in self.serien.values() for f in fs]


def standard_katalog() -> Katalog:
    """Erfundene Serien (Platzhalter), wenn kein Medienordner da ist. Home Assistant kennt sie nicht (siehe Anleitung)."""
    def serie(sid: str, n: int, dauer: int) -> tuple[Folge, ...]:
        return tuple(Folge(sid, f"folge-{i:02d}.mp3", dauer + 60 * (i % 4)) for i in range(1, n + 1))

    return Katalog(
        {"3f9a1c07b2d4": serie("3f9a1c07b2d4", 8, 1500), "a81d5e3c9b02": serie("a81d5e3c9b02", 5, 1200), "c05e7b1d4a96": serie("c05e7b1d4a96", 6, 1800)},
        Folge("e6b2f9a04c71", "teil-1", HOERBUCH_DAUER_S),
        "standard (erfundene Serien)",
    )


def lade_katalog(medien: Path | None, *, virtuell_s: int = VIRTUELLE_DAUER_S, hoerbuch_s: int = HOERBUCH_DAUER_S) -> Katalog:
    """Serien und Folgen aus dem Medienordner der Test-Box (so kennt Home Assistant sie), sonst ``standard_katalog``.

    Dauern unter 5 Minuten (die Testmedien dauern Sekunden) werden durch ``virtuell_s`` ersetzt, damit Ranglisten und
    Diagramme etwas zeigen; das Hörbuch (Serie mit ``hoerbuch`` im Ordnernamen, sonst die längste Folge) bekommt
    mindestens 30 Minuten (sonst ``hoerbuch_s``)."""
    if medien is None or not medien.is_dir():
        return standard_katalog()
    bib = lade_bibliothek(medien, leise=True)
    normal = [s for s in bib.serien if s.typ == "normal" and s.folgen]
    if not normal:
        return standard_katalog()

    def echt(s: Any, f: str) -> int | None:
        d = s.dauern.get(f)
        if not d or len(d) != len(s.tracks.get(f, (f,))) or any(x is None for x in d):
            return None
        gesamt = round(sum(d))
        return gesamt if gesamt > 0 else None

    def folgen_von(s: Any, minimum: int, ersatz: int) -> tuple[Folge, ...]:
        res = []
        for i, f in enumerate(s.folgen):
            e = echt(s, f)
            res.append(Folge(s.id, f, e if e is not None and e >= minimum else ersatz + 60 * (i % 4), e))
        return tuple(res)

    hb = next((s for s in normal if "hoerbuch" in s.ordner.lower()), None)
    if hb is None and len(normal) >= 2:
        hb = max(normal, key=lambda s: max((echt(s, f) or 0) for f in s.folgen))
    rest = [s for s in normal if s is not hb]
    if not rest:
        return standard_katalog()
    if hb is not None:
        hb_folgen = folgen_von(hb, 1800, hoerbuch_s)
        hoerbuch = max(hb_folgen, key=lambda f: f.dauer_s)
    else:
        hoerbuch = Folge("e6b2f9a04c71", "teil-1", hoerbuch_s)
    return Katalog({s.id: folgen_von(s, 300, virtuell_s) for s in rest}, hoerbuch, f"Medienordner {medien.name}")


def lade_serien_datei(pfad: Path, *, anzahl: int, seed: int) -> Katalog:
    """Serien und Folgen aus einer JSON-Datei (aus der echten HA erzeugt): genau diese Namen und **echten** Dauern.

    Format: ``[{"serie_id": "...", "name": "...", "folgen": [{"name": "<Folge wie in mqtt-v1>", "dauer_s": 2700}, ...]}, ...]``.
    Aus der Liste wählt ``seed`` deterministisch höchstens ``anzahl`` Serien; das Hörbuch ist die längste Folge der Auswahl
    (sie fällt aus dem Alltag heraus)."""
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SzenarioFehler(f"--serien {pfad}: {e}") from e
    if not isinstance(roh, list):
        raise SzenarioFehler("--serien: die Datei muss eine Liste von Serien sein")
    serien: dict[str, tuple[Folge, ...]] = {}
    for i, e in enumerate(roh):
        sid = e.get("serie_id") if isinstance(e, dict) else None
        fl = e.get("folgen") if isinstance(e, dict) else None
        if not (isinstance(sid, str) and 1 <= len(sid) <= g.MAX_SERIE and isinstance(fl, list)):
            raise SzenarioFehler(f"--serien: Eintrag {i}: serie_id (1 bis {g.MAX_SERIE} Zeichen) und folgen (Liste) fehlen")
        folgen = []
        for f in fl:
            n, d = (f.get("name"), f.get("dauer_s")) if isinstance(f, dict) else (None, None)
            if not (isinstance(n, str) and 1 <= len(n.encode("utf-8")) <= g.MAX_FOLGE_BYTES and isinstance(d, int) and not isinstance(d, bool) and d > 0):
                raise SzenarioFehler(f"--serien: Serie {sid}: jede Folge braucht name (höchstens {g.MAX_FOLGE_BYTES} Bytes) und dauer_s (ganze Zahl > 0)")
            folgen.append(Folge(sid, n, d, d))
        if folgen and sid not in serien:
            serien[sid] = tuple(folgen)
    if not serien:
        raise SzenarioFehler("--serien: keine Serie mit Folgen in der Datei")
    ids = sorted(serien)
    gewaehlt = sorted(Random(f"serien-{seed}").sample(ids, min(max(1, anzahl), len(ids))))
    hoerbuch = max((f for sid in gewaehlt for f in serien[sid]), key=lambda f: (f.dauer_s, f.serie, f.folge))
    rest = {sid: tuple(f for f in serien[sid] if f != hoerbuch) for sid in gewaehlt}
    rest = {sid: fs for sid, fs in rest.items() if fs}
    if not rest:
        raise SzenarioFehler("--serien: nach Abzug des Hörbuchs bleibt keine Folge; bitte mehr Serien wählen (--anzahl-serien)")
    return Katalog(rest, hoerbuch, f"Serien-Datei {pfad.name} ({len(gewaehlt)} von {len(ids)} Serien)")


# --------------------------------------------------------------------------
# Puffer mit Platte im Arbeitsspeicher
# --------------------------------------------------------------------------


class _SchnellPuffer(GehoertPuffer):
    """``GehoertPuffer``, der nicht bei jedem Schreibvorgang auf die Platte geht: Er merkt sich den Stand, der **auf der Platte
    stünde** (``platte``). Geschrieben wird nur bei Neustarts und am Ende (``schreibe_platte``). Sonst unverändert."""

    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        self.platte: g.Zustand | None = None

    def _schreibe(self, sync: bool) -> None:  # noqa: ARG002
        self.platte = self.z
        self.schreibungen += 1

    def schreibe_platte(self) -> None:
        """Den Stand, der zuletzt „geschrieben“ wurde, auf die Platte legen (so findet ihn der nächste Start)."""
        if self.platte is not None:
            schreibe_atomar(self.pfad, g.zu_json(self.platte))


# --------------------------------------------------------------------------
# Die simulierte Box
# --------------------------------------------------------------------------


class Welt:
    """Eine Box mit simulierter Uhr und dem echten Beobachter. Alle Zeiten kommen von hier, nie von der Systemuhr."""

    def __init__(self, scratch: Path, rng: Random, katalog: Katalog, wahr: float) -> None:
        self.scratch = scratch
        self.rng = rng
        self.katalog = katalog
        self.dauern = {f.schluessel: f.dauer_s for f in katalog.alle + [katalog.hoerbuch]}
        self.uhr = SimUhr(mono=50.0, wall=wahr)
        self.wahr = wahr  # die richtige Zeit (die Wanduhr der Box weicht bei falscher Uhr davon ab)
        self.an = False
        self.boot = ""
        self.boots = 0
        self.gen = 0
        self.serie = self.folge = ""
        self.track, self.pos = 0, 0.0
        self.puffer: _SchnellPuffer | None = None
        self.ereignisse = Counter[str]()

    # -- Hilfen ---------------------------------------------------------------------

    def neue_uuid(self) -> str:
        return str(uuid.UUID(int=self.rng.getrandbits(128), version=4))

    def _neuer_puffer(self) -> None:
        self.puffer = _SchnellPuffer(
            self.scratch, boot_id=lambda: self.boot, neue_id=self.neue_uuid,
            dauer=lambda serie, folge: self.dauern.get((serie, folge)),
        )
        self.puffer.laden(self.uhr.jetzt())

    def _p(self) -> _SchnellPuffer:
        assert self.puffer is not None and self.an, "die Box ist aus"
        return self.puffer

    def ein(self, e: ev.Ereignis, *befehle: ev.Befehl) -> None:
        self._p().beobachte(e, befehle, self.uhr.jetzt())

    def vor(self, sekunden: float) -> None:
        """Zeit vergeht, die Box ist an (Uhr und monotone Uhr laufen)."""
        self.wahr += sekunden
        self.uhr.vor(sekunden)

    # -- Gerät ----------------------------------------------------------------------

    def einschalten(self, wahr: float | None = None, *, zeit_ok: bool = True) -> None:
        """Neuer Gerätestart: neue ``boot_id``, die monotone Uhr beginnt von vorn; ohne gute Uhr zeigt die Wanduhr einen alten Stand."""
        assert not self.an
        if wahr is not None:
            self.wahr = wahr
        self.boots += 1
        self.boot = self.neue_uuid()
        self.uhr.mono = float(self.rng.randint(15, 90))
        self.uhr.zeit_ok = zeit_ok
        self.uhr.zeit_quelle = "system" if zeit_ok else "unbekannt"
        self.uhr.wall = self.wahr if zeit_ok else UHR_FALSCH_BASIS + self.uhr.mono
        self.an = True
        self.gen = 0
        self._neuer_puffer()  # lädt ``gehoert.json`` wie die Box beim Start (offene Sitzung -> ``abbruch``)

    def uhr_wird_gut(self) -> None:
        """Die Uhr wird im selben Gerätestart gut (NTP, RTC): der nächste ``Takt`` korrigiert die Zeilen dieses Starts."""
        self.uhr.zeit_ok = True
        self.uhr.zeit_quelle = "ntp"
        self.uhr.wall = self.wahr
        self.ein(ev.Takt())

    def herunterfahren(self) -> None:
        """``Herunterfahren`` (Hauptknopf): offene Sitzung endet mit ``herunterfahren``, die Platte ist sofort aktuell."""
        p = self._p()
        self.ein(ev.Takt(), ev.Pausieren("herunterfahren"), ev.Herunterfahren("hauptknopf"))
        p.schreibe_platte()
        self.an = False
        self.ereignisse["herunterfahren"] += 1

    def dienst_neustart(self) -> None:
        """Die Box-Software wird neu gestartet (Update, ``systemctl restart``): ``dienst_ende``, gleiche ``boot_id``."""
        p = self._p()
        p.dienst_ende(self.uhr.jetzt())
        p.schreibe_platte()
        self.vor(self.rng.randint(8, 25))
        self._neuer_puffer()
        self.ereignisse["dienst_neustart"] += 1

    def absturz(self) -> None:
        """Die Box-Software stürzt ab (kein ``dienst_ende``): gültig ist der Stand von der Platte (bis 2 Minuten fehlen)."""
        p = self._p()
        p.schreibe_platte()
        self.vor(self.rng.randint(5, 20))
        self._neuer_puffer()
        self.ereignisse["absturz"] += 1

    def strom_weg(self, aus_s: float | None = None) -> None:
        """Strom weg: wie ``absturz``, aber das Gerät ist aus (Stunden) und startet mit neuer ``boot_id``."""
        p = self._p()
        p.schreibe_platte()
        self.an = False
        self.wahr += aus_s if aus_s is not None else self.rng.uniform(1800, 4 * 3600)
        self.ereignisse["strom_weg"] += 1

    def bis(self, wahr: float) -> None:
        """Zeit bis ``wahr`` vergehen lassen (Box an: Uhr läuft mit und ein ``Takt``; Box aus: nur die Zeit)."""
        delta = wahr - self.wahr
        if delta <= 0:
            return
        if self.an:
            self.vor(delta)
            self.ein(ev.Takt())
        else:
            self.wahr = wahr

    # -- Hören ----------------------------------------------------------------------

    def abspielen(self, f: Folge, von_s: float = 0.0) -> None:
        """Wie der Kern: ein neues ``Abspielen`` mit neuer Generation (Auflegen, Fortsetzen, Springen)."""
        self.gen += 1
        self.serie, self.folge, self.track, self.pos = f.serie, f.folge, 0, float(von_s)
        self.ein(ev.Takt(), ev.Abspielen(f.serie, "ordner", f.folge, (f.folge,), 0, float(von_s), None, self.gen))

    def spiele(self, sekunden: float) -> None:
        """Wiedergabe: alle ``SCHRITT_S`` Sekunden eine Positionsmeldung und ein ``Takt``."""
        rest = float(sekunden)
        while rest > 0:
            dt = min(float(SCHRITT_S), rest)
            self.vor(dt)
            self.pos += dt
            rest -= dt
            self.ein(ev.PlayerPosition(self.serie, self.folge, self.track, round(self.pos, 3), True, self.gen))
            self.ein(ev.Takt())

    def pause(self, grund: str) -> None:
        self.ein(ev.PlayerPosition(self.serie, self.folge, self.track, round(self.pos, 3), False, self.gen))
        self.ein(ev.Takt(), ev.Pausieren(grund))  # type: ignore[arg-type]

    def folge_zu_ende(self) -> None:
        self.ein(ev.FolgeZuEnde(self.serie, self.folge, self.gen), ev.Pausieren("folgenende"))
        self.ereignisse["ende_der_folge"] += 1

    def hoere(self, f: Folge, von_s: float, bis_s: float | None = None, *, grund: str = "knopf") -> bool:
        """Eine Folge ab ``von_s`` bis ``bis_s`` hören (``None``: bis zum Ende). ``True``: bis zum Ende der Folge gehört."""
        ende = bis_s is None or bis_s >= f.dauer_s - 1
        ziel = float(f.dauer_s) if ende else float(bis_s)  # type: ignore[arg-type]
        self.abspielen(f, von_s)
        self.spiele(max(0.0, ziel - von_s))
        if ende:
            self.folge_zu_ende()
        else:
            self.pause(grund)
        return ende


# --------------------------------------------------------------------------
# Planung
# --------------------------------------------------------------------------


@dataclass
class Segment:
    stunde: float  # Ortszeit
    name: str
    lauf: Callable[[Welt, Kontext], None]
    frisch: bool = False  # die Box war aus und wird für dieses Hören frisch eingeschaltet (neue ``boot_id``)
    danach_aus: bool | None = None  # ``None``: nach der Regel des Alltags
    zeit_ok: bool = True
    reihe: int = 0


@dataclass
class Kontext:
    rng: Random
    katalog: Katalog
    tage: int
    szenarien: frozenset[str]
    gewicht: dict[str, float]
    lieblings_folge: Folge
    naechste: dict[str, int] = field(default_factory=dict)
    resume: dict[tuple[str, str], float] = field(default_factory=dict)
    hoerbuch_pos: float = 0.0
    hoerbuch_teile: list[float] = field(default_factory=list)  # Längen der noch ausstehenden Portionen (Sekunden)

    def waehle_serie(self) -> str:
        ids = list(self.katalog.serien)
        return self.rng.choices(ids, weights=[self.gewicht[i] for i in ids])[0]

    def waehle_folge(self) -> Folge:
        sid = self.waehle_serie()
        fs = self.katalog.serien[sid]
        r = self.rng.random()
        if r < 0.55:  # die nächste Folge der Reihe
            i = self.naechste.get(sid, 0) % len(fs)
        else:
            i = self.rng.randrange(len(fs))
        self.naechste[sid] = i + 1
        return fs[i]


PAUSEGRUENDE = (("knopf", 5), ("abgehoben", 4), ("gute_nacht", 2), ("stumm", 1))


def _grund(ctx: Kontext, abend: bool) -> str:
    if abend and ctx.rng.random() < 0.6:
        return "gute_nacht"
    return ctx.rng.choices([x for x, _ in PAUSEGRUENDE], weights=[w for _, w in PAUSEGRUENDE])[0]


def einzelne_folge(w: Welt, ctx: Kontext, *, abend: bool = False) -> None:
    """Eine Hör-Runde: eine Folge (oft von der letzten Stelle weiter), bis zum Ende oder abgebrochen, manchmal mit Anschluss."""
    r = ctx.rng
    f = ctx.waehle_folge()
    von = ctx.resume.pop(f.schluessel, 0.0) if r.random() < 0.7 else 0.0
    if f.dauer_s - von < 120:
        von = 0.0
    rest = f.dauer_s - von
    if r.random() < 0.45 or rest < 150:
        fertig = w.hoere(f, von, None)
    else:
        bis = von + rest * r.uniform(0.25, 0.9)
        fertig = w.hoere(f, von, bis, grund=_grund(ctx, abend))
        ctx.resume[f.schluessel] = bis
    if fertig and r.random() < 0.2:  # gleich die nächste Folge
        w.vor(r.randint(3, 20))
        f2 = ctx.waehle_folge()
        w.hoere(f2, 0.0, None if r.random() < 0.5 else f2.dauer_s * r.uniform(0.3, 0.8), grund=_grund(ctx, abend))
    elif not fertig and r.random() < 0.1:  # ein anderer Tobie wird aufgelegt: ``wechsel``
        w.vor(r.randint(5, 30))
        f2 = ctx.waehle_folge()
        w.hoere(f2, 0.0, min(f2.dauer_s * 0.9, r.uniform(60, 400)), grund=_grund(ctx, abend))


def _alltag(ctx: Kontext, idx: int, tag: date) -> list[Segment]:
    r = ctx.rng
    ende_woche = tag.weekday() >= 5
    segs: list[Segment] = []
    if r.random() < (0.55 if ende_woche else 0.35):
        segs.append(Segment(r.uniform(7.0, 8.4), "morgen", lambda w, c: einzelne_folge(w, c)))
    if ende_woche and r.random() < 0.6:
        segs.append(Segment(r.uniform(9.0, 11.0), "vormittag", lambda w, c: einzelne_folge(w, c)))
    if r.random() < (0.75 if ende_woche else 0.5):
        segs.append(Segment(r.uniform(14.0, 17.0), "nachmittag", lambda w, c: einzelne_folge(w, c)))
    if r.random() < 0.9:
        segs.append(Segment(r.uniform(18.5, 20.0), "abend", lambda w, c: einzelne_folge(w, c, abend=True), danach_aus=r.random() < 0.85))
    return segs


def _wiederholen(ctx: Kontext, idx: int, tag: date) -> list[Segment]:
    rest = ctx.tage - 1 - idx
    if rest not in (2, 5, 9) or ctx.tage < 3:
        return []
    n = ctx.rng.randint(3, 5)

    def lauf(w: Welt, c: Kontext) -> None:
        f = c.lieblings_folge
        for i in range(n):
            w.hoere(f, 0.0, None)  # bis zum Ende, danach sofort noch einmal
            w.vor(c.rng.randint(2, 12))

    return [Segment(19.5 + 0.1 * ctx.rng.random(), "wiederholen", lauf)]


def _hoerbuch_tage(tage: int) -> list[int]:
    """Abende (Index), an denen das Hörbuch weitergehört wird: über etwa 12 Tage, mindestens 2."""
    n = min(7, max(2, tage // 4))
    spanne = min(tage, 14)
    erster = tage - spanne
    return sorted({erster + round(i * (spanne - 2) / max(1, n - 1)) for i in range(n)})


def _hoerbuch(ctx: Kontext, idx: int, tag: date) -> list[Segment]:
    tage = _hoerbuch_tage(ctx.tage)
    if idx not in tage:
        return []
    letzter = idx == tage[-1]

    def lauf(w: Welt, c: Kontext) -> None:
        f = c.katalog.hoerbuch
        if not c.hoerbuch_teile:  # beim ersten Mal: je Abend eine Portion (ungleich lang), zusammen die ganze Folge
            gew = [c.rng.uniform(0.7, 1.3) for _ in tage]
            c.hoerbuch_teile = [f.dauer_s * x / sum(gew) for x in gew]
        t = c.hoerbuch_teile.pop(0)
        von = c.hoerbuch_pos
        if letzter or not c.hoerbuch_teile:
            w.hoere(f, von, None)  # der letzte Abend: bis zum Ende der Folge
            c.hoerbuch_pos = 0.0
        else:
            w.hoere(f, von, von + t, grund="gute_nacht" if c.rng.random() < 0.5 else "knopf")
            c.hoerbuch_pos = von + t

    return [Segment(20.2, "hoerbuch", lauf, danach_aus=True)]


def _neustart(ctx: Kontext, idx: int, tag: date) -> list[Segment]:
    rest = ctx.tage - 1 - idx
    segs: list[Segment] = []
    if rest == 8 and ctx.tage >= 9:
        def neustart(w: Welt, c: Kontext) -> None:
            f = c.waehle_folge()
            w.abspielen(f, 0.0)
            w.spiele(c.rng.randint(300, 600))  # Update der Box-Software: Dienst endet mitten im Hören
            w.dienst_neustart()
            w.hoere(f, w.pos, min(f.dauer_s, w.pos + c.rng.uniform(300, 600)), grund="knopf")  # der Tobie wird wieder aufgelegt
        segs.append(Segment(16.0, "neustart", neustart, danach_aus=False))
    if rest == 6 and ctx.tage >= 7:
        def absturz(w: Welt, c: Kontext) -> None:
            f = c.waehle_folge()
            w.abspielen(f, 0.0)
            w.spiele(c.rng.randint(420, 900))
            w.absturz()
            w.hoere(f, w.pos, min(f.dauer_s, w.pos + c.rng.uniform(200, 500)), grund="abgehoben")
        segs.append(Segment(15.0, "absturz", absturz, danach_aus=False))
    return segs


def _strom_weg(ctx: Kontext, idx: int, tag: date) -> list[Segment]:
    rest = ctx.tage - 1 - idx
    if rest != 4 or ctx.tage < 5:
        return []

    def lauf(w: Welt, c: Kontext) -> None:
        f = c.waehle_folge()
        w.abspielen(f, 0.0)
        w.spiele(c.rng.randint(480, 1200))  # mehr als 2 Minuten: der Stand auf der Platte ist alt
        w.strom_weg()
        w.einschalten()  # später wieder an, neue ``boot_id``: die offene Sitzung wird ``abbruch``
        w.hoere(c.waehle_folge(), 0.0, c.rng.uniform(300, 700), grund="knopf")

    return [Segment(17.0, "strom_weg", lauf, danach_aus=True)]


def _ueberlauf(ctx: Kontext, idx: int, tag: date) -> list[Segment]:
    if ctx.tage < 3 or idx != max(1, ctx.tage // 3):  # früh genug, dass danach noch Tage übrig bleiben (nur die ältesten Zeilen fallen weg)
        return []
    folgen = sorted(ctx.katalog.alle, key=lambda f: f.schluessel)[:6]
    if len(folgen) < 2:
        folgen = folgen * 2

    def lauf(w: Welt, c: Kontext) -> None:
        for i in range(g.MAX_ZEILEN + 30):  # Tobie-Wechsel-Spiel: jede Karte nur kurz, jede Sitzung endet mit ``wechsel``
            f = folgen[i % len(folgen)]
            w.abspielen(f, 0.0)
            w.spiele(c.rng.randint(12, 40))
            w.vor(c.rng.randint(1, 4))

    return [Segment(9.0, "ueberlauf", lauf, danach_aus=True)]


def _offline(ctx: Kontext, idx: int, tag: date) -> list[Segment]:
    rest = ctx.tage - 1 - idx
    if rest > min(4, ctx.tage - 1):
        return []
    segs = []
    for h in (ctx.rng.uniform(8.0, 10.0), ctx.rng.uniform(15.0, 17.5)):
        segs.append(Segment(h, "offline", lambda w, c: einzelne_folge(w, c), frisch=True, danach_aus=True))
    return segs


def _uhr_nie_gut(ctx: Kontext, idx: int, tag: date) -> list[Segment]:
    rest = ctx.tage - 1 - idx
    if rest not in (12, 11, 10, 9) or ctx.tage < 10:
        return []
    if rest == 9:  # ein Start mit schlechter Uhr, die nach einigen Minuten gut wird: die Zeilen werden korrigiert
        def spaet(w: Welt, c: Kontext) -> None:
            f = c.waehle_folge()
            w.abspielen(f, 0.0)
            w.spiele(c.rng.randint(240, 420))
            w.uhr_wird_gut()
            w.spiele(c.rng.randint(240, 600))
            w.pause("knopf")
        return [Segment(18.0, "uhr_spaet_gut", spaet, frisch=True, danach_aus=True, zeit_ok=False)]
    return [
        Segment(h, "uhr_nie_gut", lambda w, c: einzelne_folge(w, c), frisch=True, danach_aus=True, zeit_ok=False)
        for h in (ctx.rng.uniform(9.0, 11.0), ctx.rng.uniform(18.0, 19.5))
    ]


PLANER: dict[str, Callable[[Kontext, int, date], list[Segment]]] = {
    "alltag": _alltag, "wiederholen": _wiederholen, "hoerbuch": _hoerbuch, "neustart": _neustart,
    "strom_weg": _strom_weg, "ueberlauf": _ueberlauf, "offline": _offline, "uhr_nie_gut": _uhr_nie_gut,
}


# --------------------------------------------------------------------------
# Lauf
# --------------------------------------------------------------------------


@dataclass
class Ergebnis:
    inhalt: dict[str, Any]
    zusammenfassung: str
    ereignisse: Counter
    segmente: Counter


def _stelle_ein(w: Welt, seg: Segment) -> None:
    if w.an and seg.frisch:
        w.herunterfahren()  # unterwegs: die Box war aus und wird frisch eingeschaltet
    if not w.an:
        w.einschalten(zeit_ok=seg.zeit_ok)


def erzeuge(
    *, tage: int, seed: int, szenarien: Sequence[str] = VORGABE_SZENARIEN, jetzt: float, katalog: Katalog | None = None,
    zone: str = "Europe/Berlin", scratch: Path | None = None,
) -> Ergebnis:
    """Die Datei ``gehoert.json`` (als Inhalt) für ``tage`` Tage bis ``jetzt``. Rein im Arbeitsspeicher und in ``scratch``."""
    if tage < 1:
        raise SzenarioFehler("--tage muss mindestens 1 sein")
    unbekannt = set(szenarien) - set(SZENARIEN)
    if unbekannt:
        raise SzenarioFehler(f"unbekannte Szenarien: {sorted(unbekannt)} (bekannt: {', '.join(SZENARIEN)}, alle)")
    try:
        tz = ZoneInfo(zone)
    except ZoneInfoNotFoundError as e:
        raise SzenarioFehler(f"unbekannte Zeitzone: {zone}") from e
    katalog = katalog or standard_katalog()
    with tempfile.TemporaryDirectory(prefix="gehoert-szenario-") if scratch is None else _Nichts(scratch) as verz:
        return _lauf(Path(verz), tage, seed, tuple(szenarien), jetzt, katalog, tz)


class _Nichts:
    def __init__(self, p: Path) -> None:
        self.p = p

    def __enter__(self) -> str:
        self.p.mkdir(parents=True, exist_ok=True)
        return str(self.p)

    def __exit__(self, *a: object) -> None:
        return None


def _lauf(verz: Path, tage: int, seed: int, szenarien: tuple[str, ...], jetzt: float, katalog: Katalog, tz: ZoneInfo) -> Ergebnis:
    stumm = logging.NullHandler()  # die Protokollzeilen des Beobachters (Überlauf, Abbruch) gehören nicht auf den Bildschirm
    eventlog.logger().addHandler(stumm)
    try:
        return _lauf_still(verz, tage, seed, szenarien, jetzt, katalog, tz)
    finally:
        eventlog.logger().removeHandler(stumm)


def _lauf_still(verz: Path, tage: int, seed: int, szenarien: tuple[str, ...], jetzt: float, katalog: Katalog, tz: ZoneInfo) -> Ergebnis:
    rng = Random(seed)
    ids = list(katalog.serien)
    gewicht = {i: rng.choice((0.5, 1.0, 1.0, 2.0, 4.0)) for i in ids}
    lieblinge = [f for f in katalog.alle if f.dauer_s <= 2400] or katalog.alle
    ctx = Kontext(rng, katalog, tage, frozenset(szenarien), gewicht, rng.choice(lieblinge))
    ende_tag = datetime.fromtimestamp(jetzt, tz).date()
    start_tag = ende_tag - timedelta(days=tage - 1)
    w = Welt(verz, rng, katalog, datetime(start_tag.year, start_tag.month, start_tag.day, 0, 0, tzinfo=tz).timestamp())
    zaehler: Counter[str] = Counter()
    grenze = jetzt - ENDE_PUFFER_S
    for idx in range(tage):
        tag = start_tag + timedelta(days=idx)
        segs: list[Segment] = []
        for name in SZENARIEN:  # feste Reihenfolge: gleicher Seed gibt gleiche Datei
            if name in szenarien:
                segs += PLANER[name](ctx, idx, tag)
        for n, s in enumerate(segs):
            s.reihe = n
        for s in sorted(segs, key=lambda s: (s.stunde, s.reihe)):
            std = int(s.stunde)
            beginn = datetime(tag.year, tag.month, tag.day, std, int((s.stunde - std) * 60), tzinfo=tz).timestamp()
            if beginn > grenze:
                continue
            w.bis(beginn)
            _stelle_ein(w, s)
            s.lauf(w, ctx)
            zaehler[s.name] += 1
            aus = s.danach_aus if s.danach_aus is not None else rng.random() < 0.4
            if aus and w.an:
                w.herunterfahren()
    if w.an:  # am Ende ruhig auslaufen: die letzte Sitzung endet mit ``pause`` (30 Minuten)
        w.vor(g.PAUSE_S + 60)
        w.ein(ev.Takt())
    z = w.puffer.z if w.puffer is not None else g.Zustand()
    if z.offen is not None:
        raise SzenarioFehler("interner Fehler: am Ende ist noch eine Sitzung offen")
    inhalt = g.zu_json(z)
    pruefe(inhalt)
    return Ergebnis(inhalt, fasse_zusammen(inhalt, tage, seed, szenarien, katalog), w.ereignisse, zaehler)


def pruefe(inhalt: dict[str, Any]) -> None:
    """Jede Zeile erfüllt den Vertrag (``mqtt-v1.md`` 3.4); sonst ``SzenarioFehler``."""
    gesehen: set[str] = set()
    for r in inhalt["zeilen"]:
        if g.pruefe_zeile(r) != r:
            raise SzenarioFehler(f"Zeile verletzt den Vertrag: {r}")
        if r["sitzung"] in gesehen:
            raise SzenarioFehler(f"Sitzung doppelt: {r['sitzung']}")
        gesehen.add(r["sitzung"])
    if len(inhalt["zeilen"]) > g.MAX_ZEILEN or inhalt["offen"] is not None:
        raise SzenarioFehler("zu viele Zeilen oder eine offene Sitzung")


def fasse_zusammen(inhalt: dict[str, Any], tage: int, seed: int, szenarien: Sequence[str], katalog: Katalog) -> str:
    zeilen = inhalt["zeilen"]
    ende = Counter(r["ende"] for r in zeilen)
    stunden = sum(r["gehoert_s"] for r in zeilen) / 3600
    je_serie: Counter[str] = Counter()
    for r in zeilen:
        je_serie[r["serie"]] += r["gehoert_s"]
    datiert = sorted(r["beginn"] for r in zeilen if r["zeit_ok"])
    boots = len({r["boot_id"] for r in zeilen})
    z = [
        f"Szenarien: {', '.join(szenarien)}  (Tage {tage}, Seed {seed}, Katalog: {katalog.quelle})",
        f"Zeilen im Puffer: {len(zeilen)} von höchstens {g.MAX_ZEILEN}, verworfen (Überlauf): {inhalt['verworfen']}",
        f"Hörzeit gesamt: {stunden:.1f} h in {boots} Gerätestarts",
    ]
    if datiert:
        z.append(f"Zeitraum (nur Zeilen mit guter Uhr): {datiert[0][:10]} bis {datiert[-1][:10]}")
    z.append(f"Zeilen mit unsicherer Uhr (zeit_ok = false): {sum(1 for r in zeilen if not r['zeit_ok'])}")
    z.append("Enden: " + ", ".join(f"{k} {v}" for k, v in sorted(ende.items())))
    z.append("Hörzeit je Serie: " + ", ".join(f"{k} {v / 3600:.1f} h" for k, v in je_serie.most_common()))
    return "\n".join(z)


# --------------------------------------------------------------------------
# Kommandozeile
# --------------------------------------------------------------------------


def lies_pfade(konfig: Path) -> tuple[Path, Path | None]:
    """``[pfade] zustand`` und ``medien`` der Konfiguration (relativ zum Ordner der Datei), ohne das Passwort zu brauchen."""
    try:
        with open(konfig, "rb") as f:
            roh = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise SzenarioFehler(f"{konfig}: {e}") from e
    p = roh.get("pfade")
    if not isinstance(p, dict) or not isinstance(p.get("zustand"), str):
        raise SzenarioFehler(f"{konfig}: [pfade] zustand fehlt")
    basis = konfig.resolve().parent

    def pfad(t: str) -> Path:
        q = Path(t).expanduser()
        return q if q.is_absolute() else basis / q

    medien = p.get("medien")
    return pfad(p["zustand"]), pfad(medien) if isinstance(medien, str) else None


def box_laeuft(zustand: Path) -> bool:
    """Die Box ist an, wenn ``sim.sock`` im Zustandsordner antwortet (dann würde sie die Datei beim nächsten Schreiben überschreiben)."""
    sock = zustand / "sim.sock"
    if not sock.exists():
        return False
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(str(sock))
        return True
    except OSError:
        return False
    finally:
        s.close()


def parse_jetzt(text: str | None) -> float:
    if text is None:
        return datetime.now(timezone.utc).timestamp()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError as e:
        raise SzenarioFehler(f"--jetzt: keine ISO-Zeit: {text}") from e


def baue_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gehoert_szenario.py", description="Hördaten für die Test-Box erzeugen (Puffer gehoert.json).")
    p.add_argument("--konfig", type=Path, help="Konfiguration der Test-Box (z. B. config/boxsim.toml): Zustandsordner und Medien")
    p.add_argument("--zustand", type=Path, help="Zustandsordner (statt --konfig)")
    p.add_argument("--medien", type=Path, help="Medienordner (statt der aus --konfig); sonst erfundene Serien")
    p.add_argument("--serien", type=Path, help="JSON-Datei mit Serien, Folgen und echten Dauern (siehe Anleitung); ersetzt --medien")
    p.add_argument("--anzahl-serien", type=int, default=12, help="so viele Serien wählt --seed aus --serien aus (Vorgabe 12)")
    p.add_argument("--tage", type=int, default=40, help="so viele Tage bis jetzt (Vorgabe 40)")
    p.add_argument("--seed", type=int, default=1, help="gleicher Seed: gleiche Daten (Vorgabe 1)")
    p.add_argument("--szenario", action="append", help=f"Komma-Liste aus {', '.join(SZENARIEN)}, alle (Vorgabe: {', '.join(VORGABE_SZENARIEN)})")
    p.add_argument("--jetzt", help="Ende der simulierten Zeit (ISO, Vorgabe: jetzt); fest für gleiche Ergebnisse an jedem Tag")
    p.add_argument("--zeitzone", default="Europe/Berlin", help="Ortszeit für Tageszeiten (Vorgabe Europe/Berlin)")
    p.add_argument("--virtuelle-dauer", type=int, default=VIRTUELLE_DAUER_S, help="Länge für Testfolgen unter 5 Minuten (Sekunden)")
    p.add_argument("--trocken", action="store_true", help="nur zusammenfassen, nichts schreiben")
    p.add_argument("--ueberschreiben", action="store_true", help="eine vorhandene gehoert.json ersetzen")
    return p


def waehle_szenarien(roh: Sequence[str] | None) -> tuple[str, ...]:
    if not roh:
        return VORGABE_SZENARIEN
    namen: list[str] = []
    for teil in roh:
        for n in teil.split(","):
            n = n.strip()
            if n == "alle":
                namen += list(SZENARIEN)
            elif n:
                namen.append(n)
    return tuple(dict.fromkeys(namen))


def main(argv: Sequence[str] | None = None) -> int:
    a = baue_parser().parse_args(argv)
    try:
        zustand: Path | None = a.zustand
        medien: Path | None = a.medien
        if a.konfig is not None:
            z, m = lies_pfade(a.konfig)
            zustand = zustand or z
            medien = medien or m
        if zustand is None and not a.trocken:
            raise SzenarioFehler("--konfig oder --zustand fehlt (zum Ausprobieren ohne Test-Box: --trocken)")
        if a.serien is not None:
            katalog = lade_serien_datei(a.serien, anzahl=a.anzahl_serien, seed=a.seed)
        else:
            katalog = lade_katalog(medien, virtuell_s=a.virtuelle_dauer)
        e = erzeuge(
            tage=a.tage, seed=a.seed, szenarien=waehle_szenarien(a.szenario), jetzt=parse_jetzt(a.jetzt), katalog=katalog, zone=a.zeitzone,
        )
        print(e.zusammenfassung)
        if a.trocken:
            print("\n--trocken: nichts geschrieben.")
            return 0
        assert zustand is not None
        ziel = zustand / NAME
        if box_laeuft(zustand):
            raise SzenarioFehler(f"die Test-Box läuft ({zustand / 'sim.sock'} antwortet): bitte zuerst stoppen, sie würde die Datei überschreiben")
        if ziel.exists() and not a.ueberschreiben:
            try:
                alt = g.parse_datei(json.loads(ziel.read_text(encoding="utf-8")))
                vorhanden = bool(alt.zeilen or alt.offen)
            except (OSError, ValueError, Exception):  # noqa: BLE001 - eine kaputte Datei ist auch „vorhanden“
                vorhanden = True
            if vorhanden:
                raise SzenarioFehler(f"{ziel} enthält schon Daten: mit --ueberschreiben ersetzen (oder die Datei vorher löschen)")
        schreibe_atomar(ziel, e.inhalt)
        print(f"\nGeschrieben: {ziel}\nNächster Schritt: Test-Box starten, sie sendet die Zeilen, sobald sie mit Home Assistant verbunden ist.")
        return 0
    except SzenarioFehler as e:
        print(f"gehoert_szenario: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
