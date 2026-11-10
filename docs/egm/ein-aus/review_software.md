# Ein- und Ausschalten: Review Software, Verhalten, Verträge (Goldfisch)

*   **Gegenstand:** `design_draft.md` (Stand 10.11.), gelesen mit `concepts_brief.md`, Teilen von `research.md`, `reader-v1.md`,
    `core-interface.md`, `box-software.md` und dem Code unter `box/src/tobibox/`.
*   **Nicht geprüft:** Elektrik, Pins, Firmware-Hardware (macht der zweite Reviewer).
*   **Belege geprüft (Stichprobe, 24 Stellen):** stimmen: `idle.py:57`, `:105-107`, `:186`, `:238-242`, `:252-259`, `:153-165`, `:322-343`;
    `led.py:29`, `:64`, `:114`, `:233-234`, `:270-271`, `:280-283`; `session.py:844-845`; `core.py:44`, `:119`; `app.py:77`, `:919-927`;
    `power.py:32`, `:156-162`, `:263-267`; `quiet.py:104`; `bootid.py:3-4`; `lauf.py:6-9`; `core-interface.md:128`, `:194`, `:316`, `:320`;
    `reader-v1.md:46`, `:81`, `:281-297`, `:573-591`; `research.md:62, 79, 84, 88, 99, 120, 171, 187, 191, 207`; `box-software.md:532-537`, `:552-557`.
    Falsch: `reader.py:213` (siehe G15). Summenrechnung in Abschnitt 7 stimmt (8,1 bis 9,9 Wh).
*   **Ergebnis:** 15 Befunde: **3 hoch, 9 mittel, 3 niedrig.**

---

## Hoch

### G1 (hoch): Aus mit liegendem Tobie, LPCD-Drift weckt die Box ohne Anlass

*   **Fundstelle:** Entwurf 4.1 (`PRUEFEN`), Z01, CUJ 22 (Zeilen 136-139, 298); Entscheidung O (`box-software.md:532-537`).
*   **Ablauf:** „Gute Nacht“ endet, der Tobie bleibt liegen, nach 10 min ist die Box aus (Entscheidung O, genau dieser Fall). LPCD wird mit dem
    liegenden Tobie abgeglichen. Nachts ändern Temperatur oder Drift die Messung leicht, LPCD meldet eine „Feldänderung“. `PRUEFEN` macht **eine Lesung**:
    Sie ist **gültig**, denn der Tobie liegt ja. Also pulst der ESP32 Pad 10, die Box bootet, und der liegende Tobie spielt (S4, CUJ 20) mitten in der Nacht.
    Die Gegenmaßnahme „3 Fehlmeldungen in 10 s“ greift nur bei **ungültiger** Lesung (Hand, Metall), nicht hier.
*   **Vorschlag:** Wecken nur bei einer **Änderung**: Der ESP32 merkt sich beim Einschlafen, ob und welcher Tobie liegt. Liegt einer, weckt eine gültige Lesung
    erst, nachdem eine Lesung „leer“ gesehen wurde (Abheben und Neu-Auflegen), oder wenn die Kennung eine andere ist. Sonst nur neu abgleichen und weiterschlafen.
    In CUJ 22 und in der Zustandsliste 4.1 festhalten, mit Test in `power_fsm` (EA1) und einer Probe in Messung 2 (Tobie über Nacht liegen lassen).

### G2 (hoch): Die Box kann am Sockel aus bleiben, obwohl „am Sockel immer bereit“ gilt

*   **Fundstelle:** Brief Abschnitt 2 („Am Sockel: immer bereit, auch nachts“); Entwurf Z03, Z13, 1.2 („Unbekannt zählt wie kein Strom“), 5.6 H6 (`STROM_IN` optional), E4.
*   **Abläufe, die im Entwurf fehlen:**
    1.  Die Frist läuft ab, der Pi beginnt das Herunterfahren (Sekunden bis `SLEEP_OK`, dann `poweroff`). In dieser Zeit wird die Box auf den Sockel gestellt.
        Z15 greift nicht (`herunterfahren`, `idle.py` ignoriert fast alles), Z03 braucht eine **neue** Flanke. Strom liegt schon an, wenn der PiSugar abschaltet:
        Die Box bleibt aus, am Sockel, mit leerem Wartezustand. Ob „Einschalten bei Strom“ so etwas auslöst (Flanke oder Pegel), ist Messung 6 und offen.
    2.  `pisugar-server` hängt oder antwortet nicht: `am_lader = None` zählt als „kein Strom“ (1.2). `power.py` meldet dann nie `LaderGeaendert`.
        Die Box auf dem Sockel geht nach 10 min aus und startet nicht wieder.
    3.  Hauptknopf lang am Sockel (E4): Je nach PiSugar-Verhalten bleibt die Box aus.
