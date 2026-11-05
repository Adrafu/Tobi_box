# Tobi Box — Box-Software (Prototyp und Zielsystem)

*   **Autor:** Tobias (Projektleitung: Claude)
*   **Status:** Draft
*   **Datum:** 2026-11-05
*   **Grundlage:** `concepts_brief.md` (gleicher Ordner) inkl. Entscheidungen
    Runde 1 und 2

--------------------------------------------------------------------------------

## Überblick

Die Tobi Box ist eine mobile NFC-Audiobox für zwei Kleinkinder. Ein Kind legt
eine Figur (echter Tonie) oder eine NFC-Karte auf, und die Box spielt das
zugehörige Hörspiel vom eigenen Bestand. Dieses Dokument beschreibt die
gesamte Software der Box:

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

## Begriffe

*   **Figur:** Tonie oder NFC-Karte, die auf die Box gelegt wird.
*   **Kennung (UID):** Seriennummer des Chips in der Figur. Sie ist auf der
    Figur fest und das Einzige, woran die Box sie erkennt.
*   **Serie:** Ordner mit Folgen (Audiodateien), die zusammen eine Geschichte
    oder Reihe bilden.
*   **Folge:** Eine Audiodatei in einer Serie.
*   **Überraschungs-Serie:** Serie für unbekannte und gesperrte Figuren. Sie
    hat die feste ID `ueberraschung`.
*   **Zuordnung:** Eintrag „Kennung → Serie“ (oder → Aktion, z. B. Status).
    Tobias legt sie in Home Assistant an.
*   **Resume:** Die Box merkt sich je Serie, wo sie aufgehört hat, und spielt
    beim erneuten Auflegen dort weiter.
*   **Zeiger:** Der gespeicherte Resume-Zustand einer Serie: Folge und
    Position. Regeln: siehe „Datenmodell und Dateien“.
*   **Entsperren / gesperrter Tonie:** Manche Tonies sind im Privacy-Modus.
    Sie antworten erst, nachdem die Box sie mit dem Passwort entsperrt hat.
    Mehr im Abschnitt „Baustein 1“.
*   **Entpreller:** Logik in der Firmware, die einzelne Fehllesungen
    ausfiltert und erst dann „liegt auf“ oder „abgehoben“ meldet.
*   **Herzschlag:** Zeile `HB`, die die Firmware alle 2 s sendet. Bleibt sie
    aus, ist der Leser vermutlich weg.
*   **Vorgangs-ID:** Kurze Zufallskennung. Der Box-Dienst erzeugt sie, wenn
    er `PLACED` oder `LOCKED` empfängt. Sie steht in jeder Protokollzeile
    dieses Auflegens und macht den Ablauf nachvollziehbar.
*   **Lernmodus:** Modus, den Tobias in HA startet: Die nächste Figur, die
    innerhalb von 2 min aufgelegt wird, wird der gewählten Serie zugeordnet
    (CUJ 7b).
*   **Lautstärke-Obergrenze:** Höchste Lautstärke, die die Box ausgibt. Es
    gibt mehrere Grenzen; die **wirksame Grenze** ist das Minimum aller
    aktiven. Regel: siehe „Lautstärke“ in Baustein 3.
*   **Status-Admin-Karte:** Karte mit der Aktion „Status“. Die Box spielt dann
    eine Tonfolge, die den Zustand der Prüfpunkte zeigt (CUJ 11).
*   **Gute-Nacht-Karte:** Karte mit der Aktion „Gute Nacht“. Sie startet einen
    Timer; danach blendet die Box aus und hört auf (CUJ 14).
*   **Leise-Zeiten:** Zeitfenster, die Tobias in HA einstellt. Je Fenster gilt
    „leiser“ oder „stumm“ (CUJ 15).
*   **Netz-Klasse:** Einstufung des Netzes: `home`, `hotspot` oder `offline`.
    Regeln: siehe „Netz, Sync, Strom“.
*   **SSID:** Name eines WLAN-Netzes. Die Box erkennt Heimnetz und Hotspot
    daran.
*   **Hotspot:** WLAN, das Tobias' Handy bereitstellt. Die Box verbindet sich
    damit unterwegs wie mit einem bekannten Netz.
*   **Revision:** Versionsnummer der Zuordnungsliste. Nur für diese Liste
    gebraucht. Versionen des Plans heißen **Plan-Revision**.
*   **Listen-ID:** Zufällige Kennung des HA-Speichers, in dem die
    Zuordnungsliste liegt. Sie ändert sich, wenn HA neu aufgesetzt oder aus
    einer Sicherung wiederhergestellt wird.
*   **MQTT / Discovery:** MQTT ist ein einfacher Nachrichtenkanal zwischen
    Geräten. Per Discovery meldet sich die Box so an, dass Home Assistant ihre
    Sensoren und Knöpfe selbst anlegt.
*   **Tailscale:** Privates VPN zwischen eigenen Geräten. Eine **ACL** ist die
    Regel, welches Gerät was erreichen darf.
*   **Nabu Casa:** Bezahlter Fernzugriff auf Home Assistant.
*   **PiSugar:** Akku-Platine für den Raspberry Pi. Sie hat eine eigene Uhr
    (**RTC**) und einen Wecker.
*   **NTP:** Zeitabgleich über das Netz.
*   **MPD:** Music Player Daemon, der Audio-Abspieler auf der Box.
*   **ReplayGain:** Lautheitswerte in den Audiodateien. MPD gleicht damit die
    Lautstärke verschiedener Titel an (D6).
*   **rsync:** Programm, das einen Ordner von einem Rechner auf einen anderen
    abgleicht. Hier: NAS → Box, nur in diese Richtung.
*   **Lit:** Kleine Bibliothek für Web-Bausteine, mit der die HA-Seite
    gebaut wird.
*   **Kern:** Teil des Box-Dienstes ohne Ein-/Ausgabe: Ereignisse rein,
    Befehle raus. Besteht aus vier Teilautomaten (siehe „Kern-Zustände“).
*   **Stufe:** Lieferabschnitt der Umsetzung (Stufe 0 bis 4).
*   **Arbeitspaket (AP):** Aufgabe, die ein Agent umsetzt.
*   **Abnahme:** Prüfung am Ende einer Stufe oder eines AP, bevor sie als
    fertig gilt.
*   **Goldfisch:** Frischer Prüf-Agent ohne Gesprächsverlauf. Er sieht nur das
    Dokument und die darin genannten Dateien. Teil der Review-Methode.
*   **Haiku / Sonnet:** Zwei KI-Modelle. Haiku ist günstiger, Sonnet stärker.
    Beim AP steht, welches es umsetzt.

## Das Problem

Tobias will zwei Boxen bauen, an denen danach nicht mehr programmiert und
gesucht werden muss. Die Box muss alle Abläufe aus „Abläufe (CUJs)“ erfüllen —
auch mit geborgten Figuren, unterwegs ohne Netz und nach einem leeren Akku.

Die bisherige Planung (Plan-Revision 3.7, Stand in `docs/plan/`) setzte auf
Phoniebox V3 (fertige Open-Source-Software für NFC-Audioboxen) mit Plugins und
einem Leser, der sich als USB-Tastatur meldet. Recherche und Goldfisch-Prüfung
haben gezeigt: Phoniebox kann weder Resume noch eine sichere Abhebe-Meldung,
eine Tastatur kann keine Fehler melden, und am Mac wäre der Aufbau nur mit
Docker und einer Brücke testbar. Die meisten Funktionen der Box wären ohnehin
eigener Code.

Lösung: eine eigene Box-Software direkt auf MPD, ein festes Protokoll zum
Leser, Home Assistant als einzige Oberfläche, und ein Aufbau, der am Mac mit
echtem Leser vollständig testbar ist, bevor die Box steht.

## Ausgangslage

Was es schon gibt:

- Das Testprogramm `firmware/tonie_test/`: Es liest NTAG-Karten und Tonies,
  entsperrt Tonies mit dem eigenen Passwort und gibt das Ergebnis über die
  serielle Schnittstelle aus.
- Einen ESP32-S3 mit PN5180-Leser auf Tobias' Schreibtisch am Mac.
- Home Assistant mit laufendem MQTT-Broker; Nabu Casa ist aktiv.
- Ein QNAP-NAS.

Was es noch nicht gibt: den Raspberry Pi (noch nicht da), Audiodateien,
Box-Software, HA-Integration und Tailscale.

Neu sind in diesem Dokument: die Firmware `tobibox-reader`, der Box-Dienst,
die HA-Integration mit eigener Seite, Medien-Sync, Update und die
Hardware-Funktionen mit Simulation. `firmware/tonie_test/` bleibt unverändert
als Referenz.

## Ziele

1.  **Verhalten wie beschrieben.** Alle Abläufe in „Abläufe (CUJs)“
    funktionieren am Mac mit dem echten Leser und laufen als automatische
    Tests ohne Leser.
2.  **Zeitgrenzen eingehalten** (Maßstab für alle Abläufe; Herleitung und
    Rückfallregel: „Zeitbudget“ in Baustein 1):
    - Ton spätestens **1,0 s** nach dem Auflegen einer bekannten Figur
      (Medium lokal vorhanden).
    - Pause spätestens **1,5 s** nach dem Abheben.
    - Lese-Lücken bis **1,0 s** führen zu keiner Pause und keinem Neustart.
3.  **Gleicher Code auf Mac und Pi.** Unterschiede nur in einer
    Konfigurationsdatei (Gerätepfad, Audio-Ausgabe, Pfade, Netz-Erkennung).
4.  **Die Box spielt ohne Netz und ohne Home Assistant** alles, was sie schon
    kennt und lokal hat.
5.  **Bei Stromausfall geht höchstens der zuletzt gespeicherte Zeiger
    verloren** (≤ 30 s Wiedergabe). Alle Zustandsdateien werden atomar
    geschrieben und beim Start geprüft.
6.  **Fehler sind ohne Laptop eingrenzbar:** Status-Admin-Karte, Statusbefehl
    per SSH, einheitliches Ereignisprotokoll, das einen Stromausfall übersteht.
7.  **Updates sind geprüft:** nur manuell aus HA, nur daheim am Lader, Paket
    signiert, mit Selbsttest. Schlägt er fehl, läuft beim nächsten Start
    wieder die alte Version.
8.  **Beide Boxen** laufen aus demselben Paket und erhalten dieselben
    Zuordnungen.
9.  **Keine Funktion wartet auf die Box-Hardware.** Was an Hardware fehlt
    (LED-Ring, Tasten und Drehregler, PiSugar/Akku, Kopfhörer), wird jetzt
    gebaut: mit einer Simulation am Mac, hinter derselben Schnittstelle, die
    die echte Hardware später nutzt. Die echte Hardware ersetzt dann nur den
    Simulations-Treiber (Stufe 4).
10. **Kinderohren geschützt:** Die Lautstärke-Regel („Lautstärke“ in
    Baustein 3) gilt ab Stufe 1, auch für die Startlautstärke.

## Nicht-Ziele

Nicht im Umfang sind:

*   Eigener WLAN-Hotspot der Box.
*   Erreichbarkeit der Box aus dem Internet. Die Box öffnet keinen Port ins
    Internet; Zugriff von außen läuft nur über HA (Nabu Casa) und Tailscale.
*   Betriebssystem- und Kernel-Updates über die Update-Funktion (dafür gibt
    es ein neues SD-Image).
*   Automatisches Erkennen, welche Figur ein Tonie ist (Zuordnung einmal pro
    Exemplar). Geprüft in `research_tonie_erkennung.md`: Auf dem Chip steht
    nur eine Seriennummer; die echte Toniebox fragt die Tonie-Cloud, und eine
    öffentliche Liste „Kennung → Figur“ gibt es nicht.
*   Streaming-Dienste, Mikrofon, Aufnahme.
*   Funktionen, die weder im Plan noch in den CUJs stehen.

Hardware-Funktionen (LED-Ring, Tasten, Akku, Kopfhörer) gehören dagegen zum
Umfang: Sie entstehen in Stufe 4 mit Simulation (Ziel 9).

## Entscheidungen

Entschieden am 05.11. Begründungen abgelehnter Wege: „Abgewogene
Alternativen“.

*   **D1 — Zuordnungen in HA:** Die Zuordnungen liegen in einer eigenen kleinen
    HA-Integration `tobibox` (Python, `custom_components/tobibox/`). Sie
    speichert sie im HA-Speicher (Teil der HA-Sicherung), bietet Aktionen
    (zuordnen, lösen, Lernmodus starten/abbrechen) und veröffentlicht die
    Liste per MQTT an die Boxen. MQTT ist nur Verteilkanal. Risiko: HA-Updates;
    Gegenmittel: wenig HA-API, Tests gegen die HA-Version, Liste zusätzlich
    als Export-Datei (Regeln: Baustein 4).
*   **D2 — Serien erkennen:** Eine eigene **ID-Datei `serie.json`** in jedem
    Serien-Ordner (ID, Anzeigename, Folgen-Reihenfolge, `angelegt_am`),
    angelegt und gepflegt von der HA-Integration. Tobias will eine saubere
    Dateiverwaltung in HA (Umfang: D4). Dafür bindet HA die Medienfreigabe des
    NAS mit Schreibrecht ein (nicht auf `releases/`); die Boxen lesen nur.
    Regeln für Reihenfolge, Ordner ohne `serie.json` und doppelte IDs:
    „Datenmodell und Dateien“.
*   **D3 — Broker und Netz:** MQTT läuft in HA, mit einem eigenen Konto je Box
    und Themenrechten (Baustein 4). Tailscale ist noch nicht eingerichtet
    (HA-Add-on, QNAP-App, Boxen) → Einrichtungsschritte für Tobias in Stufe 3.
