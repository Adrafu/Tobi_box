# Abnahme A-1a: Befunde der lokalen Sichtprüfung

Stand 13.11.2026. Lokale Claude-Sitzung auf Tobias’ Mac, eingebauter Browser der Claude-App (Chromium 152), echtes
Home Assistant im Heimnetz, dunkles Theme. Code nicht geändert.

## Umgebung

| Was | Wert |
|---|---|
| Home Assistant | 2026.11.1 |
| Geladenes Skript | `/tobibox_static/tobibox-app.js?v=0.1.0` (`module_url` aus `hass.panels.tobibox.config`) |
| Stand auf dem Server | identisch mit dem Repo (Commit 3686734): alle 12 Dateien der Seite (`tobibox-app.js`, `texte.js`, `bausteine.js`, `illustrationen.js`, `seiten/*.js`) frisch vom Server geholt (`cache: 'no-store'`) und mit dem Repo verglichen, Länge und Prüfsumme gleich |
| Browser-Cache | lieferte dieselben Fassungen wie der Server |
| Antwort-Kopf der Dateien | kein `Cache-Control`, nur `ETag` und `Last-Modified` (13.11. 08:44 bzw. 09:02 UTC) |
| Konsole | keine Meldungen, keine Fehler (alle Seiten, schmal und breit) |
| Geprüfte Breiten | 390 × 844 (Handy), 1440 × 900 (Desktop, Panel 1184 px), 1280 × 800 (Panel 1024 px) |

## B1 – Reiter und alle Links in der App reagieren nicht (AB2) — **Ursache belegt**

**Beobachtung (Screenshots):**
- Handy-Breite, Start: Reiterleiste sitzt sauber am unteren Rand, sichtbar, nichts verdeckt sie.
- Klick auf „Bibliothek“: Adresszeile wechselt auf `/tobibox#bibliothek`, die Seite zeigt aber weiter „Guten Morgen“
  mit dem Start-Inhalt; der Reiter „Start“ bleibt markiert.
- Gleiches mit „Geräte“, mit einer Kachel auf Start (`#serie-…`) und mit einer Zeile in der Bibliothek: Adresse
  ändert sich, Inhalt nicht.
- Desktop (eigene Seitenleiste links): Klick auf „Bibliothek“ genauso ohne Wirkung.
- Was funktioniert: die Seite direkt mit Adresse laden (`/tobibox#bibliothek`), die Zurück-Taste des Browsers, die
  Adresse von Hand ändern.

**Messung (Ereignisse am `window` mitgeschrieben, dann Klick auf „Geräte“):**

```
pushState /tobibox#geraete stack:    at C (http://homeassistant.local:8123/frontend_latest/app.5ce0ede93b3f9512.js:2:37493)
location-changed #geraete
click(window,bubble) defaultPrevented=true
```

Danach: `location.hash = "#geraete"`, aber `tobibox-app._hash = ""` (die App hat nichts mitbekommen).

Bei der Zurück-Taste dagegen:

```
popstate #bibliothek
hashchange #bibliothek
```

**Ursache:** Home Assistant fängt Klicks auf Links im eigenen Frontend ab (`preventDefault`), ändert die Adresse
selbst mit `history.pushState` und meldet das mit dem Ereignis `location-changed`. `pushState` löst **kein**
`hashchange` aus. Die App hört aber nur auf `hashchange` (`tobibox-app.js`, Zeile 374:
`window.addEventListener('hashchange', this._onHash)`). Deshalb wechselt die Adresse, aber nicht die Seite. Das trifft
jeden `<a href="#…">` der App: Reiter, Seitenleiste, Kacheln, Zeilen, „‹ Bibliothek“, Suche- und Technik-Knopf.

Die Klicks kommen also an. Nichts ist verdeckt oder liegt außerhalb des Bildschirms, und der Cache ist es auch nicht.

**Warum das Cloud-Prüfskript es nicht sieht (belegt im Code):** `homeassistant/tests/frontend/browser/seite.html`
bettet die App ohne Home Assistant ein. Dort gibt es niemanden, der Link-Klicks abfängt. Der Browser springt selbst
zum Anker und löst `hashchange` aus, also klappt dort alles. `pruefe_seite.py` stellt Seiten außerdem mit
`location.hash = …` ein (`gehe`, Zeile 87), und dabei kommt auch im echten HA ein `hashchange`.

**Vorschlag:**
1. App: zusätzlich auf `location-changed` (am `window`) und `popstate` hören und dann `_leseHash()` aufrufen
   (gleicher Handler wie `_onHash`, ohne doppelte Wirkung, weil `_leseHash` nur bei geändertem Hash setzt). Abmelden in
   `disconnectedCallback` nicht vergessen. Den Fokus- und Scroll-Teil von `_onHash` nur ausführen, wenn sich der Hash
   wirklich geändert hat.
2. Prüfskript: In `seite.html` den Klick-Abfang von HA nachbauen: Klick auf `a[href^="#"]` (über `composedPath`,
   also auch im Shadow DOM) → `preventDefault`, `history.pushState(null, '', href)`, dann
   `window.dispatchEvent(new CustomEvent('location-changed'))`. Dann schlägt `ablauf_reiter` heute fehl (dort wird
   `aria-current` schon geprüft) und nach der Korrektur nicht mehr.
