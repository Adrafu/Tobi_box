"""Medien-Sync (AP 3.4): echter rsync-Daemon auf einem freien Port, Regeln, Schutz, Abbruch."""

from __future__ import annotations

import asyncio
import os
import shutil
import stat

import pytest
from sync_helfer import Ereignisse, dateien, rsync_daemon, schreibe  # noqa: F401  (Fixture)

from tobibox import events as ev
from tobibox import sync as s
from tobibox.config import SyncKonfig

pytestmark = pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync nicht installiert")

MB = 1024 * 1024


def baue(d, modul="medien", *, aktuell=None, einlesen=None, netz="home", lader=False, akku=None, **kw):
    aus = Ereignisse()

    async def datei():
        return aktuell

    sy = s.Sync(
        d.konfig(modul),
        d.box,
        ausgabe=aus,
        aktuelle_datei=datei if aktuell is not None else None,
        einlesen=einlesen,
        partial_dir=d.partial,
        **kw,
    )
    sy.setze_netz(netz)
    sy.setze_lader(lader)
    if akku is not None:
        sy.setze_akku(akku)
    return sy, aus


async def lauf(sy, grund="ha"):
    assert await sy.start(grund)
    await sy.warte_ende()


# --- Normalfall ---------------------------------------------------------------------------------------


async def test_kopiert_neue_dateien_und_liest_mpd_neu_ein(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "s1" / "a.mp3", b"a" * 1000)
    schreibe(d.quelle / "s1" / "b.mp3", b"b" * 1000)
    schreibe(d.box / "alt.mp3")  # nur auf der Box: wird gelöscht (1 von 6, unter 20 %)
    for i in range(5):
        schreibe(d.box / f"s0/{i}.mp3", b"f")
        schreibe(d.quelle / f"s0/{i}.mp3", b"f")
    schreibe(d.quelle / "@eaDir" / "mist")  # QNAP-Verzeichnis: nie übertragen
    gelesen = []

    async def einlesen():
        gelesen.append(dateien(d.box))

    sy, aus = baue(d, einlesen=einlesen)
    await lauf(sy)
    assert aus.typen[0] is ev.SyncGestartet
    assert aus.fertig() == ev.SyncFertig(neu=2, geloescht=1)
    voll = {"s1/a.mp3", "s1/b.mp3"} | {f"s0/{i}.mp3" for i in range(5)}
    assert dateien(d.box) == voll
    assert gelesen == [voll]  # erst nach der Übertragung
    assert not sy.laeuft
    # lesbar für MPD, auch wenn die Quelle andere Rechte hat
    assert stat.S_IMODE(os.stat(d.box / "s1" / "a.mp3").st_mode) & 0o444 == 0o444


async def test_zweiter_lauf_ohne_aenderung_uebertraegt_nichts(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "s1" / "a.mp3", b"a" * 1000)
    sy, aus = baue(d)
    await lauf(sy)
    aus2 = Ereignisse()
    sy2, aus2 = baue(d)
    await lauf(sy2)
    assert aus2.fertig() == ev.SyncFertig(neu=0, geloescht=0)


async def test_dateien_bleiben_unveraendert_replaygain_tags_nicht_angefasst(rsync_daemon):
    """Entscheidung J: Dateien kommen bytegleich an (Tags stammen von rsgain auf dem NAS)."""
    d = rsync_daemon
    inhalt = bytes(range(256)) * 50 + b"REPLAYGAIN_TRACK_GAIN=-3.20 dB"
    schreibe(d.quelle / "s1" / "a.mp3", inhalt)
    sy, _ = baue(d)
    await lauf(sy)
    assert (d.box / "s1" / "a.mp3").read_bytes() == inhalt


