# Datenmodell und Dateien (`data-model`), Version 1

*   **Status:** Vertrag Stufe 0, Entwurf zur Prüfung durch einen Goldfisch
*   **Grundlage:** `docs/designs/box-software.md` („Datenmodell und Dateien“,
    „Update“, „Fehlersuche“, Baustein 4 „Speicher und Medien“)
*   **Gilt für:** Box-Dienst (`store`, `library`, `outbox`, `update`, `eventlog`,
    `guard.py`) und die HA-Integration (`media.py`, `store.py`, `mqtt.py`).
*   Ein AP, das ein Schema einführt oder ändert, ergänzt dieses Dokument
    (siehe Umsetzungsplan).

## 1. Allgemeine Regeln

### 1.1 Format

*   JSON, UTF-8, ohne BOM, Zeilenende `\n`, Einrückung 2 Leerzeichen, ein
    abschließender Zeilenumbruch. Schlüsselnamen sind ASCII.
*   Jede Datei hat auf oberster Ebene ein Objekt mit dem Feld
    `schema_version` (ganze Zahl, hier überall `1`) **als erstes Feld**.
*   Zeitstempel: ISO 8601 in UTC mit `Z`, auf die Sekunde
    (`2026-11-05T09:30:00Z`). Im Ereignisprotokoll mit Millisekunden
    (`2026-11-05T09:30:00.123Z`).
*   Dauern: Sekunden (`_s`), Minuten (`_min`) oder Millisekunden (`_ms`),
    immer im Feldnamen. Positionen in Sekunden als Zahl mit höchstens
    1 Nachkommastelle.
*   Kennungen (`uid`) sind kanonisch (`reader-v1.md`, Abschnitt 4). Serien-IDs
    sind Zeichenfolgen von 1 bis 64 Zeichen ohne `/` und ohne
    Steuerzeichen; erzeugte IDs bestehen aus 12 Zeichen `[0-9a-f]`.
