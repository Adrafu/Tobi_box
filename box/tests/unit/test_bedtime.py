"""Teilautomat ``bedtime``: jede Zeile der Tabelle „Gute Nacht“ und die Abnahme von AP 4.6."""

from __future__ import annotations

import pytest

from tobibox import bedtime, events as ev, quiet
from tobibox.clock import SimUhr
from tobibox.volume import GRENZE_GLOBAL, GRENZE_GUTE_NACHT, GRENZE_KOPFHOERER, wirksame_grenze

KARTE = ev.AktionAusgeloest("gute_nacht", "v1")


def konfig(timer_min=30, ausblenden_s=60):
    return ev.Konfig(1, "l", {"04aa": ev.Zuordnung("aktion", aktion="gute_nacht")}, ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(timer_min, ausblenden_s))


@pytest.fixture
def uhr():
    return SimUhr()


def bereit(uhr, wirksam=60, timer_min=30, ausblenden_s=60):
    z = bedtime.neuer_zustand()
    z, _ = bedtime.step(z, ev.KonfigGeladen(konfig(timer_min, ausblenden_s)), uhr.jetzt())
    z, _ = bedtime.step(z, ev.LautstaerkeGeaendert(wirksam), uhr.jetzt())
    return z


def laeuft(uhr, **kw):
    z = bereit(uhr, **kw)
    z, _ = bedtime.step(z, KARTE, uhr.jetzt())
    return z


def ausblenden(uhr, **kw):
    z = laeuft(uhr, **kw)
    uhr.vor(z.timer_min * 60)
    z, _ = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "ausblenden"
    return z


def grenzen(out):
    return [o.prozent for o in out if isinstance(o, ev.GrenzeGesetzt) and o.name == GRENZE_GUTE_NACHT]


# ---------------------------------------------------------------- Tabelle „Gute Nacht“


def test_aus_karte_aufgelegt_startet_timer(uhr):
    z = bereit(uhr)
    assert bedtime.kennzeichen(z) == "aus"
    z, out = bedtime.step(z, KARTE, uhr.jetzt())
    assert bedtime.kennzeichen(z) == "laeuft"
    assert z.frist_bis == uhr.mono + 30 * 60
    assert not any(isinstance(o, (ev.Pausieren, ev.Abspielen, ev.GrenzeGesetzt)) for o in out)


def test_laeuft_anderer_tobie_aufgelegt_nichts(uhr):
    z = laeuft(uhr)
    frist = z.frist_bis
    uhr.vor(100)
    for e in (
        ev.Aufgelegt("04bb", "ntag", True, 5, "v2"),
        ev.SitzungGeaendert("spielt", True, True, "serie2"),
        ev.Gesperrt(6, "v3"),
        ev.AktionAusgeloest("status", "v4"),
    ):
        z2, out = bedtime.step(z, e, uhr.jetzt())
        assert z2 == z and out == ()
    assert z.frist_bis == frist  # der Timer läuft für den neuen Tobie weiter


def test_laeuft_timer_abgelaufen_ausblenden_startet(uhr):
    z = laeuft(uhr, wirksam=60)
    uhr.vor(30 * 60 - 0.5)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "laeuft" and not grenzen(out)
    uhr.vor(0.5)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "ausblenden"
    assert grenzen(out) == [60]  # Startwert = wirksam
    assert z.von == 60


def test_ausblenden_lautstaerke_bei_null_ende(uhr):
    z = ausblenden(uhr, wirksam=60)
    uhr.vor(30)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert grenzen(out) == [30]
    uhr.vor(30)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "aus"
    assert ev.GuteNachtEnde() in out
    # 0, dann in derselben Verarbeitung gelöscht (Regel 6.2.7: kein Sprung vor der Pause)
    assert grenzen(out) == [0, None]
    assert not any(isinstance(o, (ev.Pausieren, ev.ZeigerSpeichern)) for o in out)  # das macht die Sitzung


