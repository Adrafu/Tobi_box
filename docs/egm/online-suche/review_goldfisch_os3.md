# Review Goldfisch: Paket OS3 (Online-Suche, Anbindung an HA)

Stand: 19.11., Rev. 2.5 des Designs. Geprüft: `online.py` (neu) und die Änderungen in `websocket_api.py`, `http.py`, `media.py`, `cover.py`, `hub.py`, `eingang.py`, `neu_einsortieren.py`, `config_flow.py`, `const.py`, `fehler.py`, `bibliothek.py`, `gehoert_abfrage.py`, `__init__.py`, `manifest.json`, Texte und Tests.
Gegen Design 3.4, 5, 6, 7, 9, 12, Vertrag W (2.1, 3.2, 3.15, 4.11, 7, 14.1 bis 14.3), `data-model.md` 5 und 5b, die Auflagen aus `stueckliste-und-psp.md` und `resolve.md` Runde 6.

Die Tests `test_online_dienst.py` und `test_online_befehle.py` laufen grün (91 Tests). Ich habe den Code nicht geändert. Zum Nachweis habe ich kleine Probe-Tests in einer **Kopie** des Testordners im Scratchpad laufen lassen (nichts im Repo). Die Befunde GO3-1 bis GO3-4 sind damit belegt, nicht nur gelesen.

Zahl der Befunde: hoch 1, mittel 5, niedrig 7.

---

## Hoch

### GO3-1 (hoch): „Bestätigt“ legt leere Änderungen an, macht Handfelder wieder automatisch und verdrängt echte Änderungen

**Wo:** `online.py:1145-1147` (`verteile`), `1197-1198` (`if auto or bestaetigt`), `1362-1378` (`_schreibe`: nur `bestaetigt` genügt für eine Änderung), `1439-1446` (Schnappschuss für bestätigte Felder), `2013-2016` und `2031-2035` (Rücknahme zählt und markiert bestätigte Schlüssel), `766-778` (`kurz_online`).

**Was falsch ist:** Jedes Feld, das die Quelle als **sicher** liefert und das schon genau so im Eintrag steht, kommt in `bestaetigt`. Das gilt auch, wenn es nichts aufzulösen gibt (kein Prüfgrund) und auch für Felder in `hand`-ähnlichem Zustand (Grund `vorschlag`, nur `hand` wird ausgenommen). Folgen:

1. **Leere Änderung.** Auch ohne ein einziges geändertes Feld schreibt `_schreibe` eine Änderung (`felder: {}`, `bestaetigt: [...]`) mit `offen` und `fertig`, zwei `async_save`. Bei jedem Eintrag, der schon stimmt, jedes Mal, wenn er neu gefragt wird.
2. **`online` für alle.** `kurz_online` nimmt die **letzte** Änderung mit Status `fertig`. Ist das so eine leere, kommt `{"zeit": …, "felder": []}`. Die Zeile „Aus der Online-Suche übernommen: “ erscheint dann für **alle Benutzer** ohne Feldnamen, und sie ersetzt die Zeile der echten Änderung davor (Design 10, R1; Vertrag 14.2).
3. **Verdrängung.** Die leeren Änderungen zählen zu den höchstens 20 je Eintrag. Echte Änderungen mit Vorher-Werten fallen dadurch nach vorn heraus und lassen sich nicht mehr zurücknehmen (7.3).
4. **Handfelder werden automatisch.** `_schreibe` setzt für bestätigte `folge_titel`, `nummer`, `art` einen **neuen Schnappschuss** (`1439-1446`). Hat ein Mensch den Titel von Hand gesetzt oder bestätigt (Schnappschuss weg, 6.2) und die Quelle liefert denselben Wert, steht das Feld danach wieder auf „frei“ (`_sperre_grund`). Ein späterer anderer sicherer Wert überschreibt dann die Menschenhand. Das widerspricht 6.1 („Schnappschuss: Wert, den Einsortieren oder eine automatische Übernahme **gesetzt** hat“) und 6.2 („bestätigt = von Hand“).
5. **Rücknahme zählt und markiert Unverändertes.** `_eine_aenderung_zuruecknehmen` nimmt die bestätigten Schlüssel ohne Prüfung in `zurueck_keys`. Sie werden mitgezählt (`zurueckgenommen`), bekommen die Marke `zurueckgenommen` (Rücknahme je Änderung/Eintrag) und stellen `pruefen` der Folge wieder her, auch wenn ein Mensch den Wert seitdem geändert und den Grund damit erledigt hat. Das widerspricht 6.4 („nur zurückgesetzt, wenn es noch den Online-Wert trägt“).

