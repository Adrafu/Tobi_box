"""Online-Suche, Paket OS2: Abrufe im Netz, Drossel, Auswertung und Zwischenspeicher (Design ``online-suche.md``, 3.1 bis 3.3, 7.4, 8).

* ``OnlineQuellen.hole(url, quelle)`` ist die **eine** Funktion für alle Abrufe (8.1): nur ``https``, nur vier Hosts, keine
  automatischen Weiterleitungen, Größe auf **entpackte** Bytes gezählt, Zeitgrenzen, Drossel (8.2), Pause nach 429/5xx.
* Die Auswertung (JSON, HTML, XML) steckt in reinen Funktionen (``parse_*``) und läuft im Executor. Kein HTML aus fremden
  Quellen erreicht die Ausgabe.
* ``TonieListe``: die Tonie-Liste der Gemeinschaft (3.1) als Datei ``<config>/tobibox/tonies.json``.
* Zwischenspeicher (7.4): ``ItunesSpeicher``, die Sitemap in ``OnlineQuellen``, ``TrefferSpeicher``. Alles darf verloren gehen.

Das Modul kennt weder den Store noch den Dienst ``online.py`` (OS3). Die Uhr und das Schlafen werden eingespeist, damit die Tests
weder Netz noch echte Wartezeit brauchen.

Nummern: Bei den Größen steht „MB“ für 1 000 000 Byte, „MiB“ für 1 048 576 Byte.
"""

from __future__ import annotations

import asyncio
import collections
import ipaddress
import json
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Final
from urllib.parse import quote, urljoin, urlsplit

import aiohttp
from yarl import URL

from .namen import nfc, ohne_steuerzeichen

_LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Konstanten
# --------------------------------------------------------------------------

#: Quellen für ``hole`` (bestimmen Größengrenze, Zeitgrenze, Drossel und Pause)
QUELLE_ITUNES: Final = "itunes"
QUELLE_BILD: Final = "bild"
QUELLE_SHOP: Final = "shop"
QUELLE_SITEMAP: Final = "sitemap"
QUELLE_TONIE_LISTE: Final = "tonie_liste"

TONIE_LISTE_URL: Final = "https://raw.githubusercontent.com/toniebox-reverse-engineering/tonies-json/release/tonies.json"
SITEMAP_URLS: Final = (
    "https://tonies.com/sitemap_products_1.xml",
    "https://tonies.com/sitemap_products_2.xml",
)
ITUNES_URL: Final = "https://itunes.apple.com/search"
SHOP_BASIS: Final = "https://tonies.com"

HOST_ITUNES: Final = "itunes.apple.com"
HOST_GITHUB: Final = "raw.githubusercontent.com"
HOST_TONIES: Final = "tonies.com"
ENDUNG_BILD: Final = ".mzstatic.com"
ERLAUBTE_HOSTS: Final = (HOST_ITUNES, HOST_GITHUB, HOST_TONIES)

MB: Final = 1_000_000
MIB: Final = 1024 * 1024
MAX_BYTES: Final = {
    QUELLE_ITUNES: 1 * MB,
    QUELLE_BILD: 5 * MB,
    QUELLE_SHOP: 2 * MB,
    QUELLE_SITEMAP: 5 * MIB,
    QUELLE_TONIE_LISTE: 20 * MB,
}
ZEITGRENZE_S: Final = {
    QUELLE_ITUNES: 10,
    QUELLE_BILD: 10,
    QUELLE_SHOP: 10,
    QUELLE_SITEMAP: 10,
    QUELLE_TONIE_LISTE: 60,
}
MAX_SPRUENGE: Final = 3
BLOCK_BYTES: Final = 64 * 1024
MAX_URL_LAENGE: Final = 2048
MAX_VERBINDUNGEN_JE_HOST: Final = 3

#: Drossel (8.2)
ITUNES_JE_MINUTE: Final = 15
ITUNES_RESERVE_HAND: Final = 5
BILD_JE_MINUTE: Final = 30
BILD_RESERVE_HAND: Final = 15
SHOP_ABSTAND_S: Final = 4.0
FENSTER_S: Final = 60.0
HAND_WARTEN_MAX_S: Final = 5.0
PAUSE_S: Final = 15 * 60

#: Tonie-Liste (3.1). Die Schwellen sind Konstanten, die Tests setzen kleine Werte über den Konstruktor.
TONIE_ABSTAND_S: Final = 7 * 24 * 3600
#: Ohne jede Liste (erste Antwort ungültig) nach 1 Tag erneut, nicht erst nach 7
TONIE_OHNE_LISTE_ABSTAND_S: Final = 24 * 3600
TONIE_MIN_EINTRAEGE: Final = 1000
TONIE_MAX_ABWEICHUNG: Final = 0.5
TONIE_VERSUCH_ABSTAND_S: Final = 3600
TONIE_DATEI_VERSION: Final = 1

#: Zwischenspeicher (7.4)
ITUNES_TTL_S: Final = 7 * 24 * 3600
ITUNES_MAX_SUCHWOERTER: Final = 500
SITEMAP_TTL_S: Final = 7 * 24 * 3600
TREFFER_TTL_S: Final = 15 * 60
TREFFER_MAX_SUCHEN: Final = 4

ITUNES_SUCHWORT_MAX: Final = 100
BESCHREIBUNG_MAX: Final = 2000
_TAG_S: Final = 86400

