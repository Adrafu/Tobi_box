"""Bibliothek aus dem Medienordner: Reihenfolge, Ordner ohne serie.json, doppelte IDs, Überraschungs-Serie."""

from __future__ import annotations

import json
import logging

import pytest
from fixtures.audio import erzeuge_folge_ordner, erzeuge_medien, erzeuge_serie, schreibe_serie_json, schreibe_wav

from tobibox import library
from tobibox.library import lade_bibliothek, natuerlicher_schluessel, sortiere_natuerlich


@pytest.fixture
def protokoll():
    zeilen: list[logging.LogRecord] = []

    class H(logging.Handler):
        def emit(self, record):
            zeilen.append(record)

    log = logging.getLogger("tobibox")
    alt, level = log.handlers[:], log.level
    log.handlers = [H()]
    log.setLevel(logging.DEBUG)
    yield zeilen
    log.handlers = alt
    log.setLevel(level)


def ereignisse(z):
    return [r.ereignis for r in z]


# --- natürliche Sortierung (Beispiele aus data-model.md) ------------------------


@pytest.mark.parametrize(
    "aufsteigend",
    [
        ["folge-2.mp3", "folge-10.mp3"],
        ["a1.mp3", "a1b.mp3"],
        ["01.mp3", "1.mp3", "2.mp3", "10.mp3"],
        ["Folge.mp3", "folge.mp3"],
        ["Folge-01.mp3", "folge-01.mp3"],
        ["1.mp3", "a.mp3"],  # Ziffernblock vor Textblock
        ["a.mp3", "a.mp3x"],
        ["x9.mp3", "x010.mp3", "x10.mp3"],
        ["99999999999999999999.mp3", "100000000000000000000.mp3"],  # beliebige Länge
    ],
)
def test_natuerliche_sortierung(aufsteigend):
    assert sortiere_natuerlich(list(reversed(aufsteigend))) == aufsteigend


def test_sortierung_ist_total_und_unabhaengig_von_der_eingabe():
    namen = ["b2", "B2", "b02", "b10", "a", "A", "10", "9", "ä", "é"]
    import itertools

    erwartet = sortiere_natuerlich(namen)
    for perm in itertools.islice(itertools.permutations(namen), 200):
        assert sortiere_natuerlich(list(perm)) == erwartet
    assert len({natuerlicher_schluessel(n) for n in namen}) == len(namen)


# --- Laden ----------------------------------------------------------------------


def test_beispielbibliothek(tmp_path):
    bib = lade_bibliothek(erzeuge_medien(tmp_path))
    assert [s.id for s in bib.serien] == ["8c21d5e9a0b7", "3f9a1c07b2d4", "c07d2e91a45b"]  # nach Ordner baer, rabe, ueb.
    rabe = bib.serie("3f9a1c07b2d4")
    assert rabe.name == "Der kleine Rabe" and rabe.ordner == "rabe"
    assert rabe.folgen == ("folge-01.wav", "folge-02.wav", "folge-03.wav")
    assert bib.ueberraschung_status == "ok"
    assert library.finde_ueberraschung(bib.serien).id == "c07d2e91a45b"
    assert bib.ereignis().serien == bib.serien


def test_reihenfolge_der_liste_ist_massgeblich(tmp_path):
    erzeuge_serie(tmp_path, "s", ["z.wav", "a.wav", "m.wav"], serie_id="s1")
    assert lade_bibliothek(tmp_path).serie("s1").folgen == ("z.wav", "a.wav", "m.wav")


def test_dateien_ausserhalb_der_liste_werden_nicht_gespielt(tmp_path):
    ordner = erzeuge_serie(tmp_path, "s", ["a.wav", "b.wav"], serie_id="s1")
    schreibe_wav(ordner / "neu.wav")
    bib = lade_bibliothek(tmp_path)
    s = bib.serie("s1")
    assert s.folgen == ("a.wav", "b.wav")
    assert library.abspielpfad(tmp_path, s, "neu.wav") is None
    assert library.abspielpfad(tmp_path, s, "../s/a.wav") is None
    assert library.abspielpfad(tmp_path, s, "a.wav") == tmp_path / "s" / "a.wav"