def test_ausblenden_removed_normale_pause_grenze_zurueck(uhr):
    z = ausblenden(uhr, wirksam=60)
    uhr.vor(20)
    z, _ = bedtime.step(z, ev.Takt(), uhr.jetzt())
    z, out = bedtime.step(z, ev.Abgehoben(7, "v1"), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "aus"
    assert grenzen(out) == [None]
    assert ev.GuteNachtEnde() not in out
    # danach ist alles still
    uhr.vor(100)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert out == () and bedtime.kennzeichen(z) == "aus"


# ---------------------------------------------------------------- weitere Festlegungen


def test_abheben_im_zustand_laeuft_aendert_nichts(uhr):
    """Die Gute-Nacht-Karte selbst wird abgehoben (CUJ 14): der Timer läuft weiter."""
    z = laeuft(uhr)
    z2, out = bedtime.step(z, ev.Abgehoben(3, "v1"), uhr.jetzt())
    assert z2 == z and out == ()


def test_zweite_karte_im_zustand_laeuft_timer_von_vorn(uhr):
    z = laeuft(uhr)
    uhr.vor(20 * 60)
    z, out = bedtime.step(z, ev.AktionAusgeloest("gute_nacht", "v9"), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "laeuft"
    assert z.frist_bis == uhr.mono + 30 * 60
    uhr.vor(11 * 60)  # ursprüngliche Frist wäre vorbei
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "laeuft"


def test_zweite_karte_beim_ausblenden_ignoriert(uhr):
    z = ausblenden(uhr)
    z2, out = bedtime.step(z, ev.AktionAusgeloest("gute_nacht", "v9"), uhr.jetzt())
    assert bedtime.kennzeichen(z2) == "ausblenden"
    assert z2.von == z.von and z2.start == z.start
    assert not grenzen(out)


def test_dauern_aus_der_konfiguration(uhr):
    z = laeuft(uhr, timer_min=5, ausblenden_s=10, wirksam=40)
    uhr.vor(5 * 60)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "ausblenden"
    uhr.vor(5)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert grenzen(out) == [20]
    uhr.vor(5)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert ev.GuteNachtEnde() in out


def test_vorgaben_ohne_konfiguration(uhr):
    z = bedtime.neuer_zustand()
    z, _ = bedtime.step(z, KARTE, uhr.jetzt())
    assert z.frist_bis == uhr.mono + 30 * 60 and z.ausblenden_s == 60


def test_neue_konfiguration_aendert_laufenden_timer_nicht(uhr):
    z = laeuft(uhr, timer_min=30)
    frist = z.frist_bis
    z, _ = bedtime.step(z, ev.KonfigGeladen(konfig(timer_min=1, ausblenden_s=5)), uhr.jetzt())
    assert z.frist_bis == frist and bedtime.kennzeichen(z) == "laeuft"
    assert z.ausblenden_s == 5  # gilt für das Ausblenden


def test_timer_laeuft_auf_monotoner_uhr_nicht_auf_wanduhr(uhr):
    z = laeuft(uhr)
    uhr.setze_wall(uhr.wall + 5 * 3600)  # Wanduhr springt (NTP)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "laeuft"


def test_ausblenden_startwert_null_endet_sofort(uhr):
    z = ausblenden_mit_null(uhr)
    assert bedtime.kennzeichen(z) == "aus"


def ausblenden_mit_null(uhr):
    z = laeuft(uhr, wirksam=0)
    uhr.vor(30 * 60)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert ev.GuteNachtEnde() in out
    return z


def test_karte_nach_ende_startet_neu(uhr):
    z = ausblenden(uhr)
    uhr.vor(61)
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert bedtime.kennzeichen(z) == "aus"
    z, _ = bedtime.step(z, KARTE, uhr.jetzt())
    assert bedtime.kennzeichen(z) == "laeuft"


# ---------------------------------------------------------------- Abnahme: nie über der wirksamen Grenze


def test_ausblenden_nie_ueber_wirksamer_grenze_mit_kopfhoerer(uhr):
    """Mit Kopfhörer-Grenze und globaler Grenze: die wirksame Lautstärke steigt nie, nie über ``von``."""
    z = laeuft(uhr, wirksam=50, ausblenden_s=20)
    uhr.vor(30 * 60)
    gr = {GRENZE_GLOBAL: 80, GRENZE_KOPFHOERER: 50}
    werte = []
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    for _ in range(300):
        for o in out:
            if isinstance(o, ev.GrenzeGesetzt):
                if o.prozent is None:
                    gr.pop(o.name, None)
                else:
                    gr[o.name] = o.prozent
        if GRENZE_GUTE_NACHT in gr:
            werte.append(wirksame_grenze(gr))
        uhr.vor(0.1)
        z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    assert werte and all(a >= b for a, b in zip(werte, werte[1:]))
    assert max(werte) <= 50 and min(werte) <= 1
    assert bedtime.kennzeichen(z) == "aus"  # bei 0 gelöscht und beendet


def test_ausblenden_waehrend_kopfhoerer_wird_gezogen_und_leiser_wird(uhr):
    """Wird eine andere Grenze niedriger, bleibt die Rampe unverändert; die kleinste Grenze gewinnt im Kern."""
    z = ausblenden(uhr, wirksam=60)
    gr = {GRENZE_GLOBAL: 80, GRENZE_GUTE_NACHT: 60, GRENZE_KOPFHOERER: 20}
    uhr.vor(6)
    z, _ = bedtime.step(z, ev.LautstaerkeGeaendert(20), uhr.jetzt())
    z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
    gr[GRENZE_GUTE_NACHT] = grenzen(out)[0]
    assert wirksame_grenze(gr) <= 20


def test_ausblenden_nie_lauter_als_vorher_bei_lautstaerkeaenderung(uhr):
    """Steigt ``wirksam`` während des Ausblendens (Lautstärke-Taste), steigt die Rampe nicht mit."""
    z = ausblenden(uhr, wirksam=40, ausblenden_s=60)
    vorher = None
    for i in range(50):
        uhr.vor(1)
        if i == 10:
            z, _ = bedtime.step(z, ev.LautstaerkeGeaendert(90), uhr.jetzt())
        z, out = bedtime.step(z, ev.Takt(), uhr.jetzt())
        g = grenzen(out)
        if g and g[0] is not None:
            assert vorher is None or g[0] <= vorher
            vorher = g[0]


# ---------------------------------------------------------------- Zusammenspiel mit quiet


def test_stumm_beginnt_waehrend_gute_nacht_laeuft_timer_bleibt(uhr):
    """Gute Nacht und stumm sind getrennt: der Timer läuft in „stumm“ weiter, quiet gibt keine Pause aus."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    b = laeuft(uhr)
    h = SimUhr(wall=datetime(2023, 11, 14, 21, 59, tzinfo=ZoneInfo("Europe/Berlin")).timestamp())
    fenster = ev.Fenster("n", (1, 2, 3, 4, 5, 6, 7), "22:00", "07:00", "stumm", None)
    k = ev.Konfig(1, "l", {}, ev.LeiseZeiten("Europe/Berlin", (fenster,)), ev.GuteNacht(30, 60))
    q, _ = quiet.step(quiet.neuer_zustand(), ev.KonfigGeladen(k), h.jetzt())
    h.vor(60)
    q, out = quiet.step(q, ev.Takt(), h.jetzt())
    assert ev.StummBeginnt() in out
    b2, out2 = bedtime.step(b, ev.StummBeginnt(), uhr.jetzt())
    assert b2 == b and out2 == ()
