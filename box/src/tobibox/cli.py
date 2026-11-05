"""Kommandozeile ``tobibox`` (erste Fassung): ``tobibox status``.

``status`` liest nur Dateien (Konfiguration, Zustandsverzeichnis, Medienordner,
Ereignisprotokoll) und braucht **keinen laufenden Dienst**. Es verändert nichts
(keine Umbenennung defekter Dateien, kein Aufräumen). Das sagt die Ausgabe in
der ersten Zeile. Ein Statusweg zum laufenden Dienst folgt in Stufe 2.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from . import __version__
from . import config as konfig_modul
from . import library, store
from .protocol import PROTO_UNTERSTUETZT

ENV_KONFIG = "TOBIBOX_CONFIG"
STANDARD_KONFIG = "tobibox.toml"
LOG_LESE_BYTES = 256_000
LETZTE_FEHLER = 5

OK, FEHLER, UNBEKANNT = "ok", "FEHLER", "unbekannt"


def _lese_json(pfad: Path, pruefe):  # type: ignore[no-untyped-def]
    """Nur lesen: gibt (wert, hinweis) zurück; bei fehlender Datei (None, "fehlt")."""
    if not pfad.exists():
        return None, "fehlt"
    try:
        return store.lese_pruefe(pfad, pruefe), ""
    except (store.Ungueltig, OSError) as e:
        return None, f"ungueltig ({e})"


def _log_zeilen(pfad: Path) -> list[dict]:
    """Die letzten Zeilen des Ereignisprotokolls (nur die Endung der Datei lesen)."""
    try:
        with open(pfad, "rb") as f:
            f.seek(0, os.SEEK_END)
            groesse = f.tell()
            f.seek(max(0, groesse - LOG_LESE_BYTES))
            roh = f.read().decode("utf-8", "replace")
    except OSError:
        return []
    zeilen: list[dict] = []
    for z in roh.splitlines():
        try:
            d = json.loads(z)
        except ValueError:
            continue
        if isinstance(d, dict):
            zeilen.append(d)
    return zeilen


def sammle_status(kfg: konfig_modul.BoxKonfig) -> dict:
    """Prüfpunkte als Wörterbuch (auch für Tests)."""
    # Bibliothek lesen schreibt Protokollzeilen; im Status soll nichts davon erscheinen.
    log = logging.getLogger("tobibox")
    alte, log.handlers = log.handlers, [logging.NullHandler()]
    try:
        bib = library.lade_bibliothek(kfg.pfade.medien)
    finally:
        log.handlers = alte

    zustand = kfg.pfade.zustand
    resume, r_hinweis = _lese_json(zustand / "resume.json", store.parse_resume)
    cfg, c_hinweis = _lese_json(zustand / "config.json", store.parse_konfig)

    log_zeilen: list[dict] = []
    log_hinweis = ""
    if kfg.protokoll.ziel == "datei" and kfg.protokoll.datei is not None:
        log_zeilen = _log_zeilen(kfg.protokoll.datei)
        if not log_zeilen:
            log_hinweis = f"keine Zeilen in {kfg.protokoll.datei}"
    else:
        log_hinweis = "Protokoll geht nach stdout; am Pi: journalctl -u tobibox"

    fehler = [z for z in log_zeilen if z.get("ebene") == "ERROR"][-LETZTE_FEHLER:]
    leser_zeilen = [z for z in log_zeilen if z.get("baustein") == "reader"]
    if leser_zeilen:
        letzte = leser_zeilen[-1]
        leser = {"zustand": FEHLER if letzte.get("ebene") == "ERROR" else OK,
                 "letztes": f"{letzte.get('ereignis')} ({letzte.get('zeit')})"}
    else:
        leser = {"zustand": UNBEKANNT, "letztes": "kein Leser-Ereignis im Protokoll (Dienst läuft nicht?)"}

    folgen = sum(len(s.folgen) for s in bib.serien)
    medien_ok = bool(bib.serien) and folgen > 0 and bib.ueberraschung_status == "ok"
    return {
        "dienst": "nicht abgefragt: Zustand aus Dateien, kein laufender Dienst nötig",
        "leser": leser,
        "medien": {
            "zustand": OK if medien_ok else FEHLER,
            "pfad": str(kfg.pfade.medien),
            "serien": len(bib.serien),
            "folgen": folgen,
            "ueberraschung": bib.ueberraschung_status,
        },
        "speicher": {
            "zustand": OK if (r_hinweis in ("", "fehlt") and c_hinweis in ("", "fehlt")) else FEHLER,
            "pfad": str(zustand),
            "resume": f"{len(resume)} Zeiger" if resume is not None else r_hinweis,
            "config": f"Revision {cfg.revision}, {len(cfg.zuordnungen)} Zuordnungen" if cfg is not None else c_hinweis,
        },
        "letzte_fehler": [
            f"{z.get('zeit')} {z.get('baustein')}/{z.get('ereignis')} {z.get('meldung', '')}".rstrip() for z in fehler
        ],
        "protokoll": log_hinweis or str(kfg.protokoll.datei),
        "versionen": {"tobibox": __version__, "protokoll": max(PROTO_UNTERSTUETZT), "python": platform.python_version()},
    }


def formatiere(st: dict) -> str:
    z = [
        "tobibox status (erste Fassung)",
        f"Dienst:    {st['dienst']}",
        f"Leser:     {st['leser']['zustand']}  {st['leser']['letztes']}",
        "Medien:    {zustand}  {serien} Serien, {folgen} Folgen, Überraschung: {ueberraschung} ({pfad})".format(**st["medien"]),
        "Speicher:  {zustand}  Zeiger: {resume}; Konfiguration: {config} ({pfad})".format(**st["speicher"]),
        f"Protokoll: {st['protokoll']}",
        "Letzte Fehler:" + ("" if st["letzte_fehler"] else " keine im Protokoll"),
        *[f"  {t}" for t in st["letzte_fehler"]],
        "Versionen: tobibox {tobibox}, Leser-Protokoll {protokoll}, Python {python}".format(**st["versionen"]),
    ]
    return "\n".join(z)


def _konfig_pfad(arg: str | None) -> Path:
    return Path(arg or os.environ.get(ENV_KONFIG) or STANDARD_KONFIG)


def status(args: argparse.Namespace, ausgabe: TextIO) -> int:
    try:
        kfg = konfig_modul.lade(_konfig_pfad(args.config))
    except konfig_modul.KonfigFehler as e:
        print(f"tobibox status: {e}", file=sys.stderr)
        return 2
    st = sammle_status(kfg)
    print(json.dumps(st, ensure_ascii=False, indent=2) if args.json else formatiere(st), file=ausgabe)
    ok = st["medien"]["zustand"] == OK and st["speicher"]["zustand"] == OK and st["leser"]["zustand"] != FEHLER
    return 0 if ok else 1


def main(argv: Sequence[str] | None = None, ausgabe: TextIO | None = None) -> int:
    p = argparse.ArgumentParser(prog="tobibox")
    p.add_argument("--version", action="version", version=f"tobibox {__version__}")
    sub = p.add_subparsers(dest="befehl", required=True)
    s = sub.add_parser("status", help="Prüfpunkte, letzte Fehler, Versionen (ohne laufenden Dienst)")
    s.add_argument("--config", help=f"tobibox.toml (sonst ${ENV_KONFIG} oder ./{STANDARD_KONFIG})")
    s.add_argument("--json", action="store_true", help="maschinenlesbar")
    s.set_defaults(func=status)
    args = p.parse_args(argv)
    return args.func(args, ausgabe or sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
