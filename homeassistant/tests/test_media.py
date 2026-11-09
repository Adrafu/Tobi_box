"""Medienverwaltung (Vertrag W, 3.2, 3.3, Abschnitt 12; ``data-model.md`` Abschnitte 5 und 9)."""

from __future__ import annotations

import json
import os
import unicodedata
from unittest.mock import patch

import pytest

from custom_components.tobibox import ffprobe, media
from custom_components.tobibox.fehler import TobiboxFehler
from custom_components.tobibox.media import einfuege_index

from .conftest import braucht_ffmpeg

pytestmark = braucht_ffmpeg

UID1 = "e0040312345678ab"
UID2 = "04a1b2c3"


# --- Neue Ordner und Dateien erkennen (Entscheidung F, D2) ---


async def test_neuer_ordner_ohne_serie_json_bekommt_serie_json(hass, integration, nas, lege_mp3):
    hub = integration
    lege_mp3(nas.medien / "Der Rabe" / "folge-10.mp3")
    lege_mp3(nas.medien / "Der Rabe" / "folge-2.mp3")
    erg = await hub.medien.pruefen()
    assert erg.neue_serien == 1
    assert erg.neue_folgen == 2
    daten = nas.serie_json("Der Rabe")
    assert daten["schema_version"] == 1
    assert daten["id"] == "Der Rabe"  # ID = Ordnername, damit Zeiger und Zuordnungen erhalten bleiben (data-model.md)
    assert daten["name"] == "Der Rabe"
    assert daten["typ"] == "normal"
    assert daten["folgen"] == ["folge-2.mp3", "folge-10.mp3"]  # natürliche Sortierung
    assert daten["angelegt_am"].endswith("Z")
    assert hub.medien.serien["Der Rabe"].ordner == "Der Rabe"


