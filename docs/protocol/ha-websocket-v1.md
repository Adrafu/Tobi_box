# WebSocket- und Upload-Schnittstelle Seite ↔ HA-Backend, Version 1 (`ha-websocket-v1`, „Vertrag W“)

*   **Status:** Vertrag Stufe 3a, Entwurf zur Prüfung durch einen Goldfisch
*   **Grundlage:** `docs/designs/box-software.md` (Baustein 4 „Speicher und
    Medien“, „Aktionen und Seite“, „MQTT-Schnittstelle Box ↔ HA“; D1, D2, D4,
    D5, D6; Entscheidungen D, F, H; CUJ 7a, 7b, 9, 10, 11, 12; AP 3.1, AP 3.2,
    AP 4.7)
*   **Gilt für:** `websocket_api.py`, `http.py`, `media.py`, `store.py`,
    `mqtt.py` der HA-Integration `tobibox` (AP 3.1) und die Seite
    `frontend/tobibox-panel.js` samt Mock (AP 3.2). Beide Seiten entstehen
    parallel und nur nach diesem Vertrag.
*   **Verwandte Verträge:** `mqtt-v1.md` (Box ↔ HA), `data-model.md`
    (`config.json`, `serie.json`, `unknown.json`), `reader-v1.md` (Format der
    Kennung). Dieser Vertrag ändert sie nicht. Wo er etwas braucht, das dort
    fehlt, steht es unter „Offene Punkte für Tobias“.

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
*   **MQTT bleibt Verteilkanal.** Befehle, die die Konfiguration ändern, speichern
    zuerst im HA-Speicher (Revision + 1), exportieren auf das NAS und
    veröffentlichen dann `tobibox/config` (`mqtt-v1.md`, 3.1). Ist der Broker gerade
    nicht erreichbar, ist die Änderung trotzdem gespeichert; die Veröffentlichung
    wird nachgeholt (Antwortfeld `veroeffentlicht`).
*   **Medien gehen nicht über MQTT.** Befehle, die Serien, Folgen oder Papierkorb
    ändern, schreiben auf die NAS-Freigabe. Die Boxen holen sie mit dem nächsten
    Sync (CUJ 9); wer es eilig hat, stößt ihn mit `tobibox/box/sync` an.
*   **Ein Schreibvorgang nach dem anderen.** Das Backend serialisiert alle Befehle,
    die `config` oder `serie.json` ändern (eine Sperre je Ziel), damit Revision und
    Dateien nie halb geschrieben werden. Die Seite braucht dafür keine eigene
    Revision zu schicken.
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
    Backend, nicht am Netz). Was länger dauert (Prüfung der Freigabe,
    `ffprobe`), läuft im Hintergrund und meldet sich als Ereignis (Abschnitt 4).
    Dateizugriffe laufen über `hass.async_add_executor_job` (Design, Baustein 4).

## 2. Rechte, Idempotenz, MQTT: die Regeln

### 2.1 Wer darf was (abgeleitet)

HA prüft bei einem WebSocket-Befehl nur, dass der Nutzer **angemeldet** ist. Wer
Administrator sein muss, bestimmt allein der Dekorator `require_admin` am Befehl. Aus
dem Design folgt:

*   Es gibt nur Tobias als Benutzer (Entscheidung D). HA hat vollen Schreibzugriff
    auf `medien/`, `export/` und `releases/`.
*   Schreibende Befehle ändern, was die Kinder hören (Zuordnungen), löschen Dateien
    (Papierkorb leeren), starten Befehle an die Boxen (Lernmodus, Sync, später
    Update). Das Update bringt Code auf die Boxen (nur mit gültiger Signatur, aber
    der Auslöser sollte trotzdem nicht jedem offenstehen).
*   Lesende Befehle zeigen Namen von Serien und Folgen, Kennungen und den
    Status der Boxen. Das sind keine Geheimnisse.

**Regel:**

| Art | Wer | Umsetzung |
|---|---|---|
| **Lesen** (`list`, `get`, `hello`, `subscribe`) | jeder angemeldete HA-Nutzer | kein Dekorator |
| **Schreiben und Auslösen** (alles andere, auch `medien/pruefen`, weil es `serie.json` anlegt) | **nur Administratoren** | `@websocket_api.require_admin`; Fehler `unauthorized` |
| **Upload** (HTTP) | nur Administratoren | Prüfung im Handler: `request[KEY_HASS_USER].is_admin`, sonst 403 |

Die Seite wird in `hello` mit `darf_schreiben` informiert und blendet Knöpfe
aus. Das ist nur Bedienkomfort, **keine Sicherheit**: Das Backend prüft bei jedem
Aufruf selbst. Ob die Seite in der Seitenleiste auch Nicht-Administratoren
gezeigt wird (`panel_custom`, Parameter `require_admin`), steht unter „Offene
Punkte für Tobias“.

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
`anfrage_id_konflikt`.

### 2.3 Zusammenhang mit MQTT

Jeder Befehl nennt in „MQTT“, was er auslöst. Zusammengefasst:

| Wirkung auf MQTT | Befehle |
|---|---|
| veröffentlicht `tobibox/config` (retained, Revision + 1) | `zuordnung/set`, `zuordnung/remove`, `lernmodus/antwort`, Lernmodus-Zuordnung (6.2), später `einstellungen/set` |
| veröffentlicht `tobibox/config` mit **neuer Listen-ID** | `liste/neu_ausrollen` |
| sendet `tobibox/<box>/cmd` (mit `id`, `erzeugt`, `ttl_s`) | `lernmodus/start` (`lernen`, 60 s), `lernmodus/abbrechen` (`lernen_abbrechen`, 30 s), `box/sync` (`sync`, 300 s), später `box/update` (`update`, 300 s) |
| sendet `tobibox/<box>/unknown/<uid>/ack` | nur der Lernmodus (6.2: `zugeordnet`, `abgelehnt`). Die Bestätigung beim ersten Eintreffen einer Kennung (`neu`, `bekannt`) ist **Sache des Backends allein**, kein Befehl der Seite (`mqtt-v1.md`, 3.6). |
| nichts | alle übrigen (Medien, Papierkorb, Lesen, Verwerfen) |

Die **Reihenfolge** „erst Konfiguration, dann `ack`“ (Entscheidung H, 07.11.;
`mqtt-v1.md`, 4.2) gilt für jeden Weg, der eine Zuordnung schreibt und danach
bestätigt.

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

**Konfig-Stand** (`konfig`): `{"revision": <int>, "liste_id": <string>}`. Dieselben
Werte wie in `tobibox/config`.

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
| `stand` | string | Fingerabdruck von `name` und `folgen` (16 Zeichen `[0-9a-f]`); ändert sich auch, wenn jemand `serie.json` von außen ändert |
| `hinweise` | array | Hinweise zu dieser Serie, siehe unten |

**Hinweis** (`hinweise[]`): `{"code": <string>, "folge": <string oder null>, "text": <string>}`.
Codes in Version 1: `datei_fehlt` (Name steht in `folgen`, Datei fehlt; die Integration
nimmt ihn beim nächsten Prüfen heraus), `kopierschutz` (D5, Codec `drms`),
`nicht_lesbar` (`ffprobe` öffnet die Datei nicht), `probedekodierung_fehlgeschlagen`,
`pruefung_nicht_moeglich` (`ffprobe` fehlt), `doppelte_id_korrigiert` (die
Integration hat dieser jüngeren Kopie eine neue ID gegeben, `data-model.md`,
Abschnitt 5), `serie_json_ungueltig_repariert`. Unbekannte Codes zeigt die Seite
mit `text`.

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
| `faehigkeiten` | array von string | was das Backend kann; Version 1 (Stufe 3a): `medien`, `upload`, `zuordnung`, `neue_tobies`, `lernmodus`, `boxen`, `papierkorb`, `liste_ausrollen`, `sync`. Spätere Stufen ergänzen `update` (3b) und `einstellungen` (4). Die Seite zeigt nur, was hier steht. |
| `boxen` | array von string | die eingerichteten Box-Namen (aus der Einrichtung der Integration) |
| `konfig` | object | Konfig-Stand |
| `grenzen` | object | `upload_max_bytes`, `upload_block_bytes`, `endungen` (array), `serie_name_max` (100), `folge_name_max_bytes` (255) |

Fehler: keine außer den allgemeinen. Ist `v` der Seite **größer** als das Backend
kennt, antwortet das Backend trotzdem mit seinem `v`; die Seite entscheidet
(Abschnitt 9). Rechte: alle. Idempotent: ja. MQTT: –.

