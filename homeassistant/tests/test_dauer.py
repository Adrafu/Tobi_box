"""Paket A3b „Dauer“ (Vertrag W, 14.7 und 14.2; ``data-model.md``, 5a): Store ``tobibox.medieninfo``, Nachholen im Hintergrund, Dauerdeckel.

* Dauer einer MP3 und einer Ordner-Folge (``dauer_s``, ``spuren_s``), Summe in der Kurzform, Dauer in ``folgen/list``.
* Eine FLAC-Datei mit „digitaler Stille“ und behaupteter Dauer über dem Deckel bekommt **kein** ``dauer_s``.
* Der Hintergrundlauf ändert den ``stand`` nie und schreibt nichts auf das NAS.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from custom_components.tobibox import dauer as dauer_modul
from custom_components.tobibox import ffprobe
from custom_components.tobibox.const import DAUER_DECKEL_S, MEDIENINFO_VERSION
from custom_components.tobibox.dauer import DauerDienst
from custom_components.tobibox.medieninfo import MedienInfo

from .conftest import braucht_ffmpeg, erzeuge_audio, warte_auf
from .test_eingang import sortiere
from .test_websocket_api import ok

pytestmark = braucht_ffmpeg


def flac_mit_behaupteter_dauer(pfad, sekunden: int):
    """Eine gültige, winzige FLAC-Datei, deren Kopf (``STREAMINFO``) eine sehr lange Dauer behauptet: was eine Datei mit Stille tut
    (2 Stunden Stille = 1,1 MB, Design 11.4.4). ``ffprobe`` liest die Dauer aus dem Kopf; 190 000 s zu kodieren würde Sekunden dauern."""
    erzeuge_audio(pfad, dauer=1.0)
    daten = bytearray(pfad.read_bytes())
    assert daten[:4] == b"fLaC"
    start = 8 + 10  # Kopf „fLaC“ + Blockkopf, dann 2+2+3+3 Bytes Rahmen- und Blockgrößen
    rate = int.from_bytes(daten[start : start + 3], "big") >> 4
    feld = int.from_bytes(daten[start : start + 8], "big")
    feld = (feld & ~((1 << 36) - 1)) | (sekunden * rate)
    daten[start : start + 8] = feld.to_bytes(8, "big")
    pfad.write_bytes(bytes(daten))
    return pfad


@pytest.fixture
async def start_ohne_nachholen(monkeypatch, starte_integration, nas):
    """``starte()``: richtet die Integration ein, **ohne** dass der Hintergrundlauf beim Start anläuft (der Test stößt ihn selbst an)."""

    async def starte():
        with monkeypatch.context() as m:
            m.setattr(DauerDienst, "nachholen_beim_start", lambda self: None)
            return await starte_integration()

    return starte


def serie_mit(nas, lege_mp3, ordner="Rabe", sid="s1"):
    """Serie mit einer mp3 und einem Ordner aus zwei Tracks von 2 und 3 Sekunden."""
    lege_mp3(nas.medien / ordner / "a.mp3")
    erzeuge_audio(nas.medien / ordner / "Hörbuch" / "01.mp3", dauer=2.0)
    erzeuge_audio(nas.medien / ordner / "Hörbuch" / "02.mp3", dauer=3.0, frequenz=330)
    nas.serie(ordner, serie_id=sid, name="Rabe", folgen=["a.mp3", "Hörbuch"])


# --------------------------------------------------------------------------
# Messen: eine MP3, eine Ordner-Folge
# --------------------------------------------------------------------------


async def test_dauer_einer_mp3_und_einer_ordner_folge(hass, hass_ws_client, starte_integration, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    hub = await starte_integration()
    await hub.dauer.warte_auf_ende()
    assert hub.medieninfo.dauer_s("s1", "a.mp3") in (1, 2)  # 1 s Sinus, gerundet auf ganze Sekunden (Encoder-Zugabe)
    assert hub.medieninfo.spuren_s("s1", "a.mp3") is None  # nur Ordner-Folgen haben Spuren
    spuren = hub.medieninfo.spuren_s("s1", "Hörbuch")
    assert len(spuren) == 2 and spuren[0] in (2, 3) and spuren[1] in (3, 4)
    assert hub.medieninfo.dauer_s("s1", "Hörbuch") == sum(spuren)  # Summe der gerundeten Spuren
    ws = await hass_ws_client(hass)
    s = await ok(ws, "serie/get", serie_id="s1")
    a, ordner = s["folgen"]
    assert a["dauer_s"] == hub.medieninfo.dauer_s("s1", "a.mp3") and "spuren_s" not in a
    assert ordner["dauer_s"] == sum(spuren) and ordner["spuren_s"] == spuren
    assert s["dauer_s"] == a["dauer_s"] + ordner["dauer_s"]  # Kurzform: Summe der bekannten Dauern
    liste = await ok(ws, "serien/list")
    assert liste["serien"][0]["dauer_s"] == s["dauer_s"]
    zeilen = (await ok(ws, "folgen/list"))["folgen"]
    assert {z["folge"]: z["dauer_s"] for z in zeilen} == {"a.mp3": a["dauer_s"], "Hörbuch": ordner["dauer_s"]}  # Listenzeilen zeigen die Dauer


async def test_dauer_ist_ganze_sekunden(hass, starte_integration, nas):
    erzeuge_audio(nas.medien / "S" / "x.flac", dauer=2.6)
    nas.serie("S", serie_id="s", name="S", folgen=["x.flac"])
    hub = await starte_integration()
    await hub.dauer.warte_auf_ende()
    assert hub.medieninfo.dauer_s("s", "x.flac") == 3
    assert isinstance(hub.medieninfo.dauer_s("s", "x.flac"), int)


async def test_ohne_dauer_ist_das_feld_null_oder_fehlt(hass, hass_ws_client, start_ohne_nachholen, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    hub = await start_ohne_nachholen()
    ws = await hass_ws_client(hass)
    s = await ok(ws, "serie/get", serie_id="s1")
    assert s["dauer_s"] is None  # „null, solange unbekannt“
    assert all("dauer_s" not in f and "spuren_s" not in f for f in s["folgen"])  # „fehlt“
    assert all(z["dauer_s"] is None for z in (await ok(ws, "folgen/list"))["folgen"])
    assert hub.medieninfo.daten.get("s1", {}).get("folgen") is None


async def test_kurzform_summiert_nur_die_bekannten_dauern(hass, hass_ws_client, start_ohne_nachholen, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    hub = await start_ohne_nachholen()
    hub.medieninfo.setze_dauer("s1", "a.mp3", 120)
    ws = await hass_ws_client(hass)
    assert (await ok(ws, "serie/get", serie_id="s1"))["dauer_s"] == 120
    hub.medieninfo.setze_dauer("s1", "Hörbuch", 600, [100, 500])
    assert (await ok(ws, "serie/get", serie_id="s1"))["dauer_s"] == 720


# --------------------------------------------------------------------------
# Dauerdeckel: FLAC-Stille
# --------------------------------------------------------------------------


async def test_flac_stille_ueber_dem_deckel_hat_keine_dauer(hass, hass_ws_client, starte_integration, nas, lege_mp3, hass_storage):
    lege_mp3(nas.medien / "S" / "normal.mp3")
    flac_mit_behaupteter_dauer(nas.medien / "S" / "stille.flac", 190_000)  # 52 Stunden
    nas.serie("S", serie_id="s", name="S", folgen=["normal.mp3", "stille.flac"])
    # der Kopf behauptet wirklich eine so lange Dauer, und die Datei ist trotzdem gültig (besteht die Prüfung nach D5)
    assert ffprobe.probe_datei(nas.medien / "S" / "stille.flac").dauer_s > DAUER_DECKEL_S
    hub = await starte_integration()
    await hub.dauer.warte_auf_ende()
    ws = await hass_ws_client(hass)
    s = await ok(ws, "serie/get", serie_id="s")
    normal, stille = s["folgen"]
    assert "dauer_s" in normal
    assert "dauer_s" not in stille and "spuren_s" not in stille  # Zeitleiste und Gesamtdauer zeigen „–“
    assert s["dauer_s"] == normal["dauer_s"]  # die Summe zählt die Stille nicht mit
    zeilen = {z["folge"]: z["dauer_s"] for z in (await ok(ws, "folgen/list"))["folgen"]}
    assert zeilen["stille.flac"] is None
    await hub.medieninfo.async_speichern()
    gespeichert = hass_storage["tobibox.medieninfo"]["data"]["s"]["folgen"]
    assert "stille.flac" not in gespeichert  # über dem Deckel wird nichts gespeichert


async def test_flac_stille_wird_je_lauf_nur_einmal_versucht(hass, start_ohne_nachholen, nas):
    flac_mit_behaupteter_dauer(nas.medien / "S" / "stille.flac", 190_000)
    nas.serie("S", serie_id="s", name="S", folgen=["stille.flac"])
    hub = await start_ohne_nachholen()
    with patch.object(dauer_modul, "messe_folge", wraps=dauer_modul.messe_folge) as messe:
        hub.dauer.nachholen_beim_start()
        await hub.dauer.warte_auf_ende()
        hub.dauer._offen["s"] = None  # noch einmal im selben Lauf angestoßen: nicht noch einmal lesen
        hub.dauer._starte()
        await hub.dauer.warte_auf_ende()
        assert messe.call_count == 1


def test_deckel_grenze_im_store():
    store = MedienInfo.__new__(MedienInfo)
    store.daten = {}
    store._speichern = lambda: None
    assert store.setze_dauer("s", "a", DAUER_DECKEL_S) is True  # genau 48 Stunden gehen noch
    assert store.dauer_s("s", "a") == DAUER_DECKEL_S
    assert store.setze_dauer("s", "b", DAUER_DECKEL_S + 1) is False  # eine Sekunde mehr nicht
    assert store.dauer_s("s", "b") is None
    assert store.setze_dauer("s", "c", 100, [60, DAUER_DECKEL_S + 1]) is False  # auch eine einzelne Spur über dem Deckel
    assert store.setze_dauer("s", "d", 0) is False and store.setze_dauer("s", "d", -5) is False
    assert store.setze_dauer("s", "e", float("nan")) is False
    assert store.dauer_s("s", "c") is None and store.dauer_s("s", "d") is None


# --------------------------------------------------------------------------
# Der Hintergrundlauf verändert nichts, was die Boxen sehen
# --------------------------------------------------------------------------


async def test_hintergrundlauf_aendert_den_stand_nicht_und_schreibt_keine_datei(hass, hass_ws_client, start_ohne_nachholen, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    hub = await start_ohne_nachholen()
    ws = await hass_ws_client(hass)
    vorher = await ok(ws, "serie/get", serie_id="s1")
    json_pfad = nas.medien / "Rabe" / "serie.json"
    json_vorher = (json_pfad.read_bytes(), json_pfad.stat().st_mtime_ns)
    dateien_vorher = sorted(str(p.relative_to(nas.basis)) for p in nas.basis.rglob("*"))
    assert vorher["dauer_s"] is None
    hub.dauer.nachholen_beim_start()
    await hub.dauer.warte_auf_ende()
    nachher = await ok(ws, "serie/get", serie_id="s1")
    assert nachher["dauer_s"]  # der Lauf hat gemessen
    assert nachher["stand"] == vorher["stand"]
    assert hub.medien.serien["s1"].serie.stand == vorher["stand"]
    assert (json_pfad.read_bytes(), json_pfad.stat().st_mtime_ns) == json_vorher  # serie.json (die die Boxen synchronisieren) unberührt
    assert sorted(str(p.relative_to(nas.basis)) for p in nas.basis.rglob("*")) == dateien_vorher  # und keine neue Datei auf dem NAS
    assert "dauer_s" not in json.loads(json_pfad.read_text())


async def test_hintergrundlauf_meldet_serien_geaendert(hass, integration, nas, lege_mp3, ereignisse):
    serie_mit(nas, lege_mp3)
    hub = integration
    await hub.medien.pruefen()
    ereignisse.clear()
    hub.dauer.anstossen(["s1"])
    await hub.dauer.warte_auf_ende()
    await hass.async_block_till_done()
    assert any(e["art"] == "serien_geaendert" and "s1" in e["daten"]["serie_ids"] for e in ereignisse)


async def test_nachholen_beim_start_misst_nur_unvollstaendige_folgen(hass, start_ohne_nachholen, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    hub = await start_ohne_nachholen()
    hub.medieninfo.setze_info("s1", "a.mp3", 77, None, [], ["mp3"])  # vollständig (Dauer, Kapitel, Codecs)
    with patch.object(dauer_modul, "messe_folge", wraps=dauer_modul.messe_folge) as messe:
        hub.dauer.nachholen_beim_start()
        await hub.dauer.warte_auf_ende()
        assert [c.args[2] for c in messe.call_args_list] == ["Hörbuch"]
    assert hub.medieninfo.dauer_s("s1", "a.mp3") == 77  # bekannte Werte bleiben
    # einmal je Start: ein zweiter Aufruf macht nichts
    with patch.object(dauer_modul, "messe_folge") as messe:
        hub.dauer.nachholen_beim_start()
        await hub.dauer.warte_auf_ende()
        messe.assert_not_called()


async def test_seite_oeffnen_und_pruefen_starten_keinen_scan(hass, hass_ws_client, start_ohne_nachholen, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    hub = await start_ohne_nachholen()
    ws = await hass_ws_client(hass)
    with patch.object(dauer_modul, "messe_folge") as messe:
        await ok(ws, "serien/list")
        await ok(ws, "serie/get", serie_id="s1")
        await ok(ws, "folgen/list")
        await hub.medien.pruefen()
        await ok(ws, "medien/pruefen")
        await hass.async_block_till_done()
        messe.assert_not_called()


async def test_nas_weg_bricht_den_lauf_ab_und_speichert_nichts(hass, start_ohne_nachholen, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    lege_mp3(nas.medien / "Zwei" / "b.mp3")
    nas.serie("Zwei", serie_id="s2", name="Zwei", folgen=["b.mp3"])
    hub = await start_ohne_nachholen()
    with patch.object(dauer_modul, "messe_folge", return_value=dauer_modul.WEG) as messe:
        hub.dauer.nachholen_beim_start()
        await hub.dauer.warte_auf_ende()
        assert messe.call_count == 1  # beim ersten „NAS weg“ ist Schluss, die zweite Serie wird gar nicht versucht
    assert hub.medieninfo.daten.get("s1", {}).get("folgen") is None and hub.medieninfo.daten.get("s2", {}).get("folgen") is None
    assert hub.dauer._task.done() and not hub.dauer._offen


def test_messe_folge_ohne_freigabe_ist_weg(tmp_path, lege_mp3):
    medien = tmp_path / "gibtsnicht"
    assert dauer_modul.messe_folge(medien, medien / "S", "a.mp3") == dauer_modul.WEG


def test_messe_folge_unlesbare_datei_ist_none_und_nicht_weg(tmp_path):
    medien = tmp_path / "medien"
    (medien / "S").mkdir(parents=True)
    (medien / "S" / "kaputt.mp3").write_bytes(b"kein audio" * 100)
    (medien / "S" / "Ordner").mkdir()
    (medien / "S" / "Ordner" / "x.txt").write_text("keine audiodatei")
    assert dauer_modul.messe_folge(medien, medien / "S", "kaputt.mp3") is None
    assert dauer_modul.messe_folge(medien, medien / "S", "Ordner") is None  # ein Ordner ohne Tracks
    assert dauer_modul.messe_folge(medien, medien / "S", "fehlt.mp3") is None


async def test_ordner_folge_mit_einem_kaputten_track_hat_keine_halbe_summe(tmp_path, lege_mp3):
    medien = tmp_path / "medien"
    erzeuge_audio(medien / "S" / "F" / "01.mp3", dauer=2.0)
    (medien / "S" / "F" / "02.mp3").write_bytes(b"kein audio" * 100)
    assert dauer_modul.messe_folge(medien, medien / "S", "F") is None


def test_zeitgrenze_je_datei_ist_20_sekunden(tmp_path, lege_mp3):
    """Das Nachholen verkürzt die Zeitgrenze von ``ffprobe`` (30 s) auf ``MEDIENINFO_ZEITGRENZE_S`` (20 s), nie umgekehrt."""
    lege_mp3(tmp_path / "a.mp3")
    with patch.object(ffprobe, "_laufe", wraps=ffprobe._laufe) as laufe:
        ffprobe.probe_datei(tmp_path / "a.mp3", zeitlimit=20)
        assert laufe.call_args.args[1] == 20
    with patch.object(ffprobe.subprocess, "run", side_effect=ffprobe.subprocess.TimeoutExpired("ffprobe", 20)) as run:
        assert ffprobe.probe_datei(tmp_path / "a.mp3", zeitlimit=20).status == ffprobe.NICHT_LESBAR  # Zeitgrenze: nicht messbar, kein Absturz
        assert run.call_args.kwargs["timeout"] == 20
    with patch.object(ffprobe.subprocess, "run", side_effect=ffprobe.subprocess.TimeoutExpired("ffprobe", 30)) as run:
        ffprobe.probe_datei(tmp_path / "a.mp3", zeitlimit=99)
        assert run.call_args.kwargs["timeout"] == 30  # kürzer ja, länger nie


# --------------------------------------------------------------------------
# Beim Einsortieren, Verschieben, Löschen
# --------------------------------------------------------------------------


async def test_beim_einsortieren_wird_die_dauer_aus_den_proben_gespeichert(hass, integration, nas):
    for i in range(1, 4):
        erzeuge_audio(nas.eingang / "Hörbuch X" / f"Kapitel {i}.mp3", frequenz=300 + i, dauer=float(i), album="Hörbuch X", album_artist="Autor A",
                      track=f"{i}/3", title=f"Kapitel {i}")
    erzeuge_audio(nas.eingang / "Einzel.mp3", dauer=4.0, album="Anderes", album_artist="Autor B")
    with patch.object(dauer_modul, "messe_folge", wraps=dauer_modul.messe_folge) as messe:
        await sortiere(integration)
        await integration.dauer.warte_auf_ende()
        assert messe.call_count == 0  # die Proben vom Einsortieren genügen: kein zweiter Lesedurchgang
    info = integration.medieninfo
    sid_buch = next(s for s, i in integration.medien.serien.items() if "Hörbuch X" in i.serie.folgen)
    spuren = info.spuren_s(sid_buch, "Hörbuch X")
    assert len(spuren) == 3 and [abs(s - n) <= 1 for s, n in zip(spuren, (1, 2, 3), strict=True)] == [True] * 3  # 1, 2 und 3 Sekunden (Encoder-Zugabe)
    assert spuren == sorted(spuren)  # Reihenfolge der Tracks wie in der Folge (Kapitel 1, 2, 3)
    assert info.dauer_s(sid_buch, "Hörbuch X") == sum(spuren)
    sid_einzel = next(s for s, i in integration.medien.serien.items() if any(n.startswith("Einzel") for n in i.serie.folgen))
    name = next(n for n in integration.medien.serien[sid_einzel].serie.folgen if n.startswith("Einzel"))
    assert info.dauer_s(sid_einzel, name) in (4, 5)
    assert info.spuren_s(sid_einzel, name) is None


async def test_dauer_wandert_mit_beim_verschieben_und_faellt_beim_loeschen_weg(hass, hass_ws_client, start_ohne_nachholen, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    lege_mp3(nas.medien / "Zwei" / "b.mp3")
    nas.serie("Zwei", serie_id="s2", name="Zwei", folgen=["b.mp3"])
    hub = await start_ohne_nachholen()
    hub.medieninfo.setze_dauer("s1", "a.mp3", 111)
    hub.medieninfo.setze_dauer("s1", "Hörbuch", 500, [200, 300])
    ws = await hass_ws_client(hass)
    await ok(ws, "folge/verschieben", serie_id="s1", folge="a.mp3", ziel_serie_id="s2")
    assert hub.medieninfo.dauer_s("s1", "a.mp3") is None and hub.medieninfo.dauer_s("s2", "a.mp3") == 111
    await ok(ws, "folge/delete", serie_id="s1", folge="Hörbuch")
    assert hub.medieninfo.dauer_s("s1", "Hörbuch") is None and hub.medieninfo.spuren_s("s1", "Hörbuch") is None
    assert "folgen" not in hub.medieninfo.daten.get("s1", {})  # nichts übrig (die Marke ``cover_suche`` bleibt)
    hub.medieninfo.setze_dauer("s2", "b.mp3", 5)
    await ok(ws, "serie/delete", serie_id="s2")
    assert "folgen" not in hub.medieninfo.daten.get("s2", {})


async def test_bereinigen_nur_nach_gelungener_pruefung(hass, start_ohne_nachholen, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    hub = await start_ohne_nachholen()
    hub.medieninfo.setze_info("s1", "a.mp3", 10, None, [], ["mp3"])
    hub.medieninfo.setze_dauer("s1", "weg.mp3", 20)  # die Folge gibt es nicht mehr
    hub.medieninfo.setze_dauer("verschwunden", "x.mp3", 30)  # die Serie auch nicht
    hub.medieninfo.setze_cover_suche("verschwunden", "keine")  # die Marke gehört nicht hierher: bleibt
    hub.medien.geprueft_am = None  # NAS beim Start nicht erreichbar: es wird nie etwas gelöscht
    hub.dauer.nachholen_beim_start()
    await hub.dauer.warte_auf_ende()
    assert hub.medieninfo.dauer_s("s1", "weg.mp3") == 20 and hub.medieninfo.dauer_s("verschwunden", "x.mp3") == 30
    hub.medien.geprueft_am = "2026-11-14T10:00:00Z"
    hub.dauer.beim_start_nachgeholt = False
    hub.dauer.nachholen_beim_start()
    await hub.dauer.warte_auf_ende()
    assert hub.medieninfo.dauer_s("s1", "a.mp3") == 10
    assert hub.medieninfo.dauer_s("s1", "weg.mp3") is None and hub.medieninfo.dauer_s("verschwunden", "x.mp3") is None
    assert hub.medieninfo.cover_suche("verschwunden")["ergebnis"] == "keine"


async def test_store_ueberlebt_den_neustart(hass, hass_storage, start_ohne_nachholen, nas, lege_mp3):
    serie_mit(nas, lege_mp3)
    hub = await start_ohne_nachholen()
    hub.dauer.nachholen_beim_start()
    await hub.dauer.warte_auf_ende()
    spuren = hub.medieninfo.spuren_s("s1", "Hörbuch")
    await hub.medieninfo.async_speichern()
    neu = MedienInfo(hass)
    await neu.async_laden()
    assert neu.dauer_s("s1", "Hörbuch") == sum(spuren) and neu.spuren_s("s1", "Hörbuch") == spuren
    assert neu.dauer_s("s1", "a.mp3") == hub.medieninfo.dauer_s("s1", "a.mp3")
    # Form nach data-model.md 5a: Serie -> folgen -> Name -> dauer_s / spuren_s
    roh = hass_storage["tobibox.medieninfo"]["data"]["s1"]["folgen"]["Hörbuch"]
    assert roh == {"dauer_s": sum(spuren), "spuren_s": spuren, "codecs": ["mp3", "mp3"], "kapitel": roh["kapitel"], "info_v": MEDIENINFO_VERSION}
    assert [k["track"] for k in roh["kapitel"]] == [0, 1]  # Ordner-Folge: jeder Track ein Kapitel
    await warte_auf(hass, lambda: True)
