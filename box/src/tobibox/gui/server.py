"""Kleiner HTTP-Server für die Simulations-Oberfläche (AP 4.9, ``tobibox gui``).

Nur Python-Standardbibliothek. Der Server

* liefert die Seite (``seite.html``, Paketdaten),
* gibt unter ``GET /api/anzeige`` alles, was die Seite zeigt, als eine JSON-Antwort heraus
  (Antwort des Dienstes auf ``anzeige``, Tobies aus ``config.json``, Serien, letzte Protokollzeilen),
* leitet unter ``POST /api/befehl`` genau die erlaubten Befehle an ``sim.sock`` weiter.

Er ist ein Client von ``sim.sock`` wie ``tobibox sim``; die Box ändert sich dadurch nicht. Er lauscht nur auf
``127.0.0.1``. Gegen fremde Webseiten im selben Browser prüft er ``Host`` und ``Origin`` und verlangt für
``POST`` den Inhaltstyp ``application/json``.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from importlib import resources
from pathlib import Path
from typing import Any

from .. import library

VORGABE_HOST = "127.0.0.1"
VORGABE_PORT = 8765
SOCKET_TIMEOUT_S = 3.0
MAX_KOERPER = 16 * 1024
LOG_ZEILEN = 25
BIBLIOTHEK_CACHE_S = 5.0

#: Befehle, die die Seite an ``sim.sock`` weiterreichen darf.
ERLAUBT = frozenset({
    "taste", "regler", "kopfhoerer", "strom", "netz",
    "tobie_auflegen", "tobie_gesperrt", "tobie_abheben",
    "learn", "learn_abort", "ack", "zeit",
})

#: Zeile an ``sim.sock`` senden, Antwortzeile lesen (Wörterbuch) oder ``None``, wenn der Dienst nicht antwortet.
Frage = Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]


class KeineBerechtigung(Exception):
    pass


def unix_frage(pfad: Path) -> Frage:
    """Die echte Verbindung: eine Zeile je Anfrage über ``sim.sock``."""

    async def frage(zeile: dict[str, Any]) -> dict[str, Any] | None:
        try:
            async with asyncio.timeout(SOCKET_TIMEOUT_S):
                leser, schreiber = await asyncio.open_unix_connection(str(pfad))
                try:
                    schreiber.write((json.dumps(zeile) + "\n").encode())
                    await schreiber.drain()
                    roh = await leser.readline()
                finally:
                    schreiber.close()
            antwort = json.loads(roh.decode("utf-8"))
        except PermissionError as e:
            raise KeineBerechtigung(str(pfad)) from e
        except (OSError, ValueError, TimeoutError):
            return None
        return antwort if isinstance(antwort, dict) else None

    return frage


def _ziel_text(ziel: dict[str, Any], serien: dict[str, str]) -> str:
    typ = ziel.get("typ")
    if typ == "aktion":
        return {"status": "Status-Karte", "gute_nacht": "Gute-Nacht-Karte"}.get(str(ziel.get("aktion")), "Aktion")
    serie = serien.get(str(ziel.get("serie")), f"Serie {ziel.get('serie')}")
    return f"{serie}, Folge {ziel['folge']}" if typ == "folge" else serie


class Oberflaeche:
    """Der Teil, der ohne Netz testbar ist: die Antworten der API."""

    def __init__(
        self,
        frage: Frage,
        zustand: Path,
        medien: Path | None = None,
        protokoll: Path | None = None,
    ) -> None:
        self.frage = frage
        self.zustand = zustand
        self.medien = medien
        self.protokoll = protokoll
        self._bib: tuple[float, list[dict[str, Any]]] | None = None

    # -- Quellen im Dateisystem ----------------------------------------------------

    def serien(self) -> list[dict[str, Any]]:
        """Normale Serien der Bibliothek (Zwischenspeicher, damit die Abfrage alle 300 ms nichts kostet)."""
        jetzt = time.monotonic()
        if self._bib is not None and jetzt - self._bib[0] < BIBLIOTHEK_CACHE_S:
            return self._bib[1]
        liste: list[dict[str, Any]] = []
        if self.medien is not None:
            try:
                bib = library.lade_bibliothek(self.medien, leise=True)
                liste = [
                    {"id": s.id, "name": s.name, "folgen": list(s.folgen)} for s in bib.serien if s.typ == "normal"
                ]
            except OSError:
                liste = []
        self._bib = (jetzt, liste)
        return liste

    def tobies(self, serien: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Zuordnungen aus ``config.json``: Kennung, Name (Feld ``name``, sonst leer) und Ziel als Text."""
        try:
            roh = json.loads((self.zustand / "config.json").read_text(encoding="utf-8"))
            zuo = roh["zuordnungen"]
            if not isinstance(zuo, dict):
                return []
        except (OSError, ValueError, KeyError):
            return []
        namen = {s["id"]: s["name"] for s in serien}
        aus = []
        for uid, z in zuo.items():
            if not isinstance(z, dict) or not isinstance(z.get("ziel"), dict):
                continue
            name = z.get("name")
            aus.append({
                "uid": uid,
                "name": name if isinstance(name, str) and name else None,
                "ziel": _ziel_text(z["ziel"], namen),
            })
        aus.sort(key=lambda t: (t["name"] or t["uid"]).lower())
        return aus

    def protokoll_zeilen(self) -> dict[str, Any]:
        if self.protokoll is None:
            return {"zeilen": [], "hinweis": "Das Protokoll geht nach stdout (am Pi: journalctl -u tobibox)."}
        from ..cli import _log_zeilen  # späte Einfuhr: cli lädt dieses Paket erst im Befehl ``gui``

        zeilen = _log_zeilen(self.protokoll)[-LOG_ZEILEN:]
        text = [
            " ".join(str(z.get(k)) for k in ("zeit", "ebene", "baustein", "ereignis", "ergebnis") if z.get(k))
            + (" [sim]" if z.get("sim") else "")
            for z in zeilen
        ]
        return {"zeilen": text, "hinweis": "" if text else f"Noch keine Zeilen in {self.protokoll}."}

    # -- API -----------------------------------------------------------------------

    async def anzeige(self) -> dict[str, Any]:
        serien = self.serien()
        basis: dict[str, Any] = {
            "tobies": self.tobies(serien),
            "serien": serien,
            "protokoll": self.protokoll_zeilen(),
        }
        try:
            a = await self.frage({"befehl": "anzeige"})
        except KeineBerechtigung:
            return {**basis, "dienst": "keine_berechtigung"}
        if a is None:
            return {**basis, "dienst": "nicht_erreichbar"}
        if not a.get("ok"):
            return {**basis, "dienst": "fehler", "fehler": a.get("fehler")}
        a = {k: v for k, v in a.items() if k != "ok"}
        a["anzeige"] = {"ring": None, **(a.get("anzeige") or {})}
        return {**basis, "dienst": "laeuft", **a}

    async def befehl(self, zeile: Any) -> tuple[int, dict[str, Any]]:
        """Einen erlaubten Befehl weiterreichen. Rückgabe: (HTTP-Status, Antwort des Dienstes oder Fehler)."""
        if not isinstance(zeile, dict) or zeile.get("befehl") not in ERLAUBT:
            return 400, {"ok": False, "fehler": "befehl_nicht_erlaubt"}
        try:
            a = await self.frage(zeile)
        except KeineBerechtigung:
            return 503, {"ok": False, "fehler": "keine_berechtigung"}
        if a is None:
            return 503, {"ok": False, "fehler": "dienst_nicht_erreichbar"}
        # Ablehnungen des Dienstes sind Antworten, keine Fehler des Servers: Status 200, ``ok`` sagt es.
        return 200, a


