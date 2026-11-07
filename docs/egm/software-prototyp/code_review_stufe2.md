# Code-Review Stufe 2 (Goldfisch, frischer Blick)

Stand: `git diff 2d2cbf2..HEAD -- box/` (Stufe 2: Resume-Tests, `learn`, `outbox`, `sim`,
`ha_ersatz`, `status`, `selftest`, CLI, Verdrahtung in `app`).
Maßstab: `docs/designs/box-software.md` (Stufe 2), `docs/protocol/core-interface.md`,
`docs/protocol/mqtt-v1.md`, `docs/data-model.md`.

Testlauf (Python 3.11, venv): `pytest tests/unit tests/cuj tests/integration`: 1393 grün, 1 rot
(`tests/cuj/test_cuj02_abheben.py::test_app_abheben_pausiert_mpd_und_protokolliert_die_kette`).
Der Test ist allein wiederholt grün (6 von 6) und gehört nicht zu diesem Diff; siehe Befund 12.

Kein Blocker. Drei mittlere Befunde, die ich belegt habe; der Rest ist niedrig.

---

## Mittel

### 1. Aufräumen löscht die Temp-Datei eines laufenden Zeiger-Schreibens (Datenverlust Zeiger)

- **Datei:Zeile:** `box/src/tobibox/store.py:600` (`KonfigStore.laden` ruft `raeume_auf`),
  aufgerufen aus `box/src/tobibox/ha_ersatz.py:37` (`schreibe_zuordnung` ruft `store.laden()`),
  Gegenstück: `box/src/tobibox/app.py` (`ZeigerSpeichern` läuft in `asyncio.to_thread`).
- **Szenario:** Während der Wiedergabe schreibt ein Thread `resume.json.tmp` (`write`, `fsync`, dann
  `os.replace`). Zur selben Zeit kommt `tobibox sim card …` oder ein gelernter Tobie. Der
  Event-Loop ruft `schreibe_zuordnung`, das jedes Mal `KonfigStore.laden()` und damit `raeume_auf()`
  aufruft. `raeume_auf` löscht **alle** `*.tmp` im Zustandsverzeichnis, auch die des Threads. Danach
  scheitert dessen `os.replace` mit `FileNotFoundError`. Der Zeiger dieses Zyklus ist nicht gespeichert
  (nur ein ERROR `befehl_fehler` im Protokoll). Beim Abheben, also beim wichtigsten Speichern, ginge die
  Position verloren. Auf der SD-Karte des Pi dauert `fsync` Zehntelsekunden, das Fenster ist also nicht
  winzig. Vor Stufe 2 lief `raeume_auf` nur beim Start; neu ist der Aufruf zur Laufzeit.
- **Vertrag:** `data-model.md` 1.2/1.3 (Datei nie halb geschrieben, Zeiger höchstens 30 s verloren);
  Design Stufe 2, Abnahme „höchstens 30 s Wiedergabe verloren“.
- **Beleg:** Wegwerf-Skript `scratchpad/rv/race.py`: `fsync` auf 0,2 s verlangsamt, ein Thread schreibt
  `resume.json`, der Loop ruft nach 0,05 s `KonfigStore.laden()`. Ergebnis:
  `FileNotFoundError`, `resume.json` existiert nicht.
- **Vorschlag:** `raeume_auf` nur beim Start aufrufen (einmal in `app._starte`), nicht in
  `KonfigStore.laden()` und nicht in `Outbox.laden()`. Alternativ in `schreibe_zuordnung` den Store nicht
  neu von der Platte laden, sondern `store.roh` benutzen. Zusätzlich ein Test: `KonfigStore.laden()`
  lässt eine fremde `*.tmp` stehen.

### 2. Ein Fehler beim Öffnen von `sim.sock` bringt den ganzen Dienst zu Fall

- **Datei:Zeile:** `box/src/tobibox/sim.py:171-182` (`start`), `box/src/tobibox/app.py:331`.
- **Szenario:** `Sim.start()` fängt nur `FileNotFoundError`. Ein zu langer Socket-Pfad
  (`AF_UNIX path too long`, Grenze 108 Zeichen), ein nicht löschbares altes `sim.sock`
  (`PermissionError`) oder ein schreibgeschütztes Zustandsverzeichnis werfen `OSError`. In
  `app._starte` steht `await self.sim.start()` **nach** `Bereit` und `leser.start()`. Die Ausnahme
  läuft in `starte()`, das alles abräumt und neu wirft. Der Dienst ist nicht bereit, systemd startet neu,
  und die Box ist stumm. Der Startton `start` ist da schon gespielt. Ein Hilfs-Treiber (Ersatz für HA)
  darf die Box nicht verhindern.
