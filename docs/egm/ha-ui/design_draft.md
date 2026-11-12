# HA-Oberfläche einfacher und schöner: Design-Entwurf Rev. 2 (EGM Schritt 2)

Stand 12.11. · Rev. 2 (nach Goldfisch-Review `review_goldfisch.md` und Antworten Runde 4 bis 6 in `brainstorm.md`).
Grundlage: `concepts_brief.md` (mit Abschnitt 6: Stufen A, B, C), `brainstorm.md`, `ist.md`, Vertrag W (`docs/protocol/ha-websocket-v1.md`),
`docs/data-model.md`, `docs/protocol/mqtt-v1.md`. Klickbarer Prototyp v2: `prototyp.html` (erfundene Beispieldaten; die Vorschau-Leiste oben schaltet
Rolle, Aussehen, Zustand und Stufen um).
Status: **Entwurf Rev. 2, wartet auf Resolve mit Tobias** (Abschnitt 16). Gebaut wird **Stufe A**. B und C sind geplant, haben ihren Platz in der Oberfläche
und ihre Vertragsentwürfe (Abschnitte 12, 13), werden aber erst nach Freigabe gebaut.

## 1. Kurz gesagt

* Eine Seite „Tobi Box“ für **alle** HA-Benutzer. Reiter: **Start · Bibliothek · Tobies · Abends** (Stufe B: dazu **Gehört**). **Technik** (früher „Für Tobias“) ist
  kein Reiter, sondern ein Knopf oben rechts, nur für Administratoren.
* **Große Bibliothek (neu in Rev. 2):** etwa 200 Hörbücher und 300 Lieder gehen ohne Blättern. Bereiche nach **Art** (Hörspiele, Hörbücher, Musik, Geschichten),
  Kacheln **oder** „Alle Folgen“, **Suche über alles**, **Filter**, **Sortieren**, Listen mit Blättern in Päckchen von 60.
* **Ein Tobie für ein einzelnes Lied oder eine einzelne Folge** ist ein Knopf „Tobie“ in jeder Zeile.
* **Name beim Zuordnen gleich abfragen** (überspringbar). **Eigenes Cover per Foto vom Handy.**
* **Rechte (Runde 6):** Alltag = alle HA-Benutzer, jetzt auch **in den Papierkorb legen**. Leeren, Eingang entfernen, Zusammenführen bleiben bei Administratoren.
  Dazu Schutz gegen Fehlbedienung (Abschnitt 10).
* **Umbau ohne Bruch:** Die bisherige Technik-Seite bleibt als Komponente erhalten und wird in „Technik“ **eingebettet** (Abschnitt 5.9). Ihre 121 Tests laufen unverändert weiter.
  Die Seite wird erst nach der Abnahme für alle geöffnet.
* Alle 26 Befunde des Goldfischs sind beantwortet (Abschnitt 18).

### 1.1 Wichtigste Änderungen gegenüber Rev. 1

| Thema | Rev. 1 | Rev. 2 |
|---|---|---|
| Umfang | ca. 20 Hörspiele | 500+ Einträge: Arten, Suche, Filter, Sortieren, Alle Folgen, Blättern |
| Reiter | Start, Hörspiele, Tobies, Abends, Für Tobias | Start, **Bibliothek**, Tobies, Abends (B: **Gehört**); **Technik** als Knopf oben |
| Einzelne Folge/Lied als Ziel | nur in „Für Tobias“ | Knopf „Tobie“ in jeder Zeile, für alle |
| Name des Tobies | später über „Namen geben“ | wird in der Fertig-Karte gleich abgefragt, überspringbar |
| Cover | automatisch aus Tags, eigenes Foto später | automatisch (mit „schon versucht“-Marke) **und** eigenes Foto vom Handy |
| Papierkorb | nur Administrator | Alltag darf hineinlegen, nur Leeren bleibt Admin |
| Alte Technik-Seite | wird in Karten umgebaut | wird eingebettet, nicht umgebaut |
| Wochenplan-Grafik, Reihenfolge ändern | Alltag | Grafik entfällt in Stufe A, Reihenfolge nur Admin |
| Gute Nacht | Stepper, nur über „Neuer Tobie“ | Schnellwahl 15 bis 90 Minuten; Kachel „Gute Nacht“ auch für bereits belegte Tobies |

## 2. Stufen im Überblick

| Stufe | Inhalt | Stand |
|---|---|---|
| **A** | Alles aus Abschnitt 1: Arten, Suche, Filter, Sortieren, Alle Folgen, Tobie auf Lied/Folge, Name, Cover, Rechte, Technik-Einbettung | **wird gebaut** (Abschnitt 15) |
| **B** | Reiter „Gehört“ (Hörzeit pro Tag und Box, Lieblings-Hörspiele, Tageszeiten), „Zuletzt gehört“, „Meist gehört“, Favoriten (Stern); in „Technik“ Akku-Verlauf, Ladezeiten, Laufzeit, Syncs, Fehler. Daten unbegrenzt | **geplant**, Vertragsentwurf in Abschnitt 12, Bau nach Freigabe |
| **C** | Eigene Playlists aus beliebigen Folgen und Liedern als Tobie-Ziel | **Idee**, Skizze in Abschnitt 13 |

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
* **Technik:** Knopf „Technik“ (Werkzeug-Symbol, 44 px hoch) oben rechts in der Kopfzeile, **nur für Administratoren**. Der Name trägt keinen Personennamen (U22a).
  Zeigt den Knopf nicht, wer kein Administrator ist; ruft jemand `#technik` trotzdem auf, steht dort: „Dieser Bereich ist nur für Administratoren. Wenn du etwas Technisches brauchst, frag Tobias.“

### 3.2 Unterseiten, Adressen

Unterseiten: **Eintrag** (Hörspiel, Hörbuch, Album, Geschichten), **Hinzufügen**, **Tobie anlernen**. Oben links „‹ Bibliothek“ bzw. „‹ Start“; Browser-Zurück geht denselben Weg.
Adressen (nach `#`, nur einfache Namen): `#start`, `#bibliothek`, `#serie-<id>`, `#hinzufuegen`, `#anlernen`, `#tobies`, `#abends`, `#gehoert` (B), `#technik`.
Nicht `settings`, `sidebar` und Ähnliches. Der Menüknopf von HA (`ha-menu-button`) steht in der Kopfzeile, wenn `narrow` gesetzt ist.

### 3.3 Sprache (U22c, U21)

Es heißt **Tobie** (Mehrzahl Tobies), **Papierkorb**, **Folge**. Weil die Bibliothek mehr als Hörspiele enthält, gibt es kein einzelnes Oberwort mehr. Die Seite sagt, was es ist:

