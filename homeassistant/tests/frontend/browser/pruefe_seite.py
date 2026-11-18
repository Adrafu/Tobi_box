#!/usr/bin/env python3
"""Browserprüfung der neuen Seite (Paket A14-1a, Design Abschnitt 15).

Die Seite (tobibox-app.js und seiten/*.js) läuft in einem Shadow-Root, wie im HA-Panel, gegen den echten Mock
`../mock-hass.mjs` über einen kleinen lokalen Server (`server.mjs`, nur 127.0.0.1, kein Netz). Playwright (Python) fährt
Chrome/Chromium durch Seiten, Blätter und Abläufe und misst: Tippziele (44 px), waagerechtes Scrollen, Kontrast
(Text 4,5:1, Symbole und Ränder 3:1, Reiterleiste auch gegen die sechs Cover-Farben) und Konsolenfehler.

Aufruf (aus beliebigem Ordner):
    python3 homeassistant/tests/frontend/browser/pruefe_seite.py            # alles (etwa 5 Minuten, 4 Läufe parallel)
    python3 .../pruefe_seite.py --schnell                                   # nur hell, 390 und 1280 px, Admin und Benutzer
    python3 .../pruefe_seite.py --thema dunkel --breite 320 --rolle user    # Auswahl (mehrfach möglich)
    python3 .../pruefe_seite.py --bilder /tmp/bilder --json /tmp/befunde.json

Browser: Umgebungsvariable TOBIBOX_BROWSER (Pfad zu Chrome/Chromium); sonst /usr/bin/google-chrome, sonst das Chromium von
Playwright (`playwright install chromium`). Node 22 wird für den Server gebraucht (wie für die anderen Frontend-Tests).
Ende: Zusammenfassung; Exit-Code 0 ohne Befunde, 1 mit Befunden, 2 bei Fehlern im Aufbau (kein Browser, Server startet nicht).
Die Datei heißt absichtlich nicht test_*.py: pytest und `node --test` greifen sie nicht auf.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent
try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
except ImportError:  # wird in main() gemeldet
    PlaywrightTimeout = TimeoutError
UNBEKANNT = "0499887766554433"  # der unbekannte Tobie im Mock (neue_tobies beim Start)
LOEWE = "04A0000000000001"  # Tobie „Löwe“ auf der langen Serie (server.mjs)
LOEWE_FOLGE = "04A0000000000002"  # Tobie ohne Namen auf Folge 2 der langen Serie
THEMEN = ["hell", "dunkel", "gelb"]
# (Art, Breite): "fenster" = Browserfenster, "panel" = Panelbreite bei 1280 px Fensterbreite
# "ha": Fenster 1440 px mit der Seitenleiste von Home Assistant (256 px) links daneben, das Panel ist 1184 px breit (B2)
BREITEN = [("fenster", 320), ("fenster", 390), ("fenster", 1280), ("panel", 900), ("panel", 1024), ("panel", 1100), ("ha", 1440)]
ROLLEN = ["admin", "user"]
KATEGORIEN = ["konsole", "ablauf", "hscroll", "raus", "klein", "text", "symbole", "rand", "leiste", "extra"]
TECHNIK_SEITEN = [("technik", "#technik"), ("technik-boxen", "#technik-boxen"), ("technik-box", "#technik-box-kueche"), ("technik-speicher", "#technik-speicher"),
                  ("technik-liste", "#technik-liste"), ("technik-tobies", "#technik-tobies"), ("technik-meldungen", "#technik-meldungen"),
                  ("technik-einstellungen", "#technik-einstellungen")]


# ------------------------------------------------------------------ Hilfen im Lauf
class Lauf:
    """Ein Lauf = eine Browserseite mit einer Kombination aus Thema, Rolle und Breite. Sammelt Befunde."""

    def __init__(self, pg, job, bilder: Path | None):
        self.pg, self.job, self.bilder = pg, job, bilder
        self.befunde: list[tuple[str, str, str]] = []  # (Kategorie, Zustand, Text)
        self.hinweise: list[tuple[str, str]] = []  # (Zustand, Text) aus der alten Komponente
        self.zustaende = 0
        self.schritte = 0
        self._scroll_gesehen: set[str] = set()

    def befund(self, kat, zustand, text):
        self.befunde.append((kat, zustand, str(text)[:300]))

    def pruefe(self, bedingung, zustand, text):
        self.schritte += 1
        if not bedingung:
            self.befund("ablauf", zustand, text)
        return bool(bedingung)

    @contextlib.contextmanager
    def schritt(self, name):
        """Ein Ablauf: jeder Fehler (fehlendes Bedienelement, Zeitüberschreitung, verdeckter Knopf) wird ein Befund, der Lauf geht weiter."""
        try:
            yield
        except Exception as e:  # noqa: BLE001 - Playwright wirft viele Arten
            zeile = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            self.befund("ablauf", name, f"{type(e).__name__}: {zeile}")
            if self.bilder:  # Bildschirmfoto vom Zustand beim Fehler
                with contextlib.suppress(Exception):
                    self.bilder.mkdir(parents=True, exist_ok=True)
                    self.pg.screenshot(path=str(self.bilder / f"{self.job['kennung']}-fehler-{name}.png"))

    # --- Zugriff auf die Seite
    def js(self, ausdruck, arg=None):
        return self.pg.evaluate("([a, x]) => { const el = window.__el, sr = el.shadowRoot; return (new Function('el', 'sr', 'x', a))(el, sr, x); }", [ausdruck, arg])

    def ruhe(self):
        self.pg.evaluate("() => window.__ruhe()")
        self.scroll_pruefen()

    def scroll_pruefen(self):
        """Nach jedem Schritt und in jedem gemessenen Zustand: Hat irgendein Element außer den echten Scroll-Behältern (overflow auto/scroll,
        also `.rahmen`, die Inhaltsspalte, Blätter) ein `scrollTop` ungleich 0? Ein per Programm gescrollter Behälter mit `overflow: hidden`
        (Befund im echten HA: scrollIntoView am Namensfeld scrollte `.app`) schiebt die Reiterleiste in die Mitte. Sucht auch im Shadow-DOM,
        bei `el`, seinen Vorfahren und der Seite selbst. In der unteren Reiter-Anordnung muss die Unterkante der Leiste an der Unterkante des Panels liegen."""
        try:
            aus = self.js("""
              const alle = [];
              const gehe = (w) => { for (const n of w.querySelectorAll('*')) { alle.push(n); if (n.shadowRoot) gehe(n.shadowRoot); } };
              gehe(sr);
              for (let n = el; n; n = n.parentElement) alle.push(n);
              if (document.scrollingElement) alle.push(document.scrollingElement);
              const name = (n) => n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') + (typeof n.className === 'string' && n.className ? '.' + n.className.trim().split(/\\s+/).join('.') : '');
              const aus = [];
              for (const n of alle) {
                if (!n.scrollTop) continue;
                const ov = getComputedStyle(n).overflowY;
                if (ov === 'auto' || ov === 'scroll') continue;
                aus.push(`${name(n)} (overflow-y ${ov}) hat scrollTop ${Math.round(n.scrollTop)}, soll 0 sein`);
              }
              if (el.getAttribute('data-layout') === 'unten' && !sr.querySelector('.hinten.effekt-an')) { // hinter einem Blatt ist die Seite gewollt verkleinert (A6m)
                const nav = sr.querySelector('nav.tabs.unten');
                if (nav && getComputedStyle(nav).display !== 'none') {
                  const P = el.getBoundingClientRect(), b = nav.getBoundingClientRect().bottom;
                  if (Math.abs(b - P.bottom) > 1) aus.push(`Reiterleiste endet bei ${b.toFixed(1)}, das Panel bei ${P.bottom.toFixed(1)} (verschoben um ${(P.bottom - b).toFixed(1)} px)`);
                }
              }
              return aus;
            """)
        except Exception:  # noqa: BLE001 - Seite wechselt gerade
            return
        for text in aus:
            if text not in self._scroll_gesehen:
                self._scroll_gesehen.add(text)
                self.befund("extra", f"scroll@{self.hash()}", f"Scroll: {text}")

    def gehe(self, hash_):
        self.pg.evaluate("h => { location.hash = h; }", hash_)
        self.ruhe()

    def klick(self, sel, **kw):
        try:
            self.pg.locator(sel).first.click(timeout=4000, **kw)
        except PlaywrightTimeout as e:
            log = [z.strip(" -") for z in str(e).splitlines() if z.strip().startswith(("-", "waiting")) or "intercepts" in z]
            wichtig = [z for z in log if "intercepts" in z or "not visible" in z or "not enabled" in z or "waiting for" in z]
            raise RuntimeError(f"Klick auf {sel!r} nicht möglich: {(wichtig or log or ['Zeit abgelaufen'])[-1][:200]}") from None
        self.ruhe()

    def da(self, sel):
        return self.pg.locator(sel).count() > 0

    def hash(self):
        return self.pg.evaluate("() => location.hash")

    def mock(self, pfad, body=None):
        """Der Mock-Server dieses Laufs: `/legeauf` (Tobie auflegen), `/sperre`, `/zustand` (nur lesen)."""
        k = f"{self.job['profil']}~{self.job['kennung']}"
        return self.pg.evaluate("async ([p, k, b]) => (await (await fetch(`${p}?k=${encodeURIComponent(k)}`, { method: b ? 'POST' : 'GET', body: b ? JSON.stringify(b) : undefined })).json())", [pfad, k, body])

    def eingang_setzen(self, zustand):
        """A11b: Zustand des Eingangs im Mock setzen (`server.mjs`: leer, laeuft1, laeuft2, pruefen1, pruefen2, fehler, fertig) und warten, bis das Band
        der Seite ihn zeigt (die Seite holt `eingang/list` nach dem Ereignis neu)."""
        self.mock("/eingang", {"zustand": zustand})
        art = {"laeuft1": "laeuft", "laeuft2": "laeuft", "pruefen1": "pruefen", "pruefen2": "pruefen", "fehler": "fehler", "fertig": "fertig"}.get(zustand)
        if art:
            self.pg.locator(f'[data-eingang-band="{art}"]').first.wait_for(timeout=6000)
        else:
            self.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('[data-eingang-band]')", timeout=6000)
        self.ruhe()

    def warte_hash(self, teil, zeit=6000):
        self.pg.wait_for_function("t => location.hash.includes(t)", arg=teil, timeout=zeit)
        self.ruhe()

    def warte_da(self, sel, zeit=6000):
        self.pg.locator(sel).first.wait_for(timeout=zeit)
        self.ruhe()

    def toast(self):
        """Text der Erfolgsmeldung (oder '')."""
        return self.js("return sr.querySelector('.toast:not(.err) .tmsg')?.textContent ?? ''")

    def rahmen_geometrie(self):
        """Wie ha-panel-custom: das Element hat keine Höhe vom Behälter; die Leiste muss trotzdem am unteren Rand des Panels sitzen.
        Liefert Texte der Abweichungen (leer = in Ordnung). Panel = Rechteck des Elements (Fensterhöhe minus Rand des Behälters)."""
        return self.js("""
          if (sr.querySelector('.hinten.effekt-an')) return []; // hinter einem Blatt ist die Seite gewollt verkleinert (A6m)
          const e = (s) => sr.querySelector(s);
          const P = el.getBoundingClientRect();
          const ha = el.parentElement;
          const randU = ha ? parseFloat(getComputedStyle(ha).paddingBottom) || 0 : 0;
          const randO = ha ? parseFloat(getComputedStyle(ha).paddingTop) || 0 : 0;
          const aus = [];
          const nah = (a, b) => Math.abs(a - b) <= 1;
          const soll = innerHeight - randU;
          if (!nah(P.bottom, soll)) aus.push(`Panel endet bei ${P.bottom.toFixed(1)}, soll ${soll} (Fenster ${innerHeight}, Rand unten ${randU})`);
          if (!nah(P.height, innerHeight - randU - randO)) aus.push(`Panelhöhe ${P.height.toFixed(1)} statt ${innerHeight - randU - randO}`);
          const app = e('.app').getBoundingClientRect();
          if (!nah(app.bottom, P.bottom) || !nah(app.top, P.top)) aus.push(`.app ${app.top.toFixed(1)}..${app.bottom.toFixed(1)} füllt das Panel ${P.top.toFixed(1)}..${P.bottom.toFixed(1)} nicht`);
          const lay = el.getAttribute('data-layout');
          const nav = e('nav.tabs.unten');
          const mini = e('.mini');
          const miniDa = mini && !mini.hidden && getComputedStyle(mini).display !== 'none';
          if (lay === 'unten') {
            if (!nav) aus.push('keine untere Leiste');
            else if (getComputedStyle(nav).display !== 'none') {
              const n = nav.getBoundingClientRect();
              if (!nah(n.bottom, P.bottom)) aus.push(`Leiste endet bei ${n.bottom.toFixed(1)}, Panel bei ${P.bottom.toFixed(1)} (leere Fläche ${(P.bottom - n.bottom).toFixed(1)} px)`);
              if (miniDa) { const m = mini.getBoundingClientRect(); if (!nah(m.bottom, n.top)) aus.push(`Mini-Player endet bei ${m.bottom.toFixed(1)}, Leiste beginnt bei ${n.top.toFixed(1)}`); }
              const r = e('.rahmen').getBoundingClientRect();
              const darueber = miniDa ? mini.getBoundingClientRect().top : n.top;
              if (!nah(r.bottom, darueber)) aus.push(`Scrollbereich endet bei ${r.bottom.toFixed(1)}, darunter beginnt ${darueber.toFixed(1)}`);
            }
          } else {
            const r = e('.rahmen').getBoundingClientRect();
            const unter = miniDa && lay !== 'seite' ? mini.getBoundingClientRect() : null;
            if (!nah(unter ? unter.bottom : r.bottom, P.bottom)) aus.push(`Layout ${lay}: Inhalt endet bei ${(unter ? unter.bottom : r.bottom).toFixed(1)}, Panel bei ${P.bottom.toFixed(1)}`);
          }
          return aus;
        """)

    def messe(self, name, bild=True):
        self.ruhe()
        self.pg.evaluate("() => window.__ruhe(4000, true)")  # A6m: laufende Bewegung abwarten, bevor gemessen wird (halb verkleinerte Knöpfe, einblendende Meldungen)
        r = self.pg.evaluate("() => window.__mess()")
        self.zustaende += 1
        for t in self.rahmen_geometrie():
            self.befund("extra", name, f"Geometrie: {t}")
        for kat in ("hscroll", "raus", "klein", "text", "symbole", "rand", "leiste", "extra"):
            for t in r[kat]:
                self.befund(kat, name, t)
        for t in r["alt"]:
            self.hinweise.append((name, t))
        if bild and self.bilder:
            self.bilder.mkdir(parents=True, exist_ok=True)
            self.pg.screenshot(path=str(self.bilder / f"{self.job['kennung']}-{name}.png"))
        return r

    def aufraeumen(self):
        """Meldungen und Blätter eines früheren Ablaufs wegräumen (eine Fehlermeldung bleibt bis „OK“ und verdeckt sonst Knöpfe)."""
        self.js("el.schliesseBlatt('code'); sr.querySelectorAll('.toast').forEach((t) => t.remove());")
        self.ruhe()

    def blatt_zu(self):
        """Offenes Blatt über das ×; nicht vorhanden ist kein Fehler."""
        if self.da("dialog[open] .blatt-x"):
            self.pg.locator("dialog[open] .blatt-x").first.click(timeout=5000)
            self.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=3000)
            self.ruhe()


# ------------------------------------------------------------------ A11a: Hinzufügen
def hz_dateien(tmp: Path, namen, groesse=2000):
    """Kleine Testdateien (Audio-ähnlich: der Mock-Server prüft nur Namen und Endung)."""
    pfade = []
    for n in namen:
        p = tmp / n
        p.write_bytes(b"ID3" + bytes(groesse))
        pfade.append(str(p))
    return pfade


def hz_modell_waehlen(L: Lauf, namen):
    """Nur zum Messen: Dateien an das Modell geben, als hätte der Dateiwähler sie geliefert (die echten Klicks macht ablauf_hinzufuegen)."""
    L.pg.evaluate(
        """async (namen) => {
          const H = await import('/f/seiten/hinzufuegen.js');
          H.modell(window.__el.ctx).auswahl(namen.map((n) => new File([new Uint8Array(1500)], n)));
        }""", namen)
    L.pg.wait_for_selector("dialog[open] [data-kacheln]", timeout=5000)
    L.ruhe()


def hinzufuegen_blatt_messen(L: Lauf, leer=False):
    """Messung von Blatt und Vorschau (Kacheln, a, b, c, e, Wohin) und, mit gemessenem Hochladen, der Karten unter „Zuletzt hinzugefügt“."""
    namen = ["01 Der Hafen.mp3", "02 Die Karte.mp3", "03 Der Sturm.mp3"]
    with L.schritt("hinzufuegen-kacheln"):
        L.gehe("#hinzufuegen")
        hz_modell_waehlen(L, namen)
        L.messe("hinzufuegen-kacheln")
        for ziel in ("neu", "einzeln", "auto"):
            L.klick(f'dialog[open] [data-ziel="{ziel}"]')
            L.messe(f"hinzufuegen-vorschau-{ziel}")
            L.klick('dialog[open] .knoepfe button:has-text("Ändern")')
        if not leer:
            L.klick('dialog[open] [data-ziel="ergaenzen"]')
            L.warte_da("dialog[open] [data-hz-wahl] [data-wahl]")
            L.messe("hinzufuegen-wohin")
            L.klick("dialog[open] [data-hz-wahl] [data-wahl]")
            L.messe("hinzufuegen-vorschau-ergaenzen")
        L.aufraeumen()
    with L.schritt("hinzufuegen-viele"):  # acht Dateien: vier Zeilen und „… und 4 weitere“, Name mit Umlauten
        L.gehe("#hinzufuegen")
        hz_modell_waehlen(L, [f"{i:02d} Die lange Folge mit einem sehr langen Namen Nummer {i}.mp3" for i in range(1, 9)])
        L.klick('dialog[open] [data-ziel="neu"]')
        L.messe("hinzufuegen-vorschau-viele")
        L.aufraeumen()


def hz_zeilen(L: Lauf, sel):
    """Anzahl der Textzeilen eines Elements (Höhe durch Zeilenhöhe)."""
    return L.js("const e = sr.querySelector(x); if (!e) return -1; const lh = parseFloat(getComputedStyle(e).lineHeight) || parseFloat(getComputedStyle(e).fontSize) * 1.3; return Math.round(e.getBoundingClientRect().height / lh);", sel)


def hz_waehlen(L: Lauf, knopf, pfade):
    """Dateiwahl mit echtem Klick; der Dateiwähler des Browsers bekommt die Testdateien."""
    with L.pg.expect_file_chooser(timeout=5000) as fc:
        L.pg.locator(knopf).first.click(timeout=4000)
    fc.value.set_files(pfade)
    L.pg.wait_for_timeout(250)
    L.ruhe()


def ablauf_hinzufuegen(L: Lauf):
    """A11a (zugleich Teil von A14-1c): Hinzufügen nur über echte Klicks. Seite → „Dateien wählen“ (Dateiwähler, 3 Dateien) → Blatt „Was lädst du hoch?“
    (vier Kacheln mit höchstens einer Zeile, „Abbrechen“ oben rechts) → „Neu anlegen“ → Name und Art → „Ändern“ und zurück → „Hochladen“ → Fortschritt
    („Datei 2 von 3“, „Bildschirm anlassen …“) → „Wird einsortiert …“ → fertig mit „Öffnen“. Dazu die Fehler (falsches Format, zu groß vorab, 413, kein
    Speicher; die Karte bleibt), die Fehlermeldung „Bitte einen Namen eingeben.“ (bleibt, bis „OK“), das „+“ der Bibliothek (am Handy gleich die
    Dateiauswahl) und „Dateien in diesen Eintrag“. Gemessen werden Seite, Blatt, Vorschau und die Karten (Tippziele, Kontrast, kein seitliches Scrollen)."""
    import tempfile

    fein = bool(L.js("return matchMedia('(pointer: fine)').matches"))
    with tempfile.TemporaryDirectory(prefix="tb-hz-") as tmp:
        tmp = Path(tmp)
        drei = hz_dateien(tmp, ["01 Der Hafen.mp3", "02 Die Karte.mp3", "03 Der Sturm.mp3"])
        with L.schritt("hz-seite"):
            L.gehe("#hinzufuegen")
            L.pruefe(L.da("[data-dateien-waehlen]"), "hz-seite", "„Dateien wählen“ fehlt")
            L.pruefe(L.da("[data-ordner-waehlen]") == fein, "hz-seite", f"„Ordner vom Computer wählen“ nur bei pointer: fine (fein={fein})")
            L.pruefe(L.da("[data-ziehflaeche]") == fein, "hz-seite", f"Ziehfläche nur bei pointer: fine (fein={fein})")
            L.pruefe(L.js("return sr.querySelector('main .back')?.textContent.trim()") == "‹ Bibliothek", "hz-seite", "„‹ Bibliothek“ fehlt")
            L.pruefe(not L.da("[data-liste='zuletzt']"), "hz-seite", "Liste „Zuletzt hinzugefügt“ ohne Eintrag")
            L.messe("hz-seite")
        with L.schritt("hz-blatt"):
            hz_waehlen(L, "[data-dateien-waehlen]", drei)
            L.pruefe(L.da("dialog[open] [data-kacheln]"), "hz-blatt", "Blatt „Was lädst du hoch?“ nicht offen")
            L.pruefe(L.js("return sr.querySelector('dialog[open] [data-gewaehlt]')?.textContent.trim()") == "3 Dateien gewählt (01 Der Hafen.mp3 …). Was ist das?", "hz-blatt", "Zeile mit den Dateien stimmt nicht")
            L.pruefe(L.js("return sr.activeElement?.id") == "blatt-t", "hz-blatt", "Fokus nicht auf der Überschrift")
            kacheln = L.js("""return [...sr.querySelectorAll('dialog[open] .hz-kachel')].map((k) => {
              const zeilen = (e) => { const cs = getComputedStyle(e); const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.3; return Math.round(e.getBoundingClientRect().height / lh); };
              const r = k.getBoundingClientRect();
              return { titel: k.querySelector('.hz-t').textContent, titelZeilen: zeilen(k.querySelector('.hz-t')), zeilen: zeilen(k.querySelector('.hz-z')), zeile: k.querySelector('.hz-z').textContent, hoehe: r.height, breite: r.width, links: r.left, oben: r.top };
            })""")
            L.pruefe(len(kacheln) == 4, "hz-blatt", f"{len(kacheln)} Kacheln statt 4")
            for k in kacheln:
                L.pruefe(k["zeilen"] == 1, "hz-blatt", f"Kachel „{k['titel']}“: Zeile „{k['zeile']}“ braucht {k['zeilen']} Zeilen (Breite {k['breite']:.0f} px)")
                L.pruefe(k["titelZeilen"] == 1, "hz-blatt", f"Kachel „{k['titel']}“: Titel braucht {k['titelZeilen']} Zeilen")
                L.pruefe(k["hoehe"] >= 131.5, "hz-blatt", f"Kachel „{k['titel']}“ nur {k['hoehe']:.0f} px hoch")
            L.pruefe(len({round(k["oben"]) for k in kacheln}) == 2 and len({round(k["links"]) for k in kacheln}) == 2, "hz-blatt", "Kacheln stehen nicht 2 × 2")
            oben = L.js("""const d = sr.querySelector('dialog[open]').getBoundingClientRect(); const b = sr.querySelector('dialog[open] [data-blatt-oben]'); if (!b) return null;
              const r = b.getBoundingClientRect(); return { text: b.textContent.trim(), rechts: d.right - r.right, oben: r.top - d.top, hoehe: r.height, breite: r.width, x: !!sr.querySelector('dialog[open] .blatt-x') };""")
            L.pruefe(oben and oben["text"] == "Abbrechen" and not oben["x"], "hz-blatt", f"„Abbrechen“ fehlt oder „×“ ist da: {oben}")
            L.pruefe(oben and oben["rechts"] <= 24 and oben["oben"] <= 56 and oben["hoehe"] >= 43.5, "hz-blatt", f"„Abbrechen“ nicht oben rechts im Blatt, 44 px hoch: {oben}")
            L.messe("hz-blatt")
        with L.schritt("hz-vorschau"):
            L.klick('dialog[open] [data-ziel="neu"]')
            L.pruefe(L.js("return sr.activeElement?.id") == "blatt-t", "hz-vorschau", "Fokus nicht auf der Überschrift (sonst geht am Handy die Tastatur auf)")
            L.pg.locator("dialog[open] #hz-name").fill("Kapitän Knopf")
            L.klick('dialog[open] [data-art-wahl="hoerbuch"]')
            satz = L.js("return sr.querySelector('dialog[open] [data-satz]')?.textContent")
            L.pruefe(satz == "3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.", "hz-vorschau", f"Satz stimmt nicht: {satz!r}")
            L.pruefe(L.js("const s = sr.querySelector('dialog[open] [data-satz]'); return s.getAttribute('role') + '/' + s.getAttribute('aria-live')") == "status/polite", "hz-vorschau", "Satz ohne role=status und aria-live=polite")
            L.messe("hz-vorschau")
            L.klick('dialog[open] .knoepfe button:has-text("Ändern")')
            L.pruefe(L.da("dialog[open] [data-kacheln]"), "hz-aendern", "„Ändern“ führt nicht zu den Kacheln")
            L.klick('dialog[open] [data-ziel="neu"]')
            L.pruefe(L.pg.locator("dialog[open] #hz-name").input_value() == "Kapitän Knopf", "hz-aendern", "Name ging beim Ändern verloren")
        with L.schritt("hz-hochladen"):
            L.klick("dialog[open] .knoepfe button.primary")
            L.pruefe(L.hash() == "#hinzufuegen", "hz-hochladen", f"nach „Hochladen“ nicht auf der Seite „Hinzufügen“: {L.hash()}")
            L.warte_da("[data-liste='zuletzt'] [data-phase='hochladen'] [data-bildschirm]")
            L.pruefe(L.js("return sr.querySelector('[data-bildschirm]').textContent.trim()") == "Bildschirm anlassen, bis es fertig ist.", "hz-hochladen", "Satz „Bildschirm anlassen …“ fehlt während des Hochladens")
            status = L.js("return sr.querySelector('[data-liste=\"zuletzt\"] [data-status]')?.textContent.trim()")
            L.pruefe(bool(re.match(r"^Datei [123] von 3 wird hochgeladen … \d+ %$", status or "")), "hz-hochladen", f"Fortschrittssatz stimmt nicht: {status!r}")
            L.pruefe(L.da("[data-liste='zuletzt'] [role=progressbar][aria-valuenow]") and L.da("[data-schritte] li"), "hz-hochladen", "Balken oder dreiteilige Leiste fehlt")
            L.messe("hz-hochladen")
            L.pg.wait_for_selector("[data-liste='zuletzt'] [data-phase='fertig']", timeout=25000)
            L.ruhe()
            karte = L.js("const k = sr.querySelector('[data-liste=\"zuletzt\"] [data-phase=\"fertig\"]'); return { text: k.textContent.replace(/\\s+/g, ' ').trim(), href: k.querySelector('[data-oeffnen]')?.getAttribute('href'), fokus: sr.activeElement === k, bildschirm: !!k.querySelector('[data-bildschirm]') };")
            L.pruefe("fertig" in karte["text"] and "Hörbuch „Kapitän Knopf“ · 3 Kapitel" in karte["text"], "hz-fertig", f"Fertig-Karte: {karte['text']!r}")
            L.pruefe(bool(karte["href"] and karte["href"].startswith("#serie-")), "hz-fertig", f"„Öffnen“ ohne Ziel: {karte['href']!r}")
            L.pruefe(not karte["bildschirm"], "hz-fertig", "„Bildschirm anlassen“ steht nach dem Hochladen noch da")
            L.messe("hz-fertig")
            ups = L.mock("/zustand")["uploads"]
            L.pruefe(len(ups) == 3 and len({u["gruppe"] for u in ups}) == 1 and all(u["gruppe_anzahl"] == 3 and u["ziel"] == "neu" and u["art"] == "hoerbuch" and u["name"] == "Kapitän Knopf" for u in ups),
                     "hz-hochladen", f"Felder beim Server: {ups}")
            L.klick("[data-liste='zuletzt'] [data-oeffnen]")
            L.warte_hash("#serie-")
            L.pruefe(L.da("main .back"), "hz-fertig", "„Öffnen“ führt nicht zur Serienseite")
            L.gehe("#hinzufuegen")
        with L.schritt("hz-einzeln-viele"):  # drei Einzeltitel: ein Upload je Datei, alle fertig
            L.aufraeumen()
            hz_waehlen(L, "[data-dateien-waehlen]", hz_dateien(tmp, ["Der Mond.mp3", "Der Fuchs.mp3"]))
            L.klick('dialog[open] [data-ziel="einzeln"]')
            L.messe("hz-vorschau-einzeln")
            L.klick("dialog[open] .knoepfe button.primary")
            L.pg.wait_for_function("() => window.__el.shadowRoot.querySelectorAll('[data-liste=\"zuletzt\"] [data-phase=\"fertig\"]').length >= 2", timeout=25000)
            L.ruhe()
            ups = L.mock("/zustand")["uploads"][3:]
            L.pruefe(len(ups) == 2 and all(u.get("ziel") == "einzeln" and not u.get("gruppe") and u.get("art") == "musik" for u in ups), "hz-einzeln", f"Einzeln ohne Gruppe: {ups}")
        with L.schritt("hz-fehler-format"):
            L.aufraeumen()
            hz_waehlen(L, "[data-dateien-waehlen]", hz_dateien(tmp, ["Mein Lied.wma"]))
            L.pruefe(not L.da("dialog[open]"), "hz-fehler", "Blatt trotz Datei, die nicht geht")
            L.warte_da("[data-liste='zuletzt'] [data-phase='fehler']")
            L.pruefe("Dieses Dateiformat spielt die Box nicht. Erlaubt sind MP3, M4A, M4B, AAC, FLAC, OGG, Opus und WAV." in L.js("return sr.querySelector('[data-liste=\"zuletzt\"] [data-phase=\"fehler\"]').textContent"), "hz-fehler", "Text zum Format fehlt")
            L.messe("hz-fehler-format")
            L.pg.wait_for_timeout(1500)
            L.pruefe(L.da("[data-liste='zuletzt'] [data-phase='fehler']"), "hz-fehler", "Fehlerkarte verschwindet von selbst")
        with L.schritt("hz-fehler-gross-vorab"):
            L.js("el.store.s.grenzen = { ...el.store.s.grenzen, upload_max_bytes: 1048576 };")
            gross = tmp / "Gross.mp3"
            gross.write_bytes(bytes(1572864))
            hz_waehlen(L, "[data-dateien-waehlen]", [str(gross)])
            L.pruefe(not L.da("dialog[open]"), "hz-fehler", "Blatt trotz zu großer Datei")
            L.pg.wait_for_function("() => window.__el.shadowRoot.querySelector('[data-liste=\"zuletzt\"]').textContent.includes('mehr als 1 MB')", timeout=5000)
            L.js("el.store.s.grenzen = { ...el.store.s.grenzen, upload_max_bytes: 524288000 };")
            L.messe("hz-fehler-gross-vorab")
        with L.schritt("hz-fehler-server"):  # 413 und 507 kommen vom Server (Marken im Dateinamen)
            for name, text in (("zu-gross.mp3", "Die Datei ist zu groß (mehr als 500 MB)."), ("kein-platz.mp3", "Auf dem NAS ist kein Platz mehr.")):
                vorher = L.js("return sr.querySelectorAll('[data-liste=\"zuletzt\"] [data-phase=\"fehler\"]').length")
                hz_waehlen(L, "[data-dateien-waehlen]", hz_dateien(tmp, [name]))
                L.klick('dialog[open] [data-ziel="einzeln"]')
                L.klick("dialog[open] .knoepfe button.primary")
                L.pg.wait_for_function("n => window.__el.shadowRoot.querySelectorAll('[data-liste=\"zuletzt\"] [data-phase=\"fehler\"]').length > n", arg=vorher, timeout=15000)
                L.ruhe()
                L.pruefe(text in L.js("return sr.querySelector('[data-liste=\"zuletzt\"] [data-phase=\"fehler\"]').textContent"), "hz-fehler", f"{name}: Text {text!r} fehlt")
            L.messe("hz-fehler-server")
            L.aufraeumen()
        with L.schritt("hz-meldung-name"):
            hz_waehlen(L, "[data-dateien-waehlen]", drei)
            L.klick('dialog[open] [data-ziel="neu"]')
            L.pg.locator("dialog[open] #hz-name").fill("")
            L.klick("dialog[open] .knoepfe button.primary")
            L.pruefe(L.js("return sr.querySelector('dialog[open] .toast.err .tmsg')?.textContent") == "Bitte einen Namen eingeben.", "hz-meldung", "Meldung „Bitte einen Namen eingeben.“ fehlt oder steht nicht im Blatt")
            L.pruefe(L.da("dialog[open]"), "hz-meldung", "Blatt schließt trotz fehlendem Namen")
            L.messe("hz-meldung-name")
            L.pg.wait_for_timeout(5200)
            L.pruefe(L.da("dialog[open] .toast.err"), "hz-meldung", "Fehlermeldung verschwindet von selbst (soll bis „OK“ bleiben)")
            L.klick("dialog[open] .toast.err .tok")
            L.pg.wait_for_timeout(450)  # A6m: die Meldung gleitet erst hinaus (--dauer-mittel), dann wird sie entfernt
            L.pruefe(not L.da(".toast.err"), "hz-meldung", "„OK“ räumt die Meldung nicht weg")
            L.klick("dialog[open] [data-blatt-oben]")
            L.pruefe(not L.da("dialog[open]"), "hz-meldung", "„Abbrechen“ schließt das Blatt nicht")
            L.pruefe(L.js("return sr.activeElement?.matches('[data-dateien-waehlen]')"), "hz-meldung", "Fokus nach „Abbrechen“ nicht auf „Dateien wählen“")
        with L.schritt("hz-plus"):
            L.gehe("#bibliothek")
            plus = "a.kact.primaer"
            if fein:
                L.klick(plus)
                L.warte_hash("#hinzufuegen")
            else:  # am Handy öffnet „+“ gleich die Dateiauswahl, die Seite bleibt die Bibliothek
                hz_waehlen(L, plus, drei)
                L.pruefe(L.hash() == "#bibliothek", "hz-plus", f"„+“ am Handy wechselt die Seite: {L.hash()}")
                L.pruefe(L.da("dialog[open] [data-kacheln]"), "hz-plus", "Blatt nach der Dateiwahl am Handy nicht offen")
                L.klick("dialog[open] [data-blatt-oben]")
        with L.schritt("hz-aus-eintrag"):
            L.aufraeumen()
            L.gehe("#serie-lang")
            L.klick("[data-menue-serie]")
            L.pruefe(L.da('dialog [data-menue="dateien"]'), "hz-aus-eintrag", "Menüpunkt „Dateien in diesen Eintrag“ fehlt")
            hz_waehlen(L, 'dialog [data-menue="dateien"]', drei)
            satz = L.js("return sr.querySelector('dialog[open] [data-satz]')?.textContent")
            L.pruefe(bool(satz and "neue Folgen in „Die wilde Reise der kleinen Drachen durch das Wolkenland“ (Folge 46–48)" in satz), "hz-aus-eintrag", f"Vorschau b) nicht gleich offen: {satz!r}")
            L.messe("hz-aus-eintrag")
            L.klick("dialog[open] [data-blatt-oben]")


# ------------------------------------------------------------------ Messen: alle Seiten und Blätter
def gh_zuruecksetzen(L: Lauf):
    """Stufe B: „Gehört“ auf Auswahl „Alle“, Zeitraum „Woche“, Aufteilung zu und die Daten frisch (die Seite behält ihren Zustand beim Hin- und Herwechseln)."""
    L.js("""const o = el._seiten.gehoert; if (!o) return;
      o.e = { wer: 'alle', zeitraum: 'woche', serie: null }; o.auf = null; o.alleRang = false; o.laden(true);""")
    L.ruhe()
    L.pg.wait_for_function("() => { const s = window.__el.shadowRoot; return !!s.querySelector('[data-gehoert], [data-leer=\"gehoert\"], .note.err'); }", timeout=6000)
    L.ruhe()


def seiten_messen(L: Lauf):
    admin = L.job["rolle"] == "admin"
    profil = L.job["profil"]
    leer = profil == "leer"

    def seite(name, hash_, vorher=None):
        with L.schritt(name):
            L.gehe(hash_)
            if vorher:
                vorher()
            L.messe(name)

    seite("start", "#start")
    seite("bibliothek", "#bibliothek")
    seite("tobies", "#tobies")
    seite("suche", "#suche")
    if not leer:
        def tippe(text):
            def f():
                L.pg.locator("input.suchfeld").fill(text)
                L.pg.wait_for_selector(".sugrow, [data-gruppe]" if text == "wilde" else '[data-leer="suche"]', timeout=5000)
            return f
        seite("suche-treffer", "#suche", tippe("wilde"))
        seite("suche-keiner", "#suche", tippe("xyzq"))
        for sid in ["lang", "pruef", "lied", "buch", "leersammlung"]:
            seite(f"serie-{sid}", f"#serie-{sid}")
        with L.schritt("serie-lang-unten"):
            L.gehe("#serie-lang")
            L.js("sr.querySelector('.rahmen').scrollTop = 900; sr.querySelector('.spalte').scrollTop = 900;")
            L.messe("serie-lang-unten")
    # A9/A10: Seiten der Tobies (Regal, Tobie, Neuer Tobie mit beiden Wegen, festes Ziel, „Einem Tobie geben …“)
    seite("neu", "#neu")
    seite("neu-warten", "#neu-warten")
    seite("neu-queue", "#neu-queue")
    seite("neu-ziel", f"#neu-ziel-{UNBEKANNT}")
    seite("neu-ziel-weg", "#neu-ziel-GIBTSNICHT")
    seite("tobie-weg", "#tobie-GIBTSNICHT")
    if not leer:
        def tippe_regal(text):
            def f():
                L.pg.locator("#tb-suche").fill(text)
                L.ruhe()
            return f
        seite("tobies-suche", "#tobies", tippe_regal("löwe"))
        seite("tobies-suche-keiner", "#tobies", tippe_regal("xyzq"))
        seite("tobie", f"#tobie-{LOEWE}")
        seite("tobie-folge", f"#tobie-{LOEWE_FOLGE}")
        seite("tobie-folgenwahl", f"#tobie-{LOEWE}", lambda: L.klick('[data-zielwahl] [data-wert="folge"]'))
        seite("neu-fest", "#neu?s=kurz&f=k2.mp3")
        seite("neu-queue-fest", "#neu-queue?s=kurz")
        seite("neu-ziel-fest", f"#neu-ziel-{UNBEKANNT}?s=kurz&von=tobies")
        seite("geben-serie", "#geben-kurz")
        seite("geben-folge", "#geben-kurz~k2.mp3")
        seite("geben-lied", "#geben-lied~wiegenlied.mp3")
        seite("geben-weg", "#geben-gibtsnicht")
    seite("hinzufuegen", "#hinzufuegen")
    hinzufuegen_blatt_messen(L, leer)
    seite("geraete", "#geraete")
    # Stufe B (B4): Unterseite „Gehört“ in allen Zuständen; bei einer älteren HA (Profil „alt“) gibt es sie nicht (Umleitung auf „Geräte“)
    def gh(name, vorher=None):
        def f():
            gh_zuruecksetzen(L)
            if vorher:
                vorher()
        seite(name, "#gehoert", f)
    if profil == "alt":
        with L.schritt("alt-ohne-stufe-b"):
            L.gehe("#gehoert")
            L.pruefe(L.hash() == "#geraete", "alt-ohne-stufe-b", f"#gehoert führt bei älterer HA nach {L.hash()} statt #geraete")
            L.pruefe(not L.da("[data-gehoert-link]"), "alt-ohne-stufe-b", "Zeile „Wer hat was gehört?“ ohne Fähigkeit gehoert")
            L.gehe("#start")
            L.pruefe(not L.da('[data-reihe="favoriten"], [data-reihe="zuletzt_gehoert"]'), "alt-ohne-stufe-b", "Reihen der Stufe B ohne Fähigkeit")
            L.gehe("#serie-lang")
            L.pruefe(not L.da("[data-stern]") and not L.da("[data-favorit]"), "alt-ohne-stufe-b", "Stern ohne Fähigkeit favoriten")
            L.gehe("#bibliothek")
            L.klick("[data-sortieren]")
            L.pruefe(L.js("return sr.querySelector('dialog [role=radiogroup]').querySelectorAll('.optrow').length") == 3, "alt-ohne-stufe-b", "Sortierungen der Stufe B ohne Fähigkeit")
            L.pruefe(L.js("return !/Favoriten/.test(sr.querySelector('dialog').textContent)"), "alt-ohne-stufe-b", "Filter „Favoriten“ ohne Fähigkeit")
            L.blatt_zu()
            if admin:
                L.gehe("#technik-box-kueche")
                L.pruefe(not L.da('[data-karte="verlauf"]'), "alt-ohne-stufe-b", "Karte „Verlauf“ ohne Fähigkeit")
                L.gehe("#technik-speicher")
                L.pruefe(not L.da('[data-karte="hoerdaten"]'), "alt-ohne-stufe-b", "Karte „Hördaten“ ohne Fähigkeit")
    else:
        gh("gehoert")
    if not leer and profil != "alt":
        gh("gehoert-person", lambda: L.klick('[data-wer-knopf^="benutzer:"]'))
        gh("gehoert-alle-boxen", lambda: L.klick('[data-wer-knopf="alle_boxen"]'))
        gh("gehoert-monat", lambda: L.klick('[data-zeitraum] [data-wert="monat"]'))
        gh("gehoert-jahr", lambda: L.klick('[data-zeitraum] [data-wert="jahr"]'))
        gh("gehoert-alles", lambda: L.klick('[data-zeitraum] [data-wert="alles"]'))
        gh("gehoert-alle-zeilen", lambda: L.klick("[data-rang-mehr]") if L.da("[data-rang-mehr]") else None)
        gh("gehoert-aufteilung", lambda: L.klick('[data-serie-zeile="lang"]'))
        def tabellen():
            L.js("sr.querySelectorAll('[data-gehoert] details').forEach((d) => { d.open = true; })")
            L.ruhe()
        gh("gehoert-tabellen", tabellen)
    with L.schritt("geraete-abends"):
        L.gehe("#geraete")
        L.js("sr.querySelector('h2.abends')?.scrollIntoView()")
        L.messe("geraete-abends")
    if admin and profil != "alt":
        seite("technik-box-30", "#technik-box-kueche", lambda: L.klick('[data-karte="verlauf"] [data-wert="30"]'))
        seite("technik-box-tabelle", "#technik-box-kueche", lambda: (L.js("sr.querySelectorAll('[data-karte=\"verlauf\"] details').forEach((d) => { d.open = true; })"), L.ruhe()))
        seite("technik-box-ohne-akku", "#technik-box-kinderzimmer")
        seite("technik-speicher-loeschen", "#technik-speicher", lambda: L.js("sr.querySelector('[data-karte=\"hoerdaten\"]')?.scrollIntoView()"))
    seite("box", "#box-kueche")
    seite("box-offline", "#box-kinderzimmer")
    seite("box-fehlt", "#box-gibtsnicht")

    # --- Blätter
    def blatt(name, hash_, schritte, nach=None):
        with L.schritt(name):
            L.gehe(hash_)
            for s in schritte:
                L.klick(s)
            L.messe(name)
            if nach:
                nach()
        with L.schritt(name + "-zu"):
            L.js("el.schliesseBlatt('code')")
            L.ruhe()
            L.js("sr.querySelector('dialog[open]')?.removeAttribute('open')")

    blatt_sort = ["[data-sortieren]"]
    if not leer:
        blatt("blatt-sortieren", "#bibliothek", blatt_sort)
        blatt("blatt-serie-menue", "#serie-lang", ["[data-menue-serie]"])
        blatt("blatt-folgenmenue", "#serie-lang", ['[data-folge="f02.mp3"] [data-menue-folge]'])
        blatt("blatt-cover", "#serie-lang", ["[data-menue-serie]", '[data-menue="cover"]'])
        if admin:
            blatt("blatt-name", "#serie-lang", ["[data-menue-serie]", '[data-menue="name"]'])
            blatt("blatt-art", "#serie-lang", ["[data-menue-serie]", '[data-menue="art"]'])
            blatt("blatt-papierkorb", "#serie-lang", ["[data-menue-serie]", '[data-menue="papierkorb"]'])
            blatt("blatt-zusammen", "#serie-lang", ["[data-menue-serie]", '[data-menue="zusammen"]'])
            blatt("blatt-verschieben", "#serie-lang", ['[data-folge="f02.mp3"] [data-menue-folge]', '[data-menue="verschieben"]'])
            blatt("blatt-verschieben-frage", "#serie-lang", ['[data-folge="f02.mp3"] [data-menue-folge]', '[data-menue="verschieben"]', "dialog[open] [data-wahl]"])
            with L.schritt("reihenfolge"):
                L.gehe("#serie-kurz")
                L.klick("[data-menue-serie]")
                L.klick('[data-menue="reihenfolge"]')
                L.messe("reihenfolge")
                L.klick("[data-fertig]")
        else:
            blatt("blatt-stimmt-nicht", "#serie-pruef", ["[data-stimmt-nicht]"])
    if profil == "warn":  # Liste „Export neuer“: Leise-Zeiten sind gesperrt, bis die Liste geklärt ist
        with L.schritt("leise-gesperrt"):
            L.gehe("#geraete")
            L.pruefe(L.js("return sr.querySelector('[data-leise-neu]')?.disabled === true"), "leise-gesperrt", "„Neue Leise-Zeit“ bleibt bei gesperrter Liste bedienbar")
    elif not leer:
        blatt("blatt-leise-neu", "#geraete", ["[data-leise-neu]"])
        blatt("blatt-leise-leiser", "#geraete", ["[data-leise-neu]", "dialog .seg2 button:last-child"])
        blatt("blatt-leise-aendern", "#geraete", ["button.hit[data-fenster=nacht]"])
        blatt("blatt-leise-loeschen", "#geraete", ["button.hit[data-fenster=nacht]", "[data-loeschen]"])

    # --- A11b: Band in der Bibliothek (alle Zustände) und gelbe Karte auf der Serienseite
    if not leer:
        for zustand in ("laeuft1", "laeuft2", "pruefen1", "pruefen2", "fehler", "fertig"):
            with L.schritt(f"band-{zustand}"):
                L.gehe("#bibliothek")
                L.eingang_setzen(zustand)
                L.messe(f"band-{zustand}")
                if zustand == "laeuft2":  # der ruhige Punkt am Reiter „Bibliothek“ steht auch auf anderen Seiten
                    L.gehe("#geraete")
                    L.pruefe(L.da("nav.tabs a[href='#bibliothek'] .dot.ruhig") or L.da("aside nav.tabs a[href='#bibliothek'] .dot.ruhig"), "band-punkt", "Punkt am Reiter „Bibliothek“ fehlt")
                    L.messe("band-laeuft2-geraete")
        with L.schritt("serie-karte-daraus"):
            L.eingang_setzen("pruefen1")
            L.gehe("#serie-pruef")
            L.pg.locator("[data-daraus]").first.wait_for(timeout=6000)
            L.messe("serie-pruef-daraus")
        with L.schritt("band-weg"):
            L.eingang_setzen("leer")

    # --- Technik
    if admin:
        for name, h in TECHNIK_SEITEN:
            seite(name, h)
        blatt("blatt-technik-cover", "#technik-speicher", ["[data-aktion=cover]"])
        blatt("blatt-technik-stand", "#technik-liste", ['[data-stand="1"]'])
    else:
        seite("technik-sperre", "#technik")
        seite("technik-sperre-unter", "#technik-speicher")


# ------------------------------------------------------------------ Abläufe
def ablauf_reiter(L: Lauf):
    admin = L.job["rolle"] == "admin"
    with L.schritt("reiter"):
        L.gehe("#start")
        for rid in ["bibliothek", "tobies", "geraete", "start"]:
            L.klick(f'nav.tabs a[href="#{rid}"]')
            L.pruefe(L.hash() == f"#{rid}", f"reiter-{rid}", f"Hash {L.hash()!r} statt #{rid}")
            akt = L.js("return sr.querySelector('nav.tabs a[aria-current=\"page\"]')?.getAttribute('href')")
            L.pruefe(akt == f"#{rid}", f"reiter-{rid}", f"aria-current auf {akt!r}")
            L.pruefe(L.js("return !!sr.querySelector('main h2')?.textContent.trim()"), f"reiter-{rid}", "Seite ohne Überschrift")
            L.pruefe(L.js("return sr.activeElement === sr.querySelector('main')"), f"reiter-{rid}", "Fokus nach dem Wechsel nicht im Hauptteil")
    with L.schritt("reiter-abends-1-tap"):
        L.gehe("#start")
        L.klick('nav.tabs a[href="#geraete"]')
        L.pruefe(L.da('[data-karte="leise-zeiten"]'), "abends-1-tap", "Leise-Zeiten nach einem Tap auf Geräte nicht da")
        L.pruefe(L.da('[data-karte="gute-nacht"]'), "abends-1-tap", "Gute Nacht nach einem Tap auf Geräte nicht da")
    with L.schritt("kopf-suche"):
        L.gehe("#start")
        if L.job["layout"] != "seite":
            L.klick('header.kopf a[href="#suche"]')
        else:
            L.gehe("#suche")
        L.pruefe(L.hash() == "#suche" and L.da("input.suchfeld"), "kopf-suche", "Suche öffnet nicht")
    with L.schritt("rechte-technik"):
        L.gehe("#start")
        da = L.da("a.tech")
        L.pruefe(da == admin, "rechte-technik", f"Technik-Symbol {'fehlt' if admin else 'sichtbar'} für {L.job['rolle']}")
        if admin:
            L.klick("a.tech")
            L.pruefe(L.hash() == "#technik", "rechte-technik", f"Technik-Symbol führt nach {L.hash()}")
            akt = L.js("return sr.querySelector('a.tech')?.getAttribute('aria-current')")
            L.pruefe(akt == "page", "rechte-technik", "Technik-Symbol ohne aria-current")
        else:
            L.gehe("#technik")
            L.pruefe(L.da('[data-zustand="nur-admin"]'), "rechte-technik", "Benutzer sieht Technik ohne Sperre")


def ablauf_unterkante(L: Lauf):
    """Reiterleiste am unteren Rand des Panels, auch bei kurzem Inhalt; Mini-Player bündig; Safe-Area nur einmal."""
    # Safe-Area-Fälle: (Name, Rand des HA-Behälters unten, emulierter Inset der Seite selbst)
    faelle = [("ohne", 0, 0), ("ha-rand", 34, 0), ("inset", 0, 34)]
    seiten = [("start", "#start"), ("bibliothek", "#bibliothek"), ("tobies", "#tobies"), ("geraete", "#geraete")]
    for fname, ha_u, inset in faelle:
        with L.schritt(f"unterkante-{fname}"):
            L.pg.evaluate("([u, i]) => { const h = window.__el.parentElement; h.style.paddingBottom = u ? `${u}px` : ''; "
                          "if (i) document.documentElement.style.setProperty('--tb-safe-unten', `${i}px`); else document.documentElement.style.removeProperty('--tb-safe-unten'); "
                          "window.__el._messeRand(); window.__el.requestUpdate(); }", [ha_u, inset])
            L.ruhe()
            for sname, h in seiten:
                L.gehe(h)
                L.messe(f"unterkante-{fname}-{sname}", bild=False)
            # Mini-Player an: bündig auf der Leiste
            L.js("const m = document.createElement('div'); m.slot = 'mini'; m.id = 'mini-test'; m.style.height = '64px'; el.appendChild(m); el.setMini(true);")
            L.ruhe()
            L.gehe("#start")
            L.messe(f"unterkante-{fname}-mini", bild=False)
            # langer Inhalt, nach unten gescrollt (Rahmen bzw. Inhaltsspalte)
            L.gehe("#bibliothek")
            L.js("sr.querySelector('.rahmen').scrollTop = 99999; sr.querySelector('.spalte').scrollTop = 99999;")
            L.ruhe()
            L.messe(f"unterkante-{fname}-gescrollt", bild=False)
            unten = L.js("const r = sr.querySelector('.rahmen'), s = sr.querySelector('.spalte'); return [r.scrollHeight - r.clientHeight, r.scrollTop, s.scrollHeight - s.clientHeight, s.scrollTop]")
            L.pruefe(max(unten[0], unten[2]) <= 0 or unten[1] > 0 or unten[3] > 0, f"unterkante-{fname}", f"Bibliothek lässt sich nicht scrollen {unten}")
            L.js("el.setMini(false); el.querySelector('#mini-test')?.remove();")
    L.pg.evaluate("() => { const h = window.__el.parentElement; h.style.paddingBottom = ''; document.documentElement.style.removeProperty('--tb-safe-unten'); window.__el._messeRand(); }")
    L.ruhe()


def ablauf_klicks(L: Lauf):
    """B1: Seiten über echte Klicks wechseln (HA fängt Link-Klicks ab und meldet nur `location-changed`, kein `hashchange`)."""
    with L.schritt("klick-kachel-und-zurueck"):
        L.gehe("#start")
        L.pg.locator("a.tile").first.click(timeout=5000)
        L.ruhe()
        L.pruefe(L.hash().startswith("#serie-"), "klick-kachel", f"Kachel führt nach {L.hash()}")
        L.pruefe(L.da("[data-untertitel]") or L.da(".se-hero") or L.da("[data-zustand]"), "klick-kachel", "Serienseite zeigt sich nach dem Klick nicht")
        L.pg.locator("a[data-zurueck]").first.click(timeout=5000)
        L.ruhe()
        # AM6: der Knopf führt dorthin zurück, woher man kam: hier vom Start
        L.pruefe(L.hash() in ("#start", "") and not L.da("[data-liste=bibliothek]"), "klick-zurueck", f"Zurück-Link führt nicht auf den Start zurück ({L.hash()})")
        L.pg.go_back()
        L.ruhe()
        L.pruefe(L.js("return location.hash").startswith("#serie-") and L.da(".se-hero"), "klick-browser-zurueck", "Zurück-Taste des Browsers wechselt die Seite nicht")
    with L.schritt("klick-alle-anzeigen"):
        L.gehe("#start")
        L.pg.locator(f".reihe:has({REIHE_NEU}) a.alle").first.click(timeout=5000)
        L.ruhe()
        L.pruefe(L.hash().startswith("#bibliothek"), "alle-anzeigen", f"„Alle anzeigen“ führt nach {L.hash()}")
        L.pruefe(L.js("return el._seiteObj.e.sortierung") == "neu", "alle-anzeigen", "Bibliothek nicht nach „Zuletzt hinzugefügt“ sortiert")


def ablauf_reihen(L: Lauf):
    """AB5: Reihen auf dem Start zeigen, dass es weitergeht (angeschnittene Kachel, Verlauf); am Computer Pfeile bei Maus-Hover."""
    with L.schritt("reihen"):
        L.gehe("#start")
        L.pg.mouse.move(1, 1)  # die Maus von früheren Klicks nicht über der Reihe lassen
        L.pg.wait_for_timeout(450)
        info = L.js("""const sc = sr.querySelector('.hscroll[data-reihe]'); if (!sc) return null;
          const k = [...sc.querySelectorAll('.tile')]; const r = sc.getBoundingClientRect();
          const letzte = k.filter((t) => t.getBoundingClientRect().left < r.right - 1).pop().getBoundingClientRect();
          return { scrollbar: sc.offsetHeight - sc.clientHeight, angeschnitten: letzte.right > r.right + 4, rand: getComputedStyle(sr.querySelector('.reihenfeld'), '::after').opacity, breite: k[0].getBoundingClientRect().width };""")
        L.pruefe(info is not None, "reihen", "Reihe fehlt")
        if not info:
            return
        L.pruefe(info["angeschnitten"], "reihen", "Die letzte sichtbare Kachel ist nicht angeschnitten")
        L.pruefe(float(info["rand"]) > 0.5, "reihen", "Kein Verlauf am rechten Rand")
        L.pruefe(info["scrollbar"] <= 0, "reihen", f"Scrollleiste der Reihe sichtbar ({info['scrollbar']} px)")
        desktop = L.job["layout"] == "seite"
        if desktop:
            L.pruefe(info["breite"] >= 160, "reihen", f"Kachel nur {info['breite']:.0f} px breit")
        pfeil = L.pg.locator(".reihe .pfeil.vor").first
        if not desktop:
            L.pruefe(not pfeil.is_visible(), "reihen", "Pfeil am Handy sichtbar")
            return
        L.pruefe(float(L.js("return getComputedStyle(sr.querySelector('.pfeil.vor')).opacity")) < 0.1, "reihen", "Pfeil ohne Hover schon sichtbar")
        L.pg.locator(".reihenfeld").first.hover()
        L.pg.wait_for_timeout(300)
        L.pruefe(float(L.js("return getComputedStyle(sr.querySelector('.pfeil.vor')).opacity")) > 0.9, "reihen", "Pfeil rechts erscheint bei Hover nicht")
        L.pruefe(L.js("return getComputedStyle(sr.querySelector('.pfeil.zu')).display") == "none", "reihen", "Pfeil links am Anfang sichtbar")
        r = L.js("const b = sr.querySelector('.pfeil.vor').getBoundingClientRect(); return [b.width, b.height]")
        L.pruefe(r[0] >= 44 and r[1] >= 44, "reihen", f"Pfeil nur {r[0]:.0f}x{r[1]:.0f} px")
        s0 = L.js("return sr.querySelector('.hscroll[data-reihe]').scrollLeft")
        pfeil.click(timeout=4000)
        L.pg.wait_for_function("s0 => window.__el.shadowRoot.querySelector('.hscroll[data-reihe]').scrollLeft > s0 + 20", arg=s0, timeout=4000)
        L.pg.wait_for_timeout(600)
        L.pruefe(L.js("return getComputedStyle(sr.querySelector('.pfeil.zu')).display") != "none", "reihen", "Pfeil links fehlt nach dem Blättern")
        L.pruefe(float(L.js("return getComputedStyle(sr.querySelector('.reihenfeld'), '::before').opacity")) > 0.5, "reihen", "Kein Verlauf links nach dem Blättern")
        L.js("const s = sr.querySelector('.hscroll[data-reihe]'); s.scrollLeft = s.scrollWidth; s.dispatchEvent(new Event('scroll'));")
        L.pg.wait_for_timeout(200)
        L.pruefe(L.js("return getComputedStyle(sr.querySelector('.pfeil.vor')).display") == "none", "reihen", "Pfeil rechts am Ende der Reihe noch da")


def ablauf_suche(L: Lauf):
    with L.schritt("suche-vorschlag"):
        L.gehe("#suche")
        feld = L.pg.locator("input.suchfeld")
        feld.click()
        feld.press_sequentially("wild", delay=40)
        L.pg.wait_for_selector(".sugrow, [data-gruppe]", timeout=5000)
        L.ruhe()
        n = L.pg.locator(".sugrow").count()
        L.pruefe(n >= 1, "suche-vorschlag", "Kein Vorschlag zu „wild“")
        L.pruefe(L.da("[data-gruppe]"), "suche-vorschlag", "Keine Ergebnisgruppe zu „wild“")
        if n:
            text = L.pg.locator(".sugrow span").first.inner_text().strip()
            L.pg.locator(".sugrow").first.click(timeout=5000)
            L.pg.wait_for_function("t => window.__el.shadowRoot.querySelector('input.suchfeld').value.toLowerCase() === t", arg=text.lower(), timeout=5000)
            L.ruhe()
            wert = feld.input_value()
            L.pruefe(wert.strip().lower() == text.lower(), "suche-vorschlag", f"Feld {wert!r} nach Tap auf Vorschlag {text!r}")
            L.pruefe(L.da("[data-gruppe]"), "suche-vorschlag", "Keine Ergebnisse nach dem Vorschlag")
        L.pg.locator("[data-gruppe] a.lrow, [data-gruppe] a.rowbtn").first.click(timeout=5000)
        L.ruhe()
        L.pruefe(re.match(r"#(serie|tobie)-", L.hash()) is not None, "suche-treffer", f"Treffer führt nach {L.hash()}")
    with L.schritt("suche-leer"):
        L.gehe("#suche")
        feld = L.pg.locator("input.suchfeld")
        feld.fill("xyzq")
        L.pg.wait_for_selector('[data-leer="suche"]', timeout=5000)
        L.ruhe()
        L.pg.locator('[data-leer="suche"] button, [data-leer="suche"] a').first.click(timeout=5000)
        L.ruhe()
        L.pruefe(feld.input_value() == "", "suche-leer", "Eingabe nach „Suche löschen“ nicht leer")
    with L.schritt("suche-kurz"):
        L.gehe("#suche")
        L.pg.locator("input.suchfeld").fill("w")
        L.ruhe()
        L.pruefe(L.js("return sr.querySelector('[data-suche]')?.dataset.suche") == "leer", "suche-kurz", "Ein Zeichen löst eine Suche aus")


def ablauf_bibliothek(L: Lauf):
    with L.schritt("sortieren-filter"):
        L.gehe("#bibliothek")
        zahl0 = L.js("return sr.querySelectorAll('a.lrow, a.rcard').length")
        gesamt0 = L.js("return sr.querySelector('.count').textContent.trim()")
        L.pruefe(zahl0 > 0, "bibliothek-liste", "Bibliothek ohne Zeilen")
        L.klick("[data-sortieren]")
        L.pruefe(L.da("dialog[open]"), "sortieren-filter", "Blatt öffnet nicht")
        L.klick('dialog .optrow[role=radio]:nth-of-type(2)')
        L.pruefe(L.js("return sr.querySelector('dialog .optrow[role=radio]:nth-of-type(2)').getAttribute('aria-checked')") == "true", "sortieren-filter", "Sortierung „neu“ nicht gewählt")
        L.klick("dialog .optrow[aria-pressed]")
        L.pruefe(L.js("return sr.querySelector('dialog .optrow[aria-pressed]').getAttribute('aria-pressed')") == "true", "sortieren-filter", "Filter nicht gesetzt")
        L.klick("dialog .knoepfe .btn.primary")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=3000)
        L.ruhe()
        badge = L.js("return sr.querySelector('[data-sortieren] .nbadge')?.textContent.trim()")
        L.pruefe(badge == "2", "sortieren-filter", f"Zähler am Knopf {badge!r} statt '2'")
        gesamt1 = L.js("return sr.querySelector('.count').textContent.trim()")
        L.pruefe(gesamt1 != gesamt0, "sortieren-filter", f"Anzahl nach Filter unverändert ({gesamt1})")
        L.pruefe(L.js("return document.activeElement === null || sr.activeElement?.matches('[data-sortieren]')"), "sortieren-filter", "Fokus nicht am Knopf „Sortieren und Filter“")
        L.klick("[data-sortieren]")
        L.klick("dialog .knoepfe .btn:not(.primary)")  # Zurücksetzen, Blatt bleibt offen
        L.pruefe(L.da("dialog[open]"), "sortieren-filter", "Blatt schloss nach „Zurücksetzen“")
        L.klick("dialog .knoepfe .btn.primary")
        L.ruhe()
        L.pruefe(not L.da("[data-sortieren] .nbadge"), "sortieren-filter", "Zähler nach Zurücksetzen noch da")
        L.pruefe(L.js("return sr.querySelector('.count').textContent.trim()") == gesamt0, "sortieren-filter", "Anzahl nach Zurücksetzen anders")
    with L.schritt("arten"):
        L.gehe("#bibliothek")
        L.pg.locator(".arttab").nth(2).click(timeout=5000)  # Hörbücher
        L.ruhe()
        L.pruefe(L.js("return sr.querySelectorAll('.arttab')[2].getAttribute('aria-pressed')") == "true", "arten", "Art nicht gewählt")
        L.pruefe(L.js("return sr.querySelectorAll('a.lrow, a.rcard').length") > 0, "arten", "Art ohne Zeilen")
        L.pg.locator(".arttab").nth(0).click(timeout=5000)
        L.ruhe()
    with L.schritt("mehr-laden"):
        L.gehe("#bibliothek")
        n0 = L.js("return sr.querySelectorAll('a.lrow, a.rcard').length")
        L.js("sr.querySelector('button[data-mehr]')?.scrollIntoView()")
        L.pg.wait_for_function("n => window.__el.shadowRoot.querySelectorAll('a.lrow, a.rcard').length > n", arg=n0, timeout=5000)
        L.pruefe(True, "mehr-laden", "")
    with L.schritt("leere-filter"):  # Filter ohne Treffer: der Zustand mit „Zurücksetzen“
        L.gehe("#bibliothek")
        L.js("el._seiteObj.aendere({ filter: { pruefen: true }, typ: 'einzeln' })")
        L.ruhe()
        L.pruefe(L.da('[data-leer="filter"]') or L.da("a.lrow, a.rcard"), "leere-filter", "Weder Liste noch Leer-Zustand")
        L.js("el._seiteObj.zuruecksetzen({ mitArt: true })")
        L.ruhe()


def ablauf_serie(L: Lauf):
    admin = L.job["rolle"] == "admin"
    with L.schritt("serie-umbenennen"):
        L.gehe("#bibliothek")
        L.pg.locator("a.lrow, a.rcard").first.click(timeout=5000)
        L.ruhe()
        L.pruefe(L.hash().startswith("#serie-"), "serie-oeffnen", f"Zeile führt nach {L.hash()}")
        alt = L.js("return sr.querySelector('main h2')?.textContent.trim()")
        L.pruefe(bool(alt), "serie-oeffnen", "Serienseite ohne Namen")
        L.klick("[data-menue-serie]")
        for punkt, nur_admin in (("zusammen", True), ("reihenfolge", True), ("name", False)):
            da = L.da(f'dialog [data-menue="{punkt}"]')
            if nur_admin:
                L.pruefe(da == admin, "rechte-serie", f"Menüpunkt {punkt} {'fehlt' if admin else 'sichtbar'} für {L.job['rolle']}")
            else:
                L.pruefe(da, "rechte-serie", f"Menüpunkt {punkt} fehlt")
        L.klick('dialog [data-menue="name"]')
        L.pruefe(L.js("return sr.querySelector('#se-name')?.value") == alt, "serie-umbenennen", "Namensfeld enthält nicht den alten Namen")
        feld = L.pg.locator("#se-name")
        feld.fill("")
        L.klick("dialog .knoepfe .btn.primary")
        L.pruefe(L.da("dialog[open] .se-fehl"), "serie-umbenennen", "Leerer Name ohne Fehlerhinweis")
        feld.fill("Umbenannt Test")
        L.klick("dialog .knoepfe .btn.primary")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=3000)
        L.ruhe()
        L.pruefe(L.js("return sr.querySelector('main h2')?.textContent.trim()") == "Umbenannt Test", "serie-umbenennen", "Überschrift zeigt den neuen Namen nicht")
        L.pruefe(L.da(".toast"), "serie-umbenennen", "Keine Meldung nach dem Speichern")
        L.pg.locator("a[data-zurueck]").first.click(timeout=5000)
        L.ruhe()
        L.pruefe(L.hash() == "#bibliothek", "serie-umbenennen", f"Zurück führt nach {L.hash()}")
    with L.schritt("serie-menues"):
        L.gehe("#serie-lang")
        L.klick('[data-folge="f02.mp3"] [data-menue-folge]')
        L.pruefe(L.da("dialog[open]"), "serie-menues", "Folgenmenü öffnet nicht")
        L.blatt_zu()
        L.gehe("#serie-pruef")
        L.pruefe(L.da('[data-karte="ansehen"]'), "serie-menues", "Karte „bitte ansehen“ fehlt")
    if admin:
        with L.schritt("serie-reihenfolge"):
            L.gehe("#serie-kurz")
            L.klick("[data-menue-serie]")
            L.klick('[data-menue="reihenfolge"]')
            erste = L.js("return sr.querySelector('[data-folge]').dataset.folge")
            L.klick("[data-folge] [data-ab]")
            L.klick("[data-fertig]")
            L.pruefe(L.js("return sr.querySelector('[data-folge]').dataset.folge") != erste, "serie-reihenfolge", "Reihenfolge unverändert")


# ------------------------------------------------------------------ A8f: Cover ändern (Abnahme A16-1c, Punkte 5 und 6)
def testbild_png(pfad: Path, breite=600, hoehe=400):
    """Kleines Testfoto (PNG mit Farbverlauf und einem hellen Block, mit der Standardbibliothek gebaut); Querformat, damit das Zuschneiden etwas zu tun hat."""
    import struct
    import zlib

    zeilen = bytearray()
    for y in range(hoehe):
        zeilen.append(0)
        for x in range(breite):
            hell = 200 if (breite // 3 < x < breite // 2 and hoehe // 4 < y < hoehe // 2) else 0
            zeilen += bytes((min(255, x * 255 // breite + hell), min(255, y * 255 // hoehe + hell // 2), 140))

    def chunk(art, daten):
        c = struct.pack(">I", len(daten)) + art + daten
        return c + struct.pack(">I", zlib.crc32(art + daten) & 0xFFFFFFFF)

    pfad.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", breite, hoehe, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(zeilen), 6)) + chunk(b"IEND", b""))


def cover_blatt_offnen(L: Lauf, hash_):
    L.gehe(hash_)
    L.klick("[data-menue-serie]")
    L.klick('dialog [data-menue="cover"]')
    L.pruefe(L.da("dialog[open] [data-cover-waehlen]"), "cover-blatt", "Blatt „Cover ändern“ ohne „Foto wählen“")


def cover_foto_waehlen(L: Lauf, pfad, knopf="[data-cover-waehlen]"):
    """„Foto wählen“ mit echtem Klick; der Dateiwähler des Browsers bekommt das Testfoto."""
    with L.pg.expect_file_chooser(timeout=5000) as fc:
        L.pg.locator(f"dialog[open] {knopf}").first.click(timeout=4000)
    fc.value.set_files(str(pfad))
    L.pg.wait_for_timeout(250)
    L.ruhe()


def ablauf_cover(L: Lauf):
    """A8f: Cover ändern nur über echte Klicks: Menü → „Cover ändern“ → „Foto wählen“ (Dateiwähler) → Zuschneiden (Pfeilknöpfe, Ziehen mit der Maus,
    Regler, Pfeiltasten) → „Speichern“ (JPEG 1024 × 1024 kommt beim Mock an, das Cover erscheint ohne Neuladen) → „Zurück zum automatischen Cover“;
    dazu die Fehler: kein Bild, Foto über 20 MB. Die Zustände werden gemessen (Tippziele, Kontrast, kein seitliches Scrollen, Scroll-Prüfung)."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="tb-cover-") as tmp:
        tmp = Path(tmp)
        foto = tmp / "foto.png"
        testbild_png(foto)
        with L.schritt("cover-wahl"):
            cover_blatt_offnen(L, "#serie-kurz")
            L.pruefe(L.js("return sr.querySelector('dialog[open] #blatt-t')?.textContent.trim()") == "Cover für „Kleine Reise“", "cover-wahl", "Titel des Blatts stimmt nicht")
            L.pruefe(not L.da("[data-cover-zurueck]"), "cover-wahl", "„Zurück zum automatischen Cover“ ohne eigenes Foto")
            L.pruefe(L.js("return sr.activeElement?.matches('[data-cover-waehlen]')"), "cover-wahl", "Fokus nicht auf „Foto wählen“")
            L.messe("cover-wahl")
        with L.schritt("cover-fehler-kein-bild"):
            text = tmp / "brief.txt"
            text.write_text("das ist kein Bild")
            cover_foto_waehlen(L, text)
            L.pruefe(L.js("return sr.querySelector('dialog[open] .toast.err .tmsg')?.textContent") == "Das ist kein Bild. Bitte ein Foto wählen.", "cover-fehler", "Meldung „kein Bild“ fehlt oder steht nicht im Blatt")
            L.pruefe(not L.da("canvas[data-cover-vorschau]"), "cover-fehler", "Vorschau trotz Textdatei")
            L.messe("cover-fehler-kein-bild")
            L.klick("dialog[open] .toast.err .tok")
            L.pg.wait_for_timeout(450)  # A6m: die Meldung gleitet erst hinaus (--dauer-mittel), dann wird sie entfernt
            L.pruefe(not L.da(".toast.err"), "cover-fehler", "„OK“ räumt die Meldung nicht weg")
        with L.schritt("cover-fehler-zu-gross"):
            gross = tmp / "riesig.jpg"
            with open(gross, "wb") as f:
                f.truncate(21 * 1024 * 1024)
            cover_foto_waehlen(L, gross)
            L.pruefe(L.js("return sr.querySelector('dialog[open] .toast.err .tmsg')?.textContent") == "Das Foto ist zu groß (mehr als 20 MB). Nimm ein kleineres.", "cover-fehler", "Meldung „zu groß“ fehlt")
            L.klick("dialog[open] .toast.err .tok")
        with L.schritt("cover-zuschneiden"):
            cover_foto_waehlen(L, foto)
            L.warte_da("dialog[open] canvas[data-cover-vorschau]")
            box = L.pg.locator("dialog[open] canvas[data-cover-vorschau]").bounding_box()
            L.pruefe(box and 270 <= box["width"] <= 281 and abs(box["width"] - box["height"]) < 1, "cover-zuschneiden", f"Vorschau nicht quadratisch um 280 px: {box}")
            pixel = L.js("const c = sr.querySelector('canvas[data-cover-vorschau]'); const d = c.getContext('2d').getImageData(c.width / 2, c.height / 2, 1, 1).data; return [...d];")
            L.pruefe(pixel[3] == 255 and pixel[:3] != [255, 255, 255], "cover-zuschneiden", f"Vorschau ist nicht gezeichnet: {pixel}")
            L.pruefe(L.js("return sr.activeElement?.matches('canvas[data-cover-vorschau]')"), "cover-zuschneiden", "Fokus nicht auf der Vorschau")
            mitte0 = L.js("return sr.querySelector('canvas[data-cover-vorschau]').dataset.mitte")
            L.klick('dialog[open] [data-cover-pfeil="links"]')
            mitte1 = L.js("return sr.querySelector('canvas[data-cover-vorschau]').dataset.mitte")
            L.pruefe(mitte0 == "300,200", "cover-zuschneiden", f"Mitte zu Beginn {mitte0}")
            L.pruefe(mitte1 == "340,200", "cover-zuschneiden", f"„links“ verschiebt das Foto um ein Zehntel des Quadrats (40 von 400): {mitte0} -> {mitte1}")
            # Regler: Tastatur (Ende = ganz klein)
            L.pg.locator("dialog[open] [data-cover-regler]").focus()
            L.pg.keyboard.press("End")
            L.ruhe()
            L.pruefe(L.js("return sr.querySelector('canvas[data-cover-vorschau]').dataset.regler") == "100", "cover-zuschneiden", "Regler (Taste Ende) ändert den Ausschnitt nicht")
            L.klick('dialog[open] [data-cover-pfeil="links"]')
            mitte2 = L.js("return sr.querySelector('canvas[data-cover-vorschau]').dataset.mitte")
            L.pruefe(mitte2 != mitte0, "cover-zuschneiden", f"Pfeilknopf „links“ verschiebt nichts: {mitte2}")
            # Pfeiltasten auf der Vorschau
            L.pg.locator("dialog[open] canvas[data-cover-vorschau]").focus()
            L.pg.keyboard.press("ArrowUp")
            mitte3 = L.js("return sr.querySelector('canvas[data-cover-vorschau]').dataset.mitte")
            L.pruefe(mitte3 != mitte2, "cover-zuschneiden", "Pfeiltaste „hoch“ verschiebt nichts")
            # Ziehen mit der Maus
            b = L.pg.locator("dialog[open] canvas[data-cover-vorschau]").bounding_box()
            x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
            L.pg.mouse.move(x, y)
            L.pg.mouse.down()
            for i in range(1, 6):
                L.pg.mouse.move(x - 12 * i, y + 4 * i)
            L.pg.mouse.up()
            L.ruhe()
            mitte4 = L.js("return sr.querySelector('canvas[data-cover-vorschau]').dataset.mitte")
            L.pruefe(mitte4 != mitte3, "cover-zuschneiden", "Ziehen mit der Maus verschiebt nichts")
            L.pruefe(L.da("dialog[open]"), "cover-zuschneiden", "Ziehen auf der Vorschau schließt das Blatt")
            L.messe("cover-zuschneiden")
        with L.schritt("cover-speichern"):
            L.klick("dialog[open] .knoepfe .btn.primary")
            L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=6000)
            L.ruhe()
            L.pruefe("gespeichert" in L.toast(), "cover-speichern", f"Meldung nach dem Speichern: {L.toast()!r}")
            L.pruefe(not L.da(".toast.err"), "cover-speichern", "Fehlermeldung nach dem Speichern")
            z = L.mock("/zustand").get("cover", [])
            L.pruefe(len(z) == 1 and z[0]["methode"] == "POST" and z[0]["pfad"].endswith("/cover/kurz"), "cover-speichern", f"Aufrufe am Backend: {z}")
            if z:
                L.pruefe((z[0]["breite"], z[0]["hoehe"]) == (1024, 1024), "cover-speichern", f"Das JPEG ist nicht 1024 × 1024: {z[0]}")
                L.pruefe(0 < z[0]["groesse"] <= 3 * 1024 * 1024, "cover-speichern", f"Größe des JPEG {z[0]['groesse']}")
            L.pg.wait_for_function("() => { const c = window.__el.shadowRoot.querySelector('.cover.se-xl'); return c && c.dataset.stand && c.dataset.bild === '1'; }", timeout=5000)
            L.pruefe(True, "cover-speichern", "")
            L.messe("cover-gespeichert")
        with L.schritt("cover-zurueck"):
            L.klick("[data-menue-serie]")
            L.klick('dialog [data-menue="cover"]')
            L.pruefe(L.da("dialog[open] [data-cover-zurueck]"), "cover-zurueck", "„Zurück zum automatischen Cover“ fehlt mit eigenem Foto")
            L.messe("cover-eigen")
            L.klick("dialog[open] [data-cover-zurueck]")
            L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=6000)
            L.ruhe()
            z = L.mock("/zustand").get("cover", [])
            L.pruefe(len(z) == 2 and z[1]["methode"] == "DELETE" and z[1]["pfad"].endswith("/cover/kurz?quelle=eigen"), "cover-zurueck", f"Aufrufe am Backend: {z}")
            L.pruefe(L.js("return sr.querySelector('.cover.se-xl').dataset.stand") == "", "cover-zurueck", "Ohne automatisches Cover bleibt der Platzhalter")
            L.pruefe("automatische" in L.toast(), "cover-zurueck", f"Meldung: {L.toast()!r}")
    with L.schritt("cover-esc"):  # Esc verwirft ein gewähltes Foto ohne Hochladen
        with tempfile.TemporaryDirectory(prefix="tb-cover-") as tmp:
            foto = Path(tmp) / "foto.png"
            testbild_png(foto)
            cover_blatt_offnen(L, "#serie-kurz")
            cover_foto_waehlen(L, foto)
            L.warte_da("dialog[open] canvas[data-cover-vorschau]")
            n = len(L.mock("/zustand").get("cover", []))
            L.klick("dialog[open] .knoepfe .btn:first-child")  # „Abbrechen“
            L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=4000)
            L.pruefe(len(L.mock("/zustand").get("cover", [])) == n, "cover-abbrechen", "„Abbrechen“ hat trotzdem hochgeladen")
            L.pruefe(L.js("return sr.activeElement?.matches('[data-menue-serie]')"), "cover-abbrechen", "Fokus nicht zurück am Auslöser")


