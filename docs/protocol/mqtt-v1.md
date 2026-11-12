# MQTT-Schnittstelle Box ↔ Home Assistant, Version 1 (`mqtt-v1`)

*   **Status:** Vertrag Stufe 0, Entwurf zur Prüfung durch einen Goldfisch
*   **Grundlage:** `docs/designs/box-software.md` (Baustein 4 „MQTT-Schnittstelle
    Box ↔ HA“, CUJ 7a, 7b, 12, „Revisionsregel“, „Lernmodus“)
*   **Gilt für:** Modul `ha` des Box-Dienstes und `mqtt.py` der
    HA-Integration `tobibox`. Schemas der Inhalte: `data-model.md`. Ereignisse
    und Befehle im Kern: `core-interface.md`.
*   **Änderung 11.11. (Anzeige „Freier Speicher“):** Die Discovery des Sensors `speicher_frei` (6.2) trägt zusätzlich
    `suggested_unit_of_measurement` `GB` und `suggested_display_precision` `0` (Kurzformen `sug_unit_of_meas`, `sug_dsp_prc`; beide Schlüssel kennt
    der MQTT-Sensor von Home Assistant, auch in 2026.10/11). Reine Anzeige: Statusfeld `speicher_frei_mb`, Einheit `MB` und `v` bleiben. Die Versionsregel
    (Abschnitt 8) verlangt kein neues `v`. Weil HA eine vorhandene Entität nicht immer umstellt, muss einmalig die Anzeigeeinheit in den Entitätseinstellungen gesetzt werden.
*   **Änderung 10.11. (Ein/Aus, 10.11.; Klarstellung):** Das Statusfeld `lader` (3.3) und der Sensor „Lader“ (6.2) bleiben, wie sie
    waren: Es war schon immer der Wert „externer Strom“ des PiSugar (`battery_power_plugged`), also Strom am Eingang aus jeder Quelle (Netzteil, Sockel, Kabel,
    Powerbank), nicht „lädt gerade“. Die Bedeutung ändert sich nicht (V8); dieser Text stellt es nur klar. Neu ist nur, woher der Wert kommt: bei zwei Quellen
    (`pisugar-server` und Leser) gilt der Leser (`core-interface.md`, Abschnitt 9, Punkt 9). Name, Typ, `device_class` und `v` bleiben, kein neues Feld;
    die Versionsregel (Abschnitt 8) verlangt deshalb kein neues `v`.
*   **Änderung 09.11. (Befunde des Code-Reviews zu AP 3.7 und 4.8, Entscheidung P, Rev. 3.17):** `event` `fehler` bekommt zwei
    Codes der Box (3.4): `kopfhoerer_unlesbar` (Entscheidung P: der Kopfhörer-Kontakt ist nicht lesbar, es gilt die Kopfhörer-Grenze)
    und `herunterfahren_fehlgeschlagen` (B1). `befehl_abgelehnt` für `update` nennt bis Stufe 3b `detail` „Update kommt mit Stufe 3b.“ (B16).
    Rückwärtskompatibel: `art` und Felder bleiben, `code` ist ein freier Text.
*   **Änderung 09.11. (Tobie-Namen, Vertrag W):** Jede Zuordnung in `tobibox/config` darf
    ein optionales Feld `name` tragen (3.1). Die Box ignoriert es; sie liest nur `ziel`.
    Rückwärtskompatibel: kein neues `schema_version`, keine neue Revisionsregel.
*   **Änderung 09.11. (Entscheidung N, 09.11.):** `tobibox/config` darf das optionale Feld
    `lesezeichen_tage` tragen (3.1; `data-model.md`, Abschnitt 2). Rückwärtskompatibel: kein
    neues `schema_version`, keine neue Revisionsregel.
*   **Änderung 09.11. (Abgleich mit Vertrag W, Abschnitt 13):** 5.1 beschreibt die Listen-ID jetzt
    nach den Zuständen `ok`, `leer_neu` und `export_neuer`; ein leerer Speicher setzt nicht mehr von
    selbst eine neue Listen-ID.
*   **Änderung 09.11. (Befund AP 3.1):** Abschnitt 7 (ACL) noch einmal korrigiert: Das Add-on liest
    alle `*.conf` unter `/share/mosquitto/` als Mosquitto-Konfiguration. Die Regeln stehen deshalb in
    der Datei `accesscontrollist` ohne Endung; `acl.conf` enthält nur `acl_file …` (09.11., Befund AP 3.1).
*   **Änderung 09.11.:** Abschnitt 7 (ACL) korrigiert: In der Form mit
    `pattern` müssen auch die Leserechte für `tobibox/config` und
    `homeassistant/status` `pattern read` heißen; ein `topic read` ohne `user`
    gehört bei Mosquitto zum zuletzt genannten Konto (Test gegen Mosquitto 2.0.18).

## 1. Grundsätze

*   **MQTT ist nur Verteilkanal.** Die Zuordnungen liegen im HA-Speicher (D1);
    die Nachrichten transportieren sie. Die Box spielt ohne Broker alles, was
    sie kennt.
*   **Broker:** Mosquitto-Add-on in HA. Die Box erreicht ihn über Tailscale
    (Heimnetz oder Hotspot, ein einziger Weg).
*   **Protokoll:** MQTT 3.1.1, `paho-mqtt` ab Version 2. TLS ist nicht nötig
    (Tailscale verschlüsselt).
*   **Verbindung der Box:** Konto = Box-Name (siehe 2), Client-ID
    `tobibox-<box>`, **dauerhafte Sitzung** (`clean_session=False`),
    Keep-Alive 30 s, Neuverbinden mit Wartezeit 1 s, 2 s, 5 s, 10 s, dann 30 s.
    Will-Nachricht (siehe 3.2).
*   **QoS 1** für alle Nachrichten dieses Vertrags (Zustellung mindestens
    einmal). Empfänger verarbeiten **idempotent**: doppelte Zustellung schadet
    nicht (Mittel: `id` der Nachricht, Schlüssel `uid`, Revision).
*   **Nachrichtenformat:** JSON, UTF-8. Jede JSON-Nachricht dieses Vertrags
    enthält `"v": 1` (Abschnitt 8), **außer**: `tobibox/config` (hat
    `schema_version`), `…/online` (reiner Text), `…/ui/*` (feste Texte oder
    Anzeigename aus der HA-Entität), `homeassistant/status` (Text von Home
    Assistant), die Discovery-Nachrichten `homeassistant/…/config` (Format von
    Home Assistant) und die leere Nutzlast, die eine dauerhafte Nachricht
    löscht. Zeitstempel wie in `data-model.md`
    (`2026-11-05T09:30:00Z`). Unbekannte Felder werden ignoriert. Höchstens
    64 KiB je Nachricht, `tobibox/config` höchstens 256 KiB.
*   **Box-Name** `<box>`: `[a-z0-9][a-z0-9_-]{1,23}`, in `tobibox.toml`
    (`box_id`), z. B. `box1`, `box2`. Er ist zugleich der MQTT-Benutzername.
    Zugangsdaten stehen nie im Repo.

## 2. Themenbaum

`<box>` = Box-Name, `<uid>` = kanonische Kennung (`[0-9a-f]`, `reader-v1.md`).

