# HA-Oberfläche einfacher und schöner: Design-Entwurf Rev. 4 (EGM Schritt 2)

Stand 12.11. · **Rev. 4** (nach Runde 8 in `brainstorm.md`: Antworten auf die Fragen 14 bis 22 und die Rückmeldung zum Hochladen). Rev. 3 stand nach Runde 7 (Bibliothek wie eine Hörbuch-App, Reinhören im Browser), Rev. 2 nach dem Goldfisch-Review `review_goldfisch.md` und den Antworten Runde 4 bis 6.
Grundlage: `concepts_brief.md` (mit Abschnitt 6: Stufen A, B, C), `brainstorm.md`, `ist.md`, Vertrag W (`docs/protocol/ha-websocket-v1.md`),
`docs/data-model.md`, `docs/protocol/mqtt-v1.md`. Klickbarer Prototyp v4: `prototyp.html` (erfundene Beispieldaten; der Knopf „i“ oben schaltet Rolle, Aussehen, Zustand, Stufen und die gewählten Dateien beim Hochladen um).
Status: **Entwurf Rev. 4, wartet auf Resolve mit Tobias** (Abschnitt 16, neue Fragen 23 bis 26). Gebaut wird **Stufe A**. B und C sind geplant, haben ihren Platz in der Oberfläche
und ihre Vertragsentwürfe (Abschnitte 12, 13), werden aber erst nach Freigabe gebaut.

**Änderungen in Rev. 4** (Abschnitte, die sich geändert haben oder neu sind):

| Abschnitt | Änderung |
|---|---|
| 1, 1.3 | Kurzfassung und Änderungstabelle angepasst |
| 2 | Stufe A: Hochladen in Schritten, Einzeltitel, Hörkopien, Kapitelliste; Stufe B: „Mein Reinhören“; Stufe C: Playlist beim Hochladen, Weiterspielen über Playlist |
| 3.3 | Wort „Einzeltitel“ |
| 5.2, 5.3, 5.4 | Einzeltitel in Liste, Suche, Serienseite und als Tobie-Ziel; Hörbuch mit **Kapitelliste**; Hinweis „Hörprobe wird vorbereitet“ |
| **5.6, 7.3** | **Hinzufügen neu:** erst „Was lädst du hoch?“ (fünf Karten), dann Vorschau in Sätzen mit „Ändern“ und „Hochladen“, dann Fortschritt wie bisher; gleiche Wahl für Dateien vom NAS („Anders einsortieren“) |
| 5.9, 9 | Technik: Stand der Hörkopien; Fundorte |
| **5.10, 12.5** | **„Gehört“ bekommt den Umschalter Boxen \| Mein Reinhören**; Regel, wer was sieht (Empfehlung und Frage 23) |
| 5.12 | Kapitel im Player, Hörkopie, Zählung des Reinhörens |
| 6.1 | neue Fehlertexte (Hörkopie, Wunsch beim Hochladen, Anders einsortieren) |
| 8, 10.2 | Taps, Rechte der neuen Befehle |
| **11.1 bis 11.3** | **Vertragsänderungen, alle additiv:** V-7 (Hochladen mit Wunsch, `einsortierung/neu`), V-8 (Einzeltitel, Kapitel), V-9 (Hörkopie); neue Fähigkeiten `einsortier_wunsch`, `kapitel`, `hoerkopie`; neue Felder in `serie.json` |
| 11.4.2 | „Abspiel-Link“ in Alltagssprache |
| **11.4.3, 11.4.7, 11.4.8** | **Hörkopie** für Formate, die nicht jeder Browser spielt (Ort, Zeitpunkt, Speicherbedarf, Fehlerfall); **Kapitel** (Quelle, Speicherung, Anzeige) |
| 11.4.4, 11.4.6 | Dauer, Kapitel und Codec in einem `ffprobe`-Durchgang; Prüfstand (ffmpeg in HA belegt) |
| 12.2.1, 12.3, 12.4 | Zählregel mit 5-Minuten-Zusammenfassung ist jetzt beschlossen; Speicher und Befehle für „Mein Reinhören“ |
| 13 | Stufe C: Playlist beim Hochladen, Weiterspielen über Playlist |
| 14 | Barrierefreiheit: Wahlkarten, Kapitelliste, Umschalter |
| 15 | neue Pakete A3c, A3d; geänderte A3b, A4c, A7, A8, A8b, A11a, A11b, B3 bis B5 |
| 16 | Fragen 14 bis 22 mit Antwort, neue Fragen 23 bis 26 |
| 17 | Prototyp v4 |
| 18 | unverändert |

**Änderungen in Rev. 3** (zur Erinnerung):

| Abschnitt | Änderung |
|---|---|
| 1, 1.1 | Kurzfassung und Änderungstabelle angepasst |
| 2 | Stufe A enthält jetzt Serienseite mit Player |
| 3.1, 3.2 | Kopfzeile mit „+“ und „Technik“; neue Adresse `#suche` |
| 5.1 | Start: Suchfeld öffnet die Suchansicht, Reihe „Weiterhören“ |
| 5.2 | Bibliothek neu: Inhalt zuerst, eine Zeile Arten, Lupe, Reihen „Weiterhören“ und „Neu“, Liste im Audible-Stil, ein Knopf „Sortieren und Filter“; „Alle Folgen“ und die Filter-Stapel entfallen; Suchansicht |
| 5.3 | Serienseite wie ein Hörbuch: großes Cover, Gesamtdauer, „Reinhören/Weiterhören“, „Tobie zuordnen“, Folgenliste mit Abspielknopf und Menü |
| 5.4, 7.2, 8 | Tobie für eine Folge: jetzt über das Menü der Folge (3 Taps) oder den Suchtreffer (2 Taps) |
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

* Eine Seite „Tobi Box“ für **alle** HA-Benutzer. Reiter: **Start · Bibliothek · Tobies · Abends** (Stufe B: dazu **Gehört**). **Technik** (früher „Für Tobias“) ist
  kein Reiter, sondern ein Knopf oben rechts, nur für Administratoren.
* **Bibliothek wie eine Hörbuch-App (neu in Rev. 3, Vorbild Audible):** Cover zuerst, eine Zeile **Arten** (Hörspiele, Hörbücher, Musik, Geschichten), **Lupe** für die Suche über alles,
  **ein** Knopf „Sortieren und Filter“ (Blatt von unten), Reihen „Weiterhören“ und „Neu hinzugefügt“, Liste mit Cover, Untertitel, Fortschrittsbalken und Tobie-Symbol. Etwa 200 Hörbücher und 300 Lieder gehen ohne Blättern (Päckchen von 60).
* **Reinhören (neu in Rev. 3):** Auf der Serienseite spielt man Folgen **im Browser** an (Handy, Computer, HA-App; nicht auf der Box), mit Leiste unten, Vollansicht, ±30 Sekunden, Geschwindigkeit und **Weiterhören**: die Stelle wird je Folge und **je HA-Benutzer in Home Assistant** gemerkt (Abschnitte 5.12, 11.4).
* **Hochladen in Schritten (neu in Rev. 4):** Nach der Dateiwahl fragt die Seite zuerst **„Was lädst du hoch?“** mit fünf Karten (Neues Hörspiel, Hörbuch oder Album · Folgen zu einem vorhandenen hinzufügen · Einzelne Folge oder einzelnes Lied · Neue Playlist (Stufe C) · „Weiß nicht – sortier du“), je mit einem Satz Erklärung und einem Beispiel.
  Dann kommt eine **Vorschau in Sätzen** („3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.“) mit „Ändern“ und „Hochladen“, dann der Fortschritt wie bisher. Dieselbe Wahl gibt es für Dateien, die über den NAS-Eingang kommen („Anders einsortieren“). Abschnitte 5.6, 7.3.
* **Einzeltitel (neu in Rev. 4):** Ein einzelnes Lied oder eine einzelne Folge, die für sich steht, ist **eine Serie mit genau einer Folge und dem Kennzeichen `einzeln`**. Die Box ändert sich nicht. In der Bibliothek steht „Lied · einzeln · 1:06“, nie „1 Folge“ (Abschnitt 5.4, 11.3, Frage 24).
* **Hörkopien (neu in Rev. 4):** Formate, die nicht jeder Browser spielt (OGG, Opus, ALAC, auch FLAC und WAV), bekommen **einmal** eine kleine Kopie (AAC/M4A, 96 kbit/s), gespeichert auf dem NAS **neben** `medien/`, nicht auf den Boxen. Damit geht Reinhören überall, mit Springen, ohne Umwandeln beim Abspielen (11.4.7, Frage 26). Die Box bekommt immer das Original.
* **Kapitel (neu in Rev. 4):** Ein Hörbuch zeigt **eine Zeitleiste über alles und eine Kapitelliste** (Kapitel eines M4B/MP3 oder Tracks eines Ordners). Im Player und auf der Serienseite: Tipp aufs Kapitel springt dorthin, das aktuelle ist markiert (11.4.8).
* **„Mein Reinhören“ (Stufe B, neu in Rev. 4):** In „Gehört“ gibt es neben den Boxen einen eigenen Bereich für das, was man selbst am Handy oder Computer angehört hat. Er gehört dem HA-Benutzer; jeder sieht nur die eigenen Daten (12.5, Frage 23).
* **Ein Tobie für ein einzelnes Lied oder eine einzelne Folge:** „Tobie für diese Folge“ im Menü der Folge, Knopf „Tobie“ im Suchtreffer; bei einem Einzeltitel gleich „Tobie zuordnen“ auf seiner Seite.
* **Name beim Zuordnen gleich abfragen** (überspringbar). **Eigenes Cover per Foto vom Handy.**
* **Rechte (Runde 6):** Alltag = alle HA-Benutzer, jetzt auch **in den Papierkorb legen**. Leeren, Eingang entfernen, Zusammenführen bleiben bei Administratoren.
  Dazu Schutz gegen Fehlbedienung (Abschnitt 10).
* **Umbau ohne Bruch:** Die bisherige Technik-Seite bleibt als Komponente erhalten und wird in „Technik“ **eingebettet** (Abschnitt 5.9). Ihre 121 Tests laufen unverändert weiter.
  Die Seite wird erst nach der Abnahme für alle geöffnet.
* Alle 26 Befunde des Goldfischs sind beantwortet (Abschnitt 18).

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
| Serienseite | Kopfkarte, drei Knöpfe, Karte „Tobie anlernen“, Folgenliste mit „Tobie“ und „⋯“, Karte „Aufräumen“ | großes Cover, Gesamtdauer, **„Reinhören/Weiterhören“**, „Tobie zuordnen“, Folgenliste mit Abspielknopf, Fortschritt und „⋯“; Verwaltung im Menü „⋯“ |
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
| Reinhören und „Gehört“ | zählt nicht | eigener Bereich **„Mein Reinhören“**, nur eigene Daten (Stufe B) |
| Zählregel „einmal gehört“ | Frage 19 offen | beschlossen: Lücken bis 5 Minuten sind **eine** Wiedergabe |
| „Abspiel-Link“ (Frage 14) | Fachwort | in Alltagssprache erklärt (11.4.2, Frage 14) |

## 2. Stufen im Überblick

| Stufe | Inhalt | Stand |
|---|---|---|
| **A** | Alles aus Abschnitt 1: Bibliothek wie eine Hörbuch-App, Suche, Serienseite mit **Reinhören** und **Kapitelliste**, **Hochladen in Schritten**, **Einzeltitel**, **Hörkopien**, Tobie auf Lied/Folge, Name, Cover, Rechte, Technik-Einbettung | **wird gebaut** (Abschnitt 15) |
| **B** | Reiter „Gehört“ mit Umschalter **Boxen \| Mein Reinhören** (Hörzeit pro Tag und Box, Lieblings-Hörspiele, Tageszeiten; Reinhören je HA-Benutzer, 12.5), „Zuletzt gehört“, „Meist gehört“, Favoriten (Stern); in „Technik“ Akku-Verlauf, Ladezeiten, Laufzeit, Syncs, Fehler. Daten unbegrenzt | **geplant**, Vertragsentwurf in Abschnitt 12, Bau nach Freigabe |
| **C** | Eigene Playlists aus beliebigen Folgen und Liedern als Tobie-Ziel, Hochladen als Playlist, Reinhören und Weiterspielen über eine Playlist | **Idee**, Skizze in Abschnitt 13 |

Im Prototyp sind B und C sichtbar, aber mit den Marken „Stufe B – Vorschau“ bzw. „Stufe C – Idee“. Die Vorschau-Leiste hat dafür den Schalter „Nur Stufe A“.
In der echten Seite erscheint der Reiter „Gehört“ nur, wenn die Fähigkeit `gehoert` gemeldet wird (Abschnitt 12.4).

## 3. Navigation

### 3.1 Rahmen und Reiter (U15)

* Die Seite nutzt die Eigenschaft **`narrow`** des Panels (HA gibt sie vor, Grenze 870 px), keine eigene Media Query. Schmal: Reiter **unten**, sonst Reiter **oben**.
* Die untere Leiste ist **nicht `fixed`**, sondern `position: sticky; bottom: 0` am Ende des Seitenrahmens (der Rahmen füllt `height: 100%`, der Inhalt scrollt). So läuft sie nie unter die
  HA-Seitenleiste und springt nicht mit der Adressleiste. Bei offener Tastatur (Fokus in einem Textfeld, `visualViewport`) wird sie ausgeblendet. Unten gilt `env(safe-area-inset-bottom)`;
  ob die Companion-App die Werte liefert, prüft Tobias früh (Arbeitspaket A15).
* **Reiternamen (U22):** Start · Bibliothek · Tobies · Abends · (B) Gehört. 4 Reiter in Stufe A, 5 in Stufe B (390 px: je 75 px, Beschriftung 12 px, kurze Wörter).
  Roter Punkt am Reiter „Start“ mit Zahl hat einen Text für Screenreader („1 neuer Tobie“).
* **Kopfzeile (Rev. 3):** eine schlanke Zeile „Tobi Box“ mit rechts **„+“ (Hinzufügen, 44 px)**; „Hinzufügen“ ist kein großer Knopf mehr neben dem Titel jeder Ansicht. Auf der Startseite bleibt der große Knopf „Hinzufügen“ als ruhiger Hauptplatz (5.1).
* **Technik:** Knopf „Technik“ (Werkzeug-Symbol, 44 px hoch, am Handy nur das Symbol mit Beschriftung für Screenreader) oben rechts in der Kopfzeile, **nur für Administratoren**. Der Name trägt keinen Personennamen (U22a).
  Zeigt den Knopf nicht, wer kein Administrator ist; ruft jemand `#technik` trotzdem auf, steht dort: „Dieser Bereich ist nur für Administratoren. Wenn du etwas Technisches brauchst, frag Tobias.“

### 3.2 Unterseiten, Adressen

Unterseiten: **Suche**, **Serienseite** (Hörspiel, Hörbuch, Album, Geschichten), **Hinzufügen**, **Tobie anlernen**. Der Player ist keine Unterseite, sondern eine Leiste und eine Vollansicht über jeder Seite (5.12). Oben links „‹ Bibliothek“ bzw. „‹ Start“; Browser-Zurück geht denselben Weg.
Adressen (nach `#`, nur einfache Namen): `#start`, `#bibliothek`, `#suche`, `#serie-<id>`, `#hinzufuegen`, `#anlernen`, `#tobies`, `#abends`, `#gehoert` (B), `#technik`.
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
Die Überraschungs-Serie erscheint nur in „Technik“. **Box-Namen** setzt die Seite unverändert ein („Mond spielt …“, „Auf Mond“, „die Mond“). Die Optionen der Integration sagen:
„Name der Box ohne das Wort Box, zum Beispiel Mond“. Kein „Box Lisas Box“.

## 4. Stil (U14)

* **Flächen** (Hintergrund, Karten, Trennlinien, Schatten, Eckenradius) kommen aus **HA-Variablen** mit Rückfall: `--primary-background-color`, `--card-background-color`, `--secondary-background-color`,
  `--divider-color`, `--ha-card-border-radius`, `--ha-card-box-shadow`; Hell/Dunkel folgt `hass.themes.darkMode`, ohne eigenen Schalter.
