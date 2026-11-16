# Stufe B „Gehört“: Design-Entwurf (EGM Schritt 2)

Stand 16.11., **Rev. 3.1** (Auflagen der Kurzprüfung in Abschnitt 11; Rev. 3: Runde 2 der Goldfische eingearbeitet, `resolve.md`). Rev. 2: Entscheidungen R1 bis R4.
Grundlage: `concepts_brief.md`, Faktenbericht zum Code vom 16.11., alter Entwurf in `docs/designs/ha-oberflaeche.md`
Abschnitte 5.1, 5.10, 12 und 15.2. Dieser Entwurf **ersetzt** Abschnitt 12 und 15.2 der HA-Oberfläche; 5.10 (Seite
„Gehört“) gilt weiter, wo hier nichts anderes steht. Verträge: `docs/protocol/mqtt-v1.md`,
`docs/protocol/ha-websocket-v1.md`, `docs/data-model.md`.

## 0. Ziel

Die Familie sieht in Home Assistant, **wie lange welche Box (welches Kind) und welcher HA-Benutzer was gehört hat**,
wie oft und was ganz, was zuletzt lief; sie kann Einträge mit einem Stern merken; Administratoren sehen den Verlauf von
Akku und Laden. Die Daten bleiben unbegrenzt und nur in HA. **Die Hörzeit steht vorn** (R1).

## 1. Heutiger Stand (Faktenbericht 16.11.)

| Bereich | Stand | Folge für B |
|---|---|---|
| Box → HA, `tobibox/<box>/event` (mqtt-v1 3.4) | nicht retained, QoS 1; Arten `liste_abgelehnt`, `fehler`, `befehl_abgelehnt`; neue `art` ohne Versionserhöhung erlaubt (8). Empfänger müssen unbekannte `art` heute nicht ignorieren: HA legt sie in `box_ereignisse` ab | neue `art` `gespielt` auf demselben Thema (keine neue ACL); Handshake (3.5) verhindert, dass eine alte HA sie bekommt; mqtt-v1 8 sichert das Ignorieren neu zu |
| Box: Senden ohne Verbindung | `sende_event` verwirft; nur `unknown.json` hat einen Puffer (`outbox.py`) | eigener Puffer `gehoert.json` |
| Box: Uhr | `zeit_ok`, `zeitquelle`, `Jetzt(wall, mono, …)`, `boot_id` (Gerätestart) | Uhr-Regel 3.3 |
| Box: Wiedergabe | Kern `core.step()`, Teilautomat `session`; Pausegründe `abgehoben`, `folgenende`, `knopf`, `stumm`, `gute_nacht`, `leser_unbekannt`, `fehler`, `herunterfahren`; äußere Ereignisse und Befehle erreichen Beobachter (`status.beobachte`, `status.befehl`); `SitzungGeaendert` ist intern; `PlayerPosition` gilt je Track, jede Sekunde | Beobachter `gehoert.py` (3.1) |
| Box: Schreibbudget (data-model 1.7) | `resume.json` alle 30 s während der Wiedergabe (nur bei geändertem Zeiger), höchstens 320 je Tag | `gehoert.json` höchstens alle 2 Minuten während der Wiedergabe und je Sitzungsende (3.4) |
| HA: Ereignisse der Box | `mqtt.py` legt jede `art` in `box_ereignisse` (20 je Box), dedupliziert über `id`; `_on_online` reagiert nur auf Änderung | `gespielt` wird vorher abgenommen; Handshake über `status` (3.5) |
| HA: Reinhören | Seite ruft `hoerstelle/set` höchstens alle 10 s und sofort bei Pause, Sprung, Wechsel, Ende, Ausblenden; Grenze 30 je Minute; HA speichert nur die letzte Stelle (gerundet) | Reinhör-Sitzungen (5), Felder `spieler`, `spielt` |
| HA: Speicher | Stores `tobibox`, `tobibox.hoerstellen`, `tobibox.medieninfo`, `tobibox_eingang`; kein SQLite | SQLite-Datei, Store `tobibox.favoriten` |
| HA: Akku | Sensor per MQTT-Discovery der Box (`state_class measurement`) | Langzeitstatistik von HA |
| Seite | Start hat Reihen „Zuletzt auf den Boxen gehört“ und „Favoriten / Empfehlungen“ (leer, unsichtbar); `#gehoert` leitet ohne `gehoert` um; kein Stern; Sortierung `angehoert` = eigene Hörstellen | anschließen |
| ha-websocket-v1 | Befehle 1 bis 49; Stufe B nicht Teil des Vertrags (nennt noch `gehoert_reinhoeren`) | Befehle 50 bis 56 |