*   **Warum hoch:** Das ist die Kernzusage an Tobias für den Normalbetrieb (jede Nacht am Sockel). Der Entwurf löst sie nur über `STROM_IN`, das er „optional“ und
    mit „fehlende Pins entfallen zuerst“ führt (5.5, Zeile 450).
*   **Vorschlag:** Entweder `STROM_IN` zur Pflicht machen: Der ESP32 pulst Pad 10, sobald Strom anliegt, VBUS fehlt und er schlafen soll (nach dem Ende des Herunterfahrens).
    Oder Messung 6 vor dem Einfrieren der Verträge abwarten und in den Tor-Liste (T-Liste) aufnehmen: „Pegel statt Flanke“ entscheidet. Außerdem `None` getrennt behandeln:
    Frist nur bei sicherem „kein Strom“ (`False`), bei `None` nach einer Wartezeit warnen statt abschalten, oder Entscheidung von Tobias (siehe Fragen).

### G3 (hoch): E2 ist umgedeutet: LPCD in Bereit spart fast nichts, kostet aber viel

*   **Fundstelle:** Brief E2 („spart ~0,2 W, kostet vielleicht 0,3-0,5 s“); Entwurf 4.3 (Zeilen 317-325), L5, L6 (`LPCD_ARM_MS`, `LPCD_RUECK_ZYKLEN`), V5.
*   **Befund:** Der Entwurf rechnet selbst, dass Stufe 1 **nur den RF-Puls** spart, rund 0,045 W (`research.md:88`). Die 0,17 bis 0,24 W des wachen ESP32 spart erst Light-Sleep (Stufe 2, unsicher).
    Der Brief nennt aber 0,2 W als Grund der Entscheidung E2. Der Entwurf stellt das nicht als offene Frage dar, sondern baut Stufe 1 trotzdem (Standard `wach=0`).
    Ersparnis in Zahlen: 100 min Bereit am Tag × 0,045 W = **0,075 Wh** von 15 Wh (0,5 %).
*   **Kosten:** neuer Betriebsmodus mit eigenem Zyklus-Wechsel, drei Konstanten, Befehl `CFG wach`, Änderung der Zählerregel (`polls` zählt nur volle Zyklen, siehe `reader-v1.md:203`), Latenz bis 0,3 s,
    Tests, Messung 4. Für Bereit mit liegendem Tobie gilt es nicht einmal.
*   **Vorschlag:** `wach` aus diesem Paket streichen (nur LPCD im Zustand Aus behalten, dort ist es der Kern). Stufe 2 (Light-Sleep) als eigene spätere Frage, wenn Messung 4 etwas
    Ordentliches zeigt. Tobias vorlegen, weil E2 seine Entscheidung ist. Spart V5, L5, zwei Konstanten, einen Parameter in L4 und einen Betriebsmodus in 4.1.

---

## Mittel

### G4 (mittel): Tobie wird während des Abschaltens aufgelegt und verschluckt

*   **Fundstelle:** Entwurf 4.1 (`ABSCHALTEN` → `SCHLAF`), CUJ 22 (Zeile 138).
*   **Ablauf:** Fristende, die Box fährt herunter (mehrere Sekunden). Ein Kind wechselt jetzt den Tobie (oder legt ihn auf, weil es die Box noch wach glaubt).
    Der ESP32 gleicht LPCD beim Einschlafen ab; ein jetzt liegender Tobie wird zur Bezugslage und weckt nie. Die Box ist aus, der Tobie liegt, nichts passiert.
    Das ist genau der erwartete Handgriff („Folge zu Ende, nächste Folge“).
*   **Vorschlag:** In `ABSCHALTEN` die Dauerabfrage weiterlaufen lassen. Beim Übergang zu `SCHLAF` zählt: War beim `SLEEP` kein Tobie da oder ein anderer, und jetzt liegt einer, dann sofort wecken.
    Das passt zur Regel aus G1 (Bezug merken).

### G5 (mittel): Aufteilung des Rings weicht vom Brief ab und ist nicht als Frage gekennzeichnet

*   **Fundstelle:** Brief Abschnitt 4 („Die Ring-Logik (`led.py`) bleibt auf dem Pi, nur die Ausgabe geht an den ESP32“); Entwurf 3.1, 3.3.
*   **Befund:** Der Entwurf legt Atmen, Blinken, Lauflicht und Füllstand in die ESP32-Engine. Das ist mehr als „nur die Ausgabe“. Die Begründung in 3.3 ist vernünftig,
    aber der Entwurf nennt als Preis selbst: Muster stehen zweimal (Python und C++), dazu ein Gleichheitstest. Der Brief hat das nicht entschieden, Tobias hat es nicht gesehen.
