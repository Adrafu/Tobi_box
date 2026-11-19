# Online-Suche für Cover und Angaben: Design (angenommen 18.11.)

Angenommen von Tobias am 18.11. („Ja, annehmen“, Rev. 2.1); Rev. 2.2 ist eine Korrektur der Projektleitung nach der
Annahme (`resolve.md` Runde 3). Entstehung, Reviews und Resolve: `docs/egm/online-suche/`. Die Schwellen in Abschnitt 4
sind im Trockenlauf OS1 gemessen und von Tobias abgenommen (Anhang 4.A). Die Verträge (Abschnitt 9) hat Tobias am 18.11.
freigegeben (OS0, „Ja, freigeben“); sie stehen in `docs/protocol/ha-websocket-v1.md` und `docs/data-model.md`.

Stand 19.11., **Rev. 2.5** (Fragen aus OS2, T5 bis T7 von Tobias, `resolve.md` Runde 6: Vorrang der Tonie-Kategorie vor T4 in 4.7,
drei zusätzliche Eingabefelder an Claude in 3.4 und 8.3, Ausnahme im Test „keine Modellnamen“ in 3.4).
Rev. 2.4 (Goldfisch OS0 über Design und Vertragsentwurf: `review_goldfisch_os0.md`, Befunde GO-1 bis GO-18, `resolve.md` Runde 5; Stellen mit „(GO-n)“ gekennzeichnet).
Rev. 2.3 (Ergebnis des Trockenlaufs OS1: Entscheidungen R6, R7, T1 bis T3 von Tobias, `resolve.md`
Runde 4; Name nie automatisch, Namensvorschläge von Claude; Folgentitel behält den Wortlaut; Nummer strenger; Anhang 4.A).
Die mit **(PL)** markierten Folgen in 4.6, 4.8, 5.5, 9 hat Tobias am 18.11. bestätigt (13).
Rev. 2.2: Korrektur nach der Annahme (Marke `zurueckgenommen`, Kandidaten des Laufs, Reihenfolge OS2;
`resolve.md` Runde 3). Rev. 2.1: Auflagen der Kurzprüfung `review_goldfisch_rev2.md` (G2-1 bis G2-14).
Rev. 2: Runde 1 der Goldfische (`resolve.md`: R1 bis R5 von Tobias, Rest (PL)). Rev. 1: erster Entwurf.
Grundlage: `concepts_brief.md` (Entscheidungen O1 bis O16, Prüfung vom 18.11. in Abschnitt 7), Faktenbericht zum Code
vom 18.11. (Abschnitt 1), Reviews `review_goldfisch_backend.md` (GB) und `review_goldfisch_regeln.md` (GR).
Verträge: `docs/protocol/ha-websocket-v1.md` („Vertrag W“), `docs/data-model.md`. Pfade im Code relativ zu
`homeassistant/custom_components/tobibox/`.

## 0. Ziel

Die Bibliothek in HA bekommt **gute Cover, richtige Nummern, die richtige Art und, wo es sie gibt,
Beschreibung und Alter**, ohne dass ein Mensch Hunderte Einträge von Hand pflegt. Quellen sind die Tonie-Liste der
Gemeinschaft, die Tonie-Shopseite und die iTunes-Suche von Apple. Sichere Treffer übernimmt HA selbst, mit Hinweis für
alle und Rücknahme für Administratoren; unsichere werden Vorschläge. Den Namen eines Eintrags ändert HA nie selbst; Claude schlägt ihn nur vor (4.6; GO-8). Eigene Eingaben gehen immer vor. Die Boxen merken
davon nichts.

Was realistisch ist: Die Namen der Bibliothek sind nach den Läufen vom 14.11. meist gut. Der Lauf über den Rest bringt vor
allem Cover, Art, Nummern, Beschreibung und Alter. Alter gibt es nur für Tonies, die gerade im Shop sind (18.11.: 577
deutsche Seiten), Beschreibungen zusätzlich aus Apples Hörbuch-Einträgen.

## 0a. Entscheidungen (gültiger Stand)

| Nr. | Inhalt |
|---|---|
| O1, O8, O16, R3 | Suche liefert Cover, Namen, Nummer, Art, Beschreibung, Alter. Beschreibung und Alter je Folge; Beschreibung von der Tonie-Shopseite, sonst aus Apples Hörbuch-Eintrag, wenn er sicher zur Folge passt (auch für Hörspiele); Alter nur von der Tonie-Shopseite; sonst leer |
| O2, O11 | Von Hand und beim Einsortieren; sichere Treffer gleich übernehmen, sonst Vorschlag |
| O3, O13 | Quellen: iTunes-Suche (Titel gehen an Apple) und Tonie-Liste `tonies-json`; Tonie-Shopseite für Beschreibung und Alter |
| O4 | Nichts davon auf die Boxen |
| O5, O10 | Neue Uploads, Suche von Hand, Lauf über den Rest |
| O6, R2 | Ohne Nachfrage nur bei genauem Treffer („Titel und Künstler genau“); höchstens **1 falscher in 50** sicheren Treffern je Feld, gemessen im Trockenlauf vor der Vertragsfreigabe. **Ausnahmen (GO-9):** Cover 1 von 29 (Mulan), von Tobias angenommen (T3); Nummer: T2 an der alten Stichprobe geprüft, keine neue gezogen (die strengere Regel nimmt nur Zeilen weg) |
| O7, R1 | Suchen, Übernehmen, Zurücknehmen, Vorschläge: nur Administratoren. Den Hinweis „Aus der Online-Suche übernommen“ sehen **alle** |
| O9 | „Online-Suche gerade nicht erreichbar, später noch einmal.“ Alles andere geht weiter |
| O12 | Art nur setzen, wo sie geraten ist |
| O14 | Treffer von Hand: Übersicht mit Häkchen, alle gesetzt, abwählbar; von Hand gesetzte Felder ohne Häkchen |
| O15 | Zusammenführen nur als Vorschlag (von Claude, 4.8); Verschieben entfällt (4.8, bestätigt 18.11.) (GO-8) |
| R4 | Beschreibung in der Folgenzeile nur auf Tipp (eigener Knopf); Alter „ab 3“ in der Nebenzeile |
| R5 | Quellen heißen auf der Seite „Apple“ und „Tonies“ |
| R6, R7 | Den **Namen des Eintrags** ändert die Online-Suche **nie automatisch**, weder nach Regel noch nach Claude. Claude (Integration in HA) macht **Vorschläge mit Grund** (4.6). Gemessen in OS1 |
| T1 | Folgentitel: der heutige Wortlaut bleibt; dazu nur „Folge N: “; Apples Titel nur für Platzhalter (4.5) |
| T2 | Nummer von Apple nur, wenn Apple die Reihe als Künstler nennt oder sie im Album getrennt vom Titel steht (4.4) |
| T3 | Cover: Regel bleibt, obwohl „Kinofilm“ den Ausschluss „Film/Kino“ umgeht (1 falscher in 29, Mulan) |
| T4 | Art: Steht im Albumnamen „Hörspiel“ (nach `woerter` `hoerspiel`), ergibt der Treffer `hoerspiel`, auch bei `wrapperType = audiobook` (Tobias 18.11.; betraf 6 sichere Einträge; 4.7) |

## 1. Heutiger Stand (Faktenbericht 18.11., ergänzt durch GB)

| Bereich | Stand | Folge |
|---|---|---|
| Bibliothek | 341 Einträge, 820 Folgen, 122 mit Nummer; 173 „bitte ansehen“; Art 259 geraten; Cover 233 aus Tags, 99 eigen, 9 keins | Stichprobe: Namen meist gut, `pruefen` oft ohne Grund |
| Einsortieren | `eingang.py` `_serie_abarbeiten` (:1148) unter der Serien-Sperre; `_dauer_merken` (:1256) stößt Hintergrundarbeit an; Rückweg im Speicher `_rueckweg` (:585, gefüllt :1257), später in der Protokollzeile (:1384, :1409) | Andocken neben `_dauer_merken` (5.1), Rückweg fortschreiben (5.1) |
| Herkunft | nur `art_quelle`; für Name, `anzeige`, `nummer` nichts. `nummer` setzt nur das Einsortieren (kein Befehl) | Schnappschuss „unberührt“ (6.1) |
| Prüfgründe | `serie_art_setzen` (`media.py:1018-1026`) nimmt nur `art_geraten` heraus, `pruefen` nur beim letzten Grund; `einsortierung/bestaetigen` setzt auch das Eingangsprotokoll zurück (`eingang.py:675`) | je Grund auflösen (5.5) |
| Cover | Vorrang in `cover.py:233-241` (`cover_zustand`), `:242-257` `lese_cover_datei`, `:283-297` `uebernimm_cover`, `:494-508` `entferne_eigen`, `:622-645` `neu_suchen`; Sync nimmt `cover*.jpg` aus (`box/src/tobibox/sync.py:82`); Seite prüft nur `cover_quelle === 'eigen'` (`frontend/seiten/cover.js:254`) | dritte Datei (7.2) |
| `art_quelle` | `serie_aus_json` macht aus einem unbekannten Wert `manuell` (`media.py:233-234`, `const.py:113`) | `ART_QUELLEN` erweitern (9.2) |
| Stores | `Store(hass, 1, key)` ohne Migration; `medieninfo` hängt an Löschen, Verschieben, Zusammenführen, `neu_einsortieren.py` (:403, :423), `dauer.py:148` (`bereinige`); Papierkorb-Restore stellt nichts wieder her | Store `tobibox.online` an denselben Stellen (7.3) |
| Netz | keine ausgehenden Anfragen; `manifest.json` nur `Pillow` | Regeln in 8 |
| Ereignisse | `ws_subscribe` ohne `themen` abonniert alles (`websocket_api.py:217`); `Hub.emit` kennt keine Rolle | Thema `online` nur für Administratoren (9.3) |
| Seite | `seiten/serie.js` (`serieMenue` :299, `_zeile` :775, `_ansehen` :737, `brauchtPruefung` :62); Tipp auf eine Folgenzeile spielt (AM11, AM13); Technik-Unterseiten nach `docs/designs/ha-oberflaeche.md` 5.9 | 10 |

## 2. Begriffe

- **Quelle:** `tonies` (Tonie-Liste), `tonies_shop` (Shopseite), `itunes`. Auf der Seite „Tonies“ bzw. „Apple“ (R5).
- **Feld:** `serie_name`, `folge_titel` (= `folgen_info.anzeige`), `nummer`, `art`, `cover`, `beschreibung`, `alter_ab`.
- **sicher / unsicher:** Ergebnis der Regeln in Abschnitt 4, je Feld. Nur sicher wird ohne Nachfrage übernommen.
- **Schnappschuss („unberührt“):** der Wert eines Felds, den Einsortieren oder Online-Suche zuletzt gesetzt haben.
- **von Hand:** ein Feld, dessen Wert nicht mehr dem Schnappschuss entspricht, oder das ein Mensch gewählt hat (6.1).
- **Änderung:** eine Übernahme mit Vorher- und Nachher-Werten; zurücknehmbar (6.4).
- **Vorschlag:** ein unsicheres Feld, ein Name von Claude (3.4) oder ein Zusammenführen; wartet auf einen Administrator.

## 3. Quellen

