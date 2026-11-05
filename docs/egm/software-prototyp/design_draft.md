# Tobi Box — Box-Software (Prototyp und Zielsystem)

*   **Autor:** Tobias (Projektleitung: Claude)
*   **Status:** Draft
*   **Datum:** 2026-11-05
*   **Grundlage:** `concepts_brief.md` (gleicher Ordner) inkl. Entscheidungen
    Runde 1 und 2

--------------------------------------------------------------------------------

## Overview

Die Tobi Box ist eine mobile NFC-Audiobox für zwei Kleinkinder. Ein Kind legt
eine Figur (echter Tonie) oder eine NFC-Karte auf, und die Box spielt das
zugehörige Hörspiel vom eigenen Bestand. Dieses Dokument beschreibt die
komplette Software der Box:

- **Firmware** auf einem ESP32-S3 mit PN5180-Leser: liest Karten und Tonies,
  entsperrt Tonies, entscheidet „liegt auf“ / „abgehoben“ und meldet das über
  ein festes Textprotokoll per USB-Serielle.
- **Box-Dienst** (Python) auf dem Rechner der Box: steuert MPD, führt Resume,
  Serien und Zuordnungen, spricht per MQTT mit Home Assistant, holt Medien vom
  NAS, führt Updates aus.
- **Home-Assistant-Anbindung**: die einzige Bedienoberfläche der Eltern.

Die Software läuft zuerst auf einem Mac (natives MPD, ESP32 per USB am Mac)
und danach auf dem Raspberry Pi 3A+ der Box. Unser Code ist auf beiden
gleich; es unterscheidet sich nur die Konfiguration.

## The Problem

Tobias will zwei Boxen bauen, an denen danach nicht mehr programmiert und
gesucht werden muss. Die Box muss sich genau so verhalten, wie er es sich
vorstellt — auch mit geborgten Figuren, unterwegs ohne Netz und nach einem
leeren Akku.

Die bisherige Planung (Rev. 3.7) setzte auf Phoniebox V3 mit Plugins und
einem Leser, der sich als USB-Tastatur meldet. Recherche und Goldfisch-Prüfung
haben gezeigt: Phoniebox kann weder Resume noch eine sichere Abhebe-Meldung,
eine Tastatur kann keine Fehler melden, und am Mac wäre der Aufbau nur mit
Docker und einer Brücke testbar. Fast alles, was die Box besonders macht,
wäre ohnehin eigener Code.

Lösung: eine eigene, schlanke Box-Software direkt auf MPD, ein festes
Protokoll zum Leser, Home Assistant als einzige Oberfläche, und ein Aufbau,
der am Mac mit echtem Leser vollständig testbar ist, bevor die Box steht.

## Goals

1.  **Verhalten wie beschrieben.** Alle Abläufe in „Critical User Journeys“
    funktionieren am Mac mit dem echten Leser und laufen als automatische
    Tests ohne Leser.
2.  **Zeitgrenzen eingehalten:**
    - Ton spätestens **1,0 s** nach dem Auflegen einer bekannten Figur
      (Medium lokal vorhanden).
    - Pause spätestens **1,5 s** nach dem Abheben.
    - Lese-Lücken bis **1,0 s** führen zu keiner Pause und keinem Neustart.
3.  **Gleicher Code auf Mac und Pi.** Unterschiede nur in einer
    Konfigurationsdatei (Gerätepfad, Audio-Ausgabe, Pfade, Netz-Erkennung).
4.  **Die Box spielt ohne Netz und ohne Home Assistant** alles, was sie schon
    kennt und lokal hat.
5.  **Kein Zustand geht durch Stromausfall verloren oder kaputt.** Jede Datei
    wird atomar geschrieben und beim Start geprüft; höchstens der letzte
    Resume-Stand (≤ 30 s Wiedergabe) darf fehlen.
6.  **Fehler sind ohne Laptop eingrenzbar:** Status-Admin-Karte, Statusbefehl
    per SSH, einheitliches Ereignisprotokoll, das einen Stromausfall übersteht.
7.  **Updates sind sicher:** nur manuell aus HA, nur daheim am Lader, mit
    Selbsttest; schlägt er fehl, läuft automatisch wieder die alte Version.
8.  **Beide Boxen** laufen aus demselben Paket und erhalten dieselben
    Zuordnungen.

## Non-Goals

*   LED-Ring, PiSugar/Akku-Hardware, Tasten/Encoder, Kopfhörer, Leise-Zeiten —
    die Hardware fehlt. Der Dienst sieht nur Schnittstellen dafür vor
    (Akkustand und Lader kommen im Prototyp aus einer Simulation).
*   Eigener WLAN-Hotspot der Box.
*   Erreichbarkeit der Box aus dem Internet; Zugriff von außen nur über HA
    (Nabu Casa) und Tailscale.
*   Betriebssystem- und Kernel-Updates über die Update-Funktion (dafür gibt
    es ein neues SD-Image).
*   Automatisches Erkennen, welche Figur ein Tonie ist (Zuordnung einmal pro
    Exemplar). Geprüft in `research_tonie_erkennung.md`: Auf dem Chip steht
    nur eine Seriennummer; die echte Toniebox fragt die Tonie-Cloud, und eine
    öffentliche Liste „Kennung → Figur“ gibt es nicht.
*   Streaming-Dienste, Mikrofon, Aufnahme.
*   Nachbau von Phoniebox-Funktionen auf Vorrat (nur was eine Stufe braucht).

## Open Questions

*   **Q1 — Leser-Rückkanal:** Soll der Box-Dienst dem ESP32 etwas
    zurückschicken (z. B. Poll-Intervall ändern, Neustart)? Im Prototyp
    reserviert, nicht gebaut.
*   **Q2 — Audio-Rückmeldungen:** Welche Töne gibt es (Start, Überraschung,
    Fehlerklassen, Lernmodus, Status-Karte)? Klärt der Abschnitt
    Technical Plan; eigene Tonaufnahmen von Tobias möglich.