| Art (`art`) | Bereich | Einzelnes Stück | Kachel zeigt |
|---|---|---|---|
| `hoerspiel` | Hörspiele | Folge | „Hörspiel · 12 Folgen“ |
| `hoerbuch` | Hörbücher | Hörbuch (ein Buch = eine Folge mit Kapiteln) | „Hörbuch · 14 Kapitel“ |
| `musik` | Musik | Lied | „Musik · 20 Lieder“ |
| `geschichte` | Geschichten | Geschichte | „12 Geschichten“ |

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
6. **Suchfeld** „Hörspiel, Lied, Folge oder Tobie suchen“: Absenden öffnet die Bibliothek mit dem Suchwort.
7. „**Neu in der Bibliothek**“: die sechs zuletzt hinzugefügten Einträge als Kacheln, darunter „Ganze Bibliothek ansehen (60)“. (Die Startseite zeigt nicht mehr das ganze Raster, U23c.)
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

### 5.2 Bibliothek (neu, Stufe A)

Die Seite für 200 Hörbücher, 300 Lieder und mehr. Aufbau von oben nach unten (Prototyp: Reiter „Bibliothek“):

1. **Kopf:** Überschrift „Bibliothek“, Knopf „+ Hinzufügen“.
2. **Suchfeld** „Suchen: Hörspiel, Lied, Folge, Tobie“ (Suche über alles, siehe unten).
3. **Art-Leiste** (Knöpfe mit Anzahl, umbrechend): **Alles 60 · Hörspiele 20 · Hörbücher 20 · Musik 12 · Geschichten 8**. Eine Auswahl gilt auch für „Alle Folgen“.
4. **Ansicht:** Umschalter **Kacheln | Alle Folgen**.
   * *Kacheln:* Cover-Kachel je Hörspiel, Buch, Album (Name, Art, Anzahl). Tippen öffnet den Eintrag (5.3).
   * *Alle Folgen:* **eine Liste über alle Einträge**, auch einzelne Lieder: kleines Cover, Titel, „Eintrag · Folge 4“ bzw. „· Lied“, Zusatz „hat einen Tobie“ und rechts der Knopf **„Tobie“** (5.4).
5. **Filter** (Schalter, mehrere gleichzeitig): **Ohne Tobie** · **Neu** (in den letzten 14 Tagen hinzugefügt) · **Bitte ansehen**. Stufe B: **★ Favoriten**.
   „Ohne Tobie“ heißt bei einem Eintrag: kein Tobie zeigt auf ihn oder eine seiner Folgen; bei einer Folge in „Alle Folgen“: weder auf die Folge noch auf den ganzen Eintrag zeigt ein Tobie.
6. **Sortieren** (Auswahlfeld): **A bis Z** (Vorgabe) · **Zuletzt hinzugefügt**. Stufe B ergänzt **Zuletzt gehört** und **Meist gehört** (im Prototyp ausgegraut mit „Stufe B“).
7. **Zählzeile** (`aria-live`): „60 Einträge“ bzw. „572 Folgen und Lieder · 60 gezeigt“.
8. **Liste/Raster** mit **Blättern**: 60 Stück, darunter „Mehr zeigen (60 weitere)“; der Fokus springt auf den ersten neuen Eintrag.

**Suche über alles.** Ab 2 Zeichen (Verzögerung 250 ms, Umlaute und Groß/Klein egal, „Gefunden: 1 Sammlungen, 12 Folgen und Lieder, 1 Tobies“) zeigt die Seite drei Gruppen:
„Hörspiele, Bücher, Alben“ (Kacheln, höchstens 12), „Folgen und Lieder“ (Zeilen mit Knopf „Tobie“, höchstens 10, Treffer hervorgehoben) und „Tobies“ (nach Tobie-Name, Tippen öffnet das Tobie-Blatt).
Mehr Treffer: „… und 7 weitere. Oben ‚Alle Folgen‘ wählen.“ Art und Filter gelten auch für die Suche. Kein Treffer: „Nichts gefunden zu „xyz“. Nimm einen Filter weg oder wähle „Alles“.“
Leer: „Noch nichts da. Tippe auf „Hinzufügen“.“

**Leistung (500+ Einträge).** (1) Das Backend blättert (`limit`/`offset` gibt es im Vertrag W für Listen schon; V-2), die Seite lädt 60 und bei „Mehr zeigen“ die nächsten 60. Auch das Suchen, Filtern und Sortieren
macht das Backend (Index im Speicher der Integration, Ziel unter 200 ms bei 600 Einträgen und 2 000 Folgen), die Seite filtert nicht selbst. (2) Kacheln und Zeilen tragen `content-visibility: auto`, sodass der Browser Unsichtbares nicht zeichnet;
eine eigene virtuelle Liste ist **nicht** nötig (bis 1 000 Zeilen im Dokument geprüft; erst darüber würde man sie nachrüsten). (3) Cover laden erst, wenn die Kachel sichtbar wird (`IntersectionObserver`),
mit der kleinen Größe 192 px (ca. 15 KiB, V-1) statt 512 px, als `blob:` zwischengespeichert nach `cover_stand`. Bei 60 Kacheln sind das etwa 1 MB statt 8 MB.
(4) Optional: Sprungleiste „A B C …“ bei A bis Z.

### 5.3 Eintrag (Hörspiel, Hörbuch, Album, Geschichten)

* „‹ Bibliothek“. Kopfkarte: großes Cover, Name, „Hörspiel · 12 Folgen · 3 Tobies“, Knöpfe **„Name ändern“**, **„Cover ändern“** (5.5), **„Art ändern“** (Blatt „Was ist das?“ mit den vier Arten; Hinweis: „Die Art wurde aus den Tags vorgeschlagen.“).
* Falls zu prüfen: gelbe Karte „**Bitte kurz ansehen.** <Grund, Abschnitt 7.3>“ mit zwei Wegen **„Das ist richtig“** und **„Das stimmt nicht“** (U11). „Das stimmt nicht“ öffnet ein Blatt: „**Anderem zuordnen …**“ (`folge/verschieben` bzw. neu einsortieren, mit Zielwahl) oder, abgesetzt, „**In den Papierkorb …**“. Beides ist jetzt Alltag (Abschnitt 10); es gibt keine Sackgasse mehr bei „Frag Tobias“.
* Karte „**Tobie dafür anlernen**“ (für den ganzen Eintrag): „Wähle die Box. Danach legst du den Tobie auf, der „Lange Serie“ spielen soll.“ Je Box ein Knopf „Auf Mond“, „Auf Stern“; ist eine Box aus, ist ihr Knopf grau mit „Stern ist aus. Schalte sie ein, dann geht es.“
* Abschnitt „**Folgen**“ (bei Alben „Lieder“, bei Hörbüchern „Hörbuch“): Zeile = Nummer, Titel, Größe, „1 Tobie“, Knopf **„Tobie“** (5.4) und Knopf **„⋯“** (Blatt: „Name ändern“, „In anderes verschieben …“, abgesetzt „Papierkorb …“ mit Rückfrage).
  Das Umbenennen ist damit aus der Zeile genommen (U23e). Ab 20 Folgen ein Suchfeld „Hier suchen“, ab 20 Zeilen „Mehr zeigen“.
  Nur Administratoren: Knopf „Reihenfolge ändern“ (▲/▼ je Zeile, kein Ziehen; U23b: für Folgen aus Tags selten nötig).
