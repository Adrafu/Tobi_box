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
nie über der wirksamen Grenze und nie unter der Untergrenze 10, solange diese unter der Grenze liegt;
``hinweis``: ``min(grenze, max(HINWEIS_MINDEST, min(hinweis_pegel, lautstaerke)))`` (Vorgabe 15, Untergrenze 10).
Die Grenze ist für alle Töne der letzte Schritt: sie gewinnt immer (Gehörschutz). Den Pegel berechnet die Tonspur
erst, wenn der Ton wirklich an der Reihe ist (``pegel_quelle``), nicht beim Einreihen. Ohne Tondatei, oder
wenn die Datei kein 16-Bit-PCM ist (nicht sicher skalierbar), wird nichts gestartet.

Töne nie gleichzeitig (Entscheidung L, 09.11.): Alle Töne laufen über **eine** Spur, einer nach dem
anderen. Die Dauer eines Tons ist das Ende des Abspielprogramms (``afplay``/``aplay``), keine Schätzung;
ein hängendes Programm wird nach ``TON_MAX_S`` beendet. ``beschaeftigt`` und ``warte_leer`` zeigen, ob
noch ein Ton läuft; ``app.py`` startet das Hörspiel erst danach. Die Haken ``vor`` und ``nach`` rufen den
Anfang und das Ende einer zusammenhängenden Tonfolge auf (``app.py`` pausiert dort ein laufendes Hörspiel
und setzt es an derselben Stelle fort).

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
import time
import wave
from collections import deque
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import KENNLINIE_ALSA_SOFTVOL, KENNLINIE_MPD_SOFTWARE, STANDARD_SOFTVOL_BEREICH_DB
from .eventlog import logge

TON_MINDEST = 10  # Untergrenze der Ton-Lautstärke in Prozent: ein Ton bleibt hörbar (Entscheidung J)
HINWEIS_PEGEL_VORGABE = 15
HINWEIS_MINDEST = 10  # unter „stumm“ (Lautstärke 0) bleibt der Hinweiston hörbar; wie TON_MINDEST
TON_MAX_S = 10.0  # ein hängendes Abspielprogramm wird danach beendet; die Wiedergabe wartet nie länger auf einen Ton
FOLGE_PAUSE_S = 0.15  # Stille zwischen zwei Tönen einer Tonfolge (in der einen Datei, kein Prozess dazwischen)
_PRUEF_PUNKT = re.compile(r"^pruef_[a-z]+_(ok|simulation|fehler)$")


def pegel(ton: str, grenze: int, lautstaerke: int | None = None, hinweis_pegel: int | None = None) -> int:
    """Pegel in Prozent (0 bis 100) auf der Skala der MPD-Lautstärke.

    ``lautstaerke`` ist die aktuelle Lautstärke der Sitzung (zuletzt mit ``LautstaerkeSetzen`` ausgegeben),
    ``grenze`` die wirksame Grenze. Ohne ``lautstaerke`` gilt die Grenze.
    """
    grenze = max(0, min(100, int(grenze)))
    laut = grenze if lautstaerke is None else max(0, min(100, int(lautstaerke), grenze))
    if ton == "hinweis":
        h = HINWEIS_PEGEL_VORGABE if hinweis_pegel is None else hinweis_pegel
        return min(grenze, max(HINWEIS_MINDEST, min(h, laut)))  # die Grenze gewinnt immer (Gehörschutz, B7)
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


