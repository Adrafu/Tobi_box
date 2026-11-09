"""Fixtures für die Tests der Integration ``tobibox``.

* ``nas``: ein Test-Medienordner im Stil der NAS-Freigabe (``medien/``, ``eingang/``, ``export/``, ``releases/``).
* ``audio``: erzeugt kleine Audiodateien mit ``ffmpeg`` (Tags über ``-metadata``). Echte Hörspiele kommen nie ins Repo.
* ``integration``: richtet die Integration mit gemocktem MQTT (Plugin ``mqtt_mock``) ein.
* ``box``: eine Fake-Box, die auf dem Broker liest und schreibt wie die echte Box (``mqtt-v1.md``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_mqtt_message

from custom_components.tobibox import FRONTEND_PFAD  # noqa: F401  (Import prüft, dass das Paket ladbar ist)
from custom_components.tobibox import hub as hub_modul
from custom_components.tobibox.const import (
    CONF_BOXEN,
    CONF_MEDIEN_PFAD,
    CONF_UPLOAD_MAX_MIB,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"

FFMPEG = shutil.which("ffmpeg")
braucht_ffmpeg = pytest.mark.skipif(FFMPEG is None or shutil.which("ffprobe") is None, reason="ffmpeg/ffprobe fehlen")


# --------------------------------------------------------------------------
# Test-Medienordner
# --------------------------------------------------------------------------


@dataclass
class Nas:
    basis: Path

    @property
    def medien(self) -> Path:
        return self.basis / "medien"

    @property
    def eingang(self) -> Path:
        return self.basis / "eingang"

    @property
    def export(self) -> Path:
        return self.basis / "export"

    @property
    def releases(self) -> Path:
        return self.basis / "releases"

    @property
    def papierkorb(self) -> Path:
        return self.medien / "_papierkorb"

    def serie(self, ordner: str, serie_id: str | None = None, name: str | None = None, folgen: list[str] | None = None,
              typ: str = "normal", angelegt_am: str = "2026-11-01T10:00:00Z", **extra: Any) -> Path:
        """Legt einen Serien-Ordner mit ``serie.json`` an (Dateien muss der Test selbst hineinlegen)."""
        pfad = self.medien / ordner
        pfad.mkdir(parents=True, exist_ok=True)
        daten = {
            "schema_version": 1,
            "id": serie_id or ordner,
            "name": name or ordner,
            "typ": typ,
            "folgen": list(folgen or []),
            "angelegt_am": angelegt_am,
            **extra,
        }
        (pfad / "serie.json").write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return pfad

    def serie_json(self, ordner: str) -> dict[str, Any]:
        return json.loads((self.medien / ordner / "serie.json").read_text(encoding="utf-8"))


@pytest.fixture
def nas(tmp_path: Path) -> Nas:
    basis = tmp_path / "tobibox"
    for n in ("medien", "eingang", "export", "releases"):
        (basis / n).mkdir(parents=True)
    return Nas(basis)


@pytest.fixture
def frontend_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Eine Attrappe der Seite, damit ``panel_custom`` und die statischen Dateien registriert werden."""
    pfad = tmp_path / "frontend"
    pfad.mkdir()
    (pfad / "tobibox-panel.js").write_text("// Attrappe der Seite\n", encoding="utf-8")
    import custom_components.tobibox as paket

    monkeypatch.setattr(paket, "FRONTEND_PFAD", pfad)
    return pfad


# --------------------------------------------------------------------------
# Audiodateien mit ffmpeg
# --------------------------------------------------------------------------

_CODEC = {
    "mp3": ["-c:a", "libmp3lame", "-b:a", "32k", "-id3v2_version", "3", "-write_id3v1", "0"],
    "m4b": ["-c:a", "aac", "-b:a", "32k", "-movflags", "use_metadata_tags", "-f", "ipod"],
    "m4a": ["-c:a", "aac", "-b:a", "32k", "-movflags", "use_metadata_tags", "-f", "ipod"],
    "flac": ["-c:a", "flac"],
    "ogg": ["-c:a", "libvorbis", "-b:a", "32k"],
    "wav": ["-c:a", "pcm_s16le"],
}


