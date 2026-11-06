"""Der Player gegen ein echtes MPD (Null-Ausgabe, eigener Port; siehe ``conftest.py``)."""

from __future__ import annotations

import asyncio
import time

import pytest
from mpd.asyncio import MPDClient

from conftest import abspielen as _abspielen
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
    return _abspielen(serie, serie, datei, pos, vorgang)


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


# --------------------------------------------------------------------------
# Sicherheit beim Verbinden: MPD darf nie von selbst weiterspielen
# --------------------------------------------------------------------------


def _mpd_spielt_mit_zustand_neu(mpd) -> None:
    """Zustand ``play`` mit hoher Lautstärke in die Zustandsdatei schreiben, MPD neu starten."""
    mpd._frage("add lang/a.wav")
    mpd._frage("setvol 90")
    mpd._frage("play 0")
    mpd.stop()  # schreibt state_file
    assert "state: play" in (mpd.verz / "state").read_text()
    mpd.start()


def _status_roh(mpd) -> dict[str, str]:
    return dict(z.split(": ", 1) for z in mpd._frage("status").splitlines() if ": " in z)


async def test_mpd_spielt_nach_neustart_von_selbst_weiter_wird_beim_verbinden_angehalten(mpd_mit_zustand):
    mpd = mpd_mit_zustand
    _mpd_spielt_mit_zustand_neu(mpd)
    # Gegenprobe: ohne Box-Dienst spielt dieses MPD mit hoher Lautstärke von selbst
    vorher = _status_roh(mpd)
    assert vorher["state"] == "play" and int(vorher["volume"]) == 90

    p = Probe(mpd)
    await p.start()
    try:
        st = await p.status()
        assert st["state"] in ("pause", "stop")
        # noch keine Einstellungen: stumm
        assert int(st["volume"]) == 0
        # der Kern sendet die Lautstärke: danach gilt sie (unter der Grenze)
        await p.player.lautstaerke_setzen(20, 50)
        assert int((await p.status())["volume"]) == 20
    finally:
        await p.stop()


async def test_verbinden_mit_bekannter_grenze_klemmt_vor_allem_anderen(mpd_mit_zustand):
    mpd = mpd_mit_zustand
    _mpd_spielt_mit_zustand_neu(mpd)
    p = Probe(mpd)
    await p.player.lautstaerke_setzen(80, 30)  # vor dem Verbinden: Wert 30 (geklemmt)
    await p.start()
    try:
        st = await p.status()
        assert st["state"] in ("pause", "stop")
        assert int(st["volume"]) <= 30
    finally:
        await p.stop()


async def test_lautstaerke_setzen_waehrend_des_verbindens_geht_nicht_verloren(mpd):
    p = Probe(mpd)
    p.player.start()
    for prozent in (10, 15, 20, 25):  # mitten im Verbinden
        await p.player.lautstaerke_setzen(prozent, 50)
        await asyncio.sleep(0)
    assert await p.player.warte_verbunden(5.0)
    await warte(lambda: True)
    await asyncio.sleep(0.2)
    try:
        assert int((await p.status())["volume"]) == 25
    finally:
        await p.stop()


async def test_player_fehler_gleicher_art_gedrosselt(mpd):
    zeit = [0.0]
    p = Probe(mpd, mono=lambda: zeit[0])
    await p.start()
    try:
        await p.player.lautstaerke_setzen(20, 50)
        for _ in range(5):
            await p.player.abspielen(abspielen(datei="gibt-es-nicht.wav"))
        assert len(p.alle(ev.PlayerFehler)) == 1
        zeit[0] = 6.0
        await p.player.abspielen(abspielen(datei="gibt-es-nicht.wav"))
        assert len(p.alle(ev.PlayerFehler)) == 2
    finally:
        await p.stop()


async def test_pausieren_bei_stop_ist_folgenende_kein_fehler(probe, monkeypatch):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(abspielen("kurz", "a.wav"))
    await warte(lambda: probe.alle(ev.FolgeZuEnde), 5.0, "(Folgenende)")  # läuft 1 s
    assert not probe.alle(ev.PlayerFehler)


async def test_pausiere_hart_ohne_serie(mpd):
    mpd._frage("add lang/a.wav")
    mpd._frage("setvol 10")
    mpd._frage("play 0")
    p = Probe(mpd)
    await p.start()
    try:
        # der Player hat beim Verbinden schon angehalten; wieder starten und hart pausieren
        mpd._frage("play 0")
        assert _status_roh(mpd)["state"] == "play"
        assert await p.player.pausiere_hart()
        assert _status_roh(mpd)["state"] in ("pause", "stop")
    finally:
        await p.stop()


