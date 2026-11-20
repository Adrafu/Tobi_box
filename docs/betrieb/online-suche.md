# Tobi Box: Online-Suche (für den Administrator)

So benutzt du die Online-Suche: Cover und Angaben von Apple und Tonies, Namensvorschläge von Claude. Die Anleitung gilt für Administratoren. Die Partnerin sieht nur einen kleinen Teil davon, siehe `ha-seite-alltag.md` (Abschnitt „Aus der Online-Suche übernommen“).

Stand: Design Rev. 2.7 (`docs/designs/online-suche.md`). Gebaut sind OS2 bis OS4 und das Nachpaket T10/T11. Die Abnahme mit Tobias (OS5) steht noch aus. Beschriftungen unten stehen so auf der Seite.

## 1. Was die Online-Suche tut und was nicht

Sie holt für Einträge und Folgen der Bibliothek:

| Feld | Was |
|---|---|
| „Cover“ | Bild von Apple (Datei `cover-online.jpg`) |
| „Folge“ | Folgentitel; der heutige Wortlaut bleibt, davor kommt höchstens „Folge N: “. Apples Titel gilt nur für Platzhalter wie „Track 01“ |
| „Nummer“ | Nummer der Folge |
| „Art“ | Hörspiel, Hörbuch, Musik; nur dort, wo die Art nur geraten ist |
| „Beschreibung“ | Text der Folge (Tonies-Shop, sonst Apple-Hörbuch) |
| „Alter“ | „ab N“, nur vom Tonies-Shop |
| „Name“ | **nur als Vorschlag von Claude** |

**Sicher oder unsicher.** Jedes Feld wird einzeln bewertet:

- **Sicher** (Titel und Künstler stimmen genau, keine Quelle widerspricht): HA übernimmt den Wert selbst. Alle sehen dann die Zeile „Aus der Online-Suche übernommen“. Du kannst es zurücknehmen (Abschnitt 6).
- **Unsicher:** Es wird ein Vorschlag. Er wartet auf dich (Abschnitt 5).
- **Nichts passt:** Es passiert nichts.

**Was nie automatisch geschieht:**

- Der **Name** eines Eintrags. Auch Claude schlägt ihn nur vor.
- **Zusammenführen:** nur als Vorschlag von Claude, ausgeführt erst auf deinen Tipp.
- **Verschieben** von Folgen in andere Einträge. Dazu gibt es keine Vorschläge. Verschieben bleibt Handarbeit.
- Der Prüfgrund `serie_aus_interpret` oder `serie_aus_ordner` (Folge) wird von der Online-Suche **nie** aufgelöst. Den Namen bestätigst oder änderst du von Hand, oder du nimmst einen Namensvorschlag an. Das gilt auch für andere Gründe wie `teilweise_doppelt`, `track_teils_leer`, `track_doppelt`.
- Felder, die ein Mensch gesetzt hat, werden nie überschrieben (Abschnitt 4). Ein eigenes Foto geht immer vor.

Die Boxen merken nichts davon. Cover, Beschreibung und Alter bleiben in Home Assistant und gehen nicht auf die Box. Die Suche gilt nur für normale Einträge, nicht für die Überraschungs-Serie.

Quellen und was dorthin geht:

- **Apple** (iTunes-Suche): die Suchwörter, also Serien- und Folgentitel.
- **Tonies:** die Tonie-Liste der Gemeinschaft (einmal die Woche) und einzelne Seiten des Tonie-Shops. Welche Seiten abgerufen werden, verrät, welche Tonies in der Bibliothek stehen.
- Der Browser fragt nie selbst fremde Server. Cover-Vorschauen liefert HA.

## 2. Wann sie läuft

