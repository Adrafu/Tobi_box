"""Testpanel (Paket A0b): Mess-Endpunkt, ffmpeg-Messung, Registrierung der Seite."""

from __future__ import annotations

import pytest

from custom_components.tobibox import testpanel

from .conftest import FFMPEG

MIB = 1024 * 1024


@pytest.fixture
async def client(hass, integration, hass_client):
    return await hass_client()


# --- Mess-Endpunkt ---


async def test_messung_zaehlt_bytes_und_verwirft(hass, client, nas):
    daten = b"x" * (3 * MIB + 17)
    r = await client.post(testpanel.MESS_URL, data=daten)
    assert r.status == 200
    antwort = await r.json()
    assert antwort["bytes"] == len(daten)
    assert antwort["sekunden"] >= 0
    # nichts gespeichert: weder im Eingang noch im Zwischenordner noch in den Medien
    assert list(nas.eingang.iterdir()) == []
    assert not (nas.medien / "_upload").exists() or list((nas.medien / "_upload").iterdir()) == []


async def test_messung_ohne_inhalt(client):
    r = await client.post(testpanel.MESS_URL, data=b"")
    assert (await r.json())["bytes"] == 0


async def test_messung_nur_administratoren(hass, integration, hass_client, hass_client_no_auth, hass_read_only_access_token):
    lesend = await hass_client(hass_read_only_access_token)
    assert (await lesend.post(testpanel.MESS_URL, data=b"abc")).status in (401, 403)
    ohne = await hass_client_no_auth()
    assert (await ohne.post(testpanel.MESS_URL, data=b"abc")).status == 401


async def test_messung_grenze(client, monkeypatch):
    monkeypatch.setattr(testpanel, "MESS_UPLOAD_MAX_BYTES", 1000)
    r = await client.post(testpanel.MESS_URL, data=b"x" * 1001)  # mit Content-Length
    assert r.status == 413
    assert (await r.json())["fehler"]["code"] == "datei_zu_gross"

    async def strom():  # ohne Content-Length: die Grenze gilt trotzdem
        for _ in range(3):
            yield b"x" * 600

    r = await client.post(testpanel.MESS_URL, data=strom())
    assert r.status == 413
    assert (await client.post(testpanel.MESS_URL, data=b"x" * 1000)).status == 200


# --- ffmpeg-Messung ---


async def ws_messen(hass, hass_ws_client, token=None, **felder):
    ws = await hass_ws_client(hass, token) if token else await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "tobibox/testpanel/ffmpeg_messen", **felder})
    return await ws.receive_json()


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg fehlt")
async def test_ffmpeg_messung_mit_datei(hass, integration, nas, lege_mp3, hass_ws_client):
    lege_mp3(nas.medien / "Rabe" / "Folge 1.mp3")
    nas.serie("Rabe", serie_id="s1", name="Rabe", folgen=["Folge 1.mp3"])
    await integration.medien.pruefen()
    antwort = await ws_messen(hass, hass_ws_client, serie_id="s1", folge_id="Folge 1.mp3")
    assert antwort["success"], antwort
    r = antwort["result"]
    assert r["ffmpeg"] is True
    assert r["version"].startswith("ffmpeg version")
    assert r["umwandlung"]["zustand"] == "ok"
    assert r["umwandlung"]["audio_s"] > 0
    assert r["umwandlung"]["faktor"] > 0
    assert isinstance(r["aac_encoder"], list)
    assert str(nas.medien) not in str(r)  # keine Pfade in der Antwort


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg fehlt")
async def test_ffmpeg_messung_ohne_datei(hass, integration, hass_ws_client):
    r = (await ws_messen(hass, hass_ws_client))["result"]
    assert r["ffmpeg"] is True
    assert r["umwandlung"] is None
    assert any("aac" in z for z in r["aac_encoder"])


async def test_ffmpeg_messung_unbekannte_folge(hass, integration, hass_ws_client):
    if FFMPEG is None:
        pytest.skip("ffmpeg fehlt")
    antwort = await ws_messen(hass, hass_ws_client, serie_id="nix", folge_id="x.mp3")
    assert not antwort["success"]
    assert antwort["error"]["code"] == "folge_nicht_gefunden"


async def test_ffmpeg_messung_nur_administratoren(hass, integration, hass_ws_client, hass_read_only_access_token):
    antwort = await ws_messen(hass, hass_ws_client, token=hass_read_only_access_token)
    assert not antwort["success"]
    assert antwort["error"]["code"] == "unauthorized"


async def test_ffmpeg_fehlt_saubere_meldung(hass, integration, hass_ws_client, monkeypatch):
    monkeypatch.setattr(testpanel, "ffmpeg_programm", lambda hass: (None, "PATH"))
    antwort = await ws_messen(hass, hass_ws_client, serie_id="s1", folge_id="x.mp3")
    assert antwort["success"]
    assert antwort["result"]["ffmpeg"] is False
    assert "nicht gefunden" in antwort["result"]["meldung"]


async def test_ffmpeg_programm_faellt_auf_path_zurueck(hass, monkeypatch):
    monkeypatch.setattr(testpanel.shutil, "which", lambda name: None)
    assert testpanel.ffmpeg_programm(hass) == (None, "PATH")
    monkeypatch.setattr(testpanel.shutil, "which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    assert testpanel.ffmpeg_programm(hass) == ("/usr/bin/ffmpeg", "PATH")


def test_zeitgrenze_ergibt_meldung(monkeypatch, tmp_path):
    monkeypatch.setattr(testpanel, "_lauf", lambda args, zeit: _Fertig(args) if "-version" in args or "-encoders" in args else None)
    datei = tmp_path / "a.mp3"
    datei.write_bytes(b"x")
    r = testpanel.messe_ffmpeg("ffmpeg", "PATH", datei)
    assert r["umwandlung"]["zustand"] == "zeitgrenze"


class _Fertig:
    returncode = 0

    def __init__(self, args):
        self.stdout = "ffmpeg version test\n" if "-version" in args else " A....D aac AAC\n"
        self.stderr = ""


# --- Registrierung ---


async def test_seite_wird_registriert_und_ist_abschaltbar(hass, starte_integration, frontend_dir):
    (frontend_dir / testpanel.PANEL_DATEI).write_text("// Attrappe\n", encoding="utf-8")
    await starte_integration()
    panels = hass.data["frontend_panels"]
    assert panels[testpanel.PANEL_URL].require_admin is True
    assert "tobibox" in panels  # die alte Seite bleibt
