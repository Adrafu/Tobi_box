# HA-Oberfläche einfacher und schöner: Design-Entwurf (EGM Schritt 2)

Stand 12.11. · Grundlage: `concepts_brief.md`, `brainstorm.md`, `ist.md` (mit `screens/`), Vertrag W
(`docs/protocol/ha-websocket-v1.md`). Klickbarer Prototyp: `prototyp.html` (erfundene Beispieldaten, Reiter
„Vorschau mit Beispieldaten“ oben schaltet Rolle, Hell/Dunkel und die Zustände um).
Status: **Entwurf, wartet auf Goldfische.** Nur Oberfläche und Bedienbarkeit. Einzige neue Funktion: Cover aus den MP3-Tags.

## 1. Kurz gesagt

* Eine Seite „Tobi Box“ für **alle** HA-Benutzer. Fünf Reiter: **Start · Hörspiele · Tobies · Abends · Für Tobias**.
  „Für Tobias“ sieht nur ein Administrator.
* Die Startseite zeigt, was man tun will: zwei Status-Sätze der Boxen, bei Bedarf „Neuer Tobie“, zwei große Knöpfe
  („Hörspiel hinzufügen“, „Abends“), dann die Hörspiele als Cover-Kacheln.
* Alles Technische (Revision, Liste neu ausrollen, Papierkorb, Eingang im Detail, Sync, Meldungen mit Codes) wandert unverändert
  nach „Für Tobias“. Nichts geht verloren (Abschnitt 8).
* Zuordnen geht ohne Rückfrage: Kachel tippen, fertig, dazu „Rückgängig“. Rückfragen gibt es nur beim Löschen.
* Die Seite braucht dafür gelockerte Rechte (Abschnitt 9) und wenige Ergänzungen im Vertrag W (Abschnitt 10).

## 2. Navigation

### 2.1 Handy (Hochformat bis 899 px): Reiter unten

Fünf Reiter unten, fest am Rand, je mindestens 60 px hoch (Symbol + Beschriftung), Beschriftung 12 px. Für Nicht-Admins vier Reiter.
**Begründung:** Der Daumen erreicht unten alles. Die Seite hat nur vier bis fünf Hauptbereiche, das passt in eine Leiste.
Eine lange Startseite mit Abschnitten würde „Tobies“ und „Abends“ weit nach unten schieben. Auf der Startseite stehen trotzdem
die häufigen Dinge zuerst, ohne dass man einen Reiter braucht. Roter Punkt am Reiter „Start“ mit Zahl, solange ein neuer Tobie wartet.

### 2.2 Computer (ab 900 px): Reiter oben

Dieselben Reiter als **waagerechte Leiste oben**, unter der Kopfzeile, mit Symbol und Text nebeneinander. Die Inhalte laufen in
zwei bis drei Spalten (Status-Karten nebeneinander, Kachel-Raster mit 150-px-Kacheln), Breite bis 1180 px.
**Begründung:** Home Assistant hat links schon seine eigene Seitenleiste. Eine zweite linke Leiste daneben wäre eng und
ungewohnt. Waagerechte Reiter oben kennt man aus HA selbst (Einstellungen, Energie).

### 2.3 Unterseiten, Zurück, Adressen

* Unterseiten: **Hörspiel** (Folgen), **Hörspiel hinzufügen**, **Tobie anlernen**. Oben links ein Knopf „‹ Hörspiele“ bzw. „‹ Start“.
  Der Browser-Zurück-Knopf geht denselben Weg.
* Adressen (nach `#`, nur einfache Namen): `#start`, `#hoerspiele`, `#serie-<id>`, `#hinzufuegen`, `#anlernen`, `#tobies`, `#abends`, `#tobias`.
  Nicht `settings`, `sidebar` oder Ähnliches (gehören HA).
* Menüknopf von HA (`ha-menu-button`) in die Kopfzeile, wenn `narrow` gesetzt ist (heute fehlt er, `ist.md` Abschnitt 4).
  So kommt man am Handy zurück in HA.

### 2.4 Sprache, Namen

Es heißt überall **Hörspiel** (im Code `serie`), **Folge**, **Tobie** (Mehrzahl Tobies), **Papierkorb** (nie „Korb“).
Nicht mehr sichtbar für Verena: Serie, Track, Tags, Kennung, UID, Revision, Eingang (außer in „Für Tobias“ und im Satz zum NAS), Überraschung.
Die Überraschungs-Serie wird in „Hörspiele“ nicht als Kachel gezeigt (nur in „Für Tobias“).

## 3. Stil

* Home-Assistant-Look über **HA-CSS-Variablen**, mit Rückfall: `--primary-color`, `--card-background-color`, `--primary-background-color`,
  `--primary-text-color`, `--secondary-text-color`, `--divider-color`, `--error-color`, `--success-color`, `--warning-color`.
  Hell und Dunkel folgen HA, ohne eigenen Schalter. Karten wie `ha-card` (Radius 12 px, leichter Schatten).
* Das Panel bleibt eine Lit-Komponente (`tobibox-panel.js`). Das Ergebnis darf dort gelb/blau sein, wie HA es vorgibt;
  im Prototyp ist `--primary` bewusst etwas dunkler (`#01689f`), damit weißer Text auf blauen Knöpfen Kontrast 4,5:1 erreicht.
  Der Bau prüft die Kontraste mit den echten HA-Farben und nimmt `--primary-color`, wo es reicht, sonst eine Ableitung.
* Cover-Kacheln (quadratisch, Radius 12 px) für Hörspiele; Platzhalter: sechs feste Farben, Farbe aus der Serien-ID,
  großer Anfangsbuchstabe in Weiß.
* Tap-Ziele **mindestens 44 × 44 px**, Hauptknöpfe 48 px, große Startknöpfe 64 px. Abstand zwischen Knöpfen mindestens 8 px.
* Schrift: Roboto (HA), Fließtext 16 px, Nebentext 14 px, nirgends unter 12 px (nur Tab-Beschriftung und Marken).
* Wenig Text: höchstens ein Satz Erklärung pro Karte.

## 4. Seiten und ihre Texte

Alle Texte wörtlich. Die Box-Namen sind Beispiele und kommen aus den Einstellungen der Integration (Abschnitt 10, W-3).

### 4.1 Start

Aufbau von oben nach unten:

1. **Warnband** (nur bei Bedarf, siehe 5): Verbindung weg, Liste gesperrt.
2. **Status-Karten** der beiden Boxen (eine je Box, am Computer nebeneinander), siehe 4.1.1.
3. **Karte „Neuer Tobie“** (nur wenn eine Box einen unbekannten Tobie meldet), siehe 6.1.
4. **Zwei große Knöpfe:** „**Hörspiel hinzufügen**“ (blau) und „**Abends**“.
5. **Hinweiskarte zum Hinzufügen** (nur wenn etwas läuft oder angesehen werden soll): „2 Hörspiele werden gerade hinzugefügt.“ /
   „1 neues Hörspiel bitte kurz ansehen.“ / „Alles hinzugefügt.“ mit „Tippen für Einzelheiten“ (Ziel `#hinzufuegen`).
6. Überschrift „**Deine Hörspiele**“ und die ersten sechs Kacheln, darunter „Alle Hörspiele ansehen“.

#### 4.1.1 Status-Karte der Box (ein Satz)

Links Cover des Gespielten (sonst Lautsprecher-Symbol), rechts ein **Satz**, darunter eine Zeile Nebentext. Punkt grün (online) oder grau.
Quelle: `boxen/list` (`anzeige`, `online`, `status.zustand`, `status.serie`, `status.folge`, `status.akku_prozent`, `status.lader`, `konfig_stand`).
Den Namen der Serie holt die Seite über `status.serie.id` aus der eigenen Serienliste (Umbenennungen sind sofort sichtbar).

| Lage | Satz | Nebentext |
|---|---|---|
| spielt | „Box Mond spielt „Lange Serie“ · Folge 4: Der Rabe.“ | „Akku 80 %, lädt.“ oder „Akku 80 %.“ |
| pausiert | „Box Mond ist pausiert bei „Lange Serie“.“ | wie oben |
| `leer`, `beendet`, `gehalten`, `unbekannt` | „Box Mond ist bereit. Es liegt kein Tobie auf.“ | wie oben |
| `herunterfahren` | „Box Mond geht gerade aus.“ | |
| Akku ≤ 20 % und kein Laden | (Satz wie oben) | „Akku fast leer (15 %). Bitte laden.“ (orange) |
| offline (`online=false`) | „Box Stern ist aus oder nicht im WLAN.“ | „Zuletzt gesehen: heute um 18:40. Akku war bei 35 %.“ |
| noch keine Meldung (`online=null`) | „Box Stern hat sich noch nicht gemeldet.“ | |
| `konfig_stand` ≠ `aktuell` | | zusätzlich „Neue Zuordnungen kommen auf die Box, sobald sie wieder im WLAN ist.“ |

