"""Zustandsdateien: atomar schreiben, mit ``.bak`` lesen (``data-model.md``, 1 bis 3).

* ``schreibe_atomar``: ``.tmp`` -> ``fsync`` -> ``.bak`` (harter Verweis) ->
  ``os.replace`` -> Verzeichnis-``fsync`` (Abschnitt 1.2).
* ``lade_zustandsdatei``: Rückfall ``<name>`` -> ``<name>.bak`` -> Standardwerte
  (Abschnitt 1.3) samt Protokoll.
* ``ResumeStore``: ``resume.json`` laden und auf ``ZeigerSpeichern`` schreiben,
  nur bei Änderung und höchstens alle 30 s für den Grund ``periodisch``.
* ``KonfigStore``: ``config.json`` (Abschnitt 2) laden, prüfen, annehmen.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from . import events as ev
from . import pointer
from .eventlog import logge

T = TypeVar("T")

SCHEMA_VERSION = 1
BEKANNTE_VERSIONEN = frozenset({1})

#: Vorgabe-Zeitzone von ``leise_zeiten`` (Abschnitt 2)
STANDARD_ZEITZONE = "Europe/Berlin"

_UID_RE = re.compile(r"^(?:[0-9a-f]{8}|[0-9a-f]{14}|[0-9a-f]{16}|[0-9a-f]{20})$")
_LISTE_RE = re.compile(r"^[0-9a-f]{16}$")
_FENSTER_ID_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
_ZEIT_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class Ungueltig(ValueError):
    """Inhalt einer Zustandsdatei ist ungültig (Schema, Wertebereich)."""

    def __init__(self, grund: str, text: str = "") -> None:
        super().__init__(f"{grund}: {text}" if text else grund)
        self.grund = grund


# --------------------------------------------------------------------------
# Atomares Schreiben und Lesen
# --------------------------------------------------------------------------


def serialisiere(inhalt: Mapping[str, Any]) -> bytes:
    """JSON nach 1.1: UTF-8, 2 Leerzeichen, ``\\n`` am Ende, ``schema_version`` zuerst."""
    obj = dict(inhalt)
    version = obj.pop("schema_version", SCHEMA_VERSION)
    return (json.dumps({"schema_version": version, **obj}, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _fsync_verzeichnis(verzeichnis: Path) -> None:
    fd = os.open(verzeichnis, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _lesbar(pfad: Path) -> bool:
    try:
        json.loads(pfad.read_bytes().decode("utf-8"))
        return True
    except (OSError, ValueError):
        return False


def schreibe_atomar(pfad: str | Path, inhalt: Mapping[str, Any]) -> None:
    """Zustandsdatei nach Abschnitt 1.2 schreiben. ``pfad`` ist nie halb geschrieben."""
    pfad = Path(pfad)
    daten = serialisiere(inhalt)
    tmp = pfad.with_name(pfad.name + ".tmp")
    bak = pfad.with_name(pfad.name + ".bak")
    bak_tmp = pfad.with_name(pfad.name + ".bak.tmp")
    pfad.parent.mkdir(parents=True, exist_ok=True)

    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(daten)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise

    if pfad.exists() and _lesbar(pfad):
        try:
            bak_tmp.unlink()
        except FileNotFoundError:
            pass
        os.link(pfad, bak_tmp)
        os.replace(bak_tmp, bak)
    os.replace(tmp, pfad)
    _fsync_verzeichnis(pfad.parent)


def raeume_auf(verzeichnis: str | Path) -> int:
    """Reste ``*.tmp`` und ``*.bak.tmp`` löschen (beim Start). Gibt die Anzahl zurück."""
    n = 0
    verzeichnis = Path(verzeichnis)
    if not verzeichnis.is_dir():
        return 0
    for p in verzeichnis.iterdir():
        if p.name.endswith(".tmp") and p.is_file():
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
    return n


def lese_pruefe(pfad: Path, pruefe: Callable[[dict[str, Any]], T]) -> T:
    """Datei lesen und prüfen. Wirft ``Ungueltig`` (oder ``OSError`` bei Lesefehler)."""
    try:
        roh = json.loads(pfad.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise Ungueltig("kein_json", str(e)) from e
    if not isinstance(roh, dict):
        raise Ungueltig("kein_objekt")
    version = roh.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise Ungueltig("schema_ungueltig", "schema_version fehlt")
    if version > max(BEKANNTE_VERSIONEN):
        raise Ungueltig("schema_zu_neu", str(version))
    if version not in BEKANNTE_VERSIONEN:
        raise Ungueltig("schema_ungueltig", f"unbekannte Version {version}")
    return pruefe(roh)


def lade_zustandsdatei(
    pfad: str | Path,
    pruefe: Callable[[dict[str, Any]], T],
    standard: Callable[[], T],
    zurueckschreiben: Callable[[T], Mapping[str, Any]] | None = None,
) -> tuple[T, str]:
    """Abschnitt 1.3. Gibt ``(wert, quelle)`` zurück.

    ``quelle`` ist ``"datei"``, ``"neu"`` (fehlt, erster Start), ``"bak"``
    (Rückfall) oder ``"standard"`` (``datei_verloren``).
    """
    pfad = Path(pfad)
    bak = pfad.with_name(pfad.name + ".bak")
    baustein = "store"
    if not pfad.exists():
        return standard(), "neu"
    try:
        return lese_pruefe(pfad, pruefe), "datei"
    except (Ungueltig, OSError) as e:
        grund = e.grund if isinstance(e, Ungueltig) else "lesefehler"
        if grund == "schema_zu_neu":
            logge(baustein, "ERROR", "schema_zu_neu", "fehler", datei=pfad.name, detail=str(e))
        defekt = pfad.with_name(pfad.name + ".defekt")
        try:
            os.replace(pfad, defekt)
        except OSError:
            pass
        logge(baustein, "ERROR", "datei_defekt", "fehler", datei=pfad.name, grund=grund)
    if bak.exists():
        try:
            wert = lese_pruefe(bak, pruefe)
        except (Ungueltig, OSError):
            wert = None
        else:
            if zurueckschreiben is not None:
                schreibe_atomar(pfad, zurueckschreiben(wert))
            logge(baustein, "WARNING", "datei_aus_bak", "ok", datei=pfad.name)
            return wert, "bak"
    logge(baustein, "ERROR", "datei_verloren", "fehler", datei=pfad.name)
    return standard(), "standard"


# --------------------------------------------------------------------------
# resume.json
# --------------------------------------------------------------------------


def _zahl(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _ganz(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def parse_resume(roh: Mapping[str, Any]) -> dict[str, ev.Zeiger]:
    serien = roh.get("serien")
    if not isinstance(serien, dict):
        raise Ungueltig("schema_ungueltig", "serien fehlt")
    aus: dict[str, ev.Zeiger] = {}
    for sid, e in serien.items():
        if not isinstance(e, dict):
            raise Ungueltig("schema_ungueltig", f"serien.{sid}")
        folge, index, pos, zaehler = e.get("folge"), e.get("index"), e.get("position_s"), e.get("zaehler")
        if not isinstance(folge, str) or not folge:
            raise Ungueltig("schema_ungueltig", f"serien.{sid}.folge")
        if not _ganz(index) or index < 0:
            raise Ungueltig("schema_ungueltig", f"serien.{sid}.index")
        if not _zahl(pos) or pos < 0:
            raise Ungueltig("schema_ungueltig", f"serien.{sid}.position_s")
        if not _ganz(zaehler) or zaehler < 1:
            raise Ungueltig("schema_ungueltig", f"serien.{sid}.zaehler")
        aus[sid] = ev.Zeiger(sid, folge, index, float(pos), zaehler)
    return aus


def resume_zu_json(zeiger: Mapping[str, ev.Zeiger]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "serien": {
            sid: {"folge": z.datei, "index": z.index, "position_s": z.position_s, "zaehler": z.zaehler}
            for sid, z in sorted(zeiger.items())
        },
    }


class ResumeStore:
    """``resume.json``. Einziger Schreiber ist der Befehl ``ZeigerSpeichern``."""

    NAME = "resume.json"

    def __init__(self, verzeichnis: str | Path) -> None:
        self.pfad = Path(verzeichnis) / self.NAME
        self._zeiger: dict[str, ev.Zeiger] = {}
        self._letzte_schreibung: float | None = None
        self.quelle = "neu"
        self.schreibungen = 0

    @property
    def zeiger(self) -> Mapping[str, ev.Zeiger]:
        return dict(self._zeiger)

    def laden(self) -> ev.ResumeGeladen:
        """Beim Start; ohne Datei oder bei Verlust: keine Zeiger."""
        raeume_auf(self.pfad.parent)
        wert, self.quelle = lade_zustandsdatei(self.pfad, parse_resume, dict, resume_zu_json)
        self._zeiger = dict(wert)
        return ev.ResumeGeladen(tuple(self._zeiger.values()))

    def speichern(self, befehl: ev.ZeigerSpeichern, mono: float) -> bool:
        """``ZeigerSpeichern`` ausführen. ``True``, wenn geschrieben wurde.

        Schreibt nicht, wenn Datei, Index und abgerundete Position unverändert
        sind. Der Grund ``periodisch`` schreibt höchstens alle 30 s (``mono``);
        alle anderen Gründe sofort.
        """
        alt = self._zeiger.get(befehl.serie_id)
        if pointer.unveraendert(alt, befehl.datei, befehl.index, befehl.position_s):
            return False
        if (
            befehl.grund == "periodisch"
            and self._letzte_schreibung is not None
            and not pointer.periodisch_faellig(self._letzte_schreibung, mono)
        ):
            return False
        neu = pointer.neuer_zeiger(alt, befehl.serie_id, befehl.datei, befehl.index, befehl.position_s)
        zeiger = dict(self._zeiger)
        zeiger[befehl.serie_id] = neu
        schreibe_atomar(self.pfad, resume_zu_json(zeiger))
        self._zeiger = zeiger
        self._letzte_schreibung = mono
        self.schreibungen += 1
        logge(
            "store",
            "DEBUG",
            "zeiger_gespeichert",
            "ok",
            serie=befehl.serie_id,
            folge=befehl.datei,
            position_s=neu.position_s,
            grund=befehl.grund,
            zaehler=neu.zaehler,
        )
        return True


# --------------------------------------------------------------------------
# config.json
# --------------------------------------------------------------------------


def parse_konfig(roh: Mapping[str, Any]) -> ev.Konfig:
    """``config.json`` (Abschnitt 2) prüfen. Ist irgendein Teil ungültig, wirft es ``Ungueltig``."""

    def fail(was: str) -> Ungueltig:
        return Ungueltig("schema_ungueltig", was)

    rev, lid = roh.get("revision"), roh.get("liste_id")
    if not _ganz(rev) or rev < 1:
        raise fail("revision")
    if not isinstance(lid, str) or not _LISTE_RE.match(lid):
        raise fail("liste_id")

    zuo_roh = roh.get("zuordnungen")
    if not isinstance(zuo_roh, dict):
        raise fail("zuordnungen")
    zuordnungen: dict[str, ev.Zuordnung] = {}
    for uid, z in zuo_roh.items():
        if not _UID_RE.match(uid) or not isinstance(z, dict):
            raise fail(f"zuordnungen.{uid}")
        typ = z.get("typ")
        if typ == "serie":
            sid = z.get("serie")
            if not isinstance(sid, str) or not 1 <= len(sid) <= 64:
                raise fail(f"zuordnungen.{uid}.serie")
            zuordnungen[uid] = ev.Zuordnung("serie", sid, None)
        elif typ == "aktion":
            akt = z.get("aktion")
            if akt not in ("status", "gute_nacht"):
                raise fail(f"zuordnungen.{uid}.aktion")
            zuordnungen[uid] = ev.Zuordnung("aktion", None, akt)
        else:
            raise fail(f"zuordnungen.{uid}.typ")

    lz = roh.get("leise_zeiten")
    if not isinstance(lz, dict):
        raise fail("leise_zeiten")
    zone = lz.get("zeitzone", STANDARD_ZEITZONE)
    if not isinstance(zone, str):
        raise fail("leise_zeiten.zeitzone")
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(zone)
    except Exception as e:  # unbekannter Name oder fehlende Zeitzonendatenbank
        raise fail(f"leise_zeiten.zeitzone {zone!r}") from e
    fenster_roh = lz.get("fenster")
    if not isinstance(fenster_roh, list) or len(fenster_roh) > 32:
        raise fail("leise_zeiten.fenster")
    fenster: list[ev.Fenster] = []
    ids: set[str] = set()
    for i, f in enumerate(fenster_roh):
        if not isinstance(f, dict):
            raise fail(f"fenster[{i}]")
        fid = f.get("id")
        if not isinstance(fid, str) or not _FENSTER_ID_RE.match(fid) or fid in ids:
            raise fail(f"fenster[{i}].id")
        ids.add(fid)
        tage = f.get("tage")
        if (
            not isinstance(tage, list)
            or not tage
            or not all(_ganz(t) and 1 <= t <= 7 for t in tage)
            or len(set(tage)) != len(tage)
        ):
            raise fail(f"fenster[{i}].tage")
        von, bis = f.get("von"), f.get("bis")
        if not isinstance(von, str) or not _ZEIT_RE.match(von):
            raise fail(f"fenster[{i}].von")
        if not isinstance(bis, str) or not _ZEIT_RE.match(bis) or bis == von:
            raise fail(f"fenster[{i}].bis")
        wirkung = f.get("wirkung")
        grenze = f.get("grenze")
        if wirkung == "leiser":
            if not _ganz(grenze) or not 0 <= grenze <= 100:
                raise fail(f"fenster[{i}].grenze")
        elif wirkung == "stumm":
            grenze = None
        else:
            raise fail(f"fenster[{i}].wirkung")
        fenster.append(ev.Fenster(fid, tuple(tage), von, bis, wirkung, grenze))

    gn = roh.get("gute_nacht")
    if not isinstance(gn, dict):
        raise fail("gute_nacht")
    timer, aus = gn.get("timer_min"), gn.get("ausblenden_s")
    if not _ganz(timer) or not 1 <= timer <= 240:
        raise fail("gute_nacht.timer_min")
    if not _ganz(aus) or not 5 <= aus <= 600:
        raise fail("gute_nacht.ausblenden_s")
    for opt in ("ton_pegel", "hinweis_pegel"):
        if opt in roh and (not _ganz(roh[opt]) or not 0 <= roh[opt] <= 100):
            raise fail(opt)

    return ev.Konfig(
        revision=rev,
        liste_id=lid,
        zuordnungen=zuordnungen,
        leise_zeiten=ev.LeiseZeiten(zone, tuple(fenster)),
        gute_nacht=ev.GuteNacht(timer, aus),
    )


def leere_konfig() -> ev.Konfig:
    """Standard bei fehlender oder verlorener Datei: Revision 0, Listen-ID leer."""
    return ev.Konfig(0, "", {}, ev.LeiseZeiten(STANDARD_ZEITZONE, ()), ev.GuteNacht(30, 60))


def konfig_zu_json(k: ev.Konfig) -> dict[str, Any]:
    zuo: dict[str, Any] = {}
    for uid, z in k.zuordnungen.items():
        zuo[uid] = {"typ": "serie", "serie": z.serie_id} if z.typ == "serie" else {"typ": "aktion", "aktion": z.aktion}
    fenster = []
    for f in k.leise_zeiten.fenster:
        d: dict[str, Any] = {"id": f.id, "tage": list(f.tage), "von": f.von, "bis": f.bis, "wirkung": f.wirkung}
        if f.wirkung == "leiser":
            d["grenze"] = f.grenze
        fenster.append(d)
    return {
        "schema_version": SCHEMA_VERSION,
        "revision": k.revision,
        "liste_id": k.liste_id,
        "zuordnungen": zuo,
        "leise_zeiten": {"zeitzone": k.leise_zeiten.zeitzone, "fenster": fenster},
        "gute_nacht": {"timer_min": k.gute_nacht.timer_min, "ausblenden_s": k.gute_nacht.ausblenden_s},
    }


@dataclass(frozen=True, slots=True)
class Annahme:
    angenommen: bool
    grund: str  # "ok", "gleich", "schema_ungueltig", "revision_zu_niedrig"


_KONFIG_FELDER = (
    "schema_version", "revision", "liste_id", "erzeugt_am", "zuordnungen",
    "leise_zeiten", "gute_nacht", "ton_pegel", "hinweis_pegel",
)


def _parse_mit_roh(roh: Mapping[str, Any]) -> tuple[ev.Konfig, dict[str, Any]]:
    """Prüfen und die bekannten Felder behalten (``ton_pegel`` u. a. haben kein Feld in ``Konfig``)."""
    return parse_konfig(roh), {k: roh[k] for k in _KONFIG_FELDER if k in roh}


class KonfigStore:
    """``config.json``: laden und eine von HA gelieferte Liste annehmen."""

    NAME = "config.json"

    def __init__(self, verzeichnis: str | Path) -> None:
        self.pfad = Path(verzeichnis) / self.NAME
        self.konfig: ev.Konfig = leere_konfig()
        self.roh: dict[str, Any] = konfig_zu_json(self.konfig)
        self.quelle = "neu"

    def laden(self) -> ev.KonfigGeladen:
        raeume_auf(self.pfad.parent)
        (self.konfig, self.roh), self.quelle = lade_zustandsdatei(
            self.pfad,
            _parse_mit_roh,
            lambda: (leere_konfig(), konfig_zu_json(leere_konfig())),
            lambda wert: wert[1],
        )
        return ev.KonfigGeladen(self.konfig)

    def annehmen(self, roh: Mapping[str, Any]) -> Annahme:
        """Revisionsregel aus Abschnitt 2. Ungültig: bisherige Konfiguration bleibt."""
        try:
            version = roh.get("schema_version")
            if version not in BEKANNTE_VERSIONEN:
                raise Ungueltig("schema_zu_neu" if _ganz(version) and version > 1 else "schema_ungueltig")
            neu, behalten = _parse_mit_roh(roh)
        except Ungueltig as e:
            logge("store", "ERROR", "konfig_abgelehnt", "abgelehnt", grund="schema_ungueltig", detail=str(e))
            return Annahme(False, "schema_ungueltig")
        alt = self.konfig
        if neu.liste_id == alt.liste_id:
            if neu.revision == alt.revision:
                return Annahme(False, "gleich")
            if neu.revision < alt.revision:
                logge("store", "WARNING", "konfig_abgelehnt", "abgelehnt", grund="revision_zu_niedrig",
                      revision=neu.revision, aktuell=alt.revision)
                return Annahme(False, "revision_zu_niedrig")
        schreibe_atomar(self.pfad, behalten)
        self.konfig, self.roh = neu, behalten
        logge("store", "INFO", "konfig_angenommen", "ok", revision=neu.revision, liste_id=neu.liste_id)
        return Annahme(True, "ok")