def ablauf_leise(L: Lauf):
    with L.schritt("leise-zeit"):
        L.gehe("#geraete")
        ids = lambda: L.js("return [...new Set([...sr.querySelectorAll('button.hit[data-fenster]')].map((b) => b.dataset.fenster))]")  # noqa: E731
        vorher = ids()
        L.pruefe(len(vorher) == 3, "leise-zeit", f"{len(vorher)} Leise-Zeiten statt 3")
        L.pruefe(L.da("[data-jetzt]"), "leise-zeit", "Satz zum Jetzt fehlt")
        # Fehlerwege: von = bis, kein Tag
        L.klick("[data-leise-neu]")
        L.pg.locator('dialog [data-feld="von"]').fill("20:00")
        L.pg.locator('dialog [data-feld="bis"]').fill("20:00")
        L.klick("dialog .knoepfe .btn.primary")
        L.pruefe(L.da("dialog[open]") and L.da(".toast.err"), "leise-zeit-fehler", "Von = Bis: Blatt zu oder keine Fehlermeldung")
        L.pg.locator('dialog [data-feld="bis"]').fill("21:00")
        for d in range(1, 8):
            on = L.js("return sr.querySelector(`dialog [data-tag=\"${x}\"]`).getAttribute('aria-pressed')", d) == "true"
            if on:
                L.klick(f'dialog [data-tag="{d}"]')
        L.pruefe(L.da("dialog .warnl"), "leise-zeit-fehler", "Ohne Tag kein Hinweis im Blatt")
        L.klick("dialog .knoepfe .btn.primary")
        L.pruefe(L.da("dialog[open]"), "leise-zeit-fehler", "Ohne Tag schloss das Blatt")
        # gültige neue Zeit: Fr/Sa 21:00–22:00 leiser
        L.klick('dialog [data-schnell="fr-sa"]')
        L.pg.locator('dialog [data-feld="von"]').fill("21:00")
        L.pg.locator('dialog [data-feld="bis"]').fill("22:00")
        L.klick("dialog .seg2 button:last-child")
        L.pruefe(L.da("dialog #lz-grenze"), "leise-zeit", "Regler fehlt bei „Leiser“")
        L.klick("dialog .knoepfe .btn.primary")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=3000)
        L.ruhe()
        nachher = ids()
        L.pruefe(len(nachher) == 4, "leise-zeit", f"{len(nachher)} Leise-Zeiten nach dem Anlegen statt 4")
        neu = [i for i in nachher if i not in vorher]
        if neu:
            L.klick(f'button.hit[data-fenster="{neu[0]}"]')
            L.pruefe(L.da("dialog[open] [data-loeschen]"), "leise-zeit", "„Löschen“ im Blatt zum Ändern fehlt")
            L.klick("[data-loeschen]")
            L.klick("dialog .btn.danger.solid")
            L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=3000)
            L.ruhe()
            L.pruefe(len(ids()) == 3, "leise-zeit", "Löschen entfernt die Leise-Zeit nicht")
        else:
            L.befund("ablauf", "leise-zeit", "Neue Leise-Zeit nicht in der Wochenansicht")