Die Karte ist kein Knopf. Technische Einzelheiten (Netz, Speicher, Version, Sync, letzte Fehler) stehen in „Für Tobias“.

### 4.2 Hörspiele

* Kopf: Überschrift „Hörspiele“ und Knopf „+ Hörspiel hinzufügen“. Darunter Suchfeld „Hörspiel suchen“.
* Kachel-Raster. Kachel: Cover, Name (bis zu zwei Zeilen), „12 Folgen“. Orange Marke „bitte ansehen“ oben links im Cover,
  wenn etwas zu prüfen ist.
* Leer: „Noch keine Hörspiele. Tippe auf „Hörspiel hinzufügen“.“
* Suche ohne Treffer: „Nichts gefunden zu „xyz“.“
* Sortierung: nach Name. (Offene Frage 6.)

### 4.3 Hörspiel (Unterseite)

* „‹ Hörspiele“. Kopfkarte: großes Cover, Name, „12 Folgen · 3 Tobies“, Knopf „Name ändern“.
* Falls zu prüfen: gelbe Karte „**Bitte kurz ansehen.** <Grund in Alltagssprache, Abschnitt 6.3>“ mit Knopf „Passt so“.
* Karte „**Tobie dafür anlernen**“: „Wähle die Box. Danach legst du den Tobie auf, der „Lange Serie“ spielen soll.“
  Je Box ein blauer Knopf: „Auf Box Mond“, „Auf Box Stern“. Ist eine Box aus, ist ihr Knopf grau und darunter steht:
  „Box Stern ist aus. Schalte sie ein, dann geht es.“ Ist nur eine Box erreichbar, ist es ein Knopf.
* Abschnitt „Folgen“, Knopf „Reihenfolge ändern“ (schaltet ▲/▼-Knöpfe an den Zeilen ein, **kein Ziehen**; Text wechselt zu „Fertig mit Reihenfolge“).
  Zeile: Nummer, Name, „1 Kapitel · 44 MB“, Knopf „Name ändern“. Im Reihenfolge-Modus statt „Name ändern“: ▲ ▼ mit Beschriftung für Vorleser („Folge 4 nach oben“).
  Das Löschen einer Folge ist **nicht** in der Zeile (Abschnitt 8).
* Nur Administratoren: Karte „**Aufräumen**“ ganz unten, abgesetzt: „Mit anderem Hörspiel zusammenführen …“, „Hörspiel in den Papierkorb …“ (rot umrandet).
* Leer: „Noch keine Folgen. Füge Dateien über „Hörspiel hinzufügen“ hinzu.“

### 4.4 Hörspiel hinzufügen

Siehe Ablauf 6.3. Aufbau: „‹ Start“, Überschrift „Hörspiel hinzufügen“; zwei große Knöpfe „**Dateien wählen**“ (Handy und Computer)
und „**Ordner vom Computer wählen**“; am Computer zusätzlich eine Fläche „Auf dem Computer kannst du Dateien oder einen ganzen Ordner auch hierher ziehen.“
(Ziehen ist nur eine Zusatzmöglichkeit, nie der einzige Weg). Nebentext: „Erlaubt: MP3, M4A, M4B, AAC, FLAC, OGG, Opus, WAV. Bis 500 MB je Datei.
Kopiergeschützte Dateien (zum Beispiel von Audible) gehen nicht.“ Hinweiskarte: „Du kannst Dateien auch am Computer in den Eingang-Ordner auf dem NAS kopieren.
Sie erscheinen hier von selbst. Frag Tobias nach dem Ordner.“ Darunter „**Gerade eben**“ mit allen Vorgängen (6.3).
Das Wort „500 MB“ kommt aus `hello.grenzen.upload_max_bytes`, nicht fest im Text.

### 4.5 Tobies

* Überschrift „Tobies“, Satz: „Alle Tobies, die schon etwas spielen. Einen neuen legst du einfach auf eine Box. Dann erscheint er auf der Startseite.“
* Zeile je Tobie: kleines Cover des Ziels, Name oder „Tobie ohne Namen“, „spielt „Lange Serie““, Knopf „Ändern“. Aktionskarten: Mond-Symbol, „spielt „Gute Nacht““.
* Tippen auf die Zeile öffnet ein Blatt: „Namen ändern“, „Anderes Hörspiel“ (Kachelauswahl, Tippen = gespeichert, Meldung „Fertig: spielt jetzt „…“.“ mit „Rückgängig“),
  weit unten abgesetzt: „Diesen Tobie vergessen …“ (rote Schrift, mit Rückfrage).
* Eine einzelne **Folge** als Ziel: In diesem Entwurf nur lesend („spielt „Lange Serie“ · Folge 4“). Ändern geht in „Für Tobias“ (Tabelle 8). Offene Frage 4.
* Leer: „Noch keine Tobies. Lege einen Tobie auf eine Box, dann erscheint er auf der Startseite.“

### 4.6 Abends

Zwei Karten. Ablauf 6.4.

**Gute Nacht.** „Lege den Gute-Nacht-Tobie auf. Dann läuft ein Timer. Danach wird es leise und die Box hört auf.“
„Die Box spielt noch [−] **30 Minuten** [+]“ (Schritt 5 Min., 5 bis 240). „Dann wird sie leiser über [−] **1 Minute** [+]“ (Schritt 15 s, 15 bis 600 s).
Knopf „Speichern“ (grau mit „Gespeichert“, solange nichts geändert ist). Darunter „Ein Gute-Nacht-Tobie ist angelernt („Mond-Karte“).“
bzw. „Noch kein Gute-Nacht-Tobie.“ und der Textknopf „So legst du einen an“ (Blatt mit vier Schritten, Ablauf 6.1).

**Leise-Zeiten.** „In diesen Zeiten ist die Box leiser oder still.“ **Wochenplan:** sieben Zeilen Mo bis So, je ein Balken von 0 bis 24 Uhr (Achse 0, 6, 12, 18, 24 Uhr),
„Still“ blau, „Leiser“ grau. Zeiten über Mitternacht werden am Starttag bis 24 Uhr und am Folgetag ab 0 Uhr gezeichnet
(ein Fenster gehört zum Starttag, Vertrag W 3.11). Der Plan hat einen Text für Vorleser („Wochenplan: Mo–Do, So 19:30 bis 06:30 Stumm; …“).
Darunter je Zeit eine Zeile: „**Mo–Do, So** · 19:30 bis 06:30 (bis zum nächsten Morgen) · Stumm“ mit Knopf „Ändern“; Knopf „+ Zeit hinzufügen“.
Leer: „Keine Leise-Zeiten. Die Box spielt immer in normaler Lautstärke.“
**Blatt „Leise-Zeit ändern“:** „An diesen Tagen“ (sieben Tag-Knöpfe 44 px, `aria-pressed`), Schnellwahl „Jeden Tag“, „So–Do“, „Fr, Sa“;
„Von“ und „Bis“ als je zwei Auswahlfelder (Stunde : Minute, 5-Minuten-Schritte, **24 Stunden**, unabhängig von der Browsersprache;
eine vorhandene krumme Minute bleibt als Wert erhalten); „Was soll die Box tun?“ **Still | Leiser**; bei Leiser Regler „Höchste Lautstärke: 25 %“,
bei Still der Satz „Die Box spielt nicht. Ein leiser Ton zeigt, dass der Tobie erkannt wurde.“ Knöpfe „Abbrechen“, „Speichern“. Meldung danach:
„Gespeichert. Die Boxen bekommen es gleich.“ Löschen: Textknopf „Diese Leise-Zeit löschen …“ ganz unten, durch Linie abgesetzt, mit Rückfrage
(„Leise-Zeit löschen? Mo–Do, So, 19:30 bis 06:30 wird gelöscht. Danach spielt die Box in dieser Zeit in normaler Lautstärke.“).
Fehler (`einstellung_ungueltig`): „Das konnte nicht gespeichert werden: <Stelle in Worten, z. B. „Leise-Zeit 2, Bis“>. Es wurde nichts geändert.“
Mindestens ein Tag, „Von“ ≠ „Bis“ prüft die Seite vorher mit eigenem Hinweis. Höchstens 32 Zeiten (Vertrag), darüber „Mehr Leise-Zeiten gehen nicht.“
Die **Zeitzone** zeigt die Seite hier nicht; sie bleibt, wie sie ist (und wird beim Speichern unverändert mitgesendet). Ändern: „Für Tobias“.