- **Vertrag:** Design „Fehlerpfade“ und Prinzip „die Box spielt auch ohne Hilfsdienste“; AP 2.2 nennt
  `sim` einen Treiber, nicht eine Voraussetzung.
- **Beleg:** Wegwerf-Skript `scratchpad/rv/lang.py`: `Sim(...100 Zeichen Pfad...).start()` wirft
  `OSError: AF_UNIX path too long`. Der Aufruf in `app.py` ist ohne `try`.
- **Vorschlag:** In `app._starte` den Start von `sim` in `try/except OSError` setzen, ERROR
  protokollieren und weiterlaufen (`tobibox status` meldet dann „nicht erreichbar“). Ein Test mit zu
  langem Pfad.

### 3. Zweiter `sim learn` im laufenden Lernmodus verdirbt den ersten Lernlauf

- **Datei:Zeile:** `box/src/tobibox/sim.py:109-110` (`_learn` überschreibt `lernziel` und
  `lernbefehl_id` schon beim Parsen), `box/src/tobibox/ha_ersatz.py:65` (Vergleich der `befehl_id`).
  Der Test `box/tests/unit/test_sim.py::test_learn_merkt_die_befehls_id_fuer_den_ha_ersatz` hält dieses
  Verhalten fest.
- **Szenario:** Tobias startet `sim learn --serie A`, tippt nach 20 s versehentlich noch
  `sim learn --serie B`. Die Box ignoriert den zweiten Befehl (`learn.py`: `laeuft_schon`), der erste
  Lernmodus läuft weiter. `sim` hat aber `lernziel=B` und `lernbefehl_id=<id B>` gemerkt. Legt Tobias
  jetzt den Tobie auf, meldet die Box `gelernt` mit der ID von A. Der HA-Ersatz sieht
  `ID ≠ lernbefehl_id` und antwortet `abgelehnt`. Der Tobie bleibt unzugeordnet, der Eintrag ist gelöscht
  (Lernlauf verloren), nur eine WARNING im Protokoll. Dasselbe Muster gilt für einen vom Kern
  abgelehnten Befehl (unsichere Uhr, abgelaufen), der ein altes, noch gültiges Ziel überschreibt.
- **Vertrag:** `core-interface.md` 9.9 (zweiter Befehl in `lernt` wird ignoriert);
  `mqtt-v1.md` 4.2 (HA merkt sich Box, Ziel und Beginn des **angenommenen** Befehls).
- **Beleg:** Wegwerf-Test `scratchpad/rv/test_zweimal.py` (mit `SimBox`): zwei `learn`, dann Auflegen.
  Ergebnis: `zuordnungen == {}`, Assertion „Lernlauf 1 ging verloren“ schlägt fehl.
- **Vorschlag:** `lernziel`/`lernbefehl_id` erst setzen, wenn die Box den Befehl angenommen hat
  (z. B. aus `learn`: `LernenGeaendert(True)` samt `befehl_id` zurückmelden), oder: `sim` lehnt einen
  zweiten `learn` ab, solange ein Lernlauf läuft und noch nicht abgebrochen wurde. Test ändern.

---

## Niedrig

### 4. Datei-Schreiben mit `fsync` blockiert den Event-Loop

- **Datei:Zeile:** `box/src/tobibox/app.py:225-233` (`_melde` → `Outbox.melden` → `schreibe_atomar`),
  `app.py:123` (`Outbox.bestaetigt`), `ha_ersatz.py` und `sim.py` (`schreibe_zuordnung`: Lesen, drei
  Dateien mit `fsync`).
- **Szenario:** Jedes Melden, Bestätigen oder Zuordnen schreibt synchron auf dem Loop, auf der SD-Karte
  Zehn- bis Hunderte Millisekunden. In dieser Zeit stehen Leser-Ereignisse, Takt, `Abspielen` und MPD-
  Antworten still. Den Zeiger schreibt der Code mit `to_thread`, genau deshalb.
  Das Melden steht im Rang nach `Abspielen`, die 1-s-Grenze beim Auflegen ist also kaum betroffen, die
  Pause-Grenze beim Abheben direkt nach einem unbekannten Tobie schon.
