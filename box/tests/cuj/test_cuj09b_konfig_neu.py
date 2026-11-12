"""CUJ 9b (12.11.): Neue Medien in HA zugeordnet. Die Box hat die Liste sofort, die Dateien aber erst nach einem Sync.

* **Given**: Tobias lädt in HA neue Medien hoch und ordnet einem Tobie die neue Serie zu. Die Box hat die Dateien noch nicht.
* **When**: Die neue Konfiguration kommt an (``KonfigGeladen``), oder der Tobie wird aufgelegt.
* **Then**: Die Box startet **sofort** einen Sync (Grund ``konfig_neu``, beim Auflegen ``ziel_fehlt``), unter denselben Regeln wie
  jeder Sync (Netz-Klasse, Hotspot nur mit Strom oder Akku über 50 %, nicht beim Herunterfahren, nicht doppelt). Ist keiner erlaubt,
  steht nur ein Protokolleintrag ``sync`` / ``nicht_erlaubt``. Nach dem Sync lädt ``app`` die Bibliothek neu; ein danach neu
  aufgelegter Tobie spielt das richtige Ziel. Ist das Ziel schon da, gibt es keinen Sync.
"""

from __future__ import annotations

from conftest import CujBox, mk_konfig
from fixtures import audio
from fixtures.stufe4 import serie, ueberraschung

from tobibox import events as ev

UID = "04a1b2c3"  # bisheriger Tobie, Serie ``rabe``
UID_NEU = "04a1b2c9"  # Tobie, dem in HA die neue Serie ``fuchs`` zugeordnet wird
RABE = "3f9a1c07b2d4"
FUCHS = "8d2e4f6a1b3c"


def aufbau(medien):
    serie(medien, "rabe", ["a.wav", "b.wav"], RABE, "Rabe", 30.0)
    ueberraschung(medien)


def neue_box(tmp_path, klasse="home", strom=False, akku=80) -> CujBox:
    b = CujBox(tmp_path, {UID: ev.Zuordnung("serie", RABE)}, aufbau)
    b.sende(ev.AkkuStand(akku))
    b.sende(ev.LaderGeaendert(strom))
    b.sende(ev.NetzKlasse(klasse))
    b.laufe(15.0)
    b.sende(ev.SyncAbgebrochen("regel"))  # der Start-Sync am Lader (falls Strom) ist beantwortet
    return b


def konfig_mit_neuer_serie(box: CujBox, revision: int = 2) -> list:
    box.zuordnungen[UID_NEU] = ev.Zuordnung("serie", FUCHS)
    return box.sende(ev.KonfigGeladen(mk_konfig(box.zuordnungen, revision=revision)))


def syncs(box, ab=0):
    return [b.grund for b in box.befehle(ev.SyncStarten, ab)]


def nicht_erlaubt(box):
    return [p for p in box.protokoll if p.ereignis == "sync" and p.ergebnis == "nicht_erlaubt"]


def test_neue_serie_im_heimnetz_startet_sofort_einen_sync(tmp_path):
    box = neue_box(tmp_path)
    konfig_mit_neuer_serie(box)
    assert syncs(box) == ["konfig_neu"]


def test_nach_dem_sync_spielt_der_neu_aufgelegte_tobie_das_richtige_ziel(tmp_path):
    box = neue_box(tmp_path, "home")
    konfig_mit_neuer_serie(box)
    assert syncs(box) == ["konfig_neu"]
    box.auflege(UID_NEU)  # vor dem Sync: die Überraschung
    assert box.kern.session.serie_id != FUCHS
    box.hebe_ab()
    # der Sync bringt die Dateien, ``app`` lädt die Bibliothek neu
    serie(box.medien, "fuchs", ["f1.wav"], FUCHS, "Fuchs", 30.0)
    box.sende(ev.SyncGestartet())
    box.sende(ev.SyncFertig(1, 0))
    box.sende(box._library.lade_bibliothek(box.medien).ereignis())
    box.auflege(UID_NEU, "v2")
    assert box.kern.session.serie_id == FUCHS
    assert box.befehle(ev.Abspielen)[-1].serie_id == FUCHS


def test_hotspot_ohne_strom_bei_30_prozent_kein_sync(tmp_path):
    box = neue_box(tmp_path, "hotspot", strom=False, akku=30)
    konfig_mit_neuer_serie(box)
    assert syncs(box) == []
    p = nicht_erlaubt(box)
    assert len(p) == 1 and p[0].daten["grund"] == "regel" and p[0].daten["sync_grund"] == "konfig_neu"


def test_hotspot_mit_strom_oder_viel_akku_syncht(tmp_path):
    assert syncs(_nach_konfig(tmp_path / "a", "hotspot", True, 30)) == ["konfig_neu"]
    assert syncs(_nach_konfig(tmp_path / "b", "hotspot", False, 60)) == ["konfig_neu"]


def _nach_konfig(pfad, klasse, strom, akku):
    pfad.mkdir()
    box = neue_box(pfad, klasse, strom, akku)
    n = len(box.log)
    konfig_mit_neuer_serie(box)
    box.log = box.log[n:]
    return box


def test_sync_laeuft_schon_startet_keinen_zweiten(tmp_path):
    box = neue_box(tmp_path)
    box.sende(ev.SyncGestartet())
    konfig_mit_neuer_serie(box)
    assert syncs(box) == []


def test_ziel_schon_vorhanden_kein_sync(tmp_path):
    box = neue_box(tmp_path)
    box.zuordnungen[UID_NEU] = ev.Zuordnung("serie", RABE)  # zweiter Tobie, gleiche (vorhandene) Serie
    box.sende(ev.KonfigGeladen(mk_konfig(box.zuordnungen, revision=2)))
    box.auflege(UID_NEU)
    assert syncs(box) == []


def test_auflegen_mit_fehlendem_ziel_syncht_hoechstens_alle_60_s(tmp_path):
    box = neue_box(tmp_path)
    konfig_mit_neuer_serie(box)  # Versuch 1 (konfig_neu)
    box.sende(ev.SyncGestartet())
    box.sende(ev.SyncAbgebrochen("rsync_fehler"))
    box.auflege(UID_NEU)
    assert syncs(box) == ["konfig_neu"]  # seit dem letzten Versuch < 60 s
    box.hebe_ab()
    box.laufe(61.0)
    box.auflege(UID_NEU, "v2")
    assert syncs(box) == ["konfig_neu", "ziel_fehlt"]


def test_fehlende_folge_syncht(tmp_path):
    box = neue_box(tmp_path)
    box.zuordnungen[UID_NEU] = ev.Zuordnung("folge", RABE, "gibt-es-nicht.wav")
    box.sende(ev.KonfigGeladen(mk_konfig(box.zuordnungen, revision=2)))
    assert syncs(box) == ["konfig_neu"]


def test_beim_herunterfahren_kein_sync(tmp_path):
    box = neue_box(tmp_path)
    box.sende(ev.Hauptknopf("lang"))
    assert box.kern.teil["idle"].modus == "herunterfahren"
    konfig_mit_neuer_serie(box)
    assert syncs(box) == []
