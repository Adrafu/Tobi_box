"""CUJ 12 (AP 3.7): Unterwegs ohne Netz, danach daheim oder im Handy-Hotspot, als pytest-Tabelle.

* **Given**: Die Box war Tage unterwegs, ohne bekanntes Netz. Zwei unbekannte Tobies liegen in ``unknown.json``. HA hat
  inzwischen eine neue Liste (Revision 2, mit Zuordnung und Name), und auf dem NAS liegt eine neue Serie.
* **When**: Sie kommt ins Heimnetz oder in den Handy-Hotspot (``tobibox sim net``, ``tobibox sim power``).
* **Then**: Sie meldet die gesammelten Tobies und den Status an HA und holt die neue Liste. Neue Folgen holt sie nur nach den
  Regeln des Syncs: Heim immer; Hotspot nur mit Lader oder Akku über 50 %; unbekannter Akku ohne Lader nicht; offline nie.
  Kommt die Box danach heim, holt sie die Folgen nach.

Echt sind die ``App`` (mit ``net``, ``power``, ``sync`` und ``ha``), ein lokaler Mosquitto (Fake-HA) und ein rsync-Daemon
(das NAS). Die Netz-Klasse bestimmt der Test mit ``sim`` (``SimSsid``); dass „offline“ die Verbindung zu HA verhindert, bildet er
nach, indem der Broker nicht gestartet wird.
"""

from __future__ import annotations

import shutil

import pytest
from fixtures import audio
from fixtures.dienst import (
    BEKANNT,
    BOX,
    LISTE,
    NEU,
    baue_dienst,
    mpd_abschnitt,
    mqtt_abschnitt,
    netz_strom_abschnitt,
    sync_abschnitt,
)
from fixtures.ha_fake import FakeHa
from fixtures.mosquitto import GegenstelleHa, TestBroker, freier_port, warte_bis
from sync_helfer import rsync_daemon  # noqa: F401  (Fixture)

from tobibox import events as ev

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(shutil.which("rsync") is None or shutil.which("mosquitto") is None, reason="rsync oder mosquitto fehlt"),
]

NEU2 = "04ffeede"
NEUE_SERIE = "d41c7a0e93b5"
ZIEL_NEU = {"typ": "serie", "serie": NEUE_SERIE}

# (Netz-Klasse, Lader, Akku in %, kommt HA an?, holt die Box Folgen?)   ``None``: unbekannt (kein ``sim power`` für den Wert)
TABELLE = [
    pytest.param("offline", True, 100, False, False, id="offline_nie_auch_mit_lader_und_vollem_akku"),
    pytest.param("hotspot", False, 30, True, False, id="hotspot_akku_30_nur_ha"),
    pytest.param("hotspot", False, 50, True, False, id="hotspot_akku_genau_50_nur_ha"),
    pytest.param("hotspot", False, 51, True, True, id="hotspot_akku_51_synct"),
    pytest.param("hotspot", True, 5, True, True, id="hotspot_am_lader_synct_auch_bei_5_prozent"),
    pytest.param("hotspot", None, None, True, False, id="hotspot_akku_und_lader_unbekannt_nur_ha"),
    pytest.param("hotspot", None, 80, True, True, id="hotspot_lader_unbekannt_akku_80_synct"),
    pytest.param("home", False, 20, True, True, id="daheim_synct_ohne_lader"),
    pytest.param("home", None, None, True, True, id="daheim_synct_auch_bei_unbekanntem_akku"),
]


def richte_nas_ein(quelle, box_medien) -> None:
    """Das NAS: alles, was die Box hat, dazu eine neue Serie mit einer Folge."""
    shutil.copytree(box_medien, quelle, dirs_exist_ok=True)
    audio.erzeuge_serie(quelle, "neuland", ["n-01.wav", "n-02.wav"], serie_id=NEUE_SERIE, name="Neuland", dauer_s=0.5)


