"""Player: dünne MPD-Schicht über ``mpd.asyncio.MPDClient`` (``core-interface.md``, 3.2 und 4).

Aufgaben:

* Die Warteschlange enthält **alle Tracks der aktuellen Folge und nur diese**
  (Entscheidung F, 05.11.); MPD stoppt nach dem letzten Track und spielt nie von
  selbst weiter (``repeat``, ``single``, ``consume`` aus).
* ``Abspielen`` baut die Warteschlange neu auf und springt per ``seek`` auf Track
  und Position (kein Anspielen bei 0:00 bei Wiederaufnahme). Ein fehlender oder
  unlesbarer Track einer Folge mit mehreren Tracks wird übersprungen
  (``datei_fehlt`` im Protokoll); nur wenn kein Track spielbar ist, gibt es
  ``PlayerFehler``.
* ``Pausieren``, ``LautstaerkeSetzen`` (klemmt auf ``grenze``), ``AusgangWaehlen``.
* Ereignisse: ``PlayerPosition`` (mit Track, jede Sekunde, solange etwas spielt, und
  sofort nach Abspielen/Pausieren/Track-Wechsel/Folgenende), ``TrackWechsel``
  (MPD spielt mit dem nächsten Track weiter), ``FolgeZuEnde`` (erst nach dem
  letzten Track), ``PlayerFehler``, ``PlayerVerbindung``. Der Player verbindet
  sich selbst neu.
* ``ton_pause_beginn`` / ``ton_pause_ende`` (Entscheidung L, 09.11.): Kommt ein Ton, während MPD spielt,
  hält der Player MPD an und setzt es nach dem Ton an genau derselben Stelle fort (kein Rücksprung). Der
  Kern erfährt davon nichts: keine ``PlayerPosition`` mit ``spielt=False``, kein Zeiger, kein Status
  „pausiert“. Ein ``Pausieren`` oder ``Abspielen`` während des Tons beendet diese kurze Pause; dann
  setzt ``ton_pause_ende`` nichts fort.
* Vor dem ersten ``Abspielen`` muss eine Lautstärke gesetzt sein; sonst wird
  nichts gespielt. Eine Lautstärke über der Grenze wird auch im Betrieb
  (Abfrage alle 0,2 s) zurückgesetzt.

Der Player kennt weder Zeiger noch Sitzung; ``app.py`` verdrahtet ihn.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from mpd import CommandError
from mpd.asyncio import MPDClient

from . import events as ev
from .eventlog import logge

POSITION_INTERVAL_S = 1.0
ABFRAGE_S = 0.2
VERBINDEN_TIMEOUT_S = 2.0
BEFEHL_TIMEOUT_S = 5.0
NEUVERBINDEN_S: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0)
UPDATE_WARTEN_S = 5.0
FEHLER_DROSSEL_S = 5.0  # gleiche PlayerFehler höchstens alle 5 s

_VERBINDUNGSFEHLER = (ConnectionError, OSError, asyncio.TimeoutError, EOFError)


def _zahl(status: Mapping[str, Any], schluessel: str, vorgabe: float = 0.0) -> float:
    try:
        return float(status[schluessel])
    except (KeyError, TypeError, ValueError):
        return vorgabe


class Player:
    """MPD-Schicht. ``ausgabe`` bekommt jedes Ereignis (aus der Ereignisschleife)."""

    def __init__(
        self,
        ausgabe: Callable[[ev.Ereignis], None],
        host: str = "localhost",
        port: int = 6600,
        *,
        medien: str | Path | None = None,
        ausgaenge: Mapping[str, str] | None = None,
        position_interval_s: float = POSITION_INTERVAL_S,
        abfrage_s: float = ABFRAGE_S,
        backoff_s: tuple[float, ...] = NEUVERBINDEN_S,
        schlafen: Callable[[float], Awaitable[None]] = asyncio.sleep,
        mono: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ausgabe = ausgabe
        self._host = host
        self._port = port
        self._medien = Path(medien) if medien is not None else None
        self._ausgaenge = dict(ausgaenge or {})  # "lautsprecher"/"kopfhoerer" -> MPD-Ausgabename
        self._pos_intervall = position_interval_s
        self._abfrage = abfrage_s
        self._backoff = backoff_s
        self._schlafen = schlafen
        self._mono = mono

        self._client: MPDClient | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._stopp = False
        self._verbunden = False
        self._verlust_gemeldet = False  # letzte gesendete Meldung war ok=False
        self._fehler_zuletzt: dict[tuple[str, str | None, str | None], float] = {}
        self._klemmfehler_gemeldet = False

        self._prozent: int | None = None  # zuletzt gewünschte Lautstärke (nach Klemmung)
        self._grenze: int = 100
        # aktuelle Folge
        self._serie: str | None = None
        self._datei: str | None = None  # Name der Folge
        self._qtracks: list[int] = []  # Warteschlangenplatz -> Nummer des Tracks in der Folge
        self._qpos = 0  # zuletzt gesehener Warteschlangenplatz
        self._track = 0  # Nummer des laufenden Tracks in der Folge
        self._gen = 0  # Generation des letzten ``Abspielen``; trägt jedes Ereignis
        self._gespielt = False  # es lief mindestens ein Track seit dem letzten Abspielen
        self._nichts_zu_spielen = False  # Start hinter dem letzten spielbaren Track
        self._phase = "aus"  # "aus" | "spielt" | "pause"
        self._ton_pause = False  # MPD ist nur für einen Ton angehalten (Entscheidung L); kein echtes Pausieren
        self._elapsed = 0.0
        self._dauer = 0.0
        self._letzte_pos_mono = 0.0

    # ------------------------------------------------------------------
    # Steuerung
    # ------------------------------------------------------------------

    @property
    def verbunden(self) -> bool:
        return self._verbunden

    def start(self) -> asyncio.Task:
        self._stopp = False
        self._task = asyncio.get_running_loop().create_task(self._lauf(), name="tobibox-player")
        return self._task

    async def stop(self) -> None:
        self._stopp = True
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self._trenne()

    async def warte_verbunden(self, timeout_s: float = 5.0) -> bool:
        ende = self._mono() + timeout_s
        while not self._verbunden and self._mono() < ende:
            await asyncio.sleep(0.02)
        return self._verbunden

    # ------------------------------------------------------------------
    # Befehle
    # ------------------------------------------------------------------

    async def lautstaerke_setzen(self, prozent: int, grenze: int) -> None:
        """``LautstaerkeSetzen``: auf ``grenze`` klemmen und (wenn verbunden) setzen."""
        self._grenze = max(0, min(100, int(grenze)))
        self._prozent = max(0, min(int(prozent), self._grenze))
        if not self._verbunden:
            return  # wird beim Verbinden gesetzt
        async with self._lock:
            await self._schutz(self._setze_lautstaerke(), None, None)

    async def ausgang_waehlen(self, ausgang: str) -> None:
        """``AusgangWaehlen``: nur wirksam, wenn Ausgabenamen konfiguriert sind (Pi)."""
        if not self._ausgaenge or not self._verbunden:
            logge("player", "DEBUG", "ausgang", "ohne_wirkung", daten={"ausgang": ausgang})
            return
        async with self._lock:
            await self._schutz(self._waehle_ausgang(ausgang), None, None)

    def _vorhandene_tracks(self, b: ev.Abspielen) -> list[int]:
        """Nummern der Tracks, die im Medienordner liegen (ohne Medienordner: alle)."""
        if self._medien is None:
            return list(range(len(b.tracks)))
        return [i for i, pfad in enumerate(b.tracks) if (self._medien / b.ordner / pfad).is_file()]

    async def abspielen(self, b: ev.Abspielen) -> None:
        """Warteschlange mit allen Tracks der Folge, per ``seek`` auf Track und ``position_s``."""
        if self._prozent is None:
            self._fehler(b.serie_id, b.datei, "mpd_fehler", "Lautstaerke vor dem Abspielen nicht gesetzt")
            return
        vorhanden = self._vorhandene_tracks(b)
        if not vorhanden:
            self._fehler(b.serie_id, b.datei, "datei_fehlt", f"{b.ordner}/{b.datei} nicht im Medienordner")
            return
        for i, pfad in enumerate(b.tracks):
            if i not in vorhanden:
                logge("player", "WARNING", "datei_fehlt", "track_uebersprungen",
                      daten={"serie": b.serie_id, "folge": b.datei, "track": i, "pfad": pfad})
        if not self._verbunden:
            self._fehler(b.serie_id, b.datei, "mpd_fehler", "nicht mit MPD verbunden")
            return
        self._ton_pause = False  # ein neuer Start gewinnt gegen die kurze Pause für einen Ton
        async with self._lock:
            self._serie, self._datei = b.serie_id, b.datei
            self._gen = b.gen
            self._phase = "aus"
            self._elapsed = max(0.0, b.position_s)
            self._dauer = 0.0
            self._track = b.track
            self._qpos = 0
            self._qtracks = []
            self._gespielt = False
            self._nichts_zu_spielen = False
            ok = await self._schutz(self._abspielen(b, vorhanden), b.serie_id, b.datei)
            if ok and self._nichts_zu_spielen:
                # alle Tracks ab dem gewünschten fehlen: das ist das Ende der Folge
                self._folge_ende({})
            elif ok:
                self._phase = "spielt"
                self._letzte_pos_mono = self._mono()
                if self._track != b.track:
                    # fehlende Tracks am Anfang übersprungen: der Zeiger folgt dem spielenden Track
                    logge("player", "INFO", "track_wechsel", "start_uebersprungen",
                          daten={"serie": b.serie_id, "folge": b.datei, "von": b.track, "track": self._track})
                    self._ausgabe(ev.TrackWechsel(b.serie_id, b.datei, self._track, self._gen))
                await self._schutz(self._melde_position(), b.serie_id, b.datei)

    async def pausieren(self, b: ev.Pausieren) -> None:
        """Pause. Ist MPD schon gestoppt (Folgenende), geschieht nichts am Player."""
        self._ton_pause = False  # eine echte Pause gewinnt: nach dem Ton wird nichts fortgesetzt
        if not self._verbunden or self._serie is None or self._datei is None:
            return
        async with self._lock:
            await self._schutz(self._pausieren(), self._serie, self._datei)

    async def ton_pause_beginn(self) -> bool:
        """Vor einem Ton: spielt MPD gerade, anhalten (nicht als echte Pause). ``True``, wenn angehalten."""
        if not self._verbunden or self._phase != "spielt" or self._ton_pause:
            return False
        async with self._lock:
            if not self._verbunden or self._phase != "spielt" or self._client is None:
                return False
            try:
                if (await self._status()).get("state") != "play":
                    return False  # Folgenende oder Fehler: die Abfrage meldet das
                self._ton_pause = True  # vor dem Befehl, damit die Abfrage die Pause nicht als echte meldet
                await self._mpd(self._client.pause(1))
            except CommandError:
                self._ton_pause = False
                return False
            except _VERBINDUNGSFEHLER as e:
                self._ton_pause = False
                self._verbindung_weg(f"{type(e).__name__}: {e}")
                return False
        logge("player", "DEBUG", "ton_pause", "beginn")
        return True

    async def ton_pause_ende(self, fortsetzen: bool = True) -> bool:
        """Nach dem Ton: MPD an derselben Stelle fortsetzen (``pause 0``), wenn die kurze Pause noch gilt.

        ``fortsetzen=False`` beendet die kurze Pause, ohne MPD fortzusetzen (ein neuer Start folgt).
        ``True``, wenn fortgesetzt wurde.
        """
        if not self._ton_pause:
            return False
        async with self._lock:
            if not self._ton_pause:  # ``Pausieren`` oder ``Abspielen`` kam dazwischen
                return False
            self._ton_pause = False
            if not fortsetzen or self._stopp or not self._verbunden or self._client is None:
                return False
            try:
                if (await self._status()).get("state") != "pause":
                    return False
                await self._mpd(self._client.pause(0))
            except CommandError as e:
                self._fehler(self._serie, self._datei, "mpd_fehler", str(e))
                return False
            except _VERBINDUNGSFEHLER as e:
                self._verbindung_weg(f"{type(e).__name__}: {e}")
                return False
            self._letzte_pos_mono = self._mono()
        logge("player", "DEBUG", "ton_pause", "ende")
        return True

    async def pausiere_hart(self) -> bool:
        """Beim Beenden: MPD in jedem Fall anhalten, unabhängig von Serie und Sitzung.

        Erst über die bestehende Verbindung (unter ``_lock``), sonst über eine frische.
        ``True``, wenn MPD danach pausiert oder gestoppt ist.
        """
        self._ton_pause = False  # nach dem harten Pausieren darf kein Ton mehr fortsetzen
        try:
            await asyncio.wait_for(self._lock.acquire(), BEFEHL_TIMEOUT_S)
        except asyncio.TimeoutError:
            gesperrt = True
        else:
            gesperrt = False
            try:
                if self._client is not None and self._verbunden:
                    try:
                        await self._hart_pausieren(self._client)
                        self._phase = "pause" if self._phase == "spielt" else self._phase
                        return True
                    except (*_VERBINDUNGSFEHLER, CommandError) as e:
                        logge("player", "WARNING", "pause_hart", "fehler", daten={"detail": repr(e)})
            finally:
                self._lock.release()
        if gesperrt:
            logge("player", "WARNING", "pause_hart", "gesperrt")
        c = MPDClient()
        try:
            await asyncio.wait_for(c.connect(self._host, self._port), VERBINDEN_TIMEOUT_S)
            await self._hart_pausieren(c)
            return True
        except (*_VERBINDUNGSFEHLER, CommandError) as e:
            logge("player", "ERROR", "pause_hart", "fehler", daten={"detail": repr(e)})
            return False
        finally:
            with contextlib.suppress(Exception):
                c.disconnect()

    async def _hart_pausieren(self, c: MPDClient) -> None:
        try:
            await self._mpd(c.pause(1))
        except CommandError:
            await self._mpd(c.stop())

    # ------------------------------------------------------------------
    # MPD-Aufrufe (unter ``_lock``)
    # ------------------------------------------------------------------

    async def _status(self) -> Mapping[str, Any]:
        assert self._client is not None
        return await self._mpd(self._client.status())

    @staticmethod
    async def _mpd(aufruf: Awaitable[Any]) -> Any:
        """Jeder MPD-Aufruf läuft mit Zeitgrenze ``BEFEHL_TIMEOUT_S`` (hängendes MPD = Verbindungsverlust)."""
        return await asyncio.wait_for(aufruf, BEFEHL_TIMEOUT_S)

    async def _setze_lautstaerke(self) -> None:
        assert self._client is not None and self._prozent is not None
        await self._mpd(self._client.setvol(min(self._prozent, self._grenze)))

    async def _waehle_ausgang(self, ausgang: str) -> None:
        assert self._client is not None
        ziel = self._ausgaenge.get(ausgang)
        for name in self._ausgaenge.values():
            if name == ziel:
                await self._mpd(self._client.enableoutput(await self._ausgabe_id(name)))
            else:
                await self._mpd(self._client.disableoutput(await self._ausgabe_id(name)))

    async def _ausgabe_id(self, name: str) -> int:
        assert self._client is not None
        for o in await self._mpd(self._client.outputs()):
            if o.get("outputname") == name:
                return int(o["outputid"])
        raise CommandError(f"Ausgabe {name!r} unbekannt")

    async def _grundeinstellung(self) -> None:
        """Nichts spielt von selbst weiter: kein Wiederholen, kein Zufall, kein Verbrauch."""
        assert self._client is not None
        c = self._client
        await self._mpd(c.repeat(0))
        await self._mpd(c.random(0))
        await self._mpd(c.single(0))
        await self._mpd(c.consume(0))

    async def _abspielen(self, b: ev.Abspielen, vorhanden: list[int]) -> None:
        assert self._client is not None
        c = self._client
        await self._setze_lautstaerke()  # Klemmung auch kurz vor dem Start
        with contextlib.suppress(CommandError):
            await self._mpd(c.clearerror())
        await self._mpd(c.clear())
        mehrere = len(b.tracks) > 1
        aktualisiert = False
        for i in vorhanden:
            uri = f"{b.ordner}/{b.tracks[i]}"
            try:
                aktualisiert = await self._add(uri, aktualisiert)
            except CommandError as e:
                if mehrere and "No such" in str(e):
                    # nicht im MPD-Bestand (oder unlesbar): Track überspringen, nächster derselben Folge
                    logge("player", "WARNING", "datei_fehlt", "track_uebersprungen",
                          daten={"serie": b.serie_id, "folge": b.datei, "track": i, "pfad": b.tracks[i]})
                    continue
                raise
            self._qtracks.append(i)
        if not self._qtracks:
            raise CommandError("No such directory (kein Track der Folge im MPD-Bestand)")
        # erster spielbarer Track ab dem gewünschten
        start = next((q for q, i in enumerate(self._qtracks) if i >= b.track), None)
        if start is None:
            self._nichts_zu_spielen = True
            with contextlib.suppress(CommandError):
                await self._mpd(c.clear())
            return
        self._qpos = start
        self._track = self._qtracks[start]
        position = b.position_s if self._track == b.track else 0.0
        self._elapsed = max(0.0, position)
        if position > 0.05:
            try:
                await self._mpd(c.seek(start, f"{position:.3f}"))
            except CommandError as e:
                logge("player", "WARNING", "seek", "fehler", daten={"detail": str(e), "position_s": position})
                await self._mpd(c.play(start))
        else:
            await self._mpd(c.play(start))

    async def _add(self, uri: str, schon_aktualisiert: bool = False) -> bool:
        """``uri`` in die Warteschlange; gibt zurück, ob schon aktualisiert wurde (einmal je Abspielen)."""
        assert self._client is not None
        try:
            await self._mpd(self._client.add(uri))
        except CommandError as e:
            if "No such" not in str(e):
                raise
            # nicht im MPD-Bestand: einmal aktualisieren und kurz warten
            if not schon_aktualisiert:
                await self._aktualisiere(uri)
            await self._mpd(self._client.add(uri))
            return True
        return schon_aktualisiert

    async def _aktualisiere(self, uri: str) -> None:
        assert self._client is not None
        with contextlib.suppress(CommandError):
            await self._mpd(self._client.update(uri))
        ende = self._mono() + UPDATE_WARTEN_S
        while self._mono() < ende:
            if "updating_db" not in await self._status():
                return
            await self._schlafen(0.05)

    async def _pausieren(self) -> None:
        assert self._client is not None and self._serie is not None and self._datei is not None
        st = await self._status()
        zustand = st.get("state")
        if zustand == "play":
            try:
                await self._mpd(self._client.pause(1))
            except CommandError as e:
                st2 = await self._status()
                z2 = st2.get("state")
                if z2 == "pause":
                    pass
                elif z2 == "stop" and not st2.get("error"):
                    # Folge war gerade zu Ende: kein Fehler, sondern Folgenende
                    self._folge_ende(st2)
                    return
                else:
                    raise e
            self._phase = "pause"
        elif zustand == "pause":
            self._phase = "pause"
        else:
            # gestoppt: ist das Folgenende noch nicht gemeldet, meldet es die Abfrage
            if self._phase != "spielt":
                self._phase = "aus"
        st_nach = await self._status()
        self._merke(st_nach)
        self._pruefe_trackwechsel(st_nach)
        self._sende_position(spielt=False)

    async def _melde_position(self) -> None:
        self._merke(await self._status())
        self._sende_position(spielt=self._phase == "spielt")

    def _merke(self, st: Mapping[str, Any]) -> None:
        if st.get("state") in ("play", "pause"):
            self._elapsed = _zahl(st, "elapsed", self._elapsed)
            self._dauer = _zahl(st, "duration", self._dauer)

    def _sende_position(self, *, spielt: bool, position_s: float | None = None) -> None:
        if self._serie is None or self._datei is None:
            return
        pos = self._elapsed if position_s is None else position_s
        self._ausgabe(ev.PlayerPosition(self._serie, self._datei, self._track, round(pos, 3), spielt, self._gen))

    def _pruefe_trackwechsel(self, st: Mapping[str, Any]) -> None:
        """MPD ist zu einem anderen Titel der Warteschlange gewechselt: ``TrackWechsel``,
        danach sofort die Position des neuen Tracks. Springt MPD über einen unlesbaren
        Titel, ist das ein einziger Wechsel auf den Track dahinter."""
        if self._serie is None or self._datei is None or st.get("state") not in ("play", "pause"):
            return
        try:
            song = int(st["song"])
        except (KeyError, TypeError, ValueError):
            return
        if song == self._qpos or not 0 <= song < len(self._qtracks):
            return
        self._qpos = song
        self._track = self._qtracks[song]
        self._elapsed = _zahl(st, "elapsed", 0.0)
        self._dauer = _zahl(st, "duration", 0.0)
        self._letzte_pos_mono = self._mono()
        logge("player", "INFO", "track_wechsel", "ok", daten={"serie": self._serie, "folge": self._datei, "track": self._track})
        self._ausgabe(ev.TrackWechsel(self._serie, self._datei, self._track, self._gen))
        self._sende_position(spielt=st.get("state") == "play")

    # ------------------------------------------------------------------
    # Fehlerbehandlung
    # ------------------------------------------------------------------

    def _fehler(self, serie: str | None, datei: str | None, art: str, detail: str) -> None:
        jetzt = self._mono()
        schluessel = (art, serie, datei)
        zuletzt = self._fehler_zuletzt.get(schluessel)
        if zuletzt is not None and jetzt - zuletzt < FEHLER_DROSSEL_S:
            logge("player", "DEBUG", "player_fehler", "gedrosselt", daten={"art": art, "detail": detail})
            return
        self._fehler_zuletzt[schluessel] = jetzt
        logge("player", "ERROR", "player_fehler", art, daten={"serie": serie, "datei": datei, "detail": detail})
        self._ausgabe(ev.PlayerFehler(serie, datei, art, detail))  # type: ignore[arg-type]

    async def _schutz(self, aufruf: Awaitable[None], serie: str | None, datei: str | None) -> bool:
        """Einen MPD-Aufruf ausführen; Fehler werden zu Ereignissen. ``True`` bei Erfolg."""
        try:
            await aufruf
            return True
        except CommandError as e:
            text = str(e)
            art = "datei_fehlt" if "No such" in text else "mpd_fehler"
            self._phase = "aus"
            self._fehler(serie, datei, art, text)
        except _VERBINDUNGSFEHLER as e:
            self._verbindung_weg(f"{type(e).__name__}: {e}")
        return False

    # ------------------------------------------------------------------
    # Verbindung und Abfrageschleife
    # ------------------------------------------------------------------

    def _trenne(self) -> None:
        c, self._client = self._client, None
        if c is not None:
            with contextlib.suppress(Exception):
                c.disconnect()
        self._verbunden = False

    def _verbindung_weg(self, grund: str) -> None:
        war = self._verbunden
        self._trenne()
        self._phase = "aus"  # der MPD-Zustand ist verloren; Wiederaufnahme kommt per Abspielen
        if war or not self._verlust_gemeldet:
            logge("player", "ERROR", "mpd_verbindung", "verloren", daten={"detail": grund})
            self._verlust_gemeldet = True
            self._ausgabe(ev.PlayerVerbindung(False))

    async def _verbinde(self) -> None:
        c = MPDClient()
        try:
            await asyncio.wait_for(c.connect(self._host, self._port), VERBINDEN_TIMEOUT_S)
            self._client = c
            async with self._lock:
                # Zuerst Sicherheit: MPD darf nicht von selbst weiterspielen
                # (Neustart des Dienstes oder von MPD, Zustand aus einer früheren Sitzung).
                st = await self._status()
                if st.get("state") == "play":
                    try:
                        await self._mpd(c.pause(1))
                    except CommandError:
                        await self._mpd(c.stop())
                if self._prozent is None:
                    # Noch keine Grenze bekannt: stumm, bis der Kern LautstaerkeSetzen sendet
                    await self._mpd(c.setvol(0))
                else:
                    await self._setze_lautstaerke()
                await self._grundeinstellung()
                # Rennen mit lautstaerke_setzen: ab hier gilt "verbunden"; der zuletzt
                # gewünschte Wert wird noch einmal gesetzt (ohne Unterbrechung dazwischen).
                self._verbunden = True
                if self._prozent is not None:
                    await self._setze_lautstaerke()
        except BaseException:
            self._trenne()
            with contextlib.suppress(Exception):
                c.disconnect()
            raise
        logge("player", "INFO", "mpd_verbindung", "ok", daten={"host": self._host, "port": self._port})
        if self._verlust_gemeldet:
            self._verlust_gemeldet = False
            self._ausgabe(ev.PlayerVerbindung(True))

    async def _lauf(self) -> None:
        versuch = 0
        while not self._stopp:
            try:
                if not self._verbunden:
                    try:
                        await self._verbinde()
                        versuch = 0
                    except (*_VERBINDUNGSFEHLER, CommandError) as e:
                        self._verbindung_weg(f"{type(e).__name__}: {e}")
                        await self._schlafen(self._backoff[min(versuch, len(self._backoff) - 1)])
                        versuch += 1
                        continue
                await self._abfrage_schritt()
                await self._schlafen(self._abfrage)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # die Schleife darf nie still sterben
                logge("player", "ERROR", "abfrage", "fehler", daten={"detail": f'{type(e).__name__}: {e}'})
                self._verbindung_weg(f"{type(e).__name__}: {e}")
                await self._schlafen(self._backoff[0])

    async def _abfrage_schritt(self) -> None:
        async with self._lock:
            if not self._verbunden:
                return
            try:
                st = await self._status()
                await self._pruefe(st)
            except _VERBINDUNGSFEHLER as e:
                self._verbindung_weg(f"{type(e).__name__}: {e}")
            except CommandError as e:
                self._fehler(self._serie, self._datei, "mpd_fehler", str(e))

    async def _klemme(self) -> None:
        """Lautstärke zurücksetzen. Gelingt das nicht: einmal ERROR und sicherheitshalber pausieren."""
        assert self._client is not None
        try:
            await self._setze_lautstaerke()
        except CommandError as e:
            if not self._klemmfehler_gemeldet:
                self._klemmfehler_gemeldet = True
                logge("player", "ERROR", "lautstaerke_geklemmt", "fehler", daten={"detail": str(e), "grenze": self._grenze})
            try:
                await self._mpd(self._client.pause(1))
            except CommandError:
                with contextlib.suppress(CommandError):
                    await self._mpd(self._client.stop())
            if self._phase == "spielt":
                self._phase = "pause"
            return
        self._klemmfehler_gemeldet = False

    async def _pruefe(self, st: Mapping[str, Any]) -> None:
        assert self._client is not None
        # Klemmung im Dienst: MPD darf nie über der Grenze stehen
        if self._prozent is not None and "volume" in st:
            try:
                vol = int(st["volume"])
            except (TypeError, ValueError):
                vol = -1
            if vol > self._grenze:
                logge("player", "WARNING", "lautstaerke_geklemmt", "ok", daten={"mpd": vol, "grenze": self._grenze})
                await self._klemme()
        zustand = st.get("state")
        if self._phase != "spielt" or self._serie is None or self._datei is None:
            return
        if self._ton_pause:
            return  # MPD ist nur für einen Ton angehalten: weder Pause noch Position melden
        if zustand == "play":
            self._gespielt = True
            self._merke(st)
            self._pruefe_trackwechsel(st)
            jetzt = self._mono()
            if jetzt - self._letzte_pos_mono >= self._pos_intervall:
                self._letzte_pos_mono = jetzt
                self._sende_position(spielt=True)
        elif zustand == "pause":
            self._phase = "pause"  # von außen angehalten
            self._merke(st)
            self._pruefe_trackwechsel(st)
            self._sende_position(spielt=False)
        else:  # stop: Folge zu Ende oder Fehler
            serie, datei = self._serie, self._datei
            fehler = st.get("error")
            if fehler:
                with contextlib.suppress(CommandError):
                    await self._mpd(self._client.clearerror())
                if len(self._qtracks) > 1 and self._gespielt:
                    # der letzte Track einer Folge mit mehreren Tracks ist unlesbar: Ende der Folge
                    logge("player", "WARNING", "datei_unlesbar", "track_uebersprungen",
                          daten={"serie": serie, "folge": datei, "detail": str(fehler)})
                    self._folge_ende(st)
                    return
                self._phase = "aus"
                self._fehler(serie, datei, "datei_unlesbar", str(fehler))
                return
            self._folge_ende(st)

    def _folge_ende(self, st: Mapping[str, Any]) -> None:
        """Folge ist zu Ende gespielt (MPD gestoppt, kein Fehler)."""
        assert self._serie is not None and self._datei is not None
        serie, datei = self._serie, self._datei
        self._phase = "aus"
        if self._qtracks:
            self._track = self._qtracks[-1]  # die Endposition gehört zum letzten Track
        ende = self._dauer if self._dauer > 0 else self._elapsed
        self._sende_position(spielt=False, position_s=max(ende, self._elapsed))
        logge("player", "INFO", "folge_zu_ende", "ok", daten={"serie": serie, "datei": datei})
        self._ausgabe(ev.FolgeZuEnde(serie, datei, self._gen))
