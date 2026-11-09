"""CUJ 18: LED-Ring-Zustände (AP 4.1 und 4.8).

Der Ring kennt läuft, Pause, Akku, unbekannte Karte, Aufwachen und (Vorschlag, Tobias entscheidet nach Ansicht in der Simulation)
Lernmodus und Gute Nacht. Die Helligkeit liegt nie über 25 %. Am Mac zeigen Terminal und Protokoll denselben Zustand.

Teil 1: echter Kern + ``LedLogik`` (``BedienBox``). Teil 2: die echte ``App`` (Ring im Protokoll, in der Terminal-Zeile und in der Anzeige
der Oberfläche).
"""

from __future__ import annotations

import pytest
from conftest import UID_NACHT
from fixtures import stufe4
from fixtures.dienst import BAER, BEKANNT, baue_dienst, netz_strom_abschnitt
from fixtures.stufe4 import BedienBox

from tobibox import events as ev
from tobibox import led

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"


def aufbau(medien):
    stufe4.serie(medien, "rabe", ["a.wav", "b.wav"], SERIE, "Rabe", 200.0)
    stufe4.ueberraschung(medien)


@pytest.fixture
def box(tmp_path):
    zu = {UID: ev.Zuordnung("serie", SERIE), UID_NACHT: ev.Zuordnung("aktion", aktion="gute_nacht")}
    b = BedienBox(tmp_path, zu, aufbau)
    stufe4.setze_konfig(b, gute_nacht=ev.GuteNacht(1, 10))
    b.laufe(led.AUFWACHEN_S + 0.5)  # das Lauflicht vom Start ist vorbei
    return b


def deckel_gehalten(ring) -> bool:
    return 0 <= ring.helligkeit <= led.DECKEL_PROZENT and all(max(c) <= 255 for c in ring.leds)


# --- Teil 1: Kern und Logik ---------------------------------------------------------------------------


def test_ohne_tobie_ist_der_ring_aus(box):
    assert box.ring_zustand() == led.AUS


def test_laeuft(box):
    box.auflege(UID)
    box.laufe(led.AUFWACHEN_S + 0.5)  # aus dem Leerlauf in den Betrieb: erst Aufwachen
    assert box.ring_zustand() == led.LAEUFT
    assert box.ring().leds[0] == led.GRUEN


def test_aus_dem_leerlauf_zurueck_in_den_betrieb_zeigt_aufwachen(box):
    box.auflege(UID)
    assert box.ring_zustand() == led.AUFWACHEN
    box.laufe(led.AUFWACHEN_S + 0.2)
    assert box.ring_zustand() == led.LAEUFT


def test_pause_bei_liegendem_tobie(box):
    box.auflege(UID)
    box.laufe(3.0)
    box.sende(ev.Hauptknopf("kurz"))
    assert box.ring_zustand() == led.PAUSE


def test_pause_nach_dem_ende_der_folge_beendet(box):
    box.auflege(UID)
    box.laufe(3.0)
    box.sende(ev.FolgeZuEnde(SERIE, "a.wav"))
    assert box.modus == "beendet" and box.ring_zustand() == led.PAUSE


def test_abgehoben_ist_der_ring_aus(box):
    box.auflege(UID)
    box.laufe(3.0)
    box.hebe_ab()
    assert box.ring_zustand() == led.AUS  # leer-ähnlich: keine Karte, Leerlauf


def test_unbekannte_karte_bei_unterbrechung_des_lesers(box):
    box.auflege(UID)
    box.laufe(3.0)
    box.sende(ev.LeserAlarm("kein_herzschlag"))
    assert box.modus == "unbekannt" and box.ring_zustand() == led.UNBEKANNTE_KARTE
    zustaende = {box.ring().leds[0] for _ in (0, 1)}
    assert led.MAGENTA in zustaende or led.SCHWARZ in zustaende  # blinkt


def test_akku_anzeige_beim_laderwechsel_und_tiefstand(box):
    box.sende(ev.AkkuStand(80))
    box.sende(ev.LaderGeaendert(True))
    assert box.ring_zustand() == led.AKKU
    assert box.ring().leds[0] == led.BLAU  # laden
    box.laufe(led.AKKU_ANZEIGE_S + 0.5)
    assert box.ring_zustand() != led.AKKU
    box.sende(ev.LaderGeaendert(False))
    box.sende(ev.AkkuTiefstand())
    assert box.ring_zustand() == led.AKKU and box.ring().leds[0] in (led.ROT, led.SCHWARZ)