def erzeuge_audio(
    pfad: Path,
    *,
    frequenz: int = 440,
    dauer: float = 1.0,
    kapitel: list[str] | None = None,
    **tags: str,
) -> Path:
    """Eine kleine Sinus-Datei mit Tags. Die Frequenz macht den Inhalt (und die Prüfsumme) verschieden."""
    assert FFMPEG, "ffmpeg fehlt"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    endung = pfad.suffix.lstrip(".").lower()
    cmd = [FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={frequenz}:duration={dauer}"]
    meta = None
    if kapitel:
        meta = pfad.with_suffix(".ffmeta.txt")
        zeilen = [";FFMETADATA1"]
        for k, v in tags.items():
            zeilen.append(f"{k}={v}")
        for i, titel in enumerate(kapitel):
            zeilen += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={i * 500}", f"END={(i + 1) * 500}", f"title={titel}"]
        meta.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
        cmd += ["-i", str(meta), "-map", "0:a", "-map_metadata", "1"]
    cmd += _CODEC[endung]
    if not kapitel:
        for k, v in tags.items():
            cmd += ["-metadata", f"{k}={v}"]
    cmd.append(str(pfad))
    subprocess.run(cmd, check=True, capture_output=True)
    if meta is not None:
        meta.unlink()
    return pfad


@pytest.fixture
def audio() -> Callable[..., Path]:
    return erzeuge_audio


@pytest.fixture(scope="session")
def mp3_vorlage(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Eine kleine gültige mp3 ohne Tags, die Tests kopieren (schneller als jedes Mal ``ffmpeg``)."""
    if FFMPEG is None:
        pytest.skip("ffmpeg fehlt")
    return erzeuge_audio(tmp_path_factory.mktemp("vorlage") / "vorlage.mp3")


@pytest.fixture
def lege_mp3(mp3_vorlage: Path) -> Callable[..., Path]:
    """``lege_mp3(pfad)`` legt eine gültige mp3 an (Ordner werden erzeugt)."""

    def lege(pfad: Path) -> Path:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(mp3_vorlage, pfad)
        return pfad

    return lege


# --------------------------------------------------------------------------
# Fake-Box
# --------------------------------------------------------------------------


class FakeBox:
    """Spricht MQTT wie die Box (``mqtt-v1.md``) und liest, was HA veröffentlicht."""

    def __init__(self, hass: Any, mqtt_mock: Any, name: str) -> None:
        self.hass = hass
        self.mqtt = mqtt_mock
        self.name = name
        self._zaehler = 0

    # --- Box -> HA ---
    # Ein Broker liefert nur beim Abonnieren die gespeicherte (retained) Nachricht mit gesetztem Retain-Flag; spätere
    # Nachrichten kommen mit Retain=0. HA-MQTT wertet je Abo nur die erste Nachricht mit Retain-Flag aus.
    async def online(self, wert: bool = True, gespeichert: bool = False) -> None:
        async_fire_mqtt_message(self.hass, f"tobibox/{self.name}/online", "online" if wert else "offline", 1, gespeichert)
        await self.hass.async_block_till_done()

    async def status(self, gespeichert: bool = False, **felder: Any) -> dict[str, Any]:
        status = {
            "v": 1,
            "ts": "2026-11-09T10:00:00Z",
            "zustand": "leer",
            "lernmodus": False,
            "serie": None,
            "akku_prozent": 80,
            "lader": False,
            "netz": "home",
            "sync": {"zustand": "idle", "letzter_ende": None, "ergebnis": None, "grund": None, "neu": 0},
            "speicher_frei_mb": 5000,
            "version": "1.0.0",
            "firmware": "1.0.0",
            "protokoll": 1,
            "leser": "ok",
            "letzter_fehler": None,
            "zeitquelle": "ntp",
            "zeit_ok": True,
            "konfig": {"revision": 0, "liste_id": ""},
            "update": {"zustand": "ok", "version": "1.0.0", "grund": None},
        }
        status.update(felder)
        async_fire_mqtt_message(self.hass, f"tobibox/{self.name}/status", json.dumps(status), 1, gespeichert)
        await self.hass.async_block_till_done()
        return status

    async def unbekannt(self, uid: str, *, art: str = "unbekannt", anzahl: int = 1, befehl_id: str | None = None,
                        zuletzt: str | None = None, zuerst: str = "2026-11-09T10:00:00Z",
                        gespeichert: bool = False) -> dict[str, Any]:
        self._zaehler += 1
        daten = {
            "v": 1,
            "uid": uid,
            "art": art,
            "zuerst": zuerst,
            "zuletzt": zuletzt or f"2026-11-09T10:00:{self._zaehler:02d}.123Z",
            "anzahl": anzahl,
            "zeit_ok": True,
            "befehl_id": befehl_id,
        }
        async_fire_mqtt_message(self.hass, f"tobibox/{self.name}/unknown/{uid}", json.dumps(daten), 1, gespeichert)
        await self.hass.async_block_till_done()
        return daten

    async def ereignis(self, art: str, daten: dict[str, Any], eid: str | None = None) -> dict[str, Any]:
        self._zaehler += 1
        nachricht = {"v": 1, "id": eid or f"00000000-0000-4000-8000-{self._zaehler:012d}", "ts": "2026-11-09T10:05:00Z", "art": art, "daten": daten}
        async_fire_mqtt_message(self.hass, f"tobibox/{self.name}/event", json.dumps(nachricht), 1, False)
        await self.hass.async_block_till_done()
        return nachricht

    async def ui(self, objekt: str, nutzlast: str = "PRESS") -> None:
        async_fire_mqtt_message(self.hass, f"tobibox/{self.name}/ui/{objekt}", nutzlast, 1, False)
        await self.hass.async_block_till_done()

    async def discovery(self, anzeigename: str, gespeichert: bool = False) -> None:
        daten = {"name": "Akku", "device": {"identifiers": [f"tobibox_{self.name}"], "name": f"Tobi Box {anzeigename}"}}
        async_fire_mqtt_message(self.hass, f"homeassistant/sensor/tobibox_{self.name}/akku/config", json.dumps(daten), 1, gespeichert)
        await self.hass.async_block_till_done()

    # --- HA -> Box ---
    def veroeffentlicht(self) -> list[tuple[str, Any, int, bool]]:
        aus = []
        for c in self.mqtt.async_publish.call_args_list:
            thema, nutzlast, qos, retain = c.args[0], c.args[1], c.args[2], c.args[3]
            aus.append((thema, nutzlast, qos, retain))
        return aus

    def nachrichten(self, thema: str) -> list[Any]:
        aus = []
        for t, n, _q, _r in self.veroeffentlicht():
            if t == thema:
                try:
                    aus.append(json.loads(n))
                except (TypeError, ValueError):
                    aus.append(n)
        return aus

    def befehle(self, befehl: str | None = None) -> list[dict[str, Any]]:
        liste = self.nachrichten(f"tobibox/{self.name}/cmd")
        return [b for b in liste if befehl is None or b["befehl"] == befehl]

    def acks(self, uid: str) -> list[dict[str, Any]]:
        return self.nachrichten(f"tobibox/{self.name}/unknown/{uid}/ack")

    def konfigs(self) -> list[dict[str, Any]]:
        return self.nachrichten("tobibox/config")

    def reihenfolge(self) -> list[str]:
        """Themen der Veröffentlichungen in der Reihenfolge (für „erst Konfiguration, dann ack“)."""
        return [t for t, *_ in self.veroeffentlicht()]


@pytest.fixture
async def mqtt_broker(hass: Any, mqtt_mock: Any) -> AsyncGenerator[Any]:
    """Der gemockte MQTT-Client des Plugins. Beim Aufräumen wird der Zeitgeber des Clients abgemeldet, den die
    Attrappe des Plugins sonst stehen lässt (``socket_close`` kommt im Mock nicht)."""
    yield mqtt_mock
    echt = getattr(mqtt_mock, "_mock_wraps", None)
    timer = getattr(echt, "_misc_timer", None)
    if timer is not None:
        timer.cancel()
        echt._misc_timer = None


@pytest.fixture
def box_fabrik(hass: Any, mqtt_broker: Any) -> Callable[[str], FakeBox]:
    return lambda name: FakeBox(hass, mqtt_broker, name)


# --------------------------------------------------------------------------
# Integration einrichten
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def schnelle_zeiten(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kurze Wartezeiten in den Tests (echte Werte stehen in ``const.py``)."""
    monkeypatch.setattr(hub_modul, "START_WARTEN", 0.05)
    monkeypatch.setattr(hub_modul, "EXPORT_WARTEN", (0.02, 0.02, 0.02))
    monkeypatch.setattr(hub_modul, "EXPORT_WARTEN_DANACH", 0.02)
    from custom_components.tobibox import eingang as eingang_modul

    monkeypatch.setattr(eingang_modul, "EINGANG_STILLE_S", 0)


@pytest.fixture
def einrichtung_daten(nas: Nas) -> dict[str, Any]:
    return {CONF_MEDIEN_PFAD: str(nas.medien), CONF_BOXEN: ["box1", "box2"], CONF_UPLOAD_MAX_MIB: 500}


@pytest.fixture
async def starte_integration(
    hass: Any,
    mqtt_broker: Any,
    hass_storage: dict[str, Any],
    enable_custom_integrations: None,
    frontend_dir: Path,
    einrichtung_daten: dict[str, Any],
) -> AsyncGenerator[Callable[..., Any]]:
    """``await starte(warten=True)`` richtet die Integration ein. Mit ``warten=False`` kommt der Test zurück, solange die
    Prüfung des Speichers beim Start noch läuft (um dabei dauerhafte ``status``-Nachrichten der Boxen einzuspielen)."""
    eintraege: list[MockConfigEntry] = []

    async def starte(warten: bool = True) -> Any:
        entry = MockConfigEntry(domain=DOMAIN, data=einrichtung_daten, unique_id=DOMAIN, title="Tobi Box")
        entry.add_to_hass(hass)
        eintraege.append(entry)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        hub = hass.data[DOMAIN]
        if warten:
            await fertig(hass, hub)
        return hub

    yield starte
    for entry in eintraege:
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def fertig(hass: Any, hub: Any) -> None:
    """Wartet, bis die Prüfung des Speichers, die erste Prüfung der Freigabe und der erste Durchlauf des Eingangs fertig sind."""
    await hub.start_fertig.wait()
    if hub._start_task is not None:
        await hub._start_task
    if hub.eingang._task is not None:
        await hub.eingang._task
    await hass.async_block_till_done()


@pytest.fixture
async def integration(starte_integration: Callable[..., Any], nas: Nas) -> Any:
    """Die eingerichtete Integration (Erststart: neue Liste, veröffentlicht)."""
    return await starte_integration()


@pytest.fixture
def ereignisse(integration: Any) -> list[dict[str, Any]]:
    """Abonniert alle Ereignisse (wie die Seite) und sammelt die Inhalte von ``event``."""
    from custom_components.tobibox.const import EREIGNIS_THEMEN
    from custom_components.tobibox.hub import Abo

    gesammelt: list[dict[str, Any]] = []

    class Verbindung:
        user = None

        def send_message(self, nachricht: dict[str, Any]) -> None:
            gesammelt.append(nachricht["event"])

    integration.abo_hinzu(Abo(Verbindung(), 1, set(EREIGNIS_THEMEN), None))
    return gesammelt


def ereignis_arten(liste: list[dict[str, Any]], thema: str) -> list[str]:
    return [e["art"] for e in liste if e["thema"] == thema]


async def warte_auf(hass: Any, bedingung: Callable[[], bool], versuche: int = 100, *, block: bool = True) -> None:
    """Wartet, bis die Bedingung gilt. ``block=False`` wartet nicht auf die Aufgaben von HA (nötig, solange ein Executor-Job
    absichtlich hängt: ``async_block_till_done`` würde auf ihn warten)."""
    import asyncio

    for _ in range(versuche):
        if block:
            await hass.async_block_till_done()
        if bedingung():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Bedingung wurde nicht erfüllt")


def gespeicherte_konfig(hass_storage: dict[str, Any]) -> dict[str, Any] | None:
    daten = hass_storage.get("tobibox")
    return daten["data"]["konfig"] if daten else None


@pytest.fixture
def vorab_speicher(hass_storage: dict[str, Any]) -> Callable[[dict[str, Any]], None]:
    """Legt vor dem Start einen Inhalt in ``.storage/tobibox`` (z. B. für Tests der Wiederherstellung)."""

    def setze(daten: dict[str, Any]) -> None:
        hass_storage["tobibox"] = {"version": 1, "minor_version": 1, "key": "tobibox", "data": daten}

    return setze


def _unbenutzt() -> None:  # pragma: no cover
    os.getpid()
