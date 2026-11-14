# Online-Suche für Cover und Angaben („wie bei Plex“): Concepts Brief (EGM Schritt 1)

Stand 14.11. · Anlass: Tobias nach dem ersten großen Befüllen der Bibliothek (282 Einträge, davon 260 „bitte ansehen“,
234 Arten geraten): „Bei allen, die ich jetzt hochgeladen habe, gefallen mir die Bilder nicht, und die Infos sind auch
nicht perfekt.“

## 1. Problem

Die Bibliothek nimmt Namen, Art und Cover nur aus den Dateien (Tags, Ordnernamen, eingebettete Bilder). Bei gekauften
oder gesammelten Kinderhörspielen sind diese Angaben oft schlecht: Serien heißen nach Sprechern oder Autoren,
Folgentitel wiederholen den Seriennamen oder tragen Zusätze („(Das Original-Hörspiel zur TV-Serie)“), Nummern fehlen,
Arten sind geraten, Cover fehlen oder sind unscharf. Von Hand alles zu korrigieren ist bei Hunderten Einträgen zu viel.

## 2. Entscheidungen aus dem Brainstorm (Tobias, 14.11.)

| Nr. | Frage | Antwort |
|---|---|---|
| O1 | Was liefert die Suche? | **Cover, Namen (Serie, Folgentitel, Nummer) und zusätzlich Beschreibung bzw. Altersangabe** zum Anzeigen (1c) |
| O2 | Wie arbeitet sie? | **Beides** (2c): von Hand je Eintrag („⋯“ → „Online suchen“, Treffer mit Cover, einen antippen) **und** automatisch beim Einsortieren, mit „bitte ansehen“, wenn der Treffer unsicher ist |
| O3 | Quelle | **iTunes-Suche von Apple** (kostenlos, ohne Konto). In Kauf genommen: HA schickt Titel der Hörspiele an Apple |
| O4 | Cover auf die Boxen? | **Nein**, bleibt so (U8): Cover und Beschreibung sind nur für die HA-Seite |

## 3. Was schon feststeht (Messung der Projektleitung, 14.11.)

- Die iTunes-Suche (`https://itunes.apple.com/search?country=de&media=all&term=…`) findet deutsche Kinderhörspiele gut:
  z. B. „Benjamin Blümchen, Folge 109: Benjamin als Baggerfahrer“, „Gigantosaurus – Folge 1: Mazus Mutprobe“, „Zippel,
  das wirklich wahre Schlossgespenst“, mit Künstler, Genre und Cover-URL (bis ca. 1000 × 1000 px durch Ändern der Größe
  in der URL). MusicBrainz fand im selben Test weniger.
- Grenzen: Apple drosselt bei ca. 20 Anfragen je Minute; es gibt keine Garantie und keinen Vertrag. Treffer sind
  Alben/Hörbücher/Titel, keine „Serien“ – die Serie muss aus Künstler und Titel abgeleitet werden.
- Eine Durchsicht der vorhandenen 282 Einträge mit dieser Quelle läuft als Vorschlagsliste (Projektleitung), bevor die
  Funktion gebaut wird; sie zeigt, wie gut das Ableiten von Serie, Titel und Nummer klappt.

## 4. Grenzen

- Nur HA-Seite und Integration; Box, `mqtt-v1.md` und Sync bleiben unverändert (Cover und Beschreibung gehen nicht auf
  die Boxen).
- Eigene Eingaben gehen vor: Was jemand von Hand umbenannt, als Art gesetzt oder als Cover hochgeladen hat, überschreibt
  die Automatik nie.
- Vertragsänderungen (neue Befehle, neue Felder wie Beschreibung und Alter) nur nach Freigabe durch Tobias (Stufe 0).

## 5. Offene Fragen für den Entwurf

1. **Nachholen:** Läuft die Automatik auch einmal über die vorhandene Bibliothek (wie die Cover-Suche aus den Tags), oder
   nur bei neuen Einträgen? Wenn ja: alles auf einmal mit Vorschlagsliste oder still mit „bitte ansehen“?
2. **Wie sicher ist „sicher“?** Ab wann übernimmt die Automatik ohne Nachfrage (z. B. Titel und Künstler passen genau)?
3. **Rechte:** Darf jeder Benutzer „Online suchen“ (Alltag) oder nur Administratoren?
4. **Was wird gespeichert:** Beschreibung und Alter je Serie oder je Folge? Wo angezeigt (Serienseite, Kachel)?
5. **Ausfall:** Was zeigt die Seite, wenn Apple nicht antwortet oder drosselt?