### 4.7 Für Tobias (nur Administratoren)

Oben gelbe Karte: „**Nur für Administratoren.** Hier liegt alles Technische. Verena sieht diese Seite nicht.“ (Im echten Text ohne Namen: „Normale Benutzer sehen diese Seite nicht.“)
Darunter aufklappbare Karten (jeweils die Inhalte von heute, Tabelle 8): Eingang im Detail · Papierkorb · Liste, Sicherung, Export · Boxen im Detail ·
Weitere Einstellungen · Meldungen der Boxen · Hörspiele aufräumen (Überraschungs-Serie, „Freigabe prüfen“, Zusammenführen für alle Hörspiele) · Tobies im Detail (Kennung, Folgen-Ziel, Kennung von Hand).
Gefährliche Knöpfe stehen rot, einzeln und mit Rückfrage, nie neben „Ansehen“-Knöpfen. Wer als Nicht-Admin die Adresse `#tobias` aufruft, sieht:
„Dieser Bereich ist nur für Administratoren. Wenn du etwas Technisches brauchst, frag Tobias.“
Die Warnleisten zur Liste (`leer_neu`, `export_neuer`, Box mit neuerem Stand) erscheinen für Admins **oben auf allen Seiten** wie heute; Nicht-Admins sehen auf allen Seiten nur den Hinweis aus 5.

## 5. Zustände

| Zustand | Was die Seite zeigt |
|---|---|
| **Lädt** | Graue, leicht pulsierende Platzhalter-Karten (statt „Lade …“). Mit „reduzierte Bewegung“ ohne Pulsieren. Nach 10 s ohne Antwort wird es der Fehlerzustand. |
| **Leer** (noch nichts eingerichtet) | Start: statt Boxen „Noch keine Box eingerichtet. Bitte Tobias Bescheid sagen.“; Hörspiele: „Noch keine Hörspiele. Tippe oben auf „Hörspiel hinzufügen“.“; Tobies siehe 4.5. Es gibt immer einen Knopf als nächsten Schritt. |
| **Fehler beim Laden** | Rote Karte: „**Die Seite konnte nichts laden.** Home Assistant antwortet gerade nicht. Warte kurz und versuche es noch einmal. Wenn es so bleibt, sag Tobias Bescheid.“ Knopf „Noch einmal versuchen“. |
| **Verbindung weg** (Websocket zu) | Rotes Band oben: „**Keine Verbindung zu Home Assistant.** Die Ansicht wird von selbst aktuell, sobald die Verbindung wieder da ist.“ Knopf „Jetzt neu laden“. Boxen grau. Schreibende Knöpfe grau, bis die Verbindung wieder da ist. |
| **Box offline** | Statuskarte grau (4.1.1). Knopf „Auf Box Stern“ grau mit Erklärung. |
| **Liste gesperrt** (`konfig.zustand` ≠ `ok`) | Nicht-Admin, Band oben: „Änderungen sind gerade gesperrt. Bitte Tobias Bescheid sagen.“ Alle Knöpfe, die die Liste ändern, grau. Admin: die Warnleiste von heute, in einfacheren Worten (Tobias entscheidet, nicht Verena). |
| **Alte Seite** (`hello.v` oder `unknown_command`) | „Die Seite ist veraltet. Bitte lade sie neu (am Handy: Seite nach unten ziehen oder Browser neu öffnen).“ (heute „Strg+F5“). |

### 5.1 Fehlertexte: immer mit nächster Handlung

Heute nennen sie die Ursache, hier die Handlung. Die Seite übersetzt `error.code` (Vertrag W, Abschnitt 7) und bei Upload `fehler.code`:

| Code | Text |
|---|---|
| `medien_nicht_erreichbar` | „Das NAS antwortet gerade nicht. Versuche es in ein paar Minuten noch einmal. Wenn es so bleibt, sag Tobias Bescheid.“ |
| `medien_schreibfehler` | „Das Speichern auf dem NAS hat nicht geklappt. Versuche es gleich noch einmal. Wenn es so bleibt, sag Tobias Bescheid.“ |
| `kein_speicher` | „Auf dem NAS ist kein Platz mehr. Bitte Tobias Bescheid sagen.“ |
| `mqtt_nicht_verbunden` | „Die Verbindung zu den Boxen ist gerade gestört. Es wurde nichts gesendet. Versuche es gleich noch einmal.“ |
| `box_offline` | „Box Stern ist aus oder nicht im WLAN. Schalte sie ein und versuche es noch einmal.“ |
| `konfig_nicht_bereit` | „Änderungen sind gerade gesperrt. Bitte Tobias Bescheid sagen.“ |
| `unauthorized` | „Dafür fehlt dir die Berechtigung. Frag Tobias.“ |
| `zuordnung_geaendert`, `stand_veraltet` | „Jemand hat gerade etwas anderes geändert. Die Ansicht ist neu geladen. Bitte versuche es noch einmal.“ |
| `lernmodus_laeuft` | „Auf Box Mond läuft schon das Anlernen für ein anderes Hörspiel. Beende es zuerst.“ (Knopf „Dort beenden“ = `lernmodus/abbrechen`) |
| `format_nicht_erlaubt` | „Dieses Dateiformat spielt die Box nicht. Erlaubt sind MP3, M4A, M4B, AAC, FLAC, OGG, Opus und WAV.“ |
| `datei_zu_gross` | „Die Datei ist zu groß (mehr als 500 MB). Am Computer in den Eingang-Ordner kopieren.“ |
| `zu_viele_uploads` | (kein Fehler: die Seite wartet und sendet danach weiter) |
| `name_ungueltig` | „Dieser Name geht nicht. Bitte kürzer oder anders schreiben.“ |
| `einstellung_ungueltig` | siehe 4.6 |
| `unknown_error`, unbekannter Code | „Das hat nicht geklappt. Versuche es noch einmal. Wenn es wieder nicht geht, sag Tobias Bescheid.“ (Code klein dahinter, nur für Admins) |
| Verbindung beim Upload abgebrochen | „Die Verbindung ist abgebrochen. Ob die Datei angekommen ist, siehst du in ein paar Minuten unter „Gerade eben“. Wenn nicht, wähle sie noch einmal.“ |

Fehler stehen als Karte am Ort der Handlung (nicht nur oben), bleiben bis „OK“ und werden Screenreadern über `role="alert"` vorgelesen.
Erfolg: kurze Meldung unten (4,5 s, `role="status"`), bei Rückgängig-fähigen Dingen 8 s mit Knopf.

## 6. Die vier Kernaufgaben als Abläufe

Gezählt wie in `ist.md`: Taps nach dem Öffnen der Seite, ohne Texteingabe und ohne Auflegen des Tobies. Ziel höchstens drei.

### 6.1 (a) Neuer Tobie erscheint → Kachel → fertig: **1 Tap**

1. *(Körperlich)* Verena legt einen unbekannten Tobie auf Box Mond. Die Box meldet ihn (`neue_tobies`, Ereignis `neu`). Auf der Startseite
   erscheint ganz oben die Karte „**Neuer Tobie auf Box Mond**. Gerade aufgelegt, vor 2 Minuten. Was soll er spielen? Tippe auf ein Hörspiel.“
   Der Reiter „Start“ bekommt einen roten Punkt. Die Seite ist offen oder wird geöffnet; es gibt **keine** Push-Nachricht (nicht verlangt).
2. **Tap 1:** auf die Cover-Kachel, z. B. „Lange Serie“ (Zuordnung `zuordnung/set`, Ziel `serie`). Die Karte wird grün:
   „**Fertig!** Dieser Tobie spielt jetzt „Lange Serie“.“ Knöpfe „Rückgängig“ (= `zuordnung/remove`), „Namen geben“ (Blatt mit einem Textfeld), „OK“.
   Ohne weiteres Tippen bleibt das Ergebnis gültig. „OK“ blendet die Karte aus.
3. Mehrere neue Tobies: mehrere Karten untereinander, neuester oben. Jede nennt die Box und die Zeit. Bei mehr als einer Karte steht darunter
   „Der zuletzt aufgelegte steht oben.“ Wer nicht sicher ist, legt den Tobie noch einmal auf (die Zeit „vor … “ wird aktualisiert, `neue_tobies` `aktualisiert`).
4. Kacheln: alle Hörspiele (ohne Überraschungs-Serie), dazu die Aktionskachel „**Gute Nacht**“ („Timer, dann still“). Bei mehr als 12 Hörspielen ein Suchfeld über den Kacheln.
   Die Aktion „Status“ (Box sagt den Zustand an) erscheint hier nicht; sie ist in „Für Tobias“ (offene Frage 5).
