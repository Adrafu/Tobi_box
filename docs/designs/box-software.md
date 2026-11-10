# Tobi Box — Box-Software (Prototyp und Zielsystem)

*   **Autor:** Tobias (Projektleitung: Claude)
*   **Status:** Approved (05.11.2026, nach EGM-Review Stufen 5–9)

*   **Datum:** 2026-11-05
*   **Änderung 05.11.:** Entscheidung F eingearbeitet (Tobies: Folge oder Serie, Folgen mit mehreren Tracks). Alle Änderungen sind mit „(Entscheidung F, 05.11.)“ markiert.
*   **Änderung 07.11.:** Entscheidung H eingearbeitet (Lernmodus wartet still). Die Änderungen sind mit „(Entscheidung H, 07.11.)“ markiert.
*   **Änderung 09.11.:** Entscheidung I eingearbeitet (ein kleiner Rest gilt als fertig gehört). Die Änderungen sind mit „(Entscheidung I, 09.11.)“ markiert.
*   **Änderung 09.11.:** Entscheidung J eingearbeitet (Töne folgen der Lautstärke des Hörspiels). Die Änderungen sind mit „(Entscheidung J, 09.11.)“ markiert.
*   **Änderung 09.11.:** Entscheidung L eingearbeitet (nie zwei Sachen gleichzeitig). Die Änderungen sind mit „(Entscheidung L, 09.11.)“ markiert.
*   **Änderung 09.11.:** Entscheidung M eingearbeitet (Einsortieren nach Metadaten, vollautomatisch mit Korrektur) und die Vorgaben der Projektleitung zu Vertrag W (`docs/protocol/ha-websocket-v1.md`). Die Änderungen sind mit „(Entscheidung M, 09.11.)“ markiert.
*   **Änderung 09.11.:** Entscheidung N eingearbeitet (Lesezeichen je Tobie mit Ablauf). Die Änderungen sind mit „(Entscheidung N, 09.11.)“ markiert.
*   **Änderung 09.11.:** Entscheidungen O und P eingearbeitet (Leerlauf zählt auch mit liegendem Tobie; nicht lesbarer Kopfhörer-Kontakt gilt als „Kopfhörer steckt“ für die Grenze) und die Befunde des Code-Reviews zu AP 3.7 und 4.8 (`docs/egm/software-prototyp/code_review_stufe3a_4.md`). Die Änderungen sind mit „(Entscheidung O, 09.11.)“, „(Entscheidung P, 09.11.)“ bzw. „(Befund B…, 09.11.)“ markiert.
*   **Änderung 10.11.:** Ein- und Ausschalten, **Schritt 1** eingearbeitet (EGM `docs/egm/ein-aus/`, Entwurf Rev. 2, Entscheidungen R1–R11 in `resolve.md`; es ersetzt die Ladestations-Folgen aus `docs/egm/ladestation/software_folgen.md` und das ruhende EGM `docs/egm/start-am-lader/`). Neu: Zustände *Spielt / Bereit / Aus* (Namen für die Pi-Zustände `aktiv` / `leerlauf` / ausgeschaltet), Frist 10 min nur ohne Strom und ab dem Abnehmen, am Strom immer bereit (Sockel, Kabel, Powerbank), „Lader“ = Strom aus jeder Quelle (Leser-Zeile `LADER`, Vorrang Leser), Ton `lader` beim Andocken, früher Start-Ton durch einen Frühdienst (unter „stumm“ gar nicht, unter „leiser“ mit der Grenze des Fensters, R10). Es entfällt die Wiederholung des Start-Syncs am Lader (AP 4.8). Betroffen: Entscheidung O, CUJ 10, 15, 16, 18, 20, neu 21 bis 25, Baustein 2, Tabelle „Strom / Leerlauf“, „Netz, Sync, Strom“, AP 4.3 und neue Arbeitspakete E1-0 bis E1-8. Die Änderungen sind mit „(Ein/Aus, 10.11.)“ markiert. **Schritt 2** (Wecken durch Tobie, Magnet und Strom über den ESP32, Lauflicht, Ring-Weiche, Schlaf, LPCD, `WAKE`, `SLEEP`, `CFG`, `RING_PI`) folgt nach den Messungen am Breadboard und ist hier nicht eingearbeitet; wo ein Satz darauf verweist, steht „folgt mit Schritt 2“.
*   **Änderung 10.11.:** Entscheidung Q eingearbeitet (ohne aufliegenden Tobie startet nichts: Hauptknopf kurz, Vor und Zurück geben dann nur den Hinweiston; es entfällt „ohne Tobie gilt Play / Pause“). Die Änderungen sind mit „(Entscheidung Q, 10.11.)“ markiert.
*   **Änderung 10.11.:** Entscheidung R eingearbeitet (Durchsage beim Auflegen der Gute-Nacht-Karte, neuer Ton `gute_nacht`: „Gute Nacht! Ich spiele noch ein bisschen.“; unter „stumm“ keine Durchsage, die Karte wirkt trotzdem). Betroffen: CUJ 14, Tabelle „Gute Nacht“. Die Änderungen sind mit „(Entscheidung R, 10.11.)“ markiert.
*   **Grundlage:** `concepts_brief.md` (gleicher Ordner) inkl. Entscheidungen
    Runde 1 und 2

--------------------------------------------------------------------------------

## Überblick

Die Tobi Box ist eine mobile NFC-Audiobox für zwei Kleinkinder. Ein Kind legt
einen Tobie auf (ein echter Tonie oder eine NFC-Karte), und die Box spielt
das zugehörige Hörspiel vom eigenen Bestand. Die meisten Tobies spielen eine
einzelne Folge, manche eine ganze Serie (Entscheidung F, 05.11.). Dieses Dokument beschreibt die
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

*   **Tobie** (Mehrzahl **Tobies**) (Entscheidung F, 05.11.): Tonie oder NFC-Karte, die auf die Box
    gelegt wird. Beide zusammen heißen Tobie, in allen Dokumenten und Texten
    für Eltern.
*   **Glossar-Zeile (Entscheidung F, 05.11.):** Im Code heißt ein Tobie aus historischen Gründen `figur`.
*   **Kennung (UID):** Seriennummer des Chips im Tobie. Sie ist auf dem Tobie fest und das
    Einzige, woran die Box ihn erkennt.
*   **Serie:** Ordner mit Folgen, die zusammen eine Geschichte oder Reihe
    bilden. Ein einzelnes Hörspiel ohne Reihe liegt ebenfalls in einem
    Serien-Ordner (z. B. einer Serie „Einzelfolgen“); dafür gibt es keine
    Sonderregel (Entscheidung F, 05.11.).
*   **Folge** (Entscheidung F, 05.11.): Ein Hörspiel in einer Serie. Auf der Platte ist sie
    entweder **eine Audiodatei** im Serien-Ordner oder ein **Unterordner mit
    mehreren Tracks** (z. B. ein CD-Rip). Der Name der Folge ist der Dateiname
    bzw. der Name des Unterordners.
*   **Track** (Entscheidung F, 05.11.): Eine Audiodatei einer Folge. Eine Folge aus einer Datei hat
    einen Track. Die Tracks eines Folgen-Ordners sind nach der natürlichen
    Sortierung geordnet (Regeln: „Datenmodell und Dateien“).
*   **Ziel** (Entscheidung F, 05.11.): Worauf ein Tobie zeigt: `serie` (die ganze Serie, jedes
    Auflegen macht mit der nächsten ungehörten Folge weiter), `folge` (genau
    eine Folge einer Serie) oder `aktion`. Kurz: **Serien-Tobie**,
    **Folgen-Tobie**.
*   **Überraschungs-Serie:** Serie für unbekannte und gesperrte Tobies. Sie
    ist nur an `typ=ueberraschung` in ihrer `serie.json` erkennbar; eine feste
    ID gibt es nicht. Sie verhält sich wie ein Ziel `serie` (Entscheidung F, 05.11.).
*   **Zuordnung:** Eintrag „Kennung → Ziel“ (Serie, einzelne Folge oder Aktion,
    z. B. Status). Tobias legt sie in Home Assistant an und wählt dabei den
    Typ (Entscheidung F, 05.11.).
*   **Resume:** Die Box merkt sich je Serie (bei Folgen-Tobies je Folge), wo
    sie aufgehört hat, und spielt beim erneuten Auflegen dort weiter (Entscheidung F, 05.11.).
*   **Zeiger:** Der gespeicherte Resume-Zustand: Folge, Track und Position
    (Sekunden im Track) (Entscheidung F, 05.11.). Je Serie ein Zeiger (Serien-Tobies) und je Serie
    und Folge ein Zeiger (Folgen-Tobies). Nach dem Ende einer Folge zeigt der
    Zeiger einer Serie auf die nächste Folge, der Zeiger einer Folge auf ihren
    Anfang (jeweils Track 0, Position 0). Regeln: siehe „Datenmodell und
    Dateien“.
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
*   **Lernmodus:** Modus, den Tobias in HA startet: Der nächste Tobie, der
    innerhalb von 2 min aufgelegt wird, wird dem gewählten Ziel (Serie oder
    Folge) zugeordnet (CUJ 7b) (Entscheidung F, 05.11.).
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
auch mit geborgten Tobies, unterwegs ohne Netz und nach einem leeren Akku.

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
    - Ton spätestens **1,0 s** nach dem Auflegen eines bekannten Tobies
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
*   Automatisches Erkennen, welcher Tobie ein Tonie ist (Zuordnung einmal pro
    Exemplar). Geprüft in `research_tonie_erkennung.md`: Auf dem Chip steht
    nur eine Seriennummer; die echte Toniebox fragt die Tonie-Cloud, und eine
    öffentliche Liste „Kennung → Tobie“ gibt es nicht.
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
    „Datenmodell und Dateien“. Eine Folge kann auch ein Unterordner mit
    mehreren Tracks sein (Entscheidung F, 05.11.).
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
    Baustein 3). Umsetzung: AP 3.9 (Stufe 3b). Auf diesen Zielwert −18 LUFS sind auch die
    Box-Töne und die Testmedien gebracht (Entscheidung J, 09.11.).
*   **Lautstärke und Gute-Nacht-Karte:** Lautstärke-Regel in Stufe 1,
    Gute-Nacht-Karte in Stufe 4.
*   **Hardware (Ziel 9):** Alle Hardware-Funktionen werden jetzt mit
    Simulation gebaut (Stufe 4).
*   **Entscheidung A — Pause nach jeder Folge:** Nach dem Ende einer Folge
    springt der Zeiger auf die nächste (nach der letzten auf Folge 1; bei einem
    Folgen-Tobie auf den Anfang derselben Folge, F5) und die
    Box pausiert, auch wenn der Tobie noch liegt; weiter geht es erst nach
    erneutem Auflegen oder mit einem kurzen Druck auf den Hauptknopf
    (Entscheidung E).
*   **Entscheidung B — Ende eines „stumm“-Fensters:** Liegt dann ein Tobie
    auf, startet nichts von selbst; das Kind legt den Tobie erneut auf.
*   **Entscheidung C — Hotspot:** Es gibt keine Datenbegrenzung je Sync; im
    Hotspot gilt nur die Akku-Regel.
*   **Entscheidung D — NAS-Rechte:** HA hat vollen Schreibzugriff auf die
    NAS-Freigabe (`medien/`, `export/`, `releases/`); Tobias ist der einzige
    Benutzer. Die Paket-Signatur (`minisign`) bleibt und schützt davor, dass
    ein manipuliertes HA oder NAS Code auf die Boxen bringt.
*   **Entscheidung E — Hauptknopf nach Folgenende (05.11.):** Ist eine Folge zu
    Ende und der Tobie liegt noch auf der Box, spielt ein **kurzer Druck auf den
    Hauptknopf die nächste Folge** (der Zeiger zeigt schon darauf; bei einem
    Folgen-Tobie dieselbe Folge noch einmal von vorn, F6). ~~Ohne Tobie
    auf der Box behält der Hauptknopf seine normale Funktion (Play / Pause).~~
    **Ersetzt durch Entscheidung Q (10.11.):** Ohne aufliegenden Tobie startet
    nichts, nur der Hinweiston.
*   **Entscheidung Q — Ohne aufliegenden Tobie startet nichts (10.11.):**
    Hauptknopf kurz, Vor und Zurück starten **ohne aufliegenden Tobie** keine
    Wiedergabe, auch kein Fortsetzen nach dem Abheben und auch nicht in
    `beendet`, `pausiert` oder `leer`. Stattdessen spielt der Hinweiston
    `hinweis` (unter „stumm“ gilt die bestehende stumm-Regel). Die Lautstärke
    wirkt weiter, Abheben pausiert wie bisher. Gilt für echte und simulierte
    Tobies.
*   **Entscheidung F — Tobies: Folge oder Serie (05.11.):** Die meisten Tobies
    spielen eine einzelne Folge, manche eine ganze Serie. Tobias hat entschieden (Entscheidung F, 05.11.):
    *   **F1 — Begriff:** Tonies und NFC-Karten zusammen heißen **Tobie**
        (Mehrzahl Tobies), in allen Dokumenten und Texten für Eltern (HA-Seite,
        Protokoll für Eltern). Im Code heißt ein Tobie aus historischen Gründen
        `figur`; Namen wie `Aufgelegt` und `figur_liegt` bleiben.
    *   **F2 — Ziel:** Eine Zuordnung zeigt auf `serie` (jedes Auflegen setzt die
        nächste ungehörte Folge fort), `folge` (genau eine Folge einer Serie) oder
        `aktion`. In HA wählt Tobias den Typ beim Zuordnen, auch im Lernmodus.
        `config.json` bekommt dafür `ziel` (`schema_version` 2 mit Migration).
    *   **F3 — Folge auf der Platte:** Eine Folge ist eine Audiodatei im
        Serien-Ordner oder ein Unterordner mit mehreren Tracks (z. B. CD-Rip).
        Die Tracks eines Folgen-Ordners ordnet die vorhandene natürliche
        Sortierung; Dotfiles werden ignoriert, es gilt dieselbe Endungsliste.
        `serie.json.folgen` nennt Folgen mit Namen (Dateiname oder Ordnername).
        Ein Hörspiel ohne Serie liegt in einem beliebigen Serien-Ordner (z. B.
        „Einzelfolgen“), ohne Sonderregel.
    *   **F4 — Abspielen:** Eine Folge spielt alle ihre Tracks ohne Pause. Die
        Regel „Pause nach jeder Folge“ (Entscheidung A) gilt am Ende der ganzen
        Folge, nicht nach jedem Track. Die MPD-Warteschlange enthält nur die
        Tracks der aktuellen Folge; Folgenende heißt: MPD stoppt nach dem letzten
        Track. Der Player unterscheidet `TrackWechsel` und `FolgeZuEnde`.
    *   **F5 — Zeiger:** Position = (Folge, Track, Sekunden im Track). Für `serie`
        gibt es einen Zeiger je Serie (wie bisher, jetzt mit Track), für `folge`
        einen Zeiger je (Serie, Folge). Ist die Folge zu Ende, springt dieser
        Zeiger auf Track 0 / 0 s zurück: Das nächste Auflegen spielt sie **von
        vorn**. `resume.json` bekommt `schema_version` 2 mit Migration (alte
        Einträge = Track 0).
    *   **F6 — Tasten:** Vor / Zurück springen nach **Track** innerhalb der
        Folge. Zurück in den ersten 3 s eines Tracks → voriger Track, sonst
        aktuellen Track neu starten. Beim letzten Track geht Vor bei `serie` zur
        nächsten Folge, bei `folge` passiert nichts (Hinweiston). Hauptknopf
        kurz in `beendet`: `serie` → nächste Folge, `folge` → dieselbe Folge von
        vorn. Zurück in `beendet`: spielt die eben beendete Folge von vorn
        (beide Typen). Die Regeln unter „stumm“ bleiben (nichts startet).
    *   **F7 — Überraschungs-Serie:** verhält sich wie ein Ziel `serie`.
*   **Entscheidung H — Lernmodus wartet still (07.11.):** Bisher startete ein im
    Lernmodus aufgelegter unbekannter Tobie sofort die Überraschungs-Serie mit dem
    Ton `unbekannt`; mit echtem HA wäre das 1 bis 3 s zu hören gewesen. Neu
    (Entscheidung H, 07.11.):
    *   **H1 — Nur der Lernton:** Wird im Zustand `lernt` ein Tobie aufgelegt
        (bekannt oder unbekannt), kommt nur der Ton `lernen_ende`. Die Box spielt
        nichts, auch keine Überraschung und keinen Ton `unbekannt`, und wartet auf HA.
    *   **H2 — Ende des Wartens:** Die Zuordnung trifft ein (neue Konfiguration mit
        diesem Tobie): das neue Ziel startet sofort. HA lehnt ab (`bestaetigt` mit
        `grund` „abgelehnt“) oder 10 s ohne Antwort: Die Box verhält sich wie bei einem
        normalen Auflegen (bekannt → sein Ziel, unbekannt → Überraschung mit Ton).
        Kommt die Zuordnung nach den 10 s doch, gilt das bisherige Verhalten bei einer
        neuen Konfiguration mit liegendem Tobie. Abheben beendet das Warten, es spielt
        nichts. Die Sitzung merkt sich beim Beginn das bisherige Ziel des Tobies
        (unbekannt: keins). Nur eine Konfiguration, die diesem Tobie ein **anderes**
        Ziel gibt, beendet das Warten; eine andere Konfiguration (anderer Tobie geändert,
        gleiche Zuordnung) wirkt auf die Sitzung wie sonst, beendet das Warten aber nicht.
        Endet das Warten durch „abgelehnt“ und ist der Tobie unbekannt, meldet die Box ihn
        erneut als `unbekannt` (die Outbox hat den Eintrag mit der Bestätigung gelöscht).
        Nach der Frist verhält sich eine Aktionskarte wie bei einem normalen Auflegen und
        löst ihre Aktion aus. *Gewollt:* Braucht Tobias in HA für die Rückfrage beim
        Überschreiben länger als 10 s, spielt ein bekannter Tobie zuerst sein altes Ziel
        und wechselt mit der späteren Zuordnung auf das neue (wie bei jeder
        Konfigurationsänderung mit liegendem Tobie). (Entscheidung H, 07.11.)
    *   **H3 — Tasten:** Während des Wartens wirkt die Lautstärke; Hauptknopf, Vor und
        Zurück bewirken nichts.
    *   **H4 — Unverändert:** `unknown.json` und Melden laufen wie bisher (nur
        Wiedergabe und der Ton `unbekannt` warten). Regel „stumm“ und Entscheidung G
        bleiben; ein Dienst-Neustart während des Wartens lässt den Tobie `pausiert`.
        Die Wartezeit ist die Konstante `LERN_ANTWORT_FRIST_S` = 10 s auf `mono`.
*   **Entscheidung I — Ein kleiner Rest gilt als fertig gehört (09.11.):** Anlass beim
    Test am Mac: Ein Tobie wurde im Abspann abgehoben, bei 122,0 s von 123,6 s. Jedes
    neue Auflegen spielte wegen des 3-s-Rücksprungs ab 119 s nur die letzten Sekunden,
    also Stille, und wurde wieder abgehoben; das Ende der Folge wurde nie erreicht.
    Neu (Entscheidung I, 09.11.):
    *   **I1 — Regel:** Wird die Wiedergabe an einem gespeicherten Zeiger fortgesetzt
        und fehlen bis zum Ende der **ganzen Folge** (alle Tracks zusammen) weniger als
        `REST_FERTIG_S` = 15 s, gilt die Folge als fertig gehört. Gemessen wird am
        gespeicherten Zeiger, vor dem 3-s-Rücksprung. Fortsetzen heißt: Auflegen
        (auch beim Einschalten mit liegendem Tobie), Hauptknopf kurz im Zustand
        `pausiert` und Fortsetzen nach einem Dienst-Neustart. Folgen-Tobie: Die Folge
        beginnt von vorn. Serien-Tobie: Es spielt sofort die nächste Folge von vorn,
        nach der letzten Folge Folge 1 (dieselbe Zeigerlogik wie bei Folgenende).
        Überraschungs-Serie: ebenso (sie verhält sich wie ein Ziel `serie`).
    *   **I2 — Ausnahme:** Folgen, die insgesamt kürzer als `REST_REGEL_MIN_FOLGE_S` =
        60 s sind, sind ausgenommen. Kennt die Box die Dauer einer Folge nicht, gilt die
        Regel auch nicht; das steht im Protokoll (`rest_regel`, Ergebnis `dauer_unbekannt`). Ebenso, wenn die
        Position des Zeigers mehr als 2 s hinter dem Ende ihres Tracks liegt (die Dauer stimmt dann nicht;
        Code-Review, 09.11.).
    *   **I3 — Unverändert:** Die Regel ändert nichts am Speichern des Zeigers. Pause nach
        jeder Folge (Entscheidung A), Dienst-Neustart bleibt pausiert (Entscheidung G, erst
        der Hauptknopf oder neues Auflegen setzt fort, dann greift die Regel) und
        Entscheidung H gelten wie bisher.
    *   **I4 — Protokoll:** Greift die Regel, schreibt die Box eine INFO-Zeile `rest_regel`
        mit `rest_s` (Rest in Sekunden), der Folge und der Folge, die spielt.
    *   **I5 — Woher die Dauer kommt:** Die Bibliothek liest die Dauer jedes Tracks beim
        Laden aus den Kopfdaten der Dateien (WAV, MP3, M4A/M4B, FLAC; Baustein
        `audiodauer`). Andere Formate: Dauer unbekannt, ebenso MP3 mit wechselnder Bitrate ohne Xing-/VBRI-Kopf. Die Sitzung bleibt rein: Die Dauern
        stehen in `Serie.dauern`. MPD wird dafür nicht gefragt.

*   **Entscheidung J — Die Töne folgen der Lautstärke des Hörspiels (09.11.):** Anlass beim
    Test am Mac: Die Box-Töne waren viel lauter als das Hörspiel, das Hörspiel „ultra leise“.
    Ein Gegentest mit einer gesprochenen Testfolge (gleiche Stimme, gleicher Dateipegel wie die
    Ansage `start`) war ebenso leise. Es lag also an der Wiedergabe, nicht an den Dateien.
    Ursache: Töne liefen mit festem Pegel 40 % **linear** (−8 dB). Das Hörspiel läuft über
    MPD mit Lautstärke 20 % (Start) auf der **exponentiellen** Kennlinie des Software-Mixers
    (MPD 0.24: `g = (exp(p/25) − 1) / (exp(4) − 1)`, 20 % sind −33 dB). Der Unterschied war
    rund 25 dB. Zusätzlich lagen die Melodie-Töne bei −8,5 LUFS und die Sprach-Töne zufällig
    bei −17 bis −20 LUFS, während ReplayGain die Hörspiele auf −18 LUFS bringt.
    Neu (Entscheidung J, 09.11.):
    *   **J1 — Pegel:** Ein Ton spielt mit der **aktuellen Lautstärke der Sitzung** nach allen
        Grenzen, mindestens 10 (`TON_MINDEST`): `pegel = min(grenze, max(10, lautstaerke))`.
        Die Grenzen (Kopfhörer, „leiser“, Maximum) gelten weiter und stehen über der Untergrenze.
        `hinweis`: `min(grenze, max(10, min(hinweis_pegel, lautstaerke)))`, Vorgabe `hinweis_pegel` 15.
        *Nachtrag (Code-Review, 09.11.):* Die Grenze gewinnt immer (Gehörschutz); die Untergrenze 10 gilt nur,
        solange sie unter der Grenze liegt, auch beim Hinweiston.
        Die Untergrenze des Hinweistons steigt von 5 auf 10, weil 5 % auf der Kennlinie von MPD
        rund −48 dB sind und nicht mehr zu hören.
    *   **J2 — Gleiche Kennlinie:** Die Skalierung der Tondateien in Python (`skaliere_wav`) benutzt
        dieselbe Kennlinie wie die Wiedergabe des Hörspiels. Sie ist je Plattform verschieden und
        steht in der Konfiguration (`[toene] kennlinie`, `softvol_bereich_db`): Mac
        `mpd_software` (Vorgabe), Pi `alsa_softvol`. Formeln und Quellen: `core-interface.md`, 8.1.
    *   **J3 — Pfad des Pegels:** `app.py` führt Grenze und Lautstärke aus dem Zustand des Kerns nach, **ohne** die
        Rampen `ausblenden` und `gute_nacht` (Code-Review, 09.11.: sonst wären Töne nach dem Ausblenden unhörbar).
        Der Pegel entsteht erst, wenn ein Ton an der Reihe ist, nicht beim Einreihen. Der Kern
        bleibt rein und kennt keine Tonpegel. `ton_pegel` in `config.json` hat keine Wirkung
        mehr (das Feld bleibt gültig); `hinweis_pegel` gilt weiter.
    *   **J4 — Lautheit der Töne und Testmedien:** Die Box-Töne (`box/sounds/`,
        `box/sounds/sprache/`) und die gesprochenen Testmedien (`box/medien-sprache/`) liegen bei
        −18 LUFS, dem Zielwert von `rsgain` (D6). Erzeugt von `box/tools/make_sounds.py` und
        `box/tools/make_sprache.py`, gemessen mit `box/tools/lautheit.py` (`ffmpeg`, EBU R128),
        festgehalten in `box/lautheit.json`. Die MP3 der Testmedien tragen ReplayGain-Tags wie von
        `rsgain`. MPD wendet ReplayGain an (Modus Track); ohne Tags dämpft es eine Datei um
        `replaygain_missing_preamp` (−6 dB), das Hörspiel ohne Tags wäre dann 6 dB leiser als die Töne.
    *   **J5 — Pi:** Die Töne laufen am Pi über ein zweites `softvol`-Gerät mit demselben `max_dB` und
        einem eigenen, auf 100 % stehenden Regler. So gilt die harte Kappe auch für Töne, und die
        Lautstärke wirkt nur einmal (in Python). Die Kennlinie des Pi ist aus dem Quelltext von MPD
        und ALSA abgeleitet; ob sie am Gerät stimmt, zeigt der Pi-Probelauf.
    *   **J6 — Eigene Dateien am Mac:** Eigene Hörspiele ohne ReplayGain-Tags (z. B. Tobias'
        `zaehlen.mp3`) können leiser oder lauter sein als die normalisierten Testmedien. Auf der Box
        gleicht `rsgain` das aus (D6). Am Mac normalisiert Tobias sie bei Bedarf selbst
        (`docs/betrieb/mac-prototyp.md`).

