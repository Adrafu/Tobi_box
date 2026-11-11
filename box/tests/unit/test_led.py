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


def neu_pausiert(lg, t):
    """Die Sitzung wechselt zur Zeit ``t`` in die Pause: die Pause-Anzeige (``PAUSE_ANZEIGE_S``) beginnt neu."""
    lg.beobachte(melden("leer"), t)
    lg.beobachte(melden("pausiert"), t)


def lauf(lg, von, bis, schritt=0.05):
    """Holt das Bild im Takt der Box ab (``LED_TAKT_S``), wie ``app`` es tut; liefert das letzte (Überblendungen brauchen den Takt)."""
    r = None
    n = int(round((bis - von) / schritt))
    for k in range(n + 1):
        r = lg.ring(von + k * schritt)
    return r


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


def test_leser_unterbrochen_blinkt_gelb_langsam():
    """Entscheidung V (10.11., 11.11.): Leser unterbrochen (Sitzung „unbekannt“) blinkt gelb und langsam; Magenta bleibt dem unbekannten Tobie, Rot dem Tiefstand."""
    lg = logik_mit("unbekannt")
    an, aus = lg.ring(0.1), lg.ring(led.BLINK_LESER_S / 2 + 0.1)
    assert an.zustand == aus.zustand == led.LESER_UNTERBROCHEN
    assert an.helligkeit == DECKEL_PROZENT and aus.helligkeit == 0
    assert all(c == led.GELB for c in an.leds) and led.BLINK_LESER_S > led.BLINK_UNBEKANNT_NEU_S


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
    neu_pausiert(lg, 9.0)
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


def test_laderwechsel_allein_zeigt_nichts_die_anzeige_kommt_von_idle():
    """Ein/Aus, 10.11.: Andocken und Abziehen zeigt der Ring nur auf ``AkkuAnzeigen`` von ``idle`` (Sperre, erste Messung)."""
    lg = logik_mit("pausiert")
    lg.beobachte(ev.AkkuStand(80), 0.0)
    lg.beobachte(ev.LaderGeaendert(False), 0.5)
    lg.beobachte(ev.LaderGeaendert(True), 1.0)
    assert lg.zustand(1.5) == led.PAUSE


def test_warnung_zeigt_5_s_den_akku_rot_bei_20_prozent_oder_weniger():
    """Entscheidung Z, zweite Stufe (11.11.): ``AkkuAnzeigen("akku_warnung", 5.0)`` zeigt den Ladestand, rot bei höchstens 20 %."""
    lg = logik_mit("pausiert")
    lg.beobachte(ev.AkkuStand(10), 0.0)
    lg.beobachte(ev.LaderGeaendert(False), 0.0)
    neu_pausiert(lg, 19.0)
    lg.beobachte(ev.AkkuAnzeigen("akku_warnung", 5.0), 20.0)
    r = lg.ring(21.0)
    assert r.zustand == led.AKKU and r.leds[0] == led.ROT
    assert lg.zustand(20.0 + 5.0 + 0.1) == led.PAUSE


def test_andocken_pulsiert_zweimal_schnell_und_abziehen_zeigt_nach_prozent():
    """Ergänzung X (11.11.): Andocken = zweimal schnell pulsieren (keine 5-s-Anzeige mehr), Abziehen bleibt die Anzeige nach Prozent."""
    lg = logik_mit("pausiert")
    lg.beobachte(ev.AkkuStand(80), 0.0)
    lg.beobachte(ev.LaderGeaendert(False), 0.0)
    lg.beobachte(ev.LaderGeaendert(True), 20.0)
    lg.beobachte(ev.AkkuAnzeigen("andocken", 5.0), 20.0)
    neu_pausiert(lg, 19.0)
    r = lg.ring(20.0 + led.ANSTECKEN_PULS_S / 2)
    assert r.zustand == led.ANSTECKEN and r.leds[0] == led.BLAU and r.helligkeit == pytest.approx(led.AKKU_HELL)
    assert lg.zustand(20.0 + led.ANSTECKEN_DAUER_S + 0.05) == led.PAUSE  # keine 5 s Anzeige mehr
    lg.beobachte(ev.LaderGeaendert(False), 30.0)
    lg.beobachte(ev.AkkuAnzeigen("abziehen", 3.0), 30.0)
    neu_pausiert(lg, 29.0)
    assert lg.ring(31.0).leds[0] == led.GRUEN  # 80 %, ohne Strom nach Prozent
    assert lg.zustand(30.0 + 3.0 + 0.1) == led.PAUSE  # spielt die Sitzung: 3 s


def test_start_mit_strom_zeigt_nach_bereit_den_ladestand_5_s():
    lg = logik_mit("leer")
    lg.beobachte(ev.AkkuStand(60), 0.0)
    lg.beobachte(ev.LaderGeaendert(True), 1.0)  # erste Messung vor Bereit
    assert lg.zustand(1.5) == led.LADEN  # noch nicht bereit: keine Akku-Anzeige, nur der dauernde Füllstand (Entscheidung X)
    lg.beobachte(ev.Bereit(), 2.0)
    assert lg.zustand(2.5) == led.AUFWACHEN  # das Lauflicht geht vor
    assert lg.zustand(2.0 + led.AUFWACHEN_S + 0.1) == led.AKKU  # danach 5 s Ladestand
    assert lg.zustand(2.0 + led.AUFWACHEN_S + 5.1) == led.LADEN  # Entscheidung X: danach der dauernde Füllstand statt „aus“