* Karte „**Aufräumen**“ ganz unten, abgesetzt: „**In den Papierkorb …**“ (Alltag; Rückfrage nennt Tobies, die dann nichts mehr spielen, mit Namen: „Roter Tobie, Tobie ohne Namen spielen dann nichts mehr. Tobias kann es aus dem Papierkorb zurückholen.“);
  nur Administratoren: „Mit anderem zusammenführen …“.

### 5.4 Tobie für ein einzelnes Lied oder eine einzelne Folge (neu für alle)

Das Datenmodell kennt das schon (`ziel.typ="folge"`, `data-model.md` 2, `lernmodus/start` mit Ziel `folge`); neu ist, dass es **sichtbar einfach** wird:

* Überall, wo eine Folge oder ein Lied in einer Zeile steht (Eintrag, „Alle Folgen“, Suchtreffer), gibt es den Knopf **„Tobie“**.
* Er öffnet das Blatt „**Tobie für dieses Lied**“ (bzw. „… diese Folge“, „… dieses Hörbuch“, „… diese Geschichte“): „Der Tobie spielt dann nur „Backe, backe Kuchen“ aus „Kinderlieder zum Mitsingen“.“
  Zwei Wege: **„Neuen Tobie anlernen: Auf Mond / Auf Stern“** (Lernmodus mit Ziel Folge, Ablauf 7.2) und **„Tobie wählen …“** (einen bereits belegten Tobie auf dieses Lied umstellen; Tippen = gespeichert, „Fertig: Löwe spielt jetzt „…““).
  Gibt es schon einen Tobie dafür, steht oben „Schon angelernt: Gelber Hase.“ Stufe C: darunter der ausgegraute Knopf „Zu einer Playlist hinzufügen“ (Marke „Stufe C – Idee“).
* In der Karte „Neuer Tobie“ (Start) und im Blatt „Tobie umstellen“ gibt es eine **Zielwahl** mit Suche und Art-Knöpfen und dem Umschalter „**Ganzes Hörspiel, Buch, Album | Einzelne Folge oder Lied**“; so findet man auch ein Lied unter 572 Folgen (Suche, ein Tap).
* Tobies mit Ziel Folge heißen in der Tobies-Liste „spielt „Backe, backe Kuchen“ aus „Kinderlieder zum Mitsingen“ (ein Lied)“.

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

Siehe Ablauf 7.3. Aufbau: „‹ Start“, Überschrift „Hinzufügen“; große Knöpfe „**Dateien wählen**“ (Handy und Computer) und „**Ordner vom Computer wählen**“ (U12a: **nur** bei `matchMedia('(pointer: fine)')`, am Handy nicht);
am Computer zusätzlich eine Fläche „Auf dem Computer kannst du Dateien oder einen ganzen Ordner auch hierher ziehen.“ Nebentext: „Hörspiele, Hörbücher, Musik, Geschichten. Erlaubt: MP3, M4A, M4B, AAC, FLAC, OGG, Opus, WAV.
Bis 500 MB je Datei. Kopiergeschützte Dateien (zum Beispiel von Audible) gehen nicht. **Lass den Bildschirm an, bis alles fertig ist.**“ (U12d; die Zahl aus `hello.grenzen.upload_max_bytes`).
Hinweiskarte: „Du kannst Dateien auch am Computer in den Eingang-Ordner auf dem NAS kopieren. Sie erscheinen hier von selbst. Frag Tobias nach dem Ordner.“ Darunter „**Zuletzt hinzugefügt**“ (Einträge der **letzten 24 Stunden**, U13).

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
* **Stufe B:** Karte „Akku-Verlauf“ je Box mit Liniendiagramm (Prozent über 3 Tage, Ladezeiten als Bänder), Laufzeit je Ladung, Ladezeiten, Syncs, Fehler als Liste, Knöpfe „Hördaten als Tabelle sichern“ (CSV) und „Alle Hördaten löschen …“ (Rückfrage). Abschnitt 12.
* Die Warnleisten zur Liste (`leer_neu`, `export_neuer`, Box mit neuerem Stand) erscheinen für Administratoren oben auf allen Seiten wie heute; Nicht-Administratoren sehen nur den Hinweis aus Abschnitt 6.

### 5.10 Gehört (Stufe B, Vorschau im Prototyp)

Eigener Reiter für alle, **nur wenn die Fähigkeit `gehoert` gemeldet wird**. Oben ein Hinweis „Stufe B – Vorschau“ (nur im Prototyp). Aufbau:

* **Auswahl:** Box (Beide Boxen · Mond · Stern; die Namen sind die der Kinder, die Tobias in den Optionen einträgt) und Zeitraum (7 Tage · 14 Tage; später 30 Tage und Jahr).
* **Hörzeit pro Tag:** Säulendiagramm (SVG), je Tag eine Säule je Box, Achse „Minuten“ 0 bis 90 mit Linien bei 30, 60, 90, Zahl über jeder Säule (bei 7 Tagen), Tage mit Wochentag und Datum, Legende „Mond / Stern“.
  Darunter „Zahlen als Tabelle“ (für Screenreader und zum Nachlesen). Satz darüber: „In den letzten 7 Tagen: 9 Std. 53 Min. (Mond 5 Std. 58 Min., Stern 3 Std. 55 Min.).“
* **Lieblings-Hörspiele:** Balkendiagramm der fünf meistgehörten Einträge nach Hörzeit (je Box oder zusammen), Name links, Minuten rechts.
* **Tageszeiten:** 24 Säulen (Stunde 0 bis 23), Achse Minuten; Satz „am meisten um 19 Uhr“.
* **Zuletzt gehört**, **Meist gehört**, **Favoriten:** Kachel-Reihen (waagerecht scrollbar). Der **Stern** (Favorit) steht in jedem Eintrag und in jeder Folgenzeile; gilt für alle in der Familie.
* Farben der Diagramme sind Token (`--chart1`, `--chart2`, `--grid`), in Hell und Dunkel geprüft (3 zu 1 gegen die Karte). Jedes Diagramm hat `role="img"` mit Beschreibung und eine Tabelle.

### 5.11 Playlist (Stufe C, Idee)

Nur ein Platz: Im Reiter „Tobies“ eine Karte „Playlist „Autofahrt““ mit nummerierten Einträgen (Lied oder Folge, ▲/▼), Knöpfen „Lied oder Folge hinzufügen“ und „Tobie für die Playlist anlernen“; im Blatt „Tobie für dieses Lied“ der Knopf „Zu einer Playlist hinzufügen“.
Im Prototyp ausgegraut, mit der Marke „Stufe C – Idee“. Datenmodell und Auswirkungen: Abschnitt 13.

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

### 7.2 (b) Eintrag, Lied oder Folge wählen → „Tobie anlernen“ → auflegen: **2 Taps**

1. **Tap 1:** auf die Kachel (Bibliothek) **oder** bei einem Lied/einer Folge auf den Knopf „Tobie“ (5.4; dort ist „Auf Mond“ gleich Tap 2).
2. **Tap 2:** auf „Auf Mond“ in der Karte „Tobie dafür anlernen“ bzw. im Blatt (`lernmodus/start` mit Ziel `serie` oder `folge`; der Knopf je Box ersetzt die Boxauswahl, darum kein dritter Tap).
3. Die Seite wechselt zu „Tobie anlernen“ (`#anlernen`): Ring-Symbol (pulsiert, nicht bei „reduzierte Bewegung“), Überschrift „**Jetzt Tobie auf Mond legen**“,
   „Dieser Tobie soll „Lange Serie“ spielen. Ich warte noch 118 Sekunden.“ (Zähler aus `frist_bis`, wird nicht vorgelesen), Knopf „Abbrechen“ (= `lernmodus/abbrechen`).
