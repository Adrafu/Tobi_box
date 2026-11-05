"""Teilautomat Wiedergabe-Sitzung (``core-interface.md``, 5.2, 6.3, 9).

Reine Funktionen: kein Zugriff auf Dateien, Netz, Uhr oder Zufall. Der
Zustand ist unveränderlich; ``step`` gibt einen neuen Zustand und die Befehle
(und internen Ereignisse) zurück.

Die Zeigerregeln (nächste Folge, Rücksprung, fehlende Folge) stehen in
``pointer.py`` (Abschnitt 6.3 des Vertrags).
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
    # Serie, die für die Figur zuletzt gestartet wurde (auch Überraschungs-Serie)
    serie_id: str | None = None
    datei: str | None = None
    index: int = 0
    position_s: float = 0.0
    konfig: ev.Konfig | None = None
    serien: tuple[ev.Serie, ...] = ()
    zeiger: Mapping[str, ev.Zeiger] = field(default_factory=dict)
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


def _ort_am_zeiger(
    serie: ev.Serie, zeiger: ev.Zeiger | None
) -> tuple[str, int, float, bool] | None:
    """(datei, index, position, folge_fehlte) für den Start, ``None`` bei leerer Serie."""
    ort = pointer.ort_am_zeiger(serie, zeiger)
    if ort is None:
        return None
    return ort.datei, ort.index, ort.position_s, ort.folge_fehlte


def _speichern(z: Zustand, grund: str, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """``ZeigerSpeichern`` für die aktuelle Folge, nur wenn der Zeiger sich ändert."""
    if z.serie_id is None or z.datei is None:
        return z, []
    alt = z.zeiger.get(z.serie_id)
    if pointer.unveraendert(alt, z.datei, z.index, z.position_s):
        return z, []
    neu = pointer.neuer_zeiger(alt, z.serie_id, z.datei, z.index, z.position_s)
    pos = neu.position_s
    zeiger = dict(z.zeiger)
    zeiger[z.serie_id] = neu
    cmd = ev.ZeigerSpeichern(z.serie_id, z.datei, z.index, pos, grund)  # type: ignore[arg-type]
    return replace(z, zeiger=zeiger, letzte_speicherung=jetzt.mono), [cmd]


def _grenze_weg(z: Zustand) -> Ausgabe:
    return [ev.GrenzeGesetzt(GRENZE_AUSBLENDEN, None)] if z.ausblenden is not None else []


def _ruhe(z: Zustand, **felder: object) -> Zustand:
    """Zustand für „es läuft nichts mehr“: Fristen und Ausblenden verwerfen."""
    return replace(z, unbekannt_seit=None, mpd_verloren=False, mpd_bis=None, ausblenden=None, **felder)


def _start(z: Zustand, serie: ev.Serie, vorgang: str | None, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Serie am Zeiger starten (Zeiger laden, Rücksprung, ``Abspielen``)."""
    ort = _ort_am_zeiger(serie, z.zeiger.get(serie.id))
    if ort is None:
        out: Ausgabe = [
            ev.TonSpielen("fehler"),
            _prot("ERROR", "serie_leer", "fehlerton", vorgang, serie=serie.id),
        ]
        return _ruhe(z, modus="pausiert", serie_id=None, datei=None), out
    datei, index, position, fehlte = ort
    out = []
    if fehlte:
        out.append(_prot("WARNING", "zeiger_folge_fehlt", "naechste_folge", vorgang, serie=serie.id, datei=datei))
    out.append(ev.Abspielen(serie.id, serie.ordner, datei, position, vorgang))
    z = _ruhe(
        z,
        modus="spielt",
        serie_id=serie.id,
        datei=datei,
        index=index,
        position_s=position,
        letzte_speicherung=jetzt.mono,
    )
    return z, out


def _stumm_hinweis(z: Zustand, modus: str) -> tuple[Zustand, Ausgabe]:
    return replace(z, modus=modus), [ev.TonSpielen("hinweis")]


# --------------------------------------------------------------------------
# Auflegen (Figur wird gemeldet)
# --------------------------------------------------------------------------