### 3.1 Tonie-Liste (`tonies-json`)

- Feste Adresse `https://raw.githubusercontent.com/toniebox-reverse-engineering/tonies-json/release/tonies.json`
  (etwa 6,3 MB, 18.11.: 6 709 Einträge). Laden beim ersten Bedarf, danach höchstens einmal je 7 Tage, mit ETag.
- Auswerten im Executor. **Ersetzen nur**, wenn die Antwort eine gültige Liste ist, mindestens 1 000 benutzbare deutsche
  Einträge hat und sich deren Zahl um höchstens ±50 % geändert hat; sonst bleibt die alte Datei.
- Abgelegt wird nur, was benutzt wird: `model`, `series`, `episodes`, `tracks` (Zahl und Titel), `release`, `category`,
  als `<config>/tobibox/tonies.json` (atomar). `pic` (Figur) wird nicht benutzt.
- Benutzbar: `language = de-de`, `model` gesetzt, Titel ohne Merkmale anderer Sprachen (polnische, finnische,
  italienische Buchstaben und Wörter; Liste als Konstante, GR-10).
- Die Tonie-Liste **bestätigt** (Treffer, Trackzahl, Art, Nummer, Weg zur Shopseite). Sie ist **keine** Quelle für neue
  Folgentitel, weil `episodes` oft nur ein Bruchstück ist („als Babysitter“, GR-6).

### 3.2 Tonie-Shopseite

- Nur für Beschreibung und Alter, nur für Folgen mit sicherem Tonie-Treffer (4.2).
- Seite finden: Sitemap (`https://tonies.com/sitemap_products_1.xml`, `_2.xml`, höchstens 5 MiB, einmal je 7 Tage)
  nennt `/de-de/tonies/<serie-slug>/<folge-slug>/`, ohne Artikelnummer. Slug aus `series` und `episodes` (klein, `ae/oe/ue/ss`,
  sonst `-`), Suche genau, dann als Endung; höchstens 2 Seiten je Folge.
- Nach dem Abruf: `__NEXT_DATA__` → `props.pageProps.product`; `salesId` muss gleich `model` sein, sonst nichts.
  Bei Dubletten der Tonie-Liste (4.2) nur die Seite des Kandidaten mit gleicher Trackzahl.
- Übernommen: `description` (HTML → Text mit `html.parser`, Absätze bleiben, höchstens 2 000 Zeichen), `ageMin`
  (ganze Zahl 0–18, sonst verworfen).
- Grenzen: nur Tonies im Shop; keine offizielle Schnittstelle. Fehlen die Felder oder antwortet die Seite 403, gilt
  `online_shop_format` (einmal je Tag ins Protokoll), ohne Wiederholung.
- Ergebnis je Folge im Store (7.3); kein neuer Abruf, außer bei einer Suche von Hand.

### 3.3 iTunes-Suche

- `https://itunes.apple.com/search?country=de&lang=de_de&limit=25&…`; je Stufe zwei Anfragen: Alben
  (`media=music&entity=album`) und Hörbücher (`media=audiobook`).
- **Zwei Stufen** (GR-22): erst **je Folge** Serienname + Folgentitel (ohne Nummer, ohne Klammerzusätze, Seriennamen nicht
  doppelt, höchstens 100 Zeichen), bei keinem Treffer **einmal je Eintrag** nur der Serienname. Platzhalter-Titel und
  Titel gleich Serienname gehen gleich zur zweiten Stufe. Gemessen (OS1): im Mittel 5,8 Anfragen je Eintrag.
- Benutzt: `wrapperType`, `collectionId`, `collectionName`, `artistName`, `primaryGenreName`, `trackCount`,
  `releaseDate`, `artworkUrl100` (Größe nur über ein festes Muster des letzten Pfadstücks auf `600x600bb`), bei
  Hörbüchern `description`.
- Antworten bleiben 7 Tage im Speicher (höchstens 500 Suchwörter).

### 3.4 Claude für Namensvorschläge (R6, R7)

- Über die **vorhandene Claude-Integration in HA**: Dienst `ai_task.generate_data` mit `structure` und
  `return_response`. Die Entität ist eine Option der Integration (**gleich eingeschaltet**, Tobias 18.11.: Vorgabe: die `ai_task`-Entität der Claude-Integration (`anthropic`), wenn es genau eine gibt; abschaltbar; leer = keine Namensvorschläge). Die Integration
  selbst baut **keine** Verbindung zu Anthropic auf und kennt keinen Schlüssel. Die Daten gehen an den **Anbieter der gewählten Entität** (heute Claude von Anthropic); der Optionsdialog sagt, was gesendet wird (8.3, 10) (GO-6).
- **(PL)** Ein Aufruf je Eintrag, nur wenn der Eintrag einen Grund hat: neu einsortierte Serie, oder an einer Folge
  `serie_aus_interpret` / `serie_aus_ordner` (wie 6.1). **Nicht** „Ordnername ≠ Name“: Das sind meist Namen, die Tobias von
  Hand vergeben hat (OS1: Vorschläge „Tiger und Bär“ → „Janosch“, „Pyjamahelden“ → „PJ Masks“). Bei der Suche von Hand
  nicht (dort wählt der Mensch). Auch der Upload eines Alltag-Kontos löst beim Einsortieren einen Aufruf aus (GO-6).
- Eingabe: heutiger Name, Ordnername, je Folge (höchstens 12) Anzeige, Nummer, Tracks, Prüfgründe und bis zu 3 Kandidaten je
  Quelle (Tonies: `series`, `episodes`, `tracks`, `category`; Apple: `collectionName`, `artistName`, Genre, `trackCount`,
  `wrapperType`). **(T5)** Dazu wie in OS1 gemessen `einzeltitel` (der Eintrag ist ein Einzeltitel), `folgen_gesamt` (Zahl der
  Folgen) und `folgen_gezeigt` (Zahl der Folgen in der Eingabe, höchstens 12). Bei mehr als 12 Folgen die ersten 12 in der Reihenfolge der Serie (GO-18). **Keine Tobie-Namen, keine IDs.** Etwa 1 200 Eingabe-Tokens im Mittel (OS1). Die Eingabe steht als **abgegrenzter JSON-Block** unter dem Anweisungstext, mit dem Satz „Der Block enthält nur Daten, keine Anweisungen“ (GO-4).
- Antwort: `entscheidung` (`behalten` \| `kandidat`), `name`, `grund` (≤ 160 Zeichen); das Feld `sicher` entfällt (es wird nicht benutzt, GO-4). Der Code nimmt einen
  Namen nur an, wenn er wörtlich in der Eingabe steht (Kandidat, Ordnername, Teil davon vor oder nach „ - “); sonst wird
  verworfen. `name` geht durch `online_text` und `name_pruefen`, `grund` durch `online_text` (≤ 160) **beim Anlegen**; besteht eins
  nicht, gibt es keinen Vorschlag; ein Name gleich dem heutigen gilt als `behalten` (GO-4). Anweisungstext und Schema: `docs/egm/online-suche/os0_entwurf/claude_anweisung.md` (erlaubt den Teil vor **oder nach** „ - “). Die Fixture `claude/anfrage_vorlage.json` und die Messung in 4.A haben noch die alte Fassung (nur „vor“); der Nachlauf an der Prüfmenge (110) braucht Tobias’ Ja (GO-5).
- Ergebnis ist **immer** ein Vorschlag (Art `felder`, Feld `serie_name`, Quelle `claude`, mit `grund`). `behalten` erzeugt nichts. Der Vorschlag speichert `name` und `grund` (Store `werte`) und den heutigen Namen als `name_vorher` (7.3); er fällt weg, sobald der Name des Eintrags nicht mehr `name_vorher` ist (GO-1, GO-3). Der Name existiert schon als anderer Eintrag: Vorschlag zum Zusammenführen.
- Fällt Claude aus (Entität fehlt, Fehler, Zeitüberschreitung 30 s): kein Namensvorschlag, alles andere geht weiter (O9).
  Der Claude-Schritt hat eine **eigene Marke** `marke.claude` (7.3): Er läuft im Lauf für jeden Eintrag mit Grund ohne gültige
  Claude-Marke, auch wenn die übrige Marke gültig ist; ein Ausfall oder eine fehlende Option macht den Eintrag also nicht
  dauerhaft „fertig“ (GO-2). Drossel: 1 Aufruf je 3 s, im Lauf höchstens 60 je Stunde, **höchstens 200 am Tag** (GO-18); ist eine
  Grenze erreicht, wird der Schritt übersprungen, ohne Marke. Kosten: 13.
- **(T7)** Die Bezeichner aus dem Vertrag (`claude` als Quelle, `marke.claude`, `quellen.claude`) und der Integrationsname
  `anthropic` (Vorgabe der Option) stehen im Code. Der Test „keine Modellnamen im Code“ (`tests/test_texte.py`) erlaubt deshalb
  genau `claude` und `anthropic`; andere Modellnamen (`sonnet`, `haiku` …) bleiben verboten. Umsetzung in OS3.

## 4. Abgleich: wann ist ein Feld sicher

Der Trockenlauf OS1 hat die Regeln an der echten Bibliothek gemessen (Abschnitt 12, R2; Ziel höchstens 1 falscher in 50
sicheren Treffern je Feld). Die Regeln unten sind der **abgenommene Stand** nach OS1; Messung und Urteile: Anhang 4.A.
Gemessen wurde die Vereinigung beider Fassungen in 4.3 („Serie im Künstler **oder** im Album“).

### 4.1 Wörter und Nummern

- `woerter(text)`: klein, `ß→ss`, Umlaute `ae/oe/ue`, Akzente weg, **„???“ → `fragezeichen`, „!!!“ → `ausrufezeichen`**
  (OS1: sonst sind „Die drei ???“ und „Die drei !!!“ gleich, eine falsche sichere Nummer), Folgen aus `[a-z0-9]`, ohne Füllwörter (der, die, das,
  und, ein, im, mit, von …) und ohne Allerweltswörter (hörspiel, hörspiele, folge, teil, band, vol, original,
  ungekürzt …). Einzelne Buchstaben fallen weg. Listen als Konstanten.
- **Nummer abtrennen** (GR-2, GR-9): Eine vorn stehende Nummer in der Form „Folge N:“, „Folge N -“, „N:“, „N.“,
  „Teil N“, „Band N“ wird vor dem Vergleich abgetrennt, in Apples Albumnamen und in Tonie-`episodes`. Die Zahl ist ein
  Kandidat für `nummer`. Andere Zahlen bleiben im Text.
- **Serienwörter abziehen** (GR-6): Vor dem Vergleich zweier Folgentitel fallen die Wörter des Seriennamens aus beiden.

### 4.2 Tonie-Treffer

- Kandidaten: benutzbare Tonies (3.1), deren `series`- oder `episodes`-Wörter mit Serienname oder Folgentitel überlappen.
- **sicher:** Folgentitel nach 4.1 genau gleich **und** Serie gestützt (Ähnlichkeit der Seriennamen ≥ 0,85) **und**
  gleiche Trackzahl (Tracks = 0 heißt „unbekannt“ und zählt nicht als ungleich) **und nicht** „eine Datei bei uns, drei
  und mehr Tracks beim Tonie“. Mehrere sichere Kandidaten: sicher bleibt es, wenn sie in den Feldern, die sie liefern
  (Art, Nummer), übereinstimmen (Neuauflagen, GR-5); sonst keiner.
