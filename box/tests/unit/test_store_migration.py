"""Schema-Version 2 von ``resume.json`` und ``config.json`` (Entscheidung F, 05.11.): Migration
im Speicher aus Version 1, Lesen und Schreiben von Version 2, neuere Version abgelehnt."""

from __future__ import annotations

import copy
import json
import logging

import pytest
from conftest import zeiger_speichern

from tobibox import events as ev
from tobibox import pointer, store
from tobibox.store import KonfigStore, ResumeStore, lade_zustandsdatei, schreibe_atomar


@pytest.fixture
def protokoll():
    zeilen: list[logging.LogRecord] = []

    class H(logging.Handler):
        def emit(self, record):
            zeilen.append(record)

    log = logging.getLogger("tobibox")
    alt, level = log.handlers[:], log.level
    log.handlers = [H()]
    log.setLevel(logging.DEBUG)
    yield zeilen
    log.handlers = alt
    log.setLevel(level)


RESUME_V1 = {
    "schema_version": 1,
    "serien": {
        "3f9a1c07b2d4": {"folge": "folge-02.mp3", "index": 1, "position_s": 412.5, "zaehler": 37},
        "8c21d5e9a0b7": {"folge": "c.mp3", "index": 2, "position_s": 0.0, "zaehler": 3},
    },
}

KONFIG_V1 = {
    "schema_version": 1,
    "revision": 17,
    "liste_id": "a3f9c1e07b2d4856",
    "erzeugt_am": "2026-11-05T09:30:00Z",
    "zuordnungen": {
        "e0040312345678ab": {"typ": "serie", "serie": "3f9a1c07b2d4"},
        "04ffeedd": {"typ": "aktion", "aktion": "status"},
    },
    "leise_zeiten": {"zeitzone": "Europe/Berlin", "fenster": []},
    "gute_nacht": {"timer_min": 30, "ausblenden_s": 60},
    "ton_pegel": 40,
}

KONFIG_V2 = {
    **{k: v for k, v in KONFIG_V1.items() if k != "zuordnungen"},
    "schema_version": 2,
    "zuordnungen": {
        "e0040312345678ab": {"ziel": {"typ": "serie", "serie": "3f9a1c07b2d4"}},
        "04a1b2c3": {"ziel": {"typ": "folge", "serie": "8c21d5e9a0b7", "folge": "CD Schatzinsel"}},
        "04ffeedd": {"ziel": {"typ": "aktion", "aktion": "status"}},
    },
}


# --- resume.json ----------------------------------------------------------------


def test_resume_v1_wird_im_speicher_zu_v2_alle_eintraege_track_0_keine_folgen_zeiger():
    neu = store.migriere_resume_v1_nach_v2(RESUME_V1)
    assert neu["schema_version"] == 2
    assert neu["folgen"] == {}
    assert {sid: e["track"] for sid, e in neu["serien"].items()} == {"3f9a1c07b2d4": 0, "8c21d5e9a0b7": 0}
    assert neu["serien"]["3f9a1c07b2d4"]["position_s"] == 412.5  # Position bleibt
    assert RESUME_V1["serien"]["3f9a1c07b2d4"].get("track") is None  # rein: Eingabe unverändert


def test_resume_migration_ist_rein_und_idempotent_auf_v2_ergebnis():
    eingabe = copy.deepcopy(RESUME_V1)
    a = store.migriere_resume_v1_nach_v2(eingabe)
    assert eingabe == RESUME_V1
    assert store.migriere_resume_v1_nach_v2(eingabe) == a


def test_resume_v1_datei_wird_gelesen_und_beim_naechsten_speichern_als_v2_geschrieben(tmp_path):
    schreibe_atomar(tmp_path / "resume.json", RESUME_V1)
    s = ResumeStore(tmp_path)
    geladen = s.laden()
    assert s.quelle == "datei"
    assert {z.serie_id: (z.art, z.datei, z.index, z.track, z.position_s, z.zaehler) for z in geladen.zeiger} == {
        "3f9a1c07b2d4": ("serie", "folge-02.mp3", 1, 0, 412.5, 37),
        "8c21d5e9a0b7": ("serie", "c.mp3", 2, 0, 0.0, 3),
    }
    assert json.loads((tmp_path / "resume.json").read_text())["schema_version"] == 1  # noch nichts geschrieben
    assert s.speichern(zeiger_speichern("3f9a1c07b2d4", "folge-02.mp3", 1, 420.0, "pause"), 0)
    roh = json.loads((tmp_path / "resume.json").read_text())
    assert roh["schema_version"] == 2 and roh["folgen"] == {}
    assert roh["serien"]["3f9a1c07b2d4"] == {"folge": "folge-02.mp3", "index": 1, "track": 0, "position_s": 420.0, "zaehler": 38}
    assert roh["serien"]["8c21d5e9a0b7"]["track"] == 0


