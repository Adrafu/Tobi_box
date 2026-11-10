# Kern-Schnittstelle (`core-interface`), Version 1

*   **Status:** Vertrag Stufe 0, Entwurf zur Prüfung durch einen Goldfisch
*   **Grundlage:** `docs/designs/box-software.md` (Baustein 3, „Kern-Zustände“,
    „Lautstärke“, „Uhr und Zeitquelle“, „Datenmodell und Dateien“)
*   **Eigentümer der Typen:** `box/src/tobibox/events.py`. `core.py` und die
    Teilautomaten **benutzen** die Typen nur. Wer einen Typ ändern will, wendet
    sich an die Projektleitung.
*   **Zusammenhang:** Zeilen des Lesers: `reader-v1.md`. Dateien und Schemas:
    `data-model.md`. MQTT: `mqtt-v1.md`.
*   **Änderung 05.11. (Entscheidung F, 05.11.):** Tobies zeigen auf eine Serie, eine
    einzelne Folge oder eine Aktion; eine Folge hat einen oder mehrere Tracks;
    der Zeiger hat einen Track; die Player-Ereignisse unterscheiden
    `TrackWechsel` und `FolgeZuEnde`; Vor / Zurück springen nach Track.
    Im Code heißt ein Tobie aus historischen Gründen `figur`; Namen wie
    `Aufgelegt` und `figur_liegt` bleiben unverändert.

*   **Änderung 07.11. (Entscheidung H, 07.11.):** Im Lernmodus wartet ein aufgelegter
    Tobie still auf die Antwort von HA (nichts spielt, nur der Lernton, Frist
    `LERN_ANTWORT_FRIST_S` = 10 s). `Bestaetigt` mit `art="gelernt"` erreicht jetzt
    auch den Kern (nur `session` beachtet es). Siehe Abschnitt 9, Punkt 8.

*   **Änderung 09.11. (Entscheidung I, 09.11.):** Ein kleiner Rest gilt als fertig gehört. Wird
    die Wiedergabe an einem gespeicherten Zeiger fortgesetzt und fehlen bis zum Ende der
    ganzen Folge weniger als `REST_FERTIG_S` = 15 s, beginnt ein Folgen-Tobie die Folge von
    vorn und eine Serie spielt die nächste Folge von vorn. `Serie` bekommt das Feld `dauern`,
    die Bibliothek füllt es aus den Dateien. Siehe Abschnitt 6.3 und Abschnitt 9, Punkt 30.

*   **Änderung 09.11. (Entscheidung J, 09.11.):** Die Töne folgen der Lautstärke des Hörspiels. Der
    Tonpegel ist die aktuelle Lautstärke der Sitzung (nach allen Grenzen), mindestens 10; die
    Verstärkung folgt derselben Kennlinie wie MPD. `ton_pegel` entfällt als Wirkung. Die Töne und die
    gesprochenen Testmedien liegen bei −18 LUFS. Siehe Abschnitt 8.1 und Abschnitt 9, Punkt 31.

*   **Änderung 09.11. (Entscheidung L, 09.11.):** Es spielen nie zwei Sachen gleichzeitig. Töne laufen
    einzeln und nacheinander; enthält eine Ausgabe Töne und `Abspielen`, startet die Wiedergabe erst nach dem
    Ende des letzten Tons. Ein Ton, der kommt, während MPD spielt, hält MPD kurz an und setzt es an derselben
    Stelle fort, ohne Zeiger. Der Kern bleibt unverändert und rein; die Regel steht in Abschnitt 6.5 und 8.1,
    Punkt 32. `data-model.md` ist nachgezogen (`ton_pegel`, `hinweis_pegel`).

*   **Änderung 09.11. (Befunde des Code-Reviews zu I, J und L, `docs/egm/software-prototyp/code_review_ijl.md`):**
    Die **Grenze gewinnt immer**: Für alle Töne, auch `hinweis`, ist `min(grenze, …)` der letzte Schritt; die
    Untergrenze 10 gilt nur, solange sie unter der Grenze liegt (8.1). Töne richten sich nach der **dauerhaften**
    Grenze und Lautstärke des Kerns, ohne die Rampen „ausblenden“ und „gute_nacht“, und der Pegel entsteht erst,
    wenn ein Ton an der Reihe ist (8.1). Die kurze Pause für einen Ton endet verlässlich bei einem echten
    `Pausieren`, bei `Abspielen`, bei Verbindungsverlust und bei der Klemmung; ein Ton, der mitten in einem Start
    kommt, wartet auf den Start (6.5 Punkt 6e). `audiodauer` meldet MP3 mit wechselnder Bitrate ohne Kopf als
    „Dauer unbekannt“, und die Restregel gilt nicht bei einer Position hinter dem Ende des Tracks (6.3).

*   **Änderung 09.11. (Entscheidung N, 09.11.):** Lesezeichen je Tobie mit Ablauf. Wurde ein Zeiger länger als
    `Konfig.lesezeichen_tage` (Vorgabe 14, `0` = nie) nicht benutzt, beginnt beim Fortsetzen dieselbe Folge von
    vorn (Track 0, Position 0). Dafür trägt `Zeiger` den Zeitpunkt der letzten Benutzung (`benutzt_wall`,
    `resume.json`: `benutzt_am`, optional), `ZeigerSpeichern` die Wanduhr (`wall`) und `Konfig` das Feld
    `lesezeichen_tage`. Die Regel gilt nur bei sicherer Uhr, an derselben Stelle wie die Restregel und geht ihr
    voran. Der Kern bleibt rein: Die Wanduhr kommt über `jetzt`. Siehe Abschnitt 6.3 und Abschnitt 9, Punkt 33.
    Alle Änderungen sind additiv; `schema_version` bleibt 2.

*   **Änderung 09.11. (Befunde des Code-Reviews zu AP 3.7 und AP 4.8, `docs/egm/software-prototyp/code_review_stufe3a_4.md`;
    Entscheidungen O und P von Tobias, Rev. 3.17):**
    *   **Entscheidung O: Leerlauf zählt auch mit liegendem Tobie.** Leerlauf heißt: 20 min lang (seit Ein/Aus, 10.11.: 10 min und nur ohne Strom) wird nichts gespielt, egal ob ein
        Tobie liegt. Es gelten weiter die Ausnahmen Sync, Update und Lernmodus; Bedienung setzt den Zähler zurück. Beim Einschalten
        spielt ein liegender Tobie wie bisher sofort weiter (Entscheidung G). Siehe Abschnitt 9, Punkt 9.
    *   **Entscheidung P: Ist der Kopfhörer-Kontakt nicht lesbar, gilt die Kopfhörer-Grenze** (Gehörschutz), bis er wieder lesbar ist,
        auch beim Start, solange die erste Messung fehlt. Neues Ereignis `KopfhoererLesbar`, HA bekommt `fehler` mit
        `code="kopfhoerer_unlesbar"`. Siehe Abschnitt 3.5 und 9, Punkt 15.
    *   **B1:** Ein fehlgeschlagenes Herunterfahren ist nicht endgültig. Neues Ereignis `HerunterfahrenFehlgeschlagen` (von `power`);
        `idle` verlässt `herunterfahren` und zählt neu, HA bekommt `fehler` mit `code="herunterfahren_fehlgeschlagen"`. Am Mac
        (Simulation) kehrt `idle` nach `SIMULATION_RUECKKEHR_S` = 10 s in den normalen Zustand zurück. Siehe 3.6 und 9, Punkt 9.
    *   **B12:** `AkkuTiefstand` gibt einmal `TonSpielen("akku_leer")` aus; der Dienst wartet vor dem Poweroff auf das Ende des Tons.
    *   **B13:** Während der Absenkung von „leiser“ richten sich Töne schon nach dem **Ziel** der Absenkung (8.1).
    *   **B16:** Bis Stufe 3b antwortet `UpdateStarten` an HA mit `befehl_abgelehnt` (`detail` „Update kommt mit Stufe 3b.“).
    *   Weitere Befunde (B2, B4 bis B11, B14, B15, B17) betreffen die Verdrahtung und stehen im Design (`box-software.md`) und in
        `docs/betrieb/`. Alle Änderungen am Vertrag sind additiv.

*   **Änderung 10.11. (Ein/Aus, 10.11.; Schritt 1; EGM `docs/egm/ein-aus/`, Entwurf Rev. 2, Entscheidungen R1 bis R11 in `resolve.md`):**
    *   **Am Strom immer bereit, ohne Strom nach 10 min aus.** `LEERLAUF_S` = 600 (vorher 1200). Die Frist zählt nur, solange kein
        Strom am Eingang liegt; Strom verwirft sie, Abnehmen beginnt sie neu (ab dem Abnehmen, R9). Siehe Abschnitt 9, Punkt 9.
    *   **„Lader“ heißt Strom am Eingang, aus jeder Quelle.** Neben `pisugar-server` liefert der Leser den Wert (Zeile `LADER`,
        `reader-v1.md`); bei Widerspruch gilt der Leser. `LaderGeaendert` bekommt das Feld `quelle`, `LeserHallo` das Feld `caps`.
    *   **Neuer Ton `lader`** beim Andocken einer laufenden Box (nicht in Leise-Zeiten, nicht beim Hören; Regel 6.2.2a).
    *   **Früher Start-Ton.** Ein Frühdienst spielt `start`, bevor der Box-Dienst läuft; `Bereit` trägt das Feld `fruehton`
        (Marke `/run/tobibox/fruehton`, `data-model.md`). Unter „stumm“ klingt er nicht, unter „leiser“ mit der Grenze des Fensters,
        sonst normal (R10).
    *   **Entfällt:** die Wiederholung des Start-Syncs am Lader (`START_WIEDERHOLUNG_S`, `START_WIEDERHOLUNGEN`).
    *   **Nachtrag 10.11. (Ein/Aus, 10.11.; Goldfisch-Review `docs/egm/ein-aus/review_vertraege_schritt1.md`, V1 bis V17; mit dem Code E1-1 bis E1-8):**
        `app` liest die Marke des Frühtons erst bei `Bereit` und legt die Gegenmarke `uebernommen` an (V1, 6.5g); der Leser-Wert gilt nur während
        seiner Verbindung (V2); ein erster Wert einer zweiten Quelle ist keine Andock-Rückmeldung (V3); die erste Messung stellt den Zustand sofort
        (V4); der Start-Ton entfällt unter „stumm“ ganz, kein `hinweis` als Ersatz (V5, Regel 6.2.2); neuer Befehl `AkkuAnzeigen` von `idle` an `led` (V6,
        Abschnitt 4); Quellen des Frühdienstes (V7, 8.1); ungültiges `caps` gilt als fehlend (V9); „Strom unbekannt“ zählt wie „kein Strom“ (V15);
        Widerspruch erst nach `STROM_WIDERSPRUCH_S` als WARNING (V16). Alle Änderungen sind additiv.
    *   Alle Änderungen sind additiv. Die Stellen für Wecken, Schlafen, Ring-Übergabe und Weiche (Schritt 2) folgen mit Schritt 2.

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
| `mono` | `float` | monotone Uhr in Sekunden, beliebiger Nullpunkt, springt nie rückwärts. **Alle Dauern und Fristen** (Leser-Frist 3 s, MPD-Frist 5 s, Lernmodus 2 min, Wartezeit auf HA im Lernmodus 10 s (Entscheidung H, 07.11.), Gute-Nacht-Timer, Leerlauf 10 min (seit Ein/Aus, 10.11.; vorher 20 min), Zeiger alle 30 s) laufen auf `mono`. |
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
| `LeserHallo` | `proto: int`, `fw: str`, `build: str`, `pn5180: str`, `caps: str = ""` (Ein/Aus, 10.11.) | gültiges `HELLO` (beim Start der Firmware oder auf `PING`). `caps` ist der Wert des optionalen Feldes `caps` unverändert (Liste durch Komma, z. B. `"strom"`); fehlt das Feld im `HELLO` oder ist sein Wert ungültig (V9, WARNING), ist `caps` `""`: Die Firmware hat keine Fähigkeit (so verhält sich auch eine Firmware vor Schritt 1). Der Dienst prüft nie `fw` auf Fähigkeiten, nur `caps`, und entscheidet daran, welche Zeilen er senden darf (`reader-v1.md`, Abschnitt 13). |
| `Aufgelegt` | `uid: str`, `typ: Literal["ntag","iso15693"]`, `tonie: bool`, `seq: int`, `vorgang: str` | `PLACED`. `uid` ist die kanonische Kennung, unverändert. |
| `Gesperrt` | `seq: int`, `vorgang: str` | `LOCKED` (nicht zuordenbar, keine Kennung). |
| `Abgehoben` | `seq: int`, `vorgang: str \| None` | `REMOVED`. `vorgang` ist der des zugehörigen Auflegens, `None`, wenn `reader` keines kennt (nur nach einem Neustart des Dienstes oder wenn das zugehörige Auflegen verloren ging; **nicht** nach einem `HELLO`, siehe unten). |
| `LeserHerzschlag` | `present: bool`, `up_s: int`, `polls: int`, `hits: int`, `rejected: int`, `errors: int`, `cycle_ms: int` | `HB`. |
| `LeserAlarm` | `grund: Literal["kein_herzschlag","getrennt","hello_timeout","proto_unbekannt"]` | Wächter-Alarm oder Verbindungsverlust; **ein** Alarm je Ausfall (Gründe und Regel: `reader-v1.md`, Abschnitt 12). `reader` verbindet sich danach selbst neu. |
| `LeserFehler` | `code: str`, `detail: str`, `schwere: Literal["fehler","warnung","hinweis"]` | `ERR`-Zeile des Lesers. `reader` setzt `schwere` aus der Tabelle in `reader-v1.md`, Abschnitt 7 (unbekannter Code: `warnung`). Die Sitzung wertet das Ereignis nicht aus; es dient dem Status (Abschnitt 12). |

Die Zeile `LADER` des Lesers (Ein/Aus, 10.11.) gibt `reader` als `LaderGeaendert(am_lader=(in == 1), quelle="leser")` weiter (Abschnitt 3.6). Sie erscheint nach jedem gültigen `HELLO` und bei jeder Änderung von `STROM_IN`; `reader` gibt auch eine unveränderte Wiederholung weiter (nach einem `HELLO`), `idle` wertet nur Wechsel aus (Abschnitt 9, Punkt 9). **(V2)** Der Wert des Lesers gilt nur, solange die Verbindung steht und er aus der aktuellen Verbindung stammt: `idle` löscht ihn bei `LeserAlarm` und bei jedem `LeserHallo` (der Wert kommt mit dem `LADER` nach dem `HELLO` neu); bis dahin gilt `pisugar`. `LADER` nach dem `HELLO` ist schon entprellt (die Firmware sendet erst nach `STROM_ENTPRELL_HOCH_MS`/`STROM_ENTPRELL_WEG_MS`, `reader-v1.md`).

*   **Vorgangs-ID:** `reader` erzeugt sie beim Empfang von `PLACED` oder
    `LOCKED`: 8 Zeichen `[0-9a-f]` aus einer Zufallsquelle. `reader` merkt sie
    sich bis zum zugehörigen `REMOVED` und gibt sie in `Abgehoben` mit.
    Ein `PLACED` nach einem `REMOVED` bekommt eine neue ID.
*   **Wiedermeldung nach `HELLO` behält die ID.** Kommt nach einem gültigen
    `HELLO` als **erste** `PLACED`/`LOCKED`-Zeile eine Meldung derselben
    Identität (gleiche Kennung bzw. beide `LOCKED`) wie der offene (noch nicht
    abgehobene) Tobie, ist das eine **Wiedermeldung**: `reader` behält die
    bestehende Vorgangs-ID. Das betrifft die Meldung auf `PING` und die
    Meldung nach einem Neustart der Firmware. **Bestätigt (05.11.):** Dasselbe
    gilt für die **erste** `PLACED`/`LOCKED`-Zeile mit `seq=0` oder nach einem
    erkannten `seq_reset` (`reader-v1.md`, Abschnitt 5), auch wenn kein `HELLO`
    ankam (das `HELLO` ging verloren, die Firmware wurde neu gestartet): bei
    gleicher Identität wie der offene Tobie ist es eine Wiedermeldung, `reader`
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
| `TrackWechsel` | `serie_id: str`, `datei: str`, `track: int`, `gen: int` | MPD ist innerhalb der Folge zum nächsten Track übergegangen und **spielt weiter** (keine Pause) (Entscheidung F, 05.11.). `track` ist die Nummer des neuen Tracks (ab 0). `serie_id` und `datei` sind die Werte des letzten `Abspielen`. **Beginnt `Abspielen` wegen fehlender Tracks nicht beim gewünschten Track, sendet der Player sofort nach dem Start ein `TrackWechsel` auf den Track, der wirklich spielt (vor der ersten `PlayerPosition`); die Sitzung nimmt es an (6.3) (06.11.).** |
| `FolgeZuEnde` | `serie_id: str`, `datei: str`, `gen: int` | MPD hat den **letzten Track** der Folge zu Ende gespielt und **gestoppt**: Die ganze Folge ist zu Ende (Entscheidung F, 05.11.). MPD startet nie von selbst die nächste Folge (die Warteschlange enthält nur die Tracks der aktuellen Folge). `serie_id` und `datei` (Name der Folge) sind die Werte des letzten `Abspielen`. |
| `PlayerPosition` | `serie_id: str`, `datei: str`, `track: int`, `position_s: float`, `spielt: bool`, `gen: int` | Abspielposition in Sekunden **im Track** (ohne Rücksprung). Der Player sendet sie alle `POSITION_INTERVAL_S` = 1,0 s, solange etwas spielt, und **einmal sofort** nach jedem `Pausieren`, jedem `Abspielen`, jedem `TrackWechsel` und jedem Folgenende (dann mit der Endposition des letzten Tracks). |
| `PlayerFehler` | `serie_id: str \| None`, `datei: str \| None`, `art: Literal["datei_fehlt","datei_unlesbar","mpd_fehler"]`, `detail: str` | Wiedergabefehler. `datei_fehlt`: Datei nicht im MPD-Bestand. `datei_unlesbar`: MPD kann sie nicht dekodieren. `mpd_fehler`: sonstiger Fehler eines MPD-Befehls. |
| `PlayerVerbindung` | `ok: bool` | Verbindung zu MPD verloren (`False`) oder wiederhergestellt (`True`). `player` verbindet sich selbst neu. |

Die Position ist eine Eigenschaft des Players, der Kern hält die zuletzt
gemeldete (`PlayerPosition`) im Zustand der Sitzung. Beim Abheben benutzt der
Kern diese Position für `ZeigerSpeichern`; sie ist höchstens
`POSITION_INTERVAL_S` alt. **Der Kern übernimmt eine `PlayerPosition` nur in den
Zuständen mit laufendem MPD (`spielt`, `unbekannt`) und nur, wenn `serie_id`,
`datei` und `track` zum aktuellen Zeiger der Sitzung passen; sonst wird sie
ignoriert (6.3) (Entscheidung F, 05.11.).**