- **Vorschlag:** `Outbox._speichern` und `schreibe_zuordnung` in `asyncio.to_thread` (mit einer Sperre
  je Datei) oder im Pi-Probelauf ausmessen und das Ergebnis festhalten.

### 5. `letzter_fehler.zeit` ist eine Zahl, der Vertrag verlangt einen Zeitstempel

- **Datei:Zeile:** `box/src/tobibox/status.py:66`; Test `box/tests/unit/test_status.py:78` hält die
  Zahl fest.
- **Szenario:** `{"zeit": 1731000000.123, …}` statt `"2026-11-05T09:12:03.412Z"`. Die HA-Integration
  (Stufe 3a) bekommt einen anderen Typ als in `mqtt-v1.md` 3.3 (`{"zeit": <Zeitstempel>, "text": …}`,
  `ts` ist dort ein String).
- **Vorschlag:** `zeitstempel(jetzt.wall)` aus `outbox.py` benutzen; Test anpassen.

### 6. Prüfpunkt „Leser“: `leser_simulation` wird nie gesetzt

- **Datei:Zeile:** `box/src/tobibox/app.py:91` (`Statussammler()` ohne Argument),
  `status.py:25/72`.
- **Szenario:** `core-interface.md` 12.2 kennt die Zeile `simulation` (Leser-Ereignisse aus `sim`).
  Der Parameter ist toter Code: Wer die Box ohne Leser startet, sieht `getrennt` und beim Status-Karten-Ton
  einen Fehler. Dazu: In Stufe 2 gibt es kein `NetzKlasse` und kein `HaVerbindung`, der Prüfpunkt Netz
  ist also immer ein Fehlerton. Das folgt dem Vertrag, sollte Tobias aber vor der Vorführung wissen.
- **Vorschlag:** Entweder die Bedingung im Dienst festlegen (z. B. Konfiguration `leser.geraet = "sim"`)
  oder das Feld streichen und im Vertrag 12.2 vermerken. Den Hinweis zum Netz in die Abnahme schreiben.

### 7. `sim=true` wird im Protokoll nie gesetzt

- **Datei:Zeile:** `app.py` (`ereignisse_ein`, `verarbeite`); `eventlog.py:151` kann es.
- **Szenario:** Ereignisse von `sim` (`learn`, `ack`, `card`, Bestätigungen des HA-Ersatzes) sind im
  Protokoll nicht von echten zu unterscheiden. Beim Pi-Probelauf lässt sich dann nicht erkennen, was
  simuliert war.
- **Vertrag:** `core-interface.md` 6.5 Punkt 4; Design Zeile 1444 („Simulierte Ereignisse tragen
  `sim=true`“).
- **Vorschlag:** `ereignisse_ein` merkt die `id()` der Ereignisse (oder verpackt sie), `verarbeite`
  gibt `sim=True` an `logge_befehl` weiter.

### 8. HA-Ersatz überschreibt bestehende Zuordnungen ohne Nachfrage (auch Aktionskarten)

- **Datei:Zeile:** `ha_ersatz.py:65-80`; Test `test_cuj07b_lernmodus.py::test_bereits_zugeordneter_tobie_wird_neu_zugeordnet`
  hält es fest.
- **Szenario:** Im Lernmodus liegt die Status-Admin-Karte (oder ein Tobie, der schon läuft). Sie wird
  stillschweigend auf das Lernziel umgeschrieben (Revision + 1). `mqtt-v1.md` 4.2 Punkt 4: „Ist die
  Kennung schon zugeordnet, fragt HA vor dem Überschreiben nach.“
- **Einordnung:** Nur Stufe 2, Tobias startet den Lernmodus selbst. Aber der Ersatz soll „wie HA es täte“
  sein.
- **Vorschlag:** Entweder `abgelehnt` bei bestehender Zuordnung und ein Schalter `sim learn --ueberschreiben`,
  oder die Abweichung im Kopf von `ha_ersatz.py` und im Design nennen.

### 9. `learn` nimmt auch eine Wiedermeldung als „aufgelegt“

