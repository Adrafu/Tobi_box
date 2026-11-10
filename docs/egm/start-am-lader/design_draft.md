# Start am Lader: Design-Entwurf (EGM Schritt 2)

*   **Datum:** 10.11.2026
*   **Status:** Entwurf zur Prüfung durch Goldfische. Nichts umgesetzt, kein Design, kein Vertrag, kein Code geändert.
*   **Grundlage:** `docs/egm/ladestation/software_folgen.md` (Abschnitt 10 gilt vor 1 bis 9), `resolve.md` (R8, R10),
    `docs/egm/ladestation/uebergabe_software.md`, `docs/designs/box-software.md`, `docs/protocol/*`, `docs/data-model.md`,
    `docs/betrieb/pisugar-wecker.md`, `docs/plan/stueckliste-und-psp.md` (Rev. 3.18, PSP 5.6.8), Code `box/src/tobibox/`.
*   **Hardware in einem Satz:** Eine einzige USB-C-Buchse am Ladeeingang des PiSugar 3 Plus, „Einschalten bei Strom am
    Eingang“ ist aktiv. Die Software kann Sockel, Kabel und Powerbank nicht unterscheiden (S10).
*   **Begriffe:** *Lader* = Strom am Eingang, aus irgendeiner Quelle (`battery_power_plugged`, `power.py:156-162`).
    *Rückmeldung* = Ring (Lauflicht, dann Ladestand blau) plus Ton `lader`, soweit erlaubt. *Kurz-Modus* = die 120 s nach einem
    Start am Lader (S2). Im Code heißt ein Tobie `figur`.

---

## 0. Kurzfassung

1. **Start am Lader** = echtes Einschalten (neue Kennung des Starts) **und** Strom am Eingang. Ein Neustart des Dienstes
   (Update, Absturz) zählt nicht. Das trennt die Boot-Kennung (Abschnitt 3), die schon da ist (`bootid.py`, `lauf.py`).
2. Neu in `idle`: ein **Kurz-Modus** (Merker im Zustand `leerlauf`, Frist 7 s + 120 s) und **Andocken bei laufender Box**
   (S8, 10 s Sperre). Die Wiederholung des Start-Syncs (6 mal alle 10 min) **entfällt**, sie widerspricht S2 (Konflikt K1).
3. Neu im Kern: Ton `lader` (Pegel wie `hinweis`), zwei Konfliktregeln, `Bereit.einschalten`. Ring: Helligkeit nach `ruhe`
   (5 % / 3 %), Lauflicht nachts aus. Kein neuer Befehl `LaderMelden` nötig (der Ring sieht `LaderGeaendert` schon).
4. **Reihenfolge beim Start ändert sich:** Die erste Messung von `power` (Uhr, Lader, Akku) kommt **vor** `Bereit`. Nur so
   kennt `ruhe` die Uhrzeit und wird nur ein Ton gespielt (Abschnitt 3.3).
5. **Update vormerken (S6):** Der Merker liegt **nur in Home Assistant**. HA schickt beim Andocken den normalen Befehl
   `update`. Das Box-Protokoll bleibt dafür unverändert (Abschnitt 4.5). Gebaut wird das mit Stufe 3b.
6. **Startschleife** (Box fährt mit Strom herunter und startet sofort wieder) ist die größte Unbekannte. Erst messen
   (Abschnitt 6.2). Notnagel in Software: Schleifenbremse (Abschnitt 3.4); die eigentliche Antwort wäre, R8 zurückzunehmen.
7. 20 vorgeschlagene Vertragsänderungen (core 11, mqtt 3, ha-websocket 3, data-model 3), 12 offene Fragen (Abschnitt 5).

---

## 1. Verhalten

Schreibweise wie die CUJs im Design. Es entstehen zwei neue CUJs: **CUJ 21** (Start am Lader) und **CUJ 22** (Andocken bei
laufender Box). Die Zeilen darunter sagen je Entscheidung, was die Box tut und was sich gegenüber dem Bestand ändert.

### 1.1 CUJ 21: Start am Lader (S1, S2, S3, S4, S5, S7)

*   **Given**: Die Box ist aus. Strom liegt am Eingang oder kommt dazu (Sockel, Kabel, Powerbank, Auto, Wecker, Knopf am
    Sockel). „Einschalten bei Strom“ startet den Pi.
*   **When**: Der Dienst meldet `Bereit` nach einem **echten Einschalten** (neue Boot-Kennung) und die erste Messung zeigt
    Strom am Eingang.
*   **Then**:
    1.  *Rückmeldung:* Ring Lauflicht 2 s, danach Ladestand blau 5 s; Ton `lader` statt `start` (ein Ton, nie zwei).
        Nachts (`ruhe` leiser oder stumm, oder Uhr unsicher): kein Ton, Ring gedimmt, kein Lauflicht.
    2.  *Sync:* `SyncStarten("start_lader")`, einmal. Die Netz-Regel entscheidet (Heimnetz immer, Hotspot mit Lader, S7).
    3.  *Kurz-Frist:* Nach der Rückmeldung (7 s) läuft eine Frist von 120 s. Läuft ein Sync oder Update, wartet die Box,
        danach noch 30 s Nachlauf. Danach: Zeiger speichern, Herunterfahren.
    4.  *Abbruch des Kurz-Modus* (danach gilt die normale 20-min-Regel, Zähler ab diesem Moment): Ein Tobie liegt oder spielt;
        Hauptknopf kurz; ein angenommener HA-Befehl (Sync, Update, Lernmodus). **Nicht:** Weiter, Zurück, Drehregler,
        Kopfhörer, Abziehen.
    5.  *Liegt beim Start schon ein Tobie* (S4), spielt er wie bisher (CUJ 20). Der Ton `lader` kommt zuerst, das Hörspiel
        folgt (Entscheidung L). Der Kurz-Modus endet sofort. Nachts schützen die Leise-Zeiten.
*   **Ausnahme Dienst-Neustart:** `Bereit.einschalten = False`. Es gilt CUJ 20 (Ausnahme G) und alles wie bisher, aber
    **ohne** Start-Sync, ohne Kurz-Modus, ohne `lader`-Ton. Der Ton `start` klingt wie bisher.