# -- HTTP ------------------------------------------------------------------------------


def seite() -> bytes:
    return (resources.files(__package__) / "seite.html").read_bytes()


def _antwort(status: int, koerper: bytes, typ: str) -> bytes:
    gruende = {200: "OK", 400: "Bad Request", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed",
               413: "Payload Too Large", 415: "Unsupported Media Type", 503: "Service Unavailable"}
    kopf = (
        f"HTTP/1.1 {status} {gruende.get(status, 'Error')}\r\n"
        f"Content-Type: {typ}\r\nContent-Length: {len(koerper)}\r\nCache-Control: no-store\r\n"
        "X-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n"
    )
    return kopf.encode() + koerper


def _json(status: int, d: dict[str, Any]) -> bytes:
    return _antwort(status, json.dumps(d, ensure_ascii=False).encode(), "application/json; charset=utf-8")


class Server:
    def __init__(self, ober: Oberflaeche, host: str = VORGABE_HOST, port: int = VORGABE_PORT) -> None:
        self.ober = ober
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None

    def _erlaubte_hosts(self) -> set[str]:
        return {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}

    async def _bearbeite(self, leser: asyncio.StreamReader, schreiber: asyncio.StreamWriter) -> None:
        try:
            antwort = await asyncio.wait_for(self._anfrage(leser), 10)
        except (TimeoutError, ConnectionError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ValueError):
            antwort = _json(400, {"ok": False, "fehler": "anfrage_ungueltig"})
        try:
            schreiber.write(antwort)
            await schreiber.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            schreiber.close()

    async def _anfrage(self, leser: asyncio.StreamReader) -> bytes:
        start = (await leser.readline()).decode("latin-1").split()
        if len(start) != 3:
            raise ValueError("startzeile")
        methode, ziel, _ = start
        kopf: dict[str, str] = {}
        while True:
            z = (await leser.readline()).decode("latin-1")
            if z in ("\r\n", "\n", ""):
                break
            if ":" in z and len(kopf) < 50:
                k, _, v = z.partition(":")
                kopf[k.strip().lower()] = v.strip()
        if kopf.get("host", "") not in self._erlaubte_hosts():
            return _json(403, {"ok": False, "fehler": "host_nicht_erlaubt"})
        pfad = ziel.split("?", 1)[0]
        if methode == "GET":
            if pfad in ("/", "/index.html"):
                return _antwort(200, seite(), "text/html; charset=utf-8")
            if pfad == "/api/anzeige":
                return _json(200, await self.ober.anzeige())
            return _json(404, {"ok": False, "fehler": "nicht_gefunden"})
        if methode == "POST" and pfad == "/api/befehl":
            herkunft = kopf.get("origin")
            if herkunft is not None and herkunft not in {f"http://{h}" for h in self._erlaubte_hosts()}:
                return _json(403, {"ok": False, "fehler": "herkunft_nicht_erlaubt"})
            if not kopf.get("content-type", "").lower().startswith("application/json"):
                return _json(415, {"ok": False, "fehler": "nur_json"})
            laenge = int(kopf.get("content-length", "0"))
            if not 0 < laenge <= MAX_KOERPER:
                return _json(413, {"ok": False, "fehler": "koerper_groesse"})
            try:
                zeile = json.loads((await leser.readexactly(laenge)).decode("utf-8"))
            except ValueError:
                return _json(400, {"ok": False, "fehler": "kein_json"})
            status, antwort = await self.ober.befehl(zeile)
            return _json(status, antwort)
        return _json(405, {"ok": False, "fehler": "methode_nicht_erlaubt"})

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._bearbeite, self.host, self.port, limit=MAX_KOERPER)
        if self.port == 0:
            self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def laufen(self) -> None:
        await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()
