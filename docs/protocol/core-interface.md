# Kern-Schnittstelle (`core-interface`), Version 1

*   **Status:** Vertrag Stufe 0, Entwurf zur Prüfung durch einen Goldfisch
*   **Grundlage:** `docs/designs/box-software.md` (Baustein 3, „Kern-Zustände“,
    „Lautstärke“, „Uhr und Zeitquelle“, „Datenmodell und Dateien“)
*   **Eigentümer der Typen:** `box/src/tobibox/events.py`. `core.py` und die
    Teilautomaten **benutzen** die Typen nur. Wer einen Typ ändern will, wendet
    sich an die Projektleitung.
*   **Zusammenhang:** Zeilen des Lesers: `reader-v1.md`. Dateien und Schemas:
    `data-model.md`. MQTT: `mqtt-v1.md`.

Die **Tabellen „Wiedergabe-Sitzung“, „Lernmodus“, „Ruhe-Regeln“ und
„Strom / Leerlauf“** in „Kern-Zustände“ des Designs sind Teil dieses Vertrags
und gelten unverändert. Dieses Dokument legt fest, **wie** die Teilautomaten
aufgerufen werden, **welche Ereignisse und Befehle** es gibt, und ergänzt die
Fälle, die die Tabellen offenlassen (Abschnitt 9).

## 1. Grundsätze

1.  Der Kern ist **reine Logik**: keine Datei, kein Netz, keine Uhr, kein
    Zufall, kein `print`. Gleiche Eingaben ergeben gleiche Ausgaben.
2.  Ereignisse und Befehle sind **unveränderliche** Werte
    (`@dataclass(frozen=True, slots=True)`). Zustände ebenso.
3.  Alle Feldnamen sind ASCII (`ae`, `oe`, `ue`, `ss`).
4.  Alles, was zufällig oder uhrabhängig ist, kommt von außen: die Vorgangs-ID
    erzeugt das Modul `reader`, die Zeit liefert `clock`.
5.  Ein Ereignis, das ein Teilautomat nicht kennt, ändert dessen Zustand nicht
    und erzeugt keine Befehle. Unbekannte Ereignistypen sind kein Fehler.

## 2. Zeit: die Uhr als Parameter

Jeder Aufruf bekommt die Zeit als Parameter `jetzt` vom Typ `Jetzt`.
Der Kern fragt nie selbst eine Uhr.

| Feld | Typ | Bedeutung |
|---|---|---|
| `mono` | `float` | monotone Uhr in Sekunden, beliebiger Nullpunkt, springt nie rückwärts. **Alle Dauern und Fristen** (Leser-Frist 3 s, MPD-Frist 5 s, Lernmodus 2 min, Gute-Nacht-Timer, Leerlauf 20 min, Zeiger alle 30 s) laufen auf `mono`. |
| `wall` | `float` | Wanduhr als UTC-Sekunden seit 1970. Nur für Leise-Zeiten, Ablaufzeit von HA-Befehlen und Zeitstempel im Ereignisprotokoll und in `unknown.json`. |
| `zeit_quelle` | `Literal["system","rtc","ntp","unbekannt"]` | woher `wall` stammt (`system` = Systemuhr am Mac) |
| `zeit_ok` | `bool` | `wall` ist vertrauenswürdig (Mac: immer `True`; Pi: RTC beim Start gelesen oder NTP seit dem Start synchron) |

*   Das Modul `clock` liefert `Jetzt` (Uhr im Betrieb, simuliert in Tests).
*   `app.py` bildet für jedes Ereignis genau **ein** `Jetzt` zum Zeitpunkt, an
    dem das Ereignis in die Ereignisschleife gelangt, und reicht es dem Kern.
*   **Takt:** `app.py` speist alle `TAKT_S` = 0,1 s das Ereignis `Takt()` ein
    (Zeitgeber sind Ereignisse; ein fristgenauer Zeitgeber ist nicht vorgesehen).
    Zeitgesteuerte Übergänge geschehen, wenn bei einem Aufruf `jetzt.mono ≥ Frist`
    gilt, **nie** über eine eigene Uhr. Die Auflösung aller Fristen ist deshalb
    `TAKT_S`: eine Frist löst höchstens `TAKT_S` nach ihrem Ablauf aus. Fällt die
    Ereignisschleife kurz aus, fallen Takte aus; Fristen bleiben richtig, weil sie
    auf `jetzt.mono` verglichen werden. Rampen (Ausblenden, Absenken) laufen in
    Schritten von `TAKT_S` (3 s ergeben 30 Lautstärke-Stufen).
*   Ändert sich `zeit_ok` oder `zeit_quelle`, kommt zusätzlich das Ereignis
    `ZeitquelleGeaendert` (Abschnitt 3.7); die Teilautomaten dürfen sich aber
    nicht darauf verlassen, sondern lesen `jetzt.zeit_ok` bei jedem Aufruf.

## 3. Ereignisse

Alle Ereignisse sind Unterklassen von `Ereignis`. Die Tabellen nennen den Typ,
die Felder und die Quelle (das Modul, das den Wert in die Ereignisschleife gibt).

### 3.1 Leser (Quelle `reader`)

| Ereignis | Felder | Bedeutung |
|---|---|---|
| `LeserHallo` | `proto: int`, `fw: str`, `build: str`, `pn5180: str` | gültiges `HELLO` (beim Start der Firmware oder auf `PING`). |
| `Aufgelegt` | `uid: str`, `typ: Literal["ntag","iso15693"]`, `tonie: bool`, `seq: int`, `vorgang: str` | `PLACED`. `uid` ist die kanonische Kennung, unverändert. |
| `Gesperrt` | `seq: int`, `vorgang: str` | `LOCKED` (nicht zuordenbar, keine Kennung). |
| `Abgehoben` | `seq: int`, `vorgang: str \| None` | `REMOVED`. `vorgang` ist der des zugehörigen Auflegens, `None`, wenn `reader` keines kennt (nur nach einem Neustart des Dienstes oder wenn das zugehörige Auflegen verloren ging; **nicht** nach einem `HELLO`, siehe unten). |
| `LeserHerzschlag` | `present: bool`, `up_s: int`, `polls: int`, `hits: int`, `rejected: int`, `errors: int`, `cycle_ms: int` | `HB`. |
| `LeserAlarm` | `grund: Literal["kein_herzschlag","getrennt","hello_timeout","proto_unbekannt"]` | Wächter-Alarm oder Verbindungsverlust; **ein** Alarm je Ausfall (Gründe und Regel: `reader-v1.md`, Abschnitt 12). `reader` verbindet sich danach selbst neu. |
| `LeserFehler` | `code: str`, `detail: str`, `schwere: Literal["fehler","warnung","hinweis"]` | `ERR`-Zeile des Lesers. `reader` setzt `schwere` aus der Tabelle in `reader-v1.md`, Abschnitt 7 (unbekannter Code: `warnung`). Die Sitzung wertet das Ereignis nicht aus; es dient dem Status (Abschnitt 12). |

*   **Vorgangs-ID:** `reader` erzeugt sie beim Empfang von `PLACED` oder
    `LOCKED`: 8 Zeichen `[0-9a-f]` aus einer Zufallsquelle. `reader` merkt sie
    sich bis zum zugehörigen `REMOVED` und gibt sie in `Abgehoben` mit.
    Ein `PLACED` nach einem `REMOVED` bekommt eine neue ID.
*   **Wiedermeldung nach `HELLO` behält die ID.** Kommt nach einem gültigen
    `HELLO` als **erste** `PLACED`/`LOCKED`-Zeile eine Meldung derselben
    Identität (gleiche Kennung bzw. beide `LOCKED`) wie die offene (noch nicht
    abgehobene) Figur, ist das eine **Wiedermeldung**: `reader` behält die
    bestehende Vorgangs-ID. Das betrifft die Meldung auf `PING` und die
    Meldung nach einem Neustart der Firmware. **Bestätigt (05.11.):** Dasselbe
    gilt für die **erste** `PLACED`/`LOCKED`-Zeile mit `seq=0` oder nach einem
    erkannten `seq_reset` (`reader-v1.md`, Abschnitt 5), auch wenn kein `HELLO`
    ankam (das `HELLO` ging verloren, die Firmware wurde neu gestartet): bei
    gleicher Identität wie die offene Figur ist es eine Wiedermeldung, `reader`
    behält die ID. Jedes andere `PLACED`/`LOCKED` (andere Identität, oder bereits
    abgehoben, oder weder `HELLO` noch `seq=0` noch `seq_reset` davor, etwa nach
    verlorenem `REMOVED`) bekommt eine neue ID. Ein `REMOVED` gibt die ID
    frei. `vorgang=None` im `Abgehoben` entsteht deshalb nur, wenn `reader` gar
    keine ID kennt; die Aussage „direkt nach `HELLO` ist `vorgang` leer“ gilt
    nicht.
*   Alle `seq`-Prüfungen macht `reader` (siehe `reader-v1.md`, Abschnitt 5). Der
    Kern wertet `seq` nicht aus.

### 3.2 Player (Quelle `player`)

| Ereignis | Felder | Bedeutung |
|---|---|---|
| `FolgeZuEnde` | `serie_id: str`, `datei: str` | MPD hat die Folge zu Ende gespielt und **gestoppt**. MPD startet nie von selbst die nächste Folge (die Warteschlange enthält nur die aktuelle). `serie_id` und `datei` sind die Werte des letzten `Abspielen`. |
| `PlayerPosition` | `serie_id: str`, `datei: str`, `position_s: float`, `spielt: bool` | Abspielposition in Sekunden (ohne Rücksprung). Der Player sendet sie alle `POSITION_INTERVAL_S` = 1,0 s, solange etwas spielt, und **einmal sofort** nach jedem `Pausieren`, jedem `Abspielen` und jedem Folgenende (dann mit der Endposition). |
| `PlayerFehler` | `serie_id: str \| None`, `datei: str \| None`, `art: Literal["datei_fehlt","datei_unlesbar","mpd_fehler"]`, `detail: str` | Wiedergabefehler. `datei_fehlt`: Datei nicht im MPD-Bestand. `datei_unlesbar`: MPD kann sie nicht dekodieren. `mpd_fehler`: sonstiger Fehler eines MPD-Befehls. |
| `PlayerVerbindung` | `ok: bool` | Verbindung zu MPD verloren (`False`) oder wiederhergestellt (`True`). `player` verbindet sich selbst neu. |

Die Position ist eine Eigenschaft des Players, der Kern hält die zuletzt
gemeldete (`PlayerPosition`) im Zustand der Sitzung. Beim Abheben benutzt der
Kern diese Position für `ZeigerSpeichern`; sie ist höchstens
`POSITION_INTERVAL_S` alt.

### 3.3 Start und Daten (Quelle `app`, `store`, `library`, `ha`)

| Ereignis | Felder | Quelle | Bedeutung |
|---|---|---|---|
| `GeraeteEinstellungen` | `lautstaerke_max: int`, `lautstaerke_start: int`, `lautstaerke_kopfhoerer: int` | `app` aus `tobibox.toml` | je 0 bis 100. Der Kern setzt die Grenze `global` und die Startlautstärke daraus (Abschnitt 8). Kommt als **erstes** Ereignis. |
| `KonfigGeladen` | `konfig: Konfig` | `app` beim Start (aus `config.json`), `ha` nach angenommener Liste | Zuordnungen, Leise-Zeiten, Gute-Nacht-Einstellungen (Typen in 3.8). Ersetzt die bisherige Konfiguration vollständig. |
| `BibliothekGeladen` | `serien: tuple[Serie, ...]` | `app` beim Start (aus `library`), `library` nach jedem Sync und nach Änderungen im Medienordner | Alle Serien mit ihren Folgen in der maßgeblichen Reihenfolge. Ersetzt die bisherige Bibliothek. |
| `ResumeGeladen` | `zeiger: tuple[Zeiger, ...]` | `app` beim Start (aus `resume.json`) | Gespeicherte Zeiger. Kommt einmal. |
| `Bereit` | – | `app` | Alle vorigen Daten sind geliefert und MPD ist erreichbar. Bis `Bereit` hält `app` alle Ereignisse des Lesers in der Warteschlange zurück (Reihenfolge bleibt). Bei `Bereit` spielt der Kern den Start-Ton (CUJ 20: eine beim Start liegende Figur kommt als `Aufgelegt` direkt danach). |