## 2. Begriffe und Zählregel (Boxen und Reinhören gleich)

| Begriff | Regel |
|---|---|
| **Quelle** (`wer`) | `box:<id>` oder `benutzer:<HA-Benutzer-ID>`. Auswahl: **Alle** (alle Quellen, Frage 28), **Alle Boxen** (die Kinder zusammen), je Box, je Person |
| **Sitzung** | zusammenhängendes Hören **einer Folge** an **einer Quelle**. Pausen bis **30 Minuten** gehören dazu (R2). Grenzen: 3.2 (Box), 5 (Reinhören) |
| **Hörzeit** (vorn, R1) | Summe der **Inhaltszeit** aus dem Fortschritt der Position: Zuwachs `dp` zwischen zwei Meldungen zählt, wenn `0 < dp`; er wird auf `2 × dt + 2` gekappt (`dt` Monotonzeit). Die Basislinie wird neu gesetzt bei Track-, Folgen- und Wiedergabe-Wechsel (`gen`) und bei `dp ≤ 0` (Rücksprung, Springen zurück); ein Sprung nach vorn über die Kappung zählt nur bis zur Kappung. Bei schnellerem Abspielen zählt die Länge des Inhalts. Jede Sitzung mit Hörzeit > 0 zählt |
| **Mal** (Nebenspalte, R1) | Sitzungen **einer Quelle** an einer Folge bilden ein Mal, wenn die vorige höchstens 30 Minuten vor dem Beginn endete **und nicht am Ende der Folge** endete. Ein Mal zählt ab 10 s Hörzeit und gehört zum Tag seines Beginns. Wiederholen nach dem Ende ist immer ein neues Mal. Sitzungen mit unbekanntem Datum sind je ein eigenes Mal |
| **fertig** | eine Sitzung, die am **Ende der Folge** endet, wenn die Hörzeit **dieser Quelle an dieser Folge seit dem letzten fertig** mindestens **80 %** der Folgendauer ist; ohne bekannte Dauer mindestens 60 s. So zählt ein Hörbuch, das in Portionen über Tage gehört wird. Box: ihr Ereignis „Folge zu Ende“; Reinhören: `fertig: true` der Seite |
| **Fertig je Hörspiel** | verschiedene, **heute vorhandene** Folgen, die im Zeitraum mindestens einmal fertig gehört wurden, von der heutigen Zahl („17/20“) |
| **Zeitraum** | Zeitzone von HA: Woche = heute und die 6 Kalendertage davor, Monat = 30, Jahr = 365 Kalendertage; Alles = seit Beginn. Eine Sitzung zählt zum Tag und zur Stunde ihres Beginns. Ungefähres Datum (3.3) zählt normal; unbekanntes Datum nur in „Alles“ und in Ranglisten |

Die Kennung des Tobies wird nie übertragen und nie gespeichert (Frage 9). **Datenschutz** (Frage 23, präzisiert): Die
**Stelle** zum Weiterhören ist privat; **dass** jemand etwas gehört hat und wie lange, sieht die Familie.

## 3. Box

### 3.1 Beobachter `gehoert.py`

Ein **reines Modul** mit eigenem Schritt (Eingang → neuer Zustand + Ausgaben), getrieben aus `app.verarbeite` wie
`status.py`. Eingänge: `ZustandMelden` (Modus, Serie, Folge, Track), die Befehle `Abspielen` (mit `gen`),
`Pausieren(grund)` und `Herunterfahren`, die Ereignisse `FolgeZuEnde` (die **beendete** Folge), `DienstEndet`, `Takt`,
`PlayerPosition` (`spielt`, `track`, `position_s`; Nachzügler mit altem `gen` werden ignoriert). Er führt höchstens
**eine offene Sitzung**: `sitzung` (UUID), Serie, Folge, `boot_id`, `beginn_boot_s`, Wanduhr-Beginn mit `zeit_ok`,
Basislinie (Track, Position, `gen`), `gehoert_s`, letzter Pausegrund, `ende_boot_s` (letzte gespielte Sekunde).
Dasselbe Modul treibt Tests und Simulator (9, B5).

### 3.2 Sitzungsgrenzen (Vorrang von oben nach unten)

