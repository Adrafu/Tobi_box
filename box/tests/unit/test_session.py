"""Teilautomat ``session``: jede Zeile der Tabelle „Wiedergabe-Sitzung“ und die
Festlegungen aus ``core-interface.md`` (Abschnitte 6.3, 8, 9) als parametrisierte Tests."""

from __future__ import annotations

import pytest
from conftest import (
    S3,
    UID_CD,
    UID_FOLGE,
    UID_FOLGE_FEHLT,
    UID_S3,
    abspielen,
    zeiger_speichern,
    zeiger,
    ppos,
    S1,
    UEB,
    UID_FEHLT,
    UID_NACHT,
    UID_S1,
    UID_S2,
    UID_STATUS,
    UID_UNBEKANNT,
    S2,
    SitzungsHarnisch,
    in_zustand,
    kern,
    mk_konfig,
    ZUORDNUNGEN,
    typen,
)

from tobibox import events as ev
from tobibox import session

SECHS_ZUSTAENDE = ["leer", "spielt", "pausiert", "beendet", "gehalten", "unbekannt"]


def A(uid=UID_S1, v="v2", seq=5):
    return ev.Aufgelegt(uid, "ntag", False, seq, v)


def G(v="v2", seq=5):
    return ev.Gesperrt(seq, v)


def mit_stumm(aktion):
    def f(h):
        h.sende(ev.StummBeginnt())
        return aktion(h)

    return f


ABSPIELEN_S1_NEU = abspielen("s1", "s1", "a.mp3", 0.0, "v2")
ABSPIELEN_UEB = abspielen("ueb", "ueb", "u1.mp3", 0.0, "v2")
ZEIGER_S1_PAUSE = zeiger_speichern("s1", "a.mp3", 0, 10.0, "pause")

# --------------------------------------------------------------------------
# Tabelle „Wiedergabe-Sitzung“ des Designs, Zeile für Zeile
# --------------------------------------------------------------------------

TABELLE = [
    # (id, Ausgangszustand, Ereignis/Aktion, erwartete Befehle, neuer Zustand)
    ("leer|PLACED serie bekannt, nicht stumm", "leer", lambda h: h.sende(A()), [ABSPIELEN_S1_NEU], "spielt"),
    (
        "pausiert|PLACED serie bekannt, nicht stumm (Resume mit 3 s Rücksprung)",
        "pausiert_ohne_figur",
        lambda h: h.sende(A()),
        [abspielen("s1", "s1", "a.mp3", 7.0, "v2")],
        "spielt",
    ),
    (
        "leer|PLACED kennung unbekannt",
        "leer",
        lambda h: h.sende(A(UID_UNBEKANNT)),
        [ev.Melden("unbekannt", UID_UNBEKANNT, None), ev.TonSpielen("unbekannt"), ABSPIELEN_UEB],
        "spielt",
    ),
    (
        "pausiert|PLACED kennung unbekannt",
        "pausiert_ohne_figur",
        lambda h: h.sende(A(UID_UNBEKANNT)),
        [ev.Melden("unbekannt", UID_UNBEKANNT, None), ev.TonSpielen("unbekannt"), ABSPIELEN_UEB],
        "spielt",
    ),
    ("leer|LOCKED", "leer", lambda h: h.sende(G()), [ABSPIELEN_UEB], "spielt"),
    ("pausiert|LOCKED", "pausiert_ohne_figur", lambda h: h.sende(G()), [ABSPIELEN_UEB], "spielt"),
    (
        "leer|PLACED typ aktion (gute_nacht)",
        "leer",
        lambda h: h.sende(A(UID_NACHT)),
        [ev.AktionAusgeloest("gute_nacht", "v2")],
        "leer",
    ),
    (
        "pausiert|PLACED typ aktion (status)",
        "pausiert_ohne_figur",
        lambda h: h.sende(A(UID_STATUS)),
        [ev.AktionAusgeloest("status", "v2")],
        "pausiert",
    ),
    ("leer|PLACED stumm aktiv", "leer", mit_stumm(lambda h: h.sende(A())), [ev.TonSpielen("hinweis")], "gehalten"),
    (
        "pausiert|PLACED stumm aktiv",
        "pausiert_ohne_figur",
        mit_stumm(lambda h: h.sende(A())),
        [ev.TonSpielen("hinweis")],
        "gehalten",
    ),
    (
        "spielt|REMOVED",
        "spielt",
        lambda h: h.sende(ev.Abgehoben(1, "v1")),
        [ev.Pausieren("abgehoben"), ZEIGER_S1_PAUSE],
        "pausiert",
    ),
    (
        "spielt|PLACED andere Kennung",
        "spielt",
        lambda h: h.sende(A(UID_S2)),
        [zeiger_speichern("s1", "a.mp3", 0, 10.0, "figurwechsel"), abspielen("s2", "s2", "x.mp3", 0.0, "v2")],
        "spielt",
    ),
    (
        "spielt|Folge zu Ende (nicht die letzte)",
        "spielt",
        lambda h: h.sende(ev.FolgeZuEnde("s1", "a.mp3")),
        [zeiger_speichern("s1", "b.mp3", 1, 0.0, "folgenende"), ev.Pausieren("folgenende")],
        "beendet",
    ),
    ("beendet|REMOVED", "beendet", lambda h: h.sende(ev.Abgehoben(1, "v1")), [], "pausiert"),
    (
        "beendet (Figur liegt)|Hauptknopf kurz",
        "beendet",
        lambda h: h.sende(ev.Hauptknopf("kurz")),
        [abspielen("s1", "s1", "b.mp3", 0.0, "v1")],
        "spielt",
    ),
    (
        "spielt|Hauptknopf kurz",
        "spielt",
        lambda h: h.sende(ev.Hauptknopf("kurz")),
        [ev.Pausieren("knopf"), ZEIGER_S1_PAUSE],
        "pausiert",
    ),
    (
        "pausiert (Figur liegt)|Hauptknopf kurz",
        "pausiert",
        lambda h: h.sende(ev.Hauptknopf("kurz")),
        [abspielen("s1", "s1", "a.mp3", 7.0, "v1")],
        "spielt",
    ),
    ("spielt|Wächter-Alarm", "spielt", lambda h: h.sende(ev.LeserAlarm("kein_herzschlag")), [], "unbekannt"),
    (
        "unbekannt|HELLO und PLACED derselben Kennung innerhalb der Frist",
        "unbekannt",
        lambda h: (h.sende(ev.LeserHallo(1, "1.0.0", "a1b2c3d", "4.2")), h.sende(A(UID_S1, "v1", 0)))[1],
        [],
        "spielt",
    ),
    (
        "unbekannt|Frist abgelaufen",
        "unbekannt",
        lambda h: h.sende(ev.Takt(), dt=3.0),
        [ev.Pausieren("leser_unbekannt"), ZEIGER_S1_PAUSE],
        "pausiert",
    ),
    ("gehalten|REMOVED", "gehalten", lambda h: h.sende(ev.Abgehoben(1, "v2")), [], "pausiert"),
    ("gehalten|stumm endet", "gehalten", lambda h: h.sende(ev.StummEndet()), [], "pausiert"),
    (
        "beliebig|Kopfhörer rein: erst Grenze, dann Ausgang",
        "spielt",
        lambda h: h.sende(ev.Kopfhoerer(True)),
        [ev.GrenzeGesetzt("kopfhoerer", 25), ev.AusgangWaehlen("kopfhoerer")],
        "spielt",
    ),
    (
        "beliebig|Kopfhörer raus: erst Grenze, dann Ausgang",
        "pausiert",
        lambda h: h.sende(ev.Kopfhoerer(False)),
        [ev.GrenzeGesetzt("kopfhoerer", None), ev.AusgangWaehlen("lautsprecher")],
        "pausiert",
    ),
]


@pytest.mark.parametrize("name, start, aktion, erwartet, neu", TABELLE, ids=[t[0] for t in TABELLE])
def test_tabelle_wiedergabe_sitzung(name, start, aktion, erwartet, neu):
    h = in_zustand(start)
    assert aktion(h) == erwartet
    assert h.modus == neu


def test_start_mit_liegender_figur_cuj20():
    """Zeile `leer|Start mit liegender Figur`: Start-Ton bei Bereit, dann wie PLACED."""
    h = SitzungsHarnisch()
    assert h.sende(ev.Bereit()) == [ev.TonSpielen("start")]
    assert h.auflegen(UID_S1, "v7") == [abspielen("s1", "s1", "a.mp3", 0.0, "v7")]
    assert h.modus == "spielt"


def test_spielt_stumm_beginnt_blendet_sanft_aus_und_haelt():
    """Zeile `spielt|stumm beginnt`: Rampe über 3 s, Pause, Zeiger speichern, `gehalten`."""
    h = in_zustand("spielt", wirksam=40)
    assert h.sende(ev.StummBeginnt()) == []
    assert h.modus == "spielt"
    befehle = h.takt(2.9)
    erwartet = [ev.GrenzeGesetzt("ausblenden", int((40 * (30 - k) / 30) + 0.5)) for k in range(1, 30)]
    assert befehle == erwartet
    assert h.modus == "spielt"
    ende = h.takt(0.1)
    assert ende == [ev.Pausieren("stumm"), ZEIGER_S1_PAUSE, ev.GrenzeGesetzt("ausblenden", None)]
    assert h.modus == "gehalten"
    assert h.z.figur is not None  # die Figur liegt weiter


def test_ausblenden_haelt_den_startwert_aus_der_letzten_lautstaerkemeldung():
    h = in_zustand("spielt", wirksam=20)
    h.sende(ev.StummBeginnt())
    erster = h.sende(ev.Takt(), dt=0.1)
    assert erster == [ev.GrenzeGesetzt("ausblenden", 19)]
    h.sende(ev.LautstaerkeGeaendert(5))  # die Rampe selbst ändert `von` nicht
    zweiter = h.sende(ev.Takt(), dt=0.1)
    assert zweiter == [ev.GrenzeGesetzt("ausblenden", 19)]  # 20 * (1 - 0.2/3) = 18.67


# --------------------------------------------------------------------------
# 9.1 / 9.2 Leser-Unterbrechung
# --------------------------------------------------------------------------


@pytest.mark.parametrize("zustand", ["pausiert", "beendet", "gehalten", "leer"])
@pytest.mark.parametrize("ereignis", [ev.LeserAlarm("getrennt"), ev.LeserHallo(1, "1.0.0", "a1b2c3d", "4.2")])
def test_leser_unterbrechung_in_anderen_zustaenden_ohne_wirkung(zustand, ereignis):
    h = in_zustand(zustand)
    liegt = h.z.figur
    assert h.sende(ereignis) == []
    assert h.modus == zustand
    assert h.z.figur == liegt  # die Figur gilt weiter als liegend


def test_frist_beginnt_mit_dem_ersten_ereignis_und_wird_nicht_verlaengert():
    h = in_zustand("spielt")
    h.sende(ev.LeserAlarm("getrennt"))
    h.sende(ev.LeserHallo(1, "1.0.0", "a1b2c3d", "4.2"), dt=2.0)
    assert h.sende(ev.Takt(), dt=0.9) == []  # 2.9 s
    assert h.modus == "unbekannt"
    assert h.sende(ev.Takt(), dt=0.1) == [ev.Pausieren("leser_unbekannt"), ZEIGER_S1_PAUSE]  # 3.0 s
    assert h.modus == "pausiert"


def test_pause_spaetestens_3_1_s_nach_dem_ersten_ereignis():
    h = in_zustand("spielt")
    h.sende(ev.LeserAlarm("kein_herzschlag"))
    gesehen = None
    for k in range(1, 40):
        if ev.Pausieren("leser_unbekannt") in h.sende(ev.Takt(), dt=0.1):
            gesehen = k * 0.1
            break
    assert gesehen is not None and gesehen <= 3.1 + 1e-9


@pytest.mark.parametrize("zustand", ["pausiert", "beendet", "gehalten", "spielt"])
def test_wiedermeldung_gleiche_vorgang_id_ist_no_op(zustand):
    h = in_zustand(zustand)
    vorgang = h.z.figur.vorgang
    assert h.sende(A(UID_S1 if zustand != "gehalten" else UID_S1, vorgang, 0)) == []
    assert h.modus == zustand


def test_wiedermeldung_gesperrt_ist_no_op():
    h = in_zustand("leer")
    h.sende(G("v1"))
    h.position("ueb", "u1.mp3", 3.0)
    assert h.modus == "spielt"
    assert h.sende(G("v1", 0)) == []
    assert h.modus == "spielt"


def test_wiedermeldung_nach_der_frist_startet_nichts_von_selbst():
    """Abweichung vom Design: nach Ablauf der Frist pausiert die Sitzung, die Figur liegt weiter."""
    h = in_zustand("unbekannt")
    h.sende(ev.Takt(), dt=3.0)
    assert h.modus == "pausiert"
    assert h.sende(A(UID_S1, "v1", 0)) == []
    assert h.modus == "pausiert"
    assert h.sende(ev.Hauptknopf("kurz")) == [abspielen("s1", "s1", "a.mp3", 7.0, "v1")]


def test_unbekannt_andere_kennung_beendet_die_frist_figurwechsel():
    """Konflikt-Tabelle: Figurwechsel während einer Leser-Unterbrechung."""
    h = in_zustand("unbekannt")
    h.sende(ev.LeserHallo(1, "1.0.0", "a1b2c3d", "4.2"))
    out = h.sende(A(UID_S2, "v2", 0))
    assert out == [
        ev.Pausieren("leser_unbekannt"),
        zeiger_speichern("s1", "a.mp3", 0, 10.0, "figurwechsel"),
        abspielen("s2", "s2", "x.mp3", 0.0, "v2"),
    ]
    assert h.modus == "spielt"