**Wiedergabe-Generation `gen` (06.11.):** `Abspielen` trägt `gen: int`. Die Sitzung
erhöht die Zahl bei jedem `Abspielen` um 1 (Start, Hauptknopf, Weiter, Zurück,
Wiederaufnahme nach MPD-Ausfall). Der Player merkt sich die `gen` des letzten
`Abspielen` und trägt sie in jedes `PlayerPosition`, `TrackWechsel` und
`FolgeZuEnde` ein. **Die Sitzung ignoriert diese Ereignisse, wenn `gen` nicht der
aktuellen Generation entspricht** (Nachzügler einer früheren Wiedergabe, etwa eine
alte Position nach Zurück im selben Track oder ein altes `FolgeZuEnde` nach Weiter
auf dieselbe Folge). `gen` gehört nicht zur Gleichheit der Typen (Tests prüfen es gezielt).

### 3.3 Start und Daten (Quelle `app`, `store`, `library`, `ha`)

| Ereignis | Felder | Quelle | Bedeutung |
|---|---|---|---|
| `GeraeteEinstellungen` | `lautstaerke_max: int`, `lautstaerke_start: int`, `lautstaerke_kopfhoerer: int`, `neustart_uid: str \| None = None` | `app` aus `tobibox.toml` und `lauf.json` | je 0 bis 100. Der Kern setzt die Grenze `global` und die Startlautstärke daraus (Abschnitt 8). Kommt als **erstes** Ereignis. **`neustart_uid` (Entscheidung G, 06.11.):** Kennung des Tobies, der laut `lauf.json` beim Dienst-Neustart ohne Ausschalten auflag (gleiche Kennung des Starts, siehe `data-model.md`); sonst `None` (Einschalten, CUJ 20). Dieser Tobie startet nicht von selbst (6.3, Punkt 12). |
| `KonfigGeladen` | `konfig: Konfig` | `app` beim Start (aus `config.json`), `ha` nach angenommener Liste | Zuordnungen, Leise-Zeiten, Gute-Nacht-Einstellungen (Typen in 3.8). Ersetzt die bisherige Konfiguration vollständig. |
| `BibliothekGeladen` | `serien: tuple[Serie, ...]` | `app` beim Start (aus `library`), `library` nach jedem Sync und nach Änderungen im Medienordner | Alle Serien mit ihren Folgen in der maßgeblichen Reihenfolge. Ersetzt die bisherige Bibliothek. |
| `ResumeGeladen` | `zeiger: tuple[Zeiger, ...]` | `app` beim Start (aus `resume.json`) | Gespeicherte Zeiger. Kommt einmal. |
| `Bereit` | `fruehton: bool = False` (Ein/Aus, 10.11.) | `app` | Alle vorigen Daten sind geliefert und MPD ist erreichbar. Bis `Bereit` hält `app` alle Ereignisse des Lesers in der Warteschlange zurück (Reihenfolge bleibt). Bei `Bereit` spielt der Kern den Start-Ton (CUJ 20: ein beim Start liegender Tobie kommt als `Aufgelegt` direkt danach). **`fruehton=True` (Ein/Aus, 10.11.):** Der Frühdienst hat den Start-Ton schon entschieden (gespielt oder bewusst unterlassen); `session` spielt dann **keinen** `start` und auch keinen `hinweis` an seiner Stelle. `app` setzt das Feld aus der Marke `/run/tobibox/fruehton`, die es **bei `Bereit`** liest (Abschnitt 6.5, Punkt 6g; `data-model.md`, 1.6; V1). Ohne Marke (Dienst-Neustart, Frühdienst fehlt oder zu spät, Marke `fehler`) ist es `False`, und der Kern spielt `start` wie bisher (unter „stumm“ nichts, V5). |

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
| `Bestaetigt` | `id: str`, `grund: str`, `zuletzt: str`, `art: Literal["unbekannt","gelernt"]` | Bestätigung von HA für einen gemeldeten Eintrag (Abschnitt 7). `zuletzt` und `art` sind die Werte der veröffentlichten Meldung, die HA bestätigt. `app` gibt sie zuerst an `outbox`. **Mit `art="gelernt"` geht sie danach auch an den Kern, aber nur wenn `outbox` sie angenommen hat** (offener Eintrag mit passendem `zuletzt` und `art`; eine veraltete oder doppelte Bestätigung erreicht den Kern nicht) (Entscheidung H, 07.11.): `session` beendet damit das Warten im Lernmodus, wenn `grund="abgelehnt"` und `id` die Kennung des wartenden Tobies ist (Abschnitt 9, Punkt 8). Mit `art="unbekannt"` geht sie nicht an den Kern. |

### 3.5 Bedienung und Kopfhörer (Quelle `controls`, `headphones`; in der Simulation `sim`)

| Ereignis | Felder | Bedeutung |
|---|---|---|
| `Hauptknopf` | `art: Literal["kurz","lang"]` | kurzer oder langer Druck. |
| `Weiter` | – | nächster Track der Folge (Taste „Vor“); beim letzten Track Regel in Abschnitt 9, Punkt 12 (Entscheidung F, 05.11.). |
| `Zurueck` | – | voriger Track bzw. aktuellen Track neu starten (Taste „Zurück“), Regel in Abschnitt 9, Punkt 12 (Entscheidung F, 05.11.). |
| `LautstaerkeDrehen` | `delta: int` | Drehregler, in Prozentpunkten (positiv lauter). |
| `Kopfhoerer` | `steckt: bool` | Stecker erkannt (`True`) oder gezogen. |
| `KopfhoererLesbar` | `lesbar: bool` | Der Schaltkontakt der Buchse ist nicht (mehr) lesbar (`False`, einmal je Störung, auch wenn schon die erste Messung beim Start scheitert) oder wieder lesbar (`True`, erst nach einem stabilen Wert und nach dem zugehörigen `Kopfhoerer`). `session` hält solange die Grenze `kopfhoerer` (Entscheidung P, 09.11.; Punkt 9.15). Der Ausgang ändert sich nicht. |

Quellen am Pi (09.11., AP 4.8): `Hauptknopf` (kurz und lang) kommt von `power` (Taste des PiSugar) oder von `controls` (Knopf am GPIO, `pin_haupt` in `[tasten]`). **B2 (Review, 09.11.):** Für `power` ist in der Dokumentation des `pisugar-server` kein Befehl belegt, der Tastenereignisse liefert. Die Abfrage (`power.taste_lauf`) ist deshalb hinter `[strom] taste_befehl` verdrahtet (Vorgabe: aus) und **am Pi zu prüfen**; ohne `taste_befehl` und ohne `pin_haupt` warnt der Dienst beim Start (`docs/betrieb/pisugar-wecker.md`, Abschnitt „Hauptknopf“). `Kopfhoerer` kommt von der Buchse (`headphones`) und wird über 2 Messungen entprellt: Ein neuer Wert gilt erst, wenn zwei Messungen hintereinander ihn zeigen.

### 3.6 Strom, Netz, Sync, Update

| Ereignis | Felder | Quelle | Bedeutung |
|---|---|---|---|
| `LaderGeaendert` | `am_lader: bool`, `quelle: Literal["pisugar","leser"] = "pisugar"` (Ein/Aus, 10.11.) | `power` (`quelle="pisugar"`), `reader` (`quelle="leser"`) | **Strom am Eingang der Box, aus jeder Quelle** (Netzteil, Sockel, Kabel, Powerbank; vorher „am Lader“). `power` meldet `battery_power_plugged` des `pisugar-server`, `reader` den Wert `in` der Zeile `LADER`. Jede Quelle meldet bei einer Änderung und einmal beim ersten bekannten Wert. **Bei Widerspruch gilt der Leser** (`idle` führt die Werte zusammen und protokolliert den Widerspruch, Abschnitt 9, Punkt 9). |
| `AkkuStand` | `prozent: int` | `power` | 0 bis 100; nur zur Information und für `sync`. |
| `AkkuTiefstand` | – | `power` | Akku kritisch leer, Box nicht am Lader. |
| `HerunterfahrenFehlgeschlagen` | `detail: str` (Standard `""`), `simuliert: bool` (Standard `False`) | `power` (`app`, wenn es kein `power` gibt) | Der Befehl `Herunterfahren` hat nicht gewirkt (09.11., B1): das Kommando fehlt, endete mit Rückgabecode ungleich 0 oder brauchte länger als `ABSCHALT_FRIST_S` (`simuliert=False`, `detail` nennt den Grund); oder das Herunterfahren wurde nur protokolliert (Mac, `simuliert=True`). `idle` reagiert in `herunterfahren` darauf (Punkt 9.9). Nach einem Fehler meldet `power` einen fortbestehenden Tiefstand frühestens nach `TIEFSTAND_WIEDERHOLEN_S` = 60 s wieder. |
| `NetzKlasse` | `klasse: Literal["home","hotspot","offline"]` | `net` | bei Änderung und einmal beim Start. |
| `SyncGestartet` | – | `sync` | |
| `SyncFertig` | `neu: int`, `geloescht: int` | `sync` | `neu` = übertragene Dateien. |
| `SyncAbgebrochen` | `grund: str` | `sync` | z. B. `quelle_leer`, `zu_viele_loeschungen`, `kein_platz`, `akku_tiefstand`, `netz_weg`, `regel`, `nicht_eingerichtet` (09.11., AP 4.8: aus `app`, wenn `[sync]` fehlt). **Keine Wiederholung am Lader** (Ein/Aus, 10.11.: die Wiederholung des Start-Syncs entfällt; den nächsten Anstoß geben der Takt, das Andocken und HA, Abschnitt 9, Punkt 9). |
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
| `Serie` | `id: str`, `name: str`, `typ: Literal["normal","ueberraschung"]`, `ordner: str` (Pfad relativ zum Medienordner), `folgen: tuple[str, ...]` (Namen der Folgen in maßgeblicher Reihenfolge, nur vorhandene: Dateiname oder Ordnername), `tracks: Mapping[str, tuple[str, ...]]` (Name der Folge → Pfade ihrer Tracks **relativ zum Serien-Ordner** in Reihenfolge; eine Folge aus einer Datei hat genau einen Track, nämlich ihren eigenen Namen, ein Folgen-Ordner `Ordnername/Dateiname`; so stehen sie unverändert in `Abspielen.tracks`) (Entscheidung F, 05.11.), `dauern: Mapping[str, tuple[float \| None, ...]]` (Name der Folge → Dauer jedes Tracks in Sekunden, parallel zu `tracks`; `None` oder fehlender Eintrag: Dauer unbekannt; Standard leer) (Entscheidung I, 09.11.) |
| `Zeiger` | `art: Literal["serie","folge"]` (Serien-Zeiger oder Folgen-Zeiger) (Entscheidung F, 05.11.), `serie_id: str`, `datei: str` (Name der Folge), `index: int \| None` (Nummer der Folge in `folgen`, ab 0, Hinweis für den Fall einer fehlenden Folge; `None` bei `art="folge"`), `track: int` (≥ 0, Nummer des Tracks in der Folge), `position_s: float` (≥ 0, Sekunden im Track, ohne Rücksprung), `zaehler: int`, `benutzt_wall: float \| None` (Wanduhr der letzten Benutzung in Unix-Sekunden; `None` = unbekannt, der Zeiger läuft nie ab; Standard `None`) (Entscheidung N, 09.11.) |
| `Zuordnung` | `typ: Literal["serie","folge","aktion"]`, `serie_id: str \| None`, `folge: str \| None` (Name der Folge bei `typ="folge"`), `aktion: Literal["status","gute_nacht"] \| None` (Entscheidung F, 05.11.) |
| `Fenster` | `id: str`, `tage: tuple[int, ...]` (1 = Montag bis 7 = Sonntag), `von: str`, `bis: str` (`"HH:MM"`, Ortszeit), `wirkung: Literal["leiser","stumm"]`, `grenze: int \| None` |
| `LeiseZeiten` | `zeitzone: str` (IANA), `fenster: tuple[Fenster, ...]` |
| `GuteNacht` | `timer_min: int`, `ausblenden_s: int` |
| `Konfig` | `revision: int`, `liste_id: str`, `zuordnungen: Mapping[str, Zuordnung]` (Schlüssel = Kennung), `leise_zeiten: LeiseZeiten`, `gute_nacht: GuteNacht`, `lesezeichen_tage: int` (0 bis 365, Standard 14; `0` = Lesezeichen laufen nie ab) (Entscheidung N, 09.11.) |
| `Eintrag` (von `outbox.offen()`) | `uid: str`, `art: Literal["unbekannt","gelernt"]`, `zuerst: str`, `zuletzt: str`, `anzahl: int`, `zeit_ok: bool`, `befehl_id: str \| None` (die Felder von `unknown.json`, `data-model.md` Abschnitt 4, plus der Schlüssel `uid`) |

Wertebereiche und Bedeutung der Felder: `data-model.md`. `events.py` übernimmt
die Werte aus den Schemas; die **Namen weichen an einigen Stellen ab** und
werden so abgebildet:

| JSON (`data-model.md`) | Typ in `events.py` |
|---|---|
| `resume.json`: `serien` (Objekt, Schlüssel = Serien-ID) und `folgen` (Objekt, Schlüssel = Serien-ID, darunter Schlüssel = Name der Folge) | `ResumeGeladen.zeiger: tuple[Zeiger, ...]`, ein `Zeiger` je Eintrag; `art="serie"` für `serien`, `art="folge"` für `folgen` (Entscheidung F, 05.11.) |
| `serien.<id>` (Schlüssel) bzw. `folgen.<id>` (Schlüssel) | `Zeiger.serie_id` |
| `serien.<id>.folge` bzw. `folgen.<id>.<folge>` (Schlüssel) | `Zeiger.datei` |
| `serien.<id>.index`, `.track`, `.position_s`, `.zaehler` | `Zeiger.index`, `.track`, `.position_s`, `.zaehler` (gleiche Namen); bei `folgen` ist `index` = `None` |
| `serien.<id>.benutzt_am` bzw. `folgen.<id>.<folge>.benutzt_am` (Zeitstempel, optional) | `Zeiger.benutzt_wall` (Unix-Sekunden; fehlt das Feld: `None`) (Entscheidung N, 09.11.) |
| `config.json`: `zuordnungen.<uid>.ziel.serie` / `.folge` | `Zuordnung.serie_id` / `Zuordnung.folge` (und `ziel.typ` → `typ`, `ziel.aktion` → `aktion`) (Entscheidung F, 05.11.) |
| `zuordnungen` (Objekt, Schlüssel = Kennung) | `Konfig.zuordnungen: Mapping[str, Zuordnung]` |
| `leise_zeiten.fenster[].tage / von / bis / wirkung / grenze / id` | `Fenster.tage / von / bis / wirkung / grenze / id` (gleiche Namen; `tage` als `tuple`) |
| `leise_zeiten.zeitzone` (fehlt: `Europe/Berlin`) | `LeiseZeiten.zeitzone` (immer gesetzt) |
| `gute_nacht.timer_min`, `.ausblenden_s` | `GuteNacht.timer_min`, `.ausblenden_s` |
| `config.json`: `lesezeichen_tage` (fehlt: 14) | `Konfig.lesezeichen_tage` (immer gesetzt) (Entscheidung N, 09.11.) |
| `config.json`: `erzeugt_am`, `schema_version` | kein Feld in `Konfig` (nur Anzeige bzw. Format) |
| `serie.json`: `id`, `name`, `typ`, `ordner` (aus dem Pfad), `folgen` | `Serie.id`, `.name`, `.typ`, `.ordner`, `.folgen`; `Serie.tracks` liest `library` aus dem Dateisystem (Folgen-Ordner), nicht aus `serie.json` |

`position_s` wird beim Speichern auf **eine Nachkommastelle abgerundet**
(`floor(x · 10) / 10`), damit der gespeicherte Zeiger nie weiter vorn liegt als
die tatsächliche Position. „Unverändert“ im Sinne von `ZeigerSpeichern` heißt: gleiche Art, gleiche Folge,
gleicher Index, gleicher Track und gleiche so abgerundete Position (und kein Zeitstempel, der erneuert werden müsste,
siehe `ZeigerSpeichern`, Entscheidung N, 09.11.).

### 3.9 Interne Ereignisse (zwischen Teilautomaten)

Teilautomaten melden einander Dinge, indem sie ein **internes Ereignis**
zurückgeben. `core` nimmt sie aus der Ausgabe heraus und gibt sie in derselben
Verarbeitung an alle Teilautomaten weiter (Abschnitt 6.1). Sie sind
Unterklassen von `InternesEreignis` und verlassen den Kern nie.

| Ereignis | Felder | Sender → Empfänger | Bedeutung |
|---|---|---|---|
| `SitzungGeaendert` | `zustand: str`, `figur_liegt: bool`, `spielt: bool`, `serie_id: str \| None` | `session` → `idle`, `bedtime` | Zustand der Wiedergabe-Sitzung hat sich geändert. `figur_liegt` gilt auch für Aktionskarten. |
| `AktionAusgeloest` | `aktion: Literal["status","gute_nacht"]`, `vorgang: str` | `session` → `bedtime` (und `core` für `status`) | Aktionskarte wurde aufgelegt. |
| `LernenGeaendert` | `aktiv: bool` | `learn` → `idle`, `session` | Lernmodus beginnt oder endet. `session` merkt sich den Wert (Entscheidung H, 07.11.): Ein `Aufgelegt` mit Kennung, das bei `aktiv=True` eintrifft, wird nicht gespielt, sondern abgewartet. Die Sitzung sieht `Aufgelegt` vor `learn` (feste Reihenfolge, 6.1), also noch mit `aktiv=True`. |
| `StummBeginnt` | – | `quiet` → `session` | ein „stumm“-Fenster beginnt. Bei nicht vertrauenswürdiger Zeit gibt es nie „stumm“ (`data-model.md`, Abschnitt 2). |
| `StummEndet` | – | `quiet` → `session` | ein „stumm“-Fenster endet. |
| `GrenzeGesetzt` | `name: str`, `prozent: int \| None` | `quiet`, `bedtime`, `session` → `core` | setzt (`int`) oder löscht (`None`) die benannte Lautstärke-Grenze (Abschnitt 8). `core` behandelt sie selbst, die Teilautomaten sehen sie nicht. |
| `LautstaerkeGeaendert` | `wirksam: int` | `core` → alle Teilautomaten | die **wirksame Lautstärke** (`klemmen(wunsch, grenzen)`) hat sich geändert (und einmal nach `GeraeteEinstellungen`). Die Teilautomaten sind reine Funktionen und kennen `wunsch` und `grenzen` nicht; sie merken sich den zuletzt gemeldeten Wert und benutzen ihn als **Startwert einer Rampe** (Abschnitt 8) und für die Entscheidung „laute Wiedergabe“ (`wirksam` größer als die Zielgrenze). |
| `GuteNachtEnde` | – | `bedtime` → `session` | Das Ausblenden von „Gute Nacht“ hat die Lautstärke 0 erreicht; die Sitzung pausiert (9, Punkt 6). |
| `HerunterfahrenAngefordert` | `grund: Literal["leerlauf","hauptknopf","akku_tiefstand"]` | `idle` → `session`, `core` | Herunterfahren ist beschlossen. `session` pausiert und speichert den Zeiger; `core` hängt danach den Befehl `Herunterfahren` an. |
| `DienstEndet` | – | `app` → `session` | Der Dienst wird beendet (SIGTERM). `session` pausiert und speichert den Zeiger (`spielt` und `unbekannt`); `core` hängt **keinen** Befehl `Herunterfahren` an. |