*   **Einfachere Variante B (für die Frage an Tobias):** Der ESP32 kennt nur `off`, `solid`, `frame`, `breathe` und `comet`. `comet` braucht er ohnehin für das Wecken (der Pi läuft noch nicht).
    `breathe` ist das einzige Muster, das 10 Bilder/s „gerade genug“ macht (3.3). `blink` (zweimal pro Sekunde umschalten) und `fill` (ein statisches Bild für 5 s) schickt der Pi
    als `solid` bzw. `frame`. Dann gibt es in C++ nur zwei Animationen, der Gleichheitstest prüft zwei Muster statt sieben, und `n`/`dur`/`br2`-Sonderfälle von `fill` und `blink` entfallen.
    Noch einfacher (Variante C): nur `comet` und `frame` auf dem ESP32, Atmen als Bilder vom Pi mit 10 Hz (15 kbit/s, der Entwurf selbst nennt das „trägt leicht“). Preis: Atmen mit 10 Bildern/s.
*   **Vorschlag:** In der Frageliste als eigene Frage für Tobias aufnehmen (A: Entwurf, B: zwei Animationen, C: nur Lauflicht auf dem ESP32), mit der Empfehlung B.

### G6 (mittel): Ring-Protokoll `RING`: offene Regeln, doppelte Referenz, überflüssiges `dur`

*   **Fundstelle:** Entwurf 3.2 (Zeilen 239-240), 3.3 (Zeilen 253-254), 3.4.
*   **Befunde:**
    1.  **Wiederholung und Phase:** „Die Wiederholung startet das Muster nicht neu, wenn Parameter und Muster gleich sind.“ Was ist mit „Gute Nacht“? Dort ändert sich `br`/`br2` etwa einmal je Sekunde
        (Ausblende-Faktor). Der Entwurf sagt nicht, ob die Atem-Phase bei geänderten Parametern erhalten bleibt. Ohne diese Regel springt der Ring jede Sekunde. Die Regel muss in den Vertrag (L4) und in einen Test.
    2.  **`dur` mit Wiederholung:** Die Akku-Anzeige (`dur=5000`) wird alle 5 s wiederholt. Startet die Wiederholung `dur` neu, endet die Anzeige nie; startet sie es nicht neu, rennt sie gegen den Zeitpunkt, an dem der Pi
        ohnehin den nächsten Zustand sendet. `dur` doppelt die Zeitlogik von `led.py` (der Pi weiß, wann die Anzeige endet) und der Schutz bei Pi-Absturz ist schon durch `RING_TIMEOUT_S` da.
        `dur` kann entfallen (außer beim Lauflicht des ESP32, das hat `WECK_LAUFLICHT_MAX_S`).
    3.  **Phasenbezug des Gleichheitstests:** Im Python-Code ist `_laeuft(t)` abhängig von der absoluten `mono`-Zeit, nur `_aufwachen(t_seit)` ist relativ (`led.py:171`). Der ESP32 läuft ab Musterbeginn. „Prüfbilder zu festen Zeitpunkten“
        braucht eine Festlegung: Zeit ab Musterbeginn. Sonst vergleicht der Test Verschiedenes oder ist nie grün.
    4.  **Referenz und Simulation:** Wenn `led.py` weiter `ring_fuer(zustand, t)` liefert (Zustand direkt zum Bild) und der ESP32 `RING` interpretiert, gibt es drei Wege: Zustand→Befehl (`ringsender`), Zustand→Bild (heutige Simulation), Befehl→Bild (C++). Die Simulation und die GUI
        zeigen dann nie den Weg über `RING`. Besser: **ein** Python-Interpreter `befehl_zu_bild(RING-Zeile, t)` als Referenz; `led.py` erzeugt nur noch Befehle; Simulation und GUI rufen den Interpreter. Dann prüft der Gleichheitstest
        genau den Weg, der auf dem Draht liegt.
    5.  Der ESP32 klemmt `br` auf 25 %, der Pi ebenfalls (`led.py:29`). Das ist gewollt (Doppel-Schutz), aber im Gleichheitstest muss die Klemmung auch nach oben geprüft werden (`br=100` ergibt 25 %).
*   **Vorschlag:** Die Punkte 1 bis 4 in 3.2 festschreiben; `dur` streichen (Ausnahme Lauflicht); Referenz-Interpreter in EA3.

### G7 (mittel): Frühdienst: Reihenfolge, Marke und Uhr

