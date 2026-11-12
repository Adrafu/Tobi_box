"""Paket A4 „Cover-Backend“ (Vertrag W, 14.3 und 14.10; Design V-1, 5.5 und G7, G11).

* ``cover_pruefen_und_skalieren``: Kopf zuerst, Pixelbombe, CMYK, progressiv, PNG mit JPEG-Endung, kaputte Bilder.
* HTTP: GET mit ETag, POST (Foto-Upload, 3-MiB-Grenze auch ohne ``Content-Length``), DELETE ``quelle=eigen``, Menge, Rechte.
* Cover aus den Tags (``APIC``) mit der Marke „schon versucht“ im Store ``tobibox.medieninfo``, Nachholen im Hintergrund,
  Zeitgrenze, ``ffmpeg`` fehlt.
* Einsortieren (mitgeliefertes ``cover.jpg`` wird kopiert), Zusammenführen, Wiederherstellen, Umbenennen (G11).
* Befehl ``cover/neu_suchen``.
"""

from __future__ import annotations

import io
import re
import stat
import struct
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image, JpegImagePlugin

from custom_components.tobibox import cover as cover_modul
from custom_components.tobibox import ffprobe
from custom_components.tobibox.const import (
    COVER_GROSS_PX,
    COVER_JE_STUNDE,
    COVER_KANTE_MAX_PX,
    COVER_KLEIN_PX,
    COVER_UPLOAD_MAX_BYTES,
)
from custom_components.tobibox.cover import bildkopf, cover_pruefen_und_skalieren
from custom_components.tobibox.fehler import TobiboxFehler

from .conftest import braucht_ffmpeg, erzeuge_audio, warte_auf
from .test_eingang import alle_serien, sortiere
from .test_websocket_api import fehler, ok

MIB = 1024 * 1024
UEBERSCHRIFT_STAND = re.compile(r"^[0-9a-f]{8}$")


# --------------------------------------------------------------------------
# Bilder und Dateien, die die Tests brauchen
# --------------------------------------------------------------------------


def bild(groesse: tuple[int, int] = (600, 600), format_: str = "JPEG", modus: str = "RGB", **optionen) -> bytes:
    farben = {"RGB": (200, 30, 30), "CMYK": (0, 255, 255, 0), "L": 120, "RGBA": (10, 200, 10, 128), "P": 3}
    im = Image.new(modus, groesse, farben[modus])
    puffer = io.BytesIO()
    im.save(puffer, format_, **optionen)
    return puffer.getvalue()


def masse(daten: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(daten)) as b:
        return b.size


def auf_laenge(jpeg: bytes, laenge: int) -> bytes:
    """Füllt ein JPEG mit Kommentar-Segmenten (``COM``) direkt hinter ``SOI`` auf genau ``laenge`` Bytes auf."""
    fehlt = laenge - len(jpeg)
    assert fehlt >= 0
    fuell = b""
    while fehlt > 0:
        n = min(fehlt, 65535)
        if n < 4:  # ein Segment braucht mindestens Marke (2) und Länge (2)
            n = 4
        fuell += b"\xff\xfe" + struct.pack(">H", n - 2) + b"\x00" * (n - 4)
        fehlt -= n
    assert fehlt == 0
    return jpeg[:2] + fuell + jpeg[2:]


def pixelbombe(breite: int = 30000, hoehe: int = 30000, laenge: int = 3 * MIB - 64) -> bytes:
    """Ein JPEG um 3 MiB, dessen Kopf 30 000 × 30 000 px behauptet (dekodiert wären das 2,7 GB)."""
    roh = bild((64, 64))
    i = roh.index(b"\xff\xc0\x00\x11\x08")  # SOF0, drei Komponenten, 8 Bit
    gepatcht = roh[: i + 5] + struct.pack(">HH", hoehe, breite) + roh[i + 9 :]
    return auf_laenge(gepatcht, laenge)


def _syncsafe(n: int) -> bytes:
    return bytes([(n >> 21) & 0x7F, (n >> 14) & 0x7F, (n >> 7) & 0x7F, n & 0x7F])


def mp3_mit_bild(mp3: bytes, picture: bytes, mime: bytes = b"image/jpeg") -> bytes:
    """Eine mp3 mit einem ``APIC``-Rahmen (ID3v2.3) von Hand: so lässt sich auch ein präpariertes Bild einbetten.

    Die vorhandenen Rahmen (Tags von ``ffmpeg``) bleiben erhalten."""
    alt = b""
    if mp3[:3] == b"ID3":
        gross = (mp3[6] << 21) | (mp3[7] << 14) | (mp3[8] << 7) | mp3[9]
        assert mp3[3] == 3 and not mp3[5] & 0x40, "nur ID3v2.3 ohne erweiterten Kopf"
        alt, mp3 = mp3[10 : 10 + gross], mp3[10 + gross :]
    koerper = b"\x00" + mime + b"\x00" + b"\x03" + b"\x00" + picture
    rahmen = b"APIC" + struct.pack(">I", len(koerper)) + b"\x00\x00" + koerper + alt
    return b"ID3\x03\x00\x00" + _syncsafe(len(rahmen)) + rahmen + mp3


def setze_bild(pfad: Path, picture: bytes, mime: bytes = b"image/jpeg") -> Path:
    pfad.write_bytes(mp3_mit_bild(pfad.read_bytes(), picture, mime))
    return pfad


def dateien_im_ordner(pfad: Path) -> list[str]:
    return sorted(p.name for p in pfad.iterdir())


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
async def bestand(integration, nas, lege_mp3):
    """Serien ``rabe`` und ``zwei`` mit je einer mp3 ohne Bild; der Start-Lauf hat noch nichts zu tun."""
    for sid in ("rabe", "zwei"):
        pfad = nas.serie(sid, sid, f"Serie {sid}", ["a.mp3"])
        lege_mp3(pfad / "a.mp3")
    await integration.medien.pruefen()
    await integration.cover.warte_auf_ende()
    return integration


@pytest.fixture
async def api(hass, bestand, hass_ws_client):
    return await hass_ws_client(hass)


@pytest.fixture
async def api_normal(hass, bestand, hass_ws_client, hass_read_only_access_token):
    return await hass_ws_client(hass, hass_read_only_access_token)


@pytest.fixture
async def client(hass, bestand, hass_client):
    return await hass_client()


@pytest.fixture
async def client_normal(hass, bestand, hass_client, hass_read_only_access_token):
    return await hass_client(hass_read_only_access_token)


async def serie_kurz(hub, serie_id: str) -> dict:
    return next(s for s in (await hub.medien.serien_liste())["serien"] if s["id"] == serie_id)


def url(serie_id: str = "rabe") -> str:
    return f"/api/tobibox/cover/{serie_id}"


# --------------------------------------------------------------------------
# cover_pruefen_und_skalieren
# --------------------------------------------------------------------------