| Anlass | `ende` |
|---|---|
| Gerät fährt herunter | `herunterfahren` |
| Dienst endet (Neustart der Box-Software) | `dienst_ende` |
| Beim Start liegt in `gehoert.json` eine offene Sitzung (Strom weg, Absturz) | `abbruch` |
| `FolgeZuEnde` für die laufende Folge | `ende_der_folge` |
| Erste gespielte Sekunde einer **anderen** Folge (anderer Tobie, Weiter/Zurück in eine andere Folge) | `wechsel` |
| Seit 30 Minuten keine gespielte Sekunde (jede Pause, auch `fehler`, `leser_unbekannt`, `gute_nacht`) | `pause`, `grund` = letzter Pausegrund |

Track-Wechsel in einer Ordner-Folge und Springen innerhalb der Folge beenden die Sitzung nicht. Eine Sitzung mit
Hörzeit 0 wird verworfen.

### 3.3 Uhr

Alle Dauern und Fristen rechnen auf Monotonzeit. Jede Zeile trägt `boot_id`, `beginn_boot_s`, `ende_boot_s`, die
Wanduhr `beginn` und `zeit_ok`; `ende_um` = `beginn` + (`ende_boot_s` − `beginn_boot_s`). Ist `boot_id` nicht lesbar,
erzeugt die Box eine zufällige je Dienststart. Wird die Uhr im selben Gerätestart gut, korrigiert die Box **alle**
Zeilen dieses Starts im Puffer (ein Schreibvorgang).

HA bestimmt den Beginn so:
1. `zeit_ok = true` → `beginn` der Zeile.
2. sonst, wenn die Nachricht dieselbe `boot_id` trägt wie die Zeile → Empfang − (`gesendet_boot_s` − `beginn_boot_s`).
3. sonst, wenn `beginn` nach dem 1.1.2026 und vor dem Empfang liegt → `beginn`, **ungefähr** (`datum_ungefaehr`).
4. sonst Datum **unbekannt**.

### 3.4 Puffer `gehoert.json`

- Datei im Datenordner, Muster der Zustandsdateien (`schema_version`, `schreibe_atomar`, Hintergrund-Schreiber wie
  `outbox`): `{"schema_version": 1, "verworfen": n, "offen": <Sitzung oder null>, "zeilen": [<Sitzung>, …]}`. Eine
  Sitzung hat die Felder von `gespielt` (3.6) ohne die Hüllenfelder. Eine ungültige Zeile beim Laden wird verworfen
  (Box-Protokoll), nicht die ganze Datei.
- **Ein** atomarer Schreibvorgang für: neue Zeile, Löschen quittierter Zeilen, Stand der offenen Sitzung.
- Die offene Sitzung wird höchstens alle **2 Minuten** während der Wiedergabe und beim Beginn einer Pause geschrieben
  (Verlust bei Stromausfall höchstens 2 Minuten). Beim Start wird sie zur Zeile mit `ende = abbruch`.
- Bei `herunterfahren` und `dienst_ende` schreibt die Box **synchron** (mit `fsync`), bevor abgeschaltet wird bzw. der
  Dienst endet.
- Höchstens **500 Zeilen**; darüber fallen die ältesten weg, `verworfen` zählt sie (Gesamtzahl), Box-Protokoll.
- `gehoert.json` gehört **nicht** in die Rückfall-Sicherung des Updates.
- Schreibbudget (neu in data-model 1.7): je Sitzungsende einer; während der Wiedergabe höchstens 30 je Stunde;
  Quittungen werden mit dem nächsten Schreibvorgang oder spätestens nach 10 Minuten gesammelt geschrieben.

### 3.5 Handshake, Senden, Quittung

- **Handshake über den Zustand:** Bei jedem Verbinden und bei jedem `homeassistant/status online` setzt die Box
  `status.gehoert_wartet = true` und sendet nichts. HA antwortet auf **jeden** `status` mit `gehoert_wartet = true`
  und `box_faehig` ∋ `gehoert` mit einer Quittung mit leerer Liste. Danach meldet die Box `gehoert_wartet = false` und
  sendet. Eine alte Integration antwortet nie: die Box sendet ihr nichts. Ein alter retained `status` löst höchstens
  eine überflüssige, harmlose Quittung aus.
- **Senden:** nach dem Handshake alle Zeilen, bei jedem Sitzungsende alle Zeilen, danach alle 10 Minuten, solange
  Zeilen da sind. Höchstens 20 je Sekunde. Mit jeder Nachricht `boot_id` und `gesendet_boot_s` (3.3).
- **Zwischenstand:** Läuft eine Sitzung länger als 15 Minuten und ist die Box verbunden, sendet sie alle 15 Minuten
  `gespielt` mit `ende = teilweise` (nur MQTT).