def test_start_ohne_strom_keine_anzeige_und_spaetes_andocken_zeigt_nichts_ohne_freigabe():
    lg = logik_mit("pausiert")
    lg.beobachte(ev.Bereit(), 0.0)
    lg.beobachte(ev.LaderGeaendert(False), 0.5)
    lg.beobachte(ev.LaderGeaendert(True), 30.0)
    neu_pausiert(lg, 29.0)
    assert lg.zustand(30.5) == led.PAUSE


def test_leser_ausfall_loescht_nur_den_leser_wert_der_anzeige():
    lg = LedLogik()
    lg.beobachte(ev.LaderGeaendert(False, "pisugar"), 0.0)
    lg.beobachte(ev.LaderGeaendert(True, "leser"), 0.0)
    assert lg.am_lader
    lg.beobachte(ev.LeserAlarm("getrennt"), 1.0)
    assert not lg.am_lader


@pytest.mark.parametrize(
    "ruhe, gute_nacht, erwartet",
    [("normal", "aus", 15), ("leiser", "aus", 5), ("stumm", "aus", 3), ("normal", "laeuft", 5), ("normal", "ausblenden", 5), ("stumm", "laeuft", 3)],
)
def test_akku_anzeige_helligkeit_15_5_3_ohne_den_stumm_faktor(ruhe, gute_nacht, erwartet):
    lg = LedLogik()
    lg.beobachte(melden("pausiert", ruhe=ruhe, gute_nacht=gute_nacht), 0.0)
    lg.beobachte(ev.AkkuStand(70), 0.0)
    lg.akku_zeigen(1.0)
    r = lg.ring(2.0)
    assert r.zustand == led.AKKU and r.helligkeit == erwartet


@pytest.mark.parametrize("hell", [3, 5, 15])
def test_akku_anzeige_hat_mindestens_stufe_1_von_31(hell):
    r = Ring("akku", ((0, 255, 70),) * ANZAHL, hell)
    assert r.apa102_rahmen()[4] & 0x1F >= 1
    assert Ring("x", ((0, 0, 0),) * ANZAHL, 0).apa102_rahmen()[4] & 0x1F == 0


def test_akku_anzeige_wird_entprellt():
    lg = logik_mit("pausiert")
    lg.beobachte(ev.AkkuStand(70), 0.0)
    neu_pausiert(lg, 9.0)
    lg.akku_zeigen(10.0)
    lg.akku_zeigen(10.5)  # innerhalb von AKKU_ENTPRELL_S: startet nicht neu
    assert lg.zustand(10.0 + led.AKKU_ANZEIGE_S + 0.1) == led.PAUSE
    neu_pausiert(lg, 19.0)
    lg.akku_zeigen(20.0)
    lg.akku_zeigen(21.5)  # nach der Entprellzeit: neue Anzeige
    assert lg.zustand(25.5) == led.AKKU


def test_tiefstand_unter_stumm_mit_der_kleinsten_stufe_wie_die_akku_anzeige():
    """Entscheidung U (10.11.): kein Faktor 0,4 mehr; der Tiefstand zeigt unter „stumm“ ruhig mit ``AKKU_HELL_STUMM`` (Stufe 1)."""
    lg = LedLogik()
    lg.beobachte(melden("pausiert", ruhe="stumm"), 0.0)
    lg.beobachte(ev.AkkuTiefstand(), 0.0)
    r = lg.ring(0.1)
    assert r.zustand == led.AKKU and r.helligkeit == led.AKKU_HELL_STUMM and r.apa102_rahmen()[4] & 0x1F >= 1


def test_akku_tiefstand_pulsiert_rot_bis_lader():
    """Entscheidung V (11.11.): weiches An- und Abschwellen (Periode 1,5 s, Kurve wie „läuft“), oberer Punkt der Deckel, nie ganz aus."""
    lg = logik_mit("spielt")
    lg.beobachte(ev.AkkuTiefstand(), 0.0)
    assert lg.zustand(1000.0) == led.AKKU  # bleibt, bis etwas es löst
    assert led.TIEFSTAND_PULS_S == 1.5
    tief, oben = lg.ring(0.0), lg.ring(led.TIEFSTAND_PULS_S / 2)
    mitte = lg.ring(led.TIEFSTAND_PULS_S / 4)
    assert oben.helligkeit == DECKEL_PROZENT and 0 < tief.helligkeit < mitte.helligkeit < oben.helligkeit
    assert all(c == led.ROT for c in oben.leds) and len(an_leds(oben)) == ANZAHL
    assert lg.ring(led.TIEFSTAND_PULS_S).helligkeit == pytest.approx(tief.helligkeit)
    assert led.ring_fuer(led.LAEUFT, 0.0).helligkeit == tief.helligkeit  # gleiche Kurvenform wie „läuft“
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
    assert logik_mit_lernen("unbekannt").zustand(0.0) == led.LESER_UNTERBROCHEN


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


# -- Entscheidung U (10.11.): Ring unter „stumm“ ----------------------------------------------