_REDIRECT_STATUS: Final = frozenset({301, 302, 303, 307, 308})
_HOST_ZEICHEN = re.compile(r"[a-z0-9.-]+")
_PFAD_SHOP = re.compile(r"/de-de/tonies/[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*/")
_LOC = re.compile(r"<loc>\s*([^<>\s]{1,300})\s*</loc>")
_SHOP_LOC = re.compile(r"https://tonies\.com(/de-de/tonies/[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*/)")
_BILD_100 = re.compile(r"100x100bb\.jpg")
_ALTER_TEXT = re.compile(r"[0-9]{1,2}")


# --------------------------------------------------------------------------
# Fehler
# --------------------------------------------------------------------------


class OnlineFehler(Exception):
    """Basis aller Fehler der Abrufe. ``code`` ist ein kurzer Name für Protokoll und Status."""

    code = "online_fehler"

    def __init__(self, hinweis: str = "", *, code: str | None = None) -> None:
        super().__init__(hinweis or self.code)
        self.hinweis = hinweis
        if code is not None:
            self.code = code


class UrlAbgelehnt(OnlineFehler):
    """Adresse oder Weiterleitung verstößt gegen 8.1 (Schema, Host, Port, Sprünge)."""

    code = "url_abgelehnt"


class NichtErreichbar(OnlineFehler):
    """Netzfehler, Zeitüberschreitung oder ein Status, der nichts liefert (``status``)."""

    code = "nicht_erreichbar"

    def __init__(self, hinweis: str = "", *, status: int | None = None) -> None:
        super().__init__(hinweis)
        self.status = status


class QuellePausiert(OnlineFehler):
    """Die Quelle ist pausiert (429 oder 5xx, 15 Minuten); ``pause_bis`` ist die Uhrzeit (Uhr der Instanz)."""

    code = "quelle_pausiert"

    def __init__(self, gruppe: str, pause_bis: float) -> None:
        super().__init__(gruppe)
        self.gruppe = gruppe
        self.pause_bis = pause_bis


class ZuGross(OnlineFehler):
    """Mehr entpackte Bytes als erlaubt."""

    code = "zu_gross"


class FormatFehler(OnlineFehler):
    """Antwort hat nicht die erwartete Form. Für die Shopseite ``code = "online_shop_format"``."""

    code = "format"


class Gedrosselt(OnlineFehler):
    """Die Suche von Hand hätte länger als 5 s auf die Drossel warten müssen (Teilergebnis)."""

    code = "gedrosselt"


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------


def online_text(text: Any, max_zeichen: int) -> str | None:
    """Text aus einer fremden Quelle bereinigen (Design 6.3): Leerraum gestrafft, Steuerzeichen weg, NFC, gekürzt.

    Leer oder kein String: ``None``. Zeilenumbrüche und Tabs zählen als Leerraum (kein Zusammenkleben von Wörtern).
    """
    if not isinstance(text, str) or max_zeichen <= 0:
        return None
    t = "".join(" " if c.isspace() else c for c in text)
    t = ohne_steuerzeichen(t)
    t = "".join(c for c in t if not 0xD800 <= ord(c) <= 0xDFFF)  # einzelne Surrogate lassen sich nicht als UTF-8 schreiben
    t = nfc(" ".join(t.split()))
    t = t[:max_zeichen].strip()
    return t or None