- **Quittung** (HA → Box): die Liste der `sitzung`s, die HA gespeichert hat **oder schon kannte**, auch ungültige
  (HA-Protokoll). Die Box löscht genau diese Zeilen. Nachlaufend: höchstens 2 s nach der letzten empfangenen Zeile.
  Zwischenstände werden nicht quittiert.

### 3.6 Vertrag `mqtt-v1.md` (Entwurf)

**3.3 `status`, neue Felder:** `box_faehig` (Liste von Zeichenketten, hier `["gehoert"]`; nicht zu verwechseln mit den
Fähigkeiten von `hello` in HA), `gehoert_wartet` (bool), `gehoert_verworfen` (int, Gesamtzahl aus 3.4).

**3.4 neue `art` `gespielt`**, `daten`:

| Feld | Pflicht | Typ, Grenze | Bedeutung |
|---|---|---|---|
| `boot_id` | ja | string, ≤ 64 | Gerätestart **beim Senden** |
| `gesendet_boot_s` | ja | int ≥ 0 | Monotonsekunden beim Senden |
| `sitzungen` | ja | Liste, 1 bis 20 | Sitzungen, je: |
| ↳ `sitzung` | ja | UUID | eindeutig, gleich für Zwischenstände und Abschluss |
| ↳ `serie` | ja | string ≤ 64 | Serien-ID |
| ↳ `folge` | ja | string ≤ 255 | Name der Folge (wie in `resume.json`) |
| ↳ `folge_dauer_s` | nein | int > 0 oder `null` | Länge der Folge, wenn bekannt |
| ↳ `beginn` | ja | ISO-Zeit | Wanduhr der Box |
| ↳ `zeit_ok` | ja | bool | Wanduhr vertrauenswürdig |
| ↳ `boot_id`, `beginn_boot_s`, `ende_boot_s` | ja | string, int, int | Gerätestart und Monotonzeit der Sitzung |
| ↳ `gehoert_s` | ja | int ≥ 1, ≤ `ende_boot_s − beginn_boot_s + 2` | Hörzeit (2) |
| ↳ `ende` | ja | `ende_der_folge`, `wechsel`, `pause`, `herunterfahren`, `dienst_ende`, `abbruch`, `teilweise` | |
| ↳ `grund` | nein | string | bei `pause`: letzter Pausegrund |

**3.7 neuer Befehl `gehoert_quittung`**, `daten`: `sitzungen` (Liste von UUIDs, 0 bis 100). Hülle wie jeder Befehl
(`id`, `erzeugt`, `ttl_s` 3600); `ha.py` behandelt ihn selbst, **ohne** Prüfung von Ablauf und `zeit_ok`, idempotent,
nicht in den 50 gemerkten `id`s.

**8:** Empfänger ignorieren unbekannte `art`, unbekannte Felder und unbekannte Werte in `box_faehig` (neu zugesichert).

### 3.7 Datenmodell `data-model.md` (Entwurf)

1.6: neue Zustandsdatei `gehoert.json` (Aufbau 3.4). 1.7: Schreibbudget wie 3.4. Rückfall-Sicherung: ohne
`gehoert.json`.

## 4. HA: Speicher

### 4.1 SQLite `<config>/tobibox/gehoert.sqlite`

Eine Verbindung im Executor mit `threading.Lock`, `journal_mode=TRUNCATE`, `synchronous=FULL`, Schema-Version in
`PRAGMA user_version`, Migration nur vorwärts, `PRAGMA integrity_check` beim Start ins Protokoll. Ist die Datei nicht
zu öffnen, startet die Integration ohne Fähigkeit `gehoert`.

| Tabelle | Spalten | Schlüssel und Indizes |
|---|---|---|
| `sitzungen` | `sitzung` (UUID), `quelle`, `serie`, `folge`, `folge_dauer_s`, `beginn`, `ende_um` (UTC-Sekunden), `datum` (`sicher`, `ungefaehr`, `unbekannt`), `tag`, `stunde` (Zeitzone von HA), `gehoert_s`, `ende`, `grund`, **`neues_mal`** (bool), **`fertig`** (bool) | Hauptschlüssel `sitzung`; Indizes `(quelle, serie, folge, beginn)`, `(serie, folge, beginn)`, `(tag)`, `(beginn)`, `(quelle, beginn)` |
| `technik` | `box`, `zeit`, `art` (`online`, `offline`, `lader_an`, `lader_aus`, `sync_ok`, `sync_fehler`, `fehler`, `verworfen`), `wert` | Index `(box, zeit)` |