def ablauf_box(L: Lauf):
    admin = L.job["rolle"] == "admin"
    with L.schritt("box-detail"):
        L.gehe("#geraete")
        n = L.pg.locator("a.gstatus").count()
        L.pruefe(n == 2, "box-detail", f"{n} Boxen auf Geräte statt 2")
        L.pg.locator("a.gstatus").first.click(timeout=5000)
        L.ruhe()
        L.pruefe(L.hash().startswith("#box-"), "box-detail", f"Karte führt nach {L.hash()}")
        for z in ("verbindung", "akku", "laeuft"):
            L.pruefe(L.da(f'[data-zeile="{z}"]'), "box-detail", f"Zeile {z} fehlt")
        L.pruefe(L.da("main h2"), "box-detail", "Box ohne Überschrift")
        da = L.da("[data-technik-link]")
        L.pruefe(da == admin, "rechte-box", f"„Technik zu dieser Box“ {'fehlt' if admin else 'sichtbar'} für {L.job['rolle']}")
        if admin:
            L.klick("[data-technik-link]")
            L.pruefe(L.hash().startswith("#technik-box-"), "box-detail", f"Technik-Link führt nach {L.hash()}")
            L.pruefe(not L.da(".note.err"), "box-detail", "Technik zur Box zeigt einen Fehler")
            L.pg.go_back()
            L.ruhe()
        L.gehe("#box-kueche")
        L.pg.locator("a.back").first.click(timeout=5000)
        L.ruhe()
        L.pruefe(L.hash() == "#geraete", "box-detail", f"Zurück führt nach {L.hash()}")
    with L.schritt("box-fehlt"):
        L.gehe("#box-gibtsnicht")
        L.pruefe(L.da('[data-zustand="box-fehlt"]'), "box-fehlt", "Unbekannte Box ohne Hinweis")
        L.klick('[data-zustand="box-fehlt"] a.btn')
        L.pruefe(L.hash() == "#geraete", "box-fehlt", "Hinweis führt nicht zu den Geräten")


def ablauf_technik(L: Lauf):
    admin = L.job["rolle"] == "admin"
    if not admin:
        with L.schritt("technik-sperre"):
            for h in ("#technik", "#technik-speicher", "#technik-box-kueche"):
                L.gehe(h)
                L.pruefe(L.da('[data-zustand="nur-admin"]'), "technik-sperre", f"{h}: Benutzer sieht Technik")
        return
    with L.schritt("technik-unterseiten"):
        L.gehe("#technik")
        hrefs = L.js("return [...new Set([...sr.querySelectorAll('main a[href^=\"#technik-\"]')].map((a) => a.getAttribute('href')))]")
        L.pruefe(len(hrefs) >= 5, "technik-unterseiten", f"Nur {len(hrefs)} Links zu Unterseiten auf Technik")
        for h in hrefs:
            L.gehe("#technik")
            L.klick(f'main a[href="{h}"]')
            L.pruefe(L.hash() == h, "technik-unterseiten", f"Link {h} führt nach {L.hash()}")
            L.pruefe(L.da("main h2"), "technik-unterseiten", f"{h}: ohne Überschrift")
            L.pruefe(not L.da("main .note.err"), "technik-unterseiten", f"{h}: Fehlerkarte")
            L.pruefe(L.da('main a.back[href="#technik"]'), "technik-unterseiten", f"{h}: kein Link zurück nach Technik")
            L.klick('main a.back[href="#technik"]')
            L.pruefe(L.hash() == "#technik", "technik-unterseiten", f"{h}: Zurück führt nach {L.hash()}")
    with L.schritt("technik-unbekannt"):
        L.gehe("#technik-gibtsnicht")
        L.pruefe(L.da("main h2"), "technik-unbekannt", "Unbekannte Unterseite ohne Inhalt")


# Blätter auf allen Wegen schließen: (Name, Seite, Schritte bis zum Blatt, Auslöser für den Fokus)
# Der Knopf, der nur schließt: „Fertig“, „Schließen“ oder „Abbrechen“ (nicht „Zurücksetzen“, „Speichern“, „Ja“)
BLAETTER = [
    ("sortieren", "#bibliothek", ["[data-sortieren]"], "[data-sortieren]", ".knoepfe .btn.primary", False),
    ("serie-menue", "#serie-lang", ["[data-menue-serie]"], "[data-menue-serie]", ".knoepfe .btn", False),
    ("serie-name", "#serie-lang", ["[data-menue-serie]", '[data-menue="name"]'], "[data-menue-serie]", ".knoepfe .btn:first-child", False),
    ("serie-cover", "#serie-lang", ["[data-menue-serie]", '[data-menue="cover"]'], "[data-menue-serie]", ".knoepfe .btn:first-child", False),
    ("leise-neu", "#geraete", ["[data-leise-neu]"], "[data-leise-neu]", ".knoepfe .btn:first-child", False),
    ("leise-aendern", "#geraete", ["button.hit[data-fenster=nacht]"], "button.hit[data-fenster=nacht]", ".knoepfe .btn:first-child", False),
    ("technik-cover", "#technik-speicher", ["[data-aktion=cover]"], "[data-aktion=cover]", ".knoepfe .btn:last-child", True),
]
WEGE = ["x", "knopf", "esc", "hintergrund", "wischen", "route"]


def blatt_schliessen(L: Lauf, weg, knopf):
    pg = L.pg
    if weg == "x":
        pg.locator("dialog[open] .blatt-x").click(timeout=5000)
    elif weg == "knopf":
        pg.locator(f"dialog[open] {knopf}").first.click(timeout=5000)
    elif weg == "esc":
        pg.keyboard.press("Escape")
    elif weg == "hintergrund":
        pg.mouse.click(4, 4)
    elif weg == "wischen":
        r = pg.locator("dialog[open] .griff").first.bounding_box()
        h = pg.locator("dialog[open]").first.bounding_box()["height"]
        x, y = r["x"] + r["width"] / 2, r["y"] + r["height"] / 2
        pg.mouse.move(x, y)
        pg.mouse.down()
        for i in range(1, 11):
            pg.mouse.move(x, y + (h * 0.55) * i / 10)
            pg.wait_for_timeout(16)
        pg.mouse.up()
    elif weg == "route":
        pg.evaluate("() => { location.hash = '#start'; }")


def ablauf_blaetter(L: Lauf):
    admin = L.job["rolle"] == "admin"
    for name, seite, schritte, ausloeser, knopf, nur_admin in BLAETTER:
        if nur_admin and not admin:
            continue
        for weg in WEGE:
            z = f"blatt-{name}-{weg}"
            with L.schritt(z):
                L.aufraeumen()
                L.gehe("#start")
                L.gehe(seite)
                for s in schritte:
                    L.klick(s)
                L.pruefe(L.da("dialog[open]"), z, "Blatt nicht offen")
                blatt_schliessen(L, weg, knopf)
                L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog')", timeout=4000)
                L.ruhe()
                L.pruefe(L.js("return el._blatt === null"), z, "App hält das Blatt noch")
                L.pruefe(not L.da("dialog[open]"), z, "dialog noch offen")
                if weg != "route":
                    L.pruefe(L.js("return !!sr.activeElement && sr.activeElement.matches(x)", ausloeser), z, f"Fokus nicht am Auslöser ({L.js('return sr.activeElement?.outerHTML.slice(0, 60)')})")
                tf = L.js("return [sr.querySelector('.spalte'), sr.querySelector('.rahmen')].map((e) => getComputedStyle(e).transform)")
                L.pruefe(all(t in ("none", "matrix(1, 0, 0, 1, 0, 0)") for t in tf), z, f"Seite hinter dem Blatt noch verschoben: {tf}")
    with L.schritt("blatt-ersetzt"):  # Menü → Namensblatt: nur ein Dialog zur Zeit
        L.gehe("#serie-lang")
        L.klick("[data-menue-serie]")
        L.klick('[data-menue="name"]')
        L.pruefe(L.pg.locator("dialog").count() == 1, "blatt-ersetzt", "Mehr als ein Dialog nach „Name ändern“")
        L.blatt_zu()



# ------------------------------------------------------------------ A9/A10: Abnahme A16-1b (Tobies)
def zum_reiter(L: Lauf, rid):
    L.klick(f'nav.tabs a[href="#{rid}"]')


def ziel_waehlen(L: Lauf, wahl):
    """Ein Ergebnis der Zielwahl antippen (wartet, bis die Liste geladen ist)."""
    L.warte_da(f'[data-zielwahl] [data-wahl="{wahl}"]')
    L.klick(f'[data-zielwahl] [data-wahl="{wahl}"]')


def erste_serie(L: Lauf):
    """Kennung einer Serie in der Zielwahl, die nicht der Löwe spielt (die erste Kachel „Ganze Serie“)."""
    L.warte_da('[data-zielwahl] [data-ergebnis="serie"] [data-wahl]')
    return L.js("return sr.querySelector('[data-zielwahl] [data-ergebnis=\"serie\"] [data-wahl]').dataset.wahl")


def ablauf_tobies_weg1(L: Lauf):
    """(1) Neuer Tobie Weg 1 mit Namen, danach „Rückgängig“; nur Ereignisse nach dem Start der Warteseite."""
    neu_uid = "04AABBCCDD0001"
    with L.schritt("tobies-weg1"):
        L.gehe("#start")
        zum_reiter(L, "tobies")
        L.pruefe(L.hash() == "#tobies" and L.da("[data-regal] a[data-neu]"), "weg1", "Regal mit „+ Neuer Tobie“ fehlt")
        L.klick("[data-regal] a[data-neu]")
        L.pruefe(L.hash() == "#neu", "weg1", f"„+ Neuer Tobie“ führt nach {L.hash()}")
        L.messe("ablauf-neu")
        L.klick('a[data-weg="jetzt"]')
        L.pruefe(L.hash() == "#neu-warten" and L.da('[data-zustand="warten"]'), "weg1", "Warteseite fehlt")
        L.messe("ablauf-neu-warten")
        L.pg.wait_for_timeout(500)
        L.pruefe(L.hash() == "#neu-warten", "weg1", "Der schon wartende Tobie hat die Warteseite weitergeschaltet (nur Ereignisse nach dem Start zählen)")
        L.mock("/legeauf", {"box": "kinderzimmer", "uid": neu_uid})
        L.warte_hash("#neu-ziel-")
        L.pruefe(L.hash().startswith(f"#neu-ziel-{neu_uid}"), "weg1", f"Weiter nach {L.hash()}")
        L.pruefe(L.da('[data-karte="erkannt"]') and "Neuer Tobie erkannt" in L.js("return sr.querySelector('[data-karte=erkannt]').textContent"), "weg1", "„Neuer Tobie erkannt“ fehlt")
        L.pruefe(L.da(".tb-leiste [data-versehen]"), "weg1", "„Das war ein Versehen“ oben rechts fehlt")
        L.pruefe(L.js("const v = sr.querySelector('.tb-leiste [data-versehen]').getBoundingClientRect(), b = sr.querySelector('.tb-leiste a.back').getBoundingClientRect(); return v.left > b.right"), "weg1", "„Versehen“ steht nicht rechts neben „‹ Tobies“")
        L.pruefe(L.js("return sr.activeElement?.id !== 'tb-neuname'"), "weg1", "Autofokus im Namensfeld")
        L.messe("ablauf-neu-ziel")
        L.pg.locator("#tb-neuname").fill("Fuchs")
        L.ruhe()
        wahl = erste_serie(L)
        L.klick(f'[data-zielwahl] [data-wahl="{wahl}"]')
        L.pruefe(L.hash() == "#tobies", "weg1", f"Nach dem Zuordnen {L.hash()} statt #tobies")
        L.pruefe(L.toast().startswith("Fertig: Fuchs spielt jetzt"), "weg1", f"Meldung: {L.toast()!r}")
        L.pruefe(L.js("return sr.querySelector('.toast .tok')?.textContent") == "Rückgängig", "weg1", "„Rückgängig“ fehlt an der Meldung")
        L.pruefe(L.da(f'[data-regal] [data-tobie="{neu_uid}"]'), "weg1", "Der neue Tobie steht nicht im Regal")
        z = L.mock("/zustand")
        L.pruefe(z["zuordnungen"][neu_uid]["name"] == "Fuchs", "weg1", "Name nicht gespeichert")
        # (5) „Rückgängig“ bei einem neuen Tobie: die Karte auf „Geräte“ kommt wieder
        L.klick(".toast .tok")
        z = L.mock("/zustand")
        L.pruefe(neu_uid not in z["zuordnungen"] and any(e["uid"] == neu_uid for e in z["neue"]), "weg1-rueckgaengig", "Der Tobie liegt nach „Rückgängig“ nicht wieder als unbekannt in der Liste")
        L.pruefe(not L.da(f'[data-regal] [data-tobie="{neu_uid}"]'), "weg1-rueckgaengig", "Der Tobie steht noch im Regal")
        zum_reiter(L, "geraete")
        L.pruefe(L.da(f'[data-karte="neuer-tobie"][data-uid="{neu_uid}"], [data-karte="neue-tobies"] [data-uid="{neu_uid}"]'), "weg1-rueckgaengig", "Die Karte „Neuer Tobie“ ist nicht wieder da")
    with L.schritt("tobies-weg1-versehen"):
        L.gehe("#start")
        zum_reiter(L, "geraete")
        L.klick('[data-karte="neuer-tobie"] a.tb-karte-link, [data-karte="neue-tobies"] a.tb-zeilenlink')
        L.pruefe(L.hash().startswith("#neu-ziel-"), "versehen", f"Karte führt nach {L.hash()}")
        L.pruefe(L.js("return sr.querySelector('nav.tabs a[aria-current=\"page\"]')?.getAttribute('href')") == "#geraete", "versehen", "Reiter „Geräte“ ist nicht markiert")
        L.klick("[data-versehen]")
        L.pruefe(L.da("dialog[open]"), "versehen", "Keine Rückfrage")
        L.klick("dialog[open] .knoepfe .btn.primary")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=3000)
        L.ruhe()
        L.pruefe(L.hash() == "#geraete", "versehen", f"Nach „Nicht merken“: {L.hash()}")


def ablauf_tobies_weg2(L: Lauf):
    """(2) Weg 2 mit Namensfeld, danach Auflegen; (8) Abbrechen; Auto-Zuordnung scheitert."""
    with L.schritt("tobies-weg2"):
        L.gehe("#start")
        zum_reiter(L, "tobies")
        L.klick("[data-regal] a[data-neu]")
        L.klick('a[data-weg="spaeter"]')
        L.pruefe(L.hash() == "#neu-queue", "weg2", f"Weg 2 führt nach {L.hash()}")
        L.pruefe(L.js("return [...sr.querySelectorAll('[data-karte=box] .seg2 button')].map((b) => b.textContent.trim()).join('|')") == "Küche|Kinderzimmer|Egal welche", "weg2", "Boxwahl")
        L.klick('[data-karte="box"] [data-wert="kueche"]')
        L.pg.locator("#tb-queue-name").fill("Bär")
        L.ruhe()
        L.messe("ablauf-neu-queue")
        wahl = erste_serie(L)
        L.klick(f'[data-zielwahl] [data-wahl="{wahl}"]')
        L.pruefe(L.da('[data-zustand="wartet"]'), "weg2", "Wartekarte fehlt")
        L.pruefe(L.js("return sr.querySelector('[data-zustand=wartet] .tb-titel').textContent").startswith("Nächster neuer Tobie auf Küche spielt"), "weg2", "Titel der Wartekarte")
        L.messe("ablauf-neu-queue-wartet")
        z = L.mock("/zustand")
        L.pruefe(len(z["warteschlange"]) == 1 and z["warteschlange"][0]["name"] == "Bär" and z["warteschlange"][0]["box"] == "kueche", "weg2", f"Vormerkung: {z['warteschlange']}")
        L.mock("/legeauf", {"box": "kueche", "uid": "04AABBCCDD0002"})
        L.warte_hash("#tobies")
        L.pruefe(L.da('[data-regal] [data-tobie="04AABBCCDD0002"]'), "weg2", "Der aufgelegte Tobie steht nicht im Regal")
        L.pruefe(L.toast().startswith("Küche: Der neue Tobie spielt jetzt"), "weg2", f"Meldung: {L.toast()!r}")
        L.pruefe(L.js("return !sr.querySelector('.toast .tok')"), "weg2", "„Name geben“ trotz Namen")
    with L.schritt("tobies-weg2-ohne-namen"):
        L.gehe("#neu-queue")
        wahl = erste_serie(L)
        L.klick(f'[data-zielwahl] [data-wahl="{wahl}"]')
        L.klick('[data-zustand="wartet"] [data-fertig]')
        L.pruefe(L.hash() == "#tobies" and L.da("[data-eintrag]"), "weg2", "Nach „Fertig“ fehlt die Karte der Vormerkung im Regal")
        L.messe("ablauf-regal-wartet")
        L.mock("/legeauf", {"box": "kinderzimmer", "uid": "04AABBCCDD0003"})
        L.warte_da(".toast .tok")
        L.pruefe(L.js("return sr.querySelector('.toast .tok').textContent") == "Name geben", "weg2", "„Name geben“ fehlt")
        L.klick(".toast .tok")
        L.pruefe(L.hash() == "#tobie-04AABBCCDD0003?name=1", "weg2", f"„Name geben“ führt nach {L.hash()}")
        with contextlib.suppress(PlaywrightTimeout):
            L.pg.wait_for_function("() => window.__el.shadowRoot.activeElement?.id === 'tb-name'", timeout=3000)
        L.pruefe(L.js("return sr.activeElement?.id === 'tb-name'"), "weg2", f"Fokus nicht im Namensfeld ({L.js('return sr.activeElement?.outerHTML.slice(0, 80)')})")
        zum_reiter(L, "geraete")
        L.pruefe(L.da('[data-karte="platz-bekommen"]'), "weg2", "Karte „Ein neuer Tobie hat einen Platz bekommen“ fehlt auf Geräte")
        L.messe("ablauf-geraete-platz")
        L.klick('[data-karte="platz-bekommen"] [data-spaeter]')
        L.pruefe(not L.da('[data-karte="platz-bekommen"]'), "weg2", "„Später“ entfernt die Karte nicht")
    with L.schritt("tobies-queue-abbrechen"):
        L.gehe("#neu-queue")
        wahl = erste_serie(L)
        L.klick(f'[data-zielwahl] [data-wahl="{wahl}"]')
        L.klick('[data-zustand="wartet"] [data-fertig]')
        L.klick("[data-eintrag] [data-abbrechen]")
        L.pruefe(not L.da("[data-eintrag]") and L.mock("/zustand")["warteschlange"] == [], "queue-abbrechen", "Vormerkung bleibt nach „Abbrechen“")
    with L.schritt("tobies-auto-scheitert"):
        L.gehe("#neu-queue")
        wahl = erste_serie(L)
        L.klick(f'[data-zielwahl] [data-wahl="{wahl}"]')
        L.klick('[data-zustand="wartet"] [data-fertig]')
        L.mock("/sperre", {"zustand": "export_neuer"})
        L.pg.wait_for_timeout(50)
        L.mock("/legeauf", {"box": "kueche", "uid": "04AABBCCDD0004"})
        zum_reiter(L, "geraete")
        L.warte_da('[data-karte="nicht-zugeordnet"]')
        L.pruefe(L.js("return sr.querySelector('[data-karte=nicht-zugeordnet] h3').textContent") == "Konnte nicht zugeordnet werden", "auto-scheitert", "Karte „Konnte nicht zugeordnet werden“")
        L.pruefe(L.da('[data-karte="wartet"]'), "auto-scheitert", "Die Warteschlangen-Karte fehlt")
        L.messe("ablauf-geraete-nicht-zugeordnet")
        L.klick('[data-karte="wartet"] .tb-wzeile')
        L.pruefe(L.da("dialog[open]"), "auto-scheitert", "Blatt „Nicht mehr warten“ fehlt")
        L.messe("ablauf-geraete-wartet-blatt")
        L.klick("dialog[open] .knoepfe .btn.danger, dialog[open] .knoepfe .btn:last-child")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=3000)
        L.mock("/sperre", {"zustand": "ok"})
        L.ruhe()


def ablauf_tobies_name_geben_weit_unten(L: Lauf):
    """B-1: „Name geben“ (`#tobie-<kennung>?name=1`) bei vielen Serien in der Zielwahl: das Namensfeld liegt weit unten, die Seite
    scrollt es per Programm in die Sicht. Danach darf nur der Scroll-Behälter gescrollt sein, die Reiterleiste bleibt am Panelrand."""
    uid = "04AABBCCDD0031"
    with L.schritt("tobies-name-geben-weit-unten"):
        L.mock("/serien-viele", {"anzahl": 14})
        L.gehe("#neu-queue")
        wahl = erste_serie(L)
        L.klick(f'[data-zielwahl] [data-wahl="{wahl}"]')
        L.klick('[data-zustand="wartet"] [data-fertig]')
        L.mock("/legeauf", {"box": "kinderzimmer", "uid": uid})
        L.warte_da(".toast .tok")
        # Die Zuordnungen kommen spät, die Serienliste ist dann schon da: das Namensfeld sitzt ganz unten, der Behälter `.rahmen` kann es
        # nicht mehr in die Mitte rollen, den Rest müsste der äußere Behälter `.app` übernehmen (so im echten HA: .app scrollTop 178).
        L.js("const h = el.hass.connection; h.__orig = h.sendMessagePromise; "
             "h.sendMessagePromise = (m) => m.type === 'tobibox/zuordnung/list' ? new Promise((r) => setTimeout(r, 900)).then(() => h.__orig(m)) : h.__orig(m);")
        try:
            L.klick(".toast .tok")
            L.pruefe(L.hash() == f"#tobie-{uid}?name=1", "name-weit-unten", f"„Name geben“ führt nach {L.hash()}")
            with contextlib.suppress(PlaywrightTimeout):
                L.pg.wait_for_function("() => window.__el.shadowRoot.activeElement?.id === 'tb-name'", timeout=4000)
        finally:
            L.js("const h = el.hass.connection; if (h.__orig) { h.sendMessagePromise = h.__orig; delete h.__orig; }")
        L.pruefe(L.js("return sr.activeElement?.id === 'tb-name'"), "name-weit-unten", "Fokus nicht im Namensfeld")
        L.pg.wait_for_timeout(400)  # sanftes Scrollen ausklingen lassen
        L.messe("ablauf-name-geben-weit-unten")
        sicht = L.js("""
          const f = sr.querySelector('#tb-name'), r = sr.querySelector('.rahmen').getBoundingClientRect(), b = f.getBoundingClientRect();
          return { oben: b.top >= r.top - 1, unten: b.bottom <= r.bottom + 1, scroll: sr.querySelector('.rahmen').scrollTop, hoch: sr.querySelector('.rahmen').scrollHeight - sr.querySelector('.rahmen').clientHeight };
        """)
        if L.job.get("layout") == "unten":
            L.pruefe(sicht["scroll"] > 0 and sicht["scroll"] >= sicht["hoch"] - 1, "name-weit-unten", f"`.rahmen` ist nicht ganz unten: das Namensfeld lag nicht weit genug unten, der Fall wird nicht geprüft ({sicht})")
        L.scroll_pruefen()


def ablauf_tobies_meldung(L: Lauf):
    """(3) Meldung „Neuer Tobie auf Box 1.“ mit Knopf „Zuordnen“ auf einer fremden Seite, mehrere unbekannte Tobies."""
    with L.schritt("tobies-meldung"):
        L.gehe("#bibliothek")
        L.mock("/legeauf", {"box": "kueche", "uid": "04AABBCCDD0011"})
        L.mock("/legeauf", {"box": "kueche", "uid": "04AABBCCDD0012"})
        L.warte_da(".toast .tok")
        L.pruefe(L.toast() == "Neuer Tobie auf Küche.", "meldung", f"Meldung: {L.toast()!r}")
        L.pruefe(L.js("return sr.querySelector('nav.tabs a[href=\"#geraete\"] .dot')?.textContent") is not None, "meldung", "Punkt am Reiter „Geräte“ fehlt")
        L.messe("ablauf-meldung")
        L.klick(".toast .tok")
        L.pruefe(L.hash().startswith("#neu-ziel-04AABBCCDD0012"), "meldung", f"„Zuordnen“ führt nach {L.hash()}")
        zum_reiter(L, "geraete")
        zaehler = L.js("return sr.querySelector('[data-karte=\"neue-tobies\"] h3')?.textContent ?? ''")
        L.pruefe(re.match(r"^[3-9] neue Tobies auf Küche$", zaehler) is not None, "meldung", f"Zähler: {zaehler!r}")
        L.messe("ablauf-geraete-mehrere")


def ablauf_tobies_umhaengen(L: Lauf):
    """(4) Umhängen mit Meldung (altes und neues Ziel), „Rückgängig“, Zeile „Vorher“; (7) Gute-Nacht-Karte; Namen; Vergessen."""
    with L.schritt("tobies-umhaengen"):
        L.gehe("#start")
        zum_reiter(L, "tobies")
        L.klick(f'[data-regal] a[data-tobie="{LOEWE}"]')
        L.pruefe(L.hash() == f"#tobie-{LOEWE}", "umhaengen", f"Kachel führt nach {L.hash()}")
        L.pruefe(L.js("return sr.querySelector('main h2').textContent") == "Was soll Löwe spielen?", "umhaengen", "Überschrift")
        L.pruefe(L.da(".tb-cur.jetzt") and L.da('[data-wahl="aktion"]'), "umhaengen", "„Spielt jetzt“ oder Gute-Nacht-Karte fehlt")
        L.pruefe(not L.da("[data-vorher]"), "umhaengen", "„Vorher“ ohne Umhängen")
        wahl = erste_serie(L)
        L.klick(f'[data-zielwahl] [data-wahl="{wahl}"]')
        L.pruefe(L.hash() == "#tobies", "umhaengen", f"Nach dem Zuordnen {L.hash()}, Fehler: {L.js('return sr.querySelector(\'.toast.err .tmsg\')?.textContent ?? \'\'')!r}")
        t = L.toast()
        L.pruefe(t.startswith("Löwe spielt jetzt „") and "(vorher „Die wilde Reise der kleinen Drachen durch das Wolkenland“)." in t, "umhaengen", f"Meldung: {t!r}")
        L.klick(".toast .tok")
        z = L.mock("/zustand")
        L.pruefe(z["zuordnungen"][LOEWE]["ziel"] == {"typ": "serie", "serie": "lang"}, "umhaengen", "„Rückgängig“ stellt das alte Ziel nicht her")
    with L.schritt("tobies-vorher"):
        L.gehe(f"#tobie-{LOEWE}")
        wahl = erste_serie(L)
        L.klick(f'[data-zielwahl] [data-wahl="{wahl}"]')
        L.klick(f'[data-regal] a[data-tobie="{LOEWE}"]')
        L.pruefe(L.da("[data-vorher]"), "vorher", "Zeile „Vorher“ fehlt")
        L.pruefe(L.js("return sr.querySelector('[data-vorher]').textContent").strip().startswith("Vorher: Die wilde Reise"), "vorher", "Text der Zeile „Vorher“")
        L.messe("ablauf-tobie-vorher")
        L.klick("[data-zurueckstellen]")
        L.pruefe(L.toast().startswith("Löwe spielt wieder „Die wilde Reise"), "vorher", f"Meldung nach „Zurückstellen“: {L.toast()!r}")
        L.pruefe(not L.da("[data-vorher]"), "vorher", "Nach „Zurückstellen“ steht die Zeile noch da")
        L.pruefe(L.mock("/zustand")["zuordnungen"][LOEWE]["ziel"] == {"typ": "serie", "serie": "lang"}, "vorher", "„Zurückstellen“ stellt das alte Ziel nicht her")
    with L.schritt("tobies-gute-nacht"):
        L.gehe(f"#tobie-{LOEWE_FOLGE}")
        L.pruefe("Gute-Nacht-Karte" in L.js("return sr.querySelector('[data-wahl=aktion]')?.textContent ?? ''"), "gute-nacht", "Gute-Nacht-Karte fehlt")
        L.klick('[data-zielwahl] [data-wahl="aktion"]')
        L.pruefe(L.hash() == "#tobies", "gute-nacht", f"Nach der Gute-Nacht-Karte {L.hash()}")
        L.pruefe(L.mock("/zustand")["zuordnungen"][LOEWE_FOLGE]["ziel"] == {"typ": "aktion", "aktion": "gute_nacht"}, "gute-nacht", "Ziel nicht gesetzt")
    with L.schritt("tobies-name-und-vergessen"):
        L.aufraeumen()  # die Meldung vom Zuordnen liegt sonst über dem Knopf
        L.gehe(f"#tobie-{LOEWE}")
        L.pg.locator("#tb-name").fill("Leo")
        L.klick("[data-name-speichern]")
        L.pruefe(L.mock("/zustand")["zuordnungen"][LOEWE]["name"] == "Leo", "name", "Name nicht gespeichert")
        L.pruefe(L.js("return sr.querySelector('main h2').textContent") == "Was soll Leo spielen?", "name", "Überschrift zeigt den neuen Namen nicht")
        L.aufraeumen()  # „Name gespeichert.“ liegt sonst über dem Knopf
        L.klick("[data-vergessen]")
        L.pruefe(L.da("dialog[open]"), "vergessen", "Keine Rückfrage")
        L.messe("ablauf-tobie-vergessen")
        L.klick("dialog[open] .knoepfe .btn.danger, dialog[open] .knoepfe .btn.solid")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=3000)
        L.ruhe()
        L.pruefe(L.hash() == "#tobies" and LOEWE not in L.mock("/zustand")["zuordnungen"], "vergessen", "Tobie nicht vergessen")


def ablauf_tobies_geben(L: Lauf):
    """(6) „Einem Tobie geben …“ von der Serie, vom Lied und von einer Folge; Karte „Gespielt von“."""
    with L.schritt("tobies-geben-serie"):
        L.gehe("#bibliothek")
        L.gehe("#serie-kurz")
        L.pruefe(L.da('[data-karte="gespielt-von"] a[data-geben]') and not L.da('[data-karte="gespielt-von"] [data-plus]'), "geben", "Serie ohne Tobie: Textlink fehlt oder „+ Tobie“ da")
        L.klick('[data-karte="gespielt-von"] a[data-geben]')
        L.pruefe(L.hash() == "#geben-kurz", "geben", f"Link führt nach {L.hash()}")
        L.pruefe(L.js("return sr.querySelector('[data-regal] [role=listitem]:first-child a')?.getAttribute('href')") == "#neu?s=kurz", "geben", "„+ Neuer Tobie“ zuerst fehlt")
        L.messe("ablauf-geben")
        uid = L.js("return sr.querySelector('[data-regal] button[data-tobie]').dataset.tobie")
        L.klick(f'[data-regal] button[data-tobie="{uid}"]')
        L.pruefe(L.hash() == "#serie-kurz", "geben", f"Nach dem Zuordnen {L.hash()}")
        L.pruefe(L.js("return !!sr.querySelector('.toast .tok')"), "geben", "Meldung mit „Rückgängig“ fehlt")
        L.pruefe(L.da(f'[data-karte="gespielt-von"] a.tb-chip[data-chip="{uid}"]') and L.da('[data-karte="gespielt-von"] a[data-plus]'), "geben", "Chip und „+ Tobie“ fehlen danach")
        L.messe("ablauf-serie-chips")
        L.klick(f'[data-karte="gespielt-von"] a.tb-chip[data-chip="{uid}"]')
        L.pruefe(L.hash() == f"#tobie-{uid}", "geben", f"Chip führt nach {L.hash()}")
    with L.schritt("tobies-geben-folge"):
        L.aufraeumen()  # die Meldung vom Zuordnen liegt am Handy über der Folgenzeile
        L.gehe("#serie-kurz")
        L.klick('[data-folge="k3.mp3"] [data-menue-folge]')
        L.pruefe(L.js("return sr.querySelector('dialog[open] [data-menue]:first-child')?.dataset.menue") == "geben", "geben-folge", "„Einem Tobie geben …“ steht nicht zuerst im Menü")
        L.klick('dialog[open] [data-menue="geben"]')
        L.pruefe(L.hash() == "#geben-kurz~k3.mp3", "geben-folge", f"Menü führt nach {L.hash()}")
        L.klick("[data-regal] a[data-neu]")
        L.pruefe(L.hash() == "#neu?s=kurz&f=k3.mp3", "geben-folge", f"„+ Neuer Tobie“ führt nach {L.hash()}")
        L.klick('a[data-weg="jetzt"]')
        L.mock("/legeauf", {"box": "kinderzimmer", "uid": "04AABBCCDD0021"})
        L.warte_hash("#neu-ziel-")
        L.pruefe(L.da(".tb-cur.fest") and not L.da("[data-zielwahl]"), "geben-folge", "Festes Ziel: Karte fehlt oder Zielwahl steht da")
        L.klick("[data-fertig]")
        L.pruefe(L.hash() == "#serie-kurz", "geben-folge", f"Nach „Fertig“ {L.hash()}")
        L.pruefe(L.da('[data-folge="k3.mp3"] a.tb-chip[data-chip="04AABBCCDD0021"]'), "geben-folge", "Chip an der Folge fehlt")
        L.messe("ablauf-serie-folgenchip")
    with L.schritt("tobies-geben-lied"):
        L.gehe("#serie-lied")
        L.klick('[data-karte="gespielt-von"] a[data-geben]')
        L.pruefe(L.hash() == "#geben-lied~wiegenlied.mp3", "geben-lied", f"Link führt nach {L.hash()}")
    with L.schritt("tobies-geben-suche"):
        L.gehe("#suche")
        L.pg.locator("input.suchfeld").fill("Folge 4")
        L.warte_da("[data-menue-folge]")
        L.klick("[data-menue-folge]")
        L.pruefe(L.da('dialog[open] [data-menue="geben"]'), "geben-suche", "„Einem Tobie geben …“ im Blatt der Suche fehlt")
        L.blatt_zu()


