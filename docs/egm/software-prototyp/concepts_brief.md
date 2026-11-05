# Software-Prototyp Tobi Box

* **Autor:** Tobias (Projektleitung: Claude als „Elefant“)
* **Datum:** 2026-11-05
* **Stand:** Entwurf nach Goldfisch-Brainstorm, offene Fragen am Ende
* **Grundlage:** `hypothese.md`, Rohbefunde in `goldfish_brainstorm_raw.md`

## Überblick

Die komplette Software der Tobi Box entsteht, bevor die Box gebaut ist. Sie
läuft zuerst am Mac und danach auf dem Raspberry Pi 3A+ der Box. Ziel: An der
fertigen Box soll nicht mehr programmiert und gesucht werden müssen.

Bausteine:

- Firmware auf ESP32-S3 + PN5180: liest Karten und Tonies, entsperrt Tonies,
  meldet Ereignisse über ein festes Textprotokoll an die USB-Serielle.
- Phoniebox V3 (fest auf v3.6.0) mit einem eigenen Leser-Modul und eigenen
  Plugins (Resume, Figuren-Zuordnung, Überraschung).
- Home Assistant als einzige Bedienoberfläche für die Eltern, von unterwegs
  über Nabu Casa.
- Medien-Sync vom NAS, WLAN-Verhalten, manuelles Software-Update mit
  Selbsttest und Rückfall.

## Analyse (Ergebnis der sechs Goldfische)

Die Goldfische haben 66 Befunde geliefert, 14 davon als Blocker. Viele
überschneiden sich. Sie lassen sich auf neun Themen verdichten.

### 1. „Verhält sich genau wie die Box“ ist am Mac allein nicht beweisbar

Drei von sechs Goldfischen werten das als Blocker. Am Mac unterscheiden sich:
Docker statt nativer Installation, andere Prozessor-Architektur (Mac arm64,
Pi OS 32-bit armv7), Audio über PulseAudio statt I²S-Verstärker, Brücke statt
direkter Serieller, 512 MB RAM am Pi, Boot-Reihenfolge, echtes WLAN.
„Unverändert“ gilt deshalb nur für **unseren Code, unsere Daten und unsere
Konfiguration**, nicht für die Umgebung.

**Folge:** Am Mac wird die **Logik** vollständig bewiesen (alle Abläufe als
automatische Tests plus Vorführung mit echtem Leser). Die **Umgebung** wird
erst auf einem echten Pi bewiesen. Ein Pi 3A+ sollte deshalb früh da sein
(er steht ohnehin in Charge 1), nicht erst mit der fertigen Box.

### 2. Leser: eine Stelle entscheidet „liegt“ / „weg“

Zwei Goldfische empfehlen, zuerst den Tastatur-Weg (HID) zu nehmen, weil er
ohne Code auskommt. Dagegen spricht:
- Am Mac tippt eine Tastatur in das Fenster, das gerade vorne ist; Docker
  kommt nicht an das Gerät.
- V3 beendet den Lese-Teil, wenn das Gerät kurz fehlt.
- Eine Tastatur kann keine Fehler, Versionen oder „gesperrter Tonie“ melden.

Deshalb bleibt es beim **seriellen Protokoll** (von Tobias bestätigt). Daraus
folgen drei Pflichten:
- **Protokoll als Vertrag:** eigenes kurzes Dokument, maschinenlesbare
  Zeilen, Versionszeile beim Start, Herzschlag, Fehlerzeilen, Toleranz für
  unbekannte Zeilen, Rückkanal reserviert. Eine gemeinsame Testdatei mit
  Beispielzeilen prüft Firmware-Simulator, Brücke und Leser-Modul.
- **Ein Zustandsautomat an einer Stelle:** Die Firmware entprellt und
  entscheidet „aufgelegt“ / „abgehoben“. Das Leser-Modul ruft in V3 nur
  „spielen“ bzw. „Pause“ auf; die eigene 1-s-Abhebe-Erkennung von V3 wird
  abgeschaltet. Sonst verteilen sich Zeitkonstanten auf drei Schichten.
- **Ein Leser-Modul, zwei Transporte:** derselbe Zeilen-Code liest am Mac
  über TCP von der Brücke und am Pi direkt von der Seriellen. Umschalten per
  Konfiguration. Gerät verschwindet → Modul verbindet sich selbst neu und
  meldet das.

