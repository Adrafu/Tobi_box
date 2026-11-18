# OS1: Regelstand des Trockenlaufs (abgenommen, 18.11.)

Stand 18.11. Das ist der genau gemessene und von Tobias abgenommene Regelstand aus dem Trockenlauf OS1
(Messskript außerhalb des Repos, `regeln.py`). OS2 baut ihn ohne das Skript nach (`online_abgleich.py`, reine Funktionen).
Grundlage ist Abschnitt 4 von `docs/designs/online-suche.md`; wo das Design offen war, steht die Auslegung unten
(Abschnitt 5). Testmaterial mit erwartetem Ergebnis: `homeassistant/tests/fixtures/online/` (siehe dort `README.md`
und `erwartung.json`). Alle Wortlisten und Schwellen sind benannte Konstanten, damit man sie später ändern kann.

## 1. Konstanten

### Wörter (4.1)
- Füllwörter (fallen weg): `am`, `an`, `and`, `auf`, `aus`, `bei`, `das`, `dem`, `den`, `der`, `des`, `die`, `ein`, `eine`, `einem`, `einen`, `einer`, `eines`, `es`, `fuer`, `im`, `in`, `ins`, `ist`, `mit`, `oder`, `of`, `sich`, `the`, `und`, `vom`, `von`, `zu`, `zum`, `zur`
- Allerweltswörter (fallen weg): `band`, `folge`, `folgen`, `hoerbuch`, `hoerbuecher`, `hoerspiel`, `hoerspiele`, `original`, `teil`, `ungekuerzt`, `vol`, `volume`
- Einzelne Buchstaben fallen weg, einzelne Ziffern bleiben.
- Normalisierung vor allem anderen: klein, `ß` zu `ss`, `ä ö ü` zu `ae oe ue`, Akzente weg, nur `[a-z0-9]`-Folgen als Wörter.

### Ausschluss bei Apple-Alben (4.3), geprüft auf dem normalisierten Albumnamen
- Ganzes Wort: `alle`, `best`, `box`, `bundle`, `edition`, `film`, `kino`, `komplett`, `musical`, `single`
- Wortteil (irgendwo im Namen): `sammlung`, `collection`, `soundtrack`, `jubilaeum`, `edition`, `komplett`, `bundle`
- Zeichen im Original-Namen: `/`
- Trackgrenze: ausgeschlossen, wenn der Albumtitel mehr als **40** Titel hat **und** mehr als das **2**-Fache der Trackzahl unserer Folge (mindestens 1 gerechnet). Bei Reihen-Alben zählt die Summe der Tracks des Eintrags.

### Schwellen
- Seriennamen-Ähnlichkeit „Serie gestützt“ (Tonie): mindestens **0.85**.
- Titel-Ähnlichkeit für „unsicher“ (Tonie): mindestens **0.92** bei gleicher bekannter Trackzahl.
- Apple „unsicher“: mindestens **80 %** der Wörter des Folgentitels im Album, höchstens **2** Zusatzwörter im Album, keine zusätzliche Zahl.
- Tonie: „eine Datei bei uns, drei und mehr Tracks beim Tonie“ (Konstante 3) ist nie sicher.
- Mindestwörter des Folgentitels für eine Reihen-Stimme: Tonie 1, Apple 2.
- Shopseiten je Folge: höchstens 2; Beschreibung höchstens 2000 Zeichen.

### Sprachmerkmale der Tonie-Liste (3.1)
- Benutzbar: `language = de-de`, `model` gesetzt, und kein Treffer in diesen Listen (geprüft auf `series`, `episodes`, `title`).
- Fremde Zeichen: `¡`, `¿`, `ñ`, `ą`, `ć`, `ę`, `ğ`, `ı`, `ł`, `ń`, `ś`, `ş`, `ź`, `ż`
- Fremde Wörter (ganze Wörter, klein): `altre`, `amigos`, `avec`, `aventures`, `contes`, `cuentos`, `de`, `dei`, `del`, `della`, `en`, `et`, `gli`, `histoires`, `historias`, `i`, `il`, `les`, `mes`, `muita`, `nuevo`, `nuova`, `nuovo`, `och`, `otras`, `petit`, `pipsa`, `possu`, `racconti`, `storie`, `sus`, `tarinoita`, `trenino`, `une`
- Sprachkurs-Reihen (Teilstring im normalisierten `series`): `englisch lernen`, `english`, `learn english`, `learning english`, `deutsch lernen`, `franzoesisch lernen`, `spanisch lernen`. Solche Reihen sind nie „sicher“ und nie Stimme für eine Umbenennung.

