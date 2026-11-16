# Stufe B „Gehört“: Design-Entwurf (EGM Schritt 2)

Stand 16.11., Rev. 1 · Grundlage: `concepts_brief.md` (dieser Ordner), Faktenbericht zum Code vom 16.11. (Abschnitt 1),
alter Entwurf in `docs/designs/ha-oberflaeche.md` Abschnitte 5.1, 5.10, 12 und 15.2.
Dieser Entwurf **ersetzt** Abschnitt 12 und 15.2 der HA-Oberfläche; 5.10 (Seite „Gehört“) gilt weiter, wo hier nichts
anderes steht. Verträge: `docs/protocol/mqtt-v1.md`, `docs/protocol/ha-websocket-v1.md`, `docs/data-model.md`.

## 0. Ziel in einem Satz

Die Familie sieht in Home Assistant, **welche Box (welches Kind) und welcher HA-Benutzer was wie oft und wie lange
gehört hat**, was zuletzt lief und was ganz gehört wurde, kann Einträge mit einem Stern merken und sieht als
Administrator den Verlauf von Akku und Laden; die Daten bleiben unbegrenzt und nur in HA.

## 1. Heutiger Stand (Faktenbericht 16.11., gekürzt)

| Bereich | Stand | Folge für B |
|---|---|---|
| Box → HA, `tobibox/<box>/event` (mqtt-v1 3.4) | nicht retained, QoS 1, Felder `v`, `id`, `ts`, `art`, `daten`; Arten `liste_abgelehnt`, `fehler`, `befehl_abgelehnt`. Neue `art` sind ohne Versionserhöhung erlaubt (8) | neue `art` **`gespielt`** auf demselben Thema: keine neue ACL im Mosquitto nötig (7) |
| Box: Senden ohne Verbindung | `sende_event` verwirft (`box/src/tobibox/ha.py`); nur `unknown.json` hat einen Puffer (`outbox.py`) | eigener Puffer `gehoert.jsonl` mit Nummer und Quittung |
| Box: Uhr | `zeit_ok` und `zeitquelle` (mqtt-v1 3.3), `Jetzt(wall, mono, …)` | Feld heißt `zeit_ok`, nicht `zeit_unsicher` |
| Box: Wiedergabe | reiner Kern `core.step()`, Teilautomat `session`; Pausegründe `abgehoben`, `folgenende`, `knopf`, `stumm`, `gute_nacht`, `leser_unbekannt`, `fehler`, `herunterfahren` (`events.py`); jede Änderung gibt `SitzungGeaendert` aus | Sitzung wird aus `SitzungGeaendert` abgeleitet (eigener Beobachter wie `status.py`) |
| Box: Schreibbudget (data-model 1.7) | `resume.json` alle 30 s während der Wiedergabe, höchstens 320 je Tag | `gehoert.jsonl`: 1 Schreibvorgang je Sitzungsende |
| HA: Ereignisse der Box | `mqtt.py` speichert **jede** `art` in `box_ereignisse` (höchstens 20 je Box) | `gespielt` geht **nicht** in `box_ereignisse`; Rollout erst Integration, dann Box |
| HA: Reinhören | Seite ruft `hoerstelle/set` höchstens alle 10 s und sofort bei Pause, Sprung, Wechsel, Ende, Ausblenden; HA speichert nur die letzte Stelle | Reinhör-Sitzungen leitet HA im Speicher aus diesen Aufrufen ab (5) |
| HA: Speicher | Stores `tobibox`, `tobibox.hoerstellen`, `tobibox.medieninfo`, `tobibox_eingang`; kein SQLite, kein Recorder-Gebrauch | neue SQLite-Datei, neuer Store `tobibox.favoriten` |
| HA: Akku | Sensor kommt per MQTT-Discovery von der Box (`device_class battery`, `state_class measurement`) | Langzeitstatistik von HA ist schon da; HA muss nichts sammeln |
| Seite | Start hat die Reihen „Zuletzt auf den Boxen gehört“ und „Favoriten / Empfehlungen“ schon angelegt (ohne Daten, unsichtbar); `#gehoert` leitet ohne Fähigkeit `gehoert` um; kein Stern; Sortierung `angehoert` = eigene Hörstellen | anschließen statt neu bauen |
| ha-websocket-v1 | Befehle 1 bis 49; Stufe B ausdrücklich nicht Teil des Vertrags (14.1, 14.11) | neue Befehle ab **50** |