5. Unter den Kacheln, abgesetzt: „Das war ein Versehen, nicht merken“ (`neue_tobies/verwerfen`, mit Rückfrage „Nicht merken? Dieser Tobie spielt dann weiter die Überraschung. Legst du ihn noch einmal auf, taucht er wieder hier auf.“).
6. Fehler: Liste gesperrt → Kacheln grau, Band 5. `zuordnung_existiert` kann hier nicht vorkommen; kommt es doch (zwei Fenster), lädt die Seite neu und sagt: „Dieser Tobie wurde gerade woanders zugeordnet.“

Heute: 5 Taps plus Kennung lesen (`ist.md` Abschnitt 2).

### 6.2 (b) Hörspiel wählen → „Tobie dafür anlernen“ → auflegen: **2 Taps**

1. **Tap 1:** auf die Kachel des Hörspiels (Start oder Hörspiele).
2. **Tap 2:** auf „Auf Box Mond“ in der Karte „Tobie dafür anlernen“ (`lernmodus/start`; der Knopf je Box ersetzt die Boxauswahl, darum kein dritter Tap).
3. Die Seite wechselt zu „Tobie anlernen“ (`#anlernen`): Ring-Symbol (pulsiert, nicht bei „reduzierte Bewegung“), Überschrift „**Jetzt Tobie auf Box Mond legen**“,
   „Dieser Tobie soll „Lange Serie“ spielen. Ich warte noch 118 Sekunden.“ (Zähler aus `frist_bis`, wird nicht vorgelesen), Knopf „Abbrechen“ (= `lernmodus/abbrechen`).
4. *(Körperlich)* Tobie auflegen. Ereignis `lernmodus`/`zugeordnet`: grünes Häkchen, „**Erkannt!** Dieser Tobie spielt jetzt „Lange Serie“.“,
   Knöpfe „Noch einen Tobie anlernen“, „Fertig“ (zurück zum Hörspiel). Erscheint der neue Tobie auch unter „Tobies“: ja, ohne Namen.
5. Fälle:
   * Tobie hat schon ein Ziel (`rueckfrage`): Blatt „**Dieser Tobie spielt schon etwas.** Er spielt jetzt „Test-Serie“. Soll er stattdessen „Lange Serie“ spielen? Du hast dafür noch 10 Sekunden.“
     Knöpfe „Nein, so lassen“ (Vorgabe, Fokus), „Ja, ändern“ (= `lernmodus/antwort`). Zeit abgelaufen: „Das hat zu lange gedauert. Der Tobie spielt wie vorher.“ (+1 Tap).
   * Abgelaufen (`abgelaufen`): „**Kein Tobie erkannt.** Die Zeit ist abgelaufen. Lege den Tobie nach dem Start gleich auf die Box.“ „Noch einmal versuchen“ / „Zurück“.
   * Box lehnt ab (`box_lehnt_ab`, `zeit_unsicher`): „Box Mond kann gerade nicht lernen, weil sie die Uhrzeit nicht sicher kennt. Versuche es in ein paar Minuten noch einmal.“
   * Box aus (`box_offline`): Knopf schon vorher grau (4.3).
   * Läuft schon ein Lernvorgang: `lernmodus_laeuft`, Text in 5.1. Die Seite zeigt bei erneutem Öffnen einen offenen Vorgang weiter an (Abo `lernmodus`).

Heute: 5 bis 9 Taps (`ist.md`).

### 6.3 (c) Hörspiel hinzufügen: **2 Taps** (3 bei mehreren Dateien am Handy), Wartezeit ohne Tippen

1. **Tap 1:** „Hörspiel hinzufügen“ (Start oder Hörspiele).
2. **Tap 2:** „Dateien wählen“ (Handy: Dateiauswahl des Systems; Computer: dasselbe) oder „Ordner vom Computer wählen“ (`webkitdirectory`). Am Computer geht auch Hineinziehen.
3. Wurden **mehrere** Dateien gewählt, fragt ein Blatt **einmal**: „**Gehören die Dateien zu einem Hörbuch?** Wenn es Kapitel eines Hörbuchs sind, kommen sie zusammen in eine Folge.“
   „Nein, einzelne Folgen“ (Vorgabe, Fokus) / „Ja, ein Hörbuch“ (**Tap 3**, sendet `gruppe`). Bei einer Datei und bei einem Ordner entfällt die Frage
   (ein Ordner ist ein Hörbuch/Album, wenn die Tags es hergeben; die Tags entscheiden). Eine Auswahl der Zielserie gibt es hier nicht (Vorgabe „nach den Tags entscheiden“);
   wer aus einem Hörspiel heraus hochlädt (Knopf „Dateien in dieses Hörspiel“ auf der Hörspiel-Seite, ohne Tap-Mehraufwand) sendet `serie_id`.
4. Der Upload startet sofort. Je Datei oder Ordner eine Zeile unter „Gerade eben“:

   | Schritt | Anzeige |
   |---|---|
   | 1 | **„Wird hochgeladen … 37 %“** mit Balken (`role="progressbar"`), dreiteilige Leiste (Hochladen · Einsortieren · Fertig), erster Teil blau |
   | 2 | **„Wird einsortiert …“** (HTTP fertig bzw. `upload`/`fertig`; Eingang `wartet`/`bereit`/`laeuft`), zweiter Teil blau |
   | 3a | **fertig:** grüne Marke „fertig“, „Lange Serie · Folge 13“, Textknopf „Öffnen“ (`eingang` `neu_einsortiert` mit `pruefen=false`) |
   | 3b | **bitte kurz ansehen:** gelbe Karte „**Bitte kurz ansehen.** <Grund>“ mit Knöpfen „Ansehen“ (öffnet das Hörspiel) und „Passt so“ (`einsortierung/bestaetigen`) |
   | 3c | **geht nicht:** rote Karte „**Geht leider nicht.** <Grund und nächste Handlung>“ (Eingang `blockiert`, Upload-Fehler) |

   Das Ergebnis steht in dieser Liste **und** hängt nicht an der Sitzung: Die Seite lädt beim Öffnen `eingang/list` (`offen`, dazu `erledigt` der letzten Stunden) und zeigt auch Einträge, die vom NAS oder von einem anderen Gerät kamen,
   mit „vom NAS“ statt „vom Handy“. Sie bleiben, bis man sie mit „Passt so“ oder einem Tap auf „Öffnen“ erledigt hat. Das behebt den heutigen Befund „Ergebnis verschwindet beim Neuladen“.
5. **Gründe „bitte kurz ansehen“** (aus `pruefen_gruende`, Vertrag W 11.9; unbekannte Codes: „Hier stimmt etwas vielleicht nicht. Sieh es dir kurz an.“):

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
   `doppelt`: „Das gab es schon und wurde nicht noch einmal angelegt.“ Die Zeile erklärt, nicht den Code. „Entfernen“ eines blockierten Eintrags ist Admin-Sache („Für Tobias“).
6. **Zwei Uploads gleichzeitig** (Vertrag): Die Seite hält weitere Dateien in der Warteschlange („wartet“) und sendet sie nacheinander; kein 429 sichtbar.
7. **Abbrechen:** Zeile hat „Abbrechen“ solange hochgeladen wird (`AbortController`); danach „Abgebrochen. Die Datei wurde nicht gespeichert.“
8. **NAS-Weg:** Dateien, die jemand am Computer in den Eingang-Ordner kopiert, erscheinen in „Gerade eben“ ohne Hochladeschritt, direkt bei „Wird einsortiert …“ und enden wie oben.
   Der Hinweis dazu steht in 4.4.

Heute: 3 bis 5 Taps plus Suchen im Reiter „Eingang“.

### 6.4 (d) Abends: Gute Nacht und Leise-Zeiten: **2 Taps** bis zur Änderung (3 mit Speichern)

* Gute Nacht ändern: Startseite „**Abends**“ (**Tap 1**), Timer mit „+“ oder „−“ (**Tap 2**, je 5 Minuten; mehrere Taps, wenn weit weg vom Wunsch), „Speichern“ (**Tap 3**).
* Leise-Zeit hinzufügen mit Vorgabe (So–Do, 19:30–06:30, Still): „Abends“ (1), „+ Zeit hinzufügen“ (2), „Speichern“ (3). Andere Tage: +1 Tap (Schnellwahl „Jeden Tag“), andere Zeiten: +2 je Feld.
* Bestehende Zeit ändern: „Abends“ (1), „Ändern“ in der Zeile (2), Wert ändern, „Speichern“ (3+).
* Bei Wochenplan-Zeiten, die nur den Tag betreffen (Ferien): Tag-Knopf antippen, „Speichern“ (insgesamt 4).
* Der Gute-Nacht-Tobie wird wie jeder Tobie angelegt (6.1) mit der Kachel „Gute Nacht“. Das Starten des Timers von der Seite aus gibt es nicht (keine neue Funktion; offene Frage 3).