### 3. Zeitgrenzen für Ablauf 8 fehlen

„Kein Stottern“ ist nicht testbar ohne Zahlen. Benötigt werden: maximale Zeit
vom Abheben bis Pause, maximale Lese-Lücke, die überbrückt wird, Zeit vom
Auflegen bis Ton. Dazu Tests mit eingestreuten Aussetzern (z. B. 0,3 / 0,8 /
1,5 s). Nebenbefund am vorhandenen Sketch: Die Kennung kommt real nur alle
600–700 ms; ein einziger Aussetzer kann heute die V3-Pause auslösen.

**Gesperrte Tonies** sind untereinander nicht unterscheidbar. „Gesperrt liegt
auf“ muss ein stabiler Zustand sein, damit das Überraschungs-Hörspiel bei
einem Aussetzer nicht neu startet.

### 4. Verteilter Zustand: wer hat die Wahrheit?

Zuordnungen, Resume, Hörfortschritt und Status liegen sonst auf Box 1, Box 2
und Home Assistant, mit Schreiben von mehreren Seiten und offline. Das ist
eine selbst gebaute Synchronisation mit Konflikten. Vorschlag (passt zu
„HA ist die einzige Oberfläche“):

| Daten | Wahrheit liegt bei | Box | Sync |
|---|---|---|---|
| Zuordnung Kennung → Serie | **Home Assistant** (einziger Schreiber) | Kopie, nur lesend | Box holt, sobald erreichbar |
| Unbekannte Kennungen (Weg A) | Box meldet | merkt sich offline | an HA, wenn erreichbar |
| Lernmodus (Weg B) | HA startet ihn auf einer Box | Box meldet „Kennung X aufgelegt“ | HA schreibt die Zuordnung |
| Resume-Position, gehörte Folgen | **jede Box für sich** | lokal, atomar | nie synchronisiert, nur angezeigt |
| Medien (mp3) | **NAS** | Kopie | Box holt, nur Heimnetz |
| Status, Protokoll | Box | lokal gepuffert | an HA, wenn erreichbar |

Damit gibt es keine Konflikte: Nur HA ändert Zuordnungen. Fällt HA aus,
spielt die Box weiter, neue Figuren laufen als Überraschung. Weg A und Weg B
gehen dann nicht, das wird bewusst hingenommen.

### 5. Eigenes Datenmodell und stabile Kennungen

V3 kennt nur „Karte → Ordner“. Wir brauchen: Kennung, Figur, Serie, Folge,
Wiedergabestand. Pflicht:
- Kennung in **einer** festen Schreibweise, z. B. Typ + Hex-UID, MSB zuerst,
  klein geschrieben, an genau einer Stelle erzeugt. Ändert sich das Format
  später, sind alle Figuren „unbekannt“.
- Serien bekommen **stabile IDs**, die Abbildung ID → Ordner steht in einer
  Datei. Umbenennen auf dem NAS bricht dann keine Zuordnung.
- Jede gespeicherte Datei hat eine `schema_version`, wird atomar geschrieben
  (temporär, fsync, umbenennen) und beim Start geprüft (Rückfall auf `.bak`).
- Regeln festlegen: Serie durchgehört → ?, Überraschungs-Ordner leer oder
  fehlt → Fehlerton, kein Absturz.

### 6. Abhängigkeit von Phoniebox V3

V3 hat keine stabile Plugin-Schnittstelle, und der Entwicklungszweig baut den
Player gerade um. Pflicht:
- **Kern ohne V3:** Resume, Zuordnung, Serienlogik als eigenes Python-Paket
  mit eigenen Tests. Ein dünner **V3-Adapter** übersetzt; die genutzten
  V3-Berührungspunkte stehen als Liste im Design.
- V3 auf **v3.6.0, Commit 4fa84fd** gepinnt. Anheben nur mit Vertragstests.
- Abläufe 1–8 als **ausführbare Szenarien**: Protokollzeilen rein, erwarteter
  Player-Zustand raus. Sie laufen am Mac und später als Selbsttest am Pi.

### 7. Update mit Selbsttest und Rückfall konkret machen