Einfügen mit `ON CONFLICT(sitzung) DO UPDATE … WHERE alt.ende IN ('teilweise', 'verwaist')`, nie `OR REPLACE`.
Nach jedem Einfügen rechnet HA `neues_mal` und `fertig` für die Gruppe (Quelle, Serie, Folge) neu (2); nachgelieferte
Zeilen betreffen nur ihre Gruppe. Verwaiste `teilweise` schließt HA als `verwaist` (Box nach 24 h, Reinhören nach
30 Minuten). Keine Aufräumregel; einige 10 MB im Jahr. HA-Sicherungen enthalten die Hördaten (Hinweis in
`docs/betrieb/`).

### 4.2 Aufnahme

- **Box:** `gespielt` wird in `mqtt.py` **vor** `box_ereignis_hinzu` abgenommen, je Nachricht ein `COMMIT`, dann die
  Quittung (3.5). Nur bekannte Boxen. `folge_dauer_s`: Wert aus der Medieninfo von HA, sonst der der Box. `gehoert_s`
  wird auf die Schranke aus 3.6 gekappt (Protokoll).
- **Technik:** eine Zeile bei **echtem Wechsel** gegen die letzte gespeicherte Zeile je Box (`lader`, `online`,
  Sync-Ergebnis über `sync.letzter_ende`, Ereignis `fehler`, Anstieg von `gehoert_verworfen`); der erste `status` nach
  einem HA-Start wird nur verglichen. Zeit: `ts` der Box bei `zeit_ok`, sonst Empfangszeit.
- **Ändern der Bibliothek:** Verschieben und Zusammenführen schreiben `serie`/`folge` mit und rechnen die Gruppe neu;
  Umbenennen ändert nichts.
- `zuletzt_gehoert_am` je Serie und die Sortierung `meist_gehoert` kommen aus einem Zwischenspeicher, der beim Ereignis
  `gehoert` verfällt.

### 4.3 Favoriten

Store `tobibox.favoriten` für **die ganze Familie** (R3): `serie_id` oder `serie_id#folge`, `gesetzt_von`,
`gesetzt_am`; höchstens 1 000; gelöschte Einträge fallen beim Lesen weg.

## 5. HA: Reinhören als Sitzungen

- `hoerstelle/set` (Befehl 41) bekommt die optionalen Felder **`spieler`** (8–64 Zeichen `[A-Za-z0-9_-]`, zufällig je
  Player-Instanz der Seite) und **`spielt`** (bool). HA führt je (Benutzer, `spieler`) eine offene Sitzung im Speicher,
  höchstens 5 je Benutzer (die älteste wird als `wechsel` geschlossen); ohne `spieler` eine je Benutzer. Grenze 60
  Aufrufe je Minute und Benutzer. Idempotent: nein (eine Wiederholung zählt keine Hörzeit doppelt).
- Hörzeit nach 2 mit der **ungerundeten** Position aus der Eingabe (bei Ordner-Folgen mit `spuren_s` in Sekunden der
  ganzen Folge, sonst innerhalb eines Tracks). War beim letzten Aufruf `spielt = true`, zählt auch `dt > 30` (Seite
  war eingefroren, Ton lief), gekappt wie in 2.
- Ende: `fertig: true` → `ende_der_folge`; andere Folge → `wechsel`; 30 Minuten ohne Fortschritt → `pause`
  (Aufräumschleife je Minute); HA fährt herunter → `dienst_ende`. Offene Sitzungen schreibt HA alle 5 Minuten als
  `teilweise`; nach einem HA-Neustart werden sie nach 30 Minuten `verwaist`.
- Zwei Fenster mit derselben Folge zählen doppelt (so in „Was wird gezählt?“).
- **B2a vor B2:** Messung am iPhone mit gesperrtem Bildschirm (HA-App und Safari). Kommt fast nichts, steht unter
  „Was wird gezählt?“: „Am Handy mit gesperrtem Bildschirm wird nur ungefähr gezählt.“

## 6. HA: Befehle (Vertrag `ha-websocket-v1.md`, Entwurf)

| Fähigkeit | schaltet frei |
|---|---|
| `gehoert` | Befehle 50 bis 54; Unterseite `#gehoert`; Reihe „Zuletzt auf den Boxen gehört“; Sortierungen `zuletzt_gehoert`, `meist_gehoert`; Feld `zuletzt_gehoert_am`; Ereignis-Thema `gehoert`. (`gehoert_reinhoeren` entfällt) |
| `favoriten` | Befehle 55, 56; Stern; Filter und Feld `favorit`; Reihe „Favoriten“; Ereignis-Thema `favoriten` |