async def test_neue_datei_kommt_hinten_dran_und_fehlende_faellt_heraus(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("rabe", "rabe", "Rabe", ["b.mp3", "a.mp3", "weg.mp3"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    lege_mp3(pfad / "neu.mp3")
    erg = await hub.medien.pruefen()
    assert nas.serie_json("rabe")["folgen"] == ["b.mp3", "a.mp3", "neu.mp3"]  # Reihenfolge von Hand bleibt, Neues hinten
    assert erg.neue_folgen == 1
    assert erg.entfernte_folgen == 1
    codes = [h["code"] for h in hub.medien.serien["rabe"].hinweise]
    assert "datei_fehlt" in codes


async def test_dotfiles_und_fremde_endungen_sind_keine_folgen(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.medien / "serie"
    lege_mp3(pfad / "a.MP3")
    lege_mp3(pfad / "._a.mp3")
    (pfad / "cover.jpg").write_bytes(b"x")
    (pfad / "notizen.txt").write_text("x")
    await hub.medien.pruefen()
    assert nas.serie_json("serie")["folgen"] == ["a.MP3"]


async def test_folgen_ordner_mit_tracks_ist_eine_folge(hass, integration, nas, lege_mp3):
    hub = integration
    lege_mp3(nas.medien / "serie" / "CD Schatzinsel" / "01.mp3")
    lege_mp3(nas.medien / "serie" / "CD Schatzinsel" / "02.mp3")
    (nas.medien / "serie" / "leerer Ordner").mkdir()
    (nas.medien / "serie" / "nur Bilder").mkdir()
    (nas.medien / "serie" / "nur Bilder" / "x.jpg").write_bytes(b"x")
    await hub.medien.pruefen()
    assert nas.serie_json("serie")["folgen"] == ["CD Schatzinsel"]
    folge = (await hub.medien.serie_holen("serie"))["folgen"][0]
    assert folge["art"] == "ordner"
    assert folge["tracks"] == 2
    assert folge["groesse_bytes"] > 0


async def test_serie_json_behaelt_unbekannte_felder(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("rabe", "rabe", "Rabe", ["a.mp3"], zukunft={"x": [1, 2]}, folgen_info={"a.mp3": {"anzeige": "A", "unbekannt": 7}})
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    await hub.medien.pruefen()
    daten = nas.serie_json("rabe")
    assert daten["zukunft"] == {"x": [1, 2]}
    assert daten["folgen_info"]["a.mp3"] == {"anzeige": "A", "unbekannt": 7}
    assert daten["folgen"] == ["a.mp3", "b.mp3"]
    await hub.medien.serie_umbenennen("rabe", "Neuer Name")
    assert nas.serie_json("rabe")["zukunft"] == {"x": [1, 2]}


async def test_kaputte_serie_json_wird_repariert(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.medien / "kaputt"
    lege_mp3(pfad / "a.mp3")
    (pfad / "serie.json").write_text('{"schema_version": 1, "id": "k1", "name": ')
    await hub.medien.pruefen()
    daten = nas.serie_json("kaputt")
    assert daten["id"] == "kaputt"
    assert daten["folgen"] == ["a.mp3"]
    assert "serie_json_ungueltig_repariert" in [h["code"] for h in hub.medien.serien["kaputt"].hinweise]


async def test_doppelte_id_juengere_kopie_bekommt_neue_id(hass, integration, nas):
    hub = integration
    nas.serie("alt", "gleich", "Alt", angelegt_am="2026-11-01T10:00:00Z")
    nas.serie("neu", "gleich", "Neu", angelegt_am="2026-11-05T10:00:00Z")
    await hub.medien.pruefen()
    assert nas.serie_json("alt")["id"] == "gleich"
    neue_id = nas.serie_json("neu")["id"]
    assert neue_id != "gleich"
    assert len(neue_id) == 12
    assert set(hub.medien.serien) == {"gleich", neue_id}
    assert "doppelte_id_korrigiert" in [h["code"] for h in hub.medien.serien[neue_id].hinweise]


async def test_stand_aendert_sich_bei_aenderung_von_aussen(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("rabe", "rabe", "Rabe", ["a.mp3"])
    lege_mp3(pfad / "a.mp3")
    await hub.medien.pruefen()
    stand1 = (await hub.medien.serie_holen("rabe"))["stand"]
    assert len(stand1) == 16
    daten = nas.serie_json("rabe")
    daten["name"] = "Von außen umbenannt"
    (pfad / "serie.json").write_text(json.dumps(daten))
    stand2 = (await hub.medien.serie_holen("rabe"))["stand"]
    assert stand2 != stand1
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.folgen_ordnen("rabe", ["a.mp3"], stand1)
    assert err.value.code == "stand_veraltet"


# --- reservierte Ordner (Abschnitt 12) ---


async def test_reservierte_ordner_sind_keine_serien(hass, integration, nas, lege_mp3):
    hub = integration
    lege_mp3(nas.medien / "eingang" / "x.mp3")
    lege_mp3(nas.medien / "EINGANG2" / "x.mp3")
    lege_mp3(nas.medien / "_geheim" / "x.mp3")
    (nas.medien / "_upload").mkdir(exist_ok=True)
    nas.papierkorb.mkdir(exist_ok=True)
    await hub.medien.pruefen()
    assert not (nas.medien / "eingang" / "serie.json").exists()
    assert not (nas.medien / "_geheim" / "serie.json").exists()
    assert not (nas.medien / "_upload" / "serie.json").exists()
    assert not (nas.papierkorb / "serie.json").exists()
    assert set(hub.medien.serien) == {"EINGANG2"}  # nur "eingang" selbst ist reserviert
    liste = await hub.medien.serien_liste()
    hinweise = {h["folge"]: h["code"] for h in liste["hinweise"]}
    assert hinweise == {"eingang": "reservierter_ordner", "_geheim": "reservierter_ordner"}


async def test_serie_anlegen_mit_namen_eingang_ergibt_ordner_eingang_2(hass, integration, nas):
    hub = integration
    erg = await hub.medien.serie_anlegen("Eingang")
    assert erg["ordner"] == "Eingang (2)"
    assert erg["name"] == "Eingang"
    assert (nas.medien / "Eingang (2)" / "serie.json").exists()
    assert not (nas.medien / "Eingang").exists()


# --- Serie anlegen: Namensregeln für SMB (Abschnitt 12) ---


async def test_serie_anlegen_ordnername_nach_smb_regeln(hass, integration, nas):
    hub = integration
    erg = await hub.medien.serie_anlegen("Die drei ???: Folge 1 / Teil 2")
    assert erg["ordner"] == "Die drei ___ - Folge 1 _ Teil 2"
    assert erg["name"] == "Die drei ???: Folge 1 / Teil 2"  # Anzeigename bleibt frei, ':' erlaubt
    daten = nas.serie_json(erg["ordner"])
    assert daten["id"] == erg["id"]
    assert len(erg["id"]) == 12
    assert daten["typ"] == "normal"
    assert daten["folgen"] == []
    assert daten["angelegt_am"].endswith("Z")


async def test_serie_anlegen_gleicher_name_ohne_gross_kleinschreibung_bekommt_suffix(hass, integration, nas):
    hub = integration
    a = await hub.medien.serie_anlegen("Rabe")
    b = await hub.medien.serie_anlegen("RABE")
    c = await hub.medien.serie_anlegen("rabe")
    assert (a["ordner"], b["ordner"], c["ordner"]) == ("Rabe", "RABE (2)", "rabe (3)")
    assert len({a["id"], b["id"], c["id"]}) == 3  # die ID ist zufällig, der Ordnername nicht die ID
    nas.serie_json("RABE (2)")


async def test_serie_anlegen_nfc_und_nfd_sind_derselbe_name(hass, integration, nas):
    hub = integration
    nfc = unicodedata.normalize("NFC", "Hörspiel")
    nfd = unicodedata.normalize("NFD", "Hörspiel")
    a = await hub.medien.serie_anlegen(nfd)
    b = await hub.medien.serie_anlegen(nfc)
    assert a["ordner"] == nfc  # neue Namen sind NFC
    assert b["ordner"] == f"{nfc} (2)"


async def test_serie_anlegen_kuerzt_an_zeichengrenze(hass, integration, nas):
    hub = integration
    name = "ä" * 100  # 200 Bytes, aber der Ordnername darf höchstens 250 Bytes haben: passt
    erg = await hub.medien.serie_anlegen(name)
    assert erg["ordner"] == name
    lang = "😀" * 100  # 400 Bytes, 200 UTF-16-Einheiten
    erg = await hub.medien.serie_anlegen(lang)
    assert len(erg["ordner"].encode("utf-8")) <= 250
    assert erg["ordner"].encode("utf-8").decode("utf-8") == erg["ordner"]
    assert erg["name"] == lang  # Anzeigename wird nicht gekürzt (100 Zeichen sind erlaubt)


@pytest.mark.parametrize("name", ["", "   ", "\x00\x01", "x" * 101])
async def test_serie_anlegen_ungueltiger_name(hass, integration, name):
    with pytest.raises(TobiboxFehler) as err:
        await integration.medien.serie_anlegen(name)
    assert err.value.code == "name_ungueltig"


async def test_ueberraschungs_serie(hass, integration, nas):
    hub = integration
    assert (await hub.medien.serien_liste())["ueberraschung"] == "fehlt"
    await hub.medien.serie_anlegen("Überraschung", "ueberraschung")
    assert (await hub.medien.serien_liste())["ueberraschung"] == "leer"
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.serie_anlegen("Noch eine", "ueberraschung")
    assert err.value.code == "ueberraschung_existiert"


# --- Umbenennen, Reihenfolge ---


async def test_umbenennen_aendert_nur_anzeigenamen(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("ordner-alt", "id1", "Alt", ["a.mp3"], pruefen=True, pruefen_gruende=["tags_fehlen"])
    lege_mp3(pfad / "a.mp3")
    await hub.medien.pruefen()
    erg = await hub.medien.serie_umbenennen("id1", "  Neuer: Name  ")
    assert erg["name"] == "Neuer: Name"
    assert erg["ordner"] == "ordner-alt"
    assert erg["pruefen"] is False  # löscht das Kennzeichen "bitte prüfen"
    daten = nas.serie_json("ordner-alt")
    assert daten["id"] == "id1"
    assert "pruefen" not in daten
    erg = await hub.medien.folge_umbenennen("id1", "a.mp3", "Folge 1: Der Anfang", None)
    assert erg["folge"]["anzeige"] == "Folge 1: Der Anfang"
    assert erg["folge"]["name"] == "a.mp3"  # der Schlüssel (Dateiname) bleibt
    assert (nas.medien / "ordner-alt" / "a.mp3").exists()
    assert nas.serie_json("ordner-alt")["folgen"] == ["a.mp3"]


async def test_umbenennen_gleicher_name_schreibt_nichts(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("o", "id1", "Gleich", ["a.mp3"])
    lege_mp3(pfad / "a.mp3")
    await hub.medien.pruefen()
    vorher = (pfad / "serie.json").stat().st_mtime_ns
    await hub.medien.serie_umbenennen("id1", "Gleich")
    assert (pfad / "serie.json").stat().st_mtime_ns == vorher


async def test_reihenfolge_muss_umstellung_sein(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("o", "id1", "S", ["a.mp3", "b.mp3", "c.mp3"])
    for n in ("a", "b", "c"):
        lege_mp3(pfad / f"{n}.mp3")
    await hub.medien.pruefen()
    erg = await hub.medien.folgen_ordnen("id1", ["c.mp3", "a.mp3", "b.mp3"], None)
    assert nas.serie_json("o")["folgen"] == ["c.mp3", "a.mp3", "b.mp3"]
    assert erg["stand"]
    for falsch in (["a.mp3", "b.mp3"], ["a.mp3", "b.mp3", "c.mp3", "d.mp3"], ["a.mp3", "a.mp3", "b.mp3"], ["a.mp3", "b.mp3", "x.mp3"]):
        with pytest.raises(TobiboxFehler) as err:
            await hub.medien.folgen_ordnen("id1", falsch, None)
        assert err.value.code == "reihenfolge_ungueltig"


def test_einfuegeregel_11_6():
    infos = {"a": {"nummer": 1}, "b": {"nummer": 2}, "c": {"nummer": 3}}
    folgen = ["a", "b", "c", "ohne"]
    assert einfuege_index(folgen, infos, 4) == 3  # hinter 3, vor der Folge ohne Nummer
    assert einfuege_index(folgen, infos, 2) == 2  # hinter der vorhandenen 2
    assert einfuege_index(folgen, infos, 0) == 0  # vor der ersten größeren
    assert einfuege_index(folgen, infos, None) == 4  # ohne Nummer: hinten
    assert einfuege_index(["x", "y"], {}, 5) == 2  # gar keine Nummern: hinten


# --- Prüfung nach D5: Kopierschutz und Probedekodierung ---


async def test_kopierschutz_wird_als_warnung_aufgenommen(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.medien / "kauf"
    lege_mp3(pfad / "ok.mp3")
    lege_mp3(pfad / "drm.m4a".replace("m4a", "mp3"))
    echte = ffprobe.pruefe_datei

    def tu_so(datei, endung=None):
        if os.path.basename(datei) == "drm.mp3":
            return ffprobe.Pruefung("warnung", ffprobe.KOPIERSCHUTZ)
        return echte(datei, endung)

    with patch("custom_components.tobibox.media.ffprobe.pruefe_datei", side_effect=tu_so):
        await hub.medien.pruefen()
    s = await hub.medien.serie_holen("kauf")
    folgen = {f["name"]: f for f in s["folgen"]}
    assert folgen["drm.mp3"]["pruefung"] == "warnung"
    assert folgen["drm.mp3"]["hinweis"] == "kopierschutz"
    assert folgen["ok.mp3"]["pruefung"] == "ok"
    assert "drm.mp3" in nas.serie_json("kauf")["folgen"]  # von außen gekommene Dateien werden aufgenommen (Version 1)
    assert {"code": "kopierschutz", "folge": "drm.mp3"}.items() <= {k: v for h in s["hinweise"] for k, v in h.items() if h["code"] == "kopierschutz"}.items()


async def test_probedekodierung_fehlgeschlagen(hass, integration, nas, lege_mp3):
    hub = integration
    lege_mp3(nas.medien / "s" / "a.mp3")
    with patch("custom_components.tobibox.ffprobe.probedekodierung", return_value=False):
        await hub.medien.pruefen()
    f = (await hub.medien.serie_holen("s"))["folgen"][0]
    assert (f["pruefung"], f["hinweis"]) == ("warnung", "probedekodierung_fehlgeschlagen")


async def test_ffprobe_fehlt_pruefung_nicht_moeglich(hass, integration, nas, lege_mp3):
    hub = integration
    lege_mp3(nas.medien / "s" / "a.mp3")
    with patch("custom_components.tobibox.ffprobe.ffprobe_pfad", return_value=None):
        await hub.medien.pruefen()
    f = (await hub.medien.serie_holen("s"))["folgen"][0]
    assert f["pruefung"] == "nicht_moeglich"
    assert "pruefung_nicht_moeglich" in [h["code"] for h in hub.medien.serien["s"].hinweise]


# --- Papierkorb (data-model.md, Abschnitt 9) ---


async def test_folge_loeschen_legt_meta_json_an_und_stellt_wieder_her(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("o", "id1", "Rabe", ["a.mp3", "b.mp3", "c.mp3"], folgen_info={"b.mp3": {"anzeige": "Zwei", "nummer": 2}})
    for n in ("a", "b", "c"):
        lege_mp3(pfad / f"{n}.mp3")
    await hub.medien.pruefen()
    erg = await hub.medien.folge_loeschen("id1", "b.mp3", False, None)
    eintrag = erg["eintrag"]
    assert erg["betroffene_tobies"] == []
    assert not (pfad / "b.mp3").exists()
    assert nas.serie_json("o")["folgen"] == ["a.mp3", "c.mp3"]
    assert "b.mp3" not in nas.serie_json("o").get("folgen_info", {})
    eintrag_pfad = nas.papierkorb / eintrag["id"]
    meta = json.loads((eintrag_pfad / "meta.json").read_text())
    assert meta["schema_version"] == 1
    assert meta["id"] == eintrag["id"] and len(meta["id"]) == 12
    assert (meta["typ"], meta["grund"], meta["serie_id"], meta["serie_name"], meta["serie_ordner"]) == ("folge", "manuell", "id1", "Rabe", "o")
    assert (meta["name"], meta["art"], meta["dateien"]) == ("b.mp3", "datei", 1)
    assert meta["folge_info"] == {"anzeige": "Zwei", "nummer": 2}
    assert meta["serie_json"] is None
    assert (eintrag_pfad / "inhalt" / "b.mp3").exists()
    liste = await hub.medien.papierkorb_liste(100, 0)
    assert liste["gesamt"] == 1
    assert liste["eintraege"][0]["folge"] == "b.mp3"
    assert liste["eintraege"][0]["anzeige"] == "Zwei"
    # wiederherstellen: hinten in folgen, folgen_info aus meta.json
    wieder = await hub.medien.papierkorb_wiederherstellen(eintrag["id"], None)
    assert wieder["folge"] == "b.mp3"
    assert nas.serie_json("o")["folgen"] == ["a.mp3", "c.mp3", "b.mp3"]
    assert nas.serie_json("o")["folgen_info"]["b.mp3"] == {"anzeige": "Zwei", "nummer": 2}
    assert not eintrag_pfad.exists()
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.papierkorb_wiederherstellen(eintrag["id"], None)
    assert err.value.code == "eintrag_nicht_gefunden"


async def test_zwei_gleichnamige_folgen_im_papierkorb_kollidieren_nicht(hass, integration, nas, lege_mp3):
    hub = integration
    p1 = nas.serie("o1", "id1", "Eins", ["x.mp3"])
    p2 = nas.serie("o2", "id2", "Zwei", ["x.mp3"])
    lege_mp3(p1 / "x.mp3")
    lege_mp3(p2 / "x.mp3")
    await hub.medien.pruefen()
    e1 = (await hub.medien.folge_loeschen("id1", "x.mp3", False, None))["eintrag"]
    e2 = (await hub.medien.folge_loeschen("id2", "x.mp3", False, None))["eintrag"]
    assert e1["id"] != e2["id"]
    assert (await hub.medien.papierkorb_liste(100, 0))["gesamt"] == 2


async def test_folge_wiederherstellen_in_andere_serie_und_namenskonflikt(hass, integration, nas, lege_mp3):
    hub = integration
    p1 = nas.serie("o1", "id1", "Eins", ["x.mp3"])
    p2 = nas.serie("o2", "id2", "Zwei", [])
    lege_mp3(p1 / "x.mp3")
    await hub.medien.pruefen()
    eintrag = (await hub.medien.folge_loeschen("id1", "x.mp3", False, None))["eintrag"]
    erg = await hub.medien.papierkorb_wiederherstellen(eintrag["id"], "id2")
    assert erg["serie"]["id"] == "id2"
    assert (p2 / "x.mp3").exists()
    # derselbe Name noch einmal: datei_existiert
    lege_mp3(p1 / "x.mp3")
    await hub.medien.pruefen()
    e2 = (await hub.medien.folge_loeschen("id1", "x.mp3", False, None))["eintrag"]
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.papierkorb_wiederherstellen(e2["id"], "id2")
    assert err.value.code == "datei_existiert"
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.papierkorb_wiederherstellen(e2["id"], "gibtsnicht")
    assert err.value.code == "serie_nicht_gefunden"


async def test_serie_loeschen_und_wiederherstellen(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("Rabenserie", "id1", "Rabe", ["a.mp3", "CD"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "CD" / "01.mp3")
    await hub.medien.pruefen()
    erg = await hub.medien.serie_loeschen("id1", False, None)
    assert erg["ueberraschung"] == "fehlt"
    assert not pfad.exists()
    meta = json.loads((nas.papierkorb / erg["eintrag"]["id"] / "meta.json").read_text())
    assert (meta["typ"], meta["serie_id"], meta["serie_ordner"], meta["name"], meta["art"]) == ("serie", "id1", "Rabenserie", "Rabenserie", "ordner")
    assert meta["serie_json"]["id"] == "id1"
    assert meta["dateien"] == 2
    assert "id1" not in hub.medien.serien
    # inzwischen gibt es einen gleichnamigen Ordner: Suffix, die Serien-ID bleibt
    (nas.medien / "rabenserie").mkdir()
    wieder = await hub.medien.papierkorb_wiederherstellen(erg["eintrag"]["id"], None)
    assert wieder["serie"]["id"] == "id1"
    assert wieder["serie"]["ordner"] == "Rabenserie (2)"
    assert nas.serie_json("Rabenserie (2)")["id"] == "id1"
    assert (nas.medien / "Rabenserie (2)" / "CD" / "01.mp3").exists()


async def test_serie_wiederherstellen_mit_vergebener_id(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("o", "id1", "Rabe", ["a.mp3"])
    lege_mp3(pfad / "a.mp3")
    await hub.medien.pruefen()
    erg = await hub.medien.serie_loeschen("id1", False, None)
    nas.serie("anders", "id1", "Anders")
    await hub.medien.pruefen()
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.papierkorb_wiederherstellen(erg["eintrag"]["id"], None)
    assert err.value.code == "serie_existiert"


async def test_papierkorb_leeren_ohne_automatik(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("o", "id1", "Rabe", ["a.mp3", "b.mp3"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    await hub.medien.pruefen()
    e1 = (await hub.medien.folge_loeschen("id1", "a.mp3", False, None))["eintrag"]
    await hub.medien.folge_loeschen("id1", "b.mp3", False, None)
    assert (await hub.medien.papierkorb_liste(100, 0))["gesamt"] == 2  # es gibt keine Automatik
    erg = await hub.medien.papierkorb_leeren([e1["id"]])
    assert erg["geloescht"] == 1
    assert erg["freigegeben_bytes"] > 0
    assert (await hub.medien.papierkorb_liste(100, 0))["gesamt"] == 1
    erg = await hub.medien.papierkorb_leeren(None)
    assert erg["geloescht"] == 1
    assert list(nas.papierkorb.iterdir()) == []
    assert (await hub.medien.papierkorb_leeren(None))["geloescht"] == 0  # leerer Papierkorb: kein Fehler


async def test_unvollstaendiger_papierkorb_eintrag_wird_nicht_angeboten(hass, integration, nas):
    hub = integration
    (nas.papierkorb / "0123456789ab").mkdir(parents=True)
    (nas.papierkorb / "0123456789ab" / "inhalt").mkdir()  # meta.json fehlt
    (nas.papierkorb / "ba9876543210").mkdir()
    assert (await hub.medien.papierkorb_liste(100, 0))["gesamt"] == 0


# --- Löschen mit Tobies: Rückfrage, Zuordnung bleibt ---


async def test_loeschen_mit_tobies_verlangt_bestaetigung_und_laesst_zuordnung_stehen(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("o", "id1", "Rabe", ["a.mp3", "b.mp3"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    await hub.medien.pruefen()
    await hub.zuordnung_setzen(UID1, {"typ": "folge", "serie": "id1", "folge": "a.mp3"}, name="Rabe aus Holz")
    await hub.zuordnung_setzen(UID2, {"typ": "serie", "serie": "id1"})
    revision = hub.store.konfig["revision"]
    s = await hub.medien.serie_holen("id1")
    assert s["zuordnungen"] == [{"uid": UID2, "name": None}]  # Serien-Tobies stehen bei der Serie
    assert s["folgen"][0]["tobies"] == [{"uid": UID1, "name": "Rabe aus Holz"}]  # Folgen-Tobies bei der Folge
    assert s["anzahl_tobies"] == 2
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.folge_loeschen("id1", "a.mp3", False, None)
    assert err.value.code == "tobies_betroffen"
    assert (pfad / "a.mp3").exists()
    erg = await hub.medien.folge_loeschen("id1", "a.mp3", True, None)
    assert erg["betroffene_tobies"] == [{"uid": UID1, "name": "Rabe aus Holz"}]
    assert hub.store.konfig["revision"] == revision  # Zuordnung bleibt, keine neue Revision
    assert UID1 in hub.store.konfig["zuordnungen"]
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.serie_loeschen("id1", False, None)
    assert err.value.code == "tobies_betroffen"
    erg = await hub.medien.serie_loeschen("id1", True, None)
    assert {t["uid"] for t in erg["betroffene_tobies"]} == {UID1, UID2}
    assert hub.store.konfig["revision"] == revision


# --- Verschieben und Zusammenführen (Entscheidung M) ---


async def test_folge_verschieben_schreibt_zuordnungen_um(hass, integration, nas, lege_mp3, box_fabrik):
    hub = integration
    q = nas.serie("quelle", "q", "Quelle", ["folge-1.mp3", "folge-2.mp3"], folgen_info={"folge-2.mp3": {"anzeige": "Zwei", "nummer": 2, "pruefen": True, "pruefen_gruende": ["tags_fehlen"]}})
    z = nas.serie("ziel", "z", "Ziel", ["folge-1.mp3", "folge-3.mp3"], folgen_info={"folge-1.mp3": {"nummer": 1}, "folge-3.mp3": {"nummer": 3}})
    for n in ("folge-1.mp3", "folge-2.mp3"):
        lege_mp3(q / n)
    for n in ("folge-1.mp3", "folge-3.mp3"):
        lege_mp3(z / n)
    await hub.medien.pruefen()
    await hub.zuordnung_setzen(UID1, {"typ": "folge", "serie": "q", "folge": "folge-1.mp3"})
    await hub.zuordnung_setzen(UID2, {"typ": "folge", "serie": "q", "folge": "folge-2.mp3"})
    revision = hub.store.konfig["revision"]
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.folge_verschieben("q", "folge-1.mp3", "z", False, None)
    assert err.value.code == "tobies_betroffen"
    assert (q / "folge-1.mp3").exists()
    erg = await hub.medien.folge_verschieben("q", "folge-1.mp3", "z", True, None)
    assert erg["folge"] == "folge-1 (2).mp3"  # im Ziel gab es den Namen schon: Suffix
    assert erg["betroffene_tobies"] == [{"uid": UID1, "name": None}]
    assert erg["konfig"]["revision"] == revision + 1
    assert erg["veroeffentlicht"] is True
    assert hub.store.konfig["zuordnungen"][UID1]["ziel"] == {"typ": "folge", "serie": "z", "folge": "folge-1 (2).mp3"}
    assert hub.store.konfig["zuordnungen"][UID2]["ziel"]["serie"] == "q"  # andere Folge: unverändert
    assert box_fabrik("box1").konfigs()[-1]["zuordnungen"][UID1]["ziel"]["serie"] == "z"
    assert (z / "folge-1 (2).mp3").exists() and not (q / "folge-1.mp3").exists()
    assert nas.serie_json("quelle")["folgen"] == ["folge-2.mp3"]
    # Nummer unbekannt: hinten
    assert nas.serie_json("ziel")["folgen"] == ["folge-1.mp3", "folge-3.mp3", "folge-1 (2).mp3"]
    # dieselbe Serie: ziel_ungueltig
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.folge_verschieben("q", "folge-2.mp3", "q", True, None)
    assert err.value.code == "ziel_ungueltig"


async def test_folge_verschieben_ohne_tobies_aendert_keine_konfiguration(hass, integration, nas, lege_mp3):
    hub = integration
    q = nas.serie("quelle", "q", "Quelle", ["a.mp3"], folgen_info={"a.mp3": {"anzeige": "Eins", "nummer": 2, "pruefen": True, "pruefen_gruende": ["tags_fehlen"]}})
    z = nas.serie("ziel", "z", "Ziel", ["b.mp3", "c.mp3", "d.mp3"], folgen_info={"b.mp3": {"nummer": 1}, "c.mp3": {"nummer": 3}})
    lege_mp3(q / "a.mp3")
    for n in ("b", "c", "d"):
        lege_mp3(z / f"{n}.mp3")
    await hub.medien.pruefen()
    revision = hub.store.konfig["revision"]
    erg = await hub.medien.folge_verschieben("q", "a.mp3", "z", False, None)
    assert erg["konfig"] is None and erg["veroeffentlicht"] is None
    assert hub.store.konfig["revision"] == revision
    ziel = nas.serie_json("ziel")
    assert ziel["folgen"] == ["b.mp3", "a.mp3", "c.mp3", "d.mp3"]  # Nummer 2: vor der ersten größeren (3)
    assert ziel["folgen_info"]["a.mp3"] == {"anzeige": "Eins", "nummer": 2}  # "bitte prüfen" ist gelöscht


async def test_folge_verschieben_ohne_bereite_konfig(hass, integration, nas, lege_mp3):
    hub = integration
    q = nas.serie("q", "q", "Q", ["a.mp3"])
    z = nas.serie("z", "z", "Z", [])
    lege_mp3(q / "a.mp3")
    await hub.medien.pruefen()
    await hub.zuordnung_setzen(UID1, {"typ": "folge", "serie": "q", "folge": "a.mp3"})
    hub.store.zustand = "leer_neu"
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.folge_verschieben("q", "a.mp3", "z", True, None)
    assert err.value.code == "konfig_nicht_bereit"
    assert (q / "a.mp3").exists()  # dann wird nichts verschoben


async def test_serien_zusammenfuehren(hass, integration, nas, lege_mp3):
    hub = integration
    q = nas.serie("quelle", "q", "Quelle", ["a.mp3", "CD"], folgen_info={"a.mp3": {"nummer": 2}, "CD": {"nummer": 1}})
    z = nas.serie("ziel", "z", "Ziel", ["a.mp3"], folgen_info={"a.mp3": {"nummer": 5}})
    lege_mp3(q / "a.mp3")
    lege_mp3(q / "CD" / "01.mp3")
    lege_mp3(z / "a.mp3")
    (q / "cover.jpg").write_bytes(b"x")
    await hub.medien.pruefen()
    await hub.zuordnung_setzen(UID1, {"typ": "serie", "serie": "q"})
    await hub.zuordnung_setzen(UID2, {"typ": "folge", "serie": "q", "folge": "a.mp3"})
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.serien_zusammenfuehren("q", "z", False, None, None)
    assert err.value.code == "tobies_betroffen"
    erg = await hub.medien.serien_zusammenfuehren("q", "z", True, None, None)
    assert erg["verschoben"] == 2
    assert erg["umbenannt"] == [{"von": "a.mp3", "nach": "a (2).mp3"}]
    assert {t["uid"] for t in erg["betroffene_tobies"]} == {UID1, UID2}
    assert erg["eintrag"]["typ"] == "serie" and erg["eintrag"]["grund"] == "zusammengefuehrt"
    ziel = nas.serie_json("ziel")
    assert ziel["folgen"] == ["CD", "a (2).mp3", "a.mp3"]  # nach Nummern: 1, 2, 5
    assert (z / "CD" / "01.mp3").exists()
    assert not (nas.medien / "quelle").exists()  # die leere Quellserie ging in den Papierkorb
    zu = hub.store.konfig["zuordnungen"]
    assert zu[UID1]["ziel"] == {"typ": "serie", "serie": "z"}
    assert zu[UID2]["ziel"] == {"typ": "folge", "serie": "z", "folge": "a (2).mp3"}
    meta = json.loads((nas.papierkorb / erg["eintrag"]["id"] / "meta.json").read_text())
    assert meta["grund"] == "zusammengefuehrt" and meta["typ"] == "serie"
    with pytest.raises(TobiboxFehler) as err:  # zweiter Aufruf
        await hub.medien.serien_zusammenfuehren("q", "z", True, None, None)
    assert err.value.code == "serie_nicht_gefunden"


async def test_zusammenfuehren_nur_normale_verschiedene_serien(hass, integration, nas):
    hub = integration
    nas.serie("a", "a", "A")
    nas.serie("u", "u", "U", typ="ueberraschung")
    await hub.medien.pruefen()
    for q, z in (("a", "a"), ("a", "u"), ("u", "a")):
        with pytest.raises(TobiboxFehler) as err:
            await hub.medien.serien_zusammenfuehren(q, z, True, None, None)
        assert err.value.code == "ziel_ungueltig"


async def test_bestaetigen_nimmt_bitte_pruefen_weg(hass, integration, nas, lege_mp3):
    hub = integration
    pfad = nas.serie("o", "id1", "S", ["a.mp3", "b.mp3"], pruefen=True, pruefen_gruende=["serie_aus_ordner"],
                     folgen_info={"a.mp3": {"pruefen": True, "pruefen_gruende": ["tags_fehlen"]}, "b.mp3": {"pruefen": True, "pruefen_gruende": ["tags_fehlen"]}})
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    await hub.medien.pruefen()
    erg = await hub.medien.bestaetigen("id1", ["a.mp3"])
    assert erg["pruefen"] is True and erg["anzahl_pruefen"] == 1
    with pytest.raises(TobiboxFehler) as err:
        await hub.medien.bestaetigen("id1", ["x.mp3"])
    assert err.value.code == "folge_nicht_gefunden"
    erg = await hub.medien.bestaetigen("id1", None)
    assert erg["pruefen"] is False and erg["anzahl_pruefen"] == 0
    daten = nas.serie_json("o")
    assert "pruefen" not in daten
    assert "folgen_info" not in daten