async def test_anmeldung_mit_passwort_datei_und_umgebung(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")
    sy, aus = baue(d, "gesichert")
    await lauf(sy)
    assert aus.fertig() is not None and dateien(d.box) == {"a.mp3"}
    shutil.rmtree(d.box)
    d.box.mkdir()
    k = d.konfig("gesichert", passwort_datei=None, passwort_umgebung="TB_SYNC_PW")
    aus2 = Ereignisse()
    sy2 = s.Sync(k, d.box, ausgabe=aus2, partial_dir=d.partial, umgebung={**os.environ, "TB_SYNC_PW": "geheim-nur-im-test"})
    sy2.setze_netz("home")
    await lauf(sy2)
    assert aus2.fertig() is not None and dateien(d.box) == {"a.mp3"}
    # das Passwort steht nie in der Befehlszeile
    assert "geheim" not in " ".join(sy2.befehl(["--list-only"]))


async def test_falsches_passwort_oder_fehlende_variable(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")
    k = d.konfig("gesichert", passwort_datei=None, passwort_umgebung="TB_SYNC_PW")
    aus = Ereignisse()
    sy = s.Sync(k, d.box, ausgabe=aus, partial_dir=d.partial, umgebung={**os.environ, "TB_SYNC_PW": "falsch"})
    sy.setze_netz("home")
    await lauf(sy)
    assert aus.abbruch() == "anmeldung"
    aus = Ereignisse()
    sy = s.Sync(k, d.box, ausgabe=aus, partial_dir=d.partial, umgebung={})
    sy.setze_netz("home")
    await lauf(sy)
    assert aus.abbruch() == "anmeldung"
    assert dateien(d.box) == set()


# --- Schutz der Quelle --------------------------------------------------------------------------------


async def test_leere_quelle_bricht_ab_und_laesst_die_box_unberuehrt(rsync_daemon):
    d = rsync_daemon
    schreibe(d.box / "s1" / "a.mp3")
    sy, aus = baue(d, "leer")
    await lauf(sy)
    assert aus.typen == [ev.SyncGestartet, ev.SyncAbgebrochen]
    assert aus.abbruch() == "quelle_leer"
    assert dateien(d.box) == {"s1/a.mp3"}


async def test_fehlende_quelle_bricht_ab(rsync_daemon):
    d = rsync_daemon
    schreibe(d.box / "s1" / "a.mp3")
    sy, aus = baue(d, "fehlt")
    await lauf(sy)
    assert aus.abbruch() == "quelle_fehlt"
    assert dateien(d.box) == {"s1/a.mp3"}


async def test_unbekanntes_modul_ist_quelle_fehlt(rsync_daemon):
    d = rsync_daemon
    sy, aus = baue(d, "gibt-es-nicht")
    await lauf(sy)
    assert aus.abbruch() == "quelle_fehlt"


async def test_daemon_nicht_erreichbar_ist_netz_weg(rsync_daemon):
    d = rsync_daemon
    schreibe(d.box / "a.mp3")
    k = SyncKonfig(host="127.0.0.1", port=1, reserve_mb=0)  # nichts hört auf Port 1
    aus = Ereignisse()
    sy = s.Sync(k, d.box, ausgabe=aus, partial_dir=d.partial)
    sy.setze_netz("home")
    await lauf(sy)
    assert aus.abbruch() == "netz_weg"
    assert dateien(d.box) == {"a.mp3"}


async def test_zu_viele_loeschungen_brechen_ab(rsync_daemon):
    d = rsync_daemon
    for i in range(10):
        schreibe(d.box / f"s/{i}.mp3")
    for i in range(5):  # 5 von 10 fehlen in der Quelle: 50 %
        schreibe(d.quelle / f"s/{i}.mp3")
    schreibe(d.quelle / "s/neu.mp3")
    sy, aus = baue(d)
    await lauf(sy)
    assert aus.abbruch() == "zu_viele_loeschungen"
    assert len(dateien(d.box)) == 10  # nichts gelöscht, auch nichts Neues übertragen
    assert "s/neu.mp3" not in dateien(d.box)


async def test_genau_zwanzig_prozent_loeschen_ist_erlaubt(rsync_daemon):
    d = rsync_daemon
    for i in range(10):
        schreibe(d.box / f"s/{i}.mp3")
    for i in range(8):
        schreibe(d.quelle / f"s/{i}.mp3")
    sy, aus = baue(d)
    await lauf(sy)
    assert aus.fertig() == ev.SyncFertig(neu=0, geloescht=2)
    assert len(dateien(d.box)) == 8


def test_grenze_der_loeschungen():
    assert not s.zu_viele_loeschungen(2, 10)
    assert s.zu_viele_loeschungen(3, 10)
    assert not s.zu_viele_loeschungen(0, 0)
    assert s.zu_viele_loeschungen(1, 4)


async def test_zu_wenig_platz_startet_nicht(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "s/gross.mp3", b"g" * (2 * MB))
    schreibe(d.quelle / "s/alt.mp3")
    schreibe(d.box / "s/alt.mp3")
    sy, aus = baue(d, freier_platz=lambda p: 1 * MB)
    await lauf(sy)
    assert aus.abbruch() == "kein_platz"
    assert dateien(d.box) == {"s/alt.mp3"}
    assert not d.partial.exists() or not any(d.partial.rglob("*.mp3"))


async def test_platz_reicht_mit_reserve_knapp_nicht(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "gross.mp3", b"g" * (1 * MB))
    k = d.konfig(reserve_mb=1)
    aus = Ereignisse()
    sy = s.Sync(k, d.box, ausgabe=aus, partial_dir=d.partial, freier_platz=lambda p: 2 * MB - 1)
    sy.setze_netz("home")
    await lauf(sy)
    assert aus.abbruch() == "kein_platz"


# --- Spielende Datei ----------------------------------------------------------------------------------


async def test_spielende_datei_wird_nicht_ersetzt_und_nicht_geloescht(rsync_daemon):
    d = rsync_daemon
    # a.mp3 spielt und hat sich auf dem NAS geändert; b.mp3 ändert sich auch und darf ersetzt werden
    schreibe(d.box / "s/a.mp3", b"alt-a")
    schreibe(d.box / "s/b.mp3", b"alt-b")
    schreibe(d.box / "s/spielt-nur-hier.mp3", b"nur-box")
    for i in range(6):
        schreibe(d.box / f"s/fuell{i}.mp3", b"f")
        schreibe(d.quelle / f"s/fuell{i}.mp3", b"f")
    schreibe(d.quelle / "s/a.mp3", b"neu-a-und-laenger")
    schreibe(d.quelle / "s/b.mp3", b"neu-b-und-laenger")
    sy, aus = baue(d, aktuell="s/a.mp3")
    await lauf(sy)
    assert aus.fertig() is not None
    assert (d.box / "s/a.mp3").read_bytes() == b"alt-a"
    assert (d.box / "s/b.mp3").read_bytes() == b"neu-b-und-laenger"
    # nur-Box-Datei wird gelöscht, weil sie nicht spielt (1 von 9 = 11 %)
    assert not (d.box / "s/spielt-nur-hier.mp3").exists()


async def test_spielende_datei_nur_auf_der_box_ist_vor_delete_geschuetzt(rsync_daemon):
    d = rsync_daemon
    schreibe(d.box / "s/spielt.mp3", b"nur-box")
    schreibe(d.quelle / "s/andere.mp3", b"x")
    sy, aus = baue(d, aktuell="s/spielt.mp3")
    await lauf(sy)
    assert aus.fertig() is not None
    assert dateien(d.box) == {"s/spielt.mp3", "s/andere.mp3"}


async def test_spielende_datei_mit_platzhaltern_im_namen(rsync_daemon):
    d = rsync_daemon
    schreibe(d.box / "s/a[1]*.mp3", b"alt")
    schreibe(d.box / "s/a1x.mp3", b"alt-1x")
    schreibe(d.quelle / "s/a[1]*.mp3", b"neu-spielt")
    schreibe(d.quelle / "s/a1x.mp3", b"neu-1x-laenger")
    sy, aus = baue(d, aktuell="s/a[1]*.mp3")
    await lauf(sy)
    assert (d.box / "s/a[1]*.mp3").read_bytes() == b"alt"
    assert (d.box / "s/a1x.mp3").read_bytes() == b"neu-1x-laenger"


def test_maskiere():
    assert s._maskiere("a[1]*?\\") == "a\\[1]\\*\\?\\\\"


# --- partial-dir und delay-updates ----------------------------------------------------------------------


def test_partial_dir_muss_ausserhalb_des_medienordners_liegen(tmp_path):
    k = SyncKonfig(host="h")
    medien = tmp_path / "medien"
    for innen in (medien, medien / ".partial", medien / "a" / "b"):
        with pytest.raises(ValueError):
            s.Sync(k, medien, ausgabe=lambda e: None, partial_dir=innen)
    s.Sync(k, medien, ausgabe=lambda e: None, partial_dir=tmp_path / ".rsync-partial")


def test_vorgabe_partial_dir_liegt_neben_dem_medienordner(tmp_path):
    sy = s.Sync(SyncKonfig(host="h"), tmp_path / "var" / "medien", ausgabe=lambda e: None)
    assert sy.partial_dir == tmp_path / "var" / ".rsync-partial"


async def test_befehl_hat_partial_dir_absolut_und_delay_updates(rsync_daemon):
    d = rsync_daemon
    sy, _ = baue(d)
    cmd = sy.befehl(["--delete", "--delay-updates", f"--partial-dir={sy.partial_dir}", f"--temp-dir={sy.temp_dir}"])
    assert "--delay-updates" in cmd
    assert d.box not in sy.temp_dir.parents and sy.temp_dir.parent == d.partial.parent
    teil = [c for c in cmd if c.startswith("--partial-dir=")]
    assert teil == [f"--partial-dir={d.partial}"]
    assert os.path.isabs(d.partial) and d.box not in d.partial.parents


async def test_partial_dir_gleiches_dateisystem_wird_angelegt(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")
    sy, aus = baue(d)
    await lauf(sy)
    assert d.partial.is_dir()
    assert d.partial.stat().st_dev == d.box.stat().st_dev
    assert not (d.box / ".rsync-partial").exists()
    assert sy.temp_dir.stat().st_dev == d.box.stat().st_dev and not list(sy.temp_dir.iterdir())


async def test_vorlaeufiger_befehl_echter_lauf_nutzt_delay_updates(rsync_daemon, monkeypatch):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")
    sy, aus = baue(d)
    gesehen = []
    echt = sy._rsync_lauf

    async def spion(cmd, **kw):
        gesehen.append(cmd)
        return await echt(cmd, **kw)

    monkeypatch.setattr(sy, "_rsync_lauf", spion)
    await lauf(sy)
    echter = gesehen[-1]
    assert "--delay-updates" in echter and "--delete" in echter and "--dry-run" not in echter
    assert f"--partial-dir={d.partial}" in echter and f"--temp-dir={sy.temp_dir}" in echter
    assert "--dry-run" in gesehen[1] and "-i" in gesehen[1]  # Trockenlauf mit itemize-changes
    assert all(not c.startswith("--partial-dir") for c in gesehen[0])  # Listen schreibt nichts


def test_nice_und_ionice_wenn_vorhanden(tmp_path, monkeypatch):
    sy = s.Sync(SyncKonfig(host="h"), tmp_path / "m", ausgabe=lambda e: None)
    monkeypatch.setattr(s.shutil, "which", lambda n: f"/usr/bin/{n}")
    cmd = sy.befehl(["--list-only"])
    assert cmd[:7] == ["nice", "-n", "19", "ionice", "-c", "3", "rsync"]
    # Mac: ionice fehlt
    monkeypatch.setattr(s.shutil, "which", lambda n: None if n == "ionice" else f"/usr/bin/{n}")
    cmd = sy.befehl(["--list-only"])
    assert "ionice" not in cmd and cmd[:4] == ["nice", "-n", "19", "rsync"]
    monkeypatch.setattr(s.shutil, "which", lambda n: None)
    assert sy.befehl(["--list-only"])[0] == "rsync"


# --- Netzregel ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "klasse, lader, akku, erwartet",
    [
        ("home", False, None, True),
        ("home", False, 5, True),
        ("hotspot", False, 51, True),
        ("hotspot", False, 50, False),  # genau 50 %: nicht über 50
        ("hotspot", False, 30, False),
        ("hotspot", False, None, False),  # Akku unbekannt: nein
        ("hotspot", True, 5, True),  # Lader gewinnt
        ("offline", True, 100, False),
        (None, True, 100, False),  # Netz noch nicht gemeldet
    ],
)
def test_netzregel(klasse, lader, akku, erwartet):
    assert s.regel_erlaubt(klasse, lader, akku) is erwartet


@pytest.mark.parametrize(
    "netz, lader, akku",
    [("hotspot", False, 40), ("hotspot", False, 50), ("offline", True, 90)],
)
async def test_regel_verbietet_sync_ohne_rsync_zu_starten(tmp_path, netz, lader, akku):
    aus = Ereignisse()
    sy = s.Sync(SyncKonfig(host="h"), tmp_path / "m", ausgabe=aus, rsync="/gibt/es/nicht")
    sy.setze_netz(netz)
    sy.setze_lader(lader)
    sy.setze_akku(akku)
    assert await sy.start("ha") is False
    assert aus.liste == [ev.SyncAbgebrochen("regel")]  # kein SyncGestartet
    assert not sy.laeuft


async def test_hotspot_mit_viel_akku_oder_lader_synct(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")
    sy, aus = baue(d, netz="hotspot", akku=60)
    await lauf(sy)
    assert aus.fertig() == ev.SyncFertig(1, 0)
    shutil.rmtree(d.box)
    d.box.mkdir()
    sy, aus = baue(d, netz="hotspot", akku=10, lader=True)
    await lauf(sy)
    assert aus.fertig() == ev.SyncFertig(1, 0)


async def test_hotspot_akku_aendert_sich_zwischen_zwei_anfragen(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")
    sy, aus = baue(d, netz="hotspot", akku=60)
    sy.setze_akku(45)
    assert await sy.start("ha") is False
    assert aus.abbruch() == "regel"


async def test_takt_startet_nur_nach_dem_intervall_und_meldet_keine_regel(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")
    t = [1000.0]
    sy, aus = baue(d, netz="hotspot", akku=20, mono=lambda: t[0])
    assert await sy.takt() is False and aus.liste == []  # Takt meldet bei verbotener Regel nichts
    sy.setze_netz("home")
    assert await sy.takt() is True
    await sy.warte_ende()
    t[0] += 100
    assert await sy.takt() is False  # Intervall (3600 s) nicht um
    t[0] += 3600
    assert await sy.takt() is True
    await sy.warte_ende()
    assert aus.typen.count(ev.SyncGestartet) == 2


async def test_zweiter_start_waehrend_der_sync_laeuft_wird_ignoriert(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3", b"a" * (2 * MB))
    sy, aus = baue(d, zusatz=["--bwlimit=500"])
    assert await sy.start("ha")
    assert sy.laeuft
    assert await sy.start("ha") is False
    await sy.abbrechen()
    assert aus.typen.count(ev.SyncGestartet) == 1


# --- Abbruch ------------------------------------------------------------------------------------------------


def alle_dateien(ordner):
    """Auch versteckte Dateien (rsync-Zwischendateien ``.name.XXXXXX``)."""
    return dateien(ordner)


async def warte_bis(bed, max_s=15.0):
    ende = asyncio.get_running_loop().time() + max_s
    while not bed():
        assert asyncio.get_running_loop().time() < ende, "Bedingung nicht eingetreten"
        await asyncio.sleep(0.05)


async def test_abbruch_mitten_im_sync_laesst_keine_halben_dateien_im_medienordner(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "s/gross.mp3", os.urandom(4 * MB))
    schreibe(d.box / "s/alt.mp3", b"alt")
    schreibe(d.quelle / "s/alt.mp3", b"alt")
    sy, aus = baue(d, zusatz=["--bwlimit=400"])
    assert await sy.start("ha")
    # warten, bis die Übertragung begonnen hat (halbe Datei liegt im Partial-Ordner)
    await warte_bis(lambda: any(p.is_file() and p.stat().st_size > 0 for p in d.partial.parent.rglob("*") if d.box not in p.parents))
    assert alle_dateien(d.box) == {"s/alt.mp3"}  # auch keine ``.gross.mp3.XXXX`` im Medienordner
    await sy.abbrechen("akku_tiefstand")
    assert not sy.laeuft
    assert aus.abbruch() == "akku_tiefstand"
    assert aus.typen[-1] is ev.SyncAbgebrochen and ev.SyncFertig not in aus.typen
    assert alle_dateien(d.box) == {"s/alt.mp3"}  # keine halbe Datei, auch keine versteckte Zwischendatei
    # der Rest kommt beim nächsten Lauf (setzt im Partial-Ordner fort)
    sy2, aus2 = baue(d)
    await lauf(sy2)
    assert (d.box / "s/gross.mp3").read_bytes() == (d.quelle / "s/gross.mp3").read_bytes()
    assert aus2.fertig() == ev.SyncFertig(1, 0)


async def test_netz_weg_waehrend_des_syncs_bricht_ab(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "gross.mp3", os.urandom(3 * MB))
    sy, aus = baue(d, zusatz=["--bwlimit=400"])
    assert await sy.start("ha")
    await warte_bis(lambda: any(p.is_file() and p.stat().st_size > 0 for p in d.partial.parent.rglob("*") if d.box not in p.parents))
    sy.setze_netz("offline")
    await sy.warte_ende()
    assert aus.abbruch() == "netz_weg"
    assert alle_dateien(d.box) == set()


async def test_abbrechen_ohne_sync_ist_wirkungslos(rsync_daemon):
    sy, aus = baue(rsync_daemon)
    await sy.abbrechen()
    assert aus.liste == []


async def test_fortschritt_wird_gemeldet(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "gross.mp3", os.urandom(3 * MB))
    t = [0.0]

    def uhr():
        t[0] += 2.0  # jeder Aufruf: 2 s weiter, so ist die Drosselung nie im Weg
        return t[0]

    sy, aus = baue(d, zusatz=["--bwlimit=2000"], mono=uhr)
    await lauf(sy)
    fortschritt = [e for e in aus.liste if isinstance(e, s.SyncFortschritt)]
    assert fortschritt and all(0 <= e.prozent <= 100 for e in fortschritt)
    assert aus.fertig() == ev.SyncFertig(1, 0)


async def test_ausgabe_darf_fehlschlagen(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")
    sy = s.Sync(d.konfig(), d.box, ausgabe=lambda e: 1 / 0, partial_dir=d.partial)
    sy.setze_netz("home")
    await lauf(sy)
    assert dateien(d.box) == {"a.mp3"}


async def test_einlesen_fehler_kippt_den_sync_nicht(rsync_daemon):
    d = rsync_daemon
    schreibe(d.quelle / "a.mp3")

    async def kaputt():
        raise ConnectionError("mpd weg")

    sy, aus = baue(d, einlesen=kaputt)
    await lauf(sy)
    assert aus.fertig() == ev.SyncFertig(1, 0)


async def test_rsync_fehlt_ergibt_rsync_fehler(rsync_daemon):
    d = rsync_daemon
    sy, aus = baue(d, rsync="/gibt/es/nicht")
    await lauf(sy)
    assert aus.abbruch() == "rsync_fehler"


# --- MPD-Haken -----------------------------------------------------------------------------------------------


class FalscherMpd:
    def __init__(self, song, status_folge):
        self.song = song
        self.status_folge = list(status_folge)
        self.verbunden = None
        self.aktualisiert = False
        self.getrennt = False

    async def connect(self, host, port):
        self.verbunden = (host, port)

    def disconnect(self):
        self.getrennt = True

    async def currentsong(self):
        return self.song

    async def update(self):
        self.aktualisiert = True

    async def status(self):
        return self.status_folge.pop(0) if len(self.status_folge) > 1 else self.status_folge[0]


async def test_mpd_haken_currentsong_und_einlesen():
    f = FalscherMpd({"file": "s1/a.mp3"}, [{"updating_db": "1"}, {"updating_db": "1"}, {}])

    async def nicht_schlafen(_):
        return None

    h = s.MpdHaken("localhost", 6600, fabrik=lambda: f, schlafen=nicht_schlafen)
    assert await h.aktuelle_datei() == "s1/a.mp3" and f.verbunden == ("localhost", 6600) and f.getrennt
    await h.einlesen()
    assert f.aktualisiert and f.status_folge == [{}]
    leer = s.MpdHaken("h", 1, fabrik=lambda: FalscherMpd({}, [{}]))
    assert await leer.aktuelle_datei() is None