*   **Fundstelle:** Entwurf 6.4 (Zeilen 505-513), 6.1, 6.3 Nr. 7.
*   **Befunde:**
    1.  **`Before=tobiboxd.service` bei `Type=oneshot`:** Ein oneshot-Dienst gilt erst als fertig, wenn sein Prozess endet. Spielt er den Ton selbst (1 bis 2 s), **wartet `tobiboxd`** darauf.
        Das widerspricht dem Zeitplan (Frühton ≤ 5 s, `Bereit` ≤ 8,5 s) und dem Ziel „tobiboxd und MPD parallel“ (6.3 Nr. 7). Besser: Dienst schreibt die Marke **zuerst**, startet den Ton im Hintergrund und endet sofort;
        oder `Type=simple` ohne `Before=`, und der Box-Dienst liest die Marke, sobald sie da ist. Die Marke sagt „entschieden“, nicht „fertig gespielt“.
    2.  **Uhr:** `quiet.wirkung_jetzt` braucht `Jetzt` mit `zeit_ok`. Im Frühdienst fehlt dafür `zeit` (Plausibilitätsregel `RTC_FRUEHESTENS` in `power.py:252`). Der Frühdienst liest die RTC über I²C selbst und kennt Zeitzone und Plausibilität nicht.
        Zwei Stellen mit der gleichen Regel laufen auseinander. Vorschlag: Regel (`zeit_ok` aus RTC) in ein kleines gemeinsames Modul ziehen, das beide laden, ohne Asyncio und ohne Netz.
    3.  **Rückfall „vorberechnete Datei, die der Box-Dienst beim Beenden schreibt“ (Zeile 508)** ist falsch: Beim Beenden kennt der Dienst den Zeitpunkt des nächsten Starts nicht. Wer nachts per Tobie weckt, braucht die Uhrzeit **beim Wecken**.
        Möglich wäre nur eine Liste der Fenster als absolute Zeiten. Das ist keine Vereinfachung, dann besser eine Python-Startzeit messen und akzeptieren.
    4.  **Mehrere Töne gleichzeitig:** Der Frühton läuft außerhalb von `sounds` („Töne nie gleichzeitig“, `core-interface.md:316`). Wenn der Box-Dienst früh `hinweis` spielt, können sich beide überlagern. Messung 11 deckt nur ALSA allgemein ab; die Überlappung ausdrücklich prüfen.

### G8 (mittel): „Nie zwei Töne“ hält nicht, und Z10 widerspricht 6.4

*   **Fundstelle:** Entwurf Z10 (Zeile 79) gegen 6.4 (Zeile 511); Z15, 6.4 (Zeile 512); `power.py:259-282`, `idle.py`.
*   **Befunde:**
    1.  **Dienst-Neustart:** Z10 sagt „kein Frühton (Dienst läuft, kein Einschalten)“. 6.4 sagt: „Nach einem Dienst-Neustart fehlt die Datei: `start` klingt wie bisher.“ Heute spielt `session._bereit` bei **jedem** `Bereit`
        den Start-Ton (`session.py:844-845`), auch nach Neustart. Eines von beiden ist falsch. Wahrscheinlich gilt das heutige Verhalten; dann Z10 berichtigen. Besser wäre: nach Dienst-Neustart (gleiche Boot-ID, `lauf.py`) kein `start` mehr (er stört mitten im Hörspiel-Betrieb nach einem Update).
    2.  **`start` und `lader` doch zusammen:** Z15 und V19 sagen „Wechsel von ‚kein Strom‘ (auch unbekannt) nach ‚Strom‘ nach `Bereit`“. `Power` meldet `LaderGeaendert` nur bei Änderung und gar nicht, wenn `pisugar-server` beim Start noch nicht antwortet
        (`power.py` gibt bei `PiSugarFehler` nichts zurück). Beim Einschalten durch Strom (Z03) kann die erste Messung also fehlen und später `None → True` kommen: `start` (Frühton) und danach `lader`. Der Entwurf behauptet (Zeile 512), das sei ausgeschlossen. Es gilt nur,
        wenn die erste gültige Messung vor `Bereit` liegt. Zusätzlich fehlt, wie `idle` „erste Messung“ erkennt (es merkt sich nur `am_lader`, `None` vs. Wert).
    3.  **`boot_id` in `fruehton.json`** ist überflüssig: Die Datei liegt auf tmpfs (weg bei jedem Einschalten) und der Box-Dienst löscht sie beim Lesen. Ein Dienst-Neustart ohne Neustart des Pi findet keine Datei. Die Prüfung der Kennung schützt gegen nichts. Streichen (V25 einfacher).
*   **Vorschlag:** Z10 nach heutigem Verhalten formulieren (oder bewusst ändern und als Entscheidung festhalten); für `lader` entfallen, siehe G14 (Vereinfachung: ganz streichen). Wer `lader` behält: `idle` braucht ein Merkmal „Strom war bei der ersten Messung schon da“.

### G9 (mittel): `wring`/`wring_s` ist zu aufwendig und geht über S5 hinaus