#### 2. `tobibox/subscribe`

Abonniert Ereignisse (Abschnitt 4). Ein Abo je Seite genügt.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `themen` | array von string | nein | Teilmenge von `boxen`, `neue_tobies`, `lernmodus`, `medien`, `konfig`, `upload`; Vorgabe: alle |

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
| `ueberraschung` | `"ok"`, `"fehlt"`, `"mehrere"` oder `"leer"` | Zustand der Überraschungs-Serie (Box spielt sonst Fehlerton, `data-model.md`, Abschnitt 5) |
| `geprueft_am` | string oder `null` | wann die Integration die Freigabe zuletzt geprüft hat |
| `pruefung_laeuft` | bool | eine Prüfung läuft gerade |

Fehler: `medien_nicht_erreichbar`. Rechte: alle. Idempotent: ja. MQTT: –.

#### 4. `tobibox/serie/get`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | Serien-ID |

Ausgabe: die Felder der Serie-Kurzform und dazu

| Feld | Typ | Bedeutung |
|---|---|---|
| `folgen` | array | in der maßgeblichen Reihenfolge (`serie.json`), Objekte siehe unten |
| `zuordnungen` | array | Tobies, die auf die **ganze Serie** zeigen: `{"uid": <string>}` (Folgen-Tobies stehen bei der Folge) |

Folge-Objekt:

| Feld | Typ | Bedeutung |
|---|---|---|
| `name` | string | Dateiname oder Ordnername (Schlüssel, `data-model.md`, 1.1) |
| `art` | `datei` oder `ordner` | Datei im Serien-Ordner oder Unterordner mit mehreren Tracks (Entscheidung F) |
| `tracks` | int ≥ 1 | Anzahl Tracks (`datei`: 1) |
| `groesse_bytes` | int | Summe der Dateigrößen |
| `pruefung` | `ok`, `warnung`, `nicht_geprueft`, `nicht_moeglich` | Ergebnis der Prüfung nach D5 |
| `hinweis` | string oder `null` | Code aus der Hinweisliste, bei `warnung` |
| `tobies` | array von string | Kennungen, deren `ziel` genau auf diese Folge zeigt |

Fehler: `serie_nicht_gefunden`, `medien_nicht_erreichbar`. Rechte: alle.
Idempotent: ja. MQTT: –.

#### 5. `tobibox/serie/create`

Legt eine neue Serie an (Ordner + `serie.json` mit neuer zufälliger ID, `angelegt_am`
jetzt, `folgen` leer; D2, D4).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `name` | string, 1–100 Zeichen | **ja** | Anzeigename; nach dem Abschneiden von Leerraum nicht leer |
| `typ` | `normal` oder `ueberraschung` | nein | Vorgabe `normal`. `ueberraschung` nur, wenn es noch keine gibt (`ueberraschung_existiert`) |
| `anfrage_id` | string | nein | siehe 2.2 |

Der **Ordnername** entsteht aus dem Namen: Zeichen `/`, `\` und Steuerzeichen werden
durch `_` ersetzt, ein Punkt am Anfang entfällt, auf 255 Bytes gekürzt. Gibt es den
Ordner schon, hängt das Backend ` (2)`, ` (3)` … an. Der Ordnername ist **nicht** die ID
(die ID ist zufällig); er ändert sich später nie, auch nicht beim Umbenennen.

Ausgabe: `{"serie": <Serie-Kurzform>}`. Fehler: `name_ungueltig`,
`ueberraschung_existiert`, `medien_nicht_erreichbar`, `medien_schreibfehler`,
`anfrage_id_konflikt`. Rechte: Admin. Idempotent: **nicht** ohne `anfrage_id` (zweimal
gesendet gibt zwei Serien); mit gleicher `anfrage_id` nur einmal. MQTT: –. Die Boxen
sehen die Serie nach dem nächsten Sync.

#### 6. `tobibox/serie/rename`

Ändert `name` in `serie.json`. Die ID und der Ordnername bleiben; Zuordnungen und
Zeiger bleiben deshalb gültig.

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
| `folgen` | array von string | **ja** | alle Namen der Folgen in der neuen Reihenfolge |
| `stand` | string | nein | `stand` aus `serie/get`. Stimmt er nicht mehr (jemand hat `serie.json` oder den Ordner von außen geändert), lehnt das Backend ab (`stand_veraltet`) und die Seite lädt neu. Ohne `stand` gilt „letzter Schreiber gewinnt“. |

Die Liste muss eine **Umstellung** der aktuellen Liste sein: dieselben Namen, ohne
Doppelte, nichts fehlt, nichts kommt dazu. Sonst `reihenfolge_ungueltig`.

Ausgabe: `{"serie": <Serie-Kurzform>}` (mit neuem `stand`). Fehler:
`serie_nicht_gefunden`, `reihenfolge_ungueltig`, `stand_veraltet`,
`medien_schreibfehler`. Rechte: Admin. Idempotent: ja. MQTT: –. Nebenwirkung: Die
Box spielt die neue Reihenfolge nach dem Sync; der Zeiger einer Serie (Folge als
Name) bleibt gültig (`data-model.md`, Abschnitt 3).

#### 8. `tobibox/folge/delete`

Verschiebt eine Folge (Datei oder Folgen-Ordner) in den Papierkorb und nimmt sie
aus `folgen`. Nie endgültig (Design: „Löschen verschiebt in `_papierkorb/`“).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folge` | string | **ja** | Name der Folge |
| `stand` | string | nein | wie bei `folgen/order` |

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `eintrag` | object | Papierkorb-Eintrag (siehe 3.3) |
| `betroffene_tobies` | array von string | Kennungen mit `ziel.typ="folge"` auf diese Folge. Ihre Zuordnung **bleibt unverändert** (Revision wird nicht erhöht); die Box spielt für sie die Überraschungs-Serie (`folge_fehlt`), bis die Folge zurück ist (`data-model.md`, Abschnitt 2). Die Seite zeigt den Hinweis. |

Fehler: `serie_nicht_gefunden`, `folge_nicht_gefunden`, `stand_veraltet`,
`medien_schreibfehler`. Rechte: Admin. Idempotent: Endzustand ja; der zweite Aufruf
liefert `folge_nicht_gefunden`. MQTT: –. Nebenwirkung: Die Box löscht ihre Kopie
beim nächsten Sync (`--delete`, mit Schutz).

#### 9. `tobibox/medien/pruefen`

Stößt die Prüfung der Freigabe an (Design: „beim Öffnen der Seite und alle
10 min“): neue Ordner (→ `serie.json` mit neuer ID, Ordnername als Name; für
Ordner ohne Datei die ID = Ordnername, `data-model.md`, Abschnitt 5), neue Dateien und
neue Folgen-Ordner (→ hinten an `folgen`), fehlende Dateien (→ heraus, Hinweis),
doppelte Serien-IDs (→ jüngere Kopie bekommt neue ID), Format- und Kopierschutz-
Prüfung neuer Dateien (D5).

Keine Eingabe. Ausgabe: `{"gestartet": <bool>, "laeuft_bereits": <bool>}`. Die
Prüfung selbst läuft im Hintergrund; ihr Ende kommt als Ereignis `medien` mit
`art="pruefung_fertig"` (4.4). Läuft schon eine Prüfung (Timer oder anderer Nutzer),
meldet der Befehl `laeuft_bereits=true` und startet keine zweite.

Fehler: `medien_nicht_erreichbar`. Rechte: Admin (weil sie `serie.json` schreibt;
die Timer-Prüfung läuft unabhängig davon). Idempotent: ja. MQTT: –.

### 3.3 Papierkorb

