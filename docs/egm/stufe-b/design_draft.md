# Stufe B „Gehört“: Design-Entwurf (EGM Schritt 2)

Stand 16.11., **Rev. 2** (Befunde der Goldfische und Entscheidungen R1 bis R4 eingearbeitet, `resolve.md`).
Grundlage: `concepts_brief.md`, Faktenbericht zum Code vom 16.11., alter Entwurf in `docs/designs/ha-oberflaeche.md`
Abschnitte 5.1, 5.10, 12 und 15.2. Dieser Entwurf **ersetzt** Abschnitt 12 und 15.2 der HA-Oberfläche; 5.10 (Seite
„Gehört“) gilt weiter, wo hier nichts anderes steht. Verträge: `docs/protocol/mqtt-v1.md`,
`docs/protocol/ha-websocket-v1.md`, `docs/data-model.md`.

## 0. Ziel

Die Familie sieht in Home Assistant, **wie lange welche Box (welches Kind) und welcher HA-Benutzer was gehört hat**,
wie oft und was ganz, was zuletzt lief; sie kann Einträge mit einem Stern merken; Administratoren sehen den Verlauf von
Akku und Laden. Die Daten bleiben unbegrenzt und nur in HA. **Die Hörzeit steht vorn** (R1).

## 1. Heutiger Stand (Faktenbericht 16.11., berichtigt)

| Bereich | Stand | Folge für B |
|---|---|---|
| Box → HA, `tobibox/<box>/event` (mqtt-v1 3.4) | nicht retained, QoS 1; Arten `liste_abgelehnt`, `fehler`, `befehl_abgelehnt`; neue `art` ohne Versionserhöhung erlaubt (8), **aber** Empfänger müssen unbekannte `art` heute nicht ignorieren | neue `art` `gespielt` auf demselben Thema (keine neue ACL); mqtt-v1 8 sichert das Ignorieren neu zu; Handshake (3.5) |
| Box: Senden ohne Verbindung | `sende_event` verwirft; nur `unknown.json` hat einen Puffer (`outbox.py`) | eigener Puffer `gehoert.json` |
| Box: Uhr | `zeit_ok`, `zeitquelle`, `Jetzt(wall, mono, …)`, `boot_id` | Uhr-Regel 3.3 |
| Box: Wiedergabe | Kern `core.step()`, Teilautomat `session`; Pausegründe `abgehoben`, `folgenende`, `knopf`, `stumm`, `gute_nacht`, `leser_unbekannt`, `fehler`, `herunterfahren`; äußere Ereignisse und Befehle erreichen Beobachter (`status.beobachte`, `status.befehl`); `SitzungGeaendert` ist **intern** | Beobachter `gehoert.py` mit eigenen Eingängen (3.1) |
| Box: Schreibbudget (data-model 1.7) | `resume.json` alle 30 s während der Wiedergabe, höchstens 320 je Tag | offene Sitzung in `resume.json`, `gehoert.json` je Sitzungsende |
| HA: Ereignisse der Box | `mqtt.py` speichert jede `art` in `box_ereignisse` (20 je Box), dedupliziert über `id` | `gespielt` wird vorher abgenommen, dedupliziert über `sitzung` |
| HA: Reinhören | Seite ruft `hoerstelle/set` höchstens alle 10 s und sofort bei Pause, Sprung, Wechsel, Ende, Ausblenden; Grenze 30 je Minute; HA speichert nur die letzte Stelle | Reinhör-Sitzungen aus diesen Aufrufen (5), neue Felder `spieler`, `spielt` |
| HA: Speicher | Stores `tobibox`, `tobibox.hoerstellen`, `tobibox.medieninfo`, `tobibox_eingang`; kein SQLite | SQLite-Datei, Store `tobibox.favoriten` |
| HA: Akku | Sensor per MQTT-Discovery der Box (`state_class measurement`) | Langzeitstatistik von HA ist da |
| Seite | Start hat Reihen „Zuletzt auf den Boxen gehört“ und „Favoriten / Empfehlungen“ (leer, unsichtbar); `#gehoert` leitet ohne `gehoert` um; kein Stern; Sortierung `angehoert` = eigene Hörstellen | anschließen |
| ha-websocket-v1 | Befehle 1 bis 49; Stufe B nicht Teil des Vertrags | Befehle ab 50 |

