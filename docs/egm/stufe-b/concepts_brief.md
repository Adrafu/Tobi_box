# Stufe B „Gehört“: Concepts Brief (EGM Schritt 1)

Stand 16.11. · Anlass: Stufe A der HA-Oberfläche ist gebaut und abgenommen (A-1, A-2, A-3, zuletzt A16-3 am 16.11.).
Tobias: „Gleich B, gibt eh noch keine echten Boxen.“

## 1. Problem

Die Familie sieht heute nicht, **was gehört wird**: welches Kind (welche Box) welches Hörspiel wie oft und wie lange
hört, was zuletzt lief, was ganz gehört wurde. Die Box meldet nur ihren aktuellen Zustand (`status`), kein „gespielt“.
Reinhören am Handy oder Computer hinterlässt nur die private Hörstelle zum Weiterhören. Favoriten gibt es nicht.

Der Entwurf aus der HA-Oberfläche (`docs/designs/ha-oberflaeche.md` Abschnitte 5.10, 12, 15.2) beschreibt Stufe B
schon recht genau, stammt aber aus den Runden 3 bis 17 (12./13.11.), also **vor** dem Bau von Stufe A. Er muss an den
heutigen Code und die heutigen Verträge angepasst und als eigenes Design geprüft werden.

## 2. Entscheidungen aus dem Brainstorm (Tobias, 16.11.)

| Nr. | Frage | Antwort |
|---|---|---|
| B-Q1 | Zuschnitt | **Alles jetzt**: B komplett entwerfen und bauen, auch die Box-Seite (Ereignis „gespielt“, Puffer, Quittung) in der Box-Software. Die Box-Teile werden mit Tests und **simulierten Boxen** geprüft; die Abnahme mit echter Hardware folgt, wenn die Boxen gebaut sind |
| B-Q2 | Was ist wichtig? | **Alles vier gleich:** welches Kind (Box) was hört (Rangliste, fertig gehört), Favoriten (Stern), Zuletzt/Meist gehört (Reihen und Sortierungen), Hörzeit-Diagramme |

## 3. Was schon entschieden ist (aus der HA-Oberfläche, gilt weiter, wenn der Entwurf nichts anderes sagt)

- „Gehört“ ist eine Unterseite `#gehoert` hinter der Zeile „Wer hat was gehört?“ in „Geräte“ (R17-7), mit **einer**
  Auswahl „Wer?“ (Alle · je Box · je HA-Benutzer, der reingehört hat), Zeitraum Woche · Monat · Jahr · Alles (5.10).
- Zählregel 12.2.1: Wiedergabe = Sitzung ab 10 s, Sitzungen derselben Quelle und Folge mit höchstens 5 Minuten Lücke
  zählen als eine; „fertig“ = Ende der Folge; Hörzeit = Summe ohne Pausen.
- Reinhören zählt unter dem HA-Benutzer, nie bei einer Box (12.5); alle HA-Benutzer sehen alle Hördaten (Frage 23);
  die Hörstelle bleibt privat (Frage 16); löschen nur Administratoren in „Technik“ (Frage 27).
- Die Kennung des Tobies wird nie gespeichert (Frage 9). Kind = Box.
- Speicher: eigene SQLite-Datei in HA für Hör- und Technik-Ereignisse, Langzeitstatistik von HA für den Akku,
  Favoriten in `.storage` (12.3). Daten unbegrenzt, etwa 10 MB im Jahr.
- Reihen „Zuletzt auf den Boxen gehört“ und „Favoriten“ stehen auf Start (5.1, X27); Stern an jedem Eintrag und jeder
  Folge, gilt für die ganze Familie.

## 4. Grenzen

- Verträge (`docs/protocol/mqtt-v1.md`, `docs/protocol/ha-websocket-v1.md`, `docs/data-model.md`) ändern sich nur nach
  Freigabe durch Tobias (Stufe 0), wie bei A0.
- Rollout-Reihenfolge: erst die Integration, dann die Box; eine Box ohne „gespielt“ und eine Integration ohne Stufe B
  müssen weiter zusammen funktionieren.
- Box: Schreibbudget der SD-Karte (`data-model.md` 1.7) gilt; die Box ist oft offline (mobil).
- Keine echten Namen im Repo; Namen der Personen kommen aus Home Assistant.
- Ohne echte Boxen: Box-Seite mit Tests und Simulation (MQTT-Nachrichten wie bei A-1b über `mqtt.publish` oder
  Box-Software am Mac), Abnahme der Box-Teile später.

## 5. Offene Punkte für den Entwurf

- Abgleich mit dem heutigen Code: Wie ruft die Seite `hoerstelle/set` wirklich auf (Grundlage der Reinhör-Sitzungen)?
  Wo in der Box-Software entsteht eine Sitzung? Wie sendet die Box offline Gepuffertes?
- Frage 28 ist entschieden (Tobias): „Alle“ ist die Summe aus Boxen und Reinhören. Prüfen, ob „nur die Boxen“
  (die Kinder zusammen) zusätzlich gebraucht wird.
- Zuschnitt der Pakete und Abnahmen (B1 bis B6 aus 15.2 neu schneiden).

## 6. Reste aus Stufe A (Tobias, 16.11.: „und was aus A halt noch über ist“)

**In die Vertragsrevision von B** (eine Freigabe für alles):
- `hello.grenzen.hoerkopie_schlange` (A-3 Teil 1, bisher nur im Code).
- AM24 (Auslegung der Prüfungen von `einsortierung/neu`) und AM25 („Anders einsortieren“ ohne Ruhezeit) in 2.4.
- `serie/get`: Hörstelle je Folge mit `track` (Fortschritt einer Ordner-Folge ist sonst ungenau).
- `serien/list` ohne `limit` liefert alles (Vertragssatz „höchstens 200“ berichtigen).
- `einsortierung/bestaetigen` setzt `pruefen` im Eingangsprotokoll nicht zurück; `eingang/list` nennt keine
  Dateinamen und Zahlen einer Gruppe (Lücke aus A-1c).

**Als eigene kleine Pakete neben dem Entwurf** (Sonnet, 16.11. gestartet): AC6 (Papierkorb: Zurückholen ohne halben
Eintrag), AC8 (Namensvorschlag ohne doppelte Endung), AC10 (Punkt am Technik-Symbol dezenter), AC11 (Eingangs-Karte
ohne „1 Datei“), Vorladen nur bei Absicht statt beim Scrollen, kein „ab 0:00“, eigene Prüfung statt pauschaler Duldung
von `ERR_ABORTED` im Browser-Prüfskript.

**Getrennt:** Online-Suche (eigenes EGM `docs/egm/online-suche/`, nur Concepts Brief).