*   **Q3 — Gute-Nacht-Karte und Lautstärke-Grenze:** in welcher Stufe?
*   **Q4 — Pi-Probelauf:** Termin hängt an der Bestellung des Pi 3A+.
*   **Q5 — Medienverwaltung in HA:** Geklärt (05.11.): Serien anlegen und
    umbenennen, Folgen sortieren und löschen, mp3 vom Handy hochladen,
    Überraschungs-Ordner befüllen, Zuordnungen je Serie sehen — **keine
    Bilder**. Es gibt noch keine Hörspiele; die Sammlung wächst aus vielen
    Quellen. Folge: Dateien kommen auch am HA vorbei aufs NAS (z. B. vom PC);
    die Integration erkennt neue Ordner und Dateien selbst. Folgen-Reihenfolge
    steht in `serie.json` (nicht nur Dateiname). Offen: andere Formate als mp3
    (m4a, flac …) umwandeln oder nur warnen; Lautheitsangleich (Plan 7.2).
*   **Q6 — Oberfläche der Medienverwaltung:** Entschieden (D4, 05.11.):
    **eigene Seite in HA**, siehe Baustein 4.

## Critical User Journeys (CUJs)

Begriffe: **Figur** = Tonie oder NFC-Karte. **Serie** = Ordner mit Folgen
(mp3). **Überraschungs-Ordner** = Serie für unbekannte und gesperrte Figuren.

### CUJ 1: Bekannte Figur auflegen

*   **Given**: Figur ist einer Serie zugeordnet, Folgen liegen lokal, kein
    gespeicherter Stand für diese Serie auf dieser Box.
*   **When**: Kind legt die Figur mittig auf.
*   **Then**: Innerhalb von 1,0 s startet Folge 1 der Serie. Das Protokoll
    zeigt die Kette gelesen → entprellt → zugeordnet → spielt mit einer
    Vorgangs-ID.

### CUJ 2: Abheben

*   **Given**: Eine Figur liegt, ihre Serie spielt.
*   **When**: Kind nimmt die Figur weg.
*   **Then**: Innerhalb von 1,5 s Pause. Folge und Position sind für diese
    Serie gespeichert.

### CUJ 3: Dieselbe Figur wieder auflegen (Resume)

*   **Given**: Für die Serie gibt es einen gespeicherten Stand (Folge, Position).
*   **When**: Kind legt eine Figur dieser Serie auf — auch nach Neustart oder
    leerem Akku.
*   **Then**: Wiedergabe läuft an der gespeicherten Stelle weiter
    (Rücksprung von ein paar Sekunden erlaubt, Wert im Design).

### CUJ 4: Andere Figur auflegen

*   **Given**: Serie A ist pausiert oder spielt, Figur von Serie B wird aufgelegt.
*   **When**: Kind wechselt die Figur.
*   **Then**: Stand von Serie A bleibt gespeichert. Serie B läuft an ihrem
    gespeicherten Stand weiter; ohne Stand beginnt sie bei der nächsten noch
    nicht gehörten Folge. Ist die Serie durchgehört, beginnt sie wieder bei
    Folge 1.

### CUJ 5: NFC-Karte

*   **Given**: Eine NTAG215-Karte ist einer Serie zugeordnet.
*   **When**: Kind legt die Karte auf.
*   **Then**: Verhalten wie CUJ 1–4.

### CUJ 6: Gesperrter Tonie (Passwort unbekannt)

*   **Given**: Ein Tonie im Privacy-Modus, der sich mit unserem Passwort nicht
    entsperren lässt.
*   **When**: Kind legt ihn auf.
*   **Then**: Überraschungs-Ordner spielt. Kurze Aussetzer starten ihn nicht
    neu. Nicht zuordenbar (keine Kennung).

### CUJ 7a: Unbekannte Figur, Zuordnung danach (Weg A)

*   **Given**: Lesbare Figur ohne Zuordnung. Box offline oder online.
*   **When**: Kind legt sie auf.
*   **Then**: Überraschungs-Ordner spielt sofort. Die Box merkt sich die
    Kennung und meldet sie an HA, sobald HA erreichbar ist. HA zeigt „neue
    Figur“. Tippt Tobias eine Serie an, schreibt HA die Zuordnung; die Box holt
    sie und wechselt, wenn die Figur noch liegt, sofort auf die Serie.

### CUJ 7b: Lernmodus (Weg B)

*   **Given**: Box ist online. Tobias wählt in HA „Jetzt kommt ein neuer
    Tonie“ und eine Serie.
*   **When**: Innerhalb von 2 min wird eine Figur aufgelegt.
*   **Then**: Box meldet die Kennung an HA, HA schreibt die Zuordnung, die
    Serie spielt. Ist die Figur schon zugeordnet, fragt HA vor dem Überschreiben
    nach. Ohne Figur endet der Lernmodus nach 2 min; Abbruch jederzeit in HA.
    Beginn und Ende sind hörbar.

### CUJ 8: Figur am Rand oder kurz verrutscht

*   **Given**: Eine Figur spielt.
*   **When**: Sie verrutscht, die Lesungen setzen bis 1,0 s aus, oder am Rand
    kommt einmal eine verfälschte Kennung.
*   **Then**: Keine Pause, kein Neustart, kein falsches Hörspiel. Erst wenn
    eine neue Kennung 2–3× gleich gelesen wurde, gilt sie.

### CUJ 9: Neue Folgen kommen auf die Box

*   **Given**: Neue mp3 liegen auf dem NAS. Box im Heimnetz, oder im
    Handy-Hotspot und (am Lader oder Akku > 50 %).
*   **When**: Der Abgleich läuft (zeitgesteuert oder von HA angestoßen).
*   **Then**: Neue und geänderte Dateien kommen über Tailscale auf die Box,
    halbe Dateien sind nie abspielbar, laufende Wiedergabe stockt nicht.
    HA zeigt Stand und Zeitpunkt.

### CUJ 10: Software-Update

*   **Given**: Box daheim, am Lader, spielt nicht.
*   **When**: Tobias stößt in HA das Update an.
*   **Then**: Neue Version wird daneben installiert, umgeschaltet, Selbsttest
    läuft. Bestanden → bleibt. Nicht bestanden oder kein Start → beim nächsten
    Start automatisch alte Version. HA zeigt Ergebnis und Grund.

### CUJ 11: „Spielt nicht“ — Fehlersuche ohne Laptop

*   **Given**: Box spielt nicht, kein Handy zur Hand.
*   **When**: Tobias legt die Status-Admin-Karte auf.
*   **Then**: Die Box sagt an bzw. tönt, was nicht stimmt (Leser, Medien,
    Netz, Speicher). Mit SSH zeigt `tobibox status` dasselbe ausführlich.

### CUJ 12: Unterwegs ohne Netz, danach daheim