**Beleg (Probe):** Bibi-Fall, `arbeite()` zweimal. Zweite Änderung: `felder == []`, `bestaetigt == ['folge_titel@f100', 'nummer@f100', 'beschreibung@f100', 'alter_ab@f100']`; `kurz_online() == {'zeit': …, 'felder': []}`; `zuruecknehmen(SID)` meldet `zurueckgenommen: 10`, obwohl nur 5 Felder geändert wurden. Mit entferntem Schnappschuss (Mensch hat bestätigt) und gleichem Wert: danach `_sperre_grund(...) == "frei"`.

**Szenario:** Tobias startet den echten Lauf (OS5 Schritt 10). Von 340 Einträgen stimmen viele schon. Jeder bekommt eine leere Änderung. Die Seite zeigt allen (auch der Partnerin) „Aus der Online-Suche übernommen:“ ohne Inhalt. Die Stichprobe und „Alle zurücknehmen“ zählen falsch, und der Lauf hat Handwerte wieder der Automatik freigegeben.

**Vorschlag:** `bestaetigt` nur füllen, wenn es **wirklich etwas aufzulösen gibt** (der Prüfgrund des Felds ist da, 5.5). Nur dann zählt es als Änderung. Ist `felder` leer und `bestaetigt` nicht leer, die Prüfgründe ohne eigene Änderung auflösen (oder die Änderung nicht in `aenderungen`/`kurz_online` führen). Keinen Schnappschuss für bestätigte Felder setzen, wenn das Feld vorher keinen hatte (Grund `vorschlag`). Rücknahme: bestätigte Schlüssel nur mit eigener Prüfung (Wert unverändert) und nicht in `zurueckgenommen` zählen. Test dazu: zweiter Lauf an einem Eintrag, der schon stimmt, legt nichts an.

---

## Mittel

### GO3-2 (mittel): Kandidatenliste des Laufs ist nach jedem Neustart zu groß, „Weiter nach Neustart“ fragt alte Einträge neu

**Wo:** `online.py:1643` (`stand = self.tonie_liste.stand if …`), `1675-1677` (`lauf_starten` ruft `lauf_kandidaten`, ohne die Liste geladen zu haben), `344-356` (`marke_gueltig` vergleicht `m.get("liste") == liste_stand`).

**Was falsch ist:** `TonieListe.stand` ist `None`, bis zum ersten `sicherstellen()` (`online_quellen.py:910`). In `lauf_starten` wird nur `_quellen_bereit()` aufgerufen. Alle Marken `keiner`/`fehler` tragen die Zahl `liste` und gelten damit als ungültig: Sie kommen alle in die Kandidatenliste, sobald (b) zutrifft (praktisch immer, „Folge ohne Beschreibung“). Marken `geaendert`/`vorschlag` sind nicht betroffen.
Dazu: `stand` ist laut OS2 die Zeit des letzten erfolgreichen Abgleichs „(neu oder 304)“; jede wöchentliche Prüfung ändert ihn, auch ohne neue Liste. Das Design (5.3, 7.3) sagt: „bei neuer Tonie-Liste“.

**Beleg (Probe):** Marke `keiner` mit gleichem `stand` → `lauf_kandidaten() == []`. `stand = None` gesetzt → `['bibi']`.

**Szenario:** OS5 Schritt 1 („Zahl der Kandidaten nennen“) und Schritt 9: HA neu starten, neuer Lauf. Die Zahl ist zu hoch, und alle schon als `keiner` abgehakten Einträge werden noch einmal durchgesucht (Stunden Apple-Anfragen).

**Vorschlag:** In `lauf_starten` vor `lauf_kandidaten()` `tonie_liste.sicherstellen()` aufrufen (Fehler egal), oder die Marke an etwas Stabiles binden (ETag, Zahl der Einträge). Test: Marke `keiner`, Neustart (neue `OnlineDienst`-Instanz), Kandidatenliste bleibt leer.

### GO3-3 (mittel): Pause beim Cover-Bild verliert das Cover und wird als „fertig gesucht“ gemerkt

**Wo:** `online.py:1216-1219` (`_cover_bytes`: bei `QuellePausiert` nur `erg["pause"]`, kein `erg["fehler"]`), `1192-1195` (Cover fällt aus `auto`, auch nicht als Vorschlag), `1040-1051` (Marke wird trotzdem gesetzt), `1740-1743` und `1738-1739` (Lauf wiederholt dieselbe Serie, aber jetzt ist die Marke gültig und `nur_claude=True`).

