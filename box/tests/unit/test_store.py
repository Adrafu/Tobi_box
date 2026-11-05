"""Atomares Schreiben, ``.bak``-Rückfall, beschädigte Dateien, ``resume.json``, ``config.json``."""

from __future__ import annotations

import json
import logging
import os

import pytest
from conftest import KernHarnisch, UID_S1

from tobibox import events as ev
from tobibox import eventlog, store
from tobibox.store import KonfigStore, ResumeStore, lade_zustandsdatei, schreibe_atomar


@pytest.fixture
def protokoll():
    """Sammelt Protokollzeilen (``ereignis``) des Loggers ``tobibox``."""
    zeilen: list[logging.LogRecord] = []

    class H(logging.Handler):
        def emit(self, record):
            zeilen.append(record)

    log = logging.getLogger("tobibox")
    h = H()
    alt, alt_level = log.handlers[:], log.level
    log.handlers = [h]
    log.setLevel(logging.DEBUG)
    yield zeilen
    log.handlers = alt
    log.setLevel(alt_level)


def ereignisse(zeilen):
    return [z.ereignis for z in zeilen]


def zeiger_befehl(datei="a.mp3", index=0, pos=10.0, grund="pause", serie="s1"):
    return ev.ZeigerSpeichern(serie, datei, index, pos, grund)


# --- schreibe_atomar -----------------------------------------------------------


def test_schreibt_format_nach_datenmodell(tmp_path):
    p = tmp_path / "x.json"
    schreibe_atomar(p, {"b": 1, "schema_version": 1, "a": "ä"})
    text = p.read_bytes().decode("utf-8")
    assert text.endswith("}\n") and not text.startswith("﻿")
    assert text.splitlines()[1].startswith('  "schema_version"')  # erstes Feld, 2 Leerzeichen
    assert json.loads(text) == {"schema_version": 1, "b": 1, "a": "ä"}
    assert "ä" in text  # nicht als \u-Escape


def test_erste_schreibung_ohne_bak_zweite_mit_bak(tmp_path):
    p = tmp_path / "x.json"
    schreibe_atomar(p, {"v": 1})
    assert not (tmp_path / "x.json.bak").exists()
    schreibe_atomar(p, {"v": 2})
    assert json.loads((tmp_path / "x.json.bak").read_text())["v"] == 1
    assert json.loads(p.read_text())["v"] == 2


def test_keine_reste_nach_erfolgreichem_schreiben(tmp_path):
    p = tmp_path / "x.json"
    for i in range(3):
        schreibe_atomar(p, {"v": i})
    assert sorted(f.name for f in tmp_path.iterdir()) == ["x.json", "x.json.bak"]


def test_beschaedigte_datei_wird_nicht_zur_sicherung(tmp_path):
    p = tmp_path / "x.json"
    schreibe_atomar(p, {"v": 1})
    schreibe_atomar(p, {"v": 2})
    p.write_text("{kaputt")
    schreibe_atomar(p, {"v": 3})
    assert json.loads((tmp_path / "x.json.bak").read_text())["v"] == 1  # nicht der Müll


def test_fehler_beim_schreiben_laesst_alte_datei_und_raeumt_tmp(tmp_path, monkeypatch):
    p = tmp_path / "x.json"
    schreibe_atomar(p, {"v": 1})

    def kaputt(*a, **k):
        raise OSError("platte voll")

    monkeypatch.setattr(os, "fsync", kaputt)
    with pytest.raises(OSError):
        schreibe_atomar(p, {"v": 2})
    monkeypatch.undo()
    assert json.loads(p.read_text())["v"] == 1
    assert not (tmp_path / "x.json.tmp").exists()


def test_raeume_auf_loescht_tmp_und_bak_tmp(tmp_path):
    for n in ("a.json.tmp", "a.json.bak.tmp", "a.json", "a.json.bak"):
        (tmp_path / n).write_text("{}")
    assert store.raeume_auf(tmp_path) == 2
    assert sorted(f.name for f in tmp_path.iterdir()) == ["a.json", "a.json.bak"]


# --- Lesen und Rückfall (data-model 1.3) ---------------------------------------


def lade_resume(p):
    return lade_zustandsdatei(p, store.parse_resume, dict, store.resume_zu_json)


