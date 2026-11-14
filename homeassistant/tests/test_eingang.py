"""Einsortieren nach Metadaten, Entscheidung M (Vertrag W, Abschnitt 11): T1 bis T20 und mehr."""

from __future__ import annotations

import json
import os
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.components import persistent_notification

from custom_components.tobibox import ffprobe
from custom_components.tobibox.fehler import TobiboxFehler

from .conftest import braucht_ffmpeg, ereignis_arten, erzeuge_audio

pytestmark = braucht_ffmpeg


async def sortiere(hub, **kw):
    """Ein Durchlauf, der die Ruhezeit übergeht, und warten, bis er fertig ist."""
    kw.setdefault("sofort", True)
    erg = await hub.eingang.durchlauf_und_warten(**kw)
    await hub.hass.async_block_till_done()
    return erg


def alle_serien(nas) -> dict[str, dict]:
    """Anzeigename -> serie.json (+ ``_ordner``) aller Serien in ``medien/``."""
    aus = {}
    for d in sorted(nas.medien.iterdir()):
        if d.is_dir() and (d / "serie.json").exists():
            daten = json.loads((d / "serie.json").read_text())
            daten["_ordner"] = d.name
            aus[daten["name"]] = daten
    return aus


def folge_info(serie: dict, name: str) -> dict:
    return serie.get("folgen_info", {}).get(name, {})


def inhalt(pfad: Path) -> list[str]:
    return sorted(p.name for p in pfad.iterdir())


def alt(pfad: Path, sekunden: int = 1000) -> Path:
    """Setzt die Änderungszeit in die Vergangenheit (Ruhezeit)."""
    t = time.time() - sekunden
    os.utime(pfad, (t, t))
    return pfad


# --------------------------------------------------------------------------
# T1 bis T20 (Vertrag W, 11.12)
# --------------------------------------------------------------------------


async def test_T1_ordner_mit_12_tracks_wird_eine_folge(hass, integration, nas):
    """Ordner ``Hörbuch X/`` mit 12 mp3, alle ``album="Hörbuch X"``, ``album_artist="Autor A"``, ``track=1..12``."""
    for i in range(1, 13):
        erzeuge_audio(nas.eingang / "Hörbuch X" / f"Kapitel {i:02d}.mp3", frequenz=300 + i, album="Hörbuch X",
                      album_artist="Autor A", track=f"{i}/12", title=f"Kapitel {i}")
    erg = await sortiere(integration)
    assert erg["eintraege"] == 1
    serien = alle_serien(nas)
    assert list(serien) == ["Autor A"]
    serie = serien["Autor A"]
    assert "pruefen" not in serie  # neue Serie ohne "bitte prüfen"
    assert serie["folgen"] == ["Hörbuch X"]
    ordner = nas.medien / serie["_ordner"] / "Hörbuch X"
    assert ordner.is_dir()
    assert inhalt(ordner) == [f"Kapitel {i:02d}.mp3" for i in range(1, 13)]  # Dateinamen unverändert
    assert folge_info(serie, "Hörbuch X")["anzeige"] == "Hörbuch X"
    assert "pruefen" not in folge_info(serie, "Hörbuch X")
    assert not (nas.eingang / "Hörbuch X").exists()  # der Eintrag ist erledigt


async def test_T2_fuenf_alben_werden_nach_nummer_aus_dem_albumnamen_geordnet(hass, integration, nas):
    for n, datei in zip([3, 1, 5, 2, 4], "abcde", strict=True):
        erzeuge_audio(nas.eingang / "Rabe" / f"{datei}.mp3", frequenz=400 + n, album=f"Der kleine Rabe - Folge {n}: Titel {n}",
                      album_artist="Der kleine Rabe")
    await sortiere(integration)
    serie = alle_serien(nas)["Der kleine Rabe"]
    # a=3, b=1, c=5, d=2, e=4 in Dateireihenfolge
    assert serie["folgen"] == ["b.mp3", "d.mp3", "a.mp3", "e.mp3", "c.mp3"]  # Nummer 1, 2, 3, 4, 5 (R1)
    assert [folge_info(serie, n)["nummer"] for n in serie["folgen"]] == [1, 2, 3, 4, 5]
    assert folge_info(serie, "b.mp3")["anzeige"] == "Der kleine Rabe - Folge 1: Titel 1"
    assert all(not folge_info(serie, n).get("pruefen") for n in serie["folgen"])


async def test_T3_m4b_serien_tag_schlaegt_interpret(hass, integration, nas):
    erzeuge_audio(nas.eingang / "kaenguru.m4b", kapitel=["Kapitel 1", "Kapitel 2"], album="Und überhaupt",
                  album_artist="Marc-Uwe Kling", title="Und überhaupt", series="Die Känguru-Chroniken", **{"series-part": "2"})
    await sortiere(integration)
    serien = alle_serien(nas)
    assert list(serien) == ["Die Känguru-Chroniken"]  # nicht "Marc-Uwe Kling"
    serie = serien["Die Känguru-Chroniken"]
    assert serie["folgen"] == ["kaenguru.m4b"]
    info = folge_info(serie, "kaenguru.m4b")
    assert info["anzeige"] == "Und überhaupt"
    assert info["nummer"] == 2
    assert "pruefen" not in serie


