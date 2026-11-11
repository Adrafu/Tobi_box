# Datenmodell und Dateien (`data-model`), Version 1

*   **Status:** Vertrag Stufe 0, Entwurf zur Prüfung durch einen Goldfisch
*   **Grundlage:** `docs/designs/box-software.md` („Datenmodell und Dateien“,
    „Update“, „Fehlersuche“, Baustein 4 „Speicher und Medien“)
*   **Gilt für:** Box-Dienst (`store`, `library`, `outbox`, `update`, `eventlog`,
    `guard.py`) und die HA-Integration (`media.py`, `store.py`, `mqtt.py`).
*   Ein AP, das ein Schema einführt oder ändert, ergänzt dieses Dokument
    (siehe Umsetzungsplan).
*   **Änderung 05.11. (Entscheidung F, 05.11.):** Tobies zeigen auf eine Serie, eine
    einzelne Folge oder eine Aktion (`ziel`); eine Folge ist eine Datei oder ein
    Ordner mit mehreren Tracks; der Zeiger hat einen Track. `config.json` und
    `resume.json` haben deshalb `schema_version` 2. Im Code heißt ein Tobie aus
    historischen Gründen `figur`.
*   **Änderung 11.11. (Entscheidung Z, 11.11.):** Neue Tondatei `box/sounds/akku_warnung.wav` (Piepser) und `box/sounds/sprache/akku_warnung.wav`
    (Sprache: „Mein Akku wird leer. Bitte bald laden.“), beide −18 LUFS, Einträge in `box/lautheit.json`. Pegel eines gewöhnlichen Tons; unter „stumm“ spielt `hinweis`.
*   **Änderung 10.11. (Entscheidung R, 10.11.):** Neue Tondatei `box/sounds/gute_nacht.wav` (Piepser) und `box/sounds/sprache/gute_nacht.wav`
    (Sprache: „Gute Nacht! Ich spiele noch ein bisschen.“), beide −18 LUFS, Einträge in `box/lautheit.json`. Der Ton hat den Pegel eines gewöhnlichen
    Tons (`ton_pegel` und `hinweis_pegel` gelten nicht für ihn); unter „leiser“ gilt die Grenze, unter „stumm“ spielt er nicht
    (`core-interface.md`, Regel 6.2.2b). Kein Feld in `config.json`, `resume.json` oder `lauf.json` ändert sich.
*   **Änderung 10.11. (Ein/Aus, 10.11.; Schritt 1; alles additiv, `schema_version` bleibt):** Neue flüchtige Datei `/run/tobibox/fruehton`
    (Marke für den frühen Start-Ton, Abschnitt 1.6; Text, kein JSON, kein `schema_version`). Neue Tondatei
    `box/sounds/lader.wav`; `hinweis_pegel` gilt auch für den Ton `lader`, und der frühe Start-Ton hat den Pegel eines gewöhnlichen
    Tons (Abschnitt 2, Zeile `hinweis_pegel`). Kein Feld in `config.json`, `resume.json` oder `lauf.json` ändert sich.
*   **Änderung 09.11. (Entscheidung J, 09.11.; nachgezogen mit Entscheidung L, 09.11.):** `ton_pegel` hat
    keine Wirkung mehr; `hinweis_pegel` hat die Untergrenze 10 statt 5 (Tabelle in Abschnitt 3,
    Punkt 20 der Festlegungen). Entscheidung L (nie zwei Sachen gleichzeitig) ändert kein Schema. Nach dem Code-Review (09.11.): Die Grenze
    gewinnt immer, auch für den Hinweiston (Zeile `hinweis_pegel`, Abschnitt 3).

*   **Änderung 09.11. (Vertrag W, Entscheidung M, 09.11.; alles additiv, `schema_version` bleibt):**
    Optionales Feld `name` je Zuordnung in `config.json` (Tobie-Name, die Box ignoriert
    es); optionale Felder `pruefen`, `pruefen_gruende` und `folgen_info` in `serie.json`
    (Anzeigenamen, Folgen-Nummer, Erscheinungsdatum, „bitte prüfen“); reservierte
    Ordnernamen in `medien/`; neuer Abschnitt 9 (Papierkorb-Eintrag `meta.json`) und
    Abschnitt 10 (Eingang `eingang/`). Die Box-Software ändert sich dadurch nicht.

*   **Änderung 09.11. (Entscheidung N, 09.11.; alles additiv, `schema_version` bleibt):**
    Lesezeichen je Tobie mit Ablauf. `config.json` bekommt das optionale Feld `lesezeichen_tage`
    (ganze Zahl 0 bis 365, Vorgabe 14, `0` = läuft nie ab); `resume.json` bekommt je Zeiger das
    optionale Feld `benutzt_am` (Zeitstempel der letzten Benutzung). Ein Zeiger ohne `benutzt_am`
    läuft nie ab. Die Regeln stehen in `core-interface.md`, Abschnitt 6.3.

## 1. Allgemeine Regeln

### 1.1 Format

*   JSON, UTF-8, ohne BOM, Zeilenende `\n`, Einrückung 2 Leerzeichen, ein
    abschließender Zeilenumbruch. Schlüsselnamen sind ASCII.
*   Jede Datei hat auf oberster Ebene ein Objekt mit dem Feld
    `schema_version` (ganze Zahl; `config.json` und `resume.json`: `2`, alle anderen
    Dateien: `1` (Entscheidung F, 05.11.)) **als erstes Feld**.
*   Zeitstempel: ISO 8601 in UTC mit `Z`, auf die Sekunde
    (`2026-11-05T09:30:00Z`). Im Ereignisprotokoll mit Millisekunden
    (`2026-11-05T09:30:00.123Z`).
*   Dauern: Sekunden (`_s`), Minuten (`_min`) oder Millisekunden (`_ms`),
    immer im Feldnamen. Positionen in Sekunden als Zahl mit höchstens
    1 Nachkommastelle.
*   Kennungen (`uid`) sind kanonisch (`reader-v1.md`, Abschnitt 4). Serien-IDs
    sind Zeichenfolgen von 1 bis 64 Zeichen ohne `/` und ohne
    Steuerzeichen; erzeugte IDs bestehen aus 12 Zeichen `[0-9a-f]`. Ausnahme:
    Für einen Ordner, der keine `serie.json` hatte, ist die ID der Ordnername
    (Abschnitt 5).