## 7. Zusammenfassung der Taps

| Aufgabe | Heute | Neu |
|---|---|---|
| (a) Unbekannten Tobie zuordnen | 5 bis 8 | **1** (Rückgängig: +1) |
| Tobie auf ein anderes Hörspiel umstellen | 6 bis 9 (zwei Bestätigungen) | **3** (Tobies, Zeile, Kachel; ohne Rückfrage, mit „Rückgängig“) |
| (b) Hörspiel → Tobie anlernen | 5 bis 9 | **2** (+1 bei „schon belegt“) |
| (c) Hörspiel hinzufügen | 3 bis 5 + Suchen | **2** (3 bei mehreren Dateien am Handy) |
| (c2) „bitte prüfen“ bestätigen | 3 bis 7 | **1** („Passt so“ in der Zeile) |
| (d) Gute Nacht ändern | 3 + Tippen | **3** (Abends, +/−, Speichern) |
| (d) Leise-Zeit hinzufügen | 3 bis ca. 12 | **3** mit Vorgabe, sonst 4 bis 6 |
| Status der Boxen | 1 (nur Technik, ohne „spielt gerade“) | **0** (steht auf der Startseite) |

## 8. Bereich „Für Tobias“: wohin jede heutige Funktion wandert

Alles bleibt, wie es heute funktioniert (Befehle unverändert); nur Ort und Text ändern sich. Rechte siehe Abschnitt 9.

| Heute (Fundort in `ist.md`) | Neu | Wer |
|---|---|---|
| Reiter „Serien“: Liste der Serien | Reiter „Hörspiele“ (Kacheln) | alle |
| „Hochladen“-Karte (Vorgabe-Serie, „ein Hörbuch“-Häkchen, Dateiliste, „Liste leeren“) | „Hörspiel hinzufügen“ (6.3); Vorgabe-Serie über „Dateien in dieses Hörspiel“ auf der Hörspiel-Seite; „Liste leeren“ wird „Erledigte ausblenden“ | alle |
| „Neue Serie“ (leere Serie anlegen) | Für Tobias → Hörspiele aufräumen → „Neues leeres Hörspiel“ | Admin |
| Überraschungs-Serie (Hinweise, „anlegen“) | Für Tobias → Hörspiele aufräumen (Satz: „Die Überraschung spielt die Box bei unbekannten Tobies.“) | Admin |
| „Freigabe prüfen“ | Für Tobias → Hörspiele aufräumen → „Medien neu einlesen“; läuft zusätzlich beim Öffnen der Seite wie heute (`medien/pruefen`) | Admin (Auslöser beim Öffnen: Befehl für alle, Abschnitt 9) |
| Serie umbenennen | Hörspiel → „Name ändern“ | alle |
| „Alles geprüft“ / „Geprüft“ (`einsortierung/bestaetigen`) | „Passt so“ (Hörspiel-Seite und Liste „Gerade eben“) | alle |
| Folge umbenennen | Hörspiel → Zeile → „Name ändern“ | alle |
| Folge hoch/runter (und Ziehen) | Hörspiel → „Reihenfolge ändern“ (▲ ▼, kein Ziehen) | alle |
| Folge verschieben | Hörspiel → Zeile → Blatt „Mehr …“ → „In anderes Hörspiel verschieben“ (abgesetzt) | Admin |
| Folge löschen (rot in der Zeile) | Hörspiel → Zeile → Blatt „Mehr …“ → „Folge in den Papierkorb …“ (abgesetzt, ganz unten) | Admin |
| Serie löschen | Hörspiel → „Aufräumen“ → „Hörspiel in den Papierkorb …“ | Admin |
| Serien zusammenführen | Hörspiel → „Aufräumen“ → „Zusammenführen …“ | Admin |
| Reiter „Eingang“ (Im Eingang / Einsortiert, Einträge, Hinweise) | Alltag: „Gerade eben“ in „Hörspiel hinzufügen“. Voll: Für Tobias → Eingang im Detail (Filter, alle Einträge, Hinweiscodes, „Mehr laden“) | alle / Admin |
| „Erneut einsortieren“, „Sofort, ohne Wartezeit“ | Für Tobias → Eingang im Detail; „Erneut einsortieren“ zusätzlich als „Jetzt prüfen“ in „Gerade eben“ | Admin / alle |
| „Entfernen“ eines Eingangseintrags (rot) | Für Tobias → Eingang im Detail | Admin |
| Reiter „Tobies“: „Neue Tobies“ | Karte „Neuer Tobie“ auf der Startseite (6.1) | alle |
| „Verwerfen“ | „Das war ein Versehen, nicht merken“ | alle |
| „Zuordnen“ (Serie / einzelne Folge / Aktion) | Serie und „Gute Nacht“: Kachel (6.1). Einzelne Folge, Aktion „Status“: Für Tobias → Tobies im Detail → „Zuordnen (alle Möglichkeiten)“ mit dem heutigen Dialog | alle / Admin |
| Lernmodus („Neuen Tobie lernen“) | Hörspiel → „Tobie dafür anlernen“ (6.2); Auswahl „Einzelne Folge“ weiter über Für Tobias → Tobies im Detail | alle / Admin |
| „Kennung von Hand eingeben“ | Für Tobias → Tobies im Detail | Admin |
| Zugeordnete Tobies: „Name“, „Ziel ändern“, „Lösen“ | Reiter „Tobies“: „Namen ändern“, „Anderes Hörspiel“, „Diesen Tobie vergessen …“ | alle |
| Zugeordnete Tobies: Kennung, „Folge fehlt“ / „Serie fehlt“ | Für Tobias → Tobies im Detail (Kennung, Ziel, Fehlmarken). Im Alltag: „Das Hörspiel fehlt. Wähle ein anderes.“ rot in der Zeile | Admin / alle |
| Reiter „Boxen“: Karte je Box (Punkt, online, Liste-Stand, Speicher, Netz, Akku, Version, Sync, letzter Fehler, Meldungen) | Alltag: Status-Satz auf Start (4.1.1). Voll: Für Tobias → Boxen im Detail (genau die heutige Karte, Rohwerte bleiben) | alle / Admin |
| „Sync jetzt“ | Für Tobias → Boxen im Detail | Admin |
| Karte „Liste der Tobies“ (Revision, Export), „Export ansehen“, „Liste neu ausrollen“ | Für Tobias → Liste, Sicherung, Export (Begriffe wie heute, dazu eine Zeile Erklärung) | Admin |
| Warnleisten `leer_neu`, `export_neuer`, „Sicherung fehlt“, „Box neuer“ | Admin: oben auf jeder Seite wie heute; zusätzlich in Für Tobias → Liste. Nicht-Admin: Band „Änderungen sind gerade gesperrt. Bitte Tobias Bescheid sagen.“ | Admin / alle sehen Hinweis |
| Reiter „Korb“ (Papierkorb, Wiederherstellen, „In andere Serie“, leeren) | Für Tobias → Papierkorb | Admin |
| Einstellungen → Leise-Zeiten | Reiter „Abends“ (Wochenplan, 4.6); Zeitzone: Für Tobias → Weitere Einstellungen | alle / Admin (Zeitzone) |
| Einstellungen → Gute Nacht (Timer, Ausblenden) | Reiter „Abends“ | alle |
| Einstellungen → Lesezeichen (Tage) | Für Tobias → Weitere Einstellungen (Satz: „Wurde ein Tobie so viele Tage nicht gespielt, beginnt er die Folge wieder von vorn. 0 heißt: nie.“) | Admin |
| Upload-Grenze (Einrichtung der Integration, nicht in der Seite) | unverändert dort; die Seite zeigt die Grenze (aus `hello.grenzen`) | – |
| „Integration 0.1.0“ (Fußzeile) | Für Tobias → Meldungen der Boxen (Fuß) | Admin |
| „Letzte Meldungen“ je Box (rohe Art, Text) | Für Tobias → Meldungen der Boxen | Admin |
| HA-Entitäten (Akku, spielt gerade …), HA-Aktionen | unverändert in HA; die Alltagsseite zeigt dieselben Werte (4.1.1) | – |
| Backend: Update-Knopf (später) | Für Tobias → Boxen im Detail | Admin |

## 9. Rechte: wer darf was

### 9.1 Was nötig ist

1. **Panel für alle sichtbar:** In `__init__.py` `require_admin=False` (heute `True`) beim `panel_custom.async_register_panel`.
   Danach erscheint „Tobi Box“ für jeden angemeldeten HA-Benutzer in der Seitenleiste (jeder kann sie in seinem Profil ausblenden).