### 3.4 Home Assistant (Quelle `ha`; in Stufe 2 `sim`)

Alle HA-Befehle tragen eine Ablaufzeit. Der Kern prüft sie mit `jetzt.wall` und
`jetzt.zeit_ok`; wer welche Prüfung macht, steht in Abschnitt 9, Punkt 9.

| Ereignis | Felder | Bedeutung |
|---|---|---|
| `HaLernmodus` | `befehl_id: str`, `gueltig_bis: float` | Lernmodus starten. `gueltig_bis` = `erzeugt + ttl_s` als UTC-Sekunden. |
| `HaLernmodusAbbruch` | `befehl_id: str`, `gueltig_bis: float` | Lernmodus abbrechen. `gueltig_bis` = `erzeugt + ttl_s` des Befehls `lernen_abbrechen`. |
| `HaSyncAnstossen` | `befehl_id: str`, `gueltig_bis: float` | Sync jetzt. |
| `HaUpdateAnstossen` | `befehl_id: str`, `version: str`, `gueltig_bis: float` | Update installieren. |
| `HaVerbindung` | `ok: bool` | Verbindung zum Broker steht (`True`) oder ist weg. **Geht nicht an den Kern** (kein Teilautomat verarbeitet sie), sondern nur an den Statussammler und `selftest` (Abschnitt 6.5 und 12). |
| `Bestaetigt` | `id: str`, `grund: str`, `zuletzt: str`, `art: Literal["unbekannt","gelernt"]` | Bestätigung von HA für einen gemeldeten Eintrag (Abschnitt 7). `zuletzt` und `art` sind die Werte der veröffentlichten Meldung, die HA bestätigt. **Geht nicht an den Kern**, sondern an `outbox` (`app` verteilt). |

### 3.5 Bedienung und Kopfhörer (Quelle `controls`, `headphones`; in der Simulation `sim`)

| Ereignis | Felder | Bedeutung |
|---|---|---|
| `Hauptknopf` | `art: Literal["kurz","lang"]` | kurzer oder langer Druck. |
| `Weiter` | – | nächste Folge. |
| `Zurueck` | – | vorige Folge. |
| `LautstaerkeDrehen` | `delta: int` | Drehregler, in Prozentpunkten (positiv lauter). |
| `Kopfhoerer` | `steckt: bool` | Stecker erkannt (`True`) oder gezogen. |

### 3.6 Strom, Netz, Sync, Update

| Ereignis | Felder | Quelle | Bedeutung |
|---|---|---|---|
| `LaderGeaendert` | `am_lader: bool` | `power` | |
| `AkkuStand` | `prozent: int` | `power` | 0 bis 100; nur zur Information und für `sync`. |
| `AkkuTiefstand` | – | `power` | Akku kritisch leer, Box nicht am Lader. |
| `NetzKlasse` | `klasse: Literal["home","hotspot","offline"]` | `net` | bei Änderung und einmal beim Start. |
| `SyncGestartet` | – | `sync` | |
| `SyncFertig` | `neu: int`, `geloescht: int` | `sync` | `neu` = übertragene Dateien. |
| `SyncAbgebrochen` | `grund: str` | `sync` | z. B. `quelle_leer`, `zu_viele_loeschungen`, `kein_platz`, `akku_tiefstand`, `netz_weg`, `regel`. |
| `UpdateGestartet` | `version: str` | `update` | |
| `SelbsttestErgebnis` | `bestanden: bool`, `grund: str \| None` | `selftest` | |

### 3.7 Zeit und Zeitquelle

| Ereignis | Felder | Quelle | Bedeutung |
|---|---|---|---|
| `Takt` | – | `app` | alle `TAKT_S`. |
| `ZeitquelleGeaendert` | `quelle: Literal["system","rtc","ntp","unbekannt"]`, `vertrauenswuerdig: bool` | `power`, `net` | |

### 3.8 Hilfstypen

| Typ | Felder |
|---|---|
| `Serie` | `id: str`, `name: str`, `typ: Literal["normal","ueberraschung"]`, `ordner: str` (Pfad relativ zum Medienordner), `folgen: tuple[str, ...]` (Dateinamen in maßgeblicher Reihenfolge, nur vorhandene) |
| `Zeiger` | `serie_id: str`, `datei: str`, `index: int` (Nummer der Folge in `folgen`, ab 0, Hinweis für den Fall einer fehlenden Datei), `position_s: float` (≥ 0, ohne Rücksprung), `zaehler: int` |
| `Zuordnung` | `typ: Literal["serie","aktion"]`, `serie_id: str \| None`, `aktion: Literal["status","gute_nacht"] \| None` |
| `Fenster` | `id: str`, `tage: tuple[int, ...]` (1 = Montag bis 7 = Sonntag), `von: str`, `bis: str` (`"HH:MM"`, Ortszeit), `wirkung: Literal["leiser","stumm"]`, `grenze: int \| None` |
| `LeiseZeiten` | `zeitzone: str` (IANA), `fenster: tuple[Fenster, ...]` |
| `GuteNacht` | `timer_min: int`, `ausblenden_s: int` |
| `Konfig` | `revision: int`, `liste_id: str`, `zuordnungen: Mapping[str, Zuordnung]` (Schlüssel = Kennung), `leise_zeiten: LeiseZeiten`, `gute_nacht: GuteNacht` |
| `Eintrag` (von `outbox.offen()`) | `uid: str`, `art: Literal["unbekannt","gelernt"]`, `zuerst: str`, `zuletzt: str`, `anzahl: int`, `zeit_ok: bool`, `befehl_id: str \| None` (die Felder von `unknown.json`, `data-model.md` Abschnitt 4, plus der Schlüssel `uid`) |

Wertebereiche und Bedeutung der Felder: `data-model.md`. `events.py` übernimmt
die Werte aus den Schemas; die **Namen weichen an einigen Stellen ab** und
werden so abgebildet:

| JSON (`data-model.md`) | Typ in `events.py` |
|---|---|
| `resume.json`: `serien` (Objekt, Schlüssel = Serien-ID) | `ResumeGeladen.zeiger: tuple[Zeiger, ...]`, ein `Zeiger` je Eintrag |
| `serien.<id>` (Schlüssel) | `Zeiger.serie_id` |
| `serien.<id>.folge` | `Zeiger.datei` |
| `serien.<id>.index`, `.position_s`, `.zaehler` | `Zeiger.index`, `.position_s`, `.zaehler` (gleiche Namen) |
| `config.json`: `zuordnungen.<uid>.serie` | `Zuordnung.serie_id` (und `typ`, `aktion` gleich) |
| `zuordnungen` (Objekt, Schlüssel = Kennung) | `Konfig.zuordnungen: Mapping[str, Zuordnung]` |
| `leise_zeiten.fenster[].tage / von / bis / wirkung / grenze / id` | `Fenster.tage / von / bis / wirkung / grenze / id` (gleiche Namen; `tage` als `tuple`) |
| `leise_zeiten.zeitzone` (fehlt: `Europe/Berlin`) | `LeiseZeiten.zeitzone` (immer gesetzt) |
| `gute_nacht.timer_min`, `.ausblenden_s` | `GuteNacht.timer_min`, `.ausblenden_s` |
| `config.json`: `erzeugt_am`, `schema_version` | kein Feld in `Konfig` (nur Anzeige bzw. Format) |
| `serie.json`: `id`, `name`, `typ`, `ordner` (aus dem Pfad), `folgen` | `Serie.id`, `.name`, `.typ`, `.ordner`, `.folgen` |

`position_s` wird beim Speichern auf **eine Nachkommastelle abgerundet**
(`floor(x · 10) / 10`), damit der gespeicherte Zeiger nie weiter vorn liegt als
die tatsächliche Position. „Unverändert“ im Sinne von `ZeigerSpeichern` heißt: gleiche Datei,
gleicher Index und gleiche so abgerundete Position.

### 3.9 Interne Ereignisse (zwischen Teilautomaten)

Teilautomaten melden einander Dinge, indem sie ein **internes Ereignis**
zurückgeben. `core` nimmt sie aus der Ausgabe heraus und gibt sie in derselben
Verarbeitung an alle Teilautomaten weiter (Abschnitt 6.1). Sie sind
Unterklassen von `InternesEreignis` und verlassen den Kern nie.

| Ereignis | Felder | Sender → Empfänger | Bedeutung |
|---|---|---|---|
| `SitzungGeaendert` | `zustand: str`, `figur_liegt: bool`, `spielt: bool`, `serie_id: str \| None` | `session` → `idle`, `bedtime` | Zustand der Wiedergabe-Sitzung hat sich geändert. `figur_liegt` gilt auch für Aktionskarten. |
| `AktionAusgeloest` | `aktion: Literal["status","gute_nacht"]`, `vorgang: str` | `session` → `bedtime` (und `core` für `status`) | Aktionskarte wurde aufgelegt. |
| `LernenGeaendert` | `aktiv: bool` | `learn` → `idle`, `session` | Lernmodus beginnt oder endet. |
| `StummBeginnt` | – | `quiet` → `session` | ein „stumm“-Fenster beginnt. Bei nicht vertrauenswürdiger Zeit gibt es nie „stumm“ (`data-model.md`, Abschnitt 2). |
| `StummEndet` | – | `quiet` → `session` | ein „stumm“-Fenster endet. |
| `GrenzeGesetzt` | `name: str`, `prozent: int \| None` | `quiet`, `bedtime`, `session` → `core` | setzt (`int`) oder löscht (`None`) die benannte Lautstärke-Grenze (Abschnitt 8). `core` behandelt sie selbst, die Teilautomaten sehen sie nicht. |
| `LautstaerkeGeaendert` | `wirksam: int` | `core` → alle Teilautomaten | die **wirksame Lautstärke** (`klemmen(wunsch, grenzen)`) hat sich geändert (und einmal nach `GeraeteEinstellungen`). Die Teilautomaten sind reine Funktionen und kennen `wunsch` und `grenzen` nicht; sie merken sich den zuletzt gemeldeten Wert und benutzen ihn als **Startwert einer Rampe** (Abschnitt 8) und für die Entscheidung „laute Wiedergabe“ (`wirksam` größer als die Zielgrenze). |
| `GuteNachtEnde` | – | `bedtime` → `session` | Das Ausblenden von „Gute Nacht“ hat die Lautstärke 0 erreicht; die Sitzung pausiert (9, Punkt 6). |
| `HerunterfahrenAngefordert` | `grund: Literal["leerlauf","hauptknopf","akku_tiefstand"]` | `idle` → `session`, `core` | Herunterfahren ist beschlossen. `session` pausiert und speichert den Zeiger; `core` hängt danach den Befehl `Herunterfahren` an. |

## 4. Befehle

Alle Befehle sind Unterklassen von `Befehl`. `app.py` führt sie aus. Die Tabelle
nennt, wer sie ausführt.

