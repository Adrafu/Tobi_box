# Stufe B „Gehört“: Resolve (EGM Schritt 4)

Stand 16.11. · Grundlage: `design_draft.md` Rev. 1, `review_goldfisch_box.md` (G-B1 bis G-B16),
`review_goldfisch_ha.md` (G-H1 bis G-H8, G-M1 bis G-M17, G-N1, G-N2, G-L1 bis G-L7).
**(Tobias)** = Entscheidung Tobias, **(PL)** = Festlegung der Projektleitung. Eingearbeitet in `design_draft.md` Rev. 2.

## Entscheidungen Tobias (16.11.)

| Nr. | Frage | Entscheidung |
|---|---|---|
| R1 | Was zählt „Gehört“ zuerst? (Anlass G-M2, Hörbuch in Portionen) | **(Tobias)** „In Minuten tracken, nicht in Abspielungen“, auf Nachfrage: **Minuten zuerst, „Mal“ behalten.** Rangliste, Reihen und Diagramme nach Hörzeit; „Mal“ bleibt als Nebenspalte; „fertig“ bleibt |
| R2 | Wie lange darf eine Pause sein, damit es dieselbe Sitzung ist? (G-M2, G-L5) | **(Tobias)** **30 Minuten** (ersetzt die 5 Minuten aus Runde 8, Nr. 19) |
| R3 | Favoriten für die Familie oder je Benutzer? (B-F2) | **(Tobias)** **Ganze Familie** |
| R4 | Test-Box für die Abnahme (B-F3, G-B14, G-H8) | **(Tobias)** **Echte Box-Software am Mac als Test-Box**: Tobias legt für die Abnahme im Mosquitto ein Konto `boxsim` an und fügt in der Integration eine Test-Box hinzu; danach Daten der Test-Box löschen und beides wieder entfernen |

## Festlegungen der Projektleitung