| Thema | Richtung | Veröffentlicht von | Abonniert von | QoS | retained | Zweck |
|---|---|---|---|---|---|---|
| `tobibox/config` | HA → Boxen | HA-Integration | alle Boxen | 1 | **ja** | ganze Konfiguration mit Revision und Listen-ID |
| `tobibox/<box>/online` | Box → HA | Box (Birth) und Broker (Will) | HA | 1 | **ja** | Erreichbarkeit der Box |
| `tobibox/<box>/status` | Box → HA | Box | HA | 1 | **ja** | Zustand für Sensoren |
| `tobibox/<box>/event` | Box → HA | Box | HA | 1 | nein | Ereignisse ohne Bestätigung: abgelehnte Liste, Fehler, abgelehnter Befehl |
| `tobibox/<box>/unknown/<uid>` | Box → HA | Box | HA | 1 | **ja** | unbekannte oder gelernte Kennung, bis HA bestätigt |
| `tobibox/<box>/unknown/<uid>/ack` | HA → Box | HA-Integration | diese Box | 1 | **nein** | Bestätigung einer Kennung (mit Grund, `zuletzt` und `art` der bestätigten Meldung) |
| `tobibox/<box>/cmd` | HA → Box | HA-Integration | diese Box | 1 | **nein** | Befehle mit Ablaufzeit (Lernmodus, Sync, Update) |
| `tobibox/<box>/ui/<objekt>` | HA → HA-Integration | Home-Assistant-Entität (Knopf, Auswahl) | HA-Integration | 1 | nein | Eingaben der Entitäten, die die Integration in `cmd` umsetzt oder sich merkt (3.8) |
| `homeassistant/<komponente>/tobibox_<box>/<objekt>/config` | Box → HA | Box | HA | 1 | **ja** | MQTT-Discovery (Abschnitt 6) |
| `homeassistant/status` | HA → alle | Home Assistant | Box | – | – | HA meldet `online` nach dem Start; die Box veröffentlicht daraufhin die Discovery erneut |

Es gibt keine weiteren Themen. Die Box schreibt nie auf `tobibox/config`,
`…/cmd`, `…/ack` oder `…/ui/…`.

## 3. Nachrichten

### 3.1 `tobibox/config` (retained)

Inhalt: genau das Schema von `config.json` (`data-model.md`, Abschnitt 2),
einschließlich `schema_version`, `revision` und `liste_id`. Es gibt kein
zusätzliches `v`; `schema_version` übernimmt diese Rolle. Seit Entscheidung F
(05.11.) ist `schema_version` **2**: Jede Zuordnung trägt ein Feld `ziel`
(`serie`, `folge` oder `aktion`). Eine Box, die nur Version 1 kennt, lehnt die
Liste mit `schema_zu_neu` ab (5.2). **Reihenfolge der Einführung (Entscheidung F,
05.11.): zuerst alle Boxen aktualisieren, danach verteilt HA Version 2.** Eine
Box mit Entscheidung F nimmt auch Listen der Version 1 an (5.2).

*   **Tobie-Name (09.11.):** Eine Zuordnung darf ein optionales Feld `name` tragen
    (Text, 1–60 Zeichen, `data-model.md`, Abschnitt 2), das die HA-Seite als Namen des
    Tobies anzeigt. Die Box **ignoriert** es (Prüfung und Annahme der Liste hängen nur an
    `ziel`; ein vorhandenes `name` macht die Liste nie ungültig) und schreibt es nicht in
    ihre `config.json`. Eine Box ohne diese Änderung ignoriert es ebenso (unbekannte Felder
    werden ignoriert, Abschnitt 1). Auch eine Änderung nur des Namens erhöht die Revision.
*   **Lesezeichen-Frist (Entscheidung N, 09.11.):** Die Liste darf ein optionales Feld
    `lesezeichen_tage` tragen (ganze Zahl 0 bis 365, `0` = Lesezeichen laufen nie ab; fehlt es, gilt 14).
    Anders als `name` **liest die Box es** (`validiere_konfig`, Anzeige und Wirkung in
    `core-interface.md`, 6.3). Ein ungültiger Wert macht die ganze Liste ungültig (`schema_ungueltig`).
    Eine Box ohne Entscheidung N ignoriert das Feld (sie kennt keinen Ablauf).
    HA veröffentlicht das Feld in jeder Liste, bei Bedarf mit der Vorgabe 14 (09.11., Befund AP 3.1). Auch eine Änderung nur
    dieses Feldes erhöht die Revision.
*   HA veröffentlicht nach **jeder** Änderung der Konfiguration (Revision + 1)
    und bei „Liste neu ausrollen“ (neue `liste_id`).
*   Der Broker liefert die dauerhafte Nachricht bei jedem Abonnieren erneut. Die
    Box wendet deshalb die Revisionsregel (Abschnitt 5.2) an und tut bei
    gleicher Fassung nichts.

Beispiel (gekürzt):

```json
{
  "schema_version": 2,
  "revision": 17,
  "liste_id": "a3f9c1e07b2d4856",
  "erzeugt_am": "2026-11-05T09:30:00Z",
  "zuordnungen": {
    "e0040312345678ab": { "ziel": { "typ": "serie", "serie": "3f9a1c07b2d4" }, "name": "Rabe aus Holz" },
    "04a1b2c3": { "ziel": { "typ": "folge", "serie": "8c21d5e9a0b7", "folge": "folge-03.mp3" } },
    "04ffeedd": { "ziel": { "typ": "aktion", "aktion": "status" } }
  },
  "leise_zeiten": { "zeitzone": "Europe/Berlin", "fenster": [] },
  "gute_nacht": { "timer_min": 30, "ausblenden_s": 60 },
  "lesezeichen_tage": 14
}
```

### 3.2 `tobibox/<box>/online` (retained)

Reiner Text, kein JSON: `online` oder `offline`.

*   Die Box setzt beim Verbinden die **Will-Nachricht** `offline`
    (retained, QoS 1) und veröffentlicht nach erfolgreicher Verbindung und dem
    Abonnieren `online` (retained, QoS 1).
*   Ein sauberes Beenden des Dienstes veröffentlicht vor dem Trennen `offline`.

### 3.3 `tobibox/<box>/status` (retained)

Gesamtzustand der Box. Die Box veröffentlicht, wenn sich ein Feld außer `ts`
ändert, zusammengefasst auf höchstens **eine Nachricht je 5 s**, und
unabhängig davon alle 300 s sowie nach jedem Verbinden. Wer den Status zusammenbaut
und woher jedes Feld stammt (einschließlich der Abbildung von `leser`), steht in
`core-interface.md`, Abschnitt 12.

| Feld | Typ | Bedeutung |
|---|---|---|
| `v` | int | `1` |
| `ts` | string | Zeitpunkt der Nachricht (Wanduhr der Box) |
| `zustand` | string | Zustand der Wiedergabe-Sitzung: `leer`, `spielt`, `pausiert`, `beendet`, `gehalten`, `unbekannt`; während des Herunterfahrens `herunterfahren` |
| `lernmodus` | bool | Lernmodus aktiv |
| `serie` | object oder `null` | aktuelle Serie `{"id": …, "name": …}`; `null`, wenn keine |
| `folge` (optional) | object | aktuelle Folge `{"name": <Name der Folge>, "track": <int ab 0>}` (Entscheidung F, 05.11.); fehlt oder `null`, wenn keine Folge gewählt ist. Optionales Feld, `v` bleibt `1` |
| `akku_prozent` | int 0–100 oder `null` | `null`, wenn unbekannt (z. B. am Mac ohne Simulation) |
| `lader` | bool oder `null` | Strom am Eingang der Box, aus jeder Quelle (Netzteil, Sockel, Kabel, Powerbank; Ein/Aus, 10.11.); `null`, solange keine Quelle einen Wert geliefert hat |
| `netz` | string | `home`, `hotspot` oder `offline` |
| `sync` | object | `{"zustand": "idle"\|"laeuft"\|"fehler", "letzter_ende": <Zeitstempel oder null>, "ergebnis": "ok"\|"abgebrochen"\|null, "grund": <Text oder null>, "neu": <int>}` |
| `speicher_frei_mb` | int | freier Platz auf dem Medien-Dateisystem in MB |
| `version` | string | Version des Dienstes (`manifest.json`) |
| `firmware` | string oder `null` | `fw` des Lesers aus dem `HELLO`, `null` ohne Verbindung |
| `protokoll` | int | Hauptversion des Leser-Protokolls, die der Dienst spricht |
| `leser` | string | Prüfpunkt Leser: `ok`, `fehler`, `getrennt`, `simulation` |
| `letzter_fehler` | object oder `null` | `{"zeit": <Zeitstempel>, "text": <Text>}` |
| `zeitquelle` | string | `system`, `rtc`, `ntp` oder `unbekannt` |
| `zeit_ok` | bool | Uhrzeit vertrauenswürdig (sonst gelten Leise-Zeiten vorsichtig, siehe Design) |
| `konfig` | object | die gespeicherte Konfiguration `{"revision": <int>, "liste_id": <string>}`; `{"revision": 0, "liste_id": ""}`, wenn keine |
| `update` | object | `{"zustand": "ok"\|"testing"\|"failed", "version": <string>, "grund": <Text oder null>}` |