- **unsicher:** Ähnlichkeit ≥ 0,92 bei gleicher Trackzahl, oder genauer Titel bei anderer Trackzahl.
- Reihen mit Zusatz („Englisch lernen“ und andere Sprachkurse) gelten nie als gestützte Serie für den Treffer einer Folge (eine automatische Umbenennung gibt es nicht mehr, 4.6; GO-8).

### 4.3 Apple-Treffer und Cover

- Ausschluss vorab: Namen mit Box, Bundle, Sammlung, Collection, Film, Kino, Soundtrack, Musical, Single, Alle, Edition,
  Komplett, Best of, Jubiläum oder „/“ zwischen zwei Titeln (welche als ganzes Wort und welche als Wortteil gelten, steht
  in `docs/egm/online-suche/os1_regeln.md`; „Film“, „Kino“ nur als ganzes Wort, T3); Alben mit mehr als doppelt so vielen
  Titeln wie die Folge **und** mehr als 40 Titeln (gemessen OS1).
- **Album passt sicher zu einer Folge** („Titel und Künstler genau“, O6, GR-1): Serienname steht (nach `woerter`
  vollständig) in `artistName` **oder** in `collectionName`, **und** der Folgentitel nach 4.1 ist gleich dem Albumnamen nach
  4.1 (Nummer und Serienwörter abgezogen), **und** Genre „Hörspiele“ (Album) bzw. Hörbuch-Typ.
- **Cover sicher:** Ein Album passt sicher und es gibt **kein** zweites sicheres Album mit anderem `collectionId`.
  Musikgenre: höchstens unsicher (GR-3). Für Einträge mit mehreren Folgen wird ein **Reihen-Album** bevorzugt (Album, das
  nur aus dem Seriennamen besteht); ein Folgen-Cover ist dort höchstens unsicher. Höchstens **ein** Cover-Vorschlag je
  Eintrag (GR-18).
- **unsicher:** mindestens 80 % der Wörter passen, höchstens zwei zusätzliche Wörter, keine zusätzliche Zahl.
- Beide Fassungen der Prüfung (Serie im Künstler, Serie im Album) gelten („oder“); getrennt gemessen in OS1 (Anhang 4.A).

### 4.4 Nummer

Kandidaten aus Apple (4.1, sicheres Album) und aus der Tonie-Liste (abgetrennte Nummer in `episodes`). **sicher**, wenn
beide gleich sind, oder wenn eine Quelle sie nennt, die andere nicht widerspricht und der Titel genau passt. Eine
vorhandene `nummer` wird nur geändert, wenn sie noch dem Schnappschuss entspricht (6.1).

**Apple-Nummer nur aus der eigenen Reihe (T2):** Ein Album liefert eine Nummer nur, wenn die Reihe in `artistName` steht,
**oder** die Serienwörter in `collectionName` **außerhalb** des Teils stehen, der dem Folgentitel entspricht („Bibi
Blocksberg, Folge 89: Die Junghexenbande“). Heißt die Folge wie die Serie (Einzeltitel), stützt der Albumname die Nummer
nicht; sonst käme sie aus der Zählung einer fremden Reihe („Eine Weihnachtsgeschichte“ → 16 aus „Der kleine König“).
Gilt nur für die Nummer, nicht für Cover, Art, Beschreibung.

### 4.5 Folgentitel

Abgleich wie bisher: sicher nur mit sicherem Apple-Album. Der **neue Wert** (T1):

1. **Normalfall:** der heutige Titel **Wort für Wort**, davor „Folge N: “, wenn die Nummer bekannt ist (4.4). Ein
   vorhandenes Präfix („Folge 121:“, „121_“, „03_“, „3 - “) wird vereinheitlicht, nicht verdoppelt. Steht die Nummer schon
   als „Teil N“ / „Band N“ oder als „…, Folge N: …“ im Titel, bleibt er unverändert (bei anderem N: unsicher). Ohne Nummer:
   bestätigt, kein neuer Wert. Apples Albumtitel ändert hier **kein Wort** (Apple kürzt oft: „Folge 121: und die
   verlassene Jagdhütte“; Serienwörter gehören oft zum Titel: „Toy Story 2“, „Die Olchis und der schwarze Pirat“).
2. **Platzhalter** („Track 01“, „Folge 3“, „Kapitel 1“): Apples Albumtitel, Nummer als „Folge N: “, Klammerzusätze und
   „. Das Hörspiel“ am Ende weg; der Serienname vorn fällt nur weg, wenn danach „ - “, „: “, „. “ oder „, “ kommt.

Automatisch übernommen wird nur Fall 2 (leerer oder Platzhalter-Titel); Fall 1 ist sonst Vorschlag. In OS1 wurde kein
Platzhalter sicher (ein Platzhalter ist nie wortgleich mit einem Album), automatische Folgentitel kommen also praktisch
nicht vor.

### 4.6 Serienname: nie automatisch (R6, R7)

Der Name des Eintrags wird **nie automatisch** geändert. Die frühere Regel (Reihe aus Tonie-`series` oder Apple-Künstler)
fiel in OS1 durch: Tonie-`series` ist oft ein Sammelname („Disney“, „Europa-Park“, „Lieblings-Literatur“, „Maus“), Apples
Künstler oft Autor oder Interpret („Otfried Preußler“, „Janosch“). Auch das Urteil von Claude erreicht die Schwelle nicht
(Anhang 4.A: 22 von 25 „sicheren“ Antworten richtig; „Die drei !!!“ → „Die drei ???“).

- Namensvorschläge kommen **nur von Claude** (3.4), immer als Vorschlag mit Grund. Ohne Claude gibt es keine.
- Ein Vorschlag, dessen Name schon ein anderer Eintrag trägt (nach `woerter`), wird ein Vorschlag zum Zusammenführen (4.8).
- Bei der Suche von Hand bietet die Übersicht den Namen eines Treffers wie bisher zur Wahl an (ohne Häkchen, O14).
- Der Ordnername bleibt immer; deshalb findet der Eingang die Serie auch nach einer Umbenennung (GB-23).

### 4.7 Art (nur wo `art_quelle = geraten`, O12)

- Tonie `category`: `audio-play`, `audio-play-educational` → `hoerspiel`; `audio-book` → `hoerbuch`; `music` → `musik`;
  `*-songs` → unsicher; `creative-tonie`, leer, Sonstiges → keine Art (GR-10).
- Apple: Album mit Genre „Hörspiele“ → `hoerspiel`; Musikgenres (Kinderlieder, Kindermusik, Pop, Klassik …) → `musik`;
  `wrapperType = audiobook` → `hoerbuch` **nur**, wenn kein Album derselben Folge gefunden wurde (GR-4).
  **(T4)** Steht im Albumnamen „Hörspiel“ (nach `woerter` `hoerspiel`), ergibt der Treffer `hoerspiel`, auch bei
  `wrapperType = audiobook`. **(T6)** Die Tonie-Kategorie geht T4 vor (wie gebaut: „Der kleine Prinz“ bleibt `hoerbuch`, weil
  die Tonie-Liste `audio-book` sagt). Durch T4 werden außerdem „Der kleine Wassermann“ und „Die kleine Hexe“ sicher `hoerspiel`;
  Tobias hat beides am 19.11. bestätigt.
- **sicher**, wenn ein sicherer Treffer sie liefert und keine Quelle widerspricht. Art der Serie = Mehrheit der Folgen mit
  sicherer Art, mindestens die Hälfte der Folgen.

### 4.8 Zusammenführen und Verschieben (nur Vorschlag, O15)

- **Zusammenführen:** Der von Claude vorgeschlagene Name (4.6) existiert schon als anderer Eintrag. Einzeltitel nie als Ziel.
- **Verschieben: entfällt** (PL, bestätigt von Tobias 18.11.: „Ja, entfallen“). Die Reihe kam aus Tonie-`series`; in OS1 hatten 6 von 7
  Vorschlägen ein Sammel-Ziel („Disney“, „Die Eule mit der Beule“ für Grolltroll-Lieder); nur „Mickys total verrücktes
  Fußballspiel“ aus dem Eintrag „Disney“ nach „Micky Maus“ (Quelle Apple) war plausibel. Verschieben bleibt Handarbeit
  (`folge/verschieben`).
- Ausgeführt nur auf Tipp über `serien/zusammenfuehren` (Tobies, Sterne, Hördaten ziehen mit).

### 4.9 Beschreibung und Alter (R3)

1. Sicherer Tonie-Treffer mit geprüfter Shopseite (3.2): Beschreibung und Alter.
2. Sonst Apples Hörbuch-Eintrag, wenn er **sicher** zur Folge passt: gleiche Reihe (im Titel oder Künstler), gleiche
   Nummer (wenn eine bekannt ist) und gleicher Titel nach 4.1. Nur Beschreibung. Gilt auch für Hörspiel-Folgen; die Art
   bestimmt dieser Eintrag nicht.
3. Sonst leer. Es gibt keine unsicheren Beschreibungen. Bei der Suche von Hand zeigt die Übersicht die Beschreibung jedes
   Treffers zur Wahl.

### 4.A Anhang: Trockenlauf OS1 (18.11.)

Messskript außerhalb von HA (nur lesend: `serien/list`, `serie/get`, Cover; dazu Apple, Tonie-Liste, Tonie-Shop mit den
Drosseln aus 8.2). Der gemessene Regelstand (Konstanten, Auslegungen) steht in `docs/egm/online-suche/os1_regeln.md`.
**Grenze der Messung:** Bei Art, Beschreibung und Alter hat Tobias „alle richtig“ ohne Einzelhäkchen gemeldet; dieselbe
Antwort bei der Nummer übersah 2 Fehler, die erst über die Folgentitel auffielen (T2). Bibliothek: 340 Einträge (`typ = normal`), 819 Folgen. Auswahlseite mit Stichproben an Tobias, Urteile
Feld für Feld im Chat; Entscheidungen in `docs/egm/online-suche/resolve.md` Runde 4. Fixtures:
`homeassistant/tests/fixtures/online/` (gekürzte Auszüge, ohne Bibliotheksdaten).

**Ergebnis je Feld** (abgenommener Stand, Fassung A oder B; „übernommen“ = HA würde im heutigen Bestand automatisch
ändern, nach 6.1 ohne Schnappschuss):

| Feld | Einheit | sicher | unsicher | keiner | übernommen | Stichprobe | falsch | Urteil |
|---|---|---|---|---|---|---|---|---|
| Cover | Eintrag (340) | 29 | 146 | 165 | 16 | alle 29 | 1 (Mulan, Realfilm) | Regel bleibt (T3) |
| Name | Eintrag | – | – | – | 0 | 4 von 50 (abgebrochen) | 3 von 4 | nie automatisch, Vorschläge von Claude (R6, R7) |
| Folgentitel | Folge (819) | 245 | 85 | 489 | 0 | 50 + 50 | Alben 0; Titelbildung 23 (Runde 1) | Wortlaut bleibt, nur „Folge N: “ (T1) |
| Nummer | Folge | 117 | 19 | 683 | 0 | 50 | 2 (vor T2) | strenger (T2), danach 0 in der Stichprobe |
| Art | Eintrag | 142 | 143 | 55 | 36 | 50 | 0 | Regel bleibt, ergänzt um T4 |
| Beschreibung | Folge | 215 | 0 | 604 | 215 | 50 | 0 | Regel bleibt |
| Alter | Folge | 126 | 0 | 693 | 126 | 50 | 0 | Regel bleibt |

