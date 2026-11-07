"""``outbox``: unknown.json, Löschen nur bei passender Bestätigung, Neustart, Idempotenz."""

from __future__ import annotations

import asyncio
import json
import os
import time

import pytest

from tobibox import store

from tobibox.clock import SimUhr
from tobibox.outbox import MAX_EINTRAEGE, Outbox, zeitstempel

UID = "04a1b2c3"


@pytest.fixture
def uhr():
    return SimUhr()


@pytest.fixture
def box(tmp_path):
    o = Outbox(tmp_path)
    o.laden()
    return o


def neu(tmp_path):
    o = Outbox(tmp_path)
    o.laden()
    return o


def test_zeitstempel_millisekunden():
    assert zeitstempel(1_700_000_000.412) == "2023-11-14T22:13:20.412Z"


def test_melden_schreibt_eintrag(box, uhr, tmp_path):
    box.melden("unbekannt", UID, None, uhr.jetzt())
    (e,) = box.offen()
    assert (e.uid, e.art, e.anzahl, e.zeit_ok, e.befehl_id) == (UID, "unbekannt", 1, True, None)
    assert e.zuerst == e.zuletzt
    roh = json.loads((tmp_path / "unknown.json").read_text())
    assert roh["schema_version"] == 1 and roh["eintraege"][UID]["art"] == "unbekannt"


def test_eintrag_bleibt_ohne_bestaetigung_auch_nach_neustart(box, uhr, tmp_path):
    box.melden("unbekannt", UID, None, uhr.jetzt())
    o2 = neu(tmp_path)
    assert o2.offen() == box.offen()
    o3 = neu(tmp_path)
    assert len(o3.offen()) == 1


def test_bestaetigung_loescht_auch_in_datei(box, uhr, tmp_path):
    box.melden("unbekannt", UID, None, uhr.jetzt())
    e = box.offen()[0]
    assert box.bestaetigt(UID, "zugeordnet", e.zuletzt, "unbekannt") is True
    assert box.offen() == []
    assert neu(tmp_path).offen() == []


def test_doppelte_bestaetigung_schadet_nicht(box, uhr):
    box.melden("unbekannt", UID, None, uhr.jetzt())
    e = box.offen()[0]
    assert box.bestaetigt(UID, "g", e.zuletzt, "unbekannt") is True
    assert box.bestaetigt(UID, "g", e.zuletzt, "unbekannt") is False
    assert box.offen() == []


def test_unbekannte_id_wirkungslos(box, uhr):
    box.melden("unbekannt", UID, None, uhr.jetzt())
    assert box.bestaetigt("ffffffff", "g", "x", "unbekannt") is False
    assert len(box.offen()) == 1


def test_veraltete_bestaetigung_loescht_nicht(box, uhr):
    box.melden("unbekannt", UID, None, uhr.jetzt())
    alt = box.offen()[0].zuletzt
    uhr.vor(5)
    box.melden("unbekannt", UID, None, uhr.jetzt())
    assert box.bestaetigt(UID, "g", alt, "unbekannt") is False
    assert box.offen()[0].anzahl == 2
    assert box.bestaetigt(UID, "g", box.offen()[0].zuletzt, "unbekannt") is True


def test_falsche_art_loescht_nicht(box, uhr):
    box.melden("gelernt", UID, "b1", uhr.jetzt())
    e = box.offen()[0]
    assert box.bestaetigt(UID, "g", e.zuletzt, "unbekannt") is False
    assert len(box.offen()) == 1


def test_wiederholte_meldung_zaehlt(box, uhr):
    box.melden("unbekannt", UID, None, uhr.jetzt())
    erste = box.offen()[0]
    box.melden("unbekannt", UID, None, uhr.vor(10))
    (e,) = box.offen()
    assert e.anzahl == 2 and e.zuerst == erste.zuerst and e.zuletzt > erste.zuletzt


def test_gelernt_ersetzt_unbekannt_nicht_umgekehrt(box, uhr):
    box.melden("unbekannt", UID, None, uhr.jetzt())
    box.melden("gelernt", UID, "b1", uhr.vor(1))
    (e,) = box.offen()
    assert (e.art, e.befehl_id, e.anzahl) == ("gelernt", "b1", 2)
    box.melden("unbekannt", UID, None, uhr.vor(1))
    (e,) = box.offen()
    assert (e.art, e.befehl_id, e.anzahl) == ("gelernt", "b1", 3)