## 4. Befehle

Alle Befehle sind Unterklassen von `Befehl`. `app.py` führt sie aus. Die Tabelle
nennt, wer sie ausführt.

| Befehl | Felder | Ausführer | Bedeutung |
|---|---|---|---|
| `LautstaerkeSetzen` | `prozent: int`, `grenze: int` | `player` | MPD-Lautstärke setzen. Immer `0 ≤ prozent ≤ grenze ≤ 100`. `player` klemmt zusätzlich selbst auf `grenze`, falls ein Aufrufer sich irrt. |
| `AusgangWaehlen` | `ausgang: Literal["lautsprecher","kopfhoerer"]` | `player` | Ausgang umschalten (Mac: nur protokolliert). |
| `Abspielen` | `serie_id: str`, `ordner: str`, `datei: str` (Name der Folge), `tracks: tuple[str, ...]` (Pfade der Tracks relativ zu `ordner`, in Reihenfolge), `track: int`, `position_s: float`, `vorgang: str \| None`, `gen: int` (06.11.) | `player` | Warteschlange leeren, **alle Tracks dieser Folge und nur diese** laden, auf Track `track` und `position_s` springen (`seek`), spielen (Entscheidung F, 05.11.). `position_s` ist die Position im Track und enthält schon den Rücksprung (Abschnitt 6.3). Der Pfad für MPD ist `ordner + "/" + tracks[i]`; bei einer Folge aus einer Datei ist `tracks = (datei,)`, bei einem Folgen-Ordner `tracks = (datei + "/" + trackname, …)`. |
| `Pausieren` | `grund: Literal["abgehoben","folgenende","knopf","stumm","gute_nacht","leser_unbekannt","fehler","herunterfahren"]` | `player` | Pause. Ist MPD schon gestoppt (Folgenende), ist der Befehl wirkungslos. Danach sendet der Player sofort `PlayerPosition`. |
| `ZeigerSpeichern` | `art: Literal["serie","folge"]`, `serie_id: str`, `datei: str`, `index: int \| None`, `track: int`, `position_s: float`, `grund: Literal["pause","folgenende","trackwechsel","zurueck","figurwechsel","periodisch","herunterfahren"]` (`zurueck`: Zurück in `beendet`, 9.12) (Entscheidung F, 05.11.), `wall: float \| None` (Wanduhr der Benutzung in Unix-Sekunden, aus `jetzt.wall` und nur bei `jetzt.zeit_ok`, sonst `None`; Standard `None`; zählt beim Vergleich zweier Befehle nicht mit) (Entscheidung N, 09.11.) | `store` (`resume.json`) | Zeiger schreiben (`art="serie"` in `serien`, `art="folge"` in `folgen`), `zaehler` dieses Zeigers um 1 erhöhen (Entscheidung F, 05.11.). `position_s` ist abgerundet auf 1 Nachkommastelle (Abschnitt 3.8). `store` schreibt nicht, wenn Art, Folge, Index, Track und Position unverändert sind, **außer** der Zeitstempel fehlt oder ist mindestens `STEMPEL_ERNEUERN_S` = 3600 s alt und `wall` ist gesetzt: Dann wird der Zeiger mit neuem `benutzt_am` geschrieben (Benutzung ohne neue Position, zum Beispiel Auflegen und gleich Abheben; Entscheidung N, 09.11.). Ist `wall` `None`, bleibt ein vorhandener Zeitstempel stehen, und ein Zeiger ohne Zeitstempel bekommt keinen. |
| `TonSpielen` | `ton: Literal["start","unbekannt","fehler","hinweis","lernen_beginn","lernen_ende","akku_leer","lader","pruef_ok","pruef_fehler"]` (`lader`: Ein/Aus, 10.11.) | `sounds` | kurzer Rückmeldeton (Datei `box/sounds/<ton>.wav`, `pruef_*` in AP 2.3). `lader` („Strom ist da“) kommt von `idle` beim Andocken einer laufenden Box (Abschnitt 9, Punkt 9); Regel 6.2.2a, Pegel 8.1. Töne laufen nacheinander und nie gleichzeitig; ein `Abspielen` derselben Ausgabe startet erst nach dem Ende der Töne (Abschnitt 6.5, Punkt 6; Entscheidung L, 09.11.). Die Status-Karte spielt außerdem die Prüfpunkt-Töne `pruef_<punkt>_ok` und `pruef_<punkt>_fehler` mit `<punkt>` ∈ {`leser`, `medien`, `netz`, `speicher`} sowie `pruef_leser_simulation` (09.11., Sprach-Töne für Tests); sie stehen nicht in `TonSpielen`, sondern in der Tonfolge von `selftest`. Fehlt eine solche Datei im Tonordner, spielt `sounds` stattdessen `pruef_ok` bzw. `pruef_fehler`. |
| `StatusPruefen` | `vorgang: str \| None` | `selftest` | Prüfpunkte Leser, Medien, Netz, Speicher in dieser Reihenfolge nach den Kriterien aus Abschnitt 12.3 prüfen und je Punkt einen Ton spielen (`pruef_<punkt>_ok` oder `pruef_<punkt>_fehler`, Leser in der Simulation `pruef_leser_simulation`; Rückfall auf `pruef_ok`/`pruef_fehler`, siehe `TonSpielen`; 09.11., Sprach-Töne für Tests) (Status-Admin-Karte, CUJ 11). `selftest` wertet aus und lässt `sounds` die Töne spielen; ausgeführt wird der Befehl nur von `selftest`. |
| `Melden` | `art: Literal["unbekannt","gelernt"]`, `uid: str`, `befehl_id: str \| None` | `outbox` | Eintrag in `unknown.json`, Veröffentlichung an HA, Löschen erst nach Bestätigung (Abschnitt 7). `befehl_id` ist bei `gelernt` die ID des Lernbefehls, sonst `None`. |
| `EreignisSenden` | `art: Literal["fehler","befehl_abgelehnt"]`, `daten: Mapping[str, str \| int \| bool \| None]` | `ha` | Meldung an HA ohne Bestätigung (`…/event`). `befehl_abgelehnt` hat `daten = {"befehl": <lernen\|sync\|update>, "befehl_id": <str>, "grund": <bedingung\|zeit_unsicher>}` und optional `"detail"` (09.11., AP 4.8; Texte in Abschnitt 9, Punkt 9: „Die Box ist nicht im Heimnetz.“, „Die Box hängt nicht am Lader.“, „Es läuft gerade ein Hörspiel.“, „Es läuft gerade ein Sync.“, „Es läuft schon ein Update.“); `lernen_abbrechen` wird nie abgelehnt. Bis Stufe 3b beantwortet `app` `UpdateStarten` mit `befehl_abgelehnt` (`befehl="update"`, `grund="bedingung"`, `detail="Update kommt mit Stufe 3b."`, B16, 09.11.). `art="fehler"` aus dem Kern: `baustein="kopfhoerer"`, `code="kopfhoerer_unlesbar"` (`session`, Entscheidung P) und `baustein="power"`, `code="herunterfahren_fehlgeschlagen"` (`idle`, B1), jeweils mit `text`. Die Meldungen `liste_abgelehnt`, `v_unbekannt` und `befehl_unbekannt` entstehen **nicht** im Kern, sondern direkt in `ha` (Abschnitt 9, Punkt 9). |
| `ZustandMelden` | `sitzung: str`, `strom: Literal["aktiv","leerlauf","herunterfahren"]`, `serie_id: str \| None`, `lernmodus: bool`, `ruhe: Literal["normal","leiser","stumm"]`, `gute_nacht: Literal["aus","laeuft","ausblenden"]`, `figur_liegt: bool`, `folge: str \| None = None`, `track: int \| None = None` (Name der aktuellen Folge und Nummer des Tracks, für das optionale Statusfeld `folge`, 12.1) (Entscheidung F, 05.11.) | `ha` (Statussammler, Abschnitt 12), `led` | Sammelzustand für Status-Sensoren und LED-Ring. `core` erzeugt ihn bei jeder Änderung (6.1, Schritt 6). Den Status-JSON baut nicht der Kern, sondern der Statussammler in `ha` (Abschnitt 12). |
| `AkkuAnzeigen` | `grund: Literal["andocken","abziehen"]`, `dauer_s: float` (Ein/Aus, 10.11., V6) | `led` | Der Ring zeigt den Ladestand (die Akku-Füllstand-Anzeige, Farbe blau mit Strom, sonst nach Prozent) `dauer_s` lang: 5 s, spielt die Sitzung 3 s. **Schnittstelle von `idle` an `led`:** `idle` gibt ihn aus, wenn Rückmeldungen frei sind (erste Messung vorbei, Sperre `LADER_SPERRE_S` abgelaufen). Er ist ein Befehl und kein internes Ereignis, weil interne Ereignisse den Kern nicht verlassen; `led` sieht die Befehle wie bei `Melden` (`nachfuehrung.stufe_4`). `app` führt ihn nicht aus. Die Start-Anzeige beim Start mit Strom ist kein `AkkuAnzeigen`, sondern `led` allein (Abschnitt 9, Punkt 9, Nr. 4). |
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
| `session.py` | Wiedergabe-Sitzung | `leer`, `spielt`, `pausiert`, `beendet`, `gehalten`, `unbekannt` | `GeraeteEinstellungen`, `KonfigGeladen`, `BibliothekGeladen`, `ResumeGeladen`, `Bereit`, `Aufgelegt`, `Gesperrt`, `Abgehoben`, `LeserHallo`, `LeserAlarm`, `LeserHerzschlag`, `LautstaerkeGeaendert`, `TrackWechsel`, `FolgeZuEnde`, `PlayerPosition`, `PlayerFehler`, `PlayerVerbindung`, `Hauptknopf`, `Weiter`, `Zurueck`, `Kopfhoerer`, `KopfhoererLesbar` (Entscheidung P), `Takt`, `StummBeginnt`, `StummEndet`, `LernenGeaendert`, `Bestaetigt` (nur `art="gelernt"`, Entscheidung H, 07.11.), `GuteNachtEnde`, `HerunterfahrenAngefordert`, `DienstEndet` | `Abspielen`, `Pausieren`, `ZeigerSpeichern`, `TonSpielen`, `Melden`, `AusgangWaehlen`, `LeserPing`, `EreignisSenden` (nur `fehler` bei `KopfhoererLesbar`), `Protokoll`; intern `SitzungGeaendert`, `AktionAusgeloest`, `GrenzeGesetzt` (`kopfhoerer`, `ausblenden`) |
| `learn.py` | Lernmodus | `aus`, `lernt` | `HaLernmodus`, `HaLernmodusAbbruch`, `Aufgelegt`, `Gesperrt`, `Takt` | `TonSpielen`, `Melden`, `EreignisSenden`, `Protokoll`; intern `LernenGeaendert` |
| `quiet.py` und `bedtime.py` | Ruhe-Regeln | `quiet`: `normal`, `leiser`, `stumm`; `bedtime`: `aus`, `laeuft`, `ausblenden` | `KonfigGeladen`, `Takt`, `ZeitquelleGeaendert`, `LautstaerkeGeaendert` (`quiet`); `KonfigGeladen`, `Takt`, `AktionAusgeloest`, `Abgehoben`, `LautstaerkeGeaendert` (`bedtime`) | `Protokoll`; intern `StummBeginnt`, `StummEndet`, `GrenzeGesetzt` (`leise_zeit`, `ausblenden` aus `quiet`; `gute_nacht` aus `bedtime`), `GuteNachtEnde` (aus `bedtime`) |
| `idle.py` | Strom / Leerlauf | `aktiv`, `leerlauf`, `herunterfahren` | `SitzungGeaendert`, `LernenGeaendert`, `Takt`, `Hauptknopf` (lang), `Hauptknopf` (kurz), `Weiter`, `Zurueck`, `LautstaerkeDrehen`, `Kopfhoerer` (09.11., AP 4.8: Bedienung setzt den Leerlauf-Zähler zurück), `AkkuTiefstand`, `LaderGeaendert`, `NetzKlasse`, `SyncGestartet`, `SyncFertig`, `SyncAbgebrochen`, `UpdateGestartet`, `SelbsttestErgebnis`, `HaSyncAnstossen`, `HaUpdateAnstossen`, `Bereit`, `HerunterfahrenFehlgeschlagen` (09.11., B1), `LeserHallo`, `LeserAlarm` (nur um den Strom-Wert des Lesers zu löschen, V2) | `SyncStarten`, `SyncAbbrechen`, `UpdateStarten`, `EreignisSenden`, `TonSpielen` (`akku_leer` beim Tiefstand, B12; `lader` beim Andocken, Ein/Aus, 10.11.), `AkkuAnzeigen` (V6), `Protokoll`; intern `HerunterfahrenAngefordert`. **(Ein/Aus, 10.11.)** `LaderGeaendert` kommt von zwei Quellen (`quelle`); die Frist zählt nur ohne Strom (Abschnitt 9, Punkt 9). |

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
| Track-Wechsel (MPD spielt den nächsten Track) (Entscheidung F, 05.11.) | `TrackWechsel` |
| Folge zu Ende (nach dem letzten Track) | `FolgeZuEnde` |
| Vor / Zurück | `Weiter` / `Zurueck` |
| Wächter-Alarm (kein `HB`) | `LeserAlarm` |
| `HELLO` | `LeserHallo` |
| Hauptknopf kurz / lang | `Hauptknopf(art=…)` |
| stumm beginnt / endet | `StummBeginnt` / `StummEndet` |
| Uhr erreicht Fenster, Fenster endet | `Takt` mit `jetzt.wall` (`quiet`) |
| Kopfhörer rein / raus | `Kopfhoerer(steckt=…)` |
| HA-Befehl Lernmodus / abbrechen | `HaLernmodus` / `HaLernmodusAbbruch` |
| Frist 2 min | `Takt` mit `jetzt.mono ≥ Frist` |
| Frist 10 s auf HA im Lernmodus (Entscheidung H, 07.11.) | `Takt` mit `jetzt.mono ≥ Frist` |
| HA lehnt den gelernten Tobie ab (Entscheidung H, 07.11.) | `Bestaetigt` mit `art="gelernt"`, `grund="abgelehnt"` |
| Start mit liegendem Tobie | `Aufgelegt` nach `Bereit` (`app` hält Leser-Ereignisse bis `Bereit` zurück) |
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
    `TonSpielen` mit `ton ∈ {unbekannt, lernen_beginn, lernen_ende, fehler, akku_leer}`
    durch `TonSpielen("hinweis")` ersetzt. **`start` wird unter „stumm“ gestrichen, nicht ersetzt** (V5, Ein/Aus, 10.11.; R10: beim Einschalten
    kein Ton unter „stumm“, auch nicht als Rückfall ohne Frühdienst oder nach einem Dienst-Neustart). `pruef_ok` und `pruef_fehler` bleiben. `lader` gehört
    **nicht** dazu (Regel 2a).
2a. **Lader-Ton (Ein/Aus, 10.11.):** `TonSpielen("lader")` wird **gestrichen** (nicht durch `hinweis`
    ersetzt), wenn `quiet` nicht im Zustand `normal` ist (also in einem Fenster „leiser“ oder „stumm“),
    wenn `jetzt.zeit_ok` falsch ist oder wenn der Lernmodus läuft. Spielt die Sitzung (`spielt`, `unbekannt`),
    gibt `idle` den Ton gar nicht erst aus (Abschnitt 9, Punkt 9; Entscheidung L: nur Ring).
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

*   **Auflegen, Ziel `serie` (Entscheidung F, 05.11.):** Serien-Zeiger (`art="serie"`) der Serie laden.
    Gibt es keinen: Folge 1, Track 0, Position 0. Sonst die Folge `datei` des
    Zeigers, Track `track`, Position `max(0, position_s − RUECKSPRUNG_S)` mit
    `RUECKSPRUNG_S` = 3,0 (im Track). Steht die Position auf 0 (nach einem
    Folgenende), gibt es keinen Rücksprung.
*   **Auflegen, Ziel `folge` (Entscheidung F, 05.11.):** Folgen-Zeiger (`art="folge"`) für (`serie_id`,
    `folge`) laden. Gibt es keinen: Track 0, Position 0. Sonst wie beim
    Serien-Zeiger. Gibt es die Folge in der Serie auf der Box nicht, gilt wie bei
    „Serie fehlt“ (unten): Überraschungs-Serie, ohne `Melden`, und
    `Protokoll(WARNING, ereignis="folge_fehlt", daten={"uid": …, "serie": …, "folge": …})`.
*   **Fehlende Folge** (Serien-Zeiger; `datei` nicht mehr in `Serie.folgen`): die
    Folge, die jetzt am Platz `Zeiger.index` steht; ist `index` ≥ Länge der Liste,
    Folge 1. Track 0, Position 0. `Protokoll(WARNING, ereignis="zeiger_folge_fehlt")`.
    Ist die Serie leer: `TonSpielen("fehler")`, `Protokoll`, Zustand wie bei einem
    Fehlschlag (keine Wiedergabe).
*   **Fehlender Track (Entscheidung F, 05.11.):** Ist `Zeiger.track` ≥ Anzahl der Tracks der Folge
    (`Serie.tracks`), gilt Track 0, Position 0 und
    `Protokoll(WARNING, ereignis="zeiger_track_fehlt")`.
