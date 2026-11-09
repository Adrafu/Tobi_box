"""AP 4.7: Leise-Zeiten, Gute-Nacht-Einstellungen und ``lesezeichen_tage`` einstellen (Vertrag W, Abschnitt 10).

Geprüft werden:

* **Gültigkeit**: dieselben Regeln und Grenzen wie auf der Box (``parse_konfig`` in ``box/src/tobibox/store.py``).
  Ist der Quelltext der Box erreichbar (Repo), vergleicht ein Test beide Prüfungen Fall für Fall.
* **Revision und Veröffentlichung**: eine Änderung erhöht die Revision und geht an ``tobibox/config``;
  eine ungültige Änderung ändert nichts (ganz abgelehnt).
* Rechte, Ereignis, Speicher, Export und die HA-Aktionen.
"""

from __future__ import annotations

import copy
import importlib
import itertools
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.tobibox.const import DOMAIN
from custom_components.tobibox.store import (
    FENSTER_MAX,
    Ungueltig,
    einstellungen_aus,
    pruefe_gute_nacht,
    pruefe_konfig,
    pruefe_leise_zeiten,
    pruefe_lesezeichen_tage,
    standard_einstellungen,
)

from .conftest import ereignis_arten, gespeicherte_konfig, warte_auf
from .test_websocket_api import fehler, ok, senden

LISTE_ID = "a3f9c1e07b2d4856"
ABEND = {"id": "abend", "tage": [1, 2, 3, 4, 5, 6, 7], "von": "19:30", "bis": "21:00", "wirkung": "leiser", "grenze": 25}
NACHT = {"id": "nacht", "tage": [1, 2, 3, 4, 5, 6, 7], "von": "21:00", "bis": "06:30", "wirkung": "stumm"}
LEISE = {"zeitzone": "Europe/Berlin", "fenster": [ABEND, NACHT]}


def basis(**einstellungen: Any) -> dict[str, Any]:
    """Eine Konfiguration (Version 2), wie sie die Box oder HA prüfen."""
    k: dict[str, Any] = {
        "schema_version": 2,
        "revision": 1,
        "liste_id": LISTE_ID,
        "zuordnungen": {},
        "leise_zeiten": {"zeitzone": "Europe/Berlin", "fenster": []},
        "gute_nacht": {"timer_min": 30, "ausblenden_s": 60},
    }
    k.update(einstellungen)
    return k


# --------------------------------------------------------------------------
# Gültigkeit (ohne HA)
# --------------------------------------------------------------------------


def test_vorgaben_sind_die_des_designs():
    assert standard_einstellungen() == {
        "leise_zeiten": {"zeitzone": "Europe/Berlin", "fenster": []},
        "gute_nacht": {"timer_min": 30, "ausblenden_s": 60},
        "lesezeichen_tage": 14,
    }


def test_gueltige_leise_zeiten_werden_unveraendert_zurueckgegeben():
    assert pruefe_leise_zeiten(LEISE) == LEISE
    assert pruefe_leise_zeiten({"fenster": []}) == {"zeitzone": "Europe/Berlin", "fenster": []}  # Zeitzone fehlt: Vorgabe
    stumm = pruefe_leise_zeiten({"zeitzone": "UTC", "fenster": [{**NACHT, "grenze": 50}]})  # Grenze bei „stumm“ entfällt
    assert stumm["fenster"][0] == NACHT
    assert pruefe_leise_zeiten({"fenster": [{**ABEND, "id": f"f{i}"} for i in range(FENSTER_MAX)]})["fenster"]


