# Goldfisch-Review: Vertragsänderungen Ein/Aus, Schritt 1 (Commit 3faab8b)

Stand 10.11. · Prüfer: Goldfisch ohne Vorwissen · Maßstab: `resolve.md` (R1–R11, Schritt 1 nach P8) und die Versionsregeln der Verträge.
Geprüft: alle Stellen „(Ein/Aus, 10.11.)“ in `docs/protocol/core-interface.md`, `reader-v1.md`, `mqtt-v1.md`, `ha-websocket-v1.md`, `docs/data-model.md`, `docs/designs/box-software.md` und der übrige Text, der davon berührt wird.

## Ergebnis in Kürze

*   **17 Befunde: 2 hoch, 7 mittel, 8 niedrig.**
*   **Entscheidungstreue:** R4 (Lader-Ton kurz, nicht in Leise-Zeiten, nicht beim Hören, nie zwei Töne), R8 (am Sockel immer an, Hauptknopf lang fährt herunter), R9 (Frist ab dem Abnehmen), R10 (Frühton: stumm keiner, leiser leise mit Grenze, sonst normal; Abweichung von Rev. 2 ist in Vertrag und Design benannt) und R11 (nur Schritt 1) sind in den geänderten Stellen **richtig und widerspruchsfrei** umgesetzt. Die Pegelformel des Frühtons passt zur Formel des Kerns beim Dienststart.
*   **Schritt 2:** Nichts Inhaltliches hineingerutscht. `WAKE`, `SLEEP`, `CFG`, `RING_PI`, LPCD, Hall und Weiche kommen nur als „folgt mit Schritt 2“ oder in der Liste der Arbeitspakete E2-x vor (Befund V17 betrifft nur die Reihenfolge der Hinweise, nicht den Inhalt).
*   **Rückwärtsverträglichkeit:** Alter Dienst gegen neue Firmware ist sauber (`caps` wird als Zusatzfeld, `LADER` als `unknown_type` ignoriert, beide nur DEBUG). Neuer Dienst gegen Firmware 1.x ist sauber (`caps` = `""`, nur `pisugar-server`). Probleme: V9, V11, V14.
*   Die Lücken, bei denen die Umsetzung raten müsste, stehen vor allem in V1 bis V7.

---

## Hoch

### V1 · Hoch · Frühdienst kann nach dem Marken-Lesen noch spielen: Doppel-Ton

*   **Fundstelle:** `core-interface.md:739-750` (Punkt 6.5g), `data-model.md:155-162`, `box-software.md:986` (CUJ 21, „Ausnahme Frühdienst fehlt, zu langsam“).
*   **Problem:** `app` liest die Marke **einmal beim Start** des Dienstes, `Bereit` kommt aber erst einige Sekunden später (MPD, Leser). Schreibt der Frühdienst `start` **nach** diesem Lesen (Ausgang kommt spät, Ziel „höchstens 5 s nach 5 V“, `Bereit` Ziel 8,5 s), gibt es keine Marke: `app` sendet `Bereit(fruehton=False)`, der Kern spielt `start`, und der Frühdienst spielt **zugleich oder gleich danach** seinen Ton. Das verletzt „nie zwei Töne“ (Entscheidung L, P6). Der Vertrag schützt nur das Schreiben von `fertig` („legt sie nicht neu an“), nicht das erste Schreiben von `start` oder `keiner`. Dazu: Das atomare `rename` des Frühdienstes legt die Datei auch an, wenn `app` sie zwischen Prüfung und `rename` gelöscht hat.
*   **Vorschlag:** (a) `app` liest die Marke **bei `Bereit`**, nicht beim Start (die Wartezeit `FRUEHTON_WARTEN_S` läuft dann ab diesem Zeitpunkt). (b) `app` legt beim Entschluss, den Kern-Ton zu spielen, selbst eine Gegenmarke an (z. B. `kern`), und der Frühdienst darf nur starten, wenn die Marke noch fehlt (Erzeugen mit `O_EXCL`/`link`, nicht `rename`). (c) Den Satz in 6.5g auf beide Schreibvorgänge ausdehnen.

### V2 · Hoch · Leser-Wert veraltet bei Ausfall: Vorrang Leser hält die Box an oder aus