*   **Entscheidung L — Es spielen nie zwei Sachen gleichzeitig (09.11.):** Anlass beim Test am
    Mac mit den Sprach-Tönen: Im Lernmodus kam „Lernmodus beendet.“ gleichzeitig mit „Test-Serie, Folge
    drei.“, und „Diesen Tobie kenne ich noch nicht …“ überlappte sich mit der Überraschungs-Serie. Ursache:
    Töne liefen als Hintergrundaufgaben neben MPD; der Kern gibt Ton und `Abspielen` im selben Aufruf aus,
    und beide wurden sofort ausgeführt.
    Neu (Entscheidung L, 09.11.):
    *   **L1 — Ton vor Hörspiel:** Enthält eine Ausgabe des Kerns Töne und `Abspielen`, spielen zuerst die
        Töne bis zum Ende, einzeln und in der Reihenfolge der Ausgabe. Erst danach startet die Wiedergabe.
        Das gilt für den unbekannten Tobie, das Ende des Lernmodus, die Status-Karte und alle anderen
        Fälle. Läuft noch ein Ton aus einem früheren Aufruf, wartet der Start auch auf ihn.
    *   **L2 — Ton während das Hörspiel läuft:** Die Box hält MPD an, spielt den Ton und setzt danach an
        **genau derselben Stelle** fort, ohne den 3-s-Rücksprung. Für diese kurze Pause wird kein Zeiger
        gespeichert, und der Status zeigt „spielt“, nicht „pausiert“. Mehrere Töne hintereinander halten MPD
        nur einmal an.
    *   **L3 — Abheben und andere Befehle während eines Tons:** Wird der Tobie während eines Tons
        abgehoben, startet die Wiedergabe danach nicht. Der Ton läuft **zu Ende** und wird nicht abgebrochen
        (kurze Rückmeldung; ein abgebrochenes Wort klingt wie ein Fehler; der Kern kennt keine Töne).
        Ein späteres `Pausieren` (auch Hauptknopf, „stumm“, Gute Nacht) oder ein neuer Start verwirft einen
        noch wartenden Start. Zusätzlich prüft der wartende Start vor dem Beginn die Wiedergabe-Generation
        `gen` und den Zustand der Sitzung (`gen` allein genügt nicht: Abheben erhöht sie nicht). So überholt
        kein verzögerter Start eine spätere Pause.
    *   **L4 — Zeitbudget:** Beim normalen Auflegen eines bekannten Tobies gibt es keinen Ton. Der Start
        läuft sofort, ohne Warten und ohne eigene Aufgabe; das Ziel unter 1 s (`docs/timing.md`) ändert
        sich nicht. Wo ein Ton kommt, dauert es um den Ton länger bis zum Hörspiel; das ist gewollt.
    *   **L5 — Zeitlimit:** Die Dauer eines Tons ist das Ende des Abspielprogramms (`afplay`, `aplay`), keine
        Schätzung. Ein Ton ist auf 10 s begrenzt (`TON_MAX_S`); dann wird das Programm beendet, und die
        Wiedergabe startet trotzdem.
    *   **L6 — Wo die Regel gilt:** Der Kern bleibt rein und unverändert; Rang der Befehle (`Abspielen` vor
        `TonSpielen`) und Konfliktregeln bleiben. Die Regel gilt in `app.py` (Reihenfolge der Ausführung,
        wartender Start), `sounds.py` (eine Spur, Haken am Anfang und Ende einer Tonfolge) und `player.py`
        (kurze Pause für einen Ton). Verträge: `core-interface.md`, 6.5 Punkt 6, 8.1 und Punkt 32.
        *Nachtrag (Code-Review, 09.11.):* Die kurze Pause endet verlässlich bei `Pausieren`, `Abspielen`, Verbindungsverlust
        und Klemmung; ein Ton mitten in einem Start wartet auf den Start; zwischen zwei Tonfolgen blitzt das alte
        Hörspiel nicht auf (`core-interface.md`, 6.5 Punkt 6e).

*   **Entscheidung M — Einsortieren nach Metadaten, vollautomatisch mit Korrektur (09.11.):**
    Tobias will Hörbücher und Hörspiele „wie bei Plex“ ablegen, nicht von Hand in Serien
    sortieren. Neu (Entscheidung M, 09.11.); die Regeln stehen testbar in
    `docs/protocol/ha-websocket-v1.md`, Abschnitt 11:
    *   **M1 — Eingang:** Tobias legt einen Ordner (z. B. einen Hörbuch-Download) in den
        **Eingangsordner** `tobibox/eingang/` auf dem NAS (neben `medien/`, `export/`,
        `releases/`). Ein **Upload über die Seite** geht ebenfalls dorthin und durchläuft
        dieselbe Einsortierung (die Seite kann eine Serie als Vorgabe mitgeben).
    *   **M2 — Tags lesen:** Die HA-Integration liest mit `ffprobe` Album, Album-Interpret,
        Serien-Tags (`series`, `grouping`, `MVNM`/`movement_name` bei m4b, `TIT1`),
        Track- und Disc-Nummer, Titel, Datum und eine Folgen-Nummer im Albumnamen
        („Folge 12“, „Teil 2“, …).
    *   **M3 — Automatisch einsortieren:** **Album = eine Folge**, bei mehreren Dateien ein
        Folgen-Ordner mit Tracks (Entscheidung F). **Serie** aus Serien-Tag, sonst
        Album-Interpret; Alben derselben Serie werden zusammengeführt (Vergleich ohne
        Groß-/Kleinschreibung und Satzzeichen). **Folgen** in der Serie nach
        Folgen-Nummer, sonst Erscheinungsdatum, sonst Eingangsreihenfolge; **Tracks** nach
        Disc und Track, sonst natürliche Sortierung der Dateinamen. Danach legt sie
        `serie.json` an bzw. ergänzt sie (Anzeigenamen aus den Tags) und verschiebt die
        Dateien in die Medienstruktur.
    *   **M4 — Korrigieren:** Die Seite zeigt, was erkannt wurde. Tobias kann Namen ändern
        (nur **Anzeigenamen**, Dateinamen bleiben, Zeiger gehen nie verloren), die Serie
        einer Folge wechseln, die Reihenfolge ändern und zwei Serien zusammenführen.
        Fehlen Tags, nimmt HA Ordner- und Dateinamen und markiert den Eintrag als „bitte
        prüfen“.
    *   **M5 — Kopierschutz, Defekte, Doppelte:** Kopiergeschützte oder defekte Dateien
        kommen **nicht in die Medien**; sie bleiben im Eingang mit Hinweis (D5). Gleicher
        Inhalt (Prüfsumme) wird erkannt und verworfen (Papierkorb) mit Hinweis; gleicher
        Name mit anderem Inhalt erhält automatisch ein Suffix.
    *   **M6 — Box unverändert:** Die Medienstruktur auf den Boxen bleibt (Serien-Ordner mit
        `serie.json`); der Box-Code weiß nichts davon. **Nicht gesynct** werden
        `_upload/`, `_papierkorb/` und `eingang/` (AP 3.4, AP 3.5).
    *   **M7 — Tobie-Namen und Löschen:** Ein Tobie kann einen **Namen** tragen (optionales
        Feld `name` je Zuordnung, die Box ignoriert es). Eine Serie löschen geht über den
        Papierkorb; zeigen Tobies auf eine Folge oder Serie, die gelöscht wird, fragt die
        Seite vorher mit Anzahl und Namen der Tobies (die Zuordnung bleibt, die Box spielt
        bis zur Wiederherstellung die Überraschung).
    *   **M8 — Folgen:** D4 (Serien anlegen und umbenennen, Folgen sortieren und löschen,
        Audiodateien vom Handy hochladen, Überraschungs-Serie befüllen) bleibt; „Hochladen“
        heißt jetzt „in den Eingang“. Die Überraschungs-Serie kann die Seite anlegen, wenn
        es keine gibt; als Ziel einer Zuordnung ist sie verboten.

*   **Entscheidung O — Leerlauf zählt auch mit liegendem Tobie (09.11.):** Leerlauf heißt: 20 min lang wird nichts
    gespielt, **egal ob ein Tobie liegt**. Anlass (Review, B5): Nach „Gute Nacht“ oder einem „stumm“-Fenster liegt der
    Tobie noch, und die Box blieb die ganze Nacht an, bis der Akku am Morgen leer war. Es gelten weiter die Ausnahmen
    Sync, Update und Lernmodus (die Box wartet), und Bedienung an der Box setzt den Zähler zurück. (Ein/Aus, 10.11.: Die Frist ist jetzt
    10 min statt 20 min und zählt nur ohne Strom, siehe „Ein/Aus, Schritt 1“ unten.) Morgens beim
    Einschalten spielt ein liegender Tobie wie bisher sofort weiter (Entscheidung G). Der Ring zeigt die Pause bei
    liegendem Tobie auch im Leerlauf weiter. Vertrag: `core-interface.md`, Abschnitt 9, Punkt 9.

*   **Entscheidung P — Nicht lesbarer Kopfhörer-Kontakt: die Kopfhörer-Grenze gilt (09.11.):** Ist der Schaltkontakt der
    Buchse nicht lesbar (`gpioget` fehlt, falscher Pin, fehlende Rechte), gilt die Kopfhörer-Grenze. Das schützt die
    Ohren; die Grenze gilt, bis der Kontakt wieder lesbar ist, und auch beim Start, solange die erste Messung fehlt.
    Der Ausgang bleibt, wie er ist. HA bekommt einen Hinweis (`event` `fehler`, `code="kopfhoerer_unlesbar"`).
    Anlass (Review, B3): Vorher fiel der Gehörschutz stillschweigend weg. Vertrag: `core-interface.md`, Abschnitt 3.5 und 9, Punkt 15;
    `mqtt-v1.md`, Abschnitt 3.4.

*   **Befunde des Reviews zu AP 3.7 und 4.8 (09.11.), Entscheidungen der Projektleitung:**
    *   **B1 — Herunterfahren ist nicht endgültig.** `power` prüft den Rückgabecode von `systemctl poweroff` bzw. des
        eingestellten Kommandos (und eine Frist von 60 s) und meldet einen Fehler als `HerunterfahrenFehlgeschlagen`;
        `idle` verlässt `herunterfahren`, zählt neu, schreibt ins Protokoll und meldet es HA (`code="herunterfahren_fehlgeschlagen"`).
        Am Mac (Simulation, auch ohne `[strom]`) ist das Herunterfahren nur protokolliert; `idle` kehrt nach 10 s in den normalen
        Zustand zurück.
    *   **B2 — Hauptknopf am Pi.** Der `pisugar-server` hat nach der Dokumentation keinen Befehl für Tastenereignisse. Die Abfrage ist
        hinter `[strom] taste_befehl` verdrahtet (Vorgabe: aus) und **am Pi zu prüfen**; sonst braucht der Hauptknopf `[tasten] pin_haupt`.
        Ohne beides warnt der Dienst beim Start (`docs/betrieb/pisugar-wecker.md`).
    *   **B4 — Kopfhörer-Kontakt lesen.** Vorrang hat `gpiozero` (Pull-up ausdrücklich, kein Prozess je Messung, unabhängig von der
        libgpiod-Version); Rückfall `gpioget --bias=…` mit erkannter Version (1.x: `gpioget <chip> <pin>`, 2.x: `gpioget -c <chip> <pin>`),
        dann höchstens eine Messung je Sekunde.
    *   **B6, B7.** Nach dem Entschluss zum Herunterfahren startet kein zeitgesteuerter Sync mehr; ein Start-Sync am Lader wartet
        (höchstens 30 s) auf die erste Netz-Klasse.
    *   **B9 — Sim-Eingänge nur mit Quelle `sim`.** `sim time`, `key`, `headphones` und die übrigen Eingänge wirken nur, wenn die Quelle
        des Eingangs `sim` ist (Mac) oder `[sim] erlauben = true` gilt. Sonst antwortet `sim` mit `quelle_nicht_sim`, die Oberfläche
        graut den Knopf aus.
    *   **B12, B13, B14, B15, B16.** Der Ton `akku_leer` beim Tiefstand; Töne folgen der „leiser“-Absenkung; `sim regler` geht
        über `Bedienung` wie der Drehregler; die Systemuhr gilt auf einem Pi ohne `[netz]`/`[strom]` nur mit NTP-Synchronisierung
        (`timedatectl`, `/run/systemd/timesync/synchronized`); `UpdateStarten` wird bis Stufe 3b mit „Update kommt mit Stufe 3b.“ abgelehnt.

*   **Entscheidung N — Lesezeichen je Tobie mit Ablauf (09.11.):** Jeder Tobie (genauer: jeder
    Zeiger) behält seine eigene Stelle, auch wenn zwischendurch andere Tobies gespielt haben;
    das war schon so (CUJ 4, `resume.json`). Neu (Entscheidung N, 09.11.); die Regeln stehen
    testbar in `docs/protocol/core-interface.md`, Abschnitt 6.3:
    *   **N1 — Ablauf:** Wurde ein Zeiger länger als `lesezeichen_tage` nicht benutzt, beginnt
        beim Fortsetzen die **Folge** wieder von vorn: Track 0, Position 0. Bei einem
        Serien-Zeiger bleibt die Folge dieselbe, es geht nicht zurück auf Folge 1. Bei einem
        Folgen-Tobie beginnt dieselbe Folge von vorn. „Länger als“ heißt: genau 14 Tage sind noch
        nicht abgelaufen.
    *   **N2 — Einstellung:** Vorgabe 14 Tage, in HA einstellbar, deshalb ein Feld der
        Konfiguration (`config.json`, `lesezeichen_tage`, ganze Zahl 0 bis 365, additiv, Version 2
        bleibt, alte Dateien laden unverändert). `0` heißt: läuft nie ab. Fehlt das Feld, gilt 14.
        Eine eigene Bedienung auf der HA-Seite kommt mit den Einstellungen in Stufe 4; Vertrag W
        reserviert das Feld dafür.
    *   **N3 — Nur bei sicherer Uhr:** Die Regel gilt nur, wenn die Uhr sicher ist
        (`jetzt.zeit_ok`, siehe „Uhr und Zeitquelle“). Ist die Uhr unsicher, läuft nichts ab.
        Der Kern bleibt rein: Die Wanduhr kommt über `jetzt`.
    *   **N4 — Gemessen ab der letzten Benutzung:** Jeder Zeiger in `resume.json` trägt den
        Zeitpunkt seiner letzten Benutzung (`benutzt_am`, UTC, optional). Benutzung heißt: zuletzt
        gespeichert beim Spielen (alle 30 s), Pausieren oder Abheben. Ein alter Zeiger ohne
        `benutzt_am` läuft nie ab; er bekommt den Zeitstempel beim nächsten Speichern. Bei unsicherer
        Uhr wird kein neuer Zeitstempel geschrieben, ein vorhandener bleibt.
    *   **N5 — Ort der Regel:** Dieselbe Stelle wie die Restregel (Entscheidung I), also bei allen
        Wegen des Fortsetzens: Auflegen, Einschalten, Hauptknopf kurz in `pausiert`, nach einem
        Dienst-Neustart. **Reihenfolge:** zuerst der Ablauf. Ist der Zeiger abgelaufen, beginnt
        die Folge von vorn, und die Restregel entfällt.
    *   **N6 — Protokoll:** Eine INFO-Zeile `lesezeichen_abgelaufen` mit `alter_tage`.

- **Nachtrag 05.11. (Stufe-0-Verträge):** Ein Leser-Neustart startet nie von selbst eine Wiedergabe; nach einem bestätigten Leserverlust (> 3 s) bleibt die Box pausiert, auch wenn der Tobie danach wieder gemeldet wird – das Kind legt neu auf. Lesefehler gelten bis 5 s als „Tobie liegt“; fehlende Serie → Überraschungs-Serie; „stumm“ sperrt auch Knöpfe; MPD-Verlust bis 5 s wird überbrückt. Maßgeblich sind die Verträge in `docs/protocol/` und `docs/data-model.md`.

*   **Ein/Aus, Schritt 1 (10.11.), Entscheidungen von Tobias R4, R8, R9, R10, R11 und Festlegungen der Projektleitung** (`docs/egm/ein-aus/resolve.md`;
    Vertrag: `core-interface.md` Abschnitt 9, Punkt 9; `reader-v1.md`; `data-model.md`):
    *   **Drei Zustände.** *Spielt* (Pi-Zustand `aktiv`, Hörspiel läuft), *Bereit* (`leerlauf`: nichts wird gespielt, der Dienst läuft), *Aus* (Pi stromlos). Die
        technischen Namen in `ZustandMelden.strom` bleiben.
    *   **Frist 10 min, nur ohne Strom (R9).** Bereit läuft ohne Frist, solange Strom am Eingang liegt (Sockel, Kabel, Powerbank). Ohne Strom fährt die Box
        10 min nach dem letzten Spielen oder Bedienen herunter; nach dem Abnehmen vom Strom beginnt die Frist **ab dem Abnehmen**.
    *   **Am Sockel immer an (R8).** `Hauptknopf` lang fährt herunter; am Sockel startet die Box gleich wieder (mit Schritt 2 durch den Leser über `STROM_IN`;
        bis dahin hängt es an „Einschalten bei Strom“ des PiSugar). Ausschalten am Sockel heißt: abnehmen.
    *   **„Lader“ = Strom aus jeder Quelle; zwei Quellen.** `pisugar-server` und der Leser (Zeile `LADER`); bei Widerspruch gilt der Leser. „Unbekannt“ gilt nach 60 s
        als „kein Strom“. Die erste bekannte Messung löst nur den Sync-Check aus, nie Ton oder Ring.
    *   **Ton `lader` beim Andocken einer laufenden Box (R4).** Kurz; nicht in Leise-Zeiten („leiser“, „stumm“), nicht bei unsicherer Uhr, nicht im Lernmodus,
        nicht beim Hören (dann nur der Ring, Entscheidung L). Sperre 10 s für jede Rückmeldung (Ring, Ton, Sync) gegen Wackelkontakt.
    *   **Früher Start-Ton (R10, Abweichung von Rev. 2 des Entwurfs).** Ein Frühdienst spielt `start`, sobald der Ton-Ausgang da ist, ohne den Box-Dienst
        aufzuhalten. Er klingt wie heute: unter „stumm“ gar nicht, unter „leiser“ leise (mit der Grenze des Fensters), sonst normal. Nie zwei Töne zugleich: eine
        Marke unter `/run` und eine feste Reihenfolge. Nach einem Dienst-Neustart ohne Ausschalten spielt der Kern `start` wie bisher (Entscheidung G).
    *   **Entfällt:** die Wiederholung des Start-Syncs am Lader (alle 10 min, höchstens 6-mal, AP 4.8); am Sockel ist die Box ohnehin bereit,
        den nächsten Sync-Anstoß geben der Takt, das Andocken und HA. Einen „Kurz-Modus“ am Lader (Vorschlag im ruhenden EGM `start-am-lader`) gibt es nicht.
    *   **Schritt 1 ist freigegeben (R11).** Schritt 2 (Verträge B1 bis B15, Arbeitspakete E2-x) erst nach den Messungen.

## Offene Fragen

*   **Leser-Rückkanal:** Soll der Box-Dienst dem ESP32 etwas
    zurückschicken (z. B. Poll-Intervall ändern, Neustart)? Im Prototyp
    reserviert, nicht gebaut.
*   **Audio-Rückmeldungen:** Offen ist die genaue Liste der Töne und wie sie
    klingen. Gebraucht werden Töne für: Start, unbekannter Tobie / Überraschung,
    Fehler, Lernmodus Beginn und Ende, Status-Karte in Ordnung / Fehler,
    Akku fast leer, Tobie erkannt bei „stumm“. Bis zur Entscheidung gibt es
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
(Entscheidung E), Tobies als Folge oder Serie (Entscheidung F), Lernmodus wartet still (Entscheidung H), kleiner Rest gilt als fertig gehört (Entscheidung I), Töne folgen der Lautstärke (Entscheidung J), nie zwei Sachen gleichzeitig (Entscheidung L), Einsortieren nach Metadaten (Entscheidung M), Lesezeichen mit Ablauf (Entscheidung N), Leerlauf mit liegendem Tobie (Entscheidung O), nicht lesbarer Kopfhörer-Kontakt (Entscheidung P), Ein- und Ausschalten Schritt 1 (R4, R8 bis R11, 10.11.), Schnittstellen und Datenformate (Stufe 0), die Befunde R1 bis
R18 des Reviews Stufe 9.

## Risiken

| Risiko | Auswirkung | Gegenmaßnahme | Wann geprüft |
|---|---|---|---|
| Tonie-Entsperrung klappt nicht bei jedem Exemplar | Der Tobie spielt die Überraschungs-Serie statt seiner eigenen | Rückfall auf Überraschungs-Serie (CUJ 6); Test mit Tobias' Tobies | Stufe 1, mit Tobias' Tobies |
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
| Entsperren geborgter Tonies | Der Privacy-Modus fremder Tobies wird aufgehoben | Die Box liest nur die Kennung, mit Tobias' eigenem Passwort, und schreibt keine Nutzdaten; der Privacy-Modus bleibt aber aufgehoben, bis eine Toniebox ihn wieder setzt | Stufe 1 |
| Firmware-Datei veröffentlicht | Das Passwort könnte aus dem Flash ausgelesen werden | Firmware-Binary nicht veröffentlichen; CI baut nur mit Platzhalter-Passwort | laufend |
| Tailscale-Schlüssel der Box läuft ab | Box fällt unbemerkt aus dem Netz | Schlüsselablauf für die Box-Knoten abschalten (AP 3.5); HA zeigt den Netzstand | Stufe 3a, Einrichtung |

## Abläufe (CUJs)

Begriffe: siehe Abschnitt „Begriffe“ oben. Zeitgrenzen: siehe Ziel 2.
Zustände, Übergänge und Konflikte: siehe „Kern-Zustände“.

### CUJ 1: Bekannten Tobie auflegen

*   **Given**: Der Tobie ist einem Ziel zugeordnet (Serie oder einzelne Folge),
    die Dateien liegen lokal, es gibt keinen gespeicherten Zeiger für dieses
    Ziel auf dieser Box (Entscheidung F, 05.11.).