**Was falsch ist:** Zieht Apple bei den **Bildern** die Bremse (eigene Gruppe `bilder`), geht das sichere Cover verloren. Die Serie bekommt die Marke `geaendert`/`keiner` (ohne `fehler`). Der Lauf schläft, versucht dieselbe Serie nochmals, sieht jetzt eine gültige Marke und macht nur noch den Claude-Schritt. Das Cover wird nie nachgeholt. Beim Einsortieren (Schlange) ebenso. Die Apple-Suche selbst (Gruppe `itunes`) macht es richtig (Rückkehr vor der Marke).

**Beleg (Probe):** `bild_holen` wirft `QuellePausiert("bilder")`: `erg` hat `pause` gesetzt und `geaendert: 4`, `vorschlaege == []`, `marke_gueltig == True`.

**Vorschlag:** Bei Pause im Bild: wie bei der Suche vor der Marke zurückkehren (`_anwenden` vorher abbrechen oder `erg["fehler"] = True` setzen und keine Marke außer `fehler` schreiben), oder das Cover als Vorschlag anlegen. Test: Bild-Pause im Lauf, danach geht derselbe Eintrag noch einmal komplett durch.

### GO3-4 (mittel): Eine Ausnahme in einer einzigen Serie bricht den ganzen Lauf ab, mit dem Grund „Quelle“

**Wo:** `online.py:1764-1768` (`_lauf_laufen`: `except Exception` um die ganze Schleife → `abgebrochen`, `grund quelle`). Die Schlange (`914`) fängt je Serie.

**Was falsch ist:** Jeder Fehler im Code oder in den Daten einer Serie (ein `KeyError` im Abgleich, ein kaputter Eintrag) beendet einen Lauf, der 3,5 Stunden dauern soll, und meldet „Abgebrochen: Quelle nicht erreichbar“ (Design 5.3, GO-12: `quelle` heißt drei Pausen in Folge). Der Rest der Bibliothek wird nicht bearbeitet.

**Beleg (Probe):** `_arbeite_serie` wirft `KeyError`: Lauf `abgebrochen`, `grund: quelle`, `erledigt: 0`.

**Vorschlag:** Die Ausnahme je Serie fangen, loggen, Marke `fehler` setzen, `erledigt` zählen und weitermachen. Test mit einer Serie, die wirft, und einer zweiten dahinter.

### GO3-5 (mittel): Das Schreiben der Automatik prüft nur Werte, nicht `hand`/`zurueckgenommen` und nicht Beschreibung und Alter

**Wo:** `online.py:1244-1263` (`_schreibe_auto`). Die Entscheidung „frei/Vorschlag/hand“ fällt in `_anwenden` **vor** dem Netz (`1144`), unter der Sperre wird nur verglichen: Cover-Stand, `art`/`art_quelle`, `anzeige`/`nummer` gegen die gemerkten Startwerte.

**Was falsch ist:** Design 5.1 Schritt 4 verlangt „die Felder noch den gemerkten Werten entsprechen“. Das stimmt für diese Felder. Nicht geprüft werden `beschreibung`, `alter_ab` (der Dienst vergleicht den Store nicht) und die **Marken** (`hand`, `zurueckgenommen`). Zwischen dem Start (Minuten bei Apple-Drossel) und dem Schreiben kann ein Administrator
- eine Beschreibung von Hand übernehmen (`hand.beschreibung@f`) oder zurücknehmen (Marke): die Automatik schreibt trotzdem den neuen Wert darüber;
- Titel/Nummer bestätigen (nur Schnappschuss weg, Wert gleich): die Automatik darf noch schreiben.

**Szenario:** Der Lauf liest für Folge 3 die Beschreibung aus der Tonie-Shopseite. Während er auf den nächsten Treffer wartet, übernimmt Tobias für diese Folge von Hand eine andere Beschreibung. Der Lauf überschreibt sie, obwohl `hand` gesetzt ist („die Automatik fasst Felder in `hand` nie an“, 6.1).

**Vorschlag:** Unter der Sperre `_sperre_grund` für jedes Feld neu auswerten (frisch gelesen), und für `beschreibung`/`alter_ab` den Store-Wert mit dem Wert beim Start vergleichen. Wer nicht mehr „frei“ ist, wird Vorschlag oder verworfen.

### GO3-6 (mittel): Tests decken wichtige Zusagen nicht ab

