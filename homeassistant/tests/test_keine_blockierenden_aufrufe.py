"""Keine Dateizugriffe in der Event-Loop (Home Assistant meldet sie als ``Detected blocking call``).

``pytest-homeassistant-custom-component`` meldet das **nicht**: ``homeassistant.block_async_io`` wird in den Tests nie
eingeschaltet, und unter ``unittest``/``pytest`` überspringt es ``scandir``, ``listdir`` und ``open`` ohnehin
(``skip_for_tests``). ``stat``, ``is_dir``, ``is_file`` und ``exists`` kennt es gar nicht. Deshalb hängt diese Datei eine
eigene Wache in ``os``, ``io`` und ``builtins``: Jeder Zugriff auf einen Pfad unter ``tmp_path``, der im Thread der
Event-Loop geschieht, während die Wache ``aktiv`` ist, lässt den Test scheitern.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import os
import threading
import traceback
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from .conftest import braucht_ffmpeg, erzeuge_audio

pytestmark = braucht_ffmpeg

#: Alles, was auf die Platte greift (Pathlib und ``shutil`` laufen darüber)
_ZUGRIFFE = (
    (os, "stat"), (os, "lstat"), (os, "scandir"), (os, "listdir"), (os, "mkdir"), (os, "makedirs"), (os, "unlink"),
    (os, "rmdir"), (os, "rename"), (os, "replace"), (os, "open"), (os, "utime"), (builtins, "open"), (io, "open"),
)


class Wache:
    def __init__(self, wurzel: Path, loop_thread: int) -> None:
        self.wurzel = str(wurzel)
        self.loop_thread = loop_thread
        self.ist_aktiv = False
        self.treffer: list[str] = []

    @contextlib.contextmanager
    def aktiv(self) -> Iterator[None]:
        self.ist_aktiv = True
        try:
            yield
        finally:
            self.ist_aktiv = False

    def melde(self, name: str, args: tuple[Any, ...]) -> None:
        if not self.ist_aktiv or threading.get_ident() != self.loop_thread or not args:
            return
        pfad = args[0]
        if not isinstance(pfad, (str, os.PathLike)) or not os.fspath(pfad).startswith(self.wurzel):
            return
        stelle = next(
            (f"{f.filename.split('custom_components/')[-1]}:{f.lineno} {f.name}" for f in reversed(traceback.extract_stack()) if "custom_components" in f.filename),
            "?",
        )
        self.treffer.append(f"{name}({os.fspath(pfad)!r}) in {stelle}")

    def leer(self) -> None:
        assert not self.treffer, "Dateizugriffe in der Event-Loop:\n" + "\n".join(sorted(set(self.treffer)))


@pytest.fixture
async def wache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Wache:
    w = Wache(tmp_path, threading.get_ident())  # die Fixture läuft im Thread der Event-Loop
    for modul, name in _ZUGRIFFE:
        original = getattr(modul, name)

        def umhuellt(*args: Any, _o: Callable[..., Any] = original, _n: str = name, **kw: Any) -> Any:
            w.melde(_n, args)
            return _o(*args, **kw)

        monkeypatch.setattr(modul, name, umhuellt)
    return w


def _bibliothek(nas, lege_mp3) -> None:
    """Serien mit Datei-Folgen und mit Ordner-Folgen (die Stelle aus dem Log: ``tracks_in_ordner``)."""
    lege_mp3(nas.medien / "hoerbuch" / "teil-1" / "01.mp3")
    lege_mp3(nas.medien / "hoerbuch" / "teil-1" / "02.mp3")
    lege_mp3(nas.medien / "hoerbuch" / "teil-2" / "01.mp3")
    lege_mp3(nas.medien / "rabe" / "a.mp3")
    lege_mp3(nas.medien / "rabe" / "b.mp3")
    lege_mp3(nas.medien / "kopie" / "x.mp3")
    nas.serie("kopie", "hoerbuch", "Kopie", ["x.mp3"])  # doppelte ID: die jüngere Kopie bekommt eine neue


async def test_wache_erkennt_zugriffe_in_der_loop_und_nicht_im_executor(hass, wache, tmp_path):
    """Die Wache selbst: ``scandir`` und ``is_dir`` in der Loop werden gemeldet, im Executor nicht."""
    with wache.aktiv():
        await hass.async_add_executor_job(lambda: (list(os.scandir(tmp_path)), tmp_path.is_dir(), tmp_path.stat()))
    wache.leer()
    with wache.aktiv():
        list(os.scandir(tmp_path))
        tmp_path.is_dir()
    assert len(wache.treffer) == 2
    assert wache.treffer[0].startswith("scandir(")
    assert wache.treffer[1].startswith("stat(")  # ``Path.is_dir`` ruft ``os.stat``


async def test_start_und_pruefung_ohne_dateizugriffe_in_der_loop(hass, wache, starte_integration, nas, lege_mp3):
    _bibliothek(nas, lege_mp3)
    with wache.aktiv():
        hub = await starte_integration()  # ``async_setup_entry`` (Seite) und erste Prüfung der Freigabe
        await hub.medien.pruefen()  # zweite Prüfung: bekannte Folgen mit Zwischenspeicher
    wache.leer()
    assert len(hub.medien.serien) == 3
    folge = next(o for i in hub.medien.serien.values() for o in i.folgen_objekte if o["name"] == "teil-1")
    assert (folge["art"], folge["tracks"]) == ("ordner", 2)


async def test_lesen_und_aendern_ohne_dateizugriffe_in_der_loop(hass, wache, starte_integration, nas, lege_mp3):
    _bibliothek(nas, lege_mp3)
    hub = await starte_integration()
    with wache.aktiv():
        liste = await hub.medien.serien_liste()
        sid = next(s["id"] for s in liste["serien"] if s["name"] == "hoerbuch")
        serie = await hub.medien.serie_holen(sid)
        assert [f["art"] for f in serie["folgen"]] == ["ordner", "ordner"]
        await hub.medien.serie_umbenennen(sid, "Hörbuch")
        await hub.medien.serie_anlegen("Neu")
        await hub.medien.pruefen()
    wache.leer()


async def test_eingang_ohne_dateizugriffe_in_der_loop(hass, wache, starte_integration, nas):
    hub = await starte_integration()
    for i in range(1, 4):
        erzeuge_audio(nas.eingang / "Hörbuch X" / f"Kapitel {i:02d}.mp3", frequenz=300 + i, album="Hörbuch X",
                      album_artist="Autor A", track=f"{i}/3", title=f"Kapitel {i}")
    erzeuge_audio(nas.eingang / "Einzel.mp3", frequenz=500, album="Einzel", album_artist="Autor B")
    with wache.aktiv():
        await hub.eingang.durchlauf_und_warten(sofort=True)
        await hass.async_block_till_done()
    # dieselbe Datei noch einmal: der Index meldet sie als doppelt (``_index_treffer_alle``)
    original = next((nas.medien).rglob("Einzel.mp3"))
    (nas.eingang / "Kopie.mp3").write_bytes(original.read_bytes())
    with wache.aktiv():
        await hub.eingang.durchlauf_und_warten(sofort=True)
        await hass.async_block_till_done()
    wache.leer()
    assert not (nas.eingang / "Kopie.mp3").exists()
