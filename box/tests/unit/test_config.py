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
        (MINIMAL + "[lautstaerke]\nmax = 25\nkopfhoerer = 26\n", "kopfhoerer"),
        ("mpd = 3\n" + MINIMAL, "mpd"),
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


def test_toene_vorgabe_und_eigenes_kommando():
    k = config.pruefe({"pfade": {"zustand": "v", "medien": "m"}}, Path("/b"))
    assert k.toene.kommando[0] == "afplay" and k.toene.ordner is None
    k = config.pruefe(
        {"pfade": {"zustand": "v", "medien": "m"}, "toene": {"kommando": ["aplay", "{datei}"], "ordner": "t"}},
        Path("/b"),
    )
    assert k.toene.kommando == ("aplay", "{datei}") and k.toene.ordner == Path("/b/t")
    with pytest.raises(KonfigFehler):
        config.pruefe({"pfade": {"zustand": "v", "medien": "m"}, "toene": {"kommando": []}}, Path("/b"))


def test_unbekannte_schluessel_sind_nur_eine_warnung(tmp_path, caplog):
    """Rollback-Sicherheit: eine neuere Datei lädt auch mit älterer Software."""
    import logging

    log = logging.getLogger("tobibox")
    zeilen = []

    class H(logging.Handler):
        def emit(self, record):
            zeilen.append(record)

    alt, level = log.handlers[:], log.level
    log.handlers = [H()]
    log.setLevel(logging.DEBUG)
    try:
        k = config.lade(schreibe(tmp_path, MINIMAL + "[unbekannt]\nx = 1\n[mpd]\nhots = 'x'\nport = 6601\n"))
    finally:
        log.handlers = alt
        log.setLevel(level)
    assert k.mpd.port == 6601
    assert [r.ereignis for r in zeilen if r.levelno == logging.WARNING] == ["unbekannte_abschnitte", "unbekannte_schluessel"]


def test_nur_max_gegeben_kappt_die_vorgaben_auf_max(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + "[lautstaerke]\nmax = 10\n"))
    assert (k.lautstaerke.max, k.lautstaerke.start, k.lautstaerke.kopfhoerer) == (10, 10, 10)


def test_kopfhoerer_darf_max_erreichen(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + "[lautstaerke]\nmax = 40\nkopfhoerer = 40\n"))
    assert k.lautstaerke.kopfhoerer == 40


def test_toene_kennlinie_vorgabe_und_eigene_werte():
    roh = {"pfade": {"zustand": "v", "medien": "m"}}
    k = config.pruefe(roh, Path("/b"))
    assert k.toene.kennlinie == "mpd_software" and k.toene.softvol_bereich_db == 51.0  # Vorgabe: Mac
    pi = {**roh, "toene": {"kennlinie": "alsa_softvol", "softvol_bereich_db": 40}}
    k = config.pruefe(pi, Path("/b"))
    assert k.toene.kennlinie == "alsa_softvol" and k.toene.softvol_bereich_db == 40.0


@pytest.mark.parametrize(
    "toene",
    [{"kennlinie": "linear"}, {"kennlinie": ""}, {"softvol_bereich_db": 0}, {"softvol_bereich_db": "viel"},
     {"softvol_bereich_db": True}, {"softvol_bereich_db": 500}],
)
def test_toene_kennlinie_ungueltig(toene):
    with pytest.raises(KonfigFehler):
        config.pruefe({"pfade": {"zustand": "v", "medien": "m"}, "toene": toene}, Path("/b"))


# --- [mqtt], [netz], [strom] (AP 3.3) ---------------------------------------------------------


def test_ohne_mqtt_netz_strom_laeuft_alles_wie_heute(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL))
    assert k.mqtt is None and k.netz is None and k.strom is None