Beispiel:

```json
{
  "v": 1,
  "ts": "2026-11-05T09:30:00Z",
  "zustand": "spielt",
  "lernmodus": false,
  "serie": { "id": "3f9a1c07b2d4", "name": "Der kleine Rabe" },
  "folge": { "name": "folge-02.mp3", "track": 0 },
  "akku_prozent": 76,
  "lader": false,
  "netz": "hotspot",
  "sync": {
    "zustand": "idle",
    "letzter_ende": "2026-11-05T07:00:12Z",
    "ergebnis": "ok",
    "grund": null,
    "neu": 3
  },
  "speicher_frei_mb": 5120,
  "version": "1.2.0",
  "firmware": "1.0.0",
  "protokoll": 1,
  "leser": "ok",
  "letzter_fehler": null,
  "zeitquelle": "ntp",
  "zeit_ok": true,
  "konfig": { "revision": 17, "liste_id": "a3f9c1e07b2d4856" },
  "update": { "zustand": "ok", "version": "1.2.0", "grund": null }
}
```

### 3.4 `tobibox/<box>/event` (nicht retained)

Einmalige Meldungen ohne Bestätigung.

| Feld | Typ | Bedeutung |
|---|---|---|
| `v` | int | `1` |
| `id` | string | zufällige Kennung der Meldung (UUID); HA wertet doppelte `id` einmal aus |
| `ts` | string | Zeitpunkt |
| `art` | string | `liste_abgelehnt`, `fehler` oder `befehl_abgelehnt` |
| `daten` | object | je nach `art` |

`daten` je Art:

| `art` | Felder in `daten` |
|---|---|
| `liste_abgelehnt` | `liste_id`, `revision` (der abgelehnten Liste), `gespeichert_liste_id`, `gespeichert_revision` (was die Box hat), `grund` ∈ `revision_zu_niedrig`, `schema_ungueltig`, `schema_zu_neu` |
| `fehler` | `baustein` (string), `code` (string), `text` (string). Beispiel: der Update-Rückfall nach `failed` meldet `baustein="update"`, `code="rueckfall"`, `text=<Grund>`. Codes der Box (09.11., Rev. 3.17): `baustein="kopfhoerer"`, `code="kopfhoerer_unlesbar"` (der Schaltkontakt der Buchse ist nicht lesbar; bis er es wieder ist, gilt die Kopfhörer-Grenze; einmal je Störung) und `baustein="power"`, `code="herunterfahren_fehlgeschlagen"` (das Abschalt-Kommando hat nicht gewirkt; die Box läuft weiter, `text` nennt den Grund). Weitere Codes: `v_unbekannt`, `befehl_unbekannt` (`ha`). |
| `befehl_abgelehnt` | `befehl` ∈ `lernen`, `sync`, `update`, `befehl_id`, `grund` ∈ `bedingung`, `zeit_unsicher`, optional `detail` (Texte für `detail` im Abschnitt darunter; 09.11., AP 4.8) |

Beispiel:

```json
{
  "v": 1,
  "id": "0c9b7d52-61a8-4f07-b3e4-2d8f1a6c9e10",
  "ts": "2026-11-05T09:40:00Z",
  "art": "liste_abgelehnt",
  "daten": {
    "liste_id": "a3f9c1e07b2d4856",
    "revision": 12,
    "gespeichert_liste_id": "a3f9c1e07b2d4856",
    "gespeichert_revision": 17,
    "grund": "revision_zu_niedrig"
  }
}
```

Abgelaufene Befehle (`jetzt > erzeugt + ttl_s`) erzeugen **keine** Meldung, nur
einen Protokolleintrag auf der Box (Design: „ignorieren, protokollieren“).

Die Meldungen `liste_abgelehnt`, `fehler` mit `code` `v_unbekannt` oder
`befehl_unbekannt` und `befehl_abgelehnt` veröffentlicht das Modul `ha` der Box;
die ersten drei entstehen dort selbst (Revisionsregel, Nachrichtenversion und
Befehlsname liegen außerhalb des Kerns), `befehl_abgelehnt` kommt als Befehl
`EreignisSenden` aus dem Kern (`core-interface.md`, Abschnitt 9, Punkt 9).

**HA zeigt den Grund an.** Die Integration macht aus jedem `befehl_abgelehnt`
eine Benachrichtigung im Klartext. Bei `grund="zeit_unsicher"`: „Die Box <name>
hat <Befehl> abgelehnt: ihre Uhr ist nicht vertrauenswürdig (Zeitquelle:
<zeitquelle>). Lernmodus, Sync und Update gehen wieder, sobald die Box die
Uhrzeit sicher kennt.“ Bei `grund="bedingung"`: der Text aus `detail`. Der
Sensor „Zeitquelle“ (6.2) zeigt dazu `zeit_ok`.

Beispiele für `detail` (09.11., AP 4.8; heute nur bei `befehl` = `update`, Bedingungen in `core-interface.md`, Abschnitt 9, Punkt 9): „Die Box ist nicht im Heimnetz.“, „Die Box hängt nicht am Lader.“, „Es läuft gerade ein Hörspiel.“, „Es läuft gerade ein Sync.“, „Es läuft schon ein Update.“ Es wird die erste nicht erfüllte Bedingung genannt. Bis Stufe 3b gibt es kein Update: Ein `update`-Befehl, der alle Bedingungen erfüllt, wird mit `grund="bedingung"` und `detail` „Update kommt mit Stufe 3b.“ abgelehnt (B16, 09.11.), statt still verworfen zu werden.

### 3.5 `tobibox/<box>/unknown/<uid>` (retained)

Eine unbekannte oder gelernte Kennung, die HA noch nicht bestätigt hat. Die Box
veröffentlicht sie **dauerhaft (retained)** auf einem eigenen Thema je Kennung.
Dieselbe Kennung überschreibt die vorige Nachricht (neue Zählung).

| Feld | Typ | Bedeutung |
|---|---|---|
| `v` | int | `1` |
| `uid` | string | Kennung, gleich dem Themenende |
| `art` | string | `unbekannt` oder `gelernt` |
| `zuerst` | string | Zeitstempel der ersten Meldung |
| `zuletzt` | string | Zeitstempel der letzten Meldung, ISO 8601 mit Millisekunden (`2026-11-05T09:12:03.412Z`) |
| `anzahl` | int | wie oft die Kennung gemeldet wurde |
| `zeit_ok` | bool | war die Uhrzeit bei der letzten Meldung vertrauenswürdig |
| `befehl_id` | string oder `null` | bei `gelernt` die ID des Lernbefehls |