*   **Ein kleiner Rest gilt als fertig gehört (Entscheidung I, 09.11.):** Die Regel gilt überall dort, wo die
    Sitzung ein Ziel am gespeicherten Zeiger startet, also beim Auflegen (auch beim Einschalten mit
    liegendem Tobie und nach dem Warten im Lernmodus), beim Hauptknopf kurz in `pausiert` (auch nach einem
    Dienst-Neustart, Entscheidung G). In `beendet` steht der Zeiger nach `FolgeZuEnde` auf Position 0, dort
    greift sie nie. Sie ändert das Speichern des Zeigers nicht.
    *   **Messung:** am gespeicherten Zeiger, **vor** dem Rücksprung. Rest = Dauer der ganzen Folge (Summe
        aller Tracks, `Serie.dauern`) − (Dauer der Tracks vor `Zeiger.track` + `Zeiger.position_s`). Gilt
        bei `Rest < REST_FERTIG_S` (15 s); genau 15 s gelten noch nicht.
    *   **Folgen-Zeiger (Ziel `folge`):** Die Folge beginnt von vorn, Track 0, Position 0.
    *   **Serien-Zeiger (Ziel `serie`, auch die Überraschungs-Serie):** Es spielt sofort die nächste Folge von
        vorn, Track 0, Position 0, nach der letzten Folge Folge 1. Es gilt dieselbe Zeigerlogik wie bei
        `FolgeZuEnde` (`naechste_folge`); bei einer Serie mit einer Folge ist es dieselbe Folge. Die neue Folge
        wird nicht noch einmal gemessen.
    *   **Ausnahmen:** Folgen mit einer Gesamtdauer unter `REST_REGEL_MIN_FOLGE_S` (60 s) und Folgen, bei denen
        die Dauer eines Tracks unbekannt ist, werden wie bisher fortgesetzt (mit Rücksprung). Ohne
        Zeiger, bei fehlender Folge und bei fehlendem Track gibt es keine Messung.
    *   **Protokoll:** Greift die Regel: `Protokoll(INFO, ereignis="rest_regel", ergebnis="naechste_folge"` bei einer
        Serie, `"von_vorn"` bei einer Folge, `daten={"uid", "art", "serie", "folge", "rest_s", "naechste"})`; `folge` ist
        die fast fertig gehörte Folge, `rest_s` der Rest auf 1 Nachkommastelle, `naechste` die Folge, die spielt.
        Ist die Dauer unbekannt und gibt es einen Zeiger: `Protokoll(INFO, ereignis="rest_regel",
        ergebnis="dauer_unbekannt", daten={"uid", "art", "serie", "folge"})`. Bei Folgen unter 60 s keine Zeile.
    *   **Position hinter dem Track (Review B9):** Liegt `Zeiger.position_s` mehr als `REST_TOLERANZ_S` = 2 s hinter
        der Dauer ihres Tracks (oder gibt es den Track in `Serie.dauern` nicht), stimmt die Dauer nicht (zum Beispiel
        falsch geschätzt). Die Regel wird dann nicht angewendet, wie bei unbekannter Dauer; die Zeile hat
        `ergebnis="dauer_unbekannt"` und zusätzlich `grund="position_hinter_dauer"`. `audiodauer` meldet MP3 mit
        wechselnder Bitrate in den ersten Frames und ohne Xing-/VBRI-Kopf als unbekannt (`None`). *Bekannte Grenze:*
        Eine solche Datei, die in den ersten 256 KiB gleichbleibend kodiert ist und erst später wechselt, bleibt
        unerkannt; die Position-hinter-Dauer-Prüfung fängt sie nur, wenn der Zeiger weit genug hinter der
        geschätzten Dauer liegt.
*   **Lesezeichen mit Ablauf (Entscheidung N, 09.11.):** Jeder Zeiger behält seine eigene Stelle, auch wenn
    zwischendurch andere Tobies gespielt haben. Wurde ein Zeiger länger als `Konfig.lesezeichen_tage` nicht benutzt,
    beginnt beim Fortsetzen die **Folge** wieder von vorn: Track 0, Position 0, ohne Rücksprung. Die Regel greift an
    derselben Stelle wie die Restregel (`session._start`), also bei allen Wegen des Fortsetzens: Auflegen (auch beim
    Einschalten mit liegendem Tobie und nach dem Warten im Lernmodus), Hauptknopf kurz in `pausiert`, nach einem
    Dienst-Neustart (Entscheidung G), Zuordnung per neuer Konfiguration bei liegendem Tobie.
    *   **Reihenfolge:** Zuerst der Ablauf, dann die Restregel. Ist der Zeiger abgelaufen, beginnt die Folge von vorn,
        und die Restregel wird nicht mehr geprüft.
    *   **Serien-Zeiger:** Die Folge bleibt dieselbe (`Zeiger.datei`); es geht nicht zurück auf Folge 1 und nicht auf die
        nächste Folge. **Folgen-Zeiger:** dieselbe Folge von vorn.
    *   **Alter:** `alter = jetzt.wall − Zeiger.benutzt_wall`. Abgelaufen heißt `alter > lesezeichen_tage · 86400 s`; genau
        `lesezeichen_tage` Tage sind noch nicht abgelaufen. `lesezeichen_tage = 0` heißt: läuft nie ab. Fehlt eine
        Konfiguration, gilt `LESEZEICHEN_TAGE` = 14. Ein Zeitstempel in der Zukunft (Uhr zurückgestellt) ergibt kein Ablaufen.
    *   **Nur bei sicherer Uhr:** Ist `jetzt.zeit_ok` falsch, läuft nichts ab. Ein Zeiger ohne Zeitstempel (`benutzt_wall`
        ist `None`; alte Datei) läuft nie ab. Ohne Zeiger, bei fehlender Folge und bei fehlendem Track gibt es keine Prüfung.
    *   **Zeitstempel:** `Benutzung` heißt: zuletzt gespeichert beim Spielen (`periodisch`), Pausieren, Abheben, Track- und
        Folgenwechsel. `ZeigerSpeichern.wall` ist `jetzt.wall`, wenn `jetzt.zeit_ok`, sonst `None` (der Zeitstempel ändert
        sich dann nicht). Beim Start eines Ziels wird nichts gespeichert; ein abgelaufener Zeiger bekommt seine neue Stelle und
        seinen neuen Zeitstempel beim nächsten Speichern.
    *   **Protokoll:** Greift die Regel und stand der Zeiger nicht schon vorn: `Protokoll(INFO, ereignis="lesezeichen_abgelaufen",
        ergebnis="von_vorn", daten={"uid", "art", "serie", "folge", "alter_tage", "tage"})`; `alter_tage` ist das Alter auf
        1 Nachkommastelle, `tage` die Einstellung `lesezeichen_tage`.
*   **Track-Wechsel (`TrackWechsel`) (Entscheidung F, 05.11.):** Der Zeiger wird auf den neuen Track,
    Position 0 gesetzt; `ZeigerSpeichern(grund="trackwechsel")`. **Keine Pause**,
    der Zustand bleibt. Die Pause nach jeder Folge (Entscheidung A)
    gilt nur am Ende der ganzen Folge. **Entscheidung F, 05.11.: `TrackWechsel`
    gilt in jedem Zustand mit laufendem MPD**, also in `spielt` (auch während des
    Ausblendens wegen „stumm“ und während der MPD-Frist) und in `unbekannt`: Der
    Zeiger wird je Ziel immer nachgeführt (Serien-Zeiger bzw. Folgen-Zeiger) und
    gespeichert; der Zustand ändert sich nicht. Ein `TrackWechsel` mit anderer
    Serie oder Folge als der aktuellen, mit einem Track außerhalb der Folge oder
    mit einem Track, der nicht größer als der aktuelle ist (veraltet), wird
    ignoriert (`Protokoll`). In den übrigen Zuständen (`leer`, `pausiert`,
    `beendet`, `gehalten`) wird er ignoriert.
*   **Folge zu Ende (`FolgeZuEnde`) (Entscheidung F, 05.11.):** Ziel `serie`: Serien-Zeiger auf die nächste
    Folge, Track 0, Position 0, nach der letzten Folge auf Folge 1. Ziel `folge`:
    Folgen-Zeiger dieser Folge auf Track 0, Position 0 (das nächste Auflegen
    spielt sie von vorn). Dann `ZeigerSpeichern(grund="folgenende")`,
    `Pausieren("folgenende")`, Zustand `beendet`. Die Sitzung merkt sich die eben
    beendete Folge (Serie und Name) für `Zurueck` (Abschnitt 9, Punkt 12).
    **Entscheidung F, 05.11.: `FolgeZuEnde` gilt in jedem Zustand mit laufendem
    MPD.** In `unbekannt` (und in der MPD-Frist) geschieht dasselbe wie in
    `spielt`: Zeiger je Ziel setzen und speichern, Pause, Zustand `beendet`
    (Fristen werden verworfen). **Während des Ausblendens wegen „stumm“** wird das
    Ausblenden beendet (Grenze `ausblenden` gelöscht, Regel 6.2.7), der Zeiger je
    Ziel gesetzt und gespeichert, `Pausieren("folgenende")`, und der Zustand ist
    `gehalten` (nicht `beendet`; `StummEndet` macht daraus wie üblich `pausiert`).
    In den übrigen Zuständen wird `FolgeZuEnde` ignoriert.
*   **Überraschungs-Serie** (für unbekannte und gesperrte Tobies; sie verhält sich
    wie ein Ziel `serie` (Entscheidung F, 05.11.)): die einzige
    Serie mit `typ="ueberraschung"`. Gibt es keine, mehr als eine oder ist sie
    leer: `TonSpielen("fehler")` und `Protokoll`.
*   **Zuordnung auf eine Serie oder Folge, die die Box noch nicht kennt** (die `serie_id`
    steht nicht in der Bibliothek, oder bei `typ="folge"` fehlt die Folge in der
    Serie; Entscheidung Tobias 05.11., für Folgen Entscheidung F, 05.11.): Die Box spielt die
    **Überraschungs-Serie** (wie bei einem unbekannten Tobie, aber **ohne**
    `Melden`: der Tobie ist ja zugeordnet) und protokolliert den Grund
    (`Protokoll(WARNING, ereignis="serie_fehlt", daten={"uid": …, "serie": …})`).
    Kommt die Serie später (`BibliothekGeladen`), gilt die Zuordnung beim **nächsten
    Auflegen**; die laufende Überraschungs-Serie wird dadurch nicht gewechselt.
    Gibt es auch keine Überraschungs-Serie, gilt deren Fehlerfall (Fehlerton).
*   Der Zeiger wird nur geschrieben, wenn er sich geändert hat (Art, Folge, Index,
    Track oder Position). `ZeigerSpeichern` trägt den Wert aus `PlayerPosition`.
*   **`PlayerPosition` (Entscheidung F, 05.11.):** Die Sitzung übernimmt die
    Position nur in `spielt` und `unbekannt` (Zustände mit laufendem MPD) und nur,
    wenn `serie_id`, `datei` **und** `track` mit dem aktuellen Zeiger übereinstimmen.
    In allen anderen Zuständen (auch `pausiert`, `beendet`, `gehalten`) und bei
    anderer Serie, Folge oder anderem Track wird sie ignoriert. So überschreibt
    eine veraltete Position nach `FolgeZuEnde`, `TrackWechsel`, Vor oder Zurück nie
    den Zeiger. Die Position der Pause ist die zuletzt übernommene (höchstens
    `POSITION_INTERVAL_S` alt).
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

**Rang 5 vor Rang 6 bleibt (Entscheidung L, 09.11.).** `Abspielen` steht vor `TonSpielen` in der
Ausgabe, und das ändert sich nicht. „Zuerst der Ton“ ist deshalb keine Regel der Ausgabe, sondern der
Ausführung: Beim Ausführen übergibt `app.py` Töne nur an die Tonspur (das blockiert nie); ein `Abspielen`
wartet dort auf das Ende der Spur (Abschnitt 6.5, Punkt 6). So bleiben Rang, Konfliktregeln und die Tests
des Kerns unverändert.

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
6.  **Töne und Wiedergabe: nie gleichzeitig (Entscheidung L, 09.11.).** Die Regel gilt in `app.py`, nicht im Kern.
    a.  **Ton vor Hörspiel.** Enthält die Ausgabe eines Kern-Aufrufs `TonSpielen` (oder `StatusPruefen`) und
        `Abspielen`, spielen zuerst die Töne bis zum Ende, in der Reihenfolge der Ausgabe, einzeln. Erst danach
        startet die Wiedergabe. Das gilt für alle Fälle: unbekannter Tobie (`unbekannt`), Ende des Lernmodus
        (`lernen_ende`), Status-Karte, Startton beim Einschalten mit liegendem Tobie, jeder andere Fall. Läuft
        oder wartet noch ein Ton aus einem früheren Aufruf, wartet das `Abspielen` auch auf ihn. Die Dauer eines
        Tons ist das Ende des Abspielprogramms (`afplay`, `aplay`), keine Schätzung. Ein Ton ist auf 10 s
        begrenzt (`TON_MAX_S`); dann wird das Programm beendet und die Wiedergabe startet trotzdem. Ein
        hängender Ton hält die Wiedergabe also höchstens 10 s auf (bei einer Folge mehrerer Töne je Ton).
    b.  **Der Ausführer wartet nie auf einen Ton.** Der Ausführer in 6.5 Punkt 3 übergibt Töne an die Tonspur und
        macht weiter. Ein `Abspielen`, das auf Töne wartet, ist eine eigene, wartende Aufgabe. So bleiben
        `Pausieren`, `LautstaerkeSetzen` und `ZeigerSpeichern` in dieser Zeit wirksam.
    c.  **Befehle während eines Tons.** Ein späteres `Pausieren` (Abheben, Hauptknopf, „stumm“, Gute Nacht, …)
        oder ein späteres `Abspielen` verwirft einen noch wartenden Start: Er wird nie ausgeführt. Zusätzlich prüft
        ein wartender Start vor dem Beginn, ob der Kern noch zu ihm passt: `gen` des Befehls ist gleich dem
        aktuellen `gen` der Sitzung, und die Sitzung ist in `spielt` oder `unbekannt`. Die Prüfung ist nötig, weil
        `gen` nur von `Abspielen` erhöht wird (Abschnitt 3.2: schützt Ereignisse des Players vor einer früheren
        Wiedergabe), das Abheben aber nicht. Ist der Start einmal in Gang, bleibt er; ein folgendes `Pausieren`
        reiht sich beim Player dahinter ein (Sperre des Players). Ein `Pausieren` überholt also nie einen
        verzögerten Start, und ein verzögerter Start überholt nie ein `Pausieren`.
    d.  **Abheben während eines Tons: der Ton läuft zu Ende.** Er wird nicht abgebrochen. Gründe: Töne sind kurze
        Rückmeldungen (Sekunden), ein abgebrochenes Wort klingt wie ein Fehler; der Kern kennt keine Töne und
        kann sie nicht widerrufen; der Hinweis (zum Beispiel „Diesen Tobie kenne ich noch nicht“) gilt auch dann,
        wenn der Tobie schon weg ist; und „nie gleichzeitig“ gilt so oder so. Nur die Wiedergabe startet nicht.
    e.  **Ton während das Hörspiel läuft.** Beginnt eine Tonfolge, während MPD spielt (zum Beispiel `hinweis`,
        `fehler`, `akku_leer`), hält der Player MPD an (`pause 1`), die Tonfolge spielt, und danach setzt der
        Player mit `pause 0` an genau derselben Stelle fort, ohne den 3-s-Rücksprung aus 6.3. Eine Tonfolge hält
        MPD nur einmal an, auch bei mehreren Tönen. Diese kurze Pause bleibt dem Kern verborgen: Der Player meldet
        dafür weder `PlayerPosition(spielt=False)` noch ein Ereignis; es entsteht kein `Pausieren` und kein
        `ZeigerSpeichern` (Grund `pause`); der Status zeigt `spielt`, nicht `pausiert`. Kommt in dieser Zeit ein
        echtes `Pausieren` oder `Abspielen`, endet die kurze Pause, und nach dem Ton wird nichts fortgesetzt.
        Wartet nach den Tönen schon ein neuer Start, wird das alte Hörspiel nicht noch einmal fortgesetzt. Beim
        Beenden des Dienstes setzt nichts fort.
        *Wie der Player das sicherstellt (Review B1, B4, B5, B8):*
        *   **Ton-Epoche.** `pausieren` und `abspielen` erhöhen beim Eintritt (vor der Sperre des Players) einen
            Zähler. `ton_pause_beginn` merkt ihn sich, bevor es auf die Sperre wartet, und beginnt die kurze Pause
            nur, wenn er gleich geblieben ist. So kann ein echtes `Pausieren`, das zwischen dem Aufruf und der
            Sperre kommt, die kurze Pause nicht mehr nachträglich setzen. Das Flag der kurzen Pause löschen außerdem
            `_pausieren` und `abspielen` **unter** der Sperre.
        *   **`Pausieren` prüft unter der Sperre.** Ob schon eine Folge gesetzt ist, wird erst nach dem Erhalt der
            Sperre geprüft: Ein Start, der die Sperre noch hat, setzt die Folge, und das `Pausieren` dahinter wirkt
            dann (es überholt den Start nicht und geht auch nicht verloren).
        *   **Ende der kurzen Pause.** Auch ein Verbindungsverlust (`_trenne`, `_verbindung_weg`) und die Klemmung
            (`_klemme` hält MPD an) beenden sie. `ton_pause_ende` setzt nur fort, wenn der Player die Phase
            `spielt` kennt.
        *   **Ton mitten in einem Start (Review B8).** Läuft ein Start (Phase `aus`, `abspielen` hält die Sperre),
            wartet `ton_pause_beginn` auf die Sperre und hält das Hörspiel danach an. Der Ton beginnt erst, wenn
            der Haken zurückgekehrt ist, und überlagert den Start so nicht. Begründung: Der Haken `vor` ruft der
            Tonspur-Arbeiter vor dem Ton auf; ihn auf den Start warten zu lassen ist der kleinste sichere Eingriff,
            weil keine zweite Zustandsmaschine zwischen `app.py` und Player nötig wird (ein Zurückhalten des Starts
            ginge nicht, denn der Start läuft schon).
        *   **Kein Aufblitzen (Review B8).** `ton_pause_ende` bekommt zwei Funktionen, die der Player erst **unter der
            Sperre**, kurz vor dem Fortsetzen, aufruft: `fortsetzen` (ein neuer Start wartet: nicht fortsetzen)
            und `halten` (gleich folgt ein weiterer Ton der Spur: die kurze Pause bleibt bestehen, nichts wird
            fortgesetzt, und `ton_pause_beginn` hält dann nicht noch einmal an). Weder zwischen zwei Tonfolgen noch bei
            einem `Abspielen`, das genau am Ende der Tonfolge ankommt, setzt das alte Hörspiel noch kurz fort.
            *Bekannte Grenze:* Kommt das `Abspielen` erst, nachdem `pause 0` gesendet wurde, spielt das alte Hörspiel
            bis zum Ersetzen durch den neuen Start einen Moment (wenige Millisekunden); das ist kein Fehler.
    f.  **Zeitbudget.** Ein bekannter Tobie ohne Ton (Normalfall) hat keine Tonspur im Weg: `Abspielen` läuft sofort
        im Ausführer, ohne eigene Aufgabe und ohne Warten. Die Zeit bis zum Hörspiel (Ziel unter 1,0 s,
        `docs/timing.md`) ändert sich dort nicht. Wo ein Ton kommt (unbekannter Tobie, Lernmodus, Status-Karte),
        verlängert sich der Weg bis zum Hörspiel um die Dauer des Tons; das ist gewollt und gehört nicht zum Ziel.
    g.  **Früher Start-Ton: die Marke und die Wartereihenfolge (Ein/Aus, 10.11.; mit V1 und V5 nachgetragen).** Beim Einschalten spielt der
        Frühdienst `tobibox-fruehton.service` den Ton `start`, sobald der Ton-Ausgang da ist, meist vor dem Box-Dienst
        (er hält den Box-Dienst nie auf). Die Marke `/run/tobibox/fruehton` (`data-model.md`, 1.6) ist **eine** Datei mit einem Wort, und **wer sie zuerst
        anlegt, entscheidet** (atomar, nur wenn es sie noch nicht gibt: `link` einer fertig geschriebenen Datei):
        *   Der Frühdienst legt `start` (der Ton läuft) oder `keiner` (bewusst still: nur der Modus „stumm“, R10) an, spielt, und ersetzt `start` danach
            durch `fertig` (oder `fehler`, wenn der Ton nicht lief), nur wenn die Marke noch da ist. Kann er nicht spielen (Datei, Ausgang oder
            Konfiguration fehlt, Fehler), legt er **keine** Marke an.
        *   `app` liest die Marke **erst bei `Bereit`** (nicht beim Dienststart). Gibt es noch keine, legt `app` die Gegenmarke `uebernommen` an; der Frühdienst
            kann dann seine Marke nicht mehr anlegen und spielt **nicht**. So spielen Frühdienst und Kern nie beide `start` (Entscheidung L).
        *   Bei einem Dienst-Neustart ohne Ausschalten (gleiche Boot-Kennung wie in `lauf.json`, Entscheidung G; ohne lesbare Boot-Kennung gilt Einschalten) ignoriert
            `app` die Marke und ersetzt sie durch `uebernommen`.
        War eine Marke des Frühdienstes (`start`, `keiner`, `fertig`) da, sendet `app` `Bereit(fruehton=True)`; die Sitzung spielt dann keinen eigenen `start`
        (und unter „stumm“ auch keinen `hinweis` an seiner Stelle). Marke `fehler`, `uebernommen`, leer, unbekannt oder keine: `fruehton=False`, der Kern spielt `start`
        wie bisher (unter „stumm“ gar nichts, Regel 6.2.2). Steht die Marke auf `start`, **wartet `app` mit jedem
        Ton des Kerns bis zum Eintrag `fertig`, höchstens `FRUEHTON_WARTEN_S` = 3 s ab `Bereit`** (Prüfung alle 0,1 s); ein
        `Abspielen` wartet wie bisher auf die Tonspur (Punkt 6a). So klingen Frühton und `hinweis` nie zugleich
        (Entscheidung L). `app` löscht die Marke des Frühdienstes, sobald `fertig` oder `keiner` dasteht oder die Frist um ist (die Gegenmarke
        `uebernommen` bleibt); ein später schreibender Frühdienst legt die Marke nicht neu an (er ersetzt sie nur, wenn sie noch da ist).

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
*   **Ausnahme vom reinen Ausgang (Entscheidung H, 07.11.):** Eine `Bestaetigt` mit
    `art="gelernt"` geht nach `outbox` **auch an den Kern, wenn `outbox` sie angenommen hat**
    (`outbox.bestaetigt` liefert `True`; eine veraltete oder doppelte Bestätigung wird
    verworfen und erreicht den Kern nicht). Sie ändert dort nur die
    Sitzung, die im Lernmodus auf HA wartet (Abschnitt 9, Punkt 8); `outbox` und
    `unknown.json` bleiben davon unberührt.
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
*   **Nie gleichzeitig (Entscheidung L, 09.11.):** Töne laufen über **eine** Spur, einer nach dem anderen, und
    nie neben dem Hörspiel. Wie die Spur mit `Abspielen`, `Pausieren` und der laufenden Wiedergabe
    zusammenspielt, steht in Abschnitt 6.5, Punkt 6. Für `sounds` heißt das: `TonSpielen` reiht den Ton ein und
    kehrt sofort zurück; die Dauer ist das Ende des Abspielprogramms; ein Ton dauert höchstens `TON_MAX_S` = 10 s;
    zu Beginn und am Ende einer zusammenhängenden Tonfolge ruft `sounds` zwei Haken auf, mit denen `app.py` ein
    laufendes Hörspiel kurz anhält und fortsetzt.