async def test_T4_datei_ohne_tags_in_ordner(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Märchen" / "x.mp3")
    await sortiere(integration)
    serie = alle_serien(nas)["Märchen"]
    assert serie["folgen"] == ["x.mp3"]
    info = folge_info(serie, "x.mp3")
    assert info["anzeige"] == "x"  # Dateiname ohne Endung
    assert info["pruefen"] is True
    assert set(info["pruefen_gruende"]) == {"tags_fehlen", "serie_aus_ordner"}
    assert serie["pruefen"] is True
    assert "serie_aus_ordner" in serie["pruefen_gruende"]


async def test_T5_lose_datei_ohne_tags_kommt_in_einzelfolgen(hass, integration, nas):
    erzeuge_audio(nas.eingang / "x.mp3")
    await sortiere(integration)
    serie = alle_serien(nas)["Einzelfolgen"]
    assert serie["folgen"] == ["x.mp3"]
    assert set(folge_info(serie, "x.mp3")["pruefen_gruende"]) == {"tags_fehlen", "serie_aus_ordner"}
    assert serie["pruefen"] is True


async def test_T6_serienschluessel_gleich_ohne_gross_klein_und_satzzeichen(hass, integration, nas):
    erzeuge_audio(nas.eingang / "a.mp3", frequenz=301, album="Folge 1", album_artist="Die drei ???")
    await sortiere(integration)
    erzeuge_audio(nas.eingang / "b.mp3", frequenz=302, album="Folge 2", album_artist="die drei ???")
    await sortiere(integration)
    serien = alle_serien(nas)
    assert list(serien) == ["Die drei ???"]  # zwei Durchläufe, eine Serie (Schlüssel "diedrei")
    assert serien["Die drei ???"]["folgen"] == ["a.mp3", "b.mp3"]


async def test_T7_serien_widerspruch_mehrheit_gewinnt(hass, integration, nas):
    for i, serie in enumerate(["A", "A", "A", "B"], start=1):
        erzeuge_audio(nas.eingang / "Ordner" / f"{i}.mp3", frequenz=300 + i, album="Gleiches Album", series=serie, track=str(i))
    await sortiere(integration)
    serien = alle_serien(nas)
    assert list(serien) == ["A"]
    assert serien["A"]["folgen"] == ["Gleiches Album"]
    gruende = folge_info(serien["A"], "Gleiches Album")["pruefen_gruende"]
    assert gruende == ["serie_widerspruch"]


async def test_T8_reihenfolge_ungleich_namensreihenfolge_bekommt_praefix(hass, integration, nas):
    erzeuge_audio(nas.eingang / "O" / "a.mp3", frequenz=301, album="Album", album_artist="S", track="2")
    erzeuge_audio(nas.eingang / "O" / "b.mp3", frequenz=302, album="Album", album_artist="S", track="1")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    assert inhalt(nas.medien / serie["_ordner"] / "Album") == ["001 b.mp3", "002 a.mp3"]


async def test_T9_reihenfolge_gleich_namensreihenfolge_bleibt(hass, integration, nas):
    erzeuge_audio(nas.eingang / "O" / "a.mp3", frequenz=301, album="Album", album_artist="S", track="1")
    erzeuge_audio(nas.eingang / "O" / "b.mp3", frequenz=302, album="Album", album_artist="S", track="2")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    assert inhalt(nas.medien / serie["_ordner"] / "Album") == ["a.mp3", "b.mp3"]


async def test_T10_kopierschutz_haelt_die_ganze_gruppe_zurueck(hass, integration, nas):
    for i in (1, 2, 3):
        erzeuge_audio(nas.eingang / "Buch" / f"drei-{i}.mp3", frequenz=300 + i, album="Mit Schutz", album_artist="Autor", track=str(i))
    erzeuge_audio(nas.eingang / "Buch" / "frei.mp3", frequenz=350, album="Ohne Schutz", album_artist="Autor")
    echt = ffprobe.pruefe_datei

    def tu_so(datei, endung=None):
        p = echt(datei, endung)
        if os.path.basename(datei) == "drei-2.mp3":
            p.probe.codec = "drms"
            return ffprobe.Pruefung("warnung", ffprobe.KOPIERSCHUTZ, p.probe)
        return p

    with patch("custom_components.tobibox.eingang.ffprobe.pruefe_datei", side_effect=tu_so):
        await sortiere(integration)
    # die ganze Gruppe bleibt im Eingang (die gute Datei ist ohne Folge nutzlos) ...
    assert inhalt(nas.eingang / "Buch") == ["drei-1.mp3", "drei-2.mp3", "drei-3.mp3"]
    # ... andere Gruppen desselben Eintrags werden einsortiert
    serie = alle_serien(nas)["Autor"]
    assert serie["folgen"] == ["frei.mp3"]
    liste = await integration.eingang.liste("offen", 50, 0)
    eintrag = liste["eintraege"][0]
    assert eintrag["name"] == "Buch"
    assert eintrag["status"] == "teilweise"
    hinweise = {(h["code"], h["datei"]) for h in eintrag["hinweise"]}
    assert ("kopierschutz", "drei-2.mp3") in hinweise
    assert eintrag["ergebnis"][0]["folge"] == "frei.mp3"


async def test_T10b_nur_blockierte_gruppe_ist_blockiert_und_benachrichtigt(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Buch" / "a.mp3", album="X", album_artist="Autor")
    with patch("custom_components.tobibox.eingang.ffprobe.pruefe_datei", return_value=ffprobe.Pruefung("warnung", ffprobe.KOPIERSCHUTZ)):
        await sortiere(integration)
    assert (nas.eingang / "Buch" / "a.mp3").exists()
    assert alle_serien(nas) == {}
    eintrag = (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]
    assert eintrag["status"] == "blockiert"
    meldungen = persistent_notification._async_get_or_create_notifications(hass)
    assert f"tobibox_eingang_{eintrag['id']}" in meldungen  # einmal je Eintrag
    await sortiere(integration)
    assert len([k for k in persistent_notification._async_get_or_create_notifications(hass) if k.startswith("tobibox_eingang_")]) == 1


async def test_T11_doppelte_pruefsumme_kommt_in_den_papierkorb(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Folge 1.mp3", frequenz=333, album="Folge 1", album_artist="Serie D")
    await sortiere(integration)
    serie = alle_serien(nas)["Serie D"]
    assert serie["folgen"] == ["Folge 1.mp3"]
    # dieselbe Datei (gleicher Inhalt) noch einmal in den Eingang, unter anderem Namen
    original = nas.medien / serie["_ordner"] / "Folge 1.mp3"
    (nas.eingang / "Kopie.mp3").write_bytes(original.read_bytes())
    ereignis = []
    await sortiere(integration)
    assert not (nas.eingang / "Kopie.mp3").exists()
    assert alle_serien(nas)["Serie D"]["folgen"] == ["Folge 1.mp3"]  # keine neue Folge
    papierkorb = (await integration.medien.papierkorb_liste(100, 0))["eintraege"]
    assert len(papierkorb) == 1
    assert (papierkorb[0]["typ"], papierkorb[0]["grund"], papierkorb[0]["folge"]) == ("eingang", "doppelt", None)
    meta = json.loads((nas.papierkorb / papierkorb[0]["id"] / "meta.json").read_text())
    assert (meta["typ"], meta["grund"], meta["name"], meta["serie_id"]) == ("eingang", "doppelt", "Kopie.mp3", None)
    erledigt = (await integration.eingang.liste("erledigt", 50, 0))["eintraege"]
    assert erledigt[0]["name"] == "Kopie.mp3"
    assert {h["code"] for h in erledigt[0]["hinweise"]} == {"doppelt"}
    # wiederherstellen: zurück in den Eingang
    await integration.medien.papierkorb_wiederherstellen(papierkorb[0]["id"], None)
    assert (nas.eingang / "Kopie.mp3").exists()
    del ereignis


async def test_T12_gleicher_name_anderer_inhalt_bekommt_suffix(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Folge 1.mp3", frequenz=301, album="Erste", album_artist="Serie S")
    await sortiere(integration)
    erzeuge_audio(nas.eingang / "Folge 1.mp3", frequenz=777, album="Zweite", album_artist="Serie S")
    await sortiere(integration)
    serie = alle_serien(nas)["Serie S"]
    assert serie["folgen"] == ["Folge 1.mp3", "Folge 1 (2).mp3"]
    assert (nas.medien / serie["_ordner"] / "Folge 1 (2).mp3").exists()


async def test_T13_ohne_nummer_nach_erscheinungsdatum(hass, integration, nas):
    for datei, album, jahr in (("a.mp3", "Alpha", "2001"), ("b.mp3", "Beta", "1999"), ("c.mp3", "Gamma", "2000")):
        erzeuge_audio(nas.eingang / datei, frequenz=300 + ord(datei[0]), album=album, album_artist="Serie Z", date=jahr)
    await sortiere(integration)
    serie = alle_serien(nas)["Serie Z"]
    assert serie["folgen"] == ["b.mp3", "c.mp3", "a.mp3"]  # 1999, 2000, 2001
    assert folge_info(serie, "b.mp3")["datum"] == "1999-01-01"


async def test_T14_ohne_nummer_und_datum_nach_eingangsreihenfolge(hass, integration, nas):
    for datei, album in (("f1.mp3", "Zeta"), ("f2.mp3", "Alpha"), ("f3.mp3", "Mu")):
        erzeuge_audio(nas.eingang / datei, frequenz=300 + ord(datei[1]), album=album, album_artist="Serie E")
    await sortiere(integration)
    serie = alle_serien(nas)["Serie E"]
    assert serie["folgen"] == ["f1.mp3", "f2.mp3", "f3.mp3"]  # Eingangsindex 0, 1, 2


async def test_T15_neue_folge_in_vorhandene_reihenfolge_einfuegen(hass, integration, nas, lege_mp3):
    pfad = nas.serie("Bestand", "b1", "Bestand", ["f1.mp3", "f2.mp3", "f3.mp3", "ohne.mp3"],
                     folgen_info={"f1.mp3": {"nummer": 1}, "f2.mp3": {"nummer": 2}, "f3.mp3": {"nummer": 3}})
    for n in ("f1", "f2", "f3", "ohne"):
        lege_mp3(pfad / f"{n}.mp3")
    await integration.medien.pruefen()
    erzeuge_audio(nas.eingang / "n4.mp3", frequenz=401, album="Folge 4: Neu", album_artist="Bestand")
    erzeuge_audio(nas.eingang / "n2.mp3", frequenz=402, album="Folge 2: Nochmal", album_artist="Bestand")
    await sortiere(integration)
    serie = alle_serien(nas)["Bestand"]
    assert serie["folgen"] == ["f1.mp3", "f2.mp3", "n2.mp3", "f3.mp3", "n4.mp3", "ohne.mp3"]
    assert folge_info(serie, "n2.mp3")["pruefen_gruende"] == ["nummer_doppelt"]  # die Nummer 2 gab es schon
    assert "pruefen" not in folge_info(serie, "n4.mp3")


async def test_T16_various_artists_gilt_als_leer(hass, integration, nas):
    erzeuge_audio(nas.eingang / "a.mp3", frequenz=301, album="Sammlung", album_artist="Various Artists", artist="Sprecher S")
    erzeuge_audio(nas.eingang / "Ordner V" / "b.mp3", frequenz=302, album="Anderes", album_artist="Various Artists")
    await sortiere(integration)
    serien = alle_serien(nas)
    assert set(serien) == {"Sprecher S", "Ordner V"}
    assert folge_info(serien["Sprecher S"], "a.mp3")["pruefen_gruende"] == ["serie_aus_interpret"]
    assert folge_info(serien["Ordner V"], "b.mp3")["pruefen_gruende"] == ["serie_aus_ordner"]
    assert serien["Sprecher S"]["pruefen"] is True and serien["Ordner V"]["pruefen"] is True


async def test_T17_cd_zusatz_gehoert_zu_einer_gruppe(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Buch" / "cd2-01.mp3", frequenz=302, album="Hörbuch X (CD 2)", album_artist="Autor", track="1")
    erzeuge_audio(nas.eingang / "Buch" / "cd1-01.mp3", frequenz=301, album="Hörbuch X (CD 1)", album_artist="Autor", track="1")
    erzeuge_audio(nas.eingang / "Buch" / "cd1-02.mp3", frequenz=303, album="Hörbuch X (CD 1)", album_artist="Autor", track="2")
    await sortiere(integration)
    serie = alle_serien(nas)["Autor"]
    assert serie["folgen"] == ["Hörbuch X"]
    assert folge_info(serie, "Hörbuch X")["anzeige"] == "Hörbuch X"
    # CD 1 vor CD 2, dann nach Track: das ist schon die natürliche Namensordnung, die Namen bleiben
    assert inhalt(nas.medien / serie["_ordner"] / "Hörbuch X") == ["cd1-01.mp3", "cd1-02.mp3", "cd2-01.mp3"]
    assert not folge_info(serie, "Hörbuch X").get("pruefen")  # kein track_doppelt, denn die CD-Nummer trennt


async def test_T18_upload_vorgabe_serie_gilt_gegen_die_tags(hass, integration, nas, lege_mp3):
    pfad = nas.serie("Ziel", "ziel", "Ziel-Serie", [])
    await integration.medien.pruefen()
    erzeuge_audio(nas.eingang / "Upload abcd1234" / "x.mp3", album="Folge 9", album_artist="Ganz Andere Serie")
    integration.eingang.registriere_upload("Upload abcd1234/x.mp3", "ziel", "abcd1234-gruppe")
    erg = await integration.eingang.durchlauf_und_warten(sofort=False)  # Uploads übergehen die Ruhezeit
    await hass.async_block_till_done()
    assert erg["eintraege"] == 1
    serien = alle_serien(nas)
    assert list(serien) == ["Ziel-Serie"]
    assert serien["Ziel-Serie"]["folgen"] == ["x.mp3"]
    assert (pfad / "x.mp3").exists()
    integration.eingang.abbrechen()


async def test_T18b_vorgabe_serie_fehlt_dann_aus_den_tags(hass, integration, nas):
    erzeuge_audio(nas.eingang / "x.mp3", album="Folge 9", album_artist="Aus Tags")
    integration.eingang.registriere_upload("x.mp3", "gibtsnicht", None)
    await integration.eingang.durchlauf_und_warten()
    serie = alle_serien(nas)["Aus Tags"]
    assert folge_info(serie, "x.mp3")["pruefen_gruende"] == ["vorgabe_serie_fehlt"]
    integration.eingang.abbrechen()


async def test_T19_ruhezeit_30_sekunden_alt_wartet(hass, integration, nas):
    datei = erzeuge_audio(nas.eingang / "x.mp3", album="A", album_artist="S")
    t = time.time() - 30
    os.utime(datei, (t, t))
    erg = await integration.eingang.durchlauf_und_warten(sofort=False)
    assert erg["eintraege"] == 0
    assert datei.exists() and alle_serien(nas) == {}
    eintrag = (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]
    assert eintrag["status"] == "wartet"
    await sortiere(integration, sofort=True)
    assert not datei.exists()
    assert "S" in alle_serien(nas)


async def test_T20_doppelpunkt_im_dateinamen(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Folge 1: Der Rabe.mp3", album="Folge 1: Der Rabe", album_artist="Rabenserie")
    await sortiere(integration)
    serie = alle_serien(nas)["Rabenserie"]
    assert serie["folgen"] == ["Folge 1 - Der Rabe.mp3"]
    assert (nas.medien / serie["_ordner"] / "Folge 1 - Der Rabe.mp3").exists()
    assert folge_info(serie, "Folge 1 - Der Rabe.mp3")["anzeige"] == "Folge 1: Der Rabe"  # Anzeigenamen bleiben frei


# --------------------------------------------------------------------------
# Ruhezeit, Gruppieren, Zusammenführen, Reihenfolgen
# --------------------------------------------------------------------------


async def test_ruhezeit_zwei_scans_mit_gleicher_groesse(hass, integration, nas):
    """Neueste Änderung >= 120 s her **und** Anzahl und Größe beim vorigen Scan gleich (Kopierprogramme übernehmen alte Zeiten)."""
    datei = alt(erzeuge_audio(nas.eingang / "Ordner" / "a.mp3", album="A", album_artist="S"))
    alt(datei.parent)
    erg = await integration.eingang.durchlauf_und_warten(sofort=False)
    assert erg["eintraege"] == 0  # der erste Scan hat keinen früheren Scan zum Vergleichen
    # während des Kopierens kommt eine Datei dazu (mit alter Zeit): Anzahl und Größe haben sich geändert
    alt(erzeuge_audio(nas.eingang / "Ordner" / "b.mp3", frequenz=500, album="B", album_artist="S"))
    alt(datei.parent)
    erg = await integration.eingang.durchlauf_und_warten(sofort=False)
    assert erg["eintraege"] == 0
    erg = await integration.eingang.durchlauf_und_warten(sofort=False)
    assert erg["eintraege"] == 1
    assert alle_serien(nas)["S"]["folgen"] == ["a.mp3", "b.mp3"]


async def test_nachplanen_wenn_ein_eintrag_wartet(hass, integration, nas):
    erzeuge_audio(nas.eingang / "x.mp3", album="A", album_artist="S")
    await integration.eingang.durchlauf_und_warten(sofort=False)
    assert integration.eingang._nachplan_abbruch is not None  # nach 60 s ein weiterer Durchlauf
    integration.eingang.abbrechen()


async def test_lose_dateien_mit_gleichem_album_sind_eine_folge(hass, integration, nas):
    erzeuge_audio(nas.eingang / "teil1.mp3", frequenz=301, album="Das Album", album_artist="Autor", track="1")
    erzeuge_audio(nas.eingang / "teil2.mp3", frequenz=302, album="Das Album", album_artist="Autor", track="2")
    erzeuge_audio(nas.eingang / "andere.mp3", frequenz=303, album="Anderes Album", album_artist="Autor")
    await sortiere(integration)
    serie = alle_serien(nas)["Autor"]
    assert sorted(serie["folgen"]) == ["Das Album", "andere.mp3"]
    assert inhalt(nas.medien / serie["_ordner"] / "Das Album") == ["teil1.mp3", "teil2.mp3"]


async def test_verschiedene_alben_in_einem_ordner_sind_verschiedene_folgen(hass, integration, nas):
    erzeuge_audio(nas.eingang / "O" / "a.mp3", frequenz=301, album="Eins", album_artist="S")
    erzeuge_audio(nas.eingang / "O" / "b.mp3", frequenz=302, album="Zwei", album_artist="S")
    await sortiere(integration)
    assert alle_serien(nas)["S"]["folgen"] == ["a.mp3", "b.mp3"]


async def test_ordner_ohne_tags_ist_eine_folge_mit_vielen_tracks(hass, integration, nas):
    for i in (1, 2, 3):
        erzeuge_audio(nas.eingang / "CD Schatzinsel" / f"{i:02d}.mp3", frequenz=300 + i)
    await sortiere(integration)
    serie = alle_serien(nas)["CD Schatzinsel"]
    assert serie["folgen"] == ["CD Schatzinsel"]
    info = folge_info(serie, "CD Schatzinsel")
    assert info["pruefen"] is True and set(info["pruefen_gruende"]) == {"tags_fehlen", "serie_aus_ordner"}
    assert inhalt(nas.medien / serie["_ordner"] / "CD Schatzinsel") == ["01.mp3", "02.mp3", "03.mp3"]


async def test_dateien_ohne_album_und_mit_album_im_selben_ordner(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Ordner" / "a.mp3", frequenz=301, album="Mit Album", album_artist="S")
    erzeuge_audio(nas.eingang / "Ordner" / "b.mp3", frequenz=302, album_artist="S")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    assert sorted(serie["folgen"]) == ["a.mp3", "b.mp3"]
    assert "tags_fehlen" in folge_info(serie, "b.mp3")["pruefen_gruende"]
    assert not folge_info(serie, "a.mp3").get("pruefen")


async def test_nummer_aus_tag_vor_albumname_und_widerspruch(hass, integration, nas):
    for i, nr in enumerate(["3", "3", "4"], start=1):
        erzeuge_audio(nas.eingang / "O" / f"{i}.mp3", frequenz=300 + i, album="Folge 9: Falsch", album_artist="S", track=str(i), **{"series-part": nr})
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    info = folge_info(serie, "Folge 9: Falsch".replace(":", " -"))
    assert info["nummer"] == 3  # Mehrheit des Tags, nicht die 9 aus dem Namen
    assert info["pruefen_gruende"] == ["nummer_widerspruch"]


async def test_zwei_alben_mit_gleicher_nummer_beide_bleiben(hass, integration, nas):
    erzeuge_audio(nas.eingang / "a.mp3", frequenz=301, album="Folge 5: Eins", album_artist="S")
    erzeuge_audio(nas.eingang / "b.mp3", frequenz=302, album="Folge 5: Zwei", album_artist="S")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    assert serie["folgen"] == ["a.mp3", "b.mp3"]
    for n in serie["folgen"]:
        assert folge_info(serie, n)["pruefen_gruende"] == ["nummer_doppelt"]


async def test_track_teils_leer_und_track_doppelt(hass, integration, nas):
    erzeuge_audio(nas.eingang / "A" / "a.mp3", frequenz=301, album="Teils", album_artist="S", track="1")
    erzeuge_audio(nas.eingang / "A" / "b.mp3", frequenz=302, album="Teils", album_artist="S")
    erzeuge_audio(nas.eingang / "B" / "a.mp3", frequenz=303, album="Doppelt", album_artist="S", track="1")
    erzeuge_audio(nas.eingang / "B" / "b.mp3", frequenz=304, album="Doppelt", album_artist="S", track="1")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    assert folge_info(serie, "Teils")["pruefen_gruende"] == ["track_teils_leer"]
    assert folge_info(serie, "Doppelt")["pruefen_gruende"] == ["track_doppelt"]
    # die Datei mit Track kommt zuerst, beide bleiben in der Folge (Namen bleiben, die Reihenfolge ist schon die natürliche)
    assert inhalt(nas.medien / serie["_ordner"] / "Teils") == ["a.mp3", "b.mp3"]
    assert inhalt(nas.medien / serie["_ordner"] / "Doppelt") == ["a.mp3", "b.mp3"]


async def test_gleicher_name_im_folgen_ordner_bekommt_praefix(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Buch" / "CD1" / "01.mp3", frequenz=301, album="Buch", album_artist="S", disc="1", track="1")
    erzeuge_audio(nas.eingang / "Buch" / "CD2" / "01.mp3", frequenz=302, album="Buch", album_artist="S", disc="2", track="1")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    assert inhalt(nas.medien / serie["_ordner"] / "Buch") == ["001 01.mp3", "002 01.mp3"]


async def test_name_wird_nach_smb_regeln_bereinigt_und_gekuerzt(hass, integration, nas):
    lang = "L" * 251  # 255 Bytes mit ".mp3": das Dateisystem erlaubt es, die Namensregel (250) kürzt
    erzeuge_audio(nas.eingang / f"{lang}.mp3", album="Sehr langer Name", album_artist="S")
    erzeuge_audio(nas.eingang / "con.mp3", frequenz=500, album="Gerät", album_artist="S")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    namen = set(serie["folgen"])
    assert "_con.mp3" in namen
    gekuerzt = next(n for n in namen if n.startswith("LLL"))
    assert len(gekuerzt.encode()) <= 250 and gekuerzt.endswith(".mp3")
    assert "name_geaendert" in folge_info(serie, gekuerzt)["pruefen_gruende"]


async def test_nachlieferung_zu_vorhandenem_album_ist_eine_neue_folge(hass, integration, nas):
    erzeuge_audio(nas.eingang / "a.mp3", frequenz=301, album="Album", album_artist="S")
    await sortiere(integration)
    erzeuge_audio(nas.eingang / "b.mp3", frequenz=302, album="Album", album_artist="S")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    assert serie["folgen"] == ["a.mp3", "b.mp3"]
    assert folge_info(serie, "b.mp3")["pruefen_gruende"] == ["folge_gleicher_name"]


async def test_gruppe_teilweise_doppelt(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Eins.mp3", frequenz=301, album="Bekannt", album_artist="S")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    bekannt = (nas.medien / serie["_ordner"] / "Eins.mp3").read_bytes()
    (nas.eingang / "Ordner").mkdir()
    (nas.eingang / "Ordner" / "kopie.mp3").write_bytes(bekannt)
    erzeuge_audio(nas.eingang / "Ordner" / "neu1.mp3", frequenz=302, album="Gemischt", album_artist="S", track="1")
    erzeuge_audio(nas.eingang / "Ordner" / "neu2.mp3", frequenz=303, album="Gemischt", album_artist="S", track="2")
    (nas.eingang / "Ordner" / "kopie.mp3").write_bytes(bekannt)
    # Eine Gruppe (gleiches Album) mit einer doppelten Datei: das Doppelte wird verworfen, der Rest ist die Folge
    erzeuge_audio(nas.eingang / "Ordner" / "kopie.mp3", frequenz=301, album="Gemischt", album_artist="S", track="3")
    (nas.eingang / "Ordner" / "kopie.mp3").write_bytes(bekannt)
    d = nas.eingang / "Ordner" / "kopie.mp3"
    # ``kopie.mp3`` hat dieselben Bytes wie die bekannte Datei, also die Tags von "Bekannt": eigene Gruppe, ganz doppelt
    await sortiere(integration)
    assert not d.exists()
    s = alle_serien(nas)["S"]
    assert s["folgen"] == ["Eins.mp3", "Gemischt"]
    assert (await integration.medien.papierkorb_liste(100, 0))["gesamt"] == 1


async def test_gleiche_datei_zweimal_im_selben_durchlauf(hass, integration, nas):
    a = erzeuge_audio(nas.eingang / "a.mp3", frequenz=301, album="A", album_artist="S")
    (nas.eingang / "b.mp3").write_bytes(a.read_bytes())
    await sortiere(integration)
    assert alle_serien(nas)["S"]["folgen"] == ["a.mp3"]
    assert (await integration.medien.papierkorb_liste(100, 0))["gesamt"] == 1


async def test_hash_index_verliert_papierkorb_folgen_und_bekommt_sie_zurueck(hass, integration, nas):
    erzeuge_audio(nas.eingang / "a.mp3", frequenz=301, album="A", album_artist="S")
    await sortiere(integration)
    serie = alle_serien(nas)["S"]
    assert len(integration.eingang.index) == 1
    erg = await integration.medien.folge_loeschen(serie["id"], "a.mp3", False, None)
    assert integration.eingang.index == {}
    meta = json.loads((nas.papierkorb / erg["eintrag"]["id"] / "meta.json").read_text())
    assert len(meta["index_pruefsummen"]) == 1
    await integration.medien.papierkorb_wiederherstellen(erg["eintrag"]["id"], None)
    await hass.async_block_till_done()
    for _ in range(50):
        if integration.eingang.index:
            break
        await hass.async_block_till_done()
        import asyncio

        await asyncio.sleep(0.02)
    assert list(integration.eingang.index) == meta["index_pruefsummen"]


# --------------------------------------------------------------------------
# Hinweise, Reste, Abbrüche
# --------------------------------------------------------------------------


async def test_ffprobe_fehlt_der_durchlauf_bleibt_liegen(hass, integration, nas):
    datei = erzeuge_audio(nas.eingang / "a.mp3", album="A", album_artist="S")
    with patch("custom_components.tobibox.ffprobe.ffprobe_pfad", return_value=None):
        await sortiere(integration)
    assert datei.exists() and alle_serien(nas) == {}
    eintrag = (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]
    assert eintrag["status"] == "blockiert"
    assert [h["code"] for h in eintrag["hinweise"]] == ["ffprobe_fehlt"]


async def test_eintrag_ohne_audiodateien(hass, integration, nas):
    (nas.eingang / "Nur Bilder").mkdir()
    (nas.eingang / "Nur Bilder" / "cover.jpg").write_bytes(b"x")
    (nas.eingang / "notiz.txt").write_text("x")
    await sortiere(integration)
    liste = (await integration.eingang.liste("offen", 50, 0))["eintraege"]
    assert {e["name"] for e in liste} == {"Nur Bilder", "notiz.txt"}
    for e in liste:
        assert e["status"] == "blockiert"
        assert [h["code"] for h in e["hinweise"]] == ["keine_audiodateien"]
        assert e["dateien"] == 0 and e["ignoriert"] == 1
    assert (nas.eingang / "Nur Bilder" / "cover.jpg").exists()


async def test_reste_kommen_in_den_papierkorb_leere_ordner_werden_geloescht(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Buch" / "CD1" / "a.mp3", album="A", album_artist="S")
    (nas.eingang / "Buch" / "cover.jpg").write_bytes(b"jpg")
    (nas.eingang / "Buch" / "CD1" / "._a.mp3").write_bytes(b"apple")
    (nas.eingang / "Buch" / "leer" / "noch leerer").mkdir(parents=True)
    await sortiere(integration)
    assert not (nas.eingang / "Buch").exists()  # der Eintrag ist aus dem Eingang verschwunden
    papierkorb = (await integration.medien.papierkorb_liste(100, 0))["eintraege"]
    assert [(e["typ"], e["grund"], e["anzeige"]) for e in papierkorb] == [("eingang", "eingang_rest", "Buch")]
    meta = json.loads((nas.papierkorb / papierkorb[0]["id"] / "meta.json").read_text())
    assert meta["art"] == "ordner"
    assert (nas.papierkorb / papierkorb[0]["id"] / "inhalt" / "Buch" / "cover.jpg").exists()
    erledigt = (await integration.eingang.liste("erledigt", 50, 0))["eintraege"]
    assert erledigt[0]["name"] == "Buch" and erledigt[0]["status"] == "erledigt"


async def test_nur_dotfiles_als_rest_erzeugen_keinen_papierkorb_eintrag(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Buch" / "a.mp3", album="A", album_artist="S")
    (nas.eingang / "Buch" / ".DS_Store").write_bytes(b"x")
    await sortiere(integration)
    assert not (nas.eingang / "Buch").exists()
    assert (await integration.medien.papierkorb_liste(100, 0))["gesamt"] == 0


async def test_tiefer_als_fuenf_ebenen_wird_nicht_gelesen(hass, integration, nas):
    tief = nas.eingang / "Eintrag" / "1" / "2" / "3" / "4" / "5" / "6"
    erzeuge_audio(tief / "tief.mp3", album="A", album_artist="S")
    erzeuge_audio(nas.eingang / "Eintrag" / "1" / "oben.mp3", frequenz=500, album="B", album_artist="S")
    await sortiere(integration)
    assert (tief / "tief.mp3").exists()  # wird nicht gelesen
    assert alle_serien(nas)["S"]["folgen"] == ["oben.mp3"]


async def test_abbruch_zwischen_verschieben_und_serie_json(hass, integration, nas, lege_mp3):
    pfad = nas.serie("Bestand", "b1", "Bestand", ["alt.mp3"])
    lege_mp3(pfad / "alt.mp3")
    await integration.medien.pruefen()
    erzeuge_audio(nas.eingang / "neu.mp3", frequenz=444, album="Neu", album_artist="Bestand")
    with patch("custom_components.tobibox.eingang.schreibe_serie", side_effect=OSError("Netzwerk weg")):
        await sortiere(integration)
    # die Datei liegt im Serien-Ordner, steht aber nicht in folgen
    assert (pfad / "neu.mp3").exists()
    assert nas.serie_json("Bestand")["folgen"] == ["alt.mp3"]
    # die nächste Prüfung der Freigabe trägt sie hinten ein, es geht nichts verloren
    await integration.medien.pruefen()
    assert nas.serie_json("Bestand")["folgen"] == ["alt.mp3", "neu.mp3"]


async def test_ereignisse_neu_einsortiert_und_durchlauf_fertig(hass, integration, nas, ereignisse):
    erzeuge_audio(nas.eingang / "a.mp3", album="Folge 1", album_artist="S")
    erzeuge_audio(nas.eingang / "b.mp3", frequenz=500)
    await sortiere(integration)
    neu = [e for e in ereignisse if e["thema"] == "eingang" and e["art"] == "neu_einsortiert"]
    assert len(neu) == 2  # eines je Eintrag, nie zusammengefasst
    a = next(e["daten"] for e in neu if e["daten"]["eintrag_name"] == "a.mp3")
    assert a["ergebnis"][0]["serie_name"] == "S" and a["ergebnis"][0]["serie_neu"] is True
    assert a["zaehler"] == {"folgen": 1, "serien_neu": 1, "pruefen": 0, "doppelt": 0, "blockiert": 0}
    b = next(e["daten"] for e in neu if e["daten"]["eintrag_name"] == "b.mp3")
    assert b["zaehler"]["pruefen"] == 1
    fertig = [e for e in ereignisse if e["thema"] == "eingang" and e["art"] == "durchlauf_fertig"]
    assert fertig and fertig[-1]["daten"]["zaehler"]["folgen"] == 2
    assert "serien_geaendert" in ereignis_arten(ereignisse, "medien")


async def test_eingang_liste_felder_und_pagination(hass, integration, nas):
    erzeuge_audio(nas.eingang / "a.mp3", album="A", album_artist="S")
    (nas.eingang / "b.txt").write_text("x")
    await integration.eingang.durchlauf_und_warten(sofort=False)  # die Liste kommt aus dem Zwischenspeicher des letzten Durchlaufs
    liste = await integration.eingang.liste("offen", 50, 0)
    assert liste["gesamt"] == 2
    assert liste["sortierung_laeuft"] is False
    assert liste["geprueft_am"]
    a = next(e for e in liste["eintraege"] if e["name"] == "a.mp3")
    assert a["art"] == "datei" and a["dateien"] == 1 and a["ignoriert"] == 0 and a["groesse_bytes"] > 0
    assert len(a["id"]) == 12
    assert a["status"] == "wartet"
    assert a["zuerst_gesehen"].endswith("Z") and a["geaendert_am"].endswith("Z")
    assert (await integration.eingang.liste("offen", 1, 1))["eintraege"] != (await integration.eingang.liste("offen", 1, 0))["eintraege"]


async def test_eingang_sortieren_unbekannte_id(hass, integration, nas):
    with pytest.raises(TobiboxFehler) as err:
        await integration.eingang.starte_durchlauf(["0123456789ab"])
    assert err.value.code == "eintrag_nicht_gefunden"


async def test_eingang_fehlt_ist_nicht_erreichbar(hass, integration, nas):
    os.rmdir(nas.eingang)
    with pytest.raises(TobiboxFehler) as err:
        await integration.eingang.starte_durchlauf()
    assert err.value.code == "medien_nicht_erreichbar"
    assert integration.eingang.laeuft is False


async def test_laeuft_bereits(hass, integration, nas):
    erzeuge_audio(nas.eingang / "a.mp3", album="A", album_artist="S")
    erste = await integration.eingang.starte_durchlauf(sofort=True)
    zweite = await integration.eingang.starte_durchlauf(sofort=True)
    assert erste["gestartet"] is True
    assert zweite == {"gestartet": False, "laeuft_bereits": True, "eintraege": 0}
    await integration.eingang._task
    await hass.async_block_till_done()
    assert "S" in alle_serien(nas)


async def test_eintrag_id_ist_stabil():
    from custom_components.tobibox.eingang import eintrag_id

    assert eintrag_id("Hörbuch X") == eintrag_id("Hörbuch X")
    assert len(eintrag_id("x")) == 12
    assert eintrag_id("a") != eintrag_id("b")


# --------------------------------------------------------------------------
# Upload mit Wunsch (Vertrag W, 14.4; Paket A3d): ``neu``, ``ergaenzen``, ``einzeln``, ``gruppe_anzahl``
# --------------------------------------------------------------------------

GRUPPE = "gruppe12-abcdef"
ORDNER = "Upload gruppe12"


def wunsch(ziel: str, art: str | None = None, name: str | None = None, anzahl: int | None = None) -> dict:
    return {"ziel": ziel, "art": art, "name": name, "gruppe_anzahl": anzahl}


def stille_zeitgeber(integration) -> None:
    """Meldet die Zeitgeber der Integration ab (10-Minuten-Prüfung, „20 s nach dem Upload“, Nachlauf).

    Unter dem ``freezer`` löst jeder Sprung der Uhr sie aus; sie würden Durchläufe neben denen des Tests starten."""
    for fn in integration._abmelden:
        fn()
    integration._abmelden.clear()
    for fn in list(integration._timer):
        fn()
    integration._timer.clear()
    integration.eingang.abbrechen()


def lege_upload(integration, nas, nr: int, w: dict, *, serie_id: str | None = None, gruppe: str | None = GRUPPE, **tags) -> str:
    """Eine hochgeladene Datei: im Eingang-Ordner der Gruppe, wie ``http.py`` sie ablegt, mit dem Wunsch in den Vorgaben."""
    ordner = ORDNER if gruppe else ""
    rel = f"{ordner}/{nr:02d}.mp3" if ordner else f"{nr:02d}.mp3"
    erzeuge_audio(nas.eingang / rel, frequenz=300 + 7 * nr, **tags)
    integration.eingang.registriere_upload(rel, serie_id, gruppe, w)
    stille_zeitgeber(integration)  # die Durchläufe stößt der Test an
    return rel


def album_tags(nr: int, von: int) -> dict:
    return {"album": "Album X", "album_artist": "Künstler A", "track": f"{nr}/{von}", "title": f"Lied {nr}"}


async def pass_ohne_sofort(hass, integration) -> bool:
    """Ein Durchlauf ohne „sofort“. Gibt zurück, ob der Nachlauf („wartet noch etwas“) einen weiteren Durchlauf geplant hat.

    Die Zeitgeber werden danach abgemeldet (``stille_zeitgeber``), damit nur die Durchläufe des Tests laufen."""
    eingang = integration.eingang
    erg = await eingang.durchlauf_und_warten(sofort=False)
    assert erg["gestartet"] is True
    await hass.async_block_till_done()
    geplant = eingang._nachplan_abbruch is not None
    stille_zeitgeber(integration)
    return geplant


async def test_wunsch_neu_hoerbuch_zwoelf_dateien_gleiches_album_sind_eine_folge(hass, integration, nas):
    w = wunsch("neu", "hoerbuch", "Das große Hörbuch", 12)
    for i in range(1, 13):
        lege_upload(integration, nas, i, w, **album_tags(i, 12))
    erg = await integration.eingang.durchlauf_und_warten(sofort=False)  # Uploads übergehen die Ruhezeit
    await hass.async_block_till_done()
    assert erg["eintraege"] == 1
    serien = alle_serien(nas)
    assert list(serien) == ["Das große Hörbuch"]  # der Name des Wunsches, nicht „Künstler A“ aus den Tags
    serie = serien["Das große Hörbuch"]
    assert serie["folgen"] == ["Das große Hörbuch"]
    assert (serie["art"], serie["art_quelle"]) == ("hoerbuch", "manuell")
    assert not serie.get("einzeln") and "pruefen" not in serie
    assert folge_info(serie, "Das große Hörbuch")["anzeige"] == "Das große Hörbuch"
    assert "pruefen" not in folge_info(serie, "Das große Hörbuch")
    assert inhalt(nas.medien / serie["_ordner"] / "Das große Hörbuch") == [f"{i:02d}.mp3" for i in range(1, 13)]
    assert not (nas.eingang / ORDNER).exists()
    assert integration.eingang.protokoll[-1]["wunsch"] == {"ziel": "neu", "art": "hoerbuch"}
    assert integration.eingang.protokoll[-1]["ergebnis"][0]["tracks"] == 12
    integration.eingang.abbrechen()


async def test_wunsch_neu_musik_zwoelf_dateien_gleiches_album_sind_zwoelf_folgen(hass, integration, nas):
    w = wunsch("neu", "musik", "Meine Lieder", 12)
    for i in range(1, 13):
        lege_upload(integration, nas, i, w, **album_tags(i, 12))
    await pass_ohne_sofort(hass, integration)
    serien = alle_serien(nas)
    assert list(serien) == ["Meine Lieder"]
    serie = serien["Meine Lieder"]
    assert serie["folgen"] == [f"{i:02d}.mp3" for i in range(1, 13)]  # nach dem Track, nicht nach dem Zufall
    assert (serie["art"], serie["art_quelle"]) == ("musik", "manuell")
    assert [folge_info(serie, f"{i:02d}.mp3")["anzeige"] for i in (1, 2, 12)] == ["Lied 1", "Lied 2", "Lied 12"]  # der Titel, nicht das gemeinsame Album
    assert not any(folge_info(serie, n).get("pruefen") for n in serie["folgen"])  # der Wunsch ersetzt „Tags fehlen“ und „gleicher Name“
    assert len(integration.eingang.protokoll[-1]["ergebnis"]) == 12
    integration.eingang.abbrechen()


async def test_G2_drei_dateien_im_abstand_von_60_s_bleiben_eine_gruppe(hass, integration, nas, freezer):
    w = wunsch("neu", "hoerbuch", "Kapitän Knopf", 3)
    for i in (1, 2, 3):
        lege_upload(integration, nas, i, w, **album_tags(i, 3))
        geplant = await pass_ohne_sofort(hass, integration)
        if i < 3:  # die Sammelzeit von 20 s hätte hier schon einsortiert
            assert geplant is True  # der Eintrag wartet: der Nachlauf prüft in einer Minute wieder (so kommt die 30-Minuten-Grenze an die Reihe)
            assert alle_serien(nas) == {}
            eintrag = (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]
            assert eintrag["status"] == "wartet" and eintrag["dateien"] == i
            assert eintrag["wunsch"] == {"ziel": "neu", "art": "hoerbuch"}
            freezer.tick(timedelta(seconds=60))
    serie = alle_serien(nas)["Kapitän Knopf"]
    assert serie["folgen"] == ["Kapitän Knopf"]  # **eine** Folge, kein „… (2)“
    assert inhalt(nas.medien / serie["_ordner"] / "Kapitän Knopf") == ["01.mp3", "02.mp3", "03.mp3"]
    integration.eingang.abbrechen()


async def test_letzte_datei_fehlt_nach_30_minuten_ruhe_ist_die_gruppe_teilweise(hass, integration, nas, freezer):
    w = wunsch("neu", "hoerbuch", "Kapitän Knopf", 3)
    for i in (1, 2):
        lege_upload(integration, nas, i, w, **album_tags(i, 3))
    freezer.tick(timedelta(minutes=29))
    await pass_ohne_sofort(hass, integration)
    assert alle_serien(nas) == {}  # noch keine 30 Minuten Ruhe
    assert (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]["status"] == "wartet"
    freezer.tick(timedelta(minutes=2))
    await pass_ohne_sofort(hass, integration)
    serie = alle_serien(nas)["Kapitän Knopf"]
    assert inhalt(nas.medien / serie["_ordner"] / "Kapitän Knopf") == ["01.mp3", "02.mp3"]  # einsortiert, was da ist
    info = folge_info(serie, "Kapitän Knopf")
    assert info["pruefen"] is True and "gruppe_unvollstaendig" in info["pruefen_gruende"]  # „Bitte ansehen“
    eintrag = (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]
    assert eintrag["status"] == "teilweise"
    hinweis = next(h for h in eintrag["hinweise"] if h["code"] == "gruppe_unvollstaendig")
    assert "2 von 3" in hinweis["text"]
    assert eintrag["ergebnis"][0]["tracks"] == 2
    integration.eingang.abbrechen()


async def test_gruppe_wartet_solange_ein_upload_der_gruppe_noch_laeuft(hass, integration, nas, freezer):
    """Eine 2-GiB-Datei kann länger als 30 Minuten dauern: solange sie Bytes schickt, wartet der Eingang."""
    w = wunsch("neu", "hoerbuch", "Langes Buch", 2)
    lege_upload(integration, nas, 1, w, **album_tags(1, 2))
    integration.eingang.upload_beginnt(ORDNER)
    freezer.tick(timedelta(minutes=45))
    await pass_ohne_sofort(hass, integration)
    assert alle_serien(nas) == {}
    integration.eingang.upload_endet(ORDNER)
    assert integration.eingang.gruppen_aktiv == {}
    await pass_ohne_sofort(hass, integration)
    assert "Langes Buch" in alle_serien(nas)  # nun sind 30 Minuten Ruhe vorbei: teilweise
    assert (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]["status"] == "teilweise"
    integration.eingang.abbrechen()


async def test_wunsch_ergaenzen_geht_vor_die_tags(hass, integration, nas):
    nas.serie("ziel", "ziel", "Lange Serie", ["alt.mp3"], folgen_info={"alt.mp3": {"anzeige": "Folge 1", "nummer": 1}})
    erzeuge_audio(nas.medien / "ziel" / "alt.mp3", frequenz=900)
    await integration.medien.pruefen()
    w = wunsch("ergaenzen", None, None, 2)
    for i in (1, 2):
        lege_upload(integration, nas, i, w, serie_id="ziel", album="Anderes Album", album_artist="Ganz Andere", title=f"Neue Folge {i}", track=str(i))
    await pass_ohne_sofort(hass, integration)
    serien = alle_serien(nas)
    assert list(serien) == ["Lange Serie"]  # nicht „Ganz Andere“
    assert serien["Lange Serie"]["folgen"] == ["alt.mp3", "01.mp3", "02.mp3"]  # jede Datei eine neue Folge, nie ein Folgen-Ordner
    assert folge_info(serien["Lange Serie"], "02.mp3")["anzeige"] == "Neue Folge 2"
    integration.eingang.abbrechen()


async def test_wunsch_ergaenzen_in_einen_einzeltitel_faellt_auf_die_tags_zurueck(hass, integration, nas):
    nas.serie("lied", "lied", "Ein Lied", ["l.mp3"], einzeln=True)
    erzeuge_audio(nas.medien / "lied" / "l.mp3", frequenz=901)
    await integration.medien.pruefen()
    rel = lege_upload(integration, nas, 1, wunsch("ergaenzen"), serie_id="lied", gruppe=None, album="A", album_artist="Aus Tags")
    await pass_ohne_sofort(hass, integration)
    assert nas.serie_json("lied")["folgen"] == ["l.mp3"]  # in einen Einzeltitel kommt nichts Neues
    assert "Aus Tags" in alle_serien(nas)
    assert folge_info(alle_serien(nas)["Aus Tags"], rel)["pruefen_gruende"] == ["vorgabe_serie_fehlt"]
    integration.eingang.abbrechen()


async def test_wunsch_einzeln_ist_eine_serie_mit_einer_folge_und_im_suchindex(hass, integration, nas):
    rel = lege_upload(integration, nas, 1, wunsch("einzeln", "musik"), gruppe=None, album="Album Y", album_artist="Künstler B", title="Schlaflied der Sterne")
    await pass_ohne_sofort(hass, integration)
    serie = alle_serien(nas)["Schlaflied der Sterne"]  # Name = Titel der Datei
    assert serie["einzeln"] is True and serie["folgen"] == [rel]
    assert (serie["art"], serie["art_quelle"]) == ("musik", "manuell")
    assert folge_info(serie, rel)["anzeige"] == "Schlaflied der Sterne"
    # im Suchindex (A3): als Serie **und** als Folge
    treffer = (await integration.medien.serien_liste(text="sterne"))["serien"]
    assert [(s["name"], s["einzeln"], s["anzahl_folgen"]) for s in treffer] == [("Schlaflied der Sterne", True, 1)]
    zeilen = (await integration.medien.folgen_liste(text="sterne"))["folgen"]
    assert [(z["serie_name"], z["serie_einzeln"], z["folge"], z["anzeige"]) for z in zeilen] == [("Schlaflied der Sterne", True, rel, "Schlaflied der Sterne")]
    assert (await integration.medien.serien_liste(filter_=["einzeln"]))["gesamt"] == 1
    assert (await integration.medien.serien_liste(filter_=["sammlung"]))["gesamt"] == 0
    # Das Ziel eines Tobies ist die Folge
    await integration.zuordnung_setzen("04a1b2c3", {"typ": "folge", "serie": serie["id"], "folge": rel}, name="Sternchen")
    assert (await integration.medien.serien_liste(text="sterne"))["serien"][0]["anzahl_tobies"] == 1
    integration.eingang.abbrechen()


async def test_wunsch_einzeln_mit_name_und_je_datei_eine_serie(hass, integration, nas):
    lege_upload(integration, nas, 1, wunsch("einzeln", "geschichte", "Mein Name"), gruppe=None, title="Egal", album="A")
    lege_upload(integration, nas, 2, wunsch("einzeln", "musik"), gruppe=None, album="A", title="Zweites")
    await pass_ohne_sofort(hass, integration)
    serien = alle_serien(nas)
    assert set(serien) == {"Mein Name", "Zweites"} and all(s["einzeln"] and len(s["folgen"]) == 1 for s in serien.values())
    assert serien["Mein Name"]["art"] == "geschichte"
    integration.eingang.abbrechen()


async def test_einzeltitel_nimmt_keine_folgen_per_tags_auf(hass, integration, nas):
    lege_upload(integration, nas, 1, wunsch("einzeln", "musik", "Intro"), gruppe=None)
    await pass_ohne_sofort(hass, integration)
    erzeuge_audio(nas.eingang / "x.mp3", frequenz=777, album="Folge 2", album_artist="Intro")
    await sortiere(integration)
    serien = [json.loads(p.read_text()) for p in sorted(nas.medien.glob("*/serie.json"))]
    assert sorted((s["name"], len(s["folgen"]), bool(s.get("einzeln"))) for s in serien) == [("Intro", 1, False), ("Intro", 1, True)]
    integration.eingang.abbrechen()


async def test_wunsch_neu_fuehrt_nie_zusammen_gleicher_name_wird_zwei(hass, integration, nas):
    nas.serie("mond", "mond", "Mondlieder", [])
    await integration.medien.pruefen()
    lege_upload(integration, nas, 1, wunsch("neu", "musik", "Mondlieder"), gruppe=None, title="Lied")
    await pass_ohne_sofort(hass, integration)
    serien = alle_serien(nas)
    assert set(serien) == {"Mondlieder", "Mondlieder (2)"} and serien["Mondlieder"]["folgen"] == []
    assert "serie_name_doppelt" in [h["code"] for h in integration.eingang.protokoll[-1]["hinweise"]]
    integration.eingang.abbrechen()


async def test_auto_ist_kein_wunsch_und_bleibt_wie_vorher(hass, integration, nas):
    """``auto`` mit ``gruppe_anzahl``: der Eingang wartet auf alle, sortiert aber nach den Tags."""
    for i in (1, 2):
        lege_upload(integration, nas, i, wunsch("auto", None, None, 2), **album_tags(i, 2))
    await pass_ohne_sofort(hass, integration)
    serien = alle_serien(nas)
    assert list(serien) == ["Künstler A"] and serien["Künstler A"]["folgen"] == ["Album X"]  # eine Folge aus dem Album, wie bisher
    assert integration.eingang.protokoll[-1]["wunsch"] == {"ziel": "auto", "art": None}
    integration.eingang.abbrechen()


async def test_wunsch_steht_mit_ankunftszeit_in_den_persistenten_vorgaben(hass, integration, nas):
    w = wunsch("neu", "hoerbuch", "Buch", 3)
    lege_upload(integration, nas, 1, w, **album_tags(1, 3))
    gespeichert = integration.eingang._daten()["vorgaben"]
    assert gespeichert[f"{ORDNER}/01.mp3"]["wunsch"] == w and gespeichert[f"{ORDNER}/01.mp3"]["am"].endswith("Z")
    json.dumps(gespeichert)  # persistierbar
    integration.eingang.abbrechen()


# --------------------------------------------------------------------------
# Nachlese A3d (12.11.): ``quelle`` und ``pruefen`` in ``eingang/list``, ``serie_name_doppelt`` an der Serie
# --------------------------------------------------------------------------


async def test_eingang_list_quelle_upload_und_nas_pruefen_und_persistenz(hass, integration, nas):
    # ein Upload ohne Gruppe, ohne Serie, ohne Wunsch: früher spurlos in den Vorgaben, jetzt trotzdem als „upload“ gemerkt
    erzeuge_audio(nas.eingang / "hochgeladen.mp3", frequenz=311, album="Hoch", album_artist="Autor A")
    integration.eingang.registriere_upload("hochgeladen.mp3", None, None, None)
    erzeuge_audio(nas.eingang / "vom_nas.mp3", frequenz=322, album="Nas", album_artist="Autor B")
    stille_zeitgeber(integration)
    integration.eingang.geprueft_am = None  # (die Liste liest den Eingang neu)
    liste = (await integration.eingang.liste("offen", 50, 0))["eintraege"]
    assert {e["name"]: (e["quelle"], e["pruefen"]) for e in liste} == {"hochgeladen.mp3": ("upload", False), "vom_nas.mp3": ("nas", False)}
    # die Quelle gehört dem Eintrag und überlebt einen Neustart (Store) und einen blockierten Durchlauf
    assert integration.eingang._daten()["uploads"] == ["hochgeladen.mp3"]
    integration.eingang.upload_eintraege.clear()
    integration.eingang.eintraege.clear()
    integration.eingang.geprueft_am = None
    liste = (await integration.eingang.liste("offen", 50, 0))["eintraege"]
    assert {e["name"]: e["quelle"] for e in liste} == {"hochgeladen.mp3": "upload", "vom_nas.mp3": "nas"}
    await sortiere(integration)
    erledigt = (await integration.eingang.liste("erledigt", 50, 0))["eintraege"]
    assert {e["name"]: e["quelle"] for e in erledigt} == {"hochgeladen.mp3": "upload", "vom_nas.mp3": "nas"}
    assert integration.eingang.upload_quelle == set()  # erledigt: nichts mehr zu merken


async def test_eingang_list_pruefen_ist_wahr_wenn_ein_ergebnis_pruefen_hat(hass, integration, nas):
    # ohne Tags: Serie und Folge werden geraten, das Ergebnis trägt „pruefen“
    erzeuge_audio(nas.eingang / "ohne tags.mp3", frequenz=333)
    await sortiere(integration)
    e = (await integration.eingang.liste("erledigt", 50, 0))["eintraege"][0]
    assert e["pruefen"] is True and any(r["pruefen"] for r in e["ergebnis"])
    # ein altes Protokoll ohne die neuen Felder wird ergänzt
    integration.eingang.protokoll.append({"id": "0" * 12, "name": "alt", "art": "datei", "status": "erledigt", "ergebnis": [{"pruefen": True}]})
    alt = (await integration.eingang.liste("erledigt", 50, 0))["eintraege"][0]
    assert (alt["quelle"], alt["pruefen"]) == ("nas", True)


async def test_serie_name_doppelt_steht_auch_bei_serien_list_und_serie_get(hass, integration, nas):
    nas.serie("mond", "mond", "Mondlieder", [])
    await integration.medien.pruefen()
    lege_upload(integration, nas, 1, wunsch("neu", "musik", "Mondlieder"), gruppe=None, title="Lied")
    await pass_ohne_sofort(hass, integration)
    neu = next(s for s in alle_serien(nas).values() if s["name"] == "Mondlieder (2)")
    liste = (await integration.medien.serien_liste())["serien"]
    zeile = next(s for s in liste if s["id"] == neu["id"])
    assert [h["code"] for h in zeile["hinweise"]] == ["serie_name_doppelt"]
    assert "Mondlieder (2)" in zeile["hinweise"][0]["text"] and zeile["hinweise"][0]["folge"] is None
    assert next(s for s in liste if s["id"] == "mond")["hinweise"] == []
    assert [h["code"] for h in (await integration.medien.serie_holen(neu["id"]))["hinweise"]] == ["serie_name_doppelt"]
    # eine Prüfung der Freigabe lässt ihn stehen, ein Umbenennen blendet ihn aus
    await integration.medien.pruefen()
    assert [h["code"] for h in (await integration.medien.serie_holen(neu["id"]))["hinweise"]] == ["serie_name_doppelt"]
    await integration.medien.serie_umbenennen(neu["id"], "Sternlieder")
    assert (await integration.medien.serie_holen(neu["id"]))["hinweise"] == []
    integration.eingang.abbrechen()


# --------------------------------------------------------------------------
# Großer Sammel-Ordner mit vielen Unterordnern (Befund aus dem echten HA)
# --------------------------------------------------------------------------


def _pruefung_mit_defekten(*defekt: str):
    echt = ffprobe.pruefe_datei

    def tu_so(datei, endung=None):
        p = echt(datei, endung)
        if os.path.basename(datei) in defekt:
            return ffprobe.Pruefung("warnung", ffprobe.PROBEDEKODIERUNG, p.probe)
        return p

    return tu_so


async def test_sammelordner_je_buch_ein_album_nur_die_defekten_buecher_bleiben(hass, integration, nas):
    wurzel = nas.eingang / "Sammlung"
    for i in (1, 2, 3):
        erzeuge_audio(wurzel / "Buch A" / f"{i}.mp3", frequenz=300 + i, album="Buch A", album_artist="Autor")
        erzeuge_audio(wurzel / "Buch B" / f"{i}.mp3", frequenz=400 + i, album="Buch B", album_artist="Autor")
        erzeuge_audio(wurzel / "Buch C" / f"{i}.mp3", frequenz=500 + i, album="Buch C", album_artist="Autor")
    (wurzel / "Buch A" / "cover.jpg").write_bytes(b"x")
    # zwei Dateien in zwei verschiedenen Büchern lassen sich nicht dekodieren
    erzeuge_audio(wurzel / "Buch D" / "kaputt.mp3", frequenz=600, album="Buch D", album_artist="Autor")
    erzeuge_audio(wurzel / "Buch E" / "kaputt2.mp3", frequenz=700, album="Buch E", album_artist="Autor")
    with patch("custom_components.tobibox.eingang.ffprobe.pruefe_datei", side_effect=_pruefung_mit_defekten("kaputt.mp3", "kaputt2.mp3")):
        await sortiere(integration)
    serie = alle_serien(nas)["Autor"]
    assert sorted(serie["folgen"]) == ["Buch A", "Buch B", "Buch C"]
    eintrag = (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]
    assert eintrag["status"] == "teilweise"
    assert {(h["code"], h["datei"]) for h in eintrag["hinweise"]} == {
        ("probedekodierung_fehlgeschlagen", "Buch D/kaputt.mp3"),
        ("probedekodierung_fehlgeschlagen", "Buch E/kaputt2.mp3"),
    }
    assert (wurzel / "Buch D" / "kaputt.mp3").exists() and (wurzel / "Buch E" / "kaputt2.mp3").exists()
    assert not (wurzel / "Buch A").exists() or not list((wurzel / "Buch A").glob("*.mp3"))


async def test_T21_sammelordner_teil_ist_unterordner_cd_ordner_gehoeren_zum_teil(hass, integration, nas):
    wurzel = nas.eingang / "Sammlung"
    for i in (1, 2, 3):
        erzeuge_audio(wurzel / "Buch A" / f"{i}.mp3", frequenz=300 + i)  # ohne Tags
    erzeuge_audio(wurzel / "Buch B" / "kaputt.mp3", frequenz=400, album="Gemeinsam", album_artist="Autor B")
    erzeuge_audio(wurzel / "Buch B" / "heil.mp3", frequenz=401, album="Gemeinsam", album_artist="Autor B")
    erzeuge_audio(wurzel / "Buch C" / "CD1" / "1.mp3", frequenz=501, album="Gemeinsam", album_artist="Autor C", track="1")
    erzeuge_audio(wurzel / "Buch C" / "CD2" / "1.mp3", frequenz=502, album="Gemeinsam", album_artist="Autor C", track="1", disc="2")
    with patch("custom_components.tobibox.eingang.ffprobe.pruefe_datei", side_effect=_pruefung_mit_defekten("kaputt.mp3")):
        await sortiere(integration)
    serien = alle_serien(nas)
    a = serien["Buch A"]
    assert a["folgen"] == ["Buch A"]
    assert inhalt(nas.medien / a["_ordner"] / "Buch A") == ["1.mp3", "2.mp3", "3.mp3"]
    assert set(folge_info(a, "Buch A")["pruefen_gruende"]) == {"tags_fehlen", "serie_aus_ordner"}
    c = serien["Autor C"]
    assert c["folgen"] == ["Gemeinsam"]  # CD1 und CD2 sind eine Folge
    assert len(list((nas.medien / c["_ordner"] / "Gemeinsam").glob("*.mp3"))) == 2
    # Buch B bleibt ganz im Eingang, der Rest ist einsortiert
    assert "Autor B" not in serien
    assert (wurzel / "Buch B" / "kaputt.mp3").exists() and (wurzel / "Buch B" / "heil.mp3").exists()
    eintrag = (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]
    assert eintrag["status"] == "teilweise"
    assert {(h["code"], h["datei"]) for h in eintrag["hinweise"]} == {("probedekodierung_fehlgeschlagen", "Buch B/kaputt.mp3")}


async def test_hoerspiel_mit_unterordner_je_folge_gleiches_album_sind_mehrere_folgen(hass, integration, nas):
    for n in (1, 2, 3):
        for i in (1, 2):
            erzeuge_audio(nas.eingang / "Serie" / f"Folge {n}" / f"{i}.mp3", frequenz=300 + 10 * n + i, album="Serie", album_artist="Sprecher")
    await sortiere(integration)
    serie = alle_serien(nas)["Sprecher"]
    assert len(serie["folgen"]) == 3
    for name in serie["folgen"]:
        assert len(list((nas.medien / serie["_ordner"] / name).glob("*.mp3"))) == 2


async def test_dateien_direkt_im_eintrag_und_unterordner_sind_verschiedene_teile(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Box" / "lose1.mp3", frequenz=301)
    erzeuge_audio(nas.eingang / "Box" / "lose2.mp3", frequenz=302)
    erzeuge_audio(nas.eingang / "Box" / "Teil Eins" / "a.mp3", frequenz=303)
    erzeuge_audio(nas.eingang / "Box" / "Teil Eins" / "b.mp3", frequenz=304)
    erzeuge_audio(nas.eingang / "Box" / "cd 1" / "c.mp3", frequenz=305)  # CD-Ordner: gehört zum Eintrag selbst
    await sortiere(integration)
    serien = alle_serien(nas)
    assert set(serien) == {"Box", "Teil Eins"}
    assert serien["Box"]["folgen"] == ["Box"]
    assert len(list((nas.medien / serien["Box"]["_ordner"] / "Box").glob("*.mp3"))) == 3
    assert serien["Teil Eins"]["folgen"] == ["Teil Eins"]


def test_cd_ordner_erkennung_und_teil():
    from custom_components.tobibox.eingang import ist_cd_ordner, teil_von

    for ja in ("CD1", "cd 2", "Disc 1", "DISK 02", "CD 10"):
        assert ist_cd_ordner(ja), ja
    for nein in ("CD", "Disc Jockey", "Buch 1", "CDs 1", "Hörbuch CD1"):
        assert not ist_cd_ordner(nein), nein
    assert teil_von("a.mp3") is None
    assert teil_von("CD1/a.mp3") is None
    assert teil_von("Buch/a.mp3") == "Buch"
    assert teil_von("Buch/CD2/a.mp3") == "Buch"
    assert teil_von("Buch/Kapitel/a.mp3") == "Buch"


async def test_wunsch_ergaenzen_ohne_tags_macht_keinen_fehlalarm_serie_geraten(hass, integration, nas):
    """Die Serie ist ausdrücklich gewählt (V-7): ``serie_aus_ordner`` und Verwandte sind dann falsch."""
    nas.serie("ziel", "ziel", "Test-Serie", [])
    await integration.medien.pruefen()
    rel = lege_upload(integration, nas, 1, wunsch("ergaenzen"), serie_id="ziel", gruppe=None)
    await pass_ohne_sofort(hass, integration)
    info = folge_info(alle_serien(nas)["Test-Serie"], rel)
    assert not info.get("pruefen") and not info.get("pruefen_gruende")
    erg = integration.eingang.protokoll[-1]
    assert erg["ergebnis"][0]["pruefen"] is False and erg["ergebnis"][0]["pruefen_gruende"] == []
    assert not (await integration.eingang.liste("alle", 50, 0))["eintraege"][0]["pruefen"]
    integration.eingang.abbrechen()


async def test_wunsch_ergaenzen_behaelt_echte_gruende_nummer_doppelt(hass, integration, nas):
    nas.serie("ziel", "ziel", "Test-Serie", ["alt.mp3"], folgen_info={"alt.mp3": {"anzeige": "Folge 1", "nummer": 1}})
    erzeuge_audio(nas.medien / "ziel" / "alt.mp3", frequenz=900)
    await integration.medien.pruefen()
    rel = lege_upload(integration, nas, 1, wunsch("ergaenzen"), serie_id="ziel", gruppe=None, title="Folge 1")
    await pass_ohne_sofort(hass, integration)
    info = folge_info(alle_serien(nas)["Test-Serie"], rel)
    assert "nummer_doppelt" in info["pruefen_gruende"] and "serie_aus_ordner" not in info["pruefen_gruende"]
    integration.eingang.abbrechen()


async def test_upload_mit_serie_vorgabe_ohne_wunsch_hat_keine_serie_geraten_gruende(hass, integration, nas):
    nas.serie("ziel", "ziel", "Test-Serie", [])
    await integration.medien.pruefen()
    erzeuge_audio(nas.eingang / "Upload abcd1234" / "x.mp3")
    integration.eingang.registriere_upload("Upload abcd1234/x.mp3", "ziel", None)
    await integration.eingang.durchlauf_und_warten(sofort=False)
    await hass.async_block_till_done()
    info = folge_info(alle_serien(nas)["Test-Serie"], "x.mp3")
    assert not set(info.get("pruefen_gruende", [])) & {"serie_aus_ordner", "serie_aus_interpret", "serie_widerspruch"}
    integration.eingang.abbrechen()
