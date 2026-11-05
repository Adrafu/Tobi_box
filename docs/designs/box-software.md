# Tobi Box — Box-Software (Prototyp und Zielsystem)

*   **Autor:** Tobias (Projektleitung: Claude)
*   **Status:** Approved (05.11.2026, nach EGM-Review Stufen 5–9)

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
    ist nur an `typ=ueberraschung` in ihrer `serie.json` erkennbar; eine feste
    ID gibt es nicht.
*   **Zuordnung:** Eintrag „Kennung → Serie“ (oder → Aktion, z. B. Status).
    Tobias legt sie in Home Assistant an.
*   **Resume:** Die Box merkt sich je Serie, wo sie aufgehört hat, und spielt
    beim erneuten Auflegen dort weiter.
*   **Zeiger:** Der gespeicherte Resume-Zustand einer Serie: Folge und
    Position. Nach dem Ende einer Folge zeigt er auf die nächste Folge
    (Position 0). Regeln: siehe „Datenmodell und Dateien“.
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
    Timer; danach blendet die Box aus und hört auf (CUJ 14). Dauer von Timer
    und Ausblenden stellt Tobias in HA ein (Vorschlag 30 min und 60 s).
*   **Leise-Zeiten:** Zeitfenster, die Tobias in HA einstellt. Je Fenster gilt
    „leiser“ oder „stumm“ (CUJ 15).
*   **Netz-Klasse:** Einstufung des Netzes: `home`, `hotspot` oder `offline`.
    Regeln: siehe „Netz, Sync, Strom“.
*   **SSID:** Name eines WLAN-Netzes. Die Box erkennt Heimnetz und Hotspot
    daran.
*   **Hotspot:** WLAN, das Tobias' Handy bereitstellt. Die Box verbindet sich
    damit unterwegs wie mit einem bekannten Netz.
*   **Revision:** Versionsnummer der Konfiguration (Zuordnungen, Leise-Zeiten
    und Gute-Nacht-Einstellungen; eine Revision für alle). Versionen des Plans
    heißen **Plan-Revision**.
*   **Listen-ID:** Zufällige Kennung des HA-Speichers, in dem die
    Konfiguration liegt. Sie ändert sich, wenn HA neu aufgesetzt oder aus
    einer Sicherung wiederhergestellt wird, und bei der Aktion „Liste neu
    ausrollen“.
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
    Lautstärke verschiedener Titel an, hier mit Peak-Schutz und Obergrenze (D6).
*   **rsync:** Programm, das einen Ordner von einem Rechner auf einen anderen
    abgleicht. Hier: NAS → Box, nur in diese Richtung.
*   **Lit:** Kleine Bibliothek für Web-Bausteine, mit der die HA-Seite
    gebaut wird.
*   **Kern:** Teil des Box-Dienstes ohne Ein-/Ausgabe: Ereignisse rein,
    Befehle raus. Besteht aus vier Teilautomaten (siehe „Kern-Zustände“).
*   **CUJ:** Critical User Journey, ein Ablauf aus Sicht von Kind oder Tobias
    (Abschnitt „Abläufe (CUJs)“).
*   **Baustein:** Teil der Technik im Abschnitt „Technischer Plan“ (Baustein 1
    bis 4).
*   **Teilautomat:** Einer der vier Zustandsautomaten des Kerns (Sitzung,
    Lernmodus, Ruhe-Regeln, Strom / Leerlauf). Jeder ist eine reine Funktion
    `step(zustand, ereignis, jetzt) → (zustand, befehle)`.
*   **Bestätigung (ack):** Antwort von HA, dass eine gemeldete Kennung
    angekommen ist. Erst dann löscht die Box den Eintrag in `unknown.json`.
*   **Stufe:** Lieferabschnitt der Umsetzung (Stufe 0 bis 4; Stufe 3 ist in
    3a und 3b geteilt, mit getrennter Abnahme).
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
    Baustein 3) gilt ab Stufe 1, auch für die Startlautstärke. Am Mac klemmt der Dienst; am Pi kappt zusätzlich ALSA hart.

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
    NAS mit vollem Schreibrecht ein (Entscheidung D); die Boxen lesen nur.
    Regeln für Reihenfolge, Ordner ohne `serie.json` und doppelte IDs:
    „Datenmodell und Dateien“.
*   **D3 — Broker und Netz:** MQTT läuft in HA, mit einem eigenen Konto je Box
    und Themenrechten (Baustein 4). Tailscale ist noch nicht eingerichtet
    (HA-Add-on, QNAP-App, Boxen) → Einrichtungsschritte für Tobias in Stufe 3a.
*   **D4 — Medienverwaltung und Oberfläche:** Eine eigene Seite in HA
    (Baustein 4), gebaut in Stufe 3a. Umfang: Serien anlegen und umbenennen,
    Folgen sortieren und löschen, Audiodateien vom Handy hochladen,
    Überraschungs-Serie befüllen, Zuordnungen je Serie sehen — **keine
    Bilder**. Es gibt noch keine Hörspiele; die Sammlung wächst aus vielen
    Quellen. Folge: Dateien kommen auch am HA vorbei aufs NAS (z. B. vom PC);
    die Integration erkennt neue Ordner und Dateien selbst.
*   **D5 — Audioformate:** Neben mp3 spielt die Box m4a/AAC, FLAC, Ogg Vorbis,
    Opus und WAV (MPD kann sie). Kopiergeschützte Dateien (z. B. alte
    iTunes-Käufe mit DRM) lassen sich nicht abspielen: Die HA-Integration
    prüft neue Dateien: Lässt sich eine Datei mit `ffprobe` nicht öffnen,
    meldet `ffprobe` den Codec `drms` oder scheitert eine Probedekodierung
    von 1 s, warnt sie. Die Box meldet ihren freien Platz mit dem Status; die HA-Seite
    zeigt ihn je Box (FLAC ist etwa 5× größer als mp3).
*   **D6 — Lautheitsangleich (Projektplan `docs/plan/`, Abschnitt 7.2):** Die Lautstärke aller Titel wird
    angeglichen. Gemessen wird **auf dem NAS** von einem kleinen Container
    (Werkzeug `rsgain`), der ReplayGain-Werte in neue Dateien schreibt.
    Auslöser
    ist nur ein Zeitplan im Container (alle 15 min), kein Auslöser aus HA.
    `rsgain` läuft im Easy-Modus mit `-S` (vorhandene Tags nicht neu
    schreiben, sonst überträgt rsync alles erneut), Ziel −18 LUFS (Bezug
    ReplayGain 2.0), feste Version. Es gibt kein offizielles Container-Bild;
    es wird gebaut, die CPU-Architektur des QNAP ist eine Vorleistung von
    Tobias. MPD wendet ReplayGain an (Modus Track, für gemischte Quellen) mit
    `replaygain_preamp` 0 und `replaygain_missing_preamp` −6 dB. Es ist **nicht**
    garantiert, dass ReplayGain nur dämpft: Ein positiver Gain wird durch den
    Peak-Schutz (`replaygain_limit`) und am Pi durch die ALSA-Kappung
    begrenzt. Die Lautstärke-Regel bleibt darüber bestehen („Lautstärke“ in
    Baustein 3). Umsetzung: AP 3.9 (Stufe 3b).
*   **Lautstärke und Gute-Nacht-Karte:** Lautstärke-Regel in Stufe 1,
    Gute-Nacht-Karte in Stufe 4.
*   **Hardware (Ziel 9):** Alle Hardware-Funktionen werden jetzt mit
    Simulation gebaut (Stufe 4).
*   **Entscheidung A — Pause nach jeder Folge:** Nach dem Ende einer Folge
    springt der Zeiger auf die nächste (nach der letzten auf Folge 1) und die
    Box pausiert, auch wenn die Figur noch liegt; weiter geht es erst nach
    erneutem Auflegen oder mit einem kurzen Druck auf den Hauptknopf
    (Entscheidung E).
*   **Entscheidung B — Ende eines „stumm“-Fensters:** Liegt dann eine Figur
    auf, startet nichts von selbst; das Kind legt die Figur erneut auf.
*   **Entscheidung C — Hotspot:** Es gibt keine Datenbegrenzung je Sync; im
    Hotspot gilt nur die Akku-Regel.
*   **Entscheidung D — NAS-Rechte:** HA hat vollen Schreibzugriff auf die
    NAS-Freigabe (`medien/`, `export/`, `releases/`); Tobias ist der einzige
    Benutzer. Die Paket-Signatur (`minisign`) bleibt und schützt davor, dass
    ein manipuliertes HA oder NAS Code auf die Boxen bringt.
*   **Entscheidung E — Hauptknopf nach Folgenende (05.11.):** Ist eine Folge zu
    Ende und die Figur liegt noch auf der Box, spielt ein **kurzer Druck auf den
    Hauptknopf die nächste Folge** (der Zeiger zeigt schon darauf). Ohne Figur
    auf der Box behält der Hauptknopf seine normale Funktion (Play / Pause).

## Offene Fragen

*   **Leser-Rückkanal:** Soll der Box-Dienst dem ESP32 etwas
    zurückschicken (z. B. Poll-Intervall ändern, Neustart)? Im Prototyp
    reserviert, nicht gebaut.
*   **Audio-Rückmeldungen:** Offen ist die genaue Liste der Töne und wie sie
    klingen. Gebraucht werden Töne für: Start, unbekannte Figur / Überraschung,
    Fehler, Lernmodus Beginn und Ende, Status-Karte in Ordnung / Fehler,
    Akku fast leer, Figur erkannt bei „stumm“. Bis zur Entscheidung gibt es
    Platzhalter-Töne; eigene Aufnahmen von Tobias sind möglich.
*   **Pi-Probelauf:** Der Termin hängt an der Bestellung des Pi 3A+. Die
    Soll-Werte (Tabelle im Pi-Probelauf) sind ein Vorschlag; Tobias bestätigt
    sie vor dem Start.
*   **Lautstärke am Ausgang:** Ob die ALSA-Kappung (`softvol`) am Verstärker
    wirklich hält, zeigt nur eine Messung am Pi (Stufe 4, sobald Hardware da
    ist). Bis dahin prüfen die Tests nur die Konfiguration und die Klemmung im
    Dienst.

Erledigt: Medienformate und Lautheitsangleich (siehe D5 und D6), Ende der
letzten Folge und Ende eines „stumm“-Fensters (Entscheidungen A und B),
Datenvolumen im Hotspot (Entscheidung C), Hauptknopf nach Folgenende
(Entscheidung E), Schnittstellen und Datenformate (Stufe 0), die Befunde R1 bis
R18 des Reviews Stufe 9.

## Risiken

| Risiko | Auswirkung | Gegenmaßnahme | Wann geprüft |
|---|---|---|---|
| Tonie-Entsperrung klappt nicht bei jedem Exemplar | Die Figur spielt die Überraschungs-Serie statt ihrer eigenen | Rückfall auf Überraschungs-Serie (CUJ 6); Test mit Tobias' Figuren | Stufe 1, mit Tobias' Figuren |
| USB-CDC am Pi nicht stabil | Leser fällt aus | Wächter und selbständiges Neuverbinden (CUJ 13); fester Gerätename | Pi-Probelauf |
| Tonqualität / I²S-Ausgabe | Klang schlecht oder verzerrt | Hörtest und Messung am Verstärker; bei Mängeln entscheidet Tobias über die Ausgabe | Pi mit Verstärker |
| Pi 3A+ noch nicht bestellt | Pi-Probelauf und Go/No-Go verzögern sich | Mac-Prototyp läuft ohne Pi (Ziel 3); Bestellung durch Tobias | jetzt |
| Tailscale noch nicht eingerichtet | Kein Sync, kein Update, keine Fernwartung | Anleitung AP 3.5; Voraussetzung im Go/No-Go | Stufe 3a |
| Hotspot-/Akku-Regel nur mit Simulation prüfbar | Sync läuft im Hotspot bei falschem Akkustand | Tests mit Simulation; echte Prüfung, sobald PiSugar und Tailscale da sind | bis PiSugar und Tailscale vorhanden sind |
| HA-Updates brechen die Integration | Zuordnungen in HA nicht mehr bearbeitbar; Boxen behalten ihre letzte Kopie | Wenig HA-API, Tests gegen die HA-Version, automatischer Export auf das NAS | Stufe 3a, Tests gegen die HA-Version |
| SD-Karten-Verschleiß, Stromausfall beim Schreiben | Dateisystem beschädigt, Box startet nicht | Atomares Schreiben, Schreibbudget (Datenmodell), Log-Obergrenze, Read-only-Overlay ab dem ersten SD-Fehler, SD-Image im Betriebshandbuch | Pi-Probelauf, Stromausfall-Test |
| Falsche Uhrzeit nach leerem Akku ohne Netz | Leise-Zeiten wirken zur falschen Zeit | PiSugar-RTC beim Start, NTP bei Netz; sonst kleinste „leiser“-Grenze aller Fenster, nie stumm („Uhr und Zeitquelle“) | Stufe 4 (Simulation), Pi mit PiSugar |
| Pi-Budgets reißen (RAM, Startzeit, Auflegen unter Last) | Ziel 2 verfehlt, Kind wartet | Soll-Werte im Pi-Probelauf; Rückfallregel im Zeitbudget | Pi-Probelauf |
| 512 MB RAM gegen MPD-Datenbank und rsync | Speicherdruck, Verzögerungen beim Auflegen | `nice`/`ionice`, MPD-Datenbank nur nach dem Sync neu einlesen, RAM-Soll-Wert | Pi-Probelauf |
| SD-Platz voll | Sync scheitert, Box nimmt nichts Neues mehr an | Platzprüfung vor dem Sync; HA zeigt den freien Platz je Box (D5) | Stufe 3a |
| Leere oder fehlende NAS-Quelle leert die Box (`--delete`) | Box verliert ihre Medien | Abbruchregeln im Sync („Netz, Sync, Strom“) | Stufe 3a |
| Drei Schreiber auf der Medienfreigabe (HA, PC und der Lautheits-Container) | `serie.json` doppelt oder halb geschrieben; vom Container getaggte Dateien überträgt rsync erneut | Atomares Schreiben, Prüfung alle 10 min, `angelegt_am`; Container nur nach Zeitplan, eine vor dem Messen geholte Datei wird einmal nachübertragen (hingenommen); Rest bleibt bekannte Einschränkung | Stufe 3a (Container: 3b) |
| MQTT-Konten fehlen oder sind zu weit gefasst | Wer MQTT erreicht, könnte Zuordnungen oder Befehle senden | Konto je Box mit Themenrechten (Beispiel unter `homeassistant/`); ein Update braucht zusätzlich ein signiertes Paket | Stufe 3a |
| HA-Upload-Endpunkt | Angriffsfläche in HA | Nur mit HA-Anmeldung; nur Audioformate nach D5 annehmen | Stufe 3a |
| Große Uploads über Nabu Casa | Upload vom Handy bricht ab oder wird abgelehnt | Upload als Strom in Blöcken; Test am Handy über Nabu Casa; Ausweg: Dateien per PC auf das NAS legen (D4) | Stufe 3a, Abnahme am Handy |
| Zeitbudget knapp (Abheben nur etwa 90 ms Reserve; RF-Befehle bis 500 ms im Fehlerfall) | Ziel 2 verfehlt | Rückfallregel im Zeitbudget (Arbeit pro Zyklus senken); Messung am Ausgang | Stufe 1 |
| Fehler im Wächter-Skript `guard.py` | Rückfall greift nicht | Skript klein, nur Standardbibliothek, liegt außerhalb von `releases/` und kommt mit dem SD-Image; eigener Test | Stufe 3b |
| Tailscale-ACL falsch gesetzt | Box erreicht mehr als HA und die NAS-Freigabe | ACL mit Tags; Abnahmetest, dass andere Ziele gesperrt sind | Stufe 3a |
| HA hat vollen Schreibzugriff auf die NAS-Freigabe (`medien/`, `export/`, `releases/`) | Ein manipuliertes HA oder NAS könnte Code in Update-Pakete schieben, der auf den Boxen läuft | Pakete sind mit `minisign` signiert; der Signierschlüssel liegt nur bei Tobias auf seinem Mac, der Prüfschlüssel auf der Box; die Box installiert nur Pakete mit gültiger Signatur | Stufe 3b |
| Entsperren geborgter Tonies | Der Privacy-Modus fremder Figuren wird aufgehoben | Die Box liest nur die Kennung, mit Tobias' eigenem Passwort, und schreibt keine Nutzdaten; der Privacy-Modus bleibt aber aufgehoben, bis eine Toniebox ihn wieder setzt | Stufe 1 |
| Firmware-Datei veröffentlicht | Das Passwort könnte aus dem Flash ausgelesen werden | Firmware-Binary nicht veröffentlichen; CI baut nur mit Platzhalter-Passwort | laufend |
| Tailscale-Schlüssel der Box läuft ab | Box fällt unbemerkt aus dem Netz | Schlüsselablauf für die Box-Knoten abschalten (AP 3.5); HA zeigt den Netzstand | Stufe 3a, Einrichtung |

## Abläufe (CUJs)

Begriffe: siehe Abschnitt „Begriffe“ oben. Zeitgrenzen: siehe Ziel 2.
Zustände, Übergänge und Konflikte: siehe „Kern-Zustände“.

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
    Rücksprung, siehe „Datenmodell und Dateien“). Nach dem Ende einer Folge
    pausiert die Box, auch wenn die Figur noch liegt; der Zeiger steht dann auf
    der nächsten Folge (nach der letzten Folge auf Folge 1). Die nächste Folge
    spielt erst, wenn die Figur (oder eine andere Figur derselben Serie) neu
    aufgelegt wird oder der Hauptknopf kurz gedrückt wird (Entscheidung E).

### CUJ 4: Andere Figur auflegen