- **Art (T4):** Die Ergänzung „Hörspiel im Albumnamen schlägt `audiobook`“ betraf 6 sichere Einträge.
- **Folgentitel:** von den 245 sicheren ändern 0 ein Wort, 37 bekommen „Folge N: “ davor, 208 bleiben gleich. Ein Präfixwechsel wie „121_“ → „Folge 121: “ zählt als Form, nicht als Wortänderung (GO-16).
- **Nummer:** vor T2 122 sicher; T2 nahm genau 5 weg (3 falsch: „Eine Weihnachtsgeschichte“ 16, „Der kleine Prinz“ 1,
  „Moby Dick“ 8; 2 richtig: „Der Räuber Hotzenplotz“ 1 und 2). 57 der 117 setzen eine neue Nummer, 60 bestätigen.
- **Name, alte Regel 4.6:** 128 sicher, davon 11 Änderungen, praktisch alle falsch (Sammelnamen der Tonie-Liste, Autoren als
  Apple-Künstler); die einzige automatische Umbenennung im Bestand wäre „Das kleine Gespenst“ → „Otfried Preußler“ gewesen.
- **Name, Urteil von Claude** (`ai_task.claude_ai_task`, Modell laut Einstellung der Integration; 450 Aufrufe, etwa
  510 000 Eingabe-Tokens): Prüfmenge 110 Einträge mit Ordner ≠ freigegebenem Namen, Claude sah nur den Ordner: 58 richtig,
  25 „sicher“, davon 22 richtig. Die 53 % sind zu niedrig gerechnet, weil im Lauf nur der Teil **vor** „ - “ als Name
  erlaubt war („Disney - Mulan“ konnte nicht „Mulan“ werden); 3.4 erlaubt beide Teile (der Anweisungstext mit „vor oder nach“ ist nie gemessen; Nachlauf siehe 3.4, GO-5). Bestand: 4 sichere Änderungen,
  davon 2 falsch („Die drei !!!“ → „Die drei ???“, „Pyjamahelden“ → „PJ Masks“).
- **Fassungen 4.3** getrennt: Cover A 22 / B 16 / zusammen 29; Folgentitel A 173 / B 139 / 245; Nummer A 109 / B 23 / 117.
  Beide bleiben („oder“); die Schwäche von B bei Einzeltiteln regelt T2 für die Nummer.
- **Trackzahl-Grenze** (4.3): bleibt „mehr als das Doppelte und mehr als 40“. Ohne Grenze oder mit „> 4× und > 100“ gäbe es
  7 sichere Cover mehr (36), die nicht in der Stichprobe waren. 519 gefundene Alben; 178 haben mehr als dreimal so viele
  Titel wie unsere Folge, weil unsere Dateien oft zusammengefasst sind.
- **Platzhalter:** 12 Folgen, keine sicher (siehe 4.5). Ein Versuch „Album mit gleicher Nummer“ fand 6 Treffer, wird nicht
  übernommen.
- **Gegenprobe:** 23 von 23 bestanden (Hotzenplotz-Pop-Album, Soundtrack und „Alle Hörspiele“ mit 231 Titeln; Tonie-Dubletten
  `01-0033`/`10000693` und `11002078`/`2000000144`; Boxen und „/“; „Englisch lernen“; polnische, finnische, italienische
  Peppa-Titel unter `de-de`; Bibi Folge 100 als Hörbuch bestimmt nicht die Art; deutsche Titel mit „Café“, „Pokémon“,
  „los“ bleiben benutzbar).
- **Quellen:** Tonie-Liste 6 709 Einträge, 4 979 mit `de-de`, davon 4 873 benutzbar (106 wegen fremdsprachiger Merkmale ausgeschlossen);
  Sitemap 577 deutsche Seiten; 129 Shopseiten abgerufen, 125 mit passender `salesId`, 4 mit anderer (verworfen), kein
  Formatfehler. **`tonies.com` leitet nicht weiter** (alle Antworten direkt 200). Apple: 1 963 Anfragen, alle mit Status 200 (kein 429, kein 403, keine Pause).
- **Zusammenführen/Verschieben** (4.8): 3 Vorschläge zum Zusammenführen (alle Ziel „Disney“), 7 zum Verschieben (6 mit
  Sammel-Ziel, 1 plausibel: Micky Maus); deshalb entfällt Verschieben (bestätigt von Tobias).
- **Nachlauf Claude mit dem Anweisungstext aus `claude_anweisung.md`** (Rev. 2.4: Datenblock, „vor oder nach ‚ - ‘“, ohne
  `sicher`; 110 Aufrufe, 18.11.): Prüfmenge 63 von 110 richtig (57 %, vorher 53 %); 71 Namensvorschläge, davon 63 richtig,
  8 falsch (89 %); 39 × „behalten“. Bestätigt R7: brauchbare Vorschläge, aber nie automatisch. Die Fixtures unter `claude/`
  zeigen noch Antworten der ersten Fassung.
- **Laufzeit:** siehe 5.3 (etwa 3,5 Stunden für 340 Einträge im Lauf).

## 5. Abläufe

### 5.1 Beim Einsortieren (automatisch)

1. `_serie_abarbeiten` meldet nach `_dauer_merken` die neuen Folgen an `online.py` (`neu_einsortiert(serie_id, folgen)`);
   der Aufruf legt nur in die Schlange und kehrt sofort zurück, ohne etwas zu erwarten, das eine Sperre braucht.
2. **Schnappschuss:** Das Einsortieren schreibt für jede neue Folge und eine neue Serie den Schnappschuss der gesetzten
   Felder (`anzeige`, `nummer`, Art; **für den Namen keinen**, 4.6) in den Store (6.1; GO-8).
3. Ein Hintergrund-Task arbeitet die Schlange ab, eine Serie zugleich. Netzabrufe laufen **ohne** Sperre. Beim Start eines
   Auftrags merkt er sich die Werte der betroffenen Felder.
4. Zum Schreiben nimmt er nur die Serien-Sperre, liest die Serie frisch (`_frisch`), prüft, dass Serie und Folge noch da
   sind und die Felder noch den gemerkten Werten entsprechen; geänderte Felder werden zu Vorschlägen, verschwundene still
   verworfen (GB-19).
5. Sichere Felder: übernehmen (6.3). Unsichere: Vorschläge. Ergebnis als Marke (7.3); der Claude-Schritt (3.4) hat eine eigene Marke (GO-2).
6. **„Anders einsortieren“ bleibt möglich** (GB-1): Nach einer automatischen Übernahme ruft der Dienst unter derselben
   Sperre `neu_einsortieren.rueckweg_fortschreiben(eingang, stand_vorher, serie_nachher, geaenderte_folgen)`. Die Funktion
   sucht in `_rueckweg` **und** in den Protokollzeilen alle Zeilen, deren gemerkter `stand` gleich dem Stand vor der
   Übernahme ist, schreibt Name, `stand`, Art, `art_quelle` und `anzeige` je Folge neu und speichert. Wird anders
   einsortiert, verfallen die Online-Änderungen mit den Folgen (Store wird dabei aufgeräumt, 7.3). Nach einer Übernahme
   **von Hand** wird der Rückweg nicht fortgeschrieben: „Anders einsortieren“ ist dann gesperrt (gewollt, wie nach
   jeder Handänderung).
7. Das Einsortieren wartet nie. Fällt eine Quelle aus, bleibt der Eintrag wie einsortiert; Marke `fehler` (verfällt, 7.3).

### 5.2 Suche von Hand (Administrator)

1. Serienseite → „⋯“ → „Online suchen“, auch im „⋯“ einer Folge. Nur bei `typ = normal` (nicht bei der
   Überraschungs-Serie), auch bei Einzeltiteln (GR-23).
2. Blatt mit Suchfeld (vorbelegt), Trefferliste mit Cover-Vorschau, Titel, Reihe, Nummer, Quelle („Apple“, „Tonies“),
   Tracks. Höchstens 10 Treffer. Früher abgelehnte Treffer erscheinen mit der Marke „früher abgelehnt“.
3. Tipp auf einen Treffer: **Übersicht** je Feld „heute → neu“ mit Häkchen, alle gesetzt außer Felder „von Hand“ (Hinweis
   „von Hand gesetzt“). Gleiche Werte erscheinen nicht. Die Übersicht holt die Feldwerte mit eigenem Befehl (9.2).
4. „Übernehmen“ schreibt die angehakten Felder als **eine** Änderung (6.3). Diese Felder gelten danach als von Hand: Es wird
   **kein** Schnappschuss gesetzt, die Felder kommen in `hand` (6.1).

### 5.3 Lauf über den Rest (Administrator)

- Technik → Unterseite **„Online-Suche“** → „Bibliothek durchsuchen“. Ein Lauf zugleich.
- Kandidaten: Einträge (`typ = normal`), die **(a)** keine Marke haben, eine verfallene Marke `keiner`/`fehler` haben oder
  Folgen, die in der Marke noch nicht stehen, **und (b)** mindestens eins davon: `pruefen`, Art geraten, Cover aus Tags oder
  keins, Folge ohne Nummer in einer Serie mit Nummern, Folge ohne Beschreibung. Ein Eintrag mit gültiger Marke wird nicht
  erneut gefragt, auch wenn (b) noch gilt (sonst fragte jeder Lauf alle Einträge mit Tag-Cover neu).
  **Ausnahme Claude (GO-2):** Der Claude-Schritt (3.4) läuft zusätzlich für jeden Eintrag mit Grund, wenn die Option gesetzt ist und
  `marke.claude` fehlt oder verfallen ist, auch bei gültiger übriger Marke.
  Die Kandidatenliste ist ein Schnappschuss; jede Serie wird beim Bearbeiten neu nachgeschlagen.
- Je Kandidat dieselben Schritte wie 5.1 (3 bis 6). Der Rückweg wird fortgeschrieben, wo noch eine passende Zeile im
  Speicher oder Protokoll steht; sonst ist „Anders einsortieren“ für diesen Eintrag ohnehin nicht mehr möglich (wie nach
  jeder späteren Änderung). Test: Lauf an einem frischen Upload, „Anders einsortieren“ geht danach (G2-8).
- **Zustände (GO-12):** laufend `laeuft`, `pausiert` (Quelle, bis wann), `wird_angehalten` (Anhalten verlangt, die aktuelle Serie wird
  noch fertig); am Ende `fertig`, `angehalten` oder `abgebrochen` (kein Fortsetzen, neuer Start nimmt die Marken) mit `grund`:
  `neustart` (HA-Neustart), `quelle` (nach drei Pausen in Folge „Quelle nicht erreichbar“, ohne Marken `fehler` für den Rest),
  `angehalten`. In einer Quellen-Pause wartet der Lauf.