*   **Fundstelle:** Entwurf 3.4 (Zeile 261), 3.5 (Zeilen 279-281), L4 (`SLEEP wring=… wring_s=…`).
*   **Befund:** Der ESP32 kennt die Leise-Zeiten nicht, deshalb schickt der Pi vor jedem `SLEEP` zwei Zahlen und eine Restdauer, die der ESP32 mit seiner ungenauen RTC (RC-Oszillator, mehrere Prozent Fehler; bei einem 8-h-Fenster ±30 bis 50 min) abzählt.
    Das neue Feld im Befehl, die Berechnung „Sekunden bis Fensterende oder nächster Fensterbeginn“ (neue Funktion in `quiet.py`, in keinem AP und keiner Vertragsstelle) und der Sonderfall des Pfades ohne `SLEEP` (Hauptknopf lang, Tiefstand, VBUS weg:
    dort bleibt ein alter Wert stehen) kosten viel. Außerdem ist „aus“ unter „leiser“ **strenger** als Brief Abschnitt 6 (S5: „Ring gedimmt“, nicht aus).
*   **Vorschlag:** Ein fester, dunkler Wert für das Lauflicht des ESP32 (die 5 % des Entwurfs, vorher in Messung 9 an der Hülle prüfen). Kein `wring`, kein `wring_s`, kein `SLEEP`-Parameter, keine neue Funktion in `quiet.py`. Wenn 5 % nachts zu hell sind, ist das eine Frage an Tobias,
    nicht ein Grund für eine Uhr im ESP32.

### G10 (mittel): Vertragsänderungen: Versionsregel stimmt, aber Liste ist unvollständig

*   **Versionsregel (Auftrag 4): im Kern richtig.** `reader-v1.md` Abschnitt 13 erlaubt ohne neues `proto`: optionale Zusatzfelder am Ende bekannter Zeilen (`HELLO.caps` ✓), neue Zeilentypen (`WAKE`, `SLEEP_OK` ✓), neue Fehlercodes (✓).
    Neue Zeilen vom Box-Dienst deckt Abschnitt 8 als „Rückkanal reserviert“ ab; die alte Firmware antwortet mit `bad_command` (Hinweis, kein Fehler). Rückwärtskompatibilität geprüft:
    - alter Dienst + Firmware 2.0.0: ignoriert `caps`, `WAKE`, `SLEEP_OK` (Abschnitt 11) ✓; sendet nie `RING`/`SLEEP`/`CFG`, der ESP32 fällt auf „VBUS weg ohne `SLEEP`“ zurück ✓, der Ring bleibt dunkel (Rollback ohne Ring, zumindest erwähnen).
    - neuer Dienst + Firmware 1.x: sendet ohne `caps` nichts ✓.
    Zwei Haken: (a) Abschnitt 13 sagt „Neue Pflichtfelder gibt es in Version 1 nicht“. `WAKE reason ring` sind Pflichtfelder einer **neuen** Zeile. Das ist erlaubt, sollte aber in L8 ausdrücklich so stehen, sonst liest sich L1 wie ein Verstoß.
    (b) `fw` 2.0.0 mit `proto` 1: Abschnitt 13 sagt nichts zur Beziehung; L8 nennt nur `firmware_min`. In Ordnung, bitte den Satz „Die Hauptversion von `fw` und `proto` sind unabhängig“ ergänzen.
*   **Fehlende oder falsch eingestufte Stellen:**
    1.  **`reader-v1.md` Abschnitt 7, Zeile „Die Liste ist **vollständig** für Version 1“:** L3 fügt vier Codes hinzu, ändert aber diesen Satz nicht. Er widerspricht dann. (Eine Zeile mehr in V3.)
    2.  **V20 ist keine Klarstellung:** `led` gibt `RING` an `reader`, `app` sendet `SLEEP` und `CFG`. Das sind **neue Befehle** im Katalog 4 (`core-interface.md`), z. B. `RingSetzen`, `LeserSchlafen`, `LeserKonfigurieren`, samt Empfänger, Rang in `_RANG` (`core.py`) und Reihenfolge
        gegenüber `HerunterfahrenAngefordert`. Gehört zu den inhaltlichen Stellen (aus 19 wird 20 oder mehr).
    3.  **Konfigurationsschlüssel `[leser] lpcd`, `wach`** stehen nur unter „Code“ (8.4), aber in keiner Vertragsstelle (`core-interface.md` Abschnitt Konfiguration ab Zeile 1401 beschreibt `[leser]`). V-Nummer fehlt.
    4.  **`HB.polls` (`reader-v1.md:203`):** „Anzahl abgeschlossener Abfragezyklen … Jeder Zyklus zählt“. Mit Wachbetrieb steht `polls` lange still. L5 legt das fest; trotzdem in der Status-Karte oder im Wächter prüfen, dass niemand „`polls` steht still = Leser tot“ schließt.
    5.  **ESP32-Firmware-Update:** Bei `firmware_min` 2.0.0 und der neuen Zustandsmaschine (Schlaf, VBUS) muss das Flashen über USB beschrieben werden (ESP32 startet neu, `WAKE reason=reset`, kein Schlaf während des Flashens). Steht in keinem Vertrag und in keinem Arbeitspaket.
    6.  **`quiet.py`/`wring`:** siehe G9 (falls bleibt).