*   **When**: Kind legt den Tobie mittig auf.
*   **Then**: Innerhalb der Zeitgrenze (Ziel 2) startet bei einem
    Serien-Tobie Folge 1 der Serie, bei einem Folgen-Tobie die zugeordnete Folge,
    jeweils mit dem ersten Track. Hat die Folge mehrere Tracks, spielen sie ohne
    Pause nacheinander (Entscheidung F, 05.11.). Das Protokoll zeigt die Kette gelesen → entprellt →
    zugeordnet → spielt mit einer Vorgangs-ID.

### CUJ 2: Abheben

*   **Given**: Ein Tobie liegt, sein Ziel spielt.
*   **When**: Kind nimmt den Tobie weg.
*   **Then**: Innerhalb der Zeitgrenze (Ziel 2) Pause. Der Zeiger (Folge, Track und
    Position) ist für das Ziel des Tobies gespeichert (Entscheidung F, 05.11.).

### CUJ 3: Tobie wieder auflegen (Resume)

*   **Given**: Für das Ziel des Tobies gibt es einen gespeicherten Zeiger (je
    Serie bei einem Serien-Tobie, je Serie und Folge bei einem
    Folgen-Tobie) (Entscheidung F, 05.11.).
*   **When**: Kind legt einen Tobie dieses Ziels auf — auch nach Neustart oder
    leerem Akku.
*   **Then**: Wiedergabe läuft an der gespeicherten Stelle (Track und Position)
    weiter (mit Rücksprung, siehe „Datenmodell und Dateien“). Nach dem Ende der **ganzen
    Folge** (nicht nach jedem Track) pausiert die Box, auch wenn der Tobie noch
    liegt (Entscheidung F, 05.11.). Bei einem Serien-Tobie steht der Zeiger dann auf der nächsten
    Folge (nach der letzten Folge auf Folge 1), erster Track; sie spielt erst,
    wenn der Tobie (oder ein anderer Tobie derselben Serie) neu aufgelegt wird
    oder der Hauptknopf kurz gedrückt wird (Entscheidung E). Bei einem
    Folgen-Tobie steht der Zeiger auf dem Anfang derselben Folge: Das nächste
    Auflegen (oder der Hauptknopf kurz) spielt sie **von vorn**.
*   **Kleiner Rest (Entscheidung I, 09.11.)**: Fehlen am gespeicherten Zeiger bis zum Ende
    der ganzen Folge (alle Tracks) weniger als 15 s, gilt die Folge als fertig gehört
    (der Tobie wurde im Abspann abgehoben). Ein Folgen-Tobie beginnt die Folge von vorn,
    ein Serien-Tobie spielt sofort die nächste Folge von vorn (nach der letzten Folge
    Folge 1). Das gilt beim Auflegen, beim Einschalten, beim Hauptknopf in `pausiert` und
    nach einem Dienst-Neustart. Folgen unter 60 s und Folgen mit unbekannter Dauer sind
    ausgenommen.
*   **Lesezeichen mit Ablauf (Entscheidung N, 09.11.)**: Wurde der Zeiger länger als
    `lesezeichen_tage` (Vorgabe 14) nicht benutzt, beginnt die Folge von vorn: Track 0,
    Position 0, ohne Rücksprung. Ein Serien-Tobie bleibt in derselben Folge (nicht zurück auf
    Folge 1), ein Folgen-Tobie beginnt dieselbe Folge von vorn. `0` heißt: läuft nie ab. Die
    Regel gilt nur bei sicherer Uhr und nur für Zeiger mit Zeitstempel, an denselben Stellen wie
    die Restregel (Auflegen, Einschalten, Hauptknopf kurz, nach Dienst-Neustart) und geht ihr
    voran. Protokoll: `lesezeichen_abgelaufen` mit `alter_tage`.

### CUJ 4: Anderen Tobie auflegen

*   **Given**: Ein Ziel A (Serie oder Folge) ist pausiert oder spielt, ein Tobie
    mit Ziel B wird aufgelegt.
*   **When**: Kind wechselt den Tobie.
*   **Then**: Der Zeiger von A bleibt gespeichert. B läuft an seinem Zeiger
    weiter (Serie nach einer beendeten Folge: die nächste Folge; Folge nach
    ihrem Ende: von vorn). Ohne Zeiger beginnt eine Serie bei Folge 1, eine
    Folge am Anfang, jeweils beim ersten Track (Zeigerregeln: siehe „Datenmodell
    und Dateien“) (Entscheidung F, 05.11.).
*   **Lesezeichen je Tobie (Entscheidung N, 09.11.)**: Jeder Zeiger behält seine eigene Stelle,
    auch wenn andere Tobies dazwischen gespielt haben, und er altert für sich: Ob die Folge
    beim Auflegen von vorn beginnt, hängt allein davon ab, wie lange **dieser** Zeiger nicht
    benutzt wurde (mehr als `lesezeichen_tage`, Vorgabe 14). Serien-Zeiger und Folgen-Zeiger
    derselben Folge laufen getrennt ab.

### CUJ 5: NFC-Karte

*   **Given**: Eine NTAG215-Karte ist einem Ziel (Serie oder Folge) zugeordnet.
*   **When**: Kind legt die Karte auf.
*   **Then**: Verhalten wie CUJ 1–4.

### CUJ 6: Gesperrter Tonie (Passwort unbekannt)

*   **Given**: Ein Tonie im Privacy-Modus, der sich mit unserem Passwort nicht
    entsperren lässt.
*   **When**: Kind legt ihn auf.
*   **Then**: Die Überraschungs-Serie spielt. Kurze Aussetzer starten sie nicht
    neu. Nicht zuordenbar (keine Kennung).

### CUJ 7a: Unbekannter Tobie, Zuordnung danach (Weg A)

*   **Given**: Lesbarer Tobie ohne Zuordnung. Box offline oder online.
*   **When**: Kind legt ihn auf.
*   **Then**: Die Überraschungs-Serie spielt sofort. Die Box merkt sich die
    Kennung und meldet sie an HA, sobald HA erreichbar ist; sie löscht den
    Eintrag erst, wenn HA den Empfang bestätigt hat (Antwort auf `…/ack`, siehe
    „MQTT-Schnittstelle“). HA zeigt „neuer Tobie“
    (gleiche Kennung von beiden Boxen = ein Eintrag). Tobias wählt in HA den Typ (**Serie** oder
    **einzelne Folge**, bei Folge zusätzlich die Folge) (Entscheidung F, 05.11.) und tippt das Ziel an; HA
    schreibt die Zuordnung. Die Box holt sie und wechselt, wenn der Tobie noch
    liegt, sofort auf das Ziel (bei einer Folge von deren Anfang).

### CUJ 7b: Lernmodus (Weg B)

*   **Given**: Box ist online. Tobias wählt in HA „Jetzt kommt ein neuer
    Tobie“, eine Box, den Typ (**Serie** oder **Folge**) und die Serie, bei
    Folge zusätzlich die Folge (Entscheidung F, 05.11.).
*   **When**: Innerhalb von 2 min wird ein Tobie auf diese Box aufgelegt.
*   **Then**: Box meldet die Kennung an HA, HA schreibt die Zuordnung, das
    gewählte Ziel spielt (Serie oder Folge). Ist der Tobie schon zugeordnet, fragt HA vor dem Überschreiben
    nach; wird der Tobie währenddessen abgehoben, ändert das nichts, denn die
    Zuordnung hängt an der gemeldeten Kennung. **Wartet still (Entscheidung H, 07.11.):**
    Beim Auflegen kommt nur der Lernton; die Box spielt nichts (keine Überraschung, kein
    Ton `unbekannt`), bis die Zuordnung eintrifft (dann startet das Ziel sofort). Lehnt HA
    ab oder kommt nach 10 s keine Antwort, verhält sich die Box wie bei einem normalen
    Auflegen (ein unbekannter Tobie wird nach „abgelehnt“ erneut gemeldet). Abheben beendet das Warten. Lautstärke wirkt, Hauptknopf, Vor und Zurück
    bewirken in dieser Zeit nichts. Ist die Rückfrage von HA beim Überschreiben länger als 10 s, spielt ein bekannter
    Tobie zuerst sein altes Ziel und wechselt mit der Zuordnung (gewollt, Entscheidung H, 07.11.). Ohne Tobie endet der Lernmodus
    nach 2 min (die Frist misst die Box); Abbruch jederzeit in HA. Beginn und
    Ende sind hörbar. Ist die Box gerade stumm geschaltet (CUJ 15), lernt sie
    trotzdem und bestätigt mit dem leisen Ton, spielt aber nicht.

### CUJ 8: Tobie am Rand oder kurz verrutscht

*   **Given**: Ein Tobie spielt.
*   **When**: Er verrutscht, die Lesungen setzen bis 1,0 s aus, oder am Rand
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
    Abgleich), die laufende Wiedergabe stockt nicht, und ein Tobie, der
    während des Abgleichs aufgelegt wird, startet innerhalb der Zeitgrenze.
    HA zeigt Stand und Zeitpunkt.

### CUJ 10: Software-Update

*   **Given**: Box daheim, am Lader, spielt nicht (Bedingungen: siehe
    „Update“). **(Ein/Aus, 10.11.)** „Am Lader“ heißt Strom am Eingang aus jeder Quelle; am Sockel ist die Box immer bereit,
    HA kann das Update also jederzeit schicken.
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
*   **Then**: Sie meldet gesammelte unbekannte Tobies und Status an HA, holt
    neue Zuordnungen und (nach den Regeln aus CUJ 9) neue Folgen.

### CUJ 13: Leser fällt aus und kommt wieder

*   **Given**: Die Box läuft.
*   **When**: Der ESP32 startet neu oder die USB-Verbindung ist kurz weg.
*   **Then**: Der Box-Dienst merkt es (fehlender Herzschlag), protokolliert
    es, verbindet sich selbst neu. `HELLO` setzt den Zähler `seq` zurück und
    versetzt den Kern in „Leser-Zustand unbekannt“. Kommt derselbe Tobie
    wieder, läuft die Serie weiter, ohne neu zu starten. Wurde der Tobie
    während der Unterbrechung abgehoben, pausiert die Box spätestens 1,5 s
    nach dem Wächter-Alarm (Tabelle „Wiedergabe-Sitzung“).

### CUJ 14: Gute-Nacht-Karte

*   **Given**: Eine Serie spielt. Die Gute-Nacht-Karte ist als Aktion
    zugeordnet. Dauer von Timer und Ausblenden sind in HA eingestellt
    (Vorschlag 30 min und 60 s).
*   **When**: Tobias nimmt die Serien-Tobie weg (Pause) und legt die
    Gute-Nacht-Karte auf; danach legt er die Serien-Tobie wieder auf.
*   **Then**: Mit der Karte startet der Timer; die Serie spielt weiter. Nach
    Ablauf blendet die Lautstärke aus (Regel: „Lautstärke“ in Baustein 3),
    dann endet die Wiedergabe (Pause mit gespeichertem Zeiger). Das funktioniert auch am Mac. Konflikte mit anderen
    Regeln: siehe „Kern-Zustände“.
*   **Durchsage (Entscheidung R, 10.11.):** Beim Auflegen der Karte spielt die Box den Ton `gute_nacht`
    („Gute Nacht! Ich spiele noch ein bisschen.“). Es gelten die Regeln aller Töne: normaler Ton-Pegel
    (Entscheidung J), unter „leiser“ mit der Grenze des Fensters, unter „stumm“ **keine** Durchsage (auch kein
    Hinweiston als Ersatz); die Karte wirkt trotzdem, der Timer startet. Spielt gerade etwas, hält der Ton das
    Hörspiel kurz an (Entscheidung L; die Karte ist ein Tobie, die Serie wird beim Auflegen ohnehin pausiert);
    nie zwei Töne gleichzeitig. Legt man die Karte bei laufendem Timer noch einmal auf, kommt die Durchsage noch
    einmal; beim Ausblenden wird die Karte ignoriert, dann gibt es auch keine Durchsage. Im Lernmodus bleibt alles
    wie bisher (die Karte wartet still, die Aktion und mit ihr die Durchsage folgen erst nach dem Warten).

### CUJ 15: Leise-Zeiten

*   **Given**: Tobias hat in HA Leise-Zeiten frei eingestellt: beliebig viele
    Zeitfenster (Wochentage, von–bis), je Fenster eine Wirkung — **leiser**
    (mit eigener Lautstärke-Grenze) oder **stumm** (keine Wiedergabe).
    HA hat die Einstellung mit der übrigen Konfiguration (`tobibox/config`) an
    beide Boxen verteilt; jede Box hält eine Kopie.
*   **When**: Die Uhrzeit erreicht ein Fenster, oder ein Kind legt in einem
    Fenster einen Tobie auf.
*   **Then**: Bei „leiser“ gilt die Fenster-Grenze nach der Regel in
    „Lautstärke“ (Baustein 3); eine lautere laufende Wiedergabe wird sanft
    abgesenkt. Bei „stumm“ pausiert die Box und spielt nicht; ein kurzer
    leiser Hinweiston zeigt, dass der Tobie erkannt wurde. Nach dem Fenster
    gilt wieder die normale Grenze. Endet ein „stumm“-Fenster, während ein Tobie liegt, startet nichts von selbst; das Kind muss den Tobie erneut
    auflegen. Ohne Netz gilt die letzte Kopie. Ist die Uhrzeit nicht
    vertrauenswürdig, gilt die kleinste „leiser“-Grenze aller Fenster, nie
    stumm (siehe „Uhr und Zeitquelle“).
*   **Töne und Anzeige beim Ein- und Ausschalten (Ein/Aus, 10.11.):**
    *   Der Ton `lader` (Box wird angedockt, CUJ 25) entfällt unter „leiser“, unter „stumm“, bei unsicherer Uhr und im Lernmodus.
    *   Der **frühe Start-Ton** (CUJ 21) klingt wie heute (R10): unter „stumm“ **gar nicht**, unter „leiser“ **leise** (mit der Grenze des Fensters),
        sonst normal. Bei unsicherer Uhr gilt wie im Kern die kleinste „leiser“-Grenze, nie „stumm“. Anders als heute spielt die Box unter „stumm“
        beim Einschalten auch keinen Hinweiston; der Hinweiston gehört weiter zum Auflegen eines Tobies.
    *   Die **Akku-Anzeige** am Ring ist normal 15 % hell, unter „leiser“ 5 %, unter „stumm“ 3 % (mindestens die erste der 31 Stufen des Rings);
        für sie gilt der Faktor 0,4 von „stumm“ nicht.
    *   Das Lauflicht beim Wecken (tags normal, nachts gedimmt) folgt mit Schritt 2.

### CUJ 16: Leerlauf-Abschaltung (Bereit und Aus; Ein/Aus, 10.11.)

*   **Given**: Es läuft keine Wiedergabe (die Box ist *Bereit*), und es liegt **kein Strom** am Eingang der Box. Ein liegender Tobie ändert daran nichts.
*   **When**: 10 min vergehen, ohne dass etwas gespielt oder bedient wird.
*   **Then**: Die Box fährt herunter (Zeiger gespeichert) — außer es läuft ein Sync, ein Update oder der Lernmodus: dann wartet sie.
    **Mit Strom bleibt die Box bereit**, solange er anliegt (Sockel, Kabel, Powerbank, Auto): Die Frist gibt es dort nicht, die Box schaltet nie von selbst ab.
    **Kommt Strom, wird die Frist verworfen. Wird die Box abgenommen, beginnt die Frist ab dem Abnehmen** (R9), auch wenn vorher schon lange nichts
    gespielt wurde. Beim Andocken prüft die Box, ob ein Sync ansteht (CUJ 25); eine Wiederholung dieses Syncs gibt es nicht mehr.
    Bedienung an der Box (Taste, Drehregler, Hauptknopf kurz, Kopfhörer) beginnt die 10 min neu; HA-Befehle (Sync, Update) tun das nicht
    (09.11., AP 4.8). **Auch ein liegender Tobie hält die Box nicht an:** Wird 10 min lang nichts gespielt, schaltet sie ab
    (Entscheidung O, 09.11.; Frist 10 statt 20 min). Schlägt das Herunterfahren fehl, läuft die Box weiter, der Zähler beginnt neu und HA
    bekommt einen Hinweis (Befund B1). In der Simulation wird das Herunterfahren nur
    protokolliert; nach 10 s ist die Box wieder im normalen Zustand.
*   **Hauptknopf lang** fährt immer herunter, auch am Sockel (R8). Am Sockel startet die Box danach gleich wieder: Ausschalten heißt dort abnehmen.
    Wer die Box aus *Aus* holt: Hauptknopf (PiSugar). Das Wecken durch Tobie, Magnet und Strom über den ESP32 folgt mit Schritt 2; bis dahin hängt
    „Einschalten bei Strom“ am PiSugar.
*   Der Wecker des PiSugar zum nächtlichen Sync am Lader (früher geplant für Stufe 4) wird damit nicht gebraucht: Am Sockel ist die Box ohnehin bereit
    (`docs/betrieb/pisugar-wecker.md` wird nachgezogen).

### CUJ 17: Kopfhörer

*   **Given**: Eine Serie spielt über den Lautsprecher.
*   **When**: Ein Kopfhörer-Stecker wird erkannt (später eingesteckt, am Mac
    simuliert).
*   **Then**: Zuerst gilt die Kopfhörer-Grenze, dann schaltet der Ausgang um
    (Regel: „Lautstärke“ in Baustein 3). Der Lautsprecher schaltet ab. Beim
    Ziehen gilt wieder Lautsprecher mit der normalen Grenze.
*   **Kontakt nicht lesbar (Entscheidung P, 09.11.)**: Kann die Box den Schaltkontakt der Buchse nicht lesen (auch beim Start),
    gilt die Kopfhörer-Grenze, bis er wieder lesbar ist. Der Ausgang bleibt. HA bekommt einen Hinweis (`kopfhoerer_unlesbar`).

### CUJ 18: LED-Ring-Zustände

*   **Given**: Die Box läuft. Der Ring kennt die Zustände läuft, Pause, Akku,
    unbekannte Karte, Aufwachen (Projektplan `docs/plan/`, Abschnitt 5.5.2).
*   **When**: Der Zustand der Box wechselt.
*   **Then**: Der Ring zeigt den passenden Zustand. Die Helligkeit liegt nie
    über 25 %. Am Mac zeigen Terminal und Protokoll denselben Zustand.
*   **Vorschlag, Tobias entscheidet nach Ansicht in der Simulation** (09.11.,
    AP 4.8). Die Farben und Muster stehen als benannte Konstanten oben in
    `box/src/tobibox/led.py`.
    *   Lernmodus: blaues Atmen, 3 s, 8 bis 25 %.
    *   Gute Nacht, nur während der Wiedergabe: warm-oranges Glimmen, 4 s, 3 bis
        8 %, mit dem Ausblende-Faktor multipliziert; danach normale Pause.
    *   Stumm: Der Zustand bleibt, die Helligkeit ×0,4 (ausgenommen die Akku-Anzeige, siehe unten).
    *   Übrige Zustände: läuft grünes Atmen (12 bis 25 %, 6 s); Pause bernstein
        (10 %); unbekannte Karte magenta blinkend (1 s); Aufwachen weißes
        Lauflicht (2 s); Akku als Füllstand (40 LEDs, grün, gelb oder rot, mit
        Strom blau, bei Tiefstand rot blinkend). **(Ein/Aus, 10.11., V6)** „Ladestand“ (beim Andocken, CUJ 25) und „Akku“ (beim Abziehen) sind **dieselbe** Anzeige,
        die Akku-Füllstand-Anzeige; nur die Farbe folgt dem Strom (blau mit Strom, sonst nach Prozent). Wann sie erscheinen darf, gibt `idle` mit dem Befehl
        `AkkuAnzeigen` frei (`core-interface.md`, Abschnitt 4 und 9); beim Start mit Strom zeigt `led` sie nach `Bereit` allein (Start-Anzeige).
    *   **Akku-Anzeige (Ein/Aus, 10.11.):** Sie erscheint 5 s lang beim Andocken und beim Abziehen (spielt ein Hörspiel: 3 s) und auf Anforderung.
        Helligkeit 15 %; unter „leiser“ und solange „Gute Nacht“ läuft 5 %; unter „stumm“ 3 % (mindestens Stufe 1 der 31 Stufen des Rings). Der Faktor
        0,4 von „stumm“ gilt für sie nicht.
    *   **Folgt mit Schritt 2:** Der Ring ist in *Bereit* dunkel (Weiche und Ring-Schalter am ESP32, `led.py` gibt den Ring über `RING_PI` an die Weiche);
        das weiße Lauflicht beim Wecken kommt vom ESP32, danach übernimmt `led.py`; der Deckel 25 % gilt dann in Pi **und** ESP32. Bis dahin
        bleibt der Ring wie oben beschrieben (in *Bereit* mit liegendem Tobie zeigt er weiter die Pause).

### CUJ 19: Tasten und Drehregler

*   **Given**: Eine Folge (oder Serie) spielt oder ist pausiert.
*   **When**: Tobias drückt Vor / Zurück, dreht den Drehregler oder drückt den
    Hauptknopf.
*   **Then**: Vor / Zurück springen nach **Track** innerhalb der aktuellen
    Folge (Entscheidung F, 05.11.). Zurück in den ersten 3 s eines Tracks springt zum vorigen Track,
    sonst startet der aktuelle Track neu (im ersten Track: Neustart des
    Tracks). Beim letzten Track springt Vor bei einem Serien-Tobie zur nächsten
    Folge, bei einem Folgen-Tobie passiert nichts (Hinweiston). Der
    Drehregler ändert die Lautstärke innerhalb der wirksamen Grenze (Regel:
    „Lautstärke“ in Baustein 3). Der Hauptknopf kurz: Play / Pause. Ist eine
    Folge zu Ende und liegt der Tobie noch auf der Box, spielt ein kurzer Druck
    die nächste Folge (Entscheidung E); ohne Tobie auf der Box startet nichts,
    es gibt nur den Hinweiston (Entscheidung Q, 10.11.).
    In `beendet` spielt der Hauptknopf kurz bei einem Serien-Tobie die nächste
    Folge, bei einem Folgen-Tobie dieselbe Folge von vorn; Zurück spielt in
    beiden Fällen die eben beendete Folge von vorn (Entscheidung F, 05.11.). Im „stumm“-Fenster startet
    nichts. Lang: Zeiger speichern und herunterfahren.

### CUJ 20: Tobie liegt schon beim Start

*   **Given**: Die Box ist aus (Akku leer, Strom weg oder ausgeschaltet), ein Tobie liegt auf dem Leser.
    Gilt nur nach einem echten Einschalten (Entscheidung G, 06.11.).
*   **When**: Die Box startet.
*   **Then**: Sobald Leser, Kern und MPD bereit sind, wird der Tobie wie ein
    frisches Auflegen behandelt (CUJ 1 bis 3): bekanntes Ziel spielt am
    Zeiger weiter, unbekannter Tobie startet die Überraschungs-Serie. Die Zeit
    bis „bereit“ hat einen Soll-Wert (Pi-Probelauf).
    **(Ein/Aus, 10.11.)** Der frühe Start-Ton (CUJ 21) ist dann schon gespielt oder bewusst unterlassen; der Kern spielt keinen zweiten `start`
    (`Bereit.fruehton`). Unter „stumm“ startet der liegende Tobie nicht (CUJ 15). Dass der Tobie selbst die ausgeschaltete Box geweckt hat, folgt mit Schritt 2.
*   **Ausnahme: Dienst-Neustart (Entscheidung G, 06.11.)**: Nach einem Neustart des
    Box-Dienstes, ohne dass die Box ausgeschaltet war (Update, Absturz,
    `systemctl restart`), startet ein liegender Tobie **nie** von selbst. Die
    Sitzung bleibt `pausiert` (kein Ton) mit dem Zeiger seines Ziels; Hauptknopf kurz
    (oder Abheben und erneutes Auflegen) spielt am gespeicherten Zeiger. Erkannt
    wird das am Marker `lauf.json` (gleiche Kennung des Starts, siehe Datenmodell).
    Leerer Akku und Stromausfall zählen als Einschalten. **(Ein/Aus, 10.11.)** Bei einem Dienst-Neustart
    klingt der Start-Ton wie heute aus dem Kern; es gibt dann keine Marke des Frühdienstes, keine Lader-Rückmeldung und kein Wecken.