- **Dauer** (gemessen in OS1): im Mittel 5,8 Apple-Anfragen je Eintrag (Stufe 1 je Folge, 3.3), zusammen etwa 1 970 bei
  10 je Minute im Lauf (5 sind für die Suche von Hand reserviert), dazu 130 bis 260 Shopseiten zu 1 je 4 s und die
  Claude-Aufrufe (3.4) → **340 Einträge etwa 3,5 Stunden** (170 bis 230 Minuten). Das Merkmal „Folge ohne Beschreibung“
  macht heute alle Einträge zu Kandidaten; erst die Marke (7.3) verhindert, dass der nächste Lauf alles neu fragt.
  Die Seite muss nicht offen sein.
- Nach dem Lauf: Zeile „Fertig: 120 Einträge geändert, 38 Vorschläge, 12 ohne Treffer.“, Liste der Änderungen mit
  „Zurücknehmen“ je Eintrag und „Alle zurücknehmen“ (6.4).

### 5.4 Vorschläge (Administrator)

- Die Karte „bitte ansehen“ der Serienseite zeigt für Administratoren offene Vorschläge: „Vorschlag aus der Online-Suche:
  Cover und Art von Apple“ mit „Ansehen“ (öffnet die Übersicht aus 5.2) und „Nein“. Ein Namensvorschlag zeigt „Vorschlag
  von Claude: Name „…““ mit dem Grund (eine Zeile) und „Übernehmen“ / „Nein“; „Übernehmen“ ruft Nr. 59 mit
  `felder: ["serie_name"]` und `stand` und wirkt wie ein Umbenennen von Hand (9.2). Vorschläge zum Zusammenführen öffnen den vorhandenen Dialog, vorbelegt.
- „Nein“ verwirft den Vorschlag dauerhaft (Store `verworfen`); derselbe Wert aus derselben Quelle kommt im Lauf nicht
  wieder, bei der Suche von Hand aber mit Marke „früher abgelehnt“.
- Eigener Filterwert `online_vorschlag` in der Bibliothek (nur Administratoren). `filter=pruefen` bleibt unverändert (GB-11).

### 5.5 Prüfgründe nach einer Übernahme (GB-3, GB-4, GR-11)

`pruefen` wird **je Grund** aufgelöst, nie pauschal:

| Grund | aufgelöst, wenn sicher übernommen oder bestätigt |
|---|---|
| `serie_aus_interpret`, `serie_aus_ordner` (Folge) | **nie durch die Online-Suche** (PL, bestätigt von Tobias 18.11.) (der Name wird nur von Hand bestätigt oder geändert, auch über einen angenommenen Vorschlag; OS1: Claude war bei „Janosch“ falsch sicher) |
| `tags_fehlen` (Folge) | Folgentitel **und**, wenn die Serie Nummern hat, Nummer |
| `nummer_doppelt` (Folge) | Nummer |
| `art_geraten` (Serie) | Art (wie `serie_art_setzen`) |
| andere (`teilweise_doppelt`, `track_teils_leer`, `track_doppelt` …) | nie durch die Online-Suche |

`tags_fehlen` wird in der Praxis von Hand gelöst: Der Folgentitel wird nur bei Platzhaltern automatisch gesetzt (4.5), und OS1 fand
keinen sicheren (GO-16).

„Bestätigt“ heißt: Eine sichere Quelle liefert denselben Wert, den das Feld schon hat. `pruefen` einer Folge bzw. Serie
fällt, wenn kein Grund mehr übrig ist; `pruefen` der Serie ohne eigenen Grund fällt, wenn keine Folge mehr `pruefen` trägt. Dazu `eingang.pruefen_zuruecksetzen` für das Protokoll; die Namen im Eingangsprotokoll
bleiben bewusst die alten. Eine Übernahme von Hand löst Gründe wie heute ein Umbenennen.

## 6. Herkunft, Übernahme, Rücknahme

### 6.1 Was „von Hand“ ist (GB-5, GR-12)

Der Store hält je Feld (außer dem Namen, 4.6) den **Schnappschuss**: den Wert, den Einsortieren oder eine automatische Online-Übernahme zuletzt
gesetzt hat. Die Automatik ändert ein Feld nur, wenn es **noch genau diesen Wert** trägt.

| Feld | von Hand, wenn … |
|---|---|
| `cover` | `cover-eigen.jpg` liegt da (auch die 78 Cover vom 14.11.), **oder** `cover-online.jpg` stammt aus einer Übernahme von Hand |
| `art` | `art_quelle = manuell` |
| `serie_name` | **immer**: Die Automatik ändert den Namen nie (4.6, R7), es gibt keinen Schnappschuss für ihn; ein angenommener Vorschlag von Claude ist ein Umbenennen von Hand. Namen aus den Läufen vom 14.11. gelten als von Hand (von Tobias freigegeben) (GO-8) |
| `folge_titel`, `nummer` | der Wert weicht vom Schnappschuss ab, oder die letzte Übernahme war von Hand. **Bestand ohne Schnappschuss:** von Hand, außer es gibt einen passenden Grund (5.5): für `folge_titel` `tags_fehlen`, für `nummer` `tags_fehlen` oder `nummer_doppelt`. Beim ersten Bearbeiten schreibt der Dienst den Schnappschuss, danach gilt die Regel oben |
| `beschreibung`, `alter_ab` | gewählt in einer Übernahme von Hand |

**Zurückgenommen:** Ein Feld, dessen Online-Änderung ein Administrator einzeln oder je Eintrag zurückgenommen hat, steht im
Store-Schlüssel `zurueckgenommen` (7.3). Für die Automatik gilt es dann **immer** als von Hand, egal ob ein Prüfgrund
wieder da ist, `art_quelle` wieder `geraten` ist oder das Cover wieder aus Tags kommt: nur noch Vorschlag. Die Marke
verfällt nie; ein neuer Wert von Hand oder eine Übernahme von Hand ersetzt sie durch `hand`.

Eine Übernahme von Hand schreibt die Felder in den Store-Schlüssel `hand` (7.3). Er verfällt nie und wird nur von einer
Rücknahme dieser Übernahme oder einem neuen Wert von Hand berührt; die Automatik fasst Felder in `hand` nie an (G2-3).

### 6.2 Was die Herkunft ändert

- `serie/rename`, `folge/rename`, `einsortierung/bestaetigen`, `serie/art_setzen`, Cover-Upload: Der Wert weicht danach vom
  Schnappschuss ab (oder ist `manuell`/`eigen`); keine eigene Marke nötig. `einsortierung/bestaetigen` löscht zusätzlich die
  Schnappschüsse der bestätigten Felder (bestätigt = von Hand).
- Upload mit Wunschname (Vertrag W 14.4): Das Einsortieren setzt für die Art **keinen** Schnappschuss (für den Namen gibt es nie einen, GO-8).
- `nummer` setzt kein Mensch (kein Befehl); sie ist nur über Schnappschuss oder Übernahme von Hand geschützt.

### 6.3 Übernehmen

Ein Weg in `media.py` (`online_uebernehmen(serie_id, felder, herkunft)`) unter der Serien-Sperre, in dieser **Reihenfolge**
(GB-2):

1. Änderung mit Vorher-Werten (Felder, `pruefen`, `pruefen_gruende` von Serie und Folgen, Schnappschüsse, Dateistand des
   Covers) und `status: offen` in den Store, **sofort** gespeichert (`async_save`).
2. Schreiben: `serie_name` → `serie.name`; `folge_titel`, `nummer` → `folgen_info.<f>`; `art` → `serie.art` mit
   `art_quelle = "online"`; `cover` → `cover-online.jpg`; `beschreibung`, `alter_ab` → Store. Prüfgründe nach 5.5.
   Zeichenketten aus Quellen gehen vorher durch `online_text(text, max)` (Steuerzeichen weg, auf die erlaubte Länge
   gekürzt, leer = verworfen), damit `name_pruefen` nie scheitert (GB-8).
3. Schnappschüsse für `anzeige`, `nummer`, Art setzen (nur automatisch, nie für den Namen), Rückweg fortschreiben (nur automatisch, 5.1), Änderung `status: fertig`.
4. `serien_geaendert`.

**Werte** kommen bei einem Treffer aus dem gehaltenen Treffer, bei einem Vorschlag aus dem Store (`werte`, GO-1), **nie aus der Eingabe**. Ein **Namensvorschlag von Claude** schreibt den Namen wie `serie/rename` von Hand (`name_pruefen`, `stand` Pflicht, GO-3); das ist **keine** Online-Änderung (kein Eintrag in `aenderungen`, nicht in `online.felder`, GO-14).

Beim Start von HA klärt der Dienst offene Änderungen: trägt das Feld den Online-Wert, `fertig`; sonst verwerfen und den
Schnappschuss aus `schnapp_vorher` wiederherstellen (nur dafür wird er gespeichert).

### 6.4 Zurücknehmen (Administrator)

- Je Änderung, je Eintrag (alle Änderungen des Eintrags) und je Lauf („Alle zurücknehmen“).
- Ein Feld wird nur zurückgesetzt, wenn es **noch den Online-Wert** trägt; `folge_titel` und `nummer` einer Folge werden
  gemeinsam geprüft; das Cover über den gespeicherten Dateistand (GB-18). Sonst steht es in `uebersprungen` mit Grund
  `seitdem_geaendert`, `serie_nicht_gefunden` oder `folge_verschoben`.
- Zurückgesetzt werden auch `pruefen`, `pruefen_gruende` und `art_quelle`; das Eingangsprotokoll bekommt sein `pruefen`
  zurück. Der **Schnappschuss** der zurückgenommenen Felder wird **gelöscht**, nicht wiederhergestellt (G2-1): Das Feld
  gilt danach als von Hand, der Lauf darf es nur noch vorschlagen. Bei einer Übernahme von Hand werden die Felder aus
  `hand` genommen. Cover: `cover-online.jpg` gelöscht, wenn es noch die Datei der Änderung ist.
- Rücknahme je Änderung oder je Eintrag setzt für jedes zurückgesetzte Feld (alle sieben Felder) die Marke
  `zurueckgenommen` (6.1), **kein** `verworfen`: Der Lauf darf den Wert später wieder **vorschlagen**, nie automatisch
  übernehmen. Test je Feld: Rücknahme, dann Lauf: Feld bleibt, Vorschlag möglich.
- **„Alle zurücknehmen“ eines Laufs** setzt die Marke **nicht**: Es macht den Lauf als Ganzes ungeschehen (z. B. einen
  Probelauf vor dem echten Lauf, Abnahme Schritt 10); ein späterer Lauf darf wieder automatisch übernehmen.
- Je Serie ein Schritt unter ihrer Sperre, nie mehrere Sperren zugleich. „Alle zurücknehmen“ läuft im Hintergrund mit
  Ereignis (9.3).
- **Nicht** über diesen Weg: ausgeführte Zusammenführungen und Verschiebungen (dafür Papierkorb bzw. zurückverschieben).
- **Online-Cover entfernen** ohne Änderung im Store (nach Papierkorb-Restore, nach Ablauf, GB-17):
  `DELETE /api/tobibox/cover/<serie_id>?quelle=online` (Recht admin); die Seite bietet es bei `cover_quelle = online`.

## 7. Speicher

### 7.1 `serie.json` (Datenmodell 5)

Keine neuen Felder. Neu ist der Wert `"online"` für `art_quelle`. Die Box ignoriert `art` und `art_quelle`.

