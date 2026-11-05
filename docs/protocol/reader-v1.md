# Protokoll Leser ↔ Box-Dienst, Version 1 (`reader-v1`)

*   **Status:** Vertrag Stufe 0, Entwurf zur Prüfung durch einen Goldfisch
*   **Grundlage:** `docs/designs/box-software.md` (Baustein 1, Baustein 2,
    Zeitbudget, Kern-Zustände „Wiedergabe-Sitzung“)
*   **Gegenstück:** `docs/protocol/reader-v1-examples.txt` (Testgrundlage für
    beide Seiten)
*   **Gilt für:** Firmware `tobibox-reader` (ESP32-S3 mit PN5180) und die
    Module `protocol.py` und `reader.py` des Box-Dienstes.

Dieses Dokument ist der **einzige Vertrag** zwischen Firmware und Box-Dienst.
Wo es etwas nicht sagt, gilt: nicht erfinden, sondern die Projektleitung fragen.

## 1. Transport

*   USB-Serielle des ESP32-S3: HWCDC (USB-Serial/JTAG). Die Baudrate hat bei CDC
    keine Bedeutung; der Box-Dienst stellt 115200 ein.
*   Zeichensatz: ASCII. Zeilenende von der Firmware: genau `\n` (LF).
    Der Box-Dienst schickt ebenfalls `\n`. Beim Empfang wird **ein** `\r`
    unmittelbar vor dem `\n` entfernt (CRLF wird akzeptiert).
*   Die Firmware schreibt auf die USB-Serielle **nur Protokollzeilen**, keinen
    Diagnosetext. Fehler gehen als `ERR`.
*   Die Firmware setzt `setTxTimeoutMs(0)`: Ist niemand am anderen Ende, werden
    Zeilen verworfen statt zu blockieren. Das zeigt sich als Lücke in `seq`.
*   Der Box-Dienst öffnet die Serielle ohne DTR/RTS (beide vor dem Öffnen auf
    „aus“, `dsrdtr` und `rtscts` aus), damit das Öffnen keinen Reset auslöst.
*   Eine Verbindung ist eine Folge von Zeilen in beide Richtungen ohne
    Quittung. Es gibt keine Wiederholung; die Wiederherstellung des Zustands
    läuft über `HELLO` (Abschnitt 8) und den Herzschlag (Abschnitt 6).

## 2. Zeilengrammatik

```
zeile      = typ *( SP feld ) LF
typ        = 1*( "A"-"Z" / "0"-"9" / "_" )  ; beginnt mit einem Großbuchstaben
feld       = schluessel "=" wert
schluessel = "a"-"z" *( "a"-"z" / "0"-"9" / "_" )
wert       = 1*( %x21-7E )                  ; sichtbares ASCII, ohne Leerzeichen
SP         = %x20                           ; genau ein Leerzeichen
```

Regeln:

1.  Höchstens **200 Zeichen** je Zeile (ohne Zeilenende). Längere Zeilen werden
    bis zum nächsten `\n` verworfen (`too_long`).
2.  Erlaubt sind nur die Zeichen 0x20 bis 0x7E (nach Entfernen eines `\r` am
    Ende). Alles andere macht die Zeile ungültig (`not_ascii`).
3.  Zwischen Wörtern steht genau ein Leerzeichen; am Anfang und Ende der Zeile
    keines. Eine Zeile, die mit einem Leerzeichen beginnt (auch eine Zeile nur
    aus Leerzeichen), hat kein Typwort und ist `bad_syntax`.
4.  Die Reihenfolge der Felder ist festgelegt (Abschnitt 3, „Zeilentabelle“).
    Die Firmware hält sie ein, der Parser des Box-Dienstes darf **jede**
    Reihenfolge akzeptieren.
5.  Ausnahme `ERR`: Das Feld `detail=` steht immer zuletzt, sein Wert ist der
    **Rest der Zeile** und darf Leerzeichen und `=` enthalten. Erlaubte Zeichen
    in `detail`: 0x20 bis 0x7E außer `|` und `;`; 1 bis 80 Zeichen. Die Firmware
    ersetzt andere Zeichen durch `_` und kürzt auf 80 Zeichen. Der **Parser**
    ist streng: `detail` mit `|` oder `;` oder mit mehr als 80 Zeichen ist
    `bad_value`; ein leeres `detail=` ist `bad_syntax` (leerer Wert). Neue
    Zusatzfelder einer `ERR`-Zeile stehen **vor** `detail=` (Abschnitt 13),
    sonst würden sie Teil von `detail`.
6.  Zahlen sind Dezimalzahlen ohne Vorzeichen und ohne führende Nullen
    (`0` oder `[1-9][0-9]*`). „uint32“ heißt: 0 bis 4294967295, höchstens
    10 Stellen.

## 3. Zeilen vom Leser zum Box-Dienst

### Zeilentabelle

| Zeile | Felder in dieser Reihenfolge | Wann |
|---|---|---|
| `HELLO` | `proto` `fw` `build` `pn5180` | beim Start, und als Antwort auf `PING` |
| `PLACED` | `uid` `type` `tonie` `seq` | Figur mit Kennung liegt (entprellt) |
| `LOCKED` | `seq` | gesperrter Tonie liegt (entprellt) |
| `REMOVED` | `seq` | die liegende Figur ist weg |
| `HB` | `up` `present` `polls` `hits` `rejected` `errors` `cycle_ms` | Herzschlag alle 2 s |
| `ERR` | `code` `detail` | Fehler oder Hinweis |

Alle Felder jeder Zeile sind **Pflicht**. Es gibt keine optionalen Felder.

### Felder und Wertebereiche