### CUJ 21: Hochfahren mit frühem Start-Ton (Ein/Aus, 10.11.)

*   **Given**: Die Box ist *Aus*.
*   **When**: Sie wird eingeschaltet: Hauptknopf (PiSugar), Strom am Eingang (mit „Einschalten bei Strom“ des PiSugar); Tobie auflegen und Magnet folgen mit Schritt 2.
*   **Then**: (1) Das weiße Lauflicht des ESP32 sofort beim Wecken **folgt mit Schritt 2**. (2) Der Frühdienst spielt `start`, sobald der Ton-Ausgang da ist
    (Ziel höchstens 5 s nach 5 V am Pi), ohne den Box-Dienst aufzuhalten. Er klingt wie heute (R10): unter „stumm“ gar nicht, unter „leiser“ mit der Grenze
    des Fensters, sonst normal (CUJ 15). (3) *Bereit* (Ziel höchstens 8,5 s) übernimmt und spielt **keinen zweiten** Start-Ton; Frühton und Töne des Kerns
    überlagern sich nie. (4) Liegt ein Tobie, spielt er (CUJ 20); unter „stumm“ startet nichts.
*   **Ausnahme Frühdienst fehlt, zu langsam oder gescheitert:** Dann gibt es keine Marke des Frühdienstes (`app` legt bei *Bereit* die Gegenmarke an, der Frühdienst spielt dann nicht mehr, V1), und der Kern spielt `start` wie bisher. Unter „stumm“ bleibt es still: Der Kern spielt dann auch keinen Hinweiston (V5).
*   **Ausnahme Dienst-Neustart:** wie in CUJ 20 (Kern-Ton, keine Marke).
*   **Ausnahme Pi kommt nicht hoch** (kein Lauflicht-Ende, `host_timeout`, Zwangs-Aus): folgt mit Schritt 2.

### CUJ 22: Tobie weckt die ausgeschaltete Box (Ein/Aus, 10.11.)

Folgt mit Schritt 2 (Tobie auflegen und Tonie-Magnet wecken über den ESP32; nur eine Änderung weckt, R3, R6). Entwurf: `docs/egm/ein-aus/design_draft.md`, CUJ 22.

### CUJ 23: Box steht am Sockel bereit (Ein/Aus, 10.11.)

*   **Given**: Strom liegt am Eingang der Box an (Sockel, Kabel, Powerbank, Auto).
*   **When**: Zeit vergeht, nichts wird gespielt.
*   **Then**: Die Box ist *Bereit*, ohne Frist, und fährt **nie von selbst** herunter (nur Hauptknopf lang und Akku-Tiefstand ohne Strom). Ein Tobie, der aufgelegt wird,
    spielt wie sonst (Ziel höchstens 3 s). Das gilt auch, wenn `pisugar-server` hängt, weil der Leser (`LADER`) den Wert liefert; liefert keine Quelle einen Wert, gilt der
    Strom nach 60 s als „kein Strom“. Kommt der Strom, während die Box herunterfährt, startet sie wieder: folgt mit Schritt 2 (Leser); bis dahin entscheidet
    „Einschalten bei Strom“ des PiSugar.

### CUJ 24: Pause ohne Sockel, nach 10 min aus (Ein/Aus, 10.11.)

*   **Given**: Die Box hat keinen Strom am Eingang; nichts wird gespielt oder bedient; kein Lernmodus, kein Sync, kein Update.
*   **When**: 10 min vergehen.
*   **Then**: Zeiger gespeichert, Herunterfahren (CUJ 16). Wird in den 10 min ein Tobie aufgelegt oder etwas bedient, spielt die Box (Tobie: höchstens 3 s) bzw. die Frist
    beginnt neu. Dass der ESP32 danach schläft und ein anderer Tobie während des Herunterfahrens später weckt, folgt mit Schritt 2.

### CUJ 25: Andocken und Abziehen (Ein/Aus, 10.11.)

| Lage | Andocken | Abziehen |
|---|---|---|
| **Aus** | Die Box startet, wenn der PiSugar es kann („Einschalten bei Strom“); mit Schritt 2 durch den ESP32 (`STROM_IN`). Frühton `start` (CUJ 21), nach *Bereit* Ring Ladestand 5 s, Sync prüfen. **Kein** Lader-Ton (erste Messung) | – |
| **Bereit** | Ring Ladestand 5 s, **Ton `lader`** (nicht in „leiser“, „stumm“, bei unsicherer Uhr, im Lernmodus), Sync prüfen (einmal); die Frist wird verworfen | Ring Akku 5 s, kein Ton, kein Sync; die Frist beginnt (10 min **ab jetzt**) |
| **Spielt** | nur Ring 3 s (Entscheidung L: kein Ton neben dem Hörspiel); Sync prüfen | nur Ring 3 s |
| Update läuft | nur Ring, kein Sync, kein Ton | nur Ring |

*   Die **Sperre** `LADER_SPERRE_S` = 10 s gilt für jede Rückmeldung (Ring, Ton, Sync), gerechnet ab der letzten Rückmeldung **oder ab *Bereit***. Ein Wackelkontakt
    löst höchstens eine Rückmeldung je 10 s aus; Strom in den ersten 10 s nach *Bereit* gibt keinen Ton.
*   Die **erste bekannte Messung** des Stroms im laufenden Dienst (auch eine späte) und ein Dienst-Neustart lösen nur den Sync-Check aus, nie Ton oder Ring.
*   Liegt beim Andocken aus *Aus* ein Tobie, spielt er (CUJ 20); nachts schützt „stumm“.

## Technischer Plan

### Überblick der Bausteine

