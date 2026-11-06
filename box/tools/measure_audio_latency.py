#!/usr/bin/env python3
"""Misst die Zeit vom Auflegen bis zum ersten Ton und vom Abheben bis zum Ende des Tons (AP 1.6).

Eingabe (offline, nur Standardbibliothek: ``wave`` und ``array``):

* das Ereignisprotokoll des Dienstes (JSON-Zeilen, am Mac die rotierende Datei ``tobibox.log`` samt
  ``tobibox.log.1`` ...; mehrere Dateien sind erlaubt, die Reihenfolge ist egal) und
* eine WAV-Aufnahme am Ausgang, z. B. vom Mikrofon des Macs (``sox``/``rec`` oder QuickTime
  mit ``afconvert``, siehe ``docs/timing.md``).

Ausgabe je Auflegen:  t(``aufgelegt`` im Protokoll) -> t(``abspielen``) -> t(erster Ton über der Schwelle)
und je Abheben:       t(``abgehoben``)              -> t(``pausieren``) -> t(Ton aus).
Alle Zeiten sind Millisekunden nach dem Eintrag ``aufgelegt`` bzw. ``abgehoben``. Dazu kommen Mittel-
und Höchstwerte und der Vergleich mit den Grenzen (Auflegen 1000 ms, Abheben 1500 ms; Zeitbudget im
Design, Baustein 1).

Wie Protokoll und Aufnahme zusammenpassen (eine Angabe ist Pflicht):

  --wav-start ZEIT      Wanduhr (UTC, ISO 8601, z. B. 2026-11-06T09:30:00.250Z), zu der die Aufnahme begann
  --wav-ende ZEIT       Wanduhr, zu der die Aufnahme endete (Start = Ende - Dauer)
  --sync ZEIT=SEKUNDEN  ein bekannter Augenblick: Zur Uhrzeit ZEIT im Protokoll liegt die Stelle SEKUNDEN
                        in der Aufnahme (z. B. ein Händeklatschen, dessen Zeit und Stelle man kennt)
  --wav-start auto      Start = Änderungszeit der Datei - Dauer (gilt für ``sox``/``rec``; Fehler etwa 0,2 s)
  --sync-start          Das Startgeräusch des Dienstes ist die Marke: erst die Aufnahme starten und still
                        sein, dann den Dienst starten. Der erste Ton der Aufnahme gehört zum Eintrag
                        ``bereit`` (plus ``--start-ton-ms``, Vorgabe 50 ms für den Start des Abspielers).
                        Das ist der Weg ohne Uhrzeit, auch für QuickTime-Aufnahmen. Fehler etwa 0,1 s.

Beispiele:

  python box/tools/measure_audio_latency.py box/var/log/tobibox.log* --wav aufnahme.wav \\
      --wav-start 2026-11-06T09:30:00.250Z
  python box/tools/measure_audio_latency.py tobibox.log --wav aufnahme.wav --sync 2026-11-06T09:30:07.120Z=7.35
  python box/tools/measure_audio_latency.py tobibox.log --wav aufnahme.wav --wav-start auto --json

Was das Protokoll liefern muss: ``aufgelegt`` und ``abgehoben`` (Baustein ``reader``) sowie ``abspielen``
und ``pausieren`` (Baustein ``app``), alle mit derselben Vorgangs-ID, Ebene INFO. Das Auflegen zählt nur,
wenn danach ein ``abspielen`` mit gleicher Vorgangs-ID folgt (Wiedermeldungen nach einem Leser-Neustart
starten nichts und werden übersprungen).

Mit ``--klick`` sucht das Werkzeug beim Auflegen zusätzlich den Klack, den das Aufsetzen des Tobies auf
das Gehäuse macht (das erste Geräusch in den 1,2 s vor ``aufgelegt``, vor dem es still war), und gibt
``Klack`` (Klack bis ``aufgelegt``: der Anteil der Firmware) und ``Gesamt`` (Klack bis zum ersten Ton) an.
Die Grenze von 1000 ms wird dann gegen ``Gesamt`` geprüft, sonst gegen die Zeit ab ``aufgelegt`` (zu
günstig). Beim Abheben beginnt die Firmware-Frist erst 1100 ms nach dem letzten Lesen (siehe docs/timing.md).

Ton und Stille: Der erste Ton ist das erste Fenster (``--fenster-ms``, Vorgabe 5 ms) mit Spitzenpegel über
der Schwelle, das zwei Fenster in Folge bleibt. ``Ton aus`` ist der Anfang einer Stille von mindestens
``--stille-ms`` (Vorgabe 150 ms). Die Schwelle (``--schwelle``) ist ein Anteil der Vollaussteuerung (0 bis 1)
oder ``auto`` (Vorgabe: das 6-Fache des Grundrauschens, mindestens 0,01). Hörspiele haben natürliche Pausen;
für die Messung darum Töne ohne Pausen verwenden (die Überraschungs-Serie, ein Dauerton).

Beenden mit Status 0, wenn keine Grenze überschritten ist, 3, wenn mindestens ein Wert über der Grenze
liegt, 2 bei Fehlern in den Eingaben. Mit ``--json`` erscheint das Ergebnis als JSON.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import wave
from array import array
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

GRENZE_AUFLEGEN_MS = 1000.0
GRENZE_ABHEBEN_MS = 1500.0
SUCHFENSTER_S = 5.0  # so lange nach dem Protokolleintrag wird nach dem Ton gesucht
VORLAUF_S = 0.05  # Ton, der schon vor dem Eintrag begann: „schon an“


class MessFehler(Exception):
    """Falsche oder unbrauchbare Eingabe (Status 2)."""


# --------------------------------------------------------------------------
# Protokoll
# --------------------------------------------------------------------------


def parse_zeit(text: str) -> float:
    """ISO 8601 (UTC, ``Z`` oder Versatz, Sekundenbruchteile erlaubt) -> Sekunden seit 1970."""
    t = text.strip()
    if t.endswith("Z") or t.endswith("z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except ValueError as e:
        raise MessFehler(f"Zeit nicht lesbar: {text!r} (erwartet z. B. 2026-11-06T09:30:00.250Z)") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


@dataclass(frozen=True)
class Eintrag:
    zeit: float  # Wanduhr, Sekunden seit 1970
    mono: float | None
    baustein: str
    ereignis: str
    vorgang: str | None
    daten: dict


def lese_protokoll(pfade: list[Path]) -> list[Eintrag]:
    """Alle JSON-Zeilen aller Dateien, nach Wanduhr sortiert. Kaputte Zeilen werden übersprungen."""
    eintraege: list[Eintrag] = []
    for pfad in pfade:
        try:
            text = Path(pfad).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise MessFehler(f"Protokoll nicht lesbar: {pfad}: {e}") from e
        for zeile in text.splitlines():
            if not zeile.startswith("{"):
                continue
            try:
                d = json.loads(zeile)
                eintraege.append(
                    Eintrag(
                        parse_zeit(d["zeit"]),
                        float(d["mono"]) if d.get("mono") is not None else None,
                        str(d.get("baustein", "")),
                        str(d["ereignis"]),
                        d.get("vorgang"),
                        d.get("daten") or {},
                    )
                )
            except (ValueError, KeyError, TypeError, MessFehler):
                continue
    eintraege.sort(key=lambda e: e.zeit)
    return eintraege


def _abstand_ms(a: Eintrag, b: Eintrag) -> float:
    """Zeit von ``a`` bis ``b`` in ms; die monotone Uhr, wenn beide eine haben (springt nie)."""
    if a.mono is not None and b.mono is not None:
        return (b.mono - a.mono) * 1000.0
    return (b.zeit - a.zeit) * 1000.0


@dataclass
class Vorgang:
    art: str  # "auflegen" oder "abheben"
    vorgang: str | None
    start: Eintrag  # aufgelegt / abgehoben
    befehl: Eintrag | None  # abspielen / pausieren
    uid: str | None = None
    grund: str | None = None


def finde_vorgaenge(eintraege: list[Eintrag]) -> list[Vorgang]:
    """Paart ``aufgelegt`` mit dem folgenden ``abspielen`` und ``abgehoben`` mit dem folgenden ``pausieren``."""
    ergebnis: list[Vorgang] = []
    starts = [(i, e) for i, e in enumerate(eintraege) if e.baustein == "reader" and e.ereignis in ("aufgelegt", "abgehoben")]
    for n, (i, e) in enumerate(starts):
        naechster = starts[n + 1][0] if n + 1 < len(starts) else len(eintraege)
        auflegen = e.ereignis == "aufgelegt"
        ziel = "abspielen" if auflegen else "pausieren"
        befehl = None
        for k in range(i + 1, naechster):
            c = eintraege[k]
            if c.ereignis != ziel or c.baustein != "app":
                continue
            if auflegen and c.vorgang != e.vorgang:
                continue
            if not auflegen and c.vorgang not in (e.vorgang, None):
                continue
            befehl = c
            break
        ergebnis.append(
            Vorgang(
                "auflegen" if auflegen else "abheben", e.vorgang, e, befehl,
                uid=e.daten.get("uid") if auflegen else None,
                grund=befehl.daten.get("grund") if (befehl and not auflegen) else None,
            )
        )
    return ergebnis


# --------------------------------------------------------------------------
# Aufnahme
# --------------------------------------------------------------------------


@dataclass
class Aufnahme:
    rate: int
    fenster_s: float
    pegel: list[float]  # Spitzenpegel je Fenster, 0 bis 1
    dauer_s: float

    def zeit_von(self, i: int) -> float:
        return i * self.fenster_s


def _spitzen(proben: array, fenster: int, norm: float, verschiebung: float = 0.0) -> list[float]:
    """Spitzenpegel (Betrag) je Fenster mit eingebauten ``min``/``max`` (schnell, auch für Minuten)."""
    ergebnis = []
    for i in range(0, len(proben), fenster):
        teil = proben[i : i + fenster]
        ergebnis.append(max(max(teil) - verschiebung, verschiebung - min(teil)) / norm)
    return ergebnis


def lese_wav(pfad: str | Path, fenster_ms: float = 5.0) -> Aufnahme:
    """WAV (PCM 8, 16, 24 oder 32 Bit, beliebige Kanäle) -> Spitzenpegel je Fenster (Kanäle: der lauteste)."""
    try:
        w = wave.open(str(pfad), "rb")
    except (OSError, wave.Error, EOFError) as e:
        raise MessFehler(f"WAV nicht lesbar: {pfad}: {e}") from e
    with w:
        kanaele, breite, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        roh = w.readframes(n)
    if breite not in (1, 2, 3, 4):
        raise MessFehler(f"WAV-Format nicht unterstützt: {breite * 8} Bit")
    if breite == 3:  # 24 Bit auf 32 Bit aufweiten (Byte 0 = 0)
        aus = bytearray(len(roh) // 3 * 4)
        aus[1::4] = roh[0::3]
        aus[2::4] = roh[1::3]
        aus[3::4] = roh[2::3]
        proben, norm, verschiebung = array("i"), 2147483648.0, 0.0
        proben.frombytes(bytes(aus))
    elif breite == 1:  # 8 Bit sind vorzeichenlos
        proben, norm, verschiebung = array("B"), 128.0, 128.0
        proben.frombytes(roh)
    else:
        proben, norm, verschiebung = array("h" if breite == 2 else "i"), (32768.0 if breite == 2 else 2147483648.0), 0.0
        proben.frombytes(roh[: len(roh) // breite * breite])
    if sys.byteorder == "big" and breite > 1:
        proben.byteswap()
    fenster = max(1, round(rate * fenster_ms / 1000.0))
    laenge = len(proben) // kanaele
    # je Fenster alle Kanäle: Proben sind verschachtelt, also Fenster in Proben = fenster * kanaele
    pegel = _spitzen(proben[: laenge * kanaele], fenster * kanaele, norm, verschiebung)
    return Aufnahme(rate, fenster / rate, pegel, laenge / rate if rate else 0.0)


def schwelle_auto(a: Aufnahme) -> float:
    """6-Faches des Grundrauschens (10. Perzentil der Pegel), mindestens 0,01."""
    if not a.pegel:
        return 0.01
    sortiert = sorted(a.pegel)
    rauschen = sortiert[int(len(sortiert) * 0.10)]
    return max(0.01, 6.0 * rauschen)


def erster_ton(a: Aufnahme, ab_s: float, bis_s: float, schwelle: float) -> tuple[str, float | None]:
    """Sucht den ersten Ton im Bereich ``[ab_s, bis_s)``.

    Ergebnis ``("schon_an", None)``, wenn schon im ersten Fenster Ton ist; ``("ton", t)`` mit der Aufnahmezeit
    des Fensterbeginns; ``("keiner", None)``, wenn nichts über der Schwelle liegt.
    """
    i0 = max(0, int(ab_s / a.fenster_s))
    i1 = min(len(a.pegel), int(bis_s / a.fenster_s) + 1)
    p = a.pegel
    for i in range(i0, i1):
        if p[i] >= schwelle and (i + 1 >= len(p) or p[i + 1] >= schwelle):
            return ("schon_an", None) if i == i0 else ("ton", a.zeit_von(i))
    return "keiner", None


def ton_aus(a: Aufnahme, ab_s: float, bis_s: float, schwelle: float, stille_s: float) -> tuple[str, float | None]:
    """Sucht den Beginn der ersten Stille von mindestens ``stille_s`` im Bereich ``[ab_s, bis_s)``.

    ``("schon_still", None)``, wenn im ersten Fenster schon Stille herrscht (nichts zu messen);
    ``("aus", t)`` mit dem Ende des letzten lauten Fensters; ``("bleibt", None)``, wenn der Ton nicht endet.
    """
    n_still = max(1, round(stille_s / a.fenster_s))
    i0 = max(0, int(ab_s / a.fenster_s))
    i1 = min(len(a.pegel), int(bis_s / a.fenster_s) + 1)
    p = a.pegel
    if i0 >= i1 or all(x < schwelle for x in p[i0 : i0 + n_still]):
        return "schon_still", None
    lauf = 0
    for i in range(i0, i1):
        if p[i] < schwelle:
            lauf += 1
            if lauf >= n_still:
                return "aus", a.zeit_von(i - lauf + 1)
        else:
            lauf = 0
    return "bleibt", None


# --------------------------------------------------------------------------
# Messung
# --------------------------------------------------------------------------


@dataclass
class Messwert:
    art: str
    vorgang: str | None
    zeit: str  # Wanduhr des Protokolleintrags
    befehl_ms: float | None  # bis abspielen / pausieren (Protokoll)
    ton_ms: float | None  # bis erster Ton / Ton aus (Aufnahme)
    hinweis: str = ""
    klick_ms: float | None = None  # nur mit --klick: vom Klack des Aufsetzens bis `aufgelegt`
    gesamt_ms: float | None = None  # nur mit --klick: vom Klack bis zum ersten Ton
    uid: str | None = None
    grund: str | None = None
    ueber_grenze: bool = False


@dataclass
class Ergebnis:
    schwelle: float
    wav_start: str
    werte: list[Messwert] = field(default_factory=list)
    zusammenfassung: dict = field(default_factory=dict)


def _iso(sek: float) -> str:
    return datetime.fromtimestamp(sek, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def messe(
    eintraege: list[Eintrag],
    a: Aufnahme,
    wav_start: float,
    schwelle: float,
    stille_s: float = 0.15,
    grenze_auflegen_ms: float = GRENZE_AUFLEGEN_MS,
    grenze_abheben_ms: float = GRENZE_ABHEBEN_MS,
    klick: bool = False,
) -> Ergebnis:
    erg = Ergebnis(schwelle, _iso(wav_start))
    for v in finde_vorgaenge(eintraege):
        auflegen = v.art == "auflegen"
        if auflegen and v.befehl is None:
            continue  # kein abspielen: Wiedermeldung, Aktionskarte, Knopf; es startet nichts
        t = v.start.zeit - wav_start  # Stelle in der Aufnahme
        m = Messwert(
            v.art, v.vorgang, _iso(v.start.zeit),
            _abstand_ms(v.start, v.befehl) if v.befehl else None, None, uid=v.uid, grund=v.grund,
        )
        if t < -VORLAUF_S or t > a.dauer_s:
            m.hinweis = "ausserhalb der Aufnahme"
            erg.werte.append(m)
            continue
        if not v.befehl:
            m.hinweis = "keine Pause im Protokoll (nichts spielte)"
        if auflegen:
            wie, ton = erster_ton(a, t - VORLAUF_S, t + SUCHFENSTER_S, schwelle)
            if wie == "ton":
                m.ton_ms = (ton - t) * 1000.0
                if klick:
                    _klick(m, a, t, schwelle, stille_s)
            else:
                m.hinweis = {"schon_an": "Ton war schon an (Messung nicht möglich)", "keiner": "kein Ton gefunden"}[wie]
            grenze = grenze_auflegen_ms
        else:
            wie, aus = ton_aus(a, t - VORLAUF_S, t + SUCHFENSTER_S, schwelle, stille_s)
            if wie == "aus":
                m.ton_ms = (aus - t) * 1000.0
            else:
                m.hinweis = m.hinweis or {
                    "schon_still": "es war schon still", "bleibt": "Ton endet nicht (Pause nicht zu hören)",
                }[wie]
            grenze = grenze_abheben_ms
        zu_pruefen = m.gesamt_ms if m.gesamt_ms is not None else m.ton_ms
        m.ueber_grenze = zu_pruefen is not None and zu_pruefen > grenze
        erg.werte.append(m)
    erg.zusammenfassung = _zusammenfassung(erg.werte, grenze_auflegen_ms, grenze_abheben_ms)
    return erg


KLICK_SUCHE_S = 1.2  # so weit vor `aufgelegt` wird nach dem Klack des Aufsetzens gesucht


def _klick(m: Messwert, a: Aufnahme, t: float, schwelle: float, stille_s: float) -> None:
    """Der Klack des Aufsetzens: das erste Geräusch in den letzten 1,2 s vor `aufgelegt`, dem Stille vorausging."""
    i1 = int(t / a.fenster_s)
    i0 = max(0, i1 - int(KLICK_SUCHE_S / a.fenster_s))
    n_still = max(1, round(stille_s / a.fenster_s))
    p = a.pegel
    for i in range(i0 + n_still, i1 + 1):
        if p[i] >= schwelle and all(x < schwelle for x in p[i - n_still : i]):
            m.klick_ms = (t - a.zeit_von(i)) * 1000.0
            m.gesamt_ms = m.klick_ms + (m.ton_ms or 0.0)
            return
    m.hinweis = (m.hinweis + "; " if m.hinweis else "") + "kein Klack vor `aufgelegt` gefunden"


def _zusammenfassung(werte: list[Messwert], g_auf: float, g_ab: float) -> dict:
    z: dict = {}
    for art, grenze in (("auflegen", g_auf), ("abheben", g_ab)):
        art_werte = [w for w in werte if w.art == art]
        if any(w.gesamt_ms is not None for w in art_werte):  # mit --klick zählt nur die Gesamtzeit
            ton = [w.gesamt_ms for w in art_werte if w.gesamt_ms is not None]
        else:
            ton = [w.ton_ms for w in art_werte if w.ton_ms is not None]
        befehl = [w.befehl_ms for w in werte if w.art == art and w.befehl_ms is not None]
        z[art] = {
            "anzahl": len([w for w in werte if w.art == art]),
            "gemessen": len(ton),
            "grenze_ms": grenze,
            "befehl_ms": _stat(befehl),
            "ton_ms": _stat(ton),
            "ueber_grenze": len([x for x in ton if x > grenze]),
        }
    return z


def _stat(xs: list[float]) -> dict | None:
    if not xs:
        return None
    return {"min": round(min(xs)), "median": round(statistics.median(xs)), "max": round(max(xs))}


def bestimme_wav_start(
    args: argparse.Namespace, a: Aufnahme, eintraege: list[Eintrag] | None = None, schwelle: float = 0.02
) -> float:
    """Wanduhr des Aufnahmebeginns aus genau einer der vier Angaben."""
    angaben = [x for x in (args.wav_start, args.wav_ende, args.sync, args.sync_start) if x]
    if len(angaben) != 1:
        raise MessFehler(
            "Genau eine Angabe zum Abgleich nötig: --wav-start, --wav-ende, --sync oder --sync-start (siehe --help)"
        )
    if args.sync_start:
        return _sync_start(args, a, eintraege or [], schwelle)
    if args.sync:
        zeit, _, sek = args.sync.rpartition("=")
        if not zeit:
            raise MessFehler("--sync erwartet ZEIT=SEKUNDEN, z. B. 2026-11-06T09:30:07.120Z=7.35")
        try:
            return parse_zeit(zeit) - float(sek)
        except ValueError as e:
            raise MessFehler(f"--sync: SEKUNDEN nicht lesbar: {sek!r}") from e
    if args.wav_ende:
        return parse_zeit(args.wav_ende) - a.dauer_s
    if args.wav_start == "auto":
        return Path(args.wav).stat().st_mtime - a.dauer_s
    return parse_zeit(args.wav_start)


def _sync_start(args: argparse.Namespace, a: Aufnahme, eintraege: list[Eintrag], schwelle: float) -> float:
    """Das Startgeräusch des Dienstes (Ton ``start`` gleich nach dem Eintrag ``bereit``) ist die Marke."""
    erste = min((e.zeit for e in eintraege if e.baustein == "reader" and e.ereignis in ("aufgelegt", "abgehoben")), default=None)
    bereit = [e for e in eintraege if e.baustein == "app" and e.ereignis == "bereit" and (erste is None or e.zeit <= erste)]
    if not bereit:
        raise MessFehler("--sync-start: im Protokoll steht kein Eintrag `bereit` vor dem ersten Auflegen")
    wie, t = erster_ton(a, 0.0, a.dauer_s, schwelle)
    if wie != "ton" or t is None:
        raise MessFehler("--sync-start: in der Aufnahme beginnt kein Ton nach einer Stille (Startgeräusch fehlt oder "
                         "die Aufnahme beginnt nicht still)")
    return bereit[-1].zeit + args.start_ton_ms / 1000.0 - t


# --------------------------------------------------------------------------
# Ausgabe
# --------------------------------------------------------------------------


def _ms(x: float | None) -> str:
    return "-" if x is None else f"{x:7.0f}"


def formatiere(erg: Ergebnis) -> str:
    zeilen = [
        f"Schwelle: {erg.schwelle:.3f} (Anteil der Vollaussteuerung); Aufnahme begann {erg.wav_start}",
        "",
        "Auflegen:  aufgelegt -> abspielen (Protokoll) -> erster Ton (Aufnahme), in ms nach `aufgelegt`",
        "Abheben:   abgehoben -> pausieren (Protokoll) -> Ton aus (Aufnahme), in ms nach `abgehoben`",
        "",
        f"{'Art':8} {'Vorgang':8} {'Uhrzeit (UTC)':24} {'Befehl':>7} {'Ton':>7} {'Klack':>7} {'Gesamt':>7}  Hinweis",
    ]
    for w in erg.werte:
        marke = "  ÜBER GRENZE" if w.ueber_grenze else ""
        zeilen.append(
            f"{w.art:8} {w.vorgang or '-':8} {w.zeit:24} {_ms(w.befehl_ms):>7} {_ms(w.ton_ms):>7} "
            f"{_ms(w.klick_ms):>7} {_ms(w.gesamt_ms):>7}  {w.hinweis}{marke}"
        )
    zeilen.append("")
    for art, titel in (("auflegen", "Auflegen"), ("abheben", "Abheben")):
        z = erg.zusammenfassung[art]
        t, b = z["ton_ms"], z["befehl_ms"]
        zeilen.append(
            f"{titel}: {z['gemessen']} von {z['anzahl']} gemessen; "
            + (f"{'Gesamt (mit Klack)' if any(w.gesamt_ms is not None for w in erg.werte if w.art == art) else 'Ton'} "
               f"min/median/max {t['min']}/{t['median']}/{t['max']} ms" if t else "kein Wert")
            + (f"; Befehl max {b['max']} ms" if b else "")
            + f"; Grenze {z['grenze_ms']:.0f} ms"
            + (f" -> {z['ueber_grenze']} ÜBER DER GRENZE (Rückfallregel in docs/timing.md)" if z["ueber_grenze"] else " -> ok" if t else "")
        )
    return "\n".join(zeilen)


def baue_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="measure_audio_latency.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("protokoll", nargs="+", type=Path, help="Ereignisprotokoll (JSON-Zeilen), auch mehrere Dateien")
    p.add_argument("--wav", required=True, help="WAV-Aufnahme am Ausgang")
    p.add_argument("--wav-start", help="Wanduhr (UTC, ISO 8601) des Aufnahmebeginns oder `auto` (Dateizeit minus Dauer)")
    p.add_argument("--wav-ende", help="Wanduhr (UTC, ISO 8601) des Aufnahmeendes")
    p.add_argument("--sync", help="ZEIT=SEKUNDEN: Protokollzeit und die zugehörige Stelle in der Aufnahme")
    p.add_argument("--sync-start", action="store_true",
                   help="Marke ist das Startgeräusch des Dienstes: Aufnahme starten, still sein, dann den Dienst starten")
    p.add_argument("--start-ton-ms", type=float, default=50.0,
                   help="Zeit vom Eintrag `bereit` bis zum Startgeräusch, nur mit --sync-start (50)")
    p.add_argument("--schwelle", default="auto", help="Anteil der Vollaussteuerung (0 bis 1) oder `auto` (Vorgabe)")
    p.add_argument("--stille-ms", type=float, default=150.0, help="so lange muss es still sein, damit der Ton als aus gilt (150)")
    p.add_argument("--fenster-ms", type=float, default=5.0, help="Fensterlänge der Pegelmessung in ms (5)")
    p.add_argument("--grenze-auflegen-ms", type=float, default=GRENZE_AUFLEGEN_MS)
    p.add_argument("--grenze-abheben-ms", type=float, default=GRENZE_ABHEBEN_MS)
    p.add_argument("--klick", action="store_true",
                   help="beim Auflegen den Klack des Aufsetzens suchen und die Gesamtzeit vom Klack an angeben")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON ausgeben")
    return p


def main(argv: list[str] | None = None) -> int:
    args = baue_parser().parse_args(argv)
    try:
        if args.fenster_ms <= 0 or args.stille_ms <= 0:
            raise MessFehler("--fenster-ms und --stille-ms müssen größer als 0 sein")
        eintraege = lese_protokoll(args.protokoll)
        if not eintraege:
            raise MessFehler("Im Protokoll steht keine lesbare JSON-Zeile")
        aufnahme = lese_wav(args.wav, args.fenster_ms)
        try:
            schwelle = schwelle_auto(aufnahme) if args.schwelle == "auto" else float(args.schwelle)
        except ValueError as e:
            raise MessFehler(f"--schwelle: Zahl oder `auto` erwartet, nicht {args.schwelle!r}") from e
        if not 0 < schwelle <= 1:
            raise MessFehler("--schwelle muss zwischen 0 und 1 liegen")
        wav_start = bestimme_wav_start(args, aufnahme, eintraege, schwelle)
        erg = messe(
            eintraege, aufnahme, wav_start, schwelle, args.stille_ms / 1000.0,
            args.grenze_auflegen_ms, args.grenze_abheben_ms, args.klick,
        )
    except MessFehler as e:
        print(f"measure_audio_latency: {e}", file=sys.stderr)
        return 2
    if not erg.werte:
        print("measure_audio_latency: keine Auflege- oder Abhebe-Vorgänge im Protokoll gefunden "
              "(Ebene INFO nötig, siehe --help)", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(asdict(erg), ensure_ascii=False, indent=2))
    else:
        print(formatiere(erg))
    return 3 if any(w.ueber_grenze for w in erg.werte) else 0


if __name__ == "__main__":
    raise SystemExit(main())
