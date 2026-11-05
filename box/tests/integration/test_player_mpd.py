"""Der Player gegen ein echtes MPD (Null-Ausgabe, eigener Port; siehe ``conftest.py``)."""

from __future__ import annotations

import asyncio
import time

import pytest
from mpd.asyncio import MPDClient

from tobibox import events as ev
from tobibox.player import Player


async def warte(bedingung, timeout: float = 6.0, text: str = "") -> None:
    ende = time.monotonic() + timeout
    while time.monotonic() < ende:
        if bedingung():
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"Bedingung nicht rechtzeitig erfüllt {text}")


class Probe:
    """Player mit gesammelten Ereignissen und eigenem MPD-Client zum Nachsehen."""

    def __init__(self, mpd, **kw) -> None:
        self.mpd = mpd
        self.e: list[ev.Ereignis] = []
        self.player = Player(self.e.append, "127.0.0.1", mpd.port, medien=mpd.medien, abfrage_s=0.05, **kw)

    def alle(self, typ: type) -> list:
        return [x for x in self.e if isinstance(x, typ)]

    async def start(self) -> None:
        self.player.start()
        assert await self.player.warte_verbunden(5.0)

    async def status(self) -> dict:
        c = MPDClient()
        await c.connect("127.0.0.1", self.mpd.port)
        try:
            return dict(await c.status())
        finally:
            c.disconnect()

    async def stop(self) -> None:
        await self.player.stop()


@pytest.fixture
async def probe(mpd):
    p = Probe(mpd)
    await p.start()
    yield p
    await p.stop()


def abspielen(serie="lang", datei="a.wav", pos=0.0, vorgang="v1") -> ev.Abspielen:
    return ev.Abspielen(serie, serie, datei, pos, vorgang)


async def test_ohne_lautstaerke_wird_nicht_gespielt(probe):
    await probe.player.abspielen(abspielen())
    f = probe.alle(ev.PlayerFehler)
    assert f and f[0].art == "mpd_fehler" and "Lautstaerke" in f[0].detail
    assert (await probe.status())["state"] == "stop"


async def test_lautstaerke_vor_abspielen_und_start(probe):
    await probe.player.lautstaerke_setzen(30, 40)
    await probe.player.abspielen(abspielen())
    st = await probe.status()
    assert st["state"] == "play"
    assert int(st["volume"]) == 30
    # Einstellungen: nichts spielt von selbst weiter
    assert (st["repeat"], st["random"], st["single"], st["consume"]) == ("0", "0", "0", "0")
    pos = probe.alle(ev.PlayerPosition)
    assert pos and pos[0].spielt and (pos[0].serie_id, pos[0].datei) == ("lang", "a.wav")