* **Text- und Statusfarben** (Hinweis, Warnung, Fehler, Erfolg, Text auf Cover, Akzenttext) sind **eigene Token**, abgeleitet aus `--primary-text-color` und `--card-background-color` mit `color-mix()`,
  weil die HA-Standardfarben als Text auf Weiß durchfallen (`--primary-color` #03a9f4: 2,8 zu 1).
* **Primärknopf:** Fläche `--primary-color`, Schrift `--text-primary-color`. Eine kleine Funktion rechnet **zur Laufzeit** den Kontrast und wählt bei unter 4,5 zu 1 Schwarz oder Weiß.
  Für Text in Primärfarbe (Links, aktiver Reiter) gibt es das Token `--primary-ink`: so weit abgedunkelt, dass 4,5 zu 1 gegen die hellste und die dunkelste Fläche gilt.
  Der Prototyp zeigt das mit dem Aussehen „Theme mit hellem Primärton“ (Gelb): Knopfschrift wird schwarz, Linkfarbe wird dunkelgelb-braun.
* HA-eigene Elemente sparsam: nur `ha-menu-button` und `ha-icon`. Alles andere ist eigenes HTML (nativ: `<dialog>`, `<details>`, `<select>`).
* Cover-Kacheln quadratisch, Radius 12 px; Platzhalter: sechs feste Farben (aus der ID), großer Anfangsbuchstabe; die orange Marke „bitte ansehen“ sitzt **unten links** im Cover und verdeckt den Buchstaben nie (U24b).
* Tap-Ziele mindestens 44 × 44 px, Hauptknöpfe 48 px, große Startknöpfe 64 px. Schrift Roboto, Fließtext 16 px, Nebentext 14 px, nirgends unter 12 px.
* Playwright prüft mit **drei Themes** (HA-Standard hell, dunkel, ein Theme mit sehr hellem Primärton), siehe Arbeitspaket A14.

## 5. Seiten und Texte

Alle Texte wörtlich. Box-Namen sind Beispiele und kommen aus den Einstellungen der Integration (Abschnitt 11, V-3).

### 5.1 Start

Von oben nach unten:

1. **Warnband** (nur bei Bedarf, Abschnitt 6): Verbindung weg, Liste gesperrt.
2. **Status-Karten** der Boxen (am Computer nebeneinander), siehe 5.1.1.
3. **Karte „Neuer Tobie“** (nur wenn eine Box einen unbekannten Tobie meldet), Ablauf 7.1.
4. Zwei große Knöpfe: „**Hinzufügen**“ (blau) und „**Abends**“.
5. Hinweiskarte zum Hinzufügen (nur wenn etwas läuft oder angesehen werden soll): „2 Einträge werden gerade hinzugefügt.“ / „1 neuer Eintrag bitte kurz ansehen.“ / „Alles hinzugefügt.“ Ziel `#hinzufuegen`.
6. **Suchfeld** „Hörspiel, Lied, Folge oder Tobie suchen“: Absenden öffnet die Suchansicht (`#suche`, 5.2) mit dem Suchwort.
6a. **Reihe „Weiterhören“** (nur wenn etwas angefangen ist, 5.2 Punkt 4).
7. „**Neu in der Bibliothek**“: die sechs zuletzt hinzugefügten Einträge als Kacheln, darunter „Ganze Bibliothek ansehen (60)“. (Die Startseite zeigt nicht mehr das ganze Raster, U23c.) Die frühere Überschrift „Etwas suchen“ entfällt, das Feld erklärt sich selbst.
8. Stufe B: darunter „Zuletzt gehört“ (Abschnitt 5.10).

#### 5.1.1 Status-Karte der Box (ein Satz)

Links Cover des Gespielten (sonst Lautsprecher-Symbol), rechts ein **Satz**, darunter eine Zeile Nebentext. Punkt grün (online) oder grau. Quelle: `boxen/list` (`anzeige`, `online`,
`status.zustand`, `status.serie`, `status.folge`, `status.akku_prozent`, `status.lader`, `konfig_stand`). `status.folge` ist ein Dateiname; den Anzeigenamen holt die Seite **einmal je spielender Serie**
über `serie/get` (`folgen_info`), nicht über `serien/list` (U21b). Den Namen der Serie schlägt sie über `status.serie.id` in ihrer eigenen Liste nach.

| Lage | Satz | Nebentext |
|---|---|---|
| spielt | „Mond spielt „Lange Serie“ · Folge 4: Der Rabe.“ | „Akku 80 %, lädt.“ oder „Akku 80 %.“ |
| pausiert | „Mond ist pausiert bei „Lange Serie“.“ | wie oben |
| `leer`, `beendet`, `gehalten`, `unbekannt` | „Mond ist bereit. Es liegt kein Tobie auf.“ | wie oben |
| `herunterfahren` | „Mond geht gerade aus.“ | |
| Akku ≤ 20 % und kein Laden | (Satz wie oben) | „Akku fast leer (15 %). Bitte laden.“ (orange) |
| offline (`online=false`) | „Stern ist aus oder nicht im WLAN.“ | „Zuletzt gesehen: heute um 18:40. Akku war bei 35 %.“ |
| noch keine Meldung (`online=null`) | „Stern hat sich noch nicht gemeldet.“ | |
| `konfig_stand` ≠ `aktuell` **und** Box offline oder Abweichung länger als 5 Minuten (U23d) | | zusätzlich „Neue Zuordnungen kommen auf die Box, sobald sie wieder im WLAN ist.“ (kurz nach einer Änderung erscheint der Satz nicht) |


Die Karte ist kein Knopf. Technische Einzelheiten (Netz, Speicher, Version, Sync, letzte Fehler) stehen in „Technik“.

### 5.2 Bibliothek (neu in Rev. 3: wie eine Hörbuch-App)

Tobias (Runde 7): Der Reiter war „unglaublich unübersichtlich“. Oben stapelten sich Hinweisbalken, Kopf, „Hinzufügen“, Suchfeld, fünf Art-Knöpfe, ein Umschalter, vier Filter, die Sortierung und ein Zähler; der Inhalt begann erst ganz unten.
Vorbild ist jetzt **Audible**: Die Bibliothek zeigt **sofort Cover**, alles andere ist einen Tap entfernt. Aufbau von oben nach unten (Prototyp: Reiter „Bibliothek“, 390 px breit: das erste Cover endet bei 38 % der Bildschirmhöhe):

1. **Kopfzeile der Seite** (eine Zeile, für alle Reiter gleich): Titel „Tobi Box“, rechts kleine Symbolknöpfe **„+“ (Hinzufügen)** und für Administratoren **„Technik“** (am Handy nur das Werkzeug-Symbol). Der Vorschau-Hinweis des Prototyps ist ein eingeklappter Knopf „i“ in dieser Zeile, keine Leiste mehr.
2. **Zeile „Bibliothek“ mit Lupe.** Die Lupe (44 px) öffnet die **Suchansicht** (`#suche`, unten).
3. **Arten** als eine Zeile schlichter Unterreiter: **Alle · Hörspiele · Hörbücher · Musik · Geschichten** (Text mit Strich unter dem gewählten; ohne Zahlen, nur diese eine Zeile; auf schmalen Geräten scrollt die Zeile ein Stück, nicht die Seite).
4. **Zwei Reihen mit Covern** (nur bei „Alle“ und ohne Sortierung oder Filter): **„Weiterhören“** (angefangen, nicht fertig; sortiert nach zuletzt angehört; Cover mit Fortschrittsbalken, „noch 21 Min.“ und einem Abspielknopf auf dem Cover) und **„Neu hinzugefügt“** (die acht neuesten). Tippen aufs Cover öffnet die Serienseite (5.3), der Abspielknopf spielt sofort weiter.
5. **Liste im Audible-Stil:** Eine Zeile je Eintrag, mindestens 84 px hoch: **Cover links** (72 px), **Titel**, darunter **Untertitel „Hörspiel · 12 Folgen · 26 Min.“** (bei Hörbüchern „Hörbuch · 14 Kapitel · 9 Std. 40 Min.“, bei Musik „Musik · 20 Lieder · 1 Std. 12 Min.“), bei angehörten Einträgen ein **Fortschrittsbalken** mit „noch 18 Min.“ bzw. „Fertig gehört“,
   rechts ein **kleines Tobie-Symbol mit Anzahl**, wenn ein Tobie auf den Eintrag oder eine seiner Folgen zeigt, und die orange Marke „bitte ansehen“. Die ganze Zeile ist ein Link zur Serienseite. Blättern in Päckchen von 60 („Mehr zeigen“).
6. **Ein Knopf „Sortieren und Filter“** über der Liste, rechts neben der Zählzeile („60 Einträge“, `aria-live`), mit einem Zahlenpunkt, wenn etwas eingestellt ist. Er öffnet ein **Blatt von unten** (natives `<dialog>`): **Sortieren** (A bis Z, Zuletzt hinzugefügt, **Zuletzt angehört**) und **Nur zeigen** (**Ohne Tobie**, **Neu** in den letzten 14 Tagen, **Bitte ansehen**; mehrere gleichzeitig). Die Liste ändert sich dahinter sofort; „Zurücksetzen“ und „Fertig“.
   Stufe B ergänzt **Zuletzt gehört (Box)** und **Meist gehört** sowie **★ Favoriten**. „Zuletzt angehört“ meint das Reinhören am Handy oder Computer (5.12), „Zuletzt gehört“ die Box (5.10); die Namen bleiben getrennt.
   **Rev. 4:** Das Blatt hat eine dritte Gruppe **„Was zeigen“** (ein Tap, wählt eines): **Alles · Nur Hörspiele, Bücher, Alben · Nur Einzeltitel (einzelne Lieder und Folgen)**. Sie zählt wie die anderen Einstellungen am Zahlenpunkt des Knopfes mit. Backend: `filter` bekommt die Werte `sammlung` und `einzeln` (V-8).
   **Einzeltitel in der Liste (Rev. 4):** wie jede Zeile, aber der Untertitel heißt „**Lied · einzeln · 1:06**“ (bei Geschichten „Geschichte · einzeln · 1:39“, bei Hörbüchern „Hörbuch · einzeln · …“); nie „1 Folge“. Sie stehen unter ihrer Art (ein Lied unter „Musik“). 300 einzelne Lieder bleiben damit bedienbar: Arten-Zeile „Musik“ plus „Nur Einzeltitel“ oder „Nur Hörspiele, Bücher, Alben“ trennt sie von den Alben.

**Gestrichen gegenüber Rev. 2:** der Umschalter **Kacheln | Alle Folgen**, die Art-Knöpfe mit Zahlen, die vier Filter-Knöpfe in der Seite, das Auswahlfeld zum Sortieren, das Suchfeld im Seitenkopf und der große „Hinzufügen“-Knopf neben dem Titel. Einzelne Folgen und Lieder findet man jetzt **über die Suche und über die Serienseite**.
Das Backend bleibt dasselbe (`folgen/list` bedient die Suche und die Zielwahl „Einzelne Folge oder Lied“, 5.4); nur die Seite zeigt den Umschalter nicht mehr.

**Suchansicht (`#suche`).** Zeile mit Zurück-Pfeil und Suchfeld „Hörspiel, Lied, Folge oder Tobie“ (der Fokus liegt gleich im Feld). Ab 2 Zeichen (Verzögerung 250 ms, Umlaute und Groß/Klein egal) erscheinen drei Gruppen mit der Zählzeile „Gefunden: 6 Sammlungen, 102 Folgen und Lieder, 0 Tobies“:
**„Hörspiele, Bücher, Alben“** (Listenzeilen wie oben, höchstens 8, Treffer hervorgehoben, **ohne Einzeltitel**), **„Folgen und Lieder“** (Zeile mit kleinem Cover, Titel, „Serie · Dauer“ bzw. bei einem Einzeltitel „Einzeltitel · Dauer“, **Abspielknopf** und Knopf „Tobie“, höchstens 10) und **„Tobies“** (nach Tobie-Name). Mehr Treffer: „… und 7 weitere. Genauer suchen hilft.“
Kein Treffer: „Nichts gefunden zu „xyz“.“ Leer: „Tippe mindestens 2 Buchstaben. Gesucht wird in Hörspielen, Büchern, Alben, Folgen, Liedern und in den Namen der Tobies.“ Art und Filter der Bibliothek gelten **nicht** für die Suche (sie sucht über alles). Die Startseite hat weiter ihr Suchfeld; Absenden öffnet `#suche` mit dem Wort.

**Leistung (500+ Einträge).** (1) Das Backend blättert (`limit`/`offset`, V-2); die Seite lädt 60 und bei „Mehr zeigen“ die nächsten 60. Suchen, Filtern und Sortieren macht das Backend (Index im Speicher der Integration, Ziel unter 200 ms bei 600 Einträgen und 2 000 Folgen). „Zuletzt angehört“ kennt nur das Backend (die Hörstellen liegen dort, 11.4).
(2) Listenzeilen tragen `content-visibility: auto`; eine eigene virtuelle Liste ist **nicht** nötig (bis 1 000 Zeilen im Dokument geprüft). (3) Cover laden erst, wenn die Zeile sichtbar wird (`IntersectionObserver`), in der kleinen Größe 192 px (ca. 15 KiB, V-1), als `blob:` zwischengespeichert nach `cover_stand`. Bei 60 Zeilen sind das etwa 1 MB statt 8 MB.
(4) Optional: Sprungleiste „A B C …“ bei A bis Z.

### 5.3 Serienseite (Hörspiel, Hörbuch, Album, Geschichten): wie ein Hörbuch oder Album

Aufbau (Prototyp: `#serie-<id>`); oben „‹ Bibliothek“ und rechts ein Drei-Punkte-Knopf für den Eintrag:

* **Kopf:** **großes Cover** (bis 190 px am Handy, 220 px am Computer neben dem Text), **Titel**, „**Hörspiel · 12 Folgen · 26 Min.**“ (Art, Anzahl, **Gesamtdauer**), „2 Tobies“ (kleines Tobie-Symbol) und bei angehörten Einträgen „Schon 18 % gehört · noch 21 Min.“.
* **Großer Knopf „Reinhören“** (56 px, Hauptknopf). Nach dem ersten Anhören heißt er **„Weiterhören“** mit dem Zusatz „Folge 3: Die alte Mühle · ab 0:47“; ist alles gehört, „Noch einmal hören“; während der Wiedergabe „Pause“. Er startet den Player (5.12, Hörstelle des angemeldeten Benutzers).
* Darunter ein zweiter Knopf **„Tobie zuordnen“**: öffnet das Blatt „Tobie für dieses Hörspiel“ (5.4: „Auf Mond / Auf Stern“, „Tobie wählen …“). Die frühere Karte „Tobie dafür anlernen“ entfällt als eigene Karte.
* Falls zu prüfen: gelbe Karte „**Bitte kurz ansehen.** <Grund, Abschnitt 7.3>“ mit **„Das ist richtig“** und **„Das stimmt nicht“** (U11; „Anderem zuordnen …“ oder abgesetzt „In den Papierkorb …“). Unverändert.
* Abschnitt „**Folgen**“ (bei Alben „Lieder“, bei Hörbüchern „Hörbuch“): Eine Zeile je Folge mit **Nummer**, **Titel**, **Dauer** („2:19“, bei Ordner-Folgen „· 14 Kapitel“), „1 Tobie“ falls einer darauf zeigt, **Fortschritt** (Balken mit „noch 1:23“, oder „Fertig gehört“ mit Häkchen, oder bei der laufenden „läuft“/„pausiert“), einem runden **Abspielknopf** (48 px; spielt genau diese Folge, bei der laufenden „Pause“) und dem **Drei-Punkte-Menü**.
  Ab 20 Folgen ein Suchfeld „Hier suchen“ und „Mehr zeigen“.
* **Menü der Folge („⋯“):** „**Tobie für diese Folge**“ (5.4), „**Name ändern**“, „**In anderes verschieben …**“, abgesetzt „**Papierkorb …**“ mit Rückfrage. Rechte wie in Rev. 2 (Abschnitt 10: alle Benutzer, nur in den Papierkorb; nichts endgültig). Das frühere „Tobie“-Knöpfchen in der Zeile entfällt (ein Tap mehr, dafür ruhige Zeilen; im Suchtreffer bleibt es).
* **Menü des Eintrags („⋯“ oben rechts):** „**Name ändern**“, „**Cover ändern**“ (5.5), „**Art ändern**“ (Blatt „Was ist das?“), nur Administratoren „**Reihenfolge ändern**“ (▲/▼ je Zeile, kein Ziehen) und „**Mit anderem zusammenführen …**“, abgesetzt „**In den Papierkorb …**“ (Rückfrage nennt Tobies, die dann nichts mehr spielen, mit Namen; „Tobias kann es aus dem Papierkorb zurückholen.“). Die frühere Karte „Aufräumen“ unten entfällt.

* **Hörbuch mit Kapiteln (Rev. 4, Runde 8 Nr. 20):** Hat ein Hörbuch **eine** Folge mit Kapiteln (Datei mit eingebetteten Kapiteln oder Ordner mit Tracks), steht statt der Folgenliste der Abschnitt **„Kapitel“**: Satz „12 Kapitel. Tippe auf ein Kapitel, dann geht es dort los. Im Player kannst du über das ganze Buch springen.“, darunter eine Zeile je Kapitel mit **Nummer** (bei schon gehörten ein Häkchen), **Titel**, „**ab 2:49 · 0:19**“ (Start und Länge), Abspielknopf (44 px); das **Kapitel der gemerkten Stelle** ist markiert (`aria-current="true"`, getönte Fläche, „hier weiter“ bzw. „läuft“). Tipp auf eine Zeile springt dorthin und spielt (Quelle der Kapitel: 11.4.8). Die **Zeitleiste über das ganze Buch** liegt im Player (5.12); Kopfbereich („Schon 30 % gehört · noch 3 Min.“) und „Weiterhören“ bleiben wie bei anderen Einträgen.
* **Einzeltitel (Rev. 4):** Die Seite hat Kopf (Cover, Titel, „Lied · einzeln · 1:01“), „Reinhören/Weiterhören“ und „Tobie zuordnen“, aber **keine Folgenliste**; stattdessen ein Satz „Das ist ein einzelnes Lied. Es steht für sich und gehört zu keinem Album. Du kannst einen Tobie dafür anlernen.“ Das Menü „⋯“ hat Name, Cover, Art und Papierkorb wie jeder Eintrag.
* **Hörprobe wird vorbereitet (Rev. 4):** Braucht eine Folge eine Hörkopie (11.4.7) und ist sie noch nicht fertig, steht oben eine Karte „**Die Hörprobe wird gerade vorbereitet.** Dieses Format (OGG) spielt nicht jeder Browser. Home Assistant legt dafür einmal eine kleine Kopie an. Probiere es in ein paar Minuten noch einmal. Auf der Box spielt es schon.“; „Reinhören“ zeigt dann denselben Satz kurz als Meldung und startet nichts.

### 5.4 Tobie für ein einzelnes Lied oder eine einzelne Folge (neu für alle)

Das Datenmodell kennt das schon (`ziel.typ="folge"`, `data-model.md` 2, `lernmodus/start` mit Ziel `folge`); neu ist, dass es **sichtbar einfach** wird:

* Für eine Folge oder ein Lied gibt es **„Tobie für diese Folge“** im Menü „⋯“ der Folgenzeile (5.3) und den Knopf **„Tobie“** im Suchtreffer (5.2).
* Er öffnet das Blatt „**Tobie für dieses Lied**“ (bzw. „… diese Folge“, „… dieses Hörbuch“, „… diese Geschichte“): „Der Tobie spielt dann nur „Backe, backe Kuchen“ aus „Kinderlieder zum Mitsingen“.“
  Zwei Wege: **„Neuen Tobie anlernen: Auf Mond / Auf Stern“** (Lernmodus mit Ziel Folge, Ablauf 7.2) und **„Tobie wählen …“** (einen bereits belegten Tobie auf dieses Lied umstellen; Tippen = gespeichert, „Fertig: Löwe spielt jetzt „…““).
  Gibt es schon einen Tobie dafür, steht oben „Schon angelernt: Gelber Hase.“ Stufe C: darunter der ausgegraute Knopf „Zu einer Playlist hinzufügen“ (Marke „Stufe C – Idee“).
* In der Karte „Neuer Tobie“ (Start) und im Blatt „Tobie umstellen“ gibt es eine **Zielwahl** mit Suche und Art-Knöpfen und dem Umschalter „**Ganzes Hörspiel, Buch, Album | Einzelne Folge oder Lied**“; so findet man auch ein Lied unter 572 Folgen (Suche, ein Tap).
* Tobies mit Ziel Folge heißen in der Tobies-Liste „spielt „Backe, backe Kuchen“ aus „Kinderlieder zum Mitsingen“ (ein Lied)“.

* **Einzeltitel als Ziel (Rev. 4):** Auf der Seite eines Einzeltitels heißt das Blatt „Tobie für dieses Lied“ (bzw. „… diese Folge“, „… diese Geschichte“) und der Satz „Der Tobie spielt dann „Der Mond und der Fuchs“.“ (ohne „aus …“, weil es keinen Eintrag darum gibt). Gespeichert wird `ziel.typ = "folge"` mit der Serie des Einzeltitels (Empfehlung in 11.3 und Frage 24); in der Tobies-Liste steht „spielt „Der Mond und der Fuchs“ (ein Lied)“. In der Zielwahl (Neuer Tobie, „Etwas anderes spielen“) erscheinen Einzeltitel **nur** unter „Einzelne Folge oder Lied“, nicht unter „Ganzes Hörspiel, Buch, Album“.

### 5.5 Cover (U5, U8, Runde 6)

Zwei Quellen, eine Anzeige: **eigenes Foto** hat Vorrang vor dem **automatischen Cover** (aus den Tags), das vor dem **Platzhalter** (Farbe und Anfangsbuchstabe) kommt.

**Cover ändern (Alltag, Eintrag → „Cover ändern“).** Blatt „Cover für „Lange Serie““: Auswahlfeld „Foto wählen“ (`<input type="file" accept="image/*">`; am Handy bietet das System Kamera und Galerie).
Danach **Zuschneiden im Browser**: quadratische Vorschau (280 px), verschieben mit Finger oder Maus **und** mit vier Pfeilknöpfen (nicht nur Ziehen), Regler „Ausschnitt größer oder kleiner“. Der Browser zeichnet das Quadrat auf
1 024 × 1 024 px (Ausrichtung nach den EXIF-Angaben des Fotos), kodiert JPEG (Qualität 0,85, bei mehr als 1,5 MiB mit weniger Qualität) und sendet **nur das Quadrat**. „Speichern“ lädt hoch, „Abbrechen“ verwirft.
Abgesetzt, wenn ein eigenes Foto da ist: Textknopf „Zurück zum automatischen Cover“.
**Grenzen:** Foto vom Handy bis 20 MB (die Seite verkleinert vor dem Hochladen, Meldung „Das Foto ist zu groß (mehr als 20 MB). Nimm ein kleineres.“; kein Bild: „Das ist kein Bild. Bitte ein Foto wählen.“);
hochgeladen wird höchstens **3 MiB**; das Backend prüft Typ (Kopfbytes JPEG), Maße (höchstens 2 048 px, quadratisch bis auf 2 %) und rechnet selbst auf 512 px und 192 px herunter, speichert nie die Originaldatei.
Vertrag: V-1.

**Automatisches Cover (U5).** Beim Einsortieren liest die Integration das eingebettete Bild (ID3 `APIC`, MP4 `covr`, FLAC `PICTURE`) der ersten Folge, die eines hat; **Vorrang** hat ein mitgeliefertes `cover.jpg`/`folder.jpg`/`cover.png` im Ordner (U8c).
Je Eintrag eine **Marke „schon gesucht“** (`cover_suche`: Ergebnis `tags`, `datei` oder `keine`, mit Zeit) in `serie.json`. Nachholen für bestehende Einträge **nur** (a) einmal im Hintergrund nach dem Start der Integration, (b) für Einträge ohne Marke,
(c) mit Zeitgrenze 20 s je Datei und Abbruch bei `medien_nicht_erreichbar`. Neue Folgen in einem Eintrag mit Marke `keine` lösen genau eine neue Suche aus. **Kein Dauer-Scan:** `medien/pruefen` startet keine Cover-Suche mehr beim Öffnen der Seite;
die Seite ruft `medien/pruefen` höchstens alle 10 Minuten und nur, wenn sie sichtbar ist. Fehlt `ffmpeg`: Fähigkeit `cover` wird nicht gemeldet, die Seite zeigt Platzhalter, keine Fehlermeldung.
Administratoren haben in „Technik → Bibliothek aufräumen“ den Knopf „Cover neu suchen“ (löscht `cover.jpg` und Marke, nie ein eigenes Foto).

**Auf den Boxen:** `cover*.jpg` wird **nicht synchronisiert** (U8, Empfehlung übernommen; Abschnitt 11.3). Eine Box ohne Display braucht kein Cover, und es spart SD-Platz und Schreibvorgänge. Ein späteres Display bräuchte eine neue Entscheidung.

### 5.6 Hinzufügen

Siehe Ablauf 7.3. Aufbau der Seite: „‹ Start“, Überschrift „Hinzufügen“; große Knöpfe „**Dateien wählen**“ (Handy und Computer) und „**Ordner vom Computer wählen**“ (U12a: **nur** bei `matchMedia('(pointer: fine)')`, am Handy nicht);
am Computer zusätzlich eine Fläche „Auf dem Computer kannst du Dateien oder einen ganzen Ordner auch hierher ziehen.“ Nebentext: „Hörspiele, Hörbücher, Musik, Geschichten. Erlaubt: MP3, M4A, M4B, AAC, FLAC, OGG, Opus, WAV.
Bis 500 MB je Datei. Kopiergeschützte Dateien (zum Beispiel von Audible) gehen nicht. **Lass den Bildschirm an, bis alles fertig ist.**“ (U12d; die Zahl aus `hello.grenzen.upload_max_bytes`).
Hinweiskarte: „Du kannst Dateien auch am Computer in den Eingang-Ordner auf dem NAS kopieren. Sie erscheinen hier von selbst und werden nach den Angaben in den Dateien einsortiert. Stimmt etwas nicht, kannst du es hier anders einsortieren. Frag Tobias nach dem Ordner.“ Darunter „**Zuletzt hinzugefügt**“ (Einträge der **letzten 24 Stunden**, U13).

**Neu in Rev. 4: nach der Dateiwahl öffnet sich das Blatt „Was lädst du hoch?“** (Anlass: Tobias verstand das Blatt „In welches soll es?“ mit „Abbrechen / In ein bestehendes wählen … / Automatisch (nach den Dateien)“ nicht). Es ist ein Blatt von unten (natives `<dialog>`) mit der Zeile „3 Dateien gewählt (01 Der Hafen.mp3 …). Was ist das?“ und **fünf Karten**, je mit Symbol, Titel, **einem Satz Erklärung** und **einem Beispiel**. Die Karten sind große Knöpfe (mindestens 76 px hoch), kein Fachwort:

| Karte | Erklärung | Beispiel |
|---|---|---|
| **Neues Hörspiel, Hörbuch oder Album** | „Alle Dateien gehören zusammen und werden etwas Neues.“ | „Zum Beispiel: die Kapitel eines Hörbuchs oder alle Lieder einer CD.“ |
| **Folgen zu einem vorhandenen hinzufügen** | „Die Dateien kommen zu etwas, das schon da ist.“ | „Zum Beispiel: zwei neue Folgen zu „Lange Serie“.“ |
| **Einzelne Folge oder einzelnes Lied** | „Jede Datei steht für sich, ohne Serie.“ | „Zum Beispiel: ein Lied, das ein Tobie spielen soll.“ |
| **Neue Playlist** (Marke „Stufe C – Idee“, gestrichelter Rand, antippbar nur mit Meldung „Playlists gibt es noch nicht. Das kommt später (Stufe C).“) | „Eine eigene Liste aus Liedern und Folgen.“ | „Zum Beispiel: „Autofahrt“ mit fünf Lieblingsliedern.“ |
| **Weiß nicht – sortier du** (früher „Automatisch“) | „Ich lese die Angaben in den Dateien und sortiere selbst ein.“ | „Wenn ich unsicher bin, steht danach „Bitte ansehen“ da.“ |

Das Blatt hat nur „Abbrechen“ (Esc und Tippen daneben ebenso). **Ein Tap auf eine Karte** führt zur **Vorschau** (7.3): Dort steht ein Satz, was geschehen wird, darunter genau die Eingaben, die dieser Weg braucht (Name und Art; die Wahl eines vorhandenen Eintrags mit Suche und Covern; ein Name je Datei), und die Knöpfe „Abbrechen“, „**Ändern**“ (zurück zu den Karten) und „**Hochladen**“.
Die Karte „Neue Playlist“ erscheint nur, wenn Stufe C gezeigt wird (im Prototyp: „A, dazu B und C“). Aus dem Eintrag heraus („Dateien in diesen Eintrag“, `serie_id`) wird das Blatt übersprungen: der Weg ist dann „zu einem vorhandenen hinzufügen“.

### 5.7 Tobies

* Überschrift „Tobies“, Satz: „Alle Tobies, die schon etwas spielen. Der zuletzt angelernte steht oben. Einen neuen legst du einfach auf eine Box. Dann erscheint er auf der Startseite.“
* **Sortierung: zuletzt angelernt zuerst** (U4; braucht ein Zeitfeld, V-5), dazu ein **Suchfeld** „Tobie suchen (Name oder was er spielt)“.
* Zeile: kleines Cover des Ziels, Name oder „Tobie ohne Namen“, „spielt „Lange Serie““ bzw. „… (ein Lied)“, Knopf „Ändern“. Aktionskarte: Mond-Symbol, „spielt „Gute Nacht““.
* Tippen öffnet ein Blatt: „**Namen ändern**“, „**Etwas anderes spielen**“ (Zielwahl wie in 5.4, **mit Kachel „Gute Nacht“**, U16c), abgesetzt „**Diesen Tobie vergessen …**“ (Rückfrage; Backend: `zuordnung/remove` mit `erwartet_ziel`).
  Bestätigung nach dem Umstellen: „Fertig: spielt jetzt „…“.“
* **Auflegen zum Finden** (U4, wenn die Box die Kennung beim Auflegen meldet, V-5): Die Zeile des aufgelegten Tobies wird hervorgehoben. Fehlt das Datenfeld, bleiben Name, Sortierung und Suche.
* Leer: „Noch keine Tobies. Lege einen Tobie auf eine Box, dann erscheint er auf der Startseite.“
* Stufe C: darunter die Karte „Playlist“ (5.11).

### 5.8 Abends

Zwei Karten. **Gute Nacht**: „Lege den Gute-Nacht-Tobie auf. Dann läuft ein Timer. Danach wird es leise und die Box hört auf.“ „Die Box spielt noch“ mit **Schnellwahl 15 · 30 · 45 · 60 · 90 Minuten** (Knöpfe, U16a) und einem Auswahlfeld „Anderer Wert …“ (5 bis 240 Minuten).
Knopf „Speichern“ (grau mit „Gespeichert“, solange nichts geändert ist). Das **Ausblenden** („Dann wird sie leiser über …“) ist ein selten geänderter technischer Wert und liegt in „Technik → Weitere Einstellungen“ (U16b).
Darunter „Ein Gute-Nacht-Tobie ist angelernt („Mond-Karte“).“ bzw. „Noch kein Gute-Nacht-Tobie.“ und „So legst du einen an“: Neuer Tobie auflegen und Kachel „Gute Nacht“ wählen **oder** einen bereits belegten Tobie unter „Tobies“ umstellen (U16c).

**Leise-Zeiten**: „In diesen Zeiten ist die Box leiser oder still.“ Zeilenliste, je Zeit: „**Mo–Do, So** · 19:30 bis 06:30 (bis zum nächsten Morgen) · Stumm“ mit „Ändern“; Knopf „+ Zeit hinzufügen“. Die **Wochenplan-Grafik entfällt in Stufe A** (U23a: Zeilen und Grafik sagen dasselbe; Mitternachtsfälle sind die kniffligste Stelle); sie kann später folgen.
Blatt „Leise-Zeit ändern“ unverändert gegenüber Rev. 1: Tag-Knöpfe 44 px mit `aria-pressed`, Schnellwahl „Jeden Tag“, „So–Do“, „Fr, Sa“, „Von“/„Bis“ als Stunde und Minute (24 Stunden, 5-Minuten-Schritte, eine krumme vorhandene Minute bleibt),
„Was soll die Box tun?“ **Still | Leiser** (bei Leiser Regler „Höchste Lautstärke: 25 %“), Löschen abgesetzt mit Rückfrage. Prüfregeln: mindestens ein Tag, „Von“ ≠ „Bis“, höchstens 32 Zeiten.
Meldung: „Gespeichert. Die Boxen bekommen es gleich.“ Die **Zeitzone** zeigt die Seite nicht; das Backend nimmt für Nicht-Administratoren den gespeicherten Wert (V-4, U17).

### 5.9 Technik (nur Administratoren, U6, U7)

* Oben gelbe Karte: „**Nur für Administratoren.** Hier liegt alles Technische. Normale Benutzer sehen diesen Bereich nicht.“ (kein Personenname, U22b).
* **Einbettung statt Umbau (U6):** Die bestehende Komponente (`tobibox-panel.js`) wird umbenannt (`tobibox-technik`) und bekommt einen Schalter `eingebettet`, der ihre eigene Kopfzeile und Reiterleiste ausblendet.
  Sie zeigt weiter genau ihre heutigen Reiter-Inhalte (Eingang, Papierkorb, Liste/Revision/Export, Boxen, Einstellungen, Meldungen). Die 121 Tests (`panel.test.mjs`, `panel_quiet.test.mjs`) bleiben **unverändert** und grün;
  das belegt „nichts geht verloren“. Die neue Alltagsseite entsteht daneben in neuen Dateien mit eigenen Tests. Erst danach, wenn Tobias will, wird die eingebettete Seite in aufklappbare Karten zerlegt (reine Schönheit).
* **Neu in „Technik“ (Stufe A):** Karte „Bibliothek aufräumen“ (Medien neu einlesen, Cover neu suchen, Neues leeres Hörspiel, Überraschungs-Serie, Zusammenführen), Karte „Liste, Sicherung, Export“ um **„Frühere Stände ansehen“** ergänzt (die letzten 10 Stände der Liste, U2),
  „Weitere Einstellungen“ um das Ausblenden bei Gute Nacht ergänzt. Das **Papierkorb-Leeren** und „Eingang entfernen“ stehen nur hier.
  **Rev. 4:** Die Karte „Bibliothek aufräumen“ zeigt den Stand der **Hörkopien** („41 fertig, 3 warten, 0 mit Fehler · 2,1 GB auf dem NAS“) und den Knopf „Hörkopien neu erzeugen“ (`hoerkopie/neu_erzeugen`, nur Administratoren).
* **Stufe B:** Karte „Akku-Verlauf“ je Box mit Liniendiagramm (Prozent über 3 Tage, Ladezeiten als Bänder), Laufzeit je Ladung, Ladezeiten, Syncs, Fehler als Liste, Knöpfe „Hördaten als Tabelle sichern“ (CSV) und „Alle Hördaten löschen …“ (Rückfrage). Abschnitt 12.
* Die Warnleisten zur Liste (`leer_neu`, `export_neuer`, Box mit neuerem Stand) erscheinen für Administratoren oben auf allen Seiten wie heute; Nicht-Administratoren sehen nur den Hinweis aus Abschnitt 6.

### 5.10 Gehört (Stufe B, Vorschau im Prototyp)

Eigener Reiter für alle, **nur wenn die Fähigkeit `gehoert` gemeldet wird**. Oben ein Hinweis „Stufe B – Vorschau“ (nur im Prototyp). Aufbau:

* **Umschalter (Rev. 4, Runde 8 Nr. 21):** Ganz oben zwei gleich breite Knöpfe **„Boxen“ | „Mein Reinhören“** (`aria-pressed`). „Boxen“ ist alles, was unten bis „Favoriten“ steht. „Mein Reinhören“ ist der eigene Bereich für das Hören am Handy oder Computer, mit eigener Regel, wer es sieht (5.10.1, 12.5, Frage 23).
* **Auswahl:** **Box** (Beide Boxen · Mond · Stern; die Namen sind die der Kinder, die Tobias in den Optionen einträgt) und **Zeitraum: Woche · Monat · Jahr · Alles** (Woche = letzte 7 Tage, Monat = 30, Jahr = 365, immer bis jetzt gerechnet; Abschnitt 12.4).
* **Rangliste „Wer hat was gehört?“** (neu in Rev. 3, Wunsch von Tobias): je gewählter Box eine Liste der Hörspiele (auch Alben und Bücher) nach **Anzahl Mal gehört**, mit den Spalten **Mal** (Wiedergaben), **Hörzeit** („9:48 Std.“) und **Fertig** („17/20“: so viele Folgen wurden mindestens einmal ganz gehört). Die ersten 10, Zeilen sind Knöpfe.
  **Ein Tap auf ein Hörspiel** öffnet **„Aufteilung nach Folgen“** mit **denselben Spalten je Folge** (Mal, Hörzeit, **Fertig = wie oft die Folge ganz gehört wurde**, „2×“; nicht gehörte Folgen grau mit „0“ und „–“), darunter die Summe; „‹ Rangliste“ geht zurück.
  Darunter eine aufklappbare Erklärung „**Was wird gezählt?**“ (Definition in 12.2). „Beide Boxen“ addiert die Zahlen.
* **Hörzeit pro Tag:** Säulendiagramm (SVG), je Tag eine Säule je Box, Achse „Minuten“ 0 bis 90 mit Linien bei 30, 60, 90, Zahl über jeder Säule (bei 7 Tagen), Tage mit Wochentag und Datum, Legende „Mond / Stern“. Bei „Woche“ 7 Tage, sonst die Tage der Beispieldaten (in der echten Seite: Monat in Tagen, Jahr in Wochen, Alles in Monaten).
  Darunter „Zahlen als Tabelle“. Satz darüber: „In den letzten 7 Tagen: 9 Std. 53 Min. (Mond 5 Std. 58 Min., Stern 3 Std. 55 Min.).“
* **Tageszeiten:** 24 Säulen (Stunde 0 bis 23), Achse Minuten; Satz „am meisten um 19 Uhr“.
* **Zuletzt gehört**, **Favoriten:** Kachel-Reihen (waagerecht scrollbar). Der **Stern** (Favorit) steht in jedem Eintrag und in jeder Folgenzeile; gilt für alle in der Familie. (Das frühere Balkendiagramm „Lieblings-Hörspiele“ und die Reihe „Meist gehört“ sind in der Rangliste aufgegangen; „Meist gehört“ bleibt als Sortierung der Bibliothek.)
* Farben der Diagramme sind Token (`--chart1`, `--chart2`, `--grid`), in Hell und Dunkel geprüft (3 zu 1 gegen die Karte). Jedes Diagramm hat `role="img"` mit Beschreibung und eine Tabelle; die Rangliste ist selbst eine Tabelle (Spaltenköpfe, Zeilen mit vollständigem `aria-label`).
* Das Reinhören am Handy (5.12) zählt in der Ansicht „Boxen“ **nicht** mit; sie zeigt nur, was an den Boxen lief. Das Reinhören hat den eigenen Bereich „Mein Reinhören“ (5.10.1). Die Kennung des Tobies kommt nirgends vor.

#### 5.10.1 Mein Reinhören (Stufe B, Vorschau im Prototyp)

Zweiter Teil des Reiters „Gehört“, zu wählen mit dem Umschalter. Er zeigt, was **der angemeldete HA-Benutzer** (nicht eine Box) sich in der Seite angehört hat. Aufbau von oben nach unten:

* **Hinweiskasten:** „**Nur du siehst das.** Hier steht, was du selbst am Handy oder Computer angehört hast, mit deinem Home-Assistant-Konto (<Anzeigename>). Andere Benutzer sehen es nicht, auch Administratoren nicht. Was die Boxen gespielt haben, steht unter „Boxen“.“
* **Zeitraum:** Woche · Monat · Jahr · Alles (wie bei den Boxen). Keine Box-Auswahl.
* **Rangliste „Was habe ich mir angehört?“** mit denselben Spalten (Mal, Hörzeit, Fertig), Aufteilung nach Folgen und „Was wird gezählt?“ (Zusatz: „Gezählt wird, was du selbst am Handy oder Computer anhörst.“). Einzeltitel stehen hier mit ihrem Titel.
* **Hörzeit pro Tag** als Säulendiagramm (eine Farbe, Legende „Ich“; Zahlen als Tabelle).
* Karte **„Meine Reinhör-Daten“**: „Sie liegen nur in Home Assistant, bei deinem Konto. Du kannst sie jederzeit löschen. Die Stelle zum Weiterhören bleibt dabei erhalten.“ mit Knopf „Meine Reinhör-Daten löschen …“ (Rückfrage; löscht nur die eigenen).
* **Nicht dabei:** Tageszeiten, „Zuletzt gehört“ und Favoriten (die gelten für die Familie und die Boxen).

Zählregel und Herkunft der Daten: 12.5.

### 5.11 Playlist (Stufe C, Idee)

Nur ein Platz: Im Reiter „Tobies“ eine Karte „Playlist „Autofahrt““ mit nummerierten Einträgen (Lied oder Folge, ▲/▼), Knöpfen „Lied oder Folge hinzufügen“ und „Tobie für die Playlist anlernen“; im Blatt „Tobie für dieses Lied“ der Knopf „Zu einer Playlist hinzufügen“.
Im Prototyp ausgegraut, mit der Marke „Stufe C – Idee“. Datenmodell und Auswirkungen: Abschnitt 13.

### 5.12 Reinhören: Bedienung (neu in Rev. 3)

**Wozu:** Man soll am Handy oder Computer **hineinhören**, um zu erkennen, was etwas ist (Runde 7), ohne eine Box zu bemühen. **Nur im Browser** (Handy, Computer, HA-App); **nicht auf der Box**. Es zählt **nicht** bei den Hörzeiten der Boxen in „Gehört“, aber (Stufe B, Rev. 4) im eigenen Bereich „Mein Reinhören“ des angemeldeten Benutzers (5.10.1, 12.5).
**Wer darf:** **alle HA-Benutzer** (Entscheidung Runde 7, wie Runde 6).

* **Schmale Leiste unten** (Mini-Player), sobald etwas gespielt wurde: Cover, Folgentitel, Name des Eintrags, runder Play/Pause-Knopf (48 px), dünner Fortschrittsstrich oben. Sie sitzt **über** der Reiterleiste (sticky, nie unter der HA-Seitenleiste) und verschwindet bei offener Tastatur. Tippen auf die Leiste öffnet die Vollansicht, auf den Knopf schaltet Play/Pause.
  Nach dem Neuladen der Seite steht die Leiste wieder da (pausiert, bei der gemerkten Stelle, **ohne Ton**); Ton startet **nur nach einem Tap**.
* **Vollansicht** (natives `<dialog>`; am Handy ganze Fläche, am Computer ein Blatt): „Läuft gerade“, **großes Cover**, Titel, „Eintrag · 2 von 20“, **Zeitleiste** (Schieberegler 44 px hoch mit `aria-valuetext` „1:41 von 2:47“, Zeit links, Restzeit rechts), **Vorige Folge · 30 s zurück · Play/Pause (72 px) · 30 s vor · Nächste Folge**, **Geschwindigkeit 1× · 1,25× · 1,5×** (gilt für alle Folgen, wird gemerkt). Kein Schlaftimer (nicht gewünscht). „Vorige Folge“ springt bei mehr als 5 Sekunden zuerst an den Anfang der Folge.
* **Spielt weiter** über die Folgen des Eintrags: am Ende einer Folge startet die nächste; nach der letzten ist Schluss (Runde 8 Nr. 22: bei Alben so; über eine **Playlist** weiterspielen kommt mit Stufe C, Abschnitt 13). Alben und Hörbücher mit Kapiteln (Ordner-Folgen) laufen ohne Unterbrechung der Zeitleiste über die Tracks (11.4).
* **Kapitel (Rev. 4):** Hat die Folge Kapitel (11.4.8), steht in der Vollansicht unter dem Titel eine Zeile „**Kapitel 8: Das Echo (8 von 12)**“ und neben den Geschwindigkeits-Knöpfen der Knopf **„Kapitel“**. Er öffnet ein Blatt mit der Liste (Titel, „ab 2:49 · 0:19“, schon gehörte mit Häkchen, das aktuelle markiert und beim Öffnen sichtbar). **Tipp = dorthin springen und weiterspielen.** Die **Zeitleiste über das ganze Buch bleibt** (Entscheidung Tobias, Nr. 20: beides). Auf dem Sperrbildschirm kein Kapitel-Sprung (nur vorige/nächste Folge).
* **Hörkopie (Rev. 4):** Für Formate, die nicht jeder Browser spielt, spielt der Player automatisch die Hörkopie (11.4.7); die Seite merkt davon nichts, außer dem Satz „Die Hörprobe wird gerade vorbereitet …“, wenn sie noch fehlt. Springen geht wie beim Original (Range-Anfragen auf eine fertige Datei).
* **Weiterhören:** Die Stelle wird **je Folge und je HA-Benutzer in Home Assistant** gespeichert (gleich auf Handy und Computer; 11.4). Sichtbar als Fortschrittsbalken in Liste und Folgenzeilen, als Reihe „Weiterhören“ in Bibliothek und Start, als Knopf „Weiterhören“ und als Sortierung „Zuletzt angehört“. „Fertig gehört“ heißt: bis auf 2 Sekunden ans Ende.
* **Sperrbildschirm:** `navigator.mediaSession` setzt Titel, Eintrag und Art und verdrahtet Play, Pause, 30 s zurück/vor, vorige/nächste Folge und Springen. Vorschlag, ohne Gewähr auf allen Geräten (zu prüfen in A15b).
* **Fehlerfälle** (Texte in 6.1): Format spielt dieser Browser nicht; Datei nicht mehr da; Anmeldung abgelaufen (die Seite signiert neu und macht an der Stelle weiter); keine Verbindung.
* **Prototyp:** Der Player spielt **kurze, im Script erzeugte Töne** (jede Folge eine eigene sanfte Tonfolge, 1 bis 5 Minuten), damit man Springen, Geschwindigkeit, Folgenwechsel und Weiterhören hört und ausprobiert; die Hörstelle liegt dort im Browser (`localStorage`), nicht in HA.

## 6. Zustände

| Zustand | Was die Seite zeigt |
|---|---|
| **Lädt** | Graue, leicht pulsierende Platzhalter-Karten (statt „Lade …“). Mit „reduzierte Bewegung“ ohne Pulsieren. Nach 10 s ohne Antwort wird es der Fehlerzustand. |
| **Leer** (noch nichts eingerichtet) | Start: statt Boxen „Noch keine Box eingerichtet. Bitte Tobias Bescheid sagen.“; Bibliothek: „Noch nichts da. Tippe auf „Hinzufügen“.“; Tobies siehe 5.7. Es gibt immer einen Knopf als nächsten Schritt. |
| **Fehler beim Laden** | Rote Karte: „**Die Seite konnte nichts laden.** Home Assistant antwortet gerade nicht. Warte kurz und versuche es noch einmal. Wenn es so bleibt, sag Tobias Bescheid.“ Knopf „Noch einmal versuchen“. |
| **Verbindung weg** (Websocket zu) | Rotes Band oben: „**Keine Verbindung zu Home Assistant.** Die Ansicht wird von selbst aktuell, sobald die Verbindung wieder da ist.“ Knopf „Jetzt neu laden“. Boxen grau. Schreibende Knöpfe grau, bis die Verbindung wieder da ist. |
| **Box offline** | Statuskarte grau (5.1.1). Knopf „Auf Stern“ grau mit Erklärung. |
| **Liste gesperrt** (`konfig.zustand` ≠ `ok`) | Nicht-Admin, Band oben: „Änderungen sind gerade gesperrt. Bitte Tobias Bescheid sagen.“ Alle Knöpfe, die die Liste ändern, grau. Admin: die Warnleiste von heute, in einfacheren Worten (Tobias entscheidet, nicht Verena). |
| **Alte Seite** (`hello.v` oder `unknown_command`) | „Die Seite ist veraltet. Bitte lade sie neu (am Handy: Seite nach unten ziehen oder Browser neu öffnen).“ (heute „Strg+F5“). |

Änderungen gegenüber Rev. 1: „Hörspiele“ heißt „Bibliothek“; die Zeile „Liste gesperrt“ nennt „Änderungen sind gerade gesperrt. Bitte Tobias Bescheid sagen.“ nur für Nicht-Administratoren (U22b).

### 6.1 Fehlertexte: immer mit nächster Handlung (U20)

Die Seite übersetzt `error.code` (Vertrag W, Abschnitt 7) und bei Upload `fehler.code`. **`texte.js` wird gegen die Vertragstabelle vollständig abgeleitet** (der bestehende Test verlangt einen Text je Code);
die Alltagscodes stehen hier, der Rest bekommt den Standardtext, mit dem Code klein dahinter **nur für Administratoren**.

| Code | Text |
|---|---|
| `medien_nicht_erreichbar` | „Das NAS antwortet gerade nicht. Versuche es in ein paar Minuten noch einmal. Wenn es so bleibt, sag Tobias Bescheid.“ |
| `medien_schreibfehler` | „Das Speichern auf dem NAS hat nicht geklappt. Versuche es gleich noch einmal. Wenn es so bleibt, sag Tobias Bescheid.“ |
| `kein_speicher` | „Auf dem NAS ist kein Platz mehr. Bitte Tobias Bescheid sagen.“ |
| `mqtt_nicht_verbunden` | „Die Verbindung zu den Boxen ist gerade gestört. Es wurde nichts gesendet. Versuche es gleich noch einmal.“ |
| `box_offline` | „Stern ist aus oder nicht im WLAN. Schalte sie ein und versuche es noch einmal.“ |
| `konfig_nicht_bereit` | „Änderungen sind gerade gesperrt. Bitte Tobias Bescheid sagen.“ |
| `unauthorized` | „Dafür fehlt dir die Berechtigung. Frag Tobias.“ |
| `zuordnung_geaendert`, `stand_veraltet` | „Jemand hat gerade etwas anderes geändert. Die Ansicht ist neu geladen. Bitte versuche es noch einmal.“ |
| `lernmodus_laeuft` | „Auf der Mond läuft schon das Anlernen für ein anderes Hörspiel. Beende es zuerst.“ (Knopf „Dort beenden“ = `lernmodus/abbrechen`) |
| `format_nicht_erlaubt` | „Dieses Dateiformat spielt die Box nicht. Erlaubt sind MP3, M4A, M4B, AAC, FLAC, OGG, Opus und WAV.“ |
| `datei_zu_gross` | „Die Datei ist zu groß (mehr als 500 MB). Am Computer in den Eingang-Ordner kopieren.“ |
| `zu_viele_uploads` | (kein Fehler: die Seite wartet und sendet danach weiter) |
| `name_ungueltig` | „Dieser Name geht nicht. Bitte kürzer oder anders schreiben.“ |
| `einstellung_ungueltig` | siehe 4.6 |
| `unknown_error`, unbekannter Code | „Das hat nicht geklappt. Versuche es noch einmal. Wenn es wieder nicht geht, sag Tobias Bescheid.“ (Code klein dahinter, nur für Admins) |
| Verbindung beim Upload abgebrochen | „Die Verbindung ist abgebrochen. Ob die Datei angekommen ist, siehst du in ein paar Minuten unter „Gerade eben“. Wenn nicht, wähle sie noch einmal.“ |
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
| `hoerkopie_wartet` (neu, V-9) | „Die Hörprobe wird gerade vorbereitet. Versuche es in ein paar Minuten noch einmal. Auf der Box spielt es schon.“ (die Seite versucht es nach 30 Sekunden von selbst noch einmal, wenn der Player offen ist) |
| `hoerkopie_fehler` (neu, V-9; steht im Folge-Objekt, nicht als Antwort) | „Für diese Datei gibt es keine Hörprobe. Auf der Box spielt sie trotzdem.“ (Administratoren sehen dahinter in „Technik“ den Grund und „Hörkopien neu erzeugen“) |
| `zu_viele_streams` (neu, V-6) | „Es läuft schon auf mehreren Geräten etwas. Beende dort das Hören und versuche es noch einmal.“ |
| `wunsch_ungueltig` (neu, V-7) | „Das passt so nicht zusammen. Wähle noch einmal, was du hochlädst.“ |
| `neu_einsortieren_nicht_moeglich` (neu, V-7) | „Das lässt sich nicht mehr anders einsortieren, weil schon etwas daran geändert wurde. Lege es in den Papierkorb und lade es noch einmal hoch.“ |
| Audio-Anfrage abgelaufen (401) | (kein Fehler: die Seite signiert neu und macht an der Stelle weiter; klappt es nicht: „Die Verbindung ist abgebrochen. Tippe auf Abspielen, dann geht es weiter.“) |
| `konfig_zu_gross`, `export_*`, `anfrage_id_konflikt`, `box_unbekannt`, `datei_existiert`, `reihenfolge_ungueltig`, `serie_existiert`, `ueberraschung_existiert` | Standardtext (nur Administratoren sehen den Code) |

Fehler stehen als Karte am Ort der Handlung (nicht nur oben), bleiben bis „OK“ und werden Screenreadern über `role="alert"` vorgelesen. Erfolg: kurze Meldung unten (4,5 s, `role="status"`).

## 7. Die Kernaufgaben als Abläufe

Gezählt wie in `ist.md`: Taps **auf der Seite**, ohne Texteingabe und ohne Auflegen des Tobies. Ehrlich dazu (U9a): „plus Öffnen“ der Seite, das sind in der HA-App zwei Taps (Seitenleiste, „Tobi Box“). Ziel höchstens drei.

### 7.1 (a) Neuer Tobie erscheint → Kachel → fertig, Name: **1 Tap**

1. *(Körperlich)* Verena legt einen unbekannten Tobie auf Mond. Die Box meldet ihn (`neue_tobies`). Oben auf der Startseite erscheint die Karte „**Neuer Tobie auf Mond.** Gerade aufgelegt, vor 2 Minuten. **Bist du nicht sicher, welcher es ist? Lege den Tobie noch einmal auf.**
   Was soll er spielen?“ (der Satz steht **über** den Kacheln, U9b). Bei mehreren Karten ist nur die **oberste** bedienbar („Der zuletzt aufgelegte steht oben.“, U9b/c). Der Reiter „Start“ hat einen Punkt mit Zahl.
   Eine HA-Automation „Neuer Tobie → Mitteilung aufs Handy, Tippen öffnet `/tobibox`“ liegt als **Vorlage** in `homeassistant/README.md` (keine neue Funktion, U9).
2. Kacheln: die **fünf zuletzt hinzugefügten** Einträge und **„Gute Nacht“** (Timer, dann still). Darunter „**Anderes suchen …**“ öffnet die Zielwahl (5.4): Suche, Art, Ganzes oder Einzelnes (Lied, Folge). Für etwas Neues also **1 Tap**, für etwas Altes: „Anderes suchen“, tippen der ersten Buchstaben, Treffer antippen (3 Taps plus Tippen).
3. **Tap 1:** auf die Kachel (`zuordnung/set`, Ziel `serie`, `folge` oder `aktion`). Die Karte wird grün: „**Fertig!** Dieser Tobie spielt jetzt „Pirat Pippo“.“ und **fragt gleich nach dem Namen** (U4):
   „**Wie soll er heißen?** Damit du ihn später wiederfindest. Du kannst das auch überspringen.“ Textfeld „Name, zum Beispiel Farbe oder Tier“, Knopf „Name speichern“. Dazu „**Rückgängig**“ (`zuordnung/remove` mit `erwartet_ziel`) und „**Ohne Namen weiter**“ (nach dem Speichern „OK“).
   **Rückgängig bleibt, bis die Karte mit „OK“ geschlossen wird** (nicht nur 8 Sekunden, U9c). Das Textfeld bekommt auf Touch-Geräten keinen Autofokus (die Tastatur würde die Karte verdecken); am Computer schon.
4. Unter den Kacheln, abgesetzt: „Das war ein Versehen, nicht merken“ (`neue_tobies/verwerfen`, Rückfrage wie Rev. 1).
5. Fehler: Liste gesperrt → Kacheln grau, Band (Abschnitt 6). Zuordnung existiert schon (zwei Fenster): Seite lädt neu, „Dieser Tobie wurde gerade woanders zugeordnet.“

Heute: 5 Taps plus Kennung lesen.

### 7.2 (b) Eintrag, Lied oder Folge wählen → „Tobie anlernen“ → auflegen: **3 Taps** (Rev. 2: 2; die ruhigere Serienseite kostet einen Tap)

1. **Tap 1:** auf die Zeile in der Bibliothek (öffnet die Serienseite). Bei einem Lied/einer Folge im **Suchtreffer** ist es gleich der Knopf „Tobie“ (5.4), also ein Tap weniger.
2. **Tap 2:** „**Tobie zuordnen**“ auf der Serienseite (bei einer Folge: „⋯“ und „Tobie für diese Folge“, ein Tap mehr). Es öffnet das Blatt „Tobie für dieses Hörspiel“.
3. **Tap 3:** „Auf Mond“ im Blatt (`lernmodus/start` mit Ziel `serie` oder `folge`; der Knopf je Box ersetzt die Boxauswahl).
4. Die Seite wechselt zu „Tobie anlernen“ (`#anlernen`): Ring-Symbol (pulsiert, nicht bei „reduzierte Bewegung“), Überschrift „**Jetzt Tobie auf Mond legen**“,
   „Dieser Tobie soll „Lange Serie“ spielen. Ich warte noch 118 Sekunden.“ (Zähler aus `frist_bis`, wird nicht vorgelesen), Knopf „Abbrechen“ (= `lernmodus/abbrechen`).
5. *(Körperlich)* Tobie auflegen. Ereignis `lernmodus`/`zugeordnet`: grünes Häkchen, „**Erkannt!** Dieser Tobie spielt jetzt „Lange Serie“.“,
   **Name-Abfrage wie in 7.1** (Textfeld, überspringbar), Knöpfe „Noch einen Tobie anlernen“, „Fertig“ (zurück zum Eintrag). Der Name geht schon mit `lernmodus/start` (`name`), wenn Verena ihn vorher kennt; sonst setzt ihn die Seite danach mit `zuordnung/set`. Erscheint der neue Tobie auch unter „Tobies“: ja, ohne Namen.
6. Fälle:
   * Tobie hat schon ein Ziel (`rueckfrage`): Blatt „**Dieser Tobie spielt schon etwas.** Er spielt jetzt „Test-Serie“. Soll er stattdessen „Lange Serie“ spielen? Du hast dafür noch 10 Sekunden.“
     Knöpfe „Nein, so lassen“ (Vorgabe, Fokus), „Ja, ändern“ (= `lernmodus/antwort`). Zeit abgelaufen: „Das hat zu lange gedauert. Der Tobie spielt wie vorher.“ (+1 Tap).
   * Abgelaufen (`abgelaufen`): „**Kein Tobie erkannt.** Die Zeit ist abgelaufen. Lege den Tobie nach dem Start gleich auf die Box.“ „Noch einmal versuchen“ / „Zurück“.
   * Box lehnt ab (`box_lehnt_ab`, `zeit_unsicher`): „Mond kann gerade nicht lernen, weil sie die Uhrzeit nicht sicher kennt. Versuche es in ein paar Minuten noch einmal.“
   * Box aus (`box_offline`): Knopf schon vorher grau (4.3).
   * Läuft schon ein Lernvorgang: `lernmodus_laeuft`, Text in 5.1. Die Seite zeigt bei erneutem Öffnen einen offenen Vorgang weiter an (Abo `lernmodus`).

Heute: 5 bis 9 Taps (`ist.md`).

Heute: 5 bis 9 Taps.

### 7.3 (c) Hinzufügen: **4 Taps** (Rev. 4: eine Wahl mehr, dafür verständlich), Wartezeit ohne Tippen

1. **Tap 1:** „Hinzufügen“ (Start oder Bibliothek). **Tap 2:** „Dateien wählen“ (System-Auswahl) oder am Computer „Ordner vom Computer wählen“ bzw. Hineinziehen.
2. **Tap 3: „Was lädst du hoch?“** Das Blatt (5.6) fragt mit fünf Karten. Es ersetzt das alte Blatt „In welches soll es?“. Je nach Karte:

   | Karte | Was die Vorschau noch fragt | Satz in der Vorschau (Beispiele aus dem Prototyp) |
   |---|---|---|
   | **a) Neues Hörspiel, Hörbuch oder Album** | **Name** (aus den Angaben der ersten Datei vorgeschlagen, sonst aus dem Dateinamen) und **Art**: Hörspiel · Hörbuch · Album · Geschichten (aus den Angaben vorgeschlagen, mit Hinweis „Vorgeschlagen aus den Angaben in den Dateien.“ oder „Geraten, …“) | „3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.“ · „4 Dateien → neues Album „Sommerlieder“, Lied 1–4.“ · „8 Dateien → neues Hörspiel „Die Wolkenreise“, Folge 1–8.“ · „1 Datei → neues Hörbuch „…“ (ein Kapitel).“ |
   | **b) Folgen zu einem vorhandenen hinzufügen** | **Wohin?** Sofort die Auswahl **mit Suche, Covern und Art-Knöpfen** (wie in 5.4, aber **nur** Hörspiele, Bücher, Alben; **ohne** Einzeltitel und ohne „Gute Nacht“); danach steht der Eintrag mit Cover in der Vorschau, „Ändern“ wählt neu | „3 Dateien → 3 neue Folgen in „Lange Serie“ (Folge 13–15).“ · „2 Dateien → 2 neue Folgen in „Lange Serie“ (Folge 21–22).“ (hat die Serie 20 Folgen) · bei Hörbuch „… neue Teile …“, bei Album „… neue Lieder …“ |
   | **c) Einzelne Folge oder einzelnes Lied** | **Art**: Lied · Geschichte · Folge · Hörbuch (Vorgabe Lied) und **ein Name je Datei** (die ersten drei als Felder, der Rest aus den Angaben) | „1 Datei → 1 einzelnes Lied: „Der Mond und der Fuchs“.“ · „5 Dateien → 5 einzelne Lieder.“ (bis 3 Dateien mit Namen) |
   | **d) Neue Playlist** | – (Stufe C: Name der Playlist, danach wie c), die Dateien werden Einzeltitel und gehören der Playlist, Abschnitt 13) | im Prototyp nur die Meldung „Playlists gibt es noch nicht. Das kommt später (Stufe C).“ |
   | **e) Weiß nicht – sortier du** | nichts; ein Absatz erklärt: „Ich lese die Angaben in den Dateien (Album, Interpret, Titel). Dateien, die zum selben Album gehören, bleiben zusammen. Passt etwas zu einem Hörspiel, das schon da ist, kommt es dort dazu. Wenn ich unsicher bin, steht danach „Bitte ansehen“ da, und du kannst es ändern.“ | „1 Datei → ich sortiere nach den Angaben in den Dateien ein. Meine Vermutung: ein einzelnes Lied „Der Mond und der Fuchs“.“ · „3 Dateien → ich sortiere … Meine Vermutung: neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.“ |

   Der Satz ändert sich **sofort** beim Tippen im Namensfeld und beim Wechsel der Art (Bereich mit `role="status"`, `aria-live="polite"`). Unter dem Satz stehen bei a) und b) bis zu vier Zeilen „Kapitel 1 · Der Hafen“ (bzw. „Folge 13 · …“, „Lied 1 · …“) als Vorschau, was aus den Dateien wird; „… und 4 weitere“.
   **Die Nummern sind eine Vorschau** („Folge 13–15“ = nach den vorhandenen 12); Nummern aus den Angaben in den Dateien haben beim Einsortieren Vorrang (Vertrag W 11.4 bis 11.6).
