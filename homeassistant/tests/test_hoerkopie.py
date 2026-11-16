"""Paket A3c „Hörkopie“ und A4c3 „Audio-Ansicht, Zweig Kopie“ (Vertrag W, 14.8, 14.10, Befehl 45; Design 11.4.7 und 11.4.1)."""

from __future__ import annotations

import shutil
import subprocess
from unittest.mock import patch

import pytest

from custom_components.tobibox import audio, ffprobe, hoerkopie
from custom_components.tobibox.const import (
    DAUER_DECKEL_S,
    HOERKOPIE_SCHLANGE_DATEIEN,
    HOERKOPIE_ZEITGRENZE_S,
)
from custom_components.tobibox.hoerkopie import Auftrag, braucht_hoerkopie

from .conftest import FFMPEG, braucht_ffmpeg, erzeuge_audio
from .test_dauer import flac_mit_behaupteter_dauer
from .test_websocket_api import fehler, ok

pytestmark = braucht_ffmpeg


def erzeuge_opus(pfad, dauer=2.0, kanaele=2):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    ziel = ["-c:a", "libopus", "-b:a", "32k", "-ac", str(kanaele), "-f", "ogg"]
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=duration={dauer}", *ziel, str(pfad)], check=True, capture_output=True)
    return pfad


@pytest.fixture
async def bestand(hass, integration, nas, lege_mp3):
    erzeuge_opus(nas.medien / "Rabe" / "a.opus")
    lege_mp3(nas.medien / "Rabe" / "m.mp3")
    erzeuge_audio(nas.medien / "Rabe" / "f.flac", dauer=2.0)
    nas.serie("Rabe", serie_id="s1", name="Rabe", folgen=["a.opus", "m.mp3", "f.flac"])
    lege_mp3(nas.medien / "Zwei" / "z.mp3")
    erzeuge_opus(nas.medien / "Zwei" / "a.opus")
    nas.serie("Zwei", serie_id="s2", name="Zwei", folgen=["z.mp3", "a.opus"])
    await integration.medien.pruefen()
    return nas


@pytest.fixture
async def api(hass, bestand, hass_ws_client):
    return await hass_ws_client(hass)


@pytest.fixture
async def client(hass, bestand, hass_client):
    return await hass_client()


# --------------------------------------------------------------------------
# Regel und Befehl
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("codec", "soll"), [("mp3", False), ("aac", False), ("AAC", False), ("vorbis", True), ("opus", True), ("alac", True),
                                             ("flac", True), ("pcm_s16le", True), ("wmav2", True), ("", True), (None, True)])
def test_braucht_hoerkopie(codec, soll):
    assert braucht_hoerkopie(codec) is soll


def test_ffmpeg_befehl_wie_im_design(tmp_path):
    a = hoerkopie.baue_ffmpeg_befehl("ffmpeg", tmp_path / "q.flac", "flac", tmp_path / "z.m4a.part", 100.0)
    assert a[:7] == ["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file", "-f"]
    assert a[a.index("-i") + 1] == f"file:{tmp_path / 'q.flac'}"
    for paar in (("-map", "0:a:0"), ("-ac", "2"), ("-map_metadata", "-1"), ("-t", "105"), ("-c:a", "aac"), ("-b:a", "96k"), ("-movflags", "+faststart")):
        assert a[a.index(paar[0]) : a.index(paar[0]) + 2] == list(paar), paar
    assert "-vn" in a and a[-3:-1] == ["-f", "mp4"] and a[-1] == f"file:{tmp_path / 'z.m4a.part'}"
    fs = int(a[a.index("-fs") + 1])
    assert 100 * 12000 * 1.2 <= fs <= 100 * 12000 * 1.2 + 100_000
    gross = hoerkopie.baue_ffmpeg_befehl("f", "q.flac", "flac", "z", 10**9)
    assert int(gross[gross.index("-t") + 1]) <= DAUER_DECKEL_S


async def test_hello_und_befehl_ohne_ffmpeg(hass, api, bestand):
    hub = hass.data["tobibox"]
    h = await ok(api, "hello", v=1)
    assert h["faehigkeiten"][-1] == "hoerkopie" and h["grenzen"]["hoerkopie_kbit"] == 96
    assert h["grenzen"]["hoerkopie_schlange"]["dateien_max"] == HOERKOPIE_SCHLANGE_DATEIEN
    hub.hoerkopie.programm = None
    h = await ok(api, "hello", v=1)
    assert "hoerkopie" not in h["faehigkeiten"] and "hoerkopie_kbit" not in h["grenzen"]
    # ohne ffmpeg bleibt es beim Original (die Seite prüft mit canPlayType)
    r = await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")
    assert (r["zustand"], r["quelle"]) == ("bereit", "original")


