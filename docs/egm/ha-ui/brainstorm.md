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

## Antworten Runde 5 (12.11.): Analyse-Seite

Heute gibt es keine eigene Analyse; HA zeichnet nur die Sensor-Verläufe auf (Akku, Lader, Netz, Zustand), dazu die
letzten 20 Box-Meldungen. Was gehört wurde, meldet die Box nicht gesondert.

| Frage | Antwort |
|---|---|
| Inhalt | **Hörzeit pro Tag und Kind**, **Lieblings-Hörspiele** (je Box und gesamt), **Tageszeiten**, **Technik und Akku** (Akku-Verlauf, Ladezeiten, Laufzeit, Syncs, Fehler) |
| Ort | **Eigener Reiter in der Tobi-Box-Seite** für alle; der Technik-Teil unter „Für Tobias“ |
| Aufbewahrung | **Unbegrenzt** |

## Antworten Runde 6 (12.11., zum Goldfisch-Review `review_goldfisch.md`)

| Frage | Antwort |
|---|---|
| Wer darf die Alltags-Funktionen? | **Alle HA-Benutzer** (bewusst; Wandtablets und Gäste mit Konto inklusive). Ausgleich (Projektleitung, U2): `zuordnung/remove` nur mit `erwartet_ziel`, `zuordnung/set` nur für gemeldete bzw. bekannte Kennungen, Mengen begrenzt. |
| Darf Verena in den Papierkorb legen? | **Ja.** Endgültig löschen (Papierkorb leeren, Eingang entfernen) bleibt bei Tobias. |
| Name beim Zuordnen | **Gleich mit abfragen, überspringbar.** |
| Cover selbst ersetzen | **Ja, mit Foto vom Handy.** |

Außerdem sofort behoben (nicht Teil des Umbaus): Sicherheitsbefund U1, alle HA-Aktionen nur für Administratoren (Commit d41e319).

## Runde 7 (12.11., Rückmeldung zu Prototyp v2)

Tobias zum Reiter „Bibliothek“ (Screenshot Handy, dunkel): „unglaublich unübersichtlich“. Die Bibliothek soll wie eine
Musik- oder Hörbuch-App aufgebaut sein, und man soll dort **reinhören** können, um zu erkennen, was etwas ist.

| Frage | Antwort |
|---|---|
| Vorbild | **Audible / Hörbuch-App** |
| Wo reinhören? | **Nur am Handy/PC** (Browser bzw. HA-App), nicht auf der Box |
| Wie viel Player? | **Mit Weiterhören:** merkt sich je Folge, wo man war |

Festlegung der Projektleitung: Reinhören geht mit HA allein (Dateien liegen unter dem Medien-Pfad der Integration,
Ausgabe über eine Ansicht der Integration mit signiertem, kurz gültigem Pfad wie bei Kamerabildern). Music Assistant
wird nicht gebraucht. Die Hörstelle wird **je HA-Benutzer in HA** gespeichert (gleich auf Handy und PC), nicht nur im Browser.
