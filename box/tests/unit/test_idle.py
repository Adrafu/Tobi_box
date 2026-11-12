"""Teilautomat Strom / Leerlauf (CUJ 16, 23 bis 25, Tabelle „Strom / Leerlauf“) mit simulierter Uhr (Ein/Aus, 10.11.)."""

from __future__ import annotations

import pytest

from tobibox import events as ev
from tobibox import idle
from tobibox.clock import SimUhr
from tobibox.idle import (
    ANDOCK_RING_S, ANDOCK_RING_SPIELT_S, AUSSCHALT_AUSBLENDEN_S, LADER_SPERRE_S, LEERLAUF_S, STROM_UNBEKANNT_S, STROM_WIDERSPRUCH_S, SYNC_ANTWORT_FRIST_S, ZIEL_FEHLT_SPERRE_S,
)


class Rahmen:
    """Treibt ``idle.step`` mit einer ``SimUhr``; sammelt die Ausgaben ohne ``Protokoll``."""

    def __init__(self, strom: bool | None = None) -> None:
        self.uhr = SimUhr()
        self.z = idle.neuer_zustand()
        self.alles: list = []
        if strom is not None:
            self.sende(ev.LaderGeaendert(strom))  # erste Messung (pisugar)

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
    """Eine Box ohne Wiedergabe und ohne Tobie, **ohne Strom** (erste Messung „kein Strom“), Zähler läuft."""
    r = Rahmen()
    r.sende(ev.LaderGeaendert(False), ev.SitzungGeaendert("leer", False, False, None))
    assert r.modus == "leerlauf"
    return r


def belegt(r: Rahmen, zustand: str = "spielt") -> None:
    r.sende(ev.SitzungGeaendert(zustand, True, zustand == "spielt", "s1"))


FAHREN = [ev.HerunterfahrenAngefordert("leerlauf")]


# --- 20 min Leerlauf ---------------------------------------------------------------------------------------


def test_start_ist_aktiv_und_ohne_bekannten_strom_laeuft_kein_zaehler():
    r = Rahmen()
    assert r.modus == "aktiv"
    r.sende(ev.Takt())
    assert r.modus == "leerlauf" and r.z.frist_bis is None  # Strom unbekannt: der Zähler zählt noch nicht


def test_unbekannter_strom_gilt_nach_60_s_als_kein_strom_dann_beginnt_der_zaehler():
    r = Rahmen()
    r.sende(ev.Takt())
    assert r.vor(STROM_UNBEKANNT_S - 1) == [] and r.z.frist_bis is None
    assert r.vor(1) == [] and r.z.frist_bis == r.uhr.mono + LEERLAUF_S
    assert r.vor(LEERLAUF_S - 1) == []
    assert r.vor(1) == FAHREN


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


def test_spielende_wiedergabe_ist_kein_leerlauf():
    r = Rahmen()
    belegt(r, "spielt")
    assert r.vor(3 * LEERLAUF_S) == []
    assert r.modus == "aktiv"


@pytest.mark.parametrize("zustand", ["pausiert", "beendet", "gehalten"])
def test_liegender_tobie_ohne_wiedergabe_zaehlt_als_leerlauf(zustand):
    """Entscheidung O (09.11., B5): ohne Strom wird 10 min lang nichts gespielt, egal ob ein Tobie liegt (Gute Nacht, „stumm“-Fenster)."""
    r = Rahmen(strom=False)
    belegt(r, zustand)
    r.sende(ev.Takt())
    assert r.modus == "leerlauf"
    assert r.vor(LEERLAUF_S - 1) == []
    assert r.vor(2) == FAHREN
    assert r.modus == "herunterfahren"


def test_liegender_tobie_im_leerlauf_nicht_bei_sync_lernmodus():
    """Die Ausnahmen gelten weiter: Lernmodus (oder Sync, Update) halten die Abschaltung auch mit liegendem Tobie auf."""
    r = Rahmen(strom=False)
    belegt(r, "pausiert")
    r.sende(ev.LernenGeaendert(True))
    assert r.vor(2 * LEERLAUF_S) == []
    assert r.modus == "leerlauf" and r.z.faellig


def test_bedienung_setzt_den_zaehler_auch_mit_liegendem_tobie_zurueck():
    r = Rahmen(strom=False)
    belegt(r, "pausiert")
    r.sende(ev.Takt())
    r.vor(LEERLAUF_S - 10)
    r.sende(ev.Weiter())
    assert r.vor(LEERLAUF_S - 10) == []
    assert r.vor(11) == FAHREN


