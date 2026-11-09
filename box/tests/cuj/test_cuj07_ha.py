"""CUJ 7a und 7b mit Home Assistant (AP 3.7): die echte ``App``, ein echter lokaler Mosquitto und ein Fake-HA.

Der Fake-HA (``fixtures/ha_fake.py``, ``FakeHa``) tut, was die HA-Integration tut: Er veröffentlicht die Liste
(``tobibox/config``, dauerhaft), bestätigt Kennungen auf ``…/ack`` und schickt Befehle auf ``…/cmd``. Der Broker wendet die
Rechte aus ``mqtt-v1.md``, Abschnitt 7 an (die Box darf nur ihre Themen). Ersetzt sind nur Player, Leser, Töne und die Uhr
(``fixtures/dienst.py``).

**CUJ 7a** (Weg A): Ein unbekannter Tobie spielt sofort die Überraschung. Die Kennung bleibt in ``unknown.json``, bis HA
sie bestätigt (auch wenn der Broker die Nachricht schon angenommen hat). Danach schreibt HA die Zuordnung; die Box wechselt.

**CUJ 7b** (Weg B): Lernmodus per Befehl. Reihenfolge nach ``mqtt-v1.md`` 4.2: erst die Konfiguration, dann das ``ack``
(Entscheidung H). Rückfrage bei bestehender Zuordnung, Ablehnung, Abheben und Fristen.
"""

from __future__ import annotations

import asyncio

import pytest
from fixtures.dienst import BAER, BEKANNT, BOX, NEU, SERIE, UEBERRASCHUNG, baue_dienst, mqtt_abschnitt
from fixtures.ha_fake import LISTE_A, FakeHa
from fixtures.mosquitto import GegenstelleHa, TestBroker, broker, gegenstelle, warte_bis  # noqa: F401  (Fixtures)

from tobibox import events as ev
from tobibox.learn import LERN_FRIST_S
from tobibox.session import LERN_ANTWORT_FRIST_S

pytestmark = pytest.mark.asyncio

ZIEL_SERIE = {"typ": "serie", "serie": SERIE}
ZIEL_BAER = {"typ": "serie", "serie": BAER}


@pytest.fixture
async def welt(tmp_path, kurz, monkeypatch, broker, gegenstelle):
    """Eine laufende Box, verbunden mit dem Broker, und der Fake-HA. Die Liste (Revision 1) kennt nur ``BEKANNT``."""
    d = baue_dienst(tmp_path, kurz, monkeypatch, mqtt_abschnitt(broker.port))
    ha = FakeHa(gegenstelle)
    ha.revision = 1
    ha.zuordnungen = {BEKANNT: {"ziel": ZIEL_BAER}}
    await d.app.starte()
    await warte_bis(lambda: d.app.ha._bereit, text="Box hat sich nicht mit dem Broker verbunden")
    d.toene.clear()  # ohne den Startton
    yield d, ha
    await d.app.beende()


def aktuell(ha: FakeHa, uid: str, art: str | None = None) -> dict:
    m = ha.meldungen(uid)
    assert m, f"keine Meldung für {uid}"
    assert art is None or m[-1]["art"] == art, m[-1]
    return m[-1]


# ==========================================================================================================
# CUJ 7a — unbekannter Tobie, Zuordnung danach
# ==========================================================================================================


async def test_unbekannter_tobie_spielt_die_ueberraschung_und_wird_an_ha_gemeldet(welt):
    d, ha = welt
    await d.auflegen(NEU)
    assert d.abgespielt() == [UEBERRASCHUNG] and d.toene == ["unbekannt"]
    await d.warte(lambda: ha.meldungen(NEU), text="HA hat die Kennung nicht erhalten")
    m = aktuell(ha, NEU, "unbekannt")
    assert m["uid"] == NEU and m["anzahl"] == 1 and m["befehl_id"] is None and m["zeit_ok"] is True


async def test_die_kennung_bleibt_in_unknown_json_bis_ha_bestaetigt_auch_nach_dem_puback_des_brokers(welt):
    """Der Broker hat die Nachricht angenommen und an einen Abonnenten (Fake-HA) zugestellt: Der Eintrag bleibt trotzdem."""
    d, ha = welt
    await d.auflegen(NEU)
    await d.warte(lambda: ha.meldungen(NEU), text="Meldung fehlt")
    await d.ruhe()
    assert NEU in d.unknown() and d.unknown()[NEU]["art"] == "unbekannt"
    assert ha.loeschungen(NEU) == 0
    ha.bestaetigen(NEU, "neu")
    await d.warte(lambda: NEU not in d.unknown(), text="Eintrag nicht gelöscht")
    assert ha.loeschungen(NEU) == 1  # erst die dauerhafte Nachricht gelöscht (leere Nutzlast), dann der Eintrag