| Befehl | Felder | Ausführer | Bedeutung |
|---|---|---|---|
| `LautstaerkeSetzen` | `prozent: int`, `grenze: int` | `player` | MPD-Lautstärke setzen. Immer `0 ≤ prozent ≤ grenze ≤ 100`. `player` klemmt zusätzlich selbst auf `grenze`, falls ein Aufrufer sich irrt. |
| `AusgangWaehlen` | `ausgang: Literal["lautsprecher","kopfhoerer"]` | `player` | Ausgang umschalten (Mac: nur protokolliert). |
| `Abspielen` | `serie_id: str`, `ordner: str`, `datei: str`, `position_s: float`, `vorgang: str \| None` | `player` | Warteschlange leeren, **nur diese Folge** laden, auf `position_s` springen (`seek`), spielen. `position_s` enthält schon den Rücksprung (Abschnitt 6.3). Der Pfad für MPD ist `ordner + "/" + datei`. |
| `Pausieren` | `grund: Literal["abgehoben","folgenende","knopf","stumm","gute_nacht","leser_unbekannt","fehler","herunterfahren"]` | `player` | Pause. Ist MPD schon gestoppt (Folgenende), ist der Befehl wirkungslos. Danach sendet der Player sofort `PlayerPosition`. |
| `ZeigerSpeichern` | `serie_id: str`, `datei: str`, `index: int`, `position_s: float`, `grund: Literal["pause","folgenende","figurwechsel","periodisch","herunterfahren"]` | `store` (`resume.json`) | Zeiger schreiben, `zaehler` dieser Serie um 1 erhöhen. `position_s` ist abgerundet auf 1 Nachkommastelle (Abschnitt 3.8). `store` schreibt nicht, wenn Datei, Index und Position unverändert sind. |
| `TonSpielen` | `ton: Literal["start","unbekannt","fehler","hinweis","lernen_beginn","lernen_ende","akku_leer","pruef_ok","pruef_fehler"]` | `sounds` | kurzer Rückmeldeton (Datei `box/sounds/<ton>.wav`, `pruef_*` in AP 2.3). |
| `StatusPruefen` | `vorgang: str \| None` | `selftest` | Prüfpunkte Leser, Medien, Netz, Speicher in dieser Reihenfolge nach den Kriterien aus Abschnitt 12.3 prüfen und je Punkt `pruef_ok` oder `pruef_fehler` spielen (Status-Admin-Karte, CUJ 11). `selftest` wertet aus und lässt `sounds` die Töne spielen; ausgeführt wird der Befehl nur von `selftest`. |
| `Melden` | `art: Literal["unbekannt","gelernt"]`, `uid: str`, `befehl_id: str \| None` | `outbox` | Eintrag in `unknown.json`, Veröffentlichung an HA, Löschen erst nach Bestätigung (Abschnitt 7). `befehl_id` ist bei `gelernt` die ID des Lernbefehls, sonst `None`. |
| `EreignisSenden` | `art: Literal["fehler","befehl_abgelehnt"]`, `daten: Mapping[str, str \| int \| bool \| None]` | `ha` | Meldung an HA ohne Bestätigung (`…/event`). `befehl_abgelehnt` hat `daten = {"befehl": <lernen\|sync\|update>, "befehl_id": <str>, "grund": <bedingung\|zeit_unsicher>}` und optional `"detail"`; `lernen_abbrechen` wird nie abgelehnt. Die Meldungen `liste_abgelehnt`, `v_unbekannt` und `befehl_unbekannt` entstehen **nicht** im Kern, sondern direkt in `ha` (Abschnitt 9, Punkt 9). |
| `ZustandMelden` | `sitzung: str`, `strom: Literal["aktiv","leerlauf","herunterfahren"]`, `serie_id: str \| None`, `lernmodus: bool`, `ruhe: Literal["normal","leiser","stumm"]`, `gute_nacht: Literal["aus","laeuft","ausblenden"]`, `figur_liegt: bool` | `ha` (Statussammler, Abschnitt 12), `led` | Sammelzustand für Status-Sensoren und LED-Ring. `core` erzeugt ihn bei jeder Änderung (6.1, Schritt 6). Den Status-JSON baut nicht der Kern, sondern der Statussammler in `ha` (Abschnitt 12). |
| `LeserPing` | – | `reader` | `PING` an den Leser senden. |
| `SyncStarten` | `grund: Literal["ha","start_lader"]` | `sync` | Sync anfordern. `sync` entscheidet nach der Netz-Regel (Heim / Hotspot und Akku), ob er läuft; wenn nicht, meldet er `SyncAbgebrochen(grund="regel")`. |
| `SyncAbbrechen` | `grund: Literal["akku_tiefstand"]` | `sync` | laufenden Sync abbrechen. |
| `UpdateStarten` | `befehl_id: str`, `version: str` | `update` | Update ausführen. |
| `Herunterfahren` | `grund: Literal["leerlauf","hauptknopf","akku_tiefstand"]` | `power` | Herunterfahren. In der Simulation wird nur protokolliert. |
| `Protokoll` | `baustein: str`, `ebene: Literal["DEBUG","INFO","WARNING","ERROR"]`, `ereignis: str`, `ergebnis: str`, `vorgang: str \| None`, `daten: Mapping[str, str \| int \| float \| bool \| None]` | `eventlog` | Eine Zeile im Ereignisprotokoll (Schema: `data-model.md`). Die Zeitfelder setzt `eventlog`. Der Kern schreibt nie selbst. |

Es gibt **keinen** Befehl „Fortsetzen“: Spielen aus der Pause ist ein neues
`Abspielen` am gespeicherten Zeiger.

## 5. Aufrufmuster

### 5.1 Teilautomat

Jeder Teilautomat ist ein Modul mit genau diesen drei Namen:

```
Zustand                                             # unveränderlicher Zustandstyp des Moduls
neuer_zustand() -> Zustand                          # Anfangszustand
step(zustand: Zustand, ereignis: Ereignis | InternesEreignis, jetzt: Jetzt)
    -> tuple[Zustand, tuple[Befehl | InternesEreignis, ...]]
kennzeichen(zustand: Zustand) -> str                # kurzer Name des Zustands für ZustandMelden und Protokoll
```

*   `step` ist eine **reine Funktion**: kein Zugriff auf Dateien, Netz, Uhr oder
    Zufall; der Zustand wird nicht verändert, sondern ein neuer zurückgegeben.
*   Die Reihenfolge der zurückgegebenen Befehle ist die Reihenfolge, in der der
    Teilautomat sie meint; `core` ordnet sie danach (6.1).
*   Ein Teilautomat darf mehrere Befehle und mehrere interne Ereignisse
    zurückgeben, auch keine.

### 5.2 Die vier Teilautomaten

| Modul | Name im Design | Zustände (`kennzeichen`) | Verarbeitet (Ereignisse) | Gibt aus |
|---|---|---|---|---|
| `session.py` | Wiedergabe-Sitzung | `leer`, `spielt`, `pausiert`, `beendet`, `gehalten`, `unbekannt` | `GeraeteEinstellungen`, `KonfigGeladen`, `BibliothekGeladen`, `ResumeGeladen`, `Bereit`, `Aufgelegt`, `Gesperrt`, `Abgehoben`, `LeserHallo`, `LeserAlarm`, `LeserHerzschlag`, `LautstaerkeGeaendert`, `FolgeZuEnde`, `PlayerPosition`, `PlayerFehler`, `PlayerVerbindung`, `Hauptknopf`, `Weiter`, `Zurueck`, `Kopfhoerer`, `Takt`, `StummBeginnt`, `StummEndet`, `LernenGeaendert`, `GuteNachtEnde`, `HerunterfahrenAngefordert` | `Abspielen`, `Pausieren`, `ZeigerSpeichern`, `TonSpielen`, `Melden`, `AusgangWaehlen`, `LeserPing`, `Protokoll`; intern `SitzungGeaendert`, `AktionAusgeloest`, `GrenzeGesetzt` (`kopfhoerer`, `ausblenden`) |
| `learn.py` | Lernmodus | `aus`, `lernt` | `HaLernmodus`, `HaLernmodusAbbruch`, `Aufgelegt`, `Gesperrt`, `Takt` | `TonSpielen`, `Melden`, `EreignisSenden`, `Protokoll`; intern `LernenGeaendert` |
| `quiet.py` und `bedtime.py` | Ruhe-Regeln | `quiet`: `normal`, `leiser`, `stumm`; `bedtime`: `aus`, `laeuft`, `ausblenden` | `KonfigGeladen`, `Takt`, `ZeitquelleGeaendert`, `LautstaerkeGeaendert` (`quiet`); `KonfigGeladen`, `Takt`, `AktionAusgeloest`, `Abgehoben`, `LautstaerkeGeaendert` (`bedtime`) | `Protokoll`; intern `StummBeginnt`, `StummEndet`, `GrenzeGesetzt` (`leise_zeit`, `ausblenden` aus `quiet`; `gute_nacht` aus `bedtime`), `GuteNachtEnde` (aus `bedtime`) |
| `idle.py` | Strom / Leerlauf | `aktiv`, `leerlauf`, `herunterfahren` | `SitzungGeaendert`, `LernenGeaendert`, `Takt`, `Hauptknopf` (lang), `AkkuTiefstand`, `LaderGeaendert`, `NetzKlasse`, `SyncGestartet`, `SyncFertig`, `SyncAbgebrochen`, `UpdateGestartet`, `SelbsttestErgebnis`, `HaSyncAnstossen`, `HaUpdateAnstossen`, `Bereit` | `SyncStarten`, `SyncAbbrechen`, `UpdateStarten`, `EreignisSenden`, `Protokoll`; intern `HerunterfahrenAngefordert` |

Hinweise:

*   `quiet` und `bedtime` sind **zwei Module** (`quiet.py`, `bedtime.py`) mit
    je eigenem Zustand und werden in `core` getrennt geführt; zusammen sind sie
    der „Teilautomat Ruhe-Regeln“ des Designs. Insgesamt hält `core` also fünf
    Zustände: `session`, `learn`, `quiet`, `bedtime`, `idle`.
*   `quiet` und `bedtime` geben **keine** `Pausieren`-Befehle aus. Das Pausieren
    („sanft ausblenden, Pause, Zeiger speichern“) gehört der Sitzung und
    geschieht, wenn `session` `StummBeginnt` bzw. die Grenze `gute_nacht` bei 0
    sieht (siehe 9, Punkt 5 und 6).
*   Die Tabellen des Designs sind die Pflichtinhalte. Jede Zeile hat in
    `box/tests/unit/test_<modul>.py` einen parametrisierten Testfall; die
    Spalten „Ereignis“ und „Befehl“ der Tabellen heißen dort wie in diesem
    Dokument.

### 5.3 Zuordnung von Design-Wörtern zu Ereignissen

| Design | Ereignis |
|---|---|
| `PLACED`, Kennung bekannt/unbekannt | `Aufgelegt` mit `uid` in/nicht in `Konfig.zuordnungen` |
| `PLACED`, Typ `aktion` | `Aufgelegt`, `uid` ist als `Zuordnung(typ="aktion")` eingetragen |
| `LOCKED` | `Gesperrt` |
| `REMOVED` | `Abgehoben` |
| Folge zu Ende | `FolgeZuEnde` |
| Wächter-Alarm (kein `HB`) | `LeserAlarm` |
| `HELLO` | `LeserHallo` |
| Hauptknopf kurz / lang | `Hauptknopf(art=…)` |
| stumm beginnt / endet | `StummBeginnt` / `StummEndet` |
| Uhr erreicht Fenster, Fenster endet | `Takt` mit `jetzt.wall` (`quiet`) |
| Kopfhörer rein / raus | `Kopfhoerer(steckt=…)` |
| HA-Befehl Lernmodus / abbrechen | `HaLernmodus` / `HaLernmodusAbbruch` |
| Frist 2 min | `Takt` mit `jetzt.mono ≥ Frist` |
| Start mit liegender Figur | `Aufgelegt` nach `Bereit` (`app` hält Leser-Ereignisse bis `Bereit` zurück) |
| Akku-Tiefstand | `AkkuTiefstand` |
| Sync, Update oder Lernmodus läuft | Zustandsfelder in `idle` aus `SyncGestartet`/`SyncFertig`/`SyncAbgebrochen`, `UpdateGestartet`/`SelbsttestErgebnis`, `LernenGeaendert` |

## 6. Der Kern (`core.py`)

`core` kombiniert die Teilautomaten. Seine Schnittstelle ist dieselbe wie die
der Teilautomaten:

```
step(zustand: KernZustand, ereignis: Ereignis, jetzt: Jetzt)
    -> tuple[KernZustand, tuple[Befehl, ...]]
```

`KernZustand` enthält die fünf Zustände (`session`, `learn`, `quiet`, `bedtime`,
`idle`), die Lautstärke-Grenzen (`grenzen: Mapping[str,int]`), den Wunsch der
Lautstärke (`wunsch: int`), die zuletzt als `LautstaerkeGeaendert` gemeldete
wirksame Lautstärke, den zuletzt als `LautstaerkeSetzen` **ausgegebenen** Wert
(`ausgegeben`) und die zuletzt gemeldete `ZustandMelden`-Zusammenfassung.
Neue Teilautomaten trägt das Integrations-AP der Stufe in die Liste ein
(`core.py`: `TEILAUTOMATEN`, in fester Reihenfolge).

