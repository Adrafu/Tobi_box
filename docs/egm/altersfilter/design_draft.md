# Altersfilter in der Bibliothek: Design-Entwurf (EGM Schritt 2)

Rev. 2 · 23.11. · Grundlage: `concepts_brief.md` (gleicher Ordner, Entscheidungen A1 bis A8 von Tobias, Messung vom
23.11.). Rev. 2 = Befunde des Goldfisch-Reviews (`review_goldfisch.md`) eingearbeitet, Entscheidungen in `resolve.md`
Runde 1.

Bezüge: Vertrag W `docs/protocol/ha-websocket-v1.md` (3 `serien/list`, 4 `serie/get`, 27 `serien/zusammenfuehren`,
38 `serie/art_setzen`, 14.1 Fähigkeiten, 14.2 Kurzform und Eingaben), `docs/data-model.md` (1.4 unbekannte Felder,
5 `serie.json`, 5b Store `tobibox.online`), Design HA-Oberfläche `docs/designs/ha-oberflaeche.md` (5.2 Bibliothek),
Design Online-Suche `docs/designs/online-suche.md`. Code: `homeassistant/custom_components/tobibox/` `bibliothek.py`
(Filter, `zeilen()`), `media.py` (`Serie`, `serie_aus_json`, `to_json`, `kurzform`, `serien_liste`, Befehl 38),
`online.py` (Store, `folge_info`), `websocket_api.py`, `const.py` (`FAEHIGKEITEN`), `hub.py` (`faehigkeiten()`),
`frontend/seiten/bibliothek.js`, `frontend/seiten/serie.js`, `frontend/texte.js`; Box: `box/src/tobibox/library.py`.

## 1. Ziel

Eltern wählen in der Bibliothek „Für ein Kind mit 4 Jahren“ und sehen nur Einträge, die ab 4 Jahren oder jünger
empfohlen sind. Wer bearbeiten darf, kann das Alter eines Eintrags von Hand setzen, damit auch die drei Viertel ohne
Shop-Angabe filterbar werden. Mit der Wahl „Ohne Altersangabe“ findet man genau diese Einträge zum Nachtragen.

Nicht Ziel: Filter in Suche oder Start (A7), Merken der Wahl (A8), Alter oder Geburtsdatum der Kinder (keine
Personendaten), Alter je Folge von Hand, Änderungen an Box, MQTT oder Sync.

## 2. Begriffe

| Begriff | Bedeutung |
|---|---|
| **Shop-Alter** einer Folge | `alter_ab` der Folge im Store `tobibox.online` (`data-model.md` 5b), Quelle nur Tonie-Shopseite. Bleibt unverändert |
| **Alter von Hand** | neues Feld **`alter_hand`** in `serie.json` (int 0 bis 18 oder fehlt), gesetzt von einem Menschen über Befehl 66 |
| **Eintrags-Alter** | 1. `alter_hand`, wenn gesetzt; 2. sonst der **kleinste** gültige Shop-Wert der Folgen des Eintrags (A3); 3. sonst keins |

**Gültiger Shop-Wert** (AF-4): nur Folgen, die in `serie.folgen` stehen (Store-Einträge zu verschwundenen Folgen
zählen nicht), nur int von 0 bis 18, kein bool. Alles andere gilt als „diese Folge hat kein Alter“.

Beispiele: Folgen „ab 3“ und „ab 5“, ohne Wert von Hand → 3. Derselbe Eintrag mit `alter_hand` 6 → 6; die Folgen
zeigen weiter „ab 3“ und „ab 5“ (A6). Keine Shop-Werte, kein Wert von Hand → kein Eintrags-Alter.

Die Regel ist eine **reine Funktion** `eintrags_alter(alter_hand, shop_werte) -> int | None` mit eigenen Tests.

## 3. Daten

### 3.1 `alter_hand` in `serie.json`