# --------------------------------------------------------------------------
# Der Ablauf: wird_vorbereitet, dann 206 mit audio/mp4
# --------------------------------------------------------------------------


async def test_ogg_folge_erst_wird_vorbereitet_dann_206_audio_mp4(hass, api, client, bestand):
    hub = hass.data["tobibox"]
    r = await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")
    assert r["zustand"] == "wird_vorbereitet" and r["position"] >= 1 and r["warte_s"] >= 1 and "pfad" not in r
    # solange die Kopie fehlt: der Rückfall der Ansicht
    # (die Schlange läuft schon; deshalb erst die Antwort der Ansicht prüfen, wenn sie noch nicht fertig ist, sonst ist sie fertig)
    antwort = await client.get(audio.audio_pfad("s1", "a.opus"))
    assert antwort.status in (503, 200)
    if antwort.status == 503:
        assert antwort.headers["Retry-After"] == "60"
        assert (await antwort.json())["fehler"]["code"] == "hoerkopie_wartet"
    # idempotent: eine schon wartende Kopie bleibt dieselbe
    await hub.hoerkopie.warte_auf_ende()
    r = await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")
    assert r["zustand"] == "bereit" and r["quelle"] == "kopie"
    z = await client.get(r["pfad"], headers={"Range": "bytes=0-99"})
    assert z.status == 206 and z.headers["Content-Type"] == "audio/mp4" and z.headers["X-Tobibox-Quelle"] == "kopie"
    assert len(await z.read()) == 100
    kopie = list((bestand.basis / "hoerkopien" / "s1").glob("*.m4a"))
    assert len(kopie) == 1 and not list((bestand.basis / "hoerkopien").rglob("*.part"))
    p = ffprobe.probe_datei(kopie[0], "m4a")
    assert p.codec == "aac" and 1 <= p.dauer_s <= 8
    # das Original bleibt unberührt und liegt nie unter hoerkopien/
    assert (bestand.medien / "Rabe" / "a.opus").is_file() and not (bestand.medien / "hoerkopien").exists()
    # Zustand im Folge-Objekt (ohne Platte)
    s = await ok(api, "serie/get", serie_id="s1")
    assert {f["name"]: f["hoerkopie"]["zustand"] for f in s["folgen"] if "hoerkopie" in f}["a.opus"] == "fertig"


async def test_mp3_bleibt_original(api, client, bestand):
    r = await ok(api, "audio/bereit", serie_id="s1", folge="m.mp3")
    assert (r["zustand"], r["quelle"]) == ("bereit", "original")
    z = await client.get(r["pfad"], headers={"Range": "bytes=0-9"})
    assert z.status == 206 and z.headers["X-Tobibox-Quelle"] == "original" and z.headers["Content-Type"] == "audio/mpeg"
    assert not (bestand.basis / "hoerkopien").exists()


async def test_nur_zustand_lesen_stoesst_nichts_an(hass, api, bestand):
    r = await ok(api, "audio/bereit", serie_id="s1", folge="a.opus", vorbereiten=False)
    assert r == {"zustand": "fehlt", "grund": "nicht_angelegt"}
    assert not hass.data["tobibox"].hoerkopie.in_schlange("s1", "a.opus")


async def test_kopie_nur_ueber_die_eigene_serie_id(hass, api, client, bestand):
    hub = hass.data["tobibox"]
    await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")
    await hub.hoerkopie.warte_auf_ende()
    assert (await ok(api, "audio/bereit", serie_id="s1", folge="a.opus"))["zustand"] == "bereit"
    # s2 hat eine Folge gleichen Namens: sie bekommt die Kopie von s1 nie
    antwort = await client.get(audio.audio_pfad("s2", "a.opus"))
    assert antwort.status == 503
    quelle = bestand.medien / "Rabe" / "a.opus"
    st = quelle.stat()
    kenn = hoerkopie.kennung("a.opus", 0, st.st_size, st.st_mtime_ns)
    wurzel = bestand.basis / "hoerkopien"
    assert hoerkopie.finde_kopie(wurzel, "s1", kenn) is not None
    assert hoerkopie.finde_kopie(wurzel, "s2", kenn) is None
    assert hoerkopie.finde_kopie(wurzel, "..", kenn) is None and hoerkopie.finde_kopie(wurzel, "s1/../s1", kenn) is None
    assert hoerkopie.finde_kopie(wurzel, "s1", "../../../etc/passwd") is None


