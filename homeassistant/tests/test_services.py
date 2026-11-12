"""HA-Aktionen (``services.yaml``): dieselben Backend-Funktionen wie die Seite (Vertrag W, Abschnitt 1)."""

from __future__ import annotations

from unittest.mock import ANY

import pytest
import voluptuous as vol
from homeassistant.exceptions import ServiceValidationError

from custom_components.tobibox.const import DOMAIN

UID = "e0040312345678ab"
UID2 = "04a1b2c3"
SERIE = {"typ": "serie", "serie": "rabe"}
FOLGE = {"typ": "folge", "serie": "rabe", "folge": "a.mp3"}


@pytest.fixture
async def dienste(hass, integration, nas, lege_mp3, box_fabrik):
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3", "b.mp3"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    await integration.medien.pruefen()
    await box_fabrik("box1").online()

    async def ruf(aktion: str, /, **daten):
        return await hass.services.async_call(DOMAIN, aktion, daten, blocking=True)

    return ruf


async def test_zuordnen_und_loesen(hass, dienste, integration, box_fabrik):
    await dienste("zuordnen", uid=UID, typ="serie", serie_id="rabe", name="Rabe aus Holz")
    # Vertrag W 12.11., angelegt_am: Anlegen setzt den Zeitstempel
    assert integration.store.konfig["zuordnungen"][UID] == {"ziel": SERIE, "name": "Rabe aus Holz", "angelegt_am": ANY}
    assert box_fabrik("box1").konfigs()[-1]["zuordnungen"][UID]["ziel"] == SERIE  # derselbe Weg: Revision, Veröffentlichung
    await dienste("zuordnen", uid=UID2, typ="folge", serie_id="rabe", folge="a.mp3")
    await dienste("zuordnen", uid="04ffeedd", typ="aktion", aktion="gute_nacht")
    assert integration.store.konfig["zuordnungen"]["04ffeedd"]["ziel"] == {"typ": "aktion", "aktion": "gute_nacht"}
    # ohne Seite: ein anderes Ziel ersetzt nur mit ueberschreiben=true
    with pytest.raises(ServiceValidationError) as err:
        await dienste("zuordnen", uid=UID, typ="folge", serie_id="rabe", folge="b.mp3")
    assert err.value.translation_key == "zuordnung_existiert"
    await dienste("zuordnen", uid=UID, typ="folge", serie_id="rabe", folge="b.mp3", ueberschreiben=True)
    assert integration.store.konfig["zuordnungen"][UID]["ziel"]["folge"] == "b.mp3"
    assert integration.store.konfig["zuordnungen"][UID]["name"] == "Rabe aus Holz"  # der Name bleibt
    await dienste("loesen", uid=UID)
    assert UID not in integration.store.konfig["zuordnungen"]


async def test_dienst_fehler_werden_zu_service_validation_error(hass, dienste):
    with pytest.raises(ServiceValidationError) as err:
        await dienste("zuordnen", uid=UID, typ="serie", serie_id="gibtsnicht")
    assert err.value.translation_key == "serie_nicht_gefunden" and err.value.translation_domain == DOMAIN
    with pytest.raises(ServiceValidationError) as err:
        await dienste("zuordnen", uid="ZZ", typ="serie", serie_id="rabe")
    assert err.value.translation_key == "kennung_ungueltig"
    with pytest.raises(ServiceValidationError) as err:
        await dienste("papierkorb_leeren", bestaetigt=False)
    assert err.value.translation_key == "invalid_format"
    with pytest.raises(ServiceValidationError) as err:
        await dienste("liste_neu_ausrollen", bestaetigt=False)
    assert err.value.translation_key == "invalid_format"
    with pytest.raises(Exception):  # Schema: fehlendes Pflichtfeld
        await dienste("zuordnen", typ="serie")


