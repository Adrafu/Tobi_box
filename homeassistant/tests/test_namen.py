"""Namensregeln (Vertrag W, Abschnitt 12) und Regeln für Tag-Werte (Abschnitt 11.2): reine Funktionen."""

from __future__ import annotations

import pytest

from custom_components.tobibox import namen
from custom_components.tobibox.namen import (
    NamenErschoepft,
    album_ohne_cd_zusatz,
    dateiname_bereinigen,
    datum_aus_tag,
    eindeutiger_name,
    nummer_aus_tag,
    nummer_aus_text,
    sortiere_natuerlich,
    vergleichsschluessel,
)


# --- SMB-Zeichen, Ränder, Gerätenamen (Abschnitt 12, Regeln 1 bis 4) ---


@pytest.mark.parametrize(
    ("roh", "erwartet"),
    [
        ("Folge 1: Der Rabe.mp3", "Folge 1 - Der Rabe.mp3"),
        ("Folge 1 : Der Rabe.mp3", "Folge 1 - Der Rabe.mp3"),
        ("Folge 1:Der Rabe.mp3", "Folge 1 - Der Rabe.mp3"),
        ('a/b\\c*d?e"f<g>h|i.mp3', "a_b_c_d_e_f_g_h_i.mp3"),
        ("Tab\there\x00.mp3", "Tabhere.mp3"),  # Steuerzeichen entfallen
        ("   viel    Platz   .mp3", "viel Platz .mp3"),
        (".versteckt.mp3", "versteckt.mp3"),
        ("_privat.mp3", "privat.mp3"),
        ("..._ _x.mp3", "x.mp3"),
        ("Ende mit Punkt...", "Ende mit Punkt"),
        ("CON.mp3", "_CON.mp3"),
        ("com1.mp3", "_com1.mp3"),
        ("Lpt9", "_Lpt9"),
        (".", "_"),
        ("..", "_"),
    ],
)
def test_namensregeln(roh, erwartet):
    assert dateiname_bereinigen(roh)[0] == erwartet


def test_nfc_statt_nfd():
    nfd = "Hörbuch.mp3"  # o + kombinierender Umlautpunkt (macOS)
    name, _ = dateiname_bereinigen(nfd)
    assert name == "Hörbuch.mp3"
    assert name == "Hörbuch.mp3"


def test_leer_nach_bereinigung():
    assert dateiname_bereinigen("...")[0] == ""
    assert dateiname_bereinigen("\x01\x02")[0] == ""
    assert dateiname_bereinigen("   ")[0] == ""


def test_serienordner_darf_nicht_mit_unterstrich_beginnen():
    name, _ = dateiname_bereinigen("CON", mit_endung=False, fuer_serienordner=True)
    assert name == "CON_"
    assert not name.startswith("_")


# --- Länge: Bytes und UTF-16-Einheiten, Zeichengrenze, Endung bleibt (Regel 5) ---


def test_kuerzen_an_zeichengrenze_und_endung_bleibt():
    lang = "ä" * 200 + ".mp3"  # 400 Bytes UTF-8
    name, gekuerzt = dateiname_bereinigen(lang)
    assert gekuerzt
    assert name.endswith(".mp3")
    assert len(name.encode("utf-8")) <= 250
    name.encode("utf-8").decode("utf-8")  # nie mitten in einem Zeichen geschnitten
    assert set(name[: -len(".mp3")]) == {"ä"}


def test_kuerzen_utf16_einheiten():
    # Zeichen außerhalb der BMP zählen als 2 UTF-16-Einheiten (und 4 Bytes)
    lang = "\U0001F600" * 100 + ".mp3"
    name, gekuerzt = dateiname_bereinigen(lang)
    assert gekuerzt
    assert namen.utf16_einheiten(name) <= 250
    assert len(name.encode("utf-8")) <= 250
    assert name.endswith(".mp3")


def test_kurzer_name_wird_nicht_als_gekuerzt_gemeldet():
    assert dateiname_bereinigen("kurz.mp3") == ("kurz.mp3", False)


# --- Suffix (Regel 7) ---


def test_suffix_ohne_gross_kleinschreibung_und_unicode_form():
    belegt = {vergleichsschluessel("Folge.MP3"), vergleichsschluessel("Hörbuch.mp3")}
    assert eindeutiger_name("folge.mp3", belegt) == "folge (2).mp3"
    assert eindeutiger_name("Hörbuch.mp3", belegt) == "Hörbuch (2).mp3"
    belegt.add(vergleichsschluessel("folge (2).mp3"))
    assert eindeutiger_name("folge.mp3", belegt) == "folge (3).mp3"


def test_suffix_bei_ordnern_am_ende():
    assert eindeutiger_name("Serie.1", {vergleichsschluessel("Serie.1")}, mit_endung=False) == "Serie.1 (2)"


def test_suffix_ab_99_ist_ein_fehler():
    belegt = {vergleichsschluessel("x.mp3")} | {vergleichsschluessel(f"x ({n}).mp3") for n in range(2, 99)}
    with pytest.raises(NamenErschoepft):
        eindeutiger_name("x.mp3", belegt)


# --- natürliche Sortierung (data-model.md, Abschnitt 5) ---


