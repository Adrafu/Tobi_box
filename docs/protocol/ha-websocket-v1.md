# WebSocket- und Upload-Schnittstelle Seite ↔ HA-Backend, Version 1 (`ha-websocket-v1`, „Vertrag W“)

*   **Status:** Vertrag Stufe 3a, überarbeitet am 09.11. nach dem Goldfisch-Report
    (`docs/egm/software-prototyp/review_vertrag_w.md`, Befunde W-01 bis W-28 mit
    „Auflösung“ am Ende des Reports), mit Entscheidung M (Einsortieren nach Metadaten)
    und den Vorgaben der Projektleitung vom 09.11. (Abschnitt „Vorgaben der
    Projektleitung“ am Ende). Wartet auf die Freigabe durch Tobias.
*   **Änderung 09.11. (Entscheidung N, 09.11.):** Das Feld `lesezeichen_tage` der Konfiguration
    (Lesezeichen laufen nach so vielen Tagen ohne Benutzung ab, Vorgabe 14, `0` = nie;
    `data-model.md`, Abschnitt 2) ist **reserviert**: Das Backend schreibt es unverändert fort und
    exportiert es; die Einstellungen in Stufe 4 (`tobibox/einstellungen/get` und `set`, Abschnitt 10)
    bekommen es dazu. Eine eigene Seitenbedienung gibt es in Version 1 nicht; kein neuer Befehl,
    kein neuer Fehlercode, Version bleibt 1.
*   **Grundlage:** `docs/designs/box-software.md` (Baustein 4 „Speicher und
    Medien“, „Aktionen und Seite“, „MQTT-Schnittstelle Box ↔ HA“; D1, D2, D4,
    D5, D6; Entscheidungen D, F, H, M; CUJ 7a, 7b, 9, 10, 11, 12; AP 3.1, AP 3.2,
    AP 4.7)
*   **Gilt für:** `websocket_api.py`, `http.py`, `media.py`, `eingang.py`,
    `store.py`, `mqtt.py` der HA-Integration `tobibox` (AP 3.1) und die Seite
    `frontend/tobibox-panel.js` samt Mock (AP 3.2). Beide Seiten entstehen
    parallel und nur nach diesem Vertrag.
*   **Verwandte Verträge:** `mqtt-v1.md` (Box ↔ HA), `data-model.md`
    (`config.json`, `serie.json`, `unknown.json`, Papierkorb-Eintrag, Eingang),
    `reader-v1.md` (Format der Kennung). Auf Anweisung der Projektleitung wurden am
    09.11. **nur additiv** ergänzt: `data-model.md` (Tobie-Namen `name`,
    `serie.json` mit `folgen_info`, Papierkorb-Metadaten `meta.json`, Eingang und
    reservierte Namen) und `mqtt-v1.md` (`name` im Beispiel von `tobibox/config`).
    Wo dieser Vertrag mehr braucht, steht es unter „Offene Punkte für Tobias“.
*   **Änderung 09.11.:** Neue Befehle 24 bis 32 und Abschnitte 11 bis 13
    (Einsortieren, Namen, Zustand der Konfiguration); Upload geht in den Eingang
    (Abschnitt 5); Ereignisthema `eingang`; Papierkorb mit Serien und Metadaten;
    alle Befunde W-01 bis W-28 eingearbeitet.

Dieses Dokument ist der **einzige Vertrag** zwischen Seite und HA-Backend. Wo es
etwas nicht sagt, gilt: nicht erfinden, sondern die Projektleitung fragen.

## 1. Grundsätze

*   **Zwei Wege.** Alles außer dem Hochladen läuft über die HA-WebSocket-Schnittstelle
    (`/api/websocket`, HA-Anmeldung durch die Verbindung der HA-Oberfläche). Das
    Hochladen der Audiodateien läuft über **einen HTTP-Endpunkt** (Abschnitt 5),
    weil WebSocket-Nachrichten klein sind (Abschnitt 8).
*   **Das Backend ist der einzige Schreiber** für Zuordnungen und
    `serie.json` (D1, D2). Die Seite hält keinen eigenen Zustand, der nicht
    wieder aus den Befehlen lesbar ist (außer Ansichtseinstellungen).
*   **MQTT bleibt Verteilkanal.** Befehle, die die Konfiguration ändern, gehen in
    dieser Reihenfolge (W-06): (1) im HA-Speicher speichern (Revision + 1),
    (2) `tobibox/config` **veröffentlichen**, (3) den **Export** auf das NAS
    (`tobibox/export/`) im Hintergrund schreiben, mit Wiederholung. Das NAS kann
    also die Verteilung nie aufhalten (die Box wartet nach Entscheidung H nur 10 s
    auf die Konfiguration). Ist der Broker gerade nicht erreichbar, ist die Änderung
    trotzdem gespeichert; die Veröffentlichung wird beim Wiederverbinden nachgeholt
    (Antwortfeld `veroeffentlicht`). Ein Fehler beim Export bricht nie einen Befehl
    ab, wird aber **gemeldet** (`konfig.export_ok`, Ereignis `konfig`; Abschnitt 13).
    Solange `konfig.zustand` nicht `ok` ist, ändert kein Befehl die Konfiguration
    und die Integration veröffentlicht nichts (Abschnitt 13; ausgenommen die beiden Auswege `liste/neu_ausrollen` und `konfig/aus_export`).
*   **Medien gehen nicht über MQTT.** Befehle, die Serien, Folgen, Papierkorb oder
    den Eingang ändern, schreiben auf die NAS-Freigabe. Die Boxen holen sie mit dem
    nächsten Sync (CUJ 9); wer es eilig hat, stößt ihn mit `tobibox/box/sync` an.
    **Nicht gesynct** werden `medien/_upload/`, `medien/_papierkorb/` und der Eingang
    `tobibox/eingang/` (Entscheidung M, Abschnitt 11.1).
*   **Ein Schreibvorgang nach dem anderen.** Das Backend serialisiert alle Befehle,
    die die Konfiguration, eine `serie.json` oder den Eingang ändern: **eine Sperre
    für die Konfiguration, eine Sperre je Serie, eine Sperre für den Eingang** (W-21).
    Damit Revision und Dateien nie halb geschrieben werden und keine Verklemmung
    entsteht, gilt eine feste Reihenfolge beim Nehmen mehrerer Sperren: **Eingang,
    dann Serien (nach Serien-ID aufsteigend), dann Konfiguration**; nie umgekehrt.
    Die Seite braucht dafür keine eigene Revision zu schicken.
*   **Aktionen und `ui/*` sind keine eigene Logik** (W-10). Die HA-Aktionen der
    Integration (`services.yaml`, auch für Automationen) und die Eingaben auf
    `tobibox/<box>/ui/…` (`mqtt-v1.md`, 3.8) rufen **dieselben Backend-Funktionen**
    wie die Befehle dieses Vertrags (Sperren, Revision, Reihenfolge H, Vorgang).
    Eine Aktion hat keine Seite und damit keinen Antwortweg: Bei einer Rückfrage
    (Lernmodus, Löschen mit Tobies) gilt `ueberschreiben=false` bzw.
    `tobies_bestaetigt=false`, also Ablehnung, es sei denn, das Aktionsfeld
    (`ueberschreiben`, `tobies_bestaetigt`) ist ausdrücklich `true`.
    `ui/lernen_abbrechen` beendet den Vorgang wie `lernmodus/abbrechen`.
*   **Pfade kommen aus der Serien-Tabelle, nie aus der Eingabe** (Sicherheit). Eine
    Serien-ID, ein Folgenname oder ein Dateiname aus einer Eingabe wird nur als
    Schlüssel nachgeschlagen bzw. nach Abschnitt 12 bereinigt und nie ungeprüft in
    einen Pfad gesetzt.
*   **Namen sind Text.** Namen von Serien, Folgen, Tobies und Dateien stammen aus
    dem Dateisystem oder von Tobias. Die Seite stellt sie **nur als Text** dar,
    nie als HTML (Lit tut das von selbst). Die statischen Dateien der Seite
    (`async_register_static_paths`) verlangen in HA keine Anmeldung: Sie enthalten
    **keine Geheimnisse** (keine Passwörter, keine Adressen); alle Daten kommen über
    die angemeldeten Befehle (W-26).
*   **Sprache.** Namen von Befehlen, Feldern und Codes: ASCII, deutsch, Kleinbuchstaben
    mit `_` (wie in den anderen Verträgen). Texte in `message` und in
    `text`-Feldern: Deutsch, Klartext, für Eltern lesbar. Die Seite darf `message`
    anzeigen, **wertet aber nur `code` aus**.
*   **Format.** JSON, UTF-8. Zeitstempel wie in `data-model.md`
    (`2026-11-05T09:30:00Z`, Millisekunden nur wo angegeben). Kennungen (`uid`)
    kanonisch (`reader-v1.md`, Abschnitt 4). Unbekannte Felder in **Antworten und
    Ereignissen** ignoriert die Seite. Unbekannte Felder in **Eingaben** lehnt HA
    ab (`invalid_format`, siehe 9).
*   **Zeitbudget.** Jeder Befehl antwortet innerhalb von **10 s** (Messung am
    Backend, nicht am Netz). Was länger dauert (Prüfung der Freigabe, `ffprobe`,
    Einsortieren, Prüfsummen), läuft im Hintergrund und meldet sich als Ereignis
    (Abschnitt 4). Dateizugriffe laufen über `hass.async_add_executor_job` (Design,
    Baustein 4). Befehle, die Listen liefern (`serien/list`, `eingang/list`), lesen
    aus dem **Zwischenspeicher** der letzten Prüfung und nie frisch von der Freigabe
    (W-28); nur `serie/get` liest `serie.json` frisch.

## 2. Rechte, Idempotenz, MQTT: die Regeln

### 2.1 Wer darf was (abgeleitet)

HA prüft bei einem WebSocket-Befehl nur, dass der Nutzer **angemeldet** ist. Wer
Administrator sein muss, bestimmt allein der Dekorator `require_admin` am Befehl. Aus
dem Design folgt:

*   Es gibt nur Tobias als Benutzer (Entscheidung D). HA hat vollen Schreibzugriff
    auf `medien/`, `export/`, `eingang/` und `releases/`.
*   Schreibende Befehle ändern, was die Kinder hören (Zuordnungen), löschen Dateien
    (Papierkorb leeren), starten Befehle an die Boxen (Lernmodus, Sync, später
    Update). Das Update bringt Code auf die Boxen (nur mit gültiger Signatur, aber
    der Auslöser sollte trotzdem nicht jedem offenstehen).
*   Lesende Befehle zeigen Namen von Serien und Folgen, Kennungen und den
    Status der Boxen. Das sind keine Geheimnisse. Auch `hello` verrät Version und
    Box-Namen jedem angemeldeten Nutzer (W-27); in diesem Haushalt harmlos.

**Regel:**

| Art | Wer | Umsetzung |
|---|---|---|
| **Lesen** (`list`, `get`, `hello`, `subscribe`, `…/export_lesen`) | jeder angemeldete HA-Nutzer | kein Dekorator |
| **Schreiben und Auslösen** (alles andere, auch `medien/pruefen` und `eingang/sortieren`, weil sie `serie.json` anlegen) | **nur Administratoren** | `@websocket_api.require_admin`; Fehler `unauthorized` |
| **Upload** (HTTP) | nur Administratoren | der fertige Dekorator `homeassistant.components.http.decorators.require_admin` (W-19); HA wandelt `Unauthorized` in **401** um. Die Seite wertet in beiden Fällen (401, 403) den `code` aus. |

**Die Seite in der Seitenleiste ist nur für Administratoren** (`panel_custom`,
`require_admin=True`; Vorgabe der Projektleitung 09.11.). Das blendet die Seite für
andere Nutzer aus, **ersetzt aber keine Prüfung**: Das Backend prüft bei jedem
Aufruf selbst. Die Seite wird in `hello` mit `darf_schreiben` informiert und blendet
Knöpfe aus; das ist nur Bedienkomfort, **keine Sicherheit**.

### 2.2 Idempotenz

„Idempotent“ heißt hier: **Doppeltes Senden ändert den Endzustand nicht** und
löst keine zweite Wirkung aus (keine zweite MQTT-Nachricht, keine zweite Revision).
Die **Antwort** der zweiten Ausführung kann ein Fehlercode sein; er steht dann in
der Spalte „Doppelt gesendet“.

Befehle, die von Natur aus **nicht** idempotent sind (etwas Neues anlegen oder ein
Ereignis auslösen), nehmen ein optionales Feld **`anfrage_id`** (string, 8–64
Zeichen `[0-9A-Za-z-]`, die Seite erzeugt eine UUID je Knopfdruck). Das Backend
merkt sich die letzten **100** `anfrage_id` mit ihrer Antwort für **10 min** (nur im
Arbeitsspeicher, ein HA-Neustart vergisst sie) und liefert bei gleicher
`anfrage_id` und gleichem Befehl dieselbe Antwort erneut, **ohne** die Wirkung zu
wiederholen. Gleiche `anfrage_id` mit anderem Befehl oder anderen Feldern:
`anfrage_id_konflikt`. **Nur Erfolge werden gemerkt** (W-22): Wiederholt die Seite
nach einem Fehler (z. B. `mqtt_nicht_verbunden`) mit derselben `anfrage_id`, führt das
Backend den Befehl neu aus und liefert nicht den gemerkten Fehler.

### 2.3 Zusammenhang mit MQTT

Jeder Befehl nennt in „MQTT“, was er auslöst. Zusammengefasst:

| Wirkung auf MQTT | Befehle |
|---|---|
| veröffentlicht `tobibox/config` (retained, Revision + 1) | `zuordnung/set`, `zuordnung/remove`, `lernmodus/antwort`, Lernmodus-Zuordnung (6.2), `folge/verschieben` und `serien/zusammenfuehren` (nur wenn Tobies auf die verschobenen Folgen zeigen), später `einstellungen/set` |
| veröffentlicht `tobibox/config` mit **neuer Listen-ID** | `liste/neu_ausrollen`, `konfig/aus_export` |
| sendet `tobibox/<box>/cmd` (mit `id`, `erzeugt`, `ttl_s`) | `lernmodus/start` (`lernen`, 60 s), `lernmodus/abbrechen` (`lernen_abbrechen`, 30 s), `box/sync` (`sync`, 300 s), später `box/update` (`update`, 300 s) |
| sendet `tobibox/<box>/unknown/<uid>/ack` | der Lernmodus (6.2: `zugeordnet`, `abgelehnt`). Die Bestätigung beim ersten Eintreffen einer Kennung (`neu`, `bekannt`) ist **Sache des Backends allein**, kein Befehl der Seite (`mqtt-v1.md`, 3.6). |
| nichts | alle übrigen (Medien, Eingang, Papierkorb, Lesen, Verwerfen) |

Die **Reihenfolge** „erst Konfiguration, dann `ack`“ (Entscheidung H, 07.11.;
`mqtt-v1.md`, 4.2) gilt für jeden Weg, der eine Zuordnung schreibt und danach
bestätigt, und zwar **erst nach dem PUBACK** der Konfiguration (6.2, Schritt 4).

## 3. Befehle

Alle Befehle heißen `tobibox/…`. Die HA-Nachricht ist `{"id": <int>, "type":
"tobibox/…", …Felder}`; die Antwort `{"id", "type": "result", "success": true,
"result": …}` oder `{"id", "type": "result", "success": false, "error": {"code",
"message"}}` (Format von HA). **„Ausgabe“ unten ist der Inhalt von `result`.**
Pflichtfelder sind fett. Fehlercodes: Tabelle in Abschnitt 7.

### Übersicht

| Nr. | Befehl | Rechte | Idempotent | MQTT |
|---|---|---|---|---|
| 1 | `tobibox/hello` | alle | ja | – |
| 2 | `tobibox/subscribe` | alle | ja (je Abo neu) | – |
| 3 | `tobibox/serien/list` | alle | ja | – |
| 4 | `tobibox/serie/get` | alle | ja | – |
| 5 | `tobibox/serie/create` | Admin | mit `anfrage_id` | – |
| 6 | `tobibox/serie/rename` | Admin | ja | – |
| 7 | `tobibox/folgen/order` | Admin | ja | – |
| 8 | `tobibox/folge/delete` | Admin | ja (Endzustand) | – |
| 9 | `tobibox/medien/pruefen` | Admin | ja | – |
| 10 | `tobibox/papierkorb/list` | alle | ja | – |
| 11 | `tobibox/papierkorb/restore` | Admin | ja (Endzustand) | – |
| 12 | `tobibox/papierkorb/empty` | Admin | ja | – |
| 13 | `tobibox/neue_tobies/list` | alle | ja | – |
| 14 | `tobibox/neue_tobies/verwerfen` | Admin | ja | – |
| 15 | `tobibox/zuordnung/list` | alle | ja | – |
| 16 | `tobibox/zuordnung/set` | Admin | ja | `tobibox/config` |
| 17 | `tobibox/zuordnung/remove` | Admin | ja | `tobibox/config` |
| 18 | `tobibox/lernmodus/start` | Admin | mit `anfrage_id` | `…/cmd` `lernen` |
| 19 | `tobibox/lernmodus/antwort` | Admin | ja (Endzustand) | `tobibox/config`, dann `…/ack` |
| 20 | `tobibox/lernmodus/abbrechen` | Admin | ja | `…/cmd` `lernen_abbrechen` |
| 21 | `tobibox/boxen/list` | alle | ja | – |
| 22 | `tobibox/box/sync` | Admin | mit `anfrage_id` | `…/cmd` `sync` |
| 23 | `tobibox/liste/neu_ausrollen` | Admin | mit `anfrage_id` | `tobibox/config` (neue Listen-ID) |
| 24 | `tobibox/serie/delete` | Admin | ja (Endzustand) | – |
| 25 | `tobibox/folge/rename` | Admin | ja | – |
| 26 | `tobibox/folge/verschieben` | Admin | ja (Endzustand) | `tobibox/config` (nur bei betroffenen Tobies) |
| 27 | `tobibox/serien/zusammenfuehren` | Admin | ja (Endzustand) | `tobibox/config` (nur bei betroffenen Tobies) |
| 28 | `tobibox/einsortierung/bestaetigen` | Admin | ja | – |
| 29 | `tobibox/eingang/list` | alle | ja | – |
| 30 | `tobibox/eingang/sortieren` | Admin | ja | – |
| 31 | `tobibox/konfig/export_lesen` | alle | ja | – |
| 32 | `tobibox/konfig/aus_export` | Admin | mit `anfrage_id` | `tobibox/config` (neue Listen-ID) |

Dazu der HA-eigene Befehl `unsubscribe_events` zum Beenden eines Abos (Abschnitt 4).
**Reserviert** für später (Namen sind vergeben, der Inhalt kommt in der jeweiligen
Stufe): Abschnitt 10.

### Gemeinsame Objekte

**Ziel** (wie `ziel` in `config.json`, `data-model.md`, Abschnitt 2):

```json
{ "typ": "serie", "serie": "3f9a1c07b2d4" }
{ "typ": "folge", "serie": "8c21d5e9a0b7", "folge": "folge-03.mp3" }
{ "typ": "aktion", "aktion": "status" }
```