3. Am Handy (HA-App) nach der Korrektur noch einmal prüfen; die Ursache ist dieselbe, weil die Companion-App dasselbe
   Frontend lädt (Vermutung, dort nicht gemessen).

## B2 – Desktop sieht leer und unfertig aus (AB3)

**Beobachtung (1440 × 900, Screenshots):**
- **Zwei Seitenleisten nebeneinander:** die von HA (256 px) und die eigene mit Kopf „Tobi Box“ (264 px). Zusammen
  520 px Navigation, für den Inhalt bleiben 920 px. Die eigene Leiste hat nur vier Einträge und unten zwei kleine
  runde Knöpfe (Plus, Werkzeug); darüber viel leere Fläche.
- **Start:** Kurzwahl in zwei Spalten mit flachen, breiten Zeilen (Cover nur ca. 55 px hoch). „Neu hinzugefügt“ als
  Reihe kleiner Cover (ca. 110 px) mit sichtbarer Scrollleiste darunter. Unter den beiden Blöcken bleiben rund zwei
  Drittel des Fensters leer. Die Begrüßung „Guten Morgen“ ist klein und wirkt nicht wie ein Seitenkopf.
- **Bibliothek:** eine einfache Liste über die volle Breite, Cover klein links, Zahl der Tobies ganz rechts. Wirkt
  wie die Handy-Ansicht in die Breite gezogen.
- **Serienseite:** Cover links, Name rechts daneben; die Folgenliste über die volle Breite. In Ordnung, aber leer.
- **Geräte:** Box-Karte nur halb breit, darunter „Abends“ mit Karten über die volle Breite. Gute-Nacht-Knöpfe als
  umrandete Pillen (bekannt aus AB4), die Auswahl zeigt „1 Minuten“.
- **Technik:** Liste der Unterseiten über die volle Breite, sonst leer.
- **Suche:** Suchfeld über die ganze Breite, darunter nur der Hinweis „Tippe mindestens 2 Buchstaben.“
- **1280 × 800 (Panel 1024 px, Reiter oben):** Reiter stehen linksbündig in den ersten 720 px, rechts daneben leer;
  Inhalt sonst wie oben.

**Ursache:** Es gibt (noch) keine eigene Desktop-Gestaltung. Die Breite ab 1100 px schaltet nur die Navigation um
(eigene Seitenleiste statt Reiter); die Seiten selbst nutzen dieselben Bausteine wie am Handy. Zusammen mit der
HA-Seitenleiste wirkt das schwer links und leer rechts. Das deckt sich mit der Festlegung AB3 in `resolve.md`.

**Vorschlag:** AB3 wie festgelegt umsetzen und dabei die HA-Seitenleiste mitdenken:
- Eigene Seitenleiste schmaler (z. B. 200–220 px) oder erst ab größerer Panelbreite; bei 1024–1300 px Panel lieber
  Reiter oben, zentriert über dem Inhalt.
- Inhalt mit Höchstbreite **und** zentriert; Start mit größeren Kacheln (Cover ≥ 160 px), „Neu hinzugefügt“ ohne
  sichtbare Scrollleiste oder als Raster.
- Bibliothek als Cover-Raster, Liste als Umschalter.
- Geräte-Karten nebeneinander, Abends-Karten in zwei Spalten.
- Prüfskript: Desktop-Lauf mit nachgebauter HA-Seitenleiste (256 px links), damit die Breiten wie im echten HA sind.

## B3 – Kleinere Befunde (schmal, 390 px)

- **Doppelte Überschrift** (bekannt aus AB4): Kopf „Tobi Box“ und darunter Seitentitel („Bibliothek“, „Technik“,
  „Geräte“). Auf der Serienseite steht oben „Tobi Box“, darunter „‹ Bibliothek“.
- **„1 Minuten“** in der Auswahl der Gute-Nacht-Karte (Geräte → Abends): Einzahl fehlt („1 Minute“).
- Auf der Suche ist der Reiter „Bibliothek“ markiert. Falls gewollt (Suche gehört zur Bibliothek), in Ordnung.
- Sonst schmal unauffällig: Leiste unten, keine Überlappung, Mini-Leiste nicht sichtbar (kein Abspielen aktiv).

## B4 – Cache: diesmal nicht die Ursache, aber ein Risiko — **Vermutung**

- Der Skript-Pfad trägt `?v=0.1.0` aus `manifest.json`. Diese Zahl ändert sich bei keinem Commit, also ändert sich
  auch die Adresse nie.
- Die Unter-Module (`texte.js`, `seiten/*.js`, …) werden ganz ohne `?v=` geladen.
- Die statischen Dateien kommen ohne `Cache-Control` (`cache_headers=False` in `__init__.py`). Browser dürfen solche
  Dateien nach eigener Faustregel eine Weile aus dem Cache nehmen, ohne nachzufragen. In diesem Browser war alles
  aktuell, am iPhone (HA-App) ist das nicht geprüft.

**Vorschlag:** Version im `?v=` aus dem Inhalt der Dateien bilden (z. B. Prüfsumme oder jüngster Änderungszeitpunkt
des Ordners `frontend/`) und an die Unter-Module weitergeben, oder für `/tobibox_static` `Cache-Control: no-cache`
senden. Bis dahin bei Abnahmen am Handy die HA-App einmal ganz schließen bzw. „Frontend-Cache leeren“.