**Papierkorb-Eintrag** (`eintrag`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | string | Kennung des Eintrags (12 Zeichen `[0-9a-f]`, vom Backend erzeugt) |
| `serie_id` | string | Serie, aus der die Folge kam |
| `serie_name` | string | Name der Serie zum Zeitpunkt des Löschens |
| `folge` | string | Name der Folge |
| `art` | `datei` oder `ordner` | |
| `tracks` | int | |
| `groesse_bytes` | int | |
| `geloescht_am` | string | Zeitstempel |

Der Papierkorb liegt auf der Freigabe unter `medien/_papierkorb/`. Die Boxen
übernehmen ihn nicht. Das Backend muss pro Eintrag festhalten, woher er kam
(Serie, Name, Reihenfolge), damit „wiederherstellen“ geht; **wie** (Hilfsdatei im
Papierkorb), ist Sache von `media.py` und gehört danach in `data-model.md` (siehe
offene Punkte).

#### 10. `tobibox/papierkorb/list`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `limit` | int 1–200 | nein | Vorgabe 100 |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe: `{"eintraege": [<Eintrag>…], "gesamt": <int>, "gesamt_bytes": <int>}`,
neueste zuerst. Fehler: `medien_nicht_erreichbar`. Rechte: alle. Idempotent: ja.
MQTT: –.

#### 11. `tobibox/papierkorb/restore`

Stellt eine Folge wieder her: Sie kommt an ihren Platz im Serien-Ordner zurück und
**hinten** in `folgen` (die alte Position wird nicht gemerkt).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `eintrag_id` | string | **ja** | |

Ausgabe: `{"serie": <Serie-Kurzform>, "folge": <Folge-Name>}`. Fehler:
`eintrag_nicht_gefunden`, `serie_nicht_gefunden` (die Serie gibt es nicht mehr),
`datei_existiert` (im Serien-Ordner liegt inzwischen eine Folge mit demselben
Namen), `medien_schreibfehler`. Rechte: Admin. Idempotent: Endzustand ja; der zweite
Aufruf liefert `eintrag_nicht_gefunden`. MQTT: –. Nebenwirkung: Zuordnungen, die auf
die Folge zeigten, gelten wieder, sobald die Box sie nach dem Sync hat.

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
`bekannt`); die Box löscht daraufhin ihren Eintrag. Die Liste in HA bleibt, bis
Tobias die Kennung **zuordnet** (`zuordnung/set`, auch über den Lernmodus) oder
**verwirft**. Meldet eine Box die Kennung danach erneut (der Tobie liegt wieder
auf), erscheint sie wieder.

**Eintrag „Neuer Tobie“:**

| Feld | Typ | Bedeutung |
|---|---|---|
| `uid` | string | Kennung |
| `zuerst` | string | früheste Meldung aller Boxen |
| `zuletzt` | string | späteste Meldung aller Boxen |
| `anzahl` | int | Summe der Meldungen aller Boxen |
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

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `konfig` | object | Konfig-Stand |
| `zuordnungen` | array | je Eintrag: `{"uid", "ziel", "serie_name" (oder null), "folge_vorhanden" (bool oder null)}`; `serie_name` ist `null`, wenn die Serie auf der Freigabe fehlt, `folge_vorhanden` nur bei `typ="folge"` |

Sortiert nach `uid`. Die Größe ist durch die Konfiguration begrenzt (höchstens
256 KiB, Abschnitt 8). Rechte: alle. Idempotent: ja. MQTT: –.

#### 16. `tobibox/zuordnung/set`

Ordnet eine Kennung einem Ziel zu (Typ `serie`, `folge` oder `aktion`, Entscheidung F).
Das ist der Weg für „Neue Tobies“, für Aktionskarten (Status, Gute Nacht) und für
Kennungen, die Tobias von Hand eingibt.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `uid` | string | **ja** | kanonische Kennung (`reader-v1.md`, Abschnitt 4) |
| `ziel` | object | **ja** | Ziel, siehe oben |
| `ueberschreiben` | bool | nein | Vorgabe `false`. Hat die Kennung schon **ein anderes** Ziel, antwortet das Backend ohne `ueberschreiben=true` mit `zuordnung_existiert`; die Seite fragt Tobias und sendet erneut mit `true`. |

Prüfung: `ziel.typ` ∈ `serie`, `folge`, `aktion`; bei `serie`/`folge` muss die Serie in
der Medienverwaltung existieren (`serie_nicht_gefunden`; sie muss **nicht** schon auf
einer Box sein, das Design erlaubt das, die Box spielt bis dahin die
Überraschungs-Serie); bei `folge` muss die Folge in `folgen` stehen
(`folge_nicht_gefunden`); bei `aktion` ist nur `status` oder `gute_nacht` erlaubt
(`ziel_ungueltig`).

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `geaendert` | bool | `false`, wenn die Kennung schon genau dieses Ziel hatte (dann **keine** neue Revision, keine MQTT-Nachricht) |
| `konfig` | object | Konfig-Stand nach dem Befehl |
| `veroeffentlicht` | bool | `tobibox/config` ist beim Broker angekommen (PUBACK); `false` heißt: gespeichert, wird nachgeholt |

Fehler: `kennung_ungueltig`, `ziel_ungueltig`, `serie_nicht_gefunden`,
`folge_nicht_gefunden`, `zuordnung_existiert`, `konfig_zu_gross`. Rechte: Admin.
Idempotent: **ja** (gleiches Ziel zweimal: zweites Mal `geaendert=false`). MQTT:
veröffentlicht `tobibox/config` (retained, Revision + 1, `erzeugt_am` jetzt). Die
Boxen übernehmen nach der Revisionsregel (`mqtt-v1.md`, 5.2); liegt der Tobie gerade
auf, wechselt die Box auf das neue Ziel (`mqtt-v1.md`, 4.1, Schritt 6). Nebenwirkung:
Steht die Kennung in „Neue Tobies“, wird sie dort entfernt (Ereignis `neue_tobies`,
`art="entfernt"`, `grund="zugeordnet"`). Das Backend schreibt `leise_zeiten`,
`gute_nacht`, `ton_pegel` und `hinweis_pegel` unverändert fort.

#### 17. `tobibox/zuordnung/remove`

Löst eine Zuordnung („lösen“, Design: Aktionen).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `uid` | string | **ja** | |

Ausgabe: wie `zuordnung/set` (`geaendert=false`, wenn es keine Zuordnung gab).
Fehler: `kennung_ungueltig`. Rechte: Admin. Idempotent: ja. MQTT: veröffentlicht
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
| `ziel` | object | **ja** | nur `typ` `serie` oder `folge` (Aktionskarten gehen nicht über den Lernmodus, `mqtt-v1.md`, 3.8) |
| `anfrage_id` | string | nein | siehe 2.2 |

Prüfung wie bei `zuordnung/set` (Serie und Folge müssen existieren). Die Box muss
`online` sein.

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `befehl_id` | string | `id` des Befehls `lernen` (UUID); kommt in den Ereignissen und bei `lernmodus/antwort` wieder vor |
| `box` | string | |
| `ziel` | object | |
| `beginn` | string | Zeitstempel (Wanduhr von HA) |
| `frist_bis` | string | bis wann das Backend die Meldung dieses Befehls annimmt: `beginn` + 180 s (60 s Lebensdauer des Befehls + 120 s Lernfrist der Box) |

Fehler: `box_unbekannt`, `box_offline`, `mqtt_nicht_verbunden`, `ziel_ungueltig`,
`serie_nicht_gefunden`, `folge_nicht_gefunden`, `lernmodus_laeuft` (für diese Box
läuft schon ein Lernmodus mit **anderem** Ziel; mit gleichem Ziel antwortet das
Backend mit dem laufenden Vorgang, siehe Idempotenz), `anfrage_id_konflikt`. Rechte:
Admin. Idempotent: gleiche Box und gleiches Ziel bei laufendem Vorgang: ja (liefert den
laufenden Vorgang, sendet keinen zweiten Befehl); sonst nicht, deshalb
`anfrage_id`. MQTT: `tobibox/<box>/cmd` mit `befehl="lernen"`, `ttl_s` 60,
`daten` `{}`. Das Ziel geht **nicht** an die Box. Lehnt die Box den Befehl ab
(`event` `befehl_abgelehnt`, z. B. `zeit_unsicher`), meldet das Backend es als
Ereignis `lernmodus` mit `zustand="box_lehnt_ab"` (mit Klartext, `mqtt-v1.md`, 3.4).

#### 19. `tobibox/lernmodus/antwort`

Antwort auf die **Rückfrage vor dem Überschreiben** (Ereignis `lernmodus` mit
`zustand="rueckfrage"`, 6.2).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `befehl_id` | string | **ja** | aus dem Ereignis |
| `ueberschreiben` | bool | **ja** | `true`: die bestehende Zuordnung wird durch das Ziel des Lernmodus ersetzt. `false`: bleibt, das Backend lehnt die Meldung ab. |

Ausgabe: `{"zustand": "zugeordnet" | "abgelehnt", "konfig": <Konfig-Stand>}`.
Fehler: `kein_lernmodus` (kein offener Vorgang mit dieser `befehl_id`),
`rueckfrage_abgelaufen` (die Frist `frist_bis` ist vorbei, das Backend hat schon
mit `abgelehnt` bestätigt). Rechte: Admin. Idempotent: Endzustand ja; eine zweite
Antwort liefert `kein_lernmodus`. MQTT: bei `true` zuerst `tobibox/config` (Revision
+ 1), **danach** `…/ack` mit `grund="zugeordnet"`; bei `false` nur `…/ack` mit
`grund="abgelehnt"` (keine neue Konfiguration). Beide `ack` tragen `zuletzt` und `art`
der gemeldeten Kennung (`mqtt-v1.md`, 3.6).

