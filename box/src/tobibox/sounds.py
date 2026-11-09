"""Kurze Töne über ein konfigurierbares Kommando (``core-interface.md``, 8.1).

Die Lautstärke setzt **dieses Modul selbst**: die 16-Bit-PCM-Samples der WAV-Datei
werden in Python mit der Verstärkung des Pegels multipliziert und in eine temporäre
Datei geschrieben. Die Verstärkung folgt **derselben Kennlinie wie MPD** (``Kennlinie``,
Entscheidung J, 09.11.): so klingt ein Ton bei gleicher Lautstärke so laut wie das Hörspiel. Das Kommando braucht nur ``{datei}``: Mac
``afplay {datei}``, Pi ``aplay -q {datei}``. Die Platzhalter ``{pegel}`` (0 bis 100)
und ``{lautstaerke}`` (0.0 bis 1.0) werden weiter ersetzt, wenn sie vorkommen, aber
die Skalierung geschieht immer. So sind Töne auch bei einem Abspielprogramm ohne
Pegeloption nie lauter als die Grenze.

Pegel in Prozent (Entscheidung J, 09.11.): alle Töne außer ``hinweis``:
``min(grenze, max(TON_MINDEST, lautstaerke))``, also die aktuelle Lautstärke der Sitzung,
nie über der wirksamen Grenze und nie unter der Untergrenze 10; ``hinweis``:
``max(HINWEIS_MINDEST, min(hinweis_pegel, lautstaerke))`` (Vorgabe 15, Untergrenze 10). Ohne Tondatei, oder
wenn die Datei kein 16-Bit-PCM ist (nicht sicher skalierbar), wird nichts gestartet.

Rückfall der Status-Karte: Fehlt ``pruef_<punkt>_ok``, ``pruef_<punkt>_fehler`` oder
``pruef_leser_simulation`` im Tonordner, spielt die Box den allgemeinen Ton ``pruef_ok``
(bei ``_fehler`` ``pruef_fehler``). So bleibt ein Ordner nur mit den allgemeinen Tönen gültig.
"""

from __future__ import annotations

import array
import asyncio
import contextlib
import math
import os
import re
import sys
import tempfile
import wave
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import KENNLINIE_ALSA_SOFTVOL, KENNLINIE_MPD_SOFTWARE, STANDARD_SOFTVOL_BEREICH_DB
from .eventlog import logge

TON_MINDEST = 10  # Untergrenze der Ton-Lautstärke in Prozent: ein Ton bleibt hörbar (Entscheidung J)
HINWEIS_PEGEL_VORGABE = 15
HINWEIS_MINDEST = 10  # unter „stumm“ (Lautstärke 0) bleibt der Hinweiston hörbar; wie TON_MINDEST
TON_MAX_S = 10.0
_PRUEF_PUNKT = re.compile(r"^pruef_[a-z]+_(ok|simulation|fehler)$")  # ein hängendes Abspielprogramm wird danach beendet


def pegel(ton: str, grenze: int, lautstaerke: int | None = None, hinweis_pegel: int | None = None) -> int:
    """Pegel in Prozent (0 bis 100) auf der Skala der MPD-Lautstärke.

    ``lautstaerke`` ist die aktuelle Lautstärke der Sitzung (zuletzt mit ``LautstaerkeSetzen`` ausgegeben),
    ``grenze`` die wirksame Grenze. Ohne ``lautstaerke`` gilt die Grenze.
    """
    grenze = max(0, min(100, int(grenze)))
    laut = grenze if lautstaerke is None else max(0, min(100, int(lautstaerke), grenze))
    if ton == "hinweis":
        h = HINWEIS_PEGEL_VORGABE if hinweis_pegel is None else hinweis_pegel
        return max(HINWEIS_MINDEST, min(h, laut))
    return min(grenze, max(TON_MINDEST, laut))


# ``54.5981500331`` ist e hoch 4: MPD teilt durch (e^4 - 1), siehe ``Kennlinie``
_E4 = 54.5981500331
_PCM_VOLUME_1 = 1024  # MPD rechnet die Verstärkung in Zehntelbit-Schritten (PCM_VOLUME_BITS = 10)


