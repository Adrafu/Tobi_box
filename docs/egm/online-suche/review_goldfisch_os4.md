# Goldfisch-Review OS4: Seite der Online-Suche

Stand: 19.11., Prüfung des nicht committeten Codes (Serienseite, Technik, Cover-Blatt, Bibliothek, Abo) gegen Design Rev. 2.6 (Abschnitte 10, 5, 6.4, 3.4, 4.9, 12), `resolve.md` (R1, R4, O14, Runde 7) und Vertrag W (3.2, 3.15, 4.11, 7, 14.1, 14.2).
Die jsdom-Tests laufen: 896 von 896 bestanden. `pruefe_seite.py` wurde nicht gestartet. Es wurde kein Code geändert.

Ergebnis in Kürze: **hoch 0, mittel 4, niedrig 8.** Rechte und Datenschutz sind sauber (siehe „geprüft, in Ordnung“). Die Befunde betreffen Zustände, die hängen bleiben, einen Zwischenspeicher, der nie auffrischt, und eine Rücknahme, die mehr tut, als das Blatt sagt.

---

## Mittel

### GO4-1 (mittel): „Wird zurückgenommen“ kann für immer stehen bleiben, „Alle zurücknehmen“ bleibt gesperrt

- **Datei:** `seiten/technik_online.js:64` (Feld `rueck`), `:76-80` (`verlassen`), `:106` (`snapshot`), `:116-120` (Ereignis `fertig`), `:161` (`rueck` wird nach dem Befehl gesetzt), `:201` (`zu` sperrt die Knöpfe).
- **Was falsch ist:** `this.rueck` wird nur durch das Ereignis `fertig` mit `vorgang = zuruecknahme` gelöscht. `verlassen()` setzt es nicht zurück, `betreten()`/`laden()` auch nicht, und `snapshot` ebenfalls nicht. Nr. 63 enthält keine Angabe über eine laufende Rücknahme, die Seite kann den Zustand also nicht aus dem Status holen.
- **Maßstab:** Design 6.4 („Alle zurücknehmen“ läuft im Hintergrund mit Ereignis), Vertrag 4.11 („Die Ereignisse sind Hinweise; die Quelle der Wahrheit ist Nr. 63“), Design 10 (Zustände).
- **Szenario (Abnahme 10):** Tobias tippt „Alle zurücknehmen“ und wechselt noch vor dem Ende auf eine andere Technik-Unterseite oder die Verbindung reißt kurz ab. Das Abo `online` ist beim Verlassen abgemeldet, das Ereignis `fertig` geht verloren. Beim Zurückkommen steht „Wird zurückgenommen: 0 von 40.“ und alle „Alle zurücknehmen“-Knöpfe sind gesperrt, bis die ganze App neu geladen wird. Die Meldung „Zurückgenommen. N Felder blieben …“ kommt nie. Ein zweiter, kleinerer Fall: Kommt `fertig` vor der Antwort auf Nr. 60 an, setzt Zeile 161 `rueck` nach dem Ereignis und es hängt ebenfalls.
- **Vorschlag:** `rueck` in `betreten()` auf `null` setzen (die Wahrheit liefert danach die Liste der Läufe). Bei `snapshot` ebenfalls. Zeile 161 nur setzen, wenn nicht schon ein `fertig` für diese `lauf_id` eingetroffen ist (zum Beispiel `this._fertigeRueck` als Menge der `lauf_id`). Ein Test: Rücknahme starten, `verlassen()`, `fertig` verpassen, `betreten()`: Knopf wieder frei.

### GO4-2 (mittel): Ziele von Zusammenführen-Vorschlägen werden nie aufgefrischt; Zusammenführen kann dauerhaft scheitern

