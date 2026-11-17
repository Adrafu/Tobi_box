"""Beobachter „Gehört“ (Stufe B, ``docs/designs/gehoert.md`` 2 und 3; ``mqtt-v1.md`` 3.4, 4.5; ``data-model.md`` 1.6).

Reines Modul: keine Datei, kein Netz, keine Uhr, kein Zufall. ``step`` (äußeres Ereignis) und ``step_befehl`` (vom Kern
ausgegebener Befehl) nehmen den Zustand und geben den neuen Zustand und Ausgaben zurück. Zeit kommt als ``Jetzt``, die
Kennung des Gerätestarts, neue UUIDs und die Dauer einer Folge kommen über den ``Kontext``. Die Datei ``gehoert.json``, die
Hintergrund-Schreibaufgabe und das Senden stehen in ``gehoert_puffer`` und ``ha``.

**Sitzung** = zusammenhängendes Hören **einer Folge** (Pausen bis 30 Minuten gehören dazu). Der Beobachter führt höchstens
eine offene Sitzung. Die Kennung des Tobies kommt nie vor (Frage 9): Die Sitzung kennt nur Serie und Folge.

**Hörzeit** (2): Summe des Zuwachses ``dp`` der Position zwischen zwei Meldungen, wenn ``0 < dp``; er wird auf
``2 × dt + 2`` gekappt (``dt`` Monotonzeit). Die Basislinie wird bei Track-, Folgen- und Wiedergabe-Wechsel (``gen``) und
bei ``dp ≤ 0`` neu gesetzt.

**Grenzen** (3.2, Vorrang von oben nach unten): ``herunterfahren`` (Befehl ``Herunterfahren``), ``dienst_ende`` (Ereignis
``DienstEndet``), ``abbruch`` (offene Sitzung beim Start), ``ende_der_folge`` (``FolgeZuEnde`` der laufenden Folge),
``wechsel`` (erste gespielte Sekunde einer anderen Folge), ``pause`` (30 Minuten ohne gespielte Sekunde, ``grund`` = letzter
Pausegrund). Track-Wechsel und Springen in der Folge beenden nichts. Eine Sitzung mit Hörzeit 0 wird verworfen.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from . import events as ev
from .store import Ungueltig

SCHEMA_VERSION = 1
MAX_ZEILEN = 500
PAUSE_S = 30 * 60.0  # keine gespielte Sekunde seit so langer Zeit: ``pause``
OFFEN_SCHREIBEN_S = 120.0  # die offene Sitzung höchstens alle 2 Minuten (und beim Beginn einer Pause)
QUITTUNG_SCHREIBEN_S = 600.0  # Quittungen höchstens 10 Minuten ungeschrieben
ZWISCHENSTAND_S = 15 * 60.0  # Zwischenstand einer laufenden Sitzung alle 15 Minuten (nur MQTT)
KAPPUNG_FAKTOR = 2.0  # ``dp`` zählt höchstens ``2 × dt + 2``
KAPPUNG_PLUS_S = 2.0

ENDEN = ("ende_der_folge", "wechsel", "pause", "herunterfahren", "dienst_ende", "abbruch", "teilweise")
ENDEN_IN_ZEILEN = tuple(e for e in ENDEN if e != "teilweise")  # in ``zeilen`` steht nie ``teilweise`` (data-model 1.6)
MAX_SERIE = 64
MAX_FOLGE_BYTES = 255
MAX_BOOT_ID = 64
MAX_GRUND = 32


# --------------------------------------------------------------------------
# Eingänge, Zustand, Ausgaben
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Quittung:
    """HA hat diese Sitzungen gespeichert oder schon gekannt (``gehoert_quittung``, mqtt-v1 3.7): Genau diese Zeilen fallen weg."""

    sitzungen: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Kontext:
    """Was der Beobachter von außen braucht, ohne selbst Datei, Zufall oder Bibliothek zu kennen."""

    boot_id: str
    neue_id: Callable[[], str] = lambda: str(uuid.uuid4())
    #: Dauer der Folge in ganzen Sekunden (> 0), ``None``: unbekannt
    dauer: Callable[[str, str], int | None] = lambda serie, folge: None


@dataclass(frozen=True, slots=True)
class Schreiben:
    """``gehoert.json`` mit dem neuen Zustand schreiben (ein Vorgang). ``sync``: mit ``fsync``, bevor es weitergeht."""

    sync: bool = False
    grund: str = ""


@dataclass(frozen=True, slots=True)
class ZeileNeu:
    """Eine Sitzung ist zur Zeile geworden: Sie soll bald gesendet werden (4.5, Punkt 2)."""

    sitzung: str
    ende: str


Ausgabe = Schreiben | ZeileNeu | ev.Protokoll


@dataclass(frozen=True, slots=True)
class Offen:
    """Die laufende Sitzung. Basislinie und Zeiten (``…_mono``, Monotonsekunden) stehen nur im Arbeitsspeicher."""

    sitzung: str
    serie: str
    folge: str
    dauer_s: int | None
    beginn: str  # Wanduhr der Box (ISO, ``Z``)
    zeit_ok: bool
    boot_id: str
    beginn_mono: float
    letzte_mono: float  # letzte gespielte Sekunde
    gehoert: float
    basis_gen: int | None
    basis_track: int
    basis_pos: float
    basis_mono: float
    geschrieben_mono: float  # letztes Schreiben der offenen Sitzung
    geschrieben_g: int  # Hörzeit (ganze Sekunden) im letzten Schreiben
    zwischen_mono: float  # letzter Zwischenstand (oder Beginn)


@dataclass(frozen=True, slots=True)
class Zustand:
    zeilen: tuple[Mapping[str, Any], ...] = ()
    verworfen: int = 0
    offen: Offen | None = None
    gen: int | None = None  # Wiedergabe-Generation des letzten ``Abspielen``
    laeuft: bool = False  # ``Abspielen`` seit dem letzten ``Pausieren``/Folgenende: eine Sitzung darf beginnen
    grund: str | None = None  # letzter Pausegrund
    unsicher: bool = False  # Zeilen dieses Gerätestarts mit ``zeit_ok = false``: bei guter Uhr korrigieren (3.3)
    quittung_seit: float | None = None  # Quittungen, die noch nicht geschrieben sind (seit ``mono``)


@dataclass(frozen=True, slots=True)
class Geladen:
    """Inhalt einer ``gehoert.json`` nach der Prüfung (ungültige Zeilen schon verworfen)."""

    verworfen: int = 0
    offen: Mapping[str, Any] | None = None
    zeilen: tuple[Mapping[str, Any], ...] = ()
    ungueltig: int = 0  # so viele Zeilen (und eine ungültige offene Sitzung) wurden beim Laden verworfen


def _prot(ebene: str, ereignis: str, ergebnis: str, **daten: Any) -> ev.Protokoll:
    return ev.Protokoll("gehoert", ebene, ereignis, ergebnis, None, daten)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Hilfen
# --------------------------------------------------------------------------


def iso(wall: float) -> str:
    """Wanduhr als ISO-Zeit mit ``Z`` (ganze Sekunden)."""
    try:
        t = datetime.fromtimestamp(wall, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        t = datetime.fromtimestamp(0, tz=timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _kappe(text: str, n_bytes: int) -> str:
    roh = text.encode("utf-8")
    return text if len(roh) <= n_bytes else roh[:n_bytes].decode("utf-8", errors="ignore")


def _ganz_g(o: Offen) -> int:
    """Hörzeit in ganzen Sekunden, höchstens ``ende_boot_s − beginn_boot_s + 2`` (mqtt-v1 3.4).

    # B1-OFFEN: Entwurf 2 („bei schnellerem Abspielen zählt die Länge des Inhalts“) und die Schranke des Vertrags widersprechen sich
    # bei schnellerem Abspielen. Vorläufig gewinnt die Schranke: Die Box meldet nie eine Zeile, die HA kappen müsste.
    # Die erste Meldung einer Sitzung ist nur Basislinie (Entwurf 2: Basislinie bei Wechsel von ``gen``): bis zu etwa 1 s je Sitzung fehlt.
    """
    b = math.floor(o.beginn_mono)
    e = max(b, math.floor(o.letzte_mono))
    return min(int(o.gehoert + 0.5), e - b + 2)


def _zeile_aus(o: Offen, ende: str, grund: str | None) -> dict[str, Any] | None:
    """Die Sitzung als Zeile (Felder wie ``gespielt`` ohne die Hülle); ``None`` bei Hörzeit 0."""
    g = _ganz_g(o)
    if g < 1:
        return None
    b = math.floor(o.beginn_mono)
    z: dict[str, Any] = {"sitzung": o.sitzung, "serie": o.serie, "folge": o.folge}
    if o.dauer_s is not None:
        z["folge_dauer_s"] = o.dauer_s
    z.update(
        beginn=o.beginn, zeit_ok=o.zeit_ok, boot_id=o.boot_id, beginn_boot_s=b,
        ende_boot_s=max(b, math.floor(o.letzte_mono)), gehoert_s=g, ende=ende,
    )
    if grund:
        z["grund"] = grund[:MAX_GRUND]
    return z


def offene_zeile(z: Zustand) -> dict[str, Any] | None:
    """Stand der offenen Sitzung als Zeile mit ``ende = teilweise`` (für ``gehoert.json`` und den Zwischenstand), sonst ``None``."""
    return None if z.offen is None else _zeile_aus(z.offen, "teilweise", None)


def _haenge_an(z: Zustand, zeile: Mapping[str, Any]) -> tuple[Zustand, list[Ausgabe]]:
    """Neue Zeile hinten anfügen (älteste zuerst); mehr als ``MAX_ZEILEN``: die ältesten fallen weg, ``verworfen`` zählt."""
    zeilen = z.zeilen + (zeile,)
    aus: list[Ausgabe] = []
    verworfen = z.verworfen
    if len(zeilen) > MAX_ZEILEN:
        n = len(zeilen) - MAX_ZEILEN
        zeilen = zeilen[n:]
        verworfen += n
        aus.append(_prot("WARNING", "gehoert_zeile_verworfen", "ueberlauf", anzahl=n, verworfen=verworfen))
    return replace(z, zeilen=zeilen, verworfen=verworfen), aus


# --------------------------------------------------------------------------
# Prüfen und Laden (data-model 1.6)
# --------------------------------------------------------------------------


def _ist_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _ist_uuid(x: Any) -> bool:
    if not isinstance(x, str) or len(x) != 36:
        return False
    try:
        uuid.UUID(x)
    except ValueError:
        return False
    return True


def _ist_zeit(x: Any) -> bool:
    if not isinstance(x, str) or not x:
        return False
    try:
        datetime.fromisoformat(x.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def pruefe_zeile(r: Any, *, offen: bool = False) -> dict[str, Any] | None:
    """Eine Zeile nach ``mqtt-v1.md`` 3.4 prüfen; gibt sie in Soll-Reihenfolge ohne fremde Felder zurück, ungültig: ``None``.

    ``offen=True``: die offene Sitzung (``ende`` ist ``teilweise``); sonst eine abgeschlossene Zeile (nie ``teilweise``)."""
    if not isinstance(r, dict):
        return None
    sitzung, serie, folge = r.get("sitzung"), r.get("serie"), r.get("folge")
    dauer, boot_id, grund = r.get("folge_dauer_s"), r.get("boot_id"), r.get("grund")
    b, e, g, ende = r.get("beginn_boot_s"), r.get("ende_boot_s"), r.get("gehoert_s"), r.get("ende")
    if not (
        _ist_uuid(sitzung)
        and isinstance(serie, str) and 1 <= len(serie) <= MAX_SERIE
        and isinstance(folge, str) and 1 <= len(folge.encode("utf-8")) <= MAX_FOLGE_BYTES
        and (dauer is None or (_ist_int(dauer) and dauer > 0))
        and _ist_zeit(r.get("beginn"))
        and isinstance(r.get("zeit_ok"), bool)
        and isinstance(boot_id, str) and 1 <= len(boot_id) <= MAX_BOOT_ID
        and _ist_int(b) and b >= 0
        and _ist_int(e) and e >= b
        and _ist_int(g) and 1 <= g <= e - b + 2
        and ende == ("teilweise" if offen else ende) and ende in (("teilweise",) if offen else ENDEN_IN_ZEILEN)
        and (grund is None or (isinstance(grund, str) and len(grund) <= MAX_GRUND))
    ):
        return None
    z: dict[str, Any] = {"sitzung": sitzung, "serie": serie, "folge": folge}
    if dauer is not None:
        z["folge_dauer_s"] = dauer
    z.update(beginn=r["beginn"], zeit_ok=r["zeit_ok"], boot_id=boot_id, beginn_boot_s=b, ende_boot_s=e, gehoert_s=g, ende=ende)
    if grund:
        z["grund"] = grund
    return z


def parse_datei(roh: Mapping[str, Any]) -> Geladen:
    """``gehoert.json`` prüfen. Ist der Rahmen ungültig, wirft es ``Ungueltig`` (dann gilt ``.bak``, data-model 1.3);
    eine einzelne ungültige Zeile wird verworfen und gezählt (Ausnahme zu 1.3)."""
    verworfen, offen, zeilen = roh.get("verworfen"), roh.get("offen"), roh.get("zeilen")
    if not _ist_int(verworfen) or verworfen < 0:
        raise Ungueltig("schema_ungueltig", "verworfen")
    if offen is not None and not isinstance(offen, dict):
        raise Ungueltig("schema_ungueltig", "offen")
    if not isinstance(zeilen, list):
        raise Ungueltig("schema_ungueltig", "zeilen")
    gut: list[Mapping[str, Any]] = []
    ungueltig = 0
    gesehen: set[str] = set()
    for r in zeilen:
        p = pruefe_zeile(r)
        if p is None:
            ungueltig += 1
        elif p["sitzung"] not in gesehen:  # dieselbe Sitzung zweimal in einer Datei: einmal behalten
            gesehen.add(p["sitzung"])
            gut.append(p)
    offen_ok: Mapping[str, Any] | None = None
    if offen is not None:
        offen_ok = pruefe_zeile(offen, offen=True)
        if offen_ok is None:
            ungueltig += 1
    return Geladen(verworfen, offen_ok, tuple(gut), ungueltig)


def zu_json(z: Zustand) -> dict[str, Any]:
    """Inhalt von ``gehoert.json`` (``data-model.md`` 1.6)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "verworfen": z.verworfen,
        "offen": offene_zeile(z),
        "zeilen": [dict(r) for r in z.zeilen],
    }