def ablauf_tobies_lernmodus(L: Lauf):
    """(9) Der Lernmodus steht nur in „Technik“ und nur für Administratoren; Alltagsseiten bieten ihn nicht an."""
    admin = L.job["rolle"] == "admin"
    with L.schritt("tobies-lernmodus"):
        for h in ("#tobies", f"#tobie-{LOEWE_FOLGE}", "#neu", "#geraete", "#serie-lang"):
            L.gehe(h)
            L.pruefe("Lernmodus" not in L.js("return sr.querySelector('main').textContent"), "lernmodus", f"{h}: Lernmodus im Alltag")
        L.gehe("#technik-tobies")
        if admin:
            L.pg.wait_for_timeout(300)
            da = L.js("const p = sr.querySelector('tobibox-panel'); return !!p && !!p.shadowRoot && p.shadowRoot.textContent.includes('Lernmodus')")
            L.pruefe(da, "lernmodus", "Technik › Tobies zeigt den Lernmodus für Administratoren nicht")
        else:
            L.pruefe(L.da('[data-zustand="nur-admin"]') and "Lernmodus" not in L.js("return sr.querySelector('main').textContent"), "lernmodus", "Benutzer sieht den Lernmodus")




def ablauf_eingang(L: Lauf):
    """A11b: Band, Punkt am Reiter und die Karte „bitte kurz ansehen“ nur über echte Klicks. Läuft als letzter Ablauf: „Das ist richtig“ ändert die Serie `pruef`."""
    with L.schritt("eingang-band-laeuft"):
        L.gehe("#bibliothek")
        L.eingang_setzen("laeuft2")
        text = L.js("return sr.querySelector('[data-eingang-band]').textContent.replace(/\\s+/g, ' ').trim()")
        L.pruefe(text == "2 Einträge werden gerade hinzugefügt.", "eingang-band", f"Bandtext {text!r}")
        L.pruefe(L.js("return sr.querySelector('[data-eingang-band]').getAttribute('role')") == "status", "eingang-band", "Band ohne role=status")
        hoehe = L.js("return sr.querySelector('[data-eingang-band] a').getBoundingClientRect().height")
        L.pruefe(hoehe >= 43.5, "eingang-band", f"Band nur {hoehe:.1f} px hoch")
        zum_reiter(L, "start")
        L.pruefe(L.da("nav.tabs a[href='#bibliothek'] .dot.ruhig"), "eingang-punkt", "Ruhiger Punkt am Reiter „Bibliothek“ fehlt auf dem Start")
        L.pruefe(not L.da("[data-eingang-band]"), "eingang-band", "Das Band steht auch auf dem Start")
        zum_reiter(L, "bibliothek")
        L.klick("[data-eingang-band] a")
        L.pruefe(L.hash() == "#hinzufuegen", "eingang-band", f"Tipp auf das Band führt nach {L.hash()}")
    with L.schritt("eingang-karte"):
        zum_reiter(L, "bibliothek")  # nach dem Klick auf das Band steht die Seite auf „Hinzufügen“; das Band gibt es nur in der Bibliothek
        L.eingang_setzen("pruefen1")
        L.pruefe(L.js("return sr.querySelector('[data-eingang-band]').textContent.includes('1 neuer Eintrag bitte kurz ansehen.')"), "eingang-band", "Band „bitte kurz ansehen“ fehlt")
        L.pruefe(not L.da("nav.tabs a[href='#bibliothek'] .dot"), "eingang-punkt", "Punkt bei „bitte kurz ansehen“ (nur ein laufender Upload soll ihn zeigen)")
        L.gehe("#serie-pruef")
        L.warte_da("[data-karte=ansehen] [data-daraus]")
        daraus = L.js("return sr.querySelector('[data-daraus]').textContent")
        L.pruefe(daraus == "Daraus ist geworden: Hörspiel „Bibi Blocksberg“ · 1 Folge", "eingang-karte", f"Daraus: {daraus!r}")
        L.klick("[data-richtig]")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('[data-karte=ansehen]')", timeout=6000)
        L.pruefe("Danke" in L.toast(), "eingang-karte", f"Meldung: {L.toast()!r}")
        zum_reiter(L, "bibliothek")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('[data-eingang-band=pruefen]')", timeout=6000)
        L.messe("ablauf-eingang-bestaetigt")


def ablauf_eingang_liste(L: Lauf):
    """A11b Teil 2 (zugleich Rest von A14-1c): die Liste „Zuletzt hinzugefügt“ aus `eingang/list` nur über echte Klicks. Einträge vom NAS in allen Zuständen
    (wird einsortiert, geht nicht, bitte kurz ansehen, fertig) mit „vom NAS“ und den Gründen; „Das ist richtig“; „Erledigte ausblenden“ (nur dieses Gerät);
    ein Upload ist eine Zeile (nicht zwei); Neuladen mitten im Hochladen: „Unterbrochen. Wähle die Datei noch einmal.“ und weiter mit derselben Gruppe."""
    import tempfile

    karten = "[data-liste='zuletzt'] [data-eintrag]"
    anzahl = f"() => window.__el.shadowRoot.querySelectorAll(\"{karten}\").length"

    def karten_lesen():
        return L.js("return [...sr.querySelectorAll(x)].map((k) => ({ phase: k.dataset.phase, quelle: k.querySelector('[data-quelle]')?.textContent.trim() ?? null, text: k.textContent.replace(/\\s+/g, ' ').trim() }))", karten)

    with L.schritt("liste-nas"):
        L.gehe("#hinzufuegen")
        L.mock("/eingang", {"zustand": "nas"})
        L.pg.wait_for_function("() => window.__el.shadowRoot.querySelectorAll(\"[data-liste='zuletzt'] [data-eintrag][data-quelle='nas']\").length === 4", timeout=8000)
        L.ruhe()
        k = [x for x in karten_lesen() if x["quelle"] == "vom NAS"]  # Karten früherer Abläufe (eigene Uploads) stehen auch in der Liste
        L.pruefe(sorted(x["phase"] for x in k) == ["fehler", "fertig", "pruefen", "sortieren"], "liste-nas", f"Zustände der Karten: {[x['phase'] for x in k]}")
        L.pruefe(all(x["quelle"] == "vom NAS" for x in k), "liste-nas", f"„vom NAS“ fehlt: {[x['quelle'] for x in k]}")
        t = {x["phase"]: x["text"] for x in k}
        L.pruefe("Wird einsortiert …" in t.get("sortieren", ""), "liste-nas", f"„Wird einsortiert …“ fehlt: {t.get('sortieren')!r}")
        L.pruefe("Diese Datei ist kopiergeschützt" in t.get("fehler", "") and "Nimm eine Datei ohne Kopierschutz." in t.get("fehler", ""), "liste-nas", f"Grund und nächste Handlung fehlen: {t.get('fehler')!r}")
        L.pruefe("In der Datei steht kein Albumname" in t.get("pruefen", "") and "Daraus ist geworden: Neuer Eintrag „Bibi Blocksberg“" in t.get("pruefen", ""), "liste-nas", f"Gründe und „Daraus ist geworden“ fehlen: {t.get('pruefen')!r}")
        L.pruefe("Daraus ist geworden: „Kleine Reise“ · 1 neue Folge" in t.get("fertig", ""), "liste-nas", f"Daraus bei „fertig“: {t.get('fertig')!r}")
        L.pruefe(all(("Anders einsortieren" in x["text"]) == (x["phase"] in ("pruefen", "fertig")) for x in k), "liste-nas", "„Anders einsortieren …“ gehört nur zu „bitte ansehen“ und „fertig“ (A11c)")
        L.pruefe(L.js("return [...sr.querySelectorAll(\"[data-phase='pruefen'] .btns .btn\")].map((b) => b.textContent.trim()).join('|')") == "Ansehen|Das ist richtig|Anders einsortieren …", "liste-nas", "Knöpfe der Karte „bitte ansehen“")
        L.messe("liste-nas")
    with L.schritt("liste-richtig"):
        L.klick("[data-phase='pruefen'] [data-richtig]")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector(\"[data-phase='pruefen']\")", timeout=6000)
        L.ruhe()
        L.pruefe("Danke" in L.toast(), "liste-richtig", f"Meldung: {L.toast()!r}")
        L.pruefe(L.js("return sr.querySelectorAll(\"[data-quelle='nas'][data-phase='fertig']\").length") == 2, "liste-richtig", "Die bestätigte Karte steht nicht mehr als „fertig“ da")
        L.pruefe(L.js("return !!sr.activeElement?.closest?.(\"[data-phase='fertig']\")"), "liste-richtig", "Fokus nach „Das ist richtig“ nicht auf der Karte")
        zum_reiter(L, "bibliothek")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('[data-eingang-band=pruefen]')", timeout=6000)
        L.gehe("#hinzufuegen")
    with L.schritt("liste-ausblenden"):
        L.pruefe(L.js("return sr.querySelector('[data-erledigte-hinweis]')") is None, "liste-ausblenden", "Ein Hinweissatz steht da, obwohl nichts ausgeblendet ist (AM17)")
        voll = L.js("return sr.querySelectorAll(x).length", karten)
        erledigte = L.js("return sr.querySelectorAll(x + \"[data-phase='fertig']\").length", karten)
        L.klick("[data-erledigte-aus]")
        L.pruefe(L.js("return sr.querySelectorAll(x).length", karten) == voll - erledigte and L.js("return sr.querySelectorAll(x + \"[data-phase='fertig']\").length", karten) == 0, "liste-ausblenden", "Erledigte sind nicht ausgeblendet")
        L.pruefe(f"{erledigte} erledigte Einträge sind ausgeblendet." in L.js("return sr.querySelector('[data-erledigte-hinweis]').textContent"), "liste-ausblenden", "Hinweis zu den ausgeblendeten")
        L.messe("liste-ausgeblendet")
        L.klick("[data-erledigte-aus]")
        L.pruefe(L.js("return sr.querySelectorAll(x).length", karten) == voll, "liste-ausblenden", "„Erledigte zeigen“ bringt sie nicht zurück")
        L.mock("/eingang", {"zustand": "leer"})
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector(\"[data-liste='zuletzt'] [data-quelle='nas']\")", timeout=8000)
    with L.schritt("liste-dateien"):
        # Befund aus dem echten HA: „geht nicht“ und „teilweise“ nennen die Dateien (Namen je Grund, „und N weitere“), lange Namen brechen um
        L.mock("/eingang", {"zustand": "dateien"})
        L.pg.wait_for_function("() => window.__el.shadowRoot.querySelectorAll(\"[data-liste='zuletzt'] [data-quelle='nas'] [data-gruppe]\").length >= 4", timeout=8000)
        L.ruhe()
        fe = L.js("const k = sr.querySelector(\"[data-liste='zuletzt'] [data-phase='fehler'][data-quelle='nas']\"); return { gruppen: [...k.querySelectorAll('[data-gruppe]')].map((g) => ({ satz: g.querySelector('[data-grund]').textContent.trim(), namen: [...g.querySelectorAll('[data-datei]')].map((d) => d.textContent.trim()), weitere: g.querySelector('[data-weitere]')?.textContent.trim() ?? null })) }")
        kaputt = [g for g in fe["gruppen"] if g["satz"].startswith("Die Datei ist kaputt")]
        L.pruefe(len(fe["gruppen"]) == 2 and len(kaputt) == 1, "liste-dateien", f"Zwei Gründe erwartet: {fe}")
        L.pruefe(bool(kaputt) and len(kaputt[0]["namen"]) == 3 and kaputt[0]["weitere"] == "und 1 weitere", "liste-dateien", f"Drei Namen und „und 1 weitere“ erwartet: {kaputt}")
        L.pruefe(bool(kaputt) and "Felix - Briefe von Felix/Briefe von Felix.mp3" in kaputt[0]["namen"] and "Anderer Ordner/Briefe von Felix.mp3" in kaputt[0]["namen"], "liste-dateien", f"Gleiche Dateinamen brauchen den Ordner davor: {kaputt}")
        L.messe("liste-dateien-nicht")
        te = L.js("const k = sr.querySelector(\"[data-liste='zuletzt'] [data-phase='pruefen'][data-quelle='nas'] [data-liegt-noch]\")?.closest('[data-eintrag]'); return k ? { text: k.textContent.replace(/\\s+/g, ' ').trim(), rest: k.querySelectorAll('[data-liegt-noch] [data-gruppe]').length, richtig: !!k.querySelector('[data-richtig]') } : null")
        L.pruefe(te is not None and "Daraus ist geworden: Hörspiel „Bibi Blocksberg“" in te["text"] and "Liegt noch im Eingang:" in te["text"] and te["rest"] == 2 and "Geschuetzt.m4b" in te["text"], "liste-dateien", f"Karte „teilweise“: {te}")
        L.pruefe(te is not None and not te["richtig"], "liste-dateien", "Bei „teilweise“ gibt es kein „Das ist richtig“")
        L.messe("liste-dateien-teilweise")
        L.mock("/eingang", {"zustand": "leer"})
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector(\"[data-liste='zuletzt'] [data-quelle='nas']\")", timeout=8000)
    with L.schritt("liste-neuladen"):
        with tempfile.TemporaryDirectory(prefix="tb-hz2-") as tmp:
            tmp = Path(tmp)
            drei = hz_dateien(tmp, ["11 Der Leuchtturm.mp3", "12 Die Welle.mp3", "13 Der Nebel.mp3"])
            L.aufraeumen()
            meine = lambda: [x for x in karten_lesen() if "Leuchtturm" in x["text"]]  # Karten dieses Ablaufs (frühere Abläufe lassen eigene Karten stehen)
            hz_waehlen(L, "[data-dateien-waehlen]", drei)
            L.klick('dialog[open] [data-ziel="neu"]')
            L.pg.locator("dialog[open] #hz-name").fill("Sturmgeschichten")
            L.klick("dialog[open] .knoepfe button.primary")
            L.pg.wait_for_function("() => /Datei 2 von 3/.test(window.__el.shadowRoot.querySelector('[data-liste=\"zuletzt\"] [data-status]')?.textContent ?? '')", timeout=15000)
            L.pruefe(len(meine()) == 1, "liste-doppelt", "Ein Upload ist eine Zeile")
            L.pg.reload()
            L.pg.wait_for_function("() => window.__el && window.__el.shadowRoot && window.__el.shadowRoot.querySelector('main') && window.__mess", timeout=15000)
            L.ruhe()
            L.gehe("#hinzufuegen")
            L.warte_da("[data-liste='zuletzt'] [data-phase='fehlt']")
            k = [x for x in meine() if x["phase"] == "fehlt"]
            L.pruefe(len(k) == 1 and len(meine()) == 1, "liste-neuladen", f"Nach dem Neuladen eine Karte „fehlt“ erwartet: {meine()}")
            L.pruefe(bool(k) and "Unterbrochen. Wähle die Datei noch einmal." in k[0]["text"] and "Es fehlt noch eine Datei." in k[0]["text"], "liste-neuladen", f"Text: {k and k[0]['text']!r}")
            L.messe("liste-unterbrochen")
            for _ in range(3):  # jede Wahl schickt eine Datei; die Gruppe ist komplett, wenn nichts „Unterbrochen“ mehr zeigt
                if not L.da("[data-liste='zuletzt'] [data-fehlende]"):
                    break
                hz_waehlen(L, "[data-liste='zuletzt'] [data-fehlende]", [drei[1]])
                L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector(\"[data-liste='zuletzt'] [data-phase='hochladen'], [data-liste='zuletzt'] [data-phase='wartet']\")", timeout=15000)
            L.pg.wait_for_function("() => { const s = window.__el.shadowRoot; return !s.querySelector(\"[data-liste='zuletzt'] [data-phase='hochladen'], [data-liste='zuletzt'] [data-phase='wartet'], [data-liste='zuletzt'] [data-phase='sortieren'], [data-liste='zuletzt'] [data-phase='fehlt']\"); }", timeout=20000)
            L.ruhe()
            L.pruefe(len(meine()) == 1 and meine()[0]["phase"] in ("fertig", "pruefen"), "liste-neuladen", f"Nach dem Weitersenden ist es eine Zeile, einsortiert: {meine()}")
            L.pruefe(L.js("return el.store.s.lokaleUploads") == 0, "liste-neuladen", "Das Band zählt noch einen Upload, obwohl alles einsortiert ist")
            ups = L.mock("/zustand")["uploads"]
            L.pruefe(len({u["gruppe"] for u in ups if u["name"] == "Sturmgeschichten"}) == 1, "liste-neuladen", "Dieselbe Gruppe nach dem Neuladen")


def ablauf_anders_einsortieren(L: Lauf):
    """A11c „Anders einsortieren …“ nur über echte Klicks. Karte „bitte ansehen“ vom NAS: Knopf, Blatt „Was ist das?“ (dieselben vier Kacheln wie beim Hochladen, Zeile zum NAS,
    „Neu einsortieren“), danach „Wird einsortiert …“ und das Ergebnis über das Ereignis `eingang`. Ein Eintrag, an dem schon etwas geändert wurde: der Text aus 6.1, Blatt zu.
    Auf der Serienseite steht der Punkt als erster im Menü „Das stimmt nicht“."""
    karten = "[data-liste='zuletzt'] [data-eintrag]"

    def phase(name):
        return L.js("return [...sr.querySelectorAll(x[0])].find((k) => k.textContent.includes(x[1]))?.dataset.phase ?? null", [karten, name])

    with L.schritt("anders-knopf"):
        L.gehe("#hinzufuegen")
        L.mock("/eingang", {"zustand": "anders"})
        L.pg.wait_for_function("() => window.__el.shadowRoot.querySelectorAll(\"[data-liste='zuletzt'] [data-quelle='nas']\").length >= 3", timeout=8000)
        L.ruhe()
        knoepfe = L.js("const k = [...sr.querySelectorAll(x)].find((k) => k.textContent.includes('Bibi-Ordner')); return [...k.querySelectorAll('.btns .btn')].map((b) => b.textContent.trim())", karten)
        L.pruefe(knoepfe == ["Ansehen", "Das ist richtig", "Anders einsortieren …"], "anders-knopf", f"Knöpfe der Karte „bitte ansehen“: {knoepfe}")
        fertig = L.js("const k = [...sr.querySelectorAll(x)].find((k) => k.textContent.includes('Sommerlieder')); return [...k.querySelectorAll('.btns .btn')].map((b) => b.textContent.trim())", karten)
        L.pruefe(fertig == ["Öffnen", "Anders einsortieren …"], "anders-knopf", f"Knöpfe der Karte „fertig“: {fertig}")
        groesse = L.js("const b = sr.querySelector('[data-anders]').getBoundingClientRect(); return [b.width, b.height]")
        L.pruefe(groesse[1] >= 44, "anders-knopf", f"Knopf kleiner als 44 px: {groesse}")
        L.messe("anders-karten")
    with L.schritt("anders-blatt"):
        L.pg.locator("[data-liste='zuletzt'] [data-eintrag]", has_text="Bibi-Ordner").locator("[data-anders]").click(timeout=4000)
        L.warte_da("dialog.blatt[open] [data-kacheln]")
        L.ruhe()
        titel = L.js("return sr.querySelector('dialog.blatt[open] #blatt-t')?.textContent.trim()")
        zeile = L.js("return sr.querySelector('dialog.blatt[open] [data-gewaehlt]')?.textContent.trim()")
        L.pruefe(titel == "Was ist das?", "anders-blatt", f"Titel: {titel!r}")
        L.pruefe(zeile == "3 Dateien im Eingang vom NAS. Was ist das?", "anders-blatt", f"Zeile: {zeile!r}")
        L.pruefe(L.js("return sr.querySelectorAll('dialog.blatt[open] [data-kachel]').length") == 3 and not L.da('dialog[open] [data-ziel="auto"]'), "anders-blatt", "Es sollen drei Kacheln sein, ohne „Sortier du“")
        L.messe("anders-blatt")
        L.klick('dialog[open] [data-ziel="neu"]')
        L.pruefe(L.js("return sr.querySelector('dialog.blatt[open] #hz-name')?.value") == "Bibi Blocksberg", "anders-blatt", "Der Name ist nicht vorbelegt")
        knoepfe = L.js("return [...sr.querySelectorAll('dialog.blatt[open] .knoepfe button')].map((b) => b.textContent.trim())")
        L.pruefe(knoepfe == ["Abbrechen", "Ändern", "Neu einsortieren"], "anders-blatt", f"Knöpfe der Vorschau: {knoepfe}")
        L.messe("anders-vorschau")
    with L.schritt("anders-senden"):
        L.pg.locator("dialog[open] #hz-name").fill("Bibi und Tina")
        L.klick("dialog[open] .knoepfe button.primary")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog.blatt[open]')", timeout=6000)
        L.pg.wait_for_function("() => [...window.__el.shadowRoot.querySelectorAll(\"[data-liste='zuletzt'] [data-eintrag]\")].some((k) => k.textContent.includes('Bibi-Ordner') && k.dataset.phase === 'sortieren')", timeout=6000)
        L.ruhe()
        t = L.js("return [...sr.querySelectorAll(x)].find((k) => k.textContent.includes('Bibi-Ordner'))?.textContent.replace(/\\s+/g, ' ').trim()", karten)
        L.pruefe(t is not None and "Wird einsortiert …" in t and "Anders einsortieren" not in t, "anders-senden", f"Karte nach dem Senden: {t!r}")
        L.messe("anders-laeuft")
        L.pg.wait_for_function("() => [...window.__el.shadowRoot.querySelectorAll(\"[data-liste='zuletzt'] [data-eintrag]\")].some((k) => k.textContent.includes('Bibi-Ordner') && k.dataset.phase === 'fertig')", timeout=8000)
        L.ruhe()
        t = L.js("return [...sr.querySelectorAll(x)].find((k) => k.textContent.includes('Bibi-Ordner'))?.textContent.replace(/\\s+/g, ' ').trim()", karten)
        L.pruefe(t is not None and "Daraus ist geworden: Hörspiel „Bibi und Tina“" in t, "anders-senden", f"Ergebnis: {t!r}")
        L.messe("anders-fertig")
    with L.schritt("anders-nicht-moeglich"):
        L.pg.locator("[data-liste='zuletzt'] [data-eintrag]", has_text="Geändertes Hörspiel").locator("[data-anders]").click(timeout=4000)
        L.warte_da("dialog.blatt[open] [data-kacheln]")
        L.klick('dialog[open] [data-ziel="einzeln"]')
        L.klick("dialog[open] .knoepfe button.primary")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog.blatt[open]')", timeout=6000)
        L.pg.wait_for_function("() => /anders einsortieren/.test(window.__el.shadowRoot.querySelector('.toast.err .tmsg')?.textContent ?? '')", timeout=6000)
        L.ruhe()
        fehler = L.js("return sr.querySelector('.toast.err .tmsg')?.textContent ?? ''")
        L.pruefe(fehler.startswith("Das lässt sich nicht mehr anders einsortieren"), "anders-nicht-moeglich", f"Fehlertext: {fehler!r}")
        L.pruefe(phase("Geändertes Hörspiel") == "pruefen", "anders-nicht-moeglich", f"Die Karte soll bleiben, wie sie war: {phase('Geändertes Hörspiel')!r}")
        L.messe("anders-nicht-moeglich")
    with L.schritt("anders-serie"):
        L.mock("/eingang", {"zustand": "anders"})
        L.pg.wait_for_function("() => window.__el.shadowRoot.querySelectorAll(\"[data-liste='zuletzt'] [data-quelle='nas']\").length >= 3", timeout=8000)
        L.gehe("#serie-pruef")
        L.warte_da("[data-stimmt-nicht]")
        L.klick("[data-stimmt-nicht]")
        L.warte_da("dialog.blatt[open] [data-menue]")
        punkte = L.js("return [...sr.querySelectorAll('dialog.blatt[open] [data-menue]')].map((b) => b.dataset.menue)")
        L.pruefe(punkte and punkte[0] == "anders", "anders-serie", f"„Anders einsortieren …“ soll der erste Punkt sein: {punkte}")
        L.messe("anders-menue")
        L.klick('dialog[open] [data-menue="anders"]')
        L.warte_da("dialog.blatt[open] [data-kacheln]")
        L.pruefe(L.js("return sr.querySelector('dialog.blatt[open] #blatt-t')?.textContent.trim()") == "Was ist das?", "anders-serie", "Das Blatt „Was ist das?“ öffnet sich nicht")
        L.klick("dialog[open] [data-blatt-oben]")
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog.blatt[open]')", timeout=6000)
    L.mock("/eingang", {"zustand": "leer"})


def ablauf_papierkorb(L: Lauf):
    """A14-1c: Papierkorb nur über echte Klicks. Als Nicht-Administrator: Eintrag in den Papierkorb mit der Rückfrage („Der Administrator bekommt eine Mitteilung und kann
    es zurückholen.“), Meldung; „Letzte Stunde zurückholen“ ist Administratorsache (Technik), der Benutzer sieht die Sperre. Als Administrator: „Letzte Stunde zurückholen“ mit Rückfrage.
    Läuft zuletzt: die Serie `kurz` ist danach im Papierkorb."""
    admin = L.job["rolle"] == "admin"
    with L.schritt("korb-serie"):
        L.gehe("#serie-kurz")
        name = L.js("return sr.querySelector('main h2')?.textContent.trim()")
        L.klick("[data-menue-serie]")
        L.klick('dialog [data-menue="papierkorb"]')
        satz = L.js("return sr.querySelector('dialog[open]')?.textContent.replace(/\\s+/g, ' ')") or ""
        L.pruefe("Der Administrator sieht es und kann es zurückholen." in satz, "korb-serie", f"Die Rückfrage nennt die Mitteilung nicht: {satz!r}")
        L.messe("korb-rueckfrage")
        L.klick("dialog[open] .knoepfe .btn.danger")
        L.warte_hash("#bibliothek")
        L.pruefe(f"„{name}“ ist im Papierkorb." in L.toast(), "korb-serie", f"Meldung: {L.toast()!r} (Name {name!r})")
        L.gehe("#serie-kurz")
        L.pruefe(not L.da("[data-menue-serie]"), "korb-serie", "Die Serie im Papierkorb ist noch zu öffnen")
    with L.schritt("korb-letzte-stunde"):
        L.gehe("#technik-speicher")
        if not admin:
            L.pruefe(L.da('[data-zustand="nur-admin"]') and not L.da('[data-aktion="letzte_stunde"]'), "korb-letzte-stunde", "Der Benutzer sieht „Letzte Stunde zurückholen“")
            return
        L.warte_da('[data-aktion="letzte_stunde"]')
        # BB2: die Karte „Papierkorb“ zeigt zuerst nur die neuesten 5 Einträge und steht unter der Karte „Hördaten“
        L.warte_da('[data-liste="papierkorb"]')
        zeilen = L.js("return sr.querySelectorAll('[data-liste=\"papierkorb\"] [data-korb]').length")
        L.pruefe(zeilen == 5, "korb-kurz", f"Die Karte zeigt {zeilen} statt 5 Einträge")
        knopf = L.js("return sr.querySelector('[data-korb-alle]')?.textContent.trim() ?? ''")
        L.pruefe(bool(re.match(r"^Alle \d+ zeigen$", knopf)), "korb-kurz", f"Knopf „Alle <n> zeigen“ fehlt: {knopf!r}")
        if L.da('[data-karte="hoerdaten"]'):
            L.pruefe(L.js("const h = sr.querySelector('[data-karte=\"hoerdaten\"]'), k = sr.querySelector('[data-karte=\"papierkorb\"]'); return !!(h.compareDocumentPosition(k) & Node.DOCUMENT_POSITION_FOLLOWING)"), "korb-kurz", "Die Karte „Hördaten“ steht nicht über dem Papierkorb")
        L.klick("[data-korb-alle]")
        zeilen = L.js("return sr.querySelectorAll('[data-liste=\"papierkorb\"] [data-korb]').length")
        L.pruefe(zeilen > 5, "korb-kurz", f"Nach „Alle zeigen“ nur {zeilen} Einträge")
        L.klick('[data-aktion="letzte_stunde"]')
        L.pruefe("Alles, was in der letzten Stunde in den Papierkorb kam" in (L.js("return sr.querySelector('dialog[open]')?.textContent") or ""), "korb-letzte-stunde", "Rückfrage fehlt")
        L.klick("dialog[open] .knoepfe .btn.primary")
        L.pg.wait_for_function("() => /zurückgeholt\\./.test(window.__el.shadowRoot.querySelector('.toast:not(.err) .tmsg')?.textContent ?? '')", timeout=6000)
        L.pruefe(bool(re.match(r"^\d+ Eintr(?:ag|äge) zurückgeholt\.$", L.toast())), "korb-letzte-stunde", f"Meldung: {L.toast()!r}")


def ablauf_papierkorb_punkt(L: Lauf):
    """AC3: Punkt am Technik-Symbol und Hinweis „Neu im Papierkorb“. Eine andere Person legt etwas in den Papierkorb (`/korb` im Mock-Server): der Administrator
    sieht den Punkt (Kopf, am Computer in der Seitenleiste), der Benutzer nichts. Nach dem Besuch von „Technik › Speicher“ ist der Punkt weg; der Hinweis steht oben."""
    admin = L.job["rolle"] == "admin"
    punkt = '[data-punkt="papierkorb"]'
    with L.schritt("korb-punkt"):
        L.gehe("#start")
        L.pruefe(not L.da(punkt), "korb-punkt", "Punkt am Technik-Symbol, obwohl nichts Neues im Papierkorb liegt")
        L.mock("/korb", {"anzeige": "Folge vom Besuch", "von": "Person B"})
        if not admin:
            L.pg.wait_for_timeout(600)
            L.ruhe()
            L.pruefe(not L.da(punkt) and not L.da("a.rund.tech"), "korb-punkt", "Der Benutzer sieht den Punkt am Technik-Symbol")
            return
        L.warte_da(punkt)
        ziel = L.js("return sr.querySelector('[data-punkt=\"papierkorb\"]')?.closest('a')?.className ?? ''")
        L.pruefe(("srow" in ziel) if L.job["layout"] == "seite" else ("rund" in ziel), "korb-punkt", f"Der Punkt sitzt nicht am Technik-Symbol ({ziel!r}, Layout {L.job['layout']})")
        L.messe("korb-punkt")
    with L.schritt("korb-hinweis"):
        L.gehe("#technik-speicher")
        L.warte_da("[data-korb-neu]")
        text = L.js("return sr.querySelector('[data-korb-neu]')?.textContent.replace(/\\s+/g, ' ') ?? ''")
        L.pruefe("Neu im Papierkorb:" in text and "Person B" in text and "Folge vom Besuch" in text, "korb-hinweis", f"Hinweis unvollständig: {text!r}")
        L.pruefe(not L.da(punkt), "korb-hinweis", "Der Punkt bleibt nach dem Besuch von „Speicher“")
        L.messe("korb-hinweis")
        L.gehe("#start")
        L.pruefe(not L.da(punkt), "korb-hinweis", "Der Punkt kommt nach dem Besuch zurück")


# ------------------------------------------------------------------ A6m: Bewegung der Seiten (Messung 7 vom 14.11.)
BEW_AUFZEICHNEN = """
if (!window.__bew) {
  const B = window.__bew = { calls: [], vt: 0 };
  const alt = Element.prototype.animate;
  if (alt) Element.prototype.animate = function (kf, opts) {
    const an = alt.call(this, kf, opts);
    B.calls.push({ el: this, kf: JSON.parse(JSON.stringify(kf)), an, bg0: this.style ? this.style.backgroundImage.slice(0, 14) : null, bild0: this.dataset ? this.dataset.bild : null });
    return an;
  };
  const vt = document.startViewTransition;
  document.startViewTransition = function (...a) { B.vt += 1; return vt ? vt.apply(document, a) : { ready: Promise.resolve(), finished: Promise.resolve() }; };
}
window.__bew.calls.length = 0;
return true;
"""

# Misst einen Cover-Flug Bild für Bild. Der Flug läuft mit einem Klon in der obersten Schicht (Befund Tobias 14.11.: in der Liste malten Nachbarzeilen über das
# fliegende Cover). x = { klick: Selektor des Links, start: Selektor des Covers vorher (sonst das Cover im Link), istZiel: JS-Ausdruck über e und x (e = Klon),
# ziel: Selektor des echten Covers am Ziel (`{id}` wird ersetzt) }. Je Bild: liegt der Klon wirklich OBEN (elementFromPoint in seiner Mitte), und gibt es ein Bild,
# in dem weder der Klon noch das echte Cover zu sehen ist (Lücke)?
BEW_FLUG = """
const B = window.__bew;
B.calls.length = 0;
const radius = (c) => { const cs = getComputedStyle(c); const [a, b] = cs.borderTopLeftRadius.split(' ');
  const m = cs.transform === 'none' ? new DOMMatrix() : new DOMMatrix(cs.transform);
  return { x: (parseFloat(a) || 0) * m.a, y: (parseFloat(b ?? a) || 0) * m.d }; };
const rechteck = (c) => { const r = c.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; };
const link = sr.querySelector(x.klick);
const vonEl = x.start ? sr.querySelector(x.start) : link.querySelector('.cover');
const start = rechteck(vonEl); const radStart = radius(vonEl).x;
const id = x.id ?? link.dataset.serie;
const zielEl = () => sr.querySelector(x.ziel.replace('{id}', id));
link.click();
const t0 = performance.now();
const istZiel = new Function('e', 'x', 'return ' + x.istZiel);
const hat = () => B.calls.find((c) => c.el.dataset.flugklon === '1' && /translate\\(/.test(JSON.stringify(c.kf)) && istZiel(c.el, x));
let flug = null;
while (performance.now() - t0 < 2500 && !flug) { await new Promise((r) => requestAnimationFrame(r)); flug = hat(); }
if (!flug) return { flug: false, vt: B.vt };
const proben = [];
const sichtbar = (e) => !!e && e.isConnected && getComputedStyle(e).visibility !== 'hidden';
const t1 = performance.now();
const probe = () => {
  const r = rechteck(flug.el); const z = zielEl();
  const mx = (r.l + r.r) / 2; const my = (r.t + r.b) / 2;
  const pe = flug.el.style.pointerEvents; flug.el.style.pointerEvents = 'auto'; // der Klon fängt keine Eingaben ab (N17); für die Messung der Schichten kurz an
  const hit = sr.elementFromPoint(mx, my); const oben = !!hit && flug.el.contains(hit); // der Klon oder sein Buchstabe
  flug.el.style.pointerEvents = pe;
  proben.push({ ...r, vis: radius(flug.el).x, oben, luecke: !sichtbar(flug.el) && !sichtbar(z), klonDa: flug.el.isConnected });
};
while (flug.el.isConnected && flug.an.playState !== 'finished' && flug.an.playState !== 'idle' && performance.now() - t1 < 1500) {
  probe();
  await new Promise((r) => requestAnimationFrame(r));
}
for (let i = 0; i < 3; i += 1) { await new Promise((r) => requestAnimationFrame(r)); const z = zielEl(); proben.push({ nachher: true, luecke: !sichtbar(flug.el) && !sichtbar(z) }); }
const z = zielEl();
const ende = z ? rechteck(z) : null;
const ziel = z ? parseFloat(getComputedStyle(z).borderTopLeftRadius) || 0 : 0;
const imFlug = proben.filter((p) => !p.nachher);
return { flug: true, start, ende, radStart, radZiel: ziel, proben: imFlug, luecken: proben.filter((p) => p.luecke).length, vt: B.vt, kf: flug.kf,
  stil: { klonDa: flug.el.isConnected, zielSichtbar: sichtbar(z), tf: z ? getComputedStyle(z).transform : null, pe: z ? z.style.pointerEvents : null, ueberlagerLetzter: (flug.el.parentNode && flug.el.parentNode.host) ? 'shadow' : (flug.el.parentNode ? flug.el.parentNode.className : null) } };
"""

BEW_BLATT = """
const B = window.__bew;
B.calls.length = 0;
const knopf = sr.querySelector(x.knopf);
knopf.click();
const t0 = performance.now();
const tops = []; let d = null;
while (performance.now() - t0 < 900) {
  await new Promise((r) => requestAnimationFrame(r));
  d = sr.querySelector('dialog[open]');
  if (d) { const r = d.getBoundingClientRect(); tops.push(r.top); }
}
d = sr.querySelector('dialog[open]');
const r = d ? d.getBoundingClientRect() : null;
const w = sr.querySelector('.hinten');
return { da: !!d, tops, endTop: r ? r.top : null, hoehe: r ? r.height : null, imHinten: d ? d.closest('.hinten') !== null : null,
  hinten: w ? getComputedStyle(w).transform : null, klip: w ? getComputedStyle(w).clipPath : null, hell: w ? getComputedStyle(w).filter : null,
  vt: B.vt, mitTransform: B.calls.filter((c) => c.kf.some((k) => 'transform' in k)).length };
"""


def jsa(L: Lauf, code, arg=None):
    """Wie `L.js`, aber der Code darf `await` benutzen (Messungen Bild für Bild)."""
    return L.pg.evaluate("([a, x]) => { const el = window.__el, sr = el.shadowRoot; const AF = Object.getPrototypeOf(async function () {}).constructor; return (new AF('el', 'sr', 'x', a))(el, sr, x); }", [code, arg])


