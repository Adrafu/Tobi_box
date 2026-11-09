"""led: jeder Zustand, Deckel 25 %, Rangfolge, Datenformat."""

import json

import pytest

from tobibox import events as ev
from tobibox import led
from tobibox.led import ANZAHL, DECKEL_PROZENT, LedLogik, Ring


def melden(sitzung="leer", strom="aktiv", **kw):
    felder = dict(
        sitzung=sitzung, strom=strom, serie_id=None, lernmodus=False, ruhe="normal", gute_nacht="aus", figur_liegt=False
    )
    felder.update(kw)
    return ev.ZustandMelden(**felder)


def logik_mit(sitzung, strom="aktiv"):
    lg = LedLogik()
    lg.beobachte(melden(sitzung, strom), 0.0)
    return lg


def an_leds(r):
    return [c for c in r.leds if c != (0, 0, 0)]


# -- jeder Zustand -----------------------------------------------------------------------


def test_laeuft_gruen_und_atmet():
    lg = logik_mit("spielt")
    r0, r1 = lg.ring(0.0), lg.ring(led.ATMEN_S / 2)
    assert r0.zustand == r1.zustand == led.LAEUFT
    assert len(an_leds(r0)) == ANZAHL and all(c == led.GRUEN for c in r0.leds)
    assert r0.helligkeit == pytest.approx(12) and r1.helligkeit == pytest.approx(25)


@pytest.mark.parametrize("sitzung", ["pausiert", "gehalten", "beendet"])
def test_pause_bernstein_ruhig(sitzung):
    lg = logik_mit(sitzung)
    r = lg.ring(1.0)
    assert r.zustand == led.PAUSE
    assert all(c == led.BERNSTEIN for c in r.leds)
    assert lg.ring(3.3).helligkeit == r.helligkeit > 0


def test_unbekannte_karte_blinkt():
    lg = logik_mit("unbekannt")
    an, aus = lg.ring(0.1), lg.ring(0.6)
    assert an.zustand == aus.zustand == led.UNBEKANNTE_KARTE
    assert an.helligkeit == DECKEL_PROZENT and aus.helligkeit == 0
    assert all(c == led.MAGENTA for c in an.leds)


@pytest.mark.parametrize("sitzung", ["leer"])
def test_leer_ist_aus(sitzung):
    r = logik_mit(sitzung).ring(0.0)
    assert r.zustand == led.AUS and r.helligkeit == 0


@pytest.mark.parametrize("strom", ["leerlauf", "herunterfahren"])
def test_leerlauf_und_herunterfahren_sind_dunkel(strom):
    assert logik_mit("spielt", strom).zustand(0.0) == led.AUS


def test_ohne_meldung_dunkel():
    assert LedLogik().zustand(0.0) == led.AUS


def test_aufwachen_lauflicht_dann_zurueck():
    lg = logik_mit("pausiert")
    lg.aufwachen(10.0)
    a, b = lg.ring(10.0), lg.ring(10.3)
    assert a.zustand == led.AUFWACHEN and a.helligkeit == DECKEL_PROZENT
    assert a.leds != b.leds  # das Licht läuft
    assert 0 < len(an_leds(a)) <= led.KOMET_LAENGE
    assert lg.zustand(10.0 + led.AUFWACHEN_S + 0.01) == led.PAUSE


def test_aufwachen_bei_bereit_und_nach_leerlauf():
    lg = LedLogik()
    lg.beobachte(ev.Bereit(), 5.0)
    assert lg.zustand(5.1) == led.AUFWACHEN
    lg = logik_mit("pausiert", "leerlauf")
    lg.beobachte(melden("pausiert", "aktiv"), 7.0)
    assert lg.zustand(7.1) == led.AUFWACHEN