def geladen_zu_json(g: Geladen) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "verworfen": g.verworfen,
        "offen": dict(g.offen) if g.offen is not None else None,
        "zeilen": [dict(r) for r in g.zeilen],
    }


def starte(g: Geladen, k: Kontext) -> tuple[Zustand, list[Ausgabe]]:
    """Zustand nach dem Laden. Eine offene Sitzung (Strom weg, Absturz) wird zur Zeile mit ``ende = abbruch`` (3.2, 3.4)."""
    verworfen = g.verworfen + g.ungueltig  # eine so verworfene Zeile zählt mit (data-model 1.6)
    z = Zustand(zeilen=tuple(g.zeilen), verworfen=verworfen)
    aus: list[Ausgabe] = []
    schreiben = False
    if g.ungueltig:
        aus.append(_prot("WARNING", "gehoert_zeile_ungueltig", "verworfen", anzahl=g.ungueltig))
        schreiben = True
    if len(z.zeilen) > MAX_ZEILEN:  # Datei von Hand verlängert
        n = len(z.zeilen) - MAX_ZEILEN
        z = replace(z, zeilen=z.zeilen[n:], verworfen=z.verworfen + n)
        schreiben = True
    if g.offen is not None:
        schreiben = True
        zeile = {k_: v for k_, v in g.offen.items() if k_ != "grund"}
        zeile["ende"] = "abbruch"
        if all(r["sitzung"] != zeile["sitzung"] for r in z.zeilen):
            z, mehr = _haenge_an(z, zeile)
            aus += mehr
            aus.append(ZeileNeu(zeile["sitzung"], "abbruch"))
            aus.append(_prot("INFO", "gehoert_abbruch", "zeile", sitzung=zeile["sitzung"], gehoert_s=zeile["gehoert_s"]))
    if any(not r["zeit_ok"] and r["boot_id"] == k.boot_id for r in z.zeilen):
        z = replace(z, unsicher=True)  # Dienst-Neustart im selben Gerätestart: die Uhr kann noch gut werden
    if schreiben:
        aus.append(Schreiben(False, "start"))
    return z, aus