1. **Von selbst beim Einsortieren.** Wird ein Upload neu einsortiert, fragt HA im Hintergrund die Quellen. Das Einsortieren wartet nie darauf. Ist eine Quelle nicht erreichbar, bleibt der Eintrag so, wie er einsortiert wurde. Den Hinweis „Aus der Online-Suche übernommen“ gibt es nur, wenn etwas übernommen wurde.
2. **„Anders einsortieren“** geht nach einer automatischen Übernahme weiter. Die Online-Änderungen verfallen dann mit den Folgen.
3. **Ein Lauf über die ganze Bibliothek nur von Hand:**
   1. Tippe oben auf das Technik-Symbol und dann auf „Online-Suche“.
   2. Tippe auf „Bibliothek durchsuchen“. Die Meldung lautet: „Der Lauf ist gestartet.“
   3. Es läuft immer nur ein Lauf. Die Seite muss nicht offen bleiben. Unter „Lauf“ steht zum Beispiel „Läuft: 40 von 340.“
   4. Ein Lauf über die ganze Bibliothek dauert etwa dreieinhalb Stunden (gemessen für 340 Einträge). Er fragt nur Einträge, die noch nicht gesucht wurden oder bei denen die Marke verfallen ist (Abschnitt 5).
4. **Anhalten:** Tippe auf „Anhalten“. Es steht „Hält nach dieser Serie an.“ Die laufende Serie wird noch fertig, dann steht dort „Angehalten.“
5. **Pause:** Bremst eine Quelle, steht „Pause bis 14:20, weil Apple bremst.“ Der Lauf wartet und geht danach weiter.
6. **Neustart von HA:** Ein laufender Lauf endet mit „Abgebrochen (Neustart). Du kannst neu starten.“ Tippe auf „Bibliothek durchsuchen“. Der neue Lauf macht dort weiter, wo der alte aufgehört hat, weil Einträge mit gültiger Marke übersprungen werden.
7. **Quelle nicht erreichbar:** Nach drei Pausen in Folge endet der Lauf mit „Abgebrochen: Quelle nicht erreichbar.“ Die betroffenen Einträge bekommen dabei keine Fehler-Marke. Starte später neu.
8. **Ende:** „Fertig: 120 Einträge geändert, 38 Vorschläge, 12 ohne Treffer.“ Die letzten fünf Läufe stehen unter „Letzte Läufe“.

## 3. Claude: Namensvorschläge

Claude schlägt Namen vor, wenn ein Eintrag einen Grund dafür hat: Er wurde neu einsortiert, oder eine Folge hat den Prüfgrund `serie_aus_interpret` oder `serie_aus_ordner`. Claude ändert nie etwas selbst. Das Ergebnis ist immer ein Vorschlag mit Grund. Bei der Suche von Hand wird Claude nicht gefragt.

**Wichtig: Ohne eigene Einstellung ist Claude eingeschaltet.** Gibt es in HA genau eine `ai_task`-Entität der Claude-Integration (`anthropic`), benutzt die Online-Suche sie von selbst. Das gilt auch für die schon bestehende Einrichtung. **Setze oder leere die Option deshalb bewusst, bevor du den ersten echten Lauf startest** (und vor den Abnahmeschritten 14 und 15). Danach gilt immer, was du eingestellt hast.

**Option setzen oder leeren:**

1. Öffne in HA „Einstellungen“, dann „Geräte & Dienste“.
2. Tippe auf die Integration „Tobi Box“ und dann auf „Konfigurieren“. Es öffnet sich „Tobi Box ändern“.
3. Das Feld heißt „KI-Entität für die Online-Suche (Claude)“ (Schlüssel `online_ki_entitaet`). Es ist eine Auswahl der `ai_task`-Entitäten.
   - **Einschalten:** Wähle die Entität, zum Beispiel die von Claude.
   - **Ausschalten:** Leere das Feld. Dann ist der Claude-Schritt aus und die Suche nutzt nur ihre festen Regeln. Die Vorgabe kommt nicht zurück.
4. Tippe auf „Absenden“. Die Integration lädt sich neu; ein Neustart von HA ist nicht nötig.

Wählst du etwas anderes als eine `ai_task`-Entität, steht dort: „Bitte eine KI-Entität („ai_task“) wählen oder das Feld leer lassen.“

**Welche Daten an Claude gehen.** Sie gehen über HA an den Anbieter der gewählten Entität (heute Anthropic):