@dataclass(frozen=True, slots=True)
class Kennlinie:
    """Wie eine Lautstärke in Prozent in eine Verstärkung (Faktor 0 bis 1) umgesetzt wird.

    * ``mpd_software`` (Mac, ``mixer_type "software"``): MPD 0.24, ``SoftwareMixerPlugin.cxx``,
      ``PercentVolumeToSoftwareVolume``: 100 % ist 1,0; sonst ``(exp(p / 25) - 1) / (exp(4) - 1)``;
      0 % ist still. MPD rundet auf 1/1024 (``pcm_float_to_volume``). Kurve: 20 % sind -32,8 dB,
      40 % sind -22,6 dB.
    * ``alsa_softvol`` (Pi: MPD-Mixer ``hardware`` am ALSA-``softvol``-Regler): MPD 0.24,
      ``VolumeMapping.cxx`` (``set_normalized_playback_volume``) legt den Prozentwert auf den dB-Bereich
      des Reglers. Ist der Bereich größer als 24 dB, gilt ``dB = 60 * log10(m + p * (1 - m))`` mit
      ``m = 10 ** (-bereich / 60)`` (0 dB = ``max_dB``, also die harte Kappe); sonst linear in dB.
      Die Verstärkung ist ``10 ** (dB / 20)``, bezogen auf ``max_dB``.
    """

    art: str = KENNLINIE_MPD_SOFTWARE
    softvol_bereich_db: float = STANDARD_SOFTVOL_BEREICH_DB

    def verstaerkung(self, prozent: float) -> float:
        p = max(0.0, min(100.0, float(prozent)))
        if self.art == KENNLINIE_ALSA_SOFTVOL:
            return self._softvol(p / 100)
        return self._mpd_software(p)

    @staticmethod
    def _mpd_software(p: float) -> float:
        if p >= 100:
            return 1.0
        if p <= 0:
            return 0.0
        return round((math.exp(p / 25.0) - 1) / (_E4 - 1) * _PCM_VOLUME_1) / _PCM_VOLUME_1

    def _softvol(self, v: float) -> float:
        bereich = self.softvol_bereich_db
        if bereich <= 24:  # MAX_LINEAR_DB_SCALE in VolumeMapping.cxx: linear in dB
            db = -bereich * (1 - v)
        else:
            m = 10 ** (-bereich / 60)
            db = 60 * math.log10(m + v * (1 - m)) if v < 1 else 0.0
        return 10 ** (db / 20)

    def db(self, prozent: float) -> float:
        """Verstärkung in dB (``-inf`` bei Stille)."""
        g = self.verstaerkung(prozent)
        return 20 * math.log10(g) if g > 0 else float("-inf")


MPD_SOFTWARE = Kennlinie()


def skaliere_wav(quelle: Path, pegel_prozent: int, ziel: Path, kennlinie: Kennlinie = MPD_SOFTWARE) -> None:
    """16-Bit-PCM-WAV auf den Pegel ``pegel_prozent`` (0 bis 100) nach ``kennlinie`` herunterskalieren.

    Schreibt das Ergebnis nach ``ziel``. Wirft ``ValueError``, wenn die Datei kein 16-Bit-PCM ist.
    """
    faktor = kennlinie.verstaerkung(max(0, min(100, int(pegel_prozent))))
    with wave.open(str(quelle), "rb") as r:
        if r.getsampwidth() != 2 or r.getcomptype() != "NONE":
            raise ValueError(f"{quelle.name}: nur 16-Bit-PCM wird unterstützt")
        params = r.getparams()
        roh = r.readframes(r.getnframes())
    samples = array.array("h")
    samples.frombytes(roh[: len(roh) - len(roh) % 2])
    if sys.byteorder == "big":
        samples.byteswap()
    leise = array.array("h", (max(-32768, min(32767, round(x * faktor))) for x in samples))
    if sys.byteorder == "big":
        leise.byteswap()
    with wave.open(str(ziel), "wb") as w:
        w.setparams(params)
        w.writeframes(leise.tobytes())


def baue_kommando(vorlage: Sequence[str], datei: Path, pegel_prozent: int) -> list[str]:
    ersetze = {
        "{datei}": str(datei),
        "{pegel}": str(pegel_prozent),
        "{lautstaerke}": f"{pegel_prozent / 100:.2f}",
    }
    ergebnis = []
    for teil in vorlage:
        for k, v in ersetze.items():
            teil = teil.replace(k, v)
        ergebnis.append(teil)
    return ergebnis


Starter = Callable[[Sequence[str]], Awaitable[None]]