| Feld | Zeile | Typ und Bereich |
|---|---|---|
| `proto` | HELLO | uint32, ≥ 1. Protokollversion, hier `1`. |
| `fw` | HELLO | Firmware-Version `MAJOR.MINOR.PATCH` mit optionalem `-Zusatz` (`[0-9A-Za-z.]+`), höchstens 24 Zeichen. Beispiel `1.0.0`, `1.2.10-rc1`. |
| `build` | HELLO | Git-Hash: 7 bis 12 Zeichen `[0-9a-f]`, optional gefolgt von `-dirty`; oder `unknown`. |
| `pn5180` | HELLO | Firmware-Version des PN5180 als `<major>.<minor>` (Dezimalzahlen, z. B. `4.2`) oder `unknown`, wenn sie nicht gelesen werden konnte. |
| `uid` | PLACED | kanonische Kennung, Abschnitt 4. |
| `type` | PLACED | `ntag` (ISO 14443A) oder `iso15693`. |
| `tonie` | PLACED | `1` genau dann, wenn `type=iso15693` und `uid` mit `e00403` beginnt; sonst `0`. |
| `seq` | PLACED, LOCKED, REMOVED | uint32, Abschnitt 5. |
| `up` | HB | uint32, Sekunden seit dem Start. Die Firmware rechnet aus einer 64-Bit-Zeit; `up` läuft erst nach 2³² s über (nicht schon nach 49,7 Tagen wie `millis()`). |
| `present` | HB | `0` oder `1`. |
| `polls` `hits` `rejected` `errors` | HB | uint32 (Zähler seit Start; sie laufen bei 2³² über auf 0). |
| `cycle_ms` | HB | 0 bis 65535. |
| `code` | ERR | `[a-z][a-z0-9_]{0,31}`; Liste in Abschnitt 7. |
| `detail` | ERR | Freitext, siehe Grammatik Regel 5. |

Der Parser prüft zusätzlich die Zusammenhänge von `PLACED`: Passen `uid`, `type`
und `tonie` nicht zueinander (Länge der Kennung passt nicht zum Typ, oder
`tonie` stimmt nicht mit dem Präfix überein), ist die Zeile ungültig
(`uid_type_mismatch`).

### Bedeutung der Zeilen

*   **`HELLO`** — „Ich bin da, Zählung und Zustand beginnen neu.“ Nach jedem
    Start und als Antwort auf `PING`. Mit `HELLO` beginnt `seq` wieder bei 0.
    Nach einem `HELLO` auf `PING` meldet die Firmware eine liegende Figur sofort
    erneut (Abschnitt 8). Die Firmware sendet `HELLO` nie ohne Anlass wiederholt.
*   **`PLACED`** — Eine Figur mit Kennung liegt, und die Kennung wurde nach der
    Entprellregel bestätigt (Abschnitt 9). Wiederholt sich nicht, solange die
    Figur liegt.
*   **`LOCKED`** — Ein Tonie im Privacy-Modus liegt und ließ sich nicht
    entsperren. Er hat keine Kennung.
*   **`REMOVED`** — Die zuletzt gemeldete Figur (nach `PLACED` oder `LOCKED`) ist
    weg. Beim Figurwechsel kommen `REMOVED` und gleich danach `PLACED` bzw.
    `LOCKED` unmittelbar hintereinander mit aufeinanderfolgenden `seq`.
*   **`HB`** — Lebenszeichen und Zustandsabgleich (Abschnitt 6).
*   **`ERR`** — Siehe Abschnitt 7.

## 4. Kennung (kanonisch)

Die kanonische Schreibweise entsteht **nur in der Firmware**. Der Box-Dienst
prüft sie und speichert sie **unverändert** (er schreibt sie nicht um, auch
nicht in Kleinbuchstaben).

*   Hexadezimal, **Kleinbuchstaben**, **MSB zuerst**, ohne Trenner, ohne
    Präfix.
*   ISO 14443A (`type=ntag`): 4, 7 oder 10 Byte, also **8, 14 oder 20**
    Hexzeichen. Die Reihenfolge ist die, in der die Bibliothek sie liefert
    (MSB zuerst).
*   ISO 15693 (`type=iso15693`): 8 Byte, also **16** Hexzeichen. ISO 15693 sendet
    die Kennung LSB zuerst; die Firmware dreht sie um (wie `storeVicinityUid`
    in `firmware/tonie_test/`), sodass sie mit `e0` beginnt. Tonies beginnen mit
    `e00403`.

Regulärer Ausdruck (Python `re`, mit `fullmatch` verwenden):

```
[0-9a-f]{8}|[0-9a-f]{14}|[0-9a-f]{20}|[0-9a-f]{16}
```

Ergänzende Prüfung je `type`:

| `type` | erlaubte Länge | Zusatz |
|---|---|---|
| `ntag` | 8, 14 oder 20 | `tonie=0` |
| `iso15693` | 16 | `tonie=1` genau dann, wenn Präfix `e00403`, sonst `tonie=0` |

Eine Kennung ist der Schlüssel in `config.json` und `unknown.json` und wird in
MQTT-Themen verwendet; sie enthält deshalb nur `[0-9a-f]`.

## 5. `seq`

*   `seq` steht nur in `PLACED`, `LOCKED` und `REMOVED`. Es zählt **jede dieser
    Zeilen** um 1 hoch. `HELLO`, `HB` und `ERR` haben kein `seq` und zählen
    nicht mit.
*   Nach dem Start des ESP32 und nach jedem `HELLO` (auch auf `PING`) hat die
    nächste dieser Zeilen `seq=0`.
*   Überlauf: nach 4294967295 folgt 0. (In der Praxis unerreichbar.)
*   Der Box-Dienst merkt sich das zuletzt gesehene `seq` und vergleicht:
    *   `HELLO` setzt die Erwartung auf 0.
    *   Stimmt `seq` mit der Erwartung überein, gibt es nichts zu tun.
    *   Eine **Lücke** (`seq` größer als erwartet) heißt: Zeilen gingen verloren.
        Der Dienst **verarbeitet die Zeile trotzdem**, protokolliert die Lücke
        (`seq_gap`, erwartet, erhalten) und gleicht den Zustand über den
        Herzschlag ab (Abschnitt 6).
    *   `seq` kleiner als erwartet ohne vorheriges `HELLO` heißt: Die Firmware
        wurde neu gestartet und das `HELLO` ging verloren. Der Dienst
        verarbeitet die Zeile trotzdem, protokolliert `seq_reset` und stellt
        die Erwartung auf `seq + 1`.
    *   Es gibt **keine** Verwerfung wegen `seq`: Eine Zeile mit gültigen Feldern
        wird immer verarbeitet.

## 6. Herzschlag `HB`

Die Firmware sendet `HB` alle `HEARTBEAT_INTERVAL_MS` (2000 ms) auf der
monotonen Uhr, unabhängig davon, ob etwas liegt; die erste `HB` kommt
2000 ms nach dem `HELLO`. Weil die Firmware zwischen den Abfragezyklen sendet,
darf der tatsächliche Abstand bis zu einem Zyklus länger sein.