def test_unbekannt_gesperrt_statt_kennung_ist_anderer_vorgang():
    h = in_zustand("unbekannt")
    out = h.sende(G("v2", 0))
    assert out == [
        ev.Pausieren("leser_unbekannt"),
        zeiger_speichern("s1", "a.mp3", 0, 10.0, "figurwechsel"),
        ABSPIELEN_UEB,
    ]
    assert h.modus == "spielt"


def test_unbekannt_abgehoben_beendet_frist_mit_pause():
    h = in_zustand("unbekannt")
    out = h.sende(ev.Abgehoben(1, "v1"))
    assert out == [ev.Pausieren("abgehoben"), ZEIGER_S1_PAUSE]
    assert h.modus == "pausiert" and h.z.figur is None


def test_unbekannt_herzschlag_present_false_nach_hallo():
    h = in_zustand("unbekannt")
    h.sende(ev.LeserHallo(1, "1.0.0", "a1b2c3d", "4.2"))
    out = h.sende(ev.LeserHerzschlag(False, 1, 1, 0, 0, 0, 50))
    assert out == [ev.Pausieren("abgehoben"), ZEIGER_S1_PAUSE]
    assert h.modus == "pausiert" and h.z.figur is None


@pytest.mark.parametrize("zustand", ["pausiert", "beendet", "gehalten"])
def test_herzschlag_present_false_nach_hallo_gilt_als_abgehoben(zustand):
    h = in_zustand(zustand)
    h.sende(ev.LeserHallo(1, "1.0.0", "a1b2c3d", "4.2"))
    assert h.sende(ev.LeserHerzschlag(False, 1, 1, 0, 0, 0, 50)) == []
    assert h.modus == "pausiert" and h.z.figur is None


def test_herzschlag_present_true_nach_hallo_aendert_nichts():
    h = in_zustand("pausiert")
    h.sende(ev.LeserHallo(1, "1.0.0", "a1b2c3d", "4.2"))
    assert h.sende(ev.LeserHerzschlag(True, 1, 1, 0, 0, 0, 50)) == []
    assert h.z.figur is not None


def test_unbekannt_mit_verlorenem_mpd_geht_zurueck_nach_pausiert():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    h.sende(ev.LeserAlarm("getrennt"))
    assert h.modus == "unbekannt"
    assert h.sende(A(UID_S1, "v1", 0)) == []
    assert h.modus == "pausiert" and h.z.figur is not None


def test_unbekannt_mpd_wegfall_waehrend_unbekannt_geht_zurueck_nach_pausiert():
    h = in_zustand("unbekannt")
    h.sende(ev.PlayerVerbindung(False))
    assert h.sende(A(UID_S1, "v1", 0)) == []
    assert h.modus == "pausiert"


def test_mpd_fristzaehler_wird_beim_eintritt_in_unbekannt_verworfen():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    h.sende(ev.LeserAlarm("getrennt"))
    assert h.z.mpd_bis is None
    assert h.sende(ev.Takt(), dt=2.9) == []  # unbekannt: keine MPD-Frist, die Leser-Frist läuft noch


def test_stumm_in_unbekannt_wirkt_erst_nach_dem_verlassen_nach_spielt():
    h = in_zustand("unbekannt")
    h.sende(ev.StummBeginnt())
    assert h.modus == "unbekannt" and h.z.ausblenden is None
    assert h.sende(A(UID_S1, "v1", 0)) == []
    assert h.modus == "spielt" and h.z.ausblenden is not None  # gilt sofort
    assert h.takt(3.0)[-1] == ev.GrenzeGesetzt("ausblenden", None)
    assert h.modus == "gehalten"


def test_stumm_in_unbekannt_wirkt_nach_dem_verlassen_nach_pausiert():
    h = in_zustand("unbekannt")
    h.sende(ev.StummBeginnt())
    h.sende(ev.Takt(), dt=3.0)
    assert h.modus == "pausiert"  # kein Ausblenden, Punkt 12 gilt
    assert h.sende(ev.Hauptknopf("kurz")) == [ev.TonSpielen("hinweis")]


# --------------------------------------------------------------------------
# 9.3 Abgleich über den Herzschlag
# --------------------------------------------------------------------------


def hb(present):
    return ev.LeserHerzschlag(present, 10, 50, 20, 0, 0, 100)


def test_zwei_abweichende_herzschlaege_geben_ping():
    h = in_zustand("pausiert")  # Figur liegt, Leser meldet 0
    assert h.sende(hb(False)) == []
    assert h.sende(hb(False)) == [ev.LeserPing()]
    assert h.sende(hb(False)) == []  # Zähler beginnt neu
    assert h.sende(hb(False)) == [ev.LeserPing()]


def test_ein_abweichender_herzschlag_genuegt_nicht():
    h = in_zustand("pausiert")
    assert h.sende(hb(False)) == []
    assert h.sende(hb(True)) == []  # übereinstimmend setzt zurück
    assert h.sende(hb(False)) == []
    assert h.sende(hb(True)) == []


def test_figur_liegt_laut_leser_aber_nicht_laut_kern_gibt_ping():
    h = in_zustand("leer")
    h.sende(hb(True))
    assert h.sende(hb(True)) == [ev.LeserPing()]


# --------------------------------------------------------------------------
# 9.4 PLACED im Zustand spielt
# --------------------------------------------------------------------------


def test_placed_im_spielt_gleiche_kennung_neuer_vorgang_nichts_geschieht():
    h = in_zustand("spielt")
    assert h.sende(A(UID_S1, "v9", 3)) == []
    assert h.modus == "spielt" and h.z.figur.vorgang == "v9"


def test_placed_im_spielt_aktionskarte_erst_pause_dann_aktion():
    h = in_zustand("spielt")
    out = h.sende(A(UID_NACHT, "v2"))
    assert out == [
        zeiger_speichern("s1", "a.mp3", 0, 10.0, "figurwechsel"),
        ev.Pausieren("abgehoben"),
        ev.AktionAusgeloest("gute_nacht", "v2"),
    ]
    assert h.modus == "pausiert"


# --------------------------------------------------------------------------
# 9.5 Ausblenden bei stumm
# --------------------------------------------------------------------------


def test_abgehoben_waehrend_des_ausblendens_beendet_es_sofort():
    h = in_zustand("spielt")
    h.sende(ev.StummBeginnt())
    h.takt(1.0)
    out = h.sende(ev.Abgehoben(1, "v1"))
    assert out == [ev.GrenzeGesetzt("ausblenden", None), ev.Pausieren("abgehoben"), ZEIGER_S1_PAUSE]
    assert h.modus == "pausiert"


def test_stumm_endet_waehrend_des_ausblendens_endet_in_pausiert():
    """Lücke im Vertrag: das Ausblenden läuft zu Ende, danach `pausiert` statt `gehalten`."""
    h = in_zustand("spielt")
    h.sende(ev.StummBeginnt())
    h.takt(1.0)
    h.sende(ev.StummEndet())
    ende = h.takt(2.0)
    assert ev.Pausieren("stumm") in ende
    assert h.modus == "pausiert"


def test_hauptknopf_waehrend_des_ausblendens_pausiert():
    h = in_zustand("spielt")
    h.sende(ev.StummBeginnt())
    h.takt(1.0)
    out = h.sende(ev.Hauptknopf("kurz"))
    assert out == [ev.GrenzeGesetzt("ausblenden", None), ev.Pausieren("knopf"), ZEIGER_S1_PAUSE]
    assert h.modus == "pausiert"


@pytest.mark.parametrize("ereignis", [ev.Weiter(), ev.Zurueck()])
def test_weiter_zurueck_werden_waehrend_des_ausblendens_ignoriert(ereignis):
    h = in_zustand("spielt")
    h.sende(ev.StummBeginnt())
    h.takt(1.0)
    assert h.sende(ereignis) == []


def test_hauptknopf_lang_bleibt_unberuehrt():
    h = in_zustand("spielt")
    assert h.sende(ev.Hauptknopf("lang")) == []
    assert h.modus == "spielt"


# --------------------------------------------------------------------------
# 9.6 Gute Nacht, Herunterfahren
# --------------------------------------------------------------------------


def test_gute_nacht_ende_pausiert():
    h = in_zustand("spielt")
    assert h.sende(ev.GuteNachtEnde()) == [ev.Pausieren("gute_nacht"), ZEIGER_S1_PAUSE]
    assert h.modus == "pausiert"


@pytest.mark.parametrize("zustand", ["leer", "pausiert", "beendet", "gehalten"])
def test_gute_nacht_ende_in_ruhezustaenden_ohne_wirkung(zustand):
    h = in_zustand(zustand)
    assert h.sende(ev.GuteNachtEnde()) == []
    assert h.modus == zustand


def test_herunterfahren_angefordert_pausiert_und_speichert():
    h = in_zustand("spielt")
    out = h.sende(ev.HerunterfahrenAngefordert("hauptknopf"))
    assert out == [ev.Pausieren("herunterfahren"), zeiger_speichern("s1", "a.mp3", 0, 10.0, "herunterfahren")]
    assert h.modus == "pausiert"


def test_herunterfahren_angefordert_in_ruhe_ohne_wirkung():
    h = in_zustand("pausiert")
    assert h.sende(ev.HerunterfahrenAngefordert("leerlauf")) == []


# --------------------------------------------------------------------------
# 9.10 Fehler des Players
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "art, extra",
    [
        ("datei_fehlt", [zeiger_speichern("s1", "b.mp3", 1, 0.0, "pause")]),
        ("datei_unlesbar", [zeiger_speichern("s1", "b.mp3", 1, 0.0, "pause")]),
        ("mpd_fehler", []),
    ],
)
def test_player_fehler_im_spielt(art, extra):
    h = in_zustand("spielt")
    out = h.sende(ev.PlayerFehler("s1", "a.mp3", art, "details"))
    assert out == [ev.TonSpielen("fehler"), ev.Pausieren("fehler")] + extra
    assert h.modus == "pausiert" and h.z.figur is not None  # die Figur liegt weiter
    assert any(isinstance(o, ev.Protokoll) and o.ebene == "ERROR" for o in h.voll)


def test_player_fehler_letzte_folge_springt_auf_folge_1():
    h = SitzungsHarnisch(zeiger=(zeiger("s1", "c.mp3", 2, 0.0, 1),))
    h.auflegen()
    h.position("s1", "c.mp3", 5.0)
    out = h.sende(ev.PlayerFehler("s1", "c.mp3", "datei_fehlt", ""))
    assert zeiger_speichern("s1", "a.mp3", 0, 0.0, "pause") in out


@pytest.mark.parametrize("zustand", ["leer", "pausiert", "beendet", "gehalten"])
def test_player_fehler_in_anderen_zustaenden_nur_protokoll(zustand):
    h = in_zustand(zustand)
    assert h.sende(ev.PlayerFehler(None, None, "mpd_fehler", "x")) == []
    assert h.modus == zustand


def test_mpd_weg_waehrend_der_wiedergabe_speichert_und_bleibt_spielt():
    h = in_zustand("spielt")
    out = h.sende(ev.PlayerVerbindung(False))
    assert out == [ZEIGER_S1_PAUSE]
    assert h.modus == "spielt"
    assert any(isinstance(o, ev.Protokoll) and o.ebene == "ERROR" for o in h.voll)


@pytest.mark.parametrize("steckt, ausgang", [(False, "lautsprecher"), (True, "kopfhoerer")])
def test_mpd_zurueck_innerhalb_der_frist_setzt_am_zeiger_fort(steckt, ausgang):
    h = in_zustand("spielt")
    if steckt:
        h.sende(ev.Kopfhoerer(True))
    h.sende(ev.PlayerVerbindung(False))
    h.sende(ev.Takt(), dt=4.0)
    out = h.sende(ev.PlayerVerbindung(True), dt=0.5)
    assert out == [ev.AusgangWaehlen(ausgang), abspielen("s1", "s1", "a.mp3", 7.0, "v1")]
    assert h.modus == "spielt"


def test_mpd_frist_abgelaufen_pausiert():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    assert h.sende(ev.Takt(), dt=4.9) == []
    assert h.sende(ev.Takt(), dt=0.1) == [ev.Pausieren("fehler")]
    assert h.modus == "pausiert" and h.z.figur is not None
    # kein Fehlerton in diesem Fall
    assert not any(isinstance(o, ev.TonSpielen) for o in h.voll)


def test_mpd_zurueck_nach_der_frist_pausiert():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    assert h.sende(ev.PlayerVerbindung(True), dt=5.5) == [ev.Pausieren("fehler")]
    assert h.modus == "pausiert"


def test_mpd_zurueck_ohne_figur_pausiert():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    h.sende(ev.Abgehoben(1, "v1"))
    assert h.modus == "pausiert"
    assert h.sende(ev.PlayerVerbindung(True)) == [ev.Pausieren("fehler")]


def test_stumm_waehrend_der_mpd_frist_geht_sofort_nach_gehalten():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    assert h.sende(ev.StummBeginnt()) == []
    assert h.modus == "gehalten"


def test_abgehoben_waehrend_der_mpd_frist_ist_normale_pause():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    assert h.sende(ev.Abgehoben(1, "v1")) == [ev.Pausieren("abgehoben")]  # Zeiger schon gespeichert
    assert h.modus == "pausiert"


def test_hauptknopf_waehrend_der_mpd_frist_pausiert():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    assert h.sende(ev.Hauptknopf("kurz")) == [ev.Pausieren("knopf")]
    assert h.modus == "pausiert"


