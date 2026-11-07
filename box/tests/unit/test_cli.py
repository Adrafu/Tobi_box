"""``tobibox status``: läuft ohne Dienst, verändert nichts, sagt das."""

from __future__ import annotations

import io
import json

import pytest
from fixtures.audio import erzeuge_medien, erzeuge_serie

from conftest import zeiger_speichern
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
    ResumeStore(tmp / "var").speichern(zeiger_speichern("s", "a", 0, 1.0, "pause"), 0)
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


# --------------------------------------------------------------------------
# Stufe 2: offene Meldungen im Status, tobibox sim
# --------------------------------------------------------------------------


def test_status_zeigt_offene_meldungen_und_dass_der_dienst_nicht_laeuft(box):
    from tobibox.clock import SimUhr
    from tobibox.outbox import Outbox

    tmp, toml = box
    o = Outbox(tmp / "var")
    o.laden()
    o.melden("unbekannt", "04ffeedd", None, SimUhr().jetzt())
    code, text = lauf("status", "--config", str(toml))
    assert "Meldungen: 04ffeedd (unbekannt, 1x) warten auf Bestätigung" in text
    assert "nicht erreichbar" in text and "kein laufender Dienst nötig" in text
    d = json.loads(lauf("status", "--config", str(toml), "--json")[1])
    assert d["live"] is None and d["offene_meldungen"][0]["uid"] == "04ffeedd"


def test_status_ohne_meldungen(box):
    _, toml = box
    assert "Meldungen: keine offen" in lauf("status", "--config", str(toml))[1]


def test_formatiere_live_zeigt_status_und_pruefpunkte():
    live = {
        "status": {
            "zustand": "spielt", "serie": {"id": "s1", "name": "Rabe"}, "folge": {"name": "a.mp3", "track": 1},
            "lernmodus": True, "leser": "ok", "firmware": "1.0.0", "netz": "offline", "zeitquelle": "system",
            "zeit_ok": True, "konfig": {"revision": 3, "liste_id": "a3f9c1e07b2d4856"}, "speicher_frei_mb": 900,
            "letzter_fehler": None,
        },
        "pruefpunkte": {"punkte": [
            {"name": "leser", "ok": True, "detail": "ok"}, {"name": "netz", "ok": False, "detail": "offline, Broker nicht verbunden"},
        ]},
    }
    text = "\n".join(cli._live_zeilen(live))
    assert "Sitzung: spielt, Serie: Rabe, Folge a.mp3 (Track 1), Lernmodus: an" in text
    assert "Revision 3" in text and "leser ok, netz FEHLER" in text and "netz: offline, Broker nicht verbunden" in text


@pytest.mark.parametrize(
    "argv, erwartet",
    [
        (["learn", "--serie", "3f9a1c07b2d4"], {"befehl": "learn", "typ": "serie", "serie": "3f9a1c07b2d4", "ttl": 60}),
        (["learn", "--serie", "3f9a1c07b2d4", "--folge", "folge-01.wav", "--ttl", "30"],
         {"befehl": "learn", "typ": "folge", "serie": "3f9a1c07b2d4", "folge": "folge-01.wav", "ttl": 30}),
        (["learn", "--serie", "3f9a1c07b2d4", "--ueberschreiben"],
         {"befehl": "learn", "typ": "serie", "serie": "3f9a1c07b2d4", "ttl": 60, "ueberschreiben": True}),
        (["learn-abort"], {"befehl": "learn_abort"}),
        (["card", "04a1b2c3", "--serie", "3f9a1c07b2d4"],
         {"befehl": "card", "uid": "04a1b2c3", "ziel": {"typ": "serie", "serie": "3f9a1c07b2d4"}}),
        (["card", "04a1b2c3", "--serie", "3f9a1c07b2d4", "--folge", "folge-01.wav"],
         {"befehl": "card", "uid": "04a1b2c3", "ziel": {"typ": "folge", "serie": "3f9a1c07b2d4", "folge": "folge-01.wav"}}),
        (["card", "04a1b2c3", "--aktion", "status"],
         {"befehl": "card", "uid": "04a1b2c3", "ziel": {"typ": "aktion", "aktion": "status"}}),
        (["ack", "04a1b2c3", "--zuletzt", "z", "--art", "gelernt", "--grund", "zugeordnet"],
         {"befehl": "ack", "uid": "04a1b2c3", "zuletzt": "z", "art": "gelernt", "grund": "zugeordnet"}),
    ],
)
def test_sim_baut_die_json_zeile(box, monkeypatch, argv, erwartet):
    _, toml = box
    gesendet = []
    monkeypatch.setattr(cli, "_frage_socket", lambda pfad, zeile: gesendet.append((pfad, zeile)) or {"ok": True})
    out = io.StringIO()
    assert cli.main(["sim", "--config", str(toml), *argv], out) == 0
    (pfad, zeile), = gesendet
    assert zeile == erwartet and pfad.name == "sim.sock"
    assert json.loads(out.getvalue()) == {"ok": True}