| Feld | Definition |
|---|---|
| `up` | Sekunden seit dem Start des ESP32 (nicht seit `HELLO`; ein `PING` setzt es nicht zurück). |
| `present` | `1` genau dann, wenn der Entpreller im Zustand `LIEGT` ist, also seit dem letzten `PLACED` oder `LOCKED` noch kein `REMOVED` gemeldet wurde. Sonst `0`. |
| `polls` | Anzahl abgeschlossener Abfragezyklen seit Start. Jeder Zyklus zählt, mit welchem Ergebnis auch immer. Ein fehlgeschlagener PN5180-Start (Abschnitt 7) zählt **nicht** als Zyklus. |
| `hits` | Zyklen mit gültiger Lesung (`uid` oder `gesperrt`), unabhängig davon, was der Entpreller daraus macht. |
| `rejected` | Teilmenge von `hits`: gültige Lesungen, die der **Bezugsfigur widersprachen**. Bezug ist der Kandidat (im Zustand `PRUEFT`) oder die liegende Figur (im Zustand `LIEGT`). Im Zustand `LEER` zählt keine Lesung. Die ausführliche Regel steht in der Zustandstabelle (Abschnitt 9). |
| `errors` | Zyklen, deren Ergebnis `fehler(code)` war, plus fehlgeschlagene PN5180-Startversuche. Jeder Fehlerzyklus zählt, auch wenn die `ERR`-Zeile durch die Ratenbegrenzung unterdrückt wird. |
| `cycle_ms` | Dauer der Arbeit des **zuletzt abgeschlossenen** Zyklus in ms (vom Beginn der Abfrage bis zum Ergebnis, ohne die Wartezeit bis zum nächsten Zyklus). 0, solange noch kein Zyklus lief. Auf 65535 begrenzt. |

Es gilt immer: `hits + errors ≤ polls` und `rejected ≤ hits`. Die übrigen
Zyklen sind „nichts“.

### Wächter im Box-Dienst

*   Der Wächter läuft ab dem `HELLO`. Jede gültige `HB` setzt ihn zurück.
*   **5 s ohne `HB`** (`WATCHDOG_S = 5`) lösen den Wächter-Alarm aus (zwei
    verpasste Herzschläge plus Reserve). Der Dienst protokolliert, schließt die
    Verbindung und verbindet sich neu (Abschnitt 12).
*   **Abgleich über `present`:** Der Kern vergleicht `present` mit seinem
    Wissen, ob eine Figur liegt. Stimmen sie in **zwei aufeinanderfolgenden**
    `HB` nicht überein, schickt der Dienst `PING` (Abschnitt 8). Das `HELLO`
    mit der erneuten Meldung stellt den Zustand wieder her. Liegt nichts mehr
    und kommt deshalb nur das `HELLO`, gilt die Figur beim Kern mit der ersten
    `HB` danach (`present=0`) als abgehoben. Details: `core-interface.md`,
    Abschnitt 9, Punkt 3.

## 7. Fehlercodes (`ERR`)

Die Liste ist **vollständig** für Version 1. Ein unbekannter Code (neuere
Firmware) ist gültig und wird vom Dienst als Warnung behandelt.

| Code | Bedeutung | Schwere | Entsteht als |
|---|---|---|---|
| `pn5180_no_response` | Der PN5180 antwortet nicht (Produktversion unlesbar oder 0xFF, SPI/BUSY tot). | Fehler | Ergebnis `fehler` eines Zyklus, oder fehlgeschlagener Startversuch |
| `pn5180_timeout` | Ein PN5180-Befehl überschritt `PN5180_CMD_TIMEOUT_MS` oder BUSY wurde nicht frei (z. B. `setRF_on`/`setRF_off`). | Fehler | Ergebnis `fehler` eines Zyklus |
| `bad_response` | Antwort des Chips unbrauchbar (CRC-Fehler, unerwartete Länge oder Fehlerflag). | Warnung | Ergebnis `fehler` eines Zyklus |
| `uid_invalid` | ISO 14443A lieferte eine Kennungslänge außerhalb 4, 7, 10 Byte. | Warnung | Ergebnis `fehler` eines Zyklus |
| `unlock_failed` | Ein Tonie im Privacy-Modus liegt, das Entsperren mit dem Passwort ist gescheitert. Das ist der Normalfall bei fremden Tonies (CUJ 6), kein Hardwarefehler. | Hinweis | Zusatzzeile direkt nach `LOCKED`; kein `fehler`-Ergebnis, zählt nicht in `errors` |
| `bad_command` | Die Firmware erhielt eine Zeile, die kein gültiger Befehl ist. | Hinweis | Antwort auf eine Zeile vom Box-Dienst |
| `internal` | Interner Fehler der Firmware (z. B. Warteschlange voll). | Fehler | jederzeit |

„Schwere“ ist keine Zeilenangabe, sondern eine feste Zuordnung im Box-Dienst.
`reader` setzt sie beim Ereignis `LeserFehler` im Feld `schwere` (`core-interface.md`,
Abschnitt 3.1); den Prüfpunkt „Leser“ leitet der Statussammler daraus ab
(`core-interface.md`, Abschnitt 12):

*   **Fehler:** Der Prüfpunkt „Leser“ steht auf Fehler (Status-Karte, `tobibox
    status`), solange innerhalb der letzten 10 s ein solcher Code kam.
*   **Warnung:** protokolliert (Ebene WARNING), kein Einfluss auf den Prüfpunkt.
*   **Hinweis:** protokolliert (Ebene INFO), kein Einfluss.

Ergebnisse eines Abfragezyklus (`fehler(code)`) können nur diese Codes
tragen: `pn5180_no_response`, `pn5180_timeout`, `bad_response`, `uid_invalid`.

### Ausgabe der `ERR`-Zeilen (Firmware)

1.  Jedes Ergebnis `fehler(code)` erhöht `errors`. Die Zeile
    `ERR code=<code> detail=<text>` wird nur geschrieben, wenn seit der letzten
    geschriebenen `ERR`-Zeile **desselben Codes** mindestens
    `ERR_MIN_INTERVAL_MS` (2000 ms) vergangen sind (nicht „innerhalb der letzten
    2000 ms“: bei genau 2000 ms wird geschrieben). Zeitbasis ist der Zeitstempel
    `t` des Zyklus-Ergebnisses (Ende der Arbeit des Zyklus), nicht die
    tatsächliche Sendezeit; Differenzen vorzeichenlos modulo 2³². Die erste Zeile
    je Code erscheint sofort.