*   **D4 — Medienverwaltung und Oberfläche:** Eine eigene Seite in HA
    (Baustein 4), gebaut in Stufe 3. Umfang: Serien anlegen und umbenennen,
    Folgen sortieren und löschen, Audiodateien vom Handy hochladen,
    Überraschungs-Serie befüllen, Zuordnungen je Serie sehen — **keine
    Bilder**. Es gibt noch keine Hörspiele; die Sammlung wächst aus vielen
    Quellen. Folge: Dateien kommen auch am HA vorbei aufs NAS (z. B. vom PC);
    die Integration erkennt neue Ordner und Dateien selbst.
*   **D5 — Audioformate:** Neben mp3 spielt die Box m4a/AAC, FLAC, Ogg Vorbis,
    Opus und WAV (MPD kann sie). Kopiergeschützte Dateien (z. B. alte
    iTunes-Käufe mit DRM) lassen sich nicht abspielen: Die HA-Integration
    prüft neue Dateien und warnt. Die HA-Seite zeigt den belegten Speicher je
    Box-Kapazität (FLAC ist etwa 5× größer als mp3).
*   **D6 — Lautheitsangleich (Plan 7.2):** Die Lautstärke aller Titel wird
    angeglichen. Gemessen wird **auf dem NAS** von einem kleinen Container
    (Werkzeug `rsgain`), der ReplayGain-Werte in neue Dateien schreibt.
    Auslöser: neue Dateien (erkannt von der HA-Integration) oder ein
    Zeitplan. MPD wendet ReplayGain an (Modus Album oder Track; Track für
    gemischte Quellen). Die Lautstärke-Regel bleibt darüber bestehen
    („Lautstärke“ in Baustein 3). Umsetzung: AP 3.8.
*   **Lautstärke und Gute-Nacht-Karte:** Lautstärke-Regel in Stufe 1,
    Gute-Nacht-Karte in Stufe 4.
*   **Hardware (Ziel 9):** Alle Hardware-Funktionen werden jetzt mit
    Simulation gebaut (Stufe 4).

## Offene Fragen

*   **Leser-Rückkanal:** Soll der Box-Dienst dem ESP32 etwas
    zurückschicken (z. B. Poll-Intervall ändern, Neustart)? Im Prototyp
    reserviert, nicht gebaut.
*   **Audio-Rückmeldungen:** Offen ist die genaue Liste der Töne und wie sie
    klingen. Gebraucht werden Töne für: Start, unbekannte Figur / Überraschung,
    Fehler, Lernmodus Beginn und Ende, Status-Karte in Ordnung / Fehler,
    Akku fast leer, Figur erkannt bei „stumm“. Bis zur Entscheidung gibt es
    Platzhalter-Töne; eigene Aufnahmen von Tobias sind möglich.
*   **Pi-Probelauf:** Termin hängt an der Bestellung des Pi 3A+.
*   **Datenvolumen im Hotspot:** Soll ein Sync im Handy-Hotspot eine
    Obergrenze je Lauf haben? Bisher gilt nur die Akku-Regel.
*   **Ende der letzten Folge:** Nach der letzten Folge springt der Zeiger auf
    Folge 1 (CUJ 4). Dieses Dokument legt fest: die Wiedergabe endet dann mit
    Pause (Tabelle „Wiedergabe-Sitzung“). Tobias bestätigt oder ändert das.
*   **Stumm-Fenster endet bei liegender Figur:** Dieses Dokument legt fest: die
    Wiedergabe startet nicht von selbst; erst Abheben und Auflegen startet sie.
    Tobias bestätigt oder ändert das.

Erledigt: Medienformate und Lautheitsangleich (siehe D5 und D6).

## Risiken

| Risiko | Auswirkung | Gegenmaßnahme | Wann geprüft |
|---|---|---|---|
| Tonie-Entsperrung klappt nicht bei jedem Exemplar | Die Figur spielt die Überraschungs-Serie statt ihrer eigenen | Rückfall auf Überraschungs-Serie (CUJ 6); Test mit Tobias' Figuren | Stufe 1, mit Tobias' Figuren |
| USB-CDC am Pi nicht stabil | Leser fällt aus | Wächter und selbständiges Neuverbinden (CUJ 13); fester Gerätename | Pi-Probelauf |
| Tonqualität / I²S-Ausgabe | Klang schlecht oder verzerrt | Hörtest und Messung am Verstärker; bei Mängeln entscheidet Tobias über die Ausgabe | Pi mit Verstärker |
| Pi 3A+ noch nicht bestellt | Pi-Probelauf und Go/No-Go verzögern sich | Mac-Prototyp läuft ohne Pi (Ziel 3); Bestellung durch Tobias | jetzt |
| Tailscale noch nicht eingerichtet | Kein Sync, kein Update, keine Fernwartung | Anleitung AP 3.6; Voraussetzung im Go/No-Go | Stufe 3 |
| Hotspot-/Akku-Regel nur mit Simulation prüfbar | Sync läuft im Hotspot bei falschem Akkustand | Tests mit Simulation; echte Prüfung, sobald PiSugar und Tailscale da sind | bis PiSugar und Tailscale vorhanden sind |
| HA-Updates brechen die Integration | Zuordnungen in HA nicht mehr bearbeitbar; Boxen behalten ihre letzte Kopie | Wenig HA-API, Tests gegen die HA-Version, automatischer Export auf das NAS | Stufe 3, Tests gegen die HA-Version |
| SD-Karten-Verschleiß, Stromausfall beim Schreiben | Dateisystem beschädigt, Box startet nicht | Atomares Schreiben, Schreibbudget (Datenmodell), Log-Obergrenze, Read-only-Overlay ab dem ersten SD-Fehler, SD-Image im Betriebshandbuch | Pi-Probelauf, Stromausfall-Test |
| Falsche Uhrzeit nach leerem Akku ohne Netz | Leise-Zeiten wirken zur falschen Zeit | PiSugar-RTC beim Start, NTP bei Netz; sonst strengste Leise-Wirkung („Uhr und Zeitquelle“) | Stufe 4 (Simulation), Pi mit PiSugar |
| Pi-Budgets reißen (RAM, Startzeit, Auflegen unter Last) | Ziel 2 verfehlt, Kind wartet | Soll-Werte im Pi-Probelauf; Rückfallregel im Zeitbudget | Pi-Probelauf |
| 512 MB RAM gegen MPD-Datenbank und rsync | Speicherdruck, Verzögerungen beim Auflegen | `nice`/`ionice`, MPD-Datenbank nur nach dem Sync neu einlesen, RAM-Soll-Wert | Pi-Probelauf |
| SD-Platz voll | Sync scheitert, Box nimmt nichts Neues mehr an | Platzprüfung vor dem Sync; HA zeigt belegten Platz je Kapazität (D5) | Stufe 3 |
| Leere oder fehlende NAS-Quelle leert die Box (`--delete`) | Box verliert ihre Medien | Abbruchregeln im Sync („Netz, Sync, Strom“) | Stufe 3 |
| Zwei Schreiber auf der Medienfreigabe (HA und PC) | `serie.json` doppelt oder halb geschrieben | Atomares Schreiben, Prüfung alle 10 min, `angelegt_am`; Rest bleibt bekannte Einschränkung | Stufe 3 |
| MQTT-Konten fehlen oder sind zu weit gefasst | Wer MQTT erreicht, könnte Zuordnungen oder Befehle senden | Konto je Box mit Themenrechten (Beispiel unter `homeassistant/`); ein Update braucht zusätzlich ein signiertes Paket | Stufe 3 |
| HA-Upload-Endpunkt | Angriffsfläche in HA | Nur mit HA-Anmeldung; nur Audioformate nach D5 annehmen | Stufe 3 |
| Tailscale-ACL falsch gesetzt | Box erreicht mehr als HA und die NAS-Freigabe | ACL mit Tags; Abnahmetest, dass andere Ziele gesperrt sind | Stufe 3 |
| HA hat Schreibrecht auf das NAS | Ein kompromittiertes HA verändert Medien oder schiebt Code in Pakete | Schreibrecht nur auf `medien/` und `export/`, `releases/` für HA nur lesbar; Pakete signiert | Stufe 3 |
| Entsperren geborgter Tonies | Der Privacy-Modus fremder Figuren wird aufgehoben | Die Box liest nur die Kennung, mit Tobias' eigenem Passwort, und schreibt nichts auf die Figur | Stufe 1 |
| Firmware-Datei veröffentlicht | Das Passwort könnte aus dem Flash ausgelesen werden | Firmware-Binary nicht veröffentlichen; CI baut nur mit Platzhalter-Passwort | laufend |
| Tailscale-Schlüssel der Box läuft ab | Box fällt unbemerkt aus dem Netz | Schlüsselablauf für die Box-Knoten abschalten (AP 3.6); HA zeigt den Netzstand | Stufe 3, Einrichtung |

## Abläufe (CUJs)

Begriffe: siehe Abschnitt „Begriffe“ oben. Zeitgrenzen: siehe Ziel 2.
Zustände, Übergänge und Vorrang: siehe „Kern-Zustände“.

### CUJ 1: Bekannte Figur auflegen

*   **Given**: Figur ist einer Serie zugeordnet, Folgen liegen lokal, kein
    gespeicherter Zeiger für diese Serie auf dieser Box.
*   **When**: Kind legt die Figur mittig auf.
*   **Then**: Innerhalb der Zeitgrenze (Ziel 2) startet Folge 1 der Serie. Das
    Protokoll zeigt die Kette gelesen → entprellt → zugeordnet → spielt mit
    einer Vorgangs-ID.

### CUJ 2: Abheben

*   **Given**: Eine Figur liegt, ihre Serie spielt.
*   **When**: Kind nimmt die Figur weg.
*   **Then**: Innerhalb der Zeitgrenze (Ziel 2) Pause. Der Zeiger (Folge und
    Position) ist für diese Serie gespeichert.

### CUJ 3: Figur einer Serie wieder auflegen (Resume)

*   **Given**: Für die Serie gibt es einen gespeicherten Zeiger.
*   **When**: Kind legt eine Figur dieser Serie auf — auch nach Neustart oder
    leerem Akku.
*   **Then**: Wiedergabe läuft an der gespeicherten Stelle weiter (mit
    Rücksprung, siehe „Datenmodell und Dateien“).

### CUJ 4: Andere Figur auflegen

*   **Given**: Serie A ist pausiert oder spielt, Figur von Serie B wird aufgelegt.
*   **When**: Kind wechselt die Figur.
*   **Then**: Der Zeiger von Serie A bleibt gespeichert. Serie B läuft an ihrem
    Zeiger weiter, ohne Zeiger beginnt sie bei Folge 1 (Zeigerregeln: siehe
    „Datenmodell und Dateien“).

### CUJ 5: NFC-Karte

*   **Given**: Eine NTAG215-Karte ist einer Serie zugeordnet.
*   **When**: Kind legt die Karte auf.
*   **Then**: Verhalten wie CUJ 1–4.

### CUJ 6: Gesperrter Tonie (Passwort unbekannt)

*   **Given**: Ein Tonie im Privacy-Modus, der sich mit unserem Passwort nicht
    entsperren lässt.
*   **When**: Kind legt ihn auf.
*   **Then**: Die Überraschungs-Serie spielt. Kurze Aussetzer starten sie nicht
    neu. Nicht zuordenbar (keine Kennung).

### CUJ 7a: Unbekannte Figur, Zuordnung danach (Weg A)

*   **Given**: Lesbare Figur ohne Zuordnung. Box offline oder online.
*   **When**: Kind legt sie auf.
*   **Then**: Die Überraschungs-Serie spielt sofort. Die Box merkt sich die
    Kennung und meldet sie an HA, sobald HA erreichbar ist; sie löscht den
    Eintrag erst, wenn HA den Empfang bestätigt hat. HA zeigt „neue Figur“
    (gleiche Kennung von beiden Boxen = ein Eintrag). Tippt Tobias eine Serie
    an, schreibt HA die Zuordnung; die Box holt sie und wechselt, wenn die
    Figur noch liegt, sofort auf die Serie.

### CUJ 7b: Lernmodus (Weg B)

*   **Given**: Box ist online. Tobias wählt in HA „Jetzt kommt ein neuer
    Tonie“, eine Box und eine Serie.
*   **When**: Innerhalb von 2 min wird eine Figur auf diese Box aufgelegt.
*   **Then**: Box meldet die Kennung an HA, HA schreibt die Zuordnung, die
    Serie spielt. Ist die Figur schon zugeordnet, fragt HA vor dem Überschreiben
    nach; wird die Figur währenddessen abgehoben, ändert das nichts, denn die
    Zuordnung hängt an der gemeldeten Kennung. Ohne Figur endet der Lernmodus
    nach 2 min (die Frist misst die Box); Abbruch jederzeit in HA. Beginn und
    Ende sind hörbar. Ist die Box gerade stumm geschaltet (CUJ 15), lernt sie
    trotzdem und bestätigt mit dem leisen Ton, spielt aber nicht.

### CUJ 8: Figur am Rand oder kurz verrutscht

*   **Given**: Eine Figur spielt.
*   **When**: Sie verrutscht, die Lesungen setzen bis 1,0 s aus, oder am Rand
    kommt einmal eine verfälschte Kennung.
*   **Then**: Keine Pause, kein Neustart, kein falsches Hörspiel. Erst wenn
    eine neue Kennung mehrfach in Folge gleich gelesen wurde (Anzahl: siehe
    Baustein 1), gilt sie.

### CUJ 9: Neue Folgen kommen auf die Box

*   **Given**: Neue Audiodateien liegen auf dem NAS. Box im Heimnetz oder im
    Handy-Hotspot (Regeln: siehe „Netz, Sync, Strom“).
