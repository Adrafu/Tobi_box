# Hardware-Prüfung Tobi Box (Goldfisch)

* **Datum:** 11.11.2026
* **Geprüfter Stand:** Commit `1780d7b`, Plan Rev. 3.20
* **Auftrag:** Hardware-Entscheidungen samt Ladesockel auf Logik und Vollständigkeit prüfen. Nichts geändert außer dieser Datei.
* **Gelesen:** `docs/plan/stueckliste-und-psp.md`, `docs/plan/bestellliste-charge1.md`, `docs/plan/uebergabe.md`,
  `docs/egm/ladestation/` (alle Dateien), `hardware/ladesockel/` (README, `.scad`), `docs/egm/ein-aus/` (Brief, Recherche,
  Entwurf Rev. 2, Review Hardware, Resolve), `firmware/tobibox-reader/` (`platformio.ini`, `config.example.h`, `timing.h`, README, Quellen),
  dazu Stellen aus `docs/designs/box-software.md`, `docs/betrieb/pisugar-wecker.md`, `box/src/tobibox/` (`led.py`, `reader.py`,
  `headphones.py`, `controls.py`) und `box/config/tobibox.mac.example.toml`.
* **Kennzeichnung:** Aussagen über das Repo stehen mit Datei:Zeile. **[Web]** = heute nachgelesen, Quelle am Ende.
  **[gerechnet]** = eigene Rechnung aus Zahlen des Repos, nicht gemessen. **[aus Kenntnis]** = nicht nachgelesen, im Datenblatt prüfen.
  **[Vermutung]** = begründete Annahme, die eine Messung klären muss.
* **Zählung:** 28 Befunde: 6 hoch, 13 mittel, 9 niedrig. Die Nummern sind fest; die Übersicht unten zeigt, in welchem Abschnitt jeder Befund steht.

---

## Kurzfassung

Das Konzept ist in sich stimmig und baubar. Die großen Weichen sind richtig gestellt: USB-C-Stecker statt offener Kontakte, der ESP32 als Wächter am Akku, Messung M0 vor allem anderen.
Vor dem Bestellen und Löten sind aber sechs Punkte zu klären.
Erstens fehlt am Abgriff des Akku-Pads eine Sicherung, und die „Unterspannung des Reglers bei etwa 3,1 V“ gibt es bei den genannten Reglern nicht (H1).
Zweitens hängt „am Strom immer bereit“ an der ungeprüften Annahme, dass am Ladeeingang im Akkubetrieb keine Spannung steht; sonst schaltet die Box nie ab oder startet endlos neu (H2).
Drittens stützt der Kragen des Sockels das Kippen der Box nach der Rechnung aus den Maßen nicht ab; die Box steht auf einem Podest von 32 × 14 mm, und der Stecker wird zum Drehpunkt (H3).
Viertens fehlt der LED-Ring im Laufzeit-Budget: Beim Hören leuchten alle 40 LEDs dauernd, das sind rechnerisch 0,6 bis 1,1 W zusätzlich (H4).
Fünftens gibt es für die neue Wächter-Elektronik weder Schaltplan noch Träger-Platine, fast alle Bauteile sind winzige SMD-Teile, und die Stückliste im Plan nennt noch die entfallenen Teile (H5, H25).
Sechstens liegen die geplanten ESP32-Pins 14 bis 18 und 21 auf der SuperMini nur als Lötflächen auf der Unterseite; mit den Randpins geht der Plan genau auf, ohne Reserve (H6).
Die übrigen Befunde sind Lücken in Schaltungsdetails (Weiche, Weck-Pegel, Kopfhörer-Kontakt, Hauptknopf, 5-V-Verteilung, Wärme am Sockel) und veraltete Stellen in den Dokumenten.

---

## Übersicht der Befunde

| Nr. | Schwere | Befund | Abschnitt |
|---|---|---|---|
| H1 | hoch | Abgriff am Akku-Pad: keine Sicherung, keine echte Unterspannungs-Abschaltung | A |
| H2 | hoch | `STROM_IN` hängt an einer ungeprüften Annahme über den Ladeeingang | A |
| H3 | hoch | Der Kragen stützt das Kippen nicht ab; die Box steht auf einem Podest von 32 × 14 mm | C |
| H4 | hoch | Der LED-Ring beim Hören fehlt im Laufzeit-Budget | A |
| H5 | hoch | Kein Schaltplan, keine Träger-Platine, die Stückliste kennt die neuen Teile nicht | D |
| H6 | hoch | SuperMini: Die geplanten Pins 14 bis 18 und 21 gibt es nur als Lötflächen auf der Unterseite | B |
| H7 | mittel | Ring-Weiche: drei Zustände mit einem Pin, und der ESP32 wird einziger Schalter für den Ring | A |
| H8 | mittel | Wecken aus dem Tiefschlaf: EXT1 kennt nur einen Pegel für alle Pins, der Hall-Schalter braucht beide | A |
| H9 | mittel | Kopfhörer: Ein Schaltkontakt soll drei Dinge tun, die Schaltung ist nicht gezeichnet | A |
| H10 | mittel | Hauptknopf: Akku-Spannung am Pi-GPIO, hartes Ausschalten, Widerspruch zu „ein Druck“ | A |
| H11 | mittel | 5-V-Verteilung: Abgriff, Summenstrom und Einschaltstoß sind nicht festgelegt | A |
| H12 | mittel | Wärme und Akku am Sockel: immer an, immer voll, im geschlossenen Gehäuse | A |
| H13 | mittel | USB ohne VBUS: Rückspeisung auch im Tiefschlaf messen; zwei Regler beim Flashen | A |
| H14 | mittel | Stecktiefe: 0,2 mm Luft gegen eine Maßkette aus sieben gedruckten Maßen | C |
| H15 | mittel | Buchse im Zapfen: Bauform ungeklärt, Halt nur über Kleber, Angaben widersprechen sich | C |
| H16 | mittel | Hall-Schalter gegen Tonie-Halt, Antennenmitte und Lautsprecher | C |
| H17 | mittel | M2 misst mit der falschen Last, wenn der 5-V-Wandler kommt | A |
| H18 | mittel | Pinplan des Pi: veraltete Zeilen, freier SPI ungenutzt, Platzhalter widersprechen dem Plan | B |
| H19 | niedrig | Pad-10-Puls beim Anstecken: Wettlauf mit „Einschalten bei Strom“ | A |
| H20 | niedrig | Ladeeingang: Spannungsgrenze, Überspannungsschutz, schwache Quellen | A |
| H21 | niedrig | Kein Test auf Störgeräusche | A |
| H22 | niedrig | Mono im Verstärker statt in der Software (Option) | A |
| H23 | niedrig | Der dauernd versorgte ESP32 lässt sich nicht mehr stromlos machen | A |
| H24 | niedrig | Bauraum: Das Druckmuster legt Boxmaße fest, bevor es ein Maßkonzept gibt | C |
| H25 | mittel | Der Plan nennt entfallene Teile und überholte Regeln weiter | D |
| H26 | niedrig | Ladestations-Entwurf Rev. 5 widerspricht sich und späteren Entscheidungen | D |
| H27 | niedrig | Reihenfolge der Messungen: Abhängigkeiten sind nicht aufgeschrieben | D |
| H28 | niedrig | Kleinigkeiten | D |

Abschnitte: A Strom und Elektrik, B Pinbelegung, C Ladesockel, D Vollständigkeit und Planung.

---

## A. Strom und Elektrik