def test_namen_ohne_datei_werden_uebersprungen_und_doppelte_zaehlen_einmal(tmp_path, protokoll):
    ordner = erzeuge_serie(tmp_path, "s", ["a.wav", "b.wav"], serie_id="s1")
    schreibe_serie_json(ordner, "s1", "S", ["a.wav", "fehlt.wav", "b.wav", "a.wav"])
    assert lade_bibliothek(tmp_path).serie("s1").folgen == ("a.wav", "b.wav")
    assert "folge_fehlt" in ereignisse(protokoll)


def test_ordner_ohne_serie_json_nimmt_ordnernamen_und_natuerliche_sortierung(tmp_path):
    erzeuge_serie(tmp_path, "Gute Nacht", ["folge-10.wav", "folge-2.wav", "Folge-1.wav"], mit_serie_json=False)
    ordner = tmp_path / "Gute Nacht"
    (ordner / "cover.jpg").write_bytes(b"x")
    (ordner / "notizen.txt").write_text("x")
    s = lade_bibliothek(tmp_path).serie("Gute Nacht")
    assert (s.id, s.name, s.typ, s.ordner) == ("Gute Nacht", "Gute Nacht", "normal", "Gute Nacht")
    assert s.folgen == ("Folge-1.wav", "folge-2.wav", "folge-10.wav")


def test_ungueltige_serie_json_wie_fehlende_und_protokolliert(tmp_path, protokoll):
    ordner = erzeuge_serie(tmp_path, "kaputt", ["b.wav", "a.wav"], mit_serie_json=False)
    (ordner / "serie.json").write_text("{nicht json")
    bib = lade_bibliothek(tmp_path)
    assert bib.serie("kaputt").folgen == ("a.wav", "b.wav")
    assert "serie_json_ungueltig" in ereignisse(protokoll)
    assert (ordner / "serie.json").read_text() == "{nicht json"  # nicht repariert


@pytest.mark.parametrize(
    "aenderung",
    [
        {"schema_version": 2},
        {"id": "a/b"},
        {"id": ""},
        {"name": ""},
        {"typ": "sonstwas"},
        {"folgen": "a.wav"},
        {"folgen": ["../a.wav"]},
        {"angelegt_am": None},
    ],
)
def test_serie_json_pruefung(tmp_path, aenderung):
    ordner = erzeuge_serie(tmp_path, "o", ["a.wav"], serie_id="gut")
    d = json.loads((ordner / "serie.json").read_text())
    d.update(aenderung)
    (ordner / "serie.json").write_text(json.dumps(d))
    assert lade_bibliothek(tmp_path).serie("gut") is None  # fällt auf Ordnername "o" zurück
    assert lade_bibliothek(tmp_path).serie("o") is not None


def test_serie_json_unbekannte_felder_werden_ignoriert(tmp_path):
    erzeuge_serie(tmp_path, "o", ["a.wav"], serie_id="x1", zukunft={"a": 1})
    assert lade_bibliothek(tmp_path).serie("x1") is not None


def test_ordnername_als_id_ungueltig_wird_nicht_gespielt(tmp_path, protokoll):
    erzeuge_serie(tmp_path, "x" * 65, ["a.wav"], mit_serie_json=False)
    assert lade_bibliothek(tmp_path).serien == ()
    assert "ordner_name_ungueltig" in ereignisse(protokoll)


def test_doppelte_ids_die_aeltere_behaelt_die_id(tmp_path, protokoll):
    erzeuge_serie(tmp_path, "kopie", ["b.wav"], serie_id="dup", angelegt_am="2026-11-06T09:00:00Z")
    erzeuge_serie(tmp_path, "original", ["a.wav"], serie_id="dup", angelegt_am="2026-11-05T09:00:00Z")
    bib = lade_bibliothek(tmp_path)
    assert [(s.id, s.ordner) for s in bib.serien] == [("dup", "original")]
    assert "serie_id_doppelt" in ereignisse(protokoll)