async def test_pausiere_hart_ohne_player_verbindung(mpd):
    mpd._frage("add lang/a.wav")
    mpd._frage("play 0")
    from tobibox.player import Player

    pl = Player(lambda e: None, "127.0.0.1", mpd.port)  # nie gestartet: frische Verbindung
    assert await pl.pausiere_hart()
    assert _status_roh(mpd)["state"] in ("pause", "stop")


# --- Folgen mit mehreren Tracks (Entscheidung F, 05.11.) ---------------------------------------

CD3 = ("rip/01.wav", "rip/02.wav", "rip/03.wav")


def ab_tracks(tracks=CD3, track=0, pos=0.0, serie="cdserie", datei="rip", ordner="cdserie", gen=0) -> ev.Abspielen:
    return ev.Abspielen(serie, ordner, datei, tracks, track, pos, "v1", gen)


@pytest.fixture
def cd_medien(mpd):
    """Serie „cdserie“ mit der Folge „rip“: drei kurze Tracks; „lang“ hat zwei lange Tracks."""
    from fixtures import audio

    audio.erzeuge_folge_ordner(mpd.medien / "cdserie", "rip", ["01.wav", "02.wav", "03.wav"], dauer_s=1.0)
    audio.erzeuge_folge_ordner(mpd.medien / "cdlang", "rip", ["01.wav", "02.wav", "03.wav"], dauer_s=30.0)
    mpd.aktualisiere()
    return mpd