def bew_start(L: Lauf):
    L.js(BEW_AUFZEICHNEN)


def ablauf_bewegung(L: Lauf):
    """A6m, Prüfung: Cover-Flug (Messung 7 h1, h2), Blatt ohne Sprung und iOS-Effekt (h4), „weniger Bewegung“. Chromium sieht, was auf dem iPhone auffiel."""
    L.gehe("#bibliothek")
    if not L.da("a.lrow[data-serie], a.rcard[data-serie]"):
        return  # leere Bibliothek: nichts, was fliegen könnte
    bew_start(L)
    with L.schritt("bewegung-flug-hin"):
        L.gehe("#bibliothek")
        r = jsa(L, BEW_FLUG, {"klick": "a.lrow[data-serie], a.rcard[data-serie]", "istZiel": "e.classList.contains('se-xl')", "ziel": ".cover.se-xl"})
        L.ruhe()
        flug_pruefen(L, r, "hin")
        L.pruefe(r["vt"] == 0, "bewegung-flug-hin", "startViewTransition wurde aufgerufen")
        id_ = L.hash().removeprefix("#serie-")
    with L.schritt("bewegung-flug-zurueck"):
        r = jsa(L, BEW_FLUG, {"klick": "a[data-zurueck]", "start": ".cover.se-xl", "id": id_, "istZiel": "!e.classList.contains('se-xl') && e.dataset.cover === x.id", "ziel": "a[data-serie=\"{id}\"] .cover[data-cover]"})
        L.ruhe()
        flug_pruefen(L, r, "zurueck")
        L.pruefe(r["vt"] == 0, "bewegung-flug-zurueck", "startViewTransition wurde aufgerufen")
    for ziel, knopf in (("bibliothek-sortieren", "[data-sortieren]"),):
        with L.schritt(f"bewegung-blatt-{ziel}"):
            L.aufraeumen()
            L.gehe("#bibliothek")
            hoch = L.job.get("layout") == "unten"
            r = jsa(L, BEW_BLATT, {"knopf": knopf})
            L.pruefe(r["da"], "bewegung-blatt", "Blatt nicht offen")
            if r["da"]:
                grenze = 0.02 * r["hoehe"] + 3
                zu_hoch = max((r["endTop"] - t for t in r["tops"]), default=0)
                L.pruefe(zu_hoch <= grenze, "bewegung-blatt", f"Blatt liegt beim Öffnen {zu_hoch:.0f} px über seinem Endpunkt (erlaubt {grenze:.0f}): es springt")
                L.pruefe(r["imHinten"] is False, "bewegung-blatt", "Das Blatt steckt in der verkleinerten Fläche (.hinten)")
                if hoch:
                    L.pruefe(r["hinten"].startswith("matrix(0.94,") and r["hinten"].endswith(")"), "bewegung-blatt", f"Seite hinter dem Blatt: {r['hinten']!r}, erwartet matrix(0.94 …)")
                    L.pruefe("round" in r["klip"] or "inset" in r["klip"], "bewegung-blatt", f"Seite hinter dem Blatt ohne runde Ecken: {r['klip']!r}")
                    L.pruefe("brightness(0.8)" in r["hell"], "bewegung-blatt", f"Seite hinter dem Blatt nicht abgedunkelt: {r['hell']!r}")
                else:
                    L.pruefe(r["hinten"] in (None, "none"), "bewegung-blatt", f"Ab 700 px darf die Seite nicht skaliert werden: {r['hinten']!r}")
            L.js("el.schliesseBlatt('x')")
            L.pg.wait_for_timeout(900)
            L.pruefe(L.js("return getComputedStyle(sr.querySelector('.hinten')).transform") == "none", "bewegung-blatt", "Seite hinter dem Blatt nach dem Schließen nicht wieder ohne transform")
            L.pruefe(not L.da("dialog"), "bewegung-blatt", "Dialog noch im DOM")
    with L.schritt("bewegung-reduziert"):
        L.pg.emulate_media(reduced_motion="reduce")
        try:
            L.gehe("#bibliothek")
            L.pruefe(L.js("return getComputedStyle(el).getPropertyValue('--dauer-feder').trim()") == "150ms", "bewegung-reduziert", "--dauer-feder ist bei „weniger Bewegung“ nicht 150ms")
            r = jsa(L, BEW_BLATT, {"knopf": "[data-sortieren]"})
            L.pruefe(r["da"] and r["mitTransform"] == 0, "bewegung-reduziert", f"Animation mit transform trotz „weniger Bewegung“ ({r['mitTransform']})")
            L.pruefe(r["hinten"] in (None, "none"), "bewegung-reduziert", f"Seite hinter dem Blatt skaliert: {r['hinten']!r}")
            L.js("el.schliesseBlatt('x')")
            L.pg.wait_for_timeout(500)
            r = L.js("""
              const aus = [];
              for (const e of sr.querySelectorAll('*')) { const t = getComputedStyle(e).transitionProperty; if (/\\b(transform|all)\\b/.test(t)) aus.push(e.localName + '.' + (e.className?.baseVal ?? e.className) + ': ' + t); }
              return aus.slice(0, 5);""")
            L.pruefe(not r, "bewegung-reduziert", f"transform in transition-property: {r}")
            L.js("window.__bew.calls.length = 0")
            r = jsa(L, BEW_FLUG, {"klick": "a.lrow[data-serie], a.rcard[data-serie]", "istZiel": "e.classList.contains('se-xl')", "ziel": ".cover.se-xl"})
            L.pruefe(r["flug"] is False, "bewegung-reduziert", "Cover fliegt trotz „weniger Bewegung“")
        finally:
            L.pg.emulate_media(reduced_motion="no-preference")


def flug_pruefen(L: Lauf, r, richtung):
    z = f"bewegung-flug-{richtung}"
    if not L.pruefe(r["flug"], z, "Kein Cover-Flug (animate mit translate am Klon fehlt)"):
        return
    s, e = r["start"], r["ende"]
    if not L.pruefe(e is not None, z, "Das echte Cover am Ziel fehlt nach dem Flug"):
        return
    kasten = {"l": min(s["l"], e["l"]), "t": min(s["t"], e["t"]), "r": max(s["r"], e["r"]), "b": max(s["b"], e["b"])}
    tol = 4 + 0.03 * max(kasten["r"] - kasten["l"], kasten["b"] - kasten["t"])  # Feder schwingt etwa 1,5 % über das Ziel
    abw = max([0] + [max(kasten["l"] - p["l"], kasten["t"] - p["t"], p["r"] - kasten["r"], p["b"] - kasten["b"]) for p in r["proben"]])
    L.pruefe(abw <= tol, z, f"Der Flug verlässt den Kasten aus Start und Ziel um {abw:.0f} px (erlaubt {tol:.0f})")
    lo, hi = min(r["radStart"], r["radZiel"]) - 2, max(r["radStart"], r["radZiel"]) + 2
    schlecht = [p["vis"] for p in r["proben"] if not lo <= p["vis"] <= hi]
    L.pruefe(not schlecht, z, f"Sichtbarer Eckenradius springt aus [{lo:.1f}, {hi:.1f}]: {[round(v, 1) for v in schlecht[:4]]}")
    if r["proben"]:
        L.pruefe(abs(r["proben"][-1]["vis"] - r["radZiel"]) <= 1.5 or len(r["proben"]) < 2, z, f"Ecke im letzten Bild {r['proben'][-1]['vis']:.1f} px, Ziel {r['radZiel']:.1f} px")
    # Befund Tobias 14.11.: der Flug zurück lief hinter den Zeilen der Liste. Der Klon muss in jedem Bild OBEN liegen (elementFromPoint in seiner Mitte), und es darf kein
    # Bild geben, in dem weder der Klon noch das echte Cover zu sehen ist.
    unten = [i for i, p in enumerate(r["proben"]) if not p["oben"]]
    L.pruefe(not unten, z, f"Der fliegende Klon liegt in {len(unten)} von {len(r['proben'])} Bildern NICHT oben (elementFromPoint liefert etwas anderes)")
    L.pruefe(r["luecken"] == 0, z, f"{r['luecken']} Bilder, in denen weder der Klon noch das echte Cover zu sehen ist")
    L.pruefe(not r["stil"]["klonDa"] and r["stil"]["zielSichtbar"] and r["stil"]["tf"] == "none", z, f"Nach dem Flug nicht aufgeräumt: {r['stil']}")


# ------------------------------------------------------------------ Befunde Tobias 14.11. (A6m auf dem iPhone): Druck-Rückmeldung, Seitenwechsel
BEW_DRUCK = """
// Hält den Finger auf dem Ziel (Touch über CDP wäre echter; hier genügt der Zeigerzustand `:active` über das Playwright-Mausereignis): misst bei jedem Bild die
// Hintergrundfarbe der Zeile, bis sie weg ist. Die Farbe darf sich nie ändern.
const zeile = sr.querySelector(x.sel);
const zu = [];
const farbe = () => getComputedStyle(zeile).backgroundColor;
window.__druck = { vorher: farbe(), proben: zu, laeuft: true };
const t0 = performance.now();
const schritt = () => {
  if (zeile.isConnected && getComputedStyle(zeile).display !== 'none') zu.push(farbe());
  if (performance.now() - t0 < 1500 && window.__druck.laeuft) requestAnimationFrame(schritt);
};
requestAnimationFrame(schritt);
const r = zeile.getBoundingClientRect();
return { x: r.left + r.width / 2, y: r.top + Math.min(r.height / 2, 30) };
"""

BEW_OPAK = """
// Misst `main` und seine Kinder bei jedem Bild: kleinste Deckkraft und Bilder mit leerem Inhalt (weder Text noch Platzhalter), solange die Anzeige wechselt.
const m = sr.querySelector('main');
const t0 = performance.now();
const o = { min: 1, leer: 0, bilder: 0 };
window.__opak = o;
const schritt = () => {
  const mm = sr.querySelector('main');
  if (mm) {
    let mi = Number(getComputedStyle(mm).opacity);
    for (const k of mm.children) mi = Math.min(mi, Number(getComputedStyle(k).opacity));
    for (const a of mm.getAnimations({ subtree: true })) { const t = a.effect && a.effect.getComputedTiming(); if (t && a.playState === 'running' && a.effect.target && !a.effect.target.hasAttribute('data-gross-schicht')) { const v = Number(getComputedStyle(a.effect.target).opacity); if (!Number.isNaN(v)) mi = Math.min(mi, v); } }
    o.min = Math.min(o.min, mi);
    o.bilder += 1;
    if (!mm.textContent.trim() && !mm.querySelector('.skel, svg, img, .cover')) o.leer += 1;
  }
  if (performance.now() - t0 < x.ms) requestAnimationFrame(schritt); else o.fertig = true;
};
requestAnimationFrame(schritt);
return true;
"""


def ablauf_druck(L: Lauf):
    """Befund 2 (Tobias 14.11.): Eine Zeile oder Kachel, die zu einer anderen Seite führt, darf beim Drücken keine Hintergrundfarbe bekommen (sie blitzte vor dem
    Seitenwechsel auf, und iOS lässt :active hängen). Gemessen am Telefon-Layout mit gedrücktem Zeiger: die Hintergrundfarbe bleibt in jedem Bild gleich."""
    if L.job.get("layout") != "unten":
        return  # am Computer gilt der Hover (Maus), kein Drücken mit dem Finger
    for name, hash_, sel in (("lrow", "#bibliothek", "a.lrow[data-serie]"), ("tile", "#start", ".reihe a.tile[data-serie]"), ("qt", "#start", "a.qt[data-serie]")):
        with L.schritt(f"druck-{name}"):
            L.gehe(hash_)
            if not L.da(sel):
                continue
            pos = jsa(L, BEW_DRUCK, {"sel": sel})
            L.pg.mouse.move(pos["x"], pos["y"])
            L.pg.mouse.down()
            L.pg.wait_for_timeout(250)  # gedrückt gehalten: hier stand früher die Farbe
            r = L.js("return window.__druck")
            L.pruefe(len(set(r["proben"])) <= 1 and (not r["proben"] or r["proben"][0] == r["vorher"]), f"druck-{name}",
                     f"Hintergrund der Zeile ändert sich beim Drücken: vorher {r['vorher']}, gemessen {sorted(set(r['proben']))}")
            L.pg.mouse.up()  # der Klick führt zur Serie
            L.pg.wait_for_timeout(300)
            L.js("window.__druck.laeuft = false")
            r = L.js("return window.__druck")
            L.pruefe(len(set(r["proben"])) <= 1, f"druck-{name}", f"Hintergrund ändert sich im Bild vor dem Seitenwechsel: {sorted(set(r['proben']))}")
            L.ruhe()


def ablauf_seitenwechsel(L: Lauf):
    """Befund 3 (Tobias 14.11.): Seitenwechsel flackerten (neuer Inhalt begann bei Deckkraft 0, alter verschwand vor dem neuen, Platzhalter blitzten auf). Gemessen werden
    `main` und seine Kinder in jedem Bild bei Reiterwechsel sowie Serienseite öffnen und schließen: nie unter 0,5, nie ein leerer Hauptteil."""
    schritte = [("reiter-bibliothek", "#start", lambda: L.klick("nav a[href='#bibliothek']")),
                ("reiter-start", "#bibliothek", lambda: L.klick("nav a[href='#start']")),
                ("reiter-tobies", "#start", lambda: L.klick("nav a[href='#tobies']")),
                ("serie-auf", "#bibliothek", lambda: L.klick("a.lrow[data-serie], a.rcard[data-serie]")),
                ("serie-zu", None, lambda: L.klick("a[data-zurueck]"))]
    for name, start, tu in schritte:
        with L.schritt(f"wechsel-{name}"):
            if start:
                L.gehe(start)
            if not L.da("nav a[href='#bibliothek'], aside nav a[href='#bibliothek']"):
                return
            if name.startswith("serie") and name == "serie-auf" and not L.da("a.lrow[data-serie], a.rcard[data-serie]"):
                return
            L.js(BEW_OPAK, {"ms": 900})
            if name.startswith("reiter") and L.job.get("layout") == "seite":
                sel = {"reiter-bibliothek": "bibliothek", "reiter-start": "start", "reiter-tobies": "tobies"}[name]
                L.klick(f"aside nav a[href='#{sel}']")
            else:
                tu()
            L.pg.wait_for_function("() => window.__el.shadowRoot && window.__opak && window.__opak.fertig", timeout=5000)
            o = L.js("return window.__opak")
            L.pruefe(o["min"] >= 0.5, f"wechsel-{name}", f"Die Deckkraft von main fällt auf {o['min']:.2f} (erlaubt: nie unter 0,5, sonst ein leeres Bild)")
            L.pruefe(o["leer"] <= 1, f"wechsel-{name}", f"{o['leer']} Bilder mit leerem Hauptteil (erlaubt: höchstens eins)")
            L.ruhe()
    with L.schritt("wechsel-reduziert"):
        L.pg.emulate_media(reduced_motion="reduce")
        try:
            L.gehe("#start")
            L.js(BEW_OPAK, {"ms": 500})
            L.gehe("#bibliothek")
            L.pg.wait_for_function("() => window.__opak && window.__opak.fertig", timeout=5000)
            o = L.js("return window.__opak")
            L.pruefe(o["min"] >= 0.999, "wechsel-reduziert", f"Bei „weniger Bewegung“ blendet die Seite trotzdem über (Deckkraft bis {o['min']:.2f})")
        finally:
            L.pg.emulate_media(reduced_motion="no-preference")


# ------------------------------------------------------------------ A8b, A8e, A8m: Player (echter Ton, Range, Wischen, Sperre, Cover-Flug)
BEW_PLAYER_FLUG = """
// Cover-Flug der Vollansicht, Bild für Bild: `x.knopf` wird geklickt, der Klon (data-flugklon) wird verfolgt.
const B = window.__bew; B.calls.length = 0;
const mini = () => sr.querySelector('.mini .mopen .cover');
const rechteck = (c) => { const r = c.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; };
const sichtbar = (e) => !!e && e.isConnected && getComputedStyle(e).visibility !== 'hidden';
const start = x.auf ? rechteck(mini()) : rechteck(sr.querySelector('dialog.player .pin > .cover'));
const grossEl = () => sr.querySelector('dialog.player .pin > .cover');
sr.querySelector(x.knopf).click();
const t0 = performance.now();
let flug = null;
while (performance.now() - t0 < 2500 && !flug) { await new Promise((r) => requestAnimationFrame(r)); flug = B.calls.find((c) => c.el.dataset.flugklon === '1' && /translate\\(/.test(JSON.stringify(c.kf))); }
if (!flug) return { flug: false, vt: B.vt, mitTransform: B.calls.filter((c) => c.kf.some((k) => 'transform' in k && /translate|scale/.test(k.transform))).length };
const proben = []; let luecken = 0; const t1 = performance.now();
const ziel = () => (x.auf ? grossEl() : mini());
// AM14: in jedem Bild trägt der Klon ein Bild (`url(`) und zeigt keine Ersatzkachel (`.bst` sichtbar)
const bildDa = (e) => !!e && /url\\(/.test(getComputedStyle(e).backgroundImage);
const bstZu = (e) => !!e && [...e.querySelectorAll('.bst')].some((b) => getComputedStyle(b).visibility !== 'hidden');
const quelleBild = bildDa(x.auf ? mini() : grossEl()); // war am Start schon ein Bild da?
const bildProben = [];
const probe = () => {
  bildProben.push({ klonBild: bildDa(flug.el), klonBst: bstZu(flug.el), zielBst: bstZu(ziel()) && sichtbar(ziel()) });
  const r = rechteck(flug.el);
  const pe = flug.el.style.pointerEvents; flug.el.style.pointerEvents = 'auto'; // der Klon fängt keine Eingaben ab (N17); für die Messung der Schichten kurz an
  const hit = sr.elementFromPoint((r.l + r.r) / 2, (r.t + r.b) / 2); const oben = !!hit && flug.el.contains(hit);
  flug.el.style.pointerEvents = pe;
  const luecke = !sichtbar(flug.el) && !sichtbar(ziel()) && !(x.auf ? false : sr.querySelector('dialog.player'));
  proben.push({ ...r, oben, luecke });
};
while (flug.el.isConnected && flug.an.playState !== 'finished' && flug.an.playState !== 'idle' && performance.now() - t1 < 1500) { probe(); await new Promise((r) => requestAnimationFrame(r)); }
for (let i = 0; i < 4; i += 1) { await new Promise((r) => requestAnimationFrame(r)); if (!sichtbar(flug.el) && !sichtbar(ziel())) luecken += 1; }
luecken += proben.filter((p) => p.luecke).length;
const z = ziel();
return { flug: true, quelleBild, bildProben, zielBild: bildDa(z), zielBst: bstZu(z), vt: B.vt, start, ende: z ? rechteck(z) : null, proben, luecken, klonDa: flug.el.isConnected, zielSichtbar: sichtbar(z),
  miniSichtbar: sichtbar(mini()), dialogDa: !!sr.querySelector('dialog.player'), tf: z ? getComputedStyle(z).transform : null };
"""

BEW_AUDIO = """
const a = sr.querySelector('audio');
return a ? { da: true, t: a.currentTime, pausiert: a.paused, src: a.getAttribute('src'), dauer: a.duration, fehler: a.error ? a.error.code : null, rate: a.playbackRate } : { da: false };
"""


def audio_stand(L: Lauf):
    return L.js(BEW_AUDIO)


def touch_wischen(L: Lauf, x, y0, y1, schritte=8):
    """Wischen mit echten Touch-Ereignissen (CDP `Input.dispatchTouchEvent`), nur im Telefon-Layout."""
    cdp = L.pg.context.new_cdp_session(L.pg)
    try:
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y0}]})
        for i in range(1, schritte + 1):
            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y0 + (y1 - y0) * i / schritte}]})
            L.pg.wait_for_timeout(16)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    finally:
        cdp.detach()


def maus_wischen(L: Lauf, x, y0, y1, schritte=8):
    L.pg.mouse.move(x, y0)
    L.pg.mouse.down()
    for i in range(1, schritte + 1):
        L.pg.mouse.move(x, y0 + (y1 - y0) * i / schritte)
        L.pg.wait_for_timeout(12)
    L.pg.mouse.up()


def player_start(L: Lauf):
    """Reinhören starten und warten, bis wirklich Ton läuft (echter Chromium, Testdatei vom Server, signierter Pfad über audio/bereit). Die Serie ist die erste der
    Bibliothek (frühere Abläufe löschen und benennen Serien um, eine feste Kennung wäre nicht sicher)."""
    L.gehe("#bibliothek")
    L.warte_da("a.lrow[data-serie], a.rcard[data-serie]")
    sid = L.js("return sr.querySelector('a.lrow[data-serie], a.rcard[data-serie]').dataset.serie")
    L.gehe(f"#serie-{sid}")
    L.warte_da("[data-reinhoeren]")
    L.klick("[data-reinhoeren]")
    L.pg.wait_for_function("() => { const a = window.__el.shadowRoot.querySelector('audio'); return a && a.currentTime > 0.4 && !a.paused; }", timeout=8000)
    L.ruhe()


def player_aus(L: Lauf):
    """Wiedergabe anhalten und den Player wegräumen (Leiste bleibt bis zum Neuladen; die Abläufe danach stören sich nicht daran)."""
    L.js("const a = sr.querySelector('audio'); if (a) a.pause(); el.spieler.gesperrt = false; if (el.spieler.offen) { el.spieler.schliessen('knopf'); }")
    L.pg.wait_for_timeout(700)


def ablauf_player(L: Lauf):
    """A8b, A8e, A14-2: Reinhören mit echtem Ton, Springen (Range), Wischen auf und zu (Maus, Touch), Neuladen und Weiterhören, Fehler 503 → neues audio/bereit, Sperre mit
    Halten (1,5 s nicht, 2,2 s ja)."""
    L.gehe("#bibliothek")
    if not L.da("a.lrow[data-serie], a.rcard[data-serie]"):
        return
    telefon = L.job.get("layout") == "unten"
    k = f"{L.job['profil']}~{L.job['kennung']}"
    with L.schritt("player-start"):
        player_start(L)
        a = audio_stand(L)
        L.pruefe(a["da"] and a["src"] and "/api/tobibox/audio/" in a["src"] and "authSig=" in a["src"], "player-start", f"src ist kein signierter Pfad: {a}")
        L.pruefe(a["fehler"] is None, "player-start", f"Der Ton lässt sich nicht laden: Fehler {a['fehler']}")
        L.pruefe(L.js("return !sr.querySelector('.mini').hidden && sr.querySelector('.mini .mt').textContent.length > 0"), "player-start", "Leiste fehlt")
        bereit = L.pg.evaluate("async (k) => (await (await fetch(`/aufrufe?k=${encodeURIComponent(k)}&typ=tobibox/audio/bereit`)).json())", k)
        L.pruefe(bereit and "folge" in bereit[0] and "folge_id" not in bereit[0], "player-start", f"audio/bereit ohne `folge`: {bereit[:1]}")
    with L.schritt("player-voll-springen"):
        L.klick(".mini .mopen")
        L.warte_da("dialog.player[open] .pslider")
        L.pg.wait_for_timeout(700)
        L.pruefe(L.js("return el.hasAttribute('data-voll')"), "player-voll", "data-voll fehlt am Host")
        t0 = audio_stand(L)["t"]
        L.klick('dialog.player [data-p="fwd"]')
        L.pg.wait_for_timeout(600)
        t1 = audio_stand(L)["t"]
        L.pruefe(t1 >= t0 + 25, "player-springen", f"+30 s: {t0:.1f} → {t1:.1f}")
        z = L.pg.evaluate("async (k) => (await (await fetch('/audio-zaehler')).json())", k)
        L.pruefe(any(x["range"] for x in z), "player-springen", "Kein Abruf mit Range (Springen braucht 206)")
        L.klick('dialog.player [data-p="back"]')
        L.pg.wait_for_timeout(400)
        L.pruefe(audio_stand(L)["t"] < t1 - 20, "player-springen", "−30 s ging nicht")
        L.js("el.spieler.tempo = 1")
        L.messe("player-voll")
    with L.schritt("player-sperre"):
        L.klick('dialog.player [data-p="lock"]')
        L.pg.wait_for_selector('dialog.player [data-p="unlock"]')
        aus = L.js("return [...sr.querySelectorAll('dialog.player button, dialog.player input')].filter((b) => !b.matches('[data-p=unlock]') && !b.disabled).map((b) => b.getAttribute('aria-label') || b.className)")
        L.pruefe(not aus, "player-sperre", f"Bedienelemente nicht gesperrt: {aus}")
        L.pruefe(L.js("return sr.querySelector('#p-ansicht').textContent") == "Gesperrt", "player-sperre", "Titel der Ansicht heißt nicht „Gesperrt“")
        L.pg.keyboard.press("Escape")
        L.pg.wait_for_timeout(300)
        L.pruefe(L.da("dialog.player[open]"), "player-sperre", "Esc schließt die gesperrte Vollansicht")
        L.messe("player-gesperrt")
        box = L.pg.locator('dialog.player [data-p="unlock"]').bounding_box()
        mx, my = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        L.pg.mouse.move(mx, my)
        L.pg.mouse.down()
        L.pg.wait_for_timeout(1500)
        L.pruefe(L.js("return el.spieler.gesperrt"), "player-sperre", "1,5 s Halten entsperrt schon")
        L.pg.mouse.up()
        L.pg.wait_for_timeout(300)
        L.pg.mouse.down()
        L.pg.wait_for_timeout(2400)
        L.pg.mouse.up()
        L.pg.wait_for_timeout(300)
        L.pruefe(not L.js("return el.spieler.gesperrt"), "player-sperre", "2,4 s Halten entsperrt nicht")
        L.ruhe()
    with L.schritt("player-wischen"):
        L.pruefe(L.da("dialog.player[open]"), "player-wischen", "Vollansicht nicht offen")
        h = L.pg.viewport_size["height"]
        w = L.pg.viewport_size["width"]
        (touch_wischen if telefon else maus_wischen)(L, w / 2, h * 0.30, h * 0.30 + 40)  # zu kurz (unter 70 px)
        L.pg.wait_for_timeout(700)
        L.pruefe(L.da("dialog.player[open]"), "player-wischen", "Ein Wisch unter 70 px schließt schon")
        for art, f in (("maus", maus_wischen), ("touch", touch_wischen)):
            if art == "touch" and not telefon:
                continue
            f(L, w / 2, h * 0.25, h * 0.25 + 320)
            L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog.player')", timeout=3000)
            L.pruefe(L.js("return !sr.querySelector('.mini .cover').closest('.hebt')"), "player-wischen", f"Mini-Cover nach dem Wischen ({art}) nicht wieder sichtbar")
            # Wischen nach oben in der Leiste öffnet; nach unten tut nichts
            mb = L.pg.locator(".mini .mopen").bounding_box()
            cx, cy = mb["x"] + 80, mb["y"] + mb["height"] / 2
            f(L, cx, cy, cy + 40)
            L.pg.wait_for_timeout(500)
            L.pruefe(not L.da("dialog.player"), "player-wischen", f"Wischen nach unten in der Leiste ({art}) öffnet")
            L.pg.wait_for_timeout(300)
            f(L, cx, cy, cy - 90)
            L.pg.wait_for_selector("dialog.player[open]", timeout=3000)
            L.pg.wait_for_timeout(700)
        L.pruefe(L.da("dialog.player[open]"), "player-wischen", "Wischen nach oben öffnet nicht")
        # Knopf bleibt: Antippen von „Player schließen“
        L.klick('dialog.player [data-p="close"]')
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog.player')", timeout=3000)
    with L.schritt("player-fehler"):
        # die nächsten Abrufe der Datei antworten mit 503: <audio> meldet nur „Format error“, die Seite fragt per audio/bereit neu und spielt trotzdem
        n0 = len(L.pg.evaluate("async (k) => (await (await fetch(`/aufrufe?k=${encodeURIComponent(k)}&typ=tobibox/audio/bereit`)).json())", k))
        L.pg.evaluate("async ([ab, k]) => { await (await fetch('/audio-fehler', { method: 'POST', body: JSON.stringify({ n: 2, ab, k }) })).text(); }", [n0 + 1, k])  # nur Abrufe mit der nächsten (neuen) Signatur scheitern
        L.klick('.mini .mplay')  # Pause
        L.js("const sp = el.spieler; sp._laden(sp.s.serie, sp.s.i, 0, 0, { auto: true })")  # dieselbe Folge noch einmal laden (die erste Serie hat vielleicht nur eine Folge)
        L.pg.wait_for_function("() => { const a = window.__el.shadowRoot.querySelector('audio'); return a && a.currentTime > 0.3 && !a.paused; }", timeout=9000)
        for _ in range(24):  # die Wiederholungen nach dem Fehler brauchen etwas Zeit (jede fragt neu, Antwort, Laden, Fehler)
            n1 = len(L.pg.evaluate("async (k) => (await (await fetch(`/aufrufe?k=${encodeURIComponent(k)}&typ=tobibox/audio/bereit`)).json())", k))
            if n1 >= n0 + 2:
                break
            L.pg.wait_for_timeout(250)
        stand = L.js("const sp = el.spieler; const a = sr.querySelector('audio'); return { z: sp.zustand, v: sp._versuche, q: sp._quelle, g: sp._geladen, ser: sp.s && sp.s.serie.id, f: sp.folge && sp.folge.name, art: sp.folge && sp.folge.art, err: a && a.error && a.error.code, t: a && a.currentTime, p: a && a.paused, src: a && a.getAttribute('src') }")
        L.pruefe(n1 >= n0 + 2, "player-fehler", f"Nach dem 503 kein neues audio/bereit: {n0} → {n1}; Stand {stand}")
        L.pruefe(not L.toast() and not L.da(".toast.err"), "player-fehler", "Der einzelne Fehler zeigt eine Meldung")
    with L.schritt("player-neuladen"):
        L.klick(".mini .mplay") if not audio_stand(L).get("pausiert", True) else None
        L.pg.wait_for_timeout(500)
        titel = L.js("return sr.querySelector('.mini .mt').textContent")
        pos = audio_stand(L)["t"]
        L.pg.wait_for_timeout(500)  # `hoerstelle/set` ist beim Server angekommen
        L.pg.reload()
        L.pg.wait_for_function("() => window.__el && window.__el.shadowRoot && window.__el.shadowRoot.querySelector('main') && window.__mess", timeout=15000)
        L.pg.wait_for_function("() => { const m = window.__el.shadowRoot.querySelector('.mini'); return m && !m.hidden; }", timeout=8000)
        L.ruhe()
        L.pruefe(L.js("return sr.querySelector('.mini .mt').textContent") == titel, "player-neuladen", "Nach dem Neuladen steht ein anderer Titel in der Leiste")
        a = audio_stand(L)
        L.pruefe(not a["da"] or a["pausiert"], "player-neuladen", "Nach dem Neuladen spielt schon Ton")
        L.klick(".mini .mplay")
        L.pg.wait_for_function("() => { const a = window.__el.shadowRoot.querySelector('audio'); return a && !a.paused && a.currentTime > 0.2; }", timeout=9000)
        L.pruefe(audio_stand(L)["t"] >= min(pos, 30) - 3, "player-neuladen", f"Weiterhören nicht an der Stelle (vorher {pos:.1f}, jetzt {audio_stand(L)['t']:.1f})")
        L.messe("player-mini")
    with L.schritt("player-start-reihe"):
        L.js("sr.querySelector('audio').pause()")
        L.gehe("#start")
        L.pg.wait_for_selector('[data-reihe="weiterhoeren"] .wh', timeout=6000)
        L.pruefe(L.js("return sr.querySelectorAll('[data-reihe=weiterhoeren] .playov').length") >= 1, "player-start-reihe", "Kein Abspielknopf in der Reihe „Am Handy weiterhören“")
        L.messe("player-start-reihe")
    player_aus(L)


def ablauf_player_bewegung(L: Lauf):
    """A8m: Cover-Flug Mini-Player ↔ Vollansicht per FLIP mit Klon in der obersten Schicht (Messung 7, Befund Tobias 14.11.): bleibt zwischen Start und Ende, liegt in jedem Bild
    oben, keine Lücke, danach Mini-Cover sichtbar und nichts verschoben; nie startViewTransition; „weniger Bewegung“ ohne Flug."""
    L.gehe("#bibliothek")
    if not L.da("a.lrow[data-serie], a.rcard[data-serie]"):
        return
    bew_start(L)
    with L.schritt("player-flug"):
        player_start(L)
        for richtung, knopf, auf in (("auf", ".mini .mopen", True), ("zu", 'dialog.player [data-p="close"]', False)):
            r = jsa(L, BEW_PLAYER_FLUG, {"knopf": knopf, "auf": auf})
            z = f"player-flug-{richtung}"
            if not L.pruefe(r["flug"], z, "Kein Cover-Flug der Vollansicht (animate mit translate am Klon fehlt)"):
                continue
            s, e = r["start"], r["ende"]
            kasten = {"l": min(s["l"], e["l"]), "t": min(s["t"], e["t"]), "r": max(s["r"], e["r"]), "b": max(s["b"], e["b"])}
            tol = 4 + 0.03 * max(kasten["r"] - kasten["l"], kasten["b"] - kasten["t"])
            abw = max([0] + [max(kasten["l"] - p["l"], kasten["t"] - p["t"], p["r"] - kasten["r"], p["b"] - kasten["b"]) for p in r["proben"]])
            L.pruefe(abw <= tol, z, f"Der Flug verlässt den Kasten aus Start und Ziel um {abw:.0f} px (erlaubt {tol:.0f})")
            unten = [p for p in r["proben"] if not p["oben"]]
            L.pruefe(not unten, z, f"Der Klon liegt in {len(unten)} von {len(r['proben'])} Bildern nicht oben")
            L.pruefe(r["luecken"] == 0, z, f"{r['luecken']} Bilder ohne sichtbares Cover")
            L.pruefe(r["vt"] == 0, z, "startViewTransition wurde aufgerufen")
            L.pruefe(not r["klonDa"], z, "Der Klon bleibt nach dem Flug stehen")
            # AM14: Bild nie leer, Ersatzkachel nie zu sehen, solange am Start schon ein Bild da war
            if r["quelleBild"]:
                bp = r["bildProben"]
                L.pruefe(bp and all(p["klonBild"] for p in bp), z, f"Der Klon hat in {sum(1 for p in bp if not p['klonBild'])} von {len(bp)} Bildern kein Hintergrundbild")
                L.pruefe(not any(p["klonBst"] for p in bp), z, f"Die Ersatzkachel (Buchstabe) ist im Klon in {sum(1 for p in bp if p['klonBst'])} von {len(bp)} Bildern zu sehen")
                L.pruefe(not any(p["zielBst"] for p in bp), z, "Die Ersatzkachel des Ziels ist während des Flugs zu sehen")
                L.pruefe(r["zielBild"] and not r["zielBst"], z, "Das Ziel hat nach der Landung kein Bild oder zeigt die Ersatzkachel")
            if richtung == "auf":
                L.pruefe(r["zielSichtbar"] and r["tf"] == "none", z, f"Das große Cover ist nach dem Flug nicht sichtbar/unverschoben: {r['tf']}")
                L.pg.wait_for_timeout(300)
            else:
                L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog.player')", timeout=3000)
                L.pruefe(L.js("const c = sr.querySelector('.mini .mopen .cover'); return getComputedStyle(c).visibility === 'visible' && getComputedStyle(c).transform === 'none'"), z, "Das Mini-Cover ist nach dem Schließen nicht sichtbar oder verschoben")
    with L.schritt("player-flug-reduziert"):
        L.pg.emulate_media(reduced_motion="reduce")
        try:
            r = jsa(L, BEW_PLAYER_FLUG, {"knopf": ".mini .mopen", "auf": True})
            L.pruefe(r["flug"] is False, "player-flug-reduziert", "Cover fliegt trotz „weniger Bewegung“")
            L.pg.wait_for_selector("dialog.player[open]")
            L.pg.wait_for_timeout(400)
            L.klick('dialog.player [data-p="close"]')
            L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog.player')", timeout=3000)
            L.pruefe(L.js("return getComputedStyle(sr.querySelector('.mini .mopen .cover')).visibility") == "visible", "player-flug-reduziert", "Mini-Cover danach nicht sichtbar")
        finally:
            L.pg.emulate_media(reduced_motion="no-preference")
    player_aus(L)