## 2. Begriffe und Zählregel (gilt für Boxen und Reinhören gleich)

| Begriff | Regel |
|---|---|
| **Sitzung** | zusammenhängendes Hören **einer Folge** an **einer Quelle** (Box oder HA-Benutzer). Pausen bis **5 Minuten** gehören dazu; danach ist die Sitzung zu Ende |
| **Wiedergabe** („Mal gehört“) | eine Sitzung mit mindestens **10 s** gespielter Zeit. Beginnt eine Sitzung derselben Quelle und Folge höchstens 5 Minuten nach dem Ende der vorigen (z. B. nach einem Neustart der Box), zählt sie zur selben Wiedergabe (`wiedergabe`-Kennung, beim Aufnehmen vergeben) |
| **Hörzeit** | Summe der gespielten Sekunden ohne Pausen (`gespielt_s`) |
| **fertig** | die Sitzung endete am **Ende der Folge laut Gerät** (Box: ihr Ereignis „Folge zu Ende“; Seite: `fertig` in `hoerstelle/set`) |
| **Fertig je Hörspiel** | Anzahl verschiedener Folgen, die im Zeitraum mindestens einmal fertig gehört wurden, von der heutigen Zahl der Folgen („17/20“) |
| **Zeitraum** | Woche = letzte 7 Tage, Monat = 30, Jahr = 365, bis jetzt; Alles = seit Beginn; gerechnet nach dem Beginn der Sitzung |
| **Quelle** (`wer`) | `box:<id>` oder `benutzer:<HA-Benutzer-ID>`; „Alle“ = Summe aller Quellen (Frage 28) |

Die Kennung des Tobies wird nie übertragen und nie gespeichert (Frage 9).

## 3. Box: Sitzungen erkennen, puffern, senden

### 3.1 Sitzung erkennen

Ein neuer Beobachter `gehoert.py` (neben `status.py`) hört auf `SitzungGeaendert` und die Zeit-Takte und führt **eine
offene Sitzung** im Speicher: Serie, Folge, Beginn (Wanduhr + Monotonuhr + `zeit_ok`), `gespielt_s` (nur Zeit im
Zustand „spielt“), letzter Pausegrund.

Die Sitzung **endet**:

| Anlass | `ende` |
|---|---|
| Folge zu Ende (Kern meldet `folgenende`) | `ende_der_folge` |
| Andere Folge oder anderer Tobie startet | `wechsel` |
| Pause länger als 5 Minuten (Gründe `abgehoben`, `knopf`, `stumm`, `gute_nacht`, `leser_unbekannt`, `fehler`) | `pause`, dazu `grund` = letzter Pausegrund |
| Herunterfahren | `herunterfahren` |

Sitzungen unter 10 s `gespielt_s` werden verworfen (nicht geschrieben, nicht gesendet).

### 3.2 Uhr

Ist beim Beginn `zeit_ok = false`, merkt sich die Box `boot_id` und Monotonzeit. Wird die Uhr **im selben Lauf** gut,
rechnet sie den Beginn nach (`wand_jetzt − (mono_jetzt − mono_beginn)`) und setzt `zeit_ok = true`. Endet der Lauf
vorher, geht die Sitzung mit `zeit_ok = false` hinaus; HA nimmt dann die **Empfangszeit minus `gespielt_s`** als
Beginn und merkt `zeit_geschaetzt = 1` (12.2.1 alt).

### 3.3 Puffer `gehoert.jsonl`

- Datei im Datenordner der Box (`[pfade] zustand`), eine Zeile je **beendeter** Sitzung, Schreiben atomar (Anhängen
  mit `fsync`), **höchstens 1 Schreibvorgang je Sitzungsende** (neu in data-model 1.7).