def test_weitere_player_fehler_waehrend_der_mpd_frist_nur_protokoll():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    assert h.sende(ev.PlayerFehler("s1", "a.mp3", "mpd_fehler", "x")) == []
    assert h.modus == "spielt"


@pytest.mark.parametrize("zustand", ["leer", "pausiert", "beendet", "gehalten"])
@pytest.mark.parametrize("ok", [True, False])
def test_player_verbindung_in_uebrigen_zustaenden(zustand, ok):
    h = in_zustand(zustand)
    # ok=True: defensiv Pausieren("fehler") (idempotent), ok=False: nur Protokoll
    assert h.sende(ev.PlayerVerbindung(ok)) == ([ev.Pausieren("fehler")] if ok else [])
    assert h.modus == zustand


# --------------------------------------------------------------------------
# 9.12 Abspielen-Auslöser und „stumm“
# --------------------------------------------------------------------------

HAUPTKNOPF = [
    # (Zustand, stumm, erwartete Befehle, neuer Zustand)
    ("spielt", False, [ev.Pausieren("knopf"), ZEIGER_S1_PAUSE], "pausiert"),
    ("pausiert", False, [abspielen("s1", "s1", "a.mp3", 7.0, "v1")], "spielt"),
    # Entscheidung Q (10.11.): ohne aufliegenden Tobie startet nichts, nur der Hinweiston
    ("pausiert_ohne_figur", False, [ev.TonSpielen("hinweis")], "pausiert"),
    ("beendet", False, [abspielen("s1", "s1", "b.mp3", 0.0, "v1")], "spielt"),
    ("leer", False, [ev.TonSpielen("hinweis")], "leer"),
    ("unbekannt", False, [], "unbekannt"),
    ("pausiert", True, [ev.TonSpielen("hinweis")], "pausiert"),
    ("pausiert_ohne_figur", True, [ev.TonSpielen("hinweis")], "pausiert"),
    ("beendet", True, [ev.TonSpielen("hinweis")], "beendet"),
    ("gehalten", True, [ev.TonSpielen("hinweis")], "gehalten"),
]


@pytest.mark.parametrize("zustand, stumm, erwartet, neu", HAUPTKNOPF)
def test_hauptknopf_kurz(zustand, stumm, erwartet, neu):
    h = in_zustand(zustand)
    if stumm and zustand != "gehalten":
        h.sende(ev.StummBeginnt())
    assert h.sende(ev.Hauptknopf("kurz")) == erwartet
    assert h.modus == neu.replace("_ohne_figur", "")


WEITER = [
    # (Zustand, Ereignis, stumm, erwartete Befehle, neuer Zustand)
    ("spielt", ev.Weiter(), False, [zeiger_speichern("s1", "b.mp3", 1, 0.0, "folgenende"), abspielen("s1", "s1", "b.mp3", 0.0, "v1")], "spielt"),
    # Zurück nach Track (Entscheidung F): Position 10 s >= 3 s -> aktueller Track von vorn (vorher: vorige Folge)
    ("spielt", ev.Zurueck(), False, [zeiger_speichern("s1", "a.mp3", 0, 0.0, "trackwechsel"), abspielen("s1", "s1", "a.mp3", 0.0, "v1")], "spielt"),
    ("pausiert", ev.Weiter(), False, [zeiger_speichern("s1", "b.mp3", 1, 0.0, "folgenende"), abspielen("s1", "s1", "b.mp3", 0.0, "v1")], "spielt"),
    # Entscheidung Q (10.11.): ohne aufliegenden Tobie startet nichts
    ("pausiert_ohne_figur", ev.Zurueck(), False, [ev.TonSpielen("hinweis")], "pausiert"),
    ("pausiert_ohne_figur", ev.Weiter(), False, [ev.TonSpielen("hinweis")], "pausiert"),
    ("pausiert_ohne_figur", ev.Weiter(), True, [ev.TonSpielen("hinweis")], "pausiert"),
    ("beendet", ev.Weiter(), False, [abspielen("s1", "s1", "b.mp3", 0.0, "v1")], "spielt"),
    # Zurueck in beendet: die eben beendete Folge (vor dem Zeiger), Position 0 (05.11.)
    ("beendet", ev.Zurueck(), False, [zeiger_speichern("s1", "a.mp3", 0, 0.0, "zurueck"), abspielen("s1", "s1", "a.mp3", 0.0, "v1")], "spielt"),
    ("leer", ev.Weiter(), False, [ev.TonSpielen("hinweis")], "leer"),
    ("leer", ev.Zurueck(), False, [ev.TonSpielen("hinweis")], "leer"),
    ("unbekannt", ev.Zurueck(), False, [], "unbekannt"),
    ("pausiert", ev.Weiter(), True, [ev.TonSpielen("hinweis")], "pausiert"),
    ("beendet", ev.Zurueck(), True, [ev.TonSpielen("hinweis")], "beendet"),
    ("gehalten", ev.Weiter(), True, [ev.TonSpielen("hinweis")], "gehalten"),
]


@pytest.mark.parametrize("zustand, ereignis, stumm, erwartet, neu", WEITER)
def test_weiter_und_zurueck(zustand, ereignis, stumm, erwartet, neu):
    h = in_zustand(zustand)
    if stumm and zustand != "gehalten":
        h.sende(ev.StummBeginnt())
    assert h.sende(ereignis) == erwartet
    assert h.modus == neu.replace("_ohne_figur", "")


STUMM_AUFLEGEN = [
    # (Zustand, Aktion, erwartete Befehle, neuer Zustand)
    ("leer", lambda h: h.sende(A()), [ev.TonSpielen("hinweis")], "gehalten"),
    ("pausiert_ohne_figur", lambda h: h.sende(A(UID_UNBEKANNT)), [ev.Melden("unbekannt", UID_UNBEKANNT, None), ev.TonSpielen("hinweis")], "gehalten"),
    ("leer", lambda h: h.sende(G()), [ev.TonSpielen("hinweis")], "gehalten"),
    ("beendet", lambda h: h.sende(A(UID_S1, "v2")), [ev.TonSpielen("hinweis")], "beendet"),
    ("gehalten", lambda h: h.sende(A(UID_S1, "v2")), [ev.TonSpielen("hinweis")], "gehalten"),
    ("beendet", lambda h: h.sende(A(UID_UNBEKANNT, "v2")), [ev.Melden("unbekannt", UID_UNBEKANNT, None), ev.TonSpielen("hinweis")], "beendet"),
]


@pytest.mark.parametrize("zustand, aktion, erwartet, neu", STUMM_AUFLEGEN)
def test_auflegen_unter_stumm_gibt_nur_den_hinweiston(zustand, aktion, erwartet, neu):
    h = in_zustand(zustand)
    if zustand != "gehalten":
        h.sende(ev.StummBeginnt())
    assert aktion(h) == erwartet
    assert h.modus == neu.replace("_ohne_figur", "")
    assert not any(isinstance(o, ev.Abspielen) for o in h.voll)


def test_auflegen_unter_stumm_in_beendet_merkt_sich_die_neue_figur():
    h = in_zustand("beendet")
    h.sende(ev.StummBeginnt())
    h.sende(A(UID_S1, "v2"))
    assert h.z.figur.vorgang == "v2"


def test_stumm_endet_startet_nichts_von_selbst():
    h = in_zustand("leer")
    h.sende(ev.StummBeginnt())
    h.sende(A())
    assert h.modus == "gehalten"
    assert h.sende(ev.StummEndet()) == []
    assert h.modus == "pausiert"


# --------------------------------------------------------------------------
# 9.14 Neue Konfiguration bei liegender Figur
# --------------------------------------------------------------------------


def konfig_mit(uid, serie):
    z = dict(ZUORDNUNGEN)
    z[uid] = ev.Zuordnung("serie", serie)
    return ev.KonfigGeladen(mk_konfig(z))


def unbekannte_figur_liegt(zustand):
    h = SitzungsHarnisch()
    h.auflegen(UID_UNBEKANNT, "v1")
    h.position("ueb", "u1.mp3", 4.0)
    if zustand == "pausiert":
        h.sende(ev.Hauptknopf("kurz"))
    elif zustand == "beendet":
        h.sende(ev.FolgeZuEnde("ueb", "u1.mp3"))
    return h


def test_konfig_bei_liegender_figur_spielt_wechselt_sofort():
    h = unbekannte_figur_liegt("spielt")
    out = h.sende(konfig_mit(UID_UNBEKANNT, "s1"))
    assert out == [
        zeiger_speichern("ueb", "u1.mp3", 0, 4.0, "figurwechsel"),
        abspielen("s1", "s1", "a.mp3", 0.0, "v1"),
    ]
    assert h.modus == "spielt" and h.z.serie_id == "s1"


@pytest.mark.parametrize("zustand", ["pausiert", "beendet"])
def test_konfig_bei_liegender_figur_in_pause_oder_ende_startet_die_neue_serie(zustand):
    h = unbekannte_figur_liegt(zustand)
    assert h.modus == zustand
    assert h.sende(konfig_mit(UID_UNBEKANNT, "s1")) == [abspielen("s1", "s1", "a.mp3", 0.0, "v1")]
    assert h.modus == "spielt"


@pytest.mark.parametrize("zustand", ["pausiert", "beendet"])
def test_konfig_bei_liegender_figur_unter_stumm_nur_hinweiston(zustand):
    h = unbekannte_figur_liegt(zustand)
    h.sende(ev.StummBeginnt())
    assert h.sende(konfig_mit(UID_UNBEKANNT, "s1")) == [ev.TonSpielen("hinweis")]
    assert h.modus == zustand


def test_konfig_in_gehalten_unbekannt_leer_nichts():
    h = in_zustand("gehalten")
    assert h.sende(konfig_mit(UID_S1, "s2")) == []
    assert h.modus == "gehalten"
    h = in_zustand("unbekannt")
    assert h.sende(konfig_mit(UID_S1, "s2")) == []
    assert h.modus == "unbekannt"
    h = in_zustand("leer")
    assert h.sende(konfig_mit(UID_S1, "s2")) == []


def test_konfig_unveraenderte_zuordnung_nichts():
    h = in_zustand("spielt")
    assert h.sende(ev.KonfigGeladen(mk_konfig())) == []


def test_konfig_serie_nicht_in_bibliothek_nichts():
    h = unbekannte_figur_liegt("spielt")
    assert h.sende(konfig_mit(UID_UNBEKANNT, "gibt-es-nicht")) == []


def test_konfig_aktionskarte_nichts():
    h = in_zustand("pausiert_ohne_figur")
    h.sende(A(UID_NACHT))
    assert h.sende(konfig_mit(UID_NACHT, "s1")) == []


# --------------------------------------------------------------------------
# 6.3 Zeigerregeln
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "zeiger, erwartet",
    [
        (None, abspielen("s1", "s1", "a.mp3", 0.0, "v2")),  # kein Zeiger: Folge 1, Position 0
        (zeiger("s1", "b.mp3", 1, 100.0, 4), abspielen("s1", "s1", "b.mp3", 97.0, "v2")),
        (zeiger("s1", "b.mp3", 1, 2.0, 4), abspielen("s1", "s1", "b.mp3", 0.0, "v2")),  # nie unter 0
        (zeiger("s1", "c.mp3", 2, 0.0, 4), abspielen("s1", "s1", "c.mp3", 0.0, "v2")),  # nach Folgenende kein Rücksprung
        (zeiger("s1", "weg.mp3", 1, 50.0, 4), abspielen("s1", "s1", "b.mp3", 0.0, "v2")),  # Folge am Platz index
        (zeiger("s1", "weg.mp3", 7, 50.0, 4), abspielen("s1", "s1", "a.mp3", 0.0, "v2")),  # index zu groß: Folge 1
    ],
    ids=["ohne", "rücksprung", "nicht-unter-0", "nach-folgenende", "datei-fehlt", "index-zu-gross"],
)
def test_zeiger_beim_auflegen(zeiger, erwartet):
    h = SitzungsHarnisch(zeiger=(zeiger,) if zeiger else ())
    assert h.sende(A()) == [erwartet]


def test_fehlende_folge_wird_protokolliert():
    h = SitzungsHarnisch(zeiger=(zeiger("s1", "weg.mp3", 1, 50.0, 4),))
    h.sende(A())
    log = [o for o in h.voll if isinstance(o, ev.Protokoll) and o.ebene == "WARNING"]  # INFO-Kette: CUJ 1
    assert [(p.ebene, p.ereignis) for p in log] == [("WARNING", "zeiger_folge_fehlt")]


def test_leere_serie_gibt_fehlerton():
    leer = ev.Serie("s1", "Serie 1", "normal", "s1", ())
    h = SitzungsHarnisch(serien=(leer, S2, UEB))
    assert h.sende(A()) == [ev.TonSpielen("fehler")]
    assert h.modus == "pausiert"
    assert any(isinstance(o, ev.Protokoll) for o in h.voll)


@pytest.mark.parametrize(
    "serien",
    [(S1, S2), (S1, UEB, ev.Serie("ueb2", "Zwei", "ueberraschung", "ueb2", ("z.mp3",))), (S1, ev.Serie("ueb", "Leer", "ueberraschung", "ueb", ()))],
    ids=["keine", "mehrere", "leer"],
)
def test_ueberraschungs_serie_fehlerfaelle_geben_fehlerton(serien):
    h = SitzungsHarnisch(serien=serien)
    assert h.sende(A(UID_UNBEKANNT)) == [ev.Melden("unbekannt", UID_UNBEKANNT, None), ev.TonSpielen("fehler")]
    assert h.modus == "pausiert"
    assert h.sende(G("v3")) == [ev.TonSpielen("fehler")]


