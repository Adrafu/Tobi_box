"""Szenario-Werkzeug ``tools/gehoert_szenario.py`` (Stufe B, B5): deterministisch, vertragstreu, und die Box sendet die Daten."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fixtures.ha_fake import Aufbau, cmd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import gehoert_szenario as gs  # noqa: E402

from tobibox import gehoert as g  # noqa: E402
from tobibox.clock import SimUhr  # noqa: E402
from tobibox.gehoert_puffer import GehoertPuffer  # noqa: E402
from tobibox.ha import STATUS_MIN_ABSTAND_S  # noqa: E402

JETZT = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc).timestamp()
CMD, EVENT, STATUS = "tobibox/box1/cmd", "tobibox/box1/event", "tobibox/box1/status"


def lauf(szenarien, *, tage=40, seed=1, katalog=None):
    return gs.erzeuge(tage=tage, seed=seed, szenarien=szenarien, jetzt=JETZT, katalog=katalog)


def zeilen(e):
    return e.inhalt["zeilen"]


# --- Determinismus ---------------------------------------------------------------------------------------


def test_gleicher_seed_gleiche_daten_anderer_seed_andere():
    a, b, c = lauf(gs.SZENARIEN), lauf(gs.SZENARIEN), lauf(gs.SZENARIEN, seed=2)
    assert json.dumps(a.inhalt, sort_keys=True) == json.dumps(b.inhalt, sort_keys=True)
    assert json.dumps(a.inhalt, sort_keys=True) != json.dumps(c.inhalt, sort_keys=True)


# --- Vertrag (mqtt-v1 3.4, data-model 1.6) ---------------------------------------------------------------


@pytest.mark.parametrize("szenario", gs.SZENARIEN)
def test_jedes_szenario_erzeugt_nur_zeilen_die_den_vertrag_erfuellen(szenario):
    e = lauf((szenario,))
    assert e.inhalt["zeilen"], f"{szenario} erzeugt nichts"
    ids = set()
    for r in zeilen(e):
        assert g.pruefe_zeile(r) == r  # Pflichtfelder, Typen, Grenzen, ``ende`` nie ``teilweise``
        assert 1 <= r["gehoert_s"] <= r["ende_boot_s"] - r["beginn_boot_s"] + 2
        assert set(r) <= {"sitzung", "serie", "folge", "folge_dauer_s", "beginn", "zeit_ok", "boot_id", "beginn_boot_s", "ende_boot_s", "gehoert_s", "ende", "grund"}
        assert ("grund" in r) <= (r["ende"] == "pause")  # ``grund`` nur bei ``pause``
        ids.add(r["sitzung"])
    assert len(ids) == len(zeilen(e))
    assert e.inhalt["offen"] is None and len(zeilen(e)) <= g.MAX_ZEILEN


def test_die_datei_laedt_ohne_verworfene_zeilen():
    e = lauf(gs.VORGABE_SZENARIEN)
    geladen = g.parse_datei(json.loads(json.dumps(e.inhalt)))
    assert geladen.ungueltig == 0 and len(geladen.zeilen) == len(zeilen(e)) and geladen.offen is None


def test_alle_szenarien_zusammen_ueber_40_tage_sind_vertragstreu():
    e = lauf(gs.SZENARIEN)
    assert all(g.pruefe_zeile(r) == r for r in zeilen(e))


# --- Inhalt der Szenarien -----------------------------------------------------------------------------


def test_alltag_hat_viele_enden_und_mehrere_geraetestarts():
    e = lauf(("alltag",))
    enden = Counter(r["ende"] for r in zeilen(e))
    assert enden["ende_der_folge"] > 5 and enden["pause"] > 3 and enden["herunterfahren"] > 5 and enden["wechsel"] >= 1
    assert len({r["boot_id"] for r in zeilen(e)}) > 10
    assert all(r["zeit_ok"] for r in zeilen(e))
    tage = {r["beginn"][:10] for r in zeilen(e)}
    assert len(tage) >= 25  # über Wochen verteilt


def test_wiederholen_dieselbe_folge_mehrmals_bis_zum_ende():
    e = lauf(("wiederholen",))
    n = Counter((r["serie"], r["folge"]) for r in zeilen(e) if r["ende"] == "ende_der_folge")
    (schluessel, anzahl), = n.most_common(1)
    assert anzahl >= 9  # drei Abende mit 3 bis 5 Mal
    assert len(n) == 1
    assert all(r["gehoert_s"] >= 0.9 * r["folge_dauer_s"] for r in zeilen(e))


def test_hoerbuch_in_portionen_ueber_mehrere_tage_zaehlt_als_fertig():
    k = gs.standard_katalog()
    e = lauf(("hoerbuch",), katalog=k)
    hb = [r for r in zeilen(e) if r["serie"] == k.hoerbuch.serie]
    assert len(hb) >= 5
    assert len({r["beginn"][:10] for r in hb}) == len(hb)  # jeder Abend eine Portion
    assert sum(1 for r in hb if r["ende"] == "ende_der_folge") == 1 and hb[-1]["ende"] == "ende_der_folge"
    assert sum(r["gehoert_s"] for r in hb) >= 0.8 * k.hoerbuch.dauer_s  # Zählregel „fertig“: 80 % über die Portionen
    assert all(r["gehoert_s"] < 0.8 * k.hoerbuch.dauer_s for r in hb[:-1])


def test_neustart_dienst_ende_und_absturz_als_abbruch():
    e = lauf(("neustart",))
    enden = Counter(r["ende"] for r in zeilen(e))
    assert enden["dienst_ende"] == 1 and enden["abbruch"] == 1
    ab = next(r for r in zeilen(e) if r["ende"] == "abbruch")
    assert ab["gehoert_s"] >= 1


def test_strom_weg_abbruch_bei_neuem_geraetestart_und_verlust_bis_zwei_minuten():
    e = lauf(("strom_weg",))
    z = zeilen(e)
    i = next(i for i, r in enumerate(z) if r["ende"] == "abbruch")
    assert z[i + 1]["boot_id"] != z[i]["boot_id"]  # danach ein neuer Gerätestart
    assert z[i]["gehoert_s"] >= 60  # nicht alles verloren (Schreiben alle 2 Minuten)


def test_ueberlauf_mehr_als_500_die_aeltesten_fallen_weg_und_verworfen_zaehlt():
    e = lauf(("alltag", "ueberlauf"))
    assert len(zeilen(e)) == g.MAX_ZEILEN and e.inhalt["verworfen"] > 0
    assert Counter(r["ende"] for r in zeilen(e))["wechsel"] > 300


def test_offline_viele_geraetestarts_in_den_letzten_tagen():
    e = lauf(("offline",))
    assert len({r["boot_id"] for r in zeilen(e)}) >= 8
    assert all(r["ende"] in ("herunterfahren", "pause", "ende_der_folge", "wechsel") for r in zeilen(e))


def test_uhr_nie_gut_unsichere_zeilen_und_eine_spaet_korrigierte():
    e = lauf(("uhr_nie_gut",))
    schlecht = [r for r in zeilen(e) if not r["zeit_ok"]]
    gut = [r for r in zeilen(e) if r["zeit_ok"]]
    assert len(schlecht) >= 4 and gut  # die späte Korrektur macht Zeilen des Starts gut (Datum aus der Monotonuhr)
    assert all(r["beginn"].startswith("2024-") for r in schlecht)  # alter Stand der Uhr, kein echtes Datum
    korrigiert = [r for r in gut if r["beginn"][:4] == "2026"]
    assert len(korrigiert) >= 1


def test_kurze_zeitraeume_und_ungueltige_eingaben():
    e = lauf(gs.SZENARIEN, tage=1)
    assert all(g.pruefe_zeile(r) == r for r in zeilen(e))
    with pytest.raises(gs.SzenarioFehler):
        lauf(("gibt-es-nicht",))
    with pytest.raises(gs.SzenarioFehler):
        gs.erzeuge(tage=0, seed=1, jetzt=JETZT)


def test_medienordner_liefert_die_serien_der_test_box(tmp_path):
    (tmp_path / "serie-a").mkdir()
    (tmp_path / "serie-b").mkdir()
    (tmp_path / "ueberraschung").mkdir()
    for n in ("serie-a", "serie-b"):
        for f in ("folge-01.mp3", "folge-02.mp3"):
            (tmp_path / n / f).write_bytes(b"\x00")
    k = gs.lade_katalog(tmp_path)
    assert k.quelle.startswith("Medienordner")  # nicht der Ersatzkatalog
    assert sorted(k.serien) == ["serie-a", "serie-b"] or len(k.serien) == 1  # ein Ordner wird zum Hörbuch (längste Folge)
    assert all(f.dauer_s >= 300 for f in k.alle)  # unbekannte oder kurze Dauern werden virtuell verlängert
    e = lauf(("alltag",), katalog=k, tage=10)
    assert {r["serie"] for r in zeilen(e)} <= set(k.serien)


# --- Kommandozeile -------------------------------------------------------------------------------------


def argv(tmp_path, *extra):
    return ["--zustand", str(tmp_path / "z"), "--tage", "20", "--seed", "3", "--jetzt", "2026-11-17T12:00:00Z", *extra]


def test_trocken_schreibt_nichts(tmp_path, capsys):
    assert gs.main(argv(tmp_path, "--trocken")) == 0
    out = capsys.readouterr().out
    assert "Zeilen im Puffer" in out and "nichts geschrieben" in out
    assert not (tmp_path / "z").exists()


def test_schreibt_die_datei_und_schuetzt_vorhandene_daten(tmp_path, capsys):
    assert gs.main(argv(tmp_path)) == 0
    datei = tmp_path / "z" / "gehoert.json"
    erste = datei.read_text(encoding="utf-8")
    assert g.parse_datei(json.loads(erste)).zeilen
    assert gs.main(argv(tmp_path)) == 2  # enthält schon Daten
    assert "--ueberschreiben" in capsys.readouterr().err
    assert datei.read_text(encoding="utf-8") == erste
    assert gs.main(argv(tmp_path, "--ueberschreiben")) == 0
    assert datei.read_text(encoding="utf-8") == erste  # gleicher Seed, gleiche Datei


def test_ohne_ziel_ist_ein_fehler(capsys):
    assert gs.main(["--tage", "3"]) == 2
    assert "--konfig" in capsys.readouterr().err


def test_konfig_liefert_zustandsordner_und_medien_ohne_passwort(tmp_path):
    k = tmp_path / "cfg" / "boxsim.toml"
    k.parent.mkdir()
    k.write_text('[pfade]\nzustand = "../var/boxsim"\nmedien = "../medien"\n[mqtt]\nbox_id = "boxsim"\nhost = "x"\npasswort_umgebung = "NICHT_GESETZT_B5"\n', encoding="utf-8")
    z, m = gs.lies_pfade(k)
    assert z == tmp_path / "cfg" / ".." / "var" / "boxsim" and m == tmp_path / "cfg" / ".." / "medien"


def test_laufende_test_box_wird_erkannt(tmp_path, kurz):
    import socket
    assert not gs.box_laeuft(kurz)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(str(kurz / "sim.sock"))
    s.listen(1)
    try:
        assert gs.box_laeuft(kurz)
    finally:
        s.close()


# --- End zu Ende: die echte Box sendet die erzeugten Zeilen und löscht sie nach der Quittung ---------------


def gespielt(a: Aufbau) -> list[dict]:
    return [e for e in a.klient.json_auf(EVENT) if e["art"] == "gespielt"]


async def box_mit_datei(tmp_path, szenarien, **kw):
    """Szenario in den Zustandsordner schreiben, dann eine Box (``GehoertPuffer.laden`` wie beim Start) mit ``ha``."""
    verz = tmp_path / "z"
    e = lauf(szenarien, **kw)
    gs.schreibe_atomar(verz / "gehoert.json", e.inhalt)
    uhr = SimUhr(mono=3000.0, wall=JETZT)
    puffer = GehoertPuffer(verz, boot_id=lambda: "box-start-1")
    puffer.laden(uhr.jetzt())
    a = Aufbau(verz, gehoert=puffer, uhr=uhr)
    await a.start(True)
    return a, puffer, e


async def handshake_und_alles_senden(a: Aufbau, quittiert=()) -> list[dict]:
    a.klient.eingang(CMD, cmd("gehoert_quittung", daten={"sitzungen": list(quittiert)}))
    await a.ha.leere()
    for _ in range(40):  # ein Tick je Sekunde, höchstens 20 Nachrichten je Tick
        a.uhr.vor(STATUS_MIN_ABSTAND_S)
        a.ha.tick()
    return gespielt(a)


async def test_box_sendet_alle_zeilen_in_paeckchen_und_loescht_sie_nach_der_quittung(tmp_path):
    a, puffer, e = await box_mit_datei(tmp_path, gs.VORGABE_SZENARIEN)
    soll = [r["sitzung"] for r in zeilen(e)]
    assert [r["sitzung"] for r in puffer.zeilen] == soll  # der Start verwirft nichts
    assert gespielt(a) == []  # vor dem Handshake nichts
    nachrichten = await handshake_und_alles_senden(a)
    assert nachrichten and all(1 <= len(n["daten"]["sitzungen"]) <= 20 for n in nachrichten)
    gesendet = [s for n in nachrichten for s in n["daten"]["sitzungen"]]
    assert [s["sitzung"] for s in gesendet[: len(soll)]] == soll  # die erste Sendung enthält alle, in Reihenfolge
    assert gesendet[: len(soll)] == zeilen(e)  # genau die erzeugten Zeilen
    assert all(g.pruefe_zeile(s) == s for s in gesendet)  # und sie erfüllen den Vertrag auch nach dem Weg über ``ha``
    for i in range(0, len(soll), 100):  # HA quittiert die UUIDs (höchstens 100 je Befehl)
        a.klient.eingang(CMD, cmd("gehoert_quittung", daten={"sitzungen": soll[i : i + 100]}))
        await a.ha.leere()
    assert puffer.zeilen == ()
    n = len(gespielt(a))
    a.uhr.vor(700)
    a.ha.tick()
    assert len(gespielt(a)) == n  # nichts wird noch einmal gesendet
    await a.stop()


async def test_ueberlauf_erscheint_im_status_als_verworfen(tmp_path):
    a, puffer, e = await box_mit_datei(tmp_path, ("alltag", "ueberlauf"))
    assert e.inhalt["verworfen"] > 0 and len(puffer.zeilen) == g.MAX_ZEILEN
    a.uhr.vor(STATUS_MIN_ABSTAND_S)
    a.ha.tick()
    s = a.klient.json_auf(STATUS)[-1]
    assert s["gehoert_verworfen"] == e.inhalt["verworfen"] and s["gehoert_wartet"] is True
    await a.stop()


async def test_teilquittung_laesst_den_rest_im_puffer(tmp_path):
    a, puffer, e = await box_mit_datei(tmp_path, ("alltag",), tage=10)
    soll = [r["sitzung"] for r in zeilen(e)]
    await handshake_und_alles_senden(a, soll[:3])  # HA kannte drei schon
    assert [r["sitzung"] for r in puffer.zeilen] == soll[3:]
    await a.stop()


# --- --serien: Serien und echte Dauern aus einer Datei ---------------------------------------------------

SERIEN_DATEI = Path(__file__).resolve().parents[1] / "fixtures" / "serien_beispiel.json"


def test_serien_datei_echte_dauern_deterministische_auswahl_und_hoerbuch_ist_die_laengste_folge():
    k = gs.lade_serien_datei(SERIEN_DATEI, anzahl=3, seed=5)
    assert k == gs.lade_serien_datei(SERIEN_DATEI, anzahl=3, seed=5)
    assert len(k.serien) <= 3
    echt = {(s["serie_id"], f["name"]): f["dauer_s"] for s in json.loads(SERIEN_DATEI.read_text()) for f in s["folgen"]}
    assert all(echt[f.schluessel] == f.dauer_s == f.echt_s for f in k.alle + [k.hoerbuch])  # keine virtuelle Dauer
    waehlbar = [echt[(f.serie, f.folge)] for f in k.alle + [k.hoerbuch]]
    assert k.hoerbuch.dauer_s == max(waehlbar)
    a = gs.lade_serien_datei(SERIEN_DATEI, anzahl=2, seed=1)
    assert any(gs.lade_serien_datei(SERIEN_DATEI, anzahl=2, seed=s).serien.keys() != a.serien.keys() for s in range(2, 12))


def test_zeilen_mit_serien_datei_tragen_die_echten_namen_und_dauern():
    k = gs.lade_serien_datei(SERIEN_DATEI, anzahl=12, seed=1)
    e = lauf(gs.VORGABE_SZENARIEN, katalog=k)
    echt = {(s["serie_id"], f["name"]): f["dauer_s"] for s in json.loads(SERIEN_DATEI.read_text()) for f in s["folgen"]}
    assert zeilen(e) and all(g.pruefe_zeile(r) == r for r in zeilen(e))
    assert all(echt[(r["serie"], r["folge"])] == r["folge_dauer_s"] for r in zeilen(e))
    hb = [r for r in zeilen(e) if (r["serie"], r["folge"]) == k.hoerbuch.schluessel]
    assert len(hb) >= 5 and hb[-1]["ende"] == "ende_der_folge"


def test_serien_datei_fehler_und_kommandozeile(tmp_path, capsys):
    kaputt = tmp_path / "k.json"
    kaputt.write_text('[{"serie_id": "x", "folgen": [{"name": "a", "dauer_s": 0}]}]', encoding="utf-8")
    with pytest.raises(gs.SzenarioFehler):
        gs.lade_serien_datei(kaputt, anzahl=3, seed=1)
    assert gs.main(["--trocken", "--tage", "20", "--seed", "2", "--jetzt", "2026-11-17T12:00:00Z", "--serien", str(SERIEN_DATEI), "--anzahl-serien", "2"]) == 0
    assert "Serien-Datei serien_beispiel.json" in capsys.readouterr().out
    assert gs.main(["--trocken", "--serien", str(kaputt)]) == 2
