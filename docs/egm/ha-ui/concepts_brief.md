# HA-Oberfläche einfacher und schöner: Concepts Brief (EGM Schritt 1)

Stand 12.11. · Grundlage: `brainstorm.md` (Antworten von Tobias), `ist.md` (Bestandsaufnahme mit Screenshots in `screens/`).

## 1. Problem

Die Seite „Tobi Box“ in Home Assistant kann alles, was gebraucht wird, und es funktioniert. Sie ist aber für
Tobias gebaut: fünf Reiter mit Fachbegriffen (Revision, Listen-ID, UID, Eingang, Tags), Rohwerte statt Sätze,
technische Fehlertexte, kleine Knöpfe auf dem Handy, und sie ist nur für Administratoren sichtbar. Verena, die
keine Technikerin ist, kann damit die drei Alltagsaufgaben nicht erledigen (`ist.md`, Abschnitt 6, zehn Hürden).

## 2. Ziel und Grenzen

- **Nur Oberfläche und Bedienbarkeit.** Alle Funktionen bleiben, wie sie sind. Einzige kleine Ergänzung: Cover aus
  den MP3-Tags (dient nur der Bedienbarkeit). Vertrag W (`docs/protocol/ha-websocket-v1.md`) ändert sich nur dort,
  wo die Oberfläche Daten braucht, die es noch nicht gibt (Cover, Status „spielt gerade“, Rechte).
- **Verena erledigt selbst:** Tobie einem Hörspiel zuordnen, neues Hörspiel hochladen, Gute Nacht und Leise-Zeiten einstellen.
- **Geräte:** Handy (Hochformat, Daumen) **und** Computer. Beides gleich gut.
- **Stil:** Home-Assistant-Look (Karten, Hell/Dunkel, HA-Farben), aber freundlich: Cover-Kacheln, große Knöpfe, wenig Text, Alltagssprache.
- **Rechte:** Die Alltagsseite sehen **alle** HA-Benutzer. Der Bereich **„Für Tobias“** ist nur für Administratoren.
- **Zwei Boxen, eine Bibliothek:** Zuordnungen gelten für beide Boxen. Die Boxen erscheinen nur als Status-Karten mit
  Anzeigenamen, die Tobias in den Einstellungen der Integration einträgt (keine Kindernamen im Repo).

## 3. Leitlinien

1. **Aufgaben statt Datenbank:** Die Startseite zeigt, was man tun will („Neuer Tobie“, „Hörspiel hinzufügen“, „Abends“),
   nicht Tabellen.
2. **Alltagssprache:** keine Kennungen, Revisionen, Codes. Jeder Fehler sagt, **was jetzt zu tun ist**.
3. **Ein Weg pro Aufgabe, höchstens drei Taps** für die häufigen Aufgaben.
4. **Gefährliches weg vom Daumen:** Löschen nur mit Bestätigung und nie direkt neben häufigen Knöpfen.
5. **Bilder vor Text:** Serien als Cover-Kacheln; Platzhalter farbig mit Anfangsbuchstabe.
6. **Status in einem Satz:** „Lisas Box spielt Lange Serie, Akku 80 %, lädt.“ statt „Netz: home, Sync: idle“.
7. **Alles Technische im Bereich „Für Tobias“**, dort darf es so ausführlich bleiben wie heute.

## 4. Bausteine der neuen Seite (Vorschlag, wird im Entwurf ausgearbeitet)

| Bereich | Inhalt |
|---|---|
| Kopf | Zwei Status-Karten der Boxen (Name, ein Satz Status, Akku, Laden, online; Cover des Gespielten) |
| „Neuer Tobie“ | Erscheint oben, sobald eine Box einen unbekannten Tobie meldet: „Neuer Tobie auf Lisas Box – was soll er spielen?“ → Cover-Kacheln → fertig. |
| Hörspiele | Cover-Kacheln aller Serien; Tippen öffnet die Serie (Folgen, „Tobie dafür anlernen“ = Lernmodus, Name ändern). |
| „Hörspiel hinzufügen“ | Großer Knopf: Dateien vom Handy oder Ordner vom Computer; danach ein klarer Fortschritt „wird hochgeladen → wird einsortiert → fertig“ oder „bitte kurz ansehen“ mit verständlichem Grund. Neues vom NAS erscheint dort ebenso. |
| Abends | Gute Nacht (Timer, Ausblenden) und Leise-Zeiten als einfache Zeitleiste/Wochenplan mit „leiser“/„stumm“. |
| Tobies | Liste der bekannten Tobies mit Namen und Cover des Ziels; umbenennen, anderes Hörspiel, entfernen. |
| Für Tobias (nur Admin) | Alles Heutige: Eingang im Detail, Papierkorb, Liste/Revision/Export, Upload-Grenze, Lesezeichen-Tage, Box-Details, Sync, Meldungen mit Codes. |

## 5. Offene Fragen für den Entwurf

- Navigation auf dem Handy: Reiter unten oder eine lange Startseite mit Abschnitten?
- Wie viel Status gehört auf die Startseite (nur Satz, oder auch Lautstärke/Leise-Zeit aktiv)?
- Cover: Wie werden sie zwischengespeichert, wie groß, und gilt ein Cover je Serie oder je Folge?
- Upload vom Handy: Grenzen (500 MiB), Abbruch, mehrere Dateien.
- Barrierefreiheit (Kontrast, Schriftgröße, Bedienung ohne Ziehen).

## 6. Erweiterung nach Runde 4: große Bibliothek (12.11.)

Tobias rechnet mit etwa 200 Hörbüchern und 300 Liedern. Daraus folgt eine Gliederung in Stufen:

| Stufe | Inhalt | Art der Änderung |
|---|---|---|
| **A** | Bereiche nach **Art** (Hörspiele, Hörbücher, Musik, Geschichten), je Serie eine Art (aus den Tags vorgeschlagen, korrigierbar); Ansicht **„Alle Folgen“** über alle Serien; **Suche über alles** (auch Folgen- und Liedtitel); **Filter** (Art, ohne Tobie, neu, bitte ansehen); **Sortieren** (A–Z, zuletzt hinzugefügt); ein Tobie auf eine einzelne Folge oder ein einzelnes Lied wird sichtbar einfach. | Oberfläche plus ein kleines Feld `art` in `serie.json` (Vertrag W, `data-model.md`) |
| **B** | **Zuletzt gehört, meist gehört, Favoriten** (Stern je Serie). | Box meldet über MQTT, was sie gespielt hat (`mqtt-v1.md`), HA zählt; Favoriten nur in HA |
| **C** | **Eigene Playlists** aus beliebigen Folgen und Liedern, als Ziel für Tobies. | Neues Ziel im Datenmodell und auf der Box (Verträge `data-model.md`, `core-interface.md`, Box-Code) |

Stufe A gehört in diesen Entwurf. B und C werden im Entwurf mitgedacht (Platz in der Oberfläche), aber erst nach
Freigabe gebaut.