def test_resume_v2_mit_track_und_folgen_zeiger_rundreise(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    assert s.speichern(zeiger_speichern("cd", "rip", 1, 95.55, "pause", track=2), 0)
    assert s.speichern(zeiger_speichern("cd", "rip", None, 12.0, "pause", track=1, art="folge"), 1)
    assert s.speichern(zeiger_speichern("cd", "z.mp3", None, 0.0, "folgenende", art="folge"), 2)
    roh = json.loads((tmp_path / "resume.json").read_text())
    assert roh["serien"]["cd"] == {"folge": "rip", "index": 1, "track": 2, "position_s": 95.5, "zaehler": 1}
    assert roh["folgen"]["cd"] == {
        "rip": {"track": 1, "position_s": 12.0, "zaehler": 1},
        "z.mp3": {"track": 0, "position_s": 0.0, "zaehler": 1},
    }
    neu = ResumeStore(tmp_path).laden()
    arten = {(z.art, z.datei): (z.index, z.track, z.position_s) for z in neu.zeiger}
    assert arten == {("serie", "rip"): (1, 2, 95.5), ("folge", "rip"): (None, 1, 12.0), ("folge", "z.mp3"): (None, 0, 0.0)}


def test_serien_zeiger_und_folgen_zeiger_derselben_folge_sind_getrennt(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    s.speichern(zeiger_speichern("cd", "rip", 1, 5.0, "pause"), 0)
    s.speichern(zeiger_speichern("cd", "rip", None, 50.0, "pause", art="folge"), 1)
    assert s.zeiger[pointer.schluessel("serie", "cd", "")].position_s == 5.0
    assert s.zeiger[pointer.schluessel("folge", "cd", "rip")].position_s == 50.0


def test_speichern_schreibt_nicht_bei_gleichem_track_und_gleicher_position(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    assert s.speichern(zeiger_speichern("cd", "rip", 1, 5.0, "pause", track=1), 0)
    assert not s.speichern(zeiger_speichern("cd", "rip", 1, 5.04, "periodisch", track=1), 1)
    assert s.speichern(zeiger_speichern("cd", "rip", 1, 5.0, "trackwechsel", track=2), 2)  # anderer Track


def test_resume_neuere_version_wird_abgelehnt(tmp_path, protokoll):
    (tmp_path / "resume.json").write_text(json.dumps({"schema_version": 3, "serien": {}, "folgen": {}}))
    wert, quelle = lade_zustandsdatei(tmp_path / "resume.json", store.parse_resume, dict)
    assert (wert, quelle) == ({}, "standard")
    assert "schema_zu_neu" in [z.ereignis for z in protokoll]


@pytest.mark.parametrize(
    "aenderung",
    [
        lambda d: d.pop("folgen"),
        lambda d: d.update(folgen=[]),
        lambda d: d["folgen"].update(cd={"rip": {"track": -1, "position_s": 0, "zaehler": 1}}),
        lambda d: d["folgen"].update(cd={"rip": {"track": 0, "position_s": -1, "zaehler": 1}}),
        lambda d: d["folgen"].update(cd={"rip": {"track": 0, "position_s": 0, "zaehler": 0}}),
        lambda d: d["folgen"].update(cd={"a/b": {"track": 0, "position_s": 0, "zaehler": 1}}),
        lambda d: d["serien"]["s"].pop("track"),
        lambda d: d["serien"]["s"].update(track=True),
    ],
)
def test_resume_v2_ungueltig(aenderung):
    d = {"schema_version": 2, "serien": {"s": {"folge": "a", "index": 0, "track": 0, "position_s": 1.0, "zaehler": 1}}, "folgen": {}}
    aenderung(d)
    with pytest.raises(store.Ungueltig):
        store.parse_resume(d)


# --- config.json ----------------------------------------------------------------


def test_konfig_v1_wird_zu_ziel_migriert():
    neu = store.migriere_konfig_v1_nach_v2(KONFIG_V1)
    assert neu["schema_version"] == 2
    assert neu["zuordnungen"] == {
        "e0040312345678ab": {"ziel": {"typ": "serie", "serie": "3f9a1c07b2d4"}},
        "04ffeedd": {"ziel": {"typ": "aktion", "aktion": "status"}},
    }
    assert neu["ton_pegel"] == 40 and neu["revision"] == 17
    assert KONFIG_V1["zuordnungen"]["04ffeedd"] == {"typ": "aktion", "aktion": "status"}  # rein


def test_validiere_konfig_migriert_v1_dann_prueft_und_behaelt_felder():
    k, roh = store.validiere_konfig(KONFIG_V1)
    assert k.zuordnungen["e0040312345678ab"] == ev.Zuordnung("serie", "3f9a1c07b2d4")
    assert k.zuordnungen["04ffeedd"] == ev.Zuordnung("aktion", aktion="status")
    assert roh["schema_version"] == 2 and roh["zuordnungen"]["04ffeedd"] == {"ziel": {"typ": "aktion", "aktion": "status"}}
    assert roh["ton_pegel"] == 40


def test_validiere_konfig_v2_mit_folgen_tobie():
    k, roh = store.validiere_konfig(KONFIG_V2)
    assert k.zuordnungen["04a1b2c3"] == ev.Zuordnung("folge", "8c21d5e9a0b7", "CD Schatzinsel")
    assert store.konfig_zu_json(k)["zuordnungen"] == KONFIG_V2["zuordnungen"]
    assert store.konfig_zu_json(k)["schema_version"] == 2


def test_ziel_wird_nach_der_migration_geprueft_ein_folgen_eintrag_in_v1_faellt_durch():
    d = copy.deepcopy(KONFIG_V1)
    d["zuordnungen"]["04a1b2c3"] = {"typ": "folge", "serie": "s", "folge": "x.mp3"}  # gibt es in v1 nicht
    with pytest.raises(store.Ungueltig):
        store.validiere_konfig(d)


@pytest.mark.parametrize(
    "ziel",
    [
        {"typ": "folge", "serie": "s"},  # folge ohne Name
        {"typ": "folge", "folge": "x.mp3"},  # folge ohne serie
        {"typ": "folge", "serie": "s", "folge": ""},
        {"typ": "folge", "serie": "s", "folge": "a/b.mp3"},
        {"typ": "folge", "serie": "s", "folge": ".."},
        {"typ": "playlist", "serie": "s"},
        {"typ": "aktion", "aktion": "kaffee"},
        {"typ": "serie"},
        "serie",
    ],
)
def test_konfig_v2_ungueltige_ziele(ziel):
    d = copy.deepcopy(KONFIG_V2)
    d["zuordnungen"]["04a1b2c3"] = {"ziel": ziel}
    with pytest.raises(store.Ungueltig):
        store.validiere_konfig(d)


def test_konfig_v2_eintrag_ohne_ziel_ist_ungueltig():
    d = copy.deepcopy(KONFIG_V2)
    d["zuordnungen"]["04a1b2c3"] = {"typ": "serie", "serie": "s"}  # v1-Form in einer v2-Liste
    with pytest.raises(store.Ungueltig):
        store.validiere_konfig(d)


def test_konfig_neuere_version_wird_abgelehnt():
    d = {**KONFIG_V2, "schema_version": 3}
    with pytest.raises(store.Ungueltig) as e:
        store.validiere_konfig(d)
    assert e.value.grund == "schema_zu_neu"


def test_konfig_v1_datei_wird_gelesen_und_nicht_eigenmaechtig_umgeschrieben(tmp_path):
    schreibe_atomar(tmp_path / "config.json", KONFIG_V1)
    ks = KonfigStore(tmp_path)
    e = ks.laden()
    assert ks.quelle == "datei"
    assert e.konfig.zuordnungen["04ffeedd"] == ev.Zuordnung("aktion", aktion="status")
    assert json.loads((tmp_path / "config.json").read_text())["schema_version"] == 1


def test_mqtt_liste_v1_wird_angenommen_im_speicher_migriert_und_als_v2_gespeichert(tmp_path):
    ks = KonfigStore(tmp_path)
    ks.laden()
    a = ks.annehmen(KONFIG_V1)
    assert a.angenommen and a.grund == "ok"
    roh = json.loads((tmp_path / "config.json").read_text())
    assert roh["schema_version"] == 2
    assert roh["zuordnungen"]["e0040312345678ab"] == {"ziel": {"typ": "serie", "serie": "3f9a1c07b2d4"}}
    assert roh["ton_pegel"] == 40


def test_mqtt_liste_v2_mit_folgen_tobie_wird_angenommen_und_neu_geladen(tmp_path):
    ks = KonfigStore(tmp_path)
    ks.laden()
    assert ks.annehmen(KONFIG_V2).angenommen
    neu = KonfigStore(tmp_path).laden().konfig
    assert neu.zuordnungen["04a1b2c3"] == ev.Zuordnung("folge", "8c21d5e9a0b7", "CD Schatzinsel")


def test_mqtt_liste_neuere_version_wird_mit_schema_zu_neu_abgelehnt(tmp_path):
    ks = KonfigStore(tmp_path)
    ks.laden()
    a = ks.annehmen({**KONFIG_V2, "schema_version": 3})
    assert not a.angenommen and a.grund == "schema_zu_neu"
    assert not (tmp_path / "config.json").exists()


def test_mqtt_liste_ungueltiges_ziel_nach_migration_bleibt_bei_alter_konfiguration(tmp_path):
    ks = KonfigStore(tmp_path)
    ks.laden()
    assert ks.annehmen(KONFIG_V2).angenommen
    kaputt = {**KONFIG_V2, "revision": 18, "zuordnungen": {"04a1b2c3": {"ziel": {"typ": "folge", "serie": "s"}}}}
    a = ks.annehmen(kaputt)
    assert not a.angenommen and a.grund == "schema_ungueltig"
    assert ks.konfig.revision == 17