*   **Given**: Box war Tage unterwegs, ohne bekanntes Netz.
*   **When**: Sie kommt ins Heimnetz oder in den Handy-Hotspot.
*   **Then**: Sie meldet gesammelte unbekannte Figuren und Status an HA, holt
    neue Zuordnungen und (nach den Regeln aus CUJ 9) neue Folgen.

### CUJ 13: Leser fällt aus und kommt wieder

*   **Given**: Die Box läuft.
*   **When**: Der ESP32 startet neu oder die USB-Verbindung ist kurz weg.
*   **Then**: Der Box-Dienst merkt es (fehlender Herzschlag), protokolliert
    es, verbindet sich selbst neu. Eine liegende Figur wird danach wieder
    erkannt, ohne dass die Serie neu startet.

## Technical Plan (Architecture)

### Überblick der Bausteine

```
 Figur/Karte
     │  13,56 MHz
┌────▼─────────────────────┐   USB-Serielle (CDC)     ┌───────────────────────────────┐
│ ESP32-S3 + PN5180        │  Protokoll v1, Zeilen    │ Box-Rechner (Mac / Pi 3A+)    │
│ Firmware „tobibox-reader“├─────────────────────────►│ Box-Dienst „tobiboxd“ (Python)│
│ • Abfrage 14443A / 15693 │◄─────────────────────────┤  reader → core → player (MPD) │
│ • Tonie entsperren       │   (Rückkanal reserviert) │  store · eventlog · net/power │
│ • Entprellen, liegt/weg  │                          │  ha (MQTT) · sync · update    │
└──────────────────────────┘                          └──────┬───────────────┬────────┘
                                                             │ MQTT          │ rsync
                                                     Tailscale (Heimnetz oder Hotspot)
                                                             │               │
                                             ┌───────────────▼──┐   ┌────────▼─────────┐
                                             │ Home Assistant   │   │ QNAP-NAS          │
                                             │ MQTT-Broker,     │   │ Medien (mp3),     │
                                             │ Zuordnungen,     │   │ Update-Pakete     │
                                             │ Dashboard        │   │ (nur lesen)       │
                                             └──────────────────┘   └───────────────────┘
                                                   ▲ Nabu Casa (nur Tobias' Handy)
```

Die Box spricht mit HA und NAS **immer über Tailscale**, egal ob Heimnetz
oder Handy-Hotspot. So gibt es einen einzigen Weg statt zwei, und nichts ist
aus dem Internet erreichbar. Nabu Casa nutzt nur Tobias' Handy für die
HA-Oberfläche.

### Baustein 1 — Firmware `tobibox-reader` (ESP32-S3)

- Neu aufgebaut, `firmware/tonie_test/` dient als Referenz für die
  Lese- und Entsperr-Abläufe.
- Build mit **PlatformIO**, feste Versionen (Plattform, Arduino-Core,
  PN5180-Bibliothek per Commit). USB-Modus: nur **CDC** (keine Tastatur).
- Passwort aus `config.h` (gitignored), wie bisher.
- Aufbau in drei Teile:
  1. **Leser** (Hardware): ein Abfragezyklus liefert genau ein Ergebnis:
     `nichts`, `uid(typ, bytes)`, `gesperrt`, `fehler(code)`. Fehler werden
     **nicht** als „nichts“ gemeldet.
  2. **Entpreller** (reine Logik, ohne Hardware, auf dem Rechner testbar):
     bekommt Ergebnisse mit Zeitstempel, entscheidet `PLACED` / `REMOVED`.
  3. **Protokoll-Ausgabe**: schreibt Zeilen, zählt für den Herzschlag.
- **Zeitkonstanten** (alle an einer Stelle, in `config.h`):
  - Abfragezyklus ≤ 200 ms (Ziel 150 ms; Messung in Test 7 entscheidet).
  - Neue Kennung gilt nach **2 gleichen Lesungen in Folge** (3 falls Test
    zeigt, dass 2 nicht reichen).
  - `REMOVED` nach **1,1 s** ohne gültige Lesung der liegenden Figur.
    Damit: Lücken bis 1,0 s überbrückt, Pause ≤ 1,5 s nach Abheben.
  - Eine andere Kennung, während eine Figur liegt, wird erst nach
    2 gleichen Lesungen als Wechsel gemeldet (`REMOVED` + `PLACED`).
- **Gesperrter Tonie**: eigener stabiler Zustand „gesperrt liegt“; gleiche
  Entprell- und Abhebe-Regeln wie bei einer Kennung.

### Baustein 2 — Protokoll v1 (Vertrag Firmware ↔ Box-Dienst)

Eigenes Dokument `docs/protocol/reader-v1.md` (in der Umsetzung). Grundzüge:

- ASCII-Zeilen, `\n`-terminiert, 115200 Baud (bei CDC ohne Bedeutung),
  Felder `schlüssel=wert`, durch Leerzeichen getrennt. Unbekannte Felder und
  unbekannte Zeilen werden ignoriert und protokolliert.
- Vom Leser:

| Zeile | Bedeutung |
|---|---|
| `HELLO proto=1 fw=<version> build=<git-hash> pn5180=<fw-version>` | nach Start und auf `PING` |
| `PLACED uid=<hex> type=<ntag\|iso15693> tonie=<0\|1> seq=<n>` | Figur mit Kennung liegt (entprellt) |
| `LOCKED seq=<n>` | gesperrter Tonie liegt |
| `REMOVED seq=<n>` | liegende Figur ist weg |
| `HB up=<s> present=<0\|1> polls=<n> hits=<n> rejected=<n> errors=<n> cycle_ms=<n>` | Herzschlag alle 2 s |
| `ERR code=<wort> detail=<text>` | Fehler, z. B. `pn5180_no_response`, `unlock_failed` |

- Zum Leser: `PING` (Antwort `HELLO`); weitere Befehle reserviert (Q1).
- **Kennung (kanonisch):** Hex, Kleinbuchstaben, MSB zuerst, ohne Trenner,
  bei ISO 15693 also 16 Zeichen beginnend mit `e00403` für Tonies. Diese
  Schreibweise entsteht **nur** in der Firmware; der Box-Dienst prüft sie
  (Regex) und speichert sie unverändert.
- `seq` zählt jede Meldung hoch; eine Lücke zeigt verlorene Zeilen.
- Eine Testdatei `docs/protocol/reader-v1-examples.txt` mit gültigen und
  ungültigen Zeilen prüft Firmware-Ausgabe und Parser gleichermaßen.