def test_sim_ack_nimmt_zuletzt_und_art_aus_unknown_json(box, monkeypatch):
    from tobibox.clock import SimUhr
    from tobibox.outbox import Outbox

    tmp, toml = box
    o = Outbox(tmp / "var")
    o.laden()
    o.melden("gelernt", "04ffeedd", "b1", SimUhr().jetzt())
    e = o.offen()[0]
    gesendet = []
    monkeypatch.setattr(cli, "_frage_socket", lambda pfad, zeile: gesendet.append(zeile) or {"ok": True})
    assert cli.main(["sim", "--config", str(toml), "ack", "04ffeedd"], io.StringIO()) == 0
    assert gesendet == [{"befehl": "ack", "uid": "04ffeedd", "zuletzt": e.zuletzt, "art": "gelernt", "grund": "sim"}]


def test_sim_ack_ohne_eintrag_ist_ein_fehler(box, capsys):
    _, toml = box
    assert cli.main(["sim", "--config", str(toml), "ack", "04ffeedd"], io.StringIO()) == 2
    assert "kein offener Eintrag" in capsys.readouterr().err


def test_sim_ohne_dienst_exitcode_3(box, capsys):
    _, toml = box
    assert cli.main(["sim", "--config", str(toml), "learn", "--serie", "3f9a1c07b2d4"], io.StringIO()) == 3
    assert "nicht erreichbar" in capsys.readouterr().err


def test_sim_abgelehnte_zeile_exitcode_1(box, monkeypatch, capsys):
    _, toml = box
    monkeypatch.setattr(cli, "_frage_socket", lambda pfad, zeile: {"ok": False, "fehler": "typ ungueltig"})
    assert cli.main(["sim", "--config", str(toml), "learn", "--serie", "3f9a1c07b2d4"], io.StringIO()) == 1
    assert "typ ungueltig" in capsys.readouterr().err


def test_sim_card_ohne_ziel_ist_ein_aufrufefehler(box):
    _, toml = box
    with pytest.raises(SystemExit) as e:
        cli.main(["sim", "--config", str(toml), "card", "04a1b2c3"], io.StringIO())
    assert e.value.code == 2


def test_sim_ohne_rechte_auf_den_socket_ist_exitcode_4_und_nicht_nicht_erreichbar(box, monkeypatch, capsys):
    _, toml = box

    def verboten(pfad, zeile):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(cli, "_frage_socket", verboten)
    assert cli.main(["sim", "--config", str(toml), "learn", "--serie", "3f9a1c07b2d4"], io.StringIO()) == 4
    fehler = capsys.readouterr().err
    assert "keine Berechtigung" in fehler and "nicht erreichbar" not in fehler


def test_frage_socket_reicht_permission_error_weiter_und_meldet_sonst_none(tmp_path, monkeypatch):
    import socket

    class Verboten:
        def __init__(self, *a):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def settimeout(self, t):
            pass

        def connect(self, pfad):
            raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(socket, "socket", Verboten)
    with pytest.raises(PermissionError):
        cli._frage_socket(tmp_path / "sim.sock", {"befehl": "status"})
    monkeypatch.undo()
    assert cli._frage_socket(tmp_path / "gibt-es-nicht.sock", {"befehl": "status"}) is None