### Tonie-Kategorie zu Art (4.7)
- `audio-play` → hoerspiel
- `audio-play-educational` → hoerspiel
- `audio-book` → hoerbuch
- `music` → musik
- `Musik` → musik
- `audio-play-songs` → unsicher:musik
- `audio-book-songs` → unsicher:musik
- `creative-tonie` → keine Art
- `Hörspiele & Hörbücher` → keine Art
Alle anderen Werte (auch fehlend, `system`, `Wissen`, `JAKO-O`, …): keine Art. „unsicher:…“ heißt: höchstens unsicher.

### Apple-Genre zu Art
- Genre enthält (normalisiert) `hoerspiel`: Klasse `hoerspiel` (Album); `wrapperType = audiobook`: Klasse `hoerbuch`.
- Genre enthält eines von `kinderlieder`, `kindermusik`, `pop`, `klassik`, `rock`, `schlager`, `soundtrack`, `filmmusik`, `musical`, `weihnachtsmusik`, `kinder musik`, `children`, `world`, `jazz`, `dance`, `hip-hop`, `electronic`, `singer`, `folk`, `country`, `r&b`, `alternative`, `easy listening`: Klasse `musik` (nur unsicher); alles andere: `sonst`.

### Platzhalter-Titel (4.5)
Der normalisierte Titel passt auf eines dieser Muster (ohne Beachtung der Groß-/Kleinschreibung):
- `^(track|titel|kapitel|chapter|spur|audio|datei|file|folge|teil|kapitel)[\s_\-\.]*\d{1,3}$`
- `^\d{1,3}$`
- `^(track|titel|kapitel|spur|audio|datei)[\s_\-\.]*\d{1,3}\.(mp3|m4a|m4b|flac|ogg|wav|aac)$`
Dateinamen mit Endung sind **kein** Platzhalter (es sind echte Titel).

### Prüfgründe, die eine Automatik zulassen (6.1)
- Serienname: `serie_aus_interpret`, `serie_aus_ordner` (an einer Folge).
- Folgentitel (nur Platzhalter, siehe 2.9): `tags_fehlen`.
- Nummer: `tags_fehlen`, `nummer_doppelt`.

### Muster für Nummern (4.1, regulärer Ausdruck, ohne Beachtung der Groß-/Kleinschreibung)
- Nummer vorn abtrennen: `Folge|Teil|Band|Episode|Nr.|Vol.` + Zahl (1 bis 4 Ziffern) + optional `:`, `.`, `-`; **oder** nur `N:` bzw. `N. ` am Anfang. Danach ist der Rest der Titel.
- Mit Präfix: `<Text>, Folge N: Rest` bzw. mit `-`, `–`, `:` (Text höchstens 60 Zeichen; besteht der Text nur aus Serienwörtern, fällt er weg, sonst bleibt er im Titel). Es muss ein Rest folgen („Titel – Teil 1“ wird nicht zerlegt).
- Vereinheitlichen im neuen Titel (2.9): `[Folge|Episode] N` gefolgt von `:`, `.`, `_` oder ` - `, danach der Rest.
- Schon vorhandenes „Teil/Band N“ im Titel: `Teil|Band N` vorn mit `:` oder ` - `, oder am Ende nach `-`/`–`/`—`.
- Ende „Hörspiel“ für Apple-Platzhalter-Titel: ein angehängtes „. Das Hörspiel“, „- Hörspiel“, „Original-Hörspiel zur …“ o. ä. fällt weg.

### Klammerregel
Klammerzusätze `( … )` und `[ … ]` ohne Ziffer fallen beim Titelvergleich weg (z. B. „(Das Original-Hörspiel zur TV-Serie)“). Mit Ziffer („Teil 2“, „Neuauflage 2025“) bleiben sie, dann gibt es meist keinen Treffer.

## 2. Funktionen in Worten

### 2.1 `woerter(text)`
Normalisieren, in Wörter zerlegen, Füllwörter, Allerweltswörter und einzelne Buchstaben entfernen. „Die drei !!!“ und „Die drei ???“ ergeben beide `["drei"]` (Satzzeichen zählen nicht).