def test_zuordnung_auf_unbekannte_serie_spielt_ueberraschung_ohne_melden():
    h = SitzungsHarnisch()
    out = h.sende(A(UID_FEHLT))
    assert out == [ABSPIELEN_UEB]
    log = [o for o in h.voll if isinstance(o, ev.Protokoll) and o.ebene == "WARNING"]  # INFO-Kette: CUJ 1
    assert [(p.ebene, p.ereignis) for p in log] == [("WARNING", "serie_fehlt")]
    assert dict(log[0].daten) == {"uid": UID_FEHLT, "serie": "unbekannte-serie"}


def test_serie_kommt_spaeter_gilt_beim_naechsten_auflegen():
    h = SitzungsHarnisch()
    h.sende(A(UID_FEHLT, "v1"))
    neu = ev.Serie("unbekannte-serie", "Neu", "normal", "neu", ("n1.mp3",))
    assert h.sende(ev.BibliothekGeladen((S1, S2, UEB, neu))) == []
    assert h.z.serie_id == "ueb" and h.modus == "spielt"  # die laufende Serie wechselt nicht
    h.sende(ev.Abgehoben(6, "v1"))
    assert h.sende(A(UID_FEHLT, "v3")) == [abspielen("unbekannte-serie", "neu", "n1.mp3", 0.0, "v3")]


def test_folge_zu_ende_nach_der_letzten_folge_auf_folge_1():
    h = SitzungsHarnisch(zeiger=(zeiger("s1", "c.mp3", 2, 0.0, 1),))
    h.auflegen()
    out = h.sende(ev.FolgeZuEnde("s1", "c.mp3"))
    assert out == [zeiger_speichern("s1", "a.mp3", 0, 0.0, "folgenende"), ev.Pausieren("folgenende")]
    assert h.modus == "beendet"
    assert h.sende(ev.Hauptknopf("kurz")) == [abspielen("s1", "s1", "a.mp3", 0.0, "v1")]


def test_folge_zu_ende_bei_liegender_figur_pausiert_trotzdem():
    h = in_zustand("spielt")
    h.sende(ev.FolgeZuEnde("s1", "a.mp3"))
    assert h.modus == "beendet" and h.z.figur is not None


def test_folge_zu_ende_fremde_folge_wird_ignoriert():
    h = in_zustand("spielt")
    out = h.sende(ev.FolgeZuEnde("s2", "x.mp3"))
    assert out == [] and h.modus == "spielt"


def test_zeiger_wird_nur_bei_aenderung_geschrieben():
    # Der Zeiger trägt einen frischen Zeitstempel (Entscheidung N, 09.11.); ohne Stempel oder mit altem würde
    # auch ein unveränderter Zeiger neu geschrieben (siehe ``test_session_lesezeichen.py``).
    h = SitzungsHarnisch(zeiger=(zeiger("s1", "a.mp3", 0, 10.0, 1, benutzt_wall=1_700_000_000.0),))
    h.auflegen()
    h.position("s1", "a.mp3", 10.0)
    assert h.sende(ev.Abgehoben(1, "v1")) == [ev.Pausieren("abgehoben")]


def test_zeiger_position_wird_auf_eine_nachkommastelle_abgerundet():
    h = in_zustand("spielt")
    h.position("s1", "a.mp3", 12.39)
    out = h.sende(ev.Abgehoben(1, "v1"))
    assert out[1] == zeiger_speichern("s1", "a.mp3", 0, 12.3, "pause")


def test_position_einer_anderen_folge_wird_ignoriert():
    h = in_zustand("spielt")
    h.sende(ppos("s1", "b.mp3", 99.0, True))
    out = h.sende(ev.Abgehoben(1, "v1"))
    assert out[1].position_s == 10.0


def test_periodisches_speichern_nach_30_s_und_nur_bei_aenderung():
    h = in_zustand("spielt")
    assert h.sende(ev.Takt(), dt=29.9) == []
    assert h.sende(ev.Takt(), dt=0.1) == [zeiger_speichern("s1", "a.mp3", 0, 10.0, "periodisch")]
    assert h.sende(ev.Takt(), dt=30.0) == []  # Zeiger unverändert
    h.position("s1", "a.mp3", 41.0)
    assert h.sende(ev.Takt(), dt=0.1) == [zeiger_speichern("s1", "a.mp3", 0, 41.0, "periodisch")]
    assert h.sende(ev.Takt(), dt=29.8) == []


@pytest.mark.parametrize("zustand", ["leer", "pausiert", "beendet", "gehalten"])
def test_takt_in_ruhezustaenden_ohne_wirkung(zustand):
    h = in_zustand(zustand)
    assert h.sende(ev.Takt(), dt=100.0) == []


# --------------------------------------------------------------------------
# Kopfhörer, Daten, Sonstiges
# --------------------------------------------------------------------------


@pytest.mark.parametrize("zustand", SECHS_ZUSTAENDE)
def test_kopfhoerer_in_jedem_zustand_erst_grenze_dann_ausgang(zustand):
    h = in_zustand(zustand)
    assert h.sende(ev.Kopfhoerer(True)) == [ev.GrenzeGesetzt("kopfhoerer", 25), ev.AusgangWaehlen("kopfhoerer")]
    assert h.sende(ev.Kopfhoerer(False)) == [ev.GrenzeGesetzt("kopfhoerer", None), ev.AusgangWaehlen("lautsprecher")]
    assert h.modus == zustand


@pytest.mark.parametrize("zustand", SECHS_ZUSTAENDE)
def test_lernmodus_und_lautstaerke_aendern_den_zustand_nicht(zustand):
    h = in_zustand(zustand)
    assert h.sende(ev.LernenGeaendert(True)) == []
    assert h.sende(ev.LautstaerkeGeaendert(12)) == []
    assert h.modus == zustand


@pytest.mark.parametrize(
    "ereignis",
    [ev.HaVerbindung(True), ev.AkkuStand(50), ev.NetzKlasse("home"), ev.LeserFehler("internal", "x", "fehler"), ev.Hauptknopf("lang")],
)
def test_unbekannte_ereignisse_aendern_nichts(ereignis):
    h = in_zustand("spielt")
    vorher = h.z
    assert h.sende(ereignis) == []
    assert h.z == vorher


def test_sitzung_geaendert_wird_nur_bei_aenderung_ausgegeben():
    h = SitzungsHarnisch()
    h.auflegen()
    assert ev.SitzungGeaendert("spielt", True, True, "s1") in h.voll
    h.sende(ppos("s1", "a.mp3", 3.0, True))
    assert not any(isinstance(o, ev.SitzungGeaendert) for o in h.voll)
    h.sende(ev.Abgehoben(1, "v1"))
    assert ev.SitzungGeaendert("pausiert", False, False, "s1") in h.voll


def test_aktionskarte_meldet_figur_liegt_und_abgehoben_setzt_zurueck():
    h = SitzungsHarnisch()
    h.sende(A(UID_STATUS))
    assert ev.SitzungGeaendert("leer", True, False, None) in h.voll
    assert h.sende(A(UID_STATUS, "v2", 6)) == []  # Wiedermeldung löst die Aktion nicht erneut aus
    h.sende(ev.Abgehoben(7, "v2"))
    assert h.z.figur is None


def test_zustand_ist_unveraenderlich_und_step_aendert_den_alten_nicht():
    h = SitzungsHarnisch()
    vorher = h.z
    session.step(vorher, A(), h.uhr.jetzt())
    assert h.z is vorher and vorher.modus == "leer"
    with pytest.raises(Exception):
        vorher.modus = "spielt"  # type: ignore[misc]


def test_session_importiert_keine_io_module():
    import ast
    import inspect

    verboten = {"os", "socket", "serial", "time", "asyncio", "threading", "random", "pathlib", "logging", "subprocess", "datetime", "secrets", "json", "io", "sys"}
    for modul in ("tobibox.session", "tobibox.core", "tobibox.volume"):
        quelle = inspect.getsource(__import__(modul, fromlist=["x"]))
        importiert = set()
        for knoten in ast.walk(ast.parse(quelle)):
            if isinstance(knoten, ast.Import):
                importiert |= {a.name.split(".")[0] for a in knoten.names}
            elif isinstance(knoten, ast.ImportFrom) and knoten.level == 0 and knoten.module:
                importiert.add(knoten.module.split(".")[0])
        assert not importiert & verboten, (modul, importiert & verboten)


# --------------------------------------------------------------------------
# Review-Befunde (05.11.)
# --------------------------------------------------------------------------


def test_stumm_auflegen_uebernimmt_den_gespeicherten_zeiger_der_neuen_serie():
    """Zeiger c.mp3 (Index 2), stumm, auflegen, stumm endet, Weiter -> a.mp3 mit Umlauf."""
    h = SitzungsHarnisch(zeiger=(zeiger("s1", "c.mp3", 2, 10.0, 1),))
    h.sende(ev.StummBeginnt())
    h.sende(A())
    assert h.modus == "gehalten"
    assert (h.z.serie_id, h.z.datei, h.z.index, h.z.position_s) == ("s1", "c.mp3", 2, 7.0)
    h.sende(ev.StummEndet())
    assert h.modus == "pausiert"
    assert h.sende(ev.Weiter()) == [
        zeiger_speichern("s1", "a.mp3", 0, 0.0, "folgenende"),
        abspielen("s1", "s1", "a.mp3", 0.0, "v2"),
    ]


def test_stumm_figurwechsel_laesst_keine_reste_einer_anderen_serie():
    h = in_zustand("pausiert_ohne_figur")  # s1, a.mp3 bei 10 s
    h.sende(ev.StummBeginnt())
    h.sende(A(UID_S2))
    assert (h.z.serie_id, h.z.datei, h.z.index) == ("s2", "x.mp3", 0)
    h.sende(ev.StummEndet())
    assert h.sende(ev.Weiter()) == [
        zeiger_speichern("s2", "y.mp3", 1, 0.0, "folgenende"),
        abspielen("s2", "s2", "y.mp3", 0.0, "v2"),
    ]


def test_beendet_stumm_neue_figur_serie_folgt_der_neuen_figur():
    h = in_zustand("beendet")
    h.sende(ev.StummBeginnt())
    assert h.sende(A(UID_S2)) == [ev.TonSpielen("hinweis")]
    assert h.modus == "beendet"
    assert (h.z.serie_id, h.z.datei, h.z.index) == ("s2", "x.mp3", 0)
    h.sende(ev.StummEndet())
    assert h.sende(ev.Hauptknopf("kurz")) == [abspielen("s2", "s2", "x.mp3", 0.0, "v2")]


def test_beendet_weiter_spielt_zeigerfolge_zurueck_die_eben_beendete():
    h = in_zustand("beendet")  # FolgeZuEnde a.mp3 -> Zeiger b.mp3
    assert h.sende(ev.Weiter()) == [abspielen("s1", "s1", "b.mp3", 0.0, "v1")]
    h = in_zustand("beendet")
    assert h.sende(ev.Zurueck())[-1] == abspielen("s1", "s1", "a.mp3", 0.0, "v1")


def test_zurueck_in_beendet_umlauf_bei_erster_folge():
    h = SitzungsHarnisch(zeiger=(zeiger("s1", "c.mp3", 2, 0.0, 1),))
    h.auflegen()
    h.position("s1", "c.mp3", 10.0)
    h.sende(ev.FolgeZuEnde("s1", "c.mp3"))  # Zeiger wieder a.mp3
    assert h.modus == "beendet"
    assert h.sende(ev.Zurueck())[-1] == abspielen("s1", "s1", "c.mp3", 0.0, "v1")


@pytest.mark.parametrize("zustand", ["pausiert", "beendet", "gehalten", "leer"])
def test_verbindung_ok_gibt_defensiv_pausieren_fehler(zustand):
    h = in_zustand(zustand)
    assert h.sende(ev.PlayerVerbindung(True)) == [ev.Pausieren("fehler")]
    assert h.sende(ev.PlayerVerbindung(True)) == [ev.Pausieren("fehler")]  # idempotent
    assert h.modus == zustand


def test_kopfhoerer_vor_einstellungen_grenze_null():
    h = SitzungsHarnisch.__new__(SitzungsHarnisch)
    h.uhr = __import__("tobibox.clock", fromlist=["SimUhr"]).SimUhr()
    h.z = session.neuer_zustand()
    h.voll, h.alle = (), []
    assert h.sende(ev.Kopfhoerer(True)) == [ev.GrenzeGesetzt("kopfhoerer", 0), ev.AusgangWaehlen("kopfhoerer")]
    assert h.sende(ev.GeraeteEinstellungen(60, 40, 25)) == [ev.GrenzeGesetzt("kopfhoerer", 25)]


def test_zweite_einstellungen_setzen_kopfhoerergrenze_neu():
    h = SitzungsHarnisch()
    assert h.sende(ev.GeraeteEinstellungen(60, 40, 30)) == []  # Kopfhörer nicht gesteckt
    h.sende(ev.Kopfhoerer(True))
    assert h.sende(ev.GeraeteEinstellungen(60, 40, 15)) == [ev.GrenzeGesetzt("kopfhoerer", 15)]


def test_leser_zurueck_nach_abgelaufener_frist_ohne_takt_pausiert():
    h = in_zustand("spielt")
    h.sende(ev.LeserAlarm("kein_herzschlag"))
    assert h.modus == "unbekannt"
    out = h.sende(A("04a1b2c3", "v1", 6), dt=3.5)
    assert ev.Pausieren("leser_unbekannt") in out
    assert abspielen("s1", "s1", "a.mp3", 7.0, "v1") not in out
    assert h.modus == "pausiert" and h.z.figur is not None