*   **Fundstelle:** `core-interface.md:1196-1202` (Punkt 9.2 und 9.3, „Eine Quelle, die nach einem bekannten Wert schweigt, behält ihren letzten Wert“).
*   **Problem:** Bei Widerspruch gilt der Leser, auch wenn er seit Minuten nichts mehr liefert. Fällt die Leser-Verbindung aus (USB-Aussetzer, `LeserAlarm`, Firmware-Neustart ohne neues `LADER`) oder wurde eine Firmware ohne `strom` aufgespielt, bleibt der alte Wert „Strom“ gültig. Wird die Box dann abgenommen, meldet nur `pisugar-server` „kein Strom“, aber der Leser gewinnt: Die Box zählt nie, schaltet nie ab, der Akku läuft leer. Umgekehrt (alter Wert „kein Strom“, jetzt am Sockel) zählt die Frist weiter und schaltet am Sockel ab, gegen R8/CUJ 23. Dasselbe gilt für einen hängenden `pisugar-server` mit altem Wert, wenn der Leser fehlt (Firmware 1.x).
*   **Vorschlag:** Der Wert des Lesers gilt nur, solange die Leser-Verbindung steht (zwischen gültigem `HELLO` und Ausfall, `reader-v1.md` Abschnitt 12). Bei Ausfall oder bei einem `HELLO` ohne `strom` fällt `idle` auf `pisugar` zurück; `reader` meldet dafür z. B. `LaderGeaendert(am_lader=None, quelle="leser")` (Wert unbekannt) oder ein eigenes Ereignis. Für `pisugar` einen Alterungsweg festlegen (z. B. `power` meldet „unbekannt“, wenn `pisugar-server` nicht antwortet).

---

## Mittel

### V3 · Mittel · Zusammenführen zweier Quellen kann beim Start ein falsches „Andocken“ auslösen

*   **Fundstelle:** `core-interface.md:1196-1198` (9.2), `1203-1210` (9.4, 9.5), `reader-v1.md:138-146`.
*   **Problem:** „Erste bekannte Messung“ ist als „erster Wert **irgendeiner** Quelle“ erklärt, „Andocken“ als Wechsel des **zusammengeführten** Werts danach. Meldet `pisugar` zuerst „kein Strom“ (kurzer Fehlwert beim Start, Messung noch nicht stabil) und kommt dann der Leser mit „Strom“, ist das ein Wechsel nach der ersten Messung: Ring und Ton `lader` (nur die Sperre ab `Bereit` schützt, und nur 10 s). Ebenso für „Strom“ vs. später „kein Strom“ (falsches Abziehen mit Ring Akku). Zusätzlich: `LADER` direkt nach `HELLO` ist ein Pegel; der Vertrag sagt nicht, ob die Firmware beim Start schon entprellt hat. Liegt `in=0` vor Ablauf der 200 ms und folgt `in=1`, gibt es einen echten Wechsel im Dienst.
*   **Vorschlag:** (a) Festlegen: Ein Wechsel, der **nur** durch das Hinzukommen einer Quelle oder durch den Vorrangwechsel entsteht (zuvor kein Leser-Wert), ist keine Andock- oder Abzieh-Rückmeldung. (b) `reader-v1.md`: Die erste `LADER`-Zeile nach `HELLO` kommt erst, wenn der Pegel entprellt ist, oder `HELLO` verzögert sich entsprechend; oder die Firmware nennt die ersten 200 ms als „hoch“-Entprellung nicht. Eine Zeile reicht.

### V4 · Mittel · Spät kommende erste Messung „Strom“ nach den 60 s: Zähler wird nicht ausdrücklich verworfen

*   **Fundstelle:** `core-interface.md:1200-1209` (9.3, 9.4), Design Tabelle „Strom / Leerlauf“ `box-software.md:1489-1490`.
*   **Problem:** Nach 60 s ohne Wert gilt „kein Strom“, der Zähler läuft. Kommt dann die erste bekannte Messung „Strom“ (Punkt 4), löst sie laut Wortlaut **nur** den Sync-Check aus. Dass der Zähler verworfen wird (Punkt 1: „Strom kommt“), steht dort nicht ausdrücklich; Punkt 5 (Andocken) greift laut Definition nicht. Die Box am Sockel könnte so nach 10 min abschalten, obwohl Strom anliegt.
*   **Vorschlag:** In Punkt 4 ergänzen: „Der Zustand (Zähler verworfen oder begonnen) folgt dem Wert sofort; nur die Rückmeldung (Ring, Ton) entfällt.“ Dasselbe in der Tabelle „beim Start“.