**Nachtrag Projektleitung (18.11., nach der Messung, gilt für OS2):** Vor dem Zerlegen wird „???“ zu `fragezeichen` und
„!!!“ zu `ausrufezeichen` (jeweils drei oder mehr gleiche Zeichen). Gemessen hing an dem Gleichstand genau eine falsche
sichere Nummer („Der Super-Papagei“ im Eintrag „Die drei !!!“ → 1 aus einem Album von „Die drei ???“). Die übrigen 22
Gleichstände (Peppa Pig / Peppa Pig Hörspiele, Bibi & Tina / Bibi und Tina …) ändern sich dadurch nicht. Die Zahlen in
Abschnitt 4 dieser Datei sind **vor** dem Nachtrag gemessen.

### 2.2 Nummer abtrennen
Siehe die Muster oben. Ergebnis: `(Nummer oder nichts, Rest)`. Andere Zahlen im Text bleiben.

### 2.3 Serienwörter abziehen und Titel vergleichen
Beide Titel werden von Klammerzusätzen ohne Ziffer befreit, die Nummer wird abgetrennt, dann fallen die Wörter des Seriennamens **unseres Eintrags** aus beiden weg. „Titel genau gleich“ heißt: die Wortlisten nach dem Abzug sind gleich und nicht leer, **oder** die vollen Wortlisten (mit Serienwörtern) sind gleich (so bleiben Titel vergleichbar, die dem Seriennamen entsprechen).

### 2.4 Ähnlichkeit
`difflib.SequenceMatcher(None, a, b).ratio()` auf den mit Leerzeichen verbundenen Wörtern (nach dem Abzug; sind sie leer, die vollen Wörter). Für Seriennamen ohne Abzug, nur `woerter`.

### 2.5 Tonie-Treffer (4.2)
- Kandidaten: benutzbare Tonies, deren `series`- oder Titelwörter mit den Wörtern unseres Seriennamens oder Folgentitels überlappen und deren `episodes` gesetzt ist; der Titel muss gleich sein oder die Ähnlichkeit mindestens 0,92 erreichen.
- **sicher**: Titel gleich, Serie gestützt (Ähnlichkeit der Seriennamen mindestens 0,85 und keine Sprachkurs-Reihe), Trackzahl gleich (Tonie-Tracks 0 heißt „unbekannt“ und passt), und nicht „eine Datei bei uns, drei und mehr Tracks beim Tonie“.
- **unsicher**: Ähnlichkeit mindestens 0,92 bei gleicher bekannter Trackzahl, oder Titel gleich bei anderer Trackzahl, oder Titel gleich bei gleicher Trackzahl, aber Serie nicht gestützt.
- **Dubletten (mehrere sichere Kandidaten)**: Die Felder, die sie liefern (Art, Nummer), werden nur unter den Kandidaten verglichen, die einen Wert haben. Stimmen sie überein, bleibt es sicher; bei Widerspruch gilt „keiner“. Für die Shopseite zählt bei Dubletten nur der Kandidat mit gleicher Trackzahl (größer 0); ein einzelner sicherer Kandidat zählt immer.
- Nummer des Tonies: abgetrennte Nummer aus `episodes`. Art des Tonies: Kategorie-Tabelle oben.
- **Reihen-Stimme für den Namen** (nur Auslegung, 2.8): Titel gleich, Tonie-Trackzahl bekannt, größer 0 und gleich unserer, keine Sprachkurs-Reihe, nicht Datei-gegen-drei-Tracks, mindestens 1 Titelwort; die Stimmen müssen auf genau eine `series` (nach `woerter`) fallen.

### 2.6 Apple Fassung A und B (4.3)
Je Suchergebnis (Album `wrapperType = collection` oder Hörbuch `audiobook`), das nicht ausgeschlossen ist:
- **Fassung A**: alle Wörter unseres Seriennamens stehen im `artistName`.
- **Fassung B**: alle Wörter stehen im `collectionName`.
- **A oder B (Regel)**: eins von beiden. Gemessen wurden A, B und die Vereinigung getrennt; die Vereinigung gilt.
- **Passt sicher**: Serie nach A/B/Vereinigung, Titel gleich, bekannte Nummer und Albumnummer nicht verschieden, und Genre Hörspiele (Album) bzw. Hörbuch-Typ. Ein gleicher Titel mit Musikgenre oder anderem Genre ist nur unsicher.
- **Passt unsicher**: Serie nach A/B/Vereinigung und (Titel gleich, aber Nummernkonflikt oder anderes Genre) oder die Apple-Schwellen oben.
- Stufen der Suche: Stufe 1 je Folge „Serienname + Folgentitel“ (ohne Nummer und Klammern, Serienname nicht doppeln, höchstens 100 Zeichen), je Album und Hörbuch. Platzhalter-Titel und Titel gleich Serienname gehen direkt zu Stufe 2. Stufe 2 „nur Serienname“ (je Eintrag einmal), wenn Stufe 1 weder sicher noch unsicher traf.

