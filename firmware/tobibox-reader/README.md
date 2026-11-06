# tobibox-reader

Firmware des NFC-Lesers der Tobi Box: ESP32-S3 (SuperMini, 4 MB Flash) mit
PN5180. Sie liest NTAG-Karten (ISO 14443A) und Tonies (ISO 15693, auch im
Privacy-Modus), entprellt die Lesungen und schreibt Zeilen nach
`docs/protocol/reader-v1.md` auf die USB-Serielle (HWCDC). Auf der Seriellen
stehen nur Protokollzeilen, kein Diagnosetext.

Aufbau: `reader.cpp` (ein Abfragezyklus) → `debounce.cpp` (Entpreller, reine
Logik) → `protocol.cpp` (Zeilen, `seq`, Zähler). `debounce.cpp` und
`protocol.cpp` enthalten keine Arduino-Typen und laufen auch auf dem Rechner.
Alle Zeitkonstanten stehen in `include/timing.h`.

## Versionen (fest gepinnt)

| Was | Version |
|---|---|
| PlatformIO-Plattform | pioarduino `55.03.37` (Release-ZIP in `platformio.ini`) |
| Arduino-Core | 3.3.7 (steckt in dieser Plattform-Version) |
| PN5180-Bibliothek | `tueddy/PN5180-Library` Commit `69ec032289457b1adae3e1b269ca22ea16aa46fd` (2.2.0) |
| Unity (nur Tests) | 2.6.1 |
| Board | `esp32-s3-devkitc-1` mit `board_upload.flash_size = 4MB`, Partitionstabelle `default.csv` |

## Bauen

Passwort und Pins stehen in `include/config.h` (gitignored, wird **nie**
committet). Im Repo liegt nur die Vorlage:

```
cd firmware/tobibox-reader
cp include/config.example.h include/config.h
# in config.h das eigene Tonie-Passwort eintragen (TONIE_PRIVACY_PASSWORD)
pio run -e esp32s3
```

Mit dem Platzhalter-Passwort (`00 00 00 00`) baut die Firmware und läuft; ein
fremder Tonie meldet dann `LOCKED`. Die gebaute Firmware nicht weitergeben: Das
Passwort steht im Flash.

Der Git-Hash für `HELLO build=` kommt beim Bauen aus `git` (mit Zusatz
`-dirty`, wenn der Ordner Änderungen hat; ohne Git `unknown`).

## Flashen am Mac

Alle `pio`-Befehle laufen in diesem Ordner:

```
cd ~/Tobi_box/firmware/tobibox-reader
pio run -e esp32s3 -t upload
```

Der SuperMini wird über seinen USB-Anschluss (USB-Serial/JTAG) geflasht,
Auto-Reset geht dabei von selbst. Klappt das nicht, beim Einstecken die
BOOT-Taste halten. Der Anschluss heißt am Mac `/dev/cu.usbmodem*`.

## Serielle Ausgabe ansehen

```
pio device monitor -b 115200
```

Beim Öffnen mit DTR/RTS kann der Chip zurückgesetzt werden (neues `HELLO`).
Der Box-Dienst öffnet ohne DTR/RTS. Befehl zum Testen: `PING` eingeben und
Enter drücken, die Firmware antwortet mit `HELLO` und meldet eine liegende
Figur erneut. Alles andere beantwortet sie mit `ERR code=bad_command`.

Die Firmware setzt `setTxTimeoutMs(0)`: Ist niemand am anderen Ende, werden
Zeilen verworfen statt zu blockieren (eine Lücke in `seq` zeigt das).

## Tests auf dem Rechner

```
cd ~/Tobi_box/firmware/tobibox-reader
pio test -e native
```

Braucht weder `config.h` noch Hardware, aber einen C++-Compiler
(Mac: `xcode-select --install`). Die Umgebung `native` baut nur
`classify.cpp`, `debounce.cpp` und `protocol.cpp`.

* `test/test_classify/`: Einordnung der Chip-/Tag-Antworten (`classify.h`):
  Fehlerflag des Tags = `nichts`, nur Uebertragungsfehler = `fehler`,
  Entsperren (keine Karte = `nichts`, Passwort abgelehnt = `LOCKED`),
  Gesundheitsprobe (Platzhalter unveraendert = Timeout, `0xFFFFFFFF` = keine Antwort).

* `test/test_debounce/`: Entpreller mit den Standardwerten aus `timing.h`
  (2-gleich-Regel, 1,0-s-Lücke, 1,1-s-Abheben, Figurwechsel, verfälschte
  Kennung am Rand, gesperrter Tonie, „gesperrt → offen“, `fehler(code)`
  mitten in der Entprellung, Fehlerfolgen, Zeitüberlauf).
* `test/test_protocol/`: liest `docs/protocol/reader-v1-examples.txt` **zur
  Laufzeit** (Pfad vom Projektordner aus `../../docs/protocol/reader-v1-examples.txt`,
  Rückfall relativ zur Testdatei). Es gibt keinen erzeugten Header, die Datei
  ist die einzige Quelle. Geprüft werden:
  * Abschnitt 1: jede Zeile durch den Referenz-Parser `parseReaderLine()`
    (Felder und Ablehnungsgründe); bei `OK`-Zeilen zusätzlich der Formatierer
    byte-genau.
  * Abschnitt 2: Befehls-Parser und Antwort der Firmware.
  * Abschnitt 3: alle Zeitabläufe durch `Protocol` (Zeilen, Zähler, `present`).
    Jede erzeugte Zeile muss außerdem vom Parser angenommen werden.

## Zykluszeit im Fehlerfall

Der Vertrag nennt im Fehlerfall bis 500 ms je Zyklus. Die Firmware haelt das so
weit wie moeglich ein: scheitert `setupRF()` (HF-Feld startet nicht), endet der
Zyklus sofort mit `pn5180_timeout`; nach einem Chip-Fehler entfaellt `setRF_off()`
(der naechste Zyklus beginnt mit `reset()`); hat das erste Protokoll schon
450 ms gebraucht, wird das zweite nicht mehr begonnen; scheitert
`readCardSerial()` nach >= 450 ms, ist es `pn5180_timeout` statt `nichts`.

Nicht vermeidbar (Bibliothek): `setRF_on()` wartet bis zu 500 ms auf das
Feld-Signal, und `activateTypeA()` wertet dessen Fehlschlag nicht aus. Der
schlimmste Fall eines Zyklus ist daher etwa 500 ms (RF_ON-Wartezeit) plus
Befehls-Zeitgrenzen (je 30 ms) und die 10-ms-Pausen der Bibliothek, also
rund 600 ms. Das ist selten (nur bei totem oder falsch verdrahtetem Chip) und
`cycle_ms` zeigt es an.

## Bekannte Eigenheiten

* Nach einem Wiederverbinden der USB-Serielle (HWCDC) koennen noch alte Zeilen
  im Sendepuffer stehen und zuerst ankommen. Das behandelt die Box-Seite; die
  Firmware ergaenzt nichts.
* Ein ICODE-SLIX2 (Tonie im Privacy-Modus) antwortet auf ein falsches Passwort
  gar nicht. Die Firmware fragt dann erneut die Zufallszahl ab: antwortet das
  Tag noch, ist es `LOCKED`, sonst `nichts` (Figur ist weg).
* Ein Fehlerflag des Tags (z. B. "nicht unterstuetzt") gilt wie in `tonie_test`
  als `nichts`; nur Uebertragungs-/Chip-Fehler werden `fehler`.
* Es gibt in der Firmware keinen Pfad fuer `ERR code=internal` (keine
  Warteschlange); `onInternalError` wurde entfernt.
