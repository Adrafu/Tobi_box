"""Teilautomat Strom / Leerlauf (CUJ 16, Tabelle „Strom / Leerlauf“) mit simulierter Uhr."""

from __future__ import annotations

import pytest

from tobibox import events as ev
from tobibox import idle
from tobibox.clock import SimUhr
from tobibox.idle import LEERLAUF_S, SYNC_ANTWORT_FRIST_S


class Rahmen:
    """Treibt ``idle.step`` mit einer ``SimUhr``; sammelt die Ausgaben ohne ``Protokoll``."""

    def __init__(self) -> None:
        self.uhr = SimUhr()
        self.z = idle.neuer_zustand()
        self.alles: list = []

    def sende(self, *ereignisse) -> list:
        aus: list = []
        for e in ereignisse:
            self.z, a = idle.step(self.z, e, self.uhr.jetzt())
            self.alles.extend(a)
            aus.extend(x for x in a if not isinstance(x, ev.Protokoll))
        return aus

    def vor(self, s: float) -> list:
        self.uhr.vor(s)
        return self.sende(ev.Takt())

    @property
    def modus(self) -> str:
        return self.z.modus


def leer(**kw) -> Rahmen:
    """Eine Box ohne Wiedergabe und ohne Tobie, Zähler läuft."""
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("leer", False, False, None))
    assert r.modus == "leerlauf"
    return r


def belegt(r: Rahmen, zustand: str = "spielt") -> None:
    r.sende(ev.SitzungGeaendert(zustand, True, zustand == "spielt", "s1"))


FAHREN = [ev.HerunterfahrenAngefordert("leerlauf")]


# --- 20 min Leerlauf ---------------------------------------------------------------------------------------


def test_start_ist_aktiv_und_zaehler_beginnt_mit_der_ersten_auswertung():
    r = Rahmen()
    assert r.modus == "aktiv"
    r.sende(ev.Takt())
    assert r.modus == "leerlauf"
    assert r.z.frist_bis == r.uhr.mono + LEERLAUF_S


def test_nach_20_min_leerlauf_wird_heruntergefahren():
    r = leer()
    assert r.vor(LEERLAUF_S - 1) == []
    assert r.modus == "leerlauf"
    assert r.vor(1) == FAHREN
    assert r.modus == "herunterfahren"


def test_genau_auf_der_grenze_und_nur_einmal():
    r = leer()
    assert r.vor(LEERLAUF_S) == FAHREN
    assert r.vor(60) == []  # danach kommt nichts mehr
    assert r.modus == "herunterfahren"


def test_herunterfahren_wird_protokolliert():
    r = leer()
    r.vor(LEERLAUF_S)
    zeilen = [x for x in r.alles if isinstance(x, ev.Protokoll) and x.ereignis == "herunterfahren"]
    assert len(zeilen) == 1 and zeilen[0].daten["grund"] == "leerlauf"


@pytest.mark.parametrize("zustand", ["spielt", "pausiert", "beendet", "gehalten"])
def test_liegender_tobie_ist_kein_leerlauf(zustand):
    r = Rahmen()
    belegt(r, zustand)
    assert r.vor(3 * LEERLAUF_S) == []
    assert r.modus == "aktiv"


def test_wiedergabe_ohne_tobie_ist_kein_leerlauf():
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("spielt", False, True, "s1"))
    assert r.vor(3 * LEERLAUF_S) == []
    assert r.modus == "aktiv"


def test_leser_unterbrechung_ist_kein_leerlauf():
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("unbekannt", False, False, "s1"))
    assert r.vor(3 * LEERLAUF_S) == []


def test_tobie_verwirft_den_zaehler_und_abheben_startet_ihn_neu():
    r = leer()
    r.vor(LEERLAUF_S - 10)
    belegt(r)
    assert r.modus == "aktiv"
    r.vor(LEERLAUF_S)  # lange gespielt
    r.sende(ev.SitzungGeaendert("pausiert", False, False, "s1"))  # abgehoben
    assert r.modus == "leerlauf"
    assert r.vor(LEERLAUF_S - 1) == []
    assert r.vor(1) == FAHREN


def test_bedienung_setzt_den_zaehler_nicht_zurueck():
    """Der Vertrag kennt nur „keine Wiedergabe und kein Tobie“; Tasten und Regler zählen nicht."""
    r = leer()
    r.vor(LEERLAUF_S - 5)
    r.sende(ev.Hauptknopf("kurz"), ev.LautstaerkeDrehen(5), ev.Weiter(), ev.Kopfhoerer(True), ev.AkkuStand(80))
    assert r.vor(5) == FAHREN


# --- nie während Lernmodus, Sync, Update ---------------------------------------------------------------------


