# Goldfisch-Review: Nachpaket T10 (`vorschau_id`) und T11 (Nr. 65 `lauf_aenderungen`)

Stand: 19.11., ungecommitteter Arbeitsstand. Maßstab: `docs/protocol/ha-websocket-v1.md` (Änderungsvermerk 19.11., Nr. 58, Nr. 60, Nr. 65, HTTP-Vorschau, 2.1, 7, 14.1), `docs/data-model.md` 5b, Design Rev. 2.7.

Tests gelaufen: `test_online_befehle.py` + `test_online_dienst.py`: 130 grün. `online_suche.test.mjs`: 90 grün. `pruefe_seite.py` nicht gestartet.

## Zahl je Schwere

Hoch: 0. Mittel: 1. Niedrig: 7.

## Befunde

### GT-1 (Mittel): Mock und Backend setzen den Status einer Einzel-Rücknahme verschieden

- Datei: `homeassistant/custom_components/tobibox/online.py:2105` (Backend), `homeassistant/tests/frontend/mock-hass.mjs:601` (Mock, `nimmZurueck`: `a.status = 'zurueckgenommen'` immer), Test `online_suche.test.mjs:1429`, Seite `technik_online.js:221`.
- Was: Das Backend setzt `status = "zurueckgenommen"` nur, wenn mindestens ein Feld wirksam zurückging (`if zurueck_keys:`). Wurden alle Felder übersprungen (`seitdem_geaendert`), bleibt die Änderung `fertig`. Der Mock setzt den Status immer. Der Frontend-Test 1429 behauptet „der Eintrag gilt trotzdem als zurückgenommen (wie Nr. 60 sie setzt)“. Das stimmt für das echte Backend nicht. Die Seite setzt den Status nach `ok` zudem zuerst von Hand auf „Zurückgenommen“.
- Maßstab: Nr. 65 (Status „fertig“ oder „zurückgenommen“, Nr. 60 „setzt die Marke wie dort beschrieben“); der Mock soll das Backend abbilden.
- Szenario: Eine Serie wurde nach der Online-Änderung von Hand umbenannt. Tobias tippt bei dem Eintrag auf „Zurücknehmen“. Die Meldung lautet „1 Feld blieb …“. Der Eintrag springt kurz auf „Zurückgenommen“. Dann liefert Nr. 65 wieder „Geändert“ samt Knopf. Der Eintrag flackert und wirkt wie ein Fehler. Der Test sichert das Gegenteil des echten Verhaltens ab.
- Vorschlag: Zuerst entscheiden, was gelten soll. Vorschlag: Vertrag in Nr. 60/65 festhalten (ganz übersprungen bleibt `fertig`). Dann Mock und Test 1429 anpassen (Status bleibt `fertig`). Die optimistische Umstellung in `eintragZuruecknehmen` nur bei `zurueckgenommen > 0` machen. Dazu einen Python-Test für „alles übersprungen, Status bleibt `fertig`“.

### GT-2 (Niedrig): Nr. 65 listet reine Bestätigungen mit leerem `felder`

- Datei: `online.py:2575-2579`.
- Was: Eine Änderung mit leerem `felder` und nur `bestaetigt` (Status `fertig`, mit `lauf_id`) kommt als Eintrag mit `"felder": []`. `kurz_online` (`online.py:808-811`) schließt solche Änderungen aus (GO3-1). Nr. 65 verweist auf die Kurzform, „ohne bestätigte Felder“. Die Seite zeigt dann „Name“, keinen Feldtext und einen Knopf „Zurücknehmen“. Der Aria-Text lautet „Name:  zurücknehmen“.
- Szenario: Die Automatik bestätigt in einem Lauf nur einen Prüfgrund. Die Liste zeigt mehr Einträge als die Zahl „geändert“ des Laufs und einen Eintrag ohne Inhalt.
- Vorschlag: Entweder solche Einträge auslassen (wie die Kurzform) oder im Vertrag ausdrücklich sagen, dass sie mit leerem `felder` erscheinen. Test dazu ergänzen. Aktuell prüft keiner diesen Fall.

### GT-3 (Niedrig): `vorschau_id` verdrängt echte Suchen aus den 4 Plätzen

