"""CUJ 25: Andocken und Abziehen (Ein/Aus, 10.11.; AP E1-7) und die Fälle der Doppel-Ton-Tabelle (Entwurf 6.3).

Echter Kern (mit ``idle``, ``quiet``, Regel 6.2.2a) und ``LedLogik`` über ``BedienBox``; die Zeit springt in Takten.
Die Box startet ohne Strom (erste Messung „kein Strom“) und ist bereit; die Sperre von 10 s ab ``Bereit`` ist vorbei, wo der Test es sagt.
"""

from __future__ import annotations

import pytest
from fixtures import stufe4
from fixtures.stufe4 import BedienBox, wall

from tobibox import events as ev
from tobibox import led

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"
SPERRE = 10.0


def aufbau(medien):
    stufe4.serie(medien, "rabe", ["a.wav", "b.wav"], SERIE, "Rabe", 200.0)
    stufe4.ueberraschung(medien)


@pytest.fixture
def box(tmp_path):
    b = BedienBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)
    b.sende(ev.AkkuStand(70))
    b.sende(ev.LaderGeaendert(False))  # erste Messung: kein Strom
    b.uhr.setze_wall(wall(2026, 11, 9, 12, 0))
    b.laufe(led.AUFWACHEN_S + SPERRE)  # Lauflicht und Sperre ab ``Bereit`` sind vorbei
    return b


def toene(box, ab=0):
    return [b.ton for b in box.befehle(ev.TonSpielen, ab)]


def syncs(box, ab=0):
    return box.befehle(ev.SyncStarten, ab)


def andocken(box, quelle="pisugar"):
    n = len(box.log)
    box.sende(ev.LaderGeaendert(True, quelle))
    return n


# --- Bereit: Andocken und Abziehen ------------------------------------------------------------------------


def spitze(box, dauer_s):
    """Größte Helligkeit des Rings in ``dauer_s`` (im Takt des Kerns von 100 ms abgeholt)."""
    h = 0.0
    for _ in range(int(round(dauer_s / 0.1))):
        h = max(h, box.ring().helligkeit)
        box.laufe(0.1)
    return h


def test_bereit_andocken_ring_zwei_schnelle_pulse_ton_lader_und_sync(box):
    n = andocken(box)
    assert toene(box, n) == ["lader"]
    assert [s.grund for s in syncs(box, n)] == ["start_lader"]
    # Ergänzung X (11.11.): zwei schnelle, weiche Pulse bis zur Akku-Helligkeit, keine 5-s-Anzeige mehr
    assert box.ring().zustand == led.ANSTECKEN
    assert spitze(box, led.ANSTECKEN_DAUER_S - 0.1) == pytest.approx(led.AKKU_HELL, abs=0.5)
    box.laufe(0.3)
    assert box.ring_zustand() not in (led.ANSTECKEN, led.AKKU)  # danach direkt der Ladestand bzw. aus


def test_bereit_andocken_verwirft_die_frist_abziehen_beginnt_sie_ab_jetzt(box):
    box.laufe(300)
    andocken(box)
    box.laufe(3000)
    assert box.befehle(ev.Herunterfahren) == []
    n = len(box.log)
    box.sende(ev.LaderGeaendert(False))
    assert toene(box, n) == [] and syncs(box, n) == []  # Abziehen: kein Ton, kein Sync
    assert box.ring_zustand() == led.AKKU  # Ring Akku 5 s
    box.laufe(599)
    assert box.befehle(ev.Herunterfahren) == []
    box.laufe(2)
    assert [b.grund for b in box.befehle(ev.Herunterfahren)] == ["leerlauf"]


def test_abziehen_ring_zeigt_den_akku_nach_prozent_nicht_blau(box):
    box.sende(ev.AkkuStand(80))
    andocken(box)
    box.laufe(SPERRE)
    box.sende(ev.LaderGeaendert(False))
    assert box.ring().leds[0] == led.GRUEN


# --- Spielt ---------------------------------------------------------------------------------------------