#### 20. `tobibox/lernmodus/abbrechen`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `box` | string | **ja** | |

Ausgabe: `{"abgebrochen": <bool>}` (`true`, wenn ein Vorgang offen war). Das Backend
verwirft den Vorgang und sendet immer `lernen_abbrechen`, auch ohne offenen Vorgang
(im Zustand „Lernmodus aus“ wirkungslos, `mqtt-v1.md`, 3.7). Eine Meldung, die danach
noch mit der `befehl_id` des verworfenen Vorgangs eintrifft, bestätigt das Backend
mit `grund="abgelehnt"` (die Box meldet den Tobie dann erneut als unbekannt). Auch
eine offene Rückfrage endet so.

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
| `online` | bool oder `null` | aus `tobibox/<box>/online` (`online`/`offline`); `null`, wenn HA noch keine Nachricht kennt |
| `status` | object oder `null` | der letzte `tobibox/<box>/status` **unverändert** (`mqtt-v1.md`, 3.3, mit `speicher_frei_mb`, `netz`, `akku_prozent`, `sync`, `version`, `letzter_fehler`, `konfig`, `update` …); `null` ohne Nachricht. Neue Statusfelder erscheinen hier ohne Vertragsänderung. |
| `status_empfangen_am` | string oder `null` | wann HA ihn empfangen hat |
| `konfig_stand` | `aktuell`, `veraltet`, `unbekannt` | `status.konfig` gegen den Stand in HA (`aktuell`: gleiche `liste_id` und `revision`); `unbekannt` ohne Status |
| `lernmodus` | object oder `null` | der offene Vorgang dieser Box (Felder wie im Ereignis `lernmodus`, 4.3), sonst `null` |
| `ereignisse` | array | die letzten **20** Meldungen von `tobibox/<box>/event` (neueste zuerst): `{"id", "ts", "art", "daten", "text"}`; `art` und `daten` unverändert (`liste_abgelehnt`, `fehler`, `befehl_abgelehnt`), `text` ist der Klartext des Backends (`mqtt-v1.md`, 3.4: „Die Box … hat … abgelehnt“). So sieht Tobias abgelehnte Listen. |

Rechte: alle. Idempotent: ja. MQTT: –. Fehler: keine.

#### 22. `tobibox/box/sync`

Stößt den Medien-Sync der Box an (CUJ 9: „von HA angestoßen“). Ob er läuft, entscheidet
die Box nach der Netz-Regel (Heimnetz immer; Hotspot nur mit Lader oder über 50 %); wenn nicht,
steht es im Status (`sync.ergebnis="abgebrochen"`, `grund`).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `box` | string | **ja** | |
| `anfrage_id` | string | nein | siehe 2.2 |

Ausgabe: `{"befehl_id": <string>, "ttl_s": 300}`. Fehler: `box_unbekannt`,
`box_offline`, `mqtt_nicht_verbunden`, `anfrage_id_konflikt`. Rechte: Admin.
Idempotent: nicht ohne `anfrage_id`; ein zweiter Sync-Befehl während eines Syncs ist für
die Box harmlos (sie startet keinen zweiten). MQTT: `tobibox/<box>/cmd`,
`befehl="sync"`, `ttl_s` 300, `daten` `{}`. Das Ergebnis kommt über den Status
(Ereignis `boxen`).

### 3.8 Liste

#### 23. `tobibox/liste/neu_ausrollen`

Erzeugt eine neue Listen-ID und veröffentlicht die Konfiguration neu. Alle Boxen
nehmen sie an, auch bei niedrigerer Revision (`mqtt-v1.md`, 5.1 und 5.3; Betriebshandbuch
für den Fall einer Wiederherstellung aus der Sicherung).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `bestaetigt` | bool, muss `true` sein | **ja** | Schutz gegen versehentlichen Aufruf |
| `anfrage_id` | string | nein | siehe 2.2 |

Ausgabe: `{"konfig": <Konfig-Stand>, "veroeffentlicht": <bool>}`. Die neue Liste
beginnt mit Revision 1 (`data-model.md`, Abschnitt 2). Fehler: `anfrage_id_konflikt`.
Rechte: Admin. Idempotent: **nein** (jeder Aufruf erzeugt eine neue Listen-ID;
harmlos, aber unnötig), deshalb `anfrage_id`. MQTT: `tobibox/config` mit neuer
`liste_id`, `revision` 1, gleiche Zuordnungen und Einstellungen. Der Export auf das NAS
läuft wie nach jeder Änderung.

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
*   Das Backend bündelt: höchstens **ein Ereignis je Thema und Box (bzw. Serie) und
    Sekunde**. Die HA-Warteschlange je Verbindung ist begrenzt (4096 Nachrichten,
    Abschnitt 8); Ereignisse sind darum selten und klein.

### 4.1 Thema `boxen`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"boxen": [{"box", "online"}…]}` |
| `geaendert` | ein vollständiges Box-Objekt (3.7, ohne `ereignisse`), wenn sich `online`, `status` oder `konfig_stand` änderte |
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
| `uid` | string oder `null` | gemeldete Kennung (ab `rueckfrage`/`zugeordnet`) |
| `bisher` | object oder `null` | bei `rueckfrage`: das bisherige Ziel der Kennung |
| `grund` | string oder `null` | bei `abgelehnt`, `box_lehnt_ab`: Ursache |
| `text` | string oder `null` | Klartext |

`zustand`: `wartet` (Befehl gesendet, noch kein Tobie gemeldet), `rueckfrage` (Kennung
ist schon zugeordnet; die Seite zeigt die Frage und antwortet mit `lernmodus/antwort`),
`zugeordnet` (Ende), `abgelehnt` (Ende; `grund` ∈ `nutzer`, `abgelaufen`),
`abgebrochen` (Ende), `abgelaufen` (Ende: `frist_bis` ohne Meldung), `box_lehnt_ab`
(Ende; `grund` ∈ `bedingung`, `zeit_unsicher`).

`snapshot`: `{"vorgaenge": [<daten ohne Ende-Zustände>…]}` (höchstens ein Vorgang je
Box).

### 4.4 Thema `medien`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"pruefung_laeuft": <bool>, "geprueft_am": <string oder null>}` |
| `serien_geaendert` | `{"serie_ids": [<string>…]}` (Prüfung, anderer Nutzer, Upload oder Papierkorb haben etwas geändert; die Seite lädt `serien/list` bzw. `serie/get` neu) |
| `pruefung_fertig` | `{"geprueft_am": <string>, "neue_serien": <int>, "neue_folgen": <int>, "entfernte_folgen": <int>, "hinweise": <int>}` |
| `papierkorb_geaendert` | `{}` |

### 4.5 Thema `konfig`

| `art` | `daten` |
|---|---|
| `snapshot`, `geaendert` | `{"konfig": <Konfig-Stand>}`. `geaendert` kommt nach jeder Änderung durch `zuordnung/*`, `lernmodus/antwort`, `liste/neu_ausrollen` (auch von einem anderen Fenster oder einer Aktion aus). Die Seite lädt dann `zuordnung/list`. |

### 4.6 Thema `upload`

Wird nur für Uploads gesendet, die **diese Verbindung** gestartet hat (Zuordnung über
`upload_id`, 5.3). Es ergänzt den Fortschritt, den der Browser selbst beim Senden
misst (5.7), um die Phase **nach** dem Empfang.

| `art` | `daten` |
|---|---|
| `snapshot` | `{}` |
| `fortschritt` | `{"upload_id", "zustand": "empfange" \| "pruefe" \| "fertig" \| "fehler", "bytes": <int>, "code": <string oder null>}` – `empfange` höchstens einmal je Sekunde, `pruefe` einmal (Prüfung nach D5), `fertig`/`fehler` einmal am Ende (dann liegt die HTTP-Antwort schon vor oder folgt sofort) |

## 5. Hochladen (HTTP)

### 5.1 Endpunkt

*   **Pfad:** `POST /api/tobibox/upload/{serie_id}` (`{serie_id}` = Serien-ID,
    URL-kodiert). Eine Datei je Anfrage; mehrere Dateien sendet die Seite
    nacheinander.
*   **Umsetzung:** eine Klasse `TobiboxUploadView(HomeAssistantView)` mit `url`, `name =
    "api:tobibox:upload"`, `requires_auth = True` (Vorgabe), `cors_allowed = False`
    (Vorgabe); registriert mit `hass.http.register_view(...)` in `http.py`.