Beispiel:

```json
{
  "v": 1,
  "uid": "e0040312345678ab",
  "art": "gelernt",
  "zuerst": "2026-11-05T09:12:03Z",
  "zuletzt": "2026-11-05T09:12:03.412Z",
  "anzahl": 1,
  "zeit_ok": true,
  "befehl_id": "6f1c0a7e-3b52-4d1a-9c58-0e2b7a41d9f3"
}
```

Der Inhalt entspricht dem Eintrag in `unknown.json` (`data-model.md`). Ein Tobie, den **beide** Boxen melden, erscheint in HA als **ein** Eintrag
(Schlüssel = Kennung).

**Leere Nachricht:** Löscht die Box die dauerhafte Nachricht (leere Nutzlast,
retained, siehe 4.1), kommt diese leere Nachricht auch bei der HA-Integration an,
die das Thema abonniert hat. Die Integration **ignoriert jede leere Nutzlast** auf
`…/unknown/<uid>`; sie ist keine Meldung und löst weder eine Aufnahme noch eine
Bestätigung aus.

### 3.6 `tobibox/<box>/unknown/<uid>/ack` (nicht retained)

Die Bestätigung von HA. Erst sie lässt die Box den Eintrag löschen. Der PUBACK
des Brokers bestätigt nichts (HA kann gerade neu starten).

| Feld | Typ | Bedeutung |
|---|---|---|
| `v` | int | `1` |
| `ts` | string | Zeitpunkt |
| `zuletzt` | string | `zuletzt` der Meldung, die HA bestätigt (aus der Nachricht auf `…/unknown/<uid>`, **unverändert** zurückgegeben, mit Millisekunden) |
| `art` | string | `art` dieser Meldung (`unbekannt` oder `gelernt`) |
| `grund` | string | `neu` (HA hat den Tobie als „neuer Tobie“ aufgenommen), `bekannt` (die Kennung war schon aufgenommen, z. B. von der anderen Box), `zugeordnet` (Lernmodus: HA hat die Zuordnung geschrieben), `abgelehnt` (HA nimmt sie nicht an, z. B. Lernbefehl abgelaufen) |

Die Box löscht den Eintrag **nur, wenn `zuletzt` und `art` mit dem aktuellen
Eintrag übereinstimmen**, dann bei **jedem** `grund`; unbekannte Gründe werden
protokolliert und wirken wie `bekannt`. Passt eine Bestätigung nicht (sie gehört
zu einer älteren Fassung, die inzwischen überschrieben wurde), tut die Box
nichts außer einem Protokolleintrag (`ack_veraltet`); der neuere Eintrag und
seine dauerhafte Nachricht bleiben stehen, und HA bestätigt sie selbst. Ein
`ack` ohne `zuletzt` (Version 1 verlangt es) wird wie eine unpassende
Bestätigung behandelt. Das Thema ist **nicht** retained, weil eine dauerhafte
Bestätigung eine spätere neue Meldung derselben Kennung sofort „bestätigen“
würde.

Beispiel:

```json
{ "v": 1, "ts": "2026-11-05T09:12:05Z", "zuletzt": "2026-11-05T09:12:03.412Z", "art": "gelernt", "grund": "zugeordnet" }
```

### 3.7 `tobibox/<box>/cmd` (nicht retained)

Befehle an genau eine Box. Sie sind **nicht dauerhaft** und tragen eine
Ablaufzeit.

| Feld | Typ | Bedeutung |
|---|---|---|
| `v` | int | `1` |
| `id` | string | zufällige Kennung des Befehls (UUID) |
| `befehl` | string | `lernen`, `lernen_abbrechen`, `sync`, `update` |
| `erzeugt` | string | Zeitpunkt, an dem HA den Befehl erzeugt hat (Wanduhr von HA) |
| `ttl_s` | int 1–3600 | Lebensdauer in Sekunden |
| `daten` | object | `{}`; bei `update` `{"version": "<MAJOR.MINOR.PATCH>"}` |

Gültigkeit: Das Modul `ha` der Box berechnet `gueltig_bis = erzeugt + ttl_s` und
gibt es mit dem Ereignis an den Kern; **der Kern** (`learn`, `idle`) prüft mit
`jetzt.wall` und `jetzt.zeit_ok` (Zuständigkeit je Prüfung: `core-interface.md`,
Abschnitt 9, Punkt 9). Er führt den Befehl nur aus, wenn `jetzt.wall ≤ gueltig_bis`
**und** die Uhr vertrauenswürdig ist (`zeit_ok`). Sonst wird er nicht ausgeführt
(abgelaufen: nur Protokoll; Uhr unsicher: zusätzlich `event` mit
`befehl_abgelehnt`, Grund `zeit_unsicher`). Ausnahme `lernen_abbrechen`: Er hat
eine Ablaufzeit, wird aber auch bei unsicherer Uhr ausgeführt (die Ablaufzeit
wird dann nicht geprüft), wird nie mit `befehl_abgelehnt` beantwortet und ist im
Zustand „Lernmodus aus“ wirkungslos.
Voreinstellungen der Integration: `lernen` 60 s, `lernen_abbrechen` 30 s,
`sync` 300 s, `update` 300 s.

Hat ein Befehl bei Ankunft die Ablaufzeit nicht erreicht, aber die Box war
offline (dauerhafte Sitzung stellt Nachrichten später zu), sorgt die
Ablaufzeit dafür, dass er verfällt. Doppelte Zustellung wird über `id`
erkannt (die Box merkt sich die letzten 50 `id`).

| `befehl` | Wirkung auf der Box |
|---|---|
| `lernen` | Ereignis `HaLernmodus`: Lernmodus beginnt, die Box misst die Frist von 2 min selbst |
| `lernen_abbrechen` | Ereignis `HaLernmodusAbbruch` |
| `sync` | Ereignis `HaSyncAnstossen` |
| `update` | Ereignis `HaUpdateAnstossen` mit `daten.version` |

Beispiel:

```json
{
  "v": 1,
  "id": "6f1c0a7e-3b52-4d1a-9c58-0e2b7a41d9f3",
  "befehl": "lernen",
  "erzeugt": "2026-11-05T09:11:50Z",
  "ttl_s": 60,
  "daten": {}
}
```

Das Ziel für das Lernen hält HA selbst (Box, Ziel, Beginn). Das Ziel ist eine
**Serie** oder eine **einzelne Folge** (Entscheidung F, 05.11.): `typ` (`serie` oder `folge`), `serie_id`,
bei `folge` zusätzlich `folge` (Name der Folge). Die Box bekommt das Ziel nicht;
sie meldet nur die Kennung, und der Inhalt des Befehls `lernen` (`daten`) bleibt
`{}`. Welches Ziel gilt, bestimmt die **HA-Aktion „Lernmodus starten“** (3.8),
nicht die Auswahl der Box.

### 3.8 `tobibox/<box>/ui/<objekt>` (nicht retained)

Eingaben der Home-Assistant-Entitäten, die die Box per Discovery anlegt
(Abschnitt 6). Ein Knopf in HA sendet eine **feste** Nutzlast und kann deshalb
keine frische Ablaufzeit tragen; darum gehen diese Themen **nicht** an die Box,
sondern an die HA-Integration. Sie setzt die Eingabe in einen Befehl auf
`tobibox/<box>/cmd` um und trägt dabei `id`, `erzeugt` und `ttl_s` ein.

