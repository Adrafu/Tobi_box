# Altersfilter: Code-Review (AF3, frischer Agent)

Geprüft: die nicht eingecheckten Änderungen in `homeassistant/` und `box/tests` gegen `docs/designs/altersfilter.md` (Rev. 2),
den Vertrag `docs/protocol/ha-websocket-v1.md` (Stellen „23.11.“) und `docs/data-model.md` (Abschnitt 5). Gelesen und
verglichen: `media.py`, `bibliothek.py`, `websocket_api.py`, `const.py`, `bausteine.js`, `seiten/bibliothek.js`, `seiten/serie.js`,
`texte.js` und die Tests. Gelaufen: `tests/test_altersfilter.py` (97 bestanden); die Box-Tests und die Seitentests mit DOM
konnten hier nicht laufen (kein pytest für die Box, kein jsdom).

Gesamteindruck: Die Regel und der Vertrag sind sauber umgesetzt. Ich habe **keinen hohen Fehler** gefunden. Geprüft und in Ordnung:

- `0` ist überall ein gültiger Wert (`gueltiges_alter`, `alter is not None`, `eintrag is None`; kein `if wert:`).
- Hand vor Shop, kleinster gültiger Shop-Wert, nur Folgen aus `serie.folgen`, bool abgelehnt.
- `alter_hand` steht in `bekannt` (nicht in `extra`), ungültig wird `None`, `to_json` schreibt nur gültige Werte, `stand` bleibt unberührt.
- Filter ≤ X und `"ohne"` laufen vor `offset`/`limit`, `gesamt` zählt danach. Filter und `alter_ab` der Kurzform kommen aus **einem** Wörterbuch je Anfrage, nichts liegt im Index.
- Schema streng: bool, `"4"`, `"Ohne"`, -1, 19 werden abgelehnt (`_ganz`).
- Befehl 66: Recht alltag, Schreiben über `_frisch` und `schreibe_serie` wie Befehl 38, Ereignis nur bei Änderung, `null` löscht.
- Zusammenführen übernimmt nur ins Ziel ohne Wert; `folge/verschieben` fasst das Feld nicht an.
- Seite: Abschnitt und Menüpunkt nur mit Fähigkeit `alter`, `listenAnfrage` sendet eine Zahl, Einzeltitel zeigt das Alter nur oben, Fehler lässt das Blatt offen.
- Rückfall: neue Seite ohne Fähigkeit und ohne `alter_ab` zeigt nichts. Alte Seite an neuer Integration sendet kein `alter` und ignoriert die neuen Felder.
- Texte deutsch, keine echten Namen.

## Befunde