*   **Eine Tonfolge ist ein Prozess (09.11., Befund Mac „Abstand sehr lang“):** Die Töne eines
    `spiele_folge`-Aufrufs (Status-Karte: vier Ansagen) skaliert `sounds` einzeln (jeder mit seinem Pegel) und
    fügt sie mit `FOLGE_PAUSE_S` = 0,15 s Stille zu **einer** WAV-Datei zusammen, die **ein** `afplay`/`aplay`
    spielt. So liegt kein Prozessstart zwischen den Ansagen. Das Zeitlimit gilt weiter je Ton: Die Folge darf
    höchstens `TON_MAX_S` mal Anzahl der Töne dauern, dann wird das Programm beendet. Töne mit anderem Format
    (Rate, Kanäle) kommen in eine eigene Datei. Die Rand-Stille jeder Tondatei ist höchstens 0,1 s (Test).
*   **Gleicher Ausgang wie MPD:** Alle Töne gehen über denselben Audioausgang wie
    die Wiedergabe. Auf dem Pi spielt `sounds` über das ALSA-`softvol`-Gerät, das
    auch MPD benutzt; die **harte Kappe** (`lautstaerke_max`) gilt damit auch für
    Töne. Auf dem Mac gibt es **keine** harte Kappe, es gilt nur die Regel unten.
    **Wie der Pegel wirkt (korrigiert 05.11., Entscheidung F, 05.11.; geändert 09.11., Entscheidung J):**
    `sounds` skaliert die Töne **in Python** (nicht über eine Option des Abspielprogramms) und spielt
    die skalierte Datei mit `afplay {datei}` (Mac) bzw. `aplay -q {datei}` (Pi). Es gibt kein
    `afplay -v`. Die Skalierung benutzt **dieselbe Kennlinie wie MPD** (unten), damit ein Ton bei
    gleicher Lautstärke so laut klingt wie das Hörspiel.
*   **Pegel in Prozent** (Entscheidung J, 09.11.; geändert nach dem Code-Review, B2, B6, B7). Der Pegel steht auf der Skala der
    MPD-Lautstärke (0 bis 100). `app.py` führt nach jedem Schritt des Kerns zwei Werte nach, die `sounds` verwendet
    (`TonSpielen` bekommt kein Feld, der Kern bleibt rein und kennt keine Tonpegel):
    *   `grenze`: die **dauerhafte wirksame Grenze** aus Abschnitt 8, also das Minimum aller Grenzen **ohne** die
        Rampen `ausblenden` und `gute_nacht`. **Ausnahme (Review zu AP 4.8, B13, 09.11.):** Läuft die Absenkung wegen eines „leiser“-Fensters
        (`quiet.absenken`, Rampe über `ausblenden`, `LEISER_ABSENKEN_S`), zählt schon ihr **Ziel** als `leise_zeit`; ein Ton in diesen 3 s
        klingt nie über der Grenze, die gleich gilt (`nachfuehrung.ton_pegel`) (Review B2: Ohne diese Ausnahme blieben Töne nach dem Ausblenden
        hängen bei 1 % und wären nicht zu hören; „stumm“ senkt damit nicht die Töne, sondern hält nur das Hörspiel an);
    *   `lautstaerke = max(0, min(wunsch, grenze))`: die **Lautstärke der Sitzung** nach den dauerhaften Grenzen, mit
        dem Wunsch des Kerns (`KernZustand.wunsch`). Vor dem ersten `LautstaerkeSetzen` gilt
        `min(lautstaerke_start, lautstaerke_max)`. Sie ändert sich mit dem Drehregler und mit jeder dauerhaften Grenze
        (Kopfhörer, „leiser“, Maximum); ein Ton folgt ihr.
    *   **Zeitpunkt (Review B6):** Der Pegel und die Skalierung entstehen **erst, wenn der Ton an der Reihe ist**
        (`Toene` ruft dafür `pegel_quelle` von `app.py` auf), nicht beim Einreihen. Ein Ton, der hinter einem anderen
        oder in einer Status-Karte wartet, hört auf einen Kopfhörer oder auf den Regler, den es seit dem Einreihen gibt.
    *   **Die Grenze gewinnt immer (Review B7, Gehörschutz).** Für **alle** Töne, auch `hinweis`, ist
        `min(grenze, …)` der letzte Schritt.
    *   Alle Töne außer `hinweis`: `pegel = min(grenze, max(TON_MINDEST, lautstaerke))`
        mit `TON_MINDEST` = 10. Der Ton spielt also so laut wie das Hörspiel; die Untergrenze 10
        hält ihn hörbar (z. B. bei Lautstärke 0), **gilt aber nur, solange sie unter der Grenze liegt**.
        Bei einer Kopfhörer-Grenze 5 spielt jeder Ton mit 5.
    *   `hinweis` (der leise Hinweiston unter „stumm“, 6.2 Regel 2):
        `pegel = min(grenze, max(HINWEIS_MINDEST, min(hinweis_pegel, lautstaerke)))` mit `hinweis_pegel` =
        Vorgabe 15 (`HINWEIS_PEGEL_VORGABE`) und `HINWEIS_MINDEST` = 10. Er ist leiser als die
        Lautstärke und übersteigt sie nur durch die Untergrenze (unter „stumm“ ist die Lautstärke
        meist 0), nie aber die Grenze. Die Untergrenze war vor Entscheidung J 5; auf der Kennlinie von MPD sind 5 % rund
        −48 dB und nicht mehr zu hören, 10 % sind rund −41 dB.
    *   `ton_pegel` (`config.json`) hat **keine Wirkung mehr**: `app.py` liest es nicht. Das Feld bleibt
        im Schema gültig (alte Dateien laden unverändert); `data-model.md` ist am 09.11. nachgezogen.
        `hinweis_pegel` gilt weiter. Fehlt das Feld, gilt die Vorgabe 15.
    *   **Neue Töne (Ein/Aus, 10.11.).**
        *   `lader` hat den Pegel von `hinweis` (die Formel oben, mit `hinweis_pegel`; auch hier gewinnt die Grenze). Er
            spielt nur in normalen Zeiten (Regel 6.2.2a), seine Grenze ist deshalb meist die globale.
        *   Der **frühe Start-Ton** des Frühdienstes (Punkt 6.5g) hat **nicht** den Pegel von `hinweis`, sondern den eines
            gewöhnlichen Tons, so wie der `start` des Kerns beim Dienststart klingt (**Abweichung von Rev. 2 des Entwurfs,
            Entscheidung R10**: „leise wie heute“): `pegel = min(grenze, max(TON_MINDEST, min(lautstaerke_start,
            lautstaerke_max)))`. `grenze` ist das Minimum aus `lautstaerke_max`, der Grenze des „leiser“-Fensters (Ergebnis
            von `quiet.wirkung_jetzt` mit der Uhr-Regel der Box; bei unsicherer Uhr die kleinste „leiser“-Grenze, wie im Kern)
            und, solange der Kopfhörer-Kontakt nicht sicher „leer“ meldet, `lautstaerke_kopfhoerer` (Entscheidung P). Liefert
            `quiet.wirkung_jetzt` „stumm“, spielt der Frühdienst **keinen** Ton (Marke `keiner`; der Kern spielt unter „stumm“ ebenfalls keinen `start`
            und keinen `hinweis`, Regel 6.2.2; R10 verlangt: gar nicht). Der Frühdienst liest `config.json` (über `store.KonfigStore`, dieselbe Prüfung wie der
            Dienst) und `tobibox.toml` selbst und kennt keine Sitzung. **Quellen des Frühdienstes (V7):**
            *   **Uhr:** Die Regel steht in `uhrregel.py` und gilt für Dienst und Frühdienst gleich. Sicher ist die Uhr nur nach den Regeln von `[uhr]`: Mac und
                alle Quellen `sim`, oder eine Systemuhr ohne NTP-Pflicht (`system`); sonst nur mit einer plausiblen RTC, die der Frühdienst beim `pisugar-server`
                kurz abfragt (`rtc`). Läuft der `pisugar-server` noch nicht oder liefert er nichts, ist die Uhr **unsicher**: kleinste „leiser“-Grenze, nie „stumm“.
            *   **Kopfhörer-Kontakt:** wie `headphones.py` (`gpiozero`, sonst `gpioget`), zwei übereinstimmende Messungen; Stecker steckt oder Kontakt nicht lesbar
                heißt Kopfhörer-Grenze (Entscheidung P). Am Mac (`quelle = "sim"`) steckt nie etwas.
            *   **Fehler:** `tobibox.toml` unlesbar, `start.wav` oder das Abspielprogramm fehlt, jede Ausnahme: **keine Marke**, der Kern spielt `start` wie heute.
*   **Kennlinie** (Entscheidung J, 09.11.): Sie setzt eine Lautstärke `p` in Prozent in eine
    Verstärkung `g` (Faktor 0 bis 1, 100 % = 1) um. Sie hängt von der Plattform ab und steht deshalb
    in der Konfiguration (`tobibox.toml`, Abschnitt `[toene]`, Felder `kennlinie` und
    `softvol_bereich_db`; Code: `config.py`, `sounds.Kennlinie`):

    | Plattform | `kennlinie` | MPD-Mixer | Verstärkung | Quelle |
    |---|---|---|---|---|
    | Mac (Vorgabe) | `mpd_software` | `mixer_type "software"` | `g = (exp(p / 25) − 1) / (exp(4) − 1)`, gerundet auf 1/1024; 100 % ist 1, 0 % ist still | MPD 0.24, `src/mixer/plugins/SoftwareMixerPlugin.cxx`, `PercentVolumeToSoftwareVolume`; `src/pcm/Volume.hxx`, `PCM_VOLUME_BITS` = 10, `pcm_float_to_volume` |
    | Pi | `alsa_softvol` | `mixer_type "hardware"` am ALSA-`softvol`-Regler | Bereich `b` = `max_dB − min_dB` (Vorgabe 51 dB, ALSA-Vorgabe −51 bis 0 dB; Feld `softvol_bereich_db`). Ist `b` > 24 dB: `dB = 60 · log10(m + p/100 · (1 − m))` mit `m = 10^(−b/60)`, also `g = (m + p/100 · (1 − m))³`; sonst linear in dB: `dB = −b · (1 − p/100)`. 0 dB entspricht `max_dB`, der harten Kappe | MPD 0.24, `src/mixer/plugins/VolumeMapping.cxx` (`set_normalized_playback_volume`, `MAX_LINEAR_DB_SCALE` = 24); `AlsaMixerPlugin.cxx` (`SetVolume`); alsa-lib `src/pcm/pcm_softvol.c` (dB-Tabelle linear in dB zwischen `min_dB` und `max_dB`) |

    Beispiele: Am Mac sind 20 % rund −33,0 dB, 40 % rund −22,6 dB (das Hörspiel bei Startlautstärke
    und bei Maximum der Beispielkonfiguration). Der alte feste Tonpegel 40 % linear waren −8 dB; er lag
    damit rund 25 dB über dem Hörspiel bei 20 %. Am Pi sind 20 % rund −30,3 dB, 40 % rund −18,9 dB.
    Die Kennlinie wirkt **zusätzlich** zu ReplayGain und unabhängig davon (MPD wendet ReplayGain als
    eigenen Filter an). Die Werte für den Pi sind aus dem Quelltext abgeleitet und noch nicht am Gerät
    gemessen (Pi-Probelauf).
*   **Zielwert der Lautheit** (Entscheidung J, 09.11.): Die Dateien in `box/sounds/`,
    `box/sounds/sprache/` und `box/medien-sprache/` liegen bei **−18 LUFS** (integriert, EBU R128),
    dem Zielwert, den `rsgain` für die Hörspiele nutzt (Design, D6). Erlaubte Abweichung ±1 LU.
    Ein Ton und ein Hörspiel haben dann bei gleicher Lautstärke und gleicher Kennlinie den gleichen
    Pegel. Die MP3 der Testmedien tragen ReplayGain-Tags (`REPLAYGAIN_TRACK_GAIN`, `…_PEAK`),
    sonst dämpft MPD sie um `replaygain_missing_preamp` (−6 dB).
*   **Pi: ein Regler, nicht zwei.** Spielte `aplay` über denselben `softvol`-Regler wie MPD, würde die
    Lautstärke doppelt wirken (einmal im Regler, einmal in Python). Die Töne laufen am Pi deshalb über
    ein zweites `softvol`-Gerät mit **demselben `max_dB`** und eigenem Regler, der fest auf 100 %
    steht (`aplay -D <Gerät>` im Kommando, `deploy/pi/asound.conf`, Stufe 4). So gilt die harte Kappe
    auch für die Töne, und die Lautstärke wirkt genau einmal.
*   Fehlen die Felder (keine Konfiguration geladen), gilt für `hinweis_pegel` die Vorgabe 15.

## 9. Fälle, die die Tabellen des Designs offenlassen

Alle Punkte sind Festlegungen dieses Vertrags; die als „bestätigt (05.11.)“
gekennzeichneten sind von Tobias oder der Projektleitung entschieden
(Abschnitt „Festlegungen“ am Ende).

1.  **Leser-Unterbrechung: `LeserHallo` und `LeserAlarm`** (bestätigt 05.11.,
    Projektleitung). Beide Ereignisse starten **nie** eine Wiedergabe.
    *   Zustand `spielt`: Wechsel nach `unbekannt`, Frist `LESER_FRIST_S` = 3,0 s.
        Die Frist beginnt mit dem **ersten** der beiden Ereignisse (Alarm oder
        `LeserHallo`) und wird durch ein zweites nicht verlängert. Meldet `reader`
        innerhalb der Frist derselbe Tobie erneut (Punkt 2), läuft die Wiedergabe
        ohne Neustart weiter. Sonst Pause.
    *   Zustände `pausiert`, `beendet`, `gehalten`: **keine Wirkung.** Der Tobie
        gilt weiter als liegend (`figur_liegt` und der gemerkte Tobie ändern sich
        nicht). Nur `Abgehoben` (oder der Abgleich in Punkt 3) ändert das.
    *   Zustand `leer`: keine Wirkung.
    *   **Wiedermeldung:** Ein `Aufgelegt` oder `Gesperrt` mit **derselben
        Vorgangs-ID** wie der gemerkte liegende Tobie ist **in allen Zuständen
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
        Auflegen“):** Nach Ablauf der Frist pausiert die Sitzung, der Tobie gilt
        aber weiter als liegend. Meldet `reader` sie danach erneut (Wiedermeldung,
        gleiche Vorgangs-ID), startet nichts von selbst; erst Abheben und
        erneutes Auflegen oder der Hauptknopf kurz spielen wieder (Punkt 12).