## 2. Begriffe und Zählregel (Boxen und Reinhören gleich)

| Begriff | Regel |
|---|---|
| **Quelle** (`wer`) | `box:<id>` oder `benutzer:<HA-Benutzer-ID>`. Auswahl: **Alle** (alle Quellen, Frage 28), **Alle Boxen** (die Kinder zusammen), je Box, je Person |
| **Sitzung** | zusammenhängendes Hören **einer Folge** an **einer Quelle**. Pausen bis **30 Minuten** gehören dazu (R2); danach ist sie zu Ende. Grenzen im Einzelnen: 3.2 |
| **Hörzeit** (vorn, R1) | Summe der **Inhaltszeit**, aus dem Fortschritt der Position: Zuwächse `dp` mit `0 < dp ≤ 2 × dt + 2` (`dt` Monotonzeit). Springen und Pausen zählen nicht; bei schnellerem Abspielen zählt die Länge des Inhalts. Jede Sitzung zählt, auch unter 10 s |
| **Mal** (Nebenspalte, R1) | Sitzungen derselben Quelle und Folge werden zu einem Mal zusammengelegt, wenn die vorige höchstens 30 Minuten vor dem Beginn endete **und nicht am Ende der Folge** endete; ein Mal zählt ab 10 s Hörzeit. Wiederholen nach „fertig“ ist immer ein neues Mal. „Mal“ wird **bei der Abfrage** gerechnet, nicht gespeichert |
| **fertig** | ein Mal, dessen letzte Sitzung am Ende der Folge endete **und** in dem mindestens 80 % der Folgendauer gehört wurden (Dauer unbekannt: mindestens 60 s). Box: ihr Ereignis „Folge zu Ende“; Reinhören: `fertig: true` der Seite |
| **Fertig je Hörspiel** | verschiedene, **heute vorhandene** Folgen, die im Zeitraum mindestens einmal fertig gehört wurden, von der heutigen Zahl („17/20“) |
| **Zeitraum** | in der Zeitzone von HA: Woche = heute und die 6 Kalendertage davor, Monat = 30, Jahr = 365 Kalendertage; Alles = seit Beginn. Eine Sitzung zählt zum Tag und zur Stunde ihres Beginns. Sitzungen mit unbekanntem Datum (3.3) zählen nur in „Alles“ und in Ranglisten, nie in Diagrammen |

Die Kennung des Tobies wird nie übertragen und nie gespeichert (Frage 9). **Datenschutz** (Frage 23, präzisiert): Die
**Stelle** zum Weiterhören ist privat; **dass** jemand etwas gehört hat und wie lange, sieht die Familie.

## 3. Box

### 3.1 Beobachter `gehoert.py`

Ein **reines Modul** mit eigenem Schritt (Eingang → neuer Zustand + Ausgaben), getrieben aus `app.verarbeite` wie
`status.py`. Eingänge: `ZustandMelden` (Modus, Serie, Folge, Track), Befehle `Pausieren(grund)` und `ZeigerSpeichern`,
Ereignis `FolgeZuEnde` (die **beendete** Folge, nicht die nächste), `DienstEndet`, `Takt`, `PlayerPosition`
(`spielt`, `track`, `position_s`). Er führt höchstens **eine offene Sitzung**: `sitzung` (UUID), Serie, Folge,
`boot_id`, `beginn_boot_s`, Wanduhr-Beginn, letzte Position, `gehoert_s`, letzter Pausegrund, Zeitpunkt der letzten
gespielten Sekunde. Dasselbe Modul treibt Tests und Simulator (9, B5).

### 3.2 Sitzungsgrenzen (Vorrang von oben nach unten)

