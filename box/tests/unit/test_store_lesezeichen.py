"""Entscheidung N (09.11.): ``benutzt_am`` in ``resume.json`` und ``lesezeichen_tage`` in ``config.json``.

Beides ist additiv: ``schema_version`` bleibt 2, alte Dateien laden unverändert, ein Zeiger ohne Zeitstempel
läuft nie ab, ein Konfigurationsfeld, das fehlt, heißt 14 Tage.
"""

from __future__ import annotations

import copy
import json

import pytest
from conftest import zeiger_speichern

from tobibox import pointer, store
from tobibox.store import KonfigStore, ResumeStore, Ungueltig, schreibe_atomar

W = 1_700_000_000.0
W_ISO = "2023-11-14T22:13:20Z"

KONFIG = {
    "schema_version": 2,
    "revision": 3,
    "liste_id": "a3f9c1e07b2d4856",
    "zuordnungen": {"e0040312345678ab": {"ziel": {"typ": "serie", "serie": "3f9a1c07b2d4"}}},
    "leise_zeiten": {"zeitzone": "Europe/Berlin", "fenster": []},
    "gute_nacht": {"timer_min": 30, "ausblenden_s": 60},
}


# --- resume.json: Zeitstempel ------------------------------------------------------------------


def test_zeitstempel_wird_als_iso_utc_geschrieben_und_gelesen(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    assert s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause", wall=W + 0.7), 0)
    assert s.speichern(zeiger_speichern("s1", "b.mp3", None, 5.0, "pause", art="folge", wall=W), 1)
    roh = json.loads((tmp_path / "resume.json").read_text())
    assert roh["schema_version"] == 2
    assert roh["serien"]["s1"]["benutzt_am"] == W_ISO  # auf die Sekunde abgerundet
    assert roh["folgen"]["s1"]["b.mp3"]["benutzt_am"] == W_ISO
    geladen = ResumeStore(tmp_path).laden()
    assert {(z.art, z.datei): z.benutzt_wall for z in geladen.zeiger} == {("serie", "a.mp3"): W, ("folge", "b.mp3"): W}


def test_ohne_wanduhr_wird_kein_zeitstempel_geschrieben(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause"), 0)
    roh = json.loads((tmp_path / "resume.json").read_text())
    assert "benutzt_am" not in roh["serien"]["s1"]


def test_alte_datei_ohne_zeitstempel_laedt_mit_none(tmp_path):
    alt = {
        "schema_version": 2,
        "serien": {"s1": {"folge": "a.mp3", "index": 0, "track": 0, "position_s": 5.0, "zaehler": 4}},
        "folgen": {"s1": {"b.mp3": {"track": 0, "position_s": 1.0, "zaehler": 2}}},
    }
    schreibe_atomar(tmp_path / "resume.json", alt)
    geladen = ResumeStore(tmp_path).laden()
    assert [z.benutzt_wall for z in geladen.zeiger] == [None, None]


def test_alter_stempel_bleibt_beim_speichern_ohne_wanduhr(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause", wall=W), 0)
    s.speichern(zeiger_speichern("s1", "a.mp3", 0, 20.0, "pause", wall=None), 1)  # Uhr unsicher
    assert s.zeiger[("serie", "s1", "")].benutzt_wall == W
    assert json.loads((tmp_path / "resume.json").read_text())["serien"]["s1"]["benutzt_am"] == W_ISO


def test_unveraenderter_zeiger_stempel_wird_erst_nach_einer_stunde_erneuert(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    assert s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause", wall=W), 0)
    assert not s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause", wall=W + 60), 1)
    assert not s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause", wall=W + pointer.STEMPEL_ERNEUERN_S - 1), 2)
    assert s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause", wall=W + pointer.STEMPEL_ERNEUERN_S), 3)
    assert s.zeiger[("serie", "s1", "")].benutzt_wall == W + pointer.STEMPEL_ERNEUERN_S
    assert s.schreibungen == 2


def test_unveraenderter_zeiger_ohne_stempel_bekommt_einen_aber_nur_bei_sicherer_uhr(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    assert s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause"), 0)
    assert not s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause", wall=None), 1)
    assert s.speichern(zeiger_speichern("s1", "a.mp3", 0, 12.0, "pause", wall=W), 2)
    assert s.zeiger[("serie", "s1", "")].benutzt_wall == W


@pytest.mark.parametrize("wert", ["gestern", 1700000000, "2023-11-14 22:13:20", "2023-13-40T00:00:00Z", "2023-11-14T22:13:20+01:00", True])
def test_ungueltiger_zeitstempel_macht_die_datei_ungueltig(wert):
    roh = {
        "schema_version": 2,
        "serien": {"s1": {"folge": "a.mp3", "index": 0, "track": 0, "position_s": 5.0, "zaehler": 4, "benutzt_am": wert}},
        "folgen": {},
    }
    with pytest.raises(Ungueltig) as e:
        store.parse_resume(roh)
    assert e.value.grund == "schema_ungueltig"
    roh = {"schema_version": 2, "serien": {}, "folgen": {"s1": {"b.mp3": {"track": 0, "position_s": 1.0, "zaehler": 2, "benutzt_am": wert}}}}
    with pytest.raises(Ungueltig):
        store.parse_resume(roh)


def test_zeitstempel_null_gilt_als_fehlend():
    roh = {"schema_version": 2, "serien": {"s1": {"folge": "a", "index": 0, "track": 0, "position_s": 5.0, "zaehler": 1, "benutzt_am": None}}, "folgen": {}}
    assert store.parse_resume(roh)[("serie", "s1", "")].benutzt_wall is None


def test_iso_rundreise():
    assert store.wall_zu_iso(W) == W_ISO
    assert store.iso_zu_wall(W_ISO) == W


# --- config.json: lesezeichen_tage ---------------------------------------------------------------------


def test_fehlendes_feld_heisst_14_tage():
    k, roh = store.validiere_konfig(KONFIG)
    assert k.lesezeichen_tage == 14
    assert "lesezeichen_tage" not in roh  # nichts dazuerfinden: die Datei bleibt, wie HA sie schickte


@pytest.mark.parametrize("wert", [0, 1, 14, 30, 365])
def test_gueltige_werte(wert):
    k, roh = store.validiere_konfig({**KONFIG, "lesezeichen_tage": wert})
    assert k.lesezeichen_tage == wert and roh["lesezeichen_tage"] == wert


@pytest.mark.parametrize("wert", [-1, 366, 7.5, "14", None, True, False, [14]])
def test_ungueltige_werte_lehnen_die_ganze_liste_ab(wert):
    with pytest.raises(Ungueltig) as e:
        store.validiere_konfig({**KONFIG, "lesezeichen_tage": wert})
    assert e.value.grund == "schema_ungueltig" and "lesezeichen_tage" in str(e.value)


def test_liste_der_version_1_ohne_feld_gilt_14():
    v1 = copy.deepcopy(KONFIG)
    v1["schema_version"] = 1
    v1["zuordnungen"] = {"e0040312345678ab": {"typ": "serie", "serie": "3f9a1c07b2d4"}}
    k, _ = store.validiere_konfig(v1)
    assert k.lesezeichen_tage == 14


def test_json_rundreise_und_vorgabe_der_leeren_konfig():
    assert store.leere_konfig().lesezeichen_tage == 14
    k, _ = store.validiere_konfig({**KONFIG, "lesezeichen_tage": 0})
    assert store.konfig_zu_json(k)["lesezeichen_tage"] == 0
    assert store.parse_konfig(store.konfig_zu_json(k)) == k


def test_annehmen_behaelt_das_feld_in_der_datei(tmp_path):
    ks = KonfigStore(tmp_path)
    ks.laden()
    assert ks.annehmen({**KONFIG, "lesezeichen_tage": 7}).angenommen
    assert json.loads((tmp_path / "config.json").read_text())["lesezeichen_tage"] == 7
    neu = KonfigStore(tmp_path)
    assert neu.laden().konfig.lesezeichen_tage == 7


def test_ungueltiges_feld_laesst_die_bisherige_konfiguration(tmp_path):
    ks = KonfigStore(tmp_path)
    ks.laden()
    assert ks.annehmen({**KONFIG, "lesezeichen_tage": 7}).angenommen
    a = ks.annehmen({**KONFIG, "revision": 4, "lesezeichen_tage": -3})
    assert (a.angenommen, a.grund) == (False, "schema_ungueltig")
    assert ks.konfig.lesezeichen_tage == 7 and ks.konfig.revision == 3


def test_aenderung_nur_am_feld_mit_hoeherer_revision_wird_angenommen(tmp_path):
    ks = KonfigStore(tmp_path)
    ks.laden()
    ks.annehmen({**KONFIG, "lesezeichen_tage": 14})
    assert ks.annehmen({**KONFIG, "revision": 4, "lesezeichen_tage": 0}).angenommen
    assert ks.konfig.lesezeichen_tage == 0
