"""CUJ 16: Leerlauf-Abschaltung (AP 4.3 und 4.8; Ein/Aus, 10.11.: Frist 10 min nur ohne Strom).

Nach 10 min ohne Wiedergabe und **ohne Strom am Eingang** fährt die Box herunter (auch mit liegendem Tobie), außer Sync, Update oder Lernmodus
laufen. Mit Strom bleibt sie bereit und schaltet nie von selbst ab. Kommt Strom, wird die Frist verworfen; wird die Box abgenommen, beginnt
sie ab dem Abnehmen (R9). Bedienung setzt den Zähler zurück. In der Simulation wird das Herunterfahren nur protokolliert.
Andocken und Abziehen im Einzelnen: CUJ 25; die Box am Sockel: CUJ 23; Pause ohne Sockel: CUJ 24.

Echter Kern mit ``idle``; die Zeit springt in Takten (``sende(Takt, dt=…)``).
"""

from __future__ import annotations

import pytest
from conftest import CujBox
from fixtures import stufe4

from tobibox import events as ev
from tobibox.idle import AKKU_TON_WARTEN_S, AUSSCHALT_AUSBLENDEN_S, LEERLAUF_S

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"
MIN = 60.0


def aufbau(medien):
    stufe4.serie(medien, "rabe", ["a.wav", "b.wav"], SERIE, "Rabe", 60.0)
    stufe4.ueberraschung(medien)


@pytest.fixture
def box(tmp_path):
    """Eine Box ohne Strom am Eingang (die erste Messung des Stroms ist „kein Strom“)."""
    b = CujBox(tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, aufbau)
    b.sende(ev.LaderGeaendert(False))
    return b


def fahren(box, ab=0):
    return box.befehle(ev.Herunterfahren, ab)


def warte(box, sekunden: float) -> list:
    """Die Zeit springt; ein Takt danach (wie der Taktgeber). Gibt die Befehle dieses Takts zurück."""
    return box.sende(ev.Takt(), dt=sekunden)


def strom(box) -> str:
    return stufe4.zeile(box).strom


def test_nach_10_minuten_leerlauf_wird_heruntergefahren(box):
    assert strom(box) == "leerlauf"
    warte(box, 10 * MIN - 1)
    assert fahren(box) == [] and strom(box) == "leerlauf"
    warte(box, 2)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]
    assert strom(box) == "herunterfahren"


def test_herunterfahren_ist_der_letzte_befehl_der_ausgabe_und_kommt_nur_einmal(box):
    warte(box, 10 * MIN - 1)
    aus = warte(box, 2)
    assert isinstance(aus[-1], ev.Herunterfahren)
    warte(box, 10 * MIN)
    assert len(fahren(box)) == 1


def test_ein_tobie_der_liegt_haelt_die_box_wach(box):
    box.auflege(UID)
    warte(box, 3 * LEERLAUF_S)
    assert fahren(box) == [] and strom(box) == "aktiv"


def test_nach_dem_abheben_zaehlt_der_leerlauf_von_neuem(box):
    box.auflege(UID)
    warte(box, 30 * MIN)
    box.hebe_ab()
    assert strom(box) == "leerlauf"
    warte(box, 10 * MIN - 1)
    assert fahren(box) == []
    warte(box, 2)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_spielende_wiedergabe_ist_kein_leerlauf(box):
    box.auflege(UID)
    warte(box, 2 * LEERLAUF_S - 1)  # die Folge ist 60 s lang: sie wäre zu Ende; hier zählt nur, dass sie spielt
    box.sende(ev.Takt())
    assert fahren(box) == [] or box.modus != "spielt"


def test_pausierte_wiedergabe_mit_liegendem_tobie_ist_leerlauf(box):
    """Entscheidung O (09.11., B5): 10 min lang wird nichts gespielt, egal ob ein Tobie liegt. Die Box schaltet auch nachts ab."""
    box.auflege(UID)
    box.sende(ev.Hauptknopf("kurz"))  # Pause, der Tobie liegt noch
    assert box.kern.session.figur is not None
    warte(box, LEERLAUF_S - 5)
    assert fahren(box) == []
    warte(box, 10)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_bedienung_mit_liegendem_tobie_setzt_den_zaehler_zurueck(box):
    box.auflege(UID)
    box.sende(ev.Hauptknopf("kurz"))
    warte(box, LEERLAUF_S - 60)
    box.sende(ev.LautstaerkeDrehen(2))  # Bedienung: der Zähler beginnt neu, die Wiedergabe bleibt pausiert
    assert box.modus == "pausiert"
    warte(box, LEERLAUF_S - 60)
    assert fahren(box) == []


