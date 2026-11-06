"""Teilautomat Wiedergabe-Sitzung (``core-interface.md``, 5.2, 6.3, 9).

Reine Funktionen: kein Zugriff auf Dateien, Netz, Uhr oder Zufall. Der
Zustand ist unveränderlich; ``step`` gibt einen neuen Zustand und die Befehle
(und internen Ereignisse) zurück.

Die Zeigerregeln (nächste Folge, Track, Rücksprung, fehlende Folge) stehen in
``pointer.py`` (Abschnitt 6.3 des Vertrags). Ein Tobie zeigt auf eine Serie
(``ziel="serie"``, Serien-Zeiger) oder auf eine einzelne Folge (``ziel="folge"``,
Folgen-Zeiger) (Entscheidung F, 05.11.).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Literal

from . import events as ev
from . import pointer
from .events import Jetzt
from .volume import GRENZE_AUSBLENDEN, GRENZE_KOPFHOERER, rampe

LESER_FRIST_S = 3.0
MPD_FRIST_S = 5.0
RUECKSPRUNG_S = pointer.RUECKSPRUNG_S
SPEICHERN_PERIODISCH_S = pointer.SPEICHERN_PERIODISCH_S
STUMM_AUSBLENDEN_S = 3.0

_EPS = 1e-9

Modus = Literal["leer", "spielt", "pausiert", "beendet", "gehalten", "unbekannt"]


@dataclass(frozen=True, slots=True)
class Figur:
    """Die liegende Figur (auch Aktionskarten)."""

    vorgang: str
    uid: str | None  # None bei „gesperrt“
    art: Literal["serie", "unbekannt", "gesperrt", "aktion"]


@dataclass(frozen=True, slots=True)
class Zustand:
    modus: str = "leer"
    figur: Figur | None = None
    # Ziel, das für die Figur zuletzt gestartet wurde (auch Überraschungs-Serie)
    ziel: Literal["serie", "folge"] | None = None
    serie_id: str | None = None
    datei: str | None = None  # Name der aktuellen Folge
    index: int = 0
    track: int = 0
    position_s: float = 0.0  # im Track
    # eben beendete Folge (Serie, Name), nur im Zustand ``beendet`` (für Zurück)
    ende: tuple[str, str] | None = None
    konfig: ev.Konfig | None = None
    serien: tuple[ev.Serie, ...] = ()
    zeiger: Mapping[pointer.Schluessel, ev.Zeiger] = field(default_factory=dict)
    wirksam: int = 0
    kopfhoerer_grenze: int = 0  # bis zu den Einstellungen: nichts hörbar (Punkt 9.15)
    kopfhoerer_steckt: bool = False
    stumm: bool = False
    lernt: bool = False
    unbekannt_seit: float | None = None
    mpd_verloren: bool = False
    mpd_bis: float | None = None
    # (start_mono, von) beim sanften Ausblenden wegen „stumm“
    ausblenden: tuple[float, int] | None = None
    letzte_speicherung: float = 0.0
    hb_abweichungen: int = 0
    nach_hallo: bool = False
    gen: int = 0  # Wiedergabe-Generation: wächst mit jedem ``Abspielen``
    # Tobie, der beim Dienst-Neustart auflag: startet nicht von selbst (Entscheidung G, 06.11.)
    neustart_uid: str | None = None


def neuer_zustand() -> Zustand:
    return Zustand()


def kennzeichen(zustand: Zustand) -> str:
    return zustand.modus


def figur_liegt(zustand: Zustand) -> bool:
    return zustand.figur is not None


# --------------------------------------------------------------------------
# Hilfen
# --------------------------------------------------------------------------

Ausgabe = list  # Liste aus Befehlen und internen Ereignissen


def _prot(
    ebene: Literal["DEBUG", "INFO", "WARNING", "ERROR"],
    ereignis: str,
    ergebnis: str,
    vorgang: str | None = None,
    **daten: str | int | float | bool | None,
) -> ev.Protokoll:
    return ev.Protokoll("session", ebene, ereignis, ergebnis, vorgang, daten)


def _serie(z: Zustand, serie_id: str | None) -> ev.Serie | None:
    for s in z.serien:
        if s.id == serie_id:
            return s
    return None


def _ueberraschung(z: Zustand) -> ev.Serie | None:
    """Die einzige nicht leere Serie mit ``typ="ueberraschung"``, sonst ``None``."""
    kandidaten = [s for s in z.serien if s.typ == "ueberraschung"]
    if len(kandidaten) == 1 and kandidaten[0].folgen:
        return kandidaten[0]
    return None


def _ort(z: Zustand, serie: ev.Serie, art: str, folge: str | None) -> pointer.Ort | None:
    """Start-Ort des Ziels am gespeicherten Zeiger (``None``: leere Serie bzw. Folge fehlt)."""
    if art == "folge" and folge is not None:
        return pointer.ort_der_folge(serie, folge, z.zeiger.get(pointer.schluessel("folge", serie.id, folge)))
    return pointer.ort_am_zeiger(serie, z.zeiger.get(pointer.schluessel("serie", serie.id, "")))


def _abspielen(
    serie: ev.Serie, datei: str, track: int, position_s: float, vorgang: str | None, gen: int
) -> ev.Abspielen:
    return ev.Abspielen(
        serie.id, serie.ordner, datei, pointer.tracks_von(serie, datei), track, position_s, vorgang, gen
    )


def _veraltet(z: Zustand, e: ev.TrackWechsel | ev.FolgeZuEnde | ev.PlayerPosition) -> bool:
    """Ereignis einer früheren Wiedergabe (``gen`` weicht ab): ignorieren."""
    return e.gen is not None and e.gen != z.gen


def _speichern(z: Zustand, grund: str, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """``ZeigerSpeichern`` für das aktuelle Ziel, nur wenn der Zeiger sich ändert."""
    if z.serie_id is None or z.datei is None or z.ziel is None:
        return z, []
    art = z.ziel
    index = z.index if art == "serie" else None
    key = pointer.schluessel(art, z.serie_id, z.datei)
    alt = z.zeiger.get(key)
    if pointer.unveraendert(alt, art, z.datei, index, z.track, z.position_s):
        return z, []
    neu = pointer.neuer_zeiger(alt, art, z.serie_id, z.datei, index, z.track, z.position_s)
    zeiger = dict(z.zeiger)
    zeiger[key] = neu
    cmd = ev.ZeigerSpeichern(art, z.serie_id, z.datei, index, z.track, neu.position_s, grund)  # type: ignore[arg-type]
    return replace(z, zeiger=zeiger, letzte_speicherung=jetzt.mono), [cmd]


def _grenze_weg(z: Zustand) -> Ausgabe:
    return [ev.GrenzeGesetzt(GRENZE_AUSBLENDEN, None)] if z.ausblenden is not None else []


def _ruhe(z: Zustand, **felder: object) -> Zustand:
    """Zustand für „es läuft nichts mehr“: Fristen und Ausblenden verwerfen."""
    felder.setdefault("ende", None)
    return replace(z, unbekannt_seit=None, mpd_verloren=False, mpd_bis=None, ausblenden=None, **felder)


def _start(
    z: Zustand,
    serie: ev.Serie,
    vorgang: str | None,
    jetzt: Jetzt,
    art: str = "serie",
    folge: str | None = None,
) -> tuple[Zustand, Ausgabe]:
    """Ziel am Zeiger starten (Zeiger laden, Rücksprung, ``Abspielen``).

    ``art="serie"``: Serien-Zeiger der Serie; ``art="folge"``: Folgen-Zeiger der Folge ``folge``.
    """
    ort = _ort(z, serie, art, folge)
    if ort is None:
        out: Ausgabe = [
            ev.TonSpielen("fehler"),
            _prot("ERROR", "serie_leer", "fehlerton", vorgang, serie=serie.id),
        ]
        return _ruhe(z, modus="pausiert", ziel=None, serie_id=None, datei=None), out
    out = []
    if ort.folge_fehlte:
        out.append(_prot("WARNING", "zeiger_folge_fehlt", "naechste_folge", vorgang, serie=serie.id, datei=ort.datei))
    if ort.track_fehlte:
        out.append(_prot("WARNING", "zeiger_track_fehlt", "track_0", vorgang, serie=serie.id, datei=ort.datei))
    out.append(_abspielen(serie, ort.datei, ort.track, ort.position_s, vorgang, z.gen + 1))
    z = _ruhe(
        z,
        gen=z.gen + 1,
        modus="spielt",
        ziel=art,
        serie_id=serie.id,
        datei=ort.datei,
        index=ort.index,
        track=ort.track,
        position_s=ort.position_s,
        letzte_speicherung=jetzt.mono,
    )
    return z, out


def _ziel_start(z: Zustand, vorgang: str | None, jetzt: Jetzt) -> tuple[Zustand, Ausgabe] | None:
    """Das zuletzt gespielte Ziel (``z.ziel``, ``z.serie_id``, ``z.datei``) erneut am Zeiger starten."""
    serie = _serie(z, z.serie_id)
    if serie is None or z.ziel is None:
        return None
    return _start(z, serie, vorgang, jetzt, z.ziel, z.datei if z.ziel == "folge" else None)


def _stumm_hinweis(z: Zustand, modus: str) -> tuple[Zustand, Ausgabe]:
    return replace(z, modus=modus), [ev.TonSpielen("hinweis")]


# --------------------------------------------------------------------------
# Auflegen (Figur wird gemeldet)
# --------------------------------------------------------------------------


def _auflegen(z: Zustand, uid: str | None, vorgang: str, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Neue Figur in einem Zustand ohne laufende Wiedergabe behandeln."""
    zuo = z.konfig.zuordnungen.get(uid) if (uid is not None and z.konfig is not None) else None
    # Dienst-Neustart (Entscheidung G, 06.11.): der Tobie, der schon vorher lag, startet nicht
    neustart = uid is not None and uid == z.neustart_uid and z.modus == "leer"
    z = replace(z, neustart_uid=None)
    if zuo is not None and zuo.typ == "aktion" and zuo.aktion is not None:
        return replace(z, figur=Figur(vorgang, uid, "aktion")), [ev.AktionAusgeloest(zuo.aktion, vorgang)]

    out: Ausgabe = []
    serie: ev.Serie | None
    ziel_art = "serie"
    folge: str | None = None
    if uid is None:
        art: Literal["serie", "unbekannt", "gesperrt", "aktion"] = "gesperrt"
        serie = _ueberraschung(z)
    elif zuo is None:
        art = "unbekannt"
        out.append(ev.Melden("unbekannt", uid, None))
        serie = _ueberraschung(z)
    else:
        art = "serie"
        serie = _serie(z, zuo.serie_id)
        if serie is None:
            out.append(_prot("WARNING", "serie_fehlt", "ueberraschung", vorgang, uid=uid, serie=zuo.serie_id))
            serie = _ueberraschung(z)
        elif zuo.typ == "folge":
            if zuo.folge is not None and zuo.folge in serie.folgen:
                ziel_art, folge = "folge", zuo.folge
            else:
                out.append(
                    _prot("WARNING", "folge_fehlt", "ueberraschung", vorgang, uid=uid, serie=zuo.serie_id, folge=zuo.folge)
                )
                serie = _ueberraschung(z)
    z = replace(z, figur=Figur(vorgang, uid, art))

    if z.stumm or (neustart and serie is not None):
        # „stumm“: gehalten, Hinweiston. Dienst-Neustart: pausiert, still (Zeiger bleibt, Hauptknopf spielt)
        if neustart:
            modus = "pausiert"
        else:
            modus = z.modus if z.modus in ("beendet", "gehalten") else "gehalten"
        z = replace(z, modus=modus)
        if serie is not None:
            # Felder folgen dem gespeicherten Zeiger des neuen Ziels (nie Reste eines anderen)
            ort = _ort(z, serie, ziel_art, folge)
            if ort is not None:
                z = replace(
                    z, ziel=ziel_art, serie_id=serie.id, datei=ort.datei, index=ort.index,  # type: ignore[arg-type]
                    track=ort.track, position_s=ort.position_s,
                )
            else:
                z = replace(z, ziel=ziel_art, serie_id=serie.id, datei=None, index=0, track=0, position_s=0.0)  # type: ignore[arg-type]
        if not neustart:
            out.append(ev.TonSpielen("hinweis"))
        else:
            out.append(_prot("INFO", "dienst_neustart", "pausiert", vorgang, uid=uid))
        return z, out

    if serie is None:
        out.append(ev.TonSpielen("fehler"))
        out.append(_prot("ERROR", "ueberraschung_fehlt", "fehlerton", vorgang, art=art))
        return _ruhe(z, modus="pausiert", ziel=None, serie_id=None, datei=None), out

    if art == "unbekannt":
        out.append(ev.TonSpielen("unbekannt"))
    z, start = _start(z, serie, vorgang, jetzt, ziel_art, folge)
    return z, out + start