Der Contrarian hält das für überdimensioniert, Tobias will es ausdrücklich.
Die kleinste tragfähige Form:
- Ein Update ist ein **versioniertes Paket** (unser Code, Konfiguration,
  Python-Umgebung, Versionsdatei mit V3-Commit, Protokoll- und
  Schema-Version). Betriebssystem und Kernel werden **nicht** per Update
  getauscht, sondern nur über ein neues SD-Image.
- Installation nach `releases/<version>/`, Umschalten per Verweis `current`.
  Zustandsdatei: ausstehend → im Test → ok / fehlgeschlagen. Ein Wächter
  schaltet beim nächsten Start zurück, wenn „im Test“ nicht zu „ok“ wurde.
- Bedingungen prüft die Box selbst: von Tobias in HA angestoßen, Heimnetz
  (SSID **und** NAS erreichbar), Lader dran, Akku über Mindeststand, keine
  Wiedergabe, kein Medien-Sync parallel.
- Selbsttest = feste kurze Liste: Dienste laufen, Leser meldet Version,
  Protokoll passt, Szenario-Tests grün, Testton spielt.
- Ein Update-Protokoll hält fest, was vorher und nachher lief und warum
  zurückgeschaltet wurde. Boxen nacheinander aktualisieren, nie beide zugleich.

### 8. Fehlersuche ohne Laptop

„Spielt nicht“ muss eingrenzbar sein, auch im Auto. Pflicht ab Stufe 1:
- **Einheitliches Ereignisprotokoll** für alle Schichten: Zeit (mit Quelle),
  Schicht, Ereignis, Vorgangs-ID pro Auflegen. Die Kette gelesen → entprellt
  → zugeordnet → Aktion → spielt ist nachvollziehbar.
- **Herzschlag** jeder Schicht mit Version, Laufzeit, letztem Fehler; die
  Firmware zählt Abfragen, Treffer, Verworfenes und Lesefehler getrennt von
  „nichts da“.
- **Kleiner dauerhafter Protokoll-Puffer**, der einen Stromausfall übersteht
  (nur Zustandswechsel und Fehler, gedrosselt). Logs auf tmpfs allein
  reichen nicht.
- **Status-Admin-Karte:** sagt ohne Handy an, ob Leser, Netz und Medien in
  Ordnung sind. Fehlerklassen mit unterscheidbaren Tönen.
- Simulierte Ereignisse sind im Protokoll als „SIM“ markiert. Keine
  Geheimnisse im Protokoll.

### 9. Netz, Hotspot, NAS, Sicherheit

- **Heimnetz** = SSID **und** NAS erreichbar. Nur dort: Medien-Sync, Update.
- **Handy-Hotspot** = Netz mit begrenztem Datenvolumen. Nur kleiner Abgleich
  mit HA (Zuordnungen, Status), keine Medien, keine Updates. Verbindungsversuche
  mit Pausen, damit Box und Handy nicht leer funken.
- **Medien-Sync** mit rsync (bewährt, kein Eigenbau): Teil-Dateien erst nach
  Abschluss sichtbar, Musikbibliothek erst nach dem Sync neu einlesen, nicht
  beim Start. NAS-Konto nur lesend.
- **Sicherheit:** Brücke am Mac nur an localhost. V3-Steuerung und V3-Weboberfläche
  auf der Box nur lokal. Nach außen spricht die Box nur über den
  vereinbarten Kanal mit HA. Tonie-Passwort bleibt in der Firmware-Konfiguration
  und wird weder protokolliert noch synchronisiert noch gesichert.
- **Mac-Schalter** wirken auf der Ebene „NAS / HA erreichbar, langsam,
  Zeitüberschreitung“ und „Lader dran“, nicht nur „WLAN an/aus“. Sie hängen
  an denselben Schnittstellen, die am Pi die echte Hardware nutzt.

## Ziele und Nicht-Ziele

**Ziele (im Prototyp):**
- Firmware mit Protokoll, Entprellung, Fehler- und Statusmeldungen
- Leser-Modul (TCP am Mac, seriell am Pi) und Brücke am Mac
- Abläufe 1–8 inkl. Resume, Serien, Überraschung, Zuordnung Weg A und B
- Home-Assistant-Anbindung: Zuordnen, Lernmodus, Status, Update anstoßen
- Medien-Sync NAS → Box, WLAN-Regeln Heimnetz / Hotspot / offline
- Update mit Paket, Selbsttest, Wächter, Rückfall
- Ereignisprotokoll, Herzschlag, Status-Admin-Karte
- Automatische Szenario-Tests für alle Abläufe