*   **Given**: Serie A ist pausiert oder spielt, Figur von Serie B wird aufgelegt.
*   **When**: Kind wechselt die Figur.
*   **Then**: Der Zeiger von Serie A bleibt gespeichert. Serie B läuft an ihrem
    Zeiger weiter (nach einer beendeten Folge ist das die nächste Folge), ohne
    Zeiger beginnt sie bei Folge 1 (Zeigerregeln: siehe
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
    Eintrag erst, wenn HA den Empfang bestätigt hat (Antwort auf `…/ack`, siehe
    „MQTT-Schnittstelle“). HA zeigt „neue Figur“
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
    zugeordnet. Dauer von Timer und Ausblenden sind in HA eingestellt
    (Vorschlag 30 min und 60 s).
*   **When**: Tobias nimmt die Serien-Figur weg (Pause) und legt die
    Gute-Nacht-Karte auf; danach legt er die Serien-Figur wieder auf.
*   **Then**: Mit der Karte startet der Timer; die Serie spielt weiter. Nach
    Ablauf blendet die Lautstärke aus (Regel: „Lautstärke“ in Baustein 3),
    dann endet die Wiedergabe (Pause mit gespeichertem Zeiger). Das funktioniert auch am Mac. Konflikte mit anderen
    Regeln: siehe „Kern-Zustände“.

### CUJ 15: Leise-Zeiten

*   **Given**: Tobias hat in HA Leise-Zeiten frei eingestellt: beliebig viele
    Zeitfenster (Wochentage, von–bis), je Fenster eine Wirkung — **leiser**
    (mit eigener Lautstärke-Grenze) oder **stumm** (keine Wiedergabe).
    HA hat die Einstellung mit der übrigen Konfiguration (`tobibox/config`) an
    beide Boxen verteilt; jede Box hält eine Kopie.
*   **When**: Die Uhrzeit erreicht ein Fenster, oder ein Kind legt in einem
    Fenster eine Figur auf.
*   **Then**: Bei „leiser“ gilt die Fenster-Grenze nach der Regel in
    „Lautstärke“ (Baustein 3); eine lautere laufende Wiedergabe wird sanft
    abgesenkt. Bei „stumm“ pausiert die Box und spielt nicht; ein kurzer
    leiser Hinweiston zeigt, dass die Figur erkannt wurde. Nach dem Fenster
    gilt wieder die normale Grenze. Endet ein „stumm“-Fenster, während eine
    Figur liegt, startet nichts von selbst; das Kind muss die Figur erneut
    auflegen. Ohne Netz gilt die letzte Kopie. Ist die Uhrzeit nicht
    vertrauenswürdig, gilt die kleinste „leiser“-Grenze aller Fenster, nie
    stumm (siehe „Uhr und Zeitquelle“).

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
    unbekannte Karte, Aufwachen (Projektplan `docs/plan/`, Abschnitt 5.5.2).
*   **When**: Der Zustand der Box wechselt.
*   **Then**: Der Ring zeigt den passenden Zustand. Die Helligkeit liegt nie
    über 25 %. Am Mac zeigen Terminal und Protokoll denselben Zustand.

### CUJ 19: Tasten und Drehregler

*   **Given**: Eine Serie spielt oder ist pausiert.
*   **When**: Tobias drückt Vor / Zurück, dreht den Drehregler oder drückt den
    Hauptknopf.
*   **Then**: Vor / Zurück springt zur nächsten / vorigen Folge. Der
    Drehregler ändert die Lautstärke innerhalb der wirksamen Grenze (Regel:
    „Lautstärke“ in Baustein 3). Der Hauptknopf kurz: Play / Pause. Ist eine
    Folge zu Ende und liegt die Figur noch auf der Box, spielt ein kurzer Druck
    die nächste Folge (Entscheidung E); ohne Figur auf der Box gilt Play / Pause.
    Lang: Zeiger speichern und herunterfahren.

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
                                             │ Konfiguration,   │   │ Update-Pakete     │
                                             │ Dashboard        │   │ (Boxen: lesen)    │
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
- Build mit **PlatformIO** und der Plattform **pioarduino** (feste
  Release-Version). Grund: Die offizielle PlatformIO-Plattform endet bei
  Arduino-Core 2.0.17, Core 3.x gibt es nur über pioarduino. Feste Versionen
  auch für den Arduino-Core und die PN5180-Bibliothek (per Commit).
- **Board:** ESP32-S3 SuperMini mit 4 MB Flash. In `platformio.ini` stehen
  `board_upload.flash_size = 4MB` und die passende Partitionstabelle; sonst
  droht ein Bootloop.
- **Testumgebung `native`:** Sie baut nur `debounce.cpp` und `protocol.cpp`
  (`build_src_filter`). Beide Dateien nutzen keine Arduino-Typen (kein
  `String`, kein `Arduino.h`). Die Beispielzeilen liegen unter
  `docs/protocol/reader-v1-examples.txt`; der Pfad vom Projektordner
  `firmware/tobibox-reader/` aus ist fest `../../docs/protocol/reader-v1-examples.txt`.
- **USB:** HWCDC (USB-Serial/JTAG) bleibt, weil dort das Flashen mit
  Auto-Reset bequem geht. VID, PID und Produktname sind dabei fest. Der stabile
  Gerätename kommt deshalb von der **Seriennummer des Chips**: am Pi
  `/dev/serial/by-id/…Espressif…<Seriennummer>…` bzw. eine udev-Regel nach
  Seriennummer, am Mac das Suchmuster `/dev/cu.usbmodem*`. Eine eigene
  USB-Kennung (TinyUSB) wird bewusst nicht genutzt: Dort gäbe es kein
  Auto-Reset beim Flashen.
- **Schreiben ohne Blockieren:** HWCDC blockiert beim Schreiben bis 100 ms,
  wenn niemand liest. Die Firmware setzt `setTxTimeoutMs(0)`: Zeilen werden
  verworfen statt zu blockieren (eine Lücke in `seq` zeigt das). Der Box-Dienst
  öffnet die Serielle mit pyserial ohne DTR/RTS (`dsrdtr` und `rtscts` aus,
  DTR/RTS vor dem Öffnen auf „aus“), damit das Öffnen keinen Reset auslöst.
- **Zwei Konfigurationsdateien:** Pins und Tonie-Passwort stehen nur in
  `include/config.h` (gitignored, nie im Repo; im Repo liegt
  `config.example.h`). Die **Zeitkonstanten** stehen in der eingecheckten
  `include/timing.h`, damit Tests und CI ohne `config.h` laufen. Die gebaute
  Firmware-Datei wird nicht veröffentlicht, weil das Passwort aus dem Flash des
  ESP32 ausgelesen werden könnte.
- Aufbau in drei Teile:
  1. **Leser** (Hardware): ein Abfragezyklus liefert genau ein Ergebnis:
     `nichts`, `uid(typ, bytes)`, `gesperrt`, `fehler(code)`. Fehler werden
     **nicht** als „nichts“ gemeldet.
  2. **Entpreller** (reine Logik, ohne Hardware, auf dem Rechner testbar):
     bekommt Ergebnisse mit Zeitstempel, entscheidet `PLACED` / `REMOVED`.
     Seine Zustandstabelle (Zustände, Übergänge, Verhalten bei `fehler(code)`
     mitten in der Entprellung, Verhältnis „gesperrt liegt“ zu „Kennung
     liegt“) steht in `docs/protocol/reader-v1.md`.
  3. **Protokoll-Ausgabe**: schreibt Zeilen, zählt für den Herzschlag.
- **Zeitkonstanten** (alle an einer Stelle, in `timing.h`):
  - Abfragezyklus 200 ms. Die Arbeit pro Zyklus ist laut `docs/plan/uebergabe.md`
    gemessen: NTAG-Karte 176 ms (einschließlich des erfolglosen
    ISO-15693-Versuchs), gesperrter Tonie 137 ms, offener Tonie 58 ms. Die
    Messung in Stufe 1 bestätigt das an Tobias' Figuren.
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
schreibt keine Nutzdaten auf die Figur; das gilt auch für geborgte Figuren. Das
Entsperren hebt den Privacy-Modus auf, **bis eine Toniebox ihn wieder setzt**.
Danach antwortet die Figur wie ein offener Chip; nur das erste Auflegen läuft
über den Entsperrweg. Testfall dafür: „gesperrt → offen“ (gleiche Figur, danach
als Kennung gelesen). Das Entsperren hat das Testprogramm `firmware/tonie_test/`
schon einmal gezeigt.

**Zeitbudget.** Die Grenzen aus Ziel 2 ergeben sich so (Zyklus 200 ms, Messwerte
aus `docs/plan/uebergabe.md`):

| Schritt (Auflegen, NTAG-Karte, schlechtester Fall) | Zeit |
|---|---|
| Warten bis zum Beginn des nächsten Zyklus | ≤ 200 ms |
| Erste Lesung (Arbeit im Zyklus) | ≤ 176 ms |
| Entprellen: zweite Lesung, ein weiterer Zyklus | ≤ 200 ms |
| Übertragung der Zeile | < 10 ms |
| Dienst: Zuordnung, Zeiger laden, Befehl | ≤ 50 ms |
| MPD: Start, `seek` und Ausgabepuffer | ≤ 300 ms |
| **Summe** | **≈ 0,94 s, Grenze 1,0 s** |

- Auflegen (Tonie): gleiche Rechnung mit 137 ms (gesperrt) bzw. 58 ms (offen)
  statt 176 ms; die Entsperrzeit steckt in den 137 ms. Stufe 1 misst sie an
  Tobias' Figuren nach. Ziel 2 gilt erst als erreicht, wenn die gemessene Summe
  unter 1,0 s liegt.
- Abheben: `REMOVED` wird erst am Ende eines Zyklus nach den 1,1 s
  ausgewertet, also bis 1,1 s + 1 Zyklus (0,2 s) = 1,3 s; dazu Übertragung
  (< 10 ms) und Pausenbefehl (< 100 ms) = **ca. 1,41 s**. Grenze: 1,5 s. Die
  Reserve beträgt nur etwa 90 ms.
- Lücken: Lücken bis 1,0 s liegen unter der Schwelle von 1,1 s und führen zu
  keinem `REMOVED`. Im Fehlerfall können einzelne PN5180-Befehle bis 500 ms
  blockieren (`setRF_on`/`setRF_off`); ein solcher Zyklus verlängert die Lücke.
  Die Messung in Stufe 1 prüft, wie oft das vorkommt.
- **Messmethode:** Gemessen wird am **Ausgang** (Mikrofon oder Loopback: vom
  Auflegen bis zum ersten hörbaren Ton), nicht nur über das Ereignisprotokoll;
  das Protokoll misst nur den `play`-Befehl.
- **MPD-Puffer** (feste Startwerte, in beiden MPD-Konfigurationen):
  `audio_buffer_size` 1024 (KiB), `buffer_before_play` 10 %, ALSA-`buffer_time`
  100000 µs. Die Messung justiert sie.

**Rückfallregel.** Überschreitet die Messung (in Stufe 1, am Pi auch unter
Sync-Last) die Grenze von 1,0 s, gilt diese Reihenfolge: erst die **Arbeit pro
Zyklus senken** (das zuletzt gelesene Protokoll, 14443A oder 15693, zuerst
abfragen; kürzere Befehlszeitgrenze für RF-Befehle), dann Rückfrage an Tobias,
ob 1,2 s akzeptabel sind. Ziel 2 wird nicht stillschweigend geändert.

Stufe 1 misst das nach; das Ergebnis steht in `docs/timing.md`. Soll-Werte
für den Pi: siehe Pi-Probelauf.

### Baustein 2 — Protokoll v1 (Vertrag Firmware ↔ Box-Dienst)

Eigenes Dokument `docs/protocol/reader-v1.md` (Stufe 0). Grundzüge:

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
| `ERR code=<wort> detail=<text>` | Fehler; die vollständige Liste der Codes steht in `reader-v1.md` (z. B. `pn5180_no_response`, `unlock_failed`) |

- Felder des Herzschlags: `up` Sekunden seit Start, `present` liegt gerade eine
  Figur, `polls` Abfragezyklen seit Start, `hits` gültige Lesungen, `rejected`
  verworfene Lesungen (verfälscht oder abweichend), `errors` Fehlerzyklen,
  `cycle_ms` Dauer des letzten Zyklus. Genaue Definition: `reader-v1.md`.
- Zum Leser: `PING` (Antwort `HELLO`); weitere Befehle reserviert (siehe „Leser-Rückkanal“ in den Offenen Fragen).
- **Kennung (kanonisch):** Hex, Kleinbuchstaben, MSB zuerst, ohne Trenner.
  ISO 14443 (NTAG): 8, 14 oder 20 Hexzeichen (4, 7 oder 10 Byte). ISO 15693:
  16 Hexzeichen, bei Tonies beginnend mit `e00403`. Diese Schreibweise
  entsteht **nur** in der Firmware; der Box-Dienst prüft sie mit einem
  regulären Ausdruck (steht in `reader-v1.md`) und speichert sie unverändert.
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
| `core` | Zustandsautomat: Ereignisse rein, Befehle raus; hält die vier Teilautomaten (`session`, `learn`, `quiet` + `bedtime`, `idle`) in einer Liste und löst Konflikte nach der Konflikt-Tabelle (siehe „Kern-Zustände“); Schnittstelle: `docs/protocol/core-interface.md` | **nein** (reine Logik, voll testbar) |
| `volume` | Reine Funktion: wirksame Lautstärke-Grenze (siehe „Lautstärke“) | **nein** |
| `pointer` | Reine Funktionen für die Zeigerregeln: nächste Folge, fehlende Folge, Rücksprung 3 s (siehe „Datenmodell und Dateien“) | **nein** |
| `protocol` | Zeilen-Parser nach `reader-v1.md`, prüft das Kennungsformat | **nein** |
| `clock` | Uhr als Eingang des Kerns: Wanduhr und monotone Uhr, Zeitquelle | Systemuhr (im Test: simulierte Uhr) |
| `library` | Serien und Folgen aus dem Medienordner lesen | Dateisystem (lesen) |
| `store` | Zustandsdateien atomar lesen/schreiben | Dateisystem |
| `reader` | Serielle öffnen (pyserial in eigenem Thread, Zeilen über eine Warteschlange an die Ereignisschleife), Zeilen parsen, Neuverbinden, Herzschlag überwachen (Wächter: 5 s ohne `HB`) | Serielle |
| `player` | dünne Schicht über MPD (`mpd.asyncio.MPDClient` aus python-mpd2): Abspielen, Pause, Position, Lautstärke (setzt die wirksame Grenze nur durch); die Player-Ereignisse stehen in `core-interface.md` | MPD |
| `sounds` | kurze Rückmeldetöne über eigenes Kommando (Mac `afplay`, Pi `aplay`) | Prozess |
| `outbox` | Ereignis-Ausgang mit Bestätigung: hält `unknown.json`, gibt Einträge frei, wenn die Bestätigung eintrifft | Dateisystem |
| `ha` | MQTT-Anbindung (paho-mqtt ≥ 2, eigener Thread mit `loop_start`, Übergabe per `call_soon_threadsafe`), HA-Discovery, Zuordnungen empfangen, Status senden, Bestätigungen empfangen | Netz |
| `sync` | rsync vom NAS nach den Regeln, danach MPD-Bibliothek aktualisieren | Prozess, Netz |
| `update`, `selftest` | Update mit Rückfall und eingebaute Prüfroutine (siehe „Update“) | Prozess, Dateisystem |
| `net`, `power` | Netz-Klasse (Heim / Hotspot / offline), Lader, Akkustand, Zeitquelle | System bzw. Simulation |
| `eventlog` | dünne Einrichtung von Python `logging`: JSON-Format; Pi: JSON-Zeilen nach stdout, vom Dienst-Manager in journald übernommen (dauerhaft), Mac: rotierende Datei (Konfiguration) | Dateisystem, journald |
| `cli` | `tobibox status`, `tobibox sim …` (ein eigener Prozess, der Befehle an `sim` schickt) | Unix-Socket (nur `sim`) |
| Hardware-Module: `power` (ab Stufe 3a), `controls` (Tasten, Drehregler), `headphones`, `led` (Stufe 4) | je eine Schnittstelle; **ein** gemeinsamer Simulations-Treiber `sim` liefert alle Eingänge. Er entsteht in Stufe 2 und lauscht auf einem Unix-Socket (`sim.sock` im Zustandsverzeichnis) auf JSON-Zeilen; `tobibox sim …` schreibt dorthin, die Tastatur und das Terminal sind Clients desselben Sockets. Später kommen nur Eingänge dazu. der Ring zeigt seinen Zustand im Terminal und im Protokoll; die echte Hardware ersetzt später nur den Treiber | Treiber (Simulation oder Hardware) |
| `app` | **Einziger Zusammenbau-Punkt:** baut Uhr, Module und Kern, verdrahtet sie, startet und beendet den Dienst | alles (nur hier) |

**Abhängigkeitsrichtung.** Module importieren nur `events` und `core` (und die
reinen Hilfsmodule `volume`, `clock`, `pointer`, `protocol`). Der Kern
importiert keines der Ein-/Ausgabe-Module. Nur `app.py` importiert alle Module
und steckt sie zusammen. Die Uhr wird dem Kern eingespeist, er fragt sie nie
selbst.

**Bibliotheken.** Python ≥ 3.11 (Pi OS Bookworm: 3.11). `tomllib` aus der
Standardbibliothek liest die Konfiguration (kein `tomli`). `python-mpd2` mit
dem asyncio-Client `mpd.asyncio.MPDClient`. `pyserial` läuft in einem eigenen
Thread und reicht Zeilen über eine Warteschlange an die Ereignisschleife.
`paho-mqtt` ab Version 2 (mit `callback_api_version`) läuft mit `loop_start` in
einem eigenen Thread und übergibt per `call_soon_threadsafe`. Alle
Abhängigkeiten sind reines Python (Update-Paket, siehe „Update“).

**Ereignisquellen** (alle als Typen in `events.py`):

| Quelle | Ereignisse (Beispiele) |
|---|---|
| Leser (`reader`) | `PLACED`, `LOCKED`, `REMOVED`, `HELLO`, Wächter-Alarm, Leser-Fehler |
| Player (`player`) | Folge zu Ende, Wiedergabe-Fehler, MPD nicht erreichbar (Felder: `core-interface.md`) |
| HA (`ha`) | neue Konfiguration (Zuordnungen, Leise-Zeiten, Gute-Nacht), Lernmodus starten/abbrechen, Leise-Zeiten, Sync/Update anstoßen |
| Zeitgeber | Takt (mit Zeitstempel), Fristen laufen ab |
| Bedienung (`controls`) | Vor, Zurück, Lautstärke, Hauptknopf kurz/lang |
| Kopfhörer (`headphones`) | Stecker erkannt / gezogen |
| Strom (`power`) | Lader an/aus, Akkustand, Tiefstand, Zeitquelle geändert |
| Netz (`net`) | Netz-Klasse geändert |
| Sync (`sync`) | gestartet, fertig, abgebrochen |
| Update (`update`) | gestartet, Selbsttest bestanden / durchgefallen |

**Der Kern** kennt nur diese Ereignisse und Befehle (Abspielen, Pause, Lautstärke
setzen, Töne, Speichern, Melden, Herunterfahren). Alle Ereignisse und Befehle
mit ihren Feldern stehen als Vertrag in `docs/protocol/core-interface.md`
(Stufe 0); `events.py` setzt sie um und ist ihr einziger Eigentümer, `core.py`
benutzt sie nur.

**Aufrufmuster.** Jeder Teilautomat ist eine reine Funktion
`step(zustand, ereignis, jetzt) → (zustand, befehle)`. Die Zeit `jetzt` kommt als
Parameter (monotone Uhr und Wanduhr); der Kern fragt nie selbst eine Uhr. Zeitgeber
sind Ereignisse (`Takt` mit Zeitstempel). `core` reicht jedes Ereignis an alle
Teilautomaten, sammelt die Befehle und löst Konflikte nach der Konflikt-Tabelle.
Neue Teilautomaten trägt das Integrations-AP der Stufe in die Liste in `core` ein.
`app.py` führt die Befehle aus und speist Ereignisse ein. Die Ereignisse des
Players (Folge zu Ende, Fehler, MPD weg) sind in `core-interface.md` festgelegt,
damit Kern und `player` unabhängig gebaut werden können.

**Ereignis-Ausgang mit Bestätigung.** Meldungen an HA (unbekannte Kennung,
gelernte Figur) gehen über den Befehl `melden`. Das Modul `outbox` hält sie in
`unknown.json`, bis das Ereignis `bestätigt(id, grund)` eintrifft. In Stufe 2 löst
`tobibox sim ack` die Bestätigung aus, ab Stufe 3a kommt sie von HA über MQTT
(Baustein 4). Der Broker allein bestätigt nichts.

**Abspielen mit MPD.** Die MPD-Warteschlange enthält **nur die aktuelle
Folge**. Folgenende heißt: MPD stoppt, der Dienst setzt den Zeiger auf die
nächste Folge (Position 0) und meldet das dem Kern; MPD startet nie von selbst
die nächste Folge. Resume geschieht per `seek` direkt auf die Position (Zeiger
minus 3 s): Es gibt kein kurzes Spielen ab 0:00. Die Latenz dieses Aufrufs misst
Stufe 1.

Die Abläufe (CUJs) werden als **pytest-Tabellen** geschrieben: je CUJ ein
parametrisierter Test mit Zeit, Eingabezeile oder Ereignis und erwarteten
Befehlen. Die Tabellen unter „Kern-Zustände“ sind dafür die Vorlage. Die Tests
laufen ohne MPD und ohne Leser in Millisekunden, am Mac und im Container. Auf
dem Pi laufen sie nicht (kein pytest auf der Box); dort prüft die eingebaute
Prüfroutine die Prüfpunkte des Selbsttests (siehe „Update“). Für Vorführungen ohne
Hardware gibt es `box/tools/fake_reader.py`.

#### Lautstärke

**Eine Regel, ein Ort.** Alle anderen Abschnitte (Ziel 10, CUJ 14, 15, 17, 19,
Baustein 4, D6) verweisen hierher.

- **Wirksame Grenze = Minimum aller aktiven Grenzen.** Aktive Grenzen sind: die
  globale Obergrenze (Konfiguration), die Grenze eines „leiser“-Fensters, die
  Kopfhörer-Grenze (solange ein Stecker steckt) und der aktuelle Wert eines
  Gute-Nacht-Ausblendens. Keine Lautstärke liegt darüber, weder durch den
  Drehregler noch durch die Startlautstärke noch durch ReplayGain.
- **Geklemmt wird an zwei Stellen:** Die Funktion `volume` im Kern berechnet
  die wirksame Grenze; `player` setzt sie nur durch. Das ist die Klemmung im
  Dienst, die **am Mac allein gilt** (MPD kennt keine Maximal- und keine
  Startlautstärke; das ist hier offen so benannt).
- **Harte Kappung am Pi:** ALSA-`softvol` mit `max_dB` in
  `deploy/pi/asound.conf` kappt die Ausgabe hart. Die Startlautstärke setzt ein
  `ExecStartPost` im MPD-Dienst (`deploy/pi/mpd.service.d/startvolume.conf`),
  bevor etwas spielt. So bleibt die Box auch bei einem Absturz oder Neustart
  des Dienstes unter der Grenze.
- **Start:** Der Dienst setzt als Erstes die Lautstärke, bevor etwas spielt.
- **ReplayGain ist begrenzt, nicht garantiert dämpfend:** MPD wendet ReplayGain
  auf das Signal an, nicht über den Mixer-Wert; die Dienst-Grenze sieht es nicht.
  Eingestellt sind `replaygain_preamp` 0, `replaygain_missing_preamp` −6 dB und
  `replaygain_limit` (Peak-Schutz). Ein positiver Gain bleibt möglich, wird
  aber durch den Peak-Schutz und am Pi durch die ALSA-Kappung begrenzt.
- **Kopfhörerwechsel:** zuerst die neue Grenze setzen, dann den Ausgang
  schalten (nie umgekehrt).
- **Test:** pytest für die Funktion `volume` (Minimum gewinnt, nie darüber) und
  für die Klemmung im Dienst (gegen echtes MPD). Für ReplayGain und die
  ALSA-Kappung prüft ein Test die **Konfiguration** (`softvol`-`max_dB`,
  MPD-Zeilen). Ob die Kappung am Ausgang hält, zeigt nur die **Messung am
  Pi** (Pi-Probelauf, Stufe 4 mit Verstärker); sie ist offen (siehe „Offene
  Fragen“).

#### Uhr und Zeitquelle

- Der Kern bekommt die Zeit als Eingang (`clock`). Alle **Dauern** (Fristen,
  Timer, 20 min Leerlauf, 30 s Resume) laufen auf der monotonen Uhr. Die
  Wanduhr braucht nur der Kern der Leise-Zeiten und das Ereignisprotokoll.
- **Zeitquelle:** beim Start die RTC des PiSugar, bei Netz NTP. Ist die Zeit
  nicht vertrauenswürdig (weder RTC noch NTP seit dem Start), gilt die
  **kleinste „leiser“-Grenze aller Fenster, nie stumm** (gibt es kein
  „leiser“-Fenster, gilt die normale Grenze), bis die Zeit stimmt. Die Box meldet
  das an HA und trägt es ins Protokoll (Zeitquelle).
- Am Mac ist die Systemuhr vertrauenswürdig. In Tests ist die Uhr simuliert.

#### Kern-Zustände

Der Kern besteht aus vier Teilautomaten, die einzeln testbar sind. Jede
Tabelle ist die Vorlage für die pytest-Tabelle des Teilautomaten. `core`
verbindet sie; Konflikte zwischen ihnen löst die Konflikt-Tabelle am Ende. Jeder
Teilautomat ist eine Funktion `step(zustand, ereignis, jetzt) → (zustand,
befehle)` (Vertrag: `docs/protocol/core-interface.md`).

**1. Wiedergabe-Sitzung** (`session`)

Zustände: `leer` (nichts liegt, nichts läuft), `spielt`, `pausiert`,
`beendet` (Folge zu Ende, Figur liegt noch), `gehalten` (Figur liegt, wird
wegen „stumm“ nicht gespielt), `unbekannt` (Leser-Zustand unbekannt).

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `leer`, `pausiert` | `PLACED`, Serie bekannt, nicht stumm | Lautstärke setzen, Zeiger laden, Abspielen | `spielt` |
| `leer`, `pausiert` | `PLACED`, Kennung unbekannt | Kennung in `unknown.json`, Überraschungs-Serie abspielen, Ton | `spielt` |
| `leer`, `pausiert` | `LOCKED` | Überraschungs-Serie abspielen | `spielt` |
| `leer`, `pausiert` | `PLACED`, Typ `aktion` | Aktion auslösen (Status: Tonfolge; Gute Nacht: an Ruhe-Regeln) | unverändert |
| `leer`, `pausiert` | `PLACED`, stumm aktiv | leiser Hinweiston, nichts abspielen | `gehalten` |
| `spielt` | `REMOVED` | Pause, Zeiger speichern | `pausiert` |
| `spielt` | `PLACED` andere Kennung | Zeiger der alten Serie speichern, neue Serie wie in den Zeilen oben | `spielt` |
| `spielt` | Folge zu Ende (auch die letzte) | Zeiger auf die nächste Folge, Position 0 (nach der letzten auf Folge 1), speichern, Pause, auch wenn die Figur liegt | `beendet` |
| `beendet` | `REMOVED` | — (die nächste Folge spielt nach erneutem Auflegen) | `pausiert` |
| `beendet` (Figur liegt) | Hauptknopf kurz | Lautstärke setzen, nächste Folge ab Zeiger abspielen (Entscheidung E) | `spielt` |
| `spielt` | Hauptknopf kurz | Pause, Zeiger speichern | `pausiert` |
| `pausiert` (Figur liegt) | Hauptknopf kurz | Abspielen | `spielt` |
| `spielt` | Wächter-Alarm (kein `HB`) | Frist 1,5 s starten | `unbekannt` |
| `unbekannt` | `HELLO` und `PLACED` mit derselben Kennung innerhalb der Frist | nichts, Wiedergabe läuft weiter | `spielt` |
| `unbekannt` | Frist abgelaufen | Pause, Zeiger speichern | `pausiert` |
| `spielt` | stumm beginnt | sanft ausblenden, Pause, Zeiger speichern | `gehalten` |
| `gehalten` | `REMOVED` | — | `pausiert` |
| `gehalten` | stumm endet | nichts; Wiedergabe startet nicht von selbst, erst Abheben und erneutes Auflegen startet sie | `pausiert` |
| `leer` | Start mit liegender Figur (CUJ 20) | wie `PLACED`, sobald alles bereit ist | `spielt` |
| beliebig | Kopfhörer rein/raus | erst Grenze setzen, dann Ausgang umschalten | unverändert |

Kommt nach der Frist dieselbe Kennung wieder, ist das ein normales Auflegen
mit Resume am gespeicherten Zeiger (erste Zeile).

Ohne Figur auf der Box (Zustände `leer`, `pausiert` nach Abheben) behält der
Hauptknopf kurz seine normale Funktion (Play / Pause, CUJ 19). Im Zustand
`beendet` liegt die Figur immer noch auf der Box; deshalb spielt dort der
Hauptknopf die nächste Folge.

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
| beliebig | Zeit nicht vertrauenswürdig | kleinste „leiser“-Grenze aller Fenster, nie stumm, Hinweis an HA | `leiser` (ohne „leiser“-Fenster `normal`) |
| beliebig | Zeit wieder vertrauenswürdig | Wirkung nach Uhrzeit | entsprechend |

Gute Nacht — Zustände: `aus`, `läuft`, `ausblenden`.

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `aus` | Gute-Nacht-Karte aufgelegt | Timer starten (Dauer aus der Konfiguration, Vorschlag 30 min) | `läuft` |
| `läuft` | andere Figur aufgelegt | nichts; der Timer läuft für die neue Figur weiter | `läuft` |
| `läuft` | Timer abgelaufen | Ausblenden starten (Grenze sinkt über die Ausblendzeit, Vorschlag 60 s) | `ausblenden` |
| `ausblenden` | Lautstärke bei null | Pause, Zeiger speichern, Lautstärke zurücksetzen | `aus` |
| `ausblenden` | `REMOVED` | normale Pause (Zeiger gespeichert), Lautstärke zurücksetzen | `aus` |

**4. Strom / Leerlauf** (`idle`, `power`)

Zustände: `aktiv`, `leerlauf` (Zähler für 20 min läuft), `herunterfahren`.

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `aktiv` | keine Wiedergabe und keine Figur | Leerlauf-Zähler starten (monotone Uhr) | `leerlauf` |
| `leerlauf` | Wiedergabe oder Figur | Zähler verwerfen | `aktiv` |
| `leerlauf` | 20 min um, Sync, Update oder Lernmodus läuft (am Lader auch: Sync oder Update noch offen) | warten, Zähler neu; nach Ende des Syncs oder Updates erneut prüfen | `leerlauf` |
| `leerlauf` | 20 min um, nichts läuft | Zeiger speichern, Herunterfahren | `herunterfahren` |
| `aktiv` | Hauptknopf lang | Zeiger speichern, Herunterfahren | `herunterfahren` |
| `aktiv`, `leerlauf` | Akku-Tiefstand (nicht am Lader) | Sync abbrechen, Zeiger speichern, Herunterfahren | `herunterfahren` |
| beim Start | am Lader | prüfen, ob ein Sync ansteht | `aktiv` |

In der Simulation wird „Herunterfahren“ nur protokolliert. Am Lader nachts
wecken (PiSugar-Wecker) ist eine Option für Stufe 4.

**Konflikte → erwartetes Ergebnis.** Jede Zeile ist zugleich ein Abnahmetest
(Stufe 4; Zeilen ohne Stufe-4-Teile laufen schon früher).

| Situation | Erwartetes Ergebnis |
|---|---|
| Folge zu Ende, Figur liegt noch | Zeiger auf die nächste Folge (nach der letzten auf Folge 1), Position 0; die Box pausiert und wartet im Zustand `beendet`. Es passiert nichts, bis die Figur abgehoben und wieder aufgelegt wird (Entscheidung A) oder der Hauptknopf kurz gedrückt wird (Entscheidung E). |
| Hauptknopf kurz, Folge ist zu Ende, Figur liegt noch | Die nächste Folge spielt ab dem Zeiger (Position 0). Ohne Figur auf der Box behält der Hauptknopf seine normale Funktion (Play / Pause). |
| Stumm gegen Lernmodus | Die Box lernt trotzdem, bestätigt mit dem leisen Ton und spielt nicht. |
| Stumm-Fenster beginnt, während eine Figur spielt | Die Wiedergabe blendet sanft aus, pausiert, Zeiger gespeichert (`gehalten`). |
| Stumm-Fenster endet, während eine Figur liegt | Nichts startet von selbst. Erst Abheben und erneutes Auflegen startet die Wiedergabe (Entscheidung B). |
| Gute Nacht läuft, eine andere Figur wird aufgelegt | Der Timer läuft für die neue Figur weiter. |
| Figur wird beim Ausblenden abgehoben | Normale Pause, Zeiger gespeichert, Lautstärke zurückgesetzt, Resume setzt dort wieder an. |
| Figurwechsel während einer Leser-Unterbrechung (`unbekannt`, dann `HELLO` und `PLACED` mit **anderer** Kennung) | Die Frist endet; Zeiger der alten Serie gespeichert, die neue Serie startet wie bei einem normalen Auflegen. |
| Leerlauf-Abschaltung trifft Lernmodus, Sync oder Update | Die Box schaltet nie ab, solange eines davon läuft. |
| Tiefstand während Sync | Der Sync bricht ab, Zeiger gespeichert, die Box fährt herunter. |
| Mehrere Lautstärke-Grenzen gleichzeitig (z. B. Kopfhörer, „leiser“, Ausblenden) | Es gilt das Minimum aller aktiven Grenzen. |

Für nicht vorhergesehene Fälle gilt eine Reihenfolge: Herunterfahren auf
Anforderung (Tiefstand, Hauptknopf lang) und Update-Umschaltung vor stumm, vor
Ende von Gute Nacht, vor Lernmodus, vor Wiedergabe. Die Leerlauf-Abschaltung
ist kein Herunterfahren auf Anforderung: Sie wartet immer, solange Lernmodus,
Sync oder Update laufen.

### Datenmodell und Dateien

Alle Dateien JSON, mit `schema_version`, atomar geschrieben (temporäre Datei →
fsync → umbenennen), beim Start geprüft; bei Fehler Rückfall auf `.bak`.
Beim Update-Rückfall werden die gesicherten Zustandsdateien zurückgespielt;
das ist die Regel für Schema-Änderungen. Hinweis: Schema-Änderungen sollen
möglichst abwärtskompatibel sein.

| Datei | Inhalt | Wer schreibt | Sync |
|---|---|---|---|
| `config.json` | Konfiguration von HA mit **einer** Revision und **einer** Listen-ID: Zuordnungen `uid → Eintrag` (Typ `serie` mit Serien-ID oder Typ `aktion`, z. B. Status oder Gute Nacht), Leise-Zeiten, Gute-Nacht-Einstellungen (Timer-Dauer, Ausblendzeit) | nur aus HA übernommen | holt von HA |
| `resume.json` | je Serie: der Zeiger (aktuelle Folge als Dateiname + Position) + Zähler | Box | nie |
| `unknown.json` | unbekannte Kennungen mit Zeitpunkt, noch nicht von HA bestätigt | Box | an HA; Eintrag erst löschen, wenn HA bestätigt hat (`…/ack`) |

- **Serie** = Ordner im Medienordner; Folgen = Audiodateien darin (D5).
  **Reihenfolge, eine Regel überall:** Sie steht in `serie.json` (Liste
  `folgen`). Nur wenn `serie.json` fehlt, gilt die natürliche Sortierung nach
  Dateiname. Dateien, die im Ordner liegen, aber nicht in der Liste stehen,
  spielt die Box erst, wenn die Integration sie in die Liste eingetragen hat.
- **Serien-ID** — siehe Entscheidung D2. Die Box spielt auch Ordner ohne
  `serie.json`: Ordnername als ID, Reihenfolge nach Dateiname. Tragen zwei
  Ordner dieselbe ID (Ordner samt `serie.json` kopiert), gibt die
  Integration der **jüngeren** Kopie eine neue ID und meldet das. „Jünger“
  heißt: das spätere `angelegt_am` in `serie.json`.
- **Admin-Karten** (Status usw.) sind Einträge in `config.json` mit Typ
  `aktion` statt `serie`. Sie werden in HA wie jede Figur zugeordnet; bis
  Stufe 3a per `tobibox sim`.
- Alle Schemas (vollständig, mit Beispiel-JSON) stehen als Vertrag in
  `docs/data-model.md` (Stufe 0): `config.json`, `resume.json`, `unknown.json`,
  `serie.json`, `manifest.json` und die Zeile des Ereignisprotokolls. Ein AP,
  das ein Schema ändert, ergänzt `docs/data-model.md`.
- **Zeigerregeln (Resume = „nächste ungehörte Folge“):** je Serie ein Zeiger
  (Folge + Position). Ohne gespeicherten Zeiger beginnt die Serie bei Folge 1.
  **Nach jeder Folge pausiert die Box** (Entscheidung A): Folge zu Ende →
  Zeiger auf nächste Folge, Position 0, Pause, auch wenn die Figur noch liegt.
  Letzte Folge zu Ende → Zeiger auf Folge 1, ebenfalls Pause. Die nächste
  Folge spielt erst, wenn die Figur (oder eine andere Figur derselben Serie)
  neu aufgelegt wird oder der Hauptknopf kurz gedrückt wird (Entscheidung E).
  Beim Weiterspielen mitten in einer Folge 3 s Rücksprung (per `seek`, siehe
  „Abspielen mit MPD“). Die Zeigerlogik gehört zu Stufe 1.
- **Zeiger auf eine fehlende Folge** (gelöscht, umbenannt, aus der Liste): Der
  Zeiger geht auf die nächste vorhandene Folge in der Reihenfolge, Position 0,
  und die Box protokolliert das. Ist die Serie leer: Fehlerton.
- Der Zeiger wird nur gespeichert, wenn er sich geändert hat — bei Pause,
  Folgenwechsel, Figurwechsel und höchstens alle 30 s während der Wiedergabe.
- **Schreibbudget:** Bei 2 h Wiedergabe am Tag sind das etwa 240 Schreibvorgänge
  pro Tag und Box für den Zeiger. Das Ereignisprotokoll hat eine feste
  Obergrenze (Pi: journald mit begrenztem Platz; Mac: rotierende Datei,
  Vorschlag 5 Dateien zu je 1 MB). Beide Werte werden im Pi-Probelauf
  geprüft.
- **Überraschungs-Serie** ist eine normale Serie, erkennbar nur an `typ`
  `ueberraschung` in ihrer `serie.json`; eine feste ID gibt es nicht. Gibt es
  keine oder mehr als eine → Fehlerton, Protokolleintrag. Ist sie leer →
  Fehlerton, Protokolleintrag.

### Baustein 4 — Home Assistant: Integration `tobibox`, Seite und MQTT-Schnittstelle

Liegt im Repo unter `homeassistant/custom_components/tobibox/`, wird in HA
als eigene Integration installiert. Sie ist der **einzige Schreiber** für
Zuordnungen und Serien-Metadaten (D1, D2). Die HA-Konfiguration (Dashboard,
Skripte, Automationen) liegt als Dateien im Repo unter `homeassistant/`.

#### Speicher und Medien

- **Speicher:** Die Konfiguration (Zuordnungen, Leise-Zeiten,
  Gute-Nacht-Einstellungen) liegt im HA-Speicher (`.storage/tobibox`), mit
  **einer** Revision und **einer** Listen-ID. **Export** automatisch nach
  jeder Änderung als Datei auf das NAS (`tobibox/export/`). Rückweg bei
  Verlust von HA: HA-Sicherung und NAS-Export; danach „Liste neu ausrollen“.
- **Medien:** Die Medienfreigabe des QNAP ist in HA als Netzwerkspeicher
  eingebunden. Aufbau auf dem NAS: `tobibox/medien/<ordner>/serie.json` +
  Audiodateien, `tobibox/medien/_papierkorb/`, `tobibox/export/`,
  `tobibox/releases/`. HA hat vollen Schreibzugriff auf die Freigabe
  (`medien/`, `export/`, `releases/`); Tobias ist der einzige Benutzer
  (Entscheidung D). Pakete legt Tobias ab.
- **`serie.json`:** `schema_version`, `id` (zufällig, unveränderlich),
  `name` (Anzeige), `angelegt_am`, `folgen` (Reihenfolge als Liste von
  Dateinamen; maßgeblich, Regeln im Datenmodell), `typ` (`normal` oder
  `ueberraschung`; die Überraschungs-Serie wird nur daran erkannt). Geschrieben
  atomar.
- **Erkennen von außen:** Beim Öffnen der Seite und alle 10 min prüft die
  Integration die Freigabe. Neuer Ordner → `serie.json` mit neuer ID und
  Ordnername als Anzeigename. Neue Datei → hinten an die Reihenfolge (erst
  dann spielt die Box sie). Fehlende Datei → aus der Reihenfolge, Hinweis.
  Neue Dateien werden auf Format und Kopierschutz geprüft (D5). Schreiben HA,
  ein PC und der Lautheits-Container (D6) gleichzeitig auf die Freigabe, gibt
  es keine Sperre; das ist als Risiko geführt.
- **Löschen** verschiebt in `_papierkorb/`, nie endgültig sofort. Es gibt
  keine Automatik; Tobias leert den Papierkorb von Hand mit dem Knopf
  „Papierkorb leeren“ auf der Seite. Die Boxen übernehmen `_papierkorb/` nicht.

#### Aktionen und Seite

- **Aktionen** (auch für Automationen): zuordnen (auch Aktionskarten wie
  Status und Gute Nacht), lösen, Lernmodus starten / abbrechen, Serie anlegen /
  umbenennen, Folgen sortieren / löschen, Papierkorb leeren, Sync anstoßen,
  Update anstoßen, Liste neu ausrollen (erzeugt eine neue Listen-ID),
  Leise-Zeiten und Gute-Nacht-Einstellungen einstellen (Stufe 4).
- **Eigene Seite** in der HA-Seitenleiste („Tobi Box“), läuft auch über
  Nabu Casa am Handy:
  - Serienliste mit Anzahl Folgen und zugeordneten Figuren
  - Serie öffnen: Folgen per Ziehen sortieren, löschen, umbenennen,
    Audiodateien vom Handy hochladen
  - „Neue Figuren“: unbekannte Kennungen beider Boxen (gleiche Kennung = ein
    Eintrag), mit einem Tipp einer Serie zuordnen (Weg A); „Jetzt kommt ein
    neuer Tonie“ (Weg B)
  - Aktionskarten (Status, Gute Nacht) einer Kennung zuordnen
  - Box-Status: Version, Netz, Akku, Sync-Stand, letzter Fehler, abgelehnte
    Listen
  - Speicher: freier Platz je Box (die Box meldet ihn mit dem Status, D5);
    Knopf „Papierkorb leeren“
- **Technik der Seite:** ein Web-Baustein (JavaScript-Modul, Lit, ohne
  eigenen Build-Server), Daten über die HA-WebSocket-Schnittstelle mit
  HA-Anmeldung; Hochladen über einen eigenen HA-HTTP-Endpunkt mit Anmeldung,
  der nur Audioformate nach D5 annimmt. Die Seite wird mit `panel_custom`
  registriert, ihre Dateien liefert `async_register_static_paths`; Lit liegt in
  fester Version eingecheckt im Ordner der Seite. Die WebSocket-Befehle (Name,
  Eingabe, Ausgabe) sind ein Vertrag, den die Projektleitung zu Beginn von
  Stufe 3a schreibt (`docs/protocol/ha-websocket-v1.md`), bevor Backend und
  Seite parallel entstehen.
- **Technik der Integration:**
  - `manifest.json` mit `version` und `dependencies` (`mqtt`, `http`,
    `panel_custom`, `websocket_api`).
  - **HA-Version fest** (die laufende stabile Version, Tobias nennt sie). Die
    Tests mit `pytest-homeassistant-custom-component` sind an HA- und
    Python-Version gebunden und laufen deshalb in einer eigenen venv und einem
    eigenen CI-Job.
  - Upload als Strom in Blöcken (`request.multipart()`): HA begrenzt normale
    Anfragen auf 16 MiB, Hörspielfolgen sind größer. Ob Nabu Casa große
    Uploads durchlässt, wird am Handy geprüft (Risiko).
  - Datei-Zugriffe auf die Netzwerkfreigabe über `hass.async_add_executor_job`.
  - `ffprobe` im HA ist eine Annahme (HA OS hat es). Fehlt es, meldet die
    Integration „Prüfung nicht möglich“.

#### MQTT-Schnittstelle Box ↔ HA

- Verbindung per **MQTT** über Tailscale zum Broker in HA (D3), mit **QoS 1**
  und dauerhafter Sitzung; Nachrichten werden idempotent verarbeitet (doppelte
  Zustellung schadet nicht). Jede Box hat ein **eigenes MQTT-Konto** mit
  Themenrechten: Sie liest `tobibox/config` und ihr eigenes `cmd`-Thema und
  schreibt nur ihre eigenen Themen (`event`, Status, Discovery).
- Die Broker-Rechte laufen über das Mosquitto-Add-on: `customize.active: true`,
  eine ACL-Datei `/share/mosquitto/acl.conf` mit `topic readwrite …` je
  Benutzer; `homeassistant` und `addons` bleiben unbeschränkt, die Box-Konten
  sind keine HA-Administratoren (Option `logins`). Beispiele liegen unter
  `homeassistant/mosquitto/`.
- Alle Themen mit Nachrichten (Felder, Beispiele), QoS, „retained“, Ablaufzeit
  der Befehle, Bestätigungen und Discovery-Namen stehen als Vertrag in
  `docs/protocol/mqtt-v1.md` (Stufe 0).
- Themen:
  - `tobibox/config` (dauerhaft/„retained“, ganze Konfiguration:
    Zuordnungen, Leise-Zeiten, Gute-Nacht-Einstellungen, mit einer Revision
    und einer Listen-ID)
    - `tobibox/<box>/event` (gelernt, abgelehnte Liste, Fehler)
  - Unbekannte Kennungen: Die Box veröffentlicht jede Kennung **dauerhaft
    („retained“) auf einem eigenen Thema je Kennung**
    (`tobibox/<box>/unknown/<uid>`). HA bestätigt auf dem Thema `…/ack` (mit
    Grund); **erst dann** löscht die Box den Eintrag in `unknown.json` und die
    dauerhafte Nachricht. Die Bestätigung des Brokers (PUBACK) reicht nicht:
    Sie sagt nicht, dass HA die Figur hat, etwa wenn HA gerade neu startet
  - `tobibox/<box>/cmd` (Lernmodus, Sync, Update): geht an genau eine Box,
    ist **nicht** dauerhaft und trägt eine Ablaufzeit; ein abgelaufener Befehl
    wird ignoriert (Tabelle „Lernmodus“ in den Kern-Zuständen).
- Box meldet sich per **MQTT-Discovery** an: Sensoren (Zustand, läuft
  gerade, Akku, Lader, Netz, Sync-Stand, freier Speicherplatz, Version,
  letzter Fehler, Zeitquelle), Knöpfe (Sync jetzt, Update, Lernmodus
  abbrechen), Auswahl (Serie für Lernmodus).
- **Revisionsregel** (Revision = Versionsnummer der Konfiguration; die
  Listen-ID kennzeichnet den HA-Speicher, siehe Begriffe). Die Box übernimmt
  eine Konfigurations-Nachricht,
  - wenn ihre **Listen-ID neu** ist (unabhängig von der Revision), oder
  - wenn die Listen-ID gleich ist und die Revision **höher** ist als die
    gespeicherte.

  Alles andere wird nicht übernommen und als „abgelehnte Liste“ an HA
  gemeldet. Die HA-Aktion „Liste neu ausrollen“ erzeugt eine neue Listen-ID und
  wird deshalb von allen Boxen übernommen. Hat der Broker nichts, behält die
  Box ihre letzte Kopie. Damit blockiert eine HA-Wiederherstellung mit
  niedriger Revision die Boxen nicht dauerhaft.

### Netz, Sync, Strom

- **Netz-Klasse** (Pi: NetworkManager-SSID; Mac: Simulation):
  `home` (Heim-SSID **und** NAS über Tailscale erreichbar), `hotspot`
  (Hotspot-SSID), `offline`.
- **Medien-Sync** mit rsync über Tailscale zu einem **rsync-Daemon auf dem
  QNAP** (Modul `medien`, `read only = yes`; QNAP-SSH-Konten sind nur für
  Admins, deshalb kein SSH). Der Sync startet auf einen Takt im Dienst
  (Intervall in `tobibox.toml`, Vorschlag 1 h) und auf den HA-Knopf, jeweils
  nur wenn die Netz-Regel es erlaubt:
  - `home`: immer erlaubt.
  - `hotspot`: erlaubt, wenn Lader dran oder Akku > 50 %.
  - Dateien landen erst nach vollständiger Übertragung sichtbar im
    Medienordner: `--partial-dir` mit **absolutem Pfad außerhalb des
    Medienordners, aber auf demselben Dateisystem**
    (`/var/lib/tobibox/.rsync-partial`) und `--delay-updates`. So indexiert MPD
    keine halben Dateien.
  - **Spiegelnd mit `--delete`, mit Schutz:** Der Sync bricht ab, wenn die
    Quelle fehlt, leer ist oder mehr als 20 % der vorhandenen Dateien löschen
    würde. Die 20-%-Grenze wird vorab mit `--dry-run --itemize-changes` gezählt
    (Zeilen `*deleting` gegen die Zahl der vorhandenen Dateien). Vorab prüft er
    den freien Platz; reicht er nicht, startet er nicht
    und meldet das an HA.
  - Danach MPD-Bibliothek aktualisieren, nicht beim Start.
  - Nie parallel zum Update. Während eines Syncs schaltet die Box nicht ab
    (Tabelle „Strom / Leerlauf“).
  - Eine Datei, die gerade spielt, wird nie ersetzt: Der Dienst fragt MPD
    (`currentsong`) und übergibt die Datei per `--exclude` (das schützt auch
    vor `--delete`); ihre Änderung wartet auf den nächsten Abgleich.
  - rsync läuft mit niedriger CPU- und IO-Priorität (`nice`/`ionice`).
    - Die Latenz beim Auflegen während eines Syncs lässt sich nur am Pi unter
    echter Last messen. Im Container prüft ein Test nur, dass Kern-Ereignisse
    während des Syncs weiterlaufen.
  - Die Hotspot-/Akku-Regel lässt sich bis PiSugar und Tailscale vorhanden
    sind nur mit Simulation prüfen (siehe Risiken).
  - Im Hotspot gibt es **keine Datenbegrenzung** je Sync (Entscheidung C);
    es gilt nur die Akku-Regel.
- **Strom:** Schnittstelle und Simulation komplett ab Stufe 3a (AP 3.3). Im
  Prototyp Simulation über den gemeinsamen Treiber (`sim`, ab Stufe 2) (`tobibox sim power
  --charger on --battery 40`); die echte PiSugar-Anbindung ersetzt nur den
  Treiber. Abschalt- und Lader-Regeln: CUJ 16 und Tabelle „Strom / Leerlauf“.
- **Uhr:** siehe „Uhr und Zeitquelle“ in Baustein 3.

### Update

- **Auslöser:** HA-Knopf.
- **Bedingungen:** Box daheim (`home`), am Lader, spielt nicht, kein Sync.
- **Paket:** Tarball `tobibox-<version>.tar.gz` mit Code, den **fertig
  gebauten** Python-Abhängigkeiten und `manifest.json`, dazu eine
  **Signatur**. Die Abhängigkeiten werden beim Bauen mit `pip install --target`
  in einen Ordner im Paket gelegt; der Dienst startet mit `PYTHONPATH` auf
  diesen Ordner (kein venv, es ist nicht verschiebbar). Auf dem Pi wird nichts
  gebaut oder per pip geholt. Die Abhängigkeiten sind reines Python; AP 3.8
  prüft das (keine `.so`/`.dylib`, nur Pakete ohne Plattform-Kennzeichen). Die
  Python-Minor-Version beim Bauen ist die des Pi OS Bookworm (3.11). Das Paket
  liegt auf dem NAS in `tobibox/releases/`; HA darf dort schreiben
  (Entscheidung D).
- **Manifest** (Schema in `docs/data-model.md`): `schema_version`, `version`,
  `protokoll_version`, `schema_versionen` (je Zustandsdatei), `firmware_min`,
  `python` und `erstellt_am`.
- **Signatur** mit dem Standardwerkzeug `minisign` (kein eigener Code): Den
  Signierschlüssel hat nur Tobias, auf seinem Mac (nicht im Repo, nicht auf NAS
  oder HA); er signiert beim Bauen des Pakets. Der Prüfschlüssel liegt auf der
  Box (mit dem SD-Image). **Zweck:** Weil HA auf `releases/` schreiben darf,
  verhindert nur die Signatur, dass ein manipuliertes HA oder NAS (oder Netz)
  Code auf die Boxen bringt. Ohne gültige Signatur bricht die Box das Update
  ab und meldet das an HA. Die Tests erzeugen ihr eigenes Test-Schlüsselpaar
  zur Laufzeit; im Repo liegt kein Schlüssel. Die CI installiert `minisign`.
- **Ablauf:** HA-Knopf → Box prüft Bedingungen → lädt Paket → prüft Signatur →
  entpackt nach `releases/<version>/` → sichert die Zustandsdateien → schreibt
  Zustand `testing` und Zähler 0 → stellt den Verweis `current` **atomar** um
  (neuen Verweis anlegen, dann auf `current` umbenennen) → startet neu. Der
  Zustand (`testing`, `ok`, `failed`) steht in einer Zustandsdatei
  (`update.json` im Zustandsverzeichnis).
- **Selbsttest** als **eingebaute Prüfroutine** der Box (kein pytest auf der
  Box): Dienst läuft, Leser meldet `HELLO` mit passender Protokoll-Version,
  Zustandsdateien lesbar, MPD antwortet, Testton spielt. Auf Aufbauten ohne
  Leser steht der Prüfpunkt „Leser“ in der Konfiguration auf Simulation. Dann
  Zustand `ok`.
- **Rückfall** mit einem kleinen Wächter-Skript und systemd-Mitteln. Das
  Skript muss **außerhalb** der Version liegen, die ausfallen kann; sonst
  zählt bei einem Importfehler der neuen Version nichts.
  1. **`/opt/tobibox/bin/guard.py`** (Quelle im Repo: `deploy/pi/guard.py`)
     kommt mit dem SD-Image, wird nie per Update ersetzt und nutzt nur die
     Standardbibliothek. Es läuft als `ExecStartPre=` vor jedem Start.
  2. Es zählt Starts **nur im Zustand `testing`**; Neustarts im Zustand `ok`
     (Leerlauf-Abschaltung, leerer Akku) zählen nicht. Bei Zähler ≥ 3 stellt es
     den Verweis `current` auf die vorige Version zurück, **spielt die
     gesicherten Zustandsdateien zurück** (das ist die Regel für
     Schema-Änderungen), setzt `failed` und meldet den Grund an HA.
  3. **Selbsttest-Frist 5 min:** `Type=notify` und `TimeoutStartSec=300`. Im
     Zustand `testing` meldet der Dienst `READY=1` erst nach bestandenem
     Selbsttest; sonst beendet systemd ihn nach 5 min, und der Neustart zählt.
  4. **Werte in `tobiboxd.service`:** `Restart=on-failure`, `RestartSec=3`,
     `StartLimitIntervalSec=120`, `StartLimitBurst=5`,
     `OnFailure=tobiboxd-failed.service`. Diese Unit ruft `guard.py --failed`
     auf: Im Zustand `testing` erzwingt es den Rückfall und startet neu.
  5. Die Entscheidung „bleiben oder zurück“ ist eine kleine Funktion in
     `guard.py` (Eingaben: Zustand, Zähler). Sie hat einen eigenen Test.
- Firmware-Updates des ESP32 sind **nicht** Teil des Pakets (Flashen per
  USB am Mac); das Paket nennt nur die Mindestversion.

### Fehlersuche

- **Ereignisprotokoll**: Python `logging` mit JSON-Formatter, **ein
  Protokollweg je Gerät**: am Pi JSON-Zeilen nach stdout, die der Dienst-Manager in journald übernimmt
  (dauerhaft, begrenzter Platz, `SyncIntervalSec=30s`; bei Stromausfall gehen
  höchstens etwa 30 s Protokoll verloren),
  am Mac eine rotierende Datei mit fester Obergrenze (Konfiguration). Es gibt
  keine Protokolldatei auf dem Pi.
  Eine JSON-Zeile je Ereignis mit Zeit, Zeitquelle, Baustein, Ereignis,
  Ergebnis; die Vorgangs-ID (je `PLACED`/`LOCKED`, siehe Begriffe) ist ein
  Log-Feld. Die **Zeitquelle** sagt, woher die Uhrzeit stammt (Systemuhr, RTC
  oder NTP). So erkennt man falsche Zeiten nach einem Stromausfall.
  Simulierte Ereignisse tragen `sim=true`. Keine Geheimnisse.
- **`tobibox status`** (SSH, ab Stufe 1/2): Prüfpunkte (Leser, Medien, Netz,
  Speicher, HA) ausführlich, letzte Fehler, Versionen, Sync-Stand. In Stufe 3a
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
| Leser | Suchmuster `/dev/cu.usbmodem*` | `/dev/serial/by-id/…Espressif…<Seriennummer>…` bzw. udev-Regel nach Seriennummer |
| MPD | Homebrew, Ausgabe CoreAudio | Paket aus Pi OS, Ausgabe ALSA (I²S) |
| Lautstärke-Grenze | nur Klemmung im Dienst | Klemmung im Dienst plus ALSA-`softvol` mit `max_dB` |
| Python | ≥ 3.11 | 3.11 (Pi OS Bookworm), Abhängigkeiten per `pip install --target` im Paket |
| Töne | `afplay` | `aplay` |
| Netz, Strom | Simulation | NetworkManager, PiSugar |
| Uhr | Systemuhr | PiSugar-RTC beim Start, NTP bei Netz |
| LED-Ring, Tasten, Kopfhörer | Simulation (ein gemeinsamer Treiber: Tastatur; Ring-Zustand im Terminal und im Protokoll) | echte Treiber (später) |
| Start | `tobiboxd` im Terminal | systemd-Dienst |
| Pfade | `~/tobibox/…` | `/var/lib/tobibox`, `/opt/tobibox`, Wächter `/opt/tobibox/bin/guard.py` |

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
unveränderlicher ID.

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
  Modell (in Klammern, siehe „Begriffe“). Danach prüft ein **frischer Agent**
  (Goldfisch, Sonnet) den Code gegen dieses Dokument, bevor das AP als fertig
  gilt.
- **Form der APs:** Jedes AP ist eine Überschrift `#### AP x.y <Name> (<Modell>)`,
  darunter eine Zeile „Ergebnis:“, eine Dateitabelle und die Abnahme als Liste.
  Die Tabellen nennen konkrete Dateinamen (keine Ordner oder Platzhalter). Ein
  AP legt keine Datei außerhalb seiner Tabelle an.
- Jedes AP liefert Tests, die im Container ohne Hardware laufen
  (Firmware-Logik: PlatformIO `native`; Box-Dienst: pytest; MPD-Tests mit
  echtem MPD im Container). Auf der Box selbst läuft kein pytest; dort
  prüft die eingebaute Prüfroutine (siehe Abschnitt „Update“). Testdateien
  (Audio, Serienordner) erzeugen die Tests selbst; die Erzeuger liegen unter
  `box/tests/fixtures/`.
- Kein AP ändert die Verträge aus Stufe 0 eigenmächtig; Änderungswünsche
  gehen an die Projektleitung.
- Jedes AP, das ein Schema einführt oder ändert, ergänzt `docs/data-model.md`
  um dieses Schema und beachtet die Regeln aus Stufe 0 (atomar schreiben,
  `.bak`, `schema_version`, Migration).
- Keine Funktion wartet auf Hardware: Fehlende Hardware wird mit einer
  Simulation am Mac gebaut (Stufe 4).
- Abhängigkeitsregel: Module importieren nur `events` und `core`. Nur `app.py`
  importiert alle Module (Baustein 3).
- **Parallele APs und gemeinsame Dateien:** `core.py`, `session.py`, `app.py`,
  `cli.py` und `sim.py` ändert in jeder Stufe nur das **Integrations-AP** der
  Stufe. Parallele APs liefern ihren Teilautomaten oder ihr Modul als eigene
  Datei mit Unit-Tests, ohne diese Dateien anzufassen. Das Integrations-AP
  hängt alles in `core`, `app`, `cli` und `sim` ein und schreibt die
  CUJ-Tests der Stufe.
- Kein Geheimnis im Repo: `config.h`, `tobibox.toml` mit Zugangsdaten,
  Tailscale-Schlüssel, MQTT-Passwörter und der Signierschlüssel sind
  gitignored bzw. liegen nicht im Repo; im Repo liegen nur `*.example.*`.
- Jede Stufe hat eine Tabelle „Von Tobias bereitzustellen“. Die Projektleitung
  prüft vor dem Start der Stufe, dass alles da ist.

### Stufe 0 — Verträge (Projektleitung schreibt, Goldfisch prüft, Tobias gibt frei)

Die Projektleitung schreibt diese Dokumente; ein Goldfisch prüft sie vor
Stufe 1, Tobias gibt sie frei.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `docs/protocol/reader-v1.md` | neu | Protokoll v1 vollständig: Zeilen und Felder, **Felder des Herzschlags** (Bedeutung jedes Zählers), **Kennungsformat mit regulärem Ausdruck** (ISO 14443: 8, 14 oder 20 Hexzeichen; ISO 15693: 16 Hexzeichen), Zeitkonstanten, **vollständige Fehlercodes**, **Zustandstabelle des Entprellers** (auch `fehler(code)` mitten in der Entprellung, „gesperrt liegt“ gegen „Kennung liegt“), Verhalten bei unbekannten Zeilen. Einziger Vertrag zwischen Firmware und Box-Dienst. |
| `docs/protocol/reader-v1-examples.txt` | neu | Gültige und ungültige Beispielzeilen mit erwarteter Auslegung; Testgrundlage für beide Seiten. |
| `docs/protocol/core-interface.md` | neu | Alle Ereignisse und Befehle des Kerns mit Feldern; die Signatur `step(zustand, ereignis, jetzt) → (zustand, befehle)` je Teilautomat; Uhr als Parameter; Player-Ereignisse (Folge zu Ende, Fehler, MPD weg); Ereignis-Ausgang mit Bestätigung; wie ein Teilautomat in `core` eingehängt wird. |
| `docs/data-model.md` | neu | Vollständige Schemas mit Beispiel-JSON für `config.json` (mit Aktionskarten, Leise-Zeiten, Gute Nacht), `resume.json`, `unknown.json`, `serie.json`, `manifest.json` und die Zeile des Ereignisprotokolls; dazu die Regeln: atomar schreiben, `.bak`, `schema_version`, Migration. |
| `docs/protocol/mqtt-v1.md` | neu | Themen, Nachrichten (Felder, Beispiele), QoS, „retained“, Ablaufzeit von Befehlen, Bestätigung `…/ack` mit Grund, Discovery-Namen. |

Der WebSocket-Vertrag zwischen HA-Backend und Seite (`docs/protocol/ha-websocket-v1.md`)
wird zu Beginn von Stufe 3a geschrieben, nicht hier.

**Von Tobias bereitzustellen:** nur die Freigabe.

Abnahme Stufe 0:

- Ein Goldfisch-Review der fünf Dateien hat keinen offenen Blocker.
- Tobias gibt die Dateien frei.

### Stufe 1 — Leser und Abspielen (CUJ 1, 2, 5, 6, 8, 13)

**Von Tobias bereitzustellen**

| Was | Wofür | Frist |
|---|---|---|
| ESP32-S3 SuperMini mit PN5180, verdrahtet nach den Pins in `config.h` | AP 1.1 gegen Hardware, Abnahme | vor Abnahme Stufe 1 |
| Echte `config.h` mit dem Tonie-Passwort, nur lokal auf dem Mac, nie im Repo | Firmware bauen und flashen | vor Abnahme Stufe 1 |
| Mac mit Homebrew-MPD | AP 1.3, 1.4, Abnahme | vor AP 1.3 |
| Figuren zum Testen (Tonies, darunter ein gesperrter, und NFC-Karten) | Abnahme, Messung | vor Abnahme Stufe 1 |
| Mikrofon (das im Mac reicht) | Messung am Ausgang (AP 1.6) | vor AP 1.6 |
| Einige Test-Audiodateien (optional) | Hörprobe; die Tests erzeugen eigene | optional |

**Reihenfolge:** AP 1.1 läuft parallel zu allem. Danach AP 1.2a, dann AP 1.2b;
AP 1.3, 1.4 und 1.5 laufen parallel; AP 1.6 am Schluss.

#### AP 1.1 Firmware `tobibox-reader` (Sonnet)

Ergebnis: Eine Firmware, die Protokoll v1 ausgibt; die nativen Tests laufen; der
Build für `esp32s3` gelingt.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `firmware/tobibox-reader/platformio.ini` | neu | Umgebungen `esp32s3` (SuperMini, HWCDC) und `native`. pioarduino-Plattform mit fester Release-Version, Arduino-Core und PN5180-Bibliothek per fester Version/Commit; `board_upload.flash_size = 4MB` und Partitionstabelle; `native` mit `build_src_filter` nur auf `debounce.cpp` und `protocol.cpp`. |
| `firmware/tobibox-reader/include/config.example.h` | neu | Pins (aus `tonie_test/config.h`) und Passwort-Platzhalter. Keine Zeitkonstanten. |
| `firmware/tobibox-reader/include/timing.h` | neu | Alle Zeitkonstanten (Zyklus, Anzahl gleicher Lesungen, Abhebe-Zeit 1,1 s); eingecheckt. |
| `firmware/tobibox-reader/src/main.cpp` | neu | Zusammenbau: Leser → Entpreller → Protokoll; Herzschlag; `setTxTimeoutMs(0)`. |
| `firmware/tobibox-reader/src/reader.h` | neu | Schnittstelle des Lesers: Ergebnis `nichts`/`uid`/`gesperrt`/`fehler`. |
| `firmware/tobibox-reader/src/reader.cpp` | neu | Ein Abfragezyklus 14443A/15693/Entsperren nach Vorbild `tonie_test`. |
| `firmware/tobibox-reader/src/debounce.h` | neu | Schnittstelle des Entprellers, ohne Arduino-Typen. |
| `firmware/tobibox-reader/src/debounce.cpp` | neu | Zustandsautomat nach der Tabelle in `reader-v1.md`, ohne Hardware-Aufrufe (Zeit wird übergeben). |
| `firmware/tobibox-reader/src/protocol.h` | neu | Schnittstelle der Protokoll-Ausgabe, ohne Arduino-Typen. |
| `firmware/tobibox-reader/src/protocol.cpp` | neu | Formatiert Zeilen nach `reader-v1.md`, zählt `seq` und die Herzschlag-Zähler. |
| `firmware/tobibox-reader/test/test_debounce/test_debounce.cpp` | neu | Native Tests: 2-gleich-Regel, 1,0-s-Lücke, 1,1-s-Abheben, Figurwechsel, verfälschte Kennung am Rand, gesperrter Tonie, „gesperrt → offen“, `fehler(code)` mitten in der Entprellung. |
| `firmware/tobibox-reader/test/test_protocol/test_protocol.cpp` | neu | Native Tests gegen `../../docs/protocol/reader-v1-examples.txt`. |
| `firmware/tobibox-reader/README.md` | neu | Bauen, Flashen am Mac, Passwort eintragen, serielle Ausgabe ansehen. |
| `firmware/tonie_test/` | bleibt | Referenz, unverändert. |

Abnahme AP 1.1:

- Alle nativen Tests sind grün.
- `pio run -e esp32s3` baut mit dem Platzhalter-Passwort.
- `debounce.cpp` und `protocol.cpp` enthalten keinen Arduino-Typ.

#### AP 1.2a Box-Dienst: Kern, Protokoll, Leser (Sonnet)

Ergebnis: Kern und Teilautomat Sitzung nach `core-interface.md`, Zeilen-Parser
und Leser mit Wächter; alles ohne MPD und ohne Hardware testbar.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/pyproject.toml` | neu | Paket `tobibox`, Python ≥ 3.11, feste Abhängigkeiten (pyserial, python-mpd2, paho-mqtt ≥ 2), Test-Abhängigkeiten (pytest, pytest-asyncio), Einstiegspunkte `tobiboxd`, `tobibox`. |
| `box/src/tobibox/__init__.py` | neu | Paket-Kennung, Version. |
| `box/src/tobibox/events.py` | neu | Ereignis- und Befehls-Typen genau nach `core-interface.md`; einziger Eigentümer dieser Typen. |
| `box/src/tobibox/core.py` | neu | Hält die Liste der Teilautomaten (zunächst nur `session`), reicht Ereignisse weiter, sammelt Befehle, löst Konflikte nach der Konflikt-Tabelle. Reine Logik. |
| `box/src/tobibox/session.py` | neu | Teilautomat Wiedergabe-Sitzung: alle Zeilen der Tabelle „Wiedergabe-Sitzung“, auch Folge zu Ende (`beendet`), Hauptknopf kurz (Entscheidung E) und Leser-Zustand unbekannt. |
| `box/src/tobibox/volume.py` | neu | Reine Funktion: wirksame Grenze = Minimum einer **Liste benannter Grenzen**. Stufe 1 liefert globale Obergrenze und Startlautstärke; weitere Grenzen kommen in Stufe 4 ohne Änderung dieser Datei. |
| `box/src/tobibox/clock.py` | neu | Uhr als Eingang: Wanduhr, monotone Uhr, Zeitquelle; im Test simulierte Uhr. |
| `box/src/tobibox/protocol.py` | neu | Zeilen-Parser nach `reader-v1.md`, prüft das Kennungsformat. |
| `box/src/tobibox/reader.py` | neu | Serielle öffnen (pyserial in eigenem Thread mit Warteschlange, ohne DTR/RTS; Mac-Suchmuster `/dev/cu.usbmodem*`), Zeilen lesen, `HELLO`-Prüfung (setzt `seq` zurück), Herzschlag-Wächter (5 s ohne `HB`), selbst neu verbinden. |
| `box/tests/conftest.py` | neu | Simulierte Uhr, Hilfen zum Bauen von Ereignisfolgen. |
| `box/tests/unit/test_protocol.py` | neu | Parser gegen `docs/protocol/reader-v1-examples.txt`. |
| `box/tests/unit/test_volume.py` | neu | Minimum gewinnt, nie darüber. |
| `box/tests/unit/test_session.py` | neu | Jede Zeile der Tabelle „Wiedergabe-Sitzung“ als parametrisierter Test. |
| `box/tests/unit/test_core.py` | neu | Ereignisse laufen durch alle Teilautomaten; Konflikt-Tabelle. |
| `box/tests/unit/test_clock.py` | neu | Monotone und Wanduhr, Zeitquelle. |
| `box/tests/integration/test_reader_pty.py` | neu | Leser über Pseudo-Terminal: Trennung, Müllzeilen, Neustart des ESP32 (`HELLO`, `seq` bei 0), Wächter-Alarm. |

Abnahme AP 1.2a:

- Alle Unit-Tests und `test_reader_pty.py` sind grün, ohne MPD.
- `core.py` und `session.py` importieren kein Ein-/Ausgabe-Modul.
- Jede Zeile der Tabelle „Wiedergabe-Sitzung“ hat einen Testfall.

#### AP 1.2b Box-Dienst: Speicher, Bibliothek, Zeiger, Konfiguration, Protokoll, CLI (Sonnet)

Ergebnis: Zustandsdateien, Serien aus dem Medienordner, die vollständige
Zeigerlogik (Laden, Speichern, 3 s Rücksprung, Pause nach jeder Folge),
Konfiguration, Ereignisprotokoll und die erste Fassung der CLI. Läuft nach AP 1.2a.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/store.py` | neu | Atomares Lesen/Schreiben, `.bak`, `schema_version`; `resume.json` laden und speichern, nur bei Änderung und höchstens alle 30 s während der Wiedergabe. |
| `box/src/tobibox/library.py` | neu | Serien aus `serie.json` lesen; Folgen-Reihenfolge nach der Regel im Datenmodell; Überraschungs-Serie (nur über `typ`); Dateien außerhalb der Liste nicht spielen. |
| `box/src/tobibox/pointer.py` | neu | Reine Zeigerregeln: nächste Folge, nach der letzten Folge 1, fehlende Folge → nächste vorhandene, 3 s Rücksprung. |
| `box/src/tobibox/config.py` | neu | `tobibox.toml` laden und prüfen (`tomllib`), inkl. globaler Lautstärke-Obergrenze und Startlautstärke. |
| `box/src/tobibox/eventlog.py` | neu | Python `logging` mit JSON-Formatter; Pi: JSON-Zeilen nach stdout; Mac: `RotatingFileHandler` mit fester Obergrenze; Vorgangs-ID als Log-Feld. |
| `box/src/tobibox/cli.py` | neu | Erste Fassung von `tobibox status` (Leser, letzte Fehler, Versionen). |
| `box/src/tobibox/session.py` | änd. | Zeigerlogik anschließen: Zeiger laden beim Auflegen, speichern bei Abheben, Folgenende, Figurwechsel. |
| `box/src/tobibox/core.py` | änd. | Befehl „Speichern“ und Zeiger-Eingang verdrahten. |
| `box/tools/fake_reader.py` | neu | Gibt Protokollzeilen auf ein Pseudo-Terminal aus; Vorführen und Testen ohne Hardware. |
| `box/tests/fixtures/__init__.py` | neu | Paket für die Test-Erzeuger. |
| `box/tests/fixtures/audio.py` | neu | Erzeugt kurze WAV-Töne und Serienordner mit `serie.json` im Test-Verzeichnis (kein eingechecktes Audio). |
| `box/tests/unit/test_store.py` | neu | Atomares Schreiben, `.bak`-Rückfall, beschädigte Datei beim Start. |
| `box/tests/unit/test_store_powerloss.py` | neu | Stromausfall-Test: Prozess hart beenden während des Schreibens; danach ist die Datei lesbar. |
| `box/tests/unit/test_library.py` | neu | Reihenfolge, Ordner ohne `serie.json`, doppelte IDs, Überraschungs-Serie (keine oder mehr als eine, leer). |
| `box/tests/unit/test_pointer.py` | neu | Alle Zeigerregeln, darunter „Zeiger auf gelöschte oder umbenannte Folge“ und „Folge zu Ende bei liegender Figur: Pause, Zeiger auf die nächste Folge, nach der letzten auf Folge 1“. |
| `box/tests/unit/test_config.py` | neu | Konfiguration laden und prüfen. |
| `box/tests/unit/test_eventlog.py` | neu | JSON-Zeile mit allen Pflichtfeldern, Vorgangs-ID. |

Abnahme AP 1.2b:

- Alle genannten Tests sind grün.
- Der Stromausfall-Test lässt nie eine unlesbare Zustandsdatei zurück.
- Der Zeiger wird nur bei Änderung und höchstens alle 30 s geschrieben.

#### AP 1.3 Player und Töne (Sonnet)

Ergebnis: Der Dienst spielt über MPD und lässt sich mit Leser (oder
`fake_reader`) vollständig starten.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/player.py` | neu | Dünne MPD-Schicht über `mpd.asyncio.MPDClient`: Warteschlange nur mit der aktuellen Folge, Abspielen, Pause, Resume per `seek` auf Position, Lautstärke, Ereignis „Folge zu Ende“ (MPD stoppt) nach `core-interface.md`. Setzt die wirksame Grenze aus `volume.py` nur durch und setzt beim Start **zuerst** die Lautstärke. |
| `box/src/tobibox/sounds.py` | neu | Kurze Töne über konfigurierbares Kommando (Mac `afplay`, Pi `aplay`). |
| `box/src/tobibox/notify.py` | neu | `READY=1` über `NOTIFY_SOCKET` senden (reines Python, ohne `python-systemd`); am Mac ohne Wirkung. |
| `box/src/tobibox/app.py` | neu | **Einziger Zusammenbau-Punkt:** baut Uhr und Module, verdrahtet reader → core → player, Zeitgeber (`Takt`), meldet `READY=1`, beendet sauber. |
| `box/src/tobibox/__main__.py` | neu | Einstieg `python -m tobibox` bzw. `tobiboxd`. |
| `box/tools/make_sounds.py` | neu | Erzeugt die Platzhalter-Töne reproduzierbar. |
| `box/sounds/start.wav` | neu | Platzhalter-Ton: Start. |
| `box/sounds/unbekannt.wav` | neu | Platzhalter-Ton: unbekannte Figur. |
| `box/sounds/fehler.wav` | neu | Platzhalter-Ton: Fehler. |
| `box/sounds/hinweis.wav` | neu | Leiser Hinweiston (Figur erkannt bei „stumm“). |
| `box/sounds/lernen_beginn.wav` | neu | Platzhalter-Ton: Lernmodus beginnt. |
| `box/sounds/lernen_ende.wav` | neu | Platzhalter-Ton: Lernmodus endet. |
| `box/sounds/akku_leer.wav` | neu | Platzhalter-Ton: Akku fast leer. |
| `box/tests/fixtures/mpd.test.conf` | neu | MPD-Konfiguration nur für Tests: eigener Port und eigenes Verzeichnis, Null-Ausgabe. |
| `box/tests/integration/conftest.py` | neu | Startet und beendet ein MPD mit `mpd.test.conf`; nutzt `fixtures/audio.py`. |
| `box/tests/integration/test_player_mpd.py` | neu | Gegen echtes MPD: Start, Pause, Position, Resume per `seek`, Folgenende (MPD stoppt, nichts spielt weiter), Lautstärke nie über der Grenze (auch nach Neustart des Dienstes; das ist die Klemmung im Dienst, die harte Kappung folgt im Pi-Probelauf). |
| `box/tests/unit/test_sounds.py` | neu | Kommando wird korrekt zusammengesetzt; kein Aufruf ohne Datei. |

Abnahme AP 1.3:

- `test_player_mpd.py` ist grün im Container mit echtem MPD.
- Der Dienst setzt vor dem ersten Abspielen die Lautstärke.
- Nach dem Ende einer Folge spielt MPD nicht von selbst weiter.

#### AP 1.4 Mac-Einrichtung und Doku (Haiku)

Ergebnis: Tobias kann den Prototyp am Mac aufsetzen und die CUJs vorführen.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/config/tobibox.mac.example.toml` | neu | Mac-Konfiguration (Gerätesuchmuster `/dev/cu.usbmodem*`, MPD, Pfade, Lautstärke-Obergrenze, Simulation). |
| `box/config/mpd.mac.example.conf` | neu | MPD am Mac: Puffer-Werte, Software-Mixer, ReplayGain-Zeilen. Keine „harte Obergrenze“: Am Mac gilt nur die Klemmung im Dienst. |
| `docs/betrieb/mac-prototyp.md` | neu | Schritt für Schritt: Homebrew, MPD, Python-Umgebung, Firmware flashen, Testserie anlegen, `tobiboxd` starten, Vorführung der CUJs. |
| `box/medien-beispiel/serie-a/serie.json` | neu | Beispielserie, Reihenfolge der Folgen. |
| `box/medien-beispiel/serie-a/folge-01.wav` | neu | Kurzer, selbst erzeugter Ton (keine fremden Inhalte). |
| `box/medien-beispiel/serie-a/folge-02.wav` | neu | Wie oben. |
| `box/medien-beispiel/serie-a/folge-03.wav` | neu | Wie oben. |
| `box/medien-beispiel/ueberraschung/serie.json` | neu | Überraschungs-Serie (`typ` `ueberraschung`). |
| `box/medien-beispiel/ueberraschung/ton-01.wav` | neu | Selbst erzeugter Ton. |

Abnahme AP 1.4:

- Die Anleitung lässt sich auf einem frischen Mac Schritt für Schritt ausführen.
- Die Beispielserien werden von `library.py` ohne Fehler gelesen.

#### AP 1.5 Automatische Prüfung (Haiku)

Ergebnis: Jeder Push führt die Tests aus.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `.github/workflows/ci.yml` | neu | Runner `ubuntu-24.04`, Python 3.11. Job `box`: `apt install mpd` (Systemdienst aus), `pip install -e "box[test]"`, pytest über `box/tests`. Job `firmware`: PlatformIO, `cp config.example.h config.h`, `pio test -e native`, `pio run -e esp32s3` (mit Platzhalter-Passwort; die gebaute Datei wird nicht veröffentlicht oder als Artefakt abgelegt). |
| `.gitignore` | änd. | Nur ergänzen (`config.h` und `.pio/` stehen schon): `tobibox.toml`, `.venv/`, Laufzeitdaten. |

Abnahme AP 1.5:

- Der Lauf auf einem Test-Branch ist in beiden Jobs grün.
- Die CI lädt keine Firmware-Datei hoch.

#### AP 1.6 Integration Stufe 1 und Messung (Sonnet)

Ergebnis: Die CUJ-Tests der Stufe laufen, die Messung liegt vor. Das AP führt
Änderungen zusammen, falls parallele APs `core.py`, `session.py` oder `app.py`
berührt haben (Grundregel).

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/core.py`, `box/src/tobibox/session.py`, `box/src/tobibox/app.py` | änd. | Nur Zusammenführen und Fehler beheben, die die CUJ-Tests zeigen. |
| `box/tests/cuj/test_cuj01_bekannte_figur.py` | neu | CUJ 1: Kette gelesen → entprellt → zugeordnet → spielt, mit Vorgangs-ID; Folge 1 ohne Zeiger. |
| `box/tests/cuj/test_cuj02_abheben.py` | neu | CUJ 2: Pause, Zeiger gespeichert. |
| `box/tests/cuj/test_cuj05_nfc_karte.py` | neu | CUJ 5: Karte verhält sich wie CUJ 1 bis 4. |
| `box/tests/cuj/test_cuj06_gesperrter_tonie.py` | neu | CUJ 6: Überraschungs-Serie, kurze Aussetzer starten sie nicht neu. |
| `box/tests/cuj/test_cuj08_figur_verrutscht.py` | neu | CUJ 8 aus Sicht des Dienstes: Lese-Lücken (keine Zeile der Firmware) und gleiche Kennung nach der Lücke führen zu keiner Pause und keinem Neustart. Die verfälschte Kennung prüfen die nativen Firmware-Tests (AP 1.1). |
| `box/tests/cuj/test_cuj13_leser_ausfall.py` | neu | CUJ 13: `seq`-Rücksetzen, Abheben während der Unterbrechung, Wächter-Alarm mit 1,5-s-Frist. |
| `box/tools/measure_audio_latency.py` | neu | Misst die Zeit vom Auflegen (Zeitstempel im Ereignisprotokoll) bis zum ersten Ton in einer Aufnahme am Ausgang. |
| `docs/timing.md` | neu | Messung je Schritt, mit Methode und Ergebnis (siehe Abnahme Stufe 1). |

Abnahme AP 1.6:

- Alle sechs CUJ-Tests sind grün.
- `docs/timing.md` ist ausgefüllt.

**Abnahme Stufe 1**

- Alle CUJ-Tests und übrigen Tests sind grün (pytest und PlatformIO `native`); die CI ist grün.
- Tobias führt am Mac mit echtem Leser CUJ 1, 2, 5, 6, 8 und 13 vor.
- Dazu ein Leser-Neustart: USB-Kabel bei spielender Figur ziehen und stecken; ein zweites Mal mit Abheben während der Unterbrechung.
- Nach Abheben, Neustart des Dienstes und erneutem Auflegen spielt die Figur an der gespeicherten Stelle weiter (Zeigerlogik).
- Die Klemmung im Dienst wirkt auch beim Start; der Test „Grenze wird nie überschritten“ ist grün. Die harte ALSA-Kappung gehört in den Pi-Probelauf.
- `docs/timing.md` enthält je einen Messwert für: Warten auf den Zyklus, erste Lesung, Entprellen, Entsperren (Tonie), Übertragung, Dienst, MPD-Start bis zum Ton am Ausgang.
- Die Summen liegen bei Auflegen unter 1,0 s und bei Abheben unter 1,5 s; Lücken bis 1,0 s führen zu keiner Pause.
- Überschreitet eine Messung die Grenze, gilt die Rückfallregel im Zeitbudget (Baustein 1).

### Stufe 2 — Resume, Serien, Zuordnung lokal (CUJ 3, 4, 7a/7b ohne HA, 11, 20)

**Von Tobias bereitzustellen:** nichts Neues.

**Reihenfolge:** AP 2.1, 2.2 und 2.3 laufen parallel; AP 2.4 am Schluss.

#### AP 2.1 Resume-Abnahme (Sonnet)

Ergebnis: Die Resume-Fälle aus CUJ 3, 4 und 20 sind als Tests festgeschrieben.
Die Zeigerlogik selbst ist seit Stufe 1 gebaut; ein Fehler, den die Tests zeigen,
wird in AP 2.4 behoben.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/tests/cuj/test_cuj03_resume.py` | neu | CUJ 3: Resume mit 3-s-Rücksprung, auch nach Neustart; Folge zu Ende bei liegender Figur (Pause, Zeiger auf die nächste Folge, nichts passiert bis Abheben und Auflegen; nach der letzten Folge Zeiger auf Folge 1). |
| `box/tests/cuj/test_cuj04_andere_figur.py` | neu | CUJ 4: Zeiger der alten Serie bleibt, neue Serie läuft an ihrem Zeiger oder bei Folge 1. |
| `box/tests/cuj/test_cuj20_figur_beim_start.py` | neu | CUJ 20: Figur liegt beim Start (bekannt: Zeiger; unbekannt: Überraschungs-Serie). |
| `box/tests/integration/test_resume_neustart.py` | neu | Dienst hart beenden und neu starten; Zeiger ist da, höchstens 30 s Wiedergabe verloren. |

Abnahme AP 2.1:

- Alle Tests sind grün.
- Die Stromausfall-Grenze von 30 s ist im Test belegt.

#### AP 2.2 Unbekannte Figuren, Lernmodus, Simulations-Treiber (Sonnet)

Ergebnis: Teilautomat Lernmodus, Ereignis-Ausgang mit Bestätigung und der
Simulations-Treiber `sim` mit Unix-Socket. Die Bestätigung kommt in dieser Stufe
von `tobibox sim ack`; HA ersetzt sie in Stufe 3a.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/learn.py` | neu | Teilautomat Lernmodus (Tabelle „Lernmodus“): 2-min-Frist auf der Box und Ablaufzeit des Befehls nach `mqtt-v1.md`. |
| `box/src/tobibox/outbox.py` | neu | Ereignis-Ausgang mit Bestätigung: `unknown.json` führen; Eintrag erst löschen, wenn das Ereignis `bestätigt` eintrifft. |
| `box/src/tobibox/sim.py` | neu | **Gemeinsamer Simulations-Treiber:** lauscht auf dem Unix-Socket `sim.sock` im Zustandsverzeichnis, liest JSON-Zeilen und macht Ereignisse daraus. Befehle in Stufe 2: `learn`, `ack`, `card`. Spätere Stufen erweitern ihn. |
| `box/tests/unit/test_learn.py` | neu | Alle Zeilen der Tabelle „Lernmodus“, abgelaufener Befehl wird ignoriert. |
| `box/tests/unit/test_outbox.py` | neu | Eintrag bleibt ohne Bestätigung, auch nach Neustart; wird mit Bestätigung gelöscht; doppelte Bestätigung schadet nicht. |
| `box/tests/unit/test_sim.py` | neu | JSON-Zeilen über den Socket werden zu den erwarteten Ereignissen; ungültige Zeilen werden protokolliert und ignoriert. |

Abnahme AP 2.2:

- Alle Tests sind grün.
- Ohne `ack` bleibt ein Eintrag in `unknown.json` stehen, auch nach Neustart.

#### AP 2.3 Status und Admin-Karte (Sonnet)

Ergebnis: Die Prüfpunkte und die Tonfolge für die Status-Karte.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/selftest.py` | neu | Prüfpunkte (Leser, Medien, Netz, Speicher) und die eingebaute Prüfroutine; läuft ohne pytest. |
| `box/sounds/pruef_ok.wav` | neu | Kurz-hoher Ton: Prüfpunkt in Ordnung. |
| `box/sounds/pruef_fehler.wav` | neu | Tiefer Ton: Prüfpunkt hat einen Fehler. |
| `box/tests/unit/test_selftest.py` | neu | Jeder Prüfpunkt in Ordnung und mit Fehler; Reihenfolge der Tonfolge. |

Abnahme AP 2.3:

- Alle Tests sind grün.
- Die Prüfroutine läuft ohne pytest und ohne Leser (Prüfpunkt „Leser“ auf Simulation).

#### AP 2.4 Integration Stufe 2 (Sonnet)

Ergebnis: Lernmodus, Ausgang, Status-Karte und `sim` sind im Dienst verdrahtet;
die CUJ-Tests der Stufe laufen.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/core.py` | änd. | `learn` in die Liste der Teilautomaten eintragen. |
| `box/src/tobibox/session.py` | änd. | Karte mit Typ `aktion` löst die Aktion aus statt einer Serie (Status: Tonfolge); Fehler beheben, die die Tests aus AP 2.1 zeigen. |
| `box/src/tobibox/app.py` | änd. | `outbox` und `sim` verdrahten. |
| `box/src/tobibox/cli.py` | änd. | `tobibox status` ausführlich; `tobibox sim learn`, `tobibox sim ack` und `tobibox sim card` (Karte als Aktion in `config.json` zuordnen, bis HA das in Stufe 3a übernimmt). |
| `box/tests/cuj/test_cuj07a_unbekannte_figur.py` | neu | CUJ 7a: Überraschungs-Serie, Eintrag in `unknown.json`, Löschen erst nach `ack`, Wechsel auf die Serie nach der Zuordnung. |
| `box/tests/cuj/test_cuj07b_lernmodus.py` | neu | CUJ 7b ohne HA: Lernmodus per `tobibox sim learn`, Frist 2 min, Abbruch, abgelaufener Befehl. |
| `box/tests/cuj/test_cuj11_status.py` | neu | CUJ 11: Status-Admin-Karte als pytest-Tabelle. |
| `box/tests/integration/test_sim_cli.py` | neu | `tobibox sim …` als eigener Prozess gegen den laufenden Dienst. |

Abnahme AP 2.4:

- Die CUJ-Tests 7a, 7b und 11 sind grün.
- Die Tests aus AP 2.1 sind grün.

**Abnahme Stufe 2**

- Alle Punkte der Abnahme Stufe 1 gelten weiter.
- Tobias führt Resume über einen Neustart vor.
- Tobias führt den Lernmodus per `tobibox sim learn` und die Bestätigung per `tobibox sim ack` vor.
- CUJ 20 (Figur liegt beim Start) ist vorgeführt.
- Die Pause nach jeder Folge ist vorgeführt (Regel: AP 2.1, Test `test_cuj03_resume.py`).

### Pi-Probelauf (sobald der Pi 3A+ da ist)

**Von Tobias bereitzustellen**

| Was | Wofür | Frist |
|---|---|---|
| Raspberry Pi 3A+ | AP P.1 | vor AP P.1 |
| microSD-Karte | AP P.1 | vor AP P.1 |
| Netzteil | AP P.1 | vor AP P.1 |
| Entscheidung zum Image: Pi OS Lite, Bookworm, 32 Bit (Python 3.11) | AP P.1, Paketbau | vor AP P.1 |
| Bestätigung der Soll-Werte (Tabelle unten) | AP P.2 | vor AP P.2 |

#### AP P.1 Pi-Installation (Sonnet)

Ergebnis: Ein frischer Pi mit dem Dienst, MPD, harter Lautstärke-Kappung und
dauerhaftem Protokoll.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `deploy/pi/install.sh` | neu | Auf frischem Pi OS Lite: Pakete (MPD, minisign, rsync), Benutzer, Verzeichnisse, Python-Umgebung, Dienste; Zustandsverzeichnis mit `noatime`; setzt die Seriennummer des angesteckten ESP32 in die udev-Regel ein. |
| `deploy/pi/tobiboxd.service` | neu | systemd-Dienst: `Type=notify`, `TimeoutStartSec=300`, `Restart=on-failure`, `RestartSec=3`, `StartLimitIntervalSec=120`, `StartLimitBurst=5`, `PYTHONPATH` auf die Abhängigkeiten, `StandardOutput=journal`. |
| `deploy/pi/99-tobibox-reader.rules.example` | neu | udev-Regel: fester Gerätename nach der Seriennummer des ESP32 (Platzhalter). |
| `deploy/pi/mpd.conf` | neu | MPD für die Box: ALSA-Ausgabe über `softvol`, Puffer-Startwerte (`audio_buffer_size`, `buffer_before_play`, `buffer_time`), ReplayGain (`replaygain_preamp` 0, `replaygain_missing_preamp` −6 dB, `replaygain_limit`). |
| `deploy/pi/asound.conf` | neu | ALSA-`softvol` mit `max_dB`: die harte Kappung der Lautstärke. |
| `deploy/pi/mpd.service.d/startvolume.conf` | neu | systemd-Drop-in für MPD: `ExecStartPost` setzt die Startlautstärke vor dem ersten Abspielen. |
| `deploy/pi/journald-tobibox.conf` | neu | `Storage=persistent`, begrenzter Platz, `SyncIntervalSec=30s`, damit das Protokoll einen Stromausfall übersteht. |
| `box/config/tobibox.pi.example.toml` | neu | Pi-Konfiguration (Gerätename, Pfade, Obergrenze, Startlautstärke). |
| `box/tests/unit/test_deploy_configs.py` | neu | Prüft die Konfigurationsdateien: `max_dB` in `asound.conf`, ReplayGain-Zeilen in `mpd.conf`, Restart-Werte und `Type=notify` in `tobiboxd.service`. |

Abnahme AP P.1:

- `install.sh` läuft auf einem frischen Pi OS Lite ohne Handarbeit durch.
- Der Dienst startet nach `systemctl start` und meldet `READY=1`.
- `test_deploy_configs.py` ist grün.

#### AP P.2 Prüfliste Pi-Probelauf (Haiku)

Ergebnis: Eine Prüfliste mit Soll-Werten und Messmethoden.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `docs/betrieb/pi-probelauf.md` | neu | Ablauf und Prüfliste: dieselben CUJ-Tests und Vorführungen wie am Mac, plus die Messpunkte der Tabelle unten, je mit Werkzeug und Methode (Ton am Ausgang: Mikrofon oder Loopback; Speicher: `free`; Startzeit: Zeitstempel im Protokoll). |

**Soll-Werte für den Pi-Probelauf** (Vorschlag der Projektleitung; Tobias
bestätigt oder ändert sie):

| Messpunkt | Soll-Wert |
|---|---|
| Belegter Arbeitsspeicher, alle Dienste laufen | ≤ 300 MB |
| Start (Strom an) bis „bereit“ | ≤ 40 s |
| Auflegen eines Tonies (mit Entsperrzeit), ohne Last | ≤ 1,0 s |
| Auflegen einer bekannten Figur, während ein Sync läuft | ≤ 1,0 s; wird erst nach AP 3.4 am Pi gemessen (Abnahme Stufe 3a) |
| Abheben bis Pause | ≤ 1,5 s |
| Figur liegt beim Start (CUJ 20) | spielt, sobald „bereit“ |
| Lautstärke-Kappung (`softvol`) | Ausgang bleibt bei Dienst-Absturz und Neustart unter der Grenze |
| Schreibvorgänge pro Tag (Zeiger, Protokoll) | im Schreibbudget des Datenmodells |
| Temperatur | nur protokollieren (kein Soll-Wert) |
| Stromausfall-Test | Dateien nach hartem Ausschalten lesbar |

Werden Werte verfehlt, gilt die Rückfallregel aus Baustein 1: Zuerst die Arbeit
pro Zyklus senken; bleibt ein Wert verfehlt, fragt die Projektleitung Tobias, ob
1,2 s akzeptabel sind.

**Abnahme Pi-Probelauf**

- Die Prüfliste ist vollständig grün.
- Unterschiede zum Mac sind dokumentiert.
- Bei bestandenem Probelauf bestätigt er den Verzicht auf V3 (Begründung: „Abgewogene Alternativen“).

### Go/No-Go mit Tobias vor Stufe 3a

Stufe 3a beginnt, wenn:

1. die Abnahmen von Stufe 1 und 2 bestanden sind,
2. der Pi-Probelauf bestanden oder bewusst verschoben ist (mit Begründung),
3. keine Blocker-Befunde aus den Goldfisch-Reviews mehr offen sind,
4. die Voraussetzungen erfüllt sind: Tailscale (HA-Add-on, QNAP-App) und der
   MQTT-Broker in HA laufen, HA hat vollen Schreibzugriff auf die
   NAS-Freigabe (`medien/`, `export/`, `releases/`), und die Tabelle „Von Tobias
   bereitzustellen“ der Stufe 3a ist abgearbeitet.

Stufe 3b beginnt, wenn die Abnahme von Stufe 3a bestanden ist und Tobias das
Schlüsselpaar zum Signieren (`minisign`) auf seinem Mac erzeugt hat.

### Stufe 3a — HA, Medienverwaltung, Sync, Netz, Tailscale (CUJ 7a/7b mit HA, 9, 12)

**Von Tobias bereitzustellen**

| Was | Wofür | Frist |
|---|---|---|
| Home Assistant mit Mosquitto-Add-on (Broker) | HA-Tests, AP 3.3, Abnahme | vor Stufe 3a |
| Laufende HA-Version (Nummer nennen) | feste Version für die HA-Tests | vor AP 3.1 |
| Namen (SSIDs) von Heim-WLAN und Handy-Hotspot | `net.py`, Konfiguration | vor AP 3.3 |
| QNAP: rsync-Daemon mit Modul `medien` (nur lesend) und den Zugangsdaten | AP 3.4 | vor AP 3.4 |
| CPU-Architektur des QNAP | Container-Bild (Stufe 3b) | vor Stufe 3b |
| Tailscale: Konto, HA-Add-on, QNAP-App, Box-Knoten | AP 3.5 | vor AP 3.5 |
| Ein Ort für Zugangsdaten (`tobibox.toml`, MQTT-Passwörter), nie im Repo | AP 3.3, 3.5 | vor AP 3.3 |
| Handy mit Nabu Casa | Abnahme (Upload, Seite) | Abnahme |

**Vertrag W (zuerst, vor AP 3.1 und 3.2):** Die Projektleitung schreibt
`docs/protocol/ha-websocket-v1.md` mit den WebSocket-Befehlen zwischen
HA-Backend und Seite (Name, Eingabe, Ausgabe, Fehler). Ein Goldfisch prüft ihn,
Tobias gibt ihn frei. Erst danach starten AP 3.1 und 3.2.

**Reihenfolge:** Nach Vertrag W laufen AP 3.1 bis 3.6 parallel; AP 3.7 am Schluss.

#### AP 3.1 HA-Integration Backend (Sonnet)

Ergebnis: Die Integration `tobibox` mit Speicher, Medienverwaltung, MQTT und
WebSocket nach Vertrag W.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `homeassistant/custom_components/tobibox/manifest.json` | neu | Mit `version` und `dependencies` (`mqtt`, `http`, `panel_custom`, `websocket_api`). |
| `homeassistant/custom_components/tobibox/__init__.py` | neu | Einrichtung; Seite über `panel_custom` registrieren, Dateien über `async_register_static_paths`. |
| `homeassistant/custom_components/tobibox/config_flow.py` | neu | Einrichtung: Medienpfad, Boxen. |
| `homeassistant/custom_components/tobibox/const.py` | neu | Konstanten. |
| `homeassistant/custom_components/tobibox/store.py` | neu | Konfiguration (Zuordnungen, Leise-Zeiten, Gute-Nacht-Einstellungen) mit einer Revision und einer Listen-ID im HA-Speicher; automatischer Export auf das NAS nach jeder Änderung. |
| `homeassistant/custom_components/tobibox/media.py` | neu | `serie.json` lesen/schreiben (mit `angelegt_am`, `typ`), neue Ordner/Dateien erkennen (neue Dateien hinten an die Reihenfolge), Format- und Kopierschutz-Prüfung (D5), Speicheranzeige aus den Box-Meldungen, Papierkorb ohne Automatik, Hochladen als Strom in Blöcken; Datei-Zugriffe über `async_add_executor_job`. |
| `homeassistant/custom_components/tobibox/mqtt.py` | neu | `tobibox/config` veröffentlichen („Liste neu ausrollen“ = neue Listen-ID), Box-Ereignisse empfangen und idempotent verarbeiten, Kennungen auf `…/ack` bestätigen, Befehle mit Ablaufzeit senden, abgelehnte Listen anzeigen. |
| `homeassistant/custom_components/tobibox/websocket_api.py` | neu | Die WebSocket-Befehle nach Vertrag W. |
| `homeassistant/custom_components/tobibox/http.py` | neu | Upload-Endpunkt mit Anmeldung (nur Audioformate nach D5). |
| `homeassistant/custom_components/tobibox/services.yaml` | neu | Aktionen. |
| `homeassistant/custom_components/tobibox/strings.json` | neu | Texte (Quelle). |
| `homeassistant/custom_components/tobibox/translations/de.json` | neu | Deutsche Texte. |
| `homeassistant/mosquitto/acl.conf.example` | neu | Broker-Rechte: ein Konto je Box, Themenrechte wie in Baustein 4; `homeassistant` und `addons` unbeschränkt. |
| `homeassistant/mosquitto/mosquitto-addon.example.yaml` | neu | Add-on-Einstellung mit `customize.active: true` und `logins` (Box-Konten ohne HA-Admin). |
| `homeassistant/requirements-test.txt` | neu | Feste HA-Version und `pytest-homeassistant-custom-component`, passend zur HA-Version. |
| `homeassistant/README.md` | neu | Installation der Integration, getestete HA-Version. |
| `homeassistant/tests/conftest.py` | neu | Fixtures: Test-Medienordner, Fake-Box. |
| `homeassistant/tests/test_store.py` | neu | Revision und Listen-ID, Export auf das NAS. |
| `homeassistant/tests/test_media.py` | neu | Neue Ordner/Dateien, `serie.json`-Regeln, doppelte IDs, Papierkorb, DRM-Prüfung (`drms`, Probedekodierung). |
| `homeassistant/tests/test_mqtt.py` | neu | Veröffentlichen, Bestätigung `…/ack`, Ablaufzeit der Befehle, Idempotenz. |
| `homeassistant/tests/test_websocket_api.py` | neu | Jeder Befehl aus Vertrag W: gültig und ungültig. |
| `homeassistant/tests/test_upload.py` | neu | Upload größer als 16 MiB im Strom; falsches Format wird abgelehnt; ohne Anmeldung abgelehnt. |
| `homeassistant/tests/test_restore.py` | neu | „HA-Wiederherstellung mit neuer Listen-ID und niedriger Revision“ und „Liste neu ausrollen“. |

Abnahme AP 3.1:

- Alle HA-Tests sind grün, in eigener venv mit der festen HA-Version.
- Der Upload-Test belegt, dass eine Datei über 16 MiB ankommt.
- Eine Kennung wird erst nach `…/ack` als bestätigt geführt.

#### AP 3.2 HA-Seite (Sonnet)

Ergebnis: Die Seite „Tobi Box“, bedienbar am Handy.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `homeassistant/custom_components/tobibox/frontend/tobibox-panel.js` | neu | Serienliste, Folgen ziehen, Hochladen, Umbenennen, Neue Figuren, Lernmodus, Zuordnen von Aktionskarten (Status, Gute Nacht), Box-Status mit freiem Speicher, Aktionen „Liste neu ausrollen“ und „Papierkorb leeren“. |
| `homeassistant/custom_components/tobibox/frontend/lit-all.min.js` | neu | Lit in fester Version, eingecheckt (kein Laden aus dem Netz). |
| `homeassistant/tests/frontend/mock-hass.mjs` | neu | Mock für die HA-WebSocket-Schnittstelle. |
| `homeassistant/tests/frontend/panel.test.mjs` | neu | Mit `node --test`: Das Modul lädt; jeder Aufruf geht mit den Namen und Feldern aus Vertrag W gegen den Mock; Fehlerantworten werden angezeigt. |

Abnahme AP 3.2:

- `node --test homeassistant/tests/frontend` ist grün.
- Tobias bedient die Seite am Handy über Nabu Casa (Vorführung).

#### AP 3.3 Box-Dienst: HA, Netz, Strom (Sonnet)

Ergebnis: Die Box spricht MQTT, erkennt die Netz-Klasse und kennt die
Strom-Schnittstelle. Die Eingänge in `sim.py` und `cli.py` trägt AP 3.7 ein.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/ha.py` | neu | MQTT mit eigenem Konto (QoS 1, dauerhafte Sitzung), Discovery, Konfiguration nach der Revisionsregel (Listen-ID) übernehmen, abgelehnte Listen melden, unbekannte Kennungen dauerhaft je Kennung veröffentlichen und `…/ack` als Ereignis `bestätigt` weitergeben, Befehle mit Ablaufzeit prüfen, HA-Sensoren inkl. Status und freiem Speicherplatz. |
| `box/src/tobibox/net.py` | neu | Netz-Klasse (NetworkManager-SSID; im Test simuliert); Zeitquelle (NTP). |
| `box/src/tobibox/power.py` | neu | Strom-Schnittstelle **komplett** (Akkustand, Lader, Tastenereignis, Tiefstand, RTC beim Start lesen, Zeitquelle melden) und eine Simulations-Fassung für `sim`. |
| `box/tests/unit/test_ha_config_rules.py` | neu | Revisionsregel: neue Listen-ID gewinnt, höhere Revision gewinnt, alles andere wird abgelehnt und gemeldet. |
| `box/tests/unit/test_net.py` | neu | Netz-Klassen `home`, `hotspot`, `offline`. |
| `box/tests/unit/test_power.py` | neu | Tiefstand, Tastenereignis, Lader, Hotspot-/Akku-Regel des Syncs mit Simulation. |
| `box/tests/integration/test_ha_mqtt.py` | neu | Gegen einen echten lokalen Mosquitto: Konfiguration holen, Befehl mit Ablaufzeit, Kennung bleibt in `unknown.json`, bis `…/ack` kommt (auch wenn der Broker die Nachricht schon angenommen hat). |

Abnahme AP 3.3:

- Alle Tests sind grün.
- Eine Kennung wird nicht gelöscht, wenn nur der Broker, aber nicht HA bestätigt hat.

#### AP 3.4 Medien-Sync (Sonnet)

Ergebnis: Der Sync nach den Regeln aus „Netz, Sync, Strom“.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/sync.py` | neu | rsync gegen den rsync-Daemon des QNAP (Modul `medien`, nur lesend) über Tailscale; Regeln Heim/Hotspot/Akku (im Hotspot ohne Datenlimit); `--partial-dir` außerhalb des Medienordners auf demselben Dateisystem und `--delay-updates`; `--delete` mit Schutz (Abbruch bei fehlender oder leerer Quelle oder mehr als 20 % Löschungen, vorab gezählt mit `--dry-run --itemize-changes`); Platzprüfung vorab; die spielende Datei (MPD `currentsong`) per `--exclude`; MPD neu einlesen; Sperre gegen Update; keine Abschaltung während des Syncs; `nice`/`ionice`. |
| `box/tests/unit/test_sync.py` | neu | Tests gegen einen lokalen rsync-Daemon: leere Quelle, fehlende Quelle, zu viele Löschungen, zu wenig Platz, spielende Datei ausgenommen, `--partial-dir` außerhalb des Medienordners, Netzregel. |
| `box/tests/unit/test_sync_ereignisse.py` | neu | Während eines Syncs laufen Kern-Ereignisse weiter (Auflegen wird verarbeitet). Die Latenz unter echter Last misst Abnahme Stufe 3a am Pi. |

Abnahme AP 3.4:

- Alle Tests sind grün.
- Eine laufende Datei wird nie ersetzt oder gelöscht.

#### AP 3.5 Einrichtung Tailscale, NAS und MQTT-Konten (Haiku)

Ergebnis: Anleitungen und Vorlagen für die Schritte, die nur Tobias machen kann.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `docs/betrieb/tailscale-nas.md` | neu | Schritte für die QNAP-App, das HA-Add-on, die Box-Schlüssel, die ACL und den rsync-Daemon. |
| `docs/betrieb/mqtt-konten.md` | neu | Konto je Box anlegen, Themenrechte, Passwörter nur auf der Box (nicht im Repo). |
| `deploy/nas/rsyncd.example.conf` | neu | Modul `medien` und Modul `releases`, beide `read only = yes`. |
| `deploy/tailscale/acl.example.json` | neu | ACL mit Tags: Boxen erreichen nur die Medienfreigabe und HA. |
| `deploy/tailscale/acl-pruefung.sh` | neu | Prüft von einer Box aus, dass andere Ziele gesperrt sind. |
| `deploy/tailscale/einrichtung-assistent.sh` | neu | Optional: führt durch die Schritte, die nur Tobias machen kann. |

Die Anleitung enthält außerdem:

- Rechte für HA: volles Schreibrecht auf `medien/`, `export/` und `releases/`.
- Schlüsselablauf der Box-Knoten abschalten.
- Schlüssel einer verlorenen Box sperren.

Abnahme AP 3.5:

- Tobias richtet nach der Anleitung beide Boxen ein, ohne nachzufragen.
- `acl-pruefung.sh` meldet, dass andere Ziele gesperrt sind.

#### AP 3.6 CI-Erweiterung Stufe 3a (Haiku)

Ergebnis: Die CI prüft auch die HA-Integration, in einem eigenen Job.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `.github/workflows/ci.yml` | änd. | Neuer Job `homeassistant` mit eigener venv (Python-Version passend zur festen HA-Version), `pip install -r homeassistant/requirements-test.txt`, pytest über `homeassistant/tests`, `node --test homeassistant/tests/frontend`. Im Job `box` zusätzlich `apt install mosquitto rsync`. |

Abnahme AP 3.6:

- Beide Jobs laufen getrennt und sind grün.

#### AP 3.7 Integration Stufe 3a (Sonnet)

Ergebnis: HA, Netz, Strom und Sync sind im Dienst verdrahtet; die CUJ-Tests der
Stufe laufen.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/core.py` | änd. | Ereignisse aus HA, Netz, Strom und Sync an die Teilautomaten. |
| `box/src/tobibox/app.py` | änd. | `ha`, `net`, `power`, `sync` verdrahten; die Bestätigung kommt nun von `ha` statt von `sim`. |
| `box/src/tobibox/sim.py` | änd. | Eingang Strom (`power`). |
| `box/src/tobibox/cli.py` | änd. | `tobibox sim power --charger on --battery 40`; `tobibox status` zeigt HA und Sync. |
| `box/tests/cuj/test_cuj07_ha.py` | neu | CUJ 7a und 7b mit HA (Fake-HA über den lokalen Mosquitto). |
| `box/tests/cuj/test_cuj09_sync.py` | neu | CUJ 9: unvollständige Dateien nie abspielbar, laufende Datei nie ersetzt. |
| `box/tests/cuj/test_cuj12_unterwegs.py` | neu | CUJ 12 als pytest-Tabelle. |

Abnahme AP 3.7:

- Die CUJ-Tests 7, 9 und 12 sind grün.
- Die Tests aus Stufe 1 und 2 sind weiter grün.

**Abnahme Stufe 3a**

- CUJ 7a/7b mit HA, 9 und 12 sind als pytest-Tabellen grün.
- Tobias führt die Seite am Handy über Nabu Casa vor, mit einem Upload größer als 16 MiB, und eine Box am Mac.
- Auflegen während Sync: Am Pi innerhalb der Zeitgrenze; ohne Pi holt das der Pi-Lauf nach, sobald der Pi da ist.
- Leser-Neustart bei spielender Figur (CUJ 13) ist weiter bestanden.
- Die HA-Wiederherstellung mit neuer Listen-ID wird von beiden Boxen übernommen, auch bei niedrigerer Revision.
- „Liste neu ausrollen“ wird von beiden Boxen übernommen.
- Die Hotspot-/Akku-Regel ist mit Simulation geprüft.
- Die Tailscale-ACL sperrt andere Ziele.

### Stufe 3b — Update, Lautheit, Handbuch (CUJ 10)

Voraussetzung: Abnahme Stufe 3a bestanden, Schlüsselpaar von Tobias erzeugt
(siehe Go/No-Go).

**Von Tobias bereitzustellen**

| Was | Wofür | Frist |
|---|---|---|
| `minisign`-Schlüsselpaar auf dem Mac (der geheime Schlüssel bleibt dort) | AP 3.8, Pakete signieren | vor Stufe 3b |
| Container Station (oder Entsprechendes) auf dem QNAP | AP 3.9, Lautheits-Container | vor AP 3.9 |

**Reihenfolge:** AP 3.8, 3.9 und 3.10 laufen parallel; danach AP 3.11, zuletzt AP 3.12.

#### AP 3.8 Update mit Rückfall und Signatur (Sonnet)

Ergebnis: Ein signiertes Paket lässt sich installieren, prüfen und bei Fehlern
zurückrollen, auch wenn die neue Version nicht startet. Die Abhängigkeiten
liegen fertig gebaut im Paket (kein Bauen auf dem Pi).

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/update.py` | neu | Bedingungen prüfen, Paket holen, **Signatur prüfen** mit `minisign` (Prüfschlüssel auf der Box), nach `releases/<version>/` entpacken, Zustandsdateien sichern, `current` atomar umstellen, Zustand `testing`/`ok`/`failed` in `update.json`, Meldung an HA. |
| `box/src/tobibox/selftest.py` | änd. | Prüfroutine für das Update: Dienst, `HELLO`, Dateien, MPD, Testton; meldet im Zustand `testing` `READY=1` erst nach bestandenem Test. Ohne pytest. |
| `deploy/pi/guard.py` | neu | Wächter-Skript, nur Standardbibliothek: zählt Starts im Zustand `testing`, bei Zähler ≥ 3 Rückfall (Verweis zurück, Sicherung zurückspielen, `failed`); `--failed` für `OnFailure=`; die Entscheidungsfunktion „bleiben oder zurück“. Wird nach `/opt/tobibox/bin/guard.py` installiert, kommt mit dem SD-Image und wird nie per Update ersetzt. |
| `deploy/pi/tobiboxd.service.d/rollback.conf` | neu | systemd-Drop-in: `ExecStartPre=/opt/tobibox/bin/guard.py`, `OnFailure=tobiboxd-failed.service`. |
| `deploy/pi/tobiboxd-failed.service` | neu | Ruft `guard.py --failed` auf. |
| `deploy/pi/install.sh` | änd. | Installiert `guard.py` und das Drop-in. |
| `deploy/build_release.sh` | neu | Paket mit `manifest.json` und Abhängigkeiten per `pip install --target` bauen; Python-Minor-Version muss die des Pi OS (3.11) sein. |
| `deploy/sign_release.sh` | neu | Ruft nur `minisign` auf, um das Paket mit Tobias' Signierschlüssel zu signieren (der Schlüssel bleibt auf seinem Mac, nicht im Repo, nicht auf NAS oder HA); der Prüfschlüssel kommt ins SD-Image. |
| `box/tests/unit/test_update.py` | neu | Umschalten, Selbsttest-Fehler, ungültige Signatur (Test-Schlüsselpaar wird im Test erzeugt), Startfehler, Zähler zählt im Zustand `ok` nicht. |
| `box/tests/unit/test_guard.py` | neu | Die Entscheidungsfunktion mit allen Eingabe-Kombinationen; Importfehler der neuen Version (der Wächter läuft trotzdem); **Rückfall spielt die gesicherten Zustandsdateien zurück**. |
| `box/tests/unit/test_release_pure_python.py` | neu | Das gebaute Paket enthält nur reines Python (keine `.so`/`.dylib`). |
| `docs/data-model.md` | änd. | Schema `update.json`; Hinweis „Schemas möglichst abwärtskompatibel erweitern“ (die Regel ist das Zurückspielen der Sicherung). |

Abnahme AP 3.8:

- Alle Tests sind grün; die CI installiert `minisign`.
- Eine neue Version mit Importfehler wird nach 3 Starts zurückgerollt.
- Wird der Selbsttest nicht in 5 min bestanden, beendet systemd den Dienst, der Neustart zählt, und der Rückfall greift.
- Ein Update mit ungültiger Signatur wird abgelehnt.

#### AP 3.9 Lautheitsangleich (Haiku)

Ergebnis: Ein Container auf dem NAS schreibt ReplayGain-Tags (D6).

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `deploy/nas/Dockerfile` | neu | Baut `rsgain` in fester Version; Bild für die CPU-Architektur des QNAP. |
| `deploy/nas/lautheit.sh` | neu | Ruft `rsgain` im Easy-Modus mit `-S` und Ziel −18 LUFS auf. |
| `deploy/nas/crontab` | neu | Zeitplan im Container: alle 15 min; kein Auslöser aus HA. |
| `deploy/nas/compose.yaml` | neu | Container-Definition mit Medienordner. |
| `docs/betrieb/lautheit.md` | neu | Einrichtung auf dem NAS, Modus Track (für gemischte Quellen), MPD-Einstellung (`replaygain_preamp` 0, `replaygain_missing_preamp` −6 dB, `replaygain_limit`), Zusammenspiel mit der Lautstärke-Regel. Hinweis: Eine Datei, die die Box vor dem Messen geholt hat, wird einmal nachübertragen; das ist hingenommen. |
| `box/tests/unit/test_replaygain_config.py` | neu | Prüft die Konfiguration: MPD-Zeilen in `deploy/pi/mpd.conf` und `box/config/mpd.mac.example.conf`; `-S` und −18 LUFS in `lautheit.sh`. Die echte Prüfung ist die Messung am Pi. |

Abnahme AP 3.9:

- Der Konfigurationstest ist grün.
- Der Container läuft auf dem QNAP und schreibt nach Zeitplan Tags nur in neue Dateien (zweiter Lauf ändert nichts).

#### AP 3.10 CI-Erweiterung Stufe 3b (Haiku)

Ergebnis: Die CI prüft Paketbau und Signatur.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `.github/workflows/ci.yml` | änd. | Im Job `box` `apt install minisign`; Schritt, der `deploy/build_release.sh` mit Test-Schlüsselpaar ausführt und die Signatur prüft. |

Abnahme AP 3.10:

- Der Job `box` ist grün, einschließlich der Update-Tests.

#### AP 3.11 Integration Stufe 3b (Sonnet)

Ergebnis: Update und Selbsttest sind verdrahtet; CUJ 10 läuft als Test.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/core.py` | änd. | Update-Ereignisse (gestartet, Selbsttest bestanden/durchgefallen); die Leerlauf-Regel wartet während eines Updates. |
| `box/src/tobibox/app.py` | änd. | `update` und `selftest` verdrahten. |
| `box/src/tobibox/cli.py` | änd. | `tobibox status` zeigt den Update-Zustand. |
| `box/tests/cuj/test_cuj10_update.py` | neu | CUJ 10 als pytest-Tabelle. |

Abnahme AP 3.11:

- `test_cuj10_update.py` ist grün.
- Alle früheren Tests sind weiter grün.

#### AP 3.12 Betriebshandbuch (Haiku)

Ergebnis: Tobias kann eine Box ohne Hilfe wiederherstellen.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `docs/betrieb/handbuch.md` | neu | Neuinstallation, SD-Image, „was ist wo konfiguriert“, Fehlerbilder, HA-Wiederherstellung (HA-Sicherung oder NAS-Export, danach „Liste neu ausrollen“), Signierschlüssel und Pakete bauen. |

Abnahme AP 3.12:

- Ein Goldfisch kann anhand des Handbuchs jeden Schritt der Wiederherstellung benennen.

**Abnahme Stufe 3b**

- CUJ 10 ist als pytest-Tabelle grün.
- Der Rückfall spielt die Zustandsdateien zurück.
- Wird der Selbsttest nicht in 5 min bestanden, beendet sich der Dienst, der Startzähler greift, und der Rückfall greift.
- Ein Update mit ungültiger Signatur wird abgelehnt.
- Die ReplayGain-Konfiguration ist nach `test_replaygain_config.py` richtig; der Lautheits-Container läuft nach Zeitplan.
- Der Plan in `docs/plan/` ist nachgezogen.

### Stufe 4 — Hardware-Funktionen mit Simulation (CUJ 14–19)

Alle Funktionen entstehen jetzt, mit Simulation am Mac hinter derselben
Schnittstelle, die die echte Hardware später nutzt. Alle Eingänge liefert **ein**
gemeinsamer Simulations-Treiber (`sim.py`, seit Stufe 2). Die APs 4.1 bis 4.7
sind getrennt voneinander baubar; jedes liefert nur seine eigenen Dateien. AP 4.8
trägt alle Eingänge in `sim.py` ein und hängt alle Module in `core.py` und
`app.py` ein.

**Von Tobias bereitzustellen:** nichts (Simulation). Die echte Hardware folgt
später: LED-Ring, Tasten und Drehregler, PiSugar mit Akku, Kopfhörer-Buchse,
Verstärker.

#### AP 4.1 LED-Ring-Logik (Sonnet), umsetzt CUJ 18

Ergebnis: Ring-Zustände als reine Logik.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/led.py` | neu | Zustände laut Projektplan (`docs/plan/`, Abschnitt 5.5.2): läuft, Pause, Akku, unbekannte Karte, Aufwachen; Helligkeitsdeckel 25 %. Der Zustand erscheint über den gemeinsamen Treiber im Terminal und im Protokoll; keine Anzeige in HA. Der echte Ring ersetzt später nur den Treiber. |
| `box/tests/unit/test_led.py` | neu | Jeder Zustand; der Deckel wird nie überschritten. |

Abnahme AP 4.1:

- Jeder Zustand hat einen Test.
- Die Helligkeit liegt nie über 25 %.

#### AP 4.2 Tasten und Drehregler (Sonnet), umsetzt CUJ 19

Ergebnis: Bedien-Ereignisse und der Hauptknopf nach Entscheidung E.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/controls.py` | neu | Vor, Zurück, Lautstärke, Hauptknopf kurz/lang als Ereignisse für den Kern. |
| `box/tests/unit/test_controls.py` | neu | Tasten-Zuordnung, kurz/lang, Lautstärke bleibt unter der wirksamen Grenze. |
| `box/tests/unit/test_session_hauptknopf.py` | neu | Hauptknopf kurz je Zustand: `spielt` → Pause; `pausiert` mit Figur → Abspielen; `beendet` mit Figur → nächste Folge ab Zeiger; ohne Figur → normale Funktion (Play / Pause). |

Abnahme AP 4.2:

- Vor / Zurück springt zur nächsten / vorigen Folge.
- Der Drehregler ändert die Lautstärke nie über die wirksame Grenze.
- Hauptknopf kurz: Play / Pause; ist eine Folge zu Ende und liegt die Figur noch auf der Box, spielt er die nächste Folge (Entscheidung E); ohne Figur gilt Play / Pause.
- Hauptknopf lang: Zeiger speichern und herunterfahren.

#### AP 4.3 Leerlauf und PiSugar-Beschreibung (Sonnet), umsetzt CUJ 16

Ergebnis: Teilautomat Strom / Leerlauf.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/idle.py` | neu | Teilautomat Strom / Leerlauf: Abschaltung nach 20 min, nie während Sync, Update oder Lernmodus. Am Lader wird nicht abgeschaltet, solange Sync oder Update laufen; ist keines aktiv, gilt die 20-min-Regel. Beim Start am Lader Sync prüfen. Nutzt `power.py` aus AP 3.3. |
| `box/tests/unit/test_idle.py` | neu | 20-min-Leerlauf und Lader-Regel (mit simulierter Uhr). |
| `docs/betrieb/pisugar-wecker.md` | neu | Beschreibung der PiSugar-Anbindung und Option: nächtliches Wecken am Lader über den PiSugar-Wecker (nur Beschreibung, Umsetzung nach Tobias' Entscheidung). |

Abnahme AP 4.3:

- Nach 20 min Leerlauf wird heruntergefahren (in der Simulation nur protokolliert).
- Während Sync, Update oder Lernmodus wird nie abgeschaltet.

#### AP 4.4 Kopfhörer (Sonnet), umsetzt CUJ 17

Ergebnis: Kopfhörer-Ereignis und Ausgangswechsel.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/headphones.py` | neu | Ereignis „Stecker erkannt / gezogen“. |
| `box/src/tobibox/player.py` | änd. | Reihenfolge beim Wechsel: erst Grenze setzen, dann Ausgang schalten. `volume.py` bleibt unverändert (Liste benannter Grenzen). |
| `box/tests/unit/test_headphones.py` | neu | Die Grenze greift vor dem Umschalten und fällt beim Ziehen zurück. |

Abnahme AP 4.4:

- Beim Einstecken gilt zuerst die Kopfhörer-Grenze, dann schaltet der Ausgang um.
- Beim Ziehen gilt wieder Lautsprecher mit der normalen Grenze.

#### AP 4.5 Leise-Zeiten (Sonnet), umsetzt CUJ 15

Ergebnis: Teilautomat Leise-Zeiten auf der Box.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/quiet.py` | neu | Teilautomat Leise-Zeiten (Projektplan, Abschnitt 5.7): Fenster mit Wirkung „leiser“ oder „stumm“; die Einstellung kommt über das Thema `tobibox/config` (Teil derselben Konfiguration), lokale Kopie für offline; bei nicht vertrauenswürdiger Zeit gilt die kleinste „leiser“-Grenze aller Fenster, nie stumm. |
| `box/tests/unit/test_quiet.py` | neu | Fenstergrenzen mit simulierter Uhr; Zeit nicht vertrauenswürdig; stumm beginnt während der Wiedergabe; stumm endet bei liegender Figur (nichts startet). |

Abnahme AP 4.5:

- Alle Zeilen der Tabelle „Leise-Zeiten“ haben einen Test.
- Bei nicht vertrauenswürdiger Zeit wird nie stumm geschaltet.

#### AP 4.6 Gute-Nacht-Karte (Sonnet), umsetzt CUJ 14

Ergebnis: Teilautomat Gute Nacht.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/bedtime.py` | neu | Teilautomat Gute Nacht: Timer mit Ausblenden über die Lautstärke-Regel; Dauer von Timer und Ausblenden aus `config.json` (Vorschlag 30 min und 60 s); die Karte ist ein Eintrag Typ `aktion` in `config.json`; funktioniert am Mac. |
| `box/tests/unit/test_bedtime.py` | neu | Timer läuft ab, Lautstärke blendet aus, Wiedergabe endet; andere Figur während des Timers; Abheben während des Ausblendens. |

Abnahme AP 4.6:

- Alle Zeilen der Tabelle „Gute Nacht“ haben einen Test.
- Die Lautstärke liegt beim Ausblenden nie über der wirksamen Grenze.

#### AP 4.7 HA: Leise-Zeiten und Gute-Nacht-Einstellungen (Sonnet)

Ergebnis: Tobias stellt Leise-Zeiten und Gute-Nacht-Dauern in der HA-Seite ein.
Sie gehen in `tobibox/config`. Dieses AP ist das einzige in Stufe 4, das die
HA-Dateien ändert.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `homeassistant/custom_components/tobibox/store.py` | änd. | Prüfung und Speicherung der Leise-Zeiten und Gute-Nacht-Einstellungen. |
| `homeassistant/custom_components/tobibox/websocket_api.py` | änd. | Befehle zum Lesen und Setzen (Vertrag W wird dafür ergänzt). |
| `homeassistant/custom_components/tobibox/services.yaml` | änd. | Aktionen für Leise-Zeiten und Gute-Nacht-Einstellungen. |
| `homeassistant/custom_components/tobibox/frontend/tobibox-panel.js` | änd. | Eingabe der Leise-Zeiten und der Gute-Nacht-Dauern. |
| `homeassistant/tests/test_quiet_settings.py` | neu | Ungültige Fenster werden abgelehnt; Änderung erhöht die Revision und geht an `tobibox/config`. |
| `homeassistant/tests/frontend/panel_quiet.test.mjs` | neu | Seite ruft die neuen Befehle mit den richtigen Feldern auf. |

Abnahme AP 4.7:

- Alle HA-Tests sind grün.
- Eine Änderung in der Seite erscheint als neue Revision in `tobibox/config`.

#### AP 4.8 Integration Stufe 4 (Sonnet)

Ergebnis: Alle Hardware-Funktionen sind im Dienst verdrahtet und am Mac per
Simulation vorführbar.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/core.py` | änd. | `quiet`, `bedtime`, `idle` in die Liste der Teilautomaten eintragen; Konflikt-Tabelle vollständig. |
| `box/src/tobibox/app.py` | änd. | `led`, `controls`, `headphones`, `idle` verdrahten. |
| `box/src/tobibox/sim.py` | änd. | Ausgang „Ring-Zustand“ (Terminal, Protokoll); Eingänge Tasten und Drehregler per Tastatur, Eingang „Stecker“. |
| `box/src/tobibox/cli.py` | änd. | `tobibox sim key`, `tobibox sim headphones`, `tobibox sim time`. |
| `box/tests/cuj/test_cuj14_gute_nacht.py` | neu | Karte auflegen nach Abheben der Serien-Figur, Timer, Ausblenden, Ende. |
| `box/tests/cuj/test_cuj15_leise_zeiten.py` | neu | Leise-Zeiten über die Konfiguration. |
| `box/tests/cuj/test_cuj16_leerlauf.py` | neu | Leerlauf-Abschaltung. |
| `box/tests/cuj/test_cuj17_kopfhoerer.py` | neu | Kopfhörer rein und raus. |
| `box/tests/cuj/test_cuj18_led_ring.py` | neu | Ring-Zustände im Terminal und im Protokoll. |
| `box/tests/cuj/test_cuj19_tasten.py` | neu | Tasten, Drehregler und Hauptknopf, darunter Entscheidung E. |
| `box/tests/cuj/test_konflikte.py` | neu | Jede Zeile der Konflikt-Tabelle als Test. |

Abnahme AP 4.8:

- Alle CUJ-Tests 14 bis 19 und `test_konflikte.py` sind grün.
- Alle früheren Tests sind weiter grün.

**Abnahme Stufe 4**

- Jede Funktion ist am Mac per Simulation vorführbar.
- Die Konflikt-Tabelle aus „Kern-Zustände“ ist als Tests grün, mit diesen Fällen:
  - Folge zu Ende bei liegender Figur
  - Hauptknopf kurz bei beendeter Folge mit liegender Figur (nächste Folge spielt) und ohne Figur (normale Funktion)
  - stumm gegen Lernmodus
  - Stumm-Beginn und Stumm-Ende
  - Gute Nacht mit neuer Figur
  - Abheben beim Ausblenden
  - Figurwechsel bei Leser-Unterbrechung
  - Leerlauf gegen Sync, Update und Lernmodus
  - Tiefstand während Sync
  - mehrere Grenzen
- Die echte Hardware ersetzt später nur den Simulations-Treiber; dann folgt die **Messung der Lautstärke am Verstärker**.

### Dokumente, die am Ende nachgezogen werden

| Datei | Änderung |
|---|---|
| `docs/plan/stueckliste-und-psp.md`, `docs/plan/psp-baum.html` | Projektplan (Stückliste und Arbeitspaket-Baum) nachziehen: Punkte, die durch dieses Design ersetzt sind, neu fassen |
| `docs/designs/box-software.md` | angenommene Fassung dieses Dokuments |
| `CLAUDE.md` | Verweis auf Verträge und Arbeitsweise je Stufe |