- **Datei:** `seiten/serie.js:473-477` (`vorschlagZusammen`), `:482-489` (`_ladeZiele`), `:121-125` (`_ziele` wird nur bei Wechsel der Serie geleert).
- **Was falsch ist:** `_ladeZiele` holt ein Ziel nur, wenn `_ziele[id]` fehlt. `vorschlagZusammen` nimmt das zwischengespeicherte Ziel samt `stand` und `name`. Beides wird nie erneuert, solange man auf derselben Serienseite bleibt (auch nach `laden(true)`).
- **Maßstab:** Design 5.4 („Vorschläge zum Zusammenführen öffnen den vorhandenen Dialog, vorbelegt“), Vertrag Nr. 27 (`stand_ziel`), Fehlercode `stand_veraltet`.
- **Szenario:** Die Karte zeigt „mit ‚Online Ziel‘ zusammenführen“. Jemand benennt das Ziel um oder legt eine Folge hinein (neuer `stand`). Tobias tippt „Zusammenführen …“, der Dialog sendet `stand_ziel` alt, die Antwort ist `stand_veraltet`. `_fehler` lädt nur die Quelle neu und schließt das Blatt. Der zweite Versuch sendet wieder den alten `stand_ziel` des Zwischenspeichers. Das geht so lange schief, bis man die Seite verlässt. Auch die Karte zeigt den alten Namen weiter.
- **Vorschlag:** Beim Tipp auf „Zusammenführen …“ das Ziel immer frisch mit `serie/get` holen (der Name in der Karte darf aus dem Zwischenspeicher kommen) und den Zwischenspeicher bei jedem `laden()` verwerfen oder bei `stand_veraltet` löschen. Ein Test mit geändertem Ziel.

### GO4-3 (mittel): Das Blatt „Zurücknehmen?“ nennt nur die Felder der letzten Änderung, nimmt aber alle Änderungen des Eintrags zurück

- **Datei:** `seiten/online.js:347-368` (`felder = feldListe(s.online?.felder)`, Befehl 60 mit `serie_id` allein).
- **Was falsch ist:** Vertrag 14.2 sagt: `online.felder` gehört zur **letzten** Online-Änderung. Befehl 60 mit `serie_id` allein nimmt aber **alle** Änderungen des Eintrags zurück (Vertrag 3.15 Nr. 60, Design 6.4: „je Eintrag (alle Änderungen des Eintrags)“). Das Blatt sagt „Cover, Art gehen auf die alten Werte zurück.“, tatsächlich gehen auch Felder früherer Änderungen (bis 30 Tage, bis 20 Änderungen) zurück.
- **Maßstab:** Design 10 und GR-14 („nennt die Felder“); der Benutzer soll vor der Handlung wissen, was passiert.
- **Szenario:** Ein Lauf hat am Montag Nummern und Alter einer Serie gesetzt, am Dienstag hat eine Suche von Hand das Cover übernommen. Das Blatt nennt nur „Cover“. „Zurücknehmen“ setzt aber auch die Nummern am Montag zurück. Dazu kommt die Marke `zurueckgenommen`: Die Automatik darf diese Felder nie wieder von selbst setzen.
- **Vorschlag:** Entweder Befehl 60 mit `aenderung_id` der letzten Änderung senden (die Seite kennt sie nicht, dann `online` im Vertrag um `aenderung_id` ergänzen) oder den Satz ehrlich fassen („Alle Online-Änderungen dieses Eintrags gehen zurück: …“) und die Felder aus allen Änderungen bilden. Tobias entscheidet, welche Form er will. Gleichzeitig der Satz: „Cover gehen …“ bei einem Feld ist falsches Deutsch (siehe GO4-9).

### GO4-4 (mittel): Testlücken gegenüber den Abnahmeschritten OS5