| Entscheidung | Bestand (Beleg) | Änderung |
|---|---|---|
| **S1** jeder Start mit Strom ist Start am Lader, kein Merker | `idle` prüft bei `Bereit` und Lader nur den Sync, ohne Unterscheidung Einschalten / Dienst-Neustart (`idle.py:168-178`). `Bereit` hat keine Felder (`events.py:291-293`). | `Bereit.einschalten` (Abschnitt 3). Start-Sync und Kurz-Modus nur bei `einschalten`. **Folge:** Ein Dienst-Neustart am Lader startet keinen Start-Sync mehr; der Takt holt ihn nach (`sync.py:176-177, 226`: nach dem Start ist `letzter_start` leer, der erste `takt` startet, `app.py:531-536`). |
| **S2** 120 s, Sync hält wach | `LEERLAUF_S = 1200` (`idle.py:57`); Sync, Update, Lernmodus halten (`idle.py:114-116`). | Frist `LADER_RUECKMELDUNG_S` (7) + `LADER_KURZ_S` (120) ab Rückmeldung. Das „ab Ende der Rückmeldung“ aus S2 ist so umgesetzt, weil `idle` das Ende des Rings nicht sieht. Neu: `LADER_NACHLAUF_S` (30), siehe 4.5. |
| **S3** was den Kurz-Modus beendet | Bedienung setzt den Zähler zurück: Hauptknopf kurz, Weiter, Zurück, Drehregler, Kopfhörer (`idle.py:186-190, 244-250`). HA-Befehle tun es nicht (`idle.py:12-14`). | Im Kurz-Modus beendet nur Hauptknopf kurz; Weiter, Zurück, Drehregler, Kopfhörer tun **nichts** (auch kein Zähler-Reset). Tobie und angenommene HA-Befehle beenden ihn; **Bruch** mit „HA setzt den Zähler nicht zurück“: Beim Verlassen des Kurz-Modus beginnen die 20 min neu (F9). |
| **S4** liegender Tobie spielt | CUJ 20, `lauf.json` nur für Tobie (`lauf.py:23-38`). | Unverändert. Nur Ton und Reihenfolge (Rückmeldung, dann Hörspiel). |
| **S5** Leise-Zeiten | `leiser`: Ring unverändert. `stumm`: alles ×0,4 (`led.py:64, 280-283`). Lauflicht 25 % bei jedem `Bereit` (`led.py:171-179, 233-234`). Konfliktregel 2 ersetzt Töne unter „stumm“ durch `hinweis` (`core.py:44, 116-121`). | Siehe 1.3. |
| **S7** Hotspot | `syncregel.py:29-32`: Hotspot mit Lader oder Akku über 50 %. | **Keine Codeänderung.** Wirkung: Jede Powerbank ist Lader, der Start-Sync im Auto läuft über den Handy-Hotspot, ohne Datenlimit (Entscheidung C, Design Zeile 1732). Tobias nimmt das in Kauf. Nur Texte anpassen. |
| **S10** kein Taster | – | Nichts. Texte sprechen von „Strom am Eingang“. |

### 1.2 CUJ 22: Andocken bei laufender Box (S8, S9)

*   **Given**: Die Box läuft (Dienst bereit), Strom kam bisher nicht oder ist weggefallen.
*   **When**: Strom kommt dazu (`LaderGeaendert(true)` nach der ersten Messung), und der letzte Wechsel liegt mindestens
    10 s zurück.
*   **Then**: Ring zeigt Ladestand blau 5 s (wie heute, `led.py:237-241`). Ton `lader`, wenn weder ein Hörspiel läuft (S9) noch
    der Lernmodus. Sync-Prüfung `SyncStarten("start_lader")`, wenn kein Sync und kein Update läuft (S8). Kein Kurz-Modus (F5), der
    Leerlauf-Zähler läuft unverändert weiter; Andocken ist keine Bedienung.
*   **Entprellen (S8, 10 s):** Die Sperre rechnet vom **letzten Wechsel** (auch vom Abziehen). Die erste Rückmeldung kommt sofort.
    Wackelt der Kontakt, bleibt es still, bis 10 s Ruhe war. `LaderGeaendert` selbst bleibt unverzögert und richtig (Hotspot- und
    Update-Regel brauchen den echten Wert).
*   **Abziehen:** Kein Ton. Der Ring zeigt den Akku 5 s in Ampelfarben (heute schon so, `led.py:161-168, 237-241`). Der Tiefstand
    ist wieder scharf (`power.py:291-309`). Der Kurz-Modus läuft weiter (F4).

| Entscheidung | Bestand (Beleg) | Änderung |
|---|---|---|
| **S8** Sync prüfen beim Andocken | Nur einmal nach `Bereit` (`idle.py:170-172`; Test `test_idle.py:325-330`: spätes Einstecken zählt nicht). | Neu: `letzter_wechsel`, Sperre `LADER_SPERRE_S` (10). Der Test oben wird umgekehrt. |
| **S9** Hörspiel läuft: nur Ring | Ein Ton hielte MPD kurz an (Entscheidung L, `app.py:667-690`). | `idle` gibt `TonSpielen("lader")` nur aus, wenn weder `belegt` noch `lernt` gilt. Der Ring ist immer dabei. **Erweiterung:** auch bei Lernmodus kein Ton (F10). |
| Erkennung | `power` fragt alle 10 s (`power.py:209`, `config.py:222`). | Eigene Lader-Abfrage alle 2 s (`[strom] lader_intervall_s`), Akku bleibt bei 10 s. Sonst käme die Rückmeldung bis zu 10 s nach dem Andocken. Messen (6.2). |

### 1.3 Leise-Zeiten und Helligkeit (S5)

| `ruhe` | Ton `lader` | Ring, Akku-Anzeige | Lauflicht bei `Bereit` |
|---|---|---|---|
| `normal`, Uhr sicher | spielt, Pegel wie `hinweis` | 15 % (heute `led.py:168`) | wie heute, 25 % |
| `leiser` | entfällt | **5 %** (neu) | **aus** (neu) |
| `stumm` | entfällt | **3 %** (statt 15 % × 0,4 = 6 %) | **aus** |
| Uhr unsicher (`zeit_ok` falsch) | entfällt | 5 % | aus |
| Gute Nacht läuft (`gute_nacht` ≠ `aus`) | entfällt (es spielt, S9) | 5 % | – |

*   Die S5-Werte gelten für die **Akku-Anzeige** (Start, Andocken, Abziehen). Andere Zustände bleiben wie im Bestand
    (`stumm` ×0,4). Neu ist, dass auch `leiser` dimmt.
*   Die Regel „kein Ton“ steht im Kern (Konfliktregel 2a, Abschnitt 4.1), nicht im Ring.
*   **Rundung (Konflikt K6):** `Ring.apa102_rahmen` rundet die 5-Bit-Stufe ab: `hell = int(helligkeit * 31 / 100)`
    (`led.py:112-119`). 5 % ergibt Stufe 1 (3,2 %), **3 % ergibt Stufe 0, also dunkel**. Vorschlag: Stufe mindestens 1, solange
    die Helligkeit über 0 liegt; darunter über die Farbwerte skalieren. Gleicher Fehler heute bei Gute Nacht unter „stumm“
    (3 bis 8 % × 0,4).

### 1.4 Update vormerken (S6)

*   **Given**: Tobias hat in HA „Update beim nächsten Andocken“ für eine Box vorgemerkt.
*   **When**: Die Box meldet sich nach dem Andocken (Start am Lader) und HA sieht `online`, `lader`, `netz = home`, `zustand` ≠
    `spielt`, `sync.zustand` ≠ `laeuft`.
*   **Then**: HA sendet den normalen Befehl `update` (300 s). Die Box prüft die Bedingungen wie bisher (`idle.py:153-165`); der
    Befehl beendet den Kurz-Modus. Wurde er angenommen, ist der Merker verbraucht. Details und Alternative: 4.5.
*   **Bestand:** Das Update selbst gibt es noch nicht (`app.py:612-620`: `befehl_abgelehnt` „Update kommt mit Stufe 3b“).