def test_versteckte_ordner_und_dateien_im_medienordner_werden_ignoriert(tmp_path):
    erzeuge_serie(tmp_path, ".rsync-partial", ["a.wav"], mit_serie_json=False)
    (tmp_path / "lose.wav").write_bytes(b"x")
    assert lade_bibliothek(tmp_path).serien == ()


def test_medienordner_fehlt(tmp_path, protokoll):
    bib = lade_bibliothek(tmp_path / "gibt-es-nicht")
    assert bib.serien == ()
    assert "medienordner_fehlt" in ereignisse(protokoll)


# --- Überraschungs-Serie --------------------------------------------------------


def test_ueberraschung_nur_ueber_typ_nicht_ueber_id_oder_namen(tmp_path):
    erzeuge_serie(tmp_path, "ueberraschung", ["a.wav"], serie_id="ueberraschung", name="Überraschung")
    bib = lade_bibliothek(tmp_path)
    assert bib.ueberraschung_status == "keine"
    assert library.finde_ueberraschung(bib.serien) is None


def test_keine_ueberraschung(tmp_path, protokoll):
    erzeuge_serie(tmp_path, "s", ["a.wav"])
    bib = lade_bibliothek(tmp_path)
    assert bib.ueberraschung_status == "keine"
    assert "ueberraschung_ungueltig" in ereignisse(protokoll)


def test_mehr_als_eine_ueberraschung(tmp_path, protokoll):
    erzeuge_serie(tmp_path, "u1", ["a.wav"], serie_id="u1", typ="ueberraschung")
    erzeuge_serie(tmp_path, "u2", ["a.wav"], serie_id="u2", typ="ueberraschung")
    bib = lade_bibliothek(tmp_path)
    assert bib.ueberraschung_status == "mehrere"
    assert library.finde_ueberraschung(bib.serien) is None
    assert len(bib.serien) == 2  # beide bleiben normal ladbar


def test_leere_ueberraschung(tmp_path):
    erzeuge_serie(tmp_path, "u", [], serie_id="u", typ="ueberraschung")
    bib = lade_bibliothek(tmp_path)
    assert bib.ueberraschung_status == "leer"
    assert library.finde_ueberraschung(bib.serien) is None


def test_ueberraschung_ohne_dateien_im_ordner_ist_leer(tmp_path):
    ordner = erzeuge_serie(tmp_path, "u", ["a.wav"], serie_id="u", typ="ueberraschung")
    (ordner / "a.wav").unlink()
    assert lade_bibliothek(tmp_path).ueberraschung_status == "leer"


def test_ungueltiges_utf8_im_dateinamen_sortiert_und_laedt(tmp_path, protokoll):
    import os

    ordner = tmp_path / "roh"
    ordner.mkdir()
    schlecht = os.fsdecode(b"folge-\xff2.wav")
    for n in ("folge-1.wav", schlecht, "folge-3.wav"):
        try:
            schreibe_wav(ordner / n)
        except OSError as e:  # APFS u. a. lehnen ungültiges UTF-8 in Dateinamen ab (Errno 92)
            pytest.skip(f"Dateisystem lehnt ungültiges UTF-8 im Dateinamen ab: {e}")
    erzeuge_serie(tmp_path, "gut", ["a.wav"], serie_id="gut")
    assert sortiere_natuerlich([schlecht, "a"])  # wirft nicht
    bib = lade_bibliothek(tmp_path)
    assert bib.serie("gut") is not None  # andere Ordner bleiben
    assert len(bib.serie("roh").folgen) == 3
    assert not [r for r in protokoll if r.ereignis == "ordner_fehler"]


def test_ein_kaputter_ordner_stoppt_die_anderen_nicht(tmp_path, protokoll, monkeypatch):
    erzeuge_serie(tmp_path, "a", ["a.wav"], serie_id="a")
    erzeuge_serie(tmp_path, "b", ["b.wav"], serie_id="b")
    erzeuge_serie(tmp_path, "c", ["c.wav"], serie_id="c")
    echt = library._serie_aus_ordner

    def boese(ordner, medien):
        if ordner.name == "b":
            raise RuntimeError("kaputt")
        return echt(ordner, medien)

    monkeypatch.setattr(library, "_serie_aus_ordner", boese)
    bib = lade_bibliothek(tmp_path)
    assert [s.id for s in bib.serien] == ["a", "c"]
    fehler = [r for r in protokoll if r.ereignis == "ordner_fehler"]
    assert len(fehler) == 1 and fehler[0].levelno == logging.ERROR


