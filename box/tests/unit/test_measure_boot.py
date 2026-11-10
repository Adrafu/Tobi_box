"""Messskript Bootzeit (Ein/Aus, 10.11.; AP E1-8): Auswertung der Quellen, ohne Pi."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("measure_boot", WURZEL / "tools" / "measure_boot.py")
mb = importlib.util.module_from_spec(spec)
sys.modules["measure_boot"] = mb
spec.loader.exec_module(mb)

PROTOKOLL = "\n".join([
    '{"zeit":"2026-11-10T07:00:00.000Z","mono":3.1,"zeitquelle":"system","ebene":"INFO","baustein":"app","ereignis":"start","ergebnis":"ok"}',
    '{"zeit":"2026-11-10T07:00:03.000Z","mono":5.9,"zeitquelle":"system","ebene":"INFO","baustein":"app","ereignis":"fruehton","ergebnis":"fertig"}',
    '{"zeit":"2026-11-10T07:00:03.100Z","mono":6.0,"zeitquelle":"system","ebene":"INFO","baustein":"app","ereignis":"bereit","ergebnis":"ok"}',
    "kein json",
])
ANALYZE = "Startup finished in 1.790s (kernel) + 5.780s (userspace) = 7.570s"
SYSTEMCTL = "ExecMainStartTimestampMonotonic=3500000\nExecMainExitTimestampMonotonic=4200000\n"


def test_parser():
    assert mb.parse_analyze(ANALYZE) == (1.79, 5.78)
    assert mb.parse_analyze("Startup finished in 3.0s (firmware) + 2.0s (loader) + 1.5s (kernel) + 1min 5.2s (userspace) = 1min 11.7s") == (1.5, 65.2)
    assert mb.parse_analyze("nichts") is None
    assert mb.parse_systemctl(SYSTEMCTL + "ExecMainStartTimestampMonotonic=0\nAndere=1\n")["ExecMainExitTimestampMonotonic"] == 4.2
    assert mb.parse_protokoll(PROTOKOLL) == {"start": 3.1, "fruehton": 5.9, "fruehton_ergebnis": "fertig", "bereit": 6.0}


def test_nur_der_letzte_start_zaehlt():
    zwei = PROTOKOLL.splitlines()
    spaet = '{"mono":900.0,"baustein":"app","ereignis":"start","ergebnis":"ok"}'
    assert mb.parse_protokoll("\n".join(zwei + [spaet])) == {"start": 900.0}


def test_soll_wird_ab_5_v_gerechnet_firmware_zeit_kommt_dazu():
    z = mb.auswerten(protokoll=mb.parse_protokoll(PROTOKOLL), analyze=mb.parse_analyze(ANALYZE), systemctl=mb.parse_systemctl(SYSTEMCTL))
    nach_name = {r.name: r for r in z}
    ton = nach_name["Frühton zu Ende (Dienst endet)"]
    assert ton.wert_s == 4.2 + mb.FIRMWARE_S and ton.gehalten is False  # 5,45 s ist über dem Soll von 5 s
    bereit = nach_name["Bereit"]
    assert bereit.wert_s == 6.0 + mb.FIRMWARE_S and bereit.gehalten is True  # 7,25 s
    assert "Frühton nach Bereit" not in nach_name  # Bereit kam nach dem Ende des Frühdienstes


def test_ohne_bereit_im_protokoll_ist_das_soll_unbekannt_nicht_gehalten():
    z = mb.auswerten(protokoll={"start": 3.0}, analyze=None, systemctl={})
    assert {r.name: r for r in z}["Bereit"].gehalten is None


def test_ausgabe_nennt_ja_und_nein(tmp_path, capsys):
    log, an, sc = tmp_path / "l", tmp_path / "a", tmp_path / "s"
    log.write_text(PROTOKOLL)
    an.write_text(ANALYZE)
    sc.write_text(SYSTEMCTL)
    assert mb.main(["--log", str(log), "--analyze", str(an), "--systemctl", str(sc)]) == 1  # Frühton knapp zu spät
    aus = capsys.readouterr().out
    assert "Soll ≤ 5 s: NEIN" in aus and "Soll ≤ 8.5 s: JA" in aus
    assert mb.main(["--log", str(log), "--analyze", str(an), "--systemctl", str(sc), "--firmware-s", "0"]) == 0
