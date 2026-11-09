# Code-Review zu den Entscheidungen I, J und L

Stand: Commit `c1e1549` (HEAD) gegen `a037ae7`. Geprüft: `box/src/tobibox/` (`app.py`, `sounds.py`,
`player.py`, `config.py`, `selftest.py`, `session.py`, `core.py`, `audiodauer.py`) gegen
`docs/designs/box-software.md` (I, J, L) und `docs/protocol/core-interface.md` (6.3, 6.5 Punkt 6, 8.1,
Festlegungen 30 bis 32). Reviewer ohne Vorwissen. Im Repo wurde nichts geändert außer dieser Datei.

Lauf der Tests: `pytest -q tests/unit tests/cuj` ist grün. `tests/integration/test_toene_mpd.py` ist grün
(5 Tests, echtes MPD). Die Wegwerf-Skripte der Belege liegen in
`/tmp/claude-0/-home-user-Tobi-box/87837eca-ee4b-54f9-bcf7-9cb39d3c88c0/scratchpad/rvJL/`.

## Befunde

### B1 (Hoch, aber enges Zeitfenster): Ein Hörspiel kann nach dem Abheben von selbst weiterspielen

- **Datei:** `box/src/tobibox/player.py`, Zeilen 217 (`pausieren`), 233 (`ton_pause_beginn`), 426 bis 454 (`_pausieren`).
- **Szenario:** Ein Hörspiel läuft. Eine Tonfolge beginnt (zum Beispiel `hinweis`). Die Tonspur ruft
  `ton_pause_beginn` auf und wartet auf die Sperre des Players (die Abfrageschleife hält sie alle 0,2 s
  kurz; `abspielen` hält sie bis zu 5 s). In diesem Fenster kommt ein echtes `Pausieren` (Abheben,
  Hauptknopf). `pausieren()` löscht `_ton_pause` **vor** der Sperre (Zeile 217). `ton_pause_beginn`
  bekommt die Sperre zuerst und setzt `_ton_pause = True` **danach** (Zeile 233). Danach läuft
  `_pausieren()`; es lässt das Flag stehen. Der Kern steht auf `pausiert`. Am Ende des Tons ruft
  `_ton_nach` → `ton_pause_ende` auf, sieht `_ton_pause == True`, MPD ist auf „pause“, und setzt mit
  `pause 0` fort. Das Hörspiel läuft, obwohl das Kind den Tobie abgehoben hat (verletzt Entscheidungen
  A und B und die Zusage in 6.5 Punkt 6e: „Kommt in dieser Zeit ein echtes Pausieren …, wird nichts fortgesetzt“).
- **Beleg:** `.../rvJL/tonrace.py` mit echtem MPD und echtem `Player`. Ausgabe:
  `1 nach Start: play`, `2 nach Ton-Pause + Abheben: pause | _ton_pause = True`,
  `3 nach Ende des Tons: play (Kern glaubt: pausiert)`.
  Die Tests in `test_app_toene.py` nutzen einen `AufnahmePlayer`, der dieses Flag ohne Sperre und ohne
  Reihenfolge nachbildet. Der Fehler fällt dort nicht auf.
- **Wie wahrscheinlich:** Das Fenster ist ein paar Millisekunden groß (Dauer von `status` und `pause 1`
  plus Wartezeit auf die Sperre). Ein Mensch trifft es kaum; ein prellender Leser (Auflegen und gleich
  Abheben) oder ein Takt-Ereignis kann es treffen.
- **Vorschlag:** Das Flag erst **unter der Sperre** löschen: in `_pausieren()` und in `abspielen()` direkt
  nach `async with self._lock`. Oder ein Zähler `_ton_epoche`: `pausieren` und `abspielen` erhöhen ihn,
  `ton_pause_beginn` merkt ihn sich vor dem Warten und setzt das Flag nur, wenn er gleich geblieben ist.
  Dazu einen Integrationstest mit echtem `Player` und gehaltener Sperre (wie `tonrace.py`).

### B2 (Mittel): Nach einem „stumm“-Ausblenden sind Töne praktisch unhörbar, bis das nächste Hörspiel startet

