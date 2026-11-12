"""Upload in den Eingang (Vertrag W, Abschnitt 5): Strom, Abschluss mit ``asyncio.shield``, Namen, Rechte, Grenzen."""

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.tobibox import ffprobe
from custom_components.tobibox.const import UPLOAD_SAMMELZEIT_S

from .conftest import braucht_ffmpeg, erzeuge_audio, warte_auf

pytestmark = braucht_ffmpeg

MIB = 1024 * 1024


def formular(inhalt: bytes | Path, name: str = "x.mp3", **felder: str) -> aiohttp.FormData:
    """``upload_id``, ``serie_id``, ``gruppe`` in dieser Reihenfolge, dann ``datei`` (Vertrag W, 5.1).

    Ein Browser schickt den Dateinamen unverändert; ``aiohttp`` würde ihn mit ``quote_fields`` in %-Schreibweise setzen."""
    daten = aiohttp.FormData(quote_fields=False)
    for schluessel in ("upload_id", "serie_id", "gruppe"):
        if schluessel in felder:
            daten.add_field(schluessel, felder[schluessel])
    daten.add_field("datei", inhalt.open("rb") if isinstance(inhalt, Path) else inhalt, filename=name, content_type="application/octet-stream")
    return daten


def sha(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        while b := f.read(MIB):
            h.update(b)
    return h.hexdigest()


def eingang_namen(nas) -> list[str]:
    return sorted(p.name for p in nas.eingang.rglob("*") if p.is_file())


def part_dateien(nas) -> list[Path]:
    upload = nas.medien / "_upload"
    return sorted(upload.glob("*.part")) if upload.exists() else []


@pytest.fixture
async def client(hass, integration, hass_client, nas):
    return await hass_client()


@pytest.fixture
def mp3(tmp_path) -> Path:
    return erzeuge_audio(tmp_path / "quelle.mp3", frequenz=333, album="Folge 1", album_artist="Upload-Serie", title="Folge 1: Der Anfang")


async def post(client, daten, **kw):
    return await client.post("/api/tobibox/upload", data=daten, **kw)


# --- 40 MiB im Strom (Abnahme AP 3.1) ---


async def test_datei_ueber_16_mib_kommt_im_strom_an(hass, client, nas, integration, tmp_path):
    """Belegt, dass die feste HA-Version das Streaming nicht auf 16 MiB begrenzt."""
    assert hass.http.app._client_max_size == 16 * MIB  # normale Anfragen sind auf 16 MiB begrenzt
    gross = erzeuge_audio(tmp_path / "gross.wav", dauer=500)  # 16 Bit, 44,1 kHz, mono: etwa 42 MiB
    assert gross.stat().st_size > 40 * MIB
    antwort = await post(client, formular(gross, "gross.wav", upload_id="gross-upload-0001"))
    assert antwort.status == 200, await antwort.text()
    assert antwort.content_type == "application/json"
    daten = await antwort.json()
    assert daten["v"] == 1 and daten["upload_id"] == "gross-upload-0001"
    assert daten["groesse_bytes"] == gross.stat().st_size
    assert daten["eingang_name"] == "gross.wav" and daten["pruefung"] == "ok" and daten["hinweis"] is None
    assert daten["serie_id"] is None and daten["wiederholt"] is False
    ziel = nas.eingang / "gross.wav"
    assert ziel.stat().st_size == gross.stat().st_size
    assert sha(ziel) == sha(gross)  # Byte für Byte angekommen
    assert part_dateien(nas) == []  # die Zwischendatei ist weg
    integration.eingang.abbrechen()


# --- Format ---


async def test_falsches_format_wird_abgelehnt(client, nas):
    antwort = await post(client, formular(b"text", "notiz.txt"))
    assert antwort.status == 415
    assert (await antwort.json()) == {"v": 1, "fehler": {"code": "format_nicht_erlaubt", "text": "Dieses Dateiformat spielt die Box nicht."}}
    assert eingang_namen(nas) == [] and part_dateien(nas) == []


async def test_endung_ohne_gross_klein_aber_inhalt_ist_text(client, nas):
    antwort = await post(client, formular(b"Das ist Text, kein Audio.\n" * 100, "falsch.MP3"))
    assert antwort.status == 415
    assert (await antwort.json())["fehler"]["code"] == "format_nicht_erlaubt"
    assert eingang_namen(nas) == [] and part_dateien(nas) == []  # nichts bleibt


async def test_playlist_mit_audio_endung_wird_abgelehnt(client, nas):
    antwort = await post(client, formular(b"#EXTM3U\n#EXTINF:1,x\nhttp://127.0.0.1:9/x.mp3\n", "liste.mp3"))
    assert antwort.status == 415
    assert eingang_namen(nas) == []


async def test_ffprobe_wird_nur_gehaertet_aufgerufen(client, nas, mp3):
    echt = ffprobe.subprocess.run
    aufrufe = []

    def merke(args, **kw):
        aufrufe.append((args, kw))
        return echt(args, **kw)

    with patch("custom_components.tobibox.ffprobe.subprocess.run", side_effect=merke):
        antwort = await post(client, formular(mp3, "folge.mp3"))
    assert antwort.status == 200
    ffprobe_aufrufe = [a for a, _kw in aufrufe if a[0].endswith("ffprobe")]
    assert ffprobe_aufrufe
    for args in ffprobe_aufrufe:
        assert args[args.index("-protocol_whitelist") + 1] == "file"
        assert args[args.index("-f") + 1] == "mp3"  # erzwungenes Format
        assert args[-1].startswith("file:/")
    assert all(kw["timeout"] == 30 and kw["stdin"] is not None for _a, kw in aufrufe)


async def test_defekte_datei_bleibt_im_eingang_mit_warnung(client, nas):
    antwort = await post(client, formular(bytes(range(256)) * 200, "kaputt.mp3"))
    assert antwort.status == 200
    daten = await antwort.json()
    assert (daten["pruefung"], daten["hinweis"]) == ("warnung", "nicht_lesbar")
    assert (nas.eingang / "kaputt.mp3").exists()


async def test_kopierschutz_und_ffprobe_fehlt(client, nas, mp3):
    with patch("custom_components.tobibox.http.ffprobe.pruefe_datei", return_value=ffprobe.Pruefung("warnung", ffprobe.KOPIERSCHUTZ)):
        daten = await (await post(client, formular(mp3, "schutz.mp3"))).json()
    assert (daten["pruefung"], daten["hinweis"]) == ("warnung", "kopierschutz")
    with patch("custom_components.tobibox.http.ffprobe.pruefe_datei", return_value=ffprobe.Pruefung("nicht_moeglich", ffprobe.FFPROBE_FEHLT)):
        daten = await (await post(client, formular(mp3, "ohne.mp3"))).json()
    assert (daten["pruefung"], daten["hinweis"]) == ("nicht_moeglich", "ffprobe_fehlt")
    assert {"schutz.mp3", "ohne.mp3"} <= set(eingang_namen(nas))


# --- Rechte ---


async def test_ohne_anmeldung_401(hass, integration, hass_client_no_auth, nas, mp3):
    anonym = await hass_client_no_auth()
    antwort = await post(anonym, formular(mp3))
    assert antwort.status == 401
    assert eingang_namen(nas) == []


async def test_auch_nicht_administratoren_duerfen_hochladen(hass, integration, hass_client, hass_read_only_access_token, nas, mp3):
    """Seit 12.11. (Vertrag W, 2.1; W-19 entfällt): Recht „alltag“, jeder angemeldete Nutzer."""
    lesend = await hass_client(hass_read_only_access_token)
    antwort = await post(lesend, formular(mp3))
    assert antwort.status == 200, await antwort.text()
    assert eingang_namen(nas) == ["x.mp3"]
    integration.eingang.abbrechen()


# --- Namen (Abschnitt 12) ---


async def test_name_wird_bereinigt_nicht_abgelehnt(client, nas, mp3):
    daten = await (await post(client, formular(mp3, "Folge 1: Der Rabe.mp3"))).json()
    assert daten["eingang_name"] == "Folge 1 - Der Rabe.mp3"
    assert (nas.eingang / "Folge 1 - Der Rabe.mp3").exists()


async def test_name_ohne_nutzbaren_rest(client, nas, mp3):
    antwort = await post(client, formular(mp3, "...mp3"))
    assert antwort.status == 200  # die Endung bleibt, der Name wird "mp3.mp3"
    assert (await antwort.json())["eingang_name"].endswith(".mp3")


async def test_pfadteile_im_dateinamen_werden_entschaerft(client, nas, mp3):
    daten = await (await post(client, formular(mp3, "../../etc/passwd.mp3"))).json()
    assert "/" not in daten["eingang_name"] and not daten["eingang_name"].startswith(".")
    assert not (nas.basis.parent / "etc").exists()
    assert all(p.parent == nas.eingang for p in nas.eingang.rglob("*") if p.is_file())


async def test_zwei_uploads_gleichen_namens_suffix_nie_ueberschreiben(client, nas, tmp_path):
    a = erzeuge_audio(tmp_path / "a.mp3", frequenz=300)
    b = erzeuge_audio(tmp_path / "b.mp3", frequenz=500)
    r1 = await (await post(client, formular(a, "Folge.mp3"))).json()
    r2 = await (await post(client, formular(b, "folge.MP3"))).json()  # andere Schreibweise: auf SMB dieselbe Datei
    r3 = await (await post(client, formular(b, "Folge.mp3"))).json()
    assert [r["eingang_name"] for r in (r1, r2, r3)] == ["Folge.mp3", "folge (2).MP3", "Folge (3).mp3"]
    assert sha(nas.eingang / "Folge.mp3") == sha(a)  # das Erste wurde nie überschrieben
    assert sha(nas.eingang / "folge (2).MP3") == sha(b)


async def test_zwei_gleichzeitige_uploads_gleichen_namens(client, nas, tmp_path):
    a = erzeuge_audio(tmp_path / "a.mp3", frequenz=300)
    b = erzeuge_audio(tmp_path / "b.mp3", frequenz=500)
    r = await asyncio.gather(post(client, formular(a, "x.mp3")), post(client, formular(b, "x.mp3")))
    namen = sorted([(await x.json())["eingang_name"] for x in r])
    assert namen == ["x (2).mp3", "x.mp3"]
    assert len(eingang_namen(nas)) == 2


# --- Felder: serie_id, gruppe, upload_id ---


async def test_serie_id_muss_existieren_und_ist_die_vorgabe(client, nas, integration, mp3, lege_mp3):
    nas.serie("ziel", "ziel", "Ziel-Serie")
    await integration.medien.pruefen()
    antwort = await post(client, formular(mp3, "a.mp3", serie_id="gibtsnicht"))
    assert antwort.status == 404
    assert (await antwort.json())["fehler"]["code"] == "serie_nicht_gefunden"
    assert eingang_namen(nas) == []
    daten = await (await post(client, formular(mp3, "a.mp3", serie_id="ziel"))).json()
    assert daten["serie_id"] == "ziel"
    assert integration.eingang.vorgaben["a.mp3"] == {"serie_id": "ziel", "gruppe": None}
    integration.eingang.abbrechen()


async def test_gruppe_bildet_einen_eingangsordner(client, nas, integration, tmp_path):
    a = erzeuge_audio(tmp_path / "a.mp3", frequenz=300, album="Hörbuch", album_artist="S", track="1")
    b = erzeuge_audio(tmp_path / "b.mp3", frequenz=400, album="Hörbuch", album_artist="S", track="2")
    r1 = await (await post(client, formular(a, "01.mp3", gruppe="abcdef1234567890"))).json()
    r2 = await (await post(client, formular(b, "02.mp3", gruppe="abcdef1234567890"))).json()
    assert (r1["eingang_name"], r2["eingang_name"]) == ("01.mp3", "02.mp3")
    assert sorted(p.relative_to(nas.eingang).as_posix() for p in nas.eingang.rglob("*.mp3")) == ["Upload abcdef12/01.mp3", "Upload abcdef12/02.mp3"]
    integration.eingang.abbrechen()


@pytest.mark.parametrize(("feld", "wert"), [("upload_id", "kurz"), ("upload_id", "mit leerzeichen!"), ("gruppe", "x" * 65), ("gruppe", "ä-ö-ü-ä-ö-ü")])
async def test_ungueltige_felder(client, nas, mp3, feld, wert):
    antwort = await post(client, formular(mp3, "a.mp3", **{feld: wert}))
    assert antwort.status == 400
    assert (await antwort.json())["fehler"]["code"] == "invalid_format"
    assert eingang_namen(nas) == []


async def test_datei_fehlt_im_formular(client):
    daten = aiohttp.FormData(quote_fields=False)
    daten.add_field("upload_id", "kein-datei-0001")
    antwort = await post(client, daten)
    assert antwort.status == 400


async def test_wiederholung_mit_gleicher_upload_id_liefert_das_alte_ergebnis(client, nas, mp3):
    erste = await (await post(client, formular(mp3, "a.mp3", upload_id="wiederholt-0001"))).json()
    zweite = await (await post(client, formular(mp3, "a.mp3", upload_id="wiederholt-0001"))).json()
    assert erste["wiederholt"] is False and zweite["wiederholt"] is True
    assert {k: v for k, v in zweite.items() if k != "wiederholt"} == {k: v for k, v in erste.items() if k != "wiederholt"}
    assert eingang_namen(nas) == ["a.mp3"]  # nichts doppelt aufgenommen


async def test_gleiche_upload_id_parallel_upload_laeuft(hass, client, nas, mp3, integration):
    frei = threading.Event()
    echt = ffprobe.pruefe_datei

    def langsam(pfad, endung=None):
        frei.wait(10)
        return echt(pfad, endung)

    with patch("custom_components.tobibox.http.ffprobe.pruefe_datei", new=langsam):  # kein Mock: der Test-Harness von HA führt Mocks im Executor sofort in der Schleife aus
        erste = asyncio.ensure_future(post(client, formular(mp3, "a.mp3", upload_id="parallel-0001")))
        await warte_auf(hass, lambda: "parallel-0001" in integration.uploads_laufend, block=False)
        zweite = await post(client, formular(mp3, "b.mp3", upload_id="parallel-0001"))
        assert zweite.status == 409
        assert (await zweite.json())["fehler"]["code"] == "upload_laeuft"
        frei.set()
        assert (await erste).status == 200
    assert eingang_namen(nas) == ["a.mp3"]
    assert integration.uploads_laufend == set()


async def test_hoechstens_zwei_uploads_gleichzeitig(hass, client, nas, mp3, integration):
    frei = threading.Event()
    echt = ffprobe.pruefe_datei

    def langsam(pfad, endung=None):
        frei.wait(10)
        return echt(pfad, endung)

    with patch("custom_components.tobibox.http.ffprobe.pruefe_datei", new=langsam):  # kein Mock: der Test-Harness von HA führt Mocks im Executor sofort in der Schleife aus
        a = asyncio.ensure_future(post(client, formular(mp3, "a.mp3")))
        b = asyncio.ensure_future(post(client, formular(mp3, "b.mp3")))
        await warte_auf(hass, lambda: integration.upload_zaehler == 2, block=False)
        c = await post(client, formular(mp3, "c.mp3"))
        assert c.status == 429
        assert (await c.json())["fehler"]["code"] == "zu_viele_uploads"
        frei.set()
        assert (await a).status == 200 and (await b).status == 200
    assert integration.upload_zaehler == 0
    assert sorted(eingang_namen(nas)) == ["a.mp3", "b.mp3"]


# --- Größe und Platz (vor dem Körper) ---


def roh_koerper(inhalt: bytes, name: str = "x.mp3") -> tuple[bytes, dict[str, str]]:
    grenze = "tobiboxgrenze"
    koerper = (
        f"--{grenze}\r\nContent-Disposition: form-data; name=\"datei\"; filename=\"{name}\"\r\nContent-Type: audio/mpeg\r\n\r\n"
    ).encode() + inhalt + f"\r\n--{grenze}--\r\n".encode()
    return koerper, {"Content-Type": f"multipart/form-data; boundary={grenze}"}


async def test_zu_gross_nach_content_length_wird_vor_dem_koerper_abgelehnt(client, nas, integration):
    integration.upload_max_bytes = 1000
    koerper, kopf = roh_koerper(b"x" * 5000)
    antwort = await client.post("/api/tobibox/upload", data=koerper, headers=kopf)
    assert antwort.status == 413
    assert (await antwort.json())["fehler"]["code"] == "datei_zu_gross"
    assert part_dateien(nas) == [] and eingang_namen(nas) == []


async def test_zu_gross_im_strom_ohne_content_length(client, nas, integration, mp3):
    integration.upload_max_bytes = 3000

    async def strom():
        koerper, _kopf = roh_koerper(b"\x00" * 20000, "gross.mp3")
        for i in range(0, len(koerper), 4096):
            yield koerper[i : i + 4096]

    antwort = await client.post("/api/tobibox/upload", data=strom(), headers=roh_koerper(b"")[1])
    assert antwort.status == 413
    assert (await antwort.json())["fehler"]["code"] == "datei_zu_gross"
    assert part_dateien(nas) == [] and eingang_namen(nas) == []  # Zwischendatei gelöscht


async def test_platzpruefung_vorab(client, nas):
    koerper, kopf = roh_koerper(b"x" * 100)
    with patch("custom_components.tobibox.http.dateien.freier_platz", return_value=50 * MIB):  # Reserve: 100 MiB
        antwort = await client.post("/api/tobibox/upload", data=koerper, headers=kopf)
    assert antwort.status == 507
    assert (await antwort.json())["fehler"]["code"] == "kein_speicher"
    with patch("custom_components.tobibox.http.dateien.freier_platz", return_value=500 * MIB):
        antwort = await client.post("/api/tobibox/upload", data=koerper, headers=kopf)
    assert antwort.status == 200 or antwort.status == 415  # genug Platz: weiter zur Prüfung des Inhalts
    assert part_dateien(nas) == []


async def test_freigabe_nicht_erreichbar_503(client, nas, mp3):
    import os

    os.rmdir(nas.eingang)
    antwort = await post(client, formular(mp3, "a.mp3"))
    assert antwort.status == 503
    assert (await antwort.json())["fehler"]["code"] == "medien_nicht_erreichbar"


# --- Abbruch des Clients ---


@pytest.fixture
async def client_mit_abbruch(hass, integration, aiohttp_client, hass_access_token, socket_enabled):
    """Wie HA: Trennt der Client, wird der Handler mit ``CancelledError`` abgebrochen (``handler_cancellation=True``)."""
    return await aiohttp_client(
        hass.http.app, headers={"Authorization": f"Bearer {hass_access_token}"}, server_kwargs={"handler_cancellation": True}
    )


async def test_abbruch_im_empfang_hinterlaesst_nichts(hass, client_mit_abbruch, nas, integration):
    client = client_mit_abbruch
    stoppen = asyncio.Event()

    async def strom():
        koerper, _kopf = roh_koerper(b"\x00" * (6 * MIB), "halb.mp3")
        yield koerper[: 3 * MIB]
        await stoppen.wait()  # der Rest kommt nie
        yield koerper[3 * MIB :]

    aufgabe = asyncio.ensure_future(
        client.post("/api/tobibox/upload", data=strom(), headers=roh_koerper(b"")[1] | {"X-Test": "1"})
    )
    await warte_auf(hass, lambda: any(p.stat().st_size > 0 for p in part_dateien(nas)), versuche=300)
    assert len(part_dateien(nas)) == 1  # die Zwischendatei mit Zufallsnamen, ohne upload_id
    aufgabe.cancel()  # das Handy verliert das Netz
    with pytest.raises((asyncio.CancelledError, aiohttp.ClientError)):
        await aufgabe
    await warte_auf(hass, lambda: part_dateien(nas) == [], versuche=300)
    assert eingang_namen(nas) == []  # es ist nichts entstanden
    stoppen.set()


async def test_abbruch_im_abschluss_shield_datei_und_ergebnis_sind_da(hass, client_mit_abbruch, nas, integration, mp3):
    """Der Client ist nach dem letzten Byte weg: der Abschluss läuft zu Ende (``asyncio.shield``)."""
    client = client_mit_abbruch
    frei = threading.Event()
    echt = ffprobe.pruefe_datei

    def langsam(pfad, endung=None):
        frei.wait(10)
        return echt(pfad, endung)

    with patch("custom_components.tobibox.http.ffprobe.pruefe_datei", new=langsam):  # kein Mock: der Test-Harness von HA führt Mocks im Executor sofort in der Schleife aus
        aufgabe = asyncio.ensure_future(post(client, formular(mp3, "abschluss.mp3", upload_id="abschluss-0001")))
        await warte_auf(hass, lambda: "abschluss-0001" in integration.uploads_laufend, versuche=300, block=False)
        await asyncio.sleep(0.5)  # das letzte Byte ist angekommen, die Prüfung hängt
        aufgabe.cancel()
        with pytest.raises((asyncio.CancelledError, aiohttp.ClientError)):
            await aufgabe
        await asyncio.sleep(0.2)  # der Server hat die Trennung bemerkt und den Handler abgebrochen
        frei.set()
        await warte_auf(hass, lambda: "abschluss-0001" in integration.upload_ergebnisse, versuche=300, block=False)
    assert (nas.eingang / "abschluss.mp3").exists()  # Datei und Ergebnis sind da
    ergebnis = integration.upload_ergebnisse["abschluss-0001"][1]
    assert ergebnis["eingang_name"] == "abschluss.mp3" and ergebnis["pruefung"] == "ok"
    assert part_dateien(nas) == []
    # die Seite sendet nach einem Verbindungsfehler nicht blind erneut; tut sie es doch, kommt das alte Ergebnis
    zweite = await (await post(client, formular(mp3, "abschluss.mp3", upload_id="abschluss-0001"))).json()
    assert zweite["wiederholt"] is True
    assert eingang_namen(nas) == ["abschluss.mp3"]
    integration.eingang.abbrechen()


async def test_fehler_im_abschluss_raeumt_auf(hass, client, nas, mp3):
    with patch("custom_components.tobibox.http._in_den_eingang", side_effect=OSError("voll")):
        antwort = await post(client, formular(mp3, "a.mp3", upload_id="fehler-00001"))
    assert antwort.status == 500
    assert (await antwort.json())["fehler"]["code"] == "medien_schreibfehler"
    assert part_dateien(nas) == [] and eingang_namen(nas) == []
    # ein Fehler wird nicht als Ergebnis gemerkt: ein neuer Versuch mit derselben upload_id wird ausgeführt
    antwort = await post(client, formular(mp3, "a.mp3", upload_id="fehler-00001"))
    assert antwort.status == 200 and (await antwort.json())["wiederholt"] is False


async def test_alte_part_dateien_werden_bei_der_pruefung_geloescht(hass, integration, nas):
    upload = nas.medien / "_upload"
    upload.mkdir(exist_ok=True)
    alt = upload / "alt.part"
    neu = upload / "neu.part"
    alt.write_bytes(b"x")
    neu.write_bytes(b"x")
    zwei_tage = time.time() - 2 * 86400
    import os

    os.utime(alt, (zwei_tage, zwei_tage))
    await integration.medien.pruefen()
    assert not alt.exists() and neu.exists()


# --- Ereignisse (Thema upload) und Einsortieren nach der Sammelzeit ---


async def test_ereignisse_und_einsortieren_nach_20_sekunden(hass, integration, hass_ws_client, client, nas, mp3, freezer):
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["upload", "eingang"]})
    assert (await ws.receive_json())["success"] is True
    assert {(await ws.receive_json())["event"]["thema"] for _ in range(2)} == {"upload", "eingang"}
    daten = await (await post(client, formular(mp3, "folge.mp3", upload_id="ereignis-0001"))).json()
    assert daten["pruefung"] == "ok"
    fortschritt = []
    for _ in range(4):
        e = (await ws.receive_json())["event"]
        if e["thema"] == "upload":
            fortschritt.append(e["daten"])
        if len(fortschritt) == 2:
            break
    assert [f["zustand"] for f in fortschritt] == ["pruefe", "fertig"]
    assert all(f["upload_id"] == "ereignis-0001" and f["code"] is None for f in fortschritt)
    assert fortschritt[1]["bytes"] == mp3.stat().st_size
    # nach 20 s Sammelzeit wird einsortiert, die Ruhezeit von 120 s gilt für Uploads nicht
    assert (nas.eingang / "folge.mp3").exists()
    freezer.tick(timedelta(seconds=UPLOAD_SAMMELZEIT_S + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert integration.eingang._task is not None
    await integration.eingang._task  # (unter dem ``freezer`` steht die Schleifenzeit still: kein ``asyncio.sleep`` hier)
    await hass.async_block_till_done()
    assert not (nas.eingang / "folge.mp3").exists()
    serie = json.loads(next(nas.medien.glob("*/serie.json")).read_text())
    assert serie["name"] == "Upload-Serie" and serie["folgen"] == ["folge.mp3"]
    assert serie["folgen_info"]["folge.mp3"]["anzeige"] == "Folge 1"
    await ws.close()


async def test_fehler_ereignis_bei_ablehnung(hass, integration, hass_ws_client, client, nas):
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "tobibox/subscribe", "themen": ["upload"]})
    await ws.receive_json()
    await ws.receive_json()
    antwort = await post(client, formular(b"nur text\n" * 200, "x.mp3", upload_id="ablehnung-0001"))
    assert antwort.status == 415
    kette = []
    for _ in range(2):
        kette.append((await ws.receive_json())["event"]["daten"])
    assert [(k["zustand"], k["code"]) for k in kette] == [("pruefe", None), ("fehler", "format_nicht_erlaubt")]
    await ws.close()
