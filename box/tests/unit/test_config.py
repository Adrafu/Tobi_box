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


# --- [sync] (AP 3.4) ----------------------------------------------------------------------------------------


def test_ohne_sync_abschnitt_kein_sync(tmp_path):
    assert config.lade(schreibe(tmp_path, MINIMAL)).sync is None


def test_sync_vorgaben_und_pfade(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + '\n[sync]\nhost = "qnap.tail1234.ts.net"\n'))
    s = k.sync
    assert (s.host, s.port, s.modul, s.benutzer) == ("qnap.tail1234.ts.net", 873, "medien", None)
    assert s.passwort_datei is None and s.passwort_umgebung is None and s.partial_dir is None
    assert (s.intervall_s, s.reserve_mb) == (3600, 200)


def test_sync_voll_mit_passwort_datei(tmp_path):
    text = MINIMAL + (
        '\n[sync]\nhost = "100.64.0.7"\nport = 8730\nmodul = "medien"\nbenutzer = "box1"\n'
        'passwort_datei = "geheim/sync.pw"\npartial_dir = "/var/lib/tobibox/.rsync-partial"\n'
        "intervall_s = 1800\nreserve_mb = 500\n"
    )
    s = config.lade(schreibe(tmp_path, text)).sync
    assert s.port == 8730 and s.benutzer == "box1" and s.intervall_s == 1800 and s.reserve_mb == 500
    assert s.passwort_datei == tmp_path / "geheim" / "sync.pw"
    assert s.partial_dir == Path("/var/lib/tobibox/.rsync-partial")


def test_sync_passwort_ueber_umgebungsvariable(tmp_path):
    s = config.lade(schreibe(tmp_path, MINIMAL + '\n[sync]\nhost = "h"\nbenutzer = "b"\npasswort_umgebung = "TOBIBOX_SYNC_PW"\n')).sync
    assert s.passwort_umgebung == "TOBIBOX_SYNC_PW" and s.passwort_datei is None


@pytest.mark.parametrize(
    "sync",
    [
        "",  # host fehlt
        'host = "a b"',
        'host = "rsync://h"',
        'host = "h"\nport = 0',
        'host = "h"\nport = 70000',
        'host = "h"\nmodul = "../x"',
        'host = "h"\npasswort = "klartext"',  # nie ein Passwort in der Datei
        'host = "h"\nbenutzer = "b"',  # Benutzer ohne Passwortquelle
        'host = "h"\npasswort_datei = "x"',  # Passwort ohne Benutzer
        'host = "h"\nbenutzer = "b"\npasswort_datei = "x"\npasswort_umgebung = "Y"',
        'host = "h"\nbenutzer = "b"\npasswort_umgebung = "1-falsch"',
        'host = "h"\nintervall_s = 10',
        'host = "h"\nreserve_mb = -1',
        'host = "h"\npartial_dir = "/srv/medien"',  # gleich dem Medienordner
        'host = "h"\npartial_dir = "/srv/medien/.partial"',  # innerhalb
    ],
)
def test_sync_ungueltig(tmp_path, sync):
    with pytest.raises(KonfigFehler, match=r"\[sync\]"):
        config.lade(schreibe(tmp_path, MINIMAL + "\n[sync]\n" + sync + "\n"))


def test_sync_passwort_fehlermeldung_nennt_das_passwort_nicht(tmp_path):
    with pytest.raises(KonfigFehler) as e:
        config.lade(schreibe(tmp_path, MINIMAL + '\n[sync]\nhost = "h"\npasswort = "streng-geheim"\n'))
    assert "streng-geheim" not in str(e.value)


def test_sync_vorgabe_partial_dir_ist_ausserhalb_des_medienordners(tmp_path):
    # Vorgabe ``<Medienordner>/../.rsync-partial`` bei Medienordner ``/srv/medien`` ist gültig
    config.lade(schreibe(tmp_path, MINIMAL + '\n[sync]\nhost = "h"\n'))


# --- [kopfhoerer] und [tasten] (AP 4.8) ---------------------------------------------------------