# Misst die RUHE des Ziels beim Cover-Flug (Befund AM5, Tobias 15.11.: das Cover sprang beim Rückflug „ein bisschen unter den Ort und hüpfte dann hin“, weil das Ziel
# gemessen wurde, bevor die Liste fertig stand: Zeilen mit `content-visibility: auto` messen im ersten Bild mit der geschätzten Höhe). Je Bild: Ziel-Rechteck (auch solange
# es `visibility: hidden` ist, und welches Element es ist), dazu das Endrechteck des Klons (aus seinen Schlüsselbildern) und das Ziel nach der Landung. Zusätzlich (AM7):
# das Hintergrundbild des Ziels und des Klons in jedem Bild (nie leer, wenn das kleine Bild schon da war) und der Scrollstand (AM6).
# x = { aus: "klick" | "zurueck-taste", klick: Selektor des Links (sichtbarer zuerst), start, id, istZiel, ziel }.
BEW_FLUG_RUHE = """
const B = window.__bew;
B.calls.length = 0;
const rechteck = (c) => { const r = c.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; };
const scrollStand = () => Math.max(sr.querySelector('.rahmen')?.scrollTop ?? 0, sr.querySelector('.spalte')?.scrollTop ?? 0);
let link = null;
if (x.klick) {
  const alle = [...sr.querySelectorAll(x.klick)].filter((a) => a.querySelector('.cover[data-cover]'));
  const sichtbar = (a) => { const r = a.querySelector('.cover').getBoundingClientRect(); return r.top > 120 && r.bottom < innerHeight - 140 && r.left >= 0 && r.right <= innerWidth; };
  for (let i = 0; i < 60 && !alle.some((a) => sichtbar(a) && a.querySelector('.cover').dataset.bild === '1'); i += 1) await new Promise((r) => setTimeout(r, 50)); // die kleinen Bilder der sichtbaren Zeilen laden
  link = alle.find((a) => sichtbar(a) && a.querySelector('.cover').dataset.bild === '1') ?? alle.find(sichtbar) ?? alle[0];
}
const id = x.id ?? link.dataset.serie;
const zielEl = () => sr.querySelector(x.ziel.replace('{id}', id));
const ids = new WeakMap(); let zaehler = 0;
const kennung = (e) => { if (!e) return 0; if (!ids.has(e)) ids.set(e, ++zaehler); return ids.get(e); };
const scrollVorher = scrollStand();
const kleinDa = link ? link.querySelector('.cover').dataset.bild === '1' : null;
if (x.aus === 'zurueck-taste') history.back(); else (link ?? sr.querySelector(x.knopf)).click();
const t0 = performance.now();
const istZiel = new Function('e', 'x', 'return ' + x.istZiel);
const hat = () => B.calls.find((c) => c.el.dataset.flugklon === '1' && /translate\\(/.test(JSON.stringify(c.kf)) && istZiel(c.el, x));
let flug = null;
while (performance.now() - t0 < 2500 && !flug) { await new Promise((r) => requestAnimationFrame(r)); flug = hat(); }
if (!flug) { const c = zielEl(); return { flug: false, diag: { hash: location.hash, scroll: scrollStand(), top: c ? c.getBoundingClientRect().top : null, hoehe: innerHeight, vorher: scrollVorher } }; }
const tStart = performance.now() - t0;
const k = flug.el;
const zahl = (t, n) => { const m = new RegExp(n + '\\\\(([^)]*)\\\\)').exec(t); return m ? m[1].split(',').map((v) => parseFloat(v)) : null; };
const proben = [];
const t1 = performance.now();
let tLand = null;
const probe = (phase) => { const z = zielEl(); proben.push({ t: Math.round(performance.now() - t1), ab: tLand === null ? null : Math.round(performance.now() - tLand), phase, ziel: z ? rechteck(z) : null, id: kennung(z),
  vis: z ? getComputedStyle(z).visibility : null, bgZiel: z ? getComputedStyle(z).backgroundImage : null, bgKlon: k.isConnected ? getComputedStyle(k).backgroundImage : null }); };
while (k.isConnected && flug.an.playState !== 'finished' && flug.an.playState !== 'idle' && performance.now() - t1 < 1500) { probe('flug'); await new Promise((r) => requestAnimationFrame(r)); }
const kfEnde = flug.an.effect.getKeyframes(); // das Ende der Bahn am Schluss des Flugs (das Ziel darf sie nachführen)
const letzte = kfEnde[kfEnde.length - 1].transform;
const [dx, dy] = zahl(letzte, 'translate') ?? [0, 0];
const [sx, sy = sx] = zahl(letzte, 'scale') ?? [1, 1];
const kl = parseFloat(k.style.left); const kt = parseFloat(k.style.top); const kw = parseFloat(k.style.width); const kh = parseFloat(k.style.height);
const klonEnde = { l: kl + dx, t: kt + dy, r: kl + dx + kw * sx, b: kt + dy + kh * sy };
tLand = performance.now();
while (performance.now() - tLand < 1000) { probe('nach'); await new Promise((r) => requestAnimationFrame(r)); }
return { flug: true, startNachMs: Math.round(tStart), klonEnde, proben, scrollVorher, scrollNachher: scrollStand(), kleinDa, schichten: sr.querySelectorAll('[data-gross-schicht]').length };
"""


