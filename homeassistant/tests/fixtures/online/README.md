# Fixtures der Online-Suche (aus dem Trockenlauf OS1, 18.11.)

Stand 18.11. Zweck: Tests der Online-Suche (Design 8.4) ohne Netz.

## Herkunft
- `itunes/`: Rohantworten (nur Body) der iTunes-Suche (`itunes.apple.com/search`, `country=de`, `limit=25`), geholt im
  Trockenlauf OS1 am 18.11. Der Dateiname nennt den Fall; das Suchwort steht in `erwartung.json` bzw. unten.
  Die Felder `description` und `longDescription` sind **auf höchstens 200 Zeichen gekürzt** (am Wortende, mit „…“); sonst unverändert.
- `tonies_auszug.json`: Auszug aus der Tonie-Liste der Gemeinschaft (`tonies-json`, Zweig `release`), nur die Felder
  `model`, `series`, `episodes`, `tracks`, `release`, `category`, `language`.
- `shop/`: Shopseiten von `tonies.com` auf den `__NEXT_DATA__`-Block mit `props.pageProps.product` gekürzt (`salesId`,
  `description`, `ageMin`). Die `description` ist **gekürzt** (höchstens 2 kurze Sätze, höchstens 200 Zeichen, als `<p>`); `ageMin` und `salesId` sind unverändert.
- `sitemap_auszug.xml`: 20 `<loc>` aus `sitemap_products_1.xml`.
- `claude/`: aufgezeichnete Antworten von `ai_task.generate_data` (Claude über die HA-Entität `ai_task.claude_ai_task`) mit der Eingabe, dazu
  `anfrage_vorlage.json` (aktueller Anweisungstext aus `urteil.py`, `structure`). Die Antworten entstanden mit genau diesem Anweisungstext (Lauf vom 18.11., ab 15:07).
- `erwartung.json`: Ergebnis der Regeln aus OS1 je Fall und Feld (sicher/unsicher/keiner, neuer Wert) und die Urteile von Tobias.

## Gewonnen
Mit dem Messskript OS1 (Trockenlauf, nur lesende Abrufe; Antworten zeitnah am 18.11.). Nichts wurde nachträglich
verändert, außer den Kürzungen bei Shopseite und Tonie-Liste.

## Künstlich
- `shop/*_kuenstlich.html` (ohne Felder, `ageMin` als Text, falsche `salesId`).
- Fälle mit `kuenstlich: true` in `erwartung.json` (Blümchen „in Italien“, Bibi Folge 100, Peppa „Das neue Haus“, Hotzenplotz):
  der Eintrag ist ein Testeintrag, die Apple-Antwort ist echt.
- Alle iTunes-Dateien sind echt; die Pop-/Soundtrack-/„Alle Hörspiele“-Alben zu Hotzenplotz stehen in der echten Antwort.

## Suchwörter
- `itunes/hotzenplotz_pop_soundtrack_alle_83titel.json`: „Der Räuber Hotzenplotz“ (music/album), 9 Ergebnisse
- `itunes/bibi_folge100_album_mit_jubilaeum.json`: „Bibi Blocksberg Die große Hexenparty“ (music/album), 2 Ergebnisse
- `itunes/bibi_folge100_buch.json`: „Bibi Blocksberg Die große Hexenparty“ (audiobook), 2 Ergebnisse
- `itunes/blumchen_in_italien_album.json`: „Benjamin Blümchen in Italien“ (music/album), 3 Ergebnisse
- `itunes/blumchen_in_italien_buch.json`: „Benjamin Blümchen in Italien“ (audiobook), 4 Ergebnisse
- `itunes/peppa_das_neue_haus_album.json`: „Peppa Pig Das neue Haus“ (music/album), 3 Ergebnisse
- `itunes/mulan_album.json`: „Mulan“ (music/album), 25 Ergebnisse
- `itunes/toy_story_2_album.json`: „Toy Story 2“ (music/album), 25 Ergebnisse
- `itunes/fuenf_freunde_121_album_gekuerzter_titel.json`: „Fünf Freunde und die verlassene Jagdhütte“ (music/album), 1 Ergebnisse
- `itunes/olchis_geburtstagsreise_buch.json`: „Die Olchis auf Geburtstagsreise“ (audiobook), 2 Ergebnisse
- `itunes/olchis_geburtstagsreise_album_ohne_treffer.json`: „Die Olchis auf Geburtstagsreise“ (music/album), 0 Ergebnisse
- `itunes/sternenschweif_teil1_album.json`: „Sternenschweif Geheimnisvolle Verwandlung“ (music/album), 1 Ergebnisse
- `itunes/sternenschweif_teil1_buch.json`: „Sternenschweif Geheimnisvolle Verwandlung“ (audiobook), 2 Ergebnisse
- `itunes/muppets_album.json`: „Die Muppets“ (music/album), 3 Ergebnisse
- `itunes/muppets_buch_hoerbuch_genre.json`: „Die Muppets“ (audiobook), 7 Ergebnisse

## Datenschutz
Die Fixtures enthalten einige echte Einträge der Bibliothek, nämlich öffentliche Hörspieltitel (zum Beispiel Mulan,
Toy Story 2, Fünf Freunde Folge 121, Die Olchis, Sternenschweif, Die Muppets, Die drei !!!, Pyjamahelden, Das kleine
Gespenst, Janosch) mit Anzeige- und Ordnernamen. Im Verzeichnis `claude/` stehen diese Namen samt Ordnernamen, die
teils Autoren nennen (öffentlich). Es gibt keine IDs der Bibliothek, keine Tobie-Namen, keine Adressen und keine Zugangsdaten.

## Ergänzung OS2
`ergaenzung_os2.json` (neu, 18.11.): Antworten, die zu Fällen in `erwartung.json` gehören, aber in `itunes/` und
`tonies_auszug.json` fehlen (die Fälle wurden in OS1 mit dem ganzen Eintrag und allen Anfragen gemessen).
- Echt (aus dem OS1-Cache, nur die Felder, die der Abgleich braucht; `description` auf höchstens 200 Zeichen gekürzt wie oben):
  Hörbuch-Suche „Der Räuber Hotzenplotz“ und „Toy Story 2“ (je die zur Serie passenden Treffer, dazu ein fremder Kinder-Treffer als Gegenprobe; Übriges, etwa Erotik und Sachbücher, ist weggelassen), das Album „Folge 122“ der Fünf-Freunde-Antwort
  zu „Fünf Freunde und der Großalarm in Kirrin“, der Tonie `2000003223` aus der Tonie-Liste (Felder wie in `tonies_auszug.json`).
- Künstlich: die vier Hotzenplotz-Alben `900001` bis `900004` (Gegenprobe OS1: Pop, Soundtrack, „Alle Hörspiele“, Hörspiel-Album „1: …“).
- Im Test erfunden bleiben nur neutrale Zusatzfolgen („Weitere Folge …“), damit ein Eintrag mehrere Folgen hat.
- Nichts davon steht in `erwartung.json` abgeschrieben.