*   **Anmeldung:** Header `Authorization: Bearer <Zugriffstoken>` (das Token der
    HA-Sitzung; die Seite holt es aus dem `hass`-Objekt und erneuert es **vor** dem
    Start eines Uploads, falls es abgelaufen ist; das Token gilt nur beim Start der
    Anfrage, ein laufender Upload bricht nicht ab). Ohne gültiges Token antwortet HA mit
    401, das Backend prüft zusätzlich `is_admin` (403).
*   **Format des Körpers:** `multipart/form-data` (Design: `request.multipart()`).
    Felder **in dieser Reihenfolge**: `upload_id` (Text, optional, 8–64 Zeichen
    `[0-9A-Za-z-]`, von der Seite erzeugt), dann `datei` (die Datei, mit `filename`).
    Weitere Felder werden ignoriert, Felder nach `datei` nicht gelesen.
*   **Der Körper wird nie ganz gelesen.** Das Backend liest nur im Strom
    (`request.multipart()`, `part.read_chunk(...)`), keinesfalls `request.read()`,
    `request.post()` oder `request.json()`: Die sind durch die Größenbegrenzung der Anfrage
    gedeckelt (Abschnitt 8) und würden die Datei in den Speicher laden.

### 5.2 Strom in Blöcken

1.  Das Backend liest den Teil `datei` in Blöcken zu **1 MiB**
    (`UPLOAD_BLOCK_BYTES = 1048576`) und schreibt jeden Block über
    `hass.async_add_executor_job` in eine **Zwischendatei**
    `medien/_upload/<upload_id oder Zufall>.part` (gleiche Freigabe und gleiches
    Dateisystem wie das Ziel; ein Punkt-Name im Serien-Ordner würde sonst von der Box
    gesynct).
2.  Währenddessen zählt es die Bytes. Überschreitet die Datei `upload_max_bytes`:
    Abbruch, Zwischendatei löschen, 413 `datei_zu_gross`.
3.  Am Ende: `fsync`, Format prüfen (5.4), dann **atomar** in den Serien-Ordner
    umbenennen (`os.replace`). Die Box kann nie eine halbe Datei sehen.
4.  Den Namen der Folge hinten an `folgen` in `serie.json` hängen (atomar,
    `data-model.md`, 1.2 ohne `.bak`) und den Papierkorb-/Prüfzustand fortschreiben.
5.  Bricht die Verbindung ab (Handy verliert Netz), löscht das Backend die
    Zwischendatei sofort. Reste (`*.part`) älter als 24 h löscht es beim Start und bei
    jeder Prüfung der Freigabe.

### 5.3 Eingabe und Namen

