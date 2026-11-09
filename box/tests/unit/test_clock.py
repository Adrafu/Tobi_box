"""clock: monotone Uhr, Wanduhr, Zeitquelle."""

import pytest

from tobibox.clock import Jetzt, SimUhr, SystemUhr


def test_sim_uhr_laeuft_nur_wenn_man_sie_vorstellt():
    u = SimUhr(mono=10.0, wall=1000.0)
    assert u.jetzt() == Jetzt(10.0, 1000.0, "system", True)
    assert u.jetzt() == u.jetzt()
    j = u.vor(2.5)
    assert (j.mono, j.wall) == (12.5, 1002.5)


def test_sim_uhr_mono_laeuft_nie_rueckwaerts():
    u = SimUhr()
    with pytest.raises(ValueError):
        u.vor(-0.1)


def test_wanduhr_darf_springen_mono_nicht():
    u = SimUhr(mono=5.0, wall=100.0)
    u.setze_wall(50.0)
    j = u.jetzt()
    assert (j.mono, j.wall) == (5.0, 50.0)


@pytest.mark.parametrize("quelle, ok", [("system", True), ("rtc", True), ("ntp", True), ("unbekannt", False)])
def test_zeitquelle(quelle, ok):
    u = SimUhr()
    u.setze_zeit(quelle, ok)
    j = u.jetzt()
    assert (j.zeit_quelle, j.zeit_ok) == (quelle, ok)


def test_system_uhr_nimmt_die_gegebenen_quellen():
    werte = iter([1.0, 2.0])
    u = SystemUhr(mono=lambda: next(werte), wall=lambda: 1_700_000_000.0)
    a, b = u.jetzt(), u.jetzt()
    assert (a.mono, b.mono) == (1.0, 2.0)
    assert a.wall == 1_700_000_000.0
    assert (a.zeit_quelle, a.zeit_ok) == ("system", True)  # Mac: immer vertrauenswürdig


def test_system_uhr_echt_monoton():
    u = SystemUhr()
    a = u.jetzt().mono
    b = u.jetzt().mono
    assert b >= a


def test_system_uhr_quelle_wechseln():
    u = SystemUhr()
    u.setze_quelle("unbekannt", False)
    j = u.jetzt()
    assert (j.zeit_quelle, j.zeit_ok) == ("unbekannt", False)


def test_jetzt_ist_unveraenderlich():
    j = Jetzt(1.0, 2.0)
    with pytest.raises(Exception):
        j.mono = 3.0  # type: ignore[misc]


# --- AP 4.8: Wanduhr stellen (``tobibox sim time``) -----------------------------------------------------------


def test_stelle_wall_verschiebt_nur_die_wanduhr_und_sie_laeuft_weiter():
    from tobibox.clock import SystemUhr

    t = {"mono": 100.0, "wall": 1_000.0}
    uhr = SystemUhr(mono=lambda: t["mono"], wall=lambda: t["wall"])
    uhr.stelle_wall(5_000.0)
    j = uhr.jetzt()
    assert (j.mono, j.wall) == (100.0, 5_000.0)
    t["mono"] += 30
    t["wall"] += 30
    j = uhr.jetzt()
    assert (j.mono, j.wall) == (130.0, 5_030.0)  # läuft von dort weiter, die monotone Uhr blieb unberührt


def test_stelle_wall_none_stellt_die_echte_uhr_wieder_her():
    from tobibox.clock import SystemUhr

    t = {"wall": 1_000.0}
    uhr = SystemUhr(mono=lambda: 0.0, wall=lambda: t["wall"])
    uhr.stelle_wall(9_999.0)
    uhr.stelle_wall(None)
    assert uhr.jetzt().wall == 1_000.0