- **Datei:** `tests/frontend/online_suche.test.mjs`.
- **Was fehlt:**
  1. Abo `online` der Technik-Unterseite wird beim Verlassen abgemeldet (Design 10, Auftrag Ereignis `online`: „Aufräumen beim Verlassen“); kein Test ruft `verlassen()` und prüft, dass weitere Ereignisse nichts mehr ändern (und dass die Wiederkehr nur einmal abonniert).
  2. Rücknahme eines Laufs mit verpasstem `fertig` (GO4-1) und Reihenfolge Ereignis vor Antwort.
  3. `blob:`-Freigabe: getestet ist nur das Schließen mit bereits geladenen Bildern (Zeile 368-391). Nicht getestet: Bild kommt nach dem Schließen an (GO4-5), neue Suche im selben Blatt, Übersicht-Bild.
  4. Doppeltipp auf „Übernehmen“ (ein einziger Befehl 59) und auf die Knöpfe der Karte.
  5. `aenderung_nicht_gefunden` bei „Zurücknehmen“ (GO4-6).
  6. Zusammenführen-Vorschlag mit verändertem Ziel (GO4-2).
  7. „Ansehen“ eines Cover-Vorschlags: was die Übersicht beim neuen Cover zeigt (GO4-7).
  8. Beschreibung: zweimal schnell tippen, solange der volle Text lädt (GO4-8).
  9. Nr. 57 liefert zwei Quellen mit Störung zugleich (GO4-10).
- **Maßstab:** Design 12, Abnahme OS5 Schritte 4, 5, 10, 12, 13; Auftrag zu OS4.
- **Vorschlag:** Je Punkt ein kleiner Test; 1 bis 3 vor OS5.

---

## Niedrig

### GO4-5 (niedrig): `blob:`-Adressen, die nach dem Schließen eintreffen, werden nie freigegeben

- **Datei:** `seiten/online.js:146-151` (`merkeBild`), `:198-200` (Übersicht-Bild), `:340` (Freigabe in `p.then`).
- **Was falsch ist:** Die Freigabe geht einmalig über die dann bekannten `urls`. Kommt ein Bild erst danach an (Antwort langsam, Blatt schon zu), legt `urls.push(url)` die Adresse in ein totes Feld. Ebenso bleiben die Bilder älterer Suchen im selben Blatt bis zum Schließen stehen.
- **Maßstab:** Auftrag und Kopfkommentar der Datei („wird beim Schließen des Blatts freigegeben“).
- **Szenario:** Tobias öffnet das Blatt, schließt es sofort, die fünf Vorschau-Anfragen enden danach: fünf Bilder bleiben im Speicher bis zum Neuladen (klein, 192 px, aber ein Leck).
- **Vorschlag:** Flag `zu` setzen; nach dem Schließen die frisch erzeugte URL sofort freigeben und nichts mehr zeichnen. Beim Ersetzen von `S.bilder` die alten Adressen freigeben.

### GO4-6 (niedrig): Fehlertext `aenderung_nicht_gefunden` verspricht ein Neuladen, das nicht stattfindet

- **Datei:** `texte.js` (`aenderung_nicht_gefunden: '… Die Ansicht ist neu geladen.'`), `seiten/serie.js:21` (`ENDE_FEHLER` ohne diesen Code), `seiten/online.js:360`.
- **Was falsch ist:** Bei Befehl 60 ist `aenderung_nicht_gefunden` ein vertraglicher Fehler. Die Serienseite lädt dann nicht neu und das Blatt bleibt offen (`fehler(err)` liefert `offen`), der Text sagt aber „neu geladen“.
- **Maßstab:** Vertrag Abschnitt 7, Ehrlichkeit der Texte (`ha-oberflaeche.md`).
- **Szenario:** Der Hinweis „Aus der Online-Suche übernommen“ steht noch auf der Seite, die Änderung ist im Store inzwischen weg (Papierkorb, Ablauf). „Zurücknehmen“ meldet „… Ansicht ist neu geladen“, die Zeile bleibt, das Blatt bleibt offen.
- **Vorschlag:** `aenderung_nicht_gefunden` in `ENDE_FEHLER` der Serienseite aufnehmen (Blatt schließen, neu laden) oder den Text ändern.

### GO4-7 (niedrig): Übersicht eines Cover-Vorschlags („Ansehen“) zeigt das neue Cover nur als Platzhalter