*   **When**: Der Abgleich läuft (zeitgesteuert oder von HA angestoßen).
*   **Then**: Neue und geänderte Dateien kommen über Tailscale auf die Box.
    Dateien mit unvollständiger Übertragung sind nie abspielbar. Eine gerade
    spielende Datei wird nie ersetzt (ihre Änderung wartet auf den nächsten
    Abgleich), die laufende Wiedergabe stockt nicht, und eine Figur, die
    während des Abgleichs aufgelegt wird, startet innerhalb der Zeitgrenze.
    HA zeigt Stand und Zeitpunkt.

### CUJ 10: Software-Update

*   **Given**: Box daheim, am Lader, spielt nicht (Bedingungen: siehe
    „Update“).
*   **When**: Tobias stößt in HA das Update an.
*   **Then**: Das signierte Paket wird geprüft, neu daneben installiert,
    umgeschaltet, der Selbsttest läuft. Bestanden → bleibt. Nicht bestanden
    oder kein Start → beim nächsten Start automatisch die alte Version samt
    gesicherten Zustandsdateien. HA zeigt Ergebnis und Grund.

### CUJ 11: „Spielt nicht“ — Fehlersuche ohne Laptop

*   **Given**: Box spielt nicht, kein Handy zur Hand.
*   **When**: Tobias legt die Status-Admin-Karte auf.
*   **Then**: Die Box spielt eine einfache Tonfolge, die zeigt, ob alles in
    Ordnung ist oder welcher Prüfpunkt (Leser, Medien, Netz, Speicher) einen
    Fehler hat. Mit SSH zeigt `tobibox status` dasselbe ausführlich.

### CUJ 12: Unterwegs ohne Netz, danach daheim

*   **Given**: Box war Tage unterwegs, ohne bekanntes Netz.
*   **When**: Sie kommt ins Heimnetz oder in den Handy-Hotspot.
*   **Then**: Sie meldet gesammelte unbekannte Figuren und Status an HA, holt
    neue Zuordnungen und (nach den Regeln aus CUJ 9) neue Folgen.

### CUJ 13: Leser fällt aus und kommt wieder

*   **Given**: Die Box läuft.
*   **When**: Der ESP32 startet neu oder die USB-Verbindung ist kurz weg.
*   **Then**: Der Box-Dienst merkt es (fehlender Herzschlag), protokolliert
    es, verbindet sich selbst neu. `HELLO` setzt den Zähler `seq` zurück und
    versetzt den Kern in „Leser-Zustand unbekannt“. Kommt dieselbe Figur
    wieder, läuft die Serie weiter, ohne neu zu starten. Wurde die Figur
    während der Unterbrechung abgehoben, pausiert die Box spätestens 1,5 s
    nach dem Wächter-Alarm (Tabelle „Wiedergabe-Sitzung“).

### CUJ 14: Gute-Nacht-Karte

*   **Given**: Eine Serie spielt. Die Gute-Nacht-Karte ist als Aktion
    zugeordnet.
*   **When**: Tobias legt die Gute-Nacht-Karte auf.
*   **Then**: Ein Timer startet. Nach Ablauf blendet die Lautstärke aus
    (Regel: „Lautstärke“ in Baustein 3), dann endet die Wiedergabe (Pause mit
    gespeichertem Zeiger). Das funktioniert auch am Mac. Konflikte mit anderen
    Regeln: siehe „Kern-Zustände“.

### CUJ 15: Leise-Zeiten

*   **Given**: Tobias hat in HA Leise-Zeiten frei eingestellt: beliebig viele
    Zeitfenster (Wochentage, von–bis), je Fenster eine Wirkung — **leiser**
    (mit eigener Lautstärke-Grenze) oder **stumm** (keine Wiedergabe).
    HA hat die Einstellung an beide Boxen verteilt; jede Box hält eine Kopie.
*   **When**: Die Uhrzeit erreicht ein Fenster, oder ein Kind legt in einem
    Fenster eine Figur auf.
*   **Then**: Bei „leiser“ gilt die Fenster-Grenze nach der Regel in
    „Lautstärke“ (Baustein 3); eine lautere laufende Wiedergabe wird sanft
    abgesenkt. Bei „stumm“ pausiert die Box und spielt nicht; ein kurzer
    leiser Hinweiston zeigt, dass die Figur erkannt wurde. Nach dem Fenster
    gilt wieder die normale Grenze. Ohne Netz gilt die letzte Kopie. Ist die
    Uhrzeit nicht vertrauenswürdig, gilt die strengste Wirkung des Tages
    (siehe „Uhr und Zeitquelle“).

### CUJ 16: Leerlauf-Abschaltung

*   **Given**: Es läuft keine Wiedergabe und keine Figur liegt.
*   **When**: 20 min vergehen.
*   **Then**: Die Box fährt herunter — außer es läuft ein Sync, ein Update
    oder der Lernmodus: dann wartet sie. Am Lader schaltet sie erst ab, wenn
    Sync und Update fertig sind. Beim Start am Lader prüft sie, ob ein Sync
    ansteht. In der Simulation wird das Herunterfahren nur protokolliert.
    Später (Stufe 4) kann der PiSugar-Wecker die Box am Lader nachts zum Sync
    wecken.

### CUJ 17: Kopfhörer

*   **Given**: Eine Serie spielt über den Lautsprecher.
*   **When**: Ein Kopfhörer-Stecker wird erkannt (später eingesteckt, am Mac
    simuliert).
*   **Then**: Zuerst gilt die Kopfhörer-Grenze, dann schaltet der Ausgang um
    (Regel: „Lautstärke“ in Baustein 3). Der Lautsprecher schaltet ab. Beim
    Ziehen gilt wieder Lautsprecher mit der normalen Grenze.

### CUJ 18: LED-Ring-Zustände

*   **Given**: Die Box läuft. Der Ring kennt die Zustände läuft, Pause, Akku,
    unbekannte Karte, Aufwachen (Plan 5.5.2).
*   **When**: Der Zustand der Box wechselt.
*   **Then**: Der Ring zeigt den passenden Zustand. Die Helligkeit liegt nie
    über 25 %. Am Mac zeigt der virtuelle Ring dasselbe.

### CUJ 19: Tasten und Drehregler

*   **Given**: Eine Serie spielt oder ist pausiert.
*   **When**: Tobias drückt Vor / Zurück, dreht den Drehregler oder drückt den
    Hauptknopf.
*   **Then**: Vor / Zurück springt zur nächsten / vorigen Folge. Der
    Drehregler ändert die Lautstärke innerhalb der wirksamen Grenze (Regel:
    „Lautstärke“ in Baustein 3). Der Hauptknopf kurz: Play / Pause. Lang:
    Zeiger speichern und herunterfahren.

### CUJ 20: Figur liegt schon beim Start

*   **Given**: Die Box ist aus (Akku leer, Strom weg oder ausgeschaltet), eine
    Figur liegt auf dem Leser.
*   **When**: Die Box startet.
*   **Then**: Sobald Leser, Kern und MPD bereit sind, wird die Figur wie ein
    frisches Auflegen behandelt (CUJ 1 bis 3): bekannte Serie spielt am
    Zeiger weiter, unbekannte Figur startet die Überraschungs-Serie. Die Zeit
    bis „bereit“ hat einen Soll-Wert (Pi-Probelauf).