async def test_symlink_aus_hoerkopien_hinaus_wird_nicht_ausgeliefert(bestand, tmp_path):
    wurzel = bestand.basis / "hoerkopien"
    (wurzel / "s1").mkdir(parents=True)
    fremd = tmp_path / "fremd.m4a"
    fremd.write_bytes(b"x" * 10)
    (wurzel / "s1" / ("a" * 16 + ".m4a")).symlink_to(fremd)
    assert hoerkopie.finde_kopie(wurzel, "s1", "a" * 16) is None


# --------------------------------------------------------------------------
# Harte Grenzen
# --------------------------------------------------------------------------


async def test_flac_stille_unplausibel_ohne_kopie(hass, api, bestand):
    flac_mit_behaupteter_dauer(bestand.medien / "Rabe" / "stille.flac", 7200)  # 2 Stunden, gültig, winzig
    bestand.serie("Rabe", serie_id="s1", name="Rabe", folgen=["a.opus", "stille.flac"])
    await hass.data["tobibox"].medien.pruefen()
    await ok(api, "audio/bereit", serie_id="s1", folge="stille.flac")
    await hass.data["tobibox"].hoerkopie.warte_auf_ende()
    r = await ok(api, "audio/bereit", serie_id="s1", folge="stille.flac")
    assert r == {"zustand": "fehlt", "grund": "unplausibel"}
    assert not (bestand.basis / "hoerkopien" / "s1").exists() or not list((bestand.basis / "hoerkopien" / "s1").iterdir())


async def test_ueber_dem_dauerdeckel_ist_zu_lang(hass, api, bestand):
    flac_mit_behaupteter_dauer(bestand.medien / "Rabe" / "lang.flac", 190_000)
    bestand.serie("Rabe", serie_id="s1", name="Rabe", folgen=["lang.flac"])
    await hass.data["tobibox"].medien.pruefen()
    await ok(api, "audio/bereit", serie_id="s1", folge="lang.flac")
    await hass.data["tobibox"].hoerkopie.warte_auf_ende()
    assert await ok(api, "audio/bereit", serie_id="s1", folge="lang.flac") == {"zustand": "fehlt", "grund": "zu_lang"}
    s = await ok(api, "serie/get", serie_id="s1")
    assert s["folgen"][0]["hoerkopie"] == {"zustand": "fehler", "grund": "zu_lang"}


async def test_ein_versuch_je_datei_und_start(hass, api, bestand):
    hub = hass.data["tobibox"]
    flac_mit_behaupteter_dauer(bestand.medien / "Rabe" / "lang.flac", 190_000)
    bestand.serie("Rabe", serie_id="s1", name="Rabe", folgen=["lang.flac"])
    await hub.medien.pruefen()
    await ok(api, "audio/bereit", serie_id="s1", folge="lang.flac")
    await hub.hoerkopie.warte_auf_ende()
    with patch.object(hoerkopie, "erzeuge_kopie", wraps=hoerkopie.erzeuge_kopie) as erzeuge:
        for _ in range(3):
            assert (await ok(api, "audio/bereit", serie_id="s1", folge="lang.flac"))["zustand"] == "fehlt"
        await hub.hoerkopie.warte_auf_ende()
        erzeuge.assert_not_called()
        # erst auf Befehl 45 (Administrator) wieder
        assert (await ok(api, "hoerkopie/neu_erzeugen"))["eingereiht"] == 1
        await hub.hoerkopie.warte_auf_ende()
        assert erzeuge.call_count == 1


async def test_mehrkanal_wird_stereo(hass, api, bestand):
    quelle = bestand.medien / "Rabe" / "sechs.wav"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=duration=2", "-ac", "6", "-c:a", "pcm_s16le", str(quelle)], check=True, capture_output=True)
    bestand.serie("Rabe", serie_id="s1", name="Rabe", folgen=["sechs.wav"])
    await hass.data["tobibox"].medien.pruefen()
    await ok(api, "audio/bereit", serie_id="s1", folge="sechs.wav")
    await hass.data["tobibox"].hoerkopie.warte_auf_ende()
    kopie = next((bestand.basis / "hoerkopien" / "s1").glob("*.m4a"))
    aus = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=channels", "-of", "csv=p=0", str(kopie)], capture_output=True, text=True, check=True)
    assert aus.stdout.strip() == "2"