- Datei: `online.py:2540-2544` und `online_quellen.py:616-640` (`TrefferSpeicher`, Obergrenze 4 Suchen, je `lege` ein Platz).
- Was: Jede Abfrage von Nr. 58 mit Vorschlag und Cover legt einen neuen Platz an, auch bei dem Vorschlag, der schon einen hat. Das ist so beschlossen („gehalten wie ein Treffer“, Test erwartet das). Folge: Vier Übersichten verdrängen jede laufende Treffersuche von Tobias oder der Partnerin (zweites Gerät) mit `treffer_abgelaufen`. Das Bild einer offenen Übersicht überlebt vier fremde Suchen nicht.
- Szenario: Zwei Administratoren, oder Tobias öffnet viermal „Ansehen“ bei Vorschlägen und kehrt dann zu seiner Suche zurück. „Übernehmen“ mit `treffer_id` sagt „Die Suche ist zu alt“.
- Vorschlag: Ist das Risiko zu groß, einen eigenen kleinen Speicher für Vorschauen nehmen oder je `(serie_id, vorschlag_id)` den alten Platz ersetzen. Sonst nur im Vertrag erwähnen („teilt die 4 Plätze mit den Suchen“). Der Mock bildet das schon so ab (siehe GT-4).

### GT-4 (Niedrig): Der Mock zählt Plätze anders als das Backend

- Datei: `homeassistant/tests/frontend/mock-hass.mjs:621` und `:660-663`.
- Was: Backend: ein Platz je Suche (bis zu 10 Treffer teilen ihn), Verdrängung der ältesten ganzen Suche. Mock: sobald `plaetze` nicht leer ist (nach der ersten Vorschau), belegt jeder Treffer einer Suche einen Platz. Eine Suche mit mehr als 4 Treffern verdrängt dann ihre eigenen ersten Treffer. Davor (bei leerem `plaetze`) zählen Suchen gar nicht.
- Szenario: Ein künftiger Test „Vorschlag ansehen, dann suchen“ liefert im Mock `treffer_abgelaufen`, im echten Backend nicht.
- Vorschlag: Im Mock je Suche einen Platz (`suchId`) führen und die Suchen von Anfang an mitzählen.

### GT-5 (Niedrig): Zähler der Liste fängt nach „zuklappen“ wieder bei 1 an

- Datei: `technik_online.js:186-196` (`n = (alt?.n ?? 0) + 1`, `listeUmschalten` löscht den Eintrag).
- Was: Aufklappen (n=1, Anfrage A läuft), zuklappen (Eintrag weg), wieder aufklappen (n=1, Anfrage B). Antwort A hat dann dasselbe `n` und wird angenommen. Wegen der gleichen Daten meist harmlos. Hat sich in der Zwischenzeit etwas geändert (Einzel-Rücknahme), kann A älter als B sein und B kurz überschreiben.
- Vorschlag: Zähler pro Seite (`this._listeN++`) statt pro Eintrag.

### GT-6 (Niedrig): Hinweistext bei verdrängtem oder abgelaufenem Vorschau-Bild passt nicht

- Datei: `texte.js:1267` (`cover_ohne_bild`: „Neues Cover: Das Bild siehst du erst bei „Online suchen“.“), `online.js:337`.
- Was: Bei einem Vorschlag mit Cover, dessen `vorschau_id` per 410 verdrängt wurde (oder bei Netzfehler), erscheint der Satz, als gäbe es kein Bild. Das Bild gibt es, nur die Vorschau fehlt. „Übernehmen“ funktioniert. Das ist mit Test 1312 so gewollt, der Text ist für diesen Fall aber irreführend.
- Vorschlag: Eigener Satz für „Vorschau gerade nicht verfügbar, das Cover wird beim Übernehmen geladen“, oder den Satz neutraler fassen.

### GT-7 (Niedrig): `aria-controls` zeigt auf ein Element, das zugeklappt nicht da ist

- Datei: `technik_online.js:295` (`aria-controls=to-liste-<id>`, das `div` wird nur bei offener Liste gezeichnet, `_liste` liefert sonst `nothing`).
- Was: Zugeklappt verweist `aria-controls` ins Leere. Das ist kein Fehler im Sinn von Leseprogrammen, wird aber teils gemeldet.
- Vorschlag: Das `div` immer zeichnen (mit `hidden`) oder `aria-controls` nur im aufgeklappten Zustand setzen.