### 1.5 Abstimmung mit dem Bestand: Zustände nebeneinander

| Lage beim Start oder Andocken | Verhalten |
|---|---|
| Tobie liegt beim Start (CUJ 20) | Ton `lader`, dann Hörspiel (S4). Kurz-Modus endet. Unter „stumm“: `gehalten`, `hinweis`-Ton für „erkannt“ (CUJ 15), kein `lader`. |
| Entscheidung O (Leerlauf zählt mit liegendem Tobie, `idle.py:6-10`) | Nach dem Ende des Kurz-Modus durch einen Tobie gilt die 20-min-Regel mit O: Liegt er in `pausiert` / `gehalten`, geht die Box nach 20 min aus. |
| Gute Nacht | Läuft sie, spielt die Box (S9): nur Ring, 5 %. Nach dem Ausblenden: normaler Leerlauf. |
| Lernmodus läuft | Kein Ton, Ring-Anzeige, Sync darf. Der Start des Lernmodus beendet einen Kurz-Modus (`LernenGeaendert`). |
| Update läuft | Andocken: nur Ring. Kein Sync (nie parallel zum Update, Design Zeile 1721). |
| Tiefstand, Herunterfahren schon beschlossen | Nichts (`idle.py:329-355` führt nur nach). Mit R8 startet die Box danach wieder, falls der PiSugar bei Strom neu startet (Startschleife, 3.4). |
| Wecker (`pisugar-wecker.md`, Abschnitt 4) | Gilt nach S1 als Start am Lader (F3). |
| Knopf am Sockel | Gleich behandelt (S1, Übergabe). Der Druck, der die Box einschaltet, kommt nicht als `Hauptknopf` an; das Kind muss nach dem Start ein zweites Mal drücken oder einen Tobie auflegen. |

---

## 2. Tabelle „Strom / Leerlauf“ (vollständige neue Fassung)

Ersetzt die Tabelle im Design, Zeilen 1380-1397. Zustände: `aktiv`, `leerlauf` (Zähler läuft; Merker `kurz` = Kurz-Modus),
`herunterfahren`. `kennzeichen()` und `ZustandMelden.strom` bleiben unverändert (der Merker ist kein vierter Zustand).
Zeilen mit **neu** oder **geändert** sind Abnahmetests (Stufe 4).

| # | Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|---|
| 1 | `aktiv` | keine Wiedergabe (ein liegender Tobie zählt nicht, Entscheidung O) | Zähler 20 min starten | `leerlauf` |
| 2 | `leerlauf` | Wiedergabe → Zähler verwerfen; Bedienung (Hauptknopf kurz, Weiter, Zurück, Drehregler, Kopfhörer) → Zähler neu. **geändert:** *im Kurz-Modus* gilt das nur für Hauptknopf kurz (Zeile 12); die übrigen vier tun nichts | wie bisher | `aktiv` / `leerlauf` |
| 3 | `leerlauf` | Zähler um; Sync, Update oder Lernmodus läuft, oder ein Sync ist offen | warten; nach Ende sofort prüfen (Lernmodus: Zähler neu). **geändert:** *im Kurz-Modus* nach Ende von Sync oder Update noch `LADER_NACHLAUF_S` | `leerlauf` |
| 4 | `leerlauf` | Zähler um, nichts läuft | Zeiger speichern, Herunterfahren (Grund `leerlauf`; Protokoll `kurz=true/false`) | `herunterfahren` |
| 5 | `aktiv`, `leerlauf` | Hauptknopf lang | Zeiger speichern, Herunterfahren | `herunterfahren` |
| 6 | `aktiv`, `leerlauf` | Akku-Tiefstand (nicht am Lader) | Sync abbrechen, Ton `akku_leer`, Zeiger speichern, Herunterfahren | `herunterfahren` |
| 7 | `herunterfahren` | `HerunterfahrenFehlgeschlagen` (Rückgabecode, Frist 60 s) | Protokoll, Hinweis an HA, Zähler neu, **Kurz-Modus aus** | `aktiv`, `leerlauf` |
| 8 | `herunterfahren` | Simulation, 10 s | Zähler neu, Kurz-Modus aus | `aktiv`, `leerlauf` |
| 9 | **neu** beliebig außer `herunterfahren` | `Bereit` mit `einschalten` **und** erste Messung `am_lader = true` (beide Reihenfolgen) | Kurz-Modus an, Frist = jetzt + `LADER_RUECKMELDUNG_S` + `LADER_KURZ_S`; `TonSpielen("lader")`, wenn nicht `belegt` und nicht `lernt`; `SyncStarten("start_lader")`; `letzter_wechsel` = jetzt | `leerlauf` (Merker `kurz`) |
| 10 | **neu** `leerlauf` (kurz) | `SitzungGeaendert` mit `figur_liegt` oder `spielt` oder `unbekannt` | Kurz-Modus aus; Zähler 20 min ab jetzt, falls nicht belegt | `aktiv` / `leerlauf` |
| 11 | **neu** `leerlauf` (kurz) | angenommenes `HaSyncAnstossen`, `HaUpdateAnstossen`, oder `LernenGeaendert(aktiv=true)` (abgelaufen oder abgelehnt zählt nicht; `HaLernmodusAbbruch` nie) | Kurz-Modus aus; Zähler 20 min ab jetzt | `leerlauf` |
| 12 | **neu** `leerlauf` (kurz) | `Hauptknopf` kurz | Kurz-Modus aus; Zähler 20 min ab jetzt | `leerlauf` |
| 13 | **neu** `leerlauf` (kurz) | `LaderGeaendert(false)` | Frist läuft weiter; Tiefstand ist wieder scharf | `leerlauf` (kurz) |
| 14 | **neu** nicht `herunterfahren`, nach dem Start | `LaderGeaendert(true)` nach `false`, `jetzt − letzter_wechsel ≥ LADER_SPERRE_S` (S8) | `TonSpielen("lader")`, wenn nicht `belegt` und nicht `lernt`; `SyncStarten("start_lader")`, wenn kein Sync / Update läuft oder offen ist. Zähler und Kurz-Modus unverändert | unverändert |
| 15 | nicht `herunterfahren` | jeder `LaderGeaendert` | `letzter_wechsel` = jetzt | unverändert |
| 16 | beim Start | `Bereit` mit `einschalten = false` (Dienst-Neustart, Startschleife) | nichts am Strom; kein Start-Sync, kein Kurz-Modus, kein `lader`-Ton | `aktiv` |
| 17 | **entfällt** | Wiederholung des Start-Syncs alle 10 min, höchstens 6-mal (Plan 3.16) | – | – |

Anmerkungen:

*   Zeile 9 braucht beide Eingänge: `Bereit` (mit `einschalten`) und die **erste** `LaderGeaendert`. Kommt der Lader erst nach
    `Bereit` (Messung > `STROM_START_WARTEN_S`), gilt Zeile 9 trotzdem, aber **ohne Ton** (der Ton `start` hat schon geklungen,
    kein zweiter Ton).
*   Zeile 9 setzt die Frist neu, auch wenn `idle` schon in `leerlauf` mit 20 min stand (der Zähler beginnt mit dem ersten
    Ereignis, `idle.py:213-215`).
