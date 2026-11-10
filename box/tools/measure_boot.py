#!/usr/bin/env python3
"""Misst die Bootzeit der Box am Pi: 5 V am Pi -> früher Start-Ton -> ``Bereit`` (Ein/Aus, 10.11.; AP E1-8, Messliste M-P1 und M-P2).

    python box/tools/measure_boot.py                       # auf dem Pi, direkt nach dem Hochfahren
    python box/tools/measure_boot.py --log /var/lib/tobibox/log/tobibox.log --analyze analyze.txt --systemctl units.txt   # aus Dateien

Quellen (alle Zeiten in Sekunden seit dem Start des Kernels; ``mono`` des Ereignisprotokolls ist ``time.monotonic`` und unter Linux genau das):

* Ereignisprotokoll des Box-Dienstes (``data-model.md``, 8): ``app/start/ok`` (Dienst läuft an) und ``app/bereit/ok`` (*Bereit*), dazu
  ``app/fruehton/...`` (was ``app`` bei ``Bereit`` mit der Marke tat). Der Pfad steht in ``[protokoll] datei``.
* ``systemd-analyze``: Kernel- und Userspace-Zeit (``Startup finished in 1.9s (kernel) + 5.8s (userspace) = 7.7s``).
* ``systemctl show tobibox-fruehton.service -p ExecMainStartTimestampMonotonic -p ExecMainExitTimestampMonotonic`` (Mikrosekunden seit dem
  Start des Kernels): Beginn und Ende des Frühdienstes. Der Ton klingt zwischen beiden; sein Ende ist das Ende des Dienstes.

Die Firmware des ESP32 braucht vom Strom bis zum Start des Pi eine feste Zeit (Schätzung 1,25 s, ``--firmware-s``); sie kommt auf die Zeiten
seit dem Kernelstart drauf, denn die Soll-Werte zählen **ab 5 V am Pi**. Soll (``docs/timing.md``): Frühton höchstens 5 s, *Bereit* höchstens
8,5 s (Rückfall 15 s, E13). Die Ausgabe nennt für jede Zeile, ob das Soll gehalten ist, und was fehlt. Kein Messwert ersetzt die Stoppuhr am
Gerät (Lauflicht bis Ton); das Skript misst nur, was der Dienst selbst weiß.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FIRMWARE_S = 1.25  # Schätzung, Entwurf Ein/Aus 6.1 (M10 misst sie)
SOLL_FRUEHTON_S = 5.0
SOLL_BEREIT_S = 8.5
RUECKFALL_BEREIT_S = 15.0

_ANALYZE = re.compile(
    r"Startup finished in\s+(?:(?P<fw>[\d.]+\s*m?s)\s*\(firmware\)\s*\+\s*)?(?:(?P<loader>[\d.]+\s*m?s)\s*\(loader\)\s*\+\s*)?"
    r"(?P<kernel>[\d.]+\s*m?s)\s*\(kernel\)\s*\+\s*(?P<user>(?:\d+min\s*)?[\d.]+\s*m?s)\s*\(userspace\)"
)


def _sekunden(text: str) -> float:
    """``1.9s``, ``1min 5.2s``, ``850ms`` -> Sekunden."""
    t = text.strip()
    s = 0.0
    m = re.match(r"(\d+)min\s*(.*)", t)
    if m:
        s += 60 * int(m.group(1))
        t = m.group(2)
    if t.endswith("ms"):
        return s + float(t[:-2]) / 1000
    return s + float(t.rstrip("s"))


def parse_analyze(text: str) -> tuple[float, float] | None:
    """``systemd-analyze``-Zeile -> (Kernel, Userspace) in Sekunden, oder ``None``."""
    m = _ANALYZE.search(text)
    return (_sekunden(m.group("kernel")), _sekunden(m.group("user"))) if m else None


def parse_systemctl(text: str) -> dict[str, float]:
    """``systemctl show -p ...``-Ausgabe -> {Name: Sekunden seit dem Kernelstart}; ``0`` (nicht gelaufen) fehlt."""
    aus: dict[str, float] = {}
    for zeile in text.splitlines():
        if "=" not in zeile:
            continue
        name, _, wert = zeile.partition("=")
        if name.endswith("TimestampMonotonic") and wert.strip().isdigit() and int(wert) > 0:
            aus[name] = int(wert) / 1_000_000
    return aus


def parse_protokoll(text: str) -> dict[str, float]:
    """Ereignisprotokoll (JSON-Zeilen) -> ``mono`` des **letzten** Starts: ``start``, ``bereit``, dazu ``fruehton`` (Ergebnis als Text unter ``fruehton_ergebnis``)."""
    aus: dict[str, float] = {}
    letzter_start = None
    for zeile in text.splitlines():
        if not zeile.startswith("{"):
            continue
        try:
            z = json.loads(zeile)
        except ValueError:
            continue
        if z.get("baustein") != "app" or "mono" not in z:
            continue
        if z.get("ereignis") == "start" and z.get("ergebnis") == "ok":
            letzter_start = z["mono"]
            aus = {"start": z["mono"]}
        elif letzter_start is not None and z.get("ereignis") == "bereit" and z.get("ergebnis") == "ok":
            aus["bereit"] = z["mono"]
        elif letzter_start is not None and z.get("ereignis") == "fruehton":
            aus["fruehton"] = z["mono"]
            aus["fruehton_ergebnis"] = z.get("ergebnis")  # type: ignore[assignment]
    return aus


@dataclass(frozen=True)
class Zeile:
    name: str
    wert_s: float | None  # ab 5 V am Pi
    soll_s: float | None
    hinweis: str = ""

    @property
    def gehalten(self) -> bool | None:
        if self.wert_s is None or self.soll_s is None:
            return None
        return self.wert_s <= self.soll_s


def auswerten(
    *, protokoll: dict, analyze: tuple[float, float] | None, systemctl: dict[str, float], firmware_s: float = FIRMWARE_S
) -> list[Zeile]:
    """Die Messzeilen. Alle Werte zählen ab 5 V am Pi (Zeit seit Kernelstart plus ``firmware_s``)."""
    z: list[Zeile] = []
    if analyze is not None:
        kernel, user = analyze
        z.append(Zeile("Kernel", firmware_s + kernel, None, f"{kernel:.2f} s Kernel"))
        z.append(Zeile("Userspace fertig (systemd-analyze)", firmware_s + kernel + user, None, f"{user:.2f} s Userspace"))
    start = systemctl.get("ExecMainStartTimestampMonotonic")
    ende = systemctl.get("ExecMainExitTimestampMonotonic")
    if start is not None:
        z.append(Zeile("Frühdienst beginnt", firmware_s + start, None))
    if ende is not None:
        z.append(Zeile("Frühton zu Ende (Dienst endet)", firmware_s + ende, SOLL_FRUEHTON_S,
                       f"Ton dauert {ende - start:.2f} s" if start is not None else ""))
    elif start is not None:
        z.append(Zeile("Frühton zu Ende", None, SOLL_FRUEHTON_S, "Dienst läuft noch oder endete nicht sauber"))
    if "start" in protokoll:
        z.append(Zeile("Box-Dienst läuft an", firmware_s + protokoll["start"], None))
    if "bereit" in protokoll:
        z.append(Zeile("Bereit", firmware_s + protokoll["bereit"], SOLL_BEREIT_S,
                       f"Rückfall {RUECKFALL_BEREIT_S:g} s (E13)" if firmware_s + protokoll["bereit"] > SOLL_BEREIT_S else ""))
    else:
        z.append(Zeile("Bereit", None, SOLL_BEREIT_S, "kein app/bereit/ok im Protokoll"))
    if "fruehton" in protokoll and "bereit" in protokoll:
        z.append(Zeile("Marke bei Bereit", None, None, f"{protokoll.get('fruehton_ergebnis')}"))
    if "fruehton" in protokoll and "bereit" in protokoll and ende is not None and protokoll["bereit"] < ende:
        z.append(Zeile("Frühton nach Bereit", None, None, "der Frühton lief noch, als der Dienst bereit war (die Töne des Kerns warten)"))
    return z


def formatiere(zeilen: list[Zeile]) -> str:
    aus = ["Messung ab 5 V am Pi (Firmware-Zeit ist eine Schätzung, Stoppuhr am Gerät bleibt nötig)", ""]
    for r in zeilen:
        wert = "—" if r.wert_s is None else f"{r.wert_s:6.2f} s"
        soll = "" if r.soll_s is None else f"Soll ≤ {r.soll_s:g} s: " + ("JA" if r.gehalten else "NEIN" if r.gehalten is False else "unbekannt")
        aus.append(f"{r.name:<38} {wert:>9}  {soll}  {r.hinweis}".rstrip())
    return "\n".join(aus)


def _lies(pfad: str | None, befehl: list[str]) -> str:
    if pfad:
        return Path(pfad).read_text(encoding="utf-8", errors="replace")
    try:
        return subprocess.run(befehl, capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--log", help="Ereignisprotokoll des Box-Dienstes (JSON-Zeilen); Pflicht außer in Tests")
    p.add_argument("--analyze", help="Ausgabe von `systemd-analyze` (Datei); sonst wird es aufgerufen")
    p.add_argument("--systemctl", help="Ausgabe von `systemctl show tobibox-fruehton.service -p ...` (Datei); sonst wird es aufgerufen")
    p.add_argument("--firmware-s", type=float, default=FIRMWARE_S, help=f"Zeit der Firmware vom Strom bis zum Pi-Start (Vorgabe {FIRMWARE_S})")
    a = p.parse_args(argv)
    if not a.log:
        p.error("--log fehlt (Pfad aus [protokoll] datei)")
    protokoll = parse_protokoll(Path(a.log).read_text(encoding="utf-8", errors="replace"))
    analyze = parse_analyze(_lies(a.analyze, ["systemd-analyze"]))
    systemctl = parse_systemctl(_lies(a.systemctl, [
        "systemctl", "show", "tobibox-fruehton.service", "-p", "ExecMainStartTimestampMonotonic", "-p", "ExecMainExitTimestampMonotonic"
    ]))
    zeilen = auswerten(protokoll=protokoll, analyze=analyze, systemctl=systemctl, firmware_s=a.firmware_s)
    print(formatiere(zeilen))
    return 0 if all(z.gehalten is not False for z in zeilen) else 1


if __name__ == "__main__":
    sys.exit(main())
