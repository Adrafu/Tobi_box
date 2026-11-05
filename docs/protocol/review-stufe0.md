# Goldfisch-Review der Stufe-0-Verträge

**Prüfer:** frischer Agent (Sonnet) · **Datum:** 2026-11-05

REVIEW Stufe-0-Verträge (Modus REVIEW, Implementation Readiness)

Gesamturteil: Zwei unabhängige Agenten würden NICHT beim ersten Versuch zusammenpassen. Die Firmware/Parser-Seite (reader-v1 plus Beispieldatei) ist weitgehend tragfähig. Die Kern-Schnittstelle hat Entscheidungslücken, die der Implementierer treffen müsste. Zwei davon betreffen die Kinderohren oder das Verhalten der Box.

Hinweis: Ich habe die vom Drafter gelisteten Widersprüche (seq auf HB/ERR/HELLO, „gelernt“-Thema, `…/ui/…`, Listen-ID nach Restore, Tabellenzeilen in core-interface §9) nicht erneut als Befunde geführt. Die Auflösungen sind in sich stimmig. Offen bleiben die Folgen davon, siehe Befunde 3, 8 und die Tobias-Liste.

Nachgerechnet:
- Entprellertabelle: lückenlos für N≥2 und N=1. Die Zeilen 13/14/15 decken alle Fälle ab. Keine Lücke und kein Widerspruch.
- Zeitabläufe, alle von Hand nachgerechnet und stimmig (Schritt 0 vor Eingabe; Zähler `polls`/`hits`/`rejected`/`errors`; seq-Vergabe):
  - auflegen-und-abheben: REMOVED bei 2000, Lücke 1200 ≥ 1100.
  - luecke-1000: Lücke 1000 < 1100, daher kein REMOVED.
  - luecke-1200: REMOVED bei 1400, PLACED bei 1600.
  - kandidat-verfaelscht: rejected=2.
  - rand-flip: rejected=3.
  - figurwechsel, wechsel-karte-zu-tonie und die beiden gesperrt-Wechsel: rejected=2.
  - fehler-dauerhaft: REMOVED bei 1400, errors=6.
  - err-ratenbegrenzung: die dritte ERR-Zeile erscheint bei genau 2000, also gilt „≥ 2000“.
  - ping-resync: REMOVED seq=1 bei 1800.
  - zeit-ueberlauf: 4294967096 → 0, Differenz bei t=1000 ist 1200, REMOVED passt.
- Referenz `firmware/tonie_test/`: `storeVicinityUid`, `COMMAND_TIMEOUT_MS`=30 und das Präfix `e00403` stimmen mit den Verträgen überein.
- Kennungs-Regex: `fullmatch` auf `[0-9a-f]{8}|{14}|{20}|{16}` ist eindeutig. Die Länge 16 gehört nie zu `ntag`, die Typ-Zusatzprüfung greift. Die Beispiele (`bad_uid` / `uid_type_mismatch`) sind korrekt eingeordnet.

BEFUNDE

1. **Blocker** – core-interface.md §3.9, §5.1, §6.1, §8, §9.5, §9.6 (Rampen).
   - `quiet`, `session` und `bedtime` sollen `GrenzeGesetzt(name, rampe(von, nach, start, dauer, jetzt))` bei jedem Takt ausgeben.
   - `step(zustand, ereignis, jetzt)` gibt den Teilautomaten weder `wunsch` noch `grenzen` noch die wirksame Lautstärke. Das hält nur `core` (`KernZustand`).
   - Der Startwert „wirksame Lautstärke zu Beginn des Ausblendens“ (§8) ist daher für `bedtime` nicht ermittelbar. Dasselbe gilt für die Entscheidung „laute Wiedergabe“ beim Absenken in `quiet`.
   - Empfehlung: ein Ereignis `LautstaerkeGeaendert(wirksam: int)` an alle Teilautomaten, oder das Feld `wirksame_lautstaerke` in `Jetzt`. Alternativ ein Befehl `Rampe` an `core`, der den Startwert selbst einsetzt.

2. **Major** (Kinderohren, Ziel 10) – core-interface.md §6.4 zusammen mit §9.5 und §9.6.
   - Am Ende von „Gute Nacht“ und „stumm“ wird die Grenze gelöscht (`GrenzeGesetzt(…, None)`) und zugleich `Pausieren` ausgegeben.
   - Der feste Rang setzt `LautstaerkeSetzen` (Rang 1) vor `Pausieren` (Rang 3). Die Box springt kurz auf die volle Lautstärke zurück, bevor die Pause greift.
   - Empfehlung: die Rücksetzung des Werts hinter `Pausieren` legen, oder die Rücksetzung weglassen, weil §6.2 Regel 6 vor jedem `Abspielen` ohnehin setzt. Zusätzlich festlegen, ob `LautstaerkeSetzen` nach jedem `GrenzeGesetzt` oder erst am Ende der Verarbeitung entsteht (Nettowert).