### Baustein 3 — Box-Dienst `tobiboxd` (Python ≥ 3.11)

Ein Prozess, `asyncio`, ein Paket `tobibox` mit klar getrennten Modulen:

| Modul | Aufgabe | Darf auf Ein-/Ausgabe zugreifen? |
|---|---|---|
| `core` | Zustandsautomat: Ereignisse rein, Befehle raus | **nein** (reine Logik, voll testbar) |
| `library` | Serien und Folgen aus dem Medienordner lesen | Dateisystem (lesen) |
| `store` | Zustandsdateien atomar lesen/schreiben | Dateisystem |
| `reader` | Serielle öffnen, Zeilen parsen, Neuverbinden, Herzschlag überwachen | Serielle |
| `player` | dünne Schicht über MPD (python-mpd2): `play(datei, position)`, `pause()`, `position()`, `volume()` | MPD |
| `sounds` | kurze Rückmeldetöne über eigenes Kommando (Mac `afplay`, Pi `aplay`) | Prozess |
| `ha` | MQTT-Anbindung, HA-Discovery, Zuordnungen empfangen, Status senden | Netz |
| `sync` | rsync vom NAS nach den Regeln, danach MPD-Bibliothek aktualisieren | Prozess, Netz |
| `net`, `power` | Netz-Klasse (Heim / Hotspot / offline), Lader + Akkustand | System bzw. Simulation |
| `eventlog` | einheitliches Ereignisprotokoll, dauerhafter Ringpuffer | Dateisystem |
| `cli` | `tobibox status`, `tobibox sim …`, `tobibox scenario …` | — |

**Der Kern** kennt nur Ereignisse und Befehle:

- Ereignisse: `Placed(uid)`, `Locked`, `Removed`, `ReaderLost`,
  `ReaderBack`, `EpisodeEnded`, `PositionTick(pos)`, `MappingsChanged`,
  `LearnStart(series, bis)`, `LearnCancel`, `AdminCard(aktion)`, `Tick(zeit)`.
- Befehle: `Play(serie, folge, position)`, `Pause`, `Stop`,
  `PlaySound(name)`, `SaveResume(...)`, `ReportUnknown(uid)`,
  `ReportLearned(uid, serie)`, `Log(...)`.
- Die Abläufe (CUJs) werden als **Szenario-Dateien** geschrieben:
  Protokollzeilen und Zeitpunkte rein, erwartete Befehle raus. Sie laufen
  ohne MPD und ohne Leser in Millisekunden, am Mac, im Container und später
  als Teil des Selbsttests am Pi.

### Datenmodell und Dateien

Alle Dateien JSON, mit `schema_version`, atomar geschrieben (temporäre Datei →
fsync → umbenennen), beim Start geprüft; bei Fehler Rückfall auf `.bak`.

| Datei | Inhalt | Wer schreibt | Sync |
|---|---|---|---|
| `mappings.json` | `uid → serie_id`, Revisionsnummer von HA | nur aus HA übernommen | holt von HA |
| `resume.json` | je Serie: aktuelle Folge (Dateiname) + Position + Zähler | Box | nie |
| `unknown.json` | unbekannte Kennungen mit Zeitpunkt, noch nicht an HA gemeldet | Box | an HA, dann leeren |
| `admin_cards.json` | `uid → Aktion` (Status, …) | Konfiguration | Teil des Pakets |
| `eventlog/` | Ringpuffer (z. B. 4 × 256 KB JSON-Zeilen) | Box | Auszug an HA |

- **Serie** = Ordner im Medienordner; Folgen = mp3 darin, sortiert nach
  Dateiname (natürliche Sortierung). Neue Folgen am Ende verlängern die Serie.
- **Serien-ID** — siehe Entscheidung D2.
- **Resume = „nächste ungehörte Folge“** in einem: je Serie ein Zeiger
  (Folge + Position). Folge zu Ende → Zeiger auf nächste Folge, Position 0.
  Letzte Folge zu Ende → Zeiger auf Folge 1. Beim Weiterspielen 3 s
  Rücksprung.
- Resume wird gespeichert bei Pause, Folgenwechsel, Figurwechsel und
  spätestens alle 30 s während der Wiedergabe.
- **Überraschungs-Ordner** ist eine normale Serie mit fester ID
  `ueberraschung`; fehlt sie oder ist leer → Fehlerton, Protokolleintrag.

### Home Assistant

- Verbindung per **MQTT** über Tailscale zum Broker bei HA.
- Box meldet sich per **MQTT-Discovery** an: Sensoren (Zustand, läuft
  gerade, Akku, Lader, Netz, Sync-Stand, Version, letzter Fehler), Knöpfe
  (Sync jetzt, Update, Lernmodus abbrechen), Auswahl (Serie für Lernmodus).
- Box meldet unbekannte und gelernte Kennungen als Ereignis.
- HA ist **einziger Schreiber** der Zuordnungen. Sie liegen in der eigenen
  HA-Integration `tobibox` (D1); diese veröffentlicht die Liste als
  dauerhafte MQTT-Nachricht mit Revisionsnummer, die Boxen übernehmen sie.
- Die HA-Konfiguration (Dashboard, Skripte, Automationen) liegt als Dateien
  im Repo unter `homeassistant/`.

### Baustein 4 — HA-Integration `tobibox` mit eigener Seite

Liegt im Repo unter `homeassistant/custom_components/tobibox/`, wird in HA
als eigene Integration installiert. Sie ist der **einzige Schreiber** für
Zuordnungen und Serien-Metadaten.

- **Speicher:** Zuordnungen im HA-Speicher (`.storage/tobibox`), mit
  Revisionsnummer; Export als Datei für die Sicherung.
- **Medien:** Die Medienfreigabe des QNAP ist in HA als Netzwerkspeicher
  eingebunden (Schreibrecht nur für HA). Aufbau auf dem NAS:
  `tobibox/medien/<ordner>/serie.json` + mp3-Dateien,
  `tobibox/medien/_papierkorb/`, `tobibox/releases/`.
- **`serie.json`:** `schema_version`, `id` (zufällig, unveränderlich),
  `name` (Anzeige), `folgen` (Reihenfolge als Liste von Dateinamen),
  `typ` (`normal` oder `ueberraschung`). Geschrieben atomar.
