"""``[sync] pfad`` und ``[sync] rsync`` (11.11., QNAP-Weg mit gemeinsamem Konto): URL, Anker der Ausschlüsse,
nur lesend, openrsync-Erkennung."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from sync_helfer import Ereignisse, dateien, rsync_daemon, schreibe  # noqa: F401  (Fixture)

from tobibox import config
from tobibox import events as ev
from tobibox import sync as s
from tobibox.config import KonfigFehler, SyncKonfig


# --- Konfiguration -------------------------------------------------------------------------------------------


def _lade(tmp_path, sync_text):
    from test_config import MINIMAL as M, schreibe as w  # die Mindest-Konfiguration der Konfigtests

    return config.lade(w(tmp_path, M + "\n[sync]\n" + sync_text + "\n"))


def test_pfad_und_rsync_vorgabe_leer(tmp_path):
    k = _lade(tmp_path, 'host = "h"').sync
    assert k.pfad is None and k.rsync is None


def test_pfad_und_rsync_gelesen(tmp_path):
    k = _lade(tmp_path, 'host = "h"\nmodul = "tobibox"\npfad = "medien"\nrsync = "/opt/homebrew/bin/rsync"').sync
    assert (k.modul, k.pfad, k.rsync) == ("tobibox", "medien", "/opt/homebrew/bin/rsync")
    assert _lade(tmp_path, 'host = "h"\npfad = "a/b.c/d_e-f"').sync.pfad == "a/b.c/d_e-f"


@pytest.mark.parametrize(
    "pfad", ["../x", "a/../b", "/medien", "medien/", "a//b", "a b", "a/./b", ".", "..", "ä", "a\\\\b", ""],
)
def test_pfad_ungueltig(tmp_path, pfad):
    with pytest.raises(KonfigFehler, match=r"\[sync\] pfad"):
        _lade(tmp_path, f'host = "h"\npfad = "{pfad}"')


def test_rsync_leer_ungueltig(tmp_path):
    with pytest.raises(KonfigFehler, match=r"\[sync\] rsync"):
        _lade(tmp_path, 'host = "h"\nrsync = " "')


# --- URL ------------------------------------------------------------------------------------------------------


def _sync(tmp_path, **kw):
    return s.Sync(SyncKonfig(host="h", **kw), tmp_path / "m", ausgabe=lambda e: None)


def test_url_ohne_pfad_wie_bisher(tmp_path):
    assert _sync(tmp_path, modul="medien")._url() == "rsync://h:873/medien/"


def test_url_mit_pfad(tmp_path):
    sy = _sync(tmp_path, modul="tobibox", pfad="medien", benutzer="box")
    assert sy._url() == "rsync://box@h:873/tobibox/medien/"
    assert _sync(tmp_path, modul="tobibox", pfad="a/b")._url() == "rsync://h:873/tobibox/a/b/"


# --- Anker der Ausschlüsse: echter Daemon, Modul = Elternordner ------------------------------------------------


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync nicht installiert")
async def test_ausschluesse_greifen_relativ_zur_quelle_mit_pfad(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "serie" / "a.mp3", b"a")
    schreibe(d.quelle / "serie" / "eingang" / "folge.mp3", b"f")  # tief: normaler Ordner
    for ordner in ("_upload", "_papierkorb", "eingang"):
        schreibe(d.quelle / ordner / "x.mp3", b"nein")
    schreibe(d.quelle.parent / "geschwister" / "y.mp3", b"nein")  # neben ``medien``: nicht in der Quelle
    schreibe(d.box / "eingang" / "alt.mp3", b"nur auf der Box")  # bleibt (Schutz vor --delete)
    aus = Ereignisse()
    sy = s.Sync(d.konfig("nas", pfad="medien"), d.box, ausgabe=aus, partial_dir=d.partial)
    sy.setze_netz("home")
    sy.setze_lader(False)
    assert await sy.start("ha")
    await sy.warte_ende()
    assert aus.abbruch() is None
    assert dateien(d.box) == {"serie/a.mp3", "serie/eingang/folge.mp3", "eingang/alt.mp3"}


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync nicht installiert")
async def test_pfad_der_nicht_existiert_ist_quelle_fehlt(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")
    aus = Ereignisse()
    sy = s.Sync(d.konfig("nas", pfad="gibt-es-nicht"), d.box, ausgabe=aus, partial_dir=d.partial)
    sy.setze_netz("home")
    sy.setze_lader(False)
    await sy.start("ha")
    await sy.warte_ende()
    assert aus.abbruch() == "quelle_fehlt"
    assert not any(isinstance(e, ev.SyncFertig) for e in aus.liste)


# --- Nur lesend: Quelle Server, Ziel lokal ---------------------------------------------------------------------

_ALLE_LAEUFE = (
    ["--list-only", "-r"],
    ["-i", "--stats", "--delete", "--dry-run"],
    ["-i", "--stats", "--delete", "--partial-dir=/x/.p", "--temp-dir=/x/.t"],
)


@pytest.mark.parametrize("optionen", _ALLE_LAEUFE)
@pytest.mark.parametrize("pfad", [None, "medien"])
def test_befehl_quelle_server_ziel_lokal(tmp_path, optionen, pfad):
    sy = _sync(tmp_path, modul="tobibox", pfad=pfad, benutzer="box")
    cmd = sy.befehl(optionen, ["/spielt/x.mp3"])
    quellen = [a for a in cmd if a.startswith("rsync://")]
    assert len(quellen) == 1
    i = cmd.index(quellen[0])
    if "--list-only" in optionen:
        assert i == len(cmd) - 1  # nur Auflisten: kein Ziel
    else:
        assert i == len(cmd) - 2  # Quelle vor Ziel
        assert cmd[-1] == str(sy.medien) + "/" and Path(cmd[-1]).is_absolute()
    # kein Argument, das nach Server-Ziel aussieht (host:pfad), und keine Option, die am Server schreibt oder löscht
    for a in cmd:
        assert not a.startswith(("--remove", "--del-source"))
        assert a == quellen[0] or "://" not in a
    s.pruefe_nur_lesend(cmd)


@pytest.mark.parametrize(
    "cmd",
    [
        ["rsync", "-rt", "/lokal/", "rsync://h/m/"],  # Server als Ziel
        ["rsync", "-rt", "rsync://h/m/", "rsync://h/m2/"],  # zwei Server
        ["rsync", "-rt", "rsync://h/m/", "h:/pfad/"],  # entferntes Ziel per Shell
        ["rsync", "-rt", "rsync://h/m/", "relativ/"],  # Ziel nicht absolut
        ["rsync", "-rt", "--remove-source-files", "rsync://h/m/", "/lokal/"],
        ["rsync", "-rt", "rsync://h/m/", "/a/", "/b/"],
        ["rsync", "-rt", "/lokal/"],  # gar keine Quelle am Server
    ],
)
def test_pruefe_nur_lesend_lehnt_ab(cmd):
    with pytest.raises(ValueError):
        s.pruefe_nur_lesend(cmd)


def test_zusatz_mit_schreibender_option_wird_abgelehnt(tmp_path):
    sy = s.Sync(SyncKonfig(host="h"), tmp_path / "m", ausgabe=lambda e: None, zusatz=["--remove-source-files"])
    with pytest.raises(ValueError):
        sy.befehl(["-i"])


# --- openrsync / altes rsync -----------------------------------------------------------------------------------

_OPENRSYNC = "openrsync: protocol version 29\nrsync version 2.6.9 compatible\n"
_ALT = "rsync  version 2.6.9  protocol version 29\nCopyright (C) 1996-2006 by Andrew Tridgell\n"
_GUT = "rsync  version 3.4.1  protocol version 32\nCopyright (C) 1996-2025 by Andrew Tridgell\n"


@pytest.mark.parametrize("text", [_OPENRSYNC, _ALT, "irgendwas ohne Version", ""])
def test_zu_altes_rsync_wird_abgelehnt(text):
    with pytest.raises(s.RsyncUngeeignet, match=r"brew install rsync"):
        s.pruefe_rsync_ausgabe(text, "/usr/bin/rsync")


@pytest.mark.parametrize("text", [_GUT, "rsync  version 3.0.9  protocol version 30\n"])
def test_neues_rsync_passt(text):
    s.pruefe_rsync_ausgabe(text)


def _fake_rsync(tmp_path, ausgabe):
    prog = tmp_path / "rsync"
    prog.write_text(f"#!/bin/sh\ncat <<'EOF'\n{ausgabe}EOF\n")
    prog.chmod(0o755)
    return str(prog)


def test_pruefe_rsync_fragt_version_ab(tmp_path):
    with pytest.raises(s.RsyncUngeeignet, match=r"openrsync"):
        s.pruefe_rsync(_fake_rsync(tmp_path, _OPENRSYNC))
    s.pruefe_rsync(_fake_rsync(tmp_path, _GUT))


def test_pruefe_rsync_fehlendes_programm(tmp_path):
    with pytest.raises(s.RsyncUngeeignet, match=r"brew install rsync"):
        s.pruefe_rsync(str(tmp_path / "gibt-es-nicht"))


def test_dienst_start_bricht_mit_klarer_meldung_ab(tmp_path, capsys):
    from tobibox import app
    from test_config import MINIMAL as M

    prog = _fake_rsync(tmp_path, _OPENRSYNC)
    kfg = tmp_path / "tobibox.toml"
    kfg.write_text(M + f'\n[sync]\nhost = "h"\nrsync = "{prog}"\n')
    assert app.main(["--config", str(kfg)]) == 2
    assert "brew install rsync" in capsys.readouterr().err


# --- Systemdateien (11.11.) ------------------------------------------------------------------------------------

_SYSTEM = [
    ".DS_Store", ".ds_store", "._folge.mp3", "Thumbs.db", "THUMBS.DB", "desktop.ini", "Desktop.INI",
    "@eaDir/x.mp3", "@Recycle/x.mp3", ".@__thumb/x.jpg", ".@__qini", "#recycle/x.mp3", "#Recycle/y.mp3",
    "$RECYCLE.BIN/x.mp3", "serie/.DS_Store", "serie/._a.mp3", "serie/@eaDir/z", "serie/Thumbs.db",
]


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync nicht installiert")
async def test_systemdateien_kommen_nie_auf_die_box_und_lokale_bleiben(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "serie" / "a.mp3", b"a")
    for n in _SYSTEM:
        schreibe(d.quelle / n, b"nein")
    schreibe(d.box / "lokal" / ".DS_Store", b"lokal")  # nur auf der Box: --delete lässt es liegen
    aus = Ereignisse()
    sy = s.Sync(d.konfig("nas", pfad="medien"), d.box, ausgabe=aus, partial_dir=d.partial)
    sy.setze_netz("home")
    sy.setze_lader(False)
    assert await sy.start("ha")
    await sy.warte_ende()
    assert aus.abbruch() is None
    assert dateien(d.box) == {"serie/a.mp3", "lokal/.DS_Store"}


# --- Cover (12.11., Paket A4b) ---------------------------------------------------------------------------------

_COVER = [
    "serie/cover.jpg", "serie/cover-eigen.jpg", "serie/cover.png", "serie/folder.jpg",
    "serie/COVER.JPG", "serie/Cover.Png", "serie/Folder.JPG", "serie/folge2/cover.jpg", "cover.jpg",
]


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync nicht installiert")
async def test_cover_kommen_nicht_auf_die_box_und_bestehende_bleiben(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "serie" / "a.mp3", b"a")
    schreibe(d.quelle / "serie" / "serie.json", b"{}")
    schreibe(d.quelle / "serie" / "folge2" / "b.mp3", b"b")
    schreibe(d.quelle / "serie" / "cover.txt", b"anderes")  # kein Cover-Name: kommt mit
    schreibe(d.quelle / "serie" / "mein-cover.jpg", b"anderes")  # nicht ``cover*``: kommt mit
    for n in _COVER:
        schreibe(d.quelle / n, b"bild")
    schreibe(d.box / "alt" / "cover.jpg", b"schon da")  # Vertrag: --exclude schützt vor --delete, bleibt liegen
    aus = Ereignisse()
    sy = s.Sync(d.konfig("nas", pfad="medien"), d.box, ausgabe=aus, partial_dir=d.partial)
    sy.setze_netz("home")
    sy.setze_lader(False)
    assert await sy.start("ha")
    await sy.warte_ende()
    assert aus.abbruch() is None
    assert dateien(d.box) == {
        "serie/a.mp3", "serie/serie.json", "serie/folge2/b.mp3", "serie/cover.txt", "serie/mein-cover.jpg",
        "alt/cover.jpg",
    }