3. **Major** (Kind-/Elternerlebnis) – core-interface.md §9.1 im Zusammenspiel mit reader-v1 §8 (PING-Wiedermeldung), Entscheidungen A/B und Hauptknopf-Pause.
   - `LeserHallo`/`LeserAlarm` in `pausiert`, `beendet` und `gehalten` gelten als `Abgehoben` (Zustand `pausiert`). Danach meldet die Firmware die liegende Figur erneut als `PLACED seq=0`, nach `PING` oder USB-Wiederverbindung. Das ist dann ein normales Auflegen und startet die Wiedergabe von selbst.
   - Das bricht Entscheidung A (nach der Folge Pause, bis neu aufgelegt wird) und Entscheidung B (nach „stumm“ startet nichts). Es lässt auch eine per Hauptknopf pausierte Figur wieder anspielen.
   - Empfehlung: In diesen Zuständen ändert `LeserHallo`/`LeserAlarm` nichts. Ein `Aufgelegt` mit derselben Kennung wie die liegende Figur ist dort ein No-op, außer es folgte vorher ein `Abgehoben`. Dazu muss `reader` für eine Wiedermeldung derselben Kennung nach `HELLO` die bestehende Vorgangs-ID behalten.
   - Aktuell steht in §3.1 „neue ID bei PLACED nach REMOVED“, aber Wiedermeldungen sind nicht geregelt. Zugleich steht dort „`vorgang=None` direkt nach HELLO“, obwohl `PING` sofort ein `PLACED` liefert. Das ist widersprüchlich.

4. **Major** – core-interface.md §2 und §11 (`TAKT_S`=0,5, `LESER_FRIST_S`=1,5) im Zusammenspiel mit reader-v1 §12 (Backoff 1 s) und CUJ 13.
   - Fristen lösen erst beim ersten Takt ≥ Frist aus. Die Pause liegt damit bis zu 2,0 s nach dem Alarm (plus Pausenbefehl), nicht ≤ 1,5 s wie in CUJ 13 und im Design.
   - Der erste Wiederverbindungsversuch kommt nach 1 s Backoff. Dazu kommen Öffnen, `PING` und `HELLO`. Die Frist von 1,5 s läuft bei einem USB-Aussetzer meist ab. Dann pausiert die Box und startet mit 3 s Rücksprung neu, entgegen „läuft weiter, ohne neu zu starten“.
   - Fades mit 0,5-s-Takt ergeben bei 3 s nur 6 Lautstärke-Stufen.
   - Empfehlung: Takt 0,1 s oder fristgenauer Zeitgeber; erster Backoff z. B. 0,25 s; das Verhältnis Frist/Reconnect festschreiben.

5. **Major** – core-interface.md §4 (`ZustandMelden`) im Zusammenspiel mit mqtt-v1.md §3.3 (Status) und reader-v1.md §7.
   - Das Status-JSON braucht `akku_prozent`, `lader`, `netz`, `sync`, `speicher_frei_mb`, `leser`, `letzter_fehler`, `serie.name`, `konfig`, `update`, `version`, `firmware`.
   - `ZustandMelden` trägt nur sitzung, serie_id, lernmodus, ruhe, gute_nacht, figur_liegt. Nirgends steht, wer den Status zusammenbaut und woher diese Werte kommen.
   - Die Abbildung der Leser-Zustände auf `leser` ∈ {ok, fehler, getrennt, simulation} fehlt. reader-v1 §7 kennt nur „Fehler innerhalb 10 s“. Offen: wann `getrennt`, wann `fehler` bei `proto_unbekannt`, und wer den 10-s-Zähler hält. `LeserFehler` steht in der Tabelle der Sitzung, ohne dass sie damit etwas tut.
   - Kriterien der Prüfpunkte Medien, Netz und Speicher (CUJ 11, `StatusPruefen`) sind in den fünf Dokumenten nicht definiert. Zwei Ausführer (`selftest` und `sounds`) für einen Befehl sind unklar verteilt.
   - Empfehlung: Abschnitt „Statusaufbau“ mit Quelle je Feld und eine Tabelle der Prüfpunkt-Kriterien.

