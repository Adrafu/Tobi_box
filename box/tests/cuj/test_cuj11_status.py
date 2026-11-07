"""CUJ 11 (AP 2.4): „Spielt nicht“, Fehlersuche ohne Laptop. Die Status-Admin-Karte.

* Given: Box spielt nicht, kein Handy zur Hand.
* When: Tobias legt die Status-Admin-Karte (Zuordnung ``typ=aktion``, ``aktion=status``) auf.
* Then: Die Box spielt eine Tonfolge: je Prüfpunkt (Leser, Medien, Netz, Speicher, in dieser Reihenfolge)
  ``pruef_ok`` (kurz, hoch) oder ``pruef_fehler`` (tief). Es startet keine Wiedergabe.

Zwei Teile: (1) die Karte im Kern (``AktionAusgeloest(status)`` wird zu ``StatusPruefen``, auch wenn gerade
etwas spielt); (2) die Status-Karte als Tabelle: alle Prüfpunkte in Ordnung, und je ein Fehler. Teil 2 läuft
durch den echten Dienstbau ``App`` (Prüfbericht aus dem Zustand des Dienstes), nur Player, Leser und Tonausgabe
sind ersetzt.
"""

from __future__ import annotations

import shutil

import pytest
from conftest import UID_STATUS, CujBox
from fixtures import audio
from fixtures.audio import erzeuge_medien

from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox import library, selftest, store
from tobibox.app import App

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"
OK, FEHLER = "pruef_ok", "pruef_fehler"


# --- Teil 1: die Karte im Kern -----------------------------------------------------------------


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    zuo = {UID: ev.Zuordnung("serie", SERIE), UID_STATUS: ev.Zuordnung("aktion", aktion="status")}
    return CujBox(tmp_path, zuo, aufbau)


def test_status_karte_im_leerlauf_loest_die_pruefung_aus_und_spielt_nichts(box):
    n = len(box.log)
    box.auflege(UID_STATUS, "v1")
    assert box.befehle(ev.StatusPruefen, n) == [ev.StatusPruefen("v1")]
    assert box.befehle(ev.Abspielen, n) == [] and box.modus == "leer"
    assert box.kern.session.figur.art == "aktion"


def test_status_karte_wird_nicht_erneut_ausgeloest_wenn_der_leser_sie_wieder_meldet(box):
    box.auflege(UID_STATUS, "v1")
    n = len(box.log)
    box.auflege(UID_STATUS, "v1")
    assert box.befehle(ev.StatusPruefen, n) == []


def test_status_karte_nach_abheben_und_neu_auflegen_prueft_erneut(box):
    box.auflege(UID_STATUS, "v1")
    box.hebe_ab("v1")
    n = len(box.log)
    box.auflege(UID_STATUS, "v2")
    assert box.befehle(ev.StatusPruefen, n) == [ev.StatusPruefen("v2")]


def test_status_karte_waehrend_etwas_spielt_erst_pause_mit_zeiger_dann_pruefung(box):
    box.auflege(UID, "v1")
    box.laufe(8.0)
    n = len(box.log)
    box.sende(ev.Aufgelegt(UID_STATUS, "ntag", False, 1, "v2"))  # nur nach verlorenem REMOVED möglich (9, Punkt 11)
    folge = [type(b).__name__ for b in box.log[n:] if isinstance(b, (ev.Pausieren, ev.ZeigerSpeichern, ev.StatusPruefen, ev.Abspielen))]
    assert folge == ["Pausieren", "ZeigerSpeichern", "StatusPruefen"]
    assert box.modus == "pausiert" and not box.player.spielt
    z = box.resume_json()["serien"][SERIE]
    assert z["folge"] == "a.wav" and z["position_s"] == pytest.approx(8.0, abs=0.01)


