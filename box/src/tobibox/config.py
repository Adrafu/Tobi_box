"""``tobibox.toml`` laden und prüfen (``tomllib``).

Eine Konfigurationsdatei je Gerät (Design, „Mac und Pi“). Es gibt keine Abfrage
„bin ich am Mac?“: Unterschiede stehen nur in den Werten. Zugangsdaten
(MQTT-Passwort) kommen erst in Stufe 3 und liegen nur in dieser Datei, nie im Repo.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import events as ev
from .eventlog import EBENEN, logge


class KonfigFehler(ValueError):
    """``tobibox.toml`` fehlt, ist kein gültiges TOML oder hat ungültige Werte."""


@dataclass(frozen=True, slots=True)
class Pfade:
    zustand: Path
    medien: Path


#: ``leser.geraet = "sim"``: kein Leser, die Leser-Ereignisse kommen aus ``sim`` (Prüfpunkt „Leser“: ``simulation``)
LESER_SIMULATION = "sim"


@dataclass(frozen=True, slots=True)
class LeserKonfig:
    geraet: str = "/dev/cu.usbmodem*"

    @property
    def simulation(self) -> bool:
        return self.geraet == LESER_SIMULATION


@dataclass(frozen=True, slots=True)
class MpdKonfig:
    host: str = "localhost"
    port: int = 6600


@dataclass(frozen=True, slots=True)
class LautstaerkeKonfig:
    max: int = 50  # globale Obergrenze
    start: int = 20
    kopfhoerer: int = 30


#: Mac-Vorgabe; auf dem Pi ["aplay", "-q", "{datei}"] (optional "-D", "<Gerät>").
#: Nötig ist nur {datei}: die Töne werden in Python auf den Pegel skaliert (sounds.py).
#: Optional weiter ersetzt: {pegel} (0 bis 100), {lautstaerke} (0.0 bis 1.0).
STANDARD_TON_KOMMANDO: tuple[str, ...] = ("afplay", "{datei}")
STANDARD_TON_KOMMANDO_PI: tuple[str, ...] = ("aplay", "-q", "{datei}")


@dataclass(frozen=True, slots=True)
class TonKonfig:
    kommando: tuple[str, ...] = STANDARD_TON_KOMMANDO
    ordner: Path | None = None  # None: ``box/sounds`` neben dem Quellbaum


@dataclass(frozen=True, slots=True)
class ProtokollKonfig:
    ziel: str = "stdout"  # "stdout" (Pi) oder "datei" (Mac)
    datei: Path | None = None
    ebene: str = "INFO"
    max_bytes: int = 1_000_000
    anzahl: int = 5


@dataclass(frozen=True, slots=True)
class BoxKonfig:
    pfade: Pfade
    leser: LeserKonfig = field(default_factory=LeserKonfig)
    mpd: MpdKonfig = field(default_factory=MpdKonfig)
    lautstaerke: LautstaerkeKonfig = field(default_factory=LautstaerkeKonfig)
    protokoll: ProtokollKonfig = field(default_factory=ProtokollKonfig)
    toene: TonKonfig = field(default_factory=TonKonfig)

    def geraete_einstellungen(self) -> ev.GeraeteEinstellungen:
        """Das erste Ereignis des Kerns (``core-interface.md``, 3.3)."""
        v = self.lautstaerke
        return ev.GeraeteEinstellungen(v.max, v.start, v.kopfhoerer)


_BEKANNT = {
    "pfade": {"zustand", "medien"},
    "leser": {"geraet"},
    "mpd": {"host", "port"},
    "lautstaerke": {"max", "start", "kopfhoerer"},
    "protokoll": {"ziel", "datei", "ebene", "max_bytes", "anzahl"},
    "toene": {"kommando", "ordner"},
}


def _abschnitt(roh: dict[str, Any], name: str, pflicht: bool = False) -> dict[str, Any]:
    wert = roh.get(name)
    if wert is None:
        if pflicht:
            raise KonfigFehler(f"Abschnitt [{name}] fehlt")
        return {}
    if not isinstance(wert, dict):
        raise KonfigFehler(f"[{name}] muss ein Abschnitt sein")
    unbekannt = set(wert) - _BEKANNT[name]
    if unbekannt:  # nur warnen: eine neuere Datei muss nach einem Update-Rückfall noch laden
        logge("config", "WARNING", "unbekannte_schluessel", "ignoriert",
              daten={"abschnitt": name, "schluessel": sorted(unbekannt)})
    return wert


def _ganz(a: dict[str, Any], name: str, schluessel: str, vorgabe: int, lo: int, hi: int) -> int:
    wert = a.get(schluessel, vorgabe)
    if isinstance(wert, bool) or not isinstance(wert, int) or not lo <= wert <= hi:
        raise KonfigFehler(f"[{name}] {schluessel} muss eine ganze Zahl von {lo} bis {hi} sein")
    return wert


def _text(a: dict[str, Any], name: str, schluessel: str, vorgabe: str | None) -> str | None:
    wert = a.get(schluessel, vorgabe)
    if wert is None:
        return None
    if not isinstance(wert, str) or not wert.strip():
        raise KonfigFehler(f"[{name}] {schluessel} muss ein nicht leerer Text sein")
    return wert


def _pfad(text: str, basis: Path) -> Path:
    p = Path(text).expanduser()
    return p if p.is_absolute() else basis / p


def pruefe(roh: dict[str, Any], basis: Path | None = None) -> BoxKonfig:
    """Rohe TOML-Daten prüfen; relative Pfade gelten ab ``basis`` (Ordner der Datei)."""
    basis = basis or Path.cwd()
    unbekannt = set(roh) - set(_BEKANNT)
    if unbekannt:
        logge("config", "WARNING", "unbekannte_abschnitte", "ignoriert", daten={"abschnitte": sorted(unbekannt)})

    p = _abschnitt(roh, "pfade", pflicht=True)
    zustand = _text(p, "pfade", "zustand", None)
    medien = _text(p, "pfade", "medien", None)
    if zustand is None or medien is None:
        raise KonfigFehler("[pfade] braucht 'zustand' und 'medien'")

    leser = _abschnitt(roh, "leser")
    mpd = _abschnitt(roh, "mpd")
    vol = _abschnitt(roh, "lautstaerke")
    prot = _abschnitt(roh, "protokoll")
    ton = _abschnitt(roh, "toene")
    kommando = ton.get("kommando", list(STANDARD_TON_KOMMANDO))
    if (
        not isinstance(kommando, list)
        or not kommando
        or not all(isinstance(k, str) and k for k in kommando)
    ):
        raise KonfigFehler("[toene] kommando muss eine nicht leere Liste von Texten sein")
    ton_ordner = _text(ton, "toene", "ordner", None)

    maximum = _ganz(vol, "lautstaerke", "max", 50, 0, 100)
    # Nur ``max`` gegeben: die Vorgaben werden auf ``max`` gekappt. Ausdrücklich
    # gesetzte Werte über ``max`` sind ein Fehler im Eintrag, kein stilles Kappen.
    v = LautstaerkeKonfig(
        max=maximum,
        start=_ganz(vol, "lautstaerke", "start", min(20, maximum), 0, 100),
        kopfhoerer=_ganz(vol, "lautstaerke", "kopfhoerer", min(30, maximum), 0, 100),
    )
    if v.start > v.max:
        raise KonfigFehler("[lautstaerke] start darf nicht über max liegen")
    if v.kopfhoerer > v.max:
        raise KonfigFehler("[lautstaerke] kopfhoerer darf nicht über max liegen")

    ziel = _text(prot, "protokoll", "ziel", "stdout")
    if ziel not in ("stdout", "datei"):
        raise KonfigFehler("[protokoll] ziel muss 'stdout' oder 'datei' sein")
    datei = _text(prot, "protokoll", "datei", None)
    if ziel == "datei" and datei is None:
        raise KonfigFehler("[protokoll] ziel='datei' braucht 'datei'")
    ebene = _text(prot, "protokoll", "ebene", "INFO")
    if ebene not in EBENEN:
        raise KonfigFehler("[protokoll] ebene muss DEBUG, INFO, WARNING oder ERROR sein")

    return BoxKonfig(
        pfade=Pfade(_pfad(zustand, basis), _pfad(medien, basis)),
        leser=LeserKonfig(_text(leser, "leser", "geraet", "/dev/cu.usbmodem*") or ""),
        mpd=MpdKonfig(
            _text(mpd, "mpd", "host", "localhost") or "localhost",
            _ganz(mpd, "mpd", "port", 6600, 1, 65535),
        ),
        lautstaerke=v,
        protokoll=ProtokollKonfig(
            ziel=ziel or "stdout",
            datei=_pfad(datei, basis) if datei else None,
            ebene=ebene or "INFO",
            max_bytes=_ganz(prot, "protokoll", "max_bytes", 1_000_000, 10_000, 100_000_000),
            anzahl=_ganz(prot, "protokoll", "anzahl", 5, 1, 50),
        ),
        toene=TonKonfig(tuple(kommando), _pfad(ton_ordner, basis) if ton_ordner else None),
    )


def lade(pfad: str | Path) -> BoxKonfig:
    """``tobibox.toml`` lesen und prüfen; wirft ``KonfigFehler``."""
    pfad = Path(pfad)
    try:
        with open(pfad, "rb") as f:
            roh = tomllib.load(f)
    except FileNotFoundError as e:
        raise KonfigFehler(f"Konfigurationsdatei fehlt: {pfad}") from e
    except tomllib.TOMLDecodeError as e:
        raise KonfigFehler(f"{pfad}: kein gültiges TOML: {e}") from e
    except OSError as e:
        raise KonfigFehler(f"{pfad}: nicht lesbar: {e}") from e
    return pruefe(roh, pfad.resolve().parent)