### H1 · hoch · Abgriff am Akku-Pad: keine Sicherung, keine echte Unterspannungs-Abschaltung

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:251-253`, `docs/egm/ein-aus/resolve.md:31` (P10), `docs/egm/ein-aus/design_draft.md:371`.
* **Problem:**
  1. Vom Akku-Plus (PiSugar-Pad 2) läuft eine Leitung quer durch die Box zum Regler. Eine Sicherung ist nirgends vorgesehen. Scheuert die Litze nach einem Sturz durch, ist das ein Kurzschluss direkt an einer 5000-mAh-Zelle, in einem Gerät für Kleinkinder. Ob Pad 2 hinter der Schutzschaltung der Zelle liegt, ist nicht dokumentiert (`docs/egm/ein-aus/research.md:16`, `:217`).
  2. P10 verlässt sich auf eine „Unterspannung des Reglers (etwa 3,1 V)“. Die genannten Kandidaten haben die nicht: Der TPS63900 arbeitet ab 1,8 V, seine Abschaltschwelle liegt bei etwa 1,75 V **[Web]**. Ein LDO der TPS7A02-Klasse hat gar keine passende Schwelle, er reicht den sinkenden Akku einfach durch **[aus Kenntnis]**. Der ESP32 läuft dann bis in seinen Brownout und kann dort in einer Neustart-Schleife mehr Strom ziehen als im Schlaf **[Vermutung]**.
  3. Folge: Nach dem Tiefstand-Aus des Pi (5 %, etwa 250 mAh Rest) zieht der Wächter mit 1,3 bis 2,5 mA weiter (`design_draft.md:371`). Das sind rechnerisch 4 bis 8 Tage bis zur Notabschaltung der Zelle **[gerechnet]**. Eine Woche Urlaub mit leerer Box reicht für eine Tiefentladung. „Den Akku schützt der PiSugar“ (P10) gilt nur, wenn Pad 2 mit abgeschaltet wird. Das ist offen (M2).
* **Vorschlag:**
  * Rückstellbare Sicherung oder Feinsicherung (0,5 bis 1 A) direkt am Pad 2, Leitung kurz und mechanisch gesichert. Vorwiderstand (1 kΩ) im Pfad BAT → PhotoMOS → Pad 10.
  * Eigener Spannungswächter mit Hysterese (Klasse TPS3839 / XC61, unter 1 µA **[aus Kenntnis]**) am Enable des Reglers, Schwelle 3,2 bis 3,3 V, Wiedereinschalten erst bei etwa 3,5 V.
  * M2 erweitern: Verhalten von Pad 2 bei leerem Akku (schaltet der PiSugar es ab?), Strom des Wächters bei 3,0 V.
* **Quelle:** TI TPS63900 (Eingang 1,8 bis 5,5 V, UVLO etwa 1,75 V, Gehäuse WSON 2,5 × 2,5 mm) https://www.ti.com/product/TPS63900

### H2 · hoch · `STROM_IN` hängt an einer ungeprüften Annahme über den Ladeeingang

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:57-58` (Z03, Z04), `:194`, `:292`, `:505` (Tor T1), `:521` (M13); `docs/egm/ladestation/design_draft.md:152-153`, `:191` (T8).
* **Problem:** `STROM_IN` ist ein Teiler an der Eingangsspannung der USB-C-Buchse. Liegt er hoch, schläft der ESP32 nicht und weckt den Pi wieder (Z04). Das ist richtig, solange am Ladeeingang nur dann Spannung steht, wenn wirklich ein Netzteil steckt. Zwei Fälle sind nicht geprüft:
  1. **Rückspeisung:** Steht am Eingang (Pad 8) im Akkubetrieb eine Spannung, gilt die Box dauernd als „am Strom“. Sie geht nie aus, oder sie fährt herunter und startet sofort wieder. Der Akku ist am Morgen leer.
  2. **Abklingen:** Nach dem Abziehen entlädt nur der Teiler (250 kΩ) die Eingangskondensatoren. Das kann Sekunden dauern **[Vermutung]**; die Entprellung rechnet mit 1 s (`design_draft.md:239`).
  Die Messung dazu steht nur im Ladestations-Test T8 und in M13, und M13 gehört nicht zum Tor T1 (M1, M2, M7, M8). `STROM_IN` ist aber schon in Schritt 1 „Pflicht“ (P1).
* **Vorschlag:** Vor dem Festlegen der Schaltung am PiSugar-Muster messen: Spannung an Pad 8 im Akkubetrieb (Pi an, Pi aus, Hibernate), Abklingzeit nach dem Abziehen, Verhalten mit schwacher Quelle. Ein Entladewiderstand (etwa 10 kΩ) am Eingang macht den Pegel eindeutig. M13 in das Tor T1 aufnehmen. Der PiSugar erkennt externe Spannung ebenfalls nur über die Spannung am Eingang **[Web]**, der Fehler träfe also beide Quellen.
* **Quelle:** PiSugar 3, Pad-Tabelle (Pad 8 = 5-V-Eingang, Pad 11 = 5-V-Ausgang) und I²C-Datenblatt (Register 0x02 Bit 7) https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series , https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-i2c

### H4 · hoch · Der LED-Ring beim Hören fehlt im Laufzeit-Budget

* **Fundstelle:** `docs/plan/stueckliste-und-psp.md:376-387` (Laufzeit), `:580` („Läuft: grünes Atmen, 12 bis 25 %“); `box/src/tobibox/led.py:97`, `:171-174`; `docs/egm/ein-aus/design_draft.md:364-372`.
* **Problem:** Im Zustand „läuft“ leuchten alle 40 LEDs grün, dauernd, zwischen 12 und 25 % (`led.py:171-174`). Rechnung: Grün voll plus etwas Blau sind je LED 13 bis 25 mA (aus 30 bis 60 mA für Vollweiß; der Plan rechnet mit 60 mA, `stueckliste-und-psp.md:69-70`). Bei im Mittel 18,5 % und 40 LEDs sind das 95 bis 190 mA, dazu 28 bis 40 mA Ruhestrom des Rings (`docs/egm/ein-aus/research.md:19`). Zusammen **0,6 bis 1,1 W [gerechnet]**.
  Der Plan nennt für die Wiedergabe 1,6 bis 1,9 W, ohne den Ring auszuweisen. Der Pi allein liegt bei 1,0 bis 1,25 W (`research.md:34-43`), dazu Leser und Verstärker. Der Ring ist darin kaum enthalten. Vier Stunden Hören kosten dann 2,4 bis 4,4 Wh mehr; aus 8,2 bis 10,0 Wh am Tag (`design_draft.md:372`) werden 10,6 bis 14,4 Wh von 15 Wh. Das 8-Stunden-Ziel ist ohnehin „knapp“ (`stueckliste-und-psp.md:684`).
* **Vorschlag:** Am echten Ring messen (steht als offen in `stueckliste-und-psp.md:760`, aber nur als Helligkeit, nicht als Strom). Danach entscheidet Tobias: beim Hören weniger LEDs (zum Beispiel 8 von 40), dunkler (3 bis 6 %) oder nach einigen Sekunden aus wie bei Pause. Laufzeit-Tabelle 1.5 mit dem gemessenen Wert neu rechnen.
* **Quelle:** eigene Rechnung; Ruhestrom APA102-2020 0,7 bis 1 mA je LED https://memcpy.io/apa102-led-current-usage.html

### H7 · mittel · Ring-Weiche: drei Zustände mit einem Pin, und der ESP32 wird einziger Schalter für den Ring

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:163-165`, `:304`, `:152-158`; `docs/egm/ein-aus/resolve.md:10` (R1); `docs/plan/stueckliste-und-psp.md:583`; `box/src/tobibox/reader.py:67-78`.
* **Problem:**
  1. Die Weiche braucht drei Zustände (ESP32, Pi, neutral). Der Pinplan hat dafür einen Pin (GPIO 4). Ein 74AHCT125 hat vier Puffer mit je einer Freigabe, aktiv low **[aus Kenntnis]**. Für „entweder ESP32 oder Pi“ braucht es einen Inverter, für „neutral“ ein zweites Signal.
  2. Ring-Strom und Weiche steuert nur noch der ESP32. Hängt der ESP32, wird er vom Dienst neu gestartet (`reader.py:67-78`) oder ist die Firmware defekt, dann steht die Weiche auf neutral und der Ring ist stromlos. Genau dann soll der Pi aber „Leser unterbrochen: gelb, langsam blinkend“ zeigen (`stueckliste-und-psp.md:583`). Das geht nicht mehr.
  3. Offen ist, woraus der Weiche-Chip versorgt wird. Hängt er an der ungeschalteten 5-V-Schiene, kann ein hoher Ausgang den abgeschalteten Ring über dessen Dateneingänge speisen **[Vermutung]**.
* **Vorschlag:** Schaltung zeichnen, bevor Vertrag B1 bis B15 eingefroren wird. Eine einfache Form: 74AHCT157 (Auswahl und Freigabe, gesperrt = Ausgänge low) oder 74AHCT125 für den ESP32 und 74AHCT126 für den Pi am selben Signal **[aus Kenntnis, Datenblatt prüfen]**. Den Chip aus der geschalteten Ring-Schiene versorgen, dann ist „Ring aus“ zugleich „neutral“ und ein Pin reicht. Notweg für den Pi: Vorgabe der Weiche ist „Pi“, sobald die 3,3 V des Pi anliegen, der ESP32 übersteuert nur während des Lauflichts; die Freigabe des Ring-Schalters ist „ESP32 oder ein freier Pi-GPIO“ (frei sind 7, 12, 13, 16, `stueckliste-und-psp.md:421`).
* **Quelle:** Repo; Bausteine 74AHCT125 / 126 / 157 aus Kenntnis, Datenblatt prüfen.

### H8 · mittel · Wecken aus dem Tiefschlaf: EXT1 kennt nur einen Pegel für alle Pins, der Hall-Schalter braucht beide

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:191`, `:206`, `:298-301`.
* **Problem:** Der Entwurf weckt über EXT1 mit `ANY_HIGH`. Beim ESP32-S3 dürfen die EXT1-Pins keine unterschiedlichen Pegel haben **[Web]**. Der Hall-Schalter DRV5032 zieht seinen Ausgang **low**, wenn ein Magnet da ist **[Web]**. „Magnet kommt“ ist also eine fallende Flanke und weckt mit `ANY_HIGH` nicht. Der Entwurf will den Pin je nach Lage auf „Magnet weg“ oder „Magnet da“ scharf machen (`:191`); das geht mit EXT1 allein nur für eine Richtung.
* **Vorschlag:** Den Hall-Pin über EXT0 wecken lassen (ein Pin, Pegel je Schlaf frei wählbar, neben EXT1 erlaubt). EXT0 hält die RTC-Peripherie an, das kostet etwa 1 µA mehr **[aus Kenntnis]**. Äußere Pull-Widerstände statt der internen. In die Messfirmware `lpcd_probe` und in M6 aufnehmen. PN5180-IRQ, `STROM_IN` und `VBUS_SENSE` sind aktiv high und passen zu EXT1.
* **Quelle:** ESP-IDF, Sleep Modes (ESP32-S3) https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/api-reference/system/sleep_modes.html ; TI DRV5032 https://www.ti.com/lit/gpn/DRV5032

