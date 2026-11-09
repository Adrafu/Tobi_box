"""Kommandozeile ``tobibox``: ``tobibox status`` und ``tobibox sim``.

``status`` liest Dateien (Konfiguration, Zustandsverzeichnis, Medienordner,
Ereignisprotokoll) und braucht **keinen laufenden Dienst**. Es verändert nichts
(keine Umbenennung defekter Dateien, kein Aufräumen). Läuft der Dienst, fragt
``status`` ihn zusätzlich über ``sim.sock`` und zeigt den Status-JSON (``core-interface.md``,
Abschnitt 12; ``mqtt-v1.md``, 3.3) und die Prüfpunkte der Status-Karte.

``sim`` ist ein Client des Unix-Sockets ``sim.sock`` im Zustandsverzeichnis (Stufe 2, ``sim.py``):
``learn``, ``learn-abort``, ``ack`` und ``card``. Exit-Codes von ``sim``: 0 angenommen, 1 abgelehnt, 2 Eingabe,
3 Dienst nicht erreichbar, 4 keine Berechtigung auf ``sim.sock``. ``learn`` und ``card`` prüfen vorab, ob es
Serie und Folge in der Bibliothek gibt; sonst Exit-Code 2 mit den vorhandenen Serien-IDs in der Meldung.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from . import __version__
from . import config as konfig_modul
from . import library, outbox, selftest, store
from .protocol import PROTO_UNTERSTUETZT
from .sim import SOCKET_NAME, SocketPfadZuLang, pruefe_socket_pfad

ENV_KONFIG = "TOBIBOX_CONFIG"
STANDARD_KONFIG = "tobibox.toml"
LOG_LESE_BYTES = 256_000
LETZTE_FEHLER = 5
SOCKET_TIMEOUT_S = 3.0

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


def _frage_socket(pfad: Path, zeile: dict) -> dict | None:
    """Eine JSON-Zeile an ``sim.sock`` senden, die Antwortzeile lesen.

    ``None``: Dienst nicht erreichbar. Fehlende Rechte (``PermissionError``) werden weitergereicht:
    Der Dienst läuft dann, gehört aber einem anderen Benutzer. ``SocketPfadZuLang``, wenn der Pfad
    für einen Unix-Socket zu lang ist.
    """
    pruefe_socket_pfad(pfad)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(SOCKET_TIMEOUT_S)
            s.connect(str(pfad))
            s.sendall((json.dumps(zeile) + "\n").encode())
            puffer = b""
            while not puffer.endswith(b"\n"):
                teil = s.recv(65536)
                if not teil:
                    break
                puffer += teil
        antwort = json.loads(puffer.decode("utf-8"))
    except PermissionError:
        raise
    except (OSError, ValueError):
        return None
    return antwort if isinstance(antwort, dict) else None


def frage_dienst(zustand: Path) -> dict | None:
    """Status vom laufenden Dienst (Status-JSON, Prüfpunkte, offene Meldungen) oder ``None``.

    Wirft ``PermissionError``, wenn ``sim.sock`` dem Benutzer nicht offensteht.
    """
    a = _frage_socket(zustand / SOCKET_NAME, {"befehl": "status"})
    if a is None or not a.get("ok"):
        return None
    return {k: v for k, v in a.items() if k != "ok"}


def sammle_status(kfg: konfig_modul.BoxKonfig) -> dict:
    """Prüfpunkte als Wörterbuch (auch für Tests)."""
    # Medien und Speicher misst ``selftest`` (eine Stelle für 12.3); das Lesen schreibt keine Protokollzeilen.
    messung = selftest.messe(kfg.pfade.medien)
    bib = messung.bibliothek or library.Bibliothek((), "keine")

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

    offen, o_hinweis = _lese_json(zustand / outbox.NAME, outbox._parse)
    try:
        live = frage_dienst(zustand)
        keine_rechte = False
        pfad_fehler = None
    except PermissionError:
        live, keine_rechte = None, True
    except SocketPfadZuLang as e:
        live, keine_rechte, pfad_fehler = None, False, str(e)

    folgen = sum(len(s.folgen) for s in bib.serien)
    medien_ok = selftest.pruefe_medien(messung.serien).ok
    if live is not None:
        dienst = "läuft (Status vom Dienst über sim.sock)"
    elif pfad_fehler:
        dienst = f"nicht erreichbar: {pfad_fehler}"
    elif keine_rechte:
        dienst = "keine Berechtigung auf sim.sock (gehört dem Dienst-Benutzer): Zustand aus Dateien"
    else:
        dienst = "nicht erreichbar (sim.sock): Zustand aus Dateien, kein laufender Dienst nötig"
    return {
        "dienst": dienst,
        "live": live,
        "offene_meldungen": (
            [{"uid": u, "art": e.art, "anzahl": e.anzahl, "zuletzt": e.zuletzt} for u, e in offen.items()]
            if offen is not None
            else ([] if o_hinweis == "fehlt" else o_hinweis)
        ),
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


def _offen_zeile(offen: list | str) -> str:
    if isinstance(offen, str):
        return f"Meldungen: {offen}"
    if not offen:
        return "Meldungen: keine offen (unknown.json)"
    return "Meldungen: " + ", ".join(f"{m['uid']} ({m['art']}, {m['anzahl']}x)" for m in offen) + " warten auf Bestätigung"


def _live_zeilen(live: dict | None) -> list[str]:
    if not live:
        return []
    s = live["status"]
    serie = s["serie"]["name"] if s["serie"] else "-"
    folge = f", Folge {s['folge']['name']} (Track {s['folge']['track']})" if s.get("folge") else ""
    fehler = s["letzter_fehler"]["text"] if s["letzter_fehler"] else "keiner"
    z = [
        f"  Sitzung: {s['zustand']}, Serie: {serie}{folge}, Lernmodus: {'an' if s['lernmodus'] else 'aus'}",
        f"  Leser: {s['leser']} (Firmware {s['firmware'] or '-'}), Netz: {s['netz']}, Zeit: {s['zeitquelle']}"
        f" ({'ok' if s['zeit_ok'] else 'unsicher'})",
        f"  Konfiguration: Revision {s['konfig']['revision']}, Liste {s['konfig']['liste_id'] or '-'}; "
        f"frei: {s['speicher_frei_mb']} MB; letzter Fehler: {fehler}",
        "  Status-Karte: " + ", ".join(f"{p['name']} {'ok' if p['ok'] else 'FEHLER'}" for p in live["pruefpunkte"]["punkte"]),
    ]
    for p in live["pruefpunkte"]["punkte"]:
        if not p["ok"]:
            z.append(f"    {p['name']}: {p['detail']}")
    return z


def formatiere(st: dict) -> str:
    z = [
        "tobibox status",
        f"Dienst:    {st['dienst']}",
        *_live_zeilen(st.get("live")),
        f"Leser:     {st['leser']['zustand']}  {st['leser']['letztes']}",
        "Medien:    {zustand}  {serien} Serien, {folgen} Folgen, Überraschung: {ueberraschung} ({pfad})".format(**st["medien"]),
        "Speicher:  {zustand}  Zeiger: {resume}; Konfiguration: {config} ({pfad})".format(**st["speicher"]),
        _offen_zeile(st["offene_meldungen"]),
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


def _pruefe_ziel(medien: Path, serie_id: str | None, folge: str | None) -> str | None:
    """Fehlertext, wenn es die Serie (oder die Folge) in der geladenen Bibliothek nicht gibt, sonst ``None``."""
    if serie_id is None:
        return None
    bib = library.lade_bibliothek(medien, leise=True)
    normale = [s for s in bib.serien if s.typ == "normal"]
    vorhanden = ", ".join(f"{s.id} ({s.name})" for s in normale) or "keine"
    serie = next((s for s in normale if s.id == serie_id), None)
    if serie is None:
        hinweis = ""
        nach_ordner = next((s for s in normale if Path(s.ordner).name == serie_id), None)
        if nach_ordner is not None:
            hinweis = f" Das ist der Ordnername von \"{nach_ordner.name}\", gebraucht wird die ID {nach_ordner.id}."
        return f"die Serie \"{serie_id}\" gibt es nicht.{hinweis} Vorhandene Serien-IDs: {vorhanden}"
    if folge is not None and folge not in serie.folgen:
        folgen = ", ".join(serie.folgen) or "keine"
        return f"die Folge \"{folge}\" gibt es in der Serie {serie.id} ({serie.name}) nicht. Vorhandene Folgen: {folgen}"
    return None


def _sim_zeile(args: argparse.Namespace, zustand: Path, medien: Path | None = None) -> dict | str:
    """Die JSON-Zeile für ``sim.sock`` aus den Argumenten, oder ein Fehlertext."""
    if medien is not None and args.sim_befehl in ("learn", "card") and not getattr(args, "aktion", None):
        fehler = _pruefe_ziel(medien, args.serie, args.folge)
        if fehler is not None:
            return fehler
    if args.sim_befehl == "learn":
        zeile: dict = {"befehl": "learn", "typ": "folge" if args.folge else "serie", "serie": args.serie, "ttl": args.ttl}
        if args.ueberschreiben:
            zeile["ueberschreiben"] = True
        if args.folge:
            zeile["folge"] = args.folge
        return zeile
    if args.sim_befehl == "learn-abort":
        return {"befehl": "learn_abort"}
    if args.sim_befehl == "card":
        if args.aktion:
            ziel: dict = {"typ": "aktion", "aktion": args.aktion}
        elif args.folge:
            ziel = {"typ": "folge", "serie": args.serie, "folge": args.folge}
        else:
            ziel = {"typ": "serie", "serie": args.serie}
        return {"befehl": "card", "uid": args.uid, "ziel": ziel}
    # ack: ``zuletzt`` und ``art`` stehen im Eintrag von unknown.json, wenn man sie nicht angibt
    zuletzt, art = args.zuletzt, args.art
    if zuletzt is None or art is None:
        offen, _ = _lese_json(zustand / outbox.NAME, outbox._parse)
        e = (offen or {}).get(args.uid)
        if e is None:
            return f"kein offener Eintrag für {args.uid} in unknown.json (--zuletzt und --art angeben)"
        zuletzt, art = zuletzt or e.zuletzt, art or e.art
    return {"befehl": "ack", "uid": args.uid, "zuletzt": zuletzt, "art": art, "grund": args.grund}


def sim(args: argparse.Namespace, ausgabe: TextIO) -> int:
    try:
        kfg = konfig_modul.lade(_konfig_pfad(args.config))
    except konfig_modul.KonfigFehler as e:
        print(f"tobibox sim: {e}", file=sys.stderr)
        return 2
    zustand = kfg.pfade.zustand
    zeile = _sim_zeile(args, zustand, kfg.pfade.medien)
    if isinstance(zeile, str):
        print(f"tobibox sim: {zeile}", file=sys.stderr)
        return 2
    try:
        antwort = _frage_socket(zustand / SOCKET_NAME, zeile)
    except PermissionError:
        print(
            f"tobibox sim: keine Berechtigung auf {zustand / SOCKET_NAME} (der Dienst-Benutzer ist Eigentümer, "
            "Rechte 0600); als dieser Benutzer aufrufen",
            file=sys.stderr,
        )
        return 4
    except SocketPfadZuLang as e:
        print(f"tobibox sim: {e}", file=sys.stderr)
        return 2
    if antwort is None:
        print(f"tobibox sim: Dienst nicht erreichbar ({zustand / SOCKET_NAME}); läuft tobiboxd?", file=sys.stderr)
        return 3
    print(json.dumps(antwort, ensure_ascii=False), file=ausgabe)
    if not antwort.get("ok"):
        print(f"tobibox sim: abgelehnt: {antwort.get('fehler')}", file=sys.stderr)
        return 1
    return 0


def main(argv: Sequence[str] | None = None, ausgabe: TextIO | None = None) -> int:
    p = argparse.ArgumentParser(prog="tobibox")
    p.add_argument("--version", action="version", version=f"tobibox {__version__}")
    sub = p.add_subparsers(dest="befehl", required=True)
    s = sub.add_parser("status", help="Prüfpunkte, letzte Fehler, Versionen (ohne laufenden Dienst)")
    s.add_argument("--config", help=f"tobibox.toml (sonst ${ENV_KONFIG} oder ./{STANDARD_KONFIG})")
    s.add_argument("--json", action="store_true", help="maschinenlesbar")
    s.set_defaults(func=status)
    m = sub.add_parser("sim", help="Befehle an den laufenden Dienst über sim.sock (Stufe 2, ersetzt HA)")
    m.add_argument("--config", help=f"tobibox.toml (sonst ${ENV_KONFIG} oder ./{STANDARD_KONFIG})")
    m.set_defaults(func=sim)
    ms = m.add_subparsers(dest="sim_befehl", required=True)
    lern = ms.add_parser("learn", help="Lernmodus starten (Ziel: Serie oder, mit --folge, eine Folge)")
    lern.add_argument("--serie", required=True, help="Serien-ID des Ziels")
    lern.add_argument("--folge", help="Name der Folge (Ziel ist dann eine einzelne Folge)")
    lern.add_argument("--ttl", type=int, default=60, help="Lebensdauer des Befehls in Sekunden (Vorgabe 60)")
    lern.add_argument(
        "--ueberschreiben", action="store_true",
        help="Ist der aufgelegte Tobie schon zugeordnet, ersetzt die neue Zuordnung die alte "
        "(ersetzt die Rückfrage von HA; ohne diesen Schalter bleibt die alte Zuordnung)",
    )
    ms.add_parser("learn-abort", help="Lernmodus abbrechen")
    ack = ms.add_parser("ack", help="Meldung aus unknown.json bestätigen (Eintrag wird gelöscht)")
    ack.add_argument("uid")
    ack.add_argument("--zuletzt", help="Zeitstempel der Meldung (sonst aus unknown.json)")
    ack.add_argument("--art", choices=("unbekannt", "gelernt"), help="Art der Meldung (sonst aus unknown.json)")
    ack.add_argument("--grund", default="sim", help="Grund der Bestätigung (neu, bekannt, zugeordnet, abgelehnt)")
    karte = ms.add_parser("card", help="Karte oder Tobie einem Ziel zuordnen (schreibt config.json)")
    karte.add_argument("uid")
    karte.add_argument("--serie", help="Serien-ID (Ziel Serie, mit --folge Ziel Folge)")
    karte.add_argument("--folge", help="Name der Folge")
    karte.add_argument("--aktion", choices=("status", "gute_nacht"), help="Aktionskarte")
    args = p.parse_args(argv)
    if getattr(args, "sim_befehl", None) == "card" and not (args.aktion or args.serie):
        p.error("card: --serie oder --aktion angeben")
    return args.func(args, ausgabe or sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