*   Zeile 7 und 8: Ein gescheitertes Herunterfahren im Kurz-Modus lässt die Box normal weiterlaufen (20 min), nicht in
    Dauerschleife.

**Neue Zeilen für die Konflikt-Tabelle** (Design Zeilen 1402-1416):

| Situation | Erwartetes Ergebnis |
|---|---|
| Start am Lader, nichts passiert | 7 s Rückmeldung, Start-Sync, nach 127 s Herunterfahren |
| Start am Lader, Sync läuft über 127 s | Die Box wartet, nach dem Sync-Ende noch 30 s, dann Herunterfahren |
| Start am Lader, Tobie wird aufgelegt | Kurz-Modus aus, Hörspiel, später 20-min-Regel |
| Start am Lader, Weiter, Zurück, Drehregler, Kopfhörer | Nichts; die Frist läuft |
| Start am Lader ohne Netz (Auto) | Der Start-Sync endet mit `netz_weg`, die Box fährt nach 127 s herunter; **keine** Wiederholung (K1) |
| Dienst-Neustart am Lader | `start`-Ton wie bisher, kein Start-Sync, 20-min-Regel |
| Andocken, Hörspiel läuft | Nur Ring |
| Andocken, Kontakt wackelt (Wechsel in weniger als 10 s Abstand) | Eine Rückmeldung bei der ersten Verbindung, danach still |
| Andocken im „stumm“- oder „leiser“-Fenster oder bei unsicherer Uhr | Kein Ton, Ring gedimmt, kein Lauflicht |

---

## 3. Start oder Dienst-Neustart (Entscheidung G)

### 3.1 Vorschlag: Boot-Kennung auf jedem Start festhalten

*   **Bestand:** `bootid.lese()` liefert die Kennung des Geräte-Starts (`bootid.py:28-39`). `lauf.json` hält `{boot_id, uid}`
    und wird **nur geschrieben, wenn ein Tobie wechselt oder der Dienst endet** (`lauf.py:73-82`, `app.py:523-524`), und beim
    Herunterfahren gelöscht (`app.py:587-589`). Beim Start sagt die Datei nur etwas über den Tobie (`lauf.py:23-38`).
    **Ohne Tobie gibt es keine Datei, ein Dienst-Neustart ist nicht erkennbar.** Das genügt bisher, weil CUJ 20 nur den Tobie
    betrifft.
*   **Neu:** `app.starte` schreibt `lauf.json` mit der aktuellen `boot_id` **sofort nach dem Verarbeiten von `Bereit`**
    (Tobie-Feld wie bisher, `neustart_uid` bleibt erhalten, sonst `null`). Beim Start vergleicht `app` **vor** dem Schreiben:
    `dienst_neustart = (Datei lesbar und Datei.boot_id == aktuelle boot_id und boot_id nicht None)`.
    `Bereit(einschalten = not dienst_neustart and not schleife)`.
*   **Ergebnis je Fall:**

| Fall | Datei vor dem Start | `boot_id` | `einschalten` |
|---|---|---|---|
| Andocken, Knopf, Wecker (Box war aus, Dienst sauber beendet) | gelöscht (`app.py:589`) | – | **true** |
| Stromausfall, leerer Akku | alt, andere Kennung | verschieden | **true** |
| Absturz, `systemctl restart`, Update-Neustart | da, gleiche Kennung | gleich | **false** |
| Erster Start nach Installation | fehlt | – | **true** |
| Kennung nicht lesbar (`bootid.lese` = `None`) | egal | – | **true** (Konvention `bootid.py:6`, `lauf.py:9`) |

*   **Warum Boot-Kennung und nicht „Uptime klein“ oder Merker „am Lader beim Ausschalten“?** Die Kennung ändert sich nur bei
    echtem Einschalten (`bootid.py:3-4`) und ist schon getestet (`test_bootid_lauf.py`). Uptime irrt bei einem Absturz kurz
    nach dem Hochfahren. Der Merker „am Lader beim Ausschalten“ taugt nicht (`software_folgen.md`, Abschnitt 1: Box im Aus
    abgehoben und wieder angedockt ist nicht zu unterscheiden).
*   **Schreibzeitpunkt:** Nach `Bereit`, nicht davor. Stürzt der Dienst vor `Bereit` ab, zählt der nächste Start noch als
    Einschalten (die Rückmeldung kommt dann nachträglich, das ist unschädlich).

### 3.2 Was bei `einschalten = false` gilt

`start`-Ton und Lauflicht wie heute (`session.py:844-845`, `led.py:233-234`). **Gegenüber dem Bestand entfällt nur der
Start-Sync** (`idle.py:168-178`); der Takt holt ihn nach (`sync.py:176-177, 226`). Wer nach einem Absturz am Lader die ganze
Rückmeldung nicht will, bekommt sie so auch nicht (die Frage aus dem Auftrag: **nicht gewollt**).

### 3.3 Reihenfolge beim Start und ein Ton statt zwei (Entscheidung L)

*   **Bestand:** `power` startet **nach** `Bereit` (`app.py:924, 937, 944-955`). Zum Zeitpunkt `Bereit` ist die Zeitquelle auf dem
    Pi `unbekannt` und `zeit_ok` falsch (`app.py:225-229`, `net.py:202-216`), `ruhe` also falsch; `session` spielt `start`
    sofort (`session.py:844-845`); der Lader kommt erst Millisekunden später (`power.py:250-268`).
*   **Problem:** Ohne Änderung klingen `start` und danach `lader`; nachts kennt `ruhe` die Zeit noch nicht.
*   **Vorschlag:** `app.starte` ruft die erste Messung (`Power.start()`: RTC, Zeitquelle, Lader, Akku) **vor** `Bereit`, mit
    Frist `STROM_START_WARTEN_S` (2 s; fällt `pisugar-server` aus, geht `Bereit` ohne Messung raus). Dann kennen `quiet` und
    `idle` Zeit und Lader, wenn `Bereit` ankommt. In diesem einen Schritt gibt `session` `start` und `idle` `lader` aus;
    **Konfliktregel 1a** lässt dann nur `lader` stehen (und vor Regel 2 entfernt sie `start`, damit unter „stumm“ nicht der
    `hinweis`-Ersatz klingt). Ohne Strom oder bei Dienst-Neustart bleibt `start`.
*   **Alternative:** `session` kennt den Lader (neue Kopplung, Test-Aufwand) oder `lader` kommt nach `start` (zwei Töne).
    Beides schlechter.

### 3.4 Startschleife und Rückfall

*   **Risiko:** Fährt die Box mit Strom herunter (Ende des Kurz-Modus, Hauptknopf lang, 20-min-Regel am Sockel) und der PiSugar
    startet bei „Strom liegt an“ **pegelabhängig** neu, läuft sie alle ~2,5 min: Start, Ton, 120 s, Aus. Ist er
    **flankenabhängig** („Strom kommt neu“), bleibt sie aus. Nicht belegt (`software_folgen.md`, Abschnitt 1); T5, Messung 1 in 6.2.