def flug_ruhe_messen(L: Lauf, r, z, ausgabe=False, bild=False, scroll=None):
    """Auswertung zu BEW_FLUG_RUHE: (a) das Klon-Endrechteck liegt auf ±1 px auf dem Ziel bei der Landung, (b) das Ziel bewegt sich 500 ms nach der Landung um höchstens 1 px,
    (c) das Ziel ist während des Flugs dasselbe Element und bewegt sich nicht (sonst fliegt der Klon an eine Stelle, die es nicht mehr gibt). `bild` (AM7): in jedem Bild
    hat das Ziel und der Klon ein Hintergrundbild. `scroll` (AM6): der Scrollstand nach der Landung ist der gegebene (±2 px)."""
    if not L.pruefe(r["flug"], z, f"Kein Cover-Flug (animate mit translate am Klon fehlt) {r.get('diag', '')}"):
        return
    pr = r["proben"]
    nach = [p for p in pr if p["phase"] == "nach" and p["ziel"] and p["ab"] <= 500]
    if ausgabe:
        print(z, "Start nach", r["startNachMs"], "ms; Klon-Ende", {k: round(v, 1) for k, v in r["klonEnde"].items()}, "Scroll", r["scrollVorher"], "->", r["scrollNachher"])
        for p in pr[:: max(1, len(pr) // 24)]:
            print("   ", p["phase"], p["t"], "ms Ziel", {k: round(v, 1) for k, v in (p["ziel"] or {}).items()}, "Element", p["id"], p["vis"], (p["bgZiel"] or "")[:30], (p["bgKlon"] or "")[:30])
    if not L.pruefe(nach, z, "Das echte Cover am Ziel fehlt nach der Landung"):
        return
    ende, lk = nach[0]["ziel"], r["klonEnde"]
    off = max(abs(ende[k] - lk[k]) for k in ("l", "t", "r", "b"))
    L.pruefe(off <= 1, z, f"Der Klon landet {off:.1f} px neben dem Ziel (erlaubt 1 px): das Ziel wurde zu früh gemessen")
    sprung = max(max(abs(p["ziel"][k] - ende[k]) for k in ("l", "t", "r", "b")) for p in nach)
    L.pruefe(sprung <= 1, z, f"Das Ziel bewegt sich nach der Landung um {sprung:.1f} px (erlaubt 1 px)")
    im_flug = [p for p in pr if p["phase"] == "flug" and p["ziel"]]
    if im_flug:
        gleich = {p["id"] for p in im_flug} | {nach[0]["id"]}
        L.pruefe(len(gleich) == 1, z, f"Das Ziel wird während des Flugs neu gebaut ({len(gleich)} verschiedene Elemente)")
        flug_sprung = max(max(abs(p["ziel"][k] - ende[k]) for k in ("l", "t", "r", "b")) for p in im_flug)
        L.pruefe(flug_sprung <= 1, z, f"Das Ziel liegt während des Flugs bis zu {flug_sprung:.1f} px neben seinem Endplatz")
    L.pruefe(r["startNachMs"] <= 160, z, f"Der Flug startet erst {r['startNachMs']} ms nach dem Antippen (erlaubt 160 ms)")
    if bild and r["kleinDa"]:
        # der Platzhalter-Farbverlauf (`linear-gradient`) zählt nicht: gesucht ist ein echtes Bild (`url(`)
        leer = [p for p in pr if "url(" not in (p["bgZiel"] or "") or (p["phase"] == "flug" and "url(" not in (p["bgKlon"] or ""))]
        L.pruefe(not leer, z, f"Das große Cover hat in {len(leer)} von {len(pr)} Bildern kein Hintergrundbild (das kleine Bild fehlt als Platzhalter)")
        L.pruefe(r["schichten"] == 0, z, "Die Überblend-Schicht des großen Covers bleibt stehen")
    if scroll is not None:
        L.pruefe(abs(r["scrollNachher"] - scroll) <= 2, z, f"Scrollstand nach dem Zurück {r['scrollNachher']:.0f} px, vor dem Hinflug {scroll:.0f} px (erlaubt ±2 px)")


FLUG_ZURUECK = {"start": ".cover.se-xl", "istZiel": "!e.classList.contains('se-xl') && e.dataset.cover === x.id", "ziel": "a[data-serie=\"{id}\"] .cover[data-cover]"}


def flug_herkunft(L: Lauf, name, hash_, link, scrolle, weg, ausgabe):
    """Eine Herkunft: Seite öffnen, auf `scrolle` px scrollen, ein Cover antippen (Hinflug, AM7: Bild nie leer), Beschriftung und Ziel des Zurück-Knopfs prüfen (AM6), zurück per
    Knopf oder Zurück-Taste (Rückflug ruhig, AM5; Scrollstand wie vorher, AM6)."""
    z = f"flug-ruhe-{name}-{scrolle}-{weg}"
    with L.schritt(z):
        L.gehe(hash_)
        L.warte_da(link)
        L.js("for (const k of [...el._covers.bilder.keys()]) if (k.endsWith(':gross')) el._covers.bilder.delete(k)")  # das große Bild wird neu geholt (der Server liefert es 400 ms später)
        L.js("const s = sr.querySelector(el.getAttribute('data-layout') === 'seite' ? '.spalte' : '.rahmen'); if (s) s.scrollTop = x;", scrolle)
        L.pg.wait_for_timeout(600)
        L.pg.evaluate("() => window.__ruhe()")
        if scrolle:
            L.pg.wait_for_function("(s) => { const sr = window.__el.shadowRoot; const r = sr.querySelector('.rahmen'); const p = sr.querySelector('.spalte'); return Math.max(r?.scrollTop ?? 0, p?.scrollTop ?? 0) > s - 3; }", arg=scrolle - 1 if scrolle > 1 else 0)
        r = jsa(L, BEW_FLUG_RUHE, {"klick": link, "istZiel": "e.classList.contains('se-xl')", "ziel": ".cover.se-xl"})
        L.ruhe()
        flug_ruhe_messen(L, r, z + "-hin", ausgabe, bild=True)
        hin_scroll = r.get("scrollVorher", 0)
        L.pg.wait_for_timeout(800)
        id_ = L.hash().removeprefix("#serie-")
        zk = L.js("const a = sr.querySelector('a[data-zurueck]'); return a ? { text: a.textContent.trim(), href: a.getAttribute('href') } : null")
        erwartet = {"start": ("‹ Start", "#start"), "bibliothek": ("‹ Bibliothek", "#bibliothek")}[name]
        L.pruefe(zk == {"text": erwartet[0], "href": erwartet[1]}, z, f"Zurück-Knopf {zk}, erwartet {erwartet}")
        r = jsa(L, BEW_FLUG_RUHE, {**FLUG_ZURUECK, "id": id_, "aus": "klick" if weg == "knopf" else "zurueck-taste", "knopf": "a[data-zurueck]" if weg == "knopf" else None})
        L.ruhe()
        L.pruefe(L.hash() in (erwartet[1], "") if name == "start" else L.hash() == erwartet[1], z, f"Nach dem Zurück steht {L.hash()!r}, erwartet {erwartet[1]!r}")
        flug_ruhe_messen(L, r, z + "-zurueck", ausgabe, scroll=hin_scroll)


REIHE_NEU = '.hscroll[data-reihe="neu"]'


def flug_reihe(L: Lauf, fall, weg, ausgabe):
    """AM8 und AM9: Start, Reihe „Neu hinzugefügt“. `am8`: eine Serie steht in der Reihe und noch einmal weiter oben (Schnellzugriff); die Kachel der Reihe wird angetippt, der Rückflug
    landet auf ihr (±1 px), nicht auf der oberen. `am9`: die Reihe steht um etwa 300 px nach rechts gescrollt, eine Kachel darin wird angetippt; nach dem Zurück steht die Reihe wieder
    dort (±2 px) und der Rückflug landet auf der angetippten Kachel (nicht: Reihe am Anfang, Ziel außerhalb, kein Flug)."""
    z = f"flug-reihe-{fall}-{weg}"
    with L.schritt(z):
        L.gehe("#start")
        L.warte_da(REIHE_NEU + " a[data-serie]")
        L.js("for (const k of [...el._covers.bilder.keys()]) if (k.endsWith(':gross')) el._covers.bilder.delete(k)")
        # die Serie der zweiten Kachel steht zusätzlich in „Am Handy weiterhören“ (eine Reihe darüber): so gibt es sie zweimal sichtbar auf dem Start
        L.pg.evaluate("""async (reihe) => {
          const sr = window.__el.shadowRoot; const id = sr.querySelectorAll(reihe + ' a[data-serie]')[1].dataset.serie; const c = window.__el.hass.connection;
          const se = await c.sendMessagePromise({ type: 'tobibox/serie/get', serie_id: id });
          await c.sendMessagePromise({ type: 'tobibox/hoerstelle/set', serie_id: id, folge: se.folgen[0].name, position_s: 10, dauer_s: 100 });
          window.__am8Serie = { id, folge: se.folgen[0].name };
        }""", REIHE_NEU)
        L.gehe("#bibliothek")
        L.gehe("#start")
        L.warte_da('.hscroll[data-reihe="weiterhoeren"] a[data-serie]')
        L.js("""const s = sr.querySelector(el.getAttribute('data-layout') === 'seite' ? '.spalte' : '.rahmen'); const w = sr.querySelector('.hscroll[data-reihe="weiterhoeren"]');
          if (s) { s.scrollTop = 0; s.scrollTop = Math.max(0, w.getBoundingClientRect().top - 160); }
          const r = sr.querySelector(x.reihe); r.scrollLeft = x.fall === 'am9' ? 300 : 0;""", {"reihe": REIHE_NEU, "fall": fall})
        L.pg.wait_for_timeout(700)
        L.pg.evaluate("() => window.__ruhe()")
        wahl = L.js("""
          const row = sr.querySelector(x.reihe); const rr = row.getBoundingClientRect();
          const tiles = [...row.querySelectorAll('a[data-serie]')];
          const ganz = (a) => { const c = a.querySelector('.cover').getBoundingClientRect(); return c.left >= Math.max(rr.left, 0) && c.right <= Math.min(rr.right, innerWidth) && c.top > 120 && c.bottom < innerHeight - 60; };
          const imBild = (a) => { const c = a.querySelector('.cover').getBoundingClientRect(); return c.left >= 0 && c.right <= innerWidth && c.top >= 0 && c.bottom <= innerHeight; };
          const andere = (a) => [...sr.querySelectorAll(`a[data-serie="${a.dataset.serie}"]`)].filter((o) => o !== a && imBild(o)).length;
          const a = tiles.find((t) => ganz(t) && (x.fall === 'am8' ? andere(t) > 0 : !sr.querySelectorAll(`a[data-serie="${t.dataset.serie}"]`)[1]));
          return a ? { id: a.dataset.serie, links: row.scrollLeft, index: tiles.indexOf(a) } : { diag: { rr: rr.toJSON(), h: innerHeight, w: innerWidth, t: tiles.map((t) => { const c = t.querySelector('.cover').getBoundingClientRect(); return [Math.round(c.left), Math.round(c.top), Math.round(c.bottom), andere(t)]; }) } };""", {"reihe": REIHE_NEU, "fall": fall})
        if not L.pruefe("id" in wahl, z, f"Keine passende Kachel in der Reihe (am8: Serie auch ausserhalb der Reihe; am9: eigene Kachel im sichtbaren Teil) {wahl}"):
            return
        if fall == "am9":
            L.pruefe(wahl["links"] > 100, z, f"Die Reihe liess sich nicht nach rechts scrollen (scrollLeft {wahl['links']})")
        r = jsa(L, BEW_FLUG_RUHE, {"klick": f'{REIHE_NEU} a[data-serie="{wahl["id"]}"]', "istZiel": "e.classList.contains('se-xl')", "ziel": ".cover.se-xl"})
        L.ruhe()
        flug_ruhe_messen(L, r, z + "-hin", ausgabe, bild=True)
        hin_scroll = r.get("scrollVorher", 0)
        L.pg.wait_for_timeout(800)
        r = jsa(L, BEW_FLUG_RUHE, {**FLUG_ZURUECK, "id": wahl["id"], "aus": "klick" if weg == "knopf" else "zurueck-taste", "knopf": "a[data-zurueck]" if weg == "knopf" else None,
                                   "ziel": REIHE_NEU + ' a[data-serie="{id}"] .cover[data-cover]'})
        L.ruhe()
        L.pruefe(L.hash() in ("#start", ""), z, f"Nach dem Zurück steht {L.hash()!r}, erwartet '#start'")
        flug_ruhe_messen(L, r, z + "-zurueck", ausgabe, scroll=hin_scroll)
        nachher = L.js("return sr.querySelector(x).scrollLeft", REIHE_NEU)
        L.pruefe(abs(nachher - wahl["links"]) <= 2, z, f"Die Reihe steht nach dem Zurück bei {nachher:.0f} px, vorher bei {wahl['links']:.0f} px (erlaubt ±2 px)")
        # aufräumen: die Hörstelle der Prüfung gilt als fertig gehört (fällt aus der Reihe „Am Handy weiterhören“)
        L.pg.evaluate("""async () => { const m = window.__am8Serie; if (m) await window.__el.hass.connection.sendMessagePromise({ type: 'tobibox/hoerstelle/set', serie_id: m.id, folge: m.folge, position_s: 100, dauer_s: 100, fertig: true }); }""")


def ablauf_flug_ruhe(L: Lauf):
    """AM5 bis AM9: Hin- und Rückflug des Covers von Start und Bibliothek, mit laufendem Player (Mini-Leiste), oben und gescrollt, Rückweg per „‹ Start/Bibliothek“ und per
    Zurück-Taste. Das Ziel steht beim Start des Flugs ruhig (AM5), der Knopf heißt nach der Herkunft, der Scrollstand kehrt zurück (AM6), das große Cover hat nie ein leeres Bild (AM7)."""
    L.gehe("#bibliothek")
    if not L.da("a.lrow[data-serie], a.rcard[data-serie]"):
        return
    ausgabe = bool(os.environ.get("TOBIBOX_FLUG_AUSGABE"))
    bew_start(L)
    with L.schritt("flug-ruhe-player-start"):
        player_start(L)
    L.js("el.spieler.offen && el.spieler.schliessen('knopf')")
    L.pg.wait_for_timeout(700)
    # die Leiste bleibt sichtbar, der Ton wird angehalten und zurückgestellt (die Testdatei ist nur 40 s lang, die Abläufe danach starten wieder bei 0)
    L.js("const a = sr.querySelector('audio'); if (a) { a.pause(); a.currentTime = 0; }")
    for name, hash_, link, scrolle in (("bibliothek", "#bibliothek", "a.lrow[data-serie], a.rcard[data-serie]", 0), ("bibliothek", "#bibliothek", "a.lrow[data-serie], a.rcard[data-serie]", 120),
                                       ("bibliothek", "#bibliothek", "a.lrow[data-serie], a.rcard[data-serie]", 900), ("start", "#start", "a.rcard[data-serie], a.qt[data-serie], a.tile[data-serie], a.lrow[data-serie]", 0)):
        for weg in ("knopf", "zurueck-taste"):
            flug_herkunft(L, name, hash_, link, scrolle, weg, ausgabe)
    # Die Reihen der Stufe B (zwei Reihen mehr auf dem Start) verschieben die Reihe „Neu hinzugefügt“ aus dem Bild, das diese Prüfung braucht: ohne Hördaten und Sterne gibt es sie nicht
    L.mock("/gehoert", {"zustand": "leer"})
    try:
        for fall in ("am8", "am9"):
            for weg in ("knopf", "zurueck-taste"):
                flug_reihe(L, fall, weg, ausgabe)
    finally:
        L.mock("/gehoert", {"zustand": "voll"})
    player_aus(L)


def ablauf_serie_zeile(L: Lauf):
    """AM11: Die ganze Folgenzeile der Serienseite ist eine Fläche zum Antippen (Knopf über der Zeile, Name wie der frühere Play-Knopf). Der runde Play-Knopf entfällt; „⋯“ und Tobie-Chips
    bleiben eigene Ziele. Geprüft mit `elementFromPoint`: Zeilenmitte und freie Stelle → Zeilenknopf, „⋯“-Mitte → „⋯“, Chip-Mitte → Chip; der Zeilenknopf deckt die ganze Zeile (±1 px)."""
    with L.schritt("serie-zeile"):
        L.gehe("#serie-lang")
        L.warte_da('[data-folge="f02.mp3"]')
        L.js("sr.querySelector('[data-folge=\"f02.mp3\"]').scrollIntoView({ block: 'center' })")
        L.pg.wait_for_timeout(500)
        r = L.js("""
          const z = sr.querySelector('[data-folge="f02.mp3"]'); const mitte = (e) => { const b = e.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; };
          const treffer = (e) => { const [x, y] = mitte(e); const t = sr.elementFromPoint(x, y); return t ? (t.closest('.se-zeilenknopf, .se-more, .tb-chip, .se-play') || t).className : null; };
          const k = z.querySelector('.se-zeilenknopf'); const zb = z.getBoundingClientRect(); const kb = k ? k.getBoundingClientRect() : null;
          const nm = z.querySelector('.nm'); const chip = z.querySelector('.tb-chip');
          return { play: !!z.querySelector('.se-play'), knopf: !!k, name: k && k.getAttribute('aria-label'),
            deckt: kb && Math.max(Math.abs(kb.left - zb.left), Math.abs(kb.top - zb.top), Math.abs(kb.right - zb.right), Math.abs(kb.bottom - zb.bottom)),
            aufText: treffer(nm), aufMehr: treffer(z.querySelector('.se-more')), aufChip: chip ? treffer(chip) : null, aufDauer: z.querySelector('.se-dauer').offsetParent ? treffer(z.querySelector('.se-dauer')) : null };""")
        L.pruefe(not r["play"], "serie-zeile", "Der runde Play-Knopf (.se-play) steht noch in der Zeile")
        L.pruefe(r["knopf"] and r["deckt"] is not None and r["deckt"] <= 1, "serie-zeile", f"Der Zeilenknopf deckt die Zeile nicht ({r})")
        L.pruefe("abspielen" in (r["name"] or "") or "pausieren" in (r["name"] or ""), "serie-zeile", f"Name des Zeilenknopfs: {r['name']!r}")
        L.pruefe("se-zeilenknopf" in (r["aufText"] or ""), "serie-zeile", f"Ein Tipp auf den Titel trifft {r['aufText']!r}, nicht den Zeilenknopf")
        L.pruefe(r["aufDauer"] is None or "se-zeilenknopf" in r["aufDauer"], "serie-zeile", f"Ein Tipp auf die Dauer trifft {r['aufDauer']!r}, nicht den Zeilenknopf")
        L.pruefe("se-more" in (r["aufMehr"] or ""), "serie-zeile", f"Ein Tipp auf „⋯“ trifft {r['aufMehr']!r}")
        if r["aufChip"] is not None:
            L.pruefe("tb-chip" in r["aufChip"], "serie-zeile", f"Ein Tipp auf den Tobie-Chip trifft {r['aufChip']!r}")
        # AM13: Tipp auf die laufende Folge öffnet die Vollansicht, der Ton läuft weiter
        L.klick('[data-folge="f02.mp3"] .se-zeilenknopf')
        L.pg.wait_for_function("() => { const a = window.__el.shadowRoot.querySelector('audio'); return a && a.currentTime > 0.4 && !a.paused; }", timeout=8000)
        L.pruefe("im Player öffnen" in (L.js("return sr.querySelector('[data-folge=\"f02.mp3\"] .se-zeilenknopf').getAttribute('aria-label')") or ""), "serie-zeile-oeffnen", "Die laufende Folge heisst nicht „im Player öffnen“")
        L.klick('[data-folge="f02.mp3"] .se-zeilenknopf')
        L.pg.wait_for_selector("dialog.player[open]", timeout=4000)
        L.pg.wait_for_timeout(500)
        a = audio_stand(L)
        L.pruefe(L.da("dialog.player[open]") and not a.get("pausiert", True), "serie-zeile-oeffnen", f"Tipp auf die laufende Folge: Vollansicht offen, Ton darf nicht pausiert sein ({a})")
        player_aus(L)


def ablauf_blatt_tastatur(L: Lauf):
    """AM10 (Tobias, iPhone): Das Blatt „Umbenennen“ sitzt bei offener Tastatur direkt über der Tastatur. Die Tastatur wird nachgestellt, indem `visualViewport` der App durch ein Ersatzobjekt
    mit kleinerer Höhe ersetzt wird (das Layout-Viewport bleibt, wie auf dem iPhone). Geprüft: Unterkante des Blatts ≤ Oberkante der Tastatur, Titel, Textfeld und „Speichern“ liegen
    ganz im sichtbaren Teil (auch bei sehr wenig Platz: das Blatt scrollt in sich), danach sitzt das Blatt wieder unten. Nur im Telefon-Layout (unter 700 px)."""
    if L.js("return innerWidth") >= 700:
        return
    with L.schritt("blatt-tastatur"):
        L.gehe("#serie-lang")
        L.warte_da("[data-menue-serie]")
        L.klick("[data-menue-serie]")
        L.klick('dialog [data-menue="name"]')
        L.warte_da("#se-name")
        L.pg.wait_for_timeout(700)
        hoehe = L.js("return innerHeight")
        for tastatur, versatz in ((336, 0), (336, 40), (560, 0)):
            z = f"blatt-tastatur-{tastatur}-{versatz}"
            # Ersatz: der sichtbare Teil beginnt `versatz` px unter dem Seitenanfang und ist `hoehe - tastatur - versatz` hoch; die Tastatur beginnt bei `hoehe - tastatur`
            L.js("el._vvEcht ??= el._vv; el._vv = { height: innerHeight - x.t - x.v, offsetTop: x.v, addEventListener() {}, removeEventListener() {} }; sr.querySelector('#se-name').blur(); sr.querySelector('#se-name').focus();", {"t": tastatur, "v": versatz})
            L.pg.wait_for_timeout(500)
            m = L.js("""
              const d = sr.querySelector('dialog.blatt[open]'); const r = (e) => { const b = e.getBoundingClientRect(); return { t: b.top, b: b.bottom, l: b.left, r: b.right }; };
              return { dialog: r(d), feld: r(sr.querySelector('#se-name')), speichern: r(d.querySelector('.knoepfe .btn.primary')), titel: r(d.querySelector('h2')), kbd: d.hasAttribute('data-kbd'), diag: [el._kbd, el._schmal, !!el._vv, el._vv && el._vv.height, innerHeight, sr.activeElement && sr.activeElement.id, el._layout], scroll: d.scrollTop, hoch: d.scrollHeight > d.clientHeight };""")
            kbd = hoehe - tastatur
            sichtbar_oben = versatz
            L.pruefe(m["kbd"], z, f"Das Blatt weiss nichts von der Tastatur (data-kbd fehlt) {m['diag']}")
            L.pruefe(m["dialog"]["b"] <= kbd + 1, z, f"Unterkante des Blatts {m['dialog']['b']:.0f} px liegt unter der Oberkante der Tastatur {kbd} px")
            L.pruefe(m["dialog"]["t"] >= sichtbar_oben - 1, z, f"Oberkante des Blatts {m['dialog']['t']:.0f} px liegt über dem sichtbaren Teil ({sichtbar_oben} px)")
            for name in ("feld", "speichern"):
                L.pruefe(sichtbar_oben - 1 <= m[name]["t"] and m[name]["b"] <= kbd + 1 and m[name]["b"] <= m["dialog"]["b"] + 1 and m[name]["t"] >= m["dialog"]["t"] - 1, z, f"{name} liegt nicht ganz im sichtbaren Teil des Blatts: {m[name]} (Blatt {m['dialog']}, Tastatur ab {kbd})")
            if tastatur < 500:
                L.pruefe(m["titel"]["t"] >= m["dialog"]["t"] - 1 and m["titel"]["b"] <= kbd + 1, z, f"Titel nicht sichtbar: {m['titel']}")
        # Tastatur zu: das Blatt sitzt wieder ganz unten
        L.js("el._vv = el._vvEcht; sr.querySelector('#se-name').blur();")
        L.pg.wait_for_timeout(500)
        m = L.js("const d = sr.querySelector('dialog.blatt[open]'); return { b: d.getBoundingClientRect().bottom, kbd: d.hasAttribute('data-kbd'), h: innerHeight };")
        L.pruefe(not m["kbd"] and abs(m["b"] - m["h"]) <= 1, "blatt-tastatur-zu", f"Nach dem Schliessen der Tastatur sitzt das Blatt nicht unten ({m})")
        L.js("el.schliesseBlatt('code')")
        L.pg.wait_for_timeout(500)
        L.ruhe()
    # AM18 (Tobias, iPhone): Tipp auf „Speichern“ bei offener Tastatur. Das Blatt sitzt über der (nachgestellten) Tastatur. Der Tipp ist Drücken, Warten, Loslassen: nimmt der Knopf dem Feld den
    # Fokus, geht die Tastatur zu, das Blatt rutscht nach unten, und das Loslassen trifft die Fläche hinter dem Blatt (das Blatt wäre weg, der Name bliebe). Erwartet: gespeichert, Meldung „Gespeichert.“.
    with L.schritt("blatt-tastatur-speichern"):
        L.gehe("#serie-lang")
        L.warte_da("[data-menue-serie]")
        L.klick("[data-menue-serie]")
        L.klick('dialog [data-menue="name"]')
        L.warte_da("#se-name")
        L.pg.wait_for_timeout(700)
        alt = L.js("return sr.querySelector('#se-name').value")
        neu = (alt + " x")[:60]
        L.js("el._vvEcht ??= el._vv; el._vv = { height: innerHeight - 336, offsetTop: 0, addEventListener() {}, removeEventListener() {} }; const f = sr.querySelector('#se-name'); f.blur(); f.focus(); f.value = x; f.dispatchEvent(new Event('input', { bubbles: true }));", neu)
        L.pg.wait_for_timeout(500)
        z = "blatt-tastatur-speichern"
        L.pruefe(L.js("return sr.querySelector('dialog.blatt[open]').hasAttribute('data-kbd')"), z, "Das Blatt weiss nichts von der Tastatur")
        box = L.pg.locator("dialog.blatt[open] .knoepfe .btn.primary").first.bounding_box()
        mx, my = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        L.pg.mouse.move(mx, my)
        L.pg.mouse.down()
        L.pg.wait_for_timeout(250)  # in dieser Zeit verliert das Feld sonst den Fokus und das Blatt rutscht
        L.pg.mouse.up()
        L.pg.wait_for_timeout(600)
        L.pruefe(L.js("return !sr.querySelector('dialog.blatt[open]')"), z, "Das Blatt ist nach dem Tipp auf Speichern nicht zu")
        L.pruefe(L.toast() == "Gespeichert.", z, f"Keine Meldung „Gespeichert.“ (Meldung: {L.toast()!r})")
        L.pruefe(L.js("return sr.querySelector('main h2')?.textContent.trim()") == neu, z, "Der neue Name steht nicht in der Überschrift")
        L.js("el._vv = el._vvEcht;")
        L.ruhe()


# AM15: Lage und Größe aller sichtbaren Elemente (Pfad im Baum → Rechteck), dazu der Scrollstand. Der Aufzeichner der Bewegung und die Balken der Abspiel-Anzeige (`.eq`) zählen nicht.
BEW_LAGE = """
const w = (x.aus ? sr.querySelector(x.aus) : sr);
const aus = {}; let n = 0;
const lauf = (e, pfad) => {
  [...e.children].forEach((c, i) => {
    if (c.closest('dialog.player') || c.tagName === 'STYLE' || c.tagName === 'AUDIO' || c.classList.contains('eq') || c.closest('.eq') || c.closest('svg') || c.hasAttribute('data-flugklon')) return;
    const k = pfad + '/' + c.tagName.toLowerCase() + '.' + [...c.classList].slice(0, 2).join('.') + '[' + i + ']';
    const r = c.getBoundingClientRect();
    if (r.width > 0 || r.height > 0) aus[k] = { blatt: c.children.length === 0 && c.tagName !== 'SVG', l: Math.round(r.left * 10) / 10, t: Math.round(r.top * 10) / 10, w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10 };
    lauf(c, k);
  });
};
lauf(w, '');
const sc = (q) => sr.querySelector(q)?.scrollTop ?? 0;
return { el: aus, scroll: Math.max(sc('.rahmen'), sc('.spalte')) };
"""


def lage_vergleich(L: Lauf, z, vorher, nachher, was):
    """Gleiche Elemente an gleicher Stelle in gleicher Größe (höchstens 1 px), gleicher Scrollstand."""
    a, b = vorher["el"], nachher["el"]
    fehlt = sorted(set(a) ^ set(b))
    L.pruefe(not fehlt, z, f"{was}: Elemente erscheinen oder verschwinden: {fehlt[:4]}")
    # Texte ohne Unterelemente sind so breit wie ihr Text (und mittig oder links): dort zählen nur Oberkante und Höhe
    abw = sorted(((max(abs(a[k][f] - b[k][f]) for f in ("th" if a[k]["blatt"] else "ltwh")), k) for k in set(a) & set(b)), reverse=True)
    L.pruefe(not abw or abw[0][0] <= 1, z, f"{was}: Lage oder Größe ändert sich um {abw[0][0]:.1f} px bei {abw[0][1]}" if abw else "")
    L.pruefe(abs(vorher["scroll"] - nachher["scroll"]) <= 1, z, f"{was}: scrollTop {vorher['scroll']} -> {nachher['scroll']}")


def ablauf_play_pause_lage(L: Lauf):
    """AM15: Play und Pause ändern keine Höhe und keine Lage: Serienseite, Start und Bibliothek (jeweils Pause, dann wieder Play)."""
    L.gehe("#bibliothek")
    if not L.da("a.lrow[data-serie], a.rcard[data-serie]"):
        return
    with L.schritt("play-pause-lage"):
        player_start(L)
        sid = L.js("return el.spieler.s.serie.id")
        orte = (("serie", f"#serie-{sid}", "[data-reinhoeren]"), ("serie-weiter", f"#serie-{sid}", "[data-reinhoeren]"), ("start", "#start", ".mini .mplay"), ("bibliothek", "#bibliothek", ".mini .mplay"))
        for name, hash_, knopf in orte:
            L.gehe(hash_)
            L.warte_da(knopf)
            if name == "serie-weiter":  # eine gemerkte Stelle (wie nach dem Neuladen der Seite): die Zeile unter dem Knopf nennt „ab 0:24“
                L.js("const z = el._seiteObj.z.serie; const f = z.folgen[0]; z.hoerstelle = { folge: f.name }; f.hoerstelle = { position_s: 24, fertig: false }; el.requestUpdate();")
                L.pg.wait_for_timeout(300)
            L.pg.wait_for_timeout(600)
            z = f"play-pause-lage-{name}"
            spielt = L.js("return el.spieler.zustand === 'spielt'")
            if not spielt:
                L.klick(knopf)
                L.pg.wait_for_timeout(500)
            lauf = L.js(BEW_LAGE, {})
            for schritt in ("pause", "play"):
                L.klick(knopf)
                L.pg.wait_for_timeout(500)
                jetzt = L.js(BEW_LAGE, {})
                lage_vergleich(L, z, lauf, jetzt, f"nach {schritt}")
                L.pruefe(L.js("return el.spieler.zustand === 'spielt'") == (schritt == "play"), z, f"Der Knopf hat nicht auf {schritt} geschaltet")
                lauf = jetzt
    player_aus(L)


# AM19: jedes Bild (rAF) des Wechsels Liste/Start → Serienseite (und zurück) aufnehmen. Je Bild: kleinste Deckkraft von main und seinen Kindern (auch über die Vorfahren), welche Seite steht
# da (`bib`, `serie`, `laedt` = Ladeplatzhalter), ob der Kopf der Serienseite einen Titel hat, ob das große Cover ein Bild trägt, ob die Ersatzkachel (.bst) zu sehen ist, ob der Klon
# des Cover-Flugs da ist und ein Bild trägt. x = { klick, art: 'hin' | 'zurueck', verz (ms, Verzögerung von serie/get), tipp (ms zwischen Zeiger-runter und Klick), dauer (ms) }.
BEW_WECHSEL = """
const B = window.__bew; B.calls.length = 0;
const wsp = el.hass.connection;
if (!wsp.__verz) { const o = wsp.sendMessagePromise; wsp.__verz = { ms: 0 }; wsp.sendMessagePromise = async (m) => { if (m && m.type === 'tobibox/serie/get' && wsp.__verz.ms) await new Promise((r) => setTimeout(r, wsp.__verz.ms)); return o(m); }; }
wsp.__verz.ms = x.verz || 0;
const eff = (n) => { let o = 1; for (let e = n; e && e.nodeType === 1; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity); return o; };
const sicht = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; };
const bildDa = (e) => !!e && /url\\(/.test(getComputedStyle(e).backgroundImage);
const bstSicht = (e) => !!e && [...e.querySelectorAll('.bst')].some((b) => getComputedStyle(b).visibility !== 'hidden' && sicht(b));
let ausloeser; let alle = [];
if (x.art === 'hin') {
  alle = [...sr.querySelectorAll(x.klick)].filter((a) => a.querySelector('.cover[data-cover]'));
  for (let i = 0; i < 60 && !alle.some((a) => a.querySelector('.cover').dataset.bild === '1'); i += 1) await new Promise((r) => setTimeout(r, 50));
  ausloeser = alle[(x.nr ?? 0) * 3 % alle.length]; // eine Serie, die in dieser Seite noch nicht geöffnet wurde (kalt)
  ausloeser.scrollIntoView({ block: 'center' });
  for (let i = 0; i < 40 && ausloeser.querySelector('.cover').dataset.bild !== '1'; i += 1) await new Promise((r) => setTimeout(r, 50)); // das kleine Bild lädt, sobald es sichtbar ist
  await new Promise((r) => setTimeout(r, 250));
} else ausloeser = sr.querySelector(x.klick);
const kleinBild = x.art === 'hin' ? ausloeser.querySelector('.cover').dataset.bild === '1' : bildDa(sr.querySelector('main .cover.se-xl')); // war ein Bild da?
const t0 = performance.now();
const proben = [];
const nimm = () => {
  const m = sr.querySelector('main');
  const kinder = m ? [...m.children].filter(sicht) : [];
  const hero = m?.querySelector('.se-hero'); const xl = m?.querySelector('.cover.se-xl');
  const klone = [...sr.querySelectorAll('[data-flugklon]')]; const klon = klone[0];
  const serieSeite = !!hero; const bibSeite = !!m?.querySelector('a.lrow[data-serie], a.rcard[data-serie], a.tile[data-serie], a.qt[data-serie]');
  proben.push({ t: Math.round(performance.now() - t0), hash: location.hash, op: Math.min(1, ...[m, ...kinder].filter(Boolean).map(eff)), seite: serieSeite ? 'serie' : (m?.querySelector('.laedt') ? 'laedt' : (bibSeite ? 'bib' : 'leer')),
    titel: hero ? (hero.querySelector('h2')?.textContent.trim() ?? '') : null, xlBild: xl ? bildDa(xl) : null, xlBst: xl ? bstSicht(xl) : null, klon: !!klon, klonBild: klone.length ? klone.every(bildDa) : null, klonBst: klone.some(bstSicht), klonStil: klone.map((k) => `${k.style.backgroundImage.slice(0, 12)}|${k.dataset.cover}|${k.dataset.stand}|${k.dataset.bild}|${k.className}`).join(' ; ') || null,
    heroTop: hero ? Math.round(hero.getBoundingClientRect().top) : null, vorFolgen: !!m?.querySelector('[data-folge]') });
};
const r0 = ausloeser.getBoundingClientRect();
const zeiger = (art) => ausloeser.dispatchEvent(new PointerEvent(art, { bubbles: true, composed: true, cancelable: true, pointerId: 1, pointerType: 'touch', button: 0, clientX: r0.left + r0.width / 2, clientY: r0.top + r0.height / 2 }));
let weiter = true;
const lauf = (async () => { while (weiter) { nimm(); await new Promise((r) => requestAnimationFrame(r)); } })();
if (x.art === 'hin') { zeiger('pointerdown'); await new Promise((r) => setTimeout(r, x.tipp ?? 90)); zeiger('pointerup'); }
ausloeser.click();
await new Promise((r) => setTimeout(r, x.dauer ?? 1400));
weiter = false; await lauf;
const flugs = B.calls.filter((c) => c.el.dataset && c.el.dataset.flugklon === '1').map((c) => `${c.bg0}|${c.bild0}`);
const sid = x.id ?? ausloeser.dataset.serie; const urlKeys = Object.keys(Object.fromEntries(el._covers.urls)).filter((k) => k.startsWith(sid));
return { kleinBild, urlKeys, flugs, proben, vt: B.vt, id: ausloeser.dataset.serie ?? null, anzahl: alle.length };
"""


def wechsel_pruefen(L: Lauf, z, r, ausgabe=False, sofort=False):
    """Auswertung zu BEW_WECHSEL (AM19): kein Bild des Wechsels mit halb durchsichtiger Seite, leerem Kopf, Ersatzkachel (wenn ein Bild da war) oder Ladeplatzhalter."""
    pr = r["proben"]
    if ausgabe:
        print(z, "kleinBild", r["kleinBild"], len(pr), "Bilder", "id", r.get("id"), "Links", r.get("anzahl"), r.get("urlKeys"), r.get("flugs"))
        for p in pr:
            print("   ", p["t"], p["hash"][:12], "op %.2f" % p["op"], p["seite"], "titel=%r" % (p["titel"],), "xlBild", p["xlBild"], "xlBst", p["xlBst"], "klon", p["klon"], p["klonBild"], p["klonBst"], p.get("klonStil"), "heroTop", p["heroTop"], "folgen", p["vorFolgen"])
    start = next((i for i, p in enumerate(pr) if p["hash"] != pr[0]["hash"]), None)
    if start is None:
        L.pruefe(False, z, "Die Adresse hat nicht gewechselt")
        return
    w = pr[start:]
    halb = [p for p in w if p["op"] < 0.99]
    L.pruefe(not halb, z, f"{len(halb)} von {len(w)} Bildern des Wechsels mit halb durchsichtiger Seite (kleinste Deckkraft {min([p['op'] for p in halb] or [1]):.2f})")
    laedt = [p for p in w if p["seite"] in ("laedt", "leer")]
    L.pruefe(not laedt, z, f"{len(laedt)} Bilder des Wechsels zeigen den Ladeplatzhalter oder eine leere Seite ({laedt[0]['seite'] if laedt else ''})")
    leer = [p for p in w if p["seite"] == "serie" and not p["titel"]]
    L.pruefe(not leer, z, f"{len(leer)} Bilder mit leerem Kopf der Serienseite")
    if r["kleinBild"]:
        bst = [p for p in w if (p["seite"] == "serie" and p["xlBst"]) or (p["klon"] and p["klonBst"])]
        L.pruefe(not bst, z, f"{len(bst)} Bilder mit Ersatzkachel (Buchstabe) statt Cover")
        ohne = [p for p in w if p["klon"] and not p["klonBild"]]
        L.pruefe(not ohne, z, f"{len(ohne)} Bilder, in denen der Klon kein Bild trägt")
    if sofort:  # zweites Öffnen derselben Serie: die Seite steht im ersten Bild nach dem Wechsel da, ohne auf serie/get zu warten (das hier 600 ms braucht)
        spaet = [p for p in w if p["seite"] != "serie"]
        L.pruefe(not spaet, z, f"{len(spaet)} Bilder nach dem Wechsel ohne die Serienseite (wartet auf serie/get?)")


def ablauf_wechsel_serie(L: Lauf):
    """AM19: Wechsel Bibliothek/Start → Serienseite und zurück, Bild für Bild; mit langsamer CPU (4×) und verzögertem serie/get (150 ms) und ohne. Zweites Öffnen derselben Serie wartet nicht auf serie/get."""
    L.gehe("#bibliothek")
    if not L.da("a.lrow[data-serie], a.rcard[data-serie]"):
        return
    ausgabe = bool(os.environ.get("TOBIBOX_WECHSEL_AUSGABE"))
    bew_start(L)
    cdp = L.pg.context.new_cdp_session(L.pg)
    try:
        for name, hash_, sel in (("bibliothek", "#bibliothek", "a.lrow[data-serie], a.rcard[data-serie]"), ("start", "#start", "a.tile[data-serie], a.qt[data-serie], a.rcard[data-serie]")):
            for nr, (drossel, verz) in enumerate(((1, 0), (4, 150))):
                z = f"wechsel-{name}-cpu{drossel}-verz{verz}"
                with L.schritt(z):
                    L.gehe(hash_)
                    if not L.da(sel):
                        continue
                    L.pg.wait_for_timeout(500)
                    cdp.send("Emulation.setCPUThrottlingRate", {"rate": drossel})
                    try:
                        r = jsa(L, BEW_WECHSEL, {"klick": sel, "art": "hin", "verz": verz, "nr": nr + (2 if name == "start" else 0)})
                        wechsel_pruefen(L, z + "-hin", r, ausgabe)
                        L.pg.wait_for_timeout(300)
                        r = jsa(L, BEW_WECHSEL, {"klick": "a[data-zurueck]", "art": "zurueck", "verz": 0, "id": r["id"]})
                        wechsel_pruefen(L, z + "-zurueck", r, ausgabe)
                        # eine andere Serie dazwischen (die Seite behält sonst nur die letzte), dann zum zweiten Mal dieselbe wie oben, und serie/get braucht jetzt 600 ms:
                        # die Seite steht sofort da (AM19: zuletzt geöffnete Serien werden gemerkt)
                        L.pg.wait_for_timeout(300)
                        r2 = jsa(L, BEW_WECHSEL, {"klick": sel, "art": "hin", "verz": 0, "nr": nr + 5 + (2 if name == "start" else 0), "dauer": 800})
                        L.pg.wait_for_timeout(300)
                        jsa(L, BEW_WECHSEL, {"klick": "a[data-zurueck]", "art": "zurueck", "verz": 0, "id": r2["id"], "dauer": 800})
                        L.pg.wait_for_timeout(300)
                        r = jsa(L, BEW_WECHSEL, {"klick": sel, "art": "hin", "verz": 600, "nr": nr + (2 if name == "start" else 0)})
                        wechsel_pruefen(L, z + "-nochmal", r, ausgabe, sofort=True)
                        L.pg.wait_for_timeout(900)
                        r = jsa(L, BEW_WECHSEL, {"klick": "a[data-zurueck]", "art": "zurueck", "verz": 0, "id": r["id"]})
                    finally:
                        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    finally:
        cdp.detach()
        L.js("if (el.hass.connection.__verz) el.hass.connection.__verz.ms = 0;")


# A8d: Lage der Teile der Vollansicht (Cover, Zeitleiste, Knöpfe, Zeile „Kapitel“): ändert die Zeile ihren Text, darf nichts wandern (AM15)
KAP_LAGE = """
const d = sr.querySelector('dialog.player'); if (!d) return null;
const r = (s) => { const e = d.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map((v) => Math.round(v * 10) / 10); };
return { cover: r('.pin > .cover'), titel: r('.ptitle h2'), kap: r('[data-pkap]'), slider: r('.pslider'), play: r('[data-p=play]'), prev: r('[data-p=prev]'), kapitelKnopf: r('[data-p=kapitel]'), sperre: r('[data-p=lock], [data-p=unlock]'), note: r('[data-pnote]') };
"""
# Lage auf der Serienseite: großer Knopf, Zeile darunter, Kopf, erste Zeile der Liste
KAP_SEITE_LAGE = """
const r = (s) => { const e = sr.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map((v) => Math.round(v * 10) / 10); };
return { hero: r('.se-hero'), rein: r('[data-reinhoeren]'), liste: r('[data-liste]'), zeile: r('[data-liste] > :first-child') };
"""


def kap_gleich(L: Lauf, name, a, b, was):
    """Beide Lagen (aus KAP_LAGE oder KAP_SEITE_LAGE) müssen bis auf 1 px gleich sein."""
    for k, v in (a or {}).items():
        w = (b or {}).get(k)
        if v is None or w is None:
            continue
        L.pruefe(all(abs(x - y) <= 1.01 for x, y in zip(v, w)), name, f"{k} wandert {was}: {v} → {w}")


def kap_ton(L: Lauf, ab, zeit=7000):
    """Warten, bis der Ton läuft und mindestens `ab` Sekunden erreicht hat."""
    L.pg.wait_for_function("ab => { const a = window.__el.shadowRoot.querySelector('audio'); return a && !a.paused && a.currentTime >= ab; }", arg=ab, timeout=zeit)


def kap_bereit_zahl(L: Lauf):
    k = f"{L.job['profil']}~{L.job['kennung']}"
    return L.pg.evaluate("async (k) => (await (await fetch(`/aufrufe?k=${encodeURIComponent(k)}&typ=tobibox/audio/bereit`)).json())", k)


def ablauf_kapitel(L: Lauf):
    """A8d (AM11 bis AM17): Abschnitt „Kapitel“ nur beim Hörbuch aus einer Folge, Kapitelsprung mit echtem Ton (eingebettet: Zeit; Ordner-Folge: neuer Link mit `track`), AM13 (das geladene
    Kapitel öffnet nur den Player), Zeile und Knopf „Kapitel“ im Player mit Blatt und Sperre, nichts wandert (AM15), Gegenprobe ohne Kapitel; „Die Hörprobe wird vorbereitet“
    (AM20: in der Zeile unter dem großen Knopf, keine Karte, kein Platz; nach der Wartezeit fragt die Seite neu und lädt); Zähler der Hörkopie-Warteschlange in Technik."""
    L.gehe("#bibliothek")
    if not L.da("a.lrow[data-serie], a.rcard[data-serie]"):
        return
    with L.schritt("kapitel-abschnitt"):
        L.gehe("#serie-hbk")
        L.warte_da('[data-liste="kapitel"] [data-kapitel]')
        L.pruefe(not L.da('[data-liste="folgen"]'), "kapitel-abschnitt", "Hörbuch aus einer Folge zeigt noch die Folgenliste")
        L.pruefe(L.js("return sr.querySelector('.se-abschnitt')?.textContent") == "Kapitel", "kapitel-abschnitt", "Überschrift „Kapitel“ fehlt")
        z = L.js("return [...sr.querySelectorAll('[data-liste=kapitel] [data-kapitel]')].map((e) => ({ t: e.textContent.replace(/\\s+/g, ' ').trim(), knoepfe: e.querySelectorAll('button').length, h: e.getBoundingClientRect().height }))")
        L.pruefe(len(z) == 3, "kapitel-abschnitt", f"{len(z)} Zeilen statt 3")
        L.pruefe("Kapitel 1" in z[0]["t"] and "ab 0:00" in z[0]["t"], "kapitel-abschnitt", f"Zeile 1: {z[0]['t']}")
        L.pruefe("Der Hafen" in z[1]["t"] and "ab 0:12 · 0:14" in z[1]["t"], "kapitel-abschnitt", f"Zeile 2: {z[1]['t']}")
        L.pruefe(all(x["knoepfe"] == 1 for x in z), "kapitel-abschnitt", "Eine Kapitelzeile hat mehr als einen Knopf (kein eigener Play-Knopf, AM11)")
        L.pruefe(all(x["h"] >= 56 for x in z), "kapitel-abschnitt", f"Zeilen zu niedrig: {[x['h'] for x in z]}")
        L.pruefe(not L.da('[data-liste="kapitel"] [aria-current="true"]'), "kapitel-abschnitt", "ohne gemerkte Stelle ist ein Kapitel markiert")
        L.messe("kapitel-seite")
    with L.schritt("kapitel-mehrere-folgen"):
        L.gehe("#serie-reise")
        L.warte_da('[data-liste="folgen"] [data-folge]')
        L.pruefe(not L.da('[data-liste="kapitel"]'), "kapitel-mehrere-folgen", "Eine Serie mit mehreren Folgen zeigt den Abschnitt „Kapitel“ (AM12)")
    with L.schritt("kapitel-sprung-eingebettet"):
        L.gehe("#serie-hbk")
        L.warte_da('[data-liste="kapitel"] [data-kapitel]')
        n0 = len(kap_bereit_zahl(L))
        L.klick('[data-liste="kapitel"] [data-kapitel="1"] [data-abspielen]')
        kap_ton(L, 12)
        t = audio_stand(L)["t"]
        L.pruefe(12 <= t < 30, "kapitel-sprung", f"Start nicht am Kapitel 2 (12 s): {t:.1f}")
        L.pruefe(L.js("return sr.querySelector('[data-liste=kapitel] [aria-current=true]')?.dataset.kapitel") == "1", "kapitel-sprung", "Das laufende Kapitel ist nicht markiert")
        L.pruefe(L.da('[data-liste="kapitel"] [data-kapitel="1"] .eq'), "kapitel-sprung", "Keine Abspiel-Anzeige am laufenden Kapitel")
        L.klick('[data-liste="kapitel"] [data-kapitel="2"] [data-abspielen]')
        kap_ton(L, 26)
        L.pruefe(len(kap_bereit_zahl(L)) == n0 + 1, "kapitel-sprung", "Der Sprung in ein anderes Kapitel derselben Datei fragt neu (audio/bereit)")
        L.pruefe(L.js("return sr.querySelector('[data-liste=kapitel] [aria-current=true]')?.dataset.kapitel") == "2", "kapitel-sprung", "Markierung folgt dem Sprung nicht")
        L.pruefe(L.js("return !!sr.querySelector('[data-liste=kapitel] [data-kapitel=\"0\"] .se-ok')") and L.js("return !!sr.querySelector('[data-liste=kapitel] [data-kapitel=\"1\"] .se-ok')"), "kapitel-sprung", "Die Kapitel davor tragen kein Häkchen")
    with L.schritt("kapitel-am13"):
        t0 = audio_stand(L)["t"]
        L.klick('[data-liste="kapitel"] [data-kapitel="2"] [data-abspielen]')  # das geladene Kapitel: nur der Player geht auf
        L.warte_da("dialog.player[open]")
        L.pg.wait_for_timeout(700)
        a = audio_stand(L)
        L.pruefe(not a["pausiert"] and a["t"] >= t0, "kapitel-am13", f"Der Ton hat sich geändert (vorher {t0:.1f}, pausiert={a['pausiert']}, jetzt {a['t']:.1f})")
        L.pruefe(L.js("return sr.querySelector('[data-pkap]')?.textContent") .startswith("Kapitel 3: Der Sturm"), "kapitel-am13", f"Zeile im Player: {L.js('return sr.querySelector(\"[data-pkap]\")?.textContent')}")
        L.pruefe(L.js("return [...sr.querySelectorAll('dialog.player .speed button')].map((b) => b.textContent.trim())") == ["Kapitel", "Sperren"], "kapitel-am13", "Knopf „Kapitel“ steht nicht neben „Sperren“")
        L.pruefe(L.js("const e = sr.querySelector('[data-pkap]'); return e.scrollWidth <= e.clientWidth + 1 || getComputedStyle(e).textOverflow === 'ellipsis'"), "kapitel-am13", "Die Zeile „Kapitel“ bricht um")
        L.messe("kapitel-player")
    with L.schritt("kapitel-blatt"):
        voll0 = L.js(KAP_LAGE)
        L.klick('dialog.player [data-p="kapitel"]')
        L.pg.wait_for_selector("dialog.blatt[open] [data-kapitel]")
        L.pg.wait_for_timeout(500)
        L.pruefe(L.js("return sr.querySelectorAll('dialog.blatt [data-kapitel]').length") == 3, "kapitel-blatt", "Das Blatt zeigt nicht alle Kapitel")
        sicht = L.js("""
          const b = sr.querySelector('dialog.blatt[open]'); const z = b.querySelector('[aria-current="true"]'); if (!z) return null;
          const r = z.getBoundingClientRect(), f = b.getBoundingClientRect(); return { oben: r.top >= f.top - 1, unten: r.bottom <= f.bottom + 1, aktuell: z.dataset.kapitel, fokus: sr.activeElement === z };""")
        L.pruefe(sicht and sicht["oben"] and sicht["unten"] and sicht["aktuell"] == "2", "kapitel-blatt", f"Das aktuelle Kapitel ist nicht markiert und sichtbar: {sicht}")
        L.pruefe(sicht and sicht["fokus"], "kapitel-blatt", "Der Fokus liegt nicht auf dem aktuellen Kapitel")
        L.pruefe("läuft" in L.js("return sr.querySelector('dialog.blatt [aria-current=true]').textContent"), "kapitel-blatt", "Das aktuelle Kapitel nennt „läuft“ nicht")
        L.messe("kapitel-blatt")
        L.klick('dialog.blatt [data-kapitel="0"]')
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog.blatt[open]')", timeout=4000)
        kap_ton(L, 0.1)
        L.pg.wait_for_timeout(500)
        a = audio_stand(L)
        L.pruefe(a["t"] < 12 and not a["pausiert"], "kapitel-blatt", f"Nach dem Tipp auf Kapitel 1: t={a['t']:.1f}, pausiert={a['pausiert']}")
        L.pruefe(L.js("return sr.querySelector('[data-pkap]').textContent") == "Kapitel 1 (1 von 3)", "kapitel-blatt", f"Zeile: {L.js('return sr.querySelector(\"[data-pkap]\").textContent')}")
        voll1 = L.js(KAP_LAGE)
        kap_gleich(L, "kapitel-lage", voll0, voll1, "beim Wechsel des Kapitels")
    with L.schritt("kapitel-sperre"):
        L.klick('dialog.player [data-p="lock"]')
        L.pg.wait_for_selector('dialog.player [data-p="unlock"]')
        L.pruefe(L.js("return sr.querySelector('dialog.player [data-p=kapitel]').disabled"), "kapitel-sperre", "Der Knopf „Kapitel“ ist trotz Sperre bedienbar")
        L.pruefe(L.js("const k = sr.querySelector('dialog.player [data-p=kapitel]').getBoundingClientRect(), u = sr.querySelector('dialog.player [data-p=unlock]').getBoundingClientRect(); return k.right <= u.left + 1 || k.bottom <= u.top + 1"), "kapitel-sperre", "Knopf „Kapitel“ und Entsperren überlappen")
        L.pruefe(L.js("const u = sr.querySelector('dialog.player [data-p=unlock]').getBoundingClientRect(); return u.left >= 0 && u.right <= innerWidth"), "kapitel-sperre", "Der Entsperr-Knopf ragt über den Rand")
        L.messe("kapitel-gesperrt")
        L.js("el.spieler.gesperrt = false; el.requestUpdate();")
        L.pg.wait_for_selector('dialog.player [data-p="lock"]')
    with L.schritt("kapitel-ordner"):
        player_aus(L)
        L.gehe("#serie-reise")
        L.warte_da('[data-folge="teil1"] [data-abspielen]')
        L.klick('[data-folge="teil1"] [data-abspielen]')
        kap_ton(L, 0.3)
        L.klick(".mini .mopen")
        L.warte_da("dialog.player[open] [data-pkap]")
        L.pg.wait_for_timeout(600)
        L.pruefe(L.js("return sr.querySelector('[data-pkap]').textContent") == "Kapitel 1: Eins (1 von 3)", "kapitel-ordner", f"Zeile: {L.js('return sr.querySelector(\"[data-pkap]\").textContent')}")
        vor = L.js(KAP_LAGE)
        L.klick('dialog.player [data-p="kapitel"]')
        L.pg.wait_for_selector("dialog.blatt[open] [data-kapitel]")
        L.pg.wait_for_timeout(400)
        n0 = len([x for x in kap_bereit_zahl(L) if x.get("folge") == "teil1"])
        L.klick('dialog.blatt [data-kapitel="2"]')
        L.pg.wait_for_function("() => { const a = window.__el.shadowRoot.querySelector('audio'); return a && /track=2&authSig=/.test(a.getAttribute('src') || '') && !a.paused && a.currentTime > 0.1; }", timeout=8000)
        b = [x for x in kap_bereit_zahl(L) if x.get("folge") == "teil1"]  # (die nächste Folge wird im Voraus gefragt, die zählt hier nicht)
        L.pruefe(len(b) == n0 + 1 and b[-1].get("track") == 2, "kapitel-ordner", f"Kein neues audio/bereit mit track=2: {b[-1:]}")
        z = L.pg.evaluate("async () => (await (await fetch('/audio-zaehler')).json())")
        L.pruefe(any("teil1" in x["pfad"] and "track=2" in x["pfad"] for x in z), "kapitel-ordner", "Der Server hat Track 3 nie ausgeliefert")
        L.pg.wait_for_timeout(300)
        L.pruefe(L.js("return sr.querySelector('[data-pkap]').textContent") == "Kapitel 3: Drei (3 von 3)", "kapitel-ordner", f"Zeile nach dem Sprung: {L.js('return sr.querySelector(\"[data-pkap]\").textContent')}")
        kap_gleich(L, "kapitel-lage-ordner", vor, L.js(KAP_LAGE), "beim Trackwechsel")
        # die andere Folge hat keine Kapitel: Zeile und Knopf bleiben stehen (leer, gesperrt), nichts wandert
        vor = L.js(KAP_LAGE)
        L.klick('dialog.player [data-p="next"]')
        L.pg.wait_for_function("() => { const sp = window.__el.spieler; return sp.s && sp.s.i === 1 && sp._geladen; }", timeout=8000)
        L.pg.wait_for_timeout(300)
        L.pruefe(L.da("dialog.player [data-pkap]") and L.js("return sr.querySelector('[data-pkap]').textContent") == "", "kapitel-ordner", "Bei der Folge ohne Kapitel fehlt die (leere) Zeile oder sie hat Text")
        L.pruefe(L.js("return sr.querySelector('dialog.player [data-p=kapitel]').disabled"), "kapitel-ordner", "Der Knopf „Kapitel“ ist bei einer Folge ohne Kapitel nicht gesperrt")
        kap_gleich(L, "kapitel-lage-folge", vor, L.js(KAP_LAGE), "beim Wechsel zur Folge ohne Kapitel")
    with L.schritt("kapitel-gegenprobe"):
        player_aus(L)
        player_start(L)  # die erste Serie der Bibliothek hat keine Kapitel
        L.klick(".mini .mopen")
        L.warte_da("dialog.player[open] .pslider")
        L.pg.wait_for_timeout(600)
        L.pruefe(not L.da('dialog.player [data-p="kapitel"]') and not L.da("dialog.player [data-pkap]"), "kapitel-gegenprobe", "Ohne Kapitel zeigt der Player Knopf oder Zeile „Kapitel“")
        L.pruefe(L.js("return [...sr.querySelectorAll('dialog.player .speed button')].map((b) => b.textContent.trim())") == ["Sperren"], "kapitel-gegenprobe", "Nur „Sperren“ gehört in die Reihe")
        player_aus(L)
    with L.schritt("kapitel-hoerprobe"):
        L.gehe("#serie-ogg")
        L.warte_da("[data-reinhoeren]")
        L.pruefe(not L.da("[data-hoerprobe-platz]") and not L.da('[data-karte="hoerprobe"]'), "kapitel-hoerprobe", "Platz oder Karte für die Hörprobe steht vor dem Tipp (AM20)")
        normal = L.js("return sr.querySelector('[data-rein-zusatz]').textContent")
        L.pruefe("vorbereitet" not in normal, "kapitel-hoerprobe", f"Vor dem Tipp steht schon der Wartesatz: {normal!r}")
        vor = L.js(KAP_SEITE_LAGE)
        L.js("el.spieler.vorbereitetNeuMs = 1000")
        L.klick("[data-reinhoeren]")
        L.pg.wait_for_function("() => (window.__el.shadowRoot.querySelector('[data-rein-zusatz]')?.textContent || '').includes('Die Hörprobe wird vorbereitet')", timeout=5000)
        L.pruefe(not L.da('[data-karte="hoerprobe"]') and not L.da("[data-hoerprobe-platz]"), "kapitel-hoerprobe", "Es steht eine Karte oder ein Platz für die Hörprobe (AM20)")
        zl = L.js("const e = sr.querySelector('[data-rein-zusatz]'); const b = e.getBoundingClientRect(); const cs = getComputedStyle(e); return { h: b.height, zeilen: Math.round(b.height / parseFloat(cs.lineHeight || '20')), eins: e.scrollWidth <= e.clientWidth + 1 }")
        L.pruefe(zl["zeilen"] <= 1 and zl["h"] < 30, "kapitel-hoerprobe", f"Die Zeile unter dem Knopf ist mehr als eine Zeile hoch: {zl}")
        kap_gleich(L, "kapitel-hoerprobe-lage", vor, L.js(KAP_SEITE_LAGE), "als die Karte erschien (AM15)")
        L.messe("kapitel-hoerprobe")
        L.pg.wait_for_function("() => !(window.__el.shadowRoot.querySelector('[data-rein-zusatz]')?.textContent || '').includes('wird vorbereitet')", timeout=9000)
        b = [x for x in kap_bereit_zahl(L) if x.get("folge") == "wald.ogg"]
        L.pruefe(len(b) >= 3 and b[0].get("vorbereiten") in (None, True) and all(x.get("vorbereiten") is False for x in b[1:]), "kapitel-hoerprobe", f"Nach 15 s (hier 1 s) fragt die Seite nicht neu, ohne anzustoßen: {b}")
        src = L.js("return sr.querySelector('audio')?.getAttribute('src') ?? ''")
        L.pruefe("authSig=" in src and "wald.ogg" in src, "kapitel-hoerprobe", f"Bei „bereit“ ist keine Quelle gesetzt: {src!r}")
        kap_gleich(L, "kapitel-hoerprobe-lage", vor, L.js(KAP_SEITE_LAGE), "als die Karte ging (AM15)")
        player_aus(L)
    with L.schritt("kapitel-keine-probe"):
        # AM27: Administratoren sehen bei `hoerkopie.zustand = fehler` den Grund kurz in der Folgenzeile, Benutzer nichts
        L.gehe("#serie-ogg")
        L.warte_da('[data-folge="mond.mp3"]')
        z = L.js("return [...sr.querySelectorAll('[data-keine-probe]')].map((e) => ({ t: e.textContent.trim(), in: !!e.closest('[data-folge=\"mond.mp3\"]'), breite: e.scrollWidth <= e.clientWidth + 1 }))")
        if L.job["rolle"] == "admin":
            L.pruefe(len(z) == 1 and z[0]["t"] == "Keine Hörprobe: Datei wirkt beschädigt" and z[0]["in"], "kapitel-keine-probe", f"Grund in der Folgenzeile fehlt oder falsch: {z}")
            L.messe("kapitel-keine-probe")
        else:
            L.pruefe(not z, "kapitel-keine-probe", f"Nicht-Administratoren sehen den Grund: {z}")
    if L.job["rolle"] == "admin":
        with L.schritt("kapitel-technik"):
            L.gehe("#technik-speicher")
            L.warte_da("[data-hoerkopien-schlange]")
            txt = L.js("return sr.querySelector('[data-hoerkopien-schlange]').textContent")
            L.pruefe(txt == "3 von höchstens 20 Dateien · 1,4 von höchstens 50 GB", "kapitel-technik", f"Zähler: {txt!r}")
            L.pruefe(L.da('[data-aktion="hoerkopien"]'), "kapitel-technik", "Knopf „Hörkopien neu erzeugen“ fehlt")
            L.messe("kapitel-technik")



# ------------------------------------------------------------------ Stufe B (B4): Gehört, Stern, Favoriten, Technik-Karten
def aufrufe(L: Lauf, typ):
    k = f"{L.job['profil']}~{L.job['kennung']}"
    return L.pg.evaluate("async ([k, t]) => (await (await fetch(`/aufrufe?k=${encodeURIComponent(k)}&typ=${t}`)).json())", [k, typ])


def ablauf_gehoert(L: Lauf):
    """Unterseite „Gehört“: Weg von „Geräte“, Auswahl „Wer?“, Zeitraum, Rangliste mit Aufteilung nach Folgen (Fokus zurück), Diagramme mit Beschreibung und Tabelle,
    „Was wird gezählt?“ (ohne „Handy“), Neuladen nach dem Ereignis `gehoert`."""
    if L.job["profil"] == "alt":
        return
    with L.schritt("gehoert-weg"):
        L.gehe("#geraete")
        L.pruefe(L.da("[data-gehoert-link]"), "gehoert-weg", "Zeile „Wer hat was gehört?“ fehlt auf Geräte")
        L.klick("[data-gehoert-link]")
        L.pruefe(L.hash() == "#gehoert", "gehoert-weg", f"Zeile führt nach {L.hash()}")
        L.warte_da("[data-gehoert]")
        L.pruefe(L.da('a.back[href="#geraete"]'), "gehoert-weg", "‹ Geräte fehlt")
        L.klick('a.back[href="#geraete"]')
        L.pruefe(L.hash() == "#geraete", "gehoert-weg", f"Zurück führt nach {L.hash()}")
    with L.schritt("gehoert-wer"):
        L.gehe("#gehoert")
        gh_zuruecksetzen(L)
        knoepfe = L.js("return [...sr.querySelectorAll('[data-wer-knopf]')].map((b) => [b.dataset.werKnopf, b.getAttribute('aria-pressed'), b.textContent.trim()])")
        L.pruefe(knoepfe and knoepfe[0][0] == "alle" and knoepfe[0][1] == "true", "gehoert-wer", f"„Alle“ nicht vorn und gewählt: {knoepfe[:2]}")
        L.pruefe(any(k[0] == "alle_boxen" for k in knoepfe), "gehoert-wer", "„Alle Boxen“ fehlt")
        L.pruefe(sum(1 for k in knoepfe if k[0].startswith("box:")) == 2 and sum(1 for k in knoepfe if k[0].startswith("benutzer:")) >= 2, "gehoert-wer", f"Boxen und Personen fehlen: {knoepfe}")
        L.pruefe(L.js("return sr.querySelector('[data-wer]').getAttribute('aria-labelledby') === 'gh-wer' && !!sr.querySelector('#gh-wer')"), "gehoert-wer", "Gruppe „Wer?“ ohne sichtbare Beschriftung")
        tabelle_alle = L.js("return sr.querySelector('[data-tabelle=\"zeitreihe\"]')?.textContent.replace(/\\s+/g, ' ')")
        L.pruefe("Davon" in (tabelle_alle or "") and "Küche" in (tabelle_alle or "") and "Person A" in (tabelle_alle or ""), "gehoert-wer", f"Bei „Alle“ fehlt die Aufteilung nach Quellen in der Tabelle: {tabelle_alle}")
        satz0 = L.js("return sr.querySelector('[data-karte=\"zeitreihe\"] [data-satz]').textContent")
        L.klick('[data-wer-knopf="box:kueche"]')
        L.pg.wait_for_function("() => window.__el.shadowRoot.querySelector('[data-wer-knopf=\"box:kueche\"]').getAttribute('aria-pressed') === 'true'", timeout=4000)
        L.ruhe()
        satz1 = L.js("return sr.querySelector('[data-karte=\"zeitreihe\"] [data-satz]').textContent")
        L.pruefe(satz0 != satz1 and "(" not in satz1, "gehoert-wer", f"Satz ändert sich mit der Box nicht: {satz0!r} → {satz1!r}")
        n = aufrufe(L, "tobibox/gehoert/zusammenfassung")
        L.pruefe(any(a.get("wer") == "box:kueche" for a in n), "gehoert-wer", "Abfrage ohne wer=box:kueche")
        L.klick('[data-wer-knopf="alle"]')
    with L.schritt("gehoert-zeitraum"):
        for zr, art, titel in (("monat", "tag", "Hörzeit pro Tag"), ("jahr", "woche", "Hörzeit pro Woche"), ("alles", "monat", "Hörzeit pro Monat"), ("woche", "tag", "Hörzeit pro Tag")):
            L.klick(f'[data-zeitraum] [data-wert="{zr}"]')
            L.pg.wait_for_function("z => window.__el.shadowRoot.querySelector(`[data-zeitraum] [data-wert=\"${z}\"]`).getAttribute('aria-pressed') === 'true'", arg=zr, timeout=4000)
            L.ruhe()
            L.pruefe(L.js("return sr.querySelector('#gh-tag-t')?.textContent.trim()") == titel, "gehoert-zeitraum", f"{zr}: Überschrift {L.js('return sr.querySelector(\"#gh-tag-t\")?.textContent')!r} statt {titel!r}")
            sa = L.js("return sr.querySelector('[data-karte=\"zeitreihe\"] [data-satz]').textContent")
            L.pruefe({"woche": "7 Tagen", "monat": "30 Tagen", "jahr": "letzten Jahr", "alles": "Insgesamt"}[zr] in sa, "gehoert-zeitraum", f"{zr}: Satz {sa!r}")
            bild = L.js("const s = sr.querySelector('[data-diagramm=\"zeitreihe\"] svg'); return s && [s.getAttribute('role'), s.getAttribute('aria-label'), s.querySelectorAll('.gh-saeule').length]")
            L.pruefe(bild and bild[0] == "img" and bild[1] and titel in bild[1] and bild[2] > 0, "gehoert-zeitraum", f"{zr}: Diagramm ohne role=img/Beschreibung: {bild}")
            if zr == "monat":
                L.pruefe(L.js("return sr.querySelectorAll('[data-diagramm=\"zeitreihe\"] .gh-zahl').length") == 0, "gehoert-zeitraum", "Zahlen über den Säulen bei 30 Tagen")
            if zr == "woche":
                L.pruefe(L.js("return sr.querySelectorAll('[data-diagramm=\"zeitreihe\"] .gh-zahl').length") == 7, "gehoert-zeitraum", "Woche: keine Zahl über jeder der 7 Säulen")
    with L.schritt("gehoert-aufteilung"):
        L.klick('[data-serie-zeile="lang"]')
        L.warte_da('[data-karte="aufteilung"] [data-aufteilung]')
        zeilen = L.js("return [...sr.querySelectorAll('[data-aufteilung] tbody tr')].map((r) => r.dataset.folge)")
        L.pruefe(len(zeilen) == 45, "gehoert-aufteilung", f"{len(zeilen)} Folgen statt 45 (auch nicht gehörte)")
        L.pruefe(L.da("[data-aufteilung] tr.gh-nie") and L.da("[data-aufteilung] tfoot [data-summe], [data-aufteilung] tfoot tr"), "gehoert-aufteilung", "Nicht gehörte Folgen oder Summe fehlen")
        L.pruefe(L.js("return document.activeElement === null || sr.activeElement?.matches('[data-aufteilung-titel]')"), "gehoert-aufteilung", "Fokus nicht auf der Überschrift der Aufteilung")
        L.klick("[data-aufteilung-zurueck]")
        L.pruefe(L.da("[data-rangliste]") and not L.da("[data-aufteilung]"), "gehoert-aufteilung", "‹ Rangliste führt nicht zur Rangliste")
        L.pg.wait_for_timeout(100)
        L.pruefe(L.js("return sr.activeElement?.matches('[data-serie-zeile=\"lang\"]')"), "gehoert-aufteilung", "Fokus nach „‹ Rangliste“ nicht auf der Zeile")
    with L.schritt("gehoert-tabellen"):
        for karte in ("zeitreihe", "stunden"):
            L.klick(f'[data-tabelle="{karte}"] summary')
            L.pruefe(L.js(f"return sr.querySelector('[data-tabelle=\"{karte}\"]').open"), "gehoert-tabellen", f"{karte}: Tabelle klappt nicht auf")
            L.pruefe(L.js(f"return sr.querySelectorAll('[data-tabelle=\"{karte}\"] tbody tr').length") >= 7, "gehoert-tabellen", f"{karte}: Tabelle ohne Zeilen")
        satz = L.js("return sr.querySelector('[data-karte=\"stunden\"] [data-satz]').textContent")
        L.pruefe("Am meisten um" in satz and "Uhr" in satz, "gehoert-tabellen", f"Tageszeiten ohne Satz „am meisten um …“: {satz!r}")
        L.pruefe(L.js("return sr.querySelectorAll('[data-diagramm=\"stunden\"] .gh-saeule').length") > 0, "gehoert-tabellen", "Tageszeiten ohne Säulen")
    with L.schritt("gehoert-gezaehlt"):
        L.klick("[data-gezaehlt] summary")
        t = L.js("return sr.querySelector('[data-gezaehlt]').textContent")
        L.pruefe(all(w in t for w in ("Hörzeit", "Mal", "fertig", "30 Minuten")), "gehoert-gezaehlt", "Erklärung unvollständig")
        L.pruefe("Handy ungefähr" not in t and "ungefähr" not in t, "gehoert-gezaehlt", "„Handy ungefähr“ steht noch da (Messung B2a)")
    with L.schritt("gehoert-ereignis"):
        n0 = len(aufrufe(L, "tobibox/gehoert/zusammenfassung"))
        L.mock("/ereignis", {"thema": "gehoert", "art": "geaendert"})
        L.pg.wait_for_function("([k, n]) => fetch(`/aufrufe?k=${encodeURIComponent(k)}&typ=tobibox/gehoert/zusammenfassung`).then((r) => r.json()).then((l) => l.length > n)",
                               arg=[f"{L.job['profil']}~{L.job['kennung']}", n0], timeout=6000)
        L.ruhe()
        L.pruefe(L.da("[data-gehoert]"), "gehoert-ereignis", "Seite nach dem Ereignis weg")


def ablauf_stern(L: Lauf):
    """Stern auf der Serienseite (Knopf mit aria-pressed, Meldung), „Zu Favoriten“ im Menü der Folge, kleine Sterne in Zeilen und Kacheln, Filter „Favoriten“ und die
    Sortierungen der Bibliothek, die Reihen „Zuletzt auf den Boxen gehört“ und „Favoriten“ auf dem Start."""
    if L.job["profil"] == "alt":
        return
    k = f"{L.job['profil']}~{L.job['kennung']}"
    with L.schritt("stern-reihen"):
        L.mock("/ws", {"type": "tobibox/favorit/set", "serie_id": "lang", "folge": "f02.mp3", "an": True})
        L.mock("/ws", {"type": "tobibox/favorit/set", "serie_id": "lang", "an": True})
        L.gehe("#start")
        L.warte_da('[data-reihe="zuletzt_gehoert"] .tile')
        L.pruefe(L.da('[data-reihe="favoriten"] .tile'), "stern-reihen", "Reihe „Favoriten“ fehlt")
        titel = L.js("return [...sr.querySelectorAll('.reihe .rowh')].map((h) => h.textContent.trim())")
        L.pruefe("Zuletzt auf den Boxen gehört" in titel and "Favoriten" in titel and "Favoriten / Empfehlungen" not in titel, "stern-reihen", f"Reihentitel: {titel}")
        L.pruefe(L.da('[data-reihe="favoriten"] [data-favorit][aria-label="Favorit"]'), "stern-reihen", "Kein kleiner Stern in der Reihe „Favoriten“")
        L.pruefe(L.da('[data-reihe="favoriten"] [data-favorit-folge]'), "stern-reihen", "Stern an einer Folge ergibt keine Kachel mit Folgenname")
        L.pruefe(L.js("return sr.querySelector('[data-reihe=\"zuletzt_gehoert\"]').closest('.reihe').querySelector('a.alle')?.getAttribute('href')") == "#bibliothek?sortierung=zuletzt_gehoert", "stern-reihen", "„Alle anzeigen“ der Reihe „Zuletzt gehört“ falsch")
    with L.schritt("stern-serie"):
        L.gehe("#serie-lied")
        L.warte_da("[data-stern]")
        L.pruefe(L.js("return sr.querySelector('[data-stern]').getAttribute('aria-pressed')") == "false", "stern-serie", "Stern schon gesetzt")
        name = L.js("return sr.querySelector('[data-stern]').getAttribute('aria-label')")
        L.pruefe(name.startswith("Favorit"), "stern-serie", f"Wort „Favorit“ nicht im Namen: {name!r}")
        L.klick("[data-stern]")
        L.pg.wait_for_function("() => window.__el.shadowRoot.querySelector('[data-stern]').getAttribute('aria-pressed') === 'true'", timeout=4000)
        L.pruefe("ist jetzt ein Favorit" in L.toast(), "stern-serie", f"Meldung {L.toast()!r}")
        L.pruefe(any(a["serie_id"] == "lied" and a["an"] is True and "folge" not in a for a in aufrufe(L, "tobibox/favorit/set")), "stern-serie", "Kein favorit/set für den Eintrag")
        L.messe("stern-serie-gesetzt")
        L.klick("[data-stern]")
        L.pg.wait_for_function("() => window.__el.shadowRoot.querySelector('[data-stern]').getAttribute('aria-pressed') === 'false'", timeout=4000)
        L.pruefe("kein Favorit mehr" in L.toast(), "stern-serie", f"Meldung {L.toast()!r}")
    with L.schritt("stern-folge"):
        L.gehe("#serie-lang")
        L.warte_da('[data-folge="f02.mp3"]')
        L.pruefe(L.da('[data-folge="f02.mp3"] [data-favorit]'), "stern-folge", "Kleiner Stern an der Folge mit Stern fehlt")
        L.klick('[data-folge="f02.mp3"] [data-menue-folge]')
        L.pruefe(L.js("return sr.querySelector('dialog [data-menue=\"favorit\"]')?.textContent.trim()") == "Aus Favoriten", "stern-folge", "Menüpunkt „Aus Favoriten“ fehlt")
        L.klick('dialog [data-menue="favorit"]')
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=4000)
        L.ruhe()
        L.pruefe(not L.da('[data-folge="f02.mp3"] [data-favorit]'), "stern-folge", "Stern bleibt nach „Aus Favoriten“")
        L.klick('[data-folge="f03.mp3"] [data-menue-folge]')
        L.pruefe(L.js("return sr.querySelector('dialog [data-menue=\"favorit\"]')?.textContent.trim()") == "Zu Favoriten", "stern-folge", "Menüpunkt „Zu Favoriten“ fehlt")
        L.klick('dialog [data-menue="favorit"]')
        L.pg.wait_for_function("() => !!window.__el.shadowRoot.querySelector('[data-folge=\"f03.mp3\"] [data-favorit]')", timeout=4000)
        L.pruefe(any(a.get("folge") == "f03.mp3" and a["an"] is True for a in aufrufe(L, "tobibox/favorit/set")), "stern-folge", "Kein favorit/set mit folge")
    with L.schritt("stern-bibliothek"):
        # frühere Abläufe haben vielleicht Einträge gelöscht: ein Stern an einer vorhandenen Serie, damit der Filter einen Treffer hat
        L.mock("/ws", {"type": "tobibox/favorit/set", "serie_id": "lang", "an": True})
        L.gehe("#bibliothek")
        L.klick("[data-sortieren]")
        namen = L.js("return [...sr.querySelector('dialog [role=radiogroup]').querySelectorAll('.optrow')].map((b) => b.textContent.trim())")
        L.pruefe(namen == ["A bis Z", "Zuletzt hinzugefügt", "Zuletzt angehört", "Zuletzt gehört", "Meist gehört"], "stern-bibliothek", f"Sortierungen: {namen}")
        L.pruefe(L.js("return [...sr.querySelectorAll('dialog .optrow[aria-pressed]')].map((b) => b.textContent.trim()).includes('Favoriten')"), "stern-bibliothek", "Filter „Favoriten“ fehlt")
        L.klick('dialog .optrow[role=radio]:nth-of-type(5)')
        L.js("[...sr.querySelectorAll('dialog .optrow[aria-pressed]')].find((b) => b.textContent.trim() === 'Favoriten').click()")
        L.ruhe()
        L.klick("dialog .knoepfe .btn.primary")
        L.pg.wait_for_function("() => window.__el.shadowRoot.querySelectorAll('a.lrow, a.rcard').length > 0", timeout=4000)
        L.ruhe()
        L.pruefe(L.js("return sr.querySelectorAll('a.lrow, a.rcard').length") >= 1, "stern-bibliothek", "Filter „Favoriten“ ohne Treffer")
        L.pruefe(L.js("return [...sr.querySelectorAll('a.lrow, a.rcard')].every((a) => !!a.querySelector('[data-favorit]'))"), "stern-bibliothek", "Nicht alle Treffer des Filters tragen den kleinen Stern")
        s = aufrufe(L, "tobibox/serien/list")[-1]
        L.pruefe(s.get("sortierung") == "meist_gehoert" and "favorit" in s.get("filter", []), "stern-bibliothek", f"Abfrage {s}")
        L.js("el._seiten.bibliothek.zuruecksetzen({ mitArt: true })")
        L.ruhe()
    with L.schritt("stern-link"):
        L.gehe("#start")
        L.gehe("#bibliothek?filter=favorit")
        L.pg.wait_for_function("() => { const o = window.__el._seiten.bibliothek; return o && o.e.filter.favorit; }", timeout=4000)
        L.js("el._seiten.bibliothek.zuruecksetzen({ mitArt: true })")
        L.ruhe()


def ablauf_technik_gehoert(L: Lauf):
    """Technik, Stufe B: Karte „Verlauf“ (Akku-Kurve mit Beschreibung und Tabelle, 7 und 30 Tage, Ladevorgänge, Box ohne Sensor) und Karte „Hördaten“ (Tabelle sichern,
    Löschen mit Anzahl und dem Wort LÖSCHEN). Nur Administratoren."""
    if L.job["rolle"] != "admin" or L.job["profil"] == "alt":
        return
    k = f"{L.job['profil']}~{L.job['kennung']}"
    with L.schritt("verlauf"):
        L.gehe("#technik-box-kueche")
        L.warte_da('[data-karte="verlauf"] [data-diagramm="akku"] svg')
        s = L.js("const s = sr.querySelector('[data-diagramm=\"akku\"] svg'); return [s.getAttribute('role'), s.getAttribute('aria-label')]")
        L.pruefe(s[0] == "img" and "Akku der letzten 7 Tage" in (s[1] or ""), "verlauf", f"Kurve ohne Beschreibung: {s}")
        L.pruefe(L.da('[data-karte="verlauf"] [data-tabelle="akku"]'), "verlauf", "Akku-Tabelle fehlt")
        L.pruefe(L.da('[data-liste="laden"] tbody tr') and L.da('[data-liste="lauf"] tbody tr'), "verlauf", "Ladevorgänge oder Laufzeit fehlen")
        L.pruefe("läuft noch" in L.js("return sr.querySelector('[data-liste=\"laden\"]').textContent"), "verlauf", "Der laufende Ladevorgang steht nicht als „läuft noch“ da")
        L.pruefe(L.js("return sr.querySelector('[data-verworfen]').textContent").startswith("3 Einträge"), "verlauf", "Verworfene Hördaten fehlen")
        v = aufrufe(L, "tobibox/technik/verlauf")[-1]
        L.pruefe(v["box"] == "kueche" and v["von"] < v["bis"], "verlauf", f"Abfrage {v}")
        L.klick('[data-karte="verlauf"] [data-wert="30"]')
        L.pg.wait_for_function("() => /30 Tage/.test(window.__el.shadowRoot.querySelector('[data-diagramm=\"akku\"] svg')?.getAttribute('aria-label') || '')", timeout=5000)
        L.ruhe()
        L.pruefe(L.js("return sr.querySelectorAll('[data-liste=\"laden\"] tbody tr').length") == 8 and L.da('[data-liste-mehr="laden"]'), "verlauf", "30 Tage: nicht erst acht Ladevorgänge mit „Alle zeigen“")
        L.klick('[data-liste-mehr="laden"]')
        L.pruefe(L.js("return sr.querySelectorAll('[data-liste=\"laden\"] tbody tr').length") > 8, "verlauf", "„Alle zeigen“ zeigt nicht mehr")
        L.klick('[data-karte="verlauf"] [data-tabelle="akku"] summary')
        L.pruefe(L.js("return sr.querySelectorAll('[data-tabelle=\"akku\"] tbody tr').length") >= 28, "verlauf", "Akku-Tabelle: zu wenige Tage")
    with L.schritt("verlauf-ohne-sensor"):
        L.gehe("#technik-box-kinderzimmer")
        L.warte_da('[data-karte="verlauf"] [data-akku-keine]')
        L.pruefe(not L.da('[data-diagramm="akku"]'), "verlauf-ohne-sensor", "Kurve ohne Akku-Sensor")
    with L.schritt("hoerdaten-sichern"):
        L.gehe("#technik-speicher")
        L.pg.wait_for_function("() => window.__el.shadowRoot.querySelectorAll('[data-karte=\"hoerdaten\"] [data-quelle] option').length > 3", timeout=6000)
        opt = L.js("return [...sr.querySelectorAll('[data-quelle] option')].map((o) => [o.value, o.textContent.trim()])")
        L.pruefe([o[0] for o in opt[:3]] == ["alle", "boxen", "reinhoeren"] and any(o[0] == "box:kueche" for o in opt) and any(o[0].startswith("benutzer:") for o in opt), "hoerdaten-sichern", f"Auswahl: {opt}")
        L.js("window.__dl = null; el._seiten.technik.hoerdaten.download = (u) => { window.__dl = u; };")
        L.pg.select_option('[data-quelle]', "box:kueche")
        L.klick('[data-aktion="hoerdaten_sichern"]')
        L.pg.wait_for_function("() => !!window.__dl", timeout=4000)
        e = aufrufe(L, "tobibox/gehoert/exportieren")
        L.pruefe(e and e[-1]["quelle"] == "box:kueche", "hoerdaten-sichern", f"Export {e}")
        L.pruefe("authSig=" in L.js("return window.__dl"), "hoerdaten-sichern", "Download ohne signierten Pfad")
    with L.schritt("hoerdaten-loeschen"):
        L.pg.select_option('[data-quelle]', "reinhoeren")
        L.klick('[data-aktion="hoerdaten_loeschen"]')
        L.warte_da("dialog[open] [data-loeschen-zahl]")
        L.pruefe("nicht rückgängig" in L.js("return sr.querySelector('dialog[open] [data-loeschen-zahl]').textContent") and "Reinhören" in L.js("return sr.querySelector('dialog[open] [data-loeschen-zahl]').textContent"), "hoerdaten-loeschen", "Anzahl und Warnung fehlen im Blatt")
        ja = "dialog[open] .knoepfe .btn.danger"
        L.pruefe(L.js("return sr.querySelector('dialog[open] .knoepfe .btn.danger').disabled"), "hoerdaten-loeschen", "„Endgültig löschen“ vor dem Wort nicht gesperrt")
        L.pruefe(all(a.get("trocken") for a in aufrufe(L, "tobibox/gehoert/loeschen")), "hoerdaten-loeschen", "Gelöscht, bevor bestätigt wurde")
        L.pg.locator("#tv-wort").fill("falsch")
        L.pruefe(L.js("return sr.querySelector('dialog[open] .knoepfe .btn.danger').disabled"), "hoerdaten-loeschen", "Falsches Wort entsperrt den Knopf")
        L.pg.locator("#tv-wort").fill("LÖSCHEN")
        L.ruhe()
        L.klick(ja)
        L.pg.wait_for_function("() => !window.__el.shadowRoot.querySelector('dialog[open]')", timeout=4000)
        L.ruhe()
        l = aufrufe(L, "tobibox/gehoert/loeschen")
        L.pruefe(l[-1].get("bestaetigung") == "LÖSCHEN" and l[-1]["quelle"] == "reinhoeren" and not l[-1].get("trocken"), "hoerdaten-loeschen", f"Löschbefehl {l[-1]}")
        L.pruefe("gelöscht" in L.toast(), "hoerdaten-loeschen", f"Meldung {L.toast()!r}")
        L.gehe("#gehoert")
        gh_zuruecksetzen(L)
        L.pruefe(not L.da('[data-wer-knopf^="benutzer:"]') or L.js("return sr.querySelectorAll('[data-wer-knopf^=\"benutzer:\"]').length") <= 1, "hoerdaten-loeschen", "Personen stehen nach dem Löschen noch in der Auswahl")


def ablauf_player_gehoert(L: Lauf):
    """Der Player sendet mit jedem `hoerstelle/set` `spieler` (eine Kennung je Player) und `spielt`; ohne die Fähigkeit `gehoert` sendet er beides nicht."""
    L.gehe("#bibliothek")
    if not L.da("a.lrow[data-serie], a.rcard[data-serie]"):
        return
    alt = L.job["profil"] == "alt"
    with L.schritt("player-spieler"):
        n0 = len(aufrufe(L, "tobibox/hoerstelle/set"))  # frühere Abläufe haben schon Hörstellen gesendet (und den Player neu geladen)
        player_start(L)
        L.js("el.spieler._speichere(true)")
        L.pg.wait_for_timeout(300)
        L.js("const a = sr.querySelector('audio'); a.pause();")
        L.pg.wait_for_timeout(500)
        sets = aufrufe(L, "tobibox/hoerstelle/set")[n0:]
        L.pruefe(len(sets) >= 2, "player-spieler", f"Nur {len(sets)} hoerstelle/set")
        if alt:
            L.pruefe(all("spieler" not in x and "spielt" not in x for x in sets), "player-spieler", "spieler/spielt ohne die Fähigkeit gehoert gesendet")
        else:
            ids = {x.get("spieler") for x in sets}
            L.pruefe(len(ids) == 1 and re.fullmatch(r"[A-Za-z0-9_-]{8,64}", next(iter(ids)) or ""), "player-spieler", f"spieler: {ids}")
            L.pruefe(any(x.get("spielt") is True for x in sets) and sets[-1].get("spielt") is False, "player-spieler", f"spielt: {[x.get('spielt') for x in sets]} (läuft, dann Pause)")
    player_aus(L)



ABLAEUFE = [ablauf_unterkante, ablauf_reiter, ablauf_klicks, ablauf_reihen, ablauf_suche, ablauf_bibliothek, ablauf_serie, ablauf_cover, ablauf_leise, ablauf_box, ablauf_technik, ablauf_blaetter,
            ablauf_tobies_weg1, ablauf_tobies_weg2, ablauf_tobies_meldung, ablauf_tobies_umhaengen, ablauf_tobies_geben, ablauf_tobies_lernmodus,
            ablauf_tobies_name_geben_weit_unten, ablauf_hinzufuegen, ablauf_eingang_liste, ablauf_anders_einsortieren, ablauf_eingang, ablauf_papierkorb, ablauf_papierkorb_punkt, ablauf_bewegung,
            ablauf_druck, ablauf_seitenwechsel, ablauf_player_bewegung, ablauf_play_pause_lage, ablauf_wechsel_serie, ablauf_flug_ruhe, ablauf_blatt_tastatur, ablauf_serie_zeile, ablauf_kapitel, ablauf_player,
            ablauf_gehoert, ablauf_stern, ablauf_technik_gehoert, ablauf_player_gehoert]


# ------------------------------------------------------------------ Browser und Läufe
# Abläufe, in denen die Seite Audio bewusst wechselt (Spulen, Folgenwechsel, Kapitelsprung, Neuladen, Fehlerwiederholung): dort sind abgebrochene Abrufe erlaubt
AUDIO_ABBRUCH_ERLAUBT = ("ablauf_player", "ablauf_kapitel", "ablauf_wechsel_serie", "ablauf_play_pause_lage", "ablauf_serie_zeile", "ablauf_player_gehoert")


def audio_pruefen(L: Lauf, abrufe: list[dict]):
    """Je Signatur (signierter Pfad) höchstens ein nicht abgebrochener Abruf von vorn (Spulen holt per Range von der Mitte, das zählt nicht);
    abgebrochene Abrufe sind nur in den Abläufen erlaubt, die bewusst wechseln. Ein doppeltes Laden derselben Datei fällt so auf."""
    je: dict[str, list] = defaultdict(list)
    for a in abrufe:
        if not a["abgebrochen"] and a["von"] == 0:
            je[(a["ablauf"], a["url"])].append(a)
        elif a["abgebrochen"] and not (a["ablauf"] or "").startswith(AUDIO_ABBRUCH_ERLAUBT) and a["ablauf"] is not None:
            L.befund("extra", "audio-abbruch", f"Abgebrochener Audio-Abruf außerhalb eines Wechsels ({a['ablauf']}): {a['url'][-60:]}")
    for (_, url), liste in je.items():  # je Ablauf: jeder Ablauf beginnt mit einem frischen Player, der Mock vergibt dieselbe Signatur im Lauf wieder
        if len(liste) > 1:
            L.befund("extra", "audio-doppelt", f"{len(liste)} Abrufe derselben Signatur nicht abgebrochen (Ablauf {liste[0]['ablauf']}, Range {[(a['req'].headers or {}).get('range') for a in liste]}): …{url[-70:]}")


def finde_browser(p):
    """Rückgabe: Argumente für chromium.launch. Reihenfolge: TOBIBOX_BROWSER, /usr/bin/google-chrome, Playwright-Chromium."""
    pfad = os.environ.get("TOBIBOX_BROWSER")
    if pfad:
        if not Path(pfad).exists():
            raise RuntimeError(f"TOBIBOX_BROWSER zeigt auf {pfad}, die Datei gibt es nicht")
        return {"executable_path": pfad}
    if Path("/usr/bin/google-chrome").exists():
        return {"executable_path": "/usr/bin/google-chrome"}
    try:
        if Path(p.chromium.executable_path).exists():
            return {}
    except Exception:  # noqa: BLE001
        pass
    raise RuntimeError("Kein Browser: TOBIBOX_BROWSER setzen oder `playwright install chromium` ausführen")


# ------------------------------------------------------------------ Service Worker von Home Assistant
# Befund im echten HA (Workbox, sw-modern.js): /api/ und /auth/ immer aus dem Netz, alles andere stale-while-revalidate aus
# dem Cache "file-cache". Die Panel-Datei hat ?v=…, ihre Untermodule (Imports ohne ?v=) kamen nach dem Einspielen beim ersten
# Öffnen aus dem alten Cache: schwarze Seite, "does not provide an export named …". Diese Prüfung stellt das nach.
SW_JS = """
const CACHE = 'file-cache';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== self.location.origin || u.pathname === '/sw.js') return;
  if (/\\/(api|auth)\\/.*/.test(u.pathname)) return;  // NetworkOnly: der Browser holt es selbst aus dem Netz
  e.respondWith((async () => {  // StaleWhileRevalidate
    const cache = await caches.open(CACHE);
    const alt = await cache.match(e.request);
    const frisch = fetch(e.request).then((r) => { if (r.ok) return cache.put(e.request, r.clone()).then(() => r); return r; });
    e.waitUntil(frisch.catch(() => {}));
    return alt || frisch;
  })());
});
"""
SW_SEITE = """<!doctype html><meta charset="utf-8"><body>laedt
<script type="module">
const q = new URLSearchParams(location.search);
await navigator.serviceWorker.register('/sw.js');
await navigator.serviceWorker.ready;
if (!navigator.serviceWorker.controller) { location.reload(); await new Promise(() => {}); }
try { await import(`PRAEFIX/app.js?v=${q.get('stand')}`); }
catch (e) { document.body.textContent = 'FEHLER ' + e.message; console.error(e.message); }
</script>"""


def sw_static_url():
    """Der Pfad, unter dem die Integration ihre Seitendateien ausliefert: STATIC_URL aus __init__.py (nicht nachgebaut, damit ein alter Pfad rot wird)."""
    quelle = (HIER.parents[2] / "custom_components" / "tobibox" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^STATIC_URL\s*=\s*"([^"]+)"', quelle, re.M)
    if not m:
        raise RuntimeError("STATIC_URL in custom_components/tobibox/__init__.py nicht gefunden")
    return m.group(1)