| Befund | Schwere | Festlegung |
|---|---|---|
| G-B1 | hoch | **(PL)** Der Beobachter `gehoert.py` hört nicht auf `SitzungGeaendert` (intern, ohne Folge). Eingänge: `ZustandMelden` (Serie, Folge, Track, Modus), die Befehle `Pausieren(grund)` und `ZeigerSpeichern`, das Ereignis `FolgeZuEnde` (beendete Folge aus `z.ende`), `DienstEndet`, `Takt`, `PlayerPosition`. Er ist ein **reines Modul** mit eigenem Schritt (wie der Kern), damit Tests und Simulator dasselbe treiben |
| G-B2, G-M5 | mittel | **(PL)** Hörzeit = **Inhaltszeit aus dem Positionsfortschritt**, bei Box und Reinhören gleich: Summe der Zuwächse von `position_s` mit `0 < dp ≤ 2 × dt + 2`. Bei schnellerem Abspielen am Handy zählt die Länge des Inhalts („Was wird gezählt?“ sagt das) |
| G-B3, G-B13, G-B16c | hoch | **(PL)** Puffer ist **eine JSON-Datei `gehoert.json`** im vorhandenen Muster (`schema_version`, `schreibe_atomar`, Hintergrund-Schreiber wie `outbox`): `puffer_id`, `naechste_nr`, `zeilen`. Zeile, Nummer und „Quittiertes entfernen“ sind **ein** atomarer Schreibvorgang. Obergrenze **500 Zeilen**. Eintrag in data-model 1.6/1.7 |
| G-B4, G-H4 | hoch | **(PL)** Eindeutig ist eine Sitzung über ihre **`sitzung`-UUID** (Hauptschlüssel in HA). `nr` dient nur der Quittung und gilt je `puffer_id`; kein `UNIQUE(quelle, nr)`. Nie `OR REPLACE`: Einfügen mit `ON CONFLICT(sitzung) DO UPDATE … WHERE alt.ende = 'teilweise'`. `gehoert.json` gehört **nicht** in die Rückfall-Sicherung des Updates |
| G-B5, G-H3, G-B15d | hoch | **(PL)** Jede Sendung trägt `puffer_id`, `puffer_ab` (kleinste gehaltene `nr`) und `verworfen` (Zahl beim Überlauf verworfener Zeilen). HA quittiert die **höchste lückenlos gespeicherte `nr` ab `puffer_ab`**, nur steigend, **auch wenn alles schon bekannt war**; ungültige Zeilen quittiert HA trotzdem (Protokoll). Die Box ignoriert Quittungen mit fremder `puffer_id` |
| G-B6, G-M6 | hoch | **(PL)** Die offene Sitzung der Box steht im **ohnehin alle 30 s geschriebenen `resume.json`** (`sitzung_offen`); beim Start wird daraus eine abgeschlossene Zeile mit `ende = abbruch`. Kein zusätzlicher Schreibvorgang, Verlust höchstens 30 s. Offene Reinhör-Sitzungen schreibt HA alle 5 Minuten als `teilweise` |
| G-B7, G-B15e | hoch | **(PL)** **Handshake statt Reihenfolge:** Die Box sendet `gespielt` erst, wenn in diesem Lauf einmal `gehoert_quittung` von HA kam (auch `bis_nr = 0`). HA schickt diese Quittung beim `online` jeder Box, deren `status` eine Version mit B meldet. `gehoert_quittung` behandelt `ha.py` selbst (nicht der Kern): ohne Zeit- und `zeit_ok`-Prüfung, idempotent, nur steigend, nicht in den 50 gemerkten `id`s. Eine alte Integration bekommt so nie `gespielt` |
| G-B8 | mittel | **(PL)** Box sendet den Puffer bei Verbindung, bei `homeassistant/status online`, nach dem Handshake und höchstens alle 10 Minuten, solange Unquittiertes da ist. Nach einem Sitzungsende nur die **neue** Zeile |
| G-B9, G-M8 | mittel | **(PL)** Jede Zeile trägt `boot_id`, `beginn_boot_s` und `ende_boot_s` (Monotonsekunden). Wird die Uhr im selben Gerätestart gut, korrigiert die Box **alle** Zeilen dieses Starts im Puffer. Bleibt `zeit_ok = false`, rechnet HA mit `empfangen − (jetzt_boot_s − beginn_boot_s)`, wenn die Box beim Senden im selben Start ist; sonst gilt das Datum als **unbekannt**: die Sitzung zählt in „Alles“ und in der Rangliste, aber in keinem Tages- oder Stundendiagramm. Alle Dauern auf Monotonzeit |
| G-H1, G-B10, G-H2, G-M8 | hoch | **(PL)** Die Zeile trägt **`ende_um`** (Zeit der letzten gespielten Sekunde). „Mal“ (Wiedergabe) wird **nicht gespeichert**, sondern bei der Abfrage gerechnet (Fensterfunktion je Quelle und Folge nach `beginn`): zusammengelegt wird nur, wenn die vorige Sitzung höchstens **30 Minuten** (R2) vorher endete **und nicht** am Ende der Folge endete. Wiederholen nach „fertig“ ist immer ein neues Mal |
| G-B11, G-M4 | mittel | **(PL)** **fertig** = Sitzung endet am Ende der Folge **und** mindestens 80 % der Folgendauer wurden in dieser Wiedergabe gehört (ohne bekannte Dauer: mindestens 60 s). Die Box schickt `folge_dauer_s`, wenn bekannt; HA hat `dauer_s` aus der Medieninfo. Reinhören: nur `fertig: true` der Seite zählt, nicht die Hörstellen-Regel „Position ≥ Ende − 2 s“ |
| G-B12, G-M3 | mittel | **(PL)** Tabelle der Sitzungsgrenzen mit Vorrang (`herunterfahren`/`dienst_ende` vor `abbruch` vor `pause`; „Wechsel“ erst beim ersten Spielen der neuen Folge; Pause wegen `fehler`/`leser_unbekannt` wie jede Pause). Neuer Wert `dienst_ende` (Neustart des Dienstes ≠ Herunterfahren). Kurze Sitzungen (< 10 s) werden **nicht verworfen**, sondern gesendet und gespeichert: Hörzeit zählt immer; die 10-s-Schwelle gilt nur für „Mal“ (Summe der zusammengelegten Sitzungen) |
| G-B14, G-L6, G-H8 | mittel | **(PL)** Simulator = Box-Software am Mac mit Test-Konfiguration (R4) und Szenario-Werkzeug (simulierte Zeit, Vergangenheit `--tage 40`, `--seed`, Szenarien Wiederholen, Hörbuch, Neustart, Nummer zurückgesetzt, Lücke, Überlauf, offline). B1-Tests decken Absturz, abgeschnittene Datei, Doppelzustellung, Lücke, Überlauf, Uhrsprung, `puffer_id`-Wechsel und Handshake ab. `gehoert/loeschen` kennt `box:<id>` |
| G-B15 | niedrig | **(PL)** `nr` ist bei `teilweise` `null` (bedingt Pflicht, in der Tabelle). `teilweise` überschreibt nie eine Endzeile; verwaiste `teilweise` schließt HA nach 24 h als `abbruch`. SQLite: `journal_mode=TRUNCATE`, `synchronous=FULL` (wenige Schreibvorgänge; Quittung erst nach `COMMIT`) |
| G-B16, G-M9 | niedrig | **(PL)** Abschnitt 1 berichtigt. mqtt-v1 8: **„Empfänger ignorieren unbekannte `art`“ wird neu zugesichert** (heute nicht wahr). HA nimmt `gespielt` **vor** `box_ereignis_hinzu` ab und dedupliziert über `sitzung`, nicht über `id` |
| G-M7 | mittel | **(PL)** Technik-Zeilen nur bei **echtem Wechsel** gegen die letzte gespeicherte Zeile je Box; der erste `status` nach einem HA-Start wird nur verglichen, nicht als Wechsel geschrieben. Zeit: `ts` der Box bei `zeit_ok`, sonst Empfangszeit. Genauigkeit: Wechsel, die kürzer als der Mindestabstand des Status sind, fehlen (die Seite sagt das nicht, „etwa“ genügt) |
| G-H5 | hoch | **(PL)** Neuer kleiner Schritt **B2a vor B2: Messung am iPhone** (gesperrter Bildschirm, HA-App und Safari): Wie oft kommt `hoerstelle/set`? Dazu bekommt `hoerstelle/set` das Feld **`spielt`** (bool): War beim letzten Aufruf `spielt = true` und passt `dp ≤ 2 × dt + 2`, zählt auch `dt > 30`. Ergibt die Messung, dass gar nichts kommt, steht unter „Was wird gezählt?“: „Am Handy mit gesperrtem Bildschirm wird nur ungefähr gezählt“ |
| G-H6 | hoch | **(PL)** `hoerstelle/set` bekommt das Feld **`spieler`** (zufällige Kennung je Player-Instanz der Seite). HA führt je (Benutzer, `spieler`) eine offene Sitzung. Fehlt `spieler` (alte Seite), gilt eine Sitzung je Benutzer. Die Rate-Grenze bleibt je Benutzer, steigt auf 60 je Minute |
| G-H7 | hoch | **(PL)** `beginn` und `ende_um` als UTC-Sekunden; beim Einfügen zusätzlich `tag` (JJJJ-MM-TT) und `stunde` in der **Zeitzone von HA** (Spalten mit Index). Woche = heute und die 6 Kalendertage davor (Mitternacht Ortszeit), Monat 30, Jahr 365 Kalendertage, gleich für Zahlen und Diagramme. Eine Sitzung über Mitternacht zählt zum Tag ihres Beginns. Wechselt die Zeitzone von HA, bleibt das Raster alter Zeilen (dokumentiert) |
| G-M1 | mittel | **(PL)** Verschieben und Zusammenführen von Folgen/Serien schreiben die Zeilen mit (`UPDATE sitzungen SET serie, folge`); Umbenennen ändert nichts (ID bzw. Name der Folge bleibt). „Fertig 17/20“ zählt nur Folgen, die es heute gibt. Gelöschte Serien: in der Rangliste eine Zeile „Gelöscht“, damit die Summe stimmt |
| G-M10, G-M11 | mittel | **(PL)** Eine Verbindung im Executor mit `threading.Lock`; Aufnahme gesammelt (ein `COMMIT` je Sendung). Fähigkeit `gehoert` nur, wenn die Datenbank offen ist; `PRAGMA integrity_check` beim Start ins Protokoll. Leistung: Gesamtzeit des Befehls (nicht nur SQL) unter 100 ms bei 30 000 Zeilen, auch während eines Imports. Index `(beginn)` zusätzlich. Hinweis in `docs/betrieb/`: HA-Sicherungen enthalten die Hördaten |
| G-M12 | mittel | **(PL)** Befehl 50: `wer` auch **`alle_boxen`** (B-F1 damit erledigt: Knopf „Alle Boxen“ nach „Alle“); `zeitraum` und `von`/`bis` schließen sich aus; Zeitreihen (`tag`, `woche`, `monat`, `stunde`) liefern **lückenlose** Reihen aufsteigend, höchstens 400 Zeilen; `limit` gilt nur ohne Zeitschlüssel; Rückgabe nennt `zeitzone`, `von`, `bis`. Vorgabe-Sortierung **`sekunden`** (R1). Fehler `invalid_format`, `serie_nicht_gefunden`, `wer_ungueltig` |
| G-M13 | mittel | **(PL)** Ereignis-Themen `gehoert` (`geaendert`, gebündelt höchstens alle 5 s, ohne Inhalt) und `favoriten` (`geaendert` mit `serie_id`, `folge`, `an`) |
| G-M14 | mittel | **(PL)** `favorit/set`: Fehler `serie_nicht_gefunden`/`folge_nicht_gefunden`, höchstens 1 000 Favoriten, Wiederholung ohne Fehler, Mengen wie Listen-Änderungen. `favoriten/list` → `eintraege` mit `serie_id`, `folge`, `gesetzt_von {id, name}`, `gesetzt_am`; gelöschte fallen weg; gelöschter Benutzer = „unbekannt“. `folgen/list` bekommt Feld und Filter `favorit` |
| G-M15 | mittel | **(PL)** Befehl 52 entfällt (Befehl 50 mit `nach = ["serie"]`). Befehl 51 liefert Kurzformen wie `serien/list` plus `wer` und `zeit`. Sortierung `zuletzt_gehoert` in `serien/list` gilt **nur für Boxen** (wie die Reihe „Zuletzt auf den Boxen gehört“); `meist_gehoert` nach Hörzeit im letzten Jahr, alle Quellen. Nummern ohne Lücke weiterzählen |
| G-M16 | mittel | **(PL)** Export: CSV UTF-8 mit BOM, Trenner `;`, Spaltennamen deutsch, Zellen mit führendem `=`, `+`, `-`, `@` entschärft, Benutzer mit Namen aus HA; signierter Pfad **10 Minuten**, nur für den anfragenden Administrator (Benutzer in der Signatur, Prüfung auch beim Abruf) |
| G-M17 | mittel | **(PL)** Regel präzise: „Die **Stelle** zum Weiterhören ist privat; **dass** jemand etwas gehört hat und wie lange, sieht die Familie“ (Frage 23). Gäste-Konten sehen es auch (wie Frage 23); im Text der Einstellungen bei HA-Benutzern nichts Neues |
| G-N1 | mittel | **(PL)** Stern: Knopf im Kopf der Serienseite (`aria-pressed`, Wort im `aria-label`), je Folge im Menü als Text „Zu Favoriten“/„Aus Favoriten“; Ansage über die vorhandene Meldung; in Zeilen/Kacheln ein kleiner Stern mit `aria-label` „Favorit“ |
| G-N2 | mittel | **(PL)** `boxen/list` liefert je Box die Entitäts-ID des Akku-Sensors (aus der Registry); fehlt sie oder schließt der Recorder sie aus, zeigt die Karte keine Kurve. Diagramme wie 5.10 (`role="img"`, Tabelle). Löschen: erst `trocken: true` mit Anzahl („123 Einträge, nicht rückgängig“), dann Bestätigung mit Wort |
| G-L1 | niedrig | **(PL)** Gelöschter HA-Benutzer bleibt in „Alle“, erscheint in „Wer?“ als „Früherer Benutzer“, löschbar über `benutzer:<id>` |
| G-L2 | niedrig | **(PL)** Tabelle der Fähigkeiten in B0: `gehoert` (Befehle 50, 51, 53–55, Unterseite, Reihe, Sortierungen, Feld `zuletzt_gehoert_am`), `favoriten` (57, 58, Stern, Filter, Feld `favorit`) |
| G-L3 | niedrig | **(PL)** Größe neu: einige 10 MB im Jahr; keine Aufräumregel |
| G-L4 | niedrig | **(PL)** Reihen auf Start ohne Platzhalter, Fehler einzelner Reihen still; jsdom-Test |
| G-L5 | niedrig | erledigt durch R1 bis R4 und G-M12 |
| G-L7 | niedrig | **(PL)** Für Eltern heißt es überall „Hörzeit“, „Mal“, „fertig“ (eine Bezeichnung je Begriff in `texte.js`) |