*   **Software-Notnagel (Schleifenbremse):** `app` schreibt beim Befehl `Herunterfahren` die Datei `ende.json`
    `{"wall": <float oder null>, "am_lader": <bool>}` (neben dem Löschen von `lauf.json`, `app.py:587-589`). Beim Start gilt:
    `schleife = am_lader_im_marker und zeit_ok und 0 ≤ jetzt.wall − ende.wall < SCHLEIFE_S (300 s)`. Dann `einschalten = false`
    (also keine Rückmeldung, kein Kurz-Modus, `start`-Ton wie Dienst-Neustart) und einmal `EreignisSenden("fehler",
    baustein="power", code="startschleife")` an HA. Die Box läuft dann bis zur 20-min-Regel, die Schleife wird ~20 min lang statt
    2,5 min. Das ist ein **Notnagel**, keine Lösung.
*   **Die eigentliche Antwort** wäre, am PiSugar „Einschalten bei Strom“ wieder abzuschalten (R8 zurücknehmen, Plan Punkt 3
    und PSP 5.6.5 gelten dann wieder) und den Wecker nur über den RTC-Alarm zu nutzen. Das entscheidet Tobias nach der
    Messung (F2). Lesbar bleibt die Schleifenbremse zur Sicherheit im Code, solange die Messung nicht gemacht ist.
*   **Schutzwirkung:** Ein Mensch, der die Box mehr als 5 min nach dem Ausschalten wieder andockt, löst die Bremse nicht aus.
    Wer sie sofort wieder andockt (Abheben und Aufsetzen), bekommt keine Rückmeldung: Das ist hinnehmbar und sehr selten.

---

## 4. Vorgeschlagene Vertragsänderungen (alt → neu)

Alle additiv, `v` und `schema_version` bleiben. Wortlaut als Vorschlag. Nummern C = `core-interface.md`, M = `mqtt-v1.md`,
H = `ha-websocket-v1.md`, D = `data-model.md`. Tobias gibt frei (`CLAUDE.md`).

### 4.1 `core-interface.md` (11 Änderungen)

**C1, 3.3 `Bereit`** (Zeile 194). Felder `–` → `einschalten: bool = True`. Bedeutung, alt: „… Bei `Bereit` spielt der Kern den
Start-Ton (CUJ 20 …)“. Neu: „… `einschalten` ist `True`, wenn die Box eingeschaltet wurde (neue Kennung des Starts, siehe
`data-model.md` `lauf.json`) und keine Startschleife erkannt ist; `False` bei Neustart des Dienstes. Bei `Bereit` spielt
`session` den Ton `start` (CUJ 20 …). Ist `einschalten` wahr und die Box am Lader, spielt `idle` stattdessen `lader` (6.2,
Regel 1a). Vor `Bereit` hat `app` die erste Messung von `power` geliefert (`ZeitquelleGeaendert`, `LaderGeaendert`,
`AkkuStand`), höchstens `STROM_START_WARTEN_S`; sonst kommen sie danach.“

**C2, 3.6 `LaderGeaendert`** (Zeile 227), Bedeutung leer → „Strom liegt am Eingang des PiSugar an (`true`) oder nicht (`false`),
aus **irgendeiner** Quelle: Sockel, Kabel, Powerbank, Auto-Buchse. Die Box kann die Quellen nicht unterscheiden. Die erste
Messung nach dem Start ist auch eine Änderung (von „unbekannt“). Das Ereignis ist unverzögert; die Sperre von 10 s für Ton
und Sync-Prüfung liegt in `idle` (9.9).“

**C3, 3.6 `SyncAbgebrochen`** (Zeile 234). Streichen: „keine Wiederholung am Lader, Abschnitt 9, Punkt 9“ (die Wiederholung
entfällt, K1).

**C4, 4 `TonSpielen`** (Zeile 316). Literal um `"lader"` erweitern: „… `"akku_leer"`, `"lader"`, `"pruef_ok"` …“. Zusatz:
„`lader`: Strom am Eingang erkannt (Start am Lader, Andocken); Datei `box/sounds/lader.wav`.“

**C5, 6.2 Konfliktregel 2** (Zeilen 468-470). Zusatz **Regel 2a**: „Ist `quiet` im Zustand `leiser` oder `stumm`, oder ist
`jetzt.zeit_ok` falsch, wird jeder `TonSpielen("lader")` **entfernt** (nicht durch `hinweis` ersetzt).“ Dazu bekommt
`_konflikte` die Uhr (`core.py:110`).

**C6, 6.2 neue Konfliktregel 1a** (vor Regel 2 anzuwenden): „Enthält die Ausgabe `TonSpielen("lader")`, wird `TonSpielen("start")`
entfernt. (Ein Ton beim Einschalten am Lader.)“ Reihenfolge wichtig: 1a läuft vor 2 und 2a, sonst klänge unter „stumm“ der
`hinweis`-Ersatz des Starttons.

**C7, 9 Punkt 9** (Zeilen 1123-1152). Der Absatz „Start am Lader“ (Zeilen 1146-1152: Wiederholung, 10 min, 6-mal) wird ersetzt
durch den Text aus 1.1, 1.2 und Abschnitt 2 (Kurz-Modus, Andocken, Sperre). Der Absatz „Bedienung setzt den Zähler zurück“
(Zeilen 1123-1126) bekommt: „Im Kurz-Modus gilt das nur für Hauptknopf kurz.“ Die Zeile „Bedingungen für `HaUpdateAnstossen`“
(Zeile 1109) bekommt: „‚Lader an‘ heißt Strom am Eingang aus irgendeiner Quelle.“ (Klarstellung)

**C8, 5.2 Tabelle der Teilautomaten, Zeile `idle.py`** (Zeile 359). Zustände: `aktiv`, `leerlauf`, `herunterfahren` (+ Merker
`kurz` in `leerlauf`, kein eigener Zustand). Eingänge: unverändert (`Bereit`, `LaderGeaendert`, `Hauptknopf` kurz, `Weiter`,
`Zurueck`, `LautstaerkeDrehen`, `Kopfhoerer`, `SitzungGeaendert`, `LernenGeaendert`, `HaSyncAnstossen`, `HaUpdateAnstossen` sind
alle schon Eingänge). Ausgänge: `TonSpielen` (nur `akku_leer` beim Tiefstand, B12) → „`akku_leer` beim Tiefstand (B12) und
`lader`“. Kein neuer Befehl `LaderMelden`: Der Ring liest `LaderGeaendert`, `Bereit`, `ZeitquelleGeaendert` und `ZustandMelden`
selbst (`nachfuehrung.py:67`).

**C9, 11 Konstanten** (Zeilen 1344-1353).

| Konstante | alt | neu |
|---|---|---|
| `START_WIEDERHOLUNG_S`, `START_WIEDERHOLUNGEN` | 600, 6 (`idle.py`) | **entfallen** |
| `LADER_RUECKMELDUNG_S` | – | 7 (`idle.py`: Lauflicht 2 s + Ladestand 5 s) |
| `LADER_KURZ_S` | – | 120 (`idle.py`: Kurz-Frist nach der Rückmeldung, S2) |
| `LADER_NACHLAUF_S` | – | 30 (`idle.py`: Reserve nach einem Sync oder Update im Kurz-Modus) |
| `LADER_SPERRE_S` | – | 10 (`idle.py`: Entprellen, S8) |
| `STROM_START_WARTEN_S` | – | 2 (`app.py`: so lange wartet der Start auf die erste Messung von `power`) |
| `SCHLEIFE_S` | – | 300 (`app.py`: Startschleife erkennen, 3.4) |