```
 Tobie
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
    Messung in Stufe 1 bestätigt das an Tobias' Tobies.
  - Neue Kennung gilt nach **2 gleichen Lesungen in Folge** (`CONFIRM_READS`).
    Mehr würde die Auflegezeit sprengen.
  - Jede Antwort mit Fehlerbit, falscher Länge oder falscher CRC wird schon in
    der Firmware verworfen (`fehler(bad_response)`), bevor der Entpreller sie sieht.
  - `REMOVED` nach **1,1 s** ohne gültige Lesung des liegenden Tobies.
    Damit: Lücken bis 1,0 s überbrückt, Pause ≤ 1,5 s nach Abheben.
  - Eine andere Kennung, während ein Tobie liegt, wird erst nach
    **3 gleichen Lesungen in Folge** als Wechsel gemeldet (`REMOVED` + `PLACED`,
    `CHANGE_CONFIRM_READS`). Grund: Eine verfälschte Kennung am Rand wurde
    einmal zweimal gleich gelesen (09.11.). Der Wechsel dauert dadurch
    200 ms länger; das Auflegen aus leerem Zustand bleibt bei 2 Lesungen.
- **Gesperrter Tonie**: eigener stabiler Zustand „gesperrt liegt“; gleiche
  Entprell- und Abhebe-Regeln wie bei einer Kennung.

**Gesperrter Tonie.** Tonies enthalten NXP-ICODE-SLIX-L-Chips im Privacy-Modus.
Sie beantworten nur die Anfrage nach einer Zufallszahl, bis sie mit einem
4-Byte-Passwort entsperrt werden. Mit dem richtigen Passwort liefert der Chip
danach seine Kennung. Scheitert das Entsperren, meldet die Firmware `LOCKED`.
Das Passwort liegt nur in der lokalen `config.h` der Firmware, nie im Repo. Die
Box entsperrt nur mit Tobias' eigenem Passwort, liest nur die Kennung und
schreibt keine Nutzdaten auf den Tobie; das gilt auch für geborgte Tobies. Das
Entsperren hebt den Privacy-Modus auf, **bis eine Toniebox ihn wieder setzt**.
Danach antwortet der Tobie wie ein offener Chip; nur das erste Auflegen läuft
über den Entsperrweg. Testfall dafür: „gesperrt → offen“ (gleicher Tobie, danach
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
  Tobias' Tobies nach. Ziel 2 gilt erst als erreicht, wenn die gemessene Summe
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
| `HELLO proto=1 fw=<version> build=<git-hash> pn5180=<fw-version> [caps=<liste>]` | nach Start und auf `PING`; `caps` (optional, Ein/Aus, 10.11.) nennt Fähigkeiten der Firmware, Schritt 1: `strom` |
| `LADER in=<0\|1>` (Ein/Aus, 10.11.) | Strom am Eingang der Box, direkt nach jedem `HELLO` und bei jeder Änderung (entprellt); nur bei `caps` `strom` |
| `PLACED uid=<hex> type=<ntag\|iso15693> tonie=<0\|1> seq=<n>` | Tobie mit Kennung liegt (entprellt) |
| `LOCKED seq=<n>` | gesperrter Tonie liegt |
| `REMOVED seq=<n>` | liegender Tobie ist weg |
| `HB up=<s> present=<0\|1> polls=<n> hits=<n> rejected=<n> errors=<n> cycle_ms=<n>` | Herzschlag alle 2 s; der Wächter im Box-Dienst schlägt nach 5 s an (2 verpasste Herzschläge plus Reserve) |
| `ERR code=<wort> detail=<text>` | Fehler; die vollständige Liste der Codes steht in `reader-v1.md` (z. B. `pn5180_no_response`, `unlock_failed`) |

- Felder des Herzschlags: `up` Sekunden seit Start, `present` liegt gerade ein Tobie, `polls` Abfragezyklen seit Start, `hits` gültige Lesungen, `rejected`
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
| `pointer` | Reine Funktionen für die Zeigerregeln: nächste Folge, Folgenende je Ziel (`serie` / `folge`), Track-Sprünge (Vor / Zurück), fehlende Folge, Rücksprung 3 s (siehe „Datenmodell und Dateien“) (Entscheidung F, 05.11.) | **nein** |
| `protocol` | Zeilen-Parser nach `reader-v1.md`, prüft das Kennungsformat | **nein** |
| `clock` | Uhr als Eingang des Kerns: Wanduhr und monotone Uhr, Zeitquelle | Systemuhr (im Test: simulierte Uhr) |
| `library` | Serien, Folgen und die Tracks jeder Folge (Datei oder Unterordner) aus dem Medienordner lesen (Entscheidung F, 05.11.); die Dauer jedes Tracks aus den Kopfdaten der Dateien (Entscheidung I, 09.11.) | Dateisystem (lesen) |
| `store` | Zustandsdateien atomar lesen/schreiben | Dateisystem |
| `reader` | Serielle öffnen (pyserial in eigenem Thread, Zeilen über eine Warteschlange an die Ereignisschleife), Zeilen parsen, Neuverbinden, Herzschlag überwachen (Wächter: 5 s ohne `HB`) | Serielle |
| `player` | dünne Schicht über MPD (`mpd.asyncio.MPDClient` aus python-mpd2): Abspielen der Tracks einer Folge, Pause, Track und Position, Lautstärke (setzt die wirksame Grenze nur durch); die Player-Ereignisse stehen in `core-interface.md` | MPD |
| `sounds` | kurze Rückmeldetöne über eigenes Kommando (Mac `afplay`, Pi `aplay`) | Prozess |
| `outbox` | Ereignis-Ausgang mit Bestätigung: hält `unknown.json`, gibt Einträge frei, wenn die Bestätigung eintrifft | Dateisystem |
| `ha` | MQTT-Anbindung (paho-mqtt ≥ 2, eigener Thread mit `loop_start`, Übergabe per `call_soon_threadsafe`), HA-Discovery, Zuordnungen empfangen, Status senden, Bestätigungen empfangen | Netz |
| `sync` | rsync vom NAS nach den Regeln, danach MPD-Bibliothek aktualisieren | Prozess, Netz |
| `update`, `selftest` | Update mit Rückfall und eingebaute Prüfroutine (siehe „Update“) | Prozess, Dateisystem |
| `net`, `power` | Netz-Klasse (Heim / Hotspot / offline), Lader (Strom am Eingang, aus jeder Quelle; Ein/Aus, 10.11.), Akkustand, Zeitquelle | System bzw. Simulation |
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
| Leser (`reader`) | `PLACED`, `LOCKED`, `REMOVED`, `HELLO`, `LADER` (Ein/Aus, 10.11.), Wächter-Alarm, Leser-Fehler |
| Player (`player`) | Track-Wechsel, Folge zu Ende, Wiedergabe-Fehler, MPD nicht erreichbar (Felder: `core-interface.md`) (Entscheidung F, 05.11.) |
| HA (`ha`) | neue Konfiguration (Zuordnungen, Leise-Zeiten, Gute-Nacht), Lernmodus starten/abbrechen, Leise-Zeiten, Sync/Update anstoßen |
| Zeitgeber | Takt (mit Zeitstempel), Fristen laufen ab |
| Bedienung (`controls`) | Vor, Zurück, Lautstärke, Hauptknopf kurz/lang |
| Kopfhörer (`headphones`) | Stecker erkannt / gezogen |
| Strom (`power`, Leser) | Lader (Strom am Eingang) an/aus aus zwei Quellen (`pisugar-server`, Leser-Zeile `LADER`; Ein/Aus, 10.11.), Akkustand, Tiefstand, Zeitquelle geändert |
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
Players (Track-Wechsel, Folge zu Ende, Fehler, MPD weg) sind in `core-interface.md` festgelegt,
damit Kern und `player` unabhängig gebaut werden können.

**Ereignis-Ausgang mit Bestätigung.** Meldungen an HA (unbekannte Kennung,
gelernter Tobie) gehen über den Befehl `melden`. Das Modul `outbox` hält sie in
`unknown.json`, bis das Ereignis `bestätigt(id, grund)` eintrifft. In Stufe 2 löst
`tobibox sim ack` die Bestätigung aus, ab Stufe 3a kommt sie von HA über MQTT
(Baustein 4). Der Broker allein bestätigt nichts.

**Abspielen mit MPD.** Die MPD-Warteschlange enthält **nur die Tracks der
aktuellen Folge**, in der Reihenfolge der Folge (eine Datei: ein Track) (Entscheidung F, 05.11.).
Die Tracks spielen ohne Pause nacheinander; wechselt MPD zum nächsten Track,
meldet `player` `TrackWechsel` (der Zeiger bekommt den neuen Track).
**Folgenende** heißt: MPD stoppt nach dem **letzten** Track, `player` meldet
`FolgeZuEnde`, der Kern setzt den Zeiger (Serie: nächste Folge; Folge: Anfang
derselben Folge) und pausiert; MPD startet nie von selbst die nächste Folge.
Resume geschieht per `seek` direkt auf Track und Position (Zeiger minus 3 s im
Track): Es gibt kein kurzes Spielen ab 0:00. Die Latenz dieses Aufrufs misst
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
- **Töne (Entscheidung J, 09.11.):** Ein Ton spielt mit der aktuellen Lautstärke
  der Sitzung (nach allen Grenzen), mindestens 10, auf derselben Kennlinie wie das
  Hörspiel. Er ist nie lauter als die wirksame Grenze. Die Kennlinie hängt von der
  Plattform ab (Mac: Software-Mixer von MPD, Pi: ALSA-`softvol`) und steht in der
  Konfiguration. Siehe Entscheidung J und `core-interface.md`, 8.1.
- **Töne und Hörspiel nie gleichzeitig (Entscheidung L, 09.11.):** Töne laufen einzeln über eine
  Spur. Ein Start nach einem Ton wartet auf das Ende des Tons; ein Ton während des Hörspiels hält es
  kurz an und setzt es an derselben Stelle fort. Siehe Entscheidung L und `core-interface.md`, 6.5 Punkt 6.
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
  Timer, 10 min Leerlauf ohne Strom (seit Ein/Aus, 10.11.; vorher 20 min), 30 s Resume) laufen auf der monotonen Uhr. Die
  Wanduhr braucht nur der Kern der Leise-Zeiten und das Ereignisprotokoll.
- **Zeitquelle:** beim Start die RTC des PiSugar, bei Netz NTP. Ist die Zeit
  nicht vertrauenswürdig (weder RTC noch NTP seit dem Start), gilt die
  **kleinste „leiser“-Grenze aller Fenster, nie stumm** (gibt es kein
  „leiser“-Fenster, gilt die normale Grenze), bis die Zeit stimmt. Die Box meldet
  das an HA und trägt es ins Protokoll (Zeitquelle).
- Am Mac ist die Systemuhr vertrauenswürdig. In Tests ist die Uhr simuliert.
- Auf einem Pi ohne `[netz]` und `[strom]` gilt die Systemuhr nur mit NTP-Synchronisierung als sicher (`timedatectl` bzw.
  `/run/systemd/timesync/synchronized`, Prüfung alle 10 s); sonst ist die Zeit unsicher wie ohne RTC und NTP (Befund B15, 09.11.).
  `tobibox sim time` stellt die Uhr nur, wenn sie nicht von NTP abhängt (Mac). Die Vorgabe richtet sich nach dem Betriebssystem (Linux: Pflicht, Mac: nicht); `[uhr] ntp_pflicht = true|false` überstimmt sie.

#### Kern-Zustände

Der Kern besteht aus vier Teilautomaten, die einzeln testbar sind. Jede
Tabelle ist die Vorlage für die pytest-Tabelle des Teilautomaten. `core`
verbindet sie; Konflikte zwischen ihnen löst die Konflikt-Tabelle am Ende. Jeder
Teilautomat ist eine Funktion `step(zustand, ereignis, jetzt) → (zustand,
befehle)` (Vertrag: `docs/protocol/core-interface.md`).

**1. Wiedergabe-Sitzung** (`session`)

Zustände: `leer` (nichts liegt, nichts läuft), `spielt`, `pausiert`,
`beendet` (Folge zu Ende, Tobie liegt noch), `gehalten` (Tobie liegt, wird
wegen „stumm“ nicht gespielt), `unbekannt` (Leser-Zustand unbekannt).

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `leer`, `pausiert` | `PLACED`, Ziel `serie` oder `folge` bekannt, nicht stumm (Entscheidung F, 05.11.) | Lautstärke setzen, Zeiger des Ziels laden (Serie: Zeiger der Serie; Folge: Zeiger der Folge), Abspielen ab Track und Position | `spielt` |
| `leer`, `pausiert` | `PLACED`, Ziel `serie` oder `folge` bekannt, nicht stumm, am Zeiger fehlen bis zum Ende der ganzen Folge weniger als 15 s (Dauer bekannt, Folge mindestens 60 s) (Entscheidung I, 09.11.) | wie die Zeile oben, aber die Folge gilt als fertig: `serie` → nächste Folge von vorn (nach der letzten Folge 1), `folge` → dieselbe Folge von vorn; Zeiger beim Start nicht speichern; Protokoll `rest_regel` mit `rest_s` | `spielt` |
| `leer`, `pausiert` | `PLACED`, Ziel `serie` oder `folge` bekannt, nicht stumm, sichere Uhr, der Zeiger wurde länger als `lesezeichen_tage` nicht benutzt (Zeitstempel vorhanden, `lesezeichen_tage` > 0) (Entscheidung N, 09.11.) | wie die erste Zeile, aber dieselbe Folge von vorn (Track 0, Position 0, ohne Rücksprung); Vorrang vor der Restregel (die dann entfällt); Zeiger beim Start nicht speichern; Protokoll `lesezeichen_abgelaufen` mit `alter_tage` | `spielt` |
| `leer`, `pausiert` | `PLACED`, Kennung unbekannt | Kennung in `unknown.json`, Überraschungs-Serie abspielen, Ton | `spielt` |
| `leer`, `pausiert` | `LOCKED` | Überraschungs-Serie abspielen | `spielt` |
| `leer`, `pausiert` | `PLACED`, Ziel `aktion` | Aktion auslösen (Status: Tonfolge; Gute Nacht: an Ruhe-Regeln) | unverändert |
| `leer`, `pausiert` | `PLACED`, Ziel `serie` oder `folge` zeigt auf eine fehlende Serie oder Folge (Entscheidung F, 05.11.) | Überraschungs-Serie abspielen, Protokoll `serie_fehlt` bzw. `folge_fehlt`, **kein** Melden (der Tobie ist ja zugeordnet) | `spielt` |
| `leer`, `pausiert` | `PLACED`, stumm aktiv (Serie oder Folge) (Entscheidung F, 05.11.) | leiser Hinweiston, nichts abspielen | `gehalten` |
| `pausiert`, `beendet`, `gehalten` | Hauptknopf kurz, `Vor` oder `Zurück`, solange stumm gilt (Entscheidung F, 05.11.) | nur Hinweiston, nichts startet, Zeiger unverändert (Zeilen „Im stumm-Fenster“ in `core-interface.md`, 9.12) | unverändert |
| `spielt` | `REMOVED` | Pause, Zeiger speichern | `pausiert` |
| `spielt` | `PLACED` andere Kennung | Zeiger der alten Serie speichern, neue Serie wie in den Zeilen oben | `spielt` |
| `spielt` | `TrackWechsel` (MPD spielt den nächsten Track derselben Folge) (Entscheidung F, 05.11.) | Zeiger auf den neuen Track, Position 0, speichern; keine Pause | `spielt` |
| `spielt` | Folge zu Ende (nach dem letzten Track, auch die letzte Folge) (Entscheidung F, 05.11.) | `serie`: Zeiger auf die nächste Folge, Track 0, Position 0 (nach der letzten auf Folge 1); `folge`: Zeiger dieser Folge auf Track 0, Position 0; speichern, Pause, auch wenn der Tobie liegt | `beendet` |
| `spielt` (auch beim Ausblenden wegen stumm und in der MPD-Frist), `unbekannt` | `TrackWechsel` (Entscheidung F, 05.11.) | Zeiger je Ziel auf den neuen Track nachführen und speichern; keine Pause, Ausblenden und Fristen laufen weiter | unverändert |
| `unbekannt`, `spielt` (MPD-Frist) | Folge zu Ende (Entscheidung F, 05.11.) | wie in `spielt`: Zeiger je Ziel setzen und speichern, Pause; Fristen werden verworfen | `beendet` |
| `spielt` (Ausblenden wegen stumm) | Folge zu Ende (Entscheidung F, 05.11.) | Ausblenden beenden, Zeiger je Ziel setzen und speichern, Pause | `gehalten` |
| `spielt`, `unbekannt` | `PlayerPosition` (Entscheidung F, 05.11.) | Position nur übernehmen, wenn Serie, Folge **und** Track zum Zeiger passen, sonst ignorieren; in allen anderen Zuständen wird sie ignoriert, damit eine veraltete Position nie den Zeiger überschreibt | unverändert |
| `spielt`, `pausiert` | `Vor` (Entscheidung F, 05.11.) | nächster Track derselben Folge; beim letzten Track: `serie` → erster Track der nächsten Folge, `folge` → Hinweiston, nichts ändert sich; sonst Zeiger speichern, am neuen Track abspielen | `spielt` (bei Hinweiston unverändert) |
| `spielt`, `pausiert` | `Zurück` (Entscheidung F, 05.11.) | Position im Track < 3 s und es gibt einen vorigen Track → voriger Track; sonst aktuellen Track von vorn; Zeiger speichern, abspielen | `spielt` |
| `beendet` | `REMOVED` | — (die nächste Folge spielt nach erneutem Auflegen) | `pausiert` |
| `beendet` (Tobie liegt) | Hauptknopf kurz oder `Vor` | Lautstärke setzen, ab Zeiger abspielen (Entscheidung E): `serie` → nächste Folge, `folge` → dieselbe Folge von vorn (Entscheidung F, 05.11.) | `spielt` |
| `beendet` (Tobie liegt) | `Zurück` (Entscheidung F, 05.11.) | Lautstärke setzen, die eben beendete Folge von vorn abspielen (beide Typen); einzige Quelle ist die gemerkte, eben beendete Folge; `index` per Nachschlagen in `Serie.folgen`; Zeiger auf diese Folge, Track 0, Position 0, speichern mit Grund `zurueck`. `beendet` wird nicht gespeichert: nach einem Neustart des Dienstes beginnt die Sitzung ohne Wiedergabe mit dem gespeicherten Zeiger | `spielt` |
| `spielt` | Hauptknopf kurz | Pause, Zeiger speichern | `pausiert` |
| `leer`, `pausiert`, `beendet`, `gehalten` (**kein Tobie liegt**) (Entscheidung Q, 10.11.) | Hauptknopf kurz, `Vor`, `Zurück` | nur Hinweiston (`TonSpielen("hinweis")`), nichts startet, auch kein Fortsetzen nach dem Abheben; Lautstärke wirkt weiter | unverändert |
| `pausiert` (Tobie liegt) | Hauptknopf kurz | Abspielen am Zeiger; der Ablauf des Lesezeichens (Entscheidung N, 09.11.) und danach die Restregel (Entscheidung I, 09.11.) gelten wie beim Auflegen, auch nach einem Dienst-Neustart (Entscheidung G) | `spielt` |
| `spielt` | Wächter-Alarm (kein `HB`) | Frist 1,5 s starten | `unbekannt` |
| `unbekannt` | `HELLO` und `PLACED` mit derselben Kennung innerhalb der Frist | nichts, Wiedergabe läuft weiter | `spielt` |
| `unbekannt` | `PLACED` mit neuer Vorgangs-ID (andere Kennung, oder dieselbe nach verlorenem `REMOVED`), Lernmodus `lernt` (Entscheidung H, 07.11.) | Pause (`leser_unbekannt`), Zeiger speichern, dann wie in der Zeile „wartet“ unten: Frist 10 s starten, nichts abspielen | `pausiert` (wartet) |
| `spielt` | `PLACED` dieselbe Kennung, neue Vorgangs-ID (verlorenes `REMOVED`, 9.4), Lernmodus `lernt` (Entscheidung H, 07.11.) | nichts; die Sitzung wartet nicht, die Wiedergabe läuft weiter (der Lernmodus endet durch `learn`, die Kennung wird gemeldet) | `spielt` |
| `unbekannt` | Frist abgelaufen | Pause, Zeiger speichern | `pausiert` |
| `spielt` | stumm beginnt | sanft ausblenden, Pause, Zeiger speichern | `gehalten` |
| `gehalten` | `REMOVED` | — | `pausiert` |
| `gehalten` | stumm endet | nichts; Wiedergabe startet nicht von selbst, erst Abheben und erneutes Auflegen startet sie | `pausiert` |
| `leer`, `pausiert`, `beendet`, `gehalten`, `spielt` | `PLACED` (Kennung, andere Vorgangs-ID), Lernmodus `lernt` (Entscheidung H, 07.11.) | läuft etwas, wie bei „andere Kennung“ pausieren und Zeiger speichern; Kennung unbekannt: Kennung in `unknown.json`; **nichts abspielen, kein Ton `unbekannt`**, Frist 10 s starten (nur der Lernton von `learn`) | `pausiert` (wartet) |
| `pausiert` (wartet) | neue Konfiguration, die diesem Tobie ein **anderes** Ziel gibt als beim Beginn des Wartens (unbekannter Tobie: jedes Ziel) (Entscheidung H, 07.11.) | Ziel sofort starten wie beim Auflegen | `spielt` (unter „stumm“: `gehalten`) |
| `pausiert` (wartet) | andere neue Konfiguration (gleiches Ziel, anderer Tobie geändert) (Entscheidung H, 07.11.) | Konfiguration übernehmen, das Warten läuft weiter | unverändert |
| `pausiert` (wartet) | `bestaetigt` „abgelehnt“ für diesen Tobie (nur wenn die Outbox sie angenommen hat) (Entscheidung H, 07.11.) | wie ein normales Auflegen: bekannt → sein Ziel, unbekannt → Überraschung mit Ton `unbekannt` und erneut `Melden("unbekannt")` | `spielt` (unter „stumm“: `gehalten`) |
| `pausiert` (wartet) | Frist 10 s ohne Antwort (Entscheidung H, 07.11.) | wie ein normales Auflegen (Aktionskarte: Aktion auslösen); kein zweites Melden, der Eintrag bleibt offen | `spielt` (unter „stumm“: `gehalten`) |
| `pausiert` (wartet) | `REMOVED` (Entscheidung H, 07.11.) | Warten endet, nichts spielt | `pausiert` |
| `pausiert` (wartet) | Hauptknopf kurz, `Vor`, `Zurück` (Entscheidung H, 07.11.) | nichts (Lautstärke wirkt wie immer) | unverändert |
| `leer` | Start mit liegendem Tobie (CUJ 20) | wie `PLACED`, sobald alles bereit ist; nach Dienst-Neustart ohne Ausschalten nichts (Entscheidung G, 06.11.) | `spielt`; nach Dienst-Neustart `pausiert` |
| beliebig | Kopfhörer rein/raus | erst Grenze setzen, dann Ausgang umschalten | unverändert |

Kommt nach der Frist dieselbe Kennung wieder, ist das ein normales Auflegen
mit Resume am gespeicherten Zeiger (erste Zeile).

**Ohne Tobie auf der Box (Zustände `leer`, `pausiert` nach Abheben, `beendet`)
startet Hauptknopf kurz, `Vor` und `Zurück` nichts (Entscheidung Q, 10.11.):**
nur `TonSpielen("hinweis")`, der Zustand bleibt (unter „stumm“ gilt dieselbe
Regel). `spielt` pausiert wie bisher. Im Zustand
`beendet` liegt der Tobie immer noch auf der Box; deshalb spielt dort der
Hauptknopf die nächste Folge (bei einem Folgen-Tobie dieselbe Folge von
vorn) (Entscheidung F, 05.11.).

**2. Lernmodus** (`learn`, gehört der Box)

Zustände: `aus`, `lernt`.

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `aus` | HA-Befehl „Lernmodus“ an diese Box, nicht abgelaufen | Beginnton, Frist 2 min auf der Box starten | `lernt` |
| `aus` | HA-Befehl abgelaufen | ignorieren, protokollieren | `aus` |
| `lernt` | `PLACED` (bekannt oder unbekannt) | Kennung an HA melden, Endeton (die Sitzung spielt nichts und wartet auf HA, Entscheidung H, 07.11.) | `aus` |
| `lernt` | Frist 2 min ohne Tobie | Endeton | `aus` |
| `lernt` | HA „abbrechen“ | Endeton | `aus` |

**Lernmodus wartet still (Entscheidung H, 07.11.):** Im Zustand `lernt` startet ein aufgelegter
Tobie, bekannt oder unbekannt, **nichts**. Es kommt nur der Endeton; die Wiedergabe-Sitzung wartet bis zu 10 s
auf HA (siehe Sitzungstabelle, Zeilen „wartet“, und `core-interface.md`, 9.8). Die Zuordnung startet sofort das
neue Ziel; „abgelehnt“ und 10 s ohne Antwort verhalten sich wie ein normales Auflegen. `unknown.json` und
Melden laufen unverändert (nur nach „abgelehnt“ wird ein unbekannter Tobie neu gemeldet). Der Befehl geht an genau eine Box, ist nicht dauerhaft
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
| `aus` | Gute-Nacht-Karte aufgelegt | Timer starten (Dauer aus der Konfiguration, Vorschlag 30 min); `TonSpielen("gute_nacht")` (Entscheidung R, 10.11.; unter „stumm“ streicht `core` ihn, Regel 6.2.2b) | `läuft` |
| `läuft` | anderer Tobie aufgelegt | nichts; der Timer läuft für den neuen Tobie weiter | `läuft` |
| `läuft` | Timer abgelaufen | Ausblenden starten (Grenze sinkt über die Ausblendzeit, Vorschlag 60 s) | `ausblenden` |
| `ausblenden` | Lautstärke bei null | Pause, Zeiger speichern, Lautstärke zurücksetzen | `aus` |
| `ausblenden` | `REMOVED` | normale Pause (Zeiger gespeichert), Lautstärke zurücksetzen | `aus` |

**4. Strom / Leerlauf** (`idle`, `power`)

Zustände (Ein/Aus, 10.11.): `aktiv` (*Spielt*), `leerlauf` (*Bereit*: nichts wird gespielt, der Dienst läuft; der Zähler für 10 min läuft nur **ohne Strom**),
`herunterfahren` (auf dem Weg zu *Aus*). „Strom“ heißt Strom am Eingang der Box aus jeder Quelle (`pisugar-server` und Leser; bei Widerspruch gilt der Leser;
ohne Wert 60 s „unbekannt“, danach „kein Strom“). Vertrag: `core-interface.md`, Abschnitt 9, Punkt 9.

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `aktiv` | keine Wiedergabe (ein liegender Tobie zählt nicht, Entscheidung O, 09.11.) | Leerlauf-Zähler starten (monotone Uhr, `LEERLAUF_S` = 10 min), **nur wenn kein Strom anliegt** (Ein/Aus, 10.11.) | `leerlauf` |
| `leerlauf` | Wiedergabe → Zähler verwerfen; oder Bedienung (Taste, Drehregler, Hauptknopf kurz, Kopfhörer) → Zähler beginnt neu (09.11., AP 4.8; nur ohne Strom) | Zähler verwerfen (bei Wiedergabe); bei Bedienung Zähler neu starten | `aktiv` (bei Wiedergabe); `leerlauf` (bei Bedienung) |
| `leerlauf` | **Strom kommt** (Andocken, nach der ersten bekannten Messung; Ein/Aus, 10.11.) | Zähler verwerfen. Rückmeldung, wenn die Sperre `LADER_SPERRE_S` = 10 s frei ist: Ring Ladestand 5 s, Ton `lader` (nicht in „leiser“, „stumm“, bei unsicherer Uhr, im Lernmodus), Sync prüfen (`SyncStarten("start_lader")`, einmal, nicht während eines Updates) | `leerlauf` |
| `aktiv` | Strom kommt (Ein/Aus, 10.11.) | nur Ring 3 s und Sync prüfen; kein Ton (Entscheidung L) | `aktiv` |
| `leerlauf` | **Strom geht** (Abnehmen, Abziehen; Ein/Aus, 10.11.) | Zähler **ab jetzt** neu (10 min, R9); Ring Akku 5 s, kein Ton, kein Sync | `leerlauf` |
| `leerlauf` | 10 min um (kein Strom), Sync, Update oder Lernmodus läuft (auch: Sync oder Update noch offen) | warten, Zähler neu; nach Ende des Syncs oder Updates erneut prüfen | `leerlauf` |
| `leerlauf` | 10 min um (kein Strom), nichts läuft | Zeiger speichern, Herunterfahren | `herunterfahren` |
| `leerlauf` | mit Strom, beliebig lange | nichts: am Strom ist die Box immer bereit (Ein/Aus, 10.11.) | `leerlauf` |
| `aktiv`, `leerlauf` | Hauptknopf lang (auch mit Strom; am Sockel startet die Box danach wieder, R8) | Zeiger speichern, Herunterfahren | `herunterfahren` |
| `aktiv`, `leerlauf` | Akku-Tiefstand (nicht am Lader, also ohne Strom) | Sync abbrechen, Ton `akku_leer` (einmal), Zeiger speichern, Herunterfahren (Befund B12, 09.11.) | `herunterfahren` |
| `herunterfahren` | das Kommando hat nicht gewirkt (`HerunterfahrenFehlgeschlagen`: Rückgabecode ungleich 0, Kommando fehlt, Frist 60 s) | Protokoll, Hinweis an HA (`herunterfahren_fehlgeschlagen`), Zähler neu (ohne Strom) | `aktiv`, dann `leerlauf` (Befund B1, 09.11.) |
| `herunterfahren` | Simulation (Mac oder ohne `[strom]`): nur protokolliert, 10 s vergangen | Zähler neu (kein Hinweis an HA) | `aktiv`, dann `leerlauf` (Befund B1, 09.11.) |
| beim Start (`Bereit`) | erste bekannte Messung des Stroms (auch spät; auch nach einem Dienst-Neustart) ist „Strom“ | prüfen, ob ein Sync ansteht (`SyncStarten("start_lader")`, einmal; wartet höchstens 30 s auf die erste Netz-Klasse, B7). **Kein Ton, keine Andock-Rückmeldung.** Die Wiederholung des Start-Syncs (alle 10 min, höchstens 6-mal; 09.11., AP 4.8) **entfällt** (Ein/Aus, 10.11.) | `aktiv` |
| beim Start | keine Quelle liefert einen Wert | 60 s lang nichts (kein Ton, kein Ring, Zähler zählt noch nicht), danach gilt „kein Strom“ (Zähler beginnt) | `aktiv` |

In der Simulation wird „Herunterfahren“ nur protokolliert. Das Wecken aus *Aus* durch Tobie, Magnet und Strom (ESP32) folgt mit Schritt 2.

**Konflikte → erwartetes Ergebnis.** Jede Zeile ist zugleich ein Abnahmetest
(Stufe 4; Zeilen ohne Stufe-4-Teile laufen schon früher).

| Situation | Erwartetes Ergebnis |
|---|---|
| Folge zu Ende (nach dem letzten Track, nicht nach jedem Track), Tobie liegt noch (Entscheidung F, 05.11.) | `serie`: Zeiger auf die nächste Folge (nach der letzten auf Folge 1), Track 0, Position 0; `folge`: Zeiger dieser Folge auf Track 0, Position 0; die Box pausiert und wartet im Zustand `beendet`. Es passiert nichts, bis der Tobie abgehoben und wieder aufgelegt wird (Entscheidung A) oder der Hauptknopf kurz gedrückt wird (Entscheidung E). |
| Hauptknopf kurz, Folge ist zu Ende, Tobie liegt noch | Es spielt ab dem Zeiger (Track 0, Position 0): bei `serie` die nächste Folge, bei `folge` dieselbe Folge von vorn (Entscheidung F, 05.11.). Ohne Tobie auf der Box startet nichts, nur der Hinweiston (Entscheidung Q, 10.11.; vorher: normale Funktion Play / Pause). |
| `Zurück`, Folge ist zu Ende, Tobie liegt noch (Entscheidung F, 05.11.) | Die eben beendete Folge spielt von vorn (Track 0, Position 0), bei `serie` und `folge`. |
| `Vor` beim letzten Track (Entscheidung F, 05.11.) | `serie`: erster Track der nächsten Folge (nach der letzten auf Folge 1); `folge`: Hinweiston, nichts ändert sich. |
| Stumm gegen Lernmodus | Die Box lernt trotzdem, bestätigt mit dem leisen Ton und spielt nicht. |
| Stumm-Fenster beginnt, während ein Tobie spielt | Die Wiedergabe blendet sanft aus, pausiert, Zeiger gespeichert (`gehalten`). |
| Stumm-Fenster endet, während ein Tobie liegt | Nichts startet von selbst. Erst Abheben und erneutes Auflegen startet die Wiedergabe (Entscheidung B). |
| Gute Nacht läuft, ein anderer Tobie wird aufgelegt | Der Timer läuft für den neuen Tobie weiter. |
| Tobie wird beim Ausblenden abgehoben | Normale Pause, Zeiger gespeichert, Lautstärke zurückgesetzt, Resume setzt dort wieder an. |
| Tobie-Wechsel während einer Leser-Unterbrechung (`unbekannt`, dann `HELLO` und `PLACED` mit **anderer** Kennung) | Die Frist endet; Zeiger der alten Serie gespeichert, die neue Serie startet wie bei einem normalen Auflegen. |
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
| `config.json` | Konfiguration von HA mit **einer** Revision und **einer** Listen-ID: Zuordnungen `uid → Eintrag` mit einem Feld `ziel`: `{"typ":"serie","serie":id}`, `{"typ":"folge","serie":id,"folge":name}` oder `{"typ":"aktion",…}` (z. B. Status oder Gute Nacht) (Entscheidung F, 05.11.), Leise-Zeiten, Gute-Nacht-Einstellungen (Timer-Dauer, Ausblendzeit), optional `lesezeichen_tage` (Vorgabe 14, 0 = nie; Entscheidung N, 09.11.) | nur aus HA übernommen | holt von HA |
| `resume.json` | je Serie der Zeiger (aktuelle Folge als Name, Track, Position in s) + Zähler, und je (Serie, Folge) ein Zeiger für Folgen-Tobies (Track, Position, Zähler) (Entscheidung F, 05.11.); `schema_version` 2; je Zeiger optional `benutzt_am` (Zeitpunkt der letzten Benutzung, UTC; Entscheidung N, 09.11.) | Box | nie |
| `unknown.json` | unbekannte Kennungen mit Zeitpunkt, noch nicht von HA bestätigt | Box | an HA; Eintrag erst löschen, wenn HA bestätigt hat (`…/ack`) |

- **Serie** = Ordner im Medienordner; Folgen darin sind **Audiodateien (D5)
  oder Unterordner mit mehreren Tracks** (Entscheidung F, 05.11.). Eine Folge ist eine Datei, wenn sie
  eine Datei mit erlaubter Endung ist, und ein Folgen-Ordner, wenn sie ein
  Unterordner (Name ohne Punkt am Anfang) mit mindestens einem Track ist.
  **Tracks eines Folgen-Ordners:** die Dateien im Unterordner (nicht
  verschachtelt), ohne Dotfiles, mit derselben Endungsliste wie überall,
  geordnet nach der natürlichen Sortierung. Ein Folgen-Ordner ohne Track zählt
  nicht als Folge (Protokolleintrag). Der Name der Folge (Dateiname oder
  Ordnername) ist ihr Schlüssel in `serie.json` und im Zeiger.
  **Reihenfolge der Folgen, eine Regel überall:** Sie steht in `serie.json`
  (Liste `folgen`, Folgen mit Namen). Nur wenn `serie.json` fehlt, gilt die
  natürliche Sortierung nach Name. Dateien und Ordner, die im Serien-Ordner
  liegen, aber nicht in der Liste stehen, spielt die Box erst, wenn die
  Integration sie in die Liste eingetragen hat. Ein Hörspiel ohne Reihe liegt
  in einem beliebigen Serien-Ordner (z. B. „Einzelfolgen“), ohne Sonderregel.
- **Serien-ID** — siehe Entscheidung D2. Die Box spielt auch Ordner ohne
  `serie.json`: Ordnername als ID, Reihenfolge nach Dateiname; legt HA später eine
  `serie.json` an, bleibt der Ordnername die ID (09.11., Befund AP 3.1). Tragen zwei
  Ordner dieselbe ID (Ordner samt `serie.json` kopiert), gibt die
  Integration der **jüngeren** Kopie eine neue ID und meldet das. „Jünger“
  heißt: das spätere `angelegt_am` in `serie.json`.
- **Admin-Karten** (Status usw.) sind Einträge in `config.json` mit
  `ziel.typ` `aktion` statt `serie` oder `folge`. Sie werden in HA wie jeder Tobie zugeordnet; bis
  Stufe 3a per `tobibox sim`.
- Alle Schemas (vollständig, mit Beispiel-JSON) stehen als Vertrag in
  `docs/data-model.md` (Stufe 0): `config.json`, `resume.json`, `unknown.json`,
  `serie.json`, `manifest.json` und die Zeile des Ereignisprotokolls. Ein AP,
  das ein Schema ändert, ergänzt `docs/data-model.md`.
- **Zeigerregeln (Resume = „nächste ungehörte Folge“):** (Entscheidung F, 05.11.) Eine Position ist
  (Folge, Track, Sekunden im Track). Es gibt zwei Arten von Zeigern:
  - **Serien-Zeiger** (für `serie`, auch für die Überraschungs-Serie): ein
    Zeiger je Serie. Ohne gespeicherten Zeiger beginnt die Serie bei Folge 1,
    Track 0. Folge zu Ende (nach dem letzten Track) → Zeiger auf die nächste
    Folge, Track 0, Position 0; nach der letzten Folge auf Folge 1.
  - **Folgen-Zeiger** (für `folge`): ein Zeiger je (Serie, Folge), unabhängig
    vom Serien-Zeiger derselben Serie. Ohne Zeiger beginnt die Folge bei Track
    0. Folge zu Ende → der Zeiger **springt auf Track 0, Position 0 zurück**:
    Das nächste Auflegen spielt die Folge von vorn.

  **Nach jeder Folge pausiert die Box** (Entscheidung A, hier am Ende der
  **ganzen Folge**, nicht nach jedem Track; die Tracks einer Folge spielen
  ohne Pause): Pause, auch wenn der Tobie noch liegt. Die nächste Folge (Serie)
  oder dieselbe Folge von vorn (Folge) spielt erst, wenn der Tobie (oder ein
  anderer Tobie desselben Ziels) neu aufgelegt wird oder der Hauptknopf kurz
  gedrückt wird (Entscheidung E). Beim Weiterspielen mitten in einem Track 3 s
  Rücksprung im Track (per `seek`, siehe „Abspielen mit MPD“). Die Zeigerlogik
  gehört zu Stufe 1 (AP 1.7).
- **Vor / Zurück** (CUJ 19): Vor springt zum nächsten Track der Folge; beim
  letzten Track zur nächsten Folge (`serie`) bzw. nichts mit Hinweiston
  (`folge`). Zurück springt zum vorigen Track, wenn die Position im Track unter
  3 s liegt und es einen vorigen Track gibt, sonst startet der aktuelle Track
  neu. Jeder Sprung setzt Position 0 und speichert den Zeiger.
- **Zeiger auf eine fehlende Folge** (gelöscht, umbenannt, aus der Liste): Bei
  einem Serien-Zeiger geht der Zeiger auf die nächste vorhandene Folge in der
  Reihenfolge, Track 0, Position 0, und die Box protokolliert das. Ist die Serie
  leer: Fehlerton. Zeigt ein Folgen-Tobie auf eine Folge, die es auf der Box
  nicht gibt, gilt wie bei einer fehlenden Serie: Die Box spielt die
  Überraschungs-Serie und protokolliert den Grund; kommt die Folge später, gilt
  die Zuordnung beim nächsten Auflegen. **Fehlender Track** (die Folge hat jetzt
  weniger Tracks als der Zeiger meint): Track 0, Position 0, Protokolleintrag.
  **Fehlender oder unlesbarer Track innerhalb einer Folge mit mehreren Tracks**
  (Festlegung, bestätigt 05.11.): Die Box überspringt ihn und spielt den
  nächsten Track derselben Folge (Protokoll `datei_fehlt`); erst nach dem
  letzten Track gilt das als Ende der Folge (Entscheidung F, 05.11.).
- **Migration:** `resume.json` (`schema_version` 1 → 2): Jeder Eintrag in
  `serien` bekommt `track` 0; `folgen` (Folgen-Zeiger) ist leer. Alte Einträge
  gelten also als „Track 0 mit der gespeicherten Position“. `config.json`
  (`schema_version` 1 → 2): Jeder Eintrag `{typ, …}` wird zu `{ziel: {typ, …}}`.
  Beide Migrationen laufen im Speicher beim Lesen (`data-model.md`, 1.5).
  Auch eine Liste der Version 1, die per MQTT ankommt, nimmt die Box an und
  migriert sie im Speicher; die Prüfung von `ziel` läuft **nach** der
  Migration (`data-model.md`, Abschnitt 2) (Entscheidung F, 05.11.).
  Reihenfolge der Einführung: zuerst alle Boxen aktualisieren, danach verteilt
  HA Version 2 (es stehen noch keine Boxen im Feld).
- Der Zeiger wird nur gespeichert, wenn er sich geändert hat — bei Pause,
  Folgen- und Track-Wechsel, Tobie-Wechsel und höchstens alle 30 s während der Wiedergabe.
- **Schreibbudget:** Bei 2 h Wiedergabe am Tag sind das 240 periodische
  Schreibvorgänge pro Box, dazu je einer für jede Pause, jeden Tobie-Wechsel und
  jeden Track-Wechsel (Entscheidung F, 05.11., neu gerechnet): bei 40 Pausen oder
  Wechseln und 40 Track-Wechseln höchstens 320 Schreibvorgänge pro Tag und Box
  für den Zeiger. Das Ereignisprotokoll hat eine feste
  Obergrenze (Pi: journald mit begrenztem Platz; Mac: rotierende Datei,
  Vorschlag 5 Dateien zu je 1 MB). Beide Werte werden im Pi-Probelauf
  geprüft.
- **Überraschungs-Serie** ist eine normale Serie, erkennbar nur an `typ`
  `ueberraschung` in ihrer `serie.json`; eine feste ID gibt es nicht. Sie
  verhält sich wie ein Ziel `serie` (Entscheidung F, 05.11.). Gibt es
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
  Verlust von HA: HA-Sicherung und NAS-Export; danach „Liste neu ausrollen“ oder
  die Konfiguration aus dem Export zurückholen. (Vertrag W, 09.11.: Ist der Speicher leer
  oder der Export neuer, veröffentlicht die Integration **nichts**, bis Tobias entschieden
  hat; erst veröffentlichen, dann exportieren; Fehler beim Export werden gemeldet;
  Abschnitt 13.)
- **Medien:** Die Medienfreigabe des QNAP ist in HA als Netzwerkspeicher
  eingebunden. Aufbau auf dem NAS: `tobibox/medien/<ordner>/serie.json` +
  Audiodateien, `tobibox/medien/_papierkorb/`, `tobibox/medien/_upload/`
  (Zwischendateien), `tobibox/eingang/` (Entscheidung M, 09.11.), `tobibox/export/`,
  `tobibox/releases/`. HA hat vollen Schreibzugriff auf die Freigabe
  (`medien/`, `eingang/`, `export/`, `releases/`); Tobias ist der einzige Benutzer
  (Entscheidung D). Pakete legt Tobias ab. **`_upload/`, `_papierkorb/` und `eingang/`
  werden vom Sync der Boxen ausgenommen** (NAS-Modul und Box, AP 3.4, AP 3.5); Ordner mit
  `_` am Anfang und der Name `eingang` sind in `medien/` keine Serien.
- **`serie.json`:** `schema_version`, `id` (unveränderlich: zufällig; nur für einen Ordner,
  der vorher keine `serie.json` hatte, der Ordnername, siehe „Erkennen von außen“),
  `name` (Anzeige), `angelegt_am`, `folgen` (Reihenfolge als Liste von
  Namen von Dateien und Folgen-Ordnern; maßgeblich, Regeln im Datenmodell), `typ` (`normal` oder
  `ueberraschung`; die Überraschungs-Serie wird nur daran erkannt). Geschrieben
  atomar. Optional (09.11., Entscheidung M): `folgen_info` (Anzeigename, Folgen-Nummer,
  Datum je Folge) und `pruefen`/`pruefen_gruende`; die Box ignoriert sie (Datenmodell).
- **Eingang (Entscheidung M, 09.11.):** Beim Öffnen der Seite und alle 10 min liest die
  Integration `eingang/` (Ruhezeit 120 s gegen halb kopierte Ordner) und sortiert nach
  den Tags ein (`ha-websocket-v1.md`, Abschnitt 11). Kopiergeschütztes und Defektes
  bleibt im Eingang mit Hinweis; Doppelte (Prüfsumme) kommen in den Papierkorb.
- **Erkennen von außen:** Beim Öffnen der Seite und alle 10 min prüft die
  Integration die Freigabe. Neuer Ordner → `serie.json` mit Ordnername als
  Anzeigename. **ID (09.11., Befund AP 3.1):** Ein Ordner, der vorher **keine** `serie.json`
  hatte (die Box spielt ihn schon unter dem Ordnernamen als ID), behält den Ordnernamen als ID,
  damit Zeiger und Zuordnungen erhalten bleiben (Datenmodell, Abschnitt 5; ist der Name als ID
  ungültig, kommt eine zufällige). Die Seite legt neue Serien mit zufälliger ID an. Neue Datei oder neuer Folgen-Ordner → hinten an die Reihenfolge (erst
  dann spielt die Box sie). Fehlende Datei oder fehlender Ordner → aus der
  Reihenfolge, Hinweis (Entscheidung F, 05.11.).
  Neue Dateien werden auf Format und Kopierschutz geprüft (D5). Schreiben HA,
  ein PC und der Lautheits-Container (D6) gleichzeitig auf die Freigabe, gibt
  es keine Sperre; das ist als Risiko geführt.
- **Löschen** (Folge oder ganze Serie) verschiebt in `_papierkorb/<id>/` mit
  `meta.json` (Herkunft für „wiederherstellen“, `data-model.md`, Abschnitt 9), nie
  endgültig sofort. Zeigen Tobies darauf, fragt die Seite vorher mit Anzahl und Namen.
  Es gibt keine Automatik; Tobias leert den Papierkorb von Hand mit dem Knopf
  „Papierkorb leeren“ auf der Seite. Die Boxen übernehmen `_papierkorb/` nicht.

#### Aktionen und Seite

- **Aktionen** (auch für Automationen): zuordnen (Typ `serie`, `folge` oder
  Aktion; Aktionskarten wie Status und Gute Nacht) (Entscheidung F, 05.11.), lösen, Lernmodus starten / abbrechen, Serie anlegen /
  umbenennen / löschen, Folge umbenennen / verschieben, Serien zusammenführen,
  Eingang einsortieren (Entscheidung M, 09.11.), Folgen sortieren / löschen, Papierkorb leeren, Sync anstoßen,
  Update anstoßen, Liste neu ausrollen (erzeugt eine neue Listen-ID),
  Leise-Zeiten und Gute-Nacht-Einstellungen einstellen (Stufe 4).
- **Eigene Seite** in der HA-Seitenleiste („Tobi Box“), läuft auch über
  Nabu Casa am Handy:
  - Serienliste mit Anzahl Folgen und zugeordneten Tobies
  - Serie öffnen: Folgen (Dateien oder Folgen-Ordner) per Ziehen sortieren, löschen, umbenennen
    (Anzeigename), in eine andere Serie verschieben, Audiodateien vom Handy hochladen
    (sie gehen in den Eingang)
  - „Eingang“: was im Eingang liegt und was erkannt wurde (Serie, Folge, Nummer), mit
    „bitte prüfen“ bei fehlenden oder widersprüchlichen Tags, Hinweisen zu
    Kopierschutz und Doppelten, „erneut einsortieren“ und Zusammenführen zweier Serien
    (Entscheidung M, 09.11.)
  - „Neue Tobies“: unbekannte Kennungen beider Boxen (gleiche Kennung = ein
    Eintrag), mit einem Tipp einer Serie oder einer einzelnen Folge zuordnen
    (Weg A; Tobias wählt dabei den Typ `serie` oder `folge`) (Entscheidung F, 05.11.); „Jetzt kommt ein
    neuer Tobie“ (Weg B, ebenfalls mit Typ)
  - Aktionskarten (Status, Gute Nacht) einer Kennung zuordnen; Tobies bekommen auf Wunsch einen Namen
  - Warnungen: Speicher von HA leer oder Export neuer, Export fehlgeschlagen, Box mit
    neuerem Stand (Vertrag W, Abschnitt 13)
  - Box-Status: Version, Netz, Akku, Sync-Stand, letzter Fehler, abgelehnte
    Listen
  - Speicher: freier Platz je Box (die Box meldet ihn mit dem Status, D5);
    Knopf „Papierkorb leeren“
- **Technik der Seite:** ein Web-Baustein (JavaScript-Modul, Lit, ohne
  eigenen Build-Server), Daten über die HA-WebSocket-Schnittstelle mit
  HA-Anmeldung; Hochladen über einen eigenen HA-HTTP-Endpunkt mit Anmeldung,
  der nur Audioformate nach D5 annimmt. Die Seite wird mit `panel_custom`
  registriert (nur für Administratoren, `require_admin=True`), ihre Dateien liefert
  `async_register_static_paths` (öffentlich, deshalb ohne Geheimnisse); Lit liegt in
  fester Version eingecheckt im Ordner der Seite. Die WebSocket-Befehle (Name,
  Eingabe, Ausgabe) sind ein Vertrag, den die Projektleitung zu Beginn von
  Stufe 3a schreibt (`docs/protocol/ha-websocket-v1.md`), bevor Backend und
  Seite parallel entstehen.
- **Technik der Integration:**
  - `manifest.json` mit `version` und `dependencies` (`mqtt`, `http`,
    `panel_custom`, `websocket_api`).
  - **HA-Version fest: 2026.11.x** (Tobias aktualisiert darauf; die genaue
    Patch-Version nennt er beim Start von AP 3.1). Mosquitto-Add-on 7.1.3. Die
    Tests mit `pytest-homeassistant-custom-component` sind an HA- und
    Python-Version gebunden und laufen deshalb in einer eigenen venv und einem
    eigenen CI-Job.
    **Nachtrag zu Rev. 3.15 (09.11., Befund AP 3.1; keine neue Revision):** Die HA-Tests laufen
    vorerst gegen **2026.10.4**, weil `pytest-homeassistant-custom-component` für 2026.11 noch
    nicht erschienen ist. Die Integration ist statisch gegen 2026.11.0 geprüft. Die Pins
    (`homeassistant/requirements-test.txt`, CI) werden nachgezogen, sobald das Plugin da ist.
  - Upload als Strom in Blöcken (`request.multipart()`): HA begrenzt normale
    Anfragen auf 16 MiB (`MAX_CLIENT_SIZE` in `components/http/server.py`, am 09.11.
    im Quelltext belegt), Hörspielfolgen sind größer; Grenze je Datei zunächst 500 MiB,
    einstellbar. Ob Nabu Casa große Uploads durchlässt, wird am Handy mit 20, 150 und
    500 MiB gemessen (Risiko). Der Upload geht in den Eingang (Entscheidung M, 09.11.).
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
  zwei Dateien (09.11., Befund AP 3.1): `/share/mosquitto/acl.conf`
  ist eine Mosquitto-Konfiguration und enthält nur `acl_file /share/mosquitto/accesscontrollist`;
  die Regeln (`user`, `topic`, `pattern`) stehen in der Datei `accesscontrollist` ohne Endung, weil
  das Add-on jede `*.conf` als Konfiguration liest. `homeassistant` und `addons` bleiben
  unbeschränkt, die Box-Konten sind keine HA-Administratoren (Option `logins`). Beispiele liegen
  unter `homeassistant/mosquitto/`.
- Alle Themen mit Nachrichten (Felder, Beispiele), QoS, „retained“, Ablaufzeit
  der Befehle, Bestätigungen und Discovery-Namen stehen als Vertrag in
  `docs/protocol/mqtt-v1.md` (Stufe 0).
- Themen:
  - `tobibox/config` (dauerhaft/„retained“, ganze Konfiguration:
    Zuordnungen mit `ziel` (`serie`, `folge` oder `aktion`) (Entscheidung F, 05.11.), Leise-Zeiten, Gute-Nacht-Einstellungen, mit einer Revision
    und einer Listen-ID)
    - `tobibox/<box>/event` (gelernt, abgelehnte Liste, Fehler)
  - Unbekannte Kennungen: Die Box veröffentlicht jede Kennung **dauerhaft
    („retained“) auf einem eigenen Thema je Kennung**
    (`tobibox/<box>/unknown/<uid>`). HA bestätigt auf dem Thema `…/ack` (mit
    Grund); **erst dann** löscht die Box den Eintrag in `unknown.json` und die
    dauerhafte Nachricht. Die Bestätigung des Brokers (PUBACK) reicht nicht:
    Sie sagt nicht, dass HA der Tobie hat, etwa wenn HA gerade neu startet
  - `tobibox/<box>/cmd` (Lernmodus, Sync, Update): geht an genau eine Box,
    ist **nicht** dauerhaft und trägt eine Ablaufzeit; ein abgelaufener Befehl
    wird ignoriert (Tabelle „Lernmodus“ in den Kern-Zuständen).
- Box meldet sich per **MQTT-Discovery** an: Sensoren (Zustand, läuft
  gerade, Akku, Lader, Netz, Sync-Stand, freier Speicherplatz, Version,
  letzter Fehler, Zeitquelle), Knöpfe (Sync jetzt, Update, Lernmodus
  abbrechen), Auswahl (Serie für Lernmodus; Typ und Folge wählt Tobias in der
  Aktion „Lernmodus starten“ (Entscheidung F, 05.11.)).
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
  - `hotspot`: erlaubt, wenn Lader dran (Strom am Eingang, aus jeder Quelle; Ein/Aus, 10.11.) oder Akku > 50 %.
  - Dateien landen erst nach vollständiger Übertragung sichtbar im
    Medienordner: `--partial-dir` mit **absolutem Pfad außerhalb des
    Medienordners, aber auf demselben Dateisystem**
    (`/var/lib/tobibox/.rsync-partial`) und ein ebenso absolutes `--temp-dir`.
    So indexiert MPD keine halben Dateien; jede Datei wird erst fertig atomar an
    ihren Platz umbenannt. **Kein `--delay-updates`** (09.11., Befund AP 3.7): Mit
    einem absoluten `--partial-dir` legt rsync zurückgestellte Dateien flach nach
    Dateiname ab; zwei Serien mit je einer `serie.json` kollidieren, der Sync bräche
    mit `rsync_fehler` ab. Ohne `--delay-updates` ist je Datei höchstens eine halbe
    Datei unterwegs, und zwar außerhalb des Medienordners.
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
  Treiber. Abschalt- und Lader-Regeln: CUJ 16, 23 bis 25 und Tabelle „Strom / Leerlauf“.
  **(Ein/Aus, 10.11.)** „Lader“ heißt **Strom am Eingang der Box aus jeder Quelle**. Zwei Quellen liefern ihn: `pisugar-server` (`battery_power_plugged`)
  und der Leser (Zeile `LADER`, ab Firmware mit `caps` `strom`); bei Widerspruch gilt der Leser. Am Strom ist die Box immer bereit; ohne Strom fährt sie
  nach 10 min Leerlauf herunter, gerechnet ab dem Abnehmen. Beim Andocken einer laufenden Box (nach der ersten bekannten Messung) gibt es Ring, Ton `lader`
  und einen Sync-Check (Sperre 10 s); die erste bekannte Messung und ein Dienst-Neustart lösen nur den Sync-Check aus. Anders als bis 09.11. gibt es **keine
  Wiederholung** des Start-Syncs: Ein abgebrochener Sync (`netz_weg`, `regel`) hält die Abschaltung nicht auf, den nächsten Anstoß geben der Takt (Intervall
  in `tobibox.toml`), das Andocken und HA.
- **Uhr:** siehe „Uhr und Zeitquelle“ in Baustein 3.

### Update

- **Auslöser:** HA-Knopf.
- **Bedingungen:** Box daheim (`home`), am Lader (Strom am Eingang, aus jeder Quelle; Ein/Aus, 10.11.), spielt nicht, kein Sync.
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

### Automatische Erkennung des Tobies

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
| Tobies zum Testen (Tonies, darunter ein gesperrter, und NFC-Karten) | Abnahme, Messung | vor Abnahme Stufe 1 |
| Mikrofon (das im Mac reicht) | Messung am Ausgang (AP 1.6) | vor AP 1.6 |
| Einige Test-Audiodateien (optional) | Hörprobe; die Tests erzeugen eigene | optional |

**Reihenfolge:** AP 1.1 läuft parallel zu allem. Danach AP 1.2a, dann AP 1.2b;
AP 1.3, 1.4 und 1.5 laufen parallel; danach AP 1.7 (Folgen mit Tracks und
Folgen-Tobies, Entscheidung F, 05.11.; erweitert die Dateien aus AP 1.2a, 1.2b
und 1.3); AP 1.6 am Schluss.

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
| `firmware/tobibox-reader/test/test_debounce/test_debounce.cpp` | neu | Native Tests: 2-gleich-Regel, 1,0-s-Lücke, 1,1-s-Abheben, Tobie-Wechsel, verfälschte Kennung am Rand, gesperrter Tonie, „gesperrt → offen“, `fehler(code)` mitten in der Entprellung. |
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
| `box/src/tobibox/session.py` | änd. | Zeigerlogik anschließen: Zeiger laden beim Auflegen, speichern bei Abheben, Folgenende, Tobie-Wechsel. |
| `box/src/tobibox/core.py` | änd. | Befehl „Speichern“ und Zeiger-Eingang verdrahten. |
| `box/tools/fake_reader.py` | neu | Gibt Protokollzeilen auf ein Pseudo-Terminal aus; Vorführen und Testen ohne Hardware. |
| `box/tests/fixtures/__init__.py` | neu | Paket für die Test-Erzeuger. |
| `box/tests/fixtures/audio.py` | neu | Erzeugt kurze WAV-Töne und Serienordner mit `serie.json` im Test-Verzeichnis (kein eingechecktes Audio). |
| `box/tests/unit/test_store.py` | neu | Atomares Schreiben, `.bak`-Rückfall, beschädigte Datei beim Start. |
| `box/tests/unit/test_store_powerloss.py` | neu | Stromausfall-Test: Prozess hart beenden während des Schreibens; danach ist die Datei lesbar. |
| `box/tests/unit/test_library.py` | neu | Reihenfolge, Ordner ohne `serie.json`, doppelte IDs, Überraschungs-Serie (keine oder mehr als eine, leer). |
| `box/tests/unit/test_pointer.py` | neu | Alle Zeigerregeln, darunter „Zeiger auf gelöschte oder umbenannte Folge“ und „Folge zu Ende bei liegendem Tobie: Pause, Zeiger auf die nächste Folge, nach der letzten auf Folge 1“. |
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
| `box/src/tobibox/player.py` | neu | Dünne MPD-Schicht über `mpd.asyncio.MPDClient`: Warteschlange nur mit der aktuellen Folge (ab AP 1.7 mit allen Tracks der Folge), Abspielen, Pause, Resume per `seek` auf Position, Lautstärke, Ereignis „Folge zu Ende“ (MPD stoppt) nach `core-interface.md`. Setzt die wirksame Grenze aus `volume.py` nur durch und setzt beim Start **zuerst** die Lautstärke. (Entscheidung L, 09.11.: `ton_pause_beginn` / `ton_pause_ende` halten MPD für einen Ton kurz an und setzen es an derselben Stelle fort, ohne Ereignis an den Kern.) |
| `box/src/tobibox/sounds.py` | neu | Kurze Töne über konfigurierbares Kommando (Mac `afplay`, Pi `aplay`). (Entscheidung J, 09.11.: Pegel aus der Lautstärke der Sitzung, Kennlinie wie MPD. Entscheidung L, 09.11.: eine Spur, Töne nie gleichzeitig; Dauer = Ende des Prozesses, Zeitlimit 10 s; Haken `vor`/`nach` für die kurze Pause des Hörspiels.) |
| `box/src/tobibox/notify.py` | neu | `READY=1` über `NOTIFY_SOCKET` senden (reines Python, ohne `python-systemd`); am Mac ohne Wirkung. |
| `box/src/tobibox/app.py` | neu | **Einziger Zusammenbau-Punkt:** baut Uhr und Module, verdrahtet reader → core → player, Zeitgeber (`Takt`), meldet `READY=1`, beendet sauber. (Entscheidung L, 09.11.: Töne einer Ausgabe vor das `Abspielen` stellen; ein `Abspielen` wartet als eigene Aufgabe auf das Ende der Tonspur und wird von `Pausieren`, einem neuen Start oder einer Prüfung von `gen` und Zustand verworfen; Haken für die kurze Pause des Hörspiels.) |
| `box/src/tobibox/__main__.py` | neu | Einstieg `python -m tobibox` bzw. `tobiboxd`. |
| `box/tools/make_sounds.py` | neu | Erzeugt die Platzhalter-Töne reproduzierbar. (Entscheidung J, 09.11.: je Ton eine feste Anpassung `PEGEL_DB` auf −18 LUFS.) |
| `box/tools/lautheit.py` | neu | (Entscheidung J, 09.11.) Misst die Lautheit mit `ffmpeg` (EBU R128), kurze Töne werden auf mindestens 3 s wiederholt; schreibt `box/lautheit.json`. Zielwert −18 LUFS, Toleranz ±1 LU. |
| `box/lautheit.json` | neu | (Entscheidung J, 09.11.) Prüfsumme und Messwert jeder Audiodatei in `box/sounds/`, `box/sounds/sprache/`, `box/medien-sprache/`. |
| `box/tests/unit/test_lautheit.py` | neu | (Entscheidung J, 09.11.) Alle Töne und Testmedien liegen innerhalb ±1 LU bei −18 LUFS: mit `ffmpeg` gemessen, sonst über `lautheit.json`; MP3 mit ReplayGain-Tags; Messhelfer an einem Sinus. |
| `box/sounds/start.wav` | neu | Platzhalter-Ton: Start. |
| `box/sounds/unbekannt.wav` | neu | Platzhalter-Ton: unbekannter Tobie. |
| `box/sounds/fehler.wav` | neu | Platzhalter-Ton: Fehler. |
| `box/sounds/hinweis.wav` | neu | Leiser Hinweiston (Tobie erkannt bei „stumm“). |
| `box/sounds/lernen_beginn.wav` | neu | Platzhalter-Ton: Lernmodus beginnt. |
| `box/sounds/lernen_ende.wav` | neu | Platzhalter-Ton: Lernmodus endet. |
| `box/sounds/akku_leer.wav` | neu | Platzhalter-Ton: Akku fast leer. |
| `box/tests/fixtures/mpd.test.conf` | neu | MPD-Konfiguration nur für Tests: eigener Port und eigenes Verzeichnis, Null-Ausgabe. |
| `box/tests/integration/conftest.py` | neu | Startet und beendet ein MPD mit `mpd.test.conf`; nutzt `fixtures/audio.py`. |
| `box/tests/integration/test_player_mpd.py` | neu | Gegen echtes MPD: Start, Pause, Position, Resume per `seek`, Folgenende (MPD stoppt, nichts spielt weiter), Lautstärke nie über der Grenze (auch nach Neustart des Dienstes; das ist die Klemmung im Dienst, die harte Kappung folgt im Pi-Probelauf). |
| `box/tests/unit/test_sounds.py` | neu | Kommando wird korrekt zusammengesetzt; kein Aufruf ohne Datei. (Entscheidung L, 09.11.: ergänzt um die eine Spur: Töne aus verschiedenen Aufrufen nacheinander, Dauer = Ende des Prozesses, Zeitlimit beendet das Programm, Haken, Beenden ohne Haken.) |
| `box/tests/unit/test_app_toene.py` | neu (Entscheidung L, 09.11.) | Echte `App` mit gesteuertem Ton-Ersatz: Ton + Abspielen in einer Ausgabe (unbekannter Tobie, Lernmodus-Ende), mehrere Töne nacheinander, Ton während der Wiedergabe (Pause, Fortsetzen, kein Zeiger), Abheben und `Pausieren` während des Tons, veralteter Start (`gen`, Zustand), neuer Start ersetzt den alten, hängender Ton (Zeitlimit), normales Auflegen ohne Ton ohne Verzug. |
| `box/tests/integration/test_toene_mpd.py` | neu (Entscheidung L, 09.11.) | Gegen echtes MPD mit `fake_reader`; das Ton-Kommando ist `sleep 1.5`: Start erst nach dem Ton, Abheben im Ton, Ton während der Wiedergabe (MPD pausiert und setzt an derselben Stelle fort, kein Zeiger), Abheben bei angehaltenem Hörspiel, hängender Ton. Ergänzt nach dem Code-Review: Tobie-Wechsel im Ton, `stop()` mitten im Ton, MPD-Neustart im Ton. |
| `box/tests/integration/test_toene_player_mpd.py` | neu (Code-Review, 09.11.) | Echter `Player` gegen echtes MPD, Wettläufe mit gehaltener Sperre: Abheben genau beim Tonbeginn (MPD bleibt pausiert), `Pausieren` hinter dem ersten Start, Verbindungsverlust im Ton, Ton mitten in einem Start, Pause bleibt bei weiterem Ton. |

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

#### AP 1.7 Folgen mit Tracks und Folgen-Tobies (Sonnet)

Ergebnis (Entscheidung F, 05.11.): Eine Folge ist eine Datei oder ein Ordner mit
mehreren Tracks und spielt alle Tracks ohne Pause; ein Tobie zeigt auf eine
Serie oder auf eine einzelne Folge. Die Pause nach jeder Folge gilt am Ende der
ganzen Folge. Zeiger mit Track, Folgen-Zeiger, Vor / Zurück nach Track,
`resume.json` und `config.json` in Version 2 mit Migration. Läuft nach AP 1.2a,
1.2b und 1.3 und ändert deren Dateien; **AP 1.6 hängt von diesem AP ab.**
Ausnahme von der Grundregel zu `session.py` und `app.py`: Diese Änderung gehört
inhaltlich zu den Teilen und wird vor AP 1.6 gemacht; AP 1.6 führt zusammen.
Die Verträge (`docs/protocol/core-interface.md`, `docs/data-model.md`,
`docs/protocol/mqtt-v1.md`) sind schon nachgezogen (zuletzt mit den Festlegungen
25 bis 28 in `core-interface.md`: Position, Player-Ereignisse in allen Zuständen
mit laufendem MPD, Zurück in `beendet`, fehlender Track, Statusfeld `folge`);
das AP ändert sie nicht.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/events.py` | änd. | Typen nach `core-interface.md` (Entscheidung F): `TrackWechsel`, `FolgeZuEnde` (Folge nach dem letzten Track zu Ende), `PlayerPosition.track`, `Abspielen` mit `tracks` und `track`, `Zeiger` und `ZeigerSpeichern` mit `art` und `track`, `Zuordnung` mit Typ `folge`, `Serie.tracks`. |
| `box/src/tobibox/audiodauer.py` | neu (Entscheidung I, 09.11.) | Dauer einer Audiodatei aus den Kopfdaten (WAV, MP3, M4A/M4B, FLAC), sonst `None`; nur Standardbibliothek. `library.py` füllt damit `Serie.dauern`. |
| `box/src/tobibox/library.py` | änd. | Folge = Datei oder Unterordner; Tracks eines Folgen-Ordners nach natürlicher Sortierung, ohne Dotfiles, gleiche Endungsliste; leerer Folgen-Ordner zählt nicht (Protokoll); `serie.json.folgen` nennt Namen. |
| `box/src/tobibox/pointer.py` | änd. | Serien-Zeiger und Folgen-Zeiger; Folgenende je Ziel (Serie: nächste Folge, Track 0; Folge: zurück auf Track 0, 0 s); Track-Sprünge für Vor / Zurück (3-s-Regel); fehlende Folge und fehlender Track. |
| `box/src/tobibox/session.py` | änd. | Ziel `serie` / `folge` merken; `TrackWechsel` (Zeiger, keine Pause); `FolgeZuEnde` (Pause erst jetzt, Zeiger je Ziel); Vor / Zurück nach Track; Hauptknopf kurz und Zurück in `beendet`; Folgen-Tobie mit fehlender Folge → Überraschungs-Serie. |
| `box/src/tobibox/store.py` | änd. | `resume.json` Version 2 (Track, Folgen-Zeiger) und `config.json` Version 2 (`ziel`) lesen und schreiben; Migration im Speicher (alte Einträge = Track 0 bzw. `ziel` aus `typ`). **Stellt die eine Funktion für Migration und Prüfung einer Konfiguration bereit** (`validiere_konfig`: erst migrieren, dann prüfen); `ha.py` (AP 3.x) ruft sie auf und schreibt keine eigene Prüfung. |
| `box/src/tobibox/player.py` | änd. | Warteschlange mit den Tracks der aktuellen Folge; `seek` auf Track und Position; `TrackWechsel` bei Wechsel zum nächsten Track; `FolgeZuEnde` erst, wenn MPD nach dem letzten Track stoppt; `PlayerPosition` mit Track. Ein fehlender oder unlesbarer Track einer Folge mit mehreren Tracks wird übersprungen (`datei_fehlt` im Protokoll), `PlayerFehler` nur, wenn kein Track spielbar ist. |
| `box/src/tobibox/app.py` | änd. | Verdrahtung: `Abspielen` mit Tracks an den Player, neue Player-Ereignisse in den Kern, Zeiger-Speichern mit Art und Track. |
| `box/src/tobibox/core.py` | änd. | `ZustandMelden` trägt `folge` und `track` (optionales Statusfeld `folge`). |
| `box/tests/fixtures/audio.py` | änd. | Erzeugt zusätzlich Folgen-Ordner mit mehreren kurzen Tracks (und Dotfiles zum Ignorieren). |
| `box/tests/conftest.py` | änd. | Hilfen für die neuen Typen (`abspielen`, `zeiger`, `zeiger_speichern`, `ppos`), Folgen-Tobies in den Beispieldaten und der CUJ-Harnisch `CujBox` (Kern, Bibliothek, `resume.json`, simulierter Player). |
| `box/tests/unit/test_store.py`, `box/tests/unit/test_core.py` | änd. | Erwartungen an die neuen Typen angepasst (Zeiger-Schlüssel, Schema 2, `ZustandMelden`); `test_core.py` zusätzlich Tracks im Kern. |
| `box/tests/integration/test_app_e2e.py` | änd. | Kettentest mit echtem MPD: Folgen-Tobie mit drei Tracks. |
| `box/tests/unit/test_session_restregel.py`, `box/tests/unit/test_audiodauer.py` | neu (Entscheidung I, 09.11.) | Restregel: Rest unter, an und über 15 s, Folge unter 60 s, unbekannte Dauer, mehrere Tracks, Serie in der Mitte und am Ende, Folgen-Tobie, Hauptknopf, Dienst-Neustart, Einschalten, Überraschungs-Serie. Dauer aus Kopfdaten und in der Bibliothek. |
| `box/src/tobibox/session.py`, `box/src/tobibox/pointer.py`, `box/src/tobibox/store.py`, `box/src/tobibox/events.py` | änd. (Entscheidung N, 09.11.) | Lesezeichen mit Ablauf: `Zeiger.benutzt_wall`, `ZeigerSpeichern.wall`, `Konfig.lesezeichen_tage`; `session._lesezeichen` vor `_rest_regel` in `_start`; `pointer.lesezeichen_abgelaufen` und `stempel_faellig`; `resume.json` mit optionalem `benutzt_am`, `validiere_konfig` prüft `lesezeichen_tage` (ganze Zahl 0 bis 365, Vorgabe 14). |
| `box/tests/unit/test_session_lesezeichen.py`, `box/tests/unit/test_store_lesezeichen.py` | neu (Entscheidung N, 09.11.) | Abgelaufen, nicht abgelaufen, genau 14 Tage, 0 = nie, unsichere Uhr, Zeiger ohne Zeitstempel, Serie gegen Folge, Zusammenspiel mit der Restregel, alle Wege des Fortsetzens, Zeitstempel beim Speichern; `benutzt_am` und `lesezeichen_tage` lesen, prüfen, schreiben. |
| `box/tests/unit/test_library.py` | änd. | Folge als Datei und als Ordner, Track-Reihenfolge, Dotfiles, leerer Folgen-Ordner, Serie „Einzelfolgen“. |
| `box/tests/unit/test_pointer.py` | änd. | Folgenende für `serie` und `folge`, Vor / Zurück nach Track (3-s-Grenze, erster und letzter Track), fehlender Track. |
| `box/tests/unit/test_session.py` | änd. | Neue Zeilen der Tabelle „Wiedergabe-Sitzung“: `TrackWechsel`, Folgenende je Ziel, Vor, Zurück, `beendet` mit Hauptknopf und Zurück, `PlayerPosition` nur bei passendem Zeiger, `TrackWechsel` und Folgenende in allen Zuständen mit laufendem MPD, Zuordnung auf fehlende Serie oder Folge (`serie_fehlt`, `folge_fehlt`). **Enthält auch die Tests „Hauptknopf kurz je Zustand“** (früher als eigene Datei `test_session_hauptknopf.py` in AP 4.2 vorgesehen; zusammengeführt). |
| `box/tests/unit/test_store_migration.py` | neu | Migrationstest: `resume.json` Version 1 wird im Speicher zu Version 2 (alle Einträge Track 0, keine Folgen-Zeiger), `config.json` Version 1 wird zu `ziel`; neuere Version wird abgelehnt. |
| `box/tests/integration/test_player_mpd.py` | änd. | Gegen echtes MPD: Folge mit mehreren Tracks spielt durch, `TrackWechsel` je Wechsel, `FolgeZuEnde` nur nach dem letzten Track, Resume per `seek` in Track 2, fehlender oder unlesbarer Track (Mitte, Ende, Start, alle) wird übersprungen. |
| `box/tests/cuj/test_cuj01_folgen_tobie.py` | neu | CUJ 1 und 3 für einen Tobie auf eine einzelne Folge: spielt diese Folge; am Ende Pause, Zeiger zurück auf den Anfang; erneutes Auflegen spielt von vorn; Serien-Zeiger derselben Serie bleibt unberührt. |
| `box/tests/cuj/test_cuj01_folge_mit_tracks.py` | neu | Folge mit mehreren Tracks: Tracks nacheinander ohne Pause, Pause erst am Ende der Folge, Resume mitten im zweiten Track, Vor / Zurück nach Track (Serien-Tobie: letzter Track → nächste Folge; Folgen-Tobie: Hinweiston). |