def test_akku_anzeige_anteil_und_farbe():
    lg = logik_mit("spielt")
    lg.beobachte(ev.AkkuStand(50), 0.0)
    lg.akku_zeigen(1.0)
    r = lg.ring(2.0)
    assert r.zustand == led.AKKU
    assert len(an_leds(r)) == ANZAHL // 2 and r.leds[0] == led.GELB
    lg.beobachte(ev.AkkuStand(90), 2.0)
    assert lg.ring(2.0).leds[0] == led.GRUEN
    lg.beobachte(ev.AkkuStand(10), 2.0)
    assert lg.ring(2.0).leds[0] == led.ROT and len(an_leds(lg.ring(2.0))) == 4
    # nach der Anzeigedauer zurück
    assert lg.zustand(1.0 + led.AKKU_ANZEIGE_S + 0.1) == led.LAEUFT


def test_akku_anzeige_ohne_stand_zeigt_nichts():
    lg = logik_mit("spielt")
    lg.akku_zeigen(0.0)
    assert lg.zustand(1.0) == led.LAEUFT


def test_lader_wechsel_zeigt_akku_blau():
    lg = logik_mit("pausiert")
    lg.beobachte(ev.AkkuStand(80), 0.0)
    lg.beobachte(ev.LaderGeaendert(True), 1.0)
    r = lg.ring(1.5)
    assert r.zustand == led.AKKU and r.leds[0] == led.BLAU


def test_akku_tiefstand_blinkt_rot_bis_lader():
    lg = logik_mit("spielt")
    lg.beobachte(ev.AkkuTiefstand(), 0.0)
    assert lg.zustand(1000.0) == led.AKKU  # bleibt, bis etwas es löst
    an, aus = lg.ring(0.0), lg.ring(0.3)
    assert an.helligkeit == DECKEL_PROZENT and aus.helligkeit == 0 and an.leds[0] == led.ROT
    lg.beobachte(ev.LaderGeaendert(True), 1.0)
    assert lg.tiefstand is False


def test_rangfolge():
    lg = logik_mit("unbekannt")
    lg.beobachte(ev.AkkuStand(70), 0.0)
    lg.akku_zeigen(0.0)
    assert lg.zustand(1.0) == led.AKKU  # Akku vor unbekannter Karte
    lg.aufwachen(0.5)
    assert lg.zustand(1.0) == led.AUFWACHEN  # Aufwachen vor Akku
    lg.beobachte(melden("unbekannt", "herunterfahren"), 1.0)
    assert lg.zustand(1.1) == led.AKKU  # Herunterfahren bricht Aufwachen ab


def test_andere_ereignisse_werden_ignoriert():
    lg = logik_mit("spielt")
    lg.beobachte(ev.Weiter(), 1.0)
    assert lg.zustand(1.0) == led.LAEUFT


# -- Deckel ------------------------------------------------------------------------------


def test_deckel_wird_von_ring_erzwungen():
    r = Ring("x", ((255, 255, 255),) * ANZAHL, 100)
    assert r.helligkeit == DECKEL_PROZENT
    assert Ring("x", ((0, 0, 0),) * ANZAHL, -5).helligkeit == 0


def test_deckel_in_allen_zustaenden_und_zeiten():
    lg = LedLogik()
    lg.beobachte(ev.AkkuStand(75), 0.0)
    for z in led.ZUSTAENDE:
        for t in [i * 0.037 for i in range(400)]:
            r = led.ring_fuer(z, t, lg)
            assert 0 <= r.helligkeit <= DECKEL_PROZENT
            assert max(max(c) for c in r.leds) <= 255
            assert r.apa102_rahmen()[4] & 0x1F <= led.APA102_DECKEL


def test_apa102_deckel_5bit_unter_25_prozent():
    assert led.APA102_DECKEL / led.APA102_MAX <= DECKEL_PROZENT / 100