def stumm_logik(vorher=("spielt", "normal"), jetzt=("gehalten", "stumm"), t_vorher=0.0, t_jetzt=100.0, **kw):
    lg = LedLogik()
    lg.beobachte(melden(vorher[0], ruhe=vorher[1], figur_liegt=True, **kw), t_vorher)
    lg.beobachte(melden(jetzt[0], ruhe=jetzt[1], figur_liegt=True, **kw), t_jetzt)
    return lg


def test_stumm_konstanten_sind_benannt():
    assert led.STUMM_ANZEIGE_S == 5.0 and led.STUMM_FARBE == led.ROT and not hasattr(led, "STUMM_DIMMUNG")
    assert 0 < led.STUMM_HELLIGKEIT <= 5


def test_pause_wegen_stumm_ganz_dunkelrot_dann_nach_5_s_aus():
    lg = stumm_logik()
    r = lg.ring(100.5)
    assert r.zustand == led.STUMM and all(c == led.STUMM_FARBE for c in r.leds)
    assert r.helligkeit == led.STUMM_HELLIGKEIT and r.apa102_rahmen()[4] & 0x1F == 1  # kleinste sichtbare Stufe
    assert lg.ring(100.0 + led.STUMM_ANZEIGE_S - 0.01).zustand == led.STUMM
    lauf(lg, 100.0 + led.STUMM_ANZEIGE_S - 0.01, 100.0 + led.STUMM_ANZEIGE_S + led.UEBERGANG_S)  # die Überblendung nach „aus“ läuft ab
    for t in (100.0 + led.STUMM_ANZEIGE_S + led.UEBERGANG_S + 0.05, 130.0, 5000.0):
        aus = lg.ring(t)
        assert aus.zustand == led.AUS and aus.helligkeit == 0 and an_leds(aus) == []


def test_stumm_beginnt_waehrend_es_spielt_rot_ab_dem_ausblenden_und_laeuft_ueber_gehalten_weiter():
    lg = LedLogik()
    lg.beobachte(melden("spielt", figur_liegt=True), 0.0)
    lg.beobachte(melden("spielt", ruhe="stumm", figur_liegt=True), 100.0)  # Ausblenden
    assert lg.zustand(100.5) == led.STUMM
    lg.beobachte(melden("gehalten", ruhe="stumm", figur_liegt=True), 103.0)  # Ausblenden fertig: keine neue 5 s
    assert lg.zustand(104.0) == led.STUMM and lg.zustand(105.1) == led.AUS


def test_tobie_unter_stumm_aufgelegt_zeigt_rot_5_s():
    lg = LedLogik()
    lg.beobachte(melden("leer", ruhe="stumm"), 0.0)
    assert lg.zustand(50.0) == led.AUS
    lg.beobachte(melden("gehalten", ruhe="stumm", figur_liegt=True), 50.0)
    assert lg.zustand(52.0) == led.STUMM and lg.zustand(55.1) == led.AUS


def test_erneutes_auflegen_unter_stumm_startet_die_5_s_neu():
    lg = stumm_logik()
    assert lg.zustand(110.0) == led.AUS
    lg.beobachte(melden("leer", ruhe="stumm"), 120.0)  # abgehoben
    lg.beobachte(melden("gehalten", ruhe="stumm", figur_liegt=True), 130.0)
    assert lg.zustand(131.0) == led.STUMM and lg.zustand(135.1) == led.AUS


def test_gleiche_meldung_wiederholt_startet_die_5_s_nicht_neu():
    lg = stumm_logik()
    lg.beobachte(melden("gehalten", ruhe="stumm", figur_liegt=True, folge="x"), 103.0)
    assert lg.zustand(105.1) == led.AUS


def test_stumm_endet_der_ring_zeigt_wieder_die_normale_pause_und_das_fenster_ist_weg():
    lg = stumm_logik()
    lg.beobachte(melden("pausiert", ruhe="normal", figur_liegt=True), 101.0)
    assert lg.zustand(101.5) == led.PAUSE
    lg.beobachte(melden("gehalten", ruhe="normal", figur_liegt=True), 102.0)
    assert lg.zustand(102.5) == led.PAUSE


def test_pause_ohne_stumm_bleibt_bernstein():
    lg = LedLogik()
    lg.beobachte(melden("spielt", figur_liegt=True), 0.0)
    lg.beobachte(melden("pausiert", figur_liegt=True), 10.0)
    r = lg.ring(10.5)
    assert r.zustand == led.PAUSE and r.helligkeit == led.PAUSE_HELLIGKEIT


def test_nach_den_5_s_bleibt_der_ring_dunkel_solange_stumm_gilt_auch_bei_pausiert():
    lg = stumm_logik()
    lg.beobachte(melden("pausiert", ruhe="stumm", figur_liegt=True), 200.0)
    assert lg.zustand(200.1) == led.AUS


def test_akku_anzeige_geht_unter_stumm_vor_und_danach_wieder_dunkel():
    lg = stumm_logik()
    lg.beobachte(ev.AkkuStand(70), 100.0)
    lg.akku_zeigen(101.0)
    r = lg.ring(102.0)
    assert r.zustand == led.AKKU and r.helligkeit == led.AKKU_HELL_STUMM
    assert lg.zustand(101.0 + led.AKKU_ANZEIGE_S + 0.1) == led.AUS
    lg2 = stumm_logik()
    lg2.beobachte(ev.AkkuStand(70), 100.0)
    lg2.akku_zeigen(200.0)  # lange nach dem Fenster
    assert lg2.ring(201.0).zustand == led.AKKU and lg2.zustand(200.0 + led.AKKU_ANZEIGE_S + 0.1) == led.AUS