- **Erkennen von außen:** Beim Öffnen der Seite und alle 10 min prüft die
  Integration die Freigabe. Neuer Ordner → `serie.json` mit neuer ID und
  Ordnername als Anzeigename. Neue Datei → hinten an die Reihenfolge.
  Fehlende Datei → aus der Reihenfolge, Hinweis. Nicht-mp3 → Warnung (Q5).
- **Löschen** verschiebt in `_papierkorb/` (30 Tage), nie endgültig sofort.
  Die Boxen übernehmen `_papierkorb/` nicht.
- **Aktionen** (auch für Automationen): zuordnen, lösen, Lernmodus starten /
  abbrechen, Serie anlegen / umbenennen, Folgen sortieren / löschen,
  Sync anstoßen, Update anstoßen.
- **Eigene Seite** in der HA-Seitenleiste („Tobi Box“), läuft auch über
  Nabu Casa am Handy:
  - Serienliste mit Anzahl Folgen und zugeordneten Figuren
  - Serie öffnen: Folgen per Ziehen sortieren, löschen, umbenennen,
    mp3 vom Handy hochladen
  - „Neue Figuren“: unbekannte Kennungen beider Boxen, mit einem Tipp einer
    Serie zuordnen (Weg A); „Jetzt kommt ein neuer Tonie“ (Weg B)
  - Box-Status: Version, Netz, Akku, Sync-Stand, letzter Fehler
- **Technik der Seite:** ein Web-Baustein (JavaScript-Modul, Lit, ohne
  eigenen Build-Server), Daten über die HA-WebSocket-Schnittstelle mit
  HA-Anmeldung; Hochladen über einen eigenen HA-HTTP-Endpunkt mit Anmeldung.
- **MQTT** (über den vorhandenen Broker):
  `tobibox/mappings` (dauerhaft, ganze Liste + Revision),
  `tobibox/<box>/event` (unbekannt, gelernt, Fehler),
  `tobibox/<box>/cmd` (Lernmodus, Sync, Update), Status per Discovery.

### Netz, Sync, Strom

- **Netz-Klasse** (Pi: NetworkManager-SSID; Mac: Simulation):
  `home` (Heim-SSID **und** NAS über Tailscale erreichbar), `hotspot`
  (Hotspot-SSID), `offline`.
- **Medien-Sync** mit rsync über Tailscale (NAS-Konto nur lesend):
  - `home`: immer erlaubt.
  - `hotspot`: erlaubt, wenn Lader dran oder Akku > 50 %.
  - Dateien landen erst nach vollständiger Übertragung sichtbar im
    Medienordner (`--partial-dir`, `--delay-updates`).
  - Danach MPD-Bibliothek aktualisieren, nicht beim Start.
  - Nie parallel zum Update.
- **Strom** im Prototyp: Simulation (`tobibox sim power --charger on
  --battery 40`). Später PiSugar-Anbindung hinter derselben Schnittstelle.

### Update

- **Paket**: Tarball `tobibox-<version>.tar.gz` mit Code, festgelegten
  Python-Abhängigkeiten (Wheels für Pi/armv7) und `manifest.json`
  (Version, Protokoll-Version, Schema-Versionen, Firmware-Mindestversion).
  Liegt auf dem NAS in `tobibox/releases/`.
- **Ablauf**: HA-Knopf → Box prüft Bedingungen (daheim, Lader, spielt
  nicht, kein Sync) → lädt Paket → entpackt nach `releases/<version>/`
  mit eigener Python-Umgebung → sichert Zustandsdateien → stellt Verweis
  `current` um → startet neu → Zustand `testing`.
- **Selbsttest** (feste Liste): Dienst läuft, Leser meldet `HELLO` mit
  passender Protokoll-Version, Zustandsdateien lesbar, Szenario-Tests grün,
  MPD antwortet, Testton spielt. Dann Zustand `ok`.
- **Wächter**: Steht der Zustand nach 5 min noch auf `testing` oder ist er
  `failed`, stellt ein eigener systemd-Dienst beim nächsten Start `current`
  auf die vorige Version zurück und meldet den Grund an HA.
- Firmware-Updates des ESP32 sind **nicht** Teil des Pakets (Flashen per
  USB am Mac); das Paket nennt nur die Mindestversion.

### Fehlersuche

- **Ereignisprotokoll**: eine JSON-Zeile je Ereignis mit Zeit, Zeitquelle,
  Baustein, Ereignis, Vorgangs-ID (je `PLACED`), Ergebnis. Simulierte
  Ereignisse tragen `sim=true`. Keine Geheimnisse.
- **Status-Admin-Karte**: spielt eine Tonfolge je Prüfpunkt (Leser, Medien,
  Netz, Speicher, HA): kurz-hoch = in Ordnung, tief = Fehler. Optional
  später Sprachansage.
- **`tobibox status`** (SSH): dieselben Prüfpunkte ausführlich, letzte
  Fehler, Versionen, Sync-Stand.

### Mac und Pi

| | Mac (Prototyp) | Pi 3A+ (Box) |
|---|---|---|
| Leser | `/dev/cu.usbmodem…` | `/dev/serial/by-id/…tobibox…` |
| MPD | Homebrew, Ausgabe CoreAudio | Paket aus Pi OS, Ausgabe ALSA (I²S) |
| Töne | `afplay` | `aplay` |
| Netz, Strom | Simulation | NetworkManager, später PiSugar |
| Start | `tobiboxd` im Terminal | systemd-Dienst |
| Pfade | `~/tobibox/…` | `/var/lib/tobibox`, `/opt/tobibox` |

Alles in **einer** Konfigurationsdatei `tobibox.toml` je Gerät; im Code gibt
es keine Abfrage „bin ich am Mac?“.

### Offene Architektur-Entscheidungen (für Tobias)

*   **D1 — Wo liegen die Zuordnungen in Home Assistant?** Entschieden
    (05.11.): **eigene kleine HA-Integration** `tobibox` (Python,
    `custom_components/tobibox/`). Sie speichert die Zuordnungen im
    HA-Speicher (Teil der HA-Sicherung), bietet Aktionen (zuordnen, lösen,
    Lernmodus starten/abbrechen) und veröffentlicht die Liste per MQTT an
    die Boxen. Risiko: HA-Updates; Gegenmittel: wenig HA-API, Tests gegen
    die HA-Version, Liste zusätzlich als Export-Datei.