*   Namen von Folgen sind reine Namen (ohne `/`, ohne `\`, nicht `.` oder
    `..`), höchstens 255 Bytes: der Dateiname einer Folge aus einer Datei, der
    Ordnername einer Folge aus mehreren Tracks (Entscheidung F, 05.11.). Dasselbe gilt für die Namen der
    Tracks in einem Folgen-Ordner.

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
4.  Fehlt `<name>`, aber es gibt eine gültige `<name>.bak` (Abbruch zwischen
    den Schritten, Datei von Hand gelöscht), gilt `<name>.bak`: sie wird als
    `<name>` zurückgeschrieben, `Protokoll(WARNING, "datei_aus_bak")`. Nur wenn
    **beide** Dateien fehlen, ist es der erste Start (kein Fehler): Standardwerte,
    ohne Meldung. Beim Umbenennen nach `.defekt` wird das Verzeichnis
    `fsync`t, und `<name>.bak` wird vor dem Umbenennen gelesen.

### 1.4 Unbekannte Felder

*   **Beim Lesen werden unbekannte Felder ignoriert** (Vorwärtskompatibilität).
*   Der Schreiber einer Datei behält unbekannte Felder, die er aus der Datei
    gelesen hat, **nur bei `serie.json`** (dort schreibt die HA-Integration, die
    neue Felder kennen kann). Die Box schreibt ihre eigenen Dateien aus ihrem
    Wissen neu; unbekannte Felder gehen dort verloren. Das ist gewollt: Ein
    Update-Rückfall spielt ohnehin die gesicherten Dateien zurück. Beispiel (09.11.): Das
    Feld `name` einer Zuordnung liest die Box nicht (Prüfung und Wirkung hängen nur an `ziel`).
    **Ausnahme `config.json` (09.11., Befund AP 3.7):** Beim Umschreiben der Konfiguration
    **erhält** die Box `name`, unbekannte Zusatzfelder je Zuordnung und `lesezeichen_tage`
    (`sim card`, HA-Ersatz, Übernahme aus MQTT). `schreibe_zuordnung` ändert nur `ziel`.
    Der Name bleibt außerdem in HA (Speicher und Export) erhalten.

### 1.5 `schema_version` und Migration

*   Die Version zählt nur **inkompatible** Änderungen (Feld entfernt oder
    umbenannt, Bedeutung oder Einheit geändert, Pflichtfeld neu). Ein neues
    **optionales** Feld erhöht sie nicht.
*   Eine Komponente kennt eine Menge von Versionen je Datei (hier `{1}`, für
    `config.json` und `resume.json` `{1, 2}` (Entscheidung F, 05.11.)).
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
| `lauf.json` | Box, Zustandsverzeichnis | Box: `app` (einfaches Schreiben) (Entscheidung G, 06.11.) | `app` (beim Start) | nie |
| `fruehton` | Box, **flüchtig**: `/run/tobibox/fruehton` (tmpfs, bei jedem Einschalten leer) (Ein/Aus, 10.11.) | Frühdienst `tobibox-fruehton.service` (`fruehton.py`) und `app` (Gegenmarke `uebernommen`); `app` löscht die Marke des Frühdienstes | `app` (bei `Bereit`) | nie |
| `unknown.json` | Box, Zustandsverzeichnis | Box: `outbox` | `outbox`, `ha` | wird an HA gemeldet, nach Bestätigung gelöscht |
| `serie.json` | NAS, `medien/<ordner>/` | HA-Integration (`media.py`) | Box: `library` (nur lesen), HA | `rsync` NAS → Box |
| `manifest.json` | im Paket `tobibox-<version>.tar.gz` | `deploy/build_release.sh` | `update.py`, `guard.py` | liegt auf dem NAS (`releases/`) |
| `update.json` | Box, Zustandsverzeichnis | Box: `update.py` und `guard.py` | `update.py`, `guard.py`, `selftest`, `cli` | nie |
| Ereignisprotokoll | Pi: journald (stdout); Mac: rotierende Datei | `eventlog` | Tobias | nie |
| `export/config.json` | NAS, `tobibox/export/` | HA-Integration, nach jeder Änderung (nach dem Veröffentlichen, im Hintergrund) | Tobias, HA (`konfig/export_lesen`, `konfig/aus_export`) | – |
| `_papierkorb/<id>/meta.json` | NAS, `medien/_papierkorb/` | HA-Integration (`media.py`) | HA-Integration | **nie** (vom Sync ausgenommen) |
| Eingang | NAS, `tobibox/eingang/` (neben `medien/`) | Tobias (PC, Dateimanager) und HA (Upload, Einsortieren) | HA-Integration (`eingang.py`) | **nie** (liegt außerhalb des Sync-Moduls und ist ausdrücklich ausgenommen) |

*   `update.json` schreiben zwei Programme, aber nie gleichzeitig: `guard.py`
    läuft als `ExecStartPre` vor dem Dienst, `update.py` im Dienst. Beide
    benutzen das Verfahren aus 1.2 (`guard.py` mit der Standardbibliothek).
*   `export/config.json` hat dasselbe Schema wie `config.json` plus das Feld
    `exportiert_am` (Zeitstempel). Die Box liest diese Datei nicht.

**`fruehton` (Ein/Aus, 10.11.):** Eine Textdatei mit **genau einem** Wort und einem `\n`. Wörter des Frühdienstes: `start` (er hat den Ton begonnen), `keiner` (er hat **bewusst** keinen Ton gespielt:
nur der Modus „stumm“, R10), `fertig` (der Ton ist zu Ende), `fehler` (der Ton lief nicht). Wort von `app`: `uebernommen` (Gegenmarke, V1). Sie liegt in `/run/tobibox/` (tmpfs: nach jedem Einschalten leer, kein Eintrag
im Sync, im Schreibbudget oder im Update-Paket). **Wer sie zuerst anlegt, entscheidet**: Sie wird atomar und nur angelegt, wenn es sie noch nicht gibt (eine fertig geschriebene temporäre Datei im selben Verzeichnis,
dann `link`; nie ein halb gelesener Inhalt). Der Frühdienst legt `start` oder `keiner` an, spielt den Ton und ersetzt `start` danach per `rename` durch `fertig` (oder `fehler`), und zwar nur, wenn die Marke noch da ist.
Kann er nicht spielen (Konfiguration, Datei, Abspielprogramm oder Ausgang fehlt, Fehler), legt er **keine** Marke an. `app` liest sie **bei `Bereit`** (nicht beim Dienststart, V1): Gibt es sie nicht, legt `app` die Gegenmarke
`uebernommen` an, und der Frühdienst darf dann nicht mehr spielen; so gibt es nie zwei Töne. War ein Wort des Frühdienstes (`start`, `keiner`, `fertig`) da, ist `Bereit.fruehton` wahr (`core-interface.md`, Abschnitt 3.3 und 6.5g);
`app` löscht die Marke, sobald `fertig` oder `keiner` dasteht oder `FRUEHTON_WARTEN_S` um sind (die Gegenmarke bleibt bis zum Ausschalten). Bei einem Dienst-Neustart ohne Ausschalten (gleiche Boot-Kennung wie in `lauf.json`)
ignoriert `app` die Marke und ersetzt sie durch `uebernommen`; ohne lesbare Boot-Kennung (Datei fehlt oder unlesbar) gilt Einschalten (V17). Eine fehlende, leere, halbe oder unbekannte Marke und `fehler` heißen: kein Frühton,
der Kern spielt `start` wie bisher (unter „stumm“ nichts, V5). Das Verzeichnis `/run/tobibox/` legt systemd an (`RuntimeDirectory=tobibox`, Modus 0755, Besitzer der Benutzer `tobibox`, unter dem Frühdienst und Box-Dienst laufen) und
muss auch bestehen bleiben, wenn der Frühdienst endet (`RuntimeDirectoryPreserve=yes`; Umsetzung: `deploy/pi/tobibox-fruehton.service`).

**`lauf.json` (Entscheidung G, 06.11.):** `{"boot_id": <Kennung des aktuellen Starts des Geräts>, "uid": <Kennung des liegenden Tobies oder null>}`.
`boot_id` ist unter Linux `/proc/sys/kernel/random/boot_id`, am Mac die Systemstartzeit
(`sysctl -n kern.boottime`). Die Box schreibt die Datei bei jedem Wechsel des liegenden Tobies
(Aufgelegt, Abgehoben) und beim Dienst-Ende und löscht sie beim eigenen Herunterfahren. Beim Start
gilt eine Datei mit **gleicher** `boot_id` als Dienst-Neustart ohne Ausschalten (der Tobie `uid`
startet nicht von selbst, `GeraeteEinstellungen.neustart_uid`); fehlende, unlesbare oder fremde
Datei bedeutet Einschalten (CUJ 20). Kein `schema_version`, nicht im Sync, nicht im Schreibbudget
(höchstens eine Schreibung je Tobie-Wechsel).

### 1.7 Schreibbudget

*   `resume.json` (Entscheidung N, 09.11.): Der Zeitstempel `benutzt_am` verlangt keine zusätzlichen Schreibungen,
    außer bei einem **unveränderten** Zeiger, dessen Zeitstempel fehlt oder mindestens eine Stunde alt ist
    (höchstens eine Schreibung je Zeiger und Stunde, nur bei Benutzung; die Zahl unten bleibt eine Obergrenze).
*   `resume.json`: höchstens eine Schreibung je Pause, Folgen- und
    Track-Wechsel, Tobie-Wechsel, Herunterfahren und alle 30 s während der Wiedergabe, und nur
    bei Änderung (`reader-v1`/`core-interface`). **Neu gerechnet (Entscheidung F,
    05.11.):** bei 2 h Wiedergabe am Tag höchstens 240 periodische Schreibungen
    (7200 s / 30 s) plus je eine für jede Pause, jeden Tobie-Wechsel und jeden
    Track-Wechsel; mit angenommenen 40 Pausen oder Wechseln und 40 Track-Wechseln
    am Tag **höchstens 320 Schreibungen am Tag und Box** (jede Schreibung setzt die
    30-s-Frist zurück, die Zahl ist also eine Obergrenze).
*   `unknown.json`: eine Schreibung je neuer Meldung und je Bestätigung.
*   `config.json`: eine Schreibung je angenommener Liste.
*   `update.json`: je Start im Zustand `testing` eine Schreibung (Zähler).

## 2. `config.json`

Konfiguration von HA, mit **einer** Revision und **einer** Listen-ID. Dieselbe
Struktur ist die Nachricht auf dem Thema `tobibox/config` (`mqtt-v1.md`).

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `2` (Entscheidung F, 05.11.) (Version 1: ohne `ziel`, Migration unten) |
| `revision` | int ≥ 1 | ja | Versionsnummer der Konfiguration. HA erhöht sie bei jeder Änderung um 1. Eine **neue Liste** (neue `liste_id`) beginnt mit Revision 1. (Eine Box ohne Datei rechnet mit Revision 0.) |
| `liste_id` | string, 16 Zeichen `[0-9a-f]` | ja | Kennung des HA-Speichers. In Stufe 2 ohne HA hat die lokale Liste `0000000000000000`. |
| `erzeugt_am` | string (Zeitstempel) | nein | wann HA diese Fassung erzeugt hat (nur zur Anzeige) |
| `zuordnungen` | object | ja (darf leer sein) | Schlüssel = Kennung (kanonisch), Wert = Zuordnung |
| `zuordnungen.<uid>.ziel` | object | ja | Worauf der Tobie zeigt (Entscheidung F, 05.11.) |
| `zuordnungen.<uid>.name` | string, 1–60 Zeichen | nein | **Tobie-Name** für die HA-Seite (Vorgabe der Projektleitung, 09.11.), z. B. „Rabe aus Holz“. Ohne Steuerzeichen, Leerraum gekürzt. Die Box **ignoriert** das Feld (1.4): Die Prüfung der Liste (`validiere_konfig`) schaut nur auf `ziel`, ein vorhandenes `name` macht eine Liste nie ungültig. Alte Listen ohne `name` bleiben gültig. Ändert HA nur einen Namen, gilt das wie jede Änderung (Revision + 1). Ein Name erhöht die Größe der Liste um höchstens 70 Bytes je Zuordnung (Grenze 256 KiB, `mqtt-v1.md`, Abschnitt 1). |
| `ziel.typ` | `"serie"`, `"folge"` oder `"aktion"` | ja | `serie`: jedes Auflegen setzt die Serie an ihrem Zeiger fort. `folge`: genau eine Folge einer Serie. `aktion`: Aktionskarte. |
| `ziel.serie` | string | wenn `typ="serie"` oder `typ="folge"` | Serien-ID. Verweist die ID auf keine Serie auf der Box (noch nicht synchronisiert), spielt die Box die **Überraschungs-Serie** und protokolliert den Grund (`serie_fehlt`); kommt die Serie später, gilt die Zuordnung beim nächsten Auflegen (`core-interface.md`, Abschnitt 6.3). |
| `ziel.folge` | string | wenn `typ="folge"` | Name der Folge in der Serie (Dateiname oder Ordnername, reiner Name nach 1.1). Gibt es die Folge in der Serie auf der Box nicht, gilt dasselbe wie bei fehlender Serie (`folge_fehlt`). |
| `ziel.aktion` | `"status"` oder `"gute_nacht"` | wenn `typ="aktion"` | |
| `leise_zeiten` | object | ja | |
| `leise_zeiten.zeitzone` | string | nein | IANA-Zeitzone für `von` und `bis`. Vorgabe, wenn das Feld fehlt: `Europe/Berlin`. Ein Name, den die Zeitzonendatenbank der Box nicht kennt, macht die ganze Liste ungültig (`schema_ungueltig`). HA stellt sie ein (auf Reisen umstellbar). |
| `leise_zeiten.fenster` | array | ja (darf leer sein) | beliebig viele, höchstens 32 |
| `fenster[].id` | string, 1–32 Zeichen `[a-z0-9_-]` | ja | eindeutig in der Liste |
| `fenster[].tage` | array von int 1–7 | ja | ISO-Wochentage (1 Montag bis 7 Sonntag), nicht leer, ohne Doppelte. Das Fenster gehört zu dem Tag, an dem es **beginnt**. |
| `fenster[].von` | string `HH:MM` | ja | Beginn, Ortszeit, 24 Stunden |
| `fenster[].bis` | string `HH:MM` | ja | Ende (ausschließlich), Ortszeit. `bis` **kleiner als** `von` heißt: das Fenster reicht über Mitternacht in den nächsten Tag. `bis` **gleich** `von` ist ungültig. |
| `fenster[].wirkung` | `"leiser"` oder `"stumm"` | ja | |
| `fenster[].grenze` | int 0–100 | bei `leiser` ja | Lautstärke-Grenze in Prozent. Bei `stumm` fehlt das Feld oder ist `null`. |
| `gute_nacht` | object | ja | |
| `gute_nacht.timer_min` | int 1–240 | ja | Dauer des Timers (Vorschlag 30) |
| `gute_nacht.ausblenden_s` | int 5–600 | ja | Dauer des Ausblendens (Vorschlag 60) |
| `lesezeichen_tage` | int 0–365 | nein | **(09.11., Entscheidung N)** Wurde ein Zeiger (Lesezeichen) länger als so viele Tage nicht benutzt, beginnt beim Fortsetzen die Folge wieder von vorn (Track 0, Position 0); bei einer Serie bleibt die Folge dieselbe. Vorgabe **14**, wenn das Feld fehlt. `0` heißt: läuft nie ab. Gilt nur bei sicherer Uhr und nur für Zeiger mit `benutzt_am` (`core-interface.md`, 6.3). Ein Wert außerhalb von 0 bis 365 oder keine ganze Zahl macht die ganze Liste ungültig (`schema_ungueltig`). Eine Seitenbedienung kommt mit den Einstellungen in Stufe 4; Vertrag W reserviert das Feld (`protocol/ha-websocket-v1.md`, Abschnitt 10). HA legt das Feld mit der Vorgabe 14 an, veröffentlicht und exportiert es und holt es mit `konfig/aus_export` zurück (09.11., Befund AP 3.1). Additiv, `schema_version` bleibt 2. |
| `ton_pegel` | int 0–100 | nein | **Ohne Wirkung** (seit Entscheidung J, 09.11.). Die Box liest das Feld nicht; Töne folgen der aktuellen Lautstärke der Sitzung (`core-interface.md`, Abschnitt 8.1). Das Feld bleibt gültig, alte Dateien laden unverändert. |
| `hinweis_pegel` | int 0–100 | nein | Pegel des leisen Hinweistons unter „stumm“ **und des Tons `lader`** (Ein/Aus, 10.11.; der Ton `lader` spielt nur in normalen Zeiten, mit demselben Pegelweg) in Prozent; Vorgabe 15 (Feld fehlt). **Nicht** für den frühen Start-Ton: Er hat den Pegel eines gewöhnlichen Tons, in „leiser“ mit der Grenze des Fensters, in „stumm“ gar keinen Ton (`core-interface.md`, Abschnitt 8.1). Der Hinweiston ist auch in der Sprachfassung nur ein kurzer, leiser Klang, kein gesprochenes „Hinweis.“ (Entscheidung T, 10.11.). Er spielt mit `min(Grenze, max(10, min(hinweis_pegel, Lautstärke)))`, also nie leiser als die Untergrenze 10 (`HINWEIS_MINDEST`; vor Entscheidung J war sie 5) und sonst nie lauter als die aktuelle Lautstärke. **Die wirksame Grenze gewinnt immer** (Gehörschutz): Liegt sie unter 10 (zum Beispiel Kopfhörer-Grenze 5), spielt der Hinweiston mit der Grenze (`core-interface.md`, Abschnitt 8.1). |

Regeln:

*   **Gültigkeit:** Ist irgendein Teil ungültig (Wertebereich, doppelte `id`,
    Kennung nicht kanonisch, unbekannter `ziel.typ`, `folge` ohne `serie`), wird die **ganze Liste**
    abgelehnt (Grund `schema_ungueltig`). Die Box behält ihre bisherige
    Konfiguration. **Die Prüfung von `ziel` läuft nach der Migration**
    (Entscheidung F, 05.11.): Eine Liste der Version 1 (aus der Datei oder von
    `tobibox/config`) wird zuerst im Speicher nach Version 2 migriert und dann mit
    derselben Funktion geprüft wie jede Liste der Version 2. Diese eine Funktion
    (Migration und Prüfung) liegt in `store.py`; `ha.py` benutzt sie, statt
    eine eigene Prüfung zu schreiben.
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
    nichts aktiv. `t` ist die Wanduhrzeit in `leise_zeiten.zeitzone`.
*   **Sommerzeit-Umstellung:** `von` und `bis` sind Wanduhrzeiten. Auf Zeitpunkte
    (UTC) abgebildet werden sie so: Eine Ortszeit, die es gibt, ist eindeutig.
    Eine **nicht existierende** Ortszeit (Vorstellen der Uhr, z. B. 02:30 am Tag,
    an dem 02:00 auf 03:00 springt) gilt als die **nächste gültige Minute** (03:00);
    ein Fenster, das dort beginnt, beginnt also um 03:00, eines, das dort endet,
    endet um 03:00. Eine **mehrdeutige** Ortszeit (Zurückstellen, z. B. 02:30 kommt
    zweimal) gilt als ihr **erstes** Auftreten (Sommerzeit). Ein Fenster ist in der
    Umstellungsnacht deshalb in echter Dauer länger oder kürzer (ein Fenster
    „19:30 bis 07:00“ im Herbst eine Stunde länger) und fängt oder hört nie
    doppelt auf.
*   **Nicht vertrauenswürdige Zeit** (`Jetzt.zeit_ok = False`): es gilt die
    kleinste `grenze` aller „leiser“-Fenster der Liste, nie stumm; gibt es kein
    „leiser“-Fenster, gilt die normale Grenze. Außerdem lehnt die Box Lernmodus,
    Sync und Update ab und meldet es an HA (`event` `befehl_abgelehnt`,
    `grund="zeit_unsicher"`); HA zeigt den Grund an (`mqtt-v1.md`).
*   Überraschungs-Serie und gesperrte Tobies stehen nicht in `zuordnungen`. Die
    Überraschungs-Serie verhält sich wie ein Ziel `serie` (Entscheidung F, 05.11.).
*   **Migration Version 1 → 2 (Entscheidung F, 05.11.):** Jeder Eintrag `{ "typ": …, … }` in
    `zuordnungen` wird im Speicher zu `{ "ziel": { "typ": …, … } }` (die Felder
    `typ`, `serie`, `aktion` ziehen unverändert in `ziel`). Ein Eintrag mit
    `typ="serie"` bleibt ein Serien-Tobie; Folgen-Tobies entstehen nur in
    Version 2.

Beispiel:

```json
{
  "schema_version": 2,
  "revision": 17,
  "liste_id": "a3f9c1e07b2d4856",
  "erzeugt_am": "2026-11-05T09:30:00Z",
  "zuordnungen": {
    "e0040312345678ab": { "ziel": { "typ": "serie", "serie": "3f9a1c07b2d4" }, "name": "Rabe aus Holz" },
    "04a1b2c3": { "ziel": { "typ": "folge", "serie": "8c21d5e9a0b7", "folge": "folge-03.mp3" } },
    "04ffeedd": { "ziel": { "typ": "aktion", "aktion": "status" } },
    "04112233445566": { "ziel": { "typ": "aktion", "aktion": "gute_nacht" }, "name": "Gute-Nacht-Karte" }
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
  "gute_nacht": { "timer_min": 30, "ausblenden_s": 60 },
  "ton_pegel": 40,
  "hinweis_pegel": 15,
  "lesezeichen_tage": 14
}
```

## 3. `resume.json`

Die Zeiger. Nur die Box schreibt und liest sie; sie wird nie synchronisiert.
Ein Zeiger ist (Folge, Track, Position) (Entscheidung F, 05.11.). Es gibt zwei Arten: den **Serien-Zeiger**
(ein Zeiger je Serie, für Serien-Tobies und die Überraschungs-Serie) und den
**Folgen-Zeiger** (ein Zeiger je Serie und Folge, für Folgen-Tobies).

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `2` (Version 1: ohne `track` und `folgen`) |
| `serien` | object | ja (darf leer sein) | Serien-Zeiger. Schlüssel = Serien-ID |
| `serien.<id>.folge` | string | ja | Name der aktuellen Folge (Dateiname oder Ordnername, nur der Name) |
| `serien.<id>.index` | int ≥ 0 | ja | Nummer der Folge in der Reihenfolge der Serie, ab 0; Hinweis für den Fall, dass die Folge fehlt |
| `serien.<id>.track` | int ≥ 0 | ja (Version 1: fehlt, gilt als 0) | Nummer des Tracks in der Folge, ab 0 (bei einer Folge aus einer Datei immer 0) |
| `serien.<id>.position_s` | number ≥ 0 | ja | Position in Sekunden **im Track**, **ohne** den Rücksprung von 3 s (den rechnet die Box beim Abspielen), auf 1 Nachkommastelle **abgerundet**. 0 heißt: der Track beginnt vorn (z. B. nach einem Folgenende). |
| `serien.<id>.zaehler` | int ≥ 1 | ja | Anzahl der Schreibungen dieses Zeigers; wird bei jedem Speichern um 1 erhöht. Dient der Fehlersuche und der Kontrolle des Schreibbudgets. |
| `serien.<id>.benutzt_am` | string (Zeitstempel, UTC, `…Z`, auf die Sekunde) | nein | **(09.11., Entscheidung N)** Wann der Zeiger zuletzt benutzt wurde: zuletzt gespeichert beim Spielen (alle 30 s), Pausieren oder Abheben. Die Box schreibt ihn nur bei sicherer Uhr (`jetzt.zeit_ok`); bei unsicherer Uhr bleibt ein vorhandener Wert stehen. **Fehlt das Feld** (alte Datei, Uhr nie sicher), läuft der Zeiger nie ab; er bekommt den Zeitstempel beim nächsten Speichern mit sicherer Uhr. Ein Wert, der kein Zeitstempel dieser Form ist, macht die Datei ungültig (Rückfall auf `.bak`, 1.3). Additiv, `schema_version` bleibt 2. |
| `folgen` | object | ja (darf leer sein; Version 1: fehlt, gilt als leer) | Folgen-Zeiger. Schlüssel = Serien-ID, Wert = Objekt mit Schlüssel = Name der Folge |
| `folgen.<id>.<folge>.track` | int ≥ 0 | ja | wie `serien.<id>.track` |
| `folgen.<id>.<folge>.position_s` | number ≥ 0 | ja | wie `serien.<id>.position_s` |
| `folgen.<id>.<folge>.zaehler` | int ≥ 1 | ja | wie `serien.<id>.zaehler` |
| `folgen.<id>.<folge>.benutzt_am` | string (Zeitstempel) | nein | wie `serien.<id>.benutzt_am` (Entscheidung N, 09.11.) |

Regeln der Zeiger (Folgenende, fehlende Folge, fehlender Track, Rücksprung,
kleiner Rest gilt als fertig gehört (Entscheidung I, 09.11.), Vor / Zurück): siehe `core-interface.md`, Abschnitt 6.3. Die Namen der
JSON-Felder und die Typen im Kern bilden die Tabelle in `core-interface.md`,
Abschnitt 3.8, aufeinander ab (`folge` ↔ `Zeiger.datei`, `serien` und `folgen`
↔ `tuple[Zeiger]`). Ein Eintrag für eine Serie oder Folge, die es nicht mehr
gibt, bleibt stehen und schadet nicht.

*   **Folgenende bei einem Serien-Zeiger:** Der Eintrag zeigt auf die nächste
    Folge (nach der letzten auf die erste), `track` 0, `position_s` 0.
*   **Folgenende bei einem Folgen-Zeiger:** Der Eintrag springt auf `track` 0,
    `position_s` 0 zurück; das nächste Auflegen spielt die Folge von vorn.
*   **Migration Version 1 → 2 (Entscheidung F, 05.11.):** Jeder Eintrag in `serien` bekommt `track` 0
    (die gespeicherte Position gilt für den ersten Track); `folgen` ist leer.
    Die Migration ist rein und hat einen eigenen Test.
*   **Der Zustand `beendet` steht nicht in `resume.json`** (Entscheidung F,
    05.11.): Nach einem Neustart des Dienstes gibt es keine „eben beendete Folge“;
    die Sitzung beginnt ohne Wiedergabe mit dem gespeicherten Zeiger
    (`core-interface.md`, 9.12).

Beispiel:

```json
{
  "schema_version": 2,
  "serien": {
    "3f9a1c07b2d4": {
      "folge": "folge-02.mp3",
      "index": 1,
      "track": 0,
      "position_s": 412.5,
      "zaehler": 37,
      "benutzt_am": "2026-11-09T17:42:10Z"
    },
    "8c21d5e9a0b7": {
      "folge": "CD Die Schatzinsel",
      "index": 0,
      "track": 2,
      "position_s": 95.0,
      "zaehler": 3
    }
  },
  "folgen": {
    "3f9a1c07b2d4": {
      "folge-03.mp3": {
        "track": 0,
        "position_s": 0.0,
        "zaehler": 5
      }
    }
  }
}
```

## 4. `unknown.json`

Der Ereignis-Ausgang der Box (`outbox`): Kennungen, die HA noch nicht bestätigt
hat. Ein Eintrag wird **erst** gelöscht, wenn HA auf dem Thema `…/ack`
bestätigt hat (nicht schon beim PUBACK des Brokers) und die Bestätigung zum
**aktuellen** Eintrag passt: Der `ack` trägt `zuletzt` und `art` der
Veröffentlichung, die er bestätigt, und die Box löscht nur, wenn beide mit dem
Eintrag übereinstimmen. Ein verspäteter `ack` für eine ältere Fassung löscht
nichts (der Eintrag wurde inzwischen überschrieben; `anzahl` und `zuletzt`
ändern sich bei jeder neuen Meldung, `gelernt` ersetzt `unbekannt`).

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `1` |
| `eintraege` | object | ja (darf leer sein) | Schlüssel = Kennung (kanonisch); höchstens ein Eintrag je Kennung |
| `eintraege.<uid>.art` | `"unbekannt"` oder `"gelernt"` | ja | `gelernt`: im Lernmodus aufgelegt. `gelernt` ersetzt `unbekannt`, nie umgekehrt. |
| `eintraege.<uid>.zuerst` | string (Zeitstempel) | ja | erste Meldung |
| `eintraege.<uid>.zuletzt` | string (Zeitstempel) | ja | letzte Meldung, ISO 8601 mit **Millisekunden** (`2026-11-05T09:12:03.412Z`); der `ack` gibt den Wert unverändert zurück (`mqtt-v1.md`) |
| `eintraege.<uid>.anzahl` | int ≥ 1 | ja | wie oft die Kennung gemeldet wurde |
| `eintraege.<uid>.zeit_ok` | bool | ja | war die Uhrzeit bei der **letzten** Meldung vertrauenswürdig? Bei `false` sind `zuerst` und `zuletzt` mit Vorsicht zu lesen. |
| `eintraege.<uid>.befehl_id` | string oder `null` | ja | bei `gelernt` die ID des Lernbefehls aus `tobibox/<box>/cmd`, sonst `null` |

*   Höchstens **200** Einträge. Kommt ein 201. hinzu, wird der mit dem ältesten
    `zuletzt` verworfen und das protokolliert.
*   Die Box löscht auf eine passende Bestätigung zuerst die dauerhafte Nachricht
    auf dem Broker (leere Nutzlast), danach den Eintrag (`mqtt-v1.md`, 4.1). Die
    HA-Integration ignoriert diese leere Nachricht.
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
      "zuletzt": "2026-11-05T08:15:40.127Z",
      "anzahl": 3,
      "zeit_ok": true,
      "befehl_id": null
    },
    "e0040312345678ab": {
      "art": "gelernt",
      "zuerst": "2026-11-05T09:12:03Z",
      "zuletzt": "2026-11-05T09:12:03.412Z",
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
| `id` | string | ja | Serien-ID, **unveränderlich**: zufällig erzeugt (12 Zeichen `[0-9a-f]`), oder der Ordnername, wenn HA die Datei für einen Ordner anlegt, der vorher keine hatte (siehe Regeln) |
| `name` | string, 1–100 Zeichen | ja | Anzeigename |
| `typ` | `"normal"` oder `"ueberraschung"` | ja | Die Überraschungs-Serie ist **nur** daran erkennbar; es gibt keine feste ID. |
| `folgen` | array von string | ja (darf leer sein) | Namen der Folgen in der maßgeblichen Reihenfolge: Dateiname (Folge aus einer Datei) oder Ordnername (Folge aus mehreren Tracks) (Entscheidung F, 05.11.). Die Tracks eines Folgen-Ordners stehen nicht in `serie.json`; die Box liest sie aus dem Ordner. |
| `angelegt_am` | string (Zeitstempel) | ja | Anlegezeit. Bei doppelter `id` entscheidet das spätere `angelegt_am` (jüngere Kopie bekommt eine neue ID). |
| `pruefen` | bool | nein | **(09.11., Entscheidung M)** Die Serie wurde beim Einsortieren aus schwachen Angaben (Interpret, Ordnername) angelegt: „bitte prüfen“. Fehlt = `false`. |
| `pruefen_gruende` | array von string | nein | Codes zu `pruefen` (Vertrag W, 11.9). |
| `folgen_info` | object | nein | **(09.11.)** Schlüssel = Name einer Folge aus `folgen`; Wert = Objekt mit den optionalen Feldern `anzeige` (string, 1–200 Zeichen: Anzeigename), `nummer` (int ≥ 0: Folgen-Nummer aus den Tags oder dem Albumnamen), `datum` (string `YYYY-MM-DD`: Erscheinungsdatum), `pruefen` (bool) und `pruefen_gruende` (array von string). Nur die HA-Integration schreibt es. Einträge für Namen, die nicht in `folgen` stehen, sind bedeutungslos und werden beim nächsten Schreiben entfernt. |

Regeln (aus dem Design, hier zusammengefasst):

*   **Folge auf der Platte (Entscheidung F, 05.11.):** Eine Folge ist entweder **eine Audiodatei**
    im Serien-Ordner oder ein **Unterordner mit mehreren Tracks** (z. B. ein
    CD-Rip). Die **Tracks** eines Folgen-Ordners sind die Dateien direkt im
    Unterordner (keine weitere Verschachtelung), ohne Dotfiles und mit derselben
    Endungsliste wie unten (Dateifilter); ihre Reihenfolge ist die natürliche
    Sortierung (unten). Ein Unterordner ohne Track zählt nicht als Folge
    (`folge_leer`, Protokoll). Ein Name, der zugleich als Datei und als Ordner
    vorkommen könnte, kommt auf dem Dateisystem nicht doppelt vor; es gilt, was
    dort liegt. Ein Hörspiel ohne Serie liegt in einem beliebigen Serien-Ordner
    (z. B. „Einzelfolgen“), ohne Sonderregel.
*   **Reihenfolge:** Die Liste `folgen` ist maßgeblich. Dateien und
    Folgen-Ordner im Ordner, die nicht in der Liste stehen, spielt die Box erst,
    wenn die Integration sie eingetragen hat. Namen in der Liste, die im Ordner
    fehlen, werden von der Box übersprungen. Doppelte Namen in der Liste zählen einmal (erster
    Treffer).
*   **Ordner ohne `serie.json`:** Die Box spielt ihn trotzdem. ID = Ordnername,
    `name` = Ordnername, `typ` = `normal`, Reihenfolge = natürliche Sortierung
    der Dateinamen (unten). Der Ordnername muss als ID gültig sein (1 bis 64
    Zeichen, keine Steuerzeichen); sonst spielt die Box den Ordner nicht und
    protokolliert `ordner_name_ungueltig`.
*   **Dateifilter (Ordner ohne `serie.json`, und für die Tracks eines
    Folgen-Ordners):** Als Folgen bzw. Tracks zählen nur Dateien, deren Name
    **nicht mit `.` beginnt** (versteckte Dateien, `._*` von macOS)
    und deren Endung (ohne Unterscheidung von Groß-/Kleinschreibung) eine von
    `mp3`, `m4a`, `m4b`, `aac`, `flac`, `ogg`, `opus`, `wav` ist. Die
    HA-Integration benutzt dieselbe Liste, wenn sie `folgen` für einen solchen
    Ordner anlegt. Unterordner, deren Name nicht mit `.` beginnt und die
    mindestens einen Track nach diesem Filter enthalten, zählen als Folgen.
*   **HA legt `serie.json` für einen solchen Ordner an:** Die Integration
    übernimmt den **Ordnernamen als `id`** (keine neue Zufalls-ID), damit Zeiger
    (`resume.json`) und Zuordnungen (`config.json`) erhalten bleiben. Die
    Reihenfolge in `folgen` ist die natürliche Sortierung (unten). Eine Serie,
    die HA neu anlegt (neuer Ordner), bekommt eine zufällige ID.
*   **Natürliche Sortierung** (Box und HA-Integration benutzen **dieselbe**
    Regel; gibt es ein gemeinsames Hilfsmodul, dann dieses). Sortiert werden die
    Namen (UTF-8, unverändert, ohne Unicode-Normalisierung): bei den Folgen einer
    Serie ohne `serie.json` die Datei- und Ordnernamen, bei den Tracks eines
    Folgen-Ordners die Dateinamen (Entscheidung F, 05.11.):
    1.  Jeder Name wird in abwechselnde Abschnitte zerlegt: **Ziffernblöcke**
        (maximale Folgen der ASCII-Ziffern `0`–`9`) und **Textblöcke** (alles
        dazwischen).
    2.  Zwei Namen werden Abschnitt für Abschnitt von vorn verglichen. Ein
        Ziffernblock ist **kleiner** als ein Textblock. Zwei Ziffernblöcke
        vergleicht man als ganze Zahlen (führende Nullen zählen nicht, Länge
        beliebig). Zwei Textblöcke vergleicht man **ohne Unterscheidung von Groß-
        und Kleinschreibung** (Unicode-`casefold`) nach Codepunkten.
    3.  Ist ein Name am Ende seiner Abschnitte, aber der andere nicht, ist der
        kürzere kleiner.
    4.  Sind alle Abschnitte gleich, entscheidet der **rohe Byte-String** des
        Namens (UTF-8, Byte für Byte, kleinerer Wert zuerst). Das macht die
        Ordnung total und eindeutig (z. B. `Folge-01.mp3` vor `folge-01.mp3`,
        `1.mp3` nach `01.mp3`).

    Beispiele (aufsteigend): `folge-2.mp3`, `folge-10.mp3`; `a1.mp3`, `a1b.mp3`;
    `01.mp3`, `1.mp3`, `2.mp3`, `10.mp3`; `Folge.mp3`, `folge.mp3`.
*   **Die Box ignoriert `pruefen`, `pruefen_gruende` und `folgen_info`** (1.4); sie
    spielt nach Dateinamen und `folgen`. Das **Umbenennen** einer Serie oder Folge in
    HA ändert nur `name` bzw. `folgen_info.<name>.anzeige`, nie einen Datei- oder
    Ordnernamen; Zeiger und Zuordnungen bleiben gültig. Der **Sortierschlüssel**
    (Nummer, Datum) dient der HA-Integration, wenn sie neue Folgen einfügt (Vertrag W, 11.6).
*   **Reservierte Namen in `medien/` (09.11.):** Ordner, deren Name mit `_` beginnt
    (`_papierkorb`, `_upload`), und der Name `eingang` (ohne Rücksicht auf
    Groß-/Kleinschreibung) sind **keine Serien**. Die HA-Integration legt dafür keine
    `serie.json` an. Sie werden vom Sync der Box ausgenommen und erreichen die Box nie;
    die Box-Software braucht deshalb keine eigene Regel. Namensregeln für neue Dateien und
    Ordner: Vertrag W, Abschnitt 12.
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

Beispiel (Serie mit einer Folge aus mehreren Tracks (Entscheidung F, 05.11.)): Die Folge
`CD Die Schatzinsel` ist ein Unterordner mit z. B. `01.mp3`, `02.mp3`, `03.mp3`;
die Tracks stehen nicht in der Datei.

```json
{
  "schema_version": 1,
  "id": "8c21d5e9a0b7",
  "name": "Die Schatzinsel",
  "typ": "normal",
  "folgen": ["CD Die Schatzinsel", "folge-02.mp3"],
  "angelegt_am": "2026-11-05T09:02:00Z"
}
```

Beispiel (Serie, die HA aus dem Eingang einsortiert hat, mit `folgen_info` (09.11.)):

```json
{
  "schema_version": 1,
  "id": "5d0e7a3c91b8",
  "name": "Der kleine Rabe",
  "typ": "normal",
  "folgen": ["folge-01.mp3", "Der Wald"],
  "angelegt_am": "2026-11-09T18:00:00Z",
  "folgen_info": {
    "folge-01.mp3": { "anzeige": "Der kleine Rabe - Folge 1: Der Anfang", "nummer": 1, "datum": "2019-03-01" },
    "Der Wald": {
      "anzeige": "Der kleine Rabe - Folge 2: Der Wald",
      "nummer": 2,
      "pruefen": true,
      "pruefen_gruende": ["track_teils_leer"]
    }
  }
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
| `schema_versionen` | object | ja | Version je Zustandsdatei, die dieses Paket schreibt: Schlüssel `config`, `resume`, `unknown`, `serie`, `update`; Wert int (ab Entscheidung F, 05.11.: `config` und `resume` = 2) |
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
    "config": 2,
    "resume": 2,
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

## 9. Papierkorb-Eintrag (`meta.json`) (09.11., Vertrag W, 3.3)

Jeder Eintrag im Papierkorb ist ein Ordner `medien/_papierkorb/<id>/` mit der Datei
`meta.json` und dem Ordner `inhalt/`, der das Gelöschte **unter seinem bisherigen Namen**
enthält (eine Datei, ein Folgen-Ordner oder ein ganzer Serien-Ordner). `<id>` sind 12
Zeichen `[0-9a-f]` (vom Backend erzeugt), damit zwei gleichnamige Löschungen nie
kollidieren. Das Verschieben ist ein Umbenennen auf derselben Freigabe. Schreiber ist
allein die HA-Integration (`media.py`); die Boxen holen den Papierkorb nie (vom Sync
ausgenommen).

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `schema_version` | int | ja | `1` |
| `id` | string | ja | wie der Ordnername |
| `typ` | `"folge"`, `"serie"` oder `"eingang"` | ja | was es war |
| `grund` | `"manuell"`, `"zusammengefuehrt"`, `"doppelt"` oder `"eingang_rest"` | ja | wie es in den Papierkorb kam |
| `geloescht_am` | string (Zeitstempel) | ja | |
| `serie_id` | string oder `null` | ja | Serie, aus der es kam (`null` bei `eingang`) |
| `serie_name` | string oder `null` | ja | Anzeigename der Serie zum Zeitpunkt des Löschens |
| `serie_ordner` | string oder `null` | ja | Ordnername der Serie auf der Freigabe (`typ="serie"`: der Ordner, der zurückkommt) |
| `name` | string | ja | ursprünglicher Name der Datei oder des Ordners (= Name in `inhalt/`) |
| `art` | `"datei"` oder `"ordner"` | ja | |
| `dateien` | int | ja | Anzahl Dateien (Tracks) |
| `groesse_bytes` | int | ja | |
| `folge_info` | object oder `null` | ja | bei `typ="folge"` der Eintrag aus `folgen_info` (Anzeigename, Nummer, Datum, `pruefen`), sonst `null` |
| `serie_json` | object oder `null` | ja | bei `typ="serie"` eine Kopie der `serie.json`; sonst `null` |
| `index_pruefsummen` | array von string | nein | SHA-256 der Dateien, die zum Hash-Index des Einsortierens gehörten (Vertrag W, 11.10); sie kommen beim Wiederherstellen zurück in den Index |

Das Schreiben ist atomar (`.tmp`, `fsync`, umbenennen, 1.2 ohne `.bak`). Eine
`meta.json` ohne `inhalt/` (oder umgekehrt) gilt als Rest eines Abbruchs und wird beim
nächsten Prüfen der Freigabe protokolliert (`papierkorb_unvollstaendig`) und nicht
angeboten.

## 10. Eingang `eingang/` (09.11., Vertrag W, Abschnitt 11)

Der Eingang ist ein Ordner `tobibox/eingang/` auf dem NAS, **neben** `medien/`, `export/` und
`releases/` (dieselbe Freigabe). Tobias legt dort Ordner und Dateien ab (zum Beispiel einen
Hörbuch-Download), die HA-Integration liest die Tags und sortiert sie in `medien/` ein.
Es gibt **keine** Dateien mit festem Schema im Eingang; der Zustand des Einsortierens
(Protokoll der letzten 100 Einträge, Hash-Index, Upload-Vorgaben) liegt im HA-Speicher,
nicht auf dem NAS.

*   Der Eingang wird **nie gesynct** (außerhalb des Moduls `medien`); `_upload/`,
    `_papierkorb/` und `eingang` werden zusätzlich im Sync ausdrücklich ausgenommen.
*   Dateifilter wie bei den Tracks (Abschnitt 5): kein Dotfile, Endung aus der Liste.
*   Die Box-Software ändert sich dadurch nicht: Was einsortiert ist, hat die Form von
    Abschnitt 5 (Serien-Ordner, `serie.json`, Dateien oder Folgen-Ordner).

## Festlegungen in diesem Vertrag (Stand 05.11.)

Das Design lässt diese Einzelheiten offen. Entschieden wurde die einfachste
stimmige Lösung. „Bestätigt (05.11.)“ heißt: von Tobias (T) oder der
Projektleitung (P) entschieden oder aus dem Goldfisch-Review übernommen
(`protocol/review-stufe0.md`). Alle anderen Punkte sind noch offen.

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
6.  **Bestätigt (05.11., P): Ortszeit für Leise-Zeiten:** Das Feld
    `leise_zeiten.zeitzone` (IANA-Name) gehört zur Liste in `config.json`, ist
    einstellbar und hat die Vorgabe `Europe/Berlin`. Das Design nennt keine
    Zeitzone. Sommerzeit: Fenster gelten nach Wanduhrzeit, eine nicht
    existierende Startzeit beginnt zur nächsten gültigen Minute, eine mehrdeutige
    gilt als ihr erstes Auftreten. Wochentage als ISO-Zahlen 1 bis 7; Fenster
    über Mitternacht (`bis` < `von`; `bis` = `von` ungültig) gehören zum Tag des
    Beginns; mehrere aktive Fenster: „stumm“ gewinnt, bei „leiser“ die kleinste
    Grenze. Bei unsicherer Uhr lehnt die Box Lernmodus, Sync und Update ab, und
    HA zeigt den Grund (bestätigt, T).
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
14. **Bestätigt (05.11., T): Verweist eine Zuordnung auf eine Serie, die auf der
    Box fehlt,** spielt die Box die Überraschungs-Serie (kein Fehlerton, keine
    Stille), protokolliert den Grund, und die Zuordnung gilt beim nächsten Auflegen,
    sobald die Serie da ist.
15. **Bestätigt (05.11., P, Review-Befund 9): Natürliche Sortierung** der
    Dateinamen ist festgelegt (Ziffernblöcke numerisch, Groß-/Kleinschreibung
    ignoriert, Gleichstand nach rohem Byte-String) und wird von Box und
    HA-Integration gleich benutzt. Legt HA `serie.json` für einen Ordner ohne
    Datei an, ist die `id` der Ordnername; Zeiger und Zuordnungen bleiben.
16. **Bestätigt (05.11., P, Review-Befund 8): Bestätigung nur bei Übereinstimmung
    von `zuletzt` und `art`;** HA ignoriert die leere (löschende) Nachricht auf
    `…/unknown/<uid>`.
17. **Bestätigt (05.11., P, Review-Befund 14): Eine neue Liste beginnt mit
    Revision 1;** Fenster mit `bis` = `von` sind ungültig.
18. **Offen: Zeitzonenname unbekannt** macht die ganze Liste ungültig; die Box
    braucht dafür eine Zeitzonendatenbank (`tzdata`). Ordnernamen, die keine
    gültige ID sind, werden nicht gespielt.
19. **Offen:** `position_s` wird auf 1 Nachkommastelle abgerundet (nicht
    gerundet), damit der gespeicherte Zeiger nie weiter vorn liegt als die
    tatsächliche Position.
20. **Bestätigt (05.11., P): Tonpegel in `config.json`:** optionale Felder
    `ton_pegel` und `hinweis_pegel` (Vorgabe 15), 0 bis 100. **Seit Entscheidung J (09.11.)
    hat `ton_pegel` keine Wirkung mehr** (vorher Vorgabe 40) und `hinweis_pegel` hat die
    Untergrenze 10 (vorher 5); beides steht in der Tabelle oben. Sie
    ergänzen nur optionale Felder (damals blieb `schema_version` 1; seit Entscheidung F,
    05.11., ist sie 2, Punkt 22). Regel für die
    Wirkung: `core-interface.md`, Abschnitt 8.1.
21. **Bestätigt (05.11., P): `zuletzt` in `unknown.json`** hat Millisekunden-
    Auflösung (ISO 8601 mit Millisekunden); der `ack` gibt den Wert unverändert
    zurück (`mqtt-v1.md`).
22. **Bestätigt (05.11., Entscheidung F, T/P): Ziel einer Zuordnung.** Eine
    Zuordnung hat ein Feld `ziel` mit `typ` `serie`, `folge` oder `aktion`
    (`config.json`, Abschnitt 2). Das ist eine inkompatible Änderung (Feld
    verschoben, Pflichtfeld neu), deshalb `schema_version` 2 mit Migration
    (1.5). Die Überraschungs-Serie verhält sich wie ein Ziel `serie`.
23. **Bestätigt (05.11., Entscheidung F, T): Zeiger mit Track.** `resume.json`
    Version 2 trägt je Serie den Track und je (Serie, Folge) einen eigenen
    Folgen-Zeiger. Ist eine Folge zu Ende, springt ihr Folgen-Zeiger auf Track
    0 / 0 s zurück, damit das nächste Auflegen sie **von vorn** spielt. Alte
    Einträge (Version 1) gelten als Track 0.
24. **Bestätigt (05.11., Entscheidung F, T): Folge auf der Platte.** Eine Folge
    ist eine Datei oder ein Unterordner mit mehreren Tracks; die Tracks ordnet
    die natürliche Sortierung, Dotfiles werden ignoriert, es gilt dieselbe
    Endungsliste. `serie.json.folgen` nennt Folgen mit Namen (Abschnitt 5).
25. **Offen (05.11., Entscheidung F, P): Fehlende Folge oder fehlender Track.**
    Ein Folgen-Tobie auf eine Folge, die es auf der Box nicht gibt, spielt wie
    bei fehlender Serie die Überraschungs-Serie (`folge_fehlt`); hat eine Folge
    jetzt weniger Tracks als der Zeiger meint, gilt Track 0 / Position 0
    (`zeiger_track_fehlt`). Beides folgt Punkt 14 und ist von Tobias noch nicht
    bestätigt.
26. **Bestätigt (09.11., P, Vorgabe 10 des Vertrags W): Tobie-Name.** Optionales Feld
    `name` je Zuordnung in `config.json` und `tobibox/config` (Abschnitt 2); die Box
    ignoriert es. Additiv, `schema_version` bleibt 2.
27. **Bestätigt (09.11., P, Entscheidung M): `serie.json` hat optionale Felder**
    `pruefen`, `pruefen_gruende` und `folgen_info` (Anzeigename, Nummer, Datum je
    Folge). Umbenennen ändert nur Anzeigenamen. Additiv, `schema_version` bleibt 1.
28. **Bestätigt (09.11., P, Vorgabe 15): Papierkorb-Eintrag** als Ordner
    `_papierkorb/<id>/` mit `meta.json` und `inhalt/` (Abschnitt 9).
29. **Bestätigt (09.11., P, Entscheidung M): Eingang `eingang/` neben `medien/`;**
    `_…`-Ordner und `eingang` in `medien/` sind keine Serien; Eingang, `_upload/` und
    `_papierkorb/` werden nicht gesynct (Abschnitte 5 und 10).
30. **Bestätigt (09.11., T, Entscheidung N): Lesezeichen mit Ablauf.** `config.json` hat das optionale Feld
    `lesezeichen_tage` (0 bis 365, Vorgabe 14, `0` = nie), `resume.json` je Zeiger das optionale Feld
    `benutzt_am`. Ein Zeiger ohne `benutzt_am` läuft nie ab. Beides additiv, `schema_version` bleibt 2
    (Abschnitte 2 und 3, `core-interface.md` 6.3 und 9 Punkt 33).
31. **Bestätigt (10.11., Tobias, Ein/Aus R4, R10): Tondatei `lader.wav` und Marke des Frühtons.** Neue Tondatei `box/sounds/lader.wav`
    (kurz, −18 LUFS wie die übrigen Töne, mit Eintrag in `box/lautheit.json`; erzeugt von `box/tools/make_sounds.py`). Der Ton `lader` hat den Pegel von
    `hinweis` (`hinweis_pegel`); der frühe Start-Ton `start.wav` des Frühdienstes den eines gewöhnlichen Tons (R10). Die flüchtige Marke
    `/run/tobibox/fruehton` ist in Abschnitt 1.6 beschrieben. Kein Schema ändert sich, `schema_version` bleibt.