def test_wiedergabe_ohne_tobie_ist_kein_leerlauf():
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("spielt", False, True, "s1"))
    assert r.vor(3 * LEERLAUF_S) == []
    assert r.modus == "aktiv"


def test_leser_unterbrechung_ist_kein_leerlauf():
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("unbekannt", False, False, "s1"))
    assert r.vor(3 * LEERLAUF_S) == []


def test_tobie_verwirft_den_zaehler_und_abheben_startet_ihn_neu():  # ohne Strom
    r = leer()
    r.vor(LEERLAUF_S - 10)
    belegt(r)
    assert r.modus == "aktiv"
    r.vor(LEERLAUF_S)  # lange gespielt
    r.sende(ev.SitzungGeaendert("pausiert", False, False, "s1"))  # abgehoben
    assert r.modus == "leerlauf"
    assert r.vor(LEERLAUF_S - 1) == []
    assert r.vor(1) == FAHREN


@pytest.mark.parametrize(
    "bedienung",
    [ev.Hauptknopf("kurz"), ev.Weiter(), ev.Zurueck(), ev.LautstaerkeDrehen(5), ev.Kopfhoerer(True), ev.Kopfhoerer(False)],
)
def test_bedienung_setzt_den_zaehler_zurueck(bedienung):
    """Entscheidung der Projektleitung (AP 4.8): Wer an der Box spielt, will nicht, dass sie ausgeht."""
    r = leer()
    r.vor(LEERLAUF_S - 5)
    r.sende(bedienung)
    assert r.vor(5) == []  # ohne Rücksetzen wäre jetzt Schluss
    assert r.vor(LEERLAUF_S - 10) == []
    assert r.vor(5) == FAHREN  # 20 min nach der Bedienung


def test_bedienung_nach_faelligkeit_setzt_auch_die_wartezeit_zurueck():
    r = leer()
    r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 9999), ev.SyncGestartet())
    r.vor(LEERLAUF_S)  # fällig, der Sync hält
    assert r.z.faellig
    r.sende(ev.Weiter())
    assert not r.z.faellig
    r.sende(ev.SyncFertig(1, 0))
    assert r.vor(LEERLAUF_S - 5) == []
    assert r.vor(5) == FAHREN


def test_andere_ereignisse_setzen_den_zaehler_nicht_zurueck():
    r = leer()
    r.vor(LEERLAUF_S - 5)
    r.sende(ev.AkkuStand(80), ev.NetzKlasse("home"), ev.LaderGeaendert(False))
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
    r.sende(ev.SyncGestartet())
    r.vor(LEERLAUF_S + 5)
    assert r.sende(ende) == FAHREN


def test_sync_endet_vor_ablauf_die_zehn_minuten_gelten_weiter():
    r = leer()
    r.sende(ev.SyncGestartet())
    r.vor(300)
    assert r.sende(ev.SyncFertig(1, 0)) == []
    assert r.vor(LEERLAUF_S - 300) == FAHREN


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


def test_ein_offener_sync_haelt_die_abschaltung_auf():
    r = leer()
    r.vor(LEERLAUF_S - 10)
    assert r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 30)) == [ev.SyncStarten("ha")]
    assert r.vor(20) == []  # 20 min um, Sync noch nicht gemeldet
    assert r.z.faellig


def test_sync_regel_lehnt_ab_dann_faehrt_die_box_herunter():
    r = leer()
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
    r = Rahmen(strom=True)
    r.sende(ev.SitzungGeaendert("leer", False, False, None))
    assert r.sende(ev.Bereit()) == [ev.SyncStarten("start_lader")]
    r.sende(ev.SyncGestartet())
    r.vor(100)
    r.sende(ev.LaderGeaendert(False))  # abgenommen: der Zähler beginnt jetzt
    r.vor(LEERLAUF_S)
    assert r.modus == "leerlauf" and r.z.faellig
    assert r.vor(LEERLAUF_S) == []
    assert r.sende(ev.SyncFertig(0, 0)) == FAHREN


def test_mit_strom_faehrt_die_box_nie_von_selbst_herunter():
    r = Rahmen(strom=True)
    r.sende(ev.SitzungGeaendert("leer", False, False, None))
    assert r.vor(100 * LEERLAUF_S) == []
    assert r.modus == "leerlauf" and r.z.frist_bis is None


# --- Herunterfahren auf Anforderung --------------------------------------------------------------------------