class _TextSammler(HTMLParser):
    """HTML zu Text: Absätze bleiben (eine Zeile je Absatz), Tags und Skripte fallen weg."""

    _BLOCK = frozenset({"p", "br", "div", "li", "ul", "ol", "tr", "table", "section", "article", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"})
    _UEBERSPRINGEN = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.absaetze: list[str] = [""]
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in self._UEBERSPRINGEN:
            self._skip += 1
        elif tag in self._BLOCK:
            self.absaetze.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._UEBERSPRINGEN:
            self._skip = max(0, self._skip - 1)
        elif tag in self._BLOCK:
            self.absaetze.append("")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.absaetze[-1] += data


def html_zu_text(html: Any, max_zeichen: int = BESCHREIBUNG_MAX) -> str | None:
    """HTML (Beschreibung) zu reinem Text mit ``html.parser``: ein Absatz je Zeile, höchstens ``max_zeichen``; leer: ``None``."""
    if not isinstance(html, str):
        return None
    sammler = _TextSammler()
    try:
        sammler.feed(html)
        sammler.close()
    except Exception:  # noqa: BLE001 - kaputtes HTML darf nie durchschlagen
        return None
    absaetze = [a for a in (online_text(x, max_zeichen) for x in sammler.absaetze) if a]
    text = "\n".join(absaetze)[:max_zeichen].rstrip()
    return text or None


# --------------------------------------------------------------------------
# Adressen (8.1)
# --------------------------------------------------------------------------


def pruefe_url(url: Any) -> str:
    """Prüft eine Adresse nach 8.1 und gibt den Host (klein) zurück; sonst ``UrlAbgelehnt``.

    Nur ``https``, kein Port, kein Benutzerteil, keine IP-Adresse; Host genau ``itunes.apple.com``, ``raw.githubusercontent.com``,
    ``tonies.com`` oder mit der Endung ``.mzstatic.com`` (``mzstatic.com`` selbst nicht).
    """
    if not isinstance(url, str) or not url or len(url) > MAX_URL_LAENGE:
        raise UrlAbgelehnt("Adresse fehlt oder ist zu lang")
    if any(ord(c) <= 0x20 or ord(c) >= 0x7F or c == "\\" for c in url):
        raise UrlAbgelehnt("Zeichen in der Adresse nicht erlaubt")
    try:
        teile = urlsplit(url)
        port = teile.port
        host = teile.hostname
        yarl_host = URL(url).host
    except ValueError as err:
        raise UrlAbgelehnt("Adresse nicht lesbar") from err
    if teile.scheme != "https":
        raise UrlAbgelehnt("nur https")
    if port is not None or ":" in teile.netloc:
        raise UrlAbgelehnt("kein Port")
    if teile.username is not None or teile.password is not None or "@" in teile.netloc:
        raise UrlAbgelehnt("kein Benutzerteil")
    if not host or not _HOST_ZEICHEN.fullmatch(host) or yarl_host != host:
        raise UrlAbgelehnt("Host nicht erlaubt")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise UrlAbgelehnt("keine IP-Adresse")
    if host in ERLAUBTE_HOSTS:
        return host
    if host.endswith(ENDUNG_BILD) and len(host) > len(ENDUNG_BILD) and not host.startswith((".", "-")) and ".." not in host:
        return host
    raise UrlAbgelehnt("Host nicht erlaubt")


def _host_passt(quelle: str, host: str) -> bool:
    if quelle == QUELLE_ITUNES:
        return host == HOST_ITUNES
    if quelle == QUELLE_BILD:
        return host.endswith(ENDUNG_BILD)
    if quelle in (QUELLE_SHOP, QUELLE_SITEMAP):
        return host == HOST_TONIES
    if quelle == QUELLE_TONIE_LISTE:
        return host == HOST_GITHUB
    return False


#: Pause wirkt je Gruppe (Status 63 kennt Apple und Tonies; Bilder pausieren für sich)
_GRUPPE: Final = {
    QUELLE_ITUNES: "itunes",
    QUELLE_BILD: "bilder",
    QUELLE_SHOP: "tonies_shop",
    QUELLE_SITEMAP: "tonies_shop",
    QUELLE_TONIE_LISTE: "tonies",
}


# --------------------------------------------------------------------------
# Drossel (8.2)
# --------------------------------------------------------------------------


class Fenster:
    """Höchstens ``limit`` Abrufe je ``dauer``; ``reserve_hand`` davon nur für die Suche von Hand (der Lauf bekommt ``limit - reserve``)."""

    def __init__(self, limit: int, reserve_hand: int, dauer: float = FENSTER_S) -> None:
        self.limit = limit
        self.reserve_hand = reserve_hand
        self.dauer = dauer
        self._zeiten: collections.deque[float] = collections.deque()

    def wartezeit(self, jetzt: float, von_hand: bool) -> float:
        while self._zeiten and self._zeiten[0] <= jetzt - self.dauer:
            self._zeiten.popleft()
        erlaubt = self.limit if von_hand else self.limit - self.reserve_hand
        n = len(self._zeiten)
        if n < erlaubt:
            return 0.0
        return self._zeiten[n - erlaubt] + self.dauer - jetzt

    def belegen(self, jetzt: float) -> None:
        self._zeiten.append(jetzt)


class Abstand:
    """Ein Abruf je ``sekunden``."""

    def __init__(self, sekunden: float) -> None:
        self.sekunden = sekunden
        self._letzter: float | None = None

    def wartezeit(self, jetzt: float, von_hand: bool) -> float:  # noqa: ARG002 - gleiche Form wie Fenster
        if self._letzter is None:
            return 0.0
        return max(0.0, self._letzter + self.sekunden - jetzt)

    def belegen(self, jetzt: float) -> None:
        self._letzter = jetzt


# --------------------------------------------------------------------------
# Antwort und Executor
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Antwort:
    status: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)  # Namen klein
    url: str = ""


Executor = Callable[..., Awaitable[Any]]


async def _executor_standard(func: Callable[..., Any], *args: Any) -> Any:
    return await asyncio.get_running_loop().run_in_executor(None, func, *args)


def lese_version(pfad: Path | None = None) -> str:
    """Version aus ``manifest.json`` (liest die Datei: im Executor aufrufen). Ohne lesbare Datei ``"0"``."""
    pfad = pfad or Path(__file__).with_name("manifest.json")
    try:
        version = json.loads(pfad.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError, AttributeError):
        return "0"
    return version if isinstance(version, str) and re.fullmatch(r"[0-9A-Za-z.+-]{1,20}", version) else "0"


# --------------------------------------------------------------------------
# Auswertung (reine Funktionen, laufen im Executor)
# --------------------------------------------------------------------------


def _int(x: Any) -> int | None:
    return x if isinstance(x, int) and not isinstance(x, bool) else None


def bild_url_600(artwork_url_100: Any) -> str | None:
    """600-px-Adresse aus ``artworkUrl100``, nur über das feste Muster des letzten Pfadstücks ``100x100bb.jpg``; sonst ``None``."""
    if not isinstance(artwork_url_100, str):
        return None
    try:
        host = pruefe_url(artwork_url_100)
    except UrlAbgelehnt:
        return None
    if not host.endswith(ENDUNG_BILD):
        return None
    teile = urlsplit(artwork_url_100)
    pfad, _, letzter = teile.path.rpartition("/")
    if not _BILD_100.fullmatch(letzter) or teile.query or teile.fragment:
        return None
    return f"https://{host}{pfad}/600x600bb.jpg"


_ITUNES_TEXTE: Final = (  # (Feld, Höchstlänge)
    ("wrapperType", 40),
    ("collectionName", 300),
    ("artistName", 300),
    ("primaryGenreName", 100),
    ("releaseDate", 40),
)
MAX_ITUNES_ERGEBNISSE: Final = 50


def parse_itunes(body: bytes) -> list[dict[str, Any]]:
    """iTunes-JSON zu einer Liste von Dicts mit den Feldern aus 3.3. Falscher Typ: das Feld fehlt.

    Felder: ``wrapperType``, ``collectionId`` (int), ``collectionName``, ``artistName``, ``primaryGenreName``, ``trackCount`` (int),
    ``releaseDate``, ``bild_url`` (600 px, nur über das feste Muster), ``description`` (nur wenn Text, höchstens 2 000 Zeichen).
    """
    try:
        daten = json.loads(body)
    except (ValueError, RecursionError) as err:
        raise FormatFehler("iTunes: kein JSON") from err
    if not isinstance(daten, dict) or not isinstance(daten.get("results"), list):
        raise FormatFehler("iTunes: keine Ergebnisse")
    aus: list[dict[str, Any]] = []
    for roh in daten["results"][:MAX_ITUNES_ERGEBNISSE]:
        if not isinstance(roh, dict):
            continue
        e: dict[str, Any] = {}
        for feld, maximum in _ITUNES_TEXTE:
            wert = online_text(roh.get(feld), maximum)
            if wert is not None:
                e[feld] = wert
        for feld in ("collectionId", "trackCount"):
            zahl = _int(roh.get(feld))
            if zahl is not None:
                e[feld] = zahl
        bild = bild_url_600(roh.get("artworkUrl100"))
        if bild is not None:
            e["bild_url"] = bild
            e["artworkUrl100"] = roh["artworkUrl100"]  # ``online_abgleich`` liest den Cover-Wert hier; ``bild_url`` ist dieselbe Adresse in 600 px
        beschreibung = html_zu_text(roh.get("description"), BESCHREIBUNG_MAX)
        if beschreibung is not None:
            e["description"] = beschreibung
        aus.append(e)
    return aus


def parse_sitemap(body: bytes) -> list[str]:
    """Nur über ``<loc>``: Pfade ``/de-de/tonies/<a>/<b>/`` von ``https://tonies.com``; alles andere fällt weg. Ohne Doppelte, in Reihenfolge."""
    text = body.decode("utf-8", errors="replace")
    gesehen: dict[str, None] = {}
    for treffer in _LOC.finditer(text):
        m = _SHOP_LOC.fullmatch(treffer.group(1))
        if m:
            gesehen.setdefault(m.group(1), None)
    return list(gesehen)


class _NextDatenFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.bloecke: list[str] = []
        self._sammelt = False

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self._sammelt = True
            self.bloecke.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._sammelt = False

    def handle_data(self, data: str) -> None:
        if self._sammelt:
            self.bloecke[-1] += data


def _alter(x: Any) -> int | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, str) and _ALTER_TEXT.fullmatch(x.strip()):
        x = int(x.strip())
    if isinstance(x, int) and 0 <= x <= 18:
        return x
    return None