### 7.2 Cover `cover-online.jpg`

- Reservierter Dateiname. **Vorrang: `cover-eigen.jpg` vor `cover-online.jpg` vor `cover.jpg`.** `cover_quelle` Wert
  `online`.
- Erzeugt aus dem 600-px-Bild über `cover_pruefen_und_skalieren(…, modus="nachsichtig", erlaubt=("jpeg","png"))` im
  Executor. Das Bild wird schon beim Suchen geladen (9.2, GB-13).
- **Checkliste der Stellen** (GB-10): `const.py:150-152` (Konstante); `cover.py` `cover_zustand` :233-241,
  `lese_cover_datei` :242-257, `uebernimm_cover` :283-297 (kopiert die Datei, die die Quelle anzeigt (eigen vor online), unter ihrem Namen; `hand.cover` und
  `zurueckgenommen.cover` ziehen mit; GO-17), `entferne_eigen` :494-508, `neu_suchen` :622-645 (berührt die Datei nicht);
  `media.py:670`, `:723`; `http.py:543-596` (GET, DELETE mit `quelle=online`); Seite `seiten/cover.js:254`.
- Papierkorb: wandert mit dem Ordner. Sync: schon ausgenommen (`cover*.jpg`), Box unverändert.
- Tests: Vorrang eigen > online > auto; Zusammenführen kopiert online, und eigen, wenn die Quelle beide hat.

### 7.3 Store `tobibox.online` (neu)

Unterklasse `OnlineSpeicher(Store)` mit `_async_migrate_func`, Version 1, `minor_version=1`, von Anfang an (GB-24, G2-12);
Test „Store mit `minor_version` 1 lädt fehlerfrei“. Liegt in `.storage/`,
also in jeder HA-Sicherung; nicht neu berechenbar, nicht gesynct.

| Schlüssel | Inhalt | Speichern |
|---|---|---|
| `serien.<id>.schnapp` | `{"art"?, "folgen": {<f>: {"anzeige"?, "nummer"?}}}` (kein Name, 4.6; GO-8) | sofort |
| `serien.<id>.hand` | `{"serie_name"?: true, "art"?: true, "cover"?: true, "folgen": {<f>: [<feld>…]}}` (Übernahme von Hand, 6.1); verfällt nie | sofort |
| `serien.<id>.zurueckgenommen` | `{"serie_name"?: true, "art"?: true, "cover"?: true, "folgen": {<f>: [<feld>…]}}` (6.1, 6.4); verfällt nie | sofort |
| `serien.<id>.marke` | `{"ergebnis": "geaendert"\|"vorschlag"\|"keiner"\|"fehler", "zeit", "folgen": [<f>…]}`; `keiner`/`fehler` verfallen nach 30 Tagen oder bei neuer Tonie-Liste | verzögert |
| `serien.<id>.marke.claude` | `{"ergebnis": "vorschlag"\|"behalten"\|"fehler"\|"aus", "zeit"}`: Marke des Claude-Schritts (3.4); `aus` verfällt, sobald die Option gesetzt ist, `fehler` nach 1 Tag; wird auch bei gültiger übriger Marke gebraucht (5.3; GO-2) | verzögert |
| `serien.<id>.folgen.<f>` | `{"beschreibung", "alter_ab", "quelle", "tonie_model"?, "seite"?, "zeit"}`; `seite` = Pfad der Shopseite (`/de-de/tonies/<serie-slug>/<folge-slug>/`, kein freier Text); „von Hand gewählt“ steht nur in `hand` (GO-15) | verzögert |
| `serien.<id>.aenderungen` | höchstens 20, höchstens 30 Tage: `{"id", "zeit", "wer": "auto"\|<HA-Benutzer-ID>, "lauf_id"?, "quelle", "status" (`offen`\|`fertig`\|`zurueckgenommen`), "felder": {<feld>[@<f>]: {"vorher", "nachher"}}, "pruefen_vorher", "schnapp_vorher", "cover_stand"?}` | sofort |
| `serien.<id>.vorschlaege` | `{"id", "art": "felder"\|"zusammenfuehren", "quelle" (`itunes`\|`tonies`\|`claude`), "felder"?, "werte"? (`{<feld>[@<f>]: neuer Wert}`; Cover: `{"cover_url" (600 px), "collection_id"}`; Quelle `claude`: `{"serie_name": <Name>}`), "grund"? (nur `claude`, ≤ 160 Zeichen), "name_vorher"? (nur bei `serie_name`: der Name beim Anlegen), "ziel_serie_id"?, "zeit"}`; beim Lesen auf Gültigkeit geprüft (Ziel und Folge da, bei `serie_name` der Name noch gleich `name_vorher`), sonst verworfen (GO-1, GO-3) | sofort |
| `serien.<id>.verworfen` | höchstens 200: `{"feld", "wert_hash", "quelle"}`; Hash über Feld, normalisierten Wert, Quelle; Cover über `collectionId` | sofort |
| `laeufe` | letzte 5: `{"lauf_id", "beginn", "ende", "zustand", "zahlen"}` | sofort |

**Pflegestellen** (GB-16), über **eine** Klasse `OnlineStore` mit `folge_umbenannt(sid, alt, ziel_sid, neu)`,
`loesche_folge`, `loesche_serie`, `bereinige`:

1. Folge löschen, Serie löschen (wie `medieninfo`, `media.py:1276`, :1318).
2. `folge/verschieben`, `serien/zusammenfuehren` (wie `media.py:1386`, :1467, :1511): `folgen.<f>`, `schnapp`, offene
   Vorschläge ziehen mit; bei einem neuen Namen im Ziel werden alle Schlüssel und `feld@folge` umbenannt. Änderungen
   bleiben bei der Quelle und verfallen mit ihr.
3. `neu_einsortieren.py` (:403, :423): Aufräumen beim Zurückholen in den Eingang.
4. Beim Start: `bereinige` wie `dauer.py:148` (verwaiste Serien und Folgen).
5. Papierkorb-Restore stellt den Store nicht wieder her; der nächste Lauf sucht neu. Ein zurückgekommenes
   `cover-online.jpg` lässt sich über „Online-Cover entfernen“ (6.4) loswerden.

Änderungen verfallen nach 30 Tagen oder über 20, älteste zuerst; mit ihnen verschwindet die Zeile „Aus der Online-Suche
übernommen“ (das Feld `online` der Kurzform wird aus dem Store gebildet, G2-9). `hand`, `zurueckgenommen`, `schnapp`, `verworfen` sind vom
Verfall nicht betroffen. `hand`, `zurueckgenommen` und `schnapp` ziehen an denselben Pflegestellen mit wie `folgen.<f>`.

`OnlineDienst` steht in `Hub.async_stop` (Task abbrechen, Store speichern).

### 7.4 Zwischenspeicher

`<config>/tobibox/tonies.json` (3.1), Sitemap und iTunes-Antworten im Speicher, Treffer mit Bildern 15 Minuten im Speicher
(höchstens 4 Suchen). Alles darf verloren gehen.

## 8. Netz

### 8.1 Eine Funktion für alle Abrufe (GB-7, GB-8)

`hole(url, quelle)` in `online_quellen.py`:

- nur `https`, kein Port, keine IP-Adresse; Host genau `itunes.apple.com`, `raw.githubusercontent.com`, `tonies.com`
  oder mit Endung `.mzstatic.com` (Test gegen Täuschungen wie `evilmzstatic.com`, `x.mzstatic.com.evil.tld`);
- `allow_redirects=False`, höchstens 3 eigene Sprünge mit derselben Prüfung (OS1: `tonies.com` leitet nicht weiter);
- `ClientTimeout(total=10)`, Tonie-Liste 60 s;
- Größe in Blöcken auf **entpackte** Bytes gezählt: iTunes 1 MB, Bild 5 MB, Shopseite 2 MB, Sitemap 5 MiB, Tonie-Liste
  20 MB;
- Auswertung (JSON, HTML, XML) im Executor; Sitemap nur über `<loc>`; aus der Shopseite nur der eine JSON-Block;
  Typprüfung je Feld; kein HTML aus fremden Quellen erreicht die Seite;
- `User-Agent: TobiBox-HA/<version>` ohne Hostname, ohne HA-Kennung, ohne Namen.

### 8.2 Drossel

Global je Quelle (nicht je Benutzer), höchstens 3 Verbindungen je Host:

- Apple-Suche (`itunes.apple.com`): 15 Anfragen je Minute, davon 5 für die Suche von Hand reserviert.
- Apple-Bilder (`*.mzstatic.com`): eigener Eimer, 30 je Minute, davon 15 für die Suche von Hand. Beim Suchen werden die
  Bilder der obersten 5 Treffer geladen, die übrigen erst mit Befehl 58 (G2-2).
- Tonie-Shop: 1 Seite je 4 s. Tonie-Liste, Sitemap: nach 3.1, 3.2.
- 429 oder 5xx: Quelle pausiert 15 Minuten. Shop 403: Formatfehler (3.2), keine Wiederholung.
- Die Suche von Hand wartet höchstens 5 s auf die Drossel, sonst Teilergebnis (9.2).

### 8.3 Datenschutz

An Apple gehen Suchwörter (Serien- und Folgentitel), immer von HA aus (O3). An GitHub und Tonies nur Abrufe der Liste und
einzelner Seiten; welche Seiten, verrät, welche Tonies in der Bibliothek stehen (in Kauf genommen wie bei Apple).
**(R6)** An den Anbieter der gewählten `ai_task`-Entität (heute Claude von Anthropic) gehen über HA Name, Ordnername, Folgentitel, Prüfgründe und die
Kandidaten der Quellen eines Eintrags, dazu ob er ein Einzeltitel ist und die Zahl seiner Folgen (3.4, T5); keine Tobie-Namen, keine Benutzer, keine IDs. Nur wenn die Option gesetzt ist; auch Uploads von Alltag-Konten lösen beim Einsortieren einen Aufruf aus (GO-6).
Cover-Vorschauen liefert HA selbst; der Browser fragt keine fremden Hosts (auch über Nabu Casa).

### 8.4 Tests

Alle Tests mit Fixtures (iTunes-JSON, Ausschnitt der Tonie-Liste, gekürzte Shopseite, Sitemap-Ausschnitt), Sockets im
Testpaket gesperrt. Fixtures aus OS1. Fälle: fremde Weiterleitung, Host-Täuschung, gzip-Bombe, leere oder kleine
Tonie-Liste, Shopseite ohne Felder, `ageMin` als Text. Fälle Claude (GO-7): Entität leer, Dienst `ai_task` fehlt, Zeitüberschreitung, ungültige Antwort, Name nicht in der Eingabe, `grund` mit HTML oder zu lang, Name gleich dem heutigen (`behalten`), Drossel, Tagesgrenze, Marke `claude` (Option nachträglich gesetzt: Eintrag wird nachgeholt; Ausfall: `fehler` 1 Tag).

## 9. Verträge (Entwurf, Freigabe durch Tobias in OS0, nach dem Trockenlauf)

### 9.1 Datenmodell `data-model.md`

