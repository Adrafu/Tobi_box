# Ein- und Ausschalten: Review Hardware, Elektrik, Firmware-Machbarkeit (Goldfisch)

*   **Gelesen:** `design_draft.md` (ganz), `concepts_brief.md`, `research.md`, `docs/plan/stueckliste-und-psp.md`
    (Hardware-Punkte 4 bis 12, Pinbelegung Teil 2), `firmware/tobibox-reader/` (`config.example.h`, `platformio.ini`, Pins).
    Der Leser-Vertrag und die Software-Verträge sind Sache des zweiten Reviewers.
*   **Belegt im Web (heute gelesen):** PiSugar-Pad-Tabelle, SuperMini-Seite, Foren-Hinweise zu USB ohne VBUS. Wo ich aus Kenntnis schreibe
    und nicht nachgelesen habe, steht **[aus Kenntnis]**. Wo es Messung am Muster braucht, steht **[Messung]**.
*   **Zählung:** 3 hoch, 8 mittel, 4 niedrig (15 Befunde).
*   **Gesamturteil:** Das Konzept ist elektrisch machbar. Die großen Lücken sind nicht die genannten (Pad 2, Anti-Mistouch), sondern
    (1) woher der PN5180 im Tiefschlaf seine TX-Spannung bekommt, (2) der USB-Anschluss des SuperMini gegen den **ausgeschalteten** Pi,
    (3) Fehlimpulse auf Pad 10, die auf einem laufenden Pi als Tastendruck ankommen.

---

## H-G1 · hoch · TX-Versorgung (TVDD / 5-V-Pin) des PN5180 im Zustand Aus ist nicht geklärt

*   **Fundstelle:** `design_draft.md` 5.1 (H1), 4.3, 6.1; `research.md:124-128`; Messung 2 („TVDD 3,3 V gegen 5 V“).
*   **Problem:** H1 speist „ESP32 und PN5180-**Logik**“ aus dem 3,3-V-Regler. Die TX-Stufe (TVDD, laut NXP 2,7 bis 5,5 V, typ. 5 V) ist
    nicht erwähnt. Auf den üblichen PN5180-Platinen hängt der 5-V-Pin heute am USB-5-V des Pi (über den SuperMini). Ohne Pi gibt es dort **keine** 5 V,
    LPCD kann dann nicht senden. Je nach Platine gibt es zusätzlich einen Platinen-Regler 5 V auf 3,3 V; zwei Regler parallel an der 3,3-V-Schiene
    sind ein zweites Rückspeisungs-Thema. Dazu: LPCD vergleicht gegen eine **vor dem Schlafen gemessene Referenz** (`research.md:207`).
    Ändert sich TVDD zwischen „Referenz gemessen“ und „Wache“ (Akku 4,2 auf 3,4 V, oder 5 V gegen 3,3 V je nach Pi-Zustand), verschiebt sich die Schwelle:
    Fehlweckungen oder blinde Box. Die Reichweite bei 3,3 V statt 5 V sinkt zudem deutlich [Messung].
*   **Vorschlag:** (a) Genaue PN5180-Platine festlegen und den Schaltplan lesen (wo hängen 5-V-Pin, 3,3-V-Pin, Platinen-Regler?). (b) TVDD aus **einer** festen,
    geregelten Quelle speisen, im Schlaf und im Betrieb dieselbe, damit die LPCD-Referenz nicht springt; nicht aus 5-V-Rail im Betrieb und 3,3 V im Schlaf umschalten.
    Kandidaten: Buck-Boost auf 3,3 V (z. B. TPS63900-Klasse, Ruhestrom < 1 µA) oder, wenn die Reichweite 5 V braucht, ein kleiner Aufwärtswandler mit Enable, der nur
    für den LPCD-Puls läuft (teuer, nur wenn Messung 2 es verlangt). (c) Messung 2 um „Reichweite durch Deckel bei TVDD = 3,3 V fest“ als **Hauptfall** erweitern, nicht als Nebenfall.
    (d) Vor jedem Schlafengehen neu abgleichen (steht im Entwurf nur bei Fehlweckungen).
*   **Quelle:** NXP PN5180-Datenblatt (TVDD 2,7/5,0/5,5 V), `research.md:124-128`; NXP-Community „PN5180 TVDD 3.3V vs 5V“ (ohne klare Antwort):
    https://community.nxp.com/t5/NFC/PN5180-TVDD-3-3V-vs-5V/m-p/1479316 ; Herstellerangaben zu Modulen widersprechen sich (Elechouse-Handbuch: 5 V für TVDD nötig).

## H-G2 · hoch · USB ohne VBUS: Enumeration geht, aber der D+-Pull-up speist den ausgeschalteten Pi