### V5 · Mittel · Marke `keiner` bei fehlender Datei oder fehlendem Ausgang widerspricht CUJ 21

*   **Fundstelle:** `data-model.md:155-156` („`keiner` (… Modus „stumm“, Datei oder Ausgang fehlt)“) gegen `box-software.md:986` (CUJ 21: „Frühdienst … gescheitert: Dann gibt es keine Marke, und der Kern spielt `start` wie bisher“) und `core-interface.md:745-746`.
*   **Problem:** Steht `keiner` bei „Datei oder Ausgang fehlt“, ist die Marke da, `Bereit.fruehton` wahr, und der Kern spielt **keinen** `start`. Die Box startet dann ohne jeden Ton, obwohl nur der Frühdienst gescheitert ist. Unter „stumm“ ist das gewollt (R10), sonst nicht. Zusätzlich: Fällt der Frühdienst aus und die Box steht unter „stumm“, spielt der Kern als Rückfall `hinweis` (Regel 6.2.2). Das ist ein Ton unter „stumm“ beim Einschalten, den CUJ 15 („Anders als heute … auch keinen Hinweiston“) ausschließt.
*   **Vorschlag:** `keiner` nur für „bewusst: stumm“. Bei fehlender Datei oder fehlendem Ausgang keine Marke (oder `fehler`, das `app` wie „keine Marke“ behandelt). Im Rückfall unter „stumm“ (Frühdienst fehlt, Dienst-Neustart) entweder bewusst `hinweis` zulassen und in CUJ 15 und 21 so schreiben, oder den Kern-`start`/`hinweis` beim Dienststart unter „stumm“ streichen.

### V6 · Mittel · Freigabe der Andock-Anzeige für `led` ist offen (Lücke in Punkt 9.9)

*   **Fundstelle:** `core-interface.md:1226-1228` („wie `led` die Freigabe von `idle` erfährt, legen AP E1-1 und E1-4 fest und tragen es hier nach“), `box-software.md:930-934`, `3046` (E1-4).
*   **Problem:** Der Vertrag lässt die Schnittstelle zwischen `idle` und `led` offen, obwohl sie ein Vertrag ist (Ring-Anzeige gilt „mit denselben Regeln“ wie Ton und Sync, also Sperre, erste Messung, zusammengeführter Wert). Zwei Teams (E1-1 und E1-4) müssten sich einigen. Dazu: Der Ring-Text unter „Übrige Zustände“ (`box-software.md:930`, „Akku als Füllstand … am Lader blau“) und die neue Akku-Anzeige (Helligkeit 15/5/3 %, Faktor 0,4 gilt nicht) stehen nebeneinander; „Ring Ladestand 5 s“ (Andocken) und „Ring Akku 5 s“ (Abziehen) sind nicht als gleich oder verschieden erklärt.
*   **Vorschlag:** Jetzt festlegen: `idle` gibt ein internes Ereignis (z. B. `AnzeigeFreigabe(art="andocken"|"abziehen", dauer_s)`) an `led`, oder `led` liest `KernZustand.lader` und die Sperre selbst (dann gehört `LADER_SPERRE_S` in `led.py`). Ein Satz zu „Ladestand“ gegen „Akku“ (gleiche Anzeige, Farbe blau mit Strom?), und den alten Ring-Satz 930 daran anpassen.

### V7 · Mittel · Frühdienst: Quelle von Uhr-Sicherheit, Kopfhörer-Kontakt und Konfiguration fehlt