- **Datei:Zeile:** `box/src/tobibox/learn.py:81`.
- **Szenario:** Nicht nachgestellt, aus dem Vertrag abgeleitet. Liegt ein Tobie T schon auf der Box, und
  Tobias startet den Lernmodus, dann kann der Leser T erneut melden (Wiedermeldung auf `PING` oder nach
  Firmware-Neustart, gleiche Vorgangs-ID, `core-interface.md` 3.1 und 9.1). `session` behandelt das als
  No-op, `learn` nicht: T wird als `gelernt` gemeldet und umgeschrieben (siehe Befund 8). Der Lernmodus
  endet, bevor der neue Tobie aufliegt.
- **Vorschlag:** `learn` merkt sich bei Beginn die `vorgang`-ID des liegenden Tobies nicht (rein), besser:
  `core` reicht Wiedermeldungen nicht an `learn` durch, oder `learn` bekommt `figur_liegt` + `vorgang`
  vom Kern. Mit dem Vertragsautor klären, ob Tabelle „Lernmodus“ das so meint.

### 10. Mini-Randfälle im Ausgang und im Treiber

- `outbox.py:99`: Beim 201. Eintrag wird der mit dem ältesten `zuletzt` verworfen. Bei einer Uhr, die
  hinter den vorhandenen Einträgen liegt (Pi ohne RTC vor NTP), ist das der **gerade hinzugefügte**.
  Dann wirft `app._melde` (`next(...)`, `app.py:231`) `StopIteration`, als Coroutine zu `RuntimeError`,
  und der gelernte Tobie wird nicht zugeordnet und nicht bestätigt. Sehr selten (200 offene Einträge).
  Vorschlag: den neuen Eintrag vom Verwerfen ausnehmen.
- `cli.py:_frage_socket`: `PermissionError` (Socket gehört dem Dienst-Benutzer, Rechte 0600, der
  Administrator ist ein anderer Benutzer) wird wie „Dienst nicht erreichbar“ gemeldet. Vorschlag:
  getrennt melden („keine Berechtigung auf sim.sock“).
- `sim.py:start`: `os.umask(0o177)` gilt für den ganzen Prozess, auch für Threads, die in dem Moment
  eine Zustandsdatei anlegen (Rechte 0600 statt 0644). Nur beim Start, Auswirkung klein. Besser
  `socket.bind` selbst mit vorbereitetem Socket und `chmod` vor `listen`.
- `sim.card` erhöht im Betrieb die Revision lokal. Bleibt `sim.sock` nach Stufe 3a im Dienst, kollidiert
  das mit den Listen von HA (`revision_zu_niedrig` oder stilles Überschreiben). Vorschlag: `sim` nur mit
  ausdrücklichem Schalter in `tobibox.toml` und im Pi-Betrieb aus.
- `app.py:123`: `Bestaetigt` läuft nach der Outbox auch durch `core.step` (und `HaVerbindung`
  analog). `core-interface.md` 3 sagt „geht nicht an den Kern“. Harmlos (alle Teilautomaten ignorieren
  es), aber unnötige Arbeit und Abweichung vom Vertrag.
- Der Prüfpunkt Medien nutzt die beim Start gelesene Bibliothek (`app.py:pruefbericht`) und prüft nur
  `medien.is_dir()`. „Medienordner lesbar“ (12.3) ist damit nicht belegt, wenn Dateien später fehlen.
  In Stufe 3a (Sync) ohnehin neu zu laden.

### 11. Tests: prüfen weniger, als der Name sagt

- `box/tests/unit/test_sim.py::test_ungueltige_zeile_wird_ignoriert` bekommt `caplog`, prüft es aber nie.
  AP 2.2 verlangt „ungültige Zeilen werden **protokolliert** und ignoriert“. Dass protokolliert wird,
  ist ungeprüft.
- `box/tests/conftest.py:430 SimBox` baut die Verdrahtung aus `app.py` nach (`sende` ≈
  `App.verarbeite` + `_melde` + `HaErsatz`, Nachlauf statt echter Queue). CUJ 7a und 7b prüfen damit
  den Nachbau, nicht `App`. Der echte Pfad ist nur durch `unit/test_app.py` (ein Lern-Test) und
  `integration/test_sim_cli.py` (braucht MPD) gedeckt. Weicht `App` ab, bleibt CUJ 7b grün.
  Vorschlag: mindestens je ein CUJ-7b-Fall (Frist, Abbruch, zweiter Befehl) gegen `App` mit der
  `Tonfang`-Technik aus `test_cuj11_status.py`.