4. *(Körperlich)* Tobie auflegen. Ereignis `lernmodus`/`zugeordnet`: grünes Häkchen, „**Erkannt!** Dieser Tobie spielt jetzt „Lange Serie“.“,
   **Name-Abfrage wie in 7.1** (Textfeld, überspringbar), Knöpfe „Noch einen Tobie anlernen“, „Fertig“ (zurück zum Eintrag). Der Name geht schon mit `lernmodus/start` (`name`), wenn Verena ihn vorher kennt; sonst setzt ihn die Seite danach mit `zuordnung/set`. Erscheint der neue Tobie auch unter „Tobies“: ja, ohne Namen.
5. Fälle:
   * Tobie hat schon ein Ziel (`rueckfrage`): Blatt „**Dieser Tobie spielt schon etwas.** Er spielt jetzt „Test-Serie“. Soll er stattdessen „Lange Serie“ spielen? Du hast dafür noch 10 Sekunden.“
     Knöpfe „Nein, so lassen“ (Vorgabe, Fokus), „Ja, ändern“ (= `lernmodus/antwort`). Zeit abgelaufen: „Das hat zu lange gedauert. Der Tobie spielt wie vorher.“ (+1 Tap).
   * Abgelaufen (`abgelaufen`): „**Kein Tobie erkannt.** Die Zeit ist abgelaufen. Lege den Tobie nach dem Start gleich auf die Box.“ „Noch einmal versuchen“ / „Zurück“.
   * Box lehnt ab (`box_lehnt_ab`, `zeit_unsicher`): „Mond kann gerade nicht lernen, weil sie die Uhrzeit nicht sicher kennt. Versuche es in ein paar Minuten noch einmal.“
   * Box aus (`box_offline`): Knopf schon vorher grau (4.3).
   * Läuft schon ein Lernvorgang: `lernmodus_laeuft`, Text in 5.1. Die Seite zeigt bei erneutem Öffnen einen offenen Vorgang weiter an (Abo `lernmodus`).

Heute: 5 bis 9 Taps (`ist.md`).

Heute: 5 bis 9 Taps.

### 7.3 (c) Hinzufügen: **2 Taps** (Zielwahl kostet im Normalfall nichts), Wartezeit ohne Tippen

1. **Tap 1:** „Hinzufügen“ (Start oder Bibliothek). **Tap 2:** „Dateien wählen“ (System-Auswahl) oder am Computer „Ordner vom Computer wählen“ bzw. Hineinziehen.
2. **Zielwahl (U12c):** Ein Blatt fragt einmal „**In welches soll es?**“ mit der Vorgabe „**Automatisch (nach den Dateien)**“ (primär, Fokus) und „In ein bestehendes wählen …“ (Zielwahl wie 5.4). Der Normalfall braucht einen Tap („Automatisch“), also insgesamt 3; wer aus einem Eintrag heraus hochlädt („Dateien in diesen Eintrag“ im Eintrag), überspringt das Blatt (`serie_id` wird gesendet).
3. **Hörbuch-Frage (U12b):** „Gehören die Dateien zu einem Hörbuch?“ wird **nur** gestellt, wenn keine Tags gelesen werden können (kein Album), mit Beispiel („Ein Hörbuch besteht aus Kapiteln: Ja. Mehrere Folgen: Nein.“); Vorgabe „Ja“, wenn alle Dateien gleich benannt und durchnummeriert sind.
   Bei Tags entscheidet das Einsortieren (Vertrag 11.3).
4. Der Upload startet sofort. Je Datei oder Ordner eine Zeile unter „**Zuletzt hinzugefügt**“:

   | Schritt | Anzeige |
   |---|---|
   | 1 | **„Wird hochgeladen … 37 %“** mit Balken (`role="progressbar"`), dreiteilige Leiste (Hochladen · Einsortieren · Fertig) |
   | 2 | **„Wird einsortiert …“** |
   | 3a | **fertig:** grüne Marke, „Lange Serie · Folge 13“, „Öffnen“; bei Musik/Hörbuch zusätzlich „Art: Musik (aus den Tags vorgeschlagen). Stimmt nicht? Im Eintrag „Art ändern“.“ |
   | 3b | **bitte kurz ansehen:** gelbe Karte mit „Ansehen“, „**Das ist richtig**“ (`einsortierung/bestaetigen`) und „**Das stimmt nicht**“ (Blatt: anderem zuordnen / in den Papierkorb, 5.3; U11) |
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

   **Gründe „geht nicht“** (Eingangs-`hinweise`, Upload-`fehler`): `kopierschutz`: „Diese Datei ist kopiergeschützt (zum Beispiel von Audible oder Apple Books). Die Box kann sie nicht abspielen. Nimm eine Datei ohne Kopierschutz.“ ·
   `nicht_lesbar`, `probedekodierung_fehlgeschlagen`: „Die Datei ist kaputt oder unvollständig. Bitte noch einmal kopieren.“ · `keine_audiodateien`: „Darin ist keine Audiodatei.“ ·
   `ffprobe_fehlt`: „Das Prüfprogramm fehlt. Bitte Tobias Bescheid sagen.“ · `verschieben_fehlgeschlagen`: „Das Ablegen hat nicht geklappt. Versuche es später noch einmal, sonst frag Tobias.“ ·
   `doppelt`: „Das gab es schon und wurde nicht noch einmal angelegt.“ Die Zeile erklärt, nicht den Code. „Entfernen“ eines blockierten Eintrags ist Admin-Sache („Technik“).

7. **Zwei Uploads gleichzeitig:** weitere Dateien warten („wartet“) und gehen nacheinander; kein 429 sichtbar. **Abbrechen** solange hochgeladen wird (`AbortController`).
8. **Wenn das Handy den Bildschirm sperrt:** Safari und Chrome frieren die Seite ein. Darum der Hinweis in 5.6 und beim Zurückkehren: Zeilen, die bei „wird hochgeladen“ stehen geblieben sind, werden „Unterbrochen. Wähle die Datei noch einmal.“
9. **Proxy-Grenze (U12e):** HTTP 413 von einem vorgeschalteten Proxy wird als `datei_zu_gross` gezeigt; „Technik“ nennt die tatsächliche Grenze.
10. **NAS-Weg:** Dateien im Eingang-Ordner erscheinen ohne Hochladeschritt direkt bei „Wird einsortiert …“.
11. **„Jetzt prüfen“** (`eingang/sortieren`) wird für Nicht-Administratoren **ohne `sofort`** gesendet (U10) und sagt: „Dateien werden erst nach 2 Minuten Ruhe einsortiert.“ `sofort` bleibt in „Technik“.