async def test_folge_mit_drei_tracks_spielt_durch_track_wechsel_je_wechsel_folge_zu_ende_nur_am_ende(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(ab_tracks())
    st = await probe.status()
    assert st["state"] == "play" and st["playlistlength"] == "3" and st["song"] == "0"
    await warte(lambda: probe.alle(ev.FolgeZuEnde), 10.0, "(FolgeZuEnde nach drei Tracks)")
    wechsel = probe.alle(ev.TrackWechsel)
    assert wechsel == [ev.TrackWechsel("cdserie", "rip", 1), ev.TrackWechsel("cdserie", "rip", 2)]
    assert probe.alle(ev.FolgeZuEnde) == [ev.FolgeZuEnde("cdserie", "rip")]
    # Reihenfolge: Wechsel 1, Wechsel 2, dann (Endposition), dann FolgeZuEnde; FolgeZuEnde zuletzt
    arten = [type(x) for x in probe.e if isinstance(x, (ev.TrackWechsel, ev.FolgeZuEnde))]
    assert arten == [ev.TrackWechsel, ev.TrackWechsel, ev.FolgeZuEnde]
    assert probe.e[-1] == ev.FolgeZuEnde("cdserie", "rip")
    # die Position kommt sofort nach jedem Track-Wechsel mit dem neuen Track
    for w in wechsel:
        i = probe.e.index(w)
        nach = probe.e[i + 1]
        assert isinstance(nach, ev.PlayerPosition) and nach.track == w.track and nach.spielt
    # Positionen tragen den Track; die Endposition gehört zum letzten Track
    spaet = [x for x in probe.alle(ev.PlayerPosition)]
    assert {x.track for x in spaet} == {0, 1, 2}
    ende_pos = probe.e[probe.e.index(probe.alle(ev.FolgeZuEnde)[0]) - 1]
    assert isinstance(ende_pos, ev.PlayerPosition) and ende_pos.track == 2 and not ende_pos.spielt
    # MPD stoppt nach dem letzten Track und spielt nie von selbst weiter
    await asyncio.sleep(1.0)
    st = await probe.status()
    assert st["state"] == "stop" and len(probe.alle(ev.FolgeZuEnde)) == 1
    assert not probe.alle(ev.PlayerFehler)


async def test_resume_per_seek_in_track_2(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(ab_tracks(track=2, pos=12.5, serie="cdlang", ordner="cdlang"))
    st = await probe.status()
    assert st["state"] == "play" and st["playlistlength"] == "3"
    assert st["song"] == "2"  # mitten im dritten Track, nie bei Track 0 begonnen
    assert float(st["elapsed"]) >= 12.5
    erste = probe.alle(ev.PlayerPosition)[0]
    assert erste.track == 2 and erste.position_s >= 12.5
    assert not probe.alle(ev.TrackWechsel)  # der Start ist kein Wechsel


async def test_pause_und_wiederaufnahme_mitten_im_zweiten_track(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(ab_tracks(track=1, pos=5.0, serie="cdlang", ordner="cdlang"))
    await probe.player.pausieren(ev.Pausieren("knopf"))
    pos = probe.alle(ev.PlayerPosition)[-1]
    assert (pos.track, pos.spielt) == (1, False) and pos.position_s >= 5.0
    assert (await probe.status())["state"] == "pause"
    await probe.player.abspielen(ab_tracks(track=1, pos=pos.position_s - 3.0, serie="cdlang", ordner="cdlang"))
    st = await probe.status()
    assert st["state"] == "play" and st["song"] == "1" and float(st["elapsed"]) >= pos.position_s - 3.0


async def test_fehlender_track_in_der_mitte_wird_uebersprungen(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    tracks = ("rip/01.wav", "rip/gibt-es-nicht.wav", "rip/03.wav")
    await probe.player.abspielen(ab_tracks(tracks))
    assert (await probe.status())["playlistlength"] == "2"
    await warte(lambda: probe.alle(ev.FolgeZuEnde), 10.0, "(FolgeZuEnde)")
    # Track-Nummern sind die der Folge: 0 -> 2
    assert probe.alle(ev.TrackWechsel) == [ev.TrackWechsel("cdserie", "rip", 2)]
    assert not probe.alle(ev.PlayerFehler)


async def test_fehlt_der_start_track_beginnt_der_naechste_vorhandene_bei_position_0(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    tracks = ("rip/01.wav", "rip/gibt-es-nicht.wav", "rip/03.wav")
    await probe.player.abspielen(ab_tracks(tracks, track=1, pos=30.0, serie="cdlang", ordner="cdlang"))
    st = await probe.status()
    assert st["state"] == "play" and st["song"] == "1"  # Warteschlange: 01 (0), 03 (1)
    assert float(st["elapsed"]) < 5.0  # Position gilt nur für den gewünschten Track
    assert probe.alle(ev.PlayerPosition)[0].track == 2


async def test_fehlt_der_letzte_track_endet_die_folge_nach_dem_vorletzten(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    tracks = ("rip/01.wav", "rip/02.wav", "rip/gibt-es-nicht.wav")
    await probe.player.abspielen(ab_tracks(tracks))
    await warte(lambda: probe.alle(ev.FolgeZuEnde), 10.0, "(FolgeZuEnde)")
    assert probe.alle(ev.TrackWechsel) == [ev.TrackWechsel("cdserie", "rip", 1)]
    assert not probe.alle(ev.PlayerFehler)


async def test_fehlt_alles_ab_dem_start_track_ist_das_ende_der_folge(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    tracks = ("rip/01.wav", "rip/02.wav", "rip/gibt-es-nicht.wav")
    await probe.player.abspielen(ab_tracks(tracks, track=2))
    assert probe.alle(ev.FolgeZuEnde) == [ev.FolgeZuEnde("cdserie", "rip")]
    assert (await probe.status())["state"] == "stop"
    assert not probe.alle(ev.PlayerFehler)


async def test_fehlt_jeder_track_ist_es_ein_player_fehler(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(ab_tracks(("rip/a.wav", "rip/b.wav")))
    assert [x.art for x in probe.alle(ev.PlayerFehler)] == ["datei_fehlt"]
    assert not probe.alle(ev.FolgeZuEnde)


async def test_unlesbarer_track_nicht_im_mpd_bestand_wird_uebersprungen(cd_medien, probe):
    from fixtures import audio

    ordner = audio.erzeuge_folge_ordner(cd_medien.medien / "cdmuell", "rip", ["01.wav", "03.wav"], dauer_s=1.0)
    (ordner / "02.wav").write_bytes(b"kein wav" * 50)  # Müll: MPD nimmt ihn nicht in den Bestand auf
    cd_medien.aktualisiere()
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(ab_tracks(serie="cdmuell", ordner="cdmuell"))
    assert (await probe.status())["playlistlength"] == "2"
    await warte(lambda: probe.alle(ev.FolgeZuEnde), 10.0, "(FolgeZuEnde)")
    assert probe.alle(ev.TrackWechsel) == [ev.TrackWechsel("cdmuell", "rip", 2)]
    assert not probe.alle(ev.PlayerFehler)


async def test_track_nach_dem_einlesen_geloescht_mpd_ueberspringt_ihn_ohne_fehler(cd_medien):
    """Ohne Prüfung im Player (kein Medienordner): MPD springt über die fehlende Datei."""
    p = Probe(cd_medien)
    p.player = Player(p.e.append, "127.0.0.1", cd_medien.port, medien=None, abfrage_s=0.05)
    await p.start()
    try:
        (cd_medien.medien / "cdserie" / "rip" / "02.wav").unlink()  # MPD kennt sie noch
        await p.player.lautstaerke_setzen(20, 50)
        await p.player.abspielen(ab_tracks())
        await warte(lambda: p.alle(ev.FolgeZuEnde), 10.0, "(FolgeZuEnde)")
        assert p.alle(ev.TrackWechsel) == [ev.TrackWechsel("cdserie", "rip", 2)]
        assert not p.alle(ev.PlayerFehler)
    finally:
        await p.stop()


async def test_letzter_track_nach_dem_einlesen_geloescht_ist_das_ende_der_folge_kein_fehler(cd_medien):
    p = Probe(cd_medien)
    p.player = Player(p.e.append, "127.0.0.1", cd_medien.port, medien=None, abfrage_s=0.05)
    await p.start()
    try:
        (cd_medien.medien / "cdserie" / "rip" / "03.wav").unlink()
        await p.player.lautstaerke_setzen(20, 50)
        await p.player.abspielen(ab_tracks())
        await warte(lambda: p.alle(ev.FolgeZuEnde), 10.0, "(FolgeZuEnde)")
        assert p.alle(ev.TrackWechsel) == [ev.TrackWechsel("cdserie", "rip", 1)]
        assert not p.alle(ev.PlayerFehler)
        assert (await p.status())["state"] == "stop"
    finally:
        await p.stop()


async def test_einzige_datei_nach_dem_einlesen_geloescht_bleibt_ein_player_fehler(mpd):
    """Eine Folge aus einer Datei hat keinen „nächsten Track“: weiter ``datei_unlesbar``."""
    p = Probe(mpd)
    p.player = Player(p.e.append, "127.0.0.1", mpd.port, medien=None, abfrage_s=0.05)
    await p.start()
    try:
        (mpd.medien / "kurz" / "a.wav").unlink()
        await p.player.lautstaerke_setzen(20, 50)
        await p.player.abspielen(abspielen("kurz", "a.wav"))
        await warte(lambda: p.alle(ev.PlayerFehler), 6.0, "(PlayerFehler)")
        assert not p.alle(ev.FolgeZuEnde)
    finally:
        await p.stop()


async def test_warteschlange_enthaelt_nur_die_tracks_der_aktuellen_folge(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(ab_tracks(serie="cdlang", ordner="cdlang"))
    await probe.player.abspielen(abspielen("lang", "a.wav"))
    st = await probe.status()
    assert st["playlistlength"] == "1" and st["state"] == "play"


async def test_fehlt_der_erste_track_meldet_der_player_track_wechsel_auf_den_spielenden_track(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    tracks = ("rip/gibt-es-nicht.wav", "rip/02.wav", "rip/03.wav")
    await probe.player.abspielen(ab_tracks(tracks, track=0, gen=4))
    assert probe.alle(ev.TrackWechsel) == [ev.TrackWechsel("cdserie", "rip", 1)]  # sofort, vor der ersten Position
    assert probe.alle(ev.TrackWechsel)[0].gen == 4
    assert probe.e.index(probe.alle(ev.TrackWechsel)[0]) < probe.e.index(probe.alle(ev.PlayerPosition)[0])
    assert probe.alle(ev.PlayerPosition)[0].track == 1
    await warte(lambda: probe.alle(ev.FolgeZuEnde), 10.0, "(FolgeZuEnde)")
    assert [w.track for w in probe.alle(ev.TrackWechsel)] == [1, 2]  # kein zweiter Wechsel auf Track 1
    assert not probe.alle(ev.PlayerFehler)


async def test_alle_ereignisse_tragen_die_generation_des_letzten_abspielen(cd_medien, probe):
    await probe.player.lautstaerke_setzen(20, 50)
    await probe.player.abspielen(ab_tracks(gen=7))
    await warte(lambda: probe.alle(ev.FolgeZuEnde), 10.0, "(FolgeZuEnde)")
    spiel = probe.alle(ev.PlayerPosition) + probe.alle(ev.TrackWechsel) + probe.alle(ev.FolgeZuEnde)
    assert spiel and {e.gen for e in spiel} == {7}
    await probe.player.abspielen(ab_tracks(gen=8))
    assert probe.alle(ev.PlayerPosition)[-1].gen == 8
