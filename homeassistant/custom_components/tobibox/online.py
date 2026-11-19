"""Online-Suche, Paket OS3: Store ``tobibox.online``, Dienst, Schlange, Lauf, Übernahme, Rücknahme (Design ``online-suche.md`` 5 bis 7).

* ``OnlineStore``: der HA-``Store`` ``tobibox.online`` (Version 1, ``minor_version`` 1, Migrationsfunktion) und die Pflegestellen (7.3).
* ``OnlineDienst`` (``hub.online``): holt Daten über ``online_quellen`` und bewertet sie mit ``online_abgleich`` (beide aus OS2, unverändert).

  - 5.1 beim Einsortieren: ``neu_einsortiert`` legt nur in die Schlange; ein Hintergrund-Task arbeitet sie ab (eine Serie zugleich).
  - 5.2 Suche von Hand: ``suchen`` (Nr. 57), ``treffer`` (Nr. 58), ``uebernehmen`` (Nr. 59).
  - 5.3 Lauf über den Rest: ``lauf_starten``/``lauf_stoppen`` (Nr. 62), ``status`` (Nr. 63).
  - 5.4 Vorschläge: ``vorschlag_verwerfen`` (Nr. 61). 5.5 Prüfgründe.
  - 6.3/6.4 Übernahme (offen, Dateien, fertig) und Rücknahme (Nr. 60), ``beschreibung`` (Nr. 64).

Die WebSocket-Befehle selbst stehen nicht hier; jede Methode liefert genau die Ausgabe des Vertrags (Vertrag W, 3.15) oder wirft ``TobiboxFehler``
mit dem Vertragscode. Alles Netz läuft ohne Sperre, geschrieben wird nur unter der Serien-Sperre. Die Quellen, die Uhr und das Schlafen sind
austauschbar (Tests ohne Netz). Ein Ausfall einer Quelle macht nie etwas kaputt: Der Eintrag bleibt, wie er ist (O9).
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import hashlib
import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Final

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from . import online_abgleich as ab
from .const import (
    CONF_ONLINE_KI_ENTITAET,
    COVER_ONLINE,
    FOLGE_ANZEIGE_MAX,
    ONLINE_AENDERUNGEN_MAX,
    ONLINE_AENDERUNGEN_TAGE,
    ONLINE_BESCHREIBUNG_KURZ,
    ONLINE_BESCHREIBUNG_MAX,
    ONLINE_MARKE_FEHLER_TAGE,
    ONLINE_MARKE_KEINER_TAGE,
    ONLINE_STAND_BUENDEL_S,
    ONLINE_TREFFER_BILDER,
    ONLINE_TREFFER_MAX,
    ONLINE_UEBERSPRUNGEN_MAX,
    ONLINE_VERWORFEN_MAX,
    SERIE_NAME_MAX,
)
from .cover import cover_pruefen_und_skalieren, cover_zustand, loesche_datei, online_stand, schreibe_bytes_atomar
from .fehler import TobiboxFehler
from .media import Serie, name_pruefen, schreibe_serie
from .namen import vergleichsschluessel
from .neu_einsortieren import rueckweg_fortschreiben
from .online_ki import OnlineKi
from .online_ki import ART_BEHALTEN, ART_FEHLER, ART_VERWORFEN, ART_VORSCHLAG, ART_AUS, ART_UEBERSPRUNGEN, baue_eingabe
from .online_quellen import (
    FormatFehler,
    Gedrosselt,
    OnlineFehler,
    OnlineQuellen,
    QuellePausiert,
    TonieListe,
    bild_url_600,
    html_zu_text,
    lese_version,
    online_text,
)
from .util import iso, jetzt_iso, neue_id12, parse_iso

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Konstanten (die Grenzen aus Vertrag W, 3.15, „Grenzen“, stehen in ``const.py``; hier nur, was der Dienst allein braucht)
# --------------------------------------------------------------------------

STORAGE_KEY: Final = "tobibox.online"
STORAGE_VERSION: Final = 1
STORAGE_MINOR: Final = 1
SPEICHER_VERZOEGERUNG_S: Final = 10.0

LAEUFE_MAX: Final = 5

MARKE_KEINER_S: Final = ONLINE_MARKE_KEINER_TAGE * 86400
MARKE_FEHLER_S: Final = ONLINE_MARKE_FEHLER_TAGE * 86400
MARKE_CLAUDE_FEHLER_S: Final = 86400
PAUSEN_BIS_ABBRUCH: Final = 3
CLAUDE_MAX_FOLGEN: Final = 12
VORSCHLAG_MAX: Final = 30

#: Zustände des Laufs
LAUF_LAUFEND: Final = ("laeuft", "pausiert", "wird_angehalten")
LAUF_ENDE: Final = ("fertig", "angehalten", "abgebrochen")

#: Felder je Folge (alle übrigen gelten für den Eintrag)
FOLGEN_FELDER: Final = ("folge_titel", "nummer", "beschreibung", "alter_ab")
EINTRAG_FELDER: Final = ("serie_name", "art", "cover")
GRUENDE_NAME: Final = ab.GRUND_SERIE_NAME  # serie_aus_interpret, serie_aus_ordner

ZURUECK_GRUENDE: Final = ("seitdem_geaendert", "serie_nicht_gefunden", "folge_verschoben")


def feld_key(feld: str, folge: str | None = None) -> str:
    return feld if folge is None else f"{feld}@{folge}"


def teile_key(key: str) -> tuple[str, str | None]:
    """``feld@folge`` -> ``(feld, folge)``; getrennt wird am **ersten** ``@``."""
    feld, sep, folge = key.partition("@")
    return feld, (folge if sep else None)


def _zeit_iso(t: float | None) -> str | None:
    return iso(datetime.fromtimestamp(t, UTC)) if t is not None else None


def _alt_s(zeit_text: Any, jetzt_s: float) -> float:
    z = parse_iso(zeit_text)
    return jetzt_s - z.timestamp() if z else float("inf")


def beschreibung_text(text: Any) -> str | None:
    """Beschreibung vor dem Schreiben: jede Zeile durch ``online_text`` (Steuerzeichen weg), Absätze (Zeilen) bleiben, höchstens 2 000 Zeichen."""
    if not isinstance(text, str):
        return None
    zeilen = [z for z in (online_text(z, ONLINE_BESCHREIBUNG_MAX) for z in text.splitlines()) if z]
    return "\n".join(zeilen)[:ONLINE_BESCHREIBUNG_MAX].strip() or None


def kuerzen_am_satzende(text: str, maximum: int = ONLINE_BESCHREIBUNG_KURZ) -> tuple[str, bool]:
    """Auf ``maximum`` Zeichen gekürzt, am Satzende wenn möglich (``serie/get``, R4)."""
    if len(text) <= maximum:
        return text, False
    kopf = text[:maximum]
    ende = max(kopf.rfind(". "), kopf.rfind("! "), kopf.rfind("? "), kopf.rfind(".\n"))
    if ende >= maximum // 3:
        return kopf[: ende + 1].strip(), True
    wort = kopf.rsplit(" ", 1)[0] if " " in kopf else kopf
    return wort.rstrip(" ,;:") + "…", True


def wert_hash(feld: str, wert: Any, quelle: str, kennung: Any = None) -> str:
    """Hash über (Feld, normalisierter Wert, Quelle); beim Cover über die Kennung der Quelle (``collectionId``) (7.3)."""
    roh = str(kennung) if kennung is not None else ab.norm(str(wert))
    return hashlib.sha256(f"{feld}|{roh}|{quelle}".encode()).hexdigest()[:16]


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------


class OnlineSpeicher(Store[dict[str, Any]]):
    """``tobibox.online``: Version 1, ``minor_version`` 1, Migration nur vorwärts (7.3, GB-24)."""

    async def _async_migrate_func(self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]) -> dict[str, Any]:
        if old_major_version > STORAGE_VERSION:
            raise NotImplementedError("tobibox.online stammt aus einer neueren Version")
        return old_data  # 1.0 -> 1.1: keine Änderung der Form


def _leer() -> dict[str, Any]:
    return {"serien": {}, "laeufe": []}


class OnlineStore:
    """Der Store samt den Pflegestellen (7.3): ``folge_umbenannt``, ``loesche_folge``, ``loesche_serie``, ``bereinige``."""

    def __init__(self, hass: HomeAssistant, zeit: Callable[[], float] = time.time) -> None:
        self._store = OnlineSpeicher(hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_MINOR)
        self._zeit = zeit
        self.daten: dict[str, Any] = _leer()

    # --- Laden und Speichern ---

    async def laden(self) -> None:
        roh = await self._store.async_load()
        self.daten = _leer()
        if isinstance(roh, dict):
            serien = roh.get("serien")
            if isinstance(serien, dict):
                self.daten["serien"] = {k: v for k, v in serien.items() if isinstance(k, str) and isinstance(v, dict)}
            laeufe = roh.get("laeufe")
            if isinstance(laeufe, list):
                self.daten["laeufe"] = [x for x in laeufe if isinstance(x, dict) and isinstance(x.get("lauf_id"), str)][-LAEUFE_MAX:]

    async def sofort(self) -> None:
        """„sofort“ (7.3): vor der nächsten Wirkung auf die Platte."""
        # Eine Kopie: HA schreibt im Executor, der Event-Loop ändert ``daten`` währenddessen (Lauf, Schlange, Befehle)
        await self._store.async_save(copy.deepcopy(self.daten))

    def bald(self, verzoegerung: float = SPEICHER_VERZOEGERUNG_S) -> None:
        """„verzögert“ (und für synchrone Stellen: ``verzoegerung=0``)."""
        self._store.async_delay_save(lambda: copy.deepcopy(self.daten), verzoegerung)

    # --- Zugriff ---

    def lies(self, sid: str) -> dict[str, Any]:
        """Der Eintrag der Serie oder ein leeres Dict (wird nicht angelegt)."""
        return self.daten["serien"].get(sid) or {}

    def serie(self, sid: str) -> dict[str, Any]:
        return self.daten["serien"].setdefault(sid, {})

    def _aufraeumen(self, sid: str) -> None:
        s = self.daten["serien"].get(sid)
        if s is None:
            return
        for k in ("schnapp", "hand", "zurueckgenommen"):
            v = s.get(k)
            if isinstance(v, dict) and not (v.get("folgen") or any(x for kk, x in v.items() if kk != "folgen")):
                s.pop(k, None)
        for k in ("folgen", "aenderungen", "vorschlaege", "verworfen"):
            if k in s and not s[k]:
                s.pop(k, None)
        if not s:
            self.daten["serien"].pop(sid, None)

    # --- Folge-Schlüssel in ``schnapp``, ``hand``, ``zurueckgenommen`` ---

    def hand_hat(self, sid: str, key: str) -> bool:
        return self._hat(self.lies(sid).get("hand"), key)

    def zurueck_hat(self, sid: str, key: str) -> bool:
        return self._hat(self.lies(sid).get("zurueckgenommen"), key)

    @staticmethod
    def _hat(block: Any, key: str) -> bool:
        if not isinstance(block, dict):
            return False
        feld, folge = teile_key(key)
        if folge is None:
            return bool(block.get(feld))
        return feld in (block.get("folgen") or {}).get(folge, ())

    def _setze(self, sid: str, block: str, key: str) -> None:
        feld, folge = teile_key(key)
        b = self.serie(sid).setdefault(block, {})
        if folge is None:
            b[feld] = True
        else:
            liste = b.setdefault("folgen", {}).setdefault(folge, [])
            if feld not in liste:
                liste.append(feld)

    def _nimm(self, sid: str, block: str, key: str) -> None:
        b = self.lies(sid).get(block)
        if not isinstance(b, dict):
            return
        feld, folge = teile_key(key)
        if folge is None:
            b.pop(feld, None)
        else:
            liste = (b.get("folgen") or {}).get(folge)
            if liste and feld in liste:
                liste.remove(feld)
                if not liste:
                    b["folgen"].pop(folge, None)
        self._aufraeumen(sid)

    def setze_hand(self, sid: str, key: str) -> None:
        self._setze(sid, "hand", key)
        self._nimm(sid, "zurueckgenommen", key)  # ein neuer Wert von Hand ersetzt die Marke (6.1)

    def setze_zurueckgenommen(self, sid: str, key: str) -> None:
        self._setze(sid, "zurueckgenommen", key)
        self._nimm(sid, "hand", key)

    def nimm_hand(self, sid: str, key: str) -> None:
        self._nimm(sid, "hand", key)

    # --- Schnappschuss ---

    def schnapp_wert(self, sid: str, key: str) -> tuple[bool, Any]:
        """``(gibt es einen Schnappschuss, Wert)``. ``art`` einmal je Eintrag; Folge-Felder ``anzeige`` (= ``folge_titel``) und ``nummer``.
        Hat die Folge einen Eintrag, aber ohne ``nummer``, war die Nummer beim Einsortieren leer."""
        sn = self.lies(sid).get("schnapp") or {}
        feld, folge = teile_key(key)
        if feld == "art":
            return ("art" in sn), sn.get("art")
        if folge is None:
            return False, None
        f = (sn.get("folgen") or {}).get(folge)
        if f is None:
            return False, None
        return True, f.get("anzeige" if feld == "folge_titel" else feld)

    def setze_schnapp(self, sid: str, key: str, wert: Any) -> None:
        sn = self.serie(sid).setdefault("schnapp", {})
        feld, folge = teile_key(key)
        if feld == "art":
            sn["art"] = wert
        elif folge is not None:
            f = sn.setdefault("folgen", {}).setdefault(folge, {})
            name = "anzeige" if feld == "folge_titel" else feld
            if wert is None:
                f.pop(name, None)
            else:
                f[name] = wert

    def schnapp_zurueck(self, sid: str, key: str, vorher: dict[str, Any]) -> None:
        """Den Schnappschuss **eines** Felds auf den Stand ``vorher`` (ein früherer ``schnapp``-Block) zurückstellen; andere Felder bleiben (GO3-7)."""
        feld, folge = teile_key(key)
        if feld not in ("art", "folge_titel", "nummer"):
            return
        if feld == "art":
            if "art" in vorher:
                self.setze_schnapp(sid, key, vorher["art"])
            else:
                self.loesche_schnapp(sid, key)
            return
        if folge is None:
            return
        name = "anzeige" if feld == "folge_titel" else feld
        f = (vorher.get("folgen") or {}).get(folge)
        if f is None:
            self.loesche_schnapp(sid, key)
        elif name in f:
            self.setze_schnapp(sid, key, f[name])
        else:
            sn = self.lies(sid).get("schnapp")
            if isinstance(sn, dict) and folge in (sn.get("folgen") or {}):
                sn["folgen"][folge].pop(name, None)  # die Folge hatte beim Einsortieren keinen Wert (Eintrag bleibt als Merkmal)

    def loesche_schnapp(self, sid: str, key: str) -> None:
        sn = self.lies(sid).get("schnapp")
        if not isinstance(sn, dict):
            return
        feld, folge = teile_key(key)
        if feld == "art":
            sn.pop("art", None)
        elif folge is not None:
            f = (sn.get("folgen") or {}).get(folge)
            if f is not None:
                f.pop("anzeige" if feld == "folge_titel" else feld, None)
                if not f:
                    sn["folgen"].pop(folge, None)
        self._aufraeumen(sid)

    # --- Beschreibung und Alter je Folge ---

    def folge_info(self, sid: str, folge: str) -> dict[str, Any]:
        return (self.lies(sid).get("folgen") or {}).get(folge) or {}

    def setze_folge_info(self, sid: str, folge: str, **felder: Any) -> None:
        f = self.serie(sid).setdefault("folgen", {}).setdefault(folge, {})
        for k, v in felder.items():
            if v is None:
                f.pop(k, None)
            else:
                f[k] = v
        f["zeit"] = jetzt_iso()
        if not any(k in f for k in ("beschreibung", "alter_ab")):
            self.serie(sid)["folgen"].pop(folge, None)
            self._aufraeumen(sid)
        else:
            self.bald()

    # --- Marken ---

    def marke(self, sid: str) -> dict[str, Any] | None:
        m = self.lies(sid).get("marke")
        return m if isinstance(m, dict) and m.get("ergebnis") else None

    def marke_gueltig(self, sid: str, folgen: list[str], liste_stand: float | None) -> bool:
        """Gültige Marke „schon gesucht“ (5.3 a): ``geaendert``/``vorschlag`` immer, ``keiner`` 30 Tage und ``fehler`` 1 Tag, beide nur bei gleicher Tonie-Liste;
        alle ``folgen`` stehen in der Marke."""
        m = self.marke(sid)
        if m is None:
            return False
        if not set(folgen) <= set(m.get("folgen") or ()):
            return False
        if m["ergebnis"] in ("geaendert", "vorschlag"):
            return True
        if m["ergebnis"] not in ("keiner", "fehler"):
            return False
        grenze = MARKE_FEHLER_S if m["ergebnis"] == "fehler" else MARKE_KEINER_S
        return _alt_s(m.get("zeit"), self._zeit()) < grenze and m.get("liste") == liste_stand

    def setze_marke(self, sid: str, ergebnis: str, folgen: list[str], liste_stand: float | None, *, dazu: bool = True) -> None:
        s = self.serie(sid)
        alt = s.get("marke") if isinstance(s.get("marke"), dict) else {}
        vorher = set(alt.get("folgen") or ()) if dazu and alt.get("ergebnis") else set()
        neu: dict[str, Any] = {"ergebnis": ergebnis, "zeit": jetzt_iso(), "folgen": sorted(vorher | set(folgen)), "liste": liste_stand}
        if "claude" in alt:
            neu["claude"] = alt["claude"]
        s["marke"] = neu
        self.bald()

    def claude_marke(self, sid: str) -> dict[str, Any] | None:
        m = self.lies(sid).get("marke") or {}
        c = m.get("claude") if isinstance(m, dict) else None
        return c if isinstance(c, dict) and c.get("ergebnis") else None

    def claude_gueltig(self, sid: str, option_gesetzt: bool) -> bool:
        """Gültige Marke des Claude-Schritts (3.4, GO-2): ``vorschlag``/``behalten`` nie, ``fehler`` 1 Tag, ``aus`` nur solange die Option leer ist."""
        c = self.claude_marke(sid)
        if c is None:
            return False
        if c["ergebnis"] in ("vorschlag", "behalten"):
            return True
        if c["ergebnis"] == "fehler":
            return _alt_s(c.get("zeit"), self._zeit()) < MARKE_CLAUDE_FEHLER_S
        if c["ergebnis"] == "aus":
            return not option_gesetzt
        return False

    def setze_claude_marke(self, sid: str, ergebnis: str) -> None:
        s = self.serie(sid)
        m = s.get("marke") if isinstance(s.get("marke"), dict) else {}
        m["claude"] = {"ergebnis": ergebnis, "zeit": jetzt_iso()}
        s["marke"] = m
        self.bald()

    # --- Änderungen ---

    def aenderungen(self, sid: str) -> list[dict[str, Any]]:
        return self.lies(sid).get("aenderungen") or []

    def verfall_aenderungen(self, sid: str) -> None:
        """Höchstens 20, höchstens 30 Tage (älteste zuerst); ``offen`` bleibt."""
        liste = self.lies(sid).get("aenderungen")
        if not liste:
            return
        jetzt_s = self._zeit()
        neu = [a for a in liste if a.get("status") == "offen" or _alt_s(a.get("zeit"), jetzt_s) <= ONLINE_AENDERUNGEN_TAGE * 86400]
        if len(neu) > ONLINE_AENDERUNGEN_MAX:
            neu = neu[-ONLINE_AENDERUNGEN_MAX:]
        if len(neu) != len(liste):
            self.serie(sid)["aenderungen"] = neu
            self._aufraeumen(sid)

    # --- Vorschläge, Verworfenes ---

    def vorschlaege(self, sid: str) -> list[dict[str, Any]]:
        return self.lies(sid).get("vorschlaege") or []

    def verworfen_hat(self, sid: str, feld: str, hash_: str, quelle: str) -> bool:
        return any(v.get("feld") == feld and v.get("wert_hash") == hash_ and v.get("quelle") == quelle for v in self.lies(sid).get("verworfen") or [])

    def verwirf(self, sid: str, feld: str, hash_: str, quelle: str) -> None:
        liste = self.serie(sid).setdefault("verworfen", [])
        if not self.verworfen_hat(sid, feld, hash_, quelle):
            liste.append({"feld": feld, "wert_hash": hash_, "quelle": quelle})
            del liste[:-ONLINE_VERWORFEN_MAX]

    # --- Läufe ---

    def lauf_speichern(self, lauf: dict[str, Any]) -> None:
        liste = self.daten["laeufe"]
        for i, x in enumerate(liste):
            if x["lauf_id"] == lauf["lauf_id"]:
                liste[i] = lauf
                break
        else:
            liste.append(lauf)
        del liste[:-LAEUFE_MAX]

    # --- Pflegestellen (7.3) ---

    def loesche_folge(self, sid: str, folge: str) -> None:
        """Folge gelöscht oder zurück in den Eingang geholt: ihre Schlüssel fallen weg; ``aenderungen`` bleiben (Rücknahme meldet ``folge_verschoben``)."""
        s = self.daten["serien"].get(sid)
        if s is None:
            return
        (s.get("folgen") or {}).pop(folge, None)
        for blockname in ("schnapp", "hand", "zurueckgenommen"):
            b = s.get(blockname)
            if isinstance(b, dict):
                (b.get("folgen") or {}).pop(folge, None)
        m = s.get("marke")
        if isinstance(m, dict) and folge in (m.get("folgen") or ()):
            m["folgen"] = [f for f in m["folgen"] if f != folge]
        self._vorschlaege_ohne_folge(s, folge)
        self._aufraeumen(sid)
        self.bald(0)

    @staticmethod
    def _vorschlaege_ohne_folge(s: dict[str, Any], folge: str) -> None:
        neu = []
        for v in s.get("vorschlaege") or []:
            if v.get("art") == "felder":
                bleibt = [k for k in v.get("felder") or [] if teile_key(k)[1] != folge]
                if not bleibt:
                    continue
                v["felder"] = bleibt
                v["werte"] = {k: w for k, w in (v.get("werte") or {}).items() if k in bleibt}
            neu.append(v)
        if "vorschlaege" in s:
            s["vorschlaege"] = neu

    def loesche_serie(self, sid: str) -> None:
        self.daten["serien"].pop(sid, None)
        for andere, s in list(self.daten["serien"].items()):
            alt = s.get("vorschlaege")
            if alt:
                s["vorschlaege"] = [v for v in alt if v.get("ziel_serie_id") != sid]
                self._aufraeumen(andere)
        self.bald(0)

    def folge_umbenannt(self, sid: str, alt: str, ziel_sid: str, neu: str) -> None:
        """Eine Folge wandert (Verschieben, Zusammenführen) oder bekommt im Ziel einen anderen Namen: ``folgen.<f>``, ``schnapp``, ``hand``,
        ``zurueckgenommen`` und die offenen Vorschläge ziehen mit, ``feld@folge`` wird umbenannt. Änderungen bleiben bei der Quelle."""
        s = self.daten["serien"].get(sid)
        if s is None:
            return
        z = self.serie(ziel_sid)

        def zieh(block: Any, ziel_block: dict[str, Any]) -> None:
            if isinstance(block, dict) and alt in (block.get("folgen") or {}):
                ziel_block.setdefault("folgen", {})[neu] = block["folgen"].pop(alt)

        if alt in (s.get("folgen") or {}):
            z.setdefault("folgen", {})[neu] = s["folgen"].pop(alt)
        for blockname in ("schnapp", "hand", "zurueckgenommen"):
            zieh(s.get(blockname), z.setdefault(blockname, {}))
        m = s.get("marke")
        if isinstance(m, dict) and alt in (m.get("folgen") or ()):
            m["folgen"] = [f for f in m["folgen"] if f != alt]
        # Vorschläge: die Felder dieser Folge gehen als eigener Vorschlag ins Ziel
        rest = []
        for v in s.get("vorschlaege") or []:
            if v.get("art") != "felder":
                rest.append(v)
                continue
            mit = [k for k in v.get("felder") or [] if teile_key(k)[1] == alt]
            ohne = [k for k in v.get("felder") or [] if k not in mit]
            if mit:
                neuer = {kk: vv for kk, vv in v.items() if kk not in ("felder", "werte", "id")}
                neuer["id"] = neue_id12()
                neuer["felder"] = [feld_key(teile_key(k)[0], neu) for k in mit]
                neuer["werte"] = {feld_key(teile_key(k)[0], neu): (v.get("werte") or {}).get(k) for k in mit}
                z.setdefault("vorschlaege", []).append(neuer)
            if ohne:
                v["felder"] = ohne
                v["werte"] = {k: (v.get("werte") or {}).get(k) for k in ohne}
                rest.append(v)
        if "vorschlaege" in s:
            s["vorschlaege"] = rest
        self._aufraeumen(sid)
        self._aufraeumen(ziel_sid)
        self.bald(0)

    def serie_zusammengefuehrt(self, quelle: str, ziel: str, cover_kopiert: bool) -> None:
        """Nach dem Zusammenführen: ``hand.cover`` und ``zurueckgenommen.cover`` ziehen mit, wenn das Cover kopiert wurde (GO-17); der Rest der Quelle fällt weg."""
        q = self.lies(quelle)
        if cover_kopiert:
            for block in ("hand", "zurueckgenommen"):
                if (q.get(block) or {}).get("cover") and not self.lies(ziel).get(block, {}).get("cover"):
                    self.serie(ziel).setdefault(block, {})["cover"] = True
        self.loesche_serie(quelle)

    def bereinige(self, bekannt: dict[str, list[str]]) -> int:
        """Beim Start (nach gelungener Prüfung der Freigabe): Werte zu Serien und Folgen, die es nicht mehr gibt. Gibt die Zahl der entfernten Serien und Folgen zurück."""
        entfernt = 0
        for sid in list(self.daten["serien"]):
            if sid not in bekannt:
                self.daten["serien"].pop(sid)
                entfernt += 1
                continue
            vorhanden = set(bekannt[sid])
            s = self.daten["serien"][sid]
            namen: set[str] = set(s.get("folgen") or ())
            for blockname in ("schnapp", "hand", "zurueckgenommen"):
                b = s.get(blockname)
                if isinstance(b, dict):
                    namen |= set(b.get("folgen") or ())
            for f in namen - vorhanden:
                self.loesche_folge(sid, f)
                entfernt += 1
            self.verfall_aenderungen(sid)
            self._aufraeumen(sid)
        if entfernt:
            self.bald()
        return entfernt


# --------------------------------------------------------------------------
# Dienst
# --------------------------------------------------------------------------


class OnlineDienst:
    """``hub.online``."""

    def __init__(
        self,
        hub: Hub,
        *,
        quellen: OnlineQuellen | None = None,
        tonie_liste: TonieListe | None = None,
        ki: OnlineKi | None = None,
        zeit: Callable[[], float] = time.time,
        schlafen: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self.hub = hub
        self._zeit = zeit
        self._schlafen = schlafen
        self.store = OnlineStore(hub.hass, zeit)
        self.quellen: OnlineQuellen | None = quellen
        self.tonie_liste: TonieListe | None = tonie_liste
        self.ki = ki or OnlineKi(zeit)
        self._index_cache: tuple[Any, dict[str, Any]] | None = None
        self._queue: dict[str, dict[str, Any]] = {}
        self._queue_task: asyncio.Task | None = None
        self._lauf_task: asyncio.Task | None = None
        self._rueck_task: asyncio.Task | None = None
        self._rueck_lauf_id: str | None = None  # der Lauf, dessen Rücknahme gerade läuft
        self._rueck_wartend: list[str] = []  # Läufe, deren Rücknahme hinten ansteht
        self._lauf: dict[str, Any] | None = None  # der laufende Lauf (Arbeitsspeicher; ``laeufe`` im Store hält auch ihn)
        self._stop = False
        self._stop_ereignis = asyncio.Event()  # weckt einen schlafenden Lauf, wenn ``stop`` kommt (GO3-12)
        self._startet = False  # ``lauf_starten`` ist unterwegs (GO3-9)
        self._arbeit = asyncio.Lock()  # eine Serie zugleich (5.1, 5.3)
        self._quelle_stand: dict[str, bool] = {}
        self._rueck_lauf: dict[str, Any] | None = None
        self._claude_lauf_ids: set[str] = set()
        self.gestartet = False

    # --- Start und Ende ---

    async def async_laden(self) -> None:
        await self.store.laden()
        # Ein Lauf, der beim Beenden noch lief, gilt als abgebrochen (HA-Neustart, 5.3, GO-12)
        for lauf in self.store.daten["laeufe"]:
            if lauf.get("zustand") in LAUF_LAUFEND:
                lauf.update(zustand="abgebrochen", grund="neustart", ende=jetzt_iso())
                self.store.bald()
        self.gestartet = True

    async def async_speichern(self) -> None:
        with contextlib.suppress(Exception):
            await self.store.sofort()

    async def async_stop(self) -> None:
        """``Hub.async_stop``: Tasks abbrechen und abwarten, Store speichern."""
        tasks = [t for t in (self._queue_task, self._lauf_task, self._rueck_task) if t is not None and not t.done()]
        for t in tasks:
            t.cancel()
        for t in tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t
        self._queue.clear()
        if self._lauf is not None and self._lauf["zustand"] in LAUF_LAUFEND:
            # Das Beenden von HA bricht einen Lauf ab; beim nächsten Start steht er als ``abgebrochen`` (Neustart) im Store
            self._lauf.update(zustand="abgebrochen", grund="neustart", ende=jetzt_iso())
            self.store.lauf_speichern(self._lauf_store(self._lauf))
        await self.async_speichern()

    async def beim_start(self) -> None:
        """Nach der ersten Prüfung der Freigabe (nur wenn sie gelang): offene Änderungen klären, Verwaistes wegräumen (6.3, 7.3)."""
        medien = self.hub.medien
        if medien.geprueft_am is None:
            return
        await self._offene_klaeren()
        self.store.bereinige({sid: list(i.serie.folgen) for sid, i in medien.serien.items()})
        for sid in list(self.store.daten["serien"]):
            self.store.verfall_aenderungen(sid)
        await self.store.sofort()

    async def _offene_klaeren(self) -> None:
        """Ein Absturz zwischen „offen“ und „fertig“: trägt das Feld den Online-Wert, ``fertig``; sonst verwerfen und den Schnappschuss wiederherstellen."""
        medien = self.hub.medien
        for sid, s in list(self.store.daten["serien"].items()):
            liste = s.get("aenderungen") or []
            if not any(a.get("status") == "offen" for a in liste):
                continue
            info = medien.serien.get(sid)
            neu = []
            for a in liste:
                if a.get("status") != "offen":
                    neu.append(a)
                    continue
                if info is not None and self._werte_stimmen(sid, info, a, "nachher"):
                    a["status"] = "fertig"
                    a.pop("schnapp_vorher", None)
                    neu.append(a)
                else:
                    for key in a.get("felder") or {}:
                        self.store.schnapp_zurueck(sid, key, a.get("schnapp_vorher") or {})  # nur die Felder dieser Änderung (GO3-7)
            s["aenderungen"] = neu
        self.store.bald(0)

    def _werte_stimmen(self, sid: str, info: Any, a: dict[str, Any], seite: str) -> bool:
        serie = info.serie
        for key, wv in (a.get("felder") or {}).items():
            feld, folge = teile_key(key)
            soll = wv.get(seite)
            if feld == "serie_name":
                ist: Any = serie.name
            elif feld == "art":
                ist = {"art": serie.art, "art_quelle": serie.art_quelle}
            elif feld == "cover":
                ist = {"quelle": info.cover_quelle}
                if soll is not None and soll != ist and not (info.cover_quelle == "eigen"):
                    return False
                continue
            elif folge is None or folge not in serie.folgen:
                return False
            elif feld == "folge_titel":
                ist = serie.info(folge).get("anzeige")
            elif feld == "nummer":
                ist = serie.info(folge).get("nummer")
            else:
                ist = self.store.folge_info(sid, folge).get(feld)
            if ist != soll:
                return False
        return True

    # --- Hilfen: Quellen, Index, Option ---

    async def _quellen_bereit(self) -> OnlineQuellen:
        if self.quellen is None:
            self.quellen = await self._baue_quellen()
        if self.tonie_liste is None:
            pfad = Path(self.hub.hass.config.path("tobibox", "tonies.json"))
            self.tonie_liste = TonieListe(self.quellen, pfad)
        return self.quellen

    async def _baue_quellen(self) -> OnlineQuellen:
        version = await self.hub.hass.async_add_executor_job(lese_version)  # liest ``manifest.json``: im Executor
        return OnlineQuellen(async_get_clientsession(self.hub.hass), version=version, zeit=self._zeit)

    def ki_entitaet(self) -> str | None:
        """Die ``ai_task``-Entität: Schlüssel in den Optionen (oder, vom Einrichten her, in den Daten) gesetzt: dieser Wert, ``""`` heißt „aus“;
        fehlt der Schlüssel überall, gilt die Vorgabe (genau eine Claude-Entität, sonst keine). Wird bei jedem Aufruf gelesen (wirkt ohne Neustart)."""
        entry = self.hub.entry
        if CONF_ONLINE_KI_ENTITAET in entry.options:
            wert = entry.options[CONF_ONLINE_KI_ENTITAET]
        elif CONF_ONLINE_KI_ENTITAET in entry.data:
            wert = entry.data[CONF_ONLINE_KI_ENTITAET]
        else:
            from .config_flow import vorgabe_ki_entitaet  # erst hier: ``config_flow`` kennt den Hub nicht

            wert = vorgabe_ki_entitaet(self.hub.hass)
        return (wert.strip() if isinstance(wert, str) else "") or None

    async def _index(self) -> dict[str, Any]:
        """Der Tonie-Index; wird nur bei einer neuen Liste neu gebaut (im Executor)."""
        liste = self.tonie_liste
        assert liste is not None and self.quellen is not None
        schluessel = (liste.stand, liste.anzahl)
        if self._index_cache is None or self._index_cache[0] != schluessel:
            eintraege = list(liste.eintraege)
            index = await self.quellen.im_executor(ab.tonie_index_bauen, eintraege)
            self._index_cache = (schluessel, index)
        return self._index_cache[1]

    @staticmethod
    def _leerer_index() -> dict[str, Any]:
        return {"eintraege": [], "index": {}}

    # --- Ereignisse ---

    def _emit(self, art: str, daten: dict[str, Any]) -> None:
        self.hub.emit("online", art, daten)

    def _emit_stand(self, vorgang: str, daten_fn: Callable[[], dict[str, Any]]) -> None:
        self.hub.emit_gebuendelt(("online", "stand", vorgang), "online", "stand", daten_fn, ONLINE_STAND_BUENDEL_S)

    def _melde_quelle(self, quelle: str, erreichbar: bool, pause_bis: float | None = None) -> None:
        if self._quelle_stand.get(quelle, True) != erreichbar:
            daten: dict[str, Any] = {"quelle": quelle, "erreichbar": erreichbar}
            if pause_bis is not None and not erreichbar:
                daten["pause_bis"] = _zeit_iso(pause_bis)
            self._emit("quelle", daten)
        self._quelle_stand[quelle] = erreichbar

    def _melde_tonies(self) -> None:
        """Die Tonie-Liste meldet ihre Pause (Vertrag 4.11: Wechsel aller drei Quellen); gleiche Regel wie ``status`` (GO3-13)."""
        q = self.quellen
        bis = q.pause_bis("tonies") if q is not None else None
        self._melde_quelle("tonies", bis is None, bis)

    def _serien_geaendert(self, *sids: str) -> None:
        self.hub.emit("medien", "serien_geaendert", {"serie_ids": sorted(set(sids))})

    # --- Pflegestellen (7.3): ``media.py`` und ``neu_einsortieren.py`` rufen den Dienst, er reicht an den Store weiter ---

    def folge_umbenannt(self, sid: str, alt: str, ziel_sid: str, neu: str) -> None:
        self.store.folge_umbenannt(sid, alt, ziel_sid, neu)

    def loesche_folge(self, sid: str, folge: str) -> None:
        self.store.loesche_folge(sid, folge)

    def loesche_serie(self, sid: str) -> None:
        self.store.loesche_serie(sid)

    def serie_zusammengefuehrt(self, quelle: str, ziel: str, cover_kopiert: bool) -> None:
        self.store.serie_zusammengefuehrt(quelle, ziel, cover_kopiert)

    # ----------------------------------------------------------------------
    # Zugriffe für die Ausgabe (``serie/get``, ``serien/list``): nicht in ``media.py`` verdrahtet
    # ----------------------------------------------------------------------

    def kurz_online(self, sid: str) -> dict[str, Any] | None:
        """Feld ``online`` der Kurzform (für alle): ``{"zeit", "felder"}`` der letzten Änderung (Status ``fertig``), jünger als 30 Tage, sonst ``None``.
        Ein angenommener Claude-Name ist keine Änderung und steht nie darin (GO-14)."""
        jetzt_s = self._zeit()
        for a in reversed(self.store.aenderungen(sid)):
            # Eine reine Bestätigung (``felder`` leer, nur ``bestaetigt``) ändert nichts am Eintrag und steht nie in ``online`` (GO3-1)
            if a.get("status") == "fertig" and a.get("felder") and _alt_s(a.get("zeit"), jetzt_s) <= ONLINE_AENDERUNGEN_TAGE * 86400:
                felder: list[str] = []
                for k in a.get("felder") or {}:
                    f = teile_key(k)[0]
                    if f not in felder:
                        felder.append(f)
                return {"zeit": a["zeit"], "felder": felder}
        return None

    def vorschlaege_zahl(self, sid: str) -> int:
        return len(self.vorschlaege_gueltig(sid))

    def vorschlaege_liste(self, sid: str) -> list[dict[str, Any]]:
        """``online_vorschlaege_liste`` in ``serie/get`` (nur für Administratoren): ``id``, ``art``, ``quelle``, ``felder`` (Art ``felder``), ``name``
        und ``grund`` (Quelle ``claude``), ``ziel_serie_id`` (Art ``zusammenfuehren``), ``zeit``."""
        aus = []
        for v in self.vorschlaege_gueltig(sid):
            e: dict[str, Any] = {"id": v["id"], "art": v["art"], "quelle": v["quelle"], "zeit": v["zeit"]}
            if v["art"] == "felder":
                e["felder"] = list(v.get("felder") or [])
                if v["quelle"] == "claude" and "serie_name" in (v.get("werte") or {}):
                    e["name"] = v["werte"]["serie_name"]
            if v.get("grund"):
                e["grund"] = v["grund"]
            if v.get("ziel_serie_id"):
                e["ziel_serie_id"] = v["ziel_serie_id"]
            aus.append(e)
        return aus

    def folge_online(self, sid: str, folge: str) -> dict[str, Any]:
        """Neue Felder des Folge-Objekts: ``beschreibung`` (höchstens 300 Zeichen, am Satzende gekürzt), ``beschreibung_gekuerzt``, ``alter_ab``,
        ``beschreibung_quelle``. Nur die vorhandenen Felder."""
        i = self.store.folge_info(sid, folge)
        aus: dict[str, Any] = {}
        text = i.get("beschreibung")
        if isinstance(text, str) and text:
            kurz, gekuerzt = kuerzen_am_satzende(text)
            aus.update(beschreibung=kurz, beschreibung_gekuerzt=gekuerzt, beschreibung_quelle=i.get("quelle"))
        alter = i.get("alter_ab")
        if isinstance(alter, int) and not isinstance(alter, bool):
            aus["alter_ab"] = alter
        return aus

    def beschreibung_hat(self, sid: str, folge: str) -> bool:
        return bool(self.store.folge_info(sid, folge).get("beschreibung"))

    # ----------------------------------------------------------------------
    # Herkunft (6.1)
    # ----------------------------------------------------------------------

    def von_hand_gesetzt(self, sid: str, feld: str, folge: str | None = None) -> None:
        """Ein Mensch hat einen Wert gesetzt (``serie/rename``, ``folge/rename``, ``serie/art_setzen``): Die Marke „zurückgenommen“ wird durch ``hand`` ersetzt (6.1)."""
        key = feld_key(feld, folge)
        if self.store.zurueck_hat(sid, key):
            self.store.setze_hand(sid, key)
            self.store.bald(0)

    def bestaetigt(self, sid: str, folgen: list[str] | None) -> None:
        """``einsortierung/bestaetigen``: bestätigt = von Hand; die Schnappschüsse der bestätigten Felder fallen weg (6.2)."""
        s = self.store.lies(sid)
        sn = s.get("schnapp")
        if not isinstance(sn, dict):
            return
        namen = list(sn.get("folgen") or ()) if folgen is None else [f for f in folgen if f in (sn.get("folgen") or {})]
        for f in namen:
            self.store.loesche_schnapp(sid, feld_key("folge_titel", f))
            self.store.loesche_schnapp(sid, feld_key("nummer", f))
        if folgen is None:
            self.store.loesche_schnapp(sid, "art")
        self.store.bald(0)

    @staticmethod
    def _loest_grund(serie: Serie, feld: str, folge: str | None) -> bool:
        """Hat dieses Feld einen Prüfgrund, den eine Bestätigung auflösen kann (5.5)? Nur dann zählt „sicher und schon gleich“ als Bestätigung."""
        if feld == "art":
            return "art_geraten" in serie.pruefen_gruende
        if folge is None or folge not in serie.folgen:
            return False
        i = serie.info(folge)
        if not i.get("pruefen"):
            return False
        gruende = set(i.get("pruefen_gruende") or ())
        if feld == "folge_titel":
            return "tags_fehlen" in gruende
        if feld == "nummer":
            return bool(gruende & {"tags_fehlen", "nummer_doppelt"})
        return False

    def _sperre_grund(self, sid: str, serie: Serie, info: Any, feld: str, folge: str | None) -> str:
        """Wie steht das Feld zur Automatik (6.1)? ``frei``, ``hand`` (nie anfassen, nie vorschlagen), ``vorschlag`` (nur vorschlagen)."""
        key = feld_key(feld, folge)
        if self.store.hand_hat(sid, key):
            return "hand"
        if self.store.zurueck_hat(sid, key):
            return "vorschlag"
        if feld == "serie_name":
            return "vorschlag"
        if feld == "cover":
            return "hand" if info.cover_quelle == "eigen" else "frei"
        if feld == "art":
            return "hand" if serie.art_quelle == "manuell" else ("frei" if serie.art_quelle in (None, "geraten") else "hand")
        if feld in ("beschreibung", "alter_ab"):
            return "frei"
        # folge_titel, nummer
        gibt, wert = self.store.schnapp_wert(sid, key)
        aktuell = serie.info(folge or "").get("anzeige") if feld == "folge_titel" else serie.info(folge or "").get("nummer")
        if gibt:
            return "frei" if aktuell == wert else "vorschlag"
        gruende = set(serie.info(folge or "").get("pruefen_gruende") or ()) if serie.info(folge or "").get("pruefen") else set()
        erlaubt = set(ab.GRUND_FOLGE_TITEL) if feld == "folge_titel" else set(ab.GRUND_NUMMER)
        return "frei" if gruende & erlaubt else "vorschlag"

    def ist_von_hand(self, sid: str, feld: str, folge: str | None, serie: Serie, info: Any) -> bool:
        """Für ``hand`` in Nr. 58: Das Feld ist von Hand gesetzt (Häkchen aus)."""
        if feld == "serie_name":
            return True
        return self._sperre_grund(sid, serie, info, feld, folge) != "frei"

    # ----------------------------------------------------------------------
    # 5.1 Beim Einsortieren
    # ----------------------------------------------------------------------

    def neu_einsortiert(self, sid: str, neu: bool, folgen: dict[str, dict[str, Any]], art: str | None = None) -> None:
        """Aufruf aus ``eingang._serie_abarbeiten`` (die Sperre der Serie ist belegt): Schnappschuss schreiben, in die Schlange legen, sofort zurückkehren.

        ``folgen``: je neuer Folge ``{"anzeige", "nummer"}``; ``art``: die Art einer **neuen** Serie (sonst ``None``). Für den Namen gibt es keinen Schnappschuss (4.6)."""
        for f, i in folgen.items():
            self.store.setze_schnapp(sid, feld_key("folge_titel", f), i.get("anzeige"))
            self.store.setze_schnapp(sid, feld_key("nummer", f), i.get("nummer"))
            if f not in (self.store.serie(sid).setdefault("schnapp", {}).setdefault("folgen", {})):
                self.store.serie(sid)["schnapp"]["folgen"][f] = {}
        if neu and art:
            self.store.setze_schnapp(sid, "art", art)
        self.store.bald(0)
        eintrag = self._queue.setdefault(sid, {"folgen": set(), "neu": False})
        eintrag["folgen"] |= set(folgen)
        eintrag["neu"] = eintrag["neu"] or neu
        self._starte_queue()

    def _starte_queue(self) -> None:
        if self._queue and (self._queue_task is None or self._queue_task.done()):
            self._queue_task = self.hub.hass.async_create_background_task(self._arbeite_queue(), "tobibox_online_queue")

    async def warte_auf_ende(self) -> None:
        """Für Tests: wartet, bis die Schlange leer ist."""
        while self._queue_task is not None and not self._queue_task.done():
            await asyncio.shield(self._queue_task)

    async def _arbeite_queue(self) -> None:
        while self._queue:
            sid = next(iter(self._queue))
            auftrag = self._queue.pop(sid)
            try:
                async with self._arbeit:
                    erg = await self._arbeite_serie(sid, folgen=set(auftrag["folgen"]), neu=auftrag["neu"], im_lauf=False, lauf_id=None)
                if erg.get("pause") is not None:
                    _LOGGER.info("Online-Suche beim Einsortieren: Quelle pausiert (%s)", erg["pause"].gruppe)
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("Online-Suche für %s fehlgeschlagen", sid)

    # ----------------------------------------------------------------------
    # Die Arbeit an einer Serie (5.1 Schritt 3 bis 5, auch im Lauf)
    # ----------------------------------------------------------------------

    def _eintrag_fuer_abgleich(self, info: Any) -> dict[str, Any]:
        s = info.serie
        folgen = []
        for o in info.folgen_objekte:
            folgen.append(
                {
                    "name": o["name"],
                    "anzeige": o["anzeige"],
                    "nummer": o.get("nummer"),
                    "tracks": o.get("tracks"),
                    "pruefen_gruende": list(o.get("pruefen_gruende") or []),
                    "art": o.get("art"),
                }
            )
        return {
            "name": s.name,
            "ordner": info.ordner,
            "einzeln": bool(s.einzeln),
            "cover_quelle": "eigen" if info.cover_quelle in ("eigen", "online") else (info.cover_quelle or None),
            "art_quelle": s.art_quelle if s.art else None,
            "folgen": folgen,
        }

    async def _itunes_beide(self, wort: str, von_hand: bool = False) -> list[dict[str, Any]]:
        assert self.quellen is not None
        aus: list[dict[str, Any]] = []
        for art in ("album", "hoerbuch"):
            aus += await self.quellen.itunes_suche(wort, art, von_hand=von_hand)
        return aus

    async def _apple_folge(self, ctx: dict[str, Any], s2cache: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """Zwei Stufen (3.3): erst je Folge, bei keinem Treffer einmal je Eintrag nur der Serienname. ``QuellePausiert`` geht nach oben."""
        s1, s2 = ab.apple_suchwoerter(ctx)
        ergebnis: list[dict[str, Any]] = []
        if s1:
            ergebnis += await self._itunes_beide(s1)
            if ab.apple_hat_treffer(ctx, ergebnis):
                return ab.apple_entdoppeln(ergebnis)
        if s2 not in s2cache:
            s2cache[s2] = await self._itunes_beide(s2)
        return ab.apple_entdoppeln(ergebnis + s2cache[s2])

    def _hat_grund(self, info: Any, folgen: list[str] | None = None) -> bool:
        """Claude-Schritt nur für Einträge mit Grund: ``serie_aus_interpret`` / ``serie_aus_ordner`` an einer Folge (3.4)."""
        s = info.serie
        for f in s.folgen if folgen is None else folgen:
            i = s.info(f)
            if i.get("pruefen") and set(i.get("pruefen_gruende") or ()) & set(GRUENDE_NAME):
                return True
        return False

    async def _arbeite_serie(
        self, sid: str, *, folgen: set[str] | None, neu: bool, im_lauf: bool, lauf_id: str | None, nur_claude: bool = False
    ) -> dict[str, Any]:
        """Eine Serie: Daten holen (ohne Sperre), bewerten, unter der Serien-Sperre schreiben (5.1). Wirft nur ``CancelledError``.

        Ergebnis: ``geaendert`` (Zahl der automatisch übernommenen Felder), ``vorschlaege`` (neue), ``fehler``, ``pause`` (``QuellePausiert`` oder ``None``)."""
        erg: dict[str, Any] = {"geaendert": 0, "vorschlaege": 0, "fehler": False, "pause": None, "uebersprungen": False}
        medien = self.hub.medien
        info = medien.serien.get(sid)
        if info is None or info.serie.typ != "normal":
            erg["uebersprungen"] = True
            return erg
        serie = info.serie
        namen = list(serie.folgen)
        if not namen:
            erg["uebersprungen"] = True
            return erg
        bearbeiten = [f for f in namen if folgen is None or f in folgen]
        if nur_claude:
            bearbeiten = namen[:CLAUDE_MAX_FOLGEN]
        grund_claude = self._hat_grund(info) or (neu and self._ki_gewuenscht_neu(info))
        start = self._start_werte(sid, info)
        q = await self._quellen_bereit()
        assert self.tonie_liste is not None
        liste_ok = await self.tonie_liste.sicherstellen()
        self._melde_tonies()
        index = await self._index() if liste_ok else self._leerer_index()
        eintrag = self._eintrag_fuer_abgleich(info)
        n = len(namen)
        ctxs = [ab.folge_kontext(serie.name, f, bool(serie.einzeln), n) for f in eintrag["folgen"]]
        apple: list[list[dict[str, Any]] | None] = []
        s2cache: dict[str, list[dict[str, Any]]] = {}
        try:
            for f, c in zip(namen, ctxs, strict=True):
                if f not in bearbeiten:
                    apple.append([])
                    continue
                try:
                    apple.append(await self._apple_folge(c, s2cache))
                    self._melde_quelle("itunes", True)
                except QuellePausiert as err:
                    self._melde_quelle("itunes", False, err.pause_bis)
                    raise
                except OnlineFehler:
                    apple.append(None)
                    erg["fehler"] = True
        except QuellePausiert as err:
            erg["pause"] = err
            erg["fehler"] = True
            if not im_lauf:
                self.store.setze_marke(sid, "fehler", bearbeiten, self.tonie_liste.stand)
            return erg
        try:
            sitemap: list[str] | None = await q.sitemap_pfade() if liste_ok else None
        except OnlineFehler:
            sitemap = None
        # Auflage: Beschreibung erst nach den Shopseiten bewerten. Erst bewerten, um die Seiten zu kennen, dann holen, dann endgültig bewerten.
        shop_daten: dict[str, Any] = {}
        if liste_ok and sitemap is not None and not nur_claude:
            await self._shop_holen(sid, namen, bearbeiten, ctxs, index, sitemap, shop_daten, erg)
        if erg["pause"] is not None:
            erg["fehler"] = True
            if not im_lauf:
                self.store.setze_marke(sid, "fehler", bearbeiten, self.tonie_liste.stand)
            return erg
        res = ab.bewerte_eintrag(eintrag, index, apple, shop_daten, sitemap if liste_ok else None, mit_kandidaten=grund_claude)
        if any(a is None for a in apple):
            erg["fehler"] = True
        if not nur_claude:
            await self._anwenden(sid, info, start, res, bearbeiten, shop_daten, ctxs, index, sitemap, erg, lauf_id)
        # Marke
        stand = self.tonie_liste.stand
        if not nur_claude and erg.get("cover_fehlt"):
            # Das Cover-Bild kam nicht (Pause, Fehler): keine Marke, damit der Eintrag im nächsten Lauf wieder drankommt (GO3-3)
            erg["fehler"] = True
        elif not nur_claude:
            if erg["geaendert"]:
                ergebnis = "geaendert"
            elif erg["vorschlaege"] or any(v for v in self.store.vorschlaege(sid)):
                ergebnis = "vorschlag"
            elif erg["fehler"]:
                ergebnis = "fehler"
            else:
                ergebnis = "keiner"
            self.store.setze_marke(sid, ergebnis, bearbeiten, stand)
        # Claude
        if grund_claude and not erg.get("pause"):
            await self._claude(sid, info, res, ctxs, im_lauf, erg)
        return erg

    def _ki_gewuenscht_neu(self, info: Any) -> bool:
        return True

    def _start_werte(self, sid: str, info: Any) -> dict[str, Any]:
        s = info.serie
        return {
            "infos": {f: {k: self.store.folge_info(sid, f).get(k) for k in ("beschreibung", "alter_ab")} for f in s.folgen},
            "name": s.name,
            "art": s.art,
            "art_quelle": s.art_quelle,
            "cover_stand": info.cover_stand,
            "folgen": {f: (s.info(f).get("anzeige"), s.info(f).get("nummer")) for f in s.folgen},
        }

    async def _shop_holen(
        self,
        sid: str,
        namen: list[str],
        bearbeiten: list[str],
        ctxs: list[dict[str, Any]],
        index: dict[str, Any],
        sitemap: list[str],
        shop_daten: dict[str, Any],
        erg: dict[str, Any],
    ) -> None:
        """Shopseiten der Folgen mit sicherem Tonie-Treffer. Rückgabe von ``shop_seite`` direkt als ``shop_daten[model]`` (``None`` = geholt, unbrauchbar)."""
        q = self.quellen
        assert q is not None
        for f, c in zip(namen, ctxs, strict=True):
            if f not in bearbeiten:
                continue
            tp = ab.tonie_pruefen(c, index, sitemap)
            for pfad, model in tp["shop_pfade"]:
                if pfad is None or model in shop_daten:
                    continue
                gemerkt = self.store.folge_info(sid, f)
                if gemerkt.get("tonie_model") == model and gemerkt.get("seite") == pfad and gemerkt.get("quelle") == "tonies_shop":
                    daten = {k: gemerkt[k] for k in ("beschreibung", "alter_ab") if k in gemerkt}
                    if daten:
                        shop_daten[model] = daten
                        continue
                try:
                    shop_daten[model] = await q.shop_seite(pfad, model)
                    self._melde_quelle("tonies_shop", True)
                except FormatFehler:
                    shop_daten[model] = None  # Felder fehlen: geholt, aber unbrauchbar
                except QuellePausiert as err:
                    self._melde_quelle("tonies_shop", False, err.pause_bis)
                    erg["pause"] = err
                    return
                except OnlineFehler:
                    erg["fehler"] = True  # nicht geholt: die Beschreibung ist nicht endgültig

    # ---- Entscheiden und schreiben ----

    def _quelle_von(self, quelle: dict[str, Any] | None) -> str:
        typ = str((quelle or {}).get("typ") or "")
        if typ.startswith("tonies") and "apple" not in typ:
            return "tonies"
        return "itunes"

    async def _anwenden(
        self,
        sid: str,
        info: Any,
        start: dict[str, Any],
        res: dict[str, Any],
        bearbeiten: list[str],
        shop_daten: dict[str, Any],
        ctxs: list[dict[str, Any]],
        index: dict[str, Any],
        sitemap: list[str] | None,
        erg: dict[str, Any],
        lauf_id: str | None,
    ) -> None:
        serie = info.serie
        namen = list(serie.folgen)
        auto: dict[str, dict[str, Any]] = {}
        bestaetigt: list[str] = []
        vorschlaege: list[dict[str, Any]] = []

        def verteile(feld: str, folge: str | None, fe: dict[str, Any], aktuell: Any, *, nur_sicher: bool, nur_vorschlag: bool = False, neu_wert: Any = None, extra: dict | None = None) -> None:
            if fe["status"] not in ("sicher", "unsicher"):
                return
            neu = fe["neu"] if neu_wert is None else neu_wert
            if neu is None:
                return
            key = feld_key(feld, folge)
            grund = self._sperre_grund(sid, serie, info, feld, folge)
            if neu == aktuell:
                # Bestätigt nur, wenn es etwas aufzulösen gibt und das Feld der Automatik gehört (``frei``): sonst weder Änderung noch Schnappschuss (GO3-1)
                if fe["status"] == "sicher" and grund == "frei" and self._loest_grund(serie, feld, folge):
                    bestaetigt.append(key)
                return
            if grund == "hand":
                return
            quelle = self._quelle_von(fe.get("quelle"))
            k = {"key": key, "feld": feld, "folge": folge, "neu": neu, "quelle": quelle, "extra": extra or {}, "q": fe.get("quelle") or {}}
            if fe["status"] == "sicher" and grund == "frei" and not nur_vorschlag:
                auto[key] = k
            elif not nur_sicher:
                vorschlaege.append(k)
            elif grund == "vorschlag":
                vorschlaege.append(k)

        c = res["cover"]
        if not c.get("geschuetzt") and c["status"] in ("sicher", "unsicher") and c.get("neu"):
            url = bild_url_600(c["neu"])
            if url:
                verteile("cover", None, c, None, nur_sicher=False, neu_wert=url, extra={"collection_id": c.get("collection_id"), "cover_url": url})
        a = res["art"]
        if not a.get("geschuetzt") and a["status"] in ("sicher", "unsicher") and a.get("neu"):
            verteile("art", None, a, serie.art if serie.art_quelle in (None, "geraten") else object(), nur_sicher=False)
        for f, fres in zip(namen, res["folgen"], strict=True):
            if f not in bearbeiten:
                continue
            i = serie.info(f)
            ft = fres["folge_titel"]
            verteile("folge_titel", f, ft, i.get("anzeige") or serie.anzeige(f), nur_sicher=False, nur_vorschlag=(ft.get("aenderung") != "woerter"))
            verteile("nummer", f, fres["nummer"], i.get("nummer"), nur_sicher=False)
            fi = self.store.folge_info(sid, f)
            for feld in ("beschreibung", "alter_ab"):
                fe = fres[feld]
                if fe["status"] != "sicher":
                    continue
                neu_wert = beschreibung_text(fe["neu"]) if feld == "beschreibung" else fe["neu"]
                if neu_wert is None:
                    continue
                verteile(feld, f, fe, fi.get(feld), nur_sicher=True, neu_wert=neu_wert, extra={"model": (fe.get("quelle") or {}).get("model"), "seite": self._seite_zu(fres, shop_daten, fe)})
        # Titel vor dem Schreiben bereinigen
        for k in list(auto.values()) + vorschlaege:
            if k["feld"] == "folge_titel":
                k["neu"] = online_text(k["neu"], FOLGE_ANZEIGE_MAX)
        auto = {k: v for k, v in auto.items() if v["neu"] is not None}
        vorschlaege = [v for v in vorschlaege if v["neu"] is not None]
        # Cover-Bild holen (Netz, ohne Sperre)
        cover_bytes: bytes | None = None
        if "cover" in auto:
            cover_bytes = await self._cover_bytes(auto["cover"]["neu"], erg)
            if cover_bytes is None:
                auto.pop("cover")
                erg["cover_fehlt"] = True
        # Schreiben unter der Sperre
        if auto or bestaetigt:
            ok, zu_vorschlag = await self._schreibe_auto(sid, start, auto, bestaetigt, cover_bytes, lauf_id, erg)
            vorschlaege += zu_vorschlag
        erg["vorschlaege"] += self._vorschlaege_anlegen(sid, vorschlaege)

    def _seite_zu(self, fres: dict[str, Any], shop_daten: dict[str, Any], fe: dict[str, Any]) -> str | None:
        model = (fe.get("quelle") or {}).get("model")
        for p in fres.get("shop_pfade") or ():
            return p if model else None
        return None

    async def _cover_bytes(self, url: str, erg: dict[str, Any], von_hand: bool = False) -> bytes | None:
        q = self.quellen
        assert q is not None
        try:
            roh = await q.bild_holen(url, von_hand=von_hand)
            self._melde_quelle("itunes", True)
            gross, _klein = await q.im_executor(lambda: cover_pruefen_und_skalieren(roh, modus="nachsichtig", erlaubt=("jpeg", "png")))
            return gross
        except QuellePausiert as err:
            self._melde_quelle("itunes", False, err.pause_bis)
            erg["pause"] = err
        except (OnlineFehler, TobiboxFehler):
            erg["fehler"] = True
        return None

    async def _schreibe_auto(
        self,
        sid: str,
        start: dict[str, Any],
        auto: dict[str, dict[str, Any]],
        bestaetigt: list[str],
        cover_bytes: bytes | None,
        lauf_id: str | None,
        erg: dict[str, Any],
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Schritte 4 und 5 von 5.1 unter der Serien-Sperre: frisch lesen, prüfen, dass die Felder noch den gemerkten Werten entsprechen
        (sonst Vorschlag), dann übernehmen (6.3)."""
        medien = self.hub.medien
        zu_vorschlag: list[dict[str, Any]] = []
        try:
            async with medien.sperren(sid):
                try:
                    serie, pfad = await medien._frisch(sid)
                except TobiboxFehler:
                    return False, []  # verschwunden: still verwerfen (GB-19)
                cover_jetzt, cover_quelle = (await medien._executor(cover_zustand, pfad))[:2]
                frisch = SimpleNamespace(cover_quelle=cover_quelle)
                werte: dict[str, Any] = {}
                for key, k in auto.items():
                    feld, folge = k["feld"], k["folge"]
                    if folge is not None and folge not in serie.folgen:
                        continue  # die Folge ist weg
                    # Alles noch einmal frisch bewerten: ``hand``, ``zurueckgenommen`` und die Herkunft können sich seit dem Start geändert haben (GO3-5)
                    grund = self._sperre_grund(sid, serie, frisch, feld, folge)
                    if grund == "hand":
                        continue  # ein Mensch war schneller: nie anfassen, nie vorschlagen (6.1)
                    if grund == "vorschlag":
                        zu_vorschlag.append(k)
                        continue
                    if feld == "cover":
                        if cover_jetzt != start["cover_stand"] or cover_bytes is None:
                            zu_vorschlag.append(k)
                            continue
                    elif feld == "art":
                        if (serie.art, serie.art_quelle) != (start["art"], start["art_quelle"]):
                            zu_vorschlag.append(k)
                            continue
                    elif feld in ("folge_titel", "nummer"):
                        alt = start["folgen"].get(folge)
                        jetzt_ = (serie.info(folge).get("anzeige"), serie.info(folge).get("nummer"))
                        if alt is not None and jetzt_ != alt:
                            zu_vorschlag.append(k)
                            continue
                    else:  # beschreibung, alter_ab: der Wert im Store muss noch der vom Start sein
                        gemerkt = (start.get("infos") or {}).get(folge) or {}
                        if self.store.folge_info(sid, folge).get(feld) != gemerkt.get(feld):
                            zu_vorschlag.append(k)
                            continue
                    werte[key] = k
                bestaetigt = [b for b in bestaetigt if self._bestaetigung_noch_gueltig(sid, serie, frisch, start, b)]
                if not werte and not bestaetigt:
                    return False, zu_vorschlag
                quelle = next((k["quelle"] for k in werte.values()), "itunes")
                aid = await self._schreibe(sid, serie, pfad, werte, bestaetigt, wer="auto", quelle=quelle, lauf_id=lauf_id, automatisch=True, cover_bytes=cover_bytes)
                if aid is not None:
                    erg["geaendert"] += len(werte)
        except TobiboxFehler as err:
            _LOGGER.warning("Online-Übernahme für %s nicht möglich: %s", sid, err.code)
            erg["fehler"] = True
        return True, zu_vorschlag

    def _bestaetigung_noch_gueltig(self, sid: str, serie: Serie, frisch: Any, start: dict[str, Any], key: str) -> bool:
        """Unter der Sperre: Gehört das bestätigte Feld der Automatik noch, trägt es noch den Wert vom Start, und gibt es den Prüfgrund noch (GO3-5)?"""
        feld, folge = teile_key(key)
        if folge is not None and folge not in serie.folgen:
            return False
        if self._sperre_grund(sid, serie, frisch, feld, folge) != "frei" or not self._loest_grund(serie, feld, folge):
            return False
        if feld == "art":
            return (serie.art, serie.art_quelle) == (start["art"], start["art_quelle"])
        alt = start["folgen"].get(folge)
        return alt is None or (serie.info(folge).get("anzeige"), serie.info(folge).get("nummer")) == alt

    # ---- Übernahme (6.3) ----

    def _gruende_loesen(
        self, serie: Serie, art: bool, titel: set[str], nummern: set[str], *, ganz: set[str] | None = None
    ) -> set[str]:
        """Prüfgründe nach 5.5 auflösen. ``ganz``: Folgen, deren ``pruefen`` ganz fällt (Übernahme von Hand wie ein Umbenennen). Gibt die Folgen zurück, deren ``pruefen`` geändert wurde."""
        geaendert: set[str] = set()
        hat_nummern = any(isinstance(serie.info(f).get("nummer"), int) for f in serie.folgen)
        for f in titel | nummern | (ganz or set()):
            if f not in serie.folgen:
                continue
            i = serie.info(f)
            if not i.get("pruefen"):
                continue
            if ganz and f in ganz:
                serie.loesche_pruefen(f)
                geaendert.add(f)
                continue
            gr = list(i.get("pruefen_gruende") or [])
            nr_ok = (not hat_nummern) or f in nummern or isinstance(i.get("nummer"), int)
            neu = [g for g in gr if not ((g == "tags_fehlen" and f in titel and nr_ok) or (g == "nummer_doppelt" and f in nummern))]
            if neu != gr:
                geaendert.add(f)
                if neu:
                    serie.setze_info(f, pruefen_gruende=neu)
                else:
                    serie.loesche_pruefen(f)
        if art and "art_geraten" in serie.pruefen_gruende:
            serie.pruefen_gruende = [g for g in serie.pruefen_gruende if g != "art_geraten"]
            if not serie.pruefen_gruende:
                serie.pruefen = False
        if serie.pruefen and not serie.pruefen_gruende and not any(serie.info(f).get("pruefen") for f in serie.folgen):
            serie.pruefen = False
        return geaendert

    async def _schreibe(
        self,
        sid: str,
        serie: Serie,
        pfad: Path,
        werte: dict[str, dict[str, Any]],
        bestaetigt: list[str],
        *,
        wer: str,
        quelle: str,
        lauf_id: str | None,
        automatisch: bool,
        cover_bytes: bytes | None = None,
    ) -> str | None:
        """Die Übernahme in der Reihenfolge von 6.3: Änderung ``offen`` sofort speichern, schreiben, ``fertig``. Der Aufrufer hält die Sperre der Serie
        und hat ``serie`` frisch gelesen. Gibt die ``aenderung_id`` zurück (``None``, wenn es nichts zu schreiben gab)."""
        medien = self.hub.medien
        store = self.store
        stand_vorher = serie.stand
        felder: dict[str, dict[str, Any]] = {}
        pruef_vorher: dict[str, Any] = {"serie": {"pruefen": serie.pruefen, "pruefen_gruende": list(serie.pruefen_gruende)}, "folgen": {}}
        for f in serie.folgen:
            i = serie.info(f)
            if i.get("pruefen"):
                pruef_vorher["folgen"][f] = {"pruefen": True, "pruefen_gruende": list(i.get("pruefen_gruende") or [])}
        # Vorher- und Nachher-Werte (Zeichenketten sind schon durch ``online_text``)
        for key, k in werte.items():
            feld, folge = k["feld"], k["folge"]
            neu = k["neu"]
            if feld == "serie_name":
                neu = name_pruefen(online_text(neu, SERIE_NAME_MAX), SERIE_NAME_MAX)
                felder[key] = {"vorher": serie.name, "nachher": neu}
            elif feld == "art":
                felder[key] = {"vorher": {"art": serie.art, "art_quelle": serie.art_quelle}, "nachher": {"art": neu, "art_quelle": "online"}}
            elif feld == "cover":
                felder[key] = {"vorher": {"quelle": (await medien._executor(cover_zustand, pfad))[1]}, "nachher": {"quelle": "online"}}
            elif feld == "folge_titel":
                neu = online_text(neu, FOLGE_ANZEIGE_MAX)
                if neu is None:
                    continue
                felder[key] = {"vorher": serie.info(folge).get("anzeige"), "nachher": neu}
            elif feld == "nummer":
                felder[key] = {"vorher": serie.info(folge).get("nummer"), "nachher": neu}
            elif feld == "beschreibung":
                neu = beschreibung_text(neu)
                if neu is None:
                    continue
                felder[key] = {"vorher": store.folge_info(sid, folge).get("beschreibung"), "nachher": neu}
            else:  # alter_ab
                felder[key] = {"vorher": store.folge_info(sid, folge).get("alter_ab"), "nachher": neu}
            k["neu"] = neu
        if not felder and bestaetigt and not self._bestaetigung_loest(serie, bestaetigt):
            return None  # nichts zu schreiben und nichts aufzulösen: keine (leere) Änderung (GO3-1)
        if not felder and not bestaetigt:
            return None
        aid = neue_id12()
        aenderung: dict[str, Any] = {
            "id": aid,
            "zeit": jetzt_iso(),
            "wer": wer,
            "quelle": quelle,
            "status": "offen",
            "felder": felder,
            "pruefen_vorher": pruef_vorher,
            "schnapp_vorher": copy.deepcopy(store.lies(sid).get("schnapp") or {}),
        }
        if lauf_id:
            aenderung["lauf_id"] = lauf_id
        if bestaetigt:
            aenderung["bestaetigt"] = list(bestaetigt)
        # 1. offen, sofort gespeichert
        store.serie(sid).setdefault("aenderungen", []).append(aenderung)
        store.verfall_aenderungen(sid)
        await store.sofort()
        # 2. schreiben
        titel: set[str] = set()
        nummern: set[str] = set()
        ganz: set[str] = set()
        art_gesetzt = False
        for key, k in werte.items():
            if key not in felder:
                continue
            feld, folge = k["feld"], k["folge"]
            if feld == "serie_name":
                serie.name = felder[key]["nachher"]
                serie.pruefen, serie.pruefen_gruende = False, []  # wie ein Umbenennen von Hand
            elif feld == "art":
                serie.art, serie.art_quelle = k["neu"], "online"
                art_gesetzt = True
            elif feld == "folge_titel":
                serie.setze_info(folge, anzeige=k["neu"])
                titel.add(folge)
                if not automatisch:
                    ganz.add(folge)
            elif feld == "nummer":
                serie.setze_info(folge, nummer=k["neu"])
                nummern.add(folge)
        for key in bestaetigt:
            feld, folge = teile_key(key)
            if feld == "art":
                art_gesetzt = True
            elif feld == "folge_titel" and folge:
                titel.add(folge)
            elif feld == "nummer" and folge:
                nummern.add(folge)
        geloest = self._gruende_loesen(serie, art_gesetzt, titel, nummern, ganz=ganz)
        cover_geschrieben = False
        try:
            # Das Cover zuerst: scheitert es, ist noch nichts anderes geschrieben (GO3-7)
            if "cover" in werte and cover_bytes is not None:
                await medien._executor(schreibe_bytes_atomar, pfad / COVER_ONLINE, cover_bytes)
                cover_geschrieben = True
                aenderung["cover_stand"] = await medien._executor(online_stand, pfad)
            if any(k["feld"] in ("serie_name", "art", "folge_titel", "nummer") for k in werte.values()) or geloest or art_gesetzt:
                await medien._executor(schreibe_serie, pfad, serie)
        except OSError as err:
            # Die Änderung bleibt nicht ``offen`` stehen: entfernen, die Schnappschüsse **dieser** Felder zurück (GO3-7)
            await self._aenderung_verwerfen(sid, aenderung, pfad, felder, cover_geschrieben)
            raise medien._fehler_schreiben(err) from err
        for key, k in werte.items():
            if key in felder and k["feld"] in ("beschreibung", "alter_ab"):
                neu = k["neu"]
                extra = k.get("extra") or {}
                if k["feld"] == "beschreibung":
                    store.setze_folge_info(sid, k["folge"], beschreibung=neu, quelle=("tonies_shop" if k["quelle"] == "tonies" else "itunes"),
                                           tonie_model=extra.get("model") if k["quelle"] == "tonies" else None, seite=extra.get("seite") if k["quelle"] == "tonies" else None)
                else:
                    store.setze_folge_info(sid, k["folge"], alter_ab=neu)
        # 3. Schnappschüsse, hand, Rückweg, fertig
        if automatisch:
            for key, k in werte.items():
                if key not in felder:
                    continue
                if k["feld"] in ("folge_titel", "nummer", "art"):
                    store.setze_schnapp(sid, key, k["neu"])
            for key in bestaetigt:
                feld, folge = teile_key(key)
                if feld == "folge_titel" and folge:
                    store.setze_schnapp(sid, key, serie.info(folge).get("anzeige"))
                elif feld == "nummer" and folge:
                    store.setze_schnapp(sid, key, serie.info(folge).get("nummer"))
                elif feld == "art":
                    store.setze_schnapp(sid, key, serie.art)
        else:
            for key in felder:
                store.setze_hand(sid, key)
                if teile_key(key)[0] in ("folge_titel", "nummer", "art"):
                    store.loesche_schnapp(sid, key)  # kein Schnappschuss nach einer Übernahme von Hand (5.2)
        aenderung["status"] = "fertig"
        aenderung.pop("schnapp_vorher", None)
        info = await medien._aktualisiere_cache(serie, pfad.name)
        if automatisch:
            try:
                rueckweg_fortschreiben(self.hub.eingang, stand_vorher, serie, [teile_key(k)[1] for k in felder if teile_key(k)[1]])
            except Exception:
                _LOGGER.exception("Rückweg nach der Online-Übernahme nicht fortgeschrieben")
        await store.sofort()
        ganz_geloest = sorted(f for f in geloest if not serie.info(f).get("pruefen"))
        if ganz_geloest:
            self.hub.eingang.pruefen_zuruecksetzen(sid, ganz_geloest)
        self._serien_geaendert(sid)
        del info
        return aid

    def _bestaetigung_loest(self, serie: Serie, bestaetigt: list[str]) -> bool:
        """Probelauf auf einer Kopie: Löst die Bestätigung wirklich einen Prüfgrund auf (5.5)? Sonst gibt es nichts zu schreiben (GO3-1)."""
        probe = copy.deepcopy(serie)
        titel: set[str] = set()
        nummern: set[str] = set()
        art = False
        for key in bestaetigt:
            feld, folge = teile_key(key)
            if feld == "art":
                art = True
            elif feld == "folge_titel" and folge:
                titel.add(folge)
            elif feld == "nummer" and folge:
                nummern.add(folge)
        vorher = (probe.pruefen, list(probe.pruefen_gruende), {f: (probe.info(f).get("pruefen"), list(probe.info(f).get("pruefen_gruende") or [])) for f in probe.folgen})
        self._gruende_loesen(probe, art, titel, nummern)
        nachher = (probe.pruefen, list(probe.pruefen_gruende), {f: (probe.info(f).get("pruefen"), list(probe.info(f).get("pruefen_gruende") or [])) for f in probe.folgen})
        return vorher != nachher

    async def _aenderung_verwerfen(self, sid: str, aenderung: dict[str, Any], pfad: Path, felder: dict[str, Any], cover_geschrieben: bool) -> None:
        """Schreiben gescheitert (6.3, GO3-7): die ``offene`` Änderung entfernen, nur die Schnappschüsse ihrer Felder zurückstellen, ein neu
        geschriebenes Cover (das es vorher nicht als Online-Cover gab) wieder löschen. Fehler dabei werden nur protokolliert."""
        store = self.store
        liste = store.lies(sid).get("aenderungen")
        if isinstance(liste, list):
            liste[:] = [a for a in liste if a is not aenderung]
        for key in felder:
            store.schnapp_zurueck(sid, key, aenderung.get("schnapp_vorher") or {})
        store._aufraeumen(sid)  # noqa: SLF001
        if cover_geschrieben and (felder.get("cover") or {}).get("vorher", {}).get("quelle") != "online":
            with contextlib.suppress(Exception):
                await self.hub.medien._executor(loesche_datei, pfad / COVER_ONLINE)
        with contextlib.suppress(Exception):
            await store.sofort()

    # ---- Vorschläge ----

    def _vorschlaege_anlegen(self, sid: str, kandidaten: list[dict[str, Any]]) -> int:
        """Unsichere Felder werden Vorschläge, je Quelle einer (5.4). Verworfenes kommt nicht wieder. Gibt die Zahl **neuer** Vorschläge zurück."""
        if not kandidaten:
            return 0
        neu_gezaehlt = 0
        je_quelle: dict[str, list[dict[str, Any]]] = {}
        for k in kandidaten:
            kennung = (k.get("extra") or {}).get("collection_id") if k["feld"] == "cover" else None
            if self.store.verworfen_hat(sid, k["feld"] if k["folge"] is None else k["key"], wert_hash(k["key"], k["neu"], k["quelle"], kennung), k["quelle"]):
                continue
            je_quelle.setdefault(k["quelle"], []).append(k)
        for quelle, liste in je_quelle.items():
            # ein Cover-Vorschlag je Eintrag
            gesehen_cover = False
            werte: dict[str, Any] = {}
            for k in liste:
                if k["feld"] == "cover":
                    if gesehen_cover:
                        continue
                    gesehen_cover = True
                    werte[k["key"]] = {"cover_url": k["neu"], "collection_id": (k.get("extra") or {}).get("collection_id")}
                else:
                    werte[k["key"]] = k["neu"]
            if not werte:
                continue
            vorhanden = self.store.vorschlaege(sid)
            gleich = next((v for v in vorhanden if v.get("art") == "felder" and v.get("quelle") == quelle and v.get("werte") == werte), None)
            if gleich is not None:
                continue
            rest = [v for v in vorhanden if not (v.get("art") == "felder" and v.get("quelle") == quelle and set(v.get("felder") or ()) <= set(werte))]
            rest.append({"id": neue_id12(), "art": "felder", "quelle": quelle, "felder": list(werte), "werte": werte, "zeit": jetzt_iso()})
            self.store.serie(sid)["vorschlaege"] = rest[-VORSCHLAG_MAX:]
            neu_gezaehlt += 1
        if neu_gezaehlt:
            self.store.bald(0)
            self._serien_geaendert(sid)
        return neu_gezaehlt

    def vorschlaege_gueltig(self, sid: str) -> list[dict[str, Any]]:
        """Beim Lesen auf Gültigkeit geprüft (Ziel und Folge noch da, bei ``serie_name`` der Name noch gleich ``name_vorher``), sonst verworfen (GO-1, GO-3)."""
        medien = self.hub.medien
        info = medien.serien.get(sid)
        liste = self.store.vorschlaege(sid)
        if info is None or not liste:
            return list(liste) if info is None else []
        gut: list[dict[str, Any]] = []
        for v in liste:
            if v.get("art") == "zusammenfuehren":
                ziel = medien.serien.get(v.get("ziel_serie_id") or "")
                if ziel is None or ziel.serie.typ != "normal" or ziel.serie.einzeln or v.get("ziel_serie_id") == sid:
                    continue
            else:
                felder = [k for k in v.get("felder") or [] if teile_key(k)[1] is None or teile_key(k)[1] in info.serie.folgen]
                if not felder:
                    continue
                if "serie_name" in felder and v.get("name_vorher") != info.serie.name:
                    continue
                if felder != list(v.get("felder") or []):
                    v["felder"] = felder
                    v["werte"] = {k: w for k, w in (v.get("werte") or {}).items() if k in felder}
            gut.append(v)
        if len(gut) != len(liste):
            self.store.serie(sid)["vorschlaege"] = gut
            self.store._aufraeumen(sid)  # noqa: SLF001
            self.store.bald(0)
        return gut

    async def vorschlag_verwerfen(self, serie_id: str, vorschlag_id: str) -> dict[str, Any]:
        """Nr. 61: „Nein“ verwirft dauerhaft (``verworfen``); ein zweites Mal ist ``vorschlag_nicht_gefunden``."""
        self.hub.medien.finde(serie_id)
        v = next((v for v in self.vorschlaege_gueltig(serie_id) if v["id"] == vorschlag_id), None)
        if v is None:
            raise TobiboxFehler("vorschlag_nicht_gefunden")
        if v["art"] == "felder":
            for key, w in (v.get("werte") or {}).items():
                kennung = w.get("collection_id") if isinstance(w, dict) else None
                wert = w.get("cover_url") if isinstance(w, dict) else w
                self.store.verwirf(serie_id, key if teile_key(key)[1] is not None else key, wert_hash(key, wert, v["quelle"], kennung), v["quelle"])
        else:
            self.store.verwirf(serie_id, "zusammenfuehren", wert_hash("zusammenfuehren", v.get("ziel_serie_id"), v["quelle"]), v["quelle"])
        self.store.serie(serie_id)["vorschlaege"] = [x for x in self.store.vorschlaege(serie_id) if x["id"] != vorschlag_id]
        self.store._aufraeumen(serie_id)  # noqa: SLF001
        await self.store.sofort()
        self._serien_geaendert(serie_id)
        return {}

    # ---- Claude (3.4) ----

    async def _claude(self, sid: str, info: Any, res: dict[str, Any], ctxs: list[dict[str, Any]], im_lauf: bool, erg: dict[str, Any]) -> None:
        entitaet = self.ki_entitaet()
        if not entitaet:
            self.store.setze_claude_marke(sid, "aus")
            return
        if self.store.claude_gueltig(sid, True):
            return
        serie = info.serie
        folgen = []
        for o, fres in zip(info.folgen_objekte, res["folgen"], strict=True):
            kand = fres.get("kandidaten") or {"tonies": [], "apple": []}
            folgen.append(
                {
                    "anzeige": o["anzeige"],
                    "nummer": o.get("nummer"),
                    "tracks": o.get("tracks"),
                    "pruefen_gruende": list(o.get("pruefen_gruende") or []),
                    "tonies": kand.get("tonies") or [],
                    "apple": kand.get("apple") or [],
                }
            )
        eingabe = baue_eingabe(serie.name, info.ordner, folgen, einzeltitel=bool(serie.einzeln))
        erg_ki = await self.ki.frage(self.hub.hass, entitaet, eingabe, im_lauf=im_lauf)
        if erg_ki.art == ART_UEBERSPRUNGEN:
            return  # Drossel: keine Marke
        if erg_ki.art == ART_AUS:
            self.store.setze_claude_marke(sid, "aus")
        elif erg_ki.art == ART_FEHLER:
            self.store.setze_claude_marke(sid, "fehler")
        elif erg_ki.art in (ART_BEHALTEN, ART_VERWORFEN):
            self.store.setze_claude_marke(sid, "behalten")
        elif erg_ki.art == ART_VORSCHLAG and erg_ki.name:
            self.store.setze_claude_marke(sid, "vorschlag")
            if self._claude_vorschlag(sid, info, erg_ki.name, erg_ki.grund or ""):
                erg["vorschlaege"] += 1

    def _claude_vorschlag(self, sid: str, info: Any, name: str, grund: str) -> bool:
        """Ergebnis ist immer ein Vorschlag mit Grund; gibt es den Namen schon als anderen Eintrag, wird es ein Vorschlag zum Zusammenführen."""
        if self.store.verworfen_hat(sid, "serie_name", wert_hash("serie_name", name, "claude"), "claude"):
            return False
        schluessel = vergleichsschluessel(name)
        ziel_id = None
        for andere_id, a in self.hub.medien.serien.items():
            if andere_id != sid and a.serie.typ == "normal" and vergleichsschluessel(a.serie.name) == schluessel:
                if not a.serie.einzeln:
                    ziel_id = andere_id
                    break
                return False  # Einzeltitel nie als Ziel
        vorhanden = self.store.vorschlaege(sid)
        if ziel_id is not None:
            if self.store.verworfen_hat(sid, "zusammenfuehren", wert_hash("zusammenfuehren", ziel_id, "claude"), "claude"):
                return False  # „Nein“ zum Zusammenführen kommt nicht wieder (GO3-10)
            if any(v.get("art") == "zusammenfuehren" and v.get("ziel_serie_id") == ziel_id for v in vorhanden):
                return False
            neu = {"id": neue_id12(), "art": "zusammenfuehren", "quelle": "claude", "ziel_serie_id": ziel_id, "grund": grund, "zeit": jetzt_iso()}
        else:
            if any(v.get("quelle") == "claude" and (v.get("werte") or {}).get("serie_name") == name for v in vorhanden):
                return False
            neu = {"id": neue_id12(), "art": "felder", "quelle": "claude", "felder": ["serie_name"], "werte": {"serie_name": name}, "grund": grund, "name_vorher": info.serie.name, "zeit": jetzt_iso()}
        self.store.serie(sid)["vorschlaege"] = [v for v in vorhanden if not (v.get("quelle") == "claude" and v.get("art") == neu["art"])] + [neu]
        self.store.bald(0)
        self._serien_geaendert(sid)
        return True

    # ----------------------------------------------------------------------
    # 5.3 Lauf über den Rest
    # ----------------------------------------------------------------------

    def _lauf_store(self, lauf: dict[str, Any]) -> dict[str, Any]:
        aus = {k: lauf[k] for k in ("lauf_id", "beginn", "zustand") if k in lauf}
        aus["ende"] = lauf.get("ende")
        aus["zahlen"] = dict(lauf["zahlen"])
        if lauf.get("grund"):
            aus["grund"] = lauf["grund"]
        return aus

    def _lauf_ausgabe(self, lauf: dict[str, Any]) -> dict[str, Any]:
        z = lauf["zahlen"]
        aus: dict[str, Any] = {"lauf_id": lauf["lauf_id"], "zustand": lauf["zustand"]}
        aus.update({k: z[k] for k in ("erledigt", "gesamt", "geaendert", "vorschlaege", "keiner")})
        if lauf.get("pause_bis") is not None and lauf["zustand"] == "pausiert":
            aus["pause_bis"] = _zeit_iso(lauf["pause_bis"])
        return aus

    def lauf_kandidaten(self) -> list[str]:
        """5.3: (a) keine gültige Marke (oder Folgen, die in der Marke noch nicht stehen) **und** (b) ein Merkmal, das Arbeit verspricht; dazu der Claude-Schritt (GO-2)."""
        medien = self.hub.medien
        stand = self.tonie_liste.stand if self.tonie_liste is not None else None
        option = self.ki_entitaet() is not None
        ids: list[str] = []
        for sid, info in medien.serien.items():
            s = info.serie
            if s.typ != "normal" or not s.folgen:
                continue
            claude_noetig = option and self._hat_grund(info) and not self.store.claude_gueltig(sid, option)
            if self.store.marke_gueltig(sid, list(s.folgen), stand):
                if claude_noetig:
                    ids.append(sid)
                continue
            hat_nummern = any(isinstance(s.info(f).get("nummer"), int) for f in s.folgen)
            merkmal = (
                s.pruefen
                or any(s.info(f).get("pruefen") for f in s.folgen)
                or (s.art_quelle in (None, "geraten"))
                or info.cover_quelle in (None, "auto")
                or (hat_nummern and any(not isinstance(s.info(f).get("nummer"), int) for f in s.folgen))
                or any(not self.beschreibung_hat(sid, f) for f in s.folgen)
            )
            if merkmal or claude_noetig:
                ids.append(sid)
        return ids

    def lauf_zustand(self) -> dict[str, Any] | None:
        return self._lauf_ausgabe(self._lauf) if self._lauf is not None and self._lauf["zustand"] in LAUF_LAUFEND else None

    async def lauf_starten(self) -> dict[str, Any]:
        """Nr. 62 ``start``: bestimmt die Kandidaten und startet im Hintergrund. ``lauf_laeuft_schon``, wenn einer läuft."""
        if self._startet or (self._lauf is not None and self._lauf["zustand"] in LAUF_LAUFEND):
            raise TobiboxFehler("lauf_laeuft_schon")
        self._startet = True  # vor dem ersten ``await``: ein zweites ``start`` kommt nicht mehr durch (GO3-9)
        try:
            return await self._lauf_anlegen()
        finally:
            self._startet = False

    async def _lauf_anlegen(self) -> dict[str, Any]:
        await self.hub.medien._stelle_geprueft_sicher()
        await self._quellen_bereit()
        # Die Gültigkeit der Marken hängt am Stand der Tonie-Liste: erst laden (Datei, nötigenfalls Netz), sonst gelten nach einem Neustart alle
        # Marken ``keiner``/``fehler`` als ungültig (GO3-2)
        assert self.tonie_liste is not None
        with contextlib.suppress(Exception):
            await self.tonie_liste.sicherstellen()
            self._melde_tonies()
        ids = self.lauf_kandidaten()
        lauf = {
            "lauf_id": neue_id12(),
            "beginn": jetzt_iso(),
            "ende": None,
            "zustand": "laeuft",
            "zahlen": {"erledigt": 0, "gesamt": len(ids), "geaendert": 0, "vorschlaege": 0, "keiner": 0},
            "pause_bis": None,
        }
        self._lauf = lauf
        self._stop = False
        self._stop_ereignis.clear()
        self.store.lauf_speichern(self._lauf_store(lauf))
        await self.store.sofort()
        self._lauf_task = self.hub.hass.async_create_background_task(self._lauf_laufen(lauf, ids), "tobibox_online_lauf")
        self._emit("stand", self._stand_daten(lauf))
        return {"lauf": self._lauf_ausgabe(lauf)}

    async def lauf_stoppen(self) -> dict[str, Any]:
        """Nr. 62 ``stop``: hält nach der aktuellen Serie an. Ohne Lauf kein Fehler (``lauf`` ist ``None``)."""
        lauf = self._lauf
        if lauf is None or lauf["zustand"] not in LAUF_LAUFEND:
            return {"lauf": None}
        self._stop = True
        self._stop_ereignis.set()
        lauf["zustand"] = "wird_angehalten"
        self._emit_stand("lauf", lambda: self._stand_daten(lauf))
        return {"lauf": self._lauf_ausgabe(lauf)}

    def _stand_daten(self, lauf: dict[str, Any]) -> dict[str, Any]:
        return {"vorgang": "lauf", **self._lauf_ausgabe(lauf)}

    async def warte_auf_lauf(self) -> None:
        """Für Tests."""
        while self._lauf_task is not None and not self._lauf_task.done():
            await asyncio.shield(self._lauf_task)

    async def _lauf_beenden(self, lauf: dict[str, Any], zustand: str, grund: str | None) -> None:
        lauf.update(zustand=zustand, ende=jetzt_iso())
        if grund:
            lauf["grund"] = grund
        self.store.lauf_speichern(self._lauf_store(lauf))
        await self.store.sofort()
        daten = {"vorgang": "lauf", "lauf_id": lauf["lauf_id"], "zustand": zustand, **{k: lauf["zahlen"][k] for k in ("erledigt", "gesamt", "geaendert", "vorschlaege", "keiner")}}
        if grund:
            daten["grund"] = grund
        self._emit("fertig", daten)

    async def _warte_pause(self, sekunden: float) -> None:
        """Schläft ``sekunden``, endet aber sofort, wenn ``stop`` kommt (GO3-12)."""
        schlaf = asyncio.ensure_future(self._schlafen(sekunden))
        halt = asyncio.ensure_future(self._stop_ereignis.wait())
        try:
            await asyncio.wait({schlaf, halt}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for t in (schlaf, halt):
                if not t.done():
                    t.cancel()
            for t in (schlaf, halt):
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await t

    async def _serie_im_lauf(self, sid: str, lauf: dict[str, Any]) -> dict[str, Any]:
        """Eine Serie des Laufs. Eine Ausnahme in dieser Serie überspringt nur sie: Marke ``fehler``, Protokoll, der Lauf geht weiter (GO3-4)."""
        async with self._arbeit:
            info = self.hub.medien.serien.get(sid)
            if info is None:
                return {"uebersprungen": True, "geaendert": 0, "vorschlaege": 0, "fehler": False, "pause": None}
            s = info.serie
            stand = self.tonie_liste.stand if self.tonie_liste else None
            try:
                marke_ok = self.store.marke_gueltig(sid, list(s.folgen), stand)
                return await self._arbeite_serie(sid, folgen=None, neu=False, im_lauf=True, lauf_id=lauf["lauf_id"], nur_claude=marke_ok)
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("Online-Suche im Lauf: Eintrag %s übersprungen", sid)
                with contextlib.suppress(Exception):
                    self.store.setze_marke(sid, "fehler", list(s.folgen), stand)
                return {"uebersprungen": True, "geaendert": 0, "vorschlaege": 0, "fehler": True, "pause": None}

    async def _lauf_laufen(self, lauf: dict[str, Any], ids: list[str]) -> None:
        z = lauf["zahlen"]
        pausen = 0
        try:
            for sid in ids:
                if self._stop:
                    await self._lauf_beenden(lauf, "angehalten", "angehalten")
                    return
                while True:
                    erg = await self._serie_im_lauf(sid, lauf)
                    if erg.get("pause") is None:
                        pausen = 0
                        break
                    pausen += 1
                    if pausen >= PAUSEN_BIS_ABBRUCH:
                        await self._lauf_beenden(lauf, "abgebrochen", "quelle")
                        return
                    if self._stop:  # ``wird_angehalten`` nicht mit ``pausiert`` überschreiben (GO3-12)
                        await self._lauf_beenden(lauf, "angehalten", "angehalten")
                        return
                    lauf["zustand"] = "pausiert"
                    lauf["pause_bis"] = erg["pause"].pause_bis
                    self._emit_stand("lauf", lambda: self._stand_daten(lauf))
                    await self._warte_pause(max(0.0, erg["pause"].pause_bis - self._zeit()) + 1.0)
                    if self._stop:
                        await self._lauf_beenden(lauf, "angehalten", "angehalten")
                        return
                    lauf["zustand"] = "laeuft"
                    lauf["pause_bis"] = None
                z["erledigt"] += 1
                if erg.get("geaendert"):
                    z["geaendert"] += 1
                z["vorschlaege"] += erg.get("vorschlaege", 0)
                if not erg.get("geaendert") and not erg.get("vorschlaege"):
                    z["keiner"] += 1
                self._emit_stand("lauf", lambda: self._stand_daten(lauf))
            await self._lauf_beenden(lauf, "fertig", None)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Ein Fehler außerhalb einer einzelnen Serie (Speicher, Ereignis): der Lauf endet ohne ``grund``; ``quelle`` heißt nur „drei Pausen in Folge“
            _LOGGER.exception("Lauf der Online-Suche fehlgeschlagen")
            await self._lauf_beenden(lauf, "abgebrochen", None)

    # ----------------------------------------------------------------------
    # Nr. 63 Status
    # ----------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Nr. 63 (und ``snapshot`` des Themas ``online``): aus dem Arbeitsspeicher, ohne Netz.

        Pausengruppen von ``online_quellen`` -> Quellen: ``itunes`` (und ``bilder``, Apples Bilder), ``tonies`` (Tonie-Liste), ``tonies_shop``
        (Shopseiten und Sitemap)."""
        q = self.quellen

        def pause(*gruppen: str) -> float | None:
            if q is None:
                return None
            bis = [b for b in (q.pause_bis(g) for g in gruppen) if b is not None]
            return max(bis) if bis else None

        quellen: dict[str, Any] = {}
        for name, gruppen in (("itunes", ("itunes", "bilder")), ("tonies", ("tonies",)), ("tonies_shop", ("tonies_shop",))):
            b = pause(*gruppen)
            e: dict[str, Any] = {"erreichbar": b is None}
            if b is not None:
                e["pause_bis"] = _zeit_iso(b)
            quellen[name] = e
        entitaet = self.ki_entitaet()
        eingerichtet = bool(entitaet)
        quellen["claude"] = {"eingerichtet": eingerichtet, "erreichbar": bool(eingerichtet and self.ki.erreichbar(self.hub.hass, entitaet))}
        liste = self.tonie_liste
        tl = {"stand": _zeit_iso(liste.stand), "anzahl": liste.anzahl} if liste is not None and liste.stand is not None else None
        letzte = []
        for lauf in reversed(self.store.daten["laeufe"]):
            if lauf.get("zustand") not in LAUF_ENDE:
                continue
            e2: dict[str, Any] = {"lauf_id": lauf["lauf_id"], "beginn": lauf["beginn"], "ende": lauf.get("ende"), "zustand": lauf["zustand"], "zahlen": dict(lauf["zahlen"])}
            if lauf.get("grund"):
                e2["grund"] = lauf["grund"]
            letzte.append(e2)
        return {"lauf": self.lauf_zustand(), "quellen": quellen, "tonie_liste": tl, "letzte_laeufe": letzte[:LAEUFE_MAX]}

    # ----------------------------------------------------------------------
    # Nr. 64
    # ----------------------------------------------------------------------

    async def beschreibung(self, serie_id: str, folge: str) -> dict[str, Any]:
        """Nr. 64 (Recht lesen): voller Text aus dem Store, ohne Netz. Ohne Beschreibung sind ``beschreibung`` und ``quelle`` ``None``."""
        info = self.hub.medien.finde(serie_id)
        if folge not in info.serie.folgen:
            raise TobiboxFehler("folge_nicht_gefunden")
        i = self.store.folge_info(serie_id, folge)
        text = i.get("beschreibung")
        if not isinstance(text, str) or not text:
            return {"beschreibung": None, "quelle": None}
        aus: dict[str, Any] = {"beschreibung": text[:ONLINE_BESCHREIBUNG_MAX], "quelle": i.get("quelle")}
        if isinstance(i.get("alter_ab"), int):
            aus["alter_ab"] = i["alter_ab"]
        return aus

    # ----------------------------------------------------------------------
    # Nr. 60 Rücknahme (6.4)
    # ----------------------------------------------------------------------

    async def zuruecknehmen(self, serie_id: str | None = None, aenderung_id: str | None = None, lauf_id: str | None = None) -> dict[str, Any]:
        """Nr. 60. Genau eine Form: ``serie_id`` + ``aenderung_id``, ``serie_id`` allein, oder ``lauf_id`` allein (sonst ``invalid_format``)."""
        if lauf_id is not None:
            if serie_id is not None or aenderung_id is not None:
                raise TobiboxFehler("invalid_format")
            if not any(x.get("lauf_id") == lauf_id for x in self.store.daten["laeufe"]):
                raise TobiboxFehler("lauf_nicht_gefunden")
            if self._rueck_task is not None and not self._rueck_task.done():
                # dieselbe Rücknahme (läuft oder wartet): Endzustand gleich, keine zweite; sonst hinten anstellen (nie ``lauf_laeuft_schon``)
                if lauf_id != self._rueck_lauf_id and lauf_id not in self._rueck_wartend:
                    self._rueck_wartend.append(lauf_id)
                return {"gestartet": True}
            self._rueck_lauf_id = lauf_id
            self._rueck_task = self.hub.hass.async_create_background_task(self._rueck_abarbeiten(lauf_id), "tobibox_online_rueck")
            return {"gestartet": True}
        if serie_id is None:
            raise TobiboxFehler("invalid_format")
        medien = self.hub.medien
        medien.finde(serie_id)
        if aenderung_id is not None and not any(a["id"] == aenderung_id for a in self.store.aenderungen(serie_id)):
            raise TobiboxFehler("aenderung_nicht_gefunden")
        erg = await self._zuruecknehmen_serie(serie_id, aenderung_id, None, setze_marke=True)
        uebersprungen = erg["uebersprungen"]
        return {
            "zurueckgenommen": erg["zurueckgenommen"],
            "uebersprungen": uebersprungen[:ONLINE_UEBERSPRUNGEN_MAX],
            "uebersprungen_anzahl": len(uebersprungen),
        }

    async def _rueck_abarbeiten(self, lauf_id: str) -> None:
        """Nimmt die Läufe nacheinander zurück: erst ``lauf_id``, dann die, die währenddessen angestellt wurden."""
        while True:
            await self._lauf_zuruecknehmen(lauf_id)
            if not self._rueck_wartend:
                return
            lauf_id = self._rueck_lauf_id = self._rueck_wartend.pop(0)

    async def warte_auf_rueck(self) -> None:
        while self._rueck_task is not None and not self._rueck_task.done():
            await asyncio.shield(self._rueck_task)

    async def _lauf_zuruecknehmen(self, lauf_id: str) -> None:
        sids = [sid for sid, s in self.store.daten["serien"].items() if any(a.get("lauf_id") == lauf_id and a.get("status") == "fertig" for a in s.get("aenderungen") or [])]
        zahlen = {"zurueckgenommen": 0, "uebersprungen_anzahl": 0}
        daten0 = {"vorgang": "zuruecknahme", "lauf_id": lauf_id, "zustand": "laeuft", "erledigt": 0, "gesamt": len(sids)}

        def stand(erledigt: int) -> dict[str, Any]:
            return {**daten0, "erledigt": erledigt, **zahlen}

        try:
            for i, sid in enumerate(sids):
                try:
                    erg = await self._zuruecknehmen_serie(sid, None, lauf_id, setze_marke=False)
                    zahlen["zurueckgenommen"] += erg["zurueckgenommen"]
                    zahlen["uebersprungen_anzahl"] += len(erg["uebersprungen"])
                except TobiboxFehler:
                    zahlen["uebersprungen_anzahl"] += 1
                self._emit_stand("zuruecknahme", lambda i=i: stand(i + 1))
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Rücknahme des Laufs %s fehlgeschlagen", lauf_id)
        self._emit("fertig", {**stand(len(sids)), "zustand": "fertig"})

    async def _zuruecknehmen_serie(self, sid: str, aenderung_id: str | None, lauf_id: str | None, *, setze_marke: bool) -> dict[str, Any]:
        """Ein Schritt je Serie unter ihrer Sperre (6.4). Ein Feld wird nur zurückgesetzt, wenn es noch den Online-Wert trägt."""
        medien = self.hub.medien
        store = self.store
        zurueck = 0
        uebersprungen: list[dict[str, str]] = []
        async with medien.sperren(sid):
            try:
                serie, pfad = await medien._frisch(sid)
            except TobiboxFehler as err:
                if err.code != "serie_nicht_gefunden":
                    raise
                if aenderung_id is not None:
                    raise
                ziel = [a for a in store.aenderungen(sid) if a.get("status") == "fertig" and (lauf_id is None or a.get("lauf_id") == lauf_id)]
                for a in ziel:
                    for key in a.get("felder") or {}:
                        uebersprungen.append({"serie_id": sid, "feld": key, "grund": "serie_nicht_gefunden"})
                return {"zurueckgenommen": 0, "uebersprungen": uebersprungen}
            kandidaten = [
                a for a in reversed(store.aenderungen(sid))
                if a.get("status") == "fertig" and (aenderung_id is None or a["id"] == aenderung_id) and (lauf_id is None or a.get("lauf_id") == lauf_id)
            ]
            geaendert_serie = False
            pruefen_zurueck: dict[str, list[str]] = {}
            for a in kandidaten:
                zurueck_a, skip, zurueck_keys, serie_geaendert, pz = await self._eine_aenderung_zuruecknehmen(sid, serie, pfad, a, setze_marke)
                zurueck += zurueck_a
                uebersprungen += [{"serie_id": sid, "feld": k, "grund": g} for k, g in skip]
                geaendert_serie = geaendert_serie or serie_geaendert
                pruefen_zurueck.update(pz)
                if zurueck_keys:
                    a["status"] = "zurueckgenommen"
            if geaendert_serie:
                try:
                    await medien._executor(schreibe_serie, pfad, serie)
                except OSError as err:
                    raise medien._fehler_schreiben(err) from err
            if kandidaten:
                await medien._aktualisiere_cache(serie, pfad.name)
                await store.sofort()
        if pruefen_zurueck if kandidaten else False:
            self.hub.eingang.pruefen_wiederherstellen(sid, pruefen_zurueck)
        if zurueck:
            self._serien_geaendert(sid)
        return {"zurueckgenommen": zurueck, "uebersprungen": uebersprungen}

    async def _eine_aenderung_zuruecknehmen(
        self, sid: str, serie: Serie, pfad: Path, a: dict[str, Any], setze_marke: bool
    ) -> tuple[int, list[tuple[str, str]], list[str], bool, dict[str, list[str]]]:
        """``(zurückgenommene Felder, übersprungen[(key, grund)], zurückgenommene Keys, serie.json geändert, Prüfgründe zum Wiederherstellen im Protokoll)``."""
        medien = self.hub.medien
        store = self.store
        felder: dict[str, dict[str, Any]] = a.get("felder") or {}
        zurueck_keys: list[str] = []
        skip: list[tuple[str, str]] = []
        geaendert = False
        pruef_vorher = a.get("pruefen_vorher") or {}
        paare: dict[str, list[str]] = {}
        for key in felder:
            feld, folge = teile_key(key)
            if folge is not None and feld in ("folge_titel", "nummer"):
                paare.setdefault(folge, []).append(key)

        def trifft(key: str) -> bool:
            feld, folge = teile_key(key)
            nach = felder[key]["nachher"]
            if feld == "serie_name":
                return serie.name == nach
            if feld == "art":
                return {"art": serie.art, "art_quelle": serie.art_quelle} == nach
            if feld == "folge_titel":
                return serie.info(folge or "").get("anzeige") == nach
            if feld == "nummer":
                return serie.info(folge or "").get("nummer") == nach
            return store.folge_info(sid, folge or "").get(feld) == nach

        cover_ok = False
        if "cover" in felder:
            aktuell = await medien._executor(online_stand, pfad)
            cover_ok = aktuell is not None and aktuell == a.get("cover_stand")
        for key in felder:
            feld, folge = teile_key(key)
            if folge is not None and folge not in serie.folgen:
                skip.append((key, "folge_verschoben"))
                continue
            if feld == "cover":
                if not cover_ok:
                    skip.append((key, "seitdem_geaendert"))
                    continue
            elif feld in ("folge_titel", "nummer") and folge is not None:
                if not all(trifft(k) for k in paare[folge]):
                    skip.append((key, "seitdem_geaendert"))
                    continue
            elif not trifft(key):
                skip.append((key, "seitdem_geaendert"))
                continue
            vorher = felder[key]["vorher"]
            if feld == "serie_name":
                serie.name = vorher
                geaendert = True
            elif feld == "art":
                serie.art, serie.art_quelle = vorher["art"], vorher["art_quelle"]
                geaendert = True
            elif feld == "folge_titel":
                serie.setze_info(folge, anzeige=vorher)
                geaendert = True
            elif feld == "nummer":
                serie.setze_info(folge, nummer=vorher)
                geaendert = True
            elif feld == "cover":
                try:
                    await medien._executor(loesche_datei, pfad / COVER_ONLINE)
                except OSError as err:
                    raise medien._fehler_schreiben(err) from err
            elif feld in ("beschreibung", "alter_ab"):
                store.setze_folge_info(sid, folge or "", **{feld: vorher})
            zurueck_keys.append(key)
        # Bestätigtes (6.4, GO3-1): kein Feld wurde geändert, also nichts zu zählen, kein Schnappschuss, keine Marke. Nur der Prüfgrund kommt
        # zurück, und nur, solange das Feld noch so dasteht, wie die Bestätigung es hinterließ.
        bestaetigt = [k for k in (a.get("bestaetigt") or []) if self._bestaetigung_gilt(sid, serie, k)]
        wirksam = zurueck_keys + bestaetigt
        # Prüfgründe zurück
        pz: dict[str, list[str]] = {}
        if any(teile_key(k)[0] in ("art", "serie_name") for k in wirksam):
            sv = pruef_vorher.get("serie") or {}
            serie.pruefen = bool(sv.get("pruefen"))
            serie.pruefen_gruende = list(sv.get("pruefen_gruende") or [])
            geaendert = True
        for f, i in (pruef_vorher.get("folgen") or {}).items():
            beruehrt = any(teile_key(k)[1] == f and teile_key(k)[0] in ("folge_titel", "nummer") for k in wirksam)
            if beruehrt and f in serie.folgen and not serie.info(f).get("pruefen"):
                serie.setze_info(f, pruefen=True, pruefen_gruende=list(i.get("pruefen_gruende") or []))
                pz[f] = list(i.get("pruefen_gruende") or [])
                geaendert = True
        # Schnappschuss weg, hand weg, Marke: nur für wirklich zurückgesetzte Felder
        for key in zurueck_keys:
            store.loesche_schnapp(sid, key)
            store.nimm_hand(sid, key)
            if setze_marke:
                store.setze_zurueckgenommen(sid, key)
        return len(zurueck_keys), skip, wirksam, geaendert, pz

    def _bestaetigung_gilt(self, sid: str, serie: Serie, key: str) -> bool:
        """Steht das bestätigte Feld noch so da (Prüfgrund gelöst, nicht seitdem von Hand geändert)?"""
        feld, folge = teile_key(key)
        if self.store.hand_hat(sid, key) or self.store.zurueck_hat(sid, key):
            return False
        if feld == "art":
            return serie.art_quelle in (None, "geraten") and "art_geraten" not in serie.pruefen_gruende
        if folge is None or folge not in serie.folgen:
            return False
        return feld in ("folge_titel", "nummer") and not serie.info(folge).get("pruefen")

    # ----------------------------------------------------------------------
    # 5.2 Suche von Hand (Nr. 57 bis 59)
    # ----------------------------------------------------------------------

    def _info_fuer_suche(self, serie_id: str, folge: str | None) -> Any:
        info = self.hub.medien.finde(serie_id)
        if info.serie.typ != "normal":
            raise TobiboxFehler("invalid_format")
        if folge is not None and folge not in info.serie.folgen:
            raise TobiboxFehler("folge_nicht_gefunden")
        return info

    async def suchen(self, serie_id: str, folge: str | None = None, text: str | None = None) -> dict[str, Any]:
        """Nr. 57: sucht bei Apple und in der Tonie-Liste, höchstens 10 Treffer; Bilder der obersten 5 werden schon geladen."""
        info = self._info_fuer_suche(serie_id, folge)
        serie = info.serie
        if text is not None and not 2 <= len(text.strip()) <= 100:
            raise TobiboxFehler("invalid_format")
        suchtext = (text or "").strip() or (serie.anzeige(folge) if folge else serie.name)
        q = await self._quellen_bereit()
        assert self.tonie_liste is not None
        quellen_zustand = {"itunes": "ok", "tonies": "ok"}
        apple: list[dict[str, Any]] = []
        for art in ("album", "hoerbuch"):
            try:
                apple += await q.itunes_suche(suchtext, art, von_hand=True)
            except QuellePausiert as err:
                quellen_zustand["itunes"] = "pause"
                self._melde_quelle("itunes", False, err.pause_bis)
            except Gedrosselt:
                quellen_zustand["itunes"] = "pause"
            except OnlineFehler:
                quellen_zustand["itunes"] = "fehler"
        tonie_treffer: list[dict[str, Any]] = []
        liste_da = await self.tonie_liste.sicherstellen()
        self._melde_tonies()
        if liste_da:
            index = await self._index()
            roh = {x["model"]: x for x in self.tonie_liste.eintraege}
            tonie_treffer = [roh[e["model"]] for e in await q.im_executor(self._tonie_treffer, index, suchtext) if e["model"] in roh]  # rohe Einträge der Liste
        else:
            quellen_zustand["tonies"] = "fehler"
        if "ok" not in quellen_zustand.values():
            raise TobiboxFehler("online_nicht_erreichbar")
        apple = [r for r in ab.apple_entdoppeln(apple) if r.get("wrapperType") in ("collection", "audiobook")]
        sitemap: list[str] | None = None
        if tonie_treffer:
            with contextlib.suppress(OnlineFehler):
                sitemap = await q.sitemap_pfade()
        treffer = await self._treffer_bauen(info, folge, suchtext, apple, tonie_treffer, sitemap)
        such_id = secrets.token_hex(6)
        for i, t in enumerate(treffer):
            t["id"] = f"{such_id}{i:04x}"
        # Bilder der obersten 5 Treffer
        for t in treffer[:ONLINE_TREFFER_BILDER]:
            await self._treffer_bild(t)
        q.treffer_speicher.lege(such_id, {"serie_id": serie_id, "treffer": treffer})
        return {"treffer": [self._treffer_aus(t, serie_id) for t in treffer], "quellen": quellen_zustand}

    @staticmethod
    def _tonie_treffer(index: dict[str, Any], text: str) -> list[dict[str, Any]]:
        qw = set(ab.woerter(text))
        if not qw:
            return []
        gut = []
        for e in index["eintraege"]:
            worte = set(e["series_w"]) | set(ab.woerter(e["episodes"]))
            score = len(qw & worte) / len(qw)
            if score >= 0.6 and e["episodes"]:
                gut.append((-score, e["model"], e))
        gut.sort(key=lambda x: x[:2])
        return [e for *_x, e in gut[:5]]

    def _treffer_aus(self, t: dict[str, Any], sid: str) -> dict[str, Any]:
        aus: dict[str, Any] = {
            "treffer_id": t["id"],
            "quelle": t["quelle"],
            "titel": t["titel"],
            "reihe": t.get("reihe"),
            "hat_cover": bool(t.get("cover") and t["cover"].get("url")),
            "frueher_abgelehnt": self._frueher_abgelehnt(sid, t),
            "felder": list(t["felder"]),
        }
        for k in ("nummer", "tracks", "art"):
            if t.get(k) is not None:
                aus[k] = t[k]
        return aus

    def _frueher_abgelehnt(self, sid: str, t: dict[str, Any]) -> bool:
        for key, wert in t["werte"].items():
            kennung = t["cover"].get("collection_id") if key == "cover" and t.get("cover") else None
            if self.store.verworfen_hat(sid, key if teile_key(key)[1] is not None else key, wert_hash(key, wert, t["quelle"], kennung), t["quelle"]):
                return True
        return False

    async def _treffer_bild(self, t: dict[str, Any]) -> bool:
        c = t.get("cover")
        if not c or not c.get("url"):
            return False
        if c.get("bild"):
            return True
        erg: dict[str, Any] = {}
        c["bild"] = await self._cover_bytes(c["url"], erg, von_hand=True)
        return c["bild"] is not None

    async def _treffer_bauen(
        self, info: Any, folge: str | None, text: str, apple: list[dict[str, Any]], tonies: list[dict[str, Any]], sitemap: list[str] | None
    ) -> list[dict[str, Any]]:
        """Zu jedem Treffer: Felder, Werte, ``sicher`` (aus den vorhandenen Regeln von ``online_abgleich``, kein zweiter Regelsatz)."""
        serie = info.serie
        q = self.quellen
        assert q is not None
        eintrag = self._eintrag_fuer_abgleich(info)
        eintrag["cover_quelle"] = "auto"  # Schutz zählt nicht für ``sicher``; ``hand`` sagt die Übersicht
        eintrag["art_quelle"] = "geraten"
        n = len(serie.folgen)
        im_blick = [folge] if folge else (list(serie.folgen) if n == 1 else [])
        qw = set(ab.woerter(text))
        roh: list[tuple[float, dict[str, Any]]] = []
        for r in apple:
            name = r.get("collectionName") or ""
            if not isinstance(name, str) or ab.apple_ausschluss(name, r.get("trackCount"), None):
                continue
            worte = set(ab.woerter(name)) | set(ab.woerter(r.get("artistName") or ""))
            score = len(qw & worte) / len(qw) if qw else 0.0
            roh.append((score, {"typ": "apple", "r": r}))
        roh.sort(key=lambda x: -x[0])
        kandidaten = [x[1] for x in roh[: ONLINE_TREFFER_MAX - len(tonies)]] + [{"typ": "tonie", "roh": x} for x in tonies]
        aus: list[dict[str, Any]] = []
        for k in kandidaten[:ONLINE_TREFFER_MAX]:
            t = await self._treffer_aus_roh(info, eintrag, im_blick, k, sitemap)
            if t is not None:
                aus.append(t)
        return aus

    async def _treffer_aus_roh(self, info: Any, eintrag: dict[str, Any], im_blick: list[str], k: dict[str, Any], sitemap: list[str] | None) -> dict[str, Any] | None:
        serie = info.serie
        q = self.quellen
        assert q is not None
        n = len(serie.folgen)
        ctxs = [ab.folge_kontext(serie.name, f, bool(serie.einzeln), n) for f in eintrag["folgen"]]
        werte: dict[str, Any] = {}
        sicher: dict[str, bool] = {}
        cover: dict[str, Any] | None = None
        r: dict[str, Any] = k.get("r") or {}
        e: dict[str, Any] = {}
        if k["typ"] == "apple":
            index = self._leerer_index()
            ergebnisse: list[list[dict[str, Any]] | None] = [[r] for _ in range(n)]
            shop: dict[str, Any] = {}
            quelle = "itunes"
            titel = r.get("collectionName") or ""
            reihe = r.get("artistName")
            nummer = ab.nummer_abtrennen(titel, ab.woerter(reihe or ""))[0] if titel else None
            tracks = r.get("trackCount") if isinstance(r.get("trackCount"), int) else None
            art = ab.apple_art(r)
            bild = r.get("artworkUrl100")
        else:
            index = ab.tonie_index_bauen([k["roh"]])
            e = index["eintraege"][0]
            ergebnisse = [[] for _ in range(n)]
            shop = {}
            quelle = "tonies"
            titel = e["episodes"]
            reihe = e["series"]
            nummer = e["ep_nummer"]
            tracks = e["tracks"] or None
            art = e["art"]
            bild = None
            if im_blick and sitemap is not None:
                tp = ab.tonie_pruefen(ctxs[serie.folgen.index(im_blick[0])], index, sitemap)
                for pfad, model in tp["shop_pfade"][:1]:
                    if pfad:
                        try:
                            shop[model] = await q.shop_seite(pfad, model, von_hand=True)
                        except (OnlineFehler, Gedrosselt):
                            pass
        res = ab.bewerte_eintrag(eintrag, index, ergebnisse, shop, sitemap if shop else None)
        # Eintrag: Art, Cover, Name
        if art:
            werte["art"] = art
            sicher["art"] = res["art"]["status"] == "sicher" and res["art"]["neu"] == art
        if bild:
            url = bild_url_600(bild)
            if url:
                cover = {"url": url, "collection_id": r.get("collectionId"), "bild": None}
                werte["cover"] = url
                sicher["cover"] = res["cover"]["status"] == "sicher"
        # Name: bei der Suche für den Eintrag der Titel des Treffers (Reihen-Album), bei der Suche für eine Folge die Reihe (Künstler)
        if k["typ"] == "apple":
            name_neu = online_text(reihe if im_blick else titel, SERIE_NAME_MAX)
        else:
            name_neu = online_text(reihe, SERIE_NAME_MAX)
        if name_neu:
            werte["serie_name"] = name_neu
            sicher["serie_name"] = False
        # Folge (eine im Blick)
        for f in im_blick:
            idx = serie.folgen.index(f)
            fres = res["folgen"][idx]
            ctx = ctxs[idx]
            if k["typ"] == "apple":
                nr = nummer if nummer is not None else ctx["nummer_bekannt"]
                neu_titel = ab.titel_neu(ctx, {"album": titel}, nr)
                werte[feld_key("folge_titel", f)] = online_text(neu_titel, FOLGE_ANZEIGE_MAX)
                sicher[feld_key("folge_titel", f)] = fres["folge_titel"]["status"] == "sicher"
                if nummer is not None:
                    werte[feld_key("nummer", f)] = nummer
                    sicher[feld_key("nummer", f)] = fres["nummer"]["status"] == "sicher" and fres["nummer"]["neu"] == nummer
                if r.get("description") and r.get("wrapperType") == "audiobook":
                    text = beschreibung_text(html_zu_text(r["description"]) if isinstance(r["description"], str) else None)
                    if text:
                        werte[feld_key("beschreibung", f)] = text
                        sicher[feld_key("beschreibung", f)] = fres["beschreibung"]["status"] == "sicher" and fres["beschreibung"]["neu"] == text
            else:
                rest = e["ep_rest"] or e["episodes"]
                neu_titel = f"Folge {nummer}: {rest}" if nummer is not None else rest
                werte[feld_key("folge_titel", f)] = online_text(neu_titel, FOLGE_ANZEIGE_MAX)
                sicher[feld_key("folge_titel", f)] = False
                if nummer is not None:
                    werte[feld_key("nummer", f)] = nummer
                    sicher[feld_key("nummer", f)] = res["folgen"][idx]["nummer"]["status"] == "sicher"
                daten = next((v for v in shop.values() if isinstance(v, dict)), None)
                if daten:
                    if daten.get("beschreibung"):
                        werte[feld_key("beschreibung", f)] = beschreibung_text(daten["beschreibung"])
                        sicher[feld_key("beschreibung", f)] = fres["beschreibung"]["status"] == "sicher"
                    if isinstance(daten.get("alter_ab"), int):
                        werte[feld_key("alter_ab", f)] = daten["alter_ab"]
                        sicher[feld_key("alter_ab", f)] = fres["alter_ab"]["status"] == "sicher"
        werte = {key: w for key, w in werte.items() if w is not None}
        if not werte:
            return None
        return {
            "quelle": quelle,
            "titel": online_text(titel, 300) or "",
            "reihe": online_text(reihe, 300) if reihe else None,
            "nummer": nummer,
            "tracks": tracks,
            "art": art,
            "cover": cover,
            "felder": list(werte),
            "werte": werte,
            "sicher": {key: bool(sicher.get(key)) for key in werte},
            "folge": im_blick[0] if im_blick else None,
            "grund": None,
        }

    def _suche_holen(self, treffer_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """``(Suche, Treffer)`` zu einer ``treffer_id``; sonst ``treffer_abgelaufen`` (nach 15 Minuten, nach Neustart, ungültige ID)."""
        q = self.quellen
        if q is None or not isinstance(treffer_id, str) or len(treffer_id) != 16:
            raise TobiboxFehler("treffer_abgelaufen")
        such = q.treffer_speicher.hole(treffer_id[:12])
        try:
            idx = int(treffer_id[12:], 16)
        except ValueError as err:
            raise TobiboxFehler("treffer_abgelaufen") from err
        if such is None or idx >= len(such["treffer"]):
            raise TobiboxFehler("treffer_abgelaufen")
        return such, such["treffer"][idx]

    def treffer_bild(self, treffer_id: str) -> bytes | None:
        """Für die Vorschau (HTTP): das gehaltene 512-px-Bild; ``treffer_abgelaufen`` oder ``None`` (Treffer ohne Bild)."""
        _such, t = self._suche_holen(treffer_id)
        c = t.get("cover")
        return c.get("bild") if c else None

    def _heute(self, sid: str, info: Any, key: str) -> Any:
        serie = info.serie
        feld, folge = teile_key(key)
        if feld == "serie_name":
            return serie.name
        if feld == "art":
            return serie.art or "hoerspiel"
        if feld == "cover":
            return info.cover_quelle
        if feld == "folge_titel":
            return serie.anzeige(folge or "")
        if feld == "nummer":
            return serie.info(folge or "").get("nummer")
        return self.store.folge_info(sid, folge or "").get(feld)

    async def treffer(self, treffer_id: str | None = None, serie_id: str | None = None, vorschlag_id: str | None = None) -> dict[str, Any]:
        """Nr. 58: die Übersicht „heute -> neu“ je Feld. Eine Quelle: ``treffer_id`` **oder** ``serie_id`` + ``vorschlag_id``."""
        if (treffer_id is None) == (vorschlag_id is None) or (vorschlag_id is not None and serie_id is None) or (treffer_id is not None and serie_id is not None):
            raise TobiboxFehler("invalid_format")
        felder: dict[str, Any] = {}
        grund: str | None = None
        if treffer_id is not None:
            such, t = self._suche_holen(treffer_id)
            sid = such["serie_id"]
            info = self.hub.medien.finde(sid)
            if t.get("cover") and not t["cover"].get("bild"):
                await self._treffer_bild(t)
            werte, sicher = t["werte"], t["sicher"]
            cover_da = bool(t.get("cover") and t["cover"].get("bild"))
        else:
            sid = serie_id  # type: ignore[assignment]
            info = self.hub.medien.finde(sid)
            v = next((v for v in self.vorschlaege_gueltig(sid) if v["id"] == vorschlag_id), None)
            if v is None or v["art"] != "felder":
                raise TobiboxFehler("vorschlag_nicht_gefunden")
            werte = {k: (w.get("cover_url") if isinstance(w, dict) else w) for k, w in (v.get("werte") or {}).items()}
            sicher = dict.fromkeys(werte, False)
            grund = v.get("grund") if v["quelle"] == "claude" else None
            cover_da = False
            if "cover" in werte:
                erg: dict[str, Any] = {}
                bild = await self._cover_bytes(werte["cover"], erg, von_hand=True)
                cover_da = bild is not None
        for key, neu in werte.items():
            feld, folge = teile_key(key)
            if feld == "cover":
                if not cover_da:
                    continue
                felder[key] = {"heute": info.cover_quelle, "neu": True, "sicher": bool(sicher.get(key)), "hand": self.ist_von_hand(sid, feld, folge, info.serie, info)}
                continue
            heute = self._heute(sid, info, key)
            if heute == neu:
                continue
            felder[key] = {"heute": heute, "neu": neu, "sicher": bool(sicher.get(key)), "hand": self.ist_von_hand(sid, feld, folge, info.serie, info)}
        aus: dict[str, Any] = {"felder": felder}
        if grund:
            aus["grund"] = grund
        return aus

    async def uebernehmen(
        self,
        serie_id: str,
        felder: list[str],
        *,
        treffer_id: str | None = None,
        vorschlag_id: str | None = None,
        stand: str | None = None,
        nutzer_id: str | None = None,
    ) -> dict[str, Any]:
        """Nr. 59: schreibt die gewählten Felder als **eine** Änderung von Hand (6.3). Werte kommen nie aus der Eingabe."""
        if (treffer_id is None) == (vorschlag_id is None):
            raise TobiboxFehler("invalid_format")
        medien = self.hub.medien
        info = medien.finde(serie_id)
        felder = list(dict.fromkeys(felder))
        if not felder or "serie_name" in felder and stand is None:
            raise TobiboxFehler("invalid_format")
        quelle = "itunes"
        cover_bild: bytes | None = None
        grund_claude = False
        if treffer_id is not None:
            such, t = self._suche_holen(treffer_id)
            if such["serie_id"] != serie_id:
                raise TobiboxFehler("treffer_abgelaufen")
            werte = {k: w for k, w in t["werte"].items()}
            quelle = t["quelle"]
            if "cover" in felder and "cover" in werte:
                if not t["cover"].get("bild"):
                    await self._treffer_bild(t)
                cover_bild = t["cover"].get("bild")
        else:
            v = next((v for v in self.vorschlaege_gueltig(serie_id) if v["id"] == vorschlag_id), None)
            if v is None:
                raise TobiboxFehler("vorschlag_nicht_gefunden")
            if v["art"] != "felder":
                raise TobiboxFehler("invalid_format")
            werte = {k: (w.get("cover_url") if isinstance(w, dict) else w) for k, w in (v.get("werte") or {}).items()}
            quelle = v["quelle"]
            grund_claude = v["quelle"] == "claude"
            if "cover" in felder and "cover" in werte:
                cover_bild = await self._cover_bytes(werte["cover"], {}, von_hand=True)
        for key in felder:
            feld, folge = teile_key(key)
            if feld not in (*EINTRAG_FELDER, *FOLGEN_FELDER) or (folge is None) != (feld in EINTRAG_FELDER):
                raise TobiboxFehler("invalid_format")
            if folge is not None and folge not in info.serie.folgen:
                raise TobiboxFehler("folge_nicht_gefunden")
            if key not in werte:
                raise TobiboxFehler("invalid_format")  # das Feld bietet der Treffer bzw. Vorschlag nicht an
        if "cover" in felder and cover_bild is None:
            raise TobiboxFehler("invalid_format")
        if grund_claude and felder == ["serie_name"]:
            return await self._name_uebernehmen(serie_id, vorschlag_id or "", werte["serie_name"], stand)
        zeilen: dict[str, dict[str, Any]] = {}
        for key in felder:
            feld, folge = teile_key(key)
            zeilen[key] = {"key": key, "feld": feld, "folge": folge, "neu": werte[key], "quelle": quelle, "extra": {}}
        async with medien.sperren(serie_id):
            serie, pfad = await medien._frisch(serie_id)
            if stand is not None and stand != serie.stand:
                raise TobiboxFehler("stand_veraltet")
            for key, z in zeilen.items():
                if z["feld"] in ("folge_titel", "nummer", "beschreibung", "alter_ab") and z["folge"] not in serie.folgen:
                    raise TobiboxFehler("folge_nicht_gefunden")
            aid = await self._schreibe(serie_id, serie, pfad, zeilen, [], wer=nutzer_id or "hand", quelle=quelle, lauf_id=None, automatisch=False, cover_bytes=cover_bild)
            stand_neu = serie.stand
        # Ein Vorschlag, dessen Felder alle übernommen sind, verschwindet (kein „Nein“)
        if vorschlag_id is not None:
            vl = self.store.vorschlaege(serie_id)
            neu_liste = []
            for v in vl:
                if v["id"] == vorschlag_id and v.get("art") == "felder":
                    rest = [k for k in v.get("felder") or [] if k not in felder]
                    if not rest:
                        continue
                    v["felder"] = rest
                    v["werte"] = {k: w for k, w in (v.get("werte") or {}).items() if k in rest}
                neu_liste.append(v)
            self.store.serie(serie_id)["vorschlaege"] = neu_liste
            self.store._aufraeumen(serie_id)  # noqa: SLF001
            await self.store.sofort()
            self._serien_geaendert(serie_id)
        return {"aenderung_id": aid, "serie_id": serie_id, "stand": stand_neu}

    async def _name_uebernehmen(self, sid: str, vorschlag_id: str, name: str, stand: str | None) -> dict[str, Any]:
        """Ein Namensvorschlag von Claude wirkt wie ``serie/rename`` von Hand: gleiche Namensprüfung, **keine** Online-Änderung (``aenderung_id`` ``None``, GO-14)."""
        medien = self.hub.medien
        anzeige = name_pruefen(name, SERIE_NAME_MAX)
        async with medien.sperren(sid):
            serie, pfad = await medien._frisch(sid)
            if stand != serie.stand:
                raise TobiboxFehler("stand_veraltet")
            v = next((v for v in self.vorschlaege_gueltig(sid) if v["id"] == vorschlag_id), None)
            if v is None:
                raise TobiboxFehler("vorschlag_nicht_gefunden")
            serie.name = anzeige
            serie.pruefen = False
            serie.pruefen_gruende = []
            try:
                await medien._executor(schreibe_serie, pfad, serie)
            except OSError as err:
                raise medien._fehler_schreiben(err) from err
            self.von_hand_gesetzt(sid, "serie_name")
            self.store.setze_hand(sid, "serie_name")
            self.store.serie(sid)["vorschlaege"] = [x for x in self.store.vorschlaege(sid) if x["id"] != vorschlag_id]
            await medien._aktualisiere_cache(serie, pfad.name)
            stand_neu = serie.stand
        await self.store.sofort()
        self._serien_geaendert(sid)
        return {"aenderung_id": None, "serie_id": sid, "stand": stand_neu}