2. **Seite blendet „Für Tobias“ nur für Administratoren ein** (`hass.user.is_admin` bzw. `hello.rechte.admin`). Das ist Komfort, **keine Sicherheit**.
3. **Backend prüft je Befehl.** `websocket_api.befehl(..., admin=False)` wird zu `recht="lesen" | "alltag" | "admin"`:
   `lesen` und `alltag` ohne Dekorator (nur angemeldet, wie heute alles Lesen), `admin` mit `@websocket_api.require_admin`.
   Der Upload (`http.py`) behält `requires_auth`, verliert `@require_admin` und prüft nichts weiter (Alltag).
4. **Gemischter Befehl `einstellungen/set`:** Recht `alltag`, aber im Befehl: Ändert er `leise_zeiten.zeitzone` oder `lesezeichen_tage` und ist der Benutzer kein Administrator,
   Fehler `unauthorized`. Gute Nacht und Leise-Fenster darf jeder ändern. Die Seite sendet die Zeitzone unverändert mit; gleicher Wert gilt als nicht geändert.
5. **Reine Lesende Benutzer:** HA kennt in der Oberfläche nur „Administrator“ und „Benutzer“. Ein Benutzer mit eingeschränktem Zugriff existiert in diesem Haushalt nicht; der Entwurf nimmt an, dass jeder normale Benutzer ein Elternteil ist (offene Frage 1).

### 9.2 Vorschlag: Befehle für Nicht-Administratoren

| Stufe | Befehle (Nr. aus Vertrag W) |
|---|---|
| **lesen** (wie heute, alle) | 1 `hello`, 2 `subscribe`, 3 `serien/list`, 4 `serie/get`, 10 `papierkorb/list`, 13 `neue_tobies/list`, 15 `zuordnung/list`, 21 `boxen/list`, 29 `eingang/list`, 31 `konfig/export_lesen`, 34 `konfig/get`, 35 `einstellungen/get` |
| **alltag** (neu für alle angemeldeten Benutzer) | 16 `zuordnung/set` (inkl. Name), 17 `zuordnung/remove`, 14 `neue_tobies/verwerfen`, 18 `lernmodus/start`, 19 `lernmodus/antwort`, 20 `lernmodus/abbrechen`, 6 `serie/rename`, 25 `folge/rename`, 7 `folgen/order`, 28 `einsortierung/bestaetigen`, 9 `medien/pruefen`, 30 `eingang/sortieren` (auch `sofort`), 36 `einstellungen/set` (ohne Zeitzone und Lesezeichen-Tage), HTTP-Upload `POST /api/tobibox/upload`, HTTP-Cover (neu, W-1) |
| **admin** (bleibt) | 5 `serie/create`, 8 `folge/delete`, 24 `serie/delete`, 26 `folge/verschieben`, 27 `serien/zusammenfuehren`, 11 `papierkorb/restore`, 12 `papierkorb/empty`, 33 `eingang/entfernen`, 22 `box/sync`, 23 `liste/neu_ausrollen`, 32 `konfig/aus_export`, `einstellungen/set` für Zeitzone und Lesezeichen-Tage, später Update |

Begründung: „alltag“ sind genau Dinge, die Verena selbst tun soll (Brainstorm) und die **nichts endgültig zerstören**: Zuordnungen lassen sich neu anlernen,
Namen und Reihenfolge ändern, Einsortieren legt nur Dateien an. Alles, was Dateien löscht, die Medienstruktur umbaut, Boxen anweist oder die ganze Liste ersetzt, bleibt bei Tobias.
`zuordnung/remove` ist „alltag“, damit „Diesen Tobie vergessen“ und „Rückgängig“ gehen (offene Frage 2).
`medien/pruefen` und `eingang/sortieren` laufen beim Öffnen der Seite; sie dürfen daher nicht Admin sein, sonst bekäme jede Seite von Verena einen Fehler.
Die Tests prüfen die Tabelle (Abschnitt 12).

### 9.3 Folgen für den Vertrag und die Texte

* Vertrag W Abschnitt 2.1 („Wer darf was“): Tabelle ersetzen durch 9.2. Begründung steht dort ebenfalls (Haushalt mit zwei Erwachsenen, Entscheidung D „nur Tobias als Benutzer“ ist überholt, Tobias entscheidet).
* `hello.darf_schreiben` bleibt (heißt weiter: Administrator) und bekommt Geschwister (W-4).
* HA-Aktionen (`services.yaml`) sind unverändert und bleiben Administratoren vorbehalten (HA prüft das selbst nicht; das ist heute schon so).

## 10. Nötige Änderungen am Vertrag W (Vorschlag, Version 1.2, `v` bleibt 1)

Alle Änderungen sind **additiv** (Vertrag Abschnitt 9: neue Felder, Befehle, Fähigkeiten, Codes). Eine Ausnahme ist die Lockerung der Rechte (W-4), die die Projektleitung beschließt.
Die Seite sendet neue Felder nur, wenn `hello.faehigkeiten` sie zusagt. Neue Fähigkeiten: `cover`, `box_anzeigenamen`, `rechte_stufen`.

**W-1 Cover (Fähigkeit `cover`)**

* *Serie-Kurzform* (Abschnitt „Gemeinsame Objekte“) bekommt zwei Felder:
  > `cover_url` (string oder `null`): relative, **signierte** Adresse des Covers, z. B. `/api/tobibox/cover/<serie_id>?authSig=…`, **gültig 1 Stunde** (`hass.auth.async_sign_path`).
  > `null`, wenn die Serie kein Cover hat; die Seite zeichnet dann den Platzhalter (Farbe aus `id`, Anfangsbuchstabe).
  > `cover_stand` (string, 8 Zeichen `[0-9a-f]`): Fingerabdruck der Bilddatei; ändert sich das Bild, ändert sich der Wert (zum Zwischenspeichern und Neuladen).
* *Neuer HTTP-Endpunkt* `GET /api/tobibox/cover/<serie_id>`: liefert `image/jpeg`, höchstens 512 × 512 Pixel, höchstens 150 KiB; Antwort mit `ETag` (= `cover_stand`) und
  `Cache-Control: private, max-age=86400`. Zugriff: gültige Signatur **oder** `Authorization: Bearer`; Rechte: alle (Stufe lesen). 404 `cover_nicht_gefunden`.
  (`<img>` kann keinen Bearer-Header senden, darum die Signatur; die Seite lädt `serien/list` bei jedem Öffnen und alle 45 Minuten neu, sodass die Adressen nie ablaufen.)
* *Woher das Bild kommt:* Beim **Einsortieren** (Abschnitt 11) liest die Integration mit `ffprobe`/`ffmpeg` das eingebettete Bild (ID3 `APIC`, MP4 `covr`, FLAC `PICTURE`) der **ersten Folge**, die eines hat,
  und legt es, verkleinert auf höchstens 512 px und als JPEG, **im Serien-Ordner als `cover.jpg`** ab. Je **Serie** ein Cover (nicht je Folge). Ein vorhandenes `cover.jpg` wird nicht überschrieben.
  `medien/pruefen` holt fehlende Cover für bestehende Serien nach (einmaliger Durchlauf, im Hintergrund, höchstens eine Serie je Sekunde).
  Fehlt das eingebettete Bild oder ist es kaputt: kein Cover, **kein Fehler**.
* *Zu prüfen beim Bau:* `cover.jpg` im Serien-Ordner darf den Sync der Box, die Einsortierung und `medien/pruefen` nicht stören (Bilder werden dort schon als „ignoriert“ geführt, Abschnitt 11/12); ggf. `cover.jpg` zum reservierten Dateinamen machen (Abschnitt 12).
* *Optional, nicht in Stufe 1* (offene Frage 7): eigenes Foto je Hörspiel: `POST /api/tobibox/cover/<serie_id>` (Alltag), Bild bis 5 MiB, wird zu `cover-eigen.jpg`; hat Vorrang vor `cover.jpg`.

**W-2 Status „spielt gerade“ in der Seite.** Die Daten gibt es schon: `boxen/list` und Ereignis `boxen`/`geaendert` liefern `status.zustand`, `status.serie`, `status.folge`, `status.akku_prozent`, `status.lader`
(`mqtt-v1.md` 3.3). **Keine Vertragsänderung**, nur eine Festlegung für die Seite: Sie zeigt den Satz aus 4.1.1 und schlägt die Serie über `status.serie.id` in `serien/list` nach.
Einzige Voraussetzung: Das Ereignis `boxen`/`geaendert` kommt bei jeder Änderung von `status.zustand`, `status.serie`, `status.folge`, `lader` und `akku_prozent` (heute: bei jeder Änderung von `status`, passt schon).