@pytest.mark.parametrize("vorher", ["aktiv", "leerlauf"])
def test_hauptknopf_lang_faehrt_herunter(vorher):
    r = leer() if vorher == "leerlauf" else Rahmen()
    if vorher == "aktiv":
        belegt(r)
    assert r.modus == vorher
    if vorher == "aktiv":
        # Entscheidung Y (11.11.): es spielt, also erst 2 s ausblenden, dann herunterfahren
        assert r.sende(ev.Hauptknopf("lang")) == [ev.AusschaltenAusblenden(AUSSCHALT_AUSBLENDEN_S)]
        assert r.modus == "aktiv"
        assert r.vor(AUSSCHALT_AUSBLENDEN_S - 0.1) == []
        assert r.vor(0.2) == [ev.HerunterfahrenAngefordert("hauptknopf")]
    else:
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
    assert r.sende(ev.AkkuTiefstand()) == [
        ev.SyncAbbrechen("akku_tiefstand"), ev.TonSpielen("akku_leer"), ev.HerunterfahrenAngefordert("akku_tiefstand"),
    ]
    assert r.modus == "herunterfahren"


def test_tiefstand_ohne_wiedergabe_und_ohne_sync_fahrt_nur_herunter():
    r = leer()
    # B12: einmal der Ton ``akku_leer``, dann Herunterfahren
    assert r.sende(ev.AkkuTiefstand()) == [ev.TonSpielen("akku_leer"), ev.HerunterfahrenAngefordert("akku_tiefstand")]


def test_tiefstand_bei_wiedergabe_ton_dann_ausblenden_dann_herunterfahren():
    """Entscheidung Z (11.11.)."""
    r = Rahmen()
    belegt(r)
    assert r.sende(ev.AkkuTiefstand()) == [ev.TonSpielen("akku_leer")]
    assert r.modus == "aktiv"
    assert r.sende(ev.TonFolgeEnde()) == [ev.AusschaltenAusblenden(AUSSCHALT_AUSBLENDEN_S)]
    assert r.vor(AUSSCHALT_AUSBLENDEN_S + 0.1) == [ev.HerunterfahrenAngefordert("akku_tiefstand")]
    assert r.modus == "herunterfahren"


def test_tiefstand_bricht_auch_einen_offenen_sync_ab():
    r = leer()
    r.sende(ev.HaSyncAnstossen("b1", r.uhr.wall + 30))
    assert r.sende(ev.AkkuTiefstand())[0] == ev.SyncAbbrechen("akku_tiefstand")


def test_warnung_gibt_ton_und_ring_und_aendert_den_modus_nicht():
    """Entscheidung Z, zweite Stufe (11.11.): Ton ``akku_warnung`` und 5 s Akku-Anzeige, nichts wird beendet."""
    r = leer()
    assert r.sende(ev.AkkuWarnung()) == [ev.TonSpielen("akku_warnung"), ev.AkkuAnzeigen("akku_warnung", 5.0)]
    assert r.modus == "leerlauf"


def test_warnung_bei_wiedergabe_laesst_das_hoerspiel_weiterlaufen():
    r = Rahmen()
    belegt(r)
    assert r.sende(ev.AkkuWarnung()) == [ev.TonSpielen("akku_warnung"), ev.AkkuAnzeigen("akku_warnung", 5.0)]
    assert r.modus == "aktiv"
    assert r.sende(ev.TonFolgeEnde()) == []  # kein Ausblenden: das ist nur bei ``akku_leer`` so


def test_warnung_am_lader_oder_beim_ausschalten_wird_ignoriert():
    r = leer()
    r.sende(ev.LaderGeaendert(True))
    assert r.sende(ev.AkkuWarnung()) == []
    r2 = Rahmen()
    belegt(r2)
    r2.sende(ev.AkkuTiefstand())  # ``akku_leer`` läuft, das Herunterfahren ist unterwegs
    assert r2.sende(ev.AkkuWarnung()) == []


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
    r.sende(ev.Takt(), ev.LaderGeaendert(False))
    assert idle.kennzeichen(r.z) == "leerlauf"
    r.vor(LEERLAUF_S)
    assert idle.kennzeichen(r.z) == "herunterfahren"



# --- B1: ein fehlgeschlagenes Herunterfahren ist nicht endgültig --------------------------------------------------