def parse_shop(body: bytes, model: str) -> dict[str, Any] | None:
    """Shopseite: nur der eine ``__NEXT_DATA__``-Block, ``props.pageProps.product``.

    ``salesId`` muss gleich ``model`` sein, sonst kommt ``None`` zurück („geholt, aber unbrauchbar“, genau der Wert, den
    ``online_abgleich`` in ``shop_daten[model]`` dafür erwartet). Übernommen werden ``description`` (HTML zu Text, höchstens
    2 000 Zeichen) als ``beschreibung`` und ``ageMin`` (ganze Zahl 0 bis 18, auch aus einem Text aus Ziffern; sonst verworfen) als ``alter_ab``.
    Fehlen beide Felder, oder fehlt der Block: ``FormatFehler`` (``online_shop_format``).
    """
    finder = _NextDatenFinder()
    try:
        finder.feed(body.decode("utf-8", errors="replace"))
        finder.close()
    except Exception as err:  # noqa: BLE001
        raise FormatFehler("Shopseite nicht lesbar", code="online_shop_format") from err
    if len(finder.bloecke) != 1:
        raise FormatFehler("Shopseite: kein eindeutiger Datenblock", code="online_shop_format")
    try:
        daten = json.loads(finder.bloecke[0])
    except (ValueError, RecursionError) as err:
        raise FormatFehler("Shopseite: Datenblock kein JSON", code="online_shop_format") from err
    produkt = None
    if isinstance(daten, dict):
        props = daten.get("props")
        seite = props.get("pageProps") if isinstance(props, dict) else None
        produkt = seite.get("product") if isinstance(seite, dict) else None
    if not isinstance(produkt, dict):
        raise FormatFehler("Shopseite: kein Produkt", code="online_shop_format")
    if produkt.get("salesId") != model:
        return None
    aus: dict[str, Any] = {}
    beschreibung = html_zu_text(produkt.get("description"), BESCHREIBUNG_MAX)
    if beschreibung:
        aus["beschreibung"] = beschreibung
    alter = _alter(produkt.get("ageMin"))
    if alter is not None:
        aus["alter_ab"] = alter
    if not aus:
        raise FormatFehler("Shopseite: Felder fehlen", code="online_shop_format")
    return aus


#: Felder der abgelegten Tonie-Liste. ``language`` bleibt, damit die Benutzbarkeit (``tonie_benutzbar``) auch am abgelegten Eintrag prüfbar ist.
TONIE_FELDER: Final = ("model", "series", "episodes", "tracks", "release", "category", "language")