def test_lernmodus_blaues_atmen_auch_ohne_tobie(box):
    box.sende(ev.HaLernmodus("b1", box.uhr.wall + 120))
    assert stufe4.zeile(box).lernmodus
    assert box.ring_zustand() == led.LERNEN
    r = box.ring()
    assert r.leds[0] == led.FARBE_LERNEN
    hell = []
    for _ in range(31):
        box.laufe(0.1)
        hell.append(box.ring().helligkeit)
    assert max(hell) - min(hell) > 5  # atmet
    box.sende(ev.HaLernmodusAbbruch("b2", box.uhr.wall + 30))
    assert box.ring_zustand() == led.AUS


def _hell(box, dauer):
    werte = []
    for _ in range(int(dauer / 0.1)):
        box.laufe(0.1)
        werte.append(box.ring().helligkeit)
    return werte


def test_gute_nacht_glimmt_und_wird_beim_ausblenden_schwaecher(box):
    box.auflege(UID)
    box.hebe_ab()
    box.auflege(UID_NACHT, "v2")
    box.hebe_ab("v2")
    box.auflege(UID, "v3")
    box.laufe(led.AUFWACHEN_S + 0.5)
    assert box.ring_zustand() == led.GUTE_NACHT
    assert box.ring().leds[0] == led.FARBE_GUTE_NACHT
    glimmen = max(_hell(box, led.GUTE_NACHT_GLIMMEN_S))
    assert led.GUTE_NACHT_HELL_MAX * 0.9 <= glimmen <= led.GUTE_NACHT_HELL_MAX
    stufe4.gehe_bis(box, lambda: stufe4.zeile(box).gute_nacht == "ausblenden", schritt=0.1)
    box.laufe(7.0)  # 70 % der Ausblendzeit (10 s) sind um
    schwach = max(_hell(box, led.GUTE_NACHT_GLIMMEN_S / 2))
    assert schwach < glimmen * 0.5  # mit dem Ausblenden deutlich schwächer
    box.laufe(4.0)
    assert box.modus == "pausiert" and box.ring_zustand() == led.PAUSE  # Ende: normale Pause


def test_unter_stumm_bleibt_der_zustand_nur_gedimmt(box):
    stufe4.setze_konfig(box, fenster_liste=(stufe4.fenster("n", "stumm", "22:00", "07:00"),), revision=3)
    box.uhr.setze_wall(stufe4.wall(2026, 11, 9, 21, 59, 0))
    box.laufe(0.5)
    box.auflege(UID)
    box.sende(ev.Hauptknopf("kurz"))  # Pause: Bernstein mit fester Helligkeit
    box.laufe(led.AUFWACHEN_S + 0.5)
    assert box.ring_zustand() == led.PAUSE and box.ring().helligkeit == led.PAUSE_HELLIGKEIT
    box.uhr.setze_wall(stufe4.wall(2026, 11, 9, 23, 0))
    box.laufe(0.5)
    assert stufe4.zeile(box).ruhe == "stumm"
    assert box.ring_zustand() == led.PAUSE  # der Zustand bleibt, der Ring ist nicht aus
    assert box.ring().helligkeit == pytest.approx(led.PAUSE_HELLIGKEIT * led.STUMM_DIMMUNG)
    assert box.ring().leds[0] == led.BERNSTEIN


def test_herunterfahren_ring_aus(box):
    box.auflege(UID)
    box.sende(ev.Hauptknopf("lang"))
    assert stufe4.zeile(box).strom == "herunterfahren"
    assert box.ring_zustand() == led.AUS


def test_die_helligkeit_liegt_in_keinem_zustand_ueber_25_prozent(box):
    box.sende(ev.AkkuStand(90))
    box.sende(ev.LaderGeaendert(True))
    box.sende(ev.HaLernmodus("b1", box.uhr.wall + 120))
    box.laufe(1.0)
    for zustand in led.ZUSTAENDE:
        for t in range(0, 120):
            r = led.ring_fuer(zustand, t / 4.0, box.led)
            assert deckel_gehalten(r), (zustand, t)
    for _ in range(100):  # und im Lauf der Box
        box.laufe(0.1)
        assert deckel_gehalten(box.ring())
    # APA102: das 5-Bit-Feld bleibt im Bild unter dem Deckel
    assert led.APA102_DECKEL / led.APA102_MAX <= led.DECKEL_PROZENT / 100.0


