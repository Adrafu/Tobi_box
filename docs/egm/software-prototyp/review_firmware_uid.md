# Review Firmware: falsche Kennung am Rand (Schicht 1 und 2)

Prüfer: Goldfisch ohne Vorwissen. Stand: 09.11.2026, Repo-Stand `c1e1549`.
Gegenstand: Commit `5ed9e79` und die Quellen, auf die er sich bezieht.

**Wichtig vorweg:** `git show 5ed9e79` enthält nur Tests und Dokumente. Der Quellcode
der Änderung (`reader.cpp`, `classify.*`, `debounce.*`, `timing.h`) steht in
früheren WIP-Commits (`35d219e` und davor). Geprüft wurde der heutige Stand in
`firmware/tobibox-reader/`.

**Bauen und testen (alles grün):**
- `pio test -e native`: 53 von 53 Tests bestanden.
- `pio run -e esp32s3`: Build erfolgreich (Flash 24,9 %, RAM 6,9 %). Nichts hochgeladen.
- `include/config.h` wieder gelöscht. Im Repo wurde nichts geändert außer diesem Report.
- Zusatzrechnung in Python: CRC-Prüfwert "123456789" ergibt 0x906E, ein Beispielrahmen
  mit angehängter CRC ergibt den Rest 0xF0B8. Beides stimmt mit dem Code überein.

Quellen:
- Datenblatt PN5180 Rev. 3.0 (7.10.2016), Kopie `https://static.chipdip.ru/lib/101/DOC032101818.pdf`,
  Tabelle 83 (RX_STATUS_REG, Adresse 0013h) und Tabelle 82 (CRC_RX_CONFIG).
  Die NXP-Seite für C3/C4 war nicht abrufbar (404), die Revision C3/C4 wurde daher nicht
  Wort für Wort verglichen.
- PN5180-Bibliothek tueddy, Commit `69ec032` (Kopie im Scratchpad `pn5180/`).

---

## Befunde

### B1 (hoch, Risiko): Rahmenlänge 10 bzw. 12 Byte ist nicht belegt

- Datei: `src/classify.h:55-58`, `src/classify.cpp:122-136`, `src/reader.cpp:66-81`
- Szenario: Der Chip meldet für die Inventory-Antwort eines echten Tonies eine andere
  Länge als 10 oder 12 (zum Beispiel 11 oder 9, je nach RF-Konfiguration 0x0d/0x8d).
  Dann endet **jeder** Zyklus mit einem Tonie als `fehler(bad_response)`. Die Box
  würde nach 5 s (`ERROR_HOLD_MS`) Tonies als entfernt behandeln, also kein Tonie
  spielt mehr. Die Tests können das nicht zeigen, sie bauen den Rahmen selbst.
- Beleg: Das Datenblatt (Tabelle 83, Bits 8:0 `RX_NUM_BYTES_RECEIVED`) sagt nur "Anzahl
  empfangener Bytes". Es sagt nicht, ob die CRC mitgezählt wird. Tabelle 82 hat
  `RX_CRC_ENABLE` und `RX_CRC_INV` (invertierter Rest `F0B8h`); ob der Empfänger die CRC
  danach aus dem Puffer lässt, steht dort nicht. Die Bibliothek gibt auch keinen Hinweis:
  `getInventory` liest `len` Bytes und nimmt Bytes 2 bis 9 (`PN5180ISO15693.cpp:43-65`),
  `inventoryPoll` liest sogar `len+1` (`PN5180ISO15693.cpp:163`). Im Repo gibt es keine
  Messung der Länge am Gerät (`grep` in `docs/` ohne Treffer). Die Commit-Nachricht
  nennt nur Tests und Build.
- Vorschlag: Vor dem Abschluss einmal am Gerät die rohe Länge und den Rahmen mit einem
  guten Tonie ausgeben (Debug-Zeile, nicht dauerhaft). Dann in `classify.h` festhalten,
  welche Länge gilt, und den nicht vorkommenden Fall (10 oder 12) streichen, damit nicht
  tote Zweige "Sicherheit" vortäuschen. Falls die CRC im Puffer fehlt (Länge 10), ist
  Bit 16 in `RX_STATUS` die einzige CRC-Prüfung. Die Software-CRC wäre dann nie aktiv.
  Bitte auch festhalten, dass `RX_CRC_ENABLE` für die Konfiguration 0x0d wirklich gesetzt
  ist (Register `CRC_RX_CONFIG` einmal lesen). Sonst fängt Schicht 1 den
  Randfehler gar nicht, und nur Schicht 2 schützt.

### B2 (mittel): Fehlerflag des Tags wird als Rückgabewert missbraucht, zwei Fälle falsch