async def test_fs_bricht_eine_ueberlange_ausgabe_ab(hass, api, bestand):
    hub = hass.data["tobibox"]
    with patch.object(hoerkopie, "HOERKOPIE_FS_SOCKEL_BYTES", 0), patch.object(hoerkopie, "HOERKOPIE_FS_FAKTOR", 0.05):
        await ok(api, "audio/bereit", serie_id="s1", folge="f.flac")
        await hub.hoerkopie.warte_auf_ende()
    assert await ok(api, "audio/bereit", serie_id="s1", folge="f.flac") == {"zustand": "fehlt", "grund": "kodieren_fehlgeschlagen"}
    assert not list((bestand.basis / "hoerkopien").rglob("*.m4a")) and not list((bestand.basis / "hoerkopien").rglob("*.part"))


async def test_zeitgrenze_ist_fest_und_nicht_aus_dem_dateikopf(tmp_path):
    zeiten = []

    class Falsch:
        returncode = 0

        def __init__(self, *a, **k):
            pass

        def communicate(self, timeout=None):
            if timeout is None:
                return b"", b""
            zeiten.append(timeout)
            raise subprocess.TimeoutExpired("ffmpeg", timeout)

        def kill(self):
            pass

    with patch.object(hoerkopie.subprocess, "Popen", Falsch):
        assert hoerkopie._laufe_ffmpeg(["ffmpeg"], {}) is None
    assert zeiten[0] == HOERKOPIE_ZEITGRENZE_S == 5400


