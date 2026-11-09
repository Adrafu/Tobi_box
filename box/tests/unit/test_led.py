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