## Runde 2: Review von Rev. 2 (`review_goldfisch_rev2.md`, G2-1 bis G2-22), alles (PL), eingearbeitet in Rev. 3

| Befund | Schwere | Festlegung |
|---|---|---|
| G2-1, G2-3, G-B4, G-B5, G2-19, G2-22 | hoch | **(PL)** Quittung **über die Sitzungs-UUIDs statt über Nummern**: HA antwortet mit der Liste der `sitzung`s, die es gespeichert hat oder schon kannte (auch ungültige, protokolliert); die Box löscht genau diese Zeilen. Keine `nr`, keine `puffer_id`, kein `puffer_ab`. Eine geklonte Karte oder ein zurückgespielter Stand kann so nichts Fremdes löschen. Überlauf: `status.gehoert_verworfen` (Gesamtzahl) → Technik-Zeile. Quittung nachlaufend: höchstens 2 s nach der letzten Zeile |
| G2-2, G2-21d | hoch | **(PL)** Handshake **über den Zustand**: Die Box setzt `status.gehoert_wartet = true` bei jedem Verbinden und bei `homeassistant/status online`. HA schickt auf **jeden** `status` mit `gehoert_wartet = true` eine Quittung mit leerer Liste; danach meldet die Box `false` und sendet. Retained alte Stände schaden nicht (Quittung ist idempotent). Eine alte Integration antwortet nie: die Box sendet nichts |
| G2-4, G2-12 | hoch | **(PL)** Die offene Sitzung steht **in `gehoert.json`** (`offen`), nicht in `resume.json`: ein atomarer Schreibvorgang für Zeile, Löschen und offene Sitzung. Geschrieben höchstens alle 2 Minuten während der Wiedergabe und beim Beginn einer Pause (Verlust höchstens 2 Minuten). Bei `herunterfahren` und `dienst_ende` wird **synchron** geschrieben, bevor abgeschaltet wird |
| G2-5, G2-9, G2-10 | hoch | **(PL)** „Mal“ und „fertig“ rechnet HA **beim Einfügen** je (Quelle, Serie, Folge) neu und speichert sie (`neues_mal`, `fertig`); nachgelieferte Zeilen rechnen nur ihre Gruppe neu. **fertig** = Sitzung endet am Ende der Folge **und** die Hörzeit dieser Quelle an dieser Folge **seit dem letzten fertig** ist mindestens 80 % der Dauer (so zählen Portionen über mehrere Tage). Ein Mal gehört zum Tag seines Beginns; Mal je Quelle; Dauer: HA füllt `folge_dauer_s` aus der Medieninfo, sonst der Wert der Box; ohne Dauer zählt fertig nur mit Ende der Folge und ≥ 60 s |
| G2-6 | hoch | **(PL)** Verwaiste `teilweise` schließt HA als `verwaist` (Box nach 24 h, Reinhören nach 30 min); eine spätere Endzeile überschreibt `teilweise` **und** `verwaist` |
| G2-7, G2-16 | hoch | **(PL)** `gespielt` trägt die aktuelle `boot_id` und `gesendet_boot_s`. Gleiche `boot_id` in Zeile und Nachricht ⇒ Beginn = Empfang − (`gesendet_boot_s` − `beginn_boot_s`). Sonst nimmt HA die Wanduhr der Zeile als **ungefähr**, wenn sie nach dem 1.1.2026 und vor dem Empfang liegt; sonst Datum unbekannt. `ende_um` = `beginn` + (`ende_boot_s` − `beginn_boot_s`). Ist `boot_id` nicht lesbar, erzeugt die Box eine zufällige je Dienststart |
| G2-8 | hoch | **(PL)** Befehl 50 mit Ausgabetabelle in Rev. 3: `woche` = ISO-Woche (Montag), `stunde` = Stunde des Tages 0 bis 23, `monat` = Kalendermonat; Reihenfolge der Schlüssel wie in `nach`; Beispiele |
| G2-11 | mittel | **(PL)** Senden bei jedem Handshake, bei jedem Sitzungsende (alle offenen Zeilen) und danach alle 10 Minuten, solange Unquittiertes da ist |
| G2-13 | mittel | **(PL)** Basislinie der Position neu bei Track-, Folgen- und `gen`-Wechsel und bei `dp ≤ 0`; `Abspielen` (mit `gen`) ist Eingang; keine Zeile bei Hörzeit 0; HA kappt `gehoert_s` auf `ende_boot_s − beginn_boot_s + 2` |
| G2-14, G2-15 | mittel | **(PL)** `spieler`: 8–64 Zeichen `[A-Za-z0-9_-]`, höchstens 5 offene Sitzungen je Benutzer (älteste wird `wechsel`). Mit `spielt = true` wird `dp` auf `2 × dt + 2` gekappt statt verworfen; Basislinie nach jedem Aufruf; Rechnung mit ungerundeter Position. Befehl 41 wird „Idempotent: nein (Wiederholung zählt keine Hörzeit doppelt)“. Zwei Fenster mit derselben Folge zählen doppelt (so in „Was wird gezählt?“) |
| G2-17 | mittel | **(PL)** Rev. 3 Abschnitt 3.6 und 6 nennen Pflicht, Typ und Grenze je Feld, Hülle von `gehoert_quittung` (`id`, `erzeugt`, `ttl_s` 3600 wie jeder Befehl; `ha.py` prüft Ablauf und Uhr dafür nicht), Zeilenaufbau von `gehoert.json` (= Felder von `gespielt`), Verhalten bei ungültiger Zeile (Zeile verwerfen, Protokoll), Export-Spalten, Ereignis-Themen, `LÖSCHEN` (auch `LOESCHEN`), `status.box_faehig` (eigener Name, nicht `faehig`) |
| G2-18 | mittel | **(PL)** Reste aus A in B3 (Backend) und B4 (Seite); Hinweis in `docs/betrieb/` in B6 |
| G2-20 | niedrig | **(PL)** `technik` ohne Aufräumregel; Index `(quelle, beginn)` |
| G2-21 | niedrig | **(PL)** In Runde 1 gelten die Befehlsnummern von Rev. 3 (50 bis 56); die Fähigkeit `gehoert_reinhoeren` entfällt auch im Vertragstext |

