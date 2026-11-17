"""Lesen der Hördaten: Befehle 50 bis 54 (Stufe B, Paket B3; Vertrag W, 3.14 und 15; Design Abschnitt 6 und 11).

* Befehl 50 ``gehoert/zusammenfassung``: Rangliste, Aufteilung, Zeitreihen. Die Gruppierung macht SQLite (``GehoertDb.fasse_zusammen``, im Executor),
  alles Weitere (Wochen, Monate, gelöschte Serien, Raster mit Nullen, Sortierung) die Event-Loop mit den schon gruppierten Zeilen.
* Befehl 51 ``gehoert/zuletzt``, 52 ``technik/verlauf``, 53 ``gehoert/exportieren`` (CSV beim Abruf erzeugt, ``gehoert_export.py``), 54 ``gehoert/loeschen``.

Die Zeitrechnung ist **reine Datumsrechnung** in der Zeitzone von HA: ``tag`` und ``stunde`` stehen schon in der Zeile (gerechnet beim Einfügen),
„heute“ ist das Datum jetzt in der Zeitzone von HA. Dadurch gibt es mit der Sommerzeit keine Sonderfälle (Tage sind Kalendertage, Mitternacht Ortszeit).
"""

from __future__ import annotations

import csv
import io
import logging
import re
import unicodedata
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

from .const import (
    GEHOERT_LIMIT_VORGABE,
    GEHOERT_SPANNE_MAX_JAHRE,
    GEHOERT_ZEILEN_MAX,
    GEHOERT_ZULETZT_LIMIT_MAX,
    RE_BOX,
    TECHNIK_LISTE_MAX,
    TECHNIK_SPANNE_MAX_TAGE,
)
from .fehler import TobiboxFehler
from .namen import natuerlicher_schluessel
from .util import iso, jetzt

if TYPE_CHECKING:
    from .gehoert import Gehoert

_LOGGER = logging.getLogger(__name__)

ZEITSCHLUESSEL = ("tag", "woche", "monat", "stunde")
NACH_WERTE = ("wer", "serie", "folge", *ZEITSCHLUESSEL)
ZEITRAEUME = ("woche", "monat", "jahr", "alles")
SORTIERUNGEN = ("sekunden", "mal")
#: Spalte der Tabelle ``sitzungen`` je Schlüssel (``woche`` und ``monat`` werden aus ``tag`` gerechnet)
SPALTE = {"wer": "quelle", "serie": "serie", "folge": "folge", "tag": "tag", "woche": "tag", "monat": "tag", "stunde": "stunde"}
RE_TAG = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_BENUTZER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
GELOESCHT_NAME = "Gelöscht"
FRUEHERER_BENUTZER = "Früherer Benutzer"
LOESCH_WORTE = ("LÖSCHEN", "LOESCHEN")
#: Zellen, die so beginnen, würde eine Tabellenkalkulation als Formel lesen (``'`` davor entschärft sie; Vertrag W, Nr. 53)
FORMEL_ANFAENGE = ("=", "+", "-", "@", "\t", "\r")
EXPORT_SPALTEN = ("Beginn", "Ende", "Quelle", "Serie", "Folge", "Hörzeit (s)", "Ende der Sitzung", "Mal neu", "fertig", "Datum")
DATUM_TEXT = {"sicher": "sicher", "ungefaehr": "ungefähr", "unbekannt": "unbekannt"}


# --------------------------------------------------------------------------------------------
# Reine Hilfen (ohne Home Assistant testbar)
# --------------------------------------------------------------------------------------------


def parse_tag(text: Any) -> date:
    """``JJJJ-MM-TT`` streng; sonst ``invalid_format``."""
    if not isinstance(text, str) or not RE_TAG.match(text):
        raise TobiboxFehler("invalid_format")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise TobiboxFehler("invalid_format") from None