## Technischer Plan

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
                                             │ MQTT-Broker,     │   │ Medien (Audio),   │
                                             │ Zuordnungen,     │   │ Update-Pakete     │
                                             │ Dashboard        │   │ (nur lesen)       │
                                             └──────────────────┘   └───────────────────┘
                                                   ▲ Nabu Casa (nur Tobias' Handy)
```

Die Box spricht mit HA und NAS **immer über Tailscale**, egal ob Heimnetz
oder Handy-Hotspot. So gibt es einen einzigen Weg statt zwei. Die Box öffnet
keinen Port ins Internet; Zugriff von außen läuft nur über HA (Nabu Casa,
nur Tobias' Handy) und Tailscale.

### Baustein 1 — Firmware `tobibox-reader` (ESP32-S3)

- Neu aufgebaut, `firmware/tonie_test/` dient als Referenz für die
  Lese- und Entsperr-Abläufe.
- Build mit **PlatformIO**, feste Versionen (Plattform, Arduino-Core,
  PN5180-Bibliothek per Commit). USB-Modus: nur **CDC** (keine Tastatur).
- Das Tonie-Passwort steht nur in `config.h` (gitignored, nie im Repo). Die
  gebaute Firmware-Datei wird nicht veröffentlicht, weil das Passwort aus dem
  Flash des ESP32 ausgelesen werden könnte.
- Aufbau in drei Teile:
  1. **Leser** (Hardware): ein Abfragezyklus liefert genau ein Ergebnis:
     `nichts`, `uid(typ, bytes)`, `gesperrt`, `fehler(code)`. Fehler werden
     **nicht** als „nichts“ gemeldet.
  2. **Entpreller** (reine Logik, ohne Hardware, auf dem Rechner testbar):
     bekommt Ergebnisse mit Zeitstempel, entscheidet `PLACED` / `REMOVED`.
  3. **Protokoll-Ausgabe**: schreibt Zeilen, zählt für den Herzschlag.
- **Zeitkonstanten** (alle an einer Stelle, in `config.h`):
  - Abfragezyklus ≤ 200 ms (Ziel 150 ms; die Messung in Stufe 1 entscheidet).
  - Neue Kennung gilt nach **2 gleichen Lesungen in Folge** (3 falls die
    Messung zeigt, dass 2 nicht reichen).
  - `REMOVED` nach **1,1 s** ohne gültige Lesung der liegenden Figur.
    Damit: Lücken bis 1,0 s überbrückt, Pause ≤ 1,5 s nach Abheben.
  - Eine andere Kennung, während eine Figur liegt, wird erst nach
    2 gleichen Lesungen als Wechsel gemeldet (`REMOVED` + `PLACED`).
- **Gesperrter Tonie**: eigener stabiler Zustand „gesperrt liegt“; gleiche
  Entprell- und Abhebe-Regeln wie bei einer Kennung.

**Gesperrter Tonie.** Tonies enthalten NXP-ICODE-SLIX-L-Chips im Privacy-Modus.
Sie beantworten nur die Anfrage nach einer Zufallszahl, bis sie mit einem
4-Byte-Passwort entsperrt werden. Mit dem richtigen Passwort liefert der Chip
danach seine Kennung. Scheitert das Entsperren, meldet die Firmware `LOCKED`.
Das Passwort liegt nur in der lokalen `config.h` der Firmware, nie im Repo. Die
Box entsperrt nur mit Tobias' eigenem Passwort, liest nur die Kennung und
schreibt nichts auf die Figur; das gilt auch für geborgte Figuren. Das
Entsperren hat das Testprogramm `firmware/tonie_test/` schon einmal gezeigt.

**Zeitbudget.** Die Grenzen aus Ziel 2 ergeben sich so:

- Auflegen (NTAG-Karte): bis 1 Abfragezyklus Wartezeit (≤ 200 ms) + 2 Lesungen
  (≤ 2 × 200 ms) + Übertragung (< 10 ms) + Dienst und MPD-Start (Ziel
  ≤ 300 ms) = ca. 0,9 bis 1,0 s. Grenze: 1,0 s. Der Puffer ist mit etwa 90 ms
  klein.
- Auflegen (Tonie): wie oben, dazu die **Entsperrzeit** (mehrere Befehle an
  den PN5180). Sie ist hier nicht abgeschätzt, sondern wird in Stufe 1 an
  Tobias' Figuren gemessen und kommt zur Rechnung dazu. Ziel 2 gilt erst als
  erreicht, wenn die Summe mit Entsperrzeit unter 1,0 s liegt.
- Abheben: 1,1 s Timeout + Übertragung (< 10 ms) + Pausenbefehl (< 100 ms) ≈
  1,3 s. Grenze: 1,5 s.
- Lücken: Lücken bis 1,0 s liegen unter der Schwelle von 1,1 s und führen zu
  keinem `REMOVED`.

**Rückfallregel.** Reißt die Messung (in Stufe 1, am Pi auch unter Sync-Last)
die Grenze von 1,0 s, gilt diese Reihenfolge: erst der Abfragezyklus auf
150 ms, dann Rückfrage an Tobias, ob 1,2 s akzeptabel sind. Ziel 2 wird nicht
stillschweigend geändert.

Stufe 1 misst das nach; das Ergebnis steht in `docs/timing.md`. Soll-Werte
für den Pi: siehe Pi-Probelauf.

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
| `HB up=<s> present=<0\|1> polls=<n> hits=<n> rejected=<n> errors=<n> cycle_ms=<n>` | Herzschlag alle 2 s; der Wächter im Box-Dienst schlägt nach 5 s an (2 verpasste Herzschläge plus Reserve) |
| `ERR code=<wort> detail=<text>` | Fehler, z. B. `pn5180_no_response`, `unlock_failed` |

- Zum Leser: `PING` (Antwort `HELLO`); weitere Befehle reserviert (siehe „Leser-Rückkanal“ in den Offenen Fragen).
- **Kennung (kanonisch):** Hex, Kleinbuchstaben, MSB zuerst, ohne Trenner,
  bei ISO 15693 also 16 Zeichen beginnend mit `e00403` für Tonies. Diese
  Schreibweise entsteht **nur** in der Firmware; der Box-Dienst prüft sie
  (Regex) und speichert sie unverändert.
- `seq` zählt jede Meldung hoch und beginnt nach jedem Start des ESP32 bei 0.
  Eine Lücke zeigt verlorene Zeilen. `HELLO` setzt die Zählung beim
  Box-Dienst zurück; danach gleicht der Kern den Zustand über `PLACED` und
  `present=` im Herzschlag ab (CUJ 13, Tabelle „Wiedergabe-Sitzung“).
- Eine Testdatei `docs/protocol/reader-v1-examples.txt` mit gültigen und
  ungültigen Zeilen prüft Firmware-Ausgabe und Parser gleichermaßen.

### Baustein 3 — Box-Dienst `tobiboxd` (Python ≥ 3.11)

Ein Prozess, `asyncio`, ein Paket `tobibox` mit klar getrennten Modulen:

| Modul | Aufgabe | Darf auf Ein-/Ausgabe zugreifen? |
|---|---|---|
| `events` | Typen aller Ereignisse und Befehle; einziger Eigentümer | **nein** |
| `core` | Zustandsautomat: Ereignisse rein, Befehle raus; verbindet die vier Teilautomaten (`session`, `learn`, `quiet` + `bedtime`, `idle`) und legt den Vorrang fest (siehe „Kern-Zustände“) | **nein** (reine Logik, voll testbar) |
| `volume` | Reine Funktion: wirksame Lautstärke-Grenze (siehe „Lautstärke“) | **nein** |
| `clock` | Uhr als Eingang des Kerns: Wanduhr und monotone Uhr, Zeitquelle | Systemuhr (im Test: simulierte Uhr) |
| `library` | Serien und Folgen aus dem Medienordner lesen | Dateisystem (lesen) |
| `store` | Zustandsdateien atomar lesen/schreiben | Dateisystem |
| `reader` | Serielle öffnen, Zeilen parsen, Neuverbinden, Herzschlag überwachen (Wächter: 5 s ohne `HB`) | Serielle |
| `player` | dünne Schicht über MPD (python-mpd2): Abspielen, Pause, Position, Lautstärke (klemmt zusätzlich an der wirksamen Grenze); die Typen für Player-Ereignisse legt AP 1.3 fest | MPD |
| `sounds` | kurze Rückmeldetöne über eigenes Kommando (Mac `afplay`, Pi `aplay`) | Prozess |
| `ha` | MQTT-Anbindung, HA-Discovery, Zuordnungen empfangen, Status senden | Netz |
| `sync` | rsync vom NAS nach den Regeln, danach MPD-Bibliothek aktualisieren | Prozess, Netz |
| `update`, `selftest` | Update mit Rückfall und eingebaute Prüfroutine (siehe „Update“) | Prozess, Dateisystem |
| `net`, `power` | Netz-Klasse (Heim / Hotspot / offline), Lader, Akkustand, Zeitquelle | System bzw. Simulation |
| `eventlog` | dünne Einrichtung von Python `logging`: JSON-Format, rotierende Datei auf dauerhaftem Speicher | Dateisystem |
| `cli` | `tobibox status`, `tobibox sim …` | — |
| Hardware-Module (Stufe 4): `controls` (Tasten, Drehregler), `headphones`, `power`, `led` | je eine Schnittstelle plus Simulations-Treiber; die echte Hardware ersetzt später nur den Treiber | Treiber (Simulation oder Hardware) |
| `app` | **Einziger Zusammenbau-Punkt:** baut Uhr, Module und Kern, verdrahtet sie, startet und beendet den Dienst | alles (nur hier) |

**Abhängigkeitsrichtung.** Abhängigkeiten zeigen nur nach innen zu `events` und
`core` (und den reinen Hilfsmodulen `volume`, `clock`). Der Kern importiert
keines der Ein-/Ausgabe-Module. Nur `app.py` kennt alle Module und steckt sie
zusammen. Die Uhr wird dem Kern eingespeist, er fragt sie nie selbst.

**Ereignisquellen** (alle als Typen in `events.py`):

| Quelle | Ereignisse (Beispiele) |
|---|---|
| Leser (`reader`) | `PLACED`, `LOCKED`, `REMOVED`, `HELLO`, Wächter-Alarm, Leser-Fehler |
| Player (`player`) | Folge zu Ende, Wiedergabe-Fehler, MPD nicht erreichbar |
| HA (`ha`) | neue Zuordnungsliste, Lernmodus starten/abbrechen, Leise-Zeiten, Sync/Update anstoßen |
| Zeitgeber | Takt (mit Zeitstempel), Fristen laufen ab |
| Bedienung (`controls`) | Vor, Zurück, Lautstärke, Hauptknopf kurz/lang |
| Kopfhörer (`headphones`) | Stecker erkannt / gezogen |
| Strom (`power`) | Lader an/aus, Akkustand, Tiefstand, Zeitquelle geändert |
| Netz (`net`) | Netz-Klasse geändert |
| Sync (`sync`) | gestartet, fertig, abgebrochen |
| Update (`update`) | gestartet, Selbsttest bestanden / durchgefallen |

**Der Kern** kennt nur diese Ereignisse und Befehle (Abspielen, Pause, Lautstärke
setzen, Töne, Speichern, Melden, Herunterfahren). Die Typen liegen in
`events.py` (einziger Eigentümer); `core.py` benutzt sie nur.

Die Abläufe (CUJs) werden als **pytest-Tabellen** geschrieben: je CUJ ein
parametrisierter Test mit Zeit, Eingabezeile oder Ereignis und erwarteten
Befehlen. Die Tabellen unter „Kern-Zustände“ sind dafür die Vorlage. Die Tests
laufen ohne MPD und ohne Leser in Millisekunden, am Mac und im Container. Auf
dem Pi laufen sie nicht (kein pytest auf der Box); dort prüft die eingebaute
Prüfroutine einen festen Kurzablauf (siehe „Update“). Für Vorführungen ohne
Hardware gibt es `box/tools/fake_reader.py`.

#### Lautstärke

**Eine Regel, ein Ort.** Alle anderen Abschnitte (Ziel 10, CUJ 14, 15, 17, 19,
Baustein 4, D6) verweisen hierher.

- **Wirksame Grenze = Minimum aller aktiven Grenzen.** Aktive Grenzen sind: die
  globale Obergrenze (Konfiguration), die Grenze eines „leiser“-Fensters, die
  Kopfhörer-Grenze (solange ein Stecker steckt) und der aktuelle Wert eines
  Gute-Nacht-Ausblendens. Keine Lautstärke liegt darüber, weder durch den
  Drehregler noch durch die Startlautstärke noch durch ReplayGain.
- Die Funktion `volume` im Kern berechnet die wirksame Grenze. `player`
  setzt sie durch und klemmt als letzte Sicherung.
- **Zweite Sicherung außerhalb des Dienstes:** MPD startet mit einer festen
  Startlautstärke, und die Ausgabe hat eine harte Obergrenze in der MPD- bzw.
  ALSA-Konfiguration (`deploy/pi/mpd.conf`). So bleibt die Box auch bei einem
  Absturz oder Neustart des Dienstes unter der Grenze.
- **Start:** Der Dienst setzt als Erstes die Lautstärke, bevor etwas spielt.
- **ReplayGain:** MPD nutzt `replaygain_limit`, damit die Angleichung nicht
  über die Aussteuerungsgrenze hebt. Auf der Dienst-Seite gilt trotzdem die
  Grenze oben.
- **Kopfhörerwechsel:** zuerst die neue Grenze setzen, dann den Ausgang
  schalten (nie umgekehrt).
- **Test:** ReplayGain plus Grenze überschreitet den Grenzwert nie (pytest für
  die Funktion, Test gegen echtes MPD im Container). **Messung am
  Verstärker** in Stufe 4; erst sie zeigt, ob die Grenze am Ausgang hält.

#### Uhr und Zeitquelle

- Der Kern bekommt die Zeit als Eingang (`clock`). Alle **Dauern** (Fristen,
  Timer, 20 min Leerlauf, 30 s Resume) laufen auf der monotonen Uhr. Die
  Wanduhr braucht nur der Kern der Leise-Zeiten und das Ereignisprotokoll.
- **Zeitquelle:** beim Start die RTC des PiSugar, bei Netz NTP. Ist die Zeit
  nicht vertrauenswürdig (weder RTC noch NTP seit dem Start), gilt die
  **strengste Leise-Wirkung des Tages**, bis die Zeit stimmt. Die Box meldet
  das an HA und trägt es ins Protokoll (Zeitquelle).
- Am Mac ist die Systemuhr vertrauenswürdig. In Tests ist die Uhr simuliert.

#### Kern-Zustände

Der Kern besteht aus vier Teilautomaten, die einzeln testbar sind. Jede
Tabelle ist die Vorlage für die pytest-Tabelle des Teilautomaten. `core`
verbindet sie und legt den Vorrang fest.

**1. Wiedergabe-Sitzung** (`session`)

Zustände: `leer` (nichts liegt, nichts läuft), `spielt`, `pausiert`,
`gehalten` (Figur liegt, wird wegen „stumm“ nicht gespielt), `unbekannt`
(Leser-Zustand unbekannt).

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `leer`, `pausiert` | `PLACED`, Serie bekannt, nicht stumm | Lautstärke setzen, Zeiger laden, Abspielen | `spielt` |
| `leer`, `pausiert` | `PLACED`, Kennung unbekannt | Kennung in `unknown.json`, Überraschungs-Serie abspielen, Ton | `spielt` |
| `leer`, `pausiert` | `LOCKED` | Überraschungs-Serie abspielen | `spielt` |
| `leer`, `pausiert` | `PLACED`, Typ `aktion` | Aktion auslösen (Status: Tonfolge; Gute Nacht: an Ruhe-Regeln) | unverändert |
| `leer`, `pausiert` | `PLACED`, stumm aktiv | leiser Hinweiston, nichts abspielen | `gehalten` |
| `spielt` | `REMOVED` | Pause, Zeiger speichern | `pausiert` |
| `spielt` | `PLACED` andere Kennung | Zeiger der alten Serie speichern, neue Serie wie in den Zeilen oben | `spielt` |
| `spielt` | Folge zu Ende | Zeiger auf nächste Folge, weiterspielen | `spielt` |
| `spielt` | letzte Folge zu Ende | Zeiger auf Folge 1, Pause | `pausiert` |
| `spielt` | Hauptknopf kurz | Pause, Zeiger speichern | `pausiert` |
| `pausiert` (Figur liegt) | Hauptknopf kurz | Abspielen | `spielt` |
| `spielt` | Wächter-Alarm (kein `HB`) | Frist 1,5 s starten | `unbekannt` |
| `unbekannt` | `HELLO` und `PLACED` mit derselben Kennung innerhalb der Frist | nichts, Wiedergabe läuft weiter | `spielt` |
| `unbekannt` | Frist abgelaufen | Pause, Zeiger speichern | `pausiert` |
| `spielt` | stumm beginnt | sanft ausblenden, Pause, Zeiger speichern | `gehalten` |
| `gehalten` | `REMOVED` | — | `pausiert` |
| `gehalten` | stumm endet | nichts; Wiedergabe startet nicht von selbst | `pausiert` |
| `leer` | Start mit liegender Figur (CUJ 20) | wie `PLACED`, sobald alles bereit ist | `spielt` |
| beliebig | Kopfhörer rein/raus | erst Grenze setzen, dann Ausgang umschalten | unverändert |

Kommt nach der Frist dieselbe Kennung wieder, ist das ein normales Auflegen
mit Resume am gespeicherten Zeiger (erste Zeile).

**2. Lernmodus** (`learn`, gehört der Box)

Zustände: `aus`, `lernt`.

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `aus` | HA-Befehl „Lernmodus“ an diese Box, nicht abgelaufen | Beginnton, Frist 2 min auf der Box starten | `lernt` |
| `aus` | HA-Befehl abgelaufen | ignorieren, protokollieren | `aus` |
| `lernt` | `PLACED` (bekannt oder unbekannt) | Kennung an HA melden, Endeton | `aus` |
| `lernt` | Frist 2 min ohne Figur | Endeton | `aus` |
| `lernt` | HA „abbrechen“ | Endeton | `aus` |

Der Lernmodus ändert die Reaktion der Wiedergabe-Sitzung nicht: Eine
unbekannte Figur startet weiter die Überraschungs-Serie, bis HA die
Zuordnung schickt. Der Befehl geht an genau eine Box, ist nicht dauerhaft
(nicht „retained“) und hat eine Ablaufzeit (Baustein 4).

**3. Ruhe-Regeln** (`quiet` für Leise-Zeiten, `bedtime` für Gute Nacht)

Leise-Zeiten — Zustände: `normal`, `leiser`, `stumm`.

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `normal` | Uhr erreicht „leiser“-Fenster | Fenster-Grenze aktiv, laute Wiedergabe sanft absenken | `leiser` |
| `normal`, `leiser` | Uhr erreicht „stumm“-Fenster | Sitzung: sanft ausblenden und pausieren | `stumm` |
| `leiser`, `stumm` | Fenster endet | Fenster-Grenze aus | `normal` |
| beliebig | Zeit nicht vertrauenswürdig | strengste Wirkung des Tages, Hinweis an HA | entsprechend |
| beliebig | Zeit wieder vertrauenswürdig | Wirkung nach Uhrzeit | entsprechend |

Gute Nacht — Zustände: `aus`, `läuft`, `ausblenden`.

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `aus` | Gute-Nacht-Karte aufgelegt | Timer starten | `läuft` |
| `läuft` | andere Figur aufgelegt | nichts; der Timer läuft für die neue Figur weiter | `läuft` |
| `läuft` | Timer abgelaufen | Ausblenden starten (Grenze sinkt) | `ausblenden` |
| `ausblenden` | Lautstärke bei null | Pause, Zeiger speichern, Lautstärke zurücksetzen | `aus` |
| `ausblenden` | `REMOVED` | normale Pause (Zeiger gespeichert), Lautstärke zurücksetzen | `aus` |

**4. Strom / Leerlauf** (`idle`, `power`)

Zustände: `aktiv`, `leerlauf` (Zähler für 20 min läuft), `herunterfahren`.

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `aktiv` | keine Wiedergabe und keine Figur | Leerlauf-Zähler starten (monotone Uhr) | `leerlauf` |
| `leerlauf` | Wiedergabe oder Figur | Zähler verwerfen | `aktiv` |
| `leerlauf` | 20 min um, Sync, Update oder Lernmodus läuft | warten, Zähler neu | `leerlauf` |
| `leerlauf` | 20 min um, am Lader, Sync oder Update noch offen | warten bis fertig | `leerlauf` |
| `leerlauf` | 20 min um, nichts läuft | Zeiger speichern, Herunterfahren | `herunterfahren` |
| `aktiv` | Hauptknopf lang | Zeiger speichern, Herunterfahren | `herunterfahren` |
| `aktiv`, `leerlauf` | Akku-Tiefstand (nicht am Lader) | Sync abbrechen, Zeiger speichern, Herunterfahren | `herunterfahren` |
| beim Start | am Lader | prüfen, ob ein Sync ansteht | `aktiv` |

In der Simulation wird „Herunterfahren“ nur protokolliert. Am Lader nachts
wecken (PiSugar-Wecker) ist eine Option für Stufe 4.

**Vorrang.** Bei widersprüchlichen Befehlen gewinnt die höhere Stufe:

1. Herunterfahren auf Anforderung (Tiefstand, Hauptknopf lang) und
   Update-Umschaltung
2. stumm
3. Ende von Gute Nacht
4. Lernmodus
5. Wiedergabe

Die **Leerlauf-Abschaltung** ist kein Herunterfahren auf Anforderung: Sie
wartet immer, solange Lernmodus, Sync oder Update laufen. Die Lautstärke
folgt nicht dem Vorrang, sondern der Regel „Minimum aller aktiven Grenzen“.

**Auflösung typischer Konflikte:**

- **Stumm gegen Lernmodus:** Die Box lernt trotzdem, bestätigt mit dem leisen
  Ton und spielt nicht.
- **Gute Nacht läuft, eine andere Figur wird aufgelegt:** Der Timer läuft
  für die neue Figur weiter.
- **Leerlauf-Abschaltung trifft Lernmodus, Sync oder Update:** Die Box schaltet
  nie ab, solange eines davon läuft.
- **Figur wird beim Ausblenden abgehoben:** normale Pause, der Zeiger wird
  gespeichert, Resume setzt dort wieder an.
- **Stumm-Fenster beginnt, während eine Figur spielt:** Die Wiedergabe blendet
  sanft aus und pausiert.
- **Tiefstand während Sync:** Der Sync bricht ab, die Box fährt herunter.

### Datenmodell und Dateien

Alle Dateien JSON, mit `schema_version`, atomar geschrieben (temporäre Datei →
fsync → umbenennen), beim Start geprüft; bei Fehler Rückfall auf `.bak`.
Schema-Änderungen sind nur abwärtskompatibel erlaubt (alte Versionen können die
Dateien weiter lesen); sonst greift die Sicherung beim Update-Rückfall.

| Datei | Inhalt | Wer schreibt | Sync |
|---|---|---|---|
| `mappings.json` | `uid → Eintrag` (Typ `serie` mit Serien-ID oder Typ `aktion`, z. B. Status oder Gute Nacht), Revision und Listen-ID der Liste von HA | nur aus HA übernommen | holt von HA |
| `resume.json` | je Serie: der Zeiger (aktuelle Folge als Dateiname + Position) + Zähler | Box | nie |
| `unknown.json` | unbekannte Kennungen mit Zeitpunkt, noch nicht von HA bestätigt | Box | an HA; Eintrag erst nach Bestätigung von HA löschen |
| `eventlog/` | rotierende Logdateien (JSON-Zeilen) | Box | nie |

- **Serie** = Ordner im Medienordner; Folgen = Audiodateien darin (D5).
  **Reihenfolge, eine Regel überall:** Sie steht in `serie.json` (Liste
  `folgen`). Nur wenn `serie.json` fehlt, gilt die natürliche Sortierung nach
  Dateiname. Dateien, die im Ordner liegen, aber nicht in der Liste stehen,
  kommen am Ende dazu, in Dateinamen-Reihenfolge.
- **Serien-ID** — siehe Entscheidung D2. Die Box spielt auch Ordner ohne
  `serie.json`: Ordnername als ID, Reihenfolge nach Dateiname. Tragen zwei
  Ordner dieselbe ID (Ordner samt `serie.json` kopiert), gibt die
  Integration der **jüngeren** Kopie eine neue ID und meldet das. „Jünger“
  heißt: das spätere `angelegt_am` in `serie.json`.
- **Admin-Karten** (Status usw.) sind Einträge in `mappings.json` mit Typ
  `aktion` statt `serie`. Sie werden in HA wie jede Figur zugeordnet; bis
  Stufe 3 per `tobibox sim`.
- `docs/data-model.md` wächst mit jeder Stufe: Jedes AP ergänzt die Schemas,
  die es einführt.
- **Zeigerregeln (Resume = „nächste ungehörte Folge“):** je Serie ein Zeiger
  (Folge + Position). Ohne gespeicherten Zeiger beginnt die Serie bei Folge 1.
  Folge zu Ende → Zeiger auf nächste Folge, Position 0.
  Letzte Folge zu Ende → Zeiger auf Folge 1. Beim Weiterspielen 3 s
  Rücksprung.
- **Zeiger auf eine fehlende Folge** (gelöscht, umbenannt, aus der Liste): Der
  Zeiger geht auf die nächste vorhandene Folge in der Reihenfolge, Position 0,
  und die Box protokolliert das. Ist die Serie leer: Fehlerton.
- Der Zeiger wird nur gespeichert, wenn er sich geändert hat — bei Pause,
  Folgenwechsel, Figurwechsel und höchstens alle 30 s während der Wiedergabe.
- **Schreibbudget:** Bei 2 h Wiedergabe am Tag sind das etwa 240 Schreibvorgänge
  pro Tag und Box für den Zeiger. Das Ereignisprotokoll hat eine feste
  Obergrenze (Vorschlag: 5 Dateien zu je 1 MB; journald auf dem Pi mit
  begrenztem Platz). Beide Werte werden im Pi-Probelauf geprüft.
- **Überraschungs-Serie** ist eine normale Serie mit fester ID
  `ueberraschung`; fehlt sie oder ist leer → Fehlerton, Protokolleintrag.

### Baustein 4 — Home Assistant: Integration `tobibox`, Seite und MQTT-Schnittstelle

Liegt im Repo unter `homeassistant/custom_components/tobibox/`, wird in HA
als eigene Integration installiert. Sie ist der **einzige Schreiber** für
Zuordnungen und Serien-Metadaten (D1, D2). Die HA-Konfiguration (Dashboard,
Skripte, Automationen) liegt als Dateien im Repo unter `homeassistant/`.

#### Speicher und Medien

- **Speicher:** Zuordnungen im HA-Speicher (`.storage/tobibox`), mit
  Revision und Listen-ID. **Export** automatisch nach jeder Änderung als
  Datei auf das NAS (`tobibox/export/`). Wiederherstellung aus einer Box: HA-Aktion
  „Zuordnungen aus Box-Kopie übernehmen“ (Import von `mappings.json` einer Box).
- **Medien:** Die Medienfreigabe des QNAP ist in HA als Netzwerkspeicher
  eingebunden. Aufbau auf dem NAS: `tobibox/medien/<ordner>/serie.json` +
  Audiodateien, `tobibox/medien/_papierkorb/`, `tobibox/export/`,
  `tobibox/releases/`. HA darf auf `medien/` und `export/` schreiben, auf
  `releases/` nur lesen (eigene Freigabe oder Ordnerrechte; Pakete legt Tobias
  selbst ab).
- **`serie.json`:** `schema_version`, `id` (zufällig, unveränderlich),
  `name` (Anzeige), `angelegt_am`, `folgen` (Reihenfolge als Liste von
  Dateinamen; maßgeblich, Regeln im Datenmodell), `typ` (`normal` oder
  `ueberraschung`). Geschrieben atomar.
- **Erkennen von außen:** Beim Öffnen der Seite und alle 10 min prüft die
  Integration die Freigabe. Neuer Ordner → `serie.json` mit neuer ID und
  Ordnername als Anzeigename. Neue Datei → hinten an die Reihenfolge.
  Fehlende Datei → aus der Reihenfolge, Hinweis. Neue Dateien werden auf
  Format und Kopierschutz geprüft (D5). Erkannte neue Dateien stoßen auch den
  Lautheits-Container auf dem NAS an (D6, AP 3.8). Schreiben HA und ein PC
  gleichzeitig auf die Freigabe, gibt es keine Sperre; das ist als Risiko
  geführt.
- **Löschen** verschiebt in `_papierkorb/` (30 Tage), nie endgültig sofort.
  Die Boxen übernehmen `_papierkorb/` nicht.

#### Aktionen und Seite

- **Aktionen** (auch für Automationen): zuordnen, lösen, Lernmodus starten /
  abbrechen, Serie anlegen / umbenennen, Folgen sortieren / löschen,
  Sync anstoßen, Update anstoßen, Liste an alle Boxen erzwingen, Zuordnungen
  aus Box-Kopie übernehmen, Leise-Zeiten einstellen (Stufe 4).
- **Eigene Seite** in der HA-Seitenleiste („Tobi Box“), läuft auch über
  Nabu Casa am Handy:
  - Serienliste mit Anzahl Folgen und zugeordneten Figuren
  - Serie öffnen: Folgen per Ziehen sortieren, löschen, umbenennen,
    Audiodateien vom Handy hochladen
  - „Neue Figuren“: unbekannte Kennungen beider Boxen (gleiche Kennung = ein
    Eintrag), mit einem Tipp einer Serie zuordnen (Weg A); „Jetzt kommt ein
    neuer Tonie“ (Weg B)
  - Box-Status: Version, Netz, Akku, Sync-Stand, letzter Fehler, abgelehnte
    Listen
  - Speicher: belegter Platz je Box-Kapazität (D5)
- **Technik der Seite:** ein Web-Baustein (JavaScript-Modul, Lit, ohne
  eigenen Build-Server), Daten über die HA-WebSocket-Schnittstelle mit
  HA-Anmeldung; Hochladen über einen eigenen HA-HTTP-Endpunkt mit Anmeldung,
  der nur Audioformate nach D5 annimmt.

#### MQTT-Schnittstelle Box ↔ HA

- Verbindung per **MQTT** über Tailscale zum Broker in HA (D3). Jede Box hat ein
  **eigenes MQTT-Konto** mit Themenrechten: Sie liest `tobibox/mappings` und
  ihre eigenen `cmd`- und `ack`-Themen und schreibt nur ihre eigenen Themen
  (`event`, Status, Discovery). Ein Beispiel für die Broker-Rechte liegt unter
  `homeassistant/mosquitto/`.
- Themen:
  - `tobibox/mappings` (dauerhaft/„retained“, ganze Liste + Revision + Listen-ID)
  - `tobibox/<box>/event` (unbekannt, gelernt, abgelehnte Liste, Fehler)
  - `tobibox/<box>/ack` (HA bestätigt Ereignisse; erst danach löscht die Box
    sie aus `unknown.json`)
  - `tobibox/<box>/cmd` (Lernmodus, Sync, Update): geht an genau eine Box,
    ist **nicht** dauerhaft und trägt eine Ablaufzeit; ein abgelaufener Befehl
    wird ignoriert (Tabelle „Lernmodus“ in den Kern-Zuständen).
- Box meldet sich per **MQTT-Discovery** an: Sensoren (Zustand, läuft
  gerade, Akku, Lader, Netz, Sync-Stand, Version, letzter Fehler, Zeitquelle),
  Knöpfe (Sync jetzt, Update, Lernmodus abbrechen), Auswahl (Serie für
  Lernmodus).
- **Revisionsregel** (Revision = Versionsnummer der Zuordnungsliste; die
  Listen-ID kennzeichnet den HA-Speicher, siehe Begriffe). Die Box übernimmt
  eine Zuordnungs-Nachricht,
  - wenn ihre **Listen-ID neu** ist (unabhängig von der Revision), oder
  - wenn die Listen-ID gleich ist und die Revision **höher** ist als die
    gespeicherte, oder
  - wenn die Nachricht „erzwingen“ trägt (HA-Aktion „an alle Boxen
    erzwingen“).

  Alles andere wird nicht übernommen und als „abgelehnte Liste“ an HA
  gemeldet. Hat der Broker nichts, behält die Box ihre letzte Kopie. Damit
  blockiert eine HA-Wiederherstellung mit niedriger Revision die Boxen nicht
  dauerhaft.

### Netz, Sync, Strom

- **Netz-Klasse** (Pi: NetworkManager-SSID; Mac: Simulation):
  `home` (Heim-SSID **und** NAS über Tailscale erreichbar), `hotspot`
  (Hotspot-SSID), `offline`.
- **Medien-Sync** mit rsync über Tailscale (NAS-Konto nur lesend):
  - `home`: immer erlaubt.
  - `hotspot`: erlaubt, wenn Lader dran oder Akku > 50 %.
  - Dateien landen erst nach vollständiger Übertragung sichtbar im
    Medienordner (`--partial-dir`, `--delay-updates`).
  - **Spiegelnd mit `--delete`, mit Schutz:** Der Sync bricht ab, wenn die
    Quelle fehlt, leer ist oder mehr als 20 % der vorhandenen Dateien löschen
    würde. Vorab prüft er den freien Platz; reicht er nicht, startet er nicht
    und meldet das an HA.
  - Danach MPD-Bibliothek aktualisieren, nicht beim Start.
  - Nie parallel zum Update. Während eines Syncs schaltet die Box nicht ab
    (Tabelle „Strom / Leerlauf“).
  - Eine Datei, die gerade spielt, wird nie ersetzt; ihre Änderung wird auf
    den nächsten Abgleich verschoben.
  - rsync läuft mit niedriger CPU- und IO-Priorität (`nice`/`ionice`).
  - Die Hotspot-/Akku-Regel lässt sich bis PiSugar und Tailscale vorhanden
    sind nur mit Simulation prüfen (siehe Risiken).
- **Strom:** Schnittstelle ab Stufe 3 (AP 3.3), ausgebaut in Stufe 4
  (AP 4.3). Im Prototyp Simulation (`tobibox sim power --charger on
  --battery 40`); die echte PiSugar-Anbindung ersetzt nur den Treiber.
  Abschalt- und Lader-Regeln: CUJ 16 und Tabelle „Strom / Leerlauf“.
- **Uhr:** siehe „Uhr und Zeitquelle“ in Baustein 3.

### Update

- **Auslöser:** HA-Knopf.
- **Bedingungen:** Box daheim (`home`), am Lader, spielt nicht, kein Sync.
- **Paket:** Tarball `tobibox-<version>.tar.gz` mit Code, den **fertig
  gebauten** Python-Abhängigkeiten (auf dem Pi wird nichts gebaut oder per pip
  geholt) und `manifest.json` (Version, Protokoll-Version, Schema-Versionen,
  Firmware-Mindestversion), dazu eine **Signatur**. Liegt auf dem NAS in
  `tobibox/releases/`; HA darf dort nur lesen. Die bisher genannten
  Abhängigkeiten sind reines Python; AP 3.5 prüft das.
- **Signatur:** Den Signierschlüssel hat nur Tobias; er signiert beim Bauen
  des Pakets. Der Prüfschlüssel liegt auf der Box (mit dem SD-Image). Ohne
  gültige Signatur bricht die Box das Update ab und meldet das an HA.
- **Ablauf:** HA-Knopf → Box prüft Bedingungen → lädt Paket → prüft Signatur →
  entpackt nach `releases/<version>/` → sichert die Zustandsdateien → schreibt
  Zustand `testing` und Zähler 0 → stellt den Verweis `current` **atomar** um
  (neuen Verweis anlegen, dann auf `current` umbenennen) → startet neu. Der
  Zustand (`testing`, `ok`, `failed`) steht in einer Zustandsdatei.
- **Selbsttest** als **eingebaute Prüfroutine** der Box (kein pytest auf der
  Box): Dienst läuft, Leser meldet `HELLO` mit passender Protokoll-Version,
  Zustandsdateien lesbar, MPD antwortet, Testton spielt, dazu ein fest
  eingebauter Kurzablauf „Auflegen → Play → Abheben → Pause“ gegen den Kern.
  Auf Aufbauten ohne Leser steht der Prüfpunkt „Leser“ in der Konfiguration auf
  Simulation. Dann Zustand `ok`.
- **Rückfall mit systemd-Mitteln** (kein eigener Wächter-Dienst), Schritt für
  Schritt:
  1. Der Zähler zählt Starts **nur im Zustand `testing`**. Normale Neustarts im
     Zustand `ok` (Leerlauf-Abschaltung, leerer Akku) zählen nicht.
  2. Besteht der Selbsttest, wird der Zustand `ok`.
  3. Schlägt der Dienst fehl (`OnFailure=`), steht der Zähler im Zustand
     `testing` bei 3 oder mehr, oder ist `testing` älter als 5 min (geprüft
     von einem systemd-Timer), dann stellt die Box den Verweis `current` auf
     die vorige Version zurück, **spielt die gesicherten Zustandsdateien
     zurück**, setzt `failed`, startet neu und meldet den Grund an HA.
  4. Die Entscheidung „bleiben oder zurück“ trifft eine kleine Python-Funktion
     (Eingaben: Zustand, Zähler, Alter). Sie hat einen eigenen Test.
- Firmware-Updates des ESP32 sind **nicht** Teil des Pakets (Flashen per
  USB am Mac); das Paket nennt nur die Mindestversion.

### Fehlersuche

- **Ereignisprotokoll**: Python `logging` mit JSON-Formatter und
  `RotatingFileHandler` mit fester Obergrenze (Datenmodell) auf dauerhaftem
  Speicher; auf dem Pi zusätzlich journald dauerhaft, mit begrenztem Platz.
  Eine JSON-Zeile je Ereignis mit Zeit, Zeitquelle, Baustein, Ereignis,
  Ergebnis; die Vorgangs-ID (je `PLACED`/`LOCKED`, siehe Begriffe) ist ein
  Log-Feld. Die **Zeitquelle** sagt, woher die Uhrzeit stammt (Systemuhr, RTC
  oder NTP). So erkennt man falsche Zeiten nach einem Stromausfall.
  Simulierte Ereignisse tragen `sim=true`. Keine Geheimnisse.
- **`tobibox status`** (SSH, ab Stufe 1/2): Prüfpunkte (Leser, Medien, Netz,
  Speicher, HA) ausführlich, letzte Fehler, Versionen, Sync-Stand. In Stufe 3
  kommen HA-Sensoren dazu; für unterwegs gibt es einen Fehlerton.
- **Status-Admin-Karte** (Stufe 2): spielt eine einfache Tonfolge je
  Prüfpunkt: kurz-hoch = in Ordnung, tief = Fehler. Optional später
  Sprachansage.
- **SD-Fehler:** Der erste SD-Fehler (Dateisystemfehler im Kernel-Protokoll) ist
  das Kriterium, ab dem ein Read-only-Overlay eingerichtet wird. Er wird als
  Prüfpunkt „Speicher“ gemeldet.

### Mac und Pi

| | Mac (Prototyp) | Pi 3A+ (Box) |
|---|---|---|
| Leser | `/dev/cu.usbmodem…` | `/dev/serial/by-id/…tobibox…` |
| MPD | Homebrew, Ausgabe CoreAudio | Paket aus Pi OS, Ausgabe ALSA (I²S) |
| Töne | `afplay` | `aplay` |
| Netz, Strom | Simulation | NetworkManager, PiSugar |
| Uhr | Systemuhr | PiSugar-RTC beim Start, NTP bei Netz |
| LED-Ring, Tasten, Kopfhörer | Simulation (virtueller Ring, Tastatur) | echte Treiber (später) |
| Start | `tobiboxd` im Terminal | systemd-Dienst |
| Pfade | `~/tobibox/…` | `/var/lib/tobibox`, `/opt/tobibox` |

Alles in **einer** Konfigurationsdatei `tobibox.toml` je Gerät; im Code gibt
es keine Abfrage „bin ich am Mac?“.

## Abgewogene Alternativen

Quellen: `concepts_brief.md` (Abgewogene Alternativen, Entscheidungen Runde
1 und 2), `pivot_ohne_v3.md` (Begründung für den Verzicht auf Phoniebox V3),
Entscheidungen D1–D6 in diesem Dokument.

### Phoniebox V3 als Basis mit eigenen Plugins

Plan bis Plan-Revision 3.7. **Abgelehnt von Tobias:** Nach den übrigen Entscheidungen
übernimmt eigener Code fast alles (Leser, Resume, Serien, Zuordnung,
Oberfläche, Sync, Update); V3 bliebe nur als MPD-Steuerung mit einer
Plugin-Schnittstelle ohne Stabilitätszusage und einem eingefrorenen
Versionsstand. Ob V3 künftig nicht mehr frisch installierbar ist, ist nicht
geprüft. Am Mac wäre V3 nur in Docker mit Brücke testbar. Die Entscheidung
wird nach dem ersten Pi-Lauf überprüft.

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

**Abgelehnt von der Projektleitung:** Für ESPHome ist keine Unterstützung
dokumentiert, den Privacy-Modus von ICODE-SLIX-L-Chips mit einem Passwort
aufzuheben; ohne das lassen sich Tonies nicht lesen. Die eigene Firmware
kann das nachweislich (`firmware/tonie_test/`).

### V3-Weboberfläche oder eigene Handy-Seite auf der Box

**Abgelehnt von Tobias:** HA ist die einzige Oberfläche, auch von unterwegs
über Nabu Casa. Die Box wird nicht ins Netz geöffnet. Notweg ohne HA:
`tobibox status` per SSH und Status-Admin-Karte.

### Zuordnungen auf mehreren Seiten schreiben (Box und HA, Zwei-Wege-Sync)

**Abgelehnt von Tobias:** Konflikte bei zwei Boxen und Offline-Betrieb.
HA ist einziger Schreiber, Resume bleibt pro Box.

### MQTT als Speicher der Zuordnungen oder Dienst auf dem NAS (D1)

**Abgelehnt von Tobias:** MQTT als **Speicher** (dauerhafte Nachricht als
einzige Ablage) braucht fummelige HA-Skripte und kann die Liste bei einem
Fehler überschreiben; ein NAS-Dienst wäre ein weiterer Dienst. Gewählt:
eigene HA-Integration als Speicher. MQTT dient nur als **Verteilkanal**
(Revisionsregel: Baustein 4).

### Serie über den Ordnernamen erkennen (D2)

**Abgelehnt von Tobias:** Umbenennen würde Zuordnungen und Resume brechen;
gewünscht ist eine saubere Dateiverwaltung in HA. Gewählt: `serie.json` mit
fester ID.

### Medienverwaltung mit HA-Bordmitteln oder fertigem Datei-Manager (D4)

**Abgelehnt von Tobias:** Bordmittel verteilen die Bedienung auf zwei Orte
und machen Sortieren umständlich; ein fremder Datei-Manager kennt keine
Serien. Gewählt: eigene Seite in HA. Der Vorschlag des Prüfers, die Seite in
eine spätere Stufe zu verschieben, wurde von Tobias abgelehnt, weil die
Agents sie parallel bauen können.

### Medien von Hand auf die SD-Karte kopieren

**Abgelehnt von Tobias:** Es gibt zwei Boxen, die Sammlung wächst aus vielen
Quellen, und Tobias will die Verwaltung in HA. Von Hand müsste er jede Karte
einzeln aus dem Gehäuse nehmen und beide Boxen gleich halten.

### Syncthing statt rsync

**Abgelehnt von der Projektleitung:** rsync arbeitet nur in eine Richtung
(NAS → Box), braucht keinen zusätzlichen Dienst auf dem Pi, und das NAS ist die
einzige Quelle. Syncthing gleicht in beide Richtungen ab und ließe die Box
das NAS verändern.

### NAS von außen über myQNAPcloud oder QVPN/WireGuard

**Abgelehnt von Tobias:** Ein aus dem Internet erreichbares QNAP ist ein
bekanntes Angriffsziel (QNAP-Hinweis QSA-22-24 nach DeadBolt); QVPN braucht
einen offenen Port am Router. Gewählt: Tailscale mit ACL.

### Lautheit auf jeder Box messen (D6)

**Abgelehnt von Tobias:** Jede Box würde selbst rechnen und dafür eigenen Code
brauchen, statt das eingebaute ReplayGain von MPD zu nutzen. Gewählt: einmal
auf dem NAS messen und Tags in die Dateien schreiben.

### Eigener WLAN-Hotspot der Box

**Abgelehnt von Tobias:** Dauerfunk kostet Akku; stattdessen verbindet sich
die Box mit seinem Handy-Hotspot wie mit einem bekannten Netz.

### Update per `git pull`

**Abgelehnt von Tobias:** Kein Selbsttest, kein automatischer Rückfall.
Gewählt: Paket in eigenem Verzeichnis, Verweis `current`, Rückfall über
systemd.

### Automatische Erkennung der Figur

**Mit dem Chip allein nicht möglich** (siehe `research_tonie_erkennung.md`): Der
Chip trägt nur eine Seriennummer; die Zuordnung erfolgt einmal pro Exemplar.

## Umsetzungsplan

Grundregeln für die Umsetzung:

- Jedes Arbeitspaket (AP) setzt ein Agent um, mit dem billigsten passenden
  Modell (in Klammern; Haiku = günstiger, Sonnet = stärker). Danach prüft ein
  **frischer Agent** (Goldfisch, Sonnet) den Code gegen dieses Dokument, bevor
  das AP als fertig gilt.
- Jedes AP liefert Tests, die im Container ohne Hardware laufen
  (Firmware-Logik: PlatformIO `native`; Box-Dienst: pytest; MPD-Tests mit
  echtem MPD im Container). Auf der Box selbst läuft kein pytest; dort
  prüft die eingebaute Prüfroutine (siehe „Update“).
- Kein AP ändert die Verträge aus Stufe 0 eigenmächtig; Änderungswünsche
  gehen an die Projektleitung.
- Jedes AP ergänzt `docs/data-model.md` um die Schemas, die es einführt.
- Keine Funktion wartet auf Hardware: Fehlende Hardware wird mit einer
  Simulation am Mac gebaut (Stufe 4).
- Abhängigkeitsregel: Module zeigen nur nach innen zu `events` und `core`;
  nur `app.py` kennt alle Module (Baustein 3).
- Kein Geheimnis im Repo: `config.h`, `tobibox.toml` mit Zugangsdaten,
  Tailscale-Schlüssel, MQTT-Passwörter und der Signierschlüssel sind
  gitignored bzw. liegen nicht im Repo; im Repo liegen nur `*.example.*`.

### Stufe 0 — Verträge (Projektleitung schreibt, Goldfisch prüft)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `docs/protocol/reader-v1.md` | neu | Protokoll v1 vollständig: Zeilen, Felder, Kennungsformat, Zeitkonstanten, Fehlercodes, Verhalten bei unbekannten Zeilen. Einziger Vertrag zwischen Firmware und Box-Dienst. |
| `docs/protocol/reader-v1-examples.txt` | neu | Gültige und ungültige Beispielzeilen mit erwarteter Auslegung; Testgrundlage für beide Seiten. |

Das Kennungsformat steht in `reader-v1.md`. `docs/data-model.md` wächst mit
jeder Stufe (jedes AP ergänzt seine Schemas und die Regeln: atomar schreiben,
`.bak`, `schema_version`, Migration).

Abnahme: Goldfisch-Review der zwei Dateien ohne Blocker, Freigabe durch Tobias.

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
| `box/src/tobibox/events.py` | neu | Ereignis- und Befehls-Typen des Kerns; einziger Eigentümer dieser Typen. Katalog aller Quellen: Leser, Player, HA, Zeitgeber, Bedienung, Kopfhörer, Strom, Netz, Sync, Update. |
| `box/src/tobibox/core.py` | neu | Verbindet die Teilautomaten und setzt den Vorrang („Kern-Zustände“). Reine Logik; benutzt die Typen aus `events.py`. |
| `box/src/tobibox/session.py` | neu | Teilautomat Wiedergabe-Sitzung: Auflegen, Abheben, Wechsel, gesperrt, unbekannt, Überraschung, Leser-Zustand unbekannt (Tabelle in „Kern-Zustände“). |
| `box/src/tobibox/volume.py` | neu | Reine Funktion: wirksame Grenze = Minimum aller aktiven Grenzen (zunächst globale Obergrenze und Startlautstärke; weitere Eingänge in Stufe 4). |
| `box/src/tobibox/clock.py` | neu | Uhr als Eingang: Wanduhr, monotone Uhr, Zeitquelle; im Test simulierte Uhr. |
| `box/src/tobibox/protocol.py` | neu | Zeilen-Parser nach `reader-v1.md`, prüft Kennungsformat. |
| `box/src/tobibox/reader.py` | neu | Serielle öffnen, Zeilen lesen, `HELLO`-Prüfung (setzt `seq` zurück), Herzschlag-Wächter (5 s ohne `HB`, bei 2-s-Takt), selbst neu verbinden. |
| `box/src/tobibox/store.py` | neu | Atomares Lesen/Schreiben, `.bak`, `schema_version`, Zeiger nur bei Änderung. |
| `box/src/tobibox/library.py` | neu | Serien aus `serie.json` lesen; Folgen-Reihenfolge nach der Regel im Datenmodell; Überraschungs-Serie; Zeiger auf fehlende Folge → nächste vorhandene. |
| `box/src/tobibox/config.py` | neu | `tobibox.toml` laden und prüfen, inkl. globaler Lautstärke-Obergrenze und Startlautstärke. |
| `box/src/tobibox/eventlog.py` | neu | Dünne Einrichtung von Python `logging`: JSON-Formatter, `RotatingFileHandler` mit fester Obergrenze auf dauerhaftem Speicher; Vorgangs-ID als Log-Feld. |
| `box/src/tobibox/cli.py` | neu | Erste Fassung von `tobibox status` (Leser, letzte Fehler, Versionen). |
| `box/tools/fake_reader.py` | neu | Gibt Protokollzeilen auf ein Pseudo-Terminal aus; Vorführen und Testen ohne Hardware. |
| `box/tests/unit/` | neu | Tests je Modul; `test_volume.py` (Minimum gewinnt, nie darüber); `test_session.py` (Tabelle „Wiedergabe-Sitzung“). |
| `box/tests/cuj/test_cujXX_*.py` | neu | Je CUJ dieser Stufe (1, 2, 5, 6, 8, 13) ein parametrisierter pytest-Test: Zeit, Eingabezeile oder Ereignis, erwartete Befehle. CUJ 13 deckt `seq`-Rücksetzen, Abheben während der Unterbrechung und Wächter-Alarm mit 1,5-s-Frist ab. |
| `docs/data-model.md` | neu | Erste Schemas: `serie.json`, `mappings.json`, Ereignisprotokoll-Zeile. |
| `box/tests/integration/test_reader_pty.py` | neu | Leser über Pseudo-Terminal: Trennung, Müllzeilen, Neustart des ESP32 (`HELLO`, `seq` bei 0). |

**AP 1.3 Player und Töne** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/player.py` | neu | Dünne MPD-Schicht: Abspielen, Pause, Position, Lautstärke, Ereignis „Folge zu Ende“. Setzt die wirksame Grenze aus `volume.py` durch und klemmt als letzte Sicherung. Setzt beim Start zuerst die Lautstärke. Typen legt dieses AP fest. |
| `box/src/tobibox/sounds.py` | neu | Kurze Töne über konfigurierbares Kommando. |
| `box/src/tobibox/app.py` | neu | **Einziger Zusammenbau-Punkt:** baut Uhr und Module, verdrahtet reader → core → player, Zeitgeber, sauberes Beenden. |
| `box/sounds/` | neu | Platzhalter-Töne inkl. einem Fehlerton und einem leisen Hinweiston (später eigene von Tobias). |
| `box/tests/integration/test_player_mpd.py` | neu | Gegen echtes MPD im Container: Start, Pause, Position, Folgenende, Lautstärke nie über der Grenze (auch nach Dienst-Neustart und mit ReplayGain-Tags in einer Testdatei). |

**AP 1.4 Mac-Einrichtung und Doku** (Haiku)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/config/tobibox.mac.example.toml` | neu | Mac-Konfiguration (Gerätepfad, MPD, Pfade, Lautstärke-Obergrenze, Simulation). |
| `box/config/mpd.mac.example.conf` | neu | MPD am Mac mit fester Startlautstärke und harter Obergrenze. |
| `docs/betrieb/mac-prototyp.md` | neu | Schritt für Schritt: Homebrew, MPD, Python-Umgebung, Firmware flashen, Testserie anlegen, `tobiboxd` starten, Vorführung der CUJs. |
| `box/medien-beispiel/` | neu | Kleine Beispielserie mit `serie.json` und kurzen Test-Audiodateien (selbst erzeugte Töne, keine fremden Inhalte). |

**AP 1.5 Automatische Prüfung** (Haiku)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `.github/workflows/ci.yml` | neu | Bei jedem Push: pytest (mit MPD), PlatformIO `native`-Tests, Firmware-Build für `esp32s3` (mit Platzhalter-Passwort aus `config.example.h`; die gebaute Datei wird nicht veröffentlicht). |
| `.gitignore` | änd. | `config.h`, `tobibox.toml`, `.venv/`, `.pio/`, Laufzeitdaten. |

**Abnahme Stufe 1:** Alle CUJ-Tests und übrigen Tests grün; Tobias führt am
Mac mit echtem Leser CUJ 1, 2, 5, 6, 8, 13 vor, darunter einen **Leser-Neustart**
(Abziehen und Einstecken des USB-Kabels bei spielender Figur; Test auch mit
Abheben während der Unterbrechung); die Lautstärke-Grenze wirkt (auch beim Start
und nach einem Absturz des Dienstes); der Test „Grenze wird nie überschritten“
ist grün; das Ereignisprotokoll zeigt die Zeitgrenzen eingehalten. Die
Messung wird als `docs/timing.md` festgehalten (Zeitbudget je Schritt — Lesen,
Entprellen, Entsperren, Übertragen, MPD-Start — gegen 1,0 s / 1,5 s / 1,0 s,
gemessen über das Ereignisprotokoll). Reißt sie die Grenze, gilt die
Rückfallregel im Zeitbudget (Baustein 1).

### Stufe 2 — Resume, Serien, Zuordnung lokal (CUJ 3, 4, 7a/7b ohne HA, 11, 20)

**AP 2.1 Resume und Serienzeiger** (Sonnet): `session.py`, `core.py`, `store.py`
(Zeiger-Datei, nur bei Änderung speichern), `app.py` (Speichern höchstens alle
30 s und bei Pause), CUJ-Tests 3, 4 und 20 (`box/tests/cuj/`), Test „Zeiger
auf gelöschte oder umbenannte Folge“, Stromausfall-Test (Prozess hart beenden
während des Schreibens), Schema `resume.json` in `docs/data-model.md`.

**AP 2.2 Unbekannte Figuren und Lernmodus** (Sonnet):
`box/src/tobibox/learn.py` (Teilautomat Lernmodus mit 2-min-Frist auf der Box
und Ablaufzeit des Befehls), `unknown.json` (Eintrag erst nach Bestätigung
löschen), `box/src/tobibox/cli.py` ergänzt um `tobibox sim learn …` als
Ersatz für HA bis Stufe 3, CUJ-Tests 7a/7b (auch „stumm gegen Lernmodus“),
Schema `unknown.json` in `docs/data-model.md`.

**AP 2.3 Status und Admin-Karte** (Sonnet):

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/selftest.py` | neu | Prüfpunkte (Leser, Medien, Netz, Speicher) und die eingebaute Prüfroutine mit Kurzablauf „Auflegen → Play → Abheben → Pause“ gegen den Kern; läuft ohne pytest. |
| `box/src/tobibox/cli.py` | änd. | `tobibox status` ausführlich; `tobibox sim` kann eine Karte als Aktion (Typ `aktion`) in `mappings.json` zuordnen, bis HA das in Stufe 3 übernimmt. |
| `box/src/tobibox/core.py`, `session.py` | änd. | Karte mit Typ `aktion` löst die Aktion aus statt einer Serie (Status). |
| `box/sounds/` | änd. | Einfache Tonfolge je Prüfpunkt (kurz-hoch = in Ordnung, tief = Fehler). |
| `box/tests/cuj/test_cuj11_*.py` | neu | CUJ 11 als pytest-Tabelle. |
| `docs/data-model.md` | änd. | Eintrag Typ `aktion` in `mappings.json`. |

**Abnahme Stufe 2:** wie Stufe 1, zusätzlich Vorführung von Resume über
Neustart, Lernmodus per `tobibox sim` und CUJ 20 (Figur liegt beim Start).

### Pi-Probelauf (sobald der Pi 3A+ da ist)

**AP P.1 Pi-Installation** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `deploy/pi/install.sh` | neu | Auf frischem Pi OS Lite: Pakete (MPD), Benutzer, Verzeichnisse, Python-Umgebung, Dienste; Zustandsverzeichnis mit `noatime`. |
| `deploy/pi/tobiboxd.service` | neu | systemd-Dienst, Neustart bei Absturz. |
| `deploy/pi/99-tobibox-reader.rules` | neu | Fester Gerätename für den ESP32 (eigene USB-Kennung aus der Firmware). |
| `deploy/pi/mpd.conf` | neu | MPD für die Box: feste Startlautstärke, harte Obergrenze der Ausgabe, `replaygain_limit`. |
| `deploy/pi/journald-tobibox.conf` | neu | journald dauerhaft (`Storage=persistent`) mit begrenztem Platz, damit das Protokoll einen Stromausfall übersteht. |
| `box/config/tobibox.pi.example.toml` | neu | Pi-Konfiguration. |
| `docs/betrieb/pi-probelauf.md` | neu | Ablauf und Prüfliste: dieselben CUJ-Tests und Vorführungen wie am Mac, plus die Messpunkte der Tabelle unten. |

**Soll-Werte für den Pi-Probelauf** (Vorschlag der Projektleitung; Tobias
bestätigt oder ändert sie):

| Messpunkt | Soll-Wert |
|---|---|
| Benutzter Arbeitsspeicher, alle Dienste laufen | ≤ 300 MB |
| Start (Strom an) bis „bereit“ | ≤ 40 s |
| Auflegen einer bekannten Figur, während ein Sync läuft | ≤ 1,0 s |
| Auflegen eines Tonies (mit Entsperrzeit), ohne Last | ≤ 1,0 s |
| Abheben bis Pause | ≤ 1,5 s |
| Figur liegt beim Start (CUJ 20) | spielt, sobald „bereit“ |
| Schreibvorgänge pro Tag (Zeiger, Protokoll) | im Schreibbudget des Datenmodells |
| Temperatur, Stromausfall-Test | Dateien nach hartem Ausschalten lesbar |

Werden die Werte verfehlt, gilt die Rückfallregel im Zeitbudget (Abfragezyklus
150 ms, dann Rückfrage an Tobias, ob 1,2 s akzeptabel sind).

**Abnahme:** Prüfliste vollständig grün, Unterschiede zum Mac dokumentiert;
damit ist der Wegfall von V3 endgültig bestätigt.

### Go/No-Go mit Tobias vor Stufe 3

Stufe 3 beginnt, wenn:

1. die Abnahmen von Stufe 1 und 2 bestanden sind,
2. der Pi-Probelauf bestanden oder bewusst verschoben ist (mit Begründung),
3. keine Blocker-Befunde aus den Goldfisch-Reviews mehr offen sind,
4. die Voraussetzungen bereit sind: Tailscale (HA-Add-on, QNAP-App) und der
   MQTT-Broker in HA laufen, HA hat Schreibrecht auf `medien/` und `export/`
   (auf `releases/` nur Leserecht), Tobias hat das Schlüsselpaar zum Signieren
   erzeugt.

### Stufe 3 — HA, Medienverwaltung, Sync, Netz, Update, Lautheit (CUJ 7a/7b mit HA, 9, 10, 12)

**AP 3.1 HA-Integration Backend** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `homeassistant/custom_components/tobibox/manifest.json` | neu | Integration, Abhängigkeit MQTT, Version. |
| `…/__init__.py`, `config_flow.py` | neu | Einrichtung: Medienpfad, Boxen. |
| `…/store.py` | neu | Zuordnungen mit Revision und Listen-ID im HA-Speicher; automatischer Export auf das NAS nach jeder Änderung; Import aus einer Box-Kopie. |
| `…/media.py` | neu | `serie.json` lesen/schreiben (mit `angelegt_am`), Erkennen neuer Ordner/Dateien, Formate und DRM-Warnung (D5), Speicheranzeige, Papierkorb, Hochladen, Auslöser für AP 3.8. |
| `…/mqtt.py` | neu | `tobibox/mappings` veröffentlichen (Revision, Listen-ID, „erzwingen“), Box-Ereignisse empfangen und bestätigen (`ack`), Befehle mit Ablaufzeit an eine Box senden, abgelehnte Listen anzeigen. |
| `…/websocket_api.py`, `http.py` | neu | Daten für die Seite, Hochladen mit Anmeldung (nur Audioformate). |
| `…/services.yaml`, `translations/de.json` | neu | Aktionen und Texte. |
| `homeassistant/mosquitto/acl.example` | neu | Beispiel für Broker-Rechte: ein Konto je Box, Themenrechte wie in Baustein 4. |
| `homeassistant/tests/` | neu | Tests mit `pytest-homeassistant-custom-component` (Testhilfe für HA-Integrationen); darunter „HA-Wiederherstellung mit neuer Listen-ID und niedriger Revision“. |

**AP 3.2 HA-Seite** (Sonnet): `homeassistant/custom_components/tobibox/frontend/tobibox-panel.js`
— Serienliste, Folgen ziehen, Hochladen, Umbenennen, Neue Figuren, Lernmodus,
Box-Status, Aktionen „erzwingen“ und „aus Box übernehmen“; bedienbar am Handy.

**AP 3.3 Box-Dienst: HA, Netz, Strom** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/ha.py` | neu | MQTT mit eigenem Konto, Discovery, Zuordnungen nach der Revisionsregel (Listen-ID, erzwingen) übernehmen, abgelehnte Listen melden, Ereignisse melden und auf `ack` warten, Befehle mit Ablaufzeit prüfen, HA-Sensoren inkl. Status. |
| `box/src/tobibox/net.py`, `power.py` | neu | Netz-Klasse; Strom-Schnittstelle (Simulation); Zeitquelle (NTP). |
| `box/tests/cuj/test_cuj12_*.py` | neu | CUJ 12 als pytest-Tabelle. |
| `docs/betrieb/mqtt-konten.md` | neu | Konto je Box anlegen, Themenrechte, Passwörter nur auf der Box (nicht im Repo). |

**AP 3.4 Medien-Sync** (Sonnet)

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/sync.py` | neu | rsync-Regeln Heim/Hotspot/Akku, sichtbar erst nach Abschluss, `--delete` mit Schutz (Abbruch bei fehlender oder leerer Quelle oder mehr als 20 % Löschungen), Platzprüfung vorab, MPD neu einlesen, Sperre gegen Update, keine Abschaltung während des Syncs, spielende Datei nie ersetzen, `nice`/`ionice`. |
| `box/tests/unit/test_sync.py` | neu | Tests mit lokalem rsync-Ziel, auch leere Quelle, fehlende Quelle, zu viele Löschungen, zu wenig Platz. |
| `box/tests/cuj/test_cuj09_*.py` | neu | CUJ 9, darunter **Auflegen während Sync** (Figur startet innerhalb der Zeitgrenze, laufende Wiedergabe stockt nicht). |

**AP 3.5 Update mit Rückfall und Signatur** (Sonnet): Weist nach, dass die
Abhängigkeiten fertig gebaut im Paket liegen (kein Bauen auf dem Pi).

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/update.py` | neu | Bedingungen prüfen, Paket holen, **Signatur prüfen** (Prüfschlüssel auf der Box), nach `releases/<version>/` entpacken, Zustandsdateien sichern, `current` atomar umstellen (neuer Verweis, dann umbenennen), Zustand `testing`/`ok`/`failed`, Rückfall mit Zurückspielen der Sicherung, Meldung an HA. Die Entscheidung „bleiben oder zurück“ ist eine kleine eigene Funktion. |
| `box/src/tobibox/selftest.py` | änd. | Prüfroutine für das Update: Dienst, `HELLO`, Dateien, MPD, Testton, Kurzablauf gegen den Kern. Ohne pytest. |
| `deploy/build_release.sh` | neu | Paket mit `manifest.json`, **fertig gebauten Abhängigkeiten** und Signaturdatei bauen. |
| `deploy/sign_release.sh` | neu | Paket mit Tobias' Signierschlüssel signieren (Schlüssel bleibt bei Tobias, nicht im Repo, nicht auf NAS oder HA); der Prüfschlüssel kommt ins SD-Image. |
| `deploy/pi/tobiboxd.service.d/rollback.conf` | neu | systemd-Drop-in: Start-Zähler (zählt nur im Zustand `testing`) und `OnFailure=`; kein eigener Wächter-Dienst. |
| `box/tests/unit/test_update.py` | neu | Umschalten, Selbsttest-Fehler, Rückfall nach 5 min und bei Startfehler, ungültige Signatur, Zähler zählt im Zustand `ok` nicht. |
| `box/tests/unit/test_rollback.py` | neu | Die Entscheidungsfunktion mit allen Eingabe-Kombinationen; **Rückfall spielt die gesicherten Zustandsdateien zurück**. |
| `box/tests/cuj/test_cuj10_*.py` | neu | CUJ 10 als pytest-Tabelle. |
| `docs/data-model.md` | änd. | Schema `manifest.json`; Regel „Schemas nur abwärtskompatibel erweitern“. |

**AP 3.6 Einrichtung Tailscale und NAS** (Haiku): `docs/betrieb/tailscale-nas.md`
(QNAP-App, HA-Add-on, Box-Schlüssel, ACL mit Tags nur auf Medienfreigabe und
HA, Nur-Lese-Konto für die Boxen, Rechte für HA: `medien/` und `export/`
schreiben, `releases/` lesen, **Schlüsselablauf der Box-Knoten abschalten**,
Schlüssel sperren), optional ein Assistenten-Skript für die Schritte, die nur
Tobias machen kann. Dazu die Prüfung, dass die ACL andere Ziele sperrt.

**AP 3.7 Betriebshandbuch** (Haiku): `docs/betrieb/handbuch.md` —
Wiederherstellung von Null, SD-Image, „was ist wo konfiguriert“, Fehlerbilder,
HA-Wiederherstellung (Import aus Box-Kopie, „erzwingen“).

**AP 3.8 Lautheitsangleich** (Haiku): Container-Definition für `rsgain` auf dem
NAS, Doku und HA-Auslöser (D6, Plan 7.2: Lautheitsangleich aller Titel).

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `deploy/nas/` (Container-Definition, Zeitplan) | neu | Container mit `rsgain`, schreibt ReplayGain-Tags in neue Dateien; läuft nach Auslöser aus HA oder nach Zeitplan. |
| `docs/betrieb/lautheit.md` | neu | Einrichtung auf dem NAS, Modus Album oder Track (Track für gemischte Quellen), MPD-Einstellung, Zusammenspiel mit der Lautstärke-Regel. |
| `homeassistant/custom_components/tobibox/media.py` | änd. | Löst den Container aus, wenn neue Dateien erkannt werden. |
| `box/tests/integration/test_replaygain_limit.py` | neu | Dateien mit hohem ReplayGain-Wert gegen echtes MPD: die Lautstärke überschreitet die wirksame Grenze nie. |

**Abnahme Stufe 3:** Alle CUJs als pytest-Tabellen grün; Vorführung mit HA am
Handy (über Nabu Casa) und Mac-Box; zusätzlich diese Tests: **ReplayGain plus
Grenze überschreitet den Grenzwert nie**; **Auflegen während Sync** innerhalb
der Zeitgrenze; **Leser-Neustart** bei spielender Figur; **HA-Wiederherstellung
mit neuer Listen-ID** wird von beiden Boxen übernommen (auch bei niedrigerer
Revision); **Rückfall spielt die Zustandsdateien zurück**; Update mit
ungültiger Signatur wird abgelehnt; die Tailscale-ACL sperrt andere Ziele. Der
Plan in `docs/plan/` ist nachgezogen.

### Stufe 4 — Hardware-Funktionen mit Simulation (CUJ 14–19)

Alle Funktionen entstehen jetzt, mit Simulation am Mac hinter derselben
Schnittstelle, die die echte Hardware später nutzt.

**AP 4.1 LED-Ring-Logik** (Sonnet), umsetzt CUJ 18

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/led.py` | neu | Zustände laut Plan 5.5.2 (läuft, Pause, Akku, unbekannte Karte, Aufwachen) als reine Logik, Helligkeitsdeckel 25 %. |
| `box/src/tobibox/led_sim.py` | neu | Virtueller Ring am Mac (Terminal- oder HA-Anzeige); der echte Ring ersetzt nur diesen Treiber. |
| `box/tests/unit/test_led.py` | neu | Jeder Zustand; Deckel wird nie überschritten. |

**AP 4.2 Tasten und Drehregler** (Sonnet), umsetzt CUJ 19

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/controls.py` | neu | Vor, Zurück, Lautstärke, Hauptknopf einfach/lang als Ereignisse für den Kern. |
| `box/src/tobibox/controls_sim.py` | neu | Tastatur-Simulation am Mac. |
| `box/src/tobibox/core.py`, `session.py` | änd. | Reagieren auf die Bedienereignisse. |
| `box/tests/unit/test_controls.py` | neu | Tasten-Zuordnung, lang/einfach, Lautstärke bleibt unter der wirksamen Grenze. |

**AP 4.3 PiSugar-Schnittstelle und Leerlauf** (Sonnet), umsetzt CUJ 16

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/power.py` | änd. | Schnittstelle: Akkustand, Lader, Tastenereignisse, Herunterfahren bei Tiefstand, RTC beim Start lesen, Zeitquelle melden. |
| `box/src/tobibox/power_sim.py` | neu | Simulation (`tobibox sim power …`); PiSugar ersetzt später nur den Treiber. |
| `box/src/tobibox/idle.py` | neu | Teilautomat Strom / Leerlauf: Abschaltung nach 20 min, nie während Sync, Update oder Lernmodus, am Lader erst nach Sync und Update; beim Start am Lader Sync prüfen. |
| `box/tests/unit/test_power.py`, `test_idle.py` | neu | Tiefstand, Tastenereignis, 20-min-Leerlauf und Lader-Regel (mit simulierter Uhr). |
| `docs/betrieb/pisugar-wecker.md` | neu | Option: nächtliches Wecken am Lader über den PiSugar-Wecker (nur Beschreibung, Umsetzung nach Tobias' Entscheidung). |

**AP 4.4 Kopfhörer** (Sonnet), umsetzt CUJ 17

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/headphones.py` | neu | Ereignis „Stecker erkannt / gezogen“. |
| `box/src/tobibox/headphones_sim.py` | neu | Simulation des Steckers am Mac. |
| `box/src/tobibox/volume.py`, `player.py` | änd. | Kopfhörer-Grenze als weiterer Eingang der Funktion; Reihenfolge beim Wechsel: erst Grenze setzen, dann Ausgang schalten. |
| `box/tests/unit/test_headphones.py` | neu | Grenze greift vor dem Umschalten und fällt beim Ziehen zurück. |

**AP 4.5 Leise-Zeiten** (Haiku), umsetzt CUJ 15

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/quiet.py` | neu | Teilautomat Leise-Zeiten (Plan 5.7): Fenster mit Wirkung „leiser“ oder „stumm“; Einstellung kommt aus HA (MQTT, dauerhaft, mit Revision und Listen-ID wie die Zuordnungen), lokale Kopie für offline; bei nicht vertrauenswürdiger Zeit strengste Wirkung des Tages. |
| `homeassistant/custom_components/tobibox/` | änd. | Leise-Zeiten in der HA-Seite einstellen und an die Boxen verteilen. |
| `box/tests/unit/test_quiet.py` | neu | Fenstergrenzen mit simulierter Uhr, Zeit nicht vertrauenswürdig, stumm gegen Lernmodus, stumm beginnt während der Wiedergabe. |

**AP 4.6 Gute-Nacht-Karte** (Sonnet), umsetzt CUJ 14

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/bedtime.py` | neu | Teilautomat Gute Nacht: Timer mit Ausblenden über die Lautstärke-Regel; Karte ist ein Eintrag Typ `aktion` in `mappings.json`; muss am Mac funktionieren. |
| `box/tests/cuj/test_cuj_gute_nacht.py` | neu | Timer läuft ab, Lautstärke blendet aus, Wiedergabe endet; andere Figur während des Timers; Abheben während des Ausblendens. |

**Abnahme Stufe 4:** Jede Funktion ist am Mac per Simulation vorführbar; die
Konflikttabelle aus „Kern-Zustände“ ist als Tests grün (stumm gegen
Lernmodus, Gute Nacht mit neuer Figur, Leerlauf gegen Sync/Update/Lernmodus,
Abheben beim Ausblenden, Stumm-Beginn während der Wiedergabe). Die echte
Hardware ersetzt später nur den Simulations-Treiber; dann folgt die
**Messung der Lautstärke am Verstärker**.

### Dokumente, die am Ende nachgezogen werden

| Datei | Änderung |
|---|---|
| `docs/plan/stueckliste-und-psp.md`, `docs/plan/psp-baum.html` | Projektplan (Stückliste und Arbeitspaket-Baum) nachziehen: Punkte, die durch dieses Design ersetzt sind, neu fassen |
| `docs/designs/box-software.md` | angenommene Fassung dieses Dokuments |
| `CLAUDE.md` | Verweis auf Verträge und Arbeitsweise je Stufe |