3. **Vorschau und Start (Tap 4):** Knöpfe „Abbrechen“, „**Ändern**“ (zurück zu den Karten; die Eingaben bleiben erhalten) und „**Hochladen**“ (primär). „Hochladen“ prüft: bei b) fehlt die Wahl → Meldung „Bitte zuerst wählen, wohin es soll.“; bei a) fehlt der Name → „Bitte einen Namen eingeben.“. Wer aus einem Eintrag heraus hochlädt („Dateien in diesen Eintrag“), springt direkt zur Vorschau von b). Die **Hörbuch-Frage** („Gehören die Dateien zu einem Hörbuch?“, U12b) entfällt: die Art in a) beantwortet sie.
   **Was die Wahl im Backend bewirkt:** Die Seite sendet sie als **Wunsch** mit dem Upload (`ziel`, `art`, `name`, `serie_id`, `gruppe`; V-7). Der Wunsch **gilt vor den Tags**: ein „Hörbuch“ wird **eine** Folge mit den Dateien als Kapitel, ein „Album“ oder „Hörspiel“ je Datei **eine** Folge, auch wenn alle dasselbe Album nennen (bisher machte das Einsortieren aus gleichem Album immer **eine** Folge mit Tracks, Vertrag W 11.3). Der Wunsch „Weiß nicht“ (`auto`) ändert nichts: Es gilt das heutige Einsortieren (Vertrag W 11.3 bis 11.5), dazu der Art-Vorschlag (V-2).