@pytest.fixture
async def unterwegs(tmp_path, kurz, monkeypatch, rsync_daemon):
    """Die Box ohne Netz (kein Broker), zwei gesammelte unbekannte Tobies, ein NAS mit Neuem, eine neue Liste in HA."""
    broker = TestBroker(tmp_path / "broker")  # noch nicht gestartet: die Box ist ohne Netz
    abschnitte = (
        netz_strom_abschnitt() + sync_abschnitt(rsync_daemon.port) + mqtt_abschnitt(broker.port) + mpd_abschnitt(freier_port())
    )
    d = baue_dienst(tmp_path, kurz, monkeypatch, abschnitte)
    richte_nas_ein(rsync_daemon.quelle, d.medien)
    await d.app.starte()
    await d.auflegen(NEU, "v1")
    await d.abheben("v1")
    await d.auflegen(NEU2, "v2")
    await d.abheben("v2")
    d.uhr.setze_wall(d.uhr.wall + 3 * 86400)  # Tage später (nur die Wanduhr: sonst fände idle 20 min Leerlauf und fährt herunter)
    assert set(d.unknown()) == {NEU, NEU2}
    assert d.app.status.netz == "offline"  # beim Start gemessen: kein Netz
    verbunden: list[GegenstelleHa] = []
    yield d, broker, verbunden, rsync_daemon
    for g in verbunden:
        g.stop()
    await d.app.beende()
    broker.stop()


def hat_neue_serie(d) -> bool:
    """Hat ``app`` die Bibliothek nach dem Sync neu geladen und dem Kern gegeben (``BibliothekGeladen``)?"""
    return any(s.id == NEUE_SERIE for s in d.app.bibliothek.serien) and any(s.id == NEUE_SERIE for s in d.app.kern.session.serien)


def neue_folgen_da(d) -> bool:
    return (d.medien / "neuland" / "n-01.wav").exists() and (d.medien / "neuland" / "serie.json").exists()


@pytest.mark.parametrize("klasse, lader, akku, ha_erreichbar, synct", TABELLE)
async def test_cuj12(unterwegs, klasse, lader, akku, ha_erreichbar, synct):
    d, broker, verbunden, _ = unterwegs
    assert not neue_folgen_da(d)

    # When: die Box kommt in ein Netz (Lader und Akku wie in der Tabelle)
    if lader is not None:
        await d.sim(befehl="strom", lader=lader)
    if akku is not None:
        await d.sim(befehl="strom", akku=akku)
    await d.sim(befehl="netz", klasse=klasse)
    assert d.app.status.netz == klasse and d.app.status.lader == lader and d.app.status.akku == akku

    ha = None
    if ha_erreichbar:
        broker.start()
        g = GegenstelleHa(broker.port)
        verbunden.append(g)
        ha = FakeHa(g)
        ha.revision = 1
        ha.zuordnungen = {BEKANNT: {"ziel": {"typ": "serie", "serie": "8c21d5e9a0b7"}}}
        # HA hat inzwischen eine neue Liste (Revision 2), mit Name; sie ist dauerhaft
        ha.konfig_ausrollen({**ha.zuordnungen, NEU: {"ziel": ZIEL_NEU, "name": "Fuchs"}})
        await warte_bis(lambda: d.app.ha._bereit, 25.0, "Box verbindet sich nach der Rückkehr nicht mit HA")

        # Then: gesammelte Tobies und Status kommen bei HA an
        await warte_bis(lambda: ha.meldungen(NEU) and ha.meldungen(NEU2), 10.0, "gesammelte Tobies nicht gemeldet")
        await warte_bis(lambda: ha.status() is not None, 10.0, "Status fehlt")
        s = ha.status()
        assert s["netz"] == klasse and s["akku_prozent"] == akku and s["lader"] == lader
        for uid in (NEU, NEU2):
            assert ha.meldungen(uid)[-1]["art"] == "unbekannt" and uid in d.unknown()  # bleiben bis ``ack``
        # ... und die neue Liste kommt an, samt Name
        await warte_bis(lambda: d.konfig()["revision"] == 2, 10.0, "neue Liste nicht übernommen")
        assert d.konfig()["zuordnungen"][NEU]["name"] == "Fuchs"
        for uid in (NEU, NEU2):
            ha.bestaetigen(uid, "neu" if uid == NEU2 else "bekannt")
        await warte_bis(lambda: d.unknown() == {}, 10.0, "Einträge nach dem ack nicht gelöscht")
    else:
        await d.ruhe()
        assert not d.app.ha.verbunden and set(d.unknown()) == {NEU, NEU2}  # nichts gemeldet, nichts gelöscht

    # Neue Folgen: nur nach der Regel des Syncs
    if synct:
        await warte_bis(lambda: d.app.status.sync["ergebnis"] == "ok", 20.0, "Sync läuft nicht")
        assert neue_folgen_da(d) and d.app.status.sync["neu"] >= 3
        await warte_bis(lambda: hat_neue_serie(d), 10.0, "Bibliothek nicht neu geladen")
    else:
        # ein Auslöser von HA oder aus der Zeit ändert nichts: die Regel verbietet ihn
        if ha is not None:
            ha.befehl("sync", erzeugt=_jetzt(d))
            await warte_bis(lambda: d.app.status.sync["grund"] == "regel", 10.0, "Regel meldet den Sync nicht als abgebrochen")
            assert d.app.status.sync["zustand"] == "idle" and d.app.status.sync["ergebnis"] == "abgebrochen"
        await d.zeit_vor(1)
        assert not neue_folgen_da(d) and not d.app.sync.laeuft
        assert not hat_neue_serie(d)

        # Zurück daheim: jetzt holt sie die Folgen nach (Heim immer)
        if ha is None:
            broker.start()  # daheim ist auch HA wieder da
            g = GegenstelleHa(broker.port)
            verbunden.append(g)
            ha = FakeHa(g)
        await d.sim(befehl="netz", klasse="home")
        await warte_bis(lambda: d.app.status.sync["ergebnis"] == "ok", 20.0, "daheim wird nicht nachgeholt")
        assert neue_folgen_da(d)
        await warte_bis(lambda: hat_neue_serie(d), 10.0, "Bibliothek daheim nicht neu geladen")
        await warte_bis(lambda: d.app.ha._bereit, 25.0, "Box verbindet sich daheim nicht mit HA")
        await warte_bis(lambda: ha.meldungen(NEU) and ha.meldungen(NEU2), 10.0, "gesammelte Tobies daheim nicht gemeldet")