def test_ohne_kopfhoerer_und_tasten_gilt_sim(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL))
    assert k.kopfhoerer.simulation and k.kopfhoerer.gpio_pin is None and k.kopfhoerer.aktiv_niedrig and k.kopfhoerer.intervall_s == 0.2
    t = k.tasten
    assert t.simulation and (t.pin_vor, t.pin_zurueck, t.pin_dreh_a, t.pin_dreh_b, t.pin_haupt) == (None,) * 5 and t.lang_s == 1.5


def test_kopfhoerer_und_tasten_voll(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + """
[kopfhoerer]
quelle = "gpio"
gpio_pin = 17
aktiv_niedrig = false
intervall_s = 0.1

[tasten]
quelle = "gpio"
pin_vor = 5
pin_zurueck = 6
pin_dreh_a = 12
pin_dreh_b = 13
pin_haupt = 26
lang_s = 2.0
"""))
    kh, t = k.kopfhoerer, k.tasten
    assert (kh.quelle, kh.gpio_pin, kh.aktiv_niedrig, kh.intervall_s) == ("gpio", 17, False, 0.1) and not kh.simulation
    assert (t.quelle, t.pin_vor, t.pin_zurueck, t.pin_dreh_a, t.pin_dreh_b, t.pin_haupt, t.lang_s) == ("gpio", 5, 6, 12, 13, 26, 2.0)


def test_tasten_gpio_ohne_hauptknopf_pin_ist_gueltig_der_hauptknopf_kommt_vom_pisugar(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + '\n[tasten]\nquelle = "gpio"\npin_vor = 5\npin_zurueck = 6\npin_dreh_a = 12\npin_dreh_b = 13\n'))
    assert k.tasten.pin_haupt is None


@pytest.mark.parametrize(
    "abschnitt, text",
    [
        ("kopfhoerer", 'quelle = "usb"'),
        ("kopfhoerer", 'quelle = "gpio"'),  # ohne gpio_pin
        ("kopfhoerer", "gpio_pin = 99"),
        ("kopfhoerer", "gpio_pin = -1"),
        ("kopfhoerer", 'gpio_pin = "17"'),
        ("kopfhoerer", 'aktiv_niedrig = "ja"'),
        ("kopfhoerer", "intervall_s = 0.001"),
        ("kopfhoerer", "intervall_s = 100"),
        ("tasten", 'quelle = "tastatur"'),
        ("tasten", 'quelle = "gpio"'),  # ohne Pins
        ("tasten", 'quelle = "gpio"\npin_vor = 5\npin_zurueck = 6\npin_dreh_a = 12'),  # dreh_b fehlt
        ("tasten", "pin_vor = 5\npin_zurueck = 5"),  # doppelt
        ("tasten", "pin_vor = 40"),
        ("tasten", "lang_s = 0.1"),
        ("tasten", "lang_s = 60"),
        ("tasten", 'lang_s = "lang"'),
    ],
)
def test_kopfhoerer_und_tasten_ungueltig(tmp_path, abschnitt, text):
    with pytest.raises(KonfigFehler, match=rf"\[{abschnitt}\]"):
        config.lade(schreibe(tmp_path, MINIMAL + f"\n[{abschnitt}]\n{text}\n"))


def test_kopfhoerer_pin_darf_nicht_auf_einem_tastenpin_liegen(tmp_path):
    with pytest.raises(KonfigFehler, match=r"\[kopfhoerer\]"):
        config.lade(schreibe(tmp_path, MINIMAL + '\n[kopfhoerer]\nquelle = "gpio"\ngpio_pin = 5\n[tasten]\npin_vor = 5\n'))


def test_unbekannte_schluessel_in_den_neuen_abschnitten_warnen_nur(tmp_path):
    k = config.lade(schreibe(tmp_path, MINIMAL + "\n[tasten]\nneu = 1\n[kopfhoerer]\nneu = 2\n"))
    assert k.tasten.simulation and k.kopfhoerer.simulation


def test_beispielkonfiguration_mac_laedt_mit_den_platzhaltern_und_bleibt_sim():
    pfad = Path(__file__).resolve().parents[2] / "config" / "tobibox.mac.example.toml"
    k = config.lade(pfad)
    assert k.kopfhoerer.simulation and k.tasten.simulation
    text = pfad.read_text(encoding="utf-8")
    assert "[kopfhoerer]" in text and "[tasten]" in text and "gpio_pin" in text and "pin_dreh_a" in text
