# Goldfisch-Prüfung OS2: `online_quellen`, `online_abgleich`, `online_ki`

Stand 18.11. Prüfer: Goldfisch (ohne Vorgeschichte). Nichts geändert, nur gelesen und gerechnet.

## Was geprüft wurde

- Code (neu, nicht committet): `homeassistant/custom_components/tobibox/online_quellen.py`, `online_abgleich.py`, `online_ki.py`.
- Tests und Fixtures: `homeassistant/tests/test_online_quellen.py`, `test_online_abgleich.py`, `test_online_ki.py`,
  `homeassistant/tests/fixtures/online/` (README, `erwartung.json`, `ergaenzung_os2.json`).
- Maßstab: `docs/designs/online-suche.md` (0a, 3.1 bis 3.4, 4 mit Anhang 4.A, 7.4, 8.1 bis 8.4, Zeile OS2 in 12),
  `docs/egm/online-suche/os1_regeln.md` (mit den Nachträgen „???/!!!“ und T4),
  `docs/egm/online-suche/os0_entwurf/claude_anweisung.md`.
- Lauf der drei Testdateien: 630 bestanden, 2,3 s. Sockets sind durch das HA-Testplugin gesperrt (`pytest_socket`), die Tests
  laufen also ohne Netz.
- Eigene Stichproben mit kleinen Skripten (nicht im Repo) gegen den Text, nicht gegen die Tests; die Belege stehen bei den Befunden.

Nicht beanstandet (geprüft, stimmt mit dem Maßstab überein): Host-Prüfung (`.mzstatic.com`, IP, Port, Userinfo, http, Punkt am Ende),
höchstens 3 eigene Sprünge mit derselben Prüfung, `allow_redirects=False`, Zeitgrenzen 10 s und 60 s, Größe auf entpackte Bytes
in Blöcken, User-Agent ohne Kennungen und nicht überschreibbar, Auswertung im Executor, Drossel mit reservierten Anteilen
(10 von 15, 15 von 30), 3 Verbindungen je Host, 15 min Pause bei 429/5xx (Shop und Sitemap gemeinsam), Shop 1 je 4 s,
Shop 403 als `online_shop_format` ohne Wiederholung, 5-s-Grenze der Suche von Hand, Ersetzungsregel der Tonie-Liste
(1000, ±50 %, alte Datei bleibt, ETag, atomar, 7 Tage), Sitemap nur `<loc>`, `__NEXT_DATA__`, `salesId == model`, `ageMin` 0 bis 18,
Zwischenspeicher (7 Tage/500, 15 min/4). Alle Konstanten und Wortlisten in `online_abgleich.py` gleichen `os1_regeln.md` Wort für Wort.
„???“/„!!!“ und T4 sind umgesetzt, es gibt keine automatische Namensregel. `ANWEISUNG` ist zeichengleich mit dem Textblock in
`claude_anweisung.md`. Die Eingabe enthält nur die genannten Felder, keine `model`, keine `collectionId`; Begrenzer werden auch nach dem
Entfernen noch einmal geprüft; Zeitgrenze 30 s, Drossel 3 s / 60 je Stunde im Lauf / 200 am Tag, Ausfälle werfen nicht.
Öffentliches Repo: in den neuen Dateien keine lokalen Pfade, Tokens, Adressen oder Namen von Kindern oder der Partnerin.

## Befunde

### GO2-1 (Fehler): Naht `parse_itunes` zu `online_abgleich`: Das Cover geht verloren

- Stelle: `online_quellen.py:447-449` (`parse_itunes` gibt nur `bild_url`, schon 600 px, und lässt `artworkUrl100` weg);
  `online_abgleich.py:771`, `837`, `1144`, `1256` (der Abgleich liest `artworkUrl100`); Modulkopf `online_abgleich.py:52-53`
  („Die Umrechnung auf 600 px macht `online_quellen.py`“).
- Designstelle: 3.3 (benutzte Felder, 600 px über festes Muster), 4.3 (Cover), Zeile OS2 in 12 (beide Module als ein Paket).
- Beleg: `parse_itunes(mulan_album.json)` liefert die Schlüssel `wrapperType, collectionName, artistName, primaryGenreName,
  releaseDate, collectionId, trackCount, bild_url`. Gibt man diese Liste an `bewerte_eintrag`, ist der Cover-Treffer
  `status = sicher`, aber `neu = None`. Mit dem rohen iTunes-JSON kommt dieselbe Adresse (100 px) heraus. Die Tests von
  `online_abgleich` benutzen nur das rohe JSON, die von `online_quellen` prüfen `bild_url` nur für sich; die Naht ist in keinem Test.
