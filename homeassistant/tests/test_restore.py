"""Wiederherstellung, leerer Speicher, Export und Boxen mit neuerem Stand (Vertrag W, Abschnitt 13.7)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from homeassistant.components import persistent_notification

from custom_components.tobibox import hub as hub_modul
from custom_components.tobibox.fehler import TobiboxFehler
from custom_components.tobibox.store import konfig_zu_export, neue_konfig
from custom_components.tobibox.util import jetzt_iso

from .conftest import fertig, gespeicherte_konfig, warte_auf

UID = "e0040312345678ab"
UID2 = "04a1b2c3"
SERIE = {"typ": "serie", "serie": "rabe"}
ALT = "aaaaaaaaaaaaaaaa"
NEU = "bbbbbbbbbbbbbbbb"


def konfig(liste_id: str, revision: int, zuordnungen: dict[str, Any] | None = None) -> dict[str, Any]:
    k = neue_konfig(zuordnungen if zuordnungen is not None else {UID: {"ziel": SERIE, "name": "Rabe aus Holz"}})
    k["liste_id"] = liste_id
    k["revision"] = revision
    return k


def schreibe_export(nas, k: dict[str, Any], am: str = "2026-11-09T12:00:00Z") -> None:
    (nas.export / "config.json").write_text(json.dumps(konfig_zu_export(k, am)))


def veroeffentlichte_konfigs(box) -> list[dict[str, Any]]:
    return box.konfigs()


async def box_status(box, k: dict[str, Any], **kw) -> None:
    await box.status(gespeichert=True, konfig={"revision": k["revision"], "liste_id": k["liste_id"]}, **kw)


async def start_mit_status(hass, starte, box_fabrik, k_box: dict[str, Any] | None):
    """Startet die Integration und spielt währenddessen die dauerhaften ``status``-Nachrichten beider Boxen ein."""
    hub_modul.START_WARTEN = 5.0
    try:
        hub = await starte(warten=False)
        for name in ("box1", "box2"):
            if k_box is None:
                await box_fabrik(name).status(gespeichert=True)
            else:
                await box_status(box_fabrik(name), k_box)
        await fertig(hass, hub)
    finally:
        hub_modul.START_WARTEN = 0.05
    return hub


# --- (a) leerer Speicher, vorhandener Export und Box-Status: leer_neu ---


async def test_a_leerer_speicher_mit_export_und_box_status_ist_leer_neu(hass, starte_integration, box_fabrik, nas):
    schreibe_export(nas, konfig(ALT, 17))
    vorher = (nas.export / "config.json").read_bytes()
    hub = await start_mit_status(hass, starte_integration, box_fabrik, konfig(ALT, 17))
    assert hub.store.zustand == "leer_neu"
    assert hub.konfig_stand() == {"revision": None, "liste_id": None, "zustand": "leer_neu", "export_ok": False, "export_geschrieben_am": None}
    assert box_fabrik("box1").konfigs() == []  # nichts veröffentlicht, keine Listen-ID angelegt
    assert hub.store.konfig is None
    assert (nas.export / "config.json").read_bytes() == vorher  # der Export wird nicht überschrieben
    for aufruf in (
        hub.zuordnung_setzen(UID, SERIE),
        hub.zuordnung_entfernen(UID),
    ):
        with pytest.raises(TobiboxFehler) as err:
            await aufruf
        assert err.value.code == "konfig_nicht_bereit"
    # Lesen, Medien, Neue Tobies und Bestätigungen gehen weiter
    b1 = box_fabrik("box1")
    await b1.unbekannt(UID2)
    assert b1.acks(UID2)[0]["grund"] == "neu"
    assert (await hub.zuordnung_liste(None, 100, 0))["konfig"]["zustand"] == "leer_neu"
    assert hub.hello(1, True)["konfig"]["zustand"] == "leer_neu"
    await hub.medien.serie_anlegen("Trotzdem")
    assert box_fabrik("box1").konfigs() == []


async def test_a2_leerer_speicher_ohne_export_aber_box_hat_eine_liste(hass, starte_integration, box_fabrik, nas):
    hub = await start_mit_status(hass, starte_integration, box_fabrik, konfig(ALT, 3))
    assert hub.store.zustand == "leer_neu"
    assert box_fabrik("box1").konfigs() == []


async def test_a3_export_ordner_nicht_erreichbar_ist_kein_erststart(hass, starte_integration, box_fabrik, nas):
    import shutil

    shutil.rmtree(nas.export)
    hub = await start_mit_status(hass, starte_integration, box_fabrik, None)
    assert hub.store.zustand == "leer_neu"  # ohne den Export zu sehen, ist ein leerer Speicher kein Erststart
    assert box_fabrik("box1").konfigs() == []


# --- (b) Erststart ---


async def test_b_erststart_legt_neue_liste_an_und_veroeffentlicht(hass, starte_integration, box_fabrik, nas):
    hub = await start_mit_status(hass, starte_integration, box_fabrik, None)  # Boxen ohne Liste: konfig.liste_id leer
    assert hub.store.zustand == "ok"
    assert hub.konfig_stand()["revision"] == 1
    konfigs = box_fabrik("box1").konfigs()
    assert len(konfigs) == 1 and konfigs[0]["revision"] == 1 and konfigs[0]["liste_id"] == hub.store.liste_id
    await warte_auf(hass, lambda: hub.export_ok)
    assert json.loads((nas.export / "config.json").read_text())["liste_id"] == hub.store.liste_id


# --- (c) Zurückspielen: Export neuer ---


async def test_c_export_mit_hoeherer_revision_ist_neuer(hass, starte_integration, box_fabrik, nas, vorab_speicher):
    vorab_speicher({"konfig": {k: v for k, v in konfig(ALT, 3).items()}, "export_geschrieben_am": "2026-11-09T09:00:00Z"})
    schreibe_export(nas, konfig(ALT, 7, {UID: {"ziel": SERIE}, UID2: {"ziel": SERIE}}))  # gleiche Listen-ID, höhere Revision
    vorher = (nas.export / "config.json").read_bytes()
    hub = await starte_integration()
    assert hub.store.zustand == "export_neuer"
    assert hub.konfig_stand()["revision"] == 3 and hub.konfig_stand()["liste_id"] == ALT
    assert box_fabrik("box1").konfigs() == []  # nichts Neues veröffentlicht
    assert (nas.export / "config.json").read_bytes() == vorher
    with pytest.raises(TobiboxFehler) as err:
        await hub.zuordnung_setzen(UID, SERIE)
    assert err.value.code == "konfig_nicht_bereit"
    info = await hub.konfig_export_lesen()
    assert (info["revision"], info["anzahl_zuordnungen"], info["neuer_als_ha"]) == (7, 2, True)


async def test_c2_andere_listen_id_und_juengerer_export_ist_neuer(hass, starte_integration, nas, vorab_speicher):
    vorab_speicher({"konfig": konfig(ALT, 3), "export_geschrieben_am": "2026-11-09T09:00:00Z"})
    schreibe_export(nas, konfig(NEU, 1), am="2026-11-09T10:00:00Z")  # exportiert_am nach dem, was dieser Speicher selbst geschrieben hat
    assert (await starte_integration()).store.zustand == "export_neuer"


async def test_c3_aelterer_export_oder_gleicher_stand_ist_ok(hass, starte_integration, nas, vorab_speicher, box_fabrik):
    vorab_speicher({"konfig": konfig(ALT, 3), "export_geschrieben_am": "2026-11-09T09:00:00Z"})
    schreibe_export(nas, konfig(NEU, 1), am="2026-11-09T08:00:00Z")  # anderer Speicher, aber älter
    hub = await starte_integration()
    assert hub.store.zustand == "ok"
    assert hub.store.konfig["liste_id"] == ALT
    # ``ok`` verteilt: die Liste geht beim Start noch einmal hinaus und der Export wird nachgezogen
    await warte_auf(hass, lambda: hub.export_ok)
    assert json.loads((nas.export / "config.json").read_text())["liste_id"] == ALT
    assert [(k["liste_id"], k["revision"]) for k in box_fabrik("box1").konfigs()] == [(ALT, 3)]


async def test_c4_kein_export_gar_nicht_neuer(hass, starte_integration, nas, vorab_speicher):
    vorab_speicher({"konfig": konfig(ALT, 3)})
    assert (await starte_integration()).store.zustand == "ok"


# --- (d) konfig/aus_export ---


async def test_d_aus_export_neue_listen_id_revision_1_namen_uebernommen(hass, starte_integration, box_fabrik, nas):
    k_export = konfig(ALT, 17, {UID: {"ziel": SERIE, "name": "Rabe aus Holz"}, UID2: {"ziel": {"typ": "aktion", "aktion": "status"}}})
    k_export["leise_zeiten"] = {"zeitzone": "Europe/Berlin", "fenster": [{"id": "nacht", "tage": [1, 2], "von": "21:00", "bis": "06:30", "wirkung": "stumm"}]}
    k_export["gute_nacht"] = {"timer_min": 45, "ausblenden_s": 90}
    k_export["hinweis_pegel"] = 20
    k_export["lesezeichen_tage"] = 30
    schreibe_export(nas, k_export)
    hub = await start_mit_status(hass, starte_integration, box_fabrik, konfig(ALT, 17))
    assert hub.store.zustand == "leer_neu"
    erg = await hub.konfig_aus_export()
    assert erg["uebernommen"] == {"zuordnungen": 2, "fenster": 1}
    assert erg["veroeffentlicht"] is True
    assert erg["konfig"]["zustand"] == "ok"
    assert erg["konfig"]["revision"] == 1 and erg["konfig"]["liste_id"] not in (ALT, None)  # neue Listen-ID und Revision 1
    k = hub.store.konfig
    assert k["zuordnungen"][UID] == {"ziel": SERIE, "name": "Rabe aus Holz"}  # Namen kommen mit
    assert k["gute_nacht"] == {"timer_min": 45, "ausblenden_s": 90}
    assert k["leise_zeiten"]["fenster"][0]["id"] == "nacht"
    assert (k["hinweis_pegel"], k["lesezeichen_tage"]) == (20, 30)
    msg = box_fabrik("box1").konfigs()[-1]
    assert msg["liste_id"] == k["liste_id"] and msg["revision"] == 1 and msg["lesezeichen_tage"] == 30
    assert msg["zuordnungen"][UID]["name"] == "Rabe aus Holz"
    # der Zustand ist ok, Änderungen gehen wieder, der Export zieht nach
    nas.serie("rabe", "rabe", "Rabe")
    await hub.medien.pruefen()
    assert (await hub.zuordnung_setzen(UID2, SERIE, ueberschreiben=True))["konfig"]["revision"] == 2
    await warte_auf(hass, lambda: hub.export_ok)
    exportiert = json.loads((nas.export / "config.json").read_text())
    assert exportiert["liste_id"] == k["liste_id"] and exportiert["revision"] == 2


async def test_d2_aus_export_bei_export_neuer(hass, starte_integration, box_fabrik, nas, vorab_speicher):
    vorab_speicher({"konfig": konfig(ALT, 3), "export_geschrieben_am": "2026-11-09T09:00:00Z"})
    schreibe_export(nas, konfig(ALT, 7, {UID2: {"ziel": SERIE}}))
    hub = await starte_integration()
    assert hub.store.zustand == "export_neuer"
    erg = await hub.konfig_aus_export()
    assert erg["konfig"]["zustand"] == "ok"
    assert list(hub.store.konfig["zuordnungen"]) == [UID2]  # der Export gewinnt


@pytest.mark.parametrize(
    "inhalt",
    [
        "kein json",
        '{"schema_version": 2, "revision": 1}',
        json.dumps({**konfig_zu_export(konfig(ALT, 3), "2026-11-09T12:00:00Z"), "lesezeichen_tage": 999}),
        json.dumps({**konfig_zu_export(konfig(ALT, 3), "2026-11-09T12:00:00Z"), "zuordnungen": {"XYZ": {"ziel": SERIE}}}),
        json.dumps({**konfig_zu_export(konfig(ALT, 3), "2026-11-09T12:00:00Z"), "schema_version": 3}),
    ],
)
async def test_d3_ungueltiger_export_uebernimmt_nichts(hass, starte_integration, nas, inhalt):
    (nas.export / "config.json").write_text(inhalt)
    hub = await starte_integration()  # Erststart ist ausgeschlossen: die Datei ist da, also ``leer_neu``
    assert hub.store.zustand == "leer_neu"
    with pytest.raises(TobiboxFehler) as err:
        await hub.konfig_aus_export()
    assert err.value.code == "export_ungueltig"
    assert hub.store.konfig is None and hub.store.zustand == "leer_neu"
    info = await hub.konfig_export_lesen()
    assert info["vorhanden"] is False


async def test_d4_ohne_export_datei(hass, starte_integration, nas, box_fabrik, vorab_speicher):
    vorab_speicher({"konfig": konfig(ALT, 3), "export_geschrieben_am": None, "war_konfiguriert": True})
    hub = await starte_integration()
    (nas.export / "config.json").unlink(missing_ok=True)
    with pytest.raises(TobiboxFehler) as err:
        await hub.konfig_aus_export()
    assert err.value.code == "export_nicht_gefunden"
    assert (await hub.konfig_export_lesen())["vorhanden"] is False


# --- (e) Box mit neuerem Stand ---


async def test_e_box_voraus_und_abweichung_ohne_automatische_erhoehung(hass, starte_integration, box_fabrik, nas, vorab_speicher, ereignisse_nach):
    vorab_speicher({"konfig": konfig(ALT, 3)})
    hub = await starte_integration()
    nas.serie("rabe", "rabe", "Rabe")
    await hub.medien.pruefen()
    ereignisse = ereignisse_nach(hub)
    b1 = box_fabrik("box1")
    await box_status(b1, konfig(ALT, 17))  # die Box hat aus der Zeit vor der Sicherung die Revision 17
    assert hub.box_objekt("box1")["konfig_stand"] == "voraus"
    abweichungen = [e["daten"] for e in ereignisse if e["thema"] == "konfig" and e["art"] == "abweichung"]
    assert abweichungen == [{"box": "box1", "grund": "voraus", "box_liste_id": ALT, "box_revision": 17, "ha_revision": 3}]
    assert hub.store.konfig["revision"] == 3  # die Integration erhöht die Revision nie von selbst
    # eine Änderung veröffentlicht Revision 4 mit der alten Listen-ID: die Box lehnt sie ab (Revisionsregel) ...
    await hub.zuordnung_setzen(UID2, SERIE)
    msg = b1.konfigs()[-1]
    assert (msg["liste_id"], msg["revision"]) == (ALT, 4)
    assert box_nimmt_an({"liste_id": ALT, "revision": 17}, msg) is False
    # ... und meldet es als Ereignis; HA zeigt die Abweichung
    await b1.ereignis("liste_abgelehnt", {"liste_id": ALT, "revision": 4, "gespeichert_liste_id": ALT, "gespeichert_revision": 17, "grund": "revision_zu_niedrig"})
    assert [e["daten"]["grund"] for e in ereignisse if e["art"] == "abweichung"] == ["voraus", "revision_zu_niedrig"]
    # der Ausweg: Liste neu ausrollen (neue Listen-ID), alle Boxen nehmen sie an
    erg = await hub.liste_neu_ausrollen()
    neu = b1.konfigs()[-1]
    assert neu["liste_id"] != ALT and neu["revision"] == 1 and erg["konfig"]["revision"] == 1
    assert box_nimmt_an({"liste_id": ALT, "revision": 17}, neu) is True
    assert neu["zuordnungen"] == msg["zuordnungen"]  # gleiche Zuordnungen und Einstellungen


def box_nimmt_an(box: dict[str, Any], msg: dict[str, Any]) -> bool:
    """Die Revisionsregel auf der Box (``mqtt-v1.md``, 5.2)."""
    if msg["liste_id"] != box["liste_id"]:
        return True
    return msg["revision"] > box["revision"]


async def test_e2_wiederherstellung_mit_neuer_listen_id_und_niedriger_revision(hass, starte_integration, box_fabrik, nas, vorab_speicher):
    """Eine Sicherung mit anderer Listen-ID: die Boxen nehmen die Liste trotz niedriger Revision an."""
    vorab_speicher({"konfig": konfig(NEU, 2)})
    hub = await starte_integration()
    nas.serie("rabe", "rabe", "Rabe")
    await hub.medien.pruefen()
    b1 = box_fabrik("box1")
    await box_status(b1, konfig(ALT, 17))
    assert hub.box_objekt("box1")["konfig_stand"] == "veraltet"  # andere Listen-ID: veraltet, nicht voraus
    await hub.zuordnung_setzen(UID2, SERIE)
    msg = b1.konfigs()[-1]
    assert (msg["liste_id"], msg["revision"]) == (NEU, 3)
    assert box_nimmt_an({"liste_id": ALT, "revision": 17}, msg) is True


# --- (f) Export schlägt fehl ---


async def test_f_export_fehler_befehl_gelingt_wiederholung_und_meldung(hass, integration, nas, monkeypatch, ereignisse):
    hub = integration
    await warte_auf(hass, lambda: hub.export_ok)
    nas.serie("rabe", "rabe", "Rabe")
    await hub.medien.pruefen()
    echt = hub_modul.schreibe_export
    versuche = {"n": 0}

    def kaputt(ordner, k, am):
        versuche["n"] += 1
        if versuche["n"] <= 2:
            raise OSError("NAS im Standby")
        return echt(ordner, k, am)

    monkeypatch.setattr(hub_modul, "schreibe_export", kaputt)
    erg = await hub.zuordnung_setzen(UID, SERIE)
    assert erg["geaendert"] is True and erg["veroeffentlicht"] is True  # der Befehl bricht nie ab
    assert erg["konfig"]["export_ok"] is False
    await warte_auf(hass, lambda: hub._export_fehler_seit is not None, block=False)
    fehler = [e for e in ereignisse if e["thema"] == "konfig" and e["art"] == "export_fehler"]
    assert len(fehler) == 1 and fehler[0]["daten"]["seit"].endswith("Z")
    assert "Export" in fehler[0]["daten"]["text"]
    assert "tobibox_export" in persistent_notification._async_get_or_create_notifications(hass)
    assert hub.konfig_stand()["export_ok"] is False
    await warte_auf(hass, lambda: hub.export_ok, versuche=300)  # nach 10 s, 60 s, … im Test nach 0,02 s
    assert versuche["n"] == 3
    ok = [e for e in ereignisse if e["thema"] == "konfig" and e["art"] == "export_ok"]
    assert len(ok) == 1 and ok[0]["daten"]["export_geschrieben_am"].endswith("Z")
    assert "tobibox_export" not in persistent_notification._async_get_or_create_notifications(hass)
    assert json.loads((nas.export / "config.json").read_text())["revision"] == 2
    assert hub.konfig_stand()["export_ok"] is True and hub.konfig_stand()["export_geschrieben_am"]


async def test_f2_neuere_revision_ersetzt_den_wartenden_export(hass, integration, nas, monkeypatch):
    hub = integration
    await warte_auf(hass, lambda: hub.export_ok)
    nas.serie("rabe", "rabe", "Rabe")
    await hub.medien.pruefen()
    echt = hub_modul.schreibe_export
    sperre = {"offen": False}

    def mal_so(ordner, k, am):
        if not sperre["offen"]:
            raise OSError("weg")
        return echt(ordner, k, am)

    monkeypatch.setattr(hub_modul, "schreibe_export", mal_so)
    await hub.zuordnung_setzen(UID, SERIE)
    await hub.zuordnung_setzen(UID2, SERIE)
    sperre["offen"] = True
    await warte_auf(hass, lambda: hub.export_ok, versuche=300)
    assert json.loads((nas.export / "config.json").read_text())["revision"] == 3  # die neueste Revision steht im Export


# --- (g) Liste neu ausrollen nach der Wiederherstellung ---


async def test_g_liste_neu_ausrollen_aus_leer_neu_beginnt_mit_leerer_liste(hass, starte_integration, box_fabrik, nas):
    schreibe_export(nas, konfig(ALT, 17))
    hub = await start_mit_status(hass, starte_integration, box_fabrik, konfig(ALT, 17))
    assert hub.store.zustand == "leer_neu"
    erg = await hub.liste_neu_ausrollen()
    assert erg["konfig"]["zustand"] == "ok" and erg["konfig"]["revision"] == 1 and erg["veroeffentlicht"] is True
    msg = box_fabrik("box1").konfigs()[-1]
    assert msg["zuordnungen"] == {} and msg["liste_id"] != ALT  # alle Tobies verlieren ihre Zuordnung
    assert msg["leise_zeiten"] == {"zeitzone": "Europe/Berlin", "fenster": []} and msg["gute_nacht"] == {"timer_min": 30, "ausblenden_s": 60}
    await warte_auf(hass, lambda: hub.export_ok)
    assert json.loads((nas.export / "config.json").read_text())["liste_id"] == msg["liste_id"]  # der Export folgt dem neuen Stand


async def test_g2_liste_neu_ausrollen_aus_export_neuer_behaelt_den_stand_von_ha(hass, starte_integration, box_fabrik, nas, vorab_speicher):
    vorab_speicher({"konfig": konfig(ALT, 3, {UID: {"ziel": SERIE, "name": "Rabe"}}), "export_geschrieben_am": "2026-11-09T09:00:00Z"})
    schreibe_export(nas, konfig(ALT, 7, {UID2: {"ziel": SERIE}}))
    hub = await starte_integration()
    assert hub.store.zustand == "export_neuer"
    erg = await hub.liste_neu_ausrollen()
    assert erg["konfig"]["zustand"] == "ok"
    assert hub.store.konfig["zuordnungen"] == {UID: {"ziel": SERIE, "name": "Rabe"}}
    await warte_auf(hass, lambda: hub.export_ok)
    assert list(json.loads((nas.export / "config.json").read_text())["zuordnungen"]) == [UID]


async def test_g3_neu_ausrollen_ist_in_jedem_zustand_erlaubt_und_speichert(hass, integration, hass_storage):
    hub = integration
    alt = hub.store.konfig["liste_id"]
    for zustand in ("ok", "leer_neu", "export_neuer"):
        hub.store.zustand = zustand
        await hub.liste_neu_ausrollen()
        assert hub.store.zustand == "ok"
    assert gespeicherte_konfig(hass_storage)["liste_id"] == hub.store.liste_id != alt


# --- Speicher: Erststart legt Konfig sofort ab ---


async def test_storage_enthaelt_konfig_nach_erststart(hass, integration, hass_storage):
    k = gespeicherte_konfig(hass_storage)
    assert k["revision"] == 1 and k["liste_id"] == integration.store.liste_id


@pytest.fixture
def ereignisse_nach():
    """``ereignisse_nach(hub)`` abonniert alle Ereignisse und gibt die gesammelte Liste zurück."""
    from custom_components.tobibox.const import EREIGNIS_THEMEN
    from custom_components.tobibox.hub import Abo

    def abonniere(hub) -> list[dict[str, Any]]:
        liste: list[dict[str, Any]] = []

        class Verbindung:
            user = None

            def send_message(self, nachricht: dict[str, Any]) -> None:
                liste.append(nachricht["event"])

        hub.abo_hinzu(Abo(Verbindung(), 1, set(EREIGNIS_THEMEN), None))
        return liste

    return abonniere


def _jetzt() -> str:  # pragma: no cover
    return jetzt_iso()