def test_fehlgeschlagenes_herunterfahren_verlaesst_den_zustand_und_zaehlt_neu():
    r = leer()
    assert r.sende(ev.Hauptknopf("lang")) == FAHREN[:0] + [ev.HerunterfahrenAngefordert("hauptknopf")]
    assert r.modus == "herunterfahren"
    r.uhr.vor(5)
    aus = r.sende(ev.HerunterfahrenFehlgeschlagen("systemctl endete mit Rückgabecode 1"))
    assert r.modus == "leerlauf"  # kein Tobie, keine Wiedergabe: der Zähler beginnt neu
    fehler = [x for x in aus if isinstance(x, ev.EreignisSenden)]
    assert len(fehler) == 1 and fehler[0].art == "fehler"
    assert fehler[0].daten["code"] == "herunterfahren_fehlgeschlagen" and "Rückgabecode 1" in str(fehler[0].daten["text"])
    assert any(isinstance(x, ev.Protokoll) and x.ergebnis == "fehlgeschlagen" for x in r.alles)
    # neuer Zähler: nach 10 min wieder Herunterfahren, nicht sofort
    assert r.vor(LEERLAUF_S - 1) == []
    assert r.vor(2) == FAHREN


def test_nach_dem_fehlschlag_geht_hauptknopf_lang_und_tiefstand_wieder():
    r = leer()
    r.sende(ev.LaderGeaendert(False), ev.Hauptknopf("lang"))
    r.sende(ev.HerunterfahrenFehlgeschlagen("x"))
    assert r.sende(ev.Hauptknopf("lang")) == [ev.HerunterfahrenAngefordert("hauptknopf")]
    r.sende(ev.HerunterfahrenFehlgeschlagen("x"))
    assert ev.HerunterfahrenAngefordert("akku_tiefstand") in r.sende(ev.AkkuTiefstand())


def test_fehlschlag_mit_wiedergabe_geht_nach_aktiv():
    r = Rahmen()
    r.sende(ev.Hauptknopf("lang"))
    belegt(r, "spielt")  # während des Herunterfahrens meldet die Sitzung weiter
    r.sende(ev.HerunterfahrenFehlgeschlagen("x"))
    assert r.modus == "aktiv"


def test_simuliertes_herunterfahren_kehrt_nach_fester_zeit_zurueck_ohne_hinweis():
    r = leer()
    r.sende(ev.Hauptknopf("lang"))
    aus = r.sende(ev.HerunterfahrenFehlgeschlagen("", simuliert=True))
    assert aus == [] and r.modus == "herunterfahren"
    assert r.vor(idle.SIMULATION_RUECKKEHR_S - 1) == [] and r.modus == "herunterfahren"
    r.vor(2)
    assert r.modus == "leerlauf"
    assert not [x for x in r.alles if isinstance(x, ev.EreignisSenden)]
    assert r.sende(ev.Hauptknopf("lang")) == [ev.HerunterfahrenAngefordert("hauptknopf")]


# --- Ein/Aus, 10.11.: Strom, Frist, Andocken -----------------------------------------------------------------------


def bereit_ohne_strom(**kw) -> Rahmen:
    """Bereit, nichts spielt, erste Messung „kein Strom“, ``Bereit`` verarbeitet; die Sperre (10 s ab ``Bereit``) ist noch zu."""
    r = leer()
    r.sende(ev.Bereit())
    return r


def andocken(r: Rahmen, quelle="pisugar"):
    return r.sende(ev.LaderGeaendert(True, quelle))  # type: ignore[arg-type]


def test_strom_verwirft_den_zaehler_und_mit_strom_gibt_es_keine_frist():
    r = leer()
    r.vor(LEERLAUF_S - 5)
    r.sende(ev.LaderGeaendert(True))
    assert r.z.frist_bis is None
    assert r.vor(50 * LEERLAUF_S) == [] and r.modus == "leerlauf"


def test_abziehen_beginnt_die_frist_ab_dem_abnehmen_auch_nach_langer_ruhe():
    r = Rahmen(strom=True)
    r.sende(ev.SitzungGeaendert("leer", False, False, None))
    r.vor(5 * LEERLAUF_S)  # lange nichts gespielt, am Strom
    r.sende(ev.LaderGeaendert(False))
    assert r.z.frist_bis == r.uhr.mono + LEERLAUF_S
    assert r.vor(LEERLAUF_S - 1) == []
    assert r.vor(1) == FAHREN


def test_spielt_die_sitzung_beginnt_die_frist_erst_wenn_sie_nicht_mehr_spielt():
    r = Rahmen(strom=True)
    belegt(r)
    r.sende(ev.LaderGeaendert(False))
    r.vor(3 * LEERLAUF_S)
    assert r.modus == "aktiv" and r.z.frist_bis is None
    r.sende(ev.SitzungGeaendert("pausiert", False, False, "s1"))
    assert r.z.frist_bis == r.uhr.mono + LEERLAUF_S