Heute: 3 bis 5 Taps plus Suchen im Reiter „Eingang“.

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
| (b) Eintrag → Tobie anlernen | 5 bis 9 | **2** (+1 bei „schon belegt“) |
| Lied/Folge → Tobie anlernen | nur Technik | **2** (Tobie, Auf Mond) |
| (c) Hinzufügen | 3 bis 5 + Suchen | **3** (Hinzufügen, Dateien, Automatisch) |
| (c2) „bitte ansehen“ bestätigen | 3 bis 7 | **1** („Das ist richtig“) |
| Fehl-Upload korrigieren | Sackgasse | **3** („Das stimmt nicht“, Papierkorb, Bestätigen) |
| (d) Gute Nacht ändern | 3 + Tippen | **3** |
| Cover ersetzen | nur NAS von Hand | **4** (Cover ändern, Foto, Zuschneiden, Speichern) |
| Etwas in der Bibliothek finden | – | **0 bis 2** (Suche, Treffer) |

## 9. Wohin jede heutige Funktion wandert

Alles bleibt, wie es heute funktioniert; nur Ort und Text ändern sich. **Die ganze heutige Technik-Seite wird eingebettet** (5.9), also bleibt jede Zeile der Tabelle aus Rev. 1 für Administratoren erreichbar. Die Alltagsfassung:

| Heute (Fundort in `ist.md`) | Neu | Wer |
|---|---|---|
| Reiter „Serien“ | Reiter „Bibliothek“ (Kacheln, Alle Folgen, Suche, Filter, Sortieren) | alle |
| „Hochladen“-Karte | „Hinzufügen“ (7.3); Vorgabe-Serie über die Zielwahl oder „Dateien in diesen Eintrag“; „Liste leeren“ wird „Erledigte ausblenden (auf diesem Gerät)“ | alle |
| „Neue Serie“ (leer anlegen), Überraschungs-Serie | Technik → Bibliothek aufräumen | Admin |
| „Freigabe prüfen“ | Technik → „Medien neu einlesen“; beim Öffnen der Seite höchstens alle 10 Minuten (`medien/pruefen`, ohne Cover-Suche) | Admin / Auslöser alle |
| Serie/Folge umbenennen | Eintrag → „Name ändern“, Zeile → „⋯“ → „Name ändern“ | alle |
| „Alles geprüft“ | „Das ist richtig“ / „Das stimmt nicht“ | alle |
| Folge hoch/runter | Eintrag → „Reihenfolge ändern“ (▲ ▼) | Admin (U23b) |
| Folge verschieben | Zeile → „⋯“ → „In anderes verschieben …“ | **alle** (Runde 6) |
| Folge löschen / Serie löschen | Zeile → „⋯“ → „Papierkorb …“; Eintrag → Aufräumen → „In den Papierkorb …“ | **alle** (Runde 6) |
| Serien zusammenführen | Eintrag → Aufräumen → „Zusammenführen …“ | Admin |
| Reiter „Eingang“ | Alltag: „Zuletzt hinzugefügt“ in „Hinzufügen“. Voll: Technik → Eingang im Detail | alle / Admin |
| „Erneut einsortieren“ / „Sofort“ / „Entfernen“ | „Jetzt prüfen“ (ohne `sofort`) für alle; `sofort` und „Entfernen“ in Technik | alle / Admin |
| „Neue Tobies“, „Verwerfen“ | Karte „Neuer Tobie“, „Das war ein Versehen, nicht merken“ | alle |
| „Zuordnen“ (Serie / **einzelne Folge** / Aktion) | Kachel (7.1), Knopf „Tobie“ an Folgen und Liedern (5.4), Kachel „Gute Nacht“; Aktion „Status“ nur Technik → Tobies im Detail | alle / Admin |
| Lernmodus | Eintrag/Folge → „Tobie anlernen“ (7.2) | alle |
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
| **lesen** (alle) | 1 `hello`, 2 `subscribe`, 3 `serien/list` (erweitert), 4 `serie/get`, 10 `papierkorb/list`, 13 `neue_tobies/list`, 15 `zuordnung/list`, 21 `boxen/list` (ohne `ereignisse`), 29 `eingang/list`, 34 `konfig/get`, 35 `einstellungen/get`, neu `folgen/list`, HTTP-Cover (GET) |
| **alltag** (alle angemeldeten Benutzer) | 16 `zuordnung/set` (inkl. Name), 17 `zuordnung/remove`, 14 `neue_tobies/verwerfen`, 18 `lernmodus/start` (bisher Admin), 19 `lernmodus/antwort`, 20 `lernmodus/abbrechen`, 6 `serie/rename`, 25 `folge/rename`, 28 `einsortierung/bestaetigen`, 9 `medien/pruefen`, 30 `eingang/sortieren` (**ohne** `sofort`), 36 `einstellungen/set` (ohne Zeitzone und Lesezeichen-Tage), neu `serie/art_setzen`, HTTP-Upload, HTTP-Cover (POST, DELETE `eigen`),
  **8 `folge/delete`, 24 `serie/delete`, 26 `folge/verschieben`** (neu in Rev. 2: nur in den Papierkorb, nichts endgültig) |
| **admin** | 5 `serie/create`, 27 `serien/zusammenfuehren`, 11 `papierkorb/restore`, **12 `papierkorb/empty`**, **33 `eingang/entfernen`**, 22 `box/sync`, 23 `liste/neu_ausrollen`, 32 `konfig/aus_export`, **31 `konfig/export_lesen`** (U26), `boxen/list`-Feld `ereignisse`, `eingang/sortieren` mit `sofort`, `einstellungen/set` für Zeitzone und Lesezeichen-Tage, neu `cover/neu_suchen`, später Update |

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
der Prüfabschnitt „gegen die HA-API“ nennt `async_register_admin_service`. Neue Fähigkeiten nur dort, wo eine alte Seite im Zwischenspeicher sonst etwas Falsches täte: **`cover`** und **`bibliothek`** (neue Eingaben von `serien/list`, Befehl `folgen/list`).
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
* **`serien/list` bekommt optionale Eingaben:** `art`, `text` (2 bis 100 Zeichen; sucht im Namen des Eintrags und, mit `auch_folgen`, in Folgentiteln), `filter` (Liste aus `ohne_tobie`, `neu`, `pruefen`), `sortierung` (`name`, `neu`), `limit` (1 bis 200), `offset`. Ausgabe bekommt `gesamt` (nach Filter) und `weitere`.
  **Fehlt `limit`, gilt das bisherige Verhalten** (alle, höchstens 200, dazu `weitere`); so bleibt die alte Seite gültig. Das 64-KiB-Limit einer Nachricht (Vertrag, Größen) bleibt gewahrt, weil die neue Seite blättert.
