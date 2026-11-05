"""Stromausfall: ein Kindprozess schreibt in einer Schleife, der Test beendet ihn hart.

Nach jedem ``SIGKILL`` muss die Zustandsdatei lesbar sein (alte oder neue
Fassung, nie eine halbe), und nach Laden/Aufräumen auch ohne Rückfall. Der
Rückfall auf ``.bak`` wird zusätzlich einzeln geprüft.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import random
import signal
import time
from pathlib import Path

import pytest

from tobibox import store

pytestmark = pytest.mark.skipif(not hasattr(os, "fork"), reason="braucht fork")

DURCHLAEUFE = 60
POLSTER = "x" * 20_000  # größere Datei: das Schreibfenster wird breiter


def inhalt(n: int) -> dict:
    return {
        "schema_version": 1,
        "serien": {"s1": {"folge": "a.mp3", "index": 0, "position_s": float(n), "zaehler": n + 1}},
        "polster": POLSTER,
    }


def schreiber(verzeichnis: str, start: int, bereit) -> None:  # Kindprozess
    n = start
    pfad = Path(verzeichnis) / "resume.json"
    while True:
        n += 1
        store.schreibe_atomar(pfad, inhalt(n))
        bereit.set()


def lese_zaehler(pfad: Path) -> int:
    return json.loads(pfad.read_text(encoding="utf-8"))["serien"]["s1"]["zaehler"]


def test_hartes_beenden_waehrend_des_schreibens_laesst_nie_eine_unlesbare_datei(tmp_path):
    ctx = multiprocessing.get_context("fork")
    rng = random.Random(1234)
    pfad = tmp_path / "resume.json"
    letzter = 0
    kills_mit_resten = 0
    for i in range(DURCHLAEUFE):
        bereit = ctx.Event()
        kind = ctx.Process(target=schreiber, args=(str(tmp_path), letzter, bereit), daemon=True)
        kind.start()
        assert bereit.wait(10), "Kind schreibt nicht"
        time.sleep(rng.uniform(0.0, 0.03))
        os.kill(kind.pid, signal.SIGKILL)
        kind.join(10)
        assert kind.exitcode == -signal.SIGKILL

        # 1. Die Datei selbst ist lesbar und gültig (alte oder neue Fassung).
        zaehler = lese_zaehler(pfad)
        assert zaehler >= letzter, "Zähler darf nicht zurückgehen"
        store.lese_pruefe(pfad, store.parse_resume)
        # 2. Die Sicherung ist ebenfalls lesbar (falls vorhanden) und nie neuer.
        bak = tmp_path / "resume.json.bak"
        if bak.exists():
            assert lese_zaehler(bak) <= zaehler
        # 3. Beim Start räumt der Speicher Reste weg und lädt ohne Rückfall.
        if any(p.name.endswith(".tmp") for p in tmp_path.iterdir()):
            kills_mit_resten += 1
        s = store.ResumeStore(tmp_path)
        geladen = s.laden()
        assert s.quelle == "datei"
        assert len(geladen.zeiger) == 1
        assert not list(tmp_path.glob("*.tmp"))
        assert not (tmp_path / "resume.json.defekt").exists()
        letzter = zaehler
    assert kills_mit_resten >= 1, "kein Abbruch mitten im Schreiben getroffen: Test ist wirkungslos"


class Abbruch(BaseException):
    """Stellt den Stromausfall nach: unterbricht ``schreibe_atomar`` an einer Stelle."""


@pytest.mark.parametrize("abbruch_vor_schritt", range(5))
def test_abbruch_an_jeder_stelle_des_verfahrens_laesst_die_datei_lesbar(tmp_path, monkeypatch, abbruch_vor_schritt):
    """Schritte: fsync(tmp), link(bak.tmp), replace(bak), replace(neu), fsync(Verzeichnis)."""
    pfad = tmp_path / "resume.json"
    store.schreibe_atomar(pfad, inhalt(1))
    store.schreibe_atomar(pfad, inhalt(2))  # Datei und .bak existieren

    echt = {"fsync": os.fsync, "link": os.link, "replace": os.replace}
    zaehler = {"n": 0}

    def umhuellt(name):
        def f(*a):
            if zaehler["n"] == abbruch_vor_schritt:
                raise Abbruch()
            zaehler["n"] += 1
            return echt[name](*a)

        return f

    for name in echt:
        monkeypatch.setattr(os, name, umhuellt(name))
    with pytest.raises(Abbruch):
        store.schreibe_atomar(pfad, inhalt(3))
    monkeypatch.undo()

    assert lese_zaehler(pfad) in (3, 4)  # alte (Zähler 3) oder neue Fassung (Zähler 4)
    store.lese_pruefe(pfad, store.parse_resume)
    s = store.ResumeStore(tmp_path)
    s.laden()
    assert s.quelle == "datei"
    assert not list(tmp_path.glob("*.tmp"))