| Nr. | Schwere | Befund | Vorschlag |
|---|---|---|---|
| AC-1 | mittel | `media.py:726` (`_eintrags_alter`): `folgen.get(n, {}).get("alter_ab")` stürzt ab, wenn im Store ein Folgen-Eintrag `None` ist (oder `folgen` kein Dict). Weil `eintrags_alter_je_serie` bei **jeder** `serien/list`-Anfrage über alle Einträge läuft, würde ein einziger solcher Eintrag die ganze Bibliothek lahmlegen (vorher traf das nur die Einzelansicht). `online.py:351` (`folge_info`) fängt das mit `or {}` ab. | `self.hub.online.store.folge_info(s.id, n).get("alter_ab")` benutzen (wie im Design 4.2 genannt). Ein Test mit `store.daten["serien"][id]["folgen"][name] = None`. |
| AC-2 | niedrig | `media.py:1032`: Das Wörterbuch wird auch ohne Eingabe `alter` für **alle** Einträge gebaut, obwohl `kurzform` nur die Einträge der Seite braucht. Das entspricht dem Design (je Anfrage), kostet bei 600 Einträgen aber bei jedem Aufruf der Bibliothek eine volle Runde. Gemessen wird nur gegen 1 s (`test_altersfilter.py:~430`, `LEISTUNG_GRENZE_S = 1.0`), das Ziel im Design ist 200 ms. | Wörterbuch nur bauen, wenn `alter` gesetzt ist; sonst `kurzform` ohne `alter_je_serie` (rechnet je Seiteneintrag selbst). Oder die Grenze im Test auf 0,2 s ziehen und den Wert protokollieren. |
| AC-3 | niedrig | `media.py:660ff`/`kurzform`: bei `serien/list` mit Filter wird `alter_ab` aus dem Wörterbuch genommen, das **vor** dem `await self.hub.gehoert.zwischenspeicher()` gebildet wurde. Ändert sich der Store in diesem Await (Online-Lauf), kann ein Eintrag gefiltert und mit anderem Wert angezeigt werden. Sehr unwahrscheinlich, Folge wäre nur eine Anzeige bis zum nächsten Laden. | Nur zur Kenntnis; oder das Wörterbuch direkt vor dem Aufruf von `bibliothek.serien` bilden. |
| AC-4 | niedrig | `seiten/serie.js:~574` (Blatt „Ab welchem Alter?“): Die Zeile „Wert von Hand löschen“ ist ein Knopf mit `aria-pressed` **innerhalb** derselben `se-stack`, aber außerhalb der `radiogroup`. Das ist in Ordnung. Aber „Speichern“ ohne Änderung (nichts gewählt, nichts von Hand) schließt das Blatt wortlos, ohne Meldung. | Optional: Meldung oder deaktivierter „Speichern“-Knopf, solange nichts gewählt ist. Kein Fehler. |
| AC-5 | niedrig | `seiten/bibliothek.js:~144` (`alter()`): Der Absatz `<p class="alter-hinweis">` („Für ein Kind mit … Jahren“) steht **innerhalb** der `radiogroup` und ist kein `radio`. Bildschirmleser zählen die Gruppe dann evtl. mit einem Fremdkörper. Die 13 Knöpfe haben kein Pfeiltasten-Verhalten (Design 5.1 / AF-11 erlaubt das). | Den Absatz vor die `radiogroup` setzen und die Gruppe über `aria-labelledby` benennen; oder bewusst so lassen. |
| AC-6 | niedrig | `seiten/serie.js` (`_eineFolge`, `_folgeOnline`): Der Wert an der Folge wird nur ausgeblendet, wenn `s.alter_ab` oben steht. Hat ein Einzeltitel einen Folgen-Wert außerhalb 0 bis 18 (z. B. 40 im Store), zeigt `Number.isFinite` an der Folge „ab 40“, oben aber nichts. Der Store prüft beim Schreiben (`_alter_gueltig`), also nur bei beschädigtem Store. | Nur zur Kenntnis, oder `Number.isInteger(a) && a >= 0 && a <= 18` an der Folge wie in `alterAendern`. |
| AC-7 | niedrig | Tests: In `tests/frontend/online_suche.test.mjs` läuft ohne jsdom ein Test (`GO4-1/GO4-4`, Zeile ~990) mit „html is not a function“ in den Fehler. Ich konnte nicht klären, ob das schon vor der Änderung so war (die Änderung dort sind nur 3 Zeilen). Alle neuen DOM-Tests (`MIT_DOM`) sind hier übersprungen, also **nicht geprüft**. | Mit `TOBIBOX_JSDOM_DIR` setzen und die vier geänderten Dateien einmal vollständig laufen lassen, bevor die Abnahme beginnt. |
| AC-8 | niedrig | Tests: `test_befehl_66_braucht_das_recht_alltag_nicht_lesen` (`test_altersfilter.py:282`) prüft nur den Eintrag in `BEFEHL_RECHTE`, nicht das Verhalten. Das Verhalten deckt die neue Zeile in `test_rechte_schutz.py` ab, der Test ist also doppelt, aber nicht falsch. Die Seitentests für `serien/list` laufen gegen den Mock (`mock-hass.mjs`), prüfen also die Seite, nicht das Backend; das ist üblich im Projekt. | Kein Handlungsbedarf. |
| AC-9 | niedrig | Abdeckung Design 7: AF1 ist vollständig abgedeckt (Regel, Filter, Schema, Befehl 66, `hello`, Roundtrip, `stand`, rename/38, Papierkorb, Zusammenführen beide Fälle, `folge/verschieben`, Einzeltitel, Laufzeit; Box-Test vorhanden, hier nicht gelaufen). AF2: Fähigkeit, `aktiveEinstellungen`, Zurücksetzen, `listenAnfrage` als Zahl, `aria-checked`, Neuladen ab Anfang sind da. Nicht gefunden: ein Test für „Wert von Hand löschen“ **mit** Hinweistext „Dann gilt wieder: ab 3“ und für „Fehler lässt Blatt offen“ in `serie.test.mjs` im Auszug der Diff (ich habe nur die Teststartzeilen und Behauptungen gesehen, nicht jede). | Prüfen, ob beide Fälle in `serie.test.mjs` stehen; sonst nachtragen. |

Keine Tests, die nichts prüfen, gefunden: Die neuen Python-Tests vergleichen konkrete Werte (Dateiinhalt, Ereignisse, Treffermengen), die Regel-Tabelle enthält die Randfälle (0, bool, 19, Text, Kommazahl).
