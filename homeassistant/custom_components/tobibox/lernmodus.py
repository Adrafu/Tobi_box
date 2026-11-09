"""Lernmodus, Weg B (Vertrag W, 3.6 und 6.2; ``mqtt-v1.md`` 4.2).

Das Backend merkt sich Box, Ziel und Beginn eines Vorgangs, sendet den Befehl ``lernen`` und ordnet die
gemeldete Kennung zu. Reihenfolge (Entscheidung H): **erst** die Konfiguration veröffentlichen (PUBACK),
**danach** ``…/ack``. Ist die Kennung schon mit einem anderen Ziel zugeordnet, fragt das Backend nach
(Ereignis ``rueckfrage`` und HA-Benachrichtigung ``persistent_notification``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any


from .const import (
    LERN_BEFEHL_TTL_S,
    LERN_ABBRUCH_TTL_S,
    LERN_FRIST_S,
    LERN_KEIN_STATUS_S,
    LERN_RUECKFRAGE_MIN_S,
    TOBIE_NAME_MAX,
)
from .fehler import TobiboxFehler
from .media import name_pruefen
from .util import iso, jetzt, parse_iso

if TYPE_CHECKING:
    from .hub import Hub

_LOGGER = logging.getLogger(__name__)

ENDE_ZUSTAENDE = ("zugeordnet", "abgelehnt", "abgebrochen", "abgelaufen", "box_lehnt_ab")


@dataclass
class Vorgang:
    befehl_id: str
    box: str
    ziel: dict[str, Any]
    name: str | None
    beginn: datetime
    frist_bis: datetime
    zustand: str = "wartet"
    lernmodus_gesehen: bool = False
    uid: str | None = None
    bisher: dict[str, Any] | None = None
    rueckfrage_bis: datetime | None = None
    grund: str | None = None
    text: str | None = None
    #: die Meldung der Box (``zuletzt``, ``art``), sobald sie eingetroffen ist
    meldung: dict[str, Any] | None = None
    #: die Zuordnung ist gespeichert, aber das ``ack`` wartet auf den PUBACK der Konfiguration
    ack_offen: bool = False
    ack_grund: str | None = None
    verworfen: bool = False
    #: Aktion ohne Seite: ``True`` überschreibt ohne Rückfrage, ``False`` lehnt ab; ``None`` = die Seite fragt
    auto_ueberschreiben: bool | None = None
    timer: list[Any] = field(default_factory=list)

    @property
    def ende(self) -> bool:
        return self.zustand in ENDE_ZUSTAENDE

    def zu_daten(self) -> dict[str, Any]:
        return {
            "box": self.box,
            "befehl_id": self.befehl_id,
            "zustand": self.zustand,
            "ziel": self.ziel,
            "beginn": iso(self.beginn),
            "frist_bis": iso(self.frist_bis),
            "rueckfrage_bis": iso(self.rueckfrage_bis) if self.rueckfrage_bis else None,
            "uid": self.uid,
            "bisher": self.bisher,
            "grund": self.grund,
            "text": self.text,
        }


def _gleiches_ziel(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (a.get("typ"), a.get("serie"), a.get("folge"), a.get("aktion")) == (
        b.get("typ"),
        b.get("serie"),
        b.get("folge"),
        b.get("aktion"),
    )


class Lernmodus:
    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self.vorgaenge: dict[str, Vorgang] = {}
        #: zuletzt beendete Vorgänge im Arbeitsspeicher (späte Meldungen bis ``frist_bis``, wiederholte Zustellung)
        self.beendet: dict[str, Vorgang] = {}

    # --- Hilfen -----------------------------------------------------------------------

    def offener_vorgang(self, box: str) -> Vorgang | None:
        v = self.vorgaenge.get(box)
        return v if v is not None and not v.ende else None

    def zu_snapshot(self) -> list[dict[str, Any]]:
        return [v.zu_daten() for v in self.vorgaenge.values() if not v.ende]

    def _melde(self, v: Vorgang) -> None:
        self.hub.emit("lernmodus", "zustand", v.zu_daten())

    def _timer(self, v: Vorgang, wann: datetime, fn) -> None:
        delay = max(0.0, (wann - jetzt()).total_seconds())

        async def lauf(_now: Any) -> None:
            await fn(v)

        v.timer.append(self.hub.plane(delay, lauf))

    def _timer_loeschen(self, v: Vorgang) -> None:
        for abbruch in v.timer:
            abbruch()
        v.timer.clear()

    def _notification_id(self, v: Vorgang) -> str:
        return f"tobibox_rueckfrage_{v.befehl_id}"

    def _ende(self, v: Vorgang, zustand: str, grund: str | None = None, text: str | None = None) -> None:
        """Beendet den Vorgang mit genau einem Endzustand (Vertrag W, 6.2 Punkt 6)."""
        if v.ende:
            return
        v.zustand = zustand
        v.grund = grund
        v.text = text or v.text
        self._timer_loeschen(v)
        v.ack_offen = False
        self.hub.benachrichtigung_entfernen(self._notification_id(v))
        # Ein beendeter Vorgang verschwindet aus ``boxen/list``; er bleibt für späte Meldungen in ``beendet``
        if self.vorgaenge.get(v.box) is v:
            del self.vorgaenge[v.box]
        self.beendet[v.befehl_id] = v
        while len(self.beendet) > 50:
            self.beendet.pop(next(iter(self.beendet)))
        self.hub.store.lern_verlauf_hinzu(
            {
                "befehl_id": v.befehl_id,
                "box": v.box,
                "ziel": v.ziel,
                "name": v.name,
                "ergebnis": zustand,
                "uid": v.uid,
                "grund": grund,
                "ack_grund": v.ack_grund,
                "beginn": iso(v.beginn),
                "frist_bis": iso(v.frist_bis),
                "zuletzt": (v.meldung or {}).get("zuletzt"),
                "art": (v.meldung or {}).get("art"),
            }
        )
        self.hub.box_geaendert(v.box)
        self._melde(v)

    # --- Start ----------------------------------------------------------------------------

    async def _pruefe_ziel(self, ziel: dict[str, Any]) -> dict[str, Any]:
        """Aktionskarten gehen nicht über den Lernmodus; sonst gilt dieselbe Prüfung wie bei ``zuordnung/set``."""
        if not isinstance(ziel, dict) or ziel.get("typ") not in ("serie", "folge"):
            raise TobiboxFehler("ziel_ungueltig")
        return await self.hub.pruefe_ziel(ziel)

    async def start(
        self, box: str, ziel: dict[str, Any], name: Any = None, auto_ueberschreiben: bool | None = None
    ) -> dict[str, Any]:
        mqtt = self.hub.mqtt
        z = mqtt.boxen.get(box)
        if z is None:
            raise TobiboxFehler("box_unbekannt")
        ziel = await self._pruefe_ziel(ziel)
        name_neu: str | None = None
        if name is not None:
            name_neu = name_pruefen(name, TOBIE_NAME_MAX)
        if self.hub.store.zustand != "ok":
            raise TobiboxFehler("konfig_nicht_bereit")
        offen = self.offener_vorgang(box)
        if offen is not None:
            if _gleiches_ziel(offen.ziel, ziel):
                return self._start_antwort(offen)
            raise TobiboxFehler("lernmodus_laeuft")
        if z.online is not True:
            raise TobiboxFehler("box_offline")
        befehl_id = await mqtt.sende_befehl(box, "lernen", LERN_BEFEHL_TTL_S)
        beginn = jetzt()
        v = Vorgang(
            befehl_id, box, ziel, name_neu, beginn, beginn + timedelta(seconds=LERN_FRIST_S),
            auto_ueberschreiben=auto_ueberschreiben,
        )
        self.vorgaenge[box] = v
        self._timer(v, beginn + timedelta(seconds=LERN_KEIN_STATUS_S), self._timer_kein_status)
        self._timer(v, v.frist_bis, self._timer_frist)
        self.hub.box_geaendert(box)
        self._melde(v)
        return self._start_antwort(v)

    @staticmethod
    def _start_antwort(v: Vorgang) -> dict[str, Any]:
        return {
            "befehl_id": v.befehl_id,
            "box": v.box,
            "ziel": v.ziel,
            "beginn": iso(v.beginn),
            "frist_bis": iso(v.frist_bis),
        }

    # --- Zeitgeber ------------------------------------------------------------------------------

    async def _timer_kein_status(self, v: Vorgang) -> None:
        if v.zustand == "wartet" and v.meldung is None and not v.lernmodus_gesehen and not v.ende:
            self._ende(v, "abgelaufen", "kein_status", self.hub.t("lernmodus_abgelaufen"))

    async def _timer_frist(self, v: Vorgang) -> None:
        if v.ende:
            return
        if v.ack_offen:
            # Ohne PUBACK bis zur Frist: abgelehnt (Vertrag W, 6.2 Punkt 4)
            await self._ack(v, "abgelehnt")
            self._ende(v, "abgelehnt", "abgelaufen", self.hub.t("lernmodus_abgelehnt_abgelaufen"))
        elif v.zustand == "wartet" and v.meldung is None:
            self._ende(v, "abgelaufen", "frist", self.hub.t("lernmodus_abgelaufen"))

    async def _timer_rueckfrage(self, v: Vorgang) -> None:
        if v.zustand != "rueckfrage":
            return
        await self._ack(v, "abgelehnt")
        self._ende(v, "abgelehnt", "abgelaufen", self.hub.t("lernmodus_rueckfrage_abgelaufen"))

    # --- Status und Ablehnung durch die Box --------------------------------------------------------

    def on_status(self, box: str, status: dict[str, Any]) -> None:
        v = self.vorgaenge.get(box)
        if v is None or v.ende or v.zustand != "wartet" or v.meldung is not None:
            return
        if status.get("lernmodus") is True:
            v.lernmodus_gesehen = True
        elif status.get("lernmodus") is False and v.lernmodus_gesehen:
            self._ende(v, "abgelaufen", "box_beendet", self.hub.t("lernmodus_abgelaufen"))

    def on_befehl_abgelehnt(self, box: str, befehl_id: Any, grund: Any) -> None:
        v = self.vorgaenge.get(box)
        if v is None or v.ende or (befehl_id and v.befehl_id != befehl_id):
            return
        grund = grund if grund in ("bedingung", "zeit_unsicher") else "bedingung"
        text = self.hub.t("lernmodus_box_lehnt_ab_zeit" if grund == "zeit_unsicher" else "lernmodus_box_lehnt_ab")
        self._ende(v, "box_lehnt_ab", grund, text)

    # --- Meldung der Box (art="gelernt") ----------------------------------------------------------------

    async def _ack(self, v: Vorgang, grund: str) -> bool:
        if v.meldung is None or v.uid is None:
            return False
        v.ack_grund = grund
        return await self.hub.mqtt.sende_ack(v.box, v.uid, v.meldung["zuletzt"], v.meldung["art"], grund)

    async def on_gelernt(self, box: str, uid: str, daten: dict[str, Any]) -> None:
        """Eine Kennung ist als ``gelernt`` gemeldet worden (Vertrag W, 6.2 Punkt 3)."""
        mqtt = self.hub.mqtt
        zuletzt, art = daten["zuletzt"], daten["art"]
        befehl_id = daten.get("befehl_id")
        v = self.beendet.get(befehl_id) or next(
            (x for x in self.vorgaenge.values() if x.befehl_id == befehl_id), None
        ) if befehl_id else None
        if v is None:
            await self._ohne_vorgang(box, uid, daten)
            return
        # doppelte Zustellung derselben Meldung
        if v.meldung is not None and v.meldung.get("zuletzt") == zuletzt:
            if v.zustand == "rueckfrage" or v.ack_offen:
                return
            if v.ende and v.ack_grund:
                await self._wiederhole_ack(v.box, uid, daten, v.ack_grund)
            return
        if v.verworfen or v.zustand in ("abgebrochen", "box_lehnt_ab", "zugeordnet", "abgelehnt"):
            await mqtt.sende_ack(box, uid, zuletzt, art, "abgelehnt")
            return
        jetzt_ = jetzt()
        if jetzt_ > v.frist_bis:
            if not v.ende:
                self._ende(v, "abgelaufen", "frist", self.hub.t("lernmodus_abgelaufen"))
            await mqtt.sende_ack(box, uid, zuletzt, art, "abgelehnt")
            return
        # späte Meldung eines schon abgelaufenen Vorgangs: bis ``frist_bis`` noch annehmen
        if v.ende:
            v.zustand = "wartet"
            v.grund = None
            self.beendet.pop(v.befehl_id, None)
            self.vorgaenge[box] = v
            self._timer(v, v.frist_bis, self._timer_frist)
        v.uid = uid
        v.meldung = {"zuletzt": zuletzt, "art": art}
        if self.hub.store.zustand != "ok" or self.hub.store.konfig is None:
            await self._ack(v, "abgelehnt")
            self._ende(v, "abgelehnt", "konfig_nicht_bereit", self.hub.t("lernmodus_konfig_nicht_bereit"))
            return
        bestehend = self.hub.store.konfig["zuordnungen"].get(uid)
        if bestehend is None:
            await self._zuordnen(v)
            return
        gleich = _gleiches_ziel(bestehend["ziel"], v.ziel) and (v.name is None or bestehend.get("name") == v.name)
        if gleich:
            await self._ack(v, "abgelehnt")  # die Box spielt das bestehende (gleiche) Ziel ohne 10 s Stille
            self._ende(v, "zugeordnet", "unveraendert", self.hub.t("lernmodus_unveraendert"))
            return
        v.bisher = bestehend["ziel"]
        if v.auto_ueberschreiben is not None:  # Aktion ohne Seite (Vertrag W, Abschnitt 1)
            if v.auto_ueberschreiben:
                await self._zuordnen(v)
            else:
                await self._ack(v, "abgelehnt")
                self._ende(v, "abgelehnt", "nutzer", self.hub.t("lernmodus_abgelehnt_nutzer"))
            return
        v.zustand = "rueckfrage"
        v.rueckfrage_bis = max(v.frist_bis, jetzt_ + timedelta(seconds=LERN_RUECKFRAGE_MIN_S))
        v.text = self.hub.t("lernmodus_rueckfrage")
        self._timer_loeschen(v)
        self._timer(v, v.rueckfrage_bis, self._timer_rueckfrage)
        self.hub.benachrichtige(
            self._notification_id(v),
            "benachrichtigung_rueckfrage_titel",
            "benachrichtigung_rueckfrage",
            uid=uid,
            name=bestehend.get("name") or uid,
            bisher=self.hub.ziel_text(bestehend["ziel"]),
            neu=self.hub.ziel_text(v.ziel),
        )
        self.hub.box_geaendert(box)
        self._melde(v)

    async def _ohne_vorgang(self, box: str, uid: str, daten: dict[str, Any]) -> None:
        """Kein Vorgang im Arbeitsspeicher: Verlauf im HA-Speicher prüfen (nach einem Neustart, Vertrag W, 6.2)."""
        zuletzt, art = daten["zuletzt"], daten["art"]
        eintrag = next((e for e in self.hub.store.lern_verlauf if e.get("befehl_id") == daten.get("befehl_id")), None)
        if eintrag is None or not eintrag.get("ack_grund"):
            await self.hub.mqtt.sende_ack(box, uid, zuletzt, art, "abgelehnt")
            return
        await self._wiederhole_ack(box, uid, daten, eintrag["ack_grund"])

    async def _wiederhole_ack(self, box: str, uid: str, daten: dict[str, Any], ack_grund: str) -> None:
        if ack_grund == "zugeordnet":
            # sicherstellen, dass die aktuelle Konfiguration veröffentlicht ist (PUBACK), dann erst das ack
            if not await self.hub.stelle_veroeffentlicht_sicher():
                return
        await self.hub.mqtt.sende_ack(box, uid, daten["zuletzt"], daten["art"], ack_grund)

    # --- Zuordnen -------------------------------------------------------------------------------------

    async def _zuordnen(self, v: Vorgang) -> None:
        hub = self.hub
        uid = v.uid
        assert uid is not None
        # Ziel muss noch existieren
        info = hub.medien.serien.get(v.ziel["serie"])
        if info is None or (v.ziel["typ"] == "folge" and v.ziel["folge"] not in info.serie.folgen):
            await self._ack(v, "abgelehnt")
            self._ende(v, "abgelehnt", "ziel_fehlt", hub.t("lernmodus_ziel_fehlt"))
            return

        def setze(k: dict[str, Any]) -> None:
            alt = k["zuordnungen"].get(uid) or {}
            eintrag: dict[str, Any] = {"ziel": dict(v.ziel)}
            name = v.name if v.name is not None else alt.get("name")
            if name:
                eintrag["name"] = name
            k["zuordnungen"][uid] = eintrag

        try:
            erg = await hub.aendere_konfig(setze)
        except TobiboxFehler as err:
            grund = err.code if err.code in ("konfig_zu_gross", "konfig_nicht_bereit") else "speicherfehler"
            await self._ack(v, "abgelehnt")
            self._ende(v, "abgelehnt", grund, hub.t(f"lernmodus_{grund}"))
            return
        except Exception:
            _LOGGER.exception("Lernmodus: Konfiguration nicht gespeichert")
            await self._ack(v, "abgelehnt")
            self._ende(v, "abgelehnt", "speicherfehler", hub.t("lernmodus_speicherfehler"))
            return
        hub.kennung_zugeordnet(uid)
        v.zustand = "wartet"
        v.rueckfrage_bis = None
        if erg["veroeffentlicht"] and await self._ack(v, "zugeordnet"):
            self._ende(v, "zugeordnet", None, hub.t("lernmodus_zugeordnet"))
            return
        # Ohne PUBACK kein ack: der Vorgang bleibt ``wartet`` mit gespeicherter Zuordnung (nachholen beim Wiederverbinden)
        v.ack_offen = True
        v.text = hub.t("lernmodus_wartet_auf_broker")
        self._melde(v)

    async def nachholen(self) -> None:
        """Beim Wiederverbinden: offene ``ack`` nach der Veröffentlichung nachholen (Vertrag W, 13.6)."""
        for v in list(self.vorgaenge.values()):
            if not v.ack_offen or v.ende:
                continue
            if jetzt() > v.frist_bis:
                await self._ack(v, "abgelehnt")
                self._ende(v, "abgelehnt", "abgelaufen", self.hub.t("lernmodus_abgelehnt_abgelaufen"))
                continue
            if await self.hub.stelle_veroeffentlicht_sicher() and await self._ack(v, "zugeordnet"):
                self._ende(v, "zugeordnet", None, self.hub.t("lernmodus_zugeordnet"))

    # --- Antwort auf die Rückfrage, Abbrechen --------------------------------------------------------

    async def antwort(self, befehl_id: str, ueberschreiben: bool) -> dict[str, Any]:
        v = next((x for x in self.vorgaenge.values() if x.befehl_id == befehl_id), None)
        if v is None or v.ende or v.zustand != "rueckfrage":
            alt = self.beendet.get(befehl_id)
            if alt is not None and alt.grund == "abgelaufen" and alt.zustand == "abgelehnt" and alt.bisher is not None:
                raise TobiboxFehler("rueckfrage_abgelaufen")
            raise TobiboxFehler("kein_lernmodus")
        if jetzt() > (v.rueckfrage_bis or v.frist_bis):
            await self._timer_rueckfrage(v)
            raise TobiboxFehler("rueckfrage_abgelaufen")
        self._timer_loeschen(v)
        if not ueberschreiben:
            await self._ack(v, "abgelehnt")
            self._ende(v, "abgelehnt", "nutzer", self.hub.t("lernmodus_abgelehnt_nutzer"))
            return {"zustand": "abgelehnt", "konfig": self.hub.konfig_stand()}
        await self._zuordnen(v)
        zustand = "zugeordnet" if (v.zustand == "zugeordnet" or v.ack_offen) else "abgelehnt"
        return {"zustand": zustand, "konfig": self.hub.konfig_stand()}

    async def abbrechen(self, box: str) -> bool:
        mqtt = self.hub.mqtt
        if box not in mqtt.boxen:
            raise TobiboxFehler("box_unbekannt")
        if not mqtt.ist_verbunden():
            raise TobiboxFehler("mqtt_nicht_verbunden")
        v = self.offener_vorgang(box)
        offen = v is not None
        if v is not None:
            v.verworfen = True
            if v.zustand == "rueckfrage" or v.ack_offen:
                await self._ack(v, "abgelehnt")  # sofort, die Box wartet nicht auf die Frist (W-24)
            self._ende(v, "abgebrochen", None, self.hub.t("lernmodus_abgebrochen"))
        await mqtt.sende_befehl(box, "lernen_abbrechen", LERN_ABBRUCH_TTL_S)
        return offen