@pytest.mark.parametrize(
    ("lz", "pfad"),
    [
        (None, "leise_zeiten"),
        ([], "leise_zeiten"),
        ({"zeitzone": 5, "fenster": []}, "leise_zeiten.zeitzone"),
        ({"zeitzone": "Nirgendwo/Stadt", "fenster": []}, "leise_zeiten.zeitzone"),
        ({"zeitzone": "", "fenster": []}, "leise_zeiten.zeitzone"),
        ({}, "leise_zeiten.fenster"),
        ({"fenster": "x"}, "leise_zeiten.fenster"),
        ({"fenster": [{**ABEND, "id": f"f{i}"} for i in range(FENSTER_MAX + 1)]}, "leise_zeiten.fenster"),
        ({"fenster": ["x"]}, "fenster[0]"),
        ({"fenster": [{**ABEND, "id": ""}]}, "fenster[0].id"),
        ({"fenster": [{**ABEND, "id": "Gross"}]}, "fenster[0].id"),
        ({"fenster": [{**ABEND, "id": "a" * 33}]}, "fenster[0].id"),
        ({"fenster": [{**ABEND, "id": 1}]}, "fenster[0].id"),
        ({"fenster": [ABEND, {**NACHT, "id": "abend"}]}, "fenster[1].id"),  # doppelte id
        ({"fenster": [{**ABEND, "tage": []}]}, "fenster[0].tage"),
        ({"fenster": [{**ABEND, "tage": [0]}]}, "fenster[0].tage"),
        ({"fenster": [{**ABEND, "tage": [8]}]}, "fenster[0].tage"),
        ({"fenster": [{**ABEND, "tage": [1, 1]}]}, "fenster[0].tage"),
        ({"fenster": [{**ABEND, "tage": [True]}]}, "fenster[0].tage"),
        ({"fenster": [{**ABEND, "tage": [1.0]}]}, "fenster[0].tage"),
        ({"fenster": [{**ABEND, "tage": "1"}]}, "fenster[0].tage"),
        ({"fenster": [{**ABEND, "von": "24:00"}]}, "fenster[0].von"),
        ({"fenster": [{**ABEND, "von": "7:30"}]}, "fenster[0].von"),
        ({"fenster": [{**ABEND, "von": "19:60"}]}, "fenster[0].von"),
        ({"fenster": [{**ABEND, "von": 1930}]}, "fenster[0].von"),
        ({"fenster": [{**ABEND, "bis": "25:00"}]}, "fenster[0].bis"),
        ({"fenster": [{**ABEND, "bis": "19:30"}]}, "fenster[0].bis"),  # bis == von
        ({"fenster": [{**ABEND, "wirkung": "laut"}]}, "fenster[0].wirkung"),
        ({"fenster": [{**ABEND, "wirkung": None}]}, "fenster[0].wirkung"),
        ({"fenster": [{**ABEND, "grenze": -1}]}, "fenster[0].grenze"),
        ({"fenster": [{**ABEND, "grenze": 101}]}, "fenster[0].grenze"),
        ({"fenster": [{**ABEND, "grenze": True}]}, "fenster[0].grenze"),
        ({"fenster": [{**ABEND, "grenze": 25.0}]}, "fenster[0].grenze"),
        ({"fenster": [{**ABEND, "grenze": "25"}]}, "fenster[0].grenze"),
        ({"fenster": [{k: v for k, v in ABEND.items() if k != "grenze"}]}, "fenster[0].grenze"),  # „leiser“ braucht eine Grenze
    ],
)
def test_ungueltige_leise_zeiten_nennen_die_stelle(lz, pfad):
    with pytest.raises(Ungueltig) as err:
        pruefe_leise_zeiten(lz)
    assert err.value.pfad.startswith(pfad)


def test_grenzen_der_leise_zeiten_sind_inklusiv():
    for grenze in (0, 100):
        assert pruefe_leise_zeiten({"fenster": [{**ABEND, "grenze": grenze}]})["fenster"][0]["grenze"] == grenze
    for von, bis in (("00:00", "23:59"), ("23:59", "00:00"), ("23:00", "01:00")):  # über Mitternacht ist erlaubt
        assert pruefe_leise_zeiten({"fenster": [{**NACHT, "von": von, "bis": bis}]})


@pytest.mark.parametrize(("timer", "aus", "ok_"), [
    (1, 5, True), (240, 600, True), (30, 60, True),
    (0, 60, False), (241, 60, False), (30, 4, False), (30, 601, False),
    (True, 60, False), (30, True, False), (30.0, 60, False), (30, 60.0, False), ("30", 60, False), (None, 60, False), (30, None, False),
])
def test_gute_nacht_grenzen(timer, aus, ok_):
    if ok_:
        assert pruefe_gute_nacht({"timer_min": timer, "ausblenden_s": aus}) == {"timer_min": timer, "ausblenden_s": aus}
    else:
        with pytest.raises(Ungueltig):
            pruefe_gute_nacht({"timer_min": timer, "ausblenden_s": aus})


def test_gute_nacht_braucht_beide_felder_und_ein_objekt():
    for kaputt in (None, [], "x", {}, {"timer_min": 30}, {"ausblenden_s": 60}):
        with pytest.raises(Ungueltig):
            pruefe_gute_nacht(kaputt)


@pytest.mark.parametrize(("wert", "ok_"), [
    (0, True), (1, True), (14, True), (365, True),
    (-1, False), (366, False), (True, False), (False, False), (14.0, False), (14.5, False), ("14", False), (None, False), ([14], False),
])
def test_lesezeichen_tage_grenzen(wert, ok_):
    if ok_:
        assert pruefe_lesezeichen_tage(wert) == wert
    else:
        with pytest.raises(Ungueltig) as err:
            pruefe_lesezeichen_tage(wert)
        assert err.value.pfad == "lesezeichen_tage"