- Optionales Feld auf oberster Ebene, int 0 bis 18. Fehlt es, gibt es keinen Wert von Hand.
- In `serie.json`, weil es ein von **Menschen** gesetztes Feld ist wie `art` und `einzeln` (`data-model.md`,
  Änderung 12.11.). Es überlebt Papierkorb, Zusammenführen und eine Neuinstallation der Integration. Der Store
  `tobibox.online` gehört der Automatik.
- **Umsetzung (AF-3):** echtes Feld der Klasse `Serie` (`alter_hand: int | None`), Name in `bekannt` von
  `serie_aus_json`, dort geprüft (int, kein bool, 0 bis 18; sonst `None`), `to_json` schreibt es nur, wenn gesetzt.
  Ein ungültiger Wert gilt als fehlend und verschwindet beim nächsten Schreiben der Datei (egal durch welchen
  Befehl). Ohne `bekannt` landete das Feld in `extra` und überschriebe den neuen Wert.
- Eine **ältere** Integration kennt das Feld nicht, legt es in `extra` und schreibt es unverändert zurück
  (`data-model.md` 1.4, `media.py` `extra`). Die Box liest nur ihre Pflichtfelder (`box/src/tobibox/library.py`) und
  ignoriert es.
- **`stand`** rechnet **nicht** über `alter_hand` (AF-2): Er rechnet nur über `name`, `folgen` und die von Menschen
  gesetzten Felder von `folgen_info` (Vertrag W, Kurzform 14.2; `media.py` `STAND_FELDER`), wie bei `art`. Ein Alter
  zu setzen löst also kein `stand_veraltet` auf einem anderen Gerät aus.
- Anlegen (`serie/create`), Einsortieren, `einsortierung/neu`, Umbenennen (`serie/rename`) und Art ändern (38)
  setzen das Feld nicht und erhalten es (AF-16). Konfig-Export und -Import berühren es nicht (`serie.json` ist nicht
  Teil davon, AF-17).

### 3.2 Shop-Alter

Bleibt, wie es ist. Die Online-Suche schreibt und nimmt zurück wie bisher und meldet das mit `serien_geaendert`. Sie
fasst `alter_hand` **nie** an: es liegt nicht in ihrem Store und ist kein Feld ihrer Übernahmen. Das Feld `alter_ab`
in `online.felder` und in den Vorschlägen bleibt das Shop-Alter **je Folge**.

### 3.3 Verschieben, Zusammenführen, Papierkorb (AF-8)

- `serien/zusammenfuehren` (27): Hat das Ziel kein `alter_hand`, übernimmt es das der Quelle; hat es eins, bleibt
  seins. Shop-Werte wandern mit den Folgen (wie heute die Beschreibung).
- `folge/verschieben` (26): `alter_hand` gehört dem Eintrag und geht nicht mit einzelnen Folgen mit. Shop-Werte
  wandern mit der Folge.
- Papierkorb und Wiederherstellen: `serie.json` (auch die Kopie im Papierkorb) behält das Feld.

## 4. Vertrag (Entwurf, wartet auf Tobias' Ja)

Alles additiv. Neue Fähigkeit **`alter`** (in `const.FAEHIGKEITEN`, gemeldet in `hello`, gelistet in 14.1). Sie gilt
für die neuen **Eingaben** (Eingabe `alter` in `serien/list`, Befehl 66). Die neuen **Ausgabefelder** brauchen wie
alle Ausgabefelder keine Fähigkeit (14.1): Die Seite zeigt „ab X“, wenn `alter_ab` da ist (AF-9).

Rückfall: Eine ältere Seite an einer neuen Integration sendet kein `alter` und übergeht die neuen Felder. Eine neue
Seite an einer älteren Integration sieht keine Fähigkeit `alter` und kein `alter_ab` an der Kurzform: kein Abschnitt
„Alter“, kein Menüpunkt, keine Anzeige oben.