# --------------------------------------------------------------------------
# Schritt
# --------------------------------------------------------------------------


def _beende(z: Zustand, ende: str, *, sync: bool = False, grund: str | None = None) -> tuple[Zustand, list[Ausgabe]]:
    """Die offene Sitzung abschließen: Zeile anfügen (Hörzeit 0: verwerfen)."""
    o = z.offen
    if o is None:
        return z, [Schreiben(True, ende)] if sync else []
    z = replace(z, offen=None)
    zeile = _zeile_aus(o, ende, grund if ende == "pause" else None)
    if zeile is None:
        return z, ([Schreiben(True, ende)] if sync else []) + [_prot("DEBUG", "gehoert_sitzung", "verworfen", grund="hoerzeit_0", ende=ende)]
    z, aus = _haenge_an(z, zeile)
    aus.append(ZeileNeu(o.sitzung, ende))
    aus.append(Schreiben(sync, ende))
    aus.append(_prot("INFO", "gehoert_sitzung", ende, serie=o.serie, folge=o.folge, gehoert_s=zeile["gehoert_s"]))
    return z, aus


def _beginne(z: Zustand, e: ev.PlayerPosition, jetzt: ev.Jetzt, k: Kontext) -> tuple[Zustand, list[Ausgabe]]:
    folge = _kappe(e.datei, MAX_FOLGE_BYTES)
    serie = e.serie_id[:MAX_SERIE]
    gen = e.gen if e.gen is not None else z.gen
    o = Offen(
        sitzung=k.neue_id(), serie=serie, folge=folge, dauer_s=k.dauer(e.serie_id, e.datei), beginn=iso(jetzt.wall),
        zeit_ok=jetzt.zeit_ok, boot_id=k.boot_id, beginn_mono=jetzt.mono, letzte_mono=jetzt.mono, gehoert=0.0,
        basis_gen=gen, basis_track=e.track, basis_pos=e.position_s, basis_mono=jetzt.mono,
        geschrieben_mono=jetzt.mono, geschrieben_g=0, zwischen_mono=jetzt.mono,
    )
    z = replace(z, offen=o, unsicher=z.unsicher or (not jetzt.zeit_ok))
    return z, [_prot("DEBUG", "gehoert_sitzung", "beginn", serie=serie, folge=folge, zeit_ok=jetzt.zeit_ok)]