def test_leser_zurueck_innerhalb_der_frist_spielt_weiter():
    h = in_zustand("spielt")
    h.sende(ev.LeserAlarm("kein_herzschlag"))
    assert h.sende(A(UID_S1, "v1", 6), dt=2.0) == []
    assert h.modus == "spielt"


def test_player_fehler_in_unbekannt_wie_in_spielt():
    h = in_zustand("unbekannt")
    out = h.sende(ev.PlayerFehler("s1", "a.mp3", "mpd_fehler", "x"))
    assert out == [ev.TonSpielen("fehler"), ev.Pausieren("fehler")]
    assert h.modus == "pausiert" and h.z.figur is not None


def test_player_fehler_fremde_datei_in_spielt_nur_protokoll():
    h = in_zustand("spielt")
    assert h.sende(ev.PlayerFehler("s1", "b.mp3", "datei_fehlt", "x")) == []
    assert h.modus == "spielt"
    assert any(isinstance(o, ev.Protokoll) and o.ergebnis == "fremde_datei" for o in h.voll)


def test_weiter_zurueck_waehrend_mpd_frist_ignoriert():
    h = in_zustand("spielt")
    h.sende(ev.PlayerVerbindung(False))
    assert h.sende(ev.Weiter()) == []
    assert h.sende(ev.Zurueck()) == []
    assert h.modus == "spielt" and h.z.datei == "a.mp3"


def test_verbindung_ok_in_unbekannt_fuehrt_bei_rueckkehr_zu_pausiert():
    h = in_zustand("spielt")
    h.sende(ev.LeserAlarm("kein_herzschlag"))
    h.sende(ev.PlayerVerbindung(False))
    assert h.sende(ev.PlayerVerbindung(True)) == []
    h.sende(A(UID_S1, "v1", 6))
    assert h.modus == "pausiert"


# --------------------------------------------------------------------------
# DienstEndet: Dienst endet, Gerät bleibt an
# --------------------------------------------------------------------------


@pytest.mark.parametrize("zustand", ["spielt", "unbekannt"])
def test_dienst_endet_pausiert_und_speichert(zustand):
    h = in_zustand(zustand)
    out = h.sende(ev.DienstEndet())
    assert ev.Pausieren("herunterfahren") in out
    assert any(isinstance(b, ev.ZeigerSpeichern) for b in out)
    assert h.modus == "pausiert"


@pytest.mark.parametrize("zustand", ["leer", "pausiert", "beendet", "gehalten"])
def test_dienst_endet_in_ruhe_ohne_wirkung(zustand):
    h = in_zustand(zustand)
    assert h.sende(ev.DienstEndet()) == []
    assert h.modus == zustand


# ==========================================================================
# Entscheidung F (05.11.): Folgen-Tobies, Tracks, Zeiger mit Track
# ==========================================================================

CD = ("cd/01.mp3", "cd/02.mp3", "cd/03.mp3")  # Tracks der Folge „cd“ in Serie s3


def ab_cd(position=0.0, track=0, vorgang="v1"):
    return abspielen("s3", "s3", "cd", position, vorgang, track=track, tracks=CD)


def cd_spielt(uid=UID_CD, sek=10.0, track=0, zeiger_liste=()):
    """Harnisch: Tobie ``uid`` (Folge „cd“ bzw. Serie s3) liegt und spielt."""
    h = SitzungsHarnisch(zeiger=zeiger_liste)
    h.auflegen(uid)
    h.position("s3", "cd", sek, track)
    assert h.modus == "spielt"
    return h


def zustand_s3(name, uid=UID_CD):
    """Wie ``in_zustand``, aber mit dem Tobie ``uid`` auf Serie s3 (Folge „cd“ mit drei Tracks)."""
    h = SitzungsHarnisch()
    if name == "leer":
        return h
    if name == "gehalten":
        h.sende(ev.StummBeginnt())
        h.auflegen(uid)
        return h
    h.auflegen(uid)
    h.position("s3", "cd", 10.0, 0)
    if name == "pausiert":
        h.sende(ev.Hauptknopf("kurz"))
    elif name == "pausiert_ohne_figur":
        h.sende(ev.Abgehoben(1, "v1"))
    elif name == "beendet":
        h.sende(ev.FolgeZuEnde("s3", "cd"))
    elif name == "unbekannt":
        h.sende(ev.LeserAlarm("kein_herzschlag"))
    elif name != "spielt":
        raise ValueError(name)
    assert h.modus == name.replace("_ohne_figur", ""), (name, h.modus)
    return h


# --- Auflegen: Ziel serie / folge, Zeiger mit Track -------------------------------


def test_folgen_tobie_spielt_seine_folge_ab_track_0():
    h = SitzungsHarnisch()
    assert h.auflegen(UID_FOLGE) == [abspielen("s1", "s1", "b.mp3", 0.0, "v1")]
    assert (h.modus, h.z.ziel, h.z.datei, h.z.index, h.z.track) == ("spielt", "folge", "b.mp3", 1, 0)


def test_folgen_tobie_mit_mehreren_tracks_laedt_alle_tracks():
    h = SitzungsHarnisch()
    assert h.auflegen(UID_CD) == [ab_cd()]


def test_serien_tobie_auf_serie_mit_cd_folge_startet_mit_track_0_der_ersten_folge():
    h = SitzungsHarnisch()
    assert h.auflegen(UID_S3) == [ab_cd()]
    assert h.z.ziel == "serie"


def test_folgen_zeiger_mit_track_und_ruecksprung_im_track():
    fz = zeiger("s3", "cd", None, 50.0, 4, track=2, art="folge")
    h = SitzungsHarnisch(zeiger=(fz,))
    assert h.auflegen(UID_CD) == [ab_cd(47.0, track=2)]


def test_serien_zeiger_mit_track_und_ruecksprung_im_track():
    sz = zeiger("s3", "cd", 0, 50.0, 4, track=1)
    h = SitzungsHarnisch(zeiger=(sz,))
    assert h.auflegen(UID_S3) == [ab_cd(47.0, track=1)]


def test_folgen_zeiger_und_serien_zeiger_derselben_serie_sind_unabhaengig():
    sz = zeiger("s1", "a.mp3", 0, 30.0, 2)
    fz = zeiger("s1", "b.mp3", None, 12.0, 2, art="folge")
    h = SitzungsHarnisch(zeiger=(sz, fz))
    assert h.auflegen(UID_FOLGE) == [abspielen("s1", "s1", "b.mp3", 9.0, "v1")]
    h2 = SitzungsHarnisch(zeiger=(sz, fz))
    assert h2.auflegen(UID_S1) == [abspielen("s1", "s1", "a.mp3", 27.0, "v1")]


def test_fehlender_track_im_zeiger_track_0_und_protokoll():
    sz = zeiger("s3", "cd", 0, 50.0, 4, track=9)
    h = SitzungsHarnisch(zeiger=(sz,))
    assert h.auflegen(UID_S3) == [ab_cd(0.0, track=0)]
    assert any(isinstance(o, ev.Protokoll) and o.ereignis == "zeiger_track_fehlt" for o in h.alle)


def test_folgen_tobie_speichert_in_den_folgen_zeiger_und_nicht_in_den_serien_zeiger():
    h = SitzungsHarnisch()
    h.auflegen(UID_FOLGE)
    h.position("s1", "b.mp3", 20.0)
    out = h.sende(ev.Abgehoben(1, "v1"))
    assert out == [ev.Pausieren("abgehoben"), zeiger_speichern("s1", "b.mp3", None, 20.0, "pause", art="folge")]


# --- Zuordnung auf fehlende Serie oder Folge (6.3) ---------------------------------


def test_folgen_tobie_auf_fehlende_folge_spielt_ueberraschung_ohne_melden_und_protokolliert():
    h = SitzungsHarnisch()
    out = h.auflegen(UID_FOLGE_FEHLT)
    assert out == [abspielen("ueb", "ueb", "u1.mp3", 0.0, "v1")]
    assert not any(isinstance(o, ev.Melden) for o in h.alle)
    p = next(o for o in h.alle if isinstance(o, ev.Protokoll) and o.ereignis == "folge_fehlt")
    assert p.ebene == "WARNING"
    assert dict(p.daten) == {"uid": UID_FOLGE_FEHLT, "serie": "s1", "folge": "gibt-es-nicht.mp3"}
    assert (h.z.ziel, h.z.serie_id) == ("serie", "ueb")  # die Überraschungs-Serie verhält sich wie Ziel serie


def test_zuordnung_auf_fehlende_serie_spielt_ueberraschung_ohne_melden_und_protokolliert():
    h = SitzungsHarnisch()
    out = h.auflegen(UID_FEHLT)
    assert [type(o) for o in out] == [ev.Abspielen] and out[0].serie_id == "ueb"
    assert not any(isinstance(o, ev.Melden) for o in h.alle)
    p = next(o for o in h.alle if isinstance(o, ev.Protokoll) and o.ereignis == "serie_fehlt")
    assert dict(p.daten) == {"uid": UID_FEHLT, "serie": "unbekannte-serie"}


def test_folgen_tobie_auf_fehlende_folge_ohne_ueberraschung_gibt_fehlerton():
    h = SitzungsHarnisch(serien=(S1,))
    out = h.auflegen(UID_FOLGE_FEHLT)
    assert out == [ev.TonSpielen("fehler")]
    assert h.modus == "pausiert"


def test_folgen_tobie_auf_fehlende_folge_unter_stumm_nur_hinweiston():
    h = SitzungsHarnisch()
    h.sende(ev.StummBeginnt())
    assert h.auflegen(UID_FOLGE_FEHLT) == [ev.TonSpielen("hinweis")]
    assert h.modus == "gehalten"


def test_folge_kommt_spaeter_gilt_beim_naechsten_auflegen_laufende_ueberraschung_bleibt():
    s1_ohne = ev.Serie("s1", "Serie 1", "normal", "s1", ("a.mp3", "c.mp3"))
    h = SitzungsHarnisch(serien=(s1_ohne, S2, UEB, S3))
    h.auflegen(UID_FOLGE)  # b.mp3 gibt es noch nicht
    assert h.z.serie_id == "ueb"
    assert h.sende(ev.BibliothekGeladen((S1, S2, UEB, S3))) == []
    assert h.z.serie_id == "ueb" and h.modus == "spielt"  # läuft weiter
    h.sende(ev.Abgehoben(1, "v1"))
    assert h.auflegen(UID_FOLGE, "v2")[-1] == abspielen("s1", "s1", "b.mp3", 0.0, "v2")


# --- TrackWechsel ------------------------------------------------------------------


@pytest.mark.parametrize(
    "uid, art, index",
    [(UID_CD, "folge", None), (UID_S3, "serie", 0)],
)
def test_track_wechsel_fuehrt_den_zeiger_nach_ohne_pause(uid, art, index):
    h = cd_spielt(uid)
    out = h.sende(ev.TrackWechsel("s3", "cd", 1))
    assert out == [zeiger_speichern("s3", "cd", index, 0.0, "trackwechsel", track=1, art=art)]
    assert h.modus == "spielt"
    assert not any(isinstance(o, ev.Pausieren) for o in h.voll)
    h.position("s3", "cd", 5.0, track=1)
    assert h.sende(ev.Abgehoben(1, "v1"))[-1] == zeiger_speichern("s3", "cd", index, 5.0, "pause", track=1, art=art)


def test_track_wechsel_hintereinander_zaehlt_die_zeiger_schreibungen():
    h = cd_spielt()
    a = h.sende(ev.TrackWechsel("s3", "cd", 1))
    b = h.sende(ev.TrackWechsel("s3", "cd", 2))
    assert [o.track for o in a + b] == [1, 2]


@pytest.mark.parametrize(
    "e",
    [
        ev.TrackWechsel("s3", "cd", 0),  # nicht größer als der aktuelle Track (veraltet)
        ev.TrackWechsel("s3", "cd", 3),  # außerhalb der Folge
        ev.TrackWechsel("s3", "z.mp3", 1),  # andere Folge
        ev.TrackWechsel("s2", "cd", 1),  # andere Serie
    ],
)
def test_track_wechsel_veraltet_oder_fremd_wird_ignoriert(e):
    h = cd_spielt()
    assert h.sende(e) == []
    assert h.z.track == 0
    assert any(isinstance(o, ev.Protokoll) and o.ereignis == "track_wechsel_fremd" for o in h.voll)


@pytest.mark.parametrize("zustand", ["leer", "pausiert", "pausiert_ohne_figur", "beendet", "gehalten"])
def test_track_wechsel_und_folge_zu_ende_ohne_laufendes_mpd_werden_ignoriert(zustand):
    h = zustand_s3(zustand)
    vorher = h.z
    assert h.sende(ev.TrackWechsel("s3", "cd", 1)) == []
    assert h.sende(ev.FolgeZuEnde("s3", "cd")) == []
    assert h.z == vorher


def test_track_wechsel_in_unbekannt_fuehrt_nach_und_bleibt_unbekannt():
    h = zustand_s3("unbekannt")
    assert h.sende(ev.TrackWechsel("s3", "cd", 1)) == [
        zeiger_speichern("s3", "cd", None, 0.0, "trackwechsel", track=1, art="folge")
    ]
    assert h.modus == "unbekannt"
    # Frist läuft weiter: Pause mit dem neuen Zeiger
    out = h.takt(3.2)
    assert ev.Pausieren("leser_unbekannt") in out and h.modus == "pausiert" and h.z.track == 1


