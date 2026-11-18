# Online-Suche für Cover und Angaben („wie bei Plex“): Concepts Brief (EGM Schritt 1)

Stand 14.11., geprüft am 18.11. (Abschnitt 7; die dort offenen Fragen sind in Abschnitt 8 beantwortet) · Anlass: Tobias nach dem ersten großen Befüllen der Bibliothek (282 Einträge, davon 260 „bitte ansehen“,
234 Arten geraten): „Bei allen, die ich jetzt hochgeladen habe, gefallen mir die Bilder nicht, und die Infos sind auch
nicht perfekt.“

## 1. Problem

Die Bibliothek nimmt Namen, Art und Cover nur aus den Dateien (Tags, Ordnernamen, eingebettete Bilder). Bei gekauften
oder gesammelten Kinderhörspielen sind diese Angaben oft schlecht: Serien heißen nach Sprechern oder Autoren,
Folgentitel wiederholen den Seriennamen oder tragen Zusätze („(Das Original-Hörspiel zur TV-Serie)“), Nummern fehlen,
Arten sind geraten, Cover fehlen oder sind unscharf. Von Hand alles zu korrigieren ist bei Hunderten Einträgen zu viel.

## 2. Entscheidungen aus dem Brainstorm (Tobias, 14.11.)

| Nr. | Frage | Antwort |
|---|---|---|
| O1 | Was liefert die Suche? | **Cover, Namen (Serie, Folgentitel, Nummer) und zusätzlich Beschreibung bzw. Altersangabe** zum Anzeigen (1c) |
| O2 | Wie arbeitet sie? | **Beides** (2c): von Hand je Eintrag („⋯“ → „Online suchen“, Treffer mit Cover, einen antippen) **und** automatisch beim Einsortieren, mit „bitte ansehen“, wenn der Treffer unsicher ist |
| O3 | Quelle | **iTunes-Suche von Apple** (kostenlos, ohne Konto). In Kauf genommen: HA schickt Titel der Hörspiele an Apple |
| O4 | Cover auf die Boxen? | **Nein**, bleibt so (U8): Cover und Beschreibung sind nur für die HA-Seite |

## 3. Was schon feststeht (Messung der Projektleitung, 14.11.)

- Die iTunes-Suche (`https://itunes.apple.com/search?country=de&media=all&term=…`) findet deutsche Kinderhörspiele gut:
  z. B. „Benjamin Blümchen, Folge 109: Benjamin als Baggerfahrer“, „Gigantosaurus – Folge 1: Mazus Mutprobe“, „Zippel,
  das wirklich wahre Schlossgespenst“, mit Künstler, Genre und Cover-URL (bis ca. 1000 × 1000 px durch Ändern der Größe
  in der URL). MusicBrainz fand im selben Test weniger.
- Grenzen: Apple drosselt bei ca. 20 Anfragen je Minute; es gibt keine Garantie und keinen Vertrag. Treffer sind
  Alben/Hörbücher/Titel, keine „Serien“ – die Serie muss aus Künstler und Titel abgeleitet werden.
- Eine Durchsicht der vorhandenen 282 Einträge mit dieser Quelle läuft als Vorschlagsliste (Projektleitung), bevor die
  Funktion gebaut wird; sie zeigt, wie gut das Ableiten von Serie, Titel und Nummer klappt.

## 4. Grenzen

- Nur HA-Seite und Integration; Box, `mqtt-v1.md` und Sync bleiben unverändert (Cover und Beschreibung gehen nicht auf
  die Boxen).
- Eigene Eingaben gehen vor: Was jemand von Hand umbenannt, als Art gesetzt oder als Cover hochgeladen hat, überschreibt
  die Automatik nie.
- Vertragsänderungen (neue Befehle, neue Felder wie Beschreibung und Alter) nur nach Freigabe durch Tobias (Stufe 0).

## 5. Weitere Entscheidungen (Tobias, 14.11.)