6. **Major** (Elternerlebnis) – core-interface.md §9.12 und §9.14.
   - `Hauptknopf kurz`, `Weiter` und `Zurueck` sind in `stumm` nicht geregelt. Nachts im „stumm“-Fenster würde `Abspielen` die Box zum Spielen bringen, entgegen CUJ 15. Das Gleiche gilt für den Wechsel nach `KonfigGeladen` (§9.14).
   - §9.14 gilt nur im Zustand `spielt`. In `beendet` und `pausiert` mit liegender, gerade zugeordneter Figur passiert nichts, obwohl CUJ 7a „wechselt sofort“ sagt.
   - Empfehlung: `stumm` gilt für alle `Abspielen`-Auslöser (Hinweiston statt Wiedergabe). Für §9.14 die Zustände `beendet` und `pausiert` ausdrücklich regeln.

7. **Major** – Zuständigkeit für Befehls- und Listenprüfung, core-interface.md §3.4 und §9.9 gegen mqtt-v1.md §3.4 und §3.7.
   - mqtt-v1 sagt „die Box prüft“ Ablaufzeit und Uhr. core §9.9 sagt „der Kern prüft“.
   - `HaLernmodusAbbruch` hat kein `gueltig_bis`, die `cmd` hat aber `ttl_s`. Gilt für den Abbruch eine Ablaufzeit und eine `zeit_ok`-Sperre?
   - Die Aufzählung `befehl_abgelehnt` kennt `lernen_abbrechen` nicht (mqtt-v1 `befehl` ∈ lernen/sync/update).
   - `EreignisSenden.art` kennt `liste_abgelehnt` nicht. Es fehlt, wer `liste_abgelehnt`, `v_unbekannt` und `befehl_unbekannt` veröffentlicht. Vermutlich `ha`/`store` direkt, die Revisionsregel liegt außerhalb des Kerns, aber das steht nirgends.
   - Empfehlung: Spalte „prüft“ je Prüfung (Schema, Revision, Ablaufzeit, ID-Dedup, Uhr) mit Modul.

8. **Major** – mqtt-v1.md §3.5/§3.6/§4.1 und data-model.md §4 (Bestätigung).
   - `ack` wird nur über `uid` zugeordnet, aber `unknown.json` überschreibt Einträge (`anzahl`, `gelernt` ersetzt `unbekannt`). Eine verspätete `ack` für die ältere Veröffentlichung löscht den neueren Eintrag, bei `gelernt` damit auch die Zuordnung.
   - Empfehlung: `ack` trägt `zuletzt` oder `befehl_id`; die Box löscht nur bei Übereinstimmung.
   - Die HA-Integration muss die leere retained Nachricht (Box löscht) auf `…/unknown/<uid>` ignorieren. Das steht nicht im Vertrag.
   - Offen für die HA-Seite: `lern_serie` (Auswahl) gegen die Aktion „Lernmodus starten (Box und Serie)“. Welche Serie gilt? Die Auswahl enthält nur Serien, die die Box schon synchronisiert hat.

9. **Major** – data-model.md §5 (Serien und Reihenfolge).
   - „Natürliche Sortierung der Dateinamen“ wird von Box (`library`, Ordner ohne `serie.json`) und HA-Integration (neuer Ordner) benutzt. Algorithmus (Groß-/Kleinschreibung, Ziffernblöcke, Gleichstand) fehlt, die zwei Seiten können abweichen. Das ändert die Folgenreihenfolge.
   - Ordner ohne `serie.json` haben die ID = Ordnername. Legt HA später `serie.json` mit neuer Zufalls-ID an, gehen Zeiger (`resume.json`) und Zuordnungen verloren.
   - Empfehlung: Sortieralgorithmus festschreiben. HA übernimmt beim Anlegen die Ordner-ID oder migriert den Zeiger.

10. **Major** – reader-v1.md §12 Schritt 3, §6 und core-interface.md §3.1 (`LeserAlarm`).
    - Schritt 3 sagt „Alarm mit Grund `proto_unbekannt`, keine Ereignisse an den Kern“. `LeserAlarm` ist aber ein Ereignis an den Kern. Gemeint ist vermutlich „kein `LeserHallo`“. Das entscheidet, ob die Wiedergabe pausiert.
    - Die Grund-Strings `kein_herzschlag` und `getrennt` stehen nur in core-interface, nicht in reader-v1.
    - §6 verweist für das Neuverbinden auf „Abschnitt 10“, richtig ist 12.
    - Wiederholte Alarme beim Backoff (je Versuch einer): Verhalten soll ausdrücklich sein.