- **Datei:** `seiten/online.js:198` (`if (U.felder.cover && quelle.treffer_id)`), `:299-300`.
- **Was falsch ist:** Für `vorschlag_id` gibt es keine Vorschau (Vertrag: HTTP nur mit `treffer_id`). Die Übersicht zeigt dann ein graues Feld mit „+“ und dem Hilfstext „neues Cover“. Der Administrator soll aber Cover annehmen oder ablehnen und sieht es nicht.
- **Maßstab:** Design 10 („Cover als zwei kleine Bilder“).
- **Szenario:** Abnahme 5: Vorschlag „Cover und Art von Apple“, „Ansehen“: das neue Cover ist unsichtbar, Tobias entscheidet blind.
- **Vorschlag:** Vertrag ergänzen (Vorschau auch für `vorschlag_id`, etwa `GET …/online/vorschau/<vorschlag-bild-id>`) oder das Feld ehrlich beschriften („Bild wird erst nach dem Übernehmen sichtbar“). Entscheidung Tobias.

### GO4-8 (niedrig): Beschreibung: schnelles Doppeltippen öffnet den Text nach dem Zuklappen wieder

- **Datei:** `seiten/serie.js:493-513` (`beschreibungUmschalten`).
- **Was falsch ist:** Während Befehl 64 läuft, steht `offen: true, laedt: true`. Ein zweiter Tipp schließt (`offen: false`). Danach schreibt der erste Aufruf `offen: true` mit dem Text zurück und öffnet die Zeile wieder gegen den Willen. Außerdem bleibt `_beschr` nach `laden(true)` stehen: ein neu geladener (neuer) Text wird nicht angezeigt, solange der alte im Zwischenspeicher liegt.
- **Maßstab:** Bedienung (Doppeltipp), Design 10 (R4).
- **Szenario:** Langsames Netz, Tobias tippt zweimal, die Beschreibung klappt von selbst wieder auf.
- **Vorschlag:** Nach dem Warten den aktuellen Zustand lesen und `offen` nicht überschreiben; `_beschr` bei neuem `stand` der Serie leeren (nur `text` verwerfen).

### GO4-9 (niedrig): Satz im Rücknahme-Blatt grammatisch falsch bei einem Feld

- **Datei:** `texte.js` (`zuruecknehmen.text`: „{felder} gehen auf die alten Werte zurück.“), `seiten/online.js:365`.
- **Was falsch ist:** Bei einem Feld steht „Cover gehen …“ oder „Art gehen …“ (Singular, falsche Form). Dasselbe bei `alle_zurueck_text` ist richtig mit `zaehle` gelöst.
- **Maßstab:** Texte einfach und richtig (`erklaersaetze.md`).
- **Vorschlag:** Zwei Formen (ein Feld: „{felder} geht auf den alten Wert zurück.“) oder neutral: „Zurück auf die alten Werte: {felder}.“

### GO4-10 (niedrig): Quellen-Hinweise widersprechen sich, wenn beide Quellen gestört sind

- **Datei:** `seiten/online.js:246-256` (`hinweisQuellen`).
- **Was falsch ist:** Jeder Hinweis hängt „Das sind nur Treffer von {andere}.“ an (bei `aus` immer, bei `pause` ohne Uhrzeit immer), auch wenn die andere Quelle selbst nicht `ok` ist. Das Design sagt den Zusatz nur, wenn die andere antwortet (die Zeile für `quelle_pause_bis` prüft das, die anderen nicht).
- **Maßstab:** Design 10, Tabelle „Zustand und Text“.
- **Szenario:** Apple `fehler`, Tonies `pause`: zwei Zeilen („Apple antwortet gerade nicht. Das sind nur Treffer von Tonies.“ und „Tonies braucht eine Pause. Das sind nur Treffer von Apple.“), darunter „Nichts gefunden“.
- **Vorschlag:** Den Zusatz in allen Zweigen nur anhängen, wenn die andere Quelle `ok` ist (eine Hilfsfunktion).

### GO4-11 (niedrig): Fokus geht beim Wechsel Suche, Übersicht und zurück verloren