def tonie_eintrag(roh: Mapping[str, Any]) -> dict[str, Any]:
    """Nur die Felder, die benutzt werden. ``tracks`` bleibt eine Liste der Titel (die Zahl ist deren Länge)."""
    tracks = roh.get("tracks")
    release = roh.get("release")
    return {
        "model": online_text(roh.get("model"), 40) or "",
        "series": online_text(roh.get("series"), 300) or "",
        "episodes": online_text(roh.get("episodes"), 300) or "",
        "tracks": [online_text(t, 200) or "" for t in tracks[:500]] if isinstance(tracks, list) else [],
        "release": release if isinstance(release, (str, int)) and not isinstance(release, bool) else "",
        "category": online_text(roh.get("category"), 60) or "",
        "language": online_text(roh.get("language"), 20) or "",
    }


def parse_tonie_liste(body: bytes, benutzbar: Callable[[dict[str, Any]], bool] | None = None) -> list[dict[str, Any]]:
    """Tonie-Liste: nur benutzbare Einträge (``online_abgleich.tonie_benutzbar``), reduziert auf ``TONIE_FELDER``. Keine Liste: ``FormatFehler``."""
    if benutzbar is None:
        from .online_abgleich import tonie_benutzbar as benutzbar  # noqa: PLC0415 - erst bei Bedarf (im Executor)
    try:
        daten = json.loads(body)
    except (ValueError, RecursionError) as err:
        raise FormatFehler("Tonie-Liste: kein JSON") from err
    if not isinstance(daten, list):
        raise FormatFehler("Tonie-Liste: keine Liste")
    aus: list[dict[str, Any]] = []
    for roh in daten:
        if not isinstance(roh, dict):
            continue
        try:
            if benutzbar(roh):
                aus.append(tonie_eintrag(roh))
        except Exception:  # noqa: BLE001 - ein kaputter Eintrag macht die Liste nicht ungültig
            continue
    return aus


# --------------------------------------------------------------------------
# Zwischenspeicher (7.4)
# --------------------------------------------------------------------------


class ItunesSpeicher:
    """iTunes-Antworten, 7 Tage, höchstens 500 Suchwörter (die ältesten fliegen)."""

    def __init__(self, zeit: Callable[[], float] = time.time, *, ttl: float = ITUNES_TTL_S, maximum: int = ITUNES_MAX_SUCHWOERTER) -> None:
        self._zeit = zeit
        self._ttl = ttl
        self._max = maximum
        self._daten: collections.OrderedDict[Any, tuple[float, Any]] = collections.OrderedDict()

    def __len__(self) -> int:
        return len(self._daten)

    def hole(self, schluessel: Any) -> Any | None:
        eintrag = self._daten.get(schluessel)
        if eintrag is None:
            return None
        if self._zeit() - eintrag[0] >= self._ttl:
            del self._daten[schluessel]
            return None
        return eintrag[1]

    def lege(self, schluessel: Any, daten: Any) -> None:
        self._daten.pop(schluessel, None)
        self._daten[schluessel] = (self._zeit(), daten)
        while len(self._daten) > self._max:
            self._daten.popitem(last=False)


class TrefferSpeicher:
    """Treffer mit Bildern: 15 Minuten, höchstens 4 Suchen (die älteste fliegt). OS3 befüllt ihn."""

    def __init__(self, zeit: Callable[[], float] = time.time, *, ttl: float = TREFFER_TTL_S, maximum: int = TREFFER_MAX_SUCHEN) -> None:
        self._zeit = zeit
        self._ttl = ttl
        self._max = maximum
        self._suchen: collections.OrderedDict[str, tuple[float, Any]] = collections.OrderedDict()

    def __len__(self) -> int:
        return len(self._suchen)

    def lege(self, such_id: str, daten: Any) -> None:
        self._suchen.pop(such_id, None)
        self._suchen[such_id] = (self._zeit(), daten)
        while len(self._suchen) > self._max:
            self._suchen.popitem(last=False)

    def hole(self, such_id: str) -> Any | None:
        eintrag = self._suchen.get(such_id)
        if eintrag is None:
            return None
        if self._zeit() - eintrag[0] >= self._ttl:
            del self._suchen[such_id]
            return None
        return eintrag[1]


# --------------------------------------------------------------------------
# Abrufe
# --------------------------------------------------------------------------