- **Datei:** `box/src/tobibox/app.py`, Zeilen 235 bis 238 und 252 bis 253; Ursache liegt in
  `box/src/tobibox/core.py` (Regel 7, „zurückgehalten“) und `box/src/tobibox/sounds.py` Zeile 67.
- **Szenario:** Stumm beginnt, das Hörspiel blendet in 3 s aus. Die Grenze „ausblenden“ senkt dabei
  `grenze` mit der Lautstärke (letzter Befehl: `LautstaerkeSetzen(1, 1)`). Am Ende wird die Grenze
  gelöscht und `Pausieren` ausgegeben. Der Kern hält den Anstieg zurück (Regel 7), also kommt kein neuer
  `LautstaerkeSetzen`. `App.grenze` und `App.lautstaerke` bleiben bei 1. Jeder Ton ohne `Abspielen`
  (Status-Karte, `fehler`, `lernen_beginn`, `akku_leer`) bekommt `pegel = min(grenze=1, max(10, 1)) = 1`
  und ist nicht zu hören. Der Vertrag (8.1) sagt aber ausdrücklich: „die Untergrenze 10 hält ihn hörbar
  (z. B. bei Lautstärke 0 nach einem Ausblenden)“. Die Untergrenze wirkt hier nicht, weil die Rampe auch die
  `grenze` mitgezogen hat. Nur `hinweis` bleibt hörbar (er ignoriert die Grenze).
- **Beleg:** `.../rvJL/fade.py` (echter Kern, Nachbildung der Nachführung in `app.py`). Ausgabe nach dem
  Ausblenden: `modus pausiert`, `app.laut 1 app.grenze 1`, `Pegel fuer Statuston: 1`, Soll bei Lautstärke 40: 40.
  Im Test `test_app.py` wird `LautstaerkeSetzen` nur von Hand gefüttert; der Weg Kern → App ist nicht getestet.
- **Wie erreichbar:** Heute nur über `StummBeginnt` aus der Simulation. Die Teilautomaten `quiet` und
  `bedtime` fehlen noch in `TEILAUTOMATEN`. Mit ihnen (Ruhezeit, Gute Nacht) wird es zum echten Fall.
- **Vorschlag:** Für Töne die **dauerhafte** Grenze nehmen (ohne die Rampe „ausblenden“ und ohne
  zurückgehaltene Anstiege), zum Beispiel die letzte Lautstärke vor dem Ausblenden oder die Grenze aus
  `kern.grenzen` ohne `ausblenden`/`gute_nacht`. Oder im Vertrag festhalten, dass Töne nach dem Ausblenden
  leise sind, und die Untergrenze für die Prüftöne anders regeln. Dazu einen Test mit echtem Kern.

### B3 (Mittel, geringe Wahrscheinlichkeit): Stirbt die Tonspur an einer unerwarteten Ausnahme, friert der Dienst ein und MPD bleibt pausiert

- **Datei:** `box/src/tobibox/sounds.py`, Zeilen 299 bis 311 (`_arbeit`), 313 bis 324 (`_lauf`), 326 bis 329 (`warte_leer`).
- **Szenario:** `_lauf` fängt nur `TimeoutError`, `FileNotFoundError` und `OSError`. Wirft das Starten des
  Programms etwas anderes (zum Beispiel `ValueError`, `RuntimeError`, `SubprocessError`), endet `_arbeit`
  ohne den Haken `nach`. `finally` setzt `_arbeiter = None` und `_leer.set()`, lässt aber weitere Einträge in
  `_eintraege` stehen. Folgen:
  1. `ton_pause_ende` wird nie aufgerufen: MPD bleibt für den Ton angehalten, `_ton_pause` bleibt `True`,
     der Player meldet keine Position mehr, der Kern glaubt „spielt“ (dauerhaft stumm, ohne Fehlermeldung).
  2. Bei einer Folge von mindestens zwei Tönen (Status-Karte) bleibt `beschaeftigt == True` bei gesetztem
     `_leer`. `warte_leer` (und damit `_start_nach_toenen`) dreht in einer Schleife ohne `await`, die den
     ganzen Event-Loop blockiert.