def _position(z: Zustand, e: ev.PlayerPosition, jetzt: ev.Jetzt, k: Kontext) -> tuple[Zustand, list[Ausgabe]]:
    if e.gen is not None and z.gen is not None and e.gen != z.gen:
        return z, []  # Nachzügler einer früheren Wiedergabe
    if not e.serie_id or not e.datei:
        return z, [_prot("WARNING", "gehoert_position", "ignoriert", grund="serie_oder_folge_leer")]  # der Vertrag verlangt mindestens 1 Zeichen
    gen = e.gen if e.gen is not None else z.gen
    o = z.offen
    aus: list[Ausgabe] = []
    if o is not None and (o.serie, o.folge) != (e.serie_id[:MAX_SERIE], _kappe(e.datei, MAX_FOLGE_BYTES)):
        if not (e.spielt and z.laeuft):
            return z, []  # eine andere Folge, aber noch keine gespielte Sekunde: die Sitzung bleibt
        z, aus = _beende(z, "wechsel")
        o = None
    if o is None:
        if not (e.spielt and z.laeuft):
            return z, aus
        z, mehr = _beginne(z, e, jetzt, k)
        return z, aus + mehr
    gezaehlt = False
    gehoert = o.gehoert
    if o.basis_gen == gen and o.basis_track == e.track:
        dp = e.position_s - o.basis_pos
        dt = max(0.0, jetzt.mono - o.basis_mono)
        if dp > 0:
            gehoert += min(dp, KAPPUNG_FAKTOR * dt + KAPPUNG_PLUS_S)
            gezaehlt = True
    # sonst (Wechsel von Track oder Wiedergabe, dp ≤ 0): nur die Basislinie neu setzen
    o = replace(
        o, gehoert=gehoert, basis_gen=gen, basis_track=e.track, basis_pos=e.position_s, basis_mono=jetzt.mono,
        letzte_mono=jetzt.mono if (e.spielt or gezaehlt) else o.letzte_mono,
    )
    return replace(z, offen=o), aus


