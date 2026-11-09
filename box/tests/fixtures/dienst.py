"""Die echte ``App`` mit Home Assistant über einen lokalen Mosquitto, ohne MPD und ohne Leser (AP 3.7).

Echt sind: Ereignisschleife, Ausführer, Kern, Speicher (``config.json``, ``unknown.json``), ``ha`` mit ``paho-mqtt``,
``net``, ``power`` und ``sync``. Ersetzt sind Player, Leser und Tonausgabe (wie in ``cuj/test_cuj07b_app.py``) und die Uhr
(``SimUhr`` mit der echten Wanduhr als Start: Fristen laufen, wenn der Test die Uhr vorstellt).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fixtures.audio import erzeuge_medien
from fixtures.mosquitto import PASSWOERTER, warte_bis
from unit.test_app import FakeLeser, FakePlayer, FakeToene

from tobibox import app as app_modul
from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox import store
from tobibox.app import App
from tobibox.clock import SimUhr

SERIE = "3f9a1c07b2d4"  # „Der kleine Rabe“: folge-01.wav bis folge-03.wav
BAER = "8c21d5e9a0b7"  # „Bär“: a.wav, b.wav
UEBERRASCHUNG = "c07d2e91a45b"
LISTE = "a3f9c1e07b2d4856"
BEKANNT = "04a1b2c3"  # zugeordnet auf BAER
NEU = "04ffeedd"  # unbekannt
BOX = "box1"


class PlayerOhneMpd(FakePlayer):
    async def abspielen(self, b):
        self.aufrufe.append(f"abspielen {b.serie_id}")

    async def pausieren(self, b):
        self.aufrufe.append("pausieren")

    async def ausgang_waehlen(self, a):
        pass


def schreibe_toml(pfad: Path, zustand: Path, medien: Path, abschnitte: str = "") -> Path:
    pfad.write_text(
        f'[pfade]\nzustand = "{zustand}"\nmedien = "{medien}"\n[leser]\ngeraet = "sim"\n{abschnitte}', encoding="utf-8"
    )
    return pfad


def netz_strom_abschnitt() -> str:
    """``[netz]`` und ``[strom]`` mit Simulation (Mac): ``tobibox sim net`` und ``tobibox sim power`` stellen sie ein."""
    return '[netz]\nquelle = "sim"\n[strom]\nquelle = "sim"\n'


def sync_abschnitt(port: int, modul: str = "medien") -> str:
    return f'[sync]\nhost = "127.0.0.1"\nport = {port}\nmodul = "{modul}"\nreserve_mb = 0\n'


def mpd_abschnitt(port: int) -> str:
    return f'[mpd]\nhost = "127.0.0.1"\nport = {port}\n'


def mqtt_abschnitt(port: int, box: str = BOX, host: str = "127.0.0.1") -> str:
    return f'[mqtt]\nbox_id = "{box}"\nhost = "{host}"\nport = {port}\npasswort = "{PASSWOERTER[box]}"\nanzeigename = "Küche"\n'


class Dienst:
    """Eine laufende ``App`` mit Hilfen für die Tests."""

    def __init__(self, app: App, uhr: SimUhr, zustand: Path, toml: Path, medien: Path) -> None:
        self.app, self.uhr, self.zustand, self.toml, self.medien = app, uhr, zustand, toml, medien

    def neustart(self) -> None:
        """Eine neue ``App`` aus derselben Konfiguration und denselben Zustandsdateien (nach ``beende``)."""
        self.app = baue_app(self.toml, self.uhr)

    # -- Zustand ---------------------------------------------------------------------------------------------

    def konfig(self) -> dict:
        return json.loads((self.zustand / "config.json").read_text(encoding="utf-8"))

    def unknown(self) -> dict:
        p = self.zustand / "unknown.json"
        return json.loads(p.read_text(encoding="utf-8"))["eintraege"] if p.exists() else {}

    @property
    def lernt(self) -> bool:
        return self.app.kern.teil["learn"].modus == "lernt"

    @property
    def aufrufe(self) -> list[str]:
        return self.app.player.aufrufe

    def abgespielt(self) -> list[str]:
        """Serien-IDs der ``Abspielen``-Befehle in der Reihenfolge."""
        return [a.split(" ", 1)[1] for a in self.aufrufe if a.startswith("abspielen ")]

    @property
    def toene(self) -> list[str]:
        return self.app.toene.gespielt

    # -- Eingänge --------------------------------------------------------------------------------------------

    async def ruhe(self, runden: int = 3) -> None:
        """Alle bisher eingegangenen Ereignisse und die daraus folgenden Befehle sind verarbeitet."""
        for _ in range(runden):
            await self.app._leere_ereignisse()
            await self.app.befehle.join()
        await self.app.outbox.warte_gespeichert()

    async def sende(self, *ereignisse: ev.Ereignis) -> None:
        for e in ereignisse:
            self.app.ereignisse.put_nowait(e)
        await self.ruhe()

    async def auflegen(self, uid: str, vorgang: str = "v1") -> None:
        await self.sende(ev.Aufgelegt(uid, "ntag", False, 0, vorgang))

    async def abheben(self, vorgang: str = "v1") -> None:
        await self.sende(ev.Abgehoben(1, vorgang))

    async def sim(self, **zeile: Any) -> dict:
        """Eine Zeile an ``sim`` wie von ``tobibox sim`` / der Oberfläche (ohne Socket): ``strom``, ``netz``, …"""
        antwort = await self.app.sim.verarbeite(json.dumps(zeile))
        await self.ruhe()
        return antwort

    async def zeit_vor(self, sekunden: float) -> None:
        """Die simulierte Uhr geht weiter; der nächste Takt (alle 0,1 s echt) verarbeitet die Fristen."""
        self.uhr.vor(sekunden)
        await self.sende(ev.Takt())

    async def warte(self, bedingung, frist_s: float = 8.0, text: str = "") -> None:
        await warte_bis(bedingung, frist_s, text)

    def gesehen(self, name: str) -> list[int]:
        """Positionen (in ``app.gesehen``) der verarbeiteten Ereignisse dieses Typs."""
        return [i for i, n in enumerate(self.app.gesehen) if n == name]


def baue_app(toml: Path, uhr: SimUhr, **app_kw: Any) -> App:
    """Eine ``App`` aus der Konfigurationsdatei, mit Ersatz für Player, Leser und Töne; nicht gestartet.

    Ohne ``ring_ausgabe`` bleibt die Zeile im Terminal aus (Tests haben kein Terminal)."""
    app_kw.setdefault("ring_ausgabe", lambda text: None)
    a = App(konfig_modul.lade(toml), uhr=uhr, melde_bereit=False, **app_kw)
    a.player = PlayerOhneMpd()
    a.player.app = a
    a.leser = FakeLeser()
    a.toene = FakeToene()
    a.toene.gespielt = []
    a.toene.spiele = lambda ton, *args, **kw: a.toene.gespielt.append(ton) or True
    a.gesehen = []
    orig = a.verarbeite

    def verarbeite(e):
        a.gesehen.append(type(e).__name__)
        return orig(e)

    a.verarbeite = verarbeite
    return a


def baue_dienst(
    tmp_path: Path, kurz: Path, monkeypatch: Any, abschnitte: str = "", zuordnungen: dict | None = None, uhr: SimUhr | None = None,
    **app_kw: Any,
) -> Dienst:
    """Medien, ``config.json`` (Liste ``LISTE``, Revision 1) und ``tobibox.toml``; die ``App`` ist gebaut, aber nicht gestartet."""
    medien = erzeuge_medien(tmp_path / "medien")
    zustand = kurz / "var"  # ``sim.sock`` liegt darin: kurzer Pfad
    zustand.mkdir()
    k = ev.Konfig(
        1, LISTE, dict(zuordnungen if zuordnungen is not None else {BEKANNT: ev.Zuordnung("serie", BAER)}),
        ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60),
    )
    store.schreibe_atomar(zustand / "config.json", store.konfig_zu_json(k))
    toml = schreibe_toml(tmp_path / "tobibox.toml", zustand, medien, abschnitte)
    monkeypatch.setattr(app_modul.notify, "stoppt", lambda: None)
    uhr = uhr or SimUhr(wall=time.time())
    return Dienst(baue_app(toml, uhr, **app_kw), uhr, zustand, toml, medien)