- **Beleg:** `.../rvJL/tod.py`: Ausgabe `journal ['vor'] beschaeftigt True leer.is_set True eintraege 1`, danach
  hängt der Lauf, bis `timeout` ihn beendet (Rückgabe 124; auch `asyncio.wait_for` löst nicht aus).
- **Vorschlag:** In `_lauf` `except Exception` ergänzen (CancelledError durchlassen). In `_arbeit` den Haken
  `nach` in ein `try/finally` legen. In `warte_leer` nach `self._leer.wait()` bei gesetztem Ereignis und
  `beschaeftigt` ein `await asyncio.sleep(0)` oder besser: `_leer` im `finally` nur setzen, wenn
  `_eintraege` leer ist, sonst die Einträge verwerfen.

### B4 (Niedrig): `Pausieren` ist wirkungslos, solange der allererste Start nach dem Dienststart die Sperre noch nicht hat

- **Datei:** `box/src/tobibox/player.py` Zeile 218; `box/src/tobibox/app.py` Zeilen 330 bis 337 (Kommentar „der Player ordnet ihn vor“).
- **Szenario:** Ein schon laufender `_Start` ruft `player.abspielen` auf und wartet auf die Sperre
  (Abfrage hält sie gerade). `_serie` wird erst **unter** der Sperre gesetzt. Kommt in diesem Moment das
  `Pausieren` des Ausführers, ist `_serie is None` (nur beim ersten Hörspiel nach dem Dienststart), und
  `pausieren` kehrt sofort zurück, ohne zu pausieren. Der Start läuft danach durch, MPD spielt, der Kern
  steht auf `pausiert`. Vor Entscheidung L war das nicht möglich, weil der Ausführer den Start selbst
  ausführte. Spätere Starts sind nicht betroffen (`_serie` ist dann gesetzt, die Sperre ist eine FIFO-Schlange).
- **Beleg:** `.../rvJL/pausrace.py` (Sperre gehalten, `abspielen` und `pausieren` nacheinander): `MPD state: play`.
- **Vorschlag:** In `pausieren` die Prüfung `self._serie is None` erst unter der Sperre machen (oder ganz
  weglassen: `_pausieren` fragt MPD ohnehin ab). Der Rückgabe-Zweig `not self._verbunden` kann bleiben.

### B5 (Niedrig): Ein Rest des Flags `_ton_pause` überlebt einen Verbindungsverlust

- **Datei:** `box/src/tobibox/player.py`, Zeilen 532 bis 539 (`_verbindung_weg`) und 245 bis 271 (`ton_pause_ende`).
- **Szenario:** MPD fällt während einer Tonfolge aus und ist wieder da, bevor der Ton zu Ende ist. `_verbinde`
  pausiert MPD (Sicherheitsregel „nichts spielt von selbst“). `_verbindung_weg` löscht `_ton_pause` nicht.
  Entsteht daraus kein neues `Abspielen` (Kern in `unbekannt`, oder `_leser_zurueck` mit `mpd_verloren`, beides
  ohne `Pausieren`), setzt `ton_pause_ende` MPD mit `pause 0` fort. Der Player steht auf Phase „aus“, und MPD
  spielt ungemeldet. Dasselbe gilt, wenn `_klemme` (Lautstärke über der Grenze nicht setzbar) MPD
  pausiert hat: `ton_pause_ende` prüft die Phase nicht und setzt trotzdem fort.
- **Vorschlag:** `_ton_pause = False` in `_trenne()`/`_verbindung_weg()` und in `_klemme()`; in
  `ton_pause_ende` zusätzlich `self._phase == "spielt"` verlangen.

### B6 (Niedrig): Töne werden mit der Lautstärke von **vor** dem Warten gerechnet