4. Der Upload startet sofort. **Ein** Eintrag für alle Dateien dieses Hochladens (bei c) mit mehreren Dateien ebenso) unter „**Zuletzt hinzugefügt**“, mit Dateinamen („3 Dateien: 01 Der Hafen.mp3, 02 Die Karte.mp3 …“):

   | Schritt | Anzeige |
   |---|---|
   | 1 | **„Wird hochgeladen … 37 %“** mit Balken (`role="progressbar"`), dreiteilige Leiste (Hochladen · Einsortieren · Fertig) |
   | 2 | **„Wird einsortiert …“** |
   | 3a | **fertig:** grüne Marke, was daraus geworden ist („Hörbuch „Kapitän Knopf“ · 3 Kapitel“, „„Lange Serie“ · Folge 13–15“, „„Der Mond und der Fuchs“ · einzelnes Lied“) und der Knopf „Öffnen“ (44 px); nur bei „Weiß nicht“ zusätzlich „Art: Musik (aus den Tags vorgeschlagen). Stimmt nicht? Im Eintrag „Art ändern“.“ |
   | 3b | **bitte kurz ansehen:** gelbe Karte mit dem Grund und „**Daraus ist geworden:** …“, Knöpfen „Ansehen“, „**Das ist richtig**“ (`einsortierung/bestaetigen`) und „**Anders einsortieren …**“ (öffnet dieselbe Wahl wie 5.6, siehe Punkt 10 unten; auf der Serienseite heißt die Karte weiter „Das stimmt nicht“ und bietet als **erste** Möglichkeit „Anders einsortieren …“, dann „Anderem zuordnen …“ und „In den Papierkorb …“, U11) |
   | 3c | **geht nicht:** rote Karte „**Geht leider nicht.** <Grund und nächste Handlung>“ |

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
   `ffprobe_fehlt`: „Das Prüfprogramm fehlt. Bitte Tobias Bescheid sagen.“ · `verschieben_fehlgeschlagen`: „Das Ablegen hat nicht geklappt. Versuche es später noch einmal, sonst frag Tobias.“ ·
   `doppelt`: „Das gab es schon und wurde nicht noch einmal angelegt.“ Die Zeile erklärt, nicht den Code. „Entfernen“ eines blockierten Eintrags ist Admin-Sache („Technik“).

7. **Zwei Uploads gleichzeitig:** weitere Dateien warten („wartet“) und gehen nacheinander; kein 429 sichtbar. **Abbrechen** solange hochgeladen wird (`AbortController`).
8. **Wenn das Handy den Bildschirm sperrt:** Safari und Chrome frieren die Seite ein. Darum der Hinweis in 5.6 und beim Zurückkehren: Zeilen, die bei „wird hochgeladen“ stehen geblieben sind, werden „Unterbrochen. Wähle die Datei noch einmal.“
9. **Proxy-Grenze (U12e):** HTTP 413 von einem vorgeschalteten Proxy wird als `datei_zu_gross` gezeigt; „Technik“ nennt die tatsächliche Grenze.
10. **NAS-Weg (Rev. 4, dieselbe Wahl):** Dateien im Eingang-Ordner erscheinen ohne Hochladeschritt direkt bei „Wird einsortiert …“ und werden wie bisher **automatisch** einsortiert („Weiß nicht – sortier du“). Sie stehen unter „Zuletzt hinzugefügt“ mit „vom NAS“, und der Satz „Daraus ist geworden: …“ sagt, was die Automatik gemacht hat. Sieht es falsch aus, hat die Karte „bitte ansehen“ den Knopf **„Anders einsortieren …“**: Er öffnet **dasselbe Blatt**, nur mit dem Titel „**Was ist das?**“ (die Dateien liegen ja schon da: „6 Dateien im Eingang vom NAS. Was ist das?“), dieselben fünf Karten, dieselbe Vorschau in Sätzen; der Start-Knopf heißt dort **„Neu einsortieren“**. Das Backend holt die Folgen dieses Eintrags aus den Medien in den Eingang zurück und sortiert sie mit dem Wunsch neu ein (`einsortierung/neu`, V-7). Das geht nur, solange **nichts** an ihnen geändert wurde (Name, Verschieben, Tobie, angehört); sonst `neu_einsortieren_nicht_moeglich` mit dem Rat „in den Papierkorb und noch einmal hochladen“. **Machbarkeit zu prüfen in A3d:** Vertrag W kennt heute keinen Weg zurück von den Medien in den Eingang; fällt er zu teuer aus, bleibt für NAS-Einträge nur „In den Papierkorb …“ und neu hochladen (Frage 25, Variante 2: erst fragen, dann einsortieren).
11. **„Jetzt prüfen“** (`eingang/sortieren`) wird für Nicht-Administratoren **ohne `sofort`** gesendet (U10) und sagt: „Dateien werden erst nach 2 Minuten Ruhe einsortiert.“ `sofort` bleibt in „Technik“.

Heute: 3 bis 5 Taps plus Suchen im Reiter „Eingang“. Rev. 3: 3 Taps. Rev. 4: **4** Taps, dafür sagt jeder Schritt, was passiert.

### 7.4 (d) Abends: **2 bis 3 Taps**

* Gute Nacht ändern: „Abends“ (1), Schnellwahl-Knopf, z. B. „60 Min.“ (2), „Speichern“ (3). Von 30 auf 240: Auswahlfeld statt 42 Taps (U16a).
* Leise-Zeit hinzufügen mit Vorgabe (So–Do, 19:30–06:30, Still): „Abends“ (1), „+ Zeit hinzufügen“ (2), „Speichern“ (3). Andere Tage +1 (Schnellwahl), andere Zeiten +2 je Feld.
* Bestehende Zeit ändern: „Abends“ (1), „Ändern“ (2), Wert ändern, „Speichern“ (3+).
* Gute-Nacht-Tobie: neuer Tobie über „Neuer Tobie“ mit Kachel „Gute Nacht“ **oder** ein belegter Tobie über „Tobies → Etwas anderes spielen → Gute Nacht“ (U16c; Lernmodus bleibt für Folgen und Einträge, Aktionen gehen nicht über ihn, `mqtt-v1.md` 3.8).

## 8. Zusammenfassung der Taps

| Aufgabe | Heute | Neu |
|---|---|---|
| (a) Unbekannten Tobie zuordnen (neuer Eintrag) | 5 bis 8 | **1** auf der Seite (+ Öffnen); Name +1 (optional) |
| (a) Unbekannten Tobie einem **alten** Eintrag oder Lied geben | 5 bis 8 | **3** (Anderes suchen, Treffer) plus Tippen |
| Tobie umstellen | 6 bis 9 | **3** (Tobies, Zeile, Zielwahl; „Rückgängig“ statt Rückfrage) |
| (b) Eintrag → Tobie anlernen | 5 bis 9 | **3** (Zeile, Tobie zuordnen, Auf Mond; +1 bei „schon belegt“) |
| Lied/Folge → Tobie anlernen | nur Technik | **3** über die Suche (Lupe, Tobie, Auf Mond), **4** über die Serienseite (Zeile, ⋯, Tobie für diese Folge, Auf Mond) |
| (c) Hinzufügen | 3 bis 5 + Suchen | **4** (Hinzufügen, Dateien, Karte, Hochladen; Rev. 3: 3, aber unverständlich). Bei b) +1 für die Wahl des Eintrags |
| Einzelnes Lied hochladen | nur über „Einzelfolgen“ | **4** (Hinzufügen, Dateien, „Einzelne Folge oder einzelnes Lied“, Hochladen) |
| (c2) „bitte ansehen“ bestätigen | 3 bis 7 | **1** („Das ist richtig“) |
| Fehl-Upload korrigieren | Sackgasse | **3** („Das stimmt nicht“, Papierkorb, Bestätigen) oder **4** („Anders einsortieren“, Karte, Neu einsortieren) |
| (d) Gute Nacht ändern | 3 + Tippen | **3** |
| Cover ersetzen | nur NAS von Hand | **4** (Cover ändern, Foto, Zuschneiden, Speichern) |
| Etwas in der Bibliothek finden | – | **1 bis 2** (Lupe, Treffer; plus Tippen) |
| Hineinhören (Reinhören) | – | **2** (Zeile, „Reinhören“) |
| Weiterhören | – | **1** (Abspielknopf in der Reihe „Weiterhören“) |
| In ein Kapitel springen | – | **2** (Zeile „Kapitel“ auf der Serienseite: ein Tap; im Player „Kapitel“, Zeile) |

## 9. Wohin jede heutige Funktion wandert

Alles bleibt, wie es heute funktioniert; nur Ort und Text ändern sich. **Die ganze heutige Technik-Seite wird eingebettet** (5.9), also bleibt jede Zeile der Tabelle aus Rev. 1 für Administratoren erreichbar. Die Alltagsfassung:

| Heute (Fundort in `ist.md`) | Neu | Wer |
|---|---|---|
| Reiter „Serien“ | Reiter „Bibliothek“ (Arten, Liste, Suchansicht, Blatt „Sortieren und Filter“, Reihen „Weiterhören“ und „Neu“) | alle |
| „Hochladen“-Karte | „Hinzufügen“ (7.3): Blatt „Was lädst du hoch?“ mit fünf Karten, Vorschau in Sätzen; Vorgabe-Serie über Karte b) oder „Dateien in diesen Eintrag“; „Liste leeren“ wird „Erledigte ausblenden (auf diesem Gerät)“ | alle |
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
| „Neue Tobies“, „Verwerfen“ | Karte „Neuer Tobie“, „Das war ein Versehen, nicht merken“ | alle |
| „Zuordnen“ (Serie / **einzelne Folge** / Aktion) | Kachel (7.1), „Tobie zuordnen“ auf der Serienseite, „Tobie für diese Folge“ im Menü der Folge, Knopf „Tobie“ im Suchtreffer (5.4), Kachel „Gute Nacht“; Aktion „Status“ nur Technik → Tobies im Detail | alle / Admin |
| Lernmodus | Serienseite „Tobie zuordnen“ / Folge-Menü / Suchtreffer (7.2) | alle |
| „Kennung von Hand eingeben“, Kennung, Fehlmarken | Technik → Tobies im Detail | Admin |
| Zugeordnete Tobies: Name, Ziel ändern, Lösen | Reiter „Tobies“ (5.7) | alle |
| Reiter „Boxen“, „Sync jetzt“, Meldungen | Alltag: Status-Satz (5.1.1). Voll: Technik → Boxen im Detail, Meldungen | alle / Admin |
| Liste, Revision, Export, „Liste neu ausrollen“ | Technik → Liste, Sicherung, Export (plus „Frühere Stände ansehen“) | Admin |
| Warnleisten | Admin oben auf jeder Seite; Nicht-Admin: „Änderungen sind gerade gesperrt.“ | Admin / alle |
| Reiter „Korb“ | Technik → Papierkorb (Wiederherstellen, **Leeren**) | Admin |
| Einstellungen: Leise-Zeiten | Reiter „Abends“ (Zeilen, Blatt); Zeitzone in Technik | alle / Admin |
| Einstellungen: Gute Nacht (Timer) | Reiter „Abends“ (Schnellwahl); „Ausblenden“ in Technik → Weitere Einstellungen | alle / Admin |
| Einstellungen: Lesezeichen-Tage, Upload-Grenze | Technik → Weitere Einstellungen; Grenze in der Integration | Admin |
| HA-Entitäten, HA-Aktionen | unverändert in HA; Aktionen nur für Administratoren (U1, behoben in Commit d41e319) | – |

## 10. Rechte: wer darf was

### 10.1 Was nötig ist (U1, U7, U19)

1. **HA-Aktionen** (`services.py`) sind seit Commit d41e319 **nur für Administratoren** (`async_register_admin_service`, U1). Ein Test ruft jede Aktion als Nicht-Administrator auf und erwartet `Unauthorized`. Der Prüfabschnitt „gegen die HA-API“ im Vertrag W nennt das.
2. **Backend zuerst, Panel zuletzt (U7):** Die Rechte je Befehl (10.2) und der Schutz (10.3) kommen im ersten Arbeitspaket (A1), **ohne** das Panel zu öffnen: `require_admin` bleibt `True`, bis Tobias die Abnahme gemacht hat (A16). Erst dann der eigene kleine Schritt A17
   „Seite für alle öffnen“ (`require_admin=False`), mit Test in `test_init.py` (heute prüft er `require_admin is True`). Vorher wird die Tabelle 10.2 mit einem Testbenutzer geprüft.
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
| **lesen** (alle) | 1 `hello`, 2 `subscribe`, 3 `serien/list` (erweitert), 4 `serie/get`, 10 `papierkorb/list`, 13 `neue_tobies/list`, 15 `zuordnung/list`, 21 `boxen/list` (ohne `ereignisse`), 29 `eingang/list`, 34 `konfig/get`, 35 `einstellungen/get`, neu `folgen/list`, HTTP-Cover (GET), **neu in Rev. 3:** HTTP-Audio (GET, angemeldet oder signierter Pfad), `hoerstelle/get`, `hoerstelle/liste` (nur die eigene Hörstelle) |
| **alltag** (alle angemeldeten Benutzer) | 16 `zuordnung/set` (inkl. Name), 17 `zuordnung/remove`, 14 `neue_tobies/verwerfen`, 18 `lernmodus/start` (bisher Admin), 19 `lernmodus/antwort`, 20 `lernmodus/abbrechen`, 6 `serie/rename`, 25 `folge/rename`, 28 `einsortierung/bestaetigen`, 9 `medien/pruefen`, 30 `eingang/sortieren` (**ohne** `sofort`), 36 `einstellungen/set` (ohne Zeitzone und Lesezeichen-Tage), neu `serie/art_setzen`, HTTP-Upload, HTTP-Cover (POST, DELETE `eigen`), **neu in Rev. 3:** `hoerstelle/set` (nur die eigene), **neu in Rev. 4:** `einsortierung/neu` („Anders einsortieren“; Upload-Felder `ziel`, `art`, `name` ohne Recht über den normalen Upload hinaus), Stufe B: `reinhoer/loeschen` (nur die eigenen Daten),
  **8 `folge/delete`, 24 `serie/delete`, 26 `folge/verschieben`** (neu in Rev. 2: nur in den Papierkorb, nichts endgültig) |
| **admin** | 5 `serie/create`, 27 `serien/zusammenfuehren`, 11 `papierkorb/restore`, **12 `papierkorb/empty`**, **33 `eingang/entfernen`**, 22 `box/sync`, 23 `liste/neu_ausrollen`, 32 `konfig/aus_export`, **31 `konfig/export_lesen`** (U26), `boxen/list`-Feld `ereignisse`, `eingang/sortieren` mit `sofort`, `einstellungen/set` für Zeitzone und Lesezeichen-Tage, neu `cover/neu_suchen`, **neu in Rev. 4:** `hoerkopie/neu_erzeugen`, später Update |

**Reinhören (Rev. 3):** erlaubt für **alle HA-Benutzer** (Entscheidung Runde 7). Hörstellen sind **nur die eigenen** (die Kennung kommt aus der Verbindung, nie aus der Eingabe; auch Administratoren sehen keine fremden). Die Audio-Ansicht verlangt Anmeldung oder eine gültige Signatur.
Der HA-Befehl `auth/sign_path` (nicht unser Befehl) darf jeder angemeldete Benutzer aufrufen; die Signatur trägt seine Identität und gibt ihm **keine Rechte, die er nicht ohnehin hat**. Mengen: höchstens 4 gleichzeitige Streams und 30 `hoerstelle/set` je Minute und Benutzer (11.4).
**Reinhör-Daten (Stufe B, Rev. 4):** wie die Hörstelle **nur die eigenen**, auch für Administratoren; die Kennung kommt aus der Verbindung (12.5, Frage 23). `gehoert/zusammenfassung` mit `quelle="reinhoeren"` ist `lesen`, aber auf den Anfragenden beschränkt.

Begründung (ehrlich, U2): „alltag“ sind Dinge, die Verena selbst tun soll (Brainstorm, Runde 6). Endgültig zerstörbar sind nur `papierkorb/empty` und `eingang/entfernen`; sie bleiben Admin.
Die Zuordnungsliste ist dagegen **beschädigbar** (`remove` in einer Schleife), darum der Schutz in 10.3. „Lesen bleibt für alle“ ist bewusst, mit Ausnahme der beiden Befehle, die nur Tobias braucht (Liste im Detail, rohe Box-Meldungen).

### 10.3 Schutz gegen Fehlbedienung (U2, U3, U10, U17, Runde 6)

Gilt im Befehl für Nicht-Administratoren (Administratoren unverändert):

* **`zuordnung/remove` nur mit `erwartet_ziel`** (die Seite sendet es immer; schützt vor Doppeltipp und zweitem Fenster). Stimmt es nicht: `zuordnung_geaendert`. `zuordnung/set` mit `ueberschreiben=true` ebenso nur mit `erwartet_ziel`.
* **`zuordnung/set` nur für bekannte Kennungen:** die Kennung steht in `neue_tobies`, ist Ergebnis eines Lernmodus oder schon zugeordnet; sonst `kennung_ungueltig`. Die Seite hat keine Eingabe für Kennungen (die ist in „Technik“).
* **Mengen:** höchstens 30 Änderungen der Liste (`zuordnung/*`, `einstellungen/set`) je Minute und Benutzer, höchstens 20 Papierkorb-Aktionen je 10 Minuten, höchstens 4 GiB Upload je Stunde und Benutzer. Darüber `zu_viele_aenderungen`.
  Die Liste bleibt unter ihrer Grenze (`KONFIG_MAX_BYTES` 256 KiB), weil Kennungen nur bekannt oder gemeldet sein dürfen.
* **Frühere Stände der Liste:** die Integration behält die **letzten 10 Stände** als `export/config.<n>.json` (zusätzlich zum bisherigen Export). „Technik → Liste → Frühere Stände ansehen“ zeigt sie, „Aus Stand wiederherstellen“ geht wie `konfig/aus_export`. Das ist die Sicherung gegen Fehler mit Folgen für alle.
* **`eingang/sortieren`:** ohne `sofort` (U10). Die Ruhezeit schützt halb kopierte Dateien.
* **`einstellungen/set` (U17):** Das Backend **ignoriert** `leise_zeiten.zeitzone` im Objekt und nimmt den gespeicherten Wert (kein irreführendes `unauthorized`); nur `lesezeichen_tage` bleibt Admin (die Seite sendet es nie). Neues optionales Eingabefeld `erwartet_revision`:
  stimmt es nicht, Fehler `stand_veraltet`; die Seite lädt neu (so überschreiben sich zwei Eltern an zwei Geräten nicht still).
* **Papierkorb für Alltag:** Löschen mit Tobies verlangt wie bisher `tobies_bestaetigt` (Rückfrage mit Namen). „Rückgängig“ gibt es für das Löschen nicht (Wiederherstellen ist Admin); die Rückfrage sagt es: „Tobias kann es aus dem Papierkorb zurückholen.“ (Frage 7.)

## 11. Änderungen an Vertrag W, Datenmodell und Sync (Stufe A)

### 11.1 Wie der Vertrag geändert wird (U18)

Alles Folgende ist **additiv** (neue Felder, Befehle, Fähigkeiten, Codes, optionale Eingaben), **mit einer Ausnahme**: Die Lockerung der Rechte ändert das Verhalten bestehender Befehle (bisher `unauthorized`, jetzt Erfolg).
Im Vertragskopf steht dafür ein Eintrag „**Änderung 12.11. (HA-Oberfläche, Stufe A):** …“ in der Form der bisherigen Änderungen (Datum, kein „Version 1.2“-Zähler; `v` bleibt 1). **Abschnitt 2.1 („Wer darf was“) wird vollständig ersetzt** (nicht ergänzt), der Satz W-19 (Upload nur für Administratoren) entfällt,
der Prüfabschnitt „gegen die HA-API“ nennt `async_register_admin_service`. Neue Fähigkeiten nur dort, wo eine alte Seite im Zwischenspeicher sonst etwas Falsches täte: **`cover`**, **`bibliothek`** (neue Eingaben von `serien/list`, Befehl `folgen/list`) und, neu in Rev. 3, **`reinhoeren`** (Audio-Ansicht, `hoerstelle/*`, Felder `dauer_s` und `hoerstelle`; ohne sie zeigt die Seite keinen Reinhören-Knopf).
**Neu in Rev. 4 (alles additiv, Abschnitt V-7 bis V-9):** **`einsortier_wunsch`** (Upload-Felder `ziel`, `art`, `name`; Befehl `einsortierung/neu`; Feld `einzeln`; Filter `sammlung` und `einzeln`; ohne sie zeigt die Seite das alte, einfache Hochladen ohne Wahl und sendet keinen Wunsch), **`kapitel`** (Feld `kapitel`; ohne sie zeigt die Seite keine Kapitelliste) und **`hoerkopie`** (Audio-Ansicht liefert Kopien, Felder `hoerkopie`, Befehl `hoerkopie/neu_erzeugen`; ohne sie bleibt es bei der Prüfung mit `canPlayType`). In Stufe B kommt `gehoert_reinhoeren` dazu (12.5).
`box_anzeigenamen` und `rechte_stufen` entfallen (Feld da bzw. Seite und Backend liegen im selben Paket). Eine **alte Seite** im Zwischenspeicher kennt die Befehle nicht, schickt sie nicht und blendet nach `darf_schreiben` (= Administrator) aus: harmlos. Die neue Seite zeigt bei fehlender Fähigkeit „Die Seite ist veraltet. Bitte lade sie neu.“

### 11.2 Wunschliste im Einzelnen

**V-1 Cover (Fähigkeit `cover`)**

* *Serie-Kurzform* bekommt: `cover_stand` (string, 8 Zeichen `[0-9a-f]`, Fingerabdruck der angezeigten Datei) oder `null` (kein Cover), `cover_quelle` (`eigen`, `auto`, `null`).
  **Kein signiertes `cover_url`** (Review, Prüfpunkt 4): Die Adresse ist fest `/api/tobibox/cover/<serie_id>`; die Seite lädt das Bild mit `hass.fetchWithAuth` (Bearer), hält es als `blob:` und nimmt `cover_stand` als Schlüssel des Zwischenspeichers. Keine Signatur, kein Ablauf, kein Flackern.
  Ereignisse (`medien`, `snapshot`) tragen kein Cover, nur Antworten auf Befehle.
* **`GET /api/tobibox/cover/<serie_id>?groesse=klein|gross`:** `image/jpeg`, `klein` 192 px (≈ 15 KiB), `gross` 512 px (≤ 150 KiB), `ETag` = `cover_stand`, `Cache-Control: private, max-age=86400`. Recht: lesen. 404 `cover_nicht_gefunden`.
* **`POST /api/tobibox/cover/<serie_id>`:** Rumpf `image/jpeg`, höchstens 3 MiB, Quadrat bis auf 2 %, höchstens 2 048 px. Das Backend prüft die Kopfbytes, dekodiert, rechnet auf 512 und 192 px und speichert `cover-eigen.jpg` (nie das Original). Recht: **Alltag**. Fehler `cover_ungueltig`, `datei_zu_gross`, `serie_nicht_gefunden`.
* **`DELETE /api/tobibox/cover/<serie_id>?quelle=eigen`:** zurück zum automatischen Cover. Alltag.
* **Befehl `cover/neu_suchen`** (`serie_id` optional = alle): löscht `cover.jpg` und die Marke `cover_suche`, startet die Suche neu. **Admin.** Berührt nie `cover-eigen.jpg`.
* *Woher das automatische Bild kommt*, Marke, Zeitgrenzen, kein Dauer-Scan: 5.5. Fähigkeit `cover` wird nur gemeldet, wenn `ffmpeg` da ist (für das Lesen aus Tags; Foto-Upload braucht es nicht, das erledigt Pillow aus HA).

**V-2 Art, Suche, Filter, Sortieren, Blättern (Fähigkeit `bibliothek`)**

* *Serie-Kurzform* bekommt `art` (`hoerspiel`, `hoerbuch`, `musik`, `geschichte`), `art_quelle` (`tags`, `geraten`, `manuell`), `angelegt_am`, `tobies` (Anzahl Tobies, die auf den Eintrag oder eine Folge zeigen), `folgen_anzahl`. Fehlt `art` in einer alten `serie.json`, gilt `hoerspiel`.
* **`serien/list` bekommt optionale Eingaben:** `art`, `text` (2 bis 100 Zeichen; sucht im Namen des Eintrags und, mit `auch_folgen`, in Folgentiteln), `filter` (Liste aus `ohne_tobie`, `neu`, `pruefen`), `sortierung` (`name`, `neu`, neu in Rev. 3: `angehoert` = zuletzt angehört vom Anfragenden, nur mit Fähigkeit `reinhoeren`), `limit` (1 bis 200), `offset`. Ausgabe bekommt `gesamt` (nach Filter) und `weitere`.
  **Fehlt `limit`, gilt das bisherige Verhalten** (alle, höchstens 200, dazu `weitere`); so bleibt die alte Seite gültig. Das 64-KiB-Limit einer Nachricht (Vertrag, Größen) bleibt gewahrt, weil die neue Seite blättert.
* **Neuer Befehl `folgen/list`** (lesen): Eingaben `art`, `text`, `filter`, `sortierung` (`titel`, `neu`), `limit` (1 bis 100, Vorgabe 60), `offset`. Ausgabe: `folgen` = Liste aus `serie_id`, `serie_name`, `art`, `folge` (Name), `anzeige`, `nummer`, `kapitel`, `groesse_mb`, `tobies` (direkt auf die Folge), `serie_hat_tobie`; dazu `gesamt`, `weitere`.
* **`zuordnung/list`** bekommt `text` (Tobie-Name oder Ziel) und die Sortierung `neu` zuerst (V-5).
* **Neuer Befehl `serie/art_setzen`** (Alltag): `serie_id`, `art`; setzt `art_quelle="manuell"`.
* **Art beim Einsortieren aus Tags vorschlagen** (Vertrag Abschnitt 11): Genre-Tag mit „Hörbuch“/„Audiobook“/„Spoken“ oder Endung `.m4b` → `hoerbuch`; Genre „Hörspiel“/„Audio Drama“/„Radio Play“ → `hoerspiel`; Musikgenre (Pop, Kinderlieder, Children’s Music, Klassik, Schlaflied …) oder viele kurze Tracks (Mittel unter 8 Minuten) mit Album-Interpret → `musik`;
  Märchen/Geschichten/Einzeldatei unter 30 Minuten ohne Album → `geschichte`; sonst `hoerspiel` mit `art_quelle="geraten"` und Grund `art_geraten` in `pruefen_gruende` („Die Art ist geraten. Stimmt das?“). Ein von Hand gesetztes `art` (`manuell`) wird **nie** überschrieben.