### 4.1 Serie-Kurzform (14.2) bekommt

| Feld | Typ | Bedeutung |
|---|---|---|
| `alter_ab` | int 0 bis 18 oder fehlt | **Eintrags-Alter** (2.); fehlt, wenn es keins gibt |
| `alter_hand` | int 0 bis 18 oder fehlt | das Alter von Hand aus `serie.json`; fehlt, wenn keins gesetzt ist |

Gilt überall, wo die Kurzform vorkommt (`serien/list`, `serie/get`, Ausgabe von 5, 6, 38, 66 usw.). Kein Feld zur
Quelle (Tobias, AF-12): Wer es wissen will, sieht an `alter_hand`, ob ein Wert von Hand gesetzt ist.

Das Folge-Objekt von `serie/get` behält sein `alter_ab` (Shop-Alter der Folge) unverändert.

### 4.2 `serien/list` bekommt die optionale Eingabe (14.2, Fähigkeit `alter`)

| Eingabe | Typ | Bedeutung |
|---|---|---|
| `alter` | int 0 bis 18 oder `"ohne"` | Zahl X: nur Einträge mit Eintrags-Alter **≤ X**; Einträge **ohne** Eintrags-Alter fallen heraus (A2). `"ohne"`: nur Einträge **ohne** Eintrags-Alter. Fehlt: kein Altersfilter |

- Wirkt zusammen mit `art`, `text`, `auch_folgen`, `filter` als „und“, vor `offset`/`limit`; `gesamt` zählt nach
  allen Filtern.
- Strenges Schema wie bei den anderen Eingaben: bool, Text wie `"4"` oder `"Ohne"`, -1, 19 → `invalid_format`.
- Die Seite sendet `alter` nur aus der Bibliothek (A7), nicht aus der Lupe. Das Backend hat dafür keine Sonderregel
  und nimmt `alter` auch zusammen mit `text` an. `folgen/list` bekommt die Eingabe nicht.
- **Berechnung (AF-1):** Das Eintrags-Alter wird **je Anfrage** gebildet: `Medien.serien_liste` baut ein Wörterbuch
  `serie_id → Eintrags-Alter` aus `Serie.alter_hand` und dem Store (`online.store.folge_info`) und übergibt es an
  `Bibliothek.serien` (wie `online_vorschlag`). Es steht **nicht** in `_SerieZeile`: Der Index baut eine Zeile nur
  neu, wenn sich das `SerieInfo` ändert, eine Änderung nur im Store ließe sie veralten. Bei 341 Einträgen und 820
  Folgen ist das billig (Ziel der Suche unter 200 ms bleibt; Test mit 600 Einträgen und 2 000 Folgen).
- Dieselbe Funktion liefert `alter_ab` für die Kurzform, damit Filter und Anzeige nie auseinanderlaufen.

### 4.3 Neuer Befehl 66 `tobibox/serie/alter_setzen` (Fähigkeit `alter`)

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `alter_hand` | int 0 bis 18 oder `null` | **ja** | `null` löscht das Alter von Hand; danach gilt wieder der kleinste Shop-Wert oder keins |

Liest `serie.json` frisch und schreibt `alter_hand` (bzw. entfernt es) wie Befehl 38 (atomar, unbekannte Felder
bleiben). Ausgabe: `{"serie": <Serie-Kurzform>}`. Ereignis `serien_geaendert` wie bei 38.
Fehler: `serie_nicht_gefunden`, `medien_nicht_erreichbar`, `medien_schreibfehler`, `invalid_format` (Schema),
`unauthorized` (Recht). Recht: **alltag** (A5, wie 38), auch für die Überraschungs-Serie (Tobias, AF-6). Setzen und
Löschen mit demselben Recht; der letzte Schreiber gewinnt (bewusste Folge aus A5, AF-19). Idempotent: ja. MQTT: –.

### 4.4 `data-model.md`

