"""``tobibox.toml`` laden und prüfen."""

from __future__ import annotations

from pathlib import Path

import pytest

from tobibox import config
from tobibox import events as ev
from tobibox.config import KonfigFehler

MINIMAL = """
[pfade]
zustand = "var"
medien = "/srv/medien"
"""

VOLL = """
[pfade]
zustand = "~/tobibox/var"
medien = "medien"

[leser]
geraet = "/dev/serial/by-id/usb-Espressif*"

[mpd]
host = "127.0.0.1"
port = 6601

[lautstaerke]
max = 45
start = 25
kopfhoerer = 20

[protokoll]
ziel = "datei"
datei = "log/tobibox.log"
ebene = "DEBUG"
max_bytes = 500000
anzahl = 3
"""


def schreibe(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "tobibox.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_minimale_datei_mit_vorgaben(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL))
    assert k.pfade.zustand == tmp_path / "var"  # relativ zur Datei
    assert k.pfade.medien == Path("/srv/medien")
    assert (k.lautstaerke.max, k.lautstaerke.start, k.lautstaerke.kopfhoerer) == (50, 20, 30)
    assert k.protokoll.ziel == "stdout" and k.protokoll.datei is None
    assert k.mpd.port == 6600


def test_volle_datei(tmp_path):
    k = config.lade(schreibe(tmp_path, VOLL))
    assert k.pfade.zustand == Path("~/tobibox/var").expanduser()
    assert k.pfade.medien == tmp_path / "medien"
    assert k.leser.geraet.startswith("/dev/serial/by-id/")
    assert (k.mpd.host, k.mpd.port) == ("127.0.0.1", 6601)
    assert k.protokoll.datei == tmp_path / "log/tobibox.log"
    assert (k.protokoll.ebene, k.protokoll.max_bytes, k.protokoll.anzahl) == ("DEBUG", 500000, 3)


def test_geraeteeinstellungen_fuer_den_kern(tmp_path):
    k = config.lade(schreibe(tmp_path, VOLL))
    assert k.geraete_einstellungen() == ev.GeraeteEinstellungen(45, 25, 20)


def test_datei_fehlt(tmp_path):
    with pytest.raises(KonfigFehler, match="fehlt"):
        config.lade(tmp_path / "nein.toml")


def test_kein_gueltiges_toml(tmp_path):
    with pytest.raises(KonfigFehler, match="TOML"):
        config.lade(schreibe(tmp_path, "[pfade\nx"))


@pytest.mark.parametrize(
    "text,teil",
    [
        ("", "pfade"),
        ('[pfade]\nzustand = "a"\n', "medien"),
        (MINIMAL + "[lautstaerke]\nmax = 101\n", "max"),
        (MINIMAL + "[lautstaerke]\nmax = -1\n", "max"),
        (MINIMAL + "[lautstaerke]\nmax = 30\nstart = 40\n", "start"),
        (MINIMAL + '[lautstaerke]\nmax = "laut"\n', "max"),
        (MINIMAL + "[lautstaerke]\nmax = true\n", "max"),
        (MINIMAL + "[lautstaerke]\nkopfhoerer = 200\n", "kopfhoerer"),
        (MINIMAL + "[mpd]\nport = 0\n", "port"),
        (MINIMAL + '[protokoll]\nziel = "mail"\n', "ziel"),
        (MINIMAL + '[protokoll]\nziel = "datei"\n', "datei"),
        (MINIMAL + '[protokoll]\nebene = "LAUT"\n', "ebene"),
        (MINIMAL + "[unbekannt]\nx = 1\n", "unbekannt"),
        (MINIMAL + "[mpd]\nhots = 'x'\n", "hots"),
        (MINIMAL + "mpd = 3\n", "mpd"),
    ],
)
def test_ungueltige_werte(tmp_path, text, teil):
    with pytest.raises(KonfigFehler, match=teil):
        config.lade(schreibe(tmp_path, text))


def test_startlautstaerke_gleich_obergrenze_ist_erlaubt(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + "[lautstaerke]\nmax = 30\nstart = 30\n"))
    assert k.lautstaerke.start == 30


def test_beispielkonfiguration_im_repo_ist_gueltig():
    beispiel = Path(__file__).resolve().parents[2] / "config" / "tobibox.mac.example.toml"
    if not beispiel.exists():
        pytest.skip("kommt mit AP 1.4")
    config.lade(beispiel)
