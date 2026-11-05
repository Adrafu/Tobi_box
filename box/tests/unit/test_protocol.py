"""Parser gegen docs/protocol/reader-v1-examples.txt (wird zur Testzeit gelesen)."""

import re
from pathlib import Path

import pytest

from tobibox.protocol import FELDER, ZeilenFehler, parse_zeile, pruefe_befehl, schwere

BEISPIELE = Path(__file__).resolve().parents[3] / "docs" / "protocol" / "reader-v1-examples.txt"


def _entescape(text: str) -> str:
    def ersatz(m: re.Match) -> str:
        s = m.group(0)
        if s == "\\r":
            return "\r"
        if s == "\\\\":
            return "\\"
        return chr(int(s[2:], 16))

    return re.sub(r"\\r|\\\\|\\x[0-9a-fA-F]{2}", ersatz, text)


def _lade():
    zeilen = []
    for nr, roh in enumerate(BEISPIELE.read_text(encoding="utf-8").splitlines(), 1):
        if not roh.strip() or roh.startswith("#"):
            continue
        art = roh.split("|", 1)[0]
        if art in ("OK", "OKN", "ERR", "CMDOK", "CMDERR"):
            zeilen.append((nr, art, roh.split("|")))
    return zeilen


BEISPIEL_ZEILEN = _lade()


def _faelle(arten):
    return [pytest.param(nr, teile, id=f"z{nr}") for nr, art, teile in BEISPIEL_ZEILEN if art in arten]


def test_beispieldatei_ist_da_und_nicht_leer():
    assert BEISPIELE.is_file()
    arten = {art for _, art, _ in BEISPIEL_ZEILEN}
    assert arten == {"OK", "OKN", "ERR", "CMDOK", "CMDERR"}
    assert len(BEISPIEL_ZEILEN) > 100


@pytest.mark.parametrize("nr, teile", _faelle({"OK", "OKN"}))
def test_gueltige_zeilen(nr, teile):
    zeile = _entescape(teile[1])
    typ = teile[2]
    assert typ.startswith("zeile=")
    erwartet = [tuple(f.split("=", 1)) for f in teile[3:]]
    z = parse_zeile(zeile)
    assert z.typ == typ[len("zeile="):]
    assert list(z.felder.items()) == erwartet  # genau diese Felder in dieser Reihenfolge


@pytest.mark.parametrize("nr, teile", _faelle({"OK"}))
def test_kanonische_zeilen_haben_die_felder_in_tabellenreihenfolge(nr, teile):
    z = parse_zeile(_entescape(teile[1]))
    assert tuple(z.felder) == FELDER[z.typ]
    assert z.unbekannt == ()


@pytest.mark.parametrize("nr, teile", _faelle({"ERR"}))
def test_ungueltige_zeilen(nr, teile):
    zeile, grund = _entescape(teile[1]), teile[2]
    with pytest.raises(ZeilenFehler) as info:
        parse_zeile(zeile)
    assert info.value.grund == grund


@pytest.mark.parametrize("nr, teile", _faelle({"CMDOK"}))
def test_gueltige_befehle(nr, teile):
    assert pruefe_befehl(_entescape(teile[1])) == teile[2].split("=", 1)[1]


@pytest.mark.parametrize("nr, teile", _faelle({"CMDERR"}))
def test_ungueltige_befehle(nr, teile):
    with pytest.raises(ZeilenFehler) as info:
        pruefe_befehl(_entescape(teile[1]))
    assert info.value.grund == teile[2]


def test_unbekannte_zusatzfelder_werden_gemeldet_nicht_ausgewertet():
    z = parse_zeile("HB up=2 present=0 polls=10 hits=0 rejected=0 errors=0 cycle_ms=58 temp=41")
    assert z.unbekannt == ("temp",)
    assert "temp" not in z.felder


def test_crlf_wird_akzeptiert():
    assert parse_zeile("REMOVED seq=2\r").felder == {"seq": "2"}


def test_kennung_wird_unveraendert_gespeichert():
    z = parse_zeile("PLACED uid=e0040312345678ab type=iso15693 tonie=1 seq=3")
    assert z.felder["uid"] == "e0040312345678ab"


@pytest.mark.parametrize(
    "code, erwartet",
    [
        ("pn5180_no_response", "fehler"),
        ("pn5180_timeout", "fehler"),
        ("internal", "fehler"),
        ("bad_response", "warnung"),
        ("uid_invalid", "warnung"),
        ("unlock_failed", "hinweis"),
        ("bad_command", "hinweis"),
        ("future_thing", "warnung"),
    ],
)
def test_schwere_der_fehlercodes(code, erwartet):
    assert schwere(code) == erwartet