### H9 · mittel · Kopfhörer: Ein Schaltkontakt soll drei Dinge tun, die Schaltung ist nicht gezeichnet

* **Fundstelle:** `docs/plan/stueckliste-und-psp.md:173-177` (Punkt 28), `:303`, `:367-374`, `:416`, `:509`; `box/config/tobibox.mac.example.toml:110-111`; `box/src/tobibox/headphones.py:7-9`.
* **Problem:** Der Kontakt soll den Verstärker stumm schalten (SD_MODE nach Masse), „Stecker drin“ an GPIO 26 melden und beides in Hardware.
  1. Übliche 3,5-mm-Buchsen haben keinen Kontakt nach Masse. Ihr Schaltkontakt liegt **ohne** Stecker an der Tonleitung und öffnet beim Einstecken **[aus Kenntnis, am gekauften Teil prüfen]**. Das ist das Gegenteil von „zieht SD_MODE auf GND“ und von `aktiv_niedrig = true` (`tobibox.mac.example.toml:111`).
  2. Die Tonleitung des PCM5102A schwingt um Masse, mit 2,1 V effektiv, also bis etwa ±3 V **[Web, Spitze gerechnet]**. Ein Pi-GPIO an diesem Kontakt bekäme negative Spannung.
  3. SD_MODE und GPIO 26 können nicht am selben Kontakt hängen: Ohne Stecker sähe GPIO 26 den Pegel von GPIO 4 (über 1 kΩ) und meldete bei stillem Verstärker „Stecker drin“. Eine Diode zur Trennung scheitert an der Abschaltschwelle von SD_MODE (0,16 V) **[Web]**.
  4. Der PCM5102A ist ein Line-Ausgang, Last mindestens 1 kΩ **[Web]**. Mit dem Widerstandsteiler als festem Deckel hängt der Pegel am Ohr von der Impedanz des Kopfhörers ab.
* **Vorschlag:** Buchsentyp festlegen: zwei getrennte, vom Ton isolierte Schaltkontakte, oder ein Kontakt plus ein kleiner N-FET, der SD_MODE zieht. Schaltung zeichnen und in 3.2.6 prüfen, auch mit abgestürztem Dienst (8.3.6). Pegel mit dem echten Kinder-Kopfhörer in dB messen. Auf der PCM5102A-Platine muss XSMT auf high liegen, sonst bleibt sie stumm **[Web]**.
* **Quelle:** TI PCM5102A (SLAS859) https://www.ti.com/product/PCM5102A ; MAX98357A-Datenblatt (SD_MODE-Schwellen 0,16 / 0,77 / 1,4 V) https://www.analog.com/en/products/max98357a.html

### H10 · mittel · Hauptknopf: Akku-Spannung am Pi-GPIO, hartes Ausschalten, Widerspruch zu „ein Druck“

* **Fundstelle:** `docs/plan/stueckliste-und-psp.md:47-50`, `:182-185`, `:418`, `:507`, `:699`; `docs/betrieb/pisugar-wecker.md:117-118`; `docs/egm/ein-aus/design_draft.md:200`; `docs/egm/ein-aus/research.md:15`, `:171`.
* **Problem:**
  1. Der Arcade-Knopf verbindet Pad 10 mit BAT (3,0 bis 4,2 V, `research.md:15`). Der Rückfall „Knopf zusätzlich an einen GPIO“ (`pisugar-wecker.md:117-118`, `pin_haupt`) legt bis 4,2 V an einen 3,3-V-Pin. Beim Einschalten ist der Pi noch aus; dann speist der Akku über den Pin in den stromlosen Pi.
  2. Das Bit „Soft Shutdown“ des PiSugar ist nach jedem Neustart aus und bestimmt, was ein langer Druck tut **[Web]**. Ohne dieses Bit trennt ein langer Druck vermutlich hart **[Vermutung]**. Ein Kleinkind hält Knöpfe gern fest. Punkt 30 und 3.2.4 nennen das als offen; es gehört vor die erste Kinder-Nutzung.
  3. Der Plan entscheidet „Einschalten: ein Druck, Anti-Mistouch aus“ (`stueckliste-und-psp.md:699`, PSP 5.6.5 `:598`). Der Ein/Aus-Entwurf lässt Anti-Mistouch „wie ab Werk“, also an (`design_draft.md:200`). Dann braucht das Kind „kurz, dann lang“ zum Einschalten (`research.md:171`). Anti-Mistouch fällt außerdem nach einem vollständigen Reset auf „an“ zurück **[Web]**.
* **Vorschlag:** Für `pin_haupt` einen Teiler vorsehen (zum Beispiel 100 kΩ / 220 kΩ), nie direkt. Am Muster klären: Wirkung von Lang ohne und mit Soft-Shutdown, wer das Bit bei jedem Start setzt. Tobias entscheidet den Widerspruch (Frage 5 unten).
* **Quelle:** PiSugar 3 I²C-Datenblatt (0x02 Bit 3 Anti-Mistouch, 0x03 Bit 4 Soft Shutdown) https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-i2c

### H11 · mittel · 5-V-Verteilung: Abgriff, Summenstrom und Einschaltstoß sind nicht festgelegt

* **Fundstelle:** `docs/plan/stueckliste-und-psp.md:69-72` (Punkt 8), `:296`, `:397`, `:510`; `docs/egm/ein-aus/design_draft.md:519` (M11).
* **Problem:** Der PiSugar speist den Pi über Federstifte an den Header-Pins (`:397`). Wo Verstärker, DAC und Ring ihre 5 V holen, steht nirgends. Hängen sie am Header des Pi, läuft alles über diese Federstifte: Pi bis 0,8 A, Verstärker im Mittel bis 0,7 A mit Spitzen über 1 A, Ring 0,6 A am Deckel **[gerechnet]**. Im ungünstigen Fall sind das zusammen über 2 A, mit Spitzen nahe der Grenze des PiSugar (5 V, maximal 3 A **[Web]**). Der Pi meldet Unterspannung ab 4,63 V (`design_draft.md:519`). Der 1000-µF-Elko lädt beim Einschalten schlagartig; ob der Wandler des PiSugar das ohne Aussetzer startet, ist offen **[Vermutung]**.
* **Vorschlag:** Verstärker, DAC und Ring mit eigenen Leitungen sternförmig am 5-V-Ausgangs-Pad (Pad 11) und an GND (Pad 1) anschließen, nicht am Pi-Header. Ein Massepunkt für alles, auch für den Wächter-Regler und das USB-Kabel. M11 erweitern: Einschalten mit 1000 µF, laute Bässe plus Ring plus Pi-Start, bei 20 % Akku.
* **Quelle:** PiSugar 3 Series (Ausgang „5V-3Amax“) https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series

### H12 · mittel · Wärme und Akku am Sockel: immer an, immer voll, im geschlossenen Gehäuse

