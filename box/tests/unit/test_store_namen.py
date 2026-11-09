"""Tobie-Namen (Entscheidung M7) und Zusatzfelder in ``config.json``: nichts geht verloren (AP 3.7).

Fehler vorher: ``store.konfig_zu_json`` schrieb das Feld ``name`` je Zuordnung nicht. Geprüft wird jeder Weg, auf dem die
Box ``config.json`` schreibt: ``konfig_zu_json`` selbst, die Übernahme einer Liste aus MQTT (``KonfigStore.annehmen``),
``sim card`` und der HA-Ersatz (beide über ``schreibe_zuordnung``). Dazu bleibt ``lesezeichen_tage`` erhalten.
"""

from __future__ import annotations

import copy
import json

import pytest
from fixtures.ha_fake import konfig_json

from tobibox import events as ev
from tobibox import store
from tobibox.clock import SimUhr
from tobibox.ha_ersatz import HaErsatz, schreibe_zuordnung
from tobibox.sim import Sim

UID_A = "e0040312345678ab"
UID_B = "04a1b2c3"
UID_C = "04ffeedd"
NEU = "04aa00bb"


def liste(revision: int = 5, **zusatz) -> dict:
    """Eine Liste von HA mit Namen, einem unbekannten Zusatzfeld je Zuordnung und ``lesezeichen_tage``."""
    roh = konfig_json(revision=revision)
    roh["zuordnungen"][UID_A]["name"] = "Rabe aus Holz"
    roh["zuordnungen"][UID_A]["farbe"] = "rot"  # unbekanntes Feld einer neueren HA-Fassung
    roh["zuordnungen"][UID_B]["name"] = "Die Drei ??? – Folge 3"
    roh["zuordnungen"][UID_C]["name"] = "Status-Karte"
    roh["lesezeichen_tage"] = 30
    roh.update(zusatz)
    return roh


def lies(pfad) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8"))


@pytest.fixture
def ks(tmp_path):
    k = store.KonfigStore(tmp_path)
    k.laden()
    return k


# -- konfig_zu_json: der gemeldete Fehler -------------------------------------------------------------------


def test_konfig_zu_json_schreibt_den_namen_je_zuordnung():
    k = store.parse_konfig(liste())
    j = store.konfig_zu_json(k)
    assert j["zuordnungen"][UID_A]["name"] == "Rabe aus Holz"
    assert j["zuordnungen"][UID_B]["name"] == "Die Drei ??? – Folge 3"
    assert j["zuordnungen"][UID_C]["name"] == "Status-Karte"
    assert j["lesezeichen_tage"] == 30


def test_ohne_namen_schreibt_konfig_zu_json_kein_name_feld():
    j = store.konfig_zu_json(store.parse_konfig(konfig_json()))
    assert all("name" not in z for z in j["zuordnungen"].values())


def test_rundlauf_parse_schreiben_parse_behaelt_namen():
    k = store.parse_konfig(liste())
    k2 = store.parse_konfig(store.konfig_zu_json(k))
    assert k2 == k
    assert {u: z.name for u, z in k2.zuordnungen.items()} == {
        UID_A: "Rabe aus Holz", UID_B: "Die Drei ??? – Folge 3", UID_C: "Status-Karte",
    }


def test_der_name_ist_keine_andere_zuordnung():
    """Ein anderer Name darf die Wiedergabe nie wechseln: er zählt nicht zum Vergleich (und nicht zum Hash)."""
    a = ev.Zuordnung("serie", "s1", name="Rabe")
    b = ev.Zuordnung("serie", "s1", name="Fuchs")
    assert a == b == ev.Zuordnung("serie", "s1") and hash(a) == hash(b)
    assert ev.Zuordnung("serie", "s1") != ev.Zuordnung("serie", "s2", name="Rabe")


@pytest.mark.parametrize(
    "name",
    ["", " ", "  Rabe", "Rabe ", "x" * 61, "Zeile\neins", "Tab\tulator", "Nullbyte\x00", 7, None, ["Rabe"], {"a": 1}],
)
def test_ungueltiger_name_macht_die_liste_nie_ungueltig_die_box_ignoriert_ihn(name):
    roh = konfig_json()
    roh["zuordnungen"][UID_A]["name"] = name
    k = store.parse_konfig(roh)
    assert k.zuordnungen[UID_A].name is None
    assert store.validiere_konfig(roh)[0].zuordnungen[UID_A].typ == "serie"


def test_name_mit_60_zeichen_und_umlauten_ist_gueltig():
    roh = konfig_json()
    roh["zuordnungen"][UID_A]["name"] = "ä" * 60
    assert store.parse_konfig(roh).zuordnungen[UID_A].name == "ä" * 60


# -- Übernahme einer Liste aus MQTT --------------------------------------------------------------------------


def test_annehmen_laesst_namen_zusatzfelder_und_lesezeichen_tage_unveraendert(ks):
    roh = liste()
    a = ks.annehmen(copy.deepcopy(roh))
    assert a.angenommen
    auf_platte = lies(ks.pfad)
    assert auf_platte["zuordnungen"] == roh["zuordnungen"]  # Namen und ``farbe`` unverändert
    assert auf_platte["lesezeichen_tage"] == 30
    assert ks.konfig.lesezeichen_tage == 30 and ks.konfig.zuordnungen[UID_A].name == "Rabe aus Holz"


