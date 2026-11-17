"""Paket B2: die Zählregel in ``gehoert.sqlite`` (Vertrag W, 15.1; Design Abschnitte 2, 4 und 11), ohne Home Assistant.

Mal, fertig (80 % über Portionen und Tage), Wiederholen, Pausen bis und über 30 Minuten, Mitternacht, Sommerzeit, ungefähres und unbekanntes Datum,
Nachlieferung (nur die Gruppe wird neu gerechnet), verwaist, Löschmarke, Doppelzustellung, ungültige Zeilen und die Ersetzregeln.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from custom_components.tobibox import gehoert as g
from custom_components.tobibox.gehoert import GehoertDb, Zeile, bestimme_datum, verarbeite_box_nachricht

BERLIN = ZoneInfo("Europe/Berlin")
Q = "box:box1"
MIN = 60


def utc(j: int, m: int, t: int, h: int = 0, mi: int = 0, s: int = 0) -> int:
    return int(datetime(j, m, t, h, mi, s, tzinfo=UTC).timestamp())


T0 = utc(2026, 11, 10, 10, 0, 0)  # 11:00 in Berlin


def zeile(n: int, beginn: int = T0, dauer: int = 100, ende: str = "pause", *, folge_dauer: int | None = None, datum: str = "sicher", serie: str = "rabe", folge: str = "a.mp3") -> Zeile:
    """Sitzung ``n``; ``dauer`` = Hörzeit und Länge der Sitzung in Sekunden."""
    return Zeile(f"00000000-0000-4000-8000-{n:012d}", serie, folge, folge_dauer, beginn, beginn + dauer if datum != "unbekannt" else dauer, datum, dauer, ende)


@pytest.fixture
def db(tmp_path: Path):
    d = GehoertDb(tmp_path / "tobibox" / "gehoert.sqlite")
    d.oeffne()
    yield d
    d.schliesse()


def nimm(db: GehoertDb, *zeilen: Zeile, quelle: str = Q, zone=BERLIN) -> dict[str, int]:
    return db.nimm_auf(quelle, list(zeilen), zone)


def stand(db: GehoertDb, quelle: str = Q) -> list[tuple[int, int, int]]:
    """``(neues_mal, mal_zaehlt, fertig)`` je Zeile in Eingangsreihenfolge."""
    return [(r["neues_mal"], r["mal_zaehlt"], r["fertig"]) for r in db.alle(quelle)]


# --------------------------------------------------------------------------------------------
# Datei und Schema
# --------------------------------------------------------------------------------------------


def test_datei_schema_pragmas_und_version(db: GehoertDb):
    con = sqlite3.connect(db.pfad)
    assert con.execute("PRAGMA user_version").fetchone()[0] == 1
    assert db._con.execute("PRAGMA journal_mode").fetchone()[0] == "truncate"  # gilt je Verbindung
    assert db._con.execute("PRAGMA synchronous").fetchone()[0] == 2  # FULL
    tabellen = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sitzungen", "technik", "loeschmarken"} <= tabellen
    spalten = [r[1] for r in con.execute("PRAGMA table_info(sitzungen)")]
    assert spalten == ["quelle", "sitzung", "serie", "folge", "folge_dauer_s", "beginn", "ende_um", "datum", "tag", "stunde", "gehoert_s", "ende", "grund", "neues_mal", "mal_zaehlt", "fertig"]
    schluessel = [r[1] for r in con.execute("PRAGMA table_info(sitzungen)") if r[5]]
    assert schluessel == ["quelle", "sitzung"]  # Hauptschlüssel (quelle, sitzung), in dieser Reihenfolge
    indizes = {tuple(x[2] for x in con.execute(f"PRAGMA index_info({i[1]})")) for i in con.execute("PRAGMA index_list(sitzungen)") if i[3] == "c"}
    assert indizes == {("quelle", "serie", "folge", "beginn"), ("serie", "folge", "beginn"), ("tag",), ("beginn",), ("quelle", "beginn")}
    assert {tuple(x[2] for x in con.execute(f"PRAGMA index_info({i[1]})")) for i in con.execute("PRAGMA index_list(technik)")} == {("box", "zeit")}
    con.close()


def test_zu_neue_datei_wird_nicht_geoeffnet(tmp_path: Path):
    pfad = tmp_path / "x" / "gehoert.sqlite"
    pfad.parent.mkdir()
    con = sqlite3.connect(pfad)
    con.execute("PRAGMA user_version=99")
    con.execute("CREATE TABLE t (a)")
    con.commit()
    con.close()
    d = GehoertDb(pfad)
    with pytest.raises(Exception):  # noqa: B017,PT011  (TobiboxFehler)
        d.oeffne()


def test_erneutes_oeffnen_behaelt_die_daten(tmp_path: Path):
    d = GehoertDb(tmp_path / "gehoert.sqlite")
    d.oeffne()
    nimm(d, zeile(1))
    d.schliesse()
    d2 = GehoertDb(tmp_path / "gehoert.sqlite")
    d2.oeffne()
    assert len(d2.alle()) == 1
    d2.schliesse()


# --------------------------------------------------------------------------------------------
# Mal
# --------------------------------------------------------------------------------------------


def test_einzelne_sitzung_ist_ein_mal(db):
    nimm(db, zeile(1, dauer=120))
    assert stand(db) == [(1, 1, 0)]


def test_mal_zaehlt_erst_ab_zehn_sekunden_hoerzeit(db):
    nimm(db, zeile(1, dauer=9))
    assert stand(db) == [(1, 0, 0)]  # ein Mal, das nicht zählt
    nimm(db, zeile(2, T0 + 20 * MIN, dauer=10, folge="b.mp3"))
    assert stand(db)[1] == (1, 1, 0)  # genau 10 s zählen


def test_pause_bis_dreissig_minuten_gehoert_zum_selben_mal_und_summiert_die_hoerzeit(db):
    nimm(db, zeile(1, T0, dauer=5), zeile(2, T0 + 5 + 30 * MIN, dauer=5))  # genau 30 Minuten Pause
    # keine der beiden Sitzungen hat allein 10 s, zusammen schon: das Mal zählt, getragen von der ersten Sitzung
    assert stand(db) == [(1, 1, 0), (0, 0, 0)]


def test_pause_ueber_dreissig_minuten_ist_ein_neues_mal(db):
    nimm(db, zeile(1, T0, dauer=100), zeile(2, T0 + 100 + 30 * MIN + 1, dauer=100))
    assert stand(db) == [(1, 1, 0), (1, 1, 0)]


def test_mal_kette_dreier_sitzungen_mit_kurzen_pausen(db):
    nimm(db, zeile(1, T0, dauer=60), zeile(2, T0 + 60 + 25 * MIN, dauer=60), zeile(3, T0 + 120 + 50 * MIN, dauer=60))
    assert stand(db) == [(1, 1, 0), (0, 0, 0), (0, 0, 0)]  # jede Pause unter 30 Minuten: ein Mal


def test_sitzung_am_ende_der_folge_beendet_das_mal_wiederholen_ist_ein_neues_mal(db):
    nimm(db, zeile(1, T0, dauer=100, ende="ende_der_folge"), zeile(2, T0 + 100 + 60, dauer=100))
    assert [(a, c) for a, _b, c in stand(db)] == [(1, 1), (1, 0)]  # beide ein neues Mal (ohne Dauer: 100 s >= 60 s: die erste ist fertig)


def test_mal_ueberlappende_sitzungen_rechnen_gegen_das_spaeteste_ende(db):
    """Zwei Fenster: B liegt in A und endet früh; C beginnt 25 Minuten nach dem Ende von A (aber lange nach dem Ende von B)."""
    nimm(db, zeile(1, T0, dauer=5000), zeile(2, T0 + 10, dauer=20), zeile(3, T0 + 5000 + 1500, dauer=100))
    assert stand(db) == [(1, 1, 0), (0, 0, 0), (0, 0, 0)]


def test_mal_gehoert_zu_verschiedenen_quellen_getrennt(db):
    nimm(db, zeile(1, T0, dauer=100), quelle="box:box1")
    nimm(db, zeile(2, T0 + 200, dauer=100), quelle="box:box2")
    assert stand(db, "box:box1") == [(1, 1, 0)] and stand(db, "box:box2") == [(1, 1, 0)]


def test_mal_gehoert_zu_verschiedenen_folgen_getrennt(db):
    nimm(db, zeile(1, T0, dauer=100), zeile(2, T0 + 200, dauer=100, folge="b.mp3"))
    assert stand(db) == [(1, 1, 0), (1, 1, 0)]


def test_mal_nach_beginn_nicht_nach_eingang(db):
    """Nachlieferung in falscher Reihenfolge: die spätere Sitzung kommt zuerst an, die frühere danach."""
    nimm(db, zeile(2, T0 + 100 + 10 * MIN, dauer=100))
    nimm(db, zeile(1, T0, dauer=100))
    assert stand(db) == [(0, 0, 0), (1, 1, 0)]  # die nachgelieferte frühere Sitzung trägt jetzt das Mal


def test_unbekanntes_datum_jede_sitzung_ein_eigenes_mal(db):
    nimm(db, zeile(1, 0, dauer=100, datum="unbekannt"), zeile(2, 0, dauer=100, datum="unbekannt"), zeile(3, 0, dauer=4, datum="unbekannt"))
    assert stand(db) == [(1, 1, 0), (1, 1, 0), (1, 0, 0)]
    r = db.alle()[0]
    assert (r["tag"], r["stunde"], r["datum"]) == (None, None, "unbekannt")


def test_ungefaehres_datum_zaehlt_normal_mit_tag_und_stunde(db):
    nimm(db, zeile(1, T0, dauer=100, datum="ungefaehr"))
    r = db.alle()[0]
    assert (r["tag"], r["stunde"], r["datum"], r["neues_mal"], r["mal_zaehlt"]) == ("2026-11-10", 11, "ungefaehr", 1, 1)


# --------------------------------------------------------------------------------------------
# fertig
# --------------------------------------------------------------------------------------------


def test_fertig_ab_achtzig_prozent_der_dauer(db):
    nimm(db, zeile(1, T0, dauer=799, ende="ende_der_folge", folge_dauer=1000))
    assert stand(db)[0][2] == 0
    nimm(db, zeile(2, T0 + 5000, dauer=800, ende="ende_der_folge", folge_dauer=1000))
    assert stand(db)[1][2] == 1  # 800 von 1000 genügt (und die Hörzeit der ersten, nicht fertigen Sitzung kommt dazu: 1599)


def test_fertig_hoerbuch_in_portionen_ueber_mehrere_tage(db):
    d = 1000
    nimm(db, zeile(1, T0, dauer=300, ende="pause", folge_dauer=d))
    nimm(db, zeile(2, T0 + 86400, dauer=300, ende="wechsel", folge_dauer=d))
    nimm(db, zeile(3, T0 + 2 * 86400, dauer=250, ende="ende_der_folge", folge_dauer=d))
    assert [x[2] for x in stand(db)] == [0, 0, 1]  # 850 von 1000 über drei Tage: fertig, nur die letzte Sitzung trägt es


def test_fertig_portionen_zu_wenig_hoerzeit_nicht_fertig(db):
    d = 1000
    nimm(db, zeile(1, T0, dauer=300, ende="pause", folge_dauer=d), zeile(2, T0 + 86400, dauer=450, ende="ende_der_folge", folge_dauer=d))
    assert [x[2] for x in stand(db)] == [0, 0]  # 750 < 800


def test_fertig_summe_beginnt_nach_dem_letzten_fertig_neu(db):
    d = 1000
    nimm(db, zeile(1, T0, dauer=900, ende="ende_der_folge", folge_dauer=d))  # fertig
    nimm(db, zeile(2, T0 + 86400, dauer=100, ende="ende_der_folge", folge_dauer=d))  # Wiederholen, nur 100: nicht fertig
    nimm(db, zeile(3, T0 + 2 * 86400, dauer=700, ende="ende_der_folge", folge_dauer=d))  # 100 + 700 = 800: fertig
    assert [x[2] for x in stand(db)] == [1, 0, 1]


def test_fertig_ohne_dauer_ab_sechzig_sekunden(db):
    nimm(db, zeile(1, T0, dauer=59, ende="ende_der_folge"))
    assert stand(db)[0][2] == 0
    nimm(db, zeile(2, T0 + 9000, dauer=1, ende="ende_der_folge"))  # 59 + 1 = 60
    assert stand(db)[1][2] == 1


def test_nur_sitzungen_am_ende_der_folge_sind_fertig(db):
    nimm(db, zeile(1, T0, dauer=5000, ende="pause", folge_dauer=1000))
    assert stand(db)[0][2] == 0


def test_fertig_je_quelle_getrennt(db):
    nimm(db, zeile(1, T0, dauer=500, ende="pause", folge_dauer=1000), quelle="box:box1")
    nimm(db, zeile(2, T0 + 9000, dauer=400, ende="ende_der_folge", folge_dauer=1000), quelle="box:box2")
    assert stand(db, "box:box2")[0][2] == 0  # box1 hat die Hörzeit nicht „vorgehört“


def test_fertig_nachlieferung_rechnet_die_gruppe_neu(db):
    nimm(db, zeile(3, T0 + 2 * 86400, dauer=250, ende="ende_der_folge", folge_dauer=1000))
    assert stand(db) == [(1, 1, 0)]  # allein: nicht fertig
    nimm(db, zeile(1, T0, dauer=300, folge_dauer=1000), zeile(2, T0 + 86400, dauer=300, ende="wechsel", folge_dauer=1000))
    assert [x[2] for x in stand(db)] == [1, 0, 0]  # die Zeile 3 (rowid 1) ist jetzt fertig


def test_fertig_unbekanntes_datum_in_eingangsreihenfolge(db):
    nimm(db, zeile(1, 0, dauer=300, folge_dauer=1000, datum="unbekannt"))
    nimm(db, zeile(2, 0, dauer=300, folge_dauer=1000, datum="unbekannt"))
    nimm(db, zeile(3, 0, dauer=250, ende="ende_der_folge", folge_dauer=1000, datum="unbekannt"))
    assert [x[2] for x in stand(db)] == [0, 0, 1]


def test_fertig_dauer_aus_einer_anderen_zeile_der_gruppe(db):
    nimm(db, zeile(1, T0, dauer=100, folge_dauer=100), zeile(2, T0 + 9000, dauer=90, ende="ende_der_folge"))
    assert stand(db)[1][2] == 1  # die zweite Zeile kennt die Dauer nicht, die Gruppe schon: 190 >= 80


# --------------------------------------------------------------------------------------------
# Zeit: Mitternacht, Sommerzeit, Zeitzone
# --------------------------------------------------------------------------------------------


def test_sitzung_ueber_mitternacht_zaehlt_zum_tag_des_beginns(db):
    beginn = utc(2026, 11, 10, 22, 50)  # 23:50 in Berlin
    nimm(db, zeile(1, beginn, dauer=1200))
    r = db.alle()[0]
    assert (r["tag"], r["stunde"]) == ("2026-11-10", 23)
    assert r["ende_um"] > utc(2026, 11, 10, 23, 0)  # endet nach Mitternacht Ortszeit, zählt trotzdem zum 10.


def test_mal_ueber_mitternacht_gehoert_zum_tag_seines_beginns(db):
    nimm(db, zeile(1, utc(2026, 11, 10, 22, 55), dauer=300), zeile(2, utc(2026, 11, 10, 23, 5), dauer=300))
    a, b = db.alle()
    assert (a["tag"], b["tag"]) == ("2026-11-10", "2026-11-10") or (a["tag"], b["tag"]) == ("2026-11-10", "2026-11-11")
    assert (a["neues_mal"], b["neues_mal"]) == (1, 0)  # ein Mal, getragen von der ersten Sitzung: Tag 10.


@pytest.mark.parametrize(
    ("beginn", "tag", "stunde"),
    [
        (utc(2026, 3, 29, 0, 30), "2026-03-29", 1),  # 01:30 MEZ, vor dem Umstellen (um 01:00 UTC wird 03:00 MESZ)
        (utc(2026, 3, 29, 1, 30), "2026-03-29", 3),  # 03:30 MESZ: die Stunde 2 gibt es an diesem Tag nicht
        (utc(2026, 10, 24, 22, 30), "2026-10-25", 0),  # 00:30 MESZ
        (utc(2026, 10, 25, 0, 30), "2026-10-25", 2),  # 02:30 MESZ (erstes Auftreten der Stunde 2)
        (utc(2026, 10, 25, 1, 30), "2026-10-25", 2),  # 02:30 MEZ (zweites Auftreten)
        (utc(2026, 10, 25, 22, 59), "2026-10-25", 23),
    ],
)
def test_sommerzeit_tag_und_stunde_in_der_zeitzone_von_ha(db, beginn, tag, stunde):
    nimm(db, zeile(1, beginn, dauer=60))
    r = db.alle()[0]
    assert (r["tag"], r["stunde"]) == (tag, stunde)


def test_tag_und_stunde_folgen_der_zeitzone_beim_einfuegen(db):
    nimm(db, zeile(1, utc(2026, 11, 10, 23, 30), dauer=60), zone=UTC_ZONE)
    nimm(db, zeile(2, utc(2026, 11, 10, 23, 30), dauer=60, folge="b.mp3"), zone=BERLIN)
    a, b = db.alle()
    assert (a["tag"], a["stunde"]) == ("2026-11-10", 23)
    assert (b["tag"], b["stunde"]) == ("2026-11-11", 0)  # Wechselt die Zeitzone von HA, bleibt das Raster alter Zeilen


UTC_ZONE = ZoneInfo("UTC")


# --------------------------------------------------------------------------------------------
# Datum der Box (mqtt-v1.md 4.5, Punkt 6)
# --------------------------------------------------------------------------------------------

JETZT = utc(2026, 11, 16, 18, 36, 2)


def test_datum_zeit_ok_nimmt_beginn_der_zeile():
    assert bestimme_datum(True, T0, False, JETZT, 5000, 100) == (T0, "sicher")


def test_datum_gleiche_boot_id_rechnet_vom_empfang_zurueck():
    assert bestimme_datum(False, 12345, True, JETZT, 5000, 4000) == (JETZT - 1000, "sicher")


def test_datum_ungefaehr_nur_nach_dem_1_1_2026_und_vor_dem_empfang():
    assert bestimme_datum(False, T0, False, JETZT, 5000, 4000) == (T0, "ungefaehr")
    assert bestimme_datum(False, utc(2025, 12, 31, 23, 59, 59), False, JETZT, 5000, 4000) == (0, "unbekannt")
    assert bestimme_datum(False, utc(2026, 1, 1), False, JETZT, 5000, 4000)[1] == "unbekannt"  # „nach“ dem 1.1.2026
    assert bestimme_datum(False, JETZT + 1, False, JETZT, 5000, 4000) == (0, "unbekannt")
    assert bestimme_datum(False, JETZT, False, JETZT, 5000, 4000) == (JETZT, "ungefaehr")


def _nachricht(*sitzungen: dict, boot: str = "boot-a", gesendet: int = 51915) -> dict:
    return {"boot_id": boot, "gesendet_boot_s": gesendet, "sitzungen": list(sitzungen)}


def _roh(n: int = 1, **ueber) -> dict:
    s = {
        "sitzung": f"e3a8b1c4-52d7-4f09-b6a1-{n:012d}", "serie": "3f9a1c07b2d4", "folge": "folge-02.mp3", "folge_dauer_s": 1520,
        "beginn": "2026-11-16T18:10:57Z", "zeit_ok": True, "boot_id": "boot-a", "beginn_boot_s": 50400, "ende_boot_s": 51910, "gehoert_s": 1500, "ende": "ende_der_folge",
    }
    s.update(ueber)
    return s


def test_nachricht_beispiel_aus_dem_vertrag():
    zeilen, quittung = verarbeite_box_nachricht(_nachricht(_roh()), JETZT)
    assert quittung == ["e3a8b1c4-52d7-4f09-b6a1-000000000001"]
    z = zeilen[0]
    assert (z.serie, z.folge, z.folge_dauer_s, z.beginn, z.ende_um, z.datum, z.gehoert_s, z.ende) == ("3f9a1c07b2d4", "folge-02.mp3", 1520, utc(2026, 11, 16, 18, 10, 57), utc(2026, 11, 16, 18, 10, 57) + 1510, "sicher", 1500, "ende_der_folge")


def test_nachricht_datum_zeit_nicht_ok_und_boot_id_gleich_oder_anders():
    gleich = verarbeite_box_nachricht(_nachricht(_roh(zeit_ok=False)), JETZT)[0][0]
    assert (gleich.beginn, gleich.datum) == (JETZT - (51915 - 50400), "sicher")
    anders = verarbeite_box_nachricht(_nachricht(_roh(zeit_ok=False, boot_id="boot-alt")), JETZT)[0][0]
    assert (anders.beginn, anders.datum) == (utc(2026, 11, 16, 18, 10, 57), "ungefaehr")
    unbekannt = verarbeite_box_nachricht(_nachricht(_roh(zeit_ok=False, boot_id="boot-alt", beginn="1970-01-01T00:00:10Z")), JETZT)[0][0]
    assert (unbekannt.beginn, unbekannt.datum, unbekannt.ende_um) == (0, "unbekannt", 1510)


def test_gehoert_s_wird_auf_die_schranke_gekappt():
    z = verarbeite_box_nachricht(_nachricht(_roh(gehoert_s=99999)), JETZT)[0][0]
    assert z.gehoert_s == 51910 - 50400 + 2


def test_medieninfo_dauer_geht_vor_der_dauer_der_box():
    z = verarbeite_box_nachricht(_nachricht(_roh()), JETZT, lambda s, f: 1600)[0][0]
    assert z.folge_dauer_s == 1600
    z = verarbeite_box_nachricht(_nachricht(_roh()), JETZT, lambda s, f: None)[0][0]
    assert z.folge_dauer_s == 1520
    z = verarbeite_box_nachricht(_nachricht(_roh(folge_dauer_s=None)), JETZT, lambda s, f: None)[0][0]
    assert z.folge_dauer_s is None


@pytest.mark.parametrize(
    "aenderung",
    [
        {"serie": ""}, {"serie": "x" * 65}, {"folge": ""}, {"folge": "ä" * 128}, {"folge_dauer_s": 0}, {"folge_dauer_s": "5"}, {"beginn": "gestern"}, {"beginn": 5},
        {"zeit_ok": "ja"}, {"boot_id": ""}, {"beginn_boot_s": -1}, {"ende_boot_s": 100}, {"gehoert_s": 0}, {"gehoert_s": 1.5}, {"gehoert_s": True},
        {"ende": "unbekannt"}, {"ende": "verwaist"}, {"grund": "x" * 33}, {"grund": 5},
    ],
)
def test_ungueltige_zeile_wird_nicht_gespeichert_aber_quittiert(aenderung):
    zeilen, quittung = verarbeite_box_nachricht(_nachricht(_roh(1, **aenderung), _roh(2)), JETZT)
    assert [z.sitzung[-1] for z in zeilen] == ["2"]  # die gültige daneben bleibt
    assert len(quittung) == 2  # auch die ungültige wird quittiert


def test_fehlendes_pflichtfeld_ungueltig():
    roh = _roh()
    del roh["beginn_boot_s"]
    assert verarbeite_box_nachricht(_nachricht(roh), JETZT) == ([], [roh["sitzung"]])


def test_ungueltiger_zwischenstand_wird_nicht_quittiert_und_gueltiger_auch_nicht():
    zeilen, quittung = verarbeite_box_nachricht(_nachricht(_roh(1, ende="teilweise"), _roh(2, ende="teilweise", gehoert_s=0)), JETZT)
    assert len(zeilen) == 1 and quittung == []


def test_sitzung_ohne_uuid_wird_nicht_gespeichert_und_nicht_quittiert():
    zeilen, quittung = verarbeite_box_nachricht(_nachricht(_roh(sitzung="keine-uuid"), "text", {"x": 1}), JETZT)
    assert zeilen == [] and quittung == []


def test_kopf_der_nachricht_ungueltig_alle_ungueltig_aber_quittiert():
    zeilen, quittung = verarbeite_box_nachricht({"boot_id": "", "gesendet_boot_s": 5, "sitzungen": [_roh()]}, JETZT)
    assert zeilen == [] and len(quittung) == 1
    assert verarbeite_box_nachricht({"boot_id": "a", "gesendet_boot_s": 5, "sitzungen": "x"}, JETZT) == ([], [])


def test_doppelte_sitzung_in_einer_nachricht_zaehlt_einmal():
    zeilen, quittung = verarbeite_box_nachricht(_nachricht(_roh(1), _roh(1, gehoert_s=5), _roh(2)), JETZT)
    assert [z.gehoert_s for z in zeilen] == [1500, 1500] and len(quittung) == 2


def test_mehr_als_zwanzig_sitzungen_nur_die_ersten_zwanzig():
    zeilen, quittung = verarbeite_box_nachricht(_nachricht(*[_roh(n) for n in range(25)]), JETZT)
    assert len(zeilen) == 20 and len(quittung) == 20


# --------------------------------------------------------------------------------------------
# Ersetzen
# --------------------------------------------------------------------------------------------


def test_doppelzustellung_ergibt_eine_zeile(db):
    z = zeile(1, dauer=100, ende="pause")
    assert nimm(db, z)["gespeichert"] == 1
    assert nimm(db, z) == {"gespeichert": 0, "geaendert": 0, "marke": 0}
    assert len(db.alle()) == 1 and stand(db) == [(1, 1, 0)]


def test_endzeile_ersetzt_zwischenstand(db):
    nimm(db, zeile(1, dauer=100, ende="teilweise"))
    erg = nimm(db, zeile(1, dauer=150, ende="pause"))
    assert erg["geaendert"] == 1
    r = db.alle()[0]
    assert (r["ende"], r["gehoert_s"]) == ("pause", 150)


def test_endzeile_gewinnt_immer_auch_mit_weniger_hoerzeit(db):
    nimm(db, zeile(1, dauer=200, ende="teilweise"))
    nimm(db, zeile(1, dauer=100, ende="ende_der_folge"))
    r = db.alle()[0]
    assert (r["ende"], r["gehoert_s"]) == ("ende_der_folge", 100)


def test_zwischenstand_ersetzt_keine_endzeile(db):
    nimm(db, zeile(1, dauer=100, ende="pause"))
    nimm(db, zeile(1, dauer=500, ende="teilweise"))  # verspätet: gehört zu einer früheren Phase
    r = db.alle()[0]
    assert (r["ende"], r["gehoert_s"]) == ("pause", 100)


def test_endzeile_ersetzt_endzeile_nur_mit_mehr_hoerzeit(db):
    nimm(db, zeile(1, dauer=100, ende="pause"))
    nimm(db, zeile(1, dauer=50, ende="wechsel"))
    assert db.alle()[0]["ende"] == "pause"
    nimm(db, zeile(1, dauer=120, ende="wechsel"))
    assert (db.alle()[0]["ende"], db.alle()[0]["gehoert_s"]) == ("wechsel", 120)


def test_zwischenstand_mit_mehr_hoerzeit_ersetzt_zwischenstand_mit_weniger_nicht_umgekehrt(db):
    nimm(db, zeile(1, dauer=100, ende="teilweise"))
    nimm(db, zeile(1, dauer=200, ende="teilweise"))
    assert db.alle()[0]["gehoert_s"] == 200
    nimm(db, zeile(1, dauer=150, ende="teilweise"))
    assert db.alle()[0]["gehoert_s"] == 200


def test_abbruch_ersetzt_zwischenstand_nur_mit_mehr_hoerzeit_endzeile_ersetzt_abbruch(db):
    nimm(db, zeile(1, dauer=200, ende="teilweise"))
    nimm(db, zeile(1, dauer=180, ende="abbruch"))
    assert db.alle()[0]["ende"] == "teilweise"
    nimm(db, zeile(1, dauer=100, ende="pause"))
    assert db.alle()[0]["ende"] == "pause"


def test_schluessel_ist_quelle_und_sitzung_eine_fremde_box_ueberschreibt_nichts(db):
    nimm(db, zeile(1, dauer=100, ende="pause"), quelle="box:box1")
    nimm(db, zeile(1, dauer=900, ende="ende_der_folge", serie="boese"), quelle="box:box2")
    a, b = db.alle("box:box1")[0], db.alle("box:box2")[0]
    assert (a["serie"], a["gehoert_s"]) == ("rabe", 100)
    assert (b["serie"], b["gehoert_s"]) == ("boese", 900)


def test_neu_rechnen_betrifft_nur_die_gruppe_der_zeile(db, monkeypatch):
    nimm(db, zeile(1, dauer=100), zeile(2, dauer=100, folge="b.mp3"))
    gruppen: list[tuple] = []
    echt = g._neu_rechnen
    monkeypatch.setattr(g, "_neu_rechnen", lambda con, q, s, f: (gruppen.append((q, s, f)), echt(con, q, s, f))[1])
    nimm(db, zeile(3, T0 + 5000, dauer=100))
    assert gruppen == [(Q, "rabe", "a.mp3")]


def test_neu_rechnen_aendert_unbeteiligte_gruppen_nicht(db):
    nimm(db, zeile(1, dauer=100, folge="b.mp3"))
    con = sqlite3.connect(db.pfad)
    con.execute("UPDATE sitzungen SET neues_mal=0, mal_zaehlt=0")  # absichtlich „falsch“: nur eine Neuberechnung der Gruppe würde es ändern
    con.commit()
    con.close()
    nimm(db, zeile(2, dauer=100, folge="a.mp3"))
    a, b = db.alle()
    assert (b["neues_mal"], b["mal_zaehlt"]) == (1, 1)
    assert (a["neues_mal"], a["mal_zaehlt"]) == (0, 0)


# --------------------------------------------------------------------------------------------
# verwaist
# --------------------------------------------------------------------------------------------


def test_box_zwischenstand_wird_nach_24_stunden_verwaist(db):
    nimm(db, zeile(1, T0, dauer=100, ende="teilweise"))
    assert db.raeume_auf(T0 + 100 + 86400 - 1) == 0
    assert db.raeume_auf(T0 + 100 + 86400 + 1) == 1
    r = db.alle()[0]
    assert (r["ende"], r["ende_um"], r["gehoert_s"]) == ("verwaist", T0 + 100, 100)  # übernimmt ende_um des letzten Zwischenstands


def test_reinhoeren_zwischenstand_wird_nach_30_minuten_verwaist(db):
    nimm(db, zeile(1, T0, dauer=100, ende="teilweise"), quelle="benutzer:abc")
    assert db.raeume_auf(T0 + 100 + 1800 - 1) == 0
    assert db.raeume_auf(T0 + 100 + 1800 + 1) == 1
    assert db.alle()[0]["ende"] == "verwaist"


def test_box_zwischenstand_nach_30_minuten_ist_noch_nicht_verwaist(db):
    nimm(db, zeile(1, T0, dauer=100, ende="teilweise"))
    assert db.raeume_auf(T0 + 100 + 3 * 3600) == 0


def test_zwischenstand_mit_unbekanntem_datum_wird_gleich_verwaist_ende_ueberschreibt_es(db):
    nimm(db, zeile(1, 0, dauer=100, ende="teilweise", datum="unbekannt"))
    assert db.raeume_auf(T0) == 1
    nimm(db, zeile(1, 0, dauer=120, ende="pause", datum="unbekannt"))
    assert (db.alle()[0]["ende"], db.alle()[0]["gehoert_s"]) == ("pause", 120)


def test_endzeile_ueberschreibt_verwaist_und_endzeilen_werden_nie_verwaist(db):
    nimm(db, zeile(1, T0, dauer=100, ende="teilweise"), zeile(2, T0 + 9999, dauer=50, ende="pause"))
    db.raeume_auf(T0 + 10 * 86400)
    assert [r["ende"] for r in db.alle()] == ["verwaist", "pause"]
    nimm(db, zeile(1, T0, dauer=100, ende="ende_der_folge"))
    assert db.alle()[0]["ende"] == "ende_der_folge"


def test_verspaeteter_zwischenstand_ersetzt_verwaist_nur_mit_mehr_hoerzeit(db):
    nimm(db, zeile(1, T0, dauer=100, ende="teilweise"))
    db.raeume_auf(T0 + 10 * 86400)
    nimm(db, zeile(1, T0, dauer=100, ende="teilweise"))
    assert db.alle()[0]["ende"] == "verwaist"


# --------------------------------------------------------------------------------------------
# Löschmarke
# --------------------------------------------------------------------------------------------


def test_loeschen_entfernt_zeilen_der_quelle_und_setzt_die_marke(db):
    nimm(db, zeile(1), quelle="box:box1")
    nimm(db, zeile(2), quelle="box:box2")
    assert db.loesche(["box:box1"], T0 + 1000) == 1
    assert len(db.alle("box:box1")) == 0 and len(db.alle("box:box2")) == 1
    assert db.marken() == {"box:box1": T0 + 1000}


def test_nachgelieferte_zeile_vor_der_loeschung_wird_verworfen_danach_gilt_sie(db):
    db.loesche([Q], T0 + 1000)
    erg = nimm(db, zeile(1, T0, dauer=100), zeile(2, T0 + 2000, dauer=100), zeile(3, T0 + 900, dauer=100))  # ende_um 1000 ist nicht „vor“ der Löschung
    assert erg == {"gespeichert": 2, "geaendert": 0, "marke": 1}
    assert sorted(r["sitzung"][-1] for r in db.alle()) == ["2", "3"]


def test_loeschmarke_gilt_nur_fuer_die_quelle_und_unbekanntes_datum_wird_verworfen(db):
    db.loesche([Q], T0 + 1000)
    assert nimm(db, zeile(1, T0, dauer=100), quelle="box:box2")["gespeichert"] == 1
    assert nimm(db, zeile(2, 0, dauer=100, datum="unbekannt"))["marke"] == 1


def test_erneutes_loeschen_hebt_die_marke_an(db):
    db.loesche([Q], 100)
    db.loesche([Q], 500)
    assert db.marken()[Q] == 500


# --------------------------------------------------------------------------------------------
# Umschreiben (Verschieben und Zusammenführen)
# --------------------------------------------------------------------------------------------


def test_schreibe_um_aendert_serie_und_folge_und_rechnet_die_zielgruppe_neu(db):
    nimm(db, zeile(1, T0, dauer=100, serie="s1", folge="a.mp3", ende="pause"), zeile(2, T0 + 200, dauer=100, serie="s2", folge="neu.mp3"))
    assert db.schreibe_um({("s1", "a.mp3"): ("s2", "neu.mp3")}) == 1
    a, b = db.alle()
    assert (a["serie"], a["folge"]) == ("s2", "neu.mp3")
    assert (a["neues_mal"], b["neues_mal"]) == (1, 0)  # beide jetzt in einer Gruppe, Pause 100 s: ein Mal


def test_schreibe_um_ohne_treffer_aendert_nichts(db):
    nimm(db, zeile(1))
    assert db.schreibe_um({("x", "y"): ("z", "w")}) == 0
    assert db.schreibe_um({}) == 0


def test_schreibe_um_rechnet_alle_quellen_der_umgeschriebenen_folge(db):
    nimm(db, zeile(1, serie="s1", folge="a.mp3"), quelle="box:box1")
    nimm(db, zeile(2, T0 + 5, serie="s1", folge="a.mp3"), quelle="benutzer:u")
    db.schreibe_um({("s1", "a.mp3"): ("s2", "b.mp3")})
    assert all(r["serie"] == "s2" for r in db.alle())


# --------------------------------------------------------------------------------------------
# Technik
# --------------------------------------------------------------------------------------------


def test_technik_zeilen(db):
    db.technik_schreibe("box1", [(T0, "lader_an", None), (T0 + 5, "fehler", "kopfhoerer_unlesbar")])
    zeilen = db.technik_alle("box1")
    assert [(z["art"], z["wert"], z["zeit"]) for z in zeilen] == [("lader_an", None, T0), ("fehler", "kopfhoerer_unlesbar", T0 + 5)]