- `test_cuj11_status.py` setzt `status.hallo` und `app.bibliothek` von Hand; die Zeile „Medien: Ordner fehlt“
  prüft `is_dir()` und nicht das Lesen der Bibliothek. Das passt zum Code, nicht zu „lesbar“.

### 12. Instabiler Test außerhalb des Diffs

- `tests/cuj/test_cuj02_abheben.py::test_app_abheben_pausiert_mpd_und_protokolliert_die_kette` schlug im
  vollen Lauf einmal fehl (Last, 196 s), allein 6 von 6 grün. Er ist nicht Teil dieses Diffs, hängt aber
  an Zeitgrenzen mit echtem MPD. Beobachten.

### 13. Logik doppelt

- `app.pruefbericht`/`app.status_auskunft` rechnen Medien-Ordner, freien Platz und Bibliothek selbst aus,
  `selftest.pruefe` tut dasselbe für die eingebaute Prüfroutine. Dazu rechnet `cli.sammle_status`
  `medien_ok` (`cli.py:130`) noch einmal wie `selftest.pruefe_medien`. Die Bewertung selbst
  (`pruefe_*`) ist geteilt, nur die Sammlung der Messwerte nicht. Heute kein Fehler, aber drei Stellen für
  eine Änderung von 12.3.

---

## Geprüft, ohne Befund

- **`learn.py` gegen Tabelle „Lernmodus“ und 9.8/9.9:** Beginn, Frist auf `jetzt.mono` ab Annahme
  (`LERN_FRIST_S`), Abbruch, `Gesperrt` ändert nichts, zweiter Befehl ignoriert, abgelaufener Befehl nur
  Protokoll ohne `EreignisSenden`, unsichere Uhr lehnt `HaLernmodus` ab (mit `befehl_abgelehnt`,
  `grund=zeit_unsicher`), Abbruch bei unsicherer Uhr ohne Ablaufprüfung und nie abgelehnt. Reihenfolge
  Ablaufzeit vor Uhr entspricht der Tabelle in 9.9.
- **Zustand „Lernmodus hängt“:** Ende nur über `Takt` (alle 0,1 s), `Aufgelegt` oder Abbruch; kein Pfad,
  der `lernt` ohne Ablauf lässt. Neustart des Dienstes setzt `learn` zurück (Zustand nur im Speicher).
- **Konfliktregeln 6.2:** `Melden("unbekannt")` von `session` und `Melden("gelernt")` von `learn` zu einem
  Befehl, `gelernt` gewinnt (Test `test_cuj07b…::test_ziel_serie…`); Töne unter „stumm“ zu `hinweis`,
  `pruef_*` bleiben.
- **`outbox.py` gegen Abschnitt 7 und `data-model.md` 4:** `gelernt` ersetzt `unbekannt`, nie
  umgekehrt; Löschen nur bei gleichem `zuletzt` **und** `art`; veraltete und doppelte Bestätigung
  wirkungslos; höchstens 200; Schreiben atomar mit `.bak` und `fsync`; Eintrag überlebt Neustart
  (Tests `test_outbox.py`, `test_cuj07a…`, `test_app.py`).
- **Atomares Schreiben (`schreibe_atomar`)** für `unknown.json`, `config.json`: Temp-Datei, `fsync`,
  `.bak` per Hardlink, `replace`, Verzeichnis-`fsync`. (Ausnahme: Befund 1.)
- **`config.json` Version 2 durch `schreibe_zuordnung`:** `ziel` als Unterobjekt, Revision + 1,
  Listen-ID `0000000000000000` im Ersatzbetrieb, alte Zuordnungen bleiben, ungültige Kennung und
  fehlendes Ziel werden vor dem Schreiben abgelehnt, Datei bleibt dann unverändert.
- **Unix-Socket `sim.sock`:** Rechte 0600 (mit `umask`, dann `chmod`), alter Socket wird entfernt, wird
  beim Beenden gelöscht (auch zweimaliges `stop()` ist ungefährlich); zu lange Zeile wird beendet;
  ungültige Zeilen bekommen eine Fehlerantwort, die Verbindung lebt weiter; `status` erzeugt kein
  Ereignis. Beenden mit offener Verbindung hängt unter Python 3.11 und 3.12.3 nicht (geprüft).
- **Wiedergabe startet von selbst:** `KonfigGeladen` aus `sim card` oder HA-Ersatz startet nur bei
  geändertem Ziel des liegenden Tobies und nur in `spielt`, `pausiert`, `beendet` (9.14); ein
  Dienst-Neustart mit liegendem Tobie bleibt `pausiert` (Entscheidung G), auch bei unbezogener
  Konfigurationsänderung. Aktionskarten lösen keine Wiedergabe aus.