- Datei: `src/reader.cpp:77`, `src/classify.cpp:127-134`, `src/classify.cpp:87-91`
- Szenario 1: Bei Länge 10 oder 12 ist das Flag-Bit 0 gesetzt (nur durch Verfälschung
  möglich, im Code selbst so kommentiert). `inventoryChecked` gibt `buf[1]` zurück, das
  ist dann das DSFID. Hat der Tonie DSFID 0x00, ist der Rückgabewert 0 =
  `RC_OK`. Der Aufrufer (`reader.cpp:112`) übernimmt dann `uid`, und das ist **nur Nullen**
  (wegen `memset` in Zeile 52). Ergebnis: Eine Kennung `0000000000000000` wird als
  gültig gemeldet. Zweimal in Folge gelesen wäre das ein falsches PLACED.
- Szenario 2: Echter Fehlercode 0x0F ("unbekannt") der Tags landet als `RC_UNKNOWN_ERROR`
  und wird `fehler(bad_response)`, nicht "nichts". Der Test `test_frame_tag_error_flag_stays_nothing`
  (Code 0x0F) und der Kommentar in `classify.h:17-19` sagen das Gegenteil. Der Test prüft
  nur `FrameCheck::TagError`, nicht den Rückgabewert von `inventoryChecked`.
  Alle anderen Codes (außer 0 und 0x0F) laufen in den Entsperrversuch (`reader.cpp:120ff`)
  bei einem Tag, das vielleicht gar nicht im Privacy-Modus ist. Das konnte vorher
  auch passieren (Bibliothek `PN5180ISO15693.cpp:788-801` macht das gleiche), ist aber
  jetzt der Weg für **verfälschte** Rahmen.
- Beleg: `ISO15693_EC_OK = 0`, `ISO15693_EC_UNKNOWN_ERROR = 0x0f` (`PN5180ISO15693.h`);
  Rückgabe `buf[1]` in `reader.cpp:77`.
- Vorschlag: `TagError` nicht über `buf[1]` abbilden, sondern fest auf `RC_NO_CARD`
  (nichts) oder auf `RC_UNKNOWN_ERROR` (fehler). Für Bit 0 bei Länge 10/12 ist `fehler`
  richtig (es ist ein verfälschter Rahmen). Nur Länge 2/4 mit gültiger CRC ist ein echtes
  Tag-Fehlerflag. Zusätzlich einen Test auf Ebene `Reader` oder eine kleine reine
  Funktion `frameToRc(FrameCheck, buf)` in `classify.cpp` mit Tests für Code 0x00, 0x0F,
  0x01 und 0xA0.

### B3 (mittel): NTAG/ISO 14443A ist nicht geschützt, gleicher Fehler möglich

- Datei: `src/reader.cpp:86-102` (ruft `readCardSerial`), Bibliothek
  `PN5180ISO14443.cpp:88-330` und `:367-433`
- Szenario: Eine NTAG-Karte liegt am Rand, die Antikollisions-Antwort wird gestört.
  Die Bibliothek
  - liest die 5 Bytes der Antikollisionsstufe 1 (4 Byte Kennung + BCC) mit **abgeschalteter**
    Empfangs-CRC und prüft weder das BCC noch Fehlerbits in `RX_STATUS` (Parität) –
    das BCC (`cmd[6]`) wird verworfen;
  - schickt dann den Select-Befehl mit der Kennung, liest die SAK-Antwort mit
    `readData(1, ...)`, **ohne** zu prüfen, ob überhaupt etwas empfangen wurde. Eine
    verfälschte Kennung wird vom Tag nicht ausgewählt, die Bibliothek merkt das aber
    nicht, sie liefert die Kennung trotzdem (`return 4` bzw. `uidLength`);
  - bei 7-Byte-Kennung gilt das Gleiche für die zweite Stufe (Zeilen 273-306). Nur das
    Byte 0x88 (CT) wird geprüft.
  Es kann also dieselbe Art Fehler auftreten (falsche Kennung bei schwachem Feld), und
  Schicht 1 greift dort nicht. Nur Schicht 2 (3 gleiche Lesungen beim Wechsel) schützt
  die liegende Karte. Aus leerem Zustand genügen weiter 2 gleiche falsche Lesungen.
- Beleg: Bibliothekscode oben; `reader.cpp:91` ruft `readCardSerial` ohne weitere Prüfung.
- Vorschlag: Eine eigene Prüfung bauen oder die Bibliothek-Funktion ersetzen: BCC prüfen
  (XOR der 4 Byte = BCC; BCC muss mitgelesen werden), nach Select
  `rxBytesReceived() == 1` und `RX_STATUS`-Fehlerbits prüfen (Bits 16/17/18, Bit 16 nur
  mit eingeschalteter Empfangs-CRC). Wenn das zu viel für diesen Schritt ist, mindestens
  als bekannte Restlücke in `docs/protocol/reader-v1.md` und im Plan nennen. Der
  Befund wurde bisher nur bei Tonies (ISO 15693) beobachtet.