**Nicht-Ziele (vorerst):**
- LED-Ring, PiSugar-Anbindung, Tasten/Encoder, Kopfhörer, Leise-Zeiten
  (Hardware fehlt; nur ihre Schnittstellen werden vorgesehen)
- Eigener Hotspot der Box
- Zugriff auf die Box aus dem Internet
- Betriebssystem-Updates über die Update-Funktion
- Automatische Erkennung, welche Figur ein Tonie ist

## Abgewogene Alternativen

- **USB-Tastatur (HID) statt seriellem Protokoll:** verworfen von Tobias.
  Grund: Am Mac nicht nutzbar (tippt ins vordere Fenster, Docker hat keinen
  USB-Zugriff), V3-Lesethread stirbt bei Gerätewegfall, keine Fehler- und
  Statusmeldungen möglich.
- **ESPuino (ESP32 als kompletter Player ohne Pi):** vorläufig verworfen von
  der Projektleitung, Bestätigung durch Tobias offen. Grund: Hardware-Plan
  mit Pi, PiSugar und I²S steht; ESPuino hat laut Goldfisch keine Serien mit
  „nächste ungehörte Folge“, keinen NAS-Sync und keine Tonie-Entsperrung
  (unverifiziert). Seine Muster (Entprellung, Resume-Format) werden als
  Vorlage gelesen.
- **ESPHome mit PN5180:** verworfen. Tonie-Entsperrung fehlt vermutlich,
  die eigene Firmware ist erprobt.
- **V3-Weboberfläche bzw. eigene Handy-Seite statt Home Assistant:**
  verworfen von Tobias. HA ist die einzige Oberfläche; die V3-Weboberfläche
  bleibt nur als lokaler Notweg für Fehlersuche.
- **Zuordnungen als Datei auf dem NAS (einseitiger Fluss):** abgewogen. HA
  als einziger Schreiber erfüllt dasselbe Ziel (keine Konflikte) und passt
  zur gewünschten Oberfläche; HA exportiert die Zuordnungen zusätzlich als
  Sicherung.
- **Update per `git pull`:** verworfen von Tobias zugunsten Selbsttest und
  Rückfall; die kleine Paket-plus-Verweis-Lösung oben hält den Aufwand klein.
- **Phoniebox am Mac nativ statt in Docker / Linux-VM mit USB-Durchreichung:**
  offen, wird im Design entschieden. Kriterium: möglichst nah am Pi, wenig
  Sonderpfad.

## Abweichungen vom Plan Rev. 3.7 (für Rev. 3.8)

| Thema | Plan 3.7 | Neu |
|---|---|---|
| Leser-Anbindung | USB-Tastatur, kein eigenes Plugin | serielles Protokoll, eigenes Leser-Modul |
| Abheben | Wiederholung 500 ms + Abhebe-Code | Firmware entscheidet, meldet „abgehoben“ direkt |
| Oberfläche | V3-Web-UI + Handy-Seite der Box, nur lokal (6.6) | nur Home Assistant, über Nabu Casa auch unterwegs |
| Hotspot | V3-Auto-Hotspot aus, per Admin-Karte an (5.6.7) | kein eigener Hotspot; Handy-Hotspot als bekanntes Netz |
| Zuordnungs-Abgleich (6.3) | zwischen Box A und B | HA ist einziger Schreiber, Boxen holen |
| Updates (9.4.3) | V3-Updates gegen Plugins testen | manuelles Update-Paket mit Selbsttest und Rückfall |
| Logs (5.1.5) | nur tmpfs | tmpfs + kleiner dauerhafter Protokoll-Puffer |

## Entscheidungen und Stufen für den Design-Entwurf

**Stufe 0 — Verträge (vor jedem Code):** Protokoll-Dokument,
Datenmodell mit Kennungs-Schreibweise und Schemas, Zeitgrenzen für Ablauf 8,
Liste der V3-Berührungspunkte, Ereignisprotokoll-Format.