def plus_jahre(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 29. Februar oder Jahr über 9999
        try:
            return d.replace(year=d.year + n, day=28)
        except ValueError:
            return date.max


def zeit_schluessel(art: str, tag: date) -> str:
    """Der Schlüssel der Zeile: ``woche`` als ``JJJJ-Www`` (ISO-Woche, Montag), ``monat`` als ``JJJJ-MM``, ``tag`` als ``JJJJ-MM-TT``."""
    if art == "woche":
        iso_jahr, woche, _ = tag.isocalendar()
        return f"{iso_jahr}-W{woche:02d}"
    if art == "monat":
        return f"{tag.year}-{tag.month:02d}"
    return tag.isoformat()


def raster(art: str, von: date, bis: date) -> list[str | int]:
    """Alle Schlüssel von ``von`` bis ``bis`` (einschließlich), aufsteigend und lückenlos. Mehr als ``GEHOERT_ZEILEN_MAX`` Rasterzeilen: ``invalid_format``."""
    if art == "stunde":
        return list(range(24))
    tage = (bis - von).days + 1
    if tage < 1:
        raise TobiboxFehler("invalid_format")
    if art == "tag" and tage > GEHOERT_ZEILEN_MAX:
        raise TobiboxFehler("invalid_format")
    aus: list[str | int] = []
    letzter: str | None = None
    for i in range(tage):
        k = zeit_schluessel(art, von + timedelta(days=i))
        if k != letzter:
            aus.append(k)
            letzter = k
    if len(aus) > GEHOERT_ZEILEN_MAX:
        raise TobiboxFehler("invalid_format")
    return aus


def pruefe_wer_form(wer: Any, sammel: tuple[str, ...]) -> str:
    """Die **Form** von ``wer`` bzw. ``quelle``: ein Wort aus ``sammel`` oder ``box:<Name>`` oder ``benutzer:<id>``; sonst ``wer_ungueltig``."""
    if not isinstance(wer, str):
        raise TobiboxFehler("wer_ungueltig")
    if wer in sammel:
        return wer
    art, _, name = wer.partition(":")
    if art == "box" and RE_BOX.match(name):
        return wer
    if art == "benutzer" and RE_BENUTZER_ID.match(name):
        return wer
    raise TobiboxFehler("wer_ungueltig")


def quelle_sql(wer: str) -> tuple[str, tuple]:
    """Der Filter auf die Spalte ``quelle`` (``wer`` ist schon geprüft)."""
    if wer == "alle":
        return "1 = 1", ()
    if wer in ("alle_boxen", "boxen"):
        return "substr(quelle, 1, 4) = 'box:'", ()
    if wer == "reinhoeren":
        return "substr(quelle, 1, 9) = 'benutzer:'", ()
    return "quelle = ?", (wer,)


def passt_wer(wer: str, quelle: str) -> bool:
    """Gilt der Filter ``wer`` (wie ``quelle_sql``) für diese Quelle?"""
    if wer == "alle":
        return True
    if wer in ("alle_boxen", "boxen"):
        return quelle.startswith("box:")
    if wer == "reinhoeren":
        return quelle.startswith("benutzer:")
    return quelle == wer


def sortname(text: str) -> tuple:
    return natuerlicher_schluessel(text or "")


def csv_zelle(wert: Any) -> str:
    text = "" if wert is None else str(wert)
    return "'" + text if text.startswith(FORMEL_ANFAENGE) else text


def baue_csv(zeilen: list[list[Any]]) -> bytes:
    """CSV, UTF-8 **mit BOM**, Trenner ``;``, erste Zeile die Spaltennamen; jede Zelle gegen Formeln entschärft."""
    puffer = io.StringIO()
    schreiber = csv.writer(puffer, delimiter=";", lineterminator="\r\n")
    schreiber.writerow(EXPORT_SPALTEN)
    for z in zeilen:
        schreiber.writerow([csv_zelle(x) for x in z])
    return ("﻿" + puffer.getvalue()).encode("utf-8")


def export_dateiname(quelle: str, heute: date) -> str:
    """``gehoert-<quelle>-<datum>.csv`` (``:`` wird zu ``-``)."""
    return f"gehoert-{quelle.replace(':', '-')}-{heute.isoformat()}.csv"


# --------------------------------------------------------------------------------------------
# Die Abfragen
# --------------------------------------------------------------------------------------------


class GehoertAbfragen:
    """``hub.gehoert.abfrage``: die lesenden und löschenden Befehle der Hördaten."""

    def __init__(self, gehoert: Gehoert) -> None:
        self.gehoert = gehoert

    # --- Hilfen -----------------------------------------------------------------------------------

    @property
    def hub(self):
        return self.gehoert.hub

    def _db(self):
        db = self.gehoert.db
        if db is None:  # ohne Datenbank gibt es die Fähigkeit ``gehoert`` nicht (Vertrag W, 14.1)
            raise TobiboxFehler("unknown_command")
        return db

    @staticmethod
    def _zone():
        return dt_util.get_default_time_zone()

    def _heute(self) -> date:
        return jetzt().astimezone(self._zone()).date()

    async def quellen_in_db(self) -> list[str]:
        return await self.gehoert._lauf(self._db().quellen)

    async def _person(self, benutzer_id: str):
        try:
            return await self.hub.hass.auth.async_get_user(benutzer_id)
        except (ValueError, KeyError):  # pragma: no cover
            return None

    async def wer_auswahl(self, quellen_db: list[str]) -> list[dict[str, str]]:
        """Alle Quellen, die es je gab (unabhängig vom Filter): erst die Boxen (eingerichtete in ihrer Reihenfolge, dann alte mit Daten), dann die Personen
        nach Name. Ein gelöschter Benutzer heißt „Früherer Benutzer“."""
        hub = self.hub
        boxen = list(hub.boxen) + sorted({q[4:] for q in quellen_db if q.startswith("box:")} - set(hub.boxen))
        aus: list[dict[str, str]] = [{"wer": f"box:{b}", "name": hub.box_anzeige(b), "art": "box"} for b in boxen]
        personen = []
        for q in quellen_db:
            if q.startswith("benutzer:"):
                nutzer = await self._person(q[9:])
                personen.append({"wer": q, "name": (nutzer.name if nutzer is not None and nutzer.name else FRUEHERER_BENUTZER), "art": "person"})
        personen.sort(key=lambda p: (sortname(p["name"]), p["wer"]))
        return aus + personen

    async def pruefe_quelle(self, wer: str, quellen_db: list[str]) -> None:
        """``box:<Name>`` gilt für eine eingerichtete Box oder eine, zu der es Daten gibt; ``benutzer:<id>`` für einen Benutzer, den es in HA gibt oder zu dem es Daten
        gibt. Sonst ``wer_ungueltig`` (Vertrag W, Abschnitt 7).

        # B3-OFFEN: Der Vertrag nennt ``wer_ungueltig`` für „eine Box, die nicht eingerichtet ist“. Eine ausgebaute Box mit alten Daten steht aber in ``wer_auswahl``
        (alle Quellen, die es je gab) und ihre Daten müssen sich löschen lassen: sie gilt hier darum als gültig. Ohne Daten gilt der Vertrag wörtlich."""
        if wer.startswith("box:"):
            if wer[4:] not in self.hub.boxen and wer not in quellen_db:
                raise TobiboxFehler("wer_ungueltig")
        elif wer.startswith("benutzer:") and wer not in quellen_db and await self._person(wer[9:]) is None:
            raise TobiboxFehler("wer_ungueltig")

    # --- 50: gehoert/zusammenfassung ----------------------------------------------------------------

    async def zusammenfassung(
        self,
        *,
        nach: list[str],
        wer: str = "alle",
        zeitraum: str | None = None,
        von: str | None = None,
        bis: str | None = None,
        serie_id: str | None = None,
        sortierung: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        db = self._db()
        hub = self.hub
        # --- Eingabe prüfen: jede verbotene Kombination ist invalid_format (Design, 11)
        if (zeitraum is not None) == (von is not None or bis is not None) or (von is None) != (bis is None):
            raise TobiboxFehler("invalid_format")
        if len(set(nach)) != len(nach) or not 1 <= len(nach) <= 2:
            raise TobiboxFehler("invalid_format")
        zeit_art = [k for k in nach if k in ZEITSCHLUESSEL]
        if len(zeit_art) > 1 or ("serie" in nach and "folge" in nach) or ("folge" in nach and serie_id is None):
            raise TobiboxFehler("invalid_format")
        zeit_art = zeit_art[0] if zeit_art else None
        if zeit_art is not None and (sortierung is not None or limit is not None):
            raise TobiboxFehler("invalid_format")
        wer = pruefe_wer_form(wer, ("alle", "alle_boxen"))
        von_tag = parse_tag(von) if von is not None else None
        bis_tag = parse_tag(bis) if bis is not None else None
        # B3-OFFEN: „höchstens 3 Jahre“: ``bis`` darf bis zum gleichen Kalendertag drei Jahre nach ``von`` reichen (einschließlich)
        if von_tag is not None and bis_tag is not None and (bis_tag < von_tag or bis_tag > plus_jahre(von_tag, GEHOERT_SPANNE_MAX_JAHRE)):
            raise TobiboxFehler("invalid_format")
        await hub.medien._stelle_geprueft_sicher()
        serien = hub.medien.serien
        if serie_id is not None and serie_id not in serien:
            raise TobiboxFehler("serie_nicht_gefunden")
        quellen_db = await self.quellen_in_db()
        await self.pruefe_quelle(wer, quellen_db)

        # --- Filter und Zeitraum
        wo_teile, params = [quelle_sql(wer)[0]], list(quelle_sql(wer)[1])
        if serie_id is not None:
            wo_teile.append("serie = ?")
            params.append(serie_id)
        heute = self._heute()
        if zeitraum == "alles":
            erster = await self.gehoert._lauf(db.erster_tag, " AND ".join(wo_teile), tuple(params))
            von_tag, bis_tag = (date.fromisoformat(erster) if erster else heute), heute
        elif zeitraum is not None:
            tage = {"woche": 6, "monat": 29, "jahr": 364}[zeitraum]
            von_tag, bis_tag = heute - timedelta(days=tage), heute
        assert von_tag is not None and bis_tag is not None
        # Ein Zeitraum (nicht „Alles“ als Rangliste) schließt unbekanntes Datum aus; Zeitreihen brauchen immer ein Datum.
        # B3-OFFEN: Zeilen mit unbekanntem Datum haben in einer Zeitreihe keinen Platz im Raster; sie fehlen auch in ``summe`` (so ist ``summe`` die Summe der Zeilen).
        if zeitraum != "alles" or zeit_art is not None:
            wo_teile.append("tag >= ? AND tag <= ?")
            params += [von_tag.isoformat(), bis_tag.isoformat()]

        # --- Raster der Zeitreihe (vor der Abfrage: zu große Anfragen kosten nichts)
        auswahl = await self.wer_auswahl(quellen_db)
        namen_wer = {a["wer"]: a["name"] for a in auswahl}
        zeiten = raster(zeit_art, von_tag, bis_tag) if zeit_art else None
        # B3-OFFEN: Das Raster Zeit × Quellen nimmt die Quellen aus ``wer_auswahl``, die der Filter ``wer`` zulässt (bei ``alle`` also alle, wie im Vertrag).
        quellen_raster = [a["wer"] for a in auswahl if passt_wer(wer, a["wer"])] if zeit_art and "wer" in nach else None
        if zeiten is not None and quellen_raster is not None and len(zeiten) * len(quellen_raster) > GEHOERT_ZEILEN_MAX:
            raise TobiboxFehler("invalid_format")

        # --- Abfrage (Executor)
        spalten = list(dict.fromkeys(SPALTE[k] for k in nach))
        folgen_felder = "folge" not in nach and ("serie" in nach or serie_id is not None)
        gruppen, fertige, summe = await self.gehoert._lauf(db.fasse_zusammen, " AND ".join(wo_teile), tuple(params), spalten, folgen_felder)

        # --- Zeilen in der Event-Loop
        folge_anzeige: dict[str, str] = {}
        if serie_id is not None and "folge" in nach:
            folge_anzeige = {o["name"]: o.get("anzeige") or o["name"] for o in serien[serie_id].folgen_objekte}

        def schluessel(r: dict[str, Any]) -> tuple:
            teile: list[Any] = []
            for k in nach:
                if k == "wer":
                    teile.append(r["quelle"])
                elif k == "serie":
                    teile.append(r["serie"] if r["serie"] in serien else None)  # eine Serie, die es nicht mehr gibt: alle in einer Zeile
                elif k == "folge":
                    teile.append(r["folge"])
                elif k == "stunde":
                    teile.append(r["stunde"])
                else:
                    teile.append(zeit_schluessel(k, date.fromisoformat(r["tag"])))
            return tuple(teile)

        werte: dict[tuple, list[int]] = {}
        for r in gruppen:
            w = werte.setdefault(schluessel(r), [0, 0, 0])
            w[0] += r["sekunden"] or 0
            w[1] += r["mal"] or 0
            w[2] += r["fertig"] or 0
        fertige_folgen: dict[tuple, set[str]] = {}
        folgen_je_serie: dict[str, frozenset[str]] = {}
        for r in fertige:
            serie = (r["serie"] if "serie" in nach else serie_id)
            if serie not in serien:
                continue
            if serie not in folgen_je_serie:
                folgen_je_serie[serie] = frozenset(serien[serie].serie.folgen)
            if r["folge"] in folgen_je_serie[serie]:
                fertige_folgen.setdefault(schluessel(r), set()).add(r["folge"])

        def zeile(k: tuple, w: list[int]) -> dict[str, Any]:
            aus: dict[str, Any] = {}
            serie = serie_id
            for name, v in zip(nach, k, strict=True):
                aus[name] = v
                if name == "serie":
                    serie = v
                    aus["name"], aus["geloescht"] = (GELOESCHT_NAME, True) if v is None else (serien[v].serie.name, False)
            aus["sekunden"], aus["mal"], aus["fertig"] = w
            if folgen_felder:  # B3-OFFEN: die Sammelzeile der gelöschten Serien trägt 0 und 0 (der Vertrag nennt sie dort nicht)
                aus["folgen_fertig"] = len(fertige_folgen.get(k, ()))
                aus["folgen_gesamt"] = len(serien[serie].serie.folgen) if serie in serien else 0
            return aus

        def name_von(k: tuple) -> tuple:
            teile = []
            for name, v in zip(nach, k, strict=True):
                if name == "serie":
                    teile.append(sortname(GELOESCHT_NAME if v is None else serien[v].serie.name))
                elif name == "wer":
                    teile.append(sortname(namen_wer.get(v, v)))
                elif name == "folge":
                    teile.append(sortname(folge_anzeige.get(v, v)))
                else:
                    teile.append(v)
            return tuple(teile)

        weitere = False
        if zeit_art is not None:
            assert zeiten is not None
            leer = [0, 0, 0]
            if "wer" in nach:
                reihenfolge = [(t, q) if nach.index(zeit_art) < nach.index("wer") else (q, t) for t in zeiten for q in (quellen_raster or [])]
                zeilen = [zeile(k, werte.get(k, leer)) for k in reihenfolge]
            elif len(nach) == 1:
                zeilen = [zeile((t,), werte.get((t,), leer)) for t in zeiten]
            else:  # Zeit zusammen mit Serie oder Folge: nur die vorhandenen Kombinationen
                pos_zeit = nach.index(zeit_art)
                rang = {t: i for i, t in enumerate(zeiten)}
                ks = sorted(werte, key=lambda k: (rang[k[pos_zeit]], name_von(k)))
                if len(ks) > GEHOERT_ZEILEN_MAX:
                    raise TobiboxFehler("invalid_format")
                zeilen = [zeile(k, werte[k]) for k in ks]
        else:
            index = 1 if (sortierung or "sekunden") == "mal" else 0
            ks = sorted(werte, key=lambda k: (-werte[k][index], name_von(k)))
            grenze = limit if limit is not None else GEHOERT_LIMIT_VORGABE
            weitere = len(ks) > grenze
            zeilen = [zeile(k, werte[k]) for k in ks[:grenze]]

        return {
            "zeilen": zeilen,
            "summe": {"sekunden": summe[0], "mal": summe[1], "fertig": summe[2]},
            "weitere": weitere,
            "wer_auswahl": auswahl,
            "zeitzone": str(self._zone()),
            "von": von_tag.isoformat(),
            "bis": bis_tag.isoformat(),
        }

    # --- 51: gehoert/zuletzt ------------------------------------------------------------------------

    async def zuletzt(self, wer: str, limit: int, nutzer_id: str | None) -> dict[str, Any]:
        db = self._db()
        hub = self.hub
        if not 1 <= limit <= GEHOERT_ZULETZT_LIMIT_MAX:
            raise TobiboxFehler("invalid_format")
        wer = pruefe_wer_form(wer, ("alle", "alle_boxen"))
        await self.pruefe_quelle(wer, await self.quellen_in_db())
        await hub.medien._stelle_geprueft_sicher()
        await self.gehoert.zwischenspeicher()
        sql, params = quelle_sql(wer)
        zeilen = await self.gehoert._lauf(db.zuletzt_je_serie, sql, params)
        zaehler = hub.medien.bibliothek.tobie_zaehler()
        eintraege = []
        for serie, zeit, quelle in zeilen:
            info = hub.medien.serien.get(serie)
            if info is None:  # eine Serie, die es nicht mehr gibt, steht nicht in der Reihe
                continue
            eintraege.append({**hub.medien.kurzform(info, zaehler, nutzer_id), "wer": quelle, "zeit": iso(datetime.fromtimestamp(zeit, UTC))})
            if len(eintraege) >= limit:
                break
        return {"eintraege": eintraege}

    # --- 52: technik/verlauf ------------------------------------------------------------------------

    async def technik_verlauf(self, box: str, von: str, bis: str) -> dict[str, Any]:
        db = self._db()
        von_tag, bis_tag = parse_tag(von), parse_tag(bis)
        if bis_tag < von_tag or (bis_tag - von_tag).days + 1 > TECHNIK_SPANNE_MAX_TAGE:  # B3-OFFEN: „höchstens 400 Tage“ = 400 Kalendertage einschließlich ``bis``
            raise TobiboxFehler("invalid_format")
        if box not in self.hub.boxen:
            raise TobiboxFehler("box_unbekannt")
        zone = self._zone()
        von_s = int(datetime(von_tag.year, von_tag.month, von_tag.day, tzinfo=zone).timestamp())
        ende_tag = bis_tag + timedelta(days=1)
        bis_s = int(datetime(ende_tag.year, ende_tag.month, ende_tag.day, tzinfo=zone).timestamp())
        roh = await self.gehoert._lauf(db.technik_lies, box, von_s, bis_s)
        return baue_verlauf(roh["zeilen"], roh["vorher"], roh["danach"])

    # --- 53: gehoert/exportieren (der Abruf: ``gehoert_export.py``) -----------------------------------

    async def pruefe_export_quelle(self, quelle: str) -> str:
        quelle = pruefe_wer_form(quelle, ("boxen", "reinhoeren", "alle"))
        await self.pruefe_quelle(quelle, await self.quellen_in_db())
        return quelle

    async def export_csv(self, quelle: str) -> tuple[bytes, str]:
        """Die Datei beim Abruf: ``(Bytes, Dateiname)``. Zeiten in der Zeitzone von HA; ``Quelle`` ist der Anzeigename."""
        db = self._db()
        quelle = await self.pruefe_export_quelle(quelle)
        hub = self.hub
        await hub.medien._stelle_geprueft_sicher()
        sql, params = quelle_sql(quelle)
        zeilen = await self.gehoert._lauf(db.zeilen_fuer_export, sql, params)
        # B3-OFFEN: ``Quelle`` ist der Anzeigename (Box, Person), ``Folge`` der Titel der Folge, wenn es sie gibt, sonst der gespeicherte Name; ``Serie`` „Gelöscht“, wenn es sie nicht mehr gibt
        namen = {a["wer"]: a["name"] for a in await self.wer_auswahl(await self.quellen_in_db())}
        zone = self._zone()
        serien = hub.medien.serien

        def zeit(sekunden: int) -> str:
            return datetime.fromtimestamp(sekunden, zone).strftime("%Y-%m-%d %H:%M:%S")

        aus = []
        for z in zeilen:
            info = serien.get(z["serie"])
            folge = z["folge"]
            if info is not None:
                folge = next((o.get("anzeige") or folge for o in info.folgen_objekte if o["name"] == folge), folge)
            bekannt = z["datum"] != "unbekannt"
            aus.append(
                [
                    zeit(z["beginn"]) if bekannt else "",
                    zeit(z["ende_um"]) if bekannt else "",
                    namen.get(z["quelle"], z["quelle"]),
                    info.serie.name if info is not None else GELOESCHT_NAME,
                    folge,
                    z["gehoert_s"],
                    z["ende"],
                    "ja" if z["mal_zaehlt"] else "nein",  # B3-OFFEN: „Mal neu“ = erste Sitzung eines Mals, das zählt (so summiert die Spalte zur Zahl „Mal“)
                    "ja" if z["fertig"] else "nein",
                    DATUM_TEXT.get(z["datum"], z["datum"]),
                ]
            )
        return baue_csv(aus), export_dateiname(quelle, self._heute())

    # --- 54: gehoert/loeschen -----------------------------------------------------------------------

    async def konkrete_quellen(self, quelle: str, quellen_db: list[str]) -> list[str]:
        """Die konkreten Quellen hinter ``quelle``: ``boxen`` = eingerichtete Boxen und Boxen mit Daten, ``reinhoeren`` = alle Benutzer mit Daten."""
        boxen = sorted({f"box:{b}" for b in self.hub.boxen} | {q for q in quellen_db if q.startswith("box:")})
        personen = sorted(q for q in quellen_db if q.startswith("benutzer:"))
        if quelle == "boxen":
            return boxen
        if quelle == "reinhoeren":
            return personen
        if quelle == "alle":
            return boxen + personen
        return [quelle]

    async def loeschen(self, quelle: str, trocken: bool, bestaetigung: str | None) -> dict[str, int]:
        db = self._db()
        quelle = pruefe_wer_form(quelle, ("boxen", "reinhoeren", "alle"))
        if not trocken and (not isinstance(bestaetigung, str) or unicodedata.normalize("NFC", bestaetigung) not in LOESCH_WORTE):
            raise TobiboxFehler("invalid_format")
        quellen_db = await self.quellen_in_db()
        await self.pruefe_quelle(quelle, quellen_db)
        konkret = await self.konkrete_quellen(quelle, quellen_db)
        if trocken:
            return {"anzahl": await self.gehoert._lauf(db.zaehle, konkret)}
        anzahl = await self.gehoert.loesche(konkret)
        # offene Reinhör-Sitzungen der betroffenen Benutzer im Arbeitsspeicher gehören zu den gelöschten Daten
        # B3-OFFEN: (Ergänzung) Der Vertrag sagt dazu nichts; sonst schriebe eine laufende Sitzung die Hörzeit vor der Löschung wieder hinein.
        self.hub.reinhoeren.verwirf([q[9:] for q in konkret if q.startswith("benutzer:")])
        return {"anzahl": anzahl}


# --------------------------------------------------------------------------------------------
# Befehl 52: Verlauf aus den Zeilen der Tabelle ``technik``
# --------------------------------------------------------------------------------------------


def _zeitstempel(sekunden: int) -> str:
    return iso(datetime.fromtimestamp(sekunden, UTC))


def baue_verlauf(zeilen: list[dict[str, Any]], vorher: dict[str, Any] | None, danach: dict[str, Any] | None) -> dict[str, Any]:
    """Ladevorgänge, Laufzeiten, Verbindung, Syncs, Fehler und verworfene Hördaten (Vertrag W, Nr. 52).

    * ``ladevorgaenge``: ``lader_an`` bis zum nächsten ``lader_aus``; ohne ``lader_aus`` bleiben ``ende`` und ``dauer_s`` ``null``. War das Laden schon vor
      dem Zeitraum an (``vorher``), beginnt der erste Vorgang früher.
    * ``laufzeiten``: von ``lader_aus`` bis zum nächsten ``lader_an`` oder ``offline`` (``danach`` kennt, was nach dem Zeitraum kommt); ohne Ende ``null``.
    * ``weitere``: eine Liste wurde bei ``TECHNIK_LISTE_MAX`` Einträgen gekürzt."""
    laden: list[dict[str, Any]] = []
    laufzeiten: list[dict[str, Any]] = []
    verbindung: list[dict[str, Any]] = []
    syncs: list[dict[str, Any]] = []
    fehler: list[dict[str, Any]] = []
    verworfen: list[dict[str, Any]] = []
    # B3-OFFEN: Der Vertrag lässt offen, wie Ladevorgänge und Laufzeiten an den Rändern des Zeitraums gelten: ein Laden oder eine Laufzeit, die vor ``von``
    # begann, erscheint mit ihrem wahren Beginn (``vorher``); was nach ``bis`` endet, endet mit dem ersten Wechsel danach (``danach``) oder bleibt offen (``null``).
    offen_an: int | None = vorher["zeit"] if vorher and vorher["art"] == "lader_an" else None
    auf_akku: int | None = vorher["zeit"] if vorher and vorher["art"] == "lader_aus" else None  # ``lader_aus`` ohne Ende
    for z in zeilen:
        zeit, art, wert = z["zeit"], z["art"], z["wert"]
        if art == "lader_an":
            if offen_an is None:
                offen_an = zeit
            if auf_akku is not None:
                laufzeiten.append({"von": _zeitstempel(auf_akku), "bis": _zeitstempel(zeit), "dauer_s": zeit - auf_akku})
                auf_akku = None
        elif art == "lader_aus":
            if offen_an is not None:
                laden.append({"beginn": _zeitstempel(offen_an), "ende": _zeitstempel(zeit), "dauer_s": zeit - offen_an})
                offen_an = None
            auf_akku = zeit
        elif art in ("online", "offline"):
            verbindung.append({"zeit": _zeitstempel(zeit), "online": art == "online"})
            if art == "offline" and auf_akku is not None:
                laufzeiten.append({"von": _zeitstempel(auf_akku), "bis": _zeitstempel(zeit), "dauer_s": zeit - auf_akku})
                auf_akku = None
        elif art in ("sync_ok", "sync_fehler"):
            syncs.append({"zeit": _zeitstempel(zeit), "ok": art == "sync_ok", "code": wert if art == "sync_fehler" else None})
        elif art == "fehler":
            fehler.append({"zeit": _zeitstempel(zeit), "code": wert})
        elif art == "verworfen":
            try:
                gesamt = int(wert) if wert is not None else None
            except ValueError:
                gesamt = None
            verworfen.append({"zeit": _zeitstempel(zeit), "gesamt": gesamt})
    if offen_an is not None:
        laden.append({"beginn": _zeitstempel(offen_an), "ende": None, "dauer_s": None})
    if auf_akku is not None:
        if danach is not None:
            laufzeiten.append({"von": _zeitstempel(auf_akku), "bis": _zeitstempel(danach["zeit"]), "dauer_s": danach["zeit"] - auf_akku})
        else:
            laufzeiten.append({"von": _zeitstempel(auf_akku), "bis": None, "dauer_s": None})
    listen = {"ladevorgaenge": laden, "laufzeiten": laufzeiten, "verbindung": verbindung, "syncs": syncs, "fehler": fehler, "verworfen": verworfen}
    weitere = False
    for name, liste in listen.items():
        if len(liste) > TECHNIK_LISTE_MAX:
            listen[name] = liste[:TECHNIK_LISTE_MAX]
            weitere = True
    return {**listen, "weitere": weitere}