- Jede Zeile hat eine **laufende Nummer `nr`** je Box, die Neustarts überlebt (aus der letzten Zeile bzw. einer
  kleinen Merkdatei `gehoert_nr`, geschrieben mit der Zeile). Name `nr`, nicht `seq` (`seq` gehört zum Leser-Protokoll).
- Höchstens **2 000 Zeilen** (≈ 400 KiB); darüber fallen die ältesten, auch unquittierte, weg (Box-Protokoll-Eintrag).
- Quittierte Zeilen werden beim nächsten Schreiben entfernt (kein eigener Schreibvorgang nur fürs Aufräumen).

### 3.4 Senden und Quittung

- Bei jeder Verbindung (`_hallo`) und nach jedem Sitzungsende sendet die Box **alle unquittierten** Zeilen als
  Ereignisse `art = gespielt`, in Reihenfolge, höchstens 20 je Sekunde.
- HA antwortet mit dem Befehl **`gehoert_quittung`** (`daten.bis_nr`, `ttl_s` 3600): alles bis einschließlich `bis_nr`
  ist gespeichert. Die Box merkt `bis_nr` im Speicher und räumt beim nächsten Schreiben auf.
- **Zwischenstand:** Läuft eine Sitzung länger als 15 Minuten, sendet die Box alle 15 Minuten `gespielt` mit
  `ende = teilweise` und der gleichen `sitzung` (nur MQTT, **nicht** in die Datei); HA ersetzt den Stand je `sitzung`.
  So fehlen bei Stromausfall höchstens 15 Minuten.

### 3.5 Vertrag `mqtt-v1.md` (Entwurf)