def test_strom_waehrend_der_wartezeit_verwirft_die_faelligkeit():
    r = leer()
    r.sende(ev.SyncGestartet())
    r.vor(LEERLAUF_S)
    assert r.z.faellig
    r.sende(ev.LaderGeaendert(True))
    assert not r.z.faellig
    assert r.sende(ev.SyncFertig(0, 0)) == []
    assert r.modus == "leerlauf"


def test_bedienung_am_strom_aendert_nichts_und_beginnt_keinen_zaehler():
    r = Rahmen(strom=True)
    r.sende(ev.SitzungGeaendert("leer", False, False, None), ev.Weiter(), ev.Hauptknopf("kurz"))
    assert r.z.frist_bis is None


def test_hauptknopf_lang_faehrt_auch_am_strom_herunter():
    r = Rahmen(strom=True)
    assert r.sende(ev.Hauptknopf("lang")) == [ev.HerunterfahrenAngefordert("hauptknopf")]


def test_tiefstand_wird_nur_ohne_strom_ausgefuehrt_unbekannter_strom_zaehlt_als_kein_strom():
    r = Rahmen()
    assert ev.HerunterfahrenAngefordert("akku_tiefstand") in r.sende(ev.AkkuTiefstand())  # Strom unbekannt (V15)
    r = Rahmen(strom=True)
    assert r.sende(ev.AkkuTiefstand()) == []


def test_update_braucht_bekannten_strom_unbekannt_zaehlt_als_kein_strom():
    r = Rahmen()
    r.sende(ev.NetzKlasse("home"))
    aus = r.sende(ev.HaUpdateAnstossen("b1", "1.2", r.uhr.wall + 30))
    assert "Lader" in aus[0].daten["detail"]


# --- zwei Quellen ---------------------------------------------------------------------------------------------


def test_leser_hat_vorrang_bei_widerspruch():
    r = Rahmen()
    r.sende(ev.LaderGeaendert(False, "pisugar"), ev.LaderGeaendert(True, "leser"))
    assert r.z.am_lader is True
    r.sende(ev.SitzungGeaendert("leer", False, False, None))
    assert r.vor(10 * LEERLAUF_S) == []  # hängt am Sockel, trotz „kein Strom“ von pisugar


def test_pisugar_hängt_der_leser_liefert_den_wert_allein():
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("leer", False, False, None), ev.LaderGeaendert(True, "leser"))
    assert r.vor(10 * LEERLAUF_S) == []


def test_ohne_leser_gilt_pisugar():
    r = Rahmen(strom=True)
    r.sende(ev.SitzungGeaendert("leer", False, False, None))
    assert r.z.am_lader is True


def test_widerspruch_wird_erst_nach_der_entprellzeit_als_warnung_protokolliert():
    r = Rahmen()
    r.sende(ev.LaderGeaendert(True, "pisugar"), ev.LaderGeaendert(False, "leser"))
    warn = lambda: [x for x in r.alles if isinstance(x, ev.Protokoll) and x.ereignis == "strom" and x.ebene == "WARNING"]  # noqa: E731
    r.vor(STROM_WIDERSPRUCH_S - 1)
    assert warn() == []
    r.vor(1)
    assert len(warn()) == 1
    r.vor(60)
    assert len(warn()) == 1  # einmal je Widerspruch
    r.sende(ev.LaderGeaendert(False, "pisugar"))  # die Quellen stimmen wieder überein
    r.sende(ev.LaderGeaendert(True, "pisugar"))
    r.vor(STROM_WIDERSPRUCH_S)
    assert len(warn()) == 2


def test_kurzer_widerspruch_beim_normalen_andocken_ist_keine_warnung():
    r = Rahmen()
    r.sende(ev.LaderGeaendert(False, "pisugar"), ev.LaderGeaendert(False, "leser"))
    r.sende(ev.LaderGeaendert(True, "pisugar"))  # pisugar ist schneller
    r.vor(1)
    r.sende(ev.LaderGeaendert(True, "leser"))
    r.vor(60)
    assert not [x for x in r.alles if isinstance(x, ev.Protokoll) and x.ebene == "WARNING"]