### 6.1 Befehl 50 `gehoert/zusammenfassung` (Recht lesen)

Eingabe:

| Feld | Pflicht | Werte |
|---|---|---|
| `wer` | nein | `alle` (Vorgabe), `alle_boxen`, `box:<id>`, `benutzer:<id>` |
| `zeitraum` | eins von beiden | `woche`, `monat`, `jahr`, `alles` |
| `von`, `bis` | eins von beiden | Datum `JJJJ-MM-TT` (Zeitzone von HA), `bis` einschließlich, höchstens 3 Jahre |
| `nach` | ja | Liste, 1 oder 2 Schlüssel aus `wer`, `serie`, `folge`, `tag`, `woche` (ISO-Woche, Montag), `monat` (Kalendermonat), `stunde` (Stunde des Tages 0–23); höchstens ein Zeitschlüssel; `folge` nur mit `serie_id` |
| `serie_id` | nein | schränkt auf einen Eintrag ein |
| `sortierung` | nein | `sekunden` (Vorgabe), `mal`; nur ohne Zeitschlüssel |
| `limit` | nein | 1–200 (Vorgabe 50), nur ohne Zeitschlüssel |

Ausgabe: `zeilen` (je Zeile die Schlüssel aus `nach` in dieser Reihenfolge, bei `serie` zusätzlich `name` und
`geloescht` (bool; alle gelöschten Serien als **eine** Zeile mit `serie = null`), dazu `sekunden`, `mal`, `fertig`; ohne
`folge` in `nach` auch `folgen_fertig`, `folgen_gesamt`); Zeitreihen lückenlos aufsteigend vom ersten bis zum letzten
Raster des Zeitraums (bei `alles` ab dem Monat der ersten Sitzung), höchstens 400 Zeilen; Gleichstand nach Name;
`summe` (`sekunden`, `mal`, `fertig`); `wer_auswahl` (Liste `{wer, name, art}` mit `art` `box` oder `person`; gelöschte
Benutzer als „Früherer Benutzer“); `zeitzone`, `von`, `bis`. Fehler `invalid_format`, `wer_ungueltig`,
`serie_nicht_gefunden`.

Beispiele der Seite: Rangliste `nach=["serie"]`; Aufteilung `serie_id`, `nach=["folge"]`; Hörzeit pro Tag
`nach=["tag"]` (bei „Alle“ die Tabelle `nach=["tag","wer"]`); Tageszeiten `nach=["stunde"]`; Jahr `nach=["woche"]`,
Alles `nach=["monat"]`.

### 6.2 Weitere Befehle

| Nr. | Befehl | Recht | Eingabe → Ausgabe |
|---|---|---|---|
| 51 | `gehoert/zuletzt` | lesen | `wer` (Vorgabe `alle_boxen`), `limit` (1–20) → `eintraege`: Serien-Kurzformen wie `serien/list` plus `wer`, `zeit` |
| 52 | `technik/verlauf` | admin | `box`, `von`, `bis` → `ladevorgaenge` (Beginn, Ende, Dauer), `laufzeiten` (je Ladung), `verbindung` (online/offline), `syncs`, `fehler`, `verworfen`. Akku-Werte liest die Seite über `recorder/statistics_during_period` mit `akku_entitaet` aus `boxen/list` (neu, `null` ohne Sensor) |
| 53 | `gehoert/exportieren` | admin | `quelle` (`boxen`, `reinhoeren`, `alle`, `box:<id>`, `benutzer:<id>`) → `pfad` (signiert, 10 Minuten, nur für den Anfragenden, geprüft auch beim Abruf über die vorhandene Ansicht für signierte Pfade). CSV UTF-8 mit BOM, Trenner `;`, Spalten `Beginn;Ende;Quelle;Serie;Folge;Hörzeit (s);Ende der Sitzung;Mal neu;fertig;Datum`; Zeiten in der Zeitzone von HA; Zellen mit führendem `=`, `+`, `-`, `@` mit `'` entschärft; Dateiname `gehoert-<quelle>-<datum>.csv` |
| 54 | `gehoert/loeschen` | admin | `quelle` (wie 53), `trocken` (bool), `bestaetigung` = `LÖSCHEN` oder `LOESCHEN` (nicht bei `trocken`) → `{anzahl}`; Zeilen, die nach `trocken` ankommen, werden mitgelöscht; Ereignis `gehoert` |
| 55 | `favorit/set` | alltag | `serie_id`, `folge` (optional), `an` → `{an}`; Fehler `serie_nicht_gefunden`, `folge_nicht_gefunden`, `zu_viele_favoriten`; Mengen wie Listen-Änderungen; Wiederholung ohne Fehler; Ereignis `favoriten` |
| 56 | `favoriten/list` | lesen | → `eintraege` (`serie_id`, `folge`, `gesetzt_von {id, name}`, `gesetzt_am`) |