`LEERLAUF_S` (1200) bleibt. `NETZ_KLASSE_WARTEN_S` (30, `app.py:85`) bleibt; der Vorschlag `LADER_NETZ_WARTE_S` (45) aus
`software_folgen.md` entfällt, weil die Wartezeit schon da ist (`app.py:634-657`).

**C10, 8.1 Töne, Pegel** (Zeilen 851-858). Zusatz: „`lader` hat denselben Pegel wie `hinweis` (`min(grenze, max(HINWEIS_MINDEST,
min(hinweis_pegel, lautstaerke)))`), nicht die Hörlautstärke.“ Grund: Nach dem Einschalten gilt `lautstaerke_start`, nicht die
Lautstärke vom Abend. Code: `sounds.pegel` (`sounds.py:60-70`) nimmt `lader` in den `hinweis`-Zweig.

**C11, 4 `EreignisSenden`** (Zeile 319). Zusatz bei `art="fehler"`: „… und `baustein="power"`, `code="startschleife"` (`app`, nicht der
Kern: Die Box ist mit Strom heruntergefahren und innerhalb von `SCHLEIFE_S` am Lader wieder gestartet; Schleifenbremse,
Abschnitt 3.4).“

### 4.2 `mqtt-v1.md` (3 Änderungen)

**M1, 3.3 Feld `lader`** (Zeile 156) und **6.2 Entität „Lader“** (Zeile 601). alt: „Lader angeschlossen“. Neu: „Strom am Eingang,
aus irgendeiner Quelle (Sockel, Kabel, Powerbank). Der Feldname bleibt.“

**M2, 2 Themenbaum** (nach dem Satz „Es gibt keine weiteren Themen.“ bei Zeile 76). Zusatz: „Die Vormerkung ‚Update beim nächsten
Andocken‘ (Entscheidung S6) liegt nur in Home Assistant und hat **kein** Thema. HA setzt beim Andocken den normalen Befehl
`update` ab (3.7).“

**M3, 3.4 `fehler`, Codes der Box** (Zeile 220). Zusatz: „`baustein="power"`, `code="startschleife"` (die Box ist mit Strom
heruntergefahren und sofort am Lader wieder gestartet; die Box läuft ohne Rückmeldung weiter).“

### 4.3 `ha-websocket-v1.md` (3 Änderungen)

**H1, neuer Befehl Nr. 37 `tobibox/box/update_vormerken`** (nach Nr. 36, Abschnitt 3.11 oder 3.7). Eingabe: `box` (Pflicht),
`vormerken: bool` (Pflicht), `version` (optional, sonst die neueste aus `releases/`). Ausgabe: `{"box", "vorgemerkt": bool,
"version": <string oder null>}`. Rechte: Admin. Idempotent: ja (`vormerken` mit gleichem Wert ändert nichts). MQTT: –
(HA setzt den Befehl `update` später selbst ab, siehe unten). Fehler: `box_unbekannt`, `keine_version`. Fähigkeit
`update_vormerken` (3b). Der Merker liegt im HA-Speicher (nicht in `config.json`, nicht auf MQTT).
*Verhalten des Backends* (Wortlaut für den Vertrag):
(a) Der Merker wirkt bei der nächsten **Andockflanke**: die Box wird `online` und meldet `lader = true`, oder `lader` wechselt von
`false` auf `true` bei `online`.
(b) Das Backend sendet `update` (`ttl_s` 300), sobald `status.netz = "home"`, `status.zustand` ≠ `spielt` und
`status.sync.zustand` ≠ `laeuft` sind. Es versucht das bis 10 min nach der Flanke (Status ändert sich höchstens alle 5 s).
(c) Lehnt die Box ab (`befehl_abgelehnt`, `grund="bedingung"`), bleibt der Merker, und das Backend versucht es in der Frist
erneut, sobald sich der Status ändert. Danach wartet es auf die nächste Andockflanke.
(d) **Ein angenommener Befehl verbraucht den Merker** (ein Versuch je Vormerkung, auch bei Rückfall `failed`; Hinweis an die
Seite). Erreicht `status.version` die vorgemerkte Version, wird der Merker gelöscht.
(e) Ein Merker verfällt nach 30 Tagen mit Hinweis.

**H2, 21 `tobibox/boxen/list`, Box-Objekt** (Zeile ~930). Neues Feld `update_vorgemerkt`: `{"version": <string>, "seit": <Zeitstempel>}`
oder `null`. Ereignis `boxen` (4.1) bei Änderung.

**H3, 22 `tobibox/box/sync` und 2.3** (Zeilen 943-950, 170-171). Klarstellung: „Lader“ heißt Strom am Eingang aus irgendeiner Quelle;
der automatische Start-Sync beim Einschalten am Lader und beim Andocken läuft auch im Hotspot (Entscheidung S7). In 2.3 steht
bei `cmd`: „später `box/update` … und die Vormerkung (H1)“.

### 4.4 `data-model.md` (3 Änderungen)

**D1, 1.6 `lauf.json`** (Zeilen 134, 150). alt: „Die Box schreibt die Datei bei jedem Wechsel des liegenden Tobies … und beim Dienst-Ende“.
Neu: „… und **einmal beim Start, sobald `Bereit` verarbeitet ist** (auch ohne Tobie). Ein Dienst-Neustart ist daran erkennbar:
gleiche `boot_id` ergibt `Bereit.einschalten = false`.“

**D2, 1.6 neue Datei `ende.json`** (Tabelle, Zeile nach `lauf.json`): `{"wall": <Unix-Sekunden oder null>, "am_lader": <bool>}`.
Schreiber `app`, beim Befehl `Herunterfahren`. Leser `app` beim Start (Schleifenbremse). Nie gelöscht, überschrieben. Nicht im Sync,
kein `schema_version`.

**D3, 2 Feld `hinweis_pegel`** (Zeile 208). Zusatz: „Dieser Pegel gilt auch für den Ton `lader`.“ Dazu `box/sounds/lader.wav`
(neue Datei, −18 LUFS, `box/lautheit.json`).

### 4.5 S6 genauer: wo der Merker liegt

| | **A (Vorschlag): Merker in HA, normaler `update`-Befehl** | **B: Merker retained auf MQTT, Box holt selbst** |
|---|---|---|
| Wo | HA-Speicher der Integration | neues Thema `tobibox/<box>/vormerkung`, retained, HA → Box |
| Löschen | HA, bei erreichter Version, nach einem angenommenen Befehl oder nach 30 Tagen | HA schreibt leer; Box merkt sich die Kennung des Versuchs in `update.json`, damit sie nicht schleift |
| Bedingungen nicht erfüllt | Box lehnt ab (`befehl_abgelehnt`, `detail`), HA versucht es erneut oder wartet auf die nächste Flanke | Box wartet bis der Start-Sync fertig ist, prüft dann selbst |
| Änderungen am Box-Vertrag | keine (nur Kurz-Modus-Regeln) | neues Thema, ACL (`mqtt-v1.md` Abschnitt 7), neues Ereignis, Zustand in `idle`, Datei `update.json` |
| Schwäche | HA muss in den ersten 2 min nach dem Andocken reagieren (Status alle 5 s). Gegenmittel: `LADER_NACHLAUF_S` | Box schaltet nicht ab, weil sie den Merker erst nach der MQTT-Verbindung kennt (Zeitfenster, Retained-Frage) |