- der Serienname, der Ordnername, die Folgentitel (höchstens 12 Folgen je Eintrag, die ersten der Serie), die Nummern, die Zahl der Tracks, die Prüfgründe,
- bis zu drei Kandidaten je Quelle (Tonie-Liste: Reihe, Folgentitel, Tracks, Kategorie; Apple: Albumname, Künstler, Genre, Zahl der Titel),
- ob der Eintrag ein Einzeltitel ist, die Zahl seiner Folgen und wie viele davon mitgeschickt werden.

Es gehen **keine** Namen von Tobies, keine Benutzer, keine Kennungen und keine Audiodateien raus. Auch ein Upload eines Alltag-Kontos (der Partnerin) löst beim Einsortieren einen Aufruf aus, wenn der neue Eintrag einen Grund hat.

**Grenzen und Kosten:**

- Nur Einträge mit Grund, höchstens ein Aufruf je Eintrag und Marke.
- Ein Aufruf alle 3 Sekunden, im Lauf höchstens 60 in der Stunde, **höchstens 200 am Tag** (gleitend über 24 Stunden). Ist eine Grenze erreicht, wird der Schritt übersprungen. Der Eintrag wird beim nächsten Lauf nachgeholt.
- Ein Aufruf hat im Mittel etwa 1 200 Eingabe-Tokens. Im ersten Lauf sind das etwa 57 Einträge mit `serie_aus_*`, zusammen etwa 70 000 Eingabe-Tokens. Danach kommen nur neu einsortierte Einträge dazu. Das Design nennt keinen Eurobetrag. Der Probelauf mit 450 Aufrufen brauchte etwa 510 000 Eingabe-Tokens.
- Fällt Claude aus (Entität fehlt, Fehler, Zeitüberschreitung nach 30 Sekunden), gibt es keinen Namensvorschlag. Alles andere geht weiter. Der Eintrag wird beim nächsten Lauf nachgeholt, ein Fehler gilt 1 Tag.

**Zustand ansehen:** Unter „Technik“, „Online-Suche“ steht bei den „Quellen“ die Zeile für Claude: „bereit“, „antwortet gerade nicht“ oder „nicht eingerichtet, keine Namensvorschläge“.

**Wie gut Claude ist:** Im Probelauf waren von 71 Namensvorschlägen 63 richtig (etwa 89 %). Darum sind es nur Vorschläge. Prüfe Name und Grund.

## 4. Suche von Hand

Die Suche gibt es für Einträge und für einzelne Folgen. Sie kann neu suchen, wenn der automatische Weg nichts fand.

1. Öffne den Eintrag. Für eine einzelne Folge öffnest du die Folge, oder tippst in ihrer Zeile auf „⋯“.
2. Tippe auf „⋯“ und dann auf „Online suchen“.
3. Es öffnet sich das Blatt „Online suchen“. Das Suchfeld „Suchtext“ ist vorbelegt. Ändere den Text, wenn du willst, und tippe auf „Suchen“. Mindestens 2 Zeichen: „Gib mindestens 2 Zeichen ein.“
4. Während der Suche steht „Suche bei Apple und Tonies …“. Dann siehst du bis zu 10 Treffer mit Vorschaubild, Titel, Reihe, Nummer („Folge 3“), Quelle („Apple“ oder „Tonies“) und Zahl der Titel. Ein Treffer, den du früher abgelehnt hast, trägt „früher abgelehnt“. Ein Treffer ohne Bild trägt „ohne Bild“.
5. Tippe auf einen Treffer. Es kommt die Übersicht „Was soll übernommen werden?“. Je Feld steht „heute“ und „neu“, jeweils mit einem Häkchen.
   - **Alle Felder sind angehakt**, außer denen, die von Hand gesetzt wurden. Die tragen den Hinweis „von Hand gesetzt“ und sind nicht angehakt.
   - Felder mit gleichem Wert stehen nicht darin. Ist alles gleich, steht dort „Hier ist schon alles so.“
   - Ein Namensvorschlag eines Treffers ist nie vorab angehakt.
   - „Übernehmen“ geht nur mit mindestens einem Häkchen. „Zurück“ bringt dich zur Trefferliste.