# --- Teil 2: die App ----------------------------------------------------------------------------------


@pytest.fixture
async def dienst(tmp_path, kurz, monkeypatch):
    zeilen: list[str] = []
    d = baue_dienst(
        tmp_path, kurz, monkeypatch, netz_strom_abschnitt(),
        zuordnungen={BEKANNT: ev.Zuordnung("serie", BAER), UID_NACHT: ev.Zuordnung("aktion", aktion="gute_nacht")},
        ring_ausgabe=zeilen.append,
    )
    d.zeilen = zeilen  # type: ignore[attr-defined]
    await d.app.starte()
    yield d
    await d.app.beende()


def ring_aus_anzeige(d) -> dict:
    return d.app.anzeige_auskunft()["anzeige"]["ring"]


async def test_die_anzeige_der_oberflaeche_bekommt_den_ring(dienst):
    d = dienst
    r = ring_aus_anzeige(d)
    assert r is not None and len(r["farben"]) == 40 and r["zustand"] == "aufwachen"  # Bereit: Lauflicht
    assert 0 <= r["helligkeit"] <= 25 and r["deckel"] == 25
    await d.zeit_vor(3.0)
    assert ring_aus_anzeige(d)["zustand"] == "aus"
    await d.auflegen(BEKANNT)
    await d.zeit_vor(3.0)
    r = ring_aus_anzeige(d)
    assert r["zustand"] == "laeuft" and r["farben"][0] == list(led.GRUEN)


async def test_ring_geht_ins_protokoll_nur_bei_wechsel_und_ins_terminal(dienst, protokoll):
    d = dienst
    await d.zeit_vor(3.0)
    d.app._zeige_ring()
    d.app._zeige_ring()  # gleicher Zustand: keine zweite Protokollzeile
    n_aus = len([z for z in protokoll.finde("ring", baustein="led") if z["ergebnis"] == "aus"])
    assert n_aus == 1
    await d.auflegen(BEKANNT)
    await d.zeit_vor(3.0)
    for _ in range(20):
        d.uhr.vor(0.1)
        d.app._zeige_ring()  # laeuft atmet, der Zustand bleibt
    zustaende = [z["ergebnis"] for z in protokoll.finde("ring", baustein="led")]
    assert zustaende[-1] == "laeuft" and zustaende.count("laeuft") == 1
    assert zustaende == [z for i, z in enumerate(zustaende) if i == 0 or z != zustaende[i - 1]]  # nie zweimal hintereinander
    # Terminal und Protokoll zeigen denselben Zustand
    assert f"Ring: {zustaende[-1]}" in d.zeilen[-1]
    assert all(z.startswith("Ring: ") for z in d.zeilen)


async def test_strom_ereignisse_erreichen_den_ring(dienst):
    d = dienst
    await d.zeit_vor(3.0)
    await d.sim(befehl="strom", lader=True, akku=70)
    r = ring_aus_anzeige(d)
    assert r["zustand"] == "akku" and r["farben"][0] == list(led.BLAU)
    await d.zeit_vor(led.AKKU_ANZEIGE_S + 1)
    assert ring_aus_anzeige(d)["zustand"] != "akku"
    await d.sim(befehl="strom", lader=False, akku=2)
    assert ring_aus_anzeige(d)["zustand"] == "akku"  # Tiefstand blinkt


async def test_gute_nacht_und_lernmodus_im_ring_der_app(dienst):
    d = dienst
    await d.zeit_vor(3.0)
    await d.sende(ev.HaLernmodus("b1", d.uhr.jetzt().wall + 120))
    assert ring_aus_anzeige(d)["zustand"] == "lernen"
    await d.sende(ev.HaLernmodusAbbruch("b2", d.uhr.jetzt().wall + 30))
    assert ring_aus_anzeige(d)["zustand"] == "aus"
    await d.auflegen(UID_NACHT, "v7")
    await d.abheben("v7")
    await d.auflegen(BEKANNT, "v8")
    await d.zeit_vor(3.0)
    assert ring_aus_anzeige(d)["zustand"] == "gute_nacht"