def test_ohne_serie_json_punktdateien_ignoriert_und_endungen(tmp_path):
    ordner = tmp_path / "mix"
    ordner.mkdir()
    for n in ("a.mp3", "b.m4a", "c.m4b", "d.aac", "e.flac", "f.ogg", "g.opus", "h.wav", "I.MP3",
              "._a.mp3", ".versteckt.wav", "x.txt", "y.jpg", "z.wma"):
        (ordner / n).write_bytes(b"x")
    assert lade_bibliothek(tmp_path).serie("mix").folgen == (
        "a.mp3", "b.m4a", "c.m4b", "d.aac", "e.flac", "f.ogg", "g.opus", "h.wav", "I.MP3")


def test_doppelte_id_ordner_ohne_serie_json_gilt_als_juengster(tmp_path, protokoll):
    """Ein Ordner ohne ``serie.json`` (ID = Ordnername) verliert gegen eine echte ``serie.json`` mit gleicher ID."""
    erzeuge_serie(tmp_path, "aaa", ["x.wav"], mit_serie_json=False)  # Ordner zuerst im Alphabet
    erzeuge_serie(tmp_path, "zzz", ["y.wav"], serie_id="aaa", angelegt_am="2026-11-05T09:00:00Z")
    bib = lade_bibliothek(tmp_path)
    assert [(s.id, s.ordner) for s in bib.serien] == [("aaa", "zzz")]
    assert "serie_id_doppelt" in ereignisse(protokoll)


def test_doppelte_id_vergleicht_zeitpunkte_nicht_text(tmp_path):
    # Textlich "…+02:00" > "…Z", zeitlich ist es früher
    erzeuge_serie(tmp_path, "a", ["x.wav"], serie_id="d", angelegt_am="2026-11-05T10:30:00Z")
    erzeuge_serie(tmp_path, "b", ["y.wav"], serie_id="d", angelegt_am="2026-11-05T12:00:00+02:00")
    assert [s.ordner for s in lade_bibliothek(tmp_path).serien] == ["b"]


def test_doppelte_id_unlesbarer_zeitstempel_zaehlt_als_juengster(tmp_path):
    erzeuge_serie(tmp_path, "a", ["x.wav"], serie_id="d", angelegt_am="gestern")
    erzeuge_serie(tmp_path, "b", ["y.wav"], serie_id="d", angelegt_am="2026-11-05T09:00:00Z")
    assert [s.ordner for s in lade_bibliothek(tmp_path).serien] == ["b"]


# --- Folge = Datei oder Ordner mit Tracks (Entscheidung F, 05.11.) --------------------


def test_folge_als_datei_hat_genau_einen_track_den_eigenen_namen(tmp_path):
    erzeuge_serie(tmp_path, "s", ["a.wav", "b.wav"], serie_id="s1")
    s = lade_bibliothek(tmp_path).serie("s1")
    assert s.tracks == {"a.wav": ("a.wav",), "b.wav": ("b.wav",)}


def test_folge_als_ordner_tracks_in_natuerlicher_sortierung_ohne_dotfiles(tmp_path):
    ordner = erzeuge_serie(tmp_path, "s", ["x.wav"], serie_id="s1", mit_serie_json=False)
    erzeuge_folge_ordner(ordner, "CD Schatzinsel", ["track-10.wav", "track-2.wav", "Track-1.wav"],
                         dotfiles=True, fremde=["cover.jpg", "info.txt"])
    s = lade_bibliothek(tmp_path).serie("s")
    assert s.folgen == ("CD Schatzinsel", "x.wav")  # Ordner und Datei zusammen, natürlich sortiert
    assert s.tracks["CD Schatzinsel"] == (
        "CD Schatzinsel/Track-1.wav", "CD Schatzinsel/track-2.wav", "CD Schatzinsel/track-10.wav",
    )
    assert s.tracks["x.wav"] == ("x.wav",)


