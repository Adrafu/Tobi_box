"""Früher Start-Ton: Marke und Frühdienst (Ein/Aus, 10.11.; AP E1-5) mit simulierter Uhr, ohne Ton-Ausgang."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox import fruehton, store, uhrregel
from tobibox.sounds import Kennlinie, TON_MINDEST

BERLIN_NACHT = datetime(2026, 11, 9, 23, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Europe/Berlin")).timestamp()
BERLIN_TAG = datetime(2026, 11, 9, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Europe/Berlin")).timestamp()
MAX, START, KH = 50, 20, 30


def fenster(wirkung: str, grenze: int | None = None) -> ev.LeiseZeiten:
    return ev.LeiseZeiten("Europe/Berlin", (ev.Fenster("f1", (1, 2, 3, 4, 5, 6, 7), "22:00", "07:00", wirkung, grenze),))


class Welt:
    def __init__(self, tmp_path: Path, abschnitte: str = "", leise: ev.LeiseZeiten | None = None, ton: bool = True):
        self.marken = tmp_path / "run"
        self.marken.mkdir()
        zustand = tmp_path / "var"
        zustand.mkdir()
        k = ev.Konfig(1, "a3f9c1e07b2d4856", {}, leise or ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60))
        store.schreibe_atomar(zustand / "config.json", store.konfig_zu_json(k))
        ton_ordner = tmp_path / "sounds"
        ton_ordner.mkdir()
        if ton:
            from fixtures.audio import schreibe_wav

            schreibe_wav(ton_ordner / "start.wav", 0.3)
        self.konfig = konfig_modul.pruefe(
            {
                "pfade": {"zustand": str(zustand), "medien": str(tmp_path / "medien")},
                "lautstaerke": {"max": MAX, "start": START, "kopfhoerer": KH},
                "toene": {"ordner": str(ton_ordner), "kommando": ["tonprogramm", "{datei}"]},
                **({"strom": {"quelle": "sim"}, "netz": {"quelle": "sim"}} if "sim" in abschnitte else {}),
            }
        )
        self.gespielt: list[list[str]] = []
        self.rc = 0

    def starter(self, kommando: list[str]) -> int:
        self.gespielt.append(kommando)
        assert fruehton.lese_marke(self.marken) == fruehton.START  # während des Tons steht ``start``
        return self.rc

    def spiele(self, *, wall=BERLIN_TAG, kopfhoerer: bool | None = True, rtc=None, **kw) -> str:
        return fruehton.spiele(
            self.konfig, marken_verzeichnis=self.marken, lese_kopfhoerer=lambda: kopfhoerer, lese_rtc_fn=lambda: rtc,
            wall=lambda: wall, mono=lambda: 1000.0, starter=self.starter, **kw,
        )


@pytest.fixture
def mac(tmp_path):
    return Welt(tmp_path, "sim")


def test_normal_ton_gespielt_marke_start_dann_fertig(mac):
    assert mac.spiele() == "gespielt"
    assert len(mac.gespielt) == 1
    assert fruehton.lese_marke(mac.marken) == fruehton.FERTIG
    assert mac.gespielt[0][0] == "tonprogramm"


def test_pegel_ist_der_eines_gewoehnlichen_tons_nicht_der_hinweis_pegel(mac):
    assert fruehton.pegel_fuer(mac.konfig, None, True) == START  # min(grenze, max(10, min(start, max)))
    assert fruehton.pegel_fuer(mac.konfig, None, True) != 15


def test_pegel_untergrenze_und_grenzen():
    k = konfig_modul.pruefe({"pfade": {"zustand": "/tmp/x", "medien": "/tmp/y"}, "lautstaerke": {"max": 50, "start": 5, "kopfhoerer": 30}})
    assert fruehton.pegel_fuer(k, None, True) == TON_MINDEST  # nie unter 10
    k = konfig_modul.pruefe({"pfade": {"zustand": "/tmp/x", "medien": "/tmp/y"}, "lautstaerke": {"max": 50, "start": 40, "kopfhoerer": 30}})
    assert fruehton.pegel_fuer(k, 25, True) == 25  # „leiser“-Fenster
    assert fruehton.pegel_fuer(k, None, False) == 30  # Stecker steckt: Kopfhörer-Grenze
    assert fruehton.pegel_fuer(k, None, None) == 30  # Kontakt nicht lesbar: Kopfhörer-Grenze (Entscheidung P)
    k5 = konfig_modul.pruefe({"pfade": {"zustand": "/tmp/x", "medien": "/tmp/y"}, "lautstaerke": {"max": 50, "start": 40, "kopfhoerer": 5}})
    assert fruehton.pegel_fuer(k5, None, False) == 5  # die Grenze gewinnt immer, auch unter der Untergrenze 10


def test_stumm_kein_ton_marke_keiner(tmp_path):
    w = Welt(tmp_path, "sim", fenster("stumm"))
    assert w.spiele(wall=BERLIN_NACHT) == "stumm"
    assert w.gespielt == [] and fruehton.lese_marke(w.marken) == fruehton.KEINER


def test_leiser_spielt_mit_der_grenze_des_fensters(tmp_path):
    w = Welt(tmp_path, "sim", fenster("leiser", 12))
    assert w.spiele(wall=BERLIN_NACHT) == "gespielt"
    assert fruehton.entscheide(w.konfig, fenster("leiser", 12), wall=BERLIN_NACHT, mono=1.0, rtc=None, leer=True) == ("spielen", 12)
    # am Tag gilt das Fenster nicht
    assert fruehton.entscheide(w.konfig, fenster("leiser", 12), wall=BERLIN_TAG, mono=1.0, rtc=None, leer=True) == ("spielen", START)


def test_unsichere_uhr_kleinste_leiser_grenze_nie_stumm(tmp_path):
    """Pi ohne ``pisugar-server``: Uhr unsicher (V7). Ein „stumm“-Fenster gilt dann nicht, ein „leiser“-Fenster mit der kleinsten Grenze."""
    w = Welt(tmp_path, "")  # keine Abschnitte [netz]/[strom]: auf Linux gilt die NTP-Pflicht
    k = w.konfig
    assert uhrregel.fruehdienst_uhr(k, None, linux=True) == ("unbekannt", False)
    fenster_stumm = fenster("stumm")
    modus, _ = __import__("tobibox.quiet", fromlist=["x"]).wirkung_jetzt(fenster_stumm, ev.Jetzt(1.0, BERLIN_NACHT, "unbekannt", False))
    assert modus == "normal"  # nie „stumm“ bei unsicherer Uhr (nur „leiser“-Fenster zählen)
    assert fruehton.entscheide(k, fenster_stumm, wall=BERLIN_NACHT, mono=1.0, rtc=None, leer=True)[0] == "spielen"


def test_uhr_regeln_des_fruehdienstes(tmp_path):
    mac = Welt(tmp_path / "a" if (tmp_path / "a").mkdir() is None else tmp_path, "sim").konfig
    assert uhrregel.fruehdienst_uhr(mac, None) == ("system", True)  # Mac: alle Quellen ``sim``
    pi = konfig_modul.pruefe({"pfade": {"zustand": "/tmp/x", "medien": "/tmp/y"}, "strom": {"quelle": "pisugar"}})
    assert uhrregel.fruehdienst_uhr(pi, None) == ("unbekannt", False)  # ``pisugar-server`` läuft noch nicht
    plausibel = datetime(2026, 11, 10, tzinfo=timezone.utc)
    verloren = datetime(2000, 1, 1, tzinfo=timezone.utc)
    assert uhrregel.fruehdienst_uhr(pi, plausibel) == ("rtc", True)
    assert uhrregel.fruehdienst_uhr(pi, verloren) == ("unbekannt", False)  # RTC hat die Zeit verloren
    ohne = konfig_modul.pruefe({"pfade": {"zustand": "/tmp/x", "medien": "/tmp/y"}})
    assert uhrregel.fruehdienst_uhr(ohne, None, linux=False) == ("system", True)
    assert uhrregel.fruehdienst_uhr(ohne, None, linux=True) == ("unbekannt", False)
    ohne_pflicht = konfig_modul.pruefe({"pfade": {"zustand": "/tmp/x", "medien": "/tmp/y"}, "uhr": {"ntp_pflicht": False}})
    assert uhrregel.fruehdienst_uhr(ohne_pflicht, None, linux=True) == ("system", True)


def test_dieselbe_regel_wie_die_zeitquelle_des_dienstes():
    from tobibox.net import Zeitquelle

    for system, ntp, rtc in [(True, False, False), (False, True, False), (False, False, True), (False, False, False), (False, True, True)]:
        z = Zeitquelle(system=system)
        z._ntp_ok, z._rtc_ok = ntp, rtc
        assert z._bewerte() == uhrregel.bewerte(system=system, ntp_ok=ntp, rtc_ok=rtc)


def test_fehlende_datei_oder_programm_keine_marke(tmp_path):
    w = Welt(tmp_path, "sim", ton=False)
    assert w.spiele() == "fehler"
    assert fruehton.lese_marke(w.marken) is None and w.gespielt == []  # der Kern spielt ``start`` wie bisher
    w2 = Welt(tmp_path / "zwei" if (tmp_path / "zwei").mkdir() is None else tmp_path, "sim")
    assert fruehton.spiele(w2.konfig, marken_verzeichnis=w2.marken, lese_kopfhoerer=lambda: True, lese_rtc_fn=lambda: None) == "fehler"  # ``tonprogramm`` gibt es nicht
    assert fruehton.lese_marke(w2.marken) is None


def test_ausnahme_irgendwo_keine_marke(mac):
    def kaputt():
        raise RuntimeError("x")

    assert fruehton.spiele(mac.konfig, marken_verzeichnis=mac.marken, lese_kopfhoerer=kaputt, lese_rtc_fn=lambda: None, starter=mac.starter) == "fehler"
    assert fruehton.lese_marke(mac.marken) is None


def test_ton_laeuft_nicht_marke_fehler_der_kern_spielt_start(mac):
    mac.rc = 1
    assert mac.spiele() == "fehler"
    assert fruehton.lese_marke(mac.marken) == fruehton.FEHLER


def test_app_war_schneller_der_fruehdienst_spielt_nicht(mac):
    assert fruehton.uebernimm_marke(mac.marken) is None  # app bei ``Bereit``: keine Marke da, Gegenmarke gesetzt
    assert mac.spiele() == "kein_ton" and mac.gespielt == []
    assert fruehton.lese_marke(mac.marken) == fruehton.UEBERNOMMEN


def test_fertig_nur_in_eine_noch_vorhandene_marke(mac):
    def loesche_waehrend_des_tons(kommando):
        fruehton.loesche_marke(mac.marken)  # app hat die Marke (Frist um) schon gelöscht
        return 0

    fruehton.spiele(mac.konfig, marken_verzeichnis=mac.marken, lese_kopfhoerer=lambda: True, lese_rtc_fn=lambda: None, starter=loesche_waehrend_des_tons)
    assert fruehton.lese_marke(mac.marken) is None  # nicht neu angelegt


def test_marke_wird_atomar_und_vollstaendig_angelegt(tmp_path):
    verz = tmp_path
    assert fruehton.lege_marke_an(fruehton.START, verz)
    assert fruehton.pfad(verz).read_text() == "start\n"
    assert not list(verz.glob(".fruehton-*"))  # keine Reste
    assert fruehton.lege_marke_an(fruehton.KEINER, verz) is False  # es gibt sie schon
    assert fruehton.lese_marke(verz) == fruehton.START


def test_wettlauf_genau_einer_legt_die_marke_an(tmp_path):
    """Frühdienst und ``app`` gleichzeitig: genau einer gewinnt, nie beide."""
    for _ in range(30):
        verz = tmp_path / f"r{_}"
        verz.mkdir()
        ergebnis: dict[str, bool] = {}
        tor = threading.Barrier(2)

        def lauf(name, wort):
            tor.wait()
            ergebnis[name] = fruehton.lege_marke_an(wort, verz)

        ts = [threading.Thread(target=lauf, args=("fd", fruehton.START)), threading.Thread(target=lauf, args=("app", fruehton.UEBERNOMMEN))]
        [t.start() for t in ts]
        [t.join() for t in ts]
        assert sorted(ergebnis.values()) == [False, True]
        assert fruehton.lese_marke(verz) == (fruehton.START if ergebnis["fd"] else fruehton.UEBERNOMMEN)


@pytest.mark.parametrize("inhalt", ["", "start", "start\nfertig\n", "quatsch\n", "START\n"])
def test_unbekannte_oder_halbe_marken_heissen_kein_fruehton(tmp_path, inhalt):
    fruehton.pfad(tmp_path).write_text(inhalt)
    assert fruehton.lese_marke(tmp_path) is None
    assert fruehton.uebernimm_marke(tmp_path) is None


def test_uebernimm_gibt_das_wort_des_fruehdienstes(tmp_path):
    for wort in (fruehton.START, fruehton.KEINER, fruehton.FERTIG):
        verz = tmp_path / wort
        verz.mkdir()
        fruehton.lege_marke_an(wort, verz)
        assert fruehton.uebernimm_marke(verz) == wort


def test_kopfhoerer_kontakt_sim_leer_gpio_fehler_nicht_lesbar(mac, tmp_path):
    assert fruehton.kopfhoerer_leer(mac.konfig) is True
    gpio = konfig_modul.pruefe(
        {"pfade": {"zustand": "/tmp/x", "medien": "/tmp/y"}, "kopfhoerer": {"quelle": "gpio", "gpio_pin": 17}}
    )

    class Treiber:
        def __init__(self, werte):
            self.werte = list(werte)

        async def steckt(self):
            w = self.werte.pop(0)
            if isinstance(w, Exception):
                raise w
            return w

    assert fruehton.kopfhoerer_leer(gpio, lese=Treiber([False, False])) is True
    assert fruehton.kopfhoerer_leer(gpio, lese=Treiber([True, True])) is False
    assert fruehton.kopfhoerer_leer(gpio, lese=Treiber([True, False])) is None  # unruhig: nicht sicher leer
    assert fruehton.kopfhoerer_leer(gpio, lese=Treiber([OSError("x")])) is None


def test_main_ohne_lesbare_konfig_ist_still_und_legt_keine_marke_an(tmp_path, capsys):
    marken = tmp_path / "m"
    marken.mkdir()
    assert fruehton.main(["--config", str(tmp_path / "gibt-es-nicht.toml"), "--marken", str(marken)]) == 0
    assert fruehton.lese_marke(marken) is None


def test_ablauf_blockiert_nicht_ueber_die_ton_frist(mac):
    """Der Frühdienst endet nach dem Ton und hält den Box-Dienst nie auf (``Type=simple``, kein ``Before=``): hier nur: ein Aufruf, kein Dauerlauf."""
    assert mac.spiele() == "gespielt"
    assert mac.spiele() == "kein_ton"  # ein zweiter Lauf (z. B. ``systemctl restart``) spielt nicht noch einmal