async def test_position_jede_sekunde_und_pause(probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(abspielen())
    await warte(lambda: len(probe.alle(ev.PlayerPosition)) >= 3, 5.0, "(3 Positionen)")
    spielend = [p for p in probe.alle(ev.PlayerPosition) if p.spielt]
    assert [p.position_s for p in spielend] == sorted(p.position_s for p in spielend)
    assert spielend[-1].position_s >= 1.0

    anzahl = len(probe.e)
    await probe.player.pausieren(ev.Pausieren("knopf"))
    assert (await probe.status())["state"] == "pause"
    sofort = probe.e[anzahl]  # sofort nach Pausieren, mit spielt=False
    assert isinstance(sofort, ev.PlayerPosition) and not sofort.spielt
    # in der Pause keine weiteren Positionen
    n = len(probe.alle(ev.PlayerPosition))
    await asyncio.sleep(1.3)
    assert len(probe.alle(ev.PlayerPosition)) == n


async def test_resume_per_seek_ohne_anspielen_bei_null(probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(abspielen(pos=12.5))
    st = await probe.status()
    assert st["state"] == "play"
    assert float(st["elapsed"]) >= 12.5  # nie bei 0:00 begonnen
    erste = probe.alle(ev.PlayerPosition)[0]
    assert erste.position_s >= 12.5
    assert (await probe.status())["playlistlength"] == "1"


async def test_warteschlange_enthaelt_nur_die_aktuelle_folge(probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(abspielen(datei="a.wav"))
    await probe.player.abspielen(abspielen(datei="b.wav", pos=3.0))
    st = await probe.status()
    assert st["playlistlength"] == "1" and st["state"] == "play"
    assert float(st["elapsed"]) >= 3.0


async def test_folgenende_mpd_stoppt_und_nichts_spielt_weiter(probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(abspielen("kurz", "a.wav"))
    await warte(lambda: probe.alle(ev.FolgeZuEnde), 5.0, "(FolgeZuEnde)")
    ende = probe.alle(ev.FolgeZuEnde)
    assert ende == [ev.FolgeZuEnde("kurz", "a.wav")]
    # vor FolgeZuEnde kam die Endposition
    i = probe.e.index(ende[0])
    letzte = probe.e[i - 1]
    assert isinstance(letzte, ev.PlayerPosition) and not letzte.spielt and letzte.position_s >= 0.9
    # Pausieren nach Folgenende ist wirkungslos
    await probe.player.pausieren(ev.Pausieren("folgenende"))
    await asyncio.sleep(1.5)
    st = await probe.status()
    assert st["state"] == "stop" and st["playlistlength"] == "1"
    assert len(probe.alle(ev.FolgeZuEnde)) == 1
    assert not probe.alle(ev.PlayerFehler)


async def test_lautstaerke_nie_ueber_der_grenze(probe):
    await probe.player.lautstaerke_setzen(90, 30)  # Wunsch über der Grenze
    assert int((await probe.status())["volume"]) == 30
    await probe.player.abspielen(abspielen())
    # jemand dreht MPD von außen höher: der Dienst setzt zurück
    c = MPDClient()
    await c.connect("127.0.0.1", probe.mpd.port)
    await c.setvol(95)
    c.disconnect()
    async def klemmt():
        return int((await probe.status())["volume"]) <= 30
    for _ in range(100):
        if await klemmt():
            break
        await asyncio.sleep(0.05)
    assert await klemmt()


async def test_lautstaerke_nach_neustart_des_dienstes(mpd):
    # MPD behält 95 vom vorigen Dienst
    c = MPDClient()
    await c.connect("127.0.0.1", mpd.port)
    await c.setvol(95)
    c.disconnect()

    neu = Probe(mpd)
    await neu.start()
    try:
        # ohne Lautstärke kein Abspielen
        await neu.player.abspielen(abspielen())
        assert (await neu.status())["state"] == "stop"
        # wie der Kern: erst LautstaerkeSetzen, dann Abspielen
        await neu.player.lautstaerke_setzen(95, 35)
        await neu.player.abspielen(abspielen())
        st = await neu.status()
        assert st["state"] == "play" and int(st["volume"]) <= 35
    finally:
        await neu.stop()


async def test_datei_fehlt(probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(abspielen(datei="gibt-es-nicht.wav"))
    f = probe.alle(ev.PlayerFehler)
    assert [(x.art, x.serie_id, x.datei) for x in f] == [("datei_fehlt", "lang", "gibt-es-nicht.wav")]
    assert (await probe.status())["state"] == "stop"


async def test_datei_nicht_im_mpd_bestand(mpd, probe):
    from fixtures import audio

    audio.schreibe_wav(mpd.medien / "lang" / "neu.wav", 2.0)  # liegt da, MPD kennt sie noch nicht
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(abspielen(datei="neu.wav"))
    # der Player aktualisiert den Bestand einmal selbst und spielt dann
    assert (await probe.status())["state"] == "play"
    assert not probe.alle(ev.PlayerFehler)


async def test_defekte_datei_ist_ein_fehler(mpd, probe):
    (mpd.medien / "lang" / "kaputt.wav").write_bytes(b"das ist kein Audio" * 50)
    mpd.aktualisiere()
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(abspielen(datei="kaputt.wav"))
    await warte(lambda: probe.alle(ev.PlayerFehler), 5.0, "(PlayerFehler)")
    # MPD nimmt nicht dekodierbare Dateien nicht in den Bestand: "datei_fehlt"; sonst "datei_unlesbar"
    assert probe.alle(ev.PlayerFehler)[0].art in ("datei_fehlt", "datei_unlesbar")
    assert not probe.alle(ev.FolgeZuEnde)
    assert (await probe.status())["state"] == "stop"


async def test_mpd_weg_und_zurueck(mpd, probe):
    await probe.player.lautstaerke_setzen(25, 50)
    await probe.player.abspielen(abspielen())
    mpd.stop()
    await warte(lambda: probe.alle(ev.PlayerVerbindung), 6.0, "(Verbindung weg)")
    assert probe.alle(ev.PlayerVerbindung) == [ev.PlayerVerbindung(False)]
    assert not probe.alle(ev.FolgeZuEnde)  # Verlust ist keine fertige Folge
    # MPD wieder da (gleicher Port)
    mpd.start()
    await warte(lambda: len(probe.alle(ev.PlayerVerbindung)) == 2, 8.0, "(Verbindung zurück)")
    assert probe.alle(ev.PlayerVerbindung)[1] == ev.PlayerVerbindung(True)
    mpd.aktualisiere()
    # beim Verbinden wird zuerst die Lautstärke gesetzt, dann kann der Kern neu abspielen
    assert int((await probe.status())["volume"]) == 25
    await probe.player.abspielen(abspielen(pos=5.0))
    assert (await probe.status())["state"] == "play"
    assert not probe.alle(ev.FolgeZuEnde)