def test_natuerliche_sortierung_beispiele_des_datenmodells():
    assert sortiere_natuerlich(["folge-10.mp3", "folge-2.mp3"]) == ["folge-2.mp3", "folge-10.mp3"]
    assert sortiere_natuerlich(["a1b.mp3", "a1.mp3"]) == ["a1.mp3", "a1b.mp3"]
    assert sortiere_natuerlich(["10.mp3", "2.mp3", "1.mp3", "01.mp3"]) == ["01.mp3", "1.mp3", "2.mp3", "10.mp3"]
    assert sortiere_natuerlich(["folge.mp3", "Folge.mp3"]) == ["Folge.mp3", "folge.mp3"]


def test_natuerliche_sortierung_wie_die_box():
    """Box und HA benutzen dieselbe Regel (data-model.md): gleiche Ergebnisse für schwierige Namen."""
    namensliste = ["b", "A2", "a10", "a2", "a02", "ä", "Z", "1", "01", "x-1", "x-01", "x1"]
    erwartet = ["01", "1", "A2", "a02", "a2", "a10", "b", "x1", "x-01", "x-1", "Z", "ä"]
    assert sortiere_natuerlich(namensliste) == erwartet


def test_natuerliche_sortierung_gleich_der_box():
    """Wenn der Quelltext der Box erreichbar ist (Repo), muss HA genauso sortieren wie die Box."""
    import importlib.util
    import sys
    from pathlib import Path

    quelle = Path(__file__).resolve().parents[2] / "box" / "src" / "tobibox" / "library.py"
    if not quelle.exists():
        pytest.skip("Quelltext der Box nicht vorhanden")
    sys.path.insert(0, str(quelle.parents[1]))
    try:
        spec = importlib.util.find_spec("tobibox.library")
        if spec is None:
            pytest.skip("tobibox.library nicht ladbar")
        library = importlib.import_module("tobibox.library")
    except Exception as err:  # fehlende Abhängigkeiten der Box in der HA-venv
        pytest.skip(f"Box-Modul nicht ladbar: {err}")
    finally:
        sys.path.remove(str(quelle.parents[1]))
    korpus = ["b", "A2", "a10", "a2", "a02", "ä", "Z", "1", "01", "x-1", "x-01", "x1", "Folge-01.mp3", "folge-01.mp3",
              "1.mp3", "01.mp3", "folge 10", "Folge 9", "CD 1/01.mp3", "cd 1/10.mp3", "", "0", "00"]
    assert sortiere_natuerlich(korpus) == library.sortiere_natuerlich(list(korpus))


# --- Folgen-Nummer aus Text: R1 bis R4 (Abschnitt 11.2) ---


@pytest.mark.parametrize(
    ("text", "nummer"),
    [
        ("Der Rabe - Folge 12: Der Wald", 12),
        ("Nr. 3", 3),
        ("Teil 2 von 3", 2),
        ("Episode 07", 7),
        ("Band #4", 4),
        ("Vol. 9", 9),
        ("3 - Der Anfang", 3),
        ("007: Gold", 7),
        ("Abenteuer #5", 5),
        ("Der Rabe (12)", 12),
        ("Das Jahr 1984", None),
        ("2000 Meilen", None),
        ("Folge 12345", None),
        ("Stepp 3", None),
        ("Ohne Zahl", None),
    ],
)
def test_nummer_aus_text(text, nummer):
    assert nummer_aus_text(text) == nummer


def test_nummer_aus_tag():
    assert nummer_aus_tag("2") == 2
    assert nummer_aus_tag(" 007") == 7
    assert nummer_aus_tag("3/12") == 3
    assert nummer_aus_tag("abc") is None


# --- Album, CD-Zusatz, Datum, Platzhalter ---


@pytest.mark.parametrize(
    ("album", "erwartet", "cd"),
    [
        ("Hörbuch X (CD 1)", "Hörbuch X", 1),
        ("Hörbuch X [Disc 2]", "Hörbuch X", 2),
        ("Hörbuch X - CD 3", "Hörbuch X", 3),
        ("Hörbuch X (CD 2/4)", "Hörbuch X", 2),
        ("Hörbuch X (Teil 2)", "Hörbuch X (Teil 2)", None),
        ("Hörbuch X", "Hörbuch X", None),
    ],
)
def test_cd_zusatz(album, erwartet, cd):
    assert album_ohne_cd_zusatz(album) == (erwartet, cd)


def test_datum():
    assert datum_aus_tag("2019") == "2019-01-01"
    assert datum_aus_tag("2019-03") == "2019-03-01"
    assert datum_aus_tag("2019-03-07") == "2019-03-07"
    assert datum_aus_tag("1899") is None
    assert datum_aus_tag("2101-01-01") is None
    assert datum_aus_tag("gestern") is None


def test_norm_und_tagwerte():
    assert namen.norm("Die drei ???") == "diedrei"
    assert namen.norm("die DREI ???") == "diedrei"
    assert namen.norm("???") == "???"  # ohne Buchstaben: gekürzter casefold-Wert
    assert namen.norm_tagwert("  Autor \x00 A \t ") == "Autor A"
    assert namen.norm_tagwert("???") == ""  # ohne Buchstabe oder Ziffer gilt als leer
    assert len(namen.norm_tagwert("x" * 500)) == 200
    assert namen.ist_platzhalter("Various Artists")
    assert namen.ist_platzhalter("Verschiedene Interpreten")
    assert namen.ist_platzhalter("N/A")
    assert not namen.ist_platzhalter("Autor A")