async def test_lernmodus_starten_und_abbrechen(hass, dienste, integration, box_fabrik):
    box = box_fabrik("box1")
    await dienste("lernmodus_starten", box="box1", typ="serie", serie_id="rabe", name="Rabe")
    cmd = box.befehle("lernen")[0]
    v = integration.lernmodus.offener_vorgang("box1")
    assert v.befehl_id == cmd["id"] and v.name == "Rabe" and v.auto_ueberschreiben is False
    await dienste("lernmodus_abbrechen", box="box1")
    assert [c["befehl"] for c in box.befehle()] == ["lernen", "lernen_abbrechen"]
    with pytest.raises(ServiceValidationError) as err:
        await dienste("lernmodus_starten", box="box1", typ="aktion")
    assert err.value.translation_key == "ziel_ungueltig"


async def test_lernmodus_starten_nimmt_die_vorbelegung_der_box(hass, dienste, integration, box_fabrik):
    box = box_fabrik("box1")
    with pytest.raises(ServiceValidationError) as err:  # weder serie_id noch Auswahl
        await dienste("lernmodus_starten", box="box1", typ="serie")
    assert err.value.translation_key == "serie_nicht_gefunden"
    await box.ui("lern_serie", "Der kleine Rabe")
    await dienste("lernmodus_starten", box="box1", typ="serie")
    assert integration.lernmodus.offener_vorgang("box1").ziel == SERIE


async def test_lernmodus_aktion_ueberschreiben_true_ersetzt_ohne_rueckfrage(hass, dienste, integration, box_fabrik):
    box = box_fabrik("box1")
    await dienste("zuordnen", uid=UID, typ="folge", serie_id="rabe", folge="a.mp3")
    await dienste("lernmodus_starten", box="box1", typ="serie", serie_id="rabe", ueberschreiben=True)
    v = integration.lernmodus.offener_vorgang("box1")
    await box.unbekannt(UID, art="gelernt", befehl_id=v.befehl_id)
    assert integration.store.konfig["zuordnungen"][UID]["ziel"] == SERIE
    assert box.acks(UID)[-1]["grund"] == "zugeordnet"