def test_track_wechsel_beim_ausblenden_wegen_stumm_fuehrt_nach_und_blendet_weiter_aus():
    h = cd_spielt(UID_S3)
    h.sende(ev.StummBeginnt())
    assert h.z.ausblenden is not None
    assert h.sende(ev.TrackWechsel("s3", "cd", 1)) == [
        zeiger_speichern("s3", "cd", 0, 0.0, "trackwechsel", track=1)
    ]
    assert h.z.ausblenden is not None and h.modus == "spielt"
    out = h.takt(3.1)
    assert ev.Pausieren("stumm") in out and h.modus == "gehalten"
    assert h.z.track == 1


def test_track_wechsel_in_der_mpd_frist_fuehrt_nach():
    h = cd_spielt(UID_S3)
    h.sende(ev.PlayerVerbindung(False))
    assert h.z.mpd_bis is not None
    assert h.sende(ev.TrackWechsel("s3", "cd", 1)) == [
        zeiger_speichern("s3", "cd", 0, 0.0, "trackwechsel", track=1)
    ]
    assert h.z.mpd_bis is not None and h.modus == "spielt"


# --- FolgeZuEnde je Ziel -------------------------------------------------------------


def test_folge_zu_ende_ziel_serie_zeiger_auf_naechste_folge_track_0():
    h = cd_spielt(UID_S3, track=0)
    h.sende(ev.TrackWechsel("s3", "cd", 2))
    h.position("s3", "cd", 99.0, track=2)
    out = h.sende(ev.FolgeZuEnde("s3", "cd"))
    assert out == [
        zeiger_speichern("s3", "z.mp3", 1, 0.0, "folgenende", track=0),
        ev.Pausieren("folgenende"),
    ]
    assert h.modus == "beendet" and h.z.ende == ("s3", "cd")


def test_folge_zu_ende_ziel_serie_nach_der_letzten_folge_auf_folge_1():
    h = SitzungsHarnisch(zeiger=(zeiger("s3", "z.mp3", 1, 0.0, 1),))
    h.auflegen(UID_S3)
    h.position("s3", "z.mp3", 3.0)
    out = h.sende(ev.FolgeZuEnde("s3", "z.mp3"))
    assert out[0] == zeiger_speichern("s3", "cd", 0, 0.0, "folgenende", track=0)


def test_folge_zu_ende_ziel_folge_zeiger_springt_auf_track_0_position_0():
    h = cd_spielt(UID_CD)
    h.sende(ev.TrackWechsel("s3", "cd", 2))
    h.position("s3", "cd", 99.0, track=2)
    out = h.sende(ev.FolgeZuEnde("s3", "cd"))
    # der Folgen-Zeiger stand auf Track 2 (TrackWechsel); er springt zurück auf Track 0 / 0 s
    assert out == [
        zeiger_speichern("s3", "cd", None, 0.0, "folgenende", track=0, art="folge"),
        ev.Pausieren("folgenende"),
    ]
    assert h.modus == "beendet"
    assert (h.z.datei, h.z.track, h.z.position_s) == ("cd", 0, 0.0)


def test_serien_zeiger_derselben_serie_bleibt_beim_folgen_tobie_unberuehrt():
    sz = zeiger("s3", "z.mp3", 1, 8.0, 3)
    h = SitzungsHarnisch(zeiger=(sz,))
    h.auflegen(UID_CD)
    h.position("s3", "cd", 5.0)
    h.sende(ev.TrackWechsel("s3", "cd", 1))
    h.sende(ev.FolgeZuEnde("s3", "cd"))
    h.sende(ev.Abgehoben(1, "v1"))
    assert h.z.zeiger[("serie", "s3", "")] == sz
    assert h.z.zeiger[("folge", "s3", "cd")].track == 0


def test_folge_zu_ende_wiederauflegen_folgen_tobie_spielt_von_vorn_serien_tobie_naechste_folge():
    h = cd_spielt(UID_CD)
    h.sende(ev.FolgeZuEnde("s3", "cd"))
    h.sende(ev.Abgehoben(1, "v1"))
    assert h.auflegen(UID_CD, "v2") == [ab_cd(0.0, 0, "v2")]
    h = cd_spielt(UID_S3)
    h.sende(ev.FolgeZuEnde("s3", "cd"))
    h.sende(ev.Abgehoben(1, "v1"))
    assert h.auflegen(UID_S3, "v2") == [abspielen("s3", "s3", "z.mp3", 0.0, "v2")]


def test_folge_zu_ende_in_unbekannt_geht_nach_beendet_mit_zeiger_je_ziel():
    h = zustand_s3("unbekannt", UID_CD)
    out = h.sende(ev.FolgeZuEnde("s3", "cd"))
    assert out == [
        zeiger_speichern("s3", "cd", None, 0.0, "folgenende", track=0, art="folge"),
        ev.Pausieren("folgenende"),
    ]
    assert h.modus == "beendet" and h.z.unbekannt_seit is None and h.z.figur is not None
    assert h.takt(5.0) == []  # die verworfene Leser-Frist pausiert nicht noch einmal
    h = zustand_s3("unbekannt", UID_S3)
    out = h.sende(ev.FolgeZuEnde("s3", "cd"))
    assert out[0] == zeiger_speichern("s3", "z.mp3", 1, 0.0, "folgenende")
    assert h.modus == "beendet"


def test_folge_zu_ende_beim_ausblenden_wegen_stumm_geht_nach_gehalten_zeiger_je_ziel():
    h = cd_spielt(UID_S3)
    h.sende(ev.StummBeginnt())
    out = h.sende(ev.FolgeZuEnde("s3", "cd"))
    assert out == [
        ev.GrenzeGesetzt("ausblenden", None),
        zeiger_speichern("s3", "z.mp3", 1, 0.0, "folgenende"),
        ev.Pausieren("folgenende"),
    ]
    assert h.modus == "gehalten" and h.z.ausblenden is None
    assert h.sende(ev.StummEndet()) == [] and h.modus == "pausiert"
    h = cd_spielt(UID_CD)
    h.sende(ev.StummBeginnt())
    out = h.sende(ev.FolgeZuEnde("s3", "cd"))
    assert out == [
        ev.GrenzeGesetzt("ausblenden", None),
        zeiger_speichern("s3", "cd", None, 0.0, "folgenende", track=0, art="folge"),
        ev.Pausieren("folgenende"),
    ]
    assert h.modus == "gehalten"


def test_folge_zu_ende_in_der_mpd_frist_geht_nach_beendet_und_verwirft_die_frist():
    h = cd_spielt(UID_S3)
    h.sende(ev.PlayerVerbindung(False))
    out = h.sende(ev.FolgeZuEnde("s3", "cd"))
    assert out[-1] == ev.Pausieren("folgenende")
    assert h.modus == "beendet" and h.z.mpd_bis is None and not h.z.mpd_verloren
    assert h.takt(6.0) == []  # nichts mehr: keine zweite Pause nach der Frist


def test_folge_zu_ende_fremde_folge_wird_ignoriert_auch_bei_cd():
    h = cd_spielt()
    assert h.sende(ev.FolgeZuEnde("s3", "z.mp3")) == [] and h.modus == "spielt"


# --- PlayerPosition (6.3, Entscheidung F) ------------------------------------------


@pytest.mark.parametrize("zustand", ["spielt", "unbekannt"])
def test_position_wird_in_zustaenden_mit_laufendem_mpd_uebernommen(zustand):
    h = zustand_s3(zustand)
    h.position("s3", "cd", 33.3, 0)
    assert h.z.position_s == 33.3


@pytest.mark.parametrize("zustand", ["leer", "pausiert", "pausiert_ohne_figur", "beendet", "gehalten"])
def test_position_wird_ausserhalb_von_spielt_und_unbekannt_ignoriert(zustand):
    h = zustand_s3(zustand)
    vorher = h.z
    h.position("s3", "cd", 77.0, 0)
    assert h.z == vorher


@pytest.mark.parametrize(
    "serie, datei, track",
    [("s2", "cd", 0), ("s3", "z.mp3", 0), ("s3", "cd", 1), ("s3", "cd", 2)],
)
def test_position_mit_anderer_serie_folge_oder_track_wird_ignoriert(serie, datei, track):
    h = cd_spielt(sek=12.0)
    h.position(serie, datei, 88.0, track)
    assert h.z.position_s == 12.0


def test_veraltete_position_ueberschreibt_nach_track_wechsel_den_zeiger_nicht():
    h = cd_spielt(UID_S3, sek=50.0)
    h.sende(ev.TrackWechsel("s3", "cd", 1))
    h.position("s3", "cd", 51.0, track=0)  # kam noch vom alten Track
    assert (h.z.track, h.z.position_s) == (1, 0.0)
    out = h.sende(ev.Abgehoben(1, "v1"))
    assert zeiger_speichern("s3", "cd", 0, 0.0, "pause", track=1) not in out  # unverändert zum TrackWechsel-Zeiger
    assert h.z.zeiger[("serie", "s3", "")].track == 1 and h.z.zeiger[("serie", "s3", "")].position_s == 0.0


def test_veraltete_position_nach_folge_zu_ende_aendert_den_zeiger_nicht():
    h = cd_spielt(UID_S3, sek=50.0)
    h.sende(ev.FolgeZuEnde("s3", "cd"))
    zeiger_vorher = dict(h.z.zeiger)
    h.position("s3", "cd", 61.0, track=0)  # Endposition kommt nach dem Ende
    h.sende(ev.Abgehoben(1, "v1"))
    assert dict(h.z.zeiger) == zeiger_vorher
    assert zeiger_vorher[("serie", "s3", "")].datei == "z.mp3" and zeiger_vorher[("serie", "s3", "")].position_s == 0.0


def test_position_in_der_pause_nach_pausieren_aendert_den_zeiger_nicht():
    """Die Position, die der Player nach ``Pausieren`` sofort sendet, trifft auf ``pausiert``: ignoriert."""
    h = cd_spielt(UID_S3, sek=10.0)
    h.sende(ev.Hauptknopf("kurz"))
    gespeichert = h.z.zeiger[("serie", "s3", "")]
    h.position("s3", "cd", 11.0, 0)
    assert h.z.zeiger[("serie", "s3", "")] == gespeichert and h.z.position_s == 10.0


# --- Vor / Zurück nach Track ----------------------------------------------------------


@pytest.mark.parametrize("uid, art, index", [(UID_CD, "folge", None), (UID_S3, "serie", 0)])
@pytest.mark.parametrize("zustand", ["spielt", "pausiert"])
def test_weiter_springt_zum_naechsten_track_derselben_folge(uid, art, index, zustand):
    h = zustand_s3(zustand, uid)
    assert h.sende(ev.Weiter()) == [
        zeiger_speichern("s3", "cd", index, 0.0, "trackwechsel", track=1, art=art),
        ab_cd(0.0, 1),
    ]
    assert h.modus == "spielt"


def test_weiter_beim_letzten_track_ziel_serie_erster_track_der_naechsten_folge():
    h = cd_spielt(UID_S3)
    h.sende(ev.TrackWechsel("s3", "cd", 2))
    assert h.sende(ev.Weiter()) == [
        zeiger_speichern("s3", "z.mp3", 1, 0.0, "folgenende"),
        abspielen("s3", "s3", "z.mp3", 0.0, "v1"),
    ]
    assert h.modus == "spielt"


def test_weiter_beim_letzten_track_ziel_folge_nur_hinweiston_nichts_aendert_sich():
    h = cd_spielt(UID_CD)
    h.sende(ev.TrackWechsel("s3", "cd", 2))
    zustand = h.z
    assert h.sende(ev.Weiter()) == [ev.TonSpielen("hinweis")]
    assert h.z == zustand and h.modus == "spielt"
    # auch ein Folgen-Tobie auf eine Datei hat nur einen Track
    h = SitzungsHarnisch()
    h.auflegen(UID_FOLGE)
    assert h.sende(ev.Weiter()) == [ev.TonSpielen("hinweis")]


@pytest.mark.parametrize("uid, art, index", [(UID_CD, "folge", None), (UID_S3, "serie", 0)])
def test_zurueck_unter_3_s_springt_zum_vorigen_track(uid, art, index):
    h = cd_spielt(uid, sek=2.9, track=0)
    h.sende(ev.TrackWechsel("s3", "cd", 1))
    h.position("s3", "cd", 2.9, track=1)
    assert h.sende(ev.Zurueck()) == [
        zeiger_speichern("s3", "cd", index, 0.0, "trackwechsel", track=0, art=art),
        ab_cd(0.0, 0),
    ]


def test_zurueck_ab_3_s_startet_den_aktuellen_track_neu():
    h = cd_spielt(UID_S3, sek=3.0, track=0)
    h.sende(ev.TrackWechsel("s3", "cd", 1))
    h.position("s3", "cd", 3.0, track=1)
    assert h.sende(ev.Zurueck()) == [ab_cd(0.0, 1)]  # Zeiger steht schon auf Track 1, Position 0: unverändert


def test_zurueck_im_ersten_track_startet_den_track_neu_auch_unter_3_s():
    h = cd_spielt(UID_S3, sek=1.0, track=0)
    assert h.sende(ev.Zurueck()) == [
        zeiger_speichern("s3", "cd", 0, 0.0, "trackwechsel", track=0),
        ab_cd(0.0, 0),
    ]


def test_weiter_zurueck_in_pausiert_starten_die_wiedergabe_am_neuen_track():
    h = zustand_s3("pausiert", UID_S3)
    out = h.sende(ev.Weiter())
    assert out[-1] == ab_cd(0.0, 1) and h.modus == "spielt"