**Konfig-Stand** (`konfig`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `revision` | int | wie in `tobibox/config` |
| `liste_id` | string | wie in `tobibox/config` |
| `zustand` | `ok`, `leer_neu`, `export_neuer` | Zustand der Konfiguration (Abschnitt 13). Nur bei `ok` verteilt die Integration etwas. |
| `export_ok` | bool | der Export auf das NAS entspricht dem Stand im HA-Speicher (W-06) |
| `export_geschrieben_am` | string oder `null` | wann der Export zuletzt geschrieben wurde |

Nur `revision` und `liste_id` stehen auch in der MQTT-Nachricht; die anderen Felder
sind Zustand in HA. Im Zustand `leer_neu` sind `revision` und `liste_id` `null`.

**Tobie-Kurzform** (`betroffene_tobies`, `tobies`, `zuordnungen`):
`{"uid": <string>, "name": <string oder null>}` (`name`: Tobie-Name aus der
Zuordnung, `data-model.md`, Abschnitt 2).

**Serie-Kurzform** (`serien/list`, `serie/create`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | string | Serien-ID (`serie.json`) |
| `name` | string | Anzeigename |
| `typ` | `normal` oder `ueberraschung` | wie in `serie.json` |
| `ordner` | string | Ordnername auf der Freigabe (nur zur Anzeige) |
| `anzahl_folgen` | int | Länge von `folgen` |
| `anzahl_tobies` | int | Tobies, deren `ziel` auf diese Serie zeigt (`serie` und `folge`) |
| `angelegt_am` | string | Zeitstempel |
| `stand` | string | Fingerabdruck von `name`, `folgen` und `folgen_info` (16 Zeichen `[0-9a-f]`); ändert sich auch, wenn jemand `serie.json` von außen ändert |
| `pruefen` | bool | die Serie selbst ist „bitte prüfen“ (Abschnitt 11.9) |
| `anzahl_pruefen` | int | Folgen dieser Serie mit „bitte prüfen“ |
| `hinweise` | array | Hinweise zu dieser Serie, siehe unten |

**Hinweis** (`hinweise[]`): `{"code": <string>, "folge": <string oder null>, "text": <string>}`.
Codes in Version 1: `datei_fehlt` (Name steht in `folgen`, Datei fehlt; die Integration
nimmt ihn beim nächsten Prüfen heraus), `kopierschutz` (D5, Codec `drms`),
`nicht_lesbar` (`ffprobe` öffnet die Datei nicht), `probedekodierung_fehlgeschlagen`,
`pruefung_nicht_moeglich` (`ffprobe` fehlt), `doppelte_id_korrigiert` (die
Integration hat dieser jüngeren Kopie eine neue ID gegeben, `data-model.md`,
Abschnitt 5), `serie_json_ungueltig_repariert`, `reservierter_ordner` (ein Ordner mit
reserviertem Namen liegt in `medien/`, Abschnitt 12). Unbekannte Codes zeigt die Seite
mit `text`. Die Hinweise zu Dateien, die **von außen** in einen Serien-Ordner kamen,
bleiben wie in Version 1 von der Prüfung (`medien/pruefen`) bestimmt; für Dateien
im Eingang gilt Abschnitt 11.10.

### 3.1 Allgemein

#### 1. `tobibox/hello`

Erster Aufruf der Seite nach dem Laden. Prüft die Vertragsversion und liefert, was
die Seite zum Start braucht.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `v` | int | ja | Vertragsversion, die die Seite kennt (hier `1`) |

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `v` | int | Vertragsversion des Backends |
| `version` | string | Version der Integration (`manifest.json`) |
| `darf_schreiben` | bool | der angemeldete Nutzer ist Administrator |
| `faehigkeiten` | array von string | was das Backend kann; Version 1 (Stufe 3a): `medien`, `upload`, `zuordnung`, `tobie_namen`, `neue_tobies`, `lernmodus`, `boxen`, `papierkorb`, `liste_ausrollen`, `konfig_export`, `sync`, `eingang`, `korrektur`, `serie_loeschen`. Spätere Stufen ergänzen `update` (3b) und `einstellungen` (4). Die Seite zeigt nur, was hier steht. |
| `boxen` | array von string | die eingerichteten Box-Namen (aus der Einrichtung der Integration) |
| `konfig` | object | Konfig-Stand mit `zustand`. Ist `zustand` nicht `ok`, zeigt die Seite zuerst die Warnung aus Abschnitt 13 und sperrt Änderungen der Konfiguration. |
| `grenzen` | object | `upload_max_bytes` (Vorgabe 524288000 = 500 MiB, einstellbar), `upload_block_bytes`, `upload_parallel` (2), `endungen` (array), `serie_name_max` (100), `folge_anzeige_max` (200), `tobie_name_max` (60), `name_max_bytes` (255), `limit_max` (100 bzw. 200, je Befehl) |

Fehler: keine außer den allgemeinen. Ist `v` der Seite **größer** als das Backend
kennt, antwortet das Backend trotzdem mit seinem `v`; die Seite entscheidet
(Abschnitt 9). Rechte: alle. Idempotent: ja. MQTT: –.

#### 2. `tobibox/subscribe`

Abonniert Ereignisse (Abschnitt 4). Ein Abo je Seite genügt.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `themen` | array von string | nein | Teilmenge von `boxen`, `neue_tobies`, `lernmodus`, `medien`, `eingang`, `konfig`, `upload`; Vorgabe: alle |

Ausgabe: `null` (HA-Muster). Danach kommen die Ereignisse als `{"id": <id des Abos>,
"type": "event", "event": {…}}`. Direkt nach der Antwort sendet das Backend je
Thema ein Ereignis mit `art="snapshot"` (Abschnitt 4). Beenden: HA-Befehl
`unsubscribe_events` mit `subscription` = `id` des Abos. Rechte: alle.
Idempotent: jedes Abo ist unabhängig; zweimal abonnieren heißt doppelte
Ereignisse. MQTT: –.

### 3.2 Serien und Folgen

#### 3. `tobibox/serien/list`

Keine Eingabe. Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `serien` | array von Serie-Kurzform | sortiert nach Name (natürliche Sortierung, `data-model.md`, Abschnitt 5) |
| `ueberraschung` | `"ok"`, `"fehlt"`, `"mehrere"` oder `"leer"` | Zustand der Überraschungs-Serie (Box spielt sonst Fehlerton, `data-model.md`, Abschnitt 5). Bei `fehlt` bietet die Seite „Überraschungs-Serie anlegen“ (`serie/create` mit `typ="ueberraschung"`). |
| `geprueft_am` | string oder `null` | wann die Integration die Freigabe zuletzt geprüft hat |
| `pruefung_laeuft` | bool | eine Prüfung läuft gerade |
| `hinweise` | array | **(09.11., Befund AP 3.1, additiv)** Hinweise, die zu keiner Serie gehören: je reserviertem Ordner in `medien/` (Abschnitt 12) ein Objekt `{"code": "reservierter_ordner", "folge": <Ordnername>, "text": <Text>}` (`folge` trägt hier den Ordnernamen). Leer, wenn es keinen gibt. Die Systemordner `_upload` und `_papierkorb` stehen nicht darin. |

Die Antwort kommt aus dem **Zwischenspeicher** der letzten Prüfung (W-28); `geprueft_am`
zeigt sein Alter. Das Backend liest für diesen Befehl keine `serie.json` frisch von
der Freigabe. Fehler: `medien_nicht_erreichbar` (nur, wenn noch nie geprüft wurde).
Rechte: alle. Idempotent: ja. MQTT: –.

#### 4. `tobibox/serie/get`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | Serien-ID |

Liest `serie.json` frisch. Ausgabe: die Felder der Serie-Kurzform und dazu

| Feld | Typ | Bedeutung |
|---|---|---|
| `folgen` | array | in der maßgeblichen Reihenfolge (`serie.json`), Objekte siehe unten |
| `zuordnungen` | array von Tobie-Kurzform | Tobies, die auf die **ganze Serie** zeigen (Folgen-Tobies stehen bei der Folge) |

Folge-Objekt:

| Feld | Typ | Bedeutung |
|---|---|---|
| `name` | string | Dateiname oder Ordnername (Schlüssel, `data-model.md`, 1.1). Er ändert sich nie durch Umbenennen. |
| `anzeige` | string | Anzeigename: `folgen_info.<name>.anzeige`, sonst der `name` ohne Endung |
| `nummer` | int oder `null` | Folgen-Nummer (aus den Tags oder dem Albumnamen, Abschnitt 11) |
| `datum` | string oder `null` | Erscheinungsdatum `YYYY-MM-DD` |
| `art` | `datei` oder `ordner` | Datei im Serien-Ordner oder Unterordner mit mehreren Tracks (Entscheidung F) |
| `tracks` | int ≥ 1 | Anzahl Tracks (`datei`: 1) |
| `groesse_bytes` | int | Summe der Dateigrößen |
| `pruefung` | `ok`, `warnung`, `nicht_geprueft`, `nicht_moeglich` | Ergebnis der Prüfung nach D5 |
| `hinweis` | string oder `null` | Code aus der Hinweisliste, bei `warnung` |
| `pruefen` | bool | „bitte prüfen“ (Abschnitt 11.9) |
| `pruefen_gruende` | array von string | Codes aus 11.9, leer wenn `pruefen=false` |
| `tobies` | array von Tobie-Kurzform | Tobies, deren `ziel` genau auf diese Folge zeigt |

Fehler: `serie_nicht_gefunden`, `medien_nicht_erreichbar`. Rechte: alle.
Idempotent: ja. MQTT: –.

#### 5. `tobibox/serie/create`

Legt eine neue Serie an (Ordner + `serie.json` mit neuer zufälliger ID, `angelegt_am`
jetzt, `folgen` leer; D2, D4).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `name` | string, 1–100 Zeichen | **ja** | Anzeigename; nach dem Abschneiden von Leerraum nicht leer |
| `typ` | `normal` oder `ueberraschung` | nein | Vorgabe `normal`. `ueberraschung` nur, wenn es noch keine gibt (`ueberraschung_existiert`). Die Seite bietet es an, wenn `serien/list` `ueberraschung="fehlt"` meldet. |
| `anfrage_id` | string | nein | siehe 2.2 |

Der **Ordnername** entsteht aus dem Namen nach den Namensregeln (Abschnitt 12); gibt
es den Ordner schon (ohne Rücksicht auf Groß-/Kleinschreibung), hängt das Backend
` (2)`, ` (3)` … an. Der Ordnername ist **nicht** die ID (die ID ist zufällig); er
ändert sich später nie, auch nicht beim Umbenennen.

Ausgabe: `{"serie": <Serie-Kurzform>}`. Fehler: `name_ungueltig`,
`ueberraschung_existiert`, `medien_nicht_erreichbar`, `medien_schreibfehler`,
`anfrage_id_konflikt`. Rechte: Admin. Idempotent: **nicht** ohne `anfrage_id` (zweimal
gesendet gibt zwei Serien); mit gleicher `anfrage_id` nur einmal. MQTT: –. Die Boxen
sehen die Serie nach dem nächsten Sync.

#### 6. `tobibox/serie/rename`

Ändert den **Anzeigenamen** `name` in `serie.json` (Vorgabe der Projektleitung 09.11.).
Die ID und der Ordnername bleiben; Zuordnungen und Zeiger bleiben deshalb gültig,
es geht nie ein Zeiger verloren. Löscht das Kennzeichen `pruefen` der Serie.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `name` | string, 1–100 Zeichen | **ja** | neuer Anzeigename |

Ausgabe: `{"serie": <Serie-Kurzform>}`. Fehler: `serie_nicht_gefunden`,
`name_ungueltig`, `medien_schreibfehler`. Rechte: Admin. Idempotent: ja (gleicher
Name: nichts geschrieben). MQTT: –. Nebenwirkung: Die Box zeigt den neuen Namen im
Status (`serie.name`) und in der Auswahl `lern_serie` erst nach dem Sync
(`mqtt-v1.md`, 6.2).

#### 7. `tobibox/folgen/order`

Setzt die Reihenfolge der Folgen (die Seite sortiert per Ziehen und schickt die
**ganze Liste**).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folgen` | array von string | **ja** | alle Namen der Folgen (`name`, nicht `anzeige`) in der neuen Reihenfolge |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** (W-12) | `stand` aus `serie/get`. Stimmt er nicht mehr (jemand hat `serie.json` oder den Ordner von außen geändert), lehnt das Backend ab (`stand_veraltet`) und die Seite lädt neu. Ohne `stand` gilt „letzter Schreiber gewinnt“; das ist nur für Aktionen und Automationen gedacht. |

Die Liste muss eine **Umstellung** der aktuellen Liste sein: dieselben Namen, ohne
Doppelte, nichts fehlt, nichts kommt dazu. Sonst `reihenfolge_ungueltig`.

Ausgabe: `{"serie": <Serie-Kurzform>}` (mit neuem `stand`). Fehler:
`serie_nicht_gefunden`, `reihenfolge_ungueltig`, `stand_veraltet`,
`medien_schreibfehler`. Rechte: Admin. Idempotent: ja. MQTT: –. Nebenwirkung: Die
Box spielt die neue Reihenfolge nach dem Sync; der Zeiger einer Serie (Folge als
Name) bleibt gültig (`data-model.md`, Abschnitt 3).

#### 8. `tobibox/folge/delete`

Verschiebt eine Folge (Datei oder Folgen-Ordner) in den Papierkorb und nimmt sie
aus `folgen` und `folgen_info`. Nie endgültig (Design: „Löschen verschiebt in `_papierkorb/`“).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folge` | string | **ja** | Name der Folge |
| `tobies_bestaetigt` | bool | nein | Vorgabe `false`. Zeigen Tobies auf die Folge, lehnt das Backend ohne `true` ab (`tobies_betroffen`). Die Seite fragt Tobias mit Anzahl und **Namen** der Tobies (aus `serie/get`, Feld `tobies`) und sendet erneut mit `true` (Vorgabe der Projektleitung 09.11.). |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** | wie bei `folgen/order` |

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `eintrag` | object | Papierkorb-Eintrag (siehe 3.3) |
| `betroffene_tobies` | array von Tobie-Kurzform | Tobies mit `ziel.typ="folge"` auf diese Folge. Ihre Zuordnung **bleibt unverändert** (Revision wird nicht erhöht); die Box spielt für sie die Überraschungs-Serie (`folge_fehlt`), bis die Folge zurück ist (`data-model.md`, Abschnitt 2). Die Seite zeigt den Hinweis. |

Fehler: `serie_nicht_gefunden`, `folge_nicht_gefunden`, `tobies_betroffen`,
`stand_veraltet`, `medien_schreibfehler`. Rechte: Admin. Idempotent: Endzustand ja;
der zweite Aufruf liefert `folge_nicht_gefunden`. MQTT: –. Nebenwirkung: Die Box
löscht ihre Kopie beim nächsten Sync (`--delete`, mit Schutz).

#### 9. `tobibox/medien/pruefen`

Stößt die Prüfung der Freigabe an (Design: „beim Öffnen der Seite und alle
10 min“): neue Ordner (→ `serie.json` mit neuer ID, Ordnername als Name; für
Ordner ohne Datei die ID = Ordnername, damit Zeiger und Zuordnungen erhalten bleiben
(`data-model.md`, Abschnitt 5; ist der Ordnername als ID ungültig, eine neue zufällige ID)
(09.11., Befund AP 3.1), neue Dateien und
neue Folgen-Ordner (→ hinten an `folgen`), fehlende Dateien (→ heraus, Hinweis),
doppelte Serien-IDs (→ jüngere Kopie bekommt neue ID), Format- und Kopierschutz-
Prüfung neuer Dateien (D5). Das gilt für Dateien, die **von außen direkt in einen
Serien-Ordner** kamen (z. B. vom PC); sie werden wie in Version 1 aufgenommen und bei
Kopierschutz mit `pruefung="warnung"` markiert. Die Prüfung ignoriert die reservierten
Ordner (Abschnitt 12: `_…`, `eingang`). Der Eingang ist **nicht** Teil dieser
Prüfung; ihn bearbeitet `eingang/sortieren` (Nr. 30), und der 10-min-Timer ruft
beide nacheinander auf.

Keine Eingabe. Ausgabe: `{"gestartet": <bool>, "laeuft_bereits": <bool>}`. Die
Prüfung selbst läuft im Hintergrund; ihr Ende kommt als Ereignis `medien` mit
`art="pruefung_fertig"` (4.4). Läuft schon eine Prüfung (Timer oder anderer Nutzer),
meldet der Befehl `laeuft_bereits=true` und startet keine zweite.

Fehler: `medien_nicht_erreichbar`. Rechte: Admin (weil sie `serie.json` schreibt;
die Timer-Prüfung läuft unabhängig davon). Idempotent: ja. MQTT: –.

#### 24. `tobibox/serie/delete`

Verschiebt eine **ganze Serie** (Ordner mit `serie.json`, Dateien und Folgen-Ordnern)
in den Papierkorb (Vorgabe der Projektleitung 09.11.). Nie endgültig.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `tobies_bestaetigt` | bool | nein | Vorgabe `false`. Zeigen Tobies auf die Serie oder auf eine ihrer Folgen, lehnt das Backend ohne `true` ab (`tobies_betroffen`). Die Seite fragt mit Anzahl und Namen (`serie/get`: `zuordnungen` und `tobies` der Folgen). |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** | wie bei `folgen/order` |

Ausgabe: `{"eintrag": <Papierkorb-Eintrag, typ "serie">, "betroffene_tobies": [<Tobie-Kurzform>…],
"ueberraschung": <wie bei serien/list, nach dem Löschen>}`. Die Zuordnungen **bleiben**
(keine neue Revision); die Box spielt bis zur Wiederherstellung die Überraschung
(`serie_fehlt`, `folge_fehlt`). Wird die Überraschungs-Serie gelöscht, meldet
`ueberraschung="fehlt"` das.

Fehler: `serie_nicht_gefunden`, `tobies_betroffen`, `stand_veraltet`,
`medien_nicht_erreichbar`, `medien_schreibfehler`. Rechte: Admin. Idempotent:
Endzustand ja; der zweite Aufruf liefert `serie_nicht_gefunden`. MQTT: –.
Nebenwirkung: Die Box löscht ihre Kopie beim nächsten Sync (`--delete`, mit Schutz
bei mehr als 20 % Löschungen, AP 3.4).

#### 25. `tobibox/folge/rename`

Ändert nur den **Anzeigenamen** einer Folge (`folgen_info.<name>.anzeige` in
`serie.json`; Vorgabe der Projektleitung 09.11.). Der Dateiname oder Ordnername
(der Schlüssel) bleibt; Zuordnungen (`ziel.folge`) und Zeiger bleiben gültig, es geht
nie ein Zeiger verloren. Löscht das Kennzeichen `pruefen` dieser Folge.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folge` | string | **ja** | Name (Schlüssel) der Folge |
| `name` | string, 1–200 Zeichen | **ja** | neuer Anzeigename |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** | wie bei `folgen/order` |

Ausgabe: `{"serie": <Serie-Kurzform>, "folge": <Folge-Objekt>}`. Fehler:
`serie_nicht_gefunden`, `folge_nicht_gefunden`, `name_ungueltig`, `stand_veraltet`,
`medien_schreibfehler`. Rechte: Admin. Idempotent: ja (gleicher Name: nichts
geschrieben). MQTT: –.

#### 26. `tobibox/folge/verschieben`

Verschiebt eine Folge in eine **andere Serie** (Korrektur nach dem Einsortieren,
Entscheidung M). Die Dateien wechseln den Serien-Ordner (Umbenennen auf derselben
Freigabe), `folgen` und `folgen_info` beider Serien werden fortgeschrieben, die Folge
wird nach der Regel aus 11.6 in die Zielserie eingefügt.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | bisherige Serie |
| `folge` | string | **ja** | Name der Folge |
| `ziel_serie_id` | string | **ja** | neue Serie (darf die Überraschungs-Serie sein; nicht dieselbe wie `serie_id`: `ziel_ungueltig`) |
| `tobies_bestaetigt` | bool | nein | Vorgabe `false`. Zeigen Tobies auf diese Folge (`ziel.typ="folge"`), lehnt das Backend ohne `true` ab (`tobies_betroffen`). |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** | `stand` der bisherigen Serie |

Gibt es im Zielordner schon eine Datei oder einen Ordner gleichen Namens (ohne
Rücksicht auf Groß-/Kleinschreibung), erhält die Folge ein Suffix (Abschnitt 12); der
neue Name steht in der Ausgabe.

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `quelle`, `ziel` | Serie-Kurzform | beide Serien nach dem Verschieben |
| `folge` | string | Name der Folge in der Zielserie (kann vom alten Namen abweichen) |
| `betroffene_tobies` | array von Tobie-Kurzform | Folgen-Tobies, deren `ziel` umgeschrieben wurde (`ziel.serie` und gegebenenfalls `ziel.folge`) |
| `konfig` | object oder `null` | Konfig-Stand, wenn die Konfiguration geändert wurde (Revision + 1), sonst `null` |
| `veroeffentlicht` | bool oder `null` | wie bei `zuordnung/set`; `null` ohne Konfigurationsänderung |

**Zeiger:** Der Zeiger der Folge auf den Boxen (`resume.json`, je Serie und Folge)
gehört zur alten Serie. Die betroffenen Folgen-Tobies beginnen auf den Boxen nach dem
Sync **von vorn**. Das sagt die Seite in der Rückfrage (offener Punkt 3).

Reihenfolge der Schritte (Sperren nach Abschnitt 1: beide Serien nach Serien-ID, dann
Konfiguration): (1) Dateien in den Zielordner verschieben, (2) `serie.json` der
Zielserie schreiben, (3) `serie.json` der bisherigen Serie schreiben, (4) falls Tobies
betroffen: Konfiguration ändern, veröffentlichen, exportieren. Bricht es nach (1) ab,
findet die nächste Prüfung die Folge im Zielordner und trägt sie hinten ein; es geht
nichts verloren.

Fehler: `serie_nicht_gefunden`, `folge_nicht_gefunden`, `ziel_ungueltig`,
`tobies_betroffen`, `stand_veraltet`, `konfig_nicht_bereit` (Tobies betroffen, aber
`konfig.zustand` nicht `ok`; dann wird nichts verschoben), `medien_schreibfehler`.
Rechte: Admin. Idempotent: Endzustand ja; der zweite Aufruf liefert
`folge_nicht_gefunden`. MQTT: `tobibox/config` (Revision + 1) nur bei betroffenen
Tobies.

#### 27. `tobibox/serien/zusammenfuehren`

Führt zwei Serien zu einer zusammen (Korrektur, Entscheidung M): Alle Folgen der
Quellserie gehen in die Zielserie, die Quellserie (dann leer) geht in den Papierkorb.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `quelle_id` | string | **ja** | diese Serie geht auf |
| `ziel_id` | string | **ja** | diese Serie bleibt. Beide müssen `typ="normal"` sein, sonst `ziel_ungueltig`; gleiche Serie: `ziel_ungueltig`. |
| `tobies_bestaetigt` | bool | nein | Vorgabe `false`. Zeigen Tobies auf die Quellserie oder eine ihrer Folgen, lehnt das Backend ohne `true` ab (`tobies_betroffen`). |
| `stand_quelle`, `stand_ziel` | string | nein im Schema, **die Seite muss sie senden** | |

Die Folgen der Quelle werden einzeln nach der Regel aus 11.6 in die Zielserie
eingefügt, mit Suffix bei Namensgleichheit (Abschnitt 12). Alle Tobies, die auf die
Quellserie zeigen (`serie` und `folge`), zeigen danach auf die Zielserie
(`ziel.serie` und gegebenenfalls `ziel.folge` werden umgeschrieben). Deren Zeiger auf
den Boxen beginnen von vorn (wie bei Nr. 26).

Ausgabe: `{"ziel": <Serie-Kurzform>, "verschoben": <int>, "umbenannt": [{"von", "nach"}…],
"betroffene_tobies": […], "eintrag": <Papierkorb-Eintrag der Quellserie>, "konfig": …,
"veroeffentlicht": …}` (wie bei Nr. 26). Fehler: wie Nr. 26 mit `serie_nicht_gefunden`.
Rechte: Admin. Idempotent: Endzustand ja; der zweite Aufruf liefert
`serie_nicht_gefunden`. MQTT: `tobibox/config` nur bei betroffenen Tobies.

#### 28. `tobibox/einsortierung/bestaetigen`

Nimmt das Kennzeichen „bitte prüfen“ (Abschnitt 11.9) weg: Tobias hat hingeschaut.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folgen` | array von string | nein | nur diese Folgen (Namen); ohne das Feld: die Serie selbst und alle ihre Folgen |

Ausgabe: `{"serie": <Serie-Kurzform>}`. Fehler: `serie_nicht_gefunden`,
`folge_nicht_gefunden`, `medien_schreibfehler`. Rechte: Admin. Idempotent: ja.
MQTT: –. Auch `serie/rename`, `folge/rename` und `folge/verschieben` löschen das
Kennzeichen des Objekts, das sie ändern; `folgen/order` tut es nicht.

### 3.3 Papierkorb

**Papierkorb-Eintrag** (`eintrag`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | string | Kennung des Eintrags (12 Zeichen `[0-9a-f]`, vom Backend erzeugt) |
| `typ` | `folge`, `serie` oder `eingang` | was gelöscht wurde: eine Folge, eine ganze Serie oder etwas aus dem Eingang (Doppelte, Reste, Abschnitt 11.10) |
| `serie_id` | string oder `null` | Serie, aus der es kam (`null` bei `eingang`) |
| `serie_name` | string oder `null` | Name der Serie zum Zeitpunkt des Löschens |
| `folge` | string oder `null` | Name der Folge (bei `typ="folge"`) |
| `anzeige` | string | Anzeigename der Folge bzw. der Serie bzw. der Name im Eingang |
| `art` | `datei` oder `ordner` | |
| `tracks` | int | Anzahl Dateien |
| `groesse_bytes` | int | |
| `grund` | `manuell`, `zusammengefuehrt`, `doppelt`, `eingang_rest` | Wie es in den Papierkorb kam |
| `geloescht_am` | string | Zeitstempel |

Der Papierkorb liegt auf der Freigabe unter `medien/_papierkorb/`. Die Boxen
übernehmen ihn nicht (vom Sync ausgenommen). **Aufbau (W-18):** Je Eintrag ein Ordner
`_papierkorb/<id>/` mit der Datei `meta.json` (Herkunft, Reihenfolge, `folgen_info`;
Format in `data-model.md`, Abschnitt 9) und dem Ordner `inhalt/` mit dem Gelöschten
unter seinem ursprünglichen Namen. Weil die `<id>` der Ordner ist, kollidieren zwei
Löschungen gleichnamiger Folgen nie. Das Verschieben ist ein Umbenennen auf derselben
Freigabe (atomar); `restore` baut ausschließlich auf `meta.json` auf.

#### 10. `tobibox/papierkorb/list`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `limit` | int 1–200 | nein | Vorgabe 100 |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe: `{"eintraege": [<Eintrag>…], "gesamt": <int>, "gesamt_bytes": <int>}`,
neueste zuerst. Fehler: `medien_nicht_erreichbar`. Rechte: alle. Idempotent: ja.
MQTT: –.

#### 11. `tobibox/papierkorb/restore`

Stellt einen Eintrag wieder her.

*   `typ="folge"`: Die Folge kommt an ihren Platz im Serien-Ordner zurück, **hinten**
    in `folgen` (die alte Position wird nicht gemerkt); `folgen_info` kommt aus
    `meta.json` zurück.
*   `typ="serie"`: Der Serien-Ordner kommt zurück (unter dem alten Ordnernamen, bei
    Namensgleichheit mit Suffix nach Abschnitt 12; die Serien-ID bleibt).
*   `typ="eingang"`: Es kommt in den Eingang zurück (oberste Ebene, bei Namensgleichheit
    mit Suffix) und wird beim nächsten Durchlauf wieder einsortiert.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `eintrag_id` | string | **ja** | |
| `serie_id` | string | nein | nur bei `typ="folge"`: in diese Serie statt in die ursprüngliche wiederherstellen (wenn die ursprüngliche nicht mehr da ist) |

Ausgabe: `{"serie": <Serie-Kurzform oder null>, "folge": <Folge-Name oder null>}`
(`null` bei `typ="eingang"`). Fehler:
`eintrag_nicht_gefunden`, `serie_nicht_gefunden` (die Serie gibt es nicht mehr),
`serie_existiert` (`typ="serie"`: die Serien-ID ist schon vergeben),
`datei_existiert` (`typ="folge"`: im Serien-Ordner liegt inzwischen eine Folge mit
demselben Namen), `medien_schreibfehler`. Rechte: Admin. Idempotent: Endzustand ja; der
zweite Aufruf liefert `eintrag_nicht_gefunden`. MQTT: –. Nebenwirkung: Zuordnungen, die
auf die Folge oder Serie zeigten, gelten wieder, sobald die Box sie nach dem Sync hat.

#### 12. `tobibox/papierkorb/empty`

Löscht den Papierkorb **endgültig** (Knopf „Papierkorb leeren“; es gibt keine
Automatik).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `bestaetigt` | bool, muss `true` sein | **ja** | Schutz gegen versehentlichen Aufruf; die Seite fragt vorher nach. `false` oder fehlend: `invalid_format` |
| `eintrag_ids` | array von string | nein | nur diese Einträge; ohne das Feld: alle |

Ausgabe: `{"geloescht": <int>, "freigegeben_bytes": <int>}` (Platz auf der
Freigabe, **nicht** auf den Boxen). Fehler: `medien_schreibfehler` (ein Teil kann
schon gelöscht sein; `geloescht` steht dann in `message`, die Seite lädt neu).
Rechte: Admin. Idempotent: ja (leerer Papierkorb: `geloescht=0`). MQTT: –.

### 3.4 Neue Tobies (Weg A, CUJ 7a, 12)

Das Backend führt die Liste **„Neue Tobies“** aus den Meldungen auf
`tobibox/<box>/unknown/<uid>` (`mqtt-v1.md`, 3.5): Eine Kennung, die **beide**
Boxen melden, ist **ein** Eintrag. Die Liste liegt im HA-Speicher (Teil der
HA-Sicherung), getrennt von der Konfiguration (keine Revision, nicht auf MQTT). Das
Backend bestätigt jede Meldung sofort auf `…/ack` (`neu`, bei bekannter Kennung
`bekannt`); die Box löscht daraufhin ihren Eintrag. „Bestätigen“ in der Oberfläche
heißt **zuordnen** (`zuordnung/set`); das `ack` an die Box geht automatisch und ist
kein Knopf (Vorgabe der Projektleitung 09.11.).

**`bekannt`** (W-11) heißt: Die Kennung steht **schon in der Liste „Neue Tobies“ oder
schon in den Zuordnungen**. Steht sie in den Zuordnungen (die Box war lange offline
und kannte die Zuordnung noch nicht, oder ein Tobie wurde gerade zugeordnet), nimmt das
Backend sie **nicht** in „Neue Tobies“ auf und bestätigt mit `bekannt`; in der Box-Liste
zeigt `konfig_stand="veraltet"` (3.7), dass diese Box die Liste noch nicht hat. Die
Liste in HA bleibt, bis Tobias die Kennung **zuordnet** (`zuordnung/set`, auch über den
Lernmodus) oder **verwirft**. Meldet eine Box die Kennung danach erneut (der Tobie
liegt wieder auf) und sie ist weder zugeordnet noch verworfen worden, erscheint sie
wieder; eine verworfene Kennung erscheint bei erneuter Meldung wieder.

**Eintrag „Neuer Tobie“:**

| Feld | Typ | Bedeutung |
|---|---|---|
| `uid` | string | Kennung |
| `zuerst` | string | früheste Meldung aller Boxen |
| `zuletzt` | string | späteste Meldung aller Boxen |
| `anzahl` | int | Summe über die Boxen von **`anzahl` der jeweils letzten Nachricht** dieser Box. Die Zahl in einer Nachricht ist schon die Summe der Box; das Backend **ersetzt** den Wert je Box und addiert nie bei jeder Nachricht. |
| `boxen` | object | je Box, die ihn gemeldet hat: `{"zuerst", "zuletzt", "anzahl", "zeit_ok"}` (Werte aus der Meldung; bei `zeit_ok=false` sind die Zeiten mit Vorsicht zu lesen) |

#### 13. `tobibox/neue_tobies/list`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `limit` | int 1–200 | nein | Vorgabe 100 |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe: `{"eintraege": [<Eintrag>…], "gesamt": <int>}`, nach `zuletzt` absteigend.
Rechte: alle. Idempotent: ja. MQTT: –.

#### 14. `tobibox/neue_tobies/verwerfen`

Nimmt eine Kennung aus der Liste, ohne sie zuzuordnen.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `uid` | string | **ja** | kanonische Kennung |

Ausgabe: `{"entfernt": <bool>}` (`false`: war nicht in der Liste). Fehler:
`kennung_ungueltig`. Rechte: Admin. Idempotent: ja (zweimal: `entfernt=false`, kein
Fehler). MQTT: **keine** (die Bestätigung ging schon beim Eintreffen raus). Die Box
spielt für diesen Tobie weiter die Überraschungs-Serie.

### 3.5 Zuordnungen

#### 15. `tobibox/zuordnung/list`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | nein | nur Zuordnungen, die auf diese Serie zeigen (`serie` und `folge`) |
| `limit` | int 1–100 | nein | Vorgabe 100 (Vorgabe der Projektleitung 09.11., W-13) |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `konfig` | object | Konfig-Stand |
| `zuordnungen` | array | je Eintrag: `{"uid", "name" (oder null), "ziel", "serie_name" (oder null), "folge_anzeige" (oder null), "folge_vorhanden" (bool oder null)}`; `serie_name` ist `null`, wenn die Serie auf der Freigabe fehlt, `folge_vorhanden` und `folge_anzeige` nur bei `typ="folge"` |
| `gesamt` | int | Anzahl aller passenden Zuordnungen |

Sortiert nach `uid`. Eine Seite hat höchstens 100 Einträge (≈ 35 KiB, unter der
Grenze von 64 KiB, Abschnitt 8). Rechte: alle. Idempotent: ja. MQTT: –.

#### 16. `tobibox/zuordnung/set`

Ordnet eine Kennung einem Ziel zu (Typ `serie`, `folge` oder `aktion`, Entscheidung F)
und gibt ihr optional einen **Namen**. Das ist der Weg für „Neue Tobies“, für
Aktionskarten (Status, Gute Nacht) und für Kennungen, die Tobias von Hand eingibt.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `uid` | string | **ja** | kanonische Kennung (`reader-v1.md`, Abschnitt 4) |
| `ziel` | object | **ja** | Ziel, siehe oben |
| `name` | string, 1–60 Zeichen, oder `null` | nein | Tobie-Name (Vorgabe der Projektleitung 09.11.; `data-model.md`, Abschnitt 2). Fehlt das Feld, bleibt ein vorhandener Name unverändert; `null` löscht ihn. Steuerzeichen werden entfernt, Leerraum gekürzt; danach leer: `name_ungueltig`. Die Box ignoriert den Namen. |
| `ueberschreiben` | bool | nein | Vorgabe `false`. Hat die Kennung schon **ein anderes** Ziel, antwortet das Backend ohne `ueberschreiben=true` mit `zuordnung_existiert`; die Seite fragt Tobias und sendet erneut mit `true`. |
| `erwartet_ziel` | object oder `null` | nein | Das Ziel, das die Seite zuletzt gesehen hat (`null`: „keine Zuordnung“). Stimmt es nicht mit dem Stand im Backend überein, lehnt das Backend ab (`zuordnung_geaendert`, W-12), und die Seite lädt `zuordnung/list` neu. Ist `erwartet_ziel` gesetzt, entfällt die Prüfung auf `ueberschreiben`. Fehlt es, gilt „letzter Schreiber gewinnt“ (nur für Aktionen und Automationen). **Die Seite sendet es immer.** |

Prüfung: `ziel.typ` ∈ `serie`, `folge`, `aktion`; bei `serie`/`folge` muss die Serie in
der Medienverwaltung existieren (`serie_nicht_gefunden`; sie muss **nicht** schon auf
einer Box sein, das Design erlaubt das, die Box spielt bis dahin die
Überraschungs-Serie); **die Überraschungs-Serie ist als Ziel verboten**
(`ziel_ungueltig`, Vorgabe der Projektleitung 09.11.); bei `folge` muss die Folge in
`folgen` stehen (`folge_nicht_gefunden`); bei `aktion` ist nur `status` oder
`gute_nacht` erlaubt (`ziel_ungueltig`).

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `geaendert` | bool | `false`, wenn die Kennung schon genau dieses Ziel **und** diesen Namen hatte (dann **keine** neue Revision, keine MQTT-Nachricht) |
| `konfig` | object | Konfig-Stand nach dem Befehl |
| `veroeffentlicht` | bool oder `null` | `tobibox/config` ist beim Broker angekommen (PUBACK); `false` heißt: gespeichert, wird nachgeholt; `null` bei `geaendert=false` (es gab keine Veröffentlichung, W-20) |

Fehler: `kennung_ungueltig`, `ziel_ungueltig`, `serie_nicht_gefunden`,
`folge_nicht_gefunden`, `zuordnung_existiert`, `zuordnung_geaendert`, `name_ungueltig`,
`konfig_zu_gross`, `konfig_nicht_bereit`. Rechte: Admin.
Idempotent: **ja** (gleiches Ziel und gleicher Name zweimal: zweites Mal `geaendert=false`).
MQTT: veröffentlicht `tobibox/config` (retained, Revision + 1, `erzeugt_am` jetzt). Die
Boxen übernehmen nach der Revisionsregel (`mqtt-v1.md`, 5.2); liegt der Tobie gerade
auf, wechselt die Box auf das neue Ziel (`mqtt-v1.md`, 4.1, Schritt 6). Nebenwirkung:
Steht die Kennung in „Neue Tobies“, wird sie dort entfernt (Ereignis `neue_tobies`,
`art="entfernt"`, `grund="zugeordnet"`). Das Backend schreibt `leise_zeiten`,
`gute_nacht`, `ton_pegel`, `hinweis_pegel` und `lesezeichen_tage` unverändert fort
(Entscheidung N, 09.11.). **(09.11., Befund AP 3.1)** `lesezeichen_tage` legt das Backend selbst
an (Vorgabe 14) und veröffentlicht es in jeder `tobibox/config`; ein älterer Speicher ohne das Feld
bekommt 14.

#### 17. `tobibox/zuordnung/remove`

Löst eine Zuordnung („lösen“, Design: Aktionen). Der Tobie-Name geht mit.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `uid` | string | **ja** | |
| `erwartet_ziel` | object | nein | wie bei `zuordnung/set` (W-12); Abweichung: `zuordnung_geaendert`. **Die Seite sendet es immer.** |

Ausgabe: wie `zuordnung/set` (`geaendert=false` und `veroeffentlicht=null`, wenn es
keine Zuordnung gab). Fehler: `kennung_ungueltig`, `zuordnung_geaendert`,
`konfig_nicht_bereit`. Rechte: Admin. Idempotent: ja. MQTT: veröffentlicht
`tobibox/config` (Revision + 1), wenn etwas entfernt wurde. Danach spielt die Box
für den Tobie die Überraschungs-Serie und meldet ihn beim nächsten Auflegen als
unbekannt; er erscheint wieder in „Neue Tobies“.

### 3.6 Lernmodus (Weg B, CUJ 7b)

Ablauf und Reihenfolge: Abschnitt 6.2. Hier die Befehle.

#### 18. `tobibox/lernmodus/start`

„Jetzt kommt ein neuer Tobie“: Das Backend merkt sich Box, Ziel und Beginn und sendet
den Befehl `lernen` an die Box (`mqtt-v1.md`, 3.7 und 4.2).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `box` | string | **ja** | Box-Name |
| `ziel` | object | **ja** | nur `typ` `serie` oder `folge` (Aktionskarten gehen nicht über den Lernmodus, `mqtt-v1.md`, 3.8); die Überraschungs-Serie ist verboten (`ziel_ungueltig`) |
| `name` | string, 1–60 Zeichen | nein | Tobie-Name, der bei der Zuordnung gesetzt wird (wie bei `zuordnung/set`) |
| `anfrage_id` | string | nein | siehe 2.2 |

Prüfung wie bei `zuordnung/set` (Serie und Folge müssen existieren). Die Box muss
`online` sein; ist `online` `null` (HA kennt noch keine Nachricht), gilt sie als
offline (`box_offline`, W-25). Ist `konfig.zustand` nicht `ok`: `konfig_nicht_bereit`.

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `befehl_id` | string | `id` des Befehls `lernen` (UUID); kommt in den Ereignissen und bei `lernmodus/antwort` wieder vor |
| `box` | string | |
| `ziel` | object | |
| `beginn` | string | Zeitstempel (Wanduhr von HA) |
| `frist_bis` | string | bis wann das Backend die Meldung dieses Befehls annimmt: `beginn` + 180 s (60 s Lebensdauer des Befehls + 120 s Lernfrist der Box) |

Fehler: `box_unbekannt`, `box_offline`, `mqtt_nicht_verbunden`, `ziel_ungueltig`,
`serie_nicht_gefunden`, `folge_nicht_gefunden`, `name_ungueltig`, `konfig_nicht_bereit`,
`lernmodus_laeuft` (für diese Box läuft schon ein **lebender** Vorgang mit **anderem**
Ziel: **erst abbrechen**, Vorgabe der Projektleitung 09.11.; mit gleichem Ziel antwortet
das Backend mit dem laufenden Vorgang, siehe unten), `anfrage_id_konflikt`. Rechte:
Admin. MQTT: `tobibox/<box>/cmd` mit `befehl="lernen"`, `ttl_s` 60, `daten` `{}`. Das
Ziel geht **nicht** an die Box. Lehnt die Box den Befehl ab (`event`
`befehl_abgelehnt`, z. B. `zeit_unsicher`), meldet das Backend es als Ereignis
`lernmodus` mit `zustand="box_lehnt_ab"` (mit Klartext, `mqtt-v1.md`, 3.4).

**Idempotenz und „lebender“ Vorgang (W-05).** Ein Vorgang ist **lebendig**, solange er
weder beendet ist noch als tot gilt. Er gilt als **tot**, wenn (a) ein Status der Box
mit `lernmodus=true` für diesen Vorgang gesehen wurde und danach ein Status mit
`lernmodus=false` eintraf, oder (b) `frist_bis` vorbei ist, oder (c) seit `beginn` mehr
als 30 s vergangen sind, ohne dass je ein Status mit `lernmodus=true` eintraf. Ein toter
Vorgang endet mit dem Zustand `abgelaufen` (Ereignis `lernmodus`). Beim Start mit
gleicher Box und **gleichem** Ziel liefert das Backend nur einen **lebenden** Vorgang
unverändert zurück (kein zweiter Befehl); ist der Vorgang tot oder gibt es keinen,
beginnt ein neuer mit neuem Befehl. Bei **anderem** Ziel gilt `lernmodus_laeuft` nur
für einen lebenden Vorgang. Ohne `anfrage_id` ist der Befehl sonst nicht idempotent;
deshalb `anfrage_id`.

#### 19. `tobibox/lernmodus/antwort`

Antwort auf die **Rückfrage vor dem Überschreiben** (Ereignis `lernmodus` mit
`zustand="rueckfrage"`, 6.2).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `befehl_id` | string | **ja** | aus dem Ereignis |
| `ueberschreiben` | bool | **ja** | `true`: die bestehende Zuordnung wird durch das Ziel des Lernmodus ersetzt. `false`: bleibt, das Backend lehnt die Meldung ab. |

Ausgabe: `{"zustand": "zugeordnet" | "abgelehnt", "konfig": <Konfig-Stand>}`.
Fehler: `kein_lernmodus` (kein offener Vorgang mit dieser `befehl_id`),
`rueckfrage_abgelaufen` (die Frist `rueckfrage_bis` ist vorbei, das Backend hat schon
mit `abgelehnt` bestätigt). Rechte: Admin. Idempotent: Endzustand ja; eine zweite
Antwort liefert `kein_lernmodus`. MQTT: bei `true` zuerst `tobibox/config` (Revision
+ 1), **danach** `…/ack` mit `grund="zugeordnet"` (erst nach dem PUBACK, 6.2 Schritt 4);
bei `false` nur `…/ack` mit `grund="abgelehnt"` (keine neue Konfiguration). Beide `ack`
tragen `zuletzt` und `art` der gemeldeten Kennung (`mqtt-v1.md`, 3.6).

#### 20. `tobibox/lernmodus/abbrechen`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `box` | string | **ja** | |

Ausgabe: `{"abgebrochen": <bool>}` (`true`, wenn ein Vorgang offen war). Das Backend
verwirft den Vorgang und sendet immer `lernen_abbrechen`, auch ohne offenen Vorgang
(im Zustand „Lernmodus aus“ wirkungslos, `mqtt-v1.md`, 3.7). Eine Meldung, die danach
noch mit der `befehl_id` des verworfenen Vorgangs eintrifft, bestätigt das Backend
mit `grund="abgelehnt"` (die Box meldet den Tobie dann erneut als unbekannt).
**Steht eine Rückfrage offen** (die Meldung ist schon eingetroffen), sendet das Backend
das `ack` mit `grund="abgelehnt"` **sofort beim Abbrechen** (W-24); die Box wartet
nicht auf die Frist.

Fehler: `box_unbekannt`, `mqtt_nicht_verbunden`. Kein `box_offline`: Der Abbruch
wird auch an eine Box gesendet, die gerade nicht antwortet (Lebensdauer 30 s).
Rechte: Admin. Idempotent: ja. MQTT: `tobibox/<box>/cmd` mit
`befehl="lernen_abbrechen"`, `ttl_s` 30. Das Ereignis `lernmodus` meldet
`zustand="abgebrochen"`.

### 3.7 Boxen

#### 21. `tobibox/boxen/list`

Keine Eingabe. Ausgabe: `{"boxen": [<Box>…]}`, in der Reihenfolge der Einrichtung.

**Box-Objekt:**

| Feld | Typ | Bedeutung |
|---|---|---|
| `box` | string | Box-Name |
| `anzeigename` | string oder `null` | Gerätename aus der Discovery (`Tobi Box <anzeigename>`), `null`, wenn die Box noch nie da war |
| `online` | bool oder `null` | aus `tobibox/<box>/online` (`online`/`offline`); `null`, wenn HA noch keine Nachricht kennt (für Befehle wie `offline`, `box_offline`) |
| `status` | object oder `null` | der letzte `tobibox/<box>/status` **unverändert** (`mqtt-v1.md`, 3.3, mit `speicher_frei_mb`, `netz`, `akku_prozent`, `sync`, `version`, `letzter_fehler`, `konfig`, `update` …); `null` ohne Nachricht. Neue Statusfelder erscheinen hier ohne Vertragsänderung. |
| `status_empfangen_am` | string oder `null` | wann HA ihn empfangen hat |
| `konfig_stand` | `aktuell`, `veraltet`, `voraus`, `unbekannt` | `status.konfig` gegen den Stand in HA (W-02): `aktuell` = gleiche `liste_id` und `revision`; `veraltet` = andere `liste_id` oder niedrigere `revision` als in HA; **`voraus` = gleiche `liste_id` und `revision` der Box höher als in HA** (typisch nach dem Zurückspielen einer Sicherung, Abschnitt 13); `unbekannt` ohne Status |
| `lernmodus` | object oder `null` | der offene Vorgang dieser Box (Felder wie im Ereignis `lernmodus`, 4.3), sonst `null` |
| `ereignisse` | array | die letzten **20** Meldungen von `tobibox/<box>/event` (neueste zuerst), **im HA-Speicher** und damit über einen Neustart hinaus (Vorgabe der Projektleitung 09.11.): `{"id", "ts", "art", "daten", "text"}`; `art` und `daten` unverändert (`liste_abgelehnt`, `fehler`, `befehl_abgelehnt`), `text` ist der Klartext des Backends (`mqtt-v1.md`, 3.4: „Die Box … hat … abgelehnt“). So sieht Tobias abgelehnte Listen. |

Rechte: alle. Idempotent: ja. MQTT: –. Fehler: keine.

#### 22. `tobibox/box/sync`

Stößt den Medien-Sync der Box an (CUJ 9: „von HA angestoßen“). Ob er läuft, entscheidet
die Box nach der Netz-Regel (Heimnetz immer; Hotspot nur mit Lader oder über 50 %); wenn nicht,
steht es im Status (`sync.ergebnis="abgebrochen"`, `grund`). Der Sync übernimmt weder
`_upload/` noch `_papierkorb/` noch den Eingang (Abschnitt 11.1).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `box` | string | **ja** | |
| `anfrage_id` | string | nein | siehe 2.2 |

Ausgabe: `{"befehl_id": <string>, "ttl_s": 300}`. Fehler: `box_unbekannt`,
`box_offline` (auch bei `online=null`), `mqtt_nicht_verbunden`, `anfrage_id_konflikt`.
Rechte: Admin. Idempotent: nicht ohne `anfrage_id`; ein zweiter Sync-Befehl während
eines Syncs ist für die Box harmlos (sie startet keinen zweiten). MQTT:
`tobibox/<box>/cmd`, `befehl="sync"`, `ttl_s` 300, `daten` `{}`. Das Ergebnis kommt über
den Status (Ereignis `boxen`).

### 3.8 Liste

#### 23. `tobibox/liste/neu_ausrollen`

Erzeugt eine neue Listen-ID und veröffentlicht die Konfiguration neu. Alle Boxen
nehmen sie an, auch bei niedrigerer Revision (`mqtt-v1.md`, 5.1 und 5.3; Betriebshandbuch
für den Fall einer Wiederherstellung aus der Sicherung). Der Befehl ist in **jedem**
Zustand der Konfiguration erlaubt (Abschnitt 13) und ist der Weg heraus aus `leer_neu`
(„mit leerer Liste neu beginnen“) und aus `export_neuer` („den Stand in HA behalten“).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `bestaetigt` | bool, muss `true` sein | **ja** | Schutz gegen versehentlichen Aufruf. Die Seite zeigt vorher, was passiert: bei `leer_neu` „Alle Tobies verlieren ihre Zuordnung“. |
| `anfrage_id` | string | nein | siehe 2.2 |

Ausgabe: `{"konfig": <Konfig-Stand>, "veroeffentlicht": <bool>}`. Die neue Liste
beginnt mit Revision 1 (`data-model.md`, Abschnitt 2) und `zustand="ok"`. Fehler:
`anfrage_id_konflikt`. Rechte: Admin. Idempotent: **nein** (jeder Aufruf erzeugt eine neue
Listen-ID; harmlos, aber unnötig), deshalb `anfrage_id`. MQTT: `tobibox/config` mit
neuer `liste_id`, `revision` 1, gleiche Zuordnungen und Einstellungen wie der
HA-Speicher (bei `leer_neu`: leer). Der Export auf das NAS läuft danach im Hintergrund
wie nach jeder Änderung.

### 3.9 Eingang (Entscheidung M)

Tobias legt Hörbücher und Hörspiele in den **Eingang** (`tobibox/eingang/` auf dem NAS,
Abschnitt 11.1). Die Integration liest die Tags und sortiert **automatisch** in die
Medienstruktur ein (Regeln: Abschnitt 11). Die Seite zeigt, was im Eingang liegt und
was erkannt wurde, und Tobias korrigiert mit den Befehlen Nr. 6, 7, 25, 26, 27
und 28.

**Eingangs-Eintrag** (`eintrag`): ein Eintrag der **obersten Ebene** von `eingang/`
(eine Datei oder ein Ordner).

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | string | 12 Zeichen `[0-9a-f]`: Anfang der SHA-256 des Namens (stabil über Durchläufe) |
| `name` | string | Name der Datei oder des Ordners |
| `art` | `datei` oder `ordner` | |
| `dateien` | int | Anzahl Audiodateien darin (Endungsliste, ohne Dotfiles) |
| `ignoriert` | int | Anzahl anderer Dateien (Bilder, Texte …), die nie einsortiert werden |
| `groesse_bytes` | int | Summe der Audiodateien |
| `zuerst_gesehen` | string | wann ein Durchlauf den Eintrag zum ersten Mal sah (daraus die Eingangsreihenfolge, 11.6) |
| `geaendert_am` | string | neueste Änderungszeit darin |
| `status` | string | `wartet` (Ruhezeit läuft: zuletzt vor weniger als 120 s geändert), `bereit` (kommt beim nächsten Durchlauf dran), `laeuft`, `blockiert` (nichts davon einsortiert, siehe `hinweise`), `teilweise` (ein Teil einsortiert, der Rest blockiert), `erledigt` (nur mit Filter `erledigt`: aus dem Protokoll) |
| `hinweise` | array | `{"code", "datei", "text"}`: `kopierschutz`, `nicht_lesbar`, `probedekodierung_fehlgeschlagen`, `ffprobe_fehlt`, `keine_audiodateien`, `verschieben_fehlgeschlagen`, `doppelt` (die Datei war schon vorhanden und kam in den Papierkorb), `vorgabe_serie_fehlt`; `datei` ist der Pfad im Eintrag oder `null` |
| `ergebnis` | array | was einsortiert wurde: `{"serie_id", "serie_name", "serie_neu" (bool), "folge" (Name), "anzeige", "tracks", "pruefen" (bool), "pruefen_gruende" (array)}` |
| `fertig_am` | string oder `null` | wann der Eintrag (ganz oder teilweise) einsortiert wurde |

#### 29. `tobibox/eingang/list`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `filter` | `offen`, `erledigt` oder `alle` | nein | Vorgabe `offen`: was noch im Eingang liegt (`wartet`, `bereit`, `laeuft`, `blockiert`, `teilweise`). `erledigt`: die letzten 100 einsortierten Einträge aus dem **Protokoll** im HA-Speicher (überlebt einen Neustart; älteres fällt heraus). |
| `limit` | int 1–100 | nein | Vorgabe 50 |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe: `{"eintraege": [<Eintrag>…], "gesamt": <int>, "sortierung_laeuft": <bool>,
"geprueft_am": <string oder null>}`. Neueste zuerst (`zuerst_gesehen` absteigend). Die
Antwort kommt aus dem Zwischenspeicher des letzten Durchlaufs. Fehler:
`medien_nicht_erreichbar` (nur, wenn noch nie geprüft wurde). Rechte: alle.
Idempotent: ja. MQTT: –.

#### 30. `tobibox/eingang/sortieren`

Stößt einen Durchlauf des Einsortierens an („erneut einsortieren“): Einträge, die
blockiert waren (Tags nachgetragen, Datei ersetzt), und Einträge, die erst jetzt ruhig
sind. Beim Öffnen der Seite ruft die Seite `medien/pruefen` und `eingang/sortieren`
auf; der 10-min-Timer tut dasselbe.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `eintrag_ids` | array von string | nein | nur diese Einträge; ohne das Feld: alle |
| `sofort` | bool | nein | Vorgabe `false`. `true` übergeht die Ruhezeit von 120 s (Tobias weiß, dass das Kopieren fertig ist). |

Ausgabe: `{"gestartet": <bool>, "laeuft_bereits": <bool>, "eintraege": <int>}`
(`eintraege`: wie viele Einträge dieser Durchlauf bearbeitet). Der Durchlauf läuft im
Hintergrund; sein Ende kommt als Ereignis `eingang` (`durchlauf_fertig`), jeder
einsortierte Eintrag als `neu_einsortiert` (4.5). Läuft schon ein Durchlauf, meldet der
Befehl `laeuft_bereits=true`; die angegebenen Einträge werden im nächsten Durchlauf
bearbeitet. Fehler: `medien_nicht_erreichbar`, `eintrag_nicht_gefunden` (eine
`eintrag_id` unbekannt). Rechte: Admin. Idempotent: ja. MQTT: –.

### 3.10 Konfiguration: Sicherungsnetz (W-01, W-02)

Abschnitt 13 beschreibt die Zustände. Hier die beiden Befehle.

#### 31. `tobibox/konfig/export_lesen`

Zeigt, was im neuesten Export `export/config.json` auf dem NAS steht, ohne etwas zu
ändern.

Keine Eingabe. Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `vorhanden` | bool | es gibt eine lesbare Exportdatei |
| `liste_id`, `revision` | string, int | aus der Datei (sonst `null`) |
| `exportiert_am` | string oder `null` | `exportiert_am` aus der Datei |
| `anzahl_zuordnungen` | int oder `null` | |
| `anzahl_fenster` | int oder `null` | Leise-Zeiten-Fenster (Anzeige) |
| `neuer_als_ha` | bool | der Export ist neuer als der HA-Speicher (Abschnitt 13.2) |
| `konfig` | object | Konfig-Stand von HA zum Vergleich |

Fehler: `medien_nicht_erreichbar`, `export_ungueltig` (Datei da, aber nicht lesbar oder
nicht gültig nach `data-model.md`; `vorhanden` ist dann `false`, kein Fehler: der Code
gilt nur, wenn die Prüfung selbst scheitert). Rechte: alle. Idempotent: ja. MQTT: –.

#### 32. `tobibox/konfig/aus_export`

Holt die Konfiguration aus dem Export zurück (Zuordnungen **mit Tobie-Namen**,
Leise-Zeiten, Gute-Nacht-Einstellungen, `ton_pegel`, `hinweis_pegel`, `lesezeichen_tage`) und verteilt
sie mit **neuer Listen-ID** und Revision 1 (damit keine Box sie wegen einer niedrigeren
Revision ablehnt). Erlaubt in jedem Zustand; Weg heraus aus `leer_neu` und
`export_neuer`.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `bestaetigt` | bool, muss `true` sein | **ja** | Schutz gegen versehentlichen Aufruf. Die Seite zeigt vorher das Ergebnis von `export_lesen` (Revision, Zeit, Anzahl Zuordnungen). |
| `anfrage_id` | string | nein | siehe 2.2 |

Das Backend prüft die Datei mit derselben Prüfung wie die Box (Migration und Schema,
`data-model.md`, Abschnitt 2); ist irgendein Teil ungültig, übernimmt es **nichts**
(`export_ungueltig`). Verweist eine Zuordnung auf eine Serie, die es nicht (mehr) gibt,
wird sie trotzdem übernommen (Zuordnung vor Medien ist erlaubt).

Ausgabe: `{"konfig": <Konfig-Stand>, "veroeffentlicht": <bool>, "uebernommen":
{"zuordnungen": <int>, "fenster": <int>}}`. Fehler: `export_nicht_gefunden`,
`export_ungueltig`, `medien_nicht_erreichbar`, `anfrage_id_konflikt`. Rechte: Admin.
Idempotent: **nein** (jeder Aufruf erzeugt eine neue Listen-ID), deshalb `anfrage_id`.
MQTT: `tobibox/config` mit neuer `liste_id`, `revision` 1.

## 4. Ereignisse (Abo `tobibox/subscribe`)

Alle Ereignisse haben dieselbe Hülle (Inhalt des Feldes `event` der HA-Nachricht):

```json
{ "v": 1, "thema": "boxen", "art": "geaendert", "daten": { … } }
```

*   `thema` ist eines der abonnierten Themen, `art` die Art des Ereignisses, `daten`
    der Inhalt. Neue `art`-Werte und neue Felder können ohne Versionsänderung
    kommen (Abschnitt 9); die Seite ignoriert, was sie nicht kennt.
*   **`art="snapshot"`**: kommt einmal je Thema direkt nach dem Abonnieren (auch nach
    einem erneuten Abonnieren durch den Verbindungsaufbau der Seite). Er trägt nur
    den kleinen Zustand, den das Thema braucht, **nie** ganze Listen: Listen holt die
    Seite mit den Befehlen. So bleibt jede Nachricht klein (Abschnitt 8).
*   **Nur Hinweise, keine Quelle der Wahrheit.** Verpasst die Seite ein Ereignis
    (Verbindung weg), stimmt der Zustand nach dem nächsten Snapshot und einem
    `list`/`get` wieder. HA baut die Verbindung der Oberfläche selbst neu auf und
    abonniert dabei erneut.
*   **Bündeln (W-23):** Das Backend fasst nur die Ereignisse `geaendert` (Themen
    `boxen`, `konfig`, `eingang`) und `serien_geaendert` zusammen: höchstens **eines je
    Thema und Box (bzw. Serie) und Sekunde**. Ereignisse mit eigenem Inhalt
    (`boxen`/`ereignis`, `lernmodus`-Zustände, `neu_einsortiert`, `abweichung`,
    `fortschritt`) werden **nie** zusammengefasst oder verschluckt. Die HA-Warteschlange
    je Verbindung ist begrenzt (4096 Nachrichten, Abschnitt 8); Ereignisse sind darum
    selten und klein.

### 4.1 Thema `boxen`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"boxen": [{"box", "online", "konfig_stand"}…]}` |
| `geaendert` | ein vollständiges Box-Objekt (3.7, ohne `ereignisse`), wenn sich `online`, `status` oder `konfig_stand` änderte (auch auf oder von `voraus`) |
| `ereignis` | `{"box": <string>, "ereignis": {"id", "ts", "art", "daten", "text"}}` für jede neue Meldung von `…/event` (z. B. `liste_abgelehnt`) |

### 4.2 Thema `neue_tobies`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"gesamt": <int>}` |
| `neu` | `{"eintrag": <Eintrag>}`, eine Kennung erscheint zum ersten Mal |
| `aktualisiert` | `{"eintrag": <Eintrag>}`, neue Meldung zu einer bekannten Kennung |
| `entfernt` | `{"uid": <string>, "grund": "zugeordnet" \| "verworfen"}` |

### 4.3 Thema `lernmodus`

Gilt je Box und Vorgang. `daten`:

| Feld | Typ | Bedeutung |
|---|---|---|
| `box` | string | |
| `befehl_id` | string | |
| `zustand` | string | siehe unten |
| `ziel` | object | Ziel des Vorgangs |
| `beginn`, `frist_bis` | string | wie bei `lernmodus/start` |
| `rueckfrage_bis` | string oder `null` | bei `rueckfrage`: bis wann `lernmodus/antwort` gilt (6.2, Schritt 3) |
| `uid` | string oder `null` | gemeldete Kennung (ab `rueckfrage`/`zugeordnet`) |
| `bisher` | object oder `null` | bei `rueckfrage`: das bisherige Ziel der Kennung |
| `grund` | string oder `null` | bei `abgelehnt`, `box_lehnt_ab`, `abgelaufen`: Ursache; bei `zugeordnet` `unveraendert`, wenn der Tobie das Ziel schon hatte |
| `text` | string oder `null` | Klartext |

`zustand`: `wartet` (Befehl gesendet, noch kein Tobie gemeldet), `rueckfrage` (Kennung
ist schon zugeordnet; die Seite zeigt die Frage und antwortet mit `lernmodus/antwort`),
`zugeordnet` (Ende), `abgelehnt` (Ende; `grund` ∈ `nutzer`, `abgelaufen`,
`konfig_zu_gross`, `speicherfehler`, `ziel_fehlt`, `konfig_nicht_bereit`),
`abgebrochen` (Ende), `abgelaufen` (Ende; `grund` ∈ `frist` = `frist_bis` ohne Meldung,
`box_beendet` = die Box meldet den Lernmodus als beendet, `kein_status` = 30 s ohne
Lernmodus-Status; W-05), `box_lehnt_ab` (Ende; `grund` ∈ `bedingung`, `zeit_unsicher`).

`snapshot`: `{"vorgaenge": [<daten ohne Ende-Zustände>…]}` (höchstens ein Vorgang je
Box).

### 4.4 Thema `medien`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"pruefung_laeuft": <bool>, "geprueft_am": <string oder null>}` |
| `serien_geaendert` | `{"serie_ids": [<string>…]}` (Prüfung, anderer Nutzer, Upload, Einsortieren, Korrektur oder Papierkorb haben etwas geändert; die Seite lädt `serien/list` bzw. `serie/get` neu) |
| `pruefung_fertig` | `{"geprueft_am": <string>, "neue_serien": <int>, "neue_folgen": <int>, "entfernte_folgen": <int>, "hinweise": <int>}` |
| `papierkorb_geaendert` | `{}` |

### 4.5 Thema `eingang`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"offen": <int>, "blockiert": <int>, "sortierung_laeuft": <bool>, "geprueft_am": <string oder null>}` |
| `geaendert` | `{}`: die Liste im Eingang hat sich geändert; die Seite lädt `eingang/list` neu |
| `neu_einsortiert` | `{"eintrag_id", "eintrag_name", "ergebnis": [<wie in Eingangs-Eintrag>…], "hinweise": [<wie dort>…], "zaehler": {"folgen", "serien_neu", "pruefen", "doppelt", "blockiert"}}`: ein Eintrag wurde ganz oder teilweise einsortiert („neu einsortiert“). Eines je Eintrag, nie zusammengefasst. |
| `durchlauf_fertig` | `{"geprueft_am": <string>, "zaehler": {"eintraege", "folgen", "serien_neu", "pruefen", "doppelt", "blockiert"}}` |

Bleibt etwas `blockiert` (Kopierschutz, defekt), legt das Backend zusätzlich eine
HA-Benachrichtigung (`persistent_notification`) an, einmal je Eintrag.

### 4.6 Thema `konfig`

| `art` | `daten` |
|---|---|
| `snapshot`, `geaendert` | `{"konfig": <Konfig-Stand>}`. `geaendert` kommt nach jeder Änderung durch `zuordnung/*`, `lernmodus/antwort`, `folge/verschieben`, `serien/zusammenfuehren`, `liste/neu_ausrollen`, `konfig/aus_export` (auch von einem anderen Fenster oder einer Aktion aus) und bei jedem Wechsel von `zustand`, `export_ok`. Die Seite lädt dann `zuordnung/list`. |
| `abweichung` | `{"box", "grund": "voraus" \| "revision_zu_niedrig", "box_liste_id", "box_revision", "ha_revision"}` (W-02): eine Box hat einen neueren Stand als HA oder lehnt die Liste von HA wegen zu niedriger Revision ab. Die Seite zeigt „Die Box hat einen neueren Stand als HA. Bitte ‚Liste neu ausrollen‘ (oder aus dem Export holen).“ Die Integration erhöht die Revision **nie** von selbst auf den Stand der Box. |
| `export_fehler` | `{"seit": <string>, "text": <string>}`: der Export auf das NAS schlug fehl (der Befehl selbst gelang). |
| `export_ok` | `{"export_geschrieben_am": <string>}`: der Export ist nachgeholt. |

### 4.7 Thema `upload`

Das Backend sendet die Ereignisse eines Uploads an **alle Abos des Nutzers, der ihn
gestartet hat** (Thema `upload`); die Seite filtert nach `upload_id` (W-04). Die
`upload_id` kommt nur im HTTP-Körper an, das Backend kennt keine Verbindung zu einem
Upload. Der Fortschritt des Sendens ist Sache des Browsers (5.7); das Thema meldet die
Phase **nach** dem Empfang.

| `art` | `daten` |
|---|---|
| `snapshot` | `{}` |
| `fortschritt` | `{"upload_id", "zustand": "pruefe" \| "fertig" \| "fehler", "bytes": <int>, "code": <string oder null>}` – `pruefe` einmal (Prüfung nach 5.4), `fertig`/`fehler` einmal am Ende (dann liegt die HTTP-Antwort schon vor, oder der Client ist nicht mehr da, 5.2) |

## 5. Hochladen (HTTP)

Ein Upload legt die Datei in den **Eingang** (Entscheidung M, Abschnitt 11). Er
durchläuft dieselbe Einsortierung wie alles, was Tobias vom PC in den Eingang legt.

### 5.1 Endpunkt

*   **Pfad:** `POST /api/tobibox/upload`. Eine Datei je Anfrage; mehrere Dateien sendet
    die Seite nacheinander.
*   **Umsetzung:** eine Klasse `TobiboxUploadView(HomeAssistantView)` mit `url`, `name =
    "api:tobibox:upload"`, `requires_auth = True` (Vorgabe), `cors_allowed = False`
    (Vorgabe); registriert mit `hass.http.register_view(...)` in `http.py`.
*   **Anmeldung:** Header `Authorization: Bearer <Zugriffstoken>` (das Token der
    HA-Sitzung; die Seite holt es aus dem `hass`-Objekt und erneuert es **vor** dem
    Start eines Uploads, falls es abgelaufen ist; das Token gilt nur beim Start der
    Anfrage, ein laufender Upload bricht nicht ab). Ohne gültiges Token antwortet HA mit
    401. Die Administrator-Prüfung macht der Dekorator aus 2.1 (401 oder 403).
*   **Format des Körpers:** `multipart/form-data` (Design: `request.multipart()`).
    Felder **in dieser Reihenfolge**, alle außer `datei` optional: `upload_id` (Text,
    8–64 Zeichen `[0-9A-Za-z-]`, von der Seite erzeugt), `serie_id` (Text: die Serie,
    in deren Ansicht der Nutzer hochlädt; **Vorgabe** für die Einsortierung, 11.5),
    `gruppe` (Text, 8–64 Zeichen `[0-9A-Za-z-]`: Dateien mit gleicher `gruppe` kommen in
    einen gemeinsamen Eingangs-Ordner `Upload <erste 8 Zeichen>` und bilden zusammen
    ein Album, wenn die Tags es hergeben), dann `datei` (die Datei, mit `filename`).
    Weitere Felder werden ignoriert, Felder nach `datei` nicht gelesen.
*   **Der Körper wird nie ganz gelesen.** Das Backend liest nur im Strom
    (`request.multipart()`, `part.read_chunk(...)`), keinesfalls `request.read()`,
    `request.post()` oder `request.json()`: Die sind durch die Größenbegrenzung der Anfrage
    (16 MiB, Abschnitt 8) gedeckelt und würden die Datei in den Speicher laden. Auch die
    kleinen Textfelder liest es mit `part.read()`, das auf dieselbe Grenze trifft; sie
    sind höchstens 64 Zeichen lang und damit harmlos.
*   **Vor dem Körper (Schutz):** (a) Es laufen höchstens `upload_parallel` = 2 Uploads
    gleichzeitig; ein dritter bekommt 429 `zu_viele_uploads`. (b) Steht `Content-Length`
    im Kopf und übersteigt sie `upload_max_bytes`: 413 `datei_zu_gross`; übersteigt sie
    den freien Platz der Freigabe minus 100 MiB: 507 `kein_speicher`, beides **bevor** ein
    Byte gelesen wird.

### 5.2 Strom in Blöcken, Abschluss, Abbruch

Der Upload hat zwei Phasen mit verschiedenem Verhalten bei Abbruch (W-03).

**Phase A, Empfang** (bis zum letzten Byte des Teils `datei`):

1.  Das Backend liest den Teil `datei` in Blöcken zu **1 MiB**
    (`UPLOAD_BLOCK_BYTES = 1048576`) und schreibt jeden Block über
    `hass.async_add_executor_job` in eine **Zwischendatei**
    `medien/_upload/<16 Zeichen Zufall>.part` (gleiche Freigabe und gleiches
    Dateisystem wie der Eingang; der Name enthält **nie** die `upload_id`, damit zwei
    Uploads mit gleicher `upload_id` nie dieselbe Datei beschreiben). Die `upload_id`
    ist während des Laufs gesperrt: ein zweiter Upload mit gleicher `upload_id`, während
    der erste läuft, bekommt 409 `upload_laeuft`.
2.  Währenddessen zählt es die Bytes. Überschreitet die Datei `upload_max_bytes`
    (Vorgabe 500 MiB, einstellbar): Abbruch, Zwischendatei löschen, 413 `datei_zu_gross`.
3.  Bricht die Verbindung ab (Handy verliert Netz, HA bricht den Handler mit
    `CancelledError` ab, weil `handler_cancellation=True`), löscht das Backend die
    Zwischendatei sofort (`except CancelledError`/`finally`). Es ist **nichts
    entstanden**. Reste (`*.part`) älter als 24 h löscht es beim Start und bei jeder
    Prüfung der Freigabe.

**Phase B, Abschluss** (ab dem letzten Byte): Alles Folgende läuft als **eigene Aufgabe,
die der Handler mit `asyncio.shield` abwartet**. Ein Abbruch des Handlers (Client
getrennt) halbiert den Abschluss deshalb nie; die Aufgabe läuft zu Ende:

1.  `fsync` und Prüfung des Formats (5.4).
2.  Unter der **Sperre des Eingangs** (Abschnitt 1): Name nach Abschnitt 12 bereinigen,
    Namensgleichheit (ohne Rücksicht auf Groß-/Kleinschreibung und Unicode-Form, W-03)
    prüfen und gegebenenfalls ` (2)` anhängen, dann die Zwischendatei **ohne
    Überschreiben** an ihren Platz bringen (`os.link` und danach `.part` löschen, oder
    Anlegen mit `O_EXCL`; **nie** ein `os.replace` auf einen vorhandenen Namen).
3.  Die Datei im Zwischenspeicher des Eingangs eintragen, `gruppe` und `serie_id` als
    Vorgabe im HA-Speicher festhalten, das **Ergebnis je `upload_id` merken** (1 Stunde,
    100 Stück, auch wenn der Client weg ist), Ereignis `upload` `fertig`, das Einsortieren
    anstoßen (5.9).
4.  Schlägt der Abschluss fehl, räumt dieselbe Aufgabe in `finally` auf (Zwischendatei
    weg) und merkt den Fehler.

Ist der Client nach Phase A weg, liegt die Datei trotzdem im Eingang. Die Seite fragt
nach einem Verbindungsfehler per `eingang/list` nach, ob die Datei da ist, und sendet
nicht blind erneut. Sendet sie doch erneut (neue `upload_id`, oder nach einem
HA-Neustart, der das gemerkte Ergebnis vergessen hat), erkennt die Einsortierung die
zweite Datei an der **Prüfsumme** und verwirft sie (11.10).

### 5.3 Eingabe und Namen

| Feld/Teil | Regel |
|---|---|
| `serie_id` (Feld) | wenn gesetzt, muss eine vorhandene Serie sein (`serie_nicht_gefunden`, 404). Die Überraschungs-Serie ist als Vorgabe erlaubt (Befüllen, D4). |
| `datei` | `filename` wird nach den **Namensregeln (Abschnitt 12)** bereinigt: verbotene Zeichen werden ersetzt (aus `Folge 1: Der Rabe.mp3` wird `Folge 1 - Der Rabe.mp3`), nichts wird abgelehnt, solange ein Name übrig bleibt. Bleibt keiner übrig: `name_ungueltig` (400). Der tatsächliche Name steht in der Antwort (`eingang_name`). |
| Endung | siehe 5.4 |
| Name vergeben | Gibt es im Eingang schon eine Datei oder einen Ordner mit dem Namen (ohne Rücksicht auf Groß-/Kleinschreibung), hängt das Backend ` (2)`, ` (3)` … an. Es gibt keinen Fehler `datei_existiert` mehr (Vorgabe der Projektleitung 09.11.). Dieselbe Datei zweimal wird später an der Prüfsumme erkannt (11.10). |
| `upload_id` | verbindet die Anfrage mit den Ereignissen (4.7) und macht eine Wiederholung unschädlich (5.6) |

### 5.4 Formate und Prüfung (D5)

*   **Erlaubte Endungen** (ohne Unterscheidung von Groß- und Kleinschreibung), die Liste
    aus `data-model.md`, Abschnitt 5: `mp3`, `m4a`, `m4b`, `aac`, `flac`, `ogg`,
    `opus`, `wav`. Jede andere Endung: 415 `format_nicht_erlaubt`, noch **bevor** der
    Körper gelesen wird, wenn die Endung schon im ersten Teil steht (sonst nach
    dem Strom).
*   **Inhalt, `ffprobe` als Pflicht-Härtung (W-16):** Das Backend öffnet die fertige
    Zwischendatei mit `ffprobe` (im Executor). Der Aufruf **muss** so aussehen:
    *   als **Liste von Argumenten** (`asyncio.create_subprocess_exec` bzw.
        `subprocess.run([...])`), nie über eine Shell, der Dateiname nie in einer
        Shell-Zeile; der Pfad wird als `file:<absoluter Pfad>` übergeben (ein Name mit
        führendem `-` ist so keine Option);
    *   mit `-v error -protocol_whitelist file -print_format json -show_format
        -show_streams` (Tags stehen in `format.tags` und `streams[].tags`). **(09.11., Befund AP 3.1)**
        `ffprobe` kennt `-nostdin` nicht (nur `ffmpeg`; „Option not found“). Die Integration schließt
        stattdessen die Standardeingabe (`stdin=DEVNULL`). `-nostdin` bekommt nur `ffmpeg` bei der
        Probedekodierung (1 s);
    *   mit **erzwungenem Format** aus der Endung (`-f mp3`, `-f mov,mp4,m4a,3gp,3g2,mj2`
        für `m4a`/`m4b`, `-f aac`, `-f flac`, `-f ogg` für `ogg`/`opus`, `-f wav`); das
        Probieren aller Formate entfällt;
    *   mit **Zeitlimit 30 s** und **Speicherlimit** (`RLIMIT_AS` 1 GiB, soweit das System
        es erlaubt) und mit abgebrochenem Prozess bei Überschreitung;
    *   danach prüft das Backend `format.format_name` gegen die erlaubte Liste und verlangt
        **mindestens einen Audio-Strom**. Playlist-Formate (`hls`, `concat`, `m3u8`, `sdp` …)
        und alles, was nicht auf der Liste steht, lehnt es ab: 415 `format_nicht_erlaubt`.
        **Textdatei und Defekt (09.11., Befund AP 3.1):** Scheitert `ffprobe` und die Datei sieht
        aus wie Text (in den ersten 8 KiB **kein NUL-Byte** und mindestens 95 % druckbare Zeichen),
        ist es das falsche Format: 415 `format_nicht_erlaubt` (z. B. eine Textdatei oder Playlist mit
        Endung `.mp3`). Scheitert `ffprobe` an einer Binärdatei (NUL-Byte oder kaum Text), ist sie
        defekt: **kein 415**, nur die Warnung `nicht_lesbar` (nächster Punkt).
*   **Kopierschutz und Defekte** (D5; Entscheidung M, Vorgabe 8) führen im Upload **nicht
    zur Ablehnung**, sondern zur **Warnung**: Die Datei kommt in den Eingang und **bleibt
    dort** (Abschnitt 11.10), sie kommt nicht in die Medien. Warngründe: `kopierschutz`
    (Codec `drms`), `nicht_lesbar` (`ffprobe` scheitert), `probedekodierung_fehlgeschlagen`
    (Probedekodierung von 1 s). Fehlt `ffprobe` in HA, ist das Ergebnis
    `pruefung="nicht_moeglich"`; die Datei bleibt im Eingang (`ffprobe_fehlt`, ohne
    `ffprobe` gibt es auch keine Tags).
*   Lautheit (D6) misst der Container auf dem NAS **später**; sie ist kein Teil des
    Uploads.

### 5.5 Ausgabe

Erfolg: HTTP 200, `Content-Type: application/json`.

```json
{
  "v": 1,
  "upload_id": "9b6c0f7e-3b52-4d1a-9c58-0e2b7a41d9f3",
  "eingang_name": "Folge 4 - Der Rabe.mp3",
  "serie_id": "3f9a1c07b2d4",
  "groesse_bytes": 48210433,
  "pruefung": "ok",
  "hinweis": null,
  "wiederholt": false
}
```

`pruefung` ∈ `ok`, `warnung`, `nicht_moeglich`; `hinweis` ist ein Code (siehe 3.9) oder
`null`; `serie_id` ist die Vorgabe oder `null`; `wiederholt=true` heißt, die Antwort
gehört zu einer früheren Anfrage mit derselben `upload_id` (5.6). Wohin die Datei
einsortiert wird, steht erst nach dem Einsortieren fest (Ereignis `eingang`
`neu_einsortiert`, Befehl `eingang/list`). Fehler: HTTP-Status wie in Abschnitt 7 und der
Körper

```json
{ "v": 1, "fehler": { "code": "format_nicht_erlaubt", "text": "Dieses Dateiformat spielt die Box nicht." } }
```

### 5.6 Idempotenz

Der Upload ändert den Zustand (eine neue Datei). Sendet die Seite dieselbe Datei mit
**derselben `upload_id`** noch einmal (z. B. weil die Antwort verloren ging) und der
Abschluss war erfolgreich, antwortet das Backend mit dem alten Ergebnis
(`wiederholt=true`) und nimmt nichts doppelt auf (es merkt sich die letzten 100
`upload_id` für 1 Stunde im Arbeitsspeicher, **auch wenn der Client weg war**, 5.2).
Ohne `upload_id` oder mit neuer: Die Datei kommt noch einmal in den Eingang (Suffix) und
wird beim Einsortieren als Duplikat erkannt und verworfen (11.10). Ein in Phase A
abgebrochener Versuch hinterlässt keine Datei, ein Neustart des Uploads ist also immer
sicher (Fortsetzen eines halben Uploads gibt es in Version 1 nicht).

### 5.7 Fortschritt

Die Seite sendet mit `XMLHttpRequest` und misst das Senden mit `upload.onprogress`
(`fetch` kann den Fortschritt beim Hochladen nicht melden). Nach dem letzten Byte
läuft die Prüfung auf dem Backend; dafür gibt es das Ereignis `upload` (4.7). Die
HTTP-Antwort kommt erst nach dem Abschluss (Prüfung bis 30 s). Ein Ereignis `empfange`
gibt es nicht.

### 5.8 Was dieser Vertrag nicht regelt

*   Fortsetzen halber Uploads (Wiederaufnahme), parallele Übertragung einer Datei in
    mehreren Teilen.
*   Ein **Folgen-Ordner** (mehrere Tracks) entsteht beim Upload nur über die Tags:
    Dateien mit gleichem Album und gleicher `gruppe` werden zu einem Folgen-Ordner
    (11.3). Eine Nachlieferung einzelner Tracks zu einer schon einsortierten Folge gibt es
    in Version 1 nicht (11.3).
*   Ob Nabu Casa sehr große Anfragen und lange Übertragungen durchlässt: unbekannt, wird
    bei der Abnahme am Handy mit drei Größen gemessen (Abschnitt 8, offener Punkt 1).

### 5.9 Einsortieren nach dem Upload

Nach dem Abschluss wartet das Backend `UPLOAD_SAMMELZEIT_S` = 20 s ab dem **letzten**
Upload-Abschluss (damit die Dateien einer `gruppe` zusammen sortiert werden) und startet
dann einen Durchlauf. Die Ruhezeit von 120 s (11.1) gilt für hochgeladene Dateien nicht,
weil sie vollständig sind.

## 6. Abläufe

### 6.1 Neuer Tobie, Weg A (CUJ 7a, 12)

1.  Eine Box meldet eine Kennung (`…/unknown/<uid>`). Ist sie schon zugeordnet, bestätigt
    das Backend mit `bekannt` und nimmt sie nicht auf (3.4). Sonst nimmt es sie in
    „Neue Tobies“ auf, bestätigt auf `…/ack` (`neu` oder `bekannt`) und sendet das
    Ereignis `neue_tobies` (`neu`/`aktualisiert`).
2.  Die Seite zeigt den Eintrag (`neue_tobies/list`). Tobias wählt den Typ (Serie oder
    einzelne Folge, bei Folge die Folge) oder eine Aktionskarte, gibt dem Tobie auf
    Wunsch einen Namen und tippt.
3.  Die Seite sendet `zuordnung/set` (mit `erwartet_ziel: null`). Das Backend schreibt die
    Zuordnung, erhöht die Revision, veröffentlicht `tobibox/config`, entfernt den
    Eintrag aus der Liste. Die Box übernimmt die Liste und wechselt, wenn der Tobie
    noch liegt, auf das Ziel.
4.  Tobias kann statt dessen `neue_tobies/verwerfen` aufrufen.

### 6.2 Lernmodus, Weg B (CUJ 7b)

Reihenfolge wie in `mqtt-v1.md`, 4.2. Fett die Befehle dieser Schnittstelle. Alle
Wege, die eine Zuordnung schreiben (Seite, Aktion, `ui/*`), laufen durch dieselbe
Funktion (Abschnitt 1).

1.  Die Seite sendet **`lernmodus/start`** (Box, Typ, Ziel). Das Backend merkt sich Box,
    Ziel, Beginn und `befehl_id` und sendet `cmd` `lernen` (`ttl_s` 60). Ereignis
    `lernmodus` `wartet`. Sieht das Backend einen Status der Box mit `lernmodus=true`,
    merkt es sich das für den Vorgang (Voraussetzung für das Ende nach Punkt 6).
2.  Die Box lernt höchstens 2 min und meldet einen aufgelegten Tobie als
    `art="gelernt"` mit `befehl_id` auf `…/unknown/<uid>`.
3.  Das Backend sucht den Vorgang mit dieser `befehl_id` und prüft die Fristen. Ein
    Vorgang, der für die Seite schon `abgelaufen` ist (3.6, „tot“), nimmt die **späte**
    Meldung bis `frist_bis` trotzdem noch an (Funkstörung, Statusreihenfolge).
    *   **Kein Vorgang oder `frist_bis` vorbei** (auch nach **`lernmodus/abbrechen`**):
        `ack` mit `grund="abgelehnt"`, keine Konfiguration. Die Box meldet den Tobie als
        unbekannt erneut; er erscheint in „Neue Tobies“.
    *   **Nach einem HA-Neustart** (der Vorgang ist im Arbeitsspeicher weg): Die letzten
        **20** abgeschlossenen Vorgänge (`befehl_id`, Ergebnis, `uid`, Ziel) stehen im
        HA-Speicher (W-08). Kommt dieselbe `befehl_id` mit einem Ergebnis `zugeordnet`
        erneut (retained-Zustellung, QoS 1), stellt das Backend sicher, dass die aktuelle
        Konfiguration veröffentlicht ist (PUBACK) und wiederholt das `ack zugeordnet`. Steht
        das Ergebnis `abgelehnt` dort, wiederholt es `abgelehnt`. Ist die `befehl_id` ganz
        unbekannt: `abgelehnt`.
    *   **Kennung noch nicht zugeordnet:** weiter bei 4.
    *   **Kennung schon mit genau diesem Ziel (und diesem Namen, falls gesetzt):** keine
        neue Revision. Das Backend sendet `ack` mit `grund="abgelehnt"` (die Box beendet
        das Warten sofort und spielt wie beim normalen Auflegen das bestehende Ziel,
        also dasselbe; keine 10 s Stille, W-07 d) und meldet das Ereignis `lernmodus`
        `zugeordnet` mit `grund="unveraendert"` und dem Text „Der Tobie hat dieses Ziel
        schon.“ (kein `abgelehnt`-Zustand, weil für Tobias nichts schiefging).
    *   **Kennung schon mit anderem Ziel zugeordnet:** Ereignis `lernmodus` `rueckfrage`
        (mit `uid`, `bisher`, `ziel`, `rueckfrage_bis`) und eine HA-Benachrichtigung
        (`persistent_notification`; sie bleibt, bis die Rückfrage beantwortet ist oder
        abläuft; W-09). Die Seite fragt Tobias und sendet **`lernmodus/antwort`**.
        **`rueckfrage_bis` = das spätere von `frist_bis` und Eingang der Meldung + 60 s**
        (die Frist des Vorgangs bleibt 180 s, Vorgabe der Projektleitung; dazu eine
        Mindestzeit von 60 s zum Antworten). Bei `ueberschreiben=false` oder wenn bis
        `rueckfrage_bis` keine Antwort kommt (auch ohne offene Seite): `ack` `abgelehnt`,
        Ende. Bei `true`: weiter bei 4. Bei einer Aktion ohne Seite gilt
        `ueberschreiben=false`, es sei denn, das Aktionsfeld sagt `true` (Abschnitt 1).
4.  Das Backend schreibt die Zuordnung (Revision + 1) und veröffentlicht `tobibox/config`.
    **Erst nach dem PUBACK** der Konfiguration sendet es das `ack`
    `grund="zugeordnet"` (Entscheidung H, W-07 a): Zwei getrennte Veröffentlichungen
    behalten bei QoS 1 ihre Reihenfolge bei Neuübertragung nicht garantiert. **Ohne PUBACK
    (Broker weg) kein `ack`**: Der Vorgang bleibt `wartet` mit gespeicherter Zuordnung; die
    Meldung auf `…/unknown/<uid>` bleibt retained, und das Backend holt Veröffentlichung
    und `ack` beim Wiederverbinden nach, solange `frist_bis` nicht vorbei ist; danach
    `abgelehnt`. Entfernt die Kennung aus „Neue Tobies“. Ereignis `lernmodus` `zugeordnet`.
    **Fehlerwege (W-07 c):** Scheitert Schritt 4, bevor etwas gespeichert ist, sendet das
    Backend `ack` `abgelehnt` (nichts geändert, Klartext im Ereignis) mit einem `grund`:
    `konfig_zu_gross` (256 KiB), `speicherfehler` (HA-Speicher nicht schreibbar),
    `ziel_fehlt` (die Serie oder Folge gibt es inzwischen nicht mehr),
    `konfig_nicht_bereit` (Zustand der Konfiguration nicht `ok`).
5.  Braucht Tobias für die Rückfrage länger als 10 s, spielt ein bekannter Tobie
    zuerst sein altes Ziel und wechselt mit der Zuordnung (gewollt, Entscheidung H,
    `mqtt-v1.md`, 4.2).
6.  **Der Vorgang endet sauber (W-05):** Er endet mit genau einem Zustand aus
    `zugeordnet`, `abgelehnt`, `abgebrochen`, `abgelaufen`, `box_lehnt_ab`. `abgelaufen`
    folgt, sobald (a) ein Status mit `lernmodus=false` nach einem Status mit
    `lernmodus=true` eintrifft (`grund="box_beendet"`), oder (b) 30 s nach `beginn` kein
    Status mit `lernmodus=true` gesehen wurde (`grund="kein_status"`), oder (c) `frist_bis`
    vorbei ist (`grund="frist"`). Lehnt die Box den Befehl ab (`befehl_abgelehnt`), endet
    er mit `box_lehnt_ab`. Ein beendeter Vorgang verschwindet aus `boxen/list`
    (`lernmodus=null`) und steht in den letzten 20 abgeschlossenen. Ein erneuter Start
    erzeugt einen neuen Befehl (3.6).

### 6.3 Medien (CUJ 9)

Serien anlegen, umbenennen, sortieren, verschieben, zusammenführen, löschen und
Hochladen schreiben nur auf die Freigabe. Die Box holt sie mit dem Sync. Es gibt keine
MQTT-Nachricht und keine Revision, **außer** wenn eine Korrektur Tobies auf ein neues
Ziel umschreibt (Nr. 26, 27). Die Seite bietet nach einer Änderung „Sync jetzt“ an
(`box/sync`).

**Löschen mit Tobies (Vorgabe der Projektleitung 09.11.):** Die Seite liest vor dem
Löschen einer Folge oder Serie `serie/get` und zeigt, wenn Tobies darauf zeigen,
Anzahl und **Namen** (bzw. gekürzte Kennungen) mit der Rückfrage „N Tobies zeigen
darauf: … Trotzdem in den Papierkorb?“. Erst die Bestätigung sendet den Befehl mit
`tobies_bestaetigt=true`. Die Zuordnung bleibt; die Box spielt bis zur
Wiederherstellung die Überraschung.

### 6.4 Hochladen vom Handy (CUJ 9)

1.  Die Seite wählt die Dateien, auf Wunsch die Serie (Vorgabe, 11.5), erzeugt je Datei
    eine `upload_id` und für zusammengehörige Dateien (ein Hörbuch aus mehreren Dateien)
    eine gemeinsame `gruppe`.
2.  Sie holt ein frisches Token, sendet nacheinander je Datei `POST …/upload` und
    zeigt den Fortschritt (5.7).
3.  Die Antwort liefert `pruefung`; bei `warnung` zeigt die Seite den Grund und dass
    die Datei im Eingang bleibt.
4.  Das Backend sortiert nach 20 s Sammelzeit ein (5.9); Ereignis `eingang`
    `neu_einsortiert` zeigt, wohin die Datei kam und ob „bitte prüfen“ gesetzt ist.
    `medien` `serien_geaendert` lässt andere offene Fenster neu laden.

### 6.5 Einsortieren vom PC (Entscheidung M)

1.  Tobias legt einen Ordner (z. B. einen Hörbuch-Download) oder Dateien in
    `tobibox/eingang/`.
2.  Der nächste Durchlauf (Timer alle 10 min, Öffnen der Seite oder `eingang/sortieren`)
    findet den Eintrag; solange er sich noch ändert, steht er auf `wartet`.
3.  Nach der Ruhezeit liest das Backend die Tags, gruppiert zu Alben, bestimmt Serie,
    Reihenfolge und Namen (Abschnitt 11), legt Serien und `serie.json` an bzw. ergänzt
    sie und verschiebt die Dateien.
4.  Ereignis `neu_einsortiert` je Eintrag; die Seite zeigt unter „Eingang“ das
    Ergebnis, Folgen mit „bitte prüfen“ sind markiert.
5.  Tobias korrigiert bei Bedarf: Serie wechseln (`folge/verschieben`), Namen ändern
    (`serie/rename`, `folge/rename`), Reihenfolge ändern (`folgen/order`), zwei Serien
    zusammenführen (`serien/zusammenfuehren`), und bestätigt (`einsortierung/bestaetigen`).
6.  Blockiertes (Kopierschutz, defekt) bleibt im Eingang mit Hinweis (11.10).

## 7. Gemeinsame Fehlercodes

Die Codes `invalid_format`, `unauthorized`, `unknown_command`, `unknown_error` sind
die von **Home Assistant**; alle anderen sind eigene Codes dieses Vertrags. Bei
WebSocket-Befehlen steht der Code in `error.code`; HA kennt im Fehlerobjekt nur `code` und
`message`. **Maschinenlesbare Einzelheiten stehen deshalb nie nur in `message`:**
Die Seite liest bei Bedarf den Zustand neu (z. B. `zuordnung/list` nach
`zuordnung_existiert`, `serie/get` nach `tobies_betroffen`).

| Code | HTTP | Bedeutung | Befehle |
|---|---|---|---|
| `invalid_format` | 400 | Eingabe passt nicht zum Schema (fehlendes Pflichtfeld, falscher Typ, unbekanntes Feld, `bestaetigt` nicht `true`) | alle |
| `unauthorized` | 401 oder 403 | Nutzer ist kein Administrator. Bei HTTP-Ansichten macht HA daraus 401, bei WebSocket gilt der Code; die Seite wertet `code` aus (W-19). | alle schreibenden |
| `unknown_command` | – | Befehl dem Backend unbekannt (Seite neuer als Backend) | alle |
| `unknown_error` | 500 | Fehler im Backend (Fehler im Protokoll von HA); die Seite zeigt „Das hat nicht geklappt“ | alle |
| `anfrage_id_konflikt` | 409 | gleiche `anfrage_id` mit anderem Befehl oder anderen Feldern | die mit `anfrage_id` |
| `medien_nicht_erreichbar` | 503 | Die NAS-Freigabe ist nicht eingebunden oder antwortet nicht | Medien, Eingang, Papierkorb, Upload, Export |
| `medien_schreibfehler` | 500 | Schreiben auf die Freigabe schlug fehl (Rechte, Platz, Verbindung, Namen, die die Freigabe nicht annimmt) | Medien, Eingang, Papierkorb |
| `kein_speicher` | 507 | Auf der Freigabe ist kein Platz mehr (vorab geprüft, 5.1) | Upload |
| `mqtt_nicht_verbunden` | 503 | Der Broker ist nicht erreichbar; der Befehl wurde **nicht** gesendet. (Konfigurationsänderungen scheitern daran nicht: Sie sind gespeichert, `veroeffentlicht=false`.) | Befehle an Boxen |
| `serie_nicht_gefunden` | 404 | Serien-ID unbekannt | Serie, Folgen, Upload, Zuordnung, Lernmodus, Papierkorb |
| `folge_nicht_gefunden` | 404 | Folge steht nicht in `folgen` der Serie | Folgen, Zuordnung, Lernmodus |
| `eintrag_nicht_gefunden` | 404 | Papierkorb-Eintrag oder Eingangs-Eintrag unbekannt | Papierkorb, Eingang |
| `export_nicht_gefunden` | 404 | Es gibt keine Exportdatei | `konfig/aus_export` |
| `export_ungueltig` | 422 | Die Exportdatei ist nicht lesbar oder nach `data-model.md` ungültig; nichts wurde übernommen | `konfig/export_lesen`, `konfig/aus_export` |
| `box_unbekannt` | 404 | Box-Name ist nicht eingerichtet | Boxen, Lernmodus |
| `box_offline` | 409 | Die Box ist nach `…/online` nicht erreichbar oder HA kennt noch keine Nachricht (`online=null`, W-25) | `lernmodus/start`, `box/sync` |
| `kennung_ungueltig` | 400 | `uid` ist nicht kanonisch (`reader-v1.md`, Abschnitt 4) | Zuordnung, Neue Tobies |
| `ziel_ungueltig` | 400 | `ziel` ist unvollständig oder widersprüchlich (z. B. `folge` ohne `serie`, unbekannte `aktion`, `aktion` im Lernmodus), **zeigt auf die Überraschungs-Serie**, oder Quelle und Ziel sind dieselbe Serie / eine Überraschungs-Serie beim Zusammenführen | Zuordnung, Lernmodus, `folge/verschieben`, `serien/zusammenfuehren` |
| `zuordnung_existiert` | 409 | Die Kennung hat schon ein anderes Ziel, `ueberschreiben` fehlt | `zuordnung/set` |
| `zuordnung_geaendert` | 409 | `erwartet_ziel` stimmt nicht mehr (ein anderes Fenster hat die Zuordnung geändert); die Seite lädt neu | `zuordnung/set`, `zuordnung/remove` |
| `konfig_zu_gross` | 413 | Die Konfiguration würde 256 KiB überschreiten (`mqtt-v1.md`, Abschnitt 1) | `zuordnung/set`, `lernmodus/antwort` |
| `konfig_nicht_bereit` | 409 | `konfig.zustand` ist nicht `ok` (Abschnitt 13); die Seite zeigt die Warnung | alle, die die Konfiguration ändern |
| `name_ungueltig` | 400 | Name leer, zu lang oder nach der Bereinigung (Abschnitt 12) leer | Serie, Folge, Tobie-Name, Upload |
| `reihenfolge_ungueltig` | 400 | Die Liste ist keine Umstellung der vorhandenen Folgen | `folgen/order` |
| `stand_veraltet` | 409 | `stand` passt nicht mehr; die Seite lädt neu | alle mit `stand` |
| `tobies_betroffen` | 409 | Tobies zeigen auf das, was gelöscht oder verschoben wird, und `tobies_bestaetigt` fehlt; die Seite fragt Tobias und liest `serie/get` | `folge/delete`, `serie/delete`, `folge/verschieben`, `serien/zusammenfuehren` |
| `ueberraschung_existiert` | 409 | Es gibt schon eine Überraschungs-Serie | `serie/create` |
| `lernmodus_laeuft` | 409 | Für die Box läuft ein lebender Lernmodus mit anderem Ziel; erst abbrechen | `lernmodus/start` |
| `kein_lernmodus` | 404 | Kein offener Vorgang mit dieser `befehl_id` | `lernmodus/antwort` |
| `rueckfrage_abgelaufen` | 409 | `rueckfrage_bis` ist vorbei; das Backend hat die Meldung abgelehnt | `lernmodus/antwort` |
| `datei_existiert` | 409 | Im Serien-Ordner gibt es den Namen schon | `papierkorb/restore` (Folge) |
| `serie_existiert` | 409 | Die Serien-ID ist schon vergeben | `papierkorb/restore` (Serie) |
| `upload_laeuft` | 409 | Ein Upload mit dieser `upload_id` läuft noch | Upload |
| `zu_viele_uploads` | 429 | Es laufen schon `upload_parallel` Uploads | Upload |
| `datei_zu_gross` | 413 | größer als `upload_max_bytes` | Upload |
| `format_nicht_erlaubt` | 415 | Endung oder erkanntes Format nicht nach D5 | Upload |

Der Körper einer HTTP-Fehlerantwort des Uploads ist in 5.5 beschrieben. Eine
unbekannte `code`-Zeichenfolge (neueres Backend) zeigt die Seite mit `message`
beziehungsweise `fehler.text`.

## 8. Grenzen

Aus dem Quelltext von Home Assistant (Zweig `dev`, abgerufen am 09.11.2026; **maßgeblich ist die
feste HA-Version** der Stufe 3a, **2026.11.x**, die genaue Patch-Version nennt Tobias beim
Start von AP 3.1) und aus dem Design:

| Grenze | Wert | Quelle und Folge |
|---|---|---|
| Größe einer **eingehenden** WebSocket-Nachricht | 4 MiB (Vorgabe von aiohttp; HA setzt `WebSocketResponse(heartbeat=55, …)` ohne eigenen Wert) | Darum **keine** Dateien über WebSocket, sondern HTTP (Abschnitt 5). Eingaben dieses Vertrags sind klein (wenige KiB). |
| Größe einer Nachricht, die dieser Vertrag **sendet** | höchstens 64 KiB (wie `mqtt-v1.md`) | In HA gibt es keine feste Grenze für ausgehende Nachrichten (nur die Warteschlange); 64 KiB ist die eigene Wahl dieses Vertrags. Alle Listen blättern deshalb mit `limit`/`offset`: `neue_tobies/list`, `papierkorb/list` (höchstens 200 Einträge ≈ 50 KiB), `zuordnung/list` (höchstens 100 Einträge ≈ 35 KiB, W-13), `eingang/list` (höchstens 100). `serien/list` und `boxen/list` sind durch die Anzahl der Serien bzw. Boxen klein. |
| Nachrichten je Verbindung, bis HA sie trennt | 4096 wartende Nachrichten (`MAX_PENDING_MSG`) | Ereignisse sind gebündelt (4). |
| Lebenszeichen der WebSocket-Verbindung | 55 s (`heartbeat`) | von HA, nichts zu tun |
| Anmeldung | Die Verbindung muss die Authentifizierung (`auth`) innerhalb weniger Sekunden schicken | macht `hass.connection` der Oberfläche |
| Normale HTTP-Anfragen von HA | **16 MiB** | **Belegt (W-14):** `homeassistant/components/http/server.py`, Zeile 69 `MAX_CLIENT_SIZE: Final = 1024**2 * 16`, benutzt in Zeile 278 (`client_max_size=MAX_CLIENT_SIZE`); Forenmeldung zu 2026.7/2026.8 „Maximum request body size 16777216 exceeded“ (Issue #177999, „not a bug“). Die Grenze gilt für `read()`, `post()`, `json()` und `part.read()`, **nicht** für das Lesen mit `request.multipart()` und `part.read_chunk()`. HA-eigene Uploads setzen die Grenze je Ansicht (`file_upload` 100 MiB, `media_source` 20 MiB); `HomeAssistantView.max_body_size` (`helpers/http.py`, Zeile 139) wirkt vor dem Handler. Der Upload setzt es **nicht** und streamt. AP 3.1 belegt es mit einem Test über 16 MiB (z. B. **40 MiB**) gegen die feste HA-Version und deren aiohttp. |
| Größe einer Audiodatei | `upload_max_bytes`, Vorgabe **500 MiB**, in der Einrichtung der Integration einstellbar (Vorgabe der Projektleitung 09.11.; ein Hörspiel ist meist 50–200 MiB) | Schutz vor vollem Speicher und langen Übertragungen über Nabu Casa. Erst nach der Abnahme anheben. |
| Gleichzeitige Uploads | 2 (`upload_parallel`) | 429 `zu_viele_uploads` |
| Freier Platz vor dem Upload | `Content-Length` + 100 MiB Reserve gegen freien Platz der Freigabe | 507 `kein_speicher` vor dem Lesen |
| Block des Uploads | 1 MiB | fest in Version 1 |
| Zugriffstoken | gültig ~30 min | gilt für den **Start** einer Anfrage; die Seite erneuert vor jedem Upload. |
| Länge eines Namens | Serie 1–100 Zeichen; Folge-Anzeige 1–200 Zeichen; Tobie-Name 1–60 Zeichen; Datei- und Ordnername höchstens 255 Bytes (UTF-8) **und** 255 UTF-16-Einheiten, die kürzere Grenze gilt (Abschnitt 12) | `data-model.md` |
| Ruhezeit im Eingang | 120 s (`EINGANG_RUHE_S`); Sammelzeit nach Upload 20 s | Abschnitt 11.1, 5.9 |
| Nabu Casa | unbekannt (Upload-Größe, Dauer) | **Abnahme am Handy mit drei Größen: 20 MiB, 150 MiB, 500 MiB, jeweils mit gemessener Dauer** (Stufe 3a, offener Punkt 1). Ausweg: Dateien per PC in den Eingang (D4, Entscheidung M). |

## 9. Versionierung

*   **Version 1** ist diese Fassung. Sie steht in `hello` (`v`) und in jedem
    Ereignis und jeder HTTP-Antwort des Uploads (`"v": 1`).
*   **Ohne Erhöhung** erlaubt: neue Befehle (neue Namen), neue **optionale**
    Eingabefelder, neue Felder in Ausgaben und Ereignissen, neue `art`-Werte, neue
    Themen, neue Hinweis-Codes, neue Fehlercodes für neue Fälle, neue Werte in
    `faehigkeiten`. Die Seite ignoriert Unbekanntes in Antworten und Ereignissen.
*   **Eingaben sind strenger.** Der HA-Schemaprüfer lehnt **unbekannte Eingabefelder
    ab** (`invalid_format`). Eine neue Seite darf deshalb ein neues optionales
    Eingabefeld nur senden, wenn `hello.faehigkeiten` es zusagt. Seite und Backend
    liegen im selben Paket (`custom_components/tobibox/`), und die Adresse der Seite
    trägt die Version der Integration (`/tobibox_static/tobibox-panel.js?v=<version>`), um
    den Browser-Zwischenspeicher zu umgehen; das Problem entsteht nur bei einer
    alten Seite im Zwischenspeicher.
*   **Erhöhung** von `v` bei: Befehl, Feld oder Code entfernt oder umbenannt,
    Bedeutung oder Wertebereich geändert, neues **Pflichtfeld**. Dann bekommt die neue
    Hauptversion einen **neuen Wurzelnamen** für die Befehle (`tobibox2/…`) und läuft
    neben der alten, bis die Seite umgestellt ist (wie `mqtt-v1.md`, Abschnitt 8). Der
    HTTP-Pfad erhält `/api/tobibox2/…`.
*   **Prüfung beim Start:** Die Seite ruft zuerst `tobibox/hello` mit ihrem `v`. Ist
    das `v` der Antwort **kleiner** als das der Seite, oder kommt `unknown_command`,
    zeigt sie „Bitte die Seite neu laden (Strg+F5)“ und tut nichts weiter. Ist es
    **größer**, kennt die Seite nur ihre eigene Version (die alte Befehlsgruppe läuft
    weiter, solange das Backend sie noch anbietet).
*   Eine Änderung dieses Vertrags geht an die Projektleitung. Backend und Seite ändern
    sie nicht eigenmächtig.


## 10. Später (Namen reserviert, Inhalt noch nicht festgelegt)

Diese Befehle gehören **nicht** zu Version 1 der Stufe 3a. Ihre Namen sind vergeben;
die Eingabe, Ausgabe und Fehler stehen fest, sobald die Stufe beginnt. Sie brauchen
nur Ergänzungen (Abschnitt 9, „Ohne Erhöhung“). (`serie/delete` und `folge/rename`
sind seit dem 09.11. Teil von Version 1: Nr. 24 und 25.)

| Befehl | Stufe | Skizze (Vorschlag, keine Festlegung) |
|---|---|---|
| `tobibox/einstellungen/get` | 4 (AP 4.7) | Liest `leise_zeiten` (`zeitzone`, `fenster`), `gute_nacht` (`timer_min`, `ausblenden_s`) und optional `hinweis_pegel` und `lesezeichen_tage` (Entscheidung N, 09.11.): dieselben Schemas und Wertebereiche wie in `data-model.md`, Abschnitt 2; dazu `konfig`. Rechte: alle. |
| `tobibox/einstellungen/set` | 4 (AP 4.7) | Setzt `leise_zeiten` und/oder `gute_nacht` als **ganze Objekte** und/oder `lesezeichen_tage` (ganze Zahl 0 bis 365, `0` = nie; Entscheidung N, 09.11.; das Feld ist dafür **reserviert**, die Seitenbedienung kommt in Stufe 4); Prüfung wie die Box (ungültig: ganze Änderung abgelehnt, Fehlercode `einstellung_ungueltig` mit Pfad in `message`). Rechte: Admin. Idempotent. MQTT: `tobibox/config` (Revision + 1). Fähigkeit `einstellungen`. Die **Leise-Zeiten bleiben in Stufe 4** (Vorgabe der Projektleitung 09.11.). |
| `tobibox/box/update` | 3b (AP 3.8/3.11) | `{"box", "version"?}`; Backend nimmt ohne Angabe die neueste Version aus `releases/`. Rechte: Admin. MQTT: `cmd` `update`, 300 s (`mqtt-v1.md`, 3.7). Ergebnis über `status.update` (Ereignis `boxen`). Fehler wie bei `box/sync`, dazu `keine_version`. Fähigkeit `update`. |
| `tobibox/releases/list` | 3b | Liest die vorhandenen Pakete auf `releases/` (nur Name und Version). Rechte: alle. |
| `tobibox/eingang/track_anhaengen` | offen | Nachlieferung einzelner Tracks zu einer schon einsortierten Folge (11.3: in Version 1 nicht vorgesehen) |

**Schon in Stufe 3a nötig:** Das Backend legt `leise_zeiten` (`zeitzone`
`Europe/Berlin`, `fenster` leer) und `gute_nacht` (`timer_min` 30, `ausblenden_s` 60,
die Vorschläge des Designs) in der Konfiguration an, weil `config.json` sie als Pflicht
verlangt, und schreibt sie bei jeder Änderung unverändert fort. Dasselbe gilt für die
optionalen Felder `ton_pegel`, `hinweis_pegel` und `lesezeichen_tage` (Entscheidung N, 09.11.):
`ton_pegel` und `hinweis_pegel` legt das Backend nicht an, **verliert sie aber nie** beim Schreiben
einer neuen Revision. **(09.11., Befund AP 3.1)** `lesezeichen_tage` legt es mit der Vorgabe 14 an
(Bereich 0 bis 365, `0` = nie), veröffentlicht es in jeder Liste, exportiert es und holt es mit
`konfig/aus_export` zurück; eine Bedienung gibt es vorerst nicht. **Lautheit (D6)** hat
keinen Befehl: Der Container läuft nach Zeitplan, ohne Auslöser aus HA (Design).
Sichtbar wird sie höchstens später als optionales Feld an der Folge.

## 11. Einsortieren nach Metadaten (Entscheidung M, 09.11.)

Tobias legt einen Ordner (zum Beispiel einen Hörbuch-Download) oder Dateien in den
**Eingang**. Die Integration liest die Tags der Audiodateien und sortiert **vollautomatisch**
in die Medienstruktur ein („wie bei Plex“), danach korrigiert Tobias auf der Seite. Die
Medienstruktur auf den Boxen bleibt unverändert (Serien-Ordner mit `serie.json`, Folgen
als Datei oder Folgen-Ordner, Entscheidung F); der Box-Code weiß davon nichts. Die
Regeln in diesem Abschnitt sind so festgelegt, dass jede Zeile als Test geschrieben werden
kann (`homeassistant/tests/test_eingang.py`, AP 3.1). Die Regeln gelten gleich für den
Eingang vom PC und für Uploads (Abschnitt 5).

### 11.1 Ort, Durchlauf, Ruhezeit

*   **Ort:** `tobibox/eingang/` auf dem NAS, **neben** `medien/`, `export/` und
    `releases/` (gleiche Freigabe, damit das Verschieben in `medien/` ein atomares
    Umbenennen ist). HA hat dort vollen Schreibzugriff (Entscheidung D); Tobias legt den
    Ordner an (AP 3.5). Fehlt er, antworten `eingang/list` und `eingang/sortieren` mit
    `medien_nicht_erreichbar`. Bleibt das Umbenennen aus technischen Gründen
    (anderes Dateisystem) aus, bleibt der Eintrag liegen, Hinweis
    `verschieben_fehlgeschlagen`; kopiert wird nie.
*   **Nicht gesynct:** Der Eingang liegt außerhalb des rsync-Moduls `medien` und wird von
    der Box **nie** geholt. Zusätzlich schließen NAS-Modul und Box die Namen
    `_upload`, `_papierkorb` und `eingang` im Sync aus (falls jemand einen davon in
    `medien/` anlegt; Design AP 3.4, AP 3.5). Die Prüfung der Integration ignoriert sie
    ebenfalls (Abschnitt 12).
*   **Eintrag:** Eine Datei oder ein Ordner auf der obersten Ebene von `eingang/`
    (Objekt in 3.9). Tiefer als 5 Ebenen im Eintrag wird nicht gelesen.
*   **Durchlauf:** Er läuft alle 10 min (Timer, nach der Prüfung der Freigabe), beim Öffnen
    der Seite, mit `eingang/sortieren` und 20 s nach dem letzten Upload (5.9). Immer nur
    **ein** Durchlauf zugleich; ein zweiter Aufruf meldet `laeuft_bereits`.
*   **Ruhezeit:** Ein Eintrag ist erst `bereit`, wenn (a) die neueste Änderungszeit aller
    Dateien darin mindestens 120 s (`EINGANG_RUHE_S`) zurückliegt **und** (b) Dateianzahl
    und Gesamtgröße beim vorigen Scan, der mindestens 30 s zurückliegt, gleich waren
    (b ist nötig, weil Kopierprogramme die alte Änderungszeit der Quelle übernehmen). Sonst
    `wartet`; solange ein Eintrag wartet, plant das Backend nach 60 s einen weiteren Durchlauf.
    `sofort=true` und Uploads übergehen die Ruhezeit.
*   **Ignoriert** werden Dateien, deren Name mit `.` beginnt (`._*` von macOS) und
    Dateien mit anderer Endung als der Liste aus `data-model.md`, Abschnitt 5 (Bilder,
    Texte). Sie werden gezählt (`ignoriert`).
*   **Reihenfolge der Einträge** im Durchlauf: `zuerst_gesehen` aufsteigend, bei Gleichheit
    die natürliche Sortierung des Namens (`data-model.md`, Abschnitt 5). Ihre laufende
    Nummer ist der **Eingangsindex** (0, 1, 2 …), der in 11.6 gebraucht wird.

### 11.2 Tags lesen

Die Tags kommen von `ffprobe` (gleicher gehärteter Aufruf wie 5.4): `format.tags` und die
Tags des ersten Audio-Stroms; ein Schlüssel in `format.tags` gilt vor dem Strom. Schlüssel
werden **ohne Unterscheidung von Groß-/Kleinschreibung** verglichen. Werte werden vor jeder
Auswertung **normiert**: Unicode NFC, Steuerzeichen entfernt, Leerraum gekürzt und auf ein
Leerzeichen zusammengefasst, auf 200 Zeichen gekürzt. Ein Wert ohne einen einzigen
Buchstaben oder eine Ziffer gilt als **leer**. Diese Schlüssel werden gelesen
(Aliase in Vorrangfolge, der erste nicht leere gilt):

| Feld | Tag-Schlüssel (Vorrang von links) | Auswertung |
|---|---|---|
| `album` | `album` | Text. Ein Zusatz am Ende der Form `(CD 2)`, `[Disc 1]`, `- CD 3`, auch `CD 2/4`, wird für Gruppenschlüssel und Anzeige entfernt (Teil `cd`, `disc`, `disk`; **nicht** `Teil`, denn „Teil 2“ ist oft eine eigene Folge). |
| `album_interpret` | `album_artist`, `albumartist`, `album artist` | Text. **Platzhalter** gelten als leer (Vergleich mit `norm`): `various artists`, `various`, `verschiedene`, `verschiedene interpreten`, `diverse`, `va`, `unknown`, `unbekannt`, `n/a`. |
| `interpret` | `artist`, `author`, `composer` | schwacher Rückgriff (11.5), gleiche Platzhalter wie oben |
| `serien_tag` | `series`, `serie`, `show`, `movement_name`, `mvnm`, `grouping`, `tit1`, `content_group` | Text. Bei m4b zum Beispiel die Atome für Serie/Satz, bei mp3 `TIT1`/`MVNM`. |
| `nummer_tag` | `series_part`, `series-part`, `seriespart`, `part`, `movement`, `mvin`, `episode_sort`, `episode_id` | die erste ganze Zahl am Anfang (`^\s*0*(\d{1,4})`); sonst leer |
| `titel` | `title` | Text |
| `track` | `track`, `tracknumber` | `3` oder `3/12` → 3 (die Zahl vor dem `/`); sonst leer |
| `disc` | `disc`, `discnumber`, `part_of_set` | `1` oder `1/2` → 1; sonst leer |
| `datum` | `date`, `originaldate`, `original_date`, `year` | `YYYY`, `YYYY-MM` oder `YYYY-MM-DD` (Jahr 1900–2100) → `YYYY-MM-DD`, fehlender Monat/Tag = `01`; sonst leer. **Nicht** `creation_time` (das ist der Zeitpunkt der Aufnahme der Datei). |

Die genauen Schlüsselnamen, die `ffprobe` je Container liefert (`mp3`, `m4a`/`m4b`,
`flac`, `ogg`), belegt AP 3.1 mit Beispieldateien von Tobias und ergänzt die Aliase in
dieser Tabelle (eine additive Änderung). **Vergleich** zweier Werte heißt immer
`norm(a) == norm(b)` mit `norm(x)`: Unicode NFKC, `casefold`, dann alle Zeichen entfernen,
die kein Buchstabe und keine Ziffer sind (`Die drei ???` → `diedrei`). Ergibt das leer,
gilt der gekürzte `casefold`-Wert.

**Folgen-Nummer aus einem Text** (Albumname, bei einer Einzeldatei auch der Titel): Es gilt
die erste passende Regel, innerhalb einer Regel der erste Treffer; Zahlen mit mehr als
4 Ziffern passen nie; führende Nullen zählen nicht (`007` → 7). Die Regeln (ohne
Unterscheidung von Groß-/Kleinschreibung):

| Nr. | Muster | Beispiel → Ergebnis |
|---|---|---|
| R1 | Stichwort `folge`, `teil`, `band`, `episode`, `ep`, `nr`, `nummer`, `vol`, `volume` (am Wortanfang), optional `.`, `:` oder `#`, dann die Zahl | `Der Rabe - Folge 12: Der Wald` → 12; `Nr. 3` → 3; `Teil 2 von 3` → 2 |
| R2 | Zahl am Textanfang, gefolgt von einem Trennzeichen `- – — : . _ )` und weiterem Text | `3 - Der Anfang` → 3; `007: Gold` → 7 |
| R3 | `#` und Zahl | `Abenteuer #5` → 5 |
| R4 | Zahl in runden Klammern am Textende | `Der Rabe (12)` → 12 |

`Das Jahr 1984` und `2000 Meilen` ergeben **keine** Nummer.

### 11.3 Gruppieren: Album = Folge

Die Einheit des Einlesens ist die **Datei**; die Einheit des Ergebnisses die **Gruppe**:
Eine Gruppe wird **eine Folge**. Besteht sie aus einer Datei, ist die Folge diese Datei;
besteht sie aus mehreren, ist die Folge ein **Folgen-Ordner mit Tracks** (Entscheidung F).

*   **Datei mit `album`, im Ordner-Eintrag:** Gruppe = (Eintrag, `norm(album)`). Dateien
    desselben Albums in verschiedenen Unterordnern des Eintrags (`CD1/`, `CD2/`) sind eine
    Gruppe.
*   **Datei mit `album`, lose in `eingang/`:** Gruppe = `norm(album)` über alle losen
    Dateien des Durchlaufs.
*   **Datei ohne `album`, im Ordner-Eintrag:** Alle solchen Dateien des Eintrags bilden
    **eine** Gruppe (Kennzeichen `tags_fehlen`). Bei mehreren Dateien ist der Anzeigename der Name des
    Eintrags (Folgen-Ordner). Ist es nur **eine** Datei, ist ihr Anzeigename der `titel`, sonst der
    Dateiname ohne Endung, nicht der Ordnername (09.11., Befund AP 3.1; Testfall T4).
*   **Datei ohne `album`, lose:** eine Gruppe je Datei (Kennzeichen `tags_fehlen`).
*   **Ein Ordner mit vielen Dateien ohne Tags** wird also eine Folge mit vielen Tracks
    (`bitte prüfen`). Aufteilen in einzelne Folgen geht in Version 1 nur durch Tags
    ergänzen und die Dateien erneut in den Eingang legen.
*   **Nachlieferung:** Kommt später eine Datei zu einem Album, das schon einsortiert ist,
    wird sie eine **neue Folge** (Kennzeichen `folge_gleicher_name`); die vorhandene Folge
    wird nicht ergänzt (Version 1).

### 11.4 Tag → Ergebnis (Zusammenfassung)

| Ergebnis | Quelle, in Vorrangfolge | Kennzeichen, wenn die schwächere Quelle gilt |
|---|---|---|
| **Folge: Anzeigename** | 1. `album` (ohne CD-Zusatz); 2. bei einer einzelnen Datei der `titel`; 3. bei einer einzelnen Datei **der Dateiname ohne Endung** (nicht der Ordnername, auch wenn die Datei in einem Ordner-Eintrag liegt); bei einem Folgen-Ordner (mehrere Dateien) der **Name des Eintrags** (Ordner) (09.11., Befund AP 3.1) | `tags_fehlen` ab 2 |
| **Folge: Name auf der Platte** | Datei: Dateiname nach Abschnitt 12; Folgen-Ordner: Anzeigename nach Abschnitt 12 | `name_geaendert` bei Ersatzname |
| **Serie: Name** | 11.5 | `serie_aus_interpret`, `serie_aus_ordner` |
| **Folgen-Nummer** | 1. `nummer_tag`; 2. Regeln R1–R4 auf den Albumnamen; 3. bei einer Datei R1–R4 auf den Titel; 4. keine | – |
| **Datum** | frühester `datum` aller Dateien der Gruppe; sonst keines | – |
| **Reihenfolge der Folgen** | 11.6 | – |
| **Reihenfolge der Tracks** | 11.7 | `track_doppelt`, `track_teils_leer` |

### 11.5 Serie bestimmen und zusammenführen

Je Gruppe, in dieser Vorrangfolge (der erste Treffer gilt):

1.  **Vorgabe der Seite:** Kam die Datei per Upload mit `serie_id`, gilt diese Serie (auch
    die Überraschungs-Serie). Gibt es die Serie nicht mehr: weiter mit 2 und Kennzeichen
    `vorgabe_serie_fehlt`.
2.  **`serien_tag`** (Mehrheit in der Gruppe, 11.8).
3.  **`album_interpret`** (Mehrheit; Platzhalter zählen als leer).
4.  **`interpret`**, wenn alle Dateien der Gruppe denselben haben → Kennzeichen
    `serie_aus_interpret`.
5.  **Name des Eintrags** (Ordner) → Kennzeichen `serie_aus_ordner`.
6.  Sonst (lose Datei ohne Tags) die Serie **`Einzelfolgen`** → Kennzeichen
    `serie_aus_ordner`.

Die Schreibweise des Namens ist die des ersten Treffers unter den Dateien der Mehrheit,
gekürzt auf 100 Zeichen.

**Zusammenführen:** Der **Serienschlüssel** eines Namens ist `norm(name)` (11.2). Alle
Gruppen eines Durchlaufs mit gleichem Schlüssel und alle vorhandenen Serien mit
`typ="normal"`, deren Anzeigename **oder** Ordnername denselben Schlüssel hat, sind
**dieselbe Serie**: Die Folgen werden dort einsortiert. Gibt es mehrere passende
vorhandene Serien, gilt die mit dem frühesten `angelegt_am` (Kennzeichen
`serie_mehrdeutig`). Gibt es keine, wird eine **neue** Serie angelegt (zufällige ID,
Ordnername nach Abschnitt 12, Anzeigename wie oben; ist die Quelle `interpret` oder der
Ordner, trägt die neue Serie selbst das Kennzeichen `pruefen`). Die Überraschungs-Serie
nimmt nie automatisch etwas auf (nur über die Vorgabe der Seite).

### 11.6 Reihenfolge der Folgen in der Serie

Jede Folge hat `nummer` (11.4), `datum` und ihren Eingangsindex (11.1). Der
**Sortierschlüssel** einer Folge:

```
mit Nummer:   (0, nummer, datum oder "9999-99-99", eingangsindex)
ohne Nummer:  (1, 0,      datum oder "9999-99-99", eingangsindex)
```

Die neuen Folgen einer Serie in einem Durchlauf werden nach diesem Schlüssel aufsteigend
geordnet: erst die mit Nummer (nach Nummer), dann die ohne (nach Datum, dann
Eingangsreihenfolge). Gleiche Nummern behalten die Reihenfolge von Datum und Eingangsindex
und tragen das Kennzeichen `nummer_doppelt`.

Eine **neue Serie** erhält diese Reihenfolge als `folgen`. In eine **vorhandene Serie**
wird jede neue Folge (in dieser Reihenfolge) **einzeln eingefügt**, ohne die vorhandene
Reihenfolge zu ändern (eine Reihenfolge, die Tobias von Hand gesetzt hat, bleibt):

*   Hat die neue Folge eine Nummer `n`, suche in der aktuellen Liste die Folgen mit
    bekannter Nummer (`folgen_info.nummer`). Gibt es eine mit Nummer **größer als `n`**,
    wird sie **vor der ersten** davon eingefügt; sonst **hinter der letzten mit Nummer
    ≤ `n`**; gibt es gar keine mit Nummer, **hinten**.
*   Hat sie keine Nummer, kommt sie **hinten** an.

Dieselbe Einfügeregel gilt für `folge/verschieben` und `serien/zusammenfuehren`.

### 11.7 Reihenfolge der Tracks und Dateinamen im Folgen-Ordner

Die Box ordnet die Tracks eines Folgen-Ordners nach der **natürlichen Sortierung der
Dateinamen** (`data-model.md`, Abschnitt 5). Das Backend baut deshalb die Namen so, dass
diese Sortierung die gewünschte Reihenfolge ergibt.

*   **Gewünschte Reihenfolge:** Sortiert nach (`disc`, `track`, natürliche Sortierung des
    relativen Pfads). Fehlt `disc`, kommt die CD-Nummer aus dem Albumnamen (Zusatz `CD 1`, `Disc 2` usw., 11.2), sonst gilt 1 (09.11., Befund AP 3.1). Dateien **mit** `track` kommen vor Dateien
    ohne (Kennzeichen `track_teils_leer`). Hat **keine** Datei `track`, gilt allein die
    natürliche Sortierung des relativen Pfads im Eintrag (Unterordner `CD1` vor `CD2`).
    Zwei Dateien mit gleichem (`disc`, `track`) bleiben beide, in Pfad-Reihenfolge
    (Kennzeichen `track_doppelt`).
*   **Namen:** Zuerst werden die Dateinamen nach Abschnitt 12 bereinigt (ohne Pfad). Ergibt
    die natürliche Sortierung dieser Namen **schon** die gewünschte Reihenfolge und sind
    die Namen (ohne Rücksicht auf Groß-/Kleinschreibung) eindeutig, **bleiben sie**.
    Sonst erhalten **alle** Tracks der Folge das Präfix `NNN ` (laufende Nummer ab 1,
    mindestens drei Stellen, bei mehr als 999 Tracks so viele wie nötig), z. B.
    `001 Kapitel 1.mp3`.
*   Eine Folge aus einer Datei wird nicht umbenannt (außer nach Abschnitt 12).

### 11.8 Widersprüche in einem Ordner

Die Tags innerhalb einer Gruppe stimmen oft nicht überein. Regel für jedes Feld
(`serien_tag`, `album_interpret`, `interpret`, `nummer_tag`, `datum`): Es zählen nur nicht
leere Werte; die **Mehrheit** nach `norm` gewinnt, bei Gleichstand der Wert der ersten Datei
in der gewünschten Track-Reihenfolge. Haben die nicht leeren Werte **mehr als einen**
Wert, kommt ein Kennzeichen.

| Widerspruch | Regel | Kennzeichen |
|---|---|---|
| Verschiedene `album` in einem Ordner-Eintrag | verschiedene Gruppen, also verschiedene Folgen | – |
| Gleiches `album`, verschiedene `serien_tag` (oder, ohne diese, verschiedene `album_interpret`) | **eine** Gruppe, die Mehrheit bestimmt die Serie | `serie_widerspruch` |
| Gleiches `album`, verschiedene `nummer_tag` | Mehrheit | `nummer_widerspruch` |
| Gleiches `album`, verschiedene `datum` | das früheste | – |
| Einige Dateien eines Ordners ohne `album`, andere mit | die ohne bilden eine eigene Gruppe (11.3) | `tags_fehlen` |
| Gleiches (`disc`, `track`) zweimal | beide bleiben (11.7) | `track_doppelt` |
| `track` nur bei einem Teil der Dateien | die mit `track` zuerst (11.7) | `track_teils_leer` |
| Zwei Gruppen im Durchlauf mit gleicher Serie und gleicher `nummer` | beide bleiben (11.6) | `nummer_doppelt` |

### 11.9 Fehlende Tags und „bitte prüfen“

Eine Folge ist **„bitte prüfen“**, sobald sie mindestens ein Kennzeichen trägt. Die
Kennzeichen (`pruefen_gruende`) und ihre Bedeutung:

| Code | Bedeutung |
|---|---|
| `tags_fehlen` | kein `album`: Name und Serie stammen aus Ordner- und Dateinamen |
| `serie_aus_interpret` | die Serie stammt nur aus `interpret` |
| `serie_aus_ordner` | die Serie stammt aus dem Ordnernamen oder ist `Einzelfolgen` |
| `serie_widerspruch` | verschiedene Serienangaben in einem Album (Mehrheit gilt) |
| `serie_mehrdeutig` | mehrere vorhandene Serien passen; die älteste wurde genommen |
| `nummer_widerspruch` | verschiedene Folgen-Nummern in einem Album |
| `nummer_doppelt` | die Nummer gibt es in der Serie schon |
| `track_doppelt`, `track_teils_leer` | siehe 11.7 |
| `name_geaendert` | der Name musste durch einen Ersatz (`Unbenannt`) oder durch starkes Kürzen ersetzt werden (Abschnitt 12) |
| `folge_gleicher_name` | die Serie hat schon eine Folge mit demselben Anzeigenamen |
| `teilweise_doppelt` | ein Teil der Dateien war schon vorhanden und wurde verworfen (11.10) |
| `vorgabe_serie_fehlt` | die vom Upload vorgegebene Serie gibt es nicht mehr |

Die Kennzeichen stehen in `serie.json` (`folgen_info.<name>.pruefen`, `pruefen_gruende`;
bei der Serie selbst `pruefen`, `pruefen_gruende`; `data-model.md`, Abschnitt 5), damit sie
den Neustart von HA überleben. Sie verschwinden mit `einsortierung/bestaetigen` und durch
die Korrekturen aus 3.9. **Fehlende Tags sind nie ein Fehler**: Die Datei wird trotzdem
einsortiert.

### 11.10 Blockiertes, Doppeltes, Reste

*   **Kopierschutz und defekte Dateien (Vorgabe 8):** Jede Datei wird vor dem Einsortieren
    nach D5 geprüft (`ffprobe` gehärtet wie 5.4; Codec `drms`; `ffprobe` scheitert;
    Probedekodierung von 1 s). Eine Datei mit `kopierschutz`, `nicht_lesbar` oder
    `probedekodierung_fehlgeschlagen` kommt **nicht in die Medien**, sie bleibt im
    Eingang mit Hinweis (Eingangs-Eintrag, `hinweise`). Fehlt `ffprobe`: Der ganze
    Durchlauf bleibt liegen (`ffprobe_fehlt`), denn ohne `ffprobe` gibt es keine Tags.
    **Eine Gruppe wird nur vollständig einsortiert:** Ist auch nur eine Datei einer Gruppe
    blockiert, bleibt die **ganze Gruppe** im Eingang (die gute Datei ist dann ohne
    Folge nutzlos); andere Gruppen desselben Eintrags werden einsortiert (Status
    `teilweise`). Ein Eintrag ohne eine einzige Audiodatei bleibt mit dem Hinweis
    `keine_audiodateien` liegen.
*   **Doppelte (Vorgabe 7):** Von jeder Datei wird die **SHA-256-Prüfsumme** des Inhalts
    gebildet (im Executor, in Blöcken). Sie wird verglichen mit (a) dem **Index** im
    HA-Speicher (Prüfsumme → Pfad der Datei in `medien/`; es zählt nur ein Eintrag,
    dessen Datei noch am Pfad liegt und dieselbe Größe hat; der Index nimmt alles auf, was
    das Einsortieren und der Upload nach `medien/` gebracht haben, und verliert die
    Einträge, deren Folge in den Papierkorb geht oder verschoben wird; er wird beim
    Wiederherstellen ergänzt; höchstens 20 000 Einträge), (b) den anderen Dateien des
    Durchlaufs, (c) einer gleichnamigen Datei im Ziel. Bei gleicher Prüfsumme gilt die
    Datei als **doppelt**: Sie kommt in den Papierkorb (`typ="eingang"`,
    `grund="doppelt"`, wiederherstellbar) und bekommt den Hinweis `doppelt` im Ergebnis.
    Dateien, die von außen direkt in `medien/` kamen, kennt der Index nicht; sie werden
    nur gefunden, wenn der Name gleich ist (c).
    Ist nur ein Teil einer Gruppe doppelt, werden die doppelten Dateien verworfen und der
    Rest als Folge einsortiert (Kennzeichen `teilweise_doppelt`); ist **alles** doppelt,
    entsteht keine Folge.
*   **Gleicher Name, anderer Inhalt (Vorgabe 7):** Gibt es im Ziel schon eine Datei oder
    einen Ordner mit dem Namen (ohne Rücksicht auf Groß-/Kleinschreibung und Unicode-Form),
    erhält die neue ` (2)`, ` (3)` … vor der Endung (Abschnitt 12).
*   **Reste:** Ist ein Eintrag fertig (nichts blockiert, nichts mehr zu sortieren), kommen
    seine ignorierten Dateien (Bilder, Texte) in den Papierkorb (`typ="eingang"`,
    `grund="eingang_rest"`) und leere Unterordner werden gelöscht; der Eintrag
    verschwindet aus dem Eingang. Er steht als `erledigt` im Protokoll.

### 11.11 Schreiben in die Medien (Reihenfolge, Abbruch)

Je Gruppe, unter den Sperren aus Abschnitt 1 (Eingang, dann Serie):

1.  **Berechnen** ohne Schreiben (Tags, Prüfsummen, Serie, Reihenfolge, Namen, Kennzeichen).
2.  **Serie anlegen**, wenn neu: Ordner, `serie.json` (`folgen` leer; atomar nach
    `data-model.md`, 1.2).
3.  **Dateien verschieben** (Umbenennen auf derselben Freigabe, nie kopieren): Eine
    Einzeldatei direkt in den Serien-Ordner (nach erneuter Namensprüfung unter der Sperre).
    Ein Folgen-Ordner wird zuerst vollständig unter `medien/_upload/<zufall>/` aufgebaut
    und dann **als ganzer Ordner** in den Serien-Ordner umbenannt. Die Box sieht so nie
    einen halben Ordner (und ohne Eintrag in `folgen` spielt sie ihn ohnehin nicht).
4.  **`serie.json` schreiben:** die Folge nach 11.6 in `folgen` einfügen, `folgen_info`
    ergänzen (`anzeige`, `nummer`, `datum`, `pruefen`, `pruefen_gruende`). Atomar.
5.  **Index, Protokoll und Ereignisse:** Prüfsummen in den Index, Eintrag ins Protokoll
    (HA-Speicher, die letzten 100), Ereignisse `neu_einsortiert` und `serien_geaendert`.

Bricht HA zwischen 3 und 4 ab, liegt die Datei im Serien-Ordner, steht aber nicht in
`folgen`; die nächste Prüfung der Freigabe (`medien/pruefen`) trägt sie **hinten** ein
(wie jede von außen gekommene Datei). Es geht nichts verloren; nur Nummer und Anzeigename
fehlen, und die Folge ist nicht „bitte prüfen“. Kein Schritt wird an die Boxen gemeldet;
sie holen die Folge mit dem nächsten Sync.

### 11.12 Beispiele als Testfälle

Jede Zeile ist ein Test in `test_eingang.py` (Tags sind mit `ffprobe`-Schlüsseln
geschrieben; „→“ ist das Ergebnis).

| Nr. | Eingang | Ergebnis |
|---|---|---|
| T1 | Ordner `Hörbuch X/` mit 12 mp3, alle `album="Hörbuch X"`, `album_artist="Autor A"`, `track=1..12` | Serie `Autor A` (neu, ohne `pruefen`), **eine** Folge `Hörbuch X` als Ordner mit 12 Tracks, Dateinamen unverändert |
| T2 | 5 mp3 in einem Ordner, jede mit eigenem `album="Der kleine Rabe - Folge N: …"` (N = 3, 1, 5, 2, 4 in Dateireihenfolge), `album_artist="Der kleine Rabe"` | Serie `Der kleine Rabe`, 5 Folgen in der Reihenfolge Nummer 1, 2, 3, 4, 5 (Nummer aus R1) |
| T3 | m4b mit `series="Die Känguru-Chroniken"`, `series-part="2"`, `album="Und überhaupt"`, `album_artist="Marc-Uwe Kling"` | Serie `Die Känguru-Chroniken` (der `serien_tag` schlägt den Interpreten), Folge `Und überhaupt`, Nummer 2 |
| T4 | Datei ohne Tags in `Märchen/` | Serie `Märchen`, Folge (Datei) mit Anzeigename = Dateiname ohne Endung (nicht der Ordnername; der gilt nur für Folgen-Ordner, 11.4); Kennzeichen `tags_fehlen`, `serie_aus_ordner`; Serie `pruefen` |
| T5 | lose Datei `x.mp3` ohne Tags | Serie `Einzelfolgen`; Kennzeichen wie T4 |
| T6 | Zwei Durchläufe nacheinander, `album_artist` = `Die drei ???` und `die drei ???` | **eine** Serie (gleicher Serienschlüssel `diedrei`) |
| T7 | Ordner, `album` gleich, `serien_tag` 3-mal `A`, 1-mal `B` | eine Gruppe, Serie `A`, Kennzeichen `serie_widerspruch` |
| T8 | 2 Dateien `a.mp3` (track 2), `b.mp3` (track 1), gleiches Album | Folgen-Ordner mit `001 b.mp3`, `002 a.mp3` (Reihenfolge ≠ natürliche Namensordnung → Präfix) |
| T9 | wie T8, aber `a.mp3` track 1 und `b.mp3` track 2 | Namen bleiben `a.mp3`, `b.mp3` |
| T10 | Album mit 3 Dateien, eine mit Codec `drms` | die **ganze Gruppe** bleibt im Eingang, Hinweis `kopierschutz` an der Datei; Eintrag `blockiert` (andere Gruppen im Eintrag werden einsortiert, Status `teilweise`) |
| T11 | dieselbe Datei (gleiche Prüfsumme) liegt schon als einsortierte Folge in `medien/` und kommt noch einmal in den Eingang | die neue Datei kommt in den Papierkorb (`grund="doppelt"`), keine neue Folge, Hinweis `doppelt` |
| T12 | `Folge 1.mp3` mit anderem Inhalt, im Ziel gibt es schon eine gleichnamige | neue Datei heißt `Folge 1 (2).mp3` |
| T13 | 3 Folgen ohne Nummern, `date` = 2001, 1999, 2000 | Reihenfolge 1999, 2000, 2001 |
| T14 | 3 Folgen ohne Nummer und ohne Datum, Eingangsindex 0, 1, 2 | Reihenfolge 0, 1, 2 |
| T15 | Serie hat Folgen mit Nummer 1, 2, 3 (und hinten eine ohne), neue Folge Nummer 4 | wird hinter 3 und **vor** der Folge ohne Nummer eingefügt; eine neue mit Nummer 2 kommt hinter die vorhandene 2 und trägt `nummer_doppelt` |
| T16 | `album_artist="Various Artists"` | gilt als leer; die Serie kommt aus `interpret` oder dem Ordner (Kennzeichen) |
| T17 | `album="Hörbuch X (CD 1)"` und `(CD 2)` | eine Gruppe, Anzeige `Hörbuch X` |
| T18 | Upload mit `serie_id` einer vorhandenen Serie | Serie = Vorgabe, auch gegen die Tags |
| T19 | Eintrag, dessen neueste Datei 30 s alt ist | Status `wartet`, nichts verschoben (mit `sofort=true`: einsortiert) |
| T20 | Dateiname `Folge 1: Der Rabe.mp3` | Zielname `Folge 1 - Der Rabe.mp3` (Abschnitt 12) |

## 12. Namen und reservierte Ordner

Diese Regeln gelten für **jeden** Datei- und Ordnernamen, den das Backend auf der
Freigabe anlegt (Upload, Einsortieren, `serie/create`, Verschieben, Suffixe). Namen, die
schon auf der Freigabe liegen, werden nicht umgeschrieben.

1.  **Unicode NFC.** Neue Namen sind NFC (macOS liefert NFD; SMB und QNAP vergleichen
    uneinheitlich).
2.  **Verbotene Zeichen** der SMB-Freigabe ersetzen, nicht ablehnen: `:` wird zu ` - `
    (`Folge 1: Der Rabe` → `Folge 1 - Der Rabe`; vorhandene Leerzeichen um den Doppelpunkt
    gehen darin auf), `/ \ * ? " < > |` werden zu `_`, Steuerzeichen (U+0000 bis U+001F,
    U+007F) entfallen.
3.  **Ränder:** Leerraum zu einem Leerzeichen zusammenfassen, am Anfang und Ende kürzen;
    **führende Punkte und führende `_` entfallen** (kein Dotfile, kein reservierter Name);
    **Punkte und Leerzeichen am Ende entfallen** (Windows).
4.  **Gerätenamen** (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, ohne
    Rücksicht auf Groß-/Kleinschreibung, mit oder ohne Endung) erhalten ein `_` davor;
    `.` und `..` werden zu `_`. **Ausnahme Serien-Ordner (09.11., Befund AP 3.1):** Ein führendes
    `_` ergäbe einen reservierten Ordner (siehe unten). Darum bekommt ein Gerätename als Serien-Ordner
    das `_` **hinten**: `CON` wird `CON_`, nicht `_CON`.
5.  **Länge:** höchstens 255 Bytes (UTF-8) **und** 255 UTF-16-Einheiten, die kürzere Grenze
    gilt, abzüglich Platz für ` (99)`; gekürzt wird an einer **Zeichengrenze** (nie mitten
    in einem UTF-8-Zeichen), die Endung bleibt erhalten. Ein Kürzen um mehr als nur das
    Suffix trägt das Kennzeichen `name_geaendert`.
6.  **Leer** nach allem: beim Upload und bei `serie/create` `name_ungueltig`; beim
    Einsortieren der Name `Unbenannt` (Kennzeichen `name_geaendert`).
7.  **Namensgleichheit** wird ohne Rücksicht auf Groß-/Kleinschreibung und nach NFC geprüft
    (auf der SMB-Freigabe sind `Folge.MP3` und `folge.mp3` dieselbe Datei), **unter der
    Sperre**, und bei Treffer hängt das Backend ` (2)`, ` (3)` … vor die Endung (bei
    Ordnern ans Ende). Ab ` (99)` gibt es `medien_schreibfehler`.
8.  **Anzeigenamen** (Serie 1–100, Folge 1–200, Tobie 1–60 Zeichen) sind frei bis auf
    Steuerzeichen (entfernt); `:` bleibt erlaubt, denn sie sind kein Dateiname.

**Reservierte Ordner in `medien/`:** Ordner, deren Name mit `_` beginnt (`_papierkorb`,
`_upload`), und der Name `eingang` (ohne Rücksicht auf Groß-/Kleinschreibung) sind **keine
Serien**. Die Prüfung der Integration legt für sie keine `serie.json` an und meldet
`reservierter_ordner`; die Namensregeln 3 und 7 verhindern, dass das Backend selbst einen
solchen Serien-Ordner anlegt (`serie/create` mit dem Namen „eingang“ ergibt den Ordner
`eingang (2)`). Der Sync der Box lässt sie aus (11.1).

## 13. Zustand der Konfiguration: leerer Speicher, Export, Boxen mit neuerem Stand

Dieser Abschnitt sichert gegen das stille Ausrollen einer **leeren** Liste und gegen eine
Sicherung mit **alter Revision** ab (W-01, W-02, W-06). Hintergrund: Die Boxen nehmen eine
Liste mit neuer Listen-ID immer an, auch eine leere (`mqtt-v1.md`, 5.2); eine Liste mit
gleicher Listen-ID und niedrigerer Revision lehnen sie ab.

### 13.1 Die drei Zustände (`konfig.zustand`)

| Zustand | Bedeutung | Die Integration |
|---|---|---|
| `ok` | Normalbetrieb | verteilt, was Befehle ändern |
| `leer_neu` | Der HA-Speicher ist leer (neu aufgesetzt oder verloren), obwohl es schon einmal eine Konfiguration gab | **veröffentlicht nichts**, legt keine Listen-ID an, bis Tobias entscheidet |
| `export_neuer` | Der Export auf dem NAS ist neuer als der HA-Speicher (HA wurde aus einer Sicherung zurückgespielt) | veröffentlicht nichts Neues, bis Tobias entscheidet |

### 13.2 Erkennung beim Start

Die Integration prüft **beim Start** (nach Verbindung zum Broker, mit bis zu 15 s Wartezeit
auf die dauerhaften `status`-Nachrichten der Boxen):

1.  **Speicher leer** (kein Eintrag `.storage/tobibox` oder ohne Konfiguration):
    *   Gibt es **keine** Exportdatei **und** meldet **keine** Box eine `konfig.liste_id`
        im dauerhaften `status`: **Erststart**. Die Integration legt eine neue Liste an
        (Revision 1, neue Listen-ID), veröffentlicht sie, `zustand="ok"`.
    *   Sonst (es gab schon eine Konfiguration): `zustand="leer_neu"`, **keine** Listen-ID,
        **keine** Veröffentlichung.
2.  **Speicher vorhanden:** Der Export ist **neuer**, wenn er lesbar und gültig ist und
    (a) seine `liste_id` gleich der im Speicher ist und seine `revision` **höher**, oder
    (b) seine `liste_id` anders ist und sein `exportiert_am` **nach** dem
    `export_geschrieben_am` liegt, den dieser Speicher zuletzt selbst geschrieben hat.
    Dann `zustand="export_neuer"`. Sonst `ok`.

### 13.3 Verhalten außerhalb von `ok`

*   Alle Befehle, die die Konfiguration ändern (Spalte „MQTT“ mit `tobibox/config`,
    außer den beiden Auswegen), antworten `konfig_nicht_bereit`; ebenso `lernmodus/start`.
*   Lesen, Medien, Eingang, Neue Tobies, Boxen, Sync gehen weiter. Bestätigungen `neu` und
    `bekannt` auf `…/ack` gehen weiter.
*   Die Seite zeigt eine Warnung, die den Unterschied erklärt, und bietet **nur** die
    Auswege an:
    *   **Aus dem Export holen** (`konfig/aus_export`): übernimmt den Export mit neuer
        Listen-ID und Revision 1.
    *   **Stand von HA behalten / leer beginnen** (`liste/neu_ausrollen`): erzeugt eine
        neue Listen-ID aus dem Stand in HA (bei `leer_neu`: eine **leere** Liste; die Seite
        sagt vorher, dass alle Tobies ihre Zuordnung verlieren).

### 13.4 Box mit neuerem Stand (`voraus`)

Ist die `liste_id` einer Box (aus `status.konfig`) gleich der von HA und ihre `revision`
**höher**, ist `konfig_stand="voraus"` (3.7). Meldet eine Box `liste_abgelehnt` mit
`revision_zu_niedrig`, gilt dasselbe. In beiden Fällen sendet das Backend das Ereignis
`konfig` `abweichung` (4.6). **Die Integration erhöht die Revision nie von selbst** (das
würde gegen die Boxen laufen und könnte einen Stand überschreiben, den nur die Box hat). Der
Ausweg ist derselbe wie oben: `liste/neu_ausrollen` oder `konfig/aus_export`.

### 13.5 Export (W-06)

*   Der Export `export/config.json` (Schema von `config.json` plus `exportiert_am`,
    `data-model.md`, Abschnitt 1.6) wird **nach dem Veröffentlichen** im Hintergrund
    geschrieben (Abschnitt 1) und enthält die Tobie-Namen.
*   Schlägt er fehl (NAS im Standby, Netz), wiederholt das Backend nach 10 s, 60 s, 5 min,
    dann alle 15 min, bis er gelingt oder eine neuere Revision ihn ersetzt. Solange gilt
    `konfig.export_ok=false`; das Ereignis `konfig` `export_fehler` meldet es,
    `export_ok` meldet das Nachholen, und die Seite zeigt eine Warnung (das Sicherungsnetz
    fehlt!).
*   Der Befehl, der die Änderung auslöste, bleibt davon unberührt.

### 13.6 Wiederverbinden

Kehrt der Broker zurück, veröffentlicht das Backend die **aktuelle** Konfiguration noch
einmal (retained), wenn eine Veröffentlichung offen ist (`veroeffentlicht=false`). Die
Revisionsregel der Boxen macht das unschädlich. Offene `ack` des Lernmodus folgen
danach (6.2, Schritt 4).

### 13.7 Tests

`homeassistant/tests/test_restore.py` (AP 3.1) prüft: (a) **leerer Speicher mit
vorhandenem Export und Box-Status** → `leer_neu`, nichts veröffentlicht, Befehle
`konfig_nicht_bereit`; (b) **Erststart** (kein Export, kein Status) → neue Liste,
veröffentlicht; (c) Zurückspielen mit höherer Export-Revision → `export_neuer`;
(d) `konfig/aus_export` → neue Listen-ID, Revision 1, Namen übernommen, `zustand="ok"`;
(e) `voraus` und `abweichung`; (f) Export schlägt fehl → Befehl gelingt, `export_ok=false`,
Wiederholung; (g) „Liste neu ausrollen“ nach Wiederherstellung mit alter Listen-ID.

## Festlegungen in diesem Vertrag (Stand 09.11.)

Das Design lässt diese Einzelheiten offen. Entschieden wurde die einfachste
stimmige Lösung. Die Punkte 1 bis 14 stammen aus dem Entwurf vom 09.11. (vormittags) und
gelten mit den Änderungen aus der Überarbeitung; die Punkte 15 bis 24 sind neu. **Alles
geht mit der Freigabe an Tobias**; die Vorgaben der Projektleitung (unten) gelten, bis er
widerspricht.

1.  **Rechte:** Lesen für jeden angemeldeten Nutzer, Schreiben nur Administratoren
    (2.1), abgeleitet aus Entscheidung D; die Seite nur für Administratoren
    (`require_admin=True`).
2.  **Ein Abo mit Themen** (`tobibox/subscribe`) statt eines Abos je Thema; Snapshots
    enthalten nur Zähler, nie Listen.
3.  **`anfrage_id`** für Befehle ohne natürliche Idempotenz (2.2); Speicherdauer
    10 min, 100 Stück, nur Erfolge.
4.  **`stand`** (Fingerabdruck) gegen gleichzeitige Änderungen von außen (drei
    Schreiber, Risiko im Design); die Seite muss ihn senden, wo die Reihenfolge, das
    Löschen oder das Verschieben von einem alten Bild der Seite ausgehen kann. Für
    Zuordnungen entsprechend `erwartet_ziel`.
5.  **Zuordnung vor Medien:** Eine Zuordnung darf auf eine Serie zeigen, die noch auf
    keiner Box ist (Design, `data-model.md`, Abschnitt 2), muss aber auf der Freigabe
    existieren.
6.  **Löschen einer zugeordneten Folge oder Serie** lässt die Zuordnung stehen und
    verlangt vorher eine Rückfrage mit Anzahl und Namen der Tobies.
7.  **Rückfrage-Frist** beim Überschreiben: `rueckfrage_bis` = das spätere von `frist_bis`
    (180 s) und Meldung + 60 s; HA-Benachrichtigung bei geschlossener Seite.
8.  **Rückfrage als Ereignis plus Antwortbefehl** statt eines Feldes in `lernmodus/start`.
9.  **Zwischendatei** für Uploads in `medien/_upload/` (gleiche Freigabe, gleiches
    Dateisystem), damit die Box nie halbe Dateien sieht.
10. **Kopierschutz = bleibt im Eingang mit Warnung, nicht in den Medien** (Vorgabe 8;
    ersetzt die Fassung „aufnehmen mit Warnung“ für alles, was durch den Eingang kommt).
11. **`medien/pruefen` und `eingang/sortieren` laufen im Hintergrund** und melden das Ende als
    Ereignis, damit der Befehl in 10 s antwortet.
12. **Fortschritt des Sendens misst der Browser;** Ereignisse gibt es nur für die
    Prüfung danach, an alle Abos des Nutzers.
13. **Neue-Tobies-Liste im HA-Speicher,** nicht in `tobibox/config` und ohne Revision.
14. **Papierkorb: wiederherstellen hinten in `folgen`;** die alte Position wird nicht
    gemerkt.
15. **Entscheidung M:** Eingang `tobibox/eingang/`, Einsortieren nach Tags, Korrektur auf der
    Seite (Abschnitt 11).
16. **Eingang neben `medien/`,** nicht darin: Das Umbenennen ist atomar, und der Sync sieht
    ihn nie; zusätzlich schließen NAS-Modul und Box die Namen aus.
17. **Upload geht in den Eingang;** die Seite kann die Serie als Vorgabe mitgeben
    (`serie_id`) und zusammengehörige Dateien mit `gruppe` bündeln (Auslegung der
    Projektleitung: Hochladen „in eine Serie“ bleibt möglich, durchläuft aber dieselbe
    Einsortierung).
18. **Eine Gruppe wird nur vollständig einsortiert** (11.10): Eine blockierte Datei hält die
    ganze Folge zurück.
19. **Zeiger bei Verschieben und Zusammenführen:** Die Zuordnungen der Folgen-Tobies werden
    umgeschrieben, ihre Zeiger auf den Boxen beginnen von vorn (offener Punkt 3).
20. **Lernmodus, Ziel schon vorhanden:** `ack abgelehnt` statt `zugeordnet`, damit die Box
    ohne 10 s Stille das (identische) bestehende Ziel spielt; Tobias sieht „Der Tobie hat
    dieses Ziel schon.“ (6.2, Schritt 3).
21. **`ack` erst nach PUBACK** der Konfiguration; ohne PUBACK kein `ack` (W-07).
22. **Leerer Speicher veröffentlicht nichts** (Abschnitt 13); Erststart ist davon
    ausgenommen (kein Export, kein Box-Status).
23. **Export nach dem Veröffentlichen** mit Wiederholung und sichtbarem Fehler (W-06).
24. **Namen werden bereinigt statt abgelehnt** (Abschnitt 12); die Namensgleichheit prüft
    ohne Rücksicht auf Groß-/Kleinschreibung und NFC, unter der Sperre.
25. **Entscheidung N: Feld `lesezeichen_tage` reserviert** (Abschnitt 10, `data-model.md` Abschnitt 2).
    Das Backend legt es mit der Vorgabe 14 an (Bereich 0 bis 365, `0` = nie), veröffentlicht, exportiert
    es und holt es mit `konfig/aus_export` zurück (09.11., Befund AP 3.1); eine Seitenbedienung gibt es erst mit den
    Einstellungen in Stufe 4. Kein neuer Befehl, Version 1 bleibt.

## Vorgaben der Projektleitung (09.11.)

Diese Entscheidungen zu den früheren „Offenen Punkten“ hat die Projektleitung getroffen
und in den Vertrag übernommen. **Tobias kann widersprechen.** Die Nummern sind die der
früheren Liste.

| Nr. | Punkt | Entscheidung | Wo im Vertrag |
|---|---|---|---|
| 1 | Seite für Nicht-Administratoren | nur Administratoren, `require_admin=True` | 2.1 |
| 2 | „Bestätigen“ bei Neue Tobies | heißt zuordnen; das `ack` geht automatisch an die Box | 3.4 |
| 3 | „Umbenennen“ | nur **Anzeigenamen** von Serie und Folge (aus den Tags vorbelegt); Dateinamen bleiben, Zeiger gehen nie verloren | Nr. 6, 25 |
| 4 | Serie löschen | über den Papierkorb, mit Rückfrage; neuer Befehl `serie/delete` | Nr. 24 |
| 5 | Löschen mit Zuordnung | Rückfrage mit Anzahl und Namen der Tobies, danach Papierkorb; die Zuordnung bleibt, die Box spielt bis dahin die Überraschung | Nr. 8, 24, 6.3 |
| 6 | Größte Datei beim Upload | zunächst 500 MiB, einstellbar; die Abnahme misst am Handy über Nabu Casa | 5.1, 8 |
| 7 | Gleicher Dateiname | gleicher Inhalt (Prüfsumme): erkannt und verworfen mit Hinweis; gleicher Name, anderer Inhalt: automatisches Suffix | 11.10, 5.3 |
| 8 | Kopierschutz, defekt | bleibt im Eingang mit Warnung, nicht in den Medien | 5.4, 11.10 |
| 9 | Folgen-Ordner von der Seite | durch Entscheidung M erledigt (Tags bilden Folgen-Ordner, auch beim Upload) | 11.3 |
| 10 | Namen für Tobies | optionales Feld `name` je Zuordnung; die Box ignoriert es | Nr. 16, `data-model.md` |
| 11 | Rückfrage-Frist | 180 s; ohne offene Seite eine HA-Benachrichtigung (`persistent_notification`) | 6.2 |
| 12 | Zweiter Lernmodus | `lernmodus_laeuft`, erst abbrechen | Nr. 18 |
| 13 | Überraschungs-Serie | von der Seite anlegbar, wenn keine existiert; als Ziel einer Zuordnung verboten (`ziel_ungueltig`) | Nr. 3, 5, 16 |
| 14 | `_upload/`, `_papierkorb/` aus dem Sync | ausgenommen, dazu `eingang/`; vermerkt bei AP 3.4/3.5 im Design | 11.1, 12 |
| 15 | Papierkorb-Metadaten | Ordner `_papierkorb/<id>/` mit `meta.json`, in `data-model.md` | 3.3 |
| 16 | `limit`/`offset` | schon in Version 1 | Nr. 15 |
| 17 | Box-Meldungen | die letzten 20 je Box im HA-Speicher (überleben einen Neustart) | Nr. 21 |
| 18 | Leise-Zeiten | bleiben in Stufe 4 (AP 4.7) | 10 |
| 19 | HA-Version | **2026.11.x**; die genaue Patch-Version nennt Tobias beim Start von AP 3.1. Dazu Mosquitto-Add-on 7.1.3 und QNAP TS-464eU-8G (Celeron N5095, amd64) | 8, Plan Rev. 3.14 |
| 20 | Nabu Casa | wie 6: Abnahme am Handy mit 20, 150 und 500 MiB | 8 |

## Prüfung gegen die Home-Assistant-API

Geprüft am 09.11.2026 gegen den Quelltext von `home-assistant/core` (Zweig `dev`) und
aiohttp `master` (Goldfisch-Report, Abschnitt „Zu den Prüffragen“), soweit angegeben.
Alles andere stammt aus Wissen und ist in AP 3.1 gegen die feste HA-Version (2026.11.x)
zu belegen.

| Aussage | Stand |
|---|---|
| `websocket_api.websocket_command(schema)` setzt Schema und Befehlsnamen (`schema["type"]`); `extra` des Schemas lehnt Unbekanntes ab | geprüft (Quelltext). In `dev` heißt die Schema-Bibliothek in den Modulen `probatio`; das Verhalten ist das von `voluptuous` (Namensunterschied hängt an der HA-Version). Der Vertrag benutzt nur Typen (`str`, `int`, `bool`, Listen, Bereiche). |
| `websocket_api.async_response` führt den Handler als Hintergrundaufgabe aus; Pflicht für alles mit `await` | geprüft |
| `websocket_api.require_admin`: Nutzer muss `is_admin` sein, sonst `unauthorized` | geprüft. Reihenfolge der Dekoratoren wie in HA-Core: `@require_admin`, `@websocket_command(...)`, `@async_response` |
| `connection.send_result`, `send_error(msg_id, code, message)`, `send_event`, `send_message`; `websocket_api.event_message(id, event)` | geprüft |
| Abos: `connection.subscriptions[msg["id"]] = unsub`; das Beenden macht HAs `unsubscribe_events` (mit `subscription`); beim Trennen der Verbindung ruft HA alle `unsub` auf | geprüft (`subscriptions`, `async_handle_close`); `unsubscribe_events` aus Wissen |
| Fehlerobjekt hat nur `code` und `message` (plus Übersetzungsschlüssel) | geprüft |
| Eingebaute Fehlercodes `invalid_format`, `unauthorized`, `not_found`, `unknown_command`, `unknown_error`, `home_assistant_error` | geprüft (`const.py`) |
| `HomeAssistantView`: `requires_auth = True` und `cors_allowed = False` als Vorgabe; nicht angemeldete Anfrage → 401 vor dem Handler; Attribut `max_body_size` | geprüft |
| HA-Ansichten wandeln `Unauthorized` in **401** um (`helpers/http.py`, Zeilen 103–104); der Dekorator `homeassistant.components.http.decorators.require_admin` macht das | geprüft (W-19) |
| `handler_cancellation=True`: Trennt der Client, wird der Handler mit `CancelledError` abgebrochen (`http/server.py`, Zeile 605) | geprüft (W-03); darum `asyncio.shield` im Abschluss (5.2) |
| `request[KEY_HASS_USER]` (aus `homeassistant.components.http.const`) liefert den Nutzer | Name geprüft; Nutzung aus Wissen |
| Streaming: `request.multipart()` (aiohttp) und `part.read_chunk(size)` sind nicht durch `client_max_size` begrenzt; `read()`, `post()`, `part.read()` schon | geprüft im aiohttp-Quelltext (W-14); in AP 3.1 mit 40-MiB-Test gegen die feste Version |
| `panel_custom.async_register_panel(hass, frontend_url_path, webcomponent_name, sidebar_title, sidebar_icon, module_url, embed_iframe, config, require_admin, …)` | geprüft (Signatur) |
| Statische Dateien: `hass.http.async_register_static_paths([StaticPathConfig(...)])`; sie verlangen keine Anmeldung | Registrierung aus Wissen; fehlende Anmeldung geprüft (W-26) |
| Obergrenze „normale Anfragen 16 MiB“ | **geprüft**: `http/server.py` Zeile 69 und 278 (W-14), siehe Abschnitt 8 |
| Grenze der WebSocket-Nachricht | geprüft: HA setzt keinen Wert, es gilt die Vorgabe von aiohttp (4 MiB, aus Wissen) |
| `ffprobe`-Schlüsselnamen der Tags je Container | **offen** bis AP 3.1 (Beispieldateien von Tobias) |

## Offene Punkte für Tobias

Hier steht nur, was **nur Tobias** entscheiden oder tun kann. Alles andere hat die
Projektleitung entschieden (Tabelle oben, Abschnitt 11 bis 13); Tobias kann dort
widersprechen.

1.  **Upload über Nabu Casa (Messung am Handy).** Keine Grenze für Größe oder Dauer ist
    veröffentlicht. Bei der Abnahme der Stufe 3a lädt Tobias drei Dateien hoch (20 MiB,
    150 MiB, 500 MiB) und notiert die Dauer. Danach entscheidet er, ob `upload_max_bytes`
    steigt oder ob größere Dateien nur über den Eingang am PC kommen (D4).
2.  **Beispielmaterial für die Tags.** Vor AP 3.1 legt Tobias je zwei echte Dateien aus
    seinen Quellen bereit: ein m4b-Hörbuch, eine mp3-Hörspielfolge einer Serie, einen
    CD-Rip mit mehreren Dateien, eine Datei ganz ohne Tags. Daran belegt AP 3.1 die
    Tag-Schlüssel von `ffprobe` (11.2) und die Regeln für die Folgen-Nummer; ohne echtes
    Material bleibt die Erkennung Raten.
3.  **Zeiger beim Verschieben und Zusammenführen.** Verschiebt oder führt Tobias Folgen
    in eine andere Serie, schreibt HA die Zuordnungen der betroffenen Folgen-Tobies
    um, aber der gemerkte Hörstand auf den Boxen (`resume.json`, je Serie und Folge)
    geht für diese Tobies verloren: Sie beginnen von vorn. Der Vertrag lässt das mit
    Rückfrage zu. Die Alternative (Zeiger mitnehmen) braucht eine Änderung am Box-Dienst
    und am Datenmodell. Reicht „von vorn mit Rückfrage“?
4.  **Aktionen für Tobias (keine Entscheidung):** den Ordner `tobibox/eingang/` auf dem NAS
    anlegen und HA Schreibrecht geben (AP 3.5); die genaue HA-Patch-Version 2026.11.x
    nennen (Start AP 3.1).