def _folge_zu_ende(z: Zustand, e: ev.FolgeZuEnde) -> tuple[Zustand, list[Ausgabe]]:
    if e.gen is not None and z.gen is not None and e.gen != z.gen:
        return z, []
    o = z.offen
    z = replace(z, laeuft=False)
    if o is None or (o.serie, o.folge) != (e.serie_id[:MAX_SERIE], _kappe(e.datei, MAX_FOLGE_BYTES)):
        return z, []
    return _beende(z, "ende_der_folge")


def _korrigiere_uhr(z: Zustand, jetzt: ev.Jetzt, k: Kontext) -> tuple[Zustand, list[Ausgabe]]:
    """Wird die Uhr im selben Gerätestart gut, bekommen **alle** Zeilen dieses Starts (und die offene Sitzung) eine neue Wanduhr (3.3)."""
    neue = []
    n = 0
    for r in z.zeilen:
        if not r["zeit_ok"] and r["boot_id"] == k.boot_id:
            r = {**r, "beginn": iso(jetzt.wall - (jetzt.mono - r["beginn_boot_s"])), "zeit_ok": True}
            n += 1
        neue.append(r)
    o = z.offen
    if o is not None and not o.zeit_ok and o.boot_id == k.boot_id:
        o = replace(o, beginn=iso(jetzt.wall - (jetzt.mono - o.beginn_mono)), zeit_ok=True)
        n += 1
    z = replace(z, zeilen=tuple(neue), offen=o, unsicher=False)
    if n == 0:
        return z, []
    return z, [Schreiben(False, "uhr"), _prot("INFO", "gehoert_uhr", "korrigiert", anzahl=n)]