def test_pruefe_konfig_benutzt_dieselben_pruefungen_und_vorgabe_14():
    k = pruefe_konfig(basis())
    assert k["lesezeichen_tage"] == 14  # Feld fehlt: Vorgabe 14
    assert pruefe_konfig(basis(lesezeichen_tage=0))["lesezeichen_tage"] == 0
    for kaputt in (basis(lesezeichen_tage=366), basis(gute_nacht={"timer_min": 0, "ausblenden_s": 60}), basis(leise_zeiten={"fenster": [ABEND] * 2})):
        with pytest.raises(Ungueltig):
            pruefe_konfig(kaputt)


def test_einstellungen_aus_ist_eine_kopie_und_hinweis_pegel_nur_wenn_gesetzt():
    k = pruefe_konfig(basis(leise_zeiten=LEISE))
    e = einstellungen_aus(k)
    assert set(e) == {"leise_zeiten", "gute_nacht", "lesezeichen_tage"}
    e["leise_zeiten"]["fenster"].clear()
    assert len(k["leise_zeiten"]["fenster"]) == 2
    assert einstellungen_aus(pruefe_konfig(basis(hinweis_pegel=15)))["hinweis_pegel"] == 15


# --------------------------------------------------------------------------
# Gleiche Grenzen wie auf der Box: beide Prüfungen Fall für Fall
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def box_store():
    """Das Modul ``tobibox.store`` der Box aus dem Repo (ohne es zu ändern); fehlt es oder lädt es nicht, wird übersprungen."""
    quelle = Path(__file__).resolve().parents[2] / "box" / "src"
    if not (quelle / "tobibox" / "store.py").exists():
        pytest.skip("Quelltext der Box nicht vorhanden")
    sys.path.insert(0, str(quelle))
    try:
        return importlib.import_module("tobibox.store")
    except Exception as err:  # fehlende Abhängigkeiten der Box in der HA-venv
        pytest.skip(f"Box-Modul nicht ladbar: {err}")
    finally:
        sys.path.remove(str(quelle))