*   **Fundstelle:** `core-interface.md:896-908` (Neue Töne), `box-software.md:3047` (E1-5).
*   **Problem:** Die Formel braucht `zeit_ok` („Uhr-Regel der Box“), den Kopfhörer-Kontakt („solange nicht sicher ‚leer‘“), `lautstaerke_start/max/kopfhoerer` aus `tobibox.toml` und die Leise-Zeiten aus `config.json`. Nicht festgelegt ist: Wie weiß der Frühdienst, ob die RTC gelesen ist (die RTC liegt am `pisugar-server`, der beim Frühton oft noch nicht läuft)? Wie liest er den Kopfhörer-Kontakt (GPIO, Entprellung, Kontakt „nicht lesbar“, Entscheidung P)? Was gilt, wenn `config.json` fehlt oder beschädigt ist (erstes Einschalten, Entscheidung zum Fehlerfall)? Die Gehörschutz-Regel „im Zweifel die kleinste Grenze“ ist nur für die Uhr genannt.
*   **Vorschlag:** Drei Sätze im Vertrag: (1) Fehlerfälle des Frühdienstes: kein `config.json` oder kein `tobibox.toml` → kleinste vorhandene Grenze (Kopfhörer-Grenze), nie „stumm“ aus Vermutung; (2) Uhr: Kann die RTC nicht gelesen werden, gilt „unsicher“ (kleinste „leiser“-Grenze); (3) Kopfhörer-Kontakt nicht lesbar → Kopfhörer-Grenze, wie Entscheidung P.

### V8 · Mittel · MQTT `lader` ändert die Bedeutung ohne Erhöhung von `v`

*   **Fundstelle:** `mqtt-v1.md:9-11`, `159`, `604` gegen die eigene Regel `mqtt-v1.md:733` („Erhöhung von `v` bei … Bedeutung … geändert“); `ha-websocket-v1.md:8-9` ähnlich.
*   **Problem:** Das Feld heißt „Klarstellung“, ändert aber die Bedeutung (vorher Ladegerät, jetzt Strom aus jeder Quelle, auch Powerbank, Sockel, Auto). Das Gerätemerkmal `battery_charging` stimmt für eine volle Box am Strom nicht mehr. HA-Automationen, die „Lader“ als „lädt“ lesen, ändern ihr Verhalten. Das ist nach der Regel eine Erhöhung. Es ist zu beurteilen, ob der Fall für `v` eine Ausnahme sein darf.
*   **Vorschlag:** Entweder (a) die Ausnahme in der Versionsregel ausdrücklich nennen („Klarstellung ohne Änderung der Datenform; HA-Automationen prüfen“) und `device_class` auf `plug` (Strom anliegt) ändern, oder (b) nicht umdeuten, sondern ein neues Feld `strom` ergänzen (additiv) und `lader` als Alias lassen. Entscheidung gehört Tobias.

### V9 · Mittel · Ungültiges `caps` macht das ganze `HELLO` ungültig

*   **Fundstelle:** `reader-v1.md:106` (Format von `caps`), `530-535` (Tabelle, `bad_value`, `bad_syntax`), `reader-v1.md:567`, `core-interface.md:140`.
*   **Problem:** Ist `caps` formal falsch (mehr als 5 Namen, Großbuchstaben, zu lang, leer `caps=`), gilt laut Tabelle die **ganze Zeile** als ungültig. Der Dienst bekommt kein gültiges `HELLO`, es folgt `hello_timeout` und Leser-Ausfall (Abschnitt 12), obwohl alles andere stimmt. Eine künftige Firmware mit sechs Fähigkeiten würde einen alten Dienst lahmlegen. Das widerspricht der Aussage in 13, neue optionale Felder dürften alte Parser nie stören. Offen ist auch, ob die Firmware ohne Fähigkeit das Feld weglässt (ein leerer Wert ist `bad_syntax`).
*   **Vorschlag:** Für `caps` eine Ausnahme: Ein Wert, der das Format verletzt, wird wie „fehlt“ behandelt (`caps` = `""`, DEBUG-Meldung), das `HELLO` bleibt gültig. In 5 ausdrücklich: Ohne Fähigkeit wird das Feld weggelassen, nie `caps=` gesendet. Die Grenze „höchstens 5 Namen“ ist für künftige Erweiterung ohne Not eng; besser nur die Zeilenlänge als Grenze.

---

## Niedrig

### V10 · Niedrig · `reader-v1.md` Zeilen 186, 303, 631 kennen `LADER` nicht

*   **Fundstelle:** `reader-v1.md:186` („`HELLO`, `HB` und `ERR` haben kein `seq`“), `631` (Festlegung 1, dieselbe Liste), `303` (`PING`: „Liegt nichts, folgt nur das `HELLO`“).
*   **Problem:** `LADER` hat kein `seq` und folgt dem `HELLO` (Zeile 138-146), aber die zwei Aufzählungen und die `PING`-Zeile nennen das nicht. `PING` ohne liegende Figur liefert danach `HELLO` **und** `LADER`.
*   **Vorschlag:** Die drei Stellen nachziehen: „`HELLO`, `HB`, `ERR` und `LADER` haben kein `seq`“, und `PING`: „folgt das `HELLO` (und bei `caps` `strom` die Zeile `LADER`), danach eine liegende Figur“.