@pytest.mark.parametrize("ende", [ev.LeserAlarm("getrennt"), ev.LeserHallo(1, "1.0.0", "abc1234", "4.2")])
def test_der_leser_wert_gilt_nur_fuer_die_aktuelle_verbindung(ende):
    """V2: Bei Leser-Ausfall oder neuem ``HELLO`` (ohne neues ``LADER``) gilt wieder ``pisugar``."""
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("leer", False, False, None), ev.LaderGeaendert(False, "pisugar"), ev.LaderGeaendert(True, "leser"))
    assert r.z.am_lader is True and r.z.frist_bis is None
    r.sende(ende)
    assert r.z.am_lader is False and r.z.frist_bis is not None  # die Frist beginnt: am Sockel nur durch den Leser
    assert r.vor(LEERLAUF_S) == FAHREN


def test_nach_neuem_hello_zaehlt_ein_neuer_lader_wert_wieder():
    r = Rahmen()
    r.sende(ev.LaderGeaendert(False, "pisugar"), ev.LaderGeaendert(True, "leser"), ev.LeserHallo(1, "1.1.0", "abc1234", "4.2", "strom"))
    r.sende(ev.LaderGeaendert(True, "leser"))
    assert r.z.am_lader is True


# --- erste Messung --------------------------------------------------------------------------------------------


def test_erste_messung_strom_loest_nur_den_sync_check_aus():
    r = Rahmen()
    r.sende(ev.Bereit())
    r.vor(100)
    assert r.sende(ev.LaderGeaendert(True)) == [ev.SyncStarten("start_lader")]  # kein Ton, kein Ring


def test_erste_messung_vor_bereit_der_sync_check_kommt_mit_bereit():
    r = Rahmen()
    assert r.sende(ev.LaderGeaendert(True)) == []
    assert r.sende(ev.Bereit()) == [ev.SyncStarten("start_lader")]


def test_erste_messung_kein_strom_kein_sync_und_kein_ring():
    r = Rahmen()
    r.sende(ev.Bereit())
    assert r.sende(ev.LaderGeaendert(False)) == []


def test_spaete_erste_messung_nach_60_s_strom_stellt_den_zustand_neu_und_hat_keine_rueckmeldung():
    """V4: Der Zustand folgt dem Wert sofort; nur Ring und Ton entfallen."""
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("leer", False, False, None), ev.Bereit())
    r.vor(STROM_UNBEKANNT_S + 30)  # Zähler läuft seit 60 s
    assert r.z.frist_bis is not None
    aus = r.sende(ev.LaderGeaendert(True))
    assert aus == [ev.SyncStarten("start_lader")]
    assert r.z.frist_bis is None and r.vor(10 * LEERLAUF_S) == []


def test_spaete_erste_messung_kein_strom_laesst_den_zaehler_weiterlaufen():
    r = Rahmen()
    r.sende(ev.SitzungGeaendert("leer", False, False, None), ev.Bereit())
    r.vor(STROM_UNBEKANNT_S + 30)
    frist = r.z.frist_bis
    assert r.sende(ev.LaderGeaendert(False)) == [] and r.z.frist_bis == frist


def test_erster_wert_einer_zweiten_quelle_ist_keine_rueckmeldung():
    """V3: pisugar „kein Strom“, später der Leser „Strom“: der Zustand wechselt, aber kein Ring, kein Ton."""
    r = bereit_ohne_strom()
    r.vor(60)  # Sperre ist frei
    aus = r.sende(ev.LaderGeaendert(True, "leser"))
    assert [x for x in aus if isinstance(x, (ev.AkkuAnzeigen, ev.TonSpielen))] == []
    assert r.z.am_lader is True and r.z.frist_bis is None


# --- Andocken und Abziehen ------------------------------------------------------------------------------------


def test_andocken_gibt_ring_ton_und_sync_check():
    r = bereit_ohne_strom()
    r.vor(LADER_SPERRE_S)
    assert andocken(r) == [ev.AkkuAnzeigen("andocken", ANDOCK_RING_S), ev.TonSpielen("lader"), ev.SyncStarten("start_lader")]
    assert r.z.frist_bis is None  # der Zähler ist verworfen


def test_andocken_spielt_die_sitzung_nur_ring_3_s_und_sync_aber_kein_ton():
    r = bereit_ohne_strom()
    belegt(r)
    r.vor(LADER_SPERRE_S)
    assert andocken(r) == [ev.AkkuAnzeigen("andocken", ANDOCK_RING_SPIELT_S), ev.SyncStarten("start_lader")]


def test_andocken_im_leser_ausfall_zustand_unbekannt_der_sitzung_kein_ton():
    r = bereit_ohne_strom()
    r.sende(ev.SitzungGeaendert("unbekannt", False, False, "s1"))
    r.vor(LADER_SPERRE_S)
    assert ev.TonSpielen("lader") not in andocken(r)