def test_fehlende_datei_ist_kein_fehler(tmp_path, protokoll):
    wert, quelle = lade_resume(tmp_path / "resume.json")
    assert (wert, quelle) == ({}, "neu")
    assert protokoll == []


def test_beschaedigte_datei_rueckfall_auf_bak(tmp_path, protokoll):
    p = tmp_path / "resume.json"
    s = ResumeStore(tmp_path)
    s.speichern(zeiger_befehl(pos=10.0), 0)
    s.speichern(zeiger_befehl(pos=20.0), 1)
    p.write_text('{"schema_version": 1, "serien": {')  # abgeschnitten
    wert, quelle = lade_resume(p)
    assert quelle == "bak"
    assert wert["s1"].position_s == 10.0
    assert (tmp_path / "resume.json.defekt").exists()
    assert json.loads(p.read_text())["serien"]["s1"]["position_s"] == 10.0  # zurückgeschrieben
    assert "datei_defekt" in ereignisse(protokoll)
    assert "datei_verloren" not in ereignisse(protokoll)


def test_beides_defekt_standardwerte_und_datei_verloren(tmp_path, protokoll):
    (tmp_path / "resume.json").write_text("müll")
    (tmp_path / "resume.json.bak").write_text("auch müll")
    wert, quelle = lade_resume(tmp_path / "resume.json")
    assert (wert, quelle) == ({}, "standard")
    assert ereignisse(protokoll) == ["datei_defekt", "datei_verloren"]
    assert all(z.levelname == "ERROR" for z in protokoll)


def test_defekt_ohne_bak_standardwerte(tmp_path, protokoll):
    (tmp_path / "resume.json").write_text("[]")
    assert lade_resume(tmp_path / "resume.json")[1] == "standard"


def test_aeltere_defekt_datei_wird_ueberschrieben(tmp_path):
    (tmp_path / "resume.json.defekt").write_text("alt")
    (tmp_path / "resume.json").write_text("neu kaputt")
    lade_resume(tmp_path / "resume.json")
    assert (tmp_path / "resume.json.defekt").read_text() == "neu kaputt"


def test_schema_zu_neu_gilt_als_ungueltig(tmp_path, protokoll):
    (tmp_path / "resume.json").write_text(json.dumps({"schema_version": 2, "serien": {}}))
    wert, quelle = lade_resume(tmp_path / "resume.json")
    assert quelle == "standard"
    assert "schema_zu_neu" in ereignisse(protokoll)


@pytest.mark.parametrize(
    "serien",
    [
        {"s": {"folge": "a", "index": -1, "position_s": 0, "zaehler": 1}},
        {"s": {"folge": "a", "index": 0, "position_s": -1, "zaehler": 1}},
        {"s": {"folge": "a", "index": 0, "position_s": 0, "zaehler": 0}},
        {"s": {"folge": "", "index": 0, "position_s": 0, "zaehler": 1}},
        {"s": {"folge": "a", "index": 0, "position_s": 0}},
        {"s": "x"},
    ],
)
def test_ungueltige_eintraege_machen_die_datei_ungueltig(serien):
    with pytest.raises(store.Ungueltig):
        store.parse_resume({"serien": serien})


def test_unbekannte_felder_werden_ignoriert(tmp_path):
    p = tmp_path / "resume.json"
    p.write_text(json.dumps({"schema_version": 1, "neu": 1,
                             "serien": {"s": {"folge": "a", "index": 0, "position_s": 1.5, "zaehler": 2, "x": 1}}}))
    wert, quelle = lade_resume(p)
    assert quelle == "datei" and wert["s"].position_s == 1.5


# --- ResumeStore ----------------------------------------------------------------


def test_resume_laden_leer(tmp_path):
    e = ResumeStore(tmp_path).laden()
    assert e == ev.ResumeGeladen(())