**Stufe 1 — Leser und Abspielen:** Firmware (aus `tonie_test` weiterentwickelt,
PlatformIO mit festen Versionen), Brücke, Leser-Modul, Kern + V3-Adapter,
Abläufe 1, 2, 5, 6, 8 als Tests und mit echtem Leser vorführbar.
**Danach Pi-Probelauf**, sobald ein Pi da ist.

**Stufe 2 — Resume, Serien, Zuordnung:** Abläufe 3, 4, 7, Lernmodus.

**Stufe 3 — HA, Sync, Netz, Update.** Vorher Go/No-Go mit Tobias.

## Entscheidungen von Tobias (05.11.2026, Runde 1)

- Mac beweist die Logik, ein echter Pi die Umgebung. Maßstab: Es
  funktioniert genau so, wie Tobias es sich vorstellt.
- HA ist einziger Schreiber der Zuordnungen; Resume und Fortschritt pro Box.
- Verträge (Protokoll, Kennung, Zeitgrenzen) vor jedem Code.
- Pi 3A+: noch nicht bestellt → Bestellung empfohlen.
- Zeitgrenzen Ablauf 8 wie vorgeschlagen: Pause ≤ 1,5 s nach Abheben,
  Lücken bis 1 s überbrückt, Ton ≤ 1 s nach Auflegen.
- Serie durchgehört → wieder bei Folge 1.
- Handy-Hotspot: **voller Abgleich**, auch neue Folgen (ändert Thema 9:
  Medien-Sync nicht mehr nur im Heimnetz; Weg zum NAS von unterwegs und
  Datenvolumen offen).
- Speicher: 64 GB reichen.
- ESPuino verworfen: Der ESP32 könnte mp3 abspielen, aber Medien-Sync über
  WLAN auf SD, Update mit Rückfall, HA-Abgleich und die Serienlogik wären
  dort deutlich mühsamer und schlechter testbar.
- Der Sketch `tonie_test` war nur ein Machbarkeitstest; die Firmware wird
  neu und sauber aufgebaut, der Sketch dient als Referenz.

## Entscheidungen von Tobias (05.11.2026, Runde 2)

Grundlage: `pivot_ohne_v3.md`, `goldfish_pivot_raw.md`, `research_mpd_bausteine.md`.

- **Phoniebox V3 entfällt.** Eigene schlanke Box-Software in Python direkt
  auf MPD (python-mpd2, pyserial, paho-mqtt). Kleinste Form: ein Dienst;
  V3-Funktionen (Lautstärke-Grenzen, Timer, Leerlauf-Abschaltung, Tasten,
  Installationsskript) werden nur nachgebaut, wenn eine Stufe sie braucht,
  nach einer festen Liste im Design. Endgültige Bestätigung nach dem ersten
  Lauf am Pi. Folgen: am Mac kein Docker und keine Brücke; Mac und Pi lesen
  die Serielle direkt, Unterschied nur in der Konfiguration.
- **Notweg ohne HA:** SSH-Befehl `tobibox status` + Status-Admin-Karte;
  myMPD optional als fertige Oberfläche.
- **NAS von unterwegs: Tailscale** (QNAP-App + Boxen), Zugriff per ACL nur
  auf den Medienordner, NAS-Konto nur lesend, Schlüssel pro Box widerrufbar.
  myQNAPcloud und offene Ports werden nicht genutzt.
- **Hotspot:** voller Abgleich inkl. neuer Folgen, Medien-Download aber nur
  am Lader oder bei Akku über ~50 %.
- Damit sind in Thema 2 die Brücke und der TCP-Transport hinfällig, und
  Themen 6 und 7 vereinfachen sich (kein V3-Adapter, kein V3-Pin, kein
  V3 im Update-Paket).

## Offene Fragen (Runde 2, erledigt)

1. **Brauchen wir Phoniebox V3 noch?** (Frage von Tobias.) Nach den
   Entscheidungen oben bleibt von V3 wenig übrig, siehe Antwort im Chat
   und folgendes Abwägen. Entscheidung offen.
2. **Hotspot-Abgleich:** Nabu Casa leitet nur zu Home Assistant weiter,
   nicht zum NAS. Für neue Folgen unterwegs braucht die Box einen
   gesicherten Weg zum NAS (z. B. VPN wie Tailscale/WireGuard). Gibt es den
   schon? Gibt es eine Obergrenze fürs Datenvolumen?
