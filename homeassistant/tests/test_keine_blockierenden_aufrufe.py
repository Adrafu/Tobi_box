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


async def test_bibliothek_ohne_dateizugriffe_in_der_loop(hass, wache, starte_integration, nas, lege_mp3):
    """Paket A3: Suche, Filter, Blättern, ``folgen/list``, ``zuordnung/list`` und ``serie/art_setzen`` (Schreiben im Executor)."""
    _bibliothek(nas, lege_mp3)
    nas.serie("mond", "mond", "Der Mond", ["lied.mp3"], einzeln=True)
    lege_mp3(nas.medien / "mond" / "lied.mp3")
    hub = await starte_integration()
    hub.store.konfig["zuordnungen"]["04a1b2c3"] = {"ziel": {"typ": "folge", "serie": "rabe", "folge": "a.mp3"}, "name": "Hase"}
    with wache.aktiv():
        await hub.medien.serien_liste(text="rabe", art="hoerspiel", filter_=["ohne_tobie", "neu", "sammlung"], sortierung="neu", limit=10)
        await hub.medien.serien_liste(text="mond", auch_folgen=True, filter_=["einzeln", "pruefen"], offset=1)
        folgen = await hub.medien.folgen_liste(text="mp3", filter_=["ohne_tobie"], sortierung="neu", limit=5)
        assert folgen["gesamt"] >= 1 and folgen["folgen"]
        await hub.zuordnung_liste(None, 10, 0, None, "hase", True)
        await hub.medien.serie_art_setzen("mond", "musik")
        await hub.medien.serie_art_setzen("mond", "geschichte")
        await hub.medien.serien_liste(art="geschichte")
    wache.leer()
    assert nas.serie_json("mond")["art"] == "geschichte"


async def test_upload_mit_wunsch_gruppen_warten_und_reserve_ohne_dateizugriffe_in_der_loop(
    hass, wache, integration, hass_client, nas, tmp_path, freezer
):
    """Paket A3d: Upload mit ``gruppe_anzahl`` (Reserve-Rechnung, Wunsch, Warten auf die Gruppe, ``teilweise`` nach 30 Minuten)."""
    from datetime import timedelta

    import aiohttp

    client = await hass_client()
    a = erzeuge_audio(tmp_path / "a.mp3", frequenz=300, album="Buch", title="Eins").read_bytes()  # (ausserhalb der Wache gelesen)
    b = erzeuge_audio(tmp_path / "b.mp3", frequenz=400, album="Buch", title="Zwei").read_bytes()

    def formular(inhalt: bytes, dateiname: str, **felder: str) -> aiohttp.FormData:
        daten = aiohttp.FormData(quote_fields=False)
        for k, v in felder.items():
            daten.add_field(k, v)
        daten.add_field("datei", inhalt, filename=dateiname, content_type="application/octet-stream")
        return daten

    gemeinsam = {"gruppe": "abcdef1234567890", "ziel": "neu", "art": "hoerbuch", "name": "Das Buch", "gruppe_anzahl": "3"}
    with wache.aktiv():
        assert (await client.post("/api/tobibox/upload", data=formular(a, "01.mp3", **gemeinsam))).status == 200
        assert (await client.post("/api/tobibox/upload", data=formular(b, "02.mp3", **gemeinsam))).status == 200
        assert (await client.post("/api/tobibox/upload", data=formular(b, "x.mp3", ziel="neu", art="musik", name="x" * 101))).status == 400
        erg = await integration.eingang.durchlauf_und_warten()  # die Gruppe wartet auf die dritte Datei
        await hass.async_block_till_done()
        assert erg["eintraege"] == 0
        assert (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]["status"] == "wartet"
    # Zeitgeber abmelden: Der Sprung der Uhr würde sonst die 10-Minuten-Prüfung und den Nachlauf neben dem eigenen Durchlauf starten
    for fn in [*integration._abmelden, *integration._timer]:
        fn()
    integration._abmelden.clear()
    integration._timer.clear()
    integration.eingang.abbrechen()
    freezer.tick(timedelta(minutes=31))
    with wache.aktiv():
        erg = await integration.eingang.durchlauf_und_warten()  # 30 Minuten Ruhe: einsortiert, was da ist
        assert erg["gestartet"] is True
        await hass.async_block_till_done()
        eintrag = (await integration.eingang.liste("offen", 50, 0))["eintraege"][0]
    wache.leer()
    assert eintrag["status"] == "teilweise"
    assert any(h["code"] == "gruppe_unvollstaendig" for h in eintrag["hinweise"])
    integration.eingang.abbrechen()
    for fn in list(integration._timer):
        fn()


async def test_cover_ohne_dateizugriffe_in_der_loop(hass, wache, starte_integration, hass_client, hass_ws_client, nas, lege_mp3):
    """Paket A4: Nachholen nach dem Start (Datei und Tag), GET/POST/DELETE, Suche, ``cover/neu_suchen``, Zusammenführen,
    Löschen und Wiederherstellen mit Cover, Einsortieren mit mitgeliefertem ``cover.jpg``. Bildverarbeitung und ``ffmpeg`` nur im Executor."""
    from .test_cover import bild, setze_bild

    for sid in ("rabe", "zwei", "drei"):
        lege_mp3(nas.medien / sid / "a.mp3")
        nas.serie(sid, sid, f"Serie {sid}", ["a.mp3"])
    setze_bild(nas.medien / "rabe" / "a.mp3", bild((700, 700)))
    (nas.medien / "zwei" / "folder.jpg").write_bytes(bild((700, 700)))
    foto = bild((900, 900))
    erzeuge_audio(nas.eingang / "Buch" / "a.mp3", frequenz=333, album="Das Buch", album_artist="Autor A")
    (nas.eingang / "Buch" / "cover.jpg").write_bytes(bild((600, 600)))
    with wache.aktiv():
        hub = await starte_integration()  # Prüfung der Freigabe und das Nachholen der Cover im Hintergrund
        await hub.cover.warte_auf_ende()
        client = await hass_client()
        api = await hass_ws_client(hass)
        assert (await client.post("/api/tobibox/cover/drei", data=foto)).status == 200
        for ziel in ("rabe", "zwei", "drei"):
            for groesse in ("klein", "gross"):
                assert (await client.get(f"/api/tobibox/cover/{ziel}?groesse={groesse}")).status == 200
        stand = (await hub.medien.serien_liste())["serien"][0]["cover_stand"]
        assert (await client.get("/api/tobibox/cover/rabe", headers={"If-None-Match": f'"{stand}"'})).status in (200, 304)
        assert (await client.delete("/api/tobibox/cover/drei?quelle=eigen")).status == 200
        await api.send_json_auto_id({"type": "tobibox/cover/neu_suchen"})
        assert (await api.receive_json())["success"] is True
        await hub.cover.warte_auf_ende()
        await hub.medien.serien_zusammenfuehren("rabe", "drei", False, None, None)
        antwort = await hub.medien.serie_loeschen("zwei", False, None)
        await hub.medien.papierkorb_wiederherstellen(antwort["eintrag"]["id"], None)
        await hub.medien.serie_umbenennen("zwei", "Zwei neu")
        await hub.eingang.durchlauf_und_warten(sofort=True)  # mitgeliefertes cover.jpg wird kopiert, Rest in den Papierkorb
        await hub.cover.warte_auf_ende()
        await hass.async_block_till_done()
    wache.leer()
    assert (nas.medien / "zwei" / "cover.jpg").is_file()
    assert any(p.name == "cover.jpg" for p in nas.medien.glob("*/cover.jpg") if p.parent.name not in ("rabe", "zwei", "drei"))
