# B0: Vertragsänderungen für Stufe B „Gehört“ (zur Freigabe, 16.11.)

Entwurf in `b0_entwurf/` (je Vertrag die geänderte Datei und ein Diff gegen den heutigen Stand). Die echten Verträge
`docs/protocol/mqtt-v1.md`, `docs/protocol/ha-websocket-v1.md` und `docs/data-model.md` sind unverändert, bis du
freigibst. Version bleibt überall 1. Grundlage: `design_draft.md` Rev. 3.1 und `resolve.md` (drei Review-Runden).

## 1. Was sich ändert

**Box → HA (mqtt-v1)**
- Neues Ereignis **`gespielt`**: die Box meldet beendete Sitzungen (Serie, Folge, Hörzeit, Beginn, Ende, warum es
  endete). Keine Kennung des Tobies.
- Neuer Befehl **`gehoert_quittung`**: HA bestätigt, welche Sitzungen es gespeichert hat; erst dann löscht die Box sie.
- **Handshake** über `status.gehoert_wartet`: die Box sendet erst, wenn HA einmal geantwortet hat. Eine alte HA bekommt
  nie Hördaten.
- `status` bekommt `box_faehig`, `gehoert_wartet`, `gehoert_verworfen`.
- Zusage neu: Empfänger ignorieren unbekannte Ereignisarten und Felder.
- Keine neue Berechtigung im Mosquitto nötig.

**Box-Daten (data-model)**
- Neue Datei **`gehoert.json`** auf der Box: Puffer für bis zu 500 Sitzungen, auch offline; die laufende Sitzung wird
  höchstens alle 2 Minuten mitgeschrieben (Verlust bei Stromausfall höchstens 2 Minuten). Nicht in der
  Rückfall-Sicherung des Updates.
- Schreibbudget der SD-Karte: eine Schreibung je Sitzungsende, höchstens 30 je Stunde beim Hören.
- In HA: SQLite-Datei `gehoert.sqlite` (Hördaten, Technik-Verlauf, Löschmarken) und Store `tobibox.favoriten`.

**HA-Seite (ha-websocket-v1)**
- 7 neue Befehle (Nr. 50 bis 56): Zusammenfassung für „Gehört“, Zuletzt gehört, Technik-Verlauf (Admin), Export als
  Tabelle (Admin), Löschen (Admin), Favorit setzen, Favoriten auflisten.
- Neue Fähigkeiten `gehoert` und `favoriten`; neue Sortierungen „Zuletzt gehört“, „Meist gehört“, Filter „Favoriten“,
  Felder `favorit`, `zuletzt_gehoert_am`, `akku_entitaet`.
- Neue Ereignis-Themen `gehoert` und `favoriten`; Fehlercodes `wer_ungueltig`, `zu_viele_favoriten`.
- Zählregel als eigener Abschnitt 15: Hörzeit (Inhaltszeit), „Mal“ (Pausen bis 30 Minuten), „fertig“ (Ende der Folge
  und 80 % gehört, auch über mehrere Tage), Zeiträume in der Zeitzone von HA.

**Reste aus Stufe A (mit dieser Revision)**
- Nachgetragen, schon gebaut: Zähler der Hörkopie-Warteschlange, AM24 und AM25 bei „Anders einsortieren“, Hörstelle
  mit Track bei Ordner-Folgen, `serien/list` ohne Grenze.
- Neu, noch zu bauen (mit B3/B4): „Das ist richtig“ setzt „bitte ansehen“ auch im Eingangsprotokoll zurück; die
  Eingangsliste nennt Dateinamen und Zahl einer Gruppe.

## 2. Nicht rückwärtskompatibel oder geänderte Zusagen

1. **Unbekannte Ereignisarten werden ignoriert** (neu zugesichert). Die heutige Integration legt sie noch ab; der
   Handshake sorgt dafür, dass sie nie `gespielt` bekommt.
2. **Befehl 41 `hoerstelle/set`:** neue optionale Felder `spieler`, `spielt`; „idempotent: ja“ wird „nein“ (eine
   Wiederholung zählt keine Hörzeit doppelt, die Hörstelle bleibt gleich); Grenze 30 → 60 Aufrufe je Minute.
3. **Fähigkeit `gehoert_reinhoeren` entfällt** (war nie ausgeliefert).
4. Text von `neu_einsortieren_nicht_moeglich` berichtigt („älter als 24 Stunden“ statt „jünger“).

## 3. Was danach kommt

B2a (Messung am iPhone mit gesperrtem Bildschirm, mit dir) → B1 Box ‖ B2 HA-Speicher → B3 Befehle → B4 Seite ‖ B5
Simulator → B6 Abnahme mit der Test-Box am Mac (dafür legst du dann im Mosquitto ein Konto `boxsim` an).