*   Dateinamen von Folgen sind reine Dateinamen (ohne `/`, ohne `\`, nicht `.`
    oder `..`), höchstens 255 Bytes.

### 1.2 Atomares Schreiben (`store`, `guard.py`)

Jede Zustandsdatei `<name>` im Zustandsverzeichnis wird so geschrieben:

1.  Den neuen Inhalt in `<name>.tmp` schreiben (im selben Verzeichnis, damit
    dasselbe Dateisystem), Datei **`fsync`**en und schließen.
2.  Existiert `<name>` und ist lesbar: einen **harten Verweis** `<name>.bak.tmp`
    auf `<name>` anlegen und mit `os.replace` auf `<name>.bak` umbenennen. Das
    ist die vorige Fassung; `<name>` ist dabei nie weg.
3.  `os.replace("<name>.tmp", "<name>")` (atomar).
4.  Das Verzeichnis **`fsync`**en.

Folgen eines Abbruchs an jeder Stelle: `<name>` ist die alte oder die neue
Fassung, nie eine halbe. Reste (`*.tmp`, `*.bak.tmp`) löscht `store` beim Start.

### 1.3 Lesen und Rückfall auf `.bak`

Beim Start (und bei jedem Lesen) in dieser Reihenfolge:

1.  `<name>` lesen. Gültig heißt: lesbares JSON, `schema_version` bekannt
    (siehe 1.5), alle Pflichtfelder vorhanden und gültig.
2.  Sonst: die Datei in `<name>.defekt` umbenennen (eine ältere `.defekt`
    wird überschrieben), `Protokoll(ERROR, "datei_defekt")` und `<name>.bak`
    lesen. Ist sie gültig, wird sie als `<name>` zurückgeschrieben (nach 1.2) und
    benutzt.
3.  Sonst: Standardwerte (leer): `config.json` als Konfiguration ohne
    Zuordnungen (Revision 0, Listen-ID leer), `resume.json` ohne Zeiger,
    `unknown.json` ohne Einträge, `update.json` mit Zustand `ok`.
    `Protokoll(ERROR, "datei_verloren")`; der Prüfpunkt „Speicher“ meldet
    einen Fehler.
4.  Eine fehlende Datei ist kein Fehler (erster Start): Standardwerte, ohne
    Meldung.

### 1.4 Unbekannte Felder

*   **Beim Lesen werden unbekannte Felder ignoriert** (Vorwärtskompatibilität).
*   Der Schreiber einer Datei behält unbekannte Felder, die er aus der Datei
    gelesen hat, **nur bei `serie.json`** (dort schreibt die HA-Integration, die
    neue Felder kennen kann). Die Box schreibt ihre eigenen Dateien aus ihrem
    Wissen neu; unbekannte Felder gehen dort verloren. Das ist gewollt: Ein
    Update-Rückfall spielt ohnehin die gesicherten Dateien zurück.

### 1.5 `schema_version` und Migration

*   Die Version zählt nur **inkompatible** Änderungen (Feld entfernt oder
    umbenannt, Bedeutung oder Einheit geändert, Pflichtfeld neu). Ein neues
    **optionales** Feld erhöht sie nicht.
*   Eine Komponente kennt eine Menge von Versionen je Datei (hier `{1}`).
    Liest sie eine **ältere** bekannte Version, **migriert sie im Speicher**
    (Funktion `migriere_vN_nach_vN+1`, rein, mit eigenem Test) und schreibt beim
    nächsten Speichern die neue Version.
*   Eine **neuere** Version als bekannt wird nicht gelesen: Die Datei gilt als
    ungültig (1.3), `Protokoll(ERROR, "schema_zu_neu")`. Es gibt keine
    automatische Abwärtsmigration.
*   Das Update-Paket nennt in `manifest.json` die Versionen, die es schreibt
    (`schema_versionen`). Bei einem Rückfall spielt `guard.py` die gesicherten
    Zustandsdateien der alten Version zurück (`update.json`, Feld `sicherung`).
*   Schema-Änderungen sollen abwärtskompatibel sein (optionale Felder), damit
    ein Rückfall selten nötig ist.

### 1.6 Wer schreibt welche Datei

| Datei | Ort | Schreiber (einziger) | Leser | Sync |
|---|---|---|---|---|
| `config.json` | Box, Zustandsverzeichnis | Box: `ha` (über `store`), aus der angenommenen Liste von `tobibox/config`; in Stufe 2 `tobibox sim card` | `app` (lädt beim Start), `ha` | wird von HA verteilt; die Box schreibt nur die übernommene Liste |
| `resume.json` | Box, Zustandsverzeichnis | Box: `store`, auf Befehl `ZeigerSpeichern` | `app` (beim Start) | nie |
| `unknown.json` | Box, Zustandsverzeichnis | Box: `outbox` | `outbox`, `ha` | wird an HA gemeldet, nach Bestätigung gelöscht |
| `serie.json` | NAS, `medien/<ordner>/` | HA-Integration (`media.py`) | Box: `library` (nur lesen), HA | `rsync` NAS → Box |
| `manifest.json` | im Paket `tobibox-<version>.tar.gz` | `deploy/build_release.sh` | `update.py`, `guard.py` | liegt auf dem NAS (`releases/`) |
| `update.json` | Box, Zustandsverzeichnis | Box: `update.py` und `guard.py` | `update.py`, `guard.py`, `selftest`, `cli` | nie |
| Ereignisprotokoll | Pi: journald (stdout); Mac: rotierende Datei | `eventlog` | Tobias | nie |
| `export/config.json` | NAS, `tobibox/export/` | HA-Integration, nach jeder Änderung | Tobias (Wiederherstellung) | – |

*   `update.json` schreiben zwei Programme, aber nie gleichzeitig: `guard.py`
    läuft als `ExecStartPre` vor dem Dienst, `update.py` im Dienst. Beide
    benutzen das Verfahren aus 1.2 (`guard.py` mit der Standardbibliothek).
*   `export/config.json` hat dasselbe Schema wie `config.json` plus das Feld
    `exportiert_am` (Zeitstempel). Die Box liest diese Datei nicht.

### 1.7 Schreibbudget

*   `resume.json`: höchstens eine Schreibung je Pause, Folgenwechsel,
    Figurwechsel, Herunterfahren und alle 30 s während der Wiedergabe, und nur
    bei Änderung (`reader-v1`/`core-interface`). Rund 240 Schreibungen am Tag
    bei 2 h Wiedergabe.
*   `unknown.json`: eine Schreibung je neuer Meldung und je Bestätigung.
*   `config.json`: eine Schreibung je angenommener Liste.
*   `update.json`: je Start im Zustand `testing` eine Schreibung (Zähler).

## 2. `config.json`

Konfiguration von HA, mit **einer** Revision und **einer** Listen-ID. Dieselbe
Struktur ist die Nachricht auf dem Thema `tobibox/config` (`mqtt-v1.md`).

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `1` |
| `revision` | int ≥ 1 | ja | Versionsnummer der Konfiguration. HA erhöht sie bei jeder Änderung um 1. (Eine Box ohne Datei rechnet mit Revision 0.) |
| `liste_id` | string, 16 Zeichen `[0-9a-f]` | ja | Kennung des HA-Speichers. In Stufe 2 ohne HA hat die lokale Liste `0000000000000000`. |
| `erzeugt_am` | string (Zeitstempel) | nein | wann HA diese Fassung erzeugt hat (nur zur Anzeige) |
| `zuordnungen` | object | ja (darf leer sein) | Schlüssel = Kennung (kanonisch), Wert = Zuordnung |
| `zuordnungen.<uid>.typ` | `"serie"` oder `"aktion"` | ja | |
| `zuordnungen.<uid>.serie` | string | wenn `typ="serie"` | Serien-ID. Verweist die ID auf keine Serie auf der Box, spielt die Box die Überraschungs-Serie nicht, sondern gibt `TonSpielen("fehler")` aus und protokolliert (Serie fehlt noch). |
| `zuordnungen.<uid>.aktion` | `"status"` oder `"gute_nacht"` | wenn `typ="aktion"` | |
| `leise_zeiten` | object | ja | |
| `leise_zeiten.zeitzone` | string | ja | IANA-Zeitzone für `von` und `bis`, z. B. `Europe/Berlin` |
| `leise_zeiten.fenster` | array | ja (darf leer sein) | beliebig viele, höchstens 32 |
| `fenster[].id` | string, 1–32 Zeichen `[a-z0-9_-]` | ja | eindeutig in der Liste |
| `fenster[].tage` | array von int 1–7 | ja | ISO-Wochentage (1 Montag bis 7 Sonntag), nicht leer, ohne Doppelte. Das Fenster gehört zu dem Tag, an dem es **beginnt**. |
| `fenster[].von` | string `HH:MM` | ja | Beginn, Ortszeit, 24 Stunden |
| `fenster[].bis` | string `HH:MM` | ja | Ende (ausschließlich), Ortszeit. `bis` ≤ `von` heißt: das Fenster reicht über Mitternacht in den nächsten Tag. `bis` = `von` ist ungültig. |
| `fenster[].wirkung` | `"leiser"` oder `"stumm"` | ja | |
| `fenster[].grenze` | int 0–100 | bei `leiser` ja | Lautstärke-Grenze in Prozent. Bei `stumm` fehlt das Feld oder ist `null`. |
| `gute_nacht` | object | ja | |
| `gute_nacht.timer_min` | int 1–240 | ja | Dauer des Timers (Vorschlag 30) |
| `gute_nacht.ausblenden_s` | int 5–600 | ja | Dauer des Ausblendens (Vorschlag 60) |

Regeln:

*   **Gültigkeit:** Ist irgendein Teil ungültig (Wertebereich, doppelte `id`,
    Kennung nicht kanonisch, unbekannter `typ`), wird die **ganze Liste**
    abgelehnt (Grund `schema_ungueltig`). Die Box behält ihre bisherige
    Konfiguration.
*   **Annahme (Revisionsregel):** Die Box nimmt eine Liste an, wenn ihre
    `liste_id` von der gespeicherten abweicht, oder wenn sie gleich ist und die
    `revision` **höher** ist. Gleiche `liste_id` und gleiche `revision`: nichts
    zu tun, keine Meldung. Gleiche `liste_id` und niedrigere `revision`: abgelehnt
    (Grund `revision_zu_niedrig`). Einzelheiten und Meldungen: `mqtt-v1.md`.
*   **Wirkung der Fenster (für `quiet`):** Ein Fenster ist **aktiv** zur Ortszeit
    `t`, wenn es einen Tag `d` gibt, dessen Wochentag in `tage` steht und für den
    `d+von ≤ t < d+bis` gilt (bei Fenstern über Mitternacht endet es am Tag
    nach `d`). Sind mehrere Fenster aktiv: gibt es ein „stumm“-Fenster, gilt
    **stumm**; sonst gilt **leiser** mit dem **kleinsten** `grenze`; sonst ist
    nichts aktiv. Die Sommerzeit-Umstellung folgt der Ortszeit (ein Fenster
    „19:30 bis 07:00“ ist in der Umstellungsnacht entsprechend länger oder kürzer).
*   **Nicht vertrauenswürdige Zeit** (`Jetzt.zeit_ok = False`): es gilt die
    kleinste `grenze` aller „leiser“-Fenster der Liste, nie stumm; gibt es kein
    „leiser“-Fenster, gilt die normale Grenze.
*   Überraschungs-Serie und gesperrte Figuren stehen nicht in `zuordnungen`.

Beispiel:

```json
{
  "schema_version": 1,
  "revision": 17,
  "liste_id": "a3f9c1e07b2d4856",
  "erzeugt_am": "2026-11-05T09:30:00Z",
  "zuordnungen": {
    "e0040312345678ab": { "typ": "serie", "serie": "3f9a1c07b2d4" },
    "04a1b2c3": { "typ": "serie", "serie": "8c21d5e9a0b7" },
    "04ffeedd": { "typ": "aktion", "aktion": "status" },
    "04112233445566": { "typ": "aktion", "aktion": "gute_nacht" }
  },
  "leise_zeiten": {
    "zeitzone": "Europe/Berlin",
    "fenster": [
      {
        "id": "abend",
        "tage": [1, 2, 3, 4, 5, 6, 7],
        "von": "19:30",
        "bis": "21:00",
        "wirkung": "leiser",
        "grenze": 25
      },
      {
        "id": "nacht",
        "tage": [1, 2, 3, 4, 5, 6, 7],
        "von": "21:00",
        "bis": "06:30",
        "wirkung": "stumm"
      }
    ]
  },
  "gute_nacht": { "timer_min": 30, "ausblenden_s": 60 }
}
```

## 3. `resume.json`

Der Zeiger je Serie. Nur die Box schreibt und liest sie; sie wird nie
synchronisiert.

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `1` |
| `serien` | object | ja (darf leer sein) | Schlüssel = Serien-ID |
| `serien.<id>.folge` | string | ja | Dateiname der aktuellen Folge (nur der Name) |
| `serien.<id>.index` | int ≥ 0 | ja | Nummer der Folge in der Reihenfolge der Serie, ab 0; Hinweis für den Fall, dass die Datei fehlt |
| `serien.<id>.position_s` | number ≥ 0 | ja | Position in Sekunden, **ohne** den Rücksprung von 3 s (den rechnet die Box beim Abspielen). 0 heißt: Folge beginnt vorn (z. B. nach einem Folgenende). |
| `serien.<id>.zaehler` | int ≥ 1 | ja | Anzahl der Schreibungen dieses Zeigers; wird bei jedem Speichern um 1 erhöht. Dient der Fehlersuche und der Kontrolle des Schreibbudgets. |

Regeln der Zeiger (Folgenende, fehlende Folge, Rücksprung): siehe
`core-interface.md`, Abschnitt 6.3. Ein Eintrag für eine Serie, die es nicht
mehr gibt, bleibt stehen und schadet nicht.

Beispiel:

```json
{
  "schema_version": 1,
  "serien": {
    "3f9a1c07b2d4": {
      "folge": "folge-02.mp3",
      "index": 1,
      "position_s": 412.5,
      "zaehler": 37
    },
    "8c21d5e9a0b7": {
      "folge": "folge-01.mp3",
      "index": 0,
      "position_s": 0.0,
      "zaehler": 3
    }
  }
}
```

## 4. `unknown.json`

Der Ereignis-Ausgang der Box (`outbox`): Kennungen, die HA noch nicht bestätigt
hat. Ein Eintrag wird **erst** gelöscht, wenn HA auf dem Thema `…/ack`
bestätigt hat (nicht schon beim PUBACK des Brokers).

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `1` |
| `eintraege` | object | ja (darf leer sein) | Schlüssel = Kennung (kanonisch); höchstens ein Eintrag je Kennung |
| `eintraege.<uid>.art` | `"unbekannt"` oder `"gelernt"` | ja | `gelernt`: im Lernmodus aufgelegt. `gelernt` ersetzt `unbekannt`, nie umgekehrt. |
| `eintraege.<uid>.zuerst` | string (Zeitstempel) | ja | erste Meldung |
| `eintraege.<uid>.zuletzt` | string (Zeitstempel) | ja | letzte Meldung |
| `eintraege.<uid>.anzahl` | int ≥ 1 | ja | wie oft die Kennung gemeldet wurde |
| `eintraege.<uid>.zeit_ok` | bool | ja | war die Uhrzeit bei der **letzten** Meldung vertrauenswürdig? Bei `false` sind `zuerst` und `zuletzt` mit Vorsicht zu lesen. |
| `eintraege.<uid>.befehl_id` | string oder `null` | ja | bei `gelernt` die ID des Lernbefehls aus `tobibox/<box>/cmd`, sonst `null` |

*   Höchstens **200** Einträge. Kommt ein 201. hinzu, wird der mit dem ältesten
    `zuletzt` verworfen und das protokolliert.
*   Beim Start veröffentlicht `ha` alle Einträge erneut, sobald die Verbindung
    steht (der Broker kennt sie als dauerhafte Nachrichten, doppelte schaden nicht).

Beispiel:

```json
{
  "schema_version": 1,
  "eintraege": {
    "04a1b2c3": {
      "art": "unbekannt",
      "zuerst": "2026-11-04T16:02:11Z",
      "zuletzt": "2026-11-05T08:15:40Z",
      "anzahl": 3,
      "zeit_ok": true,
      "befehl_id": null
    },
    "e0040312345678ab": {
      "art": "gelernt",
      "zuerst": "2026-11-05T09:12:03Z",
      "zuletzt": "2026-11-05T09:12:03Z",
      "anzahl": 1,
      "zeit_ok": true,
      "befehl_id": "6f1c0a7e-3b52-4d1a-9c58-0e2b7a41d9f3"
    }
  }
}
```

## 5. `serie.json`

Liegt in jedem Serien-Ordner auf dem NAS (`medien/<ordner>/serie.json`). Die
HA-Integration legt sie an und pflegt sie; die Boxen lesen sie nur.

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `1` |
| `id` | string | ja | Serien-ID: zufällig erzeugt, **unveränderlich**, 12 Zeichen `[0-9a-f]` |
| `name` | string, 1–100 Zeichen | ja | Anzeigename |
| `typ` | `"normal"` oder `"ueberraschung"` | ja | Die Überraschungs-Serie ist **nur** daran erkennbar; es gibt keine feste ID. |
| `folgen` | array von string | ja (darf leer sein) | Dateinamen in der maßgeblichen Reihenfolge |
| `angelegt_am` | string (Zeitstempel) | ja | Anlegezeit. Bei doppelter `id` entscheidet das spätere `angelegt_am` (jüngere Kopie bekommt eine neue ID). |

Regeln (aus dem Design, hier zusammengefasst):

*   **Reihenfolge:** Die Liste `folgen` ist maßgeblich. Dateien im Ordner, die
    nicht in der Liste stehen, spielt die Box erst, wenn die Integration sie
    eingetragen hat. Namen in der Liste, die im Ordner fehlen, werden von der
    Box übersprungen. Doppelte Namen in der Liste zählen einmal (erster
    Treffer).
*   **Ordner ohne `serie.json`:** Die Box spielt ihn trotzdem. ID = Ordnername,
    `name` = Ordnername, `typ` = `normal`, Reihenfolge = natürliche Sortierung
    der Dateinamen.
*   **Ungültige `serie.json`:** behandelt die Box wie eine fehlende; die Datei
    wird nicht repariert, aber protokolliert. (Die Integration repariert sie.)
*   **Überraschungs-Serie:** genau eine Serie mit `typ="ueberraschung"`. Keine,
    mehr als eine oder eine leere: Fehlerton und Protokoll.
*   Die Integration schreibt `serie.json` atomar (Verfahren 1.2 ohne `.bak`:
    auf dem NAS genügen `.tmp`, `fsync`, umbenennen) und behält unbekannte
    Felder (1.4).

Beispiel (normale Serie):

```json
{
  "schema_version": 1,
  "id": "3f9a1c07b2d4",
  "name": "Der kleine Rabe",
  "typ": "normal",
  "folgen": ["folge-01.mp3", "folge-02.mp3", "folge-03.mp3"],
  "angelegt_am": "2026-11-05T09:00:00Z"
}
```

Beispiel (Überraschungs-Serie):

```json
{
  "schema_version": 1,
  "id": "c07d2e91a45b",
  "name": "Überraschung",
  "typ": "ueberraschung",
  "folgen": ["ton-01.mp3", "ton-02.mp3"],
  "angelegt_am": "2026-11-05T09:05:00Z"
}
```

## 6. `manifest.json` (Update-Paket)

Liegt im Wurzelverzeichnis des Pakets `tobibox-<version>.tar.gz`. Neben dem
Paket liegt die Signatur `tobibox-<version>.tar.gz.minisig` (`minisign`).

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `1` |
| `version` | string `MAJOR.MINOR.PATCH` | ja | Version dieses Pakets (der Dienst `tobibox`) |
| `protokoll_version` | int ≥ 1 | ja | Hauptversion des Leser-Protokolls, die dieser Dienst erwartet (`reader-v1.md`, Abschnitt 13) |
| `schema_versionen` | object | ja | Version je Zustandsdatei, die dieses Paket schreibt: Schlüssel `config`, `resume`, `unknown`, `serie`, `update`; Wert int |
| `firmware_min` | string `MAJOR.MINOR.PATCH` | ja | kleinste Firmware-Version des Lesers (`fw` im `HELLO`), mit der der Selbsttest besteht |
| `python` | string `MAJOR.MINOR` | ja | Python-Version, mit der die Abhängigkeiten gebaut wurden (`3.11`) |
| `erstellt_am` | string (Zeitstempel) | ja | Bauzeit |

Die Box prüft vor dem Entpacken: Signatur gültig; `schema_version` bekannt;
`python` gleich der Version auf der Box. Danach prüft der Selbsttest
`protokoll_version` gegen das `HELLO` und `firmware_min` gegen `fw`.

Beispiel:

```json
{
  "schema_version": 1,
  "version": "1.2.0",
  "protokoll_version": 1,
  "schema_versionen": {
    "config": 1,
    "resume": 1,
    "unknown": 1,
    "serie": 1,
    "update": 1
  },
  "firmware_min": "1.0.0",
  "python": "3.11",
  "erstellt_am": "2026-11-05T12:00:00Z"
}
```

## 7. `update.json` (Zustand des Updates)

Im Zustandsverzeichnis. Fehlt die Datei, gilt Zustand `ok` ohne Zähler.

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `1` |
| `zustand` | `"ok"`, `"testing"` oder `"failed"` | ja | `testing`: neue Version ist umgeschaltet, Selbsttest steht aus. `ok`: Selbsttest bestanden (oder kein Update im Gang). `failed`: Rückfall wurde ausgeführt. |
| `version` | string | ja | laufende (bzw. zu testende) Version |
| `vorige_version` | string oder `null` | ja | die Version, auf die ein Rückfall zurückgeht |
| `zaehler` | int ≥ 0 | ja | Starts im Zustand `testing`. `update.py` setzt ihn auf 0, `guard.py` zählt ihn bei jedem Start im Zustand `testing` um 1 hoch. Bei Zähler ≥ 3 greift der Rückfall. In den Zuständen `ok` und `failed` wird nicht gezählt. |
| `gestartet_am` | string (Zeitstempel) oder `null` | ja | wann das Update umgeschaltet wurde |
| `grund` | string oder `null` | ja | bei `failed` der Grund (z. B. `selftest_durchgefallen`, `start_fehler`, `signatur_ungueltig`); sonst `null` |
| `sicherung` | string oder `null` | ja | Name des Unterordners `sicherung/` im Zustandsverzeichnis mit den gesicherten Zustandsdateien (`config.json`, `resume.json`, `unknown.json`, jeweils samt `.bak`); `null`, wenn keine Sicherung besteht |
| `gemeldet` | bool | ja | hat der Dienst das Ergebnis schon an HA gemeldet? `guard.py` setzt bei `failed` `false`; der Dienst meldet beim nächsten Start und setzt `true`. |

Beispiel (Update läuft, Selbsttest steht aus):

```json
{
  "schema_version": 1,
  "zustand": "testing",
  "version": "1.2.0",
  "vorige_version": "1.1.0",
  "zaehler": 1,
  "gestartet_am": "2026-11-05T12:10:00Z",
  "grund": null,
  "sicherung": "1.1.0",
  "gemeldet": false
}
```

## 8. Zeile des Ereignisprotokolls

Eine JSON-Zeile je Ereignis, `\n`-terminiert, ohne Einrückung. Pi: nach stdout
(journald); Mac: rotierende Datei. Schreiber ist ausschließlich `eventlog`.
Keine Geheimnisse (kein Passwort, kein MQTT-Zugang, kein Schlüssel) im Protokoll.

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `zeit` | string | ja | Wanduhr, UTC, mit Millisekunden |
| `mono` | number | ja | monotone Uhr in Sekunden mit 3 Nachkommastellen (für Latenzmessungen; unabhängig von Zeitsprüngen) |
| `zeitquelle` | `"system"`, `"rtc"`, `"ntp"` oder `"unbekannt"` | ja | woher `zeit` stammt (so erkennt man falsche Zeiten nach einem Stromausfall) |
| `ebene` | `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"` | ja | |
| `baustein` | string | ja | Modul: `reader`, `session`, `learn`, `quiet`, `bedtime`, `idle`, `core`, `player`, `store`, `library`, `outbox`, `ha`, `sync`, `update`, `selftest`, `net`, `power`, `app`, … |
| `ereignis` | string | ja | kurzer Name in `snake_case`, z. B. `aufgelegt`, `entprellt`, `zugeordnet`, `spielt`, `abgehoben`, `zeiger_gespeichert`, `seq_gap` |
| `ergebnis` | string | ja | z. B. `ok`, `fehler`, `ignoriert`, `abgelehnt` |
| `vorgang` | string (8 Zeichen `[0-9a-f]`) | nein | Vorgangs-ID des Auflegens; steht in jeder Zeile dieses Auflegens |
| `sim` | bool | nein | nur vorhanden und `true` bei simulierten Ereignissen |
| `meldung` | string | nein | kurzer Text für Menschen |
| `daten` | object | nein | weitere Felder des Ereignisses (`uid`, `serie`, `seq`, `position_s`, `code`, …); Werte sind Zahlen, Texte, Wahrheitswerte oder `null` |

Die Kette für CUJ 1 (gelesen → entprellt → zugeordnet → spielt) besteht aus
mindestens vier Zeilen mit derselben `vorgang`.

Beispiel (eine Zeile, hier der Lesbarkeit halber umbrochen):

```json
{"zeit":"2026-11-05T09:30:00.123Z","mono":1234.567,"zeitquelle":"ntp","ebene":"INFO","baustein":"session","ereignis":"spielt","ergebnis":"ok","vorgang":"a1b2c3d4","daten":{"uid":"e0040312345678ab","serie":"3f9a1c07b2d4","folge":"folge-02.mp3","position_s":409.5}}
```

Beispiel (simuliertes Ereignis):

```json
{"zeit":"2026-11-05T09:31:10.000Z","mono":1304.444,"zeitquelle":"system","ebene":"INFO","baustein":"learn","ereignis":"lernmodus_beginnt","ergebnis":"ok","sim":true,"daten":{"befehl_id":"6f1c0a7e-3b52-4d1a-9c58-0e2b7a41d9f3"}}
```

Obergrenze des Protokolls: Pi: journald mit begrenztem Platz; Mac: bis zu
5 Dateien zu je 1 MB (Vorschlag aus dem Design, im Pi-Probelauf geprüft).

## Festlegungen in diesem Vertrag (bitte bestätigen)

Das Design lässt diese Einzelheiten offen. Entschieden wurde die einfachste
stimmige Lösung.

1.  **Zusatzfeld `index`** in `resume.json`: Es macht die Regel „nächste
    vorhandene Folge“ für eine gelöschte oder umbenannte Datei bestimmt
    (die Folge, die jetzt am alten Platz steht; hinter dem Ende Folge 1).
2.  **`zaehler` je Serie** (nicht je Datei): zählt die Schreibungen des Zeigers.
3.  **Atomares Schreiben mit hartem Verweis** für `.bak` (1.2), `.defekt` für
    eine ungültige Datei, Löschen der `.tmp`-Reste beim Start. Das Design nennt
    „temporäre Datei → fsync → umbenennen“ und „Rückfall auf `.bak`“, nicht die
    Einzelheiten.
4.  **Unbekannte Felder** werden nur bei `serie.json` beim Schreiben erhalten.
5.  **Migration** im Speicher beim Lesen, neuere Version gilt als ungültig; keine
    Abwärtsmigration. Eine Änderung, die nur optionale Felder ergänzt, erhöht
    `schema_version` nicht.
6.  **Ortszeit für Leise-Zeiten:** Das Feld `leise_zeiten.zeitzone` (IANA-Name)
    gehört zur Liste. Das Design nennt keine Zeitzone. Wochentage als
    ISO-Zahlen 1 bis 7; Fenster über Mitternacht (`bis` ≤ `von`) gehören zum
    Tag des Beginns; mehrere aktive Fenster: „stumm“ gewinnt, bei „leiser“ die
    kleinste Grenze.
7.  **Wertebereiche:** `timer_min` 1–240, `ausblenden_s` 5–600, höchstens 32
    Fenster, `grenze` 0–100, Listen-ID 16 Zeichen `[0-9a-f]`, Serien-ID 12
    Zeichen `[0-9a-f]` (erzeugt).
8.  **Gleiche `liste_id` und gleiche `revision`:** keine Wirkung und keine
    Meldung (das Design nennt nur „höher“ oder „neue Listen-ID“; bei jedem
    Wiederverbinden liefert der Broker die dauerhafte Nachricht erneut).
9.  **Ganze Liste abgelehnt** bei jedem Fehler in der Konfiguration, nicht nur
    der betroffene Eintrag.
10. **`unknown.json`** enthält neben `unbekannt` auch `gelernt` (das Design führt
    beide Meldungen über den Ereignis-Ausgang); höchstens 200 Einträge.
11. **`update.json`:** Felder `vorige_version`, `gestartet_am`, `grund`,
    `sicherung`, `gemeldet` sind Zutat dieses Vertrags (das Design nennt nur
    Zustand und Zähler). Sicherung der Zustandsdateien im Unterordner
    `sicherung/<version>` des Zustandsverzeichnisses.
12. **Ereignisprotokoll:** Felder `mono` und `daten`, `ebene`, `meldung` sind
    Zutat; Namen der Felder deutsch wie im Design („Zeit, Zeitquelle,
    Baustein, Ereignis, Ergebnis“, „Vorgangs-ID“).
13. **Exportdatei** `export/config.json` hat das Schema von `config.json` plus
    `exportiert_am` (das Design verlangt eine Exportdatei, nennt aber das Format
    nicht).
14. **Verweist eine Zuordnung auf eine Serie, die auf der Box fehlt:** Fehlerton
    und Protokoll, nicht die Überraschungs-Serie.