**W-3 Anzeigenamen der Boxen (Fähigkeit `box_anzeigenamen`)**

* Einrichtung der Integration (`config_flow.py`, Optionen, `strings.json`, `translations/de.json`): neues Feld je Box **„Anzeigename“** („Wie soll die Box in der Oberfläche heißen? Zum Beispiel „Box Mond“. Leer = der Name der Box.“), maximal 40 Zeichen.
  Gespeichert in den Optionen als `box_anzeigen` (Objekt Boxname → Anzeigename). Im Repo steht kein echter Name.
* *Box-Objekt* (`boxen/list`, Ereignis `boxen`) bekommt das Feld
  > `anzeige` (string, **nie** `null`): der Anzeigename aus den Optionen; fehlt er, `anzeigename` (Gerätename aus der Discovery), fehlt auch der, der Box-Name `box`.
  `anzeigename` bleibt unverändert (Discovery). `hello.boxen` bleibt ein Array von Box-Namen; neu `hello.box_anzeigen`: Objekt Box-Name → `anzeige`.
  Ändert Tobias die Namen in den Optionen, gilt es nach dem Neuladen der Integration (wie alle Optionen heute).
* Die Seite zeigt **nur** `anzeige`. Der Box-Name (`box1`) steht höchstens in „Für Tobias“.

**W-4 Rechte je Befehl (Fähigkeit `rechte_stufen`)**

* Abschnitt 2.1: Tabelle ersetzen durch die Stufen **lesen / alltag / admin** aus 9.2. Fehler für zu wenig Recht: weiter `unauthorized`.
* `hello` bekommt `rechte`: `{"admin": <bool>, "alltag": <bool>}` (`alltag` ist `true` für jeden angemeldeten Benutzer, außer das Backend schränkt es künftig ein). `darf_schreiben` bleibt, Bedeutung „Administrator“.
* Übersichtstabelle: Spalte „Rechte“ enthält `alle`, `Alltag`, `Admin` statt `alle` / `Admin`.
* `einstellungen/set`: Der Teil „Rechte“ lautet: „Alltag. Ändert er `leise_zeiten.zeitzone` oder `lesezeichen_tage` gegenüber dem gespeicherten Wert, ist er `admin`; sonst `unauthorized`. Es wurde nichts geändert.“
* Upload (Abschnitt 5.1 und 2.1): „Rechte: Alltag (jeder angemeldete Benutzer).“ Der Satz zur Administrator-Prüfung (W-19) entfällt.
* Panel: „Die Seite in der Seitenleiste ist für **alle** angemeldeten Benutzer sichtbar (`require_admin=False`). „Für Tobias“ blendet die Seite nur für Administratoren ein; das Backend prüft jeden Befehl.“

**W-5 Kleinigkeiten, die die Seite braucht** (alle additiv, bei Bedarf in den Bau-Arbeitspaketen als „nur wenn nötig“)

* `eingang/list`, `neu_einsortiert`: schon vorhanden (`ergebnis`, `pruefen_gruende`). Neu nur: Feld `quelle` im Eingangs-Eintrag, `upload` oder `nas`, damit die Seite „vom Handy“ / „vom NAS“ zeigt. Wenn das nicht billig geht, zeigt die Seite „vom Handy“ nur für Uploads dieser Sitzung und sonst nichts.
* `zuordnung/list`: Eintrag trägt `ziel` (heute vorhanden); für die Anzeige „spielt „Lange Serie“ · Folge 4“ löst die Seite Serien- und Folgennamen selbst über `serien/list` und `serie/get` auf (keine Änderung).

## 11. Barrierefreiheit, Gefahrloses, Reihenfolge

* **Tap-Ziele:** mindestens 44 × 44 px (geprüft im Prototyp bei 390 und 1280 px; Ausnahme nur Textlinks im Fließtext).
* **Kontrast:** Text mindestens 4,5:1, große Schrift und Symbole 3:1, in Hell und Dunkel (Prototyp geprüft; echte Farben kommen aus HA, der Bau prüft mit Script).
  Farbe nie allein: Zustände haben Text („bitte ansehen“, „fertig“, „Still/Leiser“).
* **Fokus:** sichtbarer Rand (3 px) an allem; Tab-Reihenfolge wie die Sichtreihenfolge; nach Dialogen kehrt der Fokus zum auslösenden Knopf zurück.
  Dialoge: `role="dialog"`/`alertdialog`, `aria-modal`, Fokusfalle, Esc schließt, Fokus beim Öffnen auf die **harmlose** Antwort („Abbrechen“, „Nein, so lassen“).
* **Screenreader:** Ein `aria-live`-Bereich sagt Ergebnisse an („Fertig. Dieser Tobie spielt jetzt Lange Serie“; „Geschichte_ohne_Tags.mp3: bitte kurz ansehen“). Fortschrittsbalken haben `role="progressbar"` mit Wert und Namen.
  Cover sind `aria-hidden` (der Name steht daneben); Tag-Knöpfe `aria-pressed`; Gruppen mit `aria-labelledby`. Der Wochenplan hat eine Textbeschreibung.
* **Schriftgröße:** Alles in `rem`/relativ, Seite bleibt bei 200 % Browser-Zoom benutzbar (Kacheln brechen um, kein waagerechtes Scrollen bei 390 px und bei 320 px).
* **Bewegung:** `prefers-reduced-motion`: kein Pulsieren, keine Übergänge.
* **Sprache:** Uhrzeiten 24 Stunden, Zahlen und Datum „12.11., 08:30“ (nicht nach Browsersprache). Datei-Auswahlfenster ist System-Text und lässt sich nicht ändern.
* **Löschen:** nur mit Rückfrage und rot; die Rückfrage nennt, was geschieht und was bleibt („Tobias kann es aus dem Papierkorb zurückholen“). Löschknöpfe stehen **nie in einer Reihe mit häufigen Knöpfen**:
  in einer eigenen, durch Linie und Abstand (mindestens 32 px) abgesetzten Karte oder am Blattende als Textknopf, nicht in der Zeile einer Folge, nicht neben „Speichern“.
  „Rückgängig“ statt Rückfrage überall dort, wo es sich zurückdrehen lässt (Zuordnen, Umstellen).
* **Reihenfolge ohne Ziehen:** ▲/▼ (Computer zusätzlich Ziehen und die Tasten Alt+↑/↓ als Zugabe); nach dem Verschieben bleibt der Fokus auf dem Knopf der verschobenen Folge.
* **Doppeltippen:** Knöpfe, die etwas senden, sind während des Aufrufs gesperrt (`anfrage_id` bei den Befehlen, die sie kennen).

## 12. Arbeitspakete für den Bau (Sonnet, billigstes passendes Modell)

Reihenfolge so, dass jeder Schritt allein testbar ist. Vor dem Bau: Goldfische, Resolve (Schritte 3 und 4).