* *Index:* Die Integration hält Eintrags- und Folgennamen (normalisiert) im Speicher; Aufbau beim Start, Aktualisierung bei `serien_geaendert`. Test: 600 Einträge, 2 000 Folgen, Suche unter 200 ms.

**V-6 Reinhören (Fähigkeit `reinhoeren`, neu in Rev. 3)**

* **HTTP:** `GET /api/tobibox/audio/{serie_id}/{folge_id}` (optional `?track=<n>`), Recht lesen, signierter Pfad oder Anmeldung, Range-fähig; Fehler 404 `folge_nicht_gefunden`, 429 `zu_viele_streams`, 503 `medien_nicht_erreichbar`. Einzelheiten 11.4.1 und 11.4.2. **Rev. 4:** Die Ansicht liefert bei Bedarf die Hörkopie (V-9).
* **Befehle (Recht alltag/lesen, Tabelle 10.2):** `hoerstelle/get`, `hoerstelle/set`, `hoerstelle/liste` (11.4.5). Neuer Code `zu_viele_streams`.
* **Felder (additiv):** *Serie-Kurzform* `dauer_s`, `hoerstelle` (`anteil`, `rest_s`, `zeit`, `folge`; nur des Anfragenden, nur wenn angefangen); *Folge-Objekt* von `serie/get`: `dauer_s`, `spuren_s` (bei Ordner-Folgen), `hoerstelle` (`position_s`, `fertig`); `hello.grenzen`: `audio_streams_je_benutzer` (4).
* **`serie.json`:** `folgen_info.<name>.dauer_s`, `spuren_s` (11.3, 11.4.4).

**V-7 Hochladen mit Wunsch und „Anders einsortieren“ (Fähigkeit `einsortier_wunsch`, neu in Rev. 4)**

* **Upload** (`POST /api/tobibox/upload`, Vertrag W 5.1) bekommt **optionale** Felder, wie die vorhandenen als Text im Multipart, **vor** dem Teil `datei`: `ziel` (`auto` Vorgabe, `neu`, `ergaenzen`, `einzeln`; in Stufe C auch `playlist`), `art` (`hoerspiel`, `hoerbuch`, `musik`, `geschichte`), `name` (1 bis 100 Zeichen, nach den Namensregeln aus Vertrag W Abschnitt 12 bereinigt). Die bestehenden Felder `upload_id`, `serie_id` und `gruppe` bleiben. Fehlt `ziel`, gilt `auto`: **genau das heutige Verhalten**. Eine alte Seite sendet nie etwas davon.
* **Wirkung** (Dateien mit gleicher `gruppe` gehören zusammen; der Wunsch gilt **vor** den Tags):

| `ziel` | Pflicht | Ergebnis |
|---|---|---|
| `auto` | – | wie heute (Vertrag W 11.3 bis 11.5), dazu der Art-Vorschlag (V-2) |
| `neu` | `gruppe`, `art`, `name` | **eine neue Serie** `name`; wird **nie** in eine vorhandene gleichen Namens zusammengeführt (gibt es den Namen, heißt sie „… (2)“, Kennzeichen `serie_name_doppelt`). Die **Gruppierung folgt der Art**, nicht den Tags: `hoerbuch` = **alle** Dateien eine Folge (Folgen-Ordner, die Tracks sind die Kapitel; bei einer Datei die Datei selbst, zum Beispiel eine M4B), `hoerspiel`, `musik`, `geschichte` = **jede Datei eine Folge** (auch wenn alle dasselbe Album nennen). Reihenfolge nach Vertrag W 11.6 und 11.7 (Nummer, Disc und Track, natürliche Sortierung). `art_quelle="manuell"` |
| `ergaenzen` | `serie_id` | jede Datei eine **neue Folge** der vorhandenen Serie (Einfügeregel Vertrag W 11.6), nie ein Folgen-Ordner. Die Serie darf kein Einzeltitel sein (`wunsch_ungueltig`) |
| `einzeln` | `art` (Vorgabe `musik`) | **jede Datei eine neue Serie mit genau einer Folge und `einzeln: true`** (V-8); `name` = Titel dieser einen Datei (sonst Tag `title`, sonst Dateiname). Mehrere Dateien: je Datei ein eigener Upload mit eigenem `name`, ohne gemeinsame `gruppe` |
| `playlist` (Stufe C) | … | erst in Stufe C (13): die Dateien werden Einzeltitel, die Playlist verweist darauf |

* **Fehler:** `wunsch_ungueltig` (400) bei fehlenden Pflichtfeldern oder unpassender Mischung; `serie_nicht_gefunden` wie bisher. Die Prüfung der Datei (Format, Kopierschutz, Probedekodierung) bleibt unverändert (Vertrag W 5.4).
* **Anzeige:** `eingang/list`-Einträge und das Ereignis `eingang` tragen zusätzlich `wunsch` (`ziel`, `art`), damit die Seite „Daraus ist geworden: …“ schreiben kann.
* **Neuer Befehl `einsortierung/neu`** (**Alltag**; „Anders einsortieren“ für Einträge aus dem NAS-Eingang und für Uploads, die schon einsortiert wurden): Eingabe `eintrag_id` (aus `eingang/list`), `ziel`, `art`, `name`, `serie_id` (wie oben). Das Backend holt die Folgen, die dieser Eintrag erzeugt hat, aus den Medien in den Eingang zurück und sortiert sie mit dem Wunsch neu ein. Nur möglich, solange an diesen Folgen **nichts** geändert wurde (nicht umbenannt, nicht verschoben, kein Tobie darauf, nicht angehört); sonst Fehler `neu_einsortieren_nicht_moeglich`. Die Serien, die der Eintrag neu angelegt hatte, verschwinden mit ihm (Papierkorb). **Machbarkeit zu prüfen in A3d:** Vertrag W kennt heute keinen Weg Medien → Eingang. Rückfall: nur Papierkorb und neu hochladen (Frage 25).

**V-8 Einzeltitel und Kapitel (Fähigkeiten `einsortier_wunsch`, `kapitel`; neu in Rev. 4)**

* *Serie-Kurzform* bekommt `einzeln` (bool; fehlt = `false`). `serien/list`: `filter` kennt zusätzlich `sammlung` (nur Einträge, die kein Einzeltitel sind) und `einzeln` (nur Einzeltitel). `folgen/list` trägt je Zeile `serie_einzeln`. `folgen_anzahl` ist bei einem Einzeltitel 1; die Seite zeigt sie nie („Lied · einzeln · 1:06“).
* Ein Einzeltitel ist **eine normale Serie** (eigene ID, Ordner, `serie.json`, Cover, Papierkorb, Umbenennen, `serie/art_setzen`). Neue Folgen kommen nicht hinein: `ergaenzen` und `folge/verschieben` mit einem Einzeltitel als Ziel antworten `wunsch_ungueltig` bzw. `ziel_ungueltig`; `serien/zusammenfuehren` (Admin) darf ihn als Quelle, nicht als Ziel benutzen.
* **Kapitel:** *Folge-Objekt* von `serie/get` bekommt `kapitel` = Liste aus `titel`, `start_s` und, bei Ordner-Folgen, `track` (0-basiert); nur wenn es mindestens zwei gibt. Quelle und Regeln: 11.4.8. Die Hörstelle bleibt, wie sie ist (`track`, `position_s`).

**V-9 Hörkopie (Fähigkeit `hoerkopie`; neu in Rev. 4)**

* Die Audio-Ansicht (V-6) liefert die **Hörkopie**, wenn die Folge eine braucht und sie fertig ist, sonst das Original. Antwortkopf `X-Tobibox-Quelle: kopie` oder `original` (zum Prüfen). Fehler 503 `hoerkopie_wartet` mit `Retry-After: 60`, solange die Kopie fehlt (die Ansicht reiht die Kopie dann vorn in die Warteschlange ein). Ohne Kopie-Pflicht ändert sich nichts.
* *Folge-Objekt* von `serie/get`: `hoerkopie` = `original` (braucht keine), `wartet`, `fertig`, `fehler`. `hello.grenzen`: `hoerkopie_kbit` (96).
* **Befehl `hoerkopie/neu_erzeugen`** (**Admin**): `serie_id` optional (fehlt = alle mit Zustand `fehler`); löscht Kopie und Marke und stellt die Folge neu in die Warteschlange.
* Speicherort, Zeitpunkt, Bedarf und Fehlerfall: 11.4.7.

**V-3 Anzeigenamen der Boxen** (Feld da, keine Fähigkeit): Optionen der Integration (`config_flow.py`, `strings.json`, `translations/de.json`) bekommen **ein Textfeld** „Namen der Boxen: `box1=Mond, box2=Stern`“ (U21c; gleiche Prüfung wie `parse_boxen`, höchstens 40 Zeichen je Name, Hinweis „ohne das Wort Box“). `boxen/list` trägt `anzeige` (nie `null`: Name aus den Optionen, sonst `anzeigename` der Discovery, sonst der Box-Name);
`hello.box_anzeigen`. Im Repo steht kein echter Name. Die Seite zeigt nur `anzeige`.

**V-4 Rechte (Ausnahme zur Additivität)**: Abschnitt 10; Vertrag 2.1 ersetzen, W-19 streichen. Neue Codes `zu_viele_aenderungen`; neue Eingabe `erwartet_revision` bei `einstellungen/set`; `erwartet_ziel` bei `zuordnung/remove` wird für Nicht-Administratoren Pflicht.

**V-5 Kleinigkeiten, die die Seite braucht (U4, U9, U13)**
* `eingang/list`: Feld `quelle` (`upload` oder `nas`) **fest** im Vertrag (die Integration weiß es: `registriere_upload`).
* `zuordnung/list` und `config.json` `zuordnungen.<uid>`: optionales Feld `angelegt_am` (Zeitstempel; die Box ignoriert es, `data-model.md` 1.4; +30 Byte je Zuordnung).
* `neue_tobies`-Ereignis „aufgelegt“ (wenn die Box die Kennung auch beim Auflegen eines **bekannten** Tobies meldet): Das Feld gibt es heute vermutlich nicht; ohne es entfällt nur „Auflegen zum Finden“ (5.7). Bei Bedarf additiv `status.letzte_kennung`.

### 11.3 Datenmodell und Sync (U8)

`data-model.md` Abschnitt 5 (`serie.json`), additiv, die Box ignoriert alles (1.4):

| Feld | Typ | Bedeutung |
|---|---|---|
| `art` | `"hoerspiel"`, `"hoerbuch"`, `"musik"`, `"geschichte"` | Art des Eintrags; fehlt = `hoerspiel` |
| `art_quelle` | `"tags"`, `"geraten"`, `"manuell"` | woher `art` kommt; `manuell` wird nie überschrieben |
| `folgen_info.<name>.dauer_s` | Zahl (Sekunden) | Länge der Folge (Rev. 3, 11.4.4); fehlt bis zum Nachholen |
| `folgen_info.<name>.spuren_s` | Liste von Zahlen | bei Ordner-Folgen die Länge jedes Tracks, in Folgenreihenfolge |
| `cover_suche` | object `{"ergebnis": "tags"|"datei"|"keine", "zeit": <Zeitstempel>}` | Marke „schon gesucht“ (U5) |
| `einzeln` | bool | **(Rev. 4)** Einzeltitel: genau eine Folge, steht für sich, keine neuen Folgen; fehlt = `false` |
| `folgen_info.<name>.kapitel` | Liste aus `{"titel": string, "start_s": Zahl, "track": int?}` | **(Rev. 4, 11.4.8)** Kapitel der Folge, aufsteigend nach `start_s`, höchstens 500, Titel höchstens 120 Zeichen; nur wenn mindestens zwei |
| `folgen_info.<name>.codec` | string | **(Rev. 4)** Audiocodec des Originals aus `ffprobe` (`mp3`, `aac`, `vorbis`, `opus`, `flac`, `alac`, `pcm_s16le` …); entscheidet, ob eine Hörkopie nötig ist (11.4.7) |
| `folgen_info.<name>.hoerkopie` | object `{"zustand", "zeit", "grund"?}`; `zustand` ist `"wartet"`, `"fertig"` oder `"fehler"`, `zeit` ein Zeitstempel, `grund` ein Code | **(Rev. 4)** Stand der Hörkopie; fehlt = nicht nötig oder noch nicht geprüft |

**Reservierte Dateinamen** im Serien-Ordner (neu, additiv; die Bibliothek der Box liest nur Audioendungen und ignoriert sie schon): `cover.jpg` (automatisch), `cover-eigen.jpg` (Foto, hat Vorrang); als **Quelle** gelesen, nie geschrieben: `folder.jpg`, `cover.png`. Beim **Zusammenführen** übernimmt die Ziel-Serie das Cover der Quelle, wenn sie selbst keines hat;
im **Papierkorb** wandern die Dateien mit dem Ordner; beim **Umbenennen** bleiben Ordnername und ID, also auch die Cover. Beim Einsortieren aus einem Eingangs-Ordner hat ein mitgeliefertes `cover.jpg`/`folder.jpg` Vorrang vor dem eingebetteten Bild und geht nicht in den Papierkorb.

**Sync:** `box/src/tobibox/sync.py` nimmt zusätzlich `cover*.jpg`, `cover*.png` und `folder.jpg` aus (zu den Systemdateien und `_upload`, `_papierkorb`, `eingang`). Empfehlung aus dem Review, übernommen: Die Box hat kein Display; 500 Cover à 150 KiB wären 75 MB SD-Platz und Schreibvorgänge für nichts.
Test in `box/tests`: Sync mit Covern überträgt sie nicht; Zusammenführen; Wiederherstellen aus dem Papierkorb; Serie umbenennen. Das ist die **einzige Änderung am Box-Code in Stufe A**.

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

* **Neue `HomeAssistantView`** `TobiboxAudioView` (neben `TobiboxUploadView` in `http.py`, bei `async_setup` registriert): `GET /api/tobibox/audio/{serie_id}/{folge_id}`, `requires_auth = True`, `cors_allowed = False`. `folge_id` ist der **Name der Folge** wie in `serie.json` `folgen` (Datei- oder Ordnername, URL-kodiert; die Seite kennt ihn aus `serie/get`). Bei Ordner-Folgen (mehrere Tracks) kommt `?track=<n>` (0-basiert) dazu.
* **Pfad-Sicherheit (IDs statt Pfade):** (1) `serie_id` muss die ID einer **bekannten** Serie sein (Index der Integration, `gueltige_serien_id`); (2) `folge_id` muss **genau** einem Eintrag in `serie.folgen` entsprechen (Vergleich der ganzen Zeichenkette, keine Pfadbildung aus der Eingabe); (3) `track` ist eine Zahl, die Datei kommt aus der **eigenen sortierten Trackliste** (`dateien.tracks_in_ordner`), nicht aus der Anfrage;
  (4) der fertige Pfad wird **aufgelöst** (`resolve()`) und muss **unter dem aufgelösten Medien-Pfad** liegen (`is_relative_to`), sonst 404; ein Symlink aus dem Medien-Pfad hinaus ist damit ausgeschlossen; (5) nur Dateien, keine Ordner; Endung (ohne Groß/Klein) aus `ENDUNGEN`; (6) Systemordner (`_papierkorb`, `_upload`, `eingang`, `export`, `releases`, alles mit `.`, `@`, `#`, `$` am Anfang) sind nie eine Serie, also nie erreichbar. Kein `..`, keine absoluten Pfade, keine Rückgabe von Pfaden in Fehlertexten.
  Dieselbe Strenge wie HA bei `/media/…` (`raise_if_invalid_path`, `async_full_path` mit `relative_to`; gelesen in `media_source/local_source.py`), nur enger, weil hier gar kein Pfad von außen kommt.
* **Antwort:** `aiohttp.web.FileResponse` (kann Range, ETag, Last-Modified, schickt die Datei ohne sie in den Speicher zu laden; HA benutzt es für `/media/…` genauso), Kopfzeilen `Content-Type` aus einer **eigenen Tabelle** (mp3 `audio/mpeg`, m4a und m4b `audio/mp4`, aac `audio/aac`, flac `audio/flac`, ogg und opus `audio/ogg`, wav `audio/wav`), `X-Content-Type-Options: nosniff`, `Cache-Control: private, max-age=3600`. Keine `Content-Disposition: attachment` (Browser soll abspielen, nicht speichern).
* **Range:** Safari, Chrome und Firefox fragen Audio in Teilen an (`Range: bytes=…`) und springen mit neuen Teil-Anfragen; ohne 206 geht Springen nicht (Safari spielt ohne Range gar nicht). `FileResponse` antwortet mit 206, `Content-Range`, `Accept-Ranges: bytes`, 416 bei Unmöglichem (Test unten). Nur **ein** Bereich je Anfrage; mehr fragt kein Browser.
* **Fehler:** 401 ohne gültige Anmeldung (macht HA), 404 `folge_nicht_gefunden` (auch für unbekannte Serie, damit man nicht Ordner erraten kann), 503 `medien_nicht_erreichbar` (NAS weg). **Kein** `HEAD` nötig (Browser nehmen GET mit Range); `HEAD` kann man wie bei `LocalMediaView` ergänzen.
* **Last:** Audio ist klein (MP3 128 kbps = 1 MB je Minute); ein Hörbuch mit 10 Stunden ist rund 600 MB, aber nur die gerade gebrauchten Teile werden übertragen. Höchstens 4 gleichzeitige Streams je Benutzer (darüber 429 `zu_viele_streams`), damit ein hängender Tab nicht das NAS beschäftigt.

#### 11.4.2 Zugriff: signierter Pfad (`auth/sign_path`)

Ein `<audio src>` kann **keinen Authorization-Header** senden. Darum:

1. Die Seite holt sich per WebSocket `{"type": "auth/sign_path", "path": "/api/tobibox/audio/<serie>/<folge>", "expires": 3600}` einen **signierten Pfad** (HA-eigener Befehl, jeder angemeldete Benutzer darf ihn).
2. Das Ergebnis ist `…?authSig=<JWT>`; die Seite setzt es (mit `hass.hassUrl()` für die Companion-App) als `src` des `<audio>`-Elements.
3. HA prüft die Signatur: **Pfad und Abfrage-Teile müssen genau stimmen** (`?track=2` ist mitsigniert, also je Track neu signieren), **nur GET und HEAD**, gebunden an die Anmeldung (Refresh-Token) des Benutzers: wird sie widerrufen, ist die Adresse tot. Der Benutzer ist danach `request["hass_user"]`, die Ansicht läuft also als er.
4. **Gültigkeit:** Die Ablaufzeit wird **nur beim Start jeder Anfrage** geprüft. Weil der Browser beim **Springen und nach Pausen neue Anfragen** mit derselben Adresse stellt, darf die Gültigkeit nicht „30 Sekunden“ (Vorgabe von `auth/sign_path`) sein. Vorschlag: **1 Stunde je Folge**; ist sie abgelaufen, meldet `<audio>` einen Fehler (401), und die Seite **signiert neu und macht an der Stelle weiter** (kurzer Aussetzer, kein Fehler für Verena). HA selbst benutzt für Medien **24 Stunden** (`CONTENT_AUTH_EXPIRY_TIME` in `media_player/const.py`); wäre die Wiederherstellung unschön, kann man darauf gehen (Frage 14).
5. Die Seite signiert **nur die Folge, die sie gleich spielt** (und die nächste im Voraus, damit der Wechsel nahtlos wird), nicht die ganze Liste.

*Beleg:* So macht HA es für Medien: `media_source/resolve_media` (`media_source/http.py`) ruft `async_process_play_media_url` (`media_player/browse_media.py`) auf, und das signiert mit `async_sign_path` und `CONTENT_AUTH_EXPIRY_TIME`. Die Kamera-Bilder von HA nutzen **nicht** diesen Weg, sondern ein eigenes Zugriffs-Token an der Entität (`/api/camera_proxy/<entity_id>`; **nicht** weiter geprüft). Der Beleg ist also der Medienweg von HA, nicht die Kamera.

**Was ist das, in Alltagssprache (Rev. 4, Frage 14):** Wenn du am Handy auf „Reinhören“ tippst, holt sich dein Handy die Audiodatei bei Home Assistant ab. Dafür braucht es eine **Adresse**, ähnlich einer Internetadresse. Der Player in der Seite kann beim Abholen kein Passwort mitschicken; darum hat die Adresse einen **eingebauten Schlüssel**, der nach einer Weile **von selbst abläuft**. Das ist wie eine Eintrittskarte mit Uhrzeit: Nach Ablauf funktioniert genau diese Adresse nicht mehr, und wer sie weitergibt, kann nichts mehr damit anfangen. Die Seite holt sich bei Bedarf eine neue Karte und macht an derselben Stelle weiter. Gefragt war nur: **Wie lange soll die Karte gelten?** (Empfehlung: 1 Stunde.)

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

* `serie.json`, `folgen_info.<name>.dauer_s` (Zahl, Sekunden, auf ganze Sekunden gerundet) und bei Ordner-Folgen `spuren_s` (Liste der Tracks in der Reihenfolge der Folge). Additiv, die Box ignoriert es (`data-model.md` 1.4).
* **Beim Einsortieren** gespeichert; für den **Bestand** einmal im Hintergrund nachgeholt, genau wie die Cover-Suche (5.5): nur Folgen ohne `dauer_s`, eine Datei nach der anderen, 20 s Zeitgrenze je Datei, Abbruch bei `medien_nicht_erreichbar`, **kein Dauer-Scan beim Öffnen der Seite**. Bei 5 000 Dateien ist das eine Sache von Minuten bis Stunden im Hintergrund; bis dahin zeigt die Seite „–“ statt der Dauer und blendet die Zeitleiste erst beim Laden der Datei auf (`loadedmetadata`).
* *Serie-Kurzform* bekommt `dauer_s` (Summe); das *Folge-Objekt* von `serie/get` bekommt `dauer_s`, `spuren_s`.
* **Ein Durchgang für alles (Rev. 4):** Derselbe `ffprobe`-Aufruf liefert mit `-show_chapters` zusätzlich die **Kapitel** (11.4.8); dazu wird der **Codec** des ersten Audio-Stroms gemerkt (`codec`, für 11.4.7). `ffprobe.py` ergänzt `-show_chapters` in `baue_ffprobe_befehl` (die vorhandenen Tests prüfen die Argumentliste mit „enthält“, nicht auf Gleichheit; geprüft in `test_ffprobe.py`) und `Probe` um `kapitel` und `codec`. **Kein zweiter Lesedurchgang über das NAS:** Beim Einsortieren und beim Nachholen des Bestands (Zeitgrenze 20 s je Datei, Abbruch bei `medien_nicht_erreichbar`, nie beim Öffnen der Seite) kommen `dauer_s`, `spuren_s`, `kapitel` und `codec` aus **einem** Lauf je Datei; erst danach reiht der Hintergrundlauf die Hörkopien ein.

#### 11.4.5 Hörstelle (Weiterhören), je Benutzer in HA

* **Speicher:** HA-`Store` `tobibox.hoerstellen` (Version 1, `.storage/`), gespeichert mit `async_delay_save` (Verzögerung 10 s, fasst Schreibvorgänge zusammen): `{ "<user_id>": { "<serie_id>": { "zeit": <ISO>, "folge": "<Name>", "folgen": { "<Name>": { "p": 47, "d": 167, "t": <ISO>, "fertig": false, "track": 0 } } } } }`.
  Je Benutzer nur Einträge für angefangene Serien; Obergrenze 2 000 Serien je Benutzer, 100 Folgen je Serie (darüber fallen die ältesten weg). Größenordnung: 5 000 Folgen × 90 Byte ≈ 450 KB, kein Problem. Beim Start fallen Einträge unbekannter Benutzer, gelöschter Serien und nicht mehr vorhandener Folgen weg.
* **Kein Zugriff auf fremde Hörstellen:** jeder Befehl nimmt die Benutzer-Kennung aus der Verbindung (`connection.user.id`), nie aus der Eingabe. Auch Administratoren sehen nur ihre eigenen (Frage 16).
* **Befehle** (WebSocket, Recht **alltag** = alle angemeldeten Benutzer, Vertrag W Abschnitt 6 Form):

| Befehl | Eingabe → Ausgabe |
|---|---|
| `hoerstelle/get` | `serie_id` → `weiter` (`folge`, `position_s`, `track`, `anteil`, `rest_s`, `zeit`) oder `null`; `folgen` = Objekt Name → `position_s`, `dauer_s`, `fertig`, `zeit` |
| `hoerstelle/set` | `serie_id`, `folge`, `position_s`, `dauer_s`, optional `track`, optional `fertig` → `{}`. Prüft: Serie und Folge gibt es, `0 ≤ position_s ≤ dauer_s + 2`, `dauer_s` ≤ 24 Stunden; `fertig` wird auch gesetzt, wenn `position_s ≥ dauer_s − 2`. Antwortet **sofort**, schreibt über `async_delay_save`. |
| `hoerstelle/liste` | `limit` (1 bis 12, Vorgabe 8) → angefangene, nicht fertige Einträge, zuletzt angehört zuerst: `serie_id`, `name`, `folge`, `position_s`, `anteil`, `rest_s`, `zeit` (für die Reihe „Weiterhören“) |

  `serien/list` bekommt je Kurzform (nur wenn angefangen) `hoerstelle` (`anteil`, `rest_s`, `zeit`, `folge`) **für den Anfragenden** und die Sortierung `angehoert`; `serie/get` bekommt je Folge `hoerstelle` (`position_s`, `fertig`). So braucht die Bibliothek keine zweite Abfrage je Zeile.
* **Wann die Seite speichert (gedrosselt):** höchstens **alle 10 Sekunden** während der Wiedergabe, **sofort** bei Pause, beim Springen, beim Wechsel der Folge, beim Ende, beim Schließen der Seite (`pagehide`, `visibilitychange`; auf dem Handy nicht verlässlich, darum die 10 Sekunden). Das Backend drosselt zusätzlich (höchstens 30 Schreibaufrufe je Minute und Benutzer, sonst `zu_viele_aenderungen`; dieselbe Grenze wie 10.3, eigener Zähler).
* **Zwei Geräte:** Es gilt „zuletzt gespeichert gewinnt“ je Folge. Wer auf dem Handy bei 10:00 pausiert und am Computer „Weiterhören“ drückt, holt sich beim Öffnen der Seite die Stelle von dort (`hoerstelle/get`). Gleichzeitig auf zwei Geräten hören ist nicht vorgesehen.
* **Reinhören in „Gehört“ (Stufe B, Rev. 4):** Die Hörstellen-Aufrufe sind zugleich die Quelle für „Mein Reinhören“: HA leitet daraus Sitzungen ab, die Seite sendet nichts Neues (12.5).
* **Box und Hörstelle sind getrennt:** Die Box führt ihre eigene Stelle (`resume.json`, `data-model.md`); das Reinhören verändert sie nie und umgekehrt.

#### 11.4.6 Was belegt ist und was noch zu prüfen bleibt