* **Fundstelle:** `docs/plan/stueckliste-und-psp.md:543-546` (4.6), `:749`; `docs/egm/ein-aus/design_draft.md:462` (E3); `docs/egm/ladestation/research_qi.md:49-54` (PiSugar-Issue #168).
* **Problem:** Am Sockel läuft der Pi Tag und Nacht, der Akku wird geladen und dann bei 100 % gehalten. Der PiSugar nennt für seinen Chip 50 bis 60 °C bei 2 A Ladestrom und bis 80 °C bei 3 A **[Web]**. Die Zelle sitzt direkt an dieser Platine; sie verträgt beim Laden nur 45 °C (`docs/egm/ladestation/research_qi.md:49-53`, Antwort des Herstellers). PSP 4.6.3 misst „Temperatur unter Last“, aber nicht „Laden plus Pi an, Gehäuse zu, auf Teppich oder Bett“. Dauernd voll und warm altert ein LiPo schnell. E3 fragt nur nach der Ladegrenze, nicht nach der Temperatur.
* **Vorschlag:** Neue Messung: Temperatur an der Zelle beim Laden von leer, Box geschlossen im Sockel, Pi in Bereit, zwei Stunden. Kriterium: Zelle unter 45 °C. Der PiSugar hat einen Ladeschutz (hält bei etwa 80 %), Register 0x20 Bit 7; er ist nach jedem Neustart aus **[Web]**, der Dienst müsste ihn bei jedem Start setzen. Die Chip-Temperatur ist über Register 0x04 lesbar und taugt als Warnung an HA.
* **Quelle:** https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series , https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-i2c

### H13 · mittel · USB ohne VBUS: Rückspeisung auch im Tiefschlaf messen; zwei Regler beim Flashen

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:258-260`, `:515` (M7), `:254`, `:236`; `firmware/tobibox-reader/platformio.ini:22-23`.
* **Problem:**
  1. M7 misst den Strom über D+ „bei Pi aus, ESP32 wach“. Der ESP32 schläft aber 16 Stunden am Tag neben dem ausgeschalteten Pi. Bleibt der Pull-up an D+ im Tiefschlaf an, fließen bis etwa 2 mA in den Pi **[gerechnet: 3,3 V über 1,5 kΩ]**. Das wäre mehr als das ganze Aus-Budget.
  2. Die SuperMini hat einen eigenen Regler. Steckt jemand zum Flashen ein normales Kabel mit VBUS an (Mac), arbeiten zwei Regler auf derselben 3,3-V-Schiene. Der Entwurf verbietet das selbst (`:278`).
* **Vorschlag:** M7 um „ESP32 im Tiefschlaf“ erweitern. Vor einem USB-Schalter den billigen Weg prüfen: Pull-up an D+ per Register abschalten, solange `VBUS_SENSE` tief ist; die Register-Header sind auch im Arduino-Core vorhanden **[aus Kenntnis]**. Flash-Weg festschreiben: im eingebauten Zustand nur über den Pi oder mit einem Kabel ohne VBUS; sonst den Regler der SuperMini entfernen.
* **Quelle:** Repo und eigene Rechnung.

### H17 · mittel · M2 misst mit der falschen Last, wenn der 5-V-Wandler kommt

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:252`, `:273`, `:511`.
* **Problem:** M2 belastet Pad 2 mit „150 mA Spitze“. Bei Variante A speist ein Aufwärtswandler die Sendestufe mit 5 V. Der PN5180 zieht dort 180 mA typisch, 250 mA maximal (`docs/egm/ein-aus/research.md:82`). Aus 3,0 bis 3,7 V Akku sind das 0,3 bis 0,5 A, dazu der ESP32 **[gerechnet]**.
* **Vorschlag:** Reihenfolge: M0, dann Variante wählen, dann M2 mit der Last dieser Variante (für A mindestens 0,6 A in 10-ms-Pulsen). Sicherung aus H1 danach bemessen.
* **Quelle:** Repo (`docs/egm/ein-aus/research.md:82`, dort aus dem NXP-Datenblatt) und eigene Rechnung.

### H19 · niedrig · Pad-10-Puls beim Anstecken: Wettlauf mit „Einschalten bei Strom“

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:57` (Z03), `:199-201`; `docs/egm/ein-aus/research.md:14`.
* **Problem:** „Einschalten bei Strom“ ist beim PiSugar ab Werk an (`research.md:14`). Kommt Strom, schaltet der PiSugar selbst ein, und der ESP32 pulst nach 200 ms zusätzlich Pad 10. Die Regel „nur wenn 5 V fehlen“ prüft den Beginn des Pulses. Schaltet der PiSugar während des Pulses ein, kann der Druck als „Einfach“ ankommen (Play/Pause) **[Vermutung]**.
* **Vorschlag:** Bei `reason=strom` erst 2 bis 3 s auf die 5 V warten, dann pulsen. M9 misst die Zeit „Strom → 5 V“.
* **Quelle:** nur Repo.

### H20 · niedrig · Ladeeingang: Spannungsgrenze, Überspannungsschutz, schwache Quellen

* **Fundstelle:** `docs/egm/ladestation/design_draft.md:36`, `:125-126`, `:143-153`; `docs/egm/ein-aus/design_draft.md:521`.
* **Problem:** Die PiSugar-Doku nennt für den Eingang 4,5 bis 5,2 V **[Web]**. Das Netzteil liefert nominal 5,1 V. Die Leerlaufspannung ist nicht gemessen. Die Buchse im Boden ist die einzige Stelle, an der Kinderhände, Teppich und fremde Ladegeräte an die Elektronik kommen; ein Schutz ist nicht genannt. Der Anschluss läuft über Pad 8 an der eigenen Schutzbeschaltung der PiSugar-Buchse vorbei **[Vermutung]**. Die Box liest die Stromzusage der Quelle nicht (nur Widerstände an CC); eine schwache Quelle kann einbrechen (M13).
* **Vorschlag:** In T0 die Leerlaufspannung des Netzteils notieren. Eine TVS-Diode (5 V) und ein kleiner Kondensator direkt an der Buchse. M13 mit einem 0,5-A- und einem 1-A-Ladegerät.
* **Quelle:** PiSugar 3 Series (Eingang „4.5V-5.2V“) https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series

### H21 · niedrig · Kein Test auf Störgeräusche

* **Fundstelle:** `docs/plan/stueckliste-und-psp.md:661` (8.4.4), `:656`.
* **Problem:** Der Plan prüft „LED-Flackern bei NFC-Abfrage“, aber keine Geräusche. Der Leser zieht alle 200 ms einen Strompuls (bis 250 mA), der Ring taktet, das WLAN sendet in Bursts. Im Kopfhörer kann das als Ticken oder Sirren hörbar sein **[Vermutung]**.
* **Vorschlag:** Neuer Test in 8.x: Stille abspielen, Kopfhörer und Lautsprecher bei höchster erlaubter Lautstärke, dabei Leser, Ring-Muster und Sync. Abhilfe wäre die Sternverdrahtung aus H11.
* **Quelle:** nur Repo.

### H22 · niedrig · Mono im Verstärker statt in der Software (Option)

* **Fundstelle:** `docs/plan/stueckliste-und-psp.md:52-56` (Punkt 5), `:364-365`.
* **Problem:** Der Software-Downmix macht auch den Kopfhörer mono. Der MAX98357A mischt selbst (L+R)/2, wenn SD_MODE über einen großen Widerstand getrieben wird (etwa 630 kΩ bei 3,3 V **[Web, Formel aus dem Datenblatt]**). Dann bliebe der Datenstrom stereo.
* **Vorschlag:** Nur prüfen, wenn Stereo am Kopfhörer gewünscht ist. Vorsicht: Hat die Verstärker-Platine einen Pull-up von 1 MΩ nach 5 V (Adafruit), schaltet der Verstärker mit dem großen Widerstand nicht mehr ab **[gerechnet]**. Verträgt sich nicht ohne Weiteres mit H9.
* **Quelle:** MAX98357A-Datenblatt, Link bei H9.

### H23 · niedrig · Der dauernd versorgte ESP32 lässt sich nicht mehr stromlos machen

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:249-254`; `box/src/tobibox/reader.py:67-78`.
* **Problem:** Heute setzt ein Aus- und Einschalten der Box auch den Leser zurück. Mit dem Wächter am Akku nicht mehr. Der einzige Weg ist der Neustart über USB (`reader.py:67-78`); er setzt voraus, dass der USB-Teil des Chips noch antwortet.
* **Vorschlag:** Watchdog der Firmware einschalten. Zusätzlich einen freien Pi-GPIO über einen Transistor an den EN-Pin des ESP32 legen (harter Reset durch den Dienst).
* **Quelle:** nur Repo.

---

## B. Pinbelegung

### H6 · hoch · SuperMini: Die geplanten Pins 14 bis 18 und 21 gibt es nur als Lötflächen auf der Unterseite

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:293-308`; `docs/egm/ein-aus/resolve.md:32` (P11); `firmware/tobibox-reader/include/config.example.h:10-15`.
* **Problem:** Die SuperMini führt am Rand nur 5V, GND, 3V3, TX (43), RX (44) und GPIO 1 bis 13 heraus. GPIO 14 bis 18 und 21 liegen als kleine Flächen auf der Unterseite **[Web]**. Der Pinplan legt IRQ, `STROM_IN`, Hall, `VBUS_SENSE`, Pad-10-Schalter und Ring-Schalter genau dorthin (`:298-303`). Dünne Drähte an Unterseiten-Flächen sind in einem Gerät, das Stürze überstehen soll, die schwächste Stelle. Der Entwurf sagt nur „am Exemplar zählen“ (`:308`).
  Mit den Randpins allein geht es genau auf **[gerechnet]**: Frei sind 1 bis 7, 43, 44 (neun Pins, 8 bis 13 hat der PN5180). Gebraucht werden vier Weck-Eingänge, Pad-10-Schalter, Ring-Schalter, Weiche, Ring-Daten und Ring-Takt (neun). Kein Pin bleibt für den Enable des 5-V-Wandlers, ein zweites Weiche-Signal oder den ADC. GPIO 3 müsste mitbenutzt werden.
* **Vorschlag:** Vor dem Löten entscheiden:
  * **Weg 1, nur Randpins:** Weck-Eingänge auf 4 bis 7 (RTC-fähig), gehaltene Ausgänge auf 1 und 2, Weiche auf 3, Ring-Daten und -Takt auf 43 und 44 (müssen nicht RTC-fähig sein, die Konsole läuft über USB). Dafür: Weiche mit einem Signal (H7), Wandler dauernd an (Variante A ohne Enable).
  * **Weg 2:** anderes ESP32-S3-Board mit mehr Randpins und ohne Lade-IC und LED (das erspart auch das Ablöten aus R7).
  * **Weg 3:** Träger-Platine, auf der die SuperMini flächig aufgelötet wird (passt zu H5).
* **Quelle:** https://www.espboards.dev/esp32/esp32-s3-super-mini/

### H18 · mittel · Pinplan des Pi: veraltete Zeilen, freier SPI ungenutzt, Platzhalter widersprechen dem Plan

* **Fundstelle:** `docs/plan/stueckliste-und-psp.md:395-422`, `:353-356`; `box/config/tobibox.mac.example.toml:110`, `:120-124`; `box/src/tobibox/led.py:142`.
* **Problem:**
  1. Die Tabelle führt den RC522 noch auf GPIO 8, 9, 10, 11, 25 (`:403-406`, `:415`). Zeile 422 sagt, sie entfallen. „Frei: GPIO 7, 12, 13, 16“ (`:421`) stimmt damit nicht; frei sind auch 8 bis 11 und 25.
  2. Die Begründung „APA102 nicht auf SPI0, sonst liest der Ring jede NFC-Abfrage mit“ (`:353-356`) gilt nicht mehr, der Leser hängt am USB. Bit-Bang aus Python für 40 LEDs mit Überblendungen und Atmen (`:586`) kostet auf dem Pi 3A+ dauernd Rechenzeit und damit Strom **[Vermutung]**. Ein Treiber für den echten Ring existiert noch nicht; `led.py` liefert fertige Bytes (`led.py:142`), die genau zu SPI passen.
  3. Die Platzhalter in der Beispiel-Konfiguration weichen vom Plan ab: Kopfhörer `gpio_pin = 17` (Plan: 26; 17 ist Encoder A), Drehregler 12 / 13 (Plan: 17 / 27), `pin_haupt = 26` (Plan: 26 ist der Kopfhörer). Wer sie übernimmt, baut Doppelbelegungen.
  4. Das KY-040-Modul hat Pull-ups nach seinem Plus-Pin **[aus Kenntnis]**. Es muss an 3,3 V hängen, nicht an 5 V.
* **Vorschlag:** Tabelle bereinigen. Ring auf SPI0 legen (MOSI GPIO 10, Takt GPIO 11) und über `spidev` ausgeben; die Weiche sitzt dahinter wie geplant. Platzhalter an den Plan angleichen. Konflikte habe ich im Plan selbst nicht gefunden: I²C 2/3, SD_MODE 4, Tasten 5/6, UART 14/15, Encoder 17/27/22, I²S 18/19/21, Ring 23/24, Kopfhörer 26 sind überschneidungsfrei.
* **Quelle:** Repo; Pinbelegung des Pi (SPI0 auf GPIO 10 / 11) aus Kenntnis.

Zum ESP32 sonst: GPIO 8 bis 13 für den PN5180 stimmen zwischen Entwurf und Firmware (`config.example.h:10-15`). GPIO 19/20 (USB), 0, 45, 46 (Strapping) und 48 (LED) werden gemieden. Der IRQ-Draht des PN5180 fehlt in der Firmware und ist im Entwurf als neu vermerkt (`design_draft.md:298`).

---

## C. Ladesockel

### H3 · hoch · Der Kragen stützt das Kippen nicht ab; die Box steht auf einem Podest von 32 × 14 mm

* **Fundstelle:** `docs/egm/ladestation/design_draft.md:55` (A4), `:76-81`, `:99-101`, `:185` (T2); `hardware/ladesockel/druckmuster_fuehrung.scad:34-37`, `:67-71`, `:101`, `:140`, `:246`; `hardware/ladesockel/README.md:198-201`.
* **Problem (aus den Maßen gerechnet, am Druckmuster zu prüfen):**
  1. **Worauf steht die Box?** Die Tasche ist so tief wie der Kragen hoch ist (`.scad:140`). Der Boxboden schwebt 3 mm über dem Mulden-Boden (`sitz_h`, `.scad:37`), die TPU-Ecken ragen 2 mm vor und hängen im 3 mm tiefen Freistich (`.scad:34-36`). Die gesteckte Box liegt also nur mit dem Taschendach auf der Kragen-Oberkante, einer Fläche von 32 × 14 mm mit dem Schacht in der Mitte. Sie wippt.
  2. **Kippen nach hinten:** Der Spalt zwischen Boxboden und Mulde ist hinten nur 0,9 mm (`.scad:246`, `README.md:200`). Nach knapp 1° liegt die Bodenkante auf, und die Box dreht um diese Kante. Dabei hebt sich die Tasche vom Kragen: je Grad etwa 1 mm. Der Kragen ist kegelig (3 mm auf 14 mm je Seite, `.scad:67-71`); je Millimeter Anheben wächst das Spiel um 0,2 mm. Bei 5° ist die Tasche 5,2 mm angehoben und berührt den Kragen nirgends mehr. **Den Weg begrenzt dann nur der Stecker**, der schräg aus der Buchse gezogen wird.
  3. **Kippen nach vorne:** Vorne ist der Spalt 5,1 mm. Der Kragen fängt die Box erst nach etwa 2° (0,5 mm Spiel auf 14 mm). Ein USB-C-Stecker hat in der dünnen Richtung nur etwa 1 bis 1,5° Spiel **[aus Kenntnis]**. Der Stecker trägt also zuerst. Danach geht das ganze Moment in den Kragen: 60 N oben an der Box (T2) sind rund 7 Nm, am 14 mm hohen Kragen etwa 500 N **[gerechnet]**. Der Kragen ist stehend gedruckt und reißt dann entlang der Schichten.
  4. Der Halter ist „axial nicht beweglich“ und lässt nur ±0,5 mm seitlich zu (`.scad:101`). Kippen kann er nicht.
  Anforderung A4 („Hebeln stützen Kragen und Tasche ab, nicht der Stecker“) ist damit in der Richtung vor und zurück nicht erfüllt. Das ist die dünne, schwache Richtung des Steckers. Ein Kind hebt eine Box selten gerade ab; es kippt sie.
* **Vorschlag:** Vor dem 18-Stunden-Druck des Sockels entscheiden und an der Kragenprobe testen:
  * **Stecker kippt mit:** Halter so weich oder gelenkig, dass der Stecker 10 bis 15° folgt und zurückfedert (so machen es Handy-Docks). Dann ist das Abkippen ein erlaubter Weg.
  * **Feste Auflage:** Die Box soll breit aufliegen, zum Beispiel auf vier festen Anschlägen am Mulden-Rand, nicht auf der Kragen-Oberkante.
  * T2 und T9 um schräges Abheben erweitern: 2000 Zyklen mit 10 bis 15° Kippung, nicht nur gerades Stecken. Kragen liegend oder mit Metallstift verstärkt drucken.
* **Quelle:** eigene Rechnung aus den Maßen im `.scad`; Spiel des USB-C-Steckers aus Kenntnis.

### H14 · mittel · Stecktiefe: 0,2 mm Luft gegen eine Maßkette aus sieben gedruckten Maßen

* **Fundstelle:** `hardware/ladesockel/druckmuster_fuehrung.scad:93`, `:143`, `:231`; `hardware/ladesockel/README.md:47-49`, `:213-214`; `docs/egm/ladestation/design_draft.md:87`, `:98-100`.
* **Problem:** Die Stecklänge ist 6,5 mm, die Metallschale 6,7 mm (`.scad:93`, `:143`). Es bleiben 0,2 mm. Die Tiefe ergibt sich aus Kragenhöhe, Schulter, TPU-Flansch (drückt sich ein), Sitz des Steckers im Halter, Taschentiefe, Zapfenhöhe und Sitz der Buchse. Bei ±0,2 mm je Maß sind ±0,5 mm realistisch **[gerechnet]**. Fällt die Kette zu kurz aus, sitzt die Box mit ihrem Gewicht und jedem Aufsetzstoß auf dem Stecker; der Halter ist axial fest (`README.md:47-49`). Fällt sie zu lang aus, rastet der Stecker nicht. Das zweite ist vielleicht sogar gut: Ohne Rastung sinkt die Abzugskraft, und das Problem „Sockel hebt mit ab“ (dortiger Befund H1, `docs/egm/ladestation/review_rev4.md:18`) wird kleiner.
* **Vorschlag:** In T0 mitmessen: Abzugskraft und Kontakt (auch CC) bei voller Tiefe und 0,5 / 1,0 / 1,5 mm davor. Danach die Solltiefe bewusst wählen, eher 0,5 mm vor dem Anschlag, und im `.scad` als eigenen Parameter mit Toleranz führen.
* **Quelle:** eigene Rechnung aus den Maßen im `.scad`.

### H15 · mittel · Buchse im Zapfen: Bauform ungeklärt, Halt nur über Kleber, Angaben widersprechen sich

* **Fundstelle:** `docs/egm/ladestation/design_draft.md:80`, `:122-124`, `:202`; `docs/egm/ladestation/resolve.md:145`, `:152`; `hardware/ladesockel/README.md:22-25`, `:133-136`; `docs/egm/ladestation/einkaufsliste_buchse.md:8`, `:28`; `hardware/ladesockel/druckmuster_fuehrung.scad:122-126`.
* **Problem:**
  1. Drei Fassungen: „Sink-Breakout, im Zapfen verschraubt, nicht tauschbar“ (`design_draft.md:122-124`, `:202`), „kompakte Einbaubuchse mit Litzen statt Breakout“ (`resolve.md:152`), „austauschbares Modul, Vorgabe kleben“ (`README.md:22-25`, `.scad:126`).
  2. Die Recherche fand keine Platine mit 5,1 kΩ an beiden CC, die in den Zapfen passt (`einkaufsliste_buchse.md:28`). Sie rechnet zudem mit 11 × 5 mm Innenmaß (`:8`); das Modell lässt höchstens 10,6 × 4,6 mm (Zapfen 13 × 7, Wand 1,2). Eine liegende SMD-Buchse mit Platine ist etwa 3,3 + 1,6 mm dick **[aus Kenntnis]** und passt nicht.
  3. Bei jedem Abheben ziehen 8 bis 20 N an der Buchse nach unten, aus dem Zapfen heraus. In der Vorgabe hält sie nur Kleber. PETG lässt sich schlecht kleben **[aus Kenntnis]**. Ein Formschluss gegen das Herausziehen fehlt.
* **Vorschlag:** Eine eigene kleine Platine (Buchse, zwei Widerstände 5,1 kΩ, Lötflächen für Litze), breiter als der Buchsenraum, von **innen** durch das Taschendach eingesetzt. Dann hält eine Schulter die Zugkraft, der Kleber dichtet nur. Das passt zur Träger-Platine aus H5 (gleiche Bestellung). Die drei Fassungen im Entwurf auf eine bringen.
* **Quelle:** Repo; Aussagen zu Bauform und Kleben aus Kenntnis.

### H16 · mittel · Hall-Schalter gegen Tonie-Halt, Antennenmitte und Lautsprecher

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:291`, `:514` (M6); `docs/plan/stueckliste-und-psp.md:77-81` (Punkt 10), `:231-236`, `:533` (4.2.9).
* **Problem:** PSP 4.2.9 sieht „Magnet oder Stahlscheibe für die Tobies“ im Deckel vor (`:533`). Ein eigener Magnet im Deckel hält den Hall-Schalter dauernd ausgelöst. Eine Stahlscheibe bündelt das Feld und verschiebt die Schwelle. Test 5b (Stahlscheibe) ist noch offen (`:229-230`). Der Hall-Schalter muss nahe der Mitte sitzen, wo der Tonie-Magnet liegt; dort gilt „kein Metall über der Antennenmitte“ (`:234-236`). Schalter und drei Leitungen ändern die Abstimmung der Antenne ein wenig **[Vermutung]**.
* **Vorschlag:** Reihenfolge: erst Test 5b und die Entscheidung zum Tonie-Halt, dann M6. M6 ergänzen: Lesequote und Reichweite **mit** eingebautem Hall-Schalter, mit und ohne Stahlscheibe; Typ omnipolar wählen (die Pol-Richtung des Tonie-Magneten ist nicht belegt). Leitungen radial von der Antenne weg führen.
* **Quelle:** nur Repo.

### H24 · niedrig · Bauraum: Das Druckmuster legt Boxmaße fest, bevor es ein Maßkonzept gibt

* **Fundstelle:** `hardware/ladesockel/druckmuster_fuehrung.scad:35`, `:110`; `docs/egm/ladestation/design_draft.md:239`; `docs/plan/stueckliste-und-psp.md:521-523`, `:539`, `:692`.
* **Problem:** Das Muster nimmt eine Box von 120 × 120 mm an (`.scad:35`). Tasche und Dach brauchen in der Bodenmitte 18 mm Höhe, dazu die Kabelrinne. In denselben Würfel müssen Pi und PiSugar, die Leser-Platine mit Antenne, der 80-mm-Lautsprecher mit 0,5 bis 0,8 l dichter Kammer (`:539`), Ring, Tasten, Drehregler und die neue Wächter-Elektronik. Ein Maßkonzept (4.1) gibt es nicht; CAD soll erst nach dem Breadboard starten (`:692`).
* **Vorschlag:** Vor dem Druck von Sockel und Boxboden eine grobe Hüllrechnung: Volumen und Lage der großen Teile, Abstand Lautsprecher-Magnet zu Antenne und Hall-Schalter, Platz über der Tasche.
* **Quelle:** nur Repo.

Zu den übrigen Punkten des Sockels:

* **0° und 180°, Kippeln bei 90°:** in sich schlüssig gerechnet (`README.md:168-194`). Nur die Texte widersprechen sich, siehe H26.
* **Fremdkörper:** Münze und Löffel sind gelöst. Draht und Flüssigkeit im Schacht sind als Risiko angenommen (dortiger Befund H4, `docs/egm/ladestation/resolve.md:144`) und in T6/T7 abgedeckt.
* **Netzteil:** 5,1 V / 3 A passen zum Eingang des PiSugar (höchstens 3 A **[Web]**). Spielen und Laden teilen sich diese 15 W. Ob der PiSugar den Ladestrom dabei von selbst zurücknimmt, zeigen T4 und M13.
* **Powerbank und Auto:** Die Box leert die Powerbank, das ist entschieden (E1). Neu zu bedenken: Im Auto kommt mit der Zündung Strom, die Box startet, und ein liegender Tobie spielt sofort los (`stueckliste-und-psp.md:765`). Siehe Frage 9.

---

## D. Vollständigkeit und Planung

### H5 · hoch · Kein Schaltplan, keine Träger-Platine, die Stückliste kennt die neuen Teile nicht

* **Fundstelle:** `docs/plan/stueckliste-und-psp.md:282-330` (Stückliste), `:495-517` (PSP 3); `docs/egm/ein-aus/design_draft.md:247` („kein Schaltplan“), `:449`.
* **Problem:** Der Ein/Aus-Entwurf nennt nur Anforderungen. Die Stückliste im Plan ist nicht nachgezogen; der Entwurf listet das selbst als offen (`:449`). Es fehlen:

| Teil | Wofür | Fundstelle im Entwurf |
|---|---|---|
| Regler 3,3 V aus BAT (Buck-Boost oder LDO) | Wächter | `design_draft.md:251` |
| Sicherung am BAT-Abgriff, Spannungswächter | Schutz | fehlt ganz, siehe H1 |
| Pufferkondensatoren ≥ 100 µF, zweimal | PN5180, Regler | `:252` |
| PhotoMOS-Relais, zwei Widerstände | Pad 10 | `:282` |
| Lastschalter-IC | Ring | `:286` |
| Zweiter Puffer-Chip oder Umschalter, Inverter, 330 Ω, 10 kΩ | Weiche | `:163-164` |
| Hall-Schalter | Tonie-Wecken | `:291` |
| Teiler `STROM_IN`, `VBUS_SENSE`, Pad 10, je mit 10 nF | Messleitungen | `:258`, `:292` |
| Aufwärtswandler 5 V (nur Variante A) | TVDD | `:273` |
| USB-Schalter (nur wenn M7 es verlangt) | D+ / D− | `:259` |
| USB-Kabel ohne VBUS-Ader | ESP32 an Pi | `:258` |
| Netzteile 2 (+1), Buchsen-Platine, Winkelkabel, Stahl oder Klebepads | Sockel | `docs/egm/ladestation/design_draft.md:201-206` |
| Messgerät für µA (Klasse PPK2), Federwaage | M3, T0 | `design_draft.md:512`; Ladestation `:206` |

  Fast alle diese Teile sind SMD. Der TPS63900 hat ein Gehäuse von 2,5 × 2,5 mm ohne Beinchen **[Web]**; von Hand auf Lochraster geht das nicht. Der Plan kennt weder eine Platine noch ein Arbeitspaket dafür. Die Kosten (~575 €, `:330`) stimmen nicht mehr.
* **Vorschlag:** Nach M0 bis M2 einen Schaltplan zeichnen (PSP 1.3.1 gibt es als Posten) und eine kleine Träger-Platine vom Hersteller bestücken lassen: Regler, Wächter, Sicherung, PhotoMOS, Lastschalter, Weiche, Teiler, Steckplatz für SuperMini und PN5180-Kabel. Diesen Weg gab es schon einmal für den Sockel (`docs/egm/ladestation/resolve.md:10`). Die Buchsen-Platine aus H15 in dieselbe Bestellung. Neue PSP-Punkte unter 3.2 und 3.3; Stückliste und Kosten neu rechnen. Für die Messungen am Breadboard reichen Adapter-Platinen.
* **Quelle:** Repo; Gehäuse des TPS63900 siehe Quelle bei H1.

### H25 · mittel · Der Plan nennt entfallene Teile und überholte Regeln weiter

* **Fundstelle und Problem:** Pololu #5398, Pogo-Pins, Magnete, Reeds und Load-Switch sind seit R9/R10 entfallen (`docs/plan/stueckliste-und-psp.md:745-746`). Sie stehen noch an diesen Stellen:

| Stelle | Inhalt |
|---|---|
| `stueckliste-und-psp.md:62-67` | Punkt 7: Pololu #5398, zwei Ladeeingänge (ohne Vermerk „überholt“) |
| `:83-86` | Punkt 11: „Stand 3.18: zwei Reeds in Reihe“ |
| `:93-95` | Punkt 13: Magnete (für den Sockel entfallen; offen für den Tonie-Halt) |
| `:295`, `:297`, `:304`, `:305`, `:307` | Stückliste 1.1: #5398, Breakout + Pigtail, Pogo-Pins, Magnete, USB-C-Lasche |
| `:318`, `:319` | Stückliste 1.2: Dual-Ladestation mit 5 V/4 A, Load-Switch + Reed |
| `:358-359` | 1.4: „Load-Switch im Dock, Ideal-Diode in der Box“ |
| `:508`, `:512-517`, `:531`, `:548` | PSP 3.2.5, 3.5.x, 3.6, 4.2.7, 4.7.1 |
| `:649`, `:662` | Tests 8.2.4 „Andocken weckt nicht“, 8.4.5 „USB-C und Pogo gleichzeitig“ |
| `:384`, `:596`, `:599` | „Auto-Shutdown nach ~20 min“, 5.6.3, 5.6.8 mit 120 s (seit 3.19: 10 min, kein Kurz-Modus) |
| `:209-210`, `:376-387` | Laufzeit: Leser „+0,1 bis 0,2 W“; die Recherche rechnet 0,2 bis 0,35 W (`docs/egm/ein-aus/research.md:88`) |
| `:738-742` | Entscheidungszeilen R1, R2, R5, R6 ohne Vermerk, dass R9 sie ersetzt |
| `docs/plan/bestellliste-charge1.md:46-47` | „Pololu-Ideal-Dioden, Pogo-Pins, Magnete“ für Charge 2 |
| `docs/egm/ein-aus/design_draft.md:515` | M7: „Ideal-Diode-Rückfall (Plan)“ verweist auf ein entferntes Teil |
| `docs/plan/uebergabe.md:26-29` | USB-Tastatur und Phoniebox (Stand 05.11., überholt seit 3.8) |

* **Vorschlag:** Mit der neuen Stückliste (H5) in einem Zug bereinigen; die Zeile `:746` kündigt das an. Bei `uebergabe.md` reicht ein Vermerk am Kopf.
* **Quelle:** nur Repo.

### H26 · niedrig · Ladestations-Entwurf Rev. 5 widerspricht sich und späteren Entscheidungen

* **Fundstelle und Problem:**
  * A1 und T1 verlangen bei 90° „liegt stabil auf dem Kragen“ (`docs/egm/ladestation/design_draft.md:52`, `:184`). Abschnitt 4.2 und das Resolve sagen „kippelt absichtlich“ (`:89`, `docs/egm/ladestation/resolve.md:151`). T1 kann so nicht bestanden werden.
  * Abschnitt 6 beschreibt noch den 120-s-Zähler, „Sync nur im Heimnetz“ und „kein Sync über den Hotspot“ (`:164-170`). Das widerspricht S7 (`docs/egm/ladestation/software_folgen.md`, Abschnitt 10) und dem Ein/Aus-Konzept.
  * Grundlage ist „Plan Rev. 3.16“ (`:9`).
  * Buchse: siehe H15.
  * `docs/egm/ladestation/einkaufsliste_muster.md` gilt für Rev. 3 (Magnet-Stecker, Reeds, #2810) und ist überholt. Brauchbar bleibt nur die Zeile zum Netzteil.
* **Vorschlag:** Vor der Annahme nach `docs/designs/` Rev. 6 schreiben: Abschnitt 6 durch einen Verweis auf das Ein/Aus-Design ersetzen, A1/T1 anpassen, Buchse festlegen, H3 und H14 einarbeiten.
* **Quelle:** nur Repo.

### H27 · niedrig · Reihenfolge der Messungen: Abhängigkeiten sind nicht aufgeschrieben

* **Fundstelle:** `docs/egm/ein-aus/design_draft.md:505-525`; `docs/egm/ladestation/design_draft.md:181-193`.
* **Problem:** Zwei Messlisten (M0 bis M15, T0 bis T10) laufen nebeneinander. Einige Ergebnisse entscheiden Bestellungen in der anderen Liste: T8 (Rückspeisung) entscheidet `STROM_IN` (H2), M0 entscheidet die Last für M2 (H17), Test 5b entscheidet M6 (H16), die gekaufte Buchse entscheidet den Zapfen (H15).
* **Vorschlag:** Eine gemeinsame Reihenfolge, siehe Liste „Vor der Bestellung messen“ unten.
* **Quelle:** nur Repo.

### H28 · niedrig · Kleinigkeiten

* `docs/egm/ein-aus/resolve.md:32` (P11) nennt sechs Pins für sieben Funktionen; der Entwurf weicht auf GPIO 4 aus (`design_draft.md:304`). Mit H6 ohnehin neu.
* Der Plan sagt in Rev. 3.19 „MOSFET für den Ring“ (`docs/plan/stueckliste-und-psp.md:28`), der Entwurf „Lastschalter-IC“ (`design_draft.md:286`). Gemeint ist dasselbe.
* `docs/plan/stueckliste-und-psp.md:583` nennt für „Leser unterbrochen“ Gelb, `:754` noch Rot; `:755` stellt es richtig.
* Die PiSugar-Einstellungen „Einschalten bei Strom“ und Anti-Mistouch fallen nach einem vollständigen Reset auf den Werkswert zurück, der Ladeschutz nach jedem Neustart **[Web]**. Der Dienst sollte alle Einstellungen, auf die er sich verlässt, bei jedem Start prüfen.
* **Quelle:** Repo; PiSugar-I²C-Datenblatt, Link bei H10.

---

## Antworten auf die sechs Prüffragen

| # | Frage | Kurzantwort | Befunde |
|---|---|---|---|
| 1 | Passt es elektrisch zusammen? | Im Grundsatz ja. Offen: Schutz am Akku-Abgriff, `STROM_IN`, Weiche, 5-V-Verteilung, Kopfhörer-Kontakt, Rückspeisung über D+ im Schlaf. Pegel 3,3 V gegen 5 V sind bedacht (74AHCT). | H1, H2, H7, H9, H11, H13 |
| 2 | Pinbelegung | Pi ohne Konflikt, aber veraltet. ESP32: Pins nur auf der Unterseite, Weck-Pegel für den Hall-Schalter. | H6, H8, H18 |
| 3 | Sockel | Führung und Drehlagen schlüssig. Kippen und Stecktiefe nicht. Netzteil reicht. Wärme am Sockel nicht gemessen. | H3, H14, H15, H12 |
| 4 | Stückliste vollständig? | Nein. Die ganze Wächter-Elektronik und die Sockel-Teile fehlen, eine Platine fehlt. | H5 |
| 5 | Widersprüche, Veraltetes | Ja, viele im Plan, einige im Ladestations-Entwurf. | H25, H26, H10 |
| 6 | Risiken vor dem Bestellen | Siehe die beiden Listen unten. | H1 bis H6, H27 |

---

## Fragen, die nur Tobias entscheiden kann

1. **Ring beim Hören (H4):** Sollen alle 40 LEDs dauernd leuchten, auch wenn das rechnerisch 2 bis 4 Stunden Laufzeit kostet? Oder weniger LEDs, dunkler, oder nach einigen Sekunden aus?
2. **ESP32-Board (H6):** SuperMini mit Drähten an der Unterseite, SuperMini nur mit Randpins (ohne Reserve), ein anderes Board, oder eine Träger-Platine?
3. **Eigene Platine (H5, H15):** Ist eine kleine, vom Hersteller bestückte Träger-Platine in Ordnung (Kosten, Wartezeit), oder soll alles auf Adapter-Platinen und Lochraster bleiben?
4. **Tonie-Halt (H16):** Bekommt der Deckel einen Magneten oder eine Stahlscheibe für die Tonies? Mit Magnet fällt der Hall-Schalter als Weckquelle weg.
5. **Einschalten (H10):** Gilt weiter „ein Druck“? Dann muss Anti-Mistouch aus sein und der Dienst das bei jedem Start sicherstellen. Oder ist „kurz, dann lang“ für die Kinder in Ordnung?
6. **Akku am Sockel (H12):** Ladeschutz bei etwa 80 % einschalten (längeres Akkuleben, weniger Laufzeit unterwegs) oder immer voll laden?
7. **Kippen im Sockel (H3):** Darf ein Kind die Box aus dem Sockel kippen (dann muss der Stecker mitkippen), oder soll der Sockel nur gerades Abheben zulassen?
8. **Tiefentladung (H1):** Darf der Wächter bei 3,2 bis 3,3 V bewusst abschalten? Dann weckt bis zum Laden kein Tobie mehr, nur noch Strom am Eingang.
9. **Auto (Abschnitt C):** Soll die Box losspielen, wenn im Auto die Zündung Strom gibt und ein Tobie liegt?
10. **Kopfhörer (H9, H22):** Reicht Mono am Kopfhörer? Und welcher Kopfhörer wird benutzt (für die Pegelmessung)?

---

## Vor der Bestellung messen

In dieser Reihenfolge. Jede Messung nennt, was sie entscheidet.

| # | Messung | Entscheidet | Befund |
|---|---|---|---|
| 1 | **M0:** Reichweite des Lesers mit 5 V und mit 3,3 V an der Sendestufe, durch den Deckel. Modul durchmessen: Hängt ein Regler am +3.3V-Pin? | Variante A oder B, Wandler ja oder nein | H17 |
| 2 | **PiSugar, Ladeeingang:** Spannung an Pad 8 im Akkubetrieb (Pi an, Pi aus), Abklingzeit nach dem Abziehen, Leerlaufspannung des Netzteils, schwache Quelle (0,5 A, 1 A) | `STROM_IN`-Schaltung, Tor für Schritt 2 | H2, H20 |
| 3 | **PiSugar, Pad 2:** Liegt es hinter der Schutzschaltung? Wird es bei leerem Akku getrennt? Last der gewählten Variante in Pulsen; Ladestandsanzeige unverändert? | Sicherung, Spannungswächter, Regler | H1, H17 |
| 4 | **PiSugar, Taste:** Pegel und Strom an Pad 10; kürzester wirksamer Puls; Wirkung von Lang mit und ohne Soft-Shutdown; Zeit „Strom → 5 V“; welche Einstellungen überleben einen Reset | PhotoMOS, Hauptknopf-Weg, Pulsregeln | H10, H19 |
| 5 | **SuperMini:** Welche Pads gibt es wirklich? Ruhestrom im Tiefschlaf, vor und nach dem Ablöten; D+ bei Pi aus, ESP32 wach **und** schlafend; Pull-up per Register abschaltbar? | Board-Wahl, USB-Schalter ja oder nein | H6, H13 |
| 6 | **Ring:** Strom beim Muster „läuft“ (alle 40 LEDs, 12 bis 25 %), dunkel, bei Vollweiß am Deckel | Laufzeit-Tabelle, Muster beim Hören | H4 |
| 7 | **5-V-Schiene:** Einschalten mit 1000 µF; Einbruch bei Pi-Start plus Ring plus lautem Bass, bei 20 % Akku | Verdrahtung, Elko-Größe | H11 |
| 8 | **Test 5b und Hall-Schalter:** Stahlscheibe; Hall-Schalter in der Antennenmitte: Lesequote, Tonie 10 von 10, Lautsprecher löst nicht aus | Tonie-Halt, Hall ja oder nein | H16 |
| 9 | **Kopfhörer:** gekaufte Buchse durchmessen (welcher Kontakt schließt wann); Pegel in dB mit dem echten Kopfhörer; Störgeräusche bei Leser, Ring, WLAN | Buchsentyp, Schaltung, Teilerwerte | H9, H21 |
| 10 | **Sockel T0:** Maße von Stecker und gekaufter Buchse; Abzugskraft und Kontakt bei voller Stecktiefe und 0,5 / 1,0 / 1,5 mm davor | Halter, Stecktiefe, Gewicht oder Befestigung | H14, H15 |
| 11 | **Sockel, Kragenprobe mit Boxboden:** Wippen der gesteckten Box; Kippen nach vorn und hinten mit 20 / 40 / 60 N; schräges Abheben, viele Male | Halter starr oder gelenkig, Auflage, Kragen-Druckrichtung | H3 |
| 12 | **Wärme:** Zelle beim Laden von leer, Box geschlossen im Sockel, Pi in Bereit | Ladeschutz, Lüftung | H12 |

Erst nach 1 bis 5: Schaltplan und Platine (H5). Erst nach 10 und 11: Sockel und Boxboden drucken.

---

## Quellen

* PiSugar 3 Series, Pads und Daten: https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series
* PiSugar 3, I²C-Datenblatt: https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-i2c
* ESP32-S3 SuperMini, Pinout: https://www.espboards.dev/esp32/esp32-s3-super-mini/
* ESP-IDF, Sleep Modes (ESP32-S3): https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/api-reference/system/sleep_modes.html
* TI DRV5032: https://www.ti.com/lit/gpn/DRV5032
* TI TPS63900: https://www.ti.com/product/TPS63900
* TI PCM5102A: https://www.ti.com/product/PCM5102A
* Analog Devices MAX98357A: https://www.analog.com/en/products/max98357a.html
* APA102-2020, Ruhestrom: https://memcpy.io/apa102-led-current-usage.html
* Raspberry Pi 15W USB-C Power Supply: https://www.raspberrypi.com/products/type-c-power-supply/

Nicht belegen konnte ich: ob das Raspberry-Pi-Netzteil die Spannung erst nach erkanntem Widerstand an CC einschaltet (bleibt Messung T0), und den Schaltplan des Lese-Moduls „PN5180-NFC R1.1-170710“ (bleibt Durchmessen, M0).