def test_nach_der_status_karte_spielt_der_naechste_tobie_am_zeiger_weiter(box):
    box.auflege(UID, "v1")
    box.laufe(8.0)
    box.sende(ev.Aufgelegt(UID_STATUS, "ntag", False, 1, "v2"))
    n = len(box.log)
    box.hebe_ab("v2")
    box.auflege(UID, "v3")
    (a,) = box.befehle(ev.Abspielen, n)
    assert a.datei == "a.wav" and a.position_s == pytest.approx(5.0, abs=0.01)  # 8 s minus 3 s Rücksprung


def test_status_karte_unter_stumm_wird_nicht_zum_hinweiston(box):
    """Die Töne ``pruef_*`` bleiben unter „stumm“ (6.2, Regel 2); die Karte selbst gibt keinen anderen Ton."""
    box.sende(ev.StummBeginnt())
    n = len(box.log)
    box.auflege(UID_STATUS, "v1")
    assert box.befehle(ev.StatusPruefen, n) == [ev.StatusPruefen("v1")]
    assert box.befehle(ev.TonSpielen, n) == []


# --- Teil 2: die Status-Karte als Tabelle -----------------------------------------------------------


class Tonfang:
    """Ersatz für ``Toene``: merkt sich die gespielten Folgen."""

    def __init__(self) -> None:
        self.folgen: list[list[str]] = []

    def spiele_folge(self, toene, grenze, ton_pegel=None, hinweis_pegel=None) -> bool:
        self.folgen.append(list(toene))
        return True

    async def stop(self):
        pass


class Welt:
    """Ein Dienst im Zustand „alles in Ordnung“; ein Test verdirbt einen Prüfpunkt."""

    def __init__(self, tmp_path, monkeypatch) -> None:
        self.medien = erzeuge_medien(tmp_path / "medien")
        zustand = tmp_path / "var"
        zustand.mkdir()
        toml = tmp_path / "tobibox.toml"
        toml.write_text(f'[pfade]\nzustand = "{zustand}"\nmedien = "{self.medien}"\n', encoding="utf-8")
        self.monkeypatch = monkeypatch
        monkeypatch.setattr(store, "verlorene_dateien", list(store.verlorene_dateien))
        self.app = App(konfig_modul.lade(toml), melde_bereit=False)
        self.app.toene = Tonfang()
        self.app.bibliothek = library.lade_bibliothek(self.medien)
        self.frei(10_000)
        self.sehe(ev.LeserHallo(1, "1.0.0", "fa4e0000", "4.2"), ev.NetzKlasse("home"), ev.HaVerbindung(True))

    def sehe(self, *ereignisse) -> None:
        for e in ereignisse:
            self.app.status.beobachte(e, self.app.uhr.jetzt())

    def frei(self, mb: int | None) -> None:
        self.monkeypatch.setattr(selftest, "freier_platz_mb", lambda pfad: mb)

    def karte(self) -> list[str]:
        self.app._status_pruefen(ev.StatusPruefen("v1"))
        return self.app.toene.folgen[-1]


@pytest.fixture
def welt(tmp_path, monkeypatch):
    return Welt(tmp_path, monkeypatch)


def leser_getrennt(w):
    w.sehe(ev.LeserAlarm("kein_herzschlag"))


def leser_hallo_fehlt(w):
    w.app.status.hallo = None


def leser_protokoll_unbekannt(w):
    w.sehe(ev.LeserAlarm("proto_unbekannt"))


def leser_fehler(w):
    w.sehe(ev.LeserFehler("pn5180", "Chip antwortet nicht", "fehler"))


def medien_ohne_ueberraschung(w):
    w.app.bibliothek = library.Bibliothek(tuple(s for s in w.app.bibliothek.serien if s.typ != "ueberraschung"), "keine")


def medien_ordner_weg(w):
    shutil.rmtree(w.medien)


def medien_ohne_folge(w):
    w.app.bibliothek = library.Bibliothek((), "keine")


def netz_offline(w):
    w.sehe(ev.NetzKlasse("offline"))


def netz_broker_getrennt(w):
    w.sehe(ev.HaVerbindung(False))