- Abschnitt 5 (`serie.json`): Zeile `alter_hand` (int 0 bis 18, optional, nur von Menschen über Befehl 66 und beim
  Zusammenführen übernommen, die Box ignoriert es, nicht im `stand`).
- Abschnitt 1.4 bleibt unverändert (gilt schon).

Der Diff zu beiden Verträgen kommt nach der Annahme dieses Entwurfs nach `vertrag_entwurf/` in diesem Ordner und wird
erst nach Tobias' ausdrücklichem Ja übernommen (Paket AF0).

## 5. Seite

### 5.1 Gemeinsame Knopfreihe

Eine Funktion `altersKnoepfe(wert, setze)` baut die Reihe **0 bis 12** (Tobias, AF-18) als umbrechende Reihe runder
Knöpfe, mindestens 44 × 44 px, `role="radio"`, `aria-checked`, `aria-label` „4 Jahre“ bzw. „1 Jahr“, bei 0 „0 Jahre,
für alle“. Bedienung mit Tab und Eingabe wie die anderen Wahlen, sichtbarer Fokus; keine Pfeiltasten (gibt es bei
den anderen Wahlen auch nicht, AF-11). Werte 13 bis 18 kann man nicht wählen; aus dem Shop werden sie angezeigt und
gefiltert wie andere.

### 5.2 Bibliothek, Blatt „Sortieren und Filter“ (nur mit Fähigkeit `alter`)

- Neuer Abschnitt **„Alter“** zwischen „Was“ und „Nur“, eine `radiogroup` „Alter“, genau eine Wahl gilt (A2):
  Zeile **„Alle“** (Vorgabe), Überschrift „Für ein Kind mit … Jahren“ mit der Knopfreihe 0 bis 12, Zeile
  **„Ohne Altersangabe“**.
- Der Knopf „Sortieren und Filter“ zählt eine gewählte Zahl oder „ohne“ als **1** dazu (`aktiveEinstellungen`).
- „Zurücksetzen“ stellt „Alle“ her; ein Wechsel der Art-Reiter behält die Wahl.
- Kein Treffer: der vorhandene Leerzustand `filterOhneTreffer` mit „Filter zurücksetzen“.
- Die Wahl lebt nur im Zustand der Seite (`STANDARD().alter = 'alle'`), nicht in `localStorage`, nicht in der
  Adresse (A8).
- `listenAnfrage` sendet `alter` als **Zahl** (nicht als Text) oder `"ohne"`, wenn nicht „Alle“.
- Nach eigenem Speichern eines Alters oder nach `serien_geaendert` lädt die Liste ab Anfang neu (wie bisher bei
  anderen Änderungen), damit beim Blättern kein Eintrag übersprungen wird (AF-10).
- Die Zählzeile bleibt `aria-live="polite"`.

### 5.3 Serien-Seite

- **Anzeige (A6, Tobias AF-12):** In der Kopfzeile bei den anderen Angaben (Art, Dauer) steht **„ab 4“**, wenn die
  Kurzform `alter_ab` hat, ohne Angabe der Quelle. Bei Einträgen mit mehreren Folgen bleibt „ab X“ an den Folgen
  unverändert. Bei **Einzeltiteln** (`einzeln=true`) steht das Alter nur einmal, oben; die Angabe an der einen Folge
  entfällt dort (AF-7).
- **Ändern:** Im Menü „⋯“ ein neuer Punkt **„Alter festlegen“** (nur mit Fähigkeit `alter` und Recht alltag, wie
  „Art ändern“). Blatt **„Ab welchem Alter?“**:
  - die Knopfreihe 0 bis 12, vorbelegt mit `alter_hand`, sonst nichts gewählt;
  - nur wenn `alter_hand` gesetzt ist: Zeile „Wert von Hand löschen“ mit dem Hinweis, was danach gilt („Dann gilt
    wieder: ab 3“ aus dem kleinsten Shop-Wert der Folgen der geladenen Serie, oder „Dann gibt es keine
    Altersangabe“);
  - Knöpfe „Abbrechen“ und „Speichern“; Meldung „Alter gespeichert: ab 4“ bzw. „Alter entfernt“;
  - Fehler wie bei „Art ändern“, das Blatt bleibt offen.