| Thema | Nutzlast | Wirkung in der Integration |
|---|---|---|
| `tobibox/<box>/ui/sync` | `PRESS` | `cmd` mit `befehl="sync"` |
| `tobibox/<box>/ui/update` | `PRESS` | `cmd` mit `befehl="update"` und der neuesten Version aus `releases/` |
| `tobibox/<box>/ui/lernen_abbrechen` | `PRESS` | `cmd` mit `befehl="lernen_abbrechen"` |
| `tobibox/<box>/ui/lern_serie` | Anzeigename der gewählten Serie | merkt sich die Wahl als **Vorbelegung** des Felds „Serie“ der Aktion „Lernmodus starten“ (Auswahl ohne Rückmeldung, `optimistic`); setzt selbst keinen Befehl ab und legt nichts fest |

Den Lernmodus selbst startet Tobias über die HA-Aktion „Lernmodus starten“
(Box und Ziel), nicht über einen Knopf der Box. Die Aktion trägt das Ziel
**ausdrücklich** (Entscheidung F, 05.11.): `box`, `typ` (`serie` oder `folge`), `serie_id` und bei `folge`
zusätzlich `folge`; die Auswahl `lern_serie` füllt das Feld `serie_id` nur vor.
Typ und Folge wählt Tobias immer in der Aktion. Die Auswahl enthält nur Serien, die die Box schon synchronisiert hat; die
Aktion darf jede Serie der HA-Medienverwaltung nehmen, auch eine noch nicht
synchronisierte (dann spielt die Box die Überraschungs-Serie, bis sie da ist,
`data-model.md`, Abschnitt 2).

## 4. Abläufe

### 4.1 Unbekannter Tobie (CUJ 7a, 12)

1.  Die Box legt die Kennung in `unknown.json` (`art="unbekannt"`) und spielt die
    Überraschungs-Serie.
2.  Sobald die Verbindung steht (sofort oder später, auch nach Tagen
    offline), veröffentlicht die Box **jeden** noch offenen Eintrag auf
    `tobibox/<box>/unknown/<uid>` (retained, QoS 1).
3.  HA nimmt die Kennung als „neuer Tobie“ auf (gleiche Kennung von beiden
    Boxen = ein Eintrag) und antwortet auf `…/ack` mit `grund` `neu` oder
    `bekannt` sowie `zuletzt` und `art` der bestätigten Meldung.
4.  Passen `zuletzt` und `art` zum aktuellen Eintrag, löscht die Box auf den `ack`
    hin zuerst die dauerhafte Nachricht (leere Nutzlast, retained, QoS 1, auf
    `tobibox/<box>/unknown/<uid>`; HA ignoriert diese leere Nachricht, 3.5), und
    nach dem PUBACK dieses Löschens den Eintrag in `unknown.json`, sofern er sich
    inzwischen nicht geändert hat (sonst bleibt er und wird erneut
    veröffentlicht). Passen sie nicht, bleibt alles stehen. Stürzt die Box
    dazwischen ab, ist die Nachricht weg und der Eintrag bleibt: Er wird beim
    nächsten Verbinden erneut veröffentlicht, HA bestätigt erneut (idempotent).
5.  Kommt der `ack` nie (HA aus), bleibt der Eintrag stehen; die dauerhafte
    Nachricht wartet im Broker, bis HA sie liest.
6.  Wählt Tobias in HA den Typ (Serie oder einzelne Folge) und das Ziel, ändert
    HA die Konfiguration (Revision + 1) (Entscheidung F, 05.11.) und veröffentlicht `tobibox/config`. Die Box übernimmt die Liste, und läuft
    der Tobie noch, wechselt er auf die Serie (Kern: neues `Aufgelegt` nicht
    nötig; der Wechsel geschieht durch `KonfigGeladen`, wie im Design).

### 4.2 Lernmodus (CUJ 7b)

1.  Tobias startet in HA die Aktion „Lernmodus starten“ mit Box, Typ und Ziel
    (`typ` `serie` oder `folge`, `serie_id` und bei `folge` die `folge`
    ausdrücklich in der Aktion; die Auswahl `lern_serie` füllt die Serie nur
    vor) (Entscheidung F, 05.11.). Die Integration merkt sich Box, Ziel und Beginn und sendet auf
    `tobibox/<box>/cmd` `befehl="lernen"` (`ttl_s` 60).
2.  Die Box prüft Gültigkeit und Uhr (3.7), beginnt den Lernmodus und misst
    2 min selbst.
3.  Wird in dieser Zeit ein Tobie mit Kennung aufgelegt, meldet die Box ihn als
    `art="gelernt"` mit `befehl_id` auf `tobibox/<box>/unknown/<uid>`.
4.  HA ordnet die Kennung dem Ziel aus der Aktion zu (`ziel` `serie` oder `folge`). Ist die Kennung schon
    zugeordnet, fragt HA vor dem Überschreiben nach. Lehnt HA ab (oder fragt Tobias und er verneint), gibt es
    keine neue Konfiguration; weiter mit Schritt 6.
5.  HA veröffentlicht **zuerst** die neue Konfiguration; das Ziel spielt (die Serie an ihrem
    Zeiger, die Folge von vorn oder an ihrem Zeiger).
6.  **Danach** antwortet HA auf `…/ack` mit `grund="zugeordnet"` (oder `abgelehnt`) und
    `zuletzt`/`art` der Meldung. Die Reihenfolge Konfiguration, dann `ack` (Entscheidung H, 07.11.)
    verhindert, dass der `ack` den Eintrag löscht, bevor die Box das Ziel kennt.
    **Ablauf aus Sicht der Box (Entscheidung H, 07.11.):** Von Schritt 3 bis zur Antwort
    spielt die Box **nichts**: Beim Auflegen kommt nur der Lernton (`lernen_ende`), keine
    Überraschung und kein Ton `unbekannt`, auch nicht bei einem schon bekannten Tobie.
    Die Box wartet bis zu **10 s** (`LERN_ANTWORT_FRIST_S`, gemessen auf der
    Box) auf HA. Es gilt, was zuerst eintrifft:
    *   Eine neue Konfiguration, die diesem Tobie ein **anderes** Ziel gibt als beim
        Auflegen (ein unbekannter Tobie: überhaupt eines) (Schritt 5): das Ziel
        startet sofort. Eine andere Konfiguration (anderer Tobie geändert, gleiches Ziel für
        diesen Tobie) beendet das Warten nicht. Ein `ack` mit `grund="zugeordnet"` allein
        beendet das Warten auch nicht; HA schickt deshalb die Konfiguration **vor** dem `ack`.
    *   Der `ack` mit `grund="abgelehnt"` (Schritt 6): das Warten endet sofort. Die Box
        verhält sich wie bei einem normalen Auflegen, ein bekannter Tobie spielt sein
        Ziel, ein unbekannter die Überraschung mit dem Ton `unbekannt`. Der `ack` hat den
        Eintrag gelöscht; für einen unbekannten Tobie meldet die Box ihn danach **erneut** als
        `art="unbekannt"` (neuer Eintrag in `unknown.json`), HA sieht ihn wieder als „neuer
        Tobie“. Der `ack` zählt nur, wenn er einen offenen Eintrag mit passendem
        `zuletzt` und `art` trifft (Abschnitt 3.6); ein veraltetes oder doppeltes `ack` ändert nichts.
    *   10 s ohne Antwort: wie bei „abgelehnt“, aber ohne neue Meldung; der Eintrag bleibt als
        `gelernt` offen. Eine Aktionskarte löst jetzt ihre Aktion aus. Kommt die Konfiguration
        später doch, wechselt die Box darauf (Abschnitt 4.1, Schritt 6).
    *   Der Tobie wird abgehoben: das Warten endet, nichts spielt.
    *   **Gewollt (Rückfrage beim Überschreiben):** Muss Tobias in HA die Rückfrage aus Schritt 4
        beantworten und braucht dafür länger als 10 s, spielt ein bekannter Tobie zuerst sein
        altes Ziel. Mit der späteren Zuordnung wechselt die Box auf das neue Ziel, wie bei jeder
        Konfigurationsänderung mit liegendem Tobie. Es gibt keine Verlängerung der Frist.
    Die Meldung `gelernt` und der Eintrag in `unknown.json` bleiben unverändert; der
    `ack` löscht den Eintrag wie bisher. Hauptknopf, Vor und Zurück bewirken während des
    Wartens nichts, die Lautstärke wirkt.
