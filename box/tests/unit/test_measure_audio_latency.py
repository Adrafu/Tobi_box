"""Tests für ``tools/measure_audio_latency.py`` mit künstlichen Protokollen und WAV-Dateien."""

from __future__ import annotations

import json
import math
import random
import struct
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import measure_audio_latency as m  # noqa: E402

T0 = datetime(2026, 11, 6, 9, 30, 0, tzinfo=timezone.utc).timestamp()  # Aufnahmebeginn (Wanduhr)
RATE = 8000


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def schreibe_wav(pfad, toene, dauer_s, rate=RATE, kanaele=1, breite=2, rauschen=0.002, amplitude=0.5, seed=1):
    """``toene``: Liste (von_s, bis_s); dazwischen nur Grundrauschen."""
    zufall = random.Random(seed)
    n = int(dauer_s * rate)
    voll = {1: 127, 2: 32767, 3: 8388607, 4: 2147483647}[breite]
    daten = bytearray()
    for i in range(n):
        t = i / rate
        an = any(a <= t < b for a, b in toene)
        x = amplitude * math.sin(2 * math.pi * 440 * t) if an else 0.0
        x += rauschen * (zufall.random() * 2 - 1)
        wert = int(x * voll)
        for k in range(kanaele):
            w = wert if k == 0 else int(wert * 0.1)  # zweiter Kanal leise
            if breite == 1:
                daten += struct.pack("B", w + 128)
            elif breite == 2:
                daten += struct.pack("<h", w)
            elif breite == 3:
                daten += struct.pack("<i", w << 8)[1:]
            else:
                daten += struct.pack("<i", w)
    with wave.open(str(pfad), "wb") as f:
        f.setnchannels(kanaele)
        f.setsampwidth(breite)
        f.setframerate(rate)
        f.writeframes(bytes(daten))
    return pfad


def zeile(t_rel, baustein, ereignis, vorgang, mono_offset=1000.0, **daten):
    d = {"zeit": iso(T0 + t_rel), "mono": round(mono_offset + t_rel, 3), "zeitquelle": "system", "ebene": "INFO",
         "baustein": baustein, "ereignis": ereignis, "ergebnis": "ok"}
    if vorgang:
        d["vorgang"] = vorgang
    if daten:
        d["daten"] = daten
    return json.dumps(d, separators=(",", ":"))


def schreibe_log(pfad, zeilen):
    Path(pfad).write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return pfad


def standard_log(pfad):
    """Auflegen bei 2,0 s (abspielen +40 ms), Abheben bei 8,0 s (pausieren +30 ms), zweites Auflegen bei 11,0 s."""
    return schreibe_log(pfad, [
        zeile(0.5, "app", "bereit", None),
        zeile(2.000, "reader", "aufgelegt", "aaaaaaaa", uid="04a1b2c3", seq=0),
        zeile(2.001, "reader", "entprellt", "aaaaaaaa", seq=0),
        zeile(2.040, "app", "abspielen", "aaaaaaaa", serie="s", folge="a.wav"),
        zeile(8.000, "reader", "abgehoben", "aaaaaaaa", seq=1),
        zeile(8.030, "app", "pausieren", "aaaaaaaa", grund="abgehoben"),
        zeile(11.000, "reader", "aufgelegt", "bbbbbbbb", uid="04a1b2c3", seq=2),
        zeile(11.050, "app", "abspielen", "bbbbbbbb", serie="s", folge="a.wav"),
    ])


@pytest.fixture
def standard(tmp_path):
    # Ton 1: 2,62 s bis 8,26 s (Latenz 620 ms, Ende 260 ms nach dem Abheben); Ton 2: ab 11,48 s
    wav = schreibe_wav(tmp_path / "a.wav", [(2.62, 8.26), (11.48, 13.0)], 14.0)
    return standard_log(tmp_path / "t.log"), wav


def werte(erg, art):
    return [w for w in erg.werte if w.art == art]