### 6.1 Ablauf eines Aufrufs

Die Reihenfolge der Teilautomaten ist **fest**: `session`, `learn`, `quiet`,
`bedtime`, `idle`.

1.  Eine Warteschlange `schlange` bekommt das äußere Ereignis.
2.  Solange die Warteschlange nicht leer ist: erstes Ereignis `e` entnehmen.
    *   Ist `e` eine `GrenzeGesetzt`, verarbeitet `core` sie selbst (Abschnitt 8)
        und macht weiter.
    *   Sonst ruft `core` `step` jedes Teilautomaten in fester Reihenfolge mit `e`
        auf und ersetzt dessen Zustand durch den zurückgegebenen.
    *   Interne Ereignisse aus der Ausgabe kommen **hinten** in die Warteschlange.
        Befehle kommen in die Ausgabeliste, in der Reihenfolge Teilautomat →
        Emissionsreihenfolge.
    *   Ist die Warteschlange leer, berechnet `core` die wirksame Lautstärke
        `klemmen(wunsch, grenzen)` (Abschnitt 8). Weicht sie vom zuletzt
        gemeldeten Wert ab, hängt `core` ein `LautstaerkeGeaendert(wirksam)` an
        die Warteschlange; es geht an alle Teilautomaten (sie geben darauf nichts
        aus, was eine neue Rampe oder eine Schleife auslöst). Erst wenn danach
        nichts mehr in der Warteschlange steht, ist die Verarbeitung zu Ende.
        `LautstaerkeSetzen` entsteht einmal **am Ende** der Verarbeitung aus dem
        Nettowert (Abschnitt 8), nicht nach jedem einzelnen `GrenzeGesetzt`.
3.  Schutz gegen Schleifen: Nach 32 verarbeiteten Ereignissen je äußerem
    Ereignis bricht `core` ab, hängt `Protokoll(ebene="ERROR", ereignis="kern_schleife")`
    an und gibt aus, was bis dahin gesammelt ist.
4.  Spezialbehandlung durch `core` (zusätzlich zum Weiterreichen an die
    Teilautomaten):
    *   `GeraeteEinstellungen`: Grenzen `global` und `kopfhoerer`-Wert setzen,
        `wunsch := min(lautstaerke_start, wirksame Grenze)`, `LautstaerkeSetzen`
        ausgeben (Abschnitt 8) und `LautstaerkeGeaendert` an alle Teilautomaten.
    *   `LautstaerkeDrehen(delta)`: `wunsch := clamp(wunsch + delta, 0, wirksame Grenze)`,
        `LautstaerkeSetzen`.
    *   `AktionAusgeloest(status)`: `StatusPruefen(vorgang)`.
    *   `HerunterfahrenAngefordert`: nach Ende der Warteschlange `Herunterfahren(grund)`
        als letzten Befehl anhängen.
    *   `GeraeteEinstellungen` wird zusätzlich an die Teilautomaten weitergegeben
        (`session` braucht `lautstaerke_kopfhoerer`).
5.  Konfliktregeln (6.2) auf die Ausgabeliste anwenden.
6.  `ZustandMelden` anhängen, wenn sich die Zusammenfassung seit dem letzten
    gemeldeten Wert geändert hat (`kennzeichen` der Teilautomaten, Serie,
    `figur_liegt`).
7.  Befehle nach dem Rang in 6.4 **stabil sortieren** und zurückgeben.

### 6.2 Konfliktregeln (nach dem Sammeln, vor dem Sortieren)

1.  **Herunterfahren hat Vorrang** (Reihenfolge im Design: Herunterfahren auf
    Anforderung und Update-Umschaltung vor stumm, vor Ende von Gute Nacht, vor
    Lernmodus, vor Wiedergabe): Enthält die Ausgabe `Herunterfahren`, werden
    `Abspielen`, `SyncStarten`, `UpdateStarten` und `AusgangWaehlen` entfernt.
2.  **Töne unter „stumm“:** Ist `quiet` im Zustand `stumm`, wird jeder
    `TonSpielen` mit `ton ∈ {start, unbekannt, lernen_beginn, lernen_ende, fehler, akku_leer}`
    durch `TonSpielen("hinweis")` ersetzt. `pruef_ok` und `pruef_fehler` bleiben.
3.  **Doppelte Töne:** Mehrere gleiche `TonSpielen` in einer Ausgabe werden zu
    einem. (Beispiel: stumm und Lernmodus gleichzeitig ergeben ein `hinweis`.)
4.  **Doppelte Meldungen:** Mehrere `Melden` mit derselben `uid` werden zu
    einem; `art="gelernt"` gewinnt und behält seine `befehl_id`.
5.  **Mehrere `Abspielen`:** Es bleibt das letzte.
6.  **Lautstärke vor Abspielen:** Steht in der Ausgabe ein `Abspielen` und kein
    `LautstaerkeSetzen`, setzt `core` vor das `Abspielen` ein
    `LautstaerkeSetzen` mit dem aktuellen Wunsch und der wirksamen Grenze,
    **auch wenn** `ausgegeben` schon denselben Wert hat (der Player-Wert kann
    durch Regel 7 oder einen MPD-Neustart abweichen).
7.  **Keine Lautstärke-Rückkehr vor einer Pause:** Enthält die Ausgabe ein
    `Pausieren`, und würde ein `LautstaerkeSetzen` nur deshalb entstehen, weil in
    derselben Verarbeitung die Grenze `ausblenden` oder `gute_nacht` gelöscht
    wurde (der Wert stiege wieder), gibt `core` es **nicht** aus. Der Player
    behält die niedrige Lautstärke während der Pause, `ausgegeben` bleibt der
    niedrige Wert. Erst eine Änderung von `wunsch` oder Regel 6 vor dem nächsten
    `Abspielen` setzt wieder. So springt die Box am Ende von „Gute Nacht“ und
    „stumm“ nie kurz auf volle Lautstärke zurück.

### 6.3 Zeigerregeln, die `session` anwendet

Die Funktionen stehen in `pointer.py` (rein). `session` benutzt sie so:

*   **Auflegen einer Serie:** Zeiger der Serie laden. Gibt es keinen: Folge 1,
    Position 0. Sonst die Folge `datei` des Zeigers, Position
    `max(0, position_s − RUECKSPRUNG_S)` mit `RUECKSPRUNG_S` = 3,0. Steht in der
    Position 0 (nach einem Folgenende), gibt es keinen Rücksprung.
*   **Fehlende Folge** (Datei nicht mehr in `Serie.folgen`): die Folge, die jetzt
    am Platz `Zeiger.index` steht; ist `index` ≥ Länge der Liste, Folge 1.
    Position 0. `Protokoll(WARNING, ereignis="zeiger_folge_fehlt")`. Ist die
    Serie leer: `TonSpielen("fehler")`, `Protokoll`, Zustand wie bei einem
    Fehlschlag (keine Wiedergabe).
*   **Folge zu Ende:** Zeiger auf die nächste Folge, Position 0, nach der letzten
    Folge auf Folge 1; `ZeigerSpeichern(grund="folgenende")`; `Pausieren("folgenende")`;
    Zustand `beendet`.
*   **Überraschungs-Serie** (für unbekannte und gesperrte Figuren): die einzige
    Serie mit `typ="ueberraschung"`. Gibt es keine, mehr als eine oder ist sie
    leer: `TonSpielen("fehler")` und `Protokoll`.
*   **Zuordnung auf eine Serie, die die Box noch nicht kennt** (die `serie_id`
    steht nicht in der Bibliothek; Entscheidung Tobias 05.11.): Die Box spielt die
    **Überraschungs-Serie** (wie bei einer unbekannten Figur, aber **ohne**
    `Melden`: die Figur ist ja zugeordnet) und protokolliert den Grund
    (`Protokoll(WARNING, ereignis="serie_fehlt", daten={"uid": …, "serie": …})`).
    Kommt die Serie später (`BibliothekGeladen`), gilt die Zuordnung beim **nächsten
    Auflegen**; die laufende Überraschungs-Serie wird dadurch nicht gewechselt.
    Gibt es auch keine Überraschungs-Serie, gilt deren Fehlerfall (Fehlerton).
*   Der Zeiger wird nur geschrieben, wenn er sich geändert hat (Datei, Index oder
    Position). `ZeigerSpeichern` trägt den Wert aus `PlayerPosition`.
*   **Periodisch:** Bei `Takt` im Zustand `spielt` gibt `session`
    `ZeigerSpeichern(grund="periodisch")` aus, wenn seit dem letzten Speichern
    (auf `jetzt.mono`) mindestens `SPEICHERN_PERIODISCH_S` = 30 s vergangen sind
    und sich der Zeiger geändert hat. Alle anderen Gründe speichern sofort.

### 6.4 Rang der Befehle in der Ausgabe

| Rang | Befehle |
|---|---|
| 1 | `LautstaerkeSetzen` |
| 2 | `AusgangWaehlen` |
| 3 | `Pausieren` |
| 4 | `ZeigerSpeichern` |
| 5 | `Abspielen` |
| 6 | `TonSpielen`, `StatusPruefen` |
| 7 | `Melden`, `EreignisSenden`, `LeserPing`, `ZustandMelden`, `Protokoll` |
| 8 | `SyncAbbrechen` |
| 9 | `SyncStarten`, `UpdateStarten` |
| 10 | `Herunterfahren` |

Innerhalb desselben Rangs bleibt die Emissionsreihenfolge. Folge für den
Kopfhörerwechsel: Die neue Grenze (Rang 1) steht immer **vor** dem
`AusgangWaehlen` (Rang 2). `app.py` führt die Befehle genau in dieser
Reihenfolge nacheinander aus.

### 6.5 Wie `app.py` den Kern benutzt

1.  Ereignis aus der Ereignisschleife holen, `Jetzt` bilden.
2.  `neuer_zustand, befehle = core.step(zustand, ereignis, jetzt)`.
3.  Befehle in der gegebenen Reihenfolge ausführen. Ein Befehl blockiert die
    Schleife nicht (Ein-/Ausgabe läuft asynchron). Schlägt die Ausführung eines
    Befehls fehl, protokolliert `app` das; Folgen meldet das ausführende Modul
    als Ereignis (z. B. `PlayerFehler`).
4.  `app` setzt `sim=true` im Protokoll für Ereignisse aus dem Simulations-Treiber;
    die Ereignistypen selbst unterscheiden sich nicht.
5.  **Beobachter:** `app` gibt nach jedem Kern-Aufruf eine **Kopie** jedes äußeren
    Ereignisses sowie jedes ausgegebenen `ZustandMelden` und `Protokoll` an den
    Statussammler in `ha` (Abschnitt 12). Zusätzlich erhält er `HaVerbindung`,
    das den Kern nicht erreicht. Der Beobachter ändert nichts am Kern und gibt
    keine Befehle zurück.

## 7. Ereignis-Ausgang mit Bestätigung

*   Der Kern gibt `Melden(art, uid, befehl_id)` aus. `app` übergibt es an
    `outbox`.
*   `outbox` führt `unknown.json` (Schema: `data-model.md`). Schlüssel ist die
    **Kennung** (`uid`); eine Kennung hat höchstens einen Eintrag. Meldet der
    Kern dieselbe Kennung erneut, werden `letzter_zeitpunkt` und `anzahl`
    aktualisiert, und `gelernt` ersetzt `unbekannt` (nicht umgekehrt).
*   Nach dem Schreiben lässt `outbox` den Eintrag durch `ha` veröffentlichen
    (`mqtt-v1.md`). Ohne Verbindung bleibt er in der Datei und wird bei der
    nächsten Verbindung veröffentlicht.