def test_spielt_andocken_nur_ring_3_s_kein_ton_sync_wird_geprueft(box):
    box.auflege(UID)
    box.laufe(2.5)
    n = len(box.log)
    box.sende(ev.LaderGeaendert(True))
    assert toene(box, n) == []  # Entscheidung L: kein Ton neben dem Hörspiel
    assert [s.grund for s in syncs(box, n)] == ["start_lader"]
    assert box.ring_zustand() == led.ANSTECKEN
    box.laufe(led.ANSTECKEN_DAUER_S + 0.1)
    assert box.ring_zustand() == led.LAEUFT  # danach zurück


def test_spielt_abziehen_nur_ring_3_s(box):
    andocken(box)
    box.laufe(SPERRE + led.AKKU_ANZEIGE_S)
    box.auflege(UID)
    box.laufe(2.5)
    n = len(box.log)
    box.sende(ev.LaderGeaendert(False))
    assert toene(box, n) == [] and syncs(box, n) == []
    assert box.ring_zustand() == led.AKKU
    box.laufe(3.2)
    assert box.ring_zustand() == led.LAEUFT


# --- Update läuft -----------------------------------------------------------------------------------------


def test_update_laeuft_nur_ring_kein_sync_kein_ton(box):
    box.sende(ev.UpdateGestartet("1.2.0"))
    n = andocken(box)
    assert toene(box, n) == [] and syncs(box, n) == []
    assert box.ring_zustand() == led.ANSTECKEN


# --- Sperre / Wackelkontakt ----------------------------------------------------------------------------


def test_wackelkontakt_hoechstens_eine_rueckmeldung_je_10_s(box):
    n = len(box.log)
    for _ in range(6):
        box.sende(ev.LaderGeaendert(True))
        box.laufe(0.5)
        box.sende(ev.LaderGeaendert(False))
        box.laufe(0.5)
    assert toene(box, n) == ["lader"]
    assert len(syncs(box, n)) == 1
    # nach der Sperre wieder eine Rückmeldung
    box.laufe(SPERRE)
    n = len(box.log)
    box.sende(ev.LaderGeaendert(True))
    assert toene(box, n) == ["lader"]


# --- Doppel-Ton-Tabelle ---------------------------------------------------------------------------------


def test_aus_strom_kommt_erste_messung_ist_strom_auch_spaet_kein_lader_ton(tmp_path):
    """Z03/Hauptknopf am Sockel: Die Box startet (Frühton), die erste Messung ist „Strom“, auch wenn sie spät kommt: kein ``lader``."""
    b = BedienBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)
    b.sende(ev.AkkuStand(70))
    b.laufe(SPERRE + 20)  # Bereit liegt weit zurück, noch kein Wert einer Quelle
    n = len(b.log)
    b.sende(ev.LaderGeaendert(True, "leser"))
    assert toene(b, n) == [] and [s.grund for s in syncs(b, n)] == ["start_lader"]
    assert b.ring_zustand() == led.AKKU  # die Start-Anzeige des Rings (keine Andock-Rückmeldung)
    n = len(b.log)
    b.sende(ev.LaderGeaendert(True, "pisugar"))  # die zweite Quelle meldet dasselbe: nichts
    assert toene(b, n) == [] and syncs(b, n) == []


def test_erster_wert_der_zweiten_quelle_ist_keine_rueckmeldung(tmp_path):
    b = BedienBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)
    b.laufe(SPERRE + 20)
    b.sende(ev.LaderGeaendert(False, "pisugar"))
    n = len(b.log)
    b.sende(ev.LaderGeaendert(True, "leser"))  # der Leser sieht Strom, pisugar nicht: Widerspruch, der Leser gilt
    assert toene(b, n) == [] and b.befehle(ev.Herunterfahren) == []
    b.laufe(100 * 600)
    assert b.befehle(ev.Herunterfahren) == []  # am Sockel nie aus


def test_strom_in_den_ersten_10_s_nach_bereit_kein_ton_aber_zustand_wechselt(tmp_path):
    b = BedienBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)
    b.sende(ev.LaderGeaendert(False))
    b.laufe(3)  # 3 s nach ``Bereit``
    n = len(b.log)
    b.sende(ev.LaderGeaendert(True))
    assert toene(b, n) == []  # der Frühton läuft noch oder ist gerade fertig
    b.laufe(5000)
    assert b.befehle(ev.Herunterfahren) == []