- **Status-Admin-Karte:** vier Prüfpunkte in fester Reihenfolge, Tonfolge nacheinander (nie zwei Töne
  gleichzeitig, Test `test_sounds.py`), `pruef_*` unter „stumm“ unverändert, `datei_verloren` zählt erst
  seit dem Start (`_verloren_basis`), Kriterien Netz/Speicher/Medien entsprechen 12.3. Die Töne
  `pruef_ok.wav`/`pruef_fehler.wav` sind eingecheckt und von `make_sounds.py` reproduzierbar.
- **Statussammler gegen 12.1/12.2:** Felder und Quellen, `firmware` null ab `LeserAlarm`, 10-s-Fenster
  auf `mono`, `warnung`/`hinweis` ändern `leser` nicht, `folge` nur bei gewählter Folge,
  `zustand=herunterfahren`.
- **Resume-Tests (AP 2.1):** Rücksprung 3 s, Pause nach jeder Folge, Zeiger auf Folge 1 nach der letzten,
  Folgen-Tobie von vorn, Zeiger über Neustart; `test_resume_neustart.py` prüft die 30-s-Grenze mit
  echtem `SIGKILL` und die Pause nach Dienst-Neustart; `test_cuj03…::test_resume_nach_leerem_akku…`
  prüft die Grenze mit nachgestellter Zeit wirklich (Zeiger bei 60 s, nicht bei 75 s).
- **CLI:** `sim learn|learn-abort|ack|card`, Exit-Codes (2 Eingabe, 3 Dienst nicht erreichbar, 1 abgelehnt),
  `ack` liest `zuletzt`/`art` aus `unknown.json`, `card` schreibt `ziel` (Version 2), `status` ändert
  nichts und zeigt Dienst und Dateien.
- **Tests ohne Prüfung:** per Skript alle neuen Testfunktionen auf fehlende `assert` geprüft: keine
  Funktion ohne Prüfung, kein `skip`/`xfail`/`or True`.
- **Beenden/Neustart:** `sim.stop()` vor `leser.stop()` in `_raeume_auf` und in `beende`;
  `DienstEndet` wird weiter verarbeitet; offene Meldungen werden beim Start geladen und protokolliert.
- **Rechte/Geheimnisse:** kein Tonie-Passwort im Diff; `config.example.h` unberührt.

---

## Auflösung (07.11., Umsetzung durch Agent, Entscheidungen der Projektleitung)

Je Befund eine Zeile. Alle Änderungen mit Tests; die ganze Suite lief zweimal hintereinander grün.