def _ha(k: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return pruefe_konfig(copy.deepcopy(k))
    except Ungueltig:
        return None


def _box(box_store, k: dict[str, Any]):
    try:
        return box_store.parse_konfig(copy.deepcopy(k))
    except box_store.Ungueltig:
        return None


def _gleich(box_store, k: dict[str, Any]) -> bool:
    """Beide nehmen an oder beide lehnen ab; wenn sie annehmen, mit denselben Werten."""
    ha, box = _ha(k), _box(box_store, k)
    assert (ha is None) == (box is None), f"HA {'lehnt ab' if ha is None else 'nimmt an'}, Box {'lehnt ab' if box is None else 'nimmt an'}: {k}"
    if ha is None:
        return False
    assert box.leise_zeiten.zeitzone == ha["leise_zeiten"]["zeitzone"]
    assert [(f.id, list(f.tage), f.von, f.bis, f.wirkung, f.grenze) for f in box.leise_zeiten.fenster] == [
        (f["id"], f["tage"], f["von"], f["bis"], f["wirkung"], f.get("grenze")) for f in ha["leise_zeiten"]["fenster"]
    ]
    assert (box.gute_nacht.timer_min, box.gute_nacht.ausblenden_s) == (ha["gute_nacht"]["timer_min"], ha["gute_nacht"]["ausblenden_s"])
    assert box.lesezeichen_tage == ha["lesezeichen_tage"]
    return True


ZAHLEN = [None, True, False, -1, 0, 1, 4, 5, 25, 30, 99, 100, 101, 240, 241, 365, 366, 600, 601, 14.0, 30.5, "30", [30], {}]


def test_gute_nacht_und_lesezeichen_wie_auf_der_box(box_store):
    angenommen = 0
    for timer, aus in itertools.product(ZAHLEN, ZAHLEN):
        angenommen += _gleich(box_store, basis(gute_nacht={"timer_min": timer, "ausblenden_s": aus}))
    assert angenommen == 9 * 11  # gültig sind 9 Werte für timer_min (1 bis 240) und 11 für ausblenden_s (5 bis 600)
    for tage in ZAHLEN:
        _gleich(box_store, basis(lesezeichen_tage=tage))
    fehlend = basis()
    assert _gleich(box_store, fehlend)  # Feld fehlt: beide nehmen 14
    for k in (basis(gute_nacht=None), basis(gute_nacht={}), basis(gute_nacht={"timer_min": 30}), basis(gute_nacht="x")):
        assert not _gleich(box_store, k)


def test_gute_nacht_gueltige_menge_ist_genau_gleich(box_store):
    """Alle ganzen Zahlen im Umfeld der Grenzen: dieselbe Menge der angenommenen Werte."""
    for wert in range(-2, 250):
        _gleich(box_store, basis(gute_nacht={"timer_min": wert, "ausblenden_s": 60}))
    for wert in range(-2, 610):
        _gleich(box_store, basis(gute_nacht={"timer_min": 30, "ausblenden_s": wert}))
    for wert in range(-2, 370):
        _gleich(box_store, basis(lesezeichen_tage=wert))


ZONEN = ["Europe/Berlin", "UTC", "America/New_York", "Asia/Kolkata", "Nirgendwo/Stadt", "", " ", "europe/berlin", "../etc/passwd", "Europe/Berlin\n", 5, None, True, ["UTC"]]
ZEITEN = ["00:00", "06:30", "19:30", "23:59", "24:00", "7:30", "19:3", "19:60", "19:30\n", " 19:30", "19:30 ", "1930", "ab:cd", "", None, 1930, True]
TAGE = [[1], [1, 2, 3, 4, 5, 6, 7], [7], [], [0], [8], [1, 1], [True], [1.0], ["1"], [1, None], "1", None, (1, 2)]
WIRKUNGEN = ["leiser", "stumm", "Leiser", "laut", "", None, 1]
GRENZEN = [None, 0, 25, 100, -1, 101, True, 25.0, "25"]
IDS = ["abend", "a", "a" * 32, "a" * 33, "", "A", "ab cd", "ab_cd-1", "ab\n", 1, None]


def test_zeitzonen_wie_auf_der_box(box_store):
    for zone in ZONEN:
        _gleich(box_store, basis(leise_zeiten={"zeitzone": zone, "fenster": []}))
    assert _gleich(box_store, basis(leise_zeiten={"fenster": []}))  # ohne Zeitzone: Vorgabe


def test_fenster_felder_wie_auf_der_box(box_store):
    angenommen = abgelehnt = 0
    felder = [("von", ZEITEN), ("bis", ZEITEN), ("tage", TAGE), ("wirkung", WIRKUNGEN), ("grenze", GRENZEN), ("id", IDS)]
    for feld, werte in felder:
        for wert in werte:
            f = copy.deepcopy(ABEND)
            f[feld] = wert
            if _gleich(box_store, basis(leise_zeiten={"zeitzone": "Europe/Berlin", "fenster": [f]})):
                angenommen += 1
            else:
                abgelehnt += 1
    assert angenommen > 20 and abgelehnt > 40  # beide Seiten der Grenzen wurden verglichen
    # „stumm“ mit und ohne Grenze, fehlende Felder
    for wirkung, grenze in itertools.product(WIRKUNGEN, [*GRENZEN, "fehlt"]):
        f = {k: v for k, v in NACHT.items()}
        f["wirkung"] = wirkung
        if grenze != "fehlt":
            f["grenze"] = grenze
        _gleich(box_store, basis(leise_zeiten={"fenster": [f]}))
    for feld in ("id", "tage", "von", "bis", "wirkung", "grenze"):
        f = {k: v for k, v in ABEND.items() if k != feld}
        assert not _gleich(box_store, basis(leise_zeiten={"fenster": [f]}))


def test_fensterliste_wie_auf_der_box(box_store):
    def viele(n: int) -> list[dict[str, Any]]:
        return [{**ABEND, "id": f"f{i}"} for i in range(n)]

    for n in (0, 1, 31, 32, 33, 64):
        assert _gleich(box_store, basis(leise_zeiten={"fenster": viele(n)})) == (n <= 32)
    doppelt = [ABEND, {**NACHT, "id": "abend"}]
    for lz in (
        {"fenster": doppelt}, {"fenster": None}, {"fenster": {}}, {"fenster": "x"}, {"fenster": [None]}, {"fenster": [[]]}, {}, None, [], "x",
        {"zeitzone": "Europe/Berlin"}, {"fenster": [ABEND, NACHT]}, {"fenster": [NACHT, ABEND]},
    ):
        _gleich(box_store, basis(leise_zeiten=lz))
    assert not _gleich(box_store, {k: v for k, v in basis().items() if k != "leise_zeiten"})


def test_unbekannte_zusatzfelder_stoeren_beide_nicht(box_store):
    k = basis(leise_zeiten={"zeitzone": "UTC", "extra": 1, "fenster": [{**ABEND, "extra": 2}]}, gute_nacht={"timer_min": 30, "ausblenden_s": 60, "extra": 3})
    assert _gleich(box_store, k)
    assert "extra" not in json.dumps(pruefe_konfig(k)["leise_zeiten"])  # HA schreibt nur bekannte Felder fort


def test_was_ha_veroeffentlicht_nimmt_die_box_an(box_store):
    """Die Normalform von HA ist eine gültige Konfiguration der Box (mit allen Einstellungen)."""
    k = pruefe_konfig(basis(leise_zeiten=LEISE, gute_nacht={"timer_min": 240, "ausblenden_s": 5}, lesezeichen_tage=365, hinweis_pegel=10))
    from custom_components.tobibox.store import konfig_zu_mqtt

    box = box_store.parse_konfig(konfig_zu_mqtt(k))
    assert [f.id for f in box.leise_zeiten.fenster] == ["abend", "nacht"]
    assert (box.gute_nacht.timer_min, box.gute_nacht.ausblenden_s, box.lesezeichen_tage) == (240, 5, 365)


# --------------------------------------------------------------------------
# Befehle: einstellungen/get und einstellungen/set
# --------------------------------------------------------------------------


@pytest.fixture
async def api(hass, integration, box_fabrik, hass_ws_client):
    """Client eines Administrators; ``box1`` ist online."""
    await box_fabrik("box1").online()
    return await hass_ws_client(hass)


@pytest.fixture
async def api_lesend(hass, integration, hass_ws_client, hass_read_only_access_token):
    return await hass_ws_client(hass, hass_read_only_access_token)


def konfigs(box_fabrik) -> list[dict[str, Any]]:
    return box_fabrik("box1").konfigs()


async def test_hello_sagt_die_faehigkeit_zu(api):
    assert "einstellungen" in (await ok(api, "hello", v=1))["faehigkeiten"]


async def test_get_liefert_die_vorgaben(api, api_lesend):
    for client in (api, api_lesend):  # Lesen dürfen alle
        r = await ok(client, "einstellungen/get")
        assert r["leise_zeiten"] == {"zeitzone": "Europe/Berlin", "fenster": []}
        assert r["gute_nacht"] == {"timer_min": 30, "ausblenden_s": 60}
        assert r["lesezeichen_tage"] == 14
        assert "hinweis_pegel" not in r
        assert r["konfig"]["zustand"] == "ok" and r["konfig"]["revision"] == 1
    assert await fehler(api, "einstellungen/get", x=1) == "invalid_format"


async def test_get_zeigt_hinweis_pegel_wenn_gesetzt(api, integration):
    integration.store.konfig["hinweis_pegel"] = 15
    assert (await ok(api, "einstellungen/get"))["hinweis_pegel"] == 15


async def test_set_leise_zeiten_erhoeht_die_revision_und_geht_an_tobibox_config(hass, api, box_fabrik, hass_storage, ereignisse, integration):
    vorher = len(konfigs(box_fabrik))
    integration._buendel.clear()  # das Ereignis kommt sofort, wenn in der letzten Sekunde keines kam (Bündeln, Vertrag W Abschnitt 4)
    r = await ok(api, "einstellungen/set", leise_zeiten=LEISE)
    assert r["geaendert"] is True and r["veroeffentlicht"] is True
    assert r["konfig"]["revision"] == 2 and r["konfig"]["zustand"] == "ok"
    assert r["leise_zeiten"] == LEISE and r["gute_nacht"] == {"timer_min": 30, "ausblenden_s": 60} and r["lesezeichen_tage"] == 14
    # veröffentlicht: eine neue Nachricht, retained, mit Revision 2 und den Fenstern
    gesendet = [m for m in box_fabrik("box1").veroeffentlicht() if m[0] == "tobibox/config"]
    assert len(konfigs(box_fabrik)) == vorher + 1
    _thema, nutzlast, _qos, retain = gesendet[-1]
    assert retain is True
    k = json.loads(nutzlast)
    assert k["revision"] == 2 and k["liste_id"] == integration.store.liste_id
    assert k["leise_zeiten"] == LEISE and k["gute_nacht"] == {"timer_min": 30, "ausblenden_s": 60} and k["lesezeichen_tage"] == 14
    # gespeichert und als Ereignis gemeldet
    assert gespeicherte_konfig(hass_storage)["leise_zeiten"] == LEISE
    assert gespeicherte_konfig(hass_storage)["revision"] == 2
    await hass.async_block_till_done()
    assert "geaendert" in ereignis_arten(ereignisse, "konfig")
    # und es steht danach im Lesebefehl
    assert (await ok(api, "einstellungen/get"))["leise_zeiten"] == LEISE


async def test_set_gute_nacht_und_lesezeichen_tage(api, box_fabrik, integration):
    r = await ok(api, "einstellungen/set", gute_nacht={"timer_min": 45, "ausblenden_s": 90})
    assert r["geaendert"] is True and r["konfig"]["revision"] == 2
    assert konfigs(box_fabrik)[-1]["gute_nacht"] == {"timer_min": 45, "ausblenden_s": 90}
    r = await ok(api, "einstellungen/set", lesezeichen_tage=0)  # 0 = nie
    assert r["geaendert"] is True and r["konfig"]["revision"] == 3 and r["lesezeichen_tage"] == 0
    assert konfigs(box_fabrik)[-1]["lesezeichen_tage"] == 0
    r = await ok(api, "einstellungen/set", lesezeichen_tage=365)
    assert konfigs(box_fabrik)[-1]["lesezeichen_tage"] == 365 and r["konfig"]["revision"] == 4
    assert integration.store.konfig["gute_nacht"] == {"timer_min": 45, "ausblenden_s": 90}  # der andere Teil blieb


async def test_set_mehrere_teile_in_einer_revision(api, box_fabrik):
    r = await ok(api, "einstellungen/set", leise_zeiten=LEISE, gute_nacht={"timer_min": 20, "ausblenden_s": 30}, lesezeichen_tage=7)
    assert r["konfig"]["revision"] == 2  # eine Änderung, eine Revision
    k = konfigs(box_fabrik)[-1]
    assert (k["leise_zeiten"], k["gute_nacht"], k["lesezeichen_tage"]) == (LEISE, {"timer_min": 20, "ausblenden_s": 30}, 7)


async def test_set_mit_gleichen_werten_aendert_nichts(api, box_fabrik, hass_storage):
    await ok(api, "einstellungen/set", leise_zeiten=LEISE, lesezeichen_tage=21)
    anzahl = len(konfigs(box_fabrik))
    r = await ok(api, "einstellungen/set", leise_zeiten=copy.deepcopy(LEISE), lesezeichen_tage=21)  # idempotent
    assert r["geaendert"] is False and r["veroeffentlicht"] is None and r["konfig"]["revision"] == 2
    assert len(konfigs(box_fabrik)) == anzahl  # keine neue Nachricht
    # Zusatzfelder und die Grenze bei „stumm“ fallen weg, es ist also weiterhin dieselbe Einstellung
    gleich = {"zeitzone": "Europe/Berlin", "fenster": [ABEND, {**NACHT, "grenze": 40, "extra": 1}]}
    assert (await ok(api, "einstellungen/set", leise_zeiten=gleich))["geaendert"] is False
    assert gespeicherte_konfig(hass_storage)["revision"] == 2


async def test_set_ohne_aenderung_der_standardwerte(api):
    r = await ok(api, "einstellungen/set", gute_nacht={"timer_min": 30, "ausblenden_s": 60}, lesezeichen_tage=14)
    assert r["geaendert"] is False and r["konfig"]["revision"] == 1


@pytest.mark.parametrize(
    ("felder", "pfad"),
    [
        ({"leise_zeiten": {"fenster": [{**ABEND, "von": "25:00"}]}}, "fenster[0].von"),
        ({"leise_zeiten": {"fenster": [{**ABEND, "grenze": 101}]}}, "fenster[0].grenze"),
        ({"leise_zeiten": {"zeitzone": "Nirgendwo/Stadt", "fenster": []}}, "leise_zeiten.zeitzone"),
        ({"leise_zeiten": {"fenster": [{**ABEND, "von": "20:00", "bis": "20:00"}]}}, "fenster[0].bis"),
        ({"leise_zeiten": {"fenster": [ABEND, {**ABEND}]}}, "fenster[1].id"),
        ({"leise_zeiten": {"fenster": [{**ABEND, "tage": []}]}}, "fenster[0].tage"),
        ({"leise_zeiten": "immer"}, "leise_zeiten"),
        ({"leise_zeiten": None}, "leise_zeiten"),
        ({"gute_nacht": {"timer_min": 0, "ausblenden_s": 60}}, "gute_nacht.timer_min"),
        ({"gute_nacht": {"timer_min": 241, "ausblenden_s": 60}}, "gute_nacht.timer_min"),
        ({"gute_nacht": {"timer_min": 30, "ausblenden_s": 4}}, "gute_nacht.ausblenden_s"),
        ({"gute_nacht": {"timer_min": 30, "ausblenden_s": 601}}, "gute_nacht.ausblenden_s"),
        ({"gute_nacht": {"timer_min": 30}}, "gute_nacht.ausblenden_s"),
        ({"gute_nacht": {"timer_min": 30.0, "ausblenden_s": 60}}, "gute_nacht.timer_min"),
        ({"lesezeichen_tage": 366}, "lesezeichen_tage"),
        ({"lesezeichen_tage": -1}, "lesezeichen_tage"),
        ({"lesezeichen_tage": True}, "lesezeichen_tage"),
        ({"lesezeichen_tage": "14"}, "lesezeichen_tage"),
        ({"lesezeichen_tage": 14.5}, "lesezeichen_tage"),
        ({"lesezeichen_tage": None}, "lesezeichen_tage"),
    ],
)
async def test_ungueltig_wird_ganz_abgelehnt(api, box_fabrik, hass_storage, felder, pfad):
    anzahl = len(konfigs(box_fabrik))
    antwort = await senden(api, "einstellungen/set", **felder)
    assert antwort["success"] is False
    assert antwort["error"]["code"] == "einstellung_ungueltig"
    assert pfad in antwort["error"]["message"]  # Pfad im Klartext
    assert (await ok(api, "einstellungen/get"))["konfig"]["revision"] == 1
    assert len(konfigs(box_fabrik)) == anzahl
    assert gespeicherte_konfig(hass_storage)["revision"] == 1


async def test_ein_ungueltiger_teil_verwirft_auch_die_gueltigen(api, integration, box_fabrik):
    antwort = await senden(api, "einstellungen/set", leise_zeiten=LEISE, gute_nacht={"timer_min": 0, "ausblenden_s": 60}, lesezeichen_tage=30)
    assert antwort["error"]["code"] == "einstellung_ungueltig"
    r = await ok(api, "einstellungen/get")
    assert r["leise_zeiten"]["fenster"] == [] and r["lesezeichen_tage"] == 14 and r["konfig"]["revision"] == 1
    assert integration.store.konfig["leise_zeiten"]["fenster"] == []


async def test_set_eingabe_ist_streng_und_nur_fuer_administratoren(api, api_lesend, integration):
    assert await fehler(api, "einstellungen/set") == "invalid_format"  # nichts zu ändern
    assert await fehler(api, "einstellungen/set", unbekannt=1) == "invalid_format"
    assert await fehler(api, "einstellungen/set", lesezeichen_tage=5, hinweis_pegel=20) == "invalid_format"  # nicht Teil von set
    assert await fehler(api_lesend, "einstellungen/set", lesezeichen_tage=5) == "unauthorized"
    assert integration.store.konfig["lesezeichen_tage"] == 14


async def test_set_ist_gesperrt_wenn_die_konfiguration_nicht_bereit_ist(api, integration):
    integration.store.zustand = "leer_neu"
    assert await fehler(api, "einstellungen/set", lesezeichen_tage=5) == "konfig_nicht_bereit"
    assert (await ok(api, "einstellungen/get"))["konfig"]["zustand"] == "leer_neu"  # Lesen geht weiter
    integration.store.konfig = None  # leerer Speicher: es gibt nichts zu lesen
    assert await fehler(api, "einstellungen/get") == "konfig_nicht_bereit"


async def test_ohne_broker_gespeichert_und_nachgeholt(api, integration):
    """Wie bei Zuordnungen: Scheitert die Veröffentlichung, ist die Änderung trotzdem gespeichert (``veroeffentlicht=false``)."""
    async def keine(*_a, **_k):
        return False

    integration.mqtt.veroeffentliche_konfig = keine
    r = await ok(api, "einstellungen/set", lesezeichen_tage=3)
    assert r["geaendert"] is True and r["veroeffentlicht"] is False and r["konfig"]["revision"] == 2
    assert integration.store.konfig["lesezeichen_tage"] == 3


async def test_andere_felder_bleiben_und_spaetere_aenderungen_behalten_die_einstellungen(api, integration, box_fabrik):
    integration.store.konfig["ton_pegel"] = 40
    integration.store.konfig["hinweis_pegel"] = 15
    await ok(api, "einstellungen/set", leise_zeiten=LEISE, lesezeichen_tage=30)
    k = konfigs(box_fabrik)[-1]
    assert (k["ton_pegel"], k["hinweis_pegel"]) == (40, 15)
    # eine Zuordnung danach schreibt die Einstellungen unverändert fort
    await ok(api, "zuordnung/set", uid="04ffeedd", ziel={"typ": "aktion", "aktion": "gute_nacht"}, erwartet_ziel=None)
    k = konfigs(box_fabrik)[-1]
    assert k["leise_zeiten"] == LEISE and k["lesezeichen_tage"] == 30 and k["revision"] == 3
    assert k["zuordnungen"]["04ffeedd"]["ziel"] == {"typ": "aktion", "aktion": "gute_nacht"}


async def test_export_enthaelt_die_neuen_einstellungen(hass, api, nas, integration):
    await ok(api, "einstellungen/set", leise_zeiten=LEISE, gute_nacht={"timer_min": 15, "ausblenden_s": 20}, lesezeichen_tage=0)
    datei = nas.export / "config.json"
    await warte_auf(hass, lambda: datei.exists() and json.loads(datei.read_text("utf-8")).get("revision") == 2)
    export = json.loads(datei.read_text("utf-8"))
    assert export["leise_zeiten"] == LEISE and export["gute_nacht"] == {"timer_min": 15, "ausblenden_s": 20} and export["lesezeichen_tage"] == 0
    # und der Export ist wieder eine gültige Konfiguration (Weg zurück: konfig/aus_export)
    assert pruefe_konfig(export)["leise_zeiten"] == LEISE


async def test_was_ha_veroeffentlicht_besteht_die_pruefung_der_box(api, box_fabrik, box_store):
    await ok(api, "einstellungen/set", leise_zeiten=LEISE, gute_nacht={"timer_min": 240, "ausblenden_s": 600}, lesezeichen_tage=365)
    box = box_store.parse_konfig(konfigs(box_fabrik)[-1])
    assert box.revision == 2
    assert [(f.id, f.wirkung, f.grenze) for f in box.leise_zeiten.fenster] == [("abend", "leiser", 25), ("nacht", "stumm", None)]
    assert (box.gute_nacht.timer_min, box.gute_nacht.ausblenden_s, box.lesezeichen_tage) == (240, 600, 365)


# --------------------------------------------------------------------------
# HA-Aktionen (services.yaml)
# --------------------------------------------------------------------------


@pytest.fixture
async def dienste(hass, integration, box_fabrik):
    await box_fabrik("box1").online()

    async def ruf(aktion: str, /, **daten):
        return await hass.services.async_call(DOMAIN, aktion, daten, blocking=True)

    return ruf


async def test_dienst_gute_nacht_teilweise(dienste, integration, box_fabrik):
    await dienste("gute_nacht_setzen", timer_min=45)  # fehlendes Feld bleibt
    assert integration.store.konfig["gute_nacht"] == {"timer_min": 45, "ausblenden_s": 60}
    assert konfigs(box_fabrik)[-1]["gute_nacht"] == {"timer_min": 45, "ausblenden_s": 60}
    await dienste("gute_nacht_setzen", ausblenden_s=120.0)  # Regler liefern 120.0
    assert integration.store.konfig["gute_nacht"] == {"timer_min": 45, "ausblenden_s": 120}
    assert integration.store.revision == 3


async def test_dienst_leise_zeiten(dienste, integration, box_fabrik):
    await dienste("leise_zeiten_setzen", fenster=[ABEND, NACHT])  # Zeitzone fehlt: bleibt
    assert integration.store.konfig["leise_zeiten"] == LEISE
    await dienste("leise_zeiten_setzen", zeitzone="Europe/London")  # Fenster fehlen: bleiben
    assert integration.store.konfig["leise_zeiten"] == {"zeitzone": "Europe/London", "fenster": [ABEND, NACHT]}
    assert konfigs(box_fabrik)[-1]["leise_zeiten"]["zeitzone"] == "Europe/London"
    await dienste("leise_zeiten_setzen", fenster=[])
    assert integration.store.konfig["leise_zeiten"]["fenster"] == []


async def test_dienst_lesezeichen_tage(dienste, integration, box_fabrik):
    await dienste("lesezeichen_tage_setzen", tage=0)
    assert integration.store.konfig["lesezeichen_tage"] == 0
    assert konfigs(box_fabrik)[-1]["lesezeichen_tage"] == 0
    await dienste("lesezeichen_tage_setzen", tage=60.0)
    assert integration.store.konfig["lesezeichen_tage"] == 60


async def test_dienst_ungueltig_aendert_nichts(dienste, integration, box_fabrik):
    anzahl = len(konfigs(box_fabrik))
    for aktion, daten in (
        ("gute_nacht_setzen", {"timer_min": 0}),
        ("gute_nacht_setzen", {"ausblenden_s": 601}),
        ("gute_nacht_setzen", {"timer_min": 30.5}),
        ("leise_zeiten_setzen", {"fenster": [{**ABEND, "von": "99:99"}]}),
        ("leise_zeiten_setzen", {"zeitzone": "Nirgendwo/Stadt"}),
        ("lesezeichen_tage_setzen", {"tage": 366}),
        ("lesezeichen_tage_setzen", {"tage": -1}),
    ):
        with pytest.raises(ServiceValidationError) as err:
            await dienste(aktion, **daten)
        assert err.value.translation_key == "einstellung_ungueltig" and err.value.translation_domain == DOMAIN
        assert "pfad" in err.value.translation_placeholders
    assert integration.store.revision == 1 and len(konfigs(box_fabrik)) == anzahl