def _takt(z: Zustand, jetzt: ev.Jetzt, k: Kontext) -> tuple[Zustand, list[Ausgabe]]:
    aus: list[Ausgabe] = []
    if z.unsicher and jetzt.zeit_ok:
        z, aus = _korrigiere_uhr(z, jetzt, k)
    o = z.offen
    if o is not None:
        if jetzt.mono - o.letzte_mono >= PAUSE_S:
            z, mehr = _beende(z, "pause", grund=z.grund)
            aus += mehr
        elif jetzt.mono - o.geschrieben_mono >= OFFEN_SCHREIBEN_S and _ganz_g(o) != o.geschrieben_g:
            aus.append(Schreiben(False, "offen"))
    if z.quittung_seit is not None and jetzt.mono - z.quittung_seit >= QUITTUNG_SCHREIBEN_S:
        aus.append(Schreiben(False, "quittung"))
    return z, aus


def _nach_schreiben(z: Zustand, aus: list[Ausgabe], jetzt: ev.Jetzt) -> Zustand:
    """Wer schreibt, schreibt den ganzen Stand: Quittungen sind dann auf der Platte, die offene Sitzung auch."""
    if not any(isinstance(a, Schreiben) for a in aus):
        return z
    o = z.offen
    if o is not None:
        o = replace(o, geschrieben_mono=jetzt.mono, geschrieben_g=_ganz_g(o))
    return replace(z, offen=o, quittung_seit=None)


