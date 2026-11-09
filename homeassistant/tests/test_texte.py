"""Texte nur über ``strings.json`` und ``translations/de.json``: vollständig, gleich und in einfachem Deutsch."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from custom_components.tobibox.fehler import HTTP_STATUS

PAKET = Path(__file__).resolve().parents[1] / "custom_components" / "tobibox"


def lade(name: str) -> dict:
    return json.loads((PAKET / name).read_text(encoding="utf-8"))


def test_strings_und_deutsche_uebersetzung_sind_gleich():
    assert lade("strings.json") == lade("translations/de.json")


def test_jeder_fehlercode_hat_einen_klartext():
    texte = lade("strings.json")["exceptions"]
    for code in [*HTTP_STATUS, "unknown_command"]:
        assert texte[code]["message"], code


def test_jeder_im_code_benutzte_textschluessel_existiert():
    texte = lade("strings.json")["exceptions"]
    fehlt = []
    for datei in PAKET.glob("*.py"):
        quelle = datei.read_text(encoding="utf-8")
        schluessel = set(re.findall(r"""\bt\(\s*["']([a-z_0-9]+)["']""", quelle)) | set(re.findall(r"""["'](benachrichtigung_[a-z_]+)["']""", quelle))
        fehlt += [(datei.name, s) for s in sorted(schluessel) if s not in texte]
    assert fehlt == []


def test_hinweis_und_lernmodus_codes_der_seite_haben_texte():
    texte = lade("strings.json")["exceptions"]
    for code in ("datei_fehlt", "kopierschutz", "nicht_lesbar", "probedekodierung_fehlgeschlagen", "pruefung_nicht_moeglich", "ffprobe_fehlt",
                 "doppelte_id_korrigiert", "serie_json_ungueltig_repariert", "reservierter_ordner", "keine_audiodateien",
                 "verschieben_fehlgeschlagen", "doppelt", "vorgabe_serie_fehlt"):
        assert texte[f"hinweis_{code}"]["message"], code
    for grund in ("konfig_zu_gross", "konfig_nicht_bereit", "speicherfehler"):
        assert texte[f"lernmodus_{grund}"]["message"], grund
    for grund in ("revision_zu_niedrig", "schema_ungueltig", "schema_zu_neu"):
        assert texte[f"grund_{grund}"]["message"], grund


def test_dienste_in_yaml_und_strings_stimmen_ueberein():
    yaml_dienste = yaml.safe_load((PAKET / "services.yaml").read_text(encoding="utf-8"))
    text_dienste = lade("strings.json")["services"]
    assert set(yaml_dienste) == set(text_dienste)
    for name, d in yaml_dienste.items():
        felder_yaml = set(d.get("fields", {}))
        felder_text = set(text_dienste[name]["fields"])
        assert felder_yaml == felder_text, name
        assert text_dienste[name]["name"] and text_dienste[name]["description"]


def test_begriff_tobie_und_keine_modellnamen():
    alles = "\n".join(p.read_text(encoding="utf-8") for p in list(PAKET.glob("*.py")) + [PAKET / "strings.json", PAKET / "services.yaml"])
    texte = lade("strings.json")["exceptions"]
    for schluessel, wert in texte.items():
        assert "Tonie" not in wert["message"], schluessel  # Begriff F: Tonies und NFC-Karten heißen Tobies
    assert not re.search(r"\b(claude|anthropic|sonnet|haiku)\b", alles, re.IGNORECASE)  # keine Modellnamen