*   **Zählung:** „26 Stellen (19 inhaltlich, 7 Klarstellungen)“ stimmt mit der Tabelle überein (Klarstellungen: V2, V8, V13, V14, V20, V22, V24). Mit den Punkten 1 bis 3 sind es mindestens 29.

### G11 (mittel): Hauptknopf-Pfad ist der alte, offene

*   **Fundstelle:** Z07, Z11, Z12, Z17; Entwurf 5.6 H7, E11; `core-interface.md:221`, `box-software.md:552-557` (B2); Plan Punkt 4 (`stueckliste-und-psp.md:45-52`).
*   **Befund:** Der Hauptknopf ist laut Plan nur parallel zum PiSugar-Taster geschaltet und wirkt über Shell-Befehle des `pisugar-server` (Einfach = Play/Pause, Lang = Zeiger sichern + Herunterfahren). B2 sagt, dass die Abfrage im Dienst („`taste_befehl`“) nicht belegt ist.
    Der Entwurf stützt aber Z11 (Bereit→Spielt per Knopf), Z12 (Frist neu bei Knopfdruck) und Z07/Z17 (Herunterfahren mit `SLEEP`) auf einen Knopf, der den Box-Dienst erreicht. Läuft der Langdruck über `soft_poweroff_shell` am Dienst vorbei,
    gibt es **kein `SLEEP`**, kein `wring`, und der Zeiger wird nur gesichert, wenn das Skript ihn sichert. E11 verschiebt das auf später („Hauptknopf mitlesen nicht Teil des Entwurfs“).
*   **Vorschlag:** Im Entwurf festhalten, welcher Weg gilt (Shell-Befehl ruft `tobibox`-CLI, die über den Dienst `SLEEP` auslöst; oder ESP32 liest mit, H7). B2 als Voraussetzung in die Tore (T-Liste) aufnehmen. Ohne Lösung funktioniert die Frist-Verlängerung durch Bedienung nur für Weiter/Zurück/Dreh/Kopfhörer, nicht für den Hauptknopf.

### G12 (mittel): Arbeitspakete: Reihenfolge, fehlende Simulation, Modellwahl

*   **Fundstelle:** Entwurf 10.1 bis 10.2 (Zeilen 678-707).
*   **Befunde:**
    1.  **EA0 vor den Messungen:** Die Verträge sollen mit EA10/EA11 parallel laufen, aber T1/T2 (LPCD trägt nicht, Pad 2 nicht belastbar) und Messung 8 (USB ohne VBUS) können `caps`, `WAKE reason`, `lpcd`, `VBUS_SENSE` und `SLEEP` kippen.
        Teile sind davon unabhängig: Frist ohne Strom (EA2), Ring (EA3), Frühdienst (EA5). **Vorschlag:** EA0 teilen in EA0a (Idle, Ring, Frühton: sofort) und EA0b (WAKE, SLEEP, CFG, `caps`, LPCD: nach T1, T2 und Messung 8).
    2.  **Abhängigkeit fehlt:** EA1 (Gleichheitstest) braucht die Prüfbilder aus EA3. Dort steht nur „EA0“. EA2 braucht den neuen Ton `lader` (Literal in `events.py`) aus EA6 oder EA0.
    3.  **Keine Simulation der Gegenseite:** EA4 erweitert den Sim-Leser um `WAKE`/`SLEEP_OK`. Es gibt kein Modell des ESP32 für `RING` (Wartezeit `RING_TIMEOUT_S`, `host_timeout`, VBUS, Ring-Zustand). Ein Test von CUJ 21/22 am Mac prüft deshalb nur den Pi.
        **Vorschlag:** `power_fsm.cpp` und `ring.cpp` auch als kleines Host-Programm mit Zeilen auf stdin/stdout bauen (`pio test -e native` baut sie ohnehin). Der Sim-Leser spricht das Programm über eine Pipe an. Dann sind Gleichheitstest (G6) und CUJ-Tests dieselbe Sache, und die Befehlsgrammatik wird real geprüft.
    4.  **Modell:** EA7 (CUJ-Tests über `idle`, `led`, `reader`, `power`, simulierte Uhr, mehrere Bausteine) ist laut `CLAUDE.md` „Tests mit Hardware-Bezug“ eher Sonnet als Haiku. EA6 enthält Logik im Kern (`core.py` Regel 2a): grenzwertig, besser Sonnet für die Regel, Haiku nur für den Ton.
    5.  **Fehlende Tests:** G1, G4 (Wecken bei liegendem Tobie), Z22 `sleep_aborted` am Mac, Wackelkontakt (Sperre 10 s) bei den CUJ-Tests, `host_timeout`, Pi-Hänger (`RING_TIMEOUT_S`), Sperre nach Tiefstand. Als Liste in EA7 aufnehmen.
    6.  **Fehlende Pakete:** ESP32-Update-Weg (G10 Nr. 5), Funktion „Fensterwechsel“ in `quiet.py` (falls G9 bleibt), `deploy/pi/`-Installer für den Frühdienst (ist EA5, aber ohne Test auf dem Pi).