def sw_server(praefix):
    """Kleiner Server nur für diese Prüfung: Seite, Service Worker und zwei Stände der Dateien unter `praefix`."""
    import http.server
    import threading

    zustand = {"stand": 1}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def antwort(self, typ, text):
            self.send_response(200)
            self.send_header("Content-Type", typ)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(text.encode())

        def do_GET(self):  # noqa: N802
            pfad = self.path.split("?")[0]
            if pfad == "/sw.js":
                return self.antwort("text/javascript", SW_JS)
            if pfad == "/stand/2":
                zustand["stand"] = 2  # wie ein Einspielen: neue Dateien liegen auf dem Server
                return self.antwort("text/plain", "ok")
            if pfad == "/seite":
                return self.antwort("text/html", SW_SEITE.replace("PRAEFIX", praefix))
            if pfad == f"{praefix}/app.js":  # Panel-Datei: neue Adresse (?v=) bei jedem Stand, importiert das Untermodul ohne ?v=
                neu_ = zustand["stand"] == 2
                return self.antwort("text/javascript", "import { alt%s } from './bausteine.js';\n"
                                    "document.body.textContent = 'INHALT stand %d ' + alt%s;\n" % (", neu" if neu_ else "", zustand["stand"], " + neu" if neu_ else ""))
            if pfad == f"{praefix}/bausteine.js":
                return self.antwort("text/javascript", "export const alt = 'alt';\n" + ("export const neu = '-neu';\n" if zustand["stand"] == 2 else ""))
            self.send_response(404)
            self.end_headers()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def pruefe_service_worker(praefix=None):
    """Seite laden (der Service Worker steuert sie), Dateien auf neuen Stand bringen, neu laden: keine Konsolenfehler, Inhalt da.
    Gibt Befunde als (Kategorie, Zustand, Text) zurück. Rot, sobald die Seitendateien unter einem Pfad liegen, den der Service Worker cacht."""
    from playwright.sync_api import sync_playwright

    praefix = praefix or sw_static_url()
    befunde: list[tuple[str, str, str]] = []
    srv = sw_server(praefix)
    basis = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--no-sandbox"], **finde_browser(p))
            try:
                pg = b.new_context().new_page()
                pg.set_default_timeout(8000)
                konsole: list[str] = []
                pg.on("console", lambda m: konsole.append(m.text) if m.type == "error" else None)
                pg.on("pageerror", lambda e: konsole.append(f"pageerror: {e}"))
                pg.goto(f"{basis}/seite?stand=1")
                pg.wait_for_function("() => document.body.textContent.startsWith('INHALT')")  # nach dem ersten Neuladen steuert der SW die Seite
                if pg.evaluate("() => !navigator.serviceWorker.controller"):
                    befunde.append(("ablauf", "service-worker", "Der Service Worker steuert die Seite nicht, die Prüfung wäre wirkungslos"))
                pg.evaluate("() => fetch('/stand/2')")
                konsole.clear()
                pg.goto(f"{basis}/seite?stand=2")  # neue Panel-Adresse, wie nach einem Einspielen; die Untermodule haben dieselbe Adresse wie zuvor
                with contextlib.suppress(PlaywrightTimeout):
                    pg.wait_for_function("() => document.body.textContent.startsWith('INHALT') || document.body.textContent.startsWith('FEHLER')")
                text = pg.evaluate("() => document.body.textContent")
                if "INHALT stand 2 alt-neu" not in text:
                    befunde.append(("ablauf", "service-worker", f"Nach dem Einspielen zeigt die Seite beim ersten Öffnen nicht den neuen Stand: {text[:150]!r} (Seitendateien unter {praefix}/ vom Service Worker aus dem Cache?)"))
                for k in konsole:
                    befunde.append(("konsole", "service-worker", k[:300]))
            finally:
                b.close()
    finally:
        srv.shutdown()
    return befunde


def lauf_job(job):
    from playwright.sync_api import sync_playwright  # erst im Kindprozess

    t0 = time.time()
    konsole: list[str] = []
    ergebnis = {"job": job, "befunde": [], "hinweise": [], "zustaende": 0, "schritte": 0, "dauer": 0.0, "fehler": None}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--no-sandbox"], **finde_browser(p))
            try:
                w = job["breite"] if job["art"] in ("fenster", "ha") else 1280
                mobil = w < 700
                ctx = b.new_context(viewport={"width": w, "height": 780 if mobil else 800}, has_touch=mobil, is_mobile=mobil, locale="de-DE", timezone_id="Europe/Berlin")
                pg = ctx.new_page()
                pg.set_default_timeout(8000)
                # Gewollte Fehlerantworten des Mock-Servers beim Hochladen (A11a: 413 und 507 gehören zum Ablauf) sind keine Befunde
                gewollt = re.compile(r"status of (413|507|503)\b")  # 503: der Prüfablauf „player-fehler“ lässt den Audio-Abruf einmal scheitern
                pg.on("console", lambda m: konsole.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") and not gewollt.search(m.text) else None)
                pg.on("pageerror", lambda e: konsole.append(f"pageerror: {e}"))
                pg.on("response", lambda r: konsole.append(f"HTTP {r.status} {r.url}") if r.status >= 400 and not (r.status in (413, 507) and r.url.endswith("/api/tobibox/upload")) and not (r.status == 503 and "/api/tobibox/audio/" in r.url) else None)
                # Das Neuladen mitten im Hochladen (Ablauf „liste-neuladen“) bricht die laufende Anfrage ab: gewollt
                # Audio-Abrufe werden einzeln gezählt (AC-Rest 6): je Signatur höchstens ein Abruf von vorn, der nicht abgebrochen wird; Abbrüche nur in Abläufen, die bewusst wechseln
                audio_abrufe: list[dict] = []
                aktuell = {"ablauf": None}

                def _audio_start(r):
                    pfad = r.url.split("?")[0]
                    if "/api/tobibox/audio/" in pfad:
                        rng = (r.headers or {}).get("range", "")
                        audio_abrufe.append({"req": r, "url": r.url, "von": (int(m.group(1)) if (m := re.match(r"bytes=(\d+)-", rng)) else 0), "ablauf": aktuell["ablauf"], "abgebrochen": False})

                def _fehlgeschlagen(r):
                    abgebrochen = "ERR_ABORTED" in str(r.failure)
                    for a in audio_abrufe:
                        if a["req"] is r:
                            a["abgebrochen"] = abgebrochen
                            if abgebrochen:
                                return
                    if abgebrochen and (r.url.endswith("/api/tobibox/upload") or "/ev?" in r.url):  # Neuladen mitten im Hochladen und die Abfrage der Ereignisse: gewollt
                        return
                    konsole.append(f"requestfailed {r.url} {r.failure}")
                pg.on("request", _audio_start)
                pg.on("requestfailed", _fehlgeschlagen)
                q = f"theme={job['thema']}&k={job['profil']}~{job['kennung']}" + (f"&pw={job['breite']}" if job["art"] == "panel" else "") + ("&hs=256" if job["art"] == "ha" else "")
                pg.goto(f"{job['basis']}/seite.html?{q}")
                pg.wait_for_function("() => window.__el && window.__el.shadowRoot && window.__el.shadowRoot.querySelector('main') && window.__mess", timeout=15000)
                pg.evaluate("() => window.__ruhe()")
                bilder = Path(job["bilder"]) if job.get("bilder") else None
                L = Lauf(pg, job, bilder)
                job["layout"] = pg.evaluate("() => window.__el.getAttribute('data-layout')")
                if job["umfang"] == "seiten":
                    seiten_messen(L)
                else:
                    for f in ABLAEUFE:
                        if job.get("nur") and not any(n in f.__name__ for n in job["nur"]):
                            continue
                        aktuell["ablauf"] = f.__name__
                        with L.schritt(f.__name__):
                            L.aufraeumen()
                            f(L)
                aktuell["ablauf"] = None
                audio_pruefen(L, audio_abrufe)
                ergebnis.update(befunde=L.befunde, hinweise=L.hinweise, zustaende=L.zustaende, schritte=L.schritte)
                ergebnis["layout"] = job["layout"]
            finally:
                b.close()
    except Exception as e:  # noqa: BLE001
        ergebnis["fehler"] = f"{type(e).__name__}: {e}"
    seen = set()
    for k in konsole:
        if k not in seen:
            seen.add(k)
            ergebnis["befunde"].append(("konsole", "", k[:300]))
    ergebnis["dauer"] = round(time.time() - t0, 1)
    return ergebnis


def jobs_bauen(a, basis):
    jobs = []
    themen = a.thema or (["hell"] if a.schnell else THEMEN)
    rollen = a.rolle or ROLLEN
    breiten = [(art, w) for art, w in BREITEN if (not a.breite or w in a.breite) and (not a.schnell or w in (390, 1280))]
    n = 0

    def neu(umfang, thema, rolle, art, w, profil=None):
        nonlocal n
        if a.nur and umfang == "seiten":
            return
        n += 1
        profil = profil or ("admin" if rolle == "admin" else "user")
        jobs.append({"nur": a.nur, "umfang": umfang, "thema": thema, "rolle": rolle, "art": art, "breite": w, "profil": profil, "basis": basis, "bilder": a.bilder,
                     "kennung": f"{umfang[:3]}{n:02d}-{profil}-{thema}-{art[0]}{w}"})

    for thema in themen:
        for rolle in rollen:
            for art, w in breiten:
                neu("seiten", thema, rolle, art, w)
        # Abläufe: Telefon und Schreibtisch (Seitenleiste ab 1100 px), alle Themen, beide Rollen
        for rolle in rollen:
            for art, w in [x for x in breiten if x[1] in (390, 1280, 1440)]:
                neu("ablaeufe", thema, rolle, art, w)
        # leere Bibliothek, schwacher Akku, Warnungen
        for art, w in [x for x in breiten if x[1] in (390, 1280)]:
            if "admin" in rollen:
                neu("seiten", thema, "admin", art, w, profil="leer")
    if not a.schnell:
        for profil in ("akku", "warn"):
            for thema in themen[:1]:
                if "admin" in rollen:
                    neu("seiten", thema, "admin", "fenster", 390, profil=profil)
        # ältere HA ohne Stufe B: keine Zeile, keine Reihen, kein Stern, kein Verlauf (Seiten) und der Player sendet kein `spieler` (Ablauf)
        if "admin" in rollen:
            neu("seiten", themen[0], "admin", "fenster", 390, profil="alt")
            neu("ablaeufe", themen[0], "admin", "fenster", 390, profil="alt")
    return jobs


def server_starten():
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node nicht gefunden (Node 22 wird für den Mock-Server gebraucht)")
    proc = subprocess.Popen([node, str(HIER / "server.mjs"), "0"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    zeile = proc.stdout.readline()
    m = re.match(r"PORT (\d+)", zeile or "")
    if not m:
        proc.kill()
        raise RuntimeError(f"Server startet nicht: {zeile!r} {proc.stdout.read() if proc.stdout else ''}")
    return proc, f"http://127.0.0.1:{m.group(1)}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--schnell", action="store_true", help="nur hell, 390 und 1280 px, ohne akku/warn")
    ap.add_argument("--thema", action="append", choices=THEMEN)
    ap.add_argument("--rolle", action="append", choices=ROLLEN)
    ap.add_argument("--breite", action="append", type=int, choices=[w for _, w in BREITEN])
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 2), help="parallele Läufe")
    ap.add_argument("--bilder", help="Ordner für Bildschirmfotos der gemessenen Zustände")
    ap.add_argument("--nur", action="append", help="nur Abläufe, deren Name dies enthält (mehrfach möglich, zum Beispiel --nur tobies_weg1); lässt die Seitenmessung aus")
    ap.add_argument("--nur-sw", action="store_true", help="nur die Prüfung mit dem nachgebauten Service Worker von HA (wenige Sekunden)")
    ap.add_argument("--sw-pfad", help="Pfad für die Seitendateien in der Service-Worker-Prüfung (Standard: STATIC_URL der Integration)")
    ap.add_argument("--json", help="Befunde als JSON in diese Datei schreiben")
    ap.add_argument("--zeige", type=int, default=6, help="Beispiele je Gruppe in der Zusammenfassung")
    a = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print("Das Python-Paket playwright fehlt (pip install playwright).", file=sys.stderr)
        return 2
    try:
        proc, basis = server_starten()
    except RuntimeError as e:
        print(f"Aufbau fehlgeschlagen: {e}", file=sys.stderr)
        return 2
    try:
        sw_befunde = pruefe_service_worker(a.sw_pfad)
    except Exception as e:  # noqa: BLE001
        sw_befunde = [("ablauf", "service-worker", f"Prüfung abgebrochen: {type(e).__name__}: {e}")]
    print(f"Service Worker (Dateien unter {a.sw_pfad or sw_static_url()}): {'OK' if not sw_befunde else str(len(sw_befunde)) + ' Befunde'}", flush=True)
    if a.nur_sw:
        proc.terminate()
        for _, _, t in sw_befunde:
            print("  ", t)
        print("\nERGEBNIS:", "alles in Ordnung" if not sw_befunde else f"{len(sw_befunde)} Befunde")
        return 1 if sw_befunde else 0
    jobs = jobs_bauen(a, basis)
    print(f"{len(jobs)} Läufe, {a.jobs} parallel, Server {basis}", flush=True)
    ergebnisse = []
    ergebnisse.append({"job": {"profil": "sw", "thema": "-", "art": "-", "breite": 0, "kennung": "sw"}, "befunde": sw_befunde, "hinweise": [], "zustaende": 0, "schritte": 1, "dauer": 0.0, "fehler": None})
    try:
        with cf.ProcessPoolExecutor(max_workers=a.jobs) as ex:
            for r in ex.map(lauf_job, jobs):
                ergebnisse.append(r)
                j = r["job"]
                n = len([x for x in r["befunde"]])
                print(f"{'FEHLER' if r['fehler'] else ('OK    ' if not n else 'BEFUND')} {j['kennung']:34} Layout {r.get('layout', '-'):6} {r['zustaende']:3} Zustände {r['schritte']:3} Prüfungen {n:3} Befunde {r['dauer']:5.1f}s"
                      + (f"  {r['fehler']}" if r["fehler"] else ""), flush=True)
    finally:
        proc.terminate()
    return zusammenfassung(ergebnisse, a)


def zusammenfassung(ergebnisse, a):
    gruppen = defaultdict(lambda: defaultdict(set))  # Kategorie → (Zustand, Text) → Läufe
    hinweise = defaultdict(set)
    fehler = []
    for r in ergebnisse:
        j = r["job"]
        lauf = f"{j['profil']}/{j['thema']}/{j['art'][0]}{j['breite']}"
        if r["fehler"]:
            fehler.append((lauf, r["fehler"]))
        for kat, zustand, text in r["befunde"]:
            gruppen[kat][(zustand, text)].add(lauf)
        for zustand, text in r["hinweise"]:
            hinweise[(zustand, text)].add(lauf)
    print("\n================ Zusammenfassung ================")
    print(f"Läufe: {len(ergebnisse)}, gemessene Zustände: {sum(r['zustaende'] for r in ergebnisse)}, Prüfungen in Abläufen: {sum(r['schritte'] for r in ergebnisse)}")
    anzahl = 0
    for kat in KATEGORIEN:
        g = gruppen.get(kat)
        if not g:
            print(f"  {kat:8} keine Befunde")
            continue
        anzahl += len(g)
        print(f"  {kat:8} {len(g)} verschiedene Befunde")
        for (zustand, text), laeufe in sorted(g.items(), key=lambda x: (-len(x[1]), x[0]))[: a.zeige]:
            ls = sorted(laeufe)
            print(f"      [{zustand or '-'}] {text}  ({len(ls)} Läufe: {', '.join(ls[:3])}{' …' if len(ls) > 3 else ''})")
        if len(g) > a.zeige:
            print(f"      … und {len(g) - a.zeige} weitere (mit --zeige {len(g)} alle)")
    if hinweise:
        print(f"  Hinweise aus der alten Komponente (tobibox-panel, nicht Teil von A-1a, zählen nicht): {len(hinweise)}")
        for (zustand, text), laeufe in list(sorted(hinweise.items(), key=lambda x: -len(x[1])))[:3]:
            print(f"      [{zustand}] {text}  ({len(laeufe)} Läufe)")
    for lauf, f in fehler:
        print(f"  LAUF ABGEBROCHEN {lauf}: {f}")
    if a.json:
        Path(a.json).write_text(json.dumps({
            "befunde": {k: [{"zustand": z, "text": t, "laeufe": sorted(l)} for (z, t), l in g.items()] for k, g in gruppen.items()},
            "hinweise": [{"zustand": z, "text": t, "laeufe": sorted(l)} for (z, t), l in hinweise.items()],
            "fehler": fehler}, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = not anzahl and not fehler
    print("\nERGEBNIS:", "alles in Ordnung" if ok else f"{anzahl} Befunde, {len(fehler)} abgebrochene Läufe")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