| Nr. | Frage | Antwort |
|---|---|---|
| O5 | Nachholen für die vorhandene Bibliothek? | **Ja**, einmal über alle Einträge (die Vorschlagsliste der Projektleitung ist der erste Lauf zum Ansehen) |
| O6 | Ab wann ohne Nachfrage übernehmen? | **Nur wenn Titel und Künstler genau passen**, sonst „bitte ansehen“ |
| O7 | Wer darf „Online suchen“? | **Nur Administratoren** |
| O8 | Beschreibung und Alter wo? | **Je Folge** (angezeigt auf der Serienseite bei der Folge) |
| O9 | Apple antwortet nicht | Satz „Online-Suche gerade nicht erreichbar, später noch einmal“; alles andere geht normal weiter |

## 6. Ursprünglich offene Fragen (beantwortet durch O5–O9)

1. **Nachholen:** Läuft die Automatik auch einmal über die vorhandene Bibliothek (wie die Cover-Suche aus den Tags), oder
   nur bei neuen Einträgen? Wenn ja: alles auf einmal mit Vorschlagsliste oder still mit „bitte ansehen“?
2. **Wie sicher ist „sicher“?** Ab wann übernimmt die Automatik ohne Nachfrage (z. B. Titel und Künstler passen genau)?
3. **Rechte:** Darf jeder Benutzer „Online suchen“ (Alltag) oder nur Administratoren?
4. **Was wird gespeichert:** Beschreibung und Alter je Serie oder je Folge? Wo angezeigt (Serienseite, Kachel)?
5. **Ausfall:** Was zeigt die Seite, wenn Apple nicht antwortet oder drosselt?

## 7. Prüfung gegen den Stand vom 18.11. (Projektleitung)

Seit dem 14.11. sind Stufe A (A-1 bis A-3) und Stufe B „Gehört“ gebaut, abgenommen und eingespielt. Am 14.11. liefen
außerdem drei Aufräumläufe der Projektleitung über die vorhandenen Seitenbefehle (Plan `docs/plan/stueckliste-und-psp.md`,
Eintrag 3.22): Sammelordner nach AC1 einsortiert, zwei Läufe der iTunes-Vorschlagsliste („hoch“, dann „mittel/niedrig“),
danach der Abgleich mit der Tonie-Liste der Gemeinschaft (GitHub `tonies-json`). Die Online-Suche wurde am 16.11. als
eigenes EGM abgetrennt.

### 7.1 Bibliothek heute (gelesen am 18.11. über `serien/list` und `serie/get`, nur lesend)

| Wert | 14.11. (Brief) | 18.11. |
|---|---|---|
| Einträge | 282 | **341** (nach Einsortieren 445, nach den Läufen 341) |
| Folgen | – | **820**, davon **122** mit Nummer |
| Einträge „bitte ansehen“ | 260 | **173** (151 Folgen mit Prüfgrund) |
| Art geraten | 234 | **259** (64 von Hand, 18 aus Tags) |
| Cover | – | **233** automatisch (aus Tags), **99** eigenes Bild, **9** ohne |
| „bitte ansehen“ **und** Cover aus Tags | – | **120** |
| Einträge mit Tobie | – | 3 |

Prüfgründe der Folgen: `serie_aus_interpret` 135, `tags_fehlen` 16, `serie_aus_ordner` 15, `teilweise_doppelt` 5,
`nummer_doppelt` 2, `track_teils_leer` 2, `track_doppelt` 1. Die Serien selbst tragen keinen eigenen Prüfgrund.

### 7.2 Messung der Quellen (18.11.)

- **iTunes:** Alben (so stehen die meisten Hörspiele dort, Genre „Hörspiele“) haben **keine Beschreibung und keine
  Altersangabe**. Hörbücher (`wrapperType=audiobook`, Genre „Kinder und Jugend“) haben eine Beschreibung, aber kein Alter.
  Eine Altersangabe („Ab 6 Jahren“) gab es nur bei einem Film. Eine Einzelfolge findet man oft nur als Teil einer Box
  („Handwerker Box (… als Baggerfahrer & …)“), das Zuordnen braucht also Regeln.
- **Tonie-Liste (`tonies-json`, 6 709 Einträge):** Felder `series`, `episodes`, `title`, `tracks` (Liste der
  Tracktitel), `release`, `language`, `pic` (Bild der **Figur**, kein Cover). Keine Beschreibung, kein Alter.
