# HA-Oberfläche einfacher und schöner: Brainstorm (EGM Schritt 1, läuft)

Anlass (12.11.): Alle Funktionen der Integration sind gut und funktionieren. Tobias kann sie bedienen, Verena
(keine Technikerin) hätte keine Chance. Ziel: **nur UI und Bedienbarkeit**, keine neuen Funktionen. Vorgehen wie
immer: Konzept, Entwurf, Goldfisch, Resolve, dann einmal bauen. Bestandsaufnahme: `ist.md` (in Arbeit).

## Antworten von Tobias (12.11.)

| Frage | Antwort |
|---|---|
| Was soll Verena selbst erledigen? | **Tobie einem Hörspiel zuordnen**, **neues Hörspiel hochladen**, **Gute Nacht und Leise-Zeiten** einstellen. (Nicht ausgewählt: „nur Status sehen“ als einzige Aufgabe.) |
| Gerät | **Gemischt:** Handy für schnell, Computer für Pflege. |
| Einfach gegen Technik | **Eine einfache Seite und ein eigener Bereich „Für Tobias“** für Technisches (Revision, Export, Papierkorb, Liste neu ausrollen …). |
| Stil | **HA-Look, aber freundlich:** passt zu Home Assistant (Karten, Hell/Dunkel), mit Bildern/Covern der Serien, großen Knöpfen, wenig Text. |

## Antworten Runde 2 (12.11.)

| Frage | Antwort |
|---|---|
| Zuordnen | **Beides anbieten:** (a) Tobie auflegen → oben erscheint „Neuer Tobie – was soll er spielen?“ mit Cover-Kacheln; (b) erst Hörspiel wählen, dann „Jetzt Tobie auflegen“ (Lernmodus). |
| Woher kommen Hörspiele | **Alle drei:** Dateien auf dem Handy, Ordner am Computer, direkt aufs NAS (Eingang). |
| Bilder | **Automatisch aus den MP3-Tags, sonst Platzhalter** (farbig mit Anfangsbuchstabe); eigenes Foto hochladbar. Hinweis Projektleitung: Das Cover-Auslesen ist die einzige kleine neue Funktion; sie dient nur der Bedienbarkeit. |
| Zwei Boxen | **Eine gemeinsame Bibliothek**, Boxen nur als Status-Karten (mit Namen der Kinder). |

## Antworten Runde 3 (12.11.)

| Frage | Antwort |
|---|---|
| Rechte | Verena ist keine Administratorin: **Alltagsseite für alle**, „Für Tobias“ nur für Administratoren. |
| Box-Namen | **Tobias trägt Anzeigenamen in den Einstellungen der Integration ein**; im Repo stehen keine Namen. |

## Antworten Runde 4 (12.11., nach dem ersten Prototyp)

Tobias: „Schaut schon mal nicht schlecht aus.“ Er braucht aber mehr Möglichkeiten in der Verwaltung; bei etwa
200 Hörbüchern und 300 Liedern wird es sonst unübersichtlich.

| Frage | Antwort |
|---|---|
| Arten von Inhalten | **Hörspiel-Serien, Hörbücher, Lieder/Musik, einzelne Geschichten** |
| „Folgen und Serien trennen“ | **Beides:** Bereiche nach Art **und** neben den Serien eine durchsuchbare Ansicht „Alle Folgen“ über alle Serien |
| Lieder auf einen Tobie | **Alben, eigene Playlists und sogar einzelne Lieder** |
| Finden | **Suche über alles** (auch Folgen- und Liedtitel), **Filter**, **Sortieren**, **Zuletzt gehört / Favoriten** |

**Einordnung der Projektleitung:** Damit wächst das Thema über „nur Oberfläche“ hinaus. Schon heute möglich: ein
Tobie auf eine einzelne Folge (also auch ein einzelnes Lied eines Albums). Neu wären: eine **Art** je Serie
(Hörspiel, Hörbuch, Musik, Geschichte; aus den Tags vorgeschlagen, korrigierbar), **eigene Playlists** (neues
Ziel für Tobies, betrifft Datenmodell und Box) und **Zuletzt gehört / meist gehört** (Box meldet, was gespielt
wurde). Vorschlag: in Stufen bauen, siehe `concepts_brief.md` Abschnitt 6.
