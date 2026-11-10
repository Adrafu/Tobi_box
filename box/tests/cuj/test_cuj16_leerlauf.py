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
from tobibox.idle import LEERLAUF_S

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


def test_hauptknopf_lang_speichert_den_zeiger_und_faehrt_herunter_auch_im_sync(box):
    box.auflege(UID)
    box.laufe(8.0)
    box.sende(ev.SyncGestartet())
    n = len(box.log)
    box.sende(ev.Hauptknopf("lang"))
    assert [p.grund for p in box.befehle(ev.Pausieren, n)] == ["herunterfahren"]
    assert box.befehle(ev.ZeigerSpeichern, n)
    assert [b.grund for b in fahren(box, n)] == ["hauptknopf"]
    # Reihenfolge nach Rang: Pause, Zeiger, dann Herunterfahren zuletzt
    ab = [b for b in box.log[n:] if isinstance(b, (ev.Pausieren, ev.ZeigerSpeichern, ev.Herunterfahren))]
    assert [type(b) for b in ab] == [ev.Pausieren, ev.ZeigerSpeichern, ev.Herunterfahren]
    assert box.resume_json()["serien"][SERIE]["position_s"] > 0


def test_akku_tiefstand_waehrend_sync_bricht_ab_speichert_und_faehrt_herunter(box):
    box.auflege(UID)
    box.laufe(8.0)
    box.sende(ev.SyncGestartet())
    n = len(box.log)
    box.sende(ev.AkkuTiefstand())
    assert [b.grund for b in box.befehle(ev.SyncAbbrechen, n)] == ["akku_tiefstand"]
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