- **Datei:** `box/src/tobibox/sounds.py`, Zeilen 233 bis 252 und 274 bis 287; `box/src/tobibox/app.py` Zeilen 252 bis 253 und 372.
- **Szenario:** Pegel und Skalierung entstehen beim Einreihen (`kommando_fuer`). Die Tonfolge der
  Status-Karte (4 Töne) oder ein Ton hinter einem hängenden Ton läuft erst Sekunden später. Wird in der
  Zwischenzeit ein Kopfhörer gesteckt (Grenze sinkt) oder leiser gedreht, spielen die wartenden Töne noch mit
  der alten, höheren Lautstärke und sind lauter als erlaubt. Auf dem Pi gilt zwar die harte Kappe
  (`max_dB`) des zweiten `softvol`-Geräts, aber nicht die Kopfhörer-Grenze.
- **Vorschlag:** Pegel erst beim Abspielen berechnen (Rückruf an `App` für `grenze`/`lautstaerke`), oder
  die Skalierung in `_arbeit` kurz vor dem Start des Programms machen.

### B7 (Niedrig): Der Hinweiston ignoriert die Grenze, wenn sie unter 10 liegt

- **Datei:** `box/src/tobibox/sounds.py`, Zeilen 64 bis 66.
- **Szenario:** `pegel("hinweis", grenze, …) = max(10, min(hinweis_pegel, lautstaerke))` kennt `grenze` nur über
  `lautstaerke`. Ist die Kopfhörer-Grenze 5, spielt der Hinweiston mit 10 (rund 7 dB lauter als erlaubt).
  `data-model.md` schreibt für `hinweis_pegel` ausdrücklich „die wirksame Grenze gilt weiter“; 8.1 sagt „übersteigt
  sie [die Lautstärke] nur durch die Untergrenze“. Das sind zwei verschiedene Aussagen. Der Test
  `test_pegel_regel_gilt_fuer_alle_werte` prüft nur `h <= max(laut, 10)`, nie `h <= grenze`.
- **Vorschlag:** Entscheiden (Tobias): Hinweiston unter „stumm“ darf über die Grenze (dann in `data-model.md`
  streichen und Kopfhörer-Grenze mindestens 10 verlangen), oder `min(grenze, …)` wie bei den anderen Tönen.

### B8 (Niedrig): Ein Ton kann zwischen Start-Vorbereitung und Wiedergabe überlappen

- **Datei:** `box/src/tobibox/player.py` Zeilen 225 und 228 (`ton_pause_beginn` prüft `_phase`).
- **Szenario:** Während `abspielen` läuft (Phase „aus“; bis zu 5 s bei `_aktualisiere`), beginnt eine Tonfolge.
  `ton_pause_beginn` sieht Phase „aus“ und tut nichts. Die Tonfolge läuft, MPD startet danach (`play`) und das
  Hörspiel überlagert den Rest des Tons. Gleiches Muster in Gegenrichtung: Während `_nach` MPD fortsetzt
  und ein neuer Ton eingereiht wird, entsteht ein kurzes Aufblitzen (`pause 0`, gleich wieder `pause 1`);
  und ein `Abspielen`, das genau in `_nach` ankommt, lässt das alte Hörspiel kurz fortsetzen, bevor es ersetzt wird.
- **Vorschlag:** Wenig Aufwand, wenig Nutzen. Mindestens in 6.5 Punkt 6e als bekannte Grenze notieren.

### B9 (Niedrig): MP3 ohne Xing-Kopf und mit wechselnder Bitrate gibt eine falsche, aber „bekannte“ Dauer

- **Datei:** `box/src/tobibox/audiodauer.py` Zeile 87; Wirkung in `box/src/tobibox/session.py` Zeilen 174 bis 177.
- **Szenario:** Ohne Xing/Info rechnet die Box mit der Bitrate der ersten Frame. Bei VBR ohne Kopf ist die
  Schätzung beliebig falsch. Ist sie zu klein, ist `rest` schon mitten in der Folge kleiner als 15 s oder
  negativ; die Folge gilt als „fertig gehört“, und es spielt die nächste. Kein Fall für „Dauer unbekannt“.
