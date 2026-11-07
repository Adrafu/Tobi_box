"""``tobibox sim …`` und ``tobibox status`` als eigene Prozesse gegen den laufenden Dienst (AP 2.4).

Echter Dienst (``python -m tobibox``) mit ``fake_reader`` und echtem MPD; die Befehle gehen über
``sim.sock`` im Zustandsverzeichnis. Geprüft wird, was Tobias in der Stufe 2 ohne HA tut: einen unbekannten
Tobie auflegen, bestätigen und zuordnen, den Lernmodus starten (Serie und Folge), abbrechen, die
Status-Karte zuordnen und auflegen, ``tobibox status`` ausführlich.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import app_welt
from mpd.asyncio import MPDClient

from integration.test_app_e2e import mpd_status, warte

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fake_reader

from tobibox import events as ev

UID = "04a1b2c3"
NEU = "04ffeedd"
KARTE = "04dead01"
SERIE = "3f9a1c07b2d4"
UEBERRASCHUNG = "c07d2e91a45b"


@pytest.fixture
def welt(mpd, tmp_path):
    w = app_welt(mpd, tmp_path, {UID: ev.Zuordnung("serie", SERIE)}, {"rabe": (SERIE, ["folge-01.wav", "folge-02.wav"], 60.0)})
    w["log"] = tmp_path / "log" / "tobibox.log"
    with open(w["toml"], "a", encoding="utf-8") as f:
        f.write(f'[protokoll]\nziel = "datei"\ndatei = "{w["log"]}"\nebene = "DEBUG"\n')
    return w


def starte_dienst(welt) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "tobibox", "--config", str(welt["toml"])],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "NOTIFY_SOCKET": ""},
    )


def beende(proc: subprocess.Popen, sig=signal.SIGTERM) -> None:
    if proc.poll() is None:
        proc.send_signal(sig)
        try:
            proc.wait(15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


async def cli(welt, *argv: str) -> tuple[int, str, str]:
    """``tobibox …`` als eigener Prozess."""
    p = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "tobibox.cli", *argv[:1], "--config", str(welt["toml"]), *argv[1:],
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await asyncio.wait_for(p.communicate(), 30)
    return p.returncode, out.decode(), err.decode()


async def sim(welt, *argv: str) -> tuple[int, dict | None, str]:
    code, out, err = await cli(welt, "sim", *argv)
    return code, (json.loads(out) if out.strip() else None), err


def unknown(welt) -> dict:
    try:
        return json.loads((welt["zustand"] / "unknown.json").read_text())["eintraege"]
    except (OSError, ValueError):
        return {}


def konfig(welt) -> dict:
    return json.loads((welt["zustand"] / "config.json").read_text())


def log_zeilen(welt, ereignis: str) -> list[dict]:
    try:
        zeilen = [json.loads(z) for z in welt["log"].read_text().splitlines() if z.startswith("{")]
    except OSError:
        return []
    return [z for z in zeilen if z["ereignis"] == ereignis]


async def aktuelle_datei(port: int) -> str | None:
    c = MPDClient()
    try:
        await c.connect("127.0.0.1", port)
        return dict(await c.currentsong()).get("file")
    finally:
        c.disconnect()


async def spielt_aus(port: int, ordner: str, datei: str | None = None) -> bool:
    if (await mpd_status(port))["state"] != "play":
        return False
    f = await aktuelle_datei(port)
    return f is not None and f.startswith(f"{ordner}/") and (datei is None or f.endswith(datei))


async def dienst_bereit(welt, fr) -> None:
    await warte(lambda: (welt["zustand"] / "sim.sock").exists(), 15.0, "(sim.sock)")
    await warte(lambda: "PING" in fr.empfangen, 10.0, "(Leser verbunden)")
    await asyncio.sleep(0.8)


@pytest.fixture
async def lauf(welt):
    """Dienst + Leser; liefert ``(welt, leser)``."""
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        proc = starte_dienst(welt)
        try:
            await dienst_bereit(welt, fr)
            yield welt, fr
        finally:
            beende(proc)


async def test_ohne_dienst_ist_der_exitcode_3(welt):
    code, _, err = await sim(welt, "learn", "--serie", SERIE)
    assert code == 3 and "nicht erreichbar" in err
    code, out, _ = await cli(welt, "status")
    assert "nicht erreichbar" in out  # status geht auch ohne Dienst


async def test_unbekannter_tobie_ack_loescht_den_eintrag_und_card_wechselt_auf_die_serie(lauf):
    welt, fr = lauf
    port = welt["mpd"].port
    fr.place(NEU)
    await warte(lambda: spielt_aus(port, "ueberraschung"), 10.0, "(Überraschung spielt)")
    await warte(lambda: NEU in unknown(welt), 5.0, "(Eintrag in unknown.json)")
    e = unknown(welt)[NEU]
    assert e["art"] == "unbekannt" and e["anzahl"] == 1

    # tobibox status zeigt den offenen Eintrag und den Zustand des Dienstes
    code, text, _ = await cli(welt, "status")
    assert "läuft" in text and f"{NEU} (unbekannt, 1x)" in text and "Leser: ok" in text

    # Zuordnung: der liegende Tobie wechselt sofort auf seine Serie (CUJ 7a)
    code, antwort, err = await sim(welt, "card", NEU, "--serie", SERIE)
    assert (code, antwort) == (0, {"ok": True}), err
    await warte(lambda: spielt_aus(port, "rabe", "folge-01.wav"), 10.0, "(Serie spielt)")
    k = konfig(welt)
    assert k["revision"] == 2 and k["zuordnungen"][NEU]["ziel"] == {"typ": "serie", "serie": SERIE}
    assert NEU in unknown(welt)  # die Zuordnung allein löscht den Eintrag nicht

    # erst ack löscht ihn
    code, antwort, err = await sim(welt, "ack", NEU, "--grund", "neu")
    assert (code, antwort) == (0, {"ok": True}), err
    await warte(lambda: NEU not in unknown(welt), 5.0, "(Eintrag gelöscht)")


async def test_ack_mit_falschem_zuletzt_loescht_nichts(lauf):
    welt, fr = lauf
    fr.place(NEU)
    await warte(lambda: NEU in unknown(welt), 10.0)
    code, antwort, _ = await sim(welt, "ack", NEU, "--zuletzt", "2000-01-01T00:00:00.000Z", "--art", "unbekannt")
    assert code == 0  # der Dienst nimmt die Zeile an ...
    await asyncio.sleep(0.5)
    assert NEU in unknown(welt)  # ... aber die Meldung ist veraltet
    assert log_zeilen(welt, "ack_veraltet")


async def test_offene_meldung_bleibt_ueber_den_neustart_des_dienstes(welt):
    with fake_reader.FakeReader(welt["link"], hb_intervall_s=0.5) as fr:
        proc = starte_dienst(welt)
        proc2 = None
        try:
            await dienst_bereit(welt, fr)
            fr.place(NEU)
            await warte(lambda: NEU in unknown(welt), 10.0)
            beende(proc, signal.SIGKILL)
            proc2 = starte_dienst(welt)
            n = len(fr.empfangen)
            await warte(lambda: "PING" in fr.empfangen[n:], 15.0)
            await asyncio.sleep(0.5)
            code, out, _ = await cli(welt, "status", "--json")
            d = json.loads(out)
            assert [m["uid"] for m in d["offene_meldungen"]] == [NEU]
            assert [m["uid"] for m in d["live"]["offen"]] == [NEU]
        finally:
            beende(proc, signal.SIGKILL)
            if proc2 is not None:
                beende(proc2)


async def test_lernmodus_serie_zuordnung_bestaetigung_und_serie_spielt(lauf):
    welt, fr = lauf
    port = welt["mpd"].port
    code, antwort, err = await sim(welt, "learn", "--serie", SERIE)
    assert (code, antwort) == (0, {"ok": True}), err
    await warte(lambda: log_zeilen(welt, "lernmodus_beginn"), 5.0, "(Lernmodus an)")
    fr.place(NEU)
    await warte(lambda: spielt_aus(port, "rabe", "folge-01.wav"), 10.0, "(Serie spielt)")
    # Zuordnung geschrieben (Revision + 1), bestätigt, Eintrag gelöscht, Lernmodus aus
    k = konfig(welt)
    assert k["revision"] == 2 and k["zuordnungen"][NEU]["ziel"] == {"typ": "serie", "serie": SERIE}
    await warte(lambda: unknown(welt) == {} and (welt["zustand"] / "unknown.json").exists(), 5.0, "(Eintrag gelöscht)")
    assert log_zeilen(welt, "lernmodus_ende")[-1]["ergebnis"] == "aufgelegt"
    code, out, _ = await cli(welt, "status", "--json")
    assert json.loads(out)["live"]["status"]["lernmodus"] is False


async def test_lernmodus_folge_der_tobie_spielt_diese_folge(lauf):
    welt, fr = lauf
    port = welt["mpd"].port
    code, _, err = await sim(welt, "learn", "--serie", SERIE, "--folge", "folge-02.wav")
    assert code == 0, err
    await warte(lambda: log_zeilen(welt, "lernmodus_beginn"), 5.0)
    fr.place(NEU)
    await warte(lambda: spielt_aus(port, "rabe", "folge-02.wav"), 10.0, "(Folge 2 spielt)")
    assert konfig(welt)["zuordnungen"][NEU]["ziel"] == {"typ": "folge", "serie": SERIE, "folge": "folge-02.wav"}


async def test_abbruch_beendet_den_lernmodus_der_naechste_tobie_ist_unbekannt(lauf):
    welt, fr = lauf
    await sim(welt, "learn", "--serie", SERIE)
    await warte(lambda: log_zeilen(welt, "lernmodus_beginn"), 5.0)
    code, antwort, err = await sim(welt, "learn-abort")
    assert code == 0, err
    await warte(lambda: log_zeilen(welt, "lernmodus_ende"), 5.0, "(Lernmodus aus)")
    assert log_zeilen(welt, "lernmodus_ende")[-1]["ergebnis"] == "abbruch"
    fr.place(NEU)
    await warte(lambda: NEU in unknown(welt), 10.0)
    assert unknown(welt)[NEU]["art"] == "unbekannt" and NEU not in konfig(welt)["zuordnungen"]


async def test_ungueltige_befehle_werden_abgelehnt_der_dienst_laeuft_weiter(lauf):
    welt, _ = lauf
    code, antwort, err = await sim(welt, "card", "keine-uid", "--serie", SERIE)
    assert code == 1 and antwort["ok"] is False and "abgelehnt" in err
    code, antwort, _ = await sim(welt, "learn", "--serie", SERIE, "--ttl", "0")
    assert code == 1 and antwort["ok"] is False
    code, antwort, _ = await sim(welt, "learn", "--serie", SERIE)
    assert code == 0


async def test_falsche_serien_id_wird_vom_cli_abgelehnt_der_dienst_hoert_nichts(lauf):
    welt, _ = lauf
    code, antwort, err = await sim(welt, "card", KARTE, "--serie", "rabe")
    assert code == 2 and antwort is None
    assert f"{SERIE} (rabe)" in err and "Ordnername" in err
    code, antwort, err = await sim(welt, "learn", "--serie", SERIE, "--folge", "gibt-es-nicht.wav")
    assert code == 2 and antwort is None and "folge-01.wav, folge-02.wav" in err
    assert KARTE not in konfig(welt).get("zuordnungen", {})


async def test_status_karte_wird_zugeordnet_und_aufgelegt_eine_tonfolge_keine_wiedergabe(lauf):
    welt, fr = lauf
    port = welt["mpd"].port
    code, _, err = await sim(welt, "card", KARTE, "--aktion", "status")
    assert code == 0, err
    assert konfig(welt)["zuordnungen"][KARTE]["ziel"] == {"typ": "aktion", "aktion": "status"}
    fr.place(KARTE)
    await warte(lambda: log_zeilen(welt, "status_geprueft"), 10.0, "(Prüfung gelaufen)")
    z = log_zeilen(welt, "status_geprueft")[-1]
    assert z["baustein"] == "selftest" and z["daten"]["leser"] == "ok" and z["daten"]["medien"] == "ok"
    assert z["daten"]["netz"].startswith("FEHLER")  # Stufe 2: kein Broker, Netz offline
    assert (await mpd_status(port))["state"] != "play"
    # die Töne laufen mit dem Ton-Kommando der Prüfumgebung (``true``): ein Ton je Prüfpunkt, keiner fehlt
    assert not [t for t in log_zeilen(welt, "ton") if t["ergebnis"] == "datei_fehlt"]


async def test_status_ausfuehrlich_mit_laufendem_dienst(lauf):
    welt, fr = lauf
    code, out, _ = await cli(welt, "status", "--json")
    d = json.loads(out)
    s = d["live"]["status"]
    assert s["v"] == 1 and s["leser"] == "ok" and s["firmware"] and s["zustand"] in ("leer", "pausiert")
    assert s["konfig"]["revision"] == 1 and s["netz"] == "offline" and s["protokoll"] == 1
    assert [p["name"] for p in d["live"]["pruefpunkte"]["punkte"]] == ["leser", "medien", "netz", "speicher"]
    code, text, _ = await cli(welt, "status")
    assert "Dienst:    läuft" in text and "Status-Karte: leser ok, medien ok, netz FEHLER, speicher ok" in text