def laufe(protokoll, wav, *extra):
    return m.main([str(protokoll), "--wav", str(wav), "--wav-start", iso(T0), *extra])


def test_messung_auflegen_und_abheben_auf_wenige_ms_genau(standard):
    log, wav = standard
    a = m.lese_wav(wav)
    erg = m.messe(m.lese_protokoll([log]), a, T0, m.schwelle_auto(a))
    auf = werte(erg, "auflegen")
    ab = werte(erg, "abheben")
    assert [w.vorgang for w in auf] == ["aaaaaaaa", "bbbbbbbb"] and len(ab) == 1
    assert auf[0].befehl_ms == pytest.approx(40, abs=1) and auf[0].ton_ms == pytest.approx(620, abs=10)
    assert auf[1].befehl_ms == pytest.approx(50, abs=1) and auf[1].ton_ms == pytest.approx(480, abs=10)
    assert ab[0].befehl_ms == pytest.approx(30, abs=1) and ab[0].ton_ms == pytest.approx(260, abs=15)
    assert not any(w.ueber_grenze for w in erg.werte)
    assert erg.zusammenfassung["auflegen"]["gemessen"] == 2
    assert erg.zusammenfassung["auflegen"]["ton_ms"]["max"] == pytest.approx(620, abs=10)


def test_wav_start_ende_und_sync_geben_dasselbe(standard, capsys, tmp_path):
    log, wav = standard
    a = m.lese_wav(wav)
    ref = m.messe(m.lese_protokoll([log]), a, T0, m.schwelle_auto(a))
    for extra in (
        ["--wav-ende", iso(T0 + a.dauer_s)],
        ["--sync", f"{iso(T0 + 2.62)}=2.62"],
    ):
        assert m.main([str(log), "--wav", str(wav), *extra, "--json"]) == 0
        ausgabe = json.loads(capsys.readouterr().out)
        assert [w["ton_ms"] for w in ausgabe["werte"]] == pytest.approx([w.ton_ms for w in ref.werte])


def test_wav_start_auto_nimmt_dateizeit_minus_dauer(standard, capsys):
    log, wav = standard
    import os
    ende = T0 + m.lese_wav(wav).dauer_s
    os.utime(wav, (ende, ende))
    assert m.main([str(log), "--wav", str(wav), "--wav-start", "auto", "--json"]) == 0
    ausgabe = json.loads(capsys.readouterr().out)
    assert ausgabe["werte"][0]["ton_ms"] == pytest.approx(620, abs=10)


def test_ohne_oder_mit_mehreren_abgleichsangaben_ist_fehler(standard, capsys):
    log, wav = standard
    assert m.main([str(log), "--wav", str(wav)]) == 2
    assert "Genau eine Angabe" in capsys.readouterr().err
    assert m.main([str(log), "--wav", str(wav), "--wav-start", iso(T0), "--wav-ende", iso(T0)]) == 2


def test_grenze_ueberschritten_status_3_und_markierung(tmp_path, capsys):
    wav = schreibe_wav(tmp_path / "a.wav", [(3.2, 9.9)], 12.0)  # Latenz 1200 ms, Ende 1900 ms nach dem Abheben
    log = standard_log(tmp_path / "t.log")
    assert laufe(log, wav) == 3
    ausgabe = capsys.readouterr().out
    assert "ÜBER GRENZE" in ausgabe and "docs/timing.md" in ausgabe


def test_monotone_uhr_wird_fuer_logabstaende_genutzt(tmp_path):
    zeilen = [
        zeile(2.000, "reader", "aufgelegt", "aaaaaaaa", uid="u"),
        zeile(2.040, "app", "abspielen", "aaaaaaaa"),
    ]
    # Wanduhr springt zwischen den Zeilen um 5 s, mono bleibt 40 ms
    d = json.loads(zeilen[1])
    d["zeit"] = iso(T0 + 7.040)
    zeilen[1] = json.dumps(d)
    e = m.lese_protokoll([schreibe_log(tmp_path / "t.log", zeilen)])
    (v,) = m.finde_vorgaenge(e)
    assert m._abstand_ms(v.start, v.befehl) == pytest.approx(40)