async def test_serien_und_folgen_dienste(hass, dienste, integration, nas):
    await dienste("serie_anlegen", name="Zweite Serie")
    zweite = next(s for s in integration.medien.serien.values() if s.serie.name == "Zweite Serie")
    await dienste("serie_umbenennen", serie_id=zweite.serie.id, name="Zweite Serie, neu")
    assert integration.medien.serien[zweite.serie.id].serie.name == "Zweite Serie, neu"
    await dienste("folge_umbenennen", serie_id="rabe", folge="a.mp3", name="Folge Eins")
    assert nas.serie_json("rabe")["folgen_info"]["a.mp3"]["anzeige"] == "Folge Eins"
    await dienste("folgen_sortieren", serie_id="rabe", folgen=["b.mp3", "a.mp3"])
    assert nas.serie_json("rabe")["folgen"] == ["b.mp3", "a.mp3"]
    await dienste("folge_verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id=zweite.serie.id)
    assert (nas.medien / zweite.ordner / "a.mp3").exists()
    await dienste("folge_loeschen", serie_id="rabe", folge="b.mp3")
    assert (await integration.medien.papierkorb_liste(100, 0))["gesamt"] == 1
    await dienste("serien_zusammenfuehren", quelle_id="rabe", ziel_id=zweite.serie.id)
    assert not (nas.medien / "rabe").exists()
    await dienste("serie_loeschen", serie_id=zweite.serie.id)
    assert (await integration.medien.papierkorb_liste(100, 0))["gesamt"] == 3
    await dienste("papierkorb_leeren", bestaetigt=True)
    assert (await integration.medien.papierkorb_liste(100, 0))["gesamt"] == 0


async def test_loeschen_mit_tobies_ohne_bestaetigung_wird_abgelehnt(hass, dienste, integration):
    await dienste("zuordnen", uid=UID, typ="folge", serie_id="rabe", folge="a.mp3")
    with pytest.raises(ServiceValidationError) as err:
        await dienste("folge_loeschen", serie_id="rabe", folge="a.mp3")
    assert err.value.translation_key == "tobies_betroffen"
    await dienste("folge_loeschen", serie_id="rabe", folge="a.mp3", tobies_bestaetigt=True)
    assert UID in integration.store.konfig["zuordnungen"]  # die Zuordnung bleibt


async def test_sync_update_ausrollen_eingang(hass, dienste, integration, box_fabrik, nas):
    box = box_fabrik("box1")
    await dienste("sync_anstossen", box="box1")
    assert [c["befehl"] for c in box.befehle()] == ["sync"]
    with pytest.raises(ServiceValidationError) as err:
        await dienste("update_anstossen", box="box1")
    assert err.value.translation_key == "keine_version"
    (nas.releases / "tobibox-1.3.0.tar.gz").write_bytes(b"x")
    await dienste("update_anstossen", box="box1")
    assert box.befehle("update")[0]["daten"] == {"version": "1.3.0"}
    with pytest.raises(ServiceValidationError) as err:
        await dienste("sync_anstossen", box="box2")
    assert err.value.translation_key == "box_offline"
    alt = integration.store.liste_id
    await dienste("liste_neu_ausrollen", bestaetigt=True)
    assert integration.store.liste_id != alt
    await dienste("eingang_einsortieren", sofort=True)
    await hass.async_block_till_done()


# --------------------------------------------------------------------------
# Sicherheitsbefund U1: alle Aktionen ändern etwas, also nur für Administratoren
# --------------------------------------------------------------------------


async def test_alle_aktionen_sind_admin_aktionen(hass, dienste, hass_read_only_user):
    """Keine Aktion der Integration ist offen registriert (Prüfung über die Dienste-Registry)."""
    namen = set(hass.services.async_services_internal()[DOMAIN])
    assert "papierkorb_leeren" in namen and "serie_loeschen" in namen and "liste_neu_ausrollen" in namen
    from homeassistant.core import Context
    from homeassistant.exceptions import Unauthorized

    # Ein Benutzer ohne Adminrechte darf keine einzige Aktion rufen (HA prüft zuerst das Schema, dann das Recht: mit leeren Daten kommt
    # je nach Aktion ``Invalid`` oder ``Unauthorized``; nie darf ein Aufruf durchgehen. Genau ``Unauthorized`` prüft der nächste Test)
    nutzer = hass_read_only_user
    for name in sorted(namen):
        with pytest.raises((Unauthorized, vol.Invalid)):
            await hass.services.async_call(DOMAIN, name, {}, blocking=True, context=Context(user_id=nutzer.id))


@pytest.mark.parametrize(
    ("aktion", "daten"),
    [
        ("serie_loeschen", {"serie_id": "rabe"}),
        ("papierkorb_leeren", {"bestaetigt": True}),
        ("liste_neu_ausrollen", {"bestaetigt": True}),
        ("sync_anstossen", {"box": "box1"}),
        ("update_anstossen", {"box": "box1"}),
        ("serie_anlegen", {"name": "Neu"}),
        ("loesen", {"uid": UID}),
    ],
)
async def test_nicht_admin_darf_aendernde_aktion_nicht(hass, dienste, integration, hass_read_only_user, aktion, daten):
    from homeassistant.core import Context
    from homeassistant.exceptions import Unauthorized

    vorher = dict(integration.store.konfig)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(DOMAIN, aktion, daten, blocking=True, context=Context(user_id=hass_read_only_user.id))
    assert integration.store.konfig == vorher and "rabe" in integration.medien.serien


async def test_admin_darf_aendernde_aktion(hass, dienste, integration, box_fabrik, hass_admin_user):
    from homeassistant.core import Context

    await hass.services.async_call(
        DOMAIN, "sync_anstossen", {"box": "box1"}, blocking=True, context=Context(user_id=hass_admin_user.id)
    )
    assert [c["befehl"] for c in box_fabrik("box1").befehle()] == ["sync"]