`serien/list`: Sortierungen **`zuletzt_gehoert`** (nur Boxen, wie die Reihe) und **`meist_gehoert`** (Hörzeit im
letzten Jahr, alle Quellen); Filter **`favorit`**; je Serie `favorit` und `zuletzt_gehoert_am`. `folgen/list` und
`serie/get`: je Folge `favorit`; `folgen/list` Filter `favorit`. `angehoert` bleibt die eigene, private Sortierung.
Ereignis-Themen im Aufbau der vorhandenen: `gehoert` (`geaendert`, ohne Inhalt, gebündelt höchstens alle 5 s) und
`favoriten` (`geaendert` mit `serie_id`, `folge`, `an`). Befehl 41 `hoerstelle/set`: Felder `spieler`, `spielt` (5).

## 7. Seite

- **Geräte:** Zeile „Wer hat was gehört?“ → `#gehoert` (nur mit `gehoert`). Unterseite wie HA-Oberfläche 5.10 und
  5.10.1, mit diesen Änderungen: Auswahl **Alle · Alle Boxen · je Box · je Person**; Rangliste nach **Hörzeit**, Spalten
  **Hörzeit · Mal · fertig**; Diagramm-Raster Woche/Monat in Tagen, Jahr in Wochen, Alles in Monaten; ungefähre Daten
  ohne eigene Markierung; aufklappbar „Was wird gezählt?“ (Hörzeit nach Inhalt, Pausen bis 30 Minuten, „Mal“,
  „fertig“, zwei Fenster zählen doppelt, Handy ungefähr).
- **Start:** Reihen „Zuletzt auf den Boxen gehört“ (Befehl 51) und „Favoriten“ (statt „Favoriten / Empfehlungen“);
  ohne Platzhalter, leere Reihen unsichtbar, Fehler einzelner Reihen still.
- **Bibliothek:** Sortierungen „Zuletzt gehört“, „Meist gehört“; Filter „Favoriten“.
- **Stern:** Knopf im Kopf der Serienseite (`aria-pressed`, Wort im Namen); je Folge im Menü „⋯“ als Text „Zu Favoriten“ /
  „Aus Favoriten“; Meldung nach dem Setzen; in Zeilen und Kacheln ein kleiner Stern mit `aria-label` „Favorit“.
- **Player:** sendet `spieler` (einmal je Player-Instanz erzeugt) und `spielt` mit jedem `hoerstelle/set`.
- **Technik:** Box-Unterseite: Karte „Verlauf“ (Akku-Kurve 7/30 Tage, Ladevorgänge, Laufzeit je Ladung, verworfene
  Hördaten; `role="img"` und Tabelle). „Speicher und Netz“: Karte „Hördaten“ mit „Als Tabelle sichern“ und Löschen
  (erst Anzahl, dann Bestätigung mit Wort) für Boxen, Reinhören, einzelne Box oder Person.
- Begriffe für Eltern überall gleich: „Hörzeit“, „Mal“, „fertig“. Keine Erklärsätze außer „Was wird gezählt?“ (AM16).

## 8. Reste aus Stufe A in derselben Vertragsrevision

`hello.grenzen.hoerkopie_schlange`; AM24 und AM25 in 2.4; `serie/get` Hörstelle je Folge mit `track`; `serien/list`
ohne `limit` liefert alles; `einsortierung/bestaetigen` setzt `pruefen` im Eingangsprotokoll zurück, `eingang/list`
nennt Dateinamen und Zahl einer Gruppe (`concepts_brief.md` Abschnitt 6). Umsetzung in B3 (Backend) und B4 (Seite).

## 9. Pakete und Abnahmen