*   **D2 — Woran erkennt man eine Serie dauerhaft?** Entschieden (05.11.):
    eigene **ID-Datei `serie.json`** in jedem Serien-Ordner (ID, Anzeigename,
    später Bild), angelegt und gepflegt von der HA-Integration. Tobias will
    eine **saubere Dateiverwaltung in HA** (Umfang: siehe Q5). Dafür bindet HA
    die Medienfreigabe des NAS mit Schreibrecht ein; die Boxen lesen nur.
*   **D3 — Broker:** MQTT läuft in HA. Tailscale ist noch nicht eingerichtet
    (HA-Add-on, QNAP-App, Boxen) → Einrichtungsschritte für Tobias in Stufe 3.

## Alternatives Considered

Quellen: `concepts_brief.md` (Abgewogene Alternativen, Entscheidungen Runde
1 und 2), `pivot_ohne_v3.md`, Entscheidungen D1–D4 in diesem Dokument.

### Phoniebox V3 als Basis mit eigenen Plugins

Plan bis Rev. 3.7. **Abgelehnt von Tobias:** Nach den übrigen Entscheidungen
übernimmt eigener Code fast alles (Leser, Resume, Serien, Zuordnung,
Oberfläche, Sync, Update); V3 bliebe nur als MPD-Steuerung mit einer
instabilen Plugin-Schnittstelle, einem eingefrorenen Versionsstand, der in
wenigen Jahren nicht mehr frisch installierbar ist, und am Mac nur in Docker
mit Brücke testbar. Bestätigung nach dem ersten Pi-Lauf.

### Leser als USB-Tastatur (HID)

**Abgelehnt von Tobias:** Eine Tastatur kann kein Abheben, keine Fehler und
keine Version melden; der V3-Lese-Thread stirbt bei Gerätewegfall; am Mac
tippt sie in das vordere Fenster.

### Mac-Prototyp mit Docker und Serial-zu-TCP-Brücke

**Abgelehnt von Tobias** (mit dem Wegfall von V3): Docker auf dem Mac kommt
nicht an USB; die Brücke wäre ein dritter Codepfad, den es am Pi nicht gibt.
Natives MPD am Mac liest den Leser direkt.

### ESPuino (ESP32 als kompletter Player, ohne Pi)

**Abgelehnt von Tobias:** Abspielen ginge, aber Medien-Sync über WLAN auf
SD, Update mit Rückfall, HA-Abgleich und Serienlogik wären auf dem ESP32
mühsam und schlecht testbar.

### ESPHome mit PN5180

**Abgelehnt von der Projektleitung:** Tonie-Entsperrung fehlt vermutlich,
die eigene Firmware ist erprobt.

### V3-Weboberfläche oder eigene Handy-Seite auf der Box

**Abgelehnt von Tobias:** HA ist die einzige Oberfläche, auch von unterwegs
über Nabu Casa. Die Box wird nicht ins Netz geöffnet. Notweg ohne HA:
`tobibox status` per SSH und Status-Admin-Karte.

### Zuordnungen auf mehreren Seiten schreiben (Box und HA, Zwei-Wege-Sync)

**Abgelehnt von Tobias:** Konflikte bei zwei Boxen und Offline-Betrieb.
HA ist einziger Schreiber, Resume bleibt pro Box.

### Zuordnungen als dauerhafte MQTT-Nachricht oder in einem Dienst auf dem NAS (D1)

**Abgelehnt von Tobias:** Die MQTT-Variante braucht fummelige HA-Skripte und
kann die Liste bei einem Fehler überschreiben; ein NAS-Dienst wäre ein
weiterer Dienst. Gewählt: eigene HA-Integration.

### Serie über den Ordnernamen erkennen (D2)

**Abgelehnt von Tobias:** Umbenennen würde Zuordnungen und Resume brechen;
gewünscht ist eine saubere Dateiverwaltung in HA. Gewählt: `serie.json` mit
fester ID.

### Medienverwaltung mit HA-Bordmitteln oder fertigem Datei-Manager (D4)

**Abgelehnt von Tobias:** Bordmittel verteilen die Bedienung auf zwei Orte
und machen Sortieren umständlich; ein fremder Datei-Manager kennt keine
Serien. Gewählt: eigene Seite in HA.

### NAS von außen über myQNAPcloud oder QVPN/WireGuard

**Abgelehnt von Tobias:** Ein aus dem Internet erreichbares QNAP ist ein
bekanntes Angriffsziel (QNAP-Hinweis QSA-22-24 nach DeadBolt); QVPN braucht
einen offenen Port am Router. Gewählt: Tailscale mit ACL.

### Eigener WLAN-Hotspot der Box

**Abgelehnt von Tobias:** Dauerfunk kostet Akku; stattdessen verbindet sich
die Box mit seinem Handy-Hotspot wie mit einem bekannten Netz.

### Update per `git pull`

**Abgelehnt von Tobias:** Kein Selbsttest, kein automatischer Rückfall.
Gewählt: Paket in eigenem Verzeichnis, Verweis `current`, Wächter.

### Automatische Erkennung der Figur

**Nicht möglich** (siehe `research_tonie_erkennung.md`): Der Chip trägt nur
eine Seriennummer; die Zuordnung erfolgt einmal pro Exemplar.

## Detailed Implementation

Grundregeln für die Umsetzung:

- Jedes Arbeitspaket (AP) setzt ein Agent um, mit dem billigsten passenden
  Modell (in Klammern). Danach prüft ein **frischer Agent** (Goldfisch, Sonnet)
  den Code gegen dieses Dokument, bevor das AP als fertig gilt.
- Jedes AP liefert Tests, die im Container ohne Hardware laufen
  (Firmware-Logik: PlatformIO `native`; Box-Dienst: pytest; MPD-Tests mit
  echtem MPD im Container).
- Kein AP ändert die Verträge aus Stufe 0 eigenmächtig; Änderungswünsche
  gehen an die Projektleitung.
- Kein Geheimnis im Repo: `config.h`, `tobibox.toml` mit Zugangsdaten und
  Tailscale-Schlüssel sind gitignored, im Repo liegen nur `*.example.*`.