def test_dienst_neustart_am_sockel_kein_lader_ton(box):
    andocken(box)
    box.neustart()  # Dienst-Neustart: neuer Kern, erste Messung ist „Strom“
    n = len(box.log)
    box.sende(ev.LaderGeaendert(True))
    assert "lader" not in toene(box, n)


def test_spielt_kein_lader_ton_siehe_oben_und_nach_dem_hoeren_wieder(box):
    box.auflege(UID)
    box.laufe(2)
    n = andocken(box)
    assert "lader" not in toene(box, n)
    box.laufe(SPERRE + 1)
    box.hebe_ab()
    box.sende(ev.LaderGeaendert(False))
    box.laufe(SPERRE + 1)
    n = andocken(box)
    assert toene(box, n) == ["lader"]  # beim Hören nicht, danach wieder


# --- Regel 6.2.2a: wann der Ton entfällt (der Ring und der Sync-Check bleiben) -----------------------------------


def _fenster(wirkung, grenze=None):
    return (stufe4.fenster("f", wirkung, "10:00", "14:00", grenze),)


@pytest.mark.parametrize("wirkung, grenze, helligkeit", [("leiser", 25, led.AKKU_HELL_LEISER), ("stumm", None, led.AKKU_HELL_STUMM)])
def test_leise_zeiten_kein_ton_ring_mit_eigener_helligkeit(box, wirkung, grenze, helligkeit):
    stufe4.setze_konfig(box, fenster_liste=_fenster(wirkung, grenze))
    box.laufe(SPERRE + 4)
    assert stufe4.zeile(box).ruhe == wirkung
    n = andocken(box)
    assert "lader" not in toene(box, n) and [s.grund for s in syncs(box, n)] == ["start_lader"]
    assert box.ring().zustand == led.ANSTECKEN
    assert spitze(box, led.ANSTECKEN_DAUER_S - 0.1) == pytest.approx(helligkeit, abs=0.3)  # Spitze der Pulse = Akku-Helligkeit der Leise-Zeit


def test_unsichere_uhr_kein_lader_ton(box):
    box.uhr.setze_zeit("unbekannt", False)
    box.laufe(1)
    n = andocken(box)
    assert "lader" not in toene(box, n) and syncs(box, n)


def test_lernmodus_kein_lader_ton(box):
    box.sende(ev.HaLernmodus("b1", box.uhr.wall + 600))
    assert box.kern.teil["learn"].modus == "lernt"
    n = andocken(box)
    assert "lader" not in toene(box, n) and syncs(box, n)


def test_gute_nacht_laeuft_ring_5_prozent(box):
    lg = box.led  # Gute Nacht: die Akku-Anzeige ist 5 % hell
    lg.beobachte(ev.ZustandMelden("pausiert", "leerlauf", None, False, "normal", "laeuft", True), box.uhr.mono)
    lg.akku_zeigen(box.uhr.mono)
    assert lg.ring(box.uhr.mono + 0.1).zustand == led.AKKU
    assert lg.ring(box.uhr.mono + 0.1).helligkeit == led.AKKU_HELL_LEISER


# --- Leser-Wert verfällt (V2) --------------------------------------------------------------------------


def test_leser_ausfall_dann_gilt_pisugar_und_die_frist_beginnt(tmp_path):
    b = BedienBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)
    b.sende(ev.LaderGeaendert(False, "pisugar"))
    b.sende(ev.LaderGeaendert(True, "leser"))
    b.laufe(5000)
    assert b.befehle(ev.Herunterfahren) == []
    n = len(b.log)
    b.sende(ev.LeserAlarm("getrennt"))  # USB-Aussetzer: der alte Leser-Wert „Strom“ gilt nicht mehr
    assert toene(b, n) == []  # keine Rückmeldung (V3)
    b.laufe(599)
    assert b.befehle(ev.Herunterfahren) == []
    b.laufe(2)
    assert [x.grund for x in b.befehle(ev.Herunterfahren)] == ["leerlauf"]