def test_mqtt_netz_strom_voll(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + """
[mqtt]
box_id = "box1"
host = "100.64.0.7"
port = 1884
passwort = "geheim-nur-im-test"
anzeigename = "Küche"

[netz]
quelle = "networkmanager"
heim_ssid = "MeinHeim"
hotspot_ssid = "MeinHandy"
nas_host = "nas.example.ts.net"
nas_port = 874
intervall_s = 5

[strom]
quelle = "pisugar"
pisugar_port = 8424
tiefstand_prozent = 8
intervall_s = 20
abschalt_kommando = ["sudo", "poweroff"]
"""))
    m = k.mqtt
    assert (m.box_id, m.host, m.port, m.benutzer, m.passwort, m.anzeigename) == (
        "box1", "100.64.0.7", 1884, "box1", "geheim-nur-im-test", "Küche")
    assert "geheim" not in repr(m)  # das Passwort steht nie in einer Ausgabe der Konfiguration
    n = k.netz
    assert (n.quelle, n.heim_ssid, n.hotspot_ssid, n.nas_host, n.nas_port, n.intervall_s) == (
        "networkmanager", "MeinHeim", "MeinHandy", "nas.example.ts.net", 874, 5)
    assert not n.simulation
    s = k.strom
    assert (s.quelle, s.pisugar_host, s.pisugar_port, s.tiefstand_prozent, s.intervall_s) == (
        "pisugar", "127.0.0.1", 8424, 8, 20)
    assert s.abschalt_kommando == ("sudo", "poweroff")


def test_mqtt_vorgaben(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + '\n[mqtt]\nbox_id = "box2"\nhost = "broker"\n'))
    assert (k.mqtt.port, k.mqtt.benutzer, k.mqtt.anzeigename, k.mqtt.passwort) == (1883, "box2", "box2", None)


@pytest.mark.parametrize(
    "mqtt",
    [
        'host = "broker"',  # box_id fehlt
        'box_id = "Box 1"\nhost = "broker"',  # Muster
        'box_id = "b"\nhost = "broker"',  # zu kurz
        'box_id = "box1"',  # host fehlt
        'box_id = "box1"\nhost = "broker"\nport = 0',
        'box_id = "box1"\nhost = "broker"\nbenutzer = "anderer"',  # ein Konto je Box
        'box_id = "box1"\nhost = "broker"\npasswort = ""',
        'box_id = "box1"\nhost = "broker"\nanzeigename = "' + "x" * 41 + '"',
    ],
)
def test_mqtt_ungueltig(tmp_path, mqtt):
    with pytest.raises(KonfigFehler, match=r"\[mqtt\]"):
        config.lade(schreibe(tmp_path, MINIMAL + "\n[mqtt]\n" + mqtt + "\n"))


def test_netz_vorgaben_sind_simulation(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + "\n[netz]\n"))
    assert k.netz.simulation and k.netz.heim_ssid is None and k.netz.nas_host is None
    assert (k.netz.nas_port, k.netz.intervall_s) == (873, 10)


@pytest.mark.parametrize(
    "netz",
    [
        'quelle = "wlan"',
        'quelle = "networkmanager"',  # ohne SSID
        'heim_ssid = "A"\nhotspot_ssid = "A"',
        'heim_ssid = "' + "x" * 33 + '"',
        'heim_ssid = ""',
        'nas_host = "nas; rm -rf"',
        "intervall_s = 0",
    ],
)
def test_netz_ungueltig(tmp_path, netz):
    with pytest.raises(KonfigFehler, match=r"\[netz\]"):
        config.lade(schreibe(tmp_path, MINIMAL + "\n[netz]\n" + netz + "\n"))


@pytest.mark.parametrize(
    "strom",
    [
        'quelle = "usv"',
        "tiefstand_prozent = 0",
        "tiefstand_prozent = 60",
        "abschalt_kommando = []",
        'abschalt_kommando = "poweroff"',
        'pisugar_host = "a b"',
    ],
)
def test_strom_ungueltig(tmp_path, strom):
    with pytest.raises(KonfigFehler, match=r"\[strom\]"):
        config.lade(schreibe(tmp_path, MINIMAL + "\n[strom]\n" + strom + "\n"))


def test_strom_vorgaben(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + "\n[strom]\n"))
    assert k.strom.simulation and k.strom.tiefstand_prozent == 5 and k.strom.abschalt_kommando == ("systemctl", "poweroff")


def test_mqtt_passwort_wird_nicht_protokolliert():
    """Der Protokollfilter ersetzt Passwort-Schlüssel (``eventlog``), auch in verschachtelten Daten."""
    from tobibox import eventlog

    assert eventlog._bereinige({"mqtt": {"passwort": "x", "host": "h"}}) == {"mqtt": {"passwort": "***", "host": "h"}}