**3.4, neue `art` `gespielt`** (`daten`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `nr` | int ≥ 1 | laufende Nummer je Box (nicht bei `teilweise`: dort `null`) |
| `sitzung` | string (UUID) | gleich für Zwischenstände und Abschluss |
| `serie` | string | Serien-ID |
| `folge` | string | Name der Folge (wie in `resume.json`) |
| `beginn` | string (ISO) | Beginn nach Box-Uhr |
| `zeit_ok` | bool | war die Uhr beim Beginn (oder nach dem Nachrechnen) gut? |
| `gespielt_s` | int | gespielte Sekunden ohne Pausen |
| `ende` | string | `ende_der_folge`, `wechsel`, `pause`, `herunterfahren`, `teilweise` |
| `grund` | string, optional | bei `pause`: letzter Pausegrund der Box |

**3.7, neuer Befehl `gehoert_quittung`** (`daten.bis_nr`). Eine Box, die ihn nicht kennt, antwortet wie bisher mit
`fehler/befehl_unbekannt`; HA sendet ihn nur an Boxen, die `gespielt` gesendet haben.

**8, Ergänzung:** Empfänger ignorieren unbekannte `art` (heute nicht zugesichert). HA ab Stufe B legt `gespielt` nicht
in `box_ereignisse` ab.

**Rollout:** erst die Integration (versteht `gespielt`), dann die Box. Eine alte Integration würde `gespielt` in die
20 Plätze von `box_ereignisse` legen; darum ist die Reihenfolge Pflicht (Hinweis im Update-Ablauf der Box).

## 4. HA: Speicher

### 4.1 SQLite `<config>/tobibox/gehoert.sqlite`

Zugriff nur im Executor, eine Verbindung, WAL, Schema-Version in `PRAGMA user_version`, Migration beim Start.

| Tabelle | Spalten | Schlüssel und Indizes |
|---|---|---|
| `sitzungen` | `quelle` (`box:<id>` / `benutzer:<id>`), `nr` (Box, sonst NULL), `sitzung`, `wiedergabe`, `serie`, `folge`, `beginn`, `zeit_geschaetzt`, `gespielt_s`, `ende`, `grund` | `UNIQUE(sitzung)`; `UNIQUE(quelle, nr)` wo `nr` nicht NULL; Indizes `(serie, folge, beginn)`, `(quelle, beginn)` |
| `technik` | `box`, `zeit`, `art` (`online`, `offline`, `lader_an`, `lader_aus`, `sync_ok`, `sync_fehler`, `fehler`), `wert` | Index `(box, zeit)` |

Eine Tabelle für Boxen **und** Reinhören (statt `reinhoer_sitzungen` im alten Entwurf): dieselbe Zählregel, eine
Abfrage für „Alle“. Größe: etwa 10 MB im Jahr (alter Entwurf 12.3), keine Aufräumregel.

### 4.2 Aufnahme

- **Box:** `gespielt` → Zeile einfügen bzw. bei gleicher `sitzung` ersetzen (`teilweise` → endgültig). `wiedergabe`:
  Kennung der vorigen Sitzung derselben Quelle und Folge, wenn sie höchstens 5 Minuten vor `beginn` endete, sonst neu.
  Nach dem Speichern `gehoert_quittung` mit der höchsten lückenlos gespeicherten `nr` (gesammelt, höchstens alle 2 s).
- **Technik:** HA schreibt eine Zeile, wenn sich in `status` `lader` ändert, bei `online`/`offline` und bei den
  Ereignissen `fehler` und Sync-Ergebnissen. Ladezeiten und Laufzeit je Ladung rechnet `technik/verlauf` daraus;
  Lücken, solange eine Box offline ist, bleiben Lücken (die Box ändert dafür nichts). Den Akku-Verlauf liefert die
  Langzeitstatistik von HA für den Akku-Sensor der Box.

### 4.3 Favoriten

Store `tobibox.favoriten`: Menge aus `serie_id` und `serie_id#folge`, **für die ganze Familie** (nicht je Benutzer),
mit `gesetzt_von` und `gesetzt_am`. Gelöschte Serien/Folgen fallen beim Lesen weg.

## 5. HA: Reinhören als Sitzungen

HA führt je HA-Benutzer **eine offene Reinhör-Sitzung im Speicher** (Serie, Folge, Beginn, letzte Zeit, letzte
Position, `gespielt_s`) und wertet jeden Aufruf `hoerstelle/set` aus:

- `dt` = Sekunden seit dem letzten Aufruf, `dp` = Positionsänderung (bei Ordner-Folgen über `track` und `spuren_s`
  in Sekunden der ganzen Folge).
- Als gespielt zählt `dp`, wenn `0 < dp ≤ 2 × dt + 2` und `dt ≤ 30` (Wiedergabe bis doppelte Geschwindigkeit;
  Springen und lange Pausen zählen nicht).
- Ende: `fertig` → `ende_der_folge`; andere Folge → `wechsel`; kein Aufruf mehr seit 5 Minuten → `pause` (eine
  Aufräumschleife je Minute schließt solche Sitzungen).
- Beim Herunterfahren von HA werden offene Sitzungen geschlossen und geschrieben.
- Zählregel wie Abschnitt 2; Quelle `benutzer:<id>`.

Die Grenze von 30 `hoerstelle/set` je Minute bleibt; ein abgelehnter Aufruf verliert höchstens einige Sekunden.
Genauigkeit „etwa“: Schließt jemand die Seite, fehlen bis zu 10 s.

## 6. HA: Befehle (Vertrag `ha-websocket-v1.md`, Entwurf)

Fähigkeiten: **`gehoert`** (Befehle 50 bis 56, Unterseite, Reihen, Sortierungen) und **`favoriten`** (Befehle 57, 58,
Stern). Die frühere Fähigkeit `gehoert_reinhoeren` entfällt: Personen erscheinen in „Wer?“, sobald sie reingehört
haben.

| Nr. | Befehl | Recht | Eingabe → Ausgabe |
|---|---|---|---|
| 50 | `gehoert/zusammenfassung` | lesen | `wer` (`alle` Vorgabe, `box:<id>`, `benutzer:<id>`), `zeitraum` (`woche`, `monat`, `jahr`, `alles`) **oder** `von`/`bis`, `nach` (Liste aus `wer`, `serie`, `folge`, `tag`, `woche`, `monat`, `stunde`), `serie_id` (optional), `sortierung` (`wiedergaben` Vorgabe, `sekunden`), `limit` (1–200) → `zeilen` (Schlüssel aus `nach` plus `wiedergaben`, `sekunden`, `fertig`; ohne `folge` in `nach` auch `folgen_fertig`, `folgen_gesamt`), `summe`, `wer_auswahl` (Boxen aus `boxen/list`; HA-Benutzer, die reingehört haben, mit Namen aus HA). Fehler `wer_ungueltig` |
| 51 | `gehoert/zuletzt` | lesen | `wer` (Vorgabe `boxen` = alle Boxen), `limit` → Serien mit letzter Wiedergabe (für die Reihe „Zuletzt auf den Boxen gehört“) |
| 52 | `gehoert/meist` | lesen | `wer`, `zeitraum`, `limit` → Serien nach Wiedergaben |
| 53 | `technik/verlauf` | admin | `box`, `von`, `bis` → Ladevorgänge (Beginn, Ende, Dauer), Laufzeit je Ladung, online/offline, Syncs, Fehler; Akku-Werte liest die Seite über `recorder/statistics_during_period` |
| 54 | `gehoert/exportieren` | admin | `quelle` (`boxen`, `reinhoeren`, `alle`) → signierter Download-Pfad (CSV, 1 Stunde gültig, wie Audio-Pfade) |
| 55 | `gehoert/loeschen` | admin | `quelle` (`boxen`, `reinhoeren`, `benutzer:<id>`, `alle`), `bestaetigung` = „LÖSCHEN“ → `{geloescht: n}` |
| 56 | (reserviert) | | |
| 57 | `favorit/set` | alltag | `serie_id`, `folge` (optional), `an` (bool) → `{an}`; Ereignis `favoriten` `geaendert` |
| 58 | `favoriten/list` | lesen | → Liste |

`serien/list`: neue Sortierungen **`zuletzt_gehoert`** (Boxen und Reinhören aller, nach letzter Wiedergabe) und
**`meist_gehoert`** (Wiedergaben im letzten Jahr), neuer Filter **`favorit`**; je Serie neue Felder `favorit` (bool)
und, mit `gehoert`, `zuletzt_gehoert_am`. `serie/get`: je Folge `favorit`. `angehoert` bleibt die **eigene, private**
Sortierung nach Hörstellen.

## 7. Seite

- **Geräte:** Zeile „Wer hat was gehört?“ (Muster X10) → `#gehoert`, nur mit `gehoert`. Inhalt der Unterseite wie
  HA-Oberfläche 5.10 und 5.10.1 (Wer?, Zeitraum, Rangliste mit Aufteilung nach Folgen, Hörzeit pro Tag, Tageszeiten,
  „Was wird gezählt?“). Diagramm-Raster: Woche/Monat in Tagen, Jahr in Wochen, Alles in Monaten (`nach`).
- **Start:** Reihen „Zuletzt auf den Boxen gehört“ (Befehl 51) und „Favoriten“ (statt „Favoriten / Empfehlungen“;
  Empfehlungen gibt es nicht). Leere Reihen bleiben unsichtbar.
- **Bibliothek:** Sortierungen „Zuletzt gehört“, „Meist gehört“; Filter „Favoriten“.
- **Stern:** auf der Serienseite im Kopf und je Folge im Menü „⋯“ („Zu Favoriten“ / „Aus Favoriten“), als Knopf mit
  `aria-pressed`, 44 px. In Zeilen und Kacheln ein kleiner gefüllter Stern als Zeichen (kein Knopf).
- **Technik:** Unterseite der Box (`#technik-box-<id>`) bekommt die Karte „Verlauf“ (Akku-Kurve 7/30 Tage, Ladevorgänge,
  Laufzeit je Ladung). „Speicher und Netz“ bekommt die Karte „Hördaten“: „Als Tabelle sichern“ (54), „Hördaten der
  Boxen löschen …“, „Reinhör-Daten löschen …“ (55, Bestätigung mit Wort).
- Texte kurz, keine Erklärsätze (AM16); die Erklärung „Was wird gezählt?“ ist aufklappbar.

## 8. Reste aus Stufe A in derselben Vertragsrevision

Siehe `concepts_brief.md` Abschnitt 6: `hello.grenzen.hoerkopie_schlange`; AM24 und AM25 in 2.4; `serie/get` Hörstelle
je Folge mit `track`; `serien/list` ohne `limit`; `einsortierung/bestaetigen` setzt `pruefen` im Eingangsprotokoll
zurück, `eingang/list` nennt Dateinamen und Zahl einer Gruppe.

## 9. Pakete und Abnahmen

| AP | Inhalt | Modell |
|---|---|---|
| **B0** | Verträge: mqtt-v1 (3.4 `gespielt`, 3.7 `gehoert_quittung`, 8), data-model (1.6/1.7 `gehoert.jsonl`), ha-websocket-v1 (Befehle 50–58, Fähigkeiten, Sortierungen, Felder; Reste aus A); **Freigabe Tobias** | PL |
| **B1** | Box: Beobachter `gehoert.py`, Uhr-Nachrechnung, Puffer mit `nr`, Senden bei Verbindung, Quittung, Zwischenstände; Tests im Kern-Stil (reine Funktionen, simulierte Zeit) | Sonnet |
| **B2** | HA: SQLite (Schema, Migration, Executor), Aufnahme `gespielt` mit Quittung, Technik-Zeilen aus `status`, Reinhör-Sitzungen aus `hoerstelle/set`, Favoriten-Store; Tests der Zählregel und Grenzfälle | Sonnet |
| **B3** | HA: Befehle 50–58, Sortierungen, Filter, Felder, Export-Pfad, Löschen; Leistung: Rangliste unter 50 ms bei 30 000 Zeilen | Sonnet |
| **B4** | Seite: `#gehoert`, Reihen auf Start, Sortierungen/Filter, Stern, Technik-Karten; jsdom, Browser-Prüfung mit Mock-Daten | Sonnet |
| **B5** | **Simulator** `tools/box_simulator.py` (außerhalb der Integration): spielt Sitzungen einer erfundenen Box gegen den echten Broker (eigene Test-Box-ID `boxsim`, eigenes MQTT-Konto, nur mit Freigabe) **oder** über HAs Aktion `mqtt.publish`; beantwortet `gehoert_quittung`. Grundlage der Abnahme ohne Boxen | Sonnet |
| **B6** | Abnahme mit Tobias, Schritt für Schritt: Reinhören am Mac und iPhone → „Gehört“ unter dem eigenen Namen; simulierte Box (offline gespielt, dann verbinden, Quittung) → Rangliste, Diagramme; Stern, Reihen, Sortierungen; Technik-Verlauf (simuliert); Export, Löschen | PL + Tobias |
| **B7** | Abnahme der Box-Teile an echter Hardware (wenn die Boxen gebaut sind) | PL + Tobias |

Reihenfolge: B0 → (B1 ‖ B2) → B3 → B4 ‖ B5 → B6. B1 hängt nur am Vertrag und läuft neben B2.

## 10. Offene Fragen für Tobias

| Nr. | Frage | Empfehlung |
|---|---|---|
| B-F1 | Reinhören am Handy zählt mit derselben Regel wie die Box; „Alle“ addiert Kinder (Boxen) und Erwachsene (Frage 28). Braucht es zusätzlich „Alle Boxen“ als Auswahl? | Ja, „Alle Boxen“ als zweiter Knopf nach „Alle“: die Kinder zusammen, ohne die Erwachsenen |
| B-F2 | Favoriten für die ganze Familie oder je HA-Benutzer? | Ganze Familie (wie alter Entwurf 5.10); der Stern zeigt, wer ihn gesetzt hat, nur im Menü |
| B-F3 | Simulierte Box für die Abnahme: eigenes MQTT-Konto `boxsim` im Mosquitto anlegen (du) oder nur über `mqtt.publish` aus HA? | `mqtt.publish` (kein neues Konto), Quittungen liest der Simulator dann nicht; Quittung wird mit B7 an echter Hardware abgenommen |
| B-F4 | Pause bis 5 Minuten gehört zur Sitzung (Box und Reinhören gleich). Passt das für „Gute Nacht“ (Box pausiert zur Schlafenszeit)? | Ja; die Sitzung endet mit `grund = gute_nacht` nach 5 Minuten |