- **Beleg:** Testdatei mit `ffmpeg … -write_xing 0` (20 s Rauschen, danach Sinus; echt 120 s): Schätzung 18,2 s.
  Mit Xing-Kopf: 120,03 s. Realistisch sind VBR-Dateien ohne Kopf selten (LAME, ffmpeg und iTunes schreiben ihn).
- **Vorschlag:** Die Regel nur anwenden, wenn `zeiger.position_s` höchstens die Trackdauer plus Toleranz
  (zum Beispiel 2 s) ist; sonst wie „Dauer unbekannt“ behandeln (`rest_regel`/`dauer_unbekannt` protokollieren).
  Optional: MP3 ohne Kopf als „unbekannt“ (`None`) melden, wenn die ersten Frames unterschiedliche Bitraten zeigen.

## Lücken in den Tests

- `tests/unit/test_app_toene.py` ersetzt den `Player` durch `AufnahmePlayer`. Der bildet Sperre, Reihenfolge
  der Aufrufe und das Flag `_ton_pause` nicht nach. Genau diese Teile enthalten B1, B4, B5. Die Integrationstests
  (`test_toene_mpd.py`) haben kein Fenster-Szenario (Abheben im Moment des Tonbeginns), keinen MPD-Neustart
  während eines Tons, keinen Tobie-Wechsel mit echtem MPD und kein `stop()` mitten im Ton.
- `test_veralteter_start_wird_vor_dem_start_geprueft` ruft `_start_gueltig` direkt auf und biegt den Kern
  um. Der Fall `gen_veraltet` kommt im Betrieb nicht vor, weil ein neueres `Abspielen` den alten `_Start`
  immer ersetzt. Der Test ist nicht falsch, aber er belegt nur die Funktion, nicht das Verhalten.
- `test_app.py` (Lautstärke der Töne) füttert `LautstaerkeSetzen` von Hand. Nichts prüft, dass der Kern bei
  Kopfhörer, Ausblenden und zurückgehaltenem Anstieg die Werte liefert, die `App` für die Töne braucht (B2).
- `test_pegel_regel_gilt_fuer_alle_werte` schützt für `hinweis` nur die Obergrenze `max(laut, 10)`, nicht die
  Grenze (B7).
- `test_festgehaltener_wert_liegt_am_zielwert` (Lautheit) prüft ohne `ffmpeg` nur, was das Werkzeug selbst
  aufgeschrieben hat (Prüfsumme plus Wert). Mit `ffmpeg` (hier vorhanden) misst `test_gemessene_lautheit_…`
  tatsächlich: alle 36 Dateien liegen zwischen −18,77 und −17,95 LUFS. Keine Lücke, solange CI `ffmpeg` hat.

## Geprüft, ohne Befund

- **Kennlinie Mac gegen echtes MPD:** Mit `mpd 0.23.14` (Software-Mixer, Ausgang `fifo`) die Verstärkung bei
  10, 20, 40, 50 und 70 % gemessen: 0,00895 / 0,0226 / 0,0743 / 0,11925 / 0,2882 gegen Kennlinie
  0,00879 / 0,02246 / 0,07422 / 0,11914 / 0,28809. Abweichung unter dem Messfehler. (Skript `mpclient.py`.)
- **Kennlinie Pi:** Formel und Randfall `bereich <= 24` gegen den Vertragstext und die Beispielwerte
  (−30,3 dB bei 20 %, −18,9 dB bei 40 %) nachgerechnet. Am Gerät nicht prüfbar (Pi-Probelauf steht aus, wie im Vertrag vermerkt).
- **Nachführung von `App.lautstaerke`/`grenze`:** Alle Änderungen laufen über genau einen Befehl
  (`LautstaerkeSetzen`, einziger Schreibzugriff in `_fuehre_aus`); Klemmung wie im Player; Kopfhörer, Maximum,
  Ruhezeit und Gute Nacht kommen als Grenzen im Kern an. Einzige Auffälligkeit: B2.
- **Reihenfolge Ton vor Hörspiel:** `_toene_vor_start` ordnet nur Töne um, Rang des Kerns bleibt für alles
  andere; Fälle `unbekannt`, `lernen_ende`, Status-Karte, Startton, mehrere Töne aus mehreren Ausgaben.
