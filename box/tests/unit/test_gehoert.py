"""Beobachter „Gehört“ (B1): Sitzungsgrenzen, Hörzeit, Puffer ``gehoert.json``, Uhr (``docs/designs/gehoert.md`` 2, 3.2 bis 3.4)."""

from __future__ import annotations

import copy
import json
import shutil
from dataclasses import replace

from fixtures.gehoert_harnisch import ANDERE, ANFANG_WALL, FOLGE, SERIE, Box, uuid_nr

from tobibox import events as ev
from tobibox import gehoert as g
from tobibox import gehoert_puffer
from tobibox.clock import SimUhr


def gueltig(zeilen: list[dict]) -> None:
    """Jede Zeile erfüllt den Vertrag (``mqtt-v1.md`` 3.4)."""
    for z in zeilen:
        assert g.pruefe_zeile(z) == z, z


def eine_folge(h: Box, sekunden: int = 20, folge: str = FOLGE) -> None:
    h.abspielen(folge)
    h.spiele(sekunden)
    h.folge_zu_ende()


# --- Hörzeit (2) ------------------------------------------------------------------------------------


def test_hoerzeit_aus_dem_fortschritt_der_position(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(60)
    h.pause("knopf")
    h.vergehen(30 * 60)
    (z,) = h.zeilen()
    # die erste Meldung setzt nur die Basislinie: 60 Meldungen, 59 Sekunden Zuwachs
    assert z["gehoert_s"] == 59
    assert (z["serie"], z["folge"], z["folge_dauer_s"]) == (SERIE, FOLGE, 1520)
    assert z["ende"] == "pause" and z["grund"] == "knopf"
    assert z["boot_id"] == "boot-1" and z["zeit_ok"] is True
    assert z["ende_boot_s"] - z["beginn_boot_s"] == 59
    assert "uid" not in z and not any("uid" in str(k) for k in z)  # nie die Kennung des Tobies
    gueltig([z])


def test_springen_nach_vorn_zaehlt_nur_bis_zur_kappung(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(10)  # 9 Sekunden
    h.uhr.vor(1.0)
    h.pos += 500  # MPD springt über 500 s im selben Track
    h.position()
    h.folge_zu_ende()
    (z,) = h.zeilen()
    # 9 + 4 (2 × dt + 2 mit dt = 1) wären 13; die Schranke des Vertrags (ende_boot_s − beginn_boot_s + 2) kappt auf 12
    assert z["gehoert_s"] == 12 == z["ende_boot_s"] - z["beginn_boot_s"] + 2


def test_springen_zurueck_setzt_nur_die_basislinie_neu(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(10)
    h.uhr.vor(1.0)
    h.pos = 3.0  # Rücksprung innerhalb des Tracks (dp ≤ 0)
    h.position()
    h.spiele(10)  # 9 Sekunden: die erste Meldung nach dem Sprung ist die neue Basislinie, eine zählt schon
    h.folge_zu_ende()
    (z,) = h.zeilen()
    assert z["gehoert_s"] == 9 + 10


def test_schneller_abspielen_wird_von_der_schranke_des_vertrags_gekappt(tmp_path):
    # B1-OFFEN: Entwurf 2 sagt „bei schnellerem Abspielen zählt die Länge des Inhalts“, der Vertrag (mqtt-v1 3.4) schränkt
    # ``gehoert_s`` aber auf ``ende_boot_s − beginn_boot_s + 2`` ein. Die Box meldet nie mehr als die Schranke (sonst wäre die Zeile für HA gekappt).
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(10, tempo=2.0)
    h.folge_zu_ende()
    (z,) = h.zeilen()
    assert z["gehoert_s"] == z["ende_boot_s"] - z["beginn_boot_s"] + 2 == 11  # ungekappt wären es 18
    gueltig([z])


def test_hoerzeit_ueberschreitet_nie_die_schranke_des_vertrags(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(5, tempo=4.0)  # Kappung 4 s je Sekunde: 4 × 4 = 16 > 4 + 2
    h.folge_zu_ende()
    (z,) = h.zeilen()
    assert z["gehoert_s"] == z["ende_boot_s"] - z["beginn_boot_s"] + 2
    gueltig([z])


def test_sitzung_ohne_hoerzeit_wird_verworfen(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(1)  # nur die Basislinie
    h.pause()
    h.vergehen(30 * 60)
    assert h.zeilen() == [] and h.p.z.offen is None
    assert not h.datei.exists() or h.inhalt()["zeilen"] == []


def test_nachzuegler_mit_altem_gen_werden_ignoriert(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.position(gen=0)  # Nachzügler der Wiedergabe davor
    assert h.p.z.offen is None
    h.spiele(5)
    h.position(gen=0)
    h.pos += 100
    h.position(gen=0)
    h.folge_zu_ende()
    (z,) = h.zeilen()
    assert z["gehoert_s"] == 4


def test_nach_dem_pausieren_beginnt_ohne_abspielen_keine_sitzung(tmp_path):
    h = Box(tmp_path)
    eine_folge(h)
    h.position()  # eine späte Meldung mit ``spielt = true``
    assert h.p.z.offen is None and len(h.zeilen()) == 1


# --- Sitzungsgrenzen (3.2) --------------------------------------------------------------------------


def test_ende_der_folge(tmp_path):
    h = Box(tmp_path)
    eine_folge(h, 20)
    (z,) = h.zeilen()
    assert z["ende"] == "ende_der_folge" and "grund" not in z and z["gehoert_s"] == 19
    assert h.inhalt()["zeilen"] == h.zeilen() and h.inhalt()["offen"] is None  # je Sitzungsende ein Schreibvorgang
    # Wiederholen nach dem Ende ist eine neue Sitzung
    h.abspielen()
    h.spiele(10)
    h.folge_zu_ende()
    a, b = h.zeilen()
    assert a["sitzung"] != b["sitzung"] and b["gehoert_s"] == 9


def test_veraltetes_folgenende_beendet_nichts(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(10)
    h.ein(ev.FolgeZuEnde(SERIE, FOLGE, h.gen - 1))  # Nachzügler
    h.ein(ev.FolgeZuEnde(SERIE, "andere.mp3", h.gen))  # nicht die laufende Folge
    assert h.zeilen() == [] and h.p.z.offen is not None


def test_wechsel_erst_mit_der_ersten_gespielten_sekunde_der_anderen_folge(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(20)
    h.abspielen(ANDERE)  # neuer Tobie: noch keine gespielte Sekunde
    assert h.zeilen() == []
    h.spiele(1)
    (z,) = h.zeilen()
    assert z["folge"] == FOLGE and z["ende"] == "wechsel" and z["gehoert_s"] == 19
    assert h.p.z.offen is not None and h.p.z.offen.folge == ANDERE
    h.spiele(10)
    h.folge_zu_ende()
    assert [r["folge"] for r in h.zeilen()] == [FOLGE, ANDERE]
    assert "folge_dauer_s" not in h.zeilen()[1]  # Dauer unbekannt: das Feld fehlt
    gueltig(h.zeilen())


def test_anderer_tobie_mit_derselben_folge_ist_dieselbe_sitzung(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(10)
    h.pause()
    h.abspielen(position_s=h.pos)  # ein anderer Tobie zeigt auf dieselbe Folge: Kennungen kennt der Beobachter nicht
    h.spiele(10)
    h.folge_zu_ende()
    (z,) = h.zeilen()
    assert z["gehoert_s"] == 9 + 9


def test_pause_bis_30_minuten_gehoert_dazu_danach_endet_die_sitzung(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(30)
    h.pause("stumm")
    h.vergehen(30 * 60 - 1)
    assert h.zeilen() == []
    h.abspielen(position_s=h.pos)  # nach 29:59 weiterhören: dieselbe Sitzung
    h.spiele(30)
    h.pause("abgehoben")
    h.vergehen(30 * 60 - 1)
    assert h.zeilen() == []
    h.vergehen(1)
    (z,) = h.zeilen()
    assert z["ende"] == "pause" and z["grund"] == "abgehoben" and z["gehoert_s"] == 29 + 29
    assert z["ende_boot_s"] == h.uhr.mono - 30 * 60  # die letzte gespielte Sekunde, nicht der Zeitpunkt der Prüfung


def test_nach_30_minuten_beginnt_dieselbe_folge_neu(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(20)
    h.pause("knopf")
    h.vergehen(30 * 60)
    h.abspielen(position_s=h.pos)
    h.spiele(20)
    h.folge_zu_ende()
    assert [r["ende"] for r in h.zeilen()] == ["pause", "ende_der_folge"]


def test_jeder_pausegrund_zaehlt(tmp_path):
    for grund in ("fehler", "leser_unbekannt", "gute_nacht", "abgehoben"):
        verz = tmp_path / grund
        h = Box(verz)
        h.abspielen()
        h.spiele(10)
        h.ein(ev.Takt(), ev.Pausieren(grund))  # type: ignore[arg-type]
        h.vergehen(30 * 60)
        assert h.zeilen()[0]["grund"] == grund


def test_trackwechsel_beendet_die_sitzung_nicht(tmp_path):
    h = Box(tmp_path)
    h.abspielen(track=0)
    h.spiele(20)
    h.track, h.pos = 1, 0.0  # MPD spielt mit dem nächsten Track weiter
    h.spiele(20)
    h.folge_zu_ende()
    (z,) = h.zeilen()
    assert z["gehoert_s"] == 19 + 19


def test_herunterfahren_schreibt_synchron_und_beendet(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(50)
    n = h.p.schreibungen
    h.ein(ev.Takt(), ev.Pausieren("herunterfahren"), ev.Herunterfahren("hauptknopf"))
    (z,) = h.zeilen()
    assert z["ende"] == "herunterfahren" and z["gehoert_s"] == 49
    assert h.inhalt()["zeilen"] == h.zeilen() and h.inhalt()["offen"] is None
    assert h.p.schreibungen == n + 1  # ein Vorgang (der Pausebeginn schreibt bei ``herunterfahren`` nicht noch einmal)


def test_dienst_ende_schreibt_synchron_auch_ohne_wiedergabe(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(50)
    h.pause()
    h.p.dienst_ende(h.uhr.jetzt())  # ``app.beende``, auch wenn der Kern nur pausiert ist
    (z,) = h.zeilen()
    assert z["ende"] == "dienst_ende" and z["gehoert_s"] == 49
    assert h.inhalt()["zeilen"] == h.zeilen()
    h.p.dienst_ende(h.uhr.jetzt())  # noch einmal: nichts doppelt
    assert len(h.zeilen()) == 1


def test_dienst_ende_ereignis_des_kerns(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(30)
    h.ein(ev.DienstEndet(), ev.Pausieren("herunterfahren"))
    h.position(spielt=True)  # eine späte Meldung vor dem Pausieren darf keine neue Sitzung beginnen
    (z,) = h.zeilen()
    assert z["ende"] == "dienst_ende" and h.p.z.offen is None


# --- Puffer ``gehoert.json`` (3.4) --------------------------------------------------------------------


def test_absturz_offene_sitzung_wird_beim_start_zur_zeile_abbruch(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(130)  # nach 2 Minuten steht der Stand der offenen Sitzung in der Datei
    roh = h.inhalt()
    assert roh["offen"] is not None and roh["offen"]["ende"] == "teilweise" and roh["zeilen"] == []
    gueltig([{**roh["offen"], "ende": "pause"}])  # sonst wie eine Zeile
    h.spiele(40)  # Absturz: diese 40 Sekunden gehen verloren
    h2 = h.neu_starten()  # der Dienst startet (oder das Gerät nach Stromausfall)
    (z,) = h2.zeilen()
    assert z["ende"] == "abbruch" and "grund" not in z and z["sitzung"] == roh["offen"]["sitzung"]
    assert 115 <= z["gehoert_s"] <= 125
    assert h2.inhalt()["offen"] is None and h2.inhalt()["zeilen"] == h2.zeilen()
    h3 = h2.neu_starten()  # noch ein Start: keine zweite Zeile
    assert [r["sitzung"] for r in h3.zeilen()] == [z["sitzung"]]


def test_offene_sitzung_wird_hoechstens_alle_2_minuten_und_beim_pausebeginn_geschrieben(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    n = h.p.schreibungen
    h.spiele(3600)
    assert h.p.schreibungen - n <= 30  # höchstens 30 je Stunde Wiedergabe (data-model 1.7)
    assert h.p.schreibungen - n >= 28
    h.spiele(10)
    n = h.p.schreibungen
    h.ein(ev.Takt(), ev.Pausieren("knopf"))  # Pausebeginn: Stand schreiben
    assert h.p.schreibungen == n + 1
    h.ein(ev.Takt(), ev.Pausieren("knopf"))  # nichts Neues zu schreiben
    h.vergehen(600)
    assert h.p.schreibungen == n + 1


def test_strom_weg_nach_herunterfahren_die_zeile_steht_auf_der_platte(tmp_path):
    async def lauf() -> None:
        h = Box(tmp_path, asynchron=True)
        h.abspielen()
        h.spiele(130)  # die Hintergrundaufgabe für die offene Sitzung ist geplant, aber noch nicht gelaufen
        h.ein(ev.Takt(), ev.Pausieren("herunterfahren"), ev.Herunterfahren("hauptknopf"))
        stand = json.loads((tmp_path / "gehoert.json").read_text())
        assert [r["ende"] for r in stand["zeilen"]] == ["herunterfahren"] and stand["offen"] is None
        await h.p.warte_gespeichert()
        assert json.loads((tmp_path / "gehoert.json").read_text()) == stand

    import asyncio

    asyncio.run(lauf())


def test_aelterer_stand_ueberschreibt_den_synchron_geschriebenen_nicht_im_wettlauf(tmp_path, monkeypatch):
    """Der Hintergrund-Thread schreibt gerade (langsam) den Stand mit offener Sitzung, da kommt ``Herunterfahren``."""
    import asyncio
    import threading

    echt = gehoert_puffer.schreibe_atomar
    laeuft, frei = threading.Event(), threading.Event()
    aufrufe: list[list[str]] = []

    def langsam(pfad, inhalt):
        aufrufe.append([r["ende"] for r in inhalt["zeilen"]] + (["offen"] if inhalt["offen"] else []))
        if len(aufrufe) == 1:  # der Hintergrund-Thread hängt an der SD-Karte
            laeuft.set()
            frei.wait(5)
        echt(pfad, inhalt)

    monkeypatch.setattr(gehoert_puffer, "schreibe_atomar", langsam)

    async def lauf() -> None:
        h = Box(tmp_path, asynchron=True)
        h.abspielen()
        h.spiele(130)
        await asyncio.to_thread(laeuft.wait, 5)  # der Thread schreibt jetzt den Stand mit der offenen Sitzung und hält die Sperre
        threading.Timer(0.2, frei.set).start()
        h.ein(ev.Takt(), ev.Pausieren("herunterfahren"), ev.Herunterfahren("hauptknopf"))  # wartet auf die Sperre, schreibt dann
        await h.p.warte_gespeichert()
        stand = json.loads((tmp_path / "gehoert.json").read_text())
        assert [r["ende"] for r in stand["zeilen"]] == ["herunterfahren"] and stand["offen"] is None
        assert aufrufe[0] == ["offen"] and aufrufe[1] == ["herunterfahren"]
        # und ein älterer Stand, der erst jetzt an die Reihe käme, wird übersprungen
        h.p._schreibe_datei(1, {"schema_version": 1, "verworfen": 0, "offen": None, "zeilen": []})
        assert json.loads((tmp_path / "gehoert.json").read_text()) == stand

    asyncio.run(lauf())


def test_scheitert_das_schreiben_wird_es_nachgeholt_hoechstens_alle_60_s(tmp_path, monkeypatch):
    echt = gehoert_puffer.schreibe_atomar
    versuche = []
    kaputt = {"an": True}

    def karte(pfad, inhalt):
        versuche.append(1)
        if kaputt["an"]:
            raise OSError("Karte voll")
        echt(pfad, inhalt)

    monkeypatch.setattr(gehoert_puffer, "schreibe_atomar", karte)
    h = Box(tmp_path)
    eine_folge(h)  # das Schreiben der beendeten Sitzung scheitert
    assert len(h.zeilen()) == 1 and not h.datei.exists() and len(versuche) == 1
    for _ in range(59):
        h.vergehen(1)
    assert len(versuche) == 1  # nicht jede Sekunde
    h.vergehen(1)
    assert len(versuche) == 2 and not h.datei.exists()  # zweiter Versuch scheitert, wieder 60 s Pause
    for _ in range(30):
        h.vergehen(1)
    assert len(versuche) == 2
    kaputt["an"] = False
    h.vergehen(30)
    assert len(versuche) == 3 and h.inhalt()["zeilen"] == h.zeilen()
    h.vergehen(600)
    assert len(versuche) == 3  # erledigt: kein weiteres Schreiben


def test_leere_serie_oder_folge_ergibt_keine_sitzung(tmp_path):
    h = Box(tmp_path)
    for serie, folge in (("", FOLGE), (SERIE, "")):
        h.gen += 1
        h.ein(ev.Takt(), ev.Abspielen(serie or "x", "o", folge or "x", (folge or "x",), 0, 0.0, None, h.gen))
        h.uhr.vor(1.0)
        h.ein(ev.PlayerPosition(serie, folge, 0, 1.0, True, h.gen))
        h.uhr.vor(1.0)
        h.ein(ev.PlayerPosition(serie, folge, 0, 2.0, True, h.gen))
    assert h.p.z.offen is None and h.zeilen() == []


def test_abgeschnittene_datei_faellt_auf_die_sicherung_zurueck(tmp_path):
    h = Box(tmp_path)
    eine_folge(h)
    erste = h.zeilen()
    eine_folge(h)
    datei = h.datei
    text = datei.read_bytes()
    datei.write_bytes(text[: len(text) // 2])  # Strom weg mitten im Schreiben (ohne atomares Ersetzen)
    h2 = h.neu_starten()
    assert h2.p.quelle == "bak" and h2.zeilen() == erste  # der Stand davor
    shutil.rmtree(tmp_path)
    tmp_path.mkdir()
    h3 = Box(tmp_path)
    eine_folge(h3)
    h3.datei.write_bytes(h3.datei.read_bytes()[:20])  # nur eine Datei, kein Rückfall
    h4 = h3.neu_starten()
    assert h4.zeilen() == [] and h4.p.quelle == "standard"  # leer, aber die Box läuft


def test_ungueltige_zeile_wird_verworfen_nicht_die_ganze_datei(tmp_path):
    h = Box(tmp_path)
    for _ in range(3):
        eine_folge(h)
    roh = h.inhalt()
    del roh["zeilen"][1]["serie"]  # Pflichtfeld fehlt
    roh["zeilen"][2]["gehoert_s"] = "viel"  # falscher Typ
    h.datei.write_text(json.dumps(roh))
    h2 = h.neu_starten()
    assert [r["sitzung"] for r in h2.zeilen()] == [roh["zeilen"][0]["sitzung"]]
    assert h2.p.verworfen == 2  # zählt in ``verworfen`` mit
    assert h2.inhalt()["verworfen"] == 2


def test_ungueltiger_rahmen_gilt_wie_eine_defekte_datei(tmp_path):
    h = Box(tmp_path)
    eine_folge(h)
    eine_folge(h)
    roh = h.inhalt()
    roh["zeilen"] = "keine Liste"
    h.datei.write_text(json.dumps(roh))
    h2 = h.neu_starten()
    assert h2.p.quelle == "bak" and len(h2.zeilen()) == 1


def test_ungueltige_zeilen_pruefung():
    gut = {
        "sitzung": uuid_nr(1), "serie": SERIE, "folge": FOLGE, "beginn": "2026-11-16T18:10:57Z", "zeit_ok": True,
        "boot_id": "b", "beginn_boot_s": 100, "ende_boot_s": 200, "gehoert_s": 102, "ende": "pause",
    }
    assert g.pruefe_zeile(gut) == gut
    for fehler in (
        {"gehoert_s": 103},  # über der Schranke ende − beginn + 2
        {"gehoert_s": 0},
        {"gehoert_s": True},
        {"ende": "teilweise"},  # in ``zeilen`` nie
        {"ende": "irgendwas"},
        {"sitzung": "keine-uuid"},
        {"ende_boot_s": 99},
        {"beginn": "gestern"},
        {"zeit_ok": 1},
        {"folge": "ä" * 200},  # mehr als 255 Bytes
        {"folge_dauer_s": 0},
        {"grund": "x" * 33},
        {"serie": ""},
    ):
        assert g.pruefe_zeile({**gut, **fehler}) is None, fehler
    assert g.pruefe_zeile({**gut, "folge_dauer_s": None, "fremd": 1}) == gut  # fremde Felder fallen weg
    assert g.pruefe_zeile({**gut, "ende": "teilweise"}, offen=True) is not None


def test_ueberlauf_die_aeltesten_fallen_weg_und_verworfen_zaehlt(tmp_path, monkeypatch):
    monkeypatch.setattr(gehoert_puffer, "schreibe_atomar", lambda *a, **k: None)  # 500 Datei-Schreibvorgänge brauchen wir nicht
    h = Box(tmp_path)
    for _ in range(502):
        eine_folge(h, 3)
    zeilen = h.zeilen()
    assert len(zeilen) == 500 and h.p.verworfen == 2
    assert zeilen[0]["sitzung"] == uuid_nr(3) and zeilen[-1]["sitzung"] == uuid_nr(502)  # die ältesten zwei sind weg
    assert g.zu_json(h.p.z)["verworfen"] == 2


def test_verworfenes_bleibt_ueber_den_neustart_erhalten(tmp_path):
    h = Box(tmp_path)
    eine_folge(h)
    h.p.z = replace(h.p.z, verworfen=7)
    eine_folge(h)
    assert h.neu_starten().p.verworfen == 7


def test_zeitlich_gesammelte_quittung_wird_mit_dem_naechsten_schreiben_oder_nach_10_minuten_geschrieben(tmp_path):
    h = Box(tmp_path)
    for _ in range(3):
        eine_folge(h)
    ids = [r["sitzung"] for r in h.zeilen()]
    n = h.p.schreibungen
    assert h.p.quittiere([ids[0], uuid_nr(999)], h.uhr.jetzt()) == 1  # unbekannte UUIDs ignoriert
    assert [r["sitzung"] for r in h.zeilen()] == ids[1:]
    assert h.p.schreibungen == n  # noch nicht geschrieben
    h.p.quittiere([ids[0]], h.uhr.jetzt())  # doppelte Quittung: idempotent
    h.vergehen(599)
    assert h.p.schreibungen == n
    h.vergehen(1)
    assert h.p.schreibungen == n + 1 and [r["sitzung"] for r in h.inhalt()["zeilen"]] == ids[1:]
    h.vergehen(3000)
    assert h.p.schreibungen == n + 1  # nur einmal
    # oder mit dem nächsten Schreibvorgang
    h.p.quittiere([ids[1]], h.uhr.jetzt())
    eine_folge(h)
    assert [r["sitzung"] for r in h.inhalt()["zeilen"]][0] == ids[2] and len(h.inhalt()["zeilen"]) == 2


def test_geklonte_datei_beide_boxen_laden_dieselbe_datei(tmp_path):
    a_verz, b_verz = tmp_path / "a", tmp_path / "b"
    orig = Box(a_verz)
    for _ in range(3):
        eine_folge(orig)
    bekannt = [r["sitzung"] for r in orig.zeilen()]  # HA kennt diese schon (z. B. von der Original-Box, die sie nie quittiert bekam)
    shutil.copytree(a_verz, b_verz)  # die SD-Karte wurde geklont
    a = Box(a_verz, uhr=orig.uhr, nummer=100)
    b = Box(b_verz, uhr=orig.uhr, nummer=200)
    assert a.zeilen() == b.zeilen() and len(b.zeilen()) == 3
    eine_folge(b)  # nur B erlebt etwas Eigenes: andere UUID
    eigene = b.zeilen()[-1]["sitzung"]
    assert eigene not in bekannt and eigene not in {r["sitzung"] for r in a.zeilen()}
    # HA quittiert B die eigene neue UUID: nichts anderes verschwindet
    assert b.p.quittiere([eigene], b.uhr.jetzt()) == 1
    assert [r["sitzung"] for r in b.zeilen()] == bekannt
    # HA kennt zwei Zeilen der Kopie schon und quittiert sie (auch eine, die B gar nicht hat): nur diese beiden gehen
    assert b.p.quittiere([bekannt[0], bekannt[1], uuid_nr(9999)], b.uhr.jetzt()) == 2
    assert [r["sitzung"] for r in b.zeilen()] == bekannt[2:]
    assert [r["sitzung"] for r in a.zeilen()] == bekannt  # die andere Kopie ist nicht betroffen


# --- Uhr (3.3) ---------------------------------------------------------------------------------------


def unsichere_box(tmp_path, wall: float = 1000.0) -> Box:
    uhr = SimUhr(mono=5000.0, wall=wall, zeit_quelle="unbekannt", zeit_ok=False)
    return Box(tmp_path, uhr=uhr)


def test_uhr_nie_gut_die_zeilen_tragen_zeit_ok_false_und_die_monotonzeit(tmp_path):
    h = unsichere_box(tmp_path)
    eine_folge(h, 30)
    h.vergehen(3600)
    eine_folge(h, 30)
    a, b = h.zeilen()
    assert a["zeit_ok"] is False and b["zeit_ok"] is False
    assert a["beginn"].startswith("1970-01-01")  # die Wanduhr der Box ist, was sie ist; HA rechnet über die Monotonzeit
    assert b["beginn_boot_s"] - a["beginn_boot_s"] >= 3600  # der Abstand der Sitzungen ist an der Monotonzeit abzulesen
    assert a["boot_id"] == b["boot_id"] == "boot-1"
    h.vergehen(10 * 24 * 3600)
    assert h.zeilen() == [a, b]  # nichts wird erfunden
    gueltig([a, b])


def test_uhr_wird_gut_alle_zeilen_dieses_starts_werden_korrigiert_in_einem_schreibvorgang(tmp_path):
    h = unsichere_box(tmp_path)
    eine_folge(h, 30)
    h.vergehen(600)
    eine_folge(h, 30)
    h.abspielen()
    h.spiele(20)  # eine offene Sitzung
    vorher = h.zeilen()
    n = h.p.schreibungen
    h.uhr.setze_wall(ANFANG_WALL + 5000)  # NTP ist da: die Uhr springt
    h.uhr.setze_zeit("ntp", True)
    h.vergehen(1)
    nachher = h.zeilen()
    assert all(z["zeit_ok"] for z in nachher) and h.p.schreibungen == n + 1
    for alt, neu in zip(vorher, nachher):
        erwartet = g.iso(h.uhr.wall - (h.uhr.mono - alt["beginn_boot_s"]))
        assert neu["beginn"] == erwartet
        assert {k: v for k, v in neu.items() if k not in ("beginn", "zeit_ok")} == {k: v for k, v in alt.items() if k not in ("beginn", "zeit_ok")}
    assert h.inhalt()["zeilen"] == nachher and h.inhalt()["offen"]["zeit_ok"] is True  # auch die offene Sitzung
    assert nachher[1]["beginn"] > nachher[0]["beginn"]
    h.folge_zu_ende()
    assert h.zeilen()[-1]["zeit_ok"] is True
    gueltig(h.zeilen())


def test_zeilen_aus_einem_frueheren_gerätestart_werden_nie_korrigiert(tmp_path):
    h = unsichere_box(tmp_path)
    eine_folge(h, 30)
    alt = h.zeilen()
    h2 = h.neu_starten(boot="boot-2")  # das Gerät wurde ausgeschaltet; die Monotonzeit gehört zum alten Start
    h2.uhr.setze_wall(ANFANG_WALL)
    h2.uhr.setze_zeit("rtc", True)
    h2.vergehen(1)
    assert h2.zeilen() == alt and alt[0]["boot_id"] == "boot-1"
    eine_folge(h2, 30)
    assert h2.zeilen()[1]["boot_id"] == "boot-2" and h2.zeilen()[1]["zeit_ok"] is True


def test_dienst_neustart_im_selben_geraetestart_laesst_die_uhr_noch_gut_werden(tmp_path):
    h = unsichere_box(tmp_path)
    eine_folge(h, 30)
    h2 = h.neu_starten()  # gleiche ``boot_id``
    h2.uhr.setze_wall(ANFANG_WALL)
    h2.uhr.setze_zeit("ntp", True)
    h2.vergehen(1)
    assert h2.zeilen()[0]["zeit_ok"] is True


def test_uhrsprung_in_der_sitzung_aendert_die_hoerzeit_nicht(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(30)
    beginn = h.p.z.offen.beginn
    h.uhr.setze_wall(h.uhr.wall - 3 * 24 * 3600)  # die Wanduhr springt zurück (falsche RTC, dann NTP)
    h.spiele(30)
    h.uhr.setze_wall(h.uhr.wall + 10 * 24 * 3600)  # und weit nach vorn
    h.spiele(30)
    h.folge_zu_ende()
    (z,) = h.zeilen()
    assert z["gehoert_s"] == 89 and z["beginn"] == beginn and z["ende_boot_s"] - z["beginn_boot_s"] == 89
    gueltig([z])


def test_ohne_lesbare_boot_id_nimmt_die_box_eine_zufaellige_je_dienststart(tmp_path):
    h = Box(tmp_path, boot=None)
    eine_folge(h)
    kennung = h.zeilen()[0]["boot_id"]
    assert 1 <= len(kennung) <= 64
    h2 = h.neu_starten(boot=None)
    eine_folge(h2)
    assert h2.zeilen()[1]["boot_id"] != kennung  # zwei Dienststarts, zwei Kennungen
    gueltig(h2.zeilen())


# --- Zwischenstand ------------------------------------------------------------------------------------


def test_zwischenstand_nach_15_minuten_dann_alle_15_minuten_und_nie_im_puffer(tmp_path):
    h = Box(tmp_path)
    h.abspielen()
    h.spiele(899)
    assert h.p.zwischenstand(h.uhr.jetzt()) is None
    h.spiele(2)
    z = h.p.zwischenstand(h.uhr.jetzt())
    assert z is not None and z["ende"] == "teilweise" and z["sitzung"] == h.p.z.offen.sitzung
    gueltig([{**z, "ende": "pause"}])
    assert h.p.zwischenstand(h.uhr.jetzt()) is None
    h.spiele(900)
    z2 = h.p.zwischenstand(h.uhr.jetzt())
    assert z2 is not None and z2["sitzung"] == z["sitzung"] and z2["gehoert_s"] > z["gehoert_s"]
    assert h.zeilen() == [] and "teilweise" not in json.dumps(h.inhalt()["zeilen"])
    h.folge_zu_ende()  # der Abschluss trägt dieselbe UUID
    assert h.zeilen()[0]["sitzung"] == z["sitzung"]


def test_unveraenderter_zustand_bleibt_nach_kopie_gleich():
    # ``zu_json`` des leeren Zustands: der Vertrag der Datei (data-model 1.6)
    assert g.zu_json(g.Zustand()) == {"schema_version": 1, "verworfen": 0, "offen": None, "zeilen": []}
    z = g.Zustand(zeilen=({"sitzung": uuid_nr(1)},))
    assert copy.deepcopy(g.zu_json(z))["zeilen"] == [{"sitzung": uuid_nr(1)}]