- **Tonie-Shopseite (`tonies.com/de-de/tonies/<serie>/<folge>/`, nachgemessen auf Frage von Tobias):** Die Seite
  trägt in ihren Seitendaten (`__NEXT_DATA__`, `props.pageProps.product`) **Beschreibung** (Text, mehrere Sätze),
  **Alter** (`ageMin`, z. B. 3), Laufzeit (`runTime`), Genre, Serie, Tracks, Sprecher und Erscheinungsdatum. Die
  Verbindung zur Tonie-Liste ist die Artikelnummer (`salesId` = `model` in `tonies-json`, z. B. `01-0014`). Grenzen:
  **nur Tonies, die gerade im Shop sind** (Sitemap: 577 deutsche Tonie-Seiten, die Tonie-Liste kennt etwa 4 300
  deutsche Hörspiel-Tonies); **keine offizielle Schnittstelle** (die Seite kann sich jederzeit ändern); etwa 550 KB je
  Seite; das Bild zeigt die Figur, kein Cover. `robots.txt` sperrt diese Seiten nicht.

### 7.3 Was das für die Entscheidungen heißt

| Nr. | Stand 18.11. | Bewertung |
|---|---|---|
| O1 | Cover und Namen: wie geplant. **Beschreibung nur für Hörbücher, Alter aus keiner der beiden Quellen** | **verändert**, neue Antwort von Tobias nötig |
| O2 | Von Hand und beim Einsortieren: beides noch nicht gebaut | **offen** (nach dem Aufräumen neu zu bestätigen) |
| O3 | Im Lauf am 14.11. kam als zweite Quelle die Tonie-Liste dazu (606 von 822 Folgen mit Tonie) | **verändert**: zweite Quelle ja oder nein |
| O4 | Cover gehen nicht auf die Boxen (Sync nimmt `cover*.jpg` aus, `data-model.md` 5) | **erledigt**, gilt weiter |
| O5 | Nachholen ist durch die zwei Läufe und den Tonie-Abgleich **weitgehend geschehen** (1 097 + Tonie-Vorschläge, 0 Fehler). Rest: 173 „bitte ansehen“, 259 Arten geraten, 233 Cover aus Tags | **weitgehend erledigt**; offen, ob ein zweiter Lauf in HA nötig ist |
| O6 | Die Läufe nutzten Stufen „hoch/mittel/niedrig“; Regeln und Protokoll liegen nicht im Repo | **offen** (Regeln für den Bau neu festlegen) |
| O7 | Rechte heute in drei Stufen (lesen, alltag, admin, Vertrag 2.1). „Nur Administratoren“ = Stufe admin | **gilt**, sauber einordnen |
| O8 | Beschreibung je Folge: siehe O1, bei Hörspielen gibt es keine | **verändert** |
| O9 | Satz bei Ausfall: gilt | **gilt** |

### 7.4 Neue Punkte für den Entwurf (Projektleitung)

1. **Cover aus den Läufen zählen als „eigen“.** Die 78 Cover aus der Vorschlagsliste liegen als `cover-eigen.jpg`
   (Upload über die Seite). „Eigene Eingaben gehen vor“ schützt sie jetzt genauso wie ein Handy-Foto. Der Entwurf muss
   sagen, wo ein Online-Cover liegt (`cover.jpg` als automatisches oder eigene Quelle) und was `cover_suche` und
   `cover/neu_suchen` (Befehl 44) damit tun.
2. **Speicherort für Beschreibung und Treffer:** nicht in `serie.json` (Fingerabdruck `stand`, Sync auf die Boxen),
   auch nicht einfach im Store `tobibox.medieninfo`, weil der als jederzeit neu berechenbar gilt; ein von Hand gewählter
   Treffer ist das nicht. Festlegung im Entwurf.
3. **Zusammenführen und Verschieben:** Die Läufe haben 80 Serien zusammengeführt und 18 Folgen verschoben. Ob die
   gebaute Funktion das je selbst tut, berührt Tobies, Favoriten und die Schlüssel der Hördaten (`serie_id#folge`). Als
   Grenze ausdrücklich festlegen.
4. **Art:** Die meisten Arten sind noch geraten (259). Die Quellen liefern ein Genre („Hörspiele“, „Kinder und Jugend“,
   Hörbuch-Typ). Ob die Suche auch die Art vorschlägt, ist neu zu fragen.