6. Tippe auf „Übernehmen“. Es steht „Übernommen.“ (bei einer Umbenennung: „Der Name ist geändert.“)

**Von Hand gesetzt.** Alles, was du hier übernimmst, gilt danach als von Hand. Die Automatik fasst es nie mehr an, ein Lauf kann es höchstens vorschlagen. Als von Hand gelten außerdem:

- ein eigenes Foto (`cover-eigen.jpg`; es geht immer vor dem Online-Cover),
- eine Art, die du gewählt hast,
- der Name (immer),
- Folgentitel und Nummer, die du geändert hast oder die schon vorher da waren, ohne dass die Automatik sie gesetzt hat (Ausnahme: ein Prüfgrund passt).

## 5. Vorschläge ansehen

Unsichere Treffer und Namen von Claude warten auf dich.

1. Öffne den Eintrag. Oben steht die Karte „Vorschlag aus der Online-Suche“ (oder „Bitte kurz ansehen“, wenn zugleich etwas zu prüfen ist). Nur Administratoren sehen sie.
2. In der Bibliothek zeigt „Mit Vorschlag der Online-Suche“ im Filter „Nur zeigen“ alle Einträge mit Vorschlag.
3. Die Karte nennt, was gebraucht wird:
   - **Cover und Angaben von Apple oder Tonies:** „Vorschlag aus der Online-Suche: Cover, Art von Apple“. Mit „Ansehen“ öffnest du die Übersicht „Was soll übernommen werden?“ und entscheidest je Feld. Bei einem Cover siehst du „Cover heute“ und „neues Cover“ nebeneinander. Ist das Bild nicht mehr abrufbar, steht dort: „Das Bild ist nicht mehr da. Öffne den Vorschlag noch einmal.“
   - **Name von Claude:** „Vorschlag von Claude: Name „…““. Darunter steht der Grund, den Claude nennt („Grund von Claude: …“). Mit „Übernehmen“ wird der Eintrag so umbenannt, als hättest du ihn von Hand umbenannt. Das ist keine Online-Änderung und lässt sich nicht über „Zurücknehmen“ zurückholen. Benenne ihn bei Bedarf von Hand um.
   - **Zusammenführen von Claude:** „Vorschlag von Claude: mit „…“ zusammenführen“. Der Knopf „Zusammenführen …“ öffnet den bekannten Dialog, schon ausgefüllt. Erst dort führst du zusammen.
4. **„Nein“** verwirft den Vorschlag (Meldung „Der Vorschlag ist verworfen.“). Derselbe Wert aus derselben Quelle kommt im Lauf nicht wieder. Bei der Suche von Hand erscheint er mit „früher abgelehnt“.
5. Ändert sich der Name des Eintrags, solange ein Namensvorschlag offen ist, verschwindet der Vorschlag von selbst.

**Marken: Warum fragt der Lauf einen Eintrag nicht noch einmal?** Nach einer Suche merkt sich HA das Ergebnis je Eintrag:

- „geändert“ und „Vorschlag“: bleiben, der Eintrag wird im Lauf nicht noch einmal gefragt (neue Folgen werden gefragt).
- „keiner“ (nichts gefunden): **30 Tage**, oder bis die Tonie-Liste eine neue Fassung hat.
- „fehler“ (eine Quelle fiel aus): **1 Tag**, oder bis die Tonie-Liste eine neue Fassung hat.
- Für Claude gilt eine eigene Marke. Sie ist abgelaufen oder fehlt, sobald die Option gesetzt ist, und fehlerhafte Aufrufe gelten 1 Tag. Auch bei sonst gültiger Marke wird Claude dann im Lauf gefragt.

## 6. Zurücknehmen

Zurücknehmen geht für alles, was HA **automatisch** oder durch **Übernehmen aus der Übersicht** geändert hat, innerhalb von **30 Tagen** (höchstens 20 Änderungen je Eintrag). Danach verschwindet auch die Zeile „Aus der Online-Suche übernommen“.