def test_weiter_zurueck_springen_nur_nach_dem_zustand_wie_im_vertrag():
    # „leer“ ohne Tobie: nur der Hinweiston (Entscheidung Q, 10.11.); „unbekannt“: keine Wirkung
    h = zustand_s3("leer")
    assert h.sende(ev.Weiter()) == [ev.TonSpielen("hinweis")] and h.sende(ev.Zurueck()) == [ev.TonSpielen("hinweis")]
    h = zustand_s3("unbekannt")
    assert h.sende(ev.Weiter()) == [] and h.sende(ev.Zurueck()) == []


# --- beendet: Hauptknopf, Weiter, Zurück je Ziel ---------------------------------------


@pytest.mark.parametrize(
    "ereignis",
    [ev.Hauptknopf("kurz"), ev.Weiter()],
    ids=["hauptknopf", "weiter"],
)
def test_beendet_hauptknopf_und_weiter_ziel_serie_spielt_die_naechste_folge(ereignis):
    h = zustand_s3("beendet", UID_S3)
    assert h.sende(ereignis) == [abspielen("s3", "s3", "z.mp3", 0.0, "v1")]
    assert h.modus == "spielt"


@pytest.mark.parametrize(
    "ereignis",
    [ev.Hauptknopf("kurz"), ev.Weiter()],
    ids=["hauptknopf", "weiter"],
)
def test_beendet_hauptknopf_und_weiter_ziel_folge_spielt_dieselbe_folge_von_vorn(ereignis):
    h = zustand_s3("beendet", UID_CD)
    assert h.sende(ereignis) == [ab_cd(0.0, 0)]
    assert h.modus == "spielt"


def test_beendet_zurueck_ziel_serie_spielt_die_eben_beendete_folge_index_per_nachschlagen():
    h = zustand_s3("beendet", UID_S3)  # cd ist zu Ende, Zeiger steht auf z.mp3 (Index 1)
    assert h.z.datei == "z.mp3" and h.z.index == 1
    out = h.sende(ev.Zurueck())
    assert out == [zeiger_speichern("s3", "cd", 0, 0.0, "zurueck", track=0), ab_cd(0.0, 0)]
    assert h.modus == "spielt" and (h.z.datei, h.z.index) == ("cd", 0)
    assert h.z.zeiger[("serie", "s3", "")].datei == "cd"


def test_beendet_zurueck_ziel_folge_spielt_dieselbe_folge_von_vorn_ohne_neues_speichern():
    h = zustand_s3("beendet", UID_CD)
    out = h.sende(ev.Zurueck())
    assert out == [ab_cd(0.0, 0)]  # der Folgen-Zeiger steht schon auf Track 0 / 0 s
    assert h.modus == "spielt"


def test_beendet_zurueck_index_wird_nachgeschlagen_nicht_aus_dem_alten_zustand_genommen():
    """Bibliothek ändert sich im beendet-Zustand: die beendete Folge steht jetzt an anderer Stelle."""
    h = zustand_s3("beendet", UID_S3)
    neu = ev.Serie("s3", "Serie 3", "normal", "s3", ("neu.mp3", "cd", "z.mp3"), S3.tracks | {"neu.mp3": ("neu.mp3",)})
    h.sende(ev.BibliothekGeladen((S1, S2, UEB, neu)))
    out = h.sende(ev.Zurueck())
    assert out[0] == zeiger_speichern("s3", "cd", 1, 0.0, "zurueck", track=0)


def test_beendet_zurueck_beendete_folge_fehlt_inzwischen_nur_hinweiston():
    h = zustand_s3("beendet", UID_S3)
    ohne = ev.Serie("s3", "Serie 3", "normal", "s3", ("z.mp3",))
    h.sende(ev.BibliothekGeladen((S1, S2, UEB, ohne)))
    assert h.sende(ev.Zurueck()) == [ev.TonSpielen("hinweis")] and h.modus == "beendet"


@pytest.mark.parametrize("uid", [UID_CD, UID_S3])
@pytest.mark.parametrize("ereignis", [ev.Hauptknopf("kurz"), ev.Weiter(), ev.Zurueck()])
@pytest.mark.parametrize("zustand", ["pausiert", "beendet", "gehalten"])
def test_stumm_sperrt_hauptknopf_vor_zurueck_in_pausiert_beendet_gehalten(uid, ereignis, zustand):
    h = zustand_s3(zustand, uid)
    if zustand != "gehalten":
        h.sende(ev.StummBeginnt())
    zeiger_vorher = dict(h.z.zeiger)
    assert h.sende(ereignis) == [ev.TonSpielen("hinweis")]
    assert h.modus == zustand and dict(h.z.zeiger) == zeiger_vorher


def test_beendet_wird_nicht_gespeichert_nach_neustart_beginnt_die_sitzung_ohne_wiedergabe():
    """Serie s3 ist zu Ende; der Zeiger steht auf z.mp3. Nach einem Neustart gibt es nur den Zeiger."""
    h = zustand_s3("beendet", UID_S3)
    gespeichert = tuple(h.z.zeiger.values())
    neu = SitzungsHarnisch(zeiger=gespeichert)
    assert neu.modus == "leer" and neu.z.ende is None
    # ohne Tobie nur der Hinweiston (Entscheidung Q, 10.11.)
    assert neu.sende(ev.Zurueck()) == [ev.TonSpielen("hinweis")] and neu.sende(ev.Hauptknopf("kurz")) == [ev.TonSpielen("hinweis")]
    assert neu.auflegen(UID_S3) == [abspielen("s3", "s3", "z.mp3", 0.0, "v1")]


# --- KonfigGeladen mit Ziel folge (9.14) --------------------------------------------------


def konfig_ziel(uid, zuordnung):
    z = dict(ZUORDNUNGEN)
    z[uid] = zuordnung
    return ev.KonfigGeladen(mk_konfig(z))


def test_konfig_mit_ziel_folge_wechselt_bei_liegender_figur_in_spielt():
    h = unbekannte_figur_liegt("spielt")
    out = h.sende(konfig_ziel(UID_UNBEKANNT, ev.Zuordnung("folge", "s3", "cd")))
    assert out == [zeiger_speichern("ueb", "u1.mp3", 0, 4.0, "figurwechsel"), ab_cd(0.0, 0)]
    assert (h.modus, h.z.ziel, h.z.datei) == ("spielt", "folge", "cd")


@pytest.mark.parametrize("zustand", ["pausiert", "beendet"])
def test_konfig_mit_ziel_folge_startet_in_pause_oder_ende(zustand):
    h = unbekannte_figur_liegt(zustand)
    assert h.sende(konfig_ziel(UID_UNBEKANNT, ev.Zuordnung("folge", "s3", "cd"))) == [ab_cd(0.0, 0)]
    assert h.modus == "spielt"


def test_konfig_mit_ziel_folge_unter_stumm_nur_hinweiston():
    h = unbekannte_figur_liegt("pausiert")
    h.sende(ev.StummBeginnt())
    assert h.sende(konfig_ziel(UID_UNBEKANNT, ev.Zuordnung("folge", "s3", "cd"))) == [ev.TonSpielen("hinweis")]
    assert h.modus == "pausiert"


def test_konfig_in_gehalten_unbekannt_leer_mit_ziel_folge_nichts():
    for zustand in ("gehalten", "unbekannt", "leer"):
        h = zustand_s3(zustand, UID_S1)
        assert h.sende(konfig_ziel(UID_S1, ev.Zuordnung("folge", "s3", "cd"))) == []


def test_konfig_ziel_folge_unveraendert_nichts():
    h = cd_spielt(UID_CD)
    assert h.sende(konfig_ziel(UID_CD, ev.Zuordnung("folge", "s3", "cd"))) == []


def test_konfig_wechsel_von_serie_auf_folge_derselben_serie_ist_ein_anderes_ziel():
    h = cd_spielt(UID_S3)
    out = h.sende(konfig_ziel(UID_S3, ev.Zuordnung("folge", "s3", "z.mp3")))
    assert out[-1] == abspielen("s3", "s3", "z.mp3", 0.0, "v1") and h.z.ziel == "folge"


def test_konfig_wechsel_auf_andere_folge_derselben_serie():
    h = cd_spielt(UID_CD)
    out = h.sende(konfig_ziel(UID_CD, ev.Zuordnung("folge", "s3", "z.mp3")))
    assert out[-1] == abspielen("s3", "s3", "z.mp3", 0.0, "v1")


def test_konfig_ziel_folge_fehlt_in_der_serie_nichts():
    h = unbekannte_figur_liegt("spielt")
    assert h.sende(konfig_ziel(UID_UNBEKANNT, ev.Zuordnung("folge", "s3", "gibt-es-nicht"))) == []
    assert h.z.serie_id == "ueb"


# --- Fortsetzen nach MPD-Verlust mit Track -------------------------------------------------


@pytest.mark.parametrize("uid", [UID_CD, UID_S3])
def test_mpd_zurueck_innerhalb_der_frist_setzt_mit_track_und_position_fort(uid):
    h = cd_spielt(uid)
    h.sende(ev.TrackWechsel("s3", "cd", 2))
    h.position("s3", "cd", 40.0, track=2)
    h.sende(ev.PlayerVerbindung(False))
    out = h.sende(ev.PlayerVerbindung(True), dt=1.0)
    assert out == [ev.AusgangWaehlen("lautsprecher"), ab_cd(37.0, 2)]
    assert h.modus == "spielt"


# --- Leser-Neustart startet nie eine Wiedergabe (9.1) -----------------------------------------


@pytest.mark.parametrize("uid", [UID_CD, UID_FOLGE, UID_S3])
def test_leser_neustart_startet_nie_eine_wiedergabe_auch_nicht_mit_folgen_zeiger(uid):
    fz = zeiger("s3", "cd", None, 30.0, 2, track=1, art="folge")
    h = SitzungsHarnisch(zeiger=(fz,))
    h.auflegen(uid, "v1")
    h.sende(ev.Abgehoben(1, "v1"))
    h.auflegen(uid, "v2")
    h.position(h.z.serie_id, h.z.datei, 5.0, h.z.track)
    h.sende(ev.Hauptknopf("kurz"))  # pausiert, der Tobie liegt
    assert h.modus == "pausiert"
    for e in (ev.LeserAlarm("kein_herzschlag"), ev.LeserHallo(1, "1.0", "b", "p")):
        assert h.sende(e) == []
    assert h.sende(A(uid, "v2")) == []  # Wiedermeldung, gleiche Vorgangs-ID
    assert not any(isinstance(o, ev.Abspielen) for o in h.voll)
    assert h.modus == "pausiert"


def test_leser_neustart_waehrend_spielt_mit_folgen_zeiger_setzt_nach_unbekannt_ohne_neustart_fort():
    h = cd_spielt(UID_CD)
    h.sende(ev.TrackWechsel("s3", "cd", 1))
    h.sende(ev.LeserHallo(1, "1.0", "b", "p"), dt=0.1)
    assert h.modus == "unbekannt"
    n = len([o for o in h.alle if isinstance(o, ev.Abspielen)])
    assert h.sende(A(UID_CD, "v1"), dt=0.2) == []  # derselbe Tobie innerhalb der Frist
    assert h.modus == "spielt" and len([o for o in h.alle if isinstance(o, ev.Abspielen)]) == n


def test_leser_neustart_nach_abgelaufener_frist_startet_den_folgen_tobie_nicht_neu():
    h = cd_spielt(UID_CD)
    h.sende(ev.LeserAlarm("kein_herzschlag"))
    h.takt(3.2)
    assert h.modus == "pausiert"
    n = len([o for o in h.alle if isinstance(o, ev.Abspielen)])
    h.sende(ev.LeserHallo(1, "1.0", "b", "p"))
    assert h.sende(A(UID_CD, "v1")) == []
    assert len([o for o in h.alle if isinstance(o, ev.Abspielen)]) == n


# --- Hauptknopf kurz je Zustand mit Folgen-Tobie (hier statt eigener Datei) -------------------


HAUPTKNOPF_FOLGE = [
    # (Zustand, Tobie, erwartete Befehle, neuer Zustand)
    ("spielt", UID_CD, [ev.Pausieren("knopf"), zeiger_speichern("s3", "cd", None, 10.0, "pause", art="folge")], "pausiert"),
    ("pausiert", UID_CD, [ab_cd(7.0, 0)], "spielt"),
    ("pausiert_ohne_figur", UID_CD, [ev.TonSpielen("hinweis")], "pausiert"),  # Entscheidung Q, 10.11.
    ("beendet", UID_CD, [ab_cd(0.0, 0)], "spielt"),
    ("beendet", UID_S3, [abspielen("s3", "s3", "z.mp3", 0.0, "v1")], "spielt"),
    ("leer", UID_CD, [ev.TonSpielen("hinweis")], "leer"),  # Entscheidung Q, 10.11.
    ("unbekannt", UID_CD, [], "unbekannt"),
    ("gehalten", UID_CD, [ev.TonSpielen("hinweis")], "gehalten"),  # „gehalten“ gibt es nur unter stumm
]


@pytest.mark.parametrize("zustand, uid, erwartet, neu", HAUPTKNOPF_FOLGE)
def test_hauptknopf_kurz_je_zustand_mit_folgen_tobie(zustand, uid, erwartet, neu):
    h = zustand_s3(zustand, uid)
    assert h.sende(ev.Hauptknopf("kurz")) == erwartet
    assert h.modus == neu.replace("_ohne_figur", "")


# --- PlayerFehler bei Folgen-Zeiger ---------------------------------------------------------------


def test_player_fehler_datei_fehlt_ziel_folge_dieselbe_folge_track_0_position_0():
    h = cd_spielt(UID_CD)
    h.sende(ev.TrackWechsel("s3", "cd", 1))
    out = h.sende(ev.PlayerFehler("s3", "cd", "datei_fehlt", "x"))
    assert out == [
        ev.TonSpielen("fehler"),
        ev.Pausieren("fehler"),
        zeiger_speichern("s3", "cd", None, 0.0, "pause", track=0, art="folge"),
    ]
    assert h.modus == "pausiert"