### 2.7 Cover mit Reihen-Album (4.3, 4.7)
- Eintrag mit **einer Folge** oder Einzeltitel: das Folgen-Cover. **Sicher**, wenn genau eine `collectionId` sicher als Album passt. Mehrere sichere Alben mit verschiedener `collectionId`: unsicher. Hörbuch-Treffer und unsichere Treffer: höchstens unsicher.
- Eintrag mit **zwei oder mehr Folgen**: Nur ein **Reihen-Album** zählt: ein Album, dessen Name (nach `woerter`) genau dem Seriennamen entspricht, Genre Hörspiele, nicht ausgeschlossen (bei Fassung A zusätzlich Serie im Künstler). Genau eine `collectionId`: sicher; mehrere: unsicher. Ohne Reihen-Album ist ein Folgen-Cover höchstens unsicher. Höchstens ein Cover-Vorschlag je Eintrag.
- Bild: aus `artworkUrl100` über das feste Muster des letzten Pfadstücks auf `600x600bb.jpg`.
- Vorhandenes eigenes Cover (`eigen`) wird nie automatisch ersetzt. Tobias hat bestätigt: Das Cover eines Real-Kinofilm-Hörspiels (Mulan) wurde falsch sicher gewählt; die Regel bleibt trotzdem.

### 2.8 Name des Eintrags (4.6): nur Vorschlag
Die Regel (Stimmen von Tonie und Apple für eine Reihe, mindestens die Hälfte der Folgen und mindestens zwei) hat im Messlauf Sammelnamen („Disney“, „Europa-Park“) und Autoren/Interpreten („Otfried Preußler“, „Janosch“) geliefert und ist **nicht** abgenommen. Tobias: Ein Name wird **nie automatisch** nach dieser Regel geändert. Das Urteil darüber trifft Claude (Dienst `ai_task.generate_data`, Entität `ai_task.claude_ai_task`), siehe `claude/anfrage_vorlage.json` in den Fixtures. Dessen Namen müssen wörtlich aus der Eingabe stammen (Kandidatenname, Ordnername oder Teil davor vor „ - “), sonst gilt das Urteil als unsicher.

### 2.9 Nummer (4.4) mit Stütze T2
Nummern-Quellen: sicherer Tonie (abgetrennte Nummer aus `episodes`) und Apple-Alben, die „passen sicher“ **und** die Nummer stützen. Eine Apple-Nummer zählt nur, wenn (A) die Reihe im `artistName` steht, oder (B) die Serienwörter im `collectionName` **außerhalb** des Teils stehen, der unserem Folgentitel entspricht (z. B. „Bibi Blocksberg, Folge 89: Die Junghexenbande“). Enthält unser Titel alle Serienwörter (z. B. Titel gleich Seriennamen), stützt B die Nummer nie. Nur Tonies bleiben dann. Gilt nur für die Nummer, nicht für Cover, Art oder Beschreibung.
**Sicher**: Alle Quellen mit Nummer nennen dieselbe. Verschiedene Nummern: unsicher. Nur unsichere Quellen: unsicher.
„Automatisch“ ersetzt wird nur, wenn der Prüfgrund passt (6.1).