### V11 · Niedrig · Beispieldatei nicht angepasst, gegen die Regel des Vertrags

*   **Fundstelle:** `reader-v1.md:6-7` (Gegenstück, Testgrundlage), `reader-v1.md:624-625` („die Beispieldatei wird im selben Schritt angepasst“), Commit-Meldung 3faab8b.
*   **Problem:** Die Beispieldatei fehlt für `LADER`, `caps` und die neuen Fehlerfälle. Das ist im Commit begründet (bestehende Parser-Tests lesen sie), aber im Vertrag selbst steht dazu nichts. Wer nur `reader-v1.md` liest, sieht den Verstoß gegen die eigene Regel nicht.
*   **Vorschlag:** In der Änderungsnotiz von `reader-v1.md` einen Satz: „`reader-v1-examples.txt` folgt mit AP E1-6; bis dahin gilt der Text.“ Beispiele für `HELLO` mit `caps`, ungültiges `caps`, `LADER in=0/1`, `LADER` ohne `HELLO` in E1-6 vorsehen.

### V12 · Niedrig · Alte „20 min“-Sätze ohne Hinweis stehen noch

*   **Fundstelle:** `core-interface.md:59` (Entscheidung O, ohne Markierung), `box-software.md:1349` („20 min Leerlauf“), `2922-2923` (AP 4.3: „Abschaltung nach 20 min“, nur der Satz hinten trägt den Hinweis; `test_idle.py`: „20-min-Leerlauf“), `2928` (Abnahme AP 4.3: „Nach 20 min Leerlauf wird heruntergefahren“).
*   **Problem:** Wer AP 4.3 abnimmt oder `test_idle.py` liest, bekommt 20 min und „am Lader nach der 20-min-Regel“, das jetzt falsch ist. `core-interface.md:59` ist ein datierter Eintrag, aber ohne den Verweis wie in Zeile 1170.
*   **Vorschlag:** Je „(seit Ein/Aus, 10.11.: 10 min, nur ohne Strom)“ anfügen; in 2928 die Abnahme umformulieren („nach 10 min ohne Strom“, „mit Strom nie“).

### V13 · Niedrig · Falscher Querverweis und mehrdeutiges „Punkt 9.9“

*   **Fundstelle:** `core-interface.md:208` („Abschnitt 6.5, Punkt 6f“; richtig ist 6g, `739`), `core-interface.md:1423-1426, 1460` und `mqtt-v1.md:10` („Punkt 9.9“ und „Abschnitt 9, Punkt 9“).
*   **Problem:** 6f ist das Zeitbudget. „Punkt 9.9“ liest sich wie Unterpunkt 9 (das ist „Ring“), gemeint ist Abschnitt 9, Punkt 9 als Ganzes.
*   **Vorschlag:** „6g“ und „Abschnitt 9, Punkt 9“ (ohne „9.9“), Unterpunkte als „Punkt 9, Nr. 7“ schreiben.

### V14 · Niedrig · „Fehlt `caps`, ist die Firmware 1.x“ widerspricht „`fw` und `proto` sind unabhängig“

*   **Fundstelle:** `reader-v1.md:106`, `core-interface.md:140` gegen `reader-v1.md:611-612`.
*   **Problem:** `caps` bestimmt die Fähigkeit, nicht die Hauptversion. Eine Firmware 1.5 kann `caps` haben, eine 2.0 vielleicht nicht. Der Satz „(Firmware 1.x)“ verleitet dazu, an `fw` zu prüfen.
*   **Vorschlag:** „…hat keine Fähigkeit (so verhält sich auch eine Firmware vor Schritt 1)“, und „der Dienst prüft nie `fw` auf Fähigkeiten, nur `caps`“.

### V15 · Niedrig · Verhalten in der „Strom unbekannt“-Phase und beim Herunterfahren nicht ganz festgelegt