* **Neuer Befehl `folgen/list`** (lesen): Eingaben `art`, `text`, `filter`, `sortierung` (`titel`, `neu`), `limit` (1 bis 100, Vorgabe 60), `offset`. Ausgabe: `folgen` = Liste aus `serie_id`, `serie_name`, `art`, `folge` (Name), `anzeige`, `nummer`, `kapitel`, `groesse_mb`, `tobies` (direkt auf die Folge), `serie_hat_tobie`; dazu `gesamt`, `weitere`.
* **`zuordnung/list`** bekommt `text` (Tobie-Name oder Ziel) und die Sortierung `neu` zuerst (V-5).
* **Neuer Befehl `serie/art_setzen`** (Alltag): `serie_id`, `art`; setzt `art_quelle="manuell"`.
* **Art beim Einsortieren aus Tags vorschlagen** (Vertrag Abschnitt 11): Genre-Tag mit „Hörbuch“/„Audiobook“/„Spoken“ oder Endung `.m4b` → `hoerbuch`; Genre „Hörspiel“/„Audio Drama“/„Radio Play“ → `hoerspiel`; Musikgenre (Pop, Kinderlieder, Children’s Music, Klassik, Schlaflied …) oder viele kurze Tracks (Mittel unter 8 Minuten) mit Album-Interpret → `musik`;
  Märchen/Geschichten/Einzeldatei unter 30 Minuten ohne Album → `geschichte`; sonst `hoerspiel` mit `art_quelle="geraten"` und Grund `art_geraten` in `pruefen_gruende` („Die Art ist geraten. Stimmt das?“). Ein von Hand gesetztes `art` (`manuell`) wird **nie** überschrieben.
* *Index:* Die Integration hält Eintrags- und Folgennamen (normalisiert) im Speicher; Aufbau beim Start, Aktualisierung bei `serien_geaendert`. Test: 600 Einträge, 2 000 Folgen, Suche unter 200 ms.

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
| `cover_suche` | object `{"ergebnis": "tags"|"datei"|"keine", "zeit": <Zeitstempel>}` | Marke „schon gesucht“ (U5) |

**Reservierte Dateinamen** im Serien-Ordner (neu, additiv; die Bibliothek der Box liest nur Audioendungen und ignoriert sie schon): `cover.jpg` (automatisch), `cover-eigen.jpg` (Foto, hat Vorrang); als **Quelle** gelesen, nie geschrieben: `folder.jpg`, `cover.png`. Beim **Zusammenführen** übernimmt die Ziel-Serie das Cover der Quelle, wenn sie selbst keines hat;
im **Papierkorb** wandern die Dateien mit dem Ordner; beim **Umbenennen** bleiben Ordnername und ID, also auch die Cover. Beim Einsortieren aus einem Eingangs-Ordner hat ein mitgeliefertes `cover.jpg`/`folder.jpg` Vorrang vor dem eingebetteten Bild und geht nicht in den Papierkorb.

**Sync:** `box/src/tobibox/sync.py` nimmt zusätzlich `cover*.jpg`, `cover*.png` und `folder.jpg` aus (zu den Systemdateien und `_upload`, `_papierkorb`, `eingang`). Empfehlung aus dem Review, übernommen: Die Box hat kein Display; 500 Cover à 150 KiB wären 75 MB SD-Platz und Schreibvorgänge für nichts.
Test in `box/tests`: Sync mit Covern überträgt sie nicht; Zusammenführen; Wiederherstellen aus dem Papierkorb; Serie umbenennen. Das ist die **einzige Änderung am Box-Code in Stufe A**.

Hinweis zum Sync: Die Box gleicht die **ganze** Bibliothek ab (`rsync --delete`). Bei ca. 200 Hörbüchern kann das mehr als 50 GB sein; der erste Abgleich dauert Stunden. Das ist keine Änderung der Oberfläche, aber Tobias sollte den freien Platz der Boxen (`speicher_frei`, „Technik“) im Blick haben (Frage 10).

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

### 12.3 Speicherung in HA: Vergleich

| | Recorder / Langzeitstatistik von HA | **Eigene SQLite-Datei** (`<config>/tobibox/gehoert.sqlite`) | JSON-Zeilen-Datei |
|---|---|---|---|
| Vorteile | kein eigener Speichercode; Diagramme und Karten von HA; Akku-Sensor hat `state_class: measurement`, damit gibt es **stündliche Langzeitstatistik ohne Ablauf** | beliebige Fragen (je Eintrag, Folge, Stunde, Box); unabhängig von der Recorder-Bereinigung; idempotent (`UNIQUE`); CSV-Export; HA-Sicherung enthält den Konfigurationsordner | trivial zu schreiben und zu lesen |
| Nachteile | Zustände nur 10 Tage (Vorgabe `purge_keep_days`); Langzeitstatistik nur Summen/Mittel je Entität, **kein „welches Hörspiel“**; eine Entität je Eintrag bei 250+ Einträgen untauglich | eigener Code: Schema, Migration, Zugriff im Executor, Tests; in HA-Standardkarten nicht sichtbar | langsam bei vielen Zeilen, kein Index, Gefahr halber Schreibvorgänge |
| Eignung | **Akku-Verlauf** (Statistik, schon vorhanden), Hörzeit gesamt | **Hörereignisse** und Technik-Ereignisse | nur Notlösung |

**Empfehlung:** SQLite für Hörereignisse und Technik-Ereignisse (Lader, Sync, Fehler, online), **Langzeitstatistik von HA für den Akku** (Seite liest sie über `recorder/statistics_during_period`, nur Administratoren). Favoriten liegen in HA (`.storage/tobibox.favoriten`, Schlüssel `serie_id` oder `serie_id#folge`), nicht in `serie.json` und nicht auf der Box.

**Speicherbedarf (Schätzung, 250 Byte je Zeile mit Index):** 2 Boxen × 20 Sitzungen am Tag ≈ 14 600 Zeilen im Jahr ≈ **3,7 MB**; selbst 100 Sitzungen je Box und Tag nur ≈ 18 MB im Jahr. Technik-Ereignisse (50 je Box und Tag) ≈ 5 MB im Jahr. Akku-Statistik ≈ 2 bis 3 MB im Jahr.
Zusammen **etwa 10 MB im Jahr**, 100 MB in zehn Jahren: „unbegrenzt“ ist unproblematisch. Eine Aufräumregel ist nicht nötig. Trotzdem: Knopf „Alle Hördaten löschen“ und „Als Tabelle sichern“ in „Technik“ (Hördaten über Kinder sind persönlich; sie bleiben nur in HA, nie in der Cloud).

### 12.4 Vertragsentwurf `ha-websocket-v1.md` (Stufe B)

Fähigkeit **`gehoert`** (Reiter „Gehört“, Stern und Sortierungen erscheinen nur damit). Neue Befehle:

| Befehl | Recht | Eingabe → Ausgabe |
|---|---|---|
| `gehoert/zusammenfassung` | lesen | `box` (optional), `von`, `bis`, `gruppe` (`tag`, `eintrag`, `stunde`) → `tage` (Datum, Box, Sekunden), `eintraege` (Serien-ID, Name, Sekunden, Anzahl), `stunden` (0 bis 23, Sekunden) |
| `gehoert/zuletzt`, `gehoert/meist` | lesen | `box`, `limit`, `von`, `bis` → Einträge mit Zeit bzw. Sekunden |
| `favorit/set`, `favoriten/list` | **Alltag** / lesen | `serie_id`, `folge` (optional), `an` → Liste |
| `technik/verlauf` | admin | `box`, `von`, `bis` → Akku (Statistik), Ladezeiten, Laufzeit je Ladung, Syncs, Fehler |
| `gehoert/exportieren`, `gehoert/loeschen` | admin | CSV bzw. alles löschen (mit Bestätigungswort) |

