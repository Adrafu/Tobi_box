"""controls: Tasten, kurz/lang, Drehregler unter der Grenze, GPIO-Treiber gegen eine Attrappe."""

import pytest

from tobibox import events as ev
from tobibox import controls
from tobibox.controls import Bedienung, GpioTreiber


@pytest.fixture
def aus():
    return []


@pytest.fixture
def b(aus):
    return Bedienung(aus.append, stand=40, grenze=60)


def test_vor_und_zurueck(b, aus):
    b.vor()
    b.zurueck()
    assert aus == [ev.Weiter(), ev.Zurueck()]


def test_hauptknopf_kurz(b, aus):
    b.haupt_runter(10.0)
    b.haupt_hoch(10.2)
    assert aus == [ev.Hauptknopf("kurz")]


def test_hauptknopf_lang_beim_loslassen(b, aus):
    b.haupt_runter(10.0)
    b.haupt_hoch(10.0 + controls.LANG_S)
    assert aus == [ev.Hauptknopf("lang")]


def test_hauptknopf_lang_ohne_loslassen_einmal(b, aus):
    b.haupt_runter(10.0)
    b.tick(10.5)
    assert aus == []
    b.tick(10.0 + controls.LANG_S)
    b.tick(13.0)
    assert aus == [ev.Hauptknopf("lang")]
    b.haupt_hoch(14.0)  # Loslassen nach lang sendet nichts mehr
    assert aus == [ev.Hauptknopf("lang")]


def test_hauptknopf_zweiter_druck_wieder_frei(b, aus):
    b.haupt_runter(0.0)
    b.tick(2.0)
    b.haupt_hoch(2.1)
    b.haupt_runter(5.0)
    b.haupt_hoch(5.1)
    assert aus == [ev.Hauptknopf("lang"), ev.Hauptknopf("kurz")]


def test_loslassen_ohne_druck_und_tick_ohne_druck(b, aus):
    b.haupt_hoch(1.0)
    b.tick(5.0)
    b.haupt_gehalten()
    assert aus == []


def test_schwelle_einstellbar(aus):
    b = Bedienung(aus.append, lang_s=0.5)
    b.haupt_runter(0.0)
    b.haupt_hoch(0.6)
    assert aus == [ev.Hauptknopf("lang")]


# -- Drehregler -------------------------------------------------------------------------


def test_raster_gibt_schritte(b, aus):
    b.drehen(1)
    b.drehen(-2)
    assert aus == [ev.LautstaerkeDrehen(2), ev.LautstaerkeDrehen(-4)]
    assert b.stand == 38


def test_drehen_null_sendet_nichts(b, aus):
    b.drehen(0)
    assert aus == []


def test_nie_ueber_die_grenze(b, aus):
    b.setze_lautstaerke(59, 60)
    b.drehen(5)  # Wunsch 69, Grenze 60: nur +1
    assert aus == [ev.LautstaerkeDrehen(1)] and b.stand == 60
    b.drehen(1)
    assert aus == [ev.LautstaerkeDrehen(1)]  # an der Grenze: nichts mehr


@pytest.mark.parametrize("grenze", [0, 10, 25, 60, 100])
def test_summe_der_schritte_bleibt_unter_grenze(aus, grenze):
    b = Bedienung(aus.append, stand=0, grenze=grenze)
    for _ in range(80):
        b.drehen(1)
    assert sum(e.delta for e in aus) == grenze and b.stand == grenze


def test_grenze_sinkt_unter_stand_lauter_wirkt_nicht(aus):
    b = Bedienung(aus.append, stand=80, grenze=30)  # z. B. Kopfhörer gesteckt
    b.drehen(1)
    assert aus == []
    b.drehen(-1)  # leiser: höchstens bis zur Grenze, nie lauter
    assert b.stand <= 30 and all(e.delta < 0 for e in aus)


def test_nie_unter_null(aus):
    b = Bedienung(aus.append, stand=3, grenze=100)
    b.drehen(-5)
    b.drehen(-1)
    assert aus == [ev.LautstaerkeDrehen(-3)] and b.stand == 0


def test_raster_prozent_einstellbar(aus):
    b = Bedienung(aus.append, stand=0, grenze=100, raster_prozent=5)
    b.drehen(2)
    assert aus == [ev.LautstaerkeDrehen(10)]


# -- GPIO-Treiber gegen Attrappe ------------------------------------------------------------


class AttrappeKnopf:
    def __init__(self, pin, **kw):
        self.pin, self.kw, self.zu = pin, kw, False
        self.when_pressed = self.when_released = self.when_held = None

    def close(self):
        self.zu = True


class AttrappeDreh:
    def __init__(self, a, b, **kw):
        self.pins, self.zu = (a, b), False
        self.when_rotated_clockwise = self.when_rotated_counter_clockwise = None

    def close(self):
        self.zu = True


class AttrappeGpiozero:
    Button = AttrappeKnopf
    RotaryEncoder = AttrappeDreh


def treiber(aus, haupt=None):
    uhr = iter([100.0, 100.3]).__next__
    b = Bedienung(aus.append, stand=10, grenze=20)
    t = GpioTreiber(b, pin_vor=5, pin_zurueck=6, pin_dreh_a=17, pin_dreh_b=27, pin_haupt=haupt, fabrik=AttrappeGpiozero, uhr=uhr)
    t.start()
    return t


def test_treiber_verdrahtet_tasten_und_regler(aus):
    t = treiber(aus)
    vor, zurueck, dreh = t.geraete
    assert (vor.pin, zurueck.pin, dreh.pins) == (5, 6, (17, 27))
    assert vor.kw["bounce_time"] > 0
    vor.when_pressed()
    zurueck.when_pressed()
    dreh.when_rotated_clockwise()
    dreh.when_rotated_counter_clockwise()
    assert aus == [ev.Weiter(), ev.Zurueck(), ev.LautstaerkeDrehen(2), ev.LautstaerkeDrehen(-2)]


def test_treiber_hauptknopf_kurz_und_lang(aus):
    t = treiber(aus, haupt=22)
    haupt = t.geraete[-1]
    assert haupt.kw["hold_time"] == t.b.lang_s
    haupt.when_pressed()
    haupt.when_released()  # 0,3 s: kurz
    assert aus == [ev.Hauptknopf("kurz")]
    aus.clear()
    t.b.haupt_runter(0.0)
    haupt.when_held()
    haupt.when_held()
    assert aus == [ev.Hauptknopf("lang")]


def test_treiber_ohne_hauptknopf_pin_und_stop(aus):
    t = treiber(aus)
    assert len(t.geraete) == 3
    geraete = list(t.geraete)
    t.stop()
    assert all(g.zu for g in geraete) and t.geraete == []
