"""``bootid`` (Kennung des Starts) und ``lauf`` (Marker ``lauf.json``), Entscheidung G, 06.11."""

from __future__ import annotations

import json

from tobibox import bootid, lauf


def test_parse_kern_boottime_mac():
    text = "{ sec = 1730000000, usec = 123456 } Wed Nov  6 08:13:20 2026\n"
    assert bootid.parse_kern_boottime(text) == "mac-1730000000-123456"
    assert bootid.parse_kern_boottime("Unsinn") is None


def test_lese_linux_aus_datei(tmp_path, monkeypatch):
    monkeypatch.setattr(bootid.sys, "platform", "linux")
    d = tmp_path / "boot_id"
    d.write_text("6f2d-aaaa\n")
    assert bootid.lese(d) == "6f2d-aaaa"
    d.write_text("\n")
    assert bootid.lese(d) is None
    assert bootid.lese(tmp_path / "gibt-es-nicht") is None


def test_marker_schreiben_und_lesen(tmp_path):
    assert lauf.schreibe(tmp_path, "b1", "04aa")
    assert json.loads((tmp_path / "lauf.json").read_text()) == {"boot_id": "b1", "uid": "04aa"}
    assert lauf.lese_neustart_uid(tmp_path, "b1") == "04aa"
    assert lauf.lese_neustart_uid(tmp_path, "b2") is None  # anderes Einschalten
    assert lauf.lese_neustart_uid(tmp_path, None) is None


def test_marker_ohne_tobie_und_ungueltige_inhalte(tmp_path):
    lauf.schreibe(tmp_path, "b1", None)
    assert lauf.lese_neustart_uid(tmp_path, "b1") is None
    for inhalt in ("{kaputt", "[]", '{"boot_id": "b1", "uid": 5}', '{"boot_id": "b1", "uid": ""}', ""):
        (tmp_path / "lauf.json").write_text(inhalt)
        assert lauf.lese_neustart_uid(tmp_path, "b1") is None


def test_marker_fehlt_und_loeschen(tmp_path):
    assert lauf.lese_neustart_uid(tmp_path, "b1") is None
    lauf.schreibe(tmp_path, "b1", "04aa")
    lauf.loesche(tmp_path)
    lauf.loesche(tmp_path)  # zweimal ist in Ordnung
    assert not (tmp_path / "lauf.json").exists()


def test_schreiben_ohne_boot_id_tut_nichts(tmp_path):
    assert lauf.schreibe(tmp_path, None, "04aa") is False
    assert not (tmp_path / "lauf.json").exists()