| AP | Inhalt | Modell | Tests |
|---|---|---|---|
| U0 | **Vertrag W 1.2** einarbeiten (W-1 bis W-5), Tobias gibt frei; `docs/protocol/ha-websocket-v1.md`, ggf. `docs/data-model.md` (nur falls `cover.jpg` reserviert wird) | Sonnet (Änderung nur nach Freigabe) | – |
| U1 | **Rechte:** `befehl(recht=…)`, `einstellungen/set`-Prüfung, Upload ohne `require_admin`, `hello.rechte`, `require_admin=False` im Panel | Sonnet | `tests/test_websocket_api.py`: Tabelle 9.2 als Parametertest, je Befehl mit Admin-Benutzer und Normal-Benutzer; `einstellungen/set` mit Zeitzone/Lesezeichen als Nicht-Admin = `unauthorized`; `tests/test_upload.py`: Nicht-Admin 200; `tests/test_init.py`: Panel ohne `require_admin` |
| U2 | **Anzeigenamen:** Optionen-Schritt, `strings.json` und `translations/de.json`, `boxen/list`-Feld `anzeige`, `hello.box_anzeigen` | Haiku (Formular) + Sonnet (Hub) | `tests/test_config_flow.py`, `tests/test_websocket_api.py` (Reihenfolge der Rückfälle) |
| U3 | **Cover:** Extraktion beim Einsortieren, Nachhol-Durchlauf, HTTP-Ansicht mit Signatur, `cover_url`/`cover_stand` | Sonnet | neue `tests/test_cover.py` (ffmpeg-Fixture mit MP3 mit/ohne Bild, kaputtes Bild, Neuladen, Signatur abgelaufen = 401, Größe/Format); Test, dass `cover.jpg` Sync und Einsortierung nicht stört |
| U4 | **Panel-Gerüst:** Reiter (unten/oben), Kopf mit `ha-menu-button`, Routen (`#start` …), Theme-Variablen, Zustände (lädt/leer/Fehler/offline), Meldungen, Dialog-/Blatt-Komponente mit Fokusfalle, Texttabellen (Fehler, Gründe) in einer Datei `texte.js` | Sonnet | jsdom: Reiter und Routen, Rolle Nicht-Admin sieht kein „Für Tobias“, Zustände, Fokus nach Dialog; vorhandene Tests in `panel.test.mjs` sind **anzupassen**, nicht zu löschen |
| U5 | **Start und Hörspiele:** Status-Karten (Sätze 4.1.1), Kachel-Raster mit Platzhalter-Cover, Hörspiel-Seite, Suche | Sonnet | jsdom: Satz-Tabelle (alle Zustände), Platzhalterfarbe stabil, Cover-URL erneuert |
| U6 | **Neuer Tobie und Tobies:** Karte, Kachel-Zuordnung mit Rückgängig, Verwerfen, Tobies-Liste und Blatt, Aktionskachel „Gute Nacht“ | Sonnet | jsdom mit `mock-hass.mjs`: Ereignis `neu` → Karte; Tap → `zuordnung/set`; Rückgängig → `zuordnung/remove`; gesperrte Liste |
| U7 | **Anlernen:** Seite `#anlernen`, Zustände aus Abo `lernmodus`, Rückfrage, Ablauf, Wiederaufnahme eines offenen Vorgangs | Sonnet | jsdom: alle Zustände aus Vertrag 4.3 → Text (Tabelle 6.2) |
| U8 | **Hörspiel hinzufügen:** Dateien/Ordner/Ziehen, Hörbuch-Frage, Warteschlange (2 parallel), Fortschritt, Eingang-Anbindung, Gründe-Texte, NAS-Einträge | Sonnet | jsdom: Fortschrittsschritte, „bitte kurz ansehen“, Upload-Fehlercodes, Abbruch, Wiederaufnahme nach Neuladen |
| U9 | **Abends:** Gute Nacht (Stepper), Wochenplan (Balken, Mitternacht), Blatt mit Auswahlfeldern 24 h, Prüfregeln | Sonnet | `panel_quiet.test.mjs` anpassen; neu: Mitternachtsbalken, 24-Stunden-Auswahl, krumme Minute bleibt, Fehlerstelle in Worten |
| U10 | **Für Tobias:** heutige Reiter als aufklappbare Karten umziehen (Eingang, Papierkorb, Liste, Boxen, Einstellungen, Meldungen, Tobies im Detail, Aufräumen); Warnleisten; Löschen abgesetzt | Sonnet | die bestehenden Tests dieser Funktionen laufen unverändert gegen die neuen Orte (Selektoren anpassen) |
| U11 | **Barrierefreiheit:** Prüfliste 11 abarbeiten; automatisierter Check (Tap-Ziele ≥ 44 px, Kontrast, kein waagerechtes Scrollen bei 320/390/1280 px, Hell/Dunkel) mit Playwright, Screenshots für Tobias | Sonnet | Playwright-Skript im Repo unter `homeassistant/tests/frontend/`, optional ausgeführt |
| U12 | **Doku:** `homeassistant/README.md` (Seite für alle, Anzeigenamen, Cover), `docs/betrieb/`-Kurzanleitung „Für Verena“ (Bilder aus Prototyp) | Haiku | Abgleich der Texte mit `texte.js` |
| U13 | **Abnahme mit Tobias**, Schritt für Schritt im Chat (Mac, Handy, Browser): Tobie zuordnen (a, b), Hörspiel hinzufügen vom Handy, Abends | Projektleitung + Tobias | – |

Bestehende Tests: `homeassistant/tests/frontend/panel.test.mjs`, `panel_quiet.test.mjs` (`node --test homeassistant/tests/frontend`) und die HA-Tests
(`homeassistant/tests/`, `pytest`) müssen nach **jedem** AP grün sein. Die jsdom-Tests prüfen Befehle und Texte, nicht Pixel.

## 13. Offene Fragen für Tobias (mit Empfehlung)

| Nr. | Frage | Empfehlung |
|---|---|---|
| 1 | Sind alle normalen HA-Benutzer Eltern, denen „alltag“ (9.2) zusteht? | Ja. Alltag nur für Erwachsene; Kinder haben kein HA-Konto. |
| 2 | Darf Verena einen Tobie „vergessen“ (`zuordnung/remove`) und ein Hörspiel **nicht** löschen? | Ja, so wie in 9.2. Hörspiele löschen nur Tobias; Verena meldet es. |
| 3 | Gute Nacht von der Seite starten („Gute Nacht jetzt“)? Wäre eine neue Funktion (neuer MQTT-Befehl). | Nein, nicht in dieser Stufe. Gute Nacht bleibt am Tobie. |
| 4 | Einzelne **Folge** als Ziel eines Tobies in der Alltagsseite? | Nein; nur in „Für Tobias“. Ein Tobie gehört im Alltag zu einem ganzen Hörspiel. |
| 5 | Aktion „Status“ (Box sagt den Zustand an) als Kachel? | Nur in „Für Tobias“. Den Zweck kennt die Seite nicht; neue Funktionen sind nicht Ziel. |
| 6 | Sortierung der Hörspiele: nach Name, nach zuletzt gespielt oder von Hand? | Nach Name. „Zuletzt gespielt“ kennt die Seite nicht (keine Daten). |
| 7 | **Eigenes Foto** als Cover (Brainstorm: „eigenes Foto hochladbar“) schon in Stufe 1? | Nein, erst nach der Abnahme (U3 ohne `cover-eigen.jpg`). Bis dahin Platzhalter, wenn keine Tags. |
| 8 | Cover je Hörspiel (erste Folge mit Bild) oder je Folge? | Je Hörspiel (einfacher, reicht für Kacheln). Je Folge nur bei Bedarf später. |
| 9 | Push-Hinweis (Handy) „Neuer Tobie“? | Nein. Die Seite zeigt es, wenn sie offen ist. Die HA-App kann später eine Automation nutzen. |
| 10 | Soll „Sync jetzt“ (Box sofort abgleichen) für Verena sichtbar sein, etwa wenn neue Hörspiele noch nicht auf der Box sind? | Vorerst Admin. Stattdessen sagt die Statuskarte „Neue Zuordnungen kommen auf die Box, sobald …“. Neu abwägen nach dem ersten Alltag. |
| 11 | Eine Seite für alle oder zwei Seitenleisten-Einträge („Tobi Box“, „Tobi Box – Technik“)? | **Eine Seite** (Abschnitt 9); ein zweiter Eintrag würde Technik doppelt sichtbar machen. Sicherheit liegt im Backend, nicht in der Seitenleiste. |
| 12 | Wörter „Hörspiel“ für alles (auch Hörbücher)? | Ja, ein Wort. „Hörbuch“ nur bei der Frage „Gehören die Dateien zu einem Hörbuch?“. |
| 13 | Zeiten der Leise-Zeiten in 5-Minuten-Schritten (heute beliebige Minute)? | Ja, 5-Minuten-Schritte; vorhandene krumme Werte bleiben erhalten. |

## 14. Was der Prototyp zeigt und was nicht

`prototyp.html` ist eine **Vorschau**, kein Code für den Bau. Er zeigt: Start (Status-Karten, „Neuer Tobie“ mit Fertig-Karte, große Knöpfe, Kacheln), Hörspiel-Seite mit „Tobie dafür anlernen“ und
dem Ablauf bis „Erkannt“ (mit Knöpfen „Nur Vorschau“ für Erkennen und „schon belegt“), „Hörspiel hinzufügen“ mit simuliertem Fortschritt (Handy, Ordner, „bitte kurz ansehen“, „geht nicht“),
Tobies, Abends (Gute Nacht, Wochenplan, Blatt zum Ändern, Löschen mit Rückfrage), „Für Tobias“ (angedeutet) und die Zustände (lädt, leer, Fehler, Verbindung weg).
Der Prototyp hat eigene Farben (HA-ähnlich); im echten Panel kommen sie aus den HA-Variablen. Er schickt nichts an Home Assistant.
Geprüft mit Chromium bei 390 und 1280 px, hell und dunkel: kein waagerechtes Scrollen, alle Knöpfe, Auswahlfelder und Reiter mindestens 44 px hoch, Kontraste mindestens 4,5:1.
Die Reiter erscheinen im Prototyp dort, wo sie im Panel stehen werden: unten am Handy, oben am Computer.
