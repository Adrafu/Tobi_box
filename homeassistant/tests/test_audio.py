"""Audio-Ansicht und ``audio/bereit`` (Vertrag W, 14.5): Range, Pfad-Sicherheit, Anmeldung und Signatur, Zähler."""

from __future__ import annotations

from urllib.parse import quote

import pytest

from custom_components.tobibox import audio
from custom_components.tobibox.const import AUDIO_VERBINDUNGEN_JE_BENUTZER

from .conftest import braucht_ffmpeg, warte_auf

pytestmark = braucht_ffmpeg


@pytest.fixture
async def bestand(hass, integration, nas, lege_mp3):
    """Serie ``s1`` mit einer Datei und einem Ordner (zwei Tracks), eine zweite Serie ``s2``."""
    lege_mp3(nas.medien / "Rabe" / "Folge 1.mp3")
    lege_mp3(nas.medien / "Rabe" / "Hörbuch #2 100%" / "01.mp3")
    lege_mp3(nas.medien / "Rabe" / "Hörbuch #2 100%" / "02.mp3")
    nas.serie("Rabe", serie_id="s1", name="Rabe", folgen=["Folge 1.mp3", "Hörbuch #2 100%"])
    lege_mp3(nas.medien / "Zwei" / "A.mp3")
    nas.serie("Zwei", serie_id="s2", name="Zwei", folgen=["A.mp3"])
    await integration.medien.pruefen()
    return nas


@pytest.fixture
async def client(hass, bestand, hass_client):
    return await hass_client()


def url(serie, folge, track=None):
    return audio.audio_pfad(serie, folge, track)


async def test_200_mit_kopfzeilen(client, bestand):
    r = await client.get(url("s1", "Folge 1.mp3"))
    assert r.status == 200
    daten = await r.read()
    assert len(daten) == (bestand.medien / "Rabe" / "Folge 1.mp3").stat().st_size
    assert r.headers["Content-Type"] == "audio/mpeg"
    assert r.headers["Accept-Ranges"] == "bytes"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Cache-Control"] == "private, max-age=3600"
    assert r.headers["X-Tobibox-Quelle"] == "original"
    assert "Content-Disposition" not in r.headers


async def test_206_mit_range(client, bestand):
    r = await client.get(url("s1", "Folge 1.mp3"), headers={"Range": "bytes=0-9"})
    assert r.status == 206
    assert len(await r.read()) == 10
    assert r.headers["Content-Range"].startswith("bytes 0-9/")
    r = await client.get(url("s1", "Folge 1.mp3"), headers={"Range": "bytes=100-"})
    assert r.status == 206
    assert r.headers["Content-Range"].startswith("bytes 100-")


async def test_416_bei_unmoeglichem_bereich(client, bestand):
    r = await client.get(url("s1", "Folge 1.mp3"), headers={"Range": "bytes=99999999-"})
    assert r.status == 416


async def test_head(client, bestand):
    r = await client.head(url("s1", "Folge 1.mp3"))
    assert r.status == 200
    assert int(r.headers["Content-Length"]) > 0


async def test_ordner_folge_mit_track(client, bestand):
    folge = "Hörbuch #2 100%"
    assert (await client.get(url("s1", folge, 0))).status == 200
    assert (await client.get(url("s1", folge, 1))).status == 200
    assert (await client.get(url("s1", folge))).status == 200  # ohne track: der erste
    assert (await client.get(url("s1", folge, 2))).status == 404
    assert (await client.get(url("s1", "Folge 1.mp3", 1))).status == 404  # Einzeldatei hat nur Track 0
    assert (await client.get(url("s1", folge) + "?track=-1")).status == 404
    assert (await client.get(url("s1", folge) + "?track=abc")).status == 404