2.  `unlock_failed` wird einmal je `LOCKED`-Meldung geschrieben, **unmittelbar
    nach** der `LOCKED`-Zeile, ohne Ratenbegrenzung und ohne `errors` zu erhöhen.
    Auch die erneute `LOCKED`-Meldung nach einem `PING` (Abschnitt 8) ist eine
    `LOCKED`-Meldung und bekommt ihre `unlock_failed`-Zeile.
3.  `bad_command` ist die Antwort auf jede ungültige Zeile vom Box-Dienst
    (Abschnitt 8), außer auf eine leere Zeile.
4.  Beim Start prüft die Firmware den PN5180 (Produktversion lesen). Scheitert
    das, schreibt sie `ERR code=pn5180_no_response ...` (Regel 1 gilt), erhöht
    `errors`, sendet weiter Herzschläge (`present=0`) und wiederholt den
    Startversuch alle `PN5180_INIT_RETRY_MS` (5000 ms), bis er gelingt. Sie
    bleibt nicht stehen.
5.  Die Firmware startet bei Fehlern **nicht** selbst neu. Ein Neustart des
    ESP32 ist Sache des Boxbetreibers (USB ziehen) bzw. des Wächters.
6.  **Reihenfolge innerhalb eines Schritts:** erst die Zeilen des Entprellers
    (`REMOVED`, `PLACED` bzw. `LOCKED` samt `unlock_failed`), dann die `ERR`-Zeile
    des Fehlerzyklus.

## 8. Zeilen vom Box-Dienst zum Leser

| Zeile | Wirkung |
|---|---|
| `PING` | Die Firmware antwortet mit `HELLO` (Felder wie beim Start), setzt `seq` auf 0 zurück und meldet eine **liegende Figur sofort erneut** (`PLACED` bzw. `LOCKED` mit `seq=0`). Der Entpreller-Zustand, `up` und die Zähler bleiben unverändert. Liegt nichts, folgt nur das `HELLO`. |

*   Das Wort `PING` steht allein in der Zeile, ohne Felder. Alles andere
    (Groß-/Kleinschreibung, Leerzeichen, Felder) ist ungültig.
*   **Reserviert:** Jede andere Zeile vom Box-Dienst ist in Version 1 reserviert
    (Rückkanal, siehe „Offene Fragen“ im Design; gedacht für z. B. Poll-Intervall
    ändern, Neustart). Die Firmware v1 beantwortet sie wie jede ungültige Zeile
    mit `ERR code=bad_command detail=...` und führt nichts aus. Der Box-Dienst
    v1 sendet nur `PING`.
*   Ungültig sind leere Zeile (still ignoriert, keine Antwort), Zeile über
    200 Zeichen, Zeichen außerhalb 0x20 bis 0x7E, und jede Zeile außer `PING`.
    Auf die letzten drei antwortet die Firmware mit `ERR code=bad_command`.
*   Beispiele: `reader-v1-examples.txt`, Abschnitt 2.

## 9. Entpreller

Der Entpreller ist reine Logik ohne Hardware. Er bekommt je Abfragezyklus ein
Ergebnis mit Zeitstempel und entscheidet, wann eine Meldung nötig ist. Er
vergibt kein `seq` und schreibt keine Zeilen; das macht die Protokoll-Ausgabe
(`protocol.cpp`).

### Eingaben und Ausgaben

*   **Eingabe je Zyklus**, genau eine von:
    *   `nichts`: nichts gefunden.
    *   `uid(typ, bytes)`: gültige Kennung (offen oder entsperrt gelesen; das
        macht für den Entpreller **keinen Unterschied**).
    *   `gesperrt`: Tonie im Privacy-Modus, Entsperren gescheitert.
    *   `fehler(code)`: Zyklus mit Fehler. Er ist **kein** `nichts`.
*   **Zeit:** `t` in ms, vorzeichenlos 32 Bit, monoton, Zeitpunkt des
    Zyklus-Ergebnisses. Differenzen werden **vorzeichenlos modulo 2³²**
    gerechnet (`t − last`), damit der Überlauf nach 49 Tagen nichts bricht.
*   **Ausgabe**, null bis zwei Ereignisse je Eingabe, in dieser Reihenfolge:
    `Entfernt`, dann `Platziert(typ, uid)` oder `Gesperrt`.
*   **Parameter** (dem Entpreller übergeben, Standardwerte aus `timing.h`):
    `confirm_reads` (= `CONFIRM_READS`), `remove_after_ms`
    (= `REMOVE_AFTER_MS`) und `error_hold_ms` (= `ERROR_HOLD_MS`).

### Identität

Zwei Lesungen sind **gleich**, wenn beide `gesperrt` sind, oder beide `uid` mit
derselben Kennung (Zeichenfolge gleich). Typ und Entsperrweg zählen nicht.
`gesperrt` und `uid` sind verschieden, `uid` mit anderer Kennung ist verschieden.

### Zustände

| Zustand | Bedeutung | Merkt sich |
|---|---|---|
| `LEER` | nichts liegt, kein Kandidat | – |
| `PRUEFT` | ein Kandidat wurde gelesen, noch nicht bestätigt (nichts gemeldet) | Kandidat `K`, Zähler `n` (1 bis `confirm_reads`−1) |
| `LIEGT` | Figur ist gemeldet (`PLACED` oder `LOCKED`) | liegende Identität `L`, Zeit der letzten Lesung von `L` (`last`), Marke `nur_fehler`, Herausforderer `H` mit Zähler `hn` (oder keiner) |

Die Unterscheidung „Kennung liegt“ gegen „gesperrt liegt“ ist die Identität
`L`; beide Fälle laufen in demselben Zustand `LIEGT` mit denselben Regeln.

`nur_fehler` ist wahr, solange seit der letzten gültigen Lesung von `L` **nur
Fehlerzyklen** kamen (auch: gar kein Zyklus). Jedes `nichts` und jede gültige
Lesung einer anderen Identität macht sie falsch; eine gültige Lesung von `L`
macht sie wieder wahr.

### Schritt 0: Zeitregel (vor jeder Eingabe)

Im Zustand `LIEGT` gilt als Grenze `g`:

*   `g = error_hold_ms` (5000 ms), wenn `nur_fehler` wahr ist: Fehlerzyklen
    zählen bis zu dieser Zeit als „Figur liegt noch“.