def test_skaliert_auf_512_und_192_und_wirft_metadaten_weg():
    exif = Image.Exif()
    exif[0x010F] = "Kamera-Hersteller"  # Make
    original = bild((1200, 1200), exif=exif.tobytes())
    gross, klein = cover_pruefen_und_skalieren(original)
    assert masse(gross) == (COVER_GROSS_PX, COVER_GROSS_PX) and masse(klein) == (COVER_KLEIN_PX, COVER_KLEIN_PX)
    assert gross[:3] == klein[:3] == b"\xff\xd8\xff"
    assert gross != original and len(gross) < len(original)
    with Image.open(io.BytesIO(gross)) as b:
        assert not b.getexif()  # EXIF ist weg


def test_kleines_bild_wird_nicht_vergroessert():
    gross, klein = cover_pruefen_und_skalieren(bild((100, 100)))
    assert masse(gross) == (100, 100) and masse(klein) == (100, 100)
    gross, klein = cover_pruefen_und_skalieren(bild((300, 300)))
    assert masse(gross) == (300, 300) and masse(klein) == (COVER_KLEIN_PX, COVER_KLEIN_PX)


@pytest.mark.parametrize("optionen", [{"progressive": True}, {"progressive": True, "optimize": True}, {"subsampling": 0, "quality": 100}])
def test_progressive_jpegs_gehen(optionen):
    gross, _klein = cover_pruefen_und_skalieren(bild((700, 700), **optionen))
    assert masse(gross) == (COVER_GROSS_PX, COVER_GROSS_PX)


def test_cmyk_jpeg_wird_zu_rgb_und_behaelt_die_farbe():
    gross, klein = cover_pruefen_und_skalieren(bild((600, 600), modus="CMYK"))
    with Image.open(io.BytesIO(gross)) as b:
        assert b.mode == "RGB"
        r, g, bl = b.getpixel((10, 10))
        assert r > 200 and g < 80 and bl < 80  # CMYK (0, 255, 255, 0) ist Rot
    with Image.open(io.BytesIO(klein)) as b:
        assert b.mode == "RGB"


def test_graustufen_und_png_mit_alpha_werden_zu_rgb():
    gross, _ = cover_pruefen_und_skalieren(bild((600, 600), modus="L"))
    with Image.open(io.BytesIO(gross)) as b:
        assert b.mode == "RGB"
    gross, _ = cover_pruefen_und_skalieren(bild((600, 600), "PNG", modus="RGBA"), erlaubt=("jpeg", "png"))
    with Image.open(io.BytesIO(gross)) as b:
        assert b.mode == "RGB"
        assert b.getpixel((5, 5))[1] > 150  # halb durchsichtiges Grün auf Weiß: hell, nicht schwarz


def test_png_mit_jpeg_endung_zaehlt_nach_den_kopfbytes():
    png = bild((600, 600), "PNG")
    assert bildkopf(png)[0] == "png"  # die Endung kommt nirgends vor: der Typ steht in den Kopfbytes
    with pytest.raises(TobiboxFehler) as err:
        cover_pruefen_und_skalieren(png)  # das Foto aus der Seite muss ein JPEG sein
    assert err.value.code == "cover_ungueltig"
    gross, klein = cover_pruefen_und_skalieren(png, erlaubt=("jpeg", "png"))  # ein Bild aus Tags oder ``cover.png`` darf PNG sein
    assert gross[:3] == b"\xff\xd8\xff" and masse(klein) == (COVER_KLEIN_PX, COVER_KLEIN_PX)


@pytest.mark.parametrize(
    "daten",
    [
        b"",
        b"kein Bild",
        b"\xff\xd8\xff",  # nur der Anfang
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 20,  # kein SOF
        b"\x89PNG\r\n\x1a\n",  # PNG ohne IHDR
        b"GIF89a" + b"\x00" * 100,
        b"RIFF\x00\x00\x00\x00WEBPVP8 ",
        bild((600, 600))[:200],  # abgeschnitten, der Kopf passt aber
        bild((600, 600))[:-300],  # hinten abgeschnitten
        bild((600, 600))[:400] + b"\x00" * 3000,  # Kopf gut, Bilddaten Müll
    ],
)
def test_kaputte_bilder_sind_cover_ungueltig(daten):
    with pytest.raises(TobiboxFehler) as err:
        cover_pruefen_und_skalieren(daten, erlaubt=("jpeg", "png"))
    assert err.value.code == "cover_ungueltig"


def test_pixelbombe_wird_am_kopf_abgelehnt_ohne_ein_pixel_zu_dekodieren():
    bombe = pixelbombe()
    assert 3 * MIB - 1024 < len(bombe) <= COVER_UPLOAD_MAX_BYTES
    assert bildkopf(bombe) == ("jpeg", 30000, 30000)
    with (
        patch.object(Image, "open", side_effect=AssertionError("Pillow darf nicht einmal geöffnet werden")) as geoeffnet,
        patch.object(Image.Image, "load", side_effect=AssertionError("kein Pixel darf dekodiert werden")),
    ):
        with pytest.raises(TobiboxFehler) as err:
            cover_pruefen_und_skalieren(bombe)
    assert err.value.code == "cover_ungueltig" and geoeffnet.call_count == 0


def test_pixelbombe_auch_als_png_und_mit_grossem_quadrat_knapp_ueber_der_grenze():
    # PNG-Kopf (IHDR) mit 30 000 × 30 000
    png = bytearray(bild((64, 64), "PNG"))
    png[16:24] = struct.pack(">II", 30000, 30000)
    with patch.object(Image, "open", side_effect=AssertionError):
        with pytest.raises(TobiboxFehler):
            cover_pruefen_und_skalieren(bytes(png), erlaubt=("jpeg", "png"))
    # 2049 px ist eins zu viel, 2048 px gehen
    with pytest.raises(TobiboxFehler):
        cover_pruefen_und_skalieren(bild((COVER_KANTE_MAX_PX + 1,) * 2))
    gross, _ = cover_pruefen_und_skalieren(bild((COVER_KANTE_MAX_PX,) * 2))
    assert masse(gross) == (COVER_GROSS_PX, COVER_GROSS_PX)


def test_quadrat_bis_auf_zwei_prozent():
    cover_pruefen_und_skalieren(bild((1000, 985)))  # 15 px = 1,5 %
    cover_pruefen_und_skalieren(bild((1000, 980)))  # genau 2 %
    for breite, hoehe in ((1000, 970), (800, 600), (600, 800)):
        with pytest.raises(TobiboxFehler) as err:
            cover_pruefen_und_skalieren(bild((breite, hoehe)))
        assert err.value.code == "cover_ungueltig"
    cover_pruefen_und_skalieren(bild((800, 600)), quadrat=False)  # eine Datei, die schon im Serien-Ordner liegt


# --- Modus ``nachsichtig`` (Tags und mitgelieferte Dateien): verkleinern und mittig quadratisch zuschneiden ---

NACHSICHTIG = {"erlaubt": ("jpeg", "png"), "modus": "nachsichtig"}