5. **Fähigkeit:** Ein neuer Befehl (Suche, Übernehmen) braucht nach Vertrag 14.1 eine Fähigkeit (Vorschlag `online_suche`).
6. Der Befund „Serie fehlt nach `pruefen()`“ vom 14.11. ist im Code behoben (`media.py`, Serien aus der Zeit der Prüfung
   bleiben); er stört automatische Läufe nicht mehr.

### 7.5 Wie die Läufe vom 14.11. entschieden haben (nachträgliche Beschreibung)

Skripte und Listen lagen im Scratchpad der Sitzung und sind seit dem Neustart des Macs weg. Die Regeln stehen noch in
den Protokollen der Agents, die sie geschrieben haben; hier **nachträglich beschrieben** (18.11.), nicht nachgeprüft.

- **Seriennamen, Zusammenführen, Verschieben:** eine **Handzuordnung** des Agents (Tabelle je Serie mit neuem Namen,
  Grund und Stufe H/M/N, z. B. „Serie heißt nach Autorin; die Reihe heißt …“). Die Sicherheit war ein **Urteil**, keine
  Regel. Das lässt sich nicht als feste Regel in die Integration bauen.
- **Cover (iTunes):** Wörter des Namens (klein, Umlaute aufgelöst, ohne Füllwörter wie „der“, „und“ und ohne
  Allerweltswörter wie „Hörspiel“, „Folge“, „Disney“) gegen die Wörter des Albumnamens. Mindestens 80 % der Wörter
  gefunden und **keine** zusätzlichen Zahlen im Album. **hoch:** kein zusätzliches Wort im Album; **mittel:** höchstens
  zwei zusätzliche Wörter und mindestens drei Wörter im Namen. Boxen, Sammlungen und Filme ausgeschlossen. Cover einer
  einzelnen Folge für eine ganze Reihe höchstens „mittel“. Cover in 600 × 600 px.
- **Folgennummer (iTunes):** nur wenn genau **ein** Album zu Reihe und Titel passt (alle Wörter) und eine Nummer trägt
  („Folge 12“, „12.“, „Band 12“); dann höchstens „mittel“.
- **Art:** nur von „geraten“ auf „musik“ (Titel und iTunes-Genre), immer „mittel“.
- **Tonie-Abgleich:** Ähnlichkeit der Titel (Folge und Serie getrennt, Serie gilt als gestützt ab 0,85). **hoch:** Titel
  genau gleich **und** Serie gestützt **und** gleiche Zahl der Tracks **und** deutsch (nicht: eine Datei bei uns gegen
  drei und mehr Tracks beim Tonie). **mittel:** Ähnlichkeit ab 0,92 mit gleicher Trackzahl, oder genauer Titel bei
  anderer Trackzahl. Sonst niedrig. Ein Hinweis (z. B. möglich doppelt) setzt „hoch“ auf „mittel“ herunter.

Folgerung für O6 („nur wenn Titel und Künstler genau passen“): Für **Cover** und **Nummer** gibt es erprobte Regeln.
**Seriennamen** hat am 14.11. kein Algorithmus sicher bestimmt; eine Automatik beim Einsortieren müsste sich dort auf
genaue Treffer beschränken. Die Trackzahl der Tonie-Liste war das stärkste Zeichen für „dieselbe Folge“.

### 7.6 Fragen an Tobias (Reihenfolge, eine nach der anderen)

1. Was stört nach dem Aufräumen noch? Braucht es einen Lauf über alles in HA, oder nur neue Uploads und Suchen von Hand?
2. Automatische Suche beim Einsortieren (O2): weiter gewünscht?
3. Soll die Suche auch die Art vorschlagen?
4. Tonie-Liste als zweite Quelle: ja oder nein?
5. Ein Treffer von Hand: überschreibt er alles oder nur angehakte Felder?
6. Zusammenführen und Verschieben: darf die Funktion das oder nie?
7. Beschreibung und Alter (nach der Messung 7.2): nur Hörbücher, weglassen, oder andere Quelle?

## 8. Entscheidungen nach der Prüfung (Tobias, 18.11.)

