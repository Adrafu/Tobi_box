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
    Exemplar).
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