1. 5 `serie.json`: `art_quelle` Wert `"online"`.
2. 5 Reservierte Dateinamen: `cover-online.jpg`, Vorrang zwischen `cover-eigen.jpg` und `cover.jpg`.
3. Neuer Abschnitt 5b: Store `tobibox.online` (7.3).
4. Neuer Abschnitt 13: `<config>/tobibox/tonies.json` (Zwischenspeicher, darf fehlen).
5. Kopf und 1.6 (Wer schreibt welche Datei) ergänzen.

### 9.2 Vertrag W

- **Neue Werte in vorhandenen Ausgabefeldern** (GB-11): `cover_quelle` und `art_quelle` bekommen `online`. Eintrag als
  ausdrückliche additive Änderung (wie 14.2). Code: `ART_QUELLEN` (`const.py:113`) erweitern; Test „`online` überlebt
  Lesen und Schreiben“. Rückfall auf eine ältere Integration macht `manuell` daraus (in `docs/betrieb/` nennen). Die Seite
  behandelt unbekannte Werte wie `auto`/`tags` (geprüft, `cover.js:254`).
- **Fähigkeit** `online_suche` (14.1): Befehle 57 bis 64, Filterwert `online_vorschlag`, Thema `online`,
  `DELETE …?quelle=online`. Nicht vom Netz abhängig.
- **(R6, PL) Claude:** keine eigene Fähigkeit und kein eigener Befehl. Namensvorschläge sind Vorschläge der Art `felder`
  mit Quelle `claude` und Feld `grund`; Befehl 63 nennt `quellen.claude` = `{"eingerichtet", "erreichbar"}`; `erreichbar` heißt: Entität und Dienst da und der letzte Aufruf nicht fehlgeschlagen (GO-10, GO-11). Die Entität ist eine **Option der Integration** (Optionsdialog `online_ki_entitaet`, Vorgabe: die `ai_task`-Entität der Claude-Integration (`anthropic`), wenn es genau eine gibt; abschaltbar), nicht
  Teil von Vertrag W. `manifest.json`: `ai_task` als `after_dependencies`, nicht als Pflicht.
- **(PL, OS0-Entwurf 18.11.)** Vorschläge lesen: Administratoren bekommen in `serie/get` die Liste
  `online_vorschlaege_liste` (Quelle, Art, Felder, Name, `grund`); Nr. 58 nimmt statt `treffer_id` auch `serie_id` +
  `vorschlag_id` (Übersicht zu „Ansehen“). Ein Namensvorschlag wird mit Nr. 59 übernommen (`felder: ["serie_name"]`,
  `stand`) und wirkt wie ein Umbenennen von Hand. Eine zurückgenommene Änderung hat den Status `zurueckgenommen`.
  Nr. 63: `quellen.claude` = `{"eingerichtet", "erreichbar"}`. **(GO-1, GO-3, GO-14)** Vorschläge tragen ihre Werte im Store (`werte`, 7.3): Nr. 58 mit `vorschlag_id` baut die Übersicht daraus und lädt das Cover-Bild neu (Netz; schlägt es fehl, fehlt `cover`); Nr. 59 mit `vorschlag_id` nimmt die Werte aus dem Store, nie aus der Eingabe. Bei `serie_name` ist `stand` Pflicht (sonst `invalid_format`); ein angenommener Claude-Name ist ein Umbenennen von Hand (`aenderung_id` `null`, nicht in `online.felder`). Einzelheiten: `docs/egm/online-suche/os0_entwurf/README.md`.
- **Befehle** (Recht **admin**, MQTT –; in 2.1 bei `admin` eintragen; Fehlercodes in Tabelle 7 mit HTTP-Nummer):

| Nr. | Befehl | Eingaben | Ausgabe | Fehler | Idempotent |
|---|---|---|---|---|---|
| 57 | `online/suchen` | `serie_id`, `folge`?, `text`? (2–100) | `treffer[]` (höchstens 10): `{"treffer_id", "quelle", "titel", "reihe", "nummer"?, "tracks"?, "art"?, "hat_cover", "frueher_abgelehnt", "felder": [<feld>[@<f>]…]}`, `quellen`: `{<quelle>: "ok"\|"pause"\|"fehler"}`; Treffer gelten 15 Minuten | `serie_nicht_gefunden`, `folge_nicht_gefunden`, `online_nicht_erreichbar` (nur wenn **keine** Quelle antwortet), `invalid_format` | ja (neue Treffer-IDs) |
| 58 | `online/treffer` | `treffer_id` **oder** `serie_id` + `vorschlag_id` | `{"felder": {<feld>[@<f>]: {"heute", "neu", "sicher", "hand"}}}`; Beschreibung höchstens 2 000 Zeichen; bei einem Vorschlag Werte aus dem Store, Cover-Bild neu geladen, dazu `grund` (nur Claude) | `treffer_abgelaufen`, `vorschlag_nicht_gefunden`, `serie_nicht_gefunden` | ja |
| 59 | `online/uebernehmen` | `serie_id`, `treffer_id` **oder** `vorschlag_id` (nur Art `felder`), `felder[]` (Muster `<feld>` oder `<feld>@<f>`, höchstens Folgenzahl × 4 + 3), `stand`? (**Pflicht bei `serie_name`**), `anfrage_id` | `{"aenderung_id" (`null` bei einem Namensvorschlag von Claude), "serie_id", "stand"}`; Werte **nie** aus der Eingabe | `treffer_abgelaufen`, `vorschlag_nicht_gefunden`, `stand_veraltet`, `serie_nicht_gefunden`, `folge_nicht_gefunden`, `invalid_format` (Feld nicht angeboten, falsche Vorschlagsart) | über `anfrage_id` |
| 60 | `online/zuruecknehmen` | `serie_id` + `aenderung_id`, **oder** `serie_id` allein (alle), **oder** `lauf_id` | Serie: `{"zurueckgenommen", "uebersprungen": [{"serie_id", "feld", "grund"}] (höchstens 50), "uebersprungen_anzahl"}`; Lauf: `{"gestartet": true}`, Ergebnis über Ereignis | `aenderung_nicht_gefunden`, `lauf_nicht_gefunden` | Endzustand ja (zweites Mal: 0) |
| 61 | `online/vorschlag_verwerfen` | `serie_id`, `vorschlag_id` | `{}` | `vorschlag_nicht_gefunden` | Endzustand ja |
| 62 | `online/lauf` | `aktion`: `start`\|`stop` | Laufzustand | `lauf_laeuft_schon`; `stop` ohne Lauf: kein Fehler | Endzustand ja (zweites `start`: `lauf_laeuft_schon`) |
| 63 | `online/status` | – | `{"lauf": {"lauf_id", "zustand", "erledigt", "gesamt", "geaendert", "vorschlaege", "keiner", "pause_bis"?} \| null, "quellen": {<quelle>: {"erreichbar", "pause_bis"?}}, "tonie_liste": {"stand", "anzahl"} \| null, "letzte_laeufe": [{"lauf_id", "beginn", "ende", "zustand", "grund"?, "zahlen"}]}`; laufend `laeuft`, `pausiert`, `wird_angehalten`; am Ende `fertig`, `angehalten`, `abgebrochen` mit `grund` `neustart`, `quelle`, `angehalten` (GO-12) | – | ja |
| 64 | `online/beschreibung` | `serie_id`, `folge` | `{"beschreibung", "alter_ab"?, "quelle"}` (voller Text) | `serie_nicht_gefunden`, `folge_nicht_gefunden` | ja. **Recht lesen** |

- **Vorschau-Bild:** `GET /api/tobibox/online/vorschau/<treffer_id>` (admin, `treffer_id` nur Hex, 192 px JPEG aus dem
  gehaltenen Bild, `Cache-Control: no-store`).
- **Neue Ausgabefelder** (keine Fähigkeit nötig): Folge-Objekt von `serie/get`: `beschreibung` (höchstens 300 Zeichen,
  am Satzende gekürzt), `beschreibung_gekuerzt` (bool), `alter_ab` (int), `beschreibung_quelle` (`tonies_shop`, `itunes`).
  Serie-Kurzform: `online` = `{"zeit", "felder": [<feld>…]}` der letzten Änderung, jünger als 30 Tage, **für alle**
  (R1; ein angenommener Claude-Name ist keine Änderung und steht nicht darin, GO-14); `online_vorschlaege` (int) nur für Administratoren und nur in Antworten, bei denen die Verbindung bekannt ist
  (`serien/list`, `serie/get`, `gehoert_abfrage.py:464`); Antworten auf Änderungen (`media.py:1035`, :1137, :1165, :1182,
  :1202, :1232) lassen das Feld weg, die Seite behält dann ihren Wert (G2-6).
  Neue oder verworfene Vorschläge lösen `serien_geaendert` aus (GB-20).
- **Neue Fehlercodes** (Tabelle 7, G2-10): `treffer_abgelaufen` 410, `vorschlag_nicht_gefunden` 404,
  `aenderung_nicht_gefunden` 404, `lauf_nicht_gefunden` 404, `lauf_laeuft_schon` 409, `online_nicht_erreichbar` 503.
- **Checkliste `art_quelle = online`** (G2-11): `data-model.md:544`, Vertrag W 14.2 (Tabelle), `const.py:113`
  `ART_QUELLEN`.
- 64-KiB-Grenze: gewahrt durch 10 Treffer, Feldnamen statt Werte in 57, gekürzte Beschreibungen, Obergrenze `uebersprungen`.

### 9.3 Ereignisthema `online` (nur Administratoren)

`online` geht nur an Administratoren (GB-15). Dafür neu (G2-5): Feld `ist_admin` in `Abo` (`hub.py:152-158`), `Hub.emit`
filtert Themen mit Regel „nur Administratoren“; `ws_subscribe` (`websocket_api.py:217`) streicht `online` für
Nicht-Administratoren still, auch bei ausdrücklichem `themen` (**erst die Themen auflösen, dann `online` streichen**; eine leere Menge bleibt leer und wird nicht zu „alle“; die Rolle gilt bis zum neuen Abo; GO-13). Test: Nicht-Administrator bekommt nie ein `online`-Ereignis. Arten: `snapshot`
(= Befehl 63), `stand` (Zahlen des Laufs oder der Lauf-Rücknahme; `emit_gebuendelt` mit 2 s), `fertig` (`lauf_id`,
Zahlen, `grund` bei Ende des Laufs, bei Rücknahme `uebersprungen_anzahl`; GO-12), `quelle` (`{quelle, erreichbar, pause_bis?}` bei Wechsel). Änderungen an
Serien kommen weiter über `medien`/`serien_geaendert`. Neu in `EREIGNIS_THEMEN` und `Hub.snapshot`.

### 9.4 `mqtt-v1.md`, Box

Keine Änderung.

## 10. Seite

Texte unter `ONLINE` in `texte.js`, nach `docs/egm/ha-ui/erklaersaetze.md`. Feldnamen: Name, Folge, Nummer, Art, Cover,
Beschreibung, Alter. Quellen: „Apple“, „Tonies“ (R5), für Namensvorschläge „Claude“ (bestätigt von Tobias 18.11.).

- **Serienseite, Kopf (alle, R1):** leise Zeile „Aus der Online-Suche übernommen: Cover, Art.“ solange die letzte Änderung
  jünger als 30 Tage ist. Administratoren: dahinter „Zurücknehmen“; andere: „Frag einen Administrator, wenn etwas nicht
  stimmt.“