- Folge: Der Dienst in OS3 würde „sicher, aber ohne Bild“ bekommen. Die zwei Module widersprechen sich in dem, was die Umrechnung
  tut: Der Abgleich erwartet 100 px und rechnet nichts um, das Quellenmodul rechnet schon um und verwirft das Original.
- Vorschlag: Eine Seite festlegen. Entweder `parse_itunes` behält zusätzlich `artworkUrl100` (nur nach `bild_url_600`
  geprüft, sonst weglassen), oder der Abgleich liest `bild_url` und gibt 600 px weiter. Dazu ein Test über beide Module
  (`parse_itunes` -> `bewerte_eintrag` -> `cover.neu` ist eine `600x600bb.jpg`-Adresse).

### GO2-2 (Lücke): HTML in Namen und Genre aus Apple und der Tonie-Liste bleibt stehen

- Stelle: `online_quellen.py:439-442` (`_ITUNES_TEXTE` gehen nur durch `online_text`), `online_quellen.py:547-554`
  (`tonie_eintrag`); Test `test_online_quellen.py:745-749`.
- Designstelle: 8.1 („Typprüfung je Feld; kein HTML aus fremden Quellen erreicht die Seite“), 6.3 (`online_text`).
- Beleg: Antwort mit `collectionName = "<img src=x onerror=alert(1)>Name"` und `artistName = "<b>A</b>"` kommt aus `parse_itunes`
  unverändert heraus. Nur `description` wird zu Text. Der Test heißt `test_parse_itunes_html_in_texten_wird_zu_text`, prüft aber nur
  `description` und dass `\x00` fehlt; das `<b>B</b>` im `collectionName` wird nicht beanstandet.
- Folge: Diese Texte laufen später in Übersichten (Namen von Treffern), in Vorschläge und in die Eingabe an die KI. Ob die Seite
  (OS4) immer maskiert, steht hier nicht fest; das Design legt die Sperre ausdrücklich auf die Quelle.
- Vorschlag: Für Name, Künstler, Genre und Tonie-Texte eine Prüfung wie bei `description` (Tags weg oder Eintrag verwerfen) oder im
  Design festhalten, dass die Seite alles maskiert, und den Test umbenennen. Test mit Tags in `collectionName`, `artistName`,
  `series`, `episodes` ergänzen.

### GO2-3 (Lücke): Beschreibung aus Apple wird „sicher“, obwohl die Shopseite noch aussteht

- Stelle: `online_abgleich.py:1166-1177`.
- Designstelle: 4.9 (Shop zuerst, Apple nur „sonst“), `os1_regeln.md` Auslegung 18 („nicht_geholt, solange eine nötige Shopseite
  fehlt“), Kopf von `online_abgleich.py:51`.
- Beleg: Folge mit sicherem Tonie, Seite in der Sitemap, aber noch nicht abgerufen (`shop_daten = {}`), dazu ein sicheres
  Apple-Hörbuch mit Beschreibung: `alter_ab = nicht_geholt`, aber `beschreibung = sicher` mit Quelle `apple_hoerbuch`.
- Folge: Ein Aufrufer, der „sicher“ übernimmt, nimmt Apples Text, bevor die Shopseite da ist; nach dem Abruf käme ein anderer
  Text. Der Apple-Zweig steht vor der Prüfung `ausstehend`.
- Vorschlag: Ist `ausstehend` wahr, `nicht_geholt` zurückgeben, bevor der Apple-Zweig drankommt.

### GO2-4 (Lücke): „…, Folge N: …“ im Titel mit anderem N wird nicht unsicher

- Stelle: `online_abgleich.py:1090-1099` (nur `teil_band_nummer`), `865-876`.
- Designstelle: 4.5 Fall 1 („Steht die Nummer schon als „Teil N“ / „Band N“ **oder als „…, Folge N: …“** im Titel, bleibt er
  unverändert (bei anderem N: unsicher)“). `os1_regeln.md` 2.10 nennt das „unsicher“ nur für Teil/Band; das Design ist weiter.
- Beleg: Anzeige „Gute-Nacht-Geschichten, Folge 15: Der Mond“, Tonie und Apple nennen 16: Nummer `sicher 16`, Folgentitel
  `sicher`, `neu` unverändert, kein `grund`. Bei „Teil 15: Der Mond“ mit derselben Lage wird der Titel `unsicher` (Grund
  „Teil/Band 15 im Titel, Nummer 16“).