| Nr. | Frage | Antwort |
|---|---|---|
| O10 | Was soll die Suche nach dem Aufräumen noch leisten? | **Neue Uploads, Suche von Hand und ein Lauf über den Rest** (die 173 Einträge „bitte ansehen“, geratene Arten, Cover aus Tags) |
| O11 | Neuer Upload: übernehmen oder nur vorschlagen? | **Genaue Treffer übernehmen** (bestätigt O2/O6): ein sicherer Treffer ändert gleich; der Eintrag zeigt „aus der Online-Suche“ und lässt sich zurücknehmen; sonst „bitte ansehen“. **(PL)** Für Seriennamen gelten strengere Regeln als für Cover und Nummer (7.5) |
| O12 | Soll die Suche auch die Art vorschlagen? | **Ja, nur wo sie geraten ist** (`art_quelle = geraten`); von Hand gesetzte Arten (`manuell`) und Arten aus Tags bleiben |
| O13 | Tonie-Liste als zweite Quelle? | **Ja.** Die Liste (`tonies-json`) wird geladen und liegt in HA; sie liefert Serie, Titel, Nummer und Trackzahl, keine Cover. Cover kommen weiter von Apple |
| O14 | Was übernimmt ein Treffer von Hand? | **Alles, abwählbar:** Übersicht mit Häkchen (Cover, Serienname, Folgentitel und Nummern, Art), alle gesetzt, Tobias nimmt weg, was nicht passt. **(PL)** Felder, die schon von Hand gesetzt sind (eigenes Cover, Art `manuell`, von Hand umbenannt), stehen ohne Häkchen und mit dem Hinweis „von Hand gesetzt“; wer sie trotzdem anhakt, überschreibt sie bewusst |
| O15 | Zusammenführen und Verschieben? | **Nur vorschlagen:** Die Suche erkennt „gehört zur Serie X“ und zeigt einen Vorschlag mit Knopf; ausgeführt erst nach Tipp eines Administrators, **nie automatisch** (auch nicht beim Upload oder im Lauf über den Rest). Ausführung über die vorhandenen Befehle (`serien/zusammenfuehren`, `folge/verschieben`) |
| O16 | Beschreibung und Alter (nach Messung 7.2) | **Ja, wo vorhanden:** Beschreibung und Alter von der Tonie-Shopseite (über die Artikelnummer aus der Tonie-Liste), für Hörbücher die Beschreibung von Apple. Wo es nichts gibt, bleibt es leer. Ersetzt O1 (Alter) und O8 (bleibt: je Folge, angezeigt bei der Folge) |

## 9. Problem und Grenzen nach dem Brainstorm (Stand 18.11.)

**Problem:** Nach den Läufen vom 14.11. sind 173 von 341 Einträgen noch „bitte ansehen“, 259 Arten geraten und 233 Cover
aus Tags (die Tobias nicht mag). Jeder neue Upload bringt dieselben schlechten Angaben wieder. Beschreibung und Alter
fehlen ganz.

**Was gebaut wird:**
1. **Automatik beim Einsortieren:** Suche in Tonie-Liste und bei Apple; genaue Treffer werden übernommen (Cover, Namen,
   Nummer, Art wenn geraten, Beschreibung und Alter), mit Hinweis „aus der Online-Suche“ und Rücknahme; sonst
   „bitte ansehen“ mit Vorschlag (O2, O6, O11, O12).
2. **Suche von Hand** je Eintrag für Administratoren: Treffer mit Cover, ein Tipp, Übersicht mit Häkchen (O7, O14).
3. **Lauf über den Rest** der Bibliothek mit denselben Regeln (O10).
4. **Vorschläge** zum Zusammenführen und Verschieben, nur auf Tipp (O15).

**Grenzen:**
- Quellen: Tonie-Liste (`tonies-json`, in HA geladen), Tonie-Shopseite (nur Beschreibung, Alter), iTunes-Suche von
  Apple (Cover, Namen, Hörbuch-Beschreibung). An Apple gehen Titel (O3); an Tonies nur der Abruf einzelner Seiten.
- Nur HA-Seite und Integration. Box, `mqtt-v1.md` und Sync bleiben unverändert; Cover, Beschreibung und Alter gehen nicht
  auf die Boxen (O4).
- Eigene Eingaben gehen vor; die Automatik überschreibt nie, was von Hand gesetzt ist (Abschnitt 4, O14).
- Nie automatisch zusammenführen oder verschieben (O15).
- Fällt eine Quelle aus, geht alles andere normal weiter (O9).
- Vertragsänderungen nur nach Freigabe durch Tobias.