def _jetzt(d) -> str:
    from tobibox.outbox import zeitstempel

    return zeitstempel(d.uhr.wall)


async def test_netz_weg_waehrend_des_syncs_bricht_ab_und_daheim_geht_es_weiter(unterwegs):
    """Unterwegs fällt das Netz mitten im Sync weg: Abbruch ohne halbe Dateien, später daheim vollständig."""
    d, broker, verbunden, daemon = unterwegs
    # eine große neue Datei, damit der Sync lange genug läuft
    audio.schreibe_wav(daemon.quelle / "neuland" / "n-02.wav", 30.0)
    d.app.sync._zusatz = ("--bwlimit=100",)
    await d.sim(befehl="strom", lader=True)
    await d.sim(befehl="netz", klasse="hotspot")  # Lader dran: erlaubt
    await warte_bis(lambda: d.app.sync.laeuft, 10.0, "Sync startet nicht")
    await warte_bis(lambda: any(d.app.sync.partial_dir.rglob("*")) or any(d.app.sync.temp_dir.rglob("*")), 10.0, "keine Übertragung")
    await d.sim(befehl="netz", klasse="offline")  # der Tunnel reißt ab
    await warte_bis(lambda: not d.app.sync.laeuft, 20.0, "Sync bricht nicht ab")
    assert d.app.status.sync["grund"] == "netz_weg" and d.app.status.sync["zustand"] == "fehler"
    assert not any(p.name.startswith(".") for p in d.medien.rglob("*"))  # keine Zwischendatei im Medienordner
    n2 = d.medien / "neuland" / "n-02.wav"
    assert not n2.exists() or n2.stat().st_size == (daemon.quelle / "neuland" / "n-02.wav").stat().st_size  # nie halb
    d.app.sync._zusatz = ()
    await d.sim(befehl="netz", klasse="home")
    await warte_bis(lambda: d.app.status.sync["ergebnis"] == "ok", 30.0, "daheim wird nicht fortgesetzt")
    assert n2.read_bytes() == (daemon.quelle / "neuland" / "n-02.wav").read_bytes()