**Einen Eintrag zurücknehmen:**

1. Öffne den Eintrag. Oben steht „Aus der Online-Suche übernommen: Cover, Art.“ Dahinter steht „Zurücknehmen“.
2. Tippe darauf. Das Blatt „Zurücknehmen?“ sagt: „Alle Änderungen der Online-Suche an diesem Eintrag nehmen wir zurück. Zuletzt: Cover, Art.“
3. Tippe auf „Zurücknehmen“. Es steht „Zurückgenommen.“

**Wenn Felder inzwischen von Hand geändert wurden:** Sie bleiben, wie sie sind. Die Meldung sagt es: „Zurückgenommen. 1 Feld blieb, weil es inzwischen geändert wurde.“ (bei mehreren: „Zurückgenommen. 2 Felder blieben, weil sie inzwischen geändert wurden.“). Ein zurückgenommenes Feld gilt danach als von Hand: Ein Lauf darf den Wert später wieder **vorschlagen**, übernimmt ihn aber nie mehr selbst. Titel und Nummer einer Folge gehören zusammen: Wurde eins davon von Hand geändert, bleiben beide stehen.

**Einen Lauf zurücknehmen:**

1. Tippe auf das Technik-Symbol und dann auf „Online-Suche“.
2. Unter „Letzte Läufe“ steht jeder Lauf mit „Lauf vom …“ und seinen Zahlen.
3. **Einzeln:** Tippe beim Lauf auf „Liste der Änderungen“. Die Liste wird geladen („Die Liste wird geladen …“). Jede Zeile hat Namen, Felder und Zustand („Geändert“ oder „Zurückgenommen“). Bei „Geändert“ gibt es ein eigenes „Zurücknehmen“. Der Name ist ein Link zur Serie. Sind es mehr als 500 Änderungen, steht dort: „Es gibt mehr als 500 Änderungen; hier stehen die ersten 500, nach Namen sortiert. Mit „Alle zurücknehmen“ gehen alle zurück.“
4. **Alles:** Tippe auf „Alle zurücknehmen“. Die Frage lautet „Alle zurücknehmen?“ und nennt die Zahl der Einträge („12 Einträge gehen auf die alten Werte zurück.“). Bestätige mit „Alle zurücknehmen“. Das läuft im Hintergrund („Wird zurückgenommen: 3 von 12.“) und endet mit „Zurückgenommen.“ bzw. mit der Zahl der Felder, die geblieben sind.
5. „Alle zurücknehmen“ macht einen Lauf als Ganzes ungeschehen (zum Beispiel einen Probelauf). Ein späterer Lauf darf diese Felder dann wieder automatisch übernehmen. Das unterscheidet es vom Zurücknehmen eines einzelnen Eintrags oder einer einzelnen Änderung.

**Nicht zurücknehmbar** sind Zusammenführungen und Verschieben (dafür Papierkorb bzw. zurückverschieben) und ein angenommener Namensvorschlag (von Hand umbenennen).

**Online-Cover entfernen:** Gilt für ein Online-Cover, das keine Änderung mehr hat (zum Beispiel nach einem Zurückholen aus dem Papierkorb oder nach Ablauf der 30 Tage).

1. Öffne den Eintrag, tippe auf „⋯“ und dann auf „Cover ändern“.
2. Tippe auf „Online-Cover entfernen“. Es steht „Das Online-Cover ist entfernt.“
3. Es gilt wieder das Cover aus den Dateien (ein eigenes Foto bleibt unberührt).

**Cover aus den Dateien neu lesen:** Das ist der frühere Knopf „Cover neu suchen“.

1. Tippe auf das Technik-Symbol, dann auf „Speicher und Netz“, Karte „Bibliothek aufräumen“.
2. Tippe auf „Cover aus den Dateien neu lesen“. Das Blatt sagt: „Liest die Bilder aller Einträge aus den Dateien noch einmal. Online-Cover und eigene Fotos bleiben, wie sie sind.“
3. Tippe auf „Ja, neu lesen“. Es steht „Das Einlesen der Cover läuft. Das dauert ein paar Minuten.“

