"""``tobibox.toml`` laden und prüfen (``tomllib``).

Eine Konfigurationsdatei je Gerät (Design, „Mac und Pi“). Es gibt keine Abfrage
„bin ich am Mac?“: Unterschiede stehen nur in den Werten. Zugangsdaten
(MQTT-Passwort) kommen erst in Stufe 3 und liegen nur in dieser Datei, nie im Repo.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import events as ev
from .eventlog import EBENEN, logge


class KonfigFehler(ValueError):
    """``tobibox.toml`` fehlt, ist kein gültiges TOML oder hat ungültige Werte."""


@dataclass(frozen=True, slots=True)
class Pfade:
    zustand: Path
    medien: Path


#: ``leser.geraet = "sim"``: kein Leser, die Leser-Ereignisse kommen aus ``sim`` (Prüfpunkt „Leser“: ``simulation``)
LESER_SIMULATION = "sim"


@dataclass(frozen=True, slots=True)
class LeserKonfig:
    geraet: str = "/dev/cu.usbmodem*"

    @property
    def simulation(self) -> bool:
        return self.geraet == LESER_SIMULATION


@dataclass(frozen=True, slots=True)
class MpdKonfig:
    host: str = "localhost"
    port: int = 6600


@dataclass(frozen=True, slots=True)
class LautstaerkeKonfig:
    max: int = 50  # globale Obergrenze
    start: int = 20
    kopfhoerer: int = 30


#: Mac-Vorgabe; auf dem Pi ["aplay", "-q", "{datei}"] (optional "-D", "<Gerät>").
#: Nötig ist nur {datei}: die Töne werden in Python auf den Pegel skaliert (sounds.py).
#: Optional weiter ersetzt: {pegel} (0 bis 100), {lautstaerke} (0.0 bis 1.0).
STANDARD_TON_KOMMANDO: tuple[str, ...] = ("afplay", "{datei}")
STANDARD_TON_KOMMANDO_PI: tuple[str, ...] = ("aplay", "-q", "{datei}")


#: Kennlinien: wie MPD eine Lautstärke in Prozent in eine Verstärkung umsetzt (Entscheidung J, 09.11.).
#: ``mpd_software``: Software-Mixer von MPD (Mac, ``mixer_type "software"``); ``alsa_softvol``: ALSA-``softvol``
#: über den ALSA-Mixer von MPD (Pi). Quellen und Formeln: ``core-interface.md``, 8.1.
KENNLINIE_MPD_SOFTWARE = "mpd_software"
KENNLINIE_ALSA_SOFTVOL = "alsa_softvol"
KENNLINIEN = (KENNLINIE_MPD_SOFTWARE, KENNLINIE_ALSA_SOFTVOL)
#: Bereich min_dB bis max_dB des ALSA-``softvol`` in dB; die Vorgabe von ALSA ist -51 dB bis 0 dB.
STANDARD_SOFTVOL_BEREICH_DB = 51.0


@dataclass(frozen=True, slots=True)
class TonKonfig:
    kommando: tuple[str, ...] = STANDARD_TON_KOMMANDO
    ordner: Path | None = None  # None: ``box/sounds`` neben dem Quellbaum
    kennlinie: str = KENNLINIE_MPD_SOFTWARE  # Mac; Pi: "alsa_softvol"
    softvol_bereich_db: float = STANDARD_SOFTVOL_BEREICH_DB  # nur bei "alsa_softvol": max_dB - min_dB


@dataclass(frozen=True, slots=True)
class ProtokollKonfig:
    ziel: str = "stdout"  # "stdout" (Pi) oder "datei" (Mac)
    datei: Path | None = None
    ebene: str = "INFO"
    max_bytes: int = 1_000_000
    anzahl: int = 5


# --- [sync] (AP 3.4): Medien-Sync per rsync-Daemon des QNAP ------------------------------------------
@dataclass(frozen=True, slots=True)
class SyncKonfig:
    """``[sync]``: Ort und Zugang des rsync-Daemons (Modul ``medien``, nur lesend). Ohne den Abschnitt: kein Sync.

    Das Passwort steht nie in der Datei: entweder ``passwort_datei`` (Pfad, Rechte 600) oder
    ``passwort_umgebung`` (Name einer Umgebungsvariable).
    """

    host: str
    port: int = 873
    modul: str = "medien"
    benutzer: str | None = None
    passwort_datei: Path | None = None
    passwort_umgebung: str | None = None
    partial_dir: Path | None = None  # None: ``<Medienordner>/../.rsync-partial`` (gleiches Dateisystem)
    intervall_s: int = 3600
    reserve_mb: int = 200  # so viel bleibt nach dem Sync mindestens frei


_SYNC_SCHLUESSEL = {
    "host", "port", "modul", "benutzer", "passwort_datei", "passwort_umgebung", "partial_dir", "intervall_s", "reserve_mb",
}
_SYNC_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _pruefe_sync(roh: dict[str, Any], basis: Path, medien: Path) -> SyncKonfig | None:
    a = roh.get("sync")
    if a is None:
        return None
    if not isinstance(a, dict):
        raise KonfigFehler("[sync] muss ein Abschnitt sein")
    if "passwort" in a:
        raise KonfigFehler("[sync] kein Passwort in der Datei: 'passwort_datei' (Pfad) oder 'passwort_umgebung' nutzen")
    unbekannt = set(a) - _SYNC_SCHLUESSEL
    if unbekannt:
        logge("config", "WARNING", "unbekannte_schluessel", "ignoriert", daten={"abschnitt": "sync", "schluessel": sorted(unbekannt)})
    namen = {}
    for schluessel, vorgabe in (("host", None), ("modul", "medien"), ("benutzer", None)):
        wert = _text(a, "sync", schluessel, vorgabe)
        if wert is not None and not _SYNC_NAME.match(wert):
            raise KonfigFehler(f"[sync] {schluessel} darf nur Buchstaben, Ziffern, Punkt, Minus und Unterstrich enthalten")
        namen[schluessel] = wert
    if namen["host"] is None:
        raise KonfigFehler("[sync] braucht 'host' (Name oder Tailscale-Adresse des QNAP)")
    datei = _text(a, "sync", "passwort_datei", None)
    umgebung = _text(a, "sync", "passwort_umgebung", None)
    if umgebung is not None and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", umgebung):
        raise KonfigFehler("[sync] passwort_umgebung muss ein Name einer Umgebungsvariable sein")
    if datei is not None and umgebung is not None:
        raise KonfigFehler("[sync] 'passwort_datei' und 'passwort_umgebung' nicht zusammen")
    if namen["benutzer"] is None and (datei is not None or umgebung is not None):
        raise KonfigFehler("[sync] ein Passwort braucht auch 'benutzer'")
    if namen["benutzer"] is not None and datei is None and umgebung is None:
        raise KonfigFehler("[sync] 'benutzer' braucht 'passwort_datei' oder 'passwort_umgebung'")
    partial = _text(a, "sync", "partial_dir", None)
    partial_pfad = _pfad(partial, basis) if partial else None
    pruef = partial_pfad if partial_pfad is not None else medien.parent / ".rsync-partial"
    ist_medien = pruef.resolve() == medien.resolve()
    if ist_medien or medien.resolve() in pruef.resolve().parents:
        raise KonfigFehler("[sync] partial_dir muss außerhalb des Medienordners liegen")
    return SyncKonfig(
        host=namen["host"],
        port=_ganz(a, "sync", "port", 873, 1, 65535),
        modul=namen["modul"] or "medien",
        benutzer=namen["benutzer"],
        passwort_datei=_pfad(datei, basis) if datei else None,
        passwort_umgebung=umgebung,
        partial_dir=partial_pfad,
        intervall_s=_ganz(a, "sync", "intervall_s", 3600, 60, 86400),
        reserve_mb=_ganz(a, "sync", "reserve_mb", 200, 0, 1_000_000),
    )
# --- Ende [sync] -------------------------------------------------------------------------------------

# --- [mqtt], [netz], [strom] (AP 3.3): Home Assistant, Netz-Klasse, Strom -------------------------------
BOX_ID_MUSTER = re.compile(r"^[a-z0-9][a-z0-9_-]{1,23}$")  # mqtt-v1.md, Abschnitt 1
_HOST_MUSTER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


@dataclass(frozen=True, slots=True)
class MqttKonfig:
    """``[mqtt]``: Broker in Home Assistant und eigenes Konto der Box. Ohne den Abschnitt: kein HA.

    Das Konto heißt wie die Box (``box_id``). Das Passwort steht nur in der lokalen ``tobibox.toml`` (gitignored).
    """

    box_id: str
    host: str
    port: int = 1883
    benutzer: str = ""  # leer: wie box_id
    passwort: str | None = field(default=None, repr=False)
    anzeigename: str = ""  # leer: wie box_id

    def __post_init__(self) -> None:
        if not self.benutzer:
            object.__setattr__(self, "benutzer", self.box_id)
        if not self.anzeigename:
            object.__setattr__(self, "anzeigename", self.box_id)


#: ``[netz] quelle``: ``sim`` (Mac, Test: Netz und Zeit werden vorgegeben) oder ``networkmanager`` (Pi)
NETZ_QUELLEN = ("sim", "networkmanager")


@dataclass(frozen=True, slots=True)
class NetzKonfig:
    """``[netz]``: Namen (SSIDs) von Heim-WLAN und Handy-Hotspot. Sie stehen nie im Repo."""

    quelle: str = "sim"
    heim_ssid: str | None = None
    hotspot_ssid: str | None = None
    nas_host: str | None = None  # ``home`` gilt nur, wenn der NAS erreichbar ist (ohne Eintrag: Heim-SSID genügt)
    nas_port: int = 873
    intervall_s: int = 10

    @property
    def simulation(self) -> bool:
        return self.quelle == "sim"


STROM_QUELLEN = ("sim", "pisugar")
STANDARD_ABSCHALT_KOMMANDO: tuple[str, ...] = ("systemctl", "poweroff")


@dataclass(frozen=True, slots=True)
class StromKonfig:
    """``[strom]``: Akku, Lader, Taste und Uhr des PiSugar (``pisugar-server``) oder Simulation."""

    quelle: str = "sim"
    pisugar_host: str = "127.0.0.1"
    pisugar_port: int = 8423
    tiefstand_prozent: int = 5
    warnung_prozent: int = 10  # Entscheidung Z, zweite Stufe (11.11.): einmal „Mein Akku wird leer“; muss größer als ``tiefstand_prozent`` sein
    intervall_s: int = 10
    abschalt_kommando: tuple[str, ...] = STANDARD_ABSCHALT_KOMMANDO
    #: Befehl an den ``pisugar-server``, der die Taste meldet (B2). ``None``: aus. **Am Pi zu prüfen**, siehe ``power.taste_lauf``.
    taste_befehl: str | None = None
    taste_intervall_s: float = 0.5

    @property
    def simulation(self) -> bool:
        return self.quelle == "sim"


_MQTT_SCHLUESSEL = {"box_id", "host", "port", "benutzer", "passwort", "anzeigename"}
_NETZ_SCHLUESSEL = {"quelle", "heim_ssid", "hotspot_ssid", "nas_host", "nas_port", "intervall_s"}
_STROM_SCHLUESSEL = {
    "quelle", "pisugar_host", "pisugar_port", "tiefstand_prozent", "warnung_prozent", "intervall_s", "abschalt_kommando",
    "taste_befehl", "taste_intervall_s",
}


def _pruefe_mqtt(roh: dict[str, Any]) -> MqttKonfig | None:
    a = roh.get("mqtt")
    if a is None:
        return None
    a = _abschnitt(roh, "mqtt")
    box_id = _text(a, "mqtt", "box_id", None)
    if box_id is None or not BOX_ID_MUSTER.match(box_id):
        raise KonfigFehler("[mqtt] box_id fehlt oder passt nicht zu [a-z0-9][a-z0-9_-]{1,23} (z. B. 'box1')")
    host = _text(a, "mqtt", "host", None)
    if host is None or not _HOST_MUSTER.match(host):
        raise KonfigFehler("[mqtt] host fehlt (Name oder Tailscale-Adresse des Brokers)")
    benutzer = _text(a, "mqtt", "benutzer", box_id) or box_id
    if benutzer != box_id:
        # mqtt-v1.md, Abschnitt 1: Der Benutzername ist der Box-Name (die Rechte im Broker hängen daran).
        raise KonfigFehler("[mqtt] benutzer muss gleich box_id sein (ein Konto je Box)")
    anzeige = _text(a, "mqtt", "anzeigename", box_id) or box_id
    if len(anzeige) > 40 or any(ord(c) < 32 for c in anzeige):
        raise KonfigFehler("[mqtt] anzeigename darf höchstens 40 Zeichen haben und keine Steuerzeichen")
    return MqttKonfig(
        box_id=box_id,
        host=host,
        port=_ganz(a, "mqtt", "port", 1883, 1, 65535),
        benutzer=benutzer,
        passwort=_text(a, "mqtt", "passwort", None),
        anzeigename=anzeige,
    )


def _pruefe_ssid(a: dict[str, Any], schluessel: str) -> str | None:
    wert = _text(a, "netz", schluessel, None)
    if wert is not None and len(wert.encode("utf-8")) > 32:
        raise KonfigFehler(f"[netz] {schluessel} darf höchstens 32 Bytes lang sein (WLAN-Name)")
    return wert


def _pruefe_netz(roh: dict[str, Any]) -> NetzKonfig | None:
    if roh.get("netz") is None:
        return None
    a = _abschnitt(roh, "netz")
    quelle = _text(a, "netz", "quelle", "sim")
    if quelle not in NETZ_QUELLEN:
        raise KonfigFehler(f"[netz] quelle muss {' oder '.join(repr(q) for q in NETZ_QUELLEN)} sein")
    heim, hotspot = _pruefe_ssid(a, "heim_ssid"), _pruefe_ssid(a, "hotspot_ssid")
    if heim is not None and heim == hotspot:
        raise KonfigFehler("[netz] heim_ssid und hotspot_ssid müssen verschieden sein")
    if quelle == "networkmanager" and heim is None and hotspot is None:
        raise KonfigFehler("[netz] quelle='networkmanager' braucht 'heim_ssid' und/oder 'hotspot_ssid'")
    nas = _text(a, "netz", "nas_host", None)
    if nas is not None and not _HOST_MUSTER.match(nas):
        raise KonfigFehler("[netz] nas_host muss ein Name oder eine Adresse sein")
    return NetzKonfig(
        quelle=quelle or "sim",
        heim_ssid=heim,
        hotspot_ssid=hotspot,
        nas_host=nas,
        nas_port=_ganz(a, "netz", "nas_port", 873, 1, 65535),
        intervall_s=_ganz(a, "netz", "intervall_s", 10, 1, 3600),
    )


def _pruefe_strom(roh: dict[str, Any]) -> StromKonfig | None:
    if roh.get("strom") is None:
        return None
    a = _abschnitt(roh, "strom")
    quelle = _text(a, "strom", "quelle", "sim")
    if quelle not in STROM_QUELLEN:
        raise KonfigFehler(f"[strom] quelle muss {' oder '.join(repr(q) for q in STROM_QUELLEN)} sein")
    kommando = a.get("abschalt_kommando", list(STANDARD_ABSCHALT_KOMMANDO))
    if not isinstance(kommando, list) or not kommando or not all(isinstance(k, str) and k for k in kommando):
        raise KonfigFehler("[strom] abschalt_kommando muss eine nicht leere Liste von Texten sein")
    host = _text(a, "strom", "pisugar_host", "127.0.0.1")
    if host is None or not _HOST_MUSTER.match(host):
        raise KonfigFehler("[strom] pisugar_host muss ein Name oder eine Adresse sein")
    tiefstand = _ganz(a, "strom", "tiefstand_prozent", 5, 1, 50)
    warnung = _ganz(a, "strom", "warnung_prozent", 10, 1, 100)
    if warnung <= tiefstand:
        raise KonfigFehler(f"[strom] warnung_prozent ({warnung}) muss größer sein als tiefstand_prozent ({tiefstand})")
    return StromKonfig(
        quelle=quelle or "sim",
        pisugar_host=host,
        pisugar_port=_ganz(a, "strom", "pisugar_port", 8423, 1, 65535),
        tiefstand_prozent=tiefstand,
        warnung_prozent=warnung,
        intervall_s=_ganz(a, "strom", "intervall_s", 10, 1, 3600),
        abschalt_kommando=tuple(kommando),
        taste_befehl=_text(a, "strom", "taste_befehl", None),
        taste_intervall_s=_kommazahl(a, "strom", "taste_intervall_s", 0.5, 0.1, 60.0),
    )
# --- Ende [mqtt], [netz], [strom] ----------------------------------------------------------------------

# --- [kopfhoerer], [tasten] (AP 4.8): Buchse, Tasten und Drehregler; Vorgabe ``sim`` (Mac) -----------------
#: ``sim``: Mac und Test, die Eingänge kommen von ``tobibox sim``; ``gpio``: Pi, echte Pins (BCM-Nummern)
EINGANG_QUELLEN = ("sim", "gpio")
GPIO_PIN_MAX = 27  # BCM 0 bis 27 am 40-poligen Pi-Header


@dataclass(frozen=True, slots=True)
class KopfhoererKonfig:
    """``[kopfhoerer]``: Schaltkontakt der Klinkenbuchse. Die Pin-Nummer ist noch nicht bekannt, deshalb ohne Vorgabe."""

    quelle: str = "sim"
    gpio_pin: int | None = None  # BCM; bei ``gpio`` Pflicht
    aktiv_niedrig: bool = True  # Stecker steckt = Pin niedrig (Kontakt nach Masse, Pull-up); auf dem Pi zu prüfen
    intervall_s: float = 0.2

    @property
    def simulation(self) -> bool:
        return self.quelle == "sim"


@dataclass(frozen=True, slots=True)
class TastenKonfig:
    """``[tasten]``: Vor, Zurück, Drehregler (A/B) und Hauptknopf. Die Pins sind noch nicht bekannt, deshalb ohne Vorgabe.

    ``pin_haupt`` ist optional: Der Hauptknopf kommt auf dem Pi über die Taste des PiSugar (``[strom]``).
    """

    quelle: str = "sim"
    pin_vor: int | None = None
    pin_zurueck: int | None = None
    pin_dreh_a: int | None = None
    pin_dreh_b: int | None = None
    pin_haupt: int | None = None
    lang_s: float = 1.5  # so lange gehalten = Hauptknopf lang

    @property
    def simulation(self) -> bool:
        return self.quelle == "sim"


_KOPFHOERER_SCHLUESSEL = {"quelle", "gpio_pin", "aktiv_niedrig", "intervall_s"}
_TASTEN_SCHLUESSEL = {"quelle", "pin_vor", "pin_zurueck", "pin_dreh_a", "pin_dreh_b", "pin_haupt", "lang_s"}
_TASTEN_PFLICHT_PINS = ("pin_vor", "pin_zurueck", "pin_dreh_a", "pin_dreh_b")


def _kommazahl(a: dict[str, Any], name: str, schluessel: str, vorgabe: float, lo: float, hi: float) -> float:
    wert = a.get(schluessel, vorgabe)
    if isinstance(wert, bool) or not isinstance(wert, (int, float)) or not lo <= wert <= hi:
        raise KonfigFehler(f"[{name}] {schluessel} muss eine Zahl von {lo:g} bis {hi:g} sein")
    return float(wert)


def _pin(a: dict[str, Any], name: str, schluessel: str) -> int | None:
    if schluessel not in a:
        return None
    return _ganz(a, name, schluessel, 0, 0, GPIO_PIN_MAX)


def _quelle(a: dict[str, Any], name: str) -> str:
    quelle = _text(a, name, "quelle", "sim")
    if quelle not in EINGANG_QUELLEN:
        raise KonfigFehler(f"[{name}] quelle muss {' oder '.join(repr(q) for q in EINGANG_QUELLEN)} sein")
    return quelle or "sim"


def _pruefe_kopfhoerer(roh: dict[str, Any]) -> KopfhoererKonfig:
    a = _abschnitt(roh, "kopfhoerer")
    quelle = _quelle(a, "kopfhoerer")
    pin = _pin(a, "kopfhoerer", "gpio_pin")
    if quelle == "gpio" and pin is None:
        raise KonfigFehler("[kopfhoerer] quelle='gpio' braucht 'gpio_pin' (BCM-Nummer des Schaltkontakts der Buchse)")
    aktiv = a.get("aktiv_niedrig", True)
    if not isinstance(aktiv, bool):
        raise KonfigFehler("[kopfhoerer] aktiv_niedrig muss true oder false sein")
    return KopfhoererKonfig(quelle, pin, aktiv, _kommazahl(a, "kopfhoerer", "intervall_s", 0.2, 0.05, 10.0))


def _pruefe_tasten(roh: dict[str, Any]) -> TastenKonfig:
    a = _abschnitt(roh, "tasten")
    quelle = _quelle(a, "tasten")
    pins = {k: _pin(a, "tasten", k) for k in (*_TASTEN_PFLICHT_PINS, "pin_haupt")}
    if quelle == "gpio":
        fehlt = [k for k in _TASTEN_PFLICHT_PINS if pins[k] is None]
        if fehlt:
            raise KonfigFehler(f"[tasten] quelle='gpio' braucht {', '.join(fehlt)} (BCM-Nummern)")
    belegt = [p for p in pins.values() if p is not None]
    if len(belegt) != len(set(belegt)):
        raise KonfigFehler("[tasten] jeder Pin darf nur einmal vorkommen")
    return TastenKonfig(quelle, **pins, lang_s=_kommazahl(a, "tasten", "lang_s", 1.5, 0.3, 10.0))  # type: ignore[arg-type]


def _pruefe_pins_gemeinsam(k: KopfhoererKonfig, t: TastenKonfig) -> None:
    if k.gpio_pin is not None and k.gpio_pin in (t.pin_vor, t.pin_zurueck, t.pin_dreh_a, t.pin_dreh_b, t.pin_haupt):
        raise KonfigFehler("[kopfhoerer] gpio_pin liegt auf einem Pin von [tasten]")
# --- Ende [kopfhoerer], [tasten] -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SimKonfig:
    """``[sim]``: ``erlauben = true`` lässt ``tobibox sim`` und die Oberfläche auch Eingänge bedienen, deren Quelle **nicht** ``sim`` ist
    (B9, 09.11.). Vorgabe ``false``: Am Pi wirken ``sim time``, ``key``, ``headphones`` usw. nicht auf echte Hardware und Uhr
    (Antwort ``quelle_nicht_sim``)."""

    erlauben: bool = False


@dataclass(frozen=True, slots=True)
class UhrKonfig:
    """``[uhr]``: Braucht die Systemuhr eine NTP-Synchronisierung, um als sicher zu gelten (B15)?

    ``None`` (Vorgabe, Schlüssel fehlt): Auf Linux (Pi) ja, am Mac nein. Gilt nur ohne ``[netz]`` und ``[strom]``; mit ihnen bewerten NTP
    und RTC die Uhr ohnehin. ``ntp_pflicht = false`` erzwingt die sichere Systemuhr (Entwicklung auf einem Linux-Rechner)."""

    ntp_pflicht: bool | None = None


@dataclass(frozen=True, slots=True)
class BoxKonfig:
    pfade: Pfade
    leser: LeserKonfig = field(default_factory=LeserKonfig)
    mpd: MpdKonfig = field(default_factory=MpdKonfig)
    lautstaerke: LautstaerkeKonfig = field(default_factory=LautstaerkeKonfig)
    protokoll: ProtokollKonfig = field(default_factory=ProtokollKonfig)
    toene: TonKonfig = field(default_factory=TonKonfig)
    sync: SyncKonfig | None = None  # [sync]; None: kein Medien-Sync
    mqtt: MqttKonfig | None = None  # [mqtt]; None: kein Home Assistant
    netz: NetzKonfig | None = None  # [netz]; None: keine Netz-Klasse
    strom: StromKonfig | None = None  # [strom]; None: keine Strom-Schnittstelle
    kopfhoerer: KopfhoererKonfig = field(default_factory=KopfhoererKonfig)  # [kopfhoerer]; Vorgabe sim
    tasten: TastenKonfig = field(default_factory=TastenKonfig)  # [tasten]; Vorgabe sim
    uhr: UhrKonfig = field(default_factory=UhrKonfig)  # [uhr]; Vorgabe: Linux braucht NTP, der Mac nicht
    sim: SimKonfig = field(default_factory=SimKonfig)  # [sim]; Vorgabe: nur Eingänge mit Quelle ``sim``

    def geraete_einstellungen(self) -> ev.GeraeteEinstellungen:
        """Das erste Ereignis des Kerns (``core-interface.md``, 3.3)."""
        v = self.lautstaerke
        return ev.GeraeteEinstellungen(v.max, v.start, v.kopfhoerer)


_BEKANNT = {
    "pfade": {"zustand", "medien"},
    "leser": {"geraet"},
    "mpd": {"host", "port"},
    "lautstaerke": {"max", "start", "kopfhoerer"},
    "protokoll": {"ziel", "datei", "ebene", "max_bytes", "anzahl"},
    "toene": {"kommando", "ordner", "kennlinie", "softvol_bereich_db"},
    "sync": _SYNC_SCHLUESSEL,
    "mqtt": _MQTT_SCHLUESSEL,
    "netz": _NETZ_SCHLUESSEL,
    "strom": _STROM_SCHLUESSEL,
    "kopfhoerer": _KOPFHOERER_SCHLUESSEL,
    "tasten": _TASTEN_SCHLUESSEL,
    "sim": {"erlauben"},
    "uhr": {"ntp_pflicht"},
}


def _abschnitt(roh: dict[str, Any], name: str, pflicht: bool = False) -> dict[str, Any]:
    wert = roh.get(name)
    if wert is None:
        if pflicht:
            raise KonfigFehler(f"Abschnitt [{name}] fehlt")
        return {}
    if not isinstance(wert, dict):
        raise KonfigFehler(f"[{name}] muss ein Abschnitt sein")
    unbekannt = set(wert) - _BEKANNT[name]
    if unbekannt:  # nur warnen: eine neuere Datei muss nach einem Update-Rückfall noch laden
        logge("config", "WARNING", "unbekannte_schluessel", "ignoriert",
              daten={"abschnitt": name, "schluessel": sorted(unbekannt)})
    return wert


def _ganz(a: dict[str, Any], name: str, schluessel: str, vorgabe: int, lo: int, hi: int) -> int:
    wert = a.get(schluessel, vorgabe)
    if isinstance(wert, bool) or not isinstance(wert, int) or not lo <= wert <= hi:
        raise KonfigFehler(f"[{name}] {schluessel} muss eine ganze Zahl von {lo} bis {hi} sein")
    return wert


def _text(a: dict[str, Any], name: str, schluessel: str, vorgabe: str | None) -> str | None:
    wert = a.get(schluessel, vorgabe)
    if wert is None:
        return None
    if not isinstance(wert, str) or not wert.strip():
        raise KonfigFehler(f"[{name}] {schluessel} muss ein nicht leerer Text sein")
    return wert


def _pfad(text: str, basis: Path) -> Path:
    p = Path(text).expanduser()
    return p if p.is_absolute() else basis / p


def pruefe(roh: dict[str, Any], basis: Path | None = None) -> BoxKonfig:
    """Rohe TOML-Daten prüfen; relative Pfade gelten ab ``basis`` (Ordner der Datei)."""
    basis = basis or Path.cwd()
    unbekannt = set(roh) - set(_BEKANNT)
    if unbekannt:
        logge("config", "WARNING", "unbekannte_abschnitte", "ignoriert", daten={"abschnitte": sorted(unbekannt)})

    p = _abschnitt(roh, "pfade", pflicht=True)
    zustand = _text(p, "pfade", "zustand", None)
    medien = _text(p, "pfade", "medien", None)
    if zustand is None or medien is None:
        raise KonfigFehler("[pfade] braucht 'zustand' und 'medien'")

    leser = _abschnitt(roh, "leser")
    mpd = _abschnitt(roh, "mpd")
    vol = _abschnitt(roh, "lautstaerke")
    prot = _abschnitt(roh, "protokoll")
    ton = _abschnitt(roh, "toene")
    kommando = ton.get("kommando", list(STANDARD_TON_KOMMANDO))
    if (
        not isinstance(kommando, list)
        or not kommando
        or not all(isinstance(k, str) and k for k in kommando)
    ):
        raise KonfigFehler("[toene] kommando muss eine nicht leere Liste von Texten sein")
    ton_ordner = _text(ton, "toene", "ordner", None)
    kennlinie = _text(ton, "toene", "kennlinie", KENNLINIE_MPD_SOFTWARE)
    if kennlinie not in KENNLINIEN:
        raise KonfigFehler(f"[toene] kennlinie muss {' oder '.join(repr(k) for k in KENNLINIEN)} sein")
    bereich = ton.get("softvol_bereich_db", STANDARD_SOFTVOL_BEREICH_DB)
    if isinstance(bereich, bool) or not isinstance(bereich, (int, float)) or not 1 <= bereich <= 120:
        raise KonfigFehler("[toene] softvol_bereich_db muss eine Zahl von 1 bis 120 sein")

    maximum = _ganz(vol, "lautstaerke", "max", 50, 0, 100)
    # Nur ``max`` gegeben: die Vorgaben werden auf ``max`` gekappt. Ausdrücklich
    # gesetzte Werte über ``max`` sind ein Fehler im Eintrag, kein stilles Kappen.
    v = LautstaerkeKonfig(
        max=maximum,
        start=_ganz(vol, "lautstaerke", "start", min(20, maximum), 0, 100),
        kopfhoerer=_ganz(vol, "lautstaerke", "kopfhoerer", min(30, maximum), 0, 100),
    )
    if v.start > v.max:
        raise KonfigFehler("[lautstaerke] start darf nicht über max liegen")
    if v.kopfhoerer > v.max:
        raise KonfigFehler("[lautstaerke] kopfhoerer darf nicht über max liegen")

    ziel = _text(prot, "protokoll", "ziel", "stdout")
    if ziel not in ("stdout", "datei"):
        raise KonfigFehler("[protokoll] ziel muss 'stdout' oder 'datei' sein")
    datei = _text(prot, "protokoll", "datei", None)
    if ziel == "datei" and datei is None:
        raise KonfigFehler("[protokoll] ziel='datei' braucht 'datei'")
    ebene = _text(prot, "protokoll", "ebene", "INFO")
    if ebene not in EBENEN:
        raise KonfigFehler("[protokoll] ebene muss DEBUG, INFO, WARNING oder ERROR sein")

    kopfhoerer = _pruefe_kopfhoerer(roh)
    tasten = _pruefe_tasten(roh)
    _pruefe_pins_gemeinsam(kopfhoerer, tasten)
    uhr_abschnitt = _abschnitt(roh, "uhr")
    ntp_pflicht = uhr_abschnitt.get("ntp_pflicht")
    if ntp_pflicht is not None and not isinstance(ntp_pflicht, bool):
        raise KonfigFehler("[uhr] ntp_pflicht muss true oder false sein")
    sim_abschnitt = _abschnitt(roh, "sim")
    erlauben = sim_abschnitt.get("erlauben", False)
    if not isinstance(erlauben, bool):
        raise KonfigFehler("[sim] erlauben muss true oder false sein")

    return BoxKonfig(
        pfade=Pfade(_pfad(zustand, basis), _pfad(medien, basis)),
        leser=LeserKonfig(_text(leser, "leser", "geraet", "/dev/cu.usbmodem*") or ""),
        mpd=MpdKonfig(
            _text(mpd, "mpd", "host", "localhost") or "localhost",
            _ganz(mpd, "mpd", "port", 6600, 1, 65535),
        ),
        lautstaerke=v,
        protokoll=ProtokollKonfig(
            ziel=ziel or "stdout",
            datei=_pfad(datei, basis) if datei else None,
            ebene=ebene or "INFO",
            max_bytes=_ganz(prot, "protokoll", "max_bytes", 1_000_000, 10_000, 100_000_000),
            anzahl=_ganz(prot, "protokoll", "anzahl", 5, 1, 50),
        ),
        toene=TonKonfig(
            tuple(kommando), _pfad(ton_ordner, basis) if ton_ordner else None, kennlinie, float(bereich)
        ),
        sync=_pruefe_sync(roh, basis, _pfad(medien, basis)),
        mqtt=_pruefe_mqtt(roh),
        netz=_pruefe_netz(roh),
        strom=_pruefe_strom(roh),
        kopfhoerer=kopfhoerer,
        tasten=tasten,
        uhr=UhrKonfig(ntp_pflicht),
        sim=SimKonfig(erlauben),
    )


def lade(pfad: str | Path) -> BoxKonfig:
    """``tobibox.toml`` lesen und prüfen; wirft ``KonfigFehler``."""
    pfad = Path(pfad)
    try:
        with open(pfad, "rb") as f:
            roh = tomllib.load(f)
    except FileNotFoundError as e:
        raise KonfigFehler(f"Konfigurationsdatei fehlt: {pfad}") from e
    except tomllib.TOMLDecodeError as e:
        raise KonfigFehler(f"{pfad}: kein gültiges TOML: {e}") from e
    except OSError as e:
        raise KonfigFehler(f"{pfad}: nicht lesbar: {e}") from e
    return pruefe(roh, pfad.resolve().parent)