class OnlineQuellen:
    """Alle Abrufe der Online-Suche. Session, Uhr, Schlafen und Executor werden eingespeist (Tests ohne Netz, ohne Warten)."""

    def __init__(
        self,
        session: Any,
        *,
        version: str = "0",
        zeit: Callable[[], float] = time.time,
        schlafen: Callable[[float], Awaitable[Any]] = asyncio.sleep,
        im_executor: Executor = _executor_standard,
    ) -> None:
        self._session = session
        self._version = version
        self._zeit = zeit
        self._schlafen = schlafen
        self.im_executor = im_executor
        self._eimer: dict[str, Fenster | Abstand] = {
            QUELLE_ITUNES: Fenster(ITUNES_JE_MINUTE, ITUNES_RESERVE_HAND),
            QUELLE_BILD: Fenster(BILD_JE_MINUTE, BILD_RESERVE_HAND),
            QUELLE_SHOP: Abstand(SHOP_ABSTAND_S),
        }
        self._pausen: dict[str, float] = {}
        self._hosts: dict[str, asyncio.Semaphore] = {}
        self._shop_format_geloggt: int | None = None
        self.itunes_speicher = ItunesSpeicher(zeit)
        self.treffer_speicher = TrefferSpeicher(zeit)
        self._sitemap: list[str] | None = None
        self._sitemap_zeit = 0.0
        self._sitemap_sperre = asyncio.Lock()

    # ---- Pause ----

    def pause_bis(self, quelle: str) -> float | None:
        """Uhrzeit, bis zu der die Quelle pausiert (``QUELLE_*`` oder Gruppe), sonst ``None``."""
        gruppe = _GRUPPE.get(quelle, quelle)
        bis = self._pausen.get(gruppe)
        return bis if bis is not None and bis > self._zeit() else None

    def _pause_pruefen(self, gruppe: str) -> None:
        bis = self._pausen.get(gruppe)
        if bis is not None:
            if bis > self._zeit():
                raise QuellePausiert(gruppe, bis)
            del self._pausen[gruppe]

    def _pausieren(self, gruppe: str) -> QuellePausiert:
        bis = self._zeit() + PAUSE_S
        self._pausen[gruppe] = bis
        _LOGGER.warning("Online-Quelle %s pausiert 15 Minuten", gruppe)
        return QuellePausiert(gruppe, bis)

    def shop_format_loggen(self, hinweis: str) -> None:
        """``online_shop_format`` höchstens einmal je Tag ins Protokoll."""
        tag = int(self._zeit() // _TAG_S)
        if self._shop_format_geloggt != tag:
            self._shop_format_geloggt = tag
            _LOGGER.warning("online_shop_format: %s", hinweis)

    # ---- Drossel ----

    async def _drossel(self, quelle: str, von_hand: bool) -> None:
        eimer = self._eimer.get(quelle)
        if eimer is None:
            return
        start = self._zeit()
        while True:
            jetzt = self._zeit()
            warte = eimer.wartezeit(jetzt, von_hand)
            if warte <= 0:
                eimer.belegen(jetzt)  # kein await zwischen Prüfung und Belegen
                return
            if von_hand and (jetzt - start) + warte > HAND_WARTEN_MAX_S:
                raise Gedrosselt(quelle)
            await self._schlafen(warte)

    # ---- hole ----

    async def hole(
        self,
        url: str,
        quelle: str,
        *,
        von_hand: bool = False,
        kopfzeilen: Mapping[str, str] | None = None,
    ) -> Antwort:
        """Ruft ``url`` ab (8.1, 8.2). ``quelle``: ``QUELLE_*``. Gibt bei 200 und 304 eine ``Antwort`` zurück, sonst eine ``OnlineFehler``-Ausnahme."""
        if quelle not in MAX_BYTES:
            raise ValueError(f"unbekannte Quelle: {quelle}")
        if not _host_passt(quelle, pruefe_url(url)):
            raise UrlAbgelehnt("Host passt nicht zur Quelle")
        gruppe = _GRUPPE[quelle]
        self._pause_pruefen(gruppe)
        await self._drossel(quelle, von_hand)
        aktuell = url
        for sprung in range(MAX_SPRUENGE + 1):
            antwort = await self._einmal(aktuell, quelle, gruppe, kopfzeilen)
            if antwort.status not in _REDIRECT_STATUS:
                return antwort
            if sprung == MAX_SPRUENGE:
                raise UrlAbgelehnt("zu viele Weiterleitungen")
            ziel = antwort.headers.get("location")
            if not ziel:
                raise FormatFehler("Weiterleitung ohne Ziel")
            aktuell = urljoin(aktuell, ziel)
            pruefe_url(aktuell)  # dieselbe Prüfung wie am Anfang
        raise UrlAbgelehnt("zu viele Weiterleitungen")  # pragma: no cover

    def _semaphore(self, host: str) -> asyncio.Semaphore:
        sem = self._hosts.get(host)
        if sem is None:
            sem = self._hosts[host] = asyncio.Semaphore(MAX_VERBINDUNGEN_JE_HOST)
        return sem

    async def _einmal(self, url: str, quelle: str, gruppe: str, kopfzeilen: Mapping[str, str] | None) -> Antwort:
        host = pruefe_url(url)
        header = {k: v for k, v in (kopfzeilen or {}).items() if k.lower() != "user-agent"}
        header["User-Agent"] = f"TobiBox-HA/{self._version}"
        grenze = MAX_BYTES[quelle]
        try:
            async with self._semaphore(host):
                async with self._session.get(
                    url,
                    allow_redirects=False,
                    timeout=aiohttp.ClientTimeout(total=ZEITGRENZE_S[quelle]),
                    headers=header,
                ) as resp:
                    status = resp.status
                    kopf = {str(k).lower(): str(v) for k, v in resp.headers.items()}
                    if status in _REDIRECT_STATUS:
                        return Antwort(status, b"", kopf, url)
                    if status == 429 or status >= 500:
                        raise self._pausieren(gruppe)
                    if status == 403 and quelle == QUELLE_SHOP:
                        self.shop_format_loggen("Shopseite antwortet 403")
                        raise FormatFehler("Shop antwortet 403", code="online_shop_format")
                    if status == 304:
                        return Antwort(status, b"", kopf, url)
                    if status != 200:
                        raise NichtErreichbar(f"Status {status}", status=status)
                    teile: list[bytes] = []
                    summe = 0
                    # iter_chunked liefert entpackte Bytes (aiohttp entpackt selbst): eine gzip-Bombe reißt die Grenze, bevor sie den Speicher füllt
                    async for block in resp.content.iter_chunked(BLOCK_BYTES):
                        summe += len(block)
                        if summe > grenze:
                            raise ZuGross(f"mehr als {grenze} Bytes")
                        teile.append(block)
                    return Antwort(status, b"".join(teile), kopf, url)
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            raise NichtErreichbar(type(err).__name__) from err

    # ---- Abrufe mit Auswertung ----

    async def itunes_suche(self, suchwort: str, art: str, *, von_hand: bool = False) -> list[dict[str, Any]]:
        """iTunes-Suche (3.3). ``art``: ``"album"`` (media=music, entity=album) oder ``"hoerbuch"`` (media=audiobook).

        Antworten bleiben 7 Tage im Speicher (höchstens 500 Suchwörter); ein Treffer im Speicher kostet keine Drossel.
        """
        wort = online_text(suchwort, ITUNES_SUCHWORT_MAX)
        if wort is None:
            return []
        if art == "album":
            media = "media=music&entity=album"
        elif art == "hoerbuch":
            media = "media=audiobook"
        else:
            raise ValueError(f"unbekannte Art: {art}")
        schluessel = (art, wort.casefold())
        gemerkt = self.itunes_speicher.hole(schluessel)
        if gemerkt is not None:
            return gemerkt
        url = f"{ITUNES_URL}?country=de&lang=de_de&limit=25&{media}&term={quote(wort, safe='')}"
        antwort = await self.hole(url, QUELLE_ITUNES, von_hand=von_hand)
        ergebnis = await self.im_executor(parse_itunes, antwort.body)
        self.itunes_speicher.lege(schluessel, ergebnis)
        return ergebnis

    async def bild_holen(self, url: str, *, von_hand: bool = False) -> bytes:
        """Ein Cover-Bild (Host ``*.mzstatic.com``), höchstens 5 MB."""
        return (await self.hole(url, QUELLE_BILD, von_hand=von_hand)).body

    async def sitemap_pfade(self) -> list[str]:
        """Pfade der Shopseiten aus beiden Sitemap-Dateien, höchstens einmal je 7 Tage geholt (im Speicher)."""
        async with self._sitemap_sperre:
            if self._sitemap is not None and self._zeit() - self._sitemap_zeit < SITEMAP_TTL_S:
                return self._sitemap
            pfade: dict[str, None] = {}
            for url in SITEMAP_URLS:
                antwort = await self.hole(url, QUELLE_SITEMAP)
                for p in await self.im_executor(parse_sitemap, antwort.body):
                    pfade.setdefault(p, None)
            self._sitemap = list(pfade)
            self._sitemap_zeit = self._zeit()
            return self._sitemap

    async def shop_seite(self, pfad: str, model: str, *, von_hand: bool = False) -> dict[str, Any] | None:
        """Beschreibung und Alter einer Shopseite (3.2). ``pfad`` aus ``sitemap_pfade``.

        Ergebnis direkt als ``shop_daten[model]`` für ``online_abgleich``: ein Dict (``beschreibung`` und/oder ``alter_ab``) oder ``None``
        bei falscher ``salesId`` (geholt, aber unbrauchbar). Bei ``FormatFehler`` (Felder fehlen) setzt der Aufrufer ebenfalls ``None``."""
        if not isinstance(pfad, str) or not _PFAD_SHOP.fullmatch(pfad):
            raise UrlAbgelehnt("Shop-Pfad nicht erlaubt")
        antwort = await self.hole(SHOP_BASIS + pfad, QUELLE_SHOP, von_hand=von_hand)
        try:
            return await self.im_executor(parse_shop, antwort.body, model)
        except FormatFehler as err:
            self.shop_format_loggen(err.hinweis)
            raise


# --------------------------------------------------------------------------
# Tonie-Liste (3.1)
# --------------------------------------------------------------------------


def _tonie_datei_lesen(pfad: Path) -> dict[str, Any] | None:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (
        not isinstance(daten, dict)
        or daten.get("version") != TONIE_DATEI_VERSION
        or not isinstance(daten.get("eintraege"), list)
        or not isinstance(daten.get("geladen"), (int, float))
    ):
        return None
    etag = daten.get("etag")
    geladen = float(daten["geladen"])
    stand = daten.get("stand")
    return {
        "eintraege": daten["eintraege"],
        "geladen": geladen,
        "etag": etag if isinstance(etag, str) else None,
        # Ältere Dateien ohne ``stand``: der letzte Abgleich gilt als Stand
        "stand": float(stand) if isinstance(stand, (int, float)) and not isinstance(stand, bool) else geladen,
    }


def _tonie_datei_schreiben(pfad: Path, eintraege: list[dict[str, Any]], geladen: float, etag: str | None, stand: float | None = None) -> None:
    """Atomar: erst in eine Nebendatei, dann ``replace``."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_name(pfad.name + ".tmp")
    inhalt = {"version": TONIE_DATEI_VERSION, "geladen": geladen, "stand": geladen if stand is None else stand, "etag": etag, "eintraege": eintraege}
    tmp.write_text(json.dumps(inhalt, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, pfad)


class TonieListe:
    """Die Tonie-Liste der Gemeinschaft als Datei ``tonies.json`` (3.1) und im Speicher."""

    def __init__(
        self,
        quellen: OnlineQuellen,
        datei: Path,
        *,
        benutzbar: Callable[[dict[str, Any]], bool] | None = None,
        min_eintraege: int = TONIE_MIN_EINTRAEGE,
        max_abweichung: float = TONIE_MAX_ABWEICHUNG,
        zeit: Callable[[], float] | None = None,
    ) -> None:
        self._quellen = quellen
        self._datei = datei
        self._benutzbar = benutzbar
        self._min = min_eintraege
        self._abweichung = max_abweichung
        self._zeit = zeit or quellen._zeit  # noqa: SLF001 - dieselbe Uhr
        self._eintraege: list[dict[str, Any]] | None = None
        self._stand: float | None = None
        self._etag: str | None = None
        self._von_platte = False
        #: Uhrzeit der letzten **vollständigen** Antwort (neu, 304 oder verworfen): danach höchstens einmal je 7 Tage ein neuer Abruf
        self._abgeglichen: float | None = None
        self._letzter_versuch: float | None = None
        self._sperre = asyncio.Lock()
        #: Ergebnis des letzten Versuchs: ``neu``, ``unveraendert``, ``verworfen`` oder ein Fehlercode; ``verworfen_grund`` nennt den Grund
        self.letztes_ergebnis: str | None = None
        self.verworfen_grund: str | None = None

    @property
    def eintraege(self) -> list[dict[str, Any]]:
        return self._eintraege or []

    @property
    def anzahl(self) -> int:
        return len(self._eintraege) if self._eintraege is not None else 0

    @property
    def stand(self) -> float | None:
        """Uhrzeit, seit der der **Inhalt** der Liste so ist. Ändert sich nur bei wirklich anderem Inhalt (nicht bei 304, gleichem Inhalt oder neuer ETag)."""
        return self._stand

    async def sicherstellen(self, *, erzwingen: bool = False) -> bool:
        """Liste bereit machen: beim ersten Bedarf laden (erst Datei, dann Netz), danach höchstens einmal je 7 Tage.

        Gibt zurück, ob eine Liste vorliegt. Netzfehler werfen nicht; ``letztes_ergebnis`` nennt den Grund. Nach einem Fehlschlag
        gibt es frühestens nach einer Stunde einen neuen Versuch (``erzwingen`` ignoriert das).
        """
        async with self._sperre:
            if not self._von_platte:
                self._von_platte = True
                gelesen = await self._quellen.im_executor(_tonie_datei_lesen, self._datei)
                if gelesen:
                    self._eintraege, self._stand, self._etag = gelesen["eintraege"], gelesen["stand"], gelesen["etag"]
                    self._abgeglichen = gelesen["geladen"]
            jetzt = self._zeit()
            if not erzwingen:
                # Eine verworfene Liste zählt als der Abruf der Woche (sonst käme sie stündlich wieder, die ETag der alten Liste hilft nicht)
                abstand = TONIE_ABSTAND_S if self._eintraege is not None else TONIE_OHNE_LISTE_ABSTAND_S
                if self._abgeglichen is not None and jetzt - self._abgeglichen < abstand:
                    return self._eintraege is not None
                if self._letzter_versuch is not None and jetzt - self._letzter_versuch < TONIE_VERSUCH_ABSTAND_S:
                    return self._eintraege is not None
            self._letzter_versuch = jetzt
            try:
                await self._aktualisieren(jetzt)
            except OnlineFehler as err:
                self.letztes_ergebnis = err.code
                _LOGGER.info("Tonie-Liste nicht geladen: %s", err.code)
            return self._eintraege is not None

    async def _aktualisieren(self, jetzt: float) -> None:
        kopf = {"If-None-Match": self._etag} if self._etag and self._eintraege is not None else None
        antwort = await self._quellen.hole(TONIE_LISTE_URL, QUELLE_TONIE_LISTE, kopfzeilen=kopf)
        self._abgeglichen = jetzt
        if antwort.status == 304 and self._eintraege is not None:
            await self._quellen.im_executor(_tonie_datei_schreiben, self._datei, self._eintraege, jetzt, self._etag, self._stand)
            self.letztes_ergebnis = "unveraendert"
            return
        try:
            neu = await self._quellen.im_executor(parse_tonie_liste, antwort.body, self._benutzbar)
        except FormatFehler as err:
            self._verwerfen(str(err))
            return
        if len(neu) < self._min:
            self._verwerfen(f"nur {len(neu)} benutzbare Einträge")
            return
        alt = self.anzahl
        if alt and abs(len(neu) - alt) / alt > self._abweichung:
            self._verwerfen(f"Zahl {alt} auf {len(neu)} geändert")
            return
        etag = antwort.headers.get("etag")
        # Neuer Stand nur bei anderem Inhalt: an ihm hängt das Verfallen der Marken (``keiner``/``fehler``)
        stand = self._stand if neu == self._eintraege and self._stand is not None else jetzt
        await self._quellen.im_executor(_tonie_datei_schreiben, self._datei, neu, jetzt, etag, stand)
        self._eintraege, self._stand, self._etag = neu, stand, etag
        self.letztes_ergebnis = "neu"
        self.verworfen_grund = None

    def _verwerfen(self, grund: str) -> None:
        self.letztes_ergebnis = "verworfen"
        self.verworfen_grund = grund
        _LOGGER.warning("Tonie-Liste verworfen (die alte bleibt): %s", grund)


__all__ = [
    "Abstand",
    "Antwort",
    "Fenster",
    "FormatFehler",
    "Gedrosselt",
    "ItunesSpeicher",
    "NichtErreichbar",
    "OnlineFehler",
    "OnlineQuellen",
    "QuellePausiert",
    "TonieListe",
    "TrefferSpeicher",
    "UrlAbgelehnt",
    "ZuGross",
    "bild_url_600",
    "html_zu_text",
    "lese_version",
    "online_text",
    "parse_itunes",
    "parse_shop",
    "parse_sitemap",
    "parse_tonie_liste",
    "pruefe_url",
]