*   Die **Bestätigung** kommt als `Bestaetigt(id, grund, zuletzt, art)` (`id` =
    Kennung): in Stufe 2 von `tobibox sim ack`, ab Stufe 3a von `ha` (HA hat auf
    dem Thema `…/ack` geantwortet). `zuletzt` und `art` nennen die
    Veröffentlichung, die HA bestätigt. `outbox` löscht den Eintrag **nur, wenn
    `zuletzt` und `art` mit dem aktuellen Eintrag in `unknown.json`
    übereinstimmen**. Eine Bestätigung für eine ältere Veröffentlichung (der
    Eintrag wurde inzwischen überschrieben, z. B. `unbekannt` durch `gelernt`
    oder höhere `anzahl`) ist **wirkungslos**, wird protokolliert (`ack_veraltet`)
    und lässt den Eintrag samt der neueren dauerhaften Nachricht stehen; HA
    bestätigt die neuere Veröffentlichung selbst. Bei Übereinstimmung löscht
    `outbox` den Eintrag aus `unknown.json` und `ha` die dauerhafte Nachricht auf
    dem Broker. `grund` ist ein beliebiger Text aus der Antwort von HA und wird
    protokolliert. Ändert sich der Eintrag zwischen der Prüfung und dem PUBACK der
    Löschung, behält `outbox` ihn und veröffentlicht ihn erneut.
*   Eine Bestätigung für eine unbekannte `id` oder eine zweite Bestätigung ist
    **wirkungslos** (idempotent), kein Fehler.
*   Der Broker allein (PUBACK) bestätigt nichts.
*   Schnittstelle von `outbox` (Namen verbindlich):
    *   `melden(art, uid, befehl_id, jetzt) -> None`
    *   `offen() -> list[Eintrag]` (alle noch nicht bestätigten Einträge)
    *   `bestaetigt(id, grund, zuletzt, art) -> bool` (`True`, wenn ein Eintrag gelöscht wurde)

## 8. Lautstärke: Schnittstelle der Regel

Die Regel steht einmal im Design („Lautstärke“): **wirksame Grenze = Minimum
aller aktiven Grenzen**, und keine Lautstärke liegt darüber.

*   **Benannte Grenzen** (Konstanten in `volume.py`, genau diese Namen):

    | Name | Wer setzt sie | Wert |
    |---|---|---|
    | `global` | `core` bei `GeraeteEinstellungen` | `lautstaerke_max` |
    | `leise_zeit` | `quiet` (Fenster „leiser“, oder bei nicht vertrauenswürdiger Zeit die kleinste „leiser“-Grenze aller Fenster) | `Fenster.grenze` |
    | `kopfhoerer` | `session` bei `Kopfhoerer(steckt=True)`; `None` beim Ziehen | `lautstaerke_kopfhoerer` |
    | `gute_nacht` | `bedtime` während des Ausblendens | fällt vom Startwert (die `wirksam` aus dem letzten `LautstaerkeGeaendert` zu Beginn des Ausblendens) linear auf 0 über `ausblenden_s` |
    | `ausblenden` | `session` beim sanften Ausblenden wegen „stumm“ (und `quiet` beim sanften Absenken wegen „leiser“) | fällt vom Startwert (`wirksam` zu Beginn) über `STUMM_AUSBLENDEN_S` bzw. `LEISER_ABSENKEN_S` (je 3,0 s) linear auf das Ziel |

*   **Funktionen von `volume.py`** (rein):
    *   `wirksame_grenze(grenzen: Mapping[str, int]) -> int`: Minimum aller
        Werte, die nicht `None` sind; ohne Werte 100.
    *   `klemmen(wunsch: int, grenzen: Mapping[str, int]) -> int`:
        `min(wunsch, wirksame_grenze(grenzen))`, nie unter 0.
    *   `rampe(von: int, nach: int, start_mono: float, dauer_s: float, jetzt_mono: float) -> int`:
        lineare Rampe, auf ganze Prozent gerundet, an den Rändern begrenzt.
*   **Woher die Teilautomaten den Startwert kennen:** Sie sehen `wunsch` und
    `grenzen` nicht. `core` meldet ihnen jede Änderung der wirksamen Lautstärke
    als `LautstaerkeGeaendert(wirksam)`; jeder Teilautomat merkt sich den letzten
    Wert. Beim Beginn einer Rampe hält er `von = wirksam` (und `start_mono`)
    fest und gibt dann bei jedem `Takt` `GrenzeGesetzt(name, rampe(von, nach,
    start_mono, dauer_s, jetzt.mono))` aus. „Laute Wiedergabe“ beim Beginn eines
    „leiser“-Fensters heißt: `wirksam` größer als `Fenster.grenze`; nur dann
    gibt es eine Absenk-Rampe, sonst wird die Grenze `leise_zeit` sofort gesetzt.
*   **Wer sie anwendet:** `core` hält `grenzen` und `wunsch`. Am **Ende jeder
    Verarbeitung** (nach dem Leeren der Warteschlange, 6.1) berechnet `core`
    `klemmen(wunsch, grenzen)` und gibt `LautstaerkeSetzen(prozent, grenze)`
    **nur aus, wenn sich `prozent` oder `grenze` gegenüber `ausgegeben` ändern**
    (Nettowert: mehrere `GrenzeGesetzt` in einer Verarbeitung ergeben höchstens
    einen Befehl). `player` setzt den Wert durch und klemmt auf `grenze`. Während
    einer Rampe entsteht so je `Takt` (alle 0,1 s) höchstens ein Befehl.
*   **Start:** Auf `GeraeteEinstellungen` gibt `core` als **allerersten** Befehl
    `LautstaerkeSetzen` aus, bevor etwas spielt. Zusätzlich gilt 6.2, Regel 6.
*   **Ende einer Rampe mit Pause** (Ausblenden bei „Gute Nacht“ oder „stumm“):
    Erreicht die Rampe ihr Ziel und pausiert die Sitzung, löscht der Teilautomat
    seine Grenze (`GrenzeGesetzt(…, None)`), `wunsch` bleibt unverändert. Wegen
    6.2, Regel 7 folgt daraus **kein** `LautstaerkeSetzen` vor oder mit der Pause;
    die Lautstärke bleibt in der Pause niedrig, und vor dem nächsten `Abspielen`
    setzt Regel 6 den Wunsch.
*   **Kopfhörerwechsel:** erst die neue Grenze (`GrenzeGesetzt` → `LautstaerkeSetzen`),
    dann `AusgangWaehlen` (Rang 1 vor Rang 2).

### 8.1 Töne (bestätigt 05.11.)

*   **Wer:** Das Modul `sounds` führt den bestehenden Befehl
    `TonSpielen(ton)` aus (Abschnitt 4); es gibt keinen neuen Befehl. Der Kern
    kennt keine Tonpegel.
*   **Gleicher Ausgang wie MPD:** Alle Töne gehen über denselben Audioausgang wie
    die Wiedergabe. Auf dem Pi spielt `sounds` über das ALSA-`softvol`-Gerät, das
    auch MPD benutzt; die **harte Kappe** (`lautstaerke_max`) gilt damit auch für
    Töne. Auf dem Mac spielt `sounds` mit `afplay -v <pegel/100>`; dort gibt es
    **keine** harte Kappe, es gilt nur die Regel unten.
*   **Pegel in Prozent** (Felder `ton_pegel` und `hinweis_pegel` in `config.json`,
    `data-model.md`, Abschnitt 2). `grenze` ist die **wirksame Grenze** aus
    Abschnitt 8; `app.py` gibt sie `sounds` beim Ausführen mit (der zuletzt mit
    `LautstaerkeSetzen` ausgegebene Wert `grenze`; `TonSpielen` bekommt kein Feld).
    *   Alle Töne außer `hinweis`: `pegel = min(ton_pegel, grenze)`. `ton_pegel`
        ist ein **eigener fester Wert** (Vorgabe 40), unabhängig von der
        Wiedergabelautstärke `wunsch`, aber nie über der wirksamen Grenze.
    *   `hinweis` (der leise Hinweiston unter „stumm“, 6.2 Regel 2):
        `pegel = max(5, min(hinweis_pegel, grenze))`. `hinweis_pegel` hat die
        Vorgabe 15 (hörbar, aber leise). Die Untergrenze 5 hält den Hinweiston
        auch bei sehr kleiner Grenze hörbar; die harte Kappe bleibt wirksam.
    *   Fehlen die Felder (keine Konfiguration geladen), gelten die Vorgaben 40
        und 15.

## 9. Fälle, die die Tabellen des Designs offenlassen

Alle Punkte sind Festlegungen dieses Vertrags; die als „bestätigt (05.11.)“
gekennzeichneten sind von Tobias oder der Projektleitung entschieden
(Abschnitt „Festlegungen“ am Ende).

1.  **Leser-Unterbrechung: `LeserHallo` und `LeserAlarm`** (bestätigt 05.11.,
    Projektleitung). Beide Ereignisse starten **nie** eine Wiedergabe.
    *   Zustand `spielt`: Wechsel nach `unbekannt`, Frist `LESER_FRIST_S` = 3,0 s.
        Die Frist beginnt mit dem **ersten** der beiden Ereignisse (Alarm oder
        `LeserHallo`) und wird durch ein zweites nicht verlängert. Meldet `reader`
        innerhalb der Frist dieselbe Figur erneut (Punkt 2), läuft die Wiedergabe
        ohne Neustart weiter. Sonst Pause.
    *   Zustände `pausiert`, `beendet`, `gehalten`: **keine Wirkung.** Die Figur
        gilt weiter als liegend (`figur_liegt` und die gemerkte Figur ändern sich
        nicht). Nur `Abgehoben` (oder der Abgleich in Punkt 3) ändert das.
    *   Zustand `leer`: keine Wirkung.
    *   **Wiedermeldung:** Ein `Aufgelegt` oder `Gesperrt` mit **derselben
        Vorgangs-ID** wie die gemerkte liegende Figur ist **in allen Zuständen
        außer `unbekannt` (siehe 9.2)** eine Wiedermeldung nach `HELLO` (3.1,
        auch nach `seq=0` oder `seq_reset` ohne `HELLO`) und ein **No-op**: kein
        `Abspielen`, keine
        `AktionAusgeloest`, kein `Melden`, kein Ton, keine Zustandsänderung. Eine
        **andere** Vorgangs-ID gilt als neues Auflegen (Tabellen des Designs).
    *   **Zeitgrenze und Ausnahme:** Nach einem bestätigten Verlust (Alarm oder
        `LeserHallo` während `spielt`) pausiert die Sitzung spätestens
        `LESER_FRIST_S` + `TAKT_S` = **3,1 s** nach dem ersten der beiden Ereignisse
        (plus Ausführungszeit des Pausenbefehls). Das ist eine **bewusste
        Ausnahme von der 1,5-s-Regel** des Designs (CUJ 13): Das Abheben erkennt
        die Firmware (`REMOVED` nach `REMOVE_AFTER_MS`), nicht der Kern; bei
        Verbindungsverlust kann der Kern ein Abheben nicht sehen und wartet
        deshalb absichtlich länger, damit ein kurzer USB-Aussetzer die Wiedergabe
        nicht pausiert. Bei einem Hänger ohne Verbindungsabbruch kommt der Alarm
        erst nach `WATCHDOG_S` = 5 s, die Pause also bis zu 8,1 s nach dem letzten
        Herzschlag. Mit `RECONNECT_BACKOFF_S` ab 0,25 s und der Frist von 3,0 s
        reicht die Karenz für Aussetzer in der Größenordnung von 1 bis 2 s
        (Messung in Stufe 1).
    *   **Abweichung vom Design (Tabellenzeile „Frist abgelaufen“ und der Satz
        „Kommt nach der Frist dieselbe Kennung wieder, ist das ein normales
        Auflegen“):** Nach Ablauf der Frist pausiert die Sitzung, die Figur gilt
        aber weiter als liegend. Meldet `reader` sie danach erneut (Wiedermeldung,
        gleiche Vorgangs-ID), startet nichts von selbst; erst Abheben und
        erneutes Auflegen oder der Hauptknopf kurz spielen wieder (Punkt 12).