| AP | Inhalt | Modell |
|---|---|---|
| **B0** | Verträge: mqtt-v1 (3.3, 3.4, 3.7, 8), data-model (1.6, 1.7, Rückfall), ha-websocket-v1 (Befehle 50–56, Befehl 41, Fähigkeiten, Sortierungen, Felder, Ereignis-Themen; Reste aus A); **Freigabe Tobias** | PL |
| **B2a** | Messung am iPhone: `hoerstelle/set` bei gesperrtem Bildschirm (HA-App, Safari) | PL + Tobias |
| **B1** | Box: `gehoert.py` (rein), Grenzen 3.2, Uhr 3.3, `gehoert.json`, Handshake, Senden, Quittung, `status`-Felder, synchrones Schreiben vor dem Abschalten; Tests: Absturz, Strom weg nach `Herunterfahren`, abgeschnittene Datei, ungültige Zeile, Doppelzustellung, Überlauf, Uhrsprung, Uhr nie gut, geklonte Datei, Handshake mit alter/neuer HA, HA-Neustart | Sonnet |
| **B2** | HA: SQLite, Aufnahme mit Quittung und Handshake, `neues_mal`/`fertig` je Gruppe, Technik-Zeilen, Reinhör-Sitzungen (`spieler`, `spielt`), Favoriten-Store, Mitschreiben bei Verschieben/Zusammenführen; Tests der Zählregel (Mal, fertig 80 % über Portionen, Wiederholen, Pausen 30 min, Mitternacht, Sommerzeit, ungefähres/unbekanntes Datum, Nachlieferung, verwaist) | Sonnet |
| **B3** | HA: Befehle 50–56, Felder, Sortierungen, Filter, Ereignisse, Export, Löschen; Reste aus A (Backend); Leistung auf der echten HA gemessen (Ziel: Befehl 50 unter 300 ms bei 30 000 Zeilen) | Sonnet |
| **B4** | Seite: `#gehoert`, Reihen, Sortierungen, Filter, Stern, Technik-Karten, `spieler`/`spielt` im Player, Texte; Reste aus A (Seite); jsdom, Browser-Prüfung mit Mock-Daten | Sonnet |
| **B5** | Simulator: Box-Software am Mac als Test-Box (Konfiguration `boxsim`, R4) plus Szenario-Werkzeug mit simulierter Zeit (`--tage 40`, `--seed`; Wiederholen, Hörbuch in Portionen, Neustart, Strom weg, Überlauf, offline, Uhr nie gut) | Sonnet |
| **B6** | Abnahme mit Tobias: Mosquitto-Konto `boxsim` und Test-Box anlegen (Tobias); Reinhören am Mac und iPhone → eigene Zeile; Test-Box offline spielen, verbinden, Handshake, Quittung; Rangliste, Diagramme, „Alle Boxen“; Stern, Reihen, Sortierungen; Technik-Verlauf; Export; danach Daten der Test-Box löschen, Test-Box und Konto entfernen; Hinweis in `docs/betrieb/` | PL + Tobias |
| **B7** | Abnahme der Box-Teile an echter Hardware (wenn die Boxen gebaut sind) | PL + Tobias |

Reihenfolge: B0 → B2a → (B1 ‖ B2) → B3 → (B4 ‖ B5) → B6. Eine Reihenfolge von HA und Box beim Einspielen ist durch den
Handshake nicht nötig.

## 10. Offene Fragen für Tobias

Keine. R1 bis R4 sind entschieden; „Alle Boxen“ (B-F1) ist mit G-M12 erledigt.

## 11. Auflagen aus der Kurzprüfung (Rev. 3.1, `resolve.md` Runde 3)

- Schlüssel in `sitzungen` ist **`(quelle, sitzung)`**; ein Zwischenstand ersetzt nur Zeilen derselben Quelle.
- **Ersetzen:** Eine Endzeile (`ende` nicht `teilweise`, `abbruch`, `verwaist`) gewinnt immer; sonst die Zeile mit der
  größeren Hörzeit. `verwaist` übernimmt `ende_um` des letzten Zwischenstands.
- **Mal:** `neues_mal` trägt die erste Sitzung eines Mals, zusammen mit `mal_zaehlt` (Summe des Mals ≥ 10 s); beides
  wird beim Einfügen für die Gruppe neu gerechnet. Unbekanntes Datum: eigenes Mal; `fertig` rechnet dann in
  Eingangsreihenfolge.
- **Löschmarke:** Nach `gehoert/loeschen` verwirft HA nachgelieferte Zeilen dieser Quelle, deren `ende_um` vor der
  Löschung liegt, und quittiert sie trotzdem.
- **Handshake:** kein Zwischenstand, solange `gehoert_wartet = true`; solange die Box wartet, meldet sie `status` alle
  60 s neu. Ohne Fähigkeit `gehoert` in HA puffert die Box bis 500 Zeilen und verwirft dann die ältesten.
- **Befehl 50:** mehr als 400 Zeilen oder eine verbotene Kombination in `nach` → `invalid_format`.
- **Reinhören:** bei `dt > 30` Kappung `1,5 × dt + 2`.