def test_lernmodus_verhindert_die_abschaltung_danach_beginnt_der_zaehler_neu(box):
    warte(box, 9 * MIN)
    box.sende(ev.HaLernmodus("b1", box.uhr.wall + 600))
    assert box.kern.teil["learn"].modus == "lernt"
    warte(box, 2 * MIN - 1)  # 11 min nach dem Start: Lernmodus (2 min Frist) läuft noch
    assert fahren(box) == []
    warte(box, 2)  # Lernmodus ohne Tobie abgelaufen
    assert box.kern.teil["learn"].modus == "aus" and fahren(box) == []
    warte(box, 10 * MIN - 5)
    assert fahren(box) == []
    warte(box, 10)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_laufender_sync_verhindert_die_abschaltung_nach_dem_ende_geht_es_sofort(box):
    box.sende(ev.SyncGestartet())
    warte(box, 3 * LEERLAUF_S)
    assert fahren(box) == []
    box.sende(ev.SyncFertig(3, 0))
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_laufendes_update_verhindert_die_abschaltung(box):
    box.sende(ev.UpdateGestartet("1.2.0"))
    warte(box, 3 * LEERLAUF_S)
    assert fahren(box) == []
    box.sende(ev.SelbsttestErgebnis(True))
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_ein_offener_sync_haelt_die_abschaltung_auf(box):
    """Ein Start-Sync beim Andocken ist „offen“, bis er antwortet; die Abschaltung wartet darauf (ohne Strom: nach dem Abziehen)."""
    box.sende(ev.Bereit())
    box.sende(ev.LaderGeaendert(True), dt=20.0)  # Andocken nach der Sperre
    assert [b for b in box.log if b == ev.SyncStarten("start_lader")] != []
    box.sende(ev.LaderGeaendert(False), dt=1.0)  # abgenommen: die Frist beginnt jetzt
    box.sende(ev.SyncGestartet(), dt=1.0)
    warte(box, 10 * MIN)
    assert fahren(box) == []
    box.sende(ev.SyncFertig(1, 0))
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_mit_strom_schaltet_die_box_nie_von_selbst_ab(box):
    box.sende(ev.LaderGeaendert(True))
    warte(box, 100 * LEERLAUF_S)
    assert fahren(box) == [] and strom(box) == "leerlauf"


def test_strom_verwirft_die_frist_abnehmen_beginnt_sie_ab_dem_abnehmen(box):
    warte(box, 9 * MIN)
    box.sende(ev.LaderGeaendert(True))
    warte(box, 3 * LEERLAUF_S)
    assert fahren(box) == []
    box.sende(ev.LaderGeaendert(False))  # abgenommen: 10 min ab jetzt, nicht ab dem letzten Spielen
    warte(box, 10 * MIN - 2)
    assert fahren(box) == []
    warte(box, 3)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_hauptknopf_lang_blendet_aus_speichert_den_zeiger_und_faehrt_herunter_auch_im_sync(box):
    """Entscheidung Y (11.11.): ein laufendes Hörspiel wird 2 s ausgeblendet, dann Pause, Zeiger, Herunterfahren."""
    box.auflege(UID)
    box.laufe(8.0)
    box.sende(ev.SyncGestartet())
    n = len(box.log)
    box.sende(ev.Hauptknopf("lang"))
    assert fahren(box, n) == [] and not box.befehle(ev.Pausieren, n)  # noch nicht: erst ausblenden
    assert box.modus == "spielt" and strom(box) == "aktiv"
    box.laufe(AUSSCHALT_AUSBLENDEN_S + 0.2)
    assert [p.grund for p in box.befehle(ev.Pausieren, n)] == ["herunterfahren"]
    assert box.befehle(ev.ZeigerSpeichern, n)
    assert [b.grund for b in fahren(box, n)] == ["hauptknopf"]
    # Reihenfolge nach Rang: Pause, Zeiger, dann Herunterfahren zuletzt
    ab = [b for b in box.log[n:] if isinstance(b, (ev.Pausieren, ev.ZeigerSpeichern, ev.Herunterfahren))]
    assert [type(b) for b in ab] == [ev.Pausieren, ev.ZeigerSpeichern, ev.Herunterfahren]
    assert box.resume_json()["serien"][SERIE]["position_s"] > 0
    assert strom(box) == "herunterfahren"