*   **Fundstelle:** `core-interface.md:1152` („Lader an“ bei `HaUpdateAnstossen`), `1187` (Tiefstand „nicht am Lader“), `1200-1202`, `box-software.md:994-1001` (CUJ 23, „Strom kommt, während die Box herunterfährt“).
*   **Problem:** In den ersten 60 s ohne Wert ist offen, ob ein Akku-Tiefstand abschaltet (ohne Wert: „kein Strom“ oder „unbekannt löst nichts aus“?) und ob ein HA-Update „Lader an“ bekommt. Im Zustand `herunterfahren` wird der Strom nachgeführt, aber nichts über Rückmeldungen gesagt.
*   **Vorschlag:** „Unbekannt“ zählt für Tiefstand als „kein Strom“ (sicher für den Akku), für Update und Netz-Regel (Hotspot) als „nicht am Lader“. In `herunterfahren` gibt es keine Rückmeldung.

### V16 · Niedrig · Warnung bei „Widerspruch“ erzeugt Log-Lärm

*   **Fundstelle:** `core-interface.md:1196-1199`.
*   **Problem:** `pisugar-server` meldet schnell, der Leser entprellt (200 ms hoch, 1000 ms weg). Bei **jedem** normalen Andocken oder Abziehen gibt es kurz einen Widerspruch und damit eine WARNING.
*   **Vorschlag:** Widerspruch erst melden, wenn er länger als z. B. 5 s anhält (`STROM_WIDERSPRUCH_S`), sonst nur DEBUG.

### V17 · Niedrig · Reihenfolge der Hinweise und Ränder der Marke

*   **Fundstelle:** `data-model.md:158-160` (Boot-Kennung), `data-model.md:161` (`/run/tobibox/` bleibt bestehen), `core-interface.md:1189-1190` und `box-software.md:15`.
*   **Problem:** (a) Ist `lauf.json` fehlend oder unlesbar, ist die „gleiche Boot-Kennung“ unbekannt: Marke auswerten oder ignorieren? (b) Wer legt `/run/tobibox/` mit welchem Besitzer an (beide Dienste müssen schreiben und löschen), unklar (z. B. `RuntimeDirectory=` mit `RuntimeDirectoryPreserve=yes`). (c) Zu Schritt 2: Die Verweise („folgt mit Schritt 2“) sind an mehreren Stellen gleich gesetzt; keine Schritt-2-Inhalte vorhanden. Positiv, nur der Vollständigkeit halber.
*   **Vorschlag:** (a) Ohne lesbare Boot-Kennung: Marke auswerten (Einschalten annehmen). (b) Besitzer und Rechte im Vertrag nennen. (c) Keine Änderung.

---

## Prüfung nach Aufgabenpunkten

1.  **Widersprüche zum übrigen Text:** Kein Kurz-Modus, keine Start-Sync-Wiederholung, kein „Start am Lader“ mehr im geänderten Text; `START_WIEDERHOLUNG_*` sind aus der Konstantenliste entfernt. Übrig: alte 20-min-Sätze (V12), ein Zeilenverweis (V13), `seq`-Listen und `PING` (V10), Ring-Text (V6). Die Namensgebung `SyncStarten(grund="start_lader")` bleibt auch für das Andocken; Vertrag und Design nutzen sie gleich.
2.  **Entscheidungstreue:** R4, R8, R9, R10, R11 erfüllt (siehe Kurzfassung). Zu R4 ist der Pegel von `lader` = `hinweis` (nicht von R4 verlangt, aber stimmig). Zu R10 zusätzlich V5 (Rückfall unter „stumm“).
3.  **Rückwärtsverträglichkeit:** `reader-v1.md` Abschnitt 13 ist klar und in sich stimmig (neue Zeile darf Pflichtfelder haben; Zeilen vom Dienst nur bei `caps`). Risiken: V9 (ungültiges `caps`), V11 (Beispiele), V14. Alter Dienst gegen neue Firmware: ohne Befund. MQTT: V8.
4.  **Lücken:** V1 (Marke bei Dienst-Neustart und bei spätem Frühdienst; der Neustart selbst ist über die Boot-Kennung gut gelöst), V3, V4, V6 (Freigabe `led`), V7 (Uhr unsicher), V15 (Strom unbekannt, Tiefstand).
5.  **Schritt 2:** Keine Inhalte; nur Verweise.