2.  **Im Zustand `unbekannt`:**
    *   `Aufgelegt` oder `Gesperrt` mit **derselben** Vorgangs-ID (derselbe Tobie:
        gleiche Kennung bzw. beide gesperrt) innerhalb der Frist: Zustand
        `spielt`, kein Befehl. Das ist die **einzige** Ausnahme vom No-op der
        Wiedermeldung (Punkt 1). **Bestätigt (05.11.):** Ist dabei der MPD
        verloren (Punkt 10, `PlayerVerbindung(ok=False)` ohne spätere Rückkehr)
        oder ist die `MPD_FRIST_S` während `unbekannt` abgelaufen, geht die
        Sitzung statt nach `spielt` sofort nach `pausiert` (Zeiger ist
        gespeichert; der Tobie liegt weiter). Ein laufender MPD-Fristzähler wird
        beim Eintritt in `unbekannt` verworfen.
    *   `StummBeginnt` in `unbekannt` (bestätigt 05.11.): wirkt erst, **nachdem
        die Sitzung `unbekannt` verlassen hat**; bis dahin spielt nichts. Verlässt
        sie `unbekannt` nach `spielt` (gleicher Tobie zurück), gilt „stumm“ sofort
        (Punkt 5); verlässt sie es nach `pausiert`, gilt Punkt 12.    *   `Aufgelegt` oder `Gesperrt` mit **anderer** Vorgangs-ID (andere Kennung,
        oder gesperrt gegen Kennung): Frist endet sofort, Pause und Zeiger der
        alten Serie speichern, danach der neue Tobie wie ein normales Auflegen
        (Tabelle: „Tobie-Wechsel während einer Leser-Unterbrechung“).
    *   `Abgehoben`: Frist endet, Pause, Zeiger speichern, `pausiert`,
        `figur_liegt` falsch.
    *   Frist abgelaufen (`Takt`): Pause, Zeiger speichern, `pausiert`; der Tobie
        gilt weiter als liegend (Punkt 1, letzte Abweichung).
    *   `LeserHerzschlag` mit `present=False` nach `LeserHallo`: der Tobie ist weg;
        Frist endet sofort, Pause, Zeiger speichern, `pausiert`, `figur_liegt`
        falsch.