def test_hauptknopf_lang_senkt_die_lautstaerke_ueber_2_s_und_faehrt_erst_danach_herunter(box):
    box.auflege(UID)
    box.laufe(3.0)
    start = stufe4.wirksam(box)
    assert start > 10
    n = len(box.log)
    box.sende(ev.Hauptknopf("lang"))
    box.laufe(1.0)
    mitte = stufe4.prozente(box, n)
    assert mitte and mitte == sorted(mitte, reverse=True) and 0 < mitte[-1] < start
    assert fahren(box, n) == [] and box.modus == "spielt"
    box.laufe(0.8)
    assert fahren(box, n) == []  # nach 1,8 s noch nicht
    box.laufe(0.4)
    assert [b.grund for b in fahren(box, n)] == ["hauptknopf"]
    werte = stufe4.prozente(box, n)
    assert werte == sorted(werte, reverse=True) and werte[-1] <= 2  # fällt nur, kein Springen zurück beim Pausieren


def test_nach_dem_ausblenden_ist_die_lautstaerke_wieder_der_wunsch_von_vorher(box):
    box.auflege(UID)
    box.laufe(3.0)
    wunsch = box.kern.wunsch
    box.sende(ev.Hauptknopf("lang"))
    box.laufe(AUSSCHALT_AUSBLENDEN_S + 0.2)
    assert fahren(box)
    assert "ausblenden" not in box.kern.grenzen and box.kern.wunsch == wunsch
    # Simulation: die Box bleibt an; der nächste Start spielt wieder mit dem Wunsch von vorher
    box.sende(ev.HerunterfahrenFehlgeschlagen("", simuliert=True))
    box.laufe(11.0)  # Rückkehr aus dem simulierten Herunterfahren
    assert strom(box) != "herunterfahren"
    box.hebe_ab()
    n = len(box.log)
    box.auflege(UID)
    spiel = [b for b in box.log[n:] if isinstance(b, (ev.LautstaerkeSetzen, ev.Abspielen))]
    assert isinstance(spiel[0], ev.LautstaerkeSetzen) and spiel[0].prozent == wunsch


def test_hauptknopf_lang_in_pausiert_faehrt_sofort_herunter(box):
    box.auflege(UID)
    box.laufe(3.0)
    box.sende(ev.Hauptknopf("kurz"))
    assert box.modus == "pausiert"
    n = len(box.log)
    box.sende(ev.Hauptknopf("lang"))
    assert [b.grund for b in fahren(box, n)] == ["hauptknopf"]
    assert min(stufe4.prozente(box, n), default=1) > 0  # kein Ausblenden


def test_hauptknopf_lang_ohne_wiedergabe_faehrt_sofort_herunter(box):
    n = len(box.log)
    box.sende(ev.Hauptknopf("lang"))
    assert [b.grund for b in fahren(box, n)] == ["hauptknopf"]


def test_waehrend_des_ausblendens_zaehlen_andere_tasten_nicht_und_ein_zweiter_langdruck_bricht_nicht_ab(box):
    box.auflege(UID)
    box.laufe(3.0)
    n = len(box.log)
    box.sende(ev.Hauptknopf("lang"))
    box.laufe(0.5)
    wunsch = box.kern.wunsch
    box.sende(ev.Hauptknopf("kurz"))  # würde sonst pausieren
    box.sende(ev.Weiter())
    box.sende(ev.Zurueck())
    box.sende(ev.LautstaerkeDrehen(5))
    box.sende(ev.Hauptknopf("lang"))
    assert box.kern.wunsch == wunsch
    assert box.modus == "spielt" and not box.befehle(ev.Pausieren, n) and fahren(box, n) == []
    box.laufe(AUSSCHALT_AUSBLENDEN_S)
    assert [b.grund for b in fahren(box, n)] == ["hauptknopf"]
    assert len(box.befehle(ev.Pausieren, n)) == 1


def toene(box, ab=0):
    return [t.ton for t in box.befehle(ev.TonSpielen, ab)]


def test_akku_tiefstand_bei_wiedergabe_erst_durchsage_dann_ausblenden_dann_herunterfahren(box):
    """Entscheidung Z (11.11.): ``akku_leer``, nach dem Ende des Tons 2 s ausblenden, Stelle speichern, herunterfahren."""
    box.auflege(UID)
    box.laufe(3.0)
    wunsch = box.kern.wunsch
    n = len(box.log)
    box.sende(ev.AkkuTiefstand())
    assert toene(box, n) == ["akku_leer"]
    assert fahren(box, n) == [] and not box.befehle(ev.Pausieren, n) and box.modus == "spielt"
    box.laufe(3.0)  # die Durchsage läuft (App: Hörspiel pausiert dafür); der Kern blendet noch nicht aus
    assert stufe4.prozente(box, n) == [] and fahren(box, n) == []
    box.sende(ev.TonFolgeEnde())
    box.laufe(1.0)
    mitte = stufe4.prozente(box, n)
    assert mitte and mitte == sorted(mitte, reverse=True) and mitte[-1] < wunsch
    assert fahren(box, n) == []
    box.laufe(1.2)
    assert [b.grund for b in fahren(box, n)] == ["akku_tiefstand"]
    assert [p.grund for p in box.befehle(ev.Pausieren, n)] == ["herunterfahren"]
    assert box.befehle(ev.ZeigerSpeichern, n) and not box.player.spielt
    assert toene(box, n) == ["akku_leer"]  # nur einmal
    assert "ausblenden" not in box.kern.grenzen and box.kern.wunsch == wunsch


