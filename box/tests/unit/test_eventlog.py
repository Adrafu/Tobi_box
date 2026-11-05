"""Ereignisprotokoll: JSON-Zeile mit allen Pflichtfeldern, Vorgangs-ID, Ziele, Obergrenze."""

from __future__ import annotations

import io
import json
import logging
import re

import pytest

from tobibox import eventlog
from tobibox import events as ev

PFLICHT = {"zeit", "mono", "zeitquelle", "ebene", "baustein", "ereignis", "ergebnis"}
UHR = lambda: (1_762_335_000.123, 1234.5678, "ntp")  # noqa: E731


@pytest.fixture
def strom():
    s = io.StringIO()
    eventlog.einrichten(ziel="stdout", strom=s, uhr=UHR, ebene="DEBUG")
    yield s
    eventlog.einrichten(ziel="stdout", strom=io.StringIO())


def zeilen(s: io.StringIO) -> list[dict]:
    return [json.loads(z) for z in s.getvalue().splitlines()]


def test_zeile_hat_alle_pflichtfelder_und_formate(strom):
    eventlog.logge("session", "INFO", "spielt", "ok", "a1b2c3d4", daten={"uid": '04a1b2c3', "serie": 's1', "position_s": 409.5})
    (z,) = zeilen(strom)
    assert PFLICHT <= set(z)
    assert z["zeit"] == "2025-11-05T09:30:00.123Z"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", z["zeit"])
    assert z["mono"] == 1234.568
    assert z["zeitquelle"] == "ntp"
    assert (z["ebene"], z["baustein"], z["ereignis"], z["ergebnis"]) == ("INFO", "session", "spielt", "ok")
    assert z["vorgang"] == "a1b2c3d4"
    assert z["daten"] == {"uid": "04a1b2c3", "serie": "s1", "position_s": 409.5}
    assert "sim" not in z


def test_genau_eine_zeile_je_ereignis_ohne_umbruch(strom):
    eventlog.logge("core", "ERROR", "fehler", "fehler", meldung="zwei\nZeilen", daten={"x": 'a\nb'})
    text = strom.getvalue()
    assert text.count("\n") == 1 and text.endswith("\n")
    assert json.loads(text)["meldung"] == "zwei\nZeilen"


def test_vorgang_fehlt_wenn_nicht_gesetzt_und_sim_nur_wenn_wahr(strom):
    eventlog.logge("learn", "INFO", "lernmodus_beginnt", sim=True)
    eventlog.logge("learn", "INFO", "lernmodus_endet")
    a, b = zeilen(strom)
    assert "vorgang" not in a and a["sim"] is True
    assert "sim" not in b


def test_vorgangs_id_in_jeder_zeile_der_kette(strom):
    for e in ("gelesen", "entprellt", "zugeordnet", "spielt"):
        eventlog.logge("session", "INFO", e, "ok", "deadbeef")
    zs = zeilen(strom)
    assert len(zs) == 4 and {z["vorgang"] for z in zs} == {"deadbeef"}


def test_geheimnisse_werden_nicht_protokolliert(strom):
    eventlog.logge("ha", "INFO", "verbunden", "ok", daten={"mqtt_passwort": 'geheim123', "token": 't0k', "benutzer": 'box'})
    text = strom.getvalue()
    assert "geheim123" not in text and "t0k" not in text
    assert json.loads(text)["daten"] == {"mqtt_passwort": "***", "token": "***", "benutzer": "box"}


def test_protokoll_befehl_des_kerns(strom):
    eventlog.logge_befehl(ev.Protokoll("session", "WARNING", "serie_fehlt", "ueberraschung", "v1", {"uid": "04a1b2c3"}))
    (z,) = zeilen(strom)
    assert (z["ebene"], z["baustein"], z["ereignis"], z["ergebnis"], z["vorgang"]) == (
        "WARNING", "session", "serie_fehlt", "ueberraschung", "v1")
    assert z["daten"] == {"uid": "04a1b2c3"}


def test_ebene_filtert(strom):
    eventlog.einrichten(ziel="stdout", strom=strom, uhr=UHR, ebene="WARNING")
    eventlog.logge("x", "INFO", "leise")
    eventlog.logge("x", "ERROR", "laut")
    assert [z["ereignis"] for z in zeilen(strom)] == ["laut"]


def test_normale_logging_zeile_wird_trotzdem_gueltig(strom):
    logging.getLogger("tobibox.irgendwas").warning("Hallo %s", "Welt")
    (z,) = zeilen(strom)
    assert PFLICHT <= set(z) and z["meldung"] == "Hallo Welt" and z["ebene"] == "WARNING"


def test_ohne_uhr_laufen_zeit_und_mono_von_selbst():
    s = io.StringIO()
    eventlog.einrichten(ziel="stdout", strom=s)
    eventlog.logge("x", "INFO", "e")
    z = json.loads(s.getvalue())
    assert z["zeitquelle"] == "system" and isinstance(z["mono"], float)
    eventlog.einrichten(ziel="stdout", strom=io.StringIO())


def test_datei_ziel_rotiert_mit_fester_obergrenze(tmp_path):
    pfad = tmp_path / "log" / "tobibox.log"
    eventlog.einrichten(ziel="datei", datei=pfad, max_bytes=2000, anzahl=3, uhr=UHR)
    for i in range(400):
        eventlog.logge("x", "INFO", "fuellen", "ok", daten={"n": i, "text": 'y' * 40})
    eventlog.einrichten(ziel="stdout", strom=io.StringIO())  # Datei schließen
    dateien = sorted(p.name for p in pfad.parent.iterdir())
    assert dateien == ["tobibox.log", "tobibox.log.1", "tobibox.log.2"]  # 3 Dateien, keine weiteren
    assert all(p.stat().st_size <= 2000 + 200 for p in pfad.parent.iterdir())
    for p in pfad.parent.iterdir():  # jede Zeile ist gültiges JSON mit Pflichtfeldern
        for z in p.read_text().splitlines():
            assert PFLICHT <= set(json.loads(z))


def test_standard_obergrenze_ist_5_mal_1_mb():
    assert (eventlog.DATEI_ANZAHL, eventlog.DATEI_MAX_BYTES) == (5, 1_000_000)


def test_einrichten_ersetzt_handler_statt_sie_zu_stapeln():
    for _ in range(3):
        eventlog.einrichten(ziel="stdout", strom=io.StringIO())
    assert len(logging.getLogger("tobibox").handlers) == 1


def test_unbekanntes_ziel_und_datei_ohne_namen():
    with pytest.raises(ValueError):
        eventlog.einrichten(ziel="mail")
    with pytest.raises(ValueError):
        eventlog.einrichten(ziel="datei")
