"""Prozessabbruch (Atomarität) beim Schreiben der Zustandsdateien.

Ein Kindprozess schreibt in einer Schleife, der Test beendet ihn mit
``SIGKILL``. Danach muss die Zustandsdatei lesbar sein (alte oder neue Fassung,
nie eine halbe), und nach Laden/Aufräumen auch ohne Rückfall.

Grenze: ``SIGKILL`` beendet nur den Prozess, der Kernel schreibt seinen
Seiten-Cache weiter. Das beweist die **Atomarität** (``replace``-Reihenfolge),
nicht die **Dauerhaftigkeit** bei echtem Stromausfall. Dafür prüft
``test_reihenfolge_der_betriebssystemaufrufe`` die Aufrufreihenfolge
(``fsync`` vor ``replace``, Verzeichnis-``fsync`` zuletzt); den echten
Stromausfall (Stecker ziehen) testet Tobias auf dem Pi.
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

DURCHLAEUFE = 60  # Mindestzahl der Abbrüche
MAX_DURCHLAEUFE = 600  # Obergrenze, bis ein Abbruch mitten im Schreiben getroffen wurde
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


def test_prozessabbruch_waehrend_des_schreibens_laesst_nie_eine_unlesbare_datei(tmp_path):
    ctx = multiprocessing.get_context("fork")
    rng = random.Random(1234)
    pfad = tmp_path / "resume.json"
    letzter = 0
    kills_mit_resten = 0
    for i in range(MAX_DURCHLAEUFE):
        if i >= DURCHLAEUFE and kills_mit_resten >= 1:
            break
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
    # Die Wirkung des Verfahrens an jeder Stelle prüft der Test mit ``Abbruch`` unten;
    # hier nur: bis zur Obergrenze wurde mindestens einmal mitten im Schreiben getroffen.
    assert kills_mit_resten >= 1, "kein Abbruch mitten im Schreiben getroffen (trotz Wiederholungen)"


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


def test_reihenfolge_der_betriebssystemaufrufe(tmp_path, monkeypatch):
    """data-model 1.2: fsync(tmp) vor jedem replace; link vor replace(bak); Verzeichnis-fsync zuletzt."""
    import stat

    pfad = tmp_path / "resume.json"
    store.schreibe_atomar(pfad, inhalt(1))  # damit beim zweiten Mal eine .bak entsteht

    aufrufe: list[tuple] = []
    echt = {"fsync": os.fsync, "link": os.link, "replace": os.replace}
    verz_ino = os.stat(tmp_path).st_ino

    def fsync(fd):
        st = os.fstat(fd)
        art = "verz" if stat.S_ISDIR(st.st_mode) else "datei"
        aufrufe.append(("fsync", art, st.st_ino))
        return echt["fsync"](fd)

    def link(src, dst, *a, **k):
        aufrufe.append(("link", Path(src).name, Path(dst).name, os.stat(src).st_ino))
        return echt["link"](src, dst, *a, **k)

    def replace(src, dst):
        aufrufe.append(("replace", Path(src).name, Path(dst).name, os.stat(src).st_ino))
        return echt["replace"](src, dst)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(os, "replace", replace)
    store.schreibe_atomar(pfad, inhalt(2))
    monkeypatch.undo()

    namen = [a[:3] if a[0] != "fsync" else a[:2] for a in aufrufe]
    assert namen == [
        ("fsync", "datei"),
        ("link", "resume.json", "resume.json.bak.tmp"),
        ("replace", "resume.json.bak.tmp", "resume.json.bak"),
        ("replace", "resume.json.tmp", "resume.json"),
        ("fsync", "verz"),
    ]
    # fsync der Datei geschah auf demselben Inode, der danach umbenannt wird
    tmp_ino = aufrufe[0][2]
    assert aufrufe[3][3] == tmp_ino
    # das Verzeichnis-fsync gilt dem Elternverzeichnis
    assert aufrufe[4][2] == verz_ino
    lese_zaehler(pfad)