- Vorschlag: Dieselbe Prüfung für die Form „…, Folge N:“ (die Nummer steht schon in `nummer_abtrennen`/`_RE_PRAEFIX`).
  Oder im Design/`os1_regeln.md` klarstellen, dass nur Teil/Band gemeint ist, und einen Test festschreiben.

### GO2-5 (Lücke): Gleicher Titel mit Genre außerhalb der Musikliste widerspricht der Art nicht

- Stelle: `online_abgleich.py:678-684` (`apple_art` gibt für Klasse `sonst` `None`), `1121-1127`.
- Designstelle: `os1_regeln.md` 2.11 und Auslegung 14: „Ein Apple-Treffer mit gleichem Titel, aber **anderem Genre** (Pop,
  Soundtrack …) widerspricht und macht die Art unsicher“.
- Beleg: Hörspiel-Album „Die Hexenparty“ plus Album gleichen Titels, gleicher Künstler, Genre „Comedy“: Art `sicher`. Mit Genre
  „Pop“ `unsicher`. Der Widerspruch hängt am Eintrag `art` des unsicheren Treffers, und der ist bei `sonst` leer. Der Test
  `test_art_klasse_und_t4` bestätigt `sonst -> None`, prüft aber den Widerspruch nur mit Pop.
- Vorschlag: Klären, ob „anderes Genre“ alle Genres meint (dann Widerspruch auch bei `sonst`, z. B. über `grund = genre:…`
  ohne Art-Wert) oder nur die Musikliste (dann in `os1_regeln.md` 2.11 so festhalten) und einen Test dazu schreiben.

### GO2-6 (Kleinigkeit): Ohne jede Liste sperrt eine ungültige erste Antwort eine Woche

- Stelle: `online_quellen.py:958` (`_abgeglichen = jetzt` vor der Prüfung), `943`, Test `test_online_quellen.py:1064`.
- Designstelle: 3.1 („sonst bleibt die alte Datei“ setzt eine alte Datei voraus).
- Beleg: Der Test `test_tonie_liste_ohne_liste_und_verworfen_wartet_eine_woche` legt das ausdrücklich fest: Kommt beim ersten
  Laden z. B. `[]` oder eine zu kleine Liste, gibt es 7 Tage keinen neuen Abruf (nur `erzwingen`). In dieser Zeit gibt es keine
  Tonie-Treffer, keine Shopseiten, kein Alter.
- Vorschlag: Nur wenn schon eine brauchbare Liste vorliegt, den Abruf der Woche verbuchen; sonst die Stunden-Sperre
  (`TONIE_VERSUCH_ABSTAND_S`) gelten lassen.

### GO2-7 (Kleinigkeit): `grund` kann nach dem Entschlüsseln von Entitäten wieder wie HTML aussehen

- Stelle: `online_ki.py:251` (`html_zu_text` mit `convert_charrefs=True`, danach nur `online_text`).
- Designstelle: 3.4 („`grund` durch `online_text`“), 8.1, `claude_anweisung.md` („reiner Text“).
- Beleg: `grund = "&lt;script&gt;alert(1)&lt;/script&gt; <b>x</b>"` ergibt den Vorschlag mit `grund = "<script>alert(1)</script> x"`.
  Ein `grund` aus nur Tags (`<script>…</script>`) wird dagegen als `grund_ungueltig` verworfen, obwohl das Design nur
  `online_text` verlangt (kürzen, nicht verwerfen).
- Vorschlag: Nach `html_zu_text` die Zeichen `<` und `>` entfernen oder ersetzen; im Design festhalten, dass ein leerer `grund` den
  Vorschlag verwirft (so macht es der Code schon).

### GO2-8 (Kleinigkeit): „Titel gleich Serienname“ wird als Zeichenkette verglichen

- Stelle: `online_abgleich.py:652-656`.
- Designstelle: 3.3 („Titel gleich Serienname gehen gleich zur zweiten Stufe“).
- Beleg: Serie „Bibi & Tina“, Folge „Bibi und Tina“: Stufe 1 ist „Bibi und Tina“, Stufe 2 „Bibi & Tina“ (zwei Anfragen mit
  gleichem Sinn). Gleiches bei „Die drei ???“ und „Die drei Fragezeichen“.
- Vorschlag: Wortlisten vergleichen (`woerter(rest) == woerter(serie)`).

### GO2-9 (Kleinigkeit): „N:“ ohne Leerzeichen wird nicht abgetrennt

