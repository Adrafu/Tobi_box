"""Hilfen für die Tests der Stufe 4 (AP 4.8): lange Serien, Konfiguration mit Fenstern, Wanduhr, Bedienung, Ring.

Alles auf Basis von ``conftest.CujBox``: echter Kern (mit ``quiet``, ``bedtime`` und ``idle``), echte Bibliothek, echter Speicher,
simulierter Player und simulierte Uhr.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from conftest import CujBox, mk_konfig
from fixtures import audio

from tobibox import events as ev
from tobibox.controls import Bedienung
from tobibox.led import LedLogik
from tobibox.volume import wirksame_grenze

BERLIN = ZoneInfo("Europe/Berlin")
ALLE_TAGE = (1, 2, 3, 4, 5, 6, 7)

_CACHE = Path(tempfile.mkdtemp(prefix="tb-lang-"))


def wall(jahr: int, monat: int, tag: int, h: int, m: int, s: int = 0) -> float:
    """Unix-Sekunden einer Berliner Ortszeit. 2026-11-09 ist ein Montag."""
    return datetime(jahr, monat, tag, h, m, s, tzinfo=BERLIN).timestamp()


def lange_wav(dauer_s: float) -> Path:
    """Eine WAV-Datei dieser Länge, einmal erzeugt und dann kopiert (sonst dauert jeder Test mehrere Sekunden)."""
    pfad = _CACHE / f"{dauer_s:g}.wav"
    if not pfad.exists():
        audio.schreibe_wav(pfad, dauer_s)
    return pfad


def serie(medien: Path, ordner: str, folgen: list[str], serie_id: str, name: str, dauer_s: float) -> None:
    """Wie ``audio.erzeuge_serie``, aber mit zwischengespeicherten langen Dateien."""
    audio.erzeuge_serie(medien, ordner, folgen, serie_id=serie_id, name=name, dauer_s=0.2)
    for f in folgen:
        shutil.copyfile(lange_wav(dauer_s), medien / ordner / f)


def ueberraschung(medien: Path) -> None:
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


def fenster(fid: str, wirkung: str, von: str, bis: str, grenze: int | None = None, tage=ALLE_TAGE) -> ev.Fenster:
    return ev.Fenster(fid, tuple(tage), von, bis, wirkung, grenze)  # type: ignore[arg-type]


def setze_konfig(box: CujBox, *, gute_nacht: ev.GuteNacht | None = None, fenster_liste=(), revision: int = 2) -> None:
    """Neue Konfiguration (wie von HA): Zuordnungen der Box, dazu Gute-Nacht-Dauern und Leise-Zeiten."""
    k = mk_konfig(box.zuordnungen, revision=revision, lesezeichen_tage=box.lesezeichen_tage)
    k = replace(
        k,
        gute_nacht=gute_nacht or k.gute_nacht,
        leise_zeiten=ev.LeiseZeiten("Europe/Berlin", tuple(fenster_liste)),
    )
    box.sende(ev.KonfigGeladen(k))


def lautstaerken(box: CujBox, ab: int = 0) -> list[ev.LautstaerkeSetzen]:
    return [b for b in box.log[ab:] if isinstance(b, ev.LautstaerkeSetzen)]


def prozente(box: CujBox, ab: int = 0) -> list[int]:
    return [b.prozent for b in lautstaerken(box, ab)]


def zeile(box: CujBox) -> ev.ZustandMelden:
    """Die zuletzt gemeldete Zusammenfassung des Kerns."""
    return box.kern.gemeldet


def wirksam(box: CujBox) -> int:
    from tobibox.volume import klemmen

    return klemmen(box.kern.wunsch, box.kern.grenzen)


def gehe_bis(box: CujBox, bedingung, max_s: float = 600.0, schritt: float = 1.0) -> float:
    """Die Zeit läuft in Schritten, bis ``bedingung()`` gilt. Gibt die vergangenen Sekunden zurück."""
    vergangen = 0.0
    while not bedingung():
        assert vergangen < max_s, "Bedingung nicht erreicht"
        box.laufe(schritt)
        vergangen += schritt
    return vergangen


class BedienBox(CujBox):
    """``CujBox`` mit ``Bedienung`` (Tasten, Drehregler) und ``LedLogik``: dieselben Teile wie in ``app.py``.

    ``bedienung`` sendet in ``sende``; nach jedem Schritt führt die Box Lautstärke und Ring nach (wie ``App._nachfuehren_stufe_4``).
    """

    def __init__(self, *a, **kw) -> None:
        self.led = LedLogik()
        self.bedienung = None  # type: ignore[assignment]
        super().__init__(*a, **kw)
        self.bedienung = Bedienung(self.sende, stand=self.kern.wunsch, grenze=wirksame_grenze(self.kern.grenzen))
        self._fuehre_nach()

    def sende(self, e, dt: float = 0.0) -> list:
        befehle = super().sende(e, dt)
        self.led.beobachte(e, self.uhr.mono)
        for b in befehle:
            if isinstance(b, ev.ZustandMelden):
                self.led.beobachte(b, self.uhr.mono)
        self._fuehre_nach()
        return befehle

    def _fuehre_nach(self) -> None:
        if self.bedienung is not None:
            self.bedienung.setze_lautstaerke(self.kern.wunsch, wirksame_grenze(self.kern.grenzen))
        b = self.kern.teil["bedtime"]
        faktor = None
        if b.modus == "ausblenden" and b.von > 0:
            faktor = (b.letzter if b.letzter is not None else b.von) / b.von
        self.led.setze_ausblenden(faktor)

    def ring(self):
        return self.led.ring(self.uhr.mono)

    def ring_zustand(self) -> str:
        return self.led.zustand(self.uhr.mono)
