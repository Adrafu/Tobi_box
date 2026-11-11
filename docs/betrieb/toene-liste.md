# Töne der Box: Liste für eigene Aufnahmen

Stand 10.11. · Entscheidung von Tobias (10.11.): Die gesprochenen Töne bleiben für Tests („Debug“) so, wie sie sind.
**Für den Echtbetrieb ersetzt Tobias alle Töne durch eigene MP3-Dateien.** Diese Liste trägt er vor dem Abschluss
aus; dann bauen wir sie ein.

## So füllst du die Liste

- Je Zeile eine eigene Datei, Name wie in der ersten Spalte, aber mit `.mp3` (z. B. `start.mp3`).
- **Höchstens 10 Sekunden** (längere Töne bricht die Box ab, Entscheidung L). Kurz ist besser, besonders bei `hinweis`.
- Lautstärke ist egal: Beim Einbauen gleichen wir alle Dateien auf dieselbe Lautheit an (−18 LUFS, Entscheidung J).
- Keine fremden Inhalte (Musik, Hörspiel-Ausschnitte), die Dateien kommen ins öffentliche Repo. Eigene Aufnahmen
  oder freie Klänge sind in Ordnung. Wenn eine Datei **nicht** ins Repo soll, sag es: Dann legen wir sie nur lokal auf
  die Boxen.
- Spalte „Deine Datei“: Dateiname oder „bleibt“ (dann bleibt der heutige Ton).

## Töne für die Kinder

| Datei | Wann sie spielt | Heute (Test-Fassung) | Leise-Zeiten | Deine Datei |
|---|---|---|---|---|
| `start` | Beim Hochfahren, sobald die Box bereit ist (früher Start-Ton) | „Tobi Box ist bereit.“ | „leiser“: leise · „stumm“: keiner | |
| `unbekannt` | Ein unbekannter Tobie liegt auf, danach spielt die Überraschung | „Diesen Tobie kenne ich noch nicht. Hier ist eine Überraschung.“ | „leiser“: leise · „stumm“: Hinweiston | |
| `gute_nacht` | Gute-Nacht-Karte aufgelegt (Entscheidung R) | „Gute Nacht! Ich spiele noch ein bisschen.“ | „leiser“: leise · „stumm“: keiner | |
| `lader` | Box wird angedockt, während sie läuft und nichts spielt | „Strom ist da.“ | in beiden Fenstern keiner | |
| `akku_leer` | Akku fast leer, kurz bevor die Box ausgeht | „Mein Akku ist fast leer. Ich gehe gleich aus.“ | „leiser“: leise · „stumm“: Hinweiston | |
| `akku_warnung` | Akku bei 10 %, ohne Strom, einmal; das Hörspiel läuft danach weiter (Entscheidung Z, 11.11.) | „Mein Akku wird leer. Bitte bald laden.“ | „leiser“: leise · „stumm“: Hinweiston | |
| `fehler` | Etwas klappt nicht (z. B. Datei fehlt) | „Da ist etwas schiefgegangen.“ | „leiser“: leise · „stumm“: Hinweiston | |
| `hinweis` | Taste ohne Tobie (Entscheidung Q), Tobie unter „stumm“, „Vor“ am Ende | kurzer, leiser Zweiklang (Entscheidung T) | immer leise | |

## Töne für dich (Lernmodus und Prüfkarte)

| Datei | Wann sie spielt | Heute (Test-Fassung) | Deine Datei |
|---|---|---|---|
| `lernen_beginn` | Lernmodus aus HA gestartet | „Lernmodus an. Leg den neuen Tobie auf.“ | |
| `lernen_ende` | Lernmodus beendet | „Lernmodus beendet.“ | |
| `pruef_ok` / `pruef_fehler` | Prüfkarte: Gesamtergebnis | „In Ordnung.“ / „Fehler.“ | |
| `pruef_leser_ok` / `_fehler` / `_simulation` | Prüfkarte: Leser | „Leser in Ordnung.“ / „Leser: Fehler.“ / „Leser: Simulation.“ | |
| `pruef_medien_ok` / `_fehler` | Prüfkarte: Medien | „Medien in Ordnung.“ / „Medien: Fehler.“ | |
| `pruef_netz_ok` / `_fehler` | Prüfkarte: Netz | „Netz in Ordnung.“ / „Netz: Fehler.“ | |
| `pruef_speicher_ok` / `_fehler` | Prüfkarte: Speicher | „Speicher in Ordnung.“ / „Speicher: Fehler.“ | |

Die Prüf-Töne hört nur du. Für sie ist „bleibt“ eine gute Wahl.

## Was beim Einbauen noch zu tun ist (Projektleitung)

- Ein Weg für eigene Töne: eigener Ordner (z. B. `box/sounds/eigene/`), MP3 nach WAV wandeln, auf −18 LUFS angleichen,
  Eintrag in `box/lautheit.json`; fehlt eine Datei, gilt der heutige Ton.
- Umschalter Test-Fassung / Echtbetrieb in `tobibox.toml`.