def speicher_knapp(w):
    w.frei(selftest.SPEICHER_MIN_FREI_MB - 1)


def speicher_unbekannt(w):
    w.frei(None)


def datei_verloren(w):
    store.verlorene_dateien.append("resume.json")


TABELLE = [
    ("alles in Ordnung", [], [OK, OK, OK, OK]),
    ("Netz über Hotspot ist in Ordnung", [lambda w: w.sehe(ev.NetzKlasse("hotspot"))], [OK, OK, OK, OK]),
    ("Leser: Herzschlag fehlt", [leser_getrennt], [FEHLER, OK, OK, OK]),
    ("Leser: noch nie gemeldet", [leser_hallo_fehlt], [FEHLER, OK, OK, OK]),
    ("Leser: Protokoll unbekannt", [leser_protokoll_unbekannt], [FEHLER, OK, OK, OK]),
    ("Leser: Fehler des Chips", [leser_fehler], [FEHLER, OK, OK, OK]),
    ("Medien: keine Überraschungs-Serie", [medien_ohne_ueberraschung], [OK, FEHLER, OK, OK]),
    ("Medien: Ordner fehlt", [medien_ordner_weg], [OK, FEHLER, OK, OK]),
    ("Medien: keine Serie mit Folge", [medien_ohne_folge], [OK, FEHLER, OK, OK]),
    ("Netz: offline", [netz_offline], [OK, OK, FEHLER, OK]),
    ("Netz: Broker nicht verbunden", [netz_broker_getrennt], [OK, OK, FEHLER, OK]),
    ("Speicher: zu wenig frei", [speicher_knapp], [OK, OK, OK, FEHLER]),
    ("Speicher: freier Platz unbekannt", [speicher_unbekannt], [OK, OK, OK, FEHLER]),
    ("Speicher: Datei verloren seit dem Start", [datei_verloren], [OK, OK, OK, FEHLER]),
    ("alle vier Prüfpunkte mit Fehler", [leser_getrennt, medien_ohne_folge, netz_offline, speicher_knapp], [FEHLER] * 4),
    ("Leser und Speicher mit Fehler", [leser_getrennt, datei_verloren], [FEHLER, OK, OK, FEHLER]),
]


@pytest.mark.parametrize("name, verderbe, erwartet", TABELLE, ids=[t[0] for t in TABELLE])
def test_status_karte_tonfolge(welt, name, verderbe, erwartet):
    for f in verderbe:
        f(welt)
    assert welt.karte() == erwartet


def test_leser_fehler_zaehlt_nur_zehn_sekunden(welt):
    leser_fehler(welt)
    assert welt.karte()[0] == FEHLER
    welt.app.uhr = type("U", (), {"jetzt": lambda self, j=welt.app.uhr.jetzt(): ev.Jetzt(j.mono + 10.5, j.wall + 10.5)})()
    assert welt.karte()[0] == OK


def test_leser_alarm_vorbei_nach_neuem_hallo(welt):
    leser_getrennt(welt)
    welt.sehe(ev.LeserHallo(1, "1.0.0", "fa4e0000", "4.2"))
    assert welt.karte()[0] == OK


def test_leser_warnung_aendert_den_pruefpunkt_nicht(welt):
    welt.sehe(ev.LeserFehler("pn5180", "kurz", "warnung"))
    assert welt.karte()[0] == OK


def test_pruefung_schreibt_eine_protokollzeile_mit_dem_ergebnis(welt, protokoll):
    netz_offline(welt)
    welt.karte()
    (z,) = protokoll.finde("status_geprueft", "v1", "selftest")
    assert z["ergebnis"] == "fehler" and z["daten"]["leser"] == "ok" and z["daten"]["netz"].startswith("FEHLER")


async def test_die_karte_ist_im_dienst_verdrahtet_statuspruefen_wird_ausgefuehrt(welt):
    await welt.app._fuehre_aus(ev.StatusPruefen("v1"), 0.0)
    assert welt.app.toene.folgen == [[OK, OK, OK, OK]]
