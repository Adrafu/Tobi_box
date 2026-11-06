"""CUJ 1 (AP 1.6): Bekannten Tobie auflegen. Die Kette gelesen -> entprellt -> zugeordnet -> spielt.

Bewiesene Schritte von CUJ 1 (Given / When / Then):

* Given: Tobie ist einer Serie zugeordnet, Dateien liegen lokal, es gibt keinen Zeiger.
  When: ``PLACED`` kommt von der Firmware (echte Zeilenverarbeitung ``reader.Leser``).
  Then: Folge 1, erster Track, Position 0, mit der Vorgangs-ID der Zeile; Modus ``spielt``
  (``test_auflegen_ohne_zeiger_spielt_folge_1...``).
* Then: Das Protokoll zeigt die Kette mit einer Vorgangs-ID. Die Zeilen ``aufgelegt`` und ``entprellt``
  schreibt ``app``, ``zugeordnet`` und ``spielt`` die Sitzung (``test_protokollkette_...`` mit echter
  ``App``, ``fake_reader`` und echtem MPD) und der Befehl ``Abspielen`` kommt an MPD an.
* Zeitgrenze: Die Zeitgrenze (1,0 s) misst ``docs/timing.md``; hier nur der Dienstanteil im Container.

Nicht doppelt geprüft: Folgen-Tobie und Folge mit mehreren Tracks stehen in
``test_cuj01_folgen_tobie.py`` und ``test_cuj01_folge_mit_tracks.py``; Resume und Abheben in CUJ 2/3.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest
from conftest import CujBox, app_welt
from fixtures import audio
from integration.test_app_e2e import _spielt, mpd_status, warte

from tobibox import config as konfig_modul
from tobibox import events as ev
from tobibox.app import App

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader  # noqa: E402

SERIE = "3f9a1c07b2d4"
UID = "04a1b2c3"
UID_ZWEI = "04a1b2c4"


def aufbau(medien):
    audio.erzeuge_serie(medien, "rabe", ["a.wav", "b.wav", "c.wav"], serie_id=SERIE, name="Rabe", dauer_s=20.0)
    audio.erzeuge_serie(medien, "ueberraschung", ["ton.wav"], serie_id="c07d2e91a45b", typ="ueberraschung", dauer_s=2.0)


@pytest.fixture
def box(tmp_path):
    zuordnungen = {UID: ev.Zuordnung("serie", SERIE), UID_ZWEI: ev.Zuordnung("serie", SERIE)}
    return CujBox(tmp_path, zuordnungen, aufbau)


def test_auflegen_ohne_zeiger_spielt_folge_1_mit_der_vorgangs_id_der_zeile(box):
    box.leser.hello()
    box.leser.placed(UID)
    (a,) = box.befehle(ev.Abspielen)
    assert (a.serie_id, a.datei, a.tracks, a.track, a.position_s) == (SERIE, "a.wav", ("a.wav",), 0, 0.0)
    assert a.vorgang == "00000001"  # die ID, die der Leser zu dieser PLACED-Zeile vergeben hat
    assert box.modus == "spielt" and box.player.spielt
    assert box.kern.session.figur.vorgang == a.vorgang
    assert not (box.zustand / "resume.json").exists()  # kein Zeiger vorher, und das Auflegen schreibt keinen


def test_nur_ein_abspielen_je_auflegen_und_lautstaerke_kommt_davor(box):
    box.leser.hello()
    n = len(box.log)
    box.leser.placed(UID)
    neu = box.log[n:]
    abspiel = [i for i, b in enumerate(neu) if isinstance(b, ev.Abspielen)]
    lauts = [i for i, b in enumerate(neu) if isinstance(b, ev.LautstaerkeSetzen)]
    assert len(abspiel) == 1 and lauts and max(lauts) < abspiel[0]  # Lautstärke wird vor dem Start gesetzt


def test_sitzungsprotokoll_zugeordnet_dann_spielt_mit_gleicher_vorgangs_id(box):
    box.leser.placed(UID)
    namen = [(p.ereignis, p.vorgang) for p in box.protokoll if p.ereignis in ("zugeordnet", "spielt")]
    vorgang = box.kern.session.figur.vorgang
    assert namen == [("zugeordnet", vorgang), ("spielt", vorgang)]
    z = next(p for p in box.protokoll if p.ereignis == "zugeordnet")
    assert (z.ergebnis, z.daten["uid"], z.daten["serie"], z.daten["ziel"]) == ("ok", UID, SERIE, "serie")
    s = next(p for p in box.protokoll if p.ereignis == "spielt")
    assert (s.daten["folge"], s.daten["track"], s.daten["position_s"]) == ("a.wav", 0, 0.0)


def test_zweites_auflegen_derselben_serie_mit_anderem_tobie_nach_abheben_bekommt_neue_vorgangs_id(box):
    box.leser.placed(UID)
    erste = box.kern.session.figur.vorgang
    box.leser.removed()
    box.leser.placed(UID_ZWEI)
    zweite = box.kern.session.figur.vorgang
    assert erste != zweite and box.modus == "spielt"


async def test_protokollkette_aufgelegt_entprellt_zugeordnet_spielt_und_mpd_spielt(mpd, tmp_path, protokoll):
    """Echte ``App``, ``fake_reader`` (Pseudo-Terminal) und echtes MPD: eine Vorgangs-ID in der ganzen Kette."""
    welt = app_welt(mpd, tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, {"rabe": (SERIE, ["folge-01.wav", "folge-02.wav"], 30.0)})
    link, toml = welt["link"], welt["toml"]
    with fake_reader.FakeReader(link, hb_intervall_s=0.5) as fr:
        app = App(konfig_modul.lade(toml), melde_bereit=False)
        await app.starte()
        try:
            await warte(lambda: "PING" in fr.empfangen, 5.0, "(Leser verbunden)")
            await asyncio.sleep(0.8)
            t0 = time.monotonic()
            fr.place(UID)
            await warte(lambda: _spielt(mpd.port), 8.0, "(spielt)")
            bis_ton = time.monotonic() - t0
            st = await mpd_status(mpd.port)
            assert st["playlistlength"] == "1" and float(st["elapsed"]) < 2.0  # Folge 1, von vorn
            await asyncio.sleep(0.3)
        finally:
            await app.beende()
    vorgang = app.kern.session.figur.vorgang
    kette = [z["ereignis"] for z in protokoll.zeilen() if z.get("vorgang") == vorgang]
    gesucht = ["aufgelegt", "entprellt", "zugeordnet", "spielt", "abspielen", "abspielen_fertig"]
    pos = [kette.index(n) for n in gesucht]  # fehlt eine Zeile: ValueError
    assert pos == sorted(pos), kette
    (aufgelegt,) = protokoll.finde("aufgelegt", vorgang)
    assert aufgelegt["baustein"] == "reader" and aufgelegt["daten"]["uid"] == UID and aufgelegt["daten"]["seq"] == 0
    assert len(vorgang) == 8 and all(c in "0123456789abcdef" for c in vorgang)
    # Dienstanteil: vom Eintreffen der Zeile bis zum Befehl an MPD, danach bis „play“ (Container-Wert)
    (abspielen,) = protokoll.finde("abspielen", vorgang)
    assert abspielen["mono"] - aufgelegt["mono"] < 0.25
    assert bis_ton < 1.0, bis_ton  # fake_reader -> MPD „play“ im Container; die Grenze gilt am Ausgang (timing.md)
