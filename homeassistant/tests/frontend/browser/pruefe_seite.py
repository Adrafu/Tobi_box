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
              if (el.getAttribute('data-layout') === 'unten') {
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
    with L.schritt("geraete-abends"):
        L.gehe("#geraete")
        L.js("sr.querySelector('h2.abends')?.scrollIntoView()")
        L.messe("geraete-abends")
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
        L.pruefe(L.hash() == "#bibliothek" and L.da("[data-liste=bibliothek], [data-leer]"), "klick-zurueck", f"Zurück-Link zeigt die Bibliothek nicht ({L.hash()})")
        L.pg.go_back()
        L.ruhe()
        L.pruefe(L.js("return location.hash").startswith("#serie-") and L.da(".se-hero"), "klick-browser-zurueck", "Zurück-Taste des Browsers wechselt die Seite nicht")
    with L.schritt("klick-alle-anzeigen"):
        L.gehe("#start")
        L.pg.locator("a.alle").first.click(timeout=5000)
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


ABLAEUFE = [ablauf_unterkante, ablauf_reiter, ablauf_klicks, ablauf_reihen, ablauf_suche, ablauf_bibliothek, ablauf_serie, ablauf_cover, ablauf_leise, ablauf_box, ablauf_technik, ablauf_blaetter,
            ablauf_tobies_weg1, ablauf_tobies_weg2, ablauf_tobies_meldung, ablauf_tobies_umhaengen, ablauf_tobies_geben, ablauf_tobies_lernmodus,
            ablauf_tobies_name_geben_weit_unten, ablauf_hinzufuegen, ablauf_eingang]


# ------------------------------------------------------------------ Browser und Läufe
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
                gewollt = re.compile(r"status of (413|507)\b")
                pg.on("console", lambda m: konsole.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") and not gewollt.search(m.text) else None)
                pg.on("pageerror", lambda e: konsole.append(f"pageerror: {e}"))
                pg.on("response", lambda r: konsole.append(f"HTTP {r.status} {r.url}") if r.status >= 400 and not (r.status in (413, 507) and r.url.endswith("/api/tobibox/upload")) else None)
                pg.on("requestfailed", lambda r: konsole.append(f"requestfailed {r.url} {r.failure}"))
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
                        with L.schritt(f.__name__):
                            L.aufraeumen()
                            f(L)
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
    jobs = jobs_bauen(a, basis)
    print(f"{len(jobs)} Läufe, {a.jobs} parallel, Server {basis}", flush=True)
    ergebnisse = []
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