- Stelle: `online_abgleich.py:238` (`_RE_ZAHL` verlangt `\s+` nach `:` und `.`).
- Designstelle: `os1_regeln.md` 1 („nur `N:` bzw. `N. ` am Anfang“), 4.1 („N:“, „N.“).
- Beleg: `nummer_abtrennen("3:Titel")` gibt `(None, "3:Titel")`, `"3: Titel"` gibt `(3, "Titel")`.
- Vorschlag: Bei `:` das Leerzeichen freistellen (bei `.` bleibt es nötig, wegen Dezimalzahlen), oder im Messskript
  `regeln.py` nachsehen, was gemessen wurde.

## Zu den Tests (Punkt 6)

- Die Fälle aus 8.4 sind abgedeckt: fremde Weiterleitung, Host-Täuschung (rund 35 Adressen), gzip-Bombe (Strom ohne Ende und eine echte
  gzip-Nutzlast durch aiohttps Entpacker), leere und kleine Tonie-Liste, Shopseite ohne Felder, `ageMin` als Text; bei Claude Entität
  leer, Dienst fehlt, Zeitüberschreitung, ungültige Antwort, Name nicht in der Eingabe, `grund` mit HTML und zu lang, Name gleich
  heute, Drossel, Tagesgrenze. Die Marke `claude` ist OS3.
- Nicht zirkulär: Der Abgleich wird gegen `erwartung.json` aus OS1 geprüft, mit genau einer begründeten Ausnahme (`muppets/art`, T4);
  die Eingabe an die KI gegen die aufgezeichnete Eingabe aus OS1; Anweisung und `structure` gegen die Markdown-Datei.
  Kleine Schwäche: `test_online_abgleich.py` liest Shopseiten mit einem eigenen Hilfsparser statt mit `parse_shop` (Zeilen 62-72); die Naht
  `parse_shop` -> Abgleich ist so auch nur über die Form der Daten gesichert. Die schwerere Lücke ist GO2-1.
- Der Name `test_parse_itunes_html_in_texten_wird_zu_text` verspricht mehr, als geprüft wird (GO2-2).

## Weitere Hinweise (kein Befund zu OS2)

- Im Arbeitsbaum liegen unversioniert `box/config/tobibox.toml.vor-13` und `box/config/tobibox.toml.vorher`. Sie gehören nicht zu OS2.
  Ich habe keine Geheimnisse darin gefunden (Suche nach Passwort, WLAN, Token), sie sollten aber nicht versehentlich mit committet werden.

## Gesamturteil

Solide und nah am Design; vor der Abnahme von OS2 muss GO2-1 (Naht Cover) behoben und mit einem Test über beide Module gesichert werden, GO2-2 bis GO2-5 sind vor OS3 zu klären, der Rest sind Kleinigkeiten.

## Auflösung (Projektleitung, 18.11.)

Maßstab für den Abgleich ist der in OS1 gemessene und abgenommene Stand. Befunde, bei denen der Port genau wie das Messskript
rechnet, bleiben deshalb unverändert (im Code mit „Wie OS1 gemessen“ markiert); eine Änderung wäre eine neue Regel und bräuchte
Tobias.

| Befund | Entscheidung |
|---|---|
| GO2-1 | **behoben:** `parse_itunes` behält `artworkUrl100` neben `bild_url`; neuer Test über beide Module `test_online_naht.py` |
| GO2-2 | unverändert: Namen bleiben roh, damit der Abgleich wie gemessen rechnet. Schutz an der Ausgabe: OS3 schickt jeden Wert durch `online_text` (6.3), die Seite zeigt nur Text (10). Auflage an OS3/OS4 |
| GO2-3 | unverändert, wie OS1 gemessen (Apple-Hörbuch vor „nicht geholt“). Auflage an OS3: Beschreibung erst bewerten, wenn die Shopseiten der sicheren Tonies geholt sind (Vorrang 4.9) |
| GO2-4 | unverändert, wie OS1 gemessen |
| GO2-5 | unverändert, wie OS1 gemessen (nur die Klassen `musik`, `hoerspiel`, `hoerbuch` widersprechen) |
| GO2-6 | **behoben:** ohne jede Tonie-Liste neuer Versuch nach 1 Tag, mit Liste nach 7 Tagen |
| GO2-7 | **behoben:** `grund` nur durch `online_text` (≤ 160), wie Design 3.4 |
| GO2-8 | unverändert, wie OS1 gemessen (eine Anfrage mehr, kein falscher Treffer) |
| GO2-9 | unverändert, wie OS1 gemessen |