@pytest.mark.parametrize(
    ("serie", "folge"),
    [
        ("s1", "A.mp3"),  # Datei gibt es nur in s2
        ("s1", "..%2F..%2Fs2%2FA.mp3"),
        ("s1", "%2e%2e"),
        ("..", "Folge 1.mp3"),
        ("Rabe", "Folge 1.mp3"),  # Ordnername statt ID
        ("s1", "serie.json"),
        ("s1", "folge 1.mp3"),  # ganze Zeichenkette, nicht ohne Groß/Klein
        ("_papierkorb", "x.mp3"),
        ("nix", "x.mp3"),
    ],
)
async def test_pfade_von_aussen_werden_abgelehnt(client, bestand, serie, folge):
    r = await client.get(f"/api/tobibox/audio/{quote(serie, safe='')}/{folge if '%' in folge else quote(folge, safe='')}")
    assert r.status in (400, 404)  # ``..`` weist schon aiohttp ab
    assert "tobibox" not in (await r.text()).lower().replace("folge_nicht_gefunden", "")  # keine Pfade im Text


async def test_verknuepfung_aus_dem_medien_pfad_hinaus_ist_404(client, bestand, tmp_path, lege_mp3):
    draussen = lege_mp3(tmp_path / "ausserhalb" / "geheim.mp3")
    (bestand.medien / "Zwei" / "Link.mp3").symlink_to(draussen)
    bestand.serie("Zwei", serie_id="s2", name="Zwei", folgen=["A.mp3", "Link.mp3"])
    r = await client.get(url("s2", "Link.mp3"))
    assert r.status == 404


async def test_ohne_anmeldung_abgelehnt(hass, bestand, hass_client_no_auth):
    c = await hass_client_no_auth()
    assert (await c.get(url("s1", "Folge 1.mp3"))).status == 401
    assert (await c.get(url("s1", "Folge 1.mp3") + "?authSig=unsinn")).status == 401


async def test_lesender_benutzer_darf_hoeren(hass, bestand, hass_client, hass_read_only_access_token):
    c = await hass_client(hass_read_only_access_token)
    assert (await c.get(url("s1", "Folge 1.mp3"))).status == 200


async def test_bereit_und_signierter_pfad(hass, bestand, hass_ws_client, hass_client_no_auth):
    ws = await hass_ws_client(hass)
    c = await hass_client_no_auth()
    for nr, (folge, track) in enumerate((("Folge 1.mp3", None), ("Hörbuch #2 100%", 1)), start=1):
        msg = {"id": nr, "type": "tobibox/audio/bereit", "serie_id": "s1", "folge_id": folge}
        if track is not None:
            msg["track"] = track
        await ws.send_json(msg)
        antwort = await ws.receive_json()
        assert antwort["success"], antwort
        r = antwort["result"]
        assert r["zustand"] == "bereit"
        assert r["gueltig_s"] == 86400
        assert "authSig=" in r["pfad"]
        assert r["pfad"].startswith(audio.audio_pfad("s1", folge))
        # ohne Anmeldekopf, nur mit Signatur
        g = await c.get(r["pfad"], headers={"Range": "bytes=0-9"})
        assert g.status == 206
        # ein anderer Track passt nicht zur Signatur
        if track is not None:
            falsch = r["pfad"].replace("track=1", "track=0")
            assert (await c.get(falsch)).status == 401
        # eine andere Datei passt nicht zur Signatur
        assert (await c.get(r["pfad"].replace("/s1/", "/s2/"))).status == 401


async def test_bereit_unbekannte_folge(hass, bestand, hass_ws_client):
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tobibox/audio/bereit", "serie_id": "s1", "folge_id": "../x"})
    antwort = await ws.receive_json()
    assert not antwort["success"]
    assert antwort["error"]["code"] == "folge_nicht_gefunden"


async def test_zaehler_begrenzt_und_gibt_frei(hass, bestand, client):
    from custom_components.tobibox.audio import _ZAEHLER

    assert (await (await client.get(url("s1", "Folge 1.mp3"))).read())
    await warte_auf(hass, lambda: not hass.data.get(_ZAEHLER))  # nach der Übertragung wieder frei
    hass.data[_ZAEHLER] = {k: AUDIO_VERBINDUNGEN_JE_BENUTZER for k in _alle_nutzer(hass)}
    r = await client.get(url("s1", "Folge 1.mp3"))
    assert r.status == 429
    assert (await r.json())["fehler"]["code"] == "zu_viele_streams"


def _alle_nutzer(hass):
    return [u.id for u in hass.auth._store._users.values()]