def test_apa102_rahmen_aufbau():
    r = Ring("x", ((1, 2, 3),) * ANZAHL, 25)
    b = r.apa102_rahmen()
    assert b[:4] == bytes(4)
    assert b[4:8] == bytes((0xE0 | led.APA102_DECKEL, 3, 2, 1))  # Reihenfolge B, G, R
    assert len(b) == 4 + 4 * ANZAHL + (ANZAHL // 16 + 1)
    assert Ring("x", ((1, 2, 3),) * ANZAHL, 0).apa102_rahmen()[4] == 0xE0


# -- Datenformat für die Simulation ------------------------------------------------------------


def test_als_dict_ist_json_faehig():
    lg = logik_mit("spielt")
    d = lg.ring_dict(1.0)
    assert json.loads(json.dumps(d)) == d
    assert set(d) == {"zustand", "helligkeit", "deckel", "leds"}
    assert len(d["leds"]) == ANZAHL and all(len(c) == 3 for c in d["leds"])
    assert d["deckel"] == 25 and d["zustand"] == "laeuft"


def test_sichtbar_skaliert_mit_helligkeit():
    r = Ring("x", ((200, 100, 0),) * ANZAHL, 25)
    assert r.sichtbar()[0] == (50, 25, 0)


def test_unbekannter_zustand_ist_fehler():
    with pytest.raises(ValueError):
        led.ring_fuer("gibt_es_nicht", 0.0)


def test_ring_braucht_40_leds():
    with pytest.raises(ValueError):
        Ring("x", ((0, 0, 0),) * 39, 10)


# -- AP 4.8: Lernmodus, Gute Nacht, stumm (Vorschlag, Tobias entscheidet nach Ansicht in der Simulation) ------


def test_lernmodus_blaues_atmen_auch_im_leerlauf():
    lg = LedLogik()
    lg.beobachte(melden("leer", strom="leerlauf", lernmodus=True), 0.0)
    r0, r1 = lg.ring(0.0), lg.ring(led.LERNEN_ATMEN_S / 2)
    assert r0.zustand == led.LERNEN and all(c == led.FARBE_LERNEN for c in r0.leds)
    assert r0.helligkeit == pytest.approx(led.LERNEN_HELL_MIN) and r1.helligkeit == pytest.approx(led.LERNEN_HELL_MAX)


def test_lernmodus_schlaegt_laeuft_und_pause_aber_nicht_unbekannte_karte():
    assert logik_mit_lernen("pausiert").zustand(0.0) == led.LERNEN
    assert logik_mit_lernen("spielt").zustand(0.0) == led.LERNEN
    assert logik_mit_lernen("unbekannt").zustand(0.0) == led.UNBEKANNTE_KARTE


def logik_mit_lernen(sitzung):
    lg = LedLogik()
    lg.beobachte(melden(sitzung, lernmodus=True), 0.0)
    return lg


def test_lernmodus_aus_ring_wieder_normal():
    lg = LedLogik()
    lg.beobachte(melden("leer", lernmodus=True), 0.0)
    lg.beobachte(melden("leer", lernmodus=False), 1.0)
    assert lg.zustand(1.0) == led.AUS


def test_beim_herunterfahren_ist_der_ring_aus_auch_im_lernmodus():
    lg = LedLogik()
    lg.beobachte(melden("leer", strom="herunterfahren", lernmodus=True), 0.0)
    assert lg.zustand(0.0) == led.AUS


def test_gute_nacht_glimmt_in_warmem_orange():
    lg = LedLogik()
    lg.beobachte(melden("spielt", gute_nacht="laeuft"), 0.0)
    for t in (0.0, 1.0, 2.0, 3.0):
        r = lg.ring(t)
        assert r.zustand == led.GUTE_NACHT and all(c == led.FARBE_GUTE_NACHT for c in r.leds)
        assert led.GUTE_NACHT_HELL_MIN - 1e-9 <= r.helligkeit <= led.GUTE_NACHT_HELL_MAX + 1e-9


def test_gute_nacht_wird_mit_dem_ausblenden_schwaecher_und_geht_gegen_null():
    lg = LedLogik()
    lg.beobachte(melden("spielt", gute_nacht="ausblenden"), 0.0)
    t = led.GUTE_NACHT_GLIMMEN_S / 2  # oberer Punkt des Glimmens
    hell = []
    for faktor in (1.0, 0.5, 0.1, 0.0):
        lg.setze_ausblenden(faktor)
        hell.append(lg.ring(t).helligkeit)
    assert hell == sorted(hell, reverse=True) and hell[0] == pytest.approx(led.GUTE_NACHT_HELL_MAX) and hell[-1] == 0
    lg.setze_ausblenden(7.0)  # außerhalb: geklemmt
    assert lg.ring(t).helligkeit == pytest.approx(led.GUTE_NACHT_HELL_MAX)
    lg.setze_ausblenden(None)
    assert lg.ring(t).helligkeit == pytest.approx(led.GUTE_NACHT_HELL_MAX)


def test_gute_nacht_nur_waehrend_die_wiedergabe_laeuft():
    lg = LedLogik()
    lg.beobachte(melden("pausiert", gute_nacht="laeuft"), 0.0)
    assert lg.zustand(0.0) == led.PAUSE


@pytest.mark.parametrize("zustand", [led.LAEUFT, led.PAUSE, led.LERNEN, led.GUTE_NACHT])
def test_unter_stumm_bleibt_der_zustand_nur_die_helligkeit_sinkt(zustand):
    sitzung = {led.LAEUFT: "spielt", led.PAUSE: "pausiert", led.LERNEN: "pausiert", led.GUTE_NACHT: "spielt"}[zustand]
    extra = {led.LERNEN: {"lernmodus": True}, led.GUTE_NACHT: {"gute_nacht": "laeuft"}}.get(zustand, {})
    normal, stumm = LedLogik(), LedLogik()
    normal.beobachte(melden(sitzung, **extra), 0.0)
    stumm.beobachte(melden(sitzung, ruhe="stumm", **extra), 0.0)
    for t in (0.0, 0.7, 1.9, 2.5):
        a, b = normal.ring(t), stumm.ring(t)
        assert a.zustand == b.zustand == zustand and a.leds == b.leds
        assert b.helligkeit == pytest.approx(a.helligkeit * led.STUMM_DIMMUNG) and b.helligkeit <= DECKEL_PROZENT


def test_alle_zustaende_haben_ein_bild_und_halten_den_deckel():
    lg = LedLogik()
    lg.beobachte(ev.AkkuStand(60), 0.0)
    for z in led.ZUSTAENDE:
        for t in range(0, 40):
            r = led.ring_fuer(z, t / 3.0, lg)
            assert 0 <= r.helligkeit <= DECKEL_PROZENT and r.zustand == z


def test_farben_und_muster_sind_benannte_konstanten():
    for name in ("FARBE_LERNEN", "FARBE_GUTE_NACHT", "LERNEN_ATMEN_S", "GUTE_NACHT_GLIMMEN_S", "STUMM_DIMMUNG", "PAUSE_HELLIGKEIT"):
        assert hasattr(led, name)


def test_unbekannter_tobie_blinkt_kurz_und_dann_gilt_der_normale_zustand():
    lg = logik_mit("spielt")
    lg.unbekannter_tobie(10.0)
    an, aus = lg.ring(10.1), lg.ring(10.3)
    assert an.zustand == aus.zustand == led.UNBEKANNTE_KARTE
    assert an.helligkeit == DECKEL_PROZENT and aus.helligkeit == 0
    assert all(c == led.MAGENTA for c in an.leds)
    assert lg.ring(10.6).helligkeit == DECKEL_PROZENT  # zweiter Blinker innerhalb der Sekunde
    assert lg.ring(10.0 + led.BLINK_UNBEKANNT_ANZEIGE_S + 0.01).zustand == led.LAEUFT


def test_blinken_wartet_das_lauflicht_beim_aufwachen_ab():
    lg = logik_mit("spielt")
    lg.aufwachen(10.0)
    lg.unbekannter_tobie(10.0)
    assert lg.zustand(10.5) == led.AUFWACHEN
    assert lg.zustand(10.0 + led.AUFWACHEN_S + 0.1) == led.UNBEKANNTE_KARTE
    assert lg.zustand(10.0 + led.AUFWACHEN_S + led.BLINK_UNBEKANNT_ANZEIGE_S + 0.1) == led.LAEUFT


def test_leser_unterbrechung_zeigt_weiter_magenta():
    """Offene Frage (Bericht AP Mac-Abnahme): Für die Leser-Unterbrechung legt das Design keine eigene Anzeige fest."""
    assert logik_mit("unbekannt").zustand(0.0) == led.UNBEKANNTE_KARTE
