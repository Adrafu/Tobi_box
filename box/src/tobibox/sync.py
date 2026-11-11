"""Medien-Sync: rsync vom QNAP auf die Box (Design „Netz, Sync, Strom“, AP 3.4; CUJ 9 und 12).

Aufbau wie ``outbox.py`` und ``sounds.py``: eine async-Klasse ``Sync``, die nichts importiert, was
Netz, Strom oder MPD besitzt. Netz-Klasse, Laderstand und Akku bekommt sie als Eingabe
(``setze_netz``, ``setze_lader``, ``setze_akku``), die spielende Datei und das Neueinlesen von MPD über
zwei Haken. Die Ereignisse gehen über den Haken ``ausgabe``. Verdrahtet wird sie erst in AP 3.7.

Ablauf eines Syncs:

1. Regel: ``home`` immer; ``hotspot`` nur am Lader oder bei Akku über 50 %; ``offline`` nie. Sonst
   ``SyncAbgebrochen("regel")`` (ohne ``SyncGestartet``). Im Hotspot gibt es kein Datenlimit (Entscheidung C).
2. ``SyncGestartet``. Quelle prüfen (``--list-only``): fehlt sie, ``quelle_fehlt``; ist sie leer, ``quelle_leer``.
3. Trockenlauf (``--dry-run --itemize-changes --stats``): Zeilen ``*deleting`` zählen. Mehr als 20 % der
   vorhandenen Dateien: ``zu_viele_loeschungen``. Reicht der freie Platz (übertragene Größe plus Reserve) nicht:
   ``kein_platz``.
4. Echter Lauf mit ``--delete``, ``--partial-dir`` und ``--temp-dir`` (absolut, außerhalb des Medienordners, gleiches
   Dateisystem). rsync schreibt eine Datei sonst zuerst als ``.name.XXXXXX`` in den Zielordner; ``--temp-dir`` verhindert das.
   Halbe Dateien liegen nur außerhalb, MPD sieht sie nie; jede Datei wird erst fertig an ihren Platz umbenannt (atomar).
   **Kein ``--delay-updates``** (AP 3.7, Fund aus CUJ 9): Mit einem absoluten ``--partial-dir`` hält rsync die zurückgestellten
   Dateien flach unter ihrem Dateinamen. Zwei Serien mit je einer ``serie.json`` stoßen dort zusammen, der Sync bricht mit
   ``rsync_fehler`` ab. Ein relatives ``--partial-dir`` (in jedem Ordner) wäre dafür sicher, läge aber im Medienordner, wo MPD
   es sehen könnte. Ohne ``--delay-updates`` ist je Datei höchstens eine halbe Datei unterwegs, und zwar außerhalb.
   Die gerade spielende Datei (MPD ``currentsong``) ist per ``--exclude`` ausgenommen; das schützt sie auch
   vor ``--delete``. Ihre Änderung wartet auf den nächsten Abgleich.
5. MPD neu einlesen lassen (nicht beim Start), dann ``SyncFertig``.

Lautheit (Entscheidung J, 09.11.): Testmedien und Hörspiele tragen ReplayGain-Tags. Der Sync überträgt die
Dateien unverändert. Es gibt keine Neuberechnung auf der Box, denn ``rsgain`` läuft auf dem NAS. Darum
verändert der Sync nie Tags und verlangt keine Prüfsummen-Umgehung wie ``--checksum``.

Das Passwort steht nie in der Befehlszeile: ``--password-file`` (Pfad) oder die Umgebungsvariable
``RSYNC_PASSWORD`` nur für den Kindprozess. Das Protokoll enthält keine Passwörter.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import os
import re
import shutil
import signal
import subprocess
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import events as ev
from .config import SyncKonfig
from .eventlog import logge
from .syncregel import HOTSPOT_AKKU_MIN_PROZENT, sync_erlaubt

#: Im Hotspot ist der Sync erlaubt, wenn der Akku über dieser Grenze liegt (oder ein Lader dran ist). Eine Quelle: ``syncregel``.
AKKU_GRENZE_HOTSPOT = HOTSPOT_AKKU_MIN_PROZENT
#: Mehr als dieser Anteil an Löschungen (in Prozent der vorhandenen Dateien) bricht den Sync ab.
MAX_LOESCHEN_PROZENT = 20
IO_TIMEOUT_S = 60  # rsync ``--timeout``: so lange darf keine Daten fließen
VERBINDUNG_TIMEOUT_S = 15  # rsync ``--contimeout``
ABBRUCH_WARTEN_S = 10.0  # nach SIGTERM so lange warten, dann SIGKILL
FORTSCHRITT_ABSTAND_S = 1.0
MPD_EINLESEN_MAX_S = 300.0

#: Dinge, die der QNAP selbst anlegt und die nie auf die Box gehören.
def _ohne_gross_klein(name: str) -> str:
    """rsync kennt kein ``--ignore-case`` für Muster: Buchstaben als ``[Aa]`` schreiben."""
    return "".join(f"[{c.upper()}{c.lower()}]" if c.isalpha() else c for c in name)


#: Systemdateien und -ordner (11.11.): AppleDouble ``._*``, ``.DS_Store``, ``@eaDir``/``@Recycle``/``@…`` (QNAP/Synology),
#: ``.@__thumb``, ``.@__qini``, ``#recycle``, Windows ``Thumbs.db``, ``desktop.ini``, ``$RECYCLE.BIN``. Ohne Rücksicht auf
#: Groß-/Kleinschreibung, an jeder Tiefe. ``--exclude`` schützt sie auch vor ``--delete``: Liegt so etwas lokal, bleibt es.
AUSSCHLUESSE = (
    "@*",
    "._*",
    ".@__*",
    *(_ohne_gross_klein(n) for n in ("#recycle", "$RECYCLE.BIN", ".DS_Store", "Thumbs.db", "desktop.ini")),
)

#: Ordner der HA-Medienverwaltung, die nie auf die Box gehören (Entscheidung M6, 09.11.): Upload-Zwischenablage, Papierkorb
#: und Eingang. Am Anfang der **Quelle** verankert (11.11.): rsync verankert ein ``/`` am Anfang an dem Ordner, der als Quelle
#: angegeben ist (URL mit Schrägstrich am Ende). Mit ``[sync] pfad`` ist das ``…/{modul}/{pfad}/``, nicht das Modul. ``--exclude`` schützt sie auch vor ``--delete``: Was die Box davon hätte, bleibt.
NIE_AUF_DIE_BOX = ("/_upload", "/_papierkorb", "/eingang")

#: rsync-Rückgabewerte, die auf ein weggefallenes Netz hindeuten (Socket, Datenstrom, Timeout, Verbindungs-Timeout).
_NETZ_CODES = {10, 12, 30, 35}
_VANISHED = 24  # Quelldatei verschwand während des Laufs: kein Fehler

_ITEM = re.compile(r"^([<>ch.*])([fdLDS])[^ ]{9} ")
_LOESCHEN = re.compile(r"^\*deleting\s+(.*)$")
_PROZENT = re.compile(r"\s(\d{1,3})%\s")
_GROESSE = re.compile(r"Total transferred file size:\s*([\d.,]+)")

Ausgabe = Callable[[ev.Ereignis], "Awaitable[None] | None"]
AktuelleDatei = Callable[[], Awaitable["str | None"]]
Einlesen = Callable[[], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class SyncFortschritt(ev.Ereignis):
    """Zwischenstand eines laufenden Syncs (Lücke im Vertrag: ``core-interface.md`` kennt kein solches Ereignis).

    ``prozent`` ist der Gesamtfortschritt laut rsync (0 bis 100), ``dateien`` die bisher übertragenen Dateien.
    """

    prozent: int
    dateien: int


def regel_erlaubt(klasse: str | None, am_lader: bool | None, akku: int | None) -> bool:
    """Netz-Regel: ``home`` immer; ``hotspot`` am Lader oder bei Akku über 50 %; sonst nie. Die Regel steht in ``syncregel``."""
    return sync_erlaubt(klasse, am_lader, akku)[0]


def zu_viele_loeschungen(geloescht: int, vorhanden: int) -> bool:
    """Mehr als 20 % der vorhandenen Dateien (genau 20 % ist noch erlaubt; ganzzahlig gerechnet)."""
    return geloescht * 100 > vorhanden * MAX_LOESCHEN_PROZENT


#: Optionen, mit denen rsync auf der Quelle etwas löschen oder verändern würde (das gemeinsame Konto am QNAP darf schreiben).
_SCHREIBENDE_OPTIONEN = ("--remove-source-files", "--remove-sent-files", "--del-source", "--delete-source")


def pruefe_nur_lesend(cmd: Sequence[str]) -> None:
    """Die Box benutzt rsync nur zum Abholen (11.11.): Quelle ist immer der Server, Ziel immer ein lokaler Pfad.

    Das Konto am QNAP darf schreiben; dieser Schutz sorgt dafür, dass die Box es nie tut. ``--delete`` wirkt nur
    auf das Ziel, also lokal. Verstöße sind Programmfehler (``ValueError``), nie Laufzeitfehler des Netzes."""
    args = list(cmd)
    for a in args:
        if a.split("=", 1)[0] in _SCHREIBENDE_OPTIONEN:
            raise ValueError(f"rsync darf nie auf dem Server schreiben oder löschen: {a}")
    orte = [a for a in args if a.startswith("rsync://")]
    if len(orte) != 1:
        raise ValueError("rsync braucht genau eine Server-Quelle")
    i = args.index(orte[0])
    if i != len(args) - 1 and i != len(args) - 2:
        raise ValueError("die Server-Adresse muss die Quelle sein (vor dem Ziel)")
    ziel = args[i + 1 :]
    if not ziel and "--list-only" not in args:
        raise ValueError("der Server steht am Ende: das wäre ein Ziel (nur ``--list-only`` hat kein lokales Ziel)")
    if len(ziel) > 1:
        raise ValueError("höchstens ein Ziel nach der Quelle")
    if ziel and (ziel[0].startswith("rsync://") or ":" in ziel[0].split("/", 1)[0] or not ziel[0].startswith("/")):
        raise ValueError(f"das Ziel muss ein lokaler absoluter Pfad sein: {ziel[0]}")


class RsyncUngeeignet(Exception):
    """Das gefundene rsync ist zu alt oder Apples openrsync (Protokoll 29): der Sync liefe nicht."""


_PROTOKOLL = re.compile(r"protocol version\s+(\d+)")


def pruefe_rsync_ausgabe(ausgabe: str, rsync: str = "rsync") -> None:
    """Prüft die Ausgabe von ``rsync --version``: openrsync oder Protokoll unter 30 (rsync vor 3.0) lehnt der Dienst ab."""
    text = ausgabe.lower()
    m = _PROTOKOLL.search(ausgabe)
    protokoll = int(m.group(1)) if m else None
    if "openrsync" in text or protokoll is None or protokoll < 30:
        raise RsyncUngeeignet(
            f"rsync zu alt bzw. openrsync (Apples rsync, Protokoll 29): '{rsync}' taugt nicht für den Sync. "
            "Bitte `brew install rsync` und in [sync] rsync = \"/opt/homebrew/bin/rsync\" eintragen."
        )


def pruefe_rsync(rsync: str = "rsync") -> None:
    """Beim Start: ``rsync --version`` fragen und prüfen. Fehlt das Programm, ist das ebenfalls ein klarer Fehler."""
    try:
        r = subprocess.run([rsync, "--version"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RsyncUngeeignet(f"rsync nicht ausführbar ('{rsync}': {e}). Auf dem Mac: `brew install rsync` und [sync] rsync setzen.") from e
    pruefe_rsync_ausgabe(r.stdout + r.stderr, rsync)


def _maskiere(pfad: str) -> str:
    """Muster für ``--exclude``: Platzhalter im Dateinamen ausschalten."""
    return re.sub(r"([*?\[\\])", r"\\\1", pfad)


class _Abbruch(Exception):
    def __init__(self, grund: str, detail: str | None = None) -> None:
        super().__init__(grund)
        self.grund = grund
        self.detail = detail


class Sync:
    """Ein Sync auf einmal. ``start`` läuft im Hintergrund, ``abbrechen`` beendet ihn, Ergebnisse als Ereignisse."""

    def __init__(
        self,
        konfig: SyncKonfig,
        medien: str | Path,
        *,
        ausgabe: Ausgabe,
        aktuelle_datei: AktuelleDatei | None = None,
        einlesen: Einlesen | None = None,
        partial_dir: str | Path | None = None,
        rsync: str = "rsync",
        zusatz: Sequence[str] = (),
        freier_platz: Callable[[Path], int] | None = None,
        mono: Callable[[], float] = time.monotonic,
        umgebung: dict[str, str] | None = None,
    ) -> None:
        self.konfig = konfig
        self.medien = Path(medien).absolute()
        part = partial_dir or konfig.partial_dir or self.medien.parent / ".rsync-partial"
        self.partial_dir = Path(part).absolute()
        #: rsync schreibt eine Datei zuerst als ``.name.XXXXXX`` neben das Ziel. Damit auch das nie im
        #: Medienordner liegt, zeigt ``--temp-dir`` neben den Partial-Ordner (gleiches Dateisystem).
        self.temp_dir = self.partial_dir.parent / ".rsync-tmp"
        if self.partial_dir == self.medien or self.medien in self.partial_dir.parents:
            raise ValueError("partial_dir muss außerhalb des Medienordners liegen")
        if self.temp_dir == self.medien or self.medien in self.temp_dir.parents:
            raise ValueError("der Ordner für rsync-Zwischendateien muss außerhalb des Medienordners liegen")
        self._ausgabe = ausgabe
        self._aktuelle_datei = aktuelle_datei
        self._einlesen = einlesen
        self._rsync = rsync
        self._zusatz = tuple(zusatz)  # nur für Tests (z. B. ``--bwlimit``)
        self._freier_platz = freier_platz or (lambda p: shutil.disk_usage(p).free)
        self._mono = mono
        self._umgebung = umgebung  # None: ``os.environ`` beim Start
        self._netz: str | None = None
        self._am_lader: bool | None = None  # unbekannt, bis ``setze_lader`` es sagt
        self._akku: int | None = None
        self._aufgabe: asyncio.Task | None = None
        self._prozess: asyncio.subprocess.Process | None = None
        self._abbruch_grund: str | None = None
        self._zuletzt = mono()
        self.letzter_start: float | None = None

    # --- Eingaben ---------------------------------------------------------------------------------

    def setze_netz(self, klasse: str) -> None:
        """``home``, ``hotspot`` oder ``offline``. Fällt das Netz während des Syncs weg, bricht er ab.

        Kommt die Box neu in ein Netz, in dem ein Sync erlaubt ist (CUJ 12: heim oder in den Hotspot), gilt das Intervall des
        Takts nicht mehr: Der nächste ``takt`` startet sofort einen Sync, auch nach einem Abbruch durch den Netzverlust."""
        war_erlaubt = self.erlaubt()
        self._netz = klasse
        if klasse == "offline" and self.laeuft:
            self._abbrechen_anfordern("netz_weg")
        if not war_erlaubt and self.erlaubt():
            self.letzter_start = None

    def setze_lader(self, am_lader: bool) -> None:
        """Lader dran oder weg. Ein neu angeschlossener Lader macht im Hotspot einen Sync möglich (wie bei ``setze_netz``)."""
        war_erlaubt = self.erlaubt()
        self._am_lader = am_lader
        if not war_erlaubt and self.erlaubt():
            self.letzter_start = None

    def setze_akku(self, prozent: int) -> None:
        self._akku = prozent

    @property
    def netz_bekannt(self) -> bool:
        """Hat ``setze_netz`` schon einmal eine Netz-Klasse gebracht? (Sonst wäre ``regel`` nur ein Mangel an Wissen, B7.)"""
        return self._netz is not None

    @property
    def laeuft(self) -> bool:
        """Für ``idle`` (keine Abschaltung) und das Update (Sperre): solange ein Sync läuft, ``True``."""
        return self._aufgabe is not None and not self._aufgabe.done()

    def erlaubt(self) -> bool:
        return regel_erlaubt(self._netz, self._am_lader, self._akku)

    # --- Steuerung --------------------------------------------------------------------------------

    async def start(self, grund: str = "ha") -> bool:
        """Sync anfordern (``SyncStarten``). ``False``, wenn schon einer läuft (dann kein Ereignis).

        Verbietet die Regel den Sync, kommt ``SyncAbgebrochen("regel")`` und die Antwort ist ``False``.
        """
        if self.laeuft:
            logge("sync", "INFO", "start", "laeuft_schon", daten={"grund": grund})
            return False
        if not self.erlaubt():
            logge("sync", "INFO", "start", "regel", daten={"netz": self._netz, "lader": self._am_lader, "akku": self._akku})
            await self._sende(ev.SyncAbgebrochen("regel"))
            return False
        self._abbruch_grund = None
        self.letzter_start = self._mono()
        self._aufgabe = asyncio.get_running_loop().create_task(self._lauf(grund), name="tobibox-sync")
        return True

    async def takt(self, intervall_s: float | None = None) -> bool:
        """Zeitgesteuerter Start: läuft nur, wenn das Intervall um ist und die Regel es erlaubt (sonst still)."""
        if self.laeuft or not self.erlaubt():
            return False
        abstand = self.konfig.intervall_s if intervall_s is None else intervall_s
        if self.letzter_start is not None and self._mono() - self.letzter_start < abstand:
            return False
        return await self.start("takt")

    async def abbrechen(self, grund: str = "akku_tiefstand") -> None:
        """Laufenden Sync beenden (``SyncAbbrechen``) und warten, bis rsync weg ist. Ohne Sync: nichts."""
        if not self.laeuft:
            return
        self._abbrechen_anfordern(grund)
        await self.warte_ende()

    async def warte_ende(self) -> None:
        if self._aufgabe is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.shield(self._aufgabe)

    async def beenden(self) -> None:
        """Beim Beenden des Dienstes: Sync abbrechen und aufräumen (kein Ereignis nötig, aber es kommt eines)."""
        await self.abbrechen("dienst_beendet")

    def _abbrechen_anfordern(self, grund: str) -> None:
        if self._abbruch_grund is None:
            self._abbruch_grund = grund
        p = self._prozess
        if p is not None and p.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                p.send_signal(signal.SIGTERM)

    # --- Ablauf -----------------------------------------------------------------------------------

    async def _sende(self, e: ev.Ereignis) -> None:
        try:
            r = self._ausgabe(e)
            if inspect.isawaitable(r):
                await r
        except Exception as fehler:  # ein kaputter Empfänger darf den Sync nicht kippen
            logge("sync", "ERROR", "ausgabe", "fehler", daten={"detail": repr(fehler)})

    async def _lauf(self, grund: str) -> None:
        await self._sende(ev.SyncGestartet())
        logge("sync", "INFO", "sync", "gestartet", daten={"grund": grund})
        try:
            neu, geloescht = await self._durchfuehren()
        except _Abbruch as a:
            g = self._abbruch_grund or a.grund
            logge("sync", "WARNING", "sync", "abgebrochen", daten={"grund": g, "detail": a.detail})
            await self._sende(ev.SyncAbgebrochen(g))
        except asyncio.CancelledError:
            await self._sende(ev.SyncAbgebrochen(self._abbruch_grund or "abgebrochen"))
            raise
        except Exception as fehler:
            logge("sync", "ERROR", "sync", "fehler", daten={"detail": repr(fehler)})
            await self._sende(ev.SyncAbgebrochen("rsync_fehler"))
        else:
            logge("sync", "INFO", "sync", "fertig", daten={"neu": neu, "geloescht": geloescht})
            await self._sende(ev.SyncFertig(neu, geloescht))
        finally:
            self._prozess = None
            self._zuletzt = self._mono()

    def _pruefe_abbruch(self) -> None:
        if self._abbruch_grund is not None:
            raise _Abbruch(self._abbruch_grund)

    async def _durchfuehren(self) -> tuple[int, int]:
        # Dateizugriffe in einem Thread: Ereignisschleife, Takt und Ring stehen sonst bei vielen Dateien (B10)
        await asyncio.to_thread(self._bereite_vor)

        # 1. Quelle prüfen
        code, aus, fehl = await self._rsync_lauf(self._basis(["--list-only", "-r"]), lies=True)
        self._pruefe_abbruch()
        if code != 0:
            raise _Abbruch(self._grund_aus_code(code, fehl), fehl[-300:])
        if not any(zeile.startswith("-") for zeile in aus):
            raise _Abbruch("quelle_leer")

        # 2. Trockenlauf: Löschungen und Größe
        ausnahmen = await self._spielende_ausnahmen()
        code, aus, fehl = await self._rsync_lauf(
            self._basis(["-i", "--stats", "--delete", "--dry-run"], ausnahmen), lies=True
        )
        self._pruefe_abbruch()
        if code not in (0, _VANISHED):
            raise _Abbruch(self._grund_aus_code(code, fehl), fehl[-300:])
        geplant_loeschen = 0
        for zeile in aus:
            m = _LOESCHEN.match(zeile)
            if m and not m.group(1).rstrip().endswith("/"):
                geplant_loeschen += 1
        vorhanden = await asyncio.to_thread(self._zaehle_dateien)
        if zu_viele_loeschungen(geplant_loeschen, vorhanden):
            raise _Abbruch("zu_viele_loeschungen", f"{geplant_loeschen} von {vorhanden}")
        bytes_noetig = 0
        for zeile in aus:
            m = _GROESSE.search(zeile)
            if m:
                bytes_noetig = int(re.sub(r"[.,]", "", m.group(1)))
        if self._freier_platz(self.medien) < bytes_noetig + self.konfig.reserve_mb * 1024 * 1024:
            raise _Abbruch("kein_platz", f"{bytes_noetig} Bytes nötig")

        # 3. Echter Lauf. Die spielende Datei kann sich seit dem Trockenlauf geändert haben: neu fragen.
        ausnahmen = sorted(set(ausnahmen) | set(await self._spielende_ausnahmen()))
        optionen = ["-i", "--info=progress2", "--delete", f"--partial-dir={self.partial_dir}", f"--temp-dir={self.temp_dir}"]
        neu = geloescht = 0
        letzte_meldung = self._mono() - FORTSCHRITT_ABSTAND_S
        letzte_prozent = -1

        async def zeile(z: str) -> None:
            nonlocal neu, geloescht, letzte_meldung, letzte_prozent
            if _LOESCHEN.match(z):
                if not z.rstrip().endswith("/"):
                    geloescht += 1
                return
            m = _ITEM.match(z)
            if m and m.group(1) == ">" and m.group(2) == "f":
                neu += 1
                return
            p = _PROZENT.search(z)
            if p:
                prozent = min(100, int(p.group(1)))
                jetzt = self._mono()
                if prozent != letzte_prozent and jetzt - letzte_meldung >= FORTSCHRITT_ABSTAND_S:
                    letzte_prozent, letzte_meldung = prozent, jetzt
                    await self._sende(SyncFortschritt(prozent, neu))

        code, _, fehl = await self._rsync_lauf(self._basis(optionen, ausnahmen), je_zeile=zeile)
        self._pruefe_abbruch()
        if code not in (0, _VANISHED):
            raise _Abbruch(self._grund_aus_code(code, fehl), fehl[-300:])

        # 4. MPD neu einlesen lassen (erst jetzt, nicht beim Start)
        if self._einlesen is not None:
            try:
                await self._einlesen()
            except Exception as fehler:  # Sync war erfolgreich; MPD liest beim nächsten Mal ein
                logge("sync", "WARNING", "mpd_einlesen", "fehler", daten={"detail": repr(fehler)})
        return neu, geloescht

    # --- Hilfen -----------------------------------------------------------------------------------

    def _bereite_vor(self) -> None:
        self.medien.mkdir(parents=True, exist_ok=True)
        self._bereite_partial_vor()

    def _bereite_partial_vor(self) -> None:
        for ordner in (self.partial_dir, self.temp_dir):
            ordner.mkdir(parents=True, exist_ok=True)
            if ordner.stat().st_dev != self.medien.stat().st_dev:
                raise _Abbruch("partial_dir_falsch", f"{ordner} liegt auf einem anderen Dateisystem als der Medienordner")

    def _zaehle_dateien(self) -> int:
        return sum(len(dateien) for _, _, dateien in os.walk(self.medien))

    async def _spielende_ausnahmen(self) -> list[str]:
        if self._aktuelle_datei is None:
            return []
        try:
            datei = await self._aktuelle_datei()
        except Exception as fehler:
            logge("sync", "WARNING", "currentsong", "fehler", daten={"detail": repr(fehler)})
            return []
        if not datei:
            return []
        rel = str(datei).lstrip("/")
        return ["/" + _maskiere(rel)]

    def _url(self) -> str:
        k = self.konfig
        wer = f"{k.benutzer}@" if k.benutzer else ""
        unter = f"{k.pfad}/" if k.pfad else ""  # ohne ``pfad`` wie bisher: das Modul selbst ist die Quelle
        return f"rsync://{wer}{k.host}:{k.port}/{k.modul}/{unter}"

    def _basis(self, optionen: Sequence[str], ausnahmen: Sequence[str] = ()) -> list[str]:
        return self.befehl(optionen, ausnahmen)

    def befehl(self, optionen: Sequence[str], ausnahmen: Sequence[str] = ()) -> list[str]:
        """Die vollständige Befehlszeile (auch für Tests). Enthält nie ein Passwort."""
        k = self.konfig
        kopf: list[str] = []
        if shutil.which("nice"):
            kopf += ["nice", "-n", "19"]
        if shutil.which("ionice"):  # am Mac gibt es kein ionice
            kopf += ["ionice", "-c", "3"]
        cmd = kopf + [
            self._rsync,
            "-rt",
            "--chmod=D755,F644",
            "--no-motd",
            f"--timeout={IO_TIMEOUT_S}",
            f"--contimeout={VERBINDUNG_TIMEOUT_S}",
        ]
        if k.passwort_datei is not None:
            cmd.append(f"--password-file={k.passwort_datei}")
        cmd += list(optionen)
        for a in AUSSCHLUESSE + NIE_AUF_DIE_BOX:
            cmd.append(f"--exclude={a}")
        for a in ausnahmen:
            cmd.append(f"--exclude={a}")
        cmd += list(self._zusatz)
        if "--list-only" in optionen:
            cmd.append(self._url())
        else:
            cmd += [self._url(), str(self.medien) + "/"]
        pruefe_nur_lesend(cmd)
        return cmd

    def _grund_aus_code(self, code: int, fehl: str) -> str:
        if self._abbruch_grund is not None:
            return self._abbruch_grund
        if code in _NETZ_CODES:
            return "netz_weg"
        if "auth failed" in fehl or "password file" in fehl:
            return "anmeldung"
        if code == 5 or (code == 23 and "change_dir" in fehl):
            return "quelle_fehlt"  # unbekanntes Modul, Pfad des Moduls fehlt, ``[sync] pfad`` gibt es im Modul nicht, ...
        return "rsync_fehler"

    async def _rsync_lauf(
        self,
        cmd: list[str],
        *,
        lies: bool = False,
        je_zeile: Callable[[str], Awaitable[None]] | None = None,
    ) -> tuple[int, list[str], str]:
        env = dict(os.environ if self._umgebung is None else self._umgebung)
        env.pop("RSYNC_PASSWORD", None)
        k = self.konfig
        if k.passwort_umgebung:
            wert = env.get(k.passwort_umgebung)
            if not wert:
                raise _Abbruch("anmeldung", f"Umgebungsvariable {k.passwort_umgebung} fehlt")
            env["RSYNC_PASSWORD"] = wert
        if k.passwort_datei is not None and not Path(k.passwort_datei).is_file():
            raise _Abbruch("anmeldung", "passwort_datei fehlt")
        self._pruefe_abbruch()
        try:
            p = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                env=env,
            )
        except FileNotFoundError as e:
            raise _Abbruch("rsync_fehler", f"rsync nicht gefunden: {e}") from e
        self._prozess = p
        zeilen: list[str] = []
        fehl_task = asyncio.get_running_loop().create_task(self._lies_alles(p.stderr))
        try:
            await self._lies_zeilen(p.stdout, zeilen if lies else None, je_zeile)
            code = await p.wait()
        except asyncio.CancelledError:
            await self._beende_prozess(p)
            raise
        finally:
            if p.returncode is None:
                await self._beende_prozess(p)
        fehl = (await fehl_task).decode("utf-8", "replace")
        self._prozess = None
        return code, zeilen, fehl

    @staticmethod
    async def _lies_alles(strom: asyncio.StreamReader | None) -> bytes:
        return await strom.read() if strom is not None else b""

    @staticmethod
    async def _lies_zeilen(
        strom: asyncio.StreamReader | None,
        sammeln: list[str] | None,
        je_zeile: Callable[[str], Awaitable[None]] | None,
    ) -> None:
        """Zeilen bei ``\\n`` und ``\\r`` trennen (``--info=progress2`` überschreibt die Zeile mit ``\\r``)."""
        if strom is None:
            return
        rest = ""
        while True:
            block = await strom.read(65536)
            if not block:
                break
            teile = re.split(r"[\r\n]", rest + block.decode("utf-8", "replace"))
            rest = teile.pop()
            for z in teile:
                if not z:
                    continue
                if sammeln is not None:
                    sammeln.append(z)
                if je_zeile is not None:
                    await je_zeile(z)
        if rest:
            if sammeln is not None:
                sammeln.append(rest)
            if je_zeile is not None:
                await je_zeile(rest)

    @staticmethod
    async def _beende_prozess(p: asyncio.subprocess.Process) -> None:
        if p.returncode is not None:
            return
        with contextlib.suppress(ProcessLookupError):
            p.send_signal(signal.SIGTERM)
        try:
            await asyncio.wait_for(p.wait(), ABBRUCH_WARTEN_S)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                p.kill()
            await p.wait()


# --- MPD-Haken ---------------------------------------------------------------------------------------


class MpdHaken:
    """Die zwei MPD-Haken für ``Sync``: spielende Datei und Neueinlesen. Je Aufruf eine kurze Verbindung,
    so stört der Sync die Verbindung des Players nicht. ``fabrik`` liefert einen ``mpd.asyncio.MPDClient``
    (oder Ersatz im Test)."""

    def __init__(self, host: str, port: int, *, fabrik: Callable[[], Any] | None = None, schlafen=asyncio.sleep) -> None:
        self.host = host
        self.port = port
        self._fabrik = fabrik
        self._schlafen = schlafen

    def _neu(self) -> Any:
        if self._fabrik is not None:
            return self._fabrik()
        from mpd.asyncio import MPDClient  # spät: nur der echte Dienst braucht python-mpd2

        return MPDClient()

    async def aktuelle_datei(self) -> str | None:
        """Pfad der gerade geladenen Datei relativ zum Medienordner (``currentsong``), sonst ``None``."""
        c = self._neu()
        await c.connect(self.host, self.port)
        try:
            song = await c.currentsong()
            return song.get("file") if song else None
        finally:
            with contextlib.suppress(Exception):
                c.disconnect()

    async def einlesen(self) -> None:
        """``update`` und warten, bis MPD fertig ist (höchstens ``MPD_EINLESEN_MAX_S``)."""
        c = self._neu()
        await c.connect(self.host, self.port)
        try:
            await c.update()
            ende = time.monotonic() + MPD_EINLESEN_MAX_S
            while time.monotonic() < ende:
                if "updating_db" not in await c.status():
                    return
                await self._schlafen(0.5)
        finally:
            with contextlib.suppress(Exception):
                c.disconnect()
