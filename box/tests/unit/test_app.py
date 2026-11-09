"""``App``: Start wartet auf MPD, Beenden ist robust (Fake-Player, kein MPD nötig)."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging

import pytest
from conftest import UID_S1, KernHarnisch
from fixtures.audio import erzeuge_medien

from tobibox import app as app_modul
from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox.app import App


class FakePlayer:
    def __init__(self, verbunden=True, stop_fehler=False):
        self.verbunden = verbunden
        self.stop_fehler = stop_fehler
        self.aufrufe: list[str] = []
        self.beim_warten: list[str] = []
        self.app: App | None = None

    def start(self):
        self.aufrufe.append("start")

    async def warte_verbunden(self, timeout_s=5.0):
        self.aufrufe.append(f"warte {timeout_s}")
        await asyncio.sleep(0.05)  # die Ereignisschleife kommt zum Zug
        self.beim_warten = list(self.app.gesehen)  # type: ignore[union-attr]
        return self.verbunden

    async def pausiere_hart(self):
        self.aufrufe.append("pause_hart")
        return True

    async def stop(self):
        self.aufrufe.append("stop")
        if self.stop_fehler:
            raise RuntimeError("player kaputt")

    async def lautstaerke_setzen(self, *a):
        pass


class FakeLeser:
    def __init__(self, stop_fehler=False):
        self.stop_fehler = stop_fehler
        self.gestoppt = False

    def start(self):
        pass

    async def stop(self):
        self.gestoppt = True
        if self.stop_fehler:
            raise RuntimeError("leser kaputt")

    def ping(self):
        pass


class FakeToene:
    def __init__(self):
        self.gestoppt = False

    async def stop(self):
        self.gestoppt = True


@pytest.fixture
def app(tmp_path, kurz, monkeypatch):
    medien = erzeuge_medien(tmp_path / "medien")
    zustand = kurz / "var"  # ``sim.sock`` liegt darin: kurzer Pfad (macOS)
    zustand.mkdir()
    toml = tmp_path / "tobibox.toml"
    toml.write_text(f'[pfade]\nzustand = "{zustand}"\nmedien = "{medien}"\n', encoding="utf-8")
    monkeypatch.setattr(app_modul.notify, "stoppt", lambda: None)
    a = App(konfig_modul.lade(toml), melde_bereit=False)
    a.player = FakePlayer()
    a.player.app = a
    a.leser = FakeLeser()
    a.toene = FakeToene()
    a.gesehen = []
    orig = a.verarbeite

    def verarbeite(e):
        a.gesehen.append(type(e).__name__)
        return orig(e)

    a.verarbeite = verarbeite
    return a


def setze_modus(a: App, modus: str) -> None:
    teil = {**a.kern.teil, "session": dataclasses.replace(a.kern.session, modus=modus)}
    a.kern = dataclasses.replace(a.kern, teil=teil)


async def test_starte_wartet_auf_mpd_vor_bereit(app):
    await app.starte()
    try:
        assert app.player.aufrufe[1] == f"warte {app_modul.VERBINDEN_WARTEN_S}"
        assert app_modul.VERBINDEN_WARTEN_S == 10.0
        assert "GeraeteEinstellungen" in app.player.beim_warten
        assert "Bereit" not in app.player.beim_warten
        assert "Bereit" in app.gesehen
    finally:
        await app.beende()


async def test_starte_ohne_mpd_startet_trotzdem_mit_warnung(app, caplog):
    app.player.verbunden = False
    with caplog.at_level(logging.WARNING, logger="tobibox"):
        await app.starte()
    try:
        assert "Bereit" in app.gesehen and app.bereit.is_set()
        assert any(r.levelname == "WARNING" and getattr(r, "ereignis", "") == "start" for r in caplog.records)
    finally:
        await app.beende()


async def test_starte_fehler_raeumt_auf(app, monkeypatch):
    def kaputt(*a, **k):
        raise RuntimeError("medien kaputt")

    monkeypatch.setattr(app_modul.library, "lade_bibliothek", kaputt)
    with pytest.raises(RuntimeError):
        await app.starte()
    assert "stop" in app.player.aufrufe and "pause_hart" in app.player.aufrufe
    assert app.toene.gestoppt and app.leser.gestoppt


@pytest.mark.parametrize("modus", ["spielt", "unbekannt"])
async def test_beende_sendet_dienst_endet_nicht_herunterfahren(app, modus):
    setze_modus(app, modus)
    verarbeitet: list = []
    app.verarbeite = lambda e: verarbeitet.append(e) or ()
    app._aufgaben = [asyncio.create_task(app._ereignisschleife())]
    await app.beende()
    assert verarbeitet == [ev.DienstEndet()]
    assert not any(isinstance(e, (ev.HerunterfahrenAngefordert, ev.Herunterfahren)) for e in verarbeitet)
    assert "pause_hart" in app.player.aufrufe


@pytest.mark.parametrize("modus", ["leer", "pausiert"])
async def test_beende_sendet_hart_pause_auch_ohne_wiedergabe(app, modus):
    setze_modus(app, modus)
    await app.beende()
    assert "pause_hart" in app.player.aufrufe and "stop" in app.player.aufrufe


async def test_beende_schritte_laufen_unabhaengig(app):
    app.leser = FakeLeser(stop_fehler=True)
    app.player = FakePlayer(stop_fehler=True)
    await app.beende()
    assert "pause_hart" in app.player.aufrufe
    assert "stop" in app.player.aufrufe
    assert app.toene.gestoppt


# --- Marker lauf.json und Dienst-Neustart (Entscheidung G, 06.11.) ---------------------------------


def neue_app(vorlage: App, boot_id) -> App:
    a = App(vorlage.konfig, melde_bereit=False, boot_id=lambda: boot_id)
    a.player = FakePlayer()
    a.player.app = a
    a.leser = FakeLeser()
    a.toene = FakeToene()
    a.gesehen = []
    return a


def marker_datei(a: App):
    return a.konfig.pfade.zustand / "lauf.json"


async def lege_auf(a: App, uid: str = "04a1b2c3") -> None:
    a.ereignisse.put_nowait(ev.Aufgelegt(uid, "ntag", False, 0, "v1"))
    await a._leere_ereignisse()


async def test_marker_wird_beim_auflegen_geschrieben_ohne_dienst_ende(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        assert not marker_datei(a).exists()  # beim Start ohne Tobie nichts schreiben
        await lege_auf(a)
        assert json.loads(marker_datei(a).read_text()) == {"boot_id": "boot-A", "uid": "04a1b2c3"}
        a.ereignisse.put_nowait(ev.Abgehoben(1, "v1"))
        await a._leere_ereignisse()
        assert json.loads(marker_datei(a).read_text()) == {"boot_id": "boot-A", "uid": None}
    finally:
        await a.beende()


async def test_neustart_mit_gleicher_boot_id_gibt_neustart_uid_an_den_kern(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    await lege_auf(a)
    # Absturz: kein beende(), der Marker vom Auflegen bleibt
    b = neue_app(app, "boot-A")
    await b.starte()
    try:
        assert b.kern.session.neustart_uid == "04a1b2c3"
        assert json.loads(marker_datei(b).read_text())["uid"] == "04a1b2c3"  # Start überschreibt ihn nicht
    finally:
        await b.beende()
        await a._raeume_auf()


async def test_neustart_mit_anderer_boot_id_ist_einschalten(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    await lege_auf(a)
    await a.beende()
    b = neue_app(app, "boot-B")
    await b.starte()
    try:
        assert b.kern.session.neustart_uid is None
    finally:
        await b.beende()


async def test_dienst_ende_schreibt_den_marker(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    await lege_auf(a)
    marker_datei(a).unlink()
    await a.beende()
    assert json.loads(marker_datei(a).read_text()) == {"boot_id": "boot-A", "uid": "04a1b2c3"}


async def test_unlesbarer_marker_ist_einschalten(app):
    marker_datei(app).write_text("{kaputt")
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        assert a.kern.session.neustart_uid is None
    finally:
        await a.beende()


async def test_herunterfahren_loescht_den_marker_und_schreibt_ihn_nicht_wieder(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    await lege_auf(a)
    assert marker_datei(a).exists()
    await a._fuehre_aus(ev.Herunterfahren("hauptknopf"), 0.0)
    assert not marker_datei(a).exists()
    a.ereignisse.put_nowait(ev.Abgehoben(1, "v1"))
    await a._leere_ereignisse()
    await a.beende()
    assert not marker_datei(a).exists()


async def test_ohne_lesbare_boot_id_wird_kein_marker_geschrieben(app):
    a = neue_app(app, None)
    await a.starte()
    try:
        await lege_auf(a)
        assert not marker_datei(a).exists() and a.kern.session.neustart_uid is None
    finally:
        await a.beende()


# --------------------------------------------------------------------------
# Stufe 2: Ausgang (unknown.json), sim, HA-Ersatz, Status
# --------------------------------------------------------------------------


def unknown(a: App) -> dict:
    p = a.konfig.pfade.zustand / "unknown.json"
    return json.loads(p.read_text())["eintraege"] if p.exists() else {}


async def test_unbekannter_tobie_wird_in_unknown_json_eingetragen_und_bleibt_ueber_den_neustart(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        await lege_auf(a, "04ffeedd")
        await a.befehle.join()
        await a.outbox.warte_gespeichert()
        assert unknown(a)["04ffeedd"]["art"] == "unbekannt"
    finally:
        await a.beende()
    b = neue_app(app, "boot-B")
    await b.starte()
    try:
        assert [e.uid for e in b.outbox.offen()] == ["04ffeedd"]
    finally:
        await b.beende()


async def test_bestaetigt_loescht_erst_mit_passendem_zuletzt(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        await lege_auf(a, "04ffeedd")
        await a.befehle.join()
        await a.outbox.warte_gespeichert()
        zuletzt = unknown(a)["04ffeedd"]["zuletzt"]
        a.ereignisse.put_nowait(ev.Bestaetigt("04ffeedd", "neu", "2000-01-01T00:00:00.000Z", "unbekannt"))
        await a._leere_ereignisse()
        await a.outbox.warte_gespeichert()
        assert "04ffeedd" in unknown(a)
        a.ereignisse.put_nowait(ev.Bestaetigt("04ffeedd", "neu", zuletzt, "unbekannt"))
        await a._leere_ereignisse()
        await a.outbox.warte_gespeichert()
        assert unknown(a) == {}
    finally:
        await a.beende()


async def test_sim_start_fehler_stoppt_den_dienst_nicht(app, caplog):
    """Befund 2: Pfad zu lang (``AF_UNIX``) o. ä. -> ERROR im Protokoll, die Box läuft ohne ``sim`` weiter."""
    app.sim.pfad = app.sim.zustand / ("x" * 150)
    with caplog.at_level(logging.WARNING, logger="tobibox"):
        await app.starte()
    try:
        assert app.bereit.is_set()
        (r,) = [r for r in caplog.records if getattr(r, "ereignis", "") == "sim_start"]
        assert r.levelname == "ERROR" and "ohne Simulations-Treiber" in r.meldung
        assert app._aufgaben and not app.sim.pfad.exists()
    finally:
        await app.beende()


async def test_sim_start_permission_error_stoppt_den_dienst_nicht(app, monkeypatch, caplog):
    async def verboten():
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(app.sim, "start", verboten)
    with caplog.at_level(logging.ERROR, logger="tobibox"):
        await app.starte()
    try:
        assert app.bereit.is_set() and any(getattr(r, "ereignis", "") == "sim_start" for r in caplog.records)
    finally:
        await app.beende()


async def test_sim_socket_lebt_waehrend_der_dienst_laeuft_und_ist_danach_weg(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    pfad = a.sim.pfad
    assert pfad.exists()
    await a.beende()
    assert not pfad.exists()


async def test_lernen_ueber_sim_ordnet_zu_bestaetigt_und_loescht_den_eintrag(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        e = a.sim.zeile_zu_ereignis(json.dumps({"befehl": "learn", "typ": "serie", "serie": "3f9a1c07b2d4"}))
        a.ereignisse.put_nowait(e)
        await a._leere_ereignisse()
        assert a.kern.teil["learn"].modus == "lernt"
        await lege_auf(a, "04ffeedd")
        await a.befehle.join()  # Ausführer: melden, HA-Ersatz schreibt und bestätigt
        await a._leere_ereignisse()
        await a.befehle.join()
        await a.outbox.warte_gespeichert()  # das Löschen des Eintrags schreibt asynchron
        assert unknown(a) == {}
        k = json.loads((a.konfig.pfade.zustand / "config.json").read_text())
        assert k["zuordnungen"]["04ffeedd"]["ziel"] == {"typ": "serie", "serie": "3f9a1c07b2d4"}
        assert a.kern.teil["learn"].modus == "aus"
    finally:
        await a.beende()


async def test_status_auskunft_enthaelt_status_pruefpunkte_und_offene_meldungen(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        await lege_auf(a, "04ffeedd")
        await a.befehle.join()
        r = a.status_auskunft()
        assert r["status"]["zustand"] in ("spielt", "pausiert") and r["status"]["serie"]["id"] == "c07d2e91a45b"
        assert [p["name"] for p in r["pruefpunkte"]["punkte"]] == ["leser", "medien", "netz", "speicher"]
        assert [o["uid"] for o in r["offen"]] == ["04ffeedd"]
        json.dumps(r)  # muss über den Socket gehen können
    finally:
        await a.beende()


# --- Töne folgen der Lautstärke der Sitzung (Entscheidung J, 09.11.) --------------------------------


class TonSpion:
    """Merkt sich, was ``App`` an die Tonspur übergibt."""

    def __init__(self) -> None:
        self.aufrufe: list[tuple] = []
        self.gestoppt = False

    def spiele(self, ton, grenze=None, lautstaerke=None, hinweis_pegel=None) -> bool:
        self.aufrufe.append((ton, grenze, lautstaerke, hinweis_pegel))
        return True

    def spiele_folge(self, toene, grenze=None, lautstaerke=None, hinweis_pegel=None) -> bool:
        self.aufrufe.append((tuple(toene), grenze, lautstaerke, hinweis_pegel))
        return True

    async def stop(self):
        self.gestoppt = True


def mit_echtem_kern(app) -> KernHarnisch:
    """Der Dienst arbeitet mit dem Zustand eines echten Kerns (Gerätewerte 60/40/25, Tobie ``UID_S1`` bekannt)."""
    k = KernHarnisch()
    app.kern, app.uhr = k.z, k.uhr
    return k


async def test_ton_wird_ohne_feste_pegelwerte_uebergeben_der_pegel_kommt_erst_beim_abspielen(app):
    # B6: ``App`` übergibt nur den Ton; die Tonspur holt Grenze und Lautstärke aus ``pegel_quelle``, wenn er dran ist
    assert App(app.konfig, melde_bereit=False).toene._pegel_quelle is not None
    app.toene = TonSpion()
    await app._fuehre_aus(ev.TonSpielen("start"), 0.0)
    assert app.toene.aufrufe[-1] == ("start", None, None, None)


def test_ton_pegel_vor_dem_ersten_befehl_aus_der_konfiguration(app):
    assert app._ton_pegel() == (
        app.konfig.lautstaerke.max,
        min(app.konfig.lautstaerke.start, app.konfig.lautstaerke.max),
        None,
    )


def test_ton_pegel_folgt_dem_echten_kern_ueber_alle_grenzen(app):
    k = mit_echtem_kern(app)
    app.verarbeite(ev.GeraeteEinstellungen(60, 40, 25))
    assert app._ton_pegel() == (60, 40, None)
    app.verarbeite(ev.Kopfhoerer(True))  # Kopfhörer-Grenze 25 senkt die Lautstärke
    assert app._ton_pegel() == (25, 25, None)
    app.verarbeite(ev.LautstaerkeDrehen(-10))  # 40 - 10 klemmt auf 25, dann 25 - 10
    app.verarbeite(ev.LautstaerkeDrehen(-10))
    assert app._ton_pegel() == (25, 15, None)
    app.verarbeite(ev.Kopfhoerer(False))
    assert app._ton_pegel()[0] == 60
    assert k.z is not app.kern  # der Dienst führt den Kern selbst weiter


def test_ton_pegel_nach_stumm_ausblenden_bleibt_hoerbar(app):
    """B2: Der Weg Kern → ``App.lautstaerke``/``App.grenze`` → Pegel, mit echtem Kern und echter Rampe."""
    from tobibox.sounds import pegel

    k = mit_echtem_kern(app)
    app.verarbeite(ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1"))
    soll = app._ton_pegel()
    assert soll[:2] == (60, 40)
    app.verarbeite(ev.StummBeginnt())
    sah_rampe = False
    for _ in range(40):  # 4 s Takt: die Rampe (3 s) läuft ab, die Grenze „ausblenden“ wird gelöscht
        app.uhr.vor(0.1)
        for b in app.verarbeite(ev.Takt()):
            sah_rampe = sah_rampe or isinstance(b, ev.LautstaerkeSetzen) and b.grenze < 40
        assert app._ton_pegel()[:2] == soll[:2]  # die Rampe berührt den Ton-Pegel nie
    assert sah_rampe  # der Kern hat die Rampe wirklich ausgegeben
    assert app.kern.session.modus == "gehalten"  # stumm: Hörspiel angehalten, Anstieg zurückgehalten
    assert pegel("pruef_ok", *app._ton_pegel()) == 40  # nicht 1


def test_hinweis_pegel_kommt_aus_der_konfiguration_ton_pegel_wird_ignoriert(app):
    app.konfig_store.roh = {**app.konfig_store.roh, "ton_pegel": 90, "hinweis_pegel": 22}
    mit_echtem_kern(app)
    app.verarbeite(ev.GeraeteEinstellungen(60, 40, 25))
    assert app._ton_pegel() == (60, 40, 22)  # kein ton_pegel in der Übergabe


def test_app_baut_die_kennlinie_aus_der_konfiguration(app):
    assert App(app.konfig, melde_bereit=False).toene.kennlinie.art == konfig_modul.KENNLINIE_MPD_SOFTWARE  # Vorgabe: Mac
    k = dataclasses.replace(
        app.konfig,
        toene=dataclasses.replace(app.konfig.toene, kennlinie="alsa_softvol", softvol_bereich_db=40.0),
    )
    a = App(k, melde_bereit=False)
    assert (a.toene.kennlinie.art, a.toene.kennlinie.softvol_bereich_db) == ("alsa_softvol", 40.0)


# --- Simulierter Tobie neben dem echten Leser (mac-prototyp.md, „Der Leser darf parallel zur Simulation laufen“) ---


def _herzschlag(present: bool) -> ev.LeserHerzschlag:
    return ev.LeserHerzschlag(present, 10, 100, 0, 0, 0, 50)


async def _sim_auflegen(a: App, uid: str = "04a1b2c3") -> None:
    antwort = await a.sim.verarbeite(json.dumps({"befehl": "tobie_auflegen", "uid": uid}))
    assert antwort["ok"] is True
    await a._leere_ereignisse()


async def _echte(a: App, *ereignisse: ev.Ereignis) -> None:
    for e in ereignisse:
        a.ereignisse.put_nowait(e)  # nicht über ``sim``: wie vom echten Leser
    await a._leere_ereignisse()


def _sammle_befehle(a: App) -> list[ev.Befehl]:
    befehle: list[ev.Befehl] = []
    orig = a.verarbeite

    def sammle(e):
        b = orig(e)
        befehle.extend(b)
        return b

    a.verarbeite = sammle
    return befehle


async def test_simulierter_tobie_bleibt_trotz_leermeldungen_des_echten_lesers_liegen(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        await _sim_auflegen(a)
        assert a.kern.session.figur is not None
        modus = a.kern.session.modus
        vorgang = a.kern.session.figur.vorgang
        befehle = _sammle_befehle(a)
        # Der Leser sagt „nichts da“: Herzschlag, Neuverbindung (HELLO), Ausfall, noch ein Herzschlag
        await _echte(a, _herzschlag(False), _herzschlag(False), _herzschlag(False))
        await _echte(a, ev.LeserHallo(1, "fw", "b", "pn"), _herzschlag(False), _herzschlag(False), _herzschlag(False))
        await _echte(a, ev.LeserAlarm("kein_herzschlag"), ev.LeserHallo(1, "fw", "b", "pn"), _herzschlag(False))
        assert a.kern.session.figur is not None and a.kern.session.figur.vorgang == vorgang
        assert a.kern.session.modus == modus
        assert not any(isinstance(b, ev.LeserPing) for b in befehle)
        assert not any(isinstance(b, ev.Pausieren) for b in befehle)
    finally:
        await a.beende()


async def test_simulierter_tobie_wird_nur_per_simulation_abgehoben(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        await _sim_auflegen(a)
        await _echte(a, ev.Abgehoben(7, "irgendwas"))  # ein verirrtes REMOVED des echten Lesers
        assert a.kern.session.figur is not None
        antwort = await a.sim.verarbeite(json.dumps({"befehl": "tobie_abheben"}))
        assert antwort["ok"] is True
        await a._leere_ereignisse()
        assert a.kern.session.figur is None
        assert a.kern.session.modus == "pausiert"
    finally:
        await a.beende()


async def test_echter_tobie_loest_den_simulierten_ab_und_danach_gilt_der_leser_wieder(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        await _sim_auflegen(a)
        sim_vorgang = a.kern.session.figur.vorgang
        await _echte(a, ev.Aufgelegt("04ffeedd", "ntag", False, 5, "echt1"))
        assert a.kern.session.figur.uid == "04ffeedd"
        assert a.kern.session.figur.vorgang == "echt1" != sim_vorgang
        assert a.sim.liegt is None  # die Simulation hat nichts mehr aufgelegt
        await _echte(a, ev.Abgehoben(6, "echt1"))  # der echte Tobie wird abgehoben: es zählt
        assert a.kern.session.figur is None
    finally:
        await a.beende()


async def test_ohne_simulation_gilt_der_leser_wie_bisher(app):
    a = neue_app(app, "boot-A")
    await a.starte()
    try:
        await lege_auf(a)  # echter Tobie
        befehle = _sammle_befehle(a)
        await _echte(a, _herzschlag(False), _herzschlag(False))
        assert any(isinstance(b, ev.LeserPing) for b in befehle)  # Abweichung -> PING (Design 9.3)
    finally:
        await a.beende()