def zweifarbig(groesse: tuple[int, int], format_: str = "JPEG", **optionen) -> bytes:
    """Linke Hälfte rot, rechte Hälfte blau (und oben/unten gleich), damit sich Zuschnitt und Drehung prüfen lassen."""
    im = Image.new("RGB", groesse, (230, 20, 20))
    im.paste((20, 20, 230), (groesse[0] // 2, 0, groesse[0], groesse[1]))
    puffer = io.BytesIO()
    im.save(puffer, format_, quality=95, **optionen)
    return puffer.getvalue()


def test_nachsichtig_tag_bild_3000_mal_3000_wird_angenommen():
    gross, klein = cover_pruefen_und_skalieren(bild((3000, 3000)), **NACHSICHTIG)
    assert masse(gross) == (COVER_GROSS_PX, COVER_GROSS_PX)
    assert masse(klein) == (COVER_KLEIN_PX, COVER_KLEIN_PX)


def test_nachsichtig_jpeg_wird_nur_verkleinert_dekodiert():
    with patch.object(JpegImagePlugin.JpegImageFile, "draft", autospec=True, side_effect=JpegImagePlugin.JpegImageFile.draft) as entwurf:
        cover_pruefen_und_skalieren(bild((3000, 3000)), **NACHSICHTIG)
    assert entwurf.call_count == 1


@pytest.mark.parametrize("groesse", [(1000, 1500), (1500, 1000), (4000, 2500), (1000, 985)])
def test_nachsichtig_nicht_quadratisch_wird_mittig_quadratisch(groesse):
    gross, klein = cover_pruefen_und_skalieren(bild(groesse), **NACHSICHTIG)
    assert masse(gross) == (COVER_GROSS_PX, COVER_GROSS_PX)
    assert masse(klein) == (COVER_KLEIN_PX, COVER_KLEIN_PX)


def test_nachsichtig_schneidet_aus_der_mitte_und_nicht_vom_rand():
    # 1500 breit, links rot, rechts blau; die Mitte (500 bis 1000) enthält die Grenze bei 750
    gross, _ = cover_pruefen_und_skalieren(zweifarbig((1500, 1000)), **NACHSICHTIG)
    with Image.open(io.BytesIO(gross)) as b:
        assert b.getpixel((10, 256))[0] > 150 and b.getpixel((500, 256))[2] > 150  # links rot, rechts blau
    # Hochformat 1000 × 1500: oben rot, unten blau, Mitte um die Grenze bei 750
    hoch = Image.new("RGB", (1000, 1500), (230, 20, 20))
    hoch.paste((20, 20, 230), (0, 750, 1000, 1500))
    puffer = io.BytesIO()
    hoch.save(puffer, "JPEG", quality=95)
    gross, _ = cover_pruefen_und_skalieren(puffer.getvalue(), **NACHSICHTIG)
    with Image.open(io.BytesIO(gross)) as b:
        assert b.getpixel((256, 10))[0] > 150 and b.getpixel((256, 500))[2] > 150


def test_nachsichtig_png_quer_wird_ebenso_zugeschnitten():
    gross, _ = cover_pruefen_und_skalieren(bild((1800, 900), "PNG"), **NACHSICHTIG)
    assert masse(gross) == (COVER_GROSS_PX, COVER_GROSS_PX)


def test_nachsichtig_pixelbombe_wird_weiter_am_kopf_abgelehnt():
    bombe = pixelbombe()
    png = bytearray(bild((64, 64), "PNG"))
    png[16:24] = struct.pack(">II", 30000, 30000)
    for daten in (bombe, bytes(png)):
        with (
            patch.object(Image, "open", side_effect=AssertionError("Pillow darf nicht geöffnet werden")) as geoeffnet,
            patch.object(Image.Image, "load", side_effect=AssertionError("kein Pixel darf dekodiert werden")),
        ):
            with pytest.raises(TobiboxFehler) as err:
                cover_pruefen_und_skalieren(daten, **NACHSICHTIG)
        assert err.value.code == "cover_ungueltig" and geoeffnet.call_count == 0


def test_nachsichtig_beachtet_die_exif_drehung_vor_dem_zuschnitt():
    # 1500 × 1000 (quer), links rot und rechts blau, EXIF "um 90° im Uhrzeigersinn drehen" (6):
    # angezeigt wird ein Hochformat 1000 × 1500, oben die frühere linke Seite (rot), unten blau
    exif = Image.Exif()
    exif[0x0112] = 6
    daten = zweifarbig((1500, 1000), exif=exif)
    gross, _ = cover_pruefen_und_skalieren(daten, **NACHSICHTIG)
    with Image.open(io.BytesIO(gross)) as b:
        assert b.size == (COVER_GROSS_PX, COVER_GROSS_PX)
        assert b.getpixel((256, 10))[0] > 150 and b.getpixel((256, 500))[2] > 150  # oben rot, unten blau
        assert not b.getexif()
    # ohne Drehung wäre es links rot, rechts blau: die Drehung wurde also wirklich angewendet
    ohne, _ = cover_pruefen_und_skalieren(zweifarbig((1500, 1000)), **NACHSICHTIG)
    with Image.open(io.BytesIO(ohne)) as b:
        assert b.getpixel((10, 256))[0] > 150 and b.getpixel((500, 256))[2] > 150


def test_streng_bleibt_streng_fuer_den_upload():
    for groesse in ((1500, 1000), (3000, 3000), (800, 600)):
        with pytest.raises(TobiboxFehler) as err:
            cover_pruefen_und_skalieren(bild(groesse))
        assert err.value.code == "cover_ungueltig"


def test_ueber_drei_mib_ist_datei_zu_gross_auch_im_kern():
    genau = auf_laenge(bild((600, 600)), COVER_UPLOAD_MAX_BYTES)
    assert len(genau) == COVER_UPLOAD_MAX_BYTES
    cover_pruefen_und_skalieren(genau)  # genau 3 MiB gehen
    with pytest.raises(TobiboxFehler) as err:
        cover_pruefen_und_skalieren(auf_laenge(bild((600, 600)), COVER_UPLOAD_MAX_BYTES + 1))
    assert err.value.code == "datei_zu_gross"


# --------------------------------------------------------------------------
# HTTP: GET, POST, DELETE
# --------------------------------------------------------------------------


async def test_get_ohne_cover_und_unbekannte_serie(client, bestand):
    r = await client.get(url())
    assert r.status == 404 and (await r.json())["fehler"]["code"] == "cover_nicht_gefunden"
    r = await client.get(url("gibts-nicht"))
    assert r.status == 404 and (await r.json())["fehler"]["code"] == "serie_nicht_gefunden"
    r = await client.get(url() + "?groesse=riesig")
    assert r.status == 400 and (await r.json())["fehler"]["code"] == "invalid_format"
    kurz = await serie_kurz(bestand, "rabe")
    assert (kurz["cover_stand"], kurz["cover_quelle"]) == (None, None)


async def test_foto_upload_speichert_nur_das_skalierte_und_nie_das_original(client, bestand, nas):
    original = bild((1500, 1500), progressive=True)
    stand_vorher = (await serie_kurz(bestand, "rabe"))["stand"]
    r = await client.post(url(), data=original, headers={"Content-Type": "image/jpeg"})
    assert r.status == 200, await r.text()
    antwort = await r.json()
    assert antwort["v"] == 1 and antwort["serie_id"] == "rabe" and antwort["cover_quelle"] == "eigen"
    assert UEBERSCHRIFT_STAND.match(antwort["cover_stand"])
    ordner = nas.medien / "rabe"
    assert dateien_im_ordner(ordner) == ["a.mp3", "cover-eigen.jpg", "serie.json"]  # keine Zwischendatei, kein Original
    gespeichert = (ordner / "cover-eigen.jpg").read_bytes()
    assert gespeichert != original and masse(gespeichert) == (COVER_GROSS_PX, COVER_GROSS_PX)
    assert not any(p.read_bytes() == original for p in nas.basis.rglob("*") if p.is_file())
    assert not any(p.stat().st_size >= len(original) for p in ordner.glob("cover*"))
    # in der Kurzform, in serie/get, und das Ereignis kommt an
    kurz = await serie_kurz(bestand, "rabe")
    assert (kurz["cover_stand"], kurz["cover_quelle"]) == (antwort["cover_stand"], "eigen")
    assert (await bestand.medien.serie_holen("rabe"))["cover_stand"] == antwort["cover_stand"]
    # ``serie.json`` und ``stand`` bleiben unberührt
    assert "cover" not in (nas.medien / "rabe" / "serie.json").read_text() and kurz["stand"] == stand_vorher


async def test_get_gross_klein_etag_und_304(client, bestand):
    await client.post(url(), data=bild((900, 900)))
    stand = (await serie_kurz(bestand, "rabe"))["cover_stand"]
    gross = await client.get(url() + "?groesse=gross")
    assert gross.status == 200 and gross.headers["Content-Type"] == "image/jpeg"
    assert gross.headers["ETag"] == f'"{stand}"' and gross.headers["Cache-Control"] == "private, max-age=86400"
    assert masse(await gross.read()) == (COVER_GROSS_PX, COVER_GROSS_PX)
    klein = await client.get(url() + "?groesse=klein")
    assert klein.status == 200 and klein.headers["ETag"] == f'"{stand}"'
    assert masse(await klein.read()) == (COVER_KLEIN_PX, COVER_KLEIN_PX)
    assert masse(await (await client.get(url())).read()) == (COVER_GROSS_PX, COVER_GROSS_PX)  # Vorgabe: gross
    for kopf in (f'"{stand}"', stand, f'W/"{stand}"', f'"nein", "{stand}"', "*"):
        r = await client.get(url() + "?groesse=klein", headers={"If-None-Match": kopf})
        assert r.status == 304, kopf
        assert r.headers["ETag"] == f'"{stand}"' and await r.read() == b""
    assert (await client.get(url(), headers={"If-None-Match": '"00000000"'})).status == 200
    # ein neues Foto ändert den Fingerabdruck, und der alte ETag gilt nicht mehr
    time.sleep(0.01)
    await client.post(url(), data=bild((900, 900), quality=50))
    neu = (await serie_kurz(bestand, "rabe"))["cover_stand"]
    assert neu != stand
    assert (await client.get(url(), headers={"If-None-Match": f'"{stand}"'})).status == 200


async def test_post_lehnt_ungueltiges_ab_und_laesst_nichts_zurueck(client, bestand, nas):
    for daten, code, status in (
        (b"", "cover_ungueltig", 400),
        (b"keine Bilddatei", "cover_ungueltig", 400),
        (bild((600, 600), "PNG"), "cover_ungueltig", 400),  # ein PNG ist kein Foto im Sinn von 14.3, auch mit JPEG-Kopf im Header
        (bild((800, 600)), "cover_ungueltig", 400),  # nicht quadratisch
        (bild((600, 600))[:-500], "cover_ungueltig", 400),
        (pixelbombe(), "cover_ungueltig", 400),
        (bild((2049, 2049)), "cover_ungueltig", 400),
    ):
        r = await client.post(url(), data=daten, headers={"Content-Type": "image/jpeg"})
        assert (r.status, (await r.json())["fehler"]["code"]) == (status, code)
    assert dateien_im_ordner(nas.medien / "rabe") == ["a.mp3", "serie.json"]
    r = await client.post(url("gibts-nicht"), data=bild())
    assert r.status == 404 and (await r.json())["fehler"]["code"] == "serie_nicht_gefunden"


async def test_post_dreimib_grenze_mit_content_length(client, nas):
    r = await client.post(url(), data=auf_laenge(bild((600, 600)), COVER_UPLOAD_MAX_BYTES))
    assert r.status == 200
    r = await client.post(url(), data=auf_laenge(bild((600, 600)), COVER_UPLOAD_MAX_BYTES + 1))
    assert r.status == 413 and (await r.json())["fehler"]["code"] == "datei_zu_gross"


async def test_post_dreimib_grenze_gilt_auch_ohne_content_length(client, nas):
    """Ein Rumpf im Strom (``Transfer-Encoding: chunked``) hat keine ``Content-Length``: gezählt wird beim Lesen."""

    def strom(daten: bytes):
        async def erzeuge():
            for i in range(0, len(daten), 65536):
                yield daten[i : i + 65536]

        return erzeuge()

    gesendet = []

    async def endlos(gesamt: int):
        n = 0
        while n < gesamt:
            gesendet.append(1)
            yield b"\x00" * 65536
            n += 65536

    # genau 3 MiB als Strom: angenommen
    r = await client.post(url(), data=strom(auf_laenge(bild((600, 600)), COVER_UPLOAD_MAX_BYTES)))
    assert r.status == 200, await r.text()
    # ein Byte mehr als Strom: 413, und der Server liest nicht weiter, als nötig ist
    r = await client.post(url(), data=strom(auf_laenge(bild((600, 600)), COVER_UPLOAD_MAX_BYTES + 1)))
    assert r.status == 413 and (await r.json())["fehler"]["code"] == "datei_zu_gross"
    # ein Strom, der nie aufhört (hier 64 MiB angeboten): 413 statt 16 MiB Speicher
    r = await client.post(url(), data=endlos(64 * MIB))
    assert r.status == 413
    assert len(gesendet) * 65536 < 64 * MIB


async def test_delete_eigen_gibt_das_automatische_zurueck(client, bestand, nas):
    auto = bild((300, 300), quality=30)
    (nas.medien / "rabe" / "cover.jpg").write_bytes(cover_pruefen_und_skalieren(auto)[0])
    await bestand.medien.pruefen()
    kurz = await serie_kurz(bestand, "rabe")
    assert kurz["cover_quelle"] == "auto"
    auto_stand = kurz["cover_stand"]
    await client.post(url(), data=bild((900, 900)))
    kurz = await serie_kurz(bestand, "rabe")
    assert kurz["cover_quelle"] == "eigen" and kurz["cover_stand"] != auto_stand
    r = await client.delete(url() + "?quelle=eigen")
    assert r.status == 200
    antwort = await r.json()
    assert (antwort["cover_quelle"], antwort["cover_stand"]) == ("auto", auto_stand)
    assert not (nas.medien / "rabe" / "cover-eigen.jpg").exists() and (nas.medien / "rabe" / "cover.jpg").exists()
    # noch einmal: kein Fehler, nichts ändert sich; ohne ``quelle=eigen`` ist es ungültig
    assert (await client.delete(url() + "?quelle=eigen")).status == 200
    for abfrage in ("", "?quelle=auto", "?quelle="):
        r = await client.delete(url() + abfrage)
        assert r.status == 400 and (await r.json())["fehler"]["code"] == "invalid_format"
    assert (await client.delete(url("gibts-nicht") + "?quelle=eigen")).status == 404
    assert (await client.get(url())).status == 200  # das automatische Cover bleibt


async def test_ereignis_serien_geaendert_bei_neuem_cover(client, bestand, ereignisse):
    await client.post(url(), data=bild())
    assert any(e["thema"] == "medien" and e["art"] == "serien_geaendert" and e["daten"]["serie_ids"] == ["rabe"] for e in ereignisse)


# --------------------------------------------------------------------------
# Rechte und Menge
# --------------------------------------------------------------------------


async def test_rechte_ohne_anmeldung_401_und_jeder_angemeldete_darf(hass, bestand, hass_client_no_auth, client_normal, client):
    ohne = await hass_client_no_auth()
    for methode, ziel in (("get", url()), ("post", url()), ("delete", url() + "?quelle=eigen")):
        assert (await getattr(ohne, methode)(ziel)).status == 401, methode
    # Recht „alltag“ gilt für jeden angemeldeten Benutzer (Vertrag W, 2.1), auch ohne Administrator
    assert (await client_normal.post(url(), data=bild())).status == 200
    assert (await client_normal.get(url())).status == 200
    assert (await client_normal.delete(url() + "?quelle=eigen")).status == 200
    assert (await client.get(url())).status == 404


async def test_befehl_neu_suchen_ist_nur_fuer_administratoren(api, api_normal):
    assert await fehler(api_normal, "cover/neu_suchen") == "unauthorized"
    assert await fehler(api_normal, "cover/neu_suchen", serie_id="rabe") == "unauthorized"
    assert (await ok(api, "cover/neu_suchen", serie_id="rabe"))["eintraege"] == 1


async def test_hoechstens_zwanzig_cover_je_stunde_und_benutzer(hass, bestand, client_normal, client, hass_read_only_user):
    assert COVER_JE_STUNDE == 20
    klein = bild((64, 64))
    for _ in range(20):
        assert (await client_normal.post(url(), data=klein)).status == 200
    r = await client_normal.post(url(), data=klein)
    assert r.status == 429 and (await r.json())["fehler"]["code"] == "zu_viele_aenderungen"
    assert bestand.schutz.mengen.summe("cover", hass_read_only_user.id) == 20  # der abgelehnte zählt nicht
    # je Benutzer: ein anderer Benutzer (Administrator, unbegrenzt) ist frei
    for _ in range(22):
        assert (await client.post(url("zwei"), data=klein)).status == 200
    # lesen und löschen zählen nicht
    assert (await client_normal.get(url())).status == 200
    assert (await client_normal.delete(url() + "?quelle=eigen")).status == 200
    # nach einer Stunde geht es wieder
    fenster = bestand.schutz.mengen._gebucht[("cover", hass_read_only_user.id)]
    for i, (t, m) in enumerate(fenster):  # (die Uhr springen zu lassen, liefe die Anmeldung ab)
        fenster[i] = (t - 3601, m)
    assert (await client_normal.post(url(), data=klein)).status == 200
    assert bestand.schutz.mengen.summe("cover", hass_read_only_user.id) == 1


async def test_auch_abgelehnte_bilder_zaehlen_als_versuch(bestand, client_normal, hass_read_only_user):
    for _ in range(3):
        assert (await client_normal.post(url(), data=b"kein bild")).status == 400
    assert bestand.schutz.mengen.summe("cover", hass_read_only_user.id) == 3


# --------------------------------------------------------------------------
# Cover aus den Tags, Marke „schon versucht“, Nachholen
# --------------------------------------------------------------------------


@braucht_ffmpeg
async def test_mp3_mit_bild_liefert_cover_und_marke_tags(bestand, nas):
    setze_bild(nas.medien / "rabe" / "a.mp3", bild((1000, 1000)))
    bestand.cover.suche_anstossen(["rabe"])
    await bestand.cover.warte_auf_ende()
    cover = nas.medien / "rabe" / "cover.jpg"
    assert cover.is_file() and masse(cover.read_bytes()) == (COVER_GROSS_PX, COVER_GROSS_PX)
    assert bestand.medieninfo.cover_suche("rabe")["ergebnis"] == "tags"
    kurz = await serie_kurz(bestand, "rabe")
    assert kurz["cover_quelle"] == "auto" and UEBERSCHRIFT_STAND.match(kurz["cover_stand"])
    # ``stand`` der Serie und ``serie.json`` bleiben unberührt, die Marke liegt im Store
    assert "cover" not in (nas.medien / "rabe" / "serie.json").read_text()
    assert bestand.medieninfo.daten["rabe"]["cover_suche"]["zeit"]


@braucht_ffmpeg
async def test_mp3_ohne_bild_bekommt_keine_marke_und_kein_cover(bestand, nas):
    bestand.cover.suche_anstossen(["rabe"])
    await bestand.cover.warte_auf_ende()
    assert not (nas.medien / "rabe" / "cover.jpg").exists()
    assert bestand.medieninfo.cover_suche("rabe")["ergebnis"] == "keine"
    assert (await serie_kurz(bestand, "rabe"))["cover_quelle"] is None


@braucht_ffmpeg
async def test_erste_folge_mit_bild_zaehlt_auch_bei_ordner_folgen(bestand, nas, lege_mp3):
    pfad = nas.serie("buch", "buch", "Ein Buch", ["ohne.mp3", "teil"])
    lege_mp3(pfad / "ohne.mp3")
    setze_bild(lege_mp3(pfad / "teil" / "01.mp3"), bild((700, 700), "PNG"), b"image/png")  # PNG im Tag: wird zu JPEG
    await bestand.medien.pruefen()
    bestand.cover.suche_anstossen(["buch"])
    await bestand.cover.warte_auf_ende()
    assert masse((pfad / "cover.jpg").read_bytes()) == (COVER_GROSS_PX, COVER_GROSS_PX)
    assert bestand.medieninfo.cover_suche("buch")["ergebnis"] == "tags"


@braucht_ffmpeg
@pytest.mark.parametrize(
    "praepariert",
    [
        pytest.param(pixelbombe(), id="pixelbombe"),
        pytest.param(b"\xff\xd8\xff" + b"kein Bild" * 100, id="muell-mit-jpeg-kopf"),
        pytest.param(b"\x00" * (COVER_UPLOAD_MAX_BYTES + 1000), id="ueber-drei-mib"),
        pytest.param(b"", id="leer"),
    ],
)
async def test_praepariertes_apic_ergibt_kein_cover_und_keinen_fehler(bestand, nas, praepariert):
    setze_bild(nas.medien / "rabe" / "a.mp3", praepariert)
    with patch.object(Image.Image, "load", autospec=True, side_effect=Image.Image.load) as geladen:
        bestand.cover.suche_anstossen(["rabe"])
        await bestand.cover.warte_auf_ende()
    assert not (nas.medien / "rabe" / "cover.jpg").exists()
    assert bestand.medieninfo.cover_suche("rabe")["ergebnis"] == "keine"
    assert geladen.call_count == 0  # kein präpariertes Bild kommt über den Kopf hinaus
    assert dateien_im_ordner(nas.medien / "rabe") == ["a.mp3", "serie.json"]


@braucht_ffmpeg
async def test_apic_mit_png_daten_und_falschem_typ_wird_nach_den_kopfbytes_gelesen(bestand, nas):
    setze_bild(nas.medien / "rabe" / "a.mp3", bild((650, 650), "PNG"), b"image/jpeg")  # Tag sagt JPEG, die Bytes sind PNG
    bestand.cover.suche_anstossen(["rabe"])
    await bestand.cover.warte_auf_ende()
    assert (nas.medien / "rabe" / "cover.jpg").is_file()


@braucht_ffmpeg
async def test_marke_schon_versucht_verhindert_die_zweite_suche(bestand, nas):
    with patch.object(cover_modul, "suche_in_serie", wraps=cover_modul.suche_in_serie) as suche:
        bestand.cover.suche_anstossen(["rabe"])
        await bestand.cover.warte_auf_ende()
        assert suche.call_count == 1 and bestand.medieninfo.cover_suche("rabe")["ergebnis"] == "keine"
        # Nachholen (Start): ``rabe`` hat eine Marke und wird übergangen, ``zwei`` nicht
        bestand.cover.beim_start_nachgeholt = False
        bestand.cover.nachholen_beim_start()
        await bestand.cover.warte_auf_ende()
        gesucht = [Path(c.args[0]).name for c in suche.call_args_list]
        assert gesucht == ["rabe", "zwei"]  # ``rabe`` hat eine Marke: kein zweites Mal
        # und ein zweiter Nachhol-Lauf in derselben Sitzung tut nichts
        vorher = suche.call_count
        bestand.cover.nachholen_beim_start()
        await bestand.cover.warte_auf_ende()
        assert suche.call_count == vorher


@braucht_ffmpeg
async def test_nachholen_nach_dem_start_im_hintergrund_ohne_dauer_scan(hass, starte_integration, nas, lege_mp3):
    for sid in ("a", "b", "c"):
        pfad = nas.serie(sid, sid, f"Serie {sid}", ["x.mp3"])
        lege_mp3(pfad / "x.mp3")
    setze_bild(nas.medien / "b" / "x.mp3", bild((600, 600)))
    with patch.object(cover_modul, "suche_in_serie", wraps=cover_modul.suche_in_serie) as suche:
        hub = await starte_integration()
        await hub.cover.warte_auf_ende()
        assert sorted(Path(c.args[0]).name for c in suche.call_args_list) == ["a", "b", "c"]  # jede einmal, nach dem Start
        assert (nas.medien / "b" / "cover.jpg").is_file() and not (nas.medien / "a" / "cover.jpg").exists()
        assert {s: hub.medieninfo.cover_suche(s)["ergebnis"] for s in "abc"} == {"a": "keine", "b": "tags", "c": "keine"}
        # ``medien/pruefen`` und der 10-Minuten-Lauf starten keine Suche
        await hub.medien.pruefen()
        await hub.medien.pruefen()
        await hub.cover.warte_auf_ende()
        assert suche.call_count == 3


@braucht_ffmpeg
async def test_marke_ueberlebt_den_neustart_im_store(hass, hass_storage, starte_integration, nas, lege_mp3):
    pfad = nas.serie("a", "a", "Serie a", ["x.mp3"])
    lege_mp3(pfad / "x.mp3")
    hub = await starte_integration()
    await hub.cover.warte_auf_ende()
    assert hub.medieninfo.cover_suche("a")["ergebnis"] == "keine"
    await hub.medieninfo.async_speichern()
    assert hass_storage["tobibox.medieninfo"]["data"]["a"]["cover_suche"]["ergebnis"] == "keine"
    neu = type(hub.medieninfo)(hass)
    await neu.async_laden()
    assert neu.cover_suche("a")["ergebnis"] == "keine"


async def test_ffmpeg_fehlt_ist_kein_fehler_die_faehigkeit_bleibt_und_upload_geht(bestand, nas, api, client):
    setze_bild(nas.medien / "rabe" / "a.mp3", bild((600, 600)))
    with patch.object(ffprobe, "ffmpeg_pfad", return_value=None):
        bestand.cover.suche_anstossen(["rabe", "zwei"])
        await bestand.cover.warte_auf_ende()
    assert not (nas.medien / "rabe" / "cover.jpg").exists()
    assert bestand.medieninfo.cover_suche("rabe") is None  # keine Marke: mit ffmpeg wird später gesucht
    assert "cover" in (await ok(api, "hello", v=1))["faehigkeiten"]
    assert (await client.post(url(), data=bild())).status == 200  # das Foto aus der Seite braucht nur Pillow
    assert (await ok(api, "cover/neu_suchen"))["eintraege"] == 2
    await bestand.cover.warte_auf_ende()


@braucht_ffmpeg
async def test_zeitgrenze_beendet_ffmpeg_und_die_suche_geht_weiter(bestand, nas, tmp_path):
    langsam = tmp_path / "ffmpeg-langsam"
    langsam.write_text("#!/bin/sh\nexec sleep 30\n")
    langsam.chmod(langsam.stat().st_mode | stat.S_IXUSR)
    with patch.object(cover_modul, "COVER_SUCHE_ZEITGRENZE_S", 0.3), patch.object(ffprobe, "ffmpeg_pfad", return_value=str(langsam)):
        start = time.monotonic()
        assert cover_modul.bild_aus_tags(nas.medien / "rabe" / "a.mp3", "mp3") is None
        assert time.monotonic() - start < 5  # nicht 30 Sekunden
        start = time.monotonic()
        bestand.cover.suche_anstossen(["rabe", "zwei"])
        await bestand.cover.warte_auf_ende()
        assert time.monotonic() - start < 10
    assert bestand.medieninfo.cover_suche("rabe")["ergebnis"] == "keine"
    assert bestand.medieninfo.cover_suche("zwei")["ergebnis"] == "keine"  # die zweite Serie wurde trotzdem gesucht


async def test_freigabe_weg_bricht_den_lauf_ab_ohne_marke(bestand, nas):
    with patch.object(cover_modul, "suche_in_serie", side_effect=OSError("NAS weg")) as suche:
        bestand.cover.suche_anstossen(["rabe", "zwei"])
        await bestand.cover.warte_auf_ende()
    assert suche.call_count == 1  # medien_nicht_erreichbar: Abbruch, die Warteschlange ist leer
    assert bestand.cover._offen == {}
    assert bestand.medieninfo.cover_suche("rabe") is None and bestand.medieninfo.cover_suche("zwei") is None


async def test_folder_jpg_im_serien_ordner_wird_als_quelle_gelesen_und_nie_geschrieben(bestand, nas):
    (nas.medien / "rabe" / "folder.jpg").write_bytes(bild((900, 900)))
    (nas.medien / "zwei" / "cover.png").write_bytes(bild((700, 700), "PNG"))
    original = (nas.medien / "rabe" / "folder.jpg").read_bytes()
    bestand.cover.suche_anstossen(["rabe", "zwei"])
    await bestand.cover.warte_auf_ende()
    for sid in ("rabe", "zwei"):
        assert masse((nas.medien / sid / "cover.jpg").read_bytes()) == (COVER_GROSS_PX, COVER_GROSS_PX)
        assert bestand.medieninfo.cover_suche(sid)["ergebnis"] == "datei"
    assert (nas.medien / "rabe" / "folder.jpg").read_bytes() == original  # die Quelle bleibt, wie sie war


# --------------------------------------------------------------------------
# Einsortieren: mitgeliefertes cover.jpg wird kopiert
# --------------------------------------------------------------------------


@braucht_ffmpeg
async def test_mitgeliefertes_cover_jpg_wird_kopiert_und_das_original_geht_in_den_papierkorb(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Buch" / "a.mp3", album="Das Buch", album_artist="Autor A")
    (nas.eingang / "Buch" / "Cover.JPG").write_bytes(bild((1100, 1100)))
    original = (nas.eingang / "Buch" / "Cover.JPG").read_bytes()
    await sortiere(integration)
    await integration.cover.warte_auf_ende()
    serie = alle_serien(nas)["Autor A"]
    cover = nas.medien / serie["_ordner"] / "cover.jpg"
    assert cover.is_file() and cover.read_bytes() != original and masse(cover.read_bytes()) == (COVER_GROSS_PX, COVER_GROSS_PX)
    assert integration.medieninfo.cover_suche(serie["id"])["ergebnis"] == "datei"
    # das Original folgt der alten Regel (Vertrag W, 11.10): Papierkorb, unverändert
    assert not (nas.eingang / "Buch").exists()
    papierkorb = (await integration.medien.papierkorb_liste(100, 0))["eintraege"]
    assert [(e["typ"], e["grund"]) for e in papierkorb] == [("eingang", "eingang_rest")]
    assert (nas.papierkorb / papierkorb[0]["id"] / "inhalt" / "Buch" / "Cover.JPG").read_bytes() == original
    kurz = await serie_kurz(integration, serie["id"])
    assert kurz["cover_quelle"] == "auto" and UEBERSCHRIFT_STAND.match(kurz["cover_stand"])


@braucht_ffmpeg
async def test_mitgeliefertes_bild_hat_vorrang_vor_dem_tag_und_ein_kaputtes_wird_uebergangen(hass, integration, nas):
    erzeuge_audio(nas.eingang / "Eins" / "a.mp3", frequenz=410, album="Eins", album_artist="Autor E")
    setze_bild(nas.eingang / "Eins" / "a.mp3", bild((600, 600), quality=10))
    (nas.eingang / "Eins" / "folder.jpg").write_bytes(bild((600, 600), modus="L"))
    erzeuge_audio(nas.eingang / "Zwei" / "a.mp3", frequenz=420, album="Zwei", album_artist="Autor Z")
    (nas.eingang / "Zwei" / "cover.jpg").write_bytes(b"kein Bild")
    await sortiere(integration)
    await integration.cover.warte_auf_ende()
    serien = alle_serien(nas)
    eins, zwei = serien["Autor E"], serien["Autor Z"]
    assert integration.medieninfo.cover_suche(eins["id"])["ergebnis"] == "datei"
    with Image.open(nas.medien / eins["_ordner"] / "cover.jpg") as b:
        r, g, bl = b.getpixel((5, 5))
        assert abs(r - g) < 6 and abs(g - bl) < 6  # grau: das mitgelieferte Bild, nicht das rote aus dem Tag
    assert not (nas.medien / zwei["_ordner"] / "cover.jpg").exists()
    assert integration.medieninfo.cover_suche(zwei["id"])["ergebnis"] == "keine"
    papierkorb = (await integration.medien.papierkorb_liste(100, 0))["eintraege"]
    assert sorted(e["anzeige"] for e in papierkorb) == ["Eins", "Zwei"]  # beide Reste wie bisher im Papierkorb


@braucht_ffmpeg
async def test_einsortieren_ohne_bild_liest_das_tag_und_neue_folgen_loesen_bei_marke_keine_eine_neue_suche_aus(hass, integration, nas):
    erzeuge_audio(nas.eingang / "a.mp3", frequenz=450, album="Reihe", album_artist="Autor R")
    await sortiere(integration)
    await integration.cover.warte_auf_ende()
    sid = alle_serien(nas)["Autor R"]["id"]
    assert integration.medieninfo.cover_suche(sid)["ergebnis"] == "keine"
    # eine neue Folge mit Bild im Tag: genau eine neue Suche, jetzt mit Treffer
    erzeuge_audio(nas.eingang / "b.mp3", frequenz=460, album="Reihe", album_artist="Autor R")
    setze_bild(nas.eingang / "b.mp3", bild((640, 640)))
    with patch.object(cover_modul, "suche_in_serie", wraps=cover_modul.suche_in_serie) as suche:
        await sortiere(integration)
        await integration.cover.warte_auf_ende()
        assert suche.call_count == 1
    assert integration.medieninfo.cover_suche(sid)["ergebnis"] == "tags"
    assert (nas.medien / alle_serien(nas)["Autor R"]["_ordner"] / "cover.jpg").is_file()
    # und weitere Folgen bei Marke „tags“ lösen nichts mehr aus
    erzeuge_audio(nas.eingang / "c.mp3", frequenz=470, album="Reihe", album_artist="Autor R")
    with patch.object(cover_modul, "suche_in_serie", wraps=cover_modul.suche_in_serie) as suche:
        await sortiere(integration)
        await integration.cover.warte_auf_ende()
        assert suche.call_count == 0


@braucht_ffmpeg
async def test_loses_cover_jpg_im_eingang_gehoert_keinem_eintrag(hass, integration, nas):
    """Eine Datei direkt im Eingang (nicht in einem Ordner) bekommt nie das ``cover.jpg`` eines anderen Eintrags."""
    (nas.eingang / "cover.jpg").write_bytes(bild((600, 600)))
    erzeuge_audio(nas.eingang / "lose.mp3", frequenz=480, album="Lose", album_artist="Autor L")
    await sortiere(integration)
    await integration.cover.warte_auf_ende()
    serie = alle_serien(nas)["Autor L"]
    assert not (nas.medien / serie["_ordner"] / "cover.jpg").exists()


# --------------------------------------------------------------------------
# Zusammenführen, Wiederherstellen, Umbenennen (G11)
# --------------------------------------------------------------------------


async def foto(client, serie_id: str, **kw) -> str:
    assert (await client.post(url(serie_id), data=bild(**kw))).status == 200


async def test_zusammenfuehren_uebernimmt_das_cover_der_quelle_wenn_das_ziel_keines_hat(client, api, bestand, nas):
    await foto(client, "rabe")
    (nas.medien / "rabe" / "cover.jpg").write_bytes(cover_pruefen_und_skalieren(bild((400, 400), quality=40))[0])
    await bestand.medien.pruefen()
    quelle_eigen = (nas.medien / "rabe" / "cover-eigen.jpg").read_bytes()
    r = await ok(api, "serien/zusammenfuehren", quelle_id="rabe", ziel_id="zwei")
    ziel = nas.medien / "zwei"
    assert (ziel / "cover-eigen.jpg").read_bytes() == quelle_eigen and (ziel / "cover.jpg").is_file()
    assert r["ziel"]["cover_quelle"] == "eigen" and UEBERSCHRIFT_STAND.match(r["ziel"]["cover_stand"])
    assert (await serie_kurz(bestand, "zwei"))["cover_stand"] == r["ziel"]["cover_stand"]
    # die Quelle liegt als Ganzes im Papierkorb und behält ihre Cover-Dateien
    eintrag = r["eintrag"]
    inhalt = nas.papierkorb / eintrag["id"] / "inhalt" / "rabe"
    assert (inhalt / "cover-eigen.jpg").read_bytes() == quelle_eigen and (inhalt / "cover.jpg").is_file()


async def test_zusammenfuehren_laesst_ein_vorhandenes_cover_des_ziels_in_ruhe(client, api, bestand, nas):
    await foto(client, "rabe", quality=95)
    await foto(client, "zwei", quality=20)
    ziel_vorher = (nas.medien / "zwei" / "cover-eigen.jpg").read_bytes()
    await ok(api, "serien/zusammenfuehren", quelle_id="rabe", ziel_id="zwei")
    assert (nas.medien / "zwei" / "cover-eigen.jpg").read_bytes() == ziel_vorher
    assert not (nas.medien / "zwei" / "cover.jpg").exists()  # (rabe hatte nur ein Foto)


async def test_wiederherstellen_aus_dem_papierkorb_bringt_das_cover_mit(client, api, bestand, nas):
    await foto(client, "rabe")
    vorher = await serie_kurz(bestand, "rabe")
    datei_vorher = (nas.medien / "rabe" / "cover-eigen.jpg").read_bytes()
    r = await ok(api, "serie/delete", serie_id="rabe")
    assert not (nas.medien / "rabe").exists() and "rabe" not in bestand.medien.serien
    assert (nas.papierkorb / r["eintrag"]["id"] / "inhalt" / "rabe" / "cover-eigen.jpg").is_file()
    assert (await client.get(url())).status == 404  # solange die Serie im Papierkorb liegt, gibt es sie nicht
    wieder = await ok(api, "papierkorb/restore", eintrag_id=r["eintrag"]["id"])
    assert wieder["serie"]["cover_quelle"] == "eigen" and wieder["serie"]["cover_stand"] == vorher["cover_stand"]
    assert (nas.medien / "rabe" / "cover-eigen.jpg").read_bytes() == datei_vorher
    antwort = await client.get(url() + "?groesse=klein")
    assert antwort.status == 200 and masse(await antwort.read()) == (COVER_KLEIN_PX, COVER_KLEIN_PX)


async def test_umbenennen_laesst_das_cover_liegen(client, api, bestand, nas):
    await foto(client, "rabe")
    vorher = await serie_kurz(bestand, "rabe")
    r = await ok(api, "serie/rename", serie_id="rabe", name="Ganz anders")
    assert (r["serie"]["cover_stand"], r["serie"]["cover_quelle"], r["serie"]["ordner"]) == (vorher["cover_stand"], "eigen", "rabe")
    assert (nas.medien / "rabe" / "cover-eigen.jpg").is_file()
    assert (await client.get(url())).status == 200
    await bestand.medien.pruefen()  # auch eine neue Prüfung findet es
    assert (await serie_kurz(bestand, "rabe"))["cover_stand"] == vorher["cover_stand"]


# --------------------------------------------------------------------------
# Befehl 44: cover/neu_suchen
# --------------------------------------------------------------------------


@braucht_ffmpeg
async def test_neu_suchen_loescht_cover_jpg_und_marke_aber_nie_cover_eigen(client, api, bestand, nas):
    setze_bild(nas.medien / "rabe" / "a.mp3", bild((600, 600)))
    bestand.cover.suche_anstossen(["rabe", "zwei"])
    await bestand.cover.warte_auf_ende()
    await foto(client, "rabe")
    eigen = (nas.medien / "rabe" / "cover-eigen.jpg").read_bytes()
    assert (nas.medien / "rabe" / "cover.jpg").is_file()
    # ein Treffer in den Tags wird nach dem Löschen wiedergefunden, aus einer alten Marke ``keine`` wird eine neue Suche
    setze_bild(nas.medien / "zwei" / "a.mp3", bild((600, 600)))
    r = await ok(api, "cover/neu_suchen", serie_id="rabe")
    assert r == {"gestartet": True, "eintraege": 1}
    await bestand.cover.warte_auf_ende()
    assert (nas.medien / "rabe" / "cover-eigen.jpg").read_bytes() == eigen  # nie berührt
    assert (nas.medien / "rabe" / "cover.jpg").is_file() and bestand.medieninfo.cover_suche("rabe")["ergebnis"] == "tags"
    assert not (nas.medien / "zwei" / "cover.jpg").exists()  # nur die genannte Serie
    r = await ok(api, "cover/neu_suchen")  # alle
    assert r == {"gestartet": True, "eintraege": 2}
    await bestand.cover.warte_auf_ende()
    assert (nas.medien / "zwei" / "cover.jpg").is_file() and bestand.medieninfo.cover_suche("zwei")["ergebnis"] == "tags"
    assert (nas.medien / "rabe" / "cover-eigen.jpg").read_bytes() == eigen
    assert await fehler(api, "cover/neu_suchen", serie_id="gibts-nicht") == "serie_nicht_gefunden"


async def test_neu_suchen_ohne_freigabe_ist_medien_nicht_erreichbar(api, bestand, nas):
    with patch.object(type(bestand.medien), "_medien_erreichbar", side_effect=TobiboxFehler("medien_nicht_erreichbar")):
        assert await fehler(api, "cover/neu_suchen") == "medien_nicht_erreichbar"


# --------------------------------------------------------------------------
# Bildverarbeitung nur im Executor
# --------------------------------------------------------------------------


@braucht_ffmpeg
async def test_bildverarbeitung_laeuft_nur_im_executor(hass, client, api, bestand, nas):
    loop_thread = threading.get_ident()
    threads: list[int] = []
    echt = cover_modul.cover_pruefen_und_skalieren

    def gemerkt(*args, **kw):
        threads.append(threading.get_ident())
        return echt(*args, **kw)

    with (
        patch.object(cover_modul, "cover_pruefen_und_skalieren", gemerkt),
        patch("custom_components.tobibox.http.cover_pruefen_und_skalieren", gemerkt),
    ):
        assert (await client.post(url(), data=bild((900, 900)))).status == 200  # Foto-Upload
        bestand.cover._klein.clear()  # (sonst käme die kleine Ansicht aus dem Zwischenspeicher des Uploads)
        assert (await client.get(url() + "?groesse=klein")).status == 200  # kleine Ansicht aus der Datei
        (nas.medien / "zwei" / "folder.jpg").write_bytes(bild((800, 800)))
        setze_bild(nas.medien / "rabe" / "a.mp3", bild((800, 800)))
        await ok(api, "cover/neu_suchen")  # Suche: Datei und Tag
        await bestand.cover.warte_auf_ende()
        erzeuge_audio(nas.eingang / "B" / "a.mp3", frequenz=490, album="B", album_artist="Autor B")
        (nas.eingang / "B" / "cover.jpg").write_bytes(bild((800, 800)))
        await sortiere(bestand)  # mitgeliefertes Cover beim Einsortieren
        await bestand.cover.warte_auf_ende()
    assert len(threads) >= 5 and loop_thread not in threads