| Anlass | `ende` |
|---|---|
| Gerät fährt herunter | `herunterfahren` |
| Dienst endet (Neustart der Box-Software) | `dienst_ende` |
| Beim Start liegt in `resume.json` eine offene Sitzung (Strom weg, Absturz) | `abbruch` |
| `FolgeZuEnde` für die laufende Folge | `ende_der_folge` |
| Die erste gespielte Sekunde einer **anderen** Folge (anderer Tobie, Weiter/Zurück in eine andere Folge) | `wechsel` |
| Seit 30 Minuten keine gespielte Sekunde (jede Pause, auch `fehler`, `leser_unbekannt`, `gute_nacht`) | `pause`, `grund` = letzter Pausegrund |

Track-Wechsel in einer Ordner-Folge und Springen innerhalb der Folge beenden die Sitzung nicht. `ende_um` ist immer
der Zeitpunkt der letzten gespielten Sekunde, nicht der Zeitpunkt, an dem die 30 Minuten abliefen.

### 3.3 Uhr

Alle Dauern und Fristen rechnen auf Monotonzeit. Jede Zeile trägt `boot_id`, `beginn_boot_s`, `ende_boot_s` und die
Wanduhr-Zeiten mit `zeit_ok`. Wird die Uhr im selben Gerätestart gut, korrigiert die Box **alle** Zeilen dieses
Starts im Puffer (ein Schreibvorgang). Bleibt `zeit_ok = false`, rechnet HA beim Empfang, wenn die Box noch im selben
Start ist (`status` meldet `boot_id`), `empfangen − (jetzt_boot_s − beginn_boot_s)`; sonst gilt das Datum als
**unbekannt** (2, Zeitraum).

### 3.4 Puffer `gehoert.json` und offene Sitzung

- `gehoert.json` im Datenordner, Muster der Zustandsdateien (`schema_version`, `schreibe_atomar`, Hintergrund-Schreiber
  wie `outbox`): `{"schema_version": 1, "puffer_id": <UUID>, "naechste_nr": n, "quittiert_bis": n, "zeilen": […]}`.
  Eine beendete Sitzung = eine Zeile, Nummer und Aufräumen quittierter Zeilen = **ein** atomarer Schreibvorgang.
- Höchstens **500 Zeilen**; darüber fallen die ältesten weg, die Box zählt sie in `verworfen` und schreibt einen
  Eintrag ins Box-Protokoll.
- Neue Datei (neue SD-Karte, kaputt) = neue `puffer_id`, `nr` beginnt bei 1. `gehoert.json` gehört nicht in die
  Rückfall-Sicherung des Updates.
- Die **offene** Sitzung steht in `resume.json` (`sitzung_offen`), das ohnehin alle 30 s geschrieben wird; beim Start
  wird sie zur Zeile mit `ende = abbruch`. Verlust höchstens 30 s, kein zusätzlicher Schreibvorgang.
- Schreibbudget (neu in data-model 1.7): ein Schreibvorgang je Sitzungsende; Quittungen werden mitgeschrieben oder
  höchstens alle 10 Minuten gesammelt.

### 3.5 Senden, Handshake, Quittung

- **Handshake:** Die Box sendet `gespielt` erst, wenn in diesem Lauf einmal `gehoert_quittung` kam (auch `bis_nr = 0`).
  HA schickt diese Quittung, sobald eine Box `online` ist und ihr `status` die Fähigkeit `gehoert` meldet. Eine alte
  Integration bekommt so nie `gespielt`; eine alte Box bekommt nie eine Quittung.
- **Senden:** alle unquittierten Zeilen nach dem Handshake, bei `homeassistant/status online` und höchstens alle
  10 Minuten, solange Unquittiertes da ist; nach einem Sitzungsende nur die neue Zeile. Höchstens 20 je Sekunde.
- **Zwischenstand:** Läuft eine Sitzung länger als 15 Minuten und ist die Box verbunden, sendet sie alle 15 Minuten
  `gespielt` mit `ende = teilweise`, `nr = null` (nur MQTT).
- **Quittung** (HA): höchste lückenlos gespeicherte `nr` ab `puffer_ab`, nur steigend, auch wenn alles schon bekannt
  war; ungültige Zeilen werden mitquittiert (HA-Protokoll). Die Box ignoriert Quittungen mit fremder `puffer_id`.
  `gehoert_quittung` behandelt `ha.py` selbst: ohne Zeit- und `zeit_ok`-Prüfung, idempotent, nicht in den 50
  gemerkten Befehls-`id`s.

