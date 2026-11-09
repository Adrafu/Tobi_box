"""Teilautomat ``quiet``: jede Zeile der Tabelle „Leise-Zeiten“ und die Abnahme von AP 4.5."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tobibox import core, events as ev
from tobibox import learn, quiet
from tobibox.clock import SimUhr
from tobibox.volume import GRENZE_AUSBLENDEN, GRENZE_GLOBAL, GRENZE_KOPFHOERER, GRENZE_LEISE_ZEIT, wirksame_grenze

BERLIN = ZoneInfo("Europe/Berlin")
ALLE = (1, 2, 3, 4, 5, 6, 7)


def wall(jahr, monat, tag, h, m, s=0):
    return datetime(jahr, monat, tag, h, m, s, tzinfo=BERLIN).timestamp()


# 2023-11-14 ist ein Dienstag (Wochentag 2), 2023-11-13 ein Montag
def uhr_um(h, m, tag=14, zeit_ok=True):
    return SimUhr(wall=wall(2023, 11, tag, h, m), zeit_ok=zeit_ok, zeit_quelle="system" if zeit_ok else "unbekannt")


def f_leiser(fid="abend", von="19:30", bis="21:00", grenze=25, tage=ALLE):
    return ev.Fenster(fid, tuple(tage), von, bis, "leiser", grenze)


def f_stumm(fid="nacht", von="22:00", bis="07:00", tage=ALLE):
    return ev.Fenster(fid, tuple(tage), von, bis, "stumm", None)


def konfig(*fenster, zone="Europe/Berlin"):
    return ev.Konfig(1, "l", {}, ev.LeiseZeiten(zone, tuple(fenster)), ev.GuteNacht(30, 60))


def start(uhr, *fenster, zone="Europe/Berlin", wirksam=None):
    z = quiet.neuer_zustand()
    if wirksam is not None:
        z, _ = quiet.step(z, ev.LautstaerkeGeaendert(wirksam), uhr.jetzt())
    z, out = quiet.step(z, ev.KonfigGeladen(konfig(*fenster, zone=zone)), uhr.jetzt())
    return z, out


def takt(z, uhr, sek=0.0):
    return quiet.step(z, ev.Takt(), uhr.vor(sek) if sek else uhr.jetzt())


def typen(out):
    return [type(o) for o in out]


def grenzen_aus(out):
    return [(o.name, o.prozent) for o in out if isinstance(o, ev.GrenzeGesetzt)]


# ---------------------------------------------------------------- Tabelle „Leise-Zeiten“


def test_normal_leiser_fenster_erreicht_wiedergabe_leise_genug():
    """normal | Uhr erreicht „leiser“-Fenster -> Grenze aktiv -> leiser (nicht lauter als Grenze: sofort)."""
    uhr = uhr_um(19, 29, zeit_ok=True)
    z, _ = start(uhr, f_leiser(), wirksam=20)
    assert quiet.kennzeichen(z) == "normal"
    uhr.vor(60)
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "leiser"
    assert grenzen_aus(out) == [(GRENZE_LEISE_ZEIT, 25)]


def test_normal_leiser_fenster_laute_wiedergabe_wird_sanft_abgesenkt():
    uhr = uhr_um(19, 29)
    z, _ = start(uhr, f_leiser(), wirksam=60)
    uhr.vor(60)
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "leiser"
    # erster Schritt der Rampe: noch der Startwert, die Fenster-Grenze ist noch nicht gesetzt
    assert grenzen_aus(out) == [(GRENZE_AUSBLENDEN, 60)]
    z, out = takt(z, uhr, 1.5)
    assert grenzen_aus(out) == [(GRENZE_AUSBLENDEN, 43)]  # 60 -> 25 in 3 s, halbe Zeit
    z, out = takt(z, uhr, 1.5)
    assert grenzen_aus(out) == [(GRENZE_LEISE_ZEIT, 25), (GRENZE_AUSBLENDEN, None)]
    z, out = takt(z, uhr, 1.0)
    assert out == ()


def test_normal_stumm_fenster_erreicht():
    """normal | Uhr erreicht „stumm“-Fenster -> StummBeginnt (Sitzung blendet aus) -> stumm."""
    uhr = uhr_um(21, 59)
    z, _ = start(uhr, f_stumm())
    uhr.vor(60)
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "stumm"
    assert ev.StummBeginnt() in out
    assert not any(isinstance(o, ev.Pausieren) for o in out)


def test_leiser_stumm_fenster_erreicht():
    """leiser | Uhr erreicht „stumm“-Fenster -> stumm; die Absenk-Rampe endet."""
    uhr = uhr_um(20, 59)
    z, _ = start(uhr, f_leiser(bis="22:30"), f_stumm(von="21:30"), wirksam=70)
    z, _ = takt(z, uhr)
    assert quiet.kennzeichen(z) == "leiser"
    uhr.vor(31 * 60)  # 21:30
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "stumm"
    assert ev.StummBeginnt() in out
    # die Rampe von „ausblenden“ ist beendet, sonst bliebe sie stehen
    assert z.absenken is None
    assert (GRENZE_AUSBLENDEN, None) in grenzen_aus(out)
    assert (GRENZE_LEISE_ZEIT, 25) in grenzen_aus(out)


def test_stumm_fenster_endet_nur_stumm_endet_nichts_startet():
    """stumm | Fenster endet -> Grenze aus -> normal; Entscheidung B: nur StummEndet, kein Abspielen."""
    uhr = uhr_um(6, 59)
    z, _ = start(uhr, f_stumm())
    z, _ = takt(z, uhr)
    assert quiet.kennzeichen(z) == "stumm"
    uhr.vor(60)
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "normal"
    assert ev.StummEndet() in out
    assert not any(isinstance(o, (ev.Abspielen, ev.LautstaerkeSetzen, ev.Pausieren)) for o in out)


def test_leiser_fenster_endet():
    """leiser | Fenster endet -> Grenze aus -> normal."""
    uhr = uhr_um(20, 59)
    z, out = start(uhr, f_leiser(), wirksam=10)
    assert quiet.kennzeichen(z) == "leiser"
    assert grenzen_aus(out) == [(GRENZE_LEISE_ZEIT, 25)]
    uhr.vor(60)
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "normal"
    assert grenzen_aus(out) == [(GRENZE_LEISE_ZEIT, None)]


def test_stumm_zu_leiser_fenster_ueberlappt():
    """stumm endet, ein „leiser“-Fenster ist noch aktiv: StummEndet und Grenze, Zustand leiser."""
    uhr = uhr_um(21, 59)
    z, _ = start(uhr, f_stumm(von="21:00", bis="22:00"), f_leiser(von="20:00", bis="23:00", grenze=30))
    z, _ = takt(z, uhr)
    assert quiet.kennzeichen(z) == "stumm"
    uhr.vor(60)
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "leiser"
    assert ev.StummEndet() in out
    assert (GRENZE_LEISE_ZEIT, 30) in grenzen_aus(out)


@pytest.mark.parametrize("vorher", ["normal", "leiser", "stumm"])
def test_zeit_nicht_vertrauenswuerdig_nie_stumm(vorher):
    """beliebig | Zeit nicht vertrauenswürdig -> kleinste „leiser“-Grenze aller Fenster, nie stumm."""
    uhr = uhr_um({"normal": 12, "leiser": 20, "stumm": 23}[vorher], 0)
    z, _ = start(uhr, f_leiser("a", grenze=40), f_leiser("b", von="08:00", bis="09:00", grenze=15), f_stumm(), wirksam=10)
    z, _ = takt(z, uhr)
    assert quiet.kennzeichen(z) == vorher
    uhr.setze_zeit("unbekannt", False)
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "leiser"
    assert (GRENZE_LEISE_ZEIT, 15) in grenzen_aus(out)
    assert any(isinstance(o, ev.Protokoll) and o.ebene == "WARNING" and o.ereignis == "zeit" for o in out)
    # nie „stumm“, auch nicht mitten im stumm-Fenster
    assert ev.StummBeginnt() not in out


def test_zeit_nicht_vertrauenswuerdig_ohne_leiser_fenster_normal():
    uhr = uhr_um(23, 0, zeit_ok=False)
    z, out = start(uhr, f_stumm())
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "normal"
    assert ev.StummBeginnt() not in out


def test_zeit_nicht_vertrauenswuerdig_keine_fenster():
    uhr = uhr_um(23, 0, zeit_ok=False)
    z, _ = start(uhr)
    z, out = takt(z, uhr)
    assert quiet.kennzeichen(z) == "normal"


def test_zeit_wieder_vertrauenswuerdig_wirkung_nach_uhrzeit():
    """beliebig | Zeit wieder vertrauenswürdig -> Wirkung nach Uhrzeit."""
    uhr = uhr_um(23, 0, zeit_ok=False)
    z, _ = start(uhr, f_leiser(grenze=40), f_stumm(), wirksam=10)
    z, _ = takt(z, uhr)
    assert quiet.kennzeichen(z) == "leiser"
    uhr.setze_zeit("ntp", True)
    z, out = quiet.step(z, ev.ZeitquelleGeaendert("ntp", True), uhr.jetzt())
    assert quiet.kennzeichen(z) == "stumm"
    assert ev.StummBeginnt() in out
    assert any(isinstance(o, ev.Protokoll) and o.ergebnis == "wieder_vertrauenswuerdig" for o in out)


def test_zeit_ok_wechsel_im_leiser_fenster_behaelt_kleinere_grenze():
    uhr = uhr_um(20, 0)
    z, out = start(uhr, f_leiser("a", grenze=40), f_leiser("b", von="08:00", bis="09:00", grenze=15), wirksam=10)
    assert grenzen_aus(out) == [(GRENZE_LEISE_ZEIT, 40)]
    uhr.setze_zeit("unbekannt", False)
    z, out = takt(z, uhr)
    assert grenzen_aus(out) == [(GRENZE_LEISE_ZEIT, 15)]


# ---------------------------------------------------------------- Fenster, Uhrzeit, Zeitzone


def test_fenstergrenzen_von_inklusive_bis_exklusive():
    lz = ev.LeiseZeiten("Europe/Berlin", (f_leiser(von="19:30", bis="21:00"),))
    assert quiet.wirkung_jetzt(lz, uhr_um(19, 29).jetzt())[0] == "normal"
    assert quiet.wirkung_jetzt(lz, uhr_um(19, 30).jetzt()) == ("leiser", 25)
    assert quiet.wirkung_jetzt(lz, uhr_um(20, 59).jetzt()) == ("leiser", 25)
    assert quiet.wirkung_jetzt(lz, uhr_um(21, 0).jetzt())[0] == "normal"


def test_wochentage():
    lz = ev.LeiseZeiten("Europe/Berlin", (f_leiser(tage=(1,)),))  # nur Montag
    assert quiet.wirkung_jetzt(lz, uhr_um(20, 0, tag=13).jetzt()) == ("leiser", 25)  # Montag
    assert quiet.wirkung_jetzt(lz, uhr_um(20, 0, tag=14).jetzt())[0] == "normal"  # Dienstag


def test_fenster_ueber_mitternacht():
    lz = ev.LeiseZeiten("Europe/Berlin", (f_stumm(tage=(1,)),))  # Montag 22:00 bis Dienstag 07:00
    assert quiet.wirkung_jetzt(lz, uhr_um(23, 0, tag=13).jetzt())[0] == "stumm"
    assert quiet.wirkung_jetzt(lz, uhr_um(3, 0, tag=14).jetzt())[0] == "stumm"  # Dienstag früh: gehört zu Montag
    assert quiet.wirkung_jetzt(lz, uhr_um(7, 0, tag=14).jetzt())[0] == "normal"
    assert quiet.wirkung_jetzt(lz, uhr_um(23, 0, tag=14).jetzt())[0] == "normal"  # Dienstag Abend: kein Fenster
    assert quiet.wirkung_jetzt(lz, uhr_um(3, 0, tag=13).jetzt())[0] == "normal"  # Montag früh: Sonntag fehlt


def test_mehrere_aktive_fenster_stumm_gewinnt_sonst_kleinste_grenze():
    lz = ev.LeiseZeiten("Europe/Berlin", (f_leiser("a", grenze=40), f_leiser("b", grenze=20), f_stumm("s", "20:00", "21:00")))
    assert quiet.wirkung_jetzt(lz, uhr_um(20, 30).jetzt()) == ("stumm", None)
    lz2 = ev.LeiseZeiten("Europe/Berlin", (f_leiser("a", grenze=40), f_leiser("b", grenze=20)))
    assert quiet.wirkung_jetzt(lz2, uhr_um(20, 30).jetzt()) == ("leiser", 20)


def test_zeitzone_aus_der_konfiguration():
    # 20:30 Berlin = 19:30 London
    lz = ev.LeiseZeiten("Europe/London", (f_leiser(von="19:00", bis="20:00"),))
    assert quiet.wirkung_jetzt(lz, uhr_um(20, 30).jetzt()) == ("leiser", 25)
    lz = ev.LeiseZeiten("Europe/Berlin", (f_leiser(von="19:00", bis="20:00"),))
    assert quiet.wirkung_jetzt(lz, uhr_um(20, 30).jetzt())[0] == "normal"


def test_sommerzeit_vorstellen_nicht_existierende_ortszeit_gilt_als_naechste_minute():
    # 2024-03-31: 02:00 -> 03:00. Ein Fenster 02:30-04:00 beginnt um 03:00.
    lz = ev.LeiseZeiten("Europe/Berlin", (f_stumm("x", "02:30", "04:00"),))
    vor = SimUhr(wall=datetime(2024, 3, 31, 1, 59, 59, tzinfo=BERLIN).timestamp())
    assert quiet.wirkung_jetzt(lz, vor.jetzt())[0] == "normal"
    um3 = SimUhr(wall=datetime(2024, 3, 31, 3, 0, tzinfo=BERLIN).timestamp())
    assert quiet.wirkung_jetzt(lz, um3.jetzt())[0] == "stumm"
    # ein Fenster, das dort endet, endet um 03:00
    lz = ev.LeiseZeiten("Europe/Berlin", (f_stumm("x", "01:00", "02:30"),))
    assert quiet.wirkung_jetzt(lz, SimUhr(wall=datetime(2024, 3, 31, 1, 59, tzinfo=BERLIN).timestamp()).jetzt())[0] == "stumm"
    assert quiet.wirkung_jetzt(lz, um3.jetzt())[0] == "normal"


def test_sommerzeit_zurueckstellen_fenster_ist_eine_stunde_laenger():
    # 2023-10-29: 03:00 -> 02:00. Fenster 19:30 bis 07:00 beginnt am 28.10. und dauert 12,5 h statt 11,5 h.
    lz = ev.LeiseZeiten("Europe/Berlin", (f_stumm("x", "19:30", "07:00"),))
    am_28 = datetime(2023, 10, 28, 19, 30, tzinfo=BERLIN)
    ende = datetime(2023, 10, 29, 7, 0, tzinfo=BERLIN)
    assert (ende - am_28).total_seconds() == 11.5 * 3600  # Wanduhr-Differenz, gleiche Zone
    ende_utc = ende.timestamp()
    assert quiet.wirkung_jetzt(lz, SimUhr(wall=ende_utc - 1).jetzt())[0] == "stumm"
    assert quiet.wirkung_jetzt(lz, SimUhr(wall=ende_utc).jetzt())[0] == "normal"
    assert (ende_utc - am_28.timestamp()) == 12.5 * 3600


def test_sommerzeit_zurueckstellen_mehrdeutige_zeit_gilt_als_erstes_auftreten():
    # 02:30 kommt am 2023-10-29 zweimal; ein Fenster 02:30-04:00 beginnt beim ersten Auftreten (Sommerzeit).
    lz = ev.LeiseZeiten("Europe/Berlin", (f_stumm("x", "02:30", "04:00"),))
    erstes = datetime(2023, 10, 29, 2, 30, tzinfo=BERLIN, fold=0).timestamp()
    assert quiet.wirkung_jetzt(lz, SimUhr(wall=erstes - 1).jetzt())[0] == "normal"
    assert quiet.wirkung_jetzt(lz, SimUhr(wall=erstes).jetzt())[0] == "stumm"
    # nach dem zweiten Auftreten (eine Stunde später) bleibt es aktiv; es hört nicht doppelt auf
    assert quiet.wirkung_jetzt(lz, SimUhr(wall=erstes + 3600).jetzt())[0] == "stumm"


# ---------------------------------------------------------------- Abnahme und Sonderfälle


def test_ohne_konfiguration_normal():
    uhr = uhr_um(23, 0)
    z, out = takt(quiet.neuer_zustand(), uhr)
    assert quiet.kennzeichen(z) == "normal" and out == ()


def test_neue_konfiguration_wirkt_sofort():
    uhr = uhr_um(20, 0)
    z, _ = start(uhr)
    z, out = quiet.step(z, ev.KonfigGeladen(konfig(f_stumm("s", "19:00", "21:00"))), uhr.jetzt())
    assert quiet.kennzeichen(z) == "stumm" and ev.StummBeginnt() in out
    # Fenster entfernt: stumm endet, nichts startet
    z, out = quiet.step(z, ev.KonfigGeladen(konfig()), uhr.jetzt())
    assert quiet.kennzeichen(z) == "normal" and ev.StummEndet() in out


def test_unbekannte_ereignisse_aendern_nichts():
    uhr = uhr_um(20, 0)
    z, _ = start(uhr, f_stumm("s", "19:00", "21:00"))
    z2, out = quiet.step(z, ev.Abgehoben(1, None), uhr.jetzt())
    assert z2 == z and out == ()


def test_quiet_gibt_nie_pausieren_oder_abspielen_aus():
    uhr = uhr_um(0, 0)
    z, _ = start(uhr, f_leiser(von="00:00", bis="01:00"), f_stumm("s", "01:00", "02:00"), wirksam=90)
    alle = []
    for _ in range(3 * 3600 * 2):
        z, out = takt(z, uhr, 1.0)
        alle += out
    assert not any(isinstance(o, (ev.Pausieren, ev.Abspielen)) for o in alle)
    assert alle.count(ev.StummBeginnt()) == 1 and alle.count(ev.StummEndet()) == 1


def test_takt_ohne_aenderung_ist_still():
    uhr = uhr_um(12, 0)
    z, _ = start(uhr, f_stumm())
    for _ in range(50):
        z, out = takt(z, uhr, 0.1)
        assert out == ()


# ---------------------------------------------------------------- Konflikte (mit dem Kern-Regelsatz)


def test_stumm_gegen_lernmodus_hinweiston_statt_toenen():
    """Stumm gegen Lernmodus: die Box lernt, bestätigt mit dem leisen Ton (Regel 6.2.2 und 6.2.3)."""
    uhr = uhr_um(23, 0)
    q, _ = start(uhr, f_stumm())
    q, _ = takt(q, uhr)
    assert quiet.kennzeichen(q) == "stumm"
    l, out = learn.step(learn.neuer_zustand(), ev.HaLernmodus("b1", uhr.wall + 60), uhr.jetzt())
    assert learn.kennzeichen(l) == "lernt"  # lernt trotzdem
    toene = [o for o in out if isinstance(o, ev.TonSpielen)]
    assert [t.ton for t in toene] == ["lernen_beginn"]
    ergebnis = core._konflikte(list(out) + [ev.TonSpielen("lernen_ende")], quiet.kennzeichen(q))
    assert [o.ton for o in ergebnis if isinstance(o, ev.TonSpielen)] == ["hinweis"]  # ein Ton, leise


@pytest.mark.parametrize("ton", ["start", "unbekannt", "lernen_beginn", "lernen_ende", "fehler", "akku_leer"])
def test_toene_unter_stumm_werden_zum_hinweis(ton):
    assert core._konflikte([ev.TonSpielen(ton)], "stumm") == [ev.TonSpielen("hinweis")]


@pytest.mark.parametrize("ton", ["pruef_ok", "pruef_fehler"])
def test_pruefton_bleibt_unter_stumm(ton):
    assert core._konflikte([ev.TonSpielen(ton)], "stumm") == [ev.TonSpielen(ton)]


@pytest.mark.parametrize("ruhe", ["normal", "leiser"])
def test_toene_ausserhalb_stumm_bleiben(ruhe):
    assert core._konflikte([ev.TonSpielen("start")], ruhe) == [ev.TonSpielen("start")]


def test_leiser_und_kopfhoerer_minimum_aller_grenzen():
    """Mehrere Grenzen gleichzeitig (Kopfhörer, „leiser“, global): es gilt das Minimum."""
    uhr = uhr_um(20, 0)
    z, out = start(uhr, f_leiser(grenze=25), wirksam=10)
    grenzen = {GRENZE_GLOBAL: 80, GRENZE_KOPFHOERER: 35}
    for name, p in grenzen_aus(out):
        grenzen[name] = p
    assert wirksame_grenze(grenzen) == 25
    grenzen[GRENZE_KOPFHOERER] = 10  # Kopfhörer leiser als das Fenster
    assert wirksame_grenze(grenzen) == 10


def test_absenken_wird_vom_kern_geklemmt_nie_lauter_als_wirksam():
    """Während der Rampe liegt die wirksame Lautstärke nie über der Kopfhörer-Grenze und nie über ``von``."""
    uhr = uhr_um(19, 29)
    z, _ = start(uhr, f_leiser(grenze=25), wirksam=60)
    uhr.vor(60)
    grenzen = {GRENZE_GLOBAL: 80, GRENZE_KOPFHOERER: 50}
    wirksam = 50
    z, _ = quiet.step(z, ev.LautstaerkeGeaendert(wirksam), uhr.jetzt())
    letzter = wirksam
    for _ in range(60):
        z, out = takt(z, uhr, 0.1)
        for name, p in grenzen_aus(out):
            if p is None:
                grenzen.pop(name, None)
            else:
                grenzen[name] = p
        neu = wirksame_grenze(grenzen)
        assert neu <= 50 and neu <= letzter
        letzter = neu
    assert letzter == 25


def test_rampe_bei_wirksam_gleich_grenze_ohne_absenken():
    uhr = uhr_um(19, 29)
    z, _ = start(uhr, f_leiser(grenze=25), wirksam=25)
    uhr.vor(60)
    z, out = takt(z, uhr)
    assert grenzen_aus(out) == [(GRENZE_LEISE_ZEIT, 25)]


def test_wechsel_leiser_zu_leiser_andere_grenze():
    uhr = uhr_um(20, 0)
    z, out = start(uhr, f_leiser("a", "19:00", "21:00", 30), f_leiser("b", "20:30", "22:00", 15), wirksam=10)
    assert grenzen_aus(out) == [(GRENZE_LEISE_ZEIT, 30)]
    uhr.vor(30 * 60)
    z, out = takt(z, uhr)
    assert grenzen_aus(out) == [(GRENZE_LEISE_ZEIT, 15)]
    assert quiet.kennzeichen(z) == "leiser"