async def test_ack_zu_einer_aelteren_fassung_loescht_nichts(welt):
    d, ha = welt
    await d.auflegen(NEU)
    await d.warte(lambda: ha.meldungen(NEU), text="Meldung fehlt")
    alt = aktuell(ha, NEU)["zuletzt"]
    await d.abheben()
    d.uhr.vor(5)  # neue Zeitmarke
    await d.auflegen(NEU, "v2")
    await d.warte(lambda: len(ha.meldungen(NEU)) == 2, text="zweite Meldung fehlt")
    assert aktuell(ha, NEU)["anzahl"] == 2 and aktuell(ha, NEU)["zuletzt"] != alt
    ha.bestaetigen(NEU, "neu", zuletzt=alt, art="unbekannt")  # gehört zur älteren Fassung
    await asyncio.sleep(0.5)  # das ack ist beim Broker und bei der Box angekommen (Abwesenheit lässt sich nur so prüfen)
    await d.ruhe()
    assert NEU in d.unknown() and ha.loeschungen(NEU) == 0
    ha.bestaetigen(NEU, "bekannt")  # die aktuelle Fassung
    await d.warte(lambda: NEU not in d.unknown(), text="aktuelle Fassung nicht bestätigt")


@pytest.mark.parametrize(
    "ziel, erwartet_folge",
    [
        (ZIEL_SERIE, "folge-01.wav"),
        ({"typ": "folge", "serie": SERIE, "folge": "folge-02.wav"}, "folge-02.wav"),
    ],
)
async def test_zuordnung_danach_der_tobie_liegt_noch_die_box_wechselt_sofort(welt, ziel, erwartet_folge):
    d, ha = welt
    await d.auflegen(NEU)
    await d.warte(lambda: ha.meldungen(NEU), text="Meldung fehlt")
    ha.bestaetigen(NEU, "neu")
    await d.warte(lambda: NEU not in d.unknown())
    assert d.abgespielt() == [UEBERRASCHUNG]
    ha.ordne_zu(NEU, ziel, name="Rabe aus Holz")  # Tobias wählt in HA den Typ und tippt das Ziel an
    await d.warte(lambda: d.abgespielt()[-1:] == [SERIE], text="Box wechselt nicht auf das Ziel")
    z = d.app.kern.session
    assert z.figur.uid == NEU and z.datei == erwartet_folge and d.app.kern.session.modus == "spielt"
    k = d.konfig()
    assert k["revision"] == 2 and k["liste_id"] == LISTE_A
    assert k["zuordnungen"][NEU]["ziel"] == ziel and k["zuordnungen"][NEU]["name"] == "Rabe aus Holz"  # Name bleibt erhalten
    assert k["zuordnungen"][BEKANNT]["ziel"] == ZIEL_BAER


async def test_beim_naechsten_auflegen_spielt_das_neue_ziel_ohne_ton_unbekannt(welt):
    d, ha = welt
    await d.auflegen(NEU)
    await d.warte(lambda: ha.meldungen(NEU))
    ha.bestaetigen(NEU, "neu")
    ha.ordne_zu(NEU, ZIEL_SERIE)
    await d.warte(lambda: d.abgespielt()[-1:] == [SERIE])
    await d.abheben()
    d.toene.clear()
    await d.auflegen(NEU, "v2")
    assert d.abgespielt()[-1] == SERIE and d.toene == []
    await d.ruhe()
    assert ha.meldungen(NEU)[-1]["art"] == "unbekannt" and len(ha.meldungen(NEU)) == 1  # nichts mehr gemeldet