---

## Niedrig

### G13 (niedrig): Lücken und Unstimmigkeiten im Zustandsmodell

*   **Z03 gegen CUJ 25:** Z03 endet in „Bereit (bleibt, Strom da)“, CUJ 25 (Zeile 168) sagt: Liegt ein Tobie, spielt er. Z03 sollte wie Z02 „(liegt ein Tobie: Spielt)“ nennen.
*   **Pi startet, aber nicht hoch (E10):** Nach `host_timeout` ist der Zustand des ESP32 nicht beschrieben. `WECKEN` hat nur „VBUS weg → SCHLAF“. Der ESP32 bleibt in einem Zwischenzustand, Tobie-Wecken ist für diesen Fall nicht gesperrt (wird erst durch E10 definiert). Zielzustand `FEHLER` oder `LAEUFT ohne Host` angeben.
*   **Pi hängt, 5 V da:** Der ESP32 merkt es nur am fehlenden `RING` (3.4), schaltet den Ring ab und tut sonst nichts. Der Pi zieht weiter Strom. Das gilt schon heute (nur das Ring-Symptom ist neu); in der Liste der Annahmen ausdrücklich so nennen (Auftrag Punkt 2).
*   **ESP32 weckt, Tobie ist beim Start weg:** Die Box zeigt Lauflicht, spielt `start`, bleibt 10 min bereit ohne etwas zu tun. Zulässig, aber im Modell fehlend. Außerdem fehlt, dass der ESP32 **in `WECKEN` die Dauerabfrage laufen lässt**, damit nach `PING` die liegende Figur sofort gemeldet wird (der Entpreller braucht mehrere Zyklen).
*   **Abziehen während Gute Nacht (Z09):** Die Akku-Anzeige (15 % „normal“) überdeckt das Glimmen (3 bis 8 %) für 5 s. Im dunklen Kinderzimmer ist das hell, wenn „Gute Nacht“ nicht in einem „leiser“-Fenster liegt. Vorschlag: Während Gute Nacht läuft, die Akku-Anzeige im Ring mit denselben 5 % wie unter „leiser“ zeigen.
*   **`led.py` „Aufwachen nur nach Dienst-Neustart“ (Zeile 235 des Entwurfs) stimmt nicht:** `led.py:228` löst das Lauflicht auch bei `leerlauf→aktiv` ohne liegenden Tobie aus (z. B. HA-Befehl „abspielen“). Dafür gibt es in der Tabelle keine Zeile; Verhalten bleibt, wie es ist, oder bewusst streichen.
*   **Z19:** Die Frist läuft bei Leise-Zeiten weiter (Entscheidung O). Dann geht eine Box unter „stumm“ am Sockel nicht aus (Strom), ohne Sockel aber nach 10 min; E5 sagt dasselbe. In Ordnung, nur Z19 und E5 verweisen nicht aufeinander.

### G14 (niedrig): Was sich streichen lässt (Vereinfachungen)

Nach Wirkung geordnet. Alles zusammen verkleinert Vertrag, Firmware und Tests spürbar:

1.  **Ton `lader` (E8) streichen.** Beim Andocken in Bereit reicht der Ring (Ladestand). Beim Andocken aus Aus gilt der Frühton. Spart V15, V17, V18, einen Teil von V26, EA6 (Ton), die ganze Fehlerklasse „zwei Töne“ (G8) und die Sonderfälle im Sync-Takt. Der Ring zeigt es bereits.
2.  **`LPCD wach` in Bereit streichen** (G3).
3.  **`wring`/`wring_s` streichen** (G9).
4.  **`dur` im `RING` streichen** (G6), `fill`/`blink` als `frame`/`solid` (G5).
5.  **`boot_id` in `fruehton.json` streichen** (G8).
6.  **Z07/Z17 und Z08/Z18 sind doppelt** (gleiche Aktion). In der Tabelle nur einmal führen, mit „Spielt oder Bereit“.
7.  **`SLEEP_OK`:** Der Pi wartet höchstens 1 s darauf (`SLEEP_OK_FRIST_S`) und fährt dann ohnehin herunter. Es ist nur Diagnose. Weglassen spart eine Zeile im Vertrag und eine Konstante; der ESP32 gewinnt nichts durch die Antwort.
8.  **Vier neue Fehlercodes:** `lpcd_noise`, `pad_pulse` sind Diagnose; `sleep_aborted`, `host_timeout` zeigen, wo es hakt. Behalten, aber bei ihnen steht „Hinweis“: Ob sie in der Status-Karte erscheinen sollen, ist offen (V23 nimmt nur `sleep_aborted` nach MQTT).
9.  **Z-Liste:** Z09 (Spielt, nur Ring) und Z16 (Abziehen) lassen sich in den Absatz „Ring bei Strom-Wechsel“ falten.