7.  `lernen_abbrechen` beendet den Lernmodus jederzeit. Nach 2 min ohne Tobie
    endet er von selbst.

### 4.3 Konfiguration verteilen

1.  HA ändert die Konfiguration → `revision` + 1, gleiche `liste_id` →
    Veröffentlichung auf `tobibox/config` (retained).
2.  Jede Box wendet die **Revisionsregel** an (5.2).
3.  Angenommen: Box prüft das Schema (`data-model.md`), schreibt `config.json`
    und meldet `KonfigGeladen` an den Kern. Der Status zeigt die neue Revision.
4.  Abgelehnt: Box behält ihre Kopie und veröffentlicht `event` mit
    `art="liste_abgelehnt"`.
5.  Hat der Broker nichts, behält die Box ihre letzte Kopie.

### 4.4 Verbinden

Reihenfolge bei jedem Verbinden der Box:

1.  Verbinden mit Will `offline`.
2.  Abonnieren: `tobibox/config`, `tobibox/<box>/cmd`,
    `tobibox/<box>/unknown/+/ack`, `homeassistant/status`.
3.  `online` (retained) veröffentlichen.
4.  Discovery veröffentlichen (Abschnitt 6) und `status`.
5.  Offene Einträge aus `unknown.json` veröffentlichen.
6.  Die retained `tobibox/config` trifft ein und wird nach 5.2 behandelt.

## 5. Konfiguration: Revision und Listen-ID

### 5.1 Begriffe

*   **Revision:** Versionsnummer der Konfiguration, eine für alles (Zuordnungen,
    Leise-Zeiten, Gute-Nacht-Einstellungen). HA erhöht sie bei jeder Änderung
    um 1.
*   **Listen-ID:** zufällige Kennung des HA-Speichers (16 Zeichen `[0-9a-f]`). Sie
    ändert sich nur in diesen Fällen (Vertrag W, Abschnitt 13):
    *   **Erststart:** Es gibt weder einen Export noch eine Box, die eine `liste_id` meldet. Die
        Integration legt eine neue Liste an (Revision 1) und veröffentlicht sie (Zustand `ok`).
    *   **HA-Aktion „Liste neu ausrollen“** (`liste/neu_ausrollen`): neue Listen-ID aus dem Stand in HA.
        Das ist auch der Weg aus dem Zustand `leer_neu` (dann mit einer **leeren** Liste; die
        Seite warnt vorher).
    *   **„Aus dem Export holen“** (`konfig/aus_export`): neue Listen-ID und Revision 1.

    **Ein leerer Speicher setzt nicht von selbst eine neue Listen-ID.** Ist der HA-Speicher leer,
    obwohl es schon einmal eine Konfiguration gab (Zustand `leer_neu`), veröffentlicht die Integration
    **nichts**, bis Tobias entscheidet; ebenso nicht, wenn der Export neuer ist als der Speicher
    (Zustand `export_neuer`). Im Normalbetrieb (`ok`) bleibt die Listen-ID gleich, und HA erhöht
    nur die Revision. So überschreibt nie eine leere oder alte Liste die Zuordnungen der Boxen.

### 5.2 Regel auf der Box

Die Box vergleicht die eingehende Liste (`L_neu`, `R_neu`) mit der gespeicherten
(`L_alt`, `R_alt`; ohne Datei `""` und `0`):

| Fall | Wirkung |
|---|---|
| `L_neu ≠ L_alt` | **angenommen**, unabhängig von der Revision |
| `L_neu = L_alt` und `R_neu > R_alt` | **angenommen** |
| `L_neu = L_alt` und `R_neu = R_alt` | nichts zu tun, keine Meldung (derselbe Stand, etwa erneute Zustellung der dauerhaften Nachricht) |
| `L_neu = L_alt` und `R_neu < R_alt` | **abgelehnt**, Meldung `liste_abgelehnt` mit Grund `revision_zu_niedrig` |
| Schema ungültig (`data-model.md`) | **abgelehnt**, Grund `schema_ungueltig` |
| `schema_version` neuer als bekannt | **abgelehnt**, Grund `schema_zu_neu` |

Eine Liste der Version 1 (ohne `ziel`) nimmt die Box an und **migriert sie im
Speicher nach Version 2**, bevor sie geprüft wird (`data-model.md`, Abschnitt 2);
gespeichert wird danach Version 2 (Entscheidung F, 05.11.).

### 5.3 Folgerungen

*   Eine **HA-Wiederherstellung** mit neuer Listen-ID wird von allen Boxen
    angenommen, auch bei niedrigerer Revision.
*   Wird HA aus einer Sicherung wiederhergestellt, die die **alte** Listen-ID
    enthält, lehnen die Boxen die Liste mit niedrigerer Revision ab. Dann hilft
    die HA-Aktion „Liste neu ausrollen“ (neue Listen-ID), wie das Betriebshandbuch
    es beschreibt.
*   Die Box merkt sich nur die jeweils gespeicherte Liste, keine Historie.

## 6. Home-Assistant-Discovery (Entitäten je Box)

Die Box veröffentlicht je Entität eine retained Nachricht auf
`homeassistant/<komponente>/tobibox_<box>/<objekt>/config` (QoS 1). Sie
veröffentlicht alle Nachrichten erneut: bei jedem Verbinden, wenn
`homeassistant/status` den Text `online` meldet, wenn sich `version` oder die
Serienliste ändert (für die Auswahl).

### 6.1 Gerät

Alle Entitäten einer Box gehören zu einem Gerät:

```json
"device": {
  "identifiers": ["tobibox_box1"],
  "name": "Tobi Box box1",
  "manufacturer": "Tobi Box",
  "model": "NFC-Audiobox",
  "sw_version": "1.2.0"
}
```

`name` = `Tobi Box <anzeigename>`; `anzeigename` steht in `tobibox.toml`, Vorgabe
ist der Box-Name. Jede Entität trägt außerdem:
`"unique_id": "tobibox_<box>_<objekt>"`, `"has_entity_name": true`,
`"availability_topic": "tobibox/<box>/online"`, `"payload_available": "online"`,
`"payload_not_available": "offline"`.

### 6.2 Entitäten

Alle Sensoren lesen `tobibox/<box>/status` (`state_topic`) und werten die Felder
mit `value_template` aus.