Ohne Fehler im Code, aber die Auflagen und OS5 verlangen es:

1. **Veraltete Felder (5.1 Schritt 4, GB-19)**: kein Test, dass ein Feld, das sich zwischen Start und Schreiben geändert hat, zum Vorschlag wird, und eine verschwundene Folge/Serie still verworfen wird (`_schreibe_auto`, `1248-1263`).
2. **Design 6.4 „Test je Feld: Rücknahme, dann Lauf: Feld bleibt, Vorschlag möglich“**: `test_marke_zurueckgenommen_verhindert_wiederkehr_im_lauf` prüft nur `art`, `cover`, `nummer`. Es fehlen `folge_titel`, `beschreibung`, `alter_ab` (und `serie_name` über `hand`).
3. **GO3-1** (zweiter Lauf an einem Eintrag, der stimmt) und **GO3-2/3/4**: kein Test.
4. **Fehler beim Schreiben** (`OSError` in `schreibe_serie` oder beim Cover) nach dem Status `offen`: nur der Start-Klärfall ist getestet, nicht der Fehlerweg selbst (siehe GO3-7).
5. **Mehr als eine Folge/Serie**: alle Online-Tests laufen an einer Serie mit einer Folge (`f100`). Pflegestellen mit mehreren Folgen, Reihenfolge und Mischfälle (Prüfgründe an mehreren Folgen, `ganz`) sind nicht geprüft.
6. **Auflage „Vorschlag zum Zusammenführen (8.4)“**: der Fall steht in `test_online_dienst.py:707`; die Ablehnung („Nein“) eines Zusammenführen-Vorschlags und dass er nicht wiederkommt, fehlt (siehe GO3-10).
7. **OS5 Schritt 7** („Name von Hand ändern, dann Lauf: Name bleibt“) ist nur indirekt gedeckt (kein Test, der nach `serie/rename` einen Lauf macht und den Namen prüft).

**Vorschlag:** Tests nachliefern, bevor OS5 beginnt. Punkt 1 und 3 am wichtigsten.

---

## Niedrig

### GO3-7 (niedrig): Fehlgeschlagenes Schreiben lässt die Änderung „offen“ stehen; die Start-Klärung stellt den ganzen Schnappschuss alt wieder her

**Wo:** `online.py:1380-1382` (offen), `1421-1422` (`OSError` → raise, Änderung bleibt), `404` (`verfall_aenderungen` lässt `offen` immer stehen), `655-656` (`s["schnapp"] = a["schnapp_vorher"]`).

Schlägt `schreibe_serie` oder das Cover fehl, bleibt die Änderung `offen` bis zum nächsten Start, zählt aber nicht für `kurz_online` und nicht für die Rücknahme. Bis dahin ändern sich Schnappschüsse (neue Übernahmen). Beim Start wird dann der **gesamte** Schnappschuss durch den alten ersetzt: neuere Schnappschüsse sind weg, die zugehörigen Felder gelten als von Hand (sichere Richtung, aber Datenverlust an Herkunft). Das Design sagt „verwerfen und den Schnappschuss aus `schnapp_vorher` wiederherstellen“, meint aber die Felder dieser Änderung. Dazu zählen offene Änderungen nicht zu den 20 (Liste kann wachsen).

**Vorschlag:** Bei einem Fehler im Schreiben die Änderung sofort entfernen und nur die Schnappschuss-Schlüssel der Felder dieser Änderung zurückstellen; beim Start dasselbe feldweise.

### GO3-8 (niedrig): Rücknahme eines Namens von Hand stellt die Prüfgründe der Serie nicht wieder her

**Wo:** `online.py:1394` (`serie.pruefen, serie.pruefen_gruende = False, []` bei `serie_name`), Rücknahme `2019-2023` (Wiederherstellung nur, wenn `art` unter den Schlüsseln ist).

Vertrag 3.15 Nr. 60: „Zurückgesetzt werden auch `pruefen`, `pruefen_gruende`“. Nach einem Namen von Hand (Treffer, nicht Claude) und anschließender Rücknahme ist der Name zurück, die Serien-Gründe (zum Beispiel `teilweise_doppelt`) bleiben gelöscht. Vorschlag: bei `serie_name` ebenfalls aus `pruefen_vorher.serie` wiederherstellen.

### GO3-9 (niedrig): Zwei „start“ zugleich können zwei Läufe starten