def test_unbekannt_blinken_bleibt_unter_stumm_wie_festgelegt():
    lg = stumm_logik()
    lg.unbekannter_tobie(200.0)
    assert lg.ring(200.1).zustand == led.UNBEKANNTE_KARTE and lg.ring(200.1).helligkeit == DECKEL_PROZENT
    assert lg.zustand(200.0 + led.BLINK_UNBEKANNT_ANZEIGE_S + 0.1) == led.AUS


def test_lernmodus_unter_stumm_bleibt_blau_ungedimmt():
    lg = LedLogik()
    lg.beobachte(melden("pausiert", ruhe="stumm", lernmodus=True), 0.0)
    r = lg.ring(0.0)
    assert r.zustand == led.LERNEN and r.helligkeit == pytest.approx(led.LERNEN_HELL_MIN)


def test_leerlauf_ohne_tobie_unter_stumm_bleibt_dunkel():
    lg = LedLogik()
    lg.beobachte(melden("leer", strom="leerlauf", ruhe="stumm"), 0.0)
    assert lg.zustand(0.0) == led.AUS


def test_alle_zustaende_haben_ein_bild_und_halten_den_deckel():
    lg = LedLogik()
    lg.beobachte(ev.AkkuStand(60), 0.0)
    for z in led.ZUSTAENDE:
        for t in range(0, 40):
            r = led.ring_fuer(z, t / 3.0, lg)
            assert 0 <= r.helligkeit <= DECKEL_PROZENT and r.zustand == z


def test_farben_und_muster_sind_benannte_konstanten():
    for name in ("FARBE_LERNEN", "FARBE_GUTE_NACHT", "LERNEN_ATMEN_S", "GUTE_NACHT_GLIMMEN_S", "STUMM_FARBE", "STUMM_ANZEIGE_S", "STUMM_HELLIGKEIT", "PAUSE_HELLIGKEIT"):
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


def test_leser_unterbrechung_zeigt_gelb_nicht_magenta():
    """Entscheidung V (10.11.): Leser unterbrochen ist gelb (11.11.) und langsam; Magenta gehört dem unbekannten Tobie."""
    assert logik_mit("unbekannt").zustand(0.0) == led.LESER_UNTERBROCHEN


# -- Entscheidung V (10.11.): Pause bernstein, nach 10 s aus ------------------------------------


def test_pause_bernstein_dann_nach_10_s_aus_und_bleibt_dunkel():
    lg = LedLogik()
    lg.beobachte(melden("spielt"), 0.0)
    lg.beobachte(melden("pausiert"), 50.0)
    r = lg.ring(50.5)
    assert r.zustand == led.PAUSE and r.helligkeit == led.PAUSE_HELLIGKEIT and all(c == led.BERNSTEIN for c in r.leds)
    assert led.PAUSE_ANZEIGE_S == 10.0
    assert lg.zustand(50.0 + led.PAUSE_ANZEIGE_S - 0.01) == led.PAUSE
    for t in (60.0, 120.0, 9000.0):
        assert lg.zustand(t) == led.AUS and lg.ring(t).helligkeit == 0


def test_wiederholte_pause_meldung_startet_die_10_s_nicht_neu_neues_auflegen_schon():
    lg = LedLogik()
    lg.beobachte(melden("pausiert"), 0.0)
    lg.beobachte(melden("pausiert", folge="x"), 8.0)
    assert lg.zustand(10.5) == led.AUS
    neu_pausiert(lg, 20.0)
    assert lg.zustand(25.0) == led.PAUSE and lg.zustand(30.1) == led.AUS


def test_akku_anzeige_geht_in_der_dunklen_pause_vor_und_danach_wieder_dunkel():
    lg = LedLogik()
    lg.beobachte(melden("pausiert"), 0.0)
    lg.beobachte(ev.AkkuStand(70), 0.0)
    lg.akku_zeigen(30.0)
    assert lg.zustand(31.0) == led.AKKU and lg.zustand(30.0 + led.AKKU_ANZEIGE_S + 0.1) == led.AUS


def test_abheben_im_leerlauf_ohne_tobie_zeigt_die_10_s_pause_dann_aus():
    """Wie im Dienst: spielt, dann ``pausiert`` mit ``strom=leerlauf`` und ohne liegenden Tobie (Entscheidung V)."""
    lg = LedLogik()
    lg.beobachte(melden("spielt", figur_liegt=True), 0.0)
    lg.beobachte(melden("pausiert", strom="leerlauf", figur_liegt=False), 50.0)
    assert lg.zustand(50.1) == led.PAUSE and lg.zustand(50.0 + led.PAUSE_ANZEIGE_S - 0.01) == led.PAUSE
    assert lg.zustand(50.0 + led.PAUSE_ANZEIGE_S) == led.AUS
    lg2 = LedLogik()
    lg2.beobachte(melden("leer", strom="leerlauf"), 0.0)
    assert lg2.zustand(1.0) == led.AUS


# -- Laden: dauernder Füllstand am Strom (Entscheidung X, 11.11., CUJ 18) ------------------