## Runde 3: Kurzprüfung von Rev. 3 (`review_goldfisch_rev3.md`): baureif mit Auflagen, alles (PL), eingearbeitet als Rev. 3.1 (Abschnitt 11 des Entwurfs)

| Befund | Festlegung |
|---|---|
| G3-1 | **(PL)** Schlüssel `(quelle, sitzung)`; ein Zwischenstand ersetzt nur Zeilen derselben Quelle |
| G3-2 | **(PL)** Löschmarke je Quelle: Nach `gehoert/loeschen` verwirft HA nachgelieferte Zeilen dieser Quelle, deren `ende_um` vor der Löschung liegt, und quittiert sie trotzdem |
| G3-3 | **(PL)** `neues_mal` trägt die erste Sitzung eines Mals; sie trägt auch `mal_zaehlt` (Summe des Mals ≥ 10 s), beim Einfügen neu gerechnet. Unbekanntes Datum: eigenes Mal; `fertig` rechnet die Hörzeit seit dem letzten fertig in Eingangsreihenfolge |
| G3-4 | **(PL)** Ersetzen: eine Endzeile (`ende` nicht `teilweise`, `abbruch`, `verwaist`) gewinnt immer; sonst gewinnt die Zeile mit der größeren Hörzeit. `verwaist` übernimmt `ende_um` des letzten Zwischenstands |
| G3-5 | **(PL)** Kein Zwischenstand, solange `gehoert_wartet = true`. Solange die Box wartet, meldet sie `status` alle 60 s neu. Ohne Fähigkeit `gehoert` in HA puffert die Box bis zur Grenze (500) und verwirft dann die ältesten (steht so im Vertrag) |
| G3-6 | **(PL)** Mehr als 400 Zeilen oder verbotene Kombination in `nach` → `invalid_format` |
| G3-7 | **(PL)** Reinhören mit `dt > 30`: Kappung `1,5 × dt + 2` (höchstes Tempo der Seite) |
| G3-8, G3-9 | **(PL)** so lassen: Etikett `abbruch` statt `dienst_ende` bei Neustart in der Pause ist ohne Folge für die Zahlen; ungefähres Datum ohne RTC steht so in „Was wird gezählt?“ nicht, ist aber im Vertrag als „ungefähr“ benannt |