async def test_zeitgrenze_ergibt_grund_zeitgrenze(hass, api, bestand):
    hub = hass.data["tobibox"]
    with patch.object(hoerkopie, "_laufe_ffmpeg", return_value=None):
        await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")
        await hub.hoerkopie.warte_auf_ende()
    assert (await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")) == {"zustand": "fehlt", "grund": "zeitgrenze"}


async def test_kontingent_ergibt_kein_speicher(hass, api, bestand):
    hub = hass.data["tobibox"]
    (bestand.basis / "hoerkopien" / "voll").mkdir(parents=True)
    (bestand.basis / "hoerkopien" / "voll" / "x.m4a").write_bytes(b"x" * 100)
    with patch.object(hoerkopie, "HOERKOPIE_KONTINGENT_BYTES", 50):
        await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")
        await hub.hoerkopie.warte_auf_ende()
    assert (await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")) == {"zustand": "fehlt", "grund": "kein_speicher"}
    assert (bestand.basis / "hoerkopien" / "voll" / "x.m4a").exists()  # nichts wird gelöscht


async def test_die_21_datei_kommt_nicht_in_die_schlange(hass, api, bestand, tmp_path):
    hub = hass.data["tobibox"]
    dienst = hub.hoerkopie
    dienst._starte = lambda: None  # nichts läuft: die Schlange füllt sich
    for i in range(HOERKOPIE_SCHLANGE_DATEIEN):
        dienst._einreihen(Auftrag("sx", f"f{i}", 0, tmp_path / "q.flac", 10), mit_vorziehen=False)
    assert dienst.schlange_zaehler()["dateien"] == 20
    assert await fehler(api, "audio/bereit", serie_id="s1", folge="a.opus") == "hoerkopie_warteschlange_voll"
    dienst._schlange.clear()


async def test_schlange_nach_quellbytes_begrenzt(hass, bestand, tmp_path):
    dienst = hass.data["tobibox"].hoerkopie
    dienst._starte = lambda: None
    dienst._einreihen(Auftrag("sx", "f", 0, tmp_path / "q", 10), mit_vorziehen=False)
    with patch.object(hoerkopie, "HOERKOPIE_SCHLANGE_BYTES", 15), pytest.raises(Exception) as e:
        dienst._einreihen(Auftrag("sx", "g", 0, tmp_path / "q", 10), mit_vorziehen=False)
    assert e.value.code == "hoerkopie_warteschlange_voll"
    dienst._schlange.clear()


async def test_vorziehen_je_benutzer_hoechstens_eine_datei(hass, bestand, tmp_path):
    dienst = hass.data["tobibox"].hoerkopie
    dienst._starte = lambda: None
    q = tmp_path / "q"
    dienst._einreihen(Auftrag("sx", "alt", 0, q, 1), mit_vorziehen=False)
    dienst._einreihen(Auftrag("sx", "u1a", 0, q, 1, nutzer_id="u1"), mit_vorziehen=True)
    dienst._einreihen(Auftrag("sx", "u1b", 0, q, 1, nutzer_id="u1"), mit_vorziehen=True)
    dienst._einreihen(Auftrag("sx", "u2a", 0, q, 1, nutzer_id="u2"), mit_vorziehen=True)
    assert [a.folge for a in dienst._schlange] == ["u1a", "u2a", "alt", "u1b"]  # u1b wurde nicht vorgezogen
    dienst._schlange.clear()


# --------------------------------------------------------------------------
# Neu einsortiert, Aufräumen, Bestand
# --------------------------------------------------------------------------


async def test_neu_einsortiertes_bekommt_sofort_seine_kopie(hass, integration, nas):
    from .test_eingang import sortiere

    erzeuge_audio(nas.eingang / "Lied.flac", dauer=2.0, album="Lieder", album_artist="Chor")
    erzeuge_audio(nas.eingang / "Lied2.mp3", dauer=2.0, frequenz=300, album="Andere", album_artist="Wer")
    await sortiere(integration)
    await integration.dauer.warte_auf_ende()
    for _ in range(3):
        await hass.async_block_till_done()
        await integration.hoerkopie.warte_auf_ende()
    kopien = list((nas.basis / "hoerkopien").rglob("*.m4a"))
    assert len(kopien) == 1  # nur die FLAC-Datei, nicht die MP3


async def test_bestand_wird_nicht_im_hintergrund_umgewandelt(hass, bestand):
    hub = hass.data["tobibox"]
    hub.dauer.beim_start_nachgeholt = False
    hub.dauer.nachholen_beim_start()
    await hub.dauer.warte_auf_ende()
    await hub.hoerkopie.warte_auf_ende()
    assert not (bestand.basis / "hoerkopien").exists()  # kein Hintergrund-Lauf über den Bestand
    assert hub.medieninfo.codecs("s1", "a.opus") == ["opus"]


async def test_aufraeumen_part_und_verwaistes(hass, bestand):
    hub = hass.data["tobibox"]
    wurzel = bestand.basis / "hoerkopien"
    (wurzel / "s1").mkdir(parents=True)
    (wurzel / "s1" / "halb.m4a.part").write_bytes(b"x")
    (wurzel / "s1" / ("b" * 16 + ".m4a")).write_bytes(b"x")  # Kennung unbekannt
    (wurzel / "weg").mkdir()
    (wurzel / "weg" / ("c" * 16 + ".m4a")).write_bytes(b"x")  # Serie gibt es nicht
    await hub.hoerkopie._raeume_auf(nur_part=True)
    assert not (wurzel / "s1" / "halb.m4a.part").exists() and (wurzel / "s1" / ("b" * 16 + ".m4a")).exists() and (wurzel / "weg").exists()
    await hub.hoerkopie._raeume_auf(nur_part=False)
    assert not (wurzel / "s1" / ("b" * 16 + ".m4a")).exists() and not (wurzel / "weg").exists()


async def test_nas_weg_pausiert_die_schlange(hass, api, bestand):
    hub = hass.data["tobibox"]
    with patch.object(hoerkopie, "erzeuge_kopie", return_value=hoerkopie.Ergebnis(hoerkopie.WEG)):
        await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")
        await hub.hoerkopie.warte_auf_ende()
    assert hub.hoerkopie._pausiert and hub.hoerkopie.in_schlange("s1", "a.opus")
    assert hub.medieninfo.hoerkopie_tracks("s1", "a.opus") == {}  # kein Fehlerzustand
    hub.hoerkopie.fortsetzen()
    await hub.hoerkopie.warte_auf_ende()
    assert hub.medieninfo.hoerkopie_tracks("s1", "a.opus")["0"]["zustand"] == "fertig"


async def test_neu_erzeugen_rechte_und_fehler(hass, api, bestand, hass_ws_client):
    from .test_audio import _normal

    normal = await _normal(hass, hass_ws_client)
    assert await fehler(normal, "hoerkopie/neu_erzeugen") == "unauthorized"
    assert await fehler(api, "hoerkopie/neu_erzeugen", serie_id="gibts-nicht") == "serie_nicht_gefunden"
    assert (await ok(api, "hoerkopie/neu_erzeugen"))["eingereiht"] == 0


async def test_original_bleibt_fuer_die_box_unberuehrt(hass, api, bestand):
    vorher = (bestand.medien / "Rabe" / "a.opus").read_bytes()
    json_vorher = (bestand.medien / "Rabe" / "serie.json").read_bytes()
    await ok(api, "audio/bereit", serie_id="s1", folge="a.opus")
    await hass.data["tobibox"].hoerkopie.warte_auf_ende()
    assert (bestand.medien / "Rabe" / "a.opus").read_bytes() == vorher
    assert (bestand.medien / "Rabe" / "serie.json").read_bytes() == json_vorher
    assert shutil.which("ffmpeg")