## 7. Wenn etwas nicht geht

**Wo siehst du den Zustand?** Technik, „Online-Suche“. Dort stehen die Karten „Quellen“ (Apple, Tonies, Tonies-Shop, Claude, Tonie-Liste), „Lauf“ und „Letzte Läufe“.

| Anzeige | Bedeutung und was du tust |
|---|---|
| „Online-Suche gerade nicht erreichbar, später noch einmal.“ | Keine Quelle antwortet. Warte und versuche es später. Alles andere geht weiter. |
| „Apple antwortet gerade nicht. Das sind nur Treffer von Tonies.“ (oder umgekehrt) | Nur eine Quelle fällt aus. Die Treffer der anderen sind gültig. |
| „Apple braucht eine Pause, bis 14:20.“ bzw. „Pause bis 14:20“ | Die Quelle bremst (Antwort 429 oder Serverfehler). HA pausiert sie 15 Minuten. Der Lauf wartet. Du musst nichts tun. |
| „noch nicht geladen“ bei „Tonie-Liste“ | Die Liste wurde noch nicht geholt. Sie lädt beim ersten Bedarf. Ohne sie gibt es keine Treffer von Tonies. |
| „Die Suche ist zu alt. Such bitte noch einmal.“ | Treffer gelten nur 15 Minuten. Suche noch einmal. |
| „Nichts gefunden. Versuch einen anderen Namen.“ | Ändere den Suchtext, zum Beispiel ohne Zusätze. |
| „Diesen Vorschlag gibt es nicht mehr. Bitte lade die Ansicht neu.“ | Der Vorschlag wurde inzwischen verworfen oder ist ungültig (zum Beispiel nach einer Umbenennung). Lade die Seite neu. |
| „Diese Änderung gibt es nicht mehr. Nach 30 Tagen lässt sie sich nicht mehr zurücknehmen.“ | Die Änderung ist zu alt. Ändere von Hand zurück. |
| „Diesen Lauf gibt es nicht mehr.“ | Von den Läufen werden nur die letzten fünf behalten. |
| „Es läuft schon eine Suche über die ganze Bibliothek. Bitte warte, bis sie fertig ist.“ | Es läuft immer nur ein Lauf. |
| „Das waren gerade sehr viele Änderungen. Bitte kurz warten und dann noch einmal versuchen.“ | Warte einen Moment. |
| „Abgebrochen (Neustart). Du kannst neu starten.“ | HA wurde neu gestartet. Starte den Lauf neu, er macht weiter. |
| „Abgebrochen: Quelle nicht erreichbar.“ | Drei Pausen in Folge. Starte später neu. |
| Claude: „antwortet gerade nicht“ | Die Entität fehlt oder der letzte Aufruf scheiterte. Prüfe in HA die Claude-Integration und die Option aus Abschnitt 3. Die Suche läuft ohne Namensvorschläge weiter. |
| Claude: „nicht eingerichtet, keine Namensvorschläge“ | Die Option ist leer, oder es gibt keine eindeutige Claude-Entität. Setze sie, wenn du Namensvorschläge willst. |

Weitere Hinweise:

- Fehlt bei einer Tonie-Shopseite die Beschreibung oder das Alter (die Seite hat sich geändert), vermerkt HA das einmal am Tag im Protokoll (`online_shop_format`) und versucht es nicht dauernd neu.
- Die Daten der Online-Suche liegen in der HA-Sicherung (`tobibox.online`). Nach dem Zurückholen aus dem Papierkorb sind sie nicht mehr da. Der nächste Lauf sucht dann neu.
- Spielst du eine ältere Fassung der Integration zurück, macht sie aus dem Wert „online“ bei Art und Cover-Quelle „manuell“. Cover und Angaben bleiben, aber die Art zählt dann als von Hand gesetzt.
- Nicht-Administratoren bekommen keine Online-Befehle und keine Ereignisse der Online-Suche.