def test_ton_schon_an_wird_gemeldet_nicht_gemessen(tmp_path):
    wav = schreibe_wav(tmp_path / "a.wav", [(1.0, 5.0), (11.3, 12.5)], 14.0)
    erg = m.messe(m.lese_protokoll([standard_log(tmp_path / "t.log")]), m.lese_wav(wav), T0, 0.05)
    a = werte(erg, "auflegen")[0]
    assert a.ton_ms is None and "schon an" in a.hinweis


def test_kein_ton_und_ton_endet_nicht(tmp_path):
    wav = schreibe_wav(tmp_path / "a.wav", [(7.5, 14.0)], 14.0)  # Ton erst nach dem Suchfenster von 5 s, Ende nie
    erg = m.messe(m.lese_protokoll([standard_log(tmp_path / "t.log")]), m.lese_wav(wav), T0, 0.05)
    auf = werte(erg, "auflegen")
    assert auf[0].ton_ms is None and auf[0].hinweis == "kein Ton gefunden"
    assert werte(erg, "abheben")[0].hinweis.startswith("Ton endet nicht")


def test_abheben_wenn_schon_still(tmp_path):
    wav = schreibe_wav(tmp_path / "a.wav", [(2.5, 6.0)], 14.0)
    erg = m.messe(m.lese_protokoll([standard_log(tmp_path / "t.log")]), m.lese_wav(wav), T0, 0.05)
    assert "schon still" in werte(erg, "abheben")[0].hinweis


def test_auflegen_ohne_abspielen_wird_uebersprungen(tmp_path):
    log = schreibe_log(tmp_path / "t.log", [
        zeile(2.0, "reader", "aufgelegt", "aaaaaaaa", uid="u"),  # Wiedermeldung: nichts startet
        zeile(4.0, "reader", "aufgelegt", "bbbbbbbb", uid="u"),
        zeile(4.05, "app", "abspielen", "bbbbbbbb"),
    ])
    wav = schreibe_wav(tmp_path / "a.wav", [(4.5, 6.0)], 8.0)
    erg = m.messe(m.lese_protokoll([log]), m.lese_wav(wav), T0, 0.05)
    assert [w.vorgang for w in erg.werte] == ["bbbbbbbb"]
    assert erg.werte[0].ton_ms == pytest.approx(500, abs=10)


def test_abspielen_anderer_vorgang_wird_nicht_zugeordnet(tmp_path):
    log = schreibe_log(tmp_path / "t.log", [
        zeile(2.0, "reader", "aufgelegt", "aaaaaaaa", uid="u"),
        zeile(2.05, "app", "abspielen", "zzzzzzzz"),
    ])
    wav = schreibe_wav(tmp_path / "a.wav", [(2.5, 4.0)], 6.0)
    assert m.messe(m.lese_protokoll([log]), m.lese_wav(wav), T0, 0.05).werte == []


@pytest.mark.parametrize("kanaele,breite,rate", [(1, 1, 8000), (2, 2, 8000), (1, 3, 8000), (1, 4, 8000), (1, 2, 44100)])
def test_wav_formate(tmp_path, kanaele, breite, rate):
    wav = schreibe_wav(tmp_path / "a.wav", [(2.62, 8.26)], 10.0, rate=rate, kanaele=kanaele, breite=breite)
    a = m.lese_wav(wav)
    assert a.rate == rate and a.dauer_s == pytest.approx(10.0, abs=0.01)
    wie, t = m.erster_ton(a, 2.0, 7.0, 0.05)
    assert wie == "ton" and t == pytest.approx(2.62, abs=0.012)
    wie, t = m.ton_aus(a, 7.0, 10.0, 0.05, 0.15)
    assert wie == "aus" and t == pytest.approx(8.26, abs=0.02)