| Komponente | `<objekt>` | Anzeigename (`name`) | Wert | Zusatz |
|---|---|---|---|---|
| `sensor` | `zustand` | Zustand | `{{ value_json.zustand }}` | |
| `sensor` | `serie` | Läuft gerade | `{{ value_json.serie.name if value_json.serie else 'keine' }}` | |
| `sensor` | `akku` | Akku | `{{ value_json.akku_prozent }}` | `device_class` `battery`, Einheit `%`, `state_class` `measurement` |
| `binary_sensor` | `lader` | Lader | `{% if value_json.lader is none %}None{% else %}{{ 'ON' if value_json.lader else 'OFF' }}{% endif %}` (bei `null` also „unbekannt“, nicht `OFF`; Home Assistant liest den Text `None` als unbekannt). Bedeutung „Strom am Eingang, jede Quelle“ (Ein/Aus, 10.11.) | `device_class` `battery_charging` |
| `sensor` | `netz` | Netz | `{{ value_json.netz }}` | `device_class` `enum`, Optionen `home`, `hotspot`, `offline` |
| `sensor` | `sync` | Sync-Stand | `{{ value_json.sync.zustand }}` | `json_attributes_topic` = Status, `json_attributes_template` `{{ value_json.sync \| tojson }}` (zeigt Zeitpunkt, Ergebnis, Grund) |
| `sensor` | `speicher_frei` | Freier Speicher | `{{ value_json.speicher_frei_mb }}` | Einheit `MB`, `device_class` `data_size`, `state_class` `measurement`; Anzeige (11.11.): `suggested_unit_of_measurement` `GB`, `suggested_display_precision` `0` (HA zeigt „445 GB“ statt „456.194,00 MB“; der gesendete Wert bleibt in MB). Hat HA die Entität schon angelegt, übernimmt es den Vorschlag nicht immer: dann einmalig in den Entitätseinstellungen die Anzeigeeinheit auf GB stellen |
| `sensor` | `version` | Version | `{{ value_json.version }}` | `entity_category` `diagnostic` |
| `sensor` | `letzter_fehler` | Letzter Fehler | `{{ value_json.letzter_fehler.text if value_json.letzter_fehler else 'kein Fehler' }}` | Attribute: Zeit |
| `sensor` | `zeitquelle` | Zeitquelle | `{{ value_json.zeitquelle }}` | Attribut `zeit_ok` (`json_attributes_template` `{{ {'zeit_ok': value_json.zeit_ok} \| tojson }}`); `entity_category` `diagnostic`. Erklärt, warum die Box Lernmodus, Sync und Update ablehnt (3.4) |
| `button` | `sync_jetzt` | Sync jetzt | – | `command_topic` `tobibox/<box>/ui/sync`, `payload_press` `PRESS` |
| `button` | `update` | Update | – | `command_topic` `tobibox/<box>/ui/update`, `payload_press` `PRESS` |
| `button` | `lernen_abbrechen` | Lernmodus abbrechen | – | `command_topic` `tobibox/<box>/ui/lernen_abbrechen`, `payload_press` `PRESS` |
| `select` | `lern_serie` | Serie für Lernmodus | – | **Vorbelegung** für die Aktion „Lernmodus starten“ (3.8), kein Befehl; Typ (Serie oder Folge) und Folge wählt Tobias in der Aktion. `options` = Anzeigenamen der Serien auf der Box (bei doppelten Namen hängt die Box ` (<id>)` an), `command_topic` `tobibox/<box>/ui/lern_serie`, `optimistic` `true` |

Beispiel der Nachricht für den Sensor „Akku“ (Thema
`homeassistant/sensor/tobibox_box1/akku/config`):

```json
{
  "name": "Akku",
  "unique_id": "tobibox_box1_akku",
  "has_entity_name": true,
  "state_topic": "tobibox/box1/status",
  "value_template": "{{ value_json.akku_prozent }}",
  "device_class": "battery",
  "unit_of_measurement": "%",
  "state_class": "measurement",
  "availability_topic": "tobibox/box1/online",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": {
    "identifiers": ["tobibox_box1"],
    "name": "Tobi Box box1",
    "manufacturer": "Tobi Box",
    "model": "NFC-Audiobox",
    "sw_version": "1.2.0"
  }
}
```

Beispiel der Nachricht für den Knopf „Sync jetzt“ (Thema
`homeassistant/button/tobibox_box1/sync_jetzt/config`):

```json
{
  "name": "Sync jetzt",
  "unique_id": "tobibox_box1_sync_jetzt",
  "has_entity_name": true,
  "command_topic": "tobibox/box1/ui/sync",
  "payload_press": "PRESS",
  "availability_topic": "tobibox/box1/online",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": { "identifiers": ["tobibox_box1"], "name": "Tobi Box box1" }
}
```

## 7. Mosquitto-Rechte je Box-Konto

Das Mosquitto-Add-on in HA (7.1.3) läuft mit `customize.active: true`. Die Box-Konten werden
unter `logins` angelegt, sind **keine** HA-Administratoren. Die Konten `homeassistant` und
`addons` bleiben unbeschränkt (`topic readwrite #`). Beispieldateien liegen in
`homeassistant/mosquitto/`.

**Zwei Dateien (09.11., Befund AP 3.1):** Das Add-on liest jede `*.conf` unter `/share/mosquitto/`
als Mosquitto-**Konfiguration**. Regeln mit `user`, `topic` oder `pattern` dürfen deshalb nicht in
einer `*.conf` stehen; Mosquitto würde sie als Konfiguration lesen und abbrechen.

*   `/share/mosquitto/acl.conf` enthält nur die eine Zeile
    `acl_file /share/mosquitto/accesscontrollist` (Vorlage `acl.conf.example`).
*   `/share/mosquitto/accesscontrollist` (**ohne** Endung) enthält alle Regeln dieses
    Abschnitts (Vorlage `accesscontrollist.example`).
*   Nach jeder Änderung das Add-on neu starten.

Rechte für das Konto `box1` (für `box2` entsprechend; ein Konto je Box):

```
user box1
topic read tobibox/config
topic read tobibox/box1/cmd
topic read tobibox/box1/unknown/+/ack
topic read homeassistant/status
topic write tobibox/box1/online
topic write tobibox/box1/status
topic write tobibox/box1/event
topic write tobibox/box1/unknown/+
topic write homeassistant/+/tobibox_box1/+/config
```

*   Die Box darf **nicht**: `tobibox/config` schreiben, `…/cmd`, `…/ack` und
    `…/ui/…` schreiben, Themen anderer Boxen lesen oder schreiben, Themen unter
    `homeassistant/` außer der eigenen Discovery schreiben.
*   `topic write tobibox/box1/unknown/+` erlaubt auch das Löschen der
    dauerhaften Nachricht (leere Nutzlast).
*   Gleichwertig ist eine einzige Regel mit `pattern` und `%u` (Benutzername =
    Box-Name):

    ```
    pattern read tobibox/%u/cmd
    pattern read tobibox/%u/unknown/+/ack
    pattern write tobibox/%u/online
    pattern write tobibox/%u/status
    pattern write tobibox/%u/event
    pattern write tobibox/%u/unknown/+
    pattern write homeassistant/+/tobibox_%u/+/config
    pattern read tobibox/config
    pattern read homeassistant/status
    ```

    Wichtig (Änderung 09.11.): Die beiden letzten Zeilen müssen `pattern` sein.
    Eine Zeile `topic …` ohne eigenes `user` rechnet Mosquitto dem zuletzt
    genannten `user` zu (oder, vor dem ersten `user`, allen anonymen
    Verbindungen). Als `topic read tobibox/config` neben den `pattern`-Zeilen
    bekamen die Boxen deshalb weder die Konfiguration noch den HA-Status.
    Belegt durch einen Test gegen Mosquitto 2.0.18. In der Form mit `user` je
    Konto (oben) steht jede `topic`-Zeile im `user`-Block des Kontos und ist
    richtig.
*   Passwörter der Box-Konten stehen nur auf der Box (`tobibox.toml`,
    gitignored) und im Add-on, nie im Repo.

## 8. Versionierung

*   Jede JSON-Nachricht hat das Feld `v`, mit den Ausnahmen aus Abschnitt 1
    (`tobibox/config` hat `schema_version`; `…/online`, `…/ui/*`,
    `homeassistant/status` und die Discovery-Nachrichten sind Text bzw. Format
    von Home Assistant). Beide Versionen sind hier `1`.