def test_lernmodus_haelt_die_abschaltung_auf():
    r = leer()
    r.sende(ev.LernenGeaendert(True))
    assert r.vor(LEERLAUF_S) == []
    assert r.modus == "leerlauf" and r.z.faellig
    assert r.vor(5 * LEERLAUF_S) == []


def test_nach_dem_lernmodus_beginnt_der_zaehler_neu():
    r = leer()
    r.sende(ev.LernenGeaendert(True))
    r.vor(LEERLAUF_S + 10)
    assert r.sende(ev.LernenGeaendert(False)) == []
    assert not r.z.faellig
    assert r.vor(LEERLAUF_S - 1) == []
    assert r.vor(1) == FAHREN


def test_lernmodus_der_vor_ablauf_endet_aendert_die_frist_nicht_unnoetig():
    r = leer()
    r.vor(100)
    r.sende(ev.LernenGeaendert(True))
    r.vor(30)
    r.sende(ev.LernenGeaendert(False))
    assert r.vor(LEERLAUF_S) == FAHREN


@pytest.mark.parametrize("lader", [None, True, False])
def test_sync_haelt_die_abschaltung_auf_mit_und_ohne_lader(lader):
    r = leer()
    if lader is not None:
        r.sende(ev.LaderGeaendert(lader))
    r.sende(ev.SyncGestartet())
    assert r.vor(3 * LEERLAUF_S) == []
    assert r.modus == "leerlauf"


@pytest.mark.parametrize("ende", [ev.SyncFertig(3, 0), ev.SyncAbgebrochen("netz_weg")])
def test_nach_dem_sync_wird_sofort_erneut_geprueft(ende):
    r = leer()
    r.sende(ev.LaderGeaendert(True), ev.SyncGestartet())
    r.vor(LEERLAUF_S + 5)
    assert r.sende(ende) == FAHREN


def test_sync_endet_vor_ablauf_die_zwanzig_minuten_gelten_weiter():
    r = leer()
    r.sende(ev.SyncGestartet())
    r.vor(600)
    assert r.sende(ev.SyncFertig(1, 0)) == []
    assert r.vor(LEERLAUF_S - 600) == FAHREN


def test_update_haelt_die_abschaltung_auf_bis_zum_selbsttest():
    r = leer()
    r.sende(ev.UpdateGestartet("1.2.0"))
    assert r.vor(2 * LEERLAUF_S) == []
    assert r.sende(ev.SelbsttestErgebnis(True)) == FAHREN


def test_fehlgeschlagener_selbsttest_beendet_das_update_auch():
    r = leer()
    r.sende(ev.UpdateGestartet("1.2.0"))
    r.vor(LEERLAUF_S)
    assert r.sende(ev.SelbsttestErgebnis(False, "mpd")) == FAHREN


def test_lernmodus_und_sync_zusammen_beide_muessen_enden():
    r = leer()
    r.sende(ev.LernenGeaendert(True), ev.SyncGestartet())
    r.vor(LEERLAUF_S)
    r.sende(ev.LernenGeaendert(False))  # Zähler neu, Sync läuft noch
    assert r.vor(2 * LEERLAUF_S) == []
    assert r.sende(ev.SyncFertig(0, 0)) == FAHREN


def test_tobie_waehrend_der_wartezeit_verwirft_die_faelligkeit():
    r = leer()
    r.sende(ev.SyncGestartet())
    r.vor(LEERLAUF_S)
    assert r.z.faellig
    belegt(r)
    assert r.modus == "aktiv" and not r.z.faellig
    r.sende(ev.SyncFertig(0, 0))
    assert r.modus == "aktiv"  # der Tobie liegt: nichts wird abgeschaltet


# --- am Lader: offener Sync ----------------------------------------------------------------------------------


def test_am_lader_haelt_ein_offener_sync_die_abschaltung_auf():
    r = leer()
    r.sende(ev.LaderGeaendert(True))
    r.vor(LEERLAUF_S - 10)
    assert r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 30)) == [ev.SyncStarten("ha")]
    assert r.vor(20) == []  # 20 min um, Sync noch nicht gemeldet
    assert r.z.faellig


def test_sync_regel_lehnt_ab_dann_faehrt_die_box_herunter():
    r = leer()
    r.sende(ev.LaderGeaendert(True))
    r.vor(LEERLAUF_S - 10)
    r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 30))
    r.vor(10)  # 20 min um, die Antwort fehlt noch
    assert r.modus == "leerlauf"
    assert r.sende(ev.SyncAbgebrochen("regel")) == FAHREN