2.  **Im Zustand `unbekannt`:**
    *   `Aufgelegt` oder `Gesperrt` mit **derselben** Vorgangs-ID (dieselbe Figur:
        gleiche Kennung bzw. beide gesperrt) innerhalb der Frist: Zustand
        `spielt`, kein Befehl. Das ist die **einzige** Ausnahme vom No-op der
        Wiedermeldung (Punkt 1). **Bestätigt (05.11.):** Ist dabei der MPD
        verloren (Punkt 10, `PlayerVerbindung(ok=False)` ohne spätere Rückkehr)
        oder ist die `MPD_FRIST_S` während `unbekannt` abgelaufen, geht die
        Sitzung statt nach `spielt` sofort nach `pausiert` (Zeiger ist
        gespeichert; die Figur liegt weiter). Ein laufender MPD-Fristzähler wird
        beim Eintritt in `unbekannt` verworfen.
    *   `StummBeginnt` in `unbekannt` (bestätigt 05.11.): wirkt erst, **nachdem
        die Sitzung `unbekannt` verlassen hat**; bis dahin spielt nichts. Verlässt
        sie `unbekannt` nach `spielt` (gleiche Figur zurück), gilt „stumm“ sofort
        (Punkt 5); verlässt sie es nach `pausiert`, gilt Punkt 12.    *   `Aufgelegt` oder `Gesperrt` mit **anderer** Vorgangs-ID (andere Kennung,
        oder gesperrt gegen Kennung): Frist endet sofort, Pause und Zeiger der
        alten Serie speichern, danach die neue Figur wie ein normales Auflegen
        (Tabelle: „Figurwechsel während einer Leser-Unterbrechung“).
    *   `Abgehoben`: Frist endet, Pause, Zeiger speichern, `pausiert`,
        `figur_liegt` falsch.
    *   Frist abgelaufen (`Takt`): Pause, Zeiger speichern, `pausiert`; die Figur
        gilt weiter als liegend (Punkt 1, letzte Abweichung).
    *   `LeserHerzschlag` mit `present=False` nach `LeserHallo`: die Figur ist weg;
        Frist endet sofort, Pause, Zeiger speichern, `pausiert`, `figur_liegt`
        falsch.
3.  **Abgleich über den Herzschlag:** Die Sitzung vergleicht `present` mit
    ihrem Wissen `figur_liegt`. Weichen zwei **aufeinanderfolgende**
    `LeserHerzschlag` voneinander ab (beide `present` anders als `figur_liegt`),
    gibt sie `LeserPing()` aus und zählt neu. Das `HELLO` auf den `PING` und die
    erneute Meldung der Firmware stellen den Zustand her. **Danach:** Ist die
    erste `LeserHerzschlag` nach einem `LeserHallo` `present=False`, während
    `figur_liegt` wahr ist (die Figur wurde im Ausfall abgehoben, ohne dass ein
    `REMOVED` ankam), behandelt die Sitzung das wie `Abgehoben` mit der gemerkten
    Vorgangs-ID: in `pausiert`, `beendet`, `gehalten` Zustand `pausiert`,
    `figur_liegt` falsch, kein Befehl (in diesen Zuständen läuft nichts mehr); in
    `unbekannt` Punkt 2.
4.  **`PLACED` im Zustand `spielt`** (bekannte Kennung, andere als die aktuelle,
    oder dieselbe nach verlorenem `REMOVED`): Die Firmware meldet einen Wechsel
    als `Abgehoben` + `Aufgelegt`. `Aufgelegt` im Zustand `spielt` kommt daher
    nur vor, wenn ein `REMOVED` verloren ging. Es gilt die Tabellenzeile
    „`spielt` | `PLACED` andere Kennung“; bei **gleicher** Kennung geschieht
    nichts (Wiedergabe läuft weiter).
5.  **Sanftes Ausblenden bei „stumm“** (Tabellenzeile `spielt` | stumm beginnt):
    `session` hält beim Eintreffen von `StummBeginnt` den Startwert
    `von = wirksam` (zuletzt gemeldetes `LautstaerkeGeaendert`) fest und setzt bei
    jedem `Takt` `GrenzeGesetzt("ausblenden", rampe(von, 0, start, STUMM_AUSBLENDEN_S,
    jetzt.mono))`; am Ende `Pausieren("stumm")`, `ZeigerSpeichern("pause")`,
    `GrenzeGesetzt("ausblenden", None)`, Zustand `gehalten`. Wegen 6.2, Regel 7,
    folgt daraus kein Lautstärkesprung. `Abgehoben` während des Ausblendens beendet
    es sofort wie ein normales Abheben (Grenze löschen, Regel 7 gilt auch hier).
    Dasselbe Verfahren (`LEISER_ABSENKEN_S`, Grenze `ausblenden`, Ziel
    `Fenster.grenze`, danach `leise_zeit` gesetzt und `ausblenden` gelöscht)
    benutzt `quiet`, um eine laute Wiedergabe (`wirksam` > `Fenster.grenze`) beim
    Beginn eines „leiser“-Fensters abzusenken.
6.  **Ausblenden bei „Gute Nacht“:** `bedtime` hält zu Beginn des Ausblendens den
    Startwert `von = wirksam` fest und setzt bei jedem `Takt` die Grenze
    `gute_nacht` nach `rampe(von, 0, start, ausblenden_s, jetzt.mono)`. Erreicht sie
    0, gibt `bedtime` `GrenzeGesetzt("gute_nacht", 0)` und das interne Ereignis
    `GuteNachtEnde` aus; `session` pausiert dann (`Pausieren("gute_nacht")`,
    `ZeigerSpeichern("pause")`), `bedtime` löscht die Grenze und geht auf `aus`.
    Wegen 6.2, Regel 7, springt die Lautstärke nicht zurück. (`GuteNachtEnde` ist
    ein internes Ereignis ohne Felder, `bedtime` → `session`.)
7.  **Zweite Gute-Nacht-Karte** im Zustand `laeuft`: Der Timer beginnt von vorn.
    Im Zustand `ausblenden`: ignoriert.
8.  **Lernmodus:** `Gesperrt` im Zustand `lernt` ändert nichts (keine Kennung,
    der Lernmodus läuft weiter). Bei „stumm“ und Lernmodus gilt Regel 6.2.2:
    Beginn- und Endeton werden zum leisen Hinweiston. Die Frist 2 min beginnt
    bei der Annahme des Befehls auf `jetzt.mono` und heißt `LERN_FRIST_S` = 120.
9.  **Befehle von HA: wer prüft was** (bestätigt 05.11. für die unsichere Uhr).
    Die Prüfungen verteilen sich so; `ha` ist das Modul der Box, das MQTT
    spricht, der „Kern“ ist `learn.py`/`idle.py`:

    | Prüfung | Modul | Wirkung |
    |---|---|---|
    | `v` bekannt (`mqtt-v1.md`, Abschnitt 8) | `ha` | größeres `v`: Nachricht verworfen, Protokoll, `event` `fehler` mit `code="v_unbekannt"`, von `ha` direkt veröffentlicht |
    | `befehl` bekannt | `ha` | unbekannt: verworfen, `event` `fehler` mit `code="befehl_unbekannt"`, von `ha` direkt |
    | Doppelte `id` (letzte 50) | `ha` | verworfen, nur Protokoll |
    | `tobibox/config`: Schema, Listen-ID, Revision | `ha` mit `store` (Revisionsregel `mqtt-v1.md` 5.2) | angenommen: `KonfigGeladen`; abgelehnt: `event` `liste_abgelehnt`, von `ha` direkt. Diese Regel liegt **außerhalb des Kerns**. |
    | Ablaufzeit (`jetzt.wall > gueltig_bis`) | Kern: `learn` (`HaLernmodus`, `HaLernmodusAbbruch`), `idle` (`HaSyncAnstossen`, `HaUpdateAnstossen`) | abgelaufen: ignoriert, nur `Protokoll` (kein `EreignisSenden`) |
    | Uhr (`jetzt.zeit_ok`) | Kern: `learn` (nur `HaLernmodus`), `idle` | `False`: Befehl abgelehnt, `Protokoll(WARNING)` und `EreignisSenden("befehl_abgelehnt", {"befehl":…, "befehl_id":…, "grund":"zeit_unsicher"})`. Gilt für `lernen`, `sync`, `update` |
    | Bedingungen für `HaUpdateAnstossen` | Kern: `idle` | verlangt Netz-Klasse `home`, Lader an, Zustand der Sitzung nicht `spielt`, kein Sync und kein Update aktiv. Sonst `EreignisSenden("befehl_abgelehnt", {…, "grund":"bedingung", "detail": <welche>})` |
    | Sync-Regel (Heim / Hotspot, Akku) | `sync` | `HaSyncAnstossen` wird durchgereicht (`SyncStarten("ha")`); ob er läuft, entscheidet `sync` (sonst `SyncAbgebrochen(grund="regel")`) |

    *   `HaLernmodusAbbruch` hat eine Ablaufzeit (`gueltig_bis`, 30 s), aber
        **keine Sperre bei unsicherer Uhr**: Ein Abbruch schadet nie. Bei
        `zeit_ok` falsch wird die Ablaufzeit nicht geprüft (die Wanduhr ist dann
        nicht verlässlich) und der Abbruch ausgeführt. Im Zustand `aus` ist er
        wirkungslos (nur Protokoll). Er wird **nie** mit `befehl_abgelehnt`
        beantwortet.
    *   Bei unsicherer Uhr lehnt die Box Lernmodus, Sync und Update ab (wie
        bisher). **HA zeigt den Grund an** (`mqtt-v1.md`, Abschnitt 6.2): das
        Ereignis `befehl_abgelehnt` mit `grund="zeit_unsicher"` wird als
        Benachrichtigung im Klartext angezeigt, und der Sensor „Zeitquelle“ trägt
        `zeit_ok` als Attribut.
10. **Fehler des Players:**
    *   `PlayerFehler` im Zustand `spielt`: `TonSpielen("fehler")`,
        `Pausieren("fehler")`, `Protokoll(ERROR)`. Bei `datei_fehlt` oder
        `datei_unlesbar` geht der Zeiger auf die nächste Folge (Position 0),
        sonst bleibt er. Zustand `pausiert`; die Figur liegt weiter.
    *   **MPD weg während der Wiedergabe** (bestätigt 05.11., Tobias):
        `PlayerVerbindung(ok=False)` im Zustand `spielt`: `Protokoll(ERROR)`,
        Zeiger mit der letzten Position speichern (`ZeigerSpeichern("pause")`).
        Die Sitzung bleibt im Zustand `spielt` (Kennzeichen unverändert), merkt
        sich aber die Frist `MPD_FRIST_S` = 5,0 s ab diesem Ereignis.
        *   Kommt `PlayerVerbindung(ok=True)` **innerhalb** der Frist und liegt die
            Figur weiter (`figur_liegt`), setzt die Wiedergabe am gespeicherten
            Zeiger fort: `AusgangWaehlen` (der MPD-Zustand ist verloren) und
            `Abspielen` mit `position_s = max(0, position − RUECKSPRUNG_S)`
            (Regel 6.2.6 setzt die Lautstärke davor). Zustand `spielt`.
        *   Sonst (Frist abgelaufen, `Takt`): `Pausieren("fehler")` (wirkungslos,
            wenn MPD weg ist), Zustand `pausiert`; die Figur gilt weiter als
            liegend. Das Kind legt die Figur neu auf (Abheben und Auflegen) oder
            drückt den Hauptknopf (Punkt 12). `TonSpielen("fehler")` gibt es hier
            nicht.
        *   Beginnt „stumm“ während der Frist: kein Ausblenden, sondern sofort
            Zustand `gehalten` (der Zeiger ist gespeichert).
        *   **Leser-Unterbrechung während der Frist (bestätigt 05.11.):** Geht die
            Sitzung nach `unbekannt` (Punkt 1), wird der laufende Fristzähler
            **verworfen**. Kehrt sie von `unbekannt` nach `spielt` zurück (Punkt 2)
            und ist der MPD weiter verloren oder die Frist inzwischen abgelaufen,
            geht sie **sofort nach `pausiert`** (Zeiger gespeichert, Figur liegt),
            ohne `Abspielen`. Ebenso bleibt `mpd_verloren`, wenn
            `PlayerVerbindung(ok=True)` in `unbekannt` eintrifft: die Rückkehr
            nach `spielt` führt weiter nach `pausiert` (sicheres Verhalten,
            05.11.).
        *   `Weiter`/`Zurueck` während der Frist: ignoriert (nur Protokoll;
            05.11.).
        *   `Abgehoben` während der Frist: normale Pause (Zeiger ist gespeichert),
            `pausiert`. `Hauptknopf` kurz: Pause, `pausiert`. Weitere
            `PlayerFehler` während der Frist: nur `Protokoll`.
    *   `PlayerVerbindung` in den übrigen Zuständen: nur `Protokoll`;
        `ok=True` in `pausiert`, `beendet`, `gehalten`, `leer` gibt zusätzlich
        defensiv `Pausieren("fehler")` aus (idempotent; 05.11.).