async def test_box_offline_meldet_gesammelte_kennung_sobald_ha_erreichbar_ist(tmp_path, kurz, monkeypatch):
    """Given: Box offline. Der Eintrag liegt in ``unknown.json``; sobald der Broker da ist, kommt die Meldung, und erst ``ack`` löscht."""
    b = TestBroker(tmp_path / "broker")  # noch nicht gestartet
    d = baue_dienst(tmp_path, kurz, monkeypatch, mqtt_abschnitt(b.port))
    await d.app.starte()
    try:
        await d.auflegen(NEU)
        assert d.abgespielt() == [UEBERRASCHUNG]  # die Überraschung spielt auch ohne Netz
        assert NEU in d.unknown() and not d.app.ha.verbunden
        b.start()
        try:
            g = GegenstelleHa(b.port)
            try:
                ha = FakeHa(g)
                await warte_bis(lambda: ha.meldungen(NEU), 20.0, "Box meldet die Kennung nicht nach dem Verbinden")
                assert d.app.ha.verbunden and NEU in d.unknown()
                ha.bestaetigen(NEU, "neu")
                await warte_bis(lambda: NEU not in d.unknown(), 8.0, "Eintrag nicht gelöscht")
            finally:
                g.stop()
        finally:
            await d.app.ha.stop()
            b.stop()
    finally:
        await d.app.beende()


async def test_neustart_der_box_mit_offenem_eintrag_meldet_ihn_erneut_und_ack_loescht(welt):
    d, ha = welt
    await d.auflegen(NEU)
    await d.warte(lambda: ha.meldungen(NEU))
    erste = aktuell(ha, NEU)
    await d.app.beende()
    assert NEU in d.unknown()  # blieb über das Beenden
    d.neustart()
    await d.app.starte()
    await d.warte(lambda: d.app.ha._bereit and len(ha.meldungen(NEU)) >= 2, text="offener Eintrag nicht erneut gemeldet")
    zweite = aktuell(ha, NEU)
    assert (zweite["zuerst"], zweite["zuletzt"], zweite["anzahl"]) == (erste["zuerst"], erste["zuletzt"], erste["anzahl"])  # idempotent
    ha.bestaetigen(NEU, "neu")
    await d.warte(lambda: NEU not in d.unknown())


# ==========================================================================================================
# CUJ 7b — Lernmodus
# ==========================================================================================================


async def lernen(d, ha: FakeHa, ttl_s: int = 60) -> str:
    bid = ha.befehl("lernen", ttl_s=ttl_s, erzeugt=_jetzt(d))
    await d.warte(lambda: d.lernt, text="Lernmodus beginnt nicht")
    return bid


def _jetzt(d) -> str:
    from tobibox.outbox import zeitstempel

    return zeitstempel(d.uhr.wall)


@pytest.mark.parametrize(
    "ziel, folge",
    [(ZIEL_SERIE, "folge-01.wav"), ({"typ": "folge", "serie": SERIE, "folge": "folge-03.wav"}, "folge-03.wav")],
)
async def test_lernmodus_konfiguration_vor_ack_das_gewaehlte_ziel_spielt(welt, ziel, folge):
    d, ha = welt
    bid = await lernen(d, ha)
    assert d.toene == ["lernen_beginn"]
    await d.auflegen(NEU)
    # Entscheidung H: nur der Lernton, die Box wartet still
    assert d.toene == ["lernen_beginn", "lernen_ende"] and d.abgespielt() == [] and not d.lernt
    await d.warte(lambda: ha.meldungen(NEU), text="Meldung fehlt")
    m = aktuell(ha, NEU, "gelernt")
    assert m["befehl_id"] == bid
    ha.ordne_zu(NEU, ziel, name="Neuer Tobie")
    await d.warte(lambda: NEU not in d.unknown(), text="Eintrag nach dem ack nicht gelöscht")
    assert d.abgespielt() == [SERIE] and d.app.kern.session.datei == folge
    assert d.toene == ["lernen_beginn", "lernen_ende"]  # nie ``unbekannt``, nie die Überraschung
    # Reihenfolge: die Konfiguration war da, bevor das ack den Kern erreichte (Entscheidung H, mqtt-v1.md 4.2)
    assert [t for t, _ in ha.gesendet] == ["cmd", "config", "ack"]
    assert d.gesehen("KonfigGeladen")[-1] < d.gesehen("Bestaetigt")[-1]
    assert d.konfig()["zuordnungen"][NEU]["name"] == "Neuer Tobie"