### Stufe 0 — Verträge (Projektleitung schreibt, Goldfisch prüft)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `docs/protocol/reader-v1.md` | neu | Protokoll v1 vollständig: Zeilen, Felder, Kennungsformat, Zeitkonstanten, Fehlercodes, Verhalten bei unbekannten Zeilen. Einziger Vertrag zwischen Firmware und Box-Dienst. |
| `docs/protocol/reader-v1-examples.txt` | neu | Gültige und ungültige Beispielzeilen mit erwarteter Auslegung; Testgrundlage für beide Seiten. |
| `docs/data-model.md` | neu | Schemas: `serie.json`, `mappings.json`, `resume.json`, `unknown.json`, `admin_cards.json`, `manifest.json`, Ereignisprotokoll-Zeile, MQTT-Themen und -Nachrichten. Regeln: atomar schreiben, `.bak`, `schema_version`, Migration. |
| `docs/timing.md` | neu | Zeitbudget je Schritt (Lesen, Entprellen, Übertragen, MPD-Start) für 1,0 s / 1,5 s / 1,0 s; wie gemessen wird (Ereignisprotokoll). |
| `box/tests/scenarios/README.md` | neu | Format der Szenario-Dateien (Zeit, Eingabezeile oder Ereignis, erwartete Befehle). |

Abnahme: Goldfisch-Review der fünf Dateien ohne Blocker, Freigabe durch Tobias.

### Stufe 1 — Leser und Abspielen (CUJ 1, 2, 5, 6, 8, 13)

**AP 1.1 Firmware `tobibox-reader`** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `firmware/tobibox-reader/platformio.ini` | neu | Umgebungen `esp32s3` (SuperMini, USB-CDC) und `native` (Tests am Rechner); Plattform, Core und PN5180-Bibliothek per fester Version/Commit. |
| `firmware/tobibox-reader/include/config.example.h` | neu | Pins (aus `tonie_test/config.h`), Zeitkonstanten, Passwort-Platzhalter. |
| `firmware/tobibox-reader/src/main.cpp` | neu | Zusammenbau: Leser → Entpreller → Protokoll; Herzschlag. |
| `firmware/tobibox-reader/src/reader.h/.cpp` | neu | Ein Abfragezyklus 14443A/15693/Entsperren nach Vorbild `tonie_test`; liefert `nichts`/`uid`/`gesperrt`/`fehler`. |
| `firmware/tobibox-reader/src/debounce.h/.cpp` | neu | Reiner Zustandsautomat ohne Hardware-Aufrufe (Zeit wird übergeben). |
| `firmware/tobibox-reader/src/protocol.h/.cpp` | neu | Formatiert Zeilen nach `reader-v1.md`, zählt `seq` und Zähler. |
| `firmware/tobibox-reader/test/test_debounce/` | neu | Native Tests: 2-gleich-Regel, 1,0-s-Lücke, 1,1-s-Abheben, Figurwechsel, verfälschte Kennung am Rand, gesperrter Tonie. |
| `firmware/tobibox-reader/test/test_protocol/` | neu | Native Tests gegen `reader-v1-examples.txt`. |
| `firmware/tobibox-reader/README.md` | neu | Bauen, Flashen am Mac, Passwort eintragen, serielle Ausgabe ansehen. |
| `firmware/tonie_test/` | bleibt | Referenz, unverändert. |

**AP 1.2 Box-Dienst: Kern, Protokoll, Speicher** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/pyproject.toml` | neu | Paket `tobibox`, Python ≥ 3.11, feste Abhängigkeiten (pyserial, python-mpd2, paho-mqtt, tomli bei Bedarf), Einstiegspunkte `tobiboxd`, `tobibox`. |
| `box/src/tobibox/events.py` | neu | Ereignis- und Befehls-Typen des Kerns. |
| `box/src/tobibox/core.py` | neu | Zustandsautomat (reine Logik): Auflegen, Abheben, Wechsel, gesperrt, unbekannt, Überraschung. |
| `box/src/tobibox/protocol.py` | neu | Zeilen-Parser nach `reader-v1.md`, prüft Kennungsformat. |
| `box/src/tobibox/reader.py` | neu | Serielle öffnen, Zeilen lesen, `HELLO`-Prüfung, Herzschlag-Wächter (5 s), selbst neu verbinden. |
| `box/src/tobibox/store.py` | neu | Atomares Lesen/Schreiben, `.bak`, `schema_version`. |
| `box/src/tobibox/library.py` | neu | Serien aus `serie.json` lesen, Folgen-Reihenfolge, Überraschungs-Serie. |
| `box/src/tobibox/config.py` | neu | `tobibox.toml` laden und prüfen. |
| `box/src/tobibox/eventlog.py` | neu | JSON-Zeilen, Vorgangs-ID, Ringpuffer auf Platte. |
| `box/src/tobibox/scenario.py` | neu | Spielt Szenario-Dateien gegen den Kern ab (für Tests und `tobibox scenario`). |
| `box/tools/fake_reader.py` | neu | Gibt Protokollzeilen auf ein Pseudo-Terminal aus; Vorführen und Testen ohne Hardware. |
| `box/tests/unit/` | neu | Tests je Modul. |
| `box/tests/scenarios/cuj01…cuj13*.yaml` | neu | Abläufe dieser Stufe als Szenarien. |
| `box/tests/integration/test_reader_pty.py` | neu | Leser über Pseudo-Terminal: Trennung, Müllzeilen, Neustart des ESP32. |

**AP 1.3 Player und Töne** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/player.py` | neu | Dünne MPD-Schicht: `play(datei, position)`, `pause()`, `position()`, `volume()`, Ereignis „Folge zu Ende“. |
| `box/src/tobibox/sounds.py` | neu | Kurze Töne über konfigurierbares Kommando. |
| `box/src/tobibox/daemon.py` | neu | Verbindet reader → core → player, Zeitgeber, sauberes Beenden. |
| `box/sounds/` | neu | Platzhalter-Töne (später eigene von Tobias). |
| `box/tests/integration/test_player_mpd.py` | neu | Gegen echtes MPD im Container: Start, Pause, Position, Folgenende. |