Empfehlung A (F8). Grund: Ein Befehl an eine ausgeschaltete Box geht verloren (nicht retained, `mqtt-v1.md` Zeile 71), HA sendet
aber nur an eine **laufende** Box. Damit entfällt alles, was B an Zustand auf die Box legt. `LADER_NACHLAUF_S` deckt den Rest:
Ein langer Start-Sync (neue Folgen) würde die Box sonst abschalten, bevor HA das Update schicken kann.

**Jetzt und mit Stufe 3b trennen:**

| Jetzt (Nachtrag zu Stufe 4) | Mit 3b (AP 3.8, 3.11, HA-Seite) |
|---|---|
| Kurz-Modus, `HaUpdateAnstossen` beendet ihn, `LADER_NACHLAUF_S` | das Update selbst (heute `befehl_abgelehnt`, `app.py:612-620`) |
| Vertragstext C7, H1 bis H3 festschreiben, damit 3b dagegen baut | H1: Backend-Befehl, Merker, Andockflanke, Anzeige `update_vorgemerkt` in der Seite |
| Test in `test_idle.py`: `HaUpdateAnstossen` im Kurz-Modus | Test: Merker, Flanke, abgelehnter Befehl, ein Versuch |

Nach einem Update läuft der Dienst neu (`einschalten = false`): Die Box bleibt 20 min an, nicht 2 min. Das ist hinnehmbar.

---

## 5. Konflikte mit dem Bestand und offene Fragen

| # | Konflikt / Frage | Bestand (Beleg) | Empfehlung |
|---|---|---|---|
| **K1 / F1** | Wiederholung des Start-Syncs hält die Box bis 60 min an. Mit S1 ist jede Powerbank Lader; im Auto ohne Netz widerspricht das S2. | Plan 3.16; `idle.py:39-43, 60-62, 203-211, 277-287`; Tests `test_idle.py:505-575`; Design Zeile 1394; `core-interface.md` Zeile 1146 | **Streichen** (Tabelle Zeile 17). Ersatz ist der Takt: Kommt das Netz später, startet `sync.setze_netz` sofort einen Sync (`sync.py:176-177`), solange die Box läuft. Rechtfertigung: S2 sagt 120 s. Alternative: nur Wiederholung nach dem Ende des Kurz-Modus; mehr Code, wenig Nutzen. |
| **K2 / F2** | Startschleife (Box fährt mit Strom herunter und startet sofort). | Nicht gemessen (`software_folgen.md` 1) | Erst messen (6.2). Schleifenbremse (3.4) als Sicherheitsnetz. Bei Schleife: R8 zurücknehmen (PiSugar-Schalter aus), nicht die Software verbiegen. |
| **K3 / F3** | PiSugar-Wecker nachts am Lader. | `pisugar-wecker.md` Zeilen 116-164, 180-191; Wecker nicht gebaut | Gilt nach S1 als Start am Lader: Ton (außer Leise-Zeit), Sync, 127 s. Die Lücke „kein zweiter Versuch beim Start-Sync“ ist damit **wieder offen** (Wiederholung weg, K1). Beim Bau des Weckers entscheiden. Bis dahin: Weckzeit in ein Leise-Zeit-Fenster legen. |
| **K4 / F4** | Rückmeldung beim Abziehen? | `led.py:237-241` zeigt schon 5 s Akku, ohne Ton | **Ring ja (wie heute), Ton nein.** Der Kurz-Modus läuft weiter (S3 nennt Abziehen nicht). |
| **K5 / F5** | Angedockte laufende Box: Kurz-Modus? | S2 spricht vom Start | **Nein, 20-min-Regel bleibt.** Das Kind hat die Box gerade benutzt; Abschalten nach 2 min wäre eine Überraschung. Prüfen nach dem Pi-Probelauf. |
| **K6 / F6** | S5-Helligkeiten gegen die heutige Helligkeit. | `led.py:64, 112-119, 161-168, 280-283`: `stumm` ×0,4 (6 % bei Akku), `leiser` nichts; 3 % ergibt Stufe 0 (dunkel) | Absolute Werte für die Akku-Anzeige (15 / 5 / 3 %). `apa102_rahmen`: Stufe mindestens 1. Sichtbarkeit am Muster prüfen (6.2). Auch `leiser` dimmt jetzt (Änderung). |
| **K7 / F7** | Zwei Töne beim Einschalten (Entscheidung L). | `session.py:844-845` spielt `start` bei jedem `Bereit` | `lader` ersetzt `start` (Regel 1a). Dafür **erste Messung vor `Bereit`** (3.3). Ohne die Umstellung: zwei Töne hintereinander. |
| **K8 / F8** | Wo liegt der Merker für S6. | Befehle sind nicht retained (`mqtt-v1.md` Zeile 71) | **A** (HA). Siehe 4.5. |
| **K9 / F9** | HA-Befehl beendet den Kurz-Modus, aber „HA setzt den Zähler nicht zurück“. | `idle.py:12-14`; CUJ 16 Zeile 862-864 | Nur im Kurz-Modus: beim Verlassen beginnen die 20 min neu (sonst gälte der Rest der 120 s). Satz in CUJ 16 anpassen. |
| **K10 / F10** | S9 gilt auch für Lernmodus und Gute Nacht? Kopfhörer im Kurz-Modus? | S3 nennt Kopfhörer nicht; Bestand zählt ihn als Bedienung | Lernmodus: kein Ton. Gute Nacht: es spielt, also S9. Kopfhörer im Kurz-Modus: ignorieren (wie Drehregler). |
| **K11 / F11** | Ton `lader`: Pegel. | `start` hat Hörpegel (`TON_MINDEST` 10, Zeile 851); `hinweis` 15 | Wie `hinweis`. Nach dem Einschalten gilt `lautstaerke_start`, nicht die Abendlautstärke. |
| **K12 / F12** | Hauptknopf kurz kommt auf dem Pi an? | Weg über `taste_befehl` noch offen (B2, `pisugar-wecker.md` Zeilen 81-114); Knopf am GPIO optional | Ohne Hauptknopf kurz kann das Kind den Kurz-Modus nur mit einem Tobie beenden. Messung 6 in 6.2 vor der Abnahme. |
| K13 | Dienst-Neustart am Lader startet keinen Start-Sync mehr. | `idle.py:168-178` startet ihn bei jedem `Bereit` | Gewollt (Abschnitt 3.2), der Takt holt ihn. In CUJ 16 vermerken. |
| K14 | Schwache Powerbank hält die Box „am Lader“ bei fallendem Akku; Tiefstand wird am Lader ignoriert. | `idle.py:252-254`, `power.py:295-296` | Messung 7 in 6.2. Danach entscheiden, ob Tiefstand auch am Lader bei fallendem Akku gilt. |
| K15 | Mac: Simulation von Start am Lader. | `sim power` setzt Lader (`app.py:360-369`, `cli.py:500-501`); Boot-Kennung am Mac ist die Systemstartzeit (`bootid.py:30-35`) | Siehe AP L1 und L9: Startwert `[strom] sim_lader`, Option `--einschalten` (Kennung `None`). |