def test_status_ohne_rechte_auf_den_socket_sagt_es(box, monkeypatch):
    _, toml = box

    def verboten(zustand):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(cli, "frage_dienst", verboten)
    code, text = lauf("status", "--config", str(toml))
    assert "keine Berechtigung auf sim.sock" in text and "nicht erreichbar" not in text


def test_status_schreibt_beim_lesen_der_bibliothek_keine_protokollzeilen_und_aendert_keine_handler(box):
    import logging

    _, toml = box
    strom = io.StringIO()
    eventlog.einrichten(ziel="stdout", ebene="DEBUG", strom=strom)
    try:
        handler = list(logging.getLogger("tobibox").handlers)
        lauf("status", "--config", str(toml))
        assert list(logging.getLogger("tobibox").handlers) == handler  # Handler bleiben, wie sie waren
        assert strom.getvalue() == ""
    finally:
        eventlog.logger().handlers.clear()


SERIE_RABE = "3f9a1c07b2d4"


@pytest.mark.parametrize(
    "argv",
    [
        ["learn", "--serie", "rabe"],
        ["learn", "--serie", "gibt-es-nicht", "--folge", "folge-01.wav"],
        ["card", "04a1b2c3", "--serie", "rabe"],
        ["card", "04a1b2c3", "--serie", "c07d2e91a45b"],  # die Überraschungs-Serie ist kein Ziel
    ],
)
def test_sim_unbekannte_serie_wird_abgelehnt_mit_den_vorhandenen_ids(box, monkeypatch, capsys, argv):
    _, toml = box
    gesendet = []
    monkeypatch.setattr(cli, "_frage_socket", lambda pfad, zeile: gesendet.append(zeile) or {"ok": True})
    out = io.StringIO()
    assert cli.main(["sim", "--config", str(toml), *argv], out) == 2
    fehler = capsys.readouterr().err
    assert gesendet == [] and out.getvalue() == ""
    assert f"{SERIE_RABE} (Der kleine Rabe)" in fehler and "8c21d5e9a0b7 (Bär)" in fehler
    assert "c07d2e91a45b" not in fehler.split("Vorhandene Serien-IDs:")[1]


def test_sim_ordnername_statt_id_nennt_die_richtige_id(box, monkeypatch, capsys):
    _, toml = box
    monkeypatch.setattr(cli, "_frage_socket", lambda pfad, zeile: {"ok": True})
    assert cli.main(["sim", "--config", str(toml), "card", "04a1b2c3", "--serie", "rabe"], io.StringIO()) == 2
    assert f"Ordnername von \"Der kleine Rabe\", gebraucht wird die ID {SERIE_RABE}" in capsys.readouterr().err


@pytest.mark.parametrize("befehl", [["learn", "--serie", SERIE_RABE], ["card", "04a1b2c3", "--serie", SERIE_RABE]])
def test_sim_unbekannte_folge_wird_abgelehnt_mit_den_vorhandenen_folgen(box, monkeypatch, capsys, befehl):
    _, toml = box
    gesendet = []
    monkeypatch.setattr(cli, "_frage_socket", lambda pfad, zeile: gesendet.append(zeile) or {"ok": True})
    assert cli.main(["sim", "--config", str(toml), *befehl, "--folge", "folge-99.wav"], io.StringIO()) == 2
    fehler = capsys.readouterr().err
    assert gesendet == [] and "folge-99.wav" in fehler and "folge-01.wav, folge-02.wav, folge-03.wav" in fehler


def test_sim_aktionskarte_braucht_keine_serie(box, monkeypatch):
    _, toml = box
    monkeypatch.setattr(cli, "_frage_socket", lambda pfad, zeile: {"ok": True})
    assert cli.main(["sim", "--config", str(toml), "card", "04a1b2c3", "--aktion", "status"], io.StringIO()) == 0


def test_sim_ohne_medienordner_nennt_keine_serien(tmp_path, capsys):
    toml = tmp_path / "tobibox.toml"
    toml.write_text(f'[pfade]\nzustand = "{tmp_path / "var"}"\nmedien = "{tmp_path / "fehlt"}"\n', encoding="utf-8")
    assert cli.main(["sim", "--config", str(toml), "learn", "--serie", "x"], io.StringIO()) == 2
    assert "Vorhandene Serien-IDs: keine" in capsys.readouterr().err