**Wo:** `online.py:1673-1690`. Die Prüfung `self._lauf … in LAUF_LAUFEND` und das Setzen von `self._lauf` liegen vor und nach `await`s (`_stelle_geprueft_sicher`, `_quellen_bereit`). Beim ersten Aufruf nach dem Start (Quellen noch `None`, `lese_version` im Executor) kann ein zweiter `start` dazwischenkommen. Dann laufen zwei Läufe, `async_stop` kennt nur den zweiten. Vorschlag: `self._lauf` (oder ein Flag) sofort nach der Prüfung setzen, vor dem ersten `await`.

### GO3-10 (niedrig): „Nein“ zu einem Claude-Vorschlag zum Zusammenführen wird beim Anlegen nicht geprüft

**Wo:** `online.py:1549` (verwirft mit Feld `zusammenfuehren`, Hash über `ziel_serie_id`) gegen `1596` (prüft nur `serie_name` mit Hash über den Namen). Heute verhindert die Marke `claude = vorschlag` (nie verfallend) das Wiederkommen. Fällt die Marke weg (Eintrag neu angelegt, Marke verloren), kommt derselbe Vorschlag zurück. Vorschlag: in `_claude_vorschlag` auch `zusammenfuehren` + Hash der Ziel-ID prüfen, Test dazu.

### GO3-11 (niedrig): Store wird mit dem lebenden Dict gespeichert

**Wo:** `online.py:193` (`async_save(self.daten)`), `197` (`lambda: self.daten`). HA serialisiert im Executor; der Event-Loop ändert `daten` währenddessen (Lauf, Schlange, Befehle). Mögliche Folge: „dictionary changed size during iteration“, der Schreibvorgang scheitert, bis zum nächsten Mal. Dasselbe Muster haben `medieninfo.py` und andere Stores; im Online-Store ist es wegen des langen Laufs wahrscheinlicher. Vorschlag: `copy.deepcopy` im Dienst (oder `json`-Rundreise) beim Übergeben, oder Speichern nur zwischen zwei Serien.

### GO3-12 (niedrig): „Anhalten“ in der Pause wartet bis zu 15 Minuten; `pausiert` überschreibt `wird_angehalten`

**Wo:** `online.py:1747-1754`. `_schlafen(max(0, pause_bis - jetzt) + 1)` ist nicht abbrechbar; der Zustand fällt von `wird_angehalten` auf `pausiert`/`laeuft` zurück, wenn eine Pause nach dem `stop` kommt. Vorschlag: schlafen in Schritten (oder `asyncio.Event`), Zustand `wird_angehalten` nicht überschreiben.

### GO3-13 (niedrig): kleine Abweichungen

- `eingang.py:1308-1318`/`online.py:885-886`: Ein Upload mit Wunschname (`art_quelle = manuell`) bekommt trotzdem einen Art-Schnappschuss; Design 6.2 sagt „keinen“. Folgenlos, weil `art_quelle` die Sperre schon gibt.
- `online.py:731-743`, `1213`, `1217`: Die Quelle `tonies` (Tonie-Liste) meldet nie ein Ereignis `quelle`; eine Pause der Bilder wird als `itunes` gemeldet. Vertrag 4.11: Wechsel aller drei Quellen.
- `hub.py` (`beim_start` in `contextlib.suppress(Exception)`): Ein Fehler beim Aufräumen oder beim Klären offener Änderungen bleibt unbemerkt. Wenigstens loggen.
- `cover`-Upload (`cover-eigen.jpg`) ersetzt eine Marke `zurueckgenommen.cover` nicht durch `hand` (Design 6.2 nennt das Hochladen). Beide sperren die Automatik gleich.

---

## Geprüft, in Ordnung

