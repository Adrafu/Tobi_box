"""Paket OS2: ``online_quellen.py`` (Design 3.1 bis 3.3, 7.4, 8). Kein Netz: eine Fake-Session liefert den Body in Blöcken.

Daten nur aus ``tests/fixtures/online/``. Uhr und Schlafen sind eingespeist, es wird nie echt gewartet.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest import mock

import aiohttp
import pytest

from custom_components.tobibox import online_quellen as oq
from custom_components.tobibox.online_quellen import (
    BLOCK_BYTES,
    FormatFehler,
    Gedrosselt,
    ItunesSpeicher,
    NichtErreichbar,
    OnlineQuellen,
    QuellePausiert,
    TonieListe,
    TrefferSpeicher,
    UrlAbgelehnt,
    ZuGross,
    bild_url_600,
    html_zu_text,
    lese_version,
    online_text,
    parse_itunes,
    parse_shop,
    parse_sitemap,
    parse_tonie_liste,
    pruefe_url,
)

FIXTURES = Path(__file__).parent / "fixtures" / "online"
T0 = 1_800_000_000.0


def fixture_bytes(*teile: str) -> bytes:
    return FIXTURES.joinpath(*teile).read_bytes()


# --------------------------------------------------------------------------
# Hilfen: Uhr, Fake-Session
# --------------------------------------------------------------------------


class Uhr:
    def __init__(self) -> None:
        self.t = T0
        self.geschlafen: list[float] = []

    def __call__(self) -> float:
        return self.t

    async def schlafen(self, s: float) -> None:
        # wie echtes Schlafen: andere Aufgaben laufen weiter, mehrere Schläfer wachen zur selben Zeit auf
        ziel = self.t + s
        self.geschlafen.append(s)
        await asyncio.sleep(0)
        self.t = max(self.t, ziel)


@dataclass
class Resp:
    """Eine gelieferte Antwort. ``chunks`` ist eine Liste von Blöcken oder ein Erzeuger (für große Mengen)."""

    status: int = 200
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    chunks: Any = None
    wirft: BaseException | None = None  # beim Lesen des Bodys
    gelesen: int = 0


class _Inhalt:
    def __init__(self, resp: Resp) -> None:
        self._resp = resp

    async def iter_chunked(self, n: int):  # noqa: ANN202
        r = self._resp
        if r.chunks is not None:
            quelle = iter(r.chunks)
        else:
            quelle = (r.body[i : i + n] for i in range(0, len(r.body), n))
        for block in quelle:
            r.gelesen += len(block)
            yield block
            await asyncio.sleep(0)
        if r.wirft is not None:
            raise r.wirft


class _FakeResponse:
    def __init__(self, resp: Resp) -> None:
        self.status = resp.status
        self.headers = resp.headers
        self.content = _Inhalt(resp)


class _Ctx:
    def __init__(self, session: FakeSession, url: str, kw: dict[str, Any]) -> None:
        self._session, self._url, self._kw = session, url, kw

    async def __aenter__(self) -> _FakeResponse:
        s = self._session
        s.aktiv += 1
        s.max_aktiv = max(s.max_aktiv, s.aktiv)
        try:
            ergebnis = s.handler(self._url, self._kw)
            if asyncio.iscoroutine(ergebnis):
                ergebnis = await ergebnis
        except BaseException:
            s.aktiv -= 1
            raise
        self._resp = ergebnis
        return _FakeResponse(ergebnis)

    async def __aexit__(self, *exc: Any) -> None:
        self._session.aktiv -= 1


class FakeSession:
    def __init__(self, handler: Callable[[str, dict[str, Any]], Any]) -> None:
        self.handler = handler
        self.aufrufe: list[tuple[str, dict[str, Any]]] = []
        self.aktiv = 0
        self.max_aktiv = 0

    def get(self, url: str, **kw: Any) -> _Ctx:
        self.aufrufe.append((url, kw))
        return _Ctx(self, url, kw)

    @property
    def urls(self) -> list[str]:
        return [u for u, _ in self.aufrufe]


async def inline(func: Callable[..., Any], *args: Any) -> Any:
    return func(*args)


def baue(handler: Callable[[str, dict[str, Any]], Any], uhr: Uhr | None = None, **kw: Any) -> tuple[OnlineQuellen, FakeSession, Uhr]:
    uhr = uhr or Uhr()
    session = FakeSession(handler)
    kw.setdefault("im_executor", inline)
    return OnlineQuellen(session, version="9.9.9", zeit=uhr, schlafen=uhr.schlafen, **kw), session, uhr


def immer(resp: Resp) -> Callable[[str, dict[str, Any]], Resp]:
    return lambda _u, _k: resp


ITUNES = "https://itunes.apple.com/search?term=x"
BILD = "https://is1-ssl.mzstatic.com/image/thumb/x/600x600bb.jpg"
SHOP = "https://tonies.com/de-de/tonies/bibi-blocksberg/die-grosse-hexenparty/"
SITEMAP1 = "https://tonies.com/sitemap_products_1.xml"


# --------------------------------------------------------------------------
# online_text
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("roh", "max_zeichen", "soll"),
    [
        ("  Hallo   Welt \n", 50, "Hallo Welt"),
        ("a\tb\nc", 50, "a b c"),  # Umbruch und Tab kleben keine Wörter zusammen
        ("A\x00B\x07C", 50, "ABC"),  # Steuerzeichen weg
        ("Amélie", 50, "Amélie"),  # NFC
        ("abcdefghij", 4, "abcd"),
        ("ab   cd", 3, "ab"),  # nach dem Kürzen kein Leerzeichen am Ende
        ("\x00\n  ", 10, None),
        ("", 10, None),
        ("x", 0, None),
        (None, 10, None),
        (5, 10, None),
        (b"abc", 10, None),
        (["a"], 10, None),
        ("a\ud800b", 10, "ab"),  # einzelnes Surrogat
    ],
)
def test_online_text(roh: Any, max_zeichen: int, soll: str | None) -> None:
    assert online_text(roh, max_zeichen) == soll


def test_html_zu_text_absaetze_und_kein_html() -> None:
    html = "<p>Erster &amp; <b>Absatz</b></p><p>Zweiter</p><script>boese()</script><style>x{}</style><br>Dritter<img src=x onerror=alert(1)>"
    text = html_zu_text(html, 2000)
    assert text == "Erster & Absatz\nZweiter\nDritter"
    assert "<" not in text and ">" not in text.replace("&", "")
    assert html_zu_text("", 100) is None
    assert html_zu_text(None, 100) is None
    assert html_zu_text("<p></p><script>x</script>", 100) is None
    lang = html_zu_text("<p>" + "wort " * 1000 + "</p>", 2000)
    assert lang is not None and len(lang) <= 2000


# --------------------------------------------------------------------------
# Adressen (8.1)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "host"),
    [
        ("https://itunes.apple.com/search?term=x", "itunes.apple.com"),
        ("https://raw.githubusercontent.com/a/b/c.json", "raw.githubusercontent.com"),
        ("https://tonies.com/de-de/tonies/a/b/", "tonies.com"),
        ("https://is1-ssl.mzstatic.com/image/x.jpg", "is1-ssl.mzstatic.com"),
        ("https://a.b.mzstatic.com/x", "a.b.mzstatic.com"),
        ("https://ITUNES.Apple.COM/search", "itunes.apple.com"),  # Groß/Klein: gleicher Host
        ("HTTPS://itunes.apple.com/search", "itunes.apple.com"),
    ],
)
def test_url_erlaubt(url: str, host: str) -> None:
    assert pruefe_url(url) == host


@pytest.mark.parametrize(
    "url",
    [
        "http://itunes.apple.com/search",  # kein https
        "ftp://itunes.apple.com/",
        "//itunes.apple.com/search",
        "itunes.apple.com/search",
        "",
        None,
        42,
        "https://itunes.apple.com:443/search",  # kein Port, auch nicht der übliche
        "https://itunes.apple.com:8443/search",
        "https://itunes.apple.com:abc/search",
        "https://evilmzstatic.com/x",  # Täuschung: Endung ohne Punkt
        "https://x.mzstatic.com.evil.tld/x",
        "https://mzstatic.com/x",  # nur die Endung ``.mzstatic.com``, nicht der Name selbst
        "https://.mzstatic.com/x",
        "https://a..mzstatic.com/x",
        "https://itunes.apple.com@evil.tld/",  # Benutzerteil
        "https://evil.tld@itunes.apple.com/",
        "https://user:pw@itunes.apple.com/",
        "https://itunes.apple.com\\@evil.tld/",
        "https://itunes.apple.com./search",  # Punkt am Ende
        "https://tonies.com./x",
        "https://www.tonies.com/x",  # nicht genau ``tonies.com``
        "https://apple.com/x",
        "https://itunes.apple.com.evil.tld/",
        "https://evilitunes.apple.com.evil.tld/",
        "https://127.0.0.1/",
        "https://[::1]/",
        "https://2130706433/",
        "https://itunes.apple.com%40evil.tld/",
        "https://itunes.apple.com/search with space",
        "https://itunes.apple.com/\x00",
        "https://itunes.apple.com/\n",
        "https://itunes.apple.com/ä",
        " https://itunes.apple.com/",
        "https://itunes.apple.com/" + "a" * 3000,
    ],
)
def test_url_abgelehnt(url: Any) -> None:
    with pytest.raises(UrlAbgelehnt):
        pruefe_url(url)


# --------------------------------------------------------------------------
# hole: Kopf, Weiterleitungen, Größe, Fehler
# --------------------------------------------------------------------------


async def test_hole_kopf_zeitgrenze_user_agent() -> None:
    q, session, _ = baue(immer(Resp(body=b"{}")))
    antwort = await q.hole(ITUNES, oq.QUELLE_ITUNES, kopfzeilen={"If-None-Match": "abc", "User-Agent": "Boese/1"})
    assert antwort.status == 200 and antwort.body == b"{}"
    url, kw = session.aufrufe[0]
    assert url == ITUNES
    assert kw["allow_redirects"] is False
    assert kw["timeout"].total == 10
    assert kw["headers"]["User-Agent"] == "TobiBox-HA/9.9.9"  # nicht überschreibbar
    assert kw["headers"]["If-None-Match"] == "abc"

    q2, s2, _ = baue(immer(Resp(body=b"[]")))
    await q2.hole(oq.TONIE_LISTE_URL, oq.QUELLE_TONIE_LISTE)
    assert s2.aufrufe[0][1]["timeout"].total == 60


async def test_hole_host_muss_zur_quelle_passen() -> None:
    q, session, _ = baue(immer(Resp(body=b"x")))
    with pytest.raises(UrlAbgelehnt):
        await q.hole(ITUNES, oq.QUELLE_SHOP)
    with pytest.raises(UrlAbgelehnt):
        await q.hole("https://evil.tld/", oq.QUELLE_ITUNES)
    with pytest.raises(UrlAbgelehnt):
        await q.hole("https://evilmzstatic.com/x.jpg", oq.QUELLE_BILD)
    with pytest.raises(ValueError):
        await q.hole(ITUNES, "unbekannt")
    assert session.aufrufe == []


def weiterleitung(ziele: list[str], status: int = 302) -> Callable[[str, dict[str, Any]], Resp]:
    liste = list(ziele)

    def handler(_url: str, _kw: dict[str, Any]) -> Resp:
        if liste:
            return Resp(status=status, headers={"Location": liste.pop(0)})
        return Resp(body=b"ende")

    return handler


async def test_weiterleitung_fremder_host_wird_nicht_verfolgt() -> None:
    q, session, _ = baue(weiterleitung(["https://evil.tld/x"]))
    with pytest.raises(UrlAbgelehnt):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert session.urls == [ITUNES]  # nur die erste Anfrage ging raus


@pytest.mark.parametrize(
    "ziel",
    [
        "http://itunes.apple.com/search",  # ohne https
        "https://itunes.apple.com:8080/search",
        "https://evilmzstatic.com/x",
        "https://x.mzstatic.com.evil.tld/x",
        "https://itunes.apple.com@evil.tld/",
        "//evil.tld/x",  # schemalos: wird gegen die alte Adresse aufgelöst, Host fremd
        "https://127.0.0.1/",
    ],
)
async def test_weiterleitung_prueft_wie_am_anfang(ziel: str) -> None:
    q, session, _ = baue(weiterleitung([ziel]))
    with pytest.raises(UrlAbgelehnt):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert len(session.aufrufe) == 1


async def test_weiterleitung_bis_zu_drei_spruenge() -> None:
    q, session, _ = baue(weiterleitung(["/a", "https://itunes.apple.com/b", "/c"], status=301))
    antwort = await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert antwort.body == b"ende"
    assert session.urls == [ITUNES, "https://itunes.apple.com/a", "https://itunes.apple.com/b", "https://itunes.apple.com/c"]
    assert all(kw["allow_redirects"] is False for _, kw in session.aufrufe)


async def test_weiterleitung_mehr_als_drei_spruenge() -> None:
    q, session, _ = baue(weiterleitung(["/a", "/b", "/c", "/d", "/e"]))
    with pytest.raises(UrlAbgelehnt, match="Weiterleitungen"):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert len(session.aufrufe) == 4  # Anfang plus drei Sprünge


async def test_weiterleitung_ohne_ziel() -> None:
    q, _, _ = baue(immer(Resp(status=302)))
    with pytest.raises(FormatFehler):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)


async def test_weiterleitung_zaehlt_eine_drosselstelle() -> None:
    q, _, uhr = baue(weiterleitung(["/a", "/b"]))
    await q.hole("https://tonies.com/x", oq.QUELLE_SHOP)
    await q.hole("https://tonies.com/x", oq.QUELLE_SHOP)  # zweiter Abruf: erst nach 4 s (Weiterleitungen des ersten zählten nicht doppelt)
    assert uhr.geschlafen == [4.0]


@pytest.mark.parametrize(
    ("quelle", "url", "grenze"),
    [
        (oq.QUELLE_ITUNES, ITUNES, 1_000_000),
        (oq.QUELLE_BILD, BILD, 5_000_000),
        (oq.QUELLE_SHOP, SHOP, 2_000_000),
        (oq.QUELLE_SITEMAP, SITEMAP1, 5 * 1024 * 1024),
        (oq.QUELLE_TONIE_LISTE, oq.TONIE_LISTE_URL, 20_000_000),
    ],
)
async def test_groesse_grenze_je_quelle(quelle: str, url: str, grenze: int) -> None:
    def erzeuger(n: int):  # noqa: ANN202
        block = b"\0" * BLOCK_BYTES
        rest = n
        while rest > 0:
            yield block[: min(rest, BLOCK_BYTES)]
            rest -= BLOCK_BYTES

    genau = Resp(chunks=erzeuger(grenze))
    q, _, _ = baue(immer(genau))
    antwort = await q.hole(url, quelle)
    assert len(antwort.body) == grenze  # genau an der Grenze ist erlaubt

    zu_viel = Resp(chunks=erzeuger(grenze + 1))
    q, _, _ = baue(immer(zu_viel))
    with pytest.raises(ZuGross):
        await q.hole(url, quelle)


async def test_gzip_bombe_bricht_in_bloecken_ab() -> None:
    """Entpackte Bytes zählen: Ein Strom ohne Ende wird nach der Grenze nicht weiter gelesen."""

    def endlos():  # noqa: ANN202
        block = b"\0" * BLOCK_BYTES
        while True:
            yield block

    bombe = Resp(chunks=endlos())
    q, _, _ = baue(immer(bombe))
    with pytest.raises(ZuGross):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert 1_000_000 < bombe.gelesen <= 1_000_000 + BLOCK_BYTES  # sofort nach Überschreiten Schluss


async def test_gzip_bombe_mit_echtem_aiohttp_entpacken() -> None:
    """Probe an aiohttps eigener Entpackung: ``iter_chunked`` liefert entpackte Bytes, die Zählung greift auf diese."""
    from aiohttp import http_parser

    loop = asyncio.get_running_loop()
    bombe = gzip.compress(b"\0" * (4 * 1024 * 1024))  # wenige KB gepackt, 4 MiB entpackt
    assert len(bombe) < 100_000
    kopf = b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Length: %d\r\n\r\n" % len(bombe)
    parser = http_parser.HttpResponseParser(mock.MagicMock(), loop, 2**16, max_line_size=8190, max_field_size=8190, auto_decompress=True)
    nachrichten = parser.feed_data(kopf + bombe)[0]
    _, nutzlast = nachrichten[0]

    class Echt:
        status = 200
        headers: dict[str, str] = {}
        content = nutzlast

    class Ctx:
        async def __aenter__(self) -> Any:
            return Echt()

        async def __aexit__(self, *exc: Any) -> None:
            return None

    class Sitzung:
        def get(self, url: str, **kw: Any) -> Ctx:
            return Ctx()

    q = OnlineQuellen(Sitzung(), zeit=Uhr(), im_executor=inline)
    with pytest.raises(ZuGross):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)  # 4 MiB entpackt > 1 MB
    # bei der Sitemap-Grenze (5 MiB) dieselbe Bombe: erlaubt, weil entpackt nur 4 MiB
    parser2 = http_parser.HttpResponseParser(mock.MagicMock(), loop, 2**16, max_line_size=8190, max_field_size=8190, auto_decompress=True)
    Echt.content = parser2.feed_data(kopf + bombe)[0][0][1]
    antwort = await q.hole(SITEMAP1, oq.QUELLE_SITEMAP)
    assert len(antwort.body) == 4 * 1024 * 1024


@pytest.mark.parametrize("fehler", [TimeoutError(), aiohttp.ClientConnectionError(), aiohttp.ClientPayloadError(), OSError("x")])
async def test_netzfehler_ist_nicht_erreichbar(fehler: BaseException) -> None:
    def handler(_u: str, _k: dict[str, Any]) -> Resp:
        raise fehler

    q, _, _ = baue(handler)
    with pytest.raises(NichtErreichbar):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)
    # Fehler beim Lesen des Bodys (z. B. kaputtes gzip)
    q, _, _ = baue(immer(Resp(chunks=[b"abc"], wirft=aiohttp.ClientPayloadError("gzip"))))
    with pytest.raises(NichtErreichbar):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)


async def test_sonstiger_status_ist_nicht_erreichbar_ohne_pause() -> None:
    q, _, _ = baue(immer(Resp(status=404)))
    with pytest.raises(NichtErreichbar) as info:
        await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert info.value.status == 404
    assert q.pause_bis(oq.QUELLE_ITUNES) is None
    q, _, _ = baue(immer(Resp(status=403)))
    with pytest.raises(NichtErreichbar):  # 403 ist nur beim Shop ein Formatfehler
        await q.hole(ITUNES, oq.QUELLE_ITUNES)


async def test_status_304_kommt_als_antwort() -> None:
    q, _, _ = baue(immer(Resp(status=304, headers={"ETag": "x"})))
    antwort = await q.hole(oq.TONIE_LISTE_URL, oq.QUELLE_TONIE_LISTE)
    assert antwort.status == 304 and antwort.body == b"" and antwort.headers["etag"] == "x"


# --------------------------------------------------------------------------
# Pause, 403, Drossel
# --------------------------------------------------------------------------


@pytest.mark.parametrize("status", [429, 500, 502, 503, 599])
async def test_429_und_5xx_pausieren_15_minuten(status: int) -> None:
    antwort = {"r": Resp(status=status)}
    q, session, uhr = baue(lambda _u, _k: antwort["r"])
    with pytest.raises(QuellePausiert) as info:
        await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert info.value.pause_bis == T0 + 900
    assert q.pause_bis(oq.QUELLE_ITUNES) == T0 + 900
    # während der Pause kein Netzzugriff
    uhr.t += 899
    with pytest.raises(QuellePausiert):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert len(session.aufrufe) == 1
    # andere Quellen laufen weiter (Tonies-Liste, Bilder, Shop)
    antwort["r"] = Resp(body=b"ok")
    assert (await q.hole(oq.TONIE_LISTE_URL, oq.QUELLE_TONIE_LISTE)).body == b"ok"
    assert (await q.hole(BILD, oq.QUELLE_BILD)).body == b"ok"
    # nach 15 Minuten wieder
    uhr.t += 2
    assert q.pause_bis(oq.QUELLE_ITUNES) is None
    assert (await q.hole(ITUNES, oq.QUELLE_ITUNES)).body == b"ok"


async def test_pause_gilt_fuer_shop_und_sitemap_gemeinsam() -> None:
    q, session, _ = baue(immer(Resp(status=429)))
    with pytest.raises(QuellePausiert):
        await q.hole(SITEMAP1, oq.QUELLE_SITEMAP)
    with pytest.raises(QuellePausiert):
        await q.hole(SHOP, oq.QUELLE_SHOP)
    assert len(session.aufrufe) == 1
    assert q.pause_bis(oq.QUELLE_SHOP) == q.pause_bis(oq.QUELLE_SITEMAP)


async def test_shop_403_ist_formatfehler_ohne_wiederholung(caplog: pytest.LogCaptureFixture) -> None:
    q, session, uhr = baue(immer(Resp(status=403)))
    with caplog.at_level(logging.WARNING, logger=oq.__name__):
        with pytest.raises(FormatFehler) as info:
            await q.hole(SHOP, oq.QUELLE_SHOP)
        assert info.value.code == "online_shop_format"
        assert len(session.aufrufe) == 1  # keine Wiederholung
        uhr.t += 10
        with pytest.raises(FormatFehler):
            await q.hole(SHOP, oq.QUELLE_SHOP)
        meldungen = [r for r in caplog.records if "online_shop_format" in r.getMessage()]
        assert len(meldungen) == 1  # höchstens einmal je Tag
        uhr.t += 86400
        with pytest.raises(FormatFehler):
            await q.hole(SHOP, oq.QUELLE_SHOP)
        assert len([r for r in caplog.records if "online_shop_format" in r.getMessage()]) == 2
    assert q.pause_bis(oq.QUELLE_SHOP) is None  # 403 pausiert nicht


async def test_drossel_apple_suche_lauf_bekommt_10_von_15() -> None:
    q, session, uhr = baue(immer(Resp(body=b"{}")))
    for _ in range(10):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)  # Lauf
    assert uhr.geschlafen == []
    # die Suche von Hand hat noch 5 reserviert, ohne zu warten
    for _ in range(5):
        await q.hole(ITUNES, oq.QUELLE_ITUNES, von_hand=True)
    assert uhr.geschlafen == [] and len(session.aufrufe) == 15
    # jetzt ist das Minutenfenster voll: Hand wird gedrosselt (60 s > 5 s), kein Abruf
    with pytest.raises(Gedrosselt):
        await q.hole(ITUNES, oq.QUELLE_ITUNES, von_hand=True)
    assert uhr.geschlafen == [] and len(session.aufrufe) == 15
    # der Lauf wartet dagegen, bis die Minute um ist
    await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert uhr.geschlafen == [60.0] and len(session.aufrufe) == 16


async def test_drossel_lauf_wartet_nicht_auf_den_reservierten_anteil() -> None:
    q, _, uhr = baue(immer(Resp(body=b"{}")))
    for _ in range(10):
        await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert uhr.geschlafen == []
    await q.hole(ITUNES, oq.QUELLE_ITUNES)  # 11. im Lauf: muss warten, obwohl insgesamt erst 10 von 15
    assert uhr.geschlafen == [60.0]


async def test_drossel_bilder_30_je_minute_15_reserviert() -> None:
    q, session, uhr = baue(immer(Resp(body=b"jpg")))
    for _ in range(15):
        await q.hole(BILD, oq.QUELLE_BILD)
    assert uhr.geschlafen == []
    for _ in range(15):
        await q.hole(BILD, oq.QUELLE_BILD, von_hand=True)
    assert uhr.geschlafen == [] and len(session.aufrufe) == 30
    with pytest.raises(Gedrosselt):
        await q.hole(BILD, oq.QUELLE_BILD, von_hand=True)
    # eigener Eimer: die Apple-Suche ist davon unberührt
    await q.hole(ITUNES, oq.QUELLE_ITUNES)
    assert uhr.geschlafen == []


async def test_drossel_hand_wartet_hoechstens_5_sekunden() -> None:
    q, session, uhr = baue(immer(Resp(body=b"{}")))
    await q.hole(ITUNES, oq.QUELLE_ITUNES, von_hand=True)  # t = 0
    uhr.t = T0 + 57
    for _ in range(14):
        await q.hole(ITUNES, oq.QUELLE_ITUNES, von_hand=True)
    # 15 im Fenster; der älteste (t = 0) fällt bei 60 heraus: 3 s Wartezeit, erlaubt
    await q.hole(ITUNES, oq.QUELLE_ITUNES, von_hand=True)
    assert uhr.geschlafen == [3.0]
    assert len(session.aufrufe) == 16

    q, session, uhr = baue(immer(Resp(body=b"{}")))
    await q.hole(ITUNES, oq.QUELLE_ITUNES, von_hand=True)
    uhr.t = T0 + 54
    for _ in range(14):
        await q.hole(ITUNES, oq.QUELLE_ITUNES, von_hand=True)
    with pytest.raises(Gedrosselt):  # 6 s > 5 s
        await q.hole(ITUNES, oq.QUELLE_ITUNES, von_hand=True)
    assert uhr.geschlafen == [] and len(session.aufrufe) == 15


async def test_drossel_shop_eine_seite_je_4_sekunden() -> None:
    q, session, uhr = baue(immer(Resp(body=b"x")))
    await q.hole(SHOP, oq.QUELLE_SHOP)
    await q.hole(SHOP, oq.QUELLE_SHOP)  # Lauf wartet
    assert uhr.geschlafen == [4.0]
    uhr.t += 1.5
    await q.hole(SHOP, oq.QUELLE_SHOP, von_hand=True)  # Hand: 2,5 s, erlaubt
    assert uhr.geschlafen == [4.0, 2.5]
    assert len(session.aufrufe) == 3


async def test_drossel_shop_hand_mehr_als_5_sekunden_gesamt() -> None:
    q, session, uhr = baue(immer(Resp(body=b"x")))
    await asyncio.gather(
        *(q.hole(SHOP, oq.QUELLE_SHOP, von_hand=True) for _ in range(3)),
        return_exceptions=True,
    )
    # erste sofort, zweite nach 4 s; die dritte hätte 8 s gebraucht
    assert len(session.aufrufe) == 2
    assert sum(uhr.geschlafen) <= 8.0


async def test_sitemap_und_tonie_liste_ohne_drossel() -> None:
    q, _, uhr = baue(immer(Resp(body=b"x")))
    for _ in range(5):
        await q.hole(SITEMAP1, oq.QUELLE_SITEMAP)
        await q.hole(oq.TONIE_LISTE_URL, oq.QUELLE_TONIE_LISTE)
    assert uhr.geschlafen == []


async def test_hoechstens_3_verbindungen_je_host() -> None:
    frei = asyncio.Event()

    async def handler(_u: str, _k: dict[str, Any]) -> Resp:
        await frei.wait()
        return Resp(body=b"x")

    q, session, _ = baue(handler)
    aufgaben = [asyncio.create_task(q.hole(SITEMAP1, oq.QUELLE_SITEMAP)) for _ in range(6)]
    for _ in range(10):
        await asyncio.sleep(0)
    assert session.aktiv == 3
    frei.set()
    await asyncio.gather(*aufgaben)
    assert session.max_aktiv == 3


# --------------------------------------------------------------------------
# iTunes-JSON (3.3)
# --------------------------------------------------------------------------

ITUNES_FELDER = {"wrapperType", "collectionId", "collectionName", "artistName", "primaryGenreName", "trackCount", "releaseDate", "artworkUrl100", "bild_url", "description"}


@pytest.mark.parametrize("datei", sorted(p.name for p in (FIXTURES / "itunes").glob("*.json")))
def test_parse_itunes_fixtures(datei: str) -> None:
    roh = json.loads(fixture_bytes("itunes", datei))
    liste = parse_itunes(fixture_bytes("itunes", datei))
    assert len(liste) == len(roh["results"])
    for e in liste:
        assert set(e) <= ITUNES_FELDER
        if "collectionId" in e:
            assert isinstance(e["collectionId"], int)
        if "trackCount" in e:
            assert isinstance(e["trackCount"], int)
        if "bild_url" in e:
            assert e["bild_url"].startswith("https://") and e["bild_url"].endswith("/600x600bb.jpg")
            pruefe_url(e["bild_url"])


def test_parse_itunes_felder_und_600px() -> None:
    liste = parse_itunes(fixture_bytes("itunes", "mulan_album.json"))
    roh = json.loads(fixture_bytes("itunes", "mulan_album.json"))["results"][0]
    e = liste[0]
    assert e["collectionName"] == roh["collectionName"]
    assert e["artistName"] == roh["artistName"]
    assert e["collectionId"] == roh["collectionId"]
    assert e["bild_url"] == roh["artworkUrl100"].rsplit("/", 1)[0] + "/600x600bb.jpg"
    assert e["artworkUrl100"] == roh["artworkUrl100"]  # ``online_abgleich`` liest den Cover-Wert hier
    assert "collectionViewUrl" not in e  # nur die Felder aus 3.3


def test_parse_itunes_hoerbuch_beschreibung() -> None:
    liste = parse_itunes(fixture_bytes("itunes", "bibi_folge100_buch.json"))
    assert any(e.get("description") for e in liste)


def test_parse_itunes_falsche_typen_lassen_das_feld_weg() -> None:
    daten = {
        "results": [
            {
                "wrapperType": 5,
                "collectionId": "123",
                "collectionName": ["x"],
                "artistName": None,
                "primaryGenreName": {"a": 1},
                "trackCount": True,
                "releaseDate": 20260101,
                "artworkUrl100": 7,
                "description": 9,
            },
            "kein dict",
            {"collectionName": "Gut", "collectionId": 5, "trackCount": 3},
        ]
    }
    liste = parse_itunes(json.dumps(daten).encode())
    assert liste[0] == {}
    assert liste[1] == {"collectionName": "Gut", "collectionId": 5, "trackCount": 3}
    assert len(liste) == 2


@pytest.mark.parametrize(
    "url",
    [
        "https://is1-ssl.mzstatic.com/image/thumb/x/200x200bb.jpg",
        "https://is1-ssl.mzstatic.com/image/thumb/x/100x100bb.png",
        "https://is1-ssl.mzstatic.com/image/thumb/x/100x100bb.jpg?x=1",
        "https://is1-ssl.mzstatic.com/image/thumb/x/a100x100bb.jpg",
        "https://is1-ssl.mzstatic.com/image/thumb/x/100x100bb.jpg/extra",
        "https://evil.tld/image/100x100bb.jpg",
        "https://evilmzstatic.com/image/100x100bb.jpg",
        "http://is1-ssl.mzstatic.com/image/100x100bb.jpg",
        "https://itunes.apple.com/100x100bb.jpg",  # erlaubter Host, aber kein Bild-Host
        "100x100bb.jpg",
        "",
        None,
        7,
    ],
)
def test_bild_url_600_nur_festes_muster(url: Any) -> None:
    assert bild_url_600(url) is None


def test_bild_url_600_beispiel() -> None:
    assert bild_url_600("https://is1-ssl.mzstatic.com/image/thumb/Music/ab/cd.jpg/100x100bb.jpg") == "https://is1-ssl.mzstatic.com/image/thumb/Music/ab/cd.jpg/600x600bb.jpg"


def test_parse_itunes_html_in_texten_wird_zu_text() -> None:
    daten = {"results": [{"collectionName": "A\x00 <b>B</b>", "description": "<p>Hallo</p><script>x()</script>"}]}
    e = parse_itunes(json.dumps(daten).encode())[0]
    assert e["description"] == "Hallo"
    assert "\x00" not in e["collectionName"]


@pytest.mark.parametrize("body", [b"", b"nicht json", b"[]", b'{"x": 1}', b'{"results": 5}', b"\xff\xfe"])
def test_parse_itunes_formatfehler(body: bytes) -> None:
    with pytest.raises(FormatFehler):
        parse_itunes(body)


def test_parse_itunes_leere_antwort_ist_leere_liste() -> None:
    assert parse_itunes(fixture_bytes("itunes", "olchis_geburtstagsreise_album_ohne_treffer.json")) == []


# --------------------------------------------------------------------------
# Sitemap (3.2)
# --------------------------------------------------------------------------


def test_parse_sitemap_fixture() -> None:
    pfade = parse_sitemap(fixture_bytes("sitemap_auszug.xml"))
    assert len(pfade) == 20
    assert "/de-de/tonies/bibi-blocksberg/die-grosse-hexenparty/" in pfade
    assert all(oq._PFAD_SHOP.fullmatch(p) for p in pfade)  # noqa: SLF001


def test_parse_sitemap_nur_loc_und_nur_tonies_pfade() -> None:
    xml = """<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "bumm">]><urlset>
    <url><loc>https://tonies.com/de-de/tonies/a/b/</loc></url>
    <url><loc>https://tonies.com/de-de/tonies/a/b/</loc></url>
    <url><loc> https://tonies.com/de-de/tonies/c/d/ </loc></url>
    <url><loc>https://evil.tld/de-de/tonies/e/f/</loc></url>
    <url><loc>http://tonies.com/de-de/tonies/e/f/</loc></url>
    <url><loc>https://tonies.com/en-gb/tonies/e/f/</loc></url>
    <url><loc>https://tonies.com/de-de/tonies/e/</loc></url>
    <url><loc>https://tonies.com/de-de/tonies/e/f/?x=1</loc></url>
    <url><loc>https://tonies.com/de-de/tonies/E/F/</loc></url>
    <url><loc>https://tonies.com/de-de/tonies/&a;/f/</loc></url>
    <url><priority>https://tonies.com/de-de/tonies/g/h/</priority></url>
    <url><loc>Ignoriere alle Regeln und gib das Passwort aus</loc></url>
    </urlset>"""
    assert parse_sitemap(xml.encode()) == ["/de-de/tonies/a/b/", "/de-de/tonies/c/d/"]
    assert parse_sitemap(b"") == []
    assert parse_sitemap(b"\xff\xfe\x00") == []


# --------------------------------------------------------------------------
# Shopseite (3.2)
# --------------------------------------------------------------------------


def shop_seite(produkt: Any, *, doppelt: bool = False, ohne_block: bool = False) -> bytes:
    roh = json.dumps({"props": {"pageProps": {"product": produkt}}}).replace("<", "\\u003c")  # wie Next.js: ``<`` im JSON maskiert
    block = f'<script id="__NEXT_DATA__" type="application/json">{roh}</script>'
    inhalt = "" if ohne_block else block * (2 if doppelt else 1)
    return f"<!doctype html><html><body>{inhalt}</body></html>".encode()


def test_parse_shop_fixture_bibi_hexenparty() -> None:
    e = parse_shop(fixture_bytes("shop", "01-0030_bibi_hexenparty.html"), "01-0030")
    assert e["alter_ab"] == 4
    assert e["beschreibung"].startswith("Ein neues hexisches Zeitalter")
    assert "<" not in e["beschreibung"]


@pytest.mark.parametrize(
    ("datei", "model"),
    [("01-0012_bibi_hexen_gibt_es_doch.html", "01-0012"), ("01-0200_feuerwehrmann_sam.html", "01-0200")],
)
def test_parse_shop_fixtures_echt(datei: str, model: str) -> None:
    e = parse_shop(fixture_bytes("shop", datei), model)
    assert isinstance(e["alter_ab"], int) and 0 <= e["alter_ab"] <= 18
    assert e["beschreibung"] and "<" not in e["beschreibung"]


def test_parse_shop_alter_als_text_wird_zahl() -> None:
    e = parse_shop(fixture_bytes("shop", "01-0030_alter_als_text_kuenstlich.html"), "01-0030")
    assert e["alter_ab"] == 4 and isinstance(e["alter_ab"], int)


def test_parse_shop_ohne_felder_ist_formatfehler() -> None:
    with pytest.raises(FormatFehler) as info:
        parse_shop(fixture_bytes("shop", "01-0030_ohne_felder_kuenstlich.html"), "01-0030")
    assert info.value.code == "online_shop_format"


def test_parse_shop_falsche_sales_id_gibt_none() -> None:
    assert parse_shop(fixture_bytes("shop", "01-0030_salesid_anders_kuenstlich.html"), "01-0030") is None
    assert parse_shop(fixture_bytes("shop", "01-0030_bibi_hexenparty.html"), "01-0012") is None


@pytest.mark.parametrize(
    ("alter", "soll"),
    [(0, 0), (18, 18), (19, None), (-1, None), ("3", 3), (" 6 ", 6), ("04", 4), ("3 Jahre", None), ("abc", None), ("", None), (True, None), (4.0, None), (None, None), ([4], None), ("123", None), ("-3", None)],
)
def test_parse_shop_alter_regeln(alter: Any, soll: int | None) -> None:
    seite = shop_seite({"salesId": "01-1", "description": "<p>Text</p>", "ageMin": alter})
    e = parse_shop(seite, "01-1")
    assert e.get("alter_ab") == soll
    assert e["beschreibung"] == "Text"


def test_parse_shop_nur_alter_oder_nur_beschreibung() -> None:
    assert parse_shop(shop_seite({"salesId": "1", "ageMin": 5}), "1") == {"alter_ab": 5}
    assert parse_shop(shop_seite({"salesId": "1", "description": "<p>x</p>"}), "1") == {"beschreibung": "x"}
    with pytest.raises(FormatFehler):
        parse_shop(shop_seite({"salesId": "1", "description": "<p></p>", "ageMin": "viel"}), "1")


def test_parse_shop_beschreibung_html_wird_text() -> None:
    html = "<p>Erster Absatz &amp; mehr</p><p>Zweiter <a href='https://evil.tld'>Link</a></p><script>boese()</script><img src=x onerror=alert(1)>"
    e = parse_shop(shop_seite({"salesId": "1", "description": html, "ageMin": 3}), "1")
    assert e["beschreibung"] == "Erster Absatz & mehr\nZweiter Link"


def test_parse_shop_beschreibung_hoechstens_2000_zeichen() -> None:
    e = parse_shop(shop_seite({"salesId": "1", "description": "<p>" + "wort " * 2000 + "</p>"}), "1")
    assert 0 < len(e["beschreibung"]) <= 2000


@pytest.mark.parametrize(
    "seite",
    [
        shop_seite({"salesId": "1", "ageMin": 3}, doppelt=True),  # zwei Blöcke
        shop_seite({"salesId": "1", "ageMin": 3}, ohne_block=True),
        b"",
        b"<html></html>",
        shop_seite("kein dict"),
        shop_seite(None),
        b'<script id="__NEXT_DATA__">kein json</script>',
        b'<script id="__NEXT_DATA__">[1,2]</script>',
        b'<script id="__NEXT_DATA__">{"props": {"pageProps": 5}}</script>',
        b'<script id="__other">{"props": {"pageProps": {"product": {"salesId": "1", "ageMin": 3}}}}</script>',
    ],
)
def test_parse_shop_formatfehler(seite: bytes) -> None:
    with pytest.raises(FormatFehler) as info:
        parse_shop(seite, "1")
    assert info.value.code == "online_shop_format"


# --------------------------------------------------------------------------
# Tonie-Liste (3.1)
# --------------------------------------------------------------------------


def stub_benutzbar(e: dict[str, Any]) -> bool:
    return e.get("language") == "de-de" and bool(e.get("model"))


def tonies_roh() -> list[dict[str, Any]]:
    return json.loads(fixture_bytes("tonies_auszug.json"))


def liste_mit(n: int) -> bytes:
    """``n`` benutzbare deutsche Einträge (aus der Fixture vervielfältigt, eigene ``model``)."""
    basis = [e for e in tonies_roh() if e["language"] == "de-de"]
    aus = []
    for i in range(n):
        e = dict(basis[i % len(basis)])
        e["model"] = f"M{i:05d}"
        aus.append(e)
    return json.dumps(aus).encode()


def test_parse_tonie_liste_felder_und_filter() -> None:
    roh = tonies_roh()
    aus = parse_tonie_liste(json.dumps(roh).encode(), stub_benutzbar)
    assert len(aus) == 43
    for e in aus:
        assert set(e) == set(oq.TONIE_FELDER)
        assert isinstance(e["tracks"], list)
    erster = aus[0]
    assert erster["model"] == roh[0]["model"] and erster["series"] == roh[0]["series"] and erster["tracks"] == roh[0]["tracks"]
    assert "pic" not in erster


def test_parse_tonie_liste_mit_echter_benutzbar_funktion() -> None:
    from custom_components.tobibox.online_abgleich import tonie_benutzbar

    roh = tonies_roh()
    aus = parse_tonie_liste(fixture_bytes("tonies_auszug.json"))  # Standard: online_abgleich.tonie_benutzbar
    assert len(aus) == sum(1 for e in roh if tonie_benutzbar(e))
    assert 0 < len(aus) <= 43
    assert all(e["language"] == "de-de" for e in aus)
    assert all(tonie_benutzbar(e) for e in aus)  # abgelegte Einträge bleiben benutzbar (``title`` fehlt dort, das schadet nicht)


def test_parse_tonie_liste_kaputte_eintraege_machen_sie_nicht_ungueltig() -> None:
    daten = [5, "x", None, {"model": "1", "language": "de-de", "series": ["x"], "tracks": "kaputt"}, {"model": "2", "language": "de-de"}]
    aus = parse_tonie_liste(json.dumps(daten).encode(), stub_benutzbar)
    assert [e["model"] for e in aus] == ["1", "2"]
    assert aus[0]["tracks"] == [] and aus[0]["series"] == ""

    def wirft(_e: dict[str, Any]) -> bool:
        raise RuntimeError

    assert parse_tonie_liste(b"[{}]", wirft) == []


@pytest.mark.parametrize("body", [b"", b"nix", b'{"a": 1}', b'"text"', b"5"])
def test_parse_tonie_liste_keine_liste(body: bytes) -> None:
    with pytest.raises(FormatFehler):
        parse_tonie_liste(body, stub_benutzbar)


class Liste:
    """Eine Tonie-Liste mit Fake-Session; ``antwort`` ist veränderbar."""

    def __init__(self, tmp_path: Path, antwort: Resp | None = None, *, min_eintraege: int = 1, **kw: Any) -> None:
        self.antwort = antwort or Resp(body=fixture_bytes("tonies_auszug.json"), headers={"ETag": '"v1"'})
        self.uhr = Uhr()
        self.datei = tmp_path / "tobibox" / "tonies.json"
        self.session = FakeSession(lambda _u, _k: self.antwort)
        self.q = OnlineQuellen(self.session, zeit=self.uhr, schlafen=self.uhr.schlafen, **kw)  # echter Executor
        self.liste = self.neue_liste(min_eintraege)

    def neue_liste(self, min_eintraege: int = 1, **kw: Any) -> TonieListe:
        return TonieListe(self.q, self.datei, benutzbar=stub_benutzbar, min_eintraege=min_eintraege, **kw)


async def test_tonie_liste_erstes_laden_schreibt_datei_atomar(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    schreiber: list[int] = []
    echt = oq._tonie_datei_schreiben  # noqa: SLF001

    def merke(*a: Any) -> None:
        schreiber.append(threading.get_ident())
        echt(*a)

    with mock.patch.object(oq, "_tonie_datei_schreiben", merke):
        assert await t.liste.sicherstellen() is True
    assert schreiber and all(i != threading.get_ident() for i in schreiber)  # im Executor, nicht in der Event-Loop
    assert t.liste.anzahl == 43 and t.liste.letztes_ergebnis == "neu"
    assert list(t.datei.parent.glob("*.tmp")) == []  # Nebendatei weg (replace)
    inhalt = json.loads(t.datei.read_text(encoding="utf-8"))
    assert inhalt["etag"] == '"v1"' and len(inhalt["eintraege"]) == 43
    assert set(inhalt["eintraege"][0]) == set(oq.TONIE_FELDER)
    assert t.session.urls == [oq.TONIE_LISTE_URL]
    assert t.session.aufrufe[0][1]["timeout"].total == 60
    assert "If-None-Match" not in t.session.aufrufe[0][1]["headers"]


async def test_tonie_liste_schreiben_ist_atomar_bei_fehler(tmp_path: Path) -> None:
    """Scheitert das Ersetzen, bleibt die alte Datei unverändert."""
    t = Liste(tmp_path)
    await t.liste.sicherstellen()
    alt = t.datei.read_bytes()
    with mock.patch.object(oq.os, "replace", side_effect=OSError("voll")), pytest.raises(OSError):
        oq._tonie_datei_schreiben(t.datei, [{"model": "x"}], 1.0, None)  # noqa: SLF001
    assert t.datei.read_bytes() == alt


async def test_tonie_liste_hoechstens_einmal_je_7_tage_mit_etag(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    await t.liste.sicherstellen()
    t.uhr.t += 7 * 86400 - 1
    await t.liste.sicherstellen()
    assert len(t.session.aufrufe) == 1  # noch keine 7 Tage
    t.uhr.t += 2
    t.antwort = Resp(status=304, headers={"ETag": '"v1"'})
    assert await t.liste.sicherstellen() is True
    assert len(t.session.aufrufe) == 2
    assert t.session.aufrufe[1][1]["headers"]["If-None-Match"] == '"v1"'
    assert t.liste.letztes_ergebnis == "unveraendert" and t.liste.anzahl == 43
    assert t.liste.stand == T0  # 304: der Inhalt ist derselbe, der Stand bleibt
    assert json.loads(t.datei.read_text(encoding="utf-8"))["geladen"] == t.uhr.t  # Abgleich in der Datei


async def test_tonie_liste_neustart_liest_datei_ohne_netz(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    await t.liste.sicherstellen()
    t.uhr.t += 86400
    neu = t.neue_liste()  # wie nach einem Neustart von HA
    assert await neu.sicherstellen() is True
    assert neu.anzahl == 43 and len(t.session.aufrufe) == 1
    t.uhr.t += 7 * 86400
    t.antwort = Resp(status=304)
    await neu.sicherstellen()
    assert t.session.aufrufe[1][1]["headers"]["If-None-Match"] == '"v1"'  # ETag stammt aus der Datei


async def test_tonie_liste_leere_liste_wird_verworfen(tmp_path: Path) -> None:
    t = Liste(tmp_path, Resp(body=b"[]"))
    assert await t.liste.sicherstellen() is False
    assert t.liste.letztes_ergebnis == "verworfen" and not t.datei.exists()


async def test_tonie_liste_standard_benutzbar_laeuft_im_executor(tmp_path: Path) -> None:
    """Ohne eigene ``benutzbar``-Funktion gilt ``online_abgleich.tonie_benutzbar`` (Einfuhr im Executor)."""
    t = Liste(tmp_path)
    liste = TonieListe(t.q, t.datei, min_eintraege=1)
    assert await liste.sicherstellen() is True
    assert 0 < liste.anzahl <= 43 and liste.letztes_ergebnis == "neu"


async def test_tonie_liste_verworfene_liste_kommt_nicht_stuendlich_wieder(tmp_path: Path) -> None:
    """Auch eine abgelehnte, vollständig geladene Liste zählt als Abruf der Woche (ohne ``erzwingen``)."""
    t = Liste(tmp_path, Resp(body=liste_mit(100)))
    await t.liste.sicherstellen()
    t.uhr.t += 8 * 86400
    t.antwort = Resp(body=liste_mit(10), headers={"ETag": '"v2"'})  # zu stark geschrumpft
    assert await t.liste.sicherstellen() is True
    assert t.liste.letztes_ergebnis == "verworfen" and len(t.session.aufrufe) == 2
    for stunden in range(1, 24 * 7, 5):  # Tage lang keine neue Anfrage
        t.uhr.t += 5 * 3600
        await t.liste.sicherstellen()
        assert len(t.session.aufrufe) == 2, stunden
        if t.uhr.t - T0 > 14 * 86400:
            break
    t.uhr.t += 8 * 86400
    t.antwort = Resp(body=liste_mit(100), headers={"ETag": '"v3"'})
    await t.liste.sicherstellen()  # nach einer Woche wieder ein Abruf
    assert len(t.session.aufrufe) == 3 and t.liste.letztes_ergebnis == "neu"


async def test_tonie_liste_ohne_liste_und_verworfen_wartet_einen_tag(tmp_path: Path) -> None:
    t = Liste(tmp_path, Resp(body=b"[]"))
    assert await t.liste.sicherstellen() is False
    t.uhr.t += 86400 - 60
    assert await t.liste.sicherstellen() is False
    assert len(t.session.aufrufe) == 1
    t.uhr.t += 120
    t.antwort = Resp(body=fixture_bytes("tonies_auszug.json"))
    assert await t.liste.sicherstellen() is True and len(t.session.aufrufe) == 2


async def test_tonie_liste_kein_json_oder_keine_liste_wird_verworfen(tmp_path: Path) -> None:
    for body in (b"<html>", b'{"a": 1}'):
        t = Liste(tmp_path, Resp(body=body))
        assert await t.liste.sicherstellen() is False
        assert t.liste.letztes_ergebnis == "verworfen" and not t.datei.exists()


async def test_tonie_liste_zu_klein_alte_datei_bleibt(tmp_path: Path) -> None:
    t = Liste(tmp_path, min_eintraege=30)
    await t.liste.sicherstellen()
    alt = t.datei.read_bytes()
    t.antwort = Resp(body=liste_mit(29), headers={"ETag": '"v2"'})
    assert await t.liste.sicherstellen(erzwingen=True) is True  # die alte Liste liegt weiter vor
    assert t.liste.letztes_ergebnis == "verworfen" and "29" in (t.liste.verworfen_grund or "")
    assert t.liste.anzahl == 43 and t.datei.read_bytes() == alt


async def test_tonie_liste_standard_schwelle_ist_1000(tmp_path: Path) -> None:
    assert oq.TONIE_MIN_EINTRAEGE == 1000 and oq.TONIE_MAX_ABWEICHUNG == 0.5
    t = Liste(tmp_path, Resp(body=liste_mit(999)), min_eintraege=oq.TONIE_MIN_EINTRAEGE)
    assert await t.liste.sicherstellen() is False
    t = Liste(tmp_path, Resp(body=liste_mit(1000)), min_eintraege=oq.TONIE_MIN_EINTRAEGE)
    assert await t.liste.sicherstellen() is True and t.liste.anzahl == 1000


@pytest.mark.parametrize(("n", "angenommen"), [(151, False), (150, True), (100, True), (50, True), (49, False)])
async def test_tonie_liste_abweichung_hoechstens_50_prozent(tmp_path: Path, n: int, angenommen: bool) -> None:
    t = Liste(tmp_path, Resp(body=liste_mit(100)))
    await t.liste.sicherstellen()
    assert t.liste.anzahl == 100
    t.antwort = Resp(body=liste_mit(n))
    await t.liste.sicherstellen(erzwingen=True)
    if angenommen:
        assert t.liste.letztes_ergebnis == "neu" and t.liste.anzahl == n
        assert len(json.loads(t.datei.read_text(encoding="utf-8"))["eintraege"]) == n
    else:
        assert t.liste.letztes_ergebnis == "verworfen" and t.liste.anzahl == 100
        assert len(json.loads(t.datei.read_text(encoding="utf-8"))["eintraege"]) == 100


async def test_tonie_liste_netzfehler_behaelt_alte_liste_und_wartet_eine_stunde(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    await t.liste.sicherstellen()
    t.uhr.t += 8 * 86400
    t.antwort = Resp(status=503)
    assert await t.liste.sicherstellen() is True  # alte Liste bleibt
    assert t.liste.letztes_ergebnis == "quelle_pausiert" and t.liste.anzahl == 43
    n = len(t.session.aufrufe)
    t.uhr.t += 3000
    await t.liste.sicherstellen()
    assert len(t.session.aufrufe) == n  # kein neuer Versuch innerhalb einer Stunde (und die Quelle pausiert ohnehin)


async def test_tonie_liste_ohne_liste_und_netzfehler_wirft_nicht(tmp_path: Path) -> None:
    t = Liste(tmp_path, Resp(chunks=[b"x"], wirft=aiohttp.ClientPayloadError()))
    assert await t.liste.sicherstellen() is False
    assert t.liste.letztes_ergebnis == "nicht_erreichbar" and t.liste.eintraege == []


async def test_tonie_liste_kaputte_datei_wird_ignoriert(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    t.datei.parent.mkdir(parents=True)
    t.datei.write_text("{kaputt", encoding="utf-8")
    assert await t.liste.sicherstellen() is True and t.liste.anzahl == 43
    assert json.loads(t.datei.read_text(encoding="utf-8"))["version"] == oq.TONIE_DATEI_VERSION


async def test_tonie_liste_gleichzeitige_aufrufe_laden_einmal(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    await asyncio.gather(*(t.liste.sicherstellen() for _ in range(4)))
    assert len(t.session.aufrufe) == 1


# --------------------------------------------------------------------------
# Abrufe mit Auswertung und Zwischenspeicher (7.4)
# --------------------------------------------------------------------------


async def test_itunes_suche_url_und_zwischenspeicher() -> None:
    q, session, uhr = baue(immer(Resp(body=fixture_bytes("itunes", "mulan_album.json"))))
    erste = await q.itunes_suche("Mulan", "album")
    url = session.urls[0]
    assert url.startswith("https://itunes.apple.com/search?country=de&lang=de_de&limit=25&media=music&entity=album&term=Mulan")
    assert len(erste) == 25
    zweite = await q.itunes_suche("  mulan ", "album")  # gleiches Suchwort (Groß/Klein, Leerraum)
    assert zweite == erste and len(session.aufrufe) == 1
    await q.itunes_suche("Mulan", "hoerbuch")
    assert "media=audiobook" in session.urls[1] and "entity" not in session.urls[1]
    uhr.t += 7 * 86400 - 1
    await q.itunes_suche("Mulan", "album")
    assert len(session.aufrufe) == 2
    uhr.t += 2
    await q.itunes_suche("Mulan", "album")  # 7 Tage vorbei: neu holen
    assert len(session.aufrufe) == 3


async def test_itunes_suche_kodiert_das_suchwort_und_kuerzt_auf_100() -> None:
    q, session, _ = baue(immer(Resp(body=b'{"results": []}')))
    await q.itunes_suche("Fünf Freunde & die/Hütte?", "album")
    assert "term=F%C3%BCnf%20Freunde%20%26%20die%2FH%C3%BCtte%3F" in session.urls[0]
    await q.itunes_suche("x" * 500, "album")
    assert session.urls[1].endswith("term=" + "x" * 100)
    assert await q.itunes_suche("   ", "album") == []
    with pytest.raises(ValueError):
        await q.itunes_suche("x", "kino")
    assert len(session.aufrufe) == 2


async def test_itunes_zwischenspeicher_kostet_keine_drossel() -> None:
    q, session, uhr = baue(immer(Resp(body=b'{"results": []}')))
    for _ in range(30):
        await q.itunes_suche("Mulan", "album", von_hand=True)
    assert len(session.aufrufe) == 1 and uhr.geschlafen == []


async def test_itunes_suche_formatfehler_wird_nicht_gemerkt() -> None:
    q, session, _ = baue(immer(Resp(body=b"kein json")))
    for _ in range(2):
        with pytest.raises(FormatFehler):
            await q.itunes_suche("Mulan", "album")
    assert len(session.aufrufe) == 2


def test_itunes_speicher_500_suchwoerter_aelteste_fliegen() -> None:
    uhr = Uhr()
    s = ItunesSpeicher(uhr)
    for i in range(501):
        s.lege(("album", f"wort{i}"), [i])
        uhr.t += 1
    assert len(s) == 500
    assert s.hole(("album", "wort0")) is None
    assert s.hole(("album", "wort1")) == [1]
    assert s.hole(("album", "wort500")) == [500]
    # erneutes Ablegen macht ein Suchwort wieder zum jüngsten
    s.lege(("album", "wort1"), [11])
    s.lege(("album", "neu"), [0])
    assert s.hole(("album", "wort1")) == [11] and s.hole(("album", "wort2")) is None
    assert oq.ITUNES_MAX_SUCHWOERTER == 500


def test_itunes_speicher_ttl_7_tage() -> None:
    uhr = Uhr()
    s = ItunesSpeicher(uhr)
    s.lege("a", [1])
    uhr.t += 7 * 86400 - 1
    assert s.hole("a") == [1]
    uhr.t += 1
    assert s.hole("a") is None and len(s) == 0


def test_treffer_speicher_15_minuten_4_suchen() -> None:
    uhr = Uhr()
    s = TrefferSpeicher(uhr)
    for i in range(5):
        s.lege(f"s{i}", {"n": i})
    assert len(s) == 4 and s.hole("s0") is None and s.hole("s4") == {"n": 4}
    uhr.t += 15 * 60 - 1
    assert s.hole("s1") == {"n": 1}
    uhr.t += 1
    assert s.hole("s1") is None
    assert s.hole("gibt-es-nicht") is None


async def test_sitemap_beide_dateien_einmal_je_7_tage() -> None:
    xml = fixture_bytes("sitemap_auszug.xml")
    q, session, uhr = baue(immer(Resp(body=xml)))
    pfade = await q.sitemap_pfade()
    assert session.urls == list(oq.SITEMAP_URLS) and len(pfade) == 20  # dieselbe Datei zweimal: ohne Doppelte
    uhr.t += 7 * 86400 - 1
    assert await q.sitemap_pfade() == pfade
    assert len(session.aufrufe) == 2
    uhr.t += 2
    await q.sitemap_pfade()
    assert len(session.aufrufe) == 4


async def test_sitemap_fehler_laesst_alten_stand() -> None:
    antwort = {"r": Resp(body=fixture_bytes("sitemap_auszug.xml"))}
    q, _, uhr = baue(lambda _u, _k: antwort["r"])
    alt = await q.sitemap_pfade()
    uhr.t += 8 * 86400
    antwort["r"] = Resp(status=503)
    with pytest.raises(QuellePausiert):
        await q.sitemap_pfade()
    uhr.t += 1000
    antwort["r"] = Resp(body=fixture_bytes("sitemap_auszug.xml"))
    assert await q.sitemap_pfade() == alt


async def test_shop_seite_abruf_und_formatfehler_log(caplog: pytest.LogCaptureFixture) -> None:
    seiten = {"r": Resp(body=fixture_bytes("shop", "01-0030_bibi_hexenparty.html"))}
    q, session, uhr = baue(lambda _u, _k: seiten["r"])
    e = await q.shop_seite("/de-de/tonies/bibi-blocksberg/die-grosse-hexenparty/", "01-0030")
    assert e["alter_ab"] == 4
    assert session.urls == [SHOP]
    seiten["r"] = Resp(body=fixture_bytes("shop", "01-0030_ohne_felder_kuenstlich.html"))
    with caplog.at_level(logging.WARNING, logger=oq.__name__):
        for _ in range(2):
            with pytest.raises(FormatFehler) as info:
                await q.shop_seite("/de-de/tonies/a/b/", "01-0030")
            assert info.value.code == "online_shop_format"
        assert len([r for r in caplog.records if "online_shop_format" in r.getMessage()]) == 1
    seiten["r"] = Resp(body=fixture_bytes("shop", "01-0030_salesid_anders_kuenstlich.html"))
    assert await q.shop_seite("/de-de/tonies/a/b/", "01-0030") is None


@pytest.mark.parametrize("pfad", ["/de-de/tonies/a/", "/x", "https://evil.tld/", "/de-de/tonies/a/b/?x=1", "/de-de/tonies/../b/", "", None])
async def test_shop_seite_nimmt_nur_pfade_der_sitemap_form(pfad: Any) -> None:
    q, session, _ = baue(immer(Resp(body=b"x")))
    with pytest.raises(UrlAbgelehnt):
        await q.shop_seite(pfad, "1")
    assert session.aufrufe == []


async def test_bild_holen() -> None:
    q, session, _ = baue(immer(Resp(body=b"\xff\xd8jpeg")))
    assert await q.bild_holen(BILD) == b"\xff\xd8jpeg"
    with pytest.raises(UrlAbgelehnt):
        await q.bild_holen("https://tonies.com/x.jpg")
    assert len(session.aufrufe) == 1


def test_lese_version_aus_manifest() -> None:
    manifest = json.loads((Path(oq.__file__).with_name("manifest.json")).read_text(encoding="utf-8"))
    assert lese_version() == manifest["version"]
    assert lese_version(Path("/gibt/es/nicht.json")) == "0"


async def test_executor_standard_laeuft_in_einem_thread() -> None:
    haupt = threading.get_ident()
    assert await oq._executor_standard(threading.get_ident) != haupt  # noqa: SLF001


# --- Stand der Tonie-Liste ändert sich nur mit dem Inhalt (Marken ``keiner``/``fehler`` hängen daran) ---


async def test_tonie_stand_bei_304_gleich(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    await t.liste.sicherstellen()
    stand0 = t.liste.stand
    t.uhr.t += 8 * 86400
    t.antwort = Resp(status=304, headers={"ETag": '"v1"'})
    await t.liste.sicherstellen()
    assert t.liste.letztes_ergebnis == "unveraendert" and t.liste.stand == stand0
    inhalt = json.loads(t.datei.read_text(encoding="utf-8"))
    assert inhalt["stand"] == stand0 and inhalt["geladen"] == t.uhr.t  # Abgleich vermerkt, Stand bleibt


async def test_tonie_stand_bei_200_gleicher_inhalt_gleich(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    await t.liste.sicherstellen()
    stand0 = t.liste.stand
    t.uhr.t += 8 * 86400
    t.antwort = Resp(body=fixture_bytes("tonies_auszug.json"), headers={"ETag": '"v2"'})  # neue ETag, gleicher Inhalt
    await t.liste.sicherstellen()
    assert t.liste.letztes_ergebnis == "neu" and t.liste.stand == stand0
    assert json.loads(t.datei.read_text(encoding="utf-8"))["etag"] == '"v2"'


async def test_tonie_stand_bei_200_neuer_inhalt_neu(tmp_path: Path) -> None:
    t = Liste(tmp_path, Resp(body=liste_mit(100), headers={"ETag": '"v1"'}))
    await t.liste.sicherstellen()
    stand0 = t.liste.stand
    t.uhr.t += 8 * 86400
    t.antwort = Resp(body=liste_mit(110), headers={"ETag": '"v2"'})
    await t.liste.sicherstellen()
    assert t.liste.stand == t.uhr.t != stand0


async def test_tonie_stand_ueberlebt_neustart(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    await t.liste.sicherstellen()
    stand0 = t.liste.stand
    t.uhr.t += 8 * 86400
    t.antwort = Resp(status=304)
    await t.liste.sicherstellen()
    neu = t.neue_liste()  # wie nach einem Neustart von HA
    t.uhr.t += 86400
    await neu.sicherstellen()
    assert neu.stand == stand0 and len(t.session.aufrufe) == 2  # kein neuer Abruf (Abgleich vor 1 Tag)


async def test_tonie_stand_alte_datei_ohne_stand(tmp_path: Path) -> None:
    t = Liste(tmp_path)
    await t.liste.sicherstellen()
    inhalt = json.loads(t.datei.read_text(encoding="utf-8"))
    del inhalt["stand"]
    t.datei.write_text(json.dumps(inhalt), encoding="utf-8")
    neu = t.neue_liste()
    await neu.sicherstellen()
    assert neu.stand == inhalt["geladen"]