- **Verzögerter Start:** `_abspielen`/`_verwirf_start`/`_start_gueltig`: kein `await` zwischen Prüfung und
  Aufruf des Players; `Pausieren`, neuer Start, Abheben, Hauptknopf, Weiter/Zurück ersetzen oder verwerfen
  ihn; laufender Start bleibt (bis auf B4). Normalweg ohne Ton ohne Umweg und ohne Aufgabe.
- **`warte_leer` mit nachträglich eingereihten Tönen:** Die Schleife prüft nach dem Aufwachen erneut; kein
  Verlust des Wartens, wenn zwischen `set` und Aufwachen ein neuer Ton kommt.
- **`stop()` mitten im Ton:** Programm wird beendet (kill, dann `wait`), temporäre Dateien werden gelöscht,
  Haken laufen nach `stop` nicht mehr (`_beendet`), `pausiere_hart` setzt `_ton_pause` zurück, MPD bleibt
  pausiert. Wartender Start wird in `_raeume_auf` abgebrochen. `beende()` lässt den Ton nicht zu Ende laufen
  (gewollt: „beim Beenden setzt nichts fort“).
- **Dienst-Ende mit wartendem Start:** `DienstEndet` → `Pausieren` verwirft den Start; Zeiger wird gesichert.
- **MPD-Ausfall und Wiederverbindung im Normalfall:** Innerhalb der Frist ersetzt das neue `Abspielen` den
  Start, `_ton_nach` setzt dann nicht fort; nach der Frist verwirft `Pausieren("fehler")` den Start.
- **Ton-Pause und Zeigerspeicherung:** Der Kern bekommt während der Ton-Pause keine Position; der gespeicherte
  Zeiger ist nie weiter als die tatsächliche Stelle, die 30-s-Speicherung schreibt dieselbe Position
  (`unveraendert`), kein Rücksprung, kein Status „pausiert“.
- **Tonfolge pausiert nur einmal** (bis auf die Randfälle in B8). Hörspiel-Ende genau beim Ton-Beginn:
  `ton_pause_beginn` prüft `state == play` und fängt `CommandError`.
- **Hängender Ton:** `TON_MAX_S` wird erzwungen, Programm wird beendet, `_leer` wird gesetzt.
- **Restregel (`session._rest_regel`):** Grenzen genau 15 s und genau 60 s, Messung am Zeiger vor dem
  Rücksprung, Rest über alle Tracks, Folgen-Zeiger („von vorn“), Serien-Zeiger („nächste Folge“, danach
  Folge 1), Überraschungs-Serie, einelementige Serie, unbekannte Dauer, fehlende Folge/Track, Dienst-Neustart
  (G) und Lernmodus (H). Die Tests in `test_session_restregel.py` decken diese Fälle ab. Einzige Sorge: B9.
- **`audiodauer.py`:** WAV, FLAC (STREAMINFO-Bitfelder), MP4/M4B (`mvhd`), MP3 mit Xing/Info (MPEG-1/2, mono/stereo,
  Versatz) und CBR ohne Kopf nachgerechnet; Xing-Datei: 120,03 s gegen echt 120,0 s. Unbekannte Formate (Opus, Ogg) geben `None`.
- **`config.py`:** `kennlinie` und `softvol_bereich_db` werden geprüft (Bool, Bereich 1 bis 120, nur bekannte Namen).
- **`selftest.py`/Prüftöne:** Namensbildung `pruef_<punkt>_<ok|fehler>`, `pruef_leser_simulation` und der
  Rückfall auf `pruef_ok`/`pruef_fehler` sind stimmig und getestet.
- **Skalierung der Töne:** `skaliere_wav` rundet und klemmt auf 16 Bit; Dauer je Datei hier höchstens 16 ms
  (auf dem Pi 3A+ grob das 10- bis 15-fache, also unter 0,3 s; blockiert den Event-Loop kurz, ohne Befund).
- **Lautheit der Töne und Testmedien:** `pytest tests/unit/test_lautheit.py` mit echtem `ffmpeg`: 90 Tests grün.