## Freigabe (17.11.)

Tobias: „Geb ich frei“. Die Verträge aus `b0_entwurf/` gelten jetzt (`docs/protocol/mqtt-v1.md`,
`docs/protocol/ha-websocket-v1.md`, `docs/data-model.md`, Version bleibt 1); das Design Rev. 3.1 ist angenommen und
liegt als `docs/designs/gehoert.md`. Weiter mit B2a (Messung am iPhone mit Tobias), dann B1 ‖ B2.

## B2a: Messung am iPhone (17.11.)

HA-App am iPhone (Tobias), Reinhören, Bildschirm 01:50–01:54 gesperrt: `hoerstelle/set` kam lückenlos **alle 10 s**,
die Position lief von 25 auf 316 s ohne Sprung. Safari nicht gemessen: Tobias: „ich verwende safari nie“.
**(PL)** Der Hinweis „Am Handy mit gesperrtem Bildschirm wird nur ungefähr gezählt“ entfällt; `spielt` und die Kappung
bleiben wie entworfen (sie decken Browser ab, die einfrieren). B2 wird wie entworfen gebaut.

## B1/B2: offene Punkte der Agents und der Reviews (17.11., alles PL)

| Punkt | Festlegung |
|---|---|
| B1: Schranke `gehoert_s ≤ ende − beginn + 2` gegen „Inhaltszeit bei schnellerem Abspielen“ | ohne Folge: die Box spielt nie schneller ab |
| B1: erste Positionsmeldung einer Sitzung ist nur Basislinie (bis etwa 1 s fehlt) | so lassen |
| B1: Box sendet erst, wenn `gehoert_wartet = false` gemeldet ist; Quittung beendet den Handshake nur, wenn `true` wirklich veröffentlicht war | so (Vertrag 4.5) |
| B1: beim Trennen wartet die Box wieder; Hülle der Quittung nachsichtig geprüft | so lassen |
| B1: leere `serie`/`folge` | keine Sitzung, Warnung im Protokoll |
| B2: `spielt` fehlt (alte Seite) | gilt als spielend |
| B2: Abschnitt bis zum Pause-Aufruf zählt noch | so lassen (sonst fehlen je Pause bis 10 s) |
| B2: vorhandene Endzeile nur durch Endzeile mit mehr Hörzeit ersetzt | so lassen |
| B2: Löschmarke verwirft auch Zeilen mit unbekanntem Datum | so lassen (Gelöschtes kommt nicht wieder) |
| B2: Zwischenstände mit unbekanntem Datum werden beim nächsten Aufräumen `verwaist` | so lassen (Endzeile überschreibt) |
| B2: Box-Zeilen, die erst nach einem Verschieben eintreffen, zählen am alten Namen | so lassen; offene Reinhör-Sitzungen ziehen mit |
| B2: Favoriten gelöschter Folgen zählen zur Grenze 1000 | so lassen |
| B2: Obergrenzen gegen unsinnige Werte (Boot-Sekunden ≤ 10 Jahre, Dauer ≤ 7 Tage, `beginn` ≤ Empfang + 1 Tag) | Zeile ungültig, protokolliert, trotzdem quittiert |