def test_andocken_waehrend_eines_updates_nur_ring():
    r = bereit_ohne_strom()
    r.sende(ev.UpdateGestartet("1.2"))
    r.vor(LADER_SPERRE_S)
    assert andocken(r) == [ev.AkkuAnzeigen("andocken", ANDOCK_RING_S)]


def test_andocken_waehrend_eines_syncs_kein_zweiter_sync():
    r = bereit_ohne_strom()
    r.sende(ev.SyncGestartet())
    r.vor(LADER_SPERRE_S)
    assert andocken(r) == [ev.AkkuAnzeigen("andocken", ANDOCK_RING_S), ev.TonSpielen("lader")]


def test_abziehen_ring_akku_kein_ton_kein_sync_und_die_frist_beginnt_jetzt():
    r = Rahmen(strom=True)
    r.sende(ev.SitzungGeaendert("leer", False, False, None), ev.Bereit())
    r.vor(LADER_SPERRE_S)
    assert r.sende(ev.LaderGeaendert(False)) == [ev.AkkuAnzeigen("abziehen", ANDOCK_RING_S)]
    assert r.z.frist_bis == r.uhr.mono + LEERLAUF_S


def test_abziehen_waehrend_des_spielens_ring_3_s():
    r = Rahmen(strom=True)
    belegt(r)
    r.sende(ev.Bereit())
    r.vor(LADER_SPERRE_S)
    assert r.sende(ev.LaderGeaendert(False)) == [ev.AkkuAnzeigen("abziehen", ANDOCK_RING_SPIELT_S)]


def test_sperre_ab_bereit_strom_in_den_ersten_10_s_gibt_keine_rueckmeldung_aber_der_zustand_wechselt():
    r = bereit_ohne_strom()
    r.vor(LADER_SPERRE_S - 1)
    assert andocken(r) == []
    assert r.z.am_lader is True and r.z.frist_bis is None


def test_wackelkontakt_hoechstens_eine_rueckmeldung_je_10_s():
    r = bereit_ohne_strom()
    r.vor(LADER_SPERRE_S)
    ausgaben = []
    for _ in range(5):
        ausgaben += r.sende(ev.LaderGeaendert(True))
        r.vor(1)
        ausgaben += r.sende(ev.LaderGeaendert(False))
        r.vor(1)
    anzeigen = [a for a in ausgaben if isinstance(a, ev.AkkuAnzeigen)]
    assert len(anzeigen) == 1 and anzeigen[0].grund == "andocken"
    assert len([a for a in ausgaben if a == ev.TonSpielen("lader")]) == 1
    assert r.z.frist_bis is not None  # Zustand folgt trotzdem dem Wert: zuletzt „kein Strom“
    r.vor(LADER_SPERRE_S)
    assert [a for a in andocken(r) if isinstance(a, ev.AkkuAnzeigen)]  # nach der Sperre wieder


def test_ohne_bereit_gibt_es_keine_rueckmeldung():
    r = leer()
    r.vor(100)
    assert andocken(r) == []


def test_wiederholter_gleicher_wert_ist_kein_wechsel():
    r = bereit_ohne_strom()
    r.vor(LADER_SPERRE_S)
    andocken(r)
    r.vor(LADER_SPERRE_S)
    assert andocken(r, "leser") == []  # erster Wert des Lesers, gleich: nichts
    assert andocken(r, "leser") == []  # Wiederholung nach HELLO


def test_beim_herunterfahren_gibt_es_keine_rueckmeldung_und_strom_wird_nachgefuehrt():
    r = Rahmen(strom=False)
    r.sende(ev.Bereit())
    r.vor(LADER_SPERRE_S)
    r.sende(ev.Hauptknopf("lang"))
    assert andocken(r) == []
    assert r.z.am_lader is True
    r.sende(ev.HerunterfahrenFehlgeschlagen("x"))
    assert r.modus == "leerlauf" and r.z.frist_bis is None  # Strom da: kein Zähler


def test_strom_ist_ein_wert_aus_der_stromquelle_fuer_alle():
    from tobibox.stromwert import StromQuellen

    q = StromQuellen().mit(ev.LaderGeaendert(True, "pisugar"))
    assert q.wert is True and not q.widerspruch
    q = q.mit(ev.LaderGeaendert(False, "leser"))
    assert q.wert is False and q.widerspruch


# --- Sync wegen fehlender Medien (12.11.) -------------------------------------------------------------------


