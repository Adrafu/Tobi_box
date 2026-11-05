# Goldfisch-Review Stufe 5 — Zoom-out

**Ziel:** `design_draft.md` (ganze Datei) · **Maßstab:** EGM zoom-out-standard ·
**Prüfer:** frischer Agent (Sonnet), kein Gesprächsverlauf · **Datum:** 2026-11-05

Gesamturteil des Goldfischs: Kern schlank und gut geschnitten (reine Logik im
Kern, Protokoll als Vertrag, MPD, HA als einzige Oberfläche). Für ein
Ein-Personen-Projekt aber zu breit; größter Hebel ist Stufe 3.

| # | Schwere | Befund | Bereich |
|---|---|---|---|
| 1 | Blocker | Eigene HA-Integration mit Lit-Seite ist das größte Bauteil, größer als die Box-Software; stellt D1/D4 ausdrücklich in Frage. Vorschlag: erst Bordmittel / Integration ohne Seite, Seite als spätere Stufe 4. | Baustein 4, D1, D4, AP 3.1/3.2 |
| 2 | Major | `serie.json` erzwingt NAS-Schreibrecht für HA und Reparaturlogik (fehlend, doppelte IDs nach Ordnerkopie). Vorschlag: Ordnername als feste ID, Anzeigename in HA; sonst Regeln für doppelte IDs und Box ohne `serie.json`. | D2, Datenmodell |
| 3 | Major | Update-System zu groß (eigener Wächter, Szenarien im Selbsttest, Wheels). Vorschlag: zwei Verzeichnisse + Verweis, Rückfall über systemd (`OnFailure=`/Startzähler), Selbsttest = Dienst + `HELLO`. | Update, AP 3.5 |
| 4 | Major | Stufe 0 mit fünf Dokumenten zu schwer. Vorschlag: nur Protokoll + Kennungsformat; Datenmodell wächst mit der Stufe; `timing.md` als Messergebnis. | Stufe 0 |
| 5 | Major | Zu tiefe Details im Design (Funktionssignaturen, Ereignislisten, Dateinamen). Vorschlag: Design auf Schnittstellen + Abnahmen, Details in die AP-Aufträge. | Baustein 3, Umsetzung |
| 6 | Major | Eigenes Szenario-Format + Parser + CLI = Mini-Testframework. Vorschlag: pytest-Tabellen. | Baustein 3, AP 1.2 |
| 7 | Major | Eigener Ringpuffer = Logging-Infrastruktur. Vorschlag: Python `logging` mit JSON + `RotatingFileHandler`, journald persistent; Vorgangs-ID als Log-Feld. | Fehlersuche |
| 8 | Major | Alternativen-Text lehnt MQTT ab, Entwurf nutzt es als Verteilkanal; Revisionsregel fehlt. Vorschlag: „MQTT nur Verteilkanal“, höhere Revision gewinnt. | HA, Alternativen |
| 9 | Major | Netz-Klassen und Akku-Regel hängen an fehlender Hardware und nicht eingerichtetem Tailscale; mit simulierten Eingängen wenig Aussagekraft. Vorschlag: erst „NAS erreichbar ja/nein“. | Netz, Sync, Strom |
| 10 | Major | rsync kann eine gerade spielende Datei ersetzen; „stockt nicht“ ist unbegründet; Last auf dem Pi. Vorschlag: Regel festlegen (spielende Datei nie ersetzen / Sync im Leerlauf), `nice`/`ionice`. | Sync, CUJ 9 |
| 11 | Nit | Q1/Q3 sind spekulativ; entscheiden oder streichen. | Open Questions |
| 12 | Nit | Vier Status-Wege; Tonfolge je Prüfpunkt vorab nicht prüfbar. Vorschlag: erst `tobibox status` + ein Fehlerton. | Fehlersuche |
| 13 | Nit | `admin_cards.json` überflüssig; Admin-Karten als Zuordnung mit Typ „Aktion“. | Datenmodell |
| 14 | Nit | Inkonsistenzen: Brief beschreibt oben noch V3; Q5/Q6 sind erledigt, gehören nicht zu offenen Fragen; Herkunft der Wheels unklar. | mehrere |
| 15 | Nit | Risikoliste fehlt; Go/No-Go-Überschrift ohne Kriterien. | Open Questions, Go/No-Go |

## Bewertung durch die Projektleitung (Vorschlag an Tobias)

| # | Vorschlag |
|---|---|
| 1 | **Teilweise:** D4 bleibt (Tobias' Entscheidung). Die eigene Seite und die Medienverwaltung werden aber eine **eigene Stufe 4**; Stufe 3 baut die Integration ohne Seite (Zuordnen, Lernmodus, Status als HA-Aktionen und Entitäten). |
| 2 | **Teilweise:** D2 bleibt. Ergänzt: Box spielt auch ohne `serie.json` (dann Ordnername als ID, Dateiname als Reihenfolge); doppelte IDs → Integration vergibt neue ID für die jüngere Kopie und meldet es. |
| 3 | **Ja, vereinfacht:** Verweis + systemd-Rückfall, Selbsttest = Dienst läuft, `HELLO` passt, MPD antwortet, Testton. HA-Knopf bleibt (Tobias' Wunsch). |
| 4 | **Ja.** |
| 5 | **Teilweise:** Funktionssignaturen und Ereignislisten raus aus dem Technischen Plan; Dateitabellen bleiben im Umsetzungsplan (EGM verlangt dort jede Datei). |
| 6 | **Ja.** |
| 7 | **Ja.** |
| 8 | **Ja.** |
| 9 | **Teilweise:** Regel bleibt (Tobias' Entscheidung), Umsetzung mit Simulation; echte Prüfung erst mit PiSugar und Tailscale, als Risiko vermerkt. |
| 10 | **Ja:** Eine gerade spielende Datei wird nie ersetzt (Änderung wird verschoben), Sync mit niedriger Priorität. |
| 11 | **Ja:** Q1 bleibt reserviert; **Lautstärke-Obergrenze kommt in Stufe 1** (Kinderohren), Gute-Nacht-Karte wird Nicht-Ziel des Prototyps. |
| 12 | **Ja:** erst `tobibox status`, HA-Sensoren und ein Fehlerton; Status-Karte mit einfacher Tonfolge in Stufe 2. |
| 13 | **Ja.** |
| 14 | **Ja.** |
| 15 | **Ja.** |