def test_akku_tiefstand_ohne_ende_meldung_des_tons_blendet_nach_der_frist_trotzdem_aus(box):
    box.auflege(UID)
    box.laufe(3.0)
    n = len(box.log)
    box.sende(ev.AkkuTiefstand())
    box.laufe(AKKU_TON_WARTEN_S - 0.5)
    assert fahren(box, n) == [] and stufe4.prozente(box, n) == []
    box.laufe(1.0 + AUSSCHALT_AUSBLENDEN_S + 0.3)
    assert [b.grund for b in fahren(box, n)] == ["akku_tiefstand"]


def test_waehrend_der_durchsage_zaehlen_tasten_nicht(box):
    box.auflege(UID)
    box.laufe(3.0)
    n = len(box.log)
    box.sende(ev.AkkuTiefstand())
    wunsch = box.kern.wunsch
    for e in (ev.Hauptknopf("kurz"), ev.Weiter(), ev.Zurueck(), ev.LautstaerkeDrehen(5), ev.Hauptknopf("lang"), ev.AkkuTiefstand()):
        box.sende(e)
    assert box.kern.wunsch == wunsch and box.modus == "spielt" and fahren(box, n) == []
    assert toene(box, n) == ["akku_leer"]


def test_akku_tiefstand_ohne_wiedergabe_faehrt_sofort_herunter(box):
    n = len(box.log)
    box.sende(ev.AkkuTiefstand())
    assert [b.grund for b in fahren(box, n)] == ["akku_tiefstand"]
    assert toene(box, n) == ["akku_leer"]


def test_ende_des_hoerspiels_waehrend_der_durchsage_faehrt_sofort_herunter(box):
    box.auflege(UID)
    box.laufe(3.0)
    box.sende(ev.AkkuTiefstand())
    n = len(box.log)
    box.hebe_ab()
    assert [b.grund for b in fahren(box, n)] == ["akku_tiefstand"]


def test_tiefstand_waehrend_des_ausblendens_aendert_nichts(box):
    box.auflege(UID)
    box.laufe(3.0)
    box.sende(ev.Hauptknopf("lang"))
    box.laufe(0.5)
    n = len(box.log)
    box.sende(ev.AkkuTiefstand())
    assert fahren(box, n) == [] and toene(box, n) == []
    box.laufe(AUSSCHALT_AUSBLENDEN_S)
    assert [b.grund for b in fahren(box, n)] == ["hauptknopf"]


def test_akku_tiefstand_waehrend_sync_bricht_ab_speichert_und_faehrt_herunter(box):
    box.auflege(UID)
    box.laufe(8.0)
    box.sende(ev.SyncGestartet())
    n = len(box.log)
    box.sende(ev.AkkuTiefstand())
    assert [b.grund for b in box.befehle(ev.SyncAbbrechen, n)] == ["akku_tiefstand"]
    box.sende(ev.TonFolgeEnde())
    box.laufe(AUSSCHALT_AUSBLENDEN_S + 0.2)
    assert box.befehle(ev.ZeigerSpeichern, n)
    assert [b.grund for b in fahren(box, n)] == ["akku_tiefstand"]
    assert not box.player.spielt


@pytest.mark.parametrize(
    "bedienung", [ev.Hauptknopf("kurz"), ev.Weiter(), ev.Zurueck(), ev.LautstaerkeDrehen(2), ev.Kopfhoerer(True)]
)
def test_bedienung_setzt_den_leerlauf_zaehler_zurueck(box, bedienung):
    warte(box, 10 * MIN - 5)
    box.sende(bedienung)
    warte(box, 10)
    assert fahren(box) == []
    warte(box, 10 * MIN - 15)
    assert fahren(box) == []
    warte(box, 10)
    assert [b.grund for b in fahren(box)] == ["leerlauf"]


def test_nach_dem_herunterfahren_gibt_es_kein_zweites_herunterfahren(box):
    warte(box, 11 * MIN)
    assert fahren(box)
    n = len(box.log)
    box.auflege(UID)
    assert strom(box) == "herunterfahren"
    assert fahren(box, n) == []  # kein zweites Herunterfahren