def _figur_gemeldet(z: Zustand, uid: str | None, vorgang: str, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    f = z.figur
    # Wiedermeldung derselben vorgang-ID (9.1, 9.2)
    if f is not None and f.vorgang == vorgang:
        if z.modus == "unbekannt":
            return _leser_zurueck(z, jetzt)
        return z, []

    out: Ausgabe = []
    if z.modus == "unbekannt":
        out.append(ev.Pausieren("leser_unbekannt"))
        z, sp = _speichern(z, "figurwechsel", jetzt)
        out += sp
        z = _ruhe(z, modus="pausiert")
    elif z.modus == "spielt":
        if f is not None and f.uid == uid:
            # 9.4: dieselbe Figur nach verlorenem REMOVED, nichts geschieht
            return replace(z, figur=replace(f, vorgang=vorgang)), []
        out += _grenze_weg(z)
        z, sp = _speichern(z, "figurwechsel", jetzt)
        out += sp
        z = _ruhe(z, modus="pausiert")
        z, neu = _auflegen(z, uid, vorgang, jetzt)
        if not any(isinstance(c, ev.Abspielen) for c in neu):
            out.append(ev.Pausieren("abgehoben"))
        return z, out + neu
    z, neu = _auflegen(z, uid, vorgang, jetzt)
    return z, out + neu


def _leser_zurueck(z: Zustand, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Gleiche Figur kam innerhalb der Frist zurück (9.2)."""
    if z.unbekannt_seit is not None and jetzt.mono - z.unbekannt_seit >= LESER_FRIST_S - _EPS:
        return _pausiere(z, "leser_unbekannt", "pause", jetzt)  # Frist schon abgelaufen (9.2)
    if z.mpd_verloren:
        return _ruhe(z, modus="pausiert"), [_prot("WARNING", "leser_zurueck_mpd_weg", "pausiert", z.figur.vorgang if z.figur else None)]
    z = replace(z, modus="spielt", unbekannt_seit=None)
    if z.stumm:
        z = replace(z, ausblenden=(jetzt.mono, z.wirksam))
    return z, []


def _aufgelegt(z: Zustand, e: ev.Aufgelegt, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return _figur_gemeldet(z, e.uid, e.vorgang, jetzt)


def _gesperrt(z: Zustand, e: ev.Gesperrt, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return _figur_gemeldet(z, None, e.vorgang, jetzt)


def _abgehoben(z: Zustand, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if z.figur is None:
        return z, []
    out: Ausgabe = []
    z = replace(z, figur=None, hb_abweichungen=0, neustart_uid=None)
    if z.modus in ("spielt", "unbekannt"):
        out += _grenze_weg(z)
        out.append(ev.Pausieren("abgehoben"))
        z, sp = _speichern(z, "pause", jetzt)
        out += sp
        z = _ruhe(z, modus="pausiert")
    elif z.modus in ("beendet", "gehalten"):
        z = replace(z, modus="pausiert")
    return z, out


def _abgehoben_ereignis(z: Zustand, e: ev.Abgehoben, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return _abgehoben(z, jetzt)


# --------------------------------------------------------------------------
# Leser
# --------------------------------------------------------------------------


def _leser_ausfall(z: Zustand, e: ev.Ereignis, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    z = replace(z, nach_hallo=isinstance(e, ev.LeserHallo), hb_abweichungen=0)
    if z.modus == "spielt" and z.ausblenden is None:
        z = replace(z, modus="unbekannt", unbekannt_seit=jetzt.mono, mpd_bis=None)
    return z, []


def _herzschlag(z: Zustand, e: ev.LeserHerzschlag, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    liegt = z.figur is not None
    if not liegt and not e.present and z.neustart_uid is not None:
        z = replace(z, neustart_uid=None)  # der Tobie vom Neustart liegt nicht mehr da
    if z.nach_hallo:
        z = replace(z, nach_hallo=False)
        if not e.present and liegt:
            # die Figur wurde im Ausfall abgehoben (9.3, „Danach“)
            return _abgehoben(replace(z, hb_abweichungen=0), jetzt)
    if e.present != liegt:
        n = z.hb_abweichungen + 1
        if n >= 2:
            return replace(z, hb_abweichungen=0), [ev.LeserPing()]
        return replace(z, hb_abweichungen=n), []
    return replace(z, hb_abweichungen=0), []


# --------------------------------------------------------------------------
# Player
# --------------------------------------------------------------------------


def _position(z: Zustand, e: ev.PlayerPosition, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Position nur übernehmen, wenn MPD läuft (``spielt``, ``unbekannt``) und Serie,
    Folge und Track zum Zeiger passen; sonst ignorieren (6.3, Entscheidung F)."""
    if (
        z.modus in ("spielt", "unbekannt")
        and not _veraltet(z, e)
        and e.serie_id == z.serie_id
        and e.datei == z.datei
        and e.track == z.track
    ):
        return replace(z, position_s=e.position_s), []
    return z, []


def _track_wechsel(z: Zustand, e: ev.TrackWechsel, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """MPD spielt mit dem nächsten Track derselben Folge weiter: Zeiger nachführen, keine Pause.

    Gilt in jedem Zustand mit laufendem MPD (``spielt`` auch beim Ausblenden und in der
    MPD-Frist, ``unbekannt``); sonst ignoriert."""
    if z.modus not in ("spielt", "unbekannt"):
        return z, []
    if _veraltet(z, e):
        return z, [_prot("DEBUG", "track_wechsel_veraltet", "ignoriert", z.figur.vorgang if z.figur else None, gen=e.gen, aktuell=z.gen)]
    vorgang = z.figur.vorgang if z.figur else None
    serie = _serie(z, z.serie_id)
    n = len(pointer.tracks_von(serie, z.datei)) if serie is not None and z.datei is not None else 0
    if e.serie_id != z.serie_id or e.datei != z.datei or not z.track < e.track < n:
        return z, [_prot("WARNING", "track_wechsel_fremd", "ignoriert", vorgang, serie=e.serie_id, datei=e.datei, track=e.track)]
    z = replace(z, track=e.track, position_s=0.0)
    return _speichern(z, "trackwechsel", jetzt)


def _folge_zu_ende(z: Zustand, e: ev.FolgeZuEnde, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Letzter Track zu Ende: Pause, Zeiger je Ziel (Serie: nächste Folge; Folge: zurück auf den Anfang).

    Gilt in jedem Zustand mit laufendem MPD. In ``spielt`` (auch in der MPD-Frist) und in
    ``unbekannt`` folgt ``beendet``; beim Ausblenden wegen „stumm“ folgt ``gehalten``."""
    if z.modus not in ("spielt", "unbekannt"):
        return z, []
    if _veraltet(z, e):
        return z, [_prot("DEBUG", "folge_zu_ende_veraltet", "ignoriert", z.figur.vorgang if z.figur else None, gen=e.gen, aktuell=z.gen)]
    if e.serie_id != z.serie_id or e.datei != z.datei:
        return z, [_prot("WARNING", "folge_zu_ende_fremd", "ignoriert", z.figur.vorgang if z.figur else None, serie=e.serie_id, datei=e.datei)]
    out: Ausgabe = _grenze_weg(z)
    serie = _serie(z, z.serie_id)
    ausblenden = z.ausblenden is not None
    beendete = (z.serie_id, e.datei)
    z = _ruhe(z, modus="gehalten" if ausblenden else "beendet", ende=None if ausblenden else beendete)
    if serie is not None and serie.folgen:
        if z.ziel == "folge":
            z = replace(z, track=0, position_s=0.0)
        else:
            datei, nxt = pointer.naechste_folge(serie, e.datei, z.index)
            z = replace(z, datei=datei, index=nxt, track=0, position_s=0.0)
        z, sp = _speichern(z, "folgenende", jetzt)
        out += sp
    out.append(ev.Pausieren("folgenende"))
    return z, out


def _player_fehler(z: Zustand, e: ev.PlayerFehler, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    vorgang = z.figur.vorgang if z.figur else None
    daten = {"art": e.art, "detail": e.detail, "serie": e.serie_id, "datei": e.datei}
    if z.modus not in ("spielt", "unbekannt"):
        return z, [ev.Protokoll("session", "WARNING", "player_fehler", "ignoriert", vorgang, daten)]
    if (e.datei is not None and e.datei != z.datei) or (e.serie_id is not None and e.serie_id != z.serie_id):
        return z, [ev.Protokoll("session", "WARNING", "player_fehler", "fremde_datei", vorgang, daten)]
    if z.mpd_bis is not None:
        return z, [ev.Protokoll("session", "ERROR", "player_fehler", "in_mpd_frist", vorgang, daten)]
    out: Ausgabe = _grenze_weg(z)
    out.append(ev.TonSpielen("fehler"))
    out.append(ev.Pausieren("fehler"))
    out.append(ev.Protokoll("session", "ERROR", "player_fehler", "pausiert", vorgang, daten))
    serie = _serie(z, z.serie_id)
    if e.art in ("datei_fehlt", "datei_unlesbar") and serie is not None and serie.folgen:
        if z.ziel == "folge":  # Folgen-Zeiger: dieselbe Folge, Track 0, Position 0
            z = replace(z, track=0, position_s=0.0)
        else:
            datei, nxt = pointer.naechste_folge(serie, z.datei or "", z.index)
            z = replace(z, datei=datei, index=nxt, track=0, position_s=0.0)
        z, sp = _speichern(z, "pause", jetzt)
        out += sp
    return _ruhe(z, modus="pausiert"), out


def _verbindung(z: Zustand, e: ev.PlayerVerbindung, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    vorgang = z.figur.vorgang if z.figur else None
    if z.modus == "unbekannt":
        if not e.ok:
            z = replace(z, mpd_verloren=True)
        return z, [ev.Protokoll("session", "ERROR" if not e.ok else "INFO", "mpd_verbindung", "nur_protokoll", vorgang, {"ok": e.ok})]
    if z.modus != "spielt":
        out: Ausgabe = [ev.Protokoll("session", "WARNING" if not e.ok else "INFO", "mpd_verbindung", "nur_protokoll", vorgang, {"ok": e.ok})]
        if e.ok:
            out.append(ev.Pausieren("fehler"))  # defensiv: MPD ist neu, nichts darf spielen (idempotent)
        return z, out
    if not e.ok:
        if z.mpd_bis is not None or z.ausblenden is not None:
            return replace(z, mpd_verloren=True), [ev.Protokoll("session", "ERROR", "mpd_verbindung", "weg", vorgang, {"ok": False})]
        out = [ev.Protokoll("session", "ERROR", "mpd_verloren", "frist_laeuft", vorgang, {"frist_s": MPD_FRIST_S})]
        z, sp = _speichern(z, "pause", jetzt)
        return replace(z, mpd_verloren=True, mpd_bis=jetzt.mono + MPD_FRIST_S), out + sp
    # ok=True
    if not z.mpd_verloren or z.mpd_bis is None:
        return z, [ev.Protokoll("session", "INFO", "mpd_verbindung", "ok", vorgang, {"ok": True})]
    serie = _serie(z, z.serie_id)
    if jetzt.mono < z.mpd_bis and z.figur is not None and serie is not None and z.datei is not None:
        pos = max(0.0, z.position_s - RUECKSPRUNG_S)
        ausgang = "kopfhoerer" if z.kopfhoerer_steckt else "lautsprecher"
        out = [
            ev.AusgangWaehlen(ausgang),
            _abspielen(serie, z.datei, z.track, pos, z.figur.vorgang, z.gen + 1),
        ]
        return replace(z, mpd_verloren=False, mpd_bis=None, position_s=pos, letzte_speicherung=jetzt.mono, gen=z.gen + 1), out
    return _mpd_frist_ende(z)


def _mpd_frist_ende(z: Zustand) -> tuple[Zustand, Ausgabe]:
    return _ruhe(z, modus="pausiert"), [ev.Pausieren("fehler")]


# --------------------------------------------------------------------------
# Bedienung
# --------------------------------------------------------------------------


def _pausiere(z: Zustand, grund: str, speicher_grund: str, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    out: Ausgabe = _grenze_weg(z)
    out.append(ev.Pausieren(grund))  # type: ignore[arg-type]
    z, sp = _speichern(z, speicher_grund, jetzt)
    return _ruhe(z, modus="pausiert"), out + sp


def _hauptknopf(z: Zustand, e: ev.Hauptknopf, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if e.art != "kurz":
        return z, []  # Hauptknopf lang gehört dem Teilautomat `idle`
    if z.modus == "spielt":
        return _pausiere(z, "knopf", "pause", jetzt)
    if z.modus in ("pausiert", "beendet", "gehalten"):
        if z.stumm:
            return z, [ev.TonSpielen("hinweis")]
        if z.modus == "gehalten":
            return z, []
        return _ziel_start(z, z.figur.vorgang if z.figur else None, jetzt) or (z, [])
    return z, []


def _springen(z: Zustand, delta: int, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """``Weiter`` (+1) und ``Zurueck`` (-1), nach Track innerhalb der Folge (9.12)."""
    vorgang = z.figur.vorgang if z.figur else None
    if z.modus == "spielt" and (z.ausblenden is not None or z.mpd_bis is not None):
        # während des Ausblendens und der MPD-Frist ignoriert (9.10, 9.12)
        return z, [_prot("INFO", "springen", "ignoriert", vorgang, delta=delta)]
    if z.modus not in ("spielt", "pausiert", "beendet", "gehalten"):
        return z, []
    if z.modus in ("pausiert", "beendet", "gehalten") and z.stumm:
        return z, [ev.TonSpielen("hinweis")]
    if z.modus == "gehalten":
        return z, []
    serie = _serie(z, z.serie_id)
    if serie is None or not serie.folgen or z.ziel is None or z.datei is None:
        return z, []
    if z.modus == "beendet":
        if delta > 0:
            # Weiter = Hauptknopf kurz: ab dem Zeiger des Ziels (9.12)
            return _ziel_start(z, vorgang, jetzt) or (z, [])
        return _zurueck_nach_ende(z, vorgang, jetzt)
    if delta > 0:
        sprung = pointer.weiter(serie, z.ziel, z.datei, z.index, z.track)
        if sprung is None:  # Folgen-Tobie am letzten Track: nur Hinweiston
            return z, [ev.TonSpielen("hinweis")]
    else:
        sprung = pointer.zurueck(z.datei, z.index, z.track, z.position_s)
    z = replace(z, datei=sprung.datei, index=sprung.index, track=sprung.track, position_s=0.0)
    z, sp = _speichern(z, sprung.grund, jetzt)
    z = _ruhe(z, modus="spielt", letzte_speicherung=jetzt.mono, gen=z.gen + 1)
    return z, sp + [_abspielen(serie, sprung.datei, sprung.track, 0.0, vorgang, z.gen)]


def _zurueck_nach_ende(z: Zustand, vorgang: str | None, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """``Zurueck`` in ``beendet``: die eben beendete Folge von vorn (einzige Quelle: ``z.ende``)."""
    serie = _serie(z, z.ende[0]) if z.ende is not None else None
    if serie is None or z.ende is None or z.ende[1] not in serie.folgen:
        return z, [ev.TonSpielen("hinweis"), _prot("WARNING", "zurueck_folge_fehlt", "hinweis", vorgang)]
    name = z.ende[1]
    z = replace(z, serie_id=serie.id, datei=name, index=serie.folgen.index(name), track=0, position_s=0.0)
    z, sp = _speichern(z, "zurueck", jetzt)
    z = _ruhe(z, modus="spielt", letzte_speicherung=jetzt.mono, gen=z.gen + 1)
    return z, sp + [_abspielen(serie, name, 0, 0.0, vorgang, z.gen)]


def _weiter(z: Zustand, e: ev.Weiter, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return _springen(z, +1, jetzt)


def _zurueck(z: Zustand, e: ev.Zurueck, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return _springen(z, -1, jetzt)


def _kopfhoerer(z: Zustand, e: ev.Kopfhoerer, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    grenze = z.kopfhoerer_grenze if e.steckt else None
    ausgang = "kopfhoerer" if e.steckt else "lautsprecher"
    return replace(z, kopfhoerer_steckt=e.steckt), [
        ev.GrenzeGesetzt(GRENZE_KOPFHOERER, grenze),
        ev.AusgangWaehlen(ausgang),
    ]


# --------------------------------------------------------------------------
# Daten
# --------------------------------------------------------------------------


def _einstellungen(z: Zustand, e: ev.GeraeteEinstellungen, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    z = replace(z, kopfhoerer_grenze=e.lautstaerke_kopfhoerer, neustart_uid=e.neustart_uid)
    if z.kopfhoerer_steckt:
        return z, [ev.GrenzeGesetzt(GRENZE_KOPFHOERER, e.lautstaerke_kopfhoerer)]
    return z, []


def _bibliothek(z: Zustand, e: ev.BibliothekGeladen, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return replace(z, serien=e.serien), []


def _resume(z: Zustand, e: ev.ResumeGeladen, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return replace(z, zeiger={pointer.schluessel_von(zg): zg for zg in e.zeiger}), []


def _bereit(z: Zustand, e: ev.Bereit, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return z, [ev.TonSpielen("start")]


def _konfig(z: Zustand, e: ev.KonfigGeladen, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Neue Konfiguration; bei liegender Figur gilt 9.14 (Ziel ``serie`` oder ``folge``)."""
    z = replace(z, konfig=e.konfig)
    f = z.figur
    if f is None or f.uid is None or f.art == "aktion":
        return z, []
    zuo = e.konfig.zuordnungen.get(f.uid)
    if zuo is None or zuo.typ not in ("serie", "folge"):
        return z, []
    serie = _serie(z, zuo.serie_id)
    if serie is None:
        return z, []  # „Serie fehlt“: nichts (6.3)
    folge: str | None = None
    if zuo.typ == "folge":
        if zuo.folge is None or zuo.folge not in serie.folgen:
            return z, []  # „Folge fehlt“: nichts (6.3)
        folge = zuo.folge
    # nicht das zuletzt gestartete Ziel (anderer Typ, andere Serie oder andere Folge)?
    if z.ziel == zuo.typ and z.serie_id == serie.id and (folge is None or z.datei == folge):
        return z, []
    z = replace(z, figur=replace(f, art="serie"))
    if z.modus == "spielt" and z.ausblenden is None:
        z, sp = _speichern(z, "figurwechsel", jetzt)
        z, start = _start(z, serie, f.vorgang, jetzt, zuo.typ, folge)
        return z, sp + start
    if z.modus in ("pausiert", "beendet"):
        if z.stumm:
            return z, [ev.TonSpielen("hinweis")]
        return _start(z, serie, f.vorgang, jetzt, zuo.typ, folge)
    return z, []


def _lernen(z: Zustand, e: ev.LernenGeaendert, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return replace(z, lernt=e.aktiv), []


def _lautstaerke(z: Zustand, e: ev.LautstaerkeGeaendert, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return replace(z, wirksam=e.wirksam), []


# --------------------------------------------------------------------------
# Ruhe und Strom (Eingänge von quiet, bedtime, idle)
# --------------------------------------------------------------------------


def _stumm_beginnt(z: Zustand, e: ev.StummBeginnt, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    z = replace(z, stumm=True)
    if z.modus == "spielt" and z.ausblenden is None:
        if z.mpd_verloren:
            # MPD weg: kein Ausblenden, der Zeiger ist gespeichert (9.10)
            return _ruhe(z, modus="gehalten"), []
        return replace(z, ausblenden=(jetzt.mono, z.wirksam)), []
    return z, []


def _stumm_endet(z: Zustand, e: ev.StummEndet, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    z = replace(z, stumm=False)
    if z.modus == "gehalten":
        z = replace(z, modus="pausiert")
    return z, []


def _gute_nacht_ende(z: Zustand, e: ev.GuteNachtEnde, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if z.modus in ("spielt", "unbekannt"):
        return _pausiere(z, "gute_nacht", "pause", jetzt)
    return z, []


def _herunterfahren(z: Zustand, e: ev.HerunterfahrenAngefordert, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if z.modus in ("spielt", "unbekannt"):
        return _pausiere(z, "herunterfahren", "herunterfahren", jetzt)
    return z, []


def _dienst_endet(z: Zustand, e: ev.DienstEndet, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Dienst-Ende: pausieren und Zeiger sichern, aber das Gerät nicht herunterfahren."""
    if z.modus in ("spielt", "unbekannt"):
        return _pausiere(z, "herunterfahren", "herunterfahren", jetzt)
    return z, []


# --------------------------------------------------------------------------
# Takt
# --------------------------------------------------------------------------


def _takt(z: Zustand, e: ev.Takt, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if z.modus == "unbekannt":
        if z.unbekannt_seit is not None and jetzt.mono - z.unbekannt_seit >= LESER_FRIST_S - _EPS:
            return _pausiere(z, "leser_unbekannt", "pause", jetzt)
        return z, []
    if z.modus != "spielt":
        return z, []
    if z.ausblenden is not None:
        start, von = z.ausblenden
        if jetzt.mono - start >= STUMM_AUSBLENDEN_S - _EPS:
            out: Ausgabe = [ev.Pausieren("stumm")]
            z, sp = _speichern(z, "pause", jetzt)
            out += sp
            out.append(ev.GrenzeGesetzt(GRENZE_AUSBLENDEN, None))
            return _ruhe(z, modus="gehalten" if z.stumm else "pausiert"), out
        return z, [ev.GrenzeGesetzt(GRENZE_AUSBLENDEN, rampe(von, 0, start, STUMM_AUSBLENDEN_S, jetzt.mono))]
    if z.mpd_bis is not None:
        if jetzt.mono >= z.mpd_bis - _EPS:
            return _mpd_frist_ende(z)
        return z, []
    if pointer.periodisch_faellig(z.letzte_speicherung, jetzt.mono):
        return _speichern(z, "periodisch", jetzt)
    return z, []


# --------------------------------------------------------------------------
# step
# --------------------------------------------------------------------------

_Handler = Callable[[Zustand, "ev.Ereignis", Jetzt], tuple[Zustand, Ausgabe]]

_HANDLER: dict[type, _Handler] = {
    ev.GeraeteEinstellungen: _einstellungen,
    ev.KonfigGeladen: _konfig,
    ev.BibliothekGeladen: _bibliothek,
    ev.ResumeGeladen: _resume,
    ev.Bereit: _bereit,
    ev.Aufgelegt: _aufgelegt,
    ev.Gesperrt: _gesperrt,
    ev.Abgehoben: _abgehoben_ereignis,
    ev.LeserHallo: _leser_ausfall,
    ev.LeserAlarm: _leser_ausfall,
    ev.LeserHerzschlag: _herzschlag,
    ev.LautstaerkeGeaendert: _lautstaerke,
    ev.TrackWechsel: _track_wechsel,
    ev.FolgeZuEnde: _folge_zu_ende,
    ev.PlayerPosition: _position,
    ev.PlayerFehler: _player_fehler,
    ev.PlayerVerbindung: _verbindung,
    ev.Hauptknopf: _hauptknopf,
    ev.Weiter: _weiter,
    ev.Zurueck: _zurueck,
    ev.Kopfhoerer: _kopfhoerer,
    ev.Takt: _takt,
    ev.StummBeginnt: _stumm_beginnt,
    ev.StummEndet: _stumm_endet,
    ev.LernenGeaendert: _lernen,
    ev.GuteNachtEnde: _gute_nacht_ende,
    ev.HerunterfahrenAngefordert: _herunterfahren,
    ev.DienstEndet: _dienst_endet,
}


def _signatur(z: Zustand) -> tuple[str, bool, bool, str | None]:
    return (z.modus, z.figur is not None, z.modus == "spielt", z.serie_id)


def step(
    zustand: Zustand, ereignis: ev.Ereignis | ev.InternesEreignis, jetzt: Jetzt
) -> tuple[Zustand, tuple[ev.Befehl | ev.InternesEreignis, ...]]:
    handler = _HANDLER.get(type(ereignis))
    if handler is None:
        return zustand, ()
    neu, out = handler(zustand, ereignis, jetzt)  # type: ignore[arg-type]
    if _signatur(neu) != _signatur(zustand):
        out = list(out) + [ev.SitzungGeaendert(neu.modus, neu.figur is not None, neu.modus == "spielt", neu.serie_id)]
    return neu, tuple(out)