def test_fehlende_antwort_haelt_die_abschaltung_nur_begrenzt_auf():
    r = leer()
    r.vor(LEERLAUF_S - 10)
    r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 30))
    r.vor(10)  # fällig, Sync offen
    assert r.modus == "leerlauf"
    assert r.vor(SYNC_ANTWORT_FRIST_S) == FAHREN


def test_offener_sync_wird_von_sync_gestartet_zum_laufenden():
    r = leer()
    r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 30), ev.SyncGestartet())
    assert r.z.sync_laeuft and not idle.sync_offen(r.z)
    assert r.vor(10 * LEERLAUF_S) == []


# --- Start am Lader ------------------------------------------------------------------------------------------


def test_start_am_lader_prueft_den_sync():
    r = Rahmen()
    assert r.sende(ev.LaderGeaendert(True)) == []  # noch nicht bereit
    assert r.sende(ev.Bereit()) == [ev.SyncStarten("start_lader")]


def test_start_am_lader_wenn_der_lader_nach_bereit_gemeldet_wird():
    r = Rahmen()
    assert r.sende(ev.Bereit()) == []
    assert r.sende(ev.LaderGeaendert(True)) == [ev.SyncStarten("start_lader")]


def test_start_ohne_lader_kein_sync_und_spaeteres_einstecken_zaehlt_nicht():
    r = Rahmen()
    r.sende(ev.LaderGeaendert(False), ev.Bereit())
    assert r.sende(ev.LaderGeaendert(True)) == []
    assert r.sende(ev.LaderGeaendert(False)) == []


def test_start_sync_nur_einmal():
    r = Rahmen()
    assert r.sende(ev.LaderGeaendert(True), ev.Bereit()) == [ev.SyncStarten("start_lader")]
    r.sende(ev.SyncAbgebrochen("regel"))
    assert r.sende(ev.LaderGeaendert(False), ev.LaderGeaendert(True), ev.Bereit()) == []


def test_start_sync_haelt_die_abschaltung_bis_zur_antwort():
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("leer", False, False, None))
    r.vor(LEERLAUF_S - 10)
    r.sende(ev.LaderGeaendert(True), ev.Bereit())
    r.vor(10)
    assert r.modus == "leerlauf" and r.z.faellig
    r.sende(ev.SyncGestartet())
    assert r.vor(LEERLAUF_S) == []
    assert r.sende(ev.SyncFertig(0, 0)) == FAHREN


def test_am_lader_ohne_sync_und_update_gilt_die_zwanzig_minuten_regel():
    r = leer()
    r.sende(ev.LaderGeaendert(True))
    assert r.vor(LEERLAUF_S - 1) == []
    assert r.vor(1) == FAHREN


# --- Herunterfahren auf Anforderung --------------------------------------------------------------------------


@pytest.mark.parametrize("vorher", ["aktiv", "leerlauf"])
def test_hauptknopf_lang_faehrt_herunter(vorher):
    r = leer() if vorher == "leerlauf" else Rahmen()
    if vorher == "aktiv":
        belegt(r)
    assert r.modus == vorher
    assert r.sende(ev.Hauptknopf("lang")) == [ev.HerunterfahrenAngefordert("hauptknopf")]
    assert r.modus == "herunterfahren"


def test_hauptknopf_lang_gilt_auch_waehrend_sync_update_und_lernmodus():
    r = leer()
    r.sende(ev.LernenGeaendert(True), ev.SyncGestartet(), ev.UpdateGestartet("1"))
    assert r.sende(ev.Hauptknopf("lang")) == [ev.HerunterfahrenAngefordert("hauptknopf")]


def test_hauptknopf_kurz_aendert_nichts():
    r = leer()
    assert r.sende(ev.Hauptknopf("kurz")) == []
    assert r.modus == "leerlauf"


def test_tiefstand_bricht_den_sync_ab_und_faehrt_herunter():
    r = leer()
    r.sende(ev.LaderGeaendert(False), ev.SyncGestartet())
    assert r.sende(ev.AkkuTiefstand()) == [ev.SyncAbbrechen("akku_tiefstand"), ev.HerunterfahrenAngefordert("akku_tiefstand")]
    assert r.modus == "herunterfahren"


def test_tiefstand_ohne_sync_fahrt_nur_herunter():
    r = Rahmen()
    belegt(r)
    assert r.sende(ev.AkkuTiefstand()) == [ev.HerunterfahrenAngefordert("akku_tiefstand")]


def test_tiefstand_bricht_auch_einen_offenen_sync_ab():
    r = leer()
    r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 30))
    assert r.sende(ev.AkkuTiefstand())[0] == ev.SyncAbbrechen("akku_tiefstand")


