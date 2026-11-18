"""Papierkorb leert sich nach 30 Tagen (BB1; Vertrag W, Nr. 12 „Automatik“, data-model 9 „Aufbewahrung“)."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.tobibox.const import DOMAIN, PAPIERKORB_TAGE
from custom_components.tobibox.fehler import TobiboxFehler
from custom_components.tobibox.util import iso, jetzt

import pytest


async def _zwei_folgen(hub, nas, lege_mp3):
    pfad = nas.serie("o", "id1", "Rabe", ["a.mp3", "b.mp3", "c.mp3"])
    for n in ("a", "b", "c"):
        lege_mp3(pfad / f"{n}.mp3")
    await hub.medien.pruefen()
    return [(await hub.medien.folge_loeschen("id1", f"{n}.mp3", False, None))["eintrag"]["id"] for n in ("a", "b", "c")]


def _datiere(nas, eid, tage):
    """Setzt ``geloescht_am`` des Eintrags auf vor ``tage`` Tagen (``None``: Feld entfernen, ``"kaputt"``: Unsinn)."""
    datei = nas.papierkorb / eid / "meta.json"
    meta = json.loads(datei.read_text())
    if tage is None:
        meta.pop("geloescht_am", None)
    elif tage == "kaputt":
        meta["geloescht_am"] = "gestern"
    else:
        meta["geloescht_am"] = iso(jetzt() - timedelta(days=tage))
    datei.write_text(json.dumps(meta))


def test_konstante():
    assert PAPIERKORB_TAGE == 30


async def test_alt_und_neu_gemischt(hass, integration, nas, lege_mp3, ereignisse):
    hub = integration
    alt, grenze_knapp, neu = await _zwei_folgen(hub, nas, lege_mp3)
    _datiere(nas, alt, 31)
    _datiere(nas, grenze_knapp, 29)
    ereignisse.clear()
    erg = await hub.medien.papierkorb_aufbewahrung()
    assert erg["geloescht"] == 1 and erg["freigegeben_bytes"] > 0
    assert not (nas.papierkorb / alt).exists()
    assert (nas.papierkorb / grenze_knapp).exists() and (nas.papierkorb / neu).exists()
    assert [e["art"] for e in ereignisse if e.get("thema") == "medien"].count("papierkorb_geaendert") == 1


async def test_ohne_datum_und_unvollstaendig_bleiben(hass, integration, nas, lege_mp3):
    hub = integration
    ohne, kaputt, _ = await _zwei_folgen(hub, nas, lege_mp3)
    _datiere(nas, ohne, None)
    _datiere(nas, kaputt, "kaputt")
    unvollst = nas.papierkorb / "0123456789ab"
    (unvollst / "inhalt").mkdir(parents=True)  # meta.json fehlt
    (unvollst / "inhalt" / "x.mp3").write_bytes(b"x")
    ohne_inhalt = nas.papierkorb / "ba9876543210"
    ohne_inhalt.mkdir()
    (ohne_inhalt / "meta.json").write_text(json.dumps({"id": "ba9876543210", "geloescht_am": iso(jetzt() - timedelta(days=99))}))
    erg = await hub.medien.papierkorb_aufbewahrung()
    assert erg["geloescht"] == 0
    assert (nas.papierkorb / ohne).exists() and (nas.papierkorb / kaputt).exists()
    assert unvollst.exists() and ohne_inhalt.exists()


async def test_freigabe_nicht_erreichbar_laeuft_aus(hass, integration, nas, lege_mp3, caplog):
    hub = integration
    alt = (await _zwei_folgen(hub, nas, lege_mp3))[0]
    _datiere(nas, alt, 40)
    with patch.object(type(hub.medien), "_medien_erreichbar", side_effect=TobiboxFehler("medien_nicht_erreichbar")):
        with pytest.raises(TobiboxFehler):
            await hub.medien.papierkorb_aufbewahrung()
        await hub._timer_papierkorb(None)  # der Zeitgeber fängt den Fehler ab
    assert (nas.papierkorb / alt).exists()


async def test_ereignis_nur_bei_wirkung(hass, integration, nas, lege_mp3, ereignisse):
    hub = integration
    await _zwei_folgen(hub, nas, lege_mp3)
    ereignisse.clear()
    assert (await hub.medien.papierkorb_aufbewahrung())["geloescht"] == 0
    assert [e for e in ereignisse if e.get("art") == "papierkorb_geaendert"] == []


async def test_protokollzeile_mit_anzahl_und_bytes(hass, integration, nas, lege_mp3, caplog):
    hub = integration
    alt = (await _zwei_folgen(hub, nas, lege_mp3))[0]
    _datiere(nas, alt, 45)
    caplog.set_level("INFO")
    erg = await hub.medien.papierkorb_aufbewahrung()
    zeilen = [r.getMessage() for r in caplog.records if "endgültig gelöscht" in r.getMessage()]
    assert len(zeilen) == 1 and f"({erg['freigegeben_bytes']} Bytes)" in zeilen[0] and zeilen[0].startswith("Papierkorb: 1 ")


async def test_zeitgeber_tag_und_start_und_entladen(hass, starte_integration, nas):
    hub = await starte_integration()
    lauf = AsyncMock(return_value={"geloescht": 0, "freigegeben_bytes": 0})
    with patch.object(hub.medien, "papierkorb_aufbewahrung", lauf):
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=300))  # „kurz nach dem Start“
        await hass.async_block_till_done()
        assert lauf.await_count == 1
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(days=1, minutes=1))  # der Tageslauf
        await hass.async_block_till_done()
        assert lauf.await_count == 2
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert hub._timer == set()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(days=3))
        await hass.async_block_till_done()
        assert lauf.await_count == 2  # beendet: kein Lauf mehr