### 3.6 Vertrag `mqtt-v1.md` (Entwurf)

**3.3 `status`:** neue Felder `boot_id` (string) und `faehig` (Liste, hier `["gehoert"]`).

**3.4 neue `art` `gespielt`** (`daten`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `puffer_id` | string (UUID) | Puffer der Box |
| `nr` | int ≥ 1 oder `null` | Nummer im Puffer; `null` nur bei `teilweise` |
| `puffer_ab` | int | kleinste `nr`, die die Box noch hält |
| `verworfen` | int | beim Überlauf verworfene Zeilen seit dem letzten Senden |
| `sitzung` | string (UUID) | gleich für Zwischenstände und Abschluss |
| `serie`, `folge` | string | Serien-ID, Name der Folge (wie in `resume.json`) |
| `folge_dauer_s` | int oder `null` | Länge der Folge, wenn bekannt |
| `beginn`, `ende_um` | string (ISO) | Wanduhr der Box |
| `zeit_ok` | bool | Wanduhr vertrauenswürdig |
| `boot_id`, `beginn_boot_s`, `ende_boot_s` | string, int, int | Monotonzeit des Gerätestarts |
| `gehoert_s` | int | Hörzeit nach 2 |
| `ende` | string | `ende_der_folge`, `wechsel`, `pause`, `herunterfahren`, `dienst_ende`, `abbruch`, `teilweise` |
| `grund` | string, optional | bei `pause`: letzter Pausegrund |

**3.7 neuer Befehl `gehoert_quittung`** (`daten`: `puffer_id`, `bis_nr`); Sonderregel wie 3.5.

**8:** Empfänger ignorieren unbekannte `art` und unbekannte Felder (neu zugesichert).

### 3.7 Datenmodell `data-model.md` (Entwurf)

1.6: neue Zustandsdatei `gehoert.json` (Aufbau 3.4); `resume.json` bekommt optional `sitzung_offen`. 1.7: Schreibbudget
wie 3.4. Rückfall-Sicherung: ohne `gehoert.json`.

## 4. HA: Speicher

### 4.1 SQLite `<config>/tobibox/gehoert.sqlite`

Eine Verbindung im Executor mit `threading.Lock`, `journal_mode=TRUNCATE`, `synchronous=FULL`, Schema-Version in
`PRAGMA user_version`, Migration nur vorwärts, `PRAGMA integrity_check` beim Start ins Protokoll. Ist die Datei nicht
zu öffnen, startet die Integration ohne Fähigkeit `gehoert`.

| Tabelle | Spalten | Schlüssel und Indizes |
|---|---|---|
| `sitzungen` | `sitzung` (UUID), `quelle`, `puffer_id`, `nr`, `serie`, `folge`, `folge_dauer_s`, `beginn`, `ende_um` (UTC-Sekunden), `datum_unbekannt`, `tag`, `stunde` (Zeitzone von HA), `gehoert_s`, `ende`, `grund` | Hauptschlüssel `sitzung`; Indizes `(quelle, serie, folge, beginn)`, `(serie, folge, beginn)`, `(tag)`, `(beginn)` |
| `technik` | `box`, `zeit`, `art` (`online`, `offline`, `lader_an`, `lader_aus`, `sync_ok`, `sync_fehler`, `fehler`), `wert` | Index `(box, zeit)` |

Einfügen mit `ON CONFLICT(sitzung) DO UPDATE … WHERE alt.ende = 'teilweise'`, nie `OR REPLACE`. Verwaiste `teilweise`
schließt HA nach 24 h als `abbruch`. Größe: einige 10 MB im Jahr, keine Aufräumregel. HA-Sicherungen enthalten die
Hördaten (Hinweis in `docs/betrieb/`).

### 4.2 Aufnahme

- **Box:** `gespielt` wird in `mqtt.py` **vor** `box_ereignis_hinzu` abgenommen, gesammelt geschrieben (ein `COMMIT` je
  Sendung), danach `gehoert_quittung` (3.5), höchstens alle 2 s je Box. Nur bekannte Boxen.
- **Technik:** eine Zeile bei **echtem Wechsel** gegen die letzte gespeicherte Zeile je Box (`lader`, `online`,
  Sync-Ergebnis über `sync.letzter_ende`, Ereignis `fehler`); der erste `status` nach einem HA-Start wird nur verglichen.
  Zeit: `ts` der Box bei `zeit_ok`, sonst Empfangszeit.
- **Ändern der Bibliothek:** Verschieben und Zusammenführen schreiben `serie`/`folge` in `sitzungen` mit; Umbenennen
  ändert nichts.

### 4.3 Favoriten

Store `tobibox.favoriten` für **die ganze Familie** (R3): `serie_id` oder `serie_id#folge`, `gesetzt_von`,
`gesetzt_am`; höchstens 1 000; gelöschte Einträge fallen beim Lesen weg.

## 5. HA: Reinhören als Sitzungen

- `hoerstelle/set` (Befehl 41) bekommt die optionalen Felder **`spieler`** (zufällige Kennung je Player-Instanz der
  Seite) und **`spielt`** (bool). HA führt je (Benutzer, `spieler`) eine offene Sitzung im Speicher; ohne `spieler`
  eine je Benutzer. Grenze steigt auf 60 Aufrufe je Minute und Benutzer.
- Hörzeit nach 2 (`dp` in Sekunden der ganzen Folge; bei Ordner-Folgen ohne `spuren_s` nur innerhalb eines Tracks).
  War beim letzten Aufruf `spielt = true` und passt `dp ≤ 2 × dt + 2`, zählt auch `dt > 30` (Seite war eingefroren,
  Ton lief).
- Ende: `fertig: true` → `ende_der_folge`; andere Folge → `wechsel`; 30 Minuten ohne Fortschritt → `pause`
  (Aufräumschleife je Minute); HA fährt herunter → `dienst_ende`. Offene Sitzungen schreibt HA alle 5 Minuten als
  `teilweise`.
- **B2a vor B2:** Messung am iPhone mit gesperrtem Bildschirm (HA-App und Safari), wie oft `hoerstelle/set` kommt.
  Kommt fast nichts, steht unter „Was wird gezählt?“: „Am Handy mit gesperrtem Bildschirm wird nur ungefähr gezählt.“

## 6. HA: Befehle (Vertrag `ha-websocket-v1.md`, Entwurf)

| Fähigkeit | schaltet frei |
|---|---|
| `gehoert` | Befehle 50, 51, 52, 53, 54; Unterseite `#gehoert`; Reihe „Zuletzt auf den Boxen gehört“; Sortierungen `zuletzt_gehoert`, `meist_gehoert`; Feld `zuletzt_gehoert_am`; Ereignis-Thema `gehoert` |
| `favoriten` | Befehle 55, 56; Stern; Filter und Feld `favorit`; Reihe „Favoriten“; Ereignis-Thema `favoriten` |

| Nr. | Befehl | Recht | Eingabe → Ausgabe |
|---|---|---|---|
| 50 | `gehoert/zusammenfassung` | lesen | `wer` (`alle` Vorgabe, `alle_boxen`, `box:<id>`, `benutzer:<id>`), `zeitraum` **oder** `von`/`bis` (schließen sich aus), `nach` (Liste aus `wer`, `serie`, `folge`, `tag`, `woche`, `monat`, `stunde`), `serie_id`, `sortierung` (`sekunden` Vorgabe, `mal`), `limit` (1–200, nur ohne Zeitschlüssel) → `zeilen` (Schlüssel aus `nach` plus `sekunden`, `mal`, `fertig`; ohne `folge` in `nach` auch `folgen_fertig`, `folgen_gesamt`; gelöschte Serien als eine Zeile `geloescht`), Zeitreihen lückenlos aufsteigend (höchstens 400 Zeilen), `summe`, `wer_auswahl` (Boxen aus `boxen/list`, Personen mit Namen aus HA, gelöschte als „Früherer Benutzer“), `zeitzone`, `von`, `bis`. Fehler `invalid_format`, `wer_ungueltig`, `serie_nicht_gefunden` |
| 51 | `gehoert/zuletzt` | lesen | `wer` (Vorgabe `alle_boxen`), `limit` → Serien-Kurzformen wie `serien/list` plus `wer`, `zeit` |
| 52 | `technik/verlauf` | admin | `box`, `von`, `bis` → Ladevorgänge (Beginn, Ende, Dauer), Laufzeit je Ladung, online/offline, Syncs, Fehler. Akku-Werte liest die Seite über `recorder/statistics_during_period` mit der Entitäts-ID aus `boxen/list` (neues Feld `akku_entitaet`) |
| 53 | `gehoert/exportieren` | admin | `quelle` (`boxen`, `reinhoeren`, `alle`, `box:<id>`, `benutzer:<id>`) → signierter Pfad, 10 Minuten, nur für den Anfragenden; CSV UTF-8 mit BOM, `;`, Formel-Zeichen entschärft |
| 54 | `gehoert/loeschen` | admin | `quelle` (wie 53), `trocken` (bool), `bestaetigung` = „LÖSCHEN“ (nicht bei `trocken`) → `{anzahl}` |
| 55 | `favorit/set` | alltag | `serie_id`, `folge` (optional), `an` → `{an}`; Fehler `serie_nicht_gefunden`, `folge_nicht_gefunden`, `zu_viele_favoriten`; Mengen wie Listen-Änderungen; Wiederholung ohne Fehler |
| 56 | `favoriten/list` | lesen | → `eintraege` (`serie_id`, `folge`, `gesetzt_von {id, name}`, `gesetzt_am`) |

`serien/list`: Sortierungen **`zuletzt_gehoert`** (nur Boxen, wie die Reihe) und **`meist_gehoert`** (Hörzeit im
letzten Jahr, alle Quellen); Filter **`favorit`**; je Serie `favorit` und `zuletzt_gehoert_am`. `folgen/list` und
`serie/get`: je Folge `favorit`, `folgen/list` Filter `favorit`. `angehoert` bleibt die eigene, private Sortierung.
Ereignis-Themen: `gehoert` (`geaendert`, gebündelt höchstens alle 5 s, ohne Inhalt; auch nach Löschen) und
`favoriten` (`geaendert` mit `serie_id`, `folge`, `an`). Befehl 41 `hoerstelle/set`: Felder `spieler`, `spielt` (5).

## 7. Seite

- **Geräte:** Zeile „Wer hat was gehört?“ → `#gehoert` (nur mit `gehoert`). Unterseite wie HA-Oberfläche 5.10 und
  5.10.1, mit diesen Änderungen: Auswahl **Alle · Alle Boxen · je Box · je Person**; Rangliste nach **Hörzeit**, Spalten
  **Hörzeit · Mal · fertig**; Diagramm-Raster Woche/Monat in Tagen, Jahr in Wochen, Alles in Monaten; aufklappbar
  „Was wird gezählt?“ (Hörzeit nach Inhalt, Pausen bis 30 Minuten, „Mal“, „fertig“, Handy ungefähr).
- **Start:** Reihen „Zuletzt auf den Boxen gehört“ (Befehl 51) und „Favoriten“ (statt „Favoriten / Empfehlungen“);
  ohne Platzhalter, leere Reihen unsichtbar, Fehler einzelner Reihen still.
- **Bibliothek:** Sortierungen „Zuletzt gehört“, „Meist gehört“; Filter „Favoriten“.
- **Stern:** Knopf im Kopf der Serienseite (`aria-pressed`, Wort im Namen); je Folge im Menü „⋯“ als Text „Zu Favoriten“ /
  „Aus Favoriten“; Meldung nach dem Setzen; in Zeilen und Kacheln ein kleiner Stern mit `aria-label` „Favorit“.
- **Technik:** Box-Unterseite: Karte „Verlauf“ (Akku-Kurve 7/30 Tage, Ladevorgänge, Laufzeit je Ladung; `role="img"`
  und Tabelle). „Speicher und Netz“: Karte „Hördaten“ mit „Als Tabelle sichern“ und Löschen (erst Anzahl, dann
  Bestätigung mit Wort) für Boxen, Reinhören, einzelne Box oder Person.
- Begriffe für Eltern überall gleich: „Hörzeit“, „Mal“, „fertig“. Keine Erklärsätze außer „Was wird gezählt?“ (AM16).

## 8. Reste aus Stufe A in derselben Vertragsrevision

`hello.grenzen.hoerkopie_schlange`; AM24 und AM25 in 2.4; `serie/get` Hörstelle je Folge mit `track`; `serien/list`
ohne `limit` liefert alles; `einsortierung/bestaetigen` setzt `pruefen` im Eingangsprotokoll zurück, `eingang/list`
nennt Dateinamen und Zahl einer Gruppe (`concepts_brief.md` Abschnitt 6).

## 9. Pakete und Abnahmen

| AP | Inhalt | Modell |
|---|---|---|
| **B0** | Verträge: mqtt-v1 (3.3, 3.4, 3.7, 8), data-model (1.6, 1.7, Rückfall), ha-websocket-v1 (Befehle 50–56, Befehl 41, Fähigkeiten, Sortierungen, Felder, Ereignis-Themen; Reste aus A); **Freigabe Tobias** | PL |
| **B2a** | Messung am iPhone: `hoerstelle/set` bei gesperrtem Bildschirm (HA-App, Safari) | PL + Tobias |
| **B1** | Box: `gehoert.py` (rein), Grenzen 3.2, Uhr 3.3, `gehoert.json`, `sitzung_offen` in `resume.json`, Handshake, Senden, Quittung, `status`-Felder; Tests: Absturz, abgeschnittene Datei, Doppelzustellung, Lücke, Überlauf, Uhrsprung, `puffer_id`-Wechsel, Handshake mit alter/neuer HA | Sonnet |
| **B2** | HA: SQLite, Aufnahme mit Quittung und Handshake, Technik-Zeilen, Reinhör-Sitzungen (`spieler`, `spielt`), Favoriten-Store, Mitschreiben bei Verschieben/Zusammenführen; Tests der Zählregel (Mal, fertig 80 %, Wiederholen, Pausen 30 min, Mitternacht, Sommerzeit, unbekanntes Datum, Nachlieferung) | Sonnet |
| **B3** | HA: Befehle 50–56, Felder, Sortierungen, Filter, Ereignisse, Export, Löschen; Leistung: Befehl unter 100 ms bei 30 000 Zeilen, auch während eines Imports | Sonnet |
| **B4** | Seite: `#gehoert`, Reihen, Sortierungen, Filter, Stern, Technik-Karten, `spieler`/`spielt` im Player; jsdom, Browser-Prüfung mit Mock-Daten | Sonnet |
| **B5** | Simulator: Box-Software am Mac als Test-Box (Konfiguration `boxsim`, R4) plus Szenario-Werkzeug mit simulierter Zeit (`--tage 40`, `--seed`; Wiederholen, Hörbuch, Neustart, Nummer zurückgesetzt, Lücke, Überlauf, offline) | Sonnet |
| **B6** | Abnahme mit Tobias: Mosquitto-Konto `boxsim` und Test-Box anlegen (Tobias); Reinhören am Mac und iPhone → eigene Zeile; Test-Box offline spielen, verbinden, Quittung; Rangliste, Diagramme, „Alle Boxen“; Stern, Reihen, Sortierungen; Technik-Verlauf; Export; danach Daten der Test-Box löschen, Test-Box und Konto entfernen | PL + Tobias |
| **B7** | Abnahme der Box-Teile an echter Hardware (wenn die Boxen gebaut sind) | PL + Tobias |

Reihenfolge: B0 → B2a → (B1 ‖ B2) → B3 → (B4 ‖ B5) → B6. Rollout in HA vor der Box ist durch den Handshake nicht mehr
zwingend.

## 10. Offene Fragen für Tobias

Keine. R1 bis R4 sind entschieden; B-F1 (Alle Boxen) ist mit G-M12 erledigt.
