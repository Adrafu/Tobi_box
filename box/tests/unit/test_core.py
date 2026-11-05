"""Kern: Ereignisse laufen durch die Teilautomaten, Lautstärke, Konflikt-Tabelle (6.1, 6.2, 6.4, 8)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from conftest import UID_NACHT, UID_S1, UID_STATUS, KernHarnisch, kern

from tobibox import core, session
from tobibox import events as ev
from tobibox.clock import SimUhr


def ohne_meldung(out):
    """Befehle ohne ``ZustandMelden`` und ``Protokoll``."""
    return [o for o in out if not isinstance(o, (ev.ZustandMelden, ev.Protokoll))]


def fake_teil(auf: dict | None = None, kennzeichen: str = "x"):
    """Ein Teilautomat, der auf Ereignistypen eine feste Ausgabe liefert und mitschreibt."""
    auf = auf or {}

    def step(z, e, jetzt):
        out = auf.get(type(e), ())
        if callable(out):
            out = out(e)
        return z + (type(e),), tuple(out)

    return SimpleNamespace(neuer_zustand=lambda: (), step=step, kennzeichen=lambda z: kennzeichen)


def baue(monkeypatch, *fakes: tuple[str, object]) -> KernHarnisch:
    monkeypatch.setattr(core, "TEILAUTOMATEN", (("session", session),) + tuple(fakes))
    return KernHarnisch()


# --------------------------------------------------------------------------
# Aufbau und Ablauf
# --------------------------------------------------------------------------


def test_teilautomaten_liste_beginnt_mit_session():
    assert [n for n, _ in core.TEILAUTOMATEN][0] == "session"


def test_geraete_einstellungen_setzen_lautstaerke_als_ersten_befehl():
    k = KernHarnisch(start=False)
    out = k.sende(ev.GeraeteEinstellungen(60, 40, 25))
    assert out[0] == ev.LautstaerkeSetzen(40, 60)
    assert k.z.session.wirksam == 40  # LautstaerkeGeaendert ging an die Teilautomaten


def test_startlautstaerke_wird_auf_die_grenze_gekappt():
    k = KernHarnisch(start=False)
    assert k.sende(ev.GeraeteEinstellungen(50, 80, 25))[0] == ev.LautstaerkeSetzen(50, 50)


def test_vor_den_einstellungen_keine_lautstaerke():
    k = KernHarnisch(start=False)
    assert not any(isinstance(o, ev.LautstaerkeSetzen) for o in k.sende(ev.Takt()))


def test_core_ist_deterministisch_und_veraendert_den_alten_zustand_nicht():
    k = KernHarnisch()
    z0 = k.z
    j = k.uhr.jetzt()
    a = core.step(z0, ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1"), j)
    b = core.step(z0, ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1"), j)
    assert a == b
    assert z0 is k.z and z0.session.modus == "leer"


def test_auflegen_ordnet_befehle_nach_rang():
    k = KernHarnisch()
    out = k.sende(ev.Aufgelegt("04ffeedd", "ntag", False, 0, "v1"))
    raenge = [core._RANG[type(o)] for o in out]
    assert raenge == sorted(raenge)
    assert out[0] == ev.LautstaerkeSetzen(40, 60)
    assert ev.Abspielen("ueb", "ueb", "u1.mp3", 0.0, "v1") in out


def test_lautstaerke_vor_abspielen_auch_wenn_unveraendert():
    """Regel 6: das Setzen kommt vor jedem Abspielen, auch bei gleichem Wert."""
    k = KernHarnisch()
    for v in ("v1", "v2"):
        out = k.sende(ev.Aufgelegt(UID_S1, "ntag", False, 0, v))
        assert out[0] == ev.LautstaerkeSetzen(40, 60)
        assert any(isinstance(o, ev.Abspielen) for o in out)
        k.sende(ev.Abgehoben(1, v))


def test_zustand_melden_nur_bei_aenderung_und_mit_standardwerten():
    k = KernHarnisch(start=False)
    erste = [o for o in k.sende(ev.Takt()) if isinstance(o, ev.ZustandMelden)]
    assert erste == [ev.ZustandMelden("leer", "aktiv", None, False, "normal", "aus", False)]
    assert not [o for o in k.sende(ev.Takt()) if isinstance(o, ev.ZustandMelden)]
    k.sende(ev.GeraeteEinstellungen(60, 40, 25))
    k.sende(ev.KonfigGeladen(__import__("conftest").mk_konfig()))
    k.sende(ev.BibliothekGeladen((__import__("conftest").S1,)))
    out = k.sende(ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1"))
    assert [o for o in out if isinstance(o, ev.ZustandMelden)] == [
        ev.ZustandMelden("spielt", "aktiv", "s1", False, "normal", "aus", True)
    ]


def test_aktion_status_loest_status_pruefen_aus():
    k = KernHarnisch()
    out = k.sende(ev.Aufgelegt(UID_STATUS, "ntag", False, 0, "v7"))
    assert ev.StatusPruefen("v7") in out
    assert not any(isinstance(o, (ev.Abspielen, ev.LautstaerkeSetzen)) for o in out)


def test_aktion_gute_nacht_loest_kein_status_pruefen_aus():
    k = KernHarnisch()
    out = k.sende(ev.Aufgelegt(UID_NACHT, "ntag", False, 0, "v7"))
    assert not any(isinstance(o, ev.StatusPruefen) for o in out)


def test_interne_ereignisse_gehen_an_alle_teilautomaten_in_derselben_verarbeitung(monkeypatch):
    a = fake_teil({ev.Takt: lambda e: [ev.LernenGeaendert(True)]})
    b = fake_teil()
    k = baue(monkeypatch, ("a", a), ("b", b))
    k.sende(ev.Takt())
    assert k.z.teil["b"][-2:] == (ev.Takt, ev.LernenGeaendert)
    assert k.z.teil["a"][-2:] == (ev.Takt, ev.LernenGeaendert)  # auch der Sender sieht es


def test_grenze_gesetzt_sehen_die_teilautomaten_nicht(monkeypatch):
    a = fake_teil({ev.Takt: lambda e: [ev.GrenzeGesetzt("leise_zeit", 20)]})
    k = baue(monkeypatch, ("a", a))
    out = k.sende(ev.Takt())
    assert ev.GrenzeGesetzt not in k.z.teil["a"]
    assert ev.LautstaerkeSetzen(20, 20) in out
    assert ev.LautstaerkeGeaendert in k.z.teil["a"]


def test_reihenfolge_der_teilautomaten_ist_fest(monkeypatch):
    reihenfolge = []

    def mk(name):
        t = fake_teil()
        alt = t.step

        def step(z, e, j):
            if isinstance(e, ev.Takt):
                reihenfolge.append(name)
            return alt(z, e, j)

        t.step = step
        return t

    k = baue(monkeypatch, ("learn", mk("learn")), ("quiet", mk("quiet")))
    k.sende(ev.Takt())
    assert reihenfolge == ["learn", "quiet"]


# --------------------------------------------------------------------------
# Lautstärke (Abschnitt 8)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "delta, erwartet",
    [(+10, ev.LautstaerkeSetzen(50, 60)), (-15, ev.LautstaerkeSetzen(25, 60)), (+50, ev.LautstaerkeSetzen(60, 60)), (-100, ev.LautstaerkeSetzen(0, 60))],
)
def test_lautstaerke_drehen_wird_geklemmt(delta, erwartet):
    k = KernHarnisch()
    out = k.sende(ev.LautstaerkeDrehen(delta))
    assert [o for o in out if isinstance(o, ev.LautstaerkeSetzen)] == [erwartet]


def test_lautstaerke_drehen_ohne_aenderung_gibt_keinen_befehl():
    k = KernHarnisch()
    k.sende(ev.LautstaerkeDrehen(+50))  # 60 = Grenze
    out = k.sende(ev.LautstaerkeDrehen(+5))
    assert not any(isinstance(o, ev.LautstaerkeSetzen) for o in out)


def test_kopfhoerer_erst_grenze_dann_ausgang():
    k = KernHarnisch()
    rein = k.sende(ev.Kopfhoerer(True))
    assert ohne_meldung(rein) == [ev.LautstaerkeSetzen(25, 25), ev.AusgangWaehlen("kopfhoerer")]
    raus = k.sende(ev.Kopfhoerer(False))
    assert ohne_meldung(raus) == [ev.LautstaerkeSetzen(40, 60), ev.AusgangWaehlen("lautsprecher")]


def test_drehen_unter_kopfhoerer_grenze_klemmt_den_wunsch():
    """`wunsch := clamp(wunsch + delta, 0, wirksame Grenze)`: der Wunsch bleibt unter der Grenze."""
    k = KernHarnisch()
    k.sende(ev.Kopfhoerer(True))
    k.sende(ev.LautstaerkeDrehen(+20))
    assert k.z.wunsch == 25
    out = k.sende(ev.Kopfhoerer(False))
    assert [o for o in out if isinstance(o, ev.LautstaerkeSetzen)] == [ev.LautstaerkeSetzen(25, 60)]


def test_mehrere_grenzen_ein_befehl_mit_dem_minimum(monkeypatch):
    a = fake_teil(
        {
            ev.Takt: lambda e: [
                ev.GrenzeGesetzt("leise_zeit", 30),
                ev.GrenzeGesetzt("kopfhoerer", 20),
                ev.GrenzeGesetzt("ausblenden", 10),
            ]
        }
    )
    k = baue(monkeypatch, ("a", a))
    out = k.sende(ev.Takt())
    assert [o for o in out if isinstance(o, ev.LautstaerkeSetzen)] == [ev.LautstaerkeSetzen(10, 10)]


def test_ausblenden_bei_stumm_ohne_lautstaerkesprung():
    """Regel 7: am Ende des Ausblendens bleibt die Lautstärke in der Pause niedrig."""
    k = KernHarnisch()
    k.sende(ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1"))
    k.sende(ev.PlayerPosition("s1", "a.mp3", 10.0, True))
    k.sende(ev.StummBeginnt())
    gesetzt = []
    ende = None
    for _ in range(30):
        out = k.sende(ev.Takt(), dt=0.1)
        gesetzt += [o for o in out if isinstance(o, ev.LautstaerkeSetzen)]
        ende = out
    assert [g.prozent for g in gesetzt[:3]] == [39, 37, 36]
    assert gesetzt[-1].prozent <= 2
    assert [g.prozent for g in gesetzt] == sorted((g.prozent for g in gesetzt), reverse=True)
    # letzter Takt: Pause, Zeiger, aber kein Lautstärke-Rücksprung
    assert any(isinstance(o, ev.Pausieren) and o.grund == "stumm" for o in ende)
    assert not any(isinstance(o, ev.LautstaerkeSetzen) for o in ende)
    assert k.z.ausgegeben.prozent <= 2
    assert k.modus == "gehalten"
    # weitere Ereignisse setzen die Lautstärke nicht zurück
    assert not any(isinstance(o, ev.LautstaerkeSetzen) for o in k.sende(ev.Takt(), dt=0.1))
    # erst vor dem nächsten Abspielen (Regel 6) gilt der Wunsch wieder
    k.sende(ev.Abgehoben(1, "v1"))
    k.sende(ev.StummEndet())
    out = k.sende(ev.Aufgelegt(UID_S1, "ntag", False, 0, "v2"))
    assert out[0] == ev.LautstaerkeSetzen(40, 60)
    assert any(isinstance(o, ev.Abspielen) for o in out)


def test_regel7_pause_nach_gute_nacht_grenze_loeschen(monkeypatch):
    stufe = {"n": 0}

    def takt(e):
        stufe["n"] += 1
        if stufe["n"] == 1:
            return [ev.GrenzeGesetzt("gute_nacht", 10)]
        if stufe["n"] == 2:
            return [ev.GrenzeGesetzt("gute_nacht", None), ev.Pausieren("gute_nacht")]
        return []

    k = baue(monkeypatch, ("a", fake_teil({ev.Takt: takt})))
    assert ev.LautstaerkeSetzen(10, 10) in k.sende(ev.Takt())
    out = k.sende(ev.Takt())
    assert ev.Pausieren("gute_nacht") in out
    assert not any(isinstance(o, ev.LautstaerkeSetzen) for o in out)
    assert not any(isinstance(o, ev.LautstaerkeSetzen) for o in k.sende(ev.Takt()))
    # eine Änderung von `wunsch` setzt wieder
    out = k.sende(ev.LautstaerkeDrehen(+5))
    assert ev.LautstaerkeSetzen(45, 60) in out


def test_grenze_loeschen_ohne_pause_hebt_die_lautstaerke_sofort(monkeypatch):
    stufe = {"n": 0}

    def takt(e):
        stufe["n"] += 1
        return [ev.GrenzeGesetzt("gute_nacht", 10)] if stufe["n"] == 1 else [ev.GrenzeGesetzt("gute_nacht", None)]

    k = baue(monkeypatch, ("a", fake_teil({ev.Takt: takt})))
    k.sende(ev.Takt())
    assert ev.LautstaerkeSetzen(40, 60) in k.sende(ev.Takt())


# --------------------------------------------------------------------------
# Konflikt-Tabelle (6.2)
# --------------------------------------------------------------------------


def test_regel1_herunterfahren_hat_vorrang(monkeypatch):
    a = fake_teil(
        {
            ev.Takt: [
                ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v"),
                ev.SyncStarten("ha"),
                ev.UpdateStarten("b1", "1.2.3"),
                ev.AusgangWaehlen("kopfhoerer"),
                ev.TonSpielen("hinweis"),
                ev.Pausieren("herunterfahren"),
                ev.HerunterfahrenAngefordert("hauptknopf"),
            ]
        }
    )
    k = baue(monkeypatch, ("a", a))
    out = ohne_meldung(k.sende(ev.Takt()))
    assert out == [ev.Pausieren("herunterfahren"), ev.TonSpielen("hinweis"), ev.Herunterfahren("hauptknopf")]


@pytest.mark.parametrize("grund", ["leerlauf", "hauptknopf", "akku_tiefstand"])
def test_herunterfahren_ist_der_letzte_befehl(monkeypatch, grund):
    a = fake_teil({ev.Takt: [ev.HerunterfahrenAngefordert(grund), ev.SyncAbbrechen("akku_tiefstand")]})
    k = baue(monkeypatch, ("a", a))
    out = k.sende(ev.Takt())
    assert out[-1] == ev.Herunterfahren(grund)
    assert core._RANG[type(out[-1])] == 10


def test_herunterfahren_mit_laufender_wiedergabe_pausiert_zuerst(monkeypatch):
    k = baue(monkeypatch, ("a", fake_teil({ev.Hauptknopf: [ev.HerunterfahrenAngefordert("hauptknopf")]})))
    k.sende(ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1"))
    k.sende(ev.PlayerPosition("s1", "a.mp3", 10.0, True))
    out = ohne_meldung(k.sende(ev.Hauptknopf("lang")))
    assert out == [
        ev.Pausieren("herunterfahren"),
        ev.ZeigerSpeichern("s1", "a.mp3", 0, 10.0, "herunterfahren"),
        ev.Herunterfahren("hauptknopf"),
    ]


ALLE_TOENE = ["start", "unbekannt", "fehler", "hinweis", "lernen_beginn", "lernen_ende", "akku_leer", "pruef_ok", "pruef_fehler"]


@pytest.mark.parametrize(
    "ton, erwartet",
    [(t, "hinweis" if t in {"start", "unbekannt", "lernen_beginn", "lernen_ende", "fehler", "akku_leer"} else t) for t in ALLE_TOENE],
)
def test_regel2_toene_unter_stumm(monkeypatch, ton, erwartet):
    k = baue(monkeypatch, ("quiet", fake_teil({ev.Takt: [ev.TonSpielen(ton)]}, kennzeichen="stumm")))
    assert ohne_meldung(k.sende(ev.Takt())) == [ev.TonSpielen(erwartet)]


@pytest.mark.parametrize("ruhe", ["normal", "leiser"])
def test_regel2_toene_ohne_stumm_bleiben(monkeypatch, ruhe):
    k = baue(monkeypatch, ("quiet", fake_teil({ev.Takt: [ev.TonSpielen("lernen_ende")]}, kennzeichen=ruhe)))
    assert ohne_meldung(k.sende(ev.Takt())) == [ev.TonSpielen("lernen_ende")]


def test_regel3_stumm_und_lernmodus_ergeben_einen_hinweiston(monkeypatch):
    k = baue(
        monkeypatch,
        ("quiet", fake_teil({ev.Takt: [ev.TonSpielen("lernen_ende"), ev.TonSpielen("hinweis"), ev.TonSpielen("lernen_beginn")]}, kennzeichen="stumm")),
    )
    assert ohne_meldung(k.sende(ev.Takt())) == [ev.TonSpielen("hinweis")]


def test_regel3_gleiche_toene_werden_zu_einem_verschiedene_bleiben(monkeypatch):
    k = baue(monkeypatch, ("a", fake_teil({ev.Takt: [ev.TonSpielen("fehler"), ev.TonSpielen("pruef_ok"), ev.TonSpielen("fehler"), ev.TonSpielen("pruef_ok")]})))
    assert ohne_meldung(k.sende(ev.Takt())) == [ev.TonSpielen("fehler"), ev.TonSpielen("pruef_ok")]


@pytest.mark.parametrize(
    "eingabe, erwartet",
    [
        ([ev.Melden("unbekannt", "u1"), ev.Melden("gelernt", "u1", "b1")], [ev.Melden("gelernt", "u1", "b1")]),
        ([ev.Melden("gelernt", "u1", "b1"), ev.Melden("unbekannt", "u1")], [ev.Melden("gelernt", "u1", "b1")]),
        ([ev.Melden("unbekannt", "u1"), ev.Melden("unbekannt", "u1")], [ev.Melden("unbekannt", "u1")]),
        ([ev.Melden("unbekannt", "u1"), ev.Melden("unbekannt", "u2")], [ev.Melden("unbekannt", "u1"), ev.Melden("unbekannt", "u2")]),
    ],
    ids=["unbekannt-dann-gelernt", "gelernt-dann-unbekannt", "doppelt", "verschiedene-uid"],
)
def test_regel4_doppelte_meldungen(monkeypatch, eingabe, erwartet):
    k = baue(monkeypatch, ("a", fake_teil({ev.Takt: eingabe})))
    assert ohne_meldung(k.sende(ev.Takt())) == erwartet


def test_regel5_mehrere_abspielen_es_bleibt_das_letzte(monkeypatch):
    erstes = ev.Abspielen("s1", "s1", "a.mp3", 0.0, "v")
    letztes = ev.Abspielen("s2", "s2", "x.mp3", 0.0, "v")
    k = baue(monkeypatch, ("a", fake_teil({ev.Takt: [erstes, ev.TonSpielen("hinweis"), letztes]})))
    out = ohne_meldung(k.sende(ev.Takt()))
    assert out == [ev.LautstaerkeSetzen(40, 60), letztes, ev.TonSpielen("hinweis")]


def test_befehle_gleichen_rangs_behalten_die_emissionsreihenfolge(monkeypatch):
    eingabe = [
        ev.SyncStarten("ha"),
        ev.TonSpielen("fehler"),
        ev.Melden("unbekannt", "u1"),
        ev.ZeigerSpeichern("s1", "a.mp3", 0, 1.0, "pause"),
        ev.Pausieren("knopf"),
        ev.TonSpielen("hinweis"),
        ev.AusgangWaehlen("kopfhoerer"),
        ev.SyncAbbrechen("akku_tiefstand"),
        ev.LeserPing(),
        ev.Melden("unbekannt", "u2"),
    ]
    k = baue(monkeypatch, ("a", fake_teil({ev.Takt: eingabe})))
    out = ohne_meldung(k.sende(ev.Takt()))
    assert out == [
        ev.AusgangWaehlen("kopfhoerer"),
        ev.Pausieren("knopf"),
        ev.ZeigerSpeichern("s1", "a.mp3", 0, 1.0, "pause"),
        ev.TonSpielen("fehler"),
        ev.TonSpielen("hinweis"),
        ev.Melden("unbekannt", "u1"),
        ev.LeserPing(),
        ev.Melden("unbekannt", "u2"),
        ev.SyncAbbrechen("akku_tiefstand"),
        ev.SyncStarten("ha"),
    ]


def test_schutz_gegen_schleifen(monkeypatch):
    a = fake_teil({ev.Takt: [ev.LernenGeaendert(True)], ev.LernenGeaendert: [ev.LernenGeaendert(True)]})
    k = baue(monkeypatch, ("a", a))
    vorher = len(k.z.teil["a"])
    out = k.sende(ev.Takt())
    fehler = [o for o in out if isinstance(o, ev.Protokoll) and o.ebene == "ERROR" and o.ereignis == "kern_schleife"]
    assert len(fehler) == 1
    assert len(k.z.teil["a"]) - vorher == core.MAX_EREIGNISSE
    assert core.MAX_EREIGNISSE == 32


def test_kern_laeuft_nach_einer_schleife_normal_weiter(monkeypatch):
    schleife = {"an": True}

    def takt(e):
        return [ev.LernenGeaendert(True)] if schleife["an"] else []

    a = fake_teil({ev.Takt: takt, ev.LernenGeaendert: lambda e: [ev.LernenGeaendert(True)] if schleife["an"] else []})
    k = baue(monkeypatch, ("a", a))
    k.sende(ev.Takt())
    schleife["an"] = False
    out = k.sende(ev.Takt())
    assert not any(isinstance(o, ev.Protokoll) and o.ereignis == "kern_schleife" for o in out)


def test_abnahme_core_und_session_importieren_keine_io_module():
    import ast
    import inspect

    verboten = {"os", "socket", "serial", "time", "asyncio", "threading", "random", "pathlib", "logging", "subprocess", "datetime", "secrets", "json"}
    for modul in (core, session):
        baum = ast.parse(inspect.getsource(modul))
        namen = set()
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Import):
                namen |= {a.name.split(".")[0] for a in knoten.names}
            elif isinstance(knoten, ast.ImportFrom) and knoten.level == 0 and knoten.module:
                namen.add(knoten.module.split(".")[0])
        assert not namen & verboten, namen & verboten


def test_events_sind_unveraenderlich_und_ascii():
    e = ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1")
    with pytest.raises(Exception):
        e.uid = "x"  # type: ignore[misc]
    for name in dir(ev):
        t = getattr(ev, name)
        if isinstance(t, type) and issubclass(t, (ev.Ereignis, ev.InternesEreignis, ev.Befehl)):
            assert name.isascii()
            assert all(f.isascii() for f in getattr(t, "__dataclass_fields__", {}))
