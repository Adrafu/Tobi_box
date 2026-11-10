"""Früher Start-Ton: Marke ``/run/tobibox/fruehton`` und der Frühdienst (Ein/Aus, 10.11.; AP E1-5).

``tobibox-fruehton.service`` spielt ``start.wav``, sobald der Ton-Ausgang da ist, meist **vor** dem Box-Dienst und ohne ihn aufzuhalten
(``deploy/pi/tobibox-fruehton.service``: ``Type=simple``, kein ``Before=``). Er läuft als eigener Prozess ohne Sitzung und ohne Asyncio-Schleife
des Dienstes; er liest ``tobibox.toml`` und ``config.json`` selbst.

**Die Marke** (``data-model.md``, 1.6) ist **eine** Datei mit einem Wort. Wer sie zuerst anlegt, entscheidet; angelegt wird sie atomar nur
dann, wenn es sie noch nicht gibt (``link`` einer fertig geschriebenen Datei, nie ein halb gelesener Inhalt):

* Frühdienst: ``start`` (der Ton läuft), ``keiner`` (bewusst still: Modus „stumm“, R10), danach ersetzt er ``start`` durch ``fertig``
  (oder ``fehler``, wenn der Ton nicht lief), und zwar nur, wenn die Marke noch da ist.
* ``app``: liest sie erst bei ``Bereit`` (V1). Gibt es sie noch nicht, legt ``app`` selbst ``uebernommen`` an; danach kann der Frühdienst
  seine Marke nicht mehr anlegen und spielt **nicht** (nie zwei Töne). Gibt es sie, gilt ihr Wort.

Jeder Fehler des Frühdienstes (``tobibox.toml`` unlesbar, ``start.wav`` oder das Abspielprogramm fehlt, Ausnahme) legt **keine** Marke an:
Der Kern spielt ``start`` wie bisher.

Pegel (``core-interface.md``, 8.1, R10): ``min(grenze, max(TON_MINDEST, min(lautstaerke_start, lautstaerke_max)))``; ``grenze`` ist das
Minimum aus ``lautstaerke_max``, der Grenze des „leiser“-Fensters (``quiet.wirkung_jetzt`` mit der Uhr-Regel aus ``uhrregel``) und, solange
der Kopfhörer-Kontakt nicht sicher „leer“ meldet (steckt, nicht lesbar), ``lautstaerke_kopfhoerer``. „stumm“: kein Ton, Marke ``keiner``.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from . import events as ev
from . import quiet, uhrregel

#: Am Pi ``/run/tobibox`` (tmpfs, von systemd angelegt); am Mac stellt ``TOBIBOX_MARKEN`` ein anderes Verzeichnis ein (Abnahme ohne Pi).
MARKEN_VERZEICHNIS = Path(os.environ.get("TOBIBOX_MARKEN") or "/run/tobibox")
MARKE = "fruehton"

START = "start"
KEINER = "keiner"
FERTIG = "fertig"
FEHLER = "fehler"
UEBERNOMMEN = "uebernommen"  # Gegenmarke von ``app``
WOERTER = (START, KEINER, FERTIG, FEHLER, UEBERNOMMEN)
#: Wörter, die der Frühdienst anlegt; sie bedeuten: Der Frühdienst hat entschieden.
FRUEHDIENST_WOERTER = (START, KEINER, FERTIG)
#: So lange darf das Abspielprogramm des Frühdienstes höchstens laufen.
TON_MAX_S = 10.0


# --------------------------------------------------------------------------
# Marke (gemeinsam für ``app`` und den Frühdienst)
# --------------------------------------------------------------------------


def pfad(verzeichnis: Path | str = MARKEN_VERZEICHNIS) -> Path:
    return Path(verzeichnis) / MARKE


def _temp_schreiben(verzeichnis: Path, wort: str) -> Path:
    fd, name = tempfile.mkstemp(prefix=".fruehton-", suffix=".tmp", dir=verzeichnis)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(wort + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, 0o644)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return Path(name)


def lege_marke_an(wort: str, verzeichnis: Path | str = MARKEN_VERZEICHNIS) -> bool:
    """Marke atomar anlegen, **nur wenn es sie noch nicht gibt**. ``False``: es gab sie schon (der andere war schneller)."""
    verz = Path(verzeichnis)
    tmp = _temp_schreiben(verz, wort)
    try:
        os.link(tmp, pfad(verz))  # schlägt mit EEXIST fehl, wenn die Marke da ist; die Datei erscheint immer vollständig
        return True
    except FileExistsError:
        return False
    finally:
        tmp.unlink(missing_ok=True)


def ersetze_marke(wort: str, verzeichnis: Path | str = MARKEN_VERZEICHNIS) -> bool:
    """Die Marke atomar durch ``wort`` ersetzen, **nur wenn sie noch da ist** (``rename``). ``False``: sie war schon gelöscht."""
    verz = Path(verzeichnis)
    if not pfad(verz).exists():
        return False
    tmp = _temp_schreiben(verz, wort)
    try:
        if not pfad(verz).exists():
            return False
        os.replace(tmp, pfad(verz))
        return True
    finally:
        tmp.unlink(missing_ok=True)


def lese_marke(verzeichnis: Path | str = MARKEN_VERZEICHNIS) -> str | None:
    """Das Wort der Marke; ``None``, wenn es sie nicht gibt, sie leer ist oder etwas anderes als ein bekanntes Wort enthält."""
    try:
        text = pfad(verzeichnis).read_text(encoding="ascii")
    except (OSError, ValueError):
        return None
    wort = text.strip()
    return wort if text == wort + "\n" and wort in WOERTER else None


def loesche_marke(verzeichnis: Path | str = MARKEN_VERZEICHNIS) -> None:
    with contextlib.suppress(OSError):
        pfad(verzeichnis).unlink(missing_ok=True)


def uebernimm_marke(verzeichnis: Path | str = MARKEN_VERZEICHNIS, *, neustart: bool = False) -> str | None:
    """``app`` bei ``Bereit``: das Wort des Frühdienstes (``start``, ``keiner``, ``fertig``) oder ``None`` (kein Frühton).

    Gibt es keine Marke, legt ``app`` die Gegenmarke ``uebernommen`` an und verhindert so einen späten Frühton (V1). Bei einem Dienst-Neustart
    ohne Ausschalten (gleiche Boot-Kennung) wird die Marke ignoriert und durch die Gegenmarke ersetzt. Fehler beim Schreiben (Verzeichnis fehlt,
    keine Rechte) heißen: kein Frühton."""
    verz = Path(verzeichnis)
    try:
        if neustart:
            if not ersetze_marke(UEBERNOMMEN, verz):
                lege_marke_an(UEBERNOMMEN, verz)
            return None
        if lege_marke_an(UEBERNOMMEN, verz):
            return None
    except OSError:
        return None
    wort = lese_marke(verz)
    return wort if wort in FRUEHDIENST_WOERTER else None


# --------------------------------------------------------------------------
# Frühdienst
# --------------------------------------------------------------------------


def kopfhoerer_leer(konfig, *, lese=None) -> bool | None:  # type: ignore[no-untyped-def]
    """Meldet der Kopfhörer-Kontakt **sicher** „leer“? ``True`` leer, ``False`` Stecker steckt, ``None`` nicht lesbar.

    Zwei Messungen hintereinander müssen übereinstimmen (wie die Entprellung der ``Buchse``). Am Mac (``quelle = "sim"``) steckt nie etwas."""
    kh = konfig.kopfhoerer
    if kh.simulation:
        return True
    from .headphones import GpioKopfhoerer

    treiber = lese if lese is not None else GpioKopfhoerer(kh.gpio_pin, aktiv_niedrig=kh.aktiv_niedrig)  # type: ignore[arg-type]

    async def messen() -> bool:
        a = await asyncio.wait_for(treiber.steckt(), 2.0)
        await asyncio.sleep(0.05)
        b = await asyncio.wait_for(treiber.steckt(), 2.0)
        if a != b:
            raise OSError("Kontakt unruhig")
        return a

    try:
        return not asyncio.run(messen())
    except Exception:  # noqa: BLE001 - jeder Fehler heißt „nicht lesbar“: es gilt die Kopfhörer-Grenze
        return None
    finally:
        schliesse = getattr(treiber, "schliesse", None)
        if schliesse is not None:
            with contextlib.suppress(Exception):
                schliesse()


def lese_rtc(konfig) -> datetime | None:  # type: ignore[no-untyped-def]
    """Die RTC vom ``pisugar-server``, falls er schon antwortet (kurze Frist). Mac und Fehler: ``None``."""
    s = konfig.strom
    if s is None or s.simulation:
        return None
    from .power import PiSugarStrom, parse_rtc

    async def hole() -> datetime | None:
        t = PiSugarStrom(s.pisugar_host, s.pisugar_port, s.abschalt_kommando, frist_s=0.5)
        return parse_rtc(await t._hole("rtc_time"))

    try:
        return asyncio.run(hole())
    except Exception:  # noqa: BLE001 - pisugar-server läuft noch nicht: Uhr unsicher
        return None


def pegel_fuer(konfig, grenze_fenster: int | None, leer: bool | None) -> int:
    """Pegel des frühen Start-Tons (Formel im Modulkopf)."""
    from .sounds import TON_MINDEST

    v = konfig.lautstaerke
    grenze = v.max
    if grenze_fenster is not None:
        grenze = min(grenze, grenze_fenster)
    if leer is not True:
        grenze = min(grenze, v.kopfhoerer)
    return min(grenze, max(TON_MINDEST, min(v.start, v.max)))


def entscheide(konfig, leise_zeiten, *, wall: float, mono: float, rtc: datetime | None, leer: bool | None) -> tuple[str, int]:
    """Was tut der Frühdienst? ``("stumm", 0)`` oder ``("spielen", pegel)``."""
    quelle, ok = uhrregel.fruehdienst_uhr(konfig, rtc)
    jetzt = ev.Jetzt(mono, wall, quelle, ok)
    modus, grenze = quiet.wirkung_jetzt(leise_zeiten, jetzt)
    if modus == "stumm":
        return "stumm", 0
    return "spielen", pegel_fuer(konfig, grenze, leer)


def spiele(
    konfig,  # type: ignore[no-untyped-def]
    *,
    marken_verzeichnis: Path | str = MARKEN_VERZEICHNIS,
    tondatei: Path | None = None,
    lese_kopfhoerer: Callable[[], bool | None] | None = None,
    lese_rtc_fn: Callable[[], datetime | None] | None = None,
    wall: Callable[[], float] = time.time,
    mono: Callable[[], float] = time.monotonic,
    starter: Callable[[list[str]], int] | None = None,
) -> str:
    """Der ganze Ablauf. Gibt das Ergebnis zurück: ``stumm``, ``gespielt``, ``kein_ton`` (Marke schon da oder Ton nicht gelaufen) oder ``fehler``."""
    from .sounds import baue_kommando
    from .store import KonfigStore

    verz = Path(marken_verzeichnis)
    try:
        ordner = konfig.toene.ordner or Path(__file__).resolve().parents[2] / "sounds"
        datei = tondatei or Path(ordner) / "start.wav"
        if not datei.is_file() or not konfig.toene.kommando:
            return "fehler"
        programm = konfig.toene.kommando[0]
        if starter is None and not _programm_da(programm):
            return "fehler"  # kein Ausgang, kein Programm: keine Marke, der Kern spielt ``start``
        leise = KonfigStore(konfig.pfade.zustand).laden().konfig.leise_zeiten
        leer = (lese_kopfhoerer or (lambda: kopfhoerer_leer(konfig)))()
        rtc = (lese_rtc_fn or (lambda: lese_rtc(konfig)))()
        was, pegel = entscheide(konfig, leise, wall=wall(), mono=mono(), rtc=rtc, leer=leer)
        if was == "stumm":
            lege_marke_an(KEINER, verz)  # bewusst still (R10); war die Marke schon da, ändert sich nichts
            return "stumm"
        tmp = _skaliert(datei, pegel, konfig)
        try:
            if not lege_marke_an(START, verz):
                return "kein_ton"  # ``app`` war schneller (Gegenmarke): nie zwei Töne
            ergebnis = FERTIG
            try:
                rc = (starter or _starte)(baue_kommando(konfig.toene.kommando, tmp, pegel))
                if rc != 0:
                    ergebnis = FEHLER
            except Exception:  # noqa: BLE001
                ergebnis = FEHLER
            finally:
                ersetze_marke(ergebnis, verz)
            return "gespielt" if ergebnis == FERTIG else "fehler"
        finally:
            tmp.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001 - jeder Fehler: keine Marke, der Kern spielt wie heute
        return "fehler"


def _programm_da(programm: str) -> bool:
    import shutil

    return shutil.which(programm) is not None


def _skaliert(datei: Path, pegel: int, konfig) -> Path:  # type: ignore[no-untyped-def]
    from .sounds import Kennlinie, skaliere_wav

    fd, name = tempfile.mkstemp(prefix="tobibox-fruehton-", suffix=".wav")
    os.close(fd)
    tmp = Path(name)
    try:
        skaliere_wav(datei, pegel, tmp, Kennlinie(konfig.toene.kennlinie, konfig.toene.softvol_bereich_db))
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return tmp


def _starte(kommando: list[str]) -> int:
    return subprocess.run(
        kommando, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=TON_MAX_S, check=False
    ).returncode


def main(argv: list[str] | None = None) -> int:
    """Einstiegspunkt ``python -m tobibox.fruehton --config <tobibox.toml>`` (Dienst ``tobibox-fruehton.service``). Gibt immer 0 zurück."""
    from . import config as konfig_modul

    p = argparse.ArgumentParser(prog="tobibox-fruehton", description="Früher Start-Ton der Tobi Box")
    p.add_argument("--config", help="tobibox.toml (sonst $TOBIBOX_CONFIG oder ./tobibox.toml)")
    p.add_argument("--marken", default=str(MARKEN_VERZEICHNIS), help="Verzeichnis der Marke (Vorgabe $TOBIBOX_MARKEN oder /run/tobibox)")
    a = p.parse_args(argv)
    try:
        konfig = konfig_modul.lade(Path(a.config or os.environ.get("TOBIBOX_CONFIG") or "tobibox.toml"))
    except Exception as e:  # noqa: BLE001 - kein Ton, keine Marke: der Kern spielt ``start``
        print(f"tobibox-fruehton: {e}", file=sys.stderr)
        return 0
    t0 = time.monotonic()
    ergebnis = spiele(konfig, marken_verzeichnis=a.marken)
    print(f"tobibox-fruehton: {ergebnis} nach {time.monotonic() - t0:.2f} s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