**AP 1.4 Mac-Einrichtung und Doku** (Haiku)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/config/tobibox.mac.example.toml` | neu | Mac-Konfiguration (Gerätepfad, MPD, Pfade, Simulation). |
| `docs/betrieb/mac-prototyp.md` | neu | Schritt für Schritt: Homebrew, MPD, Python-Umgebung, Firmware flashen, Testserie anlegen, `tobiboxd` starten, Vorführung der CUJs. |
| `box/medien-beispiel/` | neu | Kleine Beispielserie mit `serie.json` und kurzen Test-mp3 (selbst erzeugte Töne, keine fremden Inhalte). |

**AP 1.5 Automatische Prüfung** (Haiku)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `.github/workflows/ci.yml` | neu | Bei jedem Push: pytest (mit MPD), PlatformIO `native`-Tests, Firmware-Build für `esp32s3`. |
| `.gitignore` | änd. | `config.h`, `tobibox.toml`, `.venv/`, `.pio/`, Laufzeitdaten. |

**Abnahme Stufe 1:** Alle Szenarien und Tests grün; Tobias führt am Mac mit
echtem Leser CUJ 1, 2, 5, 6, 8, 13 vor; das Ereignisprotokoll zeigt die
Zeitgrenzen eingehalten.

### Stufe 2 — Resume, Serien, Zuordnung lokal (CUJ 3, 4, 7a/7b ohne HA, 11)

**AP 2.1 Resume und Serienzeiger** (Sonnet): `core.py`, `store.py` (Resume-
Datei), `daemon.py` (Speichern alle 30 s und bei Pause), Szenarien CUJ 3, 4,
Stromausfall-Test (Prozess hart beenden während des Schreibens).

**AP 2.2 Unbekannte Figuren und Lernmodus** (Sonnet): `core.py`
(`unknown.json`, Lernmodus 2 min), `box/src/tobibox/cli.py` mit
`tobibox sim learn …` als Ersatz für HA bis Stufe 3, Szenarien CUJ 7a/7b.

**AP 2.3 Status und Admin-Karte** (Sonnet): `box/src/tobibox/selftest.py`
(Prüfpunkte), `cli.py` (`tobibox status`), `box/admin_cards.example.json`,
Töne je Prüfpunkt, Szenario CUJ 11.

**Abnahme Stufe 2:** wie Stufe 1, zusätzlich Vorführung von Resume über
Neustart und Lernmodus per `tobibox sim`.

### Pi-Probelauf (sobald der Pi 3A+ da ist)

**AP P.1 Pi-Installation** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `deploy/pi/install.sh` | neu | Auf frischem Pi OS Lite: Pakete (MPD), Benutzer, Verzeichnisse, Python-Umgebung, Dienste. |
| `deploy/pi/tobiboxd.service` | neu | systemd-Dienst, Neustart bei Absturz. |
| `deploy/pi/99-tobibox-reader.rules` | neu | Fester Gerätename für den ESP32 (eigene USB-Kennung aus der Firmware). |
| `deploy/pi/mpd.conf` | neu | MPD für die Box. |
| `box/config/tobibox.pi.example.toml` | neu | Pi-Konfiguration. |
| `docs/betrieb/pi-probelauf.md` | neu | Ablauf und Prüfliste: dieselben Szenarien und Vorführungen wie am Mac, Startzeit, Speicherbedarf, Temperatur. |

**Abnahme:** Prüfliste vollständig grün, Unterschiede zum Mac dokumentiert;
damit ist der Wegfall von V3 endgültig bestätigt.

### Go/No-Go mit Tobias vor Stufe 3

### Stufe 3 — HA, Medienverwaltung, Sync, Netz, Update (CUJ 7a/7b mit HA, 9, 10, 12)

**AP 3.1 HA-Integration Backend** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `homeassistant/custom_components/tobibox/manifest.json` | neu | Integration, Abhängigkeit MQTT, Version. |
| `…/__init__.py`, `config_flow.py` | neu | Einrichtung: Medienpfad, Boxen. |
| `…/store.py` | neu | Zuordnungen mit Revision im HA-Speicher, Export. |
| `…/media.py` | neu | `serie.json` lesen/schreiben, Erkennen neuer Ordner/Dateien, Papierkorb, Hochladen. |
| `…/mqtt.py` | neu | `tobibox/mappings` veröffentlichen, Box-Ereignisse empfangen, Befehle senden. |
| `…/websocket_api.py`, `http.py` | neu | Daten für die Seite, Hochladen mit Anmeldung. |
| `…/services.yaml`, `translations/de.json` | neu | Aktionen und Texte. |
| `homeassistant/tests/` | neu | Tests mit `pytest-homeassistant-custom-component`. |

**AP 3.2 HA-Seite** (Sonnet): `homeassistant/custom_components/tobibox/frontend/tobibox-panel.js`
— Serienliste, Folgen ziehen, Hochladen, Umbenennen, Neue Figuren, Lernmodus,
Box-Status; bedienbar am Handy.

**AP 3.3 Box-Dienst: HA, Netz, Strom** (Sonnet): `box/src/tobibox/ha.py`
(MQTT, Discovery, Zuordnungen übernehmen, Ereignisse), `net.py`, `power.py`
(Simulation + Schnittstelle), Szenarien CUJ 12.

**AP 3.4 Medien-Sync** (Sonnet): `box/src/tobibox/sync.py` (rsync-Regeln
Heim/Hotspot/Akku, sichtbar erst nach Abschluss, MPD neu einlesen, Sperre
gegen Update), Tests mit lokalem rsync-Ziel, Szenario CUJ 9.

**AP 3.5 Update mit Wächter** (Sonnet): `box/src/tobibox/update.py`,
`deploy/build_release.sh` (Paket + `manifest.json`), `deploy/pi/tobibox-guard.service`,
Tests für Umschalten, Selbsttest-Fehler, Rückfall; Szenario CUJ 10.

**AP 3.6 Einrichtung Tailscale und NAS** (Haiku): `docs/betrieb/tailscale-nas.md`
(QNAP-App, HA-Add-on, Box-Schlüssel, ACL nur Medienfreigabe, Nur-Lese-Konto,
Schlüssel sperren), optional ein Assistenten-Skript für die Schritte, die nur
Tobias machen kann.

**AP 3.7 Betriebshandbuch** (Haiku): `docs/betrieb/handbuch.md` —
Wiederherstellung von Null, SD-Image, „was ist wo konfiguriert“, Fehlerbilder.

**Abnahme Stufe 3:** Alle CUJs als Szenarien grün; Vorführung mit HA am Handy
(über Nabu Casa) und Mac-Box; Plan auf Rev. 3.9 nachgezogen.

### Dokumente, die am Ende nachgezogen werden

| Datei | Änderung |
|---|---|
| `docs/plan/stueckliste-und-psp.md`, `docs/plan/psp-baum.html` | Rev. 3.9: PSP-Punkte, die durch dieses Design ersetzt sind |
| `docs/designs/box-software.md` | angenommene Fassung dieses Dokuments |
| `CLAUDE.md` | Verweis auf Verträge und Arbeitsweise je Stufe |