11. **Aktionskarten** (`Zuordnung.typ="aktion"`) im Zustand `leer` oder
    `pausiert`: die Sitzung bleibt im Zustand, gibt `AktionAusgeloest` aus und
    merkt sich `figur_liegt=True` und die Vorgangs-ID; `Abgehoben` setzt es
    zurück. Eine Wiedermeldung (Punkt 1) löst die Aktion **nicht** erneut aus.
    Aktionskarten im Zustand `spielt` können nur nach verlorenem `REMOVED`
    vorkommen und werden wie Punkt 4 behandelt (erst Pause, dann Aktion).
12. **Abspielen-Auslöser und „stumm“ (bestätigt 05.11., Tobias).**
    *   **Hauptknopf kurz** je Zustand (Tabelle plus): `spielt` → Pause, Zeiger
        speichern, `pausiert`; `pausiert` mit liegender Figur → Abspielen am
        Zeiger (mit Rücksprung); `pausiert` ohne Figur → Abspielen am Zeiger der
        zuletzt gespielten Serie (normale Play/Pause-Funktion); `beendet` mit
        liegender Figur → nächste Folge ab Zeiger (Entscheidung E); `gehalten`,
        `leer`, `unbekannt` → keine Wirkung. `Weiter`/`Zurueck` springen zur
        nächsten/vorigen Folge in der Reihenfolge (zyklisch), Position 0,
        `ZeigerSpeichern("folgenende")`-Regeln wie bei einer neuen Folge, nur im
        Zustand `spielt` oder `pausiert` mit Serie. **Bestätigt (05.11.) für
        `beendet`:** `Weiter` = die Folge, auf die der Zeiger steht, wie
        `Hauptknopf` kurz (Position 0, Zustand `spielt`); `Zurueck` = die Folge
        **vor** dem Zeiger (zyklisch), also die eben beendete, neu ab Position 0
        (Zustand `spielt`; geändert 05.11., Projektleitung: das Kind erwartet
        „nochmal“). Beide setzen die Figur voraus (`beendet`
        mit liegender Figur wie beim Hauptknopf) und sind im „stumm“-Fenster
        gesperrt (nur Hinweiston, Tabelle unten).
    *   **Im „stumm“-Fenster** (`quiet` im Zustand `stumm`) startet **kein**
        Abspielen-Auslöser eine Wiedergabe. Jeder Auslöser, der ohne „stumm“ ein
        `Abspielen` ergäbe, gibt stattdessen nur `TonSpielen("hinweis")` aus
        (Regel 6.2.3 fasst gleiche Töne zusammen):

        | Auslöser unter „stumm“ | Wirkung |
        |---|---|
        | `Aufgelegt` (Serie, unbekannt) und `Gesperrt` in `leer`, `pausiert` | Hinweiston, Zustand `gehalten` (Tabelle des Designs); `Melden` bei unbekannter Figur bleibt |
        | `Aufgelegt` (Serie) in `beendet` und `gehalten` (Figur wird neu aufgelegt; bestätigt 05.11.) | nur Hinweiston, nichts startet, Zustand unverändert (`gehalten` bleibt, `beendet` bleibt); `Melden` bei unbekannter Figur bleibt |
        | `Hauptknopf` kurz in `pausiert`, `beendet`, `gehalten` | Hinweiston, Zustand unverändert |
        | `Weiter`, `Zurueck` in `pausiert`, `beendet`, `gehalten` (dort, wo sie ohne „stumm“ spielen würden) | Hinweiston, Zeiger unverändert |
        | Wechsel nach `KonfigGeladen` (Punkt 14) | Hinweiston, Zustand und Zeiger unverändert |
        | Fortsetzen nach MPD-Verlust (Punkt 10) | kommt unter „stumm“ nicht vor: die Sitzung ist dann nicht `spielt` |

        Während des Ausblendens (`spielt` bis `gehalten`, 3 s) gilt: Hauptknopf
        kurz pausiert wie üblich, `Weiter`/`Zurueck` werden ignoriert. Hauptknopf
        lang (Herunterfahren) bleibt unberührt.
13. **Kein Zeiger-Eingang vor `Bereit`:** `Aufgelegt` vor `ResumeGeladen`,
    `KonfigGeladen` und `BibliothekGeladen` kommt nie vor, weil `app` die
    Ereignisse des Lesers zurückhält.
14. **Neue Konfiguration bei liegender Figur** (CUJ 7a: Tobias ordnet eine
    unbekannte Figur zu, während sie noch liegt). Die Sitzung merkt sich die
    liegende Figur (Kennung, Vorgangs-ID, Art) und die Serie `serie_id`, die für
    sie zuletzt gestartet wurde (auch die Überraschungs-Serie). Kommt
    `KonfigGeladen` und ist die Kennung der liegenden Figur jetzt einer Serie `S`
    zugeordnet (und `S` ist in der Bibliothek; sonst Punkt „Serie fehlt“ in 6.3:
    nichts), die **nicht** `serie_id` ist:
    *   `spielt`: Zeiger der laufenden Serie speichern
        (`ZeigerSpeichern("figurwechsel")`), `S` starten wie beim Auflegen
        (Zeiger laden, `Abspielen`).
    *   `pausiert` und `beendet` (die Figur liegt): `S` starten wie beim Auflegen,
        Zustand `spielt` (CUJ 7a „wechselt sofort“). Der Zeiger der bisherigen
        Serie ist dort schon gespeichert.
    *   `gehalten`, `unbekannt`, `leer`: nichts.
    *   Unter „stumm“ in `pausiert`/`beendet`: nur Hinweiston (Punkt 12).
    *   Ist die Zuordnung unverändert, gehört die Figur zur laufenden Serie oder ist
        sie eine Aktionskarte, geschieht nichts.

## 10. Wer sendet welches Ereignis, wer führt welchen Befehl aus

| Modul | sendet Ereignisse | führt Befehle aus |
|---|---|---|
| `reader` | `LeserHallo`, `Aufgelegt`, `Gesperrt`, `Abgehoben`, `LeserHerzschlag`, `LeserAlarm`, `LeserFehler` | `LeserPing` |
| `player` | `FolgeZuEnde`, `PlayerPosition`, `PlayerFehler`, `PlayerVerbindung` | `LautstaerkeSetzen`, `AusgangWaehlen`, `Abspielen`, `Pausieren` |
| `app` | `GeraeteEinstellungen`, `KonfigGeladen` (Start), `BibliothekGeladen` (Start), `ResumeGeladen`, `Bereit`, `Takt`, `ZeitquelleGeaendert` (mit `power`) | alle Befehle (verteilt an die Module) |
| `store` | – | `ZeigerSpeichern` |
| `library` | `BibliothekGeladen` (nach Änderung) | – |
| `outbox` | – | `Melden`; nimmt `Bestaetigt` an |
| `ha` | `KonfigGeladen` (angenommene Liste), `HaLernmodus`, `HaLernmodusAbbruch`, `HaSyncAnstossen`, `HaUpdateAnstossen`, `HaVerbindung` (nur an Statussammler und `selftest`), `Bestaetigt` | `EreignisSenden`, `ZustandMelden` (Statussammler baut daraus den Status, Abschnitt 12), Veröffentlichung für `outbox`; veröffentlicht `liste_abgelehnt`, `v_unbekannt`, `befehl_unbekannt` selbst (Punkt 9.9), ohne Kern-Befehl |
| `sounds` | – | `TonSpielen` (auch für `selftest`) |
| `controls` | `Hauptknopf`, `Weiter`, `Zurueck`, `LautstaerkeDrehen` | – |
| `headphones` | `Kopfhoerer` | – |
| `power` | `LaderGeaendert`, `AkkuStand`, `AkkuTiefstand`, `ZeitquelleGeaendert` | `Herunterfahren` |
| `net` | `NetzKlasse`, `ZeitquelleGeaendert` | – |
| `sync` | `SyncGestartet`, `SyncFertig`, `SyncAbgebrochen`, `BibliothekGeladen` (über `library`) | `SyncStarten`, `SyncAbbrechen` |
| `update`, `selftest` | `UpdateGestartet`, `SelbsttestErgebnis` | `UpdateStarten` (`update`), `StatusPruefen` (`selftest`, Kriterien Abschnitt 12.3) |
| `led` | – | `ZustandMelden` (Anzeige) |
| `eventlog` | – | `Protokoll` |
| `sim` | jedes Ereignis der Quellen `controls`, `headphones`, `power`, `net`, `ha` (Befehle `learn`, `ack`, `card`, später mehr) | – |

`core`, `volume`, `pointer`, `protocol`, `clock` senden keine Ereignisse und
führen keine Befehle aus.

## 11. Konstanten

Modulkonstanten mit genau diesen Namen. Es gibt keine eigene Konstanten-Datei.

| Name | Wert | Modul |
|---|---|---|
| `TAKT_S` | 0,1 | `app.py` (Takt und Auflösung aller Fristen und Rampen) |
| `POSITION_INTERVAL_S` | 1,0 | `player.py` |
| `LESER_FRIST_S` | 3,0 | `session.py` (Karenzzeit bei Leser-Unterbrechung; Pause ≤ `LESER_FRIST_S` + `TAKT_S` = 3,1 s nach dem ersten Ereignis, bewusste Ausnahme von der 1,5-s-Regel des Designs, Punkt 9.1) |
| `MPD_FRIST_S` | 5,0 | `session.py` (MPD weg während der Wiedergabe, Punkt 9.10) |
| `RUECKSPRUNG_S` | 3,0 | `pointer.py` |
| `SPEICHERN_PERIODISCH_S` | 30 | `session.py` |
| `LERN_FRIST_S` | 120 | `learn.py` |
| `LEERLAUF_S` | 1200 (20 min) | `idle.py` |
| `STUMM_AUSBLENDEN_S` | 3,0 | `session.py` |
| `LEISER_ABSENKEN_S` | 3,0 | `quiet.py` |
| `LESER_FEHLER_FENSTER_S` | 10 | `ha.py` (Statussammler: Prüfpunkt Leser auf `fehler`, Abschnitt 12.2) |
| `SPEICHER_MIN_FREI_MB` | 500 | `selftest.py` (Prüfpunkt Speicher, Abschnitt 12.3) |
| `GRENZE_GLOBAL`, `GRENZE_LEISE_ZEIT`, `GRENZE_KOPFHOERER`, `GRENZE_GUTE_NACHT`, `GRENZE_AUSBLENDEN` | `"global"`, `"leise_zeit"`, `"kopfhoerer"`, `"gute_nacht"`, `"ausblenden"` | `volume.py` |

Die Werte der Gute-Nacht-Dauern und der Leise-Zeiten kommen nicht aus
Konstanten, sondern aus `Konfig` (Vorschlag 30 min und 60 s).

## 12. Statusaufbau und Prüfpunkte

### 12.1 Wer baut den Status

Den Status-JSON (`mqtt-v1.md`, Abschnitt 3.3) baut der **Statussammler** im Modul
`ha`. Er ist kein Teilautomat und kein Teil des Kerns: Er hält nur zuletzt
gesehene Werte, und `app` füttert ihn als Beobachter (Abschnitt 6.5) mit Kopien
der Ereignisse sowie der ausgegebenen `ZustandMelden` und `Protokoll`. Quelle je
Feld:

| Status-Feld | Quelle |
|---|---|
| `zustand` | `ZustandMelden.sitzung`; ist `ZustandMelden.strom` = `herunterfahren`, dann `herunterfahren` |
| `lernmodus` | `ZustandMelden.lernmodus` |
| `serie` | `ZustandMelden.serie_id`; der Name aus der letzten `BibliothekGeladen` (ohne Treffer: `name` = `id`); `null` ohne Serie |
| `akku_prozent` | letztes `AkkuStand`; `null` bis zum ersten |
| `lader` | letztes `LaderGeaendert`; `null` bis zum ersten |
| `netz` | letztes `NetzKlasse` (bis zum ersten: `offline`) |
| `sync` | `SyncGestartet` → `zustand="laeuft"`. `SyncFertig` → `idle`, `ergebnis="ok"`, `neu`, `letzter_ende` = `jetzt.wall`. `SyncAbgebrochen` mit `grund="regel"` → `idle`, `ergebnis="abgebrochen"`, `grund`; mit anderem Grund → `fehler`, `ergebnis="abgebrochen"`, `grund` |
| `speicher_frei_mb` | `ha` fragt bei jeder Veröffentlichung das Dateisystem des Medienordners ab (freier Platz, ganze MB abgerundet) |
| `version` | `manifest.json` der laufenden Version, beim Start gelesen |
| `firmware` | `fw` des letzten gültigen `LeserHallo`; `null` ab einem `LeserAlarm` bis zum nächsten `LeserHallo` und vor dem ersten |
| `protokoll` | Konstante des Dienstes (die unterstützte Hauptversion, hier 1) |
| `leser` | Abbildung in 12.2 |
| `letzter_fehler` | der letzte `Protokoll`-Befehl der Ebene `ERROR`: `zeit` = Zeitstempel (`jetzt.wall`), `text` = `ereignis` und `meldung` |
| `zeitquelle`, `zeit_ok` | `Jetzt` des zuletzt verarbeiteten Ereignisses |
| `konfig` | letztes `KonfigGeladen`: `revision`, `liste_id` (ohne: `0` und `""`) |
| `update` | `update.json` beim Start; danach `UpdateGestartet` und `SelbsttestErgebnis` |
| `ts` | Wanduhr der Box bei der Veröffentlichung |

### 12.2 Prüfpunkt „Leser“ (Feld `leser`)

Der Statussammler hält die 10-s-Frist (`LESER_FEHLER_FENSTER_S`) auf `jetzt.mono`
(er sieht den `Takt`). Es gilt die erste zutreffende Zeile:

| `leser` | Bedingung |
|---|---|
| `simulation` | die Ereignisse des Lesers kommen aus `sim` (Stufe 2) |
| `getrennt` | noch kein `LeserHallo` seit dem Start, oder das letzte Ausfall-Ereignis ist ein `LeserAlarm` mit Grund `getrennt`, `kein_herzschlag` oder `hello_timeout` und danach kam kein gültiges `LeserHallo` |
| `fehler` | das letzte Ausfall-Ereignis ist `LeserAlarm(proto_unbekannt)`, oder in den letzten 10 s kam ein `LeserFehler` mit `schwere="fehler"` |
| `ok` | sonst |

`LeserFehler` mit `schwere` `warnung` oder `hinweis` ändern `leser` nicht.

### 12.3 Prüfpunkte der Status-Admin-Karte (`StatusPruefen`)

`selftest` führt `StatusPruefen` aus, prüft die vier Punkte in der Reihenfolge
Leser, Medien, Netz, Speicher und lässt `sounds` je Punkt `pruef_ok` oder
`pruef_fehler` spielen. Kriterium für `pruef_ok`:

| Punkt | `pruef_ok`, wenn |
|---|---|
| Leser | `leser` ist `ok` oder `simulation` (12.2) |
| Medien | der Medienordner ist lesbar, die Bibliothek enthält mindestens eine Serie mit mindestens einer Folge, und es gibt genau eine nicht leere Überraschungs-Serie |
| Netz | `netz` ist `home` oder `hotspot` und die Verbindung zum Broker steht (`HaVerbindung(ok=True)`) |
| Speicher | der freie Platz auf dem Medien-Dateisystem ist mindestens `SPEICHER_MIN_FREI_MB` und seit dem Start kam kein `datei_verloren` (`data-model.md`, Abschnitt 1.3) |

Die Tonfolge ist unter „stumm“ unverändert (6.2, Regel 2: `pruef_*` bleiben).

## Festlegungen in diesem Vertrag (Stand 05.11.)

Das Design lässt diese Einzelheiten offen. Entschieden wurde die einfachste
stimmige Lösung. „Bestätigt (05.11.)“ heißt: von Tobias (T) oder der
Projektleitung (P) entschieden oder aus dem Goldfisch-Review übernommen
(`review-stufe0.md`). Alle anderen Punkte sind noch offen.

1.  **Zeiger und Position liegen im Kern**, nicht im Player: `PlayerPosition`
    meldet die Position jede Sekunde, der Kern gibt `ZeigerSpeichern` mit dem
    Wert aus. So bleibt der Kern rein, und beim Abheben ist kein Rückruf nötig.
    Der gespeicherte Zeiger kann bis zu 1 s hinter der Wirklichkeit liegen
    (der 3-s-Rücksprung deckt das ab).
2.  **`index` im Zeiger** (Nummer der Folge) ist ein Zusatz, damit „nächste
    vorhandene Folge“ auch dann bestimmt ist, wenn die Datei nicht mehr in der
    Liste steht.
3.  **Daten kommen als Ereignisse** (`KonfigGeladen`, `BibliothekGeladen`,
    `ResumeGeladen`, `GeraeteEinstellungen`, `Bereit`), nicht als Parameter. Bis
    `Bereit` hält `app` Ereignisse des Lesers zurück.
4.  **Interne Ereignisse** (`InternesEreignis`) verbinden die Teilautomaten, damit
    sie reine Funktionen mit der Signatur des Designs bleiben. Zusätzlich zu
    den Namen aus Abschnitt 3.9: `GuteNachtEnde`. Neu (bestätigt 05.11., P,
    Review-Befund 1): `LautstaerkeGeaendert`, damit Rampen ihren Startwert kennen.
5.  **Fünf Zustände in der Liste von `core`** (`quiet` und `bedtime` getrennt),
    obwohl das Design vier Teilautomaten zählt (Ruhe-Regeln = `quiet` + `bedtime`).
    Reihenfolge: `session`, `learn`, `quiet`, `bedtime`, `idle`.
6.  **Bestätigt (05.11., P): Takt alle 0,1 s**, Auflösung aller Fristen und
    Rampen 0,1 s (Rampen in 0,1-s-Schritten). Rampen laufen über `Takt` und
    `LautstaerkeSetzen`, nicht als Befehl „Rampe“ des Players.
7.  **Fester Rang der Befehle** (6.4) und feste Konfliktregeln (6.2). Töne unter
    „stumm“ werden zum Hinweiston; `pruef_*` bleiben. **Bestätigt (05.11., P,
    Review-Befund 2):** `LautstaerkeSetzen` entsteht einmal am Ende der Verarbeitung
    aus dem Nettowert; nach einer Rampe mit Pause kein Lautstärkesprung (Regel 7).
8.  **Neue Befehle über die Liste im Design hinaus:** `LeserPing` (Abgleich),
    `StatusPruefen`, `ZustandMelden`, `Protokoll`, `EreignisSenden`,
    `AusgangWaehlen`. Neue Ereignisse: `Weiter`, `Zurueck` (das Design nennt
    „Vor, Zurück“), `LautstaerkeDrehen`, `HaVerbindung`, `AkkuStand`.
9.  **Befehle von HA:** Der Kern prüft Ablaufzeit und Uhr; bei unsicherer Uhr
    werden Lernmodus, Sync und Update abgelehnt, und HA zeigt den Grund
    (bestätigt 05.11., T/P). **Bestätigt (05.11., P, Review-Befund 7):** Tabelle
    „wer prüft was“ in 9.9; `lernen_abbrechen` hat Ablaufzeit, aber keine
    Uhr-Sperre; `liste_abgelehnt`, `v_unbekannt`, `befehl_unbekannt` veröffentlicht
    `ha` selbst.
10. **Abgleich über `present`** nach zwei abweichenden Herzschlägen mit `PING`;
    danach gilt die erste `HB` mit `present=0` als Abheben (9.3).
11. **Bestätigt (05.11., P): `LeserHallo`/`LeserAlarm` starten nie eine
    Wiedergabe** (9.1), Wiedermeldung mit gleicher Vorgangs-ID ist ein No-op,
    Abweichung vom Design bei „Frist abgelaufen“. **Bestätigt (05.11., T):
    MPD weg** (9.10): zurück innerhalb 5 s und Figur liegt → weiter am
    gespeicherten Zeiger mit 3-s-Rücksprung; sonst Pause und neu auflegen.
12. **Hauptknopf kurz bei `pausiert` ohne Figur** spielt weiter (Play/Pause),
    wie CUJ 19 es für „ohne Figur“ beschreibt. **Bestätigt (05.11., T):** Im
    „stumm“-Fenster startet nichts (Hauptknopf kurz, Weiter, Zurück, Auflegen,
    Wechsel nach `KonfigGeladen`); es gibt nur den Hinweiston (9.12).
13. **Zweite Gute-Nacht-Karte** startet den Timer neu.
    **Bestätigt (05.11., P):** weitere Festlegungen dieses Stands:
    *   Die Wiedermeldung (gleiche Vorgangs-ID) ist **in allen Zuständen außer
        `unbekannt`** ein No-op (9.1, 9.2).
    *   Aus `unbekannt` zurück nach `spielt` bei verlorenem MPD oder abgelaufener
        `MPD_FRIST_S`: sofort `pausiert`; ein laufender MPD-Fristzähler wird beim
        Eintritt in `unbekannt` verworfen (9.2, 9.10).
    *   Die Vorgangs-ID bleibt auch bei der ersten `PLACED`/`LOCKED`-Zeile mit
        `seq=0` oder nach `seq_reset` erhalten, selbst ohne `HELLO` (3.1).
    *   Töne: gleicher Ausgang wie MPD, `ton_pegel` (40) und `hinweis_pegel` (15,
        Untergrenze 5), nie über der wirksamen Grenze; Mac ohne harte Kappe (8.1).
    *   Auflegen in `beendet` und `gehalten` unter „stumm“: nur Hinweiston (9.12); `StummBeginnt` in `unbekannt` wirkt erst nach dem
        Verlassen (9.2); `Weiter`/`Zurueck` in `beendet` (9.12; `Zurueck` spielt die eben beendete Folge neu).
14. **Bestätigt (05.11., P): `volume.rampe`** und `LautstaerkeGeaendert` als
    Weg, den Startwert der Rampe zu kennen (Abschnitt 8).
15. **`kopfhoerer`-Grenze** kommt aus `tobibox.toml` als `lautstaerke_kopfhoerer`
    (das Design nennt die Grenze, aber nicht ihre Quelle).
16. **Bestätigt (05.11., P, Review-Befund 6): Neue Konfiguration bei liegender
    Figur** wechselt auf die zugeordnete Serie, auch in `pausiert` und `beendet`
    (9.14), damit CUJ 7a „Box wechselt sofort“ erfüllt ist.
17. **Bestätigt (05.11., T): Zuordnung auf eine noch nicht synchronisierte
    Serie** spielt die Überraschungs-Serie, protokolliert den Grund, und die
    Zuordnung gilt beim nächsten Auflegen (6.3).
18. **Bestätigt (05.11., P): Bestätigung mit `zuletzt`** (und `art`): die Box
    löscht nur bei Übereinstimmung (Abschnitt 7).
19. **Offen: Statusaufbau (Abschnitt 12).** Quellen der Felder, Abbildung von
    `leser` und die Kriterien der vier Prüfpunkte sind Vorschläge der
    Umsetzung; insbesondere `SPEICHER_MIN_FREI_MB` = 500 und „Netz ok nur mit
    Broker“. Tobias entscheidet, ob die Schwellen so passen.
20. **Offen: Position abgerundet** auf eine Nachkommastelle (3.8) und die
    Umsetzung von „MPD weg“ als Frist innerhalb des Zustands `spielt` (kein
    neuer Zustand, damit die Zustandsliste des Designs und der Status gleich
    bleiben).