*   `g = remove_after_ms` (1100 ms) sonst: `nichts` (und fremde Lesungen) sind
    kein Beleg für die liegende Figur.

Ist `t − last ≥ g`, dann Ausgabe `Entfernt`, neuer Zustand `LEER`,
Herausforderer gelöscht. Danach wird **die Eingabe dieses Zyklus trotzdem im
neuen Zustand verarbeitet** (Schritt 1). Das gilt für jede Eingabe
einschließlich `fehler` und einer gültigen Lesung derselben Figur: Eine Lücke
von `g` und mehr zwischen zwei gültigen Lesungen der liegenden Figur führt
immer zu `REMOVED`, danach ist es ein neues Auflegen mit frischer Bestätigung.

### Schritt 1: Übergänge

`N` steht für `confirm_reads`. Eine Eingabe „gültig“ ist `uid` oder `gesperrt`.

| Nr | Zustand | Eingabe | Bedingung | Ausgabe | Neuer Zustand und Änderungen |
|---|---|---|---|---|---|
| 1 | `LEER` | `nichts` | – | – | `LEER` |
| 2 | `LEER` | `fehler` | – | – | `LEER` |
| 3 | `LEER` | gültig `X` | `N ≥ 2` | – | `PRUEFT`, `K=X`, `n=1` |
| 4 | `LEER` | gültig `X` | `N = 1` | `Platziert`/`Gesperrt` | `LIEGT`, `L=X`, `last=t`, `nur_fehler` wahr |
| 5 | `PRUEFT` | `nichts` | – | – | `LEER` (Folge unterbrochen) |
| 6 | `PRUEFT` | `fehler` | – | – | `LEER` (Kandidat verworfen) |
| 7 | `PRUEFT` | gültig `X`, `X = K` | `n+1 < N` | – | `PRUEFT`, `n = n+1` |
| 8 | `PRUEFT` | gültig `X`, `X = K` | `n+1 ≥ N` | `Platziert`/`Gesperrt` | `LIEGT`, `L=X`, `last=t`, `nur_fehler` wahr |
| 9 | `PRUEFT` | gültig `X`, `X ≠ K` | – | – | `PRUEFT`, `K=X`, `n=1`; **rejected +1** (für `N=1` nicht erreichbar) |
| 10 | `LIEGT` | `nichts` | – | – | `LIEGT`, Herausforderer gelöscht, `nur_fehler` falsch |
| 11 | `LIEGT` | `fehler` | – | – | `LIEGT`, Herausforderer gelöscht; `last` und `nur_fehler` bleiben (der Fehler ist kein Beleg, aber auch keine Lücke) |
| 12 | `LIEGT` | gültig `X`, `X = L` | – | – | `LIEGT`, `last=t`, `nur_fehler` wahr, Herausforderer gelöscht |
| 13 | `LIEGT` | gültig `X`, `X ≠ L` | `X` ist neu oder ≠ `H`; `N ≥ 2` | – | `H=X`, `hn=1`, `nur_fehler` falsch; **rejected +1** |
| 14 | `LIEGT` | gültig `X`, `X ≠ L` | `X = H`, `hn+1 < N` | – | `hn = hn+1`, `nur_fehler` falsch; **rejected +1** |
| 15 | `LIEGT` | gültig `X`, `X ≠ L` | (`X = H` und `hn+1 ≥ N`) oder `N = 1` | `Entfernt`, dann `Platziert(X)`/`Gesperrt` | `LIEGT`, `L=X`, `last=t`, `nur_fehler` wahr, Herausforderer gelöscht; **rejected +1** |

Zu den Zeilen:

*   **Zeile 11 (`fehler` bei liegender Figur):** Ein Fehlerzyklus ist weder ein
    Beleg dafür, dass die Figur da ist (`last` wird nicht erneuert), noch dafür,
    dass sie weg ist. Eine **ununterbrochene Fehlerfolge** (`nur_fehler` wahr)
    lässt die Figur bis zu `error_hold_ms` (5 s) als „liegt noch“ gelten: Ein
    defekter oder gestörter Leser soll die Wiedergabe nicht schon nach 1,1 s
    anhalten. Wird die Lücke seit der letzten gültigen Lesung `error_hold_ms`
    lang, kommt `REMOVED` (Zeitregel; `ERR` zeigt den Grund). Kommt vorher eine
    gültige Lesung von `L`, geschieht nichts. Kommt zwischen den Fehlern auch nur
    ein `nichts` (oder eine fremde Lesung), gilt wieder `remove_after_ms`, gemessen
    ab der letzten gültigen Lesung von `L`. Fehler und `nichts` im Wechsel
    verhalten sich also wie bisher.
*   **Zeile 10 (`nichts` bei liegender Figur):** löscht einen offenen
    Herausforderer; die Bestätigungen eines Wechsels müssen **unmittelbar
    aufeinander** folgen.
*   **Zeilen 13 bis 15 (Wechsel):** Eine andere Identität gilt erst nach `N`
    gleichen Lesungen in Folge. Dazwischen ändert sie weder die liegende Figur
    noch `last`. Eine einzelne verfälschte Kennung am Rand (CUJ 8) wird so zu
    `rejected +1` und sonst ignoriert.
*   **„gesperrt liegt“ → „Kennung liegt“** (dieselbe Figur, danach als Kennung
    gelesen): wie jeder andere Wechsel, `Entfernt` + `Platziert`. Der Box-Dienst
    beendet damit die Überraschungs-Serie und startet die Serie der Figur. Das
    ist gewollt.
*   **„Kennung liegt“ → `gesperrt`:** ebenso `Entfernt` + `Gesperrt`.
*   **Gleiche Kennung, offen oder entsperrt gelesen:** Zeile 12, keine Meldung.
*   **Zählung von `rejected`:** nur in den fett markierten Zeilen, jeweils
    einmal je Zyklus. Zeile 15 zählt auch die bestätigende Lesung.
*   **`PING`** (Abschnitt 8) ändert den Zustand des Entprellers nicht, auch nicht
    im Zustand `PRUEFT`; die Meldung einer liegenden Figur (`LIEGT`) wiederholt
    sich nur als Ausgabe.

### Protokoll-Ausgabe aus den Ereignissen