Abnahme AP 1.7:

- Alle genannten Tests sind grün, auch die unveränderten aus AP 1.2a, 1.2b und 1.3.
- Eine Folge mit drei Tracks spielt ohne Pause durch; die Pause und der Zeiger-Sprung kommen erst am Ende der ganzen Folge.
- Ein Folgen-Tobie spielt nach dem Ende beim nächsten Auflegen von vorn; ein Serien-Tobie derselben Serie macht an seinem eigenen Zeiger weiter.
- Der Migrationstest für `resume.json` (und `config.json`) ist grün.
- Hauptknopf kurz und Zurück in `beendet` sind je Ziel (`serie`, `folge`) getestet; Zurück nimmt die gemerkte, eben beendete Folge (Index per Nachschlagen, Grund `zurueck`).
- Ein Folgen-Tobie auf eine fehlende Folge und eine Zuordnung auf eine fehlende Serie spielen die Überraschungs-Serie, ohne `Melden` (Protokoll `folge_fehlt` bzw. `serie_fehlt`).
- `KonfigGeladen` mit Ziel `folge` wechselt bei liegendem Tobie wie bei `serie` (Punkt 14 im Vertrag).
- Fortsetzen nach MPD-Verlust spielt mit Track und Position des Zeigers.
- Unter „stumm“ startet weder Vor noch Zurück noch der Hauptknopf eine Wiedergabe, auch nicht in `beendet` (nur Hinweiston).
- Ein Neustart des Lesers (`LeserHallo`, Wiedermeldung) startet nie eine Wiedergabe, auch nicht bei einem Folgen-Zeiger.
- Das neu gerechnete Schreibbudget (höchstens 320 Zeiger-Schreibungen pro Tag bei 2 h Wiedergabe, 40 Pausen oder Wechseln und 40 Track-Wechseln) ist als Test mit simulierter Uhr belegt.
- `PlayerPosition` wird nur in `spielt` und `unbekannt` und nur bei passender Serie, Folge und Track übernommen; `TrackWechsel` und Folgenende führen den Zeiger in `unbekannt`, beim Ausblenden wegen „stumm“ und in der MPD-Frist nach (Folgenende dort: `beendet` bzw. `gehalten`).
- Ein fehlender oder unlesbarer Track in einer Folge mit mehreren Tracks wird übersprungen; nur nach dem letzten Track gilt die Folge als zu Ende.
- `session.py` und `core.py` importieren weiter kein Ein-/Ausgabe-Modul.