*   **Fundstelle:** 5.2 (H2), 4.1 (`WECKEN`, `PRUEFEN`), Messung 8.
*   **Antwort auf die Frage:** Ja, ein Datenkabel ohne VBUS ist machbar. Der ESP32-S3 hat keinen VBUS-Pin; für die Aufzählung zählt der 1,5-kΩ-Pull-up an D+ nach 3,3 V,
    und der ist intern. Espressif-Moderator im Forum: „du musst VBUS gar nicht anschließen“. Der Pi sieht das Gerät, weil er als Host selbst VBUS liefert und nur die Pull-ups prüft.
    Das HWCDC aus `platformio.ini` (`ARDUINO_USB_CDC_ON_BOOT=1`) läuft dann ohne VBUS-Erkennung. **[Messung 8 bleibt nötig]**, die Forenlage ist kein Beleg.
*   **Problem:** Der Pull-up ist **an, sobald der ESP32 läuft** (nach jedem Reset ist der USB-Serial/JTAG-Block an GPIO 19/20 aktiv, auch lange vor `Serial.begin`)
    **[aus Kenntnis]**. In `PRUEFEN` und `WECKEN` ist der Pi aber noch **aus** (kein 5 V, Kernel nicht da). Dann drückt der ESP32 ca. 3 V über 1,5 kΩ in die D+-Leitung
    eines unversorgten BCM2837 (ESD-Strukturen, Pad-Diode in die abgeschaltete 3,3-V-Schiene). Das ist das, was die USB-Spezifikation „Back-Drive“ verbietet
    (Abschnitt 7.2.1, **[aus Kenntnis, nicht neu gelesen]**: ein selbstversorgtes Gerät darf bei fehlendem VBUS nicht in den Host speisen). Folgen: einige mA in den Pi,
    Pi-Rails halb vorgeladen, im ungünstigen Fall ein unsauberer Power-on-Reset des Pi gerade beim Einschalten (Pad-10-Puls). Der Entwurf behandelt nur VBUS, nicht die Datenleitungen.
*   **Vorschlag:** Messen: Strom und Spannung an Pi-D+ und Pi-3,3-V bei ausgeschaltetem Pi und wachem ESP32 (Teil von Messung 8). Wenn nennenswert: analoger USB-Schalter
    (FSUSB42/TS3USB221-Klasse) in D+/D−, Enable aus `VBUS_SENSE`; oder Pull-up per `USB_SERIAL_JTAG`-Register abschalten, bis `VBUS_SENSE` hoch ist (nur mit ESP-IDF-Zugriff, nicht in reinem Arduino).
    Kurzfristig: die Zeit mit wachem ESP32 und totem Pi so kurz wie möglich halten (der Entwurf hält sie ≈ 1 s, in `host_timeout` bis 30 s).