| Feld/Teil | Regel |
|---|---|
| `{serie_id}` im Pfad | muss eine vorhandene Serie sein (`serie_nicht_gefunden`, 404) |
| `datei` | `filename` ist der Name der Folge. Er gilt, wie die Namen in `data-model.md`, 1.1: nicht leer, höchstens 255 Bytes (UTF-8), ohne `/` und `\`, nicht `.` oder `..`, **nicht mit `.` beginnend** (sonst `name_ungueltig`, 400). Der Name wird **nicht umgeschrieben** (keine Normalisierung). |
| Endung | siehe 5.4 |
| Name vergeben | Gibt es im Serien-Ordner schon eine Datei oder einen Ordner mit dem Namen: `datei_existiert` (409). Die Seite bietet Tobias an, umzubenennen und neu zu senden. |
| `upload_id` | verbindet die Anfrage mit den Ereignissen (4.6) und macht eine Wiederholung unschädlich (5.6) |

### 5.4 Formate und Prüfung (D5)

*   **Erlaubte Endungen** (ohne Unterscheidung von Groß- und Kleinschreibung), die Liste
    aus `data-model.md`, Abschnitt 5: `mp3`, `m4a`, `m4b`, `aac`, `flac`, `ogg`,
    `opus`, `wav`. Jede andere Endung: 415 `format_nicht_erlaubt`, noch **bevor** der
    Körper gelesen wird, wenn die Endung schon im ersten Teil steht (sonst nach
    dem Strom).
*   **Inhalt:** Das Backend öffnet die fertige Zwischendatei mit `ffprobe` (im
    Executor, Zeitlimit 30 s). Ist das erkannte Format keines der erlaubten (z. B. eine
    Textdatei mit Endung `.mp3`), lehnt es die Datei ab: 415 `format_nicht_erlaubt`.
*   **Kopierschutz und Defekte** (D5) führen **nicht zur Ablehnung**, sondern zur
    **Warnung** (das Design sagt „warnt sie“): Die Datei wird aufgenommen, in `folgen`
    eingetragen und mit `pruefung="warnung"` markiert. Warngründe: `kopierschutz`
    (Codec `drms`), `nicht_lesbar` (`ffprobe` scheitert), `probedekodierung_fehlgeschlagen`
    (Probedekodierung von 1 s). Fehlt `ffprobe` in HA, ist das Ergebnis
    `pruefung="nicht_moeglich"` mit Hinweis `pruefung_nicht_moeglich`.
*   Lautheit (D6) misst der Container auf dem NAS **später**; sie ist kein Teil des
    Uploads.

### 5.5 Ausgabe

Erfolg: HTTP 200, `Content-Type: application/json`.

```json
{
  "v": 1,
  "upload_id": "9b6c0f7e-3b52-4d1a-9c58-0e2b7a41d9f3",
  "serie_id": "3f9a1c07b2d4",
  "folge": "folge-04.mp3",
  "groesse_bytes": 48210433,
  "pruefung": "ok",
  "hinweis": null,
  "wiederholt": false
}
```

`pruefung` ∈ `ok`, `warnung`, `nicht_moeglich`; `hinweis` ist ein Code (siehe 3.2) oder
`null`; `wiederholt=true` heißt, die Antwort gehört zu einer früheren Anfrage mit
derselben `upload_id` (5.6). Fehler: HTTP-Status wie in Abschnitt 7 und der Körper

```json
{ "v": 1, "fehler": { "code": "format_nicht_erlaubt", "text": "Dieses Dateiformat spielt die Box nicht." } }
```

### 5.6 Idempotenz

Der Upload ändert den Zustand (eine neue Datei). Sendet die Seite dieselbe Datei mit
**derselben `upload_id`** noch einmal (z. B. weil die Antwort verloren ging) und die
Datei liegt nach dem ersten Versuch vollständig da, antwortet das Backend mit dem
alten Ergebnis (`wiederholt=true`) und nimmt nichts doppelt auf (es merkt sich die
letzten 100 `upload_id` für 1 Stunde im Arbeitsspeicher). Ohne `upload_id` oder mit
neuer: `datei_existiert`. Ein abgebrochener Versuch hinterlässt keine Datei und keinen
Eintrag, ein Neustart des Uploads ist also immer sicher (Fortsetzen eines
halben Uploads gibt es in Version 1 nicht).

### 5.7 Fortschritt

Die Seite sendet mit `XMLHttpRequest` und misst das Senden mit `upload.onprogress`
(`fetch` kann den Fortschritt beim Hochladen nicht melden). Nach dem letzten Byte
läuft die Prüfung auf dem Backend; dafür gibt es das Ereignis `upload` (4.6). Die
HTTP-Antwort kommt erst nach der Prüfung.

### 5.8 Was dieser Vertrag nicht regelt

*   Fortsetzen halber Uploads (Wiederaufnahme), parallele Übertragung einer Datei in
    mehreren Teilen.
*   Hochladen in einen **Folgen-Ordner** (mehrere Tracks, CD-Rip). In Version 1 legt
    der Upload nur **Dateien im Serien-Ordner** an. Folgen-Ordner kommen vom PC aufs
    NAS (D4); die Prüfung erkennt sie.
*   Ob Nabu Casa sehr große Anfragen und lange Übertragungen durchlässt: unbekannt, wird
    bei der Abnahme am Handy geprüft (Risiko im Design).

## 6. Abläufe

### 6.1 Neuer Tobie, Weg A (CUJ 7a, 12)

1.  Eine Box meldet eine Kennung (`…/unknown/<uid>`). Das Backend nimmt sie in
    „Neue Tobies“ auf, bestätigt auf `…/ack` (`neu` oder `bekannt`) und sendet das
    Ereignis `neue_tobies` (`neu`/`aktualisiert`).
2.  Die Seite zeigt den Eintrag (`neue_tobies/list`). Tobias wählt den Typ (Serie oder
    einzelne Folge, bei Folge die Folge) oder eine Aktionskarte und tippt.
3.  Die Seite sendet `zuordnung/set`. Das Backend schreibt die Zuordnung, erhöht die
    Revision, veröffentlicht `tobibox/config`, entfernt den Eintrag aus der Liste.
    Die Box übernimmt die Liste und wechselt, wenn der Tobie noch liegt, auf das Ziel.
4.  Tobias kann statt dessen `neue_tobies/verwerfen` aufrufen.

### 6.2 Lernmodus, Weg B (CUJ 7b)

Reihenfolge wie in `mqtt-v1.md`, 4.2. Fett die Befehle dieser Schnittstelle.

1.  Die Seite sendet **`lernmodus/start`** (Box, Typ, Ziel). Das Backend merkt sich Box,
    Ziel, Beginn und `befehl_id` und sendet `cmd` `lernen` (`ttl_s` 60). Ereignis
    `lernmodus` `wartet`.
2.  Die Box lernt höchstens 2 min und meldet einen aufgelegten Tobie als
    `art="gelernt"` mit `befehl_id` auf `…/unknown/<uid>`.
3.  Das Backend sucht den Vorgang mit dieser `befehl_id` und prüft `frist_bis`.
    *   **Kein offener Vorgang oder Frist vorbei** (auch nach **`lernmodus/abbrechen`**
        oder einem HA-Neustart): `ack` mit `grund="abgelehnt"`, keine Konfiguration.
        Die Box meldet den Tobie als unbekannt erneut; er erscheint in „Neue Tobies“.
    *   **Kennung noch nicht zugeordnet oder mit genau diesem Ziel:** weiter bei 4.
    *   **Kennung schon mit anderem Ziel zugeordnet:** Ereignis `lernmodus`
        `rueckfrage` (mit `uid`, `bisher`, `ziel`). Die Seite fragt Tobias und sendet
        **`lernmodus/antwort`**. Bei `ueberschreiben=false` oder wenn bis `frist_bis`
        keine Antwort kommt (auch ohne offene Seite): `ack` `abgelehnt`, Ende. Bei
        `true`: weiter bei 4.
4.  Das Backend schreibt die Zuordnung (Revision + 1), veröffentlicht **zuerst**
    `tobibox/config`, **danach** `ack` `grund="zugeordnet"` (Entscheidung H). Entfernt
    die Kennung aus „Neue Tobies“. Ereignis `lernmodus` `zugeordnet`.
    Ist das Ziel schon genau das bestehende, gibt es keine neue Revision; das Backend
    bestätigt trotzdem mit `zugeordnet`, und die Box wartet dann bis zu 10 s und spielt
    den Tobie wie beim normalen Auflegen (`mqtt-v1.md`, 4.2).
5.  Braucht Tobias für die Rückfrage länger als 10 s, spielt ein bekannter Tobie
    zuerst sein altes Ziel und wechselt mit der Zuordnung (gewollt, Entscheidung H,
    `mqtt-v1.md`, 4.2).
6.  Lehnt die Box den Befehl ab (`befehl_abgelehnt`) oder läuft die Frist ohne Meldung
    ab, endet der Vorgang (`box_lehnt_ab`, `abgelaufen`).

### 6.3 Medien (CUJ 9)

Serien anlegen, umbenennen, sortieren, löschen und Hochladen schreiben nur auf die
Freigabe. Die Box holt sie mit dem Sync. Es gibt keine MQTT-Nachricht und keine
Revision. Die Seite bietet nach einer Änderung „Sync jetzt“ an (`box/sync`).

### 6.4 Hochladen vom Handy (CUJ 9)

1.  Die Seite wählt die Serie, die Dateien und erzeugt je Datei eine `upload_id`.
2.  Sie holt ein frisches Token, sendet nacheinander je Datei `POST …/upload/<serie_id>`
    und zeigt den Fortschritt (5.7).
3.  Die Antwort liefert `pruefung`; bei `warnung` zeigt die Seite den Grund.
4.  Das Ereignis `medien` `serien_geaendert` lässt andere offene Fenster neu laden.

## 7. Gemeinsame Fehlercodes

Die Codes `invalid_format`, `unauthorized`, `unknown_command`, `unknown_error` sind
die von **Home Assistant**; alle anderen sind eigene Codes dieses Vertrags. Bei
WebSocket-Befehlen steht der Code in `error.code`; HA kennt im Fehlerobjekt nur `code` und
`message`. **Maschinenlesbare Einzelheiten stehen deshalb nie nur in `message`:**
Die Seite liest bei Bedarf den Zustand neu (z. B. `zuordnung/list` nach
`zuordnung_existiert`).

| Code | HTTP | Bedeutung | Befehle |
|---|---|---|---|
| `invalid_format` | 400 | Eingabe passt nicht zum Schema (fehlendes Pflichtfeld, falscher Typ, unbekanntes Feld, `bestaetigt` nicht `true`) | alle |
| `unauthorized` | 403 | Nutzer ist kein Administrator | alle schreibenden |
| `unknown_command` | – | Befehl dem Backend unbekannt (Seite neuer als Backend) | alle |
| `unknown_error` | 500 | Fehler im Backend (Fehler im Protokoll von HA); die Seite zeigt „Das hat nicht geklappt“ | alle |
| `anfrage_id_konflikt` | 409 | gleiche `anfrage_id` mit anderem Befehl oder anderen Feldern | die mit `anfrage_id` |
| `medien_nicht_erreichbar` | 503 | Die NAS-Freigabe ist nicht eingebunden oder antwortet nicht | Medien, Papierkorb, Upload |
| `medien_schreibfehler` | 500 | Schreiben auf die Freigabe schlug fehl (Rechte, Platz, Verbindung) | Medien, Papierkorb |
| `kein_speicher` | 507 | Auf der Freigabe ist kein Platz mehr | Upload |
| `mqtt_nicht_verbunden` | 503 | Der Broker ist nicht erreichbar; der Befehl wurde **nicht** gesendet. (Konfigurationsänderungen scheitern daran nicht: Sie sind gespeichert, `veroeffentlicht=false`.) | Befehle an Boxen |
| `serie_nicht_gefunden` | 404 | Serien-ID unbekannt | Serie, Folgen, Upload, Zuordnung, Lernmodus |
| `folge_nicht_gefunden` | 404 | Folge steht nicht in `folgen` der Serie | Folgen, Zuordnung, Lernmodus |
| `eintrag_nicht_gefunden` | 404 | Papierkorb-Eintrag unbekannt | Papierkorb |
| `box_unbekannt` | 404 | Box-Name ist nicht eingerichtet | Boxen, Lernmodus |
| `box_offline` | 409 | Die Box ist nach `…/online` nicht erreichbar | `lernmodus/start`, `box/sync` |
| `kennung_ungueltig` | 400 | `uid` ist nicht kanonisch (`reader-v1.md`, Abschnitt 4) | Zuordnung, Neue Tobies |
| `ziel_ungueltig` | 400 | `ziel` ist unvollständig oder widersprüchlich (z. B. `folge` ohne `serie`, unbekannte `aktion`, `aktion` im Lernmodus) | Zuordnung, Lernmodus |
| `zuordnung_existiert` | 409 | Die Kennung hat schon ein anderes Ziel, `ueberschreiben` fehlt | `zuordnung/set` |
| `konfig_zu_gross` | 413 | Die Konfiguration würde 256 KiB überschreiten (`mqtt-v1.md`, Abschnitt 1) | `zuordnung/set`, `lernmodus/antwort` |
| `name_ungueltig` | 400 | Name leer, zu lang oder mit unerlaubten Zeichen | Serie, Upload |
| `reihenfolge_ungueltig` | 400 | Die Liste ist keine Umstellung der vorhandenen Folgen | `folgen/order` |
| `stand_veraltet` | 409 | `stand` passt nicht mehr; die Seite lädt neu | `folgen/order`, `folge/delete` |
| `ueberraschung_existiert` | 409 | Es gibt schon eine Überraschungs-Serie | `serie/create` |
| `lernmodus_laeuft` | 409 | Für die Box läuft ein Lernmodus mit anderem Ziel | `lernmodus/start` |
| `kein_lernmodus` | 404 | Kein offener Vorgang mit dieser `befehl_id` | `lernmodus/antwort` |
| `rueckfrage_abgelaufen` | 409 | `frist_bis` ist vorbei; das Backend hat die Meldung abgelehnt | `lernmodus/antwort` |
| `datei_existiert` | 409 | Im Serien-Ordner gibt es den Namen schon | Upload, `papierkorb/restore` |
| `datei_zu_gross` | 413 | größer als `upload_max_bytes` | Upload |
| `format_nicht_erlaubt` | 415 | Endung oder erkanntes Format nicht nach D5 | Upload |

Der Körper einer HTTP-Fehlerantwort des Uploads ist in 5.5 beschrieben. Eine
unbekannte `code`-Zeichenfolge (neueres Backend) zeigt die Seite mit `message`
beziehungsweise `fehler.text`.

## 8. Grenzen

Aus dem Quelltext von Home Assistant (Zweig `dev`, abgerufen am 09.11.2026; **maßgeblich ist die
feste HA-Version** der Stufe 3a, die Tobias nennt) und aus dem Design:

| Grenze | Wert | Quelle und Folge |
|---|---|---|
| Größe einer **eingehenden** WebSocket-Nachricht | 4 MiB (Vorgabe von aiohttp; HA setzt `WebSocketResponse(heartbeat=55, …)` ohne eigenen Wert) | Darum **keine** Dateien über WebSocket, sondern HTTP (Abschnitt 5). Eingaben dieses Vertrags sind klein (wenige KiB). |
| Größe einer Nachricht, die dieser Vertrag **sendet** | höchstens 64 KiB (wie `mqtt-v1.md`) | `neue_tobies/list`, `papierkorb/list` blättern mit `limit` (höchstens 200 Einträge ≈ 50 KiB). `zuordnung/list` ist durch die Konfiguration (höchstens 256 KiB) begrenzt; über 64 KiB (etwa 500 Zuordnungen) blättert die Seite mit `limit`/`offset`, in Version 1 bei `zuordnung/list` nicht vorgesehen: siehe offene Punkte. |
| Nachrichten je Verbindung, bis HA sie trennt | 4096 wartende Nachrichten (`MAX_PENDING_MSG`) | Ereignisse sind gebündelt (4). |
| Lebenszeichen der WebSocket-Verbindung | 55 s (`heartbeat`) | von HA, nichts zu tun |
| Anmeldung | Die Verbindung muss die Authentifizierung (`auth`) innerhalb weniger Sekunden schicken | macht `hass.connection` der Oberfläche |
| Normale HTTP-Anfragen von HA | Design: 16 MiB | Die Stelle im Quelltext habe ich bei der Prüfung **nicht gefunden**; die Aussage des Designs gilt, bis AP 3.1 es gegen die feste HA-Version belegt. Der Upload liest im Strom und ist davon unabhängig, solange nie `read()`, `post()` oder `json()` benutzt wird. `HomeAssistantView.max_body_size` (Attribut) gibt es; der Upload setzt es **nicht**. |
| Größe einer Audiodatei | `upload_max_bytes` (Vorschlag 2 GiB, offener Punkt) | Schutz vor vollem Speicher. |
| Block des Uploads | 1 MiB | fest in Version 1 |
| Zugriffstoken | gültig ~30 min | gilt für den **Start** einer Anfrage; die Seite erneuert vor jedem Upload. |
| Länge eines Namens | Serie 1–100 Zeichen; Folge 255 Bytes | `data-model.md` |
| Nabu Casa | unbekannt (Upload-Größe, Dauer) | Abnahme am Handy (Stufe 3a). Ausweg: Dateien per PC auf das NAS (D4). |

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
nur Ergänzungen (Abschnitt 9, „Ohne Erhöhung“).

| Befehl | Stufe | Skizze (Vorschlag, keine Festlegung) |
|---|---|---|
| `tobibox/einstellungen/get` | 4 (AP 4.7) | Liest `leise_zeiten` (`zeitzone`, `fenster`), `gute_nacht` (`timer_min`, `ausblenden_s`) und optional `hinweis_pegel`: dieselben Schemas und Wertebereiche wie in `data-model.md`, Abschnitt 2; dazu `konfig`. Rechte: alle. |
| `tobibox/einstellungen/set` | 4 (AP 4.7) | Setzt `leise_zeiten` und/oder `gute_nacht` als **ganze Objekte**; Prüfung wie die Box (ungültig: ganze Änderung abgelehnt, Fehlercode `einstellung_ungueltig` mit Pfad in `message`). Rechte: Admin. Idempotent. MQTT: `tobibox/config` (Revision + 1). Fähigkeit `einstellungen`. |
| `tobibox/box/update` | 3b (AP 3.8/3.11) | `{"box", "version"?}`; Backend nimmt ohne Angabe die neueste Version aus `releases/`. Rechte: Admin. MQTT: `cmd` `update`, 300 s (`mqtt-v1.md`, 3.7). Ergebnis über `status.update` (Ereignis `boxen`). Fehler wie bei `box/sync`, dazu `keine_version`. Fähigkeit `update`. |
| `tobibox/releases/list` | 3b | Liest die vorhandenen Pakete auf `releases/` (nur Name und Version). Rechte: alle. |
| `tobibox/serie/delete` | offen | verschiebt eine ganze Serie in den Papierkorb (das Design nennt nur das Löschen von Folgen) |
| `tobibox/folge/rename` | offen | siehe offene Punkte (Folgen-Zeiger und `ziel.folge` hängen am Namen) |

**Schon in Stufe 3a nötig:** Das Backend legt `leise_zeiten` (`zeitzone`
`Europe/Berlin`, `fenster` leer) und `gute_nacht` (`timer_min` 30, `ausblenden_s` 60,
die Vorschläge des Designs) in der Konfiguration an, weil `config.json` sie als Pflicht
verlangt, und schreibt sie bei jeder Änderung unverändert fort. **Lautheit (D6)** hat
keinen Befehl: Der Container läuft nach Zeitplan, ohne Auslöser aus HA (Design).
Sichtbar wird sie höchstens später als optionales Feld an der Folge.

## Festlegungen in diesem Vertrag (Stand 09.11.)

Das Design lässt diese Einzelheiten offen. Entschieden wurde die einfachste
stimmige Lösung. **Nichts davon ist bestätigt**; alles geht mit der Freigabe an Tobias
und wird erst dann „bestätigt“.

1.  **Rechte:** Lesen für jeden angemeldeten Nutzer, Schreiben nur Administratoren
    (2.1), abgeleitet aus Entscheidung D und dem Umstand, dass es nur Tobias gibt.
2.  **Ein Abo mit Themen** (`tobibox/subscribe`) statt eines Abos je Thema; Snapshots
    enthalten nur Zähler, nie Listen.
3.  **`anfrage_id`** für Befehle ohne natürliche Idempotenz (2.2); Speicherdauer
    10 min, 100 Stück.
4.  **`stand`** (Fingerabdruck) gegen gleichzeitige Änderungen von außen (drei
    Schreiber, Risiko im Design), nur dort, wo die Reihenfolge oder Löschen von einem
    alten Bild der Seite ausgehen kann.
5.  **Zuordnung vor Medien:** Eine Zuordnung darf auf eine Serie zeigen, die noch auf
    keiner Box ist (Design, `data-model.md`, Abschnitt 2), muss aber auf der Freigabe
    existieren.
6.  **Löschen einer zugeordneten Folge** lässt die Zuordnung stehen und meldet
    `betroffene_tobies` (Papierkorb ist umkehrbar).
7.  **Rückfrage-Frist** beim Überschreiben = `frist_bis` (180 s), danach `abgelehnt`.
8.  **Rückfrage als Ereignis plus Antwortbefehl** statt eines Feldes in `lernmodus/start`.
9.  **Zwischendatei** für Uploads in `medien/_upload/` (gleiche Freigabe, gleiches
    Dateisystem), damit die Box nie halbe Dateien sieht.
10. **Kopierschutz = Warnung, nicht Ablehnung** (Wortlaut D5: „warnt sie“).
11. **`medien/pruefen` läuft im Hintergrund** und meldet das Ende als Ereignis, damit
    der Befehl in 10 s antwortet.
12. **Fortschritt des Sendens misst der Browser;** Ereignisse gibt es nur für die
    Prüfung danach.
13. **Neue-Tobies-Liste im HA-Speicher,** nicht in `tobibox/config` und ohne Revision.
14. **Papierkorb: wiederherstellen hinten in `folgen`;** die alte Position wird nicht
    gemerkt.

## Prüfung gegen die Home-Assistant-API

Geprüft am 09.11.2026 gegen den Quelltext von `home-assistant/core` (Zweig `dev`) per
Abruf, soweit angegeben. Alles andere stammt aus Wissen und ist in AP 3.1 gegen die
feste HA-Version zu belegen.

| Aussage | Stand |
|---|---|
| `websocket_api.websocket_command(schema)` setzt Schema und Befehlsnamen (`schema["type"]`); `extra` des Schemas lehnt Unbekanntes ab | geprüft (Quelltext). In `dev` heißt die Schema-Bibliothek in den Modulen `probatio`; das Verhalten ist das von `voluptuous` (Namensunterschied hängt an der HA-Version). Der Vertrag benutzt nur Typen (`str`, `int`, `bool`, Listen, Bereiche). |
| `websocket_api.async_response` führt den Handler als Hintergrundaufgabe aus; Pflicht für alles mit `await` | geprüft |
| `websocket_api.require_admin`: Nutzer muss `is_admin` sein, sonst `unauthorized` | geprüft. Reihenfolge der Dekoratoren wie in HA-Core: `@require_admin`, `@websocket_command(...)`, `@async_response` |
| `connection.send_result`, `send_error(msg_id, code, message)`, `send_event`, `send_message`; `websocket_api.event_message(id, event)` | geprüft |
| Abos: `connection.subscriptions[msg["id"]] = unsub`; das Beenden macht HAs `unsubscribe_events` (mit `subscription`); beim Trennen der Verbindung ruft HA alle `unsub` auf | geprüft (`subscriptions`, `async_handle_close`); `unsubscribe_events` aus Wissen |
| Fehlerobjekt hat nur `code` und `message` (plus Übersetzungsschlüssel) | geprüft |
| Eingebaute Fehlercodes `invalid_format`, `unauthorized`, `not_found`, `unknown_command`, `unknown_error`, `home_assistant_error` | geprüft (`const.py`) |
| `HomeAssistantView`: `requires_auth = True` und `cors_allowed = False` als Vorgabe; nicht angemeldete Anfrage → 401; Attribut `max_body_size` | geprüft |
| `request[KEY_HASS_USER]` (aus `homeassistant.components.http.const`) liefert den Nutzer | Name geprüft; Nutzung aus Wissen |
| Streaming: `request.multipart()` (aiohttp) und `part.read_chunk(size)`; `request.content.iter_chunked(n)` | aus Wissen (aiohttp-API). Nicht per Abruf geprüft. |
| `panel_custom.async_register_panel(hass, frontend_url_path, webcomponent_name, sidebar_title, sidebar_icon, module_url, embed_iframe, config, require_admin, …)` | geprüft (Signatur) |
| Statische Dateien: `hass.http.async_register_static_paths([StaticPathConfig(...)])` | aus Wissen |
| Obergrenze „normale Anfragen 16 MiB“ | **nicht gefunden**, siehe Abschnitt 8 |
| Grenze der WebSocket-Nachricht | geprüft: HA setzt keinen Wert, es gilt die Vorgabe von aiohttp (4 MiB, aus Wissen) |

## Offene Punkte für Tobias

Entscheidungen, die sich nicht aus den Quellen ableiten lassen. Der Vertrag nennt je
einen Vorschlag; erst mit deiner Antwort gelten sie.

1.  **Seite für Nicht-Administratoren (`panel_custom` `require_admin`)?** Es gibt nur
    dich. Vorschlag: Seite nur für Administratoren (`require_admin=True`), die
    Befehle prüfen unabhängig davon. Alternative: Seite für alle sichtbar, andere
    Nutzer nur lesend (2.1).
2.  **Was heißt „Bestätigen“ bei Neue Tobies?** Der Vertrag liest es als „zuordnen“
    (`zuordnung/set`). Die Bestätigung an die Box (`…/ack`, `neu`/`bekannt`) geschieht
    automatisch beim Eintreffen und ist kein Knopf. Meinst du etwas anderes?
3.  **„Umbenennen“:** Der Vertrag kennt in Version 1 nur das Umbenennen einer **Serie**
    (D4). Eine Folge umzubenennen ändert ihren Schlüssel; Folgen-Zeiger der Boxen und
    `ziel.folge` aller Folgen-Tobies würden ins Leere zeigen. Soll es das geben? Dann
    muss das Backend `ziel.folge` in der Konfiguration mit umschreiben, und die
    Zeiger auf den Boxen gehen verloren (`resume.json` hat keine Umbenennung).
4.  **Ganze Serie löschen (`serie/delete`)?** Das Design nennt nur das Löschen von
    Folgen. Vorschlag: in Version 1 nicht anbieten.
5.  **Folge oder Serie löschen, auf die ein Tobie zeigt:** Vorschlag: nur Hinweis
    (`betroffene_tobies`), die Zuordnung bleibt, die Box spielt bis zur
    Wiederherstellung die Überraschungs-Serie. Alternative: Rückfrage vor dem
    Löschen.
6.  **Höchste Dateigröße beim Upload.** Vorschlag: 2 GiB (`upload_max_bytes`). Das Design
    nennt keine Grenze; sie schützt nur vor vollem Speicher.
7.  **Gleicher Dateiname beim Upload:** Vorschlag: ablehnen (`datei_existiert`), du
    benennst um. Alternative: automatisch `name (2).mp3`.
8.  **Kopiergeschützte oder defekte Datei:** Vorschlag: aufnehmen, in `folgen`
    eintragen, mit Warnung markieren (Wortlaut D5 „warnt“). Alternative: gar nicht
    aufnehmen. Die Box überspringt eine Datei, die sie nicht spielen kann.
9.  **Folgen-Ordner (CD-Rips) von der Seite anlegen oder befüllen?** Vorschlag: nein;
    sie kommen vom PC aufs NAS (D4), die Prüfung erkennt sie.
10. **Namen für Tobies.** Das Datenmodell hat keinen: Die Seite zeigt nur die Kennung
    (gekürzt). Vorschlag: optionales Feld `name` in `zuordnungen.<uid>` (additiv,
    `data-model.md` und `mqtt-v1.md` müssten angepasst werden). Entscheidung der
    Projektleitung und von dir.
11. **Rückfrage-Frist beim Überschreiben:** Vorschlag: bis `frist_bis` (180 s), dann
    „abgelehnt“. Der Wechsel auf das neue Ziel kann länger als 10 s dauern; das ist
    in Entscheidung H schon als „gewollt“ geführt.
12. **Zweiter Lernmodus mit anderem Ziel:** Vorschlag: `lernmodus_laeuft`, erst
    abbrechen. Alternative: den laufenden Vorgang ersetzen.
13. **Überraschungs-Serie von der Seite anlegen?** Vorschlag: ja, wenn noch keine
    existiert (`serie/create` mit `typ`). Offen auch: darf eine Überraschungs-Serie
    Ziel einer Zuordnung sein (Vorschlag: nicht verboten, aber sinnlos).
14. **`_upload/` und `_papierkorb/` aus dem Sync ausnehmen.** Der rsync-Daemon des
    NAS und die Box (AP 3.4, 3.5, `rsyncd.example.conf`) müssen beide Ordner
    ausschließen; das Design nennt es nur für `_papierkorb/`. Betrifft
    Dokumente, die dieser Vertrag nicht ändert.
15. **Papierkorb-Metadaten** (Herkunft eines Eintrags): Das Backend braucht eine
    Hilfsdatei je Eintrag. Soll sie in `data-model.md` aufgenommen werden? Vorschlag:
    ja, als Abschnitt `papierkorb`.
16. **Sehr viele Zuordnungen:** `zuordnung/list` hat in Version 1 keine
    Seitenaufteilung. Vorschlag: bis 500 Zuordnungen unkritisch; bei mehr
    `limit`/`offset` ergänzen (ohne neue Version, 9). Passt das?
17. **Aufbewahrung der Box-Meldungen** (abgelehnte Listen, Fehler): Vorschlag: die
    letzten 20 je Box im Arbeitsspeicher von HA; ein Neustart von HA leert sie. Soll
    das in den HA-Speicher?
18. **Leise-Zeiten:** Das Design legt die Bedienung in **Stufe 4** (AP 4.7). Der Vertrag
    reserviert `einstellungen/get` und `einstellungen/set` und legt in 3a nur die
    Vorgaben an. Ist das so gewollt, oder soll die Bedienung schon in Stufe 3a
    kommen?
19. **HA-Version:** Du nennst die laufende Version vor AP 3.1. Der Vertrag stützt sich
    auf `dev`; die Einzelheiten in „Prüfung gegen die Home-Assistant-API“ belegt AP 3.1
    gegen diese Version, vor allem die 16-MiB-Grenze.
20. **Upload über Nabu Casa:** Grenzen unbekannt (Größe, Dauer). Klärung bei der
    Abnahme am Handy; Ausweg D4.
