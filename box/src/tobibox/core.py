"""Der Kern: kombiniert die Teilautomaten (``core-interface.md``, Abschnitt 6).

Reine Logik: keine Datei, kein Netz, keine Uhr, kein Zufall. ``step`` nimmt ein
äußeres Ereignis und gibt den neuen Zustand und die geordneten Befehle zurück.

Ablauf (6.1): Ereignis in eine Warteschlange, jedes Ereignis geht an alle
Teilautomaten in fester Reihenfolge, interne Ereignisse kommen hinten in die
Warteschlange, ``core`` behandelt ``GrenzeGesetzt`` selbst und rechnet am Ende
die Lautstärke aus dem Nettowert. Danach Konfliktregeln (6.2), ``ZustandMelden``
und stabile Sortierung nach Rang (6.4).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import ModuleType
from typing import Any

from . import events as ev
from . import session
from .events import Jetzt
from .volume import (
    GRENZE_AUSBLENDEN,
    GRENZE_GLOBAL,
    GRENZE_GUTE_NACHT,
    klemmen,
    wirksame_grenze,
)

#: Teilautomaten in fester Reihenfolge. Das Integrations-AP der Stufe trägt
#: ``learn``, ``quiet``, ``bedtime`` und ``idle`` hier ein (Reihenfolge laut
#: Vertrag: session, learn, quiet, bedtime, idle).
TEILAUTOMATEN: tuple[tuple[str, ModuleType], ...] = (("session", session),)

MAX_EREIGNISSE = 32

_TOENE_UNTER_STUMM = frozenset({"start", "unbekannt", "lernen_beginn", "lernen_ende", "fehler", "akku_leer"})

_RANG: dict[type, int] = {
    ev.LautstaerkeSetzen: 1,
    ev.AusgangWaehlen: 2,
    ev.Pausieren: 3,
    ev.ZeigerSpeichern: 4,
    ev.Abspielen: 5,
    ev.TonSpielen: 6,
    ev.StatusPruefen: 6,
    ev.Melden: 7,
    ev.EreignisSenden: 7,
    ev.LeserPing: 7,
    ev.ZustandMelden: 7,
    ev.Protokoll: 7,
    ev.SyncAbbrechen: 8,
    ev.SyncStarten: 9,
    ev.UpdateStarten: 9,
    ev.Herunterfahren: 10,
}


@dataclass(frozen=True, slots=True)
class KernZustand:
    teil: Mapping[str, Any]  # Name -> Zustand des Teilautomaten
    grenzen: Mapping[str, int] = field(default_factory=dict)
    wunsch: int = 0
    wirksam_gemeldet: int | None = None  # zuletzt als LautstaerkeGeaendert gemeldet
    ausgegeben: ev.LautstaerkeSetzen | None = None  # zuletzt ausgegebener Befehl
    zurueckgehalten: bool = False  # Regel 7: Anstieg vor einer Pause zurückgehalten
    gemeldet: ev.ZustandMelden | None = None  # zuletzt gemeldete Zusammenfassung

    @property
    def session(self) -> session.Zustand:
        return self.teil["session"]


def neuer_zustand() -> KernZustand:
    return KernZustand(teil={name: modul.neuer_zustand() for name, modul in TEILAUTOMATEN})


def _zusammenfassung(teil: Mapping[str, Any]) -> ev.ZustandMelden:
    def kz(name: str, standard: str) -> str:
        for n, modul in TEILAUTOMATEN:
            if n == name:
                return modul.kennzeichen(teil[n])
        return standard

    sz: session.Zustand = teil["session"]
    return ev.ZustandMelden(
        sitzung=session.kennzeichen(sz),
        strom=kz("idle", "aktiv"),  # type: ignore[arg-type]
        serie_id=sz.serie_id,
        lernmodus=kz("learn", "aus") == "lernt",
        ruhe=kz("quiet", "normal"),  # type: ignore[arg-type]
        gute_nacht=kz("bedtime", "aus"),  # type: ignore[arg-type]
        figur_liegt=session.figur_liegt(sz),
        folge=sz.datei if sz.serie_id is not None else None,
        track=sz.track if sz.serie_id is not None and sz.datei is not None else None,
    )


def _prozent(wert: int) -> int:
    return max(0, min(100, int(wert)))


def _konflikte(befehle: list, ruhe: str) -> list:
    """Konfliktregeln 1 bis 5 (6 und 7 betreffen die Lautstärke, siehe ``step``)."""
    # 1. Herunterfahren hat Vorrang
    if any(isinstance(b, ev.Herunterfahren) for b in befehle):
        weg = (ev.Abspielen, ev.SyncStarten, ev.UpdateStarten, ev.AusgangWaehlen)
        befehle = [b for b in befehle if not isinstance(b, weg)]
    # 2. Töne unter „stumm“
    if ruhe == "stumm":
        befehle = [
            ev.TonSpielen("hinweis") if isinstance(b, ev.TonSpielen) and b.ton in _TOENE_UNTER_STUMM else b
            for b in befehle
        ]
    # 3. doppelte Töne
    gesehen_ton: set[str] = set()
    ergebnis = []
    for b in befehle:
        if isinstance(b, ev.TonSpielen):
            if b.ton in gesehen_ton:
                continue
            gesehen_ton.add(b.ton)
        ergebnis.append(b)
    befehle = ergebnis
    # 4. doppelte Meldungen: „gelernt“ gewinnt und behält seine befehl_id
    erste: dict[str, int] = {}
    ergebnis = []
    for b in befehle:
        if isinstance(b, ev.Melden):
            if b.uid in erste:
                i = erste[b.uid]
                if b.art == "gelernt":
                    ergebnis[i] = b
                continue
            erste[b.uid] = len(ergebnis)
        ergebnis.append(b)
    befehle = ergebnis
    # 5. mehrere Abspielen: das letzte bleibt
    letztes = max((i for i, b in enumerate(befehle) if isinstance(b, ev.Abspielen)), default=None)
    if letztes is not None:
        befehle = [b for i, b in enumerate(befehle) if not isinstance(b, ev.Abspielen) or i == letztes]
    return befehle


def step(
    zustand: KernZustand, ereignis: ev.Ereignis, jetzt: Jetzt
) -> tuple[KernZustand, tuple[ev.Befehl, ...]]:
    teil = dict(zustand.teil)
    grenzen = dict(zustand.grenzen)
    wunsch = zustand.wunsch
    wunsch_start = wunsch
    wirksam_gemeldet = zustand.wirksam_gemeldet
    befehle: list = []
    herunterfahren: str | None = None
    geloescht = False  # ausblenden/gute_nacht in dieser Verarbeitung gelöscht
    start_setzen = False

    schlange: deque = deque([ereignis])
    verarbeitet = 0
    abgebrochen = False
    while True:
        while schlange:
            if verarbeitet >= MAX_EREIGNISSE:
                # Schutz gegen Schleifen (6.1, Schritt 3)
                befehle.append(
                    ev.Protokoll(
                        "core", "ERROR", "kern_schleife", "abgebrochen", None, {"ereignisse": verarbeitet}
                    )
                )
                schlange.clear()
                abgebrochen = True
                break
            e = schlange.popleft()
            verarbeitet += 1

            if isinstance(e, ev.GrenzeGesetzt):
                if e.prozent is None:
                    if grenzen.pop(e.name, None) is not None and e.name in (GRENZE_AUSBLENDEN, GRENZE_GUTE_NACHT):
                        geloescht = True
                else:
                    grenzen[e.name] = e.prozent
                continue

            # Spezialbehandlung durch den Kern
            if isinstance(e, ev.GeraeteEinstellungen):
                e = replace(
                    e,
                    lautstaerke_max=_prozent(e.lautstaerke_max),
                    lautstaerke_start=_prozent(e.lautstaerke_start),
                    lautstaerke_kopfhoerer=_prozent(e.lautstaerke_kopfhoerer),
                )
                grenzen[GRENZE_GLOBAL] = e.lautstaerke_max
                # nur die globale Grenze kappt den Startwert; Kopfhörer & Co. klemmt `klemmen` am Ende
                wunsch = min(e.lautstaerke_start, e.lautstaerke_max)
                start_setzen = True
            elif isinstance(e, ev.LautstaerkeDrehen):
                wunsch = max(0, min(wunsch + e.delta, wirksame_grenze(grenzen)))
            elif isinstance(e, ev.AktionAusgeloest) and e.aktion == "status":
                befehle.append(ev.StatusPruefen(e.vorgang))
            elif isinstance(e, ev.HerunterfahrenAngefordert):
                herunterfahren = e.grund

            for name, modul in TEILAUTOMATEN:
                teil[name], out = modul.step(teil[name], e, jetzt)
                for o in out:
                    if isinstance(o, ev.InternesEreignis):
                        schlange.append(o)
                    else:
                        befehle.append(o)

        if abgebrochen:
            break
        wirksam = klemmen(wunsch, grenzen)
        if wirksam != wirksam_gemeldet:
            wirksam_gemeldet = wirksam
            schlange.append(ev.LautstaerkeGeaendert(wirksam))
            continue
        break

    if herunterfahren is not None:
        befehle.append(ev.Herunterfahren(herunterfahren))  # type: ignore[arg-type]

    # Konfliktregeln 1 bis 5
    ruhe = _zusammenfassung(teil).ruhe
    befehle = _konflikte(befehle, ruhe)

    # Lautstärke: Nettowert am Ende (Abschnitt 8), Regeln 6 und 7
    cand = ev.LautstaerkeSetzen(klemmen(wunsch, grenzen), wirksame_grenze(grenzen))
    ausgegeben = zustand.ausgegeben
    zurueckgehalten = zustand.zurueckgehalten
    vol: ev.LautstaerkeSetzen | None = None
    if any(isinstance(b, ev.Abspielen) for b in befehle):
        vol = cand  # Regel 6: immer, auch bei gleichem Wert
        zurueckgehalten = False
    elif start_setzen or (ausgegeben is not None and cand != ausgegeben):
        hat_pause = any(isinstance(b, ev.Pausieren) for b in befehle)
        steigt = ausgegeben is not None and cand.prozent > ausgegeben.prozent
        wunsch_gleich = wunsch == wunsch_start
        if steigt and wunsch_gleich and not start_setzen and (zurueckgehalten or (geloescht and hat_pause)):
            zurueckgehalten = True  # Regel 7
        else:
            vol = cand
            zurueckgehalten = False
    if vol is not None:
        befehle.append(vol)
        ausgegeben = vol

    neu = KernZustand(
        teil=teil,
        grenzen=grenzen,
        wunsch=wunsch,
        wirksam_gemeldet=wirksam_gemeldet,
        ausgegeben=ausgegeben,
        zurueckgehalten=zurueckgehalten,
        gemeldet=zustand.gemeldet,
    )

    # ZustandMelden bei Änderung
    zus = _zusammenfassung(teil)
    if zus != zustand.gemeldet:
        befehle.append(zus)
        neu = replace(neu, gemeldet=zus)

    # stabile Sortierung nach Rang (6.4)
    befehle.sort(key=lambda b: _RANG.get(type(b), 7))
    return neu, tuple(befehle)
