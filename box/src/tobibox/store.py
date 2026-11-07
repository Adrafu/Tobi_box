"""Zustandsdateien: atomar schreiben, mit ``.bak`` lesen (``data-model.md``, 1 bis 3).

* ``schreibe_atomar``: ``.tmp`` -> ``fsync`` -> ``.bak`` (harter Verweis) ->
  ``os.replace`` -> Verzeichnis-``fsync`` (Abschnitt 1.2).
* ``lade_zustandsdatei``: Rückfall ``<name>`` -> ``<name>.bak`` -> Standardwerte
  (Abschnitt 1.3) samt Protokoll. Fehlt ``<name>``, gibt es aber eine gültige
  ``.bak``, gilt die ``.bak``; „erster Start“ nur, wenn beide fehlen.
* ``ResumeStore``: ``resume.json`` laden und auf ``ZeigerSpeichern`` schreiben,
  nur bei geändertem Zeiger. Die Drosselung (30 s für ``periodisch``) liegt
  allein in ``session`` (``core-interface.md``, 6.3).
* ``KonfigStore``: ``config.json`` (Abschnitt 2) laden, prüfen, annehmen.

``resume.json`` und ``config.json`` haben ``schema_version`` 2 (Entscheidung F,
05.11.). Version 1 wird beim Lesen im Speicher migriert
(``migriere_resume_v1_nach_v2``, ``migriere_konfig_v1_nach_v2``, rein); gespeichert
wird danach Version 2. **``validiere_konfig`` ist die eine Funktion für Migration
und Prüfung einer Konfiguration** (Datei und MQTT-Liste); ``ha.py`` benutzt sie.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from . import events as ev
from . import pointer
from .eventlog import logge

T = TypeVar("T")

#: Namen der Zustandsdateien, die seit dem Start des Prozesses verloren gingen (``datei_verloren``);
#: der Prüfpunkt „Speicher“ der Status-Karte liest sie (``core-interface.md``, 12.3).
verlorene_dateien: list[str] = []

SCHEMA_VERSION = 2
BEKANNTE_VERSIONEN = frozenset({1, 2})

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
    text = json.dumps({"schema_version": version, **obj}, indent=2, ensure_ascii=False, allow_nan=False)
    return (text + "\n").encode("utf-8")


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

    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        with os.fdopen(fd, "wb") as f:
            f.write(daten)
            f.flush()
            os.fsync(f.fileno())

        if pfad.exists() and _lesbar(pfad):
            _loesche(bak_tmp)
            try:
                os.link(pfad, bak_tmp)
            except (OSError, NotImplementedError):  # Dateisystem ohne harte Verweise: kopieren
                shutil.copyfile(pfad, bak_tmp)
                with open(bak_tmp, "rb") as f:
                    os.fsync(f.fileno())
            os.replace(bak_tmp, bak)
        os.replace(tmp, pfad)
        _fsync_verzeichnis(pfad.parent)
    finally:
        _loesche(tmp)  # nach Erfolg schon umbenannt; bei Fehlern bleibt kein Rest
        _loesche(bak_tmp)


def _loesche(pfad: Path) -> None:
    try:
        pfad.unlink()
    except OSError:
        pass


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
        if not bak.exists():
            return standard(), "neu"  # erster Start: beide Dateien fehlen
        logge(baustein, "ERROR", "datei_fehlt", "fehler", daten={"datei": pfad.name})
        defekt_grund = None
    else:
        try:
            return lese_pruefe(pfad, pruefe), "datei"
        except (Ungueltig, OSError) as e:
            defekt_grund = e.grund if isinstance(e, Ungueltig) else "lesefehler"
            if defekt_grund == "schema_zu_neu":
                logge(baustein, "ERROR", "schema_zu_neu", "fehler", daten={"datei": pfad.name, "detail": str(e)})

    # ``.bak`` lesen, bevor die defekte Datei umbenannt wird.
    wert: T | None = None
    bak_ok = False
    if bak.exists():
        try:
            wert, bak_ok = lese_pruefe(bak, pruefe), True
        except (Ungueltig, OSError):
            pass

    if defekt_grund is not None:
        defekt = pfad.with_name(pfad.name + ".defekt")
        try:
            os.replace(pfad, defekt)
            _fsync_verzeichnis(pfad.parent)
        except OSError:
            pass
        logge(baustein, "ERROR", "datei_defekt", "fehler", daten={"datei": pfad.name, "grund": defekt_grund})

    if bak_ok:
        if zurueckschreiben is not None:
            schreibe_atomar(pfad, zurueckschreiben(wert))  # type: ignore[arg-type]
        logge(baustein, "WARNING", "datei_aus_bak", "ok", daten={"datei": pfad.name})
        return wert, "bak"  # type: ignore[return-value]
    logge(baustein, "ERROR", "datei_verloren", "fehler", daten={"datei": pfad.name})
    verlorene_dateien.append(pfad.name)
    return standard(), "standard"


# --------------------------------------------------------------------------
# resume.json
# --------------------------------------------------------------------------


def _zahl(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _endlich(x: Any) -> bool:
    try:
        return math.isfinite(x)
    except (OverflowError, TypeError):
        return False


def _ganz(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def migriere_resume_v1_nach_v2(roh: Mapping[str, Any]) -> dict[str, Any]:
    """``resume.json`` Version 1 -> 2 (rein): jeder Eintrag in ``serien`` bekommt ``track`` 0,
    ``folgen`` ist leer. Die gespeicherte Position gilt für den ersten Track."""
    serien = roh.get("serien")
    neu: dict[str, Any] = {k: v for k, v in roh.items() if k != "schema_version"}
    if isinstance(serien, dict):
        neu["serien"] = {
            sid: ({**e, "track": e.get("track", 0)} if isinstance(e, dict) else e) for sid, e in serien.items()
        }
    neu["folgen"] = {}
    return {"schema_version": 2, **neu}


def _gueltiger_name(x: Any) -> bool:
    return (
        isinstance(x, str)
        and x not in ("", ".", "..")
        and "/" not in x
        and "\\" not in x
        and len(x.encode("utf-8", "surrogateescape")) <= 255
    )


def _pruefe_zeiger_felder(e: Any, wo: str) -> tuple[int, float, int]:
    if not isinstance(e, dict):
        raise Ungueltig("schema_ungueltig", wo)
    track, pos, zaehler = e.get("track"), e.get("position_s"), e.get("zaehler")
    if not _ganz(track) or track < 0:
        raise Ungueltig("schema_ungueltig", f"{wo}.track")
    if not _zahl(pos) or not _endlich(pos) or pos < 0:
        raise Ungueltig("schema_ungueltig", f"{wo}.position_s")
    if not _ganz(zaehler) or zaehler < 1:
        raise Ungueltig("schema_ungueltig", f"{wo}.zaehler")
    return track, float(pos), zaehler


def parse_resume(roh: Mapping[str, Any]) -> dict[pointer.Schluessel, ev.Zeiger]:
    """``resume.json`` prüfen (Version 1 wird zuerst migriert). Schlüssel: ``pointer.schluessel``."""
    if roh.get("schema_version") == 1:
        roh = migriere_resume_v1_nach_v2(roh)
    serien = roh.get("serien")
    if not isinstance(serien, dict):
        raise Ungueltig("schema_ungueltig", "serien fehlt")
    aus: dict[pointer.Schluessel, ev.Zeiger] = {}
    for sid, e in serien.items():
        track, pos, zaehler = _pruefe_zeiger_felder(e, f"serien.{sid}")
        folge, index = e.get("folge"), e.get("index")
        if not isinstance(folge, str) or not folge:
            raise Ungueltig("schema_ungueltig", f"serien.{sid}.folge")
        if not _ganz(index) or index < 0:
            raise Ungueltig("schema_ungueltig", f"serien.{sid}.index")
        z = ev.Zeiger("serie", sid, folge, index, track, pos, zaehler)
        aus[pointer.schluessel_von(z)] = z
    folgen = roh.get("folgen")
    if not isinstance(folgen, dict):
        raise Ungueltig("schema_ungueltig", "folgen fehlt")
    for sid, je_folge in folgen.items():
        if not isinstance(je_folge, dict):
            raise Ungueltig("schema_ungueltig", f"folgen.{sid}")
        for name, e in je_folge.items():
            if not _gueltiger_name(name):
                raise Ungueltig("schema_ungueltig", f"folgen.{sid}.{name}")
            track, pos, zaehler = _pruefe_zeiger_felder(e, f"folgen.{sid}.{name}")
            z = ev.Zeiger("folge", sid, name, None, track, pos, zaehler)
            aus[pointer.schluessel_von(z)] = z
    return aus


def resume_zu_json(zeiger: Mapping[pointer.Schluessel, ev.Zeiger]) -> dict[str, Any]:
    serien: dict[str, Any] = {}
    folgen: dict[str, dict[str, Any]] = {}
    for z in sorted(zeiger.values(), key=lambda z: (z.serie_id, z.datei)):
        if z.art == "serie":
            serien[z.serie_id] = {
                "folge": z.datei,
                "index": z.index if z.index is not None else 0,
                "track": z.track,
                "position_s": z.position_s,
                "zaehler": z.zaehler,
            }
        else:
            folgen.setdefault(z.serie_id, {})[z.datei] = {
                "track": z.track,
                "position_s": z.position_s,
                "zaehler": z.zaehler,
            }
    return {"schema_version": SCHEMA_VERSION, "serien": serien, "folgen": folgen}


class ResumeStore:
    """``resume.json``. Einziger Schreiber ist der Befehl ``ZeigerSpeichern``."""

    NAME = "resume.json"

    def __init__(self, verzeichnis: str | Path) -> None:
        self.pfad = Path(verzeichnis) / self.NAME
        self._zeiger: dict[pointer.Schluessel, ev.Zeiger] = {}
        self.quelle = "neu"
        self.schreibungen = 0

    @property
    def zeiger(self) -> Mapping[pointer.Schluessel, ev.Zeiger]:
        return dict(self._zeiger)

    def laden(self) -> ev.ResumeGeladen:
        """Beim Start; ohne Datei oder bei Verlust: keine Zeiger."""
        raeume_auf(self.pfad.parent)
        wert, self.quelle = lade_zustandsdatei(self.pfad, parse_resume, dict, resume_zu_json)
        self._zeiger = dict(wert)
        return ev.ResumeGeladen(tuple(self._zeiger.values()))

    def speichern(self, befehl: ev.ZeigerSpeichern, mono: float) -> bool:
        """``ZeigerSpeichern`` ausführen. ``True``, wenn geschrieben wurde.

        Schreibt nicht, wenn Art, Folge, Index, Track und abgerundete Position
        unverändert sind; sonst immer. Die 30-s-Drosselung für ``periodisch``
        entscheidet allein ``session``. ``mono`` bleibt für die Aufrufer-Schnittstelle.
        """
        key = pointer.schluessel(befehl.art, befehl.serie_id, befehl.datei)
        alt = self._zeiger.get(key)
        if pointer.unveraendert(alt, befehl.art, befehl.datei, befehl.index, befehl.track, befehl.position_s):
            return False
        neu = pointer.neuer_zeiger(
            alt, befehl.art, befehl.serie_id, befehl.datei, befehl.index, befehl.track, befehl.position_s
        )
        zeiger = dict(self._zeiger)
        zeiger[key] = neu
        schreibe_atomar(self.pfad, resume_zu_json(zeiger))
        self._zeiger = zeiger
        self.schreibungen += 1
        logge(
            "store",
            "INFO",
            "zeiger_gespeichert",
            "ok",
            daten={
                "art": befehl.art, "serie": befehl.serie_id, "folge": befehl.datei, "track": neu.track,
                "position_s": neu.position_s, "grund": befehl.grund, "zaehler": neu.zaehler,
            },
        )
        return True


# --------------------------------------------------------------------------
# config.json
# --------------------------------------------------------------------------


def migriere_konfig_v1_nach_v2(roh: Mapping[str, Any]) -> dict[str, Any]:
    """``config.json`` Version 1 -> 2 (rein): ``{typ, …}`` wird zu ``{ziel: {typ, …}}``.

    Nur Einträge mit ``typ`` ``serie`` oder ``aktion`` (Version 1 kennt nichts anderes)
    werden verpackt; alles andere bleibt, wie es ist, und fällt in der Prüfung durch."""
    neu: dict[str, Any] = {k: v for k, v in roh.items() if k != "schema_version"}
    zuo = roh.get("zuordnungen")
    if isinstance(zuo, dict):
        neu["zuordnungen"] = {
            uid: (
                {"ziel": z}
                if isinstance(z, dict) and "ziel" not in z and z.get("typ") in ("serie", "aktion")
                else z
            )
            for uid, z in zuo.items()
        }
    return {"schema_version": 2, **neu}


def validiere_konfig(roh: Mapping[str, Any]) -> tuple[ev.Konfig, dict[str, Any]]:
    """**Die eine Funktion für Migration und Prüfung einer Konfiguration** (Datei und MQTT-Liste).

    Liste der Version 1: erst im Speicher nach Version 2 migrieren, dann prüfen
    (``ziel`` wird nach der Migration geprüft, ``data-model.md``, Abschnitt 2).
    Gibt ``(Konfig, behaltene Felder in Version 2)`` zurück; wirft ``Ungueltig``
    (``schema_zu_neu``, ``schema_ungueltig``)."""
    version = roh.get("schema_version")
    if not _ganz(version):
        raise Ungueltig("schema_ungueltig", "schema_version")
    if version > max(BEKANNTE_VERSIONEN):
        raise Ungueltig("schema_zu_neu", str(version))
    if version not in BEKANNTE_VERSIONEN:
        raise Ungueltig("schema_ungueltig", f"unbekannte Version {version}")
    if version == 1:
        roh = migriere_konfig_v1_nach_v2(roh)
    return parse_konfig(roh), {k: roh[k] for k in _KONFIG_FELDER if k in roh}


def parse_konfig(roh: Mapping[str, Any]) -> ev.Konfig:
    """``config.json`` Version 2 (Abschnitt 2) prüfen. Ist irgendein Teil ungültig, wirft es ``Ungueltig``.

    Eine Liste der Version 1 geht vorher durch ``validiere_konfig``."""
    if roh.get("schema_version") == 1:
        roh = migriere_konfig_v1_nach_v2(roh)

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
        ziel = z.get("ziel")
        if not isinstance(ziel, dict):
            raise fail(f"zuordnungen.{uid}.ziel")
        typ = ziel.get("typ")
        if typ in ("serie", "folge"):
            sid = ziel.get("serie")
            if not isinstance(sid, str) or not 1 <= len(sid) <= 64:
                raise fail(f"zuordnungen.{uid}.ziel.serie")
            if typ == "serie":
                zuordnungen[uid] = ev.Zuordnung("serie", sid)
            else:
                folge = ziel.get("folge")
                if not _gueltiger_name(folge):
                    raise fail(f"zuordnungen.{uid}.ziel.folge")
                zuordnungen[uid] = ev.Zuordnung("folge", sid, folge)
        elif typ == "aktion":
            akt = ziel.get("aktion")
            if akt not in ("status", "gute_nacht"):
                raise fail(f"zuordnungen.{uid}.ziel.aktion")
            zuordnungen[uid] = ev.Zuordnung("aktion", aktion=akt)
        else:
            raise fail(f"zuordnungen.{uid}.ziel.typ")

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
        if z.typ == "serie":
            ziel: dict[str, Any] = {"typ": "serie", "serie": z.serie_id}
        elif z.typ == "folge":
            ziel = {"typ": "folge", "serie": z.serie_id, "folge": z.folge}
        else:
            ziel = {"typ": "aktion", "aktion": z.aktion}
        zuo[uid] = {"ziel": ziel}
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
    grund: str  # "ok", "gleich", "schema_ungueltig", "schema_zu_neu", "revision_zu_niedrig"


_KONFIG_FELDER = (
    "schema_version", "revision", "liste_id", "erzeugt_am", "zuordnungen",
    "leise_zeiten", "gute_nacht", "ton_pegel", "hinweis_pegel",
)


def _parse_mit_roh(roh: Mapping[str, Any]) -> tuple[ev.Konfig, dict[str, Any]]:
    """Migrieren, prüfen und die bekannten Felder behalten (``ton_pegel`` u. a. haben kein Feld in ``Konfig``)."""
    return validiere_konfig(roh)


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
            neu, behalten = validiere_konfig(roh)  # Version 1 wird im Speicher migriert
        except Ungueltig as e:
            logge("store", "ERROR", "konfig_abgelehnt", "abgelehnt", daten={"grund": e.grund, "detail": str(e)})
            return Annahme(False, "schema_zu_neu" if e.grund == "schema_zu_neu" else "schema_ungueltig")
        alt = self.konfig
        if neu.liste_id == alt.liste_id:
            if neu.revision == alt.revision:
                return Annahme(False, "gleich")
            if neu.revision < alt.revision:
                logge("store", "WARNING", "konfig_abgelehnt", "abgelehnt", daten={"grund": 'revision_zu_niedrig', "revision": neu.revision, "aktuell": alt.revision})
                return Annahme(False, "revision_zu_niedrig")
        schreibe_atomar(self.pfad, behalten)
        self.konfig, self.roh = neu, behalten
        logge("store", "INFO", "konfig_angenommen", "ok", daten={"revision": neu.revision, "liste_id": neu.liste_id})
        return Annahme(True, "ok")
