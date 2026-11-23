# Altersfilter: Resolve (EGM Schritt 4)

## Runde 1 (23.11.): Goldfisch-Review `review_goldfisch.md` (19 Befunde: 3 hoch, 10 mittel, 6 niedrig)

### Entscheidungen von Tobias

| Befund | Frage | Entscheidung |
|---|---|---|
| AF-6 | Überraschungs-Serie | **(Tobias)** „Wie jeder Eintrag“: Alter setzen darf, wer bearbeiten darf (alltag); ohne Alter fällt sie bei einer Zahl aus der Liste |
| AF-8 | Zusammenführen, nur die Quelle hat ein Alter von Hand | **(Tobias)** „Ziel übernimmt es“: Hat das Ziel kein Alter von Hand, bekommt es das der Quelle; hat es eins, bleibt seins. `folge/verschieben` (einzelne Folgen) nimmt das Alter von Hand nicht mit |
| AF-12 | Anzeige oben auf der Serien-Seite | **(Tobias)** „Nur das Alter, Quelle egal“: Oben steht „ab 3“, das Eintrags-Alter, ohne Angabe der Quelle. Folge: `alter_quelle` entfällt (zugleich AF-13 a) |
| AF-18 | Zahlen | **(Tobias)** „0 bis 12, überall gleich“: im Filter und beim Festlegen; 0 heißt „für alle“. Werte 13 bis 18 aus dem Shop werden angezeigt und gefiltert, sind aber nicht wählbar |

### Entscheidungen der Projektleitung (technisch, eingearbeitet in Rev. 2)

| Befund | Entscheidung |
|---|---|
| AF-1 | Begründung berichtigt: Die Online-Suche sendet `serien_geaendert`; je Anfrage rechnen, weil der Index (`bibliothek.py`, `zeilen()`) Zeilen nur bei neuem `SerieInfo` neu baut. Eintrags-Alter nie in `_SerieZeile`; Wörterbuch `serie_id → Alter` in `Medien.serien_liste`, übergeben an `Bibliothek.serien` wie `online_vorschlag` |
| AF-2 | Verweis für `stand` auf Vertrag W (Kurzform, 14.2) und `media.py` (`STAND_FELDER`) |
| AF-3 | Feld als echtes Feld der Klasse `Serie` (in `bekannt`, Prüfung in `serie_aus_json`, `to_json` nur wenn gesetzt). Ungültige Werte gelten als fehlend und verschwinden beim nächsten Schreiben. Roundtrip-Test mit Fremdfeldern und ungültigem Wert |
| AF-4 | Shop-Werte nur von Folgen in `serie.folgen`, nur int 0 bis 18, kein bool |
| AF-5 | Feld in `serie.json` heißt **`alter_hand`**; gleicher Name in Befehl 66 und in der Kurzform. `alter_hand` steht in **jeder** Kurzform, wenn gesetzt |
| AF-9 | Anzeige hängt am Feld `alter_ab` (Ausgabefeld, keine Fähigkeit nötig, 14.1); Abschnitt im Blatt und Menüpunkt hängen an der Fähigkeit `alter`. Fehler von 66 vollständig |
| AF-10 | Nach eigenem Speichern oder `serien_geaendert` lädt die Bibliothek ab Anfang neu (wie bisher). Test mit „ohne“ und mehr als 60 Treffern |
| AF-11 | Keine Pfeiltasten (gibt es bei den anderen Wahlen auch nicht): Tab und Eingabe, sichtbarer Fokus, `role="radio"`, `aria-checked`, `aria-label` „4 Jahre“ |
| AF-13 | a) `alter_quelle` entfällt (AF-12). b) eine gemeinsame Knopfreihe 0 bis 12 für Filter und Blatt. c) Texte zusammengezogen |
| AF-14 | Testliste in AF1/AF2 ergänzt (Schema, Rechte, Fähigkeit, Suche, Papierkorb, Einzeltitel, Überraschung, Box liest das Feld, Seite) |
| AF-15 | Abnahme mit prüfbaren Zahlen (Alle = mit Alter + ohne), Hand größer als Shop, zwei verschiedene Folgenwerte, Blättern bis zum Ende, Tastatur, schmale Ansicht. Testeintrag vorher mit Tobias festlegen; Löschen des Werts am Ende ist Pflicht |
| AF-7 | Einzeltitel (`einzeln=true`): Das Alter steht nur einmal, oben; die Angabe „ab X“ an der einen Folge entfällt dort. Einträge mit mehreren Folgen: oben das Eintrags-Alter, an den Folgen wie bisher |
| AF-16, AF-17 | Anlegen, Einsortieren, Umbenennen, Art ändern erhalten das Feld und setzen es nicht; Konfig-Export und -Import berühren es nicht |
| AF-19 | Löschen (`null`) mit demselben Recht alltag, letzter gewinnt: bewusste Folge aus A5 |

## Runde 2 (23.11.): Annahme und Vertragsfreigabe

- **Design angenommen (Tobias, 23.11.):** `docs/designs/altersfilter.md` (Rev. 2).
- **AF0 freigegeben (Tobias, 23.11., „Ja, freigeben“):** Entwurf `vertrag_entwurf/` in Vertrag W und `data-model.md` übernommen.

## Runde 3 (23.11.): Abnahme AF3

- Eingespielt 69b5fb2 (Neustart mit Ja), Abnahme Schritt für Schritt im Chat, Testeintrag ADAC. Ergebnisse in `docs/plan/stueckliste-und-psp.md` (Zeile „AF3 Altersfilter abgenommen“).
- Schritt 12 (Konto ohne Recht alltag) ausgelassen: es gibt kein solches Konto (Tobias); die Tests decken es ab.
- **B1 Handy, Blatt scrollt nicht** (Schritt 11): Das Blatt „Sortieren und Filter“ ist mit der Knopfreihe länger als der Bildschirm und ließ sich nicht scrollen. Ursache: `touch-action: pan-x pinch-zoom` an jedem `dialog.blatt`; der Prototyp setzt es nur bei Klasse `fix` (Inhalt passt). **(PL)** Wie im Prototyp behoben (93f0c02); betrifft alle Blätter. Am iPhone geprüft (Tobias): scrollt, Wegwischen am Griff geht.
- Wert von Hand bei ADAC am Ende gelöscht (Pflicht aus AF-15): „Ohne Altersangabe“ wieder 256.