3.  **Abgleich über den Herzschlag:** Die Sitzung vergleicht `present` mit
    ihrem Wissen `figur_liegt`. Weichen zwei **aufeinanderfolgende**
    `LeserHerzschlag` voneinander ab (beide `present` anders als `figur_liegt`),
    gibt sie `LeserPing()` aus und zählt neu. Das `HELLO` auf den `PING` und die
    erneute Meldung der Firmware stellen den Zustand her. **Danach:** Ist die
    erste `LeserHerzschlag` nach einem `LeserHallo` `present=False`, während
    `figur_liegt` wahr ist (der Tobie wurde im Ausfall abgehoben, ohne dass ein
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

    **Lernmodus wartet still (Entscheidung H, 07.11.).** Wird im Zustand `lernt` ein
    Tobie mit Kennung aufgelegt (`Aufgelegt`, neue Vorgangs-ID), bekannt oder
    unbekannt, spielt die Box **nichts**: keinen Tobie, keine Überraschungs-Serie,
    keinen Ton `unbekannt`. Es kommt nur der Lernton (`lernen_ende` von `learn`). Die
    Sitzung wartet auf die Antwort von HA. Umsetzung: `session` kennt `lernt` aus
    `LernenGeaendert` und führt ein Feld `lern_wartet_bis` (`mono`, sonst `None`).
    Der Sitzungszustand (`kennzeichen`) ist während des Wartens `pausiert`, der Tobie
    liegt (`figur_liegt`); es gibt keinen neuen Wert für `ZustandMelden.sitzung`.
    Läuft bei `Aufgelegt` noch eine Wiedergabe, gilt zuerst die Regel „anderer Tobie“
    (Zeiger speichern, `Pausieren("abgehoben")`). `Aufgelegt` mit Kennung wartet für
    jede Art von Tobie, auch für eine Aktionskarte (sie löst während des Wartens keine Aktion aus;
    nach der Frist oder der Ablehnung verhält sie sich wie bei einem normalen Auflegen
    und löst ihre Aktion aus, auch von selbst nach der Frist);
    `Gesperrt` hat keine Kennung und wartet nicht (er ändert den Lernmodus nicht).
    Eine **Wiedermeldung derselben Kennung im Zustand `spielt`** (neue Vorgangs-ID nach
    verlorenem `REMOVED`) wartet nicht: Es gilt 9.4, die Wiedergabe läuft weiter, die
    Sitzung ändert nur die Vorgangs-ID. Im **Sitzungszustand `unbekannt`** (Leser
    unterbrochen, 9.2) läuft das Warten so ab: Eine `Aufgelegt` mit neuer Vorgangs-ID
    (andere Kennung oder dieselbe nach verlorenem `REMOVED`) pausiert mit
    `Pausieren("leser_unbekannt")`, speichert den Zeiger (Grund `figurwechsel`) und
    beginnt dann das Warten; der Zustand ist danach `pausiert`, die Leser-Frist ist
    erledigt. Ein Leserausfall während des Wartens ändert das Warten nicht
    (`LeserHallo` merkt sich nur das Hallo für 9.3); meldet der Herzschlag
    danach keinen Tobie mehr, gilt das als Abheben (Ende 4).
    *   **Melden:** unverändert. `session` meldet einen unbekannten Tobie wie bisher
        (`Melden("unbekannt")`), `learn` meldet `Melden("gelernt", uid, befehl_id)`;
        Regel 6.2.4 lässt `gelernt` gewinnen. `unknown.json` und die Veröffentlichung
        laufen unverändert. Nur Wiedergabe und der Ton `unbekannt` warten. Einzige
        Ausnahme: das Ende durch „abgelehnt“ bei einem unbekannten Tobie (Ende 2).
    *   **Merkfeld:** Beim Beginn des Wartens merkt sich die Sitzung das bisherige Ziel
        des Tobies (`lern_ziel`, die `Zuordnung` aus der damaligen Konfiguration; ein
        unbekannter Tobie hat keins). Es wird mit dem Ende des Wartens gelöscht.
    *   **Das Warten endet** mit genau einem dieser Ereignisse (danach läuft es nicht
        mehr; die Vorgangs-ID des Tobies bleibt):
        1.  **Zuordnung:** `KonfigGeladen`, die dem wartenden Tobie ein **anderes** Ziel
            gibt als das gemerkte (`lern_ziel`); bei einem unbekannten Tobie zählt
            jedes Ziel. Die Sitzung startet sofort das Ziel wie beim
            Auflegen (Zeiger laden, `Abspielen`; bei „stumm“ gilt 9.12; ist das Ziel
            Serie oder Folge nicht vorhanden, gilt 6.3 „fehlt“). Jede andere
            `KonfigGeladen` (ohne diese Kennung, mit unverändertem Ziel, auch mit neuer
            Revision) gilt für die Sitzung wie sonst, lässt das Warten aber
            weiterlaufen. Das gilt auch für eine Aktionskarte (sie löst nur bei einer
            anderen Aktion aus).
        2.  **Ablehnung:** `Bestaetigt` mit `art="gelernt"`, `grund="abgelehnt"` und
            `id` = Kennung des wartenden Tobies. Die Sitzung verhält sich wie bei einem
            normalen Auflegen ohne Lernmodus: bekannt → sein Ziel; unbekannt →
            Überraschungs-Serie mit Ton `unbekannt` und **erneutem `Melden("unbekannt")`**:
            `outbox` hat den Eintrag mit der Bestätigung gelöscht, der Tobie steht
            danach wieder in `unknown.json`, und HA sieht ihn als „neuer Tobie“ (Satz
            „jede Überraschung wegen eines unbekannten Tobies hat einen offenen
            Eintrag“). Bei einem bekannten Tobie kein `Melden`. Die Bestätigung zählt
            nur, wenn `outbox` sie angenommen hat (Abschnitt 3). Jeder andere `grund`
            (z. B. `zugeordnet`) beendet das Warten nicht; er ändert nur `outbox`.
        3.  **Frist:** `Takt` mit `jetzt.mono ≥ lern_wartet_bis`, gemessen ab dem
            `Aufgelegt` auf `mono`, `LERN_ANTWORT_FRIST_S` = 10 (Konstante in
            `session.py`). Wirkung wie bei der Ablehnung, aber **ohne** neues `Melden`
            (der Eintrag in `unknown.json` bleibt als `gelernt` offen und wird erneut
            veröffentlicht). Eine Aktionskarte löst jetzt ihre Aktion aus. Kommt die
            Zuordnung danach doch noch, gilt Punkt 14 (neue Konfiguration bei liegendem
            Tobie), weil der Tobie dann als gestartetes Ziel seine Überraschung oder sein
            altes Ziel hat. **Gewollt (Rückfrage beim Überschreiben):** Muss Tobias in HA
            vor dem Überschreiben eine Rückfrage beantworten (`mqtt-v1.md` 4.2) und
            braucht dafür länger als 10 s, spielt ein bekannter Tobie zuerst sein altes
            Ziel. Mit der späteren Zuordnung wechselt die Box auf das neue Ziel, wie bei
            jeder Konfigurationsänderung mit liegendem Tobie. Es gibt dafür keinen
            eigenen Mechanismus (keine Verlängerung der Frist).
        4.  **Abheben:** `Abgehoben` (oder ein Herzschlag, der das Abheben feststellt)
            beendet das Warten ohne Wirkung, es spielt nichts: wie ein normales Abheben
            ohne laufende Wiedergabe (`pausiert`, kein Tobie).
    *   **Eingaben während des Wartens (festgelegt 07.11.):**

        | Eingabe | Wirkung |
        |---|---|
        | Lautstärke drehen (`LautstaerkeDrehen`) | wirkt wie immer (Sache des Kerns, nicht der Sitzung) |
        | `Hauptknopf` kurz | ignoriert (nur `Protokoll`), kein Ton, die Frist läuft weiter |
        | `Weiter`, `Zurueck` | ignoriert (nur `Protokoll`), kein Ton, die Frist läuft weiter |
        | `Hauptknopf` lang | gehört `idle` (Herunterfahren), unberührt |
        | `Kopfhoerer`, `StummBeginnt`, `StummEndet`, `GuteNachtEnde` | wirken wie immer; es läuft keine Wiedergabe, die sie ändern könnten |

        Der Zweck: Ein Druck soll nicht die Überraschung oder das alte Ziel starten,
        solange HA noch antworten kann.
    *   **Ein anderer Tobie während des Wartens:** Der Lernmodus ist nach dem ersten
        Tobie schon `aus` (`learn` hat ihn beendet). Der zweite Tobie wird deshalb ganz
        normal behandelt (Auflegen nach 6.3 und 9.12); das Warten des ersten endet
        damit ohne eigene Wirkung. Startet ein neuer Lernbefehl, bevor der zweite
        Tobie aufgelegt wird, wartet auch dieser (mit eigenem gemerktem Ziel). `Gesperrt`
        im Warten beendet es ebenfalls und spielt die Überraschungs-Serie (9.12 und 6.3,
        ohne Ton `unbekannt`). Dieselbe Kennung mit neuer Vorgangs-ID (verlorenes
        `REMOVED`, 9.4) lässt das Warten weiterlaufen.
    *   **Dienst-Neustart während des Wartens (Entscheidung G, 06.11.):** Der Lernmodus
        überlebt keinen Neustart; der Tobie liegt in `lauf.json` und bleibt nach dem
        Neustart `pausiert`, wie in Punkt 12 beschrieben.
    *   **Regel 6.2.2 („stumm“)** gilt unverändert für `lernen_ende`.
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
    | Bedingungen für `HaUpdateAnstossen` | Kern: `idle` | verlangt Netz-Klasse `home`, Lader an, Zustand der Sitzung nicht `spielt`, kein Sync und kein Update aktiv. Sonst `EreignisSenden("befehl_abgelehnt", {…, "grund":"bedingung", "detail": <welche>})` (heute nur für `update`). Geprüft in dieser Reihenfolge, die erste nicht erfüllte Bedingung steht im `detail` (09.11., AP 4.8): „Die Box ist nicht im Heimnetz.“ (Netz-Klasse nicht `home`), „Die Box hängt nicht am Lader.“, „Es läuft gerade ein Hörspiel.“, „Es läuft gerade ein Sync.“ (auch eine offene Sync-Antwort), „Es läuft schon ein Update.“ |
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
    *   Bedienung setzt den Zähler zurück. Wer an der Box spielt, will nicht,
        dass sie ausgeht. HA-Befehle setzen ihn nicht zurück. (09.11., AP 4.8;
        Bedienung sind Hauptknopf kurz, `Weiter`, `Zurueck`, `LautstaerkeDrehen`
        und `Kopfhoerer`, Teilautomat `idle`.)
    *   **Leerlauf zählt auch mit liegendem Tobie (Entscheidung O, 09.11., Befund B5; Frist seit Ein/Aus, 10.11.: 10 min und nur ohne Strom).** Leerlauf heißt: `LEERLAUF_S` lang (vorher 20 min, seit 10.11. 10 min, und nur ohne Strom, siehe „Strom, Frist und Andocken“ unten) wird nichts
        gespielt (`spielt` und `unbekannt` zählen als belegt, `pausiert`, `beendet`, `gehalten` und `leer` nicht), egal ob ein
        Tobie liegt. Anlass: Nach Gute Nacht oder einem „stumm“-Fenster liegt der Tobie noch, und die Box blieb sonst die ganze Nacht an.
        Es gelten weiter die Ausnahmen Sync, Update und Lernmodus (die Abschaltung wartet), und Bedienung setzt den Zähler zurück.
        Morgens beim Einschalten spielt ein liegender Tobie wie bisher sofort weiter (Entscheidung G). Der Ring zeigt die Pause bei
        liegendem Tobie auch im Leerlauf weiter (`led`).
    *   **Ein fehlgeschlagenes Herunterfahren ist nicht endgültig (B1, 09.11.).** `app` führt `Herunterfahren` erst aus, nachdem ein
        laufender Ton (`akku_leer`) zu Ende ist (höchstens `TON_VOR_HERUNTERFAHREN_S` = 5 s). `power` prüft das Kommando
        (`systemctl poweroff` oder `abschalt_kommando`): Rückgabecode 0 innerhalb `ABSCHALT_FRIST_S` = 60 s. Sonst sendet `power`
        `HerunterfahrenFehlgeschlagen(detail)`. `idle` im Zustand `herunterfahren` verlässt ihn dann (neuer Zustand `aktiv`, danach
        `leerlauf`, **der Zähler beginnt neu**), schreibt `Protokoll(ERROR)` und gibt
        `EreignisSenden("fehler", {baustein: "power", code: "herunterfahren_fehlgeschlagen", text})` aus. `Hauptknopf lang` und ein
        späterer Tiefstand fahren dann wieder herunter. **Ohne `power` und am Mac** (Simulation) ist das Herunterfahren nur
        protokolliert: `power` (ohne `[strom]` `app`) sendet `HerunterfahrenFehlgeschlagen(simuliert=True)`; `idle` bleibt
        `SIMULATION_RUECKKEHR_S` = 10 s in `herunterfahren` und kehrt dann in den normalen Zustand zurück (kein Hinweis an HA), damit die
        Simulation benutzbar bleibt. In `herunterfahren` führt `idle` die Sitzungs-, Lade-, Lern- und Netzzustände nach, damit die Rückkehr auf dem
        richtigen Stand beginnt. Der Zeitgesteuerte Sync (`takt`) startet nach dem Entschluss zum Herunterfahren nicht mehr (B6).
    *   **Tiefstand (B12):** `idle` gibt bei `AkkuTiefstand` (nicht am Lader) einmal `TonSpielen("akku_leer")` aus, dann
        `HerunterfahrenAngefordert("akku_tiefstand")`. Unter „stumm“ wird der Ton zum Hinweis (6.2, Regel 2).
    *   **Strom, Frist und Andocken (Ein/Aus, 10.11.; ersetzt „Start am Lader“ und die Wiederholung des Start-Syncs vom 09.11., AP 4.8).**
        „Strom“ heißt Strom am Eingang der Box aus **irgendeiner** Quelle (Netzteil, Sockel, Kabel, Powerbank, Auto). Die Regeln im Einzelnen:
        1.  **Frist.** `LEERLAUF_S` = 600 s. Der Zähler läuft nur, solange **kein Strom** anliegt. Mit Strom ist die Box immer bereit und
            fährt nie wegen Leerlauf herunter (`Hauptknopf` lang fährt immer herunter; der Tiefstand gilt nur ohne Strom, wie bisher).
            **Strom kommt:** der Zähler wird verworfen. **Strom geht** (Abnehmen, Abziehen): der Zähler beginnt **ab diesem Zeitpunkt**
            neu (R9), egal wie lange vorher nichts gespielt wurde. Spielt die Sitzung, beginnt der Zähler wie sonst erst, wenn sie nicht mehr
            spielt. Sync, Update und Lernmodus halten die Abschaltung weiter auf (wie bisher).
        2.  **Zwei Quellen, Vorrang Leser.** `idle` hält den letzten Wert je `quelle` (`LaderGeaendert`, Abschnitt 3.6). Der zusammengeführte
            Wert ist der des Lesers, solange er einen geliefert hat, sonst der von `pisugar`. Widersprechen sich beide, gilt der Leser;
            `idle` schreibt `Protokoll(WARNING, "strom", "widerspruch")`, einmal je Widerspruch und **erst, wenn er `STROM_WIDERSPRUCH_S` = 5 s anhält**
            (V16; beim normalen Andocken meldet `pisugar-server` schneller als der entprellte Leser, das ist nur DEBUG). Hängt `pisugar-server`,
            liefert der Leser den Wert allein (CUJ 23). **(V2)** Der Vorrang des Lesers gilt nur, solange seine Verbindung steht und der Wert aus der
            aktuellen Verbindung stammt: `LeserAlarm` und jedes `LeserHallo` löschen den Leser-Wert; bis das `LADER` nach dem `HELLO` ihn neu liefert (und
            bei einer Firmware ohne `caps` `strom` dauerhaft), gilt `pisugar`. Das Löschen ist keine Andock- oder Abzieh-Rückmeldung (V3).
        3.  **Unbekannt.** Hat noch keine Quelle einen Wert geliefert, ist der Strom **unbekannt**. Unbekannt löst nichts aus (kein Ton,
            kein Ring, kein Sync) und der Zähler zählt noch nicht. Nach `STROM_UNBEKANNT_S` = 60 s seit dem Start von `idle` gilt unbekannt als
            **kein Strom** (der Zähler beginnt dann). Eine Quelle, die nach einem bekannten Wert schweigt, behält ihren letzten Wert (außer dem Leser, 9.2).
            **(V15)** „Unbekannt“ zählt für den Akku-Tiefstand wie „kein Strom“ (sicher für den Akku), für die Bedingung des Updates und die Netz-Regel
            (Hotspot nur mit Lader) wie „nicht am Lader“.
        4.  **Erste bekannte Messung.** Der erste Wert, den irgendeine Quelle im laufenden Dienst liefert, auch wenn er spät kommt (nach dem
            Start, nach den 60 s), löst **nur den Sync-Check** aus, nie einen Ton und nie eine Andock-Rückmeldung (Punkt 5). **(V4)** Der Zustand (Zähler verworfen bei „Strom“, begonnen bei „kein Strom“) folgt dem Wert sofort, auch bei einer ersten Messung nach den 60 s; nur die Rückmeldung (Ring, Ton) entfällt: Ist sie „Strom“, gibt
            `idle` einmal `SyncStarten("start_lader")` aus, sobald `Bereit` da ist (`sync` entscheidet nach der Netz-Regel; wie bisher, aber
            ohne Wiederholung). Ist die Netz-Klasse beim Start noch unbekannt (die erste Messung von `net` dauert länger als die von `power`),
            wartet `app` mit diesem Sync auf die erste `NetzKlasse`, höchstens `NETZ_KLASSE_WARTEN_S` = 30 s, statt mit `SyncAbgebrochen("regel")`
            abzubrechen (B7, 09.11.). Ein Dienst-Neustart zählt als neuer Start: auch er löst keine Rückmeldung aus. (Der Ladestand für 5 s am Ring, den die Box beim
            Start mit Strom nach `Bereit` zeigt, CUJ 25, ist die Start-Anzeige von `led` und keine Andock-Rückmeldung.)
        5.  **Andocken** = Wechsel des zusammengeführten Werts von „kein Strom“ nach „Strom“ **nach** der ersten bekannten Messung, ausgelöst durch eine Quelle, die vorher
            schon einen Wert hatte. **(V3)** Der erste Wert einer zweiten Quelle und das Löschen des Leser-Werts (9.2) sind keine Rückmeldung (nur der Zustand folgt). Der Zähler wird
            verworfen (Punkt 1). Dazu die **Rückmeldung**, wenn die Sperre (Punkt 7) frei ist:
            *   Ring: Ladestand für 5 s (spielt die Sitzung: 3 s). „Ladestand“ und „Akku“ sind **dieselbe** Anzeige, die Akku-Füllstand-Anzeige des Rings (blau mit Strom, sonst nach Prozent); `idle` gibt sie mit dem Befehl `AkkuAnzeigen` frei (Punkt 9).
            *   Ton `lader` (`TonSpielen("lader")`), **nur** wenn die Sitzung nicht spielt (`spielt`, `unbekannt`: dann nur der Ring, Entscheidung L),
                kein Update läuft und die Regel 6.2.2a ihn nicht streicht (nicht in „leiser“ und „stumm“, nicht bei unsicherer Uhr, nicht im
                Lernmodus).
            *   Sync prüfen: einmal `SyncStarten("start_lader")` (nicht, solange ein Update läuft).
        6.  **Abziehen** = Wechsel von „Strom“ nach „kein Strom“ nach der ersten bekannten Messung: der Zähler beginnt neu (Punkt 1), Ring Akku für
            5 s (spielt die Sitzung: 3 s), **kein Ton**, kein Sync. Auch hier gilt die Sperre für den Ring.
        7.  **Sperre `LADER_SPERRE_S` = 10 s.** Jede Rückmeldung (Ring, Ton, Sync) gibt es nur, wenn seit der letzten Rückmeldung **und seit
            `Bereit`** mindestens 10 s vergangen sind. Ein Wackelkontakt löst so höchstens eine Rückmeldung je 10 s aus. Der Zustand (Zähler
            verworfen oder neu begonnen) ändert sich trotzdem sofort. Kommt der Strom in den ersten 10 s nach `Bereit`, gibt es also keinen
            Ton (der Frühton läuft dann noch oder ist gerade fertig).
        8.  **Die Wiederholung des Start-Syncs entfällt** (`START_WIEDERHOLUNG_S`, `START_WIEDERHOLUNGEN`, die Zustände `start_wdh`, `wdh_n`,
            `wdh_bei`). Bricht ein Sync mit `netz_weg` oder `regel` ab, hält das die Abschaltung nicht auf; den nächsten Anstoß geben der Takt
            (Intervall in `tobibox.toml`), das Andocken oder HA.
        9.  **Ring (V6).** Der Kern befiehlt dem Ring keine Zustände (`led` beobachtet, Abschnitt 6.5), aber `idle` entscheidet, **wann** die Andock- und die
            Abzieh-Anzeige erscheinen darf, weil nur `idle` die erste Messung, den zusammengeführten Wert und die Sperre kennt. `idle` gibt dazu bei einer
            freien Rückmeldung (Punkt 5 und 6) den Befehl `AkkuAnzeigen(grund, dauer_s)` aus (Abschnitt 4); `led` setzt ihn um. Zusätzlich zeigt `led` allein die
            **Start-Anzeige** (CUJ 25): ist die erste bekannte Messung „Strom“, zeigt der Ring nach `Bereit` (nach dem Lauflicht) den Ladestand 5 s lang, ohne
            Sperre und ohne `AkkuAnzeigen`. Helligkeit der Akku-Anzeige: 15 %, in einem Fenster „leiser“ und während „Gute Nacht“ 5 %, in einem Fenster „stumm“
            3 %, mindestens Stufe 1 der 31 Stufen; der Faktor 0,4 von „stumm“ gilt nicht für sie. `led` entprellt: Eine zweite Anforderung innerhalb von 1 s nach
            dem Beginn einer laufenden Anzeige startet sie nicht neu. `led` führt den Strom-Wert aus beiden Quellen mit demselben Code zusammen (`stromwert.py`).
        10. **Hauptknopf lang am Strom.** Er fährt herunter (R8: am Sockel ist die Box danach „immer an“; dass sie dort gleich wieder startet,
            leistet mit Schritt 2 der Leser über `STROM_IN`; bis dahin hängt es an „Einschalten bei Strom“ des PiSugar, Messung M9). Ausschalten
            am Sockel heißt: abnehmen, dann gilt die Frist.
10. **Fehler des Players:**
    *   `PlayerFehler` im Zustand `spielt`: `TonSpielen("fehler")`,
        `Pausieren("fehler")`, `Protokoll(ERROR)`. Bei `datei_fehlt` oder
        `datei_unlesbar` geht der Zeiger auf die nächste Folge (Track 0, Position 0;
        bei einem Folgen-Zeiger bleibt es dieselbe Folge, Track 0, Position 0),
        sonst bleibt er (Entscheidung F, 05.11.). Zustand `pausiert`; der Tobie liegt weiter.
    *   **MPD weg während der Wiedergabe** (bestätigt 05.11., Tobias):
        `PlayerVerbindung(ok=False)` im Zustand `spielt`: `Protokoll(ERROR)`,
        Zeiger mit der letzten Position speichern (`ZeigerSpeichern("pause")`).
        Die Sitzung bleibt im Zustand `spielt` (Kennzeichen unverändert), merkt
        sich aber die Frist `MPD_FRIST_S` = 5,0 s ab diesem Ereignis.
        *   Kommt `PlayerVerbindung(ok=True)` **innerhalb** der Frist und liegt der Tobie weiter (`figur_liegt`), setzt die Wiedergabe am gespeicherten
            Zeiger fort: `AusgangWaehlen` (der MPD-Zustand ist verloren) und
            `Abspielen` mit dem gespeicherten Track und `position_s = max(0, position − RUECKSPRUNG_S)`
            (Regel 6.2.6 setzt die Lautstärke davor). Zustand `spielt`.
        *   Sonst (Frist abgelaufen, `Takt`): `Pausieren("fehler")` (wirkungslos,
            wenn MPD weg ist), Zustand `pausiert`; der Tobie gilt weiter als
            liegend. Das Kind legt den Tobie neu auf (Abheben und Auflegen) oder
            drückt den Hauptknopf (Punkt 12). `TonSpielen("fehler")` gibt es hier
            nicht.
        *   Beginnt „stumm“ während der Frist: kein Ausblenden, sondern sofort
            Zustand `gehalten` (der Zeiger ist gespeichert).
        *   **Leser-Unterbrechung während der Frist (bestätigt 05.11.):** Geht die
            Sitzung nach `unbekannt` (Punkt 1), wird der laufende Fristzähler
            **verworfen**. Kehrt sie von `unbekannt` nach `spielt` zurück (Punkt 2)
            und ist der MPD weiter verloren oder die Frist inzwischen abgelaufen,
            geht sie **sofort nach `pausiert`** (Zeiger gespeichert, Tobie liegt),
            ohne `Abspielen`. Ebenso bleibt `mpd_verloren`, wenn
            `PlayerVerbindung(ok=True)` in `unbekannt` eintrifft: die Rückkehr
            nach `spielt` führt weiter nach `pausiert` (sicheres Verhalten,
            05.11.).
        *   `Weiter`/`Zurueck` während der Frist: ignoriert (nur Protokoll;
            05.11.).
        *   `Abgehoben` während der Frist: normale Pause (Zeiger ist gespeichert),
            `pausiert`. `Hauptknopf` kurz: Pause, `pausiert`. Weitere
            `PlayerFehler` während der Frist: nur `Protokoll`.
    *   **Fehlender oder unlesbarer Track in einer Folge mit mehreren Tracks
        (bestätigt 05.11., Entscheidung F):** Der Player überspringt den Track und
        spielt den nächsten Track **derselben Folge** (`Protokoll(WARNING,
        ereignis="datei_fehlt")` bzw. `datei_unlesbar`, `TrackWechsel` auf den
        nächsten vorhandenen Track). Erst wenn nach dem letzten Track nichts mehr
        spielbar ist, gilt das als Ende der Folge (`FolgeZuEnde`). Ein
        `PlayerFehler` entsteht nur, wenn **kein** Track der Folge spielbar ist
        (und bei einer Folge aus einer Datei); dann gilt die Regel oben.
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
        speichern, `pausiert`; `pausiert` mit liegendem Tobie → Abspielen am
        Zeiger (mit Rücksprung, oder Restregel nach 6.3); `pausiert` ohne Tobie → Abspielen am Zeiger der
        zuletzt gespielten Serie (normale Play/Pause-Funktion); `beendet` mit
        liegendem Tobie → ab Zeiger abspielen (Entscheidung E): Ziel `serie` die
        nächste Folge, Ziel `folge` dieselbe Folge von vorn (der Zeiger steht auf
        Track 0, Position 0) (Entscheidung F, 05.11.); `gehalten`, `leer`, `unbekannt` → keine Wirkung.
    *   **`Weiter` / `Zurueck` springen nach Track (Entscheidung F, 05.11.)** innerhalb der Folge, nur im
        Zustand `spielt` oder `pausiert` mit Ziel `serie` oder `folge` (die
        Überraschungs-Serie zählt als `serie`). Der Sprung startet die Wiedergabe am
        neuen Track (`Abspielen`, Position 0, Zustand `spielt`) und speichert den
        Zeiger (`ZeigerSpeichern("trackwechsel")`, beim Sprung in die nächste Folge
        `"folgenende"`):
        *   `Weiter`: nächster Track derselben Folge. Beim **letzten Track**: Ziel
            `serie` → erster Track der nächsten Folge (zyklisch, Serien-Zeiger);
            Ziel `folge` → nur `TonSpielen("hinweis")`, Zeiger und Wiedergabe
            unverändert.
        *   `Zurueck`: Ist die zuletzt gemeldete Position im Track (`PlayerPosition`)
            kleiner als `ZURUECK_NEU_S` = 3,0 **und** gibt es einen vorigen Track,
            spielt der **vorige Track** von vorn; sonst startet der **aktuelle
            Track** von vorn (auch im ersten Track).
    *   **Bestätigt (05.11.) für `beendet`** (mit liegendem Tobie, wie beim
        Hauptknopf): `Weiter` wirkt wie `Hauptknopf` kurz (Ziel `serie`: nächste
        Folge ab Zeiger, Ziel `folge`: dieselbe Folge von vorn; Position 0, Zustand
        `spielt`). `Zurueck` spielt die **eben beendete Folge** neu ab Track 0,
        Position 0 (Zustand `spielt`; geändert 05.11., Projektleitung: das Kind
        erwartet „nochmal“) und gilt für beide Typen: Bei Ziel `serie` ist das die
        Folge **vor** dem Serien-Zeiger (zyklisch), der Serien-Zeiger wird auf
        sie gesetzt; bei Ziel `folge` ist es dieselbe Folge. Beide Tasten sind im
        „stumm“-Fenster gesperrt (nur Hinweiston, Tabelle unten).
        **Festlegung (Entscheidung F, 05.11.): einzige Quelle für `Zurueck` in
        `beendet` ist die gemerkte, eben beendete Folge** (Serie und Name, von
        `FolgeZuEnde` gesetzt, mit dem Zustand `beendet` verworfen). Die Sitzung
        setzt `index` durch Nachschlagen des Namens in `Serie.folgen` (bei Ziel
        `folge` bleibt `index` `None`), Track 0, Position 0, und gibt
        `ZeigerSpeichern(grund="zurueck")` aus. Fehlt die Folge inzwischen in der
        Bibliothek, gibt es nur `TonSpielen("hinweis")` und `Protokoll`.
        **`beendet` wird nicht gespeichert:** Nach einem Neustart des Dienstes gibt
        es keine gemerkte Folge und keinen Zustand `beendet`; die Sitzung beginnt
        ohne Wiedergabe (`leer`) mit dem gespeicherten Zeiger (nach einem Folgenende
        steht er schon auf der nächsten Folge bzw. bei einer Folge auf Track 0),
        und ein liegender Tobie startet dort wie beim Auflegen (CUJ 20), **außer nach
        einem Dienst-Neustart ohne Ausschalten (Entscheidung G, 06.11.):** Dann startet
        ein liegender Tobie **nie** von selbst. Ist `neustart_uid` (aus
        `GeraeteEinstellungen`) gesetzt und kommt `Aufgelegt` mit derselben Kennung in
        `leer`, baut die Sitzung den Zielzustand wie im Zweig „stumm“ (Ziel, Serie,
        Folge, Index, Track und Position aus dem gespeicherten Zeiger) und geht auf
        `pausiert`: kein Ton, kein `Abspielen`. Hauptknopf kurz (oder Abheben und
        erneutes Auflegen) spielt am gespeicherten Zeiger. `neustart_uid` wird
        geleert beim ersten `Aufgelegt`, bei `Abgehoben` und bei einem Herzschlag ohne
        Tobie. Ein echtes Einschalten (auch leerer Akku, Stromausfall) lässt
        `neustart_uid` leer: CUJ 20 gilt.
    *   **Im „stumm“-Fenster** (`quiet` im Zustand `stumm`) startet **kein**
        Abspielen-Auslöser eine Wiedergabe. Jeder Auslöser, der ohne „stumm“ ein
        `Abspielen` ergäbe, gibt stattdessen nur `TonSpielen("hinweis")` aus
        (Regel 6.2.3 fasst gleiche Töne zusammen):

        | Auslöser unter „stumm“ | Wirkung |
        |---|---|
        | `Aufgelegt` (Serie oder Folge, unbekannt) und `Gesperrt` in `leer`, `pausiert` | Hinweiston, Zustand `gehalten` (Tabelle des Designs); `Melden` bei unbekanntem Tobie bleibt |
        | `Aufgelegt` (Serie oder Folge) in `beendet` und `gehalten` (Tobie wird neu aufgelegt; bestätigt 05.11.) | nur Hinweiston, nichts startet, Zustand unverändert (`gehalten` bleibt, `beendet` bleibt); `Melden` bei unbekanntem Tobie bleibt |
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
14. **Neue Konfiguration bei liegendem Tobie** (CUJ 7a: Tobias ordnet einen unbekannten Tobie zu, während er noch liegt). Die Sitzung merkt sich den liegenden Tobie (Kennung, Vorgangs-ID, Art) und das Ziel (Art, `serie_id`, bei `folge` auch die Folge), das für
    ihn zuletzt gestartet wurde (auch die Überraschungs-Serie) (Entscheidung F, 05.11.). Kommt
    `KonfigGeladen` und ist die Kennung des liegenden Tobies jetzt einem Ziel `S`
    (Serie oder Folge) zugeordnet (und `S` ist in der Bibliothek; sonst Punkt
    „Serie fehlt“ bzw. „Folge fehlt“ in 6.3: nichts), das **nicht** das zuletzt
    gestartete Ziel ist (anderer Typ, andere Serie oder andere Folge) (Entscheidung F, 05.11.):
    *   `spielt`: Zeiger des laufenden Ziels speichern
        (`ZeigerSpeichern("figurwechsel")`), `S` starten wie beim Auflegen
        (Zeiger laden, `Abspielen`).
    *   `pausiert` und `beendet` (der Tobie liegt): `S` starten wie beim Auflegen,
        Zustand `spielt` (CUJ 7a „wechselt sofort“). Der Zeiger des bisherigen
        Ziels ist dort schon gespeichert.
    *   `gehalten`, `unbekannt`, `leer`: nichts.
    *   Unter „stumm“ in `pausiert`/`beendet`: nur Hinweiston (Punkt 12).
    *   Ist die Zuordnung unverändert, gehört der Tobie zum laufenden Ziel oder ist
        sie eine Aktionskarte, geschieht nichts.

## 10. Wer sendet welches Ereignis, wer führt welchen Befehl aus

| Modul | sendet Ereignisse | führt Befehle aus |
|---|---|---|
| `reader` | `LeserHallo`, `Aufgelegt`, `Gesperrt`, `Abgehoben`, `LeserHerzschlag`, `LeserAlarm`, `LeserFehler`, `LaderGeaendert` (`quelle="leser"`, Ein/Aus, 10.11.) | `LeserPing` |
| `player` | `TrackWechsel`, `FolgeZuEnde`, `PlayerPosition`, `PlayerFehler`, `PlayerVerbindung` | `LautstaerkeSetzen`, `AusgangWaehlen`, `Abspielen`, `Pausieren` |
| `app` | `GeraeteEinstellungen`, `KonfigGeladen` (Start), `BibliothekGeladen` (Start), `ResumeGeladen`, `Bereit`, `Takt`, `ZeitquelleGeaendert` (mit `power`) | alle Befehle (verteilt an die Module) |
| `store` | – | `ZeigerSpeichern` |
| `library` | `BibliothekGeladen` (nach Änderung) | – |
| `outbox` | – | `Melden`; nimmt `Bestaetigt` an |
| `ha` | `KonfigGeladen` (angenommene Liste), `HaLernmodus`, `HaLernmodusAbbruch`, `HaSyncAnstossen`, `HaUpdateAnstossen`, `HaVerbindung` (nur an Statussammler und `selftest`), `Bestaetigt` (an `outbox`; mit `art="gelernt"` auch an den Kern, Entscheidung H, 07.11.) | `EreignisSenden`, `ZustandMelden` (Statussammler baut daraus den Status, Abschnitt 12), Veröffentlichung für `outbox`; veröffentlicht `liste_abgelehnt`, `v_unbekannt`, `befehl_unbekannt` selbst (Punkt 9.9), ohne Kern-Befehl |
| `sounds` | – | `TonSpielen` (auch für `selftest`) |
| `controls` | `Hauptknopf`, `Weiter`, `Zurueck`, `LautstaerkeDrehen` | – |
| `headphones` | `Kopfhoerer` | – |
| `power` | `LaderGeaendert` (`quelle="pisugar"`), `AkkuStand`, `AkkuTiefstand`, `ZeitquelleGeaendert` | `Herunterfahren` |
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
| `ZURUECK_NEU_S` | 3,0 | `pointer.py` (Zurück in den ersten 3 s eines Tracks → voriger Track, sonst aktuellen Track neu starten; Entscheidung F, 05.11.) |
| `SPEICHERN_PERIODISCH_S` | 30 | `session.py` |
| `LESEZEICHEN_TAGE` | 14 | `session.py` (Vorgabe für `Konfig.lesezeichen_tage`, wenn keine Konfiguration geladen ist; Obergrenze der Prüfung 365; Entscheidung N, 09.11.) |
| `STEMPEL_ERNEUERN_S` | 3600 | `pointer.py` (ein unveränderter Zeiger bekommt seinen Zeitstempel erst nach dieser Zeit neu; Entscheidung N, 09.11.) |
| `REST_FERTIG_S` | 15 | `session.py` (Rest bis zum Ende der ganzen Folge, unter dem sie beim Fortsetzen als fertig gehört gilt; Entscheidung I, 09.11.) |
| `REST_REGEL_MIN_FOLGE_S` | 60 | `session.py` (kürzere Folgen sind von der Restregel ausgenommen; Entscheidung I, 09.11.) |
| `TON_MINDEST` | 10 | `sounds.py` (Untergrenze der Ton-Lautstärke in Prozent, Entscheidung J, 09.11.) |
| `HINWEIS_PEGEL_VORGABE`, `HINWEIS_MINDEST` | 15, 10 | `sounds.py` (Hinweiston, Entscheidung J, 09.11.; die Untergrenze war 5) |
| `REST_TOLERANZ_S` | 2 | `session.py` (so weit darf die Position hinter der Trackdauer liegen, damit die Restregel noch gilt; Review B9) |
| `ZIEL_LUFS`, `TOLERANZ_LU` | −18, 1 | `box/tools/lautheit.py` (Lautheit der Töne und Testmedien, Entscheidung J, 09.11.) |
| `LERN_FRIST_S` | 120 | `learn.py` |
| `LERN_ANTWORT_FRIST_S` | 10 | `session.py` (Wartezeit auf HA, wenn im Lernmodus ein Tobie aufgelegt wird, `mono`, Punkt 9.8) (Entscheidung H, 07.11.) |
| `LEERLAUF_S` | 600 (10 min; vorher 1200) | `idle.py` (zählt auch mit liegendem Tobie, Entscheidung O, 09.11.; seit Ein/Aus, 10.11. nur ohne Strom und ab dem Abnehmen gerechnet, Abschnitt 9, Punkt 9) |
| `LADER_SPERRE_S` | 10 | `idle.py` (Sperre für jede Rückmeldung beim Andocken oder Abziehen: Ring, Ton, Sync; gerechnet ab der letzten Rückmeldung oder ab `Bereit`; Ein/Aus, 10.11., Abschnitt 9, Punkt 9) |
| `STROM_UNBEKANNT_S` | 60 | `idle.py` (so lange gilt „Strom unbekannt“, danach „kein Strom“; Ein/Aus, 10.11., Abschnitt 9, Punkt 9) |
| `STROM_WIDERSPRUCH_S` | 5 | `idle.py` (so lange muss ein Widerspruch der Strom-Quellen anhalten, bevor er als WARNING protokolliert wird; V16, Ein/Aus, 10.11., Abschnitt 9, Punkt 9) |
| `FRUEHTON_WARTEN_S` | 3 | `app.py` (so lange ab `Bereit` wartet `app` mit Tönen des Kerns auf das Ende des Frühtons; Ein/Aus, 10.11., Abschnitt 6.5, Punkt 6g) |
| `SIMULATION_RUECKKEHR_S` | 10 | `idle.py` (Simulation: so lange bleibt `herunterfahren`, dann Rückkehr in den normalen Zustand; B1, 09.11.) |
| `ABSCHALT_FRIST_S` | 60 | `power.py` (so lange darf das Abschalt-Kommando höchstens brauchen; B1) |
| `TIEFSTAND_WIEDERHOLEN_S` | 60 | `power.py` (nach einem fehlgeschlagenen Herunterfahren meldet `power` den fortbestehenden Tiefstand frühestens dann wieder; B1) |
| `TON_VOR_HERUNTERFAHREN_S` | 5 | `app.py` (so lange wartet der Dienst vor dem Poweroff auf das Ende des Tons `akku_leer`; B12) |
| `NETZ_KLASSE_WARTEN_S` | 30 | `app.py` (Start-Sync am Lader wartet höchstens so lange auf die erste `NetzKlasse`; B7) |
| `SYSTEMUHR_PRUEFEN_S` | 10 | `app.py` (Pi ohne `[netz]`/`[strom]`: Abstand der NTP-Prüfung der Systemuhr; B15) |
| `GPIOGET_INTERVALL_MIN_S` | 1,0 | `headphones.py` (Rückfall ohne gpiozero: ein `gpioget`-Prozess je Messung, deshalb höchstens einmal je Sekunde; B4) |
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
| `folge` (optional) (Entscheidung F, 05.11.) | `ZustandMelden.folge` und `.track`: `{"name": <Name der Folge>, "track": <int ab 0>}`; fehlt das Feld (oder ist `null`), wenn keine Folge gewählt ist. Ein optionales Feld, kein neues `v` |
| `akku_prozent` | letztes `AkkuStand`; `null` bis zum ersten |
| `lader` | zusammengeführter Strom-Wert (Ein/Aus, 10.11.: letztes `LaderGeaendert` je `quelle`, bei Widerspruch der Leser, solange seine Verbindung steht; Abschnitt 9, Punkt 9); `null` bis zum ersten |
| `netz` | letztes `NetzKlasse` (bis zum ersten: `offline`) |
| `sync` | `SyncGestartet` → `zustand="laeuft"`. `SyncFertig` → `idle`, `ergebnis="ok"`, `neu`, `letzter_ende` = `jetzt.wall`. `SyncAbgebrochen` mit `grund="regel"` oder `grund="nicht_eingerichtet"` → `idle`, `ergebnis="abgebrochen"`, `grund` (09.11., AP 4.8: `nicht_eingerichtet` zählt wie `regel`, kein Fehler); mit anderem Grund → `fehler`, `ergebnis="abgebrochen"`, `grund` |
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
Leser, Medien, Netz, Speicher und lässt `sounds` je Punkt einen Ton spielen:
`pruef_<punkt>_ok` oder `pruef_<punkt>_fehler`, beim Leser in der Simulation `pruef_leser_simulation`
(09.11., Sprach-Töne für Tests). Fehlt die Datei im Tonordner, nimmt `sounds` den allgemeinen Ton
`pruef_ok` bzw. `pruef_fehler`. Kriterium für „ok“:

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
    MPD weg** (9.10): zurück innerhalb 5 s und Tobie liegt → weiter am
    gespeicherten Zeiger mit 3-s-Rücksprung; sonst Pause und neu auflegen.
12. **Hauptknopf kurz bei `pausiert` ohne Tobie** spielt weiter (Play/Pause),
    wie CUJ 19 es für „ohne Tobie“ beschreibt. **Bestätigt (05.11., T):** Im
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
        **Ersetzt am 09.11. durch Entscheidung J (Punkt 31):** Töne folgen der Lautstärke.
    *   Auflegen in `beendet` und `gehalten` unter „stumm“: nur Hinweiston (9.12); `StummBeginnt` in `unbekannt` wirkt erst nach dem
        Verlassen (9.2); `Weiter`/`Zurueck` in `beendet` (9.12; `Zurueck` spielt die eben beendete Folge neu).
14. **Bestätigt (05.11., P): `volume.rampe`** und `LautstaerkeGeaendert` als
    Weg, den Startwert der Rampe zu kennen (Abschnitt 8).
15. **`kopfhoerer`-Grenze** kommt aus `tobibox.toml` als `lautstaerke_kopfhoerer`
    (das Design nennt die Grenze, aber nicht ihre Quelle).
    **Bestätigt (09.11., Entscheidung P, Befund B3): Ist der Kopfhörer-Kontakt nicht lesbar, gilt die Kopfhörer-Grenze.** Das schützt
    die Ohren. `headphones` sendet `KopfhoererLesbar(False)` einmal je Störung, auch beim Start, wenn die erste Messung scheitert.
    `session` setzt dann die Grenze `kopfhoerer` (Wert `lautstaerke_kopfhoerer`), lässt aber den Ausgang, wie er ist, und gibt
    `EreignisSenden("fehler", {baustein: "kopfhoerer", code: "kopfhoerer_unlesbar", text})` aus (einmal). Die Grenze gilt, bis der Kontakt
    wieder lesbar ist: `KopfhoererLesbar(True)` kommt erst nach einem stabilen Wert und nach dem zugehörigen `Kopfhoerer`; steckt dann ein
    Stecker, bleibt die Grenze. `GeraeteEinstellungen` nach dem Ausfall setzen die Grenze ebenfalls.
16. **Bestätigt (05.11., P, Review-Befund 6): Neue Konfiguration bei liegender
    Tobie** wechselt auf die zugeordnete Serie, auch in `pausiert` und `beendet`
    (9.14), damit CUJ 7a „Box wechselt sofort“ erfüllt ist.
17. **Bestätigt (05.11., T): Zuordnung auf eine noch nicht synchronisierte
    Serie** spielt die Überraschungs-Serie, protokolliert den Grund, und die
    Zuordnung gilt beim nächsten Auflegen (6.3).
18. **Bestätigt (05.11., P): Bestätigung mit `zuletzt`** (und `art`): die Box
    löscht nur bei Übereinstimmung (Abschnitt 7).
    **Bestätigt (05.11., T/P): `DienstEndet`** (Dienst-Ende per SIGTERM) pausiert
    und speichert den Zeiger wie `HerunterfahrenAngefordert`, löst aber **kein**
    `Herunterfahren` aus (nur der Dienst endet, das Gerät läuft weiter).
19. **Offen: Statusaufbau (Abschnitt 12).** Quellen der Felder, Abbildung von
    `leser` und die Kriterien der vier Prüfpunkte sind Vorschläge der
    Umsetzung; insbesondere `SPEICHER_MIN_FREI_MB` = 500 und „Netz ok nur mit
    Broker“. Tobias entscheidet, ob die Schwellen so passen.
20. **Offen: Position abgerundet** auf eine Nachkommastelle (3.8) und die
    Umsetzung von „MPD weg“ als Frist innerhalb des Zustands `spielt` (kein
    neuer Zustand, damit die Zustandsliste des Designs und der Status gleich
    bleiben).
21. **Bestätigt (05.11., Entscheidung F, T): Tobies zeigen auf Serie oder Folge.**
    `Zuordnung.typ` ist `serie`, `folge` oder `aktion`; es gibt Serien-Zeiger und
    Folgen-Zeiger (`Zeiger.art`). Die Überraschungs-Serie verhält sich wie ein
    Ziel `serie`.
22. **Bestätigt (05.11., Entscheidung F, T): Track und Folgenende.** Eine Folge
    spielt alle Tracks ohne Pause (`TrackWechsel`); die Pause nach jeder Folge
    (Entscheidung A) gilt erst bei `FolgeZuEnde`. Ein Folgen-Zeiger springt am
    Ende auf Track 0 / 0 s, das nächste Auflegen spielt von vorn (6.3).
23. **Bestätigt (05.11., Entscheidung F, T): Vor / Zurück nach Track** (9.12):
    Zurück in den ersten 3 s eines Tracks → voriger Track, sonst aktuellen Track
    neu; beim letzten Track Vor → nächste Folge (`serie`) bzw. Hinweiston
    (`folge`); in `beendet` Hauptknopf kurz und Vor: `serie` nächste Folge,
    `folge` dieselbe von vorn; Zurück: die eben beendete Folge von vorn.
24. **Offen (05.11., Entscheidung F, P):** Zurück im ersten Track innerhalb von
    3 s startet den Track neu (es gibt keinen vorigen Track, auch bei `serie`
    kein Sprung in die vorige Folge); als Hinweiston bei `Weiter` am Ende eines
    `folge`-Ziels wird der vorhandene Ton `hinweis` benutzt; ein Folgen-Tobie
    auf eine fehlende Folge spielt die Überraschungs-Serie (`folge_fehlt`).
    Tobias bestätigt oder ändert das.

25. **Bestätigt (05.11., Entscheidung F): Position und Player-Ereignisse in jedem
    Zustand mit laufendem MPD.** `PlayerPosition` wird nur in `spielt` und
    `unbekannt` und nur bei passender Serie, Folge und Track übernommen;
    `TrackWechsel` und `FolgeZuEnde` führen den Zeiger in jedem Zustand mit
    laufendem MPD nach (`unbekannt`, Ausblenden wegen „stumm“, MPD-Frist);
    `FolgeZuEnde` in `unbekannt` → `beendet`, während des Ausblendens →
    `gehalten` (6.3).
26. **Bestätigt (05.11., Entscheidung F): Zurück in `beendet`** nimmt die gemerkte,
    eben beendete Folge als einzige Quelle, setzt `index` durch Nachschlagen,
    Grund `zurueck`; `beendet` wird nicht gespeichert (9.12).
27. **Bestätigt (05.11., Entscheidung F): fehlender oder unlesbarer Track** in
    einer Folge mit mehreren Tracks wird übersprungen (`datei_fehlt` im
    Protokoll), erst nach dem letzten Track gilt das Ende der Folge (9.10).
28. **Bestätigt (05.11., Entscheidung F): Statusfeld `folge`** `{name, track}`
    ist optional (12.1).
29. **Bestätigt (07.11., Entscheidung H, T): Lernmodus wartet still.** Ein im
    Lernmodus aufgelegter Tobie startet nichts, bis HA die Zuordnung schickt, die
    Ablehnung meldet oder 10 s vergangen sind (9.8); eine andere Konfiguration
    (gleiches Ziel für diesen Tobie) beendet das Warten nicht, ein unbekannter Tobie
    wird nach der Ablehnung erneut gemeldet, und nach der Frist löst eine Aktionskarte
    ihre Aktion aus. Dauert die Rückfrage von HA länger als 10 s, spielt ein bekannter
    Tobie zuerst sein altes Ziel und wechselt mit der Zuordnung (gewollt). Hauptknopf und Vor / Zurück
    bewirken in dieser Zeit nichts, die Lautstärke wirkt (Festlegung der
    Projektleitung nach Empfehlung; Tobias kann sie ändern).
30. **Bestätigt (09.11., Entscheidung I, T): Ein kleiner Rest gilt als fertig gehört.**
    Beim Fortsetzen an einem gespeicherten Zeiger (Auflegen, Einschalten, Hauptknopf in
    `pausiert`, auch nach einem Dienst-Neustart) gilt die Folge als fertig, wenn bis zum Ende der
    ganzen Folge weniger als 15 s fehlen (6.3). Anlass: Ein Tobie wurde im Abspann abgehoben
    (122,0 s von 123,6 s); jedes neue Auflegen spielte wegen des 3-s-Rücksprungs nur die letzten
    Sekunden, und das Ende der Folge wurde nie erreicht. Folgen unter 60 s und Folgen mit
    unbekannter Dauer sind ausgenommen. Die Dauer kommt aus der Bibliothek (`Serie.dauern`), die
    Sitzung bleibt rein. Pause nach jeder Folge (A), Dienst-Neustart bleibt pausiert (G) und
    Lernmodus (H) gelten unverändert.
31. **Bestätigt (09.11., Entscheidung J, T): Die Töne folgen der Lautstärke des Hörspiels.**
    Anlass: Am Mac waren die Box-Töne viel lauter als das Hörspiel, und eine gesprochene Testfolge
    mit derselben Stimme und demselben Dateipegel wie die Ansage `start` war „ultra leise“. Ursache
    war die Wiedergabe, nicht die Dateien: Töne liefen mit festem Pegel 40 % **linear**
    (−8 dB), das Hörspiel mit der MPD-Lautstärke 20 % auf der **exponentiellen** Kennlinie des
    MPD-Software-Mixers (−33 dB), also rund 25 dB leiser. Neu: Pegelregel und Kennlinie wie in 8.1,
    Untergrenze 10, Töne und Testmedien bei −18 LUFS, Testmedien mit ReplayGain-Tags. Der Kern bleibt
    rein; `app.py` führt die Lautstärke aus dem Zustand des Kerns nach. *Nachtrag (Code-Review, 09.11.):* ohne die
    Rampen `ausblenden` und `gute_nacht`; der Pegel entsteht erst beim Abspielen des Tons; die Grenze gewinnt immer,
    auch beim Hinweiston (8.1).
32. **Bestätigt (09.11., Entscheidung L, T): Es spielen nie zwei Sachen gleichzeitig.**
    Anlass am Mac mit den Sprach-Tönen: Im Lernmodus kam „Lernmodus beendet.“ gleichzeitig mit „Test-Serie,
    Folge drei.“, und „Diesen Tobie kenne ich noch nicht …“ überlappte sich mit der Überraschungs-Serie. Töne
    liefen als Hintergrundaufgaben neben MPD. Neu (Abschnitt 6.5, Punkt 6, und 8.1): Töne laufen einzeln über
    eine Spur; die Wiedergabe startet nach dem Ende der Töne derselben Ausgabe; ein Ton während des Hörspiels
    hält es kurz an und setzt es an derselben Stelle fort (kein Zeiger, kein Rücksprung, kein Status
    „pausiert“); Abheben und `Pausieren` verwerfen einen wartenden Start, der Ton läuft zu Ende; ein hängender
    Ton wird nach 10 s beendet. Der Kern, sein Rang (6.4) und seine Tests bleiben unverändert; die Regel gilt in
    `app.py`, `sounds.py` und `player.py`.
33. **Bestätigt (09.11., Entscheidung N, T): Lesezeichen je Tobie mit Ablauf.**
    Jeder Zeiger behält seine eigene Stelle (so war es schon: CUJ 4, `resume.json`). Neu: Wurde ein Zeiger länger als
    `lesezeichen_tage` (Vorgabe 14, einstellbar in HA, `0` = nie) nicht benutzt, beginnt beim Fortsetzen die Folge von
    vorn (Position 0, erster Track); bei einer Serie bleibt die Folge dieselbe, bei einem Folgen-Tobie beginnt dieselbe
    Folge von vorn. Die Regel gilt nur bei sicherer Uhr (`jetzt.zeit_ok`), nur für Zeiger mit Zeitstempel
    (`resume.json`: `benutzt_am`, optional, additiv; ein alter Zeiger ohne Stempel läuft nie ab) und an denselben Stellen
    wie die Restregel; der Ablauf geht der Restregel voran (6.3). Das Feld `lesezeichen_tage` in `config.json` ist
    additiv, `schema_version` bleibt 2; eine Seitenbedienung kommt mit den Einstellungen in Stufe 4. Der Kern bleibt
    rein: Die Wanduhr kommt über `jetzt`.