async def test_zuordnung_wirkt_auch_ohne_ack_der_eintrag_bleibt_bis_zum_ack(welt):
    d, ha = welt
    await lernen(d, ha)
    await d.auflegen(NEU)
    await d.warte(lambda: ha.meldungen(NEU))
    ha.konfig_ausrollen({**ha.zuordnungen, NEU: {"ziel": ZIEL_SERIE}})  # HA hat die Liste verteilt, das ack kommt noch nicht
    await d.warte(lambda: d.abgespielt() == [SERIE], text="Ziel startet nicht mit der Konfiguration")
    await d.ruhe()
    assert NEU in d.unknown() and d.unknown()[NEU]["art"] == "gelernt"
    ha.bestaetigen(NEU, "zugeordnet")
    await d.warte(lambda: NEU not in d.unknown(), text="ack löscht den Eintrag nicht")
    assert d.abgespielt() == [SERIE]  # kein zweiter Start


async def test_rueckfrage_bei_bestehender_zuordnung_innerhalb_der_frist_spielt_nie_das_alte_ziel(welt):
    d, ha = welt
    await lernen(d, ha)
    await d.auflegen(BEKANNT)  # schon zugeordnet (BAER): HA fragt Tobias
    assert d.abgespielt() == [] and d.toene == ["lernen_beginn", "lernen_ende"]
    await d.warte(lambda: ha.meldungen(BEKANNT))
    assert aktuell(ha, BEKANNT, "gelernt")
    await d.zeit_vor(LERN_ANTWORT_FRIST_S - 3)  # Tobias antwortet nach 7 s
    assert d.abgespielt() == []
    ha.ordne_zu(BEKANNT, ZIEL_SERIE)
    await d.warte(lambda: d.abgespielt() == [SERIE], text="neues Ziel startet nicht")
    assert BAER not in d.abgespielt()
    await d.warte(lambda: BEKANNT not in d.unknown())


async def test_rueckfrage_dauert_laenger_als_10_s_altes_ziel_spielt_dann_wechsel_mit_der_zuordnung(welt):
    """Gewollt (Entscheidung H2): Braucht Tobias länger als 10 s, spielt der bekannte Tobie erst sein altes Ziel."""
    d, ha = welt
    await lernen(d, ha)
    await d.auflegen(BEKANNT)
    await d.zeit_vor(LERN_ANTWORT_FRIST_S + 1)
    assert d.abgespielt() == [BAER]
    await d.warte(lambda: ha.meldungen(BEKANNT), text="Meldung fehlt")
    ha.ordne_zu(BEKANNT, ZIEL_SERIE)
    await d.warte(lambda: d.abgespielt() == [BAER, SERIE], text="wechselt nicht mit der späteren Zuordnung")
    await d.warte(lambda: BEKANNT not in d.unknown())


async def test_ablehnung_unbekannter_tobie_ueberraschung_mit_ton_und_erneut_gemeldet(welt):
    d, ha = welt
    await lernen(d, ha)
    await d.auflegen(NEU)
    await d.warte(lambda: ha.meldungen(NEU))
    ha.bestaetigen(NEU, "abgelehnt")
    await d.warte(lambda: d.abgespielt() == [UEBERRASCHUNG], text="Überraschung startet nicht nach der Ablehnung")
    assert d.toene == ["lernen_beginn", "lernen_ende", "unbekannt"]
    # die Outbox hat den Eintrag mit der Bestätigung gelöscht; die Box meldet ihn erneut als ``unbekannt``
    await d.warte(lambda: ha.meldungen(NEU)[-1]["art"] == "unbekannt" and NEU in d.unknown(), text="nicht erneut gemeldet")
    assert d.unknown()[NEU]["art"] == "unbekannt"
    assert d.konfig()["revision"] == 1 and NEU not in d.konfig()["zuordnungen"]


async def test_ablehnung_bekannter_tobie_spielt_sein_altes_ziel(welt):
    d, ha = welt
    await lernen(d, ha)
    await d.auflegen(BEKANNT)
    await d.warte(lambda: ha.meldungen(BEKANNT))
    ha.bestaetigen(BEKANNT, "abgelehnt")
    await d.warte(lambda: d.abgespielt() == [BAER], text="altes Ziel startet nicht")
    assert d.toene == ["lernen_beginn", "lernen_ende"]
    assert d.konfig()["zuordnungen"][BEKANNT]["ziel"] == ZIEL_BAER


