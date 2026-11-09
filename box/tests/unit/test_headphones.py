"""Kopfhörer (CUJ 17, AP 4.4): Ereignis, Treiber, Reihenfolge „erst Grenze, dann Ausgang“, Töne an der Kopfhörer-Grenze."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mpd import CommandError

from tobibox import app as app_modul
from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox import headphones
from tobibox.app import App
from tobibox.clock import SimUhr
from tobibox.headphones import Buchse, GpioKopfhoerer, KopfhoererFehler, SimKopfhoerer
from tobibox.player import Player
from tobibox.sounds import Toene, pegel
from tobibox.volume import GRENZE_KOPFHOERER

# --- Buchse und Simulation -----------------------------------------------------------------------------------


async def test_erste_messung_wird_gemeldet_auch_ohne_stecker():
    sim = SimKopfhoerer()
    b = Buchse(sim)
    assert await b.start() == [ev.Kopfhoerer(False)]
    assert await b.pruefe() == []


async def test_stecker_beim_start_wird_sofort_gemeldet():
    b = Buchse(SimKopfhoerer(True))
    assert await b.start() == [ev.Kopfhoerer(True)]


async def test_einstecken_und_ziehen_sind_zwei_ereignisse():
    sim = SimKopfhoerer()
    gesehen: list = []
    b = Buchse(sim, gesehen.append, entprellen=1)
    await b.start()
    sim.setze(True)
    assert await b.pruefe() == [ev.Kopfhoerer(True)]
    assert await b.pruefe() == []  # unverändert: nichts
    sim.setze(False)
    assert await b.pruefe() == [ev.Kopfhoerer(False)]
    assert gesehen == [ev.Kopfhoerer(False), ev.Kopfhoerer(True), ev.Kopfhoerer(False)]


async def test_entprellen_ein_wackler_zaehlt_nicht():
    sim = SimKopfhoerer()
    b = Buchse(sim, entprellen=2)
    await b.start()
    sim.setze(True)
    assert await b.pruefe() == []  # erste Messung mit Stecker
    sim.setze(False)
    assert await b.pruefe() == []  # Wackler vorbei
    sim.setze(True)
    assert await b.pruefe() == []
    assert await b.pruefe() == [ev.Kopfhoerer(True)]  # zweimal hintereinander


async def test_melde_ohne_entprellen_und_nur_bei_aenderung():
    b = Buchse(SimKopfhoerer())
    assert await b.melde(True) == [ev.Kopfhoerer(True)]
    assert await b.melde(True) == []
    assert await b.melde(False) == [ev.Kopfhoerer(False)]


async def test_ausgabe_darf_asynchron_sein():
    gesehen: list = []

    async def aus(e):
        gesehen.append(e)

    b = Buchse(SimKopfhoerer(True), aus)
    await b.start()
    assert gesehen == [ev.Kopfhoerer(True)]


async def test_unlesbarer_kontakt_haelt_den_letzten_wert_und_loggt_einmal(caplog):
    class Kaputt:
        def __init__(self):
            self.ok = True
            self.wert = True

        async def steckt(self):
            if not self.ok:
                raise KopfhoererFehler("weg")
            return self.wert

    k = Kaputt()
    b = Buchse(k, entprellen=1)
    await b.start()
    k.ok = False
    assert await b.pruefe() == [ev.KopfhoererLesbar(False)]  # Entscheidung P: einmal melden, dann gilt die Kopfhörer-Grenze
    for _ in range(2):
        assert await b.pruefe() == []
    assert b.steckt is True
    warnungen = [r for r in caplog.records if r.levelname == "WARNING" and getattr(r, "ereignis", "") == "messen"]
    assert len(warnungen) == 1
    k.ok, k.wert = True, False
    assert await b.pruefe() == [ev.Kopfhoerer(False), ev.KopfhoererLesbar(True)]  # erst der Wert, dann wieder lesbar


async def test_start_mit_unlesbarem_kontakt_meldet_nichts_und_spaeter_den_ersten_wert():
    sim = SimKopfhoerer(True)
    laeuft = {"ok": False}

    class Treiber:
        async def steckt(self):
            if not laeuft["ok"]:
                raise OSError("noch nicht")
            return await sim.steckt()

    b = Buchse(Treiber(), entprellen=1)
    assert await b.start() == [ev.KopfhoererLesbar(False)]  # B3/Entscheidung P: ohne erste Messung gilt die Kopfhörer-Grenze
    assert b.steckt is None
    laeuft["ok"] = True
    assert await b.pruefe() == [ev.Kopfhoerer(True), ev.KopfhoererLesbar(True)]


def test_entprellen_unter_eins_ist_ein_fehler():
    with pytest.raises(ValueError):
        Buchse(SimKopfhoerer(), entprellen=0)


async def test_dauerlauf_meldet_und_laesst_sich_beenden():
    sim = SimKopfhoerer()
    gesehen: list = []
    b = Buchse(sim, gesehen.append, intervall_s=0.01, entprellen=1)
    await b.start()
    aufgabe = asyncio.create_task(b.lauf())
    sim.setze(True)
    for _ in range(100):
        if ev.Kopfhoerer(True) in gesehen:
            break
        await asyncio.sleep(0.01)
    aufgabe.cancel()
    with pytest.raises(asyncio.CancelledError):
        await aufgabe
    assert gesehen == [ev.Kopfhoerer(False), ev.Kopfhoerer(True)]


# --- GPIO-Treiber gegen eine Attrappe ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "aktiv_niedrig, pegel_hoch, steckt",
    [(True, False, True), (True, True, False), (False, True, True), (False, False, False)],
)
async def test_gpio_pegel_und_polaritaet(aktiv_niedrig, pegel_hoch, steckt):
    async def lese():
        return pegel_hoch

    assert await GpioKopfhoerer(17, aktiv_niedrig=aktiv_niedrig, lese=lese).steckt() is steckt


@pytest.mark.parametrize(
    "text, erwartet",
    [("1\n", True), ("0\n", False), ('"17"=active\n', True), ('"17"=inactive\n', False), ("17=inactive", False)],
)
def test_parse_pegel(text, erwartet):
    assert headphones.parse_pegel(text) is erwartet


def test_parse_pegel_unverstaendlich():
    with pytest.raises(KopfhoererFehler):
        headphones.parse_pegel("hallo")


def _gpioget_skript(tmp_path, version: str, pegel_datei) -> None:
    """Attrappe für ``gpioget``: schreibt die Argumente in ``aufruf``, kennt ``--version``, gibt den Pegel aus der Datei aus."""
    skript = tmp_path / "gpioget"
    skript.write_text(
        '#!/bin/sh\n'
        f'if [ "$1" = "--version" ]; then echo "gpioget (libgpiod) {version}"; exit 0; fi\n'
        f'echo "$@" > {tmp_path}/aufruf\n'
        f'cat {pegel_datei}\n'
    )
    skript.chmod(0o755)


@pytest.fixture
def ohne_gpiozero(monkeypatch):
    """Rückfall auf ``gpioget``: ``gpiozero`` gilt als nicht installiert; die Versionserkennung ist frisch."""
    import sys

    from tobibox import headphones

    monkeypatch.setitem(sys.modules, "gpiozero", None)  # ``import gpiozero`` -> ImportError
    monkeypatch.setattr(headphones, "_versionen", {})


async def test_gpioget_libgpiod_1_mit_bias_pull_up(tmp_path, monkeypatch, ohne_gpiozero):
    """B4: libgpiod 1.x: ``gpioget --bias=pull-up <chip> <pin>``."""
    pegel = tmp_path / "pegel"
    pegel.write_text("0\n")
    _gpioget_skript(tmp_path, "1.6.3", pegel)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    k = GpioKopfhoerer(17, chip="gpiochip0")
    assert await k.steckt() is True  # Pegel tief, aktiv niedrig
    assert (tmp_path / "aufruf").read_text().strip() == "--bias=pull-up gpiochip0 17"
    pegel.write_text("1\n")
    assert await k.steckt() is False
    assert k.dauerhaft is False  # Prozess je Messung: die Buchse misst seltener


async def test_gpioget_libgpiod_2_mit_bias_und_c(tmp_path, monkeypatch, ohne_gpiozero):
    """B4: libgpiod 2.x: ``gpioget --bias=pull-up -c <chip> <pin>``; Ausgabe ``"17"=active`` / ``inactive``."""
    pegel = tmp_path / "pegel"
    pegel.write_text('"17"=inactive\n')
    _gpioget_skript(tmp_path, "v2.1.3", pegel)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    k = GpioKopfhoerer(17, chip="gpiochip0")
    assert await k.steckt() is True
    assert (tmp_path / "aufruf").read_text().strip() == "--bias=pull-up -c gpiochip0 17"
    pegel.write_text('"17"=active\n')
    assert await k.steckt() is False


async def test_gpioget_aktiv_hoch_nimmt_pull_down(tmp_path, monkeypatch, ohne_gpiozero):
    pegel = tmp_path / "pegel"
    pegel.write_text("1\n")
    _gpioget_skript(tmp_path, "1.6.3", pegel)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    k = GpioKopfhoerer(17, aktiv_niedrig=False)
    assert await k.steckt() is True
    assert "--bias=pull-down" in (tmp_path / "aufruf").read_text()


def test_gpioget_befehl_je_version():
    from tobibox.headphones import gpioget_befehl

    assert gpioget_befehl(1, "gpiochip0", 5, pull_up=True) == ["gpioget", "--bias=pull-up", "gpiochip0", "5"]
    assert gpioget_befehl(2, "gpiochip0", 5, pull_up=False) == ["gpioget", "--bias=pull-down", "-c", "gpiochip0", "5"]


class GpiozeroAttrappe:
    """Nur ``DigitalInputDevice``: merkt sich die Argumente; ``value`` 1 = aktiv (bei Pull-up: Pin tief)."""

    def __init__(self) -> None:
        self.aufrufe: list[tuple] = []
        self.geraet: "GpiozeroAttrappe.Geraet | None" = None

    class Geraet:
        def __init__(self) -> None:
            self.value = 0
            self.zu = False

        def close(self) -> None:
            self.zu = True

    def DigitalInputDevice(self, pin, **kw):  # noqa: N802 - Name wie in gpiozero
        self.aufrufe.append((pin, kw))
        self.geraet = self.Geraet()
        return self.geraet


async def test_gpiozero_ist_der_vorrang_ohne_prozess_und_mit_pull_up():
    """B4: Vorgabe ist gpiozero (kein Prozess je Messung, ausdrücklicher Pull-up)."""
    g = GpiozeroAttrappe()
    k = GpioKopfhoerer(17, fabrik=g)
    assert await k.steckt() is False  # value 0 = Pin hoch = offen
    assert g.aufrufe == [(17, {"pull_up": True, "bounce_time": None})]
    g.geraet.value = 1  # aktiv = Pin tief = Stecker
    assert await k.steckt() is True
    assert k.dauerhaft is True
    k.schliesse()
    assert g.geraet is not None and g.geraet.zu


async def test_gpiozero_aktiv_hoch_mit_pull_down():
    g = GpiozeroAttrappe()
    k = GpioKopfhoerer(17, aktiv_niedrig=False, fabrik=g)
    await k.steckt()
    assert g.aufrufe[0][1]["pull_up"] is False
    g.geraet.value = 1
    assert await k.steckt() is True


async def test_gpiozero_fehler_ist_ein_oserror():
    class Kaputt:
        def DigitalInputDevice(self, pin, **kw):  # noqa: N802
            raise RuntimeError("Pin belegt")

    with pytest.raises(OSError):
        await GpioKopfhoerer(17, fabrik=Kaputt()).steckt()


async def test_buchse_misst_mit_gpioget_hoechstens_einmal_je_sekunde(monkeypatch):
    """B4: Rückfall ohne gpiozero: kein Prozessstart alle 0,2 s."""
    from tobibox import headphones

    class T:
        dauerhaft = False

        async def steckt(self):
            return False

    schlaf: list[float] = []

    async def schlafen(s):
        schlaf.append(s)
        raise asyncio.CancelledError

    monkeypatch.setattr(headphones.asyncio, "sleep", schlafen)
    with pytest.raises(asyncio.CancelledError):
        await Buchse(T(), intervall_s=0.2).lauf()
    assert schlaf == [headphones.GPIOGET_INTERVALL_MIN_S]


async def test_gpioget_fehlt_ist_ein_oserror(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(OSError):
        await GpioKopfhoerer(17).steckt()


async def test_gpioget_fehlerstatus_ist_ein_oserror(tmp_path, monkeypatch):
    skript = tmp_path / "gpioget"
    skript.write_text("#!/bin/sh\nexit 1\n")
    skript.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    with pytest.raises(OSError):
        await GpioKopfhoerer(17).steckt()


async def test_buchse_mit_gpio_attrappe_ende_zu_ende():
    pegel_hoch = {"v": True}  # offen: Pull-up, hoch -> kein Stecker

    async def lese():
        return pegel_hoch["v"]

    b = Buchse(GpioKopfhoerer(17, lese=lese), entprellen=2)
    assert await b.start() == [ev.Kopfhoerer(False)]
    pegel_hoch["v"] = False
    assert await b.pruefe() == []
    assert await b.pruefe() == [ev.Kopfhoerer(True)]


# --- Player: erst Grenze, dann Ausgang --------------------------------------------------------------------------


class MpdAttrappe:
    """Schreibt alle Aufrufe in ein Journal; zwei Ausgaben ``Lautsprecher`` und ``Kopfhoerer``."""

    def __init__(self) -> None:
        self.journal: list[str] = []
        self.aktiv = {"Lautsprecher": True, "Kopfhoerer": False}
        self.zustand = "play"

    async def status(self):
        return {"state": self.zustand, "volume": "50", "elapsed": "3.0", "duration": "30.0"}

    async def setvol(self, v):
        self.journal.append(f"setvol {v}")

    async def pause(self, n):
        self.journal.append(f"pause {n}")
        self.zustand = "pause" if n else "play"

    async def outputs(self):
        return [{"outputid": "0", "outputname": "Lautsprecher"}, {"outputid": "1", "outputname": "Kopfhoerer"}]

    async def enableoutput(self, i):
        self.journal.append(f"enable {i}")

    async def disableoutput(self, i):
        self.journal.append(f"disable {i}")


def mk_player(client=None, verbunden=True):
    c = client or MpdAttrappe()
    p = Player(lambda e: None, ausgaenge={"lautsprecher": "Lautsprecher", "kopfhoerer": "Kopfhoerer"})
    p._client = c
    p._verbunden = verbunden
    return p, c


async def test_player_setzt_die_grenze_vor_dem_umschalten():
    p, c = mk_player()
    await p.lautstaerke_setzen(25, 25)  # Kern: Rang 1, die neue Grenze
    await p.ausgang_waehlen("kopfhoerer")  # Rang 2
    i_laut = max(i for i, z in enumerate(c.journal) if z.startswith("setvol"))
    i_aus = min(i for i, z in enumerate(c.journal) if z.startswith(("enable", "disable")))
    assert i_laut < i_aus
    assert c.journal[i_aus - 1] == "setvol 25"  # direkt vor dem Umschalten gilt die Grenze noch einmal
    assert c.journal[i_aus:] == ["disable 0", "enable 1"]  # der Lautsprecher schaltet ab


async def test_player_ziehen_lautsprecher_mit_normaler_grenze():
    p, c = mk_player()
    await p.lautstaerke_setzen(25, 25)
    await p.ausgang_waehlen("kopfhoerer")
    c.journal.clear()
    await p.lautstaerke_setzen(40, 60)
    await p.ausgang_waehlen("lautsprecher")
    assert c.journal == ["setvol 40", "setvol 40", "enable 0", "disable 1"]


async def test_player_klemmt_auch_wenn_der_aufrufer_sich_irrt():
    """Kopfhörer-Grenze 25, aber der Wunsch war 40: MPD bekommt nie mehr als die Grenze."""
    p, c = mk_player()
    await p.lautstaerke_setzen(40, 25)
    await p.ausgang_waehlen("kopfhoerer")
    assert all(int(z.split()[1]) <= 25 for z in c.journal if z.startswith("setvol"))


async def test_player_ohne_ausgaenge_aendert_nichts_am_mpd():
    c = MpdAttrappe()
    p = Player(lambda e: None)
    p._client, p._verbunden = c, True
    await p.lautstaerke_setzen(25, 25)
    c.journal.clear()
    await p.ausgang_waehlen("kopfhoerer")
    assert c.journal == []


async def test_player_scheitert_das_setzen_der_grenze_wird_nicht_umgeschaltet():
    class Boese(MpdAttrappe):
        async def setvol(self, v):
            raise CommandError("setvol kaputt")

    p, c = mk_player(Boese())
    p._prozent, p._grenze = 25, 25
    await p.ausgang_waehlen("kopfhoerer")
    assert c.journal == []  # keine Umschaltung ohne gesetzte Grenze


async def test_player_wunsch_gilt_nach_dem_neuverbinden_erst_hinter_der_lautstaerke(monkeypatch):
    p, c = mk_player(verbunden=False)
    await p.lautstaerke_setzen(25, 25)
    await p.ausgang_waehlen("kopfhoerer")  # MPD weg: nur gemerkt
    assert c.journal == []
    monkeypatch.setattr("tobibox.player.MPDClient", lambda: _VerbindeAttrappe(c))
    p._client = None
    await p._verbinde()
    haupt = [z for z in c.journal if z.startswith(("setvol", "enable", "disable"))]
    assert haupt.index("setvol 25") < haupt.index("enable 1")


class _VerbindeAttrappe:
    def __init__(self, c: MpdAttrappe) -> None:
        self.c = c

    async def connect(self, host, port): ...
    def disconnect(self): ...

    def __getattr__(self, name):
        return getattr(self.c, name)

    async def repeat(self, n): ...
    async def random(self, n): ...
    async def single(self, n): ...
    async def consume(self, n): ...


async def test_ausgangswechsel_waehrend_der_ton_pause_laesst_ton_pause_und_epoche_unberuehrt():
    """Entscheidung L: Der Wechsel hält MPD nicht an, setzt nichts fort und ändert die Ton-Epoche nicht."""
    p, c = mk_player()
    p._serie, p._datei, p._phase = "s", "a.wav", "spielt"
    assert await p.ton_pause_beginn() is True
    epoche = p._ton_epoche
    await p.lautstaerke_setzen(25, 25)
    await p.ausgang_waehlen("kopfhoerer")
    assert p._ton_pause is True and p._ton_epoche == epoche
    assert "pause 0" not in c.journal
    assert await p.ton_pause_ende() is True  # die Pause endet wie vorgesehen, an derselben Stelle
    assert c.journal[-1] == "pause 0"


# --- Kern und App: Reihenfolge und Töne ----------------------------------------------------------------------


@pytest.fixture
async def welt(tmp_path, monkeypatch, protokoll):
    zustand = tmp_path / "var"
    zustand.mkdir()
    (tmp_path / "medien").mkdir()
    toml = tmp_path / "tobibox.toml"
    toml.write_text(
        f'[pfade]\nzustand = "{zustand}"\nmedien = "{tmp_path / "medien"}"\n[leser]\ngeraet = "sim"\n'
        "[lautstaerke]\nmax = 60\nstart = 40\nkopfhoerer = 25\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_modul.notify, "stoppt", lambda: None)
    journal: list[str] = []
    toene: list[tuple[str, int]] = []

    class Aufnahme:
        def start(self): ...
        async def warte_verbunden(self, timeout_s=5.0):
            return True
        async def pausiere_hart(self):
            return True
        async def stop(self): ...
        async def lautstaerke_setzen(self, prozent, grenze):
            journal.append(f"lautstaerke {prozent}/{grenze}")
        async def ausgang_waehlen(self, ausgang):
            journal.append(f"ausgang {ausgang}")
        async def abspielen(self, b): ...
        async def pausieren(self, b): ...
        async def ton_pause_beginn(self):
            return False
        async def ton_pause_ende(self, *a, **k):
            return False

    class Leser:
        def start(self): ...
        async def stop(self): ...
        def ping(self): ...

    async def starter(kommando):
        toene.append((Path(kommando[-1]).name.split("-")[2], int(kommando[1])))

    a = App(konfig_modul.lade(toml), uhr=SimUhr(), melde_bereit=False)
    a.player, a.leser = Aufnahme(), Leser()
    a.toene = Toene(app_modul.STANDARD_TOENE, ["tonprogramm", "{pegel}", "{datei}"], starter=starter,
                    vor=a._ton_vor, nach=a._ton_nach, pegel_quelle=a._ton_pegel)
    await a.starte()
    await a.befehle.join()
    while a.toene.beschaeftigt:
        await asyncio.sleep(0.01)
    journal.clear()
    toene.clear()
    yield a, journal, toene
    await a.beende()


async def sende(a: App, *ereignisse) -> None:
    for e in ereignisse:
        a.ereignisse.put_nowait(e)
    await a._leere_ereignisse()
    await a.befehle.join()
    while a.toene.beschaeftigt:
        await asyncio.sleep(0.01)


async def test_app_einstecken_grenze_vor_ausgang_und_ziehen_zurueck(welt):
    a, journal, _ = welt
    await sende(a, ev.Kopfhoerer(True))
    assert journal == ["lautstaerke 25/25", "ausgang kopfhoerer"]
    assert a.kern.grenzen[GRENZE_KOPFHOERER] == 25
    journal.clear()
    await sende(a, ev.Kopfhoerer(False))
    assert journal == ["lautstaerke 40/60", "ausgang lautsprecher"]
    assert GRENZE_KOPFHOERER not in a.kern.grenzen or a.kern.grenzen[GRENZE_KOPFHOERER] is None


async def test_toene_halten_die_kopfhoerer_grenze_ein(welt):
    """Entscheidung J: Pegel = min(Grenze, ...). Mit Stecker höchstens 25, ohne wieder bis zur Lautstärke (40)."""
    a, _, toene = welt
    await sende(a, ev.Kopfhoerer(True))
    assert (a.grenze, a.lautstaerke) == (25, 25)
    a.toene.spiele("start")
    a.toene.spiele("hinweis")
    a.toene.spiele("fehler")
    await sende(a)
    assert [t for t, _ in toene] == ["start", "hinweis", "fehler"]
    assert all(p <= 25 for _, p in toene), toene
    toene.clear()
    await sende(a, ev.Kopfhoerer(False))
    assert (a.grenze, a.lautstaerke) == (60, 40)
    a.toene.spiele("start")
    await sende(a)
    assert toene == [("start", 40)]


async def test_regler_unter_dem_stecker_bleibt_unter_der_grenze_und_die_toene_folgen(welt):
    a, journal, toene = welt
    await sende(a, ev.Kopfhoerer(True), ev.LautstaerkeDrehen(-35))
    assert (a.grenze, a.lautstaerke) == (25, 5)
    a.toene.spiele("start")
    await sende(a)
    assert toene == [("start", 10)]  # die Untergrenze 10 liegt unter der Grenze 25
    await sende(a, ev.LautstaerkeDrehen(60))
    assert a.lautstaerke == 25  # nie über die Kopfhörer-Grenze


@pytest.mark.parametrize("ton", ["start", "unbekannt", "fehler", "hinweis", "lernen_beginn", "lernen_ende",
                                 "akku_leer", "pruef_ok", "pruef_fehler"])
@pytest.mark.parametrize("grenze, laut", [(5, 5), (5, 0), (25, 25), (25, 100), (0, 0)])
def test_ton_pegel_nie_ueber_der_kopfhoerer_grenze(ton, grenze, laut):
    assert pegel(ton, grenze, laut) <= grenze
