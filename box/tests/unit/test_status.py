"""Statussammler der Stufe 2: Prüfpunkt Leser (12.2) und Status-JSON (mqtt-v1, 3.3)."""

from __future__ import annotations

import pytest

from tobibox import events as ev
from tobibox.events import Jetzt
from tobibox.outbox import zeitstempel
from tobibox.status import Statussammler

J = Jetzt(1000.0, 1_700_000_000.0, "ntp", True)
HALLO = ev.LeserHallo(1, "1.0.0", "fa4e0000", "4.2")
S1 = ev.Serie("s1", "Der Rabe", "normal", "s1", ("a.mp3",))


def mit(*ereignisse, **kw) -> Statussammler:
    s = Statussammler(**kw)
    for e in ereignisse:
        s.beobachte(e, J)
    return s


def test_leser_vor_dem_ersten_hallo_ist_getrennt():
    assert mit().leser(J.mono) == "getrennt"


def test_leser_nach_hallo_ist_ok():
    assert mit(HALLO).leser(J.mono) == "ok"


@pytest.mark.parametrize("grund", ["getrennt", "kein_herzschlag", "hello_timeout"])
def test_leser_nach_ausfall_getrennt_bis_zum_naechsten_hallo(grund):
    s = mit(HALLO, ev.LeserAlarm(grund))
    assert s.leser(J.mono) == "getrennt"
    s.beobachte(HALLO, J)
    assert s.leser(J.mono) == "ok"


def test_leser_protokoll_unbekannt_ist_fehler_auch_ohne_hallo():
    assert mit(ev.LeserAlarm("proto_unbekannt")).leser(J.mono) == "fehler"
    assert mit(HALLO, ev.LeserAlarm("proto_unbekannt")).leser(J.mono) == "fehler"


def test_leser_fehler_nur_zehn_sekunden_und_nur_schwere_fehler():
    s = mit(HALLO, ev.LeserFehler("x", "y", "fehler"))
    assert s.leser(J.mono + 10.0) == "fehler" and s.leser(J.mono + 10.1) == "ok"
    for schwere in ("warnung", "hinweis"):
        assert mit(HALLO, ev.LeserFehler("x", "y", schwere)).leser(J.mono) == "ok"


def test_leser_simulation_gewinnt():
    assert mit(ev.LeserAlarm("getrennt"), leser_simulation=True).leser(J.mono) == "simulation"


def zm(**kw):
    basis = dict(sitzung="spielt", strom="aktiv", serie_id="s1", lernmodus=False, ruhe="normal", gute_nacht="aus",
                 figur_liegt=True, folge="a.mp3", track=2)
    return ev.ZustandMelden(**{**basis, **kw})


def test_status_json_vor_dem_ersten_ereignis():
    d = Statussammler().als_dict(J, (S1,), 1234)
    assert d["v"] == 1 and d["zustand"] == "leer" and d["serie"] is None and d["folge"] is None
    assert d["netz"] == "offline" and d["leser"] == "getrennt" and d["firmware"] is None
    assert d["konfig"] == {"revision": 0, "liste_id": ""} and d["speicher_frei_mb"] == 1234
    assert d["zeitquelle"] == "ntp" and d["zeit_ok"] is True and d["protokoll"] == 1
    assert d["letzter_fehler"] is None and d["akku_prozent"] is None and d["lader"] is None


def test_status_json_aus_den_beobachteten_werten():
    s = mit(HALLO, ev.NetzKlasse("hotspot"), ev.AkkuStand(76), ev.LaderGeaendert(False))
    s.befehl(zm(lernmodus=True), J)
    s.befehl(ev.Protokoll("player", "ERROR", "mpd_weg", "fehler"), J)
    d = s.als_dict(J, (S1,), 10)
    assert (d["zustand"], d["lernmodus"]) == ("spielt", True)
    assert d["serie"] == {"id": "s1", "name": "Der Rabe"} and d["folge"] == {"name": "a.mp3", "track": 2}
    assert (d["netz"], d["akku_prozent"], d["lader"], d["firmware"], d["leser"]) == ("hotspot", 76, False, "1.0.0", "ok")
    assert d["letzter_fehler"] == {"zeit": zeitstempel(J.wall), "text": "mpd_weg fehler"}  # Zeitstempel-String (mqtt-v1.md 3.3)
    assert isinstance(d["letzter_fehler"]["zeit"], str) and d["letzter_fehler"]["zeit"].endswith("Z")


def test_status_json_herunterfahren_und_serie_ohne_namen():
    s = Statussammler()
    s.befehl(zm(strom="herunterfahren", serie_id="unbekannt-id", folge=None, track=None), J)
    d = s.als_dict(J, (S1,), 1)
    assert d["zustand"] == "herunterfahren" and d["serie"] == {"id": "unbekannt-id", "name": "unbekannt-id"}
    assert d["folge"] is None


def test_status_json_konfig_aus_dem_letzten_konfig_geladen():
    k = ev.Konfig(7, "a3f9c1e07b2d4856", {}, ev.LeiseZeiten("Europe/Berlin", ()), ev.GuteNacht(30, 60))
    d = mit(ev.KonfigGeladen(k)).als_dict(J, (), 1)
    assert d["konfig"] == {"revision": 7, "liste_id": "a3f9c1e07b2d4856"}


def test_warnungen_im_protokoll_sind_kein_letzter_fehler():
    s = Statussammler()
    s.befehl(ev.Protokoll("x", "WARNING", "a", "b"), J)
    assert s.als_dict(J, (), 1)["letzter_fehler"] is None


def test_leser_simulation_zeigt_simulation_auch_ohne_hallo():
    s = Statussammler(leser_simulation=True)
    assert s.leser(0.0) == "simulation"
    assert s.als_dict(J, (S1,), 1)["leser"] == "simulation"