def am_strom(sitzung="leer", prozent=60, strom="aktiv", **kw):
    lg = LedLogik()
    lg.beobachte(melden(sitzung, strom, **kw), 0.0)
    lg.beobachte(ev.AkkuStand(prozent), 0.0)
    lg.beobachte(ev.LaderGeaendert(True), 0.0)
    return lg


def test_laden_konstanten_sind_benannt():
    assert led.LADEN_HELL == 5 and led.LADEN_HELL_RUHE == 3
    assert led.LADEN_VOLL_PROZENT == 100 and led.LADEN_HYSTERESE == 3
    assert led.LADEN_AUSBLENDEN_S == 2.0 and led.LADEN_EINBLENDEN_S == 2.0
    assert led.LADEN_PULS_S == 4.0 and led.LADEN_PULS_MIN == 0.6
    assert (led.ANSTECKEN_PULSE, led.ANSTECKEN_PULS_S) == (2, 0.6)
    assert led.ANSTECKEN_DAUER_S == pytest.approx(1.2)


def test_laden_statt_aus_blau_so_viele_leds_wie_prozent_und_pulsiert_60_bis_100_prozent_von_laden_hell():
    lg = am_strom("leer", 50)
    r = lg.ring(1.0)
    assert r.zustand == led.LADEN
    assert len(an_leds(r)) == ANZAHL // 2 and all(c == led.BLAU for c in an_leds(r))
    assert r.leds[0] == led.BLAU and r.leds[-1] == led.SCHWARZ
    assert lg.ring(0.0).helligkeit == pytest.approx(led.LADEN_HELL * led.LADEN_PULS_MIN)  # Tal
    assert lg.ring(led.LADEN_PULS_S / 2).helligkeit == pytest.approx(led.LADEN_HELL)  # Gipfel
    assert lg.ring(led.LADEN_PULS_S).helligkeit == pytest.approx(led.LADEN_HELL * led.LADEN_PULS_MIN)  # Periode 4 s
    for t in range(0, 80):
        h = lg.ring(t / 10.0).helligkeit
        assert led.LADEN_HELL * led.LADEN_PULS_MIN - 1e-9 <= h <= led.LADEN_HELL + 1e-9
    lg.beobachte(ev.AkkuStand(25), 2.0)
    assert len(an_leds(lg.ring(3.0))) == ANZAHL // 4  # folgt dem Stand ohne neue Anzeige


@pytest.mark.parametrize("ruhe", ["leiser", "stumm"])
def test_laden_in_leise_zeiten_ruhig_auf_kleinster_stufe(ruhe):
    lg = am_strom("leer", 50, ruhe=ruhe)
    for t in (0.0, 1.0, 2.0, 3.3):
        r = lg.ring(t)
        assert r.zustand == led.LADEN and r.helligkeit == led.LADEN_HELL_RUHE == 3  # kein Pulsieren
        assert r.apa102_rahmen()[4] & 0x1F == 1  # Stufe 1 von 31


def test_laden_pulsieren_faellt_nie_unter_stufe_1():
    lg = am_strom("leer", 50)
    for t in range(0, 80):
        assert lg.ring(t / 10.0).apa102_rahmen()[4] & 0x1F >= 1


def test_laden_nicht_ohne_strom_und_nicht_ohne_akkustand():
    lg = am_strom("leer", 50)
    lg.beobachte(ev.LaderGeaendert(False), 1.0)
    assert lg.zustand(2.0) == led.AUS
    lg = LedLogik()
    lg.beobachte(melden("leer"), 0.0)
    lg.beobachte(ev.LaderGeaendert(True), 0.0)
    assert lg.zustand(1.0) == led.AUS  # Stand unbekannt
    assert LedLogik().zustand(1.0) == led.AUS  # noch keine Meldung


def test_laden_nicht_beim_herunterfahren():
    assert am_strom("leer", 50, strom="herunterfahren").zustand(1.0) == led.AUS


def test_laden_statt_aus_nach_pause_stumm_und_im_leerlauf():
    lg = am_strom("leer", 50)
    neu_pausiert(lg, 10.0)
    assert lg.zustand(11.0) == led.PAUSE
    assert lg.zustand(10.0 + led.PAUSE_ANZEIGE_S + 0.1) == led.LADEN  # statt aus nach 10 s
    assert am_strom("leer", 50, strom="leerlauf").zustand(1.0) == led.LADEN
    lg = am_strom("gehalten", 50, ruhe="stumm", figur_liegt=True)
    assert lg.zustand(1.0) == led.STUMM
    r = lg.ring(led.STUMM_ANZEIGE_S + 1.0)
    assert r.zustand == led.LADEN and r.helligkeit == led.LADEN_HELL_RUHE  # nach den 5 s dunkelrot: Füllstand in kleinster Stufe


def test_laden_hat_nie_vorrang_vor_den_anzeigen():
    lg = am_strom("spielt", 50)
    assert lg.zustand(1.0) == led.LAEUFT
    assert am_strom("pausiert", 50).zustand(1.0) == led.PAUSE
    assert am_strom("unbekannt", 50).zustand(1.0) == led.LESER_UNTERBROCHEN
    assert am_strom("leer", 50, lernmodus=True).zustand(1.0) == led.LERNEN
    assert am_strom("spielt", 50, gute_nacht="laeuft").zustand(1.0) == led.GUTE_NACHT
    lg = am_strom("leer", 50)
    lg.akku_zeigen(1.0)
    assert lg.ring(2.0).zustand == led.AKKU and lg.ring(2.0).helligkeit == led.AKKU_HELL  # 5-s-Anzeige bleibt 15 %
    lg.beobachte(ev.AkkuAnzeigen("andocken", 5.0), 6.0)
    assert lg.zustand(6.1) == led.ANSTECKEN  # Anstecken-Pulsieren geht vor
    lg.unbekannter_tobie(10.0)
    assert lg.zustand(10.1) == led.UNBEKANNTE_KARTE
    lg.aufwachen(20.0)
    assert lg.zustand(20.1) == led.AUFWACHEN


