"""CUJ 9 (AP 3.7): Neue Folgen kommen auf die Box. Die echte ``App`` mit echtem MPD und echtem rsync-Daemon (``sync_helfer``).

* **Given**: Neue und geänderte Audiodateien liegen auf dem NAS. Box im Heimnetz (oder Hotspot mit Lader).
* **When**: Der Abgleich läuft (zeitgesteuert oder von HA angestoßen).
* **Then**: Neue und geänderte Dateien kommen auf die Box. **Unvollständige Dateien sind nie abspielbar.** **Eine gerade
  spielende Datei wird nie ersetzt** (ihre Änderung wartet auf den nächsten Abgleich), die laufende Wiedergabe stockt nicht,
  und ein Tobie, der während des Abgleichs aufgelegt wird, startet innerhalb der Zeitgrenze (1 s, ``docs/timing.md``). HA zeigt
  Stand und Zeitpunkt (Status ``sync``).

Die Übertragung wird gebremst (``--bwlimit``), damit der Sync lange genug läuft, um dabei zu messen.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import time
from pathlib import Path

import pytest
from fixtures import audio
from fixtures.dienst import mpd_abschnitt
from integration.test_app_e2e import mpd_status, warte
from integration.test_sim_cli import aktuelle_datei, spielt_aus
from sync_helfer import rsync_daemon  # noqa: F401  (Fixture)

from tobibox import app as app_modul
from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox import store
from tobibox.app import App
from tobibox.clock import SimUhr

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync nicht installiert"),
]

UID_LANG = "04a1b2c3"  # Serie ``lang`` (zwei Folgen zu 30 s, aus der ``mpd``-Fixture)
UID_KURZ = "04a1b2c4"  # Serie ``kurz`` (zwei Folgen zu 1 s)
ZEITGRENZE_S = 1.0  # ``docs/timing.md``: Auflegen bis Ton


def md5(p: Path) -> bytes:
    import hashlib

    return hashlib.md5(p.read_bytes()).digest()


class Beobachter:
    """Schaut alle 50 ms in den Medienordner und merkt sich jede Auffälligkeit (halbe Datei, Zwischendatei)."""

    def __init__(self, medien: Path, erlaubt: dict[str, set[int]]) -> None:
        self.medien = medien
        self.erlaubt = erlaubt  # relativer Pfad -> erlaubte Größen (alt und neu); nicht genannte Dateien: nur Größen aus ``spaeter``
        self.verstoesse: list[str] = []
        self.gesehen: set[str] = set()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._lauf())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _lauf(self) -> None:
        while True:
            self.pruefe()
            await asyncio.sleep(0.05)

    def pruefe(self) -> None:
        for p in self.medien.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(self.medien))
            self.gesehen.add(rel)
            if p.name.startswith("."):
                self.verstoesse.append(f"Zwischendatei im Medienordner: {rel}")
                continue
            if rel.endswith(".wav"):
                try:
                    groesse = p.stat().st_size
                except FileNotFoundError:
                    continue
                if rel in self.erlaubt and groesse not in self.erlaubt[rel]:
                    self.verstoesse.append(f"{rel} hat die Größe {groesse}, erlaubt {sorted(self.erlaubt[rel])}")


@pytest.fixture
async def welt(mpd, rsync_daemon, kurz, tmp_path, monkeypatch):
    """Box (``mpd.medien``) mit ``lang`` und ``kurz``; das NAS hat dasselbe, aber ``lang/a.wav`` und ``lang/b.wav`` geändert,
    dazu eine neue Folge ``lang/c.wav`` und eine neue Serie ``neu``."""
    d = rsync_daemon
    box = mpd.medien
    alt = {p.name: p.stat().st_size for p in (box / "lang").glob("*.wav")}
    alt_hash = {p.name: md5(p) for p in (box / "lang").glob("*.wav")}
    shutil.copytree(box, d.quelle, dirs_exist_ok=True)
    audio.erzeuge_serie(d.quelle, "lang", ["a.wav", "b.wav", "c.wav"], serie_id="lang", name="lang", dauer_s=31.0)
    audio.erzeuge_serie(d.quelle, "neu", ["x.wav"], serie_id="neu", name="Neu", dauer_s=40.0)
    neu = {p.name: p.stat().st_size for p in (d.quelle / "lang").glob("*.wav")}
    assert neu["a.wav"] != alt["a.wav"]  # geändert (andere Länge)

    zustand = kurz / "var"
    zustand.mkdir()
    k = ev.Konfig(
        1, "a3f9c1e07b2d4856",
        {UID_LANG: ev.Zuordnung("serie", "lang"), UID_KURZ: ev.Zuordnung("serie", "kurz")},
        ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60),
    )
    store.schreibe_atomar(zustand / "config.json", store.konfig_zu_json(k))
    toml = tmp_path / "tobibox.toml"
    toml.write_text(
        f'[pfade]\nzustand = "{zustand}"\nmedien = "{box}"\n[leser]\ngeraet = "sim"\n'
        f'{mpd_abschnitt(mpd.port)}[lautstaerke]\nmax = 50\nstart = 20\nkopfhoerer = 30\n[toene]\nkommando = ["true", "{{datei}}"]\n'
        f'[netz]\nquelle = "sim"\n[strom]\nquelle = "sim"\n'
        f'[sync]\nhost = "127.0.0.1"\nport = {d.port}\nmodul = "medien"\nreserve_mb = 0\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(app_modul.notify, "stoppt", lambda: None)
    a = App(konfig_modul.lade(toml), melde_bereit=False)
    a.sync._zusatz = ("--bwlimit=250",)
    await a.starte()
    erlaubt = {f"lang/{n}": {alt[n], neu[n]} for n in neu if n in alt}
    erlaubt["lang/c.wav"] = {neu["c.wav"]}
    erlaubt["neu/x.wav"] = {(d.quelle / "neu" / "x.wav").stat().st_size}
    obs = Beobachter(box, erlaubt)
    yield {"app": a, "mpd": mpd, "nas": d, "box": box, "alt_hash": alt_hash, "obs": obs, "toml": toml}
    await obs.stop()
    await a.beende()


async def auflegen(a: App, uid: str, vorgang: str) -> float:
    t0 = time.monotonic()
    a.ereignisse.put_nowait(ev.Aufgelegt(uid, "ntag", False, 0, vorgang))
    return t0


async def sim(a: App, **zeile) -> dict:
    return await a.sim.verarbeite(json.dumps(zeile))


async def warte_sync_fertig(a: App, frist: float = 60.0) -> None:
    try:
        await warte(lambda: a.status.sync["ergebnis"] == "ok", frist, "(Sync fertig)")
    except AssertionError as e:
        raise AssertionError(f"{e}; Stand des Syncs: {a.status.sync}") from None


async def test_sync_zeitgesteuert_unvollstaendiges_nie_abspielbar_laufende_datei_nie_ersetzt(welt):
    a, box, nas, obs = welt["app"], welt["box"], welt["nas"], welt["obs"]
    port = welt["mpd"].port
    alt_hash = welt["alt_hash"]

    # Ein Tobie spielt ``lang/a.wav``; dann kommt die Box heim: der Takt startet den Sync (erster Lauf, Intervall nicht gelaufen)
    await auflegen(a, UID_LANG, "v1")
    await warte(lambda: spielt_aus(port, "lang", "a.wav"), 10.0, "(lang spielt)")
    obs.start()
    vorher = await mpd_status(port)
    t_vorher = time.monotonic()
    await sim(a, befehl="netz", klasse="home")
    await warte(lambda: a.sync.laeuft, 10.0, "(Sync läuft)")

    # Mitten im Sync: ein zweiter Tobie wird aufgelegt und startet innerhalb der Zeitgrenze
    await warte(lambda: any(a.sync.temp_dir.rglob("*")) or any(a.sync.partial_dir.rglob("*")), 10.0, "(Übertragung läuft)")
    assert a.sync.laeuft
    t0 = await auflegen(a, UID_KURZ, "v2")
    await warte(lambda: spielt_aus(port, "kurz"), 10.0, "(kurz spielt)")
    assert time.monotonic() - t0 < ZEITGRENZE_S + 0.5, "Auflegen während des Syncs startet zu spät"  # 0,5 s Messunschärfe der Abfrage

    await warte_sync_fertig(a)
    await obs.stop()
    assert obs.verstoesse == [], obs.verstoesse  # nie eine halbe Datei, nie eine Zwischendatei im Medienordner
    # neue Dateien da, geänderte Datei ``b`` ersetzt
    assert (box / "lang" / "c.wav").exists() and (box / "neu" / "x.wav").exists()
    assert md5(box / "lang" / "b.wav") == md5(nas.quelle / "lang" / "b.wav")
    # die gerade spielende Datei wurde nie ersetzt: Die Beobachtung beginnt nach dem Auflegen, ``a.wav`` war zu Beginn alt
    assert md5(box / "lang" / "a.wav") == alt_hash["a.wav"]
    # der Sync hat der Wiedergabe nicht geschadet und Stand und Zeitpunkt stehen im Status (HA zeigt sie)
    s = a.status.als_dict(a.uhr.jetzt(), a.bibliothek.serien, None)["sync"]
    assert s["zustand"] == "idle" and s["ergebnis"] == "ok" and s["neu"] >= 3 and s["letzter_ende"]
    assert vorher["state"] == "play" and t_vorher


async def test_laufende_datei_wartet_bis_zum_naechsten_abgleich(welt):
    a, box, nas = welt["app"], welt["box"], welt["nas"]
    port = welt["mpd"].port
    alt_hash = welt["alt_hash"]
    # HA stößt den Sync an; erst ``netz home``, dann Intervall als „gerade gelaufen“, damit der Takt nicht dazwischenfunkt
    await auflegen(a, UID_LANG, "v1")
    await warte(lambda: spielt_aus(port, "lang", "a.wav"), 10.0, "(lang spielt)")
    a.sync.letzter_start = time.monotonic()
    await sim(a, befehl="netz", klasse="home")
    a.ereignisse.put_nowait(ev.HaSyncAnstossen("b1", a.uhr.jetzt().wall + 60))
    await warte(lambda: a.sync.laeuft, 10.0, "(Sync von HA angestoßen)")
    await warte_sync_fertig(a)
    assert md5(box / "lang" / "a.wav") == alt_hash["a.wav"]  # sie spielte: unverändert
    assert md5(box / "lang" / "b.wav") == md5(nas.quelle / "lang" / "b.wav")
    assert (await mpd_status(port))["state"] == "play"  # die Wiedergabe lief weiter

    # Der Tobie wird abgehoben, ein anderer spielt: ``a.wav`` ist nicht mehr dran, der nächste Abgleich ersetzt sie
    await auflegen(a, UID_KURZ, "v2")
    await warte(lambda: spielt_aus(port, "kurz"), 10.0, "(kurz spielt)")
    a.sync._zusatz = ()
    ende1 = a.status.sync["letzter_ende"]
    a.ereignisse.put_nowait(ev.HaSyncAnstossen("b2", a.uhr.jetzt().wall + 60))
    await warte(lambda: a.status.sync["letzter_ende"] != ende1 and not a.sync.laeuft, 30.0, "(zweiter Abgleich)")
    assert a.status.sync["ergebnis"] == "ok" and a.status.sync["neu"] == 1
    assert md5(box / "lang" / "a.wav") == md5(nas.quelle / "lang" / "a.wav")


async def test_abbruch_mitten_in_der_uebertragung_laesst_nichts_halbes_zum_abspielen(welt):
    a, box, nas, obs = welt["app"], welt["box"], welt["nas"], welt["obs"]
    obs.start()
    a.sync._zusatz = ("--bwlimit=100",)
    await sim(a, befehl="netz", klasse="home")
    await warte(lambda: a.sync.laeuft, 10.0, "(Sync läuft)")
    await warte(lambda: any(a.sync.temp_dir.rglob("*")) or any(a.sync.partial_dir.rglob("*")), 10.0, "(Übertragung läuft)")
    await sim(a, befehl="netz", klasse="offline")  # Tunnel reißt ab
    await warte(lambda: not a.sync.laeuft, 30.0, "(Sync bricht ab)")
    await obs.stop()
    assert a.status.sync["grund"] == "netz_weg" and a.status.sync["ergebnis"] == "abgebrochen"
    assert obs.verstoesse == [], obs.verstoesse
    # Die Bibliothek kennt nur Fertiges: jede Folge, die sie nennt, ist vollständig und lässt sich öffnen
    from tobibox import library

    bib = library.lade_bibliothek(box, leise=True)
    for serie in bib.serien:
        for folge in serie.folgen:
            for track in serie.tracks.get(folge, (folge,)):
                p = box / serie.ordner / track
                assert p.is_file() and p.name not in (".", "") and not p.name.startswith(".")
    assert not (box / "neu" / "x.wav").exists() or (box / "neu" / "x.wav").stat().st_size == (nas.quelle / "neu" / "x.wav").stat().st_size
    # der nächste Abgleich macht weiter und vollendet
    a.sync._zusatz = ()
    await sim(a, befehl="netz", klasse="home")
    await warte_sync_fertig(a)
    assert md5(box / "neu" / "x.wav") == md5(nas.quelle / "neu" / "x.wav")


async def test_mpd_kennt_die_neuen_folgen_nach_dem_sync_und_die_bibliothek_wurde_neu_geladen(welt):
    a, box = welt["app"], welt["box"]
    mpd = welt["mpd"]
    a.sync._zusatz = ()
    await sim(a, befehl="netz", klasse="home")
    await warte_sync_fertig(a)
    await warte(lambda: any(s.id == "neu" for s in a.kern.session.serien), 10.0, "(Kern kennt die neue Serie)")
    lang = next(s for s in a.bibliothek.serien if s.id == "lang")
    assert lang.folgen == ("a.wav", "b.wav", "c.wav")
    gelistet = mpd.frage("listall")
    assert "lang/c.wav" in gelistet and "neu/x.wav" in gelistet  # MPD hat neu eingelesen (Haken ``einlesen``)
    # und ein Tobie, der erst jetzt zugeordnet wird, spielt die neue Serie
    a.ereignisse.put_nowait(ev.Aufgelegt("04ffeedd", "ntag", False, 0, "v9"))
    await asyncio.sleep(0.2)
    zeile = await sim(a, befehl="card", uid="04ffeedd", ziel={"typ": "serie", "serie": "neu"})
    assert zeile["ok"]
    await warte(lambda: spielt_aus(mpd.port, "neu", "x.wav"), 10.0, "(neue Serie spielt)")


async def test_sync_wartet_nicht_im_hotspot_ohne_lader_und_ohne_akku(welt):
    a, box = welt["app"], welt["box"]
    await sim(a, befehl="strom", lader=False, akku=40)
    await sim(a, befehl="netz", klasse="hotspot")
    await asyncio.sleep(0.6)
    assert not a.sync.laeuft and not (box / "neu").exists()
    await sim(a, befehl="strom", akku=60)  # jetzt über 50 %
    await sim(a, befehl="netz", klasse="offline")
    await sim(a, befehl="netz", klasse="hotspot")  # neu im Hotspot: der nächste Takt startet
    await warte(lambda: a.sync.laeuft or a.status.sync["ergebnis"] == "ok", 10.0, "(Sync im Hotspot mit 60 %)")