`serien/list` und `folgen/list` bekommen die Sortierungen `zuletzt_gehoert`, `meist_gehoert` und den Filter `favorit` (nur mit Fähigkeit `gehoert`). Hördaten sind lesbar für alle HA-Benutzer (Frage 8).

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
* **Doppeltippen:** Knöpfe, die etwas senden, sind während des Aufrufs gesperrt (`anfrage_id`).

## 15. Arbeitspakete (Sonnet, billigstes passendes Modell)

Regeln: Vor dem Bau Resolve mit Tobias. Jedes Paket hat eigene Tests und ist allein lauffähig. **Die bestehenden Tests** (`homeassistant/tests/frontend/`: 121 Tests der alten Seite; `homeassistant/tests` mit `pytest`; `box/tests`) müssen nach **jedem** Paket grün sein und werden **nicht angepasst** (U6: die alte Seite bleibt eingebettet). Pakete A1, A2, A3, A4 hängen nicht von der Seite ab und laufen parallel.
Der Vertrag (A0) wird **zusammen mit A1** geschrieben, nicht davor (er beschreibt, was gebaut ist).

### 15.1 Stufe A (wird gebaut)

| AP | Inhalt | Modell | Tests |
|---|---|---|---|
| A0 | **Vertrag W und Datenmodell** einarbeiten (11): Eintrag „Änderung 12.11.“, Abschnitt 2.1 ersetzen, W-19 streichen, `serie.json`-Felder, reservierte Dateinamen. Nur nach Freigabe | Sonnet | – |
| A1 | **Rechte und Schutz** (10): `befehl(recht=…)`, Tabelle 10.2, Schutz 10.3 (`erwartet_ziel`, bekannte Kennungen, Mengen, `erwartet_revision`, Zeitzone ignorieren, `sofort` nur Admin), `boxen/list`/`export_lesen` nur Admin, 10 frühere Stände der Liste, Upload ohne `require_admin`. **`require_admin` bleibt `True`** | Sonnet | `tests/test_websocket_api.py`: Tabelle 10.2 als Parametertest (Admin und Normal-Benutzer je Befehl); Schutzfälle einzeln; `tests/test_services.py`: jede Aktion als Nicht-Admin = `Unauthorized`; `tests/test_upload.py`: Nicht-Admin 200 |
| A2 | **Anzeigenamen** (V-3): Textfeld in Optionen, `strings.json`, `translations/de.json`, `anzeige`, `hello.box_anzeigen` | Haiku (Formular) + Sonnet (Hub) | `test_config_flow.py`, Reihenfolge der Rückfälle |
| A3 | **Art und Bibliothek-Backend** (V-2): Art-Vorschlag beim Einsortieren, `serien/list` erweitert, `folgen/list`, `serie/art_setzen`, `zuordnung/list` mit `text`/`neu`, Index | Sonnet | Art-Regeln mit Tag-Fixtures (Genre, `.m4b`, Albumlänge); Suche, Filter, Sortieren, Blättern; **Leistungstest 600 Einträge / 2 000 Folgen < 200 ms**; alte Aufrufe ohne `limit` unverändert |
| A4 | **Cover-Backend** (V-1, 5.5): Extraktion mit Marke, Nachholen im Hintergrund mit Zeitgrenze, `ffmpeg` fehlt, GET/POST/DELETE, `cover/neu_suchen`, Zusammenführen und Papierkorb | Sonnet | `tests/test_cover.py` (ffmpeg-Fixture MP3 mit/ohne Bild, kaputtes Bild, Marke verhindert Wiederholung, Zeitgrenze, Foto-Upload: falscher Typ, zu groß, nicht quadratisch, Original wird nicht gespeichert, ETag) |
| A4b | **Sync-Ausschluss** `cover*.jpg`, `cover*.png`, `folder.jpg` in `box/src/tobibox/sync.py` | Sonnet | `box/tests`: Sync mit Covern überträgt sie nicht, übrige Dateien unverändert |
| A5 | **Texte** `texte.js`: Fehlertabelle (6.1), Gründe (7.3), Sätze (5.1.1), vollständig gegen den Vertrag geprüft | Haiku + Sonnet-Review | Test: jeder Code der Vertragstabelle hat einen Text; Texte wörtlich wie hier |
| A6 | **Panel-Gerüst** (neue Dateien): Reiter und Technik-Knopf (`narrow`, sticky, `visualViewport`), Routen, Theme-Token und Kontrastfunktion, Zustände, `<dialog>`-Blatt, Meldungen; **alte Komponente als `tobibox-technik` mit Schalter `eingebettet`** | Sonnet | jsdom: Reiter und Routen, Nicht-Admin sieht keinen Technik-Knopf, Zustände, Fokus nach Dialog; **alte 121 Tests unverändert grün** |
| A7 | **Start und Bibliothek**: Status-Sätze, Kacheln mit Platzhalter, Cover-Laden (`fetchWithAuth`, `blob:`, `IntersectionObserver`), Art-Leiste, Alle Folgen, Suche (3 Gruppen), Filter, Sortieren, Blättern | Sonnet | jsdom: Satz-Tabelle; Suche entprellt; Filter und Sortierung senden die Eingaben von V-2; „Mehr zeigen“ sendet `offset`; Platzhalterfarbe stabil |
| A8 | **Eintrag**: Kopfkarte, Name/Art/Cover ändern (Zuschneiden im Browser), „Das ist richtig/stimmt nicht“, Folgenliste mit „Tobie“ und „⋯“, Papierkorb | Sonnet | jsdom: Blatt „Tobie für dieses Lied“, Zuschneiden (Canvas-Mock), Löschen mit `tobies_bestaetigt` |
| A9 | **Neuer Tobie und Tobies**: Karte, Zielwahl, Fertig-Karte mit Name, Rückgängig (`erwartet_ziel`), Tobies-Liste (zuletzt angelernt, Suche), Blatt, Kachel „Gute Nacht“ | Sonnet | jsdom mit `mock-hass.mjs`: Ereignis `neu` → Karte; Tap → `zuordnung/set`; Name; Rückgängig → `zuordnung/remove` mit `erwartet_ziel` |
| A10 | **Anlernen** (Ziel Serie und Folge, Name, Wiederaufnahme) | Sonnet | jsdom: alle Zustände aus Vertrag 4.3 → Texte 7.2 |
| A11a | **Hinzufügen: Hochladen** (Zielwahl, Warteschlange 2 parallel, Fortschritt, Abbruch, Unterbrechung, 413) | Sonnet | jsdom: Fortschrittsschritte, Upload-Fehlercodes, `serie_id` bei Ziel |
| A11b | **Hinzufügen: Eingang-Anbindung** (24-Stunden-Liste, `quelle`, Gründe, NAS-Einträge, „Das stimmt nicht“) | Sonnet | jsdom: Gründe-Texte, „bitte kurz ansehen“, Wiederaufnahme nach Neuladen |
| A12 | **Abends** (Schnellwahl, Zeilenliste, Blatt, Prüfregeln, `erwartet_revision`) | Sonnet | `panel_quiet.test.mjs` bleibt für die alte Seite; neue Tests: 24-Stunden-Auswahl, krumme Minute bleibt, Fehlerstelle in Worten |
| A13 | **Technik**: Einbettung, Warnleisten, „Frühere Stände“, „Cover neu suchen“, Ausblenden-Wert | Sonnet | jsdom: Karten, Rechte |
| A14 | **Playwright-Skript (Pflicht)** unter `homeassistant/tests/frontend/`: Tap-Ziele ≥ 44 px, kein waagerechtes Scrollen (320, 390, 1280 px), Kontrast in **drei Themes**, Screenshots für Tobias | Sonnet | das Skript selbst; vom Prototyp übernommen (`audit`) |
| A15 | **Doku**: `homeassistant/README.md` (Seite für alle, Namen, Cover, **HA-Automation „Neuer Tobie“ als Vorlage**), `docs/betrieb/` „Für Verena“ | Haiku | Abgleich mit `texte.js` |
| A15b | **Companion-App früh prüfen** (iOS und Android: Reiter unten, Safe Area, Tastatur, Foto) | Tobias | – |
| A16 | **Abnahme mit Tobias**, Schritt für Schritt im Chat (Mac, Handy): Tobie zuordnen (a, b), Lied-Tobie, Hinzufügen vom Handy, Cover per Foto, Abends, Papierkorb als Nicht-Admin | Projektleitung + Tobias | – |
| A17 | **Seite für alle öffnen** (`require_admin=False`) | Sonnet | `test_init.py`: Panel ohne `require_admin`; Tabelle 10.2 mit Testbenutzer ein letztes Mal |