def test_resume_speichern_und_neu_laden(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    assert s.speichern(zeiger_befehl("b.mp3", 1, 412.56), 0)
    geladen = ResumeStore(tmp_path).laden()
    assert geladen.zeiger == (ev.Zeiger("s1", "b.mp3", 1, 412.5, 1),)


def test_zaehler_steigt_je_schreibung(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    for i, pos in enumerate((1.0, 2.0, 3.0), start=1):
        s.speichern(zeiger_befehl(pos=pos), i * 100)
        assert s.zeiger["s1"].zaehler == i


def test_unveraenderter_zeiger_wird_nicht_geschrieben(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    assert s.speichern(zeiger_befehl(pos=10.04), 0)
    assert not s.speichern(zeiger_befehl(pos=10.09), 1)  # gleiche abgerundete Position
    assert s.schreibungen == 1
    assert s.speichern(zeiger_befehl(pos=10.1), 2)
    assert s.schreibungen == 2


def test_speicher_drosselt_nicht_selbst_geaendert_wird_immer_geschrieben(tmp_path):
    """Die 30-s-Drosselung entscheidet allein die Sitzung; der Speicher schreibt jeden geänderten Zeiger."""
    s = ResumeStore(tmp_path)
    s.laden()
    assert s.speichern(zeiger_befehl(pos=1.0, grund="periodisch"), 100.0)
    assert s.speichern(zeiger_befehl(pos=20.0, grund="periodisch"), 100.1)
    assert not s.speichern(zeiger_befehl(pos=20.0, grund="periodisch"), 200.0)  # unverändert
    assert s.schreibungen == 2


def test_andere_gruende_speichern_sofort(tmp_path):
    s = ResumeStore(tmp_path)
    s.laden()
    s.speichern(zeiger_befehl(pos=1.0, grund="periodisch"), 100.0)
    assert s.speichern(zeiger_befehl(pos=2.0, grund="pause"), 100.5)
    assert s.speichern(zeiger_befehl(pos=3.0, grund="folgenende"), 100.6)


def test_zeigerschreibung_hoechstens_alle_30_s_ueber_2_stunden_wiedergabe(tmp_path):
    """Schreibbudget (data-model 1.7): 2 h Wiedergabe schreiben höchstens 240 + Rand."""
    h = KernHarnisch()
    s = ResumeStore(tmp_path)
    s.laden()
    from conftest import mk_konfig

    h.sende(ev.KonfigGeladen(mk_konfig()))
    h.sende(ev.ResumeGeladen(()))
    h.sende(ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1"))
    zeiten = []
    pos = 0.0
    for sek in range(7200):
        pos += 1.0
        h.sende(ev.PlayerPosition("s1", "a.mp3", pos, True), dt=1.0)
        for _ in range(10):  # Takt alle 0,1 s: Uhr nicht weiter vorstellen
            out = h.sende(ev.Takt())
            for b in out:
                if isinstance(b, ev.ZeigerSpeichern) and s.speichern(b, h.uhr.mono):
                    zeiten.append(h.uhr.mono)
    assert 230 <= len(zeiten) <= 241
    assert all(b - a >= 30 - 1e-6 for a, b in zip(zeiten, zeiten[1:]))


def test_kern_resume_ende_zu_ende(tmp_path):
    """Zeiger geladen -> Auflegen spielt ab Zeiger minus 3 s -> Pause schreibt -> Neustart liest."""
    from conftest import mk_konfig

    s = ResumeStore(tmp_path)
    s.laden()
    s.speichern(ev.ZeigerSpeichern("s1", "b.mp3", 1, 100.0, "pause"), 0)

    h = KernHarnisch(start=True)
    h.sende(ev.KonfigGeladen(mk_konfig()))
    h.sende(ev.ResumeGeladen(tuple(ResumeStore(tmp_path).laden().zeiger)))
    out = h.sende(ev.Aufgelegt(UID_S1, "ntag", False, 0, "v1"))
    ab = [b for b in out if isinstance(b, ev.Abspielen)]
    assert [(a.datei, a.position_s) for a in ab] == [("b.mp3", 97.0)]
    h.sende(ev.PlayerPosition("s1", "b.mp3", 130.0, True), dt=1.0)
    out = h.sende(ev.Hauptknopf("kurz"), dt=1.0)
    sp = [b for b in out if isinstance(b, ev.ZeigerSpeichern)]
    assert len(sp) == 1 and s.speichern(sp[0], h.uhr.mono)
    assert ResumeStore(tmp_path).laden().zeiger[0].position_s == 130.0


# --- config.json ----------------------------------------------------------------


def gute_konfig(**kw):
    d = {
        "schema_version": 1,
        "revision": 17,
        "liste_id": "a3f9c1e07b2d4856",
        "erzeugt_am": "2026-11-05T09:30:00Z",
        "zuordnungen": {
            "e0040312345678ab": {"typ": "serie", "serie": "3f9a1c07b2d4"},
            "04ffeedd": {"typ": "aktion", "aktion": "status"},
        },
        "leise_zeiten": {
            "zeitzone": "Europe/Berlin",
            "fenster": [
                {"id": "abend", "tage": [1, 2, 3], "von": "19:30", "bis": "21:00", "wirkung": "leiser", "grenze": 25},
                {"id": "nacht", "tage": [1, 2], "von": "21:00", "bis": "06:30", "wirkung": "stumm"},
            ],
        },
        "gute_nacht": {"timer_min": 30, "ausblenden_s": 60},
        "ton_pegel": 40,
    }
    d.update(kw)
    return d


def test_konfig_beispiel_aus_dem_datenmodell_ist_gueltig():
    k = store.parse_konfig(gute_konfig())
    assert k.revision == 17 and k.liste_id == "a3f9c1e07b2d4856"
    assert k.zuordnungen["04ffeedd"] == ev.Zuordnung("aktion", None, "status")
    assert k.zuordnungen["e0040312345678ab"] == ev.Zuordnung("serie", "3f9a1c07b2d4", None)
    assert k.leise_zeiten.fenster[1].grenze is None
    assert k.gute_nacht == ev.GuteNacht(30, 60)


def test_konfig_zeitzone_vorgabe():
    d = gute_konfig()
    del d["leise_zeiten"]["zeitzone"]
    assert store.parse_konfig(d).leise_zeiten.zeitzone == "Europe/Berlin"


def mutiere(f):
    d = gute_konfig()
    f(d)
    return d


@pytest.mark.parametrize(
    "aenderung",
    [
        lambda d: d.update(revision=0),
        lambda d: d.update(liste_id="XYZ"),
        lambda d: d["zuordnungen"].update({"04FFEEDD": {"typ": "aktion", "aktion": "status"}}),
        lambda d: d["zuordnungen"].update({"04aa0011": {"typ": "foo"}}),
        lambda d: d["zuordnungen"].update({"04aa0011": {"typ": "aktion", "aktion": "weg"}}),
        lambda d: d["leise_zeiten"].update(zeitzone="Mars/Olympus"),
        lambda d: d["leise_zeiten"]["fenster"][0].update(id="abend") or d["leise_zeiten"]["fenster"][1].update(id="abend"),
        lambda d: d["leise_zeiten"]["fenster"][0].update(von="21:00", bis="21:00"),
        lambda d: d["leise_zeiten"]["fenster"][0].update(tage=[]),
        lambda d: d["leise_zeiten"]["fenster"][0].update(tage=[1, 1]),
        lambda d: d["leise_zeiten"]["fenster"][0].update(tage=[0]),
        lambda d: d["leise_zeiten"]["fenster"][0].update(von="25:00"),
        lambda d: d["leise_zeiten"]["fenster"][0].pop("grenze"),
        lambda d: d["leise_zeiten"]["fenster"][0].update(grenze=101),
        lambda d: d["leise_zeiten"]["fenster"][0].update(wirkung="laut"),
        lambda d: d["gute_nacht"].update(timer_min=0),
        lambda d: d["gute_nacht"].update(timer_min=241),
        lambda d: d["gute_nacht"].update(ausblenden_s=4),
        lambda d: d.update(ton_pegel=101),
        lambda d: d.pop("gute_nacht"),
    ],
)
def test_ungueltige_konfig_wird_ganz_abgelehnt(aenderung):
    with pytest.raises(store.Ungueltig):
        store.parse_konfig(mutiere(aenderung))


def test_konfig_laden_ohne_datei_ist_revision_0(tmp_path):
    e = KonfigStore(tmp_path).laden()
    assert e.konfig.revision == 0 and e.konfig.liste_id == "" and not e.konfig.zuordnungen


def test_konfig_annehmen_neue_liste_gleiche_und_niedrigere_revision(tmp_path, protokoll):
    s = KonfigStore(tmp_path)
    s.laden()
    assert s.annehmen(gute_konfig()) == store.Annahme(True, "ok")
    assert s.annehmen(gute_konfig()) == store.Annahme(False, "gleich")
    assert s.annehmen(gute_konfig(revision=16)) == store.Annahme(False, "revision_zu_niedrig")
    assert s.annehmen(gute_konfig(revision=18)).angenommen
    assert s.annehmen(gute_konfig(revision=1, liste_id="0000000000000000")).angenommen  # neue Liste
    assert s.konfig.liste_id == "0000000000000000"


def test_konfig_ungueltig_behaelt_bisherige(tmp_path):
    s = KonfigStore(tmp_path)
    s.laden()
    s.annehmen(gute_konfig())
    assert s.annehmen(gute_konfig(revision=99, gute_nacht={"timer_min": 0, "ausblenden_s": 60})) == store.Annahme(
        False, "schema_ungueltig"
    )
    assert KonfigStore(tmp_path).laden().konfig.revision == 17


def test_konfig_behaelt_ton_pegel_beim_schreiben(tmp_path):
    s = KonfigStore(tmp_path)
    s.laden()
    s.annehmen(gute_konfig())
    assert json.loads((tmp_path / "config.json").read_text())["ton_pegel"] == 40
    assert "unbekannt" not in json.loads((tmp_path / "config.json").read_text())


def test_konfig_bak_rueckfall_behaelt_ton_pegel(tmp_path):
    s = KonfigStore(tmp_path)
    s.laden()
    s.annehmen(gute_konfig(revision=1))
    s.annehmen(gute_konfig(revision=2))
    (tmp_path / "config.json").write_text("kaputt")
    s2 = KonfigStore(tmp_path)
    assert s2.laden().konfig.revision == 1
    assert s2.quelle == "bak"
    assert json.loads((tmp_path / "config.json").read_text())["ton_pegel"] == 40


# --- Rückfall bei fehlender Datei, Reihenfolge, Verzeichnis-fsync ---------------


def test_fehlende_datei_mit_gueltiger_bak_nimmt_die_bak(tmp_path, protokoll):
    s = ResumeStore(tmp_path)
    s.speichern(zeiger_befehl(pos=10.0), 0)
    s.speichern(zeiger_befehl(pos=20.0), 1)
    (tmp_path / "resume.json").unlink()  # .bak hat 10.0
    wert, quelle = lade_resume(tmp_path / "resume.json")
    assert quelle == "bak" and wert["s1"].position_s == 10.0
    assert "datei_aus_bak" in ereignisse(protokoll)
    assert "datei_verloren" not in ereignisse(protokoll)
    assert json.loads((tmp_path / "resume.json").read_text())["serien"]["s1"]["position_s"] == 10.0  # zurückgeschrieben


def test_nur_ohne_beide_dateien_ist_es_ein_erster_start(tmp_path, protokoll):
    (tmp_path / "resume.json.bak").write_text("müll")
    wert, quelle = lade_resume(tmp_path / "resume.json")
    assert (wert, quelle) == ({}, "standard")  # .bak da, aber unbrauchbar: Verlust, kein erster Start
    assert "datei_verloren" in ereignisse(protokoll)
    assert lade_resume(tmp_path / "gibtsnicht.json")[1] == "neu"


def test_defekte_datei_bak_wird_vor_dem_umbenennen_gelesen_und_verzeichnis_fsynct(tmp_path, monkeypatch):
    s = ResumeStore(tmp_path)
    s.speichern(zeiger_befehl(pos=10.0), 0)
    s.speichern(zeiger_befehl(pos=20.0), 1)
    p = tmp_path / "resume.json"
    p.write_text("{kaputt")
    ablauf = []
    echt_replace, echt_fsync = os.replace, os.fsync
    echt_lese = store.lese_pruefe

    def lese(pfad, pruefe):
        ablauf.append(("lese", pfad.name))
        return echt_lese(pfad, pruefe)

    def replace(a, b):
        ablauf.append(("replace", os.path.basename(b)))
        return echt_replace(a, b)

    def fsync(fd):
        import stat

        ablauf.append(("fsync", "dir" if stat.S_ISDIR(os.fstat(fd).st_mode) else "datei"))
        return echt_fsync(fd)

    monkeypatch.setattr(store, "lese_pruefe", lese)
    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(os, "fsync", fsync)
    wert, quelle = lade_resume(p)
    assert quelle == "bak"
    assert ablauf.index(("lese", "resume.json.bak")) < ablauf.index(("replace", "resume.json.defekt"))
    assert ablauf[ablauf.index(("replace", "resume.json.defekt")) + 1] == ("fsync", "dir")
    assert (tmp_path / "resume.json.defekt").read_text() == "{kaputt"


# --- Gültigkeit: schema_version, NaN/inf ------------------------------------------


@pytest.mark.parametrize("version", [[1], {"a": 1}, "1", 1.0, True, None])
def test_annehmen_mit_unhashbarer_oder_falscher_schema_version_wirft_nicht(tmp_path, version):
    k = KonfigStore(tmp_path)
    k.laden()
    roh = dict(k.roh)
    roh["schema_version"] = version
    assert k.annehmen(roh) == store.Annahme(False, "schema_ungueltig")


@pytest.mark.parametrize("pos", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_resume_mit_nan_oder_inf_ist_ungueltig(tmp_path, pos):
    p = tmp_path / "resume.json"
    p.write_text('{"schema_version":1,"serien":{"s1":{"folge":"a.mp3","index":0,"position_s":%s,"zaehler":1}}}' % pos)
    with pytest.raises(store.Ungueltig):
        store.lese_pruefe(p, store.parse_resume)


def test_parse_resume_lehnt_riesige_ganzzahl_ohne_ueberlauf_ab():
    roh = {"serien": {"s": {"folge": "a", "index": 0, "position_s": 10**400, "zaehler": 1}}}
    with pytest.raises(store.Ungueltig):
        store.parse_resume(roh)


def test_serialisiere_lehnt_nan_ab():
    with pytest.raises(ValueError):
        store.serialisiere({"x": float("nan")})
    with pytest.raises(ValueError):
        store.serialisiere({"x": float("inf")})


def test_abrunden_nicht_endlich():
    from tobibox import pointer

    assert pointer.abrunden(float("nan")) == 0.0
    assert pointer.abrunden(float("inf")) == 0.0
    assert pointer.abrunden(-float("inf")) == 0.0


# --- Schreiben: Kopie statt Hardlink, Reste ------------------------------------


def test_ohne_hardlinks_wird_die_bak_kopiert(tmp_path, monkeypatch):
    p = tmp_path / "x.json"
    schreibe_atomar(p, {"v": 1})

    def kein_link(*a, **k):
        raise OSError("Operation not permitted")

    monkeypatch.setattr(os, "link", kein_link)
    schreibe_atomar(p, {"v": 2})
    assert json.loads((tmp_path / "x.json.bak").read_text())["v"] == 1
    assert json.loads(p.read_text())["v"] == 2
    assert sorted(f.name for f in tmp_path.iterdir()) == ["x.json", "x.json.bak"]


@pytest.mark.parametrize("fehler_bei", ["link", "replace_bak", "replace_neu"])
def test_fehler_im_verfahren_laesst_keine_tmp_reste(tmp_path, monkeypatch, fehler_bei):
    p = tmp_path / "x.json"
    schreibe_atomar(p, {"v": 1})
    schreibe_atomar(p, {"v": 2})
    echt_replace = os.replace

    def replace(a, b):
        if (fehler_bei == "replace_bak" and str(b).endswith(".bak")) or (
            fehler_bei == "replace_neu" and str(b).endswith("x.json")
        ):
            raise OSError("boom")
        return echt_replace(a, b)

    if fehler_bei == "link":
        monkeypatch.setattr(os, "link", lambda *a: (_ for _ in ()).throw(OSError("x")))
        monkeypatch.setattr("shutil.copyfile", lambda *a: (_ for _ in ()).throw(OSError("voll")))
    else:
        monkeypatch.setattr(os, "replace", replace)
    with pytest.raises(OSError):
        schreibe_atomar(p, {"v": 3})
    monkeypatch.undo()
    assert not list(tmp_path.glob("*.tmp"))
    assert json.loads(p.read_text())["v"] == 2