---

## 6. Umsetzungsplan

### 6.1 Arbeitspakete

Neue Nummern `L1` bis `L10` (Nachtrag zu Stufe 4, Reihenfolge von oben nach unten; Abhängigkeiten in der Spalte). Modelle nach
`CLAUDE.md`: Sonnet für Code, Haiku für Doku und Boilerplate.

| AP | Modell | Inhalt | Dateien | Abhängig von |
|---|---|---|---|---|
| **L0** | Haiku | Verträge nach Freigabe einarbeiten: C1 bis C11, M1 bis M3, H1 bis H3, D1 bis D3 (Tobias gibt frei) | `docs/protocol/*`, `docs/data-model.md` | Freigabe |
| **L1** | Sonnet | `events.Bereit.einschalten`; `lauf.py` (Boot-Kennung beim Start schreiben, `lese_dienst_neustart`); `app.starte`: erste Messung `power.start` vor `Bereit` (Frist), `ende.json` schreiben, Schleifenbremse, `EreignisSenden`; `[strom] sim_lader`, `--einschalten`; Tests `test_bootid_lauf.py`, `test_app_stufe3a.py` | `events.py`, `lauf.py`, `app.py`, `config.py`, `cli.py` | L0 |
| **L2** | Sonnet | `idle.py`: Merker `kurz`, Frist, Zeilen 9 bis 16 der Tabelle, Wiederholung entfernen, Andocken (S8), `letzter_wechsel`, `Nachlauf`; Tests `test_idle.py` (neu / umgekehrt: Zeilen 316-334, 505-575), `test_cuj16_leerlauf.py` (Zeilen 143, 156), `test_core_stufe3a.py:61`, `test_befunde_stufe3a_4.py:407-422` | `idle.py` | L1 |
| **L3** | Sonnet | `power.py`: Lader-Abfrage alle 2 s (`lader_intervall_s`), Akku bei 10 s; `Power.start` liefert Messung; Tests `test_power.py` | `power.py`, `config.py` | – |
| **L4** | Sonnet | Kern: Ton `lader` (`events.TonSpielen`), Konfliktregeln 1a, 2a (`core.py`), `sounds.pegel`; Tests `test_core.py`, `test_sounds.py`, `test_app_toene.py` | `events.py`, `core.py`, `sounds.py` | L0 |
| **L5** | Haiku | Ton `lader.wav` (`tools/make_sounds.py`), `lautheit.json`, `tools/lautheit.py` prüfen | `box/sounds/`, `box/lautheit.json` | L4 |
| **L6** | Sonnet | `led.py`: Helligkeit der Akku-Anzeige nach `ruhe` (15 / 5 / 3 %), Uhr unsicher, Lauflicht nur bei `normal` und sicherer Uhr, Akku-Anzeige nach dem Lauflicht, `apa102_rahmen` Stufe mindestens 1; `nachfuehrung.py` reicht `ZeitquelleGeaendert` durch; Tests `test_led.py`, `test_cuj18_led_ring.py` | `led.py`, `nachfuehrung.py` | – |
| **L7** | Sonnet | CUJ-Tests: neu `test_cuj21_start_am_lader.py`, `test_cuj22_andocken.py` (Simulation, Uhr), Konfliktzeilen aus Abschnitt 2 | `box/tests/cuj/` | L2, L4, L6 |
| **L8** | Haiku | Doku nachziehen: Design (CUJ 10, 15, 16, 18, 20, neu 21 und 22, Tabelle Zeilen 1380-1397 und 1402-1416, „Netz, Sync, Strom“ Zeilen 1703 und 1734, Update Zeile 1743, AP 4.1 Zeile 2790, AP 4.3 Zeile 2821), `pisugar-wecker.md` (Abschnitt 4 und 6), Plan (5.5.2, 5.6.3, 5.6.8, 8.2.4 → T5), Betriebshandbuch | `docs/` | L7 |
| **L9** | Sonnet | Mit 3b: H1 bis H3 (Backend, Seite), Test `update_vormerken` | `custom_components/…` (HA-Integration) | AP 3.8 |
| **L10** | Tobias | Pi-Probelauf (6.2) | – | L1 bis L6 |

Reihenfolge: **6.2 Messung 1 und 2 vor L1 bis L7** (sie können das Ganze kippen), dann L0, dann L3 / L4 / L6 parallel, L1, L2,
L5, L7, L8, L10. L9 mit 3b.

### 6.2 Erst am Pi (Messungen am Muster, Tobias)

| # | Messung | Entscheidet |
|---|---|---|
| 1 | **Startschleife:** Box mit Strom herunterfahren (Hauptknopf lang und 20-min-Regel am Sockel): bleibt sie aus? Mit Netzteil, Powerbank, Auto-Buchse. Dazu: Einschalten bei Strom nach Akkutausch / Reset | K2: Schleifenbremse reicht oder R8 zurück |
| 2 | Meldet `pisugar-server` `battery_power_plugged` an der **einzigen** Buchse (ohne Diode) richtig, mit leerem und vollem Akku? | Ob der ganze Ablauf trägt (R10) |
| 3 | **Startzeit** vom Aufsetzen bis `Bereit` und bis Ton / Ring (Pi 3A+, geschätzt 20 bis 30 s); `STROM_START_WARTEN_S` und Dauer der ersten Messung | S11: Frühstart-Ring ja / nein (Aufwand: kleiner Dienst, der den Ring in den ersten Sekunden schaltet) |
| 4 | Schalter „Einschalten bei Strom“ finden und prüfen (`help xx`, `config.json`, Web-Oberfläche) | Voraussetzung R8 |
| 5 | Lader-Abfrage alle 2 s: CPU-Last, Antwortzeit; Wackeln am Sockel (wie oft wechselt der Wert) | `lader_intervall_s`, `LADER_SPERRE_S` |
| 6 | **Hauptknopf kurz** kommt an (`taste_befehl` oder GPIO); Knopf am Sockel, Wecker (RTC-Alarm) startet mit Strom? | K12, S3 wirkt |
| 7 | Schwache Quelle (1 A): sinkt der Akku unter Last, obwohl `battery_power_plugged = true`? | K14 |
| 8 | Wiederholtes Wecken durch Powerbank oder Auto-Buchse, die Strom neu geben | Ob die Rückmeldung nervt; Sperre für Starts nötig |
| 9 | Ring: 3 % und 5 % durch das Gehäuse bei Nacht sichtbar / zu hell? (Stufe 1 von 31 = 3,2 %) | K6 |
| 10 | Hotspot im Auto: Datenmenge eines Start-Syncs | S7 bewusst in Kauf genommen; nur Notiz |