*   `Platziert(typ, uid)` → `PLACED uid=<uid> type=<typ> tonie=<0|1> seq=<n>`.
*   `Gesperrt` → `LOCKED seq=<n>`, danach `ERR code=unlock_failed detail=...`.
*   `Entfernt` → `REMOVED seq=<n>`.
*   Bei Wechsel stehen beide Zeilen im selben Schritt hintereinander; `seq` ist
    bei der zweiten um 1 höher.
*   `present` im Herzschlag ist `1`, wenn der Zustand `LIEGT` ist.

### Abfragezyklus der Firmware

*   Ein Zyklus beginnt alle `POLL_PERIOD_MS` (200 ms), gerechnet von Beginn zu
    Beginn. Dauert die Arbeit eines Zyklus länger (gemessen bis 176 ms,
    im Fehlerfall bis 500 ms), beginnt der nächste sofort danach.
*   Der Zeitstempel `t` eines Ergebnisses ist der Zeitpunkt am **Ende** der
    Arbeit des Zyklus.
*   Nach jedem Zyklus ist das HF-Feld aus (Strom sparen), wie in
    `firmware/tonie_test/`.
*   Wird die Zeit knapp (Zeitbudget im Design), ist die erlaubte Abhilfe, das
    zuletzt gelesene Protokoll zuerst abzufragen und `PN5180_CMD_TIMEOUT_MS` zu
    verkürzen. `POLL_PERIOD_MS` bleibt dabei unverändert.

## 10. Zeitkonstanten

### In der Firmware, Datei `firmware/tobibox-reader/include/timing.h`

Eingecheckt, ohne Geheimnisse. Die Namen sind verbindlich.

| Name | Wert | Bedeutung | Quelle |
|---|---|---|---|
| `POLL_PERIOD_MS` | 200 | Abfragezyklus, Beginn zu Beginn | Design, Baustein 1 |
| `CONFIRM_READS` | 2 | gleiche Lesungen in Folge für `PLACED`, `LOCKED` und Wechsel (3, falls die Messung in Stufe 1 zeigt, dass 2 nicht reichen) | Design, Baustein 1 |
| `REMOVE_AFTER_MS` | 1100 | `REMOVED` nach so langer Zeit ohne gültige Lesung der liegenden Figur, wenn dazwischen ein `nichts` oder eine fremde Lesung kam | Design, Baustein 1 |
| `ERROR_HOLD_MS` | 5000 | `REMOVED` bei **ununterbrochenen Lesefehlern** erst nach so langer Zeit seit der letzten gültigen Lesung (Fehlerzyklen zählen bis dahin als „Figur liegt noch“) | Entscheidung Tobias, 05.11. |
| `HEARTBEAT_INTERVAL_MS` | 2000 | Abstand der `HB` | Design, Baustein 2 |
| `ERR_MIN_INTERVAL_MS` | 2000 | Mindestabstand gleicher `ERR`-Codes | Festlegung dieses Vertrags |
| `PN5180_INIT_RETRY_MS` | 5000 | Abstand der Startversuche, wenn der PN5180 nicht antwortet | Festlegung dieses Vertrags |
| `PN5180_CMD_TIMEOUT_MS` | 30 | Zeitgrenze je PN5180-Befehl (heißt in `tonie_test` `COMMAND_TIMEOUT_MS`) | `firmware/tonie_test/config.example.h` |

Daraus folgt: Lücken aus `nichts` bis 1000 ms (= `REMOVE_AFTER_MS` − 100 ms)
führen zu keinem `REMOVED`. `REMOVE_AFTER_MS` muss größer als 5 × `POLL_PERIOD_MS`
sein (1000 ms Lücke plus Reserve). Die Abhebe-Zeit beträgt bis zu
`REMOVE_AFTER_MS` + 1 Zyklus. `ERROR_HOLD_MS` muss größer oder gleich
`REMOVE_AFTER_MS` sein. Lesefehler allein verzögern die Abhebe-Erkennung bis zu
`ERROR_HOLD_MS` + 1 Zyklus (gewollt, siehe Abschnitt 9, Zeile 11).

### Im Box-Dienst (Modulkonstanten in `reader.py`)

| Name | Wert | Bedeutung |
|---|---|---|
| `WATCHDOG_S` | 5 | Wächter-Alarm bei so langer Zeit ohne `HB` (Abschnitt 6) |
| `HELLO_TIMEOUT_S` | 2 | Wartezeit auf `HELLO` nach `PING` |
| `PING_TRIES` | 3 | Versuche, davor gilt die Verbindung als gescheitert |
| `RECONNECT_BACKOFF_S` | 0,25 · 0,5 · 1 · 2, danach 2 | Wartezeiten zwischen Verbindungsversuchen: der erste Versuch nach einem Ausfall folgt nach 0,25 s, dann verdoppelt sich die Wartezeit bis höchstens 2 s. Ein gültiges `HELLO` setzt die Folge zurück. |

Der Wert `LESER_FRIST_S = 3.0` (Frist im Zustand `unbekannt`, Karenzzeit des
Kerns) steht in `core-interface.md`. Er ist so gewählt, dass ein kurzer
USB-Aussetzer (Wiederverbinden mit dem Backoff oben, `PING`, `HELLO`, erneute
Meldung der Figur) die Wiedergabe nicht unterbricht.

## 11. Verhalten bei unbekannten oder ungültigen Zeilen

**Box-Dienst (`protocol.py`)**, Prüfreihenfolge, die erste zutreffende gewinnt:

| Fall | Grund (`reader-v1-examples.txt`) | Wirkung |
|---|---|---|
| leere Zeile | `empty_line` | still ignoriert |
| über 200 Zeichen | `too_long` | verworfen, protokolliert (WARNING) |
| Zeichen außerhalb 0x20 bis 0x7E | `not_ascii` | verworfen, protokolliert |
| Zeile beginnt mit einem Leerzeichen (auch nur Leerzeichen) | `bad_syntax` | verworfen, protokolliert (WARNING) |
| erstes Wort ist kein bekannter Zeilentyp (`HELLO PLACED LOCKED REMOVED HB ERR`) | `unknown_type` | verworfen, protokolliert (DEBUG, höchstens eine Meldung je Sekunde) |
| Syntaxfehler (Wort ohne `=`, doppelte Leerzeichen, Leerzeichen am Ende, leerer Wert, auch leeres `detail=`, ungültiger Schlüssel) | `bad_syntax` | verworfen, protokolliert (WARNING) |
| Schlüssel doppelt | `duplicate_key` | verworfen, protokolliert |
| Pflichtfeld fehlt | `missing_field` | verworfen, protokolliert |
| Wert verletzt Format oder Bereich (auch `detail` mit `|` oder `;` oder über 80 Zeichen) | `bad_value` / `bad_uid` | verworfen, protokolliert |
| `uid`, `type`, `tonie` passen nicht zusammen | `uid_type_mismatch` | verworfen, protokolliert |