| Aussage | Stand |
|---|---|
| `auth/sign_path` gibt es, Eingaben `path`, `expires` (Vorgabe 30 s), nur für angemeldete Benutzer | **belegt** (HA-Quelle `components/auth/__init__.py`, `dev`, 12.11.) |
| Signatur bindet Pfad **und** Abfrage-Teile, gilt nur für GET/HEAD, ist an den Refresh-Token gebunden, Ablauf wird beim Anfragestart geprüft | **belegt** (HA-Quelle `components/http/auth.py`: `async_sign_path`, `async_validate_signed_request`) |
| HA selbst nutzt signierte Pfade mit 24 Stunden für Medien | **belegt** (`media_player/browse_media.py`, `media_player/const.py`: `CONTENT_AUTH_EXPIRY_TIME = 3600 * 24`; `media_source/http.py`); Kamera-Bilder nutzen einen anderen Weg (nicht geprüft) |
| `web.FileResponse` beantwortet Range mit 206, `Content-Range`, `Accept-Ranges`, 416 | **belegt**: Test mit aiohttp 3.14.5 (die Version im selben Python-Umfeld wie HA 2026.10.4): `bytes=0-1` → 206, `bytes=50000-` → 206, `bytes=-500` → 206, `bytes=999999-` → 416; ohne Range 200 mit `Accept-Ranges: bytes`; `HEAD` ohne eigenen Handler 405 |
| HA benutzt `FileResponse` für lokale Medien (`/media/…`) und prüft Pfade mit `relative_to` | **belegt** (`media_source/local_source.py`) |
| Browser-Formate nach Tabelle 11.4.3 | **belegt aus caniuse-Daten**; Verhalten auf Tobias' Geräten **zu prüfen** (A15b) |
| Sonderzeichen im Pfad (Umlaute, Leerzeichen, Klammern, Punkte) laufen durch die Signatur (die Prüfung vergleicht den **entschlüsselten** Pfad) | **zu prüfen**: Test in A4c mit „Der Wald (Teil 1).mp3“ und „Märchen.m4a“ |
| Ob `FileResponse` auf dem NAS-Pfad (SMB/NFS) beim Springen schnell genug ist | **zu prüfen** am echten NAS (A16) |
| Companion-App: spielt `<audio>` bei gesperrtem Bildschirm weiter, zeigt der Sperrbildschirm die Medien-Steuerung? | **zu prüfen** (iOS und Android, A15b); sonst nur „im Vordergrund hören“ |
| `ffmpeg` ist in HA da: Die Integration `ffmpeg` (`homeassistant/components/ffmpeg`, Zweig `dev`, geholt am 12.11.) legt einen `FFmpegManager` an (`get_ffmpeg_manager(hass).binary` liefert den Pfad, Vorgabe `ffmpeg`); beim offiziellen Container-Image rechnet sie mit `ffmpeg` 6.0 (`OFFICIAL_IMAGE_VERSION`). `ffmpeg` ist also Teil des Images, nicht nur ein Python-Paket. Die Integration `tobibox` nutzt schon `shutil.which("ffmpeg")` (`ffprobe.py`, `ffmpeg_pfad()`) und das README sagt „HA OS bringt beide mit“ | **belegt** (Quellen); `get_ffmpeg_manager` wirft `ValueError`, wenn die Integration `ffmpeg` nicht geladen ist: darum nur als **optionale** Erstwahl, kein Eintrag in `manifest.json`; Version und Encoder in Tobias' HA **zu prüfen** (A16: `ffmpeg -version`, `-encoders | grep aac`) |
| `ffprobe -show_chapters` liefert Kapitel (Startzeit, Titel) für M4B **und** MP3 (ID3v2 `CHAP`), auch mit erzwungenem Format | **belegt** (Test mit ffprobe 6.1.1: M4B und MP3 mit je 3 Kapiteln, `start_time` und `tags.title` kommen zurück, Aufruf wie `ffprobe.py`); echte Hörbücher von Tobias **zu prüfen** (A3b) |
| Hörkopie mit dem eingebauten AAC-Encoder: Größe und Zeit | **gemessen** (Testrechner, ffmpeg 6.1.1): 10 Minuten aus OGG Vorbis, Opus, FLAC und ALAC je 7,3 MB (Soll 7,2 MB), Dauer unverändert (600,0 s), Kodierzeit 6,6 bis 9,5 s (60 bis 90 mal Echtzeit); **auf HA-Hardware zu prüfen** (A16) |
| Safari verlangt eine Geste zum Start | berücksichtigt: Ton startet nur nach Tap; Folgenwechsel nach Ende läuft weiter, weil die Seite schon spielt (zu prüfen auf iOS) |

#### 11.4.7 Hörkopie (neu in Rev. 4)

**Ziel (Runde 8, Nr. 17: alle Formate):** Reinhören geht für jede Datei des Bestands, auf jedem Gerät, mit Springen, ohne Umwandeln beim Abspielen. Die **Box bekommt immer das Original**; die Kopie ist nur für den Browser.

* **Wann braucht eine Folge eine Hörkopie?** Nach dem **Codec des Originals** (`codec`, aus `ffprobe`, 11.4.4): `mp3` und `aac` (also MP3, M4A/M4B mit AAC, AAC) spielen überall: **Original**. Alles andere bekommt eine Kopie: `vorbis` (OGG), `opus`, `alac` (M4A), `flac`, `pcm_*` (WAV) und alles Unbekannte. FLAC und WAV spielen in neuen Browsern; die Kopie spart dort Mobilfunk und Wartezeit (WAV: 10 MB je Minute gegen 0,7 MB). Die Regel steht an **einer** Stelle im Code (eine Funktion `braucht_hoerkopie(codec)`).
* **Erzeugen:** `ffmpeg -nostdin -v error -protocol_whitelist file -f <Format der Endung> -i file:<Pfad> -vn -map_metadata -1 -c:a aac -b:a 96k -movflags +faststart -f mp4 file:<Ziel>.part`, danach umbenennen. Gleiche Härtung wie `ffprobe.py` (Liste von Argumenten, nie Shell, `RLIMIT_AS`, Zeitgrenze; Programm: Erstwahl `get_ffmpeg_manager(hass).binary`, wenn die Integration `ffmpeg` geladen ist, sonst `shutil.which("ffmpeg")`). **Warum AAC in M4A:** `aac` ist der in ffmpeg eingebaute Encoder (immer da, `libmp3lame` nicht in jedem Bauplan), M4A spielt auf allen Zielgeräten, `+faststart` legt den Index nach vorn, damit der Browser sofort per Range anfragen kann. 96 kbit/s reichen zum Erkennen, was etwas ist. Bei Ordner-Folgen: eine Kopie je Track.
* **Wo (Entscheidung und Begründung):** Auf dem NAS im Ordner **`hoerkopien/<serie_id>/<kennung>.m4a` neben `medien/`** (wie `export/`, `eingang/` und `releases/`, gleiche Freigabe, Vertrag W 11.1), **nicht** im Medienordner der Boxen und **nicht** in HAs Konfigurationsordner. Gründe: (1) `hoerkopien/` liegt **außerhalb des rsync-Moduls `medien`**; die Box holt sie nie, `rsync --delete` und das Einlesen der Box-Bibliothek berühren sie nicht, und **`sync.py` braucht keine weitere Ausnahme** (Alternative „im Medienordner, vom Sync ausgeschlossen“ wäre eine zweite Box-Änderung und ein Risiko für das Einlesen der Bibliothek); (2) HAs Konfigurationsordner liegt meist auf einer kleinen SD-Karte oder SSD und wandert in jede HA-Sicherung (Kopien wären Sicherungsballast); (3) die Integration schreibt auf diese Freigabe schon heute. `kennung` = die ersten 16 Zeichen von `sha1(folge|track|größe|Änderungszeit)`: ändert sich das Original, entsteht eine neue Kopie; verwaiste Kopien (Serie oder Folge endgültig gelöscht, Kennung veraltet) räumt der Hintergrundlauf weg. `serie.json` verweist **nicht** auf die Datei, sie merkt nur den Zustand (`hoerkopie`, 11.3).
* **Wann sie entsteht:** (a) **Beim Einsortieren**, nachdem die Prüfung (`pruefe_datei`) gelaufen ist und die Datei in `medien/` liegt: im Hintergrund, die Meldung „fertig“ wartet nicht darauf. (b) **Bestand** im Hintergrund, wie die Dauer (Frage 18, „passt“): derselbe Durchgang (11.4.4), danach die Kopien nacheinander, eine Datei zugleich, mit niedriger Priorität (`nice`), nie beim Öffnen der Seite. (c) **Vorgezogen**: Wird eine Folge ohne fertige Kopie abgespielt, stellt die Audio-Ansicht sie an die Spitze der Warteschlange und antwortet 503 `hoerkopie_wartet`; die Seite sagt „Die Hörprobe wird gerade vorbereitet …“ und versucht es nach 30 Sekunden von selbst noch einmal. Zeitgrenze für `ffmpeg`: `max(120 s, Dauer/8 + 60 s)`, höchstens 2 Stunden.
* **Speicherbedarf (Schätzung):** 96 kbit/s = 12 KB/s = **43 MB je Stunde**. Gemessen: 10 Minuten werden 7,3 MB (11.4.6). Beispiele: 20 Hörspiel-Folgen zu je 28 Minuten in OGG ≈ **0,4 GB**; 100 Stunden Hörbücher in Opus ≈ **4,3 GB**; **schlechtester Fall:** der ganze Bestand (50 bis 80 GB, grob 1 600 Stunden) läge in keinem Browser-Format: ≈ **70 GB**, also etwa so viel wie die Originale (die Kopie spart bei Quellen unter 100 kbit/s nichts). Realistisch (MP3 und M4A als Normalfall, Tobias nennt „alle Formate“ als Möglichkeit): **wenige GB**. Das NAS muss das tragen, die Boxen nicht (Frage 26).
* **Rechenzeit:** gemessen auf dem Testrechner 60 bis 90 mal Echtzeit; auf HA-Hardware (Raspberry Pi 4, HA Green) vorsichtig 15 bis 30 mal Echtzeit: ein Hörbuch von 10 Stunden braucht dann 20 bis 40 Minuten, **im Hintergrund** (zu prüfen in A16). Der Bestand wird in Stunden bis Tagen fertig, niemand muss warten: bis dahin gilt `hoerkopie_wartet`.
* **Fehlerfall:** (1) `ffmpeg` fehlt oder die Fähigkeit nicht gemeldet: keine Kopien, kein Fehler; Formate ohne Browser-Unterstützung zeigen den Rückfalltext (heutiger Stand). (2) Das Kodieren schlägt fehl (kaputte Datei, Zeitgrenze, Platz, NAS weg): `hoerkopie.zustand = "fehler"` mit `grund` (`kodieren_fehlgeschlagen`, `zeitgrenze`, `kein_speicher`, `medien_nicht_erreichbar`). **Keine Dauerschleife:** ein Versuch je Datei und Start der Integration, danach erst wieder auf `hoerkopie/neu_erzeugen` (Admin). NAS weg pausiert die Warteschlange (wie bei der Dauer). Die Seite zeigt „Für diese Datei gibt es keine Hörprobe. Auf der Box spielt sie trotzdem.“ (3) Halbe Dateien (`*.part`) werden beim Start gelöscht. (4) Die Box ist nie betroffen: sie liest nur `medien/`.
* **Papierkorb, Umbenennen, Verschieben, Zusammenführen:** Kopien hängen an `serie_id` und Kennung; Papierkorb und Umbenennen berühren sie nicht, Verschieben und Zusammenführen ändern die `serie_id` (die Kopie wird beim nächsten Lauf unter der neuen ID wiedergefunden oder neu gemacht), endgültiges Löschen räumt der Hintergrundlauf auf.

#### 11.4.8 Kapitel (neu in Rev. 4)

* **Quellen, in dieser Reihenfolge:** (1) **Eingebettete Kapitel** der Datei (`ffprobe -show_chapters`: M4B-Kapitelspur, MP3 ID3v2 `CHAP`); belegt für beide Formate (11.4.6). (2) Bei einer **Ordner-Folge** ist jeder **Track ein Kapitel**: Titel aus dem Tag `title`, sonst Dateiname ohne Endung und ohne führende Nummer; Start = Summe der vorigen `spuren_s`. (3) Sonst keine Kapitel (die Seite zeigt keine Liste). Eine Datei **mit** eingebetteten Kapiteln gewinnt vor den Tracks.
* **Speicherung:** `folgen_info.<name>.kapitel` in `serie.json` (11.3), beim Einsortieren gelesen und im Hintergrund für den Bestand nachgeholt (11.4.4, im selben Lauf). Sortiert nach `start_s`; doppelte Startzeiten und Rückwärtssprünge fliegen raus; höchstens 500 Kapitel je Folge. Die Box ignoriert das Feld (data-model 1.4); `serie/get` gibt es als `kapitel` aus (V-8).
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
| **Wer** | Die **Box** (Kind = Box). Die Kennung des Tobies bleibt draußen (Frage 9). |
| **Reinhören am Handy** | zählt **nicht** bei den Boxen (5.12); es hat den eigenen Bereich „Mein Reinhören“, zugeordnet dem HA-Benutzer (12.5). |

Grenzfälle: Ein Tobie, der abgenommen und nach einer Minute wieder aufgelegt wird (`tobie_abgenommen`), ist **eine** Wiedergabe (Lücke höchstens 5 Minuten, Runde 8, Nr. 19); nach einer **längeren** Pause (`pause_lang`, über 10 Minuten, oder Lücke über 5 Minuten) ist das Weiterhören eine **neue** Wiedergabe: gehört „2 Mal“, aber nur einmal fertig. Bei Hörbüchern (eine lange Folge, abends in Portionen) ist „Mal“ deshalb eher hoch und „Hörzeit“ die ehrlichere Zahl; darum stehen beide in der Tabelle.
Das Zusammenfassen macht HA **beim Aufnehmen**: Beginnt eine Sitzung derselben Box und Folge höchstens 5 Minuten nach dem Ende der vorigen, bekommt sie dieselbe `wiedergabe`-Kennung; die Rangliste zählt `COUNT(DISTINCT wiedergabe)`, die Hörzeit bleibt die Summe der Sitzungen. Dieselbe Regel gilt für „Mein Reinhören“ (12.5).

### 12.3 Speicherung in HA: Vergleich

| | Recorder / Langzeitstatistik von HA | **Eigene SQLite-Datei** (`<config>/tobibox/gehoert.sqlite`) | JSON-Zeilen-Datei |
|---|---|---|---|
| Vorteile | kein eigener Speichercode; Diagramme und Karten von HA; Akku-Sensor hat `state_class: measurement`, damit gibt es **stündliche Langzeitstatistik ohne Ablauf** | beliebige Fragen (je Eintrag, Folge, Stunde, Box); unabhängig von der Recorder-Bereinigung; idempotent (`UNIQUE`); CSV-Export; HA-Sicherung enthält den Konfigurationsordner | trivial zu schreiben und zu lesen |
| Nachteile | Zustände nur 10 Tage (Vorgabe `purge_keep_days`); Langzeitstatistik nur Summen/Mittel je Entität, **kein „welches Hörspiel“**; eine Entität je Eintrag bei 250+ Einträgen untauglich | eigener Code: Schema, Migration, Zugriff im Executor, Tests; in HA-Standardkarten nicht sichtbar | langsam bei vielen Zeilen, kein Index, Gefahr halber Schreibvorgänge |
| Eignung | **Akku-Verlauf** (Statistik, schon vorhanden), Hörzeit gesamt | **Hörereignisse** und Technik-Ereignisse | nur Notlösung |

**Empfehlung:** SQLite für Hörereignisse und Technik-Ereignisse (Lader, Sync, Fehler, online), **Langzeitstatistik von HA für den Akku** (Seite liest sie über `recorder/statistics_during_period`, nur Administratoren). Favoriten liegen in HA (`.storage/tobibox.favoriten`, Schlüssel `serie_id` oder `serie_id#folge`), nicht in `serie.json` und nicht auf der Box.

**Speicherbedarf (Schätzung, 250 Byte je Zeile mit Index):** 2 Boxen × 20 Sitzungen am Tag ≈ 14 600 Zeilen im Jahr ≈ **3,7 MB**; selbst 100 Sitzungen je Box und Tag nur ≈ 18 MB im Jahr. Technik-Ereignisse (50 je Box und Tag) ≈ 5 MB im Jahr. Akku-Statistik ≈ 2 bis 3 MB im Jahr.
Zusammen **etwa 10 MB im Jahr**, 100 MB in zehn Jahren: „unbegrenzt“ ist unproblematisch. Eine Aufräumregel ist nicht nötig. Trotzdem: Knopf „Alle Hördaten löschen“ und „Als Tabelle sichern“ in „Technik“ (Hördaten über Kinder sind persönlich; sie bleiben nur in HA, nie in der Cloud).

**Spalten der Tabelle `sitzungen` (SQLite, Rev. 3):** `box`, `seq`, `sitzung`, `wiedergabe`, `serie`, `folge`, `start`, `dauer_s`, `ende`; `UNIQUE(box, seq)`, Indizes `(serie, folge, start)` und `(box, start)`. Die Rangliste ist eine einzige Abfrage: `GROUP BY serie` mit `COUNT(DISTINCT wiedergabe)` (Wiedergaben), `SUM(dauer_s)` (Hörzeit), `COUNT(DISTINCT folge)` unter `WHERE ende='ende_der_folge'` (fertige Folgen); die Aufteilung dasselbe mit `GROUP BY folge` für eine Serie.
Ziel: unter 50 ms bei 15 000 Zeilen (Jahresbedarf, siehe oben), Test in B3.

**Reinhören (Rev. 4):** Zweite Tabelle `reinhoer_sitzungen` in derselben Datei: `benutzer` (HA-Benutzerkennung), `serie`, `folge`, `wiedergabe`, `start`, `gespielt_s`, `ende`; Indizes `(benutzer, start)` und `(benutzer, serie, folge)`. Größenordnung: 2 Erwachsene × 10 Sitzungen am Tag ≈ 7 300 Zeilen im Jahr ≈ 1,8 MB. Abfragen immer mit `WHERE benutzer = <Verbindung>`.

### 12.4 Vertragsentwurf `ha-websocket-v1.md` (Stufe B)

Fähigkeit **`gehoert`** (Reiter „Gehört“, Stern und Sortierungen erscheinen nur damit). Neue Befehle:

| Befehl | Recht | Eingabe → Ausgabe |
|---|---|---|
| `gehoert/zusammenfassung` | lesen | **Eingabe:** `box` (optional; Liste von Box-IDs, fehlt = alle), `zeitraum` (`woche`, `monat`, `jahr`, `alles`) **oder** `von`/`bis`, `nach` (Liste aus `box`, `serie`, `folge`, `tag`, `stunde`; **Box × Serie × Folge** geht in einem Aufruf), `quelle` (`boxen` Vorgabe, `reinhoeren`; bei `reinhoeren` ist `box` ungültig und die Benutzerkennung kommt **aus der Verbindung**, 12.5), `serie_id` (optional, schränkt auf einen Eintrag ein), `sortierung` (`wiedergaben` Vorgabe, `sekunden`), `limit` (1 bis 200). **Ausgabe:** `zeilen`, je Zeile die Schlüssel aus `nach` plus `wiedergaben`, `sekunden`, `fertig` (Sitzungen mit `ende_der_folge`) und, wenn `folge` nicht in `nach` steht, `folgen_fertig` und `folgen_gesamt`; dazu `summe` (`wiedergaben`, `sekunden`, `fertig`). Regeln: 12.2.1 |
| `gehoert/zuletzt`, `gehoert/meist` | lesen | `box`, `limit`, `von`, `bis` → Einträge mit Zeit bzw. Sekunden |
| `favorit/set`, `favoriten/list` | **Alltag** / lesen | `serie_id`, `folge` (optional), `an` → Liste |
| `technik/verlauf` | admin | `box`, `von`, `bis` → Akku (Statistik), Ladezeiten, Laufzeit je Ladung, Syncs, Fehler |
| `gehoert/exportieren`, `gehoert/loeschen` | admin | CSV bzw. alles löschen (mit Bestätigungswort); betrifft **nur die Boxen-Daten** |
| `reinhoer/loeschen` (Rev. 4) | **Alltag** | löscht die **eigenen** Reinhör-Daten (Rückfrage in der Seite); fremde nie, auch nicht als Administrator |

**Aufrufe der Seite (5.10):** Rangliste je Box: `nach=["serie"]`, `box=["box1"]` (oder beide Boxen addiert: ohne `box`); Vergleich nebeneinander: `nach=["box","serie"]`. Aufteilung nach Folgen: `serie_id`, `nach=["folge"]`. Das Säulendiagramm bleibt `nach=["tag","box"]`, die Tageszeiten `nach=["stunde"]`.

`serien/list` und `folgen/list` bekommen die Sortierungen `zuletzt_gehoert`, `meist_gehoert` und den Filter `favorit` (nur mit Fähigkeit `gehoert`). Hördaten der Boxen sind lesbar für alle HA-Benutzer (Frage 8); Reinhör-Daten nur für den eigenen Benutzer (12.5, Frage 23). Fähigkeit **`gehoert_reinhoeren`** (der Umschalter „Mein Reinhören“ erscheint nur damit).

### 12.5 Reinhören in „Gehört“ (Rev. 4, Runde 8 Nr. 21)

**Entscheidung Tobias:** Reinhören wird **doch erfasst**, aber dem **HA-Benutzer** zugeordnet, nicht einer Box.

**Datenquelle (ohne neue Aufrufe der Seite):** Die Hörstellen-Aufrufe (`hoerstelle/set`, 11.4.5) kommen höchstens alle 10 Sekunden während der Wiedergabe und sofort bei Pause, Sprung, Wechsel und Ende. HA leitet daraus **Sitzungen** ab, je Benutzer und Folge: ein offener Zustand mit `start`, `letzte Zeit`, `letzte Position` und `gespielt_s`. Bei jedem Aufruf gilt: `dt` = Sekunden seit dem letzten Aufruf, `dp` = Positionsänderung. Als **gespielt** zählt nur, wenn `0 < dp ≤ 1,5 × dt + 2` **und** `dt ≤ 30` (normale Wiedergabe bis 1,5-fach; Springen und lange Pausen zählen nicht). Die Sitzung endet bei `fertig` (`ende_der_folge`), beim Wechsel der Folge (`anderes`) oder wenn der nächste Aufruf mehr als 5 Minuten später kommt (`pause_lang`). **Gleiche Zählregel wie 12.2.1:** Eine Wiedergabe ist eine Sitzung mit mindestens 10 Sekunden `gespielt_s`; Sitzungen derselben Folge mit höchstens 5 Minuten Lücke zählen als **eine** Wiedergabe; „fertig“ = Ende der Folge; Hörzeit = Summe `gespielt_s`.
**Genauigkeit:** Schließt jemand die Seite, fehlen bis zu 10 Sekunden; das Handy kann die Seite einfrieren (`pagehide` ist nicht verlässlich). Für Hörzeit pro Tag reicht das, die Zahlen sind „etwa“. Die Erfassung beginnt mit Stufe B (frühere Hörstellen-Aufrufe haben keinen Verlauf); wer die Daten ab dem ersten Tag will, lässt die Ableitung schon in A4d einbauen (kleines Paket, Frage 23).

**Der Widerspruch und die Regel:** Drei Antworten von Tobias treffen hier zusammen. **Nr. 8:** Die Hördaten der **Boxen** sehen alle HA-Benutzer (die Kinder haben kein Konto; Löschen nur Admin). **Nr. 16:** Von der **Hörstelle** sieht jeder nur die **eigene**, auch ein Administrator. **Nr. 21:** Reinhören wird dem **Benutzer** zugeordnet. Nr. 8 und Nr. 16 stehen nicht im Widerspruch (Boxen gegen Benutzer). Nr. 21 macht aber die Reinhör-Daten zu Daten **über Erwachsene** (wer hat wann was angehört); das liegt näher an Nr. 16 als an Nr. 8.
**Empfehlung: Jeder sieht nur die eigenen Reinhör-Daten, auch Administratoren; die Boxen-Daten bleiben für alle sichtbar.** Gründe: dieselbe Regel wie bei der Hörstelle (nichts Neues zu erklären), Wandtablets und Gäste mit Konto sehen nichts über Tobias und Verena, kein Verwaltungsaufwand. Jeder darf **seine eigenen** Reinhör-Daten löschen (`reinhoer/loeschen`); „Alle Hördaten löschen“ in „Technik“ betrifft nur die Boxen-Daten. **Alternative:** Alle sehen alle (wie Nr. 8): einfacher zu bauen (kein Filter nach Benutzer), aber Verena sähe, was Tobias hört, und umgekehrt, und ebenso jedes Gäste-Konto. **Frage 23 an Tobias.**

**Bedienung:** Reiter „Gehört“ mit dem Umschalter **Boxen | Mein Reinhören**; Inhalt in 5.10.1. Die Benennung „Mein Reinhören“ (statt „Eltern“) steht für den **angemeldeten Benutzer**, wer das auch ist; sie passt zur Regel „nur eigene“. Die Namen von Personen erscheinen nirgends als Auswahl.
**Vertrag (Stufe B):** `gehoert/zusammenfassung` mit `quelle="reinhoeren"` (12.4), `reinhoer/loeschen`, Fähigkeit `gehoert_reinhoeren`; Paket B3 bis B5 (Abschnitt 15.2).

## 13. Stufe C (Idee): eigene Playlists

Nur skizziert, Bau später. **Ziel:** Eine Playlist aus beliebigen Folgen und Liedern (auch aus verschiedenen Einträgen) kann das Ziel eines Tobies sein, so wie ein Hörspiel.

**Datenmodell (Idee):**

* `config.json` `zuordnungen.<uid>.ziel`: neuer Typ `"playlist"` mit `ziel.playlist = <id>`. Weil das ein neuer `ziel.typ` ist, den eine alte Box als ungültig ablehnt (`data-model.md` 2: unbekannter `ziel.typ` macht die ganze Liste ungültig), steigt `schema_version` auf **3**, **erst wenn** ein Tobie eine Playlist benutzt. Folge: **Boxen zuerst aktualisieren** (Update), dann die Funktion freischalten (Fähigkeit `playlists`).
* Playlist-Datei **`playlists/<id>.json`** im Medienwurzelordner (reservierter Name `playlists`, **wird synchronisiert**, anders als `_…`-Ordner): `{schema_version, id, name, angelegt_am, eintraege: [{serie, folge}]}`, höchstens 200 Einträge. Eine Datei statt Eintrag in `config.json`, damit die Liste unter ihrer 256-KiB-Grenze bleibt.
* HA-Befehle (Alltag): `playlist/create`, `playlist/rename`, `playlist/eintraege_setzen`, `playlist/delete` (Papierkorb wie bei Einträgen); Index und Suche zählen Playlists wie Einträge der Art „Playlist“.

**Auswirkung auf die Box:** neuer Ziel-Typ in `core-interface.md` 6: Die Box löst die Einträge lokal auf (Serie und Folge gibt es dort, weil die ganze Bibliothek synchronisiert wird), baut die MPD-Warteschlange, überspringt fehlende Einträge (`playlist_eintrag_fehlt`, ohne Abbruch) und führt den **Zeiger** unter `playlist:<id>` in `resume.json` (Index und Position).
Fehlt die Datei noch (nicht synchronisiert): wie `serie_fehlt` spielt die Box die Überraschungs-Serie. Das Ereignis `gespielt` (B) trägt dann `playlist=<id>` und den gespielten Eintrag.