1. **Behoben.** `raeume_auf` läuft nur noch einmal beim Dienststart (`app._starte`), nicht mehr aus `KonfigStore.laden`, `ResumeStore.laden` und `Outbox.laden`. Tests: `laden` lässt fremde `*.tmp` stehen; `schreibe_zuordnung` während eines langsamen Zeiger-Schreibens (`test_ha_ersatz.py`).
2. **Behoben.** `OSError` beim Öffnen von `sim.sock` (Pfad zu lang, Rechte, Verzeichnis) gibt ERROR `sim_start` im Protokoll, die Box läuft ohne Simulations-Treiber weiter; `Sim.start` räumt halb Angelegtes weg, `Sim.stop` löscht nur ein selbst geöffnetes Socket. Tests in `test_sim.py` und `test_app.py`.
3. **Behoben.** `sim` merkt Ziel und Befehls-ID vor und übernimmt sie erst, wenn der Kern den Lernmodus begonnen hat (`Ausgang.nach_kern` -> `Sim.angenommen`). Ein ignorierter oder abgelehnter `learn` ändert den laufenden Lernlauf nicht. Der alte Test ist angepasst, neue Tests in `test_sim.py`, `test_cuj07b_lernmodus.py`, `test_cuj07b_app.py`.
4. **Behoben.** Outbox: Speicher ändert sich sofort, eine einzige Hintergrundaufgabe schreibt den jeweils neuesten Stand in `asyncio.to_thread` (keine Reihenfolgefehler, Beenden wartet darauf). `schreibe_zuordnung` und `sim card` laufen in einem Thread, mit Sperre gegen gleichzeitige Zuordnungen. Tests in `test_outbox.py`, `test_ha_ersatz.py`, `test_sim.py`.
5. **Behoben.** `letzter_fehler.zeit` ist ein Zeitstempel-String (`zeitstempel(jetzt.wall)`), Test angepasst.
6. **Behoben.** `leser.geraet = "sim"` (Beispiel-Konfiguration kommentiert) heißt: kein Leser; der Statussammler meldet `simulation`, die Status-Karte wertet das als in Ordnung. Netz bleibt in Stufe 2 vertragsgemäß ein Fehler (keine Änderung). Tests in `test_status.py`, `test_cuj07b_app.py`.
7. **Behoben.** Alle Zeilen von `sim` und HA-Ersatz tragen `sim=true`; `app` schreibt auch die Kern-Protokollzeilen zu einem Ereignis von `sim` mit `sim=true` (`Ausgang.war_sim`). Test `test_cuj07b_app.py`.
8. **Behoben.** Der HA-Ersatz überschreibt eine bestehende Zuordnung nur mit `sim learn --ueberschreiben`; sonst `Bestaetigt` mit `grund` „abgelehnt“ und eine WARNING-Zeile mit Hinweis auf den Schalter. CLI-Hilfe angepasst; Tests in `test_ha_ersatz.py`, `test_cli.py`, `test_cuj07b_lernmodus.py`, `test_cuj07b_app.py`.
9. **Behoben.** Die Tabelle „Lernmodus“ schweigt dazu, aber `core-interface.md` 9.1/3.1 nennt die Wiedermeldung (gleiche Vorgangs-ID) ein No-op „ohne Melden“. `learn` führt dazu die Vorgangs-ID des liegenden Tobies (Feld `liegt`) und ignoriert eine Wiedermeldung; ein erneutes Auflegen nach Abheben (neue ID) zählt. Tests in `test_learn.py`, `test_cuj07b_lernmodus.py`, `test_cuj07b_app.py`.
10. **Teils behoben, Rest begründet.**
    - Behoben: 201. Eintrag verwirft nie den neuen (`Outbox.melden` gibt den Eintrag zurück, `app._melde` braucht kein `next`); CLI trennt „keine Berechtigung“ (Exit-Code 4) von „nicht erreichbar“ (3); Socket ohne `umask`: binden, `chmod 0600`, erst dann lauschen.
    - Behoben, weil Vertragsverstoß: `Bestaetigt` geht nicht mehr an den Kern (`core-interface.md` 3), nur an die Outbox.
    - Nicht geändert, begründet: `sim card` erhöht die Revision lokal. Das ist Stufe-2-Ersatz für HA und wird mit Stufe 3a ersetzt; kein Vertrag verlangt anderes. Vor 3a klären, ob `sim` im Pi-Betrieb abgeschaltet wird.
    - Nicht geändert, begründet: Die Bibliothek vom Start im Prüfpunkt Medien. 12.3 verlangt „Ordner lesbar“ (neu geprüft mit `os.access`) und eine Bibliothek mit Serie und Überraschung; die Neu-Ladung kommt mit dem Sync (Stufe 3a).
11. **Behoben.** `test_ungueltige_zeile_wird_ignoriert` prüft die Protokollzeile. Die Verdrahtung steht in `ausgang.py` und wird von `App` und `SimBox` gemeinsam benutzt. Dazu `tests/cuj/test_cuj07b_app.py`: Lernmodus (Frist, Abbruch, zweiter Befehl, Wiedermeldung, bestehende Zuordnung, `sim=true`, 201. Eintrag) gegen die echte `App`.
12. **Behoben.** `test_app_abheben_pausiert_mpd_und_protokolliert_die_kette` wartet auf Zustand (Leser gemeldet, 2,5 s gespielt, MPD pausiert, Zeiger gespeichert) statt auf feste Zeiten. Die Grenze „unter 1 s von REMOVED bis MPD pausiert“ bleibt und wird an den `mono`-Zeiten der Protokollzeilen des Dienstes gemessen, nicht an Abfragen des Tests.
13. **Behoben.** `selftest.messe` sammelt Medien und freien Platz an einer Stelle (ohne Austausch der Log-Handler: `lade_bibliothek(leise=True)`); `selftest.pruefe`, `App.pruefbericht`/`status_auskunft` und `cli.sammle_status` benutzen sie. Tests in `test_selftest.py`, `test_cli.py`.
