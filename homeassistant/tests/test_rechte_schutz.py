"""Paket A1 „Rechte und Schutz“ (Vertrag W, 2.1 und 2.4; Design 10.2 und 10.3).

* Tabelle 2.1 als Parametertest: jeder Befehl der Vertragsübersicht in genau einer Zeile, Administrator und Normal-Benutzer.
* Die Schutzregeln für Nicht-Administratoren einzeln.
* Papierkorb: keine Mitteilung (AC3), Protokoll, ``geloescht_von``, ``papierkorb/restore_letzte_stunde``.
* Frühere Stände der Liste, ``stand`` einer Serie.
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from pathlib import Path

import pytest
from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.components import persistent_notification
from pytest_homeassistant_custom_component.common import CLIENT_ID

from custom_components.tobibox import const
from custom_components.tobibox.media import Serie
from custom_components.tobibox.schutz import Nutzer

from .conftest import braucht_ffmpeg, erzeuge_audio, warte_auf
from .test_upload import formular, post
from .test_websocket_api import fehler, ok, senden

UID = "e0040312345678ab"
UID2 = "04a1b2c3"
UID3 = "04a1b2c4"
SERIE = {"typ": "serie", "serie": "rabe"}
SERIE_ZWEI = {"typ": "serie", "serie": "zwei"}
FOLGE = {"typ": "folge", "serie": "rabe", "folge": "a.mp3"}
AKTION = {"typ": "aktion", "aktion": "status"}
GIB = 1024**3

VERTRAG = Path(__file__).resolve().parents[2] / "docs" / "protocol" / "ha-websocket-v1.md"


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


async def _client(hass, hass_ws_client, name: str):
    nutzer = await hass.auth.async_create_user(name, group_ids=[GROUP_ID_USER])
    refresh = await hass.auth.async_create_refresh_token(nutzer, CLIENT_ID)
    client = await hass_ws_client(hass, hass.auth.async_create_access_token(refresh))
    client.nutzer = nutzer
    return client


@pytest.fixture
async def bestand(integration, nas, lege_mp3, box_fabrik):
    """Serien ``rabe`` (a.mp3, b.mp3) und ``zwei`` (c.mp3), Box ``box1`` online, Kennung ``UID`` als neuer Tobie gemeldet."""
    pfad = nas.serie("rabe", "rabe", "Der kleine Rabe", ["a.mp3", "b.mp3"])
    lege_mp3(pfad / "a.mp3")
    lege_mp3(pfad / "b.mp3")
    pfad2 = nas.serie("zwei", "zwei", "Zweite Serie", ["c.mp3"])
    lege_mp3(pfad2 / "c.mp3")
    await integration.medien.pruefen()
    box = box_fabrik("box1")
    await box.online()
    await box.status()
    await box.unbekannt(UID)
    return box


@pytest.fixture
async def admin(hass, bestand, hass_ws_client):
    return await hass_ws_client(hass)


@pytest.fixture
async def normal(hass, bestand, hass_ws_client):
    return await _client(hass, hass_ws_client, "Normal")


@pytest.fixture
async def normal2(hass, bestand, hass_ws_client):
    return await _client(hass, hass_ws_client, "Zweiter")


def notizen(hass, praefix: str) -> dict:
    return {k: v for k, v in persistent_notification._async_get_or_create_notifications(hass).items() if k.startswith(praefix)}


# --------------------------------------------------------------------------
# Tabelle 2.1: jeder Befehl der Übersicht in einer Zeile
# --------------------------------------------------------------------------

# (Nr., Befehl, Recht, Eingabe, Antwort des Administrators: None = Erfolg, sonst Fehlercode, gebaut)
# ``gebaut=False``: Befehl gehört zu einem späteren Paket (A3 bis A5); das Backend kennt ihn noch nicht (``unknown_command``).
TABELLE = [
    (1, "hello", "lesen", {"v": 1}, None, True),
    (2, "subscribe", "lesen", {}, None, True),
    (3, "serien/list", "lesen", {}, None, True),
    (4, "serie/get", "lesen", {"serie_id": "rabe"}, None, True),
    (5, "serie/create", "admin", {"name": "Neue Serie"}, None, True),
    (6, "serie/rename", "alltag", {"serie_id": "rabe", "name": "Neu"}, None, True),
    (7, "folgen/order", "admin", {"serie_id": "rabe", "folgen": ["b.mp3", "a.mp3"]}, None, True),
    (8, "folge/delete", "alltag", {"serie_id": "rabe", "folge": "b.mp3"}, None, True),
    (9, "medien/pruefen", "alltag", {}, None, True),
    (10, "papierkorb/list", "lesen", {}, None, True),
    (11, "papierkorb/restore", "admin", {"eintrag_id": "0123456789ab"}, "eintrag_nicht_gefunden", True),
    (12, "papierkorb/empty", "admin", {"bestaetigt": True, "eintrag_ids": []}, None, True),
    (13, "neue_tobies/list", "lesen", {}, None, True),
    (14, "neue_tobies/verwerfen", "alltag", {"uid": UID}, None, True),
    (15, "zuordnung/list", "lesen", {}, None, True),
    (16, "zuordnung/set", "alltag", {"uid": UID, "ziel": SERIE, "name": "Rabe"}, None, True),
    (17, "zuordnung/remove", "alltag", {"uid": UID2, "erwartet_ziel": None}, None, True),
    (18, "lernmodus/start", "admin", {"box": "box1", "ziel": SERIE}, None, True),
    (19, "lernmodus/antwort", "admin", {"befehl_id": "x", "ueberschreiben": True}, "kein_lernmodus", True),
    (20, "lernmodus/abbrechen", "admin", {"box": "box1"}, None, True),
    (21, "boxen/list", "lesen", {}, None, True),
    (22, "box/sync", "admin", {"box": "box1"}, None, True),
    (23, "liste/neu_ausrollen", "admin", {"bestaetigt": True}, None, True),
    (24, "serie/delete", "alltag", {"serie_id": "zwei"}, None, True),
    (25, "folge/rename", "alltag", {"serie_id": "rabe", "folge": "a.mp3", "name": "Eins"}, None, True),
    (26, "folge/verschieben", "alltag", {"serie_id": "rabe", "folge": "a.mp3", "ziel_serie_id": "zwei"}, None, True),
    (27, "serien/zusammenfuehren", "admin", {"quelle_id": "rabe", "ziel_id": "zwei"}, None, True),
    (28, "einsortierung/bestaetigen", "alltag", {"serie_id": "rabe"}, None, True),
    (29, "eingang/list", "lesen", {}, None, True),
    (30, "eingang/sortieren", "alltag", {}, None, True),
    (31, "konfig/export_lesen", "admin", {}, None, True),
    (32, "konfig/aus_export", "admin", {"bestaetigt": True}, None, True),
    (33, "eingang/entfernen", "admin", {"eintrag_id": "gibtsnicht", "bestaetigt": True}, "eintrag_nicht_gefunden", True),
    (34, "konfig/get", "lesen", {}, None, True),
    (35, "einstellungen/get", "lesen", {}, None, True),
    (36, "einstellungen/set", "alltag", {"gute_nacht": {"timer_min": 20, "ausblenden_s": 30}}, None, True),
    (37, "folgen/list", "lesen", {"text": "rabe", "filter": ["ohne_tobie"], "limit": 10}, None, True),
    (38, "serie/art_setzen", "alltag", {"serie_id": "rabe", "art": "hoerbuch"}, None, True),
    (39, "audio/bereit", "alltag", {"serie_id": "rabe", "folge_id": "a.mp3"}, None, True),
    (40, "hoerstelle/get", "lesen", {}, None, False),
    (41, "hoerstelle/set", "alltag", {}, None, False),
    (42, "hoerstelle/liste", "lesen", {}, None, False),
    (43, "einsortierung/neu", "alltag", {}, None, False),
    (44, "cover/neu_suchen", "admin", {}, None, True),
    (45, "hoerkopie/neu_erzeugen", "admin", {}, None, False),
    (46, "papierkorb/restore_letzte_stunde", "admin", {"bestaetigt": True}, None, True),
    (47, "warteschlange/set", "alltag", {"box": "box1", "ziel": SERIE}, None, True),
    (48, "warteschlange/list", "alltag", {}, None, True),
    (49, "warteschlange/abbrechen", "alltag", {"eintrag_id": "0123456789ab"}, None, True),
]
IDS = [f"{z[0]:02d}-{z[1]}" for z in TABELLE]


def vertrags_uebersicht() -> dict[str, tuple[int, str]]:
    """Die Übersicht in Abschnitt 3 des Vertrags: Befehl -> (Nr., Recht)."""
    text = VERTRAG.read_text(encoding="utf-8")
    teil = text[text.index("### Übersicht") : text.index("### Gemeinsame Objekte")]
    return {m[2]: (int(m[1]), m[3]) for m in re.finditer(r"^\| (\d+) \| `tobibox/([a-z_/]+)` \| ([a-z]+) \|", teil, re.MULTILINE)}


def test_tabelle_enthaelt_jeden_befehl_der_vertragsuebersicht_genau_einmal():
    uebersicht = vertrags_uebersicht()
    assert len(uebersicht) == 49  # seit 13.11. (A0-Q) mit den Befehlen 47 bis 49
    assert [z[1] for z in TABELLE] == [b for b, _ in sorted(uebersicht.items(), key=lambda kv: kv[1][0])]
    for nr, befehl, recht, *_ in TABELLE:
        assert uebersicht[befehl] == (nr, recht), befehl


async def _rufe(client, befehl: str, felder: dict):
    return await senden(client, befehl, **felder)


@pytest.mark.parametrize(("nr", "befehl", "recht", "felder", "admin_code", "gebaut"), TABELLE, ids=IDS)
async def test_tabelle_2_1_administrator(admin, nr, befehl, recht, felder, admin_code, gebaut):
    antwort = await _rufe(admin, befehl, felder)
    if not gebaut:
        assert antwort["success"] is False and antwort["error"]["code"] == "unknown_command"
    elif admin_code is None:
        assert antwort["success"] is True, antwort
    else:
        assert antwort["success"] is False and antwort["error"]["code"] == admin_code, antwort


@pytest.mark.parametrize(("nr", "befehl", "recht", "felder", "admin_code", "gebaut"), TABELLE, ids=IDS)
async def test_tabelle_2_1_normal_benutzer(normal, nr, befehl, recht, felder, admin_code, gebaut):
    antwort = await _rufe(normal, befehl, felder)
    if not gebaut:
        assert antwort["success"] is False and antwort["error"]["code"] == "unknown_command"
    elif recht == "admin":
        assert antwort["success"] is False and antwort["error"]["code"] == "unauthorized", antwort
    elif admin_code is None:
        assert antwort["success"] is True, antwort
    else:
        assert antwort["success"] is False and antwort["error"]["code"] == admin_code, antwort


async def test_hello_sagt_nur_zu_was_gebaut_ist(admin, normal):
    for client in (admin, normal):
        f = (await ok(client, "hello", v=1))["faehigkeiten"]
        assert f[-6:] == ["konfig_staende", "bibliothek", "einsortier_wunsch", "cover", "warteschlange", "zuordnung_rueckgaengig"]  # A1, A3, A3d, A4, A9c
        for spaeter in ("reinhoeren", "hoerkopie"):
            assert spaeter not in f
    assert (await ok(admin, "hello", v=1))["darf_schreiben"] is True
    assert (await ok(normal, "hello", v=1))["darf_schreiben"] is False


# --------------------------------------------------------------------------
# Schutz: zuordnung/remove und zuordnung/set
# --------------------------------------------------------------------------


async def test_remove_ohne_erwartet_ziel_ist_fuer_nicht_admins_unauthorized(admin, normal, integration):
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE)
    assert await fehler(normal, "zuordnung/remove", uid=UID) == "unauthorized"
    assert UID in integration.store.konfig["zuordnungen"]
    assert await fehler(normal, "zuordnung/remove", uid=UID, erwartet_ziel=SERIE_ZWEI) == "zuordnung_geaendert"
    assert UID in integration.store.konfig["zuordnungen"]
    await ok(normal, "zuordnung/remove", uid=UID, erwartet_ziel=SERIE)
    assert UID not in integration.store.konfig["zuordnungen"]
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE)
    await ok(admin, "zuordnung/remove", uid=UID)  # Administratoren brauchen es nicht


async def test_set_mit_ueberschreiben_braucht_erwartet_ziel(admin, normal, integration):
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE)
    assert await fehler(normal, "zuordnung/set", uid=UID, ziel=SERIE_ZWEI, ueberschreiben=True) == "unauthorized"
    assert integration.store.konfig["zuordnungen"][UID]["ziel"] == SERIE
    assert await fehler(normal, "zuordnung/set", uid=UID, ziel=SERIE_ZWEI) == "zuordnung_existiert"
    assert await fehler(normal, "zuordnung/set", uid=UID, ziel=SERIE_ZWEI, ueberschreiben=True, erwartet_ziel=SERIE_ZWEI) == "zuordnung_geaendert"
    await ok(normal, "zuordnung/set", uid=UID, ziel=SERIE_ZWEI, ueberschreiben=True, erwartet_ziel=SERIE)
    assert integration.store.konfig["zuordnungen"][UID]["ziel"] == SERIE_ZWEI
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE, ueberschreiben=True)  # Administrator ohne erwartet_ziel


async def test_set_nur_fuer_bekannte_kennungen(admin, normal, integration):
    assert await fehler(normal, "zuordnung/set", uid=UID2, ziel=SERIE) == "kennung_ungueltig"
    assert UID2 not in integration.store.konfig["zuordnungen"]
    await ok(admin, "zuordnung/set", uid=UID2, ziel=SERIE)  # Administratoren dürfen jede gültige Kennung eintragen
    # bekannt: gemeldet (neue_tobies, UID), schon zugeordnet (UID2) oder Ergebnis eines Lernmodus (Verlauf)
    await ok(normal, "zuordnung/set", uid=UID, ziel=SERIE)
    await ok(normal, "zuordnung/set", uid=UID2, ziel=SERIE_ZWEI, ueberschreiben=True, erwartet_ziel=SERIE)
    assert await fehler(normal, "zuordnung/set", uid=UID3, ziel=SERIE) == "kennung_ungueltig"
    integration.store.lern_verlauf_hinzu({"befehl_id": "b-1", "box": "box1", "uid": UID3, "zustand": "abgelehnt"})
    await ok(normal, "zuordnung/set", uid=UID3, ziel=SERIE)
    assert await fehler(normal, "zuordnung/set", uid="zzzz", ziel=SERIE) == "kennung_ungueltig"


# --------------------------------------------------------------------------
# Schutz: eingang/sortieren, einstellungen/set
# --------------------------------------------------------------------------


async def test_sofort_nur_admin(admin, normal):
    assert await fehler(normal, "eingang/sortieren", sofort=True) == "unauthorized"
    await ok(normal, "eingang/sortieren", sofort=False)
    await ok(normal, "eingang/sortieren")
    await ok(admin, "eingang/sortieren", sofort=True)


async def test_lesezeichen_tage_nur_admin(admin, normal, integration):
    assert await fehler(normal, "einstellungen/set", lesezeichen_tage=3) == "unauthorized"
    assert integration.store.konfig["lesezeichen_tage"] == 14
    r = await ok(admin, "einstellungen/set", lesezeichen_tage=3)
    assert r["lesezeichen_tage"] == 3


async def test_zeitzone_wird_fuer_nicht_admins_ignoriert(admin, normal, integration):
    fenster = [{"id": "nacht", "tage": [1, 2, 3, 4, 5], "von": "20:00", "bis": "07:00", "wirkung": "stumm"}]
    r = await ok(normal, "einstellungen/set", leise_zeiten={"zeitzone": "Asia/Tokyo", "fenster": fenster})
    assert r["geaendert"] is True
    assert r["leise_zeiten"]["zeitzone"] == "Europe/Berlin" and len(r["leise_zeiten"]["fenster"]) == 1
    assert integration.store.konfig["leise_zeiten"]["zeitzone"] == "Europe/Berlin"
    # auch eine Zeitzone, die es nicht gibt, ist kein Fehler: sie wird ignoriert
    r = await ok(normal, "einstellungen/set", leise_zeiten={"zeitzone": "Nirgendwo/Nix", "fenster": fenster})
    assert r["geaendert"] is False and r["leise_zeiten"]["zeitzone"] == "Europe/Berlin"
    # fehlt die Zeitzone im Objekt, bleibt der gespeicherte Wert
    r = await ok(admin, "einstellungen/set", leise_zeiten={"zeitzone": "Europe/Vienna", "fenster": fenster})
    assert r["leise_zeiten"]["zeitzone"] == "Europe/Vienna"
    r = await ok(normal, "einstellungen/set", leise_zeiten={"fenster": []})
    assert r["leise_zeiten"] == {"zeitzone": "Europe/Vienna", "fenster": []}
    # ein Administrator darf sie setzen
    r = await ok(admin, "einstellungen/set", leise_zeiten={"zeitzone": "Asia/Tokyo", "fenster": []})
    assert r["leise_zeiten"]["zeitzone"] == "Asia/Tokyo"
    # sonstige Fehler bleiben Fehler
    assert await fehler(normal, "einstellungen/set", leise_zeiten="kaputt") == "einstellung_ungueltig"


async def test_einstellungen_erwartet_revision(admin, normal, integration):
    for client in (admin, normal):
        await _pruefe_erwartet_revision(client, integration)


async def _pruefe_erwartet_revision(client, integration):
    rev = integration.store.konfig["revision"]
    timer = 25 + rev  # bei jedem Durchlauf ein anderer Wert, damit es eine Änderung ist
    assert await fehler(client, "einstellungen/set", gute_nacht={"timer_min": timer, "ausblenden_s": 30}, erwartet_revision=rev + 5) == "stand_veraltet"
    assert integration.store.konfig["gute_nacht"]["timer_min"] != timer and integration.store.konfig["revision"] == rev
    r = await ok(client, "einstellungen/set", gute_nacht={"timer_min": timer, "ausblenden_s": 30}, erwartet_revision=rev)
    assert r["geaendert"] is True and r["konfig"]["revision"] == rev + 1
    # die zweite Seite kennt die neue Revision noch nicht
    assert await fehler(client, "einstellungen/set", gute_nacht={"timer_min": timer + 1, "ausblenden_s": 30}, erwartet_revision=rev) == "stand_veraltet"
    # erwartet_revision allein zählt nicht als Änderung
    assert await fehler(client, "einstellungen/set", erwartet_revision=rev + 1) == "invalid_format"
    assert await fehler(client, "einstellungen/set", gute_nacht={"timer_min": timer + 1, "ausblenden_s": 30}, erwartet_revision="1") == "invalid_format"


# --------------------------------------------------------------------------
# Schutz: Überraschungs-Serie als Ziel
# --------------------------------------------------------------------------


async def test_folge_verschieben_in_die_ueberraschung_nur_admin(admin, normal, nas, integration):
    nas.serie("ueb", "ueb", "Überraschung", [], typ="ueberraschung")
    await integration.medien.pruefen()
    assert await fehler(normal, "folge/verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id="ueb") == "ziel_ungueltig"
    assert (nas.medien / "rabe" / "a.mp3").exists() and integration.medien.serien["rabe"].serie.folgen == ["a.mp3", "b.mp3"]
    await ok(normal, "folge/verschieben", serie_id="rabe", folge="a.mp3", ziel_serie_id="zwei")  # normale Ziele gehen
    r = await ok(admin, "folge/verschieben", serie_id="rabe", folge="b.mp3", ziel_serie_id="ueb")
    assert r["folge"] == "b.mp3"


# --------------------------------------------------------------------------
# Schutz: Mengen
# --------------------------------------------------------------------------


async def test_aenderungen_je_minute(hass, admin, normal, normal2, freezer):
    assert const.AENDERUNGEN_JE_MINUTE == 30
    for _ in range(30):
        await ok(normal, "zuordnung/set", uid=UID, ziel=SERIE)
    assert await fehler(normal, "zuordnung/set", uid=UID, ziel=SERIE) == "zu_viele_aenderungen"
    # die Zähler gelten für alle Änderungen der Liste zusammen (set, remove, einstellungen/set)
    assert await fehler(normal, "zuordnung/remove", uid=UID, erwartet_ziel=SERIE) == "zu_viele_aenderungen"
    assert await fehler(normal, "einstellungen/set", gute_nacht={"timer_min": 20, "ausblenden_s": 30}) == "zu_viele_aenderungen"
    # je Benutzer: der zweite Benutzer und der Administrator sind frei
    await ok(normal2, "zuordnung/set", uid=UID, ziel=SERIE)
    for _ in range(31):
        await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE)
    # Lesen und andere Arten zählen nicht mit
    await ok(normal, "zuordnung/list")
    await ok(normal, "folge/delete", serie_id="rabe", folge="b.mp3")
    # nach einer Minute geht es wieder
    freezer.tick(timedelta(seconds=61))
    await ok(normal, "zuordnung/set", uid=UID, ziel=SERIE)


async def test_papierkorb_aktionen_je_10_minuten(hass, admin, normal, nas, lege_mp3, integration, freezer):
    assert const.PAPIERKORB_AKTIONEN_JE_10_MIN == 20
    pfad = nas.serie("viele", "viele", "Viele Folgen", [f"f{i:02d}.mp3" for i in range(22)])
    for i in range(22):
        lege_mp3(pfad / f"f{i:02d}.mp3")
    await integration.medien.pruefen()
    for i in range(20):
        await ok(normal, "folge/delete", serie_id="viele", folge=f"f{i:02d}.mp3")
    assert await fehler(normal, "folge/delete", serie_id="viele", folge="f20.mp3") == "zu_viele_aenderungen"
    assert await fehler(normal, "serie/delete", serie_id="zwei") == "zu_viele_aenderungen"
    assert (nas.medien / "viele" / "f20.mp3").exists()
    # Änderungen der Liste zählen getrennt
    await ok(normal, "zuordnung/set", uid=UID, ziel=SERIE)
    # Administratoren sind ausgenommen
    await ok(admin, "folge/delete", serie_id="viele", folge="f20.mp3")
    freezer.tick(timedelta(minutes=11))
    await ok(normal, "folge/delete", serie_id="viele", folge="f21.mp3")


@braucht_ffmpeg
async def test_upload_je_stunde(hass, integration, nas, hass_client, hass_read_only_user, hass_read_only_access_token, tmp_path):
    assert const.UPLOAD_BYTES_JE_STUNDE == 16 * GIB
    mp3 = erzeuge_audio(tmp_path / "q.mp3", frequenz=333, album="A", title="T")
    groesse = mp3.stat().st_size
    client = await hass_client(hass_read_only_access_token)
    # fast 16 GiB in der letzten Stunde verbraucht: für diese Datei bleibt zu wenig
    integration.schutz.mengen.buche("upload_bytes", hass_read_only_user.id, 16 * GIB - groesse + 1)
    antwort = await post(client, formular(mp3, "eins.mp3"))
    assert antwort.status == 429
    assert (await antwort.json())["fehler"]["code"] == "zu_viele_aenderungen"
    assert list(nas.eingang.rglob("*.mp3")) == []
    # Administratoren sind ausgenommen
    admin_client = await hass_client()
    assert (await post(admin_client, formular(mp3, "zwei.mp3"))).status == 200
    assert integration.schutz.mengen.summe("upload_bytes", hass_read_only_user.id) == 16 * GIB - groesse + 1  # abgelehnt: nicht gezählt
    # mit Platz für Datei und Formular-Rahmen (``Content-Length`` zählt den ganzen Körper) geht es; die angenommene Datei wird gezählt
    integration.schutz.mengen._gebucht.clear()
    integration.schutz.mengen.buche("upload_bytes", hass_read_only_user.id, 16 * GIB - groesse - 4096)
    antwort = await post(client, formular(mp3, "drei.mp3"))
    assert antwort.status == 200, await antwort.text()
    assert integration.schutz.mengen.summe("upload_bytes", hass_read_only_user.id) == 16 * GIB - 4096
    assert (await post(client, formular(mp3, "vier.mp3"))).status == 429
    integration.eingang.abbrechen()


def test_zaehlfenster_laufen_ab(freezer):
    from custom_components.tobibox.schutz import STUNDE_S, Mengen

    m = Mengen()
    m.buche("upload_bytes", "u1", 100)
    freezer.tick(timedelta(minutes=59))
    m.buche("upload_bytes", "u1", 50)
    assert m.summe("upload_bytes", "u1", STUNDE_S) == 150 and m.summe("upload_bytes", "u2", STUNDE_S) == 0
    freezer.tick(timedelta(minutes=2))  # die ersten 100 sind über eine Stunde alt
    assert m.summe("upload_bytes", "u1", STUNDE_S) == 50
    freezer.tick(timedelta(minutes=60))
    assert m.summe("upload_bytes", "u1", STUNDE_S) == 0


# --------------------------------------------------------------------------
# boxen/list und konfig/export_lesen: nur Administratoren sehen mehr
# --------------------------------------------------------------------------


async def test_boxen_list_ereignisse_nur_fuer_admins(admin, normal, bestand):
    await bestand.ereignis("fehler", {"baustein": "sync", "code": "x", "text": "kaputt"}, eid="aaaaaaaa-0000-4000-8000-000000000001")
    a = (await ok(admin, "boxen/list"))["boxen"][0]
    n = (await ok(normal, "boxen/list"))["boxen"][0]
    assert a["ereignisse"] and "ereignisse" not in n
    assert n.keys() == a.keys() - {"ereignisse"}


# --------------------------------------------------------------------------
# Papierkorb: geloescht_von, Protokoll, keine Mitteilung (AC3), Letzte Stunde
# --------------------------------------------------------------------------


async def test_papierkorb_merkt_wer_geloescht_hat(admin, normal, nas):
    e1 = (await ok(normal, "folge/delete", serie_id="rabe", folge="a.mp3"))["eintrag"]
    assert e1["geloescht_von"] == {"id": normal.nutzer.id, "name": "Normal"}
    e2 = (await ok(admin, "serie/delete", serie_id="zwei"))["eintrag"]
    assert e2["geloescht_von"]["id"] and e2["geloescht_von"]["name"]
    liste = (await ok(normal, "papierkorb/list"))["eintraege"]
    assert {e["id"]: e["geloescht_von"]["name"] for e in liste}[e1["id"]] == "Normal"
    meta = next(nas.papierkorb.glob(f"{e1['id']}/meta.json")).read_text(encoding="utf-8")
    assert normal.nutzer.id in meta  # steht auch in meta.json


async def test_eintraege_ohne_benutzer_haben_geloescht_von_null(admin, integration, nas):
    # eine Löschung ohne Benutzer (HA-Aktion, Eingangs-Lauf) und ein Eintrag von vor dem 12.11.
    e = await integration.medien.folge_loeschen("rabe", "a.mp3", False, None)
    assert e["eintrag"]["geloescht_von"] is None
    meta = nas.papierkorb / e["eintrag"]["id"] / "meta.json"
    import json

    daten = json.loads(meta.read_text(encoding="utf-8"))
    daten.pop("geloescht_von", None)
    meta.write_text(json.dumps(daten), encoding="utf-8")
    assert (await ok(admin, "papierkorb/list"))["eintraege"][0]["geloescht_von"] is None


async def test_protokollzeile_je_papierkorb_aktion(admin, normal, caplog):
    caplog.set_level(logging.INFO, logger="custom_components.tobibox")
    e = (await ok(normal, "folge/delete", serie_id="rabe", folge="a.mp3"))["eintrag"]
    zeilen = [r.getMessage() for r in caplog.records if "Papierkorb" in r.getMessage() and e["id"] in r.getMessage()]
    assert len(zeilen) == 1 and "Normal" in zeilen[0] and normal.nutzer.id in zeilen[0] and "a.mp3" in zeilen[0]
    e2 = (await ok(admin, "serie/delete", serie_id="zwei"))["eintrag"]
    assert any(e2["id"] in r.getMessage() for r in caplog.records)  # auch Administratoren stehen im Protokoll


async def test_keine_mitteilung_bei_vielen_loeschungen_in_einer_stunde(hass, normal, admin, nas, lege_mp3, integration, freezer):
    # AC3: früher entstand ab der vierten Löschung eine HA-Mitteilung für alle Benutzer; jetzt zeigt die Seite das Neue (papierkorb/list)
    pfad = nas.serie("viele", "viele", "Viele Folgen", [f"f{i}.mp3" for i in range(8)])
    for i in range(8):
        lege_mp3(pfad / f"f{i}.mp3")
    await integration.medien.pruefen()
    for i in range(6):
        await ok(normal, "folge/delete", serie_id="viele", folge=f"f{i}.mp3")
    assert notizen(hass, "tobibox_papierkorb") == {}
    liste = (await ok(admin, "papierkorb/list"))["eintraege"]  # die Seite liest hier „wer“ und „wann“
    assert len(liste) == 6 and all(e["geloescht_von"] == {"id": normal.nutzer.id, "name": "Normal"} and e["geloescht_am"] for e in liste)


async def test_keine_mitteilung_bei_einem_eintrag_mit_tobies(hass, admin, normal, integration):
    await ok(admin, "zuordnung/set", uid=UID, ziel=FOLGE, name="Rabe aus Holz")
    assert await fehler(normal, "folge/delete", serie_id="rabe", folge="a.mp3") == "tobies_betroffen"
    await ok(normal, "folge/delete", serie_id="rabe", folge="a.mp3", tobies_bestaetigt=True)
    # auch eine ganze Serie mit Tobies
    await ok(admin, "zuordnung/set", uid=UID2, ziel=SERIE_ZWEI)
    await ok(normal, "serie/delete", serie_id="zwei", tobies_bestaetigt=True)
    assert notizen(hass, "tobibox_papierkorb") == {}  # AC3: keine HA-Mitteilung, sie wäre für alle Benutzer sichtbar


async def test_keine_mitteilung_fuer_administratoren(hass, admin, nas, lege_mp3, integration):
    pfad = nas.serie("viele", "viele", "Viele Folgen", [f"f{i}.mp3" for i in range(5)])
    for i in range(5):
        lege_mp3(pfad / f"f{i}.mp3")
    await integration.medien.pruefen()
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE_ZWEI)
    await ok(admin, "serie/delete", serie_id="zwei", tobies_bestaetigt=True)
    for i in range(5):
        await ok(admin, "folge/delete", serie_id="viele", folge=f"f{i}.mp3")
    assert notizen(hass, "tobibox_papierkorb") == {}


def _mache_eintrag_alt(nas, eintrag_id: str, stunden: float) -> None:
    import json

    from custom_components.tobibox.util import iso, jetzt

    meta = nas.papierkorb / eintrag_id / "meta.json"
    daten = json.loads(meta.read_text(encoding="utf-8"))
    daten["geloescht_am"] = iso(jetzt() - timedelta(hours=stunden))
    meta.write_text(json.dumps(daten), encoding="utf-8")


async def test_letzte_stunde_holt_genau_diese_eintraege_zurueck(hass, admin, normal, nas, lege_mp3, integration):
    pfad = nas.serie("viele", "viele", "Viele Folgen", [f"f{i}.mp3" for i in range(5)])
    for i in range(5):
        lege_mp3(pfad / f"f{i}.mp3")
    await integration.medien.pruefen()
    alt = (await ok(normal, "folge/delete", serie_id="viele", folge="f0.mp3"))["eintrag"]
    grenzfall = (await ok(normal, "folge/delete", serie_id="viele", folge="f3.mp3"))["eintrag"]
    _mache_eintrag_alt(nas, alt["id"], 2)  # vor zwei Stunden
    _mache_eintrag_alt(nas, grenzfall["id"], 1.1)  # gerade über eine Stunde
    neu1 = (await ok(normal, "folge/delete", serie_id="viele", folge="f1.mp3"))["eintrag"]
    neu2 = (await ok(normal, "folge/delete", serie_id="viele", folge="f2.mp3"))["eintrag"]
    neu3 = (await ok(admin, "serie/delete", serie_id="zwei"))["eintrag"]
    assert await fehler(normal, "papierkorb/restore_letzte_stunde", bestaetigt=True) == "unauthorized"
    assert await fehler(admin, "papierkorb/restore_letzte_stunde") == "invalid_format"
    assert await fehler(admin, "papierkorb/restore_letzte_stunde", bestaetigt=False) == "invalid_format"
    r = await ok(admin, "papierkorb/restore_letzte_stunde", bestaetigt=True)
    assert r == {"wiederhergestellt": 3, "uebersprungen": []}
    rest = (await ok(admin, "papierkorb/list"))["eintraege"]
    assert {e["id"] for e in rest} == {alt["id"], grenzfall["id"]}  # nur die älteren bleiben im Papierkorb
    assert (nas.medien / "viele" / "f1.mp3").exists() and (nas.medien / "viele" / "f2.mp3").exists()
    assert not (nas.medien / "viele" / "f0.mp3").exists() and not (nas.medien / "viele" / "f3.mp3").exists()
    assert "zwei" in integration.medien.serien
    assert {neu1["id"], neu2["id"], neu3["id"]}.isdisjoint({e["id"] for e in rest})
    # der Endzustand bleibt gleich
    assert (await ok(admin, "papierkorb/restore_letzte_stunde", bestaetigt=True)) == {"wiederhergestellt": 0, "uebersprungen": []}


async def test_letzte_stunde_nennt_uebersprungenes_und_holt_den_rest(admin, normal, nas, lege_mp3, integration):
    e1 = (await ok(normal, "folge/delete", serie_id="rabe", folge="a.mp3"))["eintrag"]
    e2 = (await ok(normal, "folge/delete", serie_id="rabe", folge="b.mp3"))["eintrag"]
    lege_mp3(nas.medien / "rabe" / "a.mp3")  # inzwischen liegt wieder eine Datei mit diesem Namen da
    await integration.medien.pruefen()
    r = await ok(admin, "papierkorb/restore_letzte_stunde", bestaetigt=True)
    assert r == {"wiederhergestellt": 1, "uebersprungen": [{"eintrag_id": e1["id"], "code": "datei_existiert"}]}
    assert (nas.medien / "rabe" / "b.mp3").exists()
    assert [e["id"] for e in (await ok(admin, "papierkorb/list"))["eintraege"]] == [e1["id"]]
    assert e2["id"] not in [e["id"] for e in (await ok(admin, "papierkorb/list"))["eintraege"]]


# --------------------------------------------------------------------------
# 10 frühere Stände der Liste
# --------------------------------------------------------------------------


async def _aendere_und_warte(hass, integration, admin, wert: int) -> None:
    await ok(admin, "einstellungen/set", gute_nacht={"timer_min": wert, "ausblenden_s": 30})
    await warte_auf(hass, lambda: integration.export_ok)


async def test_fruehere_staende_der_liste(hass, admin, normal, nas, integration):
    assert const.KONFIG_STAENDE_ANZAHL == 10
    await warte_auf(hass, lambda: integration.export_ok)
    assert (await ok(admin, "konfig/export_lesen"))["staende"] == []
    for wert in range(10, 26):  # 16 Änderungen: Revision 2 bis 17
        await _aendere_und_warte(hass, integration, admin, wert)
    assert integration.store.konfig["revision"] == 17
    dateien = sorted(p.name for p in nas.export.glob("config*.json"))
    assert dateien == sorted(["config.json"] + [f"config.{n}.json" for n in range(1, 11)])  # genau 10 frühere Stände
    r = await ok(admin, "konfig/export_lesen")
    assert r["revision"] == 17 and r["konfig"]["revision"] == 17
    assert [s["stand"] for s in r["staende"]] == list(range(1, 11))
    assert all(s.keys() == {"stand", "exportiert_am", "anzahl_zuordnungen"} for s in r["staende"])
    # Stand 1 ist der jüngste frühere (Revision 16), Stand 10 der älteste (Revision 7)
    assert (await ok(admin, "konfig/export_lesen", stand=1))["revision"] == 16
    assert (await ok(admin, "konfig/export_lesen", stand=10))["revision"] == 7
    assert (await ok(admin, "konfig/export_lesen", stand=1))["neuer_als_ha"] is False
    # derselbe Stand wird nicht mehrfach abgelegt (ein erneuter Export ohne neue Revision schiebt nichts)
    integration.export_planen()
    await warte_auf(hass, lambda: integration.export_ok)
    assert (await ok(admin, "konfig/export_lesen", stand=1))["revision"] == 16
    # Eingaben
    assert await fehler(admin, "konfig/export_lesen", stand=0) == "invalid_format"
    assert await fehler(admin, "konfig/export_lesen", stand=11) == "invalid_format"
    assert await fehler(admin, "konfig/export_lesen", stand="1") == "invalid_format"
    assert await fehler(admin, "konfig/export_lesen", stand=True) == "invalid_format"
    # nur Administratoren
    assert await fehler(normal, "konfig/export_lesen") == "unauthorized"
    assert await fehler(normal, "konfig/export_lesen", stand=1) == "unauthorized"
    assert await fehler(normal, "konfig/aus_export", bestaetigt=True, stand=1) == "unauthorized"


async def test_aus_stand_wiederherstellen(hass, admin, nas, integration, box_fabrik):
    await warte_auf(hass, lambda: integration.export_ok)
    await ok(admin, "zuordnung/set", uid=UID, ziel=SERIE, name="Rabe aus Holz")
    await warte_auf(hass, lambda: integration.export_ok)
    await ok(admin, "zuordnung/remove", uid=UID)
    await warte_auf(hass, lambda: integration.export_ok)
    assert UID not in integration.store.konfig["zuordnungen"]
    alt = integration.store.konfig["liste_id"]
    r = await ok(admin, "konfig/aus_export", bestaetigt=True, stand=1)  # der Stand vor dem Entfernen
    assert r["uebernommen"]["zuordnungen"] == 1 and r["konfig"]["liste_id"] != alt and r["konfig"]["revision"] == 1
    assert integration.store.konfig["zuordnungen"][UID]["name"] == "Rabe aus Holz"
    assert await fehler(admin, "konfig/aus_export", bestaetigt=True, stand=9) == "export_nicht_gefunden"
    assert await fehler(admin, "konfig/export_lesen", stand=9) == "export_nicht_gefunden"
    # ohne ``stand`` gilt der aktuelle Export wie bisher; das Wiederherstellen plant den Export im Hintergrund,
    # also erst warten, bis ``config.json`` den wiederhergestellten Stand enthält (sonst liest der Test den alten)
    await warte_auf(hass, lambda: integration.export_ok)
    assert (await ok(admin, "konfig/aus_export", bestaetigt=True))["uebernommen"]["zuordnungen"] == 1


# --------------------------------------------------------------------------
# ``stand`` einer Serie: nur Name, Folgenliste und menschliche Felder
# --------------------------------------------------------------------------


def _serie(**extra) -> Serie:
    return Serie(id="x", name="Name", typ="normal", angelegt_am="2026-11-01T10:00:00Z", folgen=["a.mp3", "b.mp3"], **extra)


def test_stand_ignoriert_werte_aus_hintergrundlaeufen():
    leer = _serie().stand
    s = _serie(folgen_info={"a.mp3": {"dauer_s": 61.5, "spuren_s": [30, 31.5], "kapitel": [{"t": 0}], "art": "hoerbuch"}})
    assert s.stand == leer
    s.folgen_info["a.mp3"].update({"extra_feld": 1})
    assert s.stand == leer
    # der Rest von folgen_info (Platzhalter für einen leeren Eintrag) zählt nicht
    assert _serie(folgen_info={"b.mp3": {}}).stand == leer


@pytest.mark.parametrize(
    "info",
    [{"anzeige": "Eins"}, {"nummer": 3}, {"datum": "2020-01-01"}, {"pruefen": True, "pruefen_gruende": ["x"]}],
    ids=["anzeige", "nummer", "datum", "pruefen"],
)
def test_stand_aendert_sich_bei_menschlichen_feldern(info):
    assert _serie(folgen_info={"a.mp3": info}).stand != _serie().stand
    mit_dauer = _serie(folgen_info={"a.mp3": {**info, "dauer_s": 5}})
    assert mit_dauer.stand == _serie(folgen_info={"a.mp3": info}).stand  # die Dauer macht keinen Unterschied


def test_stand_aendert_sich_bei_name_und_folgenliste():
    s = _serie()
    assert Serie(id="x", name="Anders", typ="normal", angelegt_am="x", folgen=["a.mp3", "b.mp3"]).stand != s.stand
    assert Serie(id="x", name="Name", typ="normal", angelegt_am="x", folgen=["b.mp3", "a.mp3"]).stand != s.stand
    assert Serie(id="x", name="Name", typ="normal", angelegt_am="x", folgen=["a.mp3"]).stand != s.stand


# --------------------------------------------------------------------------
# Upload ohne Administratorrecht
# --------------------------------------------------------------------------


@braucht_ffmpeg
async def test_upload_ohne_anmeldung_bleibt_401(hass, integration, hass_client_no_auth, tmp_path):
    client = await hass_client_no_auth()
    mp3 = erzeuge_audio(tmp_path / "q.mp3", frequenz=333)
    antwort = await post(client, formular(mp3))
    assert antwort.status == 401