**Auswirkung auf den Sync:** Eine neue Playlist kommt erst mit dem **nächsten Abgleich** auf die Box, nicht sofort wie die Liste per MQTT. Die Seite sagt „Die Playlist wird auf die Boxen kopiert“ und zeigt je Box „aktuell“ oder „noch nicht“. Änderungen an Titeln brauchen nichts.

**Auswirkung auf die Oberfläche:** Zielwahl bekommt eine dritte Auswahl „Playlist“, jedes Lied/jede Folge den Knopf „Zu einer Playlist hinzufügen“ (Prototyp: ausgegraut), Reiter „Tobies“ eine Playlist-Karte mit ▲/▼. **Aufwand:** Box-Code, drei Verträge (`data-model`, `core-interface`, `mqtt-v1` Schema-Hinweis), Boxen-Update; als eigener Block C1 bis C4 nach B (Abschnitt 15).

**Hochladen als Playlist (Rev. 4, Karte d):** Die Karte „Neue Playlist“ im Blatt „Was lädst du hoch?“ (5.6) ist im Prototyp sichtbar und mit „Stufe C – Idee“ markiert. In Stufe C fragt die Vorschau nach dem **Namen der Playlist**; jede Datei wird ein **Einzeltitel** (V-7, `ziel=einzeln`), und die Playlist verweist auf diese Titel (`eintraege: [{serie, folge}]`). Der Satz lautet dann „4 Dateien → neue Playlist „Autofahrt“ mit 4 Liedern.“ Weil Einzeltitel schon normale Serien sind, braucht die Playlist **kein** zweites Datenmodell für Dateien. Upload-Wunsch `ziel=playlist` (V-7) und die Befehle aus diesem Abschnitt (`playlist/*`) kommen in C1.
**Weiterspielen über eine Playlist (Runde 8, Nr. 22):** Reinhören auf einer Playlist spielt die Einträge in ihrer Reihenfolge und geht am Ende eines Titels zum nächsten, auch über Einträge verschiedener Serien. Die Hörstelle bleibt je Folge und Benutzer (11.4.5), braucht also keine Änderung; neu ist nur die **Warteschlange der Seite** (Quelle „Playlist“ statt „Folgen der Serie“) und der Knopf „Reinhören“ auf der Playlist-Karte. Für Alben gilt das Weiterspielen schon in Stufe A (5.12).

## 14. Barrierefreiheit, Gefahrloses (U24)

* **Tap-Ziele:** mindestens 44 × 44 px (im Prototyp bei 390 und 1280 px geprüft; Ausnahme nur Textlinks im Fließtext). **Kontrast:** Text mindestens 4,5:1, große Schrift und Symbole 3:1, in Hell, Dunkel und im Theme mit hellem Primärton (Abschnitt 4).
  Farbe nie allein: Zustände haben Text („bitte ansehen“, „fertig“, „Still/Leiser“); Diagramme haben Beschriftung, Zahlen und Tabelle.
* **Dialoge:** das native **`<dialog>` mit `showModal()`** (Esc, Fokusfalle und Hintergrundsperre kostenlos); Fokus beim Öffnen auf die **harmlose** Antwort („Abbrechen“, „Nein, so lassen“); danach zurück zum auslösenden Knopf. Im Shadow DOM prüft man den Fokus mit `getRootNode().activeElement`, nicht `document.activeElement`.
  Wo kein Dialog möglich ist, bekommt der Seitenrahmen `inert`.
* **Screenreader:** ein `aria-live`-Bereich sagt Ergebnisse an („Fertig. Dieser Tobie spielt jetzt Lange Serie“); die **Fertig-Karte erhält den Fokus**, wenn sie die Karte ersetzt (`aria-live` allein genügt Tastaturnutzern nicht, 24c). Fortschrittsbalken `role="progressbar"`; Cover `aria-hidden` (der Name steht daneben);
  Tag-Knöpfe `aria-pressed`; Zählzeile der Bibliothek `aria-live="polite"`; Reiter-Zahl „1 neuer Tobie“ als Text (24e).
* **Schriftgröße:** alles in `rem`; bleibt bei 200 % Zoom und bei 320 px benutzbar (Kacheln brechen um, kein waagerechtes Scrollen). Reiterschrift 12 px ist die Grenze; bei Systemschrift „groß“ bricht der Reiter „Bibliothek“ nicht, weil die Beschriftung kurz ist (24d).
* **Bewegung:** `prefers-reduced-motion`: kein Pulsieren, keine Übergänge. **Sprache:** Uhrzeiten 24 Stunden, Datum „12.11., 08:30“, unabhängig von der Browsersprache.
* **Löschen:** nur mit Rückfrage und rot; die Rückfrage sagt, was geschieht und was bleibt. Löschknöpfe stehen **nie in einer Reihe mit häufigen Knöpfen** (eigene Karte oder Blattende, durch Linie und mindestens 32 px abgesetzt). „Rückgängig“ statt Rückfrage dort, wo es sich zurückdrehen lässt (Zuordnen, Umstellen).
* **Reihenfolge ohne Ziehen:** ▲/▼ (nur Administratoren); der Fokus bleibt auf dem Knopf der verschobenen Folge. **Foto zuschneiden ohne Ziehen:** vier Pfeilknöpfe und Regler.
* **Player (Rev. 3):** Die Vollansicht ist ein natives `<dialog>` (Esc schließt, Fokus beim Öffnen auf Play/Pause, danach zurück auf die Leiste). Die Zeitleiste ist ein Schieberegler mit `aria-valuetext` („1:41 von 2:47“); alle Knöpfe 44 px oder mehr, Play 72 px; Geschwindigkeit als Knopfgruppe mit `aria-pressed`;
  Symbol-Knöpfe haben Namen („30 Sekunden zurück“, „Nächste Folge“). Die Leiste unten ist ein Knopf mit Namen „Player öffnen: <Titel>, <Eintrag>“. Es wird **nie von selbst Ton gestartet** (nur nach Tap); Tastatur: Leertaste = Play/Pause im Dialog. Fortschrittsbalken in Listen haben `role="progressbar"` mit Wert; Farbe nie allein (Text „noch 18 Min.“ / „Fertig gehört“).
* **Doppeltippen:** Knöpfe, die etwas senden, sind während des Aufrufs gesperrt (`anfrage_id`).
* **Hochladen (Rev. 4):** Das Blatt „Was lädst du hoch?“ ist ein natives `<dialog>` (Esc, Fokus zurück auf „Dateien wählen“); die fünf Karten sind echte Knöpfe (mindestens 76 px hoch, Titel, Erklärung und Beispiel im Namen); die gestrichelte Karte „Neue Playlist“ hat `aria-disabled="true"` und nennt „Stufe C – Idee“ im Text (kein Ausgrauen durch Deckkraft, damit der Kontrast 4,5:1 hält). Zwischen den Schritten wechselt nur der Inhalt des Blatts; der Fokus geht auf die Überschrift, nicht auf ein Textfeld (am Handy würde sonst die Tastatur aufgehen). Der Satz der Vorschau ist ein `role="status"`-Bereich (`aria-live="polite"`) und ändert sich beim Tippen. Art-Auswahl als Knopfgruppe mit `aria-pressed`.
* **Kapitelliste (Rev. 4):** Zeilen sind Knöpfe (mindestens 56 px) mit Namen „Kapitel 4: Der Sturm, ab 1:12, aktuelles Kapitel, abspielen“; das aktuelle Kapitel hat `aria-current="true"` und eine getönte Fläche **und** den Text „hier weiter“ bzw. „läuft“ (Farbe nie allein); schon gehörte tragen Häkchen **und** den Text „gehört“. Im Player-Blatt öffnet der Fokus auf dem aktuellen Kapitel.
* **Umschalter „Boxen | Mein Reinhören“ (Rev. 4):** Knopfgruppe mit `aria-pressed`, jeder Knopf mindestens 44 px hoch; der Hinweis „Nur du siehst das.“ steht als Text, nicht nur als Symbol.

## 15. Arbeitspakete (Sonnet, billigstes passendes Modell)

Regeln: Vor dem Bau Resolve mit Tobias. Jedes Paket hat eigene Tests und ist allein lauffähig. **Die bestehenden Tests** (`homeassistant/tests/frontend/`: 121 Tests der alten Seite; `homeassistant/tests` mit `pytest`; `box/tests`) müssen nach **jedem** Paket grün sein und werden **nicht angepasst** (U6: die alte Seite bleibt eingebettet). Pakete A1, A2, A3, A4 hängen nicht von der Seite ab und laufen parallel.
Der Vertrag (A0) wird **zusammen mit A1** geschrieben, nicht davor (er beschreibt, was gebaut ist).

### 15.1 Stufe A (wird gebaut)

| AP | Inhalt | Modell | Tests |
|---|---|---|---|
| A0 | **Vertrag W und Datenmodell** einarbeiten (11): Eintrag „Änderung 12.11.“, Abschnitt 2.1 ersetzen, W-19 streichen, `serie.json`-Felder, reservierte Dateinamen. Nur nach Freigabe | Sonnet | – |
| A1 | **Rechte und Schutz** (10): `befehl(recht=…)`, Tabelle 10.2, Schutz 10.3 (`erwartet_ziel`, bekannte Kennungen, Mengen, `erwartet_revision`, Zeitzone ignorieren, `sofort` nur Admin), `boxen/list`/`export_lesen` nur Admin, 10 frühere Stände der Liste, Upload ohne `require_admin`. **`require_admin` bleibt `True`** | Sonnet | `tests/test_websocket_api.py`: Tabelle 10.2 als Parametertest (Admin und Normal-Benutzer je Befehl); Schutzfälle einzeln; `tests/test_services.py`: jede Aktion als Nicht-Admin = `Unauthorized`; `tests/test_upload.py`: Nicht-Admin 200 |
| A2 | **Anzeigenamen** (V-3): Textfeld in Optionen, `strings.json`, `translations/de.json`, `anzeige`, `hello.box_anzeigen` | Haiku (Formular) + Sonnet (Hub) | `test_config_flow.py`, Reihenfolge der Rückfälle |
| A3 | **Art und Bibliothek-Backend** (V-2): Art-Vorschlag beim Einsortieren, `serien/list` erweitert (**Rev. 4:** `einzeln`, Filter `sammlung`/`einzeln`), `folgen/list` (`serie_einzeln`), `serie/art_setzen`, `zuordnung/list` mit `text`/`neu`, Index (Einzeltitel als Serie **und** als Folge) | Sonnet | Art-Regeln mit Tag-Fixtures (Genre, `.m4b`, Albumlänge); Suche, Filter, Sortieren, Blättern; **Leistungstest 600 Einträge / 2 000 Folgen < 200 ms** (dazu 300 Einzeltitel); alte Aufrufe ohne `limit` unverändert; Filter `einzeln` liefert nur Einzeltitel |
| A3b | **Dauer, Kapitel, Codec** (11.4.4, 11.4.8): `ffprobe.py` ergänzt `-show_chapters`; `dauer_s`, `spuren_s`, `kapitel`, `codec` beim Einsortieren aus **einem** Lauf speichern, Nachholen im Hintergrund (Zeitgrenze, Abbruch bei NAS weg, nie beim Öffnen), Felder in Kurzform und `serie/get`, `serie.json` additiv | Sonnet | `tests/test_media.py`: Dauer einer MP3 und einer Ordner-Folge, fehlende Datei, Nachholen genau einmal; **Kapitel** aus einer M4B und einer MP3 (ID3v2 `CHAP`) mit `ffmpeg`-Fixture, Kapitel aus den Tracks eines Ordners, doppelte Startzeiten, mehr als 500; Box ignoriert die Felder (`box/tests`: `serie.json` mit `dauer_s`, `kapitel` wird gelesen); `test_ffprobe.py` bleibt grün |
| A3c | **Hörkopie** (11.4.7, V-9): `braucht_hoerkopie(codec)`, Warteschlange mit einem Lauf zugleich und `nice`, `ffmpeg`-Aufruf (gehärtet wie `ffprobe.py`, Erstwahl `get_ffmpeg_manager`, Rückfall `shutil.which`), Ordner `hoerkopien/` neben `medien/`, `*.part` und Aufräumen, Zustand in `serie.json`, Fehlerfall ohne Dauerschleife, `hoerkopie/neu_erzeugen` (Admin) | Sonnet | `tests/test_hoerkopie.py` (ffmpeg-Fixture OGG, Opus, FLAC, WAV, ALAC): Kopie entsteht und ist AAC/M4A mit gleicher Dauer; MP3 und AAC bekommen keine; Fehler (kaputte Datei, Zeitgrenze, `kein_speicher`) setzt `fehler` und wiederholt nicht; `*.part` wird beim Start gelöscht; Quelle ändert sich → neue Kennung, alte Kopie wird aufgeräumt; kein `ffmpeg` → keine Fähigkeit, kein Fehler; die Box liest `medien/` unverändert (`box/tests`) |
| A3d | **Hochladen mit Wunsch und Einzeltitel** (V-7, V-8): Upload-Felder `ziel`, `art`, `name`; Regeln `neu` (Gruppierung nach Art, nie zusammenführen, `serie_name_doppelt`), `ergaenzen`, `einzeln` (`einzeln: true`), `auto` unverändert; `einsortierung/neu` (**Machbarkeit zuerst prüfen**, Rückfall Papierkorb); `wunsch` in `eingang/list`; `ziel_ungueltig` für Einzeltitel als Verschiebeziel | Sonnet | `tests/test_eingang.py` und `test_upload.py`: 12 Dateien mit gleichem Album: `neu`+`hoerbuch` = **eine** Folge mit 12 Tracks, `neu`+`musik` = **12** Folgen; `ergaenzen` ohne Folgen-Ordner, nummerngerecht eingefügt; `einzeln` = je Datei eine Serie mit einer Folge; ohne `ziel` alle bisherigen Testfälle T1 bis T17 unverändert; `wunsch_ungueltig`; Name doppelt → „(2)“; `einsortierung/neu` nur solange unverändert |
| A4 | **Cover-Backend** (V-1, 5.5): Extraktion mit Marke, Nachholen im Hintergrund mit Zeitgrenze, `ffmpeg` fehlt, GET/POST/DELETE, `cover/neu_suchen`, Zusammenführen und Papierkorb | Sonnet | `tests/test_cover.py` (ffmpeg-Fixture MP3 mit/ohne Bild, kaputtes Bild, Marke verhindert Wiederholung, Zeitgrenze, Foto-Upload: falscher Typ, zu groß, nicht quadratisch, Original wird nicht gespeichert, ETag) |
| A4b | **Sync-Ausschluss** `cover*.jpg`, `cover*.png`, `folder.jpg` in `box/src/tobibox/sync.py` | Sonnet | `box/tests`: Sync mit Covern überträgt sie nicht, übrige Dateien unverändert |
| A4c | **Audio-Ausgabe** (11.4.1, 11.4.2, V-9): `TobiboxAudioView` (`FileResponse`, MIME-Tabelle, Pfad-Sicherheit, `track`, Stream-Grenze), **liefert die Hörkopie, wenn nötig und fertig; sonst 503 `hoerkopie_wartet` und Vorziehen in der Warteschlange**, Fähigkeit `reinhoeren` | Sonnet | `tests/test_audio.py` mit HA-Testclient: Range 200/206/416; 401 ohne Anmeldung und mit abgelaufener oder fremder Signatur; signierter Pfad mit richtigem und falschem Pfad oder `?track`; **`..`, `%2e%2e`, `%2F`, unbekannte Serie oder Folge, Symlink aus dem Medien-Pfad, Ordner statt Datei, Endung `.txt`, Papierkorb- und Eingang-Ordner, `hoerkopien/` als Serie: alle 404**; Umlaute, Leerzeichen und Klammern im Namen (laufen durch die Signatur); Ordner-Folge mit `track`; fünfter gleichzeitiger Stream 429; NAS weg 503; **OGG-Folge: erst 503 `hoerkopie_wartet`, nach der Kopie 206 mit `audio/mp4` und `X-Tobibox-Quelle: kopie`, Range auf der Kopie** |
| A4d | **Hörstelle** (11.4.5): `Store` `tobibox.hoerstellen` mit `async_delay_save`, `hoerstelle/get`, `hoerstelle/set`, `hoerstelle/liste`, Drosselung, Aufräumen (Benutzer, Serien, Folgen), Felder `hoerstelle` in Kurzform, `serie/get`, Sortierung `angehoert` | Sonnet | `tests/test_hoerstelle.py`: zwei Benutzer sehen nie die Daten des anderen (auch kein Administrator); Prüfungen (Folge unbekannt, Position über Dauer, Dauer über 24 Stunden); „fertig“ ab Dauer − 2 s; 31. Aufruf in einer Minute `zu_viele_aenderungen`; Daten überleben einen Neustart (Store); gelöschte Serie fällt weg; Sortierung `angehoert` |
| A5 | **Texte** `texte.js`: Fehlertabelle (6.1), Gründe (7.3), Sätze (5.1.1), vollständig gegen den Vertrag geprüft | Haiku + Sonnet-Review | Test: jeder Code der Vertragstabelle hat einen Text; Texte wörtlich wie hier |
| A6 | **Panel-Gerüst** (neue Dateien): Reiter und Technik-Knopf (`narrow`, sticky, `visualViewport`), Routen, Theme-Token und Kontrastfunktion, Zustände, `<dialog>`-Blatt, Meldungen; **alte Komponente als `tobibox-technik` mit Schalter `eingebettet`** | Sonnet | jsdom: Reiter und Routen, Nicht-Admin sieht keinen Technik-Knopf, Zustände, Fokus nach Dialog; **alte 121 Tests unverändert grün** |
| A7 | **Start und Bibliothek (Rev. 3, Rev. 4)**: Status-Sätze, Kopfzeile mit „+“, Arten-Zeile, Reihen „Weiterhören“ und „Neu“, Listenzeilen (Fortschritt, Tobie-Symbol; **Einzeltitel „Lied · einzeln · 1:06“**), Blatt „Sortieren und Filter“ (**mit Gruppe „Was zeigen“**), Suchansicht `#suche` (3 Gruppen, **Einzeltitel nur in „Folgen und Lieder“**), Cover-Laden (`fetchWithAuth`, `blob:`, `IntersectionObserver`), Blättern | Sonnet | jsdom: Satz-Tabelle; Suche entprellt; Blatt sendet die Eingaben von V-2 (`filter`, `sortierung`, `angehoert`) und **`filter` `sammlung`/`einzeln`**; „Mehr zeigen“ sendet `offset`; Platzhalterfarbe stabil; Fortschrittsbalken aus `hoerstelle`; Einzeltitel erscheint nicht als „1 Folge“ |
| A8 | **Serienseite**: Kopf (Gesamtdauer), „Reinhören/Weiterhören“ (Zustände), „Tobie zuordnen“, Menü des Eintrags und der Folge, Name/Art/Cover ändern (Zuschneiden im Browser), „Das ist richtig/stimmt nicht“, Folgenliste mit Abspielknopf und Fortschritt, Papierkorb; **Rev. 4: Abschnitt „Kapitel“ für Hörbücher, Seite des Einzeltitels ohne Folgenliste, Karte „Hörprobe wird vorbereitet“, „Anders einsortieren“ als erste Möglichkeit unter „Das stimmt nicht“** | Sonnet | jsdom: Blatt „Tobie für dieses Lied“, Zuschneiden (Canvas-Mock), Löschen mit `tobies_bestaetigt`, Knopf-Beschriftung je Hörstelle (neu, angefangen, fertig, läuft); **Kapitelzeile: Tipp sendet Sprung, aktuelles Kapitel `aria-current`; Einzeltitel: keine Folgenliste, Tobie-Ziel `folge`** |
| A8b | **Player** (5.12, 11.4): `<audio>`, Signatur holen und bei 401 oder Fehler neu holen, nächste Folge vorsignieren, Ordner-Folgen über Tracks, Leiste und Vollansicht, ±30 s, Geschwindigkeit, Hörstelle gedrosselt speichern (10 s, Pause, Wechsel, `pagehide`), `canPlayType`-Vorabprüfung, Media-Session; **Rev. 4: Kapitelzeile und „Kapitel“-Blatt, Sprung (eingebettet: Zeit; Ordner: Track), `hoerkopie_wartet` mit Wiederholung nach 30 s** | Sonnet | jsdom mit gemocktem `HTMLMediaElement` (jsdom spielt nichts): Speichern höchstens alle 10 s und sofort bei Pause; Neusignieren bei 401 setzt an der Stelle fort; Folge-Ende startet die nächste; „Vorige“ springt zuerst an den Anfang; Format nicht abspielbar → Text 6.1; **Kapitelsprung setzt die Zeit, bei Ordner-Folgen den Track; 503 `hoerkopie_wartet` zeigt den Satz und versucht es nach 30 s erneut**; **Playwright** (A14) mit echtem Ton gegen eine Testdatei |
| A9 | **Neuer Tobie und Tobies**: Karte, Zielwahl, Fertig-Karte mit Name, Rückgängig (`erwartet_ziel`), Tobies-Liste (zuletzt angelernt, Suche), Blatt, Kachel „Gute Nacht“ | Sonnet | jsdom mit `mock-hass.mjs`: Ereignis `neu` → Karte; Tap → `zuordnung/set`; Name; Rückgängig → `zuordnung/remove` mit `erwartet_ziel` |
| A10 | **Anlernen** (Ziel Serie und Folge, Name, Wiederaufnahme) | Sonnet | jsdom: alle Zustände aus Vertrag 4.3 → Texte 7.2 |
| A11a | **Hinzufügen: Wahl, Vorschau, Hochladen (Rev. 4)**: Blatt „Was lädst du hoch?“ mit fünf Karten, Vorschau in Sätzen mit Eingaben je Weg (Name und Art; Auswahl mit Suche und Covern; Namen je Datei), „Ändern“ und „Hochladen“, Warteschlange 2 parallel, Fortschritt, Abbruch, Unterbrechung, 413. **Name-Vorschlag aus den Tags im Browser:** nur der Dateikopf der ersten Datei (`File.slice`, kleines Leseprogramm für ID3v2 und MP4-Atome, Rückfall Datei- und Ordnername); **Machbarkeit zu prüfen**, sonst nur Dateiname | Sonnet | jsdom: Karten und Sätze für jeden Weg und Art (Tabelle 7.3), Satz ändert sich beim Tippen, „Ändern“ erhält die Eingaben, `ziel`/`art`/`name`/`serie_id` im Upload, Fortschrittsschritte, Upload-Fehlercodes, Playlist-Karte nur Meldung |
| A11b | **Hinzufügen: Eingang-Anbindung** (24-Stunden-Liste, `quelle`, Gründe, NAS-Einträge, „Das stimmt nicht“, **Rev. 4: „Daraus ist geworden: …“, „Anders einsortieren …“ öffnet dieselbe Wahl mit dem Titel „Was ist das?“ und dem Knopf „Neu einsortieren“**) | Sonnet | jsdom: Gründe-Texte, „bitte kurz ansehen“, Wiederaufnahme nach Neuladen; **`einsortierung/neu` mit dem Wunsch, Fehler `neu_einsortieren_nicht_moeglich` in Worten** |
| A12 | **Abends** (Schnellwahl, Zeilenliste, Blatt, Prüfregeln, `erwartet_revision`) | Sonnet | `panel_quiet.test.mjs` bleibt für die alte Seite; neue Tests: 24-Stunden-Auswahl, krumme Minute bleibt, Fehlerstelle in Worten |
| A13 | **Technik**: Einbettung, Warnleisten, „Frühere Stände“, „Cover neu suchen“, Ausblenden-Wert | Sonnet | jsdom: Karten, Rechte |
| A14 | **Playwright-Skript (Pflicht)** unter `homeassistant/tests/frontend/`: Tap-Ziele ≥ 44 px, kein waagerechtes Scrollen (320, 390, 1280 px), Kontrast in **drei Themes**, Screenshots für Tobias; **Rev. 3:** erste Cover der Bibliothek in den oberen 40 % (390 px), Ablauf Suche → Serie → Reinhören → Springen → Neuladen → Weiterhören an der Stelle | Sonnet | das Skript selbst; vom Prototyp übernommen (`audit`, Ablauf) |
| A15 | **Doku**: `homeassistant/README.md` (Seite für alle, Namen, Cover, **HA-Automation „Neuer Tobie“ als Vorlage**), `docs/betrieb/` „Für Verena“ | Haiku | Abgleich mit `texte.js` |
| A15b | **Companion-App und Geräte früh prüfen** (Rev. 4 zusätzlich: spielen iPhone und Mac-Safari die Hörkopien, wie lange braucht `ffmpeg` auf Tobias' HA für 10 Minuten Audio, passt der Platz auf dem NAS) (iOS und Android: Reiter unten, Safe Area, Tastatur, Foto; **Rev. 3:** läuft `<audio>` bei gesperrtem Bildschirm und in der App weiter, zeigt der Sperrbildschirm Titel und Tasten, spielt Safari/iOS die Formate des Bestands, Springen auf dem NAS-Pfad schnell genug) | Tobias | – |
| A16 | **Abnahme mit Tobias**, Schritt für Schritt im Chat (Mac, Handy): Tobie zuordnen (a, b), Lied-Tobie, Hinzufügen vom Handy, Cover per Foto, Abends, Papierkorb als Nicht-Admin; **Rev. 3:** Reinhören am Handy und am Mac, **Stelle am Handy merken und am Mac weiterhören**, Springen, Folgenwechsel, Hörbuch mit Ordner-Folge | Projektleitung + Tobias | – |
| A17 | **Seite für alle öffnen** (`require_admin=False`) | Sonnet | `test_init.py`: Panel ohne `require_admin`; Tabelle 10.2 mit Testbenutzer ein letztes Mal |

Empfohlene Reihenfolge: A1, A2, A3, A3b, A3c, A3d, A4, A4b, A4c, A4d (parallel) → A0 → A5 → A6 → A7 → A8, A8b, A9, A10 → A11a, A11b → A12 → A13 → A14 → A15 → A15b/A16 → A17.

### 15.2 Stufe B (eigener Block, nach Freigabe)

| AP | Inhalt | Vertragsänderung |
|---|---|---|
| B1 | **Vertrag** `mqtt-v1.md`: `gespielt`, `gehoert_quittung` (12.2); `ha-websocket-v1.md`: Befehle und Fähigkeit `gehoert` (12.4); `data-model.md`: `gehoert.jsonl` der Box | ja |
| B2 | **Box:** Sitzungserkennung, Puffer `gehoert.jsonl` (Schreibbudget), Senden und Quittung | `mqtt-v1` |
| B3 | **HA:** SQLite-Speicher (Spalten und Indizes 12.3, **mit `wiedergabe`** und der Tabelle `reinhoer_sitzungen`), Aufnahme mit Doppelerkennung, Quittung, Technik-Ereignisse aus `status`, Favoriten; **Sitzungsableitung aus `hoerstelle/set` (12.5)**; Test der Zählregel 12.2.1 (10-Sekunden-Grenze, fertig, DISTINCT, Zeiträume, **5-Minuten-Zusammenfassung**) und der Ableitung (Springen zählt nicht, Pause über 5 Minuten beendet die Sitzung, 1,5-fach, Wechsel der Folge) | – |
| B4 | **HA-Befehle** `gehoert/*` (`zusammenfassung` mit `nach` = Box × Serie × Folge **und `quelle`**), `favorit/*`, `technik/verlauf`, **`reinhoer/loeschen`**, Sortierungen und Filter in `serien/list`/`folgen/list`; Test: zwei Benutzer sehen nie die Reinhör-Daten des anderen (auch kein Administrator) | `ha-websocket` |
| B5 | **Seite:** Reiter „Gehört“ (Rangliste mit Aufteilung nach Folgen, SVG-Diagramme, **Umschalter Boxen \| Mein Reinhören**), Stern, Sortierungen, Technik-Karte Akku-Verlauf | – |
| B6 | **Abnahme** mit Tobi (Box im Hörbetrieb, offline hören und danach verbinden) | – |

### 15.3 Stufe C (eigener Block, später)

C1 Verträge (`data-model`, `core-interface`, `mqtt-v1` Schema-Hinweis, `ha-websocket` `playlist/*`, Upload-Wunsch `ziel=playlist`) · C2 Box (Ziel-Typ, Zeiger, Sync-Regel, Update) · C3 HA (Befehle, Datei, Index, Papierkorb) · C4 Seite (Zielwahl, Karte, Blatt, **Hochladen als Playlist, Reinhören und Weiterspielen über eine Playlist**) · C5 Abnahme. Reihenfolge: erst Boxen aktualisieren (Schema 3), dann freischalten.

## 16. Offene Fragen für Tobias (mit Empfehlung)

Fragen 1 bis 13 sind entschieden (`resolve.md`). **Fragen 14 bis 22** hat Tobias in Runde 8 (`brainstorm.md`) beantwortet; sie stehen unten mit ihrer **Antwort**. **Neu in Rev. 4: Fragen 23 bis 26**, nur echte Abwägungen, je mit Empfehlung.

| Nr. | Frage | Empfehlung |
|---|---|---|
| 1 | „Technik“ statt „Für Tobias“, als Knopf oben statt als Reiter (U22)? | Ja: kein Personenname, ein Reiter weniger (4 statt 5, mit „Gehört“ 5 statt 6). |
| 2 | Soll Verena einen **Papierkorb-Vorgang selbst rückgängig** machen können (Wiederherstellen nur für das, was sie in den letzten 15 Minuten selbst hineinlegte)? | Nein in Stufe A (Wiederherstellen bleibt Admin); nach den ersten Wochen neu abwägen. |
| 3 | Die letzten **10 Stände der Liste** aufbewahren (U2, Sicherung gegen Fehler mit Folgen für alle)? | Ja, kleines Paket in A1. |
| 4 | **Regeln für den Art-Vorschlag** (11.2): passt das zu deinen Dateien (Genre-Tags, `.m4b`, Albumlänge)? | Fünf Beispieldateien je Art prüfen, bevor A3 fertig ist; Fehlgriffe kann man mit „Art ändern“ beheben. |
| 5 | **`cover*.jpg` nicht auf die Boxen** synchronisieren (U8)? | Ja; ein späteres Display bräuchte eine neue Entscheidung. |
| 6 | **Wochenplan-Grafik** später statt jetzt, **Reihenfolge ändern** nur Admin (U23)? | Ja. |
| 7 | Papierkorb für Alle: reicht die Rückfrage mit Namen der betroffenen Tobies? | Ja. |
| 8 | Dürfen **alle HA-Benutzer** die Hördaten sehen (Stufe B), oder nur Administratoren? | Alle (Kinder haben kein HA-Konto); der Löschknopf bleibt Admin. |
| 9 | Stufe B meldet die **Box** (Kind = Box), nicht die Kennung des Tobies. Reicht das? | Ja (weniger Daten); die Kennung später additiv, falls „welcher Tobie“ wichtig wird. |
| 10 | **Speicherplatz der Boxen:** Der Sync nimmt die **ganze** Bibliothek (200 Hörbücher können über 50 GB sein; erster Abgleich dauert Stunden). Reicht der Platz, oder soll später eine Auswahl je Box möglich sein? | Vor dem Einsortieren der 200 Hörbücher `speicher_frei` prüfen; eine Auswahl je Box wäre ein eigenes Thema, nicht Teil dieser Oberfläche. |
| 11 | **HA-Automation „Neuer Tobie → Mitteilung aufs Handy“** als Vorlage in der Doku (U9)? | Ja (keine neue Funktion). |
| 12 | Reihenfolge der geplanten Stufen: **B vor C**? | Ja: B bringt Nutzen ohne Box-Updates am Datenmodell; C braucht ein Boxen-Update. |
| 13 | **Seite erst nach der Abnahme für alle öffnen** (A17, U7)? | Ja. |
| 14 | **Was ist der Abspiel-Link, und wie lange gilt er?** In Alltagssprache: Wenn du am Handy auf „Reinhören“ tippst, holt sich dein Handy die Audiodatei bei Home Assistant ab. Dafür braucht es eine **Adresse**, und diese Adresse hat einen **eingebauten Schlüssel, der nach einer Weile von selbst abläuft**, wie eine Eintrittskarte mit Uhrzeit (der Player im Browser kann beim Abholen kein Passwort mitschicken, darum der Schlüssel). Wie lange soll die Karte gelten? (11.4.2) | **1 Stunde je Folge.** Läuft sie mitten im Hören ab, holt die Seite von selbst eine neue und macht an derselben Stelle weiter (kurzer Aussetzer, kein Fehler für Verena). Alternative: 24 Stunden wie HA bei Medien (seltener Aussetzer, aber eine weitergereichte Adresse gilt länger). **Beantwortet (Runde 8):** Tobias fragte, was das ist; nach der Erklärung gilt die Empfehlung (1 Stunde, neu signieren), solange er nicht widerspricht. |
| 15 | **Reinhören für alle HA-Benutzer**, auch Wandtablets und Gäste mit Konto (Runde 7)? | Ja; der Zugriff ist auf die Musik und Hörspiele der Familie beschränkt, die Hörstelle ist je Benutzer. **Beantwortet (Runde 8): Anhören dürfen alle.** |
| 16 | Darf ein **Administrator fremde Hörstellen** sehen? | Nein (nur eigene), weniger Daten, nichts zu erklären. **Beantwortet (Runde 8): Ja, nur die eigene Hörstelle** (auch der Administrator). Gilt jetzt auch für „Mein Reinhören“ (Empfehlung in Frage 23). |
| 17 | **Formate:** Welche Dateiformate liegen im Bestand? OGG/Opus spielt Safari erst ab Version 18.4; ALAC in M4A spielt Chrome nicht. Was tun, wenn ein Gerät es nicht spielt? | Hinweis „Auf der Box spielt es trotzdem“ in Stufe A; Umwandeln mit `ffmpeg` beim Abspielen wäre ein eigenes Paket. **Beantwortet (Runde 8): Alle Formate** (MP3, M4A/M4B, AAC, FLAC, OGG, Opus, WAV). **Folge (11.4.7):** Hörkopie, einmal erzeugt, nicht beim Abspielen; Ort und Platz in Frage 26. |
| 18 | **Dauer für den Bestand** im Hintergrund nachholen (11.4.4)? Bei vielen Dateien dauert es Minuten bis Stunden und liest jede Datei einmal vom NAS. | Ja, einmal, mit Zeitgrenze und ohne Scan beim Öffnen. **Beantwortet (Runde 8): Passt.** Derselbe Lauf holt jetzt auch Kapitel, Codec und die Hörkopien nach (11.4.4, 11.4.7, 11.4.8). |
| 19 | **Zählregel „einmal gehört“** (12.2.1): 10 Sekunden, „fertig“ = Ende der Folge. Sollen kurze Unterbrechungen (Tobie 1 Minute abgenommen) **zusammen** als eine Wiedergabe zählen? | Regel wie vorgeschlagen; Zusammenfassen bei höchstens 5 Minuten Abstand: ja, bei der Aufnahme in HA. **Beantwortet (Runde 8): Ja**, Unterbrechungen bis 5 Minuten sind **eine** Wiedergabe (jetzt Regel in 12.2.1, gilt auch für „Mein Reinhören“). |
| 20 | **Hörbuch aus einem Ordner mit vielen Tracks:** Eine Zeitleiste über alles (Vorschlag) oder eine Kapitelliste? | Eine Zeitleiste über alle Tracks (einfach; Kapitelliste später). **Beantwortet (Runde 8): Ja, eine Zeitleiste, und die Kapitelliste will er auch.** Gebaut: beides (5.3, 5.12, 11.4.8); Kapitel sind Tracks eines Ordners oder eingebettete Kapitel von M4B/MP3. |
| 21 | Soll **Reinhören in „Gehört“ zählen**? | Nein: „Gehört“ zeigt, was die Kinder an den Boxen hören. **Beantwortet (Runde 8): Doch erfassen, aber dem HA-Benutzer zugeordnet, nicht einer Box.** Umgesetzt als Bereich „Mein Reinhören“ in „Gehört“ (Stufe B, 5.10.1, 12.5); wer es sieht: Frage 23. |
| 22 | **Musik: „Reinhören“ ab dem ersten Lied** und Weiterspielen über das Album (Vorschlag), oder nur ein Lied ohne Weiterspielen? | Über das Album weiterspielen, wie bei Hörspielen. **Beantwortet (Runde 8): Ja, und über eine Playlist**, sobald Stufe C da ist (Abschnitt 13). |
| 23 | **Wer sieht „Mein Reinhören“?** Drei Antworten stoßen hier zusammen: Hördaten der **Boxen** sehen alle (Nr. 8, die Kinder haben kein Konto), die **Hörstelle** sieht nur man selbst (Nr. 16), und Reinhören ist jetzt dem **HA-Benutzer** zugeordnet (Nr. 21). Reinhör-Daten sind Daten über **Erwachsene**: wer hat wann was angehört. (12.5) | **Jeder sieht nur die eigenen, auch Administratoren** (wie Nr. 16). Die Boxen-Daten bleiben für alle sichtbar (Nr. 8). Jeder darf **seine eigenen** Reinhör-Daten löschen; „Alle Hördaten löschen“ in „Technik“ betrifft nur die Boxen. Alternative: alle sehen alle (einfacher zu bauen, aber Verena sähe, was Tobias hört, und jedes Gäste-Konto auch). Nebenfrage: Soll die Erfassung schon in Stufe A beginnen (kleiner Zusatz in A4d, dann gibt es von Anfang an Verlauf), oder erst mit Stufe B? Empfehlung: erst mit Stufe B. |
| 24 | **Wo lebt ein einzelnes Lied oder eine einzelne Folge?** Heute ist alles Serie → Folgen. (A) Eigene **Serie mit genau einer Folge** und dem Kennzeichen `einzeln` (eigenes Cover und Titel, in der Liste „Lied · einzeln · 1:06“), oder (B) eine **Sammel-Serie** je Art („Einzelne Lieder“ mit 300 Liedern). (11.3.1) | **A.** Die Box ändert sich nicht; ein Lied hat sein eigenes Cover, einen eigenen Tobie und lässt sich einzeln benennen und löschen. Preis: 300 Einträge mehr in der Bibliothek (Gegenmittel: „Was zeigen“ im Filterblatt, Arten-Zeile) und 300 kleine Ordner auf dem NAS. Der Tobie zeigt auf die **Folge** (nicht die Serie), damit er bei späteren Änderungen nur sein Lied spielt. |
| 25 | **NAS-Eingang: Was passiert mit Dateien, die einfach in den Ordner gelegt werden?** Heute werden sie automatisch einsortiert. (1) Weiter **automatisch**, bei „bitte ansehen“ gibt es **„Anders einsortieren …“** mit derselben Wahl wie beim Hochladen (die Folgen werden zurück in den Eingang geholt und neu einsortiert, solange nichts daran geändert wurde). (2) Nicht Sichere Fälle **bleiben im Eingang liegen und fragen** zuerst („Was ist das?“), erst nach der Antwort wird einsortiert. (7.3 Punkt 10) | **1.** Wer Dateien in den Ordner legt, will nichts beantworten müssen; die meisten Fälle sind eindeutig. Der Rückweg Medien → Eingang ist in Vertrag W noch nicht vorgesehen und wird in A3d zuerst geprüft; ist er zu teuer, wird es **2** (kein Rückweg nötig, aber es erscheint nichts, bis jemand antwortet) oder nur „In den Papierkorb und neu hochladen“. |
| 26 | **Hörkopien: Ort, Qualität, Platz.** Für Formate, die nicht jeder Browser spielt, legt HA **einmal** eine Kopie an: AAC/M4A, 96 kbit/s, auf dem **NAS** in einem Ordner `hoerkopien/` **neben** `medien/` (nicht auf den Boxen, nicht in HAs Konfigurationsordner). Auch FLAC und WAV bekommen eine Kopie (sie sind groß). Bedarf: 43 MB je Stunde Audio; meist **wenige GB**, im schlechtesten Fall (alles in OGG/FLAC/WAV, 1 600 Stunden) etwa **70 GB**. (11.4.7) | **Ja so.** Der Ort lässt die Boxen und den Sync völlig in Ruhe. Tobias nennt bitte den freien Platz auf dem NAS; `kein_speicher` stoppt die Erzeugung ohne Schaden. Wer FLAC und WAV lieber ohne Kopie will (nur Hinweis „Auf der Box spielt es trotzdem“), spart Platz und verliert das Reinhören für diese Dateien auf Geräten ohne Unterstützung. |

## 17. Was der Prototyp v4 zeigt und was nicht

`prototyp.html` ist eine **Vorschau**, kein Code für den Bau, und schickt nichts an Home Assistant. Er zeigt (alles im Script erzeugt, erfundene Daten): **64 Einträge** (20 Hörspiele, 20 Hörbücher, 12 Musik-Alben, 8 Geschichten und **4 Einzeltitel**; darunter ein Album mit 20 Liedern und das Hörbuch „Mia und das Meer“ mit **12 Kapiteln**), rund **576 Folgen und Lieder**, alle mit einer Dauer.

**Neu in v4:**
* **Hochladen in Schritten:** „Dateien wählen“ öffnet das Blatt **„Was lädst du hoch?“** mit den **fünf Karten** (Playlist mit der Marke „Stufe C – Idee“, nur in der Ansicht „A, dazu B und C“, antippbar nur mit Meldung). Jede Karte führt zur **Vorschau in Sätzen** („3 Dateien → neues Hörbuch „Kapitän Knopf“, Kapitel 1–3.“, „3 Dateien → 3 neue Folgen in „Lange Serie“ (Folge 13–15).“, „1 Datei → 1 einzelnes Lied: „Der Mond und der Fuchs“.“, „… ich sortiere nach den Angaben in den Dateien ein. Meine Vermutung: …“) mit „Abbrechen“, „Ändern“ und „Hochladen“; der Satz ändert sich beim Tippen und beim Wechsel der Art. Für b) öffnet sich die Auswahl mit Suche und Covern (nur Sammlungen). Danach **läuft der Fortschritt wie bisher** und **es entsteht wirklich ein Eintrag** (neues Hörbuch, neue Folgen in „Lange Serie“, ein Einzeltitel), den man in der Bibliothek findet. Im Aufklappfeld „i“ wählt man, welche **Dateien** man „gewählt“ hat (3 mit Tags, 4 Lieder, 1 Datei, 2 ohne Tags, 1 mit Kopierschutz), damit alle Sätze zu sehen sind. Ein **NAS-Eintrag** „bitte ansehen“ („Ordner „Sternenmühle“ (6 Dateien)“, „vom NAS“) hat den Knopf „**Anders einsortieren …**“: dasselbe Blatt mit dem Titel „Was ist das?“ und dem Knopf „Neu einsortieren“ (Knopf „Neuer Ordner im NAS-Eingang (Demo)“ legt einen weiteren an).
* **Einzeltitel:** in der Bibliothek „Lied · einzeln · 1:06“ (nicht „1 Folge“), eigene Seite ohne Folgenliste, Tobie-Blatt „Tobie für dieses Lied“, im Filterblatt die Gruppe „Was zeigen“ (Alles · Nur Hörspiele, Bücher, Alben · Nur Einzeltitel), in der Suche nur unter „Folgen und Lieder“, in der Zielwahl nicht unter „Ganzes Hörspiel, Buch, Album“. Ein Einzeltitel („Das Lied vom Mond“) zeigt den Zustand **„Hörprobe wird vorbereitet“**.
* **Kapitel:** Das Hörbuch zeigt auf der Serienseite den Abschnitt „Kapitel“ (12 Zeilen, aktuelles markiert, Häkchen bei gehörten), im Player die Zeile „Kapitel 8: Das Echo (8 von 12)“ und den Knopf „Kapitel“ mit dem Blatt der Kapitel. **Tipp springt mit dem erzeugten Ton** an die Stelle; die Zeitleiste über das ganze Buch bleibt.
* **„Gehört“:** Umschalter **Boxen | Mein Reinhören** (Stufe B – Vorschau). „Mein Reinhören“ mit Hinweis „Nur du siehst das.“, Rangliste „Was habe ich mir angehört?“ mit Aufteilung nach Folgen, Hörzeit pro Tag, Karte „Meine Reinhör-Daten“ mit Löschknopf (Vorschau).
* „Technik“: Zeile „Hörkopien“ und Knopf „Hörkopien neu erzeugen“.
Erhalten aus v3: Bibliothek wie eine Hörbuch-App, Suche, Serienseite, Player (Leiste, Vollansicht, ±30 s, Tempo, Weiterspielen, Weiterhören über Neuladen mit `localStorage`), „Gehört“ mit Rangliste je Box, Rollen Administrator/Verena, Name-Abfrage, Cover per Foto, Zielwahl, „Das ist richtig / stimmt nicht“, Papierkorb, Abends, Technik mit eingebetteter alter Seite, Stufe-C-Idee (Playlist), Zustände (lädt, leer, Fehler, Verbindung weg).