def _auflegen(z: Zustand, uid: str | None, vorgang: str, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Neue Figur in einem Zustand ohne laufende Wiedergabe behandeln."""
    zuo = z.konfig.zuordnungen.get(uid) if (uid is not None and z.konfig is not None) else None
    if zuo is not None and zuo.typ == "aktion" and zuo.aktion is not None:
        return replace(z, figur=Figur(vorgang, uid, "aktion")), [ev.AktionAusgeloest(zuo.aktion, vorgang)]

    out: Ausgabe = []
    serie: ev.Serie | None
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
    z = replace(z, figur=Figur(vorgang, uid, art))

    if z.stumm:
        modus = z.modus if z.modus in ("beendet", "gehalten") else "gehalten"
        z = replace(z, modus=modus)
        if serie is not None:
            # Felder folgen dem gespeicherten Zeiger der neuen Serie (nie Reste einer anderen)
            ort = _ort_am_zeiger(serie, z.zeiger.get(serie.id))
            if ort is not None:
                z = replace(z, serie_id=serie.id, datei=ort[0], index=ort[1], position_s=ort[2])
            else:
                z = replace(z, serie_id=serie.id, datei=None, index=0, position_s=0.0)
        out.append(ev.TonSpielen("hinweis"))
        return z, out

    if serie is None:
        out.append(ev.TonSpielen("fehler"))
        out.append(_prot("ERROR", "ueberraschung_fehlt", "fehlerton", vorgang, art=art))
        return _ruhe(z, modus="pausiert", serie_id=None, datei=None), out

    if art == "unbekannt":
        out.append(ev.TonSpielen("unbekannt"))
    z, start = _start(z, serie, vorgang, jetzt)
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
    z = replace(z, figur=None, hb_abweichungen=0)
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
    if e.serie_id == z.serie_id and e.datei == z.datei:
        return replace(z, position_s=e.position_s), []
    return z, []


def _folge_zu_ende(z: Zustand, e: ev.FolgeZuEnde, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    if z.modus not in ("spielt", "unbekannt"):
        return z, []
    if e.serie_id != z.serie_id or e.datei != z.datei:
        return z, [_prot("WARNING", "folge_zu_ende_fremd", "ignoriert", z.figur.vorgang if z.figur else None, serie=e.serie_id, datei=e.datei)]
    out: Ausgabe = _grenze_weg(z)
    serie = _serie(z, z.serie_id)
    z = _ruhe(z, modus="beendet")
    if serie is not None and serie.folgen:
        datei, nxt = pointer.naechste_folge(serie, e.datei, z.index)
        z = replace(z, datei=datei, index=nxt, position_s=0.0)
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
        datei, nxt = pointer.naechste_folge(serie, z.datei or "", z.index)
        z = replace(z, datei=datei, index=nxt, position_s=0.0)
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
            ev.Abspielen(serie.id, serie.ordner, z.datei, pos, z.figur.vorgang),
        ]
        return replace(z, mpd_verloren=False, mpd_bis=None, position_s=pos, letzte_speicherung=jetzt.mono), out
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
        serie = _serie(z, z.serie_id)
        if serie is None:
            return z, []
        return _start(z, serie, z.figur.vorgang if z.figur else None, jetzt)
    return z, []


def _springen(z: Zustand, delta: int, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """``Weiter`` (+1) und ``Zurueck`` (-1)."""
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
    if serie is None or not serie.folgen:
        return z, []
    if z.modus == "beendet" and delta > 0:
        # Weiter = Hauptknopf kurz: die Folge, auf die der Zeiger steht (9.12)
        return _start(z, serie, vorgang, jetzt)
    if z.modus == "spielt":
        aktuell = pointer.aktueller_index(serie, z.datei, z.index)
    else:
        # pausiert/beendet: immer vom gespeicherten Zeiger dieser Serie rechnen
        aktuell = pointer.index_am_zeiger(serie, z.zeiger.get(serie.id))
    datei, ziel = pointer.springe(serie, aktuell, delta)
    z = replace(z, datei=datei, index=ziel, position_s=0.0)
    z, sp = _speichern(z, "folgenende", jetzt)
    z = _ruhe(z, modus="spielt", letzte_speicherung=jetzt.mono)
    return z, sp + [ev.Abspielen(serie.id, serie.ordner, datei, 0.0, vorgang)]


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
    z = replace(z, kopfhoerer_grenze=e.lautstaerke_kopfhoerer)
    if z.kopfhoerer_steckt:
        return z, [ev.GrenzeGesetzt(GRENZE_KOPFHOERER, e.lautstaerke_kopfhoerer)]
    return z, []


def _bibliothek(z: Zustand, e: ev.BibliothekGeladen, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return replace(z, serien=e.serien), []


def _resume(z: Zustand, e: ev.ResumeGeladen, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return replace(z, zeiger={zg.serie_id: zg for zg in e.zeiger}), []


def _bereit(z: Zustand, e: ev.Bereit, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    return z, [ev.TonSpielen("start")]


def _konfig(z: Zustand, e: ev.KonfigGeladen, jetzt: Jetzt) -> tuple[Zustand, Ausgabe]:
    """Neue Konfiguration; bei liegender Figur gilt 9.14."""
    z = replace(z, konfig=e.konfig)
    f = z.figur
    if f is None or f.uid is None or f.art == "aktion":
        return z, []
    zuo = e.konfig.zuordnungen.get(f.uid)
    if zuo is None or zuo.typ != "serie":
        return z, []
    serie = _serie(z, zuo.serie_id)
    if serie is None or serie.id == z.serie_id:
        return z, []
    z = replace(z, figur=replace(f, art="serie"))
    if z.modus == "spielt" and z.ausblenden is None:
        z, sp = _speichern(z, "figurwechsel", jetzt)
        z, start = _start(z, serie, f.vorgang, jetzt)
        return z, sp + start
    if z.modus in ("pausiert", "beendet"):
        if z.stumm:
            return z, [ev.TonSpielen("hinweis")]
        return _start(z, serie, f.vorgang, jetzt)
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