def test_laden_voll_ring_blendet_in_2_s_aus_mit_hysterese():
    lg = am_strom("leer", 99)
    assert lg.zustand(1.0) == led.LADEN
    voll = lg.ring(2.0 - 1e-9).helligkeit  # unmittelbar vor „voll“ (Tal der Pulsierens bei t = 4 s: hier t = 2 s, Gipfel)
    lg.beobachte(ev.AkkuStand(100), 2.0)
    mitte = lg.ring(3.0)
    assert mitte.zustand == led.LADEN and 0 < mitte.helligkeit < voll  # blendet aus, nicht sofort
    assert len(an_leds(mitte)) == ANZAHL  # der Ring bleibt gefüllt
    ende = lauf(lg, 3.0, 2.0 + led.LADEN_AUSBLENDEN_S + led.UEBERGANG_S + 0.05)  # 2 s Ausblenden, dann der Wechsel nach „aus“ in 0,5 s
    assert ende.helligkeit == 0
    assert lg.zustand(2.0 + led.LADEN_AUSBLENDEN_S + 0.1) == led.AUS  # voll: Ring aus
    for p in (99, 98, 97):
        lg.beobachte(ev.AkkuStand(p), 6.0)
        assert lg.zustand(7.0) == led.AUS, p  # kein Flackern knapp unter 100
    lg.beobachte(ev.AkkuStand(led.LADEN_VOLL_PROZENT - led.LADEN_HYSTERESE - 1), 10.0)
    assert lg.zustand(10.0) == led.LADEN  # beginnt wieder: Einblenden


def test_laden_beginnt_wieder_blendet_in_2_s_ein_dann_pulsierend():
    lg = am_strom("leer", 100)
    lg.beobachte(ev.AkkuStand(90), 10.0)
    anfang, mitte = lg.ring(10.0), lg.ring(11.0)
    assert anfang.zustand == led.LADEN and anfang.helligkeit == 0
    assert 0 < mitte.helligkeit < led.LADEN_HELL  # blendet ein
    ziel = lg.ring(10.0 + led.LADEN_EINBLENDEN_S + 1.0)
    assert led.LADEN_HELL * led.LADEN_PULS_MIN - 1e-9 <= ziel.helligkeit <= led.LADEN_HELL + 1e-9
    # ohne „voll“ dazwischen: 99 nach 100 zeigt weiter nichts, erst bei 96
    lg.beobachte(ev.AkkuStand(100), 20.0)
    lg.beobachte(ev.AkkuStand(99), 30.0)
    assert lg.zustand(31.0) == led.AUS


def test_laden_ausblenden_in_leise_zeiten_geht_auch_auf_null_und_einblenden_ruhig():
    lg = am_strom("leer", 99, ruhe="leiser")
    lg.beobachte(ev.AkkuStand(100), 2.0)
    assert 0 < lg.ring(3.0).helligkeit < led.LADEN_HELL_RUHE
    assert lauf(lg, 3.0, 4.0 + led.UEBERGANG_S + 0.05).helligkeit == 0
    lg.beobachte(ev.AkkuStand(90), 10.0)
    assert lg.ring(14.0).helligkeit == led.LADEN_HELL_RUHE  # danach ruhig auf Stufe 1


def test_laden_ausblenden_nie_stufe_0_solange_sichtbar():
    lg = am_strom("leer", 99)
    lg.beobachte(ev.AkkuStand(100), 2.0)
    for k in range(1, 20):
        r = lg.ring(2.0 + k * 0.1)
        assert r.helligkeit > 0 and r.apa102_rahmen()[4] & 0x1F >= 1


def test_laden_voll_beim_ersten_stand_ohne_ausblenden():
    assert am_strom("leer", 100).zustand(0.1) == led.AUS


def test_laden_andocken_bei_vollem_akku_bleibt_aus_und_abziehen_vergisst_voll():
    lg = am_strom("leer", 100)
    assert lg.zustand(1.0) == led.AUS
    lg.beobachte(ev.LaderGeaendert(False), 2.0)
    lg.beobachte(ev.AkkuStand(98), 3.0)
    lg.beobachte(ev.LaderGeaendert(True), 4.0)
    assert lg.ring(4.0).helligkeit > 0  # neu angedockt bei 98 %: nicht voll, sofort da (kein Einblenden nach dem Anstecken)
    assert lg.zustand(5.0) == led.LADEN


def test_laden_ring_fuer_ohne_logik_und_deckel():
    r = led.ring_fuer(led.LADEN, 0.0)
    assert r.zustand == led.LADEN and r.helligkeit <= DECKEL_PROZENT


# -- Anstecken: zwei schnelle, weiche Pulse (Ergänzung X, 11.11., CUJ 25) --------------------