def test_nach_dem_neustart_sind_namen_und_zusatzfelder_noch_da(ks, tmp_path):
    ks.annehmen(liste())
    neu = store.KonfigStore(tmp_path)
    neu.laden()
    assert neu.konfig.zuordnungen[UID_B].name == "Die Drei ??? – Folge 3"
    assert neu.roh["zuordnungen"][UID_A]["farbe"] == "rot"
    assert neu.konfig.lesezeichen_tage == 30


def test_nur_den_namen_aendern_ist_eine_neue_revision_ohne_neuen_stand_der_wiedergabe(ks):
    ks.annehmen(liste(revision=5))
    roh = liste(revision=6)
    roh["zuordnungen"][UID_A]["name"] = "Rabe, rot"
    assert ks.annehmen(roh).angenommen
    assert lies(ks.pfad)["zuordnungen"][UID_A]["name"] == "Rabe, rot"
    assert ks.konfig.zuordnungen[UID_A] == ev.Zuordnung("serie", "3f9a1c07b2d4")  # gleiches Ziel


# -- sim card und HA-Ersatz (schreibe_zuordnung) ----------------------------------------------------------------


def test_schreibe_zuordnung_behaelt_namen_zusatzfelder_und_lesezeichen_tage_der_anderen(ks):
    ks.annehmen(liste())
    g = schreibe_zuordnung(ks, NEU, {"typ": "serie", "serie": "s1"})
    j = lies(ks.pfad)
    assert g.konfig.revision == 6
    assert j["zuordnungen"][UID_A] == {"ziel": {"typ": "serie", "serie": "3f9a1c07b2d4"}, "name": "Rabe aus Holz", "farbe": "rot"}
    assert j["zuordnungen"][UID_B]["name"] == "Die Drei ??? – Folge 3"
    assert j["zuordnungen"][NEU] == {"ziel": {"typ": "serie", "serie": "s1"}}
    assert j["lesezeichen_tage"] == 30


def test_ueberschreiben_aendert_nur_das_ziel_name_und_zusatzfelder_derselben_kennung_bleiben(ks):
    ks.annehmen(liste())
    schreibe_zuordnung(ks, UID_A, {"typ": "folge", "serie": "s9", "folge": "x.mp3"})
    z = lies(ks.pfad)["zuordnungen"][UID_A]
    assert z == {"ziel": {"typ": "folge", "serie": "s9", "folge": "x.mp3"}, "name": "Rabe aus Holz", "farbe": "rot"}
    assert ks.konfig.zuordnungen[UID_A].name == "Rabe aus Holz"


async def test_sim_card_laesst_namen_und_zusatzfelder_unveraendert(ks, kurz):
    ks.annehmen(liste())
    s = Sim(kurz, lambda e: None, SimUhr(), ks)
    e = await s.zeile_zu_ereignis_async(json.dumps({"befehl": "card", "uid": NEU, "ziel": {"typ": "aktion", "aktion": "status"}}))
    assert isinstance(e, ev.KonfigGeladen) and e.konfig.zuordnungen[UID_A].name == "Rabe aus Holz"
    j = lies(ks.pfad)
    assert j["zuordnungen"][UID_A]["name"] == "Rabe aus Holz" and j["zuordnungen"][UID_A]["farbe"] == "rot"
    assert j["zuordnungen"][UID_C]["name"] == "Status-Karte" and j["lesezeichen_tage"] == 30
    assert "name" not in j["zuordnungen"][NEU]
    # ``card`` auf eine benannte Kennung ändert nur das Ziel
    await s.zeile_zu_ereignis_async(json.dumps({"befehl": "card", "uid": UID_C, "ziel": {"typ": "aktion", "aktion": "gute_nacht"}}))
    assert lies(ks.pfad)["zuordnungen"][UID_C] == {"ziel": {"typ": "aktion", "aktion": "gute_nacht"}, "name": "Status-Karte"}


def test_ha_ersatz_laesst_namen_und_zusatzfelder_unveraendert(ks):
    class FakeSim:
        lernziel = {"typ": "serie", "serie": "s1"}
        lernbefehl_id = "b1"
        ueberschreiben = True

    aus: list = []
    ersatz = HaErsatz(FakeSim(), ks, aus.append)
    ks.annehmen(liste())
    ersatz.gelernt(ev.Eintrag(UID_A, "gelernt", "2026-11-09T10:00:00.000Z", "2026-11-09T10:00:00.000Z", 1, True, "b1"))
    j = lies(ks.pfad)
    assert j["zuordnungen"][UID_A] == {"ziel": {"typ": "serie", "serie": "s1"}, "name": "Rabe aus Holz", "farbe": "rot"}
    assert j["zuordnungen"][UID_B]["name"] == "Die Drei ??? – Folge 3"
    assert j["lesezeichen_tage"] == 30
    assert [type(e) for e in aus] == [ev.KonfigGeladen, ev.Bestaetigt]


def test_lesezeichen_tage_bleiben_auch_bei_null_erhalten(ks):
    ks.annehmen(liste(lesezeichen_tage=0))
    schreibe_zuordnung(ks, NEU, {"typ": "serie", "serie": "s1"})
    assert lies(ks.pfad)["lesezeichen_tage"] == 0
    assert ks.konfig.lesezeichen_tage == 0
