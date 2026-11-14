"""Audio-Ansicht und ``audio/bereit`` (Paket A4c; Vertrag W, 14.5 und Befehl 39): Range, Pfad-Sicherheit, Anmeldung und Signatur, Zähler.

Nur der Zweig **Original**; der Zweig Kopie (Hörkopie) gehört zu Paket A4c3 (A-3).
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from urllib.parse import quote

import pytest
from homeassistant.auth.const import GROUP_ID_USER
from pytest_homeassistant_custom_component.common import CLIENT_ID

from custom_components.tobibox import audio
from custom_components.tobibox.const import AUDIO_BEREIT_JE_MINUTE, AUDIO_VERBINDUNGEN_JE_BENUTZER, ENDUNGEN

from .conftest import braucht_ffmpeg, warte_auf
from .test_websocket_api import fehler, ok, senden

pytestmark = braucht_ffmpeg

#: Namen aus dem Design (11.4.6): alles, was in einer Adresse Schaden anrichten kann
SONDERNAMEN = [
    "Der Wald (Teil 1).mp3",
    "Märchen.m4a",
    "Teil 1 #2 (Ende)?.mp3",
    "100% Mond+Sterne.mp3",
    "&Rest.mp3",
    "a b;c=d,e.mp3",
    "ä\u0308 ß 日本.mp3",
]


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


async def _normal(hass, hass_ws_client, name="Normal"):
    nutzer = await hass.auth.async_create_user(name, group_ids=[GROUP_ID_USER])
    refresh = await hass.auth.async_create_refresh_token(nutzer, CLIENT_ID)
    return await hass_ws_client(hass, hass.auth.async_create_access_token(refresh))


# --------------------------------------------------------------------------
# HTTP: Antwort, Range
# --------------------------------------------------------------------------


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
    assert r.headers["ETag"] and r.headers["Last-Modified"]


async def test_content_type_je_endung_aus_eigener_tabelle(hass, client, bestand):
    erwartet = {"mp3": "audio/mpeg", "m4a": "audio/mp4", "m4b": "audio/mp4", "aac": "audio/aac", "flac": "audio/flac", "ogg": "audio/ogg",
                "opus": "audio/ogg", "wav": "audio/wav"}
    assert set(erwartet) == set(ENDUNGEN) == set(audio.CONTENT_TYPES)
    folgen = []
    for endung in erwartet:
        (bestand.medien / "Zwei" / f"t.{endung}").write_bytes(b"x" * 64)  # die Ansicht liest den Inhalt nie
        folgen.append(f"t.{endung}")
    bestand.serie("Zwei", serie_id="s2", name="Zwei", folgen=["A.mp3", *folgen])
    await hass.data["tobibox"].medien.pruefen()
    for endung, typ in erwartet.items():
        r = await client.get(url("s2", f"t.{endung}"))
        assert (r.status, r.headers["Content-Type"]) == (200, typ), endung


async def test_206_mit_range(client, bestand):
    r = await client.get(url("s1", "Folge 1.mp3"), headers={"Range": "bytes=0-9"})
    assert r.status == 206
    assert len(await r.read()) == 10
    assert r.headers["Content-Range"].startswith("bytes 0-9/")
    assert r.headers["Accept-Ranges"] == "bytes"
    r = await client.get(url("s1", "Folge 1.mp3"), headers={"Range": "bytes=100-"})
    assert r.status == 206
    assert r.headers["Content-Range"].startswith("bytes 100-")
    r = await client.get(url("s1", "Folge 1.mp3"), headers={"Range": "bytes=-500"})  # die letzten 500 Bytes (Safari fragt so nach dem Ende)
    assert r.status == 206
    assert len(await r.read()) == 500


async def test_teilanfrage_liefert_genau_die_bytes_der_datei(client, bestand):
    roh = (bestand.medien / "Rabe" / "Folge 1.mp3").read_bytes()
    r = await client.get(url("s1", "Folge 1.mp3"), headers={"Range": "bytes=1000-1999"})
    assert r.status == 206
    assert await r.read() == roh[1000:2000]


async def test_416_bei_unmoeglichem_bereich(client, bestand):
    r = await client.get(url("s1", "Folge 1.mp3"), headers={"Range": "bytes=99999999-"})
    assert r.status == 416
    assert r.headers["Content-Range"].startswith("bytes */")


async def test_nur_ein_bereich_je_anfrage(client, bestand):
    """Mehrere Bereiche in einer Anfrage fragt kein Browser; sie bekommen nie ein ``multipart``."""
    r = await client.get(url("s1", "Folge 1.mp3"), headers={"Range": "bytes=0-9,20-29"})
    assert r.status in (200, 206, 416)
    assert "multipart" not in r.headers.get("Content-Type", "")


async def test_head(client, bestand):
    r = await client.head(url("s1", "Folge 1.mp3"))
    assert r.status == 200
    assert int(r.headers["Content-Length"]) > 0


async def test_nur_lesen_post_und_delete_gibt_es_nicht(client, bestand):
    assert (await client.post(url("s1", "Folge 1.mp3"), data=b"x")).status == 405
    assert (await client.delete(url("s1", "Folge 1.mp3"))).status == 405
    assert (await client.put(url("s1", "Folge 1.mp3"), data=b"x")).status == 405


async def test_ordner_folge_mit_track(client, bestand):
    folge = "Hörbuch #2 100%"
    assert (await client.get(url("s1", folge, 0))).status == 200
    assert (await client.get(url("s1", folge, 1))).status == 200
    assert (await client.get(url("s1", folge))).status == 200  # ohne track: der erste
    assert (await client.get(url("s1", folge, 2))).status == 404
    assert (await client.get(url("s1", "Folge 1.mp3", 1))).status == 404  # Einzeldatei hat nur Track 0
    assert (await client.get(url("s1", folge) + "?track=-1")).status == 404
    assert (await client.get(url("s1", folge) + "?track=abc")).status == 404
    assert (await client.get(url("s1", folge) + "?track=1e1")).status == 404


async def test_tracks_kommen_aus_der_eigenen_sortierten_liste(client, bestand, lege_mp3):
    """``track`` zählt nach natürlicher Sortierung der Dateinamen, nicht nach der Reihenfolge auf der Platte."""
    ordner = bestand.medien / "Rabe" / "Hörbuch #2 100%"
    (ordner / "02.mp3").unlink()
    lege_mp3(ordner / "10.mp3")
    lege_mp3(ordner / "02.mp3")
    erwartet = [(ordner / n).read_bytes() for n in ("01.mp3", "02.mp3", "10.mp3")]
    (ordner / "10.mp3").write_bytes(erwartet[2] + b"\0" * 7)  # unterscheidbar: nur der dritte hat 7 Bytes mehr
    for nr, laenge in ((0, len(erwartet[0])), (1, len(erwartet[1])), (2, len(erwartet[2]) + 7)):
        r = await client.get(url("s1", "Hörbuch #2 100%", nr))
        assert (r.status, len(await r.read())) == (200, laenge), nr


# --------------------------------------------------------------------------
# HTTP: Pfad-Sicherheit (IDs statt Pfade)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("serie", "folge"),
    [
        ("s1", "A.mp3"),  # Datei gibt es nur in s2
        ("s1", "..%2F..%2Fs2%2FA.mp3"),
        ("s1", "..%2Fs2%2FA.mp3"),
        ("s1", "%2e%2e"),
        ("s1", "%2e%2e%2f%2e%2e%2fetc%2fpasswd"),
        ("s1", "%2FA.mp3"),
        ("s1", "%2Fetc%2Fpasswd"),
        ("s1", "Folge%201.mp3%00.txt"),
        ("..", "Folge 1.mp3"),
        ("%2e%2e", "Folge%201.mp3"),
        ("Rabe", "Folge 1.mp3"),  # Ordnername statt ID
        ("s1", "serie.json"),
        ("s1", "folge 1.mp3"),  # ganze Zeichenkette, nicht ohne Groß/Klein
        ("S1", "Folge 1.mp3"),
        ("_papierkorb", "x.mp3"),
        ("nix", "x.mp3"),
    ],
)
async def test_pfade_von_aussen_werden_abgelehnt(client, bestand, serie, folge):
    r = await client.get(f"/api/tobibox/audio/{quote(serie, safe='%')}/{folge if '%' in folge else quote(folge, safe='')}")
    assert r.status in (400, 404)  # ``..`` weist schon aiohttp ab
    text = (await r.text()).lower()
    assert "tmp" not in text and "/" not in text.replace("</", "")  # keine Pfade im Text


async def test_systemordner_sind_nie_eine_serie(client, bestand, lege_mp3, hass):
    """Auch wenn jemand eine ``serie.json`` in einen Systemordner legt: der Index nimmt sie nicht auf, die Ansicht liefert nichts."""
    lege_mp3(bestand.papierkorb / "x" / "inhalt" / "a.mp3")
    for ordner in ("_papierkorb", "_upload", "eingang", "export", "releases", "hoerkopien", ".versteckt", "@eaDir"):
        assert (await client.get(f"/api/tobibox/audio/{quote(ordner)}/a.mp3")).status == 404
    hub = hass.data["tobibox"]
    for name in (".x", "@x", "#x", "$x", "_x", "Eingang", "export", "releases", "hoerkopien", "_papierkorb"):
        assert audio._ist_systemname(name), name
    assert not audio._ist_systemname("Rabe") and not audio._ist_systemname("Der Wald")
    assert hub is not None


async def test_verknuepfung_aus_dem_medien_pfad_hinaus_ist_404(hass, client, bestand, tmp_path, lege_mp3):
    draussen = lege_mp3(tmp_path / "ausserhalb" / "geheim.mp3")
    (bestand.medien / "Zwei" / "Link.mp3").symlink_to(draussen)
    bestand.serie("Zwei", serie_id="s2", name="Zwei", folgen=["A.mp3", "Link.mp3"])
    await hass.data["tobibox"].medien.pruefen()
    assert "Link.mp3" in hass.data["tobibox"].medien.serien["s2"].serie.folgen  # die Folge ist bekannt: nur der Pfad-Schutz hält sie auf
    r = await client.get(url("s2", "Link.mp3"))
    assert r.status == 404


async def test_verknuepfung_in_eine_andere_serie_ist_404(hass, client, bestand):
    """Auch ein Link innerhalb von ``medien/``, aber aus dem Ordner der Serie hinaus, liefert nichts."""
    (bestand.medien / "Zwei" / "Fremd.mp3").symlink_to(bestand.medien / "Rabe" / "Folge 1.mp3")
    bestand.serie("Zwei", serie_id="s2", name="Zwei", folgen=["A.mp3", "Fremd.mp3"])
    await hass.data["tobibox"].medien.pruefen()
    assert "Fremd.mp3" in hass.data["tobibox"].medien.serien["s2"].serie.folgen
    assert (await client.get(url("s2", "Fremd.mp3"))).status == 404


async def test_name_mit_fuehrendem_punkt_ist_nie_eine_folge(client, bestand, lege_mp3):
    """Dateien mit ``.`` am Anfang listet die Integration nie als Folge (``ist_audio``); die Ansicht liefert sie also nicht, auch nicht unter dem Namen."""
    lege_mp3(bestand.medien / "Zwei" / ".versteckt.mp3")
    assert (await client.get(url("s2", ".versteckt.mp3"))).status == 404


async def test_ordner_und_fremde_dateien_sind_keine_folge(hass, client, bestand):
    """Ein Ordner ohne Audio, eine Datei mit falscher Endung und eine Datei, die nicht in ``folgen`` steht, gibt es für die Ansicht nicht."""
    (bestand.medien / "Zwei" / "Leer").mkdir()
    (bestand.medien / "Zwei" / "notiz.txt").write_text("hallo")
    bestand.serie("Zwei", serie_id="s2", name="Zwei", folgen=["A.mp3", "Leer", "notiz.txt"])
    await hass.data["tobibox"].medien.pruefen()
    for name in ("Leer", "notiz.txt", "serie.json", "Frei.mp3"):
        assert (await client.get(url("s2", name))).status == 404, name


async def test_fehlerantwort_ist_json_ohne_pfad(client, bestand):
    r = await client.get(url("s1", "nix.mp3"))
    assert r.status == 404
    antwort = await r.json()
    assert antwort["fehler"]["code"] == "folge_nicht_gefunden" and antwort["v"] == 1
    assert "tmp" not in antwort["fehler"]["text"] and "/" not in antwort["fehler"]["text"]


# --------------------------------------------------------------------------
# HTTP: Sonderzeichen in Namen, über die ganze Kette (audio/bereit -> signierter Pfad -> Ansicht)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", SONDERNAMEN)
async def test_sonderzeichen_namen_laufen_durch_die_signatur(hass, bestand, hass_ws_client, hass_client_no_auth, client, lege_mp3, name):
    lege_mp3(bestand.medien / "Zwei" / name)
    bestand.serie("Zwei", serie_id="s2", name="Zwei", folgen=["A.mp3", name])
    await hass.data["tobibox"].medien.pruefen()
    ws = await hass_ws_client(hass)
    r = await ok(ws, "audio/bereit", serie_id="s2", folge=name)
    assert r["zustand"] == "bereit"
    ohne_anmeldung = await hass_client_no_auth()
    g = await ohne_anmeldung.get(r["pfad"], headers={"Range": "bytes=0-9"})
    assert g.status == 206, name
    assert len(await g.read()) == 10
    # mit Anmeldung geht derselbe Name ohne Signatur
    assert (await client.get(url("s2", name))).status == 200


# --------------------------------------------------------------------------
# HTTP: Anmeldung
# --------------------------------------------------------------------------


async def test_ohne_anmeldung_abgelehnt(hass, bestand, hass_client_no_auth):
    c = await hass_client_no_auth()
    assert (await c.get(url("s1", "Folge 1.mp3"))).status == 401
    assert (await c.get(url("s1", "Folge 1.mp3") + "?authSig=unsinn")).status == 401
    assert (await c.head(url("s1", "Folge 1.mp3"))).status == 401
    assert (await c.get(url("s1", "Folge 1.mp3"), headers={"Authorization": "Bearer unsinn"})).status == 401


async def test_lesender_benutzer_darf_hoeren(hass, bestand, hass_client, hass_read_only_access_token):
    c = await hass_client(hass_read_only_access_token)
    assert (await c.get(url("s1", "Folge 1.mp3"))).status == 200


async def test_signierter_pfad_gilt_24_stunden(hass, bestand, hass_ws_client, hass_client_no_auth, freezer):
    ws = await hass_ws_client(hass)
    r = await ok(ws, "audio/bereit", serie_id="s1", folge="Folge 1.mp3")
    c = await hass_client_no_auth()
    assert (await c.get(r["pfad"], headers={"Range": "bytes=0-9"})).status == 206
    freezer.tick(timedelta(hours=23, minutes=55))  # Springen und Pausen stellen neue Anfragen mit derselben Adresse
    assert (await c.get(r["pfad"], headers={"Range": "bytes=10-19"})).status == 206
    freezer.tick(timedelta(minutes=10))  # nach 24 Stunden und 5 Minuten
    assert (await c.get(r["pfad"], headers={"Range": "bytes=20-29"})).status == 401


async def test_signatur_gilt_nur_fuer_diese_datei_diesen_track_und_nur_zum_lesen(hass, bestand, hass_ws_client, hass_client_no_auth):
    ws = await hass_ws_client(hass)
    c = await hass_client_no_auth()
    r = await ok(ws, "audio/bereit", serie_id="s1", folge="Hörbuch #2 100%", track=1)
    assert "track=1" in r["pfad"]
    assert (await c.get(r["pfad"])).status == 200
    assert (await c.get(r["pfad"].replace("track=1", "track=0"))).status == 401  # ein anderer Track passt nicht zur Signatur
    assert (await c.get(r["pfad"].replace("track=1&", ""))).status == 401  # ohne ``track`` auch nicht
    assert (await c.get(r["pfad"].replace("/s1/", "/s2/"))).status == 401  # eine andere Serie auch nicht
    assert (await c.post(r["pfad"])).status in (401, 405)


async def test_signatur_stirbt_mit_der_sitzung(hass, bestand, hass_client_no_auth):
    """Wird die Anmeldung (der Refresh-Token) beendet, sind alle Adressen tot (Design 11.4.2, Gegenmittel b)."""
    from custom_components.tobibox import audio as modul

    nutzer = await hass.auth.async_create_user("Sitzung", group_ids=[GROUP_ID_USER])
    refresh = await hass.auth.async_create_refresh_token(nutzer, CLIENT_ID)
    ws = type("V", (), {"refresh_token_id": refresh.id})()
    r = await modul.bereit(hass.data["tobibox"], modul.Nutzer(nutzer.id, "Sitzung", False), ws.refresh_token_id, "s1", "Folge 1.mp3")
    c = await hass_client_no_auth()
    assert (await c.get(r["pfad"])).status == 200
    hass.auth.async_remove_refresh_token(refresh)
    assert (await c.get(r["pfad"])).status == 401


# --------------------------------------------------------------------------
# HTTP: Zähler, NAS weg
# --------------------------------------------------------------------------


async def test_zaehler_begrenzt_und_gibt_frei(hass, bestand, client):
    from custom_components.tobibox.audio import _ZAEHLER

    assert (await (await client.get(url("s1", "Folge 1.mp3"))).read())
    await warte_auf(hass, lambda: not hass.data.get(_ZAEHLER))  # nach der Übertragung wieder frei
    hass.data[_ZAEHLER] = {k: AUDIO_VERBINDUNGEN_JE_BENUTZER for k in _alle_nutzer(hass)}
    r = await client.get(url("s1", "Folge 1.mp3"))
    assert r.status == 429
    assert (await r.json())["fehler"]["code"] == "zu_viele_streams"


async def test_siebte_offene_verbindung_bekommt_429(hass, bestand, client):
    """Sechs langsam lesende Verbindungen bleiben offen (der Zähler zählt im Senden, nicht um den Rückgabewert des Handlers); die siebte
    bekommt 429, und wenn eine schließt, geht es wieder."""
    from custom_components.tobibox.audio import _ZAEHLER

    gross = bestand.medien / "Zwei" / "gross.mp3"
    with open(gross, "wb") as f:
        f.truncate(128 * 1024 * 1024)  # größer als alle Puffer: der Server blockiert beim Senden, solange niemand liest
    bestand.serie("Zwei", serie_id="s2", name="Zwei", folgen=["A.mp3", "gross.mp3"])
    await hass.data["tobibox"].medien.pruefen()
    offen = []
    try:
        for _ in range(AUDIO_VERBINDUNGEN_JE_BENUTZER):
            r = await client.get(url("s2", "gross.mp3"), headers={"Range": "bytes=0-"})
            assert r.status == 206
            offen.append(r)
        await warte_auf(hass, lambda: sum(hass.data.get(_ZAEHLER, {}).values()) == AUDIO_VERBINDUNGEN_JE_BENUTZER, block=False)
        siebte = await client.get(url("s2", "A.mp3"))
        assert siebte.status == 429
        assert (await siebte.json())["fehler"]["code"] == "zu_viele_streams"
        offen.pop().close()  # eine Verbindung schließt
        await warte_auf(hass, lambda: sum(hass.data.get(_ZAEHLER, {}).values()) == AUDIO_VERBINDUNGEN_JE_BENUTZER - 1, block=False)
        assert (await client.get(url("s2", "A.mp3"))).status == 200
    finally:
        for r in offen:
            r.close()
    await warte_auf(hass, lambda: not hass.data.get(_ZAEHLER), block=False)  # alle freigegeben


async def test_zaehler_gilt_je_benutzer(hass, bestand, client, hass_client):
    """Ein Benutzer mit voller Grenze sperrt keinen anderen aus."""
    from custom_components.tobibox.audio import _ZAEHLER

    nutzer = await hass.auth.async_create_user("Zweiter", group_ids=[GROUP_ID_USER])
    refresh = await hass.auth.async_create_refresh_token(nutzer, CLIENT_ID)
    zweiter = await hass_client(hass.auth.async_create_access_token(refresh))
    hass.data[_ZAEHLER] = {u.id: AUDIO_VERBINDUNGEN_JE_BENUTZER for u in hass.auth._store._users.values() if u.id != nutzer.id}
    assert (await client.get(url("s1", "Folge 1.mp3"))).status == 429
    assert (await zweiter.get(url("s1", "Folge 1.mp3"))).status == 200


def _alle_nutzer(hass):
    return [u.id for u in hass.auth._store._users.values()]


async def test_nas_weg_ist_503(hass, bestand, client, nas):
    assert (await client.get(url("s1", "Folge 1.mp3"))).status == 200
    verschoben = nas.basis / "medien_weg"
    nas.medien.rename(verschoben)  # die Freigabe ist nicht mehr da
    try:
        r = await client.get(url("s1", "Folge 1.mp3"))
        assert r.status == 503
        antwort = await r.json()
        assert antwort["fehler"]["code"] == "medien_nicht_erreichbar"
        assert "/" not in antwort["fehler"]["text"]
    finally:
        verschoben.rename(nas.medien)
    assert (await client.get(url("s1", "Folge 1.mp3"))).status == 200


# --------------------------------------------------------------------------
# audio/bereit (Befehl 39)
# --------------------------------------------------------------------------


async def test_bereit_und_signierter_pfad(hass, bestand, hass_ws_client, hass_client_no_auth):
    ws = await hass_ws_client(hass)
    c = await hass_client_no_auth()
    for nr, (folge, track) in enumerate((("Folge 1.mp3", None), ("Hörbuch #2 100%", 1)), start=1):
        felder = {"serie_id": "s1", "folge": folge}
        if track is not None:
            felder["track"] = track
        r = await ok(ws, "audio/bereit", **felder)
        assert r["zustand"] == "bereit"
        assert r["quelle"] == "original"
        assert set(r) == {"zustand", "pfad", "quelle"}
        assert "authSig=" in r["pfad"]
        assert r["pfad"].startswith(audio.audio_pfad("s1", folge))
        g = await c.get(r["pfad"], headers={"Range": "bytes=0-9"})  # ohne Anmeldekopf, nur mit Signatur
        assert g.status == 206
        assert g.headers["X-Tobibox-Quelle"] == "original"


async def test_bereit_vorbereiten_ist_im_zweig_original_ohne_wirkung(hass, bestand, hass_ws_client):
    ws = await hass_ws_client(hass)
    for vorbereiten in (True, False):
        r = await ok(ws, "audio/bereit", serie_id="s1", folge="Folge 1.mp3", vorbereiten=vorbereiten)
        assert r["zustand"] == "bereit"
    assert await fehler(ws, "audio/bereit", serie_id="s1", folge="Folge 1.mp3", vorbereiten="ja") == "invalid_format"


async def test_bereit_fehler(hass, bestand, hass_ws_client):
    ws = await hass_ws_client(hass)
    assert await fehler(ws, "audio/bereit", serie_id="s1", folge="../x") == "folge_nicht_gefunden"
    assert await fehler(ws, "audio/bereit", serie_id="s1", folge="A.mp3") == "folge_nicht_gefunden"
    assert await fehler(ws, "audio/bereit", serie_id="s1", folge="Folge 1.mp3", track=1) == "folge_nicht_gefunden"
    assert await fehler(ws, "audio/bereit", serie_id="s1", folge="Hörbuch #2 100%", track=2) == "folge_nicht_gefunden"
    assert await fehler(ws, "audio/bereit", serie_id="gibtsnicht", folge="A.mp3") == "serie_nicht_gefunden"
    assert await fehler(ws, "audio/bereit", serie_id="s1") == "invalid_format"
    assert await fehler(ws, "audio/bereit", serie_id="s1", folge="Folge 1.mp3", track=-1) == "invalid_format"
    assert await fehler(ws, "audio/bereit", serie_id="s1", folge="Folge 1.mp3", unbekannt=1) == "invalid_format"


async def test_bereit_nas_weg_sagt_fehlt(hass, bestand, hass_ws_client, nas):
    ws = await hass_ws_client(hass)
    verschoben = nas.basis / "medien_weg"
    nas.medien.rename(verschoben)
    try:
        r = await ok(ws, "audio/bereit", serie_id="s1", folge="Folge 1.mp3")
    finally:
        verschoben.rename(nas.medien)
    assert r == {"zustand": "fehlt", "grund": "medien_nicht_erreichbar"}


async def test_bereit_sechs_je_minute_fuer_nicht_administratoren(hass, bestand, hass_ws_client, freezer):
    normal = await _normal(hass, hass_ws_client)
    for _ in range(AUDIO_BEREIT_JE_MINUTE):
        assert (await ok(normal, "audio/bereit", serie_id="s1", folge="Folge 1.mp3"))["zustand"] == "bereit"
    assert await fehler(normal, "audio/bereit", serie_id="s1", folge="Folge 1.mp3") == "zu_viele_aenderungen"
    admin = await hass_ws_client(hass)  # Administratoren sind ausgenommen (Vertrag W, 2.4), und der Zähler gilt je Benutzer
    for _ in range(AUDIO_BEREIT_JE_MINUTE + 2):
        assert (await ok(admin, "audio/bereit", serie_id="s1", folge="Folge 1.mp3"))["zustand"] == "bereit"
    freezer.tick(timedelta(seconds=61))
    assert (await ok(normal, "audio/bereit", serie_id="s1", folge="Folge 1.mp3"))["zustand"] == "bereit"


async def test_bereit_fuer_alle_benutzer_und_hello_sagt_reinhoeren_zu(hass, bestand, hass_ws_client):
    normal = await _normal(hass, hass_ws_client)
    antwort = await senden(normal, "audio/bereit", serie_id="s1", folge="Folge 1.mp3")
    assert antwort["success"] is True
    h = await ok(normal, "hello", v=1)
    assert "reinhoeren" in h["faehigkeiten"] and "hoerkopie" not in h["faehigkeiten"]
    assert h["grenzen"]["audio_verbindungen_je_benutzer"] == AUDIO_VERBINDUNGEN_JE_BENUTZER


async def test_bereit_signiert_fuer_die_anmeldung_der_verbindung(hass, bestand, hass_ws_client, hass_client_no_auth):
    """Der Link gehört zur Anmeldung des Aufrufers: die Ansicht läuft als er (Zähler je Benutzer)."""
    from custom_components.tobibox.audio import _ZAEHLER

    normal = await _normal(hass, hass_ws_client)
    r = await ok(normal, "audio/bereit", serie_id="s1", folge="Folge 1.mp3")
    c = await hass_client_no_auth()
    hass.data[_ZAEHLER] = {u.id: AUDIO_VERBINDUNGEN_JE_BENUTZER for u in hass.auth._store._users.values() if u.name != "Normal"}
    assert (await c.get(r["pfad"])).status == 200  # der „Normal“ hat noch Platz, die anderen Benutzer sind voll
    await asyncio.sleep(0)
