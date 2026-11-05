"""``tobibox status``: läuft ohne Dienst, verändert nichts, sagt das."""

from __future__ import annotations

import io
import json

import pytest
from fixtures.audio import erzeuge_medien, erzeuge_serie

from tobibox import cli, eventlog
from tobibox import events as ev
from tobibox.store import KonfigStore, ResumeStore


@pytest.fixture
def box(tmp_path):
    medien = erzeuge_medien(tmp_path / "medien")
    zustand = tmp_path / "var"
    zustand.mkdir()
    toml = tmp_path / "tobibox.toml"
    toml.write_text(
        f'[pfade]\nzustand = "{zustand}"\nmedien = "{medien}"\n'
        f'[protokoll]\nziel = "datei"\ndatei = "{tmp_path / "log" / "tobibox.log"}"\n',
        encoding="utf-8",
    )
    return tmp_path, toml


def lauf(*argv):
    out = io.StringIO()
    code = cli.main(list(argv), out)
    return code, out.getvalue()


def test_status_ohne_laufenden_dienst_sagt_es(box):
    _, toml = box
    code, text = lauf("status", "--config", str(toml))
    assert "kein laufender Dienst nötig" in text
    assert "Medien:    ok  3 Serien, 7 Folgen, Überraschung: ok" in text
    assert "Versionen: tobibox 0.1.0, Leser-Protokoll 1" in text
    assert "Letzte Fehler: keine im Protokoll" in text
    assert code == 0


def test_status_zeigt_zustandsdateien(box):
    tmp, toml = box
    ResumeStore(tmp / "var").speichern(ev.ZeigerSpeichern("s", "a", 0, 1.0, "pause"), 0)
    code, text = lauf("status", "--config", str(toml))
    assert "Zeiger: 1 Zeiger" in text


def test_status_liest_letzte_fehler_und_leser_aus_der_logdatei(box):
    tmp, toml = box
    eventlog.einrichten(ziel="datei", datei=tmp / "log" / "tobibox.log")
    eventlog.logge("reader", "INFO", "hallo", "ok")
    eventlog.logge("store", "ERROR", "datei_defekt", "fehler", meldung="resume.json")
    eventlog.einrichten(ziel="stdout", strom=io.StringIO())
    code, text = lauf("status", "--config", str(toml))
    assert "store/datei_defekt resume.json" in text
    assert "Leser:     ok" in text


def test_status_json(box):
    _, toml = box
    code, text = lauf("status", "--config", str(toml), "--json")
    d = json.loads(text)
    assert d["medien"]["serien"] == 3 and d["versionen"]["tobibox"] == "0.1.0"


def test_status_meldet_fehlende_ueberraschung_mit_exitcode_1(tmp_path):
    medien = tmp_path / "m"
    erzeuge_serie(medien, "s", ["a.wav"])
    toml = tmp_path / "t.toml"
    toml.write_text(f'[pfade]\nzustand = "{tmp_path}/var"\nmedien = "{medien}"\n')
    code, text = lauf("status", "--config", str(toml))
    assert code == 1 and "FEHLER" in text and "Überraschung: keine" in text


def test_status_veraendert_nichts(box):
    tmp, toml = box
    (tmp / "var" / "resume.json").write_text("kaputt")
    (tmp / "var" / "x.json.tmp").write_text("rest")
    vorher = sorted((p.name, p.read_bytes()) for p in (tmp / "var").iterdir())
    code, text = lauf("status", "--config", str(toml))
    assert sorted((p.name, p.read_bytes()) for p in (tmp / "var").iterdir()) == vorher
    assert code == 1 and "ungueltig" in text


def test_status_ohne_konfig_exitcode_2(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("TOBIBOX_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    code, _ = lauf("status")
    assert code == 2
    assert "fehlt" in capsys.readouterr().err


def test_konfig_aus_umgebungsvariable(box, monkeypatch):
    _, toml = box
    monkeypatch.setenv("TOBIBOX_CONFIG", str(toml))
    assert lauf("status")[0] == 0