*   **Eine ungültige Zeile hat nie eine halbe Wirkung:** Entweder sie ist
    gültig und wird vollständig verarbeitet, oder sie wird verworfen.
*   **Unbekannte Zusatzfelder** in einer bekannten Zeile werden ignoriert (nicht
    in der Auslegung), wie im Design („ignoriert und protokolliert“) aber nur
    leise: Ebene DEBUG, höchstens eine Meldung je Zeilentyp und Feldname und
    Minute. Das ist die Vorwärtskompatibilität.
*   **Unbekannte Zeilentypen** werden ignoriert. So kann spätere Firmware neue
    Zeilen senden, ohne ältere Dienste zu stören.
*   Die Firmware verhält sich auf der Befehlsseite genauso (Abschnitt 8).
*   Wiederholte Fehler gleicher Art sind in Protokoll und Tests zu begrenzen
    (höchstens eine Protokollzeile je Grund und Sekunde); die Zeile selbst wird
    immer verworfen.

## 12. Verbindungsaufbau (Box-Dienst, Modul `reader`)

1.  Gerät öffnen (Mac: Suchmuster `/dev/cu.usbmodem*`; Pi: festes
    `/dev/serial/by-id/…`), ohne DTR/RTS (Abschnitt 1).
2.  `PING` senden. Innerhalb `HELLO_TIMEOUT_S` muss ein `HELLO` kommen, sonst
    erneut `PING`, höchstens `PING_TRIES` Mal. Gelingt es nicht, Ausfall mit
    Grund `hello_timeout` (siehe unten), Verbindung schließen, nach
    `RECONNECT_BACKOFF_S` neu öffnen.
3.  `HELLO` prüfen: `proto` muss 1 sein. Sonst Ausfall mit Grund
    `proto_unbekannt`: **kein `LeserHallo`**, Prüfpunkt „Leser“ auf Fehler,
    weiter nach Backoff versuchen. Das Ereignis `LeserAlarm(proto_unbekannt)`
    geht an den Kern (es zählt wie jeder Alarm, siehe unten); nur das
    `LeserHallo` unterbleibt.
4.  Nach gültigem `HELLO`: Wächter starten, `seq`-Erwartung auf 0, Backoff
    zurücksetzen, Ereignis `LeserHallo` an den Kern. Meldet die Firmware danach
    dieselbe Figur erneut (`PLACED`/`LOCKED` mit `seq=0` nach `PING`, Abschnitt
    8, oder nach einem Neustart der Firmware), behält `reader` die bisherige
    Vorgangs-ID (`core-interface.md`, Abschnitt 3.1).
5.  Verliert der Dienst die Verbindung (Lesefehler, Gerät weg) oder löst der
    Wächter aus, gilt dasselbe wie bei Schritt 2: Ausfall melden, schließen,
    neu verbinden.
6.  Jedes gültige `HELLO` — beim Start der Firmware oder auf `PING` — hat
    dieselbe Wirkung. Der Dienst unterscheidet beide Fälle nicht.

### Ausfall und `LeserAlarm`

*   **Ein Alarm je Ausfall.** Ein Ausfall beginnt mit dem ersten Fehlschlag nach
    dem letzten gültigen `HELLO` (oder nach dem Start des Dienstes) und endet mit
    dem nächsten gültigen `HELLO`. Zu Beginn sendet `reader` genau **ein**
    `LeserAlarm` an den Kern. Weitere fehlgeschlagene Versuche im selben Ausfall
    senden keinen weiteren Alarm (nur Protokoll, DEBUG).
*   **Grund** des Alarms (die Zeichenketten des Ereignisses `LeserAlarm`):

    | `grund` | Wann |
    |---|---|
    | `getrennt` | Lesefehler oder Gerät weg bei bestehender Verbindung; auch: das Gerät lässt sich beim ersten Versuch nicht öffnen |
    | `kein_herzschlag` | `WATCHDOG_S` ohne gültige `HB` |
    | `hello_timeout` | nach `PING_TRIES` Versuchen kein `HELLO` |
    | `proto_unbekannt` | `HELLO` mit nicht unterstützter `proto` |

*   Der Kern pausiert nach einem bestätigten Verlust spätestens
    `LESER_FRIST_S` + `TAKT_S` = 3,1 s nach dem ersten Ereignis (Alarm oder
    `LeserHallo`), siehe `core-interface.md`, Abschnitt 9, Punkt 1.

## 13. Versionsregel

*   `proto` im `HELLO` ist die **Hauptversion** des Protokolls, hier 1.
*   **Ohne Erhöhung** von `proto` (rückwärts- und vorwärtskompatibel) sind
    erlaubt: neue **optionale** Zusatzfelder am Ende bekannter Zeilen (bei `ERR`
    **vor** `detail=`, Abschnitt 2, Regel 5), neue Zeilentypen, neue Fehlercodes.
    Alte Parser ignorieren sie (Abschnitt 11).
    Neue Pflichtfelder gibt es in Version 1 nicht.
*   **Erhöhung** von `proto` ist nötig bei jeder anderen Änderung: Feld entfernen
    oder umbenennen, Bedeutung oder Wertebereich ändern, Grammatik ändern, neues
    Pflichtfeld.
*   Der Box-Dienst unterstützt eine Liste von Hauptversionen (derzeit `{1}`). Ein
    `HELLO` mit anderem `proto` ist unverträglich (Abschnitt 12, Schritt 3).
*   Das Update-Paket (`manifest.json`, Feld `protokoll_version`) nennt die
    Hauptversion, die der Dienst erwartet, und `firmware_min` die kleinste
    Firmware-Version (`fw`, Vergleich als Zahlentripel). Eine Firmware unter
    `firmware_min` besteht den Selbsttest nicht.
*   Eine Änderung dieses Vertrags geht an die Projektleitung; die
    Beispieldatei wird im selben Schritt angepasst.

## Festlegungen in diesem Vertrag (Stand 05.11.)