## B3: offene Punkte des Agents (17.11., alles PL: so lassen)

Export-Pfad `/api/tobibox/export/<benutzer>/<quelle>` mit Signatur und Admin-Prüfung; ausgebaute Box mit alten Daten ist
in `wer` gültig; Zeilen mit unbekanntem Datum fehlen in Zeitreihen und `summe`, zählen in Ranglisten nur bei `alles`;
Raster Zeit × `wer` nimmt die Quellen, die der Filter zulässt; Sammelzeile gelöschter Serien mit `folgen_fertig` und
`folgen_gesamt` 0; Export-Spalten mit Anzeigenamen, „Mal neu“ nur beim zählenden Mal; in `folgen/list` gilt der Stern der
Folge; 3 Jahre bis zum gleichen Kalendertag, 400 Kalendertage einschließlich `bis`; Ränder in Befehl 52 mit wahrem
Beginn; Befehl 54 verwirft auch offene Reinhör-Sitzungen der gelöschten Personen; `einsortierung/bestaetigen` setzt auch
`teilweise` zurück; Reihenfolge in `hello.faehigkeiten` mit `hoerkopie` am Ende.

## B6: Abnahme (18.11.)

| Nr. | Befund | Entscheidung |
|---|---|---|
| BB1 | Papierkorb wird sehr lang; er leert sich nie von selbst | **(Tobias)** „Nach 30 Tagen“: Einträge, die länger als 30 Tage im Papierkorb liegen, löscht HA einmal am Tag endgültig. Vertragssatz „Nie endgültig“ wird angepasst |
| BB2 | Karte „Hördaten“ steht unter dem langen Papierkorb | **(PL)** Papierkorb-Karte zeigt die neuesten 5 Einträge plus „Alle … zeigen“; „Hördaten“ steht darüber |
| BB3 | Test-Box nach der Abnahme | **(Tobias)** aus der Integration nehmen, Mosquitto-Konto und lokale Dateien behalten |
