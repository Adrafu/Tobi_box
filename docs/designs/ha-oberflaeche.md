# HA-Oberfläche: Angenommenes Design (Stand Rev. 5 mit Runde 12 bis 16, 12.11.)

> **Angenommen am 12.11.** nach den Resolve-Runden 1–11 (`docs/egm/ha-ui/resolve.md`). Entstehung, Prototyp und Reviews: `docs/egm/ha-ui/`. Wo dieses Dokument „offene Fragen“ nennt, gelten die Antworten aus `resolve.md`. Änderungen nur mit Entscheidung von Tobias; Verträge (`docs/protocol/`, `docs/data-model.md`) ändert erst Paket A0 nach Freigabe.

> **Runde 12 (12.11.): X1–X9 eingearbeitet** (UX-Durchsicht des Prototyps v5 durch Tobias, `resolve.md` Abschnitt „Runde 12“; Prototyp jetzt v6). Neu: **vier Reiter (Start · Bibliothek · Tobies · Mehr)** mit größerer Beschriftung, „Abends“ und „Gehört“ in **„Mehr“** (3.4), freundliche **leere Zustände mit Bildern** (6.2), **Kacheln** statt Karten beim Hochladen (5.6), **Wischen** am Mini-Player (5.12), **Meldungen**: Erfolg weg nach 4,5 s, Fehler bleiben (6.3), Radien 16 und 24 px (4), Tippflächen in Listen mindestens 44 × 44 px (14), **3:1-Kontrast** für Ränder, Symbole und Warnkarten (4, 14). Rechte, Abläufe, Stufen und Verträge bleiben unverändert. Tabelle in 1.5.


> **Runde 12, X10 und X11 (12.11.):** Listenzeilen sind **ganz antippbar** mit ruhigem Pfeil „›“ rechts statt „Ändern“-Knopf (4, 5.7, 14); **keine vorsorglichen Erklärtexte** mehr („Hinzufügen“ ohne Formatzeile und NAS-Hinweis), Fehler erst im Moment, wenn sie auftreten (5.6, 6, 6.1).

> **Runde 12, X12 (12.11.): Playlists leben in der Bibliothek, nicht unter „Mehr“, und funktionieren wie bei Spotify** (Abschnitt 13, 5.2, 5.3). Gebaut wird weiter erst in Stufe C; im Prototyp stehen sie mit dem Etikett „Stufe C – Vorschau“ (Schalter „Stufen zeigen“). Die Hochlade-Kachel „Playlist“ entfällt (Vorschlag, 5.6, 13.7).

> **Runde 13 (12.11., X13 bis X19):** Warteschlange „Nächster neuer Tobie auf <Box> spielt …“ ersetzt im Alltag den Lernmodus mit Countdown (5.13; **Vertragsänderung offen**), Sperre und Geschwindigkeit im „⋯“ des Players (5.12), „Technik“ in Unterseiten (5.9), Suchvorschläge mit Tobies zuerst (5.2), tonale Knöpfe (4), aktiver Reiter als Pille und Reiterleiste als Glas (3.1, 4).

> **Runde 14 (12.11., X20 bis X26):** **X20 („Einem Tobie geben“): damals zurückgestellt, seit Runde 16 angenommen und umgesetzt (siehe unten).** X21 Box-Detailseite (5.1.2; seit Runde 15 über „Geräte“ erreicht), X22 Zeitwähler `<input type="time">` (5.8), X23 endloses Nachladen (5.2), X24 Seitenleiste ab 900 px (3.1), X25 „⋯“ abgesetzt (4), X26 **Wochenansicht der Leise-Zeiten** (5.8; „Wochenplan-Grafik später“, Frage 6, ist damit überholt). Prototyp jetzt v7.

> **Runde 15 (12.11., X27 bis X30): Umbau der Architektur.** **Start = Schaufenster für Inhalte** ohne Boxen, Uploads und Admin-Blöcke (5.1). Der Reiter **„Mehr“ entfällt**; der vierte Reiter heißt **„Geräte“** (Lautsprecher-Symbol) und zeigt Box-Karten, die Karte „Neuer Tobie aufgelegt“ (nur dort, mit Punkt am Reiter), **Abends** (Gute Nacht, Leise-Zeiten) und in Stufe B **Gehört** (3.4). **Hinzufügen** ist ein „+“ im Kopf der Bibliothek, laufende Uploads stehen als Band oben in der Bibliothek (5.2, 5.6). X1 (vier Reiter mit „Mehr“) und der Startknopf „Abends“ sind überholt; „Abends“ ist von überall **2 Taps** entfernt (7.4, 8); die Box-Karte aus X21 liegt auf „Geräte“ statt auf dem Start. **Wo dieses Dokument weiter unten noch „Mehr“ oder die Startseite mit Box-Karten nennt, gilt Runde 15 (Geräte).** Prototyp v7.

> **Runde 16 (12.11., Rückmeldung zu Prototyp v7 und Vorschau X20; `resolve.md`, Abschnitt „Runde 16“): Tobie zuerst.** **X20 angenommen** (Vorschau `docs/egm/ha-ui/x20_tobie_zuerst.html`, bleibt als Beleg; Tobias: „super“): **Zuordnen beginnt immer beim Tobie.** Der Reiter „Tobies“ ist ein **Regal** mit der Kachel „+ Neuer Tobie“ (5.7); ein Tipp auf einen Tobie fragt „**Was soll … spielen?**“ (5.4); ein neuer Tobie entsteht über „**Leg ihn jetzt auf eine Box**“ (Weg 1) oder „**Später auflegen**“ (Weg 2, Warteschlange X13; 7.1, 5.13). **In der Bibliothek gibt es keinen Zuordnen-Knopf mehr**: Serien-, Playlist- und Folgenzeilen zeigen „**Gespielt von**“ als Chips, bei fehlendem Tobie „**Noch kein Tobie · Einem Tobie geben …**“ (5.3, 5.4). Dazu die Ergänzungen: Link „Einem Tobie geben …“ bleibt in der Bibliothek (a); bei einer einzelnen Folge steht der **Serienname** in der Kachel (b); „**Gute-Nacht-Karte**“ als eigene Zeile bei der Zielwahl (c); nach dem Zuordnen **„Rückgängig“ etwa 6 s** (d, 6.3). **X12a:** keine Hochlade-Kachel „Neue Playlist“, danach „Zur Playlist hinzufügen“ (5.6, 13.7). **X13a:** **Lernmodus nur für Administratoren** (`lernmodus/start` wieder `admin`, 10.2; Vertragsbedarf für A0-Q in 5.13). **X22a:** Gute Nacht bleibt eine **Dauer mit Schnellwahl** (5.8). **X27a:** „Am Handy weiterhören“ und „Neu hinzugefügt“ **nur auf dem Start**, nicht mehr in der Bibliothek (5.1, 5.2). **X31:** der **Mini-Player sitzt bündig auf der Reiterleiste** (0 px Abstand, auch mit Safe-Area; ab 900 px bündig am unteren Rand des Inhalts; A6). **Wo dieses Dokument weiter unten noch „Tobie zuordnen“, das Blatt „Tobie anlernen“ oder die Karte „Neuer Tobie“ mit Kacheln nennt, gilt Runde 16.** Prototyp jetzt **v8**.

Stand 12.11. · **Rev. 5** (arbeitet das Goldfisch-Review `review_goldfisch_rev4.md` mit den Befunden G1 bis G31 und den nachgeprüften Punkten U2, U6, U8, U10, U15, U18, U22, U25 ein, dazu die Entscheidungen in `resolve.md`, Abschnitte „Runde 10“ und „Goldfisch-Review Rev. 4a“). Rev. 4a stand nach Runde 9, Rev. 4 nach Runde 8, Rev. 3 nach Runde 7, Rev. 2 nach dem ersten Goldfisch-Review `review_goldfisch.md` (U1 bis U26) und den Antworten Runde 4 bis 6.
Grundlage: `concepts_brief.md` (mit Abschnitt 6: Stufen A, B, C), `brainstorm.md`, `ist.md`, Vertrag W (`docs/protocol/ha-websocket-v1.md`),
`docs/data-model.md`, `docs/protocol/mqtt-v1.md`. Klickbarer Prototyp v8: `prototyp.html` (erfundene Beispieldaten; **alle Namen kommen aus einem Objekt `NAMEN` am Anfang des Scripts**: Box 1, Box 2, Person A, Person B; der Knopf „i“ oben schaltet Rolle, Aussehen, Zustand, Stufen, die gewählten Dateien beim Hochladen und **„Leer zeigen“** um).
Status: **Entwurf Rev. 5, Resolve Runde 10 abgeschlossen (Fragen 1–26 beantwortet, Fragen 27–29 neu), bereit für eine zweite Goldfisch-Runde.** Gebaut wird **Stufe A in drei Teilen** mit je eigener Abnahme: **A-1 Alltag**, **A-2 Reinhören mit Weiterhören**, **A-3 Hörkopien und Kapitel** (Abschnitt 15). B und C sind geplant, haben ihren Platz in der Oberfläche
und ihre Vertragsentwürfe (Abschnitte 12, 13), werden aber erst nach Freigabe gebaut.

**Änderungen in Runde 12** (X1 bis X11, Entscheidung Tobias; Quelle `resolve.md`; Rev.-Nummer bleibt 5):

| Nr. | Abschnitte | Änderung |
|---|---|---|
| X1, X2 | 1, 2, 3.1, 3.2, **3.4**, 5.10, 8, 9, 14 | **Vier Reiter:** Start · Bibliothek · Tobies · **Mehr**. „Abends“ und „Gehört“ wandern nach „Mehr“ (für alle Benutzer); „Technik“ bleibt der Knopf oben. Beschriftung **14 px**, Reiter **64 px** hoch, immer sichtbar |
| X3 | 5.1, 5.2, 5.7, 6, **6.2** | Leere Zustände mit eigenen kleinen Bildern (Inline-SVG, Farben aus Tokens), **einem Satz und einem Knopf** |
| X4 | 4 | Karten **16 px**, Blätter und große Kacheln **24 px** (Cover bleiben 12 px) |
| X5 | 5.6, 7.3, 14 | Wahl „Was lädst du hoch?“ als **große Kacheln** mit Symbol, kurzem Titel und **höchstens einer Zeile** Erklärung |
| X6 | 5.12, 14 | Mini-Player: **Wischen nach oben öffnet, nach unten schließt** (Knopf bleibt) |
| X7 | 6, **6.3**, 14 | **Erfolg** verschwindet nach 4,5 s; **Fehler bleiben** mit „OK“ oder lassen sich wegwischen |
| X8 | 14 | Alle Listenaktionen (Menü „⋯“, Abspielen, Pfeile, ganze Zeilen) mindestens **44 × 44 px**; **seit X10 statt „Ändern“-Knöpfen ganze Zeilen** |
| X10 | 4, 5.6, 5.7, 5.8, 5.9, 14 | **Ganze Zeile ist die Tippfläche**, rechts ruhiger Pfeil „›“ an fester Stelle; keine wiederholten umrandeten „Ändern“-Knöpfe in Listen (Tobias: „echt ungut“) |
| X11 | 5.6, 5.7, 6, 6.1 | **Keine vorsorglichen Erklärtexte** auf „Hinzufügen“ und anderen Seiten; ein Fehler erscheint erst, wenn er auftritt, genau dieser, mit dem, was zu tun ist |
| X9 | 4, 14 | Ränder, Symbole und Warnkarten mindestens **3:1**, Text 4,5:1 (Token `--line`, Rand in Warnkarten), Prüfung auch im Theme mit hellem Primärton |

**Änderungen in Rev. 5** (Befunde G1 bis G31 stehen mit „eingearbeitet (Abschnitt)“ oder „abgelehnt, weil …“ in Abschnitt 18):

| Abschnitt | Änderung |
|---|---|
| 1, 1.4, 2 | Kurzfassung; Stufe A in **drei Teilen** (A-1, A-2, A-3); Tabelle „Rev. 5 gegenüber Rev. 4“ |
| 3.1, 3.3, 5.1.1, 6, 6.1 | Kein Personenname in Texten (G24): Eintrag `verwalter` („dem Administrator“); Box-Namen im Entwurf sind „Box 1“ und „Box 2“ |
| 5.2, 5.3, 5.12 | „Hier weiterhören“ und Reihe „Am Handy weiterhören“ (G17); Suchtreffer sind Links (G25); Karte „Die Hörprobe wird vorbereitet“ |
| 5.5, 11.2 V-1, 11.3 | Cover: Maße aus dem Kopf lesen, Rumpf mit Zähler, eine Funktion für beide Wege, Pillow ins Manifest, 20 Cover je Stunde (G7); mitgeliefertes `cover.jpg` wird **kopiert**, das Original folgt der alten Regel (G11) |
| 5.6, 7.3, 6.1 | **Upload-Grenze 2 GiB** (G15, Abschnitt 5.6a); Hochladen-Blatt: „Abbrechen“ oben, „Welche Art?“, „Wohin soll es?“, Satz zu den übrigen Dateien (G26); **eine Gruppe bleibt zusammen** (`gruppe_anzahl`, G2); „Anders einsortieren“ nur für „bitte ansehen“ oder jünger als 24 Stunden (G9) |
| 5.9, 10.3 | Technik: Papierkorb mit **Mitteilung an Administratoren** und **„Letzte Stunde zurückholen“**, kein Tageslimit (G8); neues Element `tobibox-app` neben der unveränderten alten Seite (G12) |
| **5.10, 5.10.1, 12.4, 12.5, 14** | **„Gehört“ ohne Umschalter Boxen \| Reinhören und ohne Hinweistext; eine Auswahl „Wer?“** (Alle, Box 1, Box 2, Personen); Vertrag `gehoert/zusammenfassung` mit `wer`; Löschen: eigene Daten jeder, alles nur Administrator (Runde 10) |
| 10.2, 10.3 | Tabelle 10.2 vollständig (`folgen/order`, `hoerstelle/*`, neue Befehle, G20); Überraschungs-Serie nur für Administratoren als Ziel (G23); Mengen (Upload 16 GiB je Stunde, Cover, Vorziehen) |
| 11.1, 11.2 | Regel für Fähigkeiten (G22); vorhandene Feldnamen (`anzahl_folgen`, `anzahl_tobies`) und `kapitel_anzahl` (G16); neuer Befehl `audio/bereit` (G3, G4); `gruppe_anzahl` (G2); `name` bis 400 Bytes (G31) |
| 11.3, 11.4.4, 11.4.7, 11.4.8 | Abgeleitete Werte (Dauer, Spuren, Kapitel, Codecs, Hörkopie, Cover-Marke) im HA-`Store` `tobibox.medieninfo`, **nicht** in `serie.json`; `stand` rechnet nur über Name, Folgenliste und von Menschen gesetzte Felder (G10); Codec je Track (G30) |
| **11.4.1, 11.4.2, 11.4.6** | Audio-Ansicht: zwei Zweige mit je eigener Wurzel (G6); Zähler in einer `FileResponse`-Unterklasse (G5); Kodierung mit `encodeURIComponent` (G27); **Abspiel-Link 24 Stunden**, Vorabfrage per WebSocket statt 401 (G3, G4), Weitergabe-Risiko und Gegenmittel |
| **11.4.7** | **Hörkopie mit harten Grenzen** (Dauerdeckel, feste Zeitgrenze, `-t`/`-fs`, Schlange, Kontingent; gilt auch für `ffprobe`); neu Einsortiertes sofort, Bestand erst beim ersten Reinhören (G1) |
| 11.4.5 | Hörstelle: Speichern gesammelt alle 60 s (G28), `dauer_s` vom Backend (G29) |
| **15** | **Arbeitspakete neu geschnitten:** A0 (Vertrag) und A0b (Testpanel und `ffmpeg`-Messung) zuerst, dann A-1, A-2, A-3 mit Abhängigkeitsgraph, Tests und Abnahme je Teil (G13, G14, G19); neue Seite parallel unter `/tobibox-neu`, Notschalter |
| 16, 17, 18 | Fragen 14 bis 26 mit Antwort, neue Fragen 27 bis 29; Prototyp v5; Tabelle G1 bis G31 |

**Änderungen in Rev. 4** (zur Erinnerung):

| Abschnitt | Änderung |
|---|---|
| 1, 1.3 | Kurzfassung und Änderungstabelle angepasst |
| 2 | Stufe A: Hochladen in Schritten, Einzeltitel, Hörkopien, Kapitelliste; Stufe B: „Reinhören“; Stufe C: Playlist beim Hochladen, Weiterspielen über Playlist |
| 3.3 | Wort „Einzeltitel“ |
| 5.2, 5.3, 5.4 | Einzeltitel in Liste, Suche, Serienseite und als Tobie-Ziel; Hörbuch mit **Kapitelliste**; Hinweis „Hörprobe wird vorbereitet“ |
| **5.6, 7.3** | **Hinzufügen neu:** erst „Was lädst du hoch?“ (fünf Karten), dann Vorschau in Sätzen mit „Ändern“ und „Hochladen“, dann Fortschritt wie bisher; gleiche Wahl für Dateien vom NAS („Anders einsortieren“) |
| 5.9, 9 | Technik: Stand der Hörkopien; Fundorte |
| **5.10, 12.5** | **„Gehört“ bekommt den Umschalter Boxen \| Reinhören**; Regel, wer was sieht (Frage 23: alle sehen alle) |
| 5.12 | Kapitel im Player, Hörkopie, Zählung des Reinhörens |
| 6.1 | neue Fehlertexte (Hörkopie, Wunsch beim Hochladen, Anders einsortieren) |
| 8, 10.2 | Taps, Rechte der neuen Befehle |
| **11.1 bis 11.3** | **Vertragsänderungen, alle additiv:** V-7 (Hochladen mit Wunsch, `einsortierung/neu`), V-8 (Einzeltitel, Kapitel), V-9 (Hörkopie); neue Fähigkeiten `einsortier_wunsch`, `kapitel`, `hoerkopie`; neue Felder in `serie.json` |
| 11.4.2 | „Abspiel-Link“ in Alltagssprache |
| **11.4.3, 11.4.7, 11.4.8** | **Hörkopie** für Formate, die nicht jeder Browser spielt (Ort, Zeitpunkt, Speicherbedarf, Fehlerfall); **Kapitel** (Quelle, Speicherung, Anzeige) |
| 11.4.4, 11.4.6 | Dauer, Kapitel und Codec in einem `ffprobe`-Durchgang; Prüfstand (ffmpeg in HA belegt) |
| 12.2.1, 12.3, 12.4 | Zählregel mit 5-Minuten-Zusammenfassung ist jetzt beschlossen; Speicher und Befehle für „Reinhören“ |
| 13 | Stufe C: Playlist beim Hochladen, Weiterspielen über Playlist |
| 14 | Barrierefreiheit: Wahlkarten, Kapitelliste, Umschalter |
| 15 | neue Pakete A3c, A3d; geänderte A3b, A4c, A7, A8, A8b, A11a, A11b, B3 bis B5 |
| 16 | Fragen 14 bis 22 mit Antwort, neue Fragen 23 bis 26 |
| 17 | Prototyp v4 |
| 18 | unverändert |
| – | Rev. 4a: Frage 23 – Reinhör-Daten für alle sichtbar (5.10, 5.10.1, 5.12, 10, 11.1, 12.3 bis 12.5, 15.2, 16, 17); Fragen 24 bis 26 beantwortet |

**Änderungen in Rev. 3** (zur Erinnerung):

| Abschnitt | Änderung |
|---|---|
| 1, 1.1 | Kurzfassung und Änderungstabelle angepasst |
| 2 | Stufe A enthält jetzt Serienseite mit Player |
| 3.1, 3.2 | Kopfzeile mit „+“ und „Technik“; neue Adresse `#suche` |
| 5.1 | Start: Suchfeld öffnet die Suchansicht, Reihe „Weiterhören“ |
| 5.2 | Bibliothek neu: Inhalt zuerst, eine Zeile Arten, Lupe, Reihen „Am Handy weiterhören“ und „Neu“, Liste im Audible-Stil, ein Knopf „Sortieren und Filter“; „Alle Folgen“ und die Filter-Stapel entfallen; Suchansicht |
| 5.3 | Serienseite wie ein Hörbuch: großes Cover, Gesamtdauer, „Reinhören/Hier weiterhören“, Karte „Gespielt von“ (Runde 16), Folgenliste mit Abspielknopf und Menü |
| 5.4, 7.2, 8 | Tobie für eine Folge: seit Runde 16 über „Einem Tobie geben …“ im Menü der Folge (4 Taps); Zuordnen beginnt beim Tobie (X20) |
| 5.10 | „Gehört“: Rangliste „Wer hat was gehört?“ je Box mit Aufteilung nach Folgen und wählbarem Zeitraum |
| 5.12 | Reinhören (Bedienung) neu |
| 6.1 | neue Fehlertexte für das Reinhören |
| 9, 10.2 | Fundorte, Rechte für Reinhören und Hörstelle |
| 11.1, 11.2 | neue Fähigkeit `reinhoeren`; V-6 (Audio, Dauer, Hörstelle); V-2 um `angehoert` ergänzt |
| 11.3, 11.4 | `dauer_s`, `spuren_s` in `serie.json`; Reinhören: Technik (Audio-Ansicht, signierter Pfad, Range, Pfad-Sicherheit, Formate, Dauer, Hörstelle, Prüfstand) |
| 12.2, 12.3, 12.4 | Zählregel „einmal gehört“, Speicherspalten, `gehoert/zusammenfassung` gruppiert nach Box × Serie × Folge |
| 14, 15 | Barrierefreiheit des Players; Pakete A3b, A4c, A4d, A8b; A7, A8, A14, A15b, A16, B3 bis B5 angepasst |
| 16, 17 | Fragen 14 bis 22 neu; Prototyp v3 |

## 1. Kurz gesagt

* Eine Seite „Tobi Box“ für **alle** HA-Benutzer. Reiter: **Start · Bibliothek · Tobies · Geräte** (immer vier, Runde 15; „Mehr“ entfällt). **Start** ist ein Schaufenster für Inhalte (5.1), **„Geräte“** zeigt die Boxen, „Neuer Tobie aufgelegt“, **Abends** (Gute Nacht, Leise-Zeiten) und in Stufe B **Gehört** (3.4). **Playlists** (Stufe C) leben in der Bibliothek (5.2, 13). **Technik** (früher „Für Tobias“) ist
  kein Reiter, sondern ein rundes Symbol oben rechts, nur für Administratoren. **Hinzufügen** ist ein „+“ im Kopf der Bibliothek (5.2).
* **Bibliothek wie eine Hörbuch-App (neu in Rev. 3, Vorbild Audible):** Cover zuerst, eine Zeile **Arten** (Hörspiele, Hörbücher, Musik, Geschichten), **Lupe** für die Suche über alles,
  **ein** Knopf „Sortieren und Filter“ (Blatt von unten), Reihen „Am Handy weiterhören“ und „Neu hinzugefügt“, Liste mit Cover, Untertitel, Fortschrittsbalken und Tobie-Symbol. Etwa 200 Hörbücher und 300 Lieder gehen ohne Blättern (Päckchen von 60).
* **Reinhören (neu in Rev. 3):** Auf der Serienseite spielt man Folgen **im Browser** an (Handy, Computer, HA-App; nicht auf der Box), mit Leiste unten, Vollansicht, ±30 Sekunden, Geschwindigkeit und **Weiterhören**: die Stelle wird je Folge und **je HA-Benutzer in Home Assistant** gemerkt (Abschnitte 5.12, 11.4). Weil das **nicht** die Stelle der Box ist, heißt der Knopf „**Hier weiterhören**“ und die Reihe „**Am Handy weiterhören**“ (G17).
* **Hochladen in Schritten (neu in Rev. 4):** Nach der Dateiwahl fragt die Seite zuerst **„Was lädst du hoch?“** mit vier **großen Kacheln** (Neu anlegen · Zu Vorhandenem · Einzeln · Sortier du; die Kachel „Playlist“ entfällt, Runde 12 X12), je mit Symbol, kurzem Titel und **höchstens einer Zeile** Erklärung (Runde 12, X5).
  Dann kommt eine **Vorschau in Sätzen** („3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.“) mit „Ändern“ und „Hochladen“, dann der Fortschritt wie bisher. Dieselbe Wahl gibt es für Dateien, die über den NAS-Eingang kommen („Anders einsortieren“). Abschnitte 5.6, 7.3.
* **Einzeltitel (neu in Rev. 4):** Ein einzelnes Lied oder eine einzelne Folge, die für sich steht, ist **eine Serie mit genau einer Folge und dem Kennzeichen `einzeln`**. Die Box ändert sich nicht. In der Bibliothek steht „Lied · einzeln · 1:06“, nie „1 Folge“ (Abschnitt 5.4, 11.3, Frage 24).
* **Hörkopien (Rev. 4, Rev. 5 mit harten Grenzen):** Formate, die nicht jeder Browser spielt (OGG, Opus, ALAC, auch FLAC und WAV), bekommen **einmal** eine kleine Kopie (AAC/M4A, 96 kbit/s), gespeichert auf dem NAS **neben** `medien/`, nicht auf den Boxen. **Neu Einsortiertes bekommt sie sofort, der Bestand erst beim ersten Reinhören** („Die Hörprobe wird vorbereitet“, Entscheidung Runde 10). Die Erzeugung hat **harte Grenzen** (Dauerdeckel, feste Zeitgrenze, `-t`/`-fs`, Schlangenlimit, Kontingent; sie gelten auch für `ffprobe`), sonst könnte ein Konto mit einer präparierten Datei die Schlange tagelang blockieren (11.4.7, G1). Die Box bekommt immer das Original.
* **Kapitel (neu in Rev. 4):** Ein Hörbuch zeigt **eine Zeitleiste über alles und eine Kapitelliste** (Kapitel eines M4B/MP3 oder Tracks eines Ordners). Im Player und auf der Serienseite: Tipp aufs Kapitel springt dorthin, das aktuelle ist markiert (11.4.8).
* **„Gehört“ mit einer Auswahl „Wer?“ (Stufe B, Rev. 5):** kein Umschalter Boxen \| Reinhören und kein Hinweistext mehr. Eine einzige Auswahl: **Alle · Box 1 · Box 2** (Anzeigenamen aus den Einstellungen der Integration) **und die HA-Benutzer, die reingehört haben** (Name aus Home Assistant). Boxen und Personen stehen gleichberechtigt nebeneinander; Rangliste, Diagramme und Aufteilung nach Folgen gelten für die Auswahl (5.10, 12.4, 12.5). **Alle HA-Benutzer sehen alles** (Frage 23); löschen darf jeder seine eigenen Reinhör-Daten, alles nur ein Administrator.
* **Ein Tobie für ein einzelnes Lied oder eine einzelne Folge:** „Einem Tobie geben …“ im Menü der Folge (Runde 16, X20; früher „Tobie für diese Folge“ und Knopf „Tobie“); bei einem Einzeltitel steht die Karte „Gespielt von“ auf seiner Seite.
* **Name beim Zuordnen gleich abfragen** (überspringbar). **Eigenes Cover per Foto vom Handy.**
* **Rechte (Runde 6):** Alltag = alle HA-Benutzer, jetzt auch **in den Papierkorb legen**. Leeren, Eingang entfernen, Zusammenführen bleiben bei Administratoren.
  Dazu Schutz gegen Fehlbedienung (Abschnitt 10); **neu in Rev. 5:** legt ein Nicht-Administrator einen Eintrag mit Tobies oder mehr als 3 Einträge in einer Stunde in den Papierkorb, bekommen Administratoren eine **Mitteilung**, und in „Technik“ gibt es **„Letzte Stunde zurückholen“** (kein Tageslimit, Runde 10).
* **Upload bis 2 GiB je Datei (Rev. 5, Runde 10):** Hörbücher gehen vom Handy (Abschnitt 5.6a: Folgen für Upload-Code, Vertrag W 8, Speicher und Zwischendateien).
* **Stufe A in drei Teilen (Rev. 5, Runde 10):** **A-1 Alltag** (Bibliothek, Tobies, Hochladen, Abends, Rechte), **A-2 Reinhören mit Weiterhören**, **A-3 Hörkopien und Kapitel**, je mit eigener Abnahme (Abschnitt 15).
* **Umbau ohne Bruch (Rev. 5):** Die bisherige Technik-Seite behält **Datei und Elementnamen** (`tobibox-panel.js`, `tobibox-panel`) und wird in „Technik“ **eingebettet** (Abschnitt 5.9); die neue Alltagsseite ist ein **neues** Element `tobibox-app`. Ihre 121 Tests laufen unverändert weiter.
  Die neue Seite läuft zuerst **parallel unter eigener Adresse** (`/tobibox-neu`, nur Administratoren); die alte bleibt Tobias’ Seite bis zur Abnahme, A17 tauscht die Adressen und kann sie zurücktauschen (Abschnitt 15).
* Alle 26 Befunde des ersten und alle 31 Befunde des zweiten Goldfischs sind beantwortet (Abschnitt 18).

### 1.1 Wichtigste Änderungen gegenüber Rev. 1

| Thema | Rev. 1 | Rev. 2 |
|---|---|---|
| Umfang | ca. 20 Hörspiele | 500+ Einträge: Arten, Suche, Filter, Sortieren, Blättern (in Rev. 3 als Hörbuch-App neu geordnet, 5.2) |
| Reiter | Start, Hörspiele, Tobies, Abends, Für Tobias | Start, **Bibliothek**, Tobies, Abends (B: **Gehört**); **Technik** als Knopf oben |
| Einzelne Folge/Lied als Ziel | nur in „Für Tobias“ | Menü der Folge und Suchtreffer, für alle |
| Name des Tobies | später über „Namen geben“ | wird in der Fertig-Karte gleich abgefragt, überspringbar |
| Cover | automatisch aus Tags, eigenes Foto später | automatisch (mit „schon versucht“-Marke) **und** eigenes Foto vom Handy |
| Papierkorb | nur Administrator | Alltag darf hineinlegen, nur Leeren bleibt Admin |
| Alte Technik-Seite | wird in Karten umgebaut | wird eingebettet, nicht umgebaut |
| Wochenplan-Grafik, Reihenfolge ändern | Alltag | Grafik entfällt in Stufe A, Reihenfolge nur Admin |
| Gute Nacht | Stepper, nur über „Neuer Tobie“ | Schnellwahl 15 bis 90 Minuten; Kachel „Gute Nacht“ auch für bereits belegte Tobies |

### 1.2 Wichtigste Änderungen in Rev. 3 gegenüber Rev. 2

| Thema | Rev. 2 | Rev. 3 |
|---|---|---|
| Bibliothek, oberer Teil | Warnbalken, Kopf, „Hinzufügen“, Suchfeld, 5 Art-Knöpfe, Umschalter, 4 Filter, Sortierfeld, Zähler: Inhalt erst ganz unten | **Cover sofort sichtbar** (erstes Cover bei 38 % der Höhe); eine Zeile Arten, Lupe, **ein** Knopf „Sortieren und Filter“ |
| Einzelne Folgen und Lieder finden | Umschalter „Alle Folgen“ | **Suche** (3 Gruppen) und Serienseite |
| Liste | Kacheln | Zeilen wie in Audible: Cover, Titel, „Art · Folgen · Dauer“, Fortschrittsbalken, Tobie-Symbol mit Anzahl; darüber Reihen „Weiterhören“ und „Neu hinzugefügt“ |
| „Hinzufügen“ | großer Knopf neben dem Titel | kleines „+“ in der Kopfzeile; auf Start der große Knopf |
| Serienseite | Kopfkarte, drei Knöpfe, Karte „Tobie anlernen“, Folgenliste mit „Tobie“ und „⋯“, Karte „Aufräumen“ | großes Cover, Gesamtdauer, **„Reinhören/Hier weiterhören“**, „Tobie zuordnen“, Folgenliste mit Abspielknopf, Fortschritt und „⋯“; Verwaltung im Menü „⋯“ |
| Reinhören | – | **neu:** Leiste unten, Vollansicht, ±30 s, 1× bis 1,5×, Weiterhören je Benutzer in HA (5.12, 11.4) |
| Vorschau-Hinweis im Prototyp | breite Leiste | Knopf „i“ in der Kopfzeile, klappt auf |
| „Gehört“ (Stufe B) | Diagramme, „Lieblings-Hörspiele“ | + **Rangliste je Box** mit Aufteilung nach Folgen und Zeitraum (5.10, 12) |

### 1.3 Wichtigste Änderungen in Rev. 4 gegenüber Rev. 3

| Thema | Rev. 3 | Rev. 4 |
|---|---|---|
| Hochladen, Blatt nach der Dateiwahl | „In welches soll es?“ mit „Abbrechen / In ein bestehendes wählen … / Automatisch (nach den Dateien)“: unverständlich | **„Was lädst du hoch?“** mit fünf Karten, dann Vorschau in Sätzen; 4 Taps statt 3 |
| Einzelnes Lied oder einzelne Folge | nur als Lied in einem Album oder in „Einzelfolgen“ | **Einzeltitel**: eigene Serie mit einer Folge, Kennzeichen `einzeln` |
| Reinhören bei OGG, Opus, ALAC | Hinweis „Das kann dieser Browser nicht abspielen“ | **Hörkopie**, einmal erzeugt, auf dem NAS neben `medien/` |
| Hörbuch | eine Zeitleiste | Zeitleiste **und Kapitelliste** |
| Reinhören und „Gehört“ | zählt nicht | Bereich **„Reinhören“** in „Gehört“, für alle HA-Benutzer sichtbar (Auswahl „Alle“ oder ein Benutzer; Stufe B) |
| Zählregel „einmal gehört“ | Frage 19 offen | beschlossen: Lücken bis 5 Minuten sind **eine** Wiedergabe |
| „Abspiel-Link“ (Frage 14) | Fachwort | in Alltagssprache erklärt (11.4.2, Frage 14) |

### 1.4 Wichtigste Änderungen in Rev. 5 gegenüber Rev. 4a

| Thema | Rev. 4a | Rev. 5 |
|---|---|---|
| Stufe A | ein Block, 27 Pakete, eine Abnahme | **drei Teile** A-1, A-2, A-3 mit je eigener Abnahme; A0 (Vertrag) und A0b (Testpanel, Messung) zuerst |
| Hörkopien | Bestand im Hintergrund auf Vorrat, Zeitgrenze aus dem Dateikopf | neu Einsortiertes sofort, **Bestand erst beim ersten Reinhören**; Dauerdeckel, feste Zeitgrenze, `-t`/`-fs`, Schlangenlimit |
| Abspielen im Browser | `<audio>` meldet 401, 503, 429; Seite reagiert auf den Status | Seite fragt vorher per WebSocket (`audio/bereit`: bereit, wird_vorbereitet, fehlt) und bekommt den signierten Pfad; **Link 24 Stunden** |
| Hochladen mehrerer Dateien | `gruppe` allein; 20 Sekunden Sammelzeit zerreißt lange Uploads | `gruppe_anzahl`: der Eingang wartet auf alle; höchstens 30 Minuten Ruhe, dann „teilweise“ |
| Upload-Grenze | 500 MiB | **2 GiB** |
| Papierkorb für alle | Rückfrage mit Namen | zusätzlich Mitteilung an Administratoren und „Letzte Stunde zurückholen“ |
| „Anders einsortieren“ | für die letzten 100 Einträge | nur „bitte ansehen“ oder jünger als 24 Stunden |
| „Gehört“ | Umschalter Boxen \| Reinhören, Hinweistext, Auswahl Benutzer | **eine Auswahl „Wer?“**, kein Hinweistext |
| Abgeleitete Werte | in `serie.json`, ändern den `stand` | im Store `tobibox.medieninfo`, `stand` bleibt ruhig |
| Alte Seite | „umbenennen in `tobibox-technik`“ | Datei und Elementname bleiben, neues Element `tobibox-app` |

### 1.5 Wichtigste Änderungen in Runde 12 (X1 bis X9)

* **Vier Reiter statt fünf (X1, X2):** Start · Bibliothek · Tobies · **Mehr**. Beschriftung 14 px, Symbol 26 px, Reiter 64 px hoch; bei 390 px je 97 px, nichts wird abgeschnitten. Stufe B braucht keinen fünften Reiter mehr: „Gehört“ liegt in „Mehr“. **Überholt in Runde 15 (X28):** der vierte Reiter heißt „Geräte“, „Mehr“ entfällt.
* **„Mehr“ für alle (X1):** große Zeilen, zuerst „Abends“. Die Partnerin kommt weiter mit **einem** Tap vom Start zu „Abends“ (großer Knopf auf dem Start), von jedem anderen Reiter mit **zwei** (Mehr, Abends). Abschnitte 3.4, 7.4, 8. **Überholt in Runde 15 (X28, X30):** „Mehr“ entfällt; „Abends“ liegt in „Geräte“ und ist von überall 2 Taps entfernt.
* **Leere Zustände (X3):** sechs eigene Bilder (Bibliothek leer, keine Tobies, keine Box, Suche ohne Treffer, Papierkorb leer, Gehört ohne Daten), je ein Satz und ein Knopf (6.2). Prototyp: Schalter „Leer zeigen“ im Menü „i“.
* **Formsprache (X4), Kacheln (X5), Wischen (X6), Meldungen (X7), Tippflächen (X8), Kontrast (X9):** Abschnitte 4, 5.6, 5.12, 6.3, 14.
* **Runde 12, X10 (Listenzeilen):** In Listen steht **kein** umrandeter Knopf mehr je Zeile (er sprang je nach Textlänge, wiederholte sich und wirkte schwer). **Die ganze Zeile ist die Tippfläche**, rechts steht ein ruhiger Pfeil „›“ an fester Stelle am Rand. Betrifft Tobies, Leise-Zeiten, Papierkorb, Auswahl „Wohin soll es?“ (Folgen) und die Suche (Abschnitte 4, 5.6 bis 5.9, 14).
* **Runde 12, X11 (nichts vorsorglich erklären):** Erlaubte Formate, 2 GB, Kopierschutz, „Bildschirm anlassen“ und der NAS-Eingang-Hinweis sind von „Hinzufügen“ **weg**; ebenso erklärende Sätze auf anderen Seiten. Die Seite meldet einen Fehler erst, wenn er eintritt (Abschnitte 5.6, 6, 6.1).

### 1.6 Wichtigste Änderungen in Runde 12 (X12) bis Runde 14 (X26)

* **Playlists (X12):** Bibliothek, Art-Zeile „Playlists“, Knopf „Neue Playlist“, „⋯“ → „Zur Playlist hinzufügen“, eigene Seite mit Cover-Mosaik, Umsortieren per Ziehen und per Menü; Datenmodell als Skizze in 13. Stufe C.
* **Warteschlange statt Countdown (X13):** „Nächster neuer Tobie auf Box 1 / Box 2 / irgendeiner Box spielt …“; HA ordnet beim Auflegen eines unbekannten Tobies sofort zu (5.13). Der Lernmodus bleibt als Admin-Weg in „Technik“.
* **Player (X14):** „Sperren“ gegen Kinderfinger, Entsperren mit 2 Sekunden langem Drücken; Geschwindigkeit im „⋯“ (5.12).
* **Technik (X15):** Unterseiten Boxen · Speicher und Netz · Liste und Sicherung · Meldungen · Einstellungen (5.9). **Suche (X16):** Vorschläge, Tobies zuerst (5.2).
* **Aussehen (X17, X18, X19, X25):** tonale Knöpfe, Pille für den aktiven Reiter, Reiterleiste als Glas mit Rückfall, „⋯“ als eigene 44-px-Fläche (4, 3.1).
* **Runde 14:** X20 zurückgestellt; X21 Box-Detailseite (5.1.2); X22 Zeitwähler; X23 endloses Nachladen; X24 Seitenleiste ab 900 px; X26 Wochenansicht der Leise-Zeiten (5.8).

## 2. Stufen im Überblick

| Stufe | Inhalt | Stand |
|---|---|---|
| **A-1 Alltag** | Bibliothek wie eine Hörbuch-App mit Suche und Serienseite (ohne Player), **Hochladen in Schritten** (mit `gruppe_anzahl`, 2 GiB), **Einzeltitel**, Tobie auf Lied/Folge, Name, Cover, Abends, Rechte und Schutz, Papierkorb mit Mitteilung, Technik-Einbettung, Anzeigenamen der Boxen | **wird gebaut** (Abschnitt 15), Abnahme 1 |
| **A-2 Reinhören** | Player (Leiste, Vollansicht, ±30 s, Tempo), **Weiterhören** je Benutzer in HA, Audio-Ansicht mit signiertem Pfad (24 Stunden) und Vorabfrage, Reihe „Am Handy weiterhören“, nur Originale in Formaten, die der Browser spielt | **wird gebaut** nach A-1, Abnahme 2 |
| **A-3 Hörkopien und Kapitel** | **Hörkopien** (neu Einsortiertes sofort, Bestand beim ersten Reinhören, mit harten Grenzen), **Kapitelliste** und Dauer-Nachholen im Hintergrund, „Anders einsortieren“ (nur wenn der Rückweg machbar ist) | **wird gebaut** nach A-2, Abnahme 3 |
| **B** | Abschnitt „Gehört“ in „Geräte“ (3.4) mit der Auswahl **Wer?** (Alle, Box 1, Box 2, Personen; Hörzeit pro Tag, Rangliste, Tageszeiten; Reinhör-Daten für alle sichtbar, 12.5), „Zuletzt gehört“, „Meist gehört“, Favoriten (Stern); in „Technik“ Akku-Verlauf, Ladezeiten, Laufzeit, Syncs, Fehler. Daten unbegrenzt | **geplant**, Vertragsentwurf in Abschnitt 12, Bau nach Freigabe |
| **C** | Eigene Playlists **in der Bibliothek, wie bei Spotify** (anlegen, aus Folgen und Liedern füllen, umsortieren, als Tobie-Ziel, Reinhören und Weiterspielen über eine Playlist) | **Idee**, Ausarbeitung in Abschnitt 13; im Prototyp als „Stufe C – Vorschau“ durchklickbar |

Im Prototyp sind B und C sichtbar, aber mit den Marken „Stufe B – Vorschau“ bzw. „Stufe C – Vorschau“. Die Vorschau-Leiste hat dafür den Schalter „Stufen zeigen“ (A, dazu B und C · A, dazu B · nur A); Playlists erscheinen nur bei „dazu B und C“.
In der echten Seite erscheint der Abschnitt „Gehört“ in „Geräte“ nur, wenn die Fähigkeit `gehoert` gemeldet wird (Abschnitt 12.4). **Reihenfolge ist bindend:** A-1 muss abgenommen sein, bevor A-2 beginnt, und A-2 vor A-3 (Abhängigkeiten in 15.1).

## 3. Navigation

### 3.1 Rahmen und Reiter (U15)

* Die Seite nutzt die Eigenschaft **`narrow`** des Panels (HA gibt sie vor, Grenze 870 px), keine eigene Media Query. Schmal: Reiter **unten**, sonst Reiter **oben**.
* Die untere Leiste ist **nicht `fixed`**, sondern `position: sticky; bottom: 0` am Ende des Seitenrahmens (der Rahmen füllt `height: 100%`, der Inhalt scrollt). So läuft sie nie unter die
  HA-Seitenleiste und springt nicht mit der Adressleiste. Bei offener Tastatur (Fokus in einem Textfeld, `visualViewport`) wird sie ausgeblendet. Unten gilt `env(safe-area-inset-bottom)`;
  ob die Companion-App die Werte liefert, prüft Tobias früh (Arbeitspaket A15).
* **Reiternamen (U22, Runde 15 X28):** **Start · Bibliothek · Tobies · Geräte** (Symbol Lautsprecher), immer vier (Stufe B ändert die Zahl nicht). 390 px: je 97 px, **Beschriftung 14 px** (Prototyp; Untergrenze 13 px), Symbol 26 px, Reiter **64 px** hoch, Beschriftung immer sichtbar, nie nur Symbole. „Abends“ und „Gehört“ liegen in „Geräte“ (3.4); „Mehr“ gibt es nicht mehr.
  **Roter Punkt mit Zahl am Reiter „Geräte“** (nicht mehr am Start), solange ein unbekannter Tobie wartet; Text für Screenreader „1 neuer Tobie“ (7.1).
* **Aktiver Reiter als Pille (Runde 13, X18):** Statt der Linie am Rand liegt hinter dem Symbol des aktiven Reiters ein abgerundeter Hintergrund (`--primary-soft`, 56 × 32 px am Handy); Symbol und Beschriftung des aktiven Reiters in `--primary-ink`.
* **Reiterleiste als Glas (Runde 13, X19):** Unten (Handy) steht die Leiste ohne harte Linie, mit weichem Schatten und leicht durchscheinendem Hintergrund aus Tokens (`color-mix(in srgb, var(--card) 94%, transparent)` mit `backdrop-filter: blur(12px) saturate(1.3)`). **Rückfall:** Ohne `backdrop-filter` oder `color-mix` (`@supports`) ist der Hintergrund deckend `var(--card)`. **Kontrast:** Die Beschriftung (`--text2` bzw. `--primary-ink`) muss ≥ 4,5:1 gegen den **ungünstigsten Inhalt** dahinter halten; darum nur 94 % Deckkraft (bei 90 % fiel das Theme mit hellem Primärton gegen schwarzen Inhalt auf 4,42:1; der Prüfstand rechnet gegen Schwarz, Weiß und Grau unter der Leiste).
* **Breite Bildschirme (Runde 14, X24):** Ab **900 px** ersetzt eine **Seitenleiste links** (264 px breit, volle Höhe, `position: sticky`) Kopf- und Reiterleiste: oben „Tobi Box“, darunter die vier Reiter als Liste (je 52 px, Symbol und Beschriftung nebeneinander, aktiver Reiter als Pille über die ganze Zeile), unten Info, „+“ und für Administratoren „Technik“. Der Inhalt nutzt die volle Höhe (höchstens 1100 px breit); die **Player-Leiste** liegt unten über der Inhaltsbreite, nicht unter der Seitenleiste. Die untere Leiste gibt es dort nicht. (Der Prototyp nimmt 900 px; die echte Seite folgt der Eigenschaft `narrow` des Panels, 3.1 oben.)
* **Kopf (Rev. 3, Runde 15 X27/X29):** eine schlanke Zeile. Auf dem **Start** steht dort die **Begrüßung nach Tageszeit** („Guten Morgen“ bis 11 Uhr, „Guten Tag“ bis 17, „Guten Abend“ bis 22, sonst „Gute Nacht“; kein Name) und rechts **kleine runde Symbole** (48 px): Suchen (`#suche`) und für Administratoren Technik (im Prototyp zusätzlich „i“ für die Vorschau-Einstellungen). Auf allen anderen Seiten steht „Tobi Box“ mit denselben Symbolen (ohne Suchen). **Hinzufügen** steht nicht mehr im Kopf, sondern als „+“ in der Bibliothek (5.2).
* **Technik:** rundes Symbol „Technik“ (Werkzeug, 48 px, Name „Technik“ für Screenreader) oben rechts im Kopf, **nur für Administratoren**. Der Name trägt keinen Personennamen (U22a).
  Zeigt den Knopf nicht, wer kein Administrator ist; ruft jemand `#technik` trotzdem auf, steht dort: „Dieser Bereich ist nur für Administratoren. Wenn du etwas Technisches brauchst, frag den Administrator.“ (Texte, die auf den Administrator verweisen, benutzen **einen** Texteintrag `verwalter` in `texte.js`; Vorgabe „den Administrator“. Ein Name aus Home Assistant darf dort erst zur Laufzeit stehen, nie im Repo; G24.)

### 3.2 Unterseiten, Adressen

Unterseiten: **Suche**, **Serienseite** (Hörspiel, Hörbuch, Album, Geschichten), **Playlist** (Stufe C), **Hinzufügen** (aus der Bibliothek), **Box-Detailseite** (aus „Geräte“), die **Tobie-Seiten** „Was soll … spielen?“, „Neuer Tobie“ und „Einem Tobie geben“ (Runde 16), **Tobie anlernen** (Lernmodus, nur Administratoren) und die **Technik-Unterseiten**. Oben links „‹ Bibliothek“, „‹ Geräte“ bzw. „‹ Technik“; Browser-Zurück geht denselben Weg. Der Player ist keine Unterseite, sondern eine Leiste und eine Vollansicht über jeder Seite (5.12).
Adressen (nach `#`, nur einfache Namen): `#start`, `#bibliothek`, `#suche`, `#serie-<id>`, `#hinzufuegen`, `#anlernen` (nur Lernmodus, Administratoren), `#tobies`, **neu in Runde 16:** `#tobie-<kennung>`, `#neu`, `#neu-warten`, `#neu-ziel`, `#neu-queue`, `#geben-<ziel>` (Ziel: `<serie>`, `<serie>~<nr>` für eine Folge, `@<playlist>`), **`#geraete`**, `#technik`, **neu:** `#box-<id>` (Box-Detailseite, 5.1.2), `#technik-boxen`, `#technik-box-<id>`, `#technik-speicher`, `#technik-liste`, `#technik-meldungen`, `#technik-einstellungen` (5.9) und `#playlist-<id>` (Stufe C, 13). `#abends`, `#gehoert` und `#mehr` (alte Lesezeichen) führen nach **`#geraete`** (Runde 15); dort stehen die Abschnitte.
Nicht `settings`, `sidebar` und Ähnliches. Der Menüknopf von HA (`ha-menu-button`) steht in der Kopfzeile, wenn `narrow` gesetzt ist.

### 3.3 Sprache (U22c, U21)

Es heißt **Tobie** (Mehrzahl Tobies), **Papierkorb**, **Folge**. Weil die Bibliothek mehr als Hörspiele enthält, gibt es kein einzelnes Oberwort mehr. Die Seite sagt, was es ist:

| Art (`art`) | Bereich | Einzelnes Stück | Kachel zeigt |
|---|---|---|---|
| `hoerspiel` | Hörspiele | Folge | „Hörspiel · 12 Folgen“ |
| `hoerbuch` | Hörbücher | Hörbuch (ein Buch = eine Folge mit Kapiteln) | „Hörbuch · 14 Kapitel“ |
| `musik` | Musik | Lied | „Musik · 20 Lieder“ |
| `geschichte` | Geschichten | Geschichte | „12 Geschichten“ |

Ein einzelnes Lied oder eine einzelne Folge, die für sich steht (nicht in einem Album oder Hörspiel), heißt **Einzeltitel**. In Listen steht „Lied · einzeln · 1:06“ bzw. „Geschichte · einzeln · 1:39“, nie „Serie mit 1 Folge“; die Wahl beim Hochladen heißt „Einzelne Folge oder einzelnes Lied“.
Allgemein heißt der Knopf zum Anlegen **„Hinzufügen“**, der Bereich **„Bibliothek“**. Nicht mehr sichtbar für Eltern: Serie, Track, Tags, Kennung, UID, Revision, Eingang (außer im Satz zum NAS und in „Technik“).
Die Überraschungs-Serie erscheint nur in „Technik“. **Box-Namen** setzt die Seite unverändert ein („Box 1 spielt …“, „Auf Box 2“). Die Optionen der Integration sagen: „Anzeigename der Box, zum Beispiel Box 1“. **Runde 11 (Tobias):** Der Anzeigename ist der **ganze Name der Box** (z. B. „Box 1“ oder „Annas Box“), damit Sätze wie „Neuer Tobie auf Annas Box“ und die Auswahl „Wer?“ Boxen und Personen klar trennen. Die echten Namen stehen nur in den Einstellungen in Home Assistant, nie im Repo (CLAUDE.md); in diesem Entwurf und im Prototyp heißen die Boxen „Box 1“ und „Box 2“, die Personen „Person A“ und „Person B“.

### 3.4 „Geräte“ (ersetzt „Mehr“, Runde 15, X28)

Der vierte Reiter heißt **„Geräte“** (Lautsprecher-Symbol). Er ersetzt „Mehr“ (Runde 12, X1); eine Liste „Mehr“ gibt es nicht mehr. **Wer:** **alle** HA-Benutzer (Abends ist Alltag der Partnerin). **Technik** bleibt das runde Symbol im Kopf, nur für Administratoren.

* **Aufbau, eine Seite, Überschrift „Geräte“, von oben nach unten:**
  1. Warnband bei Verbindungsproblemen (Abschnitt 6).
  2. **Status-Karten der Boxen** (5.1.1; am Computer nebeneinander). **Tippen öffnet die Box-Detailseite** (5.1.2, X21).
  3. **Karte „Neuer Tobie auf Box 1 – was soll er spielen?“** (Ablauf 7.1; Tipp öffnet Name und Zielwahl; Runde 16) – **nur hier** – und der **Punkt mit Zahl am Reiter „Geräte“**, damit sie nicht übersehen wird. Darunter, wenn Einträge in der Warteschlange stehen, die Karte „Wartet auf einen neuen Tobie“ (5.13).
  4. Abschnitt **„Abends“**: Karte „Gute Nacht“ und Karte „Leise-Zeiten“ als Wochenansicht (5.8).
  5. Abschnitt **„Gehört“** (Stufe B, nur mit Fähigkeit `gehoert`, 5.10): Auswahl „Wer?“, Rangliste je Box und Person, Hörzeit pro Tag, Tageszeiten.
* **Regel:** Alles, was ein **Gerät** betrifft (Box, Zeiten, was auf ihr gehört wurde, ein neuer Tobie, der gerade aufgelegt wurde), liegt hier; Inhalte liegen in Start und Bibliothek; Tobies verwalten heißt Reiter „Tobies“.
* **Taps:** „Abends“ ist von überall **2 Taps** entfernt (Reiter „Geräte“, dann steht der Abschnitt auf der Seite; Gute Nacht ändern: Reiter, Schnellwahl, Speichern = 3). „Gehört“ öffnen: 1 Tap auf den Reiter (Scrollen zählt nicht). Der große Startknopf „Abends“ entfällt (X30).
* **Stufe A allein:** Ohne „Gehört“; „Geräte“ hat dann Boxen, Neuer Tobie und Abends.
* **Prototyp:** Reiter „Geräte“ mit allen Abschnitten (Schalter „Stufen zeigen“ blendet „Gehört“ aus); die Adressen `#abends`, `#gehoert`, `#mehr` führen hierher.

## 4. Stil (U14)

* **Flächen** (Hintergrund, Karten, Trennlinien, Schatten, Eckenradius) kommen aus **HA-Variablen** mit Rückfall: `--primary-background-color`, `--card-background-color`, `--secondary-background-color`,
  `--divider-color`, `--ha-card-border-radius`, `--ha-card-box-shadow`; Hell/Dunkel folgt `hass.themes.darkMode`, ohne eigenen Schalter.
* **Text- und Statusfarben** (Hinweis, Warnung, Fehler, Erfolg, Text auf Cover, Akzenttext) sind **eigene Token**, abgeleitet aus `--primary-text-color` und `--card-background-color` mit `color-mix()`,
  weil die HA-Standardfarben als Text auf Weiß durchfallen (`--primary-color` #03a9f4: 2,8 zu 1).
* **Primärknopf:** Fläche `--primary-color`, Schrift `--text-primary-color`. Eine kleine Funktion rechnet **zur Laufzeit** den Kontrast und wählt bei unter 4,5 zu 1 Schwarz oder Weiß.
  Für Text in Primärfarbe (Links, aktiver Reiter) gibt es das Token `--primary-ink`: so weit abgedunkelt, dass 4,5 zu 1 gegen die hellste und die dunkelste Fläche gilt.
  Der Prototyp zeigt das mit dem Aussehen „Theme mit hellem Primärton“ (Gelb): Knopfschrift wird schwarz, Linkfarbe wird dunkelgelb-braun.
* HA-eigene Elemente sparsam: nur `ha-menu-button` und `ha-icon`. Alles andere ist eigenes HTML (nativ: `<dialog>`, `<details>`, `<select>`).
* **Formsprache (Runde 12, X4):** **Karten** (Status, Hinweise, Listen-Karten, „Mehr“-Zeilen) Radius **16 px**; **Blätter, Player-Vollansicht, große Kacheln** (Hochladen-Wahl, große Startknöpfe, leere Zustände) Radius **24 px**; Knöpfe und Chips bleiben Kapseln. Als Token `--r-card: 16px`, `--r-big: 24px` (kein Farbwert, gelten in Hell und Dunkel gleich).
* **Kontrast (Runde 12, X9):** Text 4,5:1. **Ränder von Bedienelementen, Symbole und Hinweiskarten mindestens 3:1** gegen die Fläche dahinter. Dafür gibt es das Token **`--line`** (Hell `#7c8187`, Dunkel `#7d848c`: 3,4 bis 5,4 zu 1 gegen Seite, Karte und Primärton-Hinweis) für Ränder von Knöpfen, Chips, Eingabefeldern, Kacheln und Zeilen; die dünnen Trennlinien in Listen (`--divider`) bleiben dezent, weil sie nur gliedern. **Warn-, Fehler- und Erfolgskarten** (Fläche kaum heller als die Seite) haben **2 px Rand in ihrer Textfarbe**, Hinweiskarten 1 px `--line`. Alles, was die Primärfarbe als **Fläche oder Rand** nutzt (Primärknopf, gewählter Chip, Fortschrittsbalken, Reiter-Strich, Symbolkreis), bekommt **`--primary-ink`** als Rand bzw. Strich: bei Blau sieht man keinen Unterschied, beim Theme mit hellem Primärton (Gelb) ist es der dunkelgelbe Rand, ohne den der Knopf auf Weiß nur 1,2 zu 1 hätte.
* **Listenmuster (Runde 12, X10):** Eine Liste mit **derselben Aktion in jeder Zeile** (Tobies, Leise-Zeiten, Papierkorb, Auswahllisten) zeigt **keinen Knopf je Zeile**. Die **ganze Zeile ist ein Knopf** (`<button>`, mindestens 56 px hoch, Name „<Name> bearbeiten“ o. Ä., sichtbarer Fokusring, bei Berührung leichte Hinterlegung `--primary-soft`); **rechts steht ein Pfeil „›“** in `--text2` (4,5:1 und mehr) **an fester Stelle** am rechten Rand, 24 px breit, nie verschoben. Der Text links bekommt die **freie Breite**, bricht um und schiebt nichts. Hat eine Zeile **zwei verschiedene Aktionen** (Folge: Abspielen und Menü), bleiben zwei Symbolknöpfe: Abspielen als Kreis, „⋯“ rechts an fester Stelle, beide mindestens 44 × 44 px.
* **Tonale Knöpfe (Runde 13, X17):** Sekundäre Knöpfe haben **keinen Rand**, einen getönten Hintergrund `--primary-soft` und Schrift `--primary-ink` (≥ 4,5:1 in allen Themes, im Prototyp in Hell, Dunkel und Theme mit hellem Primärton gemessen). Hauptknöpfe bleiben gefüllt (`--primary`), „Löschen“-Knöpfe tonal in `--danger-bg` mit `--danger`. Auf farbigem Grund (Hinweiskarten) bekommen tonale Knöpfe `--card` mit Rand `--line`, sonst verschwänden sie. Umschalter (Chips, Segmente) behalten ihren Rand.
* **„⋯“ in Zeilen (Runde 14, X25):** Das Menü-Symbol ist eine **eigene Fläche** (44 × 44 px, Radius 12 px, getönt `--primary-soft`, 8 px Abstand links). Die **Zeilenfläche endet davor**; Antippen öffnet **nur ein Menü**, nie eine Aktion direkt. Gilt für Folgenzeilen, Suchtreffer und Playlist-Einträge.
* Cover-Kacheln quadratisch, Radius 12 px; Platzhalter: sechs feste Farben (aus der ID), großer Anfangsbuchstabe; die orange Marke „bitte ansehen“ sitzt **unten links** im Cover und verdeckt den Buchstaben nie (U24b).
* Tap-Ziele mindestens 44 × 44 px, Hauptknöpfe 48 px, große Startknöpfe 64 px. Schrift Roboto, Fließtext 16 px, Nebentext 14 px, **Reiterbeschriftung 14 px**, sonst nirgends unter 12 px (nur Marken und Zähler).
* Playwright prüft mit **drei Themes** (HA-Standard hell, dunkel, ein Theme mit sehr hellem Primärton), siehe Arbeitspaket A14; geprüft werden Text (4,5:1), **Rand und Symbole (3:1, Runde 12)**, Tippziele (44 px) und waagerechtes Scrollen.

## 5. Seiten und Texte

Alle Texte wörtlich. Box-Namen sind Beispiele und kommen aus den Einstellungen der Integration (Abschnitt 11, V-3).

### 5.1 Start (Schaufenster für Inhalte, Runde 15, X27)

Der Start zeigt **nur Inhalte**: keine Boxen, keine Uploads, keine Admin-Blöcke (Boxen und „Neuer Tobie“: „Geräte“, 3.4; Hinzufügen: Bibliothek, 5.2). Von oben nach unten:

1. **Warnband** (nur bei Bedarf, Abschnitt 6): Verbindung weg.
2. **Kopf:** Begrüßung nach Tageszeit (3.1), rechts kleine runde Symbole: Suchen und, nur für Administratoren, Technik.
3. **Schnellzugriff** (Raster **2 × 3**, sechs flache Kacheln: Cover 56 px links, Titel in bis zu zwei Zeilen; Tippen öffnet die Serienseite). **Datenquelle je Stufe:** **Stufe A:** zuletzt einem Tobie **zugeordnete**, danach zuletzt **hinzugefügte** Einträge (`zuordnung/list`, `serien/list`). **Stufe B:** **meist gehört bzw. Favoriten** (`gehoert/zusammenfassung`, Favoriten, 12.2 bis 12.4). Fehlt die Fähigkeit `gehoert`, bleibt es bei der Stufe-A-Füllung.
4. **Reihen** (**seit Runde 16, X27a, nur hier und nicht mehr in der Bibliothek**; Cover mit Titel, seitlich scrollbar; **eine Reihe ohne Daten fehlt ganz**, es gibt keine leeren Reihen):

   | Reihe | Daten aus Stufe | Quelle |
   |---|---|---|
   | „Am Handy weiterhören“ | **A-2** (Reinhören) | Hörstellen je Benutzer (11.4.5): angefangen, nicht fertig, zuletzt angehört zuerst; Cover mit Balken, „noch 21 Min.“ und Abspielknopf (5.2 Punkt 4) |
   | „Zuletzt auf den Boxen gehört“ | **B** | `gehoert/zusammenfassung` (Ereignis `gespielt`, 12.2); Zeile „Box 1 · heute 17:40“ |
   | „Neu hinzugefügt“ | **A-1** | die acht neuesten Einträge (`serien/list`, `hinzugefuegt_am`) |
   | „Favoriten / Empfehlungen“ | **B** | Favoriten (Stern, 12.3); „Empfehlungen“ ist eine Idee ohne festgelegte Quelle (zum Beispiel „lange nicht gehört“); bis es sie gibt, stehen hier nur Favoriten |

5. Leer (X3, 6.2): „Noch nichts da. Tippe in der Bibliothek auf „+“.“ mit Knopf „Zur Bibliothek“.

**Gestrichen vom Start (Runde 15):** die Status-Karten der Boxen und die Karte „Neuer Tobie“ (jetzt „Geräte“), die großen Knöpfe „Hinzufügen“ und „Abends“ (jetzt „+“ in der Bibliothek bzw. Reiter „Geräte“), die Upload-Zusammenfassung (jetzt Band in der Bibliothek), das Suchfeld (jetzt die Lupe im Kopf), „Ganze Bibliothek ansehen“ (der Reiter Bibliothek genügt).

#### 5.1.1 Status-Karte der Box (ein Satz; liegt seit Runde 15 auf „Geräte“)

Links Cover des Gespielten (sonst Lautsprecher-Symbol), rechts ein **Satz**, darunter eine Zeile Nebentext. Punkt grün (online) oder grau. Quelle: `boxen/list` (`anzeige`, `online`,
`status.zustand`, `status.serie`, `status.folge`, `status.akku_prozent`, `status.lader`, `konfig_stand`). `status.folge` ist ein Dateiname; den Anzeigenamen holt die Seite **einmal je spielender Serie**
über `serie/get` (`folgen_info`), nicht über `serien/list` (U21b). Den Namen der Serie schlägt sie über `status.serie.id` in ihrer eigenen Liste nach.

| Lage | Satz | Nebentext |
|---|---|---|
| spielt | „Box 1 spielt „Lange Serie“ · Folge 4: Der Rabe.“ | „Akku 80 %, lädt.“ oder „Akku 80 %.“ |
| pausiert | „Box 1 ist pausiert bei „Lange Serie“.“ | wie oben |
| `leer`, `beendet`, `gehalten`, `unbekannt` | „Box 1 ist bereit. Es liegt kein Tobie auf.“ | wie oben |
| `herunterfahren` | „Box 1 geht gerade aus.“ | |
| Akku ≤ 20 % und kein Laden | (Satz wie oben) | „Akku fast leer (15 %). Bitte laden.“ (orange) |
| offline (`online=false`) | „Box 2 ist aus oder nicht im WLAN.“ | „Zuletzt gesehen: heute um 18:40. Akku war bei 35 %.“ |
| noch keine Meldung (`online=null`) | „Box 2 hat sich noch nicht gemeldet.“ | |
| `konfig_stand` ≠ `aktuell` **und** Box offline oder Abweichung länger als 5 Minuten (U23d) | | zusätzlich „Neue Zuordnungen kommen auf die Box, sobald sie wieder im WLAN ist.“ (kurz nach einer Änderung erscheint der Satz nicht) |


**Seit Runde 14 (X21) ist die Karte ein Link** (ganze Karte, Pfeil „›“ rechts; sie liegt seit Runde 15 auf „Geräte“, nicht mehr auf dem Start) auf die Box-Detailseite (5.1.2). Technische Einzelheiten stehen dort für Administratoren und in „Technik“.

#### 5.1.2 Box-Detailseite (Runde 14, X21)

`#box-<id>`, oben „‹ Geräte“, Überschrift = Name der Box. **Für alle Benutzer:** dieselbe Status-Karte wie in 5.1.1, darunter die Zeilen **Verbindung** (online · aus, zuletzt gesehen …), **Akku** (Prozent, „lädt“) und **Läuft gerade**. **Für Administratoren** folgt darunter die Überschrift „Technik“ mit den Karten **dieser** Box: „Box 1 im Detail“ (Zustand, Liste, Netz, freier Speicher, Version, Sync; Knöpfe „Box 1 jetzt abgleichen“ und „Lernmodus starten …“) und in Stufe B „Akku-Verlauf“. Das ist **dieselbe Darstellung** wie „Technik › Boxen › Box 1“ (`#technik-box-<id>`, 5.9); Nicht-Administratoren sehen nur den oberen Teil. Daten: `boxen/list` (Feld `ereignisse` bleibt Admin, Rechte unverändert). Der Prototyp zeigt beides (Rolle im Menü „i“ umschalten).

### 5.2 Bibliothek (neu in Rev. 3: wie eine Hörbuch-App)

Tobias (Runde 7): Der Reiter war „unglaublich unübersichtlich“. Oben stapelten sich Hinweisbalken, Kopf, „Hinzufügen“, Suchfeld, fünf Art-Knöpfe, ein Umschalter, vier Filter, die Sortierung und ein Zähler; der Inhalt begann erst ganz unten.
Vorbild ist jetzt **Audible**: Die Bibliothek zeigt **sofort Cover**, alles andere ist einen Tap entfernt. Aufbau von oben nach unten (Prototyp: Reiter „Bibliothek“, 390 px breit: das erste Cover endet bei 38 % der Bildschirmhöhe):

1. **Kopf** (3.1): „Tobi Box“ mit den runden Symbolen (Technik nur für Administratoren). Das frühere „+“ im Kopf steht jetzt in Zeile 2.
2. **Zeile „Bibliothek“ mit Lupe.** Die Lupe (44 px) öffnet die **Suchansicht** (`#suche`, unten). **Rechts daneben das „+“ (Hinzufügen, 48 px, gefüllt, `aria-label` „Hinzufügen“; Runde 15, X29)**; Hochladen bleibt Alltag für alle Benutzer.
2a. **Band für laufende Uploads** (Runde 15, X29): Läuft oder wartet etwas, steht **über** der Zeile „Bibliothek“ ein dezentes Band (tonal, 44 px, `role="status"`): „2 Einträge werden gerade hinzugefügt.“ / „1 neuer Eintrag bitte kurz ansehen.“ (orange) / „Alles hinzugefügt.“; Tippen öffnet `#hinzufuegen` (Einzelheiten, 5.6). Ohne Uploads fehlt es. Es erscheint **nur** in der Bibliothek, nicht auf dem Start.
3. **Arten** als eine Zeile schlichter Unterreiter: **Alle · Hörspiele · Hörbücher · Musik · Geschichten** (Text mit Strich unter dem gewählten; ohne Zahlen, nur diese eine Zeile; auf schmalen Geräten scrollt die Zeile ein Stück, nicht die Seite).
4. **Keine Reihen mehr (Runde 16, X27a):** „Am Handy weiterhören“ und „Neu hinzugefügt“ stehen **nur auf dem Start** (5.1). Die Bibliothek beginnt nach der Arten-Zeile gleich mit der Zählzeile und der Liste. (Rev. 3 hatte hier zwei Reihen mit Covern; sie doppelten den Start.)
5. **Liste im Audible-Stil:** Eine Zeile je Eintrag, mindestens 84 px hoch: **Cover links** (72 px), **Titel**, darunter **Untertitel „Hörspiel · 12 Folgen · 26 Min.“** (Zahlen aus `anzahl_folgen` und `dauer_s` der Kurzform; bei Hörbüchern „Hörbuch · 14 Kapitel · 9 Std. 40 Min.“ aus `kapitel_anzahl`, bei Musik „Musik · 20 Lieder · 1 Std. 12 Min.“), bei angehörten Einträgen ein **Fortschrittsbalken** mit „noch 18 Min.“ bzw. „Fertig gehört“,
   rechts ein **kleines Tobie-Symbol mit Anzahl**, wenn ein Tobie auf den Eintrag oder eine seiner Folgen zeigt, und die orange Marke „bitte ansehen“. Die ganze Zeile ist ein Link zur Serienseite. Blättern in Päckchen von 60, **endlos** (Runde 14, X23, siehe unten).
6. **Ein Knopf „Sortieren und Filter“** über der Liste, rechts neben der Zählzeile („60 Einträge“, `aria-live`), mit einem Zahlenpunkt, wenn etwas eingestellt ist. Er öffnet ein **Blatt von unten** (natives `<dialog>`): **Sortieren** (A bis Z, Zuletzt hinzugefügt, **Zuletzt angehört**) und **Nur zeigen** (**Ohne Tobie**, **Neu** in den letzten 14 Tagen, **Bitte ansehen**; mehrere gleichzeitig). Die Liste ändert sich dahinter sofort; „Zurücksetzen“ und „Fertig“.
   Stufe B ergänzt **Zuletzt gehört (Box)** und **Meist gehört** sowie **★ Favoriten**. „Zuletzt angehört“ meint das Reinhören am Handy oder Computer (5.12), „Zuletzt gehört“ die Box (5.10); die Namen bleiben getrennt.
   **Rev. 4:** Das Blatt hat eine dritte Gruppe **„Was zeigen“** (ein Tap, wählt eines): **Alles · Nur Hörspiele, Bücher, Alben · Nur Einzeltitel (einzelne Lieder und Folgen)**. Sie zählt wie die anderen Einstellungen am Zahlenpunkt des Knopfes mit. Backend: `filter` bekommt die Werte `sammlung` und `einzeln` (V-8).
   **Einzeltitel in der Liste (Rev. 4):** wie jede Zeile, aber der Untertitel heißt „**Lied · einzeln · 1:06**“ (bei Geschichten „Geschichte · einzeln · 1:39“, bei Hörbüchern „Hörbuch · einzeln · …“); nie „1 Folge“. Sie stehen unter ihrer Art (ein Lied unter „Musik“). 300 einzelne Lieder bleiben damit bedienbar: Arten-Zeile „Musik“ plus „Nur Einzeltitel“ oder „Nur Hörspiele, Bücher, Alben“ trennt sie von den Alben.

**Playlists in der Bibliothek (Stufe C, Runde 12, X12):** Die Arten-Zeile bekommt zwischen „Alle“ und „Hörspiele“ den Unterreiter **„Playlists“** (nur wenn die Fähigkeit `playlists` gemeldet wird; „Alle“ zeigt keine Playlists). Er zeigt oben die Zählzeile („3 Playlists“, Etikett im Prototyp), rechts den Knopf **„+ Neue Playlist“** und eine Liste im Muster der Bibliothek: Cover-Mosaik (72 px), Name, „Playlist · 5 Einträge · 6 Min.“, Tobie-Symbol mit Anzahl. Leer: Bild „leeres Regal“, „Noch keine Playlists.“, Knopf „Neue Playlist“. Die Suche findet Playlists in einer eigenen Gruppe. Die Seite einer Playlist, „Zur Playlist hinzufügen“ und alles Übrige: 13.1.

**Endloses Nachladen (Runde 14, X23):** Lange Listen (Bibliothek, Folgenliste einer Serie) laden beim Scrollen die nächsten 60 (Folgen: 20) nach (`IntersectionObserver` auf dem Knopf am Listenende, 200 px Vorlauf). Der Knopf **„Mehr laden (4 weitere)“** bleibt sichtbar als **Rückfall** für Tastatur, Screenreader und Browser ohne Beobachter; nach jedem Nachladen sagt der `aria-live`-Bereich „Weitere Einträge geladen.“ Der Fokus wird nicht gestohlen. Backend unverändert (`limit`/`offset`).

**Suche (Runde 13, X16):** Beim Tippen erscheinen oben **bis zu fünf Vorschläge** (Autovervollständigen aus Tobie-Namen, Namen von Einträgen und Playlists, Folgen- und Liedtiteln; Wortanfang oder Wortbeginn, Zeile 48 px, Treffer hervorgehoben, Tippen setzt den Begriff ein). **Die Gruppen stehen in neuer Reihenfolge: Tobies zuerst** (gefunden nach Name **oder** nach dem, was sie spielen; jede Zeile sagt „spielt „…““), danach Playlists (Stufe C), Hörspiele/Bücher/Alben, Folgen und Lieder. Die Zählzeile nennt Tobies zuerst. Das gilt statt der Reihenfolge im Absatz „Suchansicht“.

**Leere Zustände der Bibliothek (Runde 12, X3, 6.2):** Bibliothek ganz leer: Bild „leeres Regal“, „Noch nichts da. Tippe auf „Hinzufügen“.“, Knopf „Hinzufügen“. Filter ohne Treffer: „Nichts gefunden. Nimm einen Filter weg.“ mit Knopf „Filter zurücksetzen“.

**Gestrichen gegenüber Rev. 2:** der Umschalter **Kacheln | Alle Folgen**, die Art-Knöpfe mit Zahlen, die vier Filter-Knöpfe in der Seite, das Auswahlfeld zum Sortieren, das Suchfeld im Seitenkopf und der große „Hinzufügen“-Knopf neben dem Titel. Einzelne Folgen und Lieder findet man jetzt **über die Suche und über die Serienseite**.
Das Backend bleibt dasselbe (`folgen/list` bedient die Suche und die Zielwahl „Einzelne Folge oder Lied“, 5.4); nur die Seite zeigt den Umschalter nicht mehr.

**Suchansicht (`#suche`).** Zeile mit Zurück-Pfeil und Suchfeld „Hörspiel, Lied, Folge oder Tobie“ (der Fokus liegt gleich im Feld). Ab 2 Zeichen (Verzögerung 250 ms, Umlaute und Groß/Klein egal) erscheinen drei Gruppen mit der Zählzeile „Gefunden: 6 Sammlungen, 102 Folgen und Lieder, 0 Tobies“:
**„Hörspiele, Bücher, Alben“** (Listenzeilen wie oben, höchstens 8, Treffer hervorgehoben, **ohne Einzeltitel**), **„Folgen und Lieder“** (Zeile mit kleinem Cover, Titel, „Serie · Dauer“ bzw. bei einem Einzeltitel „Einzeltitel · Dauer“, **Abspielknopf** und Knopf „Tobie“, höchstens 10) und **„Tobies“** (nach Tobie-Name; ein Treffer öffnet die Seite „Was soll … spielen?“, 5.7). Mehr Treffer: „… und 7 weitere. Genauer suchen hilft.“
**Jede Zeile ist ein Link** (G25): bei einer Folge zur Serienseite, bei einem Einzeltitel zu seiner Seite (dort stehen Name, Cover, Art und Papierkorb); „Abspielen“ und „Mehr“ (⋯, enthält „Einem Tobie geben …“; Runde 12, X10: kein Knopf „Tobie“ in jeder Zeile; Runde 16, X20) bleiben eigene Knöpfe (beide mindestens 44 × 44 px, X8). Kein Treffer: leerer Zustand mit Bild, „Nichts gefunden zu „xyz“.“ und Knopf „Suche löschen“ (6.2) Leer: „Tippe mindestens 2 Buchstaben.“ Art und Filter der Bibliothek gelten **nicht** für die Suche (sie sucht über alles). Die Startseite hat weiter ihr Suchfeld; Absenden öffnet `#suche` mit dem Wort.

**Leistung (500+ Einträge).** (1) Das Backend blättert (`limit`/`offset`, V-2); die Seite lädt 60 und bei „Mehr zeigen“ die nächsten 60. Suchen, Filtern und Sortieren macht das Backend (Index im Speicher der Integration, Ziel unter 200 ms bei 600 Einträgen und 2 000 Folgen). „Zuletzt angehört“ kennt nur das Backend (die Hörstellen liegen dort, 11.4); die Liste zeigt in A-1 noch keine Dauer und keine Hörstellen, die Kapitelzahl erst in A-3 (Abschnitt 15).
(2) Listenzeilen tragen `content-visibility: auto`; eine eigene virtuelle Liste ist **nicht** nötig (bis 1 000 Zeilen im Dokument geprüft). (3) Cover laden erst, wenn die Zeile sichtbar wird (`IntersectionObserver`), in der kleinen Größe 192 px (ca. 15 KiB, V-1), als `blob:` zwischengespeichert nach `cover_stand`. Bei 60 Zeilen sind das etwa 1 MB statt 8 MB.
(4) Optional: Sprungleiste „A B C …“ bei A bis Z.

### 5.3 Serienseite (Hörspiel, Hörbuch, Album, Geschichten): wie ein Hörbuch oder Album

Aufbau (Prototyp: `#serie-<id>`); oben „‹ Bibliothek“ und rechts ein Drei-Punkte-Knopf für den Eintrag:

* **Kopf:** **großes Cover** (bis 190 px am Handy, 220 px am Computer neben dem Text), **Titel**, „**Hörspiel · 12 Folgen · 26 Min.**“ (Art, Anzahl, **Gesamtdauer**) und bei angehörten Einträgen „Schon 18 % gehört · noch 21 Min.“.
* **Großer Knopf „Reinhören“** (56 px, Hauptknopf). Nach dem ersten Anhören heißt er **„Hier weiterhören“** mit dem Zusatz „Folge 3: Die alte Mühle · ab 0:47“; ist alles gehört, „Noch einmal hören“; während der Wiedergabe „Pause“. Er startet den Player (5.12, Hörstelle des angemeldeten Benutzers). **Beim ersten Mal steht darunter ein Satz: „Das spielt hier am Handy oder Computer, nicht auf der Box.“** (G17: die Box führt ihre eigene Stelle; die Seite zeigt sie nirgends.)
* **Karte „Gespielt von“** (Runde 16, X20; ersetzt den Knopf „Tobie zuordnen“) unter dem Kopf: Spielen Tobies diesen Eintrag oder eine seiner Folgen, stehen ihre **Namen als Chips** da („Gespielt von:“, jeder Chip 44 px hoch, Tipp öffnet die Seite des Tobies, 5.7). Spielt keiner, steht dort „**Noch kein Tobie** · Einem Tobie geben …“ (Textknopf, öffnet `#geben-<serie>`, 5.4). **Hat der Eintrag schon Tobies, gibt es keinen Link**; weitere Tobies stellt man im Reiter „Tobies“ ein. Ein Zuordnen-Knopf steht in der Bibliothek nirgends mehr.
* Falls zu prüfen: gelbe Karte „**Bitte kurz ansehen.** <Grund, Abschnitt 7.3>“ mit **„Das ist richtig“** und **„Das stimmt nicht“** (U11; „Anderem zuordnen …“ oder abgesetzt „In den Papierkorb …“). Unverändert.
* Abschnitt „**Folgen**“ (bei Alben „Lieder“, bei Hörbüchern „Hörbuch“): Eine Zeile je Folge mit **Nummer**, **Titel**, **Dauer** („2:19“, bei Ordner-Folgen „· 14 Kapitel“), darunter **Chips** der Tobies, die genau diese Folge spielen (Runde 16), **Fortschritt** (Balken mit „noch 1:23“, oder „Fertig gehört“ mit Häkchen, oder bei der laufenden „läuft“/„pausiert“), einem runden **Abspielknopf** (48 px; spielt genau diese Folge, bei der laufenden „Pause“) und dem **Drei-Punkte-Menü**.
  Ab 20 Folgen ein Suchfeld „Hier suchen“ und „Mehr zeigen“.
* **Menü der Folge („⋯“):** „**Einem Tobie geben …**“ (5.4, öffnet `#geben-<serie>~<nr>`), (Stufe C) „**Zur Playlist hinzufügen**“ (13.1), „**Name ändern**“, „**In anderes verschieben …**“, abgesetzt „**Papierkorb …**“ mit Rückfrage. Rechte wie in Rev. 2 (Abschnitt 10: alle Benutzer, nur in den Papierkorb; nichts endgültig). Das frühere „Tobie“-Knöpfchen in der Zeile entfällt (ein Tap mehr, dafür ruhige Zeilen; im Suchtreffer bleibt es).
* **Menü des Eintrags („⋯“ oben rechts):** (Stufe C) „**Zur Playlist hinzufügen**“ (alle Folgen des Eintrags), „**Name ändern**“, „**Cover ändern**“ (5.5), „**Art ändern**“ (Blatt „Was ist das?“), nur Administratoren „**Reihenfolge ändern**“ (▲/▼ je Zeile, kein Ziehen) und „**Mit anderem zusammenführen …**“, abgesetzt „**In den Papierkorb …**“ (Rückfrage nennt Tobies, die dann nichts mehr spielen, mit Namen; „Der Administrator bekommt eine Mitteilung und kann es zurückholen.“). Die frühere Karte „Aufräumen“ unten entfällt.

* **Hörbuch mit Kapiteln (Rev. 4, Runde 8 Nr. 20):** Hat ein Hörbuch **eine** Folge mit Kapiteln (Datei mit eingebetteten Kapiteln oder Ordner mit Tracks), steht statt der Folgenliste der Abschnitt **„Kapitel“**: Satz „12 Kapitel. Tippe auf ein Kapitel, dann geht es dort los. Im Player kannst du über das ganze Buch springen.“, darunter eine Zeile je Kapitel mit **Nummer** (bei schon gehörten ein Häkchen), **Titel**, „**ab 2:49 · 0:19**“ (Start und Länge), Abspielknopf (44 px); das **Kapitel der gemerkten Stelle** ist markiert (`aria-current="true"`, getönte Fläche, „hier weiter“ bzw. „läuft“). Tipp auf eine Zeile springt dorthin und spielt (Quelle der Kapitel: 11.4.8). Die **Zeitleiste über das ganze Buch** liegt im Player (5.12); Kopfbereich („Schon 30 % gehört · noch 3 Min.“) und „Weiterhören“ bleiben wie bei anderen Einträgen.
* **Einzeltitel (Rev. 4):** Die Seite hat Kopf (Cover, Titel, „Lied · einzeln · 1:01“), „Reinhören/Hier weiterhören“ und der Karte „Gespielt von“, aber **keine Folgenliste**; stattdessen ein Satz „Das ist ein einzelnes Lied. Es steht für sich und gehört zu keinem Album. Du kannst einen Tobie dafür anlernen.“ Das Menü „⋯“ hat Name, Cover, Art und Papierkorb wie jeder Eintrag.
* **Hörprobe wird vorbereitet (Rev. 4, Rev. 5):** Braucht eine Folge eine Hörkopie (11.4.7), fragt die Seite **vor dem Abspielen** (`audio/bereit`, 11.4.1). Ist die Kopie schon da (neu Einsortiertes sofort), spielt es gleich. Beim **ersten Reinhören im Bestand** (Entscheidung Runde 10) antwortet das Backend `wird_vorbereitet`, stößt die Erzeugung an und die Seite zeigt oben eine Karte „**Die Hörprobe wird vorbereitet.** Dieses Format (OGG) spielt nicht jeder Browser. Home Assistant legt dafür einmal eine kleine Kopie an. Bei einem Lied dauert das etwa eine Minute, bei einem langen Hörbuch bis zu einer halben Stunde. Du kannst die Seite offen lassen, sie sagt Bescheid. Auf der Box spielt es schon.“ mit einem Balken. Die Seite fragt alle 15 Sekunden nach; ist die Kopie fertig, kommt die Meldung „Die Hörprobe ist fertig. Tippe auf Reinhören.“ (es startet **kein** Ton von selbst, Safari verlangt einen Tap). „Reinhören“ zeigt in der Zwischenzeit nur eine kurze Meldung und startet nichts. Ist die Warteschlange voll, steht dort stattdessen „Gerade sind viele Hörproben in Arbeit. Versuche es in einer Viertelstunde noch einmal.“

### 5.4 Zuordnen beginnt beim Tobie (Runde 16, X20 „Tobie zuerst“)

**Grundsatz** (Tobias: „super“; Vorschau `docs/egm/ha-ui/x20_tobie_zuerst.html`, bleibt als Beleg): Zuordnen beginnt **immer beim Tobie**. Wer einem Tobie etwas zu spielen geben will, geht in den Reiter „Tobies“ (5.7), tippt auf den Tobie (oder auf „+ Neuer Tobie“) und wählt dort das Ziel. **Die Bibliothek hat keinen Zuordnen-Knopf mehr**; sie zeigt nur, welche Tobies etwas spielen, und führt zu ihnen (5.3). Es entfallen: das Blatt „Tobie anlernen“ / „Tobie für dieses Lied“ mit „Auf Box 1 / Auf Box 2“ und „Tobie wählen …“, der Knopf „Tobie zuordnen“, der Knopf „Tobie“ im Suchtreffer und die Zielwahl als Blatt.

**Die Zielwahl „Was soll … spielen?“** ist **eine Seite** (kein Blatt) und dieselbe für „Tobie bearbeiten“ (`#tobie-<kennung>`), „Neuer Tobie“ (Weg 1 und 2, 7.1) und die Warteschlange (5.13). Von oben nach unten:

1. bei einem bestehenden Tobie die Karte **„Spielt jetzt“** (Cover, Titel, Art: „Ganzes Hörspiel“, „Lange Serie · Folge“, „Einzeltitel“, „Aktion“, „Playlist“);
2. der Umschalter **„Ganze Serie | Folge oder Lied | Playlist“** (Playlist nur in Stufe C, mit Etikett „C“; 44 px hoch). „Serie“ steht für Hörspiel, Hörbuch, Album und Geschichten;
3. Suchfeld „In der Bibliothek suchen“ und die Arten-Zeile (Alle · Hörspiele · Hörbücher · Musik · Geschichten);
4. das Ergebnis: **Ganze Serie** = Kacheln (mit Suchbegriff Zeilen), ohne Einzeltitel; **Folge oder Lied** = Liste der Serien zum **Aufklappen** (Pfeil dreht sich, `aria-expanded`), Einzeltitel als eigene Zeile, mit Suchbegriff eine flache Trefferliste (Folge, darunter die Serie); **Playlist** = Liste der Playlists. Lange Listen laden in Päckchen zu 30 („Mehr zeigen“);
5. darunter, **abgesetzt als eigene Zeile, die „Gute-Nacht-Karte“** („Timer, dann wird es still“; Ergänzung c; U16c).

**Ein Tap auf ein Ergebnis ordnet zu.** Es gibt keinen „Fertig“-Knopf und keine Rückfrage.

**Nach dem Zuordnen** (Ergänzung d): Die Meldung „**Fertig: Löwe spielt jetzt „Kommissar Kralle“.**“ hat den Knopf **„Rückgängig“** und bleibt **etwa 6 Sekunden** (ausnahmsweise länger als die 4,5 s der anderen Erfolgsmeldungen, 6.3). „Rückgängig“ stellt das vorherige Ziel wieder her (`zuordnung/set` mit dem alten Ziel; `erwartet_ziel` schützt vor Überschreiben). Die Seite kehrt zum Regal zurück.

**Einem Tobie geben … (aus der Bibliothek, Ergänzung a):** Hat eine Serie, ein Einzeltitel oder eine Playlist noch keinen Tobie, steht in der Karte „Gespielt von“ **„Noch kein Tobie · Einem Tobie geben …“** (5.3). Der Link öffnet die Seite **„Welcher Tobie soll das spielen?“** (`#geben-<ziel>`; oben „‹ <Name>“, darunter das Ziel): ein Regal mit **„+ Neuer Tobie“** zuerst und allen Tobies (jede Kachel nennt, was er jetzt spielt). Tap auf einen Tobie ordnet zu, die Seite kehrt zur Serie zurück, Meldung mit „Rückgängig“. „+ Neuer Tobie“ startet Weg 1 oder 2 (7.1) **mit festem Ziel**: die Zielwahl entfällt, oben steht „Er soll spielen: …“. Für eine **einzelne Folge oder ein Lied** (Folgenzeile, Suchtreffer, Playlist-Eintrag) heißt der Eintrag im Menü „⋯“ **„Einem Tobie geben …“**.

* **Kachel im Regal** (Ergänzung b): Tobie-Symbol, Name (oder „Tobie ohne Namen“), darunter Cover (32 px) und **Titel des Ziels**; bei einer **einzelnen Folge** steht darunter in Grau auch der **Serienname** („Der Mond ist aufgegangen“ / „Kinderlieder zum Mitsingen“). Ein Einzeltitel hat keinen Zusatz (er gehört zu keiner Serie).
* **Einzeltitel als Ziel (Rev. 4):** Gespeichert wird `ziel.typ = "folge"` mit der Serie des Einzeltitels (Empfehlung in 11.3 und Frage 24). Er erscheint in der Zielwahl **nur** unter „Folge oder Lied“, nicht unter „Ganze Serie“.
* **Warteschlange:** Weg 2 „Später auflegen“ benutzt dieselbe Zielwahl (5.13).

### 5.5 Cover (U5, U8, Runde 6)

Zwei Quellen, eine Anzeige: **eigenes Foto** hat Vorrang vor dem **automatischen Cover** (aus den Tags), das vor dem **Platzhalter** (Farbe und Anfangsbuchstabe) kommt.

**Cover ändern (Alltag, Eintrag → „Cover ändern“).** Blatt „Cover für „Lange Serie““: Auswahlfeld „Foto wählen“ (`<input type="file" accept="image/*">`; am Handy bietet das System Kamera und Galerie).
Danach **Zuschneiden im Browser**: quadratische Vorschau (280 px), verschieben mit Finger oder Maus **und** mit vier Pfeilknöpfen (nicht nur Ziehen), Regler „Ausschnitt größer oder kleiner“. Der Browser zeichnet das Quadrat auf
1 024 × 1 024 px (Ausrichtung nach den EXIF-Angaben des Fotos), kodiert JPEG (Qualität 0,85, bei mehr als 1,5 MiB mit weniger Qualität) und sendet **nur das Quadrat**. „Speichern“ lädt hoch, „Abbrechen“ verwirft.
Abgesetzt, wenn ein eigenes Foto da ist: Textknopf „Zurück zum automatischen Cover“.
**Grenzen:** Foto vom Handy bis 20 MB (die Seite verkleinert vor dem Hochladen, Meldung „Das Foto ist zu groß (mehr als 20 MB). Nimm ein kleineres.“; kein Bild: „Das ist kein Bild. Bitte ein Foto wählen.“);
hochgeladen wird höchstens **3 MiB**. **Reihenfolge im Backend (G7):** (1) der Rumpf wird **in Blöcken gelesen und gezählt** (3 MiB gelten auch ohne `Content-Length`; HA selbst lässt bis 16 MiB zu), (2) Typ aus den Kopfbytes, (3) **Maße und Pixelzahl aus dem Kopf lesen, bevor ein Pixel dekodiert wird** (höchstens 2 048 px je Seite, quadratisch bis auf 2 %; ein 3-MiB-JPEG mit 30 000 × 30 000 px wird abgelehnt), (4) erst dann dekodieren, auf 512 px und 192 px herunterrechnen, Originaldatei nie speichern. Dieselbe **eine** Funktion `cover_pruefen_und_skalieren` gilt für das **aus den Tags gezogene** Bild (ein Hörbuch mit präpariertem `APIC` darf nicht schwerer wiegen als ein Upload). Grenze: **höchstens 20 Cover je Stunde und Benutzer** (`zu_viele_aenderungen`). Pillow: `"requirements": ["Pillow"]` im `manifest.json` (nicht darauf verlassen, dass `image_upload` es mitbringt).
Vertrag: V-1.

**Automatisches Cover (U5).** Beim Einsortieren liest die Integration das eingebettete Bild (ID3 `APIC`, MP4 `covr`, FLAC `PICTURE`) der ersten Folge, die eines hat; **Vorrang** hat ein mitgeliefertes `cover.jpg`/`folder.jpg`/`cover.png` im Ordner (U8c); die Integration **kopiert** es beim Einsortieren als `cover.jpg` in den Serien-Ordner (durch dieselbe Prüffunktion), die mitgelieferte Datei im Eingang folgt danach der **bisherigen Regel** (Reste gehen in den Papierkorb, Vertrag W 11.10; G11).
Je Eintrag eine **Marke „schon gesucht“** (`cover_suche`: Ergebnis `tags`, `datei` oder `keine`, mit Zeit) in `serie.json`. Nachholen für bestehende Einträge **nur** (a) einmal im Hintergrund nach dem Start der Integration, (b) für Einträge ohne Marke,
(c) mit Zeitgrenze 20 s je Datei und Abbruch bei `medien_nicht_erreichbar`. Neue Folgen in einem Eintrag mit Marke `keine` lösen genau eine neue Suche aus. **Kein Dauer-Scan:** `medien/pruefen` startet keine Cover-Suche mehr beim Öffnen der Seite;
die Seite ruft `medien/pruefen` höchstens alle 10 Minuten und nur, wenn sie sichtbar ist. Fehlt `ffmpeg`: Fähigkeit `cover` wird nicht gemeldet, die Seite zeigt Platzhalter, keine Fehlermeldung.
Administratoren haben in „Technik → Bibliothek aufräumen“ den Knopf „Cover neu suchen“ (löscht `cover.jpg` und Marke, nie ein eigenes Foto).

**Auf den Boxen:** `cover*.jpg` wird **nicht synchronisiert** (U8, Empfehlung übernommen; Abschnitt 11.3). Eine Box ohne Display braucht kein Cover, und es spart SD-Platz und Schreibvorgänge. Ein späteres Display bräuchte eine neue Entscheidung.

### 5.6 Hinzufügen

Siehe Ablauf 7.3. Erreichbar über das „+“ in der Bibliothek und das Band (Runde 15, X29), nicht mehr vom Start. Aufbau der Seite: „‹ Bibliothek“, Überschrift „Hinzufügen“; große Knöpfe „**Dateien wählen**“ (Handy und Computer) und „**Ordner vom Computer wählen**“ (U12a: **nur** bei `matchMedia('(pointer: fine)')`, am Handy nicht);
am Computer zusätzlich eine Fläche „Dateien oder Ordner hierher ziehen“. **Sonst nichts** (Runde 12, X11): keine Formatzeile, keine Größe, kein Hinweis auf Kopierschutz, kein „Lass den Bildschirm an“, keine Hinweiskarte zum NAS-Eingang. Der Benutzer macht einfach; **erst wenn etwas nicht geht, zeigt die Seite genau diesen Fehler** am Ort der Handlung (Eintrag unter „Zuletzt hinzugefügt“, Texte in 6.1): „Dieses Dateiformat spielt die Box nicht. Erlaubt sind MP3, M4A, M4B, AAC, FLAC, OGG, Opus und WAV.“ (`format_nicht_erlaubt`), „Die Datei ist zu groß (mehr als 2 GB). Kopiere sie am Computer in den Eingang-Ordner auf dem NAS. …“ (`datei_zu_gross`, Zahl aus `hello.grenzen.upload_max_bytes`), „Diese Datei ist kopiergeschützt (zum Beispiel von Audible). Die Box kann sie nicht abspielen. Nimm eine Datei ohne Kopierschutz.“, „Die Verbindung ist abgebrochen. Die Seite wurde geschlossen oder der Bildschirm gesperrt. …“ (Upload abgebrochen). Der Prototyp zeigt jeden dieser Fälle über die Demo-Auswahl der Dateien (neu: „1 Datei im falschen Format“). Darunter „**Zuletzt hinzugefügt**“ (Einträge der **letzten 24 Stunden**, U13).

**Nach der Dateiwahl öffnet sich das Blatt „Was lädst du hoch?“** (Rev. 4; **Runde 12, X5: Kacheln statt Karten**). Anlass der Rev. 4: Tobias verstand das Blatt „In welches soll es?“ mit „Abbrechen / In ein bestehendes wählen … / Automatisch (nach den Dateien)“ nicht; Anlass der Runde 12: die fünf Karten mit Satz **und** Beispiel waren zu textlastig. Es ist ein Blatt von unten (natives `<dialog>`, Radius 24 px) mit der Zeile „3 Dateien gewählt (01 Der Hafen.mp3 …). Was ist das?“ und **vier großen Kacheln** in **zwei Spalten** (2 × 2; die frühere fünfte Kachel „Playlist“ entfällt, Runde 12 X12, 13.7). Jede Kachel hat ein **Symbol** im Kreis, einen **kurzen Titel** und **höchstens eine Zeile** Erklärung; Beispiele entfallen. Kachel mindestens **132 px** hoch, Radius 24 px, Rand `--line`, kein Fachwort. **Die Zeile darunter passt in einer Zeile in die Kachel (bei 390 px sind das etwa 22 Zeichen); der Prototyp misst das.**

| Kachel | Symbol | Titel | Zeile darunter | Bisherige Karte (Backend-Weg, 7.3) |
|---|---|---|---|---|
| 1 | Bücherregal | **Neu anlegen** | „Hörspiel, Buch, Album“ | a) Neues Hörspiel, Hörbuch oder Album |
| 2 | Regal mit Plus | **Zu Vorhandenem** | „Neue Folgen dazu“ | b) Folgen zu einem vorhandenen hinzufügen |
| 3 | Note | **Einzeln** | „Lied oder Folge für sich“ | c) Einzelne Folge oder einzelnes Lied |
| 4 | Zauberstab | **Sortier du** | „Ich lese die Angaben“ | e) Weiß nicht – sortier du |

Die **ausführlichen Sätze** der Rev. 4 („Alle Dateien gehören zusammen und werden etwas Neues.“ usw.) stehen als **nur für Screenreader sichtbarer Text** in jeder Kachel und in der Vorschau (7.3); sehende Nutzer lesen sie dort. Der Satz zu „Sortier du“ steht in der Vorschau („Ich lese die Angaben in den Dateien …“).
Das Blatt hat nur „**Abbrechen**“, **oben rechts** im Blatt (auf dem Handy gibt es kein Esc, und unten lag der Knopf zur Hälfte unter der Kante; Tippen daneben schließt ebenso, G26a). **Ein Tap auf eine Kachel** führt zur **Vorschau** (7.3): Dort steht ein Satz, was geschehen wird, darunter genau die Eingaben, die dieser Weg braucht (Name und „**Welche Art?**“ in einer Zeile unter dem Namen, vorausgewählt, G26b; die Wahl eines vorhandenen Eintrags mit Suche und Covern, Titel der Auswahl „**Wohin soll es?**“, G26c; ein Name je Datei, bei mehr als drei Dateien der Satz „Die übrigen 2 Dateien heißen wie in ihren Angaben.“, G26d), bei mehreren Dateien der Satz „Die Dateien bleiben zusammen. Einsortiert wird, wenn alle 3 da sind.“, und die Knöpfe „Abbrechen“, „**Ändern**“ (zurück zu den Kacheln) und „**Hochladen**“.
**Keine Kachel „Playlist“ und keine Kachel „Neue Playlist“ (Runde 12, X12; Runde 16, X12a: Tobias entschieden):** Bei Spotify lädt man nicht in Playlists hoch, man füllt sie aus der Bibliothek. Darum entfällt die Kachel; nach dem Hochladen bietet die Fertig-Karte unter „Zuletzt hinzugefügt“ in Stufe C **„Zur Playlist hinzufügen“** (für neue Einzeltitel, Alben und Hörbücher), im selben Blatt wie überall (13.1). Aus dem Eintrag heraus („Dateien in diesen Eintrag“, `serie_id`) wird das Blatt übersprungen: der Weg ist dann „zu einem vorhandenen hinzufügen“.

### 5.6a Upload-Grenze 2 GiB: Folgen (Rev. 5, Runde 10, G15)

Entscheidung Tobias: die Grenze je Datei steigt von 500 MiB auf **2 GiB** (Hörbücher gehen vom Handy; 12 Stunden M4B bei 128 kbit/s sind 690 MiB). Geprüft am Code (`http.py`, `hub.py`, `const.py`, `config_flow.py`) und am Vertrag W 5 und 8:

| Stelle | Folge | Änderung |
|---|---|---|
| `const.py` `UPLOAD_MAX_MIB_VORGABE` (500) | gilt nur für **neue** Einrichtungen; ein bestehender Konfigurationseintrag hat 500 gespeichert | Vorgabe auf 2 048; **bestehender Eintrag wird beim Update angehoben** (Optionen setzen oder eine kleine Migration) und „Technik“ zeigt die wirksame Grenze; `config_flow.py` erlaubt schon bis 100 000, Text in `strings.json` und `translations/de.json` (heute „Vorgabe 500“) anpassen |
| `http.py` `_empfange` | streamt in Blöcken (`UPLOAD_BLOCK_BYTES` 1 MiB), nie ganz im Speicher: **kein Speicherproblem**. 413 vor dem ersten Byte, wenn `Content-Length` größer ist | keine; die Zwischendatei (`_upload/*.part`) wächst bis 2 GiB |
| Freier Platz | Prüfung gegen `UPLOAD_RESERVE_BYTES` (100 MiB) nur mit **dem Stand beim Start**; zwei parallele 2-GiB-Uploads (`upload_parallel` = 2) bestehen die Prüfung beide, auch wenn der Platz nur für einen reicht | Reserve auf **2 GiB** und laufende Zwischendateien (angekündigte Bytes) vom freien Platz abziehen; Test: zwei Uploads, Platz nur für einen → der zweite bekommt `kein_speicher` |
| Zwischendatei und Abschluss | `_in_den_eingang` verschiebt `.part` in den Eingang (gleiche Freigabe, Umbenennen, keine Kopie); `fsync` einer 2-GiB-Datei dauert auf dem NAS Sekunden bis Minuten | Test mit 2-GiB-Dummy (sparse) im Eingang-Ordner; Fortschrittsschritt „Wird geprüft …“ ist schon im Vertrag |
| `ffprobe` und Probedekodierung | lesen Kopf und eine Sekunde, nicht die ganze Datei; 30 s fest, `RLIMIT_AS` 1 GiB | keine; bei M4A mit `moov` am Ende liest ffprobe das Ende (auf dem NAS-Pfad messen, A0b) |
| Vertrag W Abschnitt 8 | Zeile „Größe einer Audiodatei“ nennt 500 MiB; „Erst nach der Abnahme anheben“; „Nabu Casa: unbekannt, Abnahme mit 20, 150, 500 MiB“ | Zeile auf 2 GiB; Abnahme mit **20 MiB, 150 MiB, 500 MiB und 2 GiB**, jeweils mit gemessener Dauer (A0b, A-1 Abnahme); Ausweg bleibt der Eingang-Ordner am Computer |
| Mengengrenze 10.3 | „4 GiB je Stunde und Benutzer“ ließe nur **zwei** große Hörbücher je Stunde zu | auf **16 GiB je Stunde und Benutzer** (`zu_viele_aenderungen`) |
| Zeit und Verbindung | 2 GiB bei 10 Mbit/s Handy-Upload sind rund 30 Minuten; Handy-Browser frieren die Seite bei gesperrtem Bildschirm ein | der Hinweis „Lass den Bildschirm an“ bleibt; Unterbrochenes meldet 7.3 Punkt 8; Tobias misst früh (A0b) |
| Fehlertext | `datei_zu_gross` nennt die Zahl und den Rat | „Die Datei ist zu groß (mehr als 2 GB). Kopiere sie am Computer in den Eingang-Ordner auf dem NAS. Frag den Administrator nach dem Ordner.“ (6.1; der Prototyp zeigt den Fall bei „2 Dateien, dazu eine über 2 GB“) |

### 5.7 Tobies (Regal, Runde 16, X20)

* Überschrift „Tobies“, **kein Erklärsatz** (Runde 12, X11). Wartet etwas auf einen neuen Tobie, stehen darüber Karten „**Nächster neuer Tobie auf Box 1 spielt „Lange Serie“**“ / „Wartet auf einen unbekannten Tobie“ mit dem Knopf **„Abbrechen“** (5.13).
* **Das Regal:** ein Raster aus Kacheln (mindestens 150 px breit und 148 px hoch). **Zuerst die gestrichelte Kachel „+ Neuer Tobie“** (7.1), danach die Tobies, **zuletzt zugeordnet zuerst** (U4; braucht ein Zeitfeld, V-5). Die Kachel (Aufbau 5.4, Ergänzung b) ist **ganz ein Link**; Name für Screenreader: „Löwe, spielt Kommissar Kralle“. Aktionskarte: Mond-Symbol (ein Bild, kein Name), „Gute Nacht“. Die frühere Zeilenliste mit Pfeil „›“ (X10) gilt nur noch für die Tobies in der Suche.
* **Suche im Regal:** ab **9 Tobies** steht über dem Regal das Suchfeld „Tobie suchen (Name oder was er spielt)“; bis dahin ist das Regal überschaubar. Ohne Treffer: „Kein Tobie gefunden zu „…“.“ mit „Suche löschen“.
* **Tipp auf einen Tobie** öffnet die Seite „**Was soll Löwe spielen?**“ (`#tobie-<kennung>`, oben „‹ Tobies“): die Zielwahl (5.4), darunter abgesetzt „**Namen ändern**“ (Textfeld, Knopf „Name speichern“; Meldung „Name gespeichert.“) und „**Diesen Tobie vergessen …**“ (Rückfrage; Backend: `zuordnung/remove` mit `erwartet_ziel`).
* **Auflegen zum Finden** (U4, wenn die Box die Kennung beim Auflegen meldet, V-5): Die Kachel des aufgelegten Tobies wird hervorgehoben. Fehlt das Datenfeld, bleiben Name, Sortierung und Suche.
* **Ohne Tobies** zeigt das Regal nur die Kachel „+ Neuer Tobie“. Der leere Zustand (X3, 6.2: Bild „Tobie wartet auf die Box“, „Noch keine Tobies. Lege einen Tobie auf eine Box, dann erscheint er unter „Geräte“.“, Knopf „Zu den Geräten“) gilt, wenn nichts eingerichtet ist (keine Box).
* Tobies mit dem Ziel „Playlist“ zeigen den Namen der Playlist; die Zielwahl hat in Stufe C die dritte Auswahl „Playlist“ (13.1). In der **Suche** stehen Tobies als Zeilen („spielt „…“ aus „…““); der Treffer öffnet `#tobie-<kennung>`.

### 5.8 Abends (Abschnitt von „Geräte“, 3.4; Leise-Zeiten als Wochenansicht, Runde 14 X26)

Überschrift „Abends“ auf der Seite „Geräte“, unter den Boxen (kein eigener Bildschirm mehr; die alte Adresse `#abends` führt nach `#geraete`).

Zwei Karten. **Gute Nacht**: „Lege den Gute-Nacht-Tobie auf. Dann läuft ein Timer. Danach wird es leise und die Box hört auf.“ „Die Box spielt noch“ mit **Schnellwahl 15 · 30 · 45 · 60 · 90 Minuten** (Knöpfe, U16a) und einem Auswahlfeld „Anderer Wert …“ (5 bis 240 Minuten).
Knopf „Speichern“ (grau mit „Gespeichert“, solange nichts geändert ist). Das **Ausblenden** („Dann wird sie leiser über …“) ist ein selten geänderter technischer Wert und liegt in „Technik → Weitere Einstellungen“ (U16b).
Darunter „Ein Gute-Nacht-Tobie ist angelernt („Nacht-Karte“).“ bzw. „Noch kein Gute-Nacht-Tobie.“ und „So legst du einen an“: unter „Tobies“ „+ Neuer Tobie“ wählen und unten die „Gute-Nacht-Karte“ **oder** einen bereits belegten Tobie unter „Tobies“ antippen und unten die „Gute-Nacht-Karte“ wählen (U16c, Runde 16).

**Leise-Zeiten (Runde 14, X26: Wochenansicht mit Zeitleisten):** Oben **ein Satz zum Jetzt**: „Jetzt: leiser bis 7:00“, „Jetzt: still bis 7:30“, sonst „Jetzt: normale Lautstärke, die nächste Leise-Zeit beginnt um 19:30“. Darunter **je Wochentag (Mo bis So) eine Leiste von 0 bis 24 Uhr** (Stundenmarken 0 · 6 · 12 · 18 · 24, Leiste 28 px hoch mit Rand `--line` und senkrechten Linien alle 6 Stunden) mit **Abschnitten**: **„Still“ = ausgefüllt** (`--primary-ink`), **„Leiser“ = schräg gestreift** (`--primary-ink` auf `--primary-soft`, mit Rand). Muster **und** Legende („Still“ / „Leiser“) unterscheiden, nicht nur die Farbe; der Kontrast der Abschnitte gegen die Leiste ist ≥ 3:1 in allen Themes. **Zeiten über Mitternacht laufen sichtbar in den nächsten Tag** (So 19:30–6:30 füllt So ab 19:30 und Mo bis 6:30). Eine senkrechte **Marke „jetzt“** (2 px, `--text`, Beschriftung oben) läuft über alle Leisten; der heutige Wochentag ist hervorgehoben. **Tippen auf einen Abschnitt** öffnet das Bearbeiten-Blatt (die Tippfläche ist mindestens 44 px breit und hoch, auch bei einer Stunde Dauer); der Knopf **„+ Leise-Zeit“** legt eine neue an. Am Handy (390 px) ist jede Leiste etwa 290 px breit (12 px je Stunde), Marken alle 6 Stunden. Jeder Abschnitt hat einen Namen für Screenreader („Mo, 19:30 bis 6:30, still, bearbeiten“; die Fortsetzung: „Mo, von So bis 6:30 …“). Leer: „Keine Leise-Zeiten. Die Box spielt immer in normaler Lautstärke.“ Die frühere Zeilenliste entfällt (sie sagte dasselbe, X11). **Überholt:** „Wochenplan-Grafik später“ (Frage 6, U23a). **Gute Nacht** bleibt eine **Dauer** (Schnellwahl, „Anderer Wert“), kein Zeitfeld; der Zeitwähler (X22) gilt nur für die Leise-Zeiten (**X22a, Runde 16: von Tobias bestätigt**).
Blatt „Leise-Zeit ändern“ (per Tipp auf einen Abschnitt der Wochenansicht): Tag-Knöpfe 44 px mit `aria-pressed`, Schnellwahl „Jeden Tag“, „So–Do“, „Fr, Sa“, „Von“/„Bis“ als **Zeitfeld `<input type="time" step="300">`** (System-Zeitwähler, 5-Minuten-Schritte; Runde 14, X22; ersetzt die Auswahllisten),
„Was soll die Box tun?“ **Still | Leiser** (bei Leiser Regler „Höchste Lautstärke: 25 %“), Löschen abgesetzt mit Rückfrage. Prüfregeln: mindestens ein Tag, „Von“ ≠ „Bis“, höchstens 32 Zeiten.
Meldung: „Gespeichert. Die Boxen bekommen es gleich.“ Die **Zeitzone** zeigt die Seite nicht; das Backend nimmt für Nicht-Administratoren den gespeicherten Wert (V-4, U17).

### 5.9 Technik (nur Administratoren, U6, U7)

* **Unterseiten statt Aufklappkarten (Runde 13, X15):** „Technik“ ist eine Liste großer Zeilen (Muster X10) mit fünf Unterseiten, je mit „‹ Technik“: **Boxen** (je Box eine Zeile → `#technik-box-<id>`: Detail, „jetzt abgleichen“, „Lernmodus starten …“, Stufe B „Akku-Verlauf“; dieselbe Darstellung wie die Box-Detailseite für Administratoren, 5.1.2), **Speicher und Netz** (Eingang im Detail, Papierkorb, Bibliothek aufräumen mit Hörkopien), **Liste und Sicherung** (Stände, Export, neu ausrollen), **Meldungen** (Protokoll mit Codes), **Einstellungen** (Zeitzone, Lesezeichen-Tage, Ausblenden bei Gute Nacht). Kein Warnkasten „Nur für Administratoren“ (X11); wer es ohne Rechte aufruft, sieht den Satz aus 3.1. Der **Lernmodus mit Countdown** bleibt hier der Admin-Weg (5.13).
* **Einbettung statt Umbau (U6, Rev. 5 nach G12):** Die bestehende Komponente behält **Datei und Elementnamen** (`tobibox-panel.js`, `customElements.get('tobibox-panel')`, `PANEL_DATEI`, `PANEL_ELEMENT` in `__init__.py`); `panel.test.mjs` importiert die Datei, prüft den Elementnamen und liest die Datei nach Text, ein Umbenennen in `tobibox-technik` hätte die 121 Tests gebrochen. Sie bekommt nur ein **Attribut `eingebettet`** (Vorgabe aus), das ihre eigene Kopfzeile und Reiterleiste ausblendet.
  Die neue Alltagsseite ist ein **neues** Element **`tobibox-app`** in **`tobibox-app.js`**, das die alte Komponente mit `eingebettet` in „Technik“ einbettet. HA registriert das neue Element; nur `test_init.py` ändert sich (das tut A17 ohnehin). Die alte Seite zeigt weiter genau ihre heutigen Reiter-Inhalte (Eingang, Papierkorb, Liste/Revision/Export, Boxen, Einstellungen, Meldungen). Die 121 Tests (`panel.test.mjs`, `panel_quiet.test.mjs`) bleiben **unverändert** und grün;
  das belegt „nichts geht verloren“. Die neue Seite hat eigene Dateien mit eigenen Tests. Die Unterseiten (X15) sind Ansichten der neuen Seite, die je einen Bereich der eingebetteten Komponente zeigen (Attribut `bereich`, Vorgabe: alle); die 121 Tests ändern sich nicht (Prüfung in A13).
* **Rückweg (G19):** Bis zur Abnahme läuft die neue Seite **parallel** unter `/tobibox-neu` (`require_admin=True`); `/tobibox` bleibt die alte Seite. A17 tauscht die Adressen und kann sie zurücktauschen. Notschalter in den Optionen der Integration: Boolean „Alltagsseite für alle Benutzer“ (Vorgabe an; **keine** Benutzerliste, U3 bleibt abgelehnt).
* **Papierkorb in der Liste (Runde 12, X10, X11):** jede Zeile ist **ganz antippbar** (stellt wieder her, Pfeil „›“ rechts, Name „<Eintrag> wiederherstellen“, Zeile „… · Tippen zum Wiederherstellen“); der Erklärsatz zur Mitteilung an Administratoren steht nicht mehr in der Karte.
* **Neu in „Technik“ (Stufe A):** Karte „Bibliothek aufräumen“ (Medien neu einlesen, Cover neu suchen, Neues leeres Hörspiel, Überraschungs-Serie, Zusammenführen), Karte „Liste, Sicherung, Export“ um **„Frühere Stände ansehen“** ergänzt (die letzten 10 Stände der Liste, U2),
  „Weitere Einstellungen“ um das Ausblenden bei Gute Nacht ergänzt. Das **Papierkorb-Leeren** und „Eingang entfernen“ stehen nur hier.
  **Rev. 4, Rev. 5:** Die Karte „Bibliothek aufräumen“ zeigt den Stand der **Hörkopien** („41 fertig, 3 warten, 0 mit Fehler, 1 zu lang · 2,1 GB auf dem NAS“), den **Zähler der Schlange** („3 von höchstens 20 Dateien · 1,4 von höchstens 50 GB“, G1d) und den Knopf „Hörkopien neu erzeugen“ (`hoerkopie/neu_erzeugen`, nur Administratoren).
  **Papierkorb (Rev. 5, G8):** In der Karte „Papierkorb“ steht je Eintrag **wer** ihn wann gelöscht hat („gelöscht am 08.11., 11:00 von Person B“; die Upload-Ereignisse tragen `nutzer_id` schon), und der Knopf **„Letzte Stunde zurückholen“** (`papierkorb/restore_letzte_stunde`, Admin) holt alles zurück, was in der letzten Stunde hineinkam. Dazu ein Satz: „Legt jemand ohne Admin-Rechte einen Eintrag mit Tobies oder mehr als 3 Einträge in einer Stunde in den Papierkorb, bekommen Administratoren eine Mitteilung in Home Assistant.“ (persistente Mitteilung, Vorlage fürs Handy in der Doku.) **Kein Tageslimit** (Entscheidung Runde 10).
* **Stufe B:** Karte „Akku-Verlauf“ je Box mit Liniendiagramm (Prozent über 3 Tage, Ladezeiten als Bänder), Laufzeit je Ladung, Ladezeiten, Syncs, Fehler als Liste, Knöpfe „Hördaten als Tabelle sichern“ (CSV), „Alle Hördaten der Boxen löschen …“ und **„Alle Reinhör-Daten löschen …“** (beide mit Rückfrage; nur Administratoren, Runde 10). Abschnitt 12.
* Die Warnleisten zur Liste (`leer_neu`, `export_neuer`, Box mit neuerem Stand) erscheinen für Administratoren oben auf allen Seiten wie heute; Nicht-Administratoren sehen nur den Hinweis aus Abschnitt 6.

### 5.10 Gehört (Stufe B, Vorschau im Prototyp)

Abschnitt „Gehört“ auf der Seite „Geräte“ (3.4; Runde 15, X28; früher Unterseite von „Mehr“) für alle, **nur wenn die Fähigkeit `gehoert` gemeldet wird**; Überschrift „Gehört“ unter „Abends“. Ohne Daten: leerer Zustand „Noch nichts gehört. Sobald eine Box spielt oder jemand reinhört, steht es hier.“ mit Bild „Kopfhörer“ und Knopf „Zur Bibliothek“ (6.2). Oben ein Hinweis „Stufe B – Vorschau“ (nur im Prototyp). **Rev. 5 (Runde 10): kein Umschalter „Boxen \| Reinhören“ und kein Hinweistext „Alle in Home Assistant sehen das.“** Aufbau:

* **Auswahl „Wer?“** (eine einzige, 5.10.1): Knopfgruppe mit sichtbarer Beschriftung **Alle · Box 1 · Box 2 · Person A · Person B**. Die Boxen heißen so, wie sie in den Einstellungen der Integration benannt sind (`anzeige`); die Personen sind die **HA-Benutzer, die reingehört haben** (Name aus Home Assistant). Boxen und Personen stehen gleichberechtigt nebeneinander; „Alle“ ist die Summe aller Quellen. Rangliste, Hörzeit pro Tag, Tageszeiten und die Aufteilung nach Folgen gelten für die Auswahl.
* **Zeitraum:** **Woche · Monat · Jahr · Alles** (Woche = letzte 7 Tage, Monat = 30, Jahr = 365, immer bis jetzt gerechnet; Abschnitt 12.4).
* **Rangliste „Wer hat was gehört?“** (neu in Rev. 3, Wunsch von Tobias): für die gewählte Quelle eine Liste der Hörspiele (auch Alben und Bücher) nach **Anzahl Mal gehört**, mit den Spalten **Mal** (Wiedergaben), **Hörzeit** („9:48 Std.“) und **Fertig** („17/20“: so viele Folgen wurden mindestens einmal ganz gehört). Die ersten 10, Zeilen sind Knöpfe.
  **Ein Tap auf ein Hörspiel** öffnet **„Aufteilung nach Folgen“** mit **denselben Spalten je Folge** (Mal, Hörzeit, **Fertig = wie oft die Folge ganz gehört wurde**, „2×“; nicht gehörte Folgen grau mit „0“ und „–“), darunter die Summe; „‹ Rangliste“ geht zurück.
  Darunter eine aufklappbare Erklärung „**Was wird gezählt?**“ (Definition in 12.2; sie nennt Boxen und Handy/Computer gemeinsam).
* **Hörzeit pro Tag:** Säulendiagramm (SVG) für die Auswahl: **eine** Säule je Tag (bei „Alle“ die Summe; die Aufteilung auf Box 1, Box 2, Person A und Person B steht in der Tabelle darunter und im Satz), Achse „Minuten“ (0 bis 90, bei „Alle“ bis 180), Zahl über jeder Säule (bei 7 Tagen), Tage mit Wochentag und Datum. Bei „Woche“ 7 Tage, sonst die Tage der Beispieldaten (in der echten Seite: Monat in Tagen, Jahr in Wochen, Alles in Monaten).
  Darunter „Zahlen als Tabelle“. Satz darüber: „In den letzten 7 Tagen: 9 Std. 53 Min. (Box 1 5 Std. 58 Min., Box 2 3 Std. 55 Min., …).“
* **Tageszeiten:** 24 Säulen (Stunde 0 bis 23), Achse Minuten; Satz „am meisten um 19 Uhr“.
* **Zuletzt gehört**, **Favoriten (Runde 15, X27):** Die beiden Kachel-Reihen stehen **auf dem Start** (5.1: „Zuletzt auf den Boxen gehört“, „Favoriten / Empfehlungen“), nicht mehr hier. Der **Stern** (Favorit) steht in jedem Eintrag und in jeder Folgenzeile; gilt für alle in der Familie.
* **Löschen (Runde 10):** Ganz unten ein ruhiger Textknopf „**Meine Reinhör-Daten löschen …**“ (für jeden, Rückfrage, löscht nur die eigenen). **Alle** Reinhör-Daten und alle Hördaten der Boxen löschen nur Administratoren, in „Technik“ (5.9). Die Hörstelle (Weiterhören) bleibt davon unberührt (Frage 16). Ob der Knopf für die eigenen Daten wirklich in „Gehört“ sitzt: Frage 27.
* Farben der Diagramme sind Token (`--chart1`, `--chart2`, `--grid`), in Hell und Dunkel geprüft (3 zu 1 gegen die Karte). Jedes Diagramm hat `role="img"` mit Beschreibung und eine Tabelle; die Rangliste ist selbst eine Tabelle (Spaltenköpfe, Zeilen mit vollständigem `aria-label`).
* Die Kennung des Tobies kommt nirgends vor.

#### 5.10.1 Die Auswahl „Wer?“ (Rev. 5)

* **Inhalt:** „Alle“ (Vorgabe), je Box ein Knopf (Name aus `boxen/list` `anzeige`, Reihenfolge wie dort) und je HA-Benutzer, **der reingehört hat**, ein Knopf (Name aus Home Assistant, nie aus dem Repo; die Liste liefert `gehoert/zusammenfassung` als `wer_auswahl`, 12.4). Hat noch niemand reingehört, stehen nur „Alle“ und die Boxen da.
* **Bedeutung:** `alle` = alle Quellen zusammen (Boxen **und** Reinhören), `box:<id>` = diese Box, `benutzer:<id>` = dieser HA-Benutzer am Handy oder Computer. Es gibt **keine Mehrfachwahl**; ein Vergleich nebeneinander geht über die Aufteilung nach Quellen in der Tabelle (`nach=["wer"]`). Frage 28 fragt, ob „Alle“ Boxen und Reinhören addieren soll.
* **Rechte:** Alle HA-Benutzer sehen alles (Frage 23); die Hörstelle bleibt privat (Frage 16).
* **Barrierefreiheit:** Knopfgruppe mit `aria-pressed` und sichtbarer Beschriftung „Wer?“ (`aria-labelledby`), jeder Knopf mindestens 44 px; bei vielen Benutzern bricht die Gruppe um (kein waagerechtes Scrollen).

Zählregel und Herkunft der Daten: 12.5.

### 5.11 Playlists (Stufe C, in der Bibliothek, Runde 12 X12)

Playlists leben in der **Bibliothek** (Arten-Zeile „Playlists“, 5.2) und haben eine eigene Seite; es gibt sie nicht mehr unter „Mehr“ oder als Karte bei den Tobies. Bedienung, Datenmodell und Auswirkungen: **Abschnitt 13**. Im Prototyp sind sie mit dem Etikett „Stufe C – Vorschau“ durchklickbar.

### 5.12 Reinhören: Bedienung (neu in Rev. 3)

**Wozu:** Man soll am Handy oder Computer **hineinhören**, um zu erkennen, was etwas ist (Runde 7), ohne eine Box zu bemühen. **Nur im Browser** (Handy, Computer, HA-App); **nicht auf der Box**. Es zählt **nicht** als Wiedergabe einer Box, aber (Stufe B) in „Gehört“ unter dem Namen des HA-Benutzers (Auswahl „Wer?“, 5.10.1, 12.5), für alle HA-Benutzer sichtbar.
**Wer darf:** **alle HA-Benutzer** (Entscheidung Runde 7, wie Runde 6).

* **Schmale Leiste unten** (Mini-Player), sobald etwas gespielt wurde: Cover, Folgentitel, Name des Eintrags, runder Play/Pause-Knopf (48 px), dünner Fortschrittsstrich oben. Sie sitzt **über** der Reiterleiste (sticky, nie unter der HA-Seitenleiste) und verschwindet bei offener Tastatur. Tippen auf die Leiste öffnet die Vollansicht, auf den Knopf schaltet Play/Pause. **Wischen (Runde 12, X6):** In der Leiste öffnet **Wischen nach oben** (mindestens 40 px, deutlich mehr senkrecht als waagerecht) die Vollansicht; in der Vollansicht schließt **Wischen nach unten** (mindestens 70 px, von irgendwo außer vom Zeitregler) sie wieder. Die Vollansicht zeigt dafür einen kleinen **Griff** oben. Umsetzung mit **Pointer-Events** (Maus, Touch, Stift gleich) und Schwelle; `touch-action: pan-x` auf der Leiste und im Inhalt der Vollansicht, damit der Browser das senkrechte Wischen nicht selbst als Scrollen nimmt (bei niedrigem Fenster unter 560 px Höhe entfällt es, dort darf man scrollen). Ein Wisch löst **keinen** Tipp aus (Tipp-Sperre 250 ms danach). **Der Knopf bleibt**: Antippen der Leiste, Knopf „Player schließen“ und Esc gehen weiter (Barrierefreiheit: Wischen ist nur eine zweite Möglichkeit, nie die einzige). Ein kürzeres Wischen unter der Schwelle und Wischen nach unten in der Leiste tun nichts.
  Nach dem Neuladen der Seite steht die Leiste wieder da (pausiert, bei der gemerkten Stelle, **ohne Ton**); Ton startet **nur nach einem Tap**.
* **Vollansicht** (natives `<dialog>`; am Handy ganze Fläche, am Computer ein Blatt): „Läuft gerade“, **großes Cover**, Titel, „Eintrag · 2 von 20“, **Zeitleiste** (Schieberegler 44 px hoch mit `aria-valuetext` „1:41 von 2:47“, Zeit links, Restzeit rechts), **Vorige Folge · 30 s zurück · Play/Pause (72 px) · 30 s vor · Nächste Folge**, **Geschwindigkeit** (1× · 1,25× · 1,5×, gilt für alle Folgen, wird gemerkt) steht **im „⋯“ des Players** (oben rechts in der Vollansicht, Blatt „Wiedergabe“; Runde 13, X14), nicht mehr in der Hauptzeile. Kein Schlaftimer (nicht gewünscht). „Vorige Folge“ springt bei mehr als 5 Sekunden zuerst an den Anfang der Folge.
* **Sperren gegen Kinderfinger (Runde 13, X14):** Der Knopf „**Sperren**“ unter den Bedienelementen sperrt **alle** Bedienelemente (Zeitleiste, Folgenwechsel, ±30 s, Play/Pause, „⋯“, Kapitel, Schließen: `disabled`, ausgegraut). Cover und Titel bleiben, die Zeit läuft weiter, Esc und Wischen schließen die Vollansicht nicht, der Titel der Ansicht heißt „Gesperrt“. **Entsperren nur durch langes Drücken (2 Sekunden)** auf den großen Schloss-Knopf „Gedrückt halten“ (ein Füllbalken zeigt den Fortschritt; Maus und Touch; mit Tastatur Leertaste oder Eingabe 2 Sekunden halten); ein kurzer Tipp sagt „Zum Entsperren zwei Sekunden gedrückt halten.“, Loslassen vor 2 Sekunden bricht ab. Kontextmenü und Textauswahl auf dem Knopf sind aus. Die Sperre gilt nur im Browser, wird nicht gemerkt und ändert nichts an der Box.
* **Spielt weiter** über die Folgen des Eintrags: am Ende einer Folge startet die nächste; nach der letzten ist Schluss (Runde 8 Nr. 22: bei Alben so; über eine **Playlist** weiterspielen kommt mit Stufe C, Abschnitt 13). Alben und Hörbücher mit Kapiteln (Ordner-Folgen) laufen ohne Unterbrechung der Zeitleiste über die Tracks (11.4).
* **Kapitel (Rev. 4):** Hat die Folge Kapitel (11.4.8), steht in der Vollansicht unter dem Titel eine Zeile „**Kapitel 8: Das Echo (8 von 12)**“ und neben dem Knopf „Sperren“ der Knopf **„Kapitel“**. Er öffnet ein Blatt mit der Liste (Titel, „ab 2:49 · 0:19“, schon gehörte mit Häkchen, das aktuelle markiert und beim Öffnen sichtbar). **Tipp = dorthin springen und weiterspielen.** Die **Zeitleiste über das ganze Buch bleibt** (Entscheidung Tobias, Nr. 20: beides). Auf dem Sperrbildschirm kein Kapitel-Sprung (nur vorige/nächste Folge).
* **Abspielen (Rev. 5, G3, G4):** Vor jedem Start einer Folge (und nach jedem Fehler des `<audio>`-Elements) fragt die Seite per WebSocket `audio/bereit` (11.4.1). Antwort `bereit`: die Seite setzt den signierten Pfad als `src` (Link 24 Stunden, 11.4.2). `wird_vorbereitet`: Karte „Die Hörprobe wird vorbereitet …“ (5.3), nach 15 Sekunden fragt die Seite erneut. `fehlt`: Satz aus 6.1. Das `<audio>`-Element verrät den HTTP-Status nicht (Chromium meldet 401, 429, 503 und 404 alle als „Format error“, gemessen); darum liest die Seite den Zustand **nie** aus dem Fehler des Elements.
* **Hörkopie (Rev. 4):** Für Formate, die nicht jeder Browser spielt, spielt der Player automatisch die Hörkopie (11.4.7); die Seite merkt davon nichts, außer dem Satz „Die Hörprobe wird vorbereitet …“, wenn sie noch fehlt. Springen geht wie beim Original (Range-Anfragen auf eine fertige Datei).
* **Längeres Hören am gesperrten Handy (G18):** Reinhören ist zum **Erkennen** gedacht. Weil der Link jetzt 24 Stunden gilt, bricht ein Hörbuch nicht mehr nach einer Stunde ab; ob `<audio>` bei gesperrtem Bildschirm weiterspielt, hängt von Gerät und Companion-App ab und ist **nicht zugesagt**. Bei Ordner-Folgen (mehrere Dateien) wechselt die Quelle am Ende eines Tracks mit einer kurzen Lücke, auf iOS nur ohne Tap, wenn die Seite im Vordergrund ist; der Wechsel zum nächsten Track wird im Voraus signiert (`audio/bereit` für den nächsten Track). Beide Fälle sind der **erste** Test auf Tobias’ iPhone und Android (A0b).
* **Weiterhören:** Die Stelle wird **je Folge und je HA-Benutzer in Home Assistant** gespeichert (gleich auf Handy und Computer; 11.4). Sichtbar als Fortschrittsbalken in Liste und Folgenzeilen, als Reihe „**Am Handy weiterhören**“ in Bibliothek und Start, als Knopf „**Hier weiterhören**“ und als Sortierung „Zuletzt angehört“. Die Box hat ihre eigene Stelle; die Seite sagt es (G17). „Fertig gehört“ heißt: bis auf 2 Sekunden ans Ende.
* **Sperrbildschirm:** `navigator.mediaSession` setzt Titel, Eintrag und Art und verdrahtet Play, Pause, 30 s zurück/vor, vorige/nächste Folge und Springen. Vorschlag, ohne Gewähr auf allen Geräten (zu prüfen in A15b).
* **Fehlerfälle** (Texte in 6.1): Format spielt dieser Browser nicht; Datei nicht mehr da; Hörprobe wird vorbereitet; zu viele Wiedergaben gleichzeitig; Link abgelaufen (kommt nur nach über 24 Stunden Pause vor: die Seite fragt neu und macht an der Stelle weiter); keine Verbindung.
* **Prototyp:** Der Player spielt **kurze, im Script erzeugte Töne** (jede Folge eine eigene sanfte Tonfolge, 1 bis 5 Minuten), damit man Springen, Geschwindigkeit, Folgenwechsel und Weiterhören hört und ausprobiert; die Hörstelle liegt dort im Browser (`localStorage`), nicht in HA. Das Lied „Das Lied vom Mond“ (OGG) zeigt beim ersten Reinhören „Die Hörprobe wird vorbereitet“ und ist nach fünf Sekunden bereit.

### 5.13 Warteschlange „Nächster neuer Tobie“ (Runde 13, X13)

**Prinzip:** Tobies und Karten werden **nicht beschrieben**; die Box liest nur die Kennung. Statt eines Countdowns legt man **vorab am Handy** fest, was der **nächste unbekannte Tobie** spielen soll. **Nur Home Assistant ordnet zu**, keine Box-Änderung. Die Warteschlange ersetzt im Alltag den Lernmodus mit Countdown (7.2); der Lernmodus bleibt als Admin-Weg in „Technik › Boxen › <Box>“.

* **Anlegen (Weg 2 „Später auflegen“, Runde 16):** Im Reiter „Tobies“ → „+ Neuer Tobie“ → „**Später auflegen**“ („Erst wählen, was er spielen soll“), oder bei „Einem Tobie geben …“ aus der Bibliothek (dann mit festem Ziel). Dort: „**Auf welcher Box?**“ mit **Box 1 | Box 2 | Egal welche** (Vorgabe „Egal welche“; nichts ist ausgegraut, auch eine ausgeschaltete Box geht, die Warteschlange liegt in HA), danach die Zielwahl „Was soll er spielen?“ (5.4) bzw. bei festem Ziel der Knopf „**Vormerken**“. Danach die Seite „**Nächster neuer Tobie auf Box 1 spielt „Lange Serie“**“ („Kein Zeitlimit. Du musst die Seite nicht offen lassen.“, Knöpfe „Abbrechen“ und „Fertig“). Das Blatt „Tobie anlernen“ mit dem Abschnitt „Nächster neuer Tobie“ (Runde 13) entfällt. Ein **bekannter** Tobie wird bewusst über seine eigene Seite umgestellt (5.4).
* **Anzeigen und Abbrechen:** Im Reiter „Tobies“ steht je Eintrag eine Karte „Nächster neuer Tobie auf Box 1 spielt „Lange Serie““ / „Wartet auf einen unbekannten Tobie“ mit dem Knopf „**Abbrechen**“ (= Abbrechen, Meldung „Vormerkung abgebrochen.“). Auf „Geräte“ steht darüber hinaus die Karte „**Wartet auf einen neuen Tobie**“ (unter der Karte „Neuer Tobie auf Box 1 – was soll er spielen?“) als Zeilen (Muster X10, Pfeil „›“): „Nächster neuer Tobie auf Box 1“ / „spielt „Lange Serie“ · Nr. 1 von 2“; Tippen öffnet ein Blatt mit „**Nicht mehr warten**“. **Kein Zeitlimit:** ein Eintrag bleibt, bis ein Tobie aufgelegt oder er abgebrochen wird.
* **Auflegen:** Meldet die Box einen **unbekannten** Tobie (Ereignis `neue_tobies`, `mqtt-v1.md`), prüft HA die Warteschlange dieser Box: Einträge für diese Box oder „irgendeine“, **ältester zuerst**. Trifft einer zu, ordnet HA sofort zu (`zuordnung/set`, die Kennung steht in `neue_tobies`, also gilt die Regel „nur bekannte Kennungen“ aus 10.3) und entfernt den Eintrag. Die Seite zeigt die Meldung „**Box 1: Der neue Tobie spielt jetzt „Lange Serie“.**“ mit dem Knopf „**Name geben**“ (öffnet die Seite des Tobies mit dem Namensfeld, 5.7); der Tobie steht im Regal. Steht die Seite gerade auf der Wartekarte (Weg 2), geht sie zum Regal. Die Karte „Fertig!“ mit Name-Abfrage auf „Geräte“ entfällt (Runde 16). Wartet nichts, erscheint die Karte „Neuer Tobie auf Box 1 – was soll er spielen?“ (7.1).
* **Schutz:** (1) **Nur unbekannte Tobies, nie umhängen:** Die Warteschlange rührt keinen Tobie an, der schon ein Ziel hat; ein bekannter Tobie spielt weiter wie bisher, der Eintrag bleibt stehen. Umstellen geht nur bewusst (über die Seite des Tobies, 5.4). (2) **Zwei Einträge warten:** Sie werden in der Reihenfolge der Anlage bedient (**FIFO**); „irgendeine Box“ und „Box 1“ konkurrieren nach Anlagezeit. Jeder neue unbekannte Tobie nimmt den nächsten passenden Eintrag; ist keiner mehr da, kommt die normale Karte „Neuer Tobie“. (3) **Höchstens 5 Einträge** (`warteschlange_voll`: „Es warten schon 5 Tobies. Warte, bis einer aufgelegt ist, oder nimm einen aus der Liste.“); derselbe Eintrag (gleiches Ziel, gleiche Box) zweimal: „Das wartet schon.“ (4) **Doppelte Meldung** derselben Kennung (Prellen): eine Zuordnung (Idempotenz über die Kennung). (5) **Ziel inzwischen gelöscht** (Papierkorb): HA verwirft den Eintrag beim Auflegen (`ziel_unbekannt`) und zeigt die normale Karte „Neuer Tobie“. (6) HA-Neustart: die Warteschlange bleibt (persistiert).
* **Rechte:** **Alltag** (alle angemeldeten Benutzer): anlegen, ansehen, abbrechen. Unter dem Mengenschutz aus 10.3.
* **Lernmodus nur für Administratoren (X13a, Runde 16):** `lernmodus/*` bleibt im Vertrag und im Prototyp unter „Technik › Boxen › <Box> › Lernmodus starten …“ (Countdown, Seite „Tobie anlernen“, 7.2). **`lernmodus/start` ist wieder `admin`** (A1 hatte es auf Alltag gelockert, 10.2); die Alltagsseite ruft den Lernmodus nicht auf. Der Vertragsbedarf steht in der Liste unten (A0-Q).
* **Vertragsänderungen, nur Skizze; `docs/protocol/` ist nicht geändert, die Änderung ist offen und braucht die Freigabe von Tobias (Paket A0-Q):**
  * `ha-websocket-v1.md`: neue Befehle `warteschlange/set` (Eingabe `box`: Box-ID oder `alle`, `ziel` wie bei `zuordnung/set` mit `typ` `serie`, `folge`, `aktion`, in Stufe C `playlist`; Ausgabe `id`), `warteschlange/list` (Einträge mit `id`, `box`, `ziel`, `angelegt_von`, `angelegt_am`, Reihenfolge) und `warteschlange/abbrechen` (`id`); Abo-Ereignis `warteschlange` (`angelegt`, `abgebrochen`, `abgearbeitet` mit `kennung` und `eintrag_id`); Fehlercodes `warteschlange_voll`, `warteschlange_doppelt`, `ziel_unbekannt`; `neue_tobies/list`: neue Felder `automatisch_zugeordnet` (bool) und `ziel` für die Meldung „Name geben“; Tabelle in 10.2: die drei Befehle **alltag**.
  * **`lernmodus/start` zurück auf `admin` (X13a, Runde 16):** Rechte-Spalte in `ha-websocket-v1.md` und der Test in A1 (Tabelle 10.2). `lernmodus/antwort` und `lernmodus/abbrechen` gehören zum selben Vorgang und folgen (mit A0-Q bestätigen, Frage 31). Sonst keine Änderung am Lernmodus.
  * Datenmodell (`data-model.md`): **keine Änderung**; die Warteschlange liegt im HA-Speicher (`.storage` der Integration), nicht in `config.json` und nicht auf den Boxen.
  * `mqtt-v1.md` und Box: **keine Änderung** (genutzt wird das vorhandene Ereignis „neuer Tobie“; die Zuordnung geht wie bisher als neue Liste auf die Box).
  * Reihenfolge: A0-Q (Vertragsentwurf, Freigabe), dann A9c (unten, 15.1).

## 6. Zustände

| Zustand | Was die Seite zeigt |
|---|---|
| **Lädt** | Graue, leicht pulsierende Platzhalter-Karten (statt „Lade …“). Mit „reduzierte Bewegung“ ohne Pulsieren. Nach 10 s ohne Antwort wird es der Fehlerzustand. |
| **Leer** (noch nichts eingerichtet) | Start: statt Boxen „Noch keine Box eingerichtet. Bitte dem Administrator Bescheid sagen.“; Bibliothek: „Noch nichts da. Tippe auf „Hinzufügen“.“; Tobies siehe 5.7. **Seit Runde 12 mit eigenem Bild, einem Satz und einem Knopf, Abschnitt 6.2.** Es gibt immer einen Knopf als nächsten Schritt. |
| **Fehler beim Laden** | Rote Karte: „**Die Seite konnte nichts laden.** Home Assistant antwortet gerade nicht. Warte kurz und versuche es noch einmal. Wenn es so bleibt, sag dem Administrator Bescheid.“ Knopf „Noch einmal versuchen“. |
| **Verbindung weg** (Websocket zu) | Rotes Band oben: „**Keine Verbindung zu Home Assistant.** Die Ansicht wird von selbst aktuell, sobald die Verbindung wieder da ist.“ Knopf „Jetzt neu laden“. Boxen grau. Schreibende Knöpfe grau, bis die Verbindung wieder da ist. |
| **Box offline** | Statuskarte grau (5.1.1). Knopf „Auf Box 2“ grau mit Erklärung. |
| **Liste gesperrt** (`konfig.zustand` ≠ `ok`) | Nicht-Admin, Band oben: „Änderungen sind gerade gesperrt. Bitte dem Administrator Bescheid sagen.“ Alle Knöpfe, die die Liste ändern, grau. Admin: die Warnleiste von heute, in einfacheren Worten (der Administrator entscheidet, nicht die Partnerin). |
| **Alte Seite** (`hello.v` oder `unknown_command`) | „Die Seite ist veraltet. Bitte lade sie neu (am Handy: Seite nach unten ziehen oder Browser neu öffnen).“ (heute „Strg+F5“). |

**Grundsatz (Runde 12, X11): keine vorsorglichen Erklärkästen.** Die Seiten erklären nichts „für alle Fälle“ (erlaubte Formate, Größen, Kopierschutz, „Bildschirm anlassen“, Hinweis auf den NAS-Eingang, Satz zu Sortierung oder Papierkorb). Zeigen darf eine Seite nur **echte Zustände**: leere Zustände mit Bild (6.2), Fehler (6.1), „Bitte kurz ansehen“, „wird vorbereitet“, „Keine Verbindung“. Tritt ein Fehler ein, zeigt die Seite **genau diesen einen Fehler** mit dem, was zu tun ist (Texte in 6.1).

Änderungen gegenüber Rev. 1: „Hörspiele“ heißt „Bibliothek“; die Zeile „Liste gesperrt“ nennt „Änderungen sind gerade gesperrt. Bitte dem Administrator Bescheid sagen.“ nur für Nicht-Administratoren (U22b).

### 6.1 Fehlertexte: immer mit nächster Handlung (U20)

Die Seite übersetzt `error.code` (Vertrag W, Abschnitt 7) und bei Upload `fehler.code`. **`texte.js` wird gegen die Vertragstabelle vollständig abgeleitet** (der bestehende Test verlangt einen Text je Code);
die Alltagscodes stehen hier, der Rest bekommt den Standardtext, mit dem Code klein dahinter **nur für Administratoren**.

| Code | Text |
|---|---|
| `medien_nicht_erreichbar` | „Das NAS antwortet gerade nicht. Versuche es in ein paar Minuten noch einmal. Wenn es so bleibt, sag dem Administrator Bescheid.“ |
| `medien_schreibfehler` | „Das Speichern auf dem NAS hat nicht geklappt. Versuche es gleich noch einmal. Wenn es so bleibt, sag dem Administrator Bescheid.“ |
| `kein_speicher` | „Auf dem NAS ist kein Platz mehr. Bitte dem Administrator Bescheid sagen.“ |
| `mqtt_nicht_verbunden` | „Die Verbindung zu den Boxen ist gerade gestört. Es wurde nichts gesendet. Versuche es gleich noch einmal.“ |
| `box_offline` | „Box 2 ist aus oder nicht im WLAN. Schalte sie ein und versuche es noch einmal.“ |
| `konfig_nicht_bereit` | „Änderungen sind gerade gesperrt. Bitte dem Administrator Bescheid sagen.“ |
| `unauthorized` | „Dafür fehlt dir die Berechtigung. Frag den Administrator.“ |
| `zuordnung_geaendert`, `stand_veraltet` | „Jemand hat gerade etwas anderes geändert. Die Ansicht ist neu geladen. Bitte versuche es noch einmal.“ |
| `lernmodus_laeuft` | „Auf Box 1 läuft schon das Anlernen für ein anderes Hörspiel. Beende es zuerst.“ (Knopf „Dort beenden“ = `lernmodus/abbrechen`) |
| `format_nicht_erlaubt` | „Dieses Dateiformat spielt die Box nicht. Erlaubt sind MP3, M4A, M4B, AAC, FLAC, OGG, Opus und WAV.“ |
| `datei_zu_gross` | „Die Datei ist zu groß (mehr als 2 GB). Kopiere sie am Computer in den Eingang-Ordner auf dem NAS. Frag den Administrator nach dem Ordner.“ (die Zahl kommt aus `hello.grenzen`) |
| `zu_viele_uploads` | (kein Fehler: die Seite wartet und sendet danach weiter) |
| `name_ungueltig` | „Dieser Name geht nicht. Bitte kürzer oder anders schreiben.“ |
| `einstellung_ungueltig` | siehe 4.6 |
| `unknown_error`, unbekannter Code | „Das hat nicht geklappt. Versuche es noch einmal. Wenn es wieder nicht geht, sag dem Administrator Bescheid.“ (Code klein dahinter, nur für Admins) |
| Verbindung beim Upload abgebrochen (Seite geschlossen oder Bildschirm gesperrt, Runde 12, X11: erscheint erst, wenn es passiert) | „Die Verbindung ist abgebrochen. Ob die Datei angekommen ist, siehst du in ein paar Minuten unter „Gerade eben“. Wenn nicht, wähle sie noch einmal.“ |
| `rueckfrage_abgelaufen` | „Das hat zu lange gedauert. Der Tobie spielt wie vorher.“ |
| `kein_lernmodus` | „Es läuft gerade kein Anlernen. Starte es noch einmal.“ |
| `serie_nicht_gefunden`, `folge_nicht_gefunden`, `eintrag_nicht_gefunden` | „Das gibt es nicht mehr. Die Ansicht ist neu geladen.“ |
| `sortierung_laeuft` | „Es wird gerade einsortiert. Versuche es in einer Minute noch einmal.“ |
| `upload_laeuft` | „Es läuft schon ein Hochladen. Warte, bis es fertig ist.“ |
| `tobies_betroffen` | (kein Fehler: die Seite fragt mit Anzahl und Namen der Tobies nach und sendet mit `tobies_bestaetigt`) |
| `kennung_ungueltig` | „Dieser Tobie ist hier nicht bekannt. Lege ihn auf eine Box.“ |
| `ziel_ungueltig` | „Das geht als Ziel nicht. Wähle etwas anderes.“ |
| `zu_viele_aenderungen` (neu, V-4) | „Das waren gerade sehr viele Änderungen. Warte eine Minute und versuche es noch einmal.“ |
| `cover_ungueltig` (neu, V-1) | „Das Bild geht nicht. Nimm ein anderes Foto.“ |
| Format nicht abspielbar (Reinhören, Seite stellt es fest; nur noch, wenn es keine Hörkopie gibt, zum Beispiel ohne `ffmpeg`) | „Das kann dieser Browser nicht abspielen. Auf der Box spielt es trotzdem.“ |
| `audio/bereit` → `wird_vorbereitet` (neu, V-6/V-9; **kein Fehler**, eine normale Antwort) | „Die Hörprobe wird vorbereitet. Bei einem Lied dauert das etwa eine Minute, bei einem langen Hörbuch bis zu einer halben Stunde. Du kannst die Seite offen lassen, sie sagt Bescheid. Auf der Box spielt es schon.“ (die Seite fragt alle 15 Sekunden neu; ist es fertig: „Die Hörprobe ist fertig. Tippe auf Reinhören.“) |
| `hoerkopie_warteschlange_voll` (neu, V-9) | „Gerade sind viele Hörproben in Arbeit. Versuche es in einer Viertelstunde noch einmal. Auf der Box spielt es schon.“ |
| `audio/bereit` → `fehlt` / `hoerkopie.zustand = fehler` (neu, V-9; steht im Folge-Objekt) | „Für diese Datei gibt es keine Hörprobe. Auf der Box spielt sie trotzdem.“ (Administratoren sehen dahinter in „Technik“ den Grund, zum Beispiel `zu_lang`, `zeitgrenze`, `unplausibel`, und „Hörkopien neu erzeugen“) |
| `zu_viele_streams` (neu, V-6) | „Es läuft schon auf mehreren Geräten etwas. Beende dort das Hören und versuche es noch einmal.“ |
| Upload-Gruppe unvollständig (`gruppe_unvollstaendig`, neu, V-7; Hinweis im Eingangs-Eintrag, kein Fehlercode der Antwort) | „Es fehlt noch eine Datei. 2 von 3 Dateien sind angekommen. Wähle die fehlende Datei noch einmal. Kommt sie nicht, wird mit den vorhandenen einsortiert und mit „Bitte ansehen“ markiert.“ |
| `wunsch_ungueltig` (neu, V-7) | „Das passt so nicht zusammen. Wähle noch einmal, was du hochlädst.“ |
| `neu_einsortieren_nicht_moeglich` (neu, V-7) | „Das lässt sich nicht mehr anders einsortieren, weil schon etwas daran geändert wurde. Lege es in den Papierkorb und lade es noch einmal hoch.“ |
| Abspiel-Link abgelaufen (kommt nur nach über 24 Stunden Pause vor, G4) | (kein Fehler: die Seite fragt per `audio/bereit` neu und macht an der Stelle weiter; klappt es nicht: „Die Verbindung ist abgebrochen. Tippe auf Abspielen, dann geht es weiter.“) Die Seite erneuert den Link vorher (bei jedem Start und nach 20 Stunden), damit HA nie einen 401 sieht: jeder 401 einer Ansicht mit Anmeldung löst dort eine Meldung „Login attempt failed“ aus (11.4.2) |
| `konfig_zu_gross`, `export_*`, `anfrage_id_konflikt`, `box_unbekannt`, `datei_existiert`, `reihenfolge_ungueltig`, `serie_existiert`, `ueberraschung_existiert` | Standardtext (nur Administratoren sehen den Code) |

Fehler stehen als Karte am Ort der Handlung (nicht nur oben) **oder**, bei kurzen Fehlern zu einer Eingabe oder Aktion („Bitte einen Namen eingeben.“), als **Fehlermeldung unten**; beide bleiben, bis man „OK“ tippt oder die Meldung wegwischt (6.3), und werden Screenreadern über `role="alert"` vorgelesen. Erfolg: kurze Meldung unten (4,5 s, `role="status"`, 6.3).

### 6.2 Leere Zustände (neu in Runde 12, X3)

Tobias fand die leeren Zustände „technisch“. Jeder bekommt jetzt ein **eigenes kleines Bild**, **einen Satz** und **einen Knopf** als nächsten Schritt. Die Bilder sind **Inline-SVG** (200 × 150, `aria-hidden`, kein Alt-Text nötig, weil der Satz alles sagt), **ohne fremde Marken oder Figuren**, gezeichnet nur mit **Farben aus den Tokens** (`--primary-soft`, `--primary-ink`, `--card`, `--warn`, `--warn-bg`, `--ok`, `--text2`): in Hell, Dunkel und im Theme mit hellem Primärton stimmig, ohne eigene Dunkelvariante. Sie stehen in einer Karte mit 24 px Radius, Bild etwa 220 px breit, Satz 18 px, Knopf darunter.

| Zustand | Bild | Satz | Knopf |
|---|---|---|---|
| Bibliothek leer | leeres Regal mit Lücke und Note | „Noch nichts da. Tippe auf „Hinzufügen“.“ | **Hinzufügen** (primär, führt zu `#hinzufuegen`) |
| Filter ohne Treffer (Bibliothek) | Lupe mit Fragezeichen | „Nichts gefunden. Nimm einen Filter weg.“ | **Filter zurücksetzen** |
| Keine Tobies | lächelnder Tobie über der Box | „Noch keine Tobies. Lege einen Tobie auf eine Box, dann erscheint er unter „Geräte“.“ | **Zu den Geräten** |
| Keine Box eingerichtet (Geräte) | schlafende Box mit Zzz und gezogenem Stecker | „Noch keine Box eingerichtet. Bitte dem Administrator Bescheid sagen.“ | **Jetzt neu laden** |
| Suche ohne Treffer (Suchansicht, Tobies-Suche) | Lupe mit Fragezeichen | „Nichts gefunden zu „xyz“.“ | **Suche löschen** |
| Papierkorb leer (Technik) | Papierkorb mit Haken | „Der Papierkorb ist leer.“ | **Zur Bibliothek** |
| Gehört ohne Daten (Stufe B) | Kopfhörer mit leerem Diagramm | „Noch nichts gehört. Sobald eine Box spielt oder jemand reinhört, steht es hier.“ | **Zur Bibliothek** |

Der Suchbegriff steht im Satz als Text (`textContent`, nie als HTML). **Prototyp:** Im Menü „i“ gibt es den Schalter **„Leer zeigen“**; er zeigt alle sechs Bilder (Start, Bibliothek, Tobies, Suche, Technik → Papierkorb, Gehört), ohne dass man Daten löschen muss. Der Papierkorb liegt in „Technik“ unter „Papierkorb“ (aufklappen). Die Bilder sind ein Teil von **A6** (Arbeitspaket 15.1).

### 6.3 Meldungen: Erfolg geht, Fehler bleiben (neu in Runde 12, X7)

* **Erfolg** („Gespeichert. Die Boxen bekommen es gleich.“, „Fertig: spielt jetzt …“): kleine dunkle Meldung unten, über der Reiterleiste (und über dem Mini-Player, wenn er da ist), `role="status"`, **verschwindet nach 4,5 Sekunden** von selbst. Eine neue Erfolgsmeldung ersetzt die alte. **Ausnahme (Runde 16, X20 d):** Eine Erfolgsmeldung **mit Aktion**, zum Beispiel „**Rückgängig**“ nach dem Zuordnen (5.4) oder „**Name geben**“ beim Auflegen (5.13), bleibt **etwa 6 Sekunden**, damit man den Knopf erreicht (Knopf mindestens 44 px; sonst gleiche Regeln).
* **Fehler** („Bitte einen Namen eingeben.“, „Das kann dieser Browser nicht abspielen.“, Texte aus 6.1 als Meldung): Meldung in Fehlerfarben mit **2 px Rand**, `role="alert"`, mit Knopf **„OK“** (mindestens 44 px) und **bleibt, bis man „OK“ tippt oder sie nach links oder rechts wegwischt** (Schwelle 70 px, Pointer-Events). Mehrere Fehler stehen übereinander. Ein Erfolg entfernt keinen Fehler. Der Fokus wird nicht entführt.
* **Über einem offenen Blatt:** Ein offenes Blatt (`<dialog>`) liegt im Top-Layer und deckt alles andere zu. Der Meldungsbereich **zieht deshalb in den offenen Dialog um** und steht dann **oben** im Blatt (sonst wäre die Fehlermeldung zu „Namen eingeben“ unsichtbar und ihr „OK“ nicht bedienbar, weil der Rest der Seite gesperrt ist); nach dem Schließen geht er zurück nach unten.
* Gilt auch für die Fehlertexte aus 6.1 (Meldung am Ort der Handlung bleibt eine Karte). Texte stehen wörtlich in `texte.js` (A5), das Verhalten im Gerüst (A6).

## 7. Die Kernaufgaben als Abläufe

Gezählt wie in `ist.md`: Taps **auf der Seite**, ohne Texteingabe und ohne Auflegen des Tobies. Ehrlich dazu (U9a): „plus Öffnen“ der Seite, das sind in der HA-App zwei Taps (Seitenleiste, „Tobi Box“). Ziel höchstens drei.

### 7.1 (a) Neuer Tobie: „+ Neuer Tobie“ → auflegen → Ziel wählen: **3 Taps** (Runde 16, X20; vorher eine Karte mit Kacheln auf „Geräte“: 1 Tap)

Gezählt wie oben. Zwei Wege, beide beginnen im Reiter „Tobies“ mit der Kachel **„+ Neuer Tobie“** (Tap 1). Die Seite „Neuer Tobie“ (`#neu`) bietet **zwei große Zeilen**:

**Weg 1 „Leg ihn jetzt auf eine Box“** („Die Seite wartet auf ihn“; Tap 2):
1. Seite „**Leg den Tobie auf Box 1 oder Box 2**“ (Ring pulsiert, nicht bei „reduzierte Bewegung“; „Ich warte auf einen Tobie, den ich noch nicht kenne.“, Knopf „Abbrechen“). *(Körperlich)* die Partnerin legt den Tobie auf eine Box; die Box meldet ihn (`neue_tobies`).
2. Die Seite zeigt „**Neuer Tobie erkannt** auf Box 1.“ (grün), die Karte „**Wie soll er heißen?** Du kannst das überspringen.“ (Textfeld „Name, zum Beispiel Farbe oder Tier“; auf Touch-Geräten kein Autofokus, die Tastatur würde die Seite verdecken, U4) und „**Was soll er spielen?**“ mit der Zielwahl (5.4).
3. **Tap 3:** das Ziel (`zuordnung/set`, Ziel `serie`, `folge`, `aktion`, in Stufe C `playlist`; die Kennung steht in `neue_tobies`; der Name geht mit). Meldung „Fertig: Löwe spielt jetzt „…“.“ mit „**Rückgängig**“ (~6 s); der Tobie steht im Regal. „Rückgängig“ nimmt die Zuordnung zurück; der Tobie liegt dann wieder als unbekannter da („Geräte“ zeigt die Karte wieder).
4. Unter der Zielwahl, abgesetzt: „**Das war ein Versehen, nicht merken**“ (`neue_tobies/verwerfen`, Rückfrage „Nicht merken?“).

**Weg 2 „Später auflegen“** („Erst wählen, was er spielen soll“; Tap 2): **Warteschlange X13** (5.13). Box wählen (Vorgabe „Egal welche“), Ziel wählen (Tap 3), danach die Wartekarte („Nächster neuer Tobie auf Box 1 spielt „…“, kein Zeitlimit, die Seite darf zu sein“). Beim Auflegen ordnet HA sofort zu; die Seite zeigt „Box 1: Der neue Tobie spielt jetzt „…“.“ mit „**Name geben**“.

**Hat jemand einen Tobie aufgelegt, ohne die Seite zu öffnen** (kein Eintrag in der Warteschlange): Auf **„Geräte“** erscheint oben (unter den Box-Karten) die **Karte „Neuer Tobie auf Box 1 – was soll er spielen?“** (Warnfarbe, ganze Karte antippbar, „Gerade aufgelegt, vor 2 Minuten.“) und der **Punkt mit Zahl am Reiter „Geräte“**, damit sie nicht übersehen wird. Ein Tipp öffnet dieselbe Seite wie nach dem Erkennen in Weg 1 (Name, Zielwahl, Versehen): **2 Taps** (Karte, Ziel) plus Öffnen. Eine HA-Automation „Neuer Tobie → Mitteilung aufs Handy, Tippen öffnet `/tobibox`“ liegt als **Vorlage** in `homeassistant/README.md` (keine neue Funktion, U9).

**Mit festem Ziel** (von „Einem Tobie geben …“, 5.4): Die Seite „Neuer Tobie“ zeigt oben „**Er soll spielen:** …“; in Weg 1 entfällt die Zielwahl (Knopf „Fertig“), in Weg 2 steht „Vormerken“ statt der Zielwahl. Danach zurück zur Serie.

Fehler: Liste gesperrt → Zeilen grau, Band (Abschnitt 6). Zuordnung existiert schon (zwei Fenster): Seite lädt neu, „Dieser Tobie wurde gerade woanders zugeordnet.“

Heute: 5 Taps plus Kennung lesen.

### 7.2 (b) Eintrag, Lied oder Folge → „Einem Tobie geben …“: **3 Taps** (Runde 16, X20; vorher das Blatt „Tobie anlernen“)

1. **Tap 1:** Zeile in der Bibliothek (öffnet die Serienseite). Bei einem Lied oder einer Folge im Suchtreffer: „⋯“ in der Zeile.
2. **Tap 2:** „**Einem Tobie geben …**“ in der Karte „Gespielt von“ (bei einer einzelnen Folge: „⋯“ der Zeile, dann „Einem Tobie geben …“, ein Tap mehr). Hat der Eintrag schon Tobies, zeigt die Karte ihre Chips (Tipp = Seite des Tobies, 5.7).
3. **Tap 3:** ein Tobie im Regal („Welcher Tobie soll das spielen?“). Er spielt das ab sofort (`zuordnung/set`), Meldung mit „Rückgängig“ (~6 s), zurück zur Serie; die Karte zeigt seinen Chip. Oder „+ Neuer Tobie“ (Weg 1 oder 2, 7.1, mit festem Ziel).

**Lernmodus mit Countdown (nur Administratoren, X13a):** „Technik › Boxen › Box › Lernmodus starten …“, Zielwahl, dann die Seite „Tobie anlernen“. Seit X13 und Runde 16 ist das **nicht** der Alltagsweg (Warteschlange, 5.13, 7.1).

L1. Die Seite wechselt zu „Tobie anlernen“ (`#anlernen`): Ring-Symbol (pulsiert, nicht bei „reduzierte Bewegung“), Überschrift „**Jetzt Tobie auf Box 1 legen**“,
   „Dieser Tobie soll „Lange Serie“ spielen. Ich warte noch 118 Sekunden.“ (Zähler aus `frist_bis`, wird nicht vorgelesen), Knopf „Abbrechen“ (= `lernmodus/abbrechen`).
L2. *(Körperlich)* Tobie auflegen. Ereignis `lernmodus`/`zugeordnet`: grünes Häkchen, „**Erkannt!** Dieser Tobie spielt jetzt „Lange Serie“.“,
   **Name-Abfrage** (Textfeld, überspringbar), Knöpfe „Noch einen Tobie anlernen“, „Fertig“ (zurück zum Eintrag). Der Name geht schon mit `lernmodus/start` (`name`), wenn man ihn vorher kennt; sonst setzt ihn die Seite danach mit `zuordnung/set`. Der neue Tobie erscheint auch unter „Tobies“, ohne Namen.
L3. Fälle:
   * Tobie hat schon ein Ziel (`rueckfrage`): Blatt „**Dieser Tobie spielt schon etwas.** Er spielt jetzt „Test-Serie“. Soll er stattdessen „Lange Serie“ spielen? Du hast dafür noch 10 Sekunden.“
     Knöpfe „Nein, so lassen“ (Vorgabe, Fokus), „Ja, ändern“ (= `lernmodus/antwort`). Zeit abgelaufen: „Das hat zu lange gedauert. Der Tobie spielt wie vorher.“ (+1 Tap).
   * Abgelaufen (`abgelaufen`): „**Kein Tobie erkannt.** Die Zeit ist abgelaufen. Lege den Tobie nach dem Start gleich auf die Box.“ „Noch einmal versuchen“ / „Zurück“.
   * Box lehnt ab (`box_lehnt_ab`, `zeit_unsicher`): „Box 1 kann gerade nicht lernen, weil sie die Uhrzeit nicht sicher kennt. Versuche es in ein paar Minuten noch einmal.“
   * Box aus (`box_offline`): Knopf schon vorher grau (4.3).
   * Läuft schon ein Lernvorgang: `lernmodus_laeuft`, Text in 5.1. Die Seite zeigt bei erneutem Öffnen einen offenen Vorgang weiter an (Abo `lernmodus`).

Heute: 5 bis 9 Taps (`ist.md`).

### 7.3 (c) Hinzufügen: **4 Taps in der Bibliothek, 5 von den anderen Reitern** (Rev. 4: eine Wahl mehr, dafür verständlich), Wartezeit ohne Tippen

1. **Tap 1:** das „+“ in der Bibliothek (Runde 15, X29; vom Start kommt der Tap auf den Reiter Bibliothek davor dazu). **Tap 2:** „Dateien wählen“ (System-Auswahl) oder am Computer „Ordner vom Computer wählen“ bzw. Hineinziehen.
2. **Tap 3: „Was lädst du hoch?“** Das Blatt (5.6) fragt mit vier **Kacheln** (Runde 12, X12; die Zeilen a), b), c) und e) der Tabelle sind die Kacheln 1 bis 4, d) entfällt). Es ersetzt das alte Blatt „In welches soll es?“. Je nach Karte:

   | Karte | Was die Vorschau noch fragt | Satz in der Vorschau (Beispiele aus dem Prototyp) |
   |---|---|---|
   | **a) Neues Hörspiel, Hörbuch oder Album** | **Name** (aus den Angaben der ersten Datei vorgeschlagen, sonst aus dem Dateinamen) und **Art**: Hörspiel · Hörbuch · Album · Geschichten (aus den Angaben vorgeschlagen, ohne erklärenden Hinweis (X11); bisher: „Vorgeschlagen aus den Angaben in den Dateien.“ oder „Geraten, …“) | „3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.“ · „4 Dateien → neues Album „Sommerlieder“, Lied 1–4.“ · „8 Dateien → neues Hörspiel „Die Wolkenreise“, Folge 1–8.“ · „1 Datei → neues Hörbuch „…“ (ein Kapitel).“ |
   | **b) Folgen zu einem vorhandenen hinzufügen** | **Wohin?** Sofort die Auswahl **mit Suche, Covern und Art-Knöpfen** (wie in 5.4, aber **nur** Hörspiele, Bücher, Alben; **ohne** Einzeltitel und ohne „Gute Nacht“); danach steht der Eintrag mit Cover in der Vorschau, „Ändern“ wählt neu | „3 Dateien → 3 neue Folgen in „Lange Serie“ (Folge 13–15).“ · „2 Dateien → 2 neue Folgen in „Lange Serie“ (Folge 21–22).“ (hat die Serie 20 Folgen) · bei Hörbuch „… neue Teile …“, bei Album „… neue Lieder …“ |
   | **c) Einzelne Folge oder einzelnes Lied** | **Art**: Lied · Geschichte · Folge · Hörbuch (Vorgabe Lied) und **ein Name je Datei** (die ersten drei als Felder, der Rest aus den Angaben) | „1 Datei → 1 einzelnes Lied: „Der Mond und der Fuchs“.“ · „5 Dateien → 5 einzelne Lieder.“ (bis 3 Dateien mit Namen) |
   | **d) (entfällt, Runde 12 X12)** | – | Playlists lädt man nicht hoch, man füllt sie aus der Bibliothek (13.1). Nach dem Hochladen bietet die Fertig-Karte „Zur Playlist hinzufügen“ (Stufe C, 13.7). |
   | **e) Weiß nicht – sortier du** | nichts; ein Absatz erklärt: „Ich lese die Angaben in den Dateien (Album, Interpret, Titel). Dateien, die zum selben Album gehören, bleiben zusammen. Passt etwas zu einem Hörspiel, das schon da ist, kommt es dort dazu. Wenn ich unsicher bin, steht danach „Bitte ansehen“ da, und du kannst es ändern.“ | „1 Datei → ich sortiere nach den Angaben in den Dateien ein. Meine Vermutung: ein einzelnes Lied „Der Mond und der Fuchs“.“ · „3 Dateien → ich sortiere … Meine Vermutung: neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.“ |

   Der Satz ändert sich **sofort** beim Tippen im Namensfeld und beim Wechsel der Art (Bereich mit `role="status"`, `aria-live="polite"`). Unter dem Satz stehen bei a) und b) bis zu vier Zeilen „Kapitel 1 · Der Hafen“ (bzw. „Folge 13 · …“, „Lied 1 · …“) als Vorschau, was aus den Dateien wird; „… und 4 weitere“.
   **Die Nummern sind eine Vorschau** (ohne eigenen Hinweistext, X11; „Folge 13–15“ = nach den vorhandenen 12); Nummern aus den Angaben in den Dateien haben beim Einsortieren Vorrang (Vertrag W 11.4 bis 11.6).
3. **Vorschau und Start (Tap 4):** Knöpfe „Abbrechen“, „**Ändern**“ (zurück zu den Karten; die Eingaben bleiben erhalten) und „**Hochladen**“ (primär). „Hochladen“ prüft: bei b) fehlt die Wahl → Meldung „Bitte zuerst wählen, wohin es soll.“; bei a) fehlt der Name → „Bitte einen Namen eingeben.“. Wer aus einem Eintrag heraus hochlädt („Dateien in diesen Eintrag“), springt direkt zur Vorschau von b). Die **Hörbuch-Frage** („Gehören die Dateien zu einem Hörbuch?“, U12b) entfällt: die Art in a) beantwortet sie.
   **Was die Wahl im Backend bewirkt:** Die Seite sendet sie als **Wunsch** mit dem Upload (`ziel`, `art`, `name`, `serie_id`, `gruppe`, `gruppe_anzahl`; V-7). Der Wunsch **gilt vor den Tags**: ein „Hörbuch“ wird **eine** Folge mit den Dateien als Kapitel, ein „Album“ oder „Hörspiel“ je Datei **eine** Folge, auch wenn alle dasselbe Album nennen (bisher machte das Einsortieren aus gleichem Album immer **eine** Folge mit Tracks, Vertrag W 11.3). Der Wunsch „Weiß nicht“ (`auto`) ändert nichts: Es gilt das heutige Einsortieren (Vertrag W 11.3 bis 11.5), dazu der Art-Vorschlag (V-2).
   **Mehrere Dateien bleiben zusammen (Rev. 5, G2):** Ein Wunsch `neu` oder `ergaenzen` mit mehreren Dateien ist nur gültig, wenn die Seite die **Zahl der Dateien** mitschickt (`gruppe_anzahl`, 2 bis 200). Der Eingang sortiert die Gruppe erst ein, wenn alle Dateien da sind (oder nach **30 Minuten Ruhe** ohne neue Datei, dann `teilweise`: einsortiert, was da ist, mit „Bitte ansehen“ und dem Hinweis `gruppe_unvollstaendig`). Ohne diese Zusage würde die Sammelzeit von 20 Sekunden (`UPLOAD_SAMMELZEIT_S`) nach dem letzten fertigen Upload eine lange Datei vom Handy (Minuten) zerreißen, und weil `neu` nie zusammenführt, entstünden „Kapitän Knopf (2)“, „(3)“ … . Der Wunsch wird **je Gruppe einmal** gespeichert (im persistenten `vorgaben`). Die Seite zeigt während des Hochladens „Datei 2 von 3 wird hochgeladen …“ und „Einsortiert wird erst, wenn alle 3 Dateien da sind.“; bricht eine Datei ab, steht „Es fehlt noch eine Datei“ mit dem Knopf „Fehlende Datei wählen“ (6.1). Bei `einzeln` hat jede Datei ihren eigenen Upload ohne Gruppe (kein Warten).
4. Der Upload startet sofort. **Ein** Eintrag für alle Dateien dieses Hochladens (bei c) mit mehreren Dateien ebenso) unter „**Zuletzt hinzugefügt**“, mit Dateinamen („3 Dateien: 01 Der Hafen.mp3, 02 Die Karte.mp3 …“):

   | Schritt | Anzeige |
   |---|---|
   | 1 | **„Wird hochgeladen … 37 %“** (bei mehreren Dateien „Datei 2 von 3 wird hochgeladen … 37 %“ und „Einsortiert wird erst, wenn alle 3 Dateien da sind.“) mit Balken über alle Dateien (`role="progressbar"`), dreiteilige Leiste (Hochladen · Einsortieren · Fertig) |
   | 2 | **„Wird einsortiert …“** |
   | 3a | **fertig:** grüne Marke, was daraus geworden ist („Hörbuch „Kapitän Knopf“ · 3 Kapitel“, „„Lange Serie“ · Folge 13–15“, „„Der Mond und der Fuchs“ · einzelnes Lied“) und der Knopf „Öffnen“ (44 px); nur bei „Weiß nicht“ zusätzlich „Art: Musik (aus den Tags vorgeschlagen). Stimmt nicht? Im Eintrag „Art ändern“.“ |
   | 3b | **bitte kurz ansehen:** gelbe Karte mit dem Grund und „**Daraus ist geworden:** …“, Knöpfen „Ansehen“, „**Das ist richtig**“ (`einsortierung/bestaetigen`) und „**Anders einsortieren …**“ (öffnet dieselbe Wahl wie 5.6, siehe Punkt 10 unten; auf der Serienseite heißt die Karte weiter „Das stimmt nicht“ und bietet als **erste** Möglichkeit „Anders einsortieren …“ (nur bei „bitte ansehen“ oder wenn der Eintrag jünger als 24 Stunden ist, G9), dann „Anderem zuordnen …“ und „In den Papierkorb …“, U11) |
   | 3c | **geht nicht:** rote Karte „**Geht leider nicht.** <Grund und nächste Handlung>“ |
| 3d | **Es fehlt noch eine Datei (Rev. 5):** gelbe Karte „**Es fehlt noch eine Datei.** 2 von 3 Dateien sind angekommen. …“ mit „Fehlende Datei wählen“; nach 30 Minuten wird mit den vorhandenen einsortiert und „Bitte ansehen“ gezeigt |

5. **Zustand ohne Sitzung (U13):** Die Seite lädt beim Öffnen `eingang/list` und zeigt **Einträge der letzten 24 Stunden** (`fertig_am`), auch vom NAS oder von einem anderen Gerät, mit „vom NAS“/„vom Handy“ (`quelle` ist jetzt **fest** im Vertrag, V-5). Ältere blendet die Seite aus.
   „Das ist richtig“ merkt nur der Serverzustand `pruefen`; „Erledigte ausblenden“ merkt nur das Gerät (ehrlich gesagt: „auf diesem Gerät“). Kein neuer Serverzustand.
6. **Gründe „bitte kurz ansehen“** und **„geht nicht“** wie Rev. 1:

   | Code | Text für Eltern |
   |---|---|
   | `tags_fehlen` | „In der Datei steht kein Albumname. Name und Hörspiel sind aus dem Dateinamen geraten.“ |
   | `serie_aus_interpret` | „Das Hörspiel ist aus dem Künstlernamen in der Datei abgeleitet.“ |
   | `serie_aus_ordner` | „Das Hörspiel ist aus dem Ordnernamen abgeleitet.“ |
   | `serie_widerspruch` | „Die Dateien nennen verschiedene Hörspiele. Das häufigste wurde genommen.“ |
   | `serie_mehrdeutig` | „Es passten mehrere Hörspiele. Das älteste wurde genommen.“ |
   | `nummer_widerspruch` | „Die Dateien nennen verschiedene Folgen-Nummern.“ |
   | `nummer_doppelt` | „Diese Folgen-Nummer gibt es in dem Hörspiel schon.“ |
   | `track_doppelt`, `track_teils_leer` | „Die Reihenfolge der Kapitel ist nicht eindeutig.“ |
   | `name_geaendert` | „Der Name ging so nicht und wurde angepasst.“ |
   | `folge_gleicher_name` | „Eine Folge mit diesem Namen gibt es schon.“ |
   | `teilweise_doppelt` | „Ein Teil war schon da und wurde nicht noch einmal abgelegt.“ |
   | `vorgabe_serie_fehlt` | „Das gewählte Hörspiel gibt es nicht mehr.“ |
| `serie_name_doppelt` (neu, V-7) | „Einen Eintrag mit diesem Namen gab es schon. Der neue heißt „Kapitän Knopf (2)“.“ |
| `art_geraten` (V-2) | „Die Art ist geraten. Stimmt das?“ |

   **Gründe „geht nicht“** (Eingangs-`hinweise`, Upload-`fehler`): `kopierschutz`: „Diese Datei ist kopiergeschützt (zum Beispiel von Audible oder Apple Books). Die Box kann sie nicht abspielen. Nimm eine Datei ohne Kopierschutz.“ ·
   `nicht_lesbar`, `probedekodierung_fehlgeschlagen`: „Die Datei ist kaputt oder unvollständig. Bitte noch einmal kopieren.“ · `keine_audiodateien`: „Darin ist keine Audiodatei.“ ·
   `ffprobe_fehlt`: „Das Prüfprogramm fehlt. Bitte dem Administrator Bescheid sagen.“ · `verschieben_fehlgeschlagen`: „Das Ablegen hat nicht geklappt. Versuche es später noch einmal, sonst frag den Administrator.“ ·
   `doppelt`: „Das gab es schon und wurde nicht noch einmal angelegt.“ Die Zeile erklärt, nicht den Code. „Entfernen“ eines blockierten Eintrags ist Admin-Sache („Technik“).

7. **Zwei Uploads gleichzeitig:** weitere Dateien warten („wartet“) und gehen nacheinander; kein 429 sichtbar. **Abbrechen** solange hochgeladen wird (`AbortController`).
8. **Wenn das Handy den Bildschirm sperrt:** Safari und Chrome frieren die Seite ein. Darum der Hinweis in 5.6 und beim Zurückkehren: Zeilen, die bei „wird hochgeladen“ stehen geblieben sind, werden „Unterbrochen. Wähle die Datei noch einmal.“
9. **Proxy-Grenze (U12e):** HTTP 413 von einem vorgeschalteten Proxy wird als `datei_zu_gross` gezeigt; „Technik“ nennt die tatsächliche Grenze.
10. **NAS-Weg (Rev. 4, dieselbe Wahl):** Dateien im Eingang-Ordner erscheinen ohne Hochladeschritt direkt bei „Wird einsortiert …“ und werden wie bisher **automatisch** einsortiert („Weiß nicht – sortier du“). Sie stehen unter „Zuletzt hinzugefügt“ mit „vom NAS“, und der Satz „Daraus ist geworden: …“ sagt, was die Automatik gemacht hat. Sieht es falsch aus, hat die Karte „bitte ansehen“ den Knopf **„Anders einsortieren …“** (**Rev. 5, G9:** nur für Einträge, die „bitte ansehen“ sind **oder** höchstens 24 Stunden alt; das Backend prüft es genauso, die Ruhezeit gilt, es zählt als Papierkorb-Aktion; „Nicht angehört“ prüft das Backend intern an den fremden Hörstellen, ohne sie anzuzeigen): Er öffnet **dasselbe Blatt**, nur mit dem Titel „**Was ist das?**“ (die Dateien liegen ja schon da: „6 Dateien im Eingang vom NAS. Was ist das?“), dieselben fünf Karten, dieselbe Vorschau in Sätzen; der Start-Knopf heißt dort **„Neu einsortieren“**. Das Backend holt die Folgen dieses Eintrags aus den Medien in den Eingang zurück und sortiert sie mit dem Wunsch neu ein (`einsortierung/neu`, V-7). Das geht nur, solange **nichts** an ihnen geändert wurde (Name, Verschieben, Tobie, angehört); sonst `neu_einsortieren_nicht_moeglich` mit dem Rat „in den Papierkorb und noch einmal hochladen“. **Machbarkeit zu prüfen in A3d:** Vertrag W kennt heute keinen Weg zurück von den Medien in den Eingang; fällt er zu teuer aus, bleibt für NAS-Einträge nur „In den Papierkorb …“ und neu hochladen (Frage 25, Variante 2: erst fragen, dann einsortieren).
11. **„Jetzt prüfen“** (`eingang/sortieren`) wird für Nicht-Administratoren **ohne `sofort`** gesendet (U10) und sagt: „Dateien werden erst nach 2 Minuten Ruhe einsortiert.“ `sofort` bleibt in „Technik“.

Heute: 3 bis 5 Taps plus Suchen im Reiter „Eingang“. Rev. 3: 3 Taps. Rev. 4: **4** Taps, dafür sagt jeder Schritt, was passiert. Rev. 5 ändert die Zahl nicht.

### 7.4 (d) Abends: **2 Taps von überall** (Runde 15: Reiter „Geräte“, der Abschnitt „Abends“ steht auf der Seite; „Mehr“ und der Startknopf „Abends“ entfallen)

* **Weg dorthin:** Reiter „Geräte“ (1); „Abends“ ist ein Abschnitt unter den Boxen. Gleich von jedem Reiter aus.
* Gute Nacht ändern: „Geräte“ (1), Schnellwahl-Knopf, z. B. „60 Min.“ (2), „Speichern“ (3). Von 30 auf 240: Auswahlfeld statt 42 Taps (U16a).
* Leise-Zeit hinzufügen mit Vorgabe (So–Do, 19:30–06:30, Still): „Geräte“ (1), „+ Leise-Zeit“ (2), „Speichern“ (3). Andere Tage +1 (Schnellwahl), andere Zeiten: je Feld der System-Zeitwähler (X22).
* Bestehende Zeit ändern: „Geräte“ (1), Tipp auf den Abschnitt in der Wochenansicht (2), Wert ändern, „Speichern“ (3+).
* Gute-Nacht-Tobie: „Tobies → + Neuer Tobie“ mit der „Gute-Nacht-Karte“ **oder** ein belegter Tobie über „Tobies → Tobie → Gute-Nacht-Karte“ (U16c; Lernmodus bleibt für Folgen und Einträge, Aktionen gehen nicht über ihn, `mqtt-v1.md` 3.8).

## 8. Zusammenfassung der Taps

| Aufgabe | Heute | Neu |
|---|---|---|
| (a) Neuer Tobie, Weg 1 „jetzt auflegen“ (7.1) | 5 bis 8 | **3** (+ Neuer Tobie, Leg ihn jetzt auf eine Box, Ziel; der Name steht auf derselben Seite); von „Geräte“ aus **2** (Karte, Ziel), plus Öffnen |
| (a) Neuen Tobie einem **alten** Eintrag oder Lied geben | 5 bis 8 | **3** plus Tippen (Zielwahl: Suche, Treffer; bei „Folge oder Lied“ +1 zum Aufklappen) |
| Tobie umstellen | 6 bis 9 | **3** (Tobies, Tobie, Ziel; „Rückgängig“ ~6 s statt Rückfrage) |
| (b) Eintrag → einem Tobie geben (Runde 16) | 5 bis 9 | **3** (Zeile, „Einem Tobie geben …“, Tobie) |
| (b′) Tobie **vorab festlegen** (Weg 2, Warteschlange X13) | – | **3** (+ Neuer Tobie, Später auflegen, Ziel; die Box ist mit „Egal welche“ vorgewählt); danach nichts mehr auf der Seite, Auflegen jederzeit |
| Folge oder Lied in eine Playlist (Stufe C) | – | **3** („⋯“, „Zur Playlist hinzufügen“, Playlist) |
| Lied/Folge → einem Tobie geben | nur Technik | **4** (Zeile bzw. Lupe, „⋯“, Einem Tobie geben …, Tobie) |
| (c) Hinzufügen | 3 bis 5 + Suchen | **4** in der Bibliothek, **5** von den anderen Reitern („+“, Dateien, Karte, Hochladen; Runde 15: das „+“ liegt in der Bibliothek). Bei b) +1 für die Wahl des Eintrags |
| Einzelnes Lied hochladen | nur über „Einzelfolgen“ | **4** (Hinzufügen, Dateien, „Einzelne Folge oder einzelnes Lied“, Hochladen) |
| (c2) „bitte ansehen“ bestätigen | 3 bis 7 | **1** („Das ist richtig“) |
| Fehl-Upload korrigieren | Sackgasse | **3** („Das stimmt nicht“, Papierkorb, Bestätigen) oder **4** („Anders einsortieren“, Karte, Neu einsortieren) |
| (d) Gute Nacht ändern | 3 + Tippen | **3** von jedem Reiter (Geräte, Schnellwahl, Speichern; Runde 15) |
| „Abends“ öffnen | 1 (Reiter) | **2 von überall** (Reiter „Geräte“; der Abschnitt steht auf der Seite; Runde 15: kein Startknopf, kein „Mehr“) |
| „Gehört“ öffnen (Stufe B) | – | **1** (Reiter „Geräte“; Abschnitt auf der Seite) |
| Cover ersetzen | nur NAS von Hand | **4** (Cover ändern, Foto, Zuschneiden, Speichern) |
| Etwas in der Bibliothek finden | – | **1 bis 2** (Lupe, Treffer; plus Tippen) |
| Hineinhören (Reinhören) | – | **2** (Zeile, „Reinhören“) |
| Weiterhören (am Handy) | – | **1** (Abspielknopf in der Reihe „Am Handy weiterhören“ auf dem **Start**; seit X27a nicht mehr in der Bibliothek) |
| In ein Kapitel springen | – | **2** (Zeile „Kapitel“ auf der Serienseite: ein Tap; im Player „Kapitel“, Zeile) |

## 9. Wohin jede heutige Funktion wandert

Alles bleibt, wie es heute funktioniert; nur Ort und Text ändern sich. **Die ganze heutige Technik-Seite wird eingebettet** (5.9), also bleibt jede Zeile der Tabelle aus Rev. 1 für Administratoren erreichbar. Die Alltagsfassung:

| Heute (Fundort in `ist.md`) | Neu | Wer |
|---|---|---|
| Reiter „Serien“ | Reiter „Bibliothek“ (Arten, Liste, Suchansicht, Blatt „Sortieren und Filter“, Reihen „Weiterhören“ und „Neu“) | alle |
| „Hochladen“-Karte | „Hinzufügen“ (7.3): Blatt „Was lädst du hoch?“ mit vier Kacheln (über das „+“ in der Bibliothek), Vorschau in Sätzen; Vorgabe-Serie über Kachel b) („Zu Vorhandenem“) oder „Dateien in diesen Eintrag“; „Liste leeren“ wird „Erledigte ausblenden (auf diesem Gerät)“ | alle |
| „Neue Serie“ (leer anlegen), Überraschungs-Serie | Technik → Bibliothek aufräumen | Admin |
| (neu) Hörkopien | Technik → Bibliothek aufräumen: Stand und „Hörkopien neu erzeugen“ | Admin |
| „Freigabe prüfen“ | Technik → „Medien neu einlesen“; beim Öffnen der Seite höchstens alle 10 Minuten (`medien/pruefen`, ohne Cover-Suche) | Admin / Auslöser alle |
| Serie/Folge umbenennen | Serienseite → „⋯“ → „Name ändern“, Folgenzeile → „⋯“ → „Name ändern“ | alle |
| „Alles geprüft“ | „Das ist richtig“ / „Das stimmt nicht“ | alle |
| Folge hoch/runter | Serienseite → „⋯“ → „Reihenfolge ändern“ (▲ ▼) | Admin (U23b) |
| Folge verschieben | Zeile → „⋯“ → „In anderes verschieben …“ | **alle** (Runde 6) |
| Folge löschen / Serie löschen | Folgenzeile → „⋯“ → „Papierkorb …“; Serienseite → „⋯“ → „In den Papierkorb …“ | **alle** (Runde 6) |
| Serien zusammenführen | Serienseite → „⋯“ → „Zusammenführen …“ | Admin |
| Reiter „Eingang“ | Alltag: „Zuletzt hinzugefügt“ in „Hinzufügen“. Voll: Technik → Eingang im Detail | alle / Admin |
| „Erneut einsortieren“ / „Sofort“ / „Entfernen“ | „Jetzt prüfen“ (ohne `sofort`) für alle; `sofort` und „Entfernen“ in Technik | alle / Admin |
| „Neue Tobies“, „Verwerfen“ | Karte „Neuer Tobie auf Box 1 – was soll er spielen?“ (Geräte), „Das war ein Versehen, nicht merken“ (7.1) | alle |
| „Zuordnen“ (Serie / **einzelne Folge** / Aktion) | Reiter „Tobies“: Tobie → „Was soll … spielen?“, „+ Neuer Tobie“ (5.4, 5.7, 7.1); Bibliothek: „Einem Tobie geben …“ (Serien- und Playlist-Seite, Menü der Folge); „Gute-Nacht-Karte“; Aktion „Status“ nur Technik → Tobies im Detail | alle / Admin |
| Lernmodus | Technik → Boxen → Box → „Lernmodus starten …“ (7.2; seit Runde 16 nicht mehr aus der Bibliothek) | Admin |
| „Kennung von Hand eingeben“, Kennung, Fehlmarken | Technik → Tobies im Detail | Admin |
| Zugeordnete Tobies: Name, Ziel ändern, Lösen | Reiter „Tobies“ (5.7) | alle |
| Reiter „Boxen“, „Sync jetzt“, Meldungen | Alltag: Status-Satz (5.1.1). Voll: Technik → Boxen im Detail, Meldungen | alle / Admin |
| Liste, Revision, Export, „Liste neu ausrollen“ | Technik → Liste, Sicherung, Export (plus „Frühere Stände ansehen“) | Admin |
| Warnleisten | Admin oben auf jeder Seite; Nicht-Admin: „Änderungen sind gerade gesperrt.“ | Admin / alle |
| Reiter „Korb“ | Technik → Papierkorb (Wiederherstellen, **Letzte Stunde zurückholen**, **Leeren**, mit „gelöscht von …“) | Admin |
| Einstellungen: Leise-Zeiten | „Geräte“ → Abschnitt „Abends“ (Wochenansicht, Blatt); Zeitzone in Technik | alle / Admin |
| Einstellungen: Gute Nacht (Timer) | „Geräte“ → „Abends“ (Schnellwahl); „Ausblenden“ in Technik → Weitere Einstellungen | alle / Admin |
| Einstellungen: Lesezeichen-Tage, Upload-Grenze | Technik → Weitere Einstellungen; Grenze in der Integration | Admin |
| HA-Entitäten, HA-Aktionen | unverändert in HA; Aktionen nur für Administratoren (U1, behoben in Commit d41e319) | – |

## 10. Rechte: wer darf was

### 10.1 Was nötig ist (U1, U7, U19)

1. **HA-Aktionen** (`services.py`) sind seit Commit d41e319 **nur für Administratoren** (`async_register_admin_service`, U1). Ein Test ruft jede Aktion als Nicht-Administrator auf und erwartet `Unauthorized`. Der Prüfabschnitt „gegen die HA-API“ im Vertrag W nennt das.
2. **Backend zuerst, Panel zuletzt (U7):** Die Rechte je Befehl (10.2) und der Schutz (10.3) kommen im ersten Arbeitspaket (A1), **ohne** das Panel zu öffnen: `require_admin` bleibt `True`, bis Tobias die Abnahme gemacht hat (A-1-Abnahme). Erst dann der eigene kleine Schritt A17
   „Seite für alle öffnen“ (`require_admin=False`), mit Test in `test_init.py` (heute prüft er `require_admin is True`). Vorher wird die Tabelle 10.2 mit einem Testbenutzer geprüft.
   **Ehrlich dazu (G19b):** A1 lockert die Rechte bestehender Befehle (zum Beispiel `einsortierung/bestaetigen`; `lernmodus/start` bleibt seit Runde 16 Administrator) schon vor A17. Wer ohne die Seite per WebSocket aufruft, kann sie dann als Nicht-Administrator benutzen, auch ohne Panel. Das ist bei „alle HA-Benutzer“ gewollt (Runde 6); die Schutzregeln 10.3 gelten ab A1. Die neue Seite läuft bis zur Abnahme parallel unter `/tobibox-neu` (nur Administratoren), die alte unter `/tobibox` bleibt.
3. **Panel für alle sichtbar** (nach A17): HA liefert die Seite nur Benutzern aus, die das Panel sehen dürfen; der Eintrag in der Seitenleiste ist je Benutzer ausblendbar. Das ist **nur Komfort**. Wer die Adresse `/tobibox` kennt, kommt hin; dafür sorgt allein das Backend.
   Das JavaScript unter `/tobibox_static/` ist schon heute ohne Anmeldung abrufbar und enthält keine Geheimnisse (und darf nie welche enthalten).
4. **Seite blendet „Technik“ nur für Administratoren ein** (`hass.user.is_admin`; kein neues Feld in `hello`, U18). Das ist ebenfalls Komfort, keine Sicherheit.
5. **Backend prüft je Befehl:** `befehl(..., recht="lesen" | "alltag" | "admin")`: `lesen` und `alltag` ohne Dekorator (nur angemeldet), `admin` mit `websocket_api.require_admin`; Zusatzprüfungen im Befehl (10.3) werfen `unauthorized`.
   HTTP: Upload und Cover ohne `@require_admin`, `request["hass_user"]` bleibt gesetzt.
6. **Kreis der Benutzer:** **Alle HA-Benutzer** (Entscheidung Tobias, Runde 6; Wandtablets und Gäste mit Konto sind bewusst eingeschlossen). Die in U3 vorgeschlagene Benutzerliste in den Optionen wird nicht gebaut, der Schutz in 10.3 gleicht es aus;
   sie bleibt eine kleine spätere Erweiterung, falls ein Konto doch ausgeschlossen werden soll.

### 10.2 Befehle nach Stufe (Nr. aus Vertrag W)

| Stufe | Befehle |
|---|---|
| **lesen** (alle) | 1 `hello`, 2 `subscribe`, 3 `serien/list` (erweitert), 4 `serie/get`, 10 `papierkorb/list`, 13 `neue_tobies/list`, 15 `zuordnung/list`, 21 `boxen/list` (ohne `ereignisse`), 29 `eingang/list`, 34 `konfig/get`, 35 `einstellungen/get`, neu `folgen/list`, HTTP-Cover (GET), **neu in Rev. 3:** HTTP-Audio (GET, angemeldet oder signierter Pfad), `hoerstelle/get`, `hoerstelle/liste` (nur die eigene Hörstelle; **Rev. 5:** `hoerstelle/*` einheitlich: `get` und `liste` lesen, `set` Alltag, G20) |
| **alltag** (alle angemeldeten Benutzer) | 16 `zuordnung/set` (inkl. Name), 17 `zuordnung/remove`, 14 `neue_tobies/verwerfen`, 6 `serie/rename`, 25 `folge/rename`, 28 `einsortierung/bestaetigen`, 9 `medien/pruefen`, 30 `eingang/sortieren` (**ohne** `sofort`), 36 `einstellungen/set` (ohne Zeitzone und Lesezeichen-Tage), neu `serie/art_setzen`, HTTP-Upload, HTTP-Cover (POST, DELETE `eigen`), **neu in Rev. 3:** `hoerstelle/set` (nur die eigene), **neu in Rev. 4:** `einsortierung/neu` („Anders einsortieren“; nur für „bitte ansehen“ oder jünger als 24 Stunden, 10.3; Upload-Felder `ziel`, `art`, `name`, `gruppe_anzahl` ohne Recht über den normalen Upload hinaus), **neu in Rev. 5:** `audio/bereit` (liefert den Zustand und den signierten Pfad; darf die Hörkopie anstoßen, höchstens eine vorgezogene Datei je Benutzer, 11.4.7), Stufe B: `reinhoer/loeschen` (nur die eigenen Daten; alle nur Admin, siehe admin-Zeile),
  **8 `folge/delete`, 24 `serie/delete`, 26 `folge/verschieben`** (neu in Rev. 2: nur in den Papierkorb, nichts endgültig; **Rev. 5:** Ziel „Überraschungs-Serie“ nur für Administratoren, G23) |
| **admin** | 5 `serie/create`, **18 `lernmodus/start`, 19 `lernmodus/antwort`, 20 `lernmodus/abbrechen`** (seit Runde 16, X13a: wieder Administrator; Vertragsbedarf in 5.13), 27 `serien/zusammenfuehren`, **7 `folgen/order`** („Reihenfolge ändern“, Rev. 5: in der Tabelle ergänzt, G20), 11 `papierkorb/restore`, **12 `papierkorb/empty`**, **33 `eingang/entfernen`**, 22 `box/sync`, 23 `liste/neu_ausrollen`, 32 `konfig/aus_export`, **31 `konfig/export_lesen`** (U26), `boxen/list`-Feld `ereignisse`, `eingang/sortieren` mit `sofort`, `einstellungen/set` für Zeitzone und Lesezeichen-Tage, neu `cover/neu_suchen`, **neu in Rev. 4:** `hoerkopie/neu_erzeugen`, **neu in Rev. 5:** `papierkorb/restore_letzte_stunde`, Stufe B: `reinhoer/loeschen` mit `alle` (alle Reinhör-Daten), später Update |

**Reinhören (Rev. 3):** erlaubt für **alle HA-Benutzer** (Entscheidung Runde 7). Hörstellen sind **nur die eigenen** (die Kennung kommt aus der Verbindung, nie aus der Eingabe; auch Administratoren sehen keine fremden). Die Audio-Ansicht verlangt Anmeldung oder eine gültige Signatur.
Der HA-Befehl `auth/sign_path` (nicht unser Befehl) darf jeder angemeldete Benutzer aufrufen; die Signatur trägt seine Identität und gibt ihm **keine Rechte, die er nicht ohnehin hat**. Mengen: höchstens 6 offene Audio-Verbindungen (nicht „Streams“, G5) und 6 Wiedergabe-Starts (`audio/bereit`) je Minute und Benutzer; `hoerstelle/set` wird gesammelt (11.4.5).
**Reinhör-Daten (Stufe B, Rev. 4a, Frage 23; Rev. 5 Auswahl `wer`):** **für alle HA-Benutzer lesbar.** `gehoert/zusammenfassung` ist `lesen`; `wer` (`alle`, `box:<id>`, `benutzer:<id>`) wählt die Quelle. Löschen: `reinhoer/loeschen` ohne `alle` ist `alltag` und löscht nur die eigenen Daten; `alle` ist nur für Administratoren (12.4). Die Hörstelle bleibt nur die eigene (Frage 16).

**Neu (Runde 12/13, Vorschlag; Verträge offen):** `warteschlange/set`, `warteschlange/list`, `warteschlange/abbrechen` = **alltag** (5.13); `playlist/create`, `playlist/rename`, `playlist/eintraege_hinzufuegen`, `playlist/eintraege_setzen`, `playlist/delete` = **alltag** (Stufe C; Löschen in den Papierkorb wie bei Serien, 13.2). `lernmodus/*` bleibt im Vertrag, die Alltagsseite ruft ihn nicht mehr auf; **Rückstufung auf Administrator entschieden (X13a, Runde 16; Vertragsbedarf für A0-Q in 5.13).**

Begründung (ehrlich, U2): „alltag“ sind Dinge, die die Partnerin selbst tun soll (Brainstorm, Runde 6). Endgültig zerstörbar sind nur `papierkorb/empty` und `eingang/entfernen`; sie bleiben Admin.
Die Zuordnungsliste ist dagegen **beschädigbar** (`remove` in einer Schleife), darum der Schutz in 10.3. „Lesen bleibt für alle“ ist bewusst, mit Ausnahme der beiden Befehle, die nur Tobias braucht (Liste im Detail, rohe Box-Meldungen).

### 10.3 Schutz gegen Fehlbedienung (U2, U3, U10, U17, Runde 6)

Gilt im Befehl für Nicht-Administratoren (Administratoren unverändert):

* **`zuordnung/remove` nur mit `erwartet_ziel`** (die Seite sendet es immer; schützt vor Doppeltipp und zweitem Fenster). Stimmt es nicht: `zuordnung_geaendert`. `zuordnung/set` mit `ueberschreiben=true` ebenso nur mit `erwartet_ziel`.
* **`zuordnung/set` nur für bekannte Kennungen:** die Kennung steht in `neue_tobies`, ist Ergebnis eines Lernmodus oder schon zugeordnet; sonst `kennung_ungueltig`. Die Seite hat keine Eingabe für Kennungen (die ist in „Technik“).
* **Mengen:** höchstens 30 Änderungen der Liste (`zuordnung/*`, `einstellungen/set`) je Minute und Benutzer, höchstens 20 Papierkorb-Aktionen je 10 Minuten, höchstens **16 GiB Upload je Stunde und Benutzer** (Rev. 5: bei 2 GiB je Datei ließen 4 GiB nur zwei Hörbücher zu, 5.6a), höchstens 20 Cover-Uploads je Stunde und Benutzer (G7). Darüber `zu_viele_aenderungen`.
  Die Liste bleibt unter ihrer Grenze (`KONFIG_MAX_BYTES` 256 KiB), weil Kennungen nur bekannt oder gemeldet sein dürfen.
* **Frühere Stände der Liste:** die Integration behält die **letzten 10 Stände** als `export/config.<n>.json` (zusätzlich zum bisherigen Export). „Technik → Liste → Frühere Stände ansehen“ zeigt sie, „Aus Stand wiederherstellen“ geht wie `konfig/aus_export`. Das ist die Sicherung gegen Fehler mit Folgen für alle.
* **`eingang/sortieren`:** ohne `sofort` (U10). Die Ruhezeit schützt halb kopierte Dateien.
* **`einstellungen/set` (U17):** Das Backend **ignoriert** `leise_zeiten.zeitzone` im Objekt und nimmt den gespeicherten Wert (kein irreführendes `unauthorized`); nur `lesezeichen_tage` bleibt Admin (die Seite sendet es nie). Neues optionales Eingabefeld `erwartet_revision`:
  stimmt es nicht, Fehler `stand_veraltet`; die Seite lädt neu (so überschreiben sich zwei Eltern an zwei Geräten nicht still).
* **Papierkorb für Alltag (Rev. 5, G8):** Löschen mit Tobies verlangt wie bisher `tobies_bestaetigt` (Rückfrage mit Namen). „Rückgängig“ gibt es für das Löschen nicht (Wiederherstellen ist Admin); die Rückfrage sagt es: „Der Administrator bekommt eine Mitteilung und kann es zurückholen.“ (Frage 7.) Dazu drei kleine Dinge, **ohne** Tageslimit (Entscheidung Runde 10): (a) legt ein **Nicht-Administrator** einen Eintrag mit Tobies oder mehr als 3 Einträge innerhalb einer Stunde in den Papierkorb, erzeugt die Integration eine **persistente Mitteilung** für Administratoren („Person B hat 4 Einträge in den Papierkorb gelegt. Du kannst sie in Technik zurückholen.“); (b) jede Papierkorb-Aktion schreibt eine **Protokollzeile** „Benutzer, Zeit, Eintrag“ (die Upload-Ereignisse tragen `nutzer_id` schon); (c) „Technik → Papierkorb → **Letzte Stunde zurückholen**“ (`papierkorb/restore_letzte_stunde`, Admin) holt alles zurück, was in der letzten Stunde hineinkam. Die Box-Bremse `zu_viele_loeschungen` (über 20 % im Sync) bleibt; sie hilft nur halb, weil danach kein Sync mehr läuft, darum (c).
* **`einsortierung/neu` (Rev. 5, G9):** Das Backend nimmt nur Einträge aus `eingang/list`, die `pruefen=true` sind **oder** höchstens 24 Stunden alt; sonst `neu_einsortieren_nicht_moeglich`. Es zählt als Papierkorb-Aktion (Menge oben), die **Ruhezeit** gilt wie beim Einsortieren, und es prüft vor dem Zurückholen, dass an den Folgen nichts geändert wurde (nicht umbenannt, nicht verschoben, kein Tobie, `art_quelle` nicht `manuell`, Cover nicht eigen, nicht angehört: dafür liest es **intern** fremde Hörstellen, zeigt sie aber nirgends). Die vollständige Liste der „etwas geändert“-Prüfungen steht im Vertrag (A0).
* **Überraschungs-Serie (Rev. 5, G23):** `folge/verschieben` mit der Überraschungs-Serie als Ziel antwortet Nicht-Administratoren `ziel_ungueltig`; die Serie bestimmt, was die Box beim unbekannten Tobie spielt (kurze Töne). Test in A1.
* **Vorziehen von Hörkopien:** je Benutzer höchstens **eine** vorgezogene Datei gleichzeitig (11.4.7).

## 11. Änderungen an Vertrag W, Datenmodell und Sync (Stufe A)

### 11.1 Wie der Vertrag geändert wird (U18)

Alles Folgende ist **additiv** (neue Felder, Befehle, Fähigkeiten, Codes, optionale Eingaben), **mit einer Ausnahme**: Die Lockerung der Rechte ändert das Verhalten bestehender Befehle (bisher `unauthorized`, jetzt Erfolg).
Im Vertragskopf steht dafür ein Eintrag „**Änderung 12.11. (HA-Oberfläche, Stufe A):** …“ in der Form der bisherigen Änderungen (Datum, kein „Version 1.2“-Zähler; `v` bleibt 1). **Abschnitt 2.1 („Wer darf was“) wird vollständig ersetzt** (nicht ergänzt), der Satz W-19 (Upload nur für Administratoren) entfällt,
der Prüfabschnitt „gegen die HA-API“ nennt `async_register_admin_service`. Weitere Vertragsstellen, die sich ändern: **Abschnitt 8** (Zeile „Größe einer Audiodatei“: 2 GiB; Reserve; Nabu-Casa-Abnahme mit vier Größen, 5.6a), **5.1** (Textfelder: `name` bis 400 Bytes, `gruppe_anzahl`; die Zeile „höchstens 64 Zeichen“ gilt für die übrigen Felder, G31) und **11.10** (nur wenn A0 es entscheidet; Rev. 5 lässt 11.10 unverändert, G11).
**Regel für Fähigkeiten (Rev. 5, G22):** Eine Fähigkeit gibt es **nur** (1) für etwas, das von der Umgebung abhängt (`ffmpeg`: `cover`, `hoerkopie`), oder (2) für **neue Eingabefelder und Eingabewerte**, die ein älteres Backend (neue JavaScript-Dateien werden sofort ausgeliefert, Python erst nach dem Neustart von HA) streng ablehnen würde. Reine neue Ausgabefelder brauchen keine: die Seite zeigt sie, wenn sie da sind. Danach:
* **`cover`** (Foto-Upload, Cover aus Tags; nur mit `ffmpeg` für das Lesen aus Tags).
* **`bibliothek`**: `serien/list` mit `art`, `text`, `filter` (**einschließlich der Werte `sammlung` und `einzeln`**), `sortierung`, `limit`, `offset`; Befehl `folgen/list`; **`erwartet_revision`** bei `einstellungen/set`; **`text` und `neu`** bei `zuordnung/list` (G22a, G22b).
* **`reinhoeren`**: Audio-Ansicht, Befehl `audio/bereit`, `hoerstelle/*` (Eingaben). Ohne sie zeigt die Seite keinen Reinhören-Knopf.
* **`einsortier_wunsch`**: Upload-Felder `ziel`, `art`, `name`, `gruppe_anzahl`; Befehl `einsortierung/neu`. Ohne sie zeigt die Seite das alte, einfache Hochladen ohne Wahl.
* **`hoerkopie`**: hängt von `ffmpeg` ab (Audio-Ansicht liefert Kopien, Zustand in `audio/bereit`, Befehl `hoerkopie/neu_erzeugen`). Ohne sie bleibt es bei der Prüfung mit `canPlayType`.
* **`kapitel` entfällt** (Rev. 5): Das Feld `kapitel` ist ein Ausgabefeld; fehlt es, zeigt die Seite keine Liste. In Stufe B kommt `gehoert_reinhoeren` dazu (12.5).
`box_anzeigenamen` und `rechte_stufen` entfallen (Feld da bzw. Seite und Backend liegen im selben Paket). Fehlt eine Fähigkeit, die die Seite braucht, zeigt sie **eine** Antwort: „Die Seite ist veraltet. Bitte lade sie neu.“ (6). Eine **alte Seite** im Zwischenspeicher kennt die Befehle nicht, schickt sie nicht und blendet nach `darf_schreiben` (= Administrator) aus: harmlos.

### 11.2 Wunschliste im Einzelnen

**V-1 Cover (Fähigkeit `cover`)**

* *Serie-Kurzform* bekommt: `cover_stand` (string, 8 Zeichen `[0-9a-f]`, Fingerabdruck der angezeigten Datei) oder `null` (kein Cover), `cover_quelle` (`eigen`, `auto`, `null`).
  **Kein signiertes `cover_url`** (Review, Prüfpunkt 4): Die Adresse ist fest `/api/tobibox/cover/<serie_id>`; die Seite lädt das Bild mit `hass.fetchWithAuth` (Bearer), hält es als `blob:` und nimmt `cover_stand` als Schlüssel des Zwischenspeichers. Keine Signatur, kein Ablauf, kein Flackern.
  Ereignisse (`medien`, `snapshot`) tragen kein Cover, nur Antworten auf Befehle.
* **`GET /api/tobibox/cover/<serie_id>?groesse=klein|gross`:** `image/jpeg`, `klein` 192 px (≈ 15 KiB), `gross` 512 px (≤ 150 KiB), `ETag` = `cover_stand`, `Cache-Control: private, max-age=86400`. Recht: lesen. 404 `cover_nicht_gefunden`.
* **`POST /api/tobibox/cover/<serie_id>`:** Rumpf `image/jpeg`, höchstens 3 MiB, Quadrat bis auf 2 %, höchstens 2 048 px. Das Backend liest den Rumpf **in Blöcken mit Zähler** (3 MiB gelten auch ohne `Content-Length`), prüft die Kopfbytes, liest **Maße und Pixelzahl aus dem Kopf, bevor ein Pixel dekodiert wird**, dekodiert erst dann, rechnet auf 512 und 192 px und speichert `cover-eigen.jpg` (nie das Original); dieselbe Funktion `cover_pruefen_und_skalieren` prüft das aus Tags gezogene Bild (5.5, G7). Höchstens 20 Cover je Stunde und Benutzer. Recht: **Alltag**. Fehler `cover_ungueltig`, `datei_zu_gross`, `serie_nicht_gefunden`.
* **`DELETE /api/tobibox/cover/<serie_id>?quelle=eigen`:** zurück zum automatischen Cover. Alltag.
* **Befehl `cover/neu_suchen`** (`serie_id` optional = alle): löscht `cover.jpg` und die Marke `cover_suche`, startet die Suche neu. **Admin.** Berührt nie `cover-eigen.jpg`.
* *Woher das automatische Bild kommt*, Marke, Zeitgrenzen, kein Dauer-Scan: 5.5. Fähigkeit `cover` wird nur gemeldet, wenn `ffmpeg` da ist (für das Lesen aus Tags; der Foto-Upload braucht es nicht). Skalieren macht **Pillow**; `manifest.json` bekommt `"requirements": ["Pillow"]` (die Annahme „kommt aus `image_upload` mit“ ist nicht belegt, G7d).

**V-2 Art, Suche, Filter, Sortieren, Blättern (Fähigkeit `bibliothek`)**

* *Serie-Kurzform* bekommt `art` (`hoerspiel`, `hoerbuch`, `musik`, `geschichte`), `art_quelle` (`tags`, `geraten`, `manuell`) und **`kapitel_anzahl`** (Summe der Kapitel, für „Hörbuch · 14 Kapitel“; G16b). **Schon vorhanden und unverändert benutzt (G16a):** `anzahl_folgen`, `anzahl_tobies` (zählt `serie` **und** `folge`) und `angelegt_am`; Rev. 4 führte dafür zweite Namen (`folgen_anzahl`, `tobies`) ein, die entfallen. Fehlt `art` in einer alten `serie.json`, gilt `hoerspiel`.
* **`serien/list` bekommt optionale Eingaben:** `art`, `text` (2 bis 100 Zeichen; sucht im Namen des Eintrags und, mit `auch_folgen`, in Folgentiteln), `filter` (Liste aus `ohne_tobie`, `neu`, `pruefen`), `sortierung` (`name`, `neu`, neu in Rev. 3: `angehoert` = zuletzt angehört vom Anfragenden, nur mit Fähigkeit `reinhoeren`), `limit` (1 bis 200), `offset`. Ausgabe bekommt `gesamt` (nach Filter) und `weitere`.
  **Fehlt `limit`, gilt das bisherige Verhalten** (alle, höchstens 200, dazu `weitere`); so bleibt die alte Seite gültig. Das 64-KiB-Limit einer Nachricht (Vertrag, Größen) bleibt gewahrt, weil die neue Seite blättert.
* **Neuer Befehl `folgen/list`** (lesen): Eingaben `art`, `text`, `filter`, `sortierung` (`titel`, `neu`), `limit` (1 bis 100, Vorgabe 60), `offset`. Ausgabe: `folgen` = Liste aus `serie_id`, `serie_name`, `art`, `folge` (Name), `anzeige`, `nummer`, `kapitel`, `groesse_mb`, `tobies` (direkt auf die Folge), `serie_hat_tobie`; dazu `gesamt`, `weitere`.
* **`zuordnung/list`** bekommt `text` (Tobie-Name oder Ziel) und die Sortierung `neu` zuerst (V-5).
* **Neuer Befehl `serie/art_setzen`** (Alltag): `serie_id`, `art`; setzt `art_quelle="manuell"`.
* **Art beim Einsortieren aus Tags vorschlagen** (Vertrag Abschnitt 11): Genre-Tag mit „Hörbuch“/„Audiobook“/„Spoken“ oder Endung `.m4b` → `hoerbuch`; Genre „Hörspiel“/„Audio Drama“/„Radio Play“ → `hoerspiel`; Musikgenre (Pop, Kinderlieder, Children’s Music, Klassik, Schlaflied …) oder viele kurze Tracks (Mittel unter 8 Minuten) mit Album-Interpret → `musik`;
  Märchen/Geschichten/Einzeldatei unter 30 Minuten ohne Album → `geschichte`; sonst `hoerspiel` mit `art_quelle="geraten"` und Grund `art_geraten` in `pruefen_gruende` („Die Art ist geraten. Stimmt das?“). Ein von Hand gesetztes `art` (`manuell`) wird **nie** überschrieben.
* *Index:* Die Integration hält Eintrags- und Folgennamen (normalisiert) im Speicher; Aufbau beim Start, Aktualisierung bei `serien_geaendert`. Test: 600 Einträge, 2 000 Folgen, Suche unter 200 ms.

**V-6 Reinhören (Fähigkeit `reinhoeren`, neu in Rev. 3; Rev. 5 überarbeitet)**

* **Neuer Befehl `audio/bereit`** (Recht alltag, G3, G4). Eingabe: `serie_id`, `folge`, optional `track`, optional `vorbereiten` (Vorgabe `true`: darf die Hörkopie anstoßen, 11.4.7). Ausgabe: `zustand` = `bereit`, `wird_vorbereitet` oder `fehlt`. Bei `bereit`: `pfad` (der **signierte** Pfad `/api/tobibox/audio/…?authSig=…`, vom Backend mit `async_sign_path` für die Anmeldung der Verbindung gebildet, **24 Stunden** gültig) und `quelle` (`original` oder `kopie`). Bei `wird_vorbereitet`: `warte_s` (Schätzung) und `position` in der Schlange. Bei `fehlt`: `grund` (`zu_lang`, `zeitgrenze`, `unplausibel`, `kodieren_fehlgeschlagen`, `medien_nicht_erreichbar`, `ffmpeg_fehlt`). Fehler: `folge_nicht_gefunden`, `hoerkopie_warteschlange_voll`, `zu_viele_aenderungen`. **Die Seite fragt vor jedem Start**, nie erst aus dem Fehler des `<audio>`-Elements (11.4.1).
* **HTTP:** `GET /api/tobibox/audio/{serie_id}/{folge_id}` (optional `?track=<n>`), Recht lesen, signierter Pfad oder Anmeldung, Range-fähig; Fehler 404 `folge_nicht_gefunden`, 429 `zu_viele_streams`, 503 `medien_nicht_erreichbar`. Einzelheiten 11.4.1 und 11.4.2. **Rev. 4:** Die Ansicht liefert bei Bedarf die Hörkopie (V-9). Die Seite benutzt die HTTP-Fehler nur noch zur Diagnose.
* **Befehle (Recht nach Tabelle 10.2):** `hoerstelle/get` und `hoerstelle/liste` (lesen), `hoerstelle/set` (alltag), 11.4.5. Neuer Code `zu_viele_streams`.
* **Felder (additiv):** *Serie-Kurzform* `dauer_s`, `kapitel_anzahl`, `hoerstelle` (`anteil`, `rest_s`, `zeit`, `folge`; nur des Anfragenden, nur wenn angefangen); *Folge-Objekt* von `serie/get`: `dauer_s`, `spuren_s` (bei Ordner-Folgen), `hoerstelle` (`position_s`, `fertig`); `hello.grenzen`: `audio_verbindungen_je_benutzer` (6, vorher „audio_streams_je_benutzer“).
* **Ablage:** `dauer_s`, `spuren_s`, `kapitel`, `codecs` und `hoerkopie` liegen im Store `tobibox.medieninfo` (11.3), **nicht** in `serie.json` (G10). Dasselbe gilt für die Hörstelle (`tobibox.hoerstellen`).

**V-7 Hochladen mit Wunsch und „Anders einsortieren“ (Fähigkeit `einsortier_wunsch`, neu in Rev. 4)**

* **Upload** (`POST /api/tobibox/upload`, Vertrag W 5.1) bekommt **optionale** Felder, wie die vorhandenen als Text im Multipart, **vor** dem Teil `datei`: `ziel` (`auto` Vorgabe, `neu`, `ergaenzen`, `einzeln`; in Stufe C auch `playlist`), `art` (`hoerspiel`, `hoerbuch`, `musik`, `geschichte`), `name` (1 bis 100 Zeichen, nach den Namensregeln aus Vertrag W Abschnitt 12 bereinigt) und **`gruppe_anzahl`** (2 bis 200: die Zahl der Dateien dieser `gruppe`, Rev. 5, G2). Die bestehenden Felder `upload_id`, `serie_id` und `gruppe` bleiben. **Lesegrenze (G31):** `_lies_feld` liest heute 200 Bytes; `name` hat bis 100 Zeichen, mit Umlauten oder Emojis bis 400 Bytes und würde mitten im Zeichen abgeschnitten. Neu: `name` bis **400 Bytes**, bei Überlauf `wunsch_ungueltig`; Vertrag W 5.1 sagt dann „höchstens 64 Zeichen, `name` höchstens 100 Zeichen (400 Bytes)“. Fehlt `ziel`, gilt `auto`: **genau das heutige Verhalten**. Eine alte Seite sendet nie etwas davon.
* **Wirkung** (Dateien mit gleicher `gruppe` gehören zusammen; der Wunsch gilt **vor** den Tags):

| `ziel` | Pflicht | Ergebnis |
|---|---|---|
| `auto` | – | wie heute (Vertrag W 11.3 bis 11.5), dazu der Art-Vorschlag (V-2) |
| `neu` | `gruppe`, `gruppe_anzahl` (bei mehr als einer Datei), `art`, `name` | **eine neue Serie** `name`; wird **nie** in eine vorhandene gleichen Namens zusammengeführt (gibt es den Namen, heißt sie „… (2)“, Kennzeichen `serie_name_doppelt`). Die **Gruppierung folgt der Art**, nicht den Tags: `hoerbuch` = **alle** Dateien eine Folge (Folgen-Ordner, die Tracks sind die Kapitel; bei einer Datei die Datei selbst, zum Beispiel eine M4B), `hoerspiel`, `musik`, `geschichte` = **jede Datei eine Folge** (auch wenn alle dasselbe Album nennen). Reihenfolge nach Vertrag W 11.6 und 11.7 (Nummer, Disc und Track, natürliche Sortierung). `art_quelle="manuell"` |
| `ergaenzen` | `serie_id`, `gruppe`, `gruppe_anzahl` (bei mehr als einer Datei) | jede Datei eine **neue Folge** der vorhandenen Serie (Einfügeregel Vertrag W 11.6), nie ein Folgen-Ordner. Die Serie darf kein Einzeltitel sein (`wunsch_ungueltig`) |
| `einzeln` | `art` (Vorgabe `musik`) | **jede Datei eine neue Serie mit genau einer Folge und `einzeln: true`** (V-8); `name` = Titel dieser einen Datei (sonst Tag `title`, sonst Dateiname). Mehrere Dateien: je Datei ein eigener Upload mit eigenem `name`, ohne gemeinsame `gruppe` |
| `playlist` (Stufe C) | … | erst in Stufe C (13): die Dateien werden Einzeltitel, die Playlist verweist darauf |

* **Gruppe bleibt zusammen (G2, belegt am Code):** `plane_nach_upload` sortiert 20 Sekunden (`UPLOAD_SAMMELZEIT_S`) nach dem **letzten** Upload-Abschluss, und Upload-Einträge gelten sofort als bereit (`_ist_bereit`). Dauert eine Datei vom Handy länger als 20 Sekunden (500-MiB-Kapitel: Minuten), wären die ersten Dateien schon einsortiert, die späteren eine „Nachlieferung“, und weil `neu` **nie zusammenführt**, entstünde „… (2)“. Darum: Hat ein Wunsch `gruppe_anzahl` N, **wartet der Eingang, bis N Dateien der Gruppe da sind**, oder 30 Minuten Ruhe vergangen sind (dann `teilweise` mit Hinweis `gruppe_unvollstaendig`, einsortiert wird, was da ist). Ohne `gruppe_anzahl` ist `neu`/`ergaenzen` mit mehreren Dateien `wunsch_ungueltig`. Der Wunsch wird je Gruppe einmal gespeichert (steckt im persistenten `vorgaben`). Tests in A3d: drei Dateien im Abstand von 60 Sekunden → **eine** Folge mit 3 Tracks; die letzte Datei fehlt → `teilweise` nach 30 Minuten.
* **Fehler:** `wunsch_ungueltig` (400) bei fehlenden Pflichtfeldern oder unpassender Mischung; `serie_nicht_gefunden` wie bisher. Die Prüfung der Datei (Format, Kopierschutz, Probedekodierung) bleibt unverändert (Vertrag W 5.4).
* **Anzeige:** `eingang/list`-Einträge und das Ereignis `eingang` tragen zusätzlich `wunsch` (`ziel`, `art`), damit die Seite „Daraus ist geworden: …“ schreiben kann.
* **Neuer Befehl `einsortierung/neu`** (**Alltag**; „Anders einsortieren“ für Einträge aus dem NAS-Eingang und für Uploads, die schon einsortiert wurden): Eingabe `eintrag_id` (aus `eingang/list`), `ziel`, `art`, `name`, `serie_id` (wie oben). Das Backend holt die Folgen, die dieser Eintrag erzeugt hat, aus den Medien in den Eingang zurück und sortiert sie mit dem Wunsch neu ein. **Nur** für Einträge mit `pruefen=true` **oder** höchstens 24 Stunden alt (G9, 10.3). Nur möglich, solange an diesen Folgen **nichts** geändert wurde (nicht umbenannt, nicht verschoben, kein Tobie darauf, nicht angehört, `art_quelle` nicht `manuell`, kein eigenes Cover); sonst Fehler `neu_einsortieren_nicht_moeglich`. Die Serien, die der Eintrag neu angelegt hatte, verschwinden mit ihm (Papierkorb). **Machbarkeit zu prüfen in A3d:** Vertrag W kennt heute keinen Weg Medien → Eingang. Rückfall: nur Papierkorb und neu hochladen (Frage 25).

**V-8 Einzeltitel und Kapitel (Fähigkeiten `einsortier_wunsch`, `kapitel`; neu in Rev. 4)**

* *Serie-Kurzform* bekommt `einzeln` (bool; fehlt = `false`). `serien/list`: `filter` kennt zusätzlich `sammlung` (nur Einträge, die kein Einzeltitel sind) und `einzeln` (nur Einzeltitel). `folgen/list` trägt je Zeile `serie_einzeln`. `anzahl_folgen` ist bei einem Einzeltitel 1; die Seite zeigt sie nie („Lied · einzeln · 1:06“).
* Ein Einzeltitel ist **eine normale Serie** (eigene ID, Ordner, `serie.json`, Cover, Papierkorb, Umbenennen, `serie/art_setzen`). Neue Folgen kommen nicht hinein: `ergaenzen` und `folge/verschieben` mit einem Einzeltitel als Ziel antworten `wunsch_ungueltig` bzw. `ziel_ungueltig`; `serien/zusammenfuehren` (Admin) darf ihn als Quelle, nicht als Ziel benutzen.
* **Kapitel:** *Folge-Objekt* von `serie/get` bekommt `kapitel` = Liste aus `titel`, `start_s` und, bei Ordner-Folgen, `track` (0-basiert); nur wenn es mindestens zwei gibt. Quelle und Regeln: 11.4.8. Die Hörstelle bleibt, wie sie ist (`track`, `position_s`). Die Kapitel liegen im Store `tobibox.medieninfo` (11.3), nicht in `serie.json`.

**V-9 Hörkopie (Fähigkeit `hoerkopie`; neu in Rev. 4, Rev. 5 mit Grenzen)**

* Die Audio-Ansicht (V-6) liefert die **Hörkopie**, wenn die Folge eine braucht und sie fertig ist, sonst das Original. Antwortkopf `X-Tobibox-Quelle: kopie` oder `original` (zum Prüfen). Die Seite erfährt den Zustand vorher über `audio/bereit` (V-6); der HTTP-Fehler 503 `hoerkopie_wartet` mit `Retry-After: 60` bleibt nur als Rückfall für Aufrufer, die `audio/bereit` nicht benutzt haben. Ohne Kopie-Pflicht ändert sich nichts.
* *Folge-Objekt* von `serie/get`: `hoerkopie` = `original` (braucht keine), `nicht_angelegt` (Bestand, noch nicht angefordert), `wartet`, `fertig`, `fehler` (mit `grund`). `hello.grenzen`: `hoerkopie_kbit` (96), `hoerkopie_dauer_max_s` (Dauerdeckel).
* **Befehl `hoerkopie/neu_erzeugen`** (**Admin**): `serie_id` optional (fehlt = alle mit Zustand `fehler`); löscht Kopie und Marke und stellt die Folge neu in die Warteschlange.
* Grenzen, Speicherort, Zeitpunkt, Bedarf und Fehlerfall: 11.4.7.

**V-3 Anzeigenamen der Boxen** (Feld da, keine Fähigkeit): Optionen der Integration (`config_flow.py`, `strings.json`, `translations/de.json`) bekommen **ein Textfeld** „Namen der Boxen: `box1=Box 1, box2=Box 2`“ (U21c; gleiche Prüfung wie `parse_boxen`, höchstens 40 Zeichen je Name, Hinweis „ohne das Wort Box“). `boxen/list` trägt `anzeige` (nie `null`: Name aus den Optionen, sonst `anzeigename` der Discovery, sonst der Box-Name);
`hello.box_anzeigen`. Im Repo steht kein echter Name (CLAUDE.md). Die Seite zeigt nur `anzeige`.

**V-4 Rechte (Ausnahme zur Additivität)**: Abschnitt 10; Vertrag 2.1 ersetzen, W-19 streichen. Neue Codes `zu_viele_aenderungen`; neue Eingabe `erwartet_revision` bei `einstellungen/set`; `erwartet_ziel` bei `zuordnung/remove` wird für Nicht-Administratoren Pflicht.

**V-5 Kleinigkeiten, die die Seite braucht (U4, U9, U13)**
* `eingang/list`: Feld `quelle` (`upload` oder `nas`) **fest** im Vertrag (die Integration weiß es: `registriere_upload`).
* `zuordnung/list` und `config.json` `zuordnungen.<uid>`: optionales Feld `angelegt_am` (Zeitstempel; die Box ignoriert es, `data-model.md` 1.4; +30 Byte je Zuordnung).
* `neue_tobies`-Ereignis „aufgelegt“ (wenn die Box die Kennung auch beim Auflegen eines **bekannten** Tobies meldet): Das Feld gibt es heute vermutlich nicht; ohne es entfällt nur „Auflegen zum Finden“ (5.7). Bei Bedarf additiv `status.letzte_kennung`.

### 11.3 Datenmodell und Sync (U8)

**Rev. 5 trennt zwei Dinge (G10).** `serie.json` bekommt nur Felder, die **ein Mensch** setzt. Alles, was ein Hintergrundlauf berechnet und jederzeit neu berechnen kann, liegt im HA-`Store` **`tobibox.medieninfo`** (Schlüssel `serie_id`, dann Folge, `.storage/`, `async_delay_save`). Grund: Der Fingerabdruck `stand` einer Serie (`media.py`, Eigenschaft `stand`) rechnet heute über `name`, `folgen` **und das ganze `folgen_info`**. Lägen Dauer, Codec, Kapitel und Hörkopie-Zustand dort, änderte jeder Hintergrundlauf den `stand`, und die Partnerin bekäme beim Umbenennen „Jemand hat gerade etwas anderes geändert“ (`stand_veraltet`), ohne dass jemand etwas getan hat. Außerdem schriebe jeder Zustandswechsel `serie.json` auf das NAS, und die Boxen synchronisierten es mit. Der `stand` rechnet künftig **nur** über Name, Folgenliste und die von Menschen gesetzten `folgen_info`-Felder `anzeige`, `nummer`, `datum`, `pruefen`; Test in A3b: ein Hintergrundlauf ändert den `stand` nicht.

`data-model.md` Abschnitt 5 (`serie.json`), additiv, die Box ignoriert alles (1.4); **nur von Menschen gesetzte Felder**:

| Feld | Typ | Bedeutung |
|---|---|---|
| `art` | `"hoerspiel"`, `"hoerbuch"`, `"musik"`, `"geschichte"` | Art des Eintrags; fehlt = `hoerspiel` |
| `art_quelle` | `"tags"`, `"geraten"`, `"manuell"` | woher `art` kommt; `manuell` wird nie überschrieben |
| `einzeln` | bool | **(Rev. 4)** Einzeltitel: genau eine Folge, steht für sich, keine neuen Folgen; fehlt = `false` |

Store **`tobibox.medieninfo`** (HA, nicht synchronisiert, nicht in `stand`, bei Verlust neu berechenbar):

| Feld | Typ | Bedeutung |
|---|---|---|
| `<serie_id>.folgen.<name>.dauer_s` | Zahl (Sekunden), höchstens der Dauerdeckel | Länge der Folge (Rev. 3, 11.4.4); fehlt bis zum Nachholen; **über dem Deckel wird nichts gespeichert** (G1a) |
| `….spuren_s` | Liste von Zahlen | bei Ordner-Folgen die Länge jedes Tracks, in Folgenreihenfolge |
| `….kapitel` | Liste aus `{"titel": string, "start_s": Zahl, "track": int?}` | **(Rev. 4, 11.4.8)** Kapitel der Folge, aufsteigend nach `start_s`, höchstens 500, Titel höchstens 120 Zeichen; nur wenn mindestens zwei |
| `….codecs` | Liste von Strings, **je Track** (bei einer Datei ein Eintrag) | **(Rev. 5, G30)** Audiocodec aus `ffprobe` (`mp3`, `aac`, `vorbis`, `opus`, `flac`, `alac`, `pcm_s16le` …); die Regel `braucht_hoerkopie(codec)` entscheidet **je Track** (11.4.7); eine Ordner-Folge darf MP3 und FLAC mischen |
| `….hoerkopie` | object `{"zustand", "zeit", "grund"?}`; `zustand` ist `"nicht_angelegt"`, `"wartet"`, `"fertig"` oder `"fehler"` | **(Rev. 4, 5)** Stand der Hörkopie der Folge (fertig, wenn alle nötigen Tracks fertig sind); fehlt = nicht nötig oder noch nicht geprüft |
| `<serie_id>.cover_suche` | object `{"ergebnis": "tags"\|"datei"\|"keine", "zeit": <Zeitstempel>}` | Marke „schon gesucht“ (U5) |

**Reservierte Dateinamen** im Serien-Ordner (neu, additiv; die Bibliothek der Box liest nur Audioendungen und ignoriert sie schon): `cover.jpg` (automatisch), `cover-eigen.jpg` (Foto, hat Vorrang); als **Quelle** gelesen, nie geschrieben: `folder.jpg`, `cover.png`. Beim **Zusammenführen** übernimmt die Ziel-Serie das Cover der Quelle, wenn sie selbst keines hat;
im **Papierkorb** wandern die Dateien mit dem Ordner; beim **Umbenennen** bleiben Ordnername und ID, also auch die Cover. Beim Einsortieren aus einem Eingangs-Ordner hat ein mitgeliefertes `cover.jpg`/`folder.jpg` Vorrang vor dem eingebetteten Bild: die Integration **kopiert** es (durch `cover_pruefen_und_skalieren`) als `cover.jpg` in den Serien-Ordner, die mitgelieferte Datei im Eingang geht danach **wie bisher** in den Papierkorb (Vertrag W 11.10, Test `test_reste_kommen_in_den_papierkorb_leere_ordner_werden_geloescht` bleibt unverändert; G11). Cover im Papierkorb sind also eine Kopie des Originals und mit dem Eintrag wiederherstellbar.

**Sync:** `box/src/tobibox/sync.py` nimmt zusätzlich `cover*.jpg`, `cover*.png` und `folder.jpg` aus (zu den Systemdateien und `_upload`, `_papierkorb`, `eingang`). Empfehlung aus dem Review, übernommen: Die Box hat kein Display; 500 Cover à 150 KiB wären 75 MB SD-Platz und Schreibvorgänge für nichts.
Test in `box/tests`: Sync mit Covern überträgt sie nicht. Tests in `homeassistant/tests` (A4, G11): Zusammenführen übernimmt das Cover der Quelle, Wiederherstellen aus dem Papierkorb bringt es mit, Umbenennen lässt es liegen. Das ist die **einzige Änderung am Box-Code in Stufe A**.

**Einzeltitel und Sync (Rev. 4):** Ein Einzeltitel ist ein Serien-Ordner mit einer Datei und einer `serie.json`; die Box liest ihn wie jede Serie und ignoriert `einzeln` (data-model 1.4). 300 einzelne Lieder sind 300 kleine Ordner: `rsync` braucht keine Sonderregel, das Verzeichnis wird etwas länger (eine zusätzliche `serie.json` je Lied, etwa 300 Byte). Hörkopien liegen **nicht** in `medien/` (11.4.7), also gibt es dort nichts auszunehmen: **die Box-Änderung in Stufe A bleibt allein der Cover-Ausschluss.**

Hinweis zum Sync: Die Box gleicht die **ganze** Bibliothek ab (`rsync --delete`). Bei ca. 200 Hörbüchern kann das mehr als 50 GB sein; der erste Abgleich dauert Stunden. Das ist keine Änderung der Oberfläche, aber Tobias sollte den freien Platz der Boxen (`speicher_frei`, „Technik“) im Blick haben (Frage 10).

#### 11.3.1 Wo lebt ein einzelnes Lied? Vergleich (Rev. 4)

Heute ist alles **Serie → Folgen** (`data-model.md` Abschnitt 5; ein Tobie zeigt auf `serie`, `folge` oder `aktion`). Ein Lied, das für sich steht, braucht einen Platz, ohne die Box zu ändern. Zwei Wege, beide ohne Vertragsbruch:

| | **A: eigene Serie mit einer Folge, Kennzeichen `einzeln`** (Empfehlung) | **B: Sammel-Serie je Art** („Einzelne Lieder“, „Einzelne Geschichten“) |
|---|---|---|
| Aufbau | Ordner `medien/<lied>/` mit `serie.json` (`einzeln: true`, `folgen: ["lied.mp3"]`) | ein Ordner `Einzelne Lieder` mit allen Liedern als Folgen (wie die heutige Serie `Einzelfolgen`, Vertrag W 11.5) |
| Anzeige | Eintrag mit eigenem Cover und Titel; „Lied · einzeln · 1:06“, **nicht** „Serie mit 1 Folge“ | ein Eintrag „Einzelne Lieder · 300 Lieder“; ein Lied findet man nur per Suche oder in der langen Folgenliste; **ein Cover für alle** |
| Tobie-Ziel | `folge` (siehe unten); ein Tobie für „Das Lied vom Mond“ | `folge` einer Folge der Sammel-Serie; **wird die Folge verschoben oder die Reihenfolge geändert, bleibt der Tobie nicht verlässlich** |
| Löschen, Umbenennen, Cover, Art | je Lied wie bei jedem Eintrag; Papierkorb nennt den Tobie | je Lied nur als „Folge“; Cover der ganzen Sammlung |
| Suche | Treffer in der Gruppe „Folgen und Lieder“ (Einträge ohne die Gruppe „Hörspiele, Bücher, Alben“) | Treffer in „Folgen und Lieder“ mit dem Hinweis „aus Einzelne Lieder“ |
| Sync und Box | 300 kleine Ordner, jede `serie.json` wird gelesen; die Box ist unverändert | ein Ordner; unverändert |
| Hörstelle (Weiterhören) | je Lied, wie sonst | je Folge der Sammlung, wie sonst |
| Nachteil | viele Einträge in der Bibliothek (Gegenmittel: Filter „Was zeigen“, Arten-Zeile); Aufnahme jedes Liedes kostet einen Ordner | Reiter und Zähler wirken wie **ein** Album; „Zuletzt hinzugefügt“ und „Neu“ zeigen immer nur die Sammlung; Cover fehlt; Tobie auf eine Folge, deren Sammlung wächst und umsortiert wird |
| Playlist (Stufe C) | Eintrag der Playlist = ein Einzeltitel (`serie`, `folge`) | Eintrag der Playlist = Folge der Sammlung |

**Empfehlung: A.** Sie ist die einfachste Lösung, die die Box nicht ändert und in der Oberfläche wie ein eigener Titel aussieht. **Folgen:**
* *Tobie-Ziel:* Die Seite speichert `ziel.typ = "folge"` (Serie des Einzeltitels, Folge `lied.mp3`), **nicht** `serie`: Kommt später doch eine Folge in diesen Ordner (etwa von Hand auf dem NAS), spielt der Tobie weiter nur sein Lied. Ein Tobie auf `serie` würde dann alles spielen. Die Box kennt beide Fälle schon (`data-model.md` 2).
* *Suche:* Einzeltitel stehen in der Gruppe „Folgen und Lieder“ (mit Abspiel- und Tobie-Knopf), nicht in „Hörspiele, Bücher, Alben“; sonst käme jedes Lied doppelt vor. Der Index führt sie als Serie **und** als Folge, die Seite filtert.
* *Sync:* siehe oben; kein Eingriff in `sync.py`.
* *Vertrag:* nur das additive Feld `einzeln` in `serie.json` und in der Kurzform, der Filter `sammlung`/`einzeln` und der Upload-Wunsch `einzeln` (V-7, V-8). Kein neuer `ziel.typ`, kein neues Boxen-Schema.
* *Ohne Wunsch* (`auto`) bleibt die heutige Regel: eine lose Datei ohne Tags landet in der Serie `Einzelfolgen`. Wer einen eigenen Eintrag will, wählt „Einzelne Folge oder einzelnes Lied“.
* *Rückbau:* Entfernt jemand das Kennzeichen von Hand (`einzeln` aus `serie.json`), ist es eine Serie mit einer Folge; nichts bricht. Ein Knopf dafür ist nicht vorgesehen.

### 11.4 Reinhören: Technik (neu in Rev. 3)

**Ergebnis der Prüfung vorab (12.11.):** Die Quellen von Home Assistant (Zweig `dev`, geholt am 12.11.) und von aiohttp sind durchgesehen; Range-Anfragen wurden mit einem kleinen Test belegt. Was **belegt** und was **zu prüfen** ist, steht in der Tabelle am Ende.

**Warum nicht Music Assistant:** Music Assistant ist ein eigener Server mit eigener Mediathek, der Boxen und Lautsprecher bespielt; wir brauchen nur „diese Datei im Browser abspielen“, und die Dateien liegen schon unter dem Medien-Pfad der Integration. Ein zweites System wäre mehr Pflege ohne Nutzen.

#### 11.4.1 Audio-Ausgabe: Ansicht der Integration

* **Neue `HomeAssistantView`** `TobiboxAudioView` (neben `TobiboxUploadView` in `http.py`, bei `async_setup` registriert): `GET /api/tobibox/audio/{serie_id}/{folge_id}`, `requires_auth = True`, `cors_allowed = False`. `folge_id` ist der **Name der Folge** wie in `serie.json` `folgen` (Datei- oder Ordnername; die Seite kennt ihn aus `serie/get` und bildet **jedes Pfadsegment mit `encodeURIComponent`**, G27; die Signatur vergleicht den **entschlüsselten** Pfad, `claims["path"] != request.path` in `http/auth.py`). Bei Ordner-Folgen (mehrere Tracks) kommt `?track=<n>` (0-basiert) dazu.
* **Pfad-Sicherheit (IDs statt Pfade):** (1) `serie_id` muss die ID einer **bekannten** Serie sein (Index der Integration, `gueltige_serien_id`); (2) `folge_id` muss **genau** einem Eintrag in `serie.folgen` entsprechen (Vergleich der ganzen Zeichenkette, keine Pfadbildung aus der Eingabe); (3) `track` ist eine Zahl, die Datei kommt aus der **eigenen sortierten Trackliste** (`dateien.tracks_in_ordner`), nicht aus der Anfrage;
  (4) **zwei getrennte Zweige (G6):** (a) **Original**: Wurzel ist der aufgelöste Medien-Pfad `medien/`, der fertige Pfad wird **aufgelöst** (`resolve()`) und muss darunter liegen (`is_relative_to`), sonst 404; (b) **Hörkopie**: Wurzel ist der aufgelöste Ordner `hoerkopien/` (liegt absichtlich **außerhalb** von `medien/`, 11.4.7), der Pfad entsteht **nur** aus `serie_id` und `kennung`, beide vom Backend erzeugt (nie aus der Anfrage), dann `resolve()` und `is_relative_to(hoerkopien)`. Eine Kopie ist über keine andere `serie_id` erreichbar (Test). Die Regel „unter dem Medien-Pfad“ gilt also nur für den Zweig (a); sie wörtlich auf (b) anzuwenden hieße, nie eine Kopie auszuliefern; ein Symlink aus dem Medien-Pfad hinaus ist damit ausgeschlossen; (5) nur Dateien, keine Ordner; Endung (ohne Groß/Klein) aus `ENDUNGEN`; (6) Systemordner (`_papierkorb`, `_upload`, `eingang`, `export`, `releases`, alles mit `.`, `@`, `#`, `$` am Anfang) sind nie eine Serie, also nie erreichbar. Kein `..`, keine absoluten Pfade, keine Rückgabe von Pfaden in Fehlertexten.
  Dieselbe Strenge wie HA bei `/media/…` (`raise_if_invalid_path`, `async_full_path` mit `relative_to`; gelesen in `media_source/local_source.py`), nur enger, weil hier gar kein Pfad von außen kommt.
* **Antwort:** eine **Unterklasse von** `aiohttp.web.FileResponse` (kann Range, ETag, Last-Modified, schickt die Datei ohne sie in den Speicher zu laden; HA benutzt es für `/media/…` genauso), Kopfzeilen `Content-Type` aus einer **eigenen Tabelle** (mp3 `audio/mpeg`, m4a und m4b `audio/mp4`, aac `audio/aac`, flac `audio/flac`, ogg und opus `audio/ogg`, wav `audio/wav`), `X-Content-Type-Options: nosniff`, `Cache-Control: private, max-age=3600`. Keine `Content-Disposition: attachment` (Browser soll abspielen, nicht speichern).
* **Range:** Safari, Chrome und Firefox fragen Audio in Teilen an (`Range: bytes=…`) und springen mit neuen Teil-Anfragen; ohne 206 geht Springen nicht (Safari spielt ohne Range gar nicht). `FileResponse` antwortet mit 206, `Content-Range`, `Accept-Ranges: bytes`, 416 bei Unmöglichem (Test unten). Nur **ein** Bereich je Anfrage; mehr fragt kein Browser.
* **Fehler:** 401 ohne gültige Anmeldung (macht HA), 404 `folge_nicht_gefunden` (auch für unbekannte Serie, damit man nicht Ordner erraten kann), 503 `medien_nicht_erreichbar` (NAS weg). **Kein** `HEAD` nötig (Browser nehmen GET mit Range); `HEAD` kann man wie bei `LocalMediaView` ergänzen. **Wichtig (G3, belegt im Versuch mit Chromium):** `<audio>` meldet für 401, 429, 503 und 404 **dasselbe** (`MediaError` Code 4, „Format error“). Die Seite kann den Zustand also nicht aus dem Element lesen; darum der WebSocket-Befehl **`audio/bereit`** (V-6): Er liefert **vor** dem Setzen von `src` den Zustand `bereit`, `wird_vorbereitet` oder `fehlt` und bei `bereit` den signierten Pfad. Nach **jedem** `error` des Elements fragt die Seite wieder `audio/bereit` (nie mit einem alten Link per `fetch` probieren: ein 401 wäre ein „fehlgeschlagener Login“, 11.4.2) und liest erst mit dem **frischen** Link, falls nötig, per `fetch(…, {headers: {Range: "bytes=0-0"}})` Status und JSON-Fehler zur Diagnose.
* **Last und Zähler (G5):** Audio ist klein (MP3 128 kbps = 1 MB je Minute); ein Hörbuch mit 10 Stunden ist rund 600 MB, aber nur die gerade gebrauchten Teile werden übertragen. **Grenze: höchstens 6 offene Audio-Verbindungen je Benutzer** (darüber 429 `zu_viele_streams`); „Stream“ ist hier eine **offene HTTP-Verbindung** (ein Browser hält je `<audio>`-Element 1 bis 2). **Umsetzung:** Ein Zähler um `return web.FileResponse(...)` zählt zu früh herunter, weil `FileResponse` **nach** dem Rückgabewert des Handlers sendet (im Versuch mit aiohttp 3.14.5 stand der Zähler während der Übertragung schon wieder bei 0). Darum zählt die **Unterklasse in `prepare()` hoch und gibt im `finally` frei** (alternativ ein Zähler mit Ablaufzeit). Test in A4c mit einem **langsam lesenden** Client: die siebte offene Verbindung bekommt 429.

#### 11.4.2 Zugriff: signierter Pfad (`auth/sign_path`)

Ein `<audio src>` kann **keinen Authorization-Header** senden. Darum:

1. Die Seite fragt per WebSocket `audio/bereit` (V-6). Das Backend bildet den **signierten Pfad** mit `async_sign_path` (derselbe Aufruf wie HAs eigener Befehl `auth/sign_path`; **24 Stunden**) und gibt ihn bei `bereit` mit. (Der HA-Befehl `auth/sign_path` selbst darf jeder angemeldete Benutzer aufrufen; die Seite braucht ihn nicht mehr.)
2. Das Ergebnis ist `…?authSig=<JWT>`; die Seite setzt es (mit `hass.hassUrl()` für die Companion-App) als `src` des `<audio>`-Elements.
3. HA prüft die Signatur: **Pfad und Abfrage-Teile müssen genau stimmen** (`?track=2` ist mitsigniert, also je Track neu signieren), **nur GET und HEAD**, gebunden an die Anmeldung (Refresh-Token) des Benutzers: wird sie widerrufen, ist die Adresse tot. Der Benutzer ist danach `request["hass_user"]`, die Ansicht läuft also als er.
4. **Gültigkeit: 24 Stunden** (Entscheidung Tobias, Runde 10; ersetzt „1 Stunde“ aus Frage 14). Die Ablaufzeit wird **nur beim Start jeder Anfrage** geprüft. Weil der Browser beim **Springen und nach Pausen neue Anfragen** mit derselben Adresse stellt, darf die Gültigkeit nicht „30 Sekunden“ (Vorgabe von `auth/sign_path`) sein. HA selbst benutzt für Medien ebenfalls **24 Stunden** (`CONTENT_AUTH_EXPIRY_TIME` in `media_player/const.py`). **Warum nicht kürzer (G4, belegt in `http/ban.py`, `helpers/http.py`):** Jeder 401 einer Ansicht mit Anmeldung läuft durch `ban_middleware`, die `HTTPUnauthorized` fängt und `process_wrong_login` ruft: **Eintrag im Log und persistente Mitteilung „Login attempt failed“**, bei gesetzter Schwelle `login_attempts_threshold` auch ein IP-Bann (Vorgabe: kein Bann, aber die Mitteilung kommt immer). Ein Entwurf, der den 401 als Normalfall einplant, hätte Tobias jede Stunde eine Mitteilung beschert und bei gesetzter Schwelle die Familie aussperren können. Darum: **der Link wird vorher erneuert** (bei jedem Start einer Folge und, solange die Seite offen ist, nach 20 Stunden); ein 401 soll praktisch nie vorkommen (nur nach über 24 Stunden Pause, dann fragt die Seite per `audio/bereit` neu). „Kein Fehler für die Partnerin“ heißt jetzt auch: **keine Meldung für Tobias**.
   **Weitergabe-Risiko und Gegenmittel (kurz):** Wer die Adresse hat, kann **diese eine Datei** bis zum Ablauf mit den Rechten des Besitzers abrufen (kein Rechtezuwachs, keine Liste, kein Raten anderer Dateien); 24 Stunden sind ein größeres Fenster als 1 Stunde. Gegenmittel: (a) ein Link gilt nur für **eine Folge** und, bei Ordnern, einen Track (`?track` ist mitsigniert); (b) er ist an die Anmeldung gebunden: wird die Sitzung des Kontos in HA beendet (Profil, Sicherheit, Sitzung löschen), sind **alle** Links dieses Kontos sofort tot; (c) er läuft von selbst ab; (d) die Seite zeigt ihn nirgends zum Kopieren; (e) die Doku sagt: Adresse nicht weitergeben.
5. Die Seite fragt **nur die Folge, die sie gleich spielt** (und die nächste im Voraus, damit der Wechsel nahtlos wird), nicht die ganze Liste.

*Beleg:* So macht HA es für Medien: `media_source/resolve_media` (`media_source/http.py`) ruft `async_process_play_media_url` (`media_player/browse_media.py`) auf, und das signiert mit `async_sign_path` und `CONTENT_AUTH_EXPIRY_TIME`. Die Kamera-Bilder von HA nutzen **nicht** diesen Weg, sondern ein eigenes Zugriffs-Token an der Entität (`/api/camera_proxy/<entity_id>`; **nicht** weiter geprüft). Der Beleg ist also der Medienweg von HA, nicht die Kamera.

**Was ist das, in Alltagssprache (Rev. 4, Frage 14):** Wenn du am Handy auf „Reinhören“ tippst, holt sich dein Handy die Audiodatei bei Home Assistant ab. Dafür braucht es eine **Adresse**, ähnlich einer Internetadresse. Der Player in der Seite kann beim Abholen kein Passwort mitschicken; darum hat die Adresse einen **eingebauten Schlüssel**, der nach einer Weile **von selbst abläuft**. Das ist wie eine Eintrittskarte mit Uhrzeit: Nach Ablauf funktioniert genau diese Adresse nicht mehr, und wer sie weitergibt, kann nichts mehr damit anfangen. Die Seite holt sich rechtzeitig eine neue Karte und macht an derselben Stelle weiter. Beschlossen: Die Karte gilt **24 Stunden**, wie bei Home Assistant selbst (Frage 14).

#### 11.4.3 Dateiformate

Die Bibliothek erlaubt (`data-model.md` Abschnitt 5, `const.ENDUNGEN`): **MP3, M4A, M4B, AAC, FLAC, OGG, Opus, WAV.** Ob der **Browser** sie spielt (Daten von caniuse.com, am 12.11. aus dem Quell-Repository geholt, „im `audio`-Element“):

| Format | Chrome / Edge | Firefox | Safari (Mac) | Safari iPhone/iPad |
|---|---|---|---|---|
| MP3 | ja | ja | ja | ja |
| M4A, M4B, AAC (AAC im MP4-Behälter) | ja | ja (je nach Betriebssystem: „teilweise“) | ja | ja |
| FLAC | ja (ab 56) | ja (ab 51) | ja (ab 13) | ja (ab 11) |
| WAV | ja | ja | ja | ja |
| OGG (Vorbis) | ja | ja | **erst ab 18.4** | **erst ab iOS 18.4** |
| Opus (OGG) | ja | ja | nur teilweise | erst ab iOS 18.4 |

Folgerungen: **MP3 und M4A/M4B (mit AAC) gehen überall** und sind der Normalfall (Audible-Dateien mit Kopierschutz kommen ohnehin nicht herein). **OGG/Opus** brauchen in älteren Safari-Versionen eine Umwandlung; M4A kann auch Apple-Lossless (ALAC) enthalten, das Chrome nicht spielt; FLAC und WAV spielen in neuen Browsern, sind aber groß (WAV etwa 10 MB je Minute) und für Mobilfunk unhandlich.
**Entscheidung Tobias (Runde 8, Nr. 17): alle Formate im Bestand.** Damit Reinhören überall geht, legt Home Assistant für diese Formate **einmal eine Hörkopie** an (11.4.7): AAC in M4A, 96 kbit/s, mit `ffmpeg`, auf dem NAS **neben** `medien/`, nicht auf den Boxen. Es wird **nicht beim Abspielen umgewandelt**: abgespielt wird immer eine fertige Datei, also geht Springen per Range-Anfrage wie beim Original. Die Seite behält die Vorabprüfung mit `canPlayType` und den Text „**Das kann dieser Browser nicht abspielen. Auf der Box spielt es trotzdem.**“ nur noch als Rückfall (kein `ffmpeg`, Kopie fehlgeschlagen).
Kapitel eingebetteter M4B-/MP3-Dateien zeigt die Seite jetzt in der Kapitelliste (11.4.8); die Datei selbst läuft weiter als **eine** Zeitleiste.

#### 11.4.4 Dauer, Kapitel und Codec (neu, additiv)

Für „Gesamtdauer“, Zeitleiste und Fortschritt braucht die Seite die Länge. `ffprobe` liefert sie beim Einsortieren schon (`ProbeErgebnis.dauer_s`), sie wird nur nicht gespeichert.

* Store `tobibox.medieninfo` (11.3, **nicht** `serie.json`, G10): `dauer_s` (Zahl, Sekunden, auf ganze Sekunden gerundet) und bei Ordner-Folgen `spuren_s` (Liste der Tracks in der Reihenfolge der Folge).
* **Plausibilität und Deckel (G1):** Eine gültige FLAC-Datei mit digitaler Stille besteht `pruefe_datei` und hat bei 500 MiB eine Dauer von rund 940 Stunden (gemessen: 2 Stunden Stille = 1,1 MB). Darum speichert die Integration **keine Dauer über dem Dauerdeckel** (48 Stunden); `hoerkopie` wird dann `fehler` mit Grund `zu_lang`, und Zeitleiste und Gesamtdauer zeigen „–“. Dazu die Plausibilität Größe zu Dauer (11.4.7).
* **Beim Einsortieren** gespeichert; für den **Bestand** einmal im Hintergrund nachgeholt (Frage 18 gilt weiter, **nur** für Dauer, Kapitel und Codec, **nicht** für Hörkopien, 11.4.7), genau wie die Cover-Suche (5.5): nur Folgen ohne `dauer_s`, eine Datei nach der anderen, **feste** 20 s Zeitgrenze je Datei (`ffprobe` hat zusätzlich seine 30 s und `RLIMIT_AS`), Abbruch bei `medien_nicht_erreichbar`, **kein Dauer-Scan beim Öffnen der Seite**. Bei 5 000 Dateien ist das eine Sache von Minuten bis Stunden im Hintergrund; bis dahin zeigt die Seite „–“ statt der Dauer und blendet die Zeitleiste erst beim Laden der Datei auf (`loadedmetadata`).
* *Serie-Kurzform* bekommt `dauer_s` (Summe); das *Folge-Objekt* von `serie/get` bekommt `dauer_s`, `spuren_s`.
* **Ein Durchgang für alles (Rev. 4):** Derselbe `ffprobe`-Aufruf liefert mit `-show_chapters` zusätzlich die **Kapitel** (11.4.8); dazu wird der **Codec** des ersten Audio-Stroms **je Track** gemerkt (`codecs`, für 11.4.7, G30). `ffprobe.py` ergänzt `-show_chapters` in `baue_ffprobe_befehl` (die vorhandenen Tests prüfen die Argumentliste mit „enthält“, nicht auf Gleichheit; geprüft in `test_ffprobe.py`) und `Probe` um `kapitel` und `codec` (je Track gesammelt). **Kein zweiter Lesedurchgang über das NAS:** Beim Einsortieren und beim Nachholen des Bestands (Zeitgrenze 20 s je Datei, Abbruch bei `medien_nicht_erreichbar`, nie beim Öffnen der Seite) kommen `dauer_s`, `spuren_s`, `kapitel` und `codecs` aus **einem** Lauf je Datei. Hörkopien reiht der Hintergrundlauf **nur für neu Einsortiertes** ein (11.4.7).

#### 11.4.5 Hörstelle (Weiterhören), je Benutzer in HA

* **Speicher:** HA-`Store` `tobibox.hoerstellen` (Version 1, `.storage/`), gespeichert mit `async_delay_save` (**Verzögerung 60 s**, G28: im Speicher sofort, auf der Platte gesammelt; bei einem Store für alle Benutzer wären 10-Sekunden-Schreibvorgänge bei 450 KB Obergrenze rund 160 MB je Stunde Dauerhören auf einer SD-Karte; beim Stoppen von HA schreibt `Store` ohnehin zuletzt): `{ "<user_id>": { "<serie_id>": { "zeit": <ISO>, "folge": "<Name>", "folgen": { "<Name>": { "p": 47, "d": 167, "t": <ISO>, "fertig": false, "track": 0 } } } } }`.
  Je Benutzer nur Einträge für angefangene Serien; Obergrenze 2 000 Serien je Benutzer, 100 Folgen je Serie (darüber fallen die ältesten weg). Größenordnung: 5 000 Folgen × 90 Byte ≈ 450 KB, kein Problem. Beim Start fallen Einträge unbekannter Benutzer, gelöschter Serien und nicht mehr vorhandener Folgen weg.
* **Kein Zugriff auf fremde Hörstellen:** jeder Befehl nimmt die Benutzer-Kennung aus der Verbindung (`connection.user.id`), nie aus der Eingabe. Auch Administratoren sehen nur ihre eigenen (Frage 16).
* **Befehle** (WebSocket; Recht: `get` und `liste` **lesen**, `set` **alltag**, wie in 10.2; Vertrag W Abschnitt 6 Form):

| Befehl | Eingabe → Ausgabe |
|---|---|
| `hoerstelle/get` | `serie_id` → `weiter` (`folge`, `position_s`, `track`, `anteil`, `rest_s`, `zeit`) oder `null`; `folgen` = Objekt Name → `position_s`, `dauer_s`, `fertig`, `zeit` |
| `hoerstelle/set` | `serie_id`, `folge`, `position_s`, `dauer_s`, optional `track`, optional `fertig` → `{}`. Prüft: Serie und Folge gibt es, `0 ≤ position_s ≤ dauer_s + 2`; **ist `dauer_s` der Folge im Store `tobibox.medieninfo` bekannt, nimmt das Backend diesen Wert und ignoriert den gesendeten** (G29: der Aufrufer darf die Prüfung nicht selbst bestimmen; in Stufe B zählt es als Hörzeit); nur bei unbekannter Dauer gilt der gesendete Wert bis höchstens 24 Stunden; `fertig` wird auch gesetzt, wenn `position_s ≥ dauer_s − 2`. Antwortet **sofort**, schreibt über `async_delay_save`. |
| `hoerstelle/liste` | `limit` (1 bis 12, Vorgabe 8) → angefangene, nicht fertige Einträge, zuletzt angehört zuerst: `serie_id`, `name`, `folge`, `position_s`, `anteil`, `rest_s`, `zeit` (für die Reihe „Weiterhören“) |

  `serien/list` bekommt je Kurzform (nur wenn angefangen) `hoerstelle` (`anteil`, `rest_s`, `zeit`, `folge`) **für den Anfragenden** und die Sortierung `angehoert`; `serie/get` bekommt je Folge `hoerstelle` (`position_s`, `fertig`). So braucht die Bibliothek keine zweite Abfrage je Zeile.
* **Wann die Seite speichert (gedrosselt):** höchstens **alle 10 Sekunden** während der Wiedergabe, **sofort** bei Pause, beim Springen, beim Wechsel der Folge, beim Ende, beim Schließen der Seite (`pagehide`, `visibilitychange`; auf dem Handy nicht verlässlich, darum die 10 Sekunden). Das Backend drosselt zusätzlich (höchstens 30 Schreibaufrufe je Minute und Benutzer, sonst `zu_viele_aenderungen`; dieselbe Grenze wie 10.3, eigener Zähler); die Platte sieht davon nur einen Schreibvorgang je 60 Sekunden.
* **Zwei Geräte:** Es gilt „zuletzt gespeichert gewinnt“ je Folge. Wer auf dem Handy bei 10:00 pausiert und am Computer „Weiterhören“ drückt, holt sich beim Öffnen der Seite die Stelle von dort (`hoerstelle/get`). Gleichzeitig auf zwei Geräten hören ist nicht vorgesehen.
* **Reinhören in „Gehört“ (Stufe B, Rev. 4):** Die Hörstellen-Aufrufe sind zugleich die Quelle für den Bereich „Reinhören“: HA leitet daraus Sitzungen ab, die Seite sendet nichts Neues (12.5).
* **Box und Hörstelle sind getrennt:** Die Box führt ihre eigene Stelle (`resume.json`, `data-model.md`); das Reinhören verändert sie nie und umgekehrt.

#### 11.4.6 Was belegt ist und was noch zu prüfen bleibt

| Aussage | Stand |
|---|---|
| `auth/sign_path` gibt es, Eingaben `path`, `expires` (Vorgabe 30 s), nur für angemeldete Benutzer | **belegt** (HA-Quelle `components/auth/__init__.py`, `dev`, 12.11.) |
| Signatur bindet Pfad **und** Abfrage-Teile, gilt nur für GET/HEAD, ist an den Refresh-Token gebunden, Ablauf wird beim Anfragestart geprüft | **belegt** (HA-Quelle `components/http/auth.py`: `async_sign_path`, `async_validate_signed_request`) |
| HA selbst nutzt signierte Pfade mit 24 Stunden für Medien (**auch unser Wert**, Runde 10) | **belegt** (`media_player/browse_media.py`, `media_player/const.py`: `CONTENT_AUTH_EXPIRY_TIME = 3600 * 24`; `media_source/http.py`); Kamera-Bilder nutzen einen anderen Weg (nicht geprüft) |
| `web.FileResponse` beantwortet Range mit 206, `Content-Range`, `Accept-Ranges`, 416 | **belegt**: Test mit aiohttp 3.14.5 (die Version im selben Python-Umfeld wie HA 2026.10.4): `bytes=0-1` → 206, `bytes=50000-` → 206, `bytes=-500` → 206, `bytes=999999-` → 416; ohne Range 200 mit `Accept-Ranges: bytes`; `HEAD` ohne eigenen Handler 405 |
| HA benutzt `FileResponse` für lokale Medien (`/media/…`) und prüft Pfade mit `relative_to` | **belegt** (`media_source/local_source.py`) |
| Browser-Formate nach Tabelle 11.4.3 | **belegt aus caniuse-Daten**; Verhalten auf Tobias' Geräten **zu prüfen** (A15b) |
| Sonderzeichen im Pfad laufen durch die Signatur (die Prüfung vergleicht den **entschlüsselten** Pfad, `claims["path"] != request.path`) | **belegt** (HA-Quelle), Verhalten **zu prüfen**: Test in A4c und im Player-Test mit „Der Wald (Teil 1).mp3“, „Märchen.m4a“, „Teil 1 #2 (Ende)?.mp3“, „100% Mond+Sterne.mp3“, „&Rest.mp3“ und führendem Punkt; die Seite bildet jedes Segment mit `encodeURIComponent` |
| `<audio>` unterscheidet 401, 429, 503 und 404 nicht (immer `MediaError` Code 4) | **belegt** (Versuch mit Chromium und aiohttp 3.14.5, Review Rev. 4a); darum `audio/bereit` |
| Jeder 401 einer Ansicht mit Anmeldung löst `process_wrong_login` aus (Log, persistente Mitteilung „Login attempt failed“, bei Schwelle Bann) | **belegt** (HA-Quelle `components/http/ban.py`, `ban_middleware`; im Wheel 2026.10.4 gelesen) |
| Ein Zähler um den Rückgabewert von `FileResponse` zählt zu früh herunter | **belegt** (Versuch mit aiohttp 3.14.5); Lösung: Unterklasse mit `prepare()` und `finally` |
| Ob `FileResponse` auf dem NAS-Pfad (SMB/NFS) beim Springen schnell genug ist | **zu prüfen** am echten NAS (A16) |
| Companion-App: spielt `<audio>` bei gesperrtem Bildschirm weiter, zeigt der Sperrbildschirm die Medien-Steuerung? | **zu prüfen** (iOS und Android, A0b); sonst nur „im Vordergrund hören“ |
| `ffmpeg` ist in HA da: Die Integration `ffmpeg` (`homeassistant/components/ffmpeg`, Zweig `dev`, geholt am 12.11.) legt einen `FFmpegManager` an (`get_ffmpeg_manager(hass).binary` liefert den Pfad, Vorgabe `ffmpeg`); beim offiziellen Container-Image rechnet sie mit `ffmpeg` 6.0 (`OFFICIAL_IMAGE_VERSION`). `ffmpeg` ist also Teil des Images, nicht nur ein Python-Paket. Die Integration `tobibox` nutzt schon `shutil.which("ffmpeg")` (`ffprobe.py`, `ffmpeg_pfad()`) und das README sagt „HA OS bringt beide mit“ | **belegt** (Quellen); `get_ffmpeg_manager` wirft `ValueError`, wenn die Integration `ffmpeg` nicht geladen ist: darum nur als **optionale** Erstwahl, kein Eintrag in `manifest.json`; Version und Encoder in Tobias' HA **zu prüfen** (A0b: `ffmpeg -version`, `-encoders | grep aac`) |
| `ffprobe -show_chapters` liefert Kapitel (Startzeit, Titel) für M4B **und** MP3 (ID3v2 `CHAP`), auch mit erzwungenem Format | **belegt** (Test mit ffprobe 6.1.1: M4B und MP3 mit je 3 Kapiteln, `start_time` und `tags.title` kommen zurück, Aufruf wie `ffprobe.py`); echte Hörbücher von Tobias **zu prüfen** (A3b) |
| Hörkopie mit dem eingebauten AAC-Encoder: Größe und Zeit | **gemessen** (Testrechner, ffmpeg 6.1.1): 10 Minuten aus OGG Vorbis, Opus, FLAC und ALAC je 7,3 MB (Soll 7,2 MB), Dauer unverändert (600,0 s), Kodierzeit 6,6 bis 9,5 s (60 bis 90 mal Echtzeit); **auf HA-Hardware zu prüfen** (A16) |
| Safari verlangt eine Geste zum Start | berücksichtigt: Ton startet nur nach Tap; Folgenwechsel nach Ende läuft weiter, weil die Seite schon spielt (zu prüfen auf iOS) |

#### 11.4.7 Hörkopie (Rev. 4, Rev. 5 mit harten Grenzen)

**Ziel (Runde 8, Nr. 17: alle Formate):** Reinhören geht für jede Datei des Bestands, auf jedem Gerät, mit Springen, ohne Umwandeln beim Abspielen. Die **Box bekommt immer das Original**; die Kopie ist nur für den Browser.

* **Wann braucht ein Track eine Hörkopie?** Nach dem **Codec des Tracks** (`codecs`, 11.3; **je Track**, G30): `mp3` und `aac` (also MP3, M4A/M4B mit AAC, AAC) spielen überall: **Original**. Alles andere bekommt eine Kopie: `vorbis` (OGG), `opus`, `alac`, `flac`, `pcm_*` (WAV) und alles Unbekannte. Die Regel steht an **einer** Stelle im Code (`braucht_hoerkopie(codec)`); die Folge ist „fertig“, wenn alle Tracks fertig sind, die eine Kopie brauchen.
* **Wann sie entsteht (Entscheidung Tobias, Runde 10):** (a) **Neu Einsortiertes sofort**: nach `pruefe_datei` und dem Ablegen in `medien/`, im Hintergrund, die Meldung „fertig“ wartet nicht darauf. (b) **Der Bestand erst beim ersten Reinhören** („Die Hörprobe wird vorbereitet“, 5.3): `audio/bereit` (V-6) stellt die Datei in die Warteschlange und antwortet `wird_vorbereitet`. Das **ersetzt für die Hörkopien den Hintergrund-Lauf über den Bestand**; Dauer, Kapitel und Codec werden weiter einmal im Hintergrund nachgeholt (Frage 18). Zustand im Bestand bis dahin: `nicht_angelegt`. Wartezeit: bei einem Lied etwa eine Minute, bei einem Hörbuch von 10 Stunden 20 bis 40 Minuten (Schätzung 15 bis 30 mal Echtzeit auf HA-Hardware, **zu messen in A0b**). (c) **Vorgezogen** heißt dasselbe wie (b): Die angeforderte Datei geht an die Spitze, aber **je Benutzer höchstens eine** vorgezogene Datei zugleich.
* **Harte Grenzen (G1; gelten für `ffmpeg` und für `ffprobe`):** Ohne sie macht jede hochgeladene Datei (jeder darf jetzt hochladen) aus der Kopie eine unbegrenzte Rechenarbeit: eine FLAC-Stille von 500 MiB hat eine Dauer von rund 940 Stunden, bindet die Schlange 2 Stunden (und hinterlässt Hunderte MB `.part` auf dem NAS), acht davon je Stunde blockieren **alle** Hörproben für Tage (gemessen; auf HA-Hardware langsamer).

| Grenze | Wert (Vorgabe, nach A0b einstellbar als Konstante) |
|---|---|
| **Dauerdeckel** | **48 Stunden**; darüber `hoerkopie: fehler`, Grund `zu_lang`, keine Kopie, **auch kein `dauer_s` über dem Deckel** (11.4.4) |
| **Zeitgrenze je Datei, fest** | **60 Minuten**, **nicht** aus der Dauer im Dateikopf gerechnet (die alte Formel `max(120 s, Dauer/8 + 60 s)`, höchstens 2 Stunden, entfällt); überschritten: Abbruch, Grund `zeitgrenze`. `ffprobe` hat seine festen 30 s |
| **`-t`** | Ausgabe höchstens **Dauer + 5 s**, nie über dem Deckel |
| **`-fs`** | Ausgabe höchstens **Dauer × 12 KB/s × 1,2** (96 kbit/s = 12 KB/s); überschritten: Abbruch |
| **Plausibilität Größe zu Dauer** | Faktor über 50 (Bytes je Sekunde gegen das übliche Maß, bei FLAC, ALAC, Opus) ist verdächtig: **keine Kopie**, Grund `unplausibel` |
| **Schlangenlimit** | höchstens **20 Dateien** und **50 GB** Quelle in der Warteschlange; darüber `hoerkopie_warteschlange_voll`; der Zähler steht in „Technik“ (5.9) |
| **Kontingent `hoerkopien/`** | höchstens **100 GB** insgesamt; darüber `kein_speicher`, nichts wird gelöscht |
| **Vorziehen** | je Benutzer eine Datei (10.3) |
| **Parallel** | eine Datei zugleich, `nice` |

* **Erzeugen:** `ffmpeg -nostdin -v error -protocol_whitelist file -f <Format der Endung> -i file:<Pfad> -map 0:a:0 -vn -ac 2 -map_metadata -1 -t <Dauer+5> -fs <Grenze> -c:a aac -b:a 96k -movflags +faststart -f mp4 file:<Ziel>.part`, danach umbenennen. `-map 0:a:0` nimmt genau einen Audiostrom, `-ac 2` mischt Mehrkanal auf Stereo. Gleiche Härtung wie `ffprobe.py` (Liste von Argumenten, nie Shell, `RLIMIT_AS`, feste Zeitgrenze; Programm: Erstwahl `get_ffmpeg_manager(hass).binary`, wenn die Integration `ffmpeg` geladen ist, sonst `shutil.which("ffmpeg")`). **Warum AAC in M4A:** `aac` ist der in ffmpeg eingebaute Encoder (immer da, `libmp3lame` nicht in jedem Bauplan), M4A spielt auf allen Zielgeräten, `+faststart` legt den Index nach vorn, damit der Browser sofort per Range anfragen kann. 96 kbit/s reichen zum Erkennen, was etwas ist. Bei Ordner-Folgen: eine Kopie je Track.
* **Wo (Entscheidung und Begründung):** Auf dem NAS im Ordner **`hoerkopien/<serie_id>/<kennung>.m4a` neben `medien/`** (wie `export/`, `eingang/` und `releases/`, gleiche Freigabe, Vertrag W 11.1), **nicht** im Medienordner der Boxen und **nicht** in HAs Konfigurationsordner. Gründe: (1) `hoerkopien/` liegt **außerhalb des rsync-Moduls `medien`**; die Box holt sie nie, und **`sync.py` braucht keine weitere Ausnahme**; (2) HAs Konfigurationsordner liegt meist auf einer kleinen SD-Karte oder SSD und wandert in jede HA-Sicherung; (3) die Integration schreibt auf diese Freigabe schon heute. `kennung` = die ersten 16 Zeichen von `sha1(folge|track|größe|Änderungszeit)`: ändert sich das Original, entsteht eine neue Kopie; verwaiste Kopien (Serie oder Folge endgültig gelöscht, Kennung veraltet) räumt ein Hintergrundlauf weg. Der Zustand steht im Store `tobibox.medieninfo` (11.3), **nicht** in `serie.json`. Die Audio-Ansicht liest diesen Ordner über den **eigenen Zweig** (11.4.1, G6).
* **Speicherbedarf (Schätzung):** 96 kbit/s = 12 KB/s = **43 MB je Stunde**. Gemessen: 10 Minuten werden 7,3 MB (11.4.6). Seit Runde 10 entsteht der Bestand nur nach Bedarf: Platz wächst mit dem, was jemand anhört. Schlechtester Fall (ganzer Bestand in keinem Browser-Format, 1 600 Stunden): ≈ **70 GB**, begrenzt durch das Kontingent. Das NAS hat einige TB frei (Frage 26).
* **Fehlerfall:** (1) `ffmpeg` fehlt oder die Fähigkeit nicht gemeldet: keine Kopien, kein Fehler; Formate ohne Browser-Unterstützung zeigen den Rückfalltext. (2) Das Kodieren schlägt fehl (kaputte Datei, `zu_lang`, `zeitgrenze`, `unplausibel`, `kein_speicher`, NAS weg): `hoerkopie.zustand = "fehler"` mit `grund`. **Keine Dauerschleife:** ein Versuch je Datei und Start der Integration, danach erst wieder auf `hoerkopie/neu_erzeugen` (Admin). NAS weg pausiert die Warteschlange. Die Seite zeigt „Für diese Datei gibt es keine Hörprobe. Auf der Box spielt sie trotzdem.“ (3) Halbe Dateien (`*.part`) werden beim Start gelöscht. (4) Die Box ist nie betroffen.
* **Papierkorb, Umbenennen, Verschieben, Zusammenführen:** Kopien hängen an `serie_id` und Kennung; Papierkorb und Umbenennen berühren sie nicht, Verschieben und Zusammenführen ändern die `serie_id` (die Kopie wird beim nächsten Lauf unter der neuen ID wiedergefunden oder neu gemacht), endgültiges Löschen räumt der Hintergrundlauf auf.
* **Tests (A3c):** FLAC-Stille (2 Stunden, gültig) → `zu_lang` bzw. `unplausibel` **ohne** Kopie und ohne `dauer_s` über dem Deckel; Mehrkanal-Quelle → Stereo; `-fs` bricht eine überlange Ausgabe ab; die Schlange nimmt die 21. Datei nicht; das Vorziehen je Benutzer ist auf eine Datei begrenzt; Zeitgrenze fest, nicht aus dem Dateikopf.

#### 11.4.8 Kapitel (neu in Rev. 4)

* **Quellen, in dieser Reihenfolge:** (1) **Eingebettete Kapitel** der Datei (`ffprobe -show_chapters`: M4B-Kapitelspur, MP3 ID3v2 `CHAP`); belegt für beide Formate (11.4.6). (2) Bei einer **Ordner-Folge** ist jeder **Track ein Kapitel**: Titel aus dem Tag `title`, sonst Dateiname ohne Endung und ohne führende Nummer; Start = Summe der vorigen `spuren_s`. (3) Sonst keine Kapitel (die Seite zeigt keine Liste). Eine Datei **mit** eingebetteten Kapiteln gewinnt vor den Tracks.
* **Speicherung:** `kapitel` im Store `tobibox.medieninfo` (11.3, nicht in `serie.json`, G10), beim Einsortieren gelesen und im Hintergrund für den Bestand nachgeholt (11.4.4, im selben Lauf). Sortiert nach `start_s`; doppelte Startzeiten und Rückwärtssprünge fliegen raus; höchstens 500 Kapitel je Folge. `serie/get` gibt es als `kapitel` aus (V-8); die Box bekommt es nie.
* **Anzeige:** Player-Vollansicht (Zeile „Kapitel 8: Das Echo (8 von 12)“, Knopf „Kapitel“ und Blatt, 5.12) und Serienseite (Abschnitt „Kapitel“ statt Folgenliste, 5.3). **Eine Zeitleiste über alles bleibt** (Entscheidung Tobias, Nr. 20).
* **Springen:** Bei eingebetteten Kapiteln setzt die Seite `currentTime = start_s`. Bei Ordner-Folgen wechselt sie auf den Track (`?track=n`, neue Signatur, 11.4.2) und setzt die Zeit im Track. Die Hörstelle speichert wie bisher `track` und `position_s`; es gibt kein neues Feld und keinen neuen Befehl.
* **Grenzen:** Hörspiel-Folgen aus **einer** Datei ohne Kapitel zeigen keine Liste. Ein Hörbuch, dessen Ordner nur **eine** Datei hat, zeigt Kapitel nur, wenn die Datei welche enthält. Titel, die nur aus Zahlen bestehen („1“, „2“), zeigt die Seite als „Kapitel 1“, „Kapitel 2“.

## 12. Stufe B (geplant): Gehört, Favoriten, Technik-Verlauf

Nur Entwurf. Gebaut wird nach Freigabe als eigener Block (Abschnitt 15, B1 bis B5).

### 12.1 Was gebraucht wird

Heute meldet die Box **nicht**, was sie gespielt hat (`status` kennt nur den aktuellen Zustand). Für „Gehört“ braucht es ein **Ereignis „gespielt“** und eine **Speicherung** in HA, die über Jahre hält.

### 12.2 Vertragsentwurf für `docs/protocol/mqtt-v1.md` (Box → HA)

Neue `art` in 3.4 (`tobibox/<box>/event`, nicht retained, QoS 1): **`gespielt`**. Eine **Sitzung** ist eine zusammenhängende Wiedergabe einer Folge.

| Feld in `daten` | Typ | Bedeutung |
|---|---|---|
| `seq` | int | laufende Nummer je Box, überlebt Neustarts; Grundlage für Quittung und Doppelerkennung |
| `sitzung` | string (UUID) | gleiche Kennung für Zwischenstände und Abschluss einer Sitzung; HA **ersetzt** den früheren Stand |
| `serie` | string | Serien-ID |
| `folge` | string | Name der Folge (Datei- oder Ordnername) |
| `start` | string oder `null` | Beginn (Box-Uhr); `null`, wenn die Uhr nicht vertrauenswürdig ist (`zeit_unsicher=true`); HA nimmt dann die Empfangszeit minus `dauer_s` |
| `dauer_s` | int | gespielte Sekunden ohne Pausen; Sitzungen unter **10 s** werden nicht gemeldet |
| `ende` | string | `ende_der_folge`, `tobie_abgenommen`, `pause_lang` (Pause über 10 Minuten), `anderes` (anderer Tobie oder Folge), `herunterfahren`, `teilweise` (Zwischenstand) |
| `teilweise_s` | int, nur bei `teilweise` | alle 15 Minuten bei langen Sitzungen (Hörbuch), damit bei Stromausfall höchstens 15 Minuten fehlen |

Keine Kennung des Tobies (Datenschutz, Wiederholung nicht nötig): „Kind“ ist die **Box**. Folge 3.7 bekommt den Befehl **`gehoert_quittung`** (`bis_seq`, Lebensdauer 1 Stunde): HA bestätigt damit gespeicherte Ereignisse.
**Puffer auf der Box:** Boxen sind mobil und oft ohne WLAN. Die Box schreibt jede Sitzung beim Ende als Zeile in `gehoert.jsonl` (Datenordner, höchstens 2 000 Zeilen ≈ 400 KiB, älteste fallen weg) und sendet **alles Unquittierte** beim Verbinden. Schreibbudget (`data-model.md` 1.7): höchstens 1 Schreibvorgang je Sitzungsende; Zwischenstände nur im Speicher und per MQTT (sind sie nicht sendbar, höchstens 4 Schreibvorgänge je Stunde).
Idempotenz: HA speichert mit `UNIQUE(box, seq)`. Rollout: erst die Integration (versteht `gespielt`), dann die Box; eine ältere Integration soll unbekannte `art` ignorieren (zu prüfen gegen mqtt-v1 Abschnitt 8). Technik-Ereignisse (Lader an/aus, online/offline, Sync, Fehler) leitet HA aus `status`, `online` und den vorhandenen Ereignissen selbst ab; dafür ändert sich **nichts** an der Box.

#### 12.2.1 Was „einmal gehört“ heißt (Rev. 3, Zusatz von Tobias)

Tobias will sehen, **welche Box welches Hörspiel wie oft gehört hat**. Dafür gilt, festgelegt auf Vorschlag der Projektleitung:

| Begriff | Regel |
|---|---|
| **Wiedergabe** („Mal gehört“) | Eine **Sitzung** (`sitzung`) mit **mindestens 10 Sekunden** gespielter Zeit (`dauer_s ≥ 10`; kürzere meldet die Box gar nicht). Zwischenstände (`teilweise`) derselben Sitzung zählen **nicht** doppelt (HA ersetzt den Stand je `sitzung`). **Beschlossen (Runde 8, Nr. 19): Sitzungen derselben Box und Folge mit höchstens 5 Minuten Lücke zählen als eine Wiedergabe** (Spalte `wiedergabe`, 12.3). |
| **Hörzeit** | Summe der gespielten Sekunden (`dauer_s`) ohne Pausen. |
| **fertig** („ganz gehört“) | Eine Sitzung mit `ende = ende_der_folge`. Nur sie macht eine Folge „fertig“. |
| **Fertig in der Rangliste (je Hörspiel)** | Anzahl **verschiedener Folgen**, die im Zeitraum mindestens einmal fertig gehört wurden, von der heutigen Zahl der Folgen („17/20“). |
| **Fertig je Folge** (Aufteilung) | Anzahl fertiger Wiedergaben dieser Folge im Zeitraum („2×“). |
| **Zeitraum** | Woche = letzte 7 Tage, Monat = 30, Jahr = 365, jeweils bis jetzt; Alles = seit Beginn. Gerechnet nach `start` der Sitzung. |
| **Wer** | Eine **Quelle**: eine **Box** (Kind = Box) oder ein **HA-Benutzer** am Handy oder Computer; „Alle“ ist die Summe. Die Kennung des Tobies bleibt draußen (Frage 9). |
| **Reinhören am Handy** | zählt **nicht** bei einer Box (5.12); es zählt unter dem Namen des HA-Benutzers in der Auswahl „Wer?“ (12.5). |

Grenzfälle: Ein Tobie, der abgenommen und nach einer Minute wieder aufgelegt wird (`tobie_abgenommen`), ist **eine** Wiedergabe (Lücke höchstens 5 Minuten, Runde 8, Nr. 19); nach einer **längeren** Pause (`pause_lang`, über 10 Minuten, oder Lücke über 5 Minuten) ist das Weiterhören eine **neue** Wiedergabe: gehört „2 Mal“, aber nur einmal fertig. Bei Hörbüchern (eine lange Folge, abends in Portionen) ist „Mal“ deshalb eher hoch und „Hörzeit“ die ehrlichere Zahl; darum stehen beide in der Tabelle.
Das Zusammenfassen macht HA **beim Aufnehmen**: Beginnt eine Sitzung derselben Box und Folge höchstens 5 Minuten nach dem Ende der vorigen, bekommt sie dieselbe `wiedergabe`-Kennung; die Rangliste zählt `COUNT(DISTINCT wiedergabe)`, die Hörzeit bleibt die Summe der Sitzungen. Dieselbe Regel gilt für den Bereich „Reinhören“ (12.5).

### 12.3 Speicherung in HA: Vergleich

| | Recorder / Langzeitstatistik von HA | **Eigene SQLite-Datei** (`<config>/tobibox/gehoert.sqlite`) | JSON-Zeilen-Datei |
|---|---|---|---|
| Vorteile | kein eigener Speichercode; Diagramme und Karten von HA; Akku-Sensor hat `state_class: measurement`, damit gibt es **stündliche Langzeitstatistik ohne Ablauf** | beliebige Fragen (je Eintrag, Folge, Stunde, Box); unabhängig von der Recorder-Bereinigung; idempotent (`UNIQUE`); CSV-Export; HA-Sicherung enthält den Konfigurationsordner | trivial zu schreiben und zu lesen |
| Nachteile | Zustände nur 10 Tage (Vorgabe `purge_keep_days`); Langzeitstatistik nur Summen/Mittel je Entität, **kein „welches Hörspiel“**; eine Entität je Eintrag bei 250+ Einträgen untauglich | eigener Code: Schema, Migration, Zugriff im Executor, Tests; in HA-Standardkarten nicht sichtbar | langsam bei vielen Zeilen, kein Index, Gefahr halber Schreibvorgänge |
| Eignung | **Akku-Verlauf** (Statistik, schon vorhanden), Hörzeit gesamt | **Hörereignisse** und Technik-Ereignisse | nur Notlösung |

**Empfehlung:** SQLite für Hörereignisse und Technik-Ereignisse (Lader, Sync, Fehler, online), **Langzeitstatistik von HA für den Akku** (Seite liest sie über `recorder/statistics_during_period`, nur Administratoren). Favoriten liegen in HA (`.storage/tobibox.favoriten`, Schlüssel `serie_id` oder `serie_id#folge`), nicht in `serie.json` und nicht auf der Box.

**Speicherbedarf (Schätzung, 250 Byte je Zeile mit Index):** 2 Boxen × 20 Sitzungen am Tag ≈ 14 600 Zeilen im Jahr ≈ **3,7 MB**; selbst 100 Sitzungen je Box und Tag nur ≈ 18 MB im Jahr. Technik-Ereignisse (50 je Box und Tag) ≈ 5 MB im Jahr. Akku-Statistik ≈ 2 bis 3 MB im Jahr.
Zusammen **etwa 10 MB im Jahr**, 100 MB in zehn Jahren: „unbegrenzt“ ist unproblematisch. Eine Aufräumregel ist nicht nötig. Trotzdem: Knopf „Alle Hördaten löschen“ und „Als Tabelle sichern“ in „Technik“ (betrifft nur die Boxen-Daten; Hördaten über Kinder sind persönlich; sie bleiben nur in HA, nie in der Cloud).

**Spalten der Tabelle `sitzungen` (SQLite, Rev. 3):** `box`, `seq`, `sitzung`, `wiedergabe`, `serie`, `folge`, `start`, `dauer_s`, `ende`; `UNIQUE(box, seq)`, Indizes `(serie, folge, start)` und `(box, start)`. Die Rangliste ist eine einzige Abfrage: `GROUP BY serie` mit `COUNT(DISTINCT wiedergabe)` (Wiedergaben), `SUM(dauer_s)` (Hörzeit), `COUNT(DISTINCT folge)` unter `WHERE ende='ende_der_folge'` (fertige Folgen); die Aufteilung dasselbe mit `GROUP BY folge` für eine Serie.
Ziel: unter 50 ms bei 15 000 Zeilen (Jahresbedarf, siehe oben), Test in B3.

**Reinhören (Rev. 4a):** Zweite Tabelle `reinhoer_sitzungen` in derselben Datei: `benutzer` (HA-Benutzerkennung), `serie`, `folge`, `wiedergabe`, `start`, `gespielt_s`, `ende`; Indizes `(benutzer, start)` und `(benutzer, serie, folge)`. Größenordnung: 2 Erwachsene × 10 Sitzungen am Tag ≈ 7 300 Zeilen im Jahr ≈ 1,8 MB. Abfragen: `wer=alle` fasst `sitzungen` und `reinhoer_sitzungen` zusammen, `wer=box:<id>` liest `sitzungen WHERE box = <id>`, `wer=benutzer:<id>` liest `reinhoer_sitzungen WHERE benutzer = <id>`.

### 12.4 Vertragsentwurf `ha-websocket-v1.md` (Stufe B)

Fähigkeit **`gehoert`** (Abschnitt „Gehört“ in „Geräte“, Stern und Sortierungen erscheinen nur damit). Neue Befehle:

| Befehl | Recht | Eingabe → Ausgabe |
|---|---|---|
| `gehoert/zusammenfassung` | lesen | **Eingabe (Rev. 5):** **`wer`** (`alle` Vorgabe, `box:<id>` oder `benutzer:<id>`; **ersetzt** die früheren Felder `box`, `quelle` und `benutzer`), `zeitraum` (`woche`, `monat`, `jahr`, `alles`) **oder** `von`/`bis`, `nach` (Liste aus `wer`, `serie`, `folge`, `tag`, `stunde`; **Quelle × Serie × Folge** geht in einem Aufruf), `serie_id` (optional, schränkt auf einen Eintrag ein), `sortierung` (`wiedergaben` Vorgabe, `sekunden`), `limit` (1 bis 200). **Ausgabe:** `zeilen`, je Zeile die Schlüssel aus `nach` (`wer` als `box:<id>` oder `benutzer:<id>`) plus `wiedergaben`, `sekunden`, `fertig` (Sitzungen mit `ende_der_folge`) und, wenn `folge` nicht in `nach` steht, `folgen_fertig` und `folgen_gesamt`; dazu `summe` (`wiedergaben`, `sekunden`, `fertig`) und **`wer_auswahl`**: die Liste der Quellen für die Auswahl „Wer?“ (je Box `{wer: "box:<id>", name: <anzeige>}`, je HA-Benutzer, **der reingehört hat**, `{wer: "benutzer:<id>", name: <Name aus Home Assistant>}`; die Namen kommen nie aus dem Repo). Fehler `wer_ungueltig` bei unbekannter Box oder unbekanntem Benutzer. Regeln: 12.2.1 |
| `gehoert/zuletzt`, `gehoert/meist` | lesen | `box`, `limit`, `von`, `bis` → Einträge mit Zeit bzw. Sekunden |
| `favorit/set`, `favoriten/list` | **Alltag** / lesen | `serie_id`, `folge` (optional), `an` → Liste |
| `technik/verlauf` | admin | `box`, `von`, `bis` → Akku (Statistik), Ladezeiten, Laufzeit je Ladung, Syncs, Fehler |
| `gehoert/exportieren`, `gehoert/loeschen` | admin | CSV bzw. alles löschen (mit Bestätigungswort); betrifft **nur die Boxen-Daten**; in „Technik“ steht dafür „Alle Hördaten der Boxen löschen“ |
| `reinhoer/loeschen` (Rev. 4a) | **Alltag** (eigene); **admin** mit `alle` | Ohne `alle` löscht es die **eigenen** Reinhör-Daten (Rückfrage in der Seite). Mit `alle: true` löscht ein Administrator alle Reinhör-Daten (Rückfrage). Ein Nicht-Administrator löscht nie fremde Daten |

**Aufrufe der Seite (5.10):** Rangliste für die Auswahl: `wer=<Auswahl>`, `nach=["serie"]`. Aufteilung nach Folgen: `serie_id`, `nach=["folge"]`. Das Säulendiagramm: `nach=["tag"]` (die Tabelle darunter bei „Alle“: `nach=["tag","wer"]`), die Tageszeiten `nach=["stunde"]`. Die Auswahl selbst kommt aus `wer_auswahl`.

`serien/list` und `folgen/list` bekommen die Sortierungen `zuletzt_gehoert`, `meist_gehoert` und den Filter `favorit` (nur mit Fähigkeit `gehoert`). Hördaten der Boxen sind lesbar für alle HA-Benutzer (Frage 8); Reinhör-Daten ebenso für alle, gewählt mit `wer` (12.5, Frage 23). Fähigkeit **`gehoert_reinhoeren`** (die Personen in der Auswahl „Wer?“ und der Knopf „Meine Reinhör-Daten löschen“ erscheinen nur damit).

### 12.5 Reinhören in „Gehört“ (Rev. 4a, Runde 8 Nr. 21, Frage 23)

**Entscheidung Tobias:** Reinhören wird **doch erfasst**, aber dem **HA-Benutzer** zugeordnet, nicht einer Box.

**Datenquelle (ohne neue Aufrufe der Seite):** Die Hörstellen-Aufrufe (`hoerstelle/set`, 11.4.5) kommen höchstens alle 10 Sekunden während der Wiedergabe und sofort bei Pause, Sprung, Wechsel und Ende. HA leitet daraus **Sitzungen** ab, je Benutzer und Folge: ein offener Zustand mit `start`, `letzte Zeit`, `letzte Position` und `gespielt_s`. Bei jedem Aufruf gilt: `dt` = Sekunden seit dem letzten Aufruf, `dp` = Positionsänderung. Als **gespielt** zählt nur, wenn `0 < dp ≤ 1,5 × dt + 2` **und** `dt ≤ 30` (normale Wiedergabe bis 1,5-fach; Springen und lange Pausen zählen nicht). Die Sitzung endet bei `fertig` (`ende_der_folge`), beim Wechsel der Folge (`anderes`) oder wenn der nächste Aufruf mehr als 5 Minuten später kommt (`pause_lang`). **Gleiche Zählregel wie 12.2.1:** Eine Wiedergabe ist eine Sitzung mit mindestens 10 Sekunden `gespielt_s`; Sitzungen derselben Folge mit höchstens 5 Minuten Lücke zählen als **eine** Wiedergabe; „fertig“ = Ende der Folge; Hörzeit = Summe `gespielt_s`.
**Genauigkeit:** Schließt jemand die Seite, fehlen bis zu 10 Sekunden; das Handy kann die Seite einfrieren (`pagehide` ist nicht verlässlich). Für Hörzeit pro Tag reicht das, die Zahlen sind „etwa“. Die Erfassung beginnt mit Stufe B (Frage 23, Entscheidung Runde 9); frühere Hörstellen-Aufrufe haben keinen Verlauf.

**Die Regel (Frage 23, Entscheidung Tobias in Runde 9):** Alle HA-Benutzer sehen die Reinhör-Daten (Auswahl „Alle“ oder ein Benutzer). Die Empfehlung (nur die eigenen sehen) ist damit verworfen. Die **Hörstelle** bleibt privat (Nr. 16): Sie ist die Stelle zum Weiterhören und wird nie fremd angezeigt. Folge: die Partnerin sieht, was der Administrator am Handy hört, und ein Gäste-Konto sieht es auch. **Löschen:** Jeder löscht seine **eigenen** Reinhör-Daten (`reinhoer/loeschen`, Alltag); Administratoren löschen alle (`alle`, mit Rückfrage, in „Technik“). „Alle Hördaten der Boxen löschen“ in „Technik“ betrifft nur die Boxen.

**Bedienung (Rev. 5, Runde 10; seit Runde 15 als Abschnitt von „Geräte“):** „Gehört“ mit **einer** Auswahl „Wer?“ (5.10, 5.10.1); **kein Umschalter und kein Hinweistext** mehr. Die Namen der Personen kommen aus Home Assistant und stehen nie im Repo. **Löschen:** jeder seine eigenen Reinhör-Daten (`reinhoer/loeschen`, Knopf unten in „Gehört“, Frage 27), **alle** Reinhör-Daten und alle Hördaten der Boxen nur Administratoren, in „Technik“.
**Vertrag (Stufe B):** `gehoert/zusammenfassung` mit `wer` (12.4), `reinhoer/loeschen` (mit `alle` nur Admin), Fähigkeit `gehoert_reinhoeren`; Paket B3 bis B5 (Abschnitt 15.2).

## 13. Stufe C: Playlists, wie bei Spotify (Runde 12, X12)

**Ziel:** Eine Playlist aus beliebigen Folgen und Liedern (auch aus verschiedenen Einträgen) lebt in der **Bibliothek**, wird **wie bei Spotify** bedient und kann das Ziel eines Tobies sein. Gebaut wird sie **erst in Stufe C** (Block C1 bis C5, 15.3); bis dahin ist sie im Prototyp mit dem Etikett „Stufe C – Vorschau“ durchklickbar (Schalter „Stufen zeigen“: „A, dazu B und C“; sonst ausgeblendet). In der echten Seite erscheint sie nur mit der Fähigkeit `playlists`.

### 13.1 Bedienung

* **Anlegen:** In der Bibliothek hat die Arten-Zeile den Unterreiter **„Playlists“** (zwischen „Alle“ und „Hörspiele“; „Alle“ zeigt keine Playlists). Er zeigt die Zählzeile, den Knopf **„+ Neue Playlist“** und die Playlists als Listenzeilen (Cover-Mosaik 72 px, Name, „Playlist · 5 Einträge · 6 Min.“, Tobie-Symbol mit Anzahl). „Neue Playlist“ fragt nur nach dem **Namen** (Blatt, 1 bis 100 Zeichen) und öffnet die leere Playlist-Seite.
* **Hinzufügen:** Bei **jeder Folge und jedem Lied** („⋯“ in der Folgenzeile, im Suchtreffer und auf der Seite eines Einzeltitels) gibt es **„Zur Playlist hinzufügen“**; im „⋯“ eines Eintrags (Album, Hörspiel) hängt es **alle** Folgen an. Es öffnet ein **Blatt** mit der Zeile „**+ Neue Playlist**“ zuerst und darunter allen Playlists (Cover, Name, Anzahl; „schon drin“, wenn die Folge schon dort steht). Tippen auf eine Playlist fügt am **Ende** an („„Hänschen klein“ ist jetzt in „Zum Einschlafen“.“); eine Folge steht höchstens **einmal** je Playlist („Das ist schon in „…“.“), höchstens **200 Einträge** („Die Playlist … ist voll.“). 3 Taps: „⋯“, „Zur Playlist hinzufügen“, Playlist.
* **Playlist-Seite** (`#playlist-<id>`, oben „‹ Bibliothek“, „⋯“ rechts): **Cover-Mosaik aus den ersten vier Covern** (ab vier Einträgen 2 × 2; bei einem bis drei Einträgen das Cover des ersten; leer: Platzhalter), **Name**, „5 Einträge · 6 Min.“ (**Anzahl und Gesamtdauer**), Knopf **„Reinhören“** (spielt der Reihe nach, wie 5.12; „Pause“, wenn sie läuft) und darunter die Karte **„Gespielt von“** (Chips der Tobies, sonst „Noch kein Tobie · Einem Tobie geben …“, 5.4; Runde 16 statt „Tobie zuordnen“). Darunter die Einträge.
* **Einträge:** je Zeile **Ziehgriff** (44 px, links), kleines Cover, Titel, „Serie · Dauer“ (Einzeltitel: „Einzeltitel“); Tippen auf den Titel spielt ab dieser Stelle; rechts das „⋯“ als eigene Fläche (4, X25).
  * **Umsortieren durch Ziehen:** Griff greifen und verschieben (Zeiger, Maus und Touch; am Rand scrollt die Seite mit); beim Loslassen wird gespeichert. **Alternative ohne Ziehen (Barrierefreiheit):** (1) „⋯“ → **„Nach oben“** / **„Nach unten“** (am Ende ausgegraut); (2) am Griff mit **Pfeil hoch/runter** (Tastatur). Ansage: „„X“ ist jetzt Platz 3 von 5.“ (`aria-live`).
  * **Entfernen:** „⋯“ → „**Aus der Playlist entfernen**“ (ohne Rückfrage; die Folge bleibt in der Bibliothek). Dort außerdem „Einem Tobie geben …“, „Nach oben/unten“.
  * **Umbenennen** und **Löschen:** „⋯“ oben rechts → „**Umbenennen**“, abgesetzt „**In den Papierkorb …**“ (Rückfrage mit Namen, nennt Tobies, die dann nichts mehr spielen; „Der Administrator bekommt eine Mitteilung und kann sie zurückholen.“).
* **Leer:** Bild, „Noch nichts in dieser Playlist.“, Knopf „Lied oder Folge suchen“. **Suche:** Playlists haben in der Suche eine eigene Gruppe.
* **Als Tobie-Ziel:** Die Zielwahl „Was soll … spielen?“ (5.4) hat in Stufe C die dritte Auswahl **„Playlist“**; im Regal steht der Name der Playlist (5.7).

### 13.2 Rechte

**Alltag für alle** (anlegen, hinzufügen, umsortieren, entfernen, umbenennen). **Löschen wie bei Serien:** in den Papierkorb (kein endgültiges Löschen), Rückfrage mit Namen, `tobies_bestaetigt` wenn Tobies darauf zeigen, Mitteilung an Administratoren, Wiederherstellen und Leeren nur durch Administratoren (10.3).

### 13.3 Datenmodell (Skizze)

* **Datei `playlists/<id>.json`** im Medienwurzelordner (reservierter Name `playlists`, **wird synchronisiert**, anders als `_…`-Ordner): `{schema_version, id, name, angelegt_am, rev, eintraege: [{serie_id, folge}]}`, höchstens 200 Einträge. `folge` ist der Name der Folge in der Serie (Dateiname oder Ordnername, wie `ziel.folge` in `data-model.md` 2); die Feldnamen werden in C1 an `data-model.md` angeglichen (dort heißt es `ziel.serie`). Eine Datei je Playlist statt Einträgen in `config.json`, damit die Liste unter ihrer 256-KiB-Grenze bleibt. `rev` zählt Änderungen (gegen gleichzeitiges Bearbeiten).
* **Tobie-Ziel:** `config.json` `zuordnungen.<uid>.ziel`: neuer Typ **`typ="playlist"`** mit `ziel.playlist = <id>`. Weil das ein neuer `ziel.typ` ist, den eine alte Box als ungültig ablehnt (`data-model.md` 2: unbekannter `ziel.typ` macht die ganze Liste ungültig), steigt `schema_version` auf **3**, **erst wenn** ein Tobie eine Playlist benutzt. Folge: **Boxen zuerst aktualisieren**, dann die Funktion freischalten (Fähigkeit `playlists`).
* **Einträge sind Folgen** (Einzeltitel sind schon normale Serien mit einer Folge, 11.3.1); die Playlist braucht **kein** zweites Datenmodell für Dateien.

### 13.4 Verhalten auf der Box

Die Box löst die Einträge lokal auf (Serie und Folge gibt es dort, weil die ganze Bibliothek synchronisiert wird), baut die MPD-Warteschlange und **spielt der Reihe nach**. Sie **merkt sich die Stelle wie bei Serien**: Zeiger unter `playlist:<id>` in `resume.json` (`serie_id`, `folge`, Index als Hinweis, Position, Zähler); die Stelle folgt dem **Eintrag**, nicht dem Platz (wird umsortiert, bleibt sie beim selben Lied); fehlt der Eintrag, gilt der Index als Hinweis. Fehlende Einträge überspringt sie (`playlist_eintrag_fehlt`, ohne Abbruch). Fehlt die Playlist-Datei noch (nicht synchronisiert) oder wurde sie gelöscht: wie `serie_fehlt` spielt die Box die Überraschungs-Serie (`playlist_fehlt`). Das Ereignis `gespielt` (B) trägt `playlist=<id>` und den gespielten Eintrag.

### 13.5 Gelöschte Folgen

Kommt eine Folge in den Papierkorb, **bleibt der Eintrag in der Datei**: die Playlist-Seite zeigt ihn ausgegraut mit „Nicht mehr da“ (Menü: nur „Aus der Playlist entfernen“), zählt nicht in Anzahl und Dauer, die Box überspringt ihn. Wird die Folge aus dem Papierkorb **zurückgeholt, ist der Eintrag wieder da**. Wird der Papierkorb **endgültig geleert**, entfernt HA die Einträge aus allen Playlists (Datei neu schreiben, `rev` erhöhen). Wird die ganze Serie gelöscht, gilt dasselbe für alle ihre Folgen. Eine gelöschte Playlist geht in den Papierkorb; Tobies darauf spielen dann die Überraschung (wie bei einer gelöschten Serie, Rückfrage nennt sie vorher).

### 13.6 Sync

Eine neue oder geänderte Playlist kommt erst mit dem **nächsten Abgleich** auf die Box, nicht sofort wie die Liste per MQTT. Die Seite sagt „Die Playlist wird auf die Boxen kopiert“ und zeigt je Box „aktuell“ oder „noch nicht“ (Box-Detailseite, 5.1.2). Änderungen an Titeln brauchen nichts. Gleichzeitiges Bearbeiten: `playlist/eintraege_setzen` trägt `erwartet_rev`; bei Abweichung `stand_veraltet`, die Seite lädt neu; `eintraege_hinzufuegen` hängt nur an und ist unkritisch.

### 13.7 Hochladen und Playlists (entschieden, X12a)

Die Hochlade-Kachel „Playlist“ bzw. „Neue Playlist“ (Rev. 4, Wahl d; Runde 12) **entfällt**: Bei Spotify lädt man nicht in Playlists hoch, man füllt sie aus der Bibliothek. Stattdessen bietet die **Fertig-Karte** unter „Zuletzt hinzugefügt“ (neue Einzeltitel, Alben, Hörbücher) in Stufe C den Knopf **„Zur Playlist hinzufügen“** (Blatt wie 13.1; ein Album hängt alle Lieder an). Folgen: das Blatt „Was lädst du hoch?“ hat **vier** Kacheln (2 × 2) und **keine Kachel „Neue Playlist“**; die Wege bleiben `auto`, `neu`, `ergaenzen`, `einzeln`. **Von Tobias entschieden (X12a, Runde 16).**

### 13.8 Vertragsänderungen (Skizze, nichts in `docs/protocol/` geändert)

`data-model.md` (Playlist-Datei, `ziel.typ="playlist"`, `schema_version` 3), `core-interface.md` 6 (Ziel-Typ, Zeiger, Sync-Regel, `playlist_*`-Ereignisse), `mqtt-v1.md` (Schema-Hinweis, `gespielt` mit `playlist`), `ha-websocket-v1.md`: `playlist/create`, `playlist/rename`, `playlist/list`, `playlist/get`, `playlist/eintraege_hinzufuegen`, `playlist/eintraege_setzen` (mit `erwartet_rev`), `playlist/delete` (Papierkorb); Index und Suche zählen Playlists wie Einträge der Art „Playlist“; Fähigkeit `playlists`. Alles erst im Block C1 (15.3), nach Freigabe.

**Weiterspielen über eine Playlist (Runde 8, Nr. 22):** Reinhören auf einer Playlist spielt die Einträge in ihrer Reihenfolge und geht am Ende eines Titels zum nächsten, auch über Einträge verschiedener Serien (Prototyp: gezeigt). Die Hörstelle bleibt je Folge und Benutzer (11.4.5); neu ist nur die **Warteschlange der Seite** (Quelle „Playlist“); Umsortieren während des Hörens verwirft sie.


## 14. Barrierefreiheit, Gefahrloses (U24)

* **Tap-Ziele:** mindestens 44 × 44 px (im Prototyp bei 390 und 1280 px geprüft; Ausnahme nur Textlinks im Fließtext). **Runde 12, X8: auch alle Listenaktionen**, also „⋯“ (Mehr zu dieser Folge), Abspielen, ▲/▼, ganze Zeilen von Tobies, Kapiteln und „Mehr“ (im Prototyp 48 × 48 px bei Symbolknöpfen, Zeilen 56 bis 84 px), damit man sie **einhändig mit dem Daumen** trifft. **Kontrast:** Text mindestens 4,5:1; **Ränder von Bedienelementen, Symbole, Warn- und Hinweiskarten mindestens 3:1** gegen den Hintergrund (Runde 12, X9; Token `--line`, 2 px Rand in Warnkarten, `--primary-ink` statt `--primary` für Ränder und Striche, Abschnitt 4), in Hell, Dunkel und im Theme mit hellem Primärton. Wo ein Rand fehlt (Karten nur mit Schatten), trägt der Text die Erkennbarkeit; Trennlinien in Listen sind reine Gliederung.
  Farbe nie allein: Zustände haben Text („bitte ansehen“, „fertig“, „Still/Leiser“); Diagramme haben Beschriftung, Zahlen und Tabelle.
* **Listenzeilen (Runde 12, X10):** Eine Zeile mit einer Aktion ist **ein einziger `<button>`** (mindestens 56 px, volle Breite) mit sprechendem Namen (`aria-label` „Gelber Hase bearbeiten“, „Alte Serie wiederherstellen“); der Pfeil „›“ ist `aria-hidden` und `--text2` (mindestens 4,5:1, mehr als die geforderten 3:1), sitzt an fester Stelle am rechten Rand (24 px, vom Text unabhängig); sichtbarer Fokusring (innen, 3 px `--focus`), beim Drücken leichte Hinterlegung (nicht allein Farbe: der Pfeil und der Text bleiben). Zeilen mit **zwei** Aktionen (Abspielen, „⋯“) haben zwei getrennte Symbolknöpfe, je mindestens 44 × 44 px.
* **Dialoge:** das native **`<dialog>` mit `showModal()`** (Esc, Fokusfalle und Hintergrundsperre kostenlos); Fokus beim Öffnen auf die **harmlose** Antwort („Abbrechen“, „Nein, so lassen“); danach zurück zum auslösenden Knopf. Im Shadow DOM prüft man den Fokus mit `getRootNode().activeElement`, nicht `document.activeElement`.
  Wo kein Dialog möglich ist, bekommt der Seitenrahmen `inert`.
* **Screenreader:** ein `aria-live`-Bereich sagt Ergebnisse an („Fertig. Dieser Tobie spielt jetzt Lange Serie“); die **Fertig-Karte erhält den Fokus**, wenn sie die Karte ersetzt (`aria-live` allein genügt Tastaturnutzern nicht, 24c). Fortschrittsbalken `role="progressbar"`; Cover `aria-hidden` (der Name steht daneben);
  Tag-Knöpfe `aria-pressed`; Zählzeile der Bibliothek `aria-live="polite"`; Reiter-Zahl „1 neuer Tobie“ als Text (24e). **Reiter (Runde 12, 15):** die Leiste ist `<nav aria-label="Bereiche">`, der aktive Reiter trägt `aria-current="page"`, auch wenn eine Unterseite (Box-Detailseite, Technik-Unterseite) offen ist; die Zeilen der Technik-Liste sind echte Links (Titel = Name, Erklärung = Beschreibung).
* **Schriftgröße:** alles in `rem`; bleibt bei 200 % Zoom und bei 320 px benutzbar (Kacheln brechen um, kein waagerechtes Scrollen). **Reiterschrift 14 px (Runde 12, X2; Untergrenze 13 px)**; bei Systemschrift „groß“ bricht der Reiter „Bibliothek“ nicht, weil die Beschriftung kurz ist und bei vier Reitern 97 px je Reiter zur Verfügung stehen (24d); bei 200 % Zoom oder 320 px darf die Beschriftung auf zwei Zeilen umbrechen, nie abgeschnitten werden.
* **Bewegung:** `prefers-reduced-motion`: kein Pulsieren, keine Übergänge. **Wischen (Runde 12, X6):** nur eine zweite Möglichkeit neben den Knöpfen; wer nicht wischen kann, tippt die Leiste an und schließt mit dem Knopf oder Esc. Die Wischschwelle verhindert versehentliches Öffnen beim Scrollen. **Sprache:** Uhrzeiten 24 Stunden, Datum „12.11., 08:30“, unabhängig von der Browsersprache.
* **Löschen:** nur mit Rückfrage und rot; die Rückfrage sagt, was geschieht und was bleibt. Löschknöpfe stehen **nie in einer Reihe mit häufigen Knöpfen** (eigene Karte oder Blattende, durch Linie und mindestens 32 px abgesetzt). „Rückgängig“ statt Rückfrage dort, wo es sich zurückdrehen lässt (Zuordnen, Umstellen).
* **Reihenfolge ohne Ziehen:** ▲/▼ (nur Administratoren); der Fokus bleibt auf dem Knopf der verschobenen Folge. **Foto zuschneiden ohne Ziehen:** vier Pfeilknöpfe und Regler.
* **Player (Rev. 3):** Die Vollansicht ist ein natives `<dialog>` (Esc schließt, Fokus beim Öffnen auf Play/Pause, danach zurück auf die Leiste). Die Zeitleiste ist ein Schieberegler mit `aria-valuetext` („1:41 von 2:47“); alle Knöpfe 44 px oder mehr, Play 72 px; Geschwindigkeit als Knopfgruppe mit `aria-pressed`;
  Symbol-Knöpfe haben Namen („30 Sekunden zurück“, „Nächste Folge“). Die Leiste unten ist ein Knopf mit Namen „Player öffnen: <Titel>, <Eintrag>“. Es wird **nie von selbst Ton gestartet** (nur nach Tap); Tastatur: Leertaste = Play/Pause im Dialog. Fortschrittsbalken in Listen haben `role="progressbar"` mit Wert; Farbe nie allein (Text „noch 18 Min.“ / „Fertig gehört“).
* **Meldungen (Runde 12, X7):** Erfolg `role="status"` (höflich, verschwindet nach 4,5 s, das reicht, weil das Ergebnis auch in der Seite steht); Fehler `role="alert"`, mit „OK“-Knopf (44 px), bleiben, bis bestätigt oder weggewischt; der Fokus bleibt, wo er war. Über einem offenen Blatt zieht der Meldungsbereich in das Blatt um (6.3), sonst wäre er verdeckt und nicht bedienbar.
* **Leere Zustände (Runde 12, X3):** Bild `aria-hidden`, der Satz steht als normaler Text, der Knopf ist ein echter Knopf oder Link (44 px); keine Information steckt nur im Bild.
* **Doppeltippen:** Knöpfe, die etwas senden, sind während des Aufrufs gesperrt (`anfrage_id`).
* **Hochladen (Rev. 4, Runde 12 X5):** Das Blatt „Was lädst du hoch?“ ist ein natives `<dialog>` (Esc, Fokus zurück auf „Dateien wählen“; „Abbrechen“ steht **oben rechts** im Blatt, 44 px, damit es am Handy nie unter der Kante liegt); die vier **Kacheln** sind echte Knöpfe (mindestens 132 px hoch, Titel und Zeile darunter sichtbar, der ausführliche Satz der Rev. 4 als nur für Screenreader sichtbarer Text im Namen; das Symbol ist `aria-hidden`). Zwischen den Schritten wechselt nur der Inhalt des Blatts; der Fokus geht auf die Überschrift, nicht auf ein Textfeld (am Handy würde sonst die Tastatur aufgehen). Der Satz der Vorschau ist ein `role="status"`-Bereich (`aria-live="polite"`) und ändert sich beim Tippen. Art-Auswahl als Knopfgruppe mit `aria-pressed`.
* **Kapitelliste (Rev. 4):** Zeilen sind Knöpfe (mindestens 56 px) mit Namen „Kapitel 4: Der Sturm, ab 1:12, aktuelles Kapitel, abspielen“; das aktuelle Kapitel hat `aria-current="true"` und eine getönte Fläche **und** den Text „hier weiter“ bzw. „läuft“ (Farbe nie allein); schon gehörte tragen Häkchen **und** den Text „gehört“. Im Player-Blatt öffnet der Fokus auf dem aktuellen Kapitel.
* **Auswahl „Wer?“ (Rev. 5, ersetzt den Umschalter Boxen | Reinhören):** Knopfgruppe mit sichtbarer Beschriftung „Wer?“ (`aria-labelledby`) und `aria-pressed`, jeder Knopf mindestens 44 px hoch, bricht bei vielen Benutzern um; die Rangliste nennt die Auswahl im Text („Alle zusammen · in der letzten Woche“), das Diagramm hat sie in `aria-label` und Tabelle.

* **Runde 12 bis 15 (Ergänzungen):** **Playlist-Seite:** Ziehgriff ist ein Knopf mit Namen „<Titel> verschieben, Platz 2 von 5. Mit den Pfeiltasten nach oben oder unten bewegen.“ (Pfeiltasten bewegen, Ansage im `aria-live`-Bereich), dazu die Menü-Alternative „Nach oben/Nach unten“; ausgegraute Einträge sagen „Nicht mehr da“ als Text. **Wochenansicht (X26):** jeder Abschnitt ein Knopf mit Namen („Mo, 19:30 bis 6:30, still, bearbeiten“), Satz „Jetzt: …“ als `role="status"`, Marke „jetzt“ `aria-hidden`, Legende zusätzlich als Text; Muster statt nur Farbe. **Player-Sperre (X14):** gesperrte Bedienelemente `disabled`, der Entsperr-Knopf nennt „Entsperren: 2 Sekunden gedrückt halten“ und ist mit Tastatur (Leertaste oder Eingabe halten) bedienbar; `aria-live` sagt „Gesperrt“ und „Entsperrt“. **Suchvorschläge (X16):** `role="listbox"` mit Optionen, 48 px. **Endloses Nachladen (X23):** der Knopf „Mehr laden“ bleibt als Rückfall, `aria-live` „Weitere Einträge geladen.“ **Reiter „Geräte“ (X28):** der Punkt trägt den Text „1 neuer Tobie“. **Seitenleiste (X24):** `<nav aria-label="Bereiche">` bleibt, `aria-current="page"` am aktiven Reiter. **Zeitfelder (X22):** `<label for>` und System-Zeitwähler.

## 15. Arbeitspakete (Sonnet, billigstes passendes Modell)

Regeln: Vor dem Bau Resolve mit Tobias. Jedes Paket hat eigene Tests und ist allein lauffähig. **Die bestehenden Tests** (`homeassistant/tests/frontend/`: 121 Tests der alten Seite; `homeassistant/tests` mit `pytest`; `box/tests`) müssen nach **jedem** Paket grün sein. Sie werden **nur nach einer Entscheidung in A0 geändert** (Rev. 4 sagte „nicht angepasst“; G11): Rev. 5 ändert **keinen** bestehenden Test, außer `test_init.py` in A17 (`require_admin`, Adressen). Die alte Seite behält Datei und Elementnamen (5.9, G12).
**Stufe A läuft in drei Teilen** (Entscheidung Tobias, Runde 10): A-1 Alltag, A-2 Reinhören, A-3 Hörkopien und Kapitel, **jeder mit eigener Abnahme** im Chat, Schritt für Schritt (CLAUDE.md). Ein Teil beginnt erst nach der Abnahme des vorigen. Eine fehlerhafte Stelle in A-2 oder A-3 hält die Seite für die Partnerin nicht mehr zurück, weil sie nach A-1 schon läuft (A17).
**Reihenfolge der Backend-Pakete ist streng nacheinander** (G13b): Sie ändern alle `media.py`, `eingang.py`, `hub.py` und `websocket_api.py`; parallele Agents erzeugten Zusammenführungskonflikte. Parallel laufen nur Pakete mit getrennten Dateien (A4b, A5, A15, später die Seitenpakete A7 bis A13 untereinander nach A6).

### 15.1 Stufe A (wird gebaut)

**Abhängigkeiten (Pfeil = „braucht zuerst“):**

```
A0 (Vertrag, Freigabe Tobias)  ──►  A1 ─► A2 ─► A3 ─► A3d ─► A4 ─► A4b ─► A5 ─► A6 ─► A6b ─► A7, A8, A9, A10, A11a/b, A12, A13 ─► A14 ─► A15 ─► A16-1 ─► A17
A0b (Testpanel, Messungen)  ──► (Konstanten für A-2 und A-3; Nabu Casa vor A3d: Grenze 2 GiB)
A-1 abgenommen ─► A3b ─► A4c ─► A4d ─► A8b (+ A7b, A8c) ─► A14b ─► A16-2
A-2 abgenommen ─► A3b3 ─► A3c ─► A4c3 ─► A8d ─► A3e ─► A11c ─► A16-3
```

**Vor allem anderen (G13a, G19a):**

| AP | Inhalt | Modell | Tests / Ergebnis |
|---|---|---|---|
| **A0** | **Vertrag W und Datenmodell zuerst** (nicht „zusammen mit A1“, Rev. 4 widersprach sich): Eintrag „Änderung 12.11.“, Abschnitt 2.1 ersetzen, W-19 streichen, Abschnitt 8 (2 GiB, Reserve, vier Abnahmegrößen), 5.1 (`gruppe_anzahl`, `name` 400 Bytes), V-1 bis V-9 mit allen Befehlen, Feldern, Fähigkeiten und Codes (11), `serie.json` und Store `tobibox.medieninfo`, reservierte Dateinamen, Liste der „etwas geändert“-Prüfungen für `einsortierung/neu`. **Vertragsentwurf, Freigabe durch Tobias**, erst dann Code (CLAUDE.md: Agents ändern Verträge nicht eigenmächtig) | Sonnet | Vertragstest „alte Antworten bleiben gültig“ (G13d): alle Felder des heutigen Vertrags W bleiben in `serien/list`, `serie/get`, `eingang/list` (mit und ohne `limit`) |
| **A0b** | **Testpanel und Messungen** (G19a, ersetzt A15b als Erstes): 50-Zeilen-Panel unter `/tobibox-neu` mit nur `<audio>` und signiertem Pfad (24 Stunden, `audio/bereit` als Attrappe), Foto-Auswahl, Tastatur, Safe Area. **Tobias misst:** (1) Companion-App iOS und Android: Reiter unten, Safe Area, Tastatur, Foto; (2) `<audio>` bei **gesperrtem Bildschirm** (Dauer 5 Minuten und über 1 Stunde) und **Ordner-Folge** (Trackwechsel); (3) `ffmpeg -version`, `-encoders \| grep aac` und die **Zeit für 10 Minuten Audio** auf Tobias’ HA (bestimmt Zeitgrenze und Schlange, 11.4.7); (4) Springen auf dem NAS-Pfad; (5) Upload mit **20 MiB, 150 MiB, 500 MiB und 2 GiB** über Nabu Casa mit gemessener Dauer; (6) Formate auf iPhone und Mac-Safari | Tobias (Anleitung von Haiku) | Messwerte in `docs/plan/`; Konstanten in 11.4.7 werden danach festgelegt |

**A-1 Alltag** (ohne Player, ohne Hörstellen, ohne Dauer, Kapitel und Hörkopien; Untertitel „Hörspiel · 12 Folgen“):

| AP | Inhalt | Modell | Tests |
|---|---|---|---|
| A1 | **Rechte und Schutz** (10): `befehl(recht=…)`, Tabelle 10.2 (jetzt mit `folgen/order`, `hoerstelle/*`), Schutz 10.3 (`erwartet_ziel`, bekannte Kennungen, Mengen mit 16 GiB, `erwartet_revision`, Zeitzone ignorieren, `sofort` nur Admin, Überraschungs-Serie als Ziel nur Admin), **Papierkorb: Mitteilung, Protokoll, `papierkorb/restore_letzte_stunde`**, `boxen/list`/`export_lesen` nur Admin, 10 frühere Stände, Upload ohne `require_admin`, **`stand` rechnet nur über Name, Folgenliste und menschliche Felder**. **`require_admin` bleibt `True`** | Sonnet | Tabelle 10.2 als Parametertest (Admin und Normal-Benutzer je Befehl, **jeder Befehl der Vertragsübersicht ist in einer Zeile**); Schutzfälle einzeln; `test_services.py`: jede Aktion als Nicht-Admin = `Unauthorized`; `test_upload.py`: Nicht-Admin 200; Mitteilung bei 4 Löschungen oder Eintrag mit Tobies; „Letzte Stunde“ holt genau diese zurück; `folge/verschieben` in die Überraschungs-Serie als Nicht-Admin = `ziel_ungueltig` |
| A2 | **Anzeigenamen** (V-3): Textfeld in Optionen, `strings.json`, `translations/de.json`, `anzeige`, `hello.box_anzeigen` | Haiku + Sonnet | `test_config_flow.py`, Reihenfolge der Rückfälle |
| A3 | **Art und Bibliothek-Backend** (V-2): Art-Vorschlag, `serien/list` erweitert (`einzeln`, Filter `sammlung`/`einzeln`, vorhandene Namen `anzahl_folgen`/`anzahl_tobies`), `folgen/list`, `serie/art_setzen`, `zuordnung/list` mit `text`/`neu`, Index (Einzeltitel als Serie **und** als Folge) | Sonnet | Art-Regeln mit Tag-Fixtures; Suche, Filter, Sortieren, Blättern; **Leistungstest 600 Einträge / 2 000 Folgen < 200 ms** (dazu 300 Einzeltitel); alte Aufrufe ohne `limit` unverändert |
| A3d | **Hochladen mit Wunsch und Einzeltitel** (V-7, V-8) **ohne** `einsortierung/neu`: Felder `ziel`, `art`, `name` (400 Bytes), **`gruppe_anzahl`** (der Eingang wartet auf alle, 30 Minuten Ruhe → `teilweise`), Regeln `neu`/`ergaenzen`/`einzeln`/`auto`, `wunsch` in `eingang/list`; **Upload 2 GiB** (Vorgabe, bestehenden Eintrag anheben, Reserve 2 GiB, laufende Zwischendateien abziehen) | Sonnet | `test_eingang.py`, `test_upload.py`: 12 Dateien gleiches Album: `neu`+`hoerbuch` = **eine** Folge mit 12 Tracks, `neu`+`musik` = **12** Folgen; **drei Dateien im Abstand von 60 s bleiben eine Gruppe (G2)**; letzte Datei fehlt → `teilweise` nach 30 Minuten; `neu` mit mehreren Dateien ohne `gruppe_anzahl` = `wunsch_ungueltig`; ohne `ziel` alle bisherigen Testfälle T1 bis T17 unverändert; 2-GiB-Datei (sparse) wird angenommen, zwei parallele bei Platz für eine: zweite `kein_speicher`; Name mit 100 Emojis (400 Bytes) nicht abgeschnitten |
| A4 | **Cover-Backend** (V-1, 5.5): `cover_pruefen_und_skalieren` (Kopf zuerst, Zähler, Pixelzahl), Extraktion mit Marke im Store, Nachholen im Hintergrund, `ffmpeg` fehlt, GET/POST/DELETE, 20 je Stunde, `cover/neu_suchen`, `"requirements": ["Pillow"]`, mitgeliefertes `cover.jpg` wird **kopiert** | Sonnet | `tests/test_cover.py`: MP3 mit/ohne Bild, kaputtes Bild, **Pixelbombe (3-MiB-JPEG mit 30 000 × 30 000 px)**, **3-MiB-Grenze ohne `Content-Length`**, CMYK und progressiv, PNG mit JPEG-Endung, präpariertes `APIC`, Marke, Zeitgrenze, Foto-Upload, Original wird nicht gespeichert, ETag; **Zusammenführen, Wiederherstellen, Umbenennen** (G11); `test_reste_kommen_in_den_papierkorb_…` bleibt unverändert grün |
| A4b | **Sync-Ausschluss** `cover*.jpg`, `cover*.png`, `folder.jpg` in `box/src/tobibox/sync.py` | Sonnet | `box/tests`: Sync mit Covern überträgt sie nicht, übrige Dateien unverändert |
| A5 | **Texte** `texte.js` (nach A0, G13c): Fehlertabelle (6.1), Gründe (7.3), Sätze (5.1.1), Eintrag `verwalter`, **Texte der leeren Zustände (6.2), der „Mehr“-Zeilen (3.4) und der Kacheln beim Hochladen (5.6: Titel, Zeile, Satz für Screenreader)** | Haiku + Sonnet-Review | jeder Code der Vertragstabelle hat einen Text; Texte wörtlich wie hier |
| A6 | **Panel-Gerüst** (neue Dateien `tobibox-app.js`): **vier Reiter (Start · Bibliothek · Tobies · Geräte, 14 px, 64 px hoch; Seitenleiste ab 900 px, X24; Pille und Glas mit Rückfall, X18/X19) und Geräte-Seite** (3.4: Box-Karten, „Neuer Tobie aufgelegt“ mit Punkt am Reiter, Abends, „Gehört“ nur mit Fähigkeit `gehoert`) und rundes Technik-Symbol (`narrow`, sticky, `visualViewport`), **Mini-Player bündig auf der Reiterleiste (X31: 0 px Abstand, auch mit Safe-Area; die Höhe der Leiste wird gemessen und als `--navh` gesetzt; ab 900 px bündig am unteren Rand des Inhalts)**, Routen (`#geraete`; `#mehr`, `#abends`, `#gehoert` führen dorthin), Token (**`--line`, `--r-card` 16 px, `--r-big` 24 px**, Ränder und Striche mit `--primary-ink`) und Kontrastfunktion, Zustände, `<dialog>`-Blatt, **Meldungen nach 6.3 (Erfolg 4,5 s weg, Fehler mit „OK“ und Wegwischen, Umzug in offene Blätter)**; **alte Komponente unverändert, nur Attribut `eingebettet`**; Panel `/tobibox-neu` (Admin) neben `/tobibox`; Option „Alltagsseite für alle Benutzer“ | Sonnet | jsdom: **vier Reiter, „Geräte“ für Nicht-Admin mit „Abends“**, Routen (`#abends` markiert „Mehr“; `#gehoert` ohne Fähigkeit → `#mehr`), Nicht-Admin ohne Technik-Knopf, Fokus nach Dialog; **Fehlermeldung bleibt (Zeit vorstellen), Erfolg geht nach 4,5 s, Umzug in ein offenes `<dialog>`**; **alte 121 Tests unverändert grün** |
| **A6b** | **Illustrationen und leere Zustände** (neu, Runde 12, X3; klein): sechs Inline-SVG-Bilder aus dem Prototyp v6 (`ILLU`) in eine Datei `bilder.js`, Baustein `leerKarte(art, satz, knopf)` (6.2); nur Token-Farben | Haiku (Sonnet prüft) | jsdom: jede der sechs Arten zeigt Bild (`aria-hidden`), **einen** Satz und einen Knopf; Datei enthält **keinen** Farbwert (`#…`, `rgb(`), nur `var(--…)`; Suchbegriff wird als Text eingesetzt (kein HTML); Screenshots Hell, Dunkel, Theme mit hellem Primärton von Tobias gesichtet |
| A7 | **Start (Schaufenster, X27: Begrüßung, Schnellzugriff 2 × 3, Reihen mit Vermerk der Stufe, fehlende Reihen weg) und Bibliothek ohne die Reihen „Am Handy weiterhören“ und „Neu hinzugefügt“ (X27a: nur auf dem Start)** (Kopf mit „+“ und Band für laufende Uploads, X29; endloses Nachladen, X23; Suchvorschläge, Tobies zuerst, X16): Arten-Zeile, Listenzeilen (Tobie-Symbol, Einzeltitel „Lied · einzeln“), Blatt „Sortieren und Filter“ (mit „Was zeigen“), Suchansicht (3 Gruppen, **Zeilen sind Links**), Cover-Laden, Blättern; **leere Zustände Bibliothek, Filter ohne Treffer, Suche ohne Treffer und „keine Box“ (6.2)**; Listenaktionen mindestens 44 × 44 px | Sonnet | jsdom wie bisher; Suchtreffer-Zeile verlinkt auf die Serienseite bzw. den Einzeltitel |
| A7b | **Geräte** (3.4, 5.1.1, 5.1.2, 5.8): Box-Karten (Status-Sätze) als Links, **Box-Detailseite** (für Administratoren mit den Technik-Details der Box), Abschnitt „Abends“ mit Gute Nacht und **Leise-Zeiten als Wochenansicht** (Zeitleisten, Mitternachtsfall, Satz „Jetzt“, Marke, Zeitfelder `type=time step=300`), Abschnitt „Gehört“ (B5) | Sonnet | jsdom: Karte → Detailseite, Nicht-Administrator ohne Technik-Teil; Wochenansicht: Abschnitte je Tag, So 19:30–6:30 füllt Mo bis 6:30, Satz „Jetzt“ je Lage, Tippfläche ≥ 44 px; Playwright: kein waagerechtes Scrollen bei 390 px |
| A8 | **Serienseite ohne Player**: Kopf, Karte „Gespielt von“ / „Noch kein Tobie · Einem Tobie geben …“ (Runde 16), Menüs, Name/Art/Cover ändern, „Das ist richtig/stimmt nicht“, Folgenliste, Papierkorb, Einzeltitel-Seite | Sonnet | jsdom: Menü der Folge „Einem Tobie geben …“ führt zu `#geben-<serie>~<nr>`, Zuschneiden (Canvas-Mock), Löschen mit `tobies_bestaetigt`; Einzeltitel ohne Folgenliste, Ziel `folge` |
| A8c | **Player-Erweiterungen** (X14): „Sperren“, Entsperren durch 2 Sekunden Halten (Zeiger und Tastatur), Geschwindigkeit im „⋯“ | Sonnet | jsdom: gesperrt = alle Bedienelemente `disabled`, Esc und Wischen schließen nicht; 1,9 s Halten entsperrt nicht, 2 s entsperrt |
| A9, A10 | **Tobies als Regal und Zuordnen (Runde 16, X20; 5.4, 5.7, 7.1):** Reiter „Tobies“ mit Kachel „+ Neuer Tobie“, Kacheln mit Ziel und Serienname, „Was soll … spielen?“ (Zielwahl, Namen ändern, vergessen), „Neuer Tobie“ Weg 1 (jetzt auflegen) und Weg 2 (später, Box wählen), „Welcher Tobie soll das spielen?“ aus der Bibliothek, „Gespielt von“-Chips (Serien-, Playlist- und Folgenzeile), Meldung mit „Rückgängig“ (~6 s), Karte „Neuer Tobie auf Box 1 – was soll er spielen?“ nur in „Geräte“ (Punkt am Reiter), leerer Zustand (6.2); Lernmodus-Seite „Tobie anlernen“ nur für Administratoren in „Technik“ | Sonnet | jsdom: Weg 1 (Warten, erkannt, Ziel, Regal), Weg 2 (Vormerken, Auflegen, zugeordnet, „Name geben“), Umstellen und „Rückgängig“ stellt das alte Ziel her, `#geben-…` ordnet zu und kehrt zur Serie zurück, Bibliothek ohne Zuordnen-Knopf, „Einem Tobie geben …“ nur ohne Tobie; Playwright wie bei Prototyp v8 |
| A9c | **Warteschlange „Nächster neuer Tobie“** (5.13, Runde 13 X13): zuerst **A0-Q Vertragsentwurf** (dazu **`lernmodus/start` zurück auf `admin`**, X13a; `warteschlange/set`, `list`, `abbrechen`, Ereignis, Fehlercodes; Freigabe Tobias), dann Backend (Speicher in `.storage`, Abgleich im Ereignis `neue_tobies`, FIFO, Höchstzahl 5, Idempotenz, nie bekannte Tobies umhängen), Seite (Weg 2 „Später auflegen“ mit Wartekarte und Knopf „Abbrechen“ im Reiter „Tobies“, Meldung „Name geben“ beim Auflegen, Runde 16), Lernmodus nur noch in „Technik“ und nur für Administratoren | Sonnet | pytest: FIFO bei zwei Einträgen, „irgendeine Box“, bekannter Tobie bleibt unverändert, doppelte Meldung ordnet einmal zu, Ziel gelöscht verwirft, Neustart behält Einträge; jsdom: Karten und Meldungen |
| A11a | **Hinzufügen: Wahl, Vorschau, Hochladen**: vier **Kacheln** (5.6, zwei Spalten, Symbol, Titel, eine Zeile; Radius 24 px; erreicht über das „+“ in der Bibliothek, Band für laufende Uploads, X29), Vorschau in Sätzen, Abbrechen oben rechts, „Welche Art?“, „Wohin soll es?“, `gruppe_anzahl`, „Datei 2 von 3“, „Es fehlt noch eine Datei“, 2 GiB und `datei_zu_gross` mit Zahl und Rat, Warteschlange, Abbruch, Unterbrechung, 413. **Name-Vorschlag aus den Tags im Browser entfällt** (G14: „Daraus ist geworden“ und „Name ändern“ reichen) | Sonnet | jsdom: Karten und Sätze je Weg, `gruppe_anzahl` im Upload, Fortschritt je Datei, Fehlercodes |
| A11b | **Hinzufügen: Eingang-Anbindung** (24-Stunden-Liste, `quelle`, Gründe, NAS-Einträge, „Das stimmt nicht“, „Daraus ist geworden: …“); **ohne** „Anders einsortieren“ (kommt in A-3) | Sonnet | jsdom: Gründe-Texte, „bitte kurz ansehen“, Wiederaufnahme nach Neuladen |
| A12, A13 | **Technik** (Unterseiten Boxen, Speicher und Netz, Liste und Sicherung, Meldungen, Einstellungen, X15; Einbettung, Warnleisten, Frühere Stände, „Cover neu suchen“, Papierkorb mit „gelöscht von“, „Letzte Stunde zurückholen“ und leerem Zustand, Ausblenden-Wert) | Sonnet | `panel_quiet.test.mjs` bleibt; neue jsdom-Tests |
| A14 | **Playwright-Skript (Pflicht)** unter `homeassistant/tests/frontend/`: Tap-Ziele ≥ 44 px (**auch Listenaktionen**), kein waagerechtes Scrollen (320, 390, 1280 px), **Text 4,5:1 und Rand/Symbole 3:1** in drei Themes (Hell, Dunkel, Theme mit hellem Primärton; Rolle Admin und Benutzer), Screenshots; Abläufe Hochladen mit mehreren Dateien; **Start → Mehr → Abends, „Gehört“ nur über Mehr, Fehlermeldung bleibt und Erfolg geht nach 4,5 s, sechs leere Zustände sichtbar, Kacheln mit höchstens einer Zeile Erklärung** (der Prototyp-Test `v6` ist die Vorlage) | Sonnet | das Skript; vom Prototyp übernommen |
| A15 | **Doku**: `homeassistant/README.md` (Seite für alle, Namen, Cover, 2 GiB, Papierkorb-Mitteilung und Vorlage fürs Handy, HA-Automation „Neuer Tobie“), `docs/betrieb/` „Für die Partnerin“, Rückweg (Adressen tauschen) | Haiku | Abgleich mit `texte.js` |
| **A16-1** | **Abnahme 1 mit Tobias**, Schritt für Schritt im Chat (Mac, Handy): Neuer Tobie (Weg 1 und Weg 2), Tobie umstellen mit „Rückgängig“, „Einem Tobie geben …“ (Serie, Lied), **Hinzufügen vom Handy mit mehreren Dateien (ein Hörbuch aus 3 Dateien, ein Upload über 500 MiB)**, Einzeltitel, Cover per Foto, **Abends (vom Start und über „Mehr“, mit der Partnerin)**, **Kacheln beim Hochladen (verständlich?)**, **leere Zustände** (Bilder ansehen), **Fehlermeldung bleibt, Erfolg geht**, Papierkorb als Nicht-Admin und Mitteilung, Rechte | Projektleitung + Tobias | – |
| A17 | **Seite für alle öffnen**: Adressen tauschen (`/tobibox` = neue Seite, `/tobibox-alt` = alte, jederzeit zurücktauschbar), `require_admin=False` | Sonnet | `test_init.py`: Panel ohne `require_admin`; Tabelle 10.2 mit Testbenutzer ein letztes Mal |

**A-2 Reinhören mit Weiterhören** (nur Originale in Formaten, die der Browser spielt; Formate ohne Unterstützung zeigen den Rückfalltext, bis A-3 da ist):

| AP | Inhalt | Modell | Tests |
|---|---|---|---|
| A3b | **Dauer** (11.4.4) und Store `tobibox.medieninfo`: `dauer_s`, `spuren_s` beim Einsortieren, Nachholen im Hintergrund (feste Zeitgrenze, Abbruch bei NAS weg, nie beim Öffnen), **Dauerdeckel 48 Stunden**, Plausibilität; Felder in Kurzform und `serie/get`; Listenzeilen zeigen die Dauer | Sonnet | **Hintergrundlauf ändert den `stand` nicht**; Dauer einer MP3 und einer Ordner-Folge; FLAC-Stille (Deckel) ohne `dauer_s`; Nachholen genau einmal |
| A4c | **Audio-Ansicht und `audio/bereit`** (11.4.1, 11.4.2, V-6): `TobiboxAudioView` als `FileResponse`-Unterklasse (Zähler in `prepare()`/`finally`), Zweig **Original**, MIME-Tabelle, `track`, **6 offene Verbindungen**, `audio/bereit` (`bereit`/`fehlt`, signierter Pfad 24 Stunden), Fähigkeit `reinhoeren` | Sonnet | HA-Testclient: Range 200/206/416; 401 ohne Anmeldung und mit fremder Signatur; **`..`, `%2e%2e`, `%2F`, unbekannte Serie oder Folge, Symlink hinaus, Ordner statt Datei, Endung `.txt`, Papierkorb/Eingang/`hoerkopien/` als Serie: alle 404**; **Namen „Teil 1 #2 (Ende)?.mp3“, „100% Mond+Sterne.mp3“, Umlaute, Klammern, führender Punkt** durch die Signatur; **langsam lesender Client: siebte Verbindung 429**; NAS weg 503 |
| A4d | **Hörstelle** (11.4.5): `Store` mit 60 s Verzögerung, `get`/`set`/`liste`, `dauer_s` aus dem Store, Drosselung, Aufräumen, Sortierung `angehoert` | Sonnet | zwei Benutzer sehen nie die Daten des anderen (auch kein Administrator); Prüfungen; gesendetes `dauer_s` wird ignoriert, wenn bekannt; Store überlebt Neustart |
| A8b | **Player** (5.12): **Wischen nach oben öffnet, nach unten schließt (Pointer-Events mit Schwelle, Knopf bleibt, 6.3/14)**, `<audio>`, **`audio/bereit` vor jedem Start und nach jedem Fehler**, Link erneuern bei jedem Start und nach 20 Stunden (kein 401), nächste Folge im Voraus, Ordner-Folgen über Tracks, Leiste, Vollansicht, ±30 s, Tempo, Hörstelle gesammelt speichern, `canPlayType`, Media-Session, `encodeURIComponent` je Segment | Sonnet | jsdom mit gemocktem `HTMLMediaElement`; **Playwright mit echtem Chromium und einer Testdatei** (jsdom spielt nichts und kennt `MediaError` nicht, G3); **Wischgeste mit `page.mouse` und per CDP-Touch (öffnen, schließen, unter der Schwelle nichts, Regler zieht nicht zu)**: Fehler 401/503 führen zu neuem `audio/bereit`, nie zu „Format“-Text; Sonderzeichen-Namen |
| A7b, A8c | **Reihe „Am Handy weiterhören“**, Knopf „Hier weiterhören“ mit Satz „Das spielt hier am Handy, nicht auf der Box.“, Fortschritt in Liste und Folgenzeilen, Sortierung „Zuletzt angehört“ | Sonnet | jsdom: Beschriftung je Hörstelle; Test mit der Partnerin in der Abnahme (G17) |
| A14b | Playwright: Suche → Serie → Reinhören → Springen → **Wischen (Mini → Vollansicht → zu)** → Neuladen → Weiterhören an der Stelle | Sonnet | das Skript |
| **A16-2** | **Abnahme 2 mit Tobias**: Reinhören am Handy und am Mac, **Stelle am Handy merken und am Mac weiterhören**, Springen, Folgenwechsel, Ordner-Folge, **gesperrtes Handy und Trackwechsel als erster Test** (G18), kein „Login attempt failed“ im Log nach einem Tag Benutzung | Projektleitung + Tobias | – |

**A-3 Hörkopien und Kapitel:**

| AP | Inhalt | Modell | Tests |
|---|---|---|---|
| A3b3 | **Kapitel und Codecs** (11.4.4, 11.4.8): `ffprobe -show_chapters`, `kapitel`, `codecs` je Track im Store, `kapitel_anzahl` in der Kurzform, Nachholen im selben Lauf | Sonnet | Kapitel aus M4B und MP3 (ID3v2 `CHAP`) mit `ffmpeg`-Fixture, aus Tracks, doppelte Startzeiten, über 500; `test_ffprobe.py` bleibt grün; Box liest `serie.json` unverändert |
| A3c | **Hörkopie** (11.4.7, V-9): `braucht_hoerkopie(codec)` je Track, Warteschlange mit **allen Grenzen** (Dauerdeckel, feste Zeitgrenze, `-t`, `-fs`, Plausibilität, 20 Dateien/50 GB, Kontingent 100 GB, Vorziehen je Benutzer eine), `-ac 2 -map 0:a:0`, Ordner `hoerkopien/`, Aufräumen, `hoerkopie/neu_erzeugen`; **neu Einsortiertes sofort, Bestand erst auf Anforderung** | Sonnet | **FLAC-Stille 2 Stunden: keine Kopie, Grund `zu_lang`/`unplausibel`**; Mehrkanal → Stereo; `-fs` bricht ab; 21. Datei `hoerkopie_warteschlange_voll`; ein Benutzer kann nur eine Datei vorziehen; OGG, Opus, FLAC, WAV, ALAC: Kopie ist AAC/M4A mit gleicher Dauer; MP3/AAC keine; Fehler wiederholt nicht; `*.part` weg beim Start; kein `ffmpeg` → keine Fähigkeit, kein Fehler |
| A4c3 | **Audio-Ansicht: Zweig Kopie** (Wurzel `hoerkopien/`, Pfad nur aus `serie_id` und `kennung`), `audio/bereit` mit `wird_vorbereitet` | Sonnet | Kopie einer Serie ist über **keine andere `serie_id`** erreichbar; OGG-Folge: erst `wird_vorbereitet`, nach der Kopie 206 mit `audio/mp4` und `X-Tobibox-Quelle: kopie`, Range auf der Kopie |
| A8d | **Seite**: Abschnitt „Kapitel“, Kapitelzeile und Blatt im Player, Sprung, Karte „Die Hörprobe wird vorbereitet“ mit Nachfrage alle 15 s, Technik-Karte (Zähler, Fehlergründe) | Sonnet | jsdom: Kapitelsprung setzt Zeit bzw. Track; `wird_vorbereitet` zeigt den Satz und fragt neu; Playwright mit echtem Ton |
| A3e, A11c | **„Anders einsortieren“** (`einsortierung/neu`, V-7): **Machbarkeit zuerst prüfen** (Rückfall Frage 25: nur Papierkorb und neu hochladen), nur `pruefen=true` oder jünger als 24 Stunden, zählt als Papierkorb-Aktion, Ruhezeit; Seite: Blatt „Was ist das?“, Knopf „Neu einsortieren“ | Sonnet | nur solange unverändert; ältere Einträge ohne `pruefen` → `neu_einsortieren_nicht_moeglich`; Papierkorb-Zähler; Ruhezeit |
| **A16-3** | **Abnahme 3 mit Tobias**: Hörprobe eines OGG im Bestand (Wartezeit messen), neu hochgeladenes OGG sofort, Hörbuch mit Kapiteln, Ordner-Folge, Plausibilitätsfall, Technik-Zähler, „Anders einsortieren“ (falls machbar) | Projektleitung + Tobias | – |

### 15.2 Stufe B (eigener Block, nach Freigabe)

| AP | Inhalt | Vertragsänderung |
|---|---|---|
| B1 | **Vertrag** `mqtt-v1.md`: `gespielt`, `gehoert_quittung` (12.2); `ha-websocket-v1.md`: Befehle und Fähigkeit `gehoert` (12.4, mit `wer`); `data-model.md`: `gehoert.jsonl` der Box | ja |
| B2 | **Box:** Sitzungserkennung, Puffer `gehoert.jsonl` (Schreibbudget), Senden und Quittung | `mqtt-v1` |
| B3 | **HA:** SQLite-Speicher (Spalten und Indizes 12.3, mit `wiedergabe` und der Tabelle `reinhoer_sitzungen`), Aufnahme mit Doppelerkennung, Quittung, Technik-Ereignisse, Favoriten; **Sitzungsableitung aus `hoerstelle/set` (12.5)**; Test der Zählregel 12.2.1 und der Ableitung | – |
| B4 | **HA-Befehle** `gehoert/*` (`zusammenfassung` mit **`wer`**, `nach` mit `wer`, `wer_auswahl`), `favorit/*`, `technik/verlauf`, `reinhoer/loeschen`, Sortierungen und Filter; Test: Reinhör-Daten sind für alle lesbar; `wer=benutzer:<id>`, `wer=box:<id>`, `wer=alle` rechnen richtig (Summe = Teile); `reinhoer/loeschen` ohne `alle` löscht nur die eigenen, mit `alle` nur Administratoren; die Hörstelle bleibt nur die eigene | `ha-websocket` |
| B5 | **Seite:** „Gehört“ als Abschnitt der Seite „Geräte“ (Eintrag nur mit Fähigkeit `gehoert`; Auswahl **Wer?**, Rangliste mit Aufteilung nach Folgen, SVG-Diagramme), Stern, Sortierungen, Technik-Karten (Akku-Verlauf, Alle Reinhör-Daten löschen) | – |
| B6 | **Abnahme** mit Tobias (Box im Hörbetrieb, offline hören und danach verbinden) | – |

### 15.3 Stufe C (eigener Block, später)

C1 Verträge (`data-model`, `core-interface`, `mqtt-v1` Schema-Hinweis, `ha-websocket` `playlist/*`) · C2 Box (Ziel-Typ, Zeiger, Sync-Regel, Update) · C3 HA (Befehle, Datei, Index, Papierkorb, gelöschte Folgen 13.5) · C4 Seite (Unterreiter „Playlists“, Playlist-Seite mit Mosaik, Ziehen und Menü-Alternative, Blatt „Zur Playlist hinzufügen“, Zielwahl, „Zur Playlist hinzufügen“ in der Fertig-Karte, Reinhören und Weiterspielen) · C5 Abnahme. Reihenfolge: erst Boxen aktualisieren (Schema 3), dann freischalten.

## 16. Offene Fragen für Tobias (mit Empfehlung)

Fragen 1 bis 13 sind entschieden (`resolve.md`). Fragen 14 bis 22 (Runde 8) und 23 bis 26 (Runde 9) sind **beantwortet**; ebenso die Frage 23a und die Namensregel (Runde 10) und die sechs Fragen des Reviews (`resolve.md`, „Goldfisch-Review Rev. 4a“, unten als „Review 1 bis 6“). **Neu in Rev. 5: nur die Fragen 27 bis 29**, echte Abwägungen mit Empfehlung. **Neu in Runde 16: die Fragen 30 und 31.**

| Nr. | Frage | Empfehlung |
|---|---|---|
| 1 | „Technik“ statt „Für Tobias“, als Knopf oben statt als Reiter (U22)? | Ja: kein Personenname, ein Reiter weniger (4 statt 5, mit „Gehört“ 5 statt 6). **Runde 12 (X1): jetzt immer vier Reiter, „Abends“ und „Gehört“ liegen in „Mehr“.** |
| 2 | Soll die Partnerin einen **Papierkorb-Vorgang selbst rückgängig** machen können (Wiederherstellen nur für das, was sie in den letzten 15 Minuten selbst hineinlegte)? | Nein in Stufe A (Wiederherstellen bleibt Admin); nach den ersten Wochen neu abwägen. |
| 3 | Die letzten **10 Stände der Liste** aufbewahren (U2, Sicherung gegen Fehler mit Folgen für alle)? | Ja, kleines Paket in A1. |
| 4 | **Regeln für den Art-Vorschlag** (11.2): passt das zu deinen Dateien (Genre-Tags, `.m4b`, Albumlänge)? | Fünf Beispieldateien je Art prüfen, bevor A3 fertig ist; Fehlgriffe kann man mit „Art ändern“ beheben. |
| 5 | **`cover*.jpg` nicht auf die Boxen** synchronisieren (U8)? | Ja; ein späteres Display bräuchte eine neue Entscheidung. |
| 6 | **Wochenplan-Grafik** später statt jetzt, **Reihenfolge ändern** nur Admin (U23)? | Ja. **Teil „Wochenplan-Grafik später“ überholt (Runde 14, X26):** die Wochenansicht der Leise-Zeiten kommt schon in Stufe A (5.8, Paket A7b). Reihenfolge ändern bleibt nur Admin. |
| 7 | Papierkorb für Alle: reicht die Rückfrage mit Namen der betroffenen Tobies? | Ja. |
| 8 | Dürfen **alle HA-Benutzer** die Hördaten sehen (Stufe B), oder nur Administratoren? | Alle (Kinder haben kein HA-Konto); der Löschknopf bleibt Admin. |
| 9 | Stufe B meldet die **Box** (Kind = Box), nicht die Kennung des Tobies. Reicht das? | Ja (weniger Daten); die Kennung später additiv, falls „welcher Tobie“ wichtig wird. |
| 10 | **Speicherplatz der Boxen:** Der Sync nimmt die **ganze** Bibliothek (200 Hörbücher können über 50 GB sein; erster Abgleich dauert Stunden). Reicht der Platz, oder soll später eine Auswahl je Box möglich sein? | Vor dem Einsortieren der 200 Hörbücher `speicher_frei` prüfen; eine Auswahl je Box wäre ein eigenes Thema, nicht Teil dieser Oberfläche. |
| 11 | **HA-Automation „Neuer Tobie → Mitteilung aufs Handy“** als Vorlage in der Doku (U9)? | Ja (keine neue Funktion). |
| 12 | Reihenfolge der geplanten Stufen: **B vor C**? | Ja: B bringt Nutzen ohne Box-Updates am Datenmodell; C braucht ein Boxen-Update. |
| 13 | **Seite erst nach der Abnahme für alle öffnen** (A17, U7)? | Ja. |
| 14 | **Was ist der Abspiel-Link, und wie lange gilt er?** In Alltagssprache: Wenn du am Handy auf „Reinhören“ tippst, holt sich dein Handy die Audiodatei bei Home Assistant ab. Dafür braucht es eine **Adresse**, und diese Adresse hat einen **eingebauten Schlüssel, der nach einer Weile von selbst abläuft**, wie eine Eintrittskarte mit Uhrzeit (der Player im Browser kann beim Abholen kein Passwort mitschicken, darum der Schlüssel). Wie lange soll die Karte gelten? (11.4.2) | **1 Stunde je Folge.** Läuft sie mitten im Hören ab, holt die Seite von selbst eine neue und macht an derselben Stelle weiter (kurzer Aussetzer, kein Fehler für die Partnerin). Alternative: 24 Stunden wie HA bei Medien (seltener Aussetzer, aber eine weitergereichte Adresse gilt länger). **Beantwortet (Runde 8):** 1 Stunde. **Überholt (Runde 10, Review Frage 6, Tobias): 24 Stunden wie bei HA** (11.4.2): ein gesperrtes Handy bricht nach einer Stunde nicht mehr ab, und HA sieht fast nie einen 401. Preis: das Weitergabe-Fenster ist größer (Gegenmittel in 11.4.2). |
| 15 | **Reinhören für alle HA-Benutzer**, auch Wandtablets und Gäste mit Konto (Runde 7)? | Ja; der Zugriff ist auf die Musik und Hörspiele der Familie beschränkt, die Hörstelle ist je Benutzer. **Beantwortet (Runde 8): Anhören dürfen alle.** |
| 16 | Darf ein **Administrator fremde Hörstellen** sehen? | Nein (nur eigene), weniger Daten, nichts zu erklären. **Beantwortet (Runde 8): Ja, nur die eigene Hörstelle** (auch der Administrator). Reinhör-Daten sind davon nicht betroffen; sie sind für alle sichtbar (Frage 23). |
| 17 | **Formate:** Welche Dateiformate liegen im Bestand? OGG/Opus spielt Safari erst ab Version 18.4; ALAC in M4A spielt Chrome nicht. Was tun, wenn ein Gerät es nicht spielt? | Hinweis „Auf der Box spielt es trotzdem“ in Stufe A; Umwandeln mit `ffmpeg` beim Abspielen wäre ein eigenes Paket. **Beantwortet (Runde 8): Alle Formate** (MP3, M4A/M4B, AAC, FLAC, OGG, Opus, WAV). **Folge (11.4.7):** Hörkopie, einmal erzeugt, nicht beim Abspielen; Ort und Platz in Frage 26. |
| 18 | **Dauer für den Bestand** im Hintergrund nachholen (11.4.4)? Bei vielen Dateien dauert es Minuten bis Stunden und liest jede Datei einmal vom NAS. | Ja, einmal, mit Zeitgrenze und ohne Scan beim Öffnen. **Beantwortet (Runde 8): Passt.** Derselbe Lauf holt jetzt auch Kapitel, Codec und die Hörkopien nach (11.4.4, 11.4.7, 11.4.8). |
| 19 | **Zählregel „einmal gehört“** (12.2.1): 10 Sekunden, „fertig“ = Ende der Folge. Sollen kurze Unterbrechungen (Tobie 1 Minute abgenommen) **zusammen** als eine Wiedergabe zählen? | Regel wie vorgeschlagen; Zusammenfassen bei höchstens 5 Minuten Abstand: ja, bei der Aufnahme in HA. **Beantwortet (Runde 8): Ja**, Unterbrechungen bis 5 Minuten sind **eine** Wiedergabe (jetzt Regel in 12.2.1, gilt auch für Reinhören). |
| 20 | **Hörbuch aus einem Ordner mit vielen Tracks:** Eine Zeitleiste über alles (Vorschlag) oder eine Kapitelliste? | Eine Zeitleiste über alle Tracks (einfach; Kapitelliste später). **Beantwortet (Runde 8): Ja, eine Zeitleiste, und die Kapitelliste will er auch.** Gebaut: beides (5.3, 5.12, 11.4.8); Kapitel sind Tracks eines Ordners oder eingebettete Kapitel von M4B/MP3. |
| 21 | Soll **Reinhören in „Gehört“ zählen**? | Nein: „Gehört“ zeigt, was die Kinder an den Boxen hören. **Beantwortet (Runde 8): Doch erfassen, aber dem HA-Benutzer zugeordnet, nicht einer Box.** Umgesetzt als Bereich „Reinhören“ in „Gehört“ (Stufe B, 5.10.1, 12.5); wer es sieht: Frage 23. |
| 22 | **Musik: „Reinhören“ ab dem ersten Lied** und Weiterspielen über das Album (Vorschlag), oder nur ein Lied ohne Weiterspielen? | Über das Album weiterspielen, wie bei Hörspielen. **Beantwortet (Runde 8): Ja, und über eine Playlist**, sobald Stufe C da ist (Abschnitt 13). |
| 23 | **Wer sieht „Reinhören“?** Drei Antworten stoßen hier zusammen: Hördaten der **Boxen** sehen alle (Nr. 8, die Kinder haben kein Konto), die **Hörstelle** sieht nur man selbst (Nr. 16), und Reinhören ist jetzt dem **HA-Benutzer** zugeordnet (Nr. 21). Reinhör-Daten sind Daten über **Erwachsene**: wer hat wann was angehört. (12.5) | Empfehlung (durch Runde 9 überholt): **Jeder sieht nur die eigenen, auch Administratoren** (wie Nr. 16). Die Boxen-Daten bleiben für alle sichtbar (Nr. 8). Jeder darf **seine eigenen** Reinhör-Daten löschen; „Alle Hördaten löschen“ in „Technik“ betrifft nur die Boxen. Alternative: alle sehen alle (einfacher zu bauen, aber die Partnerin sähe, was Tobias hört, und jedes Gäste-Konto auch). Nebenfrage: Soll die Erfassung schon in Stufe A beginnen (kleiner Zusatz in A4d, dann gibt es von Anfang an Verlauf), oder erst mit Stufe B? Empfehlung: erst mit Stufe B. **Beantwortet (Runde 9): Alle HA-Benutzer sehen die Reinhör-Daten** (Entscheidung Tobias, ersetzt die Empfehlung). Im Reiter „Gehört“ wählt man „Alle“ oder einen HA-Benutzer (Namen aus HA, nie im Repo). Löschen: jeder seine **eigenen** Reinhör-Daten, Administratoren alle. Die Hörstelle bleibt privat (Frage 16). Die Erfassung beginnt mit Stufe B. Der Umschalter „Boxen \| Reinhören“ ist in Rev. 5 entfallen (Frage 23a). |
| 23a | **„Gehört“ ohne Umschalter und ohne Hinweistext?** | **Beantwortet (Runde 10, Tobias):** Eine Auswahl „Wer?“: Alle, Box 1, Box 2 (Anzeigenamen aus den Integrations-Einstellungen) und die HA-Benutzer, die reingehört haben (Name aus HA); Boxen und Personen gleichberechtigt. Löschen: eigene Reinhör-Daten jeder, alles nur Administratoren (5.10, 12.4). Bleibt offen, **wo** der Knopf für die eigenen Daten sitzt: Frage 27. |
| N | **Echte Namen im Repo?** | **Beantwortet (Runde 10, Tobias):** nie, auch nicht die der Eltern. Der Prototyp im Repo hat Platzhalter in **einem** Objekt `NAMEN`. |
| 24 | **Wo lebt ein einzelnes Lied oder eine einzelne Folge?** Heute ist alles Serie → Folgen. (A) Eigene **Serie mit genau einer Folge** und dem Kennzeichen `einzeln` (eigenes Cover und Titel, in der Liste „Lied · einzeln · 1:06“), oder (B) eine **Sammel-Serie** je Art („Einzelne Lieder“ mit 300 Liedern). (11.3.1) | **A.** Die Box ändert sich nicht; ein Lied hat sein eigenes Cover, einen eigenen Tobie und lässt sich einzeln benennen und löschen. Preis: 300 Einträge mehr in der Bibliothek (Gegenmittel: „Was zeigen“ im Filterblatt, Arten-Zeile) und 300 kleine Ordner auf dem NAS. Der Tobie zeigt auf die **Folge** (nicht die Serie), damit er bei späteren Änderungen nur sein Lied spielt. **Beantwortet (Runde 9): Wie empfohlen (A).** |
| 25 | **NAS-Eingang: Was passiert mit Dateien, die einfach in den Ordner gelegt werden?** Heute werden sie automatisch einsortiert. (1) Weiter **automatisch**, bei „bitte ansehen“ gibt es **„Anders einsortieren …“** mit derselben Wahl wie beim Hochladen (die Folgen werden zurück in den Eingang geholt und neu einsortiert, solange nichts daran geändert wurde). (2) Nicht Sichere Fälle **bleiben im Eingang liegen und fragen** zuerst („Was ist das?“), erst nach der Antwort wird einsortiert. (7.3 Punkt 10) | **1.** Wer Dateien in den Ordner legt, will nichts beantworten müssen; die meisten Fälle sind eindeutig. Der Rückweg Medien → Eingang ist in Vertrag W noch nicht vorgesehen und wird in A3d zuerst geprüft; ist er zu teuer, wird es **2** (kein Rückweg nötig, aber es erscheint nichts, bis jemand antwortet) oder nur „In den Papierkorb und neu hochladen“. **Beantwortet (Runde 9): Wie empfohlen (1).** Ist der Rückweg Medien → Eingang zu teuer, gilt der Rückfall aus dieser Frage (Option 2). **Runde 10: Rückfall-Formulierung passt.** Review Frage 5: „Anders einsortieren“ nur für „bitte ansehen“ oder jünger als 24 Stunden. |
| 26 | **Hörkopien: Ort, Qualität, Platz.** Für Formate, die nicht jeder Browser spielt, legt HA **einmal** eine Kopie an: AAC/M4A, 96 kbit/s, auf dem **NAS** in einem Ordner `hoerkopien/` **neben** `medien/` (nicht auf den Boxen, nicht in HAs Konfigurationsordner). Auch FLAC und WAV bekommen eine Kopie (sie sind groß). Bedarf: 43 MB je Stunde Audio; meist **wenige GB**, im schlechtesten Fall (alles in OGG/FLAC/WAV, 1 600 Stunden) etwa **70 GB**. (11.4.7) | **Ja so.** Der Ort lässt die Boxen und den Sync völlig in Ruhe. **Beantwortet (Runde 9): NAS hat einige TB frei.** **Review Frage 2 (Tobias): neu Einsortiertes sofort, Bestand erst beim ersten Reinhören** („Hörprobe wird vorbereitet“), mit den Grenzen aus 11.4.7. `kein_speicher` stoppt die Erzeugung ohne Schaden. Wer FLAC und WAV lieber ohne Kopie will (nur Hinweis „Auf der Box spielt es trotzdem“), spart Platz und verliert das Reinhören für diese Dateien auf Geräten ohne Unterstützung. |
| Review 1 | **Stufe A in drei Freigaben schneiden (G14)?** | **Beantwortet (Tobias): ja.** A-1 Alltag, A-2 Reinhören mit Weiterhören, A-3 Hörkopien und Kapitel, je eigene Abnahme (Abschnitt 15). |
| Review 3 | **Upload-Grenze (G15)?** | **Beantwortet (Tobias): 2 GiB je Datei** (5.6a). |
| Review 4 | **Papierkorb für alle (G8): Tageslimit?** | **Beantwortet (Empfehlung übernommen): Mitteilung an Administratoren plus „Letzte Stunde zurückholen“, kein Tageslimit** (10.3). |
| 27 | **Wo sitzt „Meine Reinhör-Daten löschen“?** Runde 10 sagt: eigene Daten löscht jeder, alles nur der Administrator, „in Technik“. „Technik“ sehen aber nur Administratoren; die Partnerin könnte ihre eigenen Daten dann nicht löschen. | Eigene Daten: ruhiger Textknopf **ganz unten in „Gehört“** (für jeden, Rückfrage); alle Reinhör-Daten und alle Hördaten der Boxen: „Technik“ (nur Administratoren). Alternative: alles nur in „Technik“, dann löscht die Partnerin nichts selbst. Der Prototyp zeigt die Empfehlung. **Beantwortet (Runde 11, Tobias):** Nur in „Technik“ (Administrator), kein Knopf in „Gehört“; eigene Daten löschen kommt praktisch nicht vor. `reinhoer/loeschen` ist damit nur `admin`. |
| 28 | **Was heißt „Alle“ in „Wer?“?** Boxen (die Kinder) und Reinhören (die Erwachsenen) zusammen addiert, oder nur die Boxen? | **Alles zusammen** (die Auswahl ist eine Summe der Quellen, einfachster Vertrag: `wer=alle`). Hörzeit und Rangliste mischen dann Kinder und Erwachsene; wer nur die Kinder sehen will, wählt eine Box (bei Geschwistern zweimal und im Kopf addieren). Alternative: „Alle Boxen“ als eigener Knopf neben „Alle“. **Beantwortet (Runde 11, Tobias): Ja**, „Alle“ ist die Summe aus Boxen und Reinhören. |
| 29 | **Grenzen der Hörkopie (11.4.7):** Dauerdeckel 48 Stunden, Zeitgrenze 60 Minuten je Datei, Schlange 20 Dateien und 50 GB, Kontingent 100 GB. Ein einzelnes Hörbuch über etwa 30 Stunden schafft die Zeitgrenze auf einem langsamen HA vielleicht nicht und bekommt dann keine Hörprobe (auf der Box spielt es trotzdem). | Die Zahlen **nach der Messung in A0b** festlegen (Konstanten); Hörbücher dieser Länge ohne Hörprobe in Kauf nehmen (Reinhören ist zum Erkennen gedacht). Alternative: Kopie in Teilen je Stunde (mehr Code, nicht in Stufe A). **Runde 11:** Erklärt; Grenzen werden nach der Messung in A0b festgelegt. |
| Runde 16 | **X20, X12a, X13a, X22a, X27a, X31** | **Beantwortet (Tobias, 12.11.):** X20 angenommen (Reiter „Tobies“ als Regal, Zuordnen beginnt beim Tobie: 5.4, 5.7, 7.1); X12a keine Hochlade-Kachel „Neue Playlist“ (5.6, 13.7); X13a Lernmodus nur Administratoren (10.2, 5.13); X22a Gute Nacht bleibt eine Dauer (5.8); X27a Reihen nur auf dem Start (5.1, 5.2); X31 Player bündig (A6). |
| 30 | **Zweiter Tobie für einen Eintrag, der schon einen hat:** Auf der Serienseite stehen dann nur die Chips, **kein** Link „Einem Tobie geben …“ (so beschlossen, X20). Reicht der Weg „Tobies → Tobie → Ziel“? | Ja für den Alltag (selten, meist ein Tobie je Eintrag). Fehlt es, kommt ein Textlink „Noch einem Tobie geben …“ neben die Chips (kleine Änderung). |
| 31 | **Rechte von `lernmodus/antwort` und `lernmodus/abbrechen`:** X13a nennt nur `lernmodus/start`. Alle drei zurück auf `admin`? | Ja, alle drei (ein Vorgang); mit A0-Q bestätigen. |

## 17. Was der Prototyp v8 zeigt und was nicht

`prototyp.html` ist eine **Vorschau**, kein Code für den Bau, und schickt nichts an Home Assistant. Er zeigt (alles im Script erzeugt, erfundene Daten): **64 Einträge** (20 Hörspiele, 20 Hörbücher, 12 Musik-Alben, 8 Geschichten und **4 Einzeltitel**; darunter ein Album mit 20 Liedern und das Hörbuch „Mia und das Meer“ mit **12 Kapiteln**), rund **576 Folgen und Lieder**, alle mit einer Dauer. Alles aus v4 und v5 (Bibliothek, Suche, Serienseite, Player, Hochladen in Schritten, Kapitel, Einzeltitel, Technik, Abends, Zustände, „Gehört“ mit „Wer?“) bleibt; **v6 setzt die Runde 12 (X1 bis X9) um.**

**Namen (Runde 10):** Alle Namen stehen in **einem** Objekt `NAMEN` ganz oben im Script (`const NAMEN = { box1: 'Box 1', box2: 'Box 2', personA: 'Person A', personB: 'Person B' };`); sonst kommt kein Name im Text vor (geprüft mit `grep`). Die Rollen heißen „Administrator (Person A)“ und „Benutzer ohne Admin (Person B)“. Die Beispielnamen „Mond“ und „Stern“ sind überall ersetzt; echte Namen kommen in der echten Seite aus HA.

**Neu in v8 (Runde 16, X20, X12a, X13a, X22a, X27a, X31):**
* **Reiter „Tobies“ als Regal** (Kachel „+ Neuer Tobie“, Kacheln mit Ziel und bei einer einzelnen Folge dem Serienzusatz; Suchfeld erst ab 9 Tobies); **„Was soll … spielen?“** (Zielwahl als Seite: Spielt jetzt, Ganze Serie · Folge oder Lied · Playlist, Suche, Arten, aufklappbare Serien, „Gute-Nacht-Karte“ als eigene Zeile, Namen ändern, vergessen); **Neuer Tobie** Weg 1 (Warteseite, „Neuer Tobie erkannt“, Name, Zielwahl, Versehen) und Weg 2 (Box wählen, Ziel, Wartekarte mit „Abbrechen“); Karte „Neuer Tobie auf Box 1 – was soll er spielen?“ nur auf „Geräte“; **„Gespielt von“-Chips** auf Serien-, Playlist- und Folgenzeilen, „Noch kein Tobie · Einem Tobie geben …“ und die Seite „Welcher Tobie soll das spielen?“ (auch für eine Folge über „⋯“, für Einzeltitel und Playlists); **Meldung mit „Rückgängig“** (6 s) nach jedem Zuordnen, „Name geben“ nach der Zuordnung durch die Warteschlange. Der Menü-Knopf „i“ legt Tobies weiter über „Neuen Tobie auf Box 1/2 auflegen (Demo)“ an (auf der Warteseite ist das das Auflegen).
* **Entfernt:** Knopf „Tobie zuordnen“ (Serien- und Playlist-Seite), Blatt „Tobie anlernen“ mit „Auf Box 1“, Tobie-Blatt der Tobies-Liste, Karte „Neuer Tobie“ mit Kacheln und „Fertig!“-Karte, die Reihen „Am Handy weiterhören“ und „Neu hinzugefügt“ in der Bibliothek (sie bleiben auf dem Start). Das Hochladen hat weiter vier Kacheln und keine Playlist-Kachel; „Zur Playlist hinzufügen“ steht nach dem Hochladen (Stufe C). Der Lernmodus liegt nur noch unter „Technik“ (Administrator).
* **Mini-Player bündig (X31):** Der Player sitzt mit `bottom: var(--navh)` auf der Leiste; `--navh` wird aus der gemessenen Höhe der Leiste gesetzt (Safe-Area eingeschlossen). v7 ließ 1 px Spalt (65 px gegen 64 px Leiste).
* **Prüfung v8** (Playwright, Chromium, 390 × 844 und 1280 × 800 px, Hell, Dunkel und Theme mit hellem Primärton): 15 Ansichten (Start, Bibliothek, Tobies, Tobie-Seite, Neuer Tobie, Warteseite, Weg 2, Geben für Serie und Folge, drei Serienseiten, Geräte mit Karte, Neuer Tobie erkannt, Hinzufügen, Suche): **kein waagerechtes Scrollen, alle Tippziele mindestens 44 px, Text mindestens 4,5:1 (große Schrift 3:1): 0 Treffer; keine Konsolenfehler.** Abläufe (alle bestanden): Weg 1 mit Name, Ziel, Regal, „Rückgängig“ (Tobie liegt wieder als unbekannter auf „Geräte“); Weg 2 mit Box, Folge aus aufgeklappter Serie, Warteseite, simuliertes Auflegen, „Name geben“, Umbenennen; Tobie → anderes Ziel → „Rückgängig“, Meldung 5,9 s sichtbar; Suche in der Zielwahl; Bibliothek ohne Reihen und ohne Zuordnen-Knopf, Start mit beiden Reihen; Serie → „Einem Tobie geben …“ → Tobie → Chip → „Rückgängig“; „+ Neuer Tobie“ mit festem Ziel; Folgenmenü und Einzeltitel und Playlist-Seite; doppelter Warteschlangen-Eintrag; „Versehen, nicht merken“; Regal mit 10 Tobies und Suche; Tobie vergessen; Wizard „Was lädst du hoch?“ ohne Playlist-Kachel; Rolle Benutzer; „Leer zeigen“.
* **Messung X31** (mit Mini-Player, Seiten Bibliothek, Tobies und Serie, je oben, Mitte, Ende): **Abstand Unterkante Player zu Oberkante Leiste 0 px** bei 360, 390, 600 und 899 px, **ohne** und **mit** emulierter Safe-Area (34 px; Leiste dann 98 px hoch). Ab 900 px mit Seitenleiste liegt die Unterkante des Players auf dem unteren Rand des Fensters (0 px; am äußersten Seitenende bei gebrochener Seitenhöhe bis 0,4 px Rundung des Browsers).

**Neu in v7 (Runde 12 bis 15):**
* **Reiter Start · Bibliothek · Tobies · Geräte** (Pille, Glas mit Rückfall, ab 900 px Seitenleiste links); **Start** als Schaufenster (Begrüßung, Schnellzugriff 2 × 3, Reihen je Stufe, Raster in Stufe A mit zuletzt zugeordneten und hinzugefügten Einträgen); **Geräte** mit Box-Karten (Tipp → Box-Detailseite, für Administratoren mit Technik-Details, für Person B ohne), Karte „Neuer Tobie aufgelegt“ mit Punkt am Reiter, Warteschlange, Gute Nacht, Wochenansicht der Leise-Zeiten, „Gehört“ (B); **Bibliothek** mit „+“, Band für laufende Uploads, Unterreiter „Playlists“ (C), endlosem Nachladen.
* **Playlists** (Stufe C – Vorschau): Seite mit Cover-Mosaik, Ziehen und Menü, Hinzufügen, Entfernen, Umbenennen, Papierkorb, als Tobie-Ziel, Weiterspielen; **Warteschlange** (Menü „i“: „Neuen Tobie auf Box 1/2 auflegen“, „Bekannten Tobie auflegen“); **Player-Sperre**; **Technik-Unterseiten**; **Suchvorschläge**; **tonale Knöpfe**; **Zeitfelder**; „⋯“ als eigene Fläche; Schalter „Stufen zeigen“ hat „A, dazu B (ohne Stufe C)“.
* **Prüfung v7** (Playwright, Chromium, 390 und 1280 px, Hell, Dunkel und Theme mit hellem Primärton, Administrator und Person B): kein waagerechtes Scrollen, Tippziele ≥ 44 px, Textkontrast ≥ 4,5:1 (große Schrift 3:1), Reiterbeschriftung gegen Schwarz, Weiß und Grau unter der Glasleiste ≥ 4,5:1, keine Konsolenfehler. Abläufe: Lied → „⋯“ → Zur Playlist hinzufügen → umsortieren (Menü, Ziehen, Tastatur) → entfernen; Warteschlange → simuliertes Auflegen → zugeordnet; Sperren und Entsperren (kurz gehalten bleibt gesperrt); Technik-Unterseiten; Suche mit Vorschlägen; Box-Karte → Detailseite (Admin, Person B); Bibliothek → „+“ → Hochladen mit Band; Start in Stufe A und B; endloses Nachladen (60 → 64 Einträge).


**Neu in v6 (Runde 12, X1 bis X9):**
* **Vier Reiter** (Start · Bibliothek · Tobies · Mehr, 14 px, 64 px hoch) und die **Mehr-Seite** mit „Abends“, „Gehört“ (Vorschau B) und „Playlists“ (Idee C); „Nur Stufe A“ lässt nur „Abends“ stehen. Abends und Gehört haben oben „‹ Mehr“. Der große Knopf „Abends“ auf dem Start bleibt (1 Tap).
* **Leere Zustände mit sechs Bildern** (Regal, Lupe, Tobie, Box, Papierkorb, Kopfhörer), je Satz und Knopf; Schalter **„Leer zeigen“** im Menü „i“.
* **Hochladen mit Kacheln** (zwei Spalten, Symbol, Titel, eine Zeile); **Radien** 16 und 24 px; **Wischen** am Mini-Player (oben auf, unten zu; Knopf bleibt, Griff in der Vollansicht); **Meldungen**: Erfolg 4,5 s, Fehler mit „OK“ und Wegwischen, im offenen Blatt oben; Listenaktionen 48 px; Token **`--line`** und Ränder in `--primary-ink`, im Theme mit hellem Primärton geprüft.
* Der Prüfstand rechnet jetzt auch **Rand- und Symbolkontrast (3:1)** und läuft mit echter Fensterbreite 390 px (der Test für v5 nutzte `is_mobile` ohne Viewport-Angabe und prüfte dadurch eine Breite von 980 px).

**Prüfung v6** mit Playwright (Chromium) bei **390 × 844 und 1280 × 900 px** (echte Fensterbreite), **Hell, Dunkel und Theme mit hellem Primärton**, Rolle **Administrator und Benutzer ohne Admin**, je Ansicht (Start, Mehr, Abends, Bibliothek, Suche mit und ohne Treffer, drei Serienseiten, Tobies, Gehört, Hinzufügen, Technik; Rolle Benutzer ohne Technik) und mit **„Leer zeigen“** (Start, Bibliothek, Tobies, Suche, Gehört, Technik → Papierkorb), dazu Wahlblatt und Vorschau beim Hochladen, Player und Fehlermeldung: **231 Prüfläufe: kein waagerechtes Scrollen, alle Knöpfe, Links, Auswahlfelder und Regler mindestens 44 px, Text mindestens 4,5:1 (3:1 große Schrift), Ränder und Symbole mindestens 3:1: 0 Treffer; keine Konsolenfehler; keine alert/confirm/prompt; 143 Ablaufprüfungen ohne Fehler.** Die Ablaufprüfungen: vier Reiter mit 14 px Schrift und 64 px Höhe; **Start → Mehr → Abends** (2 Taps, Reiter „Mehr“ bleibt markiert, „‹ Mehr“ führt zurück) und **Start → Knopf „Abends“** (1 Tap); „Gehört“ nur über „Mehr“; „Nur Stufe A“ lässt nur „Abends“ in „Mehr“ und leitet `#gehoert` nach `#mehr`; Person B sieht „Mehr“ mit „Abends“ und keinen „Technik“-Knopf; **Wischen am Player** mit `page.mouse` und per CDP-Touch (nach oben öffnet, nach unten schließt, unter der Schwelle und nach unten in der Leiste passiert nichts, Antippen, Knopf und Tastatur gehen weiter, Regler ziehen schließt nicht); **Fehlermeldung bleibt nach 6 s, „OK“ und Wegwischen entfernen sie, sie ist über einem offenen Blatt sichtbar und kompakt; Erfolgsmeldung ist nach 4 s noch da und nach 5 s weg**; **sechs leere Zustände** mit Bild, Satz und Knopf; fünf Kacheln mit Symbol, Erklärung in **einer** Zeile und 24 px Radius; Radien Karte 16 px, große Kachel 24 px, Blatt 24 px; Listenaktionen mindestens 44 × 44 px. Die Bilder (Mehr, leere Zustände in Hell, Dunkel und Gelb, Wahlblatt, Player, Meldungen) habe ich selbst durchgesehen; **ein Durchgang Korrekturen** behob (1) eine über die ganze Höhe gestreckte Fehlermeldung im Blatt (Vorrang einer Regel für den Mini-Player), (2) den gelben Rand des aktiven „Technik“-Knopfs im Theme mit hellem Primärton (1,2:1, jetzt `--primary-ink`), (3) zu lange Zeilen in zwei Kacheln („Hörspiel, Buch oder Album“, „Kommt später · Stufe C – Idee“) und (4) eine Hinweiskarte „1 neuer Eintrag“ und die Reihe „Am Handy weiterhören“ über dem leeren Start. **Nicht belegt** (wie bisher): echte HA-Farben und -Themes, Wischen auf einem echten Handy mit der Companion-App, Verhalten bei 320 px Breite und 200 % Zoom im Prototyp.

**Neu in v5:**
* **„Gehört“:** kein Umschalter, kein Hinweistext; **eine Auswahl „Wer?“** (Alle · Box 1 · Box 2 · Person A · Person B). Rangliste, Aufteilung nach Folgen, Hörzeit pro Tag (mit Zahlen als Tabelle, bei „Alle“ aufgeteilt) und „Was wird gezählt?“ gelten für die Auswahl. Unten „Meine Reinhör-Daten löschen …“ (jeder); „Alle Reinhör-Daten löschen …“ und „Alle Hördaten der Boxen löschen …“ in „Technik“.
* **Hochladen mit mehreren Dateien:** „Datei 2 von 3 wird hochgeladen“, „Einsortiert wird erst, wenn alle 3 Dateien da sind“; Demo „3 Dateien, die dritte kommt nicht an“ („Es fehlt noch eine Datei“); Demo „2 Dateien, dazu eine über 2 GB“ (Hinweis „zu groß“ im Blatt und in der Zeile). „Abbrechen“ oben rechts im Blatt, „Welche Art?“, „Wohin soll es?“, Satz „Die übrigen N Dateien heißen wie in ihren Angaben.“, Grenze „Bis 2 GB je Datei“.
* **„Die Hörprobe wird vorbereitet“:** „Das Lied vom Mond“ (OGG) ist im Bestand noch ohne Kopie; das erste Reinhören stößt die Vorbereitung an (Karte mit Balken, fünf Sekunden), danach Meldung „Die Hörprobe ist fertig. Tippe auf Reinhören.“ „Hörstellen zurücksetzen“ stellt es zurück.
* **„Hier weiterhören“** und „Am Handy weiterhören“ mit dem Satz „Das spielt hier am Handy oder Computer, nicht auf der Box.“; **Suchtreffer sind Links**; Technik: Papierkorb mit „gelöscht von …“, „Letzte Stunde zurückholen“ und Satz zur Mitteilung, Hörkopien mit Schlangenzähler; Texte „dem Administrator“ statt eines Namens.

**Prüfung v5** mit Playwright (Chromium) bei **390 × 844 und 1280 × 900 px, hell und dunkel**: elf Ansichten (Start, Bibliothek, Suche, drei Serienseiten, Tobies, Abends, Gehört, Hinzufügen, Technik) plus Gehört mit jeder Auswahl, Blatt „Was lädst du hoch?“, Vorschau, drei Upload-Abläufe, Hörprobe und Suche mit Treffern: **kein waagerechtes Scrollen, alle Knöpfe, Links, Auswahlfelder und Regler mindestens 44 px, Kontrast mindestens 4,5:1 (3:1 große Schrift): 0 Treffer; keine Konsolenfehler; keine alert/confirm/prompt; 120 Ablaufprüfungen ohne Fehler** (kein Umschalter und kein Hinweistext, fünf Auswahlknöpfe mit richtiger Rangliste je Auswahl, Aufteilung für Person A, Löschknöpfe nach Rolle, Rollenbeschriftung aus `NAMEN`, Hörprobe mit Wechsel auf „fertig“, Upload mit mehreren Dateien bis „Hörbuch „Kapitän Knopf“ · 3 Kapitel“, „Es fehlt noch eine Datei“, „zu groß“, Suchtreffer als Link, „Am Handy weiterhören“, „Hier weiterhören“). Die Bilder (Gehört, Wahlblatt, Vorschau, Upload, Hörprobe) habe ich selbst durchgesehen; ein Durchgang Korrekturen behob eine Leerstelle im Satz zur Hörzeit („1 Std. , Person B“).
**Nicht belegt:** echte HA-Farben und -Themes, die Companion-App (Ton im Hintergrund, Sperrbildschirm), echte Audiodateien über die Audio-Ansicht und signierte Pfade (A4c, A8b), echte Hörkopien und Kapitel aus Tobias’ Dateien (A3b3, A3c), Safari und iPhone, Springen auf dem NAS-Pfad, echte Fotos vom Handy, der Rückweg Medien → Eingang bei „Anders einsortieren“ (A3e), 2-GiB-Uploads über Nabu Casa (A0b).

## 18. Befunde des Goldfischs und ihre Behandlung

**Erster Goldfisch (U1 bis U26): 26 Befunde. Eingearbeitet 24 (davon U1 schon behoben), teilweise abgelehnt 2 (U3, U23), vollständig abgelehnt 0. In Rev. 5 nachgearbeitet: U2, U6, U8, U10, U15, U18, U22, U25.**
**Zweiter Goldfisch (`review_goldfisch_rev4.md`, G1 bis G31): 31 Befunde (hoch 3, mittel 16, niedrig 12). Eingearbeitet 31, abgelehnt 0.** Wo ein Vorschlag angepasst wurde (G1: Zeitgrenze 60 statt 30 Minuten; G5: 6 statt 4 Verbindungen; G11: Kopieren statt Test ändern; G14: Name-Vorschlag im Browser entfällt), steht der Grund in der Zeile.

### 18.1 Zweiter Goldfisch: G-Nr. → Behandlung

| G | Schwere | Behandlung |
|---|---|---|
| G1 | hoch | eingearbeitet (11.4.7, 11.4.4, 10.3, 15 A3c): Dauerdeckel 48 Stunden, **feste** Zeitgrenze (60 Minuten statt des vorgeschlagenen Beispiels 30, weil ein Hörbuch von 10 Stunden bei 15-facher Echtzeit 40 Minuten braucht; Konstante nach A0b, Frage 29), `-t` und `-fs`, Plausibilität Größe zu Dauer, Schlangenlimit mit Zähler in „Technik“, Vorziehen eine Datei je Benutzer, `-ac 2 -map 0:a:0`, gilt auch für `ffprobe` (feste 30 s, kein `dauer_s` über dem Deckel), Test FLAC-Stille |
| G2 | hoch | eingearbeitet (7.3, 11.2 V-7, 5.6, 15 A3d): `gruppe_anzahl`, der Eingang wartet auf alle, 30 Minuten Ruhe → `teilweise`; Tests mit 60 Sekunden Abstand und fehlender Datei; `neu` ohne Zusage `wunsch_ungueltig` |
| G3 | hoch | eingearbeitet (11.4.1, 11.2 V-6, 5.12, 6.1, 15 A8b): Befehl `audio/bereit` (`bereit`/`wird_vorbereitet`/`fehlt`, mit signiertem Pfad); Seite liest den Zustand nie aus dem `<audio>`-Fehler; Test mit echtem Chromium |
| G4 | mittel | eingearbeitet (11.4.2, 6.1): am HA-Code belegt (`ban_middleware` → `process_wrong_login`); Link 24 Stunden, Erneuerung vor Ablauf, kein Probe-`fetch` mit altem Link, „keine Meldung für Tobias“ |
| G5 | mittel | eingearbeitet (11.4.1, 10.2, 15 A4c): Unterklasse von `FileResponse` zählt in `prepare()` und gibt im `finally` frei; „Stream“ = offene Verbindung, Grenze **6** statt 4 (der Browser hält je Element 1 bis 2); Test mit langsam lesendem Client |
| G6 | mittel | eingearbeitet (11.4.1 Punkt 4, 15 A4c3): zwei Zweige, Original unter `medien/`, Kopie unter `hoerkopien/` nur aus `serie_id` und `kennung`; Test: nicht über andere `serie_id` erreichbar |
| G7 | mittel | eingearbeitet (5.5, 11.2 V-1, 15 A4): Maße aus dem Kopf vor dem Dekodieren, Rumpf mit Zähler, eine Funktion für beide Wege, `Pillow` im Manifest, 20 Cover je Stunde, Tests (Pixelbombe, chunked, CMYK, PNG mit JPEG-Endung) |
| G8 | mittel | eingearbeitet (10.3, 5.9, 15 A1): Mitteilung an Administratoren, Protokollzeile, „Letzte Stunde zurückholen“, **kein** Tageslimit (Tobias, Review Frage 4) |
| G9 | mittel | eingearbeitet (7.3 Punkt 10, 10.3, 11.2 V-7, 15 A3e): nur `pruefen=true` oder jünger als 24 Stunden, Ruhezeit, Papierkorb-Aktion, Liste der Prüfungen im Vertrag, Fremd-Hörstellen nur intern |
| G10 | mittel | eingearbeitet (11.3, 11.4.4, 15 A3b): abgeleitete Werte im Store `tobibox.medieninfo`, `stand` rechnet nur über Name, Folgenliste und menschliche Felder; Test „Hintergrundlauf ändert `stand` nicht“ |
| G11 | mittel | eingearbeitet (5.5, 11.3, 15): mitgeliefertes `cover.jpg` wird **kopiert**, das Original geht wie bisher in den Papierkorb; kein bestehender Test und kein Vertrag 11.10 ändert sich; fehlende Tests in A4; Satz „nicht angepasst“ ersetzt |
| G12 | mittel | eingearbeitet (5.9, 15 A6): Datei und Elementname der alten Seite bleiben, neues Element `tobibox-app` bettet sie mit `eingebettet` ein; nur `test_init.py` ändert sich in A17 |
| G13 | mittel | eingearbeitet (15, 15.1): A0 zuerst mit Freigabe, Backend-Pakete nacheinander, Abhängigkeitsgraph, A5 nach A0, Vertragstest „alte Antworten bleiben gültig“ |
| G14 | mittel | eingearbeitet (2, 15; Tobias, Review Frage 1): A-1, A-2, A-3; Name-Vorschlag aus den Tags im Browser entfällt |
| G15 | mittel | eingearbeitet (5.6a, 6.1, 10.3, 15 A3d; Tobias, Review Frage 3): 2 GiB, Folgen für Code, Vertrag W 8, Reserve, Zwischendateien, Nabu-Casa-Messung (A0b); Fehlertext mit Zahl und Rat; Prototyp zeigt „zu groß“ |
| G16 | mittel | eingearbeitet (11.2 V-2, V-6): vorhandene Namen `anzahl_folgen`, `anzahl_tobies`, `angelegt_am`; neu `kapitel_anzahl` |
| G17 | mittel | eingearbeitet (5.2, 5.3, 5.12, 8): „Hier weiterhören“, Reihe „Am Handy weiterhören“, Satz „Das spielt hier am Handy, nicht auf der Box.“; Test mit der Partnerin in A-2 |
| G18 | mittel | eingearbeitet (5.12, 11.4.2; Tobias, Review Frage 6): Link 24 Stunden, ehrliche Fassung („zum Erkennen“), gesperrtes Handy und Ordner-Folge als erster Test (A0b, A16-2) |
| G19 | mittel | eingearbeitet (5.9, 10.1, 15 A0b/A6/A17): Prüfung vorgezogen, neue Seite parallel unter `/tobibox-neu`, Adressen tauschbar, Notschalter als Boolean |
| G20 | niedrig | eingearbeitet (10.2): `folgen/order` in der Zeile admin, `hoerstelle/*` einheitlich (`get`/`liste` lesen, `set` alltag) |
| G21 | niedrig | eingearbeitet (12.4, 16): „Mein Reinhören“ ersetzt |
| G22 | niedrig | eingearbeitet (11.1): Regel (Umgebung oder neue Eingaben), `erwartet_revision` und `zuordnung/list`-Felder unter `bibliothek`, Filterwerte bei `bibliothek`, `kapitel` entfällt, **eine** Antwort der Seite |
| G23 | niedrig | eingearbeitet (10.2, 10.3, 15 A1): Überraschungs-Serie als Ziel nur für Administratoren |
| G24 | niedrig | eingearbeitet (3.1, 3.3, 5.3, 6, 6.1, 10.3, Prototyp): Eintrag `verwalter`, neutral „dem Administrator“; Namen nie im Repo |
| G25 | niedrig | eingearbeitet (5.2, 15 A7, Prototyp): Suchtreffer sind Links |
| G26 | niedrig | eingearbeitet (5.6, 7.3, 14, Prototyp): Abbrechen oben rechts, „Welche Art?“, „Wohin soll es?“, Satz zu den übrigen Dateien |
| G27 | niedrig | eingearbeitet (11.4.1, 11.4.6, 15 A4c/A8b): `encodeURIComponent` je Segment, Testnamen mit `#`, `?`, `%`, `+`, `&`, führendem Punkt |
| G28 | niedrig | eingearbeitet (11.4.5): Verzögerung 60 Sekunden |
| G29 | niedrig | eingearbeitet (11.4.5): Backend nimmt bekannte Dauer aus dem Store |
| G30 | niedrig | eingearbeitet (11.3, 11.4.7): `codecs` je Track, Entscheidung je Track |
| G31 | niedrig | eingearbeitet (11.2 V-7, 11.1): `name` bis 400 Bytes, sonst `wunsch_ungueltig`; Vertrag 5.1 angepasst |

### 18.2 Erster Goldfisch: U-Nr. → Behandlung

| U | Behandlung |
|---|---|
| U1 | **Schon behoben** (Commit d41e319); Test siehe 10.1 und A1 |
| U2 | eingearbeitet (10.3, 10.2): `remove` nur mit `erwartet_ziel`, `set` nur für bekannte Kennungen, Mengen, 10 frühere Stände (Frage 3) **Rev. 5 (G8):** gilt jetzt auch für den Papierkorb (Mitteilung, Protokoll, „Letzte Stunde zurückholen“, 10.3). |
| U3 | **teilweise abgelehnt, weil** Tobias in Runde 6 bewusst „alle HA-Benutzer“ entschied; die Benutzerliste in den Optionen wird nicht gebaut (10.1 Punkt 6). Eingearbeitet: Mengen- und Upload-Obergrenze (10.3) |
| U4 | eingearbeitet (7.1, 5.7): Name in der Fertig-Karte, „zuletzt angelernt“ oben, Suche, Auflegen-zum-Finden wenn die Box die Kennung meldet |
| U5 | eingearbeitet (5.5): Marke „schon gesucht“, einmal im Hintergrund, Zeitgrenze, kein Dauer-Scan, `ffmpeg` fehlt, `medien/pruefen` höchstens alle 10 Minuten |
| U6 | eingearbeitet (5.9, 15): alte Seite einbetten, 121 Tests unverändert **Rev. 5 (G12):** Datei und Elementname der alten Seite bleiben, neues Element `tobibox-app` (5.9). |
| U7 | eingearbeitet (10.1, A17): `require_admin` bleibt `True` bis nach der Abnahme |
| U8 | eingearbeitet (5.5, 11.3): `cover*.jpg` nicht auf die Boxen, reservierte Namen, Zusammenführen, Papierkorb, Quelle `cover.jpg`/`folder.jpg`, „Cover neu suchen“, Tests; Frage 5 **Rev. 5 (G11):** mitgeliefertes `cover.jpg` wird kopiert, das Original folgt der alten Regel (Papierkorb); fehlende Tests (Zusammenführen, Wiederherstellen, Umbenennen) in A4 (11.3, 15). |
| U9 | eingearbeitet (7.1, A15): ehrlich zählen, Automation-Vorlage, Satz über den Kacheln, nur die oberste Karte bedienbar, Rückgängig bis „OK“ |
| U10 | eingearbeitet (10.3, 7.3): `eingang/sortieren` ohne `sofort` für Alltag **Rev. 5 (G9):** `einsortierung/neu` nur für „bitte ansehen“ oder jünger als 24 Stunden, Ruhezeit, zählt als Papierkorb-Aktion (10.3). |
| U11 | eingearbeitet (5.3, 7.3): „Das ist richtig / Das stimmt nicht“, verschieben und Papierkorb für Alltag |
| U12 | eingearbeitet (5.6, 7.3): Ordner-Knopf nur mit Maus, Hörbuch-Frage nur ohne Tags, Zielwahl, Bildschirm anlassen und Unterbrechung, 413 |
| U13 | eingearbeitet (7.3): 24 Stunden, „auf diesem Gerät“, `quelle` fest im Vertrag |
| U14 | eingearbeitet (4): Flächen aus HA-Variablen, eigene Text- und Statusfarben, Laufzeit-Kontrast, `--primary-ink`, drei Themes im Test (Prototyp: Theme mit hellem Primärton) |
| U15 | eingearbeitet (3.1): `narrow`, sticky statt `fixed`, Tastatur, Companion-App früh prüfen (A15b) **Rev. 5 (G19):** Prüfung in der Companion-App als **A0b** vorgezogen (15.1). |
| U16 | eingearbeitet (5.8, 5.7): Schnellwahl, „Ausblenden“ nach Technik, Kachel „Gute Nacht“ auch für belegte Tobies |
| U17 | eingearbeitet (10.3): Zeitzone ignorieren statt `unauthorized`, `erwartet_revision` |
| U18 | eingearbeitet (11.1): Änderungseintrag mit Datum, 2.1 ersetzen, W-19 streichen, Fähigkeiten reduziert, `rechte` entfällt **Rev. 5 (G22, G16):** Regel für Fähigkeiten (11.1), vorhandene Feldnamen benutzt, `kapitel` entfällt. |
| U19 | eingearbeitet (10.1): Aktionen, JavaScript ohne Anmeldung, Seitenleiste nur Komfort |
| U20 | eingearbeitet (6.1, A5): Fehlertexte vollständig aus dem Vertrag abgeleitet |
| U21 | eingearbeitet (3.3, 5.1.1, 11.2 V-3): Name unverändert, „ohne das Wort Box“, Folgenname über `serie/get`, ein Textfeld in den Optionen |
| U22 | eingearbeitet (3.1, 3.3, 5.9): „Technik“, kein Personenname, Begriffe „Das ist richtig / Das stimmt nicht“, „Zuletzt hinzugefügt“ statt „Gerade eben“ **Rev. 5 (G24):** Texte nennen „den Administrator“ (Eintrag `verwalter`), nirgends einen Personennamen (3.1, 6.1). |
| U23 | **teilweise abgelehnt:** (a) Wochenplan-Grafik, (b) Reihenfolge nur Admin, (d) Zusatzsatz, (e) „Name ändern“ im Blatt **eingearbeitet**; (c) der Reiter bleibt, aber als „Bibliothek“ (bei 500+ Einträgen unverzichtbar), die Startseite zeigt nur noch „Neu in der Bibliothek“ |
| U24 | eingearbeitet (14, 4): `<dialog>`, `getRootNode()`, Marke unten links, Fokus auf Fertig-Karte, Reiterzahl als Text |
| U25 | eingearbeitet (15): U8 geteilt (A11a/b), Rechte/Namen/Cover parallel, Texte-Paket vorweg, Playwright Pflicht (A14), Vertrag mit A1 **Rev. 5 (G13, G14):** A0 zuerst, Backend-Pakete nacheinander, Abhängigkeitsgraph, Stufe A in drei Teilen (15). |
| U26 | eingearbeitet (10.2): `konfig/export_lesen` und `ereignisse` nur Admin, „Lesen bleibt für alle“ bewusst |