### 2.10 Folgentitel-Bildung T1 (4.5)
- **Abgleich** (sicher/unsicher) nur über ein Apple-Album, Regeln wie 2.6.
- **Neuer Titel im Normalfall**: der heutige Titel Wort für Wort, davor „Folge N: “, wenn die Nummer bekannt ist (sichere Nummer, sonst `nummer`, sonst Nummer aus der Anzeige). Ein vorhandenes Nummernpräfix („Folge 121:“, „121_“, „03_“, „3 - “) wird zu „Folge N: “ vereinheitlicht, nicht verdoppelt. Ohne Nummer: kein neuer Titel (bestätigt).
- **Teil/Band**: Steht die Nummer schon als „Teil N“ oder „Band N“ im Titel (vorn mit `:` oder ` - `, oder am Ende nach `-`/`–`), bleibt der Titel unverändert (kein „Folge N:“ davor). Gleiches N: bestätigt. Anderes N: Titel bleibt unverändert, Zeile ist unsicher.
- **Steht „Folge N:“ erst nach einem Text** („Gute-Nacht-Geschichten, Folge 15: …“): Titel bleibt unverändert.
- **Nur bei Platzhalter**: Apples Albumtitel, Klammerzusätze ohne Ziffer weg, „. Das Hörspiel“ u. ä. am Ende weg, Serienname vorn nur weg, wenn danach ein Trennzeichen kommt (` - `, `: `, `. `, `, `), dazu „Folge N: “ bei bekannter Nummer. Ein Platzhalter-Titel kann nie wortgleich mit einem Album sein, deshalb wird `folge_titel` bei Platzhaltern nie sicher; automatisch ersetzt wird nur, wenn der Abgleich sicher wäre.
- **Änderungsart** (für Anzeige): nur Präfix dazu oder vereinheitlicht = „Form“; Platzhalter ersetzt = „Wörter“.

### 2.11 Art (4.7)
Je Folge: sicher, wenn ein sicherer Treffer sie liefert und keine Quelle widerspricht. Quellen: Tonie-Kategorie; Apple-Album mit Genre Hörspiele (`hoerspiel`); Apple-Hörbuch (`hoerbuch`) **nur**, wenn für dieselbe Folge kein Album gefunden wurde; Musikgenre-Album nur unsicher. Ein Apple-Treffer mit gleichem Titel, aber anderem Genre (Pop, Soundtrack …), widerspricht und macht die Art unsicher. Art des Eintrags: Mehrheit (mehr als 50 %) der Folgen mit sicherer Art, mindestens die Hälfte aller Folgen. Übernommen wird nur bei `art_quelle = geraten`.
Beobachtung: Einträge, deren Apple-Album „Hörspiel“ im Namen trägt, aber die Art `hoerbuch` ergibt (z. B. „Die Muppets (Hörspiel zum Kinofilm)“), kommen vor, wenn das Album nur als Hörbuch-Typ gefunden wurde. Die Regel ist unverändert.

### 2.12 Beschreibung und Alter (4.9)
1. Sicherer Tonie-Treffer und eine Shopseite aus der Sitemap (`/de-de/tonies/<serie-slug>/<folge-slug>/`; Slug klein, `ae/oe/ue/ss`, sonst `-`; genau, dann als Endung; auch mit `episodes` ohne Nummer; höchstens 2 Seiten je Folge). Aus `__NEXT_DATA__` → `props.pageProps.product`: `salesId` muss gleich `model` sein, sonst nichts. `description` (HTML zu Text, höchstens 2000 Zeichen), `ageMin` (ganze Zahl 0 bis 18, Text aus Ziffern wird zur Zahl, sonst verworfen).
2. Sonst die Beschreibung eines Apple-Hörbuchs, wenn es sicher passt (Serie im Titel oder Künstler, gleiche Nummer wenn bekannt, gleicher Titel) und genau eine `collectionId` mit Beschreibung vorliegt. Nur Beschreibung, kein Alter. Die Art bestimmt dieser Eintrag nicht.
3. Sonst leer. Es gibt keine unsicheren Beschreibungen.

## 3. Messstand des vollen Laufs (18.11.)
- Tonie-Liste: 6709 Einträge, davon 4979 mit `language = de-de` (alle mit `model`), davon **4873 benutzbar** und **106 wegen Sprachmerkmalen ausgeschlossen**. Deutsche Shopseiten in der Sitemap: 577.
- Apple: 1963 Anfragen (voller Lauf plus Pilot), alle mit Status 200, kein 429 und kein 403, keine Pause.
- Shopseiten: 129 abgerufen, 125 mit passender `salesId` und Feldern; keine Weiterleitung von `tonies.com`.

## 4. Fixtures
`homeassistant/tests/fixtures/online/`: Apple-Antworten (nur Body), Auszug der Tonie-Liste, gekürzte Shopseiten, Sitemap-Auszug, aufgezeichnete Antworten von Claude und `erwartung.json` mit dem Ergebnis dieser Regeln je Fall. Die Tests von OS2 prüfen die Funktionen gegen `erwartung.json`.