def test_tiefstand_am_lader_wird_ignoriert():
    r = leer()
    r.sende(ev.LaderGeaendert(True))
    assert r.sende(ev.AkkuTiefstand()) == []
    assert r.modus == "leerlauf"


def test_nach_dem_herunterfahren_kommt_nichts_mehr():
    r = leer()
    r.sende(ev.Hauptknopf("lang"))
    assert r.sende(ev.AkkuTiefstand(), ev.Hauptknopf("lang"), ev.HaSyncAnstossen("b", r.uhr.wall + 9)) == []
    assert r.vor(10 * LEERLAUF_S) == []


# --- HA-Befehle ----------------------------------------------------------------------------------------------


def test_sync_befehl_wird_zu_sync_starten():
    r = leer()
    assert r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 30)) == [ev.SyncStarten("ha")]


def test_zweiter_sync_befehl_waehrend_er_laeuft_wird_ignoriert():
    r = leer()
    r.sende(ev.SyncGestartet())
    assert r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 30)) == []


def test_abgelaufener_befehl_nur_protokoll():
    r = leer()
    assert r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall - 1)) == []
    assert r.sende(ev.HaUpdateAnstossen("b2", "1.2", r.uhr.wall - 1)) == []
    assert [x.ereignis for x in r.alles if isinstance(x, ev.Protokoll) and x.ebene == "WARNING"] == [
        "sync_befehl", "update_befehl"
    ]


@pytest.mark.parametrize("befehl, name", [("sync", "sync"), ("update", "update")])
def test_unsichere_uhr_lehnt_ab(befehl, name):
    r = leer()
    r.uhr.setze_zeit("unbekannt", False)
    e = ev.HaSyncAnstossen("b1", r.uhr.wall + 30) if befehl == "sync" else ev.HaUpdateAnstossen("b1", "1.2", r.uhr.wall + 30)
    assert r.sende(e) == [
        ev.EreignisSenden("befehl_abgelehnt", {"befehl": name, "befehl_id": "b1", "grund": "zeit_unsicher"})
    ]


def bereit_fuers_update(r: Rahmen) -> None:
    r.sende(ev.NetzKlasse("home"), ev.LaderGeaendert(True))


def test_update_befehl_bei_erfuellten_bedingungen():
    r = leer()
    bereit_fuers_update(r)
    assert r.sende(ev.HaUpdateAnstossen("b1", "1.2", r.uhr.wall + 30)) == [ev.UpdateStarten("b1", "1.2")]


@pytest.mark.parametrize(
    "vorbereitung, stichwort",
    [
        (lambda r: r.sende(ev.NetzKlasse("hotspot")), "Heimnetz"),
        (lambda r: r.sende(ev.NetzKlasse("offline")), "Heimnetz"),
        (lambda r: r.sende(ev.LaderGeaendert(False)), "Lader"),
        (lambda r: r.sende(ev.SitzungGeaendert("spielt", True, True, "s1")), "Hörspiel"),
        (lambda r: r.sende(ev.SyncGestartet()), "Sync"),
        (lambda r: r.sende(ev.UpdateGestartet("1.1")), "Update"),
    ],
)
def test_update_befehl_bedingung_nicht_erfuellt(vorbereitung, stichwort):
    r = leer()
    bereit_fuers_update(r)
    vorbereitung(r)
    aus = r.sende(ev.HaUpdateAnstossen("b1", "1.2", r.uhr.wall + 30))
    assert len(aus) == 1 and isinstance(aus[0], ev.EreignisSenden)
    assert aus[0].daten["grund"] == "bedingung" and stichwort in aus[0].daten["detail"]
    assert aus[0].daten["befehl"] == "update" and aus[0].daten["befehl_id"] == "b1"


def test_update_ohne_bekannten_lader_oder_netz_wird_abgelehnt():
    r = leer()
    aus = r.sende(ev.HaUpdateAnstossen("b1", "1.2", r.uhr.wall + 30))
    assert aus[0].daten["grund"] == "bedingung"


def test_pausierte_sitzung_ist_fuer_das_update_kein_spielen():
    r = Rahmen()
    bereit_fuers_update(r)
    belegt(r, "pausiert")
    assert r.sende(ev.HaUpdateAnstossen("b1", "1.2", r.uhr.wall + 30)) == [ev.UpdateStarten("b1", "1.2")]


# --- Kennzeichen ---------------------------------------------------------------------------------------------


def test_kennzeichen_ist_der_modus():
    r = Rahmen()
    assert idle.kennzeichen(r.z) == "aktiv"
    r.sende(ev.Takt())
    assert idle.kennzeichen(r.z) == "leerlauf"
    r.vor(LEERLAUF_S)
    assert idle.kennzeichen(r.z) == "herunterfahren"
