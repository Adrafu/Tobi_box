"""Gemeinsamer Simulations-Treiber (``box-software.md``, Bausteine und AP 2.2).

Lauscht auf dem Unix-Socket ``<zustand>/sim.sock`` (Rechte 0600), liest JSON-Zeilen und macht
Ereignisse daraus, die er an ``ausgabe`` übergibt. Befehle in Stufe 2 (Schlüssel ``befehl``):

* ``learn``: ``{"befehl":"learn","typ":"serie","serie":"s1","ttl":60}`` oder
  ``{"befehl":"learn","typ":"folge","serie":"s1","folge":"a.mp3","ttl":60}`` -> ``HaLernmodus``
  (``gueltig_bis = jetzt.wall + ttl``). Das Ziel steht nicht im Ereignis (es gehört der Zuordnung
  durch HA); der Treiber merkt es in ``lernziel`` und protokolliert es.
* ``ack``: ``{"befehl":"ack","uid":…,"zuletzt":…,"art":"unbekannt"|"gelernt"}`` -> ``Bestaetigt``.
* ``card``: ``{"befehl":"card","uid":…,"ziel":{"typ":"serie","serie":…}}`` (auch ``folge``, ``aktion``)
  trägt die Zuordnung in ``config.json`` ein (``store``) -> ``KonfigGeladen``.
* ``learn_abort``: ``{"befehl":"learn_abort"}`` -> ``HaLernmodusAbbruch`` (Ablaufzeit 30 s).
* ``status``: ``{"befehl":"status"}`` -> Antwort mit dem Status des Dienstes (``auskunft``), kein Ereignis.

Wer nach dem Lernen die Zuordnung schreibt und bestätigt, steht in ``ha_ersatz.py``.

Ungültige Zeilen werden protokolliert und ignoriert. Jede Zeile wird mit einer JSON-Zeile beantwortet
(``{"ok": true}`` oder ``{"ok": false, "fehler": …}``).
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import events as ev
from .clock import Uhr
from .eventlog import logge
from .ha_ersatz import Abgelehnt, schreibe_zuordnung
from .store import KonfigStore

SOCKET_NAME = "sim.sock"
MAX_ZEILE = 64 * 1024


class Ungueltig(ValueError):
    pass


def _text(d: dict[str, Any], schluessel: str) -> str:
    x = d.get(schluessel)
    if not isinstance(x, str) or not x:
        raise Ungueltig(f"{schluessel} fehlt")
    return x


class Sim:
    def __init__(
        self,
        zustand: str | Path,
        ausgabe: Callable[[ev.Ereignis], Any],
        uhr: Uhr,
        konfig_store: KonfigStore | None = None,
        auskunft: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.zustand = Path(zustand)
        self.pfad = self.zustand / SOCKET_NAME
        self.ausgabe = ausgabe
        self.uhr = uhr
        self.lernziel: dict[str, str] | None = None
        self.lernbefehl_id: str | None = None  # ID des letzten ``learn``; der HA-Ersatz prüft sie
        self.auskunft = auskunft  # Antwort auf ``status`` (der Dienst gibt sie herein)
        self._konfig = konfig_store or KonfigStore(self.zustand)
        self._server: asyncio.AbstractServer | None = None

    # -- Zeile -> Ereignis ---------------------------------------------------

    def zeile_zu_ereignis(self, zeile: str | bytes) -> ev.Ereignis:
        """Wirft ``Ungueltig`` bei jeder ungültigen Zeile."""
        try:
            text = zeile.decode("utf-8") if isinstance(zeile, bytes) else zeile
            d = json.loads(text)
        except ValueError as e:
            raise Ungueltig("kein_json") from e
        if not isinstance(d, dict):
            raise Ungueltig("kein_objekt")
        befehl = d.get("befehl")
        if befehl == "learn":
            return self._learn(d)
        if befehl == "ack":
            art = d.get("art")
            if art not in ("unbekannt", "gelernt"):
                raise Ungueltig("art ungueltig")
            return ev.Bestaetigt(_text(d, "uid"), str(d.get("grund") or "sim"), _text(d, "zuletzt"), art)
        if befehl == "card":
            return self._card(d)
        if befehl == "learn_abort":
            return ev.HaLernmodusAbbruch(str(uuid.uuid4()), self.uhr.jetzt().wall + 30)
        raise Ungueltig(f"befehl unbekannt: {befehl!r}")

    def _learn(self, d: dict[str, Any]) -> ev.Ereignis:
        typ = d.get("typ")
        if typ not in ("serie", "folge"):
            raise Ungueltig("typ ungueltig")
        ziel = {"typ": typ, "serie": _text(d, "serie")}
        if typ == "folge":
            ziel["folge"] = _text(d, "folge")
        ttl = d.get("ttl", 60)
        if isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= 3600:
            raise Ungueltig("ttl ungueltig")
        befehl_id = str(uuid.uuid4())
        self.lernziel = ziel
        self.lernbefehl_id = befehl_id
        logge("sim", "INFO", "lernen", "ok", daten={"befehl_id": befehl_id, **ziel})
        return ev.HaLernmodus(befehl_id, self.uhr.jetzt().wall + ttl)

    def _card(self, d: dict[str, Any]) -> ev.Ereignis:
        uid = _text(d, "uid")
        ziel = d.get("ziel")
        if not isinstance(ziel, dict):
            raise Ungueltig("ziel fehlt")
        try:
            return schreibe_zuordnung(self._konfig, uid, ziel)
        except Abgelehnt as e:
            raise Ungueltig(f"card abgelehnt: {e}") from e

    # -- Server --------------------------------------------------------------

    async def _abliefern(self, e: ev.Ereignis) -> None:
        r = self.ausgabe(e)
        if inspect.isawaitable(r):
            await r

    def _auskunft(self, zeile: bytes) -> dict[str, Any] | None:
        """``status``: der Dienst antwortet mit seinem Status; es entsteht kein Ereignis."""
        try:
            d = json.loads(zeile)
        except ValueError:
            return None
        if not isinstance(d, dict) or d.get("befehl") != "status":
            return None
        if self.auskunft is None:
            raise Ungueltig("status nicht verfuegbar")
        return {"ok": True, **self.auskunft()}

    async def _client(self, leser: asyncio.StreamReader, schreiber: asyncio.StreamWriter) -> None:
        try:
            while True:
                try:
                    zeile = await leser.readline()
                except (asyncio.LimitOverrunError, ValueError):
                    logge("sim", "WARNING", "zeile", "zu_lang")
                    break
                if not zeile:
                    break
                if not zeile.strip():
                    continue
                try:
                    antwort = self._auskunft(zeile)
                    if antwort is None:
                        await self._abliefern(self.zeile_zu_ereignis(zeile))
                        antwort = {"ok": True}
                except Ungueltig as ex:
                    logge("sim", "WARNING", "zeile", "ungueltig", daten={"grund": str(ex)})
                    antwort = {"ok": False, "fehler": str(ex)}
                try:
                    schreiber.write((json.dumps(antwort) + "\n").encode())
                    await schreiber.drain()
                except (ConnectionError, OSError):
                    break
        finally:
            schreiber.close()

    async def start(self) -> None:
        self.zustand.mkdir(parents=True, exist_ok=True)
        try:
            self.pfad.unlink()
        except FileNotFoundError:
            pass
        alt = os.umask(0o177)
        try:
            self._server = await asyncio.start_unix_server(self._client, path=str(self.pfad), limit=MAX_ZEILE)
        finally:
            os.umask(alt)
        os.chmod(self.pfad, 0o600)
        logge("sim", "INFO", "socket", "offen", daten={"pfad": str(self.pfad)})

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        try:
            self.pfad.unlink()
        except FileNotFoundError:
            pass