### 5.4 Liste und Kacheln der Bibliothek

Kein Alter in Kachel oder Zeile (Platz; A6 verlangt es nicht).

### 5.5 Texte (neu in `texte.js`)

„Alter“, „Alle“, „Für ein Kind mit … Jahren“, „{n} Jahre“ (Ausnahme „1 Jahr“), „0 Jahre, für alle“,
„Ohne Altersangabe“, „Alter festlegen“, „Ab welchem Alter?“, „ab {alter}“, „Wert von Hand löschen“,
„Dann gilt wieder: ab {alter}“, „Dann gibt es keine Altersangabe“, „Alter gespeichert: ab {alter}“, „Alter entfernt“.

## 6. Fehler und Grenzfälle

| Fall | Verhalten |
|---|---|
| `alter_hand` 6, Folge im Shop „ab 3“ | Eintrags-Alter 6; bei „4 Jahre“ **nicht** sichtbar, bei „6 Jahre“ sichtbar |
| Folgen „ab 3“ und „ab 5“ | Eintrags-Alter 3; bei „3 Jahre“ sichtbar |
| Online-Suche nimmt Shop-Werte zurück | Eintrags-Alter fällt auf den nächsten Shop-Wert oder auf keins, bei der nächsten Anfrage |
| `alter_hand` gleich dem Shop-Wert | bleibt gespeichert; spätere Shop-Änderungen wirken nicht |
| Store hat Wert zu einer Folge, die es nicht mehr gibt, oder Wert 40, -1, `true` | zählt nicht |
| Eintrag ohne Folgen | nur `alter_hand` oder keins |
| `serie.json` hat `alter_hand: "4"` (Text) | gilt als fehlt; verschwindet beim nächsten Schreiben |
| Überraschungs-Serie | wie jeder Eintrag (AF-6) |
| Zusammenführen | siehe 3.3 |
| Ältere Integration / ältere Seite | siehe 4 (Rückfall) |
| Speichern scheitert | Meldung wie bei „Art ändern“, Blatt bleibt offen |
| Zwei Geräte setzen gleichzeitig | der letzte gewinnt (wie 38, kein `stand`) |

## 7. Pakete

| Paket | Inhalt | Modell |
|---|---|---|
| **AF0** | Vertragsentwurf (Diff zu W und `data-model.md`) nach 4. in `vertrag_entwurf/`; Freigabe durch Tobias | Projektleitung |
| **AF1** | Backend: Feld `alter_hand` in `Serie` (3.1), reine Funktion `eintrags_alter` (2.), Kurzform-Felder, Eingabe `alter` in `serien/list`, Befehl 66, Zusammenführen (3.3), Fähigkeit `alter`. **Tests:** Regel mit allen Fällen aus 6.; Filter ≤ X und `"ohne"`, mit `art`/`filter`/`text`, Blättern und `gesamt`; Schema-Fälle (`"ohne"` ja; `"Ohne"`, `true`, -1, 19, `"4"` nein) für `alter` und `alter_hand`; Befehl 66 setzen, löschen, ungültig, Recht (lesen nein, alltag ja), Überraschungs-Serie; `hello` meldet `alter`; Roundtrip `serie.json` mit Fremdfeldern und ungültigem Wert; `stand` unverändert; `serie/rename` und 38 erhalten `alter_hand`; Papierkorb und Wiederherstellen; Zusammenführen (Ziel ohne/mit Wert); `folge/verschieben`; Einzeltitel; Laufzeit mit 600 Einträgen und 2 000 Folgen. **Box:** ein Test in der Box-Suite, dass `library.py` eine `serie.json` mit `alter_hand` fehlerfrei liest | Sonnet |
| **AF2** | Seite: `altersKnoepfe`, Abschnitt „Alter“ im Blatt, Zähler, Zurücksetzen, `listenAnfrage`; Serien-Seite Anzeige (auch Einzeltitel) und Blatt „Alter festlegen“; Texte. **Tests** wie bei den vorhandenen: ohne Fähigkeit weder Abschnitt noch Menüpunkt; ohne `alter_ab` keine Anzeige; `aktiveEinstellungen` (Zahl und „ohne“ je 1); Zurücksetzen; `listenAnfrage` (Zahl als int); `aria-checked`; Neuladen ab Anfang nach Speichern | Sonnet |
| **AF3** | Review durch frischen Agent (Code gegen dieses Design), dann Abnahme mit Tobias im echten HA, Schritt für Schritt | Sonnet / Tobias |