Empfohlene Reihenfolge: A1, A2, A3, A4, A4b (parallel) → A0 → A5 → A6 → A7 → A8, A9, A10 → A11a, A11b → A12 → A13 → A14 → A15 → A15b/A16 → A17.

### 15.2 Stufe B (eigener Block, nach Freigabe)

| AP | Inhalt | Vertragsänderung |
|---|---|---|
| B1 | **Vertrag** `mqtt-v1.md`: `gespielt`, `gehoert_quittung` (12.2); `ha-websocket-v1.md`: Befehle und Fähigkeit `gehoert` (12.4); `data-model.md`: `gehoert.jsonl` der Box | ja |
| B2 | **Box:** Sitzungserkennung, Puffer `gehoert.jsonl` (Schreibbudget), Senden und Quittung | `mqtt-v1` |
| B3 | **HA:** SQLite-Speicher, Aufnahme mit Doppelerkennung, Quittung, Technik-Ereignisse aus `status`, Favoriten | – |
| B4 | **HA-Befehle** `gehoert/*`, `favorit/*`, `technik/verlauf`, Sortierungen und Filter in `serien/list`/`folgen/list` | `ha-websocket` |
| B5 | **Seite:** Reiter „Gehört“ (SVG-Diagramme), Stern, Sortierungen, Technik-Karte Akku-Verlauf | – |
| B6 | **Abnahme** mit Tobi (Box im Hörbetrieb, offline hören und danach verbinden) | – |

### 15.3 Stufe C (eigener Block, später)

C1 Verträge (`data-model`, `core-interface`, `mqtt-v1` Schema-Hinweis, `ha-websocket` `playlist/*`) · C2 Box (Ziel-Typ, Zeiger, Sync-Regel, Update) · C3 HA (Befehle, Datei, Index, Papierkorb) · C4 Seite (Zielwahl, Karte, Blatt) · C5 Abnahme. Reihenfolge: erst Boxen aktualisieren (Schema 3), dann freischalten.

## 16. Offene Fragen für Tobias (mit Empfehlung)

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

## 17. Was der Prototyp v2 zeigt und was nicht

`prototyp.html` ist eine **Vorschau**, kein Code für den Bau, und schickt nichts an Home Assistant. Er zeigt (alles im Script erzeugt, erfundene Daten): **60 Einträge** (20 Hörspiele, 20 Hörbücher, 12 Musik-Alben, 8 Geschichten, darunter ein Album mit 20 Liedern), **572 Folgen und Lieder** in „Alle Folgen“.
Funktionsfähig sind: Suche über alles (3 Gruppen, Treffer hervorgehoben), Art-Leiste, Filter („Ohne Tobie“, „Neu“, „Bitte ansehen“), Sortieren (A bis Z, zuletzt hinzugefügt), Kacheln und „Alle Folgen“, „Mehr zeigen“ (Blättern in 60er-Päckchen), Knopf „Tobie“ an jedem Lied (Blatt, Anlernen auf Folge, Umstellen),
Zielwahl mit „Einzelne Folge oder Lied“, **Name-Abfrage** in der Fertig-Karte und nach dem Anlernen, **Cover per Foto** (Dateiauswahl, quadratischer Ausschnitt mit Ziehen, Pfeilen und Regler, Speichern, „Zurück zum automatischen Cover“), „Das ist richtig / Das stimmt nicht“,
Papierkorb, Gute Nacht (Schnellwahl), Leise-Zeiten (Zeilen), „Technik“ mit eingebetteter alter Seite. **Stufe B** (Reiter „Gehört“ mit drei SVG-Diagrammen, „Zuletzt gehört“, „Meist gehört“, Favoriten, Akku-Verlauf in „Technik“) ist mit „Stufe B – Vorschau“ markiert, **Stufe C** (Playlist-Karte, ausgegrauter Knopf) mit „Stufe C – Idee“.
Der **Rollen-Umschalter** (Administrator / Verena) zeigt die Unterschiede: Verena hat keinen Technik-Knopf, keine „Reihenfolge ändern“, kein „Zusammenführen“, kann aber in den Papierkorb legen; Leeren gibt es nur in „Technik“.

**Prüfung** mit Playwright (Chromium) bei 390 und 1280 px, Hell, Dunkel und „Theme mit hellem Primärton“, Administrator und Verena, alle 9 Ansichten: kein waagerechtes Scrollen, alle Knöpfe, Auswahlfelder und Reiter mindestens 44 px, Kontrast mindestens 4,5:1 (3:1 große Schrift): **0 Treffer**;
dazu ein Ablauf-Skript (Suche, Filter, Sortieren, Alle Folgen, Blättern, Lied-Tobie, Name, Cover-Upload, Rollen, Papierkorb) ohne Fehler. Der Durchgang Korrekturen behob: überlaufende Auswahlfelder in der Vorschau-Leiste bei 390 px, unsichtbare Kacheln in den waagerechten Reihen (`content-visibility`), zu große Diagrammschrift am Computer und überlappende Achsenbeschriftung,
eine zu helle Linkfarbe im Theme mit hellem Primärton (jetzt gegen die hellste Fläche gerechnet), eine gestreckte Marke im Blatt und den Knopftext „OK“ nach dem Speichern des Namens.
**Nicht belegt:** echte HA-Farben und -Themes, Companion-App, echte Fotos vom Handy, Tastatur auf iOS.

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