- **Datei:** `seiten/online.js:186-209`, `:332`, `:339` (nur `fokus: 'titel'` beim Öffnen; kein `ctx.blattFokus()` beim Wechsel).
- **Was falsch ist:** Der Tipp auf einen Treffer oder „Zurück“ entfernt das fokussierte Element. Der Fokus fällt auf `body` des Dialogs. Tastatur und Screenreader beginnen wieder oben im Blatt ohne Ansage, die Überschrift ändert sich still.
- **Maßstab:** `ha-oberflaeche.md` (Blätter, Fokus); `ctx.blattFokus` gibt es dafür.
- **Vorschlag:** Nach dem Phasenwechsel `ctx.blattFokus()` aufrufen. Das Suchfeld ohne Treffer nicht fokussieren (Esc-Problem, Kommentar Zeile 339).

### GO4-12 (niedrig): Kleinigkeiten in der Bedienung

- `seiten/online.js:156` `suche()`: Bei weniger als 2 Zeichen passiert nichts, ohne Hinweis (Vorgabe aus einem einstelligen Namen: leere Liste, kein Satz). `maxlength=100` hilft nicht bei einem vorbelegten längeren Namen: Ändert man ihn nur leicht, sendet die Seite mehr als 100 Zeichen (`invalid_format`).
- `seiten/online.js:299, 305`: Bei langer `heute`-Beschreibung ohne lange `neu`-Beschreibung gibt es kein „mehr“ (`langerText` prüft nur `neu`).
- `seiten/online.js:266`: `aria-label` „{titel} ansehen“ ersetzt den Inhalt der Zeile; Reihe, Nummer, Quelle, „früher abgelehnt“ sind für Screenreader nicht mehr lesbar (Marke „früher abgelehnt“ ist eine Warnung).
- `seiten/online.js:110-115` und `:167`: 404 `cover_nicht_gefunden` („Bild noch nicht geladen“) führt zu dauerhaftem Platzhalter; ein erneuter Versuch fehlt.
- `seiten/serie.js` `vorschlagZeilen` wird ohne `gesperrt` aufgerufen; während `_busy` sind die Knöpfe nicht grau (der zweite Tipp wird still verschluckt).
- `seiten/technik_online.js:185-195`: Nach dem Ereignis `fertig` steht bis zum Neuladen der Liste für einen Moment das Ende des **vorigen** Laufs in der Karte „Lauf“.
- `seiten/bibliothek.js:22, 27`: Ein bereits gesetzter Filter `online_vorschlag` wird gezählt und gesendet, auch wenn Administrator oder Fähigkeit fehlen würden (nur im Speicher der Seite, im Alltag nicht erreichbar).

---

## Geprüft, in Ordnung

**Rechte und Datenschutz**
- Alles Sendende hängt an `ctx.admin === true && faehig('online_suche')`: Menüpunkte „Online suchen“ (Eintrag und Folge, `darfSuchen`), Suche, Übersicht, Karte „bitte ansehen“ (`vorschlaege()`), Zurücknehmen (`hinweisZeile`), „Online-Cover entfernen“ (cover.js), Filter `online_vorschlag`, Vorschau-Bilder, Technik-Unterseite (Technik ist ohnehin Administratoren vorbehalten; ohne Fähigkeit fällt `#technik-online` auf die Liste).
- Nicht-Administrator sieht nur: Hinweiszeile mit „Frag einen Administrator …“, „ab 3“, Beschreibung auf Tipp, voller Text mit Befehl 64 (Recht lesen, nur mit Fähigkeit). Kein Abo `online` (`_onlineBeobachten` prüft `is_admin` und Fähigkeit), keine Vorschlagsliste, keine Vorschau-Anfrage.
- Kein HTML aus Quellen oder von Claude: Titel, Reihe, Beschreibung, Name und `grund` stehen als Lit-Textknoten. In `frontend/` gibt es weder `unsafeHTML` noch `innerHTML` mit Daten des Backends (die eine Stelle in `tobibox-app.js:1407` nimmt eine feste eigene Datei). Attribute (`data-…`, `aria-label`, `src` nur `blob:`) sind Lit-gebunden; die Breite des Fortschrittsbalkens ist eine gerundete Zahl.
- Vorschau-Bilder kommen nur über `hass.fetchWithAuth` mit eigener Adresse, `treffer_id` mit `encodeURIComponent`; kein Fremdhost.