## 5. Auslegungen (wo das Design offen war)
1. Ähnlichkeit = difflib.SequenceMatcher auf den mit Leerzeichen verbundenen Wörtern (nach Abzug der Serienwörter; sind sie dann leer, die vollen Wörter).
2. Klammerzusätze ohne Ziffer ('(Das Original-Hörspiel zur TV-Serie)') werden beim Titelvergleich entfernt, mit Ziffer ('(Teil 2)', '(Neuauflage 2025)') bleiben sie (dann kein Treffer).
3. Folgentitel 'genau gleich' (4.1/4.2/4.3): Nummer abgetrennt und Serienwörter abgezogen auf beiden Seiten gleich, oder die vollen Wörter (mit Serienwörtern) gleich. Zusätzlich zu den genannten Formen wird auch '<Präfix>, Folge N: Rest' abgetrennt (Tonie-episodes und Apple-Hörbücher tragen das).
4. Nummer aus Apple (Entscheidung Tobias): nur wenn die Reihe im artistName steht (A) oder die Serienwörter im collectionName außerhalb des zum Folgentitel passenden Teils stehen (B); enthält unser Titel alle Serienwörter (z. B. Titel = Serienname), stützt B die Nummer nie, dann nur Tonies. Gilt nur für die Nummer (und das 'Folge N:' im neuen Titel), nicht für Cover, Art, Beschreibung.
5. Bekannte Nummer einer Folge = `nummer`, sonst die aus der Anzeige abgetrennte ('Folge 3: …'). Nummer 4.4 'aendert' vergleicht aber mit dem Feld `nummer` (leer -> N zählt als Änderung).
6. Tonie-Treffer: Serie 'gestützt' = Ähnlichkeit >= 0,85 und keine Sprachkurs-Reihe (Marker: englisch lernen, english, …); Sprachkurs-Reihen sind nie sicher und nie Reihen-Stimme. Titel-Ähnlichkeit >= 0,92 bei gleicher Trackzahl (bekannt) -> unsicher; Titel gleich bei fremder Trackzahl -> unsicher; Titel gleich, Serie nicht gestützt -> unsicher.
7. Dubletten (GR-5): 'in den Feldern, die sie liefern' = nur Kandidaten mit einem Wert zählen; Widerspruch (zwei verschiedene Arten oder Nummern) -> keiner (Flag dublette_widerspruch).
8. Tonie-Kategorien: audio-play, audio-play-educational -> hoerspiel; audio-book -> hoerbuch; music, 'Musik' -> musik; *-songs -> nur unsicher (musik); creative-tonie, leer, 'Hörspiele & Hörbücher', Sonstiges -> keine Art.
9. Apple 'passt sicher' (4.3): Serie (alle woerter) im artistName (Fassung A) oder im collectionName (Fassung B) oder einem von beiden (U), Titel gleich, nicht ausgeschlossen, Genre 'Hörspiele' (Album) bzw. wrapperType audiobook; Musikgenre mit gleichem Titel -> nur unsicher; bekannte Nummer und Albumnummer verschieden -> nur unsicher. Apple 'unsicher': Serie wie oben, >= 80 % der Titelwörter im Album, höchstens zwei Zusatzwörter, keine zusätzliche Zahl.
10. Ausschluss: Token box/bundle/film/kino/single/alle/best/musical/komplett/edition, Teilstrings sammlung/collection/soundtrack/jubilaeum/edition/komplett/bundle, '/' im Namen, mehr als 40 Titel UND mehr als das Doppelte der Folgen-Trackzahl (Eintrag: Summe der Tracks).
11. Apple-Stufen: Stufe 1 je Folge ('Serie Titel', Serienname nicht doppelt, ohne Nummer/Klammern, <= 100 Zeichen; Platzhalter-Titel und Titel = Serienname gehen direkt zu Stufe 2); Stufe 2 'nur Serienname' (je Serie einmal), wenn Stufe 1 weder sicheren noch unsicheren Treffer (Fassung U) hatte. Je Stufe Album + Hörbuch (2 Anfragen).
12. Cover (Eintrag): bei >= 2 Folgen (nicht einzeln) zählt nur ein Reihen-Album (collectionName = nur Serienname, Genre Hörspiele): genau eines (eine collectionId) -> sicher, mehrere -> unsicher; ohne Reihen-Album ist ein Folgen-Cover höchstens unsicher. Bei einer Folge/Einzeltitel gilt das Folgen-Cover. Hörbuch-Treffer liefern Cover höchstens unsicher. Mehrere sichere Alben mit verschiedener collectionId -> unsicher.
13. Cover 'aendert': heutiges Cover ist `auto` (Tags) oder keins; `eigen` zählt als geschützt (aendert = False, Zeile als 'eigen' markiert).
14. Art (4.7) aus Apple: sicher nur von Album-Treffer 'Hörspiele' (-> hoerspiel) oder von Hörbuch-Treffer (-> hoerbuch) nur, wenn kein Album derselben Folge gefunden wurde (GR-4). Musikgenre-Album -> höchstens unsicher. 'Keine Quelle widerspricht': ein Apple-Treffer mit gleichem Titel, aber anderem Genre (Pop usw.) widerspricht und macht die Art unsicher. Art des Eintrags: Mehrheit (> 50 %) der Folgen mit sicherer Art, mindestens die Hälfte aller Folgen.
15. Serienname (4.6): Reihen-Stimme je Folge = Tonie mit Titel gleich + gleicher bekannter Trackzahl (> 0), keine Sprachkurs-Reihe, genau eine Reihe (ohne Serienstütze, sonst könnte nie umbenannt werden), oder Apple-Album 'Hörspiele' mit gleichem Titel (>= 2 Wörter), nicht ausgeschlossen, genau eine collectionId (Reihe = artistName). Sicher: Stimmen derselben Reihe (nach woerter) bei >= der Hälfte der Folgen und >= 2 (bei einer Folge: diese). 'wuerde_uebernommen' zusätzlich: Prüfgrund serie_aus_interpret/ordner an einer Folge und kein anderer Eintrag trägt den Namen. Stimmt die Reihe mit dem heutigen Namen überein: sicher, aber bestätigt.
16. Neuer Folgentitel (Entscheidung Tobias): heutiger Titel Wort für Wort, davor 'Folge N: ' bei bekannter Nummer (sicherer Treffer, sonst heutige Nummer/Nummer aus der Anzeige); vorhandenes Präfix ('Folge 121:', '121_', '03_') wird vereinheitlicht. Ohne Nummer: kein neuer Titel. Nur bei Platzhalter: Apple-Albumtitel (Nummer als 'Folge N: ', Klammerzusätze und '. Das Hörspiel' am Ende weg, Serienname vorn nur vor Trennzeichen).
17. Folgentitel (4.5): Abgleich (sicher/unsicher) nur über Apple, sicheres Album; 'aendert' = Zeichenkette weicht ab; 'form' = nur Präfix dazu/vereinheitlicht, 'woerter' = Platzhalter ersetzt. Steht die Nummer schon als 'Teil N'/'Band N' im Titel (vorn mit ':'/' - ', am Ende nach '-'/'–'), bleibt der Titel unverändert; bei anderem N zusätzlich 'unsicher'.
18. Beschreibung/Alter: 'nicht_geholt', solange eine nötige Shopseite (sicherer Tonie, Seite in der Sitemap) oder die Apple-Daten fehlen. Sitemap-Slug: genau, dann als Endung, Varianten episodes und episodes ohne Nummer; höchstens 2 Seiten je Folge.
19. Fassung A/B: Die Reihen-Stimmen für Serienname und das Reihen-Album gelten in beiden Fassungen gleich (bei A zusätzlich Serie im Künstler des Reihen-Albums).
20. Versuch Platzhalter-Titel: eine zusätzliche Anfrage 'Serie Folge N' (nur Album) je Platzhalter-Folge mit bekannter Nummer; nicht in 'sicher' eingerechnet.
21. (b) der Kandidaten nach 5.3: berechnet mit und ohne das Merkmal 'Folge ohne Beschreibung' (heute hat keine Folge eine, mit dem Merkmal wären es alle).

**Nachtrag T4 (Tobias, 18.11., gilt für OS2):** Steht im Apple-Albumnamen „Hörspiel“ (nach `woerter`: `hoerspiel`), ergibt der
Treffer die Art `hoerspiel`, auch bei `wrapperType = audiobook`. Gemessen betraf das 6 sichere Einträge (vorher `hoerbuch`).