- **Rechte (2.1, 3.15):** Nr. 57 bis 63 `admin`, Nr. 64 `lesen`; Vorschau-GET und `DELETE ?quelle=online` nur Administratoren (403 `unauthorized`); `online_vorschlag` für Nicht-Administratoren `unauthorized`; `online_vorschlaege` und `online_vorschlaege_liste` nur für Administratoren; `online` (Kurzform) für alle; `online_vorschlaege` fehlt in Antworten auf Änderungen. Tabelle in `test_rechte_schutz.py` und `test_online_befehle.py` bestätigt das.
- **Ereignis `online` (4.11):** `Abo.ist_admin`, Filter in `Hub.emit`, Themen erst auflösen, dann `online` streichen (`["online"]` bleibt leer, kein Snapshot); Arten `snapshot`/`stand` (gebündelt 2 s)/`fertig`/`quelle`; Daten entsprechen dem Vertrag.
- **Fehlercodes (7):** sechs neue Codes mit den richtigen HTTP-Nummern, Texte in `strings.json` und `translations/de.json`; `online_nicht_erreichbar` nur, wenn keine Quelle antwortet.
- **Cover-Vorrang eigen > online > auto** in `cover_zustand`, `lese_cover_datei`, `uebernimm_cover`; `neu_suchen` berührt `cover-online.jpg` nie; `entferne_online` ohne Store-Änderung; Vorschau mit `RE_LISTE_ID` (kein Zeilenumbruch-Trick), `no-store`, 192 px aus dem gehaltenen Bild; Cover wird im Executor geprüft und geschrieben.
- **Übernahme-Reihenfolge 6.3** (offen mit `sofort`, Dateien, Store, `fertig`, Rückweg, `serien_geaendert`) und Start-Klärung offener Änderungen in beiden Richtungen; `online_text`/`name_pruefen` vor dem Schreiben (Auflage 1); Name wird **nie** automatisch gesetzt (`serie_name` nur über Vorschlag/Hand).
- **Von Hand (6.1):** Handübernahme setzt `hand`, kein Schnappschuss, entfernt die Marke `zurueckgenommen`; Claude-Namensvorschlag ist ein Umbenennen von Hand (`aenderung_id` null, nicht in `online.felder`, `stand` Pflicht); der Vorschlag fällt weg, wenn der Name nicht mehr `name_vorher` ist.
- **Rücknahme 6.4** (je Änderung, je Eintrag, je Lauf): nur bei unverändertem Wert, `folge_titel`/`nummer` gemeinsam, Cover über den Dateistand, Schnappschuss gelöscht, Marke nur bei Änderung/Eintrag, nicht beim Lauf; Lauf-Rücknahme im Hintergrund, doppelte Anstellung zählt einmal.
- **Verworfene Vorschläge** kommen im Lauf nicht wieder (gleicher Hash), in der Suche von Hand mit `frueher_abgelehnt`; Übernehmen zählt nicht als „Nein“.
- **Pflegestellen:** Folge löschen, Serie löschen, Verschieben, Zusammenführen (`hand.cover`/`zurueckgenommen.cover` ziehen mit), Anders einsortieren, `bereinige` beim Start (nur nach gelungener Prüfung der Freigabe), `async_stop` (Tasks abbrechen, laufenden Lauf als `abgebrochen`/`neustart` speichern). Lock-Reihenfolge `_arbeit` → Serien-Sperre ohne Gegenrichtung (keine Verklemmung).
- **Auflagen an OS3:** `online_text` vor dem Schreiben ✓; Beschreibung erst nach den Shopseiten (`shop_daten[model]`, `None` = geholt, unbrauchbar) ✓; Pausengruppen auf Nr. 63 (`itunes`+`bilder`, `tonies`, `tonies_shop`) ✓; `lese_version` im Executor ✓; Marke `claude` (`aus`, `fehler` 1 Tag, `vorschlag`/`behalten` nie) und Vorschlag zum Zusammenführen getestet ✓; T7 (Test „keine Modellnamen“ erlaubt genau `claude` und `anthropic`) ✓.
- **Netz und Datenschutz:** Tests ohne Netz (Autouse-Attrappe der Sitzung, Fixtures); alle Abrufe über OS2 (`hole`); Rechenarbeit des Index und Bildprüfung im Executor; an Claude geht nur, was 8.3 nennt (Name, Ordnername, Folgentitel, Prüfgründe, Kandidaten, `einzeltitel`, Folgenzahl), keine IDs und Tobie-Namen; der Optionsdialog sagt es; Vorgabe „gleich eingeschaltet“ wie von Tobias entschieden, `manifest.json` mit `after_dependencies: ai_task`.
- **Einsortieren:** `_online_merken` legt nur in die Schlange, fängt Fehler, hält das Einsortieren nie auf; Rückweg wird nach automatischer Übernahme fortgeschrieben, nach Handübernahme nicht.

## Hinweis zur Abnahme (kein Befund)

Weil die Claude-Entität ohne ausdrückliche Einstellung als Vorgabe gilt (genau eine `anthropic`-Entität), gehen Daten zu Anthropic, sobald der echte Lauf (OS5 Schritt 10) startet, auch wenn Tobias den Optionsdialog nie geöffnet hat. Für Schritt 14 und 15 der Abnahme muss er die Option zuerst ausdrücklich leeren bzw. setzen; das gehört in die Anleitung in `docs/betrieb/`.