**Prüfung** mit Playwright (Chromium) bei 390 × 844 und 1280 × 900 px, Hell und Dunkel (dazu das Theme mit hellem Primärton und die Rolle Verena ohne Administratorrechte), **170 Ansichten**: Start, Bibliothek, Suche (leer und mit Treffern), Serienseiten (Hörspiel, Hörbuch mit Kapiteln, Einzeltitel, Einzeltitel mit „Hörprobe wird vorbereitet“), Tobies, Abends, Gehört (Boxen und Mein Reinhören, je mit Aufteilung nach Folgen), Hinzufügen, Technik, Blatt „Sortieren und Filter“ (auch mit „Nur Einzeltitel“), **Hochladen: Blatt „Was lädst du hoch?“, Vorschau für neu, zu vorhandenem, einzeln und „Weiß nicht“, Fortschritt, fertig, „bitte ansehen“, Kopierschutz, NAS-Wahl und -Vorschau**, Serienseite mit Leiste, Player mit Kapiteln, Kapitelblatt:
**kein waagerechtes Scrollen, alle Knöpfe, Links, Auswahlfelder und Schieberegler mindestens 44 px, Kontrast mindestens 4,5:1 (3:1 große Schrift): 0 Treffer** (die Prüfung fand im ersten Lauf den Link „Öffnen“ in der fertigen Upload-Zeile mit 48 × 19 px; er ist jetzt ein Knopf; die Prüfung selbst wurde in v3 gegen absichtlich schlechte Elemente gegengeprüft).
**Erste Cover der Bibliothek am Handy:** unteres Ende bei **35 % der Bildschirmhöhe** (Vorgabe: in den ersten etwa 40 %).
**Ablauf-Skripte:** (1) Hochladen: alle fünf Wege (a mit Art-Wechsel, Namensänderung und „Ändern“, b mit Auswahl und Suche, c, d nur Meldung, e), die Sätze wörtlich, Fortschritt bis „fertig“, der neue Eintrag in der Bibliothek, Einzeltitel als „Lied · einzeln“ und nicht als „1 Folge“, Kopierschutz-Karte, NAS „Anders einsortieren“ bis „Neu einsortiert“: **83 Prüfungen ohne Fehler**. (2) Kapitel und „Gehört“: 12 Kapitel, ein markiertes aus der gemerkten Stelle, Tipp auf Kapitel 8 → Ton springt (171 s, Start 169 s), Zeile im Player, Sprung aus dem Kapitelblatt, nach Neuladen bleibt das Kapitel markiert, Filter „Nur Einzeltitel“, Hörprobe-Meldung, Umschalter und Diagramm in „Gehört“: **jeweils beide Breiten, alle Prüfungen ohne Fehler**.
Der **Durchgang Korrekturen** behob: die fünf Wahlkarten waren zu hoch (die fünfte lag unter dem Rand; Texte gekürzt, jetzt passen alle fünf auf 390 × 844), „Art: … (aus den Tags vorgeschlagen)“ erschien auch nach eigener Wahl (jetzt nur bei „Weiß nicht“), der Link „Öffnen“ war zu klein, der Titel im Player wiederholte bei Hörbüchern den Namen („Mia und das Meer“ zweimal), das Blatt der Kapitel sprang zu weit, und ein **Fehler schon aus v3**: das Säulendiagramm „Hörzeit pro Tag“ in „Gehört“ zeichnete nichts (falsche Variable für die Tage); es ist behoben. Die Bilder bei 390 px (Wahl, Vorschau, Einzeltitel, Kapitel, Player, Kapitelblatt, Gehört, Filter) habe ich selbst durchgesehen.
**Nicht belegt:** echte HA-Farben und -Themes, die Companion-App (Ton im Hintergrund, Sperrbildschirm), echte Audiodateien über die Audio-Ansicht und signierte Pfade (A4c, A8b), echte Hörkopien und Kapitel aus Tobias' Dateien (A3b, A3c), Safari und iPhone (Autoplay-Regeln, Formate), Springen auf dem NAS-Pfad, Tastatur auf iOS, echte Fotos vom Handy, das Lesen der Tags im Browser beim Hochladen (A11a), der Rückweg Medien → Eingang bei „Anders einsortieren“ (A3d).

## 18. Befunde des Goldfischs und ihre Behandlung

**Stand: 26 Befunde. Eingearbeitet 24 (davon U1 schon behoben), teilweise abgelehnt 2 (U3, U23), vollständig abgelehnt 0.**

| U | Behandlung |
|---|---|
| U1 | **Schon behoben** (Commit d41e319); Test siehe 10.1 und A1 |
| U2 | eingearbeitet (10.3, 10.2): `remove` nur mit `erwartet_ziel`, `set` nur für bekannte Kennungen, Mengen, 10 frühere Stände (Frage 3) |
| U3 | **teilweise abgelehnt, weil** Tobias in Runde 6 bewusst „alle HA-Benutzer“ entschied; die Benutzerliste in den Optionen wird nicht gebaut (10.1 Punkt 6). Eingearbeitet: Mengen- und Upload-Obergrenze (10.3) |
| U4 | eingearbeitet (7.1, 5.7): Name in der Fertig-Karte, „zuletzt angelernt“ oben, Suche, Auflegen-zum-Finden wenn die Box die Kennung meldet |
| U5 | eingearbeitet (5.5): Marke „schon gesucht“, einmal im Hintergrund, Zeitgrenze, kein Dauer-Scan, `ffmpeg` fehlt, `medien/pruefen` höchstens alle 10 Minuten |
| U6 | eingearbeitet (5.9, 15): alte Seite einbetten, 121 Tests unverändert |
| U7 | eingearbeitet (10.1, A17): `require_admin` bleibt `True` bis nach der Abnahme |
| U8 | eingearbeitet (5.5, 11.3): `cover*.jpg` nicht auf die Boxen, reservierte Namen, Zusammenführen, Papierkorb, Quelle `cover.jpg`/`folder.jpg`, „Cover neu suchen“, Tests; Frage 5 |
| U9 | eingearbeitet (7.1, A15): ehrlich zählen, Automation-Vorlage, Satz über den Kacheln, nur die oberste Karte bedienbar, Rückgängig bis „OK“ |
| U10 | eingearbeitet (10.3, 7.3): `eingang/sortieren` ohne `sofort` für Alltag |
| U11 | eingearbeitet (5.3, 7.3): „Das ist richtig / Das stimmt nicht“, verschieben und Papierkorb für Alltag |
| U12 | eingearbeitet (5.6, 7.3): Ordner-Knopf nur mit Maus, Hörbuch-Frage nur ohne Tags, Zielwahl, Bildschirm anlassen und Unterbrechung, 413 |
| U13 | eingearbeitet (7.3): 24 Stunden, „auf diesem Gerät“, `quelle` fest im Vertrag |
| U14 | eingearbeitet (4): Flächen aus HA-Variablen, eigene Text- und Statusfarben, Laufzeit-Kontrast, `--primary-ink`, drei Themes im Test (Prototyp: Theme mit hellem Primärton) |
| U15 | eingearbeitet (3.1): `narrow`, sticky statt `fixed`, Tastatur, Companion-App früh prüfen (A15b) |
| U16 | eingearbeitet (5.8, 5.7): Schnellwahl, „Ausblenden“ nach Technik, Kachel „Gute Nacht“ auch für belegte Tobies |
| U17 | eingearbeitet (10.3): Zeitzone ignorieren statt `unauthorized`, `erwartet_revision` |
| U18 | eingearbeitet (11.1): Änderungseintrag mit Datum, 2.1 ersetzen, W-19 streichen, Fähigkeiten reduziert, `rechte` entfällt |
| U19 | eingearbeitet (10.1): Aktionen, JavaScript ohne Anmeldung, Seitenleiste nur Komfort |
| U20 | eingearbeitet (6.1, A5): Fehlertexte vollständig aus dem Vertrag abgeleitet |
| U21 | eingearbeitet (3.3, 5.1.1, 11.2 V-3): Name unverändert, „ohne das Wort Box“, Folgenname über `serie/get`, ein Textfeld in den Optionen |
| U22 | eingearbeitet (3.1, 3.3, 5.9): „Technik“, kein Personenname, Begriffe „Das ist richtig / Das stimmt nicht“, „Zuletzt hinzugefügt“ statt „Gerade eben“ |
| U23 | **teilweise abgelehnt:** (a) Wochenplan-Grafik, (b) Reihenfolge nur Admin, (d) Zusatzsatz, (e) „Name ändern“ im Blatt **eingearbeitet**; (c) der Reiter bleibt, aber als „Bibliothek“ (bei 500+ Einträgen unverzichtbar), die Startseite zeigt nur noch „Neu in der Bibliothek“ |
| U24 | eingearbeitet (14, 4): `<dialog>`, `getRootNode()`, Marke unten links, Fokus auf Fertig-Karte, Reiterzahl als Text |
| U25 | eingearbeitet (15): U8 geteilt (A11a/b), Rechte/Namen/Cover parallel, Texte-Paket vorweg, Playwright Pflicht (A14), Vertrag mit A1 |
| U26 | eingearbeitet (10.2): `konfig/export_lesen` und `ereignisse` nur Admin, „Lesen bleibt für alle“ bewusst |