11. **Major** – reader-v1.md §2, §11, §13 und Beispieldatei (Parser).
    - §13 erlaubt neue Zusatzfelder „am Ende“. Bei `ERR` ist `detail=` Rest der Zeile, ein Feld dahinter wird Teil von `detail`. Neue Felder müssten vor `detail` stehen.
    - Nicht definiert, wie sich der Parser verhält bei: `detail` mit `|` oder `;`, `detail=` leer, `detail` > 80 Zeichen (bad_value? bad_syntax?), Zeile aus nur Leerzeichen und führendem Leerzeichen (`unknown_type` oder `bad_syntax`, Prüfreihenfolge).
    - Das Design sagt, unbekannte Felder werden „ignoriert und protokolliert“. Der Vertrag: nicht protokolliert.
    - Nach `PING` bei liegendem gesperrtem Tonie: die erneute `LOCKED`-Meldung hat dann auch `ERR unlock_failed`? §7 Regel 2 sagt „einmal je LOCKED-Meldung“, die Beispieldatei zeigt es nicht.
    - Empfehlung: je Fall ein Beispiel in der Datei und ein Satz im Vertrag.

12. **Nit** – reader-v1.md §7 Regel 1 und §9.
    - Die Ratenbegrenzung „innerhalb der letzten 2000 ms“ muss „mindestens 2000 ms seit der letzten Zeile“ heißen (das Beispiel bei t=2000 schreibt). Zeitbasis fehlt: Zeitstempel des Zyklus oder echte Sendezeit.
    - `up` aus `millis()` läuft nach 49,7 Tagen über. Das Feld soll aus 64-Bit-Zeit kommen.
    - Die Beispieldatei deckt nicht ab: Zeile 10 (`nichts` löscht den Herausforderer), Zeile 14 (N=3 Wechsel), N=1 (Zeilen 4 und 15), `PING` im Zustand `PRUEFT`, `fehler` bei liegender Figur mit offenem Herausforderer.

13. **Nit** – core-interface.md §3.8 und data-model.md §2/§3 („1:1 übernommen“).
    - Die Namen weichen ab: `resume.json` `folge` gegen `Zeiger.datei`, `serien` (Objekt) gegen `tuple[Zeiger]`, `zuordnungen.<uid>.serie` gegen `Zuordnung.serie_id`. Abbildung als Tabelle angeben.
    - Der Typ `Eintrag` in `outbox.offen()` ist nicht beschrieben.
    - Rundung der Position auf eine Nachkommastelle (round oder floor) fehlt.

14. **Nit** – data-model.md §2 (Fenster).
    - „`bis` ≤ `von` heißt über Mitternacht“ widerspricht „`bis` = `von` ist ungültig“ (Gleichheit ist beides).
    - Nicht existierende Ortszeit bei der Sommerzeitumstellung ist nicht geregelt.
    - Eine neue Liste (neue `liste_id`) hat welche Startrevision (1)? Nicht gesagt.

15. **Nit** – mqtt-v1.md §1/§8 und §6.2.
    - „Jede Nachricht außer config und online hat `v`“ stimmt nicht für `ui/*` (`PRESS`, Anzeigename) und `homeassistant/status`. Die Ausnahmeliste vervollständigen.
    - `binary_sensor` Lader meldet bei `null` „OFF“ statt unbekannt.
    - `HaVerbindung` ist an den Kern geführt, wird aber von keinem Teilautomaten verarbeitet.

Für Tobias zu bestätigen

1. Zuordnung auf eine Serie, die die Box noch nicht synchronisiert hat (data-model Festlegung 14): Das Kind hört den Fehlerton und danach nichts, nicht die Überraschungs-Serie. Das kommt oft vor, weil man in HA zuordnet, bevor die Box synchronisiert hat. Ist das gewollt?
2. Lesefehler am Leser von 1,1 s oder länger (reader-v1 Festlegung 4): Die Musik pausiert, weil der Fehlerzyklus nicht als „Figur ist da“ zählt. Soll der Leser eher weiterspielen lassen?
3. Kurzer USB-Aussetzer oder Neustart des Lesers: Die Wiedergabe kann mit 3 s Rücksprung neu starten. Mit der heutigen Fassung kann die Box nach einer Pause (Hauptknopf, Folgenende, „stumm“) von selbst weiterspielen (Befunde 3 und 4). Ist das akzeptabel?
4. Hauptknopf im „stumm“-Fenster: Soll er nachts trotzdem abspielen? Der Vertrag lässt es offen (Befund 6).
5. Defekte oder fehlende Folge wird mit Fehlerton übersprungen. Geht MPD verloren, pausiert die Box und das Kind muss die Figur neu auflegen (core §9.10). Ist das so gewollt?
6. Leise-Zeiten laufen in einer festen Zeitzone der Liste (Europe/Berlin), auch auf Reisen. Bei unsicherer Uhr lehnt die Box Lernmodus, Sync und Update ab. Nach einer HA-Wiederherstellung aus Sicherung kommen neue Zuordnungen erst nach der Aktion „Liste neu ausrollen“ bei den Boxen an.