def bedarf_rahmen(klasse: str = "home", strom: bool = False, akku: int | None = 80) -> Rahmen:
    r = Rahmen()
    r.sende(ev.LaderGeaendert(strom), ev.NetzKlasse(klasse), ev.SitzungGeaendert("leer", False, False, None))
    if akku is not None:
        r.sende(ev.AkkuStand(akku))
    return r


@pytest.mark.parametrize("grund", ["konfig_neu", "ziel_fehlt"])
def test_bedarf_im_heimnetz_startet_den_sync(grund):
    r = bedarf_rahmen("home")
    assert r.sende(ev.SyncBedarf(grund)) == [ev.SyncStarten(grund)]
    assert idle.sync_offen(r.z)


def test_bedarf_im_hotspot_ohne_strom_bei_30_prozent_kein_sync():
    r = bedarf_rahmen("hotspot", strom=False, akku=30)
    assert r.sende(ev.SyncBedarf("konfig_neu")) == []
    assert not idle.sync_offen(r.z)
    p = [x for x in r.alles if isinstance(x, ev.Protokoll) and x.ereignis == "sync"]
    assert [(x.ergebnis, x.daten["grund"], x.daten["sync_grund"]) for x in p] == [("nicht_erlaubt", "regel", "konfig_neu")]


def test_bedarf_im_hotspot_mit_strom_oder_viel_akku_startet():
    assert bedarf_rahmen("hotspot", strom=True, akku=30).sende(ev.SyncBedarf("konfig_neu")) == [ev.SyncStarten("konfig_neu")]
    assert bedarf_rahmen("hotspot", strom=False, akku=51).sende(ev.SyncBedarf("konfig_neu")) == [ev.SyncStarten("konfig_neu")]
    assert bedarf_rahmen("hotspot", strom=False, akku=50).sende(ev.SyncBedarf("konfig_neu")) == []  # genau 50 % reicht nicht


def test_bedarf_offline_kein_sync():
    assert bedarf_rahmen("offline").sende(ev.SyncBedarf("konfig_neu")) == []


def test_bedarf_sync_laeuft_schon_nicht_doppelt():
    r = bedarf_rahmen("home")
    r.sende(ev.SyncGestartet())
    assert r.sende(ev.SyncBedarf("konfig_neu")) == []
    r2 = bedarf_rahmen("home")
    assert r2.sende(ev.SyncBedarf("konfig_neu")) == [ev.SyncStarten("konfig_neu")]  # offen, Antwort fehlt noch
    assert r2.sende(ev.SyncBedarf("konfig_neu")) == []


def test_bedarf_nicht_waehrend_herunterfahren_oder_update():
    r = bedarf_rahmen("home")
    r.sende(ev.Hauptknopf("lang"))
    assert r.modus == "herunterfahren"
    assert r.sende(ev.SyncBedarf("konfig_neu")) == []
    r2 = bedarf_rahmen("home")
    r2.sende(ev.UpdateGestartet("1.2.3"))
    assert r2.sende(ev.SyncBedarf("konfig_neu")) == []


def test_ziel_fehlt_hoechstens_alle_60_s_konfig_neu_sofort():
    r = bedarf_rahmen("home")
    assert r.sende(ev.SyncBedarf("ziel_fehlt")) == [ev.SyncStarten("ziel_fehlt")]
    r.sende(ev.SyncAbgebrochen("rsync_fehler"))
    r.uhr.vor(ZIEL_FEHLT_SPERRE_S - 1)
    assert r.sende(ev.SyncBedarf("ziel_fehlt")) == []  # zu früh
    assert r.sende(ev.SyncBedarf("konfig_neu")) == [ev.SyncStarten("konfig_neu")]  # eine neue Konfiguration wartet nicht
    r.sende(ev.SyncAbgebrochen("rsync_fehler"))
    r.uhr.vor(ZIEL_FEHLT_SPERRE_S)
    assert r.sende(ev.SyncBedarf("ziel_fehlt")) == [ev.SyncStarten("ziel_fehlt")]


def test_bedarf_haelt_die_abschaltung_bis_zur_antwort():
    r = bedarf_rahmen("home")
    assert r.sende(ev.SyncBedarf("konfig_neu")) == [ev.SyncStarten("konfig_neu")]
    r.sende(ev.SyncGestartet())
    assert r.vor(LEERLAUF_S + 5) == []  # ohne Strom abgelaufen, aber der Sync läuft
    assert r.sende(ev.SyncFertig(1, 0)) == FAHREN