#### AP 1.6 Integration Stufe 1 und Messung (Sonnet)

Ergebnis: Die CUJ-Tests der Stufe laufen, die Messung liegt vor. Das AP führt
Änderungen zusammen, falls parallele APs `core.py`, `session.py` oder `app.py`
berührt haben (Grundregel). **Abhängig von AP 1.7** (läuft danach, Entscheidung F, 05.11.).

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/core.py`, `box/src/tobibox/session.py`, `box/src/tobibox/app.py` | änd. | Nur Zusammenführen und Fehler beheben, die die CUJ-Tests zeigen. |
| `box/tests/cuj/test_cuj01_bekannte_figur.py` | neu | CUJ 1: Kette gelesen → entprellt → zugeordnet → spielt, mit Vorgangs-ID; Folge 1 ohne Zeiger. |
| `box/tests/cuj/test_cuj02_abheben.py` | neu | CUJ 2: Pause, Zeiger gespeichert. |
| `box/tests/cuj/test_cuj05_nfc_karte.py` | neu | CUJ 5: Karte verhält sich wie CUJ 1 bis 4. |
| `box/tests/cuj/test_cuj06_gesperrter_tonie.py` | neu | CUJ 6: Überraschungs-Serie, kurze Aussetzer starten sie nicht neu. |
| `box/tests/cuj/test_cuj08_figur_verrutscht.py` | neu | CUJ 8 aus Sicht des Dienstes: Lese-Lücken (keine Zeile der Firmware) und gleiche Kennung nach der Lücke führen zu keiner Pause und keinem Neustart. Die verfälschte Kennung prüfen die nativen Firmware-Tests (AP 1.1). |
| `box/tests/cuj/test_cuj13_leser_ausfall.py` | neu | CUJ 13: `seq`-Rücksetzen, Abheben während der Unterbrechung, Wächter-Alarm mit 3,0-s-Karenz (Vertrag 9.1). |
| `box/tools/measure_audio_latency.py` | neu | Misst die Zeit vom Auflegen (Zeitstempel im Ereignisprotokoll) bis zum ersten Ton in einer Aufnahme am Ausgang. |
| `docs/timing.md` | neu | Messung je Schritt, mit Methode und Ergebnis (siehe Abnahme Stufe 1). |

Abnahme AP 1.6:

- Alle sechs CUJ-Tests sind grün; die zwei CUJ-Tests aus AP 1.7 bleiben grün.
- `docs/timing.md` ist ausgefüllt.

**Abnahme Stufe 1**

- Alle CUJ-Tests und übrigen Tests sind grün (pytest und PlatformIO `native`); die CI ist grün.
- Tobias führt am Mac mit echtem Leser CUJ 1, 2, 5, 6, 8 und 13 vor.
- Dazu ein Leser-Neustart: USB-Kabel bei spielendem Tobie ziehen und stecken; ein zweites Mal mit Abheben während der Unterbrechung.
- Nach Abheben, Neustart des Dienstes und erneutem Auflegen spielt der Tobie an der gespeicherten Stelle weiter (Zeigerlogik).
- Tobias führt einen Tobie auf eine einzelne Folge und einen Tobie mit mehreren Tracks vor (AP 1.7, Entscheidung F, 05.11.): Tracks spielen ohne Pause, Pause erst am Ende der Folge, Folgen-Tobie spielt danach von vorn.
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
| `box/tests/cuj/test_cuj03_resume.py` | neu (Entscheidung I, 09.11.: ergänzt um die Restregel) | CUJ 3: Resume mit 3-s-Rücksprung, auch nach Neustart; Folge zu Ende bei liegendem Tobie (Pause, Zeiger auf die nächste Folge, nichts passiert bis Abheben und Auflegen; nach der letzten Folge Zeiger auf Folge 1); Resume mitten im zweiten Track einer Folge; Folgen-Tobie spielt nach dem Ende von vorn (Entscheidung F, 05.11.). Entscheidung N, 09.11.: Lesezeichen mit Ablauf (14 Tage, Serie bleibt in der Folge, 0 = nie, unsichere Uhr, Zeiger ohne Zeitstempel, vor der Restregel, alle Wege des Fortsetzens). |
| `box/tests/cuj/test_cuj04_andere_figur.py` | neu | CUJ 4: Zeiger der alten Serie bleibt, neue Serie läuft an ihrem Zeiger oder bei Folge 1. Entscheidung N, 09.11.: jeder Zeiger altert für sich, andere Tobies dazwischen halten ihn nicht am Leben. |
| `box/tests/cuj/test_cuj20_figur_beim_start.py` | neu | CUJ 20: Tobie liegt beim Start (bekannt: Zeiger; unbekannt: Überraschungs-Serie); Dienst-Neustart mit liegendem Tobie bleibt `pausiert`, Hauptknopf spielt am Zeiger (Entscheidung G, 06.11.). |
| `box/tests/integration/test_resume_neustart.py` | neu | Dienst hart beenden und neu starten; Zeiger ist da, höchstens 30 s Wiedergabe verloren. |

Abnahme AP 2.1:

- Alle Tests sind grün.
- Die Stromausfall-Grenze von 30 s ist im Test belegt.

#### AP 2.2 Unbekannte Tobies, Lernmodus, Simulations-Treiber (Sonnet)

Ergebnis: Teilautomat Lernmodus, Ereignis-Ausgang mit Bestätigung und der
Simulations-Treiber `sim` mit Unix-Socket. Die Bestätigung kommt in dieser Stufe
von `tobibox sim ack`; HA ersetzt sie in Stufe 3a.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/learn.py` | neu | Teilautomat Lernmodus (Tabelle „Lernmodus“): 2-min-Frist auf der Box und Ablaufzeit des Befehls nach `mqtt-v1.md`. |
| `box/src/tobibox/outbox.py` | neu | Ereignis-Ausgang mit Bestätigung: `unknown.json` führen; Eintrag erst löschen, wenn das Ereignis `bestätigt` eintrifft. |
| `box/src/tobibox/sim.py` | neu | **Gemeinsamer Simulations-Treiber:** lauscht auf dem Unix-Socket `sim.sock` im Zustandsverzeichnis, liest JSON-Zeilen und macht Ereignisse daraus. Befehle in Stufe 2: `learn`, `ack`, `card` sowie (aus AP 2.4) `learn_abort` (Lernmodus abbrechen, CLI: `tobibox sim learn-abort`) und `status` (Antwort mit dem Status des Dienstes für `tobibox status`, erzeugt kein Ereignis). Spätere Stufen erweitern ihn. |
| `box/tests/unit/test_learn.py` | neu | Alle Zeilen der Tabelle „Lernmodus“, abgelaufener Befehl wird ignoriert. Entscheidung H (07.11.): zusätzlich `box/tests/unit/test_session_lernwarten.py` für das stille Warten der Sitzung (Zuordnung, abgelehnt, Frist 10 s, Abheben, Tasten, bekannter Tobie). |
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
| `box/sounds/sprache/*.wav` | neu | (09.11., Sprach-Töne für Tests) Gesprochener Satz mit denselben Namen, dazu `pruef_<punkt>_ok`, `pruef_<punkt>_fehler` und `pruef_leser_simulation`; Auswahl über `[toene] ordner`. Fehlt ein Prüfpunkt-Ton, gilt `pruef_ok`/`pruef_fehler`. |
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
| `box/src/tobibox/session.py` | änd. | Karte mit Ziel `aktion` löst die Aktion aus statt einer Serie (Status: Tonfolge); Fehler beheben, die die Tests aus AP 2.1 zeigen. |
| `box/src/tobibox/app.py` | änd. | `outbox` und `sim` verdrahten. |
| `box/src/tobibox/cli.py` | änd. | `tobibox status` ausführlich; `tobibox sim learn`, `tobibox sim ack` und `tobibox sim card` (Karte als Aktion in `config.json` zuordnen, bis HA das in Stufe 3a übernimmt; schreibt das Feld `ziel` der Version 2, `data-model.md`, Abschnitt 2, Entscheidung F, 05.11.). |
| `box/tests/cuj/test_cuj07a_unbekannte_figur.py` | neu | CUJ 7a: Überraschungs-Serie, Eintrag in `unknown.json`, Löschen erst nach `ack`, Wechsel auf die Serie nach der Zuordnung. |
| `box/tests/cuj/test_cuj07b_lernmodus.py` | neu | CUJ 7b ohne HA: Lernmodus per `tobibox sim learn`, Frist 2 min, Abbruch, abgelaufener Befehl. Entscheidung H (07.11.): kein Ton `unbekannt` und keine Überraschung zwischen Auflegen und Zuordnung; abgelehnt, Frist 10 s, Abheben, Tasten. |
| `box/tests/cuj/test_cuj11_status.py` | neu | CUJ 11: Status-Admin-Karte als pytest-Tabelle. |
| `box/tests/integration/test_sim_cli.py` | neu | `tobibox sim …` als eigener Prozess gegen den laufenden Dienst. |
| `box/src/tobibox/ha_ersatz.py` | neu | HA-Ersatz bis Stufe 3a: schreibt nach dem Lernlauf die Zuordnung in `config.json` (Revision + 1) und bestätigt sie. Spielt die Rolle von HA; Stufe 3a ersetzt ihn durch MQTT. |
| `box/src/tobibox/status.py` | neu | Statussammler: merkt sich die zuletzt gesehenen Werte (Leser, Netz, Zustand, Konfiguration) für `tobibox status` und die Status-Karte. Kein Teil des Kerns. |
| `box/src/tobibox/ausgang.py` | neu | Gemeinsame Verdrahtung von Outbox, `sim` und HA-Ersatz. `App` und der Testaufbau nutzen dieselbe Klasse, damit die Tests den echten Code prüfen. |
| `box/tests/cuj/test_cuj07b_app.py` | neu | CUJ 7b gegen die echte `App`: Lernmodus mit Frist und Abbruch, bestehende Zuordnung, `sim=true` in den Protokollzeilen. Entscheidung H (07.11.): kein Ton `unbekannt` und keine Überraschung zwischen Auflegen und Zuordnung; abgelehnt, Frist 10 s, Abheben, Tasten. |

Abnahme AP 2.4:

- Die CUJ-Tests 7a, 7b und 11 sind grün.
- Die Tests aus AP 2.1 sind grün.

**Umgesetzt (07.11.):**

- Am Socket `sim.sock` kommen zwei Befehle dazu: `learn_abort` (CLI: `tobibox sim learn-abort`) und `status`. Den Status holt man mit `tobibox status`, nicht mit `tobibox sim`. Er erzeugt kein Ereignis.
- `tobibox sim learn --ueberschreiben` ersetzt bis Stufe 3a die Rückfrage, die HA vor dem Überschreiben einer bestehenden Zuordnung stellt. Ohne den Schalter bleibt die alte Zuordnung.
- `leser.geraet = "sim"` heißt: kein Leser. Der Prüfpunkt Leser zeigt dann `simulation`.
- Der Prüfpunkt Netz ist in Stufe 2 immer ein Fehler, weil es noch keinen Broker (MQTT) gibt. Das entspricht dem Vertrag.
- Exit-Codes der CLI: `tobibox sim` 0 angenommen, 1 abgelehnt, 2 Eingabe, 3 Dienst nicht erreichbar, 4 keine Berechtigung auf `sim.sock`. `tobibox status` 0 (Medien und Speicher ok, Leser kein Fehler), 1 (sonst), 2 (Konfiguration nicht lesbar).

**Abnahme Stufe 2**