def test_einzelner_klick_unter_zwei_fenstern_zaehlt_nicht_als_ton(tmp_path):
    wav = schreibe_wav(tmp_path / "a.wav", [(3.0, 3.002), (4.0, 6.0)], 8.0)  # 2 ms Klick, dann Ton bei 4 s
    a = m.lese_wav(wav)
    wie, t = m.erster_ton(a, 2.0, 7.0, 0.05)
    assert wie == "ton" and t == pytest.approx(4.0, abs=0.012)


def test_kurze_pause_im_ton_unter_der_stillegrenze_zaehlt_nicht_als_aus(tmp_path):
    wav = schreibe_wav(tmp_path / "a.wav", [(1.0, 4.0), (4.08, 6.0)], 8.0)  # 80 ms Pause
    a = m.lese_wav(wav)
    wie, t = m.ton_aus(a, 3.0, 7.0, 0.05, 0.15)
    assert wie == "aus" and t == pytest.approx(6.0, abs=0.02)


def test_schwelle_auto_folgt_dem_grundrauschen(tmp_path):
    leise = m.lese_wav(schreibe_wav(tmp_path / "l.wav", [(1, 2)], 4.0, rauschen=0.002))
    laut = m.lese_wav(schreibe_wav(tmp_path / "r.wav", [(1, 2)], 4.0, rauschen=0.05))
    assert m.schwelle_auto(leise) == pytest.approx(0.012, abs=0.004)
    assert m.schwelle_auto(laut) > 0.2


def test_mehrere_protokolldateien_rotiert_werden_sortiert(tmp_path):
    zeilen = open(standard_log(tmp_path / "x.log")).read().splitlines()
    schreibe_log(tmp_path / "tobibox.log.1", zeilen[:4])
    schreibe_log(tmp_path / "tobibox.log", ["kaputt", "{nicht json", *zeilen[4:]])
    e = m.lese_protokoll([tmp_path / "tobibox.log", tmp_path / "tobibox.log.1"])
    assert [x.ereignis for x in e if x.baustein in ("reader", "app")][:2] == ["bereit", "aufgelegt"]
    assert len(m.finde_vorgaenge(e)) == 3


def test_ausgabe_text_und_json(standard, capsys):
    log, wav = standard
    assert laufe(log, wav) == 0
    text = capsys.readouterr().out
    assert "aaaaaaaa" in text and "Auflegen: 2 von 2 gemessen" in text and "Abheben: 1 von 1 gemessen" in text
    assert laufe(log, wav, "--json") == 0
    daten = json.loads(capsys.readouterr().out)
    assert daten["zusammenfassung"]["abheben"]["gemessen"] == 1 and len(daten["werte"]) == 3


def test_fehler_bei_leerem_protokoll_kaputter_wav_und_ohne_vorgaenge(tmp_path, capsys):
    wav = schreibe_wav(tmp_path / "a.wav", [], 2.0)
    leer = tmp_path / "leer.log"
    leer.write_text("")
    assert m.main([str(leer), "--wav", str(wav), "--wav-start", iso(T0)]) == 2
    kaputt = tmp_path / "k.wav"
    kaputt.write_bytes(b"nichts")
    assert m.main([str(standard_log(tmp_path / "t.log")), "--wav", str(kaputt), "--wav-start", iso(T0)]) == 2
    nur_start = schreibe_log(tmp_path / "s.log", [zeile(0.1, "app", "bereit", None)])
    assert m.main([str(nur_start), "--wav", str(wav), "--wav-start", iso(T0)]) == 2
    assert m.main([str(nur_start), "--wav", str(wav), "--wav-start", "gestern"]) == 2
    assert "Zeit nicht lesbar" in capsys.readouterr().err