### G15 (niedrig): Kleine Fehler im Entwurf

*   `reader.py:213` (Entwurf 4.1, Zeile 303): Dort steht nur die Methode `ping()`. Das `PING` bei jeder neuen Verbindung sendet `reader.py:308` und `:322`.
*   Kurzfassung Nr. 8 „Neun offene Fragen“; Abschnitt 9 führt E3, E4, E5, E6, E8 bis E14 = **elf**.
*   Abschnitt 8.3, Zeile „S4 liegender Tobie“: erwähnt „G2 des Reviews“, ohne dass die Datei in der Grundlage steht (`review_goldfisch.md` des ruhenden Entwurfs ist in der Kopfzeile genannt, gut; die Nummer sollte mit Datei stehen).
*   Zeitschätzung 6.1: Auflegen (Aus) → Hörspiel „1,0 + 8,5 + 0,5“ ergibt 10,0 s ohne Reserve; der Entwurf nennt das selbst „ehrgeizig“. Gut so; E13 sollte schon jetzt 15 s als Zielwert in Plan und Brief führen, sonst kippt jede Messung die Zusage.

---

## Zu den Prüfpunkten des Auftrags (Kurzantwort)

1.  **Treue zum Brief:** E1 ✓ (Z15, CUJ 23). E7 ✓ (Lauflicht, keine Extra-LED/Summer). **E2 umgedeutet (G3).** Ring-Aufteilung weicht ab, ohne Frage (G5). Lauflicht unter „leiser“ aus, strenger als S5 (G9).
    E6 und E8 bis E14 sind richtig als Fragen geführt.
2.  **Zustandsmodell:** Die Hauptlücken sind G1, G2, G4. Alle anderen Abläufe aus dem Auftrag gehen auf (Pause→10 min→Tobie: Z24/Z01 ✓ nach G1/G4; Sockel nachts stumm: ✓; Abziehen in Gute Nacht: G13; Wackelkontakt: ✓ bis auf G2/G8; Dienst-Absturz: ESP32 schaltet den Ring nach 15 s ab ✓;
    Pi startet nicht: G13; Tiefstand ohne Strom: ✓; Update am Sockel: ✓ bis auf ESP32-Flash G10; Lernmodus: ✓; Tobie bei Start nicht gelesen: G13).
3.  **Ring:** Aufteilung sauber, aber zu groß geraten (G5, G6).
4.  **Verträge:** Versionsregel richtig, Liste unvollständig (G10).
5.  **Frühton:** Reihenfolge, Uhr, zweiter Ton: G7, G8.
6.  **Einfachheit:** G14.
7.  **Arbeitspakete:** G12.

---

## Fragen, die nur Tobias entscheiden kann

1.  **Ring-Aufteilung (G5):** A) Muster auf dem ESP32 (Entwurf), B) nur Atmen und Lauflicht auf dem ESP32, C) nur das Lauflicht, Rest als Bilder vom Pi. Empfehlung B.
2.  **LPCD in Bereit (G3):** Streichen (spart nur 0,075 Wh am Tag), oder behalten, weil E2 es wollte? Empfehlung: streichen, später Light-Sleep prüfen.
3.  **Ton `lader` (G14 Nr. 1):** Reicht beim Andocken in Bereit der Ring? Empfehlung ja (entspricht E8 „billiger“, löst die Doppel-Ton-Frage).
4.  **Lauflicht beim Wecken unter „leiser“/„stumm“ (G9):** Immer fest 5 % (einfach), oder nachts ganz aus (braucht `wring`/Uhr im ESP32)?
5.  **Am Sockel nie aus (G2):** Bauen wir `STROM_IN` sicher ein (Pflicht), auch wenn dafür ein Pin gebraucht wird? Und bei „Strom unbekannt“ (`pisugar-server` antwortet nicht): abschalten (Entwurf) oder weiter bereit bleiben?
6.  **Dienst-Neustart (G8):** Soll nach einem Update-Neustart der Start-Ton ausbleiben (ruhiger) oder wie heute klingen?
7.  **Wecken bei liegendem Tobie (G1):** Soll ein Tobie, der seit der Abschaltung unverändert liegt, die Box nie wecken (Empfehlung), auch nicht nach Abheben und Wiederauflegen zählt erst dann? Oder soll auch der unveränderte Tobie nach einer Weile wecken?
8.  **Hauptknopf (G11):** Welcher Weg ist verbindlich: PiSugar-Shell-Befehl über `tobibox`-CLI, oder Mitlesen durch den ESP32 (H7), und zwar jetzt oder später?
9.  **Freigabe von EA0 (G12):** Verträge in zwei Schritten (jetzt Idle/Ring/Frühton, nach den Messungen WAKE/SLEEP/LPCD)?