### GT-8 (Niedrig): Fehlende Tests im Backend

- Datei: `tests/test_online_befehle.py` (Abschnitt Nr. 65 und T10).
- Fehlt:
  1. verfallene Änderungen (älter als 30 Tage) fehlen in Nr. 65;
  2. Eintrag, den es nicht mehr gibt (`finde` wirft), fehlt in Nr. 65;
  3. Änderung mit leerem `felder` (siehe GT-2);
  4. Einzel-Rücknahme mit allen Feldern übersprungen (siehe GT-1);
  5. Nr. 59 mit einer `vorschau_id` als `treffer_id` ergibt `treffer_abgelaufen` (getestet ist nur Nr. 58);
  6. HTTP-Vorschau mit `vorschau_id` eines Eintrags, der gelöscht wurde.
- Vorschlag: Kurze Tests ergänzen. Sie sind klein, die Logik steht schon.

## Geprüft, in Ordnung

- **Nr. 65 Ausgabeform:** Schlüssel `eintraege` und `weitere`; je Eintrag `serie_id`, `name`, `aenderung_id`, `zeit`, `status`, `felder`. Sortierung nach `name` (casefold, danach `name`, `serie_id`). `name` ist der heutige Name. Status nur `fertig` und `zurueckgenommen`, offene fehlen. Die Grenze 500 mit `weitere` stimmt, die Konstante steht in `const.py`.
- **Nr. 65 Fehler:** `lauf_nicht_gefunden` (gegen die gehaltenen Läufe), `invalid_format` (fehlende oder fremde Felder, getestet), `unauthorized` für Nicht-Administratoren (`recht="admin"`). In `test_rechte_schutz.py` steht die Zeile 65. Die Vertragsübersicht gibt 65 Befehle her.
- **Fähigkeit `online_lauf_liste`:** in `const.py` und an den Hello-Tests nachgezogen. Die Seite zeigt ohne sie nur Zahlen und „Alle zurücknehmen“ (Test 1497). Kein Befehl 65 ohne Fähigkeit (Mock: `unknown_command`).
- **Nicht-Admin:** Seite zeigt nichts und schickt keinen Befehl 65 (Test 1510). Die HTTP-Vorschau mit `vorschau_id` gibt 403 für Nicht-Administratoren (Python-Test). Das Backend lässt Nr. 65 für Nicht-Administratoren nicht durch.
- **`vorschau_id`:** 16 Zeichen `[0-9a-f]`; nur bei Vorschlag mit `cover` in `felder`; fehlt, wenn das Bild nicht geladen werden kann. Eine `vorschau_id` ist als `treffer_id` für Nr. 58 und Nr. 59 abgelehnt (`treffer_abgelaufen`). Haltezeit 15 Minuten (TTL), Ablauf 410 getestet. Vorschau 192 px, `Cache-Control: no-store`.
- **Seite, Vorschau:** Platzhalter und Satz richtig geschaltet (`vorschauLaedt`); `blob:` wird beim Schließen und bei neuer Übersicht freigegeben, ein zu spät ankommendes Bild gleich. Netzfehler und 410 lassen die Übersicht benutzbar. Kein zweiter Versuch bei der `vorschau_id` nötig (kein 404).
- **Seite, Liste:** Doppeltipp auf „Zurücknehmen“ wird durch `tu` geschluckt, nur ein Befehl 60; die anderen Knöpfe und „Alle zurücknehmen“ sind währenddessen grau. Nach „Alle zurücknehmen“ lädt die offene Liste still nach. Fehlerkarte mit „Noch einmal versuchen“, `lauf_nicht_gefunden` schließt die Liste und lädt die Läufe neu. Beim Verlassen ist die Liste zu. Ein veraltetes `aenderung_nicht_gefunden` lädt Liste und Läufe neu.
- **Alles Test-Technische:** die Befehle 60 der Einzel-Rücknahme sind ohne `lauf_id`; der Link zeigt auf `#serie-<id>`; die Texte sind einfach und ohne echte Namen.