async def test_abheben_waehrend_des_wartens_beendet_es_die_zuordnung_aendert_nichts_am_spielen(welt):
    """Die Zuordnung hängt an der gemeldeten Kennung, nicht am liegenden Tobie (CUJ 7b)."""
    d, ha = welt
    await lernen(d, ha)
    await d.auflegen(NEU)
    await d.warte(lambda: ha.meldungen(NEU))
    await d.abheben()
    ha.ordne_zu(NEU, ZIEL_SERIE)
    await d.warte(lambda: NEU not in d.unknown(), text="Eintrag nicht bestätigt")
    assert d.abgespielt() == [] and d.app.kern.session.figur is None
    assert d.konfig()["zuordnungen"][NEU]["ziel"] == ZIEL_SERIE  # die Zuordnung gilt trotzdem


async def test_lernmodus_endet_nach_zwei_minuten_ohne_tobie_und_abbruch_von_ha(welt):
    d, ha = welt
    await lernen(d, ha)
    await d.zeit_vor(LERN_FRIST_S + 1)
    assert not d.lernt and d.toene[-1] == "lernen_ende"
    await lernen(d, ha)
    ha.befehl("lernen_abbrechen", erzeugt=_jetzt(d), ttl_s=30)
    await d.warte(lambda: not d.lernt, text="Abbruch wirkt nicht")


async def test_befehl_wird_nur_einmal_ausgefuehrt_doppelte_zustellung_wird_erkannt(welt):
    d, ha = welt
    bid = ha.befehl("lernen", erzeugt=_jetzt(d))
    await d.warte(lambda: d.lernt)
    ha.befehl("lernen_abbrechen", erzeugt=_jetzt(d), ttl_s=30)
    await d.warte(lambda: not d.lernt)
    ha.befehl("lernen", erzeugt=_jetzt(d), id=bid)  # dieselbe ``id`` noch einmal
    await asyncio.sleep(0.5)
    await d.ruhe()
    assert not d.lernt


async def test_abgelaufener_befehl_wird_ignoriert_ohne_meldung_an_ha(welt):
    d, ha = welt
    ha.befehl("lernen", erzeugt="2020-01-01T00:00:00Z", ttl_s=60)
    await asyncio.sleep(0.5)
    await d.zeit_vor(1)
    assert not d.lernt and ha.ereignisse("befehl_abgelehnt") == []


async def test_unsichere_uhr_lehnt_den_lernbefehl_ab_und_meldet_den_grund(welt):
    d, ha = welt
    d.uhr.setze_zeit("unbekannt", False)
    bid = ha.befehl("lernen", erzeugt=_jetzt(d))
    await d.warte(lambda: ha.ereignisse("befehl_abgelehnt"), text="HA erfährt die Ablehnung nicht")
    (m,) = ha.ereignisse("befehl_abgelehnt")
    assert m["daten"]["grund"] == "zeit_unsicher" and m["daten"]["befehl_id"] == bid and m["daten"]["befehl"] == "lernen"
    assert not d.lernt


async def test_unbekannter_befehl_und_kaputte_liste_werden_an_ha_gemeldet(welt):
    d, ha = welt
    ha.g.veroeffentliche(f"tobibox/{BOX}/cmd", {"v": 1, "id": "x1", "befehl": "kaffee", "erzeugt": _jetzt(d), "ttl_s": 60, "daten": {}})
    ha.konfig_ausrollen({**ha.zuordnungen, NEU: {"ziel": ZIEL_SERIE}}, revision=7)
    await d.warte(lambda: d.konfig()["revision"] == 7)
    ha.konfig_ausrollen(revision=3)
    await d.warte(lambda: ha.ereignisse("liste_abgelehnt") and ha.ereignisse("fehler"), text="Meldungen an HA fehlen")
    assert ha.ereignisse("liste_abgelehnt")[0]["daten"]["grund"] == "revision_zu_niedrig"
    assert ha.ereignisse("fehler")[0]["daten"]["code"] == "befehl_unbekannt"
    assert d.konfig()["revision"] == 7


async def test_beenden_veroeffentlicht_zuerst_offline_und_start_online_discovery_status(welt):
    d, ha = welt
    online = f"tobibox/{BOX}/online"
    await d.warte(lambda: ha.g.auf(online) and ha.status() is not None, text="online und Status fehlen")
    assert ha.g.auf(online)[0][0] == b"online"
    assert ha.status()["netz"] == "offline" and ha.status()["zustand"] in ("leer", "pausiert")
    assert {t for t in ha.g.themen() if t.startswith("homeassistant/")}  # Discovery
    await d.app.beende()
    await d.warte(lambda: ha.g.auf(online)[-1][0] == b"offline", text="offline fehlt beim sauberen Beenden")