Das Design lässt diese Einzelheiten offen. Entschieden wurde die einfachste
stimmige Lösung. „Bestätigt (05.11.)“ heißt: von Tobias oder der Projektleitung
bestätigt oder entschieden. Alle anderen Punkte sind noch offen.

1.  **`seq` zählt nur `PLACED`, `LOCKED`, `REMOVED`.** `HB`, `ERR` und `HELLO`
    haben kein `seq`, wie in der Zeilentabelle des Designs. Das Design sagt
    zugleich „zählt jede Meldung“; gemeint ist hier: jede Zustandsmeldung.
    Verlorene `HB` oder `ERR` zeigt `seq` deshalb nicht an (die `HB` zeigt der
    Wächter, `ERR` ist Diagnose).
2.  **`PING` setzt `seq` zurück und löst eine erneute Meldung aus.** Das Design
    sagt „`HELLO` setzt die Zählung zurück“ und „`HELLO` auch auf `PING`“.
    Damit beides zusammenpasst, setzt die Firmware auf `PING` ihr `seq` zurück
    und meldet eine liegende Figur sofort erneut (`PLACED`/`LOCKED` mit
    `seq=0`). So ist `PING` der Weg, nach dem Öffnen der Verbindung oder nach
    einem `present`-Widerspruch den Zustand abzugleichen. **Bestätigt (05.11.,
    Projektleitung):** Die erneute Meldung startet nie von selbst eine
    Wiedergabe; `reader` behält dafür die Vorgangs-ID (`core-interface.md`,
    Abschnitt 3.1 und 9.1).
3.  **Wechsel gilt als `REMOVED` + `PLACED`/`LOCKED`**, auch bei „gesperrt →
    Kennung“ und „Kennung → gesperrt“ (Abschnitt 9). Die Firmware meldet keinen
    „Aufstieg“ von gesperrt zu Kennung als eigene Zeile.
4.  **Bestätigt (05.11., Tobias): `fehler(code)`** mitten in der Entprellung
    verwirft den Kandidaten (Zeile 6). **Bei liegender Figur** zählen
    Lesefehler bis zu `ERROR_HOLD_MS` = 5 s als „Figur liegt noch“ (Zeile 11);
    erst nach 5 s ununterbrochener Fehler seit der letzten gültigen Lesung
    kommt `REMOVED` (und `ERR`). `nichts` behält die Regel `REMOVE_AFTER_MS`
    = 1,1 s. Ein `nichts` zwischen den Fehlern stellt die 1,1-s-Regel wieder her
    (Festlegung der Umsetzung, Marke `nur_fehler`).
5.  **Zeitregel vor der Eingabe (Schritt 0):** Eine Lücke von mindestens
    `REMOVE_AFTER_MS` führt auch dann zu `REMOVED`, wenn im selben Zyklus die
    liegende Figur wieder gelesen wird.
6.  **Fehlercodes:** `pn5180_no_response`, `pn5180_timeout` und `unlock_failed`
    nennt das Design; `bad_response`, `uid_invalid`, `bad_command` und
    `internal` kommen von diesem Vertrag. Der Prüfpunkt „Leser“ steht auf Fehler,
    solange in den letzten 10 s ein Code der Schwere „Fehler“ kam; die
    Abbildung auf `ok`/`fehler`/`getrennt`/`simulation` steht in
    `core-interface.md`, Abschnitt 12. `unlock_failed` ist ein Hinweis
    (Zusatzzeile nach `LOCKED`), kein Zyklusfehler.
7.  **Ratenbegrenzung** der `ERR`-Zeilen (`ERR_MIN_INTERVAL_MS` = 2000 ms je Code)
    und **Wiederholung** des PN5180-Starts (`PN5180_INIT_RETRY_MS` = 5000 ms).
8.  **Feldformate:** `fw` als `MAJOR.MINOR.PATCH` (damit `firmware_min`
    vergleichbar ist), `build` als 7 bis 12 Hexzeichen, höchstens 200 Zeichen je
    Zeile, `detail` höchstens 80 Zeichen ohne `|` und `;`.
9.  **Zeilenende:** Firmware sendet `\n`; der Dienst akzeptiert zusätzlich `\r\n`.
10. **Abfragezyklus 200 ms Beginn zu Beginn** (einschließlich der Arbeit des
    Zyklus), `cycle_ms` = Arbeitsdauer des letzten Zyklus.
11. **Erste `HB`** 2000 ms nach dem `HELLO`; `up` zählt seit dem Start des ESP32.
12. **`rejected`:** zählt gültige Lesungen, die der Bezugsfigur widersprechen
    (Tabelle Abschnitt 9). Das Design nennt „verfälscht oder abweichend“ ohne
    genaue Regel.
13. **Verbindungsaufbau-Zeiten** `HELLO_TIMEOUT_S` = 2, `PING_TRIES` = 3 und
    der Abgleich über `present` nach **zwei** abweichenden `HB`. **Bestätigt
    (05.11., Projektleitung):** Backoff 0,25 · 0,5 · 1 · 2 s, danach 2 s;
    Karenzzeit des Kerns `LESER_FRIST_S` = 3,0 s, damit ein kurzer
    USB-Aussetzer nicht pausiert. Offen: Ob 3,0 s für den echten Aussetzer
    (Neustart des ESP32 nach Spannungseinbruch) reichen, misst Stufe 1 am
    Gerät.
14. **Keine Verwerfung wegen `seq`:** Der Dienst verarbeitet gültige Zeilen
    immer, `seq` dient der Diagnose.
15. **Bestätigt (05.11., Projektleitung): ein `LeserAlarm` je Ausfall**, mit den
    Gründen aus Abschnitt 12 (Tabelle); `proto_unbekannt` löst keinen
    `LeserHallo` aus, wohl aber den Alarm.
16. **Parser streng bei `detail`** (`|`, `;`, über 80 Zeichen: `bad_value`;
    leeres `detail=`: `bad_syntax`); Zeile mit führendem Leerzeichen:
    `bad_syntax`; unbekannte Zusatzfelder: leise DEBUG-Meldung (Abgleich mit dem
    Design, das „ignoriert und protokolliert“ sagt).
17. **`up` aus 64-Bit-Zeit**, Ratenbegrenzung „mindestens 2000 ms seit der
    letzten Zeile“ auf der Zeitbasis des Zyklus-Ergebnisses, Reihenfolge der
    Zeilen innerhalb eines Schritts (Abschnitt 7, Regel 6).