def test_vorgang_ausserhalb_der_aufnahme(tmp_path):
    wav = schreibe_wav(tmp_path / "a.wav", [(2.62, 4.0)], 5.0)
    erg = m.messe(m.lese_protokoll([standard_log(tmp_path / "t.log")]), m.lese_wav(wav), T0, 0.05)
    assert "ausserhalb" in werte(erg, "abheben")[0].hinweis


def test_hilfe_beschreibt_gebrauch(capsys):
    with pytest.raises(SystemExit) as e:
        m.main(["--help"])
    assert e.value.code == 0
    h = capsys.readouterr().out
    for stichwort in ("--wav-start", "--sync", "aufgelegt", "abspielen", "pausieren", "Grenzen"):
        assert stichwort in h


def test_klick_methode_gibt_firmware_anteil_und_gesamtzeit(tmp_path):
    # Klack (20 ms) bei 1,55 s, `aufgelegt` bei 2,0 s (Firmware 450 ms), Ton ab 2,62 s
    wav = schreibe_wav(tmp_path / "a.wav", [(1.55, 1.57), (2.62, 8.26), (11.48, 13.0)], 14.0)
    log = standard_log(tmp_path / "t.log")
    a = m.lese_wav(wav)
    erg = m.messe(m.lese_protokoll([log]), a, T0, 0.05, klick=True)
    ersatz = werte(erg, "auflegen")[0]
    assert ersatz.klick_ms == pytest.approx(450, abs=10) and ersatz.gesamt_ms == pytest.approx(1070, abs=15)
    assert ersatz.ueber_grenze  # 1070 ms > 1000 ms
    zweites = werte(erg, "auflegen")[1]
    assert zweites.klick_ms is None and "kein Klack" in zweites.hinweis
    assert erg.zusammenfassung["auflegen"]["ton_ms"]["max"] == pytest.approx(1070, abs=15)


def test_klick_cli_ausgabe(tmp_path, capsys):
    wav = schreibe_wav(tmp_path / "a.wav", [(1.55, 1.57), (2.62, 8.26)], 10.0)
    log = standard_log(tmp_path / "t.log")
    assert laufe(log, wav, "--klick") == 3
    ausgabe = capsys.readouterr().out
    assert "Gesamt (mit Klack)" in ausgabe and "ÜBER GRENZE" in ausgabe


def test_sync_start_nimmt_das_startgeraeusch_als_marke(tmp_path, capsys):
    # Standardlog: `bereit` bei 0,5 s. Die Aufnahme begann 0,3 s vor T0: alle Zeiten liegen in ihr 0,3 s später.
    # Startgeräusch 50 ms nach `bereit`: bei 0,5 + 0,05 + 0,3 = 0,85 s in der Aufnahme.
    wav = schreibe_wav(tmp_path / "b.wav", [(0.85, 0.95), (2.92, 8.56), (11.78, 13.3)], 14.0)
    assert m.main([str(standard_log(tmp_path / "t.log")), "--wav", str(wav), "--sync-start", "--json"]) == 0
    erg = json.loads(capsys.readouterr().out)
    assert [w["ton_ms"] for w in erg["werte"] if w["art"] == "auflegen"] == pytest.approx([620, 480], abs=15)


def test_sync_start_ohne_startgeraeusch_oder_bereit_ist_fehler(tmp_path, capsys):
    wav = schreibe_wav(tmp_path / "a.wav", [(0.0, 1.0)], 4.0)  # beginnt nicht still
    assert m.main([str(standard_log(tmp_path / "t.log")), "--wav", str(wav), "--sync-start"]) == 2
    assert "Startgeräusch fehlt" in capsys.readouterr().err
    log = schreibe_log(tmp_path / "x.log", [zeile(2.0, "reader", "aufgelegt", "aaaaaaaa"), zeile(2.1, "app", "abspielen", "aaaaaaaa")])
    assert m.main([str(log), "--wav", str(wav), "--sync-start"]) == 2
    assert "kein Eintrag `bereit`" in capsys.readouterr().err
