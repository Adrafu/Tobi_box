"""Teilautomat ``session``: jede Zeile der Tabelle „Wiedergabe-Sitzung“ und die
Festlegungen aus ``core-interface.md`` (Abschnitte 6.3, 8, 9) als parametrisierte Tests."""

from __future__ import annotations

import pytest
from conftest import (
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


ABSPIELEN_S1_NEU = ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v2")
ABSPIELEN_UEB = ev.Abspielen("ueb", "ueb", "u1.mp3", 0.0, "v2")
ZEIGER_S1_PAUSE = ev.ZeigerSpeichern("s1", "a.mp3", 0, 10.0, "pause")

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
        [ev.Abspielen("s1", "s1", "a.mp3", 7.0, "v2")],
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
        [ev.ZeigerSpeichern("s1", "a.mp3", 0, 10.0, "figurwechsel"), ev.Abspielen("s2", "s2", "x.mp3", 0.0, "v2")],
        "spielt",
    ),
    (
        "spielt|Folge zu Ende (nicht die letzte)",
        "spielt",
        lambda h: h.sende(ev.FolgeZuEnde("s1", "a.mp3")),
        [ev.ZeigerSpeichern("s1", "b.mp3", 1, 0.0, "folgenende"), ev.Pausieren("folgenende")],
        "beendet",
    ),
    ("beendet|REMOVED", "beendet", lambda h: h.sende(ev.Abgehoben(1, "v1")), [], "pausiert"),
    (
        "beendet (Figur liegt)|Hauptknopf kurz",
        "beendet",
        lambda h: h.sende(ev.Hauptknopf("kurz")),
        [ev.Abspielen("s1", "s1", "b.mp3", 0.0, "v1")],
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
        [ev.Abspielen("s1", "s1", "a.mp3", 7.0, "v1")],
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
    assert h.auflegen(UID_S1, "v7") == [ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v7")]
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
    assert h.sende(ev.Hauptknopf("kurz")) == [ev.Abspielen("s1", "s1", "a.mp3", 7.0, "v1")]


def test_unbekannt_andere_kennung_beendet_die_frist_figurwechsel():
    """Konflikt-Tabelle: Figurwechsel während einer Leser-Unterbrechung."""
    h = in_zustand("unbekannt")
    h.sende(ev.LeserHallo(1, "1.0.0", "a1b2c3d", "4.2"))
    out = h.sende(A(UID_S2, "v2", 0))
    assert out == [
        ev.Pausieren("leser_unbekannt"),
        ev.ZeigerSpeichern("s1", "a.mp3", 0, 10.0, "figurwechsel"),
        ev.Abspielen("s2", "s2", "x.mp3", 0.0, "v2"),
    ]
    assert h.modus == "spielt"


def test_unbekannt_gesperrt_statt_kennung_ist_anderer_vorgang():
    h = in_zustand("unbekannt")
    out = h.sende(G("v2", 0))
    assert out == [
        ev.Pausieren("leser_unbekannt"),
        ev.ZeigerSpeichern("s1", "a.mp3", 0, 10.0, "figurwechsel"),
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
        ev.ZeigerSpeichern("s1", "a.mp3", 0, 10.0, "figurwechsel"),
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
    assert out == [ev.Pausieren("herunterfahren"), ev.ZeigerSpeichern("s1", "a.mp3", 0, 10.0, "herunterfahren")]
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
        ("datei_fehlt", [ev.ZeigerSpeichern("s1", "b.mp3", 1, 0.0, "pause")]),
        ("datei_unlesbar", [ev.ZeigerSpeichern("s1", "b.mp3", 1, 0.0, "pause")]),
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
    h = SitzungsHarnisch(zeiger=(ev.Zeiger("s1", "c.mp3", 2, 0.0, 1),))
    h.auflegen()
    h.position("s1", "c.mp3", 5.0)
    out = h.sende(ev.PlayerFehler("s1", "c.mp3", "datei_fehlt", ""))
    assert ev.ZeigerSpeichern("s1", "a.mp3", 0, 0.0, "pause") in out


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
    assert out == [ev.AusgangWaehlen(ausgang), ev.Abspielen("s1", "s1", "a.mp3", 7.0, "v1")]
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
    ("pausiert", False, [ev.Abspielen("s1", "s1", "a.mp3", 7.0, "v1")], "spielt"),
    ("pausiert_ohne_figur", False, [ev.Abspielen("s1", "s1", "a.mp3", 7.0, None)], "spielt"),
    ("beendet", False, [ev.Abspielen("s1", "s1", "b.mp3", 0.0, "v1")], "spielt"),
    ("leer", False, [], "leer"),
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
    ("spielt", ev.Weiter(), False, [ev.ZeigerSpeichern("s1", "b.mp3", 1, 0.0, "folgenende"), ev.Abspielen("s1", "s1", "b.mp3", 0.0, "v1")], "spielt"),
    ("spielt", ev.Zurueck(), False, [ev.ZeigerSpeichern("s1", "c.mp3", 2, 0.0, "folgenende"), ev.Abspielen("s1", "s1", "c.mp3", 0.0, "v1")], "spielt"),
    ("pausiert", ev.Weiter(), False, [ev.ZeigerSpeichern("s1", "b.mp3", 1, 0.0, "folgenende"), ev.Abspielen("s1", "s1", "b.mp3", 0.0, "v1")], "spielt"),
    ("pausiert_ohne_figur", ev.Zurueck(), False, [ev.ZeigerSpeichern("s1", "c.mp3", 2, 0.0, "folgenende"), ev.Abspielen("s1", "s1", "c.mp3", 0.0, None)], "spielt"),
    ("beendet", ev.Weiter(), False, [ev.Abspielen("s1", "s1", "b.mp3", 0.0, "v1")], "spielt"),
    # Zurueck in beendet: die eben beendete Folge (vor dem Zeiger), Position 0 (05.11.)
    ("beendet", ev.Zurueck(), False, [ev.ZeigerSpeichern("s1", "a.mp3", 0, 0.0, "folgenende"), ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v1")], "spielt"),
    ("leer", ev.Weiter(), False, [], "leer"),
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
        ev.ZeigerSpeichern("ueb", "u1.mp3", 0, 4.0, "figurwechsel"),
        ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v1"),
    ]
    assert h.modus == "spielt" and h.z.serie_id == "s1"


@pytest.mark.parametrize("zustand", ["pausiert", "beendet"])
def test_konfig_bei_liegender_figur_in_pause_oder_ende_startet_die_neue_serie(zustand):
    h = unbekannte_figur_liegt(zustand)
    assert h.modus == zustand
    assert h.sende(konfig_mit(UID_UNBEKANNT, "s1")) == [ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v1")]
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
        (None, ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v2")),  # kein Zeiger: Folge 1, Position 0
        (ev.Zeiger("s1", "b.mp3", 1, 100.0, 4), ev.Abspielen("s1", "s1", "b.mp3", 97.0, "v2")),
        (ev.Zeiger("s1", "b.mp3", 1, 2.0, 4), ev.Abspielen("s1", "s1", "b.mp3", 0.0, "v2")),  # nie unter 0
        (ev.Zeiger("s1", "c.mp3", 2, 0.0, 4), ev.Abspielen("s1", "s1", "c.mp3", 0.0, "v2")),  # nach Folgenende kein Rücksprung
        (ev.Zeiger("s1", "weg.mp3", 1, 50.0, 4), ev.Abspielen("s1", "s1", "b.mp3", 0.0, "v2")),  # Folge am Platz index
        (ev.Zeiger("s1", "weg.mp3", 7, 50.0, 4), ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v2")),  # index zu groß: Folge 1
    ],
    ids=["ohne", "rücksprung", "nicht-unter-0", "nach-folgenende", "datei-fehlt", "index-zu-gross"],
)
def test_zeiger_beim_auflegen(zeiger, erwartet):
    h = SitzungsHarnisch(zeiger=(zeiger,) if zeiger else ())
    assert h.sende(A()) == [erwartet]


def test_fehlende_folge_wird_protokolliert():
    h = SitzungsHarnisch(zeiger=(ev.Zeiger("s1", "weg.mp3", 1, 50.0, 4),))
    h.sende(A())
    log = [o for o in h.voll if isinstance(o, ev.Protokoll)]
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
    log = [o for o in h.voll if isinstance(o, ev.Protokoll)]
    assert [(p.ebene, p.ereignis) for p in log] == [("WARNING", "serie_fehlt")]
    assert dict(log[0].daten) == {"uid": UID_FEHLT, "serie": "unbekannte-serie"}


def test_serie_kommt_spaeter_gilt_beim_naechsten_auflegen():
    h = SitzungsHarnisch()
    h.sende(A(UID_FEHLT, "v1"))
    neu = ev.Serie("unbekannte-serie", "Neu", "normal", "neu", ("n1.mp3",))
    assert h.sende(ev.BibliothekGeladen((S1, S2, UEB, neu))) == []
    assert h.z.serie_id == "ueb" and h.modus == "spielt"  # die laufende Serie wechselt nicht
    h.sende(ev.Abgehoben(6, "v1"))
    assert h.sende(A(UID_FEHLT, "v3")) == [ev.Abspielen("unbekannte-serie", "neu", "n1.mp3", 0.0, "v3")]


def test_folge_zu_ende_nach_der_letzten_folge_auf_folge_1():
    h = SitzungsHarnisch(zeiger=(ev.Zeiger("s1", "c.mp3", 2, 0.0, 1),))
    h.auflegen()
    out = h.sende(ev.FolgeZuEnde("s1", "c.mp3"))
    assert out == [ev.ZeigerSpeichern("s1", "a.mp3", 0, 0.0, "folgenende"), ev.Pausieren("folgenende")]
    assert h.modus == "beendet"
    assert h.sende(ev.Hauptknopf("kurz")) == [ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v1")]


def test_folge_zu_ende_bei_liegender_figur_pausiert_trotzdem():
    h = in_zustand("spielt")
    h.sende(ev.FolgeZuEnde("s1", "a.mp3"))
    assert h.modus == "beendet" and h.z.figur is not None


def test_folge_zu_ende_fremde_folge_wird_ignoriert():
    h = in_zustand("spielt")
    out = h.sende(ev.FolgeZuEnde("s2", "x.mp3"))
    assert out == [] and h.modus == "spielt"


def test_zeiger_wird_nur_bei_aenderung_geschrieben():
    h = SitzungsHarnisch(zeiger=(ev.Zeiger("s1", "a.mp3", 0, 10.0, 1),))
    h.auflegen()
    h.position("s1", "a.mp3", 10.0)
    assert h.sende(ev.Abgehoben(1, "v1")) == [ev.Pausieren("abgehoben")]


def test_zeiger_position_wird_auf_eine_nachkommastelle_abgerundet():
    h = in_zustand("spielt")
    h.position("s1", "a.mp3", 12.39)
    out = h.sende(ev.Abgehoben(1, "v1"))
    assert out[1] == ev.ZeigerSpeichern("s1", "a.mp3", 0, 12.3, "pause")


def test_position_einer_anderen_folge_wird_ignoriert():
    h = in_zustand("spielt")
    h.sende(ev.PlayerPosition("s1", "b.mp3", 99.0, True))
    out = h.sende(ev.Abgehoben(1, "v1"))
    assert out[1].position_s == 10.0


def test_periodisches_speichern_nach_30_s_und_nur_bei_aenderung():
    h = in_zustand("spielt")
    assert h.sende(ev.Takt(), dt=29.9) == []
    assert h.sende(ev.Takt(), dt=0.1) == [ev.ZeigerSpeichern("s1", "a.mp3", 0, 10.0, "periodisch")]
    assert h.sende(ev.Takt(), dt=30.0) == []  # Zeiger unverändert
    h.position("s1", "a.mp3", 41.0)
    assert h.sende(ev.Takt(), dt=0.1) == [ev.ZeigerSpeichern("s1", "a.mp3", 0, 41.0, "periodisch")]
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
    h.sende(ev.PlayerPosition("s1", "a.mp3", 3.0, True))
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
    h = SitzungsHarnisch(zeiger=(ev.Zeiger("s1", "c.mp3", 2, 10.0, 1),))
    h.sende(ev.StummBeginnt())
    h.sende(A())
    assert h.modus == "gehalten"
    assert (h.z.serie_id, h.z.datei, h.z.index, h.z.position_s) == ("s1", "c.mp3", 2, 7.0)
    h.sende(ev.StummEndet())
    assert h.modus == "pausiert"
    assert h.sende(ev.Weiter()) == [
        ev.ZeigerSpeichern("s1", "a.mp3", 0, 0.0, "folgenende"),
        ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v2"),
    ]


def test_stumm_figurwechsel_laesst_keine_reste_einer_anderen_serie():
    h = in_zustand("pausiert_ohne_figur")  # s1, a.mp3 bei 10 s
    h.sende(ev.StummBeginnt())
    h.sende(A(UID_S2))
    assert (h.z.serie_id, h.z.datei, h.z.index) == ("s2", "x.mp3", 0)
    h.sende(ev.StummEndet())
    assert h.sende(ev.Weiter()) == [
        ev.ZeigerSpeichern("s2", "y.mp3", 1, 0.0, "folgenende"),
        ev.Abspielen("s2", "s2", "y.mp3", 0.0, "v2"),
    ]


def test_beendet_stumm_neue_figur_serie_folgt_der_neuen_figur():
    h = in_zustand("beendet")
    h.sende(ev.StummBeginnt())
    assert h.sende(A(UID_S2)) == [ev.TonSpielen("hinweis")]
    assert h.modus == "beendet"
    assert (h.z.serie_id, h.z.datei, h.z.index) == ("s2", "x.mp3", 0)
    h.sende(ev.StummEndet())
    assert h.sende(ev.Hauptknopf("kurz")) == [ev.Abspielen("s2", "s2", "x.mp3", 0.0, "v2")]


def test_beendet_weiter_spielt_zeigerfolge_zurueck_die_eben_beendete():
    h = in_zustand("beendet")  # FolgeZuEnde a.mp3 -> Zeiger b.mp3
    assert h.sende(ev.Weiter()) == [ev.Abspielen("s1", "s1", "b.mp3", 0.0, "v1")]
    h = in_zustand("beendet")
    assert h.sende(ev.Zurueck())[-1] == ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v1")


def test_zurueck_in_beendet_umlauf_bei_erster_folge():
    h = SitzungsHarnisch(zeiger=(ev.Zeiger("s1", "c.mp3", 2, 0.0, 1),))
    h.auflegen()
    h.position("s1", "c.mp3", 10.0)
    h.sende(ev.FolgeZuEnde("s1", "c.mp3"))  # Zeiger wieder a.mp3
    assert h.modus == "beendet"
    assert h.sende(ev.Zurueck())[-1] == ev.Abspielen("s1", "s1", "c.mp3", 0.0, "v1")


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
    assert ev.Abspielen("s1", "s1", "a.mp3", 7.0, "v1") not in out
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