def lies_skaliert(quelle: Path, pegel_prozent: int, kennlinie: Kennlinie = MPD_SOFTWARE) -> tuple[wave._wave_params, array.array]:
    """16-Bit-PCM-WAV lesen und auf den Pegel ``pegel_prozent`` (0 bis 100) nach ``kennlinie`` herunterskalieren.

    Gibt Kopfdaten und Samples (Maschinenreihenfolge) zurück. Wirft ``ValueError``, wenn die Datei kein
    16-Bit-PCM ist.
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
    return params, array.array("h", (max(-32768, min(32767, round(x * faktor))) for x in samples))


def schreibe_samples(ziel: Path, params: wave._wave_params, samples: array.array) -> None:
    if sys.byteorder == "big":
        samples = array.array("h", samples)
        samples.byteswap()
    with wave.open(str(ziel), "wb") as w:
        w.setparams(params)
        w.writeframes(samples.tobytes())


def skaliere_wav(quelle: Path, pegel_prozent: int, ziel: Path, kennlinie: Kennlinie = MPD_SOFTWARE) -> None:
    """16-Bit-PCM-WAV auf den Pegel ``pegel_prozent`` (0 bis 100) nach ``kennlinie`` herunterskalieren.

    Schreibt das Ergebnis nach ``ziel``. Wirft ``ValueError``, wenn die Datei kein 16-Bit-PCM ist.
    """
    params, leise = lies_skaliert(quelle, pegel_prozent, kennlinie)
    schreibe_samples(ziel, params, leise)


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
    """Abspielprogramm starten und bis zu seinem Ende warten. Die Zeitgrenze setzt der Aufrufer.

    Wird die Aufgabe abgebrochen (Zeitgrenze, Beenden), wird auch das Programm beendet.
    """
    proc = await asyncio.create_subprocess_exec(
        *kommando, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        rc = await proc.wait()
    except BaseException:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        with contextlib.suppress(Exception):
            await asyncio.shield(proc.wait())
        raise
    if rc != 0:
        logge("sounds", "WARNING", "ton", "kommando_fehler", daten={"kommando": kommando[0], "rc": rc})


Haken = Callable[[], Awaitable[None]]
# liefert (grenze, lautstaerke, hinweis_pegel); wird erst aufgerufen, wenn ein Ton an der Reihe ist
Pegelquelle = Callable[[], tuple[int, int | None, int | None]]
_Werte = tuple[int, int | None, int | None]


class Toene:
    """Führt ``TonSpielen`` aus. Eine Spur: Töne laufen nacheinander, nie gleichzeitig (Entscheidung L).

    ``spiele`` und ``spiele_folge`` reihen ein und kehren sofort zurück; ein Arbeiter spielt die Töne
    der Reihe nach, jeden bis zum Ende seines Prozesses (höchstens ``ton_max_s``).
    """

    def __init__(
        self,
        ordner: str | Path,
        kommando: Sequence[str],
        *,
        starter: Starter | None = None,
        kennlinie: Kennlinie = MPD_SOFTWARE,
        vor: Haken | None = None,
        nach: Haken | None = None,
        ton_max_s: float | None = None,
        pegel_quelle: Pegelquelle | None = None,
    ) -> None:
        self.ordner = Path(ordner)
        self.kommando = tuple(kommando)
        self.kennlinie = kennlinie
        self.ton_max_s = TON_MAX_S if ton_max_s is None else ton_max_s
        self._starter = starter or _starte_prozess
        self._vor = vor
        self._nach = nach
        self._pegel_quelle = pegel_quelle
        # je Aufruf von ``spiele`` / ``spiele_folge`` eine Gruppe aus (Ton, feste Pegel-Werte oder ``None`` für die Quelle)
        self._eintraege: deque[list[tuple[str, _Werte | None]]] = deque()
        self._arbeiter: asyncio.Task | None = None
        self._leer = asyncio.Event()
        self._leer.set()
        self._beendet = False
        self._temp: set[Path] = set()

    @property
    def beschaeftigt(self) -> bool:
        """``True``, solange ein Ton läuft oder wartet."""
        return bool(self._eintraege) or self._arbeiter is not None

    @property
    def folge_wartet(self) -> bool:
        """``True``, wenn noch ein Ton eingereiht ist, der nicht läuft (dann endet die Tonfolge noch nicht)."""
        return bool(self._eintraege)

    def datei(self, ton: str) -> Path:
        """Tondatei; fehlt ein Prüfpunkt-Ton, die Datei des allgemeinen Tons (``pruef_ok``/``pruef_fehler``)."""
        d = self.ordner / f"{ton}.wav"
        m = _PRUEF_PUNKT.match(ton)
        if m and not d.is_file():
            return self.ordner / f"{'pruef_fehler' if m.group(1) == 'fehler' else 'pruef_ok'}.wav"
        return d

    def _brauchbar(self, ton: str) -> bool:
        """Gibt es die Datei und ist sie 16-Bit-PCM? Sonst wird der Ton gar nicht erst eingereiht."""
        d = self.datei(ton)
        if not d.is_file():
            logge("sounds", "WARNING", "ton", "datei_fehlt", daten={"ton": ton, "datei": str(d)})
            return False
        try:
            with wave.open(str(d), "rb") as r:
                if r.getsampwidth() != 2 or r.getcomptype() != "NONE":
                    raise ValueError("nur 16-Bit-PCM wird unterstützt")
        except (ValueError, wave.Error, EOFError, OSError) as e:
            logge("sounds", "WARNING", "ton", "nicht_skalierbar", daten={"ton": ton, "detail": str(e)})
            return False
        return True

    def kommando_fuer(
        self, ton: str, grenze: int, lautstaerke: int | None = None, hinweis_pegel: int | None = None
    ) -> list[str] | None:
        """Das fertige Kommando für einen einzelnen Ton, oder ``None`` ohne Datei (Prüfung und Tests)."""
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

    def _reihe_ein(self, gruppe: list[tuple[str, _Werte | None]]) -> None:
        self._eintraege.append(gruppe)
        self._leer.clear()
        if self._arbeiter is None:
            self._arbeiter = asyncio.get_running_loop().create_task(self._arbeit(), name="tobibox-ton-spur")

    @staticmethod
    def _werte(grenze: int | None, lautstaerke: int | None, hinweis_pegel: int | None) -> _Werte | None:
        return None if grenze is None else (grenze, lautstaerke, hinweis_pegel)

    def spiele(
        self, ton: str, grenze: int | None = None, lautstaerke: int | None = None, hinweis_pegel: int | None = None
    ) -> bool:
        """Ton einreihen (spielt nach allen früheren Tönen). ``False``, wenn nichts eingereiht wurde.

        Ohne ``grenze`` holt die Spur Grenze und Lautstärke erst beim Abspielen aus der ``pegel_quelle`` (B6).
        """
        if not self._brauchbar(ton):
            return False
        self._reihe_ein([(ton, self._werte(grenze, lautstaerke, hinweis_pegel))])
        return True

    def spiele_folge(
        self,
        toene: Sequence[str],
        grenze: int | None = None,
        lautstaerke: int | None = None,
        hinweis_pegel: int | None = None,
    ) -> bool:
        """Töne einer Folge einreihen (Status-Karte: ein Ton je Prüfpunkt). ``False`` bei leerer Folge.

        Die Töne einer Folge werden zu **einer** Datei mit ``FOLGE_PAUSE_S`` Stille dazwischen zusammengefügt
        und von **einem** Abspielprogramm gespielt: Zwischen den Ansagen liegt so kein Prozessstart.
        """
        if not toene:
            return False
        werte = self._werte(grenze, lautstaerke, hinweis_pegel)
        eintraege = [(ton, werte) for ton in toene if self._brauchbar(ton)]  # eine fehlende Datei stoppt die Folge nicht
        if eintraege:
            self._reihe_ein(eintraege)
        return True

    async def _haken(self, haken: Haken | None, name: str) -> None:
        if haken is None or self._beendet:
            return
        try:
            await haken()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # ein Fehler des Hakens darf die Tonspur nicht anhalten
            logge("sounds", "WARNING", "ton", "haken_fehler", daten={"haken": name, "detail": repr(e)})

    async def _arbeit(self) -> None:
        try:
            while self._eintraege:
                await self._haken(self._vor, "vor")
                try:
                    while self._eintraege:
                        await self._lauf(self._eintraege.popleft())
                finally:
                    await self._haken(self._nach, "nach")  # das Ende der Tonfolge kommt in jedem Fall (B3)
        finally:
            self._arbeiter = None
            if self._beendet or self._eintraege:
                # beim Beenden, oder wenn die Spur unerwartet endet: nichts liegen lassen, sonst bliebe
                # ``beschaeftigt`` wahr und ``warte_leer`` hinge ohne Ende
                self._eintraege.clear()
            self._leer.set()  # erst hier, und nur bei wirklich leerer Spur

    def _baue_folge(self, gruppe: list[tuple[str, _Werte | None]]) -> list[tuple[list[str], Path, int]]:
        """Die Töne einer Gruppe skalieren und zu je einer Datei zusammenfügen.

        Gibt je Datei (Kommando, Datei, Anzahl der Töne) zurück. Töne mit anderem Format (Rate, Kanäle) können
        nicht in dieselbe Datei und bilden eine eigene; im Normalfall ist es genau eine Datei. Der Pegel jedes
        Tons entsteht jetzt (B6), mit den festen Werten des Tons oder aus der ``pegel_quelle``.
        """
        quelle: _Werte | None = None
        teile: list[tuple[str, wave._wave_params, array.array, int]] = []
        for ton, werte in gruppe:
            if werte is None:
                if quelle is None:
                    quelle = self._pegel_quelle() if self._pegel_quelle is not None else (100, None, None)
                werte = quelle
            d = self.datei(ton)
            if not d.is_file():
                logge("sounds", "WARNING", "ton", "datei_fehlt", daten={"ton": ton, "datei": str(d)})
                continue
            p = pegel(ton, *werte)
            try:
                params, samples = lies_skaliert(d, p, self.kennlinie)
            except (ValueError, wave.Error, EOFError, OSError) as e:
                logge("sounds", "WARNING", "ton", "nicht_skalierbar", daten={"ton": ton, "detail": str(e)})
                continue  # lieber still als unbegrenzt laut
            teile.append((ton, params, samples, p))
        laeufe: list[list[tuple[str, wave._wave_params, array.array, int]]] = []
        for t in teile:
            if laeufe and laeufe[-1][0][1][:3] == t[1][:3]:
                laeufe[-1].append(t)
            else:
                laeufe.append([t])
        dateien: list[tuple[list[str], Path, int]] = []
        for lauf in laeufe:
            params = lauf[0][1]
            luecke = array.array("h", bytes(2 * params.nchannels * int(round(params.framerate * FOLGE_PAUSE_S))))
            gesamt = array.array("h")
            for i, (_ton, _params, samples, _p) in enumerate(lauf):
                if i:
                    gesamt.extend(luecke)
                gesamt.extend(samples)
            fd, name = tempfile.mkstemp(prefix=f"tobibox-ton-{lauf[0][0]}-", suffix=".wav")
            os.close(fd)
            tmp = Path(name)
            self._temp.add(tmp)
            schreibe_samples(tmp, params, gesamt)
            dateien.append((baue_kommando(self.kommando, tmp, lauf[0][3]), tmp, len(lauf)))
        return dateien

    async def _lauf(self, gruppe: list[tuple[str, _Werte | None]]) -> None:
        """Eine Tonfolge spielen: ein Prozess für alle Töne (Zeitlimit: ``ton_max_s`` je Ton der Folge)."""
        namen = "+".join(t for t, _ in gruppe)
        dateien: list[tuple[list[str], Path, int]] = []
        try:
            dateien = self._baue_folge(gruppe)
        except Exception as e:  # was auch kommt: die Tonspur darf nicht sterben (CancelledError läuft durch)
            logge("sounds", "WARNING", "ton", "unerwartet", daten={"ton": namen, "detail": repr(e)})
        try:
            for kommando, _tmp, anzahl in dateien:
                await self._spiele_datei(namen, kommando, anzahl)
        finally:
            for kommando, _tmp, _anzahl in dateien:
                self._aufraeumen(kommando)

    async def _spiele_datei(self, namen: str, kommando: list[str], anzahl: int) -> None:
        try:
            t0 = time.monotonic()
            await asyncio.wait_for(self._starter(kommando), self.ton_max_s * anzahl)
            logge("sounds", "DEBUG", "ton", "gespielt",
                  daten={"ton": namen, "kommando": kommando[0], "prozess_ms": round((time.monotonic() - t0) * 1000)})
        except asyncio.TimeoutError:
            logge("sounds", "WARNING", "ton", "zeitueberschreitung", daten={"ton": namen, "kommando": kommando[0]})
        except FileNotFoundError:
            logge("sounds", "WARNING", "ton", "programm_fehlt", daten={"ton": namen, "kommando": kommando[0]})
        except OSError as e:
            logge("sounds", "WARNING", "ton", "start_fehler", daten={"ton": namen, "detail": str(e)})
        except Exception as e:  # was auch kommt: die Tonspur darf nicht sterben (CancelledError läuft durch)
            logge("sounds", "WARNING", "ton", "unerwartet", daten={"ton": namen, "detail": repr(e)})

    async def warte_leer(self) -> None:
        """Warten, bis kein Ton mehr läuft oder wartet (auch nicht einer, der unterdessen dazukam)."""
        while self.beschaeftigt:
            await self._leer.wait()
            if self.beschaeftigt:
                await asyncio.sleep(0.01)  # nie den Event-Loop festhalten, auch bei gesetztem ``_leer`` (B3)

    async def warte(self) -> None:
        """Auf laufende Töne warten (Tests, sauberes Beenden)."""
        await self.warte_leer()

    async def stop(self) -> None:
        self._beendet = True  # keine Haken mehr: nach dem Beenden darf nichts weiterspielen
        a = self._arbeiter
        if a is not None:
            a.cancel()
            await asyncio.gather(a, return_exceptions=True)
        self._eintraege.clear()
        for tmp in list(self._temp):
            tmp.unlink(missing_ok=True)
        self._temp.clear()
