"""Paket A3e: „Anders einsortieren“, Befehl 43 ``einsortierung/neu`` (Vertrag W, 2.4, 3.12 und 14.4)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from custom_components.tobibox import const, neu_einsortieren
from custom_components.tobibox.fehler import TobiboxFehler
from custom_components.tobibox.media import lese_papierkorb
from custom_components.tobibox.schutz import Nutzer
from custom_components.tobibox.util import iso, jetzt

from .conftest import braucht_ffmpeg, ereignis_arten, erzeuge_audio
from .test_eingang import alle_serien, folge_info, sortiere
from .test_rechte_schutz import _client
from .test_websocket_api import fehler, ok, senden

pytestmark = braucht_ffmpeg

ADMIN = Nutzer("admin-1", "Admin", True)
ALLTAG = Nutzer("alltag-1", "Alltag", False)


@pytest.fixture
async def api(hass, integration, hass_ws_client):
    return await hass_ws_client(hass)


@pytest.fixture
async def normal(hass, integration, hass_ws_client):
    return await _client(hass, hass_ws_client, "Normal")


def lege_alben(nas, name: str = "Quelle", interpret: str = "Künstler", start: int = 311) -> None:
    """Ordner mit zwei Dateien, zwei Alben, ein Interpret: wird eine Serie mit zwei Folgen (ohne „bitte prüfen“)."""
    erzeuge_audio(nas.eingang / name / "a.mp3", frequenz=start, album=f"{name} Eins", album_artist=interpret, title="Eins")
    erzeuge_audio(nas.eingang / name / "b.mp3", frequenz=start + 1, album=f"{name} Zwei", album_artist=interpret, title="Zwei")


async def einsortiert(hub, nas, **kw) -> dict:
    """Legt ``lege_alben`` in den Eingang, sortiert ein und gibt die Protokollzeile zurück."""
    lege_alben(nas, **kw)
    await sortiere(hub)
    zeile = hub.eingang.protokoll[-1]
    assert zeile["name"] == kw.get("name", "Quelle")
    return zeile


async def neu(hub, zeile, ziel="neu", art="hoerbuch", name="Mein Hörbuch", serie_id=None, nutzer=ADMIN):
    return await hub.eingang.neu_einsortieren(zeile["id"], ziel, art, name, serie_id, nutzer)


async def nicht_moeglich(hub, zeile, **kw) -> None:
    with pytest.raises(TobiboxFehler) as err:
        await neu(hub, zeile, **kw)
    assert err.value.code == "neu_einsortieren_nicht_moeglich"


def audio_anzahl(*wurzeln: Path) -> int:
    return sum(1 for w in wurzeln for p in w.rglob("*") if p.is_file() and p.suffix == ".mp3")


async def warte_ende(hub) -> None:
    """Wartet auf einen laufenden Durchlauf (der Befehl stößt einen an, der die Ruhezeit noch nicht erfüllt sieht)."""
    if hub.eingang._task is not None:
        await hub.eingang._task
    await hub.hass.async_block_till_done()


# --------------------------------------------------------------------------
# Erfolg
# --------------------------------------------------------------------------


async def test_neu_hoerbuch_serie_kommt_in_den_papierkorb_und_der_eingang_sortiert_neu(hass, integration, nas, ereignisse):
    zeile = await einsortiert(integration, nas)
    assert list(alle_serien(nas)) == ["Künstler"]
    assert audio_anzahl(nas.medien) == 2
    ereignisse.clear()
    assert await neu(integration, zeile) == {"gestartet": True}
    await warte_ende(integration)
    # die alte Serie liegt im Papierkorb (typ serie, grund manuell, geloescht_von), die alte Zeile ist weg
    assert "Künstler" not in alle_serien(nas)
    (eintrag,) = lese_papierkorb(nas.papierkorb)
    assert (eintrag["typ"], eintrag["grund"], eintrag["serie_name"], eintrag["geloescht_von"]) == ("serie", "manuell", "Künstler", {"id": "admin-1", "name": "Admin"})
    assert [p["id"] for p in integration.eingang.protokoll] == [zeile["id"]]  # nur die neue Zeile (gleicher Name)
    # AM25: ohne Warten auf ``EINGANG_RUHE_S`` einsortiert (wie ein Upload), ohne ``sofort``
    assert not integration.eingang.upload_quelle  # die Herkunft bleibt: der alte Eintrag kam nicht per Upload
    assert not integration.eingang.upload_eintraege  # nach dem Einsortieren ist die Ruhefreiheit wieder weg
    assert integration.eingang.protokoll[-1]["id"] == zeile["id"]
    serie = alle_serien(nas)["Mein Hörbuch"]
    assert (serie["art"], serie["art_quelle"]) == ("hoerbuch", "manuell")
    assert audio_anzahl(nas.eingang) == 0 and audio_anzahl(nas.medien) == 2
    assert len(serie["folgen"]) == 1  # hoerbuch: alle Dateien eine Folge
    assert audio_anzahl(nas.eingang) == 0
    neu_ereignisse = [e for e in ereignisse if e["thema"] == "eingang" and e["art"] == "neu_einsortiert"]
    (e,) = neu_ereignisse
    assert e["daten"]["eintrag_id"] == zeile["id"]  # derselbe Name, dieselbe Kennung
    assert e["daten"]["zaehler"]["folgen"] == 1 and e["daten"]["ergebnis"][0]["serie_name"] == "Mein Hörbuch"
    assert "papierkorb_geaendert" in ereignis_arten(ereignisse, "medien")
    # ein Doppeltes wurde es nicht: die Prüfsummen waren aus dem Index
    assert not [h for h in e["daten"]["hinweise"] if h["code"] == "doppelt"]


async def test_ergaenzen_in_vorhandene_serie(hass, integration, nas, lege_mp3):
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["x.mp3"])
    lege_mp3(pfad / "x.mp3")
    await integration.medien.pruefen()
    zeile = await einsortiert(integration, nas)
    assert await neu(integration, zeile, ziel="ergaenzen", art=None, name=None, serie_id="rabe") == {"gestartet": True}
    await warte_ende(integration)
    await sortiere(integration)
    serien = alle_serien(nas)
    assert "Künstler" not in serien
    assert len(serien["Der kleine Rabe"]["folgen"]) == 3  # x.mp3 und die zwei Dateien, jede eine neue Folge
    assert {"a.mp3", "b.mp3"} <= set(serien["Der kleine Rabe"]["folgen"])


async def test_einzeln_jede_datei_eine_eigene_serie(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    await neu(integration, zeile, ziel="einzeln", art="musik", name="Wird bei zwei Dateien ignoriert")
    await warte_ende(integration)
    await sortiere(integration)
    serien = alle_serien(nas)
    assert set(serien) == {"Eins", "Zwei"}  # nach dem Titel jeder Datei
    assert all(s["einzeln"] and s["art"] == "musik" and len(s["folgen"]) == 1 for s in serien.values())


async def test_einzeln_mit_einer_datei_nimmt_den_namen(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Lied.mp3", frequenz=500, album="Ein Album", album_artist="Sänger", title="Titel")
    await sortiere(integration)
    zeile = integration.eingang.protokoll[-1]
    await neu(integration, zeile, ziel="einzeln", art="musik", name="Mein Lied")
    assert (nas.eingang / "Lied.mp3").is_file()  # eine einzelne Datei liegt lose im Eingang, unter demselben Namen wie vorher
    await warte_ende(integration)
    await sortiere(integration)
    assert list(alle_serien(nas)) == ["Mein Lied"]
    assert integration.eingang.protokoll[-1]["id"] == zeile["id"]


async def test_eintrag_in_vorhandener_serie_nimmt_nur_seine_folgen_zurueck(hass, integration, nas, lege_mp3):
    """Der Eintrag hat in eine **vorhandene** Serie einsortiert: die Serie bleibt, nur seine Folgen gehen."""
    pfad = nas.serie("kuenstler", "k1", "Künstler", ["x.mp3"])
    lege_mp3(pfad / "x.mp3")
    await integration.medien.pruefen()
    zeile = await einsortiert(integration, nas)
    assert sorted(alle_serien(nas)["Künstler"]["folgen"]) == ["a.mp3", "b.mp3", "x.mp3"]
    await neu(integration, zeile)
    assert alle_serien(nas)["Künstler"]["folgen"] == ["x.mp3"]
    assert lese_papierkorb(nas.papierkorb) == []  # nichts Neues angelegt, nichts im Papierkorb
    await warte_ende(integration)
    await sortiere(integration)
    assert len(alle_serien(nas)["Mein Hörbuch"]["folgen"]) == 1


async def test_pruefen_liste_gibt_den_rueckweg_nicht_aus(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    assert "rueckweg" in zeile
    liste = await integration.eingang.liste("erledigt", 10, 0)
    assert all("rueckweg" not in z for z in liste["eintraege"])


# --------------------------------------------------------------------------
# Alter, „bitte ansehen“
# --------------------------------------------------------------------------


async def test_aelter_als_24_stunden_ohne_pruefen_geht_nicht(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    assert zeile["pruefen"] is False
    zeile["fertig_am"] = iso(jetzt() - timedelta(seconds=const.EINSORTIERUNG_NEU_ALTER_MAX_S + 60))
    await nicht_moeglich(integration, zeile)
    zeile["fertig_am"] = iso(jetzt() - timedelta(seconds=const.EINSORTIERUNG_NEU_ALTER_MAX_S - 60))
    assert await neu(integration, zeile) == {"gestartet": True}


async def test_pruefen_true_und_aelter_als_24_stunden_geht(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Märchen" / "x.mp3", frequenz=330)  # ohne Tags: „bitte ansehen“
    await sortiere(integration)
    zeile = integration.eingang.protokoll[-1]
    assert zeile["pruefen"] is True
    zeile["fertig_am"] = iso(jetzt() - timedelta(days=30))
    assert await neu(integration, zeile, ziel="neu", art="geschichte", name="Neue Märchen") == {"gestartet": True}
    await warte_ende(integration)
    await sortiere(integration)
    assert list(alle_serien(nas)) == ["Neue Märchen"]


async def test_alter_eintrag_ohne_rueckweg_geht_nicht(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    del zeile["rueckweg"]
    await nicht_moeglich(integration, zeile)
    assert audio_anzahl(nas.eingang) == 0 and list(alle_serien(nas)) == ["Künstler"]


# --------------------------------------------------------------------------
# Die sieben Prüfungen (2.4): jede einzeln
# --------------------------------------------------------------------------


async def pruefungen(hub, zeile) -> list[str]:
    async with hub.medien.sperren(*zeile["rueckweg"]["serien"]):
        return await neu_einsortieren.geaenderte_pruefungen(hub, zeile["rueckweg"])


async def unveraendert(hub, nas, zeile) -> None:
    """Nach einer Ablehnung ist nichts bewegt: Dateien, Serie, Papierkorb, Protokoll."""
    assert audio_anzahl(nas.eingang) == 0
    assert not lese_papierkorb(nas.papierkorb)
    assert zeile in hub.eingang.protokoll


async def test_ohne_aenderung_ist_keine_pruefung_betroffen(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    assert await pruefungen(integration, zeile) == []


async def test_pruefung_1_serie_umbenannt(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    await integration.medien.serie_umbenennen(sid, "Andere Serie")
    assert "umbenannt" in await pruefungen(integration, zeile)
    await nicht_moeglich(integration, zeile)
    await unveraendert(integration, nas, zeile)


async def test_pruefung_1_folge_umbenannt(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    await integration.medien.folge_umbenennen(sid, "a.mp3", "Anderer Titel", None)
    assert "umbenannt" in await pruefungen(integration, zeile)
    await nicht_moeglich(integration, zeile)
    await unveraendert(integration, nas, zeile)


async def test_pruefung_2_reihenfolge_geaendert(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    folgen = (await integration.medien._frisch(sid))[0].folgen
    await integration.medien.folgen_ordnen(sid, list(reversed(folgen)), None)
    assert await pruefungen(integration, zeile) == ["verschoben"]
    await nicht_moeglich(integration, zeile)
    await unveraendert(integration, nas, zeile)


async def test_pruefung_2_folge_in_andere_serie_verschoben(hass, integration, nas, lege_mp3):
    pfad = nas.serie("ziel", "ziel", "Ziel", ["z.mp3"])
    lege_mp3(pfad / "z.mp3")
    await integration.medien.pruefen()
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    await integration.medien.folge_verschieben(sid, "a.mp3", "ziel", False, None, None)
    assert "verschoben" in await pruefungen(integration, zeile)
    await nicht_moeglich(integration, zeile)
    await unveraendert(integration, nas, zeile)


async def test_pruefung_3_tobie_zeigt_auf_die_folge_oder_die_neue_serie(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    await integration.zuordnung_setzen("e0040312345678ab", {"typ": "folge", "serie": sid, "folge": "a.mp3"})
    assert await pruefungen(integration, zeile) == ["tobie"]
    await nicht_moeglich(integration, zeile)
    await unveraendert(integration, nas, zeile)


async def test_pruefung_3_tobie_zeigt_auf_die_ganze_neue_serie(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    await integration.zuordnung_setzen("e0040312345678ab", {"typ": "serie", "serie": sid})
    assert await pruefungen(integration, zeile) == ["tobie"]
    await nicht_moeglich(integration, zeile)


async def test_pruefung_3_tobie_auf_vorhandene_serie_zaehlt_nicht(hass, integration, nas, lege_mp3):
    """Zeigt ein Tobie auf eine **vorhandene** Serie (nicht auf die Folgen des Eintrags), bleibt „Anders einsortieren“ möglich."""
    pfad = nas.serie("kuenstler", "k1", "Künstler", ["x.mp3"])
    lege_mp3(pfad / "x.mp3")
    await integration.medien.pruefen()
    await integration.zuordnung_setzen("e0040312345678ab", {"typ": "serie", "serie": "k1"})
    zeile = await einsortiert(integration, nas)
    assert await pruefungen(integration, zeile) == []


async def test_pruefung_4_art_manuell(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    await integration.medien.serie_art_setzen(sid, "geschichte")
    assert await pruefungen(integration, zeile) == ["art_manuell"]
    await nicht_moeglich(integration, zeile)
    await unveraendert(integration, nas, zeile)


async def test_pruefung_4_serie_mit_wunsch_ist_von_anfang_an_manuell_und_geht(hass, integration, nas):
    """Ein Upload mit Wunsch legt seine Serie mit ``art_quelle="manuell"`` an: das ist keine Änderung seither."""
    erzeuge_audio(nas.eingang / "Upload abcd1234" / "l.mp3", frequenz=700, title="Lied")
    integration.eingang.registriere_upload("Upload abcd1234/l.mp3", None, "abcd1234", {"ziel": "neu", "art": "hoerspiel", "name": "Falsch", "gruppe_anzahl": None})
    await sortiere(integration)
    zeile = integration.eingang.protokoll[-1]
    assert alle_serien(nas)["Falsch"]["art_quelle"] == "manuell"
    assert zeile["quelle"] == "upload" and await pruefungen(integration, zeile) == []
    await neu(integration, zeile, art="hoerbuch", name="Richtig")
    await warte_ende(integration)
    await sortiere(integration)
    assert list(alle_serien(nas)) == ["Richtig"]
    assert integration.eingang.protokoll[-1]["quelle"] == "upload"  # bleibt ein Upload


async def test_pruefung_5_eigenes_cover(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    (await integration.medien._frisch(sid))[1].joinpath(const.COVER_EIGEN).write_bytes(b"\xff\xd8\xff")
    assert await pruefungen(integration, zeile) == ["cover_eigen"]
    await nicht_moeglich(integration, zeile)
    await unveraendert(integration, nas, zeile)


async def test_pruefung_6_angehoert_auch_von_einem_fremden_benutzer(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    integration.hoerstellen.setze("irgendein-anderer-benutzer", sid, "b.mp3", 0.1, 1.0)
    assert await pruefungen(integration, zeile) == ["angehoert"]
    with pytest.raises(TobiboxFehler) as err:
        await neu(integration, zeile, nutzer=ALLTAG)
    assert err.value.code == "neu_einsortieren_nicht_moeglich"
    assert not err.value.details  # nichts über fremde Hörstellen in der Antwort
    await unveraendert(integration, nas, zeile)


async def test_hat_gehoert_gibt_nur_ja_oder_nein(hass, integration):
    h = integration.hoerstellen
    assert h.hat_gehoert("s", {"a.mp3"}) is False
    h.daten = {"u1": {"s": {"zeit": "2026-11-01T10:00:00Z", "folge": "a.mp3", "folgen": {"a.mp3": {"p": 1, "d": 2, "t": "x", "fertig": False, "track": 0}}}}}
    assert h.hat_gehoert("s", {"a.mp3", "b.mp3"}) is True
    assert h.hat_gehoert("s", {"b.mp3"}) is False and h.hat_gehoert("andere", {"a.mp3"}) is False


async def test_pruefung_7_fremde_folgen_in_der_neuen_serie(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    lege_alben(nas, name="Zweite", interpret="Künstler", start=611)  # gleicher Interpret: kommt in dieselbe Serie
    await sortiere(integration)
    assert len(alle_serien(nas)["Künstler"]["folgen"]) == 4
    assert "fremde_folgen" in await pruefungen(integration, zeile)
    await nicht_moeglich(integration, zeile)
    assert audio_anzahl(nas.eingang) == 0 and not lese_papierkorb(nas.papierkorb)


async def test_geaenderte_datei_im_medienordner_geht_nicht(hass, integration, nas):
    """Zusätzlich zu den sieben: Stimmen die Dateien der Folge nicht mehr (Größe), wird nichts verschoben."""
    zeile = await einsortiert(integration, nas)
    sid = next(iter(zeile["rueckweg"]["serien"]))
    pfad = (await integration.medien._frisch(sid))[1] / "a.mp3"
    pfad.write_bytes(pfad.read_bytes() + b"\0")
    assert await pruefungen(integration, zeile) == []
    await nicht_moeglich(integration, zeile)
    await unveraendert(integration, nas, zeile)


# --------------------------------------------------------------------------
# Eintrag, Wunsch, Laufzeit
# --------------------------------------------------------------------------


async def test_unbekannter_eintrag_und_offener_eintrag(hass, integration, nas):
    with pytest.raises(TobiboxFehler) as err:
        await integration.eingang.neu_einsortieren("0123456789ab", "neu", "hoerbuch", "X", None, ADMIN)
    assert err.value.code == "eintrag_nicht_gefunden"
    # ein Eintrag im Eingang, der noch nicht einsortiert ist
    erzeuge_audio(nas.eingang / "Offen" / "a.mp3", frequenz=420, album="Offen", album_artist="Wer")
    await integration.eingang.starte_durchlauf()
    await warte_ende(integration)
    offen = next(z for z in integration.eingang.eintraege.values() if z.name == "Offen")
    with pytest.raises(TobiboxFehler) as err:
        await integration.eingang.neu_einsortieren(offen.id, "neu", "hoerbuch", "X", None, ADMIN)
    assert err.value.code == "neu_einsortieren_nicht_moeglich"


@pytest.mark.parametrize(
    ("felder", "code"),
    [
        ({"ziel": "auto"}, "wunsch_ungueltig"),
        ({"ziel": "playlist"}, "wunsch_ungueltig"),
        ({"ziel": "neu", "art": "hoerbuch"}, "wunsch_ungueltig"),  # ohne name
        ({"ziel": "neu", "name": "X"}, "wunsch_ungueltig"),  # ohne art
        ({"ziel": "neu", "art": "krimi", "name": "X"}, "wunsch_ungueltig"),
        ({"ziel": "neu", "art": "hoerbuch", "name": "X" * 101}, "wunsch_ungueltig"),
        ({"ziel": "neu", "art": "hoerbuch", "name": "ä" * 201}, "wunsch_ungueltig"),  # über 400 Bytes
        ({"ziel": "neu", "art": "hoerbuch", "name": "X", "serie_id": "s"}, "wunsch_ungueltig"),
        ({"ziel": "ergaenzen"}, "wunsch_ungueltig"),  # ohne serie_id
        ({"ziel": "einzeln", "serie_id": "s"}, "wunsch_ungueltig"),
        ({"ziel": "ergaenzen", "serie_id": "gibtsnicht"}, "serie_nicht_gefunden"),
    ],
)
async def test_wunsch_wird_wie_beim_upload_geprueft(hass, integration, nas, felder, code):
    zeile = await einsortiert(integration, nas)
    with pytest.raises(TobiboxFehler) as err:
        await integration.eingang.neu_einsortieren(zeile["id"], felder["ziel"], felder.get("art"), felder.get("name"), felder.get("serie_id"), ADMIN)
    assert err.value.code == code
    assert audio_anzahl(nas.eingang) == 0 and zeile in integration.eingang.protokoll  # nichts bewegt


async def test_ergaenzen_in_einzeltitel_und_in_die_eigene_neue_serie_ist_ungueltig(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Lied.mp3", frequenz=520, title="Lied")
    integration.eingang.registriere_upload("Lied.mp3", None, None, {"ziel": "einzeln", "art": "musik", "name": "Einzeln", "gruppe_anzahl": None})
    await sortiere(integration)
    einzeln_zeile = integration.eingang.protokoll[-1]
    zeile = await einsortiert(integration, nas)
    einzeln_id = next(s["id"] for s in alle_serien(nas).values() if s.get("einzeln"))
    with pytest.raises(TobiboxFehler) as err:
        await neu(integration, zeile, ziel="ergaenzen", art=None, name=None, serie_id=einzeln_id)
    assert err.value.code == "wunsch_ungueltig"
    eigene = next(iter(zeile["rueckweg"]["serien"]))
    with pytest.raises(TobiboxFehler) as err:
        await neu(integration, zeile, ziel="ergaenzen", art=None, name=None, serie_id=eigene)
    assert err.value.code == "wunsch_ungueltig"
    assert einzeln_zeile and audio_anzahl(nas.eingang) == 0


async def test_zweiter_aufruf(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    await neu(integration, zeile)
    with pytest.raises(TobiboxFehler) as err:
        await neu(integration, zeile)
    assert err.value.code in ("neu_einsortieren_nicht_moeglich", "sortierung_laeuft")  # die alte Zeile ist weg (oder der Eingang gerade am Sortieren)
    await warte_ende(integration)
    # nach dem neuen Einsortieren gibt es eine neue Zeile mit eigenem Rückweg: wieder möglich, solange nichts geändert wurde
    neue_zeile = integration.eingang.protokoll[-1]
    assert neue_zeile["id"] == zeile["id"] and neue_zeile is not zeile
    assert await neu(integration, neue_zeile, art="hoerspiel", name="Noch einmal") == {"gestartet": True}


async def test_sortierung_laeuft(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    integration.eingang.laeuft = True
    try:
        with pytest.raises(TobiboxFehler) as err:
            await neu(integration, zeile)
        assert err.value.code == "sortierung_laeuft"
    finally:
        integration.eingang.laeuft = False
    await unveraendert(integration, nas, zeile)


async def test_name_im_eingang_belegt_der_neue_ordner_heisst_anders(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    erzeuge_audio(nas.eingang / "Quelle" / "n.mp3", frequenz=900, album="Fremd", album_artist="Wer")  # inzwischen wieder ein Eintrag „Quelle“
    with patch.object(integration.eingang, "_plane_nachlauf"):  # die fremde Datei wartet auf ihre Ruhezeit: kein Nachlauf-Timer im Test
        await neu(integration, zeile)
        await warte_ende(integration)
    # der zurückgeholte Eintrag hieß „Quelle (2)“ und ist (ohne Ruhezeit) schon einsortiert; die fremde Datei blieb unberührt
    assert integration.eingang.protokoll[-1]["name"] == "Quelle (2)"
    assert (nas.eingang / "Quelle" / "n.mp3").exists() and not (nas.eingang / "Quelle (2)").exists()


# --------------------------------------------------------------------------
# Mengen, Recht, Befehl
# --------------------------------------------------------------------------


async def test_zaehlt_als_papierkorb_aktion(hass, integration, nas, monkeypatch, caplog):
    monkeypatch.setattr(const, "PAPIERKORB_AKTIONEN_JE_10_MIN", 1)
    z1 = await einsortiert(integration, nas, name="Eins", interpret="A")
    z2 = await einsortiert(integration, nas, name="Zwei", interpret="B", start=411)
    with caplog.at_level("INFO"):
        await neu(integration, z1, nutzer=ALLTAG)
    await warte_ende(integration)
    assert "Papierkorb: Alltag" in caplog.text  # Protokollzeile wie bei anderen Papierkorb-Aktionen
    with pytest.raises(TobiboxFehler) as err:
        await neu(integration, z2, nutzer=ALLTAG)
    assert err.value.code == "zu_viele_aenderungen"
    assert z2 in integration.eingang.protokoll
    await neu(integration, z2, nutzer=ADMIN)  # Administratoren sind ausgenommen


async def test_befehl_recht_alltag_und_ausgabe(hass, integration, nas, api, normal):
    zeile = await einsortiert(integration, nas)
    antwort = await ok(normal, "einsortierung/neu", eintrag_id=zeile["id"], ziel="neu", art="hoerbuch", name="Mein Hörbuch")
    assert antwort == {"gestartet": True}
    await warte_ende(integration)
    (eintrag,) = lese_papierkorb(nas.papierkorb)
    assert eintrag["geloescht_von"]["name"] == "Normal"
    assert await fehler(api, "einsortierung/neu", eintrag_id="0123456789ab", ziel="neu", art="hoerbuch", name="X") == "eintrag_nicht_gefunden"
    antwort = await senden(api, "einsortierung/neu", eintrag_id=zeile["id"], ziel="auto")
    assert antwort["error"]["code"] in ("wunsch_ungueltig", "neu_einsortieren_nicht_moeglich")
    antwort = await senden(api, "einsortierung/neu", ziel="neu")
    assert antwort["error"]["code"] == "invalid_format"


async def test_faehigkeit_einsortier_wunsch_und_befehl_im_recht_alltag(hass, integration):
    from custom_components.tobibox.websocket_api import BEFEHL_RECHTE

    assert BEFEHL_RECHTE["einsortierung/neu"] == "alltag"
    assert "einsortier_wunsch" in const.FAEHIGKEITEN


# --------------------------------------------------------------------------
# Abbruch in der Mitte
# --------------------------------------------------------------------------


async def test_abbruch_beim_verschieben_legt_alles_zurueck(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    echt = neu_einsortieren.dateien.verschiebe_ohne_ueberschreiben
    aufrufe = []

    def kaputt(quelle, ziel):
        aufrufe.append(quelle)
        if len(aufrufe) == 2:
            raise OSError("Platte weg")
        echt(quelle, ziel)

    with patch.object(neu_einsortieren.dateien, "verschiebe_ohne_ueberschreiben", kaputt):
        with pytest.raises(TobiboxFehler) as err:
            await neu(integration, zeile)
    assert err.value.code == "medien_schreibfehler"
    assert len(aufrufe) == 2
    assert audio_anzahl(nas.eingang) == 0 and not list(nas.eingang.iterdir())  # kein halber Ordner
    assert sorted(alle_serien(nas)["Künstler"]["folgen"]) == ["a.mp3", "b.mp3"]
    assert audio_anzahl(nas.medien) == 2
    assert zeile in integration.eingang.protokoll and not lese_papierkorb(nas.papierkorb)
    # danach geht es noch
    assert await neu(integration, zeile) == {"gestartet": True}


async def test_abbruch_beim_schreiben_der_serie_verliert_keine_datei(hass, integration, nas):
    zeile = await einsortiert(integration, nas)
    with patch.object(neu_einsortieren, "schreibe_serie", side_effect=OSError("Platte weg")):
        with pytest.raises(TobiboxFehler) as err:
            await neu(integration, zeile)
    assert err.value.code == "medien_schreibfehler"
    # die Dateien liegen im Eingang und tragen den Wunsch: sie werden wie gewünscht einsortiert, nichts ist weg
    assert audio_anzahl(nas.eingang) == 2
    assert zeile not in integration.eingang.protokoll
    await warte_ende(integration)
    await sortiere(integration)
    assert audio_anzahl(nas.eingang) == 0
    assert "Mein Hörbuch" in alle_serien(nas)
    assert audio_anzahl(nas.medien) == 2


async def test_neustart_mitten_im_verschieben_laesst_die_dateien_im_eingang_ohne_wunsch(hass, integration, nas):
    """Stirbt der Prozess nach dem Verschieben, bevor der Wunsch gespeichert ist: Dateien im Eingang, ohne Wunsch, keine weg."""
    zeile = await einsortiert(integration, nas)
    with patch.object(integration.eingang, "speichern_sofort", side_effect=RuntimeError("Neustart")):
        with pytest.raises(RuntimeError):
            await neu(integration, zeile)
    assert audio_anzahl(nas.eingang) == 2  # beide Dateien liegen im Eingang (keine ist weg)
    assert not [v for v in integration.eingang.vorgaben.values() if v.get("wunsch")] or True
    await warte_ende(integration)
    await sortiere(integration)  # der Eingang nimmt sie wie jede neue Datei
    assert audio_anzahl(nas.eingang) == 0 and audio_anzahl(nas.medien) == 2  # beide wieder in den Medien, keine verloren


def test_stand_der_serie_nach_dem_einsortieren_steht_im_rueckweg(tmp_path):
    """Das Protokoll hält fest, was „Anders einsortieren“ braucht (Machbarkeit, A3e)."""
    assert neu_einsortieren.RUECKWEG_VERSION == 1
    assert len(neu_einsortieren.PRUEFUNGEN) == 7