### B4 (niedrig): Verhalten gegenüber der Bibliothek leicht verändert

- Datei: `src/reader.cpp:54` und `:56-74`
- Szenario a: `sendData` liefert `false` (Chip nicht im Zustand WaitTransmit, BUSY-Zeitgrenze).
  Die Bibliothek ignoriert das Ergebnis und endet über "kein SOF" mit `EC_NO_CARD`
  (nichts). Jetzt wird es `fehler(bad_response, "inventory transfer error")`. Das ist
  vertretbar, kann aber bei einer leeren Box Warnungen erzeugen, falls das gelegentlich
  vorkommt (zählt in `errors`, hält die Figur nicht länger als 5 s).
- Szenario b: Die Bibliothek liest nach `readData` noch einmal `IRQ_STATUS` und
  verwirft den Rahmen, wenn `RX_SOF_DET` fehlt (`PN5180ISO15693.cpp:781-786`). Das fehlt in
  `inventoryChecked`. Da `RX_IRQ` und `RX_SOF_DET` vorher schon gesehen wurden, ist der
  Verlust klein.
- Reihenfolge der Chip-Befehle sonst gleich: `sendData`, `delay(10)`, `getIRQStatus` (SOF),
  Warteschleife auf `RX_IRQ` mit `commandTimeout`, `readRegister(RX_STATUS)`, `readData`,
  `clearIRQStatus(RX_SOF|IDLE|TX|RX)`. Die Zeit je Zyklus bleibt gleich (eine
  Registerabfrage weniger).
- Vorschlag: Szenario a beobachten (Zähler `errors` bei leerer Box im Dauerlauf). Falls
  es Warnungen gibt: `sendData`-Fehler wie bisher als "nichts" behandeln.

### B5 (niedrig): Restlücken im Entpreller

- Datei: `src/debounce.cpp:334-338` (Zeilen 3 und 4: `LEER`, `N=2`), `:364-388`
- a) Aus dem leeren Zustand (`LEER`) genügen weiter zwei gleiche Lesungen. Liegt ein Tonie
  am Rand, die Lesung setzt länger als 1,1 s aus (REMOVED) und kommt dann mit zweimal
  derselben falschen Kennung zurück, wird sie platziert. Das ist nach der Zeitbudget-Rechnung
  gewollt (1 s), aber eine Restlücke; Schicht 1 muss sie schließen.
- b) Alle `gesperrt`-Lesungen sind gleich (`Identity::operator==`). Ein Wechsel von einem
  gesperrten zu einem **anderen** gesperrten Tonie ohne Lücke über 1,1 s wird nicht erkannt.
  Das ist Teil des Designs, steht aber nirgends als Grenze im Vertrag.
- c) Dritte Lesung und Zeitregel: Die Wechsel-Lesungen aktualisieren `last_` nicht. Bei
  Herausforderer, Fehlerzyklus (löscht Herausforderer, Zeile 11), Herausforderer ... kann nach
  1,1 s `REMOVED` kommen, danach beginnt die Prüfung mit `N=2` von vorn. Das Ergebnis ist
  richtig (Tobie weg, neuer kommt), nur ein Wechsel mit vielen Fehlern dauert länger.
  Kein Fehler.

### B6 (niedrig): Kleinigkeiten in Kommentaren und Tests

- `src/classify.h:51`: "Tabelle 93". Im Datenblatt Rev. 3.0 ist es **Tabelle 83**
  (RX_STATUS_REG). Für C3/C4 nicht geprüft. Bitte Revision und Tabelle nennen.
- `test_classify.cpp`: `test_frame_with_one_wrong_bit_is_rejected_by_crc` ändert drei Bits
  (`0x42 ^ 0x4c`), nicht eins. Name anpassen oder ein einzelnes Bit nehmen (die CRC
  erkennt beides).
- `test_frame_tag_error_flag_stays_nothing`: Name stimmt nicht mit dem echten Verhalten
  überein (siehe B2).
- Die Parameter des Konstruktors `DebounceParams(confirm, remove, error, change)` haben eine
  andere Reihenfolge als die Felder (`confirm, change, remove, error`). Kein Fehler, aber
  eine Stolperfalle.

---

## Antworten auf die Prüffragen