def test_folge_ordner_in_der_liste_von_serie_json_ist_massgeblich(tmp_path):
    ordner = erzeuge_serie(tmp_path, "s", ["a.wav"], serie_id="s1")
    erzeuge_folge_ordner(ordner, "rip", ["02.wav", "01.wav"])
    erzeuge_folge_ordner(ordner, "nicht-gelistet", ["01.wav"])
    schreibe_serie_json(ordner, "s1", "S", ["rip", "a.wav"])
    s = lade_bibliothek(tmp_path).serie("s1")
    assert s.folgen == ("rip", "a.wav")  # „nicht-gelistet“ wird nicht gespielt
    assert s.tracks["rip"] == ("rip/01.wav", "rip/02.wav")


def test_leerer_folgen_ordner_zaehlt_nicht_und_wird_protokolliert(tmp_path, protokoll):
    ordner = erzeuge_serie(tmp_path, "s", ["a.wav"], serie_id="s1", mit_serie_json=False)
    (ordner / "leer").mkdir()
    erzeuge_folge_ordner(ordner, "nur-fremdes", [], fremde=["cover.jpg"], dotfiles=True)
    s = lade_bibliothek(tmp_path).serie("s")
    assert s.folgen == ("a.wav",)
    assert ereignisse(protokoll).count("folge_leer") == 2
    # auch aus der Liste: leerer Ordner wird übersprungen
    schreibe_serie_json(ordner, "s1", "S", ["leer", "a.wav"])
    assert lade_bibliothek(tmp_path).serie("s1").folgen == ("a.wav",)


def test_versteckter_ordner_ist_keine_folge(tmp_path):
    ordner = erzeuge_serie(tmp_path, "s", ["a.wav"], serie_id="s1", mit_serie_json=False)
    erzeuge_folge_ordner(ordner, ".Trash", ["01.wav"])
    assert lade_bibliothek(tmp_path).serie("s").folgen == ("a.wav",)


def test_serie_einzelfolgen_ohne_sonderregel(tmp_path):
    """Ein Hörspiel ohne Reihe liegt in einer gewöhnlichen Serie „Einzelfolgen“."""
    ordner = erzeuge_serie(tmp_path, "Einzelfolgen", ["Frosch.wav"], mit_serie_json=False)
    erzeuge_folge_ordner(ordner, "Schatzinsel", ["01.wav", "02.wav", "03.wav"])
    s = lade_bibliothek(tmp_path).serie("Einzelfolgen")
    assert (s.typ, s.folgen) == ("normal", ("Frosch.wav", "Schatzinsel"))
    assert len(s.tracks["Schatzinsel"]) == 3 and s.tracks["Frosch.wav"] == ("Frosch.wav",)


@pytest.mark.parametrize("name", ["@eaDir", "@Recycle", "#recycle", "$RECYCLE.BIN", ".@__thumb", ".Trash"])
def test_systemordner_sind_keine_serien(tmp_path, name):
    """11.11.: QNAP- und Windows-Systemordner (auch mit Audio darin, z. B. ein Papierkorb) werden nicht eingelesen."""
    erzeuge_serie(tmp_path, "echt", ["folge-1.wav"], mit_serie_json=False)
    erzeuge_serie(tmp_path, name, ["geloescht.wav"], mit_serie_json=False)
    assert [s.ordner for s in lade_bibliothek(tmp_path).serien] == ["echt"]


def test_systemordner_in_serie_sind_keine_folgen_und_systemdateien_keine_tracks(tmp_path):
    erzeuge_serie(tmp_path, "serie", ["folge-1.wav"], mit_serie_json=False)
    schreibe_wav(tmp_path / "serie" / "@eaDir" / "x.wav")
    schreibe_wav(tmp_path / "serie" / "._folge-1.wav")
    (tmp_path / "serie" / ".DS_Store").write_bytes(b"x")
    (tmp_path / "serie" / "Thumbs.db").write_bytes(b"x")
    s = lade_bibliothek(tmp_path).serie("serie")
    assert s.folgen == ("folge-1.wav",)