def test_player_fehler_datei_fehlt_ziel_serie_naechste_folge_track_0():
    h = cd_spielt(UID_S3)
    out = h.sende(ev.PlayerFehler("s3", "cd", "datei_unlesbar", "x"))
    assert zeiger_speichern("s3", "z.mp3", 1, 0.0, "pause", track=0) in out


# --- Schreibbudget (neu gerechnet, Entscheidung F) -----------------------------------------------


def test_schreibbudget_zwei_stunden_wiedergabe_hoechstens_320_zeiger_schreibungen():
    """2 h Wiedergabe, 40 Pausen (Hauptknopf zweimal) und 40 Track-Wechsel: höchstens 240 + 40 + 40.

    Die Position wandert jede Sekunde mit, damit jede periodische Schreibung wirklich nötig ist."""
    viele = tuple(f"rip/{i:02}.mp3" for i in range(60))
    gross = ev.Serie("gross", "Gross", "normal", "gross", ("rip",), {"rip": viele})
    h = SitzungsHarnisch(serien=(S1, S2, UEB, gross))
    h.sende(konfig_mit("04a1b2d0", "gross"))
    h.auflegen("04a1b2d0")

    def zaehle(out) -> int:
        return sum(isinstance(o, ev.ZeigerSpeichern) for o in out)

    schreibungen = track = pausen = 0
    sek = 0.0
    for s in range(1, 7201):
        for _ in range(10):
            schreibungen += zaehle(h.sende(ev.Takt(), dt=0.1))
        sek += 1.0
        h.position("gross", "rip", sek, track)
        if s % 180 == 0 and track < 40:  # 40 Track-Wechsel
            track += 1
            schreibungen += zaehle(h.sende(ev.TrackWechsel("gross", "rip", track)))
            sek = 0.0
        if s % 180 == 90 and pausen < 40:  # 40 Pausen: Hauptknopf kurz (Pause), Hauptknopf kurz (weiter)
            schreibungen += zaehle(h.sende(ev.Hauptknopf("kurz")))
            schreibungen += zaehle(h.sende(ev.Hauptknopf("kurz")))
            sek = max(0.0, sek - 3.0)
            pausen += 1
    assert h.modus == "spielt" and track == 40 and pausen == 40
    assert 200 <= schreibungen <= 240 + 40 + 40, schreibungen


# --------------------------------------------------------------------------
# Dienst-Neustart mit liegendem Tobie (Entscheidung G, 06.11.)
# --------------------------------------------------------------------------

_ZEIGER_S1_B = zeiger("s1", "b.mp3", 1, 100.0, 3)


def _neustart_harnisch(uid=UID_S1, **kw) -> SitzungsHarnisch:
    return SitzungsHarnisch(zeiger=(_ZEIGER_S1_B,), neustart_uid=uid, **kw)


def test_neustart_liegender_tobie_bleibt_pausiert_still_und_zeigt_auf_den_zeiger():
    h = _neustart_harnisch()
    out = h.auflegen()
    assert out == []  # kein Ton, kein Abspielen
    z = h.z
    assert h.modus == "pausiert" and z.figur is not None and z.figur.uid == UID_S1
    assert (z.ziel, z.serie_id, z.datei, z.index, z.track, z.position_s) == ("serie", "s1", "b.mp3", 1, 0, 97.0)  # wie im Zweig „stumm“: Position mit Rücksprung
    assert z.neustart_uid is None


def test_neustart_hauptknopf_kurz_spielt_am_zeiger_mit_ruecksprung():
    h = _neustart_harnisch()
    h.auflegen()
    out = h.sende(ev.Hauptknopf("kurz"))
    assert out == [abspielen("s1", "s1", "b.mp3", 97.0, "v1")]
    assert h.modus == "spielt"


def test_neustart_abheben_und_wieder_auflegen_spielt():
    h = _neustart_harnisch()
    h.auflegen()
    h.sende(ev.Abgehoben(1, "v1"))
    out = h.auflegen(vorgang="v2")
    assert out == [abspielen("s1", "s1", "b.mp3", 97.0, "v2")]


def test_neustart_anderer_tobie_spielt_sofort_und_loescht_die_merkung():
    h = _neustart_harnisch(uid=UID_S1)
    out = h.auflegen(UID_S2)
    assert ev.Abspielen in typen(out) and h.modus == "spielt"
    assert h.z.neustart_uid is None


def test_neustart_tobie_gleich_aber_nicht_in_leer_spielt_normal():
    h = _neustart_harnisch()
    h.auflegen(UID_S2)  # anderer Tobie startet, die Merkung ist weg
    h.sende(ev.Abgehoben(1, "v1"))
    out = h.auflegen(UID_S1, vorgang="v2")
    assert ev.Abspielen in typen(out)


def test_neustart_herzschlag_ohne_tobie_loescht_die_merkung():
    h = _neustart_harnisch()
    h.sende(ev.LeserHerzschlag(False, 1, 1, 0, 0, 0, 50))
    assert h.z.neustart_uid is None
    assert ev.Abspielen in typen(h.auflegen())


def test_neustart_unter_stumm_bleibt_still_und_pausiert():
    h = _neustart_harnisch()
    h.sende(ev.StummBeginnt())
    assert h.auflegen() == []
    assert h.modus == "pausiert" and h.z.datei == "b.mp3"


def test_ohne_neustart_uid_startet_der_tobie_wie_in_cuj20():
    h = SitzungsHarnisch(zeiger=(_ZEIGER_S1_B,))
    assert ev.Abspielen in typen(h.auflegen())


def test_neustart_unbekannter_tobie_meldet_aber_spielt_nicht():
    h = _neustart_harnisch(uid=UID_UNBEKANNT)
    out = h.auflegen(UID_UNBEKANNT)
    assert ev.Abspielen not in typen(out) and ev.TonSpielen not in typen(out)
    assert out == [ev.Melden("unbekannt", UID_UNBEKANNT, None)] and h.modus == "pausiert"


# --------------------------------------------------------------------------
# Wiedergabe-Generation (gen)
# --------------------------------------------------------------------------


def _gens(out) -> list[int]:
    return [b.gen for b in out if isinstance(b, ev.Abspielen)]


def test_gen_waechst_mit_jedem_abspielen():
    h = SitzungsHarnisch()
    assert _gens(h.auflegen()) == [1]
    assert _gens(h.sende(ev.Weiter())) == [2]
    assert _gens(h.sende(ev.Zurueck())) == [3]
    assert h.z.gen == 3


def test_veraltete_position_nach_zurueck_im_selben_track_wird_ignoriert():
    h = SitzungsHarnisch()
    h.auflegen()
    h.sende(ev.PlayerPosition("s1", "a.mp3", 0, 50.0, True, 1))
    assert h.z.position_s == 50.0
    (a,) = [b for b in h.sende(ev.Zurueck()) if isinstance(b, ev.Abspielen)]  # Zurück in a.mp3: dieselbe Folge, Track
    assert (a.datei, a.track, a.gen) == ("a.mp3", 0, 2)
    # Nachzügler des alten Abspielens: gleiche Folge und Track, aber Generation 1
    h.sende(ev.PlayerPosition("s1", "a.mp3", 0, 52.0, True, 1))
    assert h.z.position_s == 0.0
    h.sende(ev.PlayerPosition("s1", "a.mp3", 0, 1.0, True, 2))
    assert h.z.position_s == 1.0


def test_veraltetes_folge_zu_ende_nach_weiter_auf_dieselbe_folge_wird_ignoriert():
    h = SitzungsHarnisch(serien=(S3,))
    h.auflegen(UID_CD)  # Folge „cd“ mit drei Tracks, Folgen-Tobie
    h.sende(ev.TrackWechsel("s3", "cd", 1, 1))
    h.sende(ev.TrackWechsel("s3", "cd", 2, 1))
    h.sende(ev.Zurueck())  # Zurück im Track (Position > 3 s) oder vorheriger Track, jedenfalls neues Abspielen, gen 2
    assert h.z.gen == 2 and h.modus == "spielt"
    out = h.sende(ev.FolgeZuEnde("s3", "cd", 1))  # Ende der alten Wiedergabe kommt zu spät
    assert out == [] and h.modus == "spielt"
    out = h.sende(ev.FolgeZuEnde("s3", "cd", 2))
    assert ev.Pausieren("folgenende") in out and h.modus == "beendet"


def test_veraltetes_track_wechsel_wird_ignoriert():
    h = SitzungsHarnisch(serien=(S3,))
    h.auflegen(UID_CD)
    h.sende(ev.Hauptknopf("kurz"))  # pausiert
    h.sende(ev.Hauptknopf("kurz"))  # spielt wieder, gen 2
    assert h.z.gen == 2
    assert h.sende(ev.TrackWechsel("s3", "cd", 1, 1)) == [] and h.z.track == 0
    h.sende(ev.TrackWechsel("s3", "cd", 1, 2))
    assert h.z.track == 1


def test_erster_track_fehlt_der_player_meldet_track_wechsel_die_sitzung_nimmt_ihn_an():
    h = SitzungsHarnisch(serien=(S3,))
    h.auflegen(UID_CD)
    assert h.z.track == 0
    h.sende(ev.TrackWechsel("s3", "cd", 1, 1))
    assert (h.z.track, h.z.position_s) == (1, 0.0) and h.modus == "spielt"
    h.sende(ev.PlayerPosition("s3", "cd", 1, 2.0, True, 1))
    assert h.z.position_s == 2.0


# --------------------------------------------------------------------------
# Protokollzeile „zugeordnet“: art nennt das Ziel (Fehler aus AP 2.2: „serie“ auch bei Folgen-Zielen)
# --------------------------------------------------------------------------


def _zugeordnet(h):
    (z,) = [p for p in h.alle if isinstance(p, ev.Protokoll) and p.ereignis == "zugeordnet"]
    return z


@pytest.mark.parametrize(
    "uid, art, ziel, ergebnis",
    [
        (UID_S1, "serie", "serie", "ok"),
        (UID_FOLGE, "folge", "folge", "ok"),
        (UID_CD, "folge", "folge", "ok"),
        (UID_UNBEKANNT, "unbekannt", "serie", "ueberraschung"),
        (UID_FOLGE_FEHLT, "serie", "serie", "ueberraschung"),  # Folge fehlt: Überraschungs-Serie
    ],
)
def test_zugeordnet_art_nennt_serie_oder_folge(uid, art, ziel, ergebnis):
    h = SitzungsHarnisch()
    h.auflegen(uid)
    z = _zugeordnet(h)
    assert (z.daten["art"], z.daten["ziel"], z.ergebnis) == (art, ziel, ergebnis)


def test_zugeordnet_art_gesperrt():
    h = SitzungsHarnisch()
    h.sende(ev.Gesperrt(0, "v1"))
    assert _zugeordnet(h).daten["art"] == "gesperrt"


# --- Sync-Bedarf bei fehlenden Medien (12.11.) ----------------------------------------------------------


def bedarf(h, ab=0):
    return [x.grund for x in h.alle[ab:] if isinstance(x, ev.SyncBedarf)]


def test_konfig_mit_fehlender_serie_meldet_sync_bedarf():
    h = SitzungsHarnisch(konfig=False)
    h.sende(ev.KonfigGeladen(mk_konfig({UID_S1: ev.Zuordnung("serie", "s1"), UID_S2: ev.Zuordnung("serie", "neu")})))
    assert bedarf(h) == ["konfig_neu"]


def test_konfig_mit_fehlender_folge_meldet_sync_bedarf():
    h = SitzungsHarnisch(konfig=False)
    h.sende(ev.KonfigGeladen(mk_konfig({UID_S1: ev.Zuordnung("folge", "s1", "neu.mp3")})))
    assert bedarf(h) == ["konfig_neu"]


def test_konfig_mit_vorhandenen_zielen_und_aktionen_kein_bedarf():
    h = SitzungsHarnisch(konfig=False)
    h.sende(ev.KonfigGeladen(mk_konfig({
        UID_S1: ev.Zuordnung("serie", "s1"), UID_FOLGE: ev.Zuordnung("folge", "s1", "b.mp3"),
        UID_NACHT: ev.Zuordnung("aktion", aktion="gute_nacht"),
    })))
    assert bedarf(h) == []


def test_konfig_vor_der_bibliothek_meldet_keinen_bedarf():
    h = SitzungsHarnisch(serien=(), konfig=False)
    h.z = session.neuer_zustand()  # wie beim Start: erst die Konfiguration, die Bibliothek kommt danach
    h.sende(ev.KonfigGeladen(mk_konfig({UID_S1: ev.Zuordnung("serie", "s1")})))
    assert bedarf(h) == []


def test_auflegen_mit_fehlendem_ziel_meldet_ziel_fehlt():
    h = SitzungsHarnisch()
    h.auflegen(UID_FEHLT)
    assert bedarf(h)[-1:] == ["ziel_fehlt"]
    n = len(h.alle)
    h.auflegen(UID_FOLGE_FEHLT, vorgang="v2")
    assert bedarf(h, n) == ["ziel_fehlt"]


def test_auflegen_mit_vorhandenem_ziel_oder_unbekanntem_tobie_kein_ziel_fehlt():
    h = SitzungsHarnisch()
    n = len(h.alle)
    h.auflegen(UID_S1)
    h.auflegen(UID_UNBEKANNT, vorgang="v2")
    assert "ziel_fehlt" not in bedarf(h, n)