## 8. Abnahme (Skizze, Schritt für Schritt im Chat)

Vorher mit Tobias einen **Testeintrag ohne Alter** festlegen (in der echten Bibliothek; Name nur im Chat). Am Ende
wird sein Wert wieder gelöscht (Pflicht).

1. Einspielen per Commit-SHA über das HA-Terminal, Neustart nach Tobias' Ja.
2. Bibliothek, „Alle“: Zählzeile notieren (Stand 23.11.: 341).
3. „Sortieren und Filter“ → „Ohne Altersangabe“: Zählzeile notieren (23.11.: 256), Knopf zeigt 1. Bis zum Ende
   blättern: keine Doppelten, letzte Zeile da.
4. „12 Jahre“: Zählzeile + Zahl aus Schritt 3 = Zahl aus Schritt 2 (bei Shop-Werten bis 10).
5. „4 Jahre“: Stichprobe von drei Einträgen, jeder zeigt oben „ab 4“ oder kleiner. Ein Eintrag mit zwei verschiedenen
   Folgenwerten (z. B. 3 und 5) erscheint bei „3 Jahre“.
6. Testeintrag öffnen → „⋯“ → „Alter festlegen“ → 4 → Speichern; oben „ab 4“.
7. Bibliothek: Er erscheint bei „4 Jahre“, nicht bei „3 Jahre“, nicht bei „Ohne Altersangabe“.
8. Einen Eintrag mit Shop-Wert 3 auf Hand-Wert 6 setzen: bei „4 Jahre“ weg, bei „6 Jahre“ da; danach Wert löschen,
   Hinweis „Dann gilt wieder: ab 3“, er ist wieder bei „4 Jahre“.
9. Tastatur am Mac: Blatt mit Tab erreichen, „5 Jahre“ mit Eingabe wählen, Fokus sichtbar.
10. Schmale Ansicht (Handy): Knopfreihe bricht um, nichts abgeschnitten.
11. Ein Benutzer ohne Recht alltag (falls vorhanden): kein Menüpunkt „Alter festlegen“.
12. Seite neu laden: die Wahl ist weg („Alle“).
13. Testeintrag: Wert von Hand löschen; er ist wieder „Ohne Altersangabe“.

## 9. Risiken

| Risiko | Gegenmittel |
|---|---|
| Shop-Werte sind Empfehlungen des Herstellers, kein Urteil der Eltern | Wert von Hand geht immer vor |
| Der Filter blendet 256 Einträge aus, die Eltern vergessen | Zählzeile und Zähler am Knopf zeigen, dass ein Filter wirkt; „Ohne Altersangabe“ macht sie auffindbar |
| Index und Store laufen auseinander | Eintrags-Alter je Anfrage bilden, eine Funktion für Filter und Anzeige (4.2) |
| Feld geht beim Schreiben verloren oder wird überschrieben | echtes Feld in `Serie` mit Roundtrip-Test (3.1) |