- Alle Punkte der Abnahme Stufe 1 gelten weiter.
- Tobias führt Resume über einen Neustart vor.
- Tobias führt den Lernmodus per `tobibox sim learn` und die Bestätigung per `tobibox sim ack` vor.
- CUJ 20 (Tobie liegt beim Start) ist vorgeführt.
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
| `deploy/pi/asound.conf` | neu | ALSA-`softvol` mit `max_dB`: die harte Kappung der Lautstärke. (Entscheidung J, 09.11.: dazu ein zweites `softvol`-Gerät für die Töne mit demselben `max_dB` und eigenem Regler auf 100 %; `softvol_bereich_db` in `tobibox.toml` muss zu `max_dB − min_dB` passen; MPD-Mixer `hardware` am ersten Regler.) |
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
| Auflegen eines bekannten Tobies, während ein Sync läuft | ≤ 1,0 s; wird erst nach AP 3.4 am Pi gemessen (Abnahme Stufe 3a) |
| Abheben bis Pause | ≤ 1,5 s |
| Tobie liegt beim Start (CUJ 20) | spielt, sobald „bereit“ (nur nach Einschalten; nach Dienst-Neustart bleibt er `pausiert`, Entscheidung G, 06.11.) |
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
| HA auf **2026.11.x** aktualisieren und die genaue Patch-Version nennen (Mosquitto-Add-on 7.1.3) | feste Version für die HA-Tests | vor AP 3.1 |
| Beispieldateien (m4b-Hörbuch, mp3-Serienfolge, CD-Rip mit mehreren Dateien, Datei ohne Tags; Entscheidung M) | Tag-Schlüssel und Folgen-Nummer belegen | vor AP 3.1 |
| Ordner `tobibox/eingang/` auf dem NAS anlegen, HA Schreibrecht (Entscheidung M) | Eingang, Upload | vor AP 3.5 |
| Namen (SSIDs) von Heim-WLAN und Handy-Hotspot | `net.py`, Konfiguration | vor AP 3.3 |
| QNAP: rsync-Daemon mit Modul `medien` (nur lesend) und den Zugangsdaten | AP 3.4 | vor AP 3.4 |
| CPU-Architektur des QNAP: **bekannt**, QNAP TS-464eU-8G (Celeron N5095), amd64 | Container-Bild (Stufe 3b) | erledigt (09.11.) |
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
| `homeassistant/custom_components/tobibox/store.py` | neu | Konfiguration (Zuordnungen mit optionalem `name`, Leise-Zeiten, Gute-Nacht-Einstellungen) mit einer Revision und einer Listen-ID im HA-Speicher; **erst veröffentlichen, dann exportieren** (Export im Hintergrund mit Wiederholung, Fehler sichtbar); Zustand `ok` / `leer_neu` / `export_neuer`, Befehle `konfig/export_lesen` und `konfig/aus_export` (Vertrag W, Abschnitt 13); Letzte 20 Box-Meldungen und die letzten 20 Lernmodus-Vorgänge im HA-Speicher. |
| `homeassistant/custom_components/tobibox/eingang.py` | neu | **(Entscheidung M, 09.11.)** Eingang lesen (Ruhezeit), Tags mit `ffprobe` (gehärtet, Vertrag W 5.4), Gruppieren, Serie bestimmen und zusammenführen, Reihenfolge von Folgen und Tracks, Prüfsummen und Hash-Index, Einsortieren in `medien/` (Vertrag W, Abschnitt 11), Protokoll der letzten 100 Einträge im HA-Speicher. Kein Code in `media.py`, der das Dateisystem anders anfasst als dort beschrieben. |
| `homeassistant/custom_components/tobibox/media.py` | neu | `serie.json` lesen/schreiben (mit `angelegt_am`, `typ`, `folgen_info`, `pruefen`), Namensregeln und reservierte Ordner (Vertrag W, Abschnitt 12), Serie löschen / Folge verschieben / Serien zusammenführen, Papierkorb mit `meta.json`, neue Ordner/Dateien erkennen (neue Dateien und neue Folgen-Ordner hinten an die Reihenfolge (Entscheidung F, 05.11.)), Format- und Kopierschutz-Prüfung (D5), Speicheranzeige aus den Box-Meldungen, Papierkorb ohne Automatik (je Eintrag `_papierkorb/<id>/meta.json`), Datei-Zugriffe über `async_add_executor_job`. |
| `homeassistant/custom_components/tobibox/mqtt.py` | neu | `tobibox/config` veröffentlichen („Liste neu ausrollen“ = neue Listen-ID; `ack` im Lernmodus erst nach dem PUBACK der Konfiguration), Box-Ereignisse empfangen und idempotent verarbeiten, Kennungen auf `…/ack` bestätigen, Befehle mit Ablaufzeit senden, abgelehnte Listen anzeigen. |
| `homeassistant/custom_components/tobibox/websocket_api.py` | neu | Die WebSocket-Befehle nach Vertrag W. |
| `homeassistant/custom_components/tobibox/http.py` | neu | Upload-Endpunkt mit Anmeldung (nur Audioformate nach D5) in den **Eingang**: Abschluss mit `asyncio.shield` unter der Sperre des Eingangs, Zwischendatei mit Zufallsnamen, Namens-Suffix statt Überschreiben, Ergebnis je `upload_id` merken, höchstens 2 gleichzeitige Uploads, Platzprüfung vorab (Vertrag W, Abschnitt 5). |
| `homeassistant/custom_components/tobibox/services.yaml` | neu | Aktionen. |
| `homeassistant/custom_components/tobibox/strings.json` | neu | Texte (Quelle). |
| `homeassistant/custom_components/tobibox/translations/de.json` | neu | Deutsche Texte. |
| `homeassistant/mosquitto/acl.conf.example` | neu | Nur `acl_file /share/mosquitto/accesscontrollist` (09.11., Befund AP 3.1: eine `*.conf` liest das Add-on als Konfiguration). |
| `homeassistant/mosquitto/accesscontrollist.example` | neu | Broker-Rechte ohne Endung `.conf` (09.11., Befund AP 3.1): ein Konto je Box, Themenrechte wie in Baustein 4; `homeassistant` und `addons` unbeschränkt. |
| `homeassistant/mosquitto/mosquitto-addon.example.yaml` | neu | Add-on-Einstellung mit `customize.active: true` und `logins` (Box-Konten ohne HA-Admin). |
| `homeassistant/requirements-test.txt` | neu | Feste HA-Version und `pytest-homeassistant-custom-component`, passend zur HA-Version. |
| `homeassistant/README.md` | neu | Installation der Integration, getestete HA-Version. |
| `homeassistant/tests/conftest.py` | neu | Fixtures: Test-Medienordner, Fake-Box. |
| `homeassistant/tests/test_store.py` | neu | Revision und Listen-ID, Export auf das NAS. |
| `homeassistant/tests/test_media.py` | neu | Neue Ordner/Dateien, `serie.json`-Regeln, doppelte IDs, Papierkorb (`meta.json`, Serie und Folge, Wiederherstellen), DRM-Prüfung (`drms`, Probedekodierung), Namensregeln (SMB-Zeichen, Groß-/Kleinschreibung, NFC, Kürzen an Zeichengrenzen), reservierte Ordner, Verschieben und Zusammenführen mit umgeschriebenen Zuordnungen. |
| `homeassistant/tests/test_eingang.py` | neu | **(Entscheidung M)** Jede Zeile T1 bis T20 aus Vertrag W, 11.12, dazu Ruhezeit, Gruppieren, Vorrang der Serie, Zusammenführen, Folgen- und Track-Reihenfolge, Widersprüche, Kopierschutz (ganze Gruppe bleibt), Doppelte (Prüfsumme), Suffix, Abbruch zwischen Verschieben und `serie.json`. |
| `homeassistant/tests/test_mqtt.py` | neu | Veröffentlichen, Bestätigung `…/ack`, Ablaufzeit der Befehle, Idempotenz. |
| `homeassistant/tests/test_websocket_api.py` | neu | Jeder Befehl aus Vertrag W: gültig und ungültig. |
| `homeassistant/tests/test_upload.py` | neu | Upload größer als 16 MiB im Strom (z. B. **40 MiB**, belegt, dass die feste HA-Version das Streaming nicht begrenzt); falsches Format wird abgelehnt; `ffprobe` nur mit `-protocol_whitelist file` und erzwungenem Format; ohne Anmeldung abgelehnt (401); Abbruch des Clients im Empfang (nichts bleibt) und im Abschluss (`shield`: Datei und Ergebnis da); zwei Uploads mit gleichem Namen (Suffix, nie Überschreiben); gleiche `upload_id` parallel (`upload_laeuft`); Platzprüfung. |
| `homeassistant/tests/test_restore.py` | neu | „HA-Wiederherstellung mit neuer Listen-ID und niedriger Revision“ und „Liste neu ausrollen“; **leerer Speicher** (`leer_neu`: nichts veröffentlicht, Befehle `konfig_nicht_bereit`), Erststart, Export neuer, `konfig/aus_export`, Box `voraus`, Export schlägt fehl (Vertrag W, 13.7). |

Abnahme AP 3.1:

- Alle HA-Tests sind grün, in eigener venv mit der festen HA-Version.
- Der Upload-Test belegt, dass eine Datei über 16 MiB (40 MiB) ankommt.
- Die Tests aus `test_eingang.py` sind grün; die Tag-Schlüssel sind mit den Beispieldateien von Tobias belegt (Vertrag W, 11.2).
- Eine Kennung wird erst nach `…/ack` als bestätigt geführt.

#### AP 3.2 HA-Seite (Sonnet)

Ergebnis: Die Seite „Tobi Box“, bedienbar am Handy.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `homeassistant/custom_components/tobibox/frontend/tobibox-panel.js` | neu | Serienliste, Folgen ziehen, Hochladen (in den Eingang, optional mit Serie als Vorgabe), Umbenennen (Anzeigenamen von Serie und Folge), Serie löschen und Löschen mit Rückfrage zu betroffenen Tobies, Folge verschieben, Serien zusammenführen, Ansicht „Eingang“ (erkannt, „bitte prüfen“, Hinweise, erneut einsortieren; Entscheidung M, 09.11.), Tobie-Namen, Warnungen zu Konfiguration (leerer Speicher, Export neuer, Export fehlgeschlagen, Box mit neuerem Stand), Neue Tobies, Lernmodus (mit Wahl Serie oder Folge), Zuordnen mit Typ `serie` / `folge` (Entscheidung F, 05.11.), Zuordnen von Aktionskarten (Status, Gute Nacht), Box-Status mit freiem Speicher, Aktionen „Liste neu ausrollen“ und „Papierkorb leeren“. |
| `homeassistant/custom_components/tobibox/frontend/lit-all.min.js` | neu | Lit in fester Version, eingecheckt (kein Laden aus dem Netz). |
| `homeassistant/tests/frontend/mock-hass.mjs` | neu | Mock für die HA-WebSocket-Schnittstelle. |
| `homeassistant/tests/frontend/panel.test.mjs` | neu | Mit `node --test`: Das Modul lädt; jeder Aufruf geht mit den Namen und Feldern aus Vertrag W gegen den Mock (auch `stand`, `erwartet_ziel`, `tobies_bestaetigt`); Fehlerantworten werden angezeigt; Namen werden nur als Text dargestellt. |

Abnahme AP 3.2:

- `node --test homeassistant/tests/frontend` ist grün.
- Tobias bedient die Seite am Handy über Nabu Casa (Vorführung).

#### AP 3.3 Box-Dienst: HA, Netz, Strom (Sonnet)

Ergebnis: Die Box spricht MQTT, erkennt die Netz-Klasse und kennt die
Strom-Schnittstelle. Die Eingänge in `sim.py` und `cli.py` trägt AP 3.7 ein.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/ha.py` | neu | MQTT mit eigenem Konto (QoS 1, dauerhafte Sitzung), Discovery, Konfiguration nach der Revisionsregel (Listen-ID) übernehmen (Migration und Prüfung ruft `ha.py` aus `store.py` auf, die eine Funktion aus AP 1.7 `validiere_konfig`, keine eigene Prüfung; Entscheidung F, 05.11.), abgelehnte Listen melden, unbekannte Kennungen dauerhaft je Kennung veröffentlichen und `…/ack` als Ereignis `bestätigt` weitergeben, Befehle mit Ablaufzeit prüfen, HA-Sensoren inkl. Status und freiem Speicherplatz. |
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
| `box/src/tobibox/sync.py` | neu | rsync gegen den rsync-Daemon des QNAP (Modul `medien`, nur lesend) über Tailscale; Regeln Heim/Hotspot/Akku (im Hotspot ohne Datenlimit); `--partial-dir` und `--temp-dir` außerhalb des Medienordners auf demselben Dateisystem, **kein `--delay-updates`** (09.11., Befund AP 3.7: absolutes `--partial-dir` legt zurückgestellte Dateien flach nach Dateiname ab, zwei `serie.json` kollidieren); `--delete` mit Schutz (Abbruch bei fehlender oder leerer Quelle oder mehr als 20 % Löschungen, vorab gezählt mit `--dry-run --itemize-changes`); Platzprüfung vorab; die spielende Datei (MPD `currentsong`) per `--exclude`; **`_upload`, `_papierkorb` und `eingang` per `--exclude` ausnehmen (Entscheidung M, 09.11.)**, auch wenn das NAS-Modul sie schon auslässt; MPD neu einlesen; Sperre gegen Update; keine Abschaltung während des Syncs; `nice`/`ionice`. |
| `box/tests/unit/test_sync.py` | neu | Tests gegen einen lokalen rsync-Daemon: leere Quelle, fehlende Quelle, zu viele Löschungen, zu wenig Platz, spielende Datei ausgenommen, **Ordner `_upload`, `_papierkorb` und `eingang` in der Quelle werden nicht übertragen und nicht auf der Box gelöscht**, `--partial-dir` außerhalb des Medienordners, Netzregel. |
| `box/tests/unit/test_sync_ereignisse.py` | neu | Während eines Syncs laufen Kern-Ereignisse weiter (Auflegen wird verarbeitet). Die Latenz unter echter Last misst Abnahme Stufe 3a am Pi. |

Abnahme AP 3.4:

- Alle Tests sind grün.
- Eine laufende Datei wird nie ersetzt oder gelöscht.

#### AP 3.5 Einrichtung Tailscale, NAS und MQTT-Konten (Haiku)

Ergebnis: Anleitungen und Vorlagen für die Schritte, die nur Tobias machen kann.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `docs/betrieb/tailscale-nas.md` | neu | Schritte für die QNAP-App, das HA-Add-on, die Box-Schlüssel, die ACL und den rsync-Daemon; die Freigabe `tobibox/` mit `medien/`, `eingang/`, `export/`, `releases/` (Entscheidung M, 09.11.: `eingang/` anlegen, HA Schreibrecht). |
| `docs/betrieb/mqtt-konten.md` | neu | Konto je Box anlegen, Themenrechte, Passwörter nur auf der Box (nicht im Repo). Zwei Dateien: `acl.conf` (nur `acl_file`) und `accesscontrollist` (Regeln, ohne Endung) (09.11., Befund AP 3.1). |
| `deploy/nas/rsyncd.example.conf` | neu | Modul `medien` und Modul `releases`, beide `read only = yes`; im Modul `medien` `exclude` für `_upload`, `_papierkorb` und `eingang` (Entscheidung M, 09.11.). |
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
- Tobias führt die Seite am Handy über Nabu Casa vor, mit Uploads von 20, 150 und 500 MiB (Dauer gemessen, alle größer als die 16 MiB von HA), und eine Box am Mac.
- Einsortieren (Entscheidung M): Tobias legt seine Beispieldateien in den Eingang; Serie, Folgen und Reihenfolge sind richtig oder als „bitte prüfen“ markiert, eine Korrektur auf der Seite wirkt nach dem Sync auf der Box; `eingang/`, `_upload/` und `_papierkorb/` landen nicht auf der Box.
- Leerer HA-Speicher: Die Integration verteilt nichts, bis Tobias entschieden hat; „aus dem Export holen“ stellt die Zuordnungen samt Namen auf beiden Boxen wieder her.
- Auflegen während Sync: Am Pi innerhalb der Zeitgrenze; ohne Pi holt das der Pi-Lauf nach, sobald der Pi da ist.
- Leser-Neustart bei spielendem Tobie (CUJ 13) ist weiter bestanden.
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
| `docs/betrieb/handbuch.md` | neu | Neuinstallation, SD-Image, „was ist wo konfiguriert“, Fehlerbilder, HA-Wiederherstellung (HA-Sicherung oder NAS-Export, danach „Liste neu ausrollen“), Signierschlüssel und Pakete bauen; Reihenfolge bei Schema-Sprüngen der Konfiguration: **zuerst alle Boxen aktualisieren, danach verteilt HA die neue Version** (für Version 2 gilt das schon, es stehen keine Boxen im Feld; Entscheidung F, 05.11.). |

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

Abnahme AP 4.2:

- Vor / Zurück springt nach Track innerhalb der Folge (Zurück in den ersten 3 s: voriger Track); beim letzten Track geht Vor bei `serie` zur nächsten Folge, bei `folge` gibt es den Hinweiston (Entscheidung F, 05.11.).
- Der Drehregler ändert die Lautstärke nie über die wirksame Grenze.
- Die Tests „Hauptknopf kurz je Zustand“ stehen schon in `test_session.py` (AP 1.7, zusammengeführt, keine eigene Datei `test_session_hauptknopf.py`); `controls.py` liefert nur das Ereignis.
- Hauptknopf kurz: Play / Pause; ist eine Folge zu Ende und liegt der Tobie noch auf der Box, spielt er die nächste Folge (Entscheidung E); ohne Tobie startet nichts, nur der Hinweiston (Entscheidung Q, 10.11.).
- Hauptknopf lang: Zeiger speichern und herunterfahren.

#### AP 4.3 Leerlauf und PiSugar-Beschreibung (Sonnet), umsetzt CUJ 16

Ergebnis: Teilautomat Strom / Leerlauf.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/idle.py` | neu | Teilautomat Strom / Leerlauf: Abschaltung nach 20 min (seit Ein/Aus, 10.11.: 10 min und nur ohne Strom am Eingang; mit Strom nie), nie während Sync, Update oder Lernmodus. Am Lader wird nicht abgeschaltet, solange Sync oder Update laufen; ist keines aktiv, gilt die 20-min-Regel (seit Ein/Aus: mit Strom gibt es keine Frist). Beim Start am Lader Sync prüfen. Nutzt `power.py` aus AP 3.3. **(Ein/Aus, 10.11.: Frist jetzt 10 min und nur ohne Strom, Andocken und Abziehen, zwei Strom-Quellen, keine Wiederholung des Start-Syncs; siehe Nachtrag E1-1.)** |
| `box/tests/unit/test_idle.py` | neu | Leerlauf und Lader-Regel (mit simulierter Uhr; seit Ein/Aus, 10.11.: 10 min nur ohne Strom, zwei Quellen, Andocken und Sperre). |
| `docs/betrieb/pisugar-wecker.md` | neu | Beschreibung der PiSugar-Anbindung und Option: nächtliches Wecken am Lader über den PiSugar-Wecker (nur Beschreibung, Umsetzung nach Tobias' Entscheidung). |

Abnahme AP 4.3:

- Nach 10 min Leerlauf **ohne Strom** wird heruntergefahren (in der Simulation nur protokolliert; seit Ein/Aus, 10.11., vorher 20 min); **mit Strom nie von selbst**.
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
| `box/tests/unit/test_quiet.py` | neu | Fenstergrenzen mit simulierter Uhr; Zeit nicht vertrauenswürdig; stumm beginnt während der Wiedergabe; stumm endet bei liegendem Tobie (nichts startet). |

Abnahme AP 4.5:

- Alle Zeilen der Tabelle „Leise-Zeiten“ haben einen Test.
- Bei nicht vertrauenswürdiger Zeit wird nie stumm geschaltet.

#### AP 4.6 Gute-Nacht-Karte (Sonnet), umsetzt CUJ 14

Ergebnis: Teilautomat Gute Nacht.

| Datei | Neu/Änd. | Inhalt und Grund |
|---|---|---|
| `box/src/tobibox/bedtime.py` | neu | Teilautomat Gute Nacht: Timer mit Ausblenden über die Lautstärke-Regel; Dauer von Timer und Ausblenden aus `config.json` (Vorschlag 30 min und 60 s); die Karte ist ein Eintrag Typ `aktion` in `config.json`; funktioniert am Mac. |
| `box/tests/unit/test_bedtime.py` | neu | Timer läuft ab, Lautstärke blendet aus, Wiedergabe endet; anderer Tobie während des Timers; Abheben während des Ausblendens. |

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
| `box/src/tobibox/cli.py` | änd. | `tobibox sim key`, `tobibox sim headphones`, `tobibox sim time`. Der sim-Befehl `zeit` (`tobibox sim time`, ISO oder now) stellt die simulierte Wanduhr; Beschreibung in `docs/betrieb/mac-prototyp.md` (09.11., AP 4.8). |
| `box/src/tobibox/config.py` | änd. | `[kopfhoerer]` und `[tasten]` in der Konfiguration (Vorgabe `sim`). `pin_haupt` ist optional: Am Pi kommt der Hauptknopf über die Taste des PiSugar (09.11., AP 4.8). |
| `box/tests/cuj/test_cuj14_gute_nacht.py` | neu | Karte auflegen nach Abheben der Serien-Tobie, Timer, Ausblenden, Ende. |
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
  - Folge zu Ende bei liegendem Tobie
  - Hauptknopf kurz bei beendeter Folge mit liegendem Tobie (nächste Folge spielt) und ohne Tobie (nur Hinweiston, Entscheidung Q, 10.11.); Hauptknopf kurz, Vor und Zurück ohne Tobie in `pausiert`, `beendet`, `leer` und unter „stumm“ starten nichts
  - stumm gegen Lernmodus
  - Stumm-Beginn und Stumm-Ende
  - Gute Nacht mit neuem Tobie
  - Abheben beim Ausblenden
  - Tobie-Wechsel bei Leser-Unterbrechung
  - Leerlauf gegen Sync, Update und Lernmodus
  - Tiefstand während Sync
  - mehrere Grenzen
- Die echte Hardware ersetzt später nur den Simulations-Treiber; dann folgt die **Messung der Lautstärke am Verstärker**.

### Nachtrag 10.11.: Ein/Aus, Schritt 1 (Arbeitspakete E1-0 bis E1-8)

Freigegeben durch Tobias am 10.11. (R11). Quelle: `docs/egm/ein-aus/design_draft.md`, Abschnitt 10.1. Alles läuft am Mac und in der Simulation; Modelle nach `CLAUDE.md`.
Schritt 2 (Arbeitspakete E2-x: Firmware-Logik, `WAKE`, `SLEEP`, `CFG`, `RING_PI`, CUJ-Tests 21, 22 und 24 mit Herunterfahren, Gesamtprobelauf) folgt nach den Messungen.

| AP | Modell | Inhalt | Abhängig von |
|---|---|---|---|
| **E1-0** | Sonnet | Verträge A1 bis A19 einarbeiten (erledigt am 10.11.); Gegenlesen durch einen Goldfisch | Freigabe |
| **E1-1** | Sonnet | `idle.py` und `test_idle.py`: Frist 600 s nur ohne Strom; Strom verwirft, Abziehen beginnt neu; zwei Strom-Quellen mit Vorrang Leser; unbekannt 60 s; erste Messung ohne Rückmeldung; Sperre ab `Bereit`; Wiederholung und `start_wdh` entfernen | E1-0 |
| **E1-2** | Sonnet | `core.py` Regel 2a, `events.py` (Ton `lader`, `Bereit.fruehton`, `LaderGeaendert.quelle`, `LeserHallo.caps`), `session.py` (kein `start` bei `fruehton`), `app.py` (Marke lesen, Wartereihenfolge), Konfiguration | E1-0 |
| **E1-3** | Haiku | Ton `lader.wav` (`tools/make_sounds.py`, −18 LUFS, `lautheit.json`) | E1-0 |
| **E1-4** | Sonnet | `led.py`: Akku-Anzeige 15/5/3 %, Stufe ≥ 1, Ausnahme vom Faktor 0,4, Entprellen, 5 % während Gute Nacht; `test_led.py`; Freigabe der Ring-Rückmeldung von `idle` | E1-0, E1-1 |
| **E1-5** | Sonnet | gemeinsames Uhr-Modul, `fruehton.py`, `deploy/pi/tobibox-fruehton.service`, Test mit simulierter Uhr | E1-0 |
| **E1-6** | Sonnet | `reader.py` (`LADER`, `caps`, `LaderGeaendert(quelle="leser")`), Sim-Leser sendet `LADER` | E1-0 |
| **E1-7** | Sonnet | CUJ-Tests 16, 23, 24, 25 und die Fälle der Tabelle „Lader-Ton und Doppel-Ton“ im Entwurf (Doppel-Ton, Wackelkontakt, `pisugar-server` hängt, Strom kommt beim Herunterfahren), simulierte Uhr | E1-1 bis E1-6 |
| **E1-8** | Haiku | Doku nachziehen (`pisugar-wecker.md`, `mac-prototyp.md`, `docs/timing.md`, Plan); Messskript Bootzeit und Prüfliste | E1-7 |

**Stand der Umsetzung (E1-1 bis E1-8, 10.11.):** `idle.py` (Frist, zwei Quellen über `stromwert.py`, Sperre, `AkkuAnzeigen`), `core.py` (Regel 2a, `start` unter „stumm“ gestrichen), `session.py`
(`Bereit.fruehton`), `app.py` (Marke bei `Bereit`, Gegenmarke, Wartereihenfolge), `fruehton.py` und `uhrregel.py` (Frühdienst, gemeinsame Uhr-Regel), `deploy/pi/tobibox-fruehton.service`,
`led.py` (Akku-Anzeige 15/5/3 %, Stufe ≥ 1, Entprellen, Start-Anzeige), `reader.py`/`protocol.py` (`caps`, `LADER`), `sim.py`/`cli.py`/GUI (zweite Quelle `--source leser`), `box/sounds/lader.wav`
(auch `sounds/sprache/`), `box/tools/measure_boot.py`; Tests `test_idle.py`, `test_led.py`, `test_fruehton.py`, `test_app_fruehton.py`, `test_cuj16_leerlauf.py`, `test_cuj23_24_sockel_und_pause.py`,
`test_cuj25_andocken.py`. Abnahme am Mac: `docs/betrieb/mac-prototyp.md`, Abschnitt 14. Nachtrag der Verträge nach dem Goldfisch-Review V1 bis V17: `core-interface.md`, Änderung 10.11. „Nachtrag“.

### Dokumente, die am Ende nachgezogen werden

| Datei | Änderung |
|---|---|
| `docs/plan/stueckliste-und-psp.md`, `docs/plan/psp-baum.html` | Projektplan (Stückliste und Arbeitspaket-Baum) nachziehen: Punkte, die durch dieses Design ersetzt sind, neu fassen |
| `docs/designs/box-software.md` | angenommene Fassung dieses Dokuments |
| `CLAUDE.md` | Verweis auf Verträge und Arbeitsweise je Stufe |