*   **Quelle:** esp32.com „ESP32 S3 WROOM USB VBUS connection“ (https://esp32.com/viewtopic.php?p=152207); Espressif „Self-Powered USB Device Solutions“
    (https://docs.espressif.com/projects/esp-iot-solution/en/latest/usb/usb_overview/usb_device_self_power.html: Selbstversorgte Geräte müssen VBUS per Teiler erkennen).

## H-G3 · hoch · Ein Fehlimpuls auf Pad 10 kommt auf einem laufenden Pi als **Tastendruck** an

*   **Fundstelle:** 4.2 (Pulsdauer 150 ms, „Puls nach der Lesung“), 4.1 `PRUEFEN`, L3 `pad_pulse`.
*   **Problem:** Laut Plan Punkt 4 ist „Einfach“ am PiSugar = Play/Pause, „Doppel“ evtl. belegt, „Lang“ = Herunterfahren. Der Entwurf sagt nur, dass der Puls „nach der Lesung“ kommt.
    Er sagt nicht, was passiert, wenn
    (a) Knopf oder Strom und Tobie fast gleichzeitig kommen: Der Pi startet schon, der Puls aus `PRUEFEN` kommt danach als „Einfach“ und pausiert das Hörspiel, das gerade anläuft;
    (b) `pad_pulse` (keine 5 V binnen 2 s) zu einem **zweiten** Puls führt, obwohl der erste nur langsam wirkte (PiSugar-Entprellung, Hibernate-Aufwachen, 3 s Schlussverzögerung des vorherigen Poweroffs);
    (c) zwei Pulse < 0,5 s Abstand als Doppelklick gelten;
    (d) der ESP32 nach einem Brownout-/Watchdog-Reset im Betrieb (Pi läuft!) in `PRUEFEN` landet.
*   **Vorschlag:** Regeln in die Zustandsmaschine (und in `power_fsm` als Test): Puls **nur**, wenn `VBUS_SENSE` unmittelbar davor und nach der Lesung (10 ms Abstand) tief ist;
    **höchstens ein Puls je Wecken**, Wiederholung frühestens nach 10 s und wieder mit VBUS-Prüfung; nach einem Reset mit Pi-an (VBUS hoch) nie pulsen (`reason=reset` ohne Puls: im Entwurf angedeutet, nicht festgelegt).
    Pulsbreite aus Messung 5 bestimmen und **beide** Grenzen messen (kürzester wirksamer Puls, längster Puls unter „Lang“).
*   **Quelle:** Plan `stueckliste-und-psp.md:45-48`; PiSugar-Pad-Tabelle https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series (Pad 10 löst beim Verbinden mit BAT die Powertaste-Funktion aus, sonst keine Zeitangabe).

## H-G4 · mittel · Rückfall „kurz, dann lang“ ist sicherer als im Entwurf behauptet

*   **Fundstelle:** 4.2: „Kein Rückfall mit ‚kurz, dann lang‘: ein langer Druck auf eine laufende Box würde sie wieder ausschalten.“
*   **Problem:** Der ESP32 pulst nur, wenn der Pi aus ist (VBUS tief). Dann schadet ein langer Druck nichts. Der Entwurf verlässt sich dagegen ganz darauf, dass Anti-Mistouch **aus** bleibt,
    obwohl dokumentiert ist, dass die Einstellung ab Werk **an** ist und nicht belegt ist, ob sie einen Stromverlust (Akku ganz leer, Tiefentladung, Reset) übersteht (`research.md:191`).
    Verliert der PiSugar die Einstellung, weckt kein Tobie mehr, und der ESP32 sieht nur `pad_pulse` ohne Abhilfe. Das Kind merkt: Box tot, nur der Hauptknopf (kurz, dann lang) geht.
*   **Vorschlag:** Zweiter Versuch nach `pad_pulse`: erneute VBUS-Prüfung (noch tief), dann „kurz, Pause 300 ms, lang 1,5 s“ (Zeiten aus Messung 5), danach VBUS-Prüfung; wirkt es, Meldung `anti_mistouch_an` an den Pi
    (der setzt `set_anti_mistouch false` neu). Messung 5 ergänzen: „bleibt Anti-Mistouch aus nach Akku ganz leer und wieder geladen?“. Vorbehalt: Race, wenn der Pi doch gerade startet; deshalb nur bei VBUS tief über ≥ 2 s.

## H-G5 · mittel · SuperMini-Platine: Dauerverbraucher und Rückspeisung über den 3V3-Pin

*   **Fundstelle:** 5.1 („Die LED wird entfernt oder getrennt; der Platinen-Regler darf nicht zusätzlich am 3,3-V-Netz hängen“), `research.md:79`.
*   **Problem:** Die SuperMini hat nach der Produktseite eine rote Power-LED **und** eine WS2812 beide an GPIO 48, dazu Lade-IC mit blauer LED und einen Platinen-Regler (Typ nicht angegeben).
    Die Angabe „43 µA Tiefschlaf“ ist eine Verkäuferangabe ohne Messbedingung (`espboards.dev`). Speist man den 3V3-Pin **von außen**, sitzt die 3,3 V am Regler-Ausgang. Je nach Regler leitet dessen Body-Diode rückwärts auf
    die VBUS-/5V-Schiene der Platine (ca. 2,7 V), dort hängen der Lade-IC und die blaue LED. Das kann glimmen und Strom ziehen. Eine WS2812 zieht auch dunkel typ. 0,3 bis 1 mA **[aus Kenntnis]**,
    die rote LED etwa 0,2 bis 1 mA. Das ist mehr als das ganze Wächter-Budget von `research.md:90` (0,2 bis 0,8 mA).
*   **Vorschlag:** Vor dem Bestellen eines Reglers eine SuperMini im Aufbau messen: (1) 3V3-Pin extern, nichts an USB, µA-Messung im Tiefschlaf; (2) LED/WS2812 abgelötet; (3) Regler abgelötet. Muss der Regler weg, geht das nur am Lötkolben:
    Beschaffung eines Boards ohne Lade-IC/LED (z. B. ESP32-S3-Zero/QT-Py-Klasse) ist die Alternative. Der Akkuanschluss des SuperMini selbst bleibt ungenutzt. In die Messliste (Messung 8) aufnehmen.
*   **Quelle:** https://www.espboards.dev/esp32/esp32-s3-super-mini/ (LED an GPIO 48, 43 µA, Batterie-Pads/Lade-LED, Regler nicht genannt).

## H-G6 · mittel · Reglerwahl, Dropout und Spitzenstrom aus BAT sind noch offen formuliert

*   **Fundstelle:** 5.1: „Ruhestrom ≤ 5 µA“, „≥ 150 mA“, „Unterspannungs-Abschaltung bei etwa 3,1 V“.
*   **Problem:** (a) Ein 3,3-V-LDO fällt bei BAT 3,0 bis 3,5 V aus der Regelung; der Ausgang folgt dann BAT minus Dropout (3,0 bis 3,2 V). Der ESP32-S3 darf bis 3,0 V (Datenblatt, **[aus Kenntnis]**),
    der PN5180 TX und der eingebaute Flash des ESP32-S3FH4R2 sind dann im Grenzbereich. Der Pi fährt bei 5 % herunter (ca. 3,5 V), danach fällt Aus-Betrieb ohne Beobachter weiter;
    eine „Unterspannungsabschaltung 3,1 V“ im Regler steht im Widerspruch zu „Wächter dauernd“: Der ESP32 verschwindet lautlos, danach weckt kein Tobie mehr. Das ist erwünscht (Tiefentladeschutz), muss aber gewollt sein.
    (b) Spitzen: PN5180-TX bis 250 mA (Datenblatt) plus ESP32 beim Start 100+ mA; Eingang BAT ist über die Zelle und die PiSugar-Schutzschaltung angebunden, deren Innenwiderstand nicht bekannt ist [Messung 7].
    (c) 150 mA reicht für 10-ms-Pulse nur mit ≥ 100 µF Pufferkondensator am PN5180.
*   **Vorschlag:** Entweder Buck-Boost (z. B. TPS63900, Ruhestrom etwa 75 nA laut TI **[aus Kenntnis, Datenblatt prüfen]**, Eingang ab 1,8 V) für saubere 3,3 V über den ganzen Bereich, oder LDO mit sehr kleinem Ruhestrom (TPS7A02-Klasse) und bewusstem Dropout.
    Entscheidung und Abschaltschwelle schriftlich, mit Begründung „wann endet der Wächter“. Pufferkondensator (≥ 100 µF, niedriger ESR) am PN5180 und am Reglerausgang in die Stückliste.
    Zusätzlich: Ruhestrom des **Reglers mit Last von 20 µA** messen, nicht im Leerlauf (Ruhestrom-Angaben gelten oft nur ohne Last).

## H-G7 · mittel · Schalter für Pad 10: Bauteilwahl nach dem Pegel, nicht umgekehrt

*   **Fundstelle:** 5.3 (H3).
*   **Problem:** Der Entwurf nennt „PhotoMOS oder Optokoppler oder P-FET/PNP mit Treiber“. Der Pegel an Pad 10 ist unbekannt (Pull-Widerstand, Strom), der Original-Taster schaltet nur Pad 10 gegen BAT.
    Ein P-FET direkt am ESP32-GPIO sperrt bei BAT = 4,2 V und GPIO = 3,3 V **nicht** sicher (Vgs = −0,9 V; viele Typen leiten teilweise). Ein Optokoppler hat ein CTR-Problem (Transistorausgang hat Restspannung, die Pad 10 als „nicht BAT“ sehen kann).
*   **Vorschlag:** Ein **PhotoMOS-Relais** (z. B. TLP175A/AQY-Klasse, Sperrstrom < 1 µA, LED-Strom 2 bis 5 mA nur für 150 ms) hat keine Pegelfrage: Kontakt zwischen BAT und Pad 10 wie der Taster, ein Widerstand vom GPIO zur LED, 100 kΩ nach Masse an der LED-Seite (Reset/Tiefschlaf).
    Die LED-Seite muss im Tiefschlaf auf **Low** gehalten werden (`rtc_gpio_hold_en`), nicht floaten. Ein einziges Bauteil, zwei Widerstände.
    Vorher Messung 5 (Pegel, Pull-Widerstand, Zeit) ausführen, wie im Entwurf. Parallel zum Arcade-Hauptknopf ist unproblematisch (zwei Kontakte).

## H-G8 · mittel · Ring-Schalter: Lastschalter-IC statt diskretem High-Side-Aufbau, Einschaltverhalten, harter Poweroff

*   **Fundstelle:** 5.4 (H4), 3.4 („Ring aus“, „Tiefschlaf“).
*   **Problem:** (a) Diskret: P-FET + Treibertransistor + Pull-up heißt vier Teile und ein ungeklärtes Einschaltverhalten (Einschaltstromstoß in Ringkondensatoren). (b) Beim Einschalten der Ring-Schiene startet der 74AHCT125 erst bei VCC ≈ 2 V definiert;
    bis dahin sind DI/CI unbestimmt, die APA102 können beim Anlauf kurz flackern. (c) **Harter Poweroff** (Hauptknopf lang, Akku leer, Pi hängt): Die 5-V-Schiene bricht weg, während der ESP32 noch Daten schickt; ein Pegel „High“ am Eingang eines unversorgten
    Puffers speist die Schiene zurück, **wenn** dessen Eingang eine Klemmdiode nach VCC hat. Beim 74AHCT125 ist laut Datenblättern der Eingang bis 7 V ausgelegt, meist ohne Diode nach VCC **[aus Kenntnis, Datenblatt prüfen]**; der Entwurf nennt „Eingangsdioden“,
    das stimmt dann nicht, ist aber ein Messpunkt wert (Messung 9). (d) Die Annahme „MOSFET dauernd ≥ 1 A, Spitze 2,4 A bei Vollweiß“ ist wegen des 25-%-Deckels nur ein Fehlerfall; PTC 1,1 A hinter dem Schalter bleibt.
*   **Vorschlag:** Lastschalter-IC mit Slew-Rate-Begrenzung und Ausgangsentladung, **3,3-V-tauglichem Enable** und Sperrstrom < 1 µA (TPS22918-Klasse, 5,5 V max, **[aus Kenntnis, Datenblatt prüfen]**). Ein Teil statt vier, kein Treibertransistor, definierter Anlauf.
    DI und CI mit 10 kΩ nach Masse auf der Ring-Seite; 330 Ω in Reihe zwischen ESP32 und Puffer-Eingang (begrenzt die Rückspeisung, falls doch eine Diode da ist). Bei Verlust der 5 V (`VBUS_SENSE` fällt) beide Leitungen **sofort** auf Low (Interrupt, nicht erst im Takt).
    Reihenfolge beim Einschalten: erst Schalter, nach 5 ms Daten (nicht umgekehrt).

## H-G9 · mittel · Tiefschlaf-Firmware: EXT1-Pegel, IRQ-Löschen, Hold, USB nach dem Wecken

*   **Fundstelle:** 4.1, 4.5 (`hw_power.cpp`), 5.2 („RTC-fähige GPIOs 0 bis 21“).
*   **Antwort:** RTC-fähig sind beim ESP32-S3 GPIO 0 bis 21 **[aus Kenntnis, Espressif-Seite „Sleep Modes“]**. Wecken aus Deep-Sleep per EXT1 geht auf diesen Pins; Pegelwecken (`ANY_HIGH`), keine Flanke. Das hat Folgen, die der Entwurf nicht beschreibt:
    (a) Der PN5180-IRQ bleibt **high**, bis der Chip ihn zurückgesetzt bekommt. Wer schlafen geht, ohne IRQ-Status zu löschen und neu zu scharfen, wacht sofort wieder auf (Dauerschleife, leerer Akku). ESPuino hatte genau diesen Fall (`research.md:207`).
    (b) `VBUS_SENSE` und IRQ in derselben EXT1-Maske: Ist `VBUS_SENSE` beim Einschlafen noch hoch (Pi fährt herunter, Kondensatoren), weckt der ESP32 sofort. Die Regel „schlafen nur nach VBUS 3 s tief“ im Entwurf deckt das ab; sie muss als Test in `power_fsm` stehen (VBUS prellt: Neustart des 3-s-Zählers).
    (c) `gpio_hold` für Ring-MOSFET, Ring-Daten/Takt und Pad-Schalter: Die Pins sind RTC-GPIOs, `rtc_gpio_hold_en` plus `gpio_deep_sleep_hold_en` ist nötig, sonst floaten sie im Tiefschlaf. Nach dem Wecken Hold lösen **vor** dem ersten Schreiben.
    (d) Zeit bis zum ersten Lauflicht: ROM + Bootloader + Arduino-Start des ESP32-S3 ≈ 250 bis 400 ms **[Schätzung]**. Das Ziel „≤ 0,5 s nach Knopf oder Strom“ (CUJ 21) ist knapp, weil `VBUS_SENSE` erst hochgeht, wenn der PiSugar schon eingeschaltet hat. Messung 10 sollte das trennen.
*   **Vorschlag:** Die vier Punkte als eigene Zeilen in `power_fsm` bzw. Messfirmware `lpcd_probe` (EA10) aufnehmen; Ziel 0,5 s auf 0,8 s lockern oder messen.
*   **Quelle:** ESPuino-Hinweise in `research.md:207`; Espressif Sleep-Modes-Dokumentation **[aus Kenntnis, nicht neu abgerufen]**.

## H-G10 · mittel · LPCD: Belege dünn, Ruhestrom bei 300 ms offen, Referenz driftet

*   **Fundstelle:** 4.3, 7 (Ruhestrom), 5.1, 6.2; `research.md:84, 206`.
*   **Befund:** Die einzige Strombelegung ist „+ca. 300 µA“ vom ESPuino-Entwickler, ohne Messbedingung, bei ca. 1-s-Zähler. Bei 300 ms (Entwurf) sind es mindestens das 3-fache der Feldpulse; ein fester Teil (PN5180 Standby 15 µA) bleibt.
    Realistisch 0,4 bis 1,5 mA [Schätzung]. Das ändert die Tagesrechnung kaum (siehe H-G13), aber die Zeile „Wächter 0,2 bis 0,8 mA“ in Abschnitt 7 ist zu optimistisch und gehört auf 0,3 bis 1,5 mA.
    Die ESPuino-Entwickler selbst nennen LPCD aufwendig und wenig nützlich, andere wollen es entfernen (`research.md:206`). Für Tonie-Chips (ISO 15693, SLIX2) ist die Erkennung nur seit Version 20240111 überhaupt vorgesehen. Die Referenz hängt außerdem an Temperatur, TVDD (H-G1),
    Gehäuse-Metall und, in Bereit mit `wach=1`, am Ring: Zündet der Ring (3 s Aufleuchten), ändert sich das Feld/Umfeld; der LPCD-Wachbetrieb bekommt dadurch Fehlmeldungen, die zwar nur volle Abfragezyklen auslösen (harmlos), aber den Spareffekt aufzehren.
    PN5180-Firmware ≥ 4.0 ist Voraussetzung; viele Platinen kommen mit 3.5 (`research.md:207`), das Update braucht ein eigenes Werkzeug und ist ein Arbeitspaket.
*   **Vorschlag:** (a) Messung 2 als **Gate** vor jeder Hardwarebestellung (der Entwurf tut das: T1, gut). (b) Messung 2 um Temperaturlauf über Stunden ergänzen (Fehlweckungen je Tag, gezählt im ESP32 und in `lpcd_noise` abgelegt). (c) Für Stufe 1 den Wachbetrieb in Bereit (`wach=1`, spart nur etwa 0,045 W)
    **nicht** bauen: erst nach Messung 4. Dafür ist die Dauerabfrage, wie sie heute läuft, die risikoärmere Wahl; sie hat aber in der Praxis mehr als 5 % Feld-an-Zeit (Abfrage für ISO 14443 und 15693 je Zyklus), die 0,045 W sind eine untere Schranke [Messung 4].

## H-G11 · niedrig · Pinplan: Zählung stimmt nicht ganz, IRQ-Draht fehlt, Pins prüfen

*   **Fundstelle:** 5.5.
*   **Befund:** (1) „GPIO 1 bis 7 sind frei (sieben Stück)“, davon ist GPIO 3 ein Strapping-Pin (JTAG-Quelle). Der Entwurf meidet GPIO 3 richtig, dann bleiben sechs, und die sind mit IRQ (4), VBUS (5), Pad (6), MOSFET (7), Ring (1, 2) **alle** belegt. `STROM_IN` und ADC „frei“ gibt es dann nicht.
    (2) Ausweichen auf GPIO 14 bis 18 und 21 (RTC-fähig bis 21; **19/20 sind USB D−/D+ und tabu**; 43/44 sind UART0/Konsole; 48 ist die Onboard-LED/WS2812). Die Produktseite führt 1 bis 18, 21, 33 bis 48 heraus; **welche Pads der eigenen SuperMini wirklich herausgeführt sind,
    ist am Exemplar zu zählen** (die Seite ist nicht der Schaltplan). Die Strapping-Angabe dort (9 bis 14, 39 bis 42) weicht von Espressif ab (nur 0, 3, 45, 46) und sollte nicht übernommen werden.
    (3) `config.example.h` hat heute keinen IRQ-Pin; der PN5180-IRQ ist ein **neuer Draht** an der Platine (nicht „schon da“). (4) Die bestehenden Pins 8 bis 13 sind in Ordnung: GPIO 10 bis 13 sind die nativen FSPI-Pins, der zweite SPI-Host für den Ring (SPI3) läuft über die GPIO-Matrix auf 1/2 ohne Störung.
*   **Vorschlag:** Tabelle in 5.5 auf die tatsächlich benötigten Pins mit Spalte „RTC ja/nein, Strapping, ADC“ erweitern und `STROM_IN`/ADC auf GPIO 14 bis 18/21 legen. Die Vorgabe „GPIO 3 offen lassen“ in den Entwurf.

## H-G12 · niedrig · Teiler für `VBUS_SENSE` ist zu knapp bemessen

*   **Fundstelle:** 5.2: Teiler z. B. 100 kΩ/200 kΩ.
*   **Befund:** 5,0 V × 200/300 = 3,33 V; bei 5,25 V sind es 3,5 V, über 3,3 V + 0,3 V Grenze des ESP32-S3-Pins ist es dann knapp. Dazu ist die Eingangsschwelle ca. 0,75 × VDD ≈ 2,5 V; fällt VDD auf 3,0 V (H-G6), sind es 2,25 V.
*   **Vorschlag:** 100 kΩ/150 kΩ (3,0 V bei 5 V, 3,15 V bei 5,25 V), 10 nF nach Masse gegen Spitzen, und die Firmware legt das Gewicht auf die Entprellung (3 s bei Wegfall, 50 ms bei Anstieg).

## H-G13 · mittel · Budget plausibel, aber Messliste hat Lücken

*   **Fundstelle:** 7, 10.3.
*   **Nachgerechnet:** Die Summen in Abschnitt 7 stimmen (6,4 + 1,7 + 0,03 + 0,01 = 8,1 Wh; 7,6 + 2,2 + 0,03 + 0,11 = 9,9 Wh). Aus ist mit höchstens 0,11 Wh unkritisch, **auch** bei 3 mA statt 1,8 mA. Das Tagesbudget hängt an Hören und Bereit, nicht am Wächter.
    Der Entwurf hat zudem übersehen, dass die Versorgung des ESP32 aus BAT **einen Teil von der 5-V-Seite wegnimmt**: ESP32/PN5180 (0,2 bis 0,35 W aus `research.md:88`) rechnet auf 5 V über LDO. Aus BAT mit LDO sind es 3,7 V × I (kleiner), mit Buck-Boost noch weniger.
    Die Spalte „Bereit 1,0 bis 1,3 W“ gilt am 5-V-Ausgang und ist durch die verlagerte Last eher zu hoch; die gewonnene Menge bleibt eine Messung (Messung 4), keine Annahme.
*   **Fehlende Messungen (zusätzlich zu 1 bis 15):**
    1. **Strom im Aus mit Strom-Messgerät für nA/µA** (PPK2/µCurrent-Klasse), nicht mit Multimeter: Tiefschlaf mit LPCD hat Spitzen von mehreren mA alle 300 ms; Mittelwert über Minuten.
    2. **Rückwirkung auf PiSugar:** ändert die Dauerlast an BAT die Ladestandsanzeige/den Tiefstand-Schutz (`power.py`), und bleibt „Einschalten bei Strom“ unverändert?
    3. **Spannungseinbruch der 5-V-Schiene beim Pi-Start mit laufendem Lauflicht** (0,6 A Ring + Pi-Start 0,7 A + Verstärker-Puffer), bei kaltem und schwachem Akku; sinkt die Schiene unter die Brownout-Schwelle des Pi (4,63 V)?
    4. **USB-Rückspeisung in den Pi** (H-G2) und Strom über die D+-Leitung bei Pi aus.
    5. **Verhalten bei Akku fast leer:** Regler-Ausgang, ESP32-Brownout (kein Bootloop), `lpcd=0`-Speicher überlebt nur den Tiefschlaf, nicht den Stromverlust. Nach Tiefentladung und Aufladen ist `lpcd=1` wieder Standard.
    6. **Kalter Akku (Keller/Auto, 0 bis 5 °C):** Pad-Puls, Pi-Start, LPCD-Referenz.
    7. **Fehlmeldungsrate LPCD über 24 h** im Gehäuse neben Lautsprecher und Netzteil (H-G10).
    8. **Zeit Puls → 5 V** und **Zeit 5 V → Lauflicht** getrennt, nicht nur Gesamtzeit (H-G9d).
    9. **Doppelter Auslöser:** Hauptknopf und Tobie gleichzeitig (H-G3a).
    10. **PN5180-Platinen-Schaltplan** und Strom bei Platine unversorgt auf 5 V-Pin (H-G1).

## H-G14 · niedrig · Zeitaussagen zum Lauflicht: Hardware-Anteil sauber ausweisen

*   **Fundstelle:** 6.2, 3.4, 1.3.
*   **Befund:** Bei Tobie-Wecken: Das Lauflicht beginnt, sobald die 5 V am Ring-Schalter stehen, also nach ≈ 0,95 s [Schätzung]; die Annahme „PiSugar schaltet 0,2 s nach dem Puls“ ist unbelegt (Entprellung, Hibernate-Aufwachen).
    Bei Knopf/Strom: Der ESP32 erfährt nichts von selbst, bis `VBUS_SENSE` hoch ist **und** er gebootet hat (H-G9d). Die Lauflicht-Zeit „≤ 0,5 s“ gilt deshalb nur, wenn der ESP32 schon vorher wach wäre. Ein Auslösen des Lauflichts über den Pad-Schalter allein ist nicht möglich.
*   **Vorschlag:** Ziele als „≤ 1,5 s (Tobie)“ und „≤ 1,0 s (Knopf/Strom)“ lassen, bis Messung 10 vorliegt; im Entwurf kennzeichnen, dass beide **Messziele** sind.

## H-G15 · niedrig · Einfachere Wege zum gleichen Ziel (zur Abwägung)

*   **A. Hall-Sensor statt LPCD für Tonies.** Der Plan sagt selbst, dass ein Tonie einen Magneten im Sockel hat (`stueckliste-und-psp.md`, Punkt 10, 4.2.9). Ein Hall-Schalter mit µA-Verbrauch (DRV5032-Klasse, < 1 µA **[aus Kenntnis]**) oder ein Reed-Kontakt unter dem Deckel
    weckt den ESP32 ohne PN5180, ohne LPCD-Referenz, ohne TVDD-Frage (H-G1), ohne Firmware-4.0-Update. Nachteile: Karten ohne Magnet wecken nicht; Lautsprechermagnet ist ein konstantes Gleichfeld und muss weg vom Sensor sein. Risikoarm als Rückfall für E12.
*   **B. Ring-Weiche in Hardware statt Muster-Engine.** Wenn die Pi-Software `led.py` (Bit-Bang auf 23/24) unverändert bleibt, genügt: zwei Puffer-Gatter 74AHCT125 je Leitung (ESP32 und Pi), Ausgänge verbunden, Enable über einen Pi-GPIO (frei: 7, 12, 13, 16), Pull-down hält ESP32 als Standard. Der ESP32 braucht nur ein Lauflicht und „aus“;
    das Schalten der Ring-Schiene ist ODER aus ESP32-Enable und Pi-Enable. Spart den Vertrag `RING`/`SLEEP`-Teil der 26 Vertragsstellen, die doppelte Engine in C++ und den Gleichheitstest (3.3). Preis: Pi und ESP32 müssen sich über einen Pin einigen. Das widerspricht E7 (Ring über den ESP32) nicht ganz,
    ist aber eine Entscheidung für Tobias.
*   **C. `wach=1` (LPCD in Bereit) auslassen** (H-G10): Spart ein Firmware-Paket und eine Vertragsstelle für 0,05 bis 0,2 W.
*   **D. Lastschalter-IC und PhotoMOS** (H-G7, H-G8) statt diskreter Schaltungen: weniger Teile, weniger Fehler.
*   **E. Nichts am USB-Kabel ändern:** Normales Kabel mit VBUS lassen, ESP32 trotzdem aus BAT versorgen; zwei Quellen auf der SuperMini sind nicht schädlich (höhere Spannung gewinnt), und `VBUS_SENSE` greift vom 5V-Pad der SuperMini ab. Aber **Achtung** (H-G5): Bei Pi aus kann die Rückspeisung über den Platinenregler am 5V-Pad
    ca. 1,8 V am Teiler erzeugen, also einen unklaren Pegel. Der Entwurf mit eigener Leitung vom Pi-5-V (Pad 11) ist hier sauberer. Beide Wege bleiben Messfälle (Messung 8).

---

## Fragen, die nur Tobias entscheiden kann

1. **PN5180-Platine festlegen:** Welche Platine ist bestellt/gebaut (Schaltplan lesen)? Soll TVDD dauerhaft 3,3 V sein (kürzere Reichweite), oder ist ein zusätzlicher Wandler für 5 V erlaubt? (H-G1)
2. **Rückfall Hall/Reed statt LPCD** für Tonies, wenn Messung 2 schlecht ausfällt, ausreichend? Karten würden dann nur über den Hauptknopf wecken. (H-G15 A, E12)
3. **Ring-Weiche in Hardware (H-G15 B)** statt kompletter Ring-Engine im ESP32: Soll die einfachere Variante geprüft werden, bevor Vertragsänderungen V1 bis V10 geschrieben werden?
4. **Wie ernst ist ein Fehlstart per Pad-Impuls?** Ist „Hauptknopf und Tobie gleichzeitig pausiert das Hörspiel einmal“ hinnehmbar, oder soll der ESP32 strenger prüfen (H-G3)?
5. **Lötarbeit an der SuperMini erlaubt** (LED/WS2812/Regler entfernen), oder soll ein anderes Board bestellt werden? (H-G5)
6. **Abschaltschwelle des Wächters:** Soll der Wächter bei leerem Akku bewusst verschwinden (Regler-Unterspannung), oder soll er so lange wie möglich leben, auf Kosten der Tiefentladung? (H-G6)
7. **Zeitziele Lauflicht:** Bleibt das Ziel „≤ 1,5 s/≤ 0,5 s“ hart oder gilt „so schnell, wie die Messung erlaubt“? (H-G14)