def test_anstecken_zwei_weiche_pulse_bis_akku_helligkeit_dann_direkt_der_ladestand():
    lg = am_strom("leer", 50)
    lg.beobachte(ev.AkkuAnzeigen("andocken", 5.0), 10.0)
    halb = led.ANSTECKEN_PULS_S / 2
    spitzen = [lg.ring(10.0 + k * led.ANSTECKEN_PULS_S + halb) for k in range(led.ANSTECKEN_PULSE)]
    for r in spitzen:
        assert r.zustand == led.ANSTECKEN and r.helligkeit == pytest.approx(led.AKKU_HELL)
        assert len(an_leds(r)) == ANZAHL // 2 and r.leds[0] == led.BLAU  # der Ladestand pulsiert, kein Vollring
    tal = lg.ring(10.0 + led.ANSTECKEN_PULS_S)
    assert tal.helligkeit < spitzen[0].helligkeit  # zwischen den Pulsen wieder tiefer
    # weich: keine Stufe zwischen zwei 10-ms-Schritten
    letzte = lg.ring(9.999).helligkeit
    for k in range(0, int(led.ANSTECKEN_DAUER_S * 100) + 60):
        h = lg.ring(10.0 + k / 100.0).helligkeit
        assert abs(h - letzte) < 1.0, k
        letzte = h
    nach = lg.ring(10.0 + led.ANSTECKEN_DAUER_S + 0.001)
    assert nach.zustand == led.LADEN and len(an_leds(nach)) == ANZAHL // 2
    assert nach.helligkeit == pytest.approx(lg.ring(10.0 + led.ANSTECKEN_DAUER_S - 0.001).helligkeit, abs=0.01)  # Übergang ohne Sprung


@pytest.mark.parametrize(
    "ruhe, gute_nacht, erwartet",
    [("normal", "aus", 15), ("leiser", "aus", 5), ("stumm", "aus", 3), ("normal", "laeuft", 5)],
)
def test_anstecken_spitze_wie_die_akku_anzeige_der_tageszeit(ruhe, gute_nacht, erwartet):
    lg = am_strom("pausiert", 50, ruhe=ruhe, gute_nacht=gute_nacht)
    lg.beobachte(ev.AkkuAnzeigen("andocken", 5.0), 10.0)
    spitze = max(lg.ring(10.0 + k / 100.0).helligkeit for k in range(int(led.ANSTECKEN_DAUER_S * 100)))
    assert spitze == pytest.approx(erwartet, abs=0.05)
    assert all(
        lg.ring(10.0 + k / 100.0).apa102_rahmen()[4] & 0x1F >= 1 and lg.ring(10.0 + k / 100.0).helligkeit <= led.DECKEL_PROZENT
        for k in range(int(led.ANSTECKEN_DAUER_S * 100))
    )


def test_anstecken_in_stumm_nie_heller_als_die_kleinste_stufe():
    lg = am_strom("pausiert", 50, ruhe="stumm")
    lg.beobachte(ev.AkkuAnzeigen("andocken", 5.0), 10.0)
    assert all(lg.ring(10.0 + k / 100.0).helligkeit == led.LADEN_HELL_RUHE for k in range(120))


def test_anstecken_bei_vollem_akku_pulst_aus_dem_dunkel_und_bleibt_danach_aus():
    lg = am_strom("leer", 100)
    lg.beobachte(ev.AkkuAnzeigen("andocken", 5.0), 10.0)
    assert lg.ring(10.0).helligkeit == 0
    assert lg.ring(10.3).helligkeit > 0
    assert lg.ring(10.0 + led.ANSTECKEN_DAUER_S).helligkeit == 0
    assert lg.zustand(10.0 + led.ANSTECKEN_DAUER_S + 0.1) == led.AUS


def test_anstecken_nach_den_pulsen_zurueck_zum_normalen_zustand():
    lg = am_strom("spielt", 50)
    lg.beobachte(ev.AkkuAnzeigen("andocken", 3.0), 10.0)
    assert lg.zustand(10.1) == led.ANSTECKEN
    assert lg.zustand(10.0 + led.ANSTECKEN_DAUER_S + 0.01) == led.LAEUFT


def test_anstecken_ohne_akkustand_zeigt_trotzdem_den_ring():
    lg = logik_mit("leer")
    lg.beobachte(ev.AkkuAnzeigen("andocken", 5.0), 10.0)
    assert lg.zustand(10.1) == led.ANSTECKEN


def test_anstecken_hinter_aufwachen_und_tiefstand():
    lg = am_strom("leer", 50)
    lg.aufwachen(10.0)
    lg.beobachte(ev.AkkuAnzeigen("andocken", 5.0), 10.5)
    assert lg.zustand(10.6) == led.AUFWACHEN
    assert lg.zustand(10.0 + led.AUFWACHEN_S + 0.1) == led.ANSTECKEN  # erst das Lauflicht, dann die Pulse
    lg2 = LedLogik()
    lg2.beobachte(melden("leer"), 0.0)
    lg2.beobachte(ev.AkkuTiefstand(), 0.0)
    lg2.beobachte(ev.AkkuAnzeigen("andocken", 5.0), 1.0)
    assert lg2.zustand(1.1) == led.AKKU