def test_zeit_ok_der_letzten_meldung(box, uhr):
    box.melden("unbekannt", UID, None, uhr.jetzt())
    uhr.setze_zeit("unbekannt", False)
    box.melden("unbekannt", UID, None, uhr.vor(1))
    assert box.offen()[0].zeit_ok is False


def test_hoechstens_200_aeltester_faellt_weg(box, uhr):
    for i in range(MAX_EINTRAEGE + 1):
        box.melden("unbekannt", f"{i:08x}", None, uhr.vor(1))
    uids = {e.uid for e in box.offen()}
    assert len(uids) == MAX_EINTRAEGE and f"{0:08x}" not in uids


def test_defekte_datei_gibt_leeren_ausgang(tmp_path):
    (tmp_path / "unknown.json").write_text("{kaputt")
    assert neu(tmp_path).offen() == []


def test_ungueltiger_eintrag_gilt_als_defekt(tmp_path):
    (tmp_path / "unknown.json").write_text(json.dumps({"schema_version": 1, "eintraege": {UID: {"art": "x"}}}))
    assert neu(tmp_path).offen() == []


def test_beim_201_eintrag_wird_nie_der_neue_verworfen_auch_bei_einer_uhr_hinter_den_alten(box, uhr, tmp_path):
    """Pi ohne RTC vor NTP: Die Uhr steht vor den alten Einträgen, der neue hat das kleinste ``zuletzt``."""
    for i in range(MAX_EINTRAEGE):
        box.melden("unbekannt", f"04{i:06x}", None, uhr.jetzt())
    uhr.setze_wall(uhr.wall - 3600)
    e = box.melden("gelernt", UID, "b1", uhr.jetzt())
    assert len(box.offen()) == MAX_EINTRAEGE
    assert e in box.offen() and box.offen()[-1].uid == UID
    assert UID in json.loads((tmp_path / "unknown.json").read_text())["eintraege"]


def test_melden_gibt_den_eintrag_zurueck(box, uhr):
    e = box.melden("unbekannt", UID, None, uhr.jetzt())
    assert e == box.offen()[0]


def test_laden_laesst_fremde_temp_dateien_stehen(tmp_path):
    (tmp_path / "resume.json.tmp").write_text("{}")  # gehört vielleicht zu einem laufenden Schreiben
    neu(tmp_path)
    assert (tmp_path / "resume.json.tmp").exists()


async def test_asynchron_schreibt_in_einem_thread_ohne_die_schleife_zu_blockieren(tmp_path, uhr, monkeypatch):
    orig = os.fsync

    def langsam(fd):
        time.sleep(0.2)
        return orig(fd)

    monkeypatch.setattr(store.os, "fsync", langsam)
    o = Outbox(tmp_path, asynchron=True)
    o.laden()
    t0 = time.monotonic()
    o.melden("unbekannt", UID, None, uhr.jetzt())
    assert time.monotonic() - t0 < 0.1  # ``melden`` wartet nicht auf die Platte
    await o.warte_gespeichert()
    assert UID in json.loads((tmp_path / "unknown.json").read_text())["eintraege"]


async def test_asynchron_aufeinanderfolgende_aenderungen_enden_im_neuesten_stand(tmp_path, uhr):
    """Melden und Bestätigen kurz hintereinander: Die Datei zeigt am Ende den neuesten Stand, nie einen älteren."""
    o = Outbox(tmp_path, asynchron=True)
    o.laden()
    e = o.melden("unbekannt", UID, None, uhr.jetzt())
    o.melden("unbekannt", "04a1b2c4", None, uhr.jetzt())
    assert o.bestaetigt(UID, "neu", e.zuletzt, "unbekannt") is True
    await asyncio.sleep(0)  # der Schreiber läuft an, während weitere Änderungen kommen
    o.melden("gelernt", "04a1b2c5", "b1", uhr.jetzt())
    await o.warte_gespeichert()
    assert set(json.loads((tmp_path / "unknown.json").read_text())["eintraege"]) == {"04a1b2c4", "04a1b2c5"}


async def test_asynchron_ohne_laufende_schleife_schreibt_sofort(tmp_path, uhr):
    o = Outbox(tmp_path, asynchron=True)
    await asyncio.to_thread(o.melden, "unbekannt", UID, None, uhr.jetzt())  # im Thread gibt es keine Schleife
    assert UID in json.loads((tmp_path / "unknown.json").read_text())["eintraege"]