**Verhalten gegen Design und Vertrag**
- Vorauswahl der Häkchen (`vorauswahl`): alle außer `hand` (O14), Name hat vom Backend `hand` und steht daher ohne Häkchen mit „von Hand gesetzt“; „Übernehmen“ nur mit mindestens einem Häkchen.
- Übernehmen sendet nur `serie_id`, Quelle, angehakte `felder`, `stand` und `anfrage_id`; nie Werte. Dieselbe Wahl nach einem Fehler: dieselbe `anfrage_id`; neue Wahl: neue. Namensvorschlag von Claude: `felder: ["serie_name"]` mit `stand`, Meldung „Der Name ist geändert.“, keine Hinweiszeile.
- Fehlerfolgen: `treffer_abgelaufen` (Meldung, Rückkehr zur Suche, bei Vorschlag Blatt zu), `stand_veraltet`, `serie_nicht_gefunden`, `folge_nicht_gefunden`, `vorschlag_nicht_gefunden` (Blatt zu, Seite lädt neu), `online_nicht_erreichbar` (Satz O9 ohne Fehlerton), `name_ungueltig` und `medien_*` (Blatt bleibt offen).
- Rücknahme: Befehl 60 mit `serie_id`; Meldung „Zurückgenommen.“ bzw. „… N Felder blieben, weil sie inzwischen geändert wurden.“ aus `uebersprungen_anzahl`. „Alle zurücknehmen“: Bestätigung mit Zahl, Befehl 60 mit `lauf_id`, Ergebnis aus Ereignis `fertig` (`vorgang = zuruecknahme`, mit „blieben“).
- Vorschläge: „Ansehen“ (Befehl 58 mit `serie_id` und `vorschlag_id`), „Nein“ (Befehl 61, „Der Vorschlag ist verworfen.“), Namensvorschlag mit Grund als Text, Zusammenführen über den vorhandenen Dialog (nie Befehl 59), nur mit Fähigkeit `korrektur`.
- Beschreibung nur auf Tipp, eigener Knopf neben der Zeile (Zeilentipp spielt weiter, CSS `pointer-events`), Befehl 64 nur bei `beschreibung_gekuerzt` und Fähigkeit, bei Fehler bleibt der gekürzte Text. Einzeltitel und Kapitel-Hörbuch zeigen „ab 3“ und Beschreibung unter dem Kopf.
- Lauf-Zustände: `laeuft`, `pausiert` (mit Quelle und Uhrzeit), `wird_angehalten`; Ende `fertig`, `angehalten`, `abgebrochen` mit Grund `neustart`/`quelle`/`angehalten` und **ohne** `grund` (Text „Abgebrochen. Du kannst neu starten.“, kein „undefined“). Texte stimmen wörtlich mit Design 10.
- Ereignis `online`: Abo beim Betreten, `verlassen()` meldet ab und erhöht den Zähler gegen späte Antworten; `snapshot`, `stand` (Lauf und Rücknahme getrennt), `quelle`, `fertig`. Fehler beim Laden zeigt die Fehlerkarte.
- „Cover neu suchen“ heißt „Cover aus den Dateien neu lesen“ mit Satz, dass Online-Cover und eigene Fotos bleiben (GR-17).

**Bedienung**
- Tippziele: `.os-link`, `.os-knopf` 44 px, Zeilen der Felder ≥ 56 px, Treffer ≥ 64 px; Häkchen als `role="checkbox"` mit `aria-checked`; Fokusring über `--focus`; Esc schließt das Blatt (Fokus auf der Überschrift, nicht im Suchfeld); Übernehmen gesperrt während der Anfrage (`U.laeuft`) und ohne Häkchen; Suchen-Knopf gesperrt während der Suche.
- Lange Texte (`overflow-wrap: anywhere`), schmale Breite (Suchzeile als Grid, Zeilen der Technik mit Umbruch), leere Zustände („Nichts gefunden.“, „Hier ist schon alles so.“, „Noch kein Lauf.“, „Kein Lauf.“).