1. **Datenblatt:** Bitlagen stimmen mit Rev. 3.0, Tabelle 83: Bit 16 `RX_DATA_INTEGRITY_ERROR`
   (falsche Parität oder CRC, Empfang geht weiter), Bit 17 `RX_PROTOCOL_ERROR`, Bit 18
   `RX_COLLISION_DETECTED`, Bits 19:25 Kollisionsposition, Bits 8:0 `RX_NUM_BYTES_RECEIVED`.
   Maske `0x00070000` und `0x1FF` sind richtig. Die tueddy-Bibliothek nutzt selbst
   `(rxStatus >> 18) & 1` für die Kollision (`PN5180ISO15693.cpp:145`).
   **CRC-16:** Polynom 0x8408 (gespiegelt 0x1021), Start 0xFFFF, Komplement beim Senden,
   niedriges Byte zuerst, Rest über den ganzen Rahmen 0xF0B8 – korrekt (das Datenblatt nennt
   selbst `F0B8h` als invertierten Vergleichswert, Tabelle 82). Testvektor `"123456789"
   -> 0x906E` ist der bekannte Prüfwert von CRC-16/X-25, und von mir nachgerechnet.
   **Länge 10/12:** nicht belegt (siehe B1).
2. **Bibliothek:** Reihenfolge der Chip-Befehle gleich (siehe B4). Nach einem verworfenen
   Rahmen sind die vier IRQ-Bits gelöscht (`reader.cpp:74` vor der Auswertung), bei
   zu großer Länge alle (`:69`), und `readIso15693` beginnt jeden Zyklus mit `reset()`.
   Der Chip bleibt damit sauber. Nach `readData`-Fehler (`:73`) wird nicht gelöscht, wie
   in der Bibliothek, wegen `reset()` im nächsten Zyklus aber ohne Folgen.
3. **Entsperren:** Weg Inventory (keine Antwort, `RC_NO_CARD`) → `getRandomNumber` →
   `disablePrivacyMode` → `clearIRQStatus(0xffffffff)` → zweites `inventoryChecked` ist
   gegenüber vorher unverändert (Diff `3f763be..HEAD`, `reader.cpp`). Ein Tonie im
   Privacy-Modus antwortet auf das erste Inventory nicht und erreicht den Entsperrweg weiter.
   Neu: Ein verworfenes zweites Inventory ergibt `fehler` statt "gesperrt" (Zeile 155).
4. **NTAG:** nicht berührt und nicht geschützt (B3).
5. **Entprellung:** Tabelle in `reader-v1.md` (Zeilen 13-15 mit `C`) stimmt mit
   `debounce.cpp:363-388` überein. Fehlerzyklus löscht den Herausforderer (Zeile 11),
   `nichts` ebenso (Zeile 10), ein neuer Herausforderer startet bei 1 (Zeile 13), `LOCKED`↔Kennung
   braucht 3 Lesungen. Grenzfälle siehe B5.
6. **Zeiten:** `POLL_PERIOD_MS`, `REMOVE_AFTER_MS` und `ERROR_HOLD_MS` unverändert, die
   `static_assert`s in `timing.h` gelten. Die Zeit je Zyklus bleibt gleich. Ein Wechsel
   braucht 3 Zyklen (400 ms nach der ersten Lesung des neuen Tobie), das steht auch in
   `docs/timing.md`. Das Auflegen aus leer bleibt bei 2 Lesungen, unter 1 s.
7. **Tests:** `test_repeated_corruption_twice_is_no_change` prüft den Fall wirklich
   (mit der alten Regel `C=2` wäre `removed` 1). Die Rahmentests prüfen nur die reine Funktion,
   nicht `inventoryChecked` (nur auf dem ESP32 gebaut). Lücken: B1, B2.

---

## Geprüft, ohne Befund

- Bitlagen und Masken von `RX_STATUS` (Bits 16/17/18, `& 0x1ff`) gegen Datenblatt.
- CRC-16 (Polynom, Startwert, Komplement, Byte-Reihenfolge, Rest 0xF0B8) und Testvektor.
- Eigener Puffer (`buf[16]` frisch genullt), keine alten Bytes aus `readBufferStatic16`;
  Längenprüfung vor `readData`, kein Überlauf (`len > 16` abgefangen).
- Fehler beim Lesen von `RX_STATUS` (SPI tot, `0xFFFFFFFF`) wird als Fehlerbit verworfen.
- Reihenfolge der Chip-Befehle gegenüber der Bibliothek und Löschen der IRQ-Bits.
- Entsperr-Weg im Privacy-Modus (Ablauf unverändert).
- Zeitgrenzen und `static_assert`s in `timing.h`; Zyklusdauer unverändert.
- Zustandstabelle gegen `debounce.cpp` (Zeilen 10 bis 15), Klemmung `change_reads >= confirm_reads`,
  Zeitüberlauf (Test vorhanden).
- Vertrag `reader-v1.md` (`bad_response`, `CHANGE_CONFIRM_READS`) und `docs/timing.md` stimmen
  mit dem Code überein.
- Tonie-Passwort: nicht im Repo, `config.h` nur lokal erzeugt und wieder gelöscht,
  `git status` sauber (außer diesem Report).