*   **Ohne Erhöhung** erlaubt: neue optionale Felder, neue `art`-Werte in
    `event`, neue Entitäten, neue `befehl`-Werte. Empfänger ignorieren
    Unbekanntes: unbekannte Felder werden ignoriert, ein unbekannter `befehl`
    wird mit `event` `art="fehler"` (`code="befehl_unbekannt"`) beantwortet und
    sonst verworfen.
*   **Erhöhung** von `v` bei: Feld entfernt oder umbenannt, Bedeutung oder
    Wertebereich geändert, neues Pflichtfeld. Ein Empfänger, der ein größeres `v`
    sieht als er kennt, verwirft die Nachricht und protokolliert sie; die Box
    meldet zusätzlich ein `event` mit `art="fehler"` (`code="v_unbekannt"`).
*   Die Themennamen ändern sich nicht innerhalb einer Hauptversion. Würde eine
    Hauptversion die Themen ändern, bekommt sie einen neuen Wurzelnamen
    (`tobibox2/…`) und läuft neben der alten, bis alle Boxen aktualisiert sind.
*   Eine Änderung dieses Vertrags geht an die Projektleitung.

## Festlegungen in diesem Vertrag (Stand 05.11.)

Das Design lässt diese Einzelheiten offen. Entschieden wurde die einfachste
stimmige Lösung. „Bestätigt (05.11.)“ heißt: von Tobias (T) oder der
Projektleitung (P) entschieden oder aus dem Goldfisch-Review übernommen
(`review-stufe0.md`). Alle anderen Punkte sind noch offen.

1.  **MQTT 3.1.1** mit dauerhafter Sitzung, Keep-Alive 30 s, Client-ID
    `tobibox-<box>`. Verzichtet wird auf MQTT 5 (die HA-Veröffentlichung kann die
    „Message Expiry“-Eigenschaft nicht setzen); die Ablaufzeit steht deshalb in
    der Nachricht (`erzeugt` + `ttl_s`).
2.  **Bestätigt (05.11., T): Ablaufzeit mit Wanduhr:** Eine Box mit unsicherer
    Uhrzeit führt Lernmodus, Sync und Update nicht aus (Sicherheit, vor allem beim
    Update), und HA zeigt den Grund (3.4). Das Design nennt nur die Ablaufzeit.
    Der Abbruch des Lernmodus ist davon ausgenommen (3.7).
3.  **Gelernte Kennungen** laufen wie unbekannte über `…/unknown/<uid>` mit
    Bestätigung (`art="gelernt"`). Das Design nennt im Themenbaum „gelernt“ unter
    `…/event`, führt aber im Abschnitt „Ereignis-Ausgang mit Bestätigung“ beide
    Meldungen über den Ausgang mit Bestätigung; dieser Vertrag folgt dem
    zweiten. `…/event` trägt nur `liste_abgelehnt`, `fehler`, `befehl_abgelehnt`.
4.  **Knöpfe und Auswahl** der Box senden an `tobibox/<box>/ui/…` und die
    Integration macht daraus `cmd` mit Ablaufzeit. Grund: Eine Discovery-
    Entität sendet eine feste Nutzlast ohne frische Zeit. Das Design legt die
    Entitäten auf der Box an; ihr `command_topic` ist hier ein anderes.
5.  **`ack` nicht retained** (sonst würde er eine spätere neue Meldung derselben
    Kennung sofort bestätigen). Die Box löscht erst die dauerhafte Nachricht,
    danach den Eintrag in `unknown.json`. **Bestätigt (05.11., P, Review-Befund 8):**
    Der `ack` trägt `zuletzt` und `art`; die Box löscht nur bei Übereinstimmung;
    HA ignoriert die leere (löschende) Nachricht auf `…/unknown/<uid>`.
6.  **`ack`-Gründe** `neu`, `bekannt`, `zugeordnet`, `abgelehnt`; die Box löscht
    bei jedem (bei passendem `zuletzt`). **Bestätigt (05.11., P):** `zuletzt`
    hat Millisekunden-Auflösung (ISO 8601 mit Millisekunden), damit zwei
    Meldungen kurz nacheinander nicht denselben Wert tragen.
7.  **Gleiche Liste (gleiche Listen-ID und gleiche Revision)** wird still
    ignoriert; das Design nennt „alles andere wird abgelehnt“, aber die
    dauerhafte Nachricht kommt bei jedem Verbinden erneut.
8.  **Status:** Felder wie in 3.3; Veröffentlichung bei Änderung (höchstens alle
    5 s) und alle 300 s; `retained`. **Bestätigt (05.11., P, Review-Befund 5):**
    Quelle je Feld und Abbildung von `leser` in `core-interface.md`, Abschnitt 12.
9.  **Befehlsarten** `lernen`, `lernen_abbrechen`, `sync`, `update` und die
    Lebensdauern 60/30/300/300 s.
10. **Box-Namen** `box1`, `box2` als Beispiel; Regel `[a-z0-9][a-z0-9_-]{1,23}`.
11. **Entitätsnamen** wie in 6.2 (deutsch, wie im Design aufgezählt). Die
    Diagnose-Kategorien für Version und Zeitquelle sind eine Zutat.
12. **Wiederholte Veröffentlichung** der Discovery bei jedem Verbinden und bei
    `homeassistant/status` = `online`.
13. **Bestätigt (05.11., P, Review-Befund 6): Der Wechsel auf die zugeordnete
    Serie** bei liegendem Tobie (CUJ 7a) wird im Kern durch `KonfigGeladen`
    ausgelöst (`core-interface.md`, Abschnitt 9, Punkt 14), auch in `pausiert`
    und `beendet`; unter „stumm“ nur mit Hinweiston.
14. **Bestätigt (05.11., P, Review-Befund 8): Lernmodus-Serie ausdrücklich.** Die
    HA-Aktion „Lernmodus starten“ trägt die Serien-ID; die Auswahl `lern_serie`
    füllt sie nur vor. **Erweitert (05.11., Entscheidung F, T):** Die Aktion
    wählt auch den Typ (`serie` oder `folge`) und bei `folge` die Folge; der
    Befehl `lernen` an die Box bleibt unverändert (`daten` = `{}`).
15. **Bestätigt (05.11., P, Review-Befund 7 und 15): Zuständigkeiten** (`ha`
    prüft `v`, Befehlsname, `id`-Dublette und die Revisionsregel; der Kern prüft
    Ablaufzeit und Uhr), vollständige Ausnahmeliste für `v`, Lader `null` wird zu
    „unbekannt“.
16. **Bestätigt (05.11., Entscheidung F, T/P): `tobibox/config` hat
    `schema_version` 2** (Zuordnung mit `ziel`: `serie`, `folge` oder `aktion`,
    `data-model.md`, Abschnitt 2). Das ist eine inkompatible Änderung; eine Box mit
    Software von vor Entscheidung F lehnt die Liste mit `schema_zu_neu` ab (5.2).
    **Entschieden (05.11., Entscheidung F):** Zuerst werden alle Boxen aktualisiert,
    dann verteilt HA Version 2 (Auflösung des Widerspruchs zu 3.1). Es stehen noch
    keine Boxen im Feld; das Betriebshandbuch (AP 3.12) nennt die Reihenfolge. Die
    Box migriert Version-1-Listen von MQTT und die gespeicherte Datei im Speicher
    (5.2).
17. **Bestätigt (09.11., P, Vorgabe 10 des Vertrags W): Tobie-Name.** `tobibox/config` darf je
    Zuordnung ein optionales Feld `name` tragen; die Box ignoriert es (3.1). Additiv,
    `schema_version` bleibt 2. Das Beispiel in 3.1 zeigt es.