def step(z: Zustand, e: ev.Ereignis | Quittung, jetzt: ev.Jetzt, k: Kontext) -> tuple[Zustand, tuple[Ausgabe, ...]]:
    """Ein äußeres Ereignis (oder eine ``Quittung`` von HA)."""
    aus: list[Ausgabe] = []
    if isinstance(e, ev.Takt):
        z, aus = _takt(z, jetzt, k)
    elif isinstance(e, ev.PlayerPosition):
        z, aus = _position(z, e, jetzt, k)
    elif isinstance(e, ev.FolgeZuEnde):
        z, aus = _folge_zu_ende(z, e)
    elif isinstance(e, ev.DienstEndet):
        z = replace(z, laeuft=False)
        z, aus = _beende(z, "dienst_ende", sync=True)
        if not aus:
            aus = [Schreiben(True, "dienst_ende")]
    elif isinstance(e, Quittung):
        weg = set(e.sitzungen)
        rest = tuple(r for r in z.zeilen if r["sitzung"] not in weg)
        if len(rest) != len(z.zeilen):
            z = replace(z, zeilen=rest, quittung_seit=z.quittung_seit if z.quittung_seit is not None else jetzt.mono)
    z = _nach_schreiben(z, aus, jetzt)
    return z, tuple(aus)


def step_befehl(z: Zustand, b: ev.Befehl, jetzt: ev.Jetzt, k: Kontext) -> tuple[Zustand, tuple[Ausgabe, ...]]:
    """Ein vom Kern ausgegebener Befehl (``Abspielen``, ``Pausieren``, ``Herunterfahren``)."""
    aus: list[Ausgabe] = []
    if isinstance(b, ev.Abspielen):
        z = replace(z, gen=b.gen, laeuft=True, grund=None)
    elif isinstance(b, ev.Pausieren):
        z = replace(z, laeuft=False, grund=b.grund)
        o = z.offen
        # Beginn einer Pause: den Stand der offenen Sitzung schreiben (Verlust bei Stromausfall höchstens 2 Minuten).
        # ``herunterfahren`` schreibt gleich der Befehl ``Herunterfahren`` (synchron).
        if o is not None and b.grund != "herunterfahren" and _ganz_g(o) >= 1 and _ganz_g(o) != o.geschrieben_g:
            aus.append(Schreiben(False, "pause"))
    elif isinstance(b, ev.Herunterfahren):
        z = replace(z, laeuft=False)
        z, aus = _beende(z, "herunterfahren", sync=True)
        if not aus:
            aus = [Schreiben(True, "herunterfahren")]
    z = _nach_schreiben(z, aus, jetzt)
    return z, tuple(aus)


# --------------------------------------------------------------------------
# Senden (Hilfen für ``ha``, rein)
# --------------------------------------------------------------------------


def zwischenstand(z: Zustand, jetzt: ev.Jetzt) -> tuple[Zustand, dict[str, Any] | None]:
    """Ist ein Zwischenstand fällig (Sitzung länger als 15 Minuten, alle 15 Minuten)? Dann die Zeile mit ``ende = teilweise``."""
    o = z.offen
    if o is None or jetzt.mono - o.zwischen_mono < ZWISCHENSTAND_S or jetzt.mono - o.beginn_mono < ZWISCHENSTAND_S:
        return z, None
    zeile = _zeile_aus(o, "teilweise", None)
    if zeile is None:
        return z, None
    return replace(z, offen=replace(o, zwischen_mono=jetzt.mono)), zeile


def baue_nachricht(zeilen: Sequence[Mapping[str, Any]], boot_id: str, jetzt: ev.Jetzt) -> dict[str, Any]:
    """``daten`` der Meldung ``gespielt`` (mqtt-v1 3.4): 1 bis 20 Sitzungen, ``boot_id`` und ``gesendet_boot_s`` beim Senden."""
    assert 1 <= len(zeilen) <= 20
    return {"boot_id": boot_id, "gesendet_boot_s": max(0, math.floor(jetzt.mono)), "sitzungen": [dict(r) for r in zeilen]}