async def _starte_prozess(kommando: Sequence[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *kommando, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        rc = await asyncio.wait_for(proc.wait(), TON_MAX_S)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        await proc.wait()
        logge("sounds", "WARNING", "ton", "zeitueberschreitung", daten={"kommando": kommando[0]})
        return
    if rc != 0:
        logge("sounds", "WARNING", "ton", "kommando_fehler", daten={"kommando": kommando[0], "rc": rc})


class Toene:
    """Führt ``TonSpielen`` aus. Spielt im Hintergrund; blockiert nie."""

    def __init__(
        self,
        ordner: str | Path,
        kommando: Sequence[str],
        *,
        starter: Starter | None = None,
        kennlinie: Kennlinie = MPD_SOFTWARE,
    ) -> None:
        self.ordner = Path(ordner)
        self.kommando = tuple(kommando)
        self.kennlinie = kennlinie
        self._starter = starter or _starte_prozess
        self._aufgaben: set[asyncio.Task] = set()
        self._temp: set[Path] = set()

    def datei(self, ton: str) -> Path:
        """Tondatei; fehlt ein Prüfpunkt-Ton, die Datei des allgemeinen Tons (``pruef_ok``/``pruef_fehler``)."""
        d = self.ordner / f"{ton}.wav"
        m = _PRUEF_PUNKT.match(ton)
        if m and not d.is_file():
            return self.ordner / f"{'pruef_fehler' if m.group(1) == 'fehler' else 'pruef_ok'}.wav"
        return d

    def kommando_fuer(
        self, ton: str, grenze: int, lautstaerke: int | None = None, hinweis_pegel: int | None = None
    ) -> list[str] | None:
        """Das fertige Kommando, oder ``None`` ohne Datei."""
        d = self.datei(ton)
        if not d.is_file():
            logge("sounds", "WARNING", "ton", "datei_fehlt", daten={"ton": ton, "datei": str(d)})
            return None
        p = pegel(ton, grenze, lautstaerke, hinweis_pegel)
        fd, name = tempfile.mkstemp(prefix=f"tobibox-ton-{ton}-", suffix=".wav")
        os.close(fd)
        tmp = Path(name)
        try:
            skaliere_wav(d, p, tmp, self.kennlinie)
        except (ValueError, wave.Error, EOFError, OSError) as e:
            tmp.unlink(missing_ok=True)
            logge("sounds", "WARNING", "ton", "nicht_skalierbar", daten={"ton": ton, "detail": str(e)})
            return None  # lieber still als unbegrenzt laut
        self._temp.add(tmp)
        return baue_kommando(self.kommando, tmp, p)

    def _aufraeumen(self, kommando: Sequence[str]) -> None:
        for tmp in list(self._temp):
            if str(tmp) in kommando:
                tmp.unlink(missing_ok=True)
                self._temp.discard(tmp)

    def spiele(self, ton: str, grenze: int, lautstaerke: int | None = None, hinweis_pegel: int | None = None) -> bool:
        """Ton starten (Hintergrundaufgabe). ``False``, wenn nichts gestartet wurde."""
        k = self.kommando_fuer(ton, grenze, lautstaerke, hinweis_pegel)
        if k is None:
            return False
        t = asyncio.get_running_loop().create_task(self._lauf(ton, k), name=f"tobibox-ton-{ton}")
        self._aufgaben.add(t)
        t.add_done_callback(self._aufgaben.discard)
        return True

    def spiele_folge(
        self, toene: Sequence[str], grenze: int, lautstaerke: int | None = None, hinweis_pegel: int | None = None
    ) -> bool:
        """Töne nacheinander spielen (Status-Karte: ein Ton je Prüfpunkt). ``False`` bei leerer Folge."""
        if not toene:
            return False
        t = asyncio.get_running_loop().create_task(
            self._folge(tuple(toene), grenze, lautstaerke, hinweis_pegel), name="tobibox-ton-folge"
        )
        self._aufgaben.add(t)
        t.add_done_callback(self._aufgaben.discard)
        return True

    async def _folge(self, toene: Sequence[str], grenze: int, lautstaerke: int | None, hinweis_pegel: int | None) -> None:
        for ton in toene:
            k = self.kommando_fuer(ton, grenze, lautstaerke, hinweis_pegel)
            if k is not None:
                await self._lauf(ton, k)

    async def _lauf(self, ton: str, kommando: list[str]) -> None:
        try:
            await self._starter(kommando)
            logge("sounds", "DEBUG", "ton", "gespielt", daten={"ton": ton, "kommando": kommando[0]})
        except FileNotFoundError:
            logge("sounds", "WARNING", "ton", "programm_fehlt", daten={"ton": ton, "kommando": kommando[0]})
        except OSError as e:
            logge("sounds", "WARNING", "ton", "start_fehler", daten={"ton": ton, "detail": str(e)})
        finally:
            self._aufraeumen(kommando)

    async def warte(self) -> None:
        """Auf laufende Töne warten (Tests, sauberes Beenden)."""
        if self._aufgaben:
            await asyncio.gather(*list(self._aufgaben), return_exceptions=True)

    async def stop(self) -> None:
        for t in list(self._aufgaben):
            t.cancel()
        await self.warte()
        for tmp in list(self._temp):
            tmp.unlink(missing_ok=True)
        self._temp.clear()