def test_abziehen_und_warnung_zeigen_weiter_die_akku_anzeige_nicht_die_pulse():
    lg = am_strom("leer", 50)
    lg.beobachte(ev.LaderGeaendert(False), 5.0)
    lg.beobachte(ev.AkkuAnzeigen("abziehen", 5.0), 5.0)
    assert lg.zustand(5.1) == led.AKKU
    lg.beobachte(ev.AkkuAnzeigen("akku_warnung", 5.0), 20.0)
    assert lg.zustand(20.1) == led.AKKU


def test_anstecken_ring_fuer_ohne_logik_und_deckel():
    for t in range(0, 20):
        r = led.ring_fuer(led.ANSTECKEN, t / 10.0)
        assert r.zustand == led.ANSTECKEN and r.helligkeit <= DECKEL_PROZENT


# -- Überblendung zwischen den Zuständen (Ergänzung X, 11.11.) ---------------------------


def test_ueberblendung_zwischen_zwei_zustaenden_zwischenwerte_nach_der_halben_zeit():
    lg = logik_mit("pausiert")
    vorher = lg.ring(5.9)  # Pause, bernstein
    assert vorher.zustand == led.PAUSE
    lg.beobachte(melden("leer", lernmodus=True), 6.0)  # Lernmodus: blau atmend
    anfang = lg.ring(6.0)
    mitte = lg.ring(6.0 + led.UEBERGANG_S / 2)
    ende = lg.ring(6.0 + led.UEBERGANG_S)
    assert anfang.zustand == mitte.zustand == ende.zustand == led.LERNEN  # der Name ist schon der neue
    assert anfang.sichtbar() == vorher.sichtbar()  # beginnt auf dem alten Bild
    r, g, b = mitte.sichtbar()[0]
    alt = vorher.sichtbar()[0]
    neu = led.ring_fuer(led.LERNEN, 6.0 + led.UEBERGANG_S / 2, lg).sichtbar()[0]
    assert r > 0 and b > 0  # Bernstein (Rot) und Blau sind beide teilweise da
    assert min(alt[2], neu[2]) <= b <= max(alt[2], neu[2]) and min(alt[0], neu[0]) <= r <= max(alt[0], neu[0])
    assert ende.sichtbar() == led.ring_fuer(led.LERNEN, 6.0 + led.UEBERGANG_S, lg).sichtbar()  # danach das reine neue Bild


def test_ueberblendung_an_nach_aus_und_aus_nach_an_geht_ueber_zwischenwerte():
    lg = logik_mit("pausiert")
    neu_pausiert(lg, 0.0)
    lauf(lg, 0.0, led.PAUSE_ANZEIGE_S - 0.05)
    bilder = [lg.ring(led.PAUSE_ANZEIGE_S + k * 0.05) for k in range(0, 11)]
    w = [r.helligkeit for r in bilder]
    assert w[0] == pytest.approx(led.PAUSE_HELLIGKEIT)  # beginnt auf dem alten Bild
    assert w[-1] == 0 and all(a >= b for a, b in zip(w, w[1:])) and 0 < w[5] < w[0]  # weich bis 0, am Ende darf 0 kommen
    assert all(r.apa102_rahmen()[4] & 0x1F >= 1 for r in bilder[:-1])  # solange etwas leuchtet, mindestens Stufe 1
    lauf(lg, 10.5, 19.95)
    neu_pausiert(lg, 20.0)  # Pause beginnt neu: aus → an
    w = [lg.ring(20.0 + k * 0.05).helligkeit for k in range(0, 11)]
    assert w[0] == 0 and w[-1] == pytest.approx(led.PAUSE_HELLIGKEIT) and 0 < w[5] < w[-1]


def test_ueberblendung_deckel_gilt_in_jedem_schritt():
    lg = logik_mit("spielt")
    lauf(lg, 0.0, 1.0)
    lg.beobachte(melden("leer", lernmodus=True), 1.0)
    lg.unbekannter_tobie(1.0)
    for k in range(0, 60):
        r = lg.ring(1.0 + k * 0.05)
        assert 0 <= r.helligkeit <= DECKEL_PROZENT and all(max(c) <= 255 for c in r.leds)


def test_ueberblendung_ohne_takt_beginnt_der_neue_zustand_sofort():
    lg = logik_mit("pausiert")
    lg.ring(1.0)
    neu_pausiert(lg, 40.0)
    assert lg.ring(41.0).helligkeit == led.PAUSE_HELLIGKEIT  # kein Abruf dazwischen: nichts zum Überblenden


def test_blinkmuster_bleiben_hart_nur_eintritt_und_austritt_sind_weich():
    lg = logik_mit("leer")
    lauf(lg, 0.0, 1.0)
    lg.unbekannter_tobie(1.0)
    eintritt = lauf(lg, 1.0, 1.0 + led.UEBERGANG_S / 2)
    assert eintritt.zustand == led.UNBEKANNTE_KARTE and 0 < eintritt.helligkeit < DECKEL_PROZENT or eintritt.helligkeit == 0
    lauf(lg, 1.0 + led.UEBERGANG_S / 2, 1.0 + led.UEBERGANG_S + 0.05)
    # danach wechselt das Blinken selbst hart (gleicher Zustand, keine Überblendung)
    hell = {lg.ring(1.0 + led.UEBERGANG_S + 0.1 + k * 0.05).helligkeit for k in range(0, 5)}
    assert hell <= {DECKEL_PROZENT, 0}