- **„⋯“ (Administratoren, Fähigkeit `online_suche`, `typ = normal`):** „Online suchen“; bei `cover_quelle = online`
  zusätzlich im Cover-Blatt „Online-Cover entfernen“.
- **Blatt „Online suchen“:** Suchfeld, Trefferliste (Vorschau, Titel, Reihe, Nummer, Marke „Apple“/„Tonies“, Tracks,
  „früher abgelehnt“).
- **Übersicht:** je Feld „heute → neu“, Cover als zwei kleine Bilder, Beschreibung gekürzt mit „mehr“; „Übernehmen“ nur mit
  mindestens einem Häkchen.
- **Blatt „Zurücknehmen?“** (GR-14): nennt die Felder („Cover, Art“); danach „Zurückgenommen.“ bzw. „Zurückgenommen.
  2 Felder blieben, weil sie inzwischen geändert wurden.“ „Alle zurücknehmen“ nennt die Zahl der Einträge und braucht
  eine Bestätigung.
- **Folgenzeile (alle, R4):** Nebenzeile mit „ab 3“; ein kleiner Knopf zum Aufklappen der Beschreibung, nur wenn es eine
  gibt (der Tipp auf die Zeile spielt weiter). Aufgeklappt: Text, bei `beschreibung_gekuerzt` lädt die Seite den vollen
  Text mit Befehl 64 (nur mit Fähigkeit `online_suche`; sonst bleibt der gekürzte Text, G2-4).
- **Karte „bitte ansehen“ (Administratoren):** Vorschläge mit „Ansehen“ und „Nein“ (5.4); der `grund` von Claude erscheint als Text, nie als HTML (GO-4). Nicht-Administratoren sehen
  Vorschläge nicht.
- **Optionsdialog der Integration** (`online_ki_entitaet`): Der Text sagt, was an den Anbieter der Entität geht: Name, Ordnername, Folgentitel, Zahl der Tracks, Prüfgründe, Kandidaten der Quellen (GO-6).
- **Technik → „Online-Suche“** (neue Unterseite, Zeilenmuster X10, `ha-oberflaeche.md` 5.9 wird ergänzt): Zustand der
  Quellen, Stand der Tonie-Liste, „Bibliothek durchsuchen“ bzw. „Anhalten“, Fortschritt, letztes Ergebnis mit „Alle
  zurücknehmen“. Der vorhandene Knopf „Cover neu suchen“ heißt künftig **„Cover aus den Dateien neu lesen“**; sein Blatt sagt,
  dass Online-Cover und eigene Fotos bleiben (GR-17).

**Zustände und Texte** (GR-16):

| Zustand | Text |
|---|---|
| Suche läuft | „Suche bei Apple und Tonies …“ |
| nichts gefunden | „Nichts gefunden. Versuch einen anderen Namen.“ |
| eine Quelle aus | über der Liste: „Apple antwortet gerade nicht. Das sind nur Treffer von Tonies.“ (bzw. umgekehrt) |
| keine Quelle | „Online-Suche gerade nicht erreichbar, später noch einmal.“ (O9) |
| gedrosselt | „Apple braucht eine Pause, bis 14:20.“ |
| Treffer abgelaufen | „Die Suche ist zu alt. Such bitte noch einmal.“ |
| alles gleich | „Hier ist schon alles so.“ |
| Treffer ohne Cover | Platzhalter wie in der Bibliothek |
| Lauf pausiert / abgebrochen / angehalten / fertig | „Pause bis 14:20, weil Apple bremst.“ · „Abgebrochen (Neustart). Du kannst neu starten.“ bzw. „Abgebrochen: Quelle nicht erreichbar.“ · „Hält nach dieser Serie an.“ (`wird_angehalten`) · „Angehalten.“ · „Fertig: …“ |

## 11. Grenzen und Nicht-Ziele

- Keine Änderung an Box, `mqtt-v1.md`, Sync. Cover, Beschreibung, Alter bleiben in HA (O4).
- Kein automatisches Zusammenführen, Verschieben, Löschen (O15); keine Vorschläge zum Verschieben (4.8).
- Keine automatische Änderung des Namens eines Eintrags (R7); Claude schlägt nur vor.
- Keine Änderung an Datei- oder Ordnernamen.
- Keine weiteren Quellen; keine Eingabe für eigene Beschreibungen oder Alter.
- Kein Dauer-Scan: gesucht wird beim Einsortieren, von Hand, im gestarteten Lauf und beim Nachholen nach dem Start (nur
  Folgen ohne Marke, wie `cover.nachholen_beim_start`).

## 12. Pakete und Abnahmen

| Paket | Inhalt | Modell |
|---|---|---|
| **OS1** (braucht: –) **erledigt 18.11.** (Ergebnis Anhang 4.A) | **Trockenlauf** außerhalb von HA (ein Messskript, kein Code der Integration; „kein Code vor OS0“ gilt für die Integration) (Skript im Scratchpad, nur lesend über die Seitenbefehle und die Quellen): Regeln aus Abschnitt 4 über die echte Bibliothek. Ausgabe an Tobias als Auswahlseite: je Feld Zahl sicher/unsicher/keiner, **Stichprobe 50 sichere Treffer je Feld** (bei weniger: alle), **alle** automatischen Serien-Umbenennungen, Gegenprobe mit bekannten Fällen (Hotzenplotz-Album, Dubletten, Boxen, englische Fassungen), Zahl der Folgen mit Shopseite, Weiterleitungen von `tonies.com`, Laufzeit. Tobias markiert falsche; mehr als 1 in 50 → Regel strenger, neue Stichprobe. Fixtures sichern. Ergebnis als Anhang zu Abschnitt 4 | Sonnet |
| **OS0** (braucht: OS1) **freigegeben 18.11.** | Vertragsänderungen aus Abschnitt 9 als Entwurf (Diffs wie `stufe-b/b0_entwurf`), **Freigabe Tobias** | Projektleitung |
| **OS2** (braucht: OS1, OS0) | `online_quellen.py` (8, `hole`, Drossel, Zwischenspeicher), `online_abgleich.py` (4, reine Funktionen, Konstanten wie im Trockenlauf), `online_ki.py` (3.4, Aufruf `ai_task`, Prüfung der Antwort); Tests nur mit Fixtures aus `homeassistant/tests/fixtures/online/`; Anweisungstext und `structure`: `os0_entwurf/claude_anweisung.md` (GO-4, GO-5) | Sonnet |
| **OS3** (braucht: OS0, OS2) | `online.py` (Dienst, Schlange, Lauf), `OnlineStore`, Übernahme, Rücknahme, Schnappschuss, Prüfgründe, Rückweg, Befehle 57–64, Ereignis, Cover-Vorrang (Checkliste 7.2), Pflegestellen, `async_stop`; **Claude (GO-7):** Optionsdialog `online_ki_entitaet` (config_flow, Übersetzungen), `manifest.json` (`after_dependencies: ai_task`), Anbindung ans Einsortieren, `marke.claude` (GO-2) | Sonnet |
| **OS4** (braucht: OS0, OS3) | Seite (Abschnitt 10), jsdom- und Browser-Prüfung | Sonnet |
| **OS5** (braucht: alle) | Doku `docs/betrieb/`, Einspielen (Neustart nur mit Tobias’ Ja), **Abnahme** Schritt für Schritt (unten) | Projektleitung + Tobias |

**Abnahme OS5** (je Schritt Befehl bzw. Handgriff und Erwartung; Testmaterial aus OS1 mit bekanntem Ergebnis):

1. HA-Sicherung; Zahl der Kandidaten für den Lauf nennen.
2. Upload einer Datei mit erwartetem **sicheren** Treffer: Cover, Art, Nummer übernommen; Zeile „Aus der Online-Suche
   übernommen“ für Tobias und im Konto der Partnerin (dort ohne „Zurücknehmen“).
3. „Anders einsortieren“ an diesem Upload: geht.
4. Zurücknehmen: alte Werte und „bitte ansehen“ zurück.
5. Upload mit erwartetem **unsicheren** Treffer: Vorschlag in der Karte; „Nein“; Vorschlag kommt im Lauf nicht wieder.
6. Suche von Hand an einem Eintrag mit eigenem Foto: Cover ohne Häkchen, „von Hand gesetzt“.
7. Name von Hand ändern, dann Lauf über eine Test-Serie: Name bleibt.
8. Ausfall: Netz von HA zu Apple sperren (oder Drossel simulieren): Teilergebnis bzw. Satz O9; alles andere geht.
9. Lauf über die Bibliothek starten, nach einigen Einträgen HA neu starten (mit Tobias’ Ja): Zustand „abgebrochen“, neuer
   Start geht weiter.
10. Echter Lauf; danach Stichprobe; „Alle zurücknehmen“ an einem Test-Lauf geprüft.
11. Beschreibung aufklappen (Folge mit Shopseite), Alter „ab 3“ sichtbar, für alle Benutzer.
12. Name einer online geänderten Folge von Hand ändern, dann die Online-Änderung zurücknehmen: Name bleibt, Meldung
    „1 Feld blieb, weil es inzwischen geändert wurde.“
13. Konto der Partnerin: kein „Online suchen“, keine Vorschläge, kein „Zurücknehmen“; Befehl 57 wird abgewiesen
    (`unauthorized`); kein Ereignis `online`.
14. Claude, Option **leer**: Upload mit Grund (neue Serie): kein Namensvorschlag, alles andere geht (GO-7).
15. Option **gesetzt** (mit Tobias’ Ja, weil Daten rausgehen): Upload oder Lauf an einem Eintrag mit Grund: Vorschlag „von Claude“ mit
    Grund in der Karte; „Übernehmen“ (Name geändert wie von Hand) und „Nein“ (kommt im Lauf nicht wieder).
16. Name von Hand ändern, solange ein Namensvorschlag offen ist: der Vorschlag ist weg (GO-3).

## 13. Offene Punkte

Keine offenen Entscheidungen über die Regeln (OS1 abgenommen, Anhang 4.A). Die Festlegungen **(PL)** aus Rev. 2.3 hat Tobias
bestätigt:

1. Claude nur für Einträge mit Grund (neu einsortiert oder `serie_aus_*`), Entität als Option der Integration (3.4, 9.2).
   **Tobias, 18.11.: „Gleich eingeschaltet“** (Vorgabe ist die Claude-Entität, nicht leer).
2. `serie_aus_interpret` / `serie_aus_ordner` löst die Online-Suche nie auf (5.5). **Bestätigt (Tobias, 18.11.).**
3. Keine Vorschläge zum Verschieben (4.8). **Bestätigt (Tobias, 18.11.).**
4. Quelle der Namensvorschläge heißt auf der Seite „Claude“ (10). **Bestätigt (Tobias, 18.11.).**

Offen für Tobias (Rev. 2.4):

- **Nachlauf** der Prüfmenge (110 Einträge) mit dem geänderten Anweisungstext „vor oder nach“ (3.4, GO-5): **Tobias 18.11.:
  „Ja, messen“**; gemessen, Ergebnis in 4.A. Erledigt.
- **Kosten Claude (GO-18):** im ersten Lauf die 57 Einträge mit `serie_aus_*` (OS1), etwa 70 000 Eingabe-Tokens; danach nur neu
  einsortierte Einträge; höchstens 200 Aufrufe am Tag.
