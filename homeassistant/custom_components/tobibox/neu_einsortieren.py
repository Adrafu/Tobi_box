"""„Anders einsortieren“ (Vertrag W, Befehl 43 ``einsortierung/neu``, 2.4 und 14.4; Paket A3e).

Der Weg zurück von ``medien/`` in den Eingang. Er ist machbar, weil das Einsortieren ab jetzt mitschreibt, was es getan hat
(``rueckweg`` in der Protokollzeile des Eintrags, nie in der Ausgabe von ``eingang/list``):

* je betroffene Serie: ob der Eintrag sie neu angelegt hat, ``name``, ``stand`` (Fingerabdruck **nach** dem Einsortieren), ``art``,
  ``art_quelle`` und ob schon ein eigenes Cover da war;
* je Folge: Serie, Name der Folge, ``anzeige``, Ordner-Folge oder Datei, Namen und Größen der Audiodateien.

Alte Einträge (vor A3e) haben das nicht: ``neu_einsortieren_nicht_moeglich``.

**Ablauf** (Eingang gesperrt, dann die betroffenen Serien; alles auf derselben Freigabe, Dateien werden nur **verschoben**, nie kopiert und
gelöscht):

0. Prüfen (nichts wird angefasst): Alter oder „bitte ansehen“, alle sieben „etwas geändert“-Prüfungen, und die Dateien der Folgen sind noch
   genau die, die einsortiert wurden (Namen und Größen).
1. Die Folgen in einen neuen Ordner im Eingang verschieben (Name des alten Eintrags, sonst mit „(2)“). Scheitert ein Verschieben,
   wird alles bisher Verschobene zurückgelegt; der Befehl endet mit ``medien_schreibfehler``.
2. ``serie.json`` der betroffenen Serien ohne diese Folgen schreiben; die vom Eintrag **neu angelegten** Serien (jetzt ohne Folgen)
   gehen in den Papierkorb (``grund="manuell"``, ``geloescht_von``).
3. Den Wunsch (14.4) je Datei in den Vorgaben des Eingangs festhalten, Prüfsummen aus dem Index nehmen, alte Protokollzeile entfernen,
   sofort speichern. Dann sortiert der Eingang sofort ein (ohne Ruhezeit, AM25) und meldet ``neu_einsortiert``.

**Was bei einem Abbruch übrig bleibt** (Neustart von HA oder Fehler mitten drin): keine Datei geht verloren, schlimmstenfalls steht eine
Folge doppelt da.

* vor Schritt 1 zu Ende: nichts geändert.
* mitten in Schritt 1 (Neustart): die schon verschobenen Folgen liegen im Eingang unter dem neuen Ordner, ohne Wunsch; der Eingang sortiert
  sie nach seiner Ruhezeit nach den Tags ein (wie jede neue Datei). Die alte Serie führt sie noch in ``serie.json`` auf, bis ``medien/pruefen`` läuft.
* zwischen Schritt 1 und 3: wie oben, nur ist ``serie.json`` schon bereinigt.
* Schreibfehler in Schritt 2: der Ablauf macht trotzdem mit Schritt 3 weiter (die Dateien liegen ja schon im Eingang und sollen nach dem
  Wunsch einsortiert werden) und meldet danach ``medien_schreibfehler``; eine Serie kann dann noch Folgen aufführen, deren Datei fehlt
  (``medien/pruefen`` räumt auf), oder eine leere neue Serie bleibt statt im Papierkorb liegen.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import dateien
from .const import COVER_EIGEN, EINSORTIERUNG_NEU_ALTER_MAX_S
from .fehler import TobiboxFehler
from .media import Serie, lese_serie, papierkorb_anlegen, schreibe_serie
from .namen import NamenErschoepft, eindeutiger_name, vergleichsschluessel
from .util import jetzt, jetzt_iso, neue_id12, parse_iso

if TYPE_CHECKING:
    from .eingang import Eingang, Gruppe
    from .hub import Hub
    from .schutz import Nutzer

_LOGGER = logging.getLogger(__name__)

RUECKWEG_VERSION = 1

#: Namen der sieben Prüfungen aus Vertrag W, 2.4 (in der Reihenfolge dort); nur für Protokoll und Tests, nie in der Ausgabe
PRUEFUNGEN = ("umbenannt", "verschoben", "tobie", "art_manuell", "cover_eigen", "angehoert", "fremde_folgen")


# --------------------------------------------------------------------------
# Mitschreiben beim Einsortieren (Aufruf aus ``eingang.py``)
# --------------------------------------------------------------------------


async def rueckweg_merken(
    eingang: Eingang, serie: Serie, pfad: Path, neu: bool, neue_folgen: list[tuple[Gruppe, str]], eintraege: dict[str, dict[str, Any]]
) -> None:
    """Hält fest, was dieses Einsortieren in der Serie getan hat. ``eintraege``: Name des Eingangs-Eintrags -> ``rueckweg``.

    Der ``stand`` kommt frisch von der Platte (so rechnet ihn später die Prüfung auch). Ein Fehler hier hält das Einsortieren nie auf:
    dann fehlt ``rueckweg``, und der Eintrag lässt sich nicht neu einsortieren."""
    try:

        def lies() -> tuple[Serie | None, bool]:
            fertig, _ = lese_serie(pfad)
            return fertig, (pfad / COVER_EIGEN).exists()

        von_platte, cover_eigen = await eingang.hub.hass.async_add_executor_job(lies)
        if von_platte is None:
            return
        serien_stand = {
            "neu": bool(neu),
            "name": von_platte.name,
            "stand": von_platte.stand,
            "art": von_platte.art,
            "art_quelle": von_platte.art_quelle,
            "cover_eigen": cover_eigen,
        }
        for g, endname in neue_folgen:
            rw = eintraege.setdefault(g.eintrag, {"v": RUECKWEG_VERSION, "serien": {}, "folgen": []})
            rw["serien"][serie.id] = dict(serien_stand)
            rw["folgen"].append(
                {
                    "serie_id": serie.id,
                    "folge": endname,
                    "anzeige": g.anzeige[:200],
                    "ist_ordner": bool(g.ist_ordner),
                    # Ordner-Folge: die Namen im Ordner; Datei-Folge: der Name der Folge selbst (kann ein „(2)“ tragen)
                    "dateien": [[g.zielnamen.get(d.rel, d.name), d.groesse] for d in g.dateien] if g.ist_ordner else [[endname, g.dateien[0].groesse]],
                }
            )
    except Exception:
        _LOGGER.exception("Rückweg beim Einsortieren nicht gemerkt")


# --------------------------------------------------------------------------
# Die sieben Prüfungen (2.4)
# --------------------------------------------------------------------------


@dataclass
class _Ist:
    """Die Serie, wie sie jetzt auf der Platte steht (``serie`` ist ``None``, wenn es sie nicht mehr gibt)."""

    serie: Serie | None
    pfad: Path | None = None
    cover_eigen: bool = False


async def _lies_ist(hub: Hub, rw: dict[str, Any]) -> dict[str, _Ist]:
    medien = hub.medien
    aus: dict[str, _Ist] = {}
    for sid in rw["serien"]:
        try:
            serie, pfad = await medien._frisch(sid)
        except TobiboxFehler as err:
            if err.code != "serie_nicht_gefunden":
                raise
            aus[sid] = _Ist(None)
            continue
        cover = await hub.hass.async_add_executor_job((pfad / COVER_EIGEN).exists)
        aus[sid] = _Ist(serie, pfad, cover)
    return aus


def _folgen_je_serie(rw: dict[str, Any]) -> dict[str, set[str]]:
    aus: dict[str, set[str]] = {sid: set() for sid in rw["serien"]}
    for f in rw["folgen"]:
        aus[f["serie_id"]].add(f["folge"])
    return aus


def _p_umbenannt(hub: Hub, rw: dict[str, Any], ist: dict[str, _Ist]) -> bool:
    """(1) Eine betroffene Serie oder Folge wurde umbenannt."""
    for sid, s in rw["serien"].items():
        cur = ist[sid].serie
        if cur is not None and cur.name != s["name"]:
            return True
    for f in rw["folgen"]:
        cur = ist[f["serie_id"]].serie
        if cur is not None and f["folge"] in cur.folgen and cur.info(f["folge"]).get("anzeige") != f["anzeige"]:
            return True
    return False


def _p_verschoben(hub: Hub, rw: dict[str, Any], ist: dict[str, _Ist]) -> bool:
    """(2) Eine Folge ist nicht mehr in ihrer Serie (verschoben, gelöscht) oder der ``stand`` der Serie weicht vom gemerkten ab (Reihenfolge)."""
    for sid, s in rw["serien"].items():
        cur = ist[sid].serie
        if cur is None or cur.stand != s["stand"]:
            return True
    return any(f["folge"] not in ist[f["serie_id"]].serie.folgen for f in rw["folgen"])  # type: ignore[union-attr]


def _p_tobie(hub: Hub, rw: dict[str, Any], ist: dict[str, _Ist]) -> bool:
    """(3) Ein Tobie zeigt auf eine betroffene Folge oder auf eine Serie, die der Eintrag neu angelegt hat (sie verschwindet)."""
    medien = hub.medien
    if any(s["neu"] and medien.tobies_der_serie(sid) for sid, s in rw["serien"].items()):
        return True
    return any(medien.tobies_der_folge(f["serie_id"], f["folge"]) for f in rw["folgen"])


def _p_art_manuell(hub: Hub, rw: dict[str, Any], ist: dict[str, _Ist]) -> bool:
    """(4) ``art_quelle`` ist ``manuell`` geworden (oder die Art hat sich geändert), seit der Eintrag einsortiert wurde.

    Ein Upload mit Wunsch legt seine Serie von Anfang an mit ``manuell`` an: das zählt nicht als Änderung."""
    for sid, s in rw["serien"].items():
        cur = ist[sid].serie
        if cur is None:
            continue
        if cur.art != s["art"] or (cur.art_quelle == "manuell" and s["art_quelle"] != "manuell"):
            return True
    return False


def _p_cover_eigen(hub: Hub, rw: dict[str, Any], ist: dict[str, _Ist]) -> bool:
    """(5) Eine betroffene Serie hat ein eigenes Cover (``cover-eigen.jpg``), das beim Einsortieren noch nicht da war."""
    return any(ist[sid].cover_eigen and not s["cover_eigen"] for sid, s in rw["serien"].items())


def _p_angehoert(hub: Hub, rw: dict[str, Any], ist: dict[str, _Ist]) -> bool:
    """(6) Irgendein Benutzer hat eine betroffene Folge angehört. Liest die Hörstellen aller Benutzer **nur intern** (ja oder nein)."""
    return any(hub.hoerstellen.hat_gehoert(sid, folgen) for sid, folgen in _folgen_je_serie(rw).items())


def _p_fremde_folgen(hub: Hub, rw: dict[str, Any], ist: dict[str, _Ist]) -> bool:
    """(7) In einer vom Eintrag neu angelegten Serie liegen Folgen, die nicht von diesem Eintrag stammen."""
    eigene = _folgen_je_serie(rw)
    for sid, s in rw["serien"].items():
        cur = ist[sid].serie
        if s["neu"] and cur is not None and set(cur.folgen) - eigene[sid]:
            return True
    return False


_PRUEFER = (_p_umbenannt, _p_verschoben, _p_tobie, _p_art_manuell, _p_cover_eigen, _p_angehoert, _p_fremde_folgen)


async def geaenderte_pruefungen(hub: Hub, rw: dict[str, Any]) -> list[str]:
    """Die Namen aller „etwas geändert“-Prüfungen (``PRUEFUNGEN``), die für diesen Eintrag zutreffen; leer: nichts geändert.

    Jede einzelne genügt für ``neu_einsortieren_nicht_moeglich``. Der Aufrufer hat die Serien gesperrt."""
    ist = await _lies_ist(hub, rw)
    return [name for name, pruefer in zip(PRUEFUNGEN, _PRUEFER, strict=True) if pruefer(hub, rw, ist)]


# --------------------------------------------------------------------------
# Der Befehl
# --------------------------------------------------------------------------


def _wunsch(ziel: str, art: str | None, name: str | None, serie_id: str | None) -> dict[str, Any]:
    """Der Wunsch wie beim Upload (14.4, dieselbe Prüfung); ohne gültigen Wunsch ``wunsch_ungueltig``. ``auto`` gibt es hier nicht."""
    from .http import _pruefe_wunsch  # erst hier: ``http`` kennt das Eingangs-Modul

    felder = {"ziel": ziel}
    if art:
        felder["art"] = art
    roh_name = name.encode("utf-8") if name is not None else None
    wunsch = _pruefe_wunsch(felder, roh_name, serie_id, None)
    if wunsch is None or wunsch["ziel"] == "auto":
        raise TobiboxFehler("wunsch_ungueltig")
    return wunsch


def _finde_zeile(eingang: Eingang, eintrag_id: str) -> dict[str, Any]:
    """Die jüngste Protokollzeile des Eintrags. Ein Eintrag, der noch offen ist, lässt sich nicht neu einsortieren."""
    zeile = next((p for p in reversed(eingang.protokoll) if p.get("id") == eintrag_id), None)
    if zeile is not None:
        return zeile
    if any(z.id == eintrag_id for z in eingang.eintraege.values()):
        raise TobiboxFehler("neu_einsortieren_nicht_moeglich")
    raise TobiboxFehler("eintrag_nicht_gefunden")


def _rueckweg_von(zeile: dict[str, Any]) -> dict[str, Any]:
    rw = zeile.get("rueckweg")
    if not isinstance(rw, dict) or rw.get("v") != RUECKWEG_VERSION or not rw.get("folgen"):
        raise TobiboxFehler("neu_einsortieren_nicht_moeglich")  # ein alter Eintrag: das Einsortieren hat nichts gemerkt
    return rw


def _alter_ok(zeile: dict[str, Any]) -> bool:
    if zeile.get("pruefen"):
        return True
    fertig = parse_iso(zeile.get("fertig_am"))
    return fertig is not None and (jetzt() - fertig).total_seconds() <= EINSORTIERUNG_NEU_ALTER_MAX_S


def _dateien_stimmen(quelle: Path, f: dict[str, Any]) -> bool:
    """Sind die Dateien der Folge genau die, die einsortiert wurden (Namen und Größen)? Läuft im Executor."""
    try:
        if f["ist_ordner"]:
            if not quelle.is_dir():
                return False
            vorhanden = {e.name: e.stat().st_size for e in os.scandir(quelle) if e.is_file() and dateien.ist_audio(e.name)}
            return vorhanden == {n: g for n, g in f["dateien"]}
        (name, groesse), = f["dateien"]
        return quelle.is_file() and quelle.name == name and quelle.stat().st_size == groesse
    except (OSError, ValueError):
        return False


def _hole_zurueck(auftraege: list[tuple[Path, Path]], ordner: Path | None) -> None:
    """Schritt 1 (Executor): legt ``ordner`` an (``None``: eine lose Datei, kein Ordner) und verschiebt jede Folge dorthin.
    Scheitert eines, kommt alles Verschobene zurück."""
    if ordner is not None:
        ordner.mkdir()
    fertig: list[tuple[Path, Path]] = []
    try:
        for quelle, ziel in auftraege:
            dateien.verschiebe_ohne_ueberschreiben(quelle, ziel)
            fertig.append((quelle, ziel))
    except BaseException:
        for quelle, ziel in reversed(fertig):
            try:
                if not os.path.lexists(quelle):
                    os.rename(ziel, quelle)
            except OSError:
                _LOGGER.error("Zurücklegen von %s nach %s fehlgeschlagen; die Folge liegt im Eingang (%s)", ziel, quelle, ordner)
        if ordner is not None:
            try:
                ordner.rmdir()  # klappt nur, wenn alles zurückgelegt ist
            except OSError:
                pass
        raise


async def neu_einsortieren(
    hub: Hub, eintrag_id: str, ziel: str, art: str | None, name: str | None, serie_id: str | None, nutzer: Nutzer | None
) -> dict[str, Any]:
    """Befehl 43 (Vertrag W): holt die Folgen des Eintrags in den Eingang zurück und sortiert sie mit dem neuen Wunsch neu ein.

    Gibt ``{"gestartet": True}`` zurück; das Ergebnis meldet der Eingang später als Ereignis ``neu_einsortiert``. Ablauf und Abbruch: siehe oben."""
    eingang = hub.eingang
    medien = hub.medien
    hub.schutz.papierkorb_pruefen(nutzer)
    await eingang._stelle_gescannt_sicher()
    if eingang.laeuft:
        raise TobiboxFehler("sortierung_laeuft")
    await medien._stelle_geprueft_sicher()
    await medien._medien_erreichbar()
    wunsch_fehler: TobiboxFehler | None = None
    wunsch: dict[str, Any] | None = None
    try:
        wunsch = _wunsch(ziel, art, name, serie_id)
    except TobiboxFehler as err:
        wunsch_fehler = err  # erst melden, wenn es den Eintrag gibt
    neuer_ordner = ""
    schreib_fehler: BaseException | None = None
    async with eingang.sperre:
        if eingang.laeuft:
            raise TobiboxFehler("sortierung_laeuft")
        zeile = _finde_zeile(eingang, eintrag_id)
        if wunsch_fehler is not None or wunsch is None:
            raise wunsch_fehler or TobiboxFehler("wunsch_ungueltig")
        if wunsch["ziel"] == "ergaenzen":
            info = medien.serien.get(serie_id or "")
            if info is None:
                raise TobiboxFehler("serie_nicht_gefunden")
            if info.serie.einzeln or info.serie.typ != "normal":
                raise TobiboxFehler("wunsch_ungueltig")  # in einen Einzeltitel kommen keine neuen Folgen (14.2)
        rw = _rueckweg_von(zeile)
        if not _alter_ok(zeile):
            raise TobiboxFehler("neu_einsortieren_nicht_moeglich")
        if wunsch["ziel"] == "ergaenzen" and (rw["serien"].get(serie_id) or {}).get("neu"):
            raise TobiboxFehler("wunsch_ungueltig")  # diese Serie ginge mit dem Eintrag in den Papierkorb
        async with medien.sperren(*rw["serien"]):
            geaendert = await geaenderte_pruefungen(hub, rw)
            if geaendert:
                _LOGGER.info("Eintrag %s lässt sich nicht neu einsortieren (Prüfungen: %s)", eintrag_id, ", ".join(geaendert))
                raise TobiboxFehler("neu_einsortieren_nicht_moeglich")
            ist = await _lies_ist(hub, rw)
            # --- 0. Die Dateien sind noch die einsortierten ---
            for f in rw["folgen"]:
                quelle = ist[f["serie_id"]].pfad / f["folge"]  # type: ignore[operator]
                if not await hub.hass.async_add_executor_job(_dateien_stimmen, quelle, f):
                    raise TobiboxFehler("neu_einsortieren_nicht_moeglich")
            # --- 1. Folgen in den Eingang ---
            belegt_eingang = {vergleichsschluessel(e.name) for e in await hub.hass.async_add_executor_job(lambda: list(os.scandir(hub.pfade.eingang)))}
            belegt_innen: set[str] = set()
            innen: list[str] = []  # Name jeder Folge im neuen Eintrag
            try:
                for f in rw["folgen"]:
                    unter = eindeutiger_name(f["folge"], belegt_innen, mit_endung=not f["ist_ordner"])
                    belegt_innen.add(vergleichsschluessel(unter))
                    innen.append(unter)
                # Der Eintrag heißt wie der alte, wenn der Name frei ist. Eine Datei im Eintrag darf nicht so heißen wie er selbst
                # (der Eingang kennt ``rel == eintrag`` als lose Datei): dann bekommt der Eintrag einen anderen Namen.
                loser_eintrag = len(innen) == 1 and not rw["folgen"][0]["ist_ordner"] and vergleichsschluessel(innen[0]) == vergleichsschluessel(zeile["name"])
                if loser_eintrag:
                    neuer_ordner = eindeutiger_name(innen[0], belegt_eingang, mit_endung=True)  # eine einzelne Datei liegt lose im Eingang
                else:
                    neuer_ordner = eindeutiger_name(zeile["name"], belegt_eingang | {vergleichsschluessel(u) for f, u in zip(rw["folgen"], innen, strict=True) if not f["ist_ordner"]}, mit_endung=False)
            except NamenErschoepft as err:
                raise medien._fehler_schreiben(err) from err
            ziel_ordner = hub.pfade.eingang / neuer_ordner
            auftraege: list[tuple[Path, Path]] = []
            rel_dateien: list[str] = []  # Pfad der Audiodateien im neuen Eintrag
            for f, unter in zip(rw["folgen"], innen, strict=True):
                if loser_eintrag:
                    auftraege.append((ist[f["serie_id"]].pfad / f["folge"], ziel_ordner))  # type: ignore[operator]
                    rel_dateien.append(neuer_ordner)
                    continue
                auftraege.append((ist[f["serie_id"]].pfad / f["folge"], ziel_ordner / unter))  # type: ignore[operator]
                if f["ist_ordner"]:
                    rel_dateien += [f"{unter}/{n}" for n, _g in f["dateien"]]
                else:
                    rel_dateien.append(unter)
            try:
                await hub.hass.async_add_executor_job(_hole_zurueck, auftraege, None if loser_eintrag else ziel_ordner)
            except OSError as err:
                raise medien._fehler_schreiben(err) from err
            # Ab hier liegen die Dateien im Eingang: nichts mehr wird zurückgenommen, ein Fehler wird nach Schritt 3 gemeldet.
            for f in rw["folgen"]:
                eingang.index_entferne_praefix(f"{ist[f['serie_id']].pfad.name}/{f['folge']}")  # type: ignore[union-attr]
            # --- 2. serie.json bereinigen, neue Serien in den Papierkorb ---
            geaenderte_serien: list[str] = []
            papierkorb_aenderung = False
            for sid, s in rw["serien"].items():
                serie, pfad = ist[sid].serie, ist[sid].pfad
                if serie is None or pfad is None:
                    continue
                weg = {f["folge"] for f in rw["folgen"] if f["serie_id"] == sid}
                serie.folgen = [n for n in serie.folgen if n not in weg]
                for n in weg:
                    serie.folgen_info.pop(n, None)
                    medien._pruefergebnisse.pop((pfad.name, n), None)
                    hub.medieninfo.loesche_folge(sid, n)
                try:
                    await hub.hass.async_add_executor_job(schreibe_serie, pfad, serie)
                    if s["neu"]:
                        summen = eingang.index_entferne_praefix(f"{pfad.name}/")
                        await hub.hass.async_add_executor_job(
                            lambda: papierkorb_anlegen(
                                hub.pfade.papierkorb,
                                pfad,
                                typ="serie",
                                grund="manuell",
                                serie_id=serie.id,
                                serie_name=serie.name,
                                serie_ordner=pfad.name,
                                serie_json=serie.to_json(),
                                pruefsummen=summen,
                                geloescht_von=nutzer.geloescht_von if nutzer else None,
                            )
                        )
                        medien.serien.pop(sid, None)
                        hub.medieninfo.loesche_serie_folgen(sid)
                        for k in [k for k in medien._pruefergebnisse if k[0] == pfad.name]:
                            medien._pruefergebnisse.pop(k, None)
                        papierkorb_aenderung = True
                    else:
                        await medien._aktualisiere_cache(serie, pfad.name)
                except OSError as err:
                    _LOGGER.error("Serie %s nach dem Zurückholen nicht bereinigt: %s", pfad.name, err)
                    schreib_fehler = err
                geaenderte_serien.append(sid)
            # --- 3. Wunsch festhalten, alte Zeile weg, speichern ---
            gruppe = None if wunsch["ziel"] == "einzeln" else neue_id12()
            wunsch_datei = dict(wunsch)
            if wunsch["ziel"] == "einzeln" and len(rel_dateien) > 1:
                wunsch_datei["name"] = None  # ein Name gilt für eine Datei; sonst heißt jede nach ihrem Titel
            jetzt_text = jetzt_iso()
            for rel in rel_dateien:
                eingang.vorgaben[rel if loser_eintrag else f"{neuer_ordner}/{rel}"] = {
                    "serie_id": serie_id if wunsch["ziel"] == "ergaenzen" else None,
                    "gruppe": gruppe,
                    "wunsch": dict(wunsch_datei),
                    "am": jetzt_text,
                }
            if zeile.get("quelle") == "upload":
                eingang.upload_quelle.add(neuer_ordner)
            eingang.protokoll = [p for p in eingang.protokoll if p is not zeile]
            # AM25: Zurückgeholte Dateien sind vollständig, also keine Ruhezeit: der Eintrag zählt für die Bereitschaft wie ein Upload
            # (``upload_eintraege``, nur im Speicher; nach einem Neustart gilt die Ruhezeit wieder). ``upload_quelle`` (Herkunft) bleibt wie oben.
            eingang.upload_eintraege.add(neuer_ordner)
            await eingang.speichern_sofort()
    # --- danach (ohne Sperre) ---
    nummer = {"typ": "einsortierung", "id": eintrag_id, "anzeige": zeile.get("name"), "geloescht_am": jetzt_iso()}
    hub.schutz.papierkorb_gebucht(nutzer, nummer, [])
    if geaenderte_serien:
        hub.emit("medien", "serien_geaendert", {"serie_ids": geaenderte_serien})
    if papierkorb_aenderung:
        hub.emit("medien", "papierkorb_geaendert", {})
    hub.emit("eingang", "geaendert", {})
    if schreib_fehler is not None:
        raise medien._fehler_schreiben(schreib_fehler) from schreib_fehler
    try:
        from .eingang import eintrag_id as id_von_name

        await eingang.starte_durchlauf([id_von_name(neuer_ordner)])  # erfasst den neuen Eintrag und sortiert ihn gleich ein (AM25)
    except TobiboxFehler:
        _LOGGER.debug("Durchlauf nach „Anders einsortieren“ nicht gestartet", exc_info=True)
    return {"gestartet": True}
