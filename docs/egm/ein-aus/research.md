# Ein- und Ausschalten: Recherche (Fakten für das Brainstorming)

* **Datum:** 10.11.2026
* **Zweck:** Belastbare Zahlen für `docs/egm/ein-aus/` (Schritt 1, Brainstorm). Keine Bewertung, keine Auswahl.
* **Stand:** Nur gelesen und recherchiert. Kein Code, nichts geändert, nichts committet.
* **Kennzeichnung jeder Zahl:** **[gemessen]** (Messung, auch von Dritten, Quelle genannt), **[Herstellerangabe]** (Datenblatt, Hersteller-Doku, Verkäuferseite), **[Schätzung]** (Rechnung oder Annahme, auch aus dem Repo). Was nur als Suchtreffer-Zusammenfassung vorlag und nicht selbst gelesen wurde, steht als **(Suchtreffer)**.
* **Rechengrundlage Akku:** 5000 mAh × 3,7 V = 18,5 Wh. Das Repo rechnet mit ~15 Wh nutzbar (Wandlerverluste, Abschaltgrenze) [Schätzung], `docs/plan/stueckliste-und-psp.md:335-338`. Der Wirkungsgrad des 5-V-Wandlers im PiSugar 3 Plus ist nirgends veröffentlicht (keine Quelle gefunden). Hier gilt: Laufzeit = 15 Wh ÷ Leistung am 5-V-Eingang des Pi. Mit 80 bis 90 % Wirkungsgrad wären es 14,8 bis 16,7 Wh.

---

## 0. Die zehn wichtigsten Erkenntnisse

1. **Der PiSugar 3 Plus schaltet den Pi nach `systemctl poweroff` wirklich ab.** Sein Dienst `pisugar-poweroff` schaltet 3 s nach dem Herunterfahren den 5-V-Ausgang ab (PR #23, Quelle P5; vom Autor nicht am Gerät geprüft). Danach geht er in „Hibernate“. Dort laufen nur noch Taste, Netzteil-Erkennung, RTC und Timer weiter (I²C-Datenblatt, P1). Die Ruhestrom-Zahl für Hibernate gibt es **nicht**. Es gibt nur: „Ausgang aus, aber **ohne** Hibernate: 1 mA“ [Herstellerangabe].
2. **Einschalten bei Strom am Eingang ist beim PiSugar 3 laut I²C-Datenblatt ab Werk AN** (Register 0x02, Bit 4, „Default on“) [Herstellerangabe, P1]. Das Repo geht an mehreren Stellen von „aus“ aus (`docs/plan/stueckliste-und-psp.md:41`, `:589`) und nannte die Bedeutung „unklar“ (`docs/egm/ladestation/software_folgen.md:26`). Der Schalter `auto_power_on` in der `config.json` des Servers ist etwas anderes: Er „verhindert das Einschlafen“ (P4) und soll das Setzen des RTC-Alarms blockieren (Beobachtung im Quellcode eines Dritten, P5, nicht geprüft).
3. **Taster-Pads des PiSugar 3 Plus:** Pad 10 (Powertaste) und Pad 9 (Sondertaste) lösen aus, wenn sie mit **BAT (Pad 2) verbunden** werden. BAT liegt bei etwa 3,0 bis 4,2 V [Herstellerangabe, P2]. Ein GPIO des ESP32 (3,3 V) kann das nicht direkt treiben, es braucht einen Schalter von BAT nach Pad 10 (Transistor, Analogschalter oder Optokoppler). Schaltplan: **nicht gefunden**. Mit eingeschaltetem Anti-Mistouch (Werkseinstellung) braucht das Einschalten „kurz drücken, dann lang drücken“, bis 4 LEDs zählen [Herstellerangabe, P2]; ausgeschaltet reicht kurz [P1].
4. **Der ESP32 braucht eine eigene Stromquelle, solange der Pi aus ist.** Der 5-V-Ausgang ist dann weg. Dokumentiert und dauerhaft vorhanden ist nur **BAT (Pad 2, 3,0 bis 4,2 V)**. Ob man dort Strom entnehmen darf, steht nirgends (keine Warnung, keine Freigabe). Der ESP32-S3 und der PN5180 brauchen 3,3 V; BAT liegt darüber, also ein Spannungsregler mit kleinem Ruhestrom dazwischen.
5. **PN5180 LPCD-Wache ist machbar, aber nicht kostenlos.** ESPuino macht genau das (ESP32 im Deep-Sleep, PN5180 im LPCD, IRQ weckt den ESP32). Der ESPuino-Entwickler nennt **+~300 µA im Deep-Sleep** [Entwicklerangabe, kein Messprotokoll, P12]. Der PN5180-Chip selbst: Standby 15 µA, Power-down 10 µA [Herstellerangabe, P10]; einen LPCD-Mittelwert nennt NXP im Datenblatt nicht. LPCD merkt **jede Änderung des Feldes** (Karte oder Metall), nicht nur eine Karte; seit 01/2024 prüft ESPuino beim Aufwachen auch ISO 15693 (P13). Ob ein **Tonie** (ICODE SLIX2 hinter Deckel) so zuverlässig erkannt wird: **nirgends belegt, nur am Muster messbar**.
6. **Die Dauerabfrage ist teurer als der Plan annimmt.** Der ESP32-S3 im Leerlauf bei 240 MHz zieht 33 bis 48 mA bei 3,3 V (Tab. 5-9, Zeile WAITI) [Herstellerangabe, P11]. Der PN5180 mit Feld an: 180 mA typisch bei 5 V ≈ 0,9 W (P10). Der Plan rechnet mit +0,1 bis 0,2 W (`docs/plan/stueckliste-und-psp.md:207-208`). Meine Gegenrechnung: ESP32 + PN5180 im 200-ms-Takt ≈ **0,2 bis 0,4 W** [Schätzung] (Abschnitt 1.4).
7. **Der APA102-Ring zieht auch dunkel Strom:** ~0,7 bis 1 mA je LED, bei 40 LEDs ≈ 28 bis 40 mA ≈ **0,14 bis 0,2 W** [gemessen von einem Dritten, 1 Stück, P14; für den LuMini-Ring unbestätigt]. Das ist so viel wie WLAN. Der Ring-Strom lässt sich nur abschalten, wenn die Hardware dafür einen Schalter hat.
8. **Der Pi 3 Model A+ kann nicht schlafen.** Suspend ist in Raspberry Pi OS abgeschaltet; ein experimenteller Kernel-Zweig (s2idle für BCM2835-Familie, getestet u. a. auf 3A+) spart beim Pi 1 nur ~0,34 W, und der USB-Teil schläft nicht mit (P6). Realistisch bleibt: Pi an (≥ ~0,8 bis 1,0 W) oder Pi aus.
9. **Kalter Start:** Für den Pi 3A+ mit Raspberry Pi OS Lite gibt es **keine gemessene Zahl** in den Quellen. Vergleichswerte: Pi 3 mit Buster Lite, von Hand getrimmt, 7,6 s (Kernel 1,8 + Userspace 5,8, ohne Firmware-Zeit) [gemessen, P20]; Zero 2 W mit Bookworm unverändert 22 bis 23 s [gemessen, P21]. Das Repo schätzt 20 bis 30 s bis „bereit“ (`docs/egm/ladestation/resolve.md:101`). Der Pi-Firmware-Teil kommt dazu (~1,25 s auf einem Pi 3 mit Buildroot, P22).
10. **Echte Toniebox:** Schaltet sich nach 10 min (Toniebox 1) bzw. 5 min (Toniebox 2) ohne Aktivität ab, Aufwecken laut Tonies-Support durch Zwicken eines Ohres. Zum Ruhestrom gibt es **keine** veröffentlichte Zahl. Laufzeit „7 h“ (Toniebox 1, 3 × NiMH 2000 mAh) bzw. „bis zu 10 h“ (Toniebox 2, laut Händler 9,6 Wh) (Abschnitt 6).

**Unsicher bleibt (nur am Muster messbar):** Ruhestrom des PiSugar im Hibernate; ob ein Tonie die LPCD-Schwelle auslöst und aus welcher Höhe; Strom aus Pad 2 (BAT) für einen ESP32; Zeit der „kurz-dann-lang“-Taste; Startzeit des Pi 3A+ bis zum Ton; echter Leerlauf-Strom der ganzen Box; ob „Einschalten bei Strom“ pegel- oder flankenabhängig ist (Startschleife); Regler des SuperMini (LDO oder Schaltregler) und sein Ruhestrom. Liste in Abschnitt 9.

---

## 1. Stromverbrauch je Zustand

### 1.1 Pi 3 Model A+ (Rechner allein)

| Zustand | Wert | Art | Quelle |
|---|---|---|---|
| Leerlauf, Wi-Fi verbunden, HDMI-Monitor und USB-Dongle dran, 5,2 V | **240 mA** (≈ 1,25 W) | gemessen (Dritter, Shunt, Zeitmittel) | P15: raspi.tv, „How much power does the Raspberry Pi 3A+ use“ |
| dieselbe Quelle, nach `startx` (LXDE) | 470 mA | gemessen (Dritter) | P15 |
| Leerlauf | 220 mA; unter Last (sysbench) 830 mA | gemessen (Dritter) | P16: Linux Format 12/2018 **(Suchtreffer)** |
| Leerlauf | ≈ 1,126 W (≈ 225 mA bei 5 V) | gemessen (Dritter) | P17: kompulsa.com **(Suchtreffer)** |
| Pi Zero 2 W (gleiche Chipfamilie, nicht 3A+), HDMI+LEDs aus | 100 mA ohne, 120 mA mit Onboard-WLAN | gemessen (Dritter) | P18: pidramble.com Power-Consumption (der 3A+ fehlt dort, nur A+, 3B, 3B+) |
| Pi 3B (zum Vergleich), HDMI+LEDs aus | 230 mA, mit WLAN 250 mA | gemessen (Dritter) | P18 |
| Pi 3B+, Leerlauf mit WLAN | 435 mA; HDMI aus −20 mA; WLAN-Schnittstelle runter: 142 mA (nach ausgeschaltetem USB-Bus, der 3B+ hat einen LAN/Hub-Chip, den der 3A+ nicht hat) | gemessen (Dritter) | P19: forums.raspberrypi.com `t=208110` |
| Pi 3, nach `poweroff` aber 5 V weiter dran | ~85 mA; nach `halt` über 500 mA (alte Firmware, 2016, Pi 3B) | gemessen (Dritter) | P23: forums.raspberrypi.com `t=140088` |

Der Plan rechnet mit Leerlauf mit WLAN 1,1 bis 1,3 W für die **ganze Box** und Wiedergabe 1,6 bis 1,9 W [Schätzung], `docs/plan/stueckliste-und-psp.md:376-385`. Der Pi allein liegt nach den Messungen bei etwa 1,0 bis 1,25 W (HDMI nicht angeschlossen: etwas weniger).

### 1.2 Was einzelne Maßnahmen am Pi bringen

| Maßnahme | Effekt | Art | Quelle |
|---|---|---|---|
| WLAN aus (`wlan0 down`, rfkill, Overlay `disable-wifi`) | Pi 3B+: ~50 mA (142 gegen ~195 mA). Zero 2 W: ~20 mA. Für den 3A+ also grob **−0,1 bis −0,25 W** | gemessen (Dritte), Übertrag auf 3A+ = Schätzung | P19, P18 |
| HDMI aus | 3B+: −20 mA (alt). Auf Lite ohne Monitor laut einer Anleitung 2026 „nichts zu sparen“ | gemessen (alt) / Aussage Dritter | P19; P24 (raspberry.tips, **Suchtreffer**) |
| Kerne abschalten (`maxcpus=1`) | Zero 2 W: **unter Last** 420 bis 460 mA → 180 bis 220 mA; **im Leerlauf** kaum Wirkung (INA260-Messung im Forum; CNX: 74,5 mA Leerlauf erreicht) | gemessen (Dritte) | P25: Jeff Geerling, CNX, forums `t=322478` **(Suchtreffer)** |
| Takt senken | Auf dem Pi 3 hat `arm_freq_min` laut einem Mailinglisten-Beitrag in neuer Firmware keine Wirkung nach unten; Leerlauf-Takt ist schon niedrig | Aussage Dritter, **nicht geprüft** | P26 (**Suchtreffer**) |
| USB-Strom aus (`buspower`) | 3B+: −200 mA, weil der Hub/LAN-Chip ausgeht. **Gilt für den 3A+ nicht**: er hat nur einen USB-Port ohne Hub-Chip; am Port hängt der ESP32 | gemessen (3B+); Folgerung = Schätzung | P19 |
| LAN-Chip aus | entfällt beim 3A+ (kein LAN-Chip) | Folgerung | P19 |
| Wi-Fi-Powersave (`iw wlan0 set power_save on`) | **keine Messung gefunden**; im Repo offen als PSP 5.6.6 | – | `docs/plan/stueckliste-und-psp.md:595` |

### 1.3 PiSugar 3 Plus selbst

| Zustand | Wert | Art | Quelle |
|---|---|---|---|
| Ausgang aus, **ohne** Hibernate | **1 mA** | Herstellerangabe (Satz im Original abgeschnitten, Bedingung unklar) | P1: I²C-Datenblatt, Abschnitt „Automatic Hibernate“, Punkt 8d |
| Ausgang aus, **mit** Hibernate (Werkseinstellung: an) | **keine Zahl veröffentlicht**. I²C geht dann nicht mehr. Taste, Netzteil-Erkennung, RTC und Timer laufen weiter | Herstellerangabe (nur Funktion) | P1 (Register 0x03, Bit 6) |
| Eigenverbrauch bei laufendem Pi | **keine Zahl veröffentlicht** | – | P1, P2 |
| Eingang/Ausgang/Akku | Eingang 5 V bis 3 A, Ausgang 5 V bis 3 A, 5000 mAh | Herstellerangabe | P2 |
| Wirkungsgrad Wandler, Chip | **nicht veröffentlicht** | – | – |
| Verkäuferangabe Laufzeit | 8 bis 10 h (Tindie, Beschreibung) | Herstellerangabe, ohne Bedingungen | P27 |

Der Ruhestrom im Aus-Zustand ist die wichtigste Zahl für „Wochen im Regal“ und **nur am Muster zu messen**. Rechenbeispiel (rein rechnerisch, ohne Selbstentladung der Zelle und ohne Abschaltspannung): 5000 mAh ÷ 1 mA = 5000 h ≈ **208 Tage**; ÷ 0,3 mA ≈ 694 Tage; ÷ 0,1 mA ≈ 2083 Tage [Schätzung]. In der Praxis dominiert ab etwa 0,1 mA die Selbstentladung der LiPo-Zelle (keine Quelle gelesen).

### 1.4 ESP32-S3 SuperMini + PN5180

| Zustand | Wert | Art | Quelle |
|---|---|---|---|
| ESP32-S3, Modem-Sleep (Funk aus), 240 MHz, beide Kerne im Leerlauf (WAITI) | **32,9 mA** (Peripherie-Takte aus) bzw. 47,6 mA (alle an), bei 3,3 V | Herstellerangabe | P11: ESP32-S3 Datasheet v2.2, Tab. 5-9 |
| dasselbe bei 80 MHz | 22,0 / 36,1 mA; bei 40 MHz 13,2 / 18,8 mA | Herstellerangabe | P11 |
| dasselbe, beide Kerne rechnen (240 MHz, 32-Bit-Zugriffe) | 66,2 / 81,3 mA | Herstellerangabe | P11 |
| Light-Sleep | 240 µA (nur Chip; mit Flash am Strom ein Nutzerbericht: ~692 µA) | Herstellerangabe / gemessen (Dritter) | P11; esp32.com-Forum **(Suchtreffer)** |
| **Deep-Sleep** (RTC-Speicher an, RTC-Peripherie aus) | **7 µA**; mit RTC-Peripherie 8 µA; „Power off“ (CHIP_PU low) 1 µA | Herstellerangabe | P11: Tab. 5-10 |
| SuperMini-**Platine** im Deep-Sleep | „etwa 43 µA“ (ohne Messbedingung, nicht als gemessen gekennzeichnet). Roter Power-LED/WS2812 und Spannungsregler können deutlich mehr verbrauchen (Beispiel-LDO 80 µA typ.; Power-LED ~0,25 mA) | Verkäuferangabe / Aussage Dritter | P28: espboards.dev; P29: hubble.com, esp32.com (**Suchtreffer**) |
| PN5180 Power-down (RESET_N low) | 10 µA typisch | Herstellerangabe | P10: NXP PN5180A0xx/C3,C4 Datasheet Rev. 4.3, Tab. 1 |
| PN5180 Standby | 15 µA typisch | Herstellerangabe | P10, Tab. 1 |
| PN5180 Feld an (TX-Treiber, TVDD 5 V) | 180 mA typisch, 250 mA max. ≈ **0,9 W** | Herstellerangabe | P10, Tab. 1 |
| PN5180 LPCD, Mittelwert | **kein Wert im Datenblatt.** Ablauf: Standby-Phase (Wake-up-Zähler 1 bis 2690 ms), dann kurze Messphase mit Feld an (`LPCD_FIELD_ON_TIME`, Byte × 8 µs). Mittelwert hängt von diesen Einstellungen ab | Herstellerangabe | P10: Abschnitt „SWITCH_MODE“, EEPROM 0x36/0x37 |
| PN5180 LPCD in ESPuino (Deep-Sleep des ESP32 + PN5180 im LPCD) | „**~300 µA mehr** im Deep-Sleep“. Zähler in ESPuino: 0x3FF ≈ 1023 ms | Entwicklerangabe im Pull-Request, Messbedingung nicht genannt | P12: github.com/biologist79/ESPuino/pull/50; Zähler: P13 (`RfidPn5180.cpp`) |
| Firmware heute: Abfragetakt | 200 ms (Beginn zu Beginn), kein LPCD, kein Sleep | Repo | `firmware/tobibox-reader/include/timing.h:9`; `src/main.cpp:103-116` |

**Gegenrechnung Dauerabfrage im 200-ms-Takt [Schätzung]:**
ESP32-S3 im Leerlauf 33 bis 48 mA, bei Speisung aus 5 V über einen Linearregler dieselbe Stromstärke: 5 V × 0,033 bis 0,048 A = **0,17 bis 0,24 W**. Der Regler des SuperMini (LDO oder Schaltregler) ist **nicht belegt**. Dazu der RF-Puls des PN5180: Bei z. B. 10 ms Feld an je 200 ms wären es 5 % × 0,9 W ≈ 0,045 W (Dauer des Feldes nicht gemessen). Summe etwa **0,2 bis 0,35 W**. Der Plan nennt 0,1 bis 0,2 W (`docs/plan/stueckliste-und-psp.md:207-208`). Das Repo sagt selbst, ein dauerhaft eingeschaltetes Feld wäre „fast 1 W“ (`:208`), das deckt sich mit 180 mA × 5 V aus dem Datenblatt.

**Summe „Wache“ mit ESP32 im Deep-Sleep + PN5180 im LPCD [Schätzung]:** ESP-Platine 0,05 bis 0,5 mA (je nach LED/Regler) + PN5180/LPCD 0,1 bis 0,3 mA (ESPuino-Angabe) + Spannungsregler am Akku 0,001 bis 0,08 mA ≈ **0,2 bis 0,8 mA**. Das kommt zum Ruhestrom des PiSugar dazu.

### 1.5 MAX98357A

Quelle P30: MAX98357A/B Datenblatt (Maxim/Analog Devices), Tabelle „Electrical Characteristics“; [Herstellerangabe].

| Zustand | Wert |
|---|---|
| Ruhestrom im Betrieb (kein Signal), VDD = 3,7 V | 2,4 mA typ., 2,85 mA max. (bei anderer Spannung 2,75 / 3,35 mA) |
| **Shutdown** (SD_MODE = 0 V) | **0,6 µA typ., 2 µA max.** |
| **Standby** (SD_MODE = 1,8 V, kein BCLK) | 340 µA typ., 400 µA max. |
| Einschaltzeit aus Shutdown | 7 ms typ., 7,5 ms max. |

Im Plan steuert das Kernel-Overlay `max98357a` SD_MODE selbst und hält den Verstärker still, solange kein Strom fließt (`docs/plan/stueckliste-und-psp.md:50-54`). Die Platine hängt am 5-V-Ausgang des PiSugar; ist der Pi aus, ist auch der Verstärker stromlos. Beim Adafruit-Breakout ziehen 1 MΩ von SD nach VIN und intern 100 kΩ nach GND den Pin (Adafruit-Learn-Seite, **Suchtreffer**); welche Platine bestellt ist, steht in der Stückliste nicht genau.
Kopfhörer-DAC PCM5102A: Standby-Strom DVDD 0,3 bis 0,8 mA, Betrieb AVDD ~11 bis 16 mA laut Datenblatt-Zusammenfassung (**Suchtreffer**, nicht selbst gelesen, Revisionen weichen ab).

### 1.6 Laufzeit je Zustand (Rechnung, 15 Wh nutzbar)

Leistung = ganze Box am 5-V-Ausgang des PiSugar. Alle Werte [Schätzung], aus den Einzelwerten oben und dem Plan.

| Zustand | Leistung | Laufzeit (15 Wh) | Bemerkung |
|---|---|---|---|
| Wiedergabe | 1,6 bis 1,9 W (Plan) | 7,9 bis 9,4 h | `docs/plan/stueckliste-und-psp.md:378` |
| Leerlauf mit WLAN, Wert des Plans | 1,1 bis 1,3 W | 11,5 bis 13,6 h | `:379` |
| Leerlauf mit WLAN, **Gegenrechnung** (Pi 1,0 bis 1,2 W + ESP32/PN5180 0,2 bis 0,35 W + Ring dunkel 0,14 bis 0,2 W) | 1,35 bis 1,75 W | 8,6 bis 11,1 h | Streuung aus 1.1 bis 1.4; Ring-Strom nur, wenn nicht abschaltbar |
| Leerlauf, WLAN aus | wie oben −0,1 bis −0,25 W | 9,6 bis 13,6 h (mit Gegenrechnung) | Dienst erreichbar nur lokal; Sync/HA/Tailscale weg |
| + Ring-Strom per Schalter aus | −0,14 bis −0,2 W | +1 bis +2 h | Hardware-Änderung |
| Pi „aus“ aber 5 V an (poweroff ohne PiSugar-Abschaltung) | ~0,43 W (85 mA × 5 V, alte Messung Pi 3B) | ~35 h | Zeigt, warum die Abschaltung durch den PiSugar nötig ist (P23) |
| Pi aus, PiSugar im Ruhezustand | ≤ 1 mA (ohne Hibernate), Hibernate unbekannt | rechnerisch ≥ 208 Tage | Selbstentladung nicht eingerechnet |
| Pi aus + ESP32/PN5180-Wache (LPCD) | 0,2 bis 0,8 mA zusätzlich | rechnerisch 125 bis 400 Tage mit PiSugar 1 mA | in der Praxis begrenzt durch Selbstentladung; nur Muster-Messung zählt |
| Pi mit Akku laufen lassen: ein Kaltstart kostet | etwa 25 s × ~1,5 W ≈ 0,01 Wh | ≈ 30 s Leerlauf entsprechen einem Kaltstart | **Schätzung ohne Messung** (Bootstrom nicht gefunden). Heißt: Leerlauf länger als ~1 min kostet mehr Energie als ein Kaltstart |

---

## 2. Kann der Pi 3A+ schlafen?

| Frage | Antwort | Art / Quelle |
|---|---|---|
| Gibt es Suspend-to-RAM / Standby? | **Nein.** Raspberry Pi OS hat Suspend abgeschaltet. Ein Kernel-Entwickler schrieb, Suspend-to-RAM werde für Raspberry-Pi-Produkte „nicht für alle“ unterstützt und kommt wohl nie. | Aussage Dritter; P6 (**Suchtreffer** openSUSE Bug 1212877, Fedora-Forum) |
| Gibt es etwas Experimentelles? | Ja: **suspend-to-idle (s2idle)** für die BCM2835-Familie (Pi 1, 2, 3). Laut Patch-Serie getestet auf Pi 1B, **Pi 3A+**, 3B+. Weckquelle im Test: Debug-UART. Noch im Entwurf, nicht im Standard-Image. Ersparnis: Pi 1 idle 1,67 W, suspendiert 1,33 W (**≈ 0,34 W**). Der USB-Teil wird (noch) nicht schlafen gelegt. | The Register 07/2024 (gelesen); Patchwork-Serie von Stefan Wahren (**Suchtreffer**) – P6 |
| Weckt der ESP32 über USB einen suspendierten Pi? | Nicht belegt; der Test weckt über UART. | – |
| Wake-from-halt per GPIO3 | Der Pi (Firmware) startet aus dem **Halt** neu, wenn GPIO3 (SCL, Pin 5) auf Masse gezogen wird. Der Pi bleibt dabei **am 5 V**, der Halt-Zustand zieht Strom: ~85 mA nach `poweroff` (Pi 3B, 2016), über 500 mA nach `halt`. Der PiSugar kann außerdem beim Einschalten SCL kurz auf Low ziehen (Register 0x20, Bit 3, „SCL wake“, Werkseinstellung aus). | tstellanova.github.io (gelesen); P23; P1 |
| Was bringt Abschalten von Teilen im Leerlauf? | WLAN aus: −0,1 bis −0,25 W. HDMI: nichts (headless). Kerne/Takt: im Leerlauf ~nichts, nur unter Last. USB: nicht möglich (ESP32 hängt dran, kein Hub-Chip). Ring: −0,14 bis −0,2 W nur per Hardware-Schalter. | Abschnitt 1.2; alles [Schätzung] für den 3A+ |
| Niedrigste realistische Leerlauf-Leistung mit sofortiger Reaktion? | Pi 3A+ ohne WLAN/HDMI und mit ruhendem Ring: etwa **0,8 bis 1,0 W** (grob 150 bis 200 mA am Pi) plus ESP32/PN5180 0,2 bis 0,35 W. Der Dienst reagiert dann ohne Verzögerung; mit WLAN aus fehlen Sync, HA, Tailscale. Ein WLAN, das erst beim Wecken wieder verbindet, braucht mehrere Sekunden (**keine Messung gefunden**). | [Schätzung] aus 1.1/1.2; der Wert ist **nur am Muster zu bestätigen** |

---

## 3. Startzeit: Pi 3A+ bis zum ersten Ton

**Für den Pi 3A+ mit Raspberry Pi OS Lite (Bookworm/Trixie) wurde keine Messung gefunden.** Das Repo schätzt „20 bis 30 s bis Rückmeldung“ [Schätzung], `docs/egm/ladestation/resolve.md:101`, `docs/egm/ladestation/software_folgen.md:149`, `docs/egm/start-am-lader/design_draft.md:448` (Messung 3 am Muster).

Belegte Beispiele (andere Geräte, alle ohne Garantie für den 3A+):

| Beispiel | Zeit | Art | Quelle |
|---|---|---|---|
| Pi 3, Raspbian Buster Lite (2019-09), von Hand getrimmt (13 Dienste deaktiviert: keyboard-setup, dphys-swapfile, avahi, raspi-config, rsyslog, bluetooth, hciuart u. a.; optional dhcpcd aus) | `systemd-analyze`: **1,79 s Kernel + 5,78 s Userspace = 7,57 s** (ohne Firmware-/bootcode-Zeit) | gemessen (Dritter) | P20: kevinsaye.wordpress.com, 02/2020 |
| Pi Zero 2 W, Bookworm Lite (unverändert, mit Desktop-Resten wie wayvnc) | 6,7 s + 16,3 s = **22,9 s**; größte Posten: NetworkManager-wait-online 7,4 s, logrotate 6,2 s | gemessen (Dritter) | P21: forums.raspberrypi.com `t=373247` |
| Pi Zero 2 W, Bookworm, nur Konsole, WLAN/BT aus | 2,4 + 9,0 = ~11,5 s | gemessen (Dritter) | P21 (**Suchtreffer** einer Zusammenfassung, Beitrag nicht selbst gelesen) |
| Pi 4, Bookworm Lite getrimmt | 1,1 + 6,0 = 7,1 s | gemessen (Dritter) | P21 (**Suchtreffer**) |
| Pi 5, Raspberry Pi OS Lite 64, Stoppuhr bis Oberfläche | 25 s (29 s mit Desktop); Bluetooth/Extras aus: −4 s | gemessen (Dritter) | P31: forums.raspberrypi.com `p=2331366` |
| Pi 3, Buildroot-Eigenbau, Hochgeschwindigkeitskamera bis Qt-App | Standard **10,17 s**, optimiert **2,82 s** (Firmware 1,25 s + 0,25 + 0,25 + 0 + 1,07 s); Hebel: Kernel entschlackt, Device-Tree eingebettet, kein BusyBox-Init, App als `/sbin/init`; `start_cd.elf` −0,5 s (ging nicht wegen GPU-Speicher) | gemessen (Dritter), **kein Raspberry Pi OS** | P22: furkantokac.com |
| Pi 4, Raspberry Pi OS Desktop, SSD, Ethernet, WLAN/BT aus, übertaktet | ~3,0 bis 4,5 s (`systemd-analyze`) | gemessen (Dritter); Messpunkt unklar | P32: forums.raspberrypi.com `t=313463` |

Wo die Zeit steckt (alle aus den Beispielen):

* **Pi-Firmware** (bootcode.bin, start.elf): ~1,25 s auf einem Pi 3 [gemessen, P22]; `systemd-analyze` zählt das **nicht** mit.
* **Kernel:** 1,8 s (Pi 3, getrimmt) bis 6,7 s (Zero 2 W, Standard) [P20, P21].
* **Userspace:** 5,8 s getrimmt bis 16 s und mehr. Bremsen in den Beispielen: `NetworkManager-wait-online` (7,4 s), `logrotate` (6,2 s), `man-db` (15 s), `hciuart` (9 s), `exim4`, cloud-init (Trixie auf Zero 1 W: >1 min bis multi-user, mit `/etc/cloud/cloud-init.disabled` abstellbar; P33: forums `t=394400`) [alle gemessen von Dritten].
* **Hebel mit Beleg:** unnötige Dienste abschalten (P20), Bluetooth/UART-Dienste aus (P20, P31 −4 s), `cloud-init` aus (P33), Wait-Online-Dienste nicht abwarten (P21: 7,4 s im Beispiel), kleinere/entschlackte Kernel (P22, mit Buildroot, nicht mit Raspberry Pi OS).
* **Ohne Beleg im Rechercheumfang:** `initramfs` aus, Kernel-Optionen (`quiet`, `boot_delay=0`, `disable_splash=1` – genannt in P34 **(Suchtreffer)**, keine Messung), SD-Karten-Einfluss (keine Quelle). Ein Pi-3B+-Nutzer berichtete im Forum, die Boot-Zeit sei trotz abgeschalteter Dienste gleich geblieben (Suchtreffer, Beitrag nicht gelesen).
* Dazu kommen **im Tobi-Box-System** (ohne Messwerte, nur aus dem Design): USB-Enumeration des ESP32, Start von MPD und `tobiboxd`, erste Messung des PiSugar (`STROM_START_WARTEN_S`), Netz-Klasse (bis 30 s Wartezeit beim Start-Sync, `docs/designs/box-software.md:558-560`), PiSugar-„kurz-dann-lang“ beim Einschalten per Taste. Wartezeit bis zum **Ton** ist deshalb größer als die `systemd-analyze`-Zahl.
* Einschaltzeit ESP32-S3: nicht gefunden (nur Größenordnung ~1 bis 2 s bis zur Seriellen, Schätzung).

---

## 4. Weck-Quellen des PiSugar 3 Plus

### 4.1 Welche gibt es

| Weck-Quelle | Beleg | Art |
|---|---|---|
| **Taste** (Powertaste, Pad 10). Mit Anti-Mistouch (Werkseinstellung an): **kurz drücken, dann lang drücken**, bis 4 LEDs zählen. Mit Anti-Mistouch aus: kurz drücken reicht. Ausschalten im Betrieb: immer lang drücken (>2 s). | P2 („Click & Hold“); P1 (Register 0x02, Bit 3) | Herstellerangabe |
| **RTC-Wecker** („Timing boot“ für PiSugar 3 unterstützt). Befehle: `rtc_alarm_set <ISO-Zeit> <Wiederholung>`, `rtc_alarm_disable`, `get rtc_alarm_enabled/time`, `get alarm_repeat` (Wochentag-Maske, 127 = alle). Im Register-Datenblatt: Zeitsteuerung Bit 7 von 0x40, Wochentage in 0x44 bis 0x47 (0 = Sonntag), bleibt über Neustart erhalten. Nach einer Lesart der Alarm-Zeit im Quellcode eines Dritten speichert der PiSugar 3 **nur Stunde/Minute/Sekunde in UTC** plus Wochentage (PR #23, vom Autor nicht am Gerät geprüft). | P3, P4, P1, P5 | Herstellerangabe; letzter Punkt Aussage Dritter |
| **Einschalten bei Strom am Eingang („Auto-Power-On“, „Power Restore“)**: Wiki-Tabelle „unterstützt“ für PiSugar 3. Im I²C-Datenblatt Register 0x02, **Bit 4, Werkseinstellung AN**: „Restored power boots the Pi and enables output“. Fremdbericht: Web-Oberfläche kennt „Schedule Wake up Config = On Power Restore“; Pi startet, wenn man das Netzkabel zieht und wieder steckt. | P3, P1; Gardenbot-Seite (aus `software_folgen.md:29`) | Herstellerangabe |
| **SCL-Wake**: Register 0x20, Bit 3: zieht beim Einschalten SCL (GPIO3) kurz auf Low, um einen **haltenden** Pi zu wecken (Werkseinstellung aus). | P1 | Herstellerangabe |
| **Watchdogs** (Software-Watchdog, Boot-Watchdog): schalten bei ausbleibendem Füttern den Ausgang kurz aus (Neustart). Kein Weck-Weg aus „aus“. Hinweis im Sugarpie-Projekt: Boot-Watchdog und Ausgangs-Verzögerung „funktionieren auf dem 3 Plus derzeit nicht“. | P1; P7 | Herstellerangabe / Aussage Dritter |
| **Reset-Taste** (Pad 6): setzt den PiSugar zurück, „kein Einschalt-Taster“. | P2 | Herstellerangabe |
| **Sondertaste** (Pad 9, „Custom“): löst die frei belegte Sonderfunktion aus, **nicht** das Einschalten. | P2 | Herstellerangabe |

Weitere Fakten:

* **Hibernate (Werkseinstellung an):** Ist der Ausgang aus, geht der PiSugar sofort in den Ruhezustand; I²C und Sondertasten gehen dann nicht, „power button, external power detection, RTC, timer still function“ (P1, Register 0x03 Bit 6).
* **Wechselwirkung `auto_power_on` (Server-Konfiguration) und RTC-Alarm:** In PR #23 steht, der Alarm lasse sich bei eingeschaltetem `auto_power_on` nicht setzen (Quellcode-Lesung des PR-Autors, nicht am Gerät geprüft) (P5).
* **Boot-Schleife:** Issue #73 im pisugar-power-manager-rs-Projekt beschreibt eine Schleife bei „On Power Restore“, wenn der Akku an der Sicherheits-Schwelle (30 %) liegt: Der Pi startet, fährt wegen der Schwelle herunter, bekommt wieder Strom und startet erneut. Ohne Antwort des Projekts, am 20.10.2026 als „not planned“ geschlossen (P35). Ob „Power Restore“ pegel- oder flankenabhängig ist, ist nicht belegt (`docs/egm/ladestation/software_folgen.md:43-46`). Die Tobi-Box hat dafür eine Schleifenbremse im Entwurf (`docs/egm/start-am-lader/design_draft.md:233-250`).

### 4.2 Kann ein externes Signal (ESP32-GPIO) den PiSugar einschalten?

* **Pads:** Pad 10 = Powertaste, Pad 9 = Sondertaste, beide „Trigger … when connected to **BAT (PAD:2)**“. BAT = Akku-Plus, „roughly 3 V to 4,2 V“ (P2, Herstellerangabe). Das ist ein **Kontakt nach BAT**, kein Massekontakt und kein 3,3-V-Logikpegel.
* **Schaltplan, Pegel, Pull-Widerstand am Pad, Strom beim Drücken:** **nicht gefunden** (nur die Pad-Tabelle der Doku). Die Doku enthält keine Warnung und keine Freigabe zum Anlöten.
* **Hinweise Dritter:** Eine Reddit-Antwort (nur Suchtreffer, unbestätigt) schlägt einen Taster zwischen „Punkt 2 und 10“ vor, das deckt sich mit der Doku. Ein Hackaday-Projekt hat den Original-Taster entfernt und die Pads für einen eigenen Schalter genutzt (ohne Pegel-Angaben) (P36).
* **Im Repo:** Der Arcade-Hauptknopf soll parallel zum Bordtaster des PiSugar gelötet werden; ob der PiSugar 3 Plus Lötpunkte dafür hat, „ließ sich in der Doku nicht nachlesen“ (`docs/plan/stueckliste-und-psp.md:48`, `:180-183`, Punkt 30). Nach der Pad-Tabelle gibt es sie (Pad 10 und Pad 2).
* **Was der ESP32 also tun müsste:** Pad 10 mit BAT verbinden und wieder lösen. Das geht nicht mit einem 3,3-V-GPIO am Pad, sondern über einen Schalter: Transistor oder P-MOSFET mit Pegelumsetzung, ein Analogschalter oder ein Optokoppler/PhotoMOS (Möglichkeiten, **nicht belegt**). Bei eingeschaltetem Anti-Mistouch zwei Impulse in der Reihenfolge „kurz, dann lang“; die Zeiten stehen in der Doku nicht (nur „wait for the LEDs count from 1 to 4“). Alternative: Anti-Mistouch ausschalten (Web-Oberfläche „Advanced Settings“ oder Befehl `set_anti_mistouch`, Register 0x02 Bit 3); ob die Einstellung nach Stromverlust erhalten bleibt, ist nicht belegt.

### 4.3 Wie meldet der pisugar-server Tastendrücke an den Pi?

* **Keine Abfrage, kein Ereignis über die Schnittstellen** (TCP 8423, Socket, WebSocket 8422, HTTP 8421): Es gibt nur `get/set_button_enable <single|double|long>` und `get/set_button_shell`. Der Server **führt für Einfach-, Doppel- und Langdruck einen Shell-Befehl aus** (P4: README und Doku „Power Manager“; wie genau er Tasten erkennt, steht dort nicht). Beispiel der Doku: `set_button_enable long sudo shutdown now`.
* **Repo-Stand:** `docs/betrieb/pisugar-wecker.md:77-114` (Abschnitt 3a, „am Pi prüfen“): `[strom] taste_befehl` als Platzhalter; sichere Wege: Arcade-Knopf zusätzlich an einen GPIO (`[tasten] pin_haupt`) oder Shell-Befehl des PiSugar (`tobibox sim key haupt`, nicht erprobt). Design: `docs/designs/box-software.md:552-557` (Befund B2).
* **I²C direkt:** Das Register-Datenblatt kennt Bit 0 des Registers 0x02 („ob die Powertaste gerade gedrückt ist“) und erwähnt das Löschen eines „TAP“-Tastenzustands (P1). Adressen im Einzelnen und Kollision mit dem laufenden `pisugar-server` (er pollt den I²C-Bus) sind **nicht geprüft**.

---

## 5. Weckt ein aufgelegter Tobie die Box?

### 5.1 Technisch möglich?

* **Ja, im Prinzip:** PN5180 im LPCD + ESP32-S3 im Deep-Sleep, IRQ-Pin des PN5180 weckt den ESP32 (EXT1-Wake) – so macht es ESPuino (P12, P13). Beim Aufwachen initialisiert der ESP32 den PN5180, liest die Kennung; findet er keine Karte, war es wohl Metall, und er geht wieder schlafen. Dann müsste der ESP32 den PiSugar-Taster nachbilden (Abschnitt 4.2).
* **LPCD und ISO 15693 (Tonies):** Älterer ESPuino-Stand: nur ISO 14443 (Aussage des Entwicklers 04/2021). **Seit Version 20240111-1-DEV** erkennt LPCD auch ISO-15693-Tags: der PN5180 melde im LPCD „alle Feldänderungen“, nur die Prüfung beim Aufwachen fehlte (P13: forum.espuino.de „LPCD-Feature: Abhängig von Kartentyp?“). Ein früherer Bericht: ISO-15693-Karten lösten den IRQ aus, ließen sich aber „nicht zuverlässig wecken“ (P37: forum.espuino.de „PN5180 Deepsleep“). Der Entwickler dort: „Jetzt ist aber so das für LPCD viel Aufwand betrieben wurde und der Nutzen eher klein ist“; ein anderer: „In der Praxis gab es mit LPCD schon so viele Probleme, dass ich es am liebsten ausbauen würde“ (Aussagen Dritter, P37).
* **Voraussetzungen und Fallen** (alle P12/P13/P10): PN5180-Firmware **≥ 4.0** (ab Werk oft 3.5, Update über separates Projekt nötig); Metall in der Nähe löst Fehlweckungen aus; IRQ muss an einen echten GPIO des ESP32 (Wake-Pin), nicht an einen Port-Expander; ein Fall mit Dauer-Aufwachen wegen falschem Wake-Modus (`ANY_HIGH` statt `ALL_LOW`); Referenzwerte (Gain/Threshold) werden vor dem Schlafen gemessen.
* **Tonie-Reichweite im LPCD:** Es gibt **keine Messung** für Tonies oder die Reichweite durch den Deckel (der Plan peilt ≤ 2 mm über der Antenne an, `docs/plan/stueckliste-und-psp.md:349`). Der LPCD-Schwellwert (`LPCD_THRESHOLD`) und die Feld-an-Zeit müssen am Muster eingestellt werden (P10, EEPROM 0x36/0x37). **Nur am Muster messbar.**
* **Stand im Repo:** Firmware `tobibox-reader` hat **kein** LPCD und keinen Sleep (nur Bibliotheks-Beispiel unter `.pio/libdeps/…/PN5180-LowPowerCardDetection`); Recherche-Notiz: `docs/egm/software-prototyp/research_pn5180_esp32s3.md:56-62`, `:99` (ESPuino nutzt LPCD nur zum Wecken aus dem Deep-Sleep, `pn5180Lpcd` Vorgabe aus).

### 5.2 Wie bekommt der ESP32 Strom, wenn der Pi aus ist?

Heute: der ESP32-S3 SuperMini hängt per USB am Pi und bekommt 5 V aus dem Pi-USB-Port (`firmware/tobibox-reader/README.md`). Beim Pi-Aus ist der 5-V-Ausgang des PiSugar weg (P5), damit auch der ESP32 und der PN5180.

| Möglichkeit | Fakten | Offen |
|---|---|---|
| **BAT (Pad 2) über Spannungsregler** | 3,0 bis 4,2 V [P2]. PN5180 darf VBAT 2,7 bis 5,5 V und TVDD 2,7 bis 5,5 V [P10], PVDD 3,3 V; ESP32-S3 braucht 3,3 V. Ein Regler mit kleinem Ruhestrom (Datenblattwerte Dritter: bis herunter zu wenigen µA) wäre nötig. | Doku sagt nichts zur **Strombelastbarkeit von Pad 2** oder zur Kopplung mit der Schutzschaltung (Warnung: keine, Freigabe: keine). Eine Rückspeisung des ESP32 in den USB-Port des Pi (Diodenentkopplung) muss gelöst werden. |
| **5-V-Eingang (Pad 8 / USB-C)** | Nur da, wenn Netzteil steckt. Nicht für „Akku-Betrieb“. | – |
| **5-V-Ausgang (Pad 11)** | Aus, wenn Pi aus. | – |
| **Eigene kleine Zelle/Knopfzelle für den Wächter** | Nicht in der Stückliste; Hardware-Änderung. | – |

ESPuino hält den PN5180 im Deep-Sleep des ESP32 am Strom (Jumper JP1, „Keeps the PN5180 powered while the ESP32 sleeps“; P37). LDO/3,3-V-Regelung ist in dem Beitrag nicht besprochen.

### 5.3 Gibt es Projekte, die das so machen?

| Projekt | Was | Quelle |
|---|---|---|
| **ESPuino** (ESP32 + PN5180/RC522) | LPCD-Wake aus Deep-Sleep (PN5180), Timeout 10 min Inaktivität; Aufwecken auch per Taster; Akku-Betrieb mit LiPo/LiFePO4. Messwerte zum Ruhestrom nicht veröffentlicht, nur „+300 µA im Deep-Sleep durch LPCD“. | P12 (PR #50, Januar 2021), P13, README von Hackieuino (ESPuino-Port auf Tonieboxen, P38) |
| **Hackieuino** (Port auf die ESP32-Toniebox) | Wie ESPuino; ISO-15693-Tonies mit Passwort lesbar; Ruhe: Deep-Sleep nach 10 min Standardwert, Wecken mit Encoder-Taste; LPCD nur für ISO 14443 genannt. | P38 |
| **Phoniebox** (Raspberry Pi) | Power-On per Taste an GPIO3 oder Zusatzplatinen (OnOff SHIM). **Kein** Projekt gefunden, das den Pi per NFC-Karte aus „aus“ weckt. Ein Forenbeitrag weist darauf hin, dass ein „ausgeschalteter“ Pi an einer Powerbank trotzdem Strom zieht. | Suchtreffer (forum-raspberrypi.de) |
| **TonUINO** | Kein Beleg zu NFC-Wake gefunden. | – |
| Pi + externer Mikrocontroller, der per Karte weckt | **Nichts gefunden.** | – |

### 5.4 Ruhestrom des Wächter-Aufbaus

Siehe 1.4 (Summe 0,2 bis 0,8 mA [Schätzung]) und 1.6. Der Anteil des ESP32-S3-SuperMini ist die größte Unbekannte (Platine: 43 µA nach Verkäuferangabe bis mehrere hundert µA mit LED/LDO).

---

## 6. Wie macht es die echte Toniebox (nur Fakten)

| Punkt | Fakt | Art / Quelle |
|---|---|---|
| Abschaltzeit | **Toniebox 1:** nach **10 min** ohne Wiedergabe/Änderung automatisch aus. **Toniebox 2:** nach **5 min** Inaktivität. Tonie abnehmen beschleunigt das Ausschalten. | giga.de „Toniebox ausschalten“ (gelesen, P39); Tonies-Support laut Suchtreffer (P40, Seite lieferte 403) |
| Manuell ausschalten | Toniebox 1: gar nicht. Toniebox 2: Box mit der Vorderseite auf die Lautsprecher legen, ein Ohr 4 s drücken. Nicht möglich, solange ein Schlaf-Timer läuft. | P39, P40 |
| Aufwecken | Laut Tonies-Support: **ein Ohr zwicken/drücken**, dann leuchtet die LED grün. Ein Händler-Vergleichstext (MonsterDealz) sagt dagegen: „wacht auf, sobald wieder ein Tonie draufsteht“. Beide Aussagen widersprechen sich, **keine Primärquelle gelesen**. | P40 (Suchtreffer); P41: monsterdealz.de (gelesen) |
| Neustart | Beide Ohren ~10 s (Toniebox 1) bzw. 60 s (Toniebox 2), Box dabei nicht auf der Ladestation. | P39 |
| Laufzeit | Toniebox 1: „7 Stunden“, 3 × NiMH, 2000 mAh [iFixit, P42; ≈ 7,2 Wh bei 3,6 V nominal, Rechnung]. Toniebox 2: „bis zu 10 Stunden“, Hersteller nennt keine exakte Zahl (P41), ein Händlerblatt nennt 9,6 Wh (**Suchtreffer**). Daraus rechnerisch jeweils ≈ 1 W Durchschnitt [Schätzung]. | – |
| Bauteile Toniebox 1 | TI CC3200 (WLAN-Mikrocontroller), TRF7962A (NFC-Leser), DAC3100 (Audio), MMA8451 (Beschleunigungssensor), Lade-IC, 8-GB-microSD. Die Ladestation enthält laut Nutzerkommentar nur ein Netzteil, keine Elektronik. | iFixit-Teardown (P42) |
| Ruhestrom, Wake-Quelle (Ohr-Taster, Beschleunigungssensor, NFC?) | **Nicht veröffentlicht.** Der CC3200 hat einen Hibernate-Modus mit Weckquellen Timer/GPIO (TI-Doku, P43), ob und wie die Toniebox ihn nutzt, ist nicht belegt. | – |
| Tiefentladung | Anleitungen raten, die Box nicht wochenlang leer stehen zu lassen; „kein Licht“ = leer oder tiefentladen. Aus Sicht eines Fremden ein Hinweis auf Ruhestrom, aber kein Beleg. | Suchtreffer (otto.de, desired.de) |
| Toniebox 2 | Schlaf-Timer, Sonnenaufgangswecker, LED-Ring (Neuerungen gegenüber Toniebox 1). | P41 |

---

## 7. Bestand im Repo: wie heute ein- und ausgeschaltet wird

Alle Zeilenangaben Stand 10.11.2026. Kurzform: **Die Box läuft, bis 20 min nichts gespielt wird; dann fährt sie über `systemctl poweroff` herunter und der PiSugar schaltet ab. Eingeschaltet wird per PiSugar-Taste, beim Strom-Anlegen (so geplant, noch nicht am Muster geprüft) oder (nicht gebaut) per RTC-Wecker.**

| Thema | Regel | Beleg |
|---|---|---|
| **Leerlauf 20 min** | `LEERLAUF_S = 1200.0`. Leerlauf = 20 min lang wird nichts gespielt. Danach: Zeiger speichern, herunterfahren. | `box/src/tobibox/idle.py:57`; Design `docs/designs/box-software.md:855-868` (CUJ 16), Tabelle `:1380-1394` |
| **Entscheidung O (09.11.)** | Leerlauf zählt auch bei **liegendem Tobie** (20 min nichts gespielt). Ausnahmen: Sync, Update, Lernmodus. Bedienung an der Box setzt den Zähler zurück. Beim Einschalten spielt ein liegender Tobie sofort weiter. | `docs/designs/box-software.md:532-537` |
| **Zähler zurücksetzen** | Taste, Drehregler, Hauptknopf kurz, Kopfhörer starten die 20 min neu; HA-Befehle (Sync, Update) nicht. | `docs/designs/box-software.md:862-864`, `:1387`; `docs/plan/stueckliste-und-psp.md:741` |
| **Nie abschalten, solange …** | Lernmodus, Sync oder Update laufen. Am Lader zusätzlich: Sync oder Update noch offen. | `docs/designs/box-software.md:1388`, `:1414`, `:1420-1422` |
| **Tiefstand** | Bei Akku-Tiefstand (nicht am Lader): Sync abbrechen, Ton `akku_leer` (einmal), Zeiger speichern, Herunterfahren. Schwelle Vorgabe **5 %**, Hysterese 3 %, Wiederholung nach fehlgeschlagenem Herunterfahren frühestens nach 60 s. Zusätzlich hat der PiSugar eigene Werte `safe_shutdown_level` / `safe_shutdown_delay`. | `docs/designs/box-software.md:1391`, `:1415`; `box/src/tobibox/power.py:32`, `:40`, `:208`; `docs/betrieb/pisugar-wecker.md:50` |
| **Hauptknopf lang** | Zeiger speichern und herunterfahren. Der PiSugar führt Einfach-/Doppel-/Langdruck als Shell-Befehle aus (Plan: „Lang = Position sichern + Herunterfahren“). **Wie der Druck im Dienst ankommt, ist offen** (`taste_befehl` Platzhalter, oder Knopf zusätzlich an einen GPIO). | `docs/designs/box-software.md:917`, `:1390`, `:552-557`; `docs/plan/stueckliste-und-psp.md:45-48`, `:505`; `docs/betrieb/pisugar-wecker.md:77-114` |
| **Herunterfahren selbst** | `systemctl poweroff` (Vorgabe `abschalt_kommando`), Rückgabecode geprüft, Frist 60 s; bei Fehler Rückkehr in den Betrieb, Zähler neu, HA-Hinweis. | `box/src/tobibox/config.py:211`; `box/src/tobibox/power.py:36-37`, `:182-191`; `docs/designs/box-software.md:547-551` (B1) |
| **Uhr/RTC beim Start** | Beim Start Uhrzeit aus der RTC des PiSugar (`rtc_rtc2pi`), bei Netz NTP; sonst „leiser“-Grenze statt stumm. Offen: Antwort auf `rtc_rtc2pi`. | `docs/designs/box-software.md:1262-1266`; `docs/betrieb/pisugar-wecker.md:58-63` |
| **PiSugar-Wecker** | **Nicht gebaut, kein Code.** Beschrieben: Weckzeit mit `rtc_alarm_set <Zeit> 127`; Box startet, `idle.py` stößt am Lader einmal den Sync an, fährt danach herunter. Offene Punkte: ob der RTC-Alarm nach dem Herunterfahren wirklich einschaltet, ob er bestehen bleibt, Zeit bis zum ersten Sync. Entscheidung für Tobias steht aus (Wecker nur „am Lader“ gedacht). | `docs/betrieb/pisugar-wecker.md:1-7`, `:116-178`; `docs/designs/box-software.md:2815-2828` (AP 4.3) |
| **Einschalten bei Strom (R8)** | Entschieden 10.11.: „Andocken weckt die Box kurz“ (Ton, Ring, Sync). PiSugar-Schalter dafür **am Muster zu bestätigen**. Ersetzt den alten Plan „Andocken darf nicht wecken“. | `docs/egm/ladestation/resolve.md:92-102`; `docs/plan/stueckliste-und-psp.md:41`, `:589`, `:734` |
| **Start am Lader S1–S11 (10.11.)** | S1 jeder Start mit Strom = Start am Lader (kein Merker). S2 Kurz-Zähler **120 s** ab Ende der Rückmeldung, laufender Sync hält wach. S3 Kurz-Modus endet bei Tobie auflegen, Hauptknopf kurz, HA-Befehl (nicht Weiter/Zurück/Drehregler). S4 liegender Tobie spielt wie bisher. S5 Leise-Zeiten: kein Ton, Ring gedimmt. S6 Update vormerken (Vertragsänderung nötig). S7 Start-Sync auch über Hotspot. S8 Andocken bei laufender Box: Sync prüfen. S9 spielendes Hörspiel: nur Ring. S10 Sockel/Kabel nicht unterscheiden. S11 Frühstart-Ring erst nach Messung. | `docs/egm/ladestation/software_folgen.md:449-463`; Entwurf: `docs/egm/start-am-lader/design_draft.md:40-57` |
| **Antworten Teil 1 (10.11., angehalten)** | Q1 Wiederholung des Start-Syncs nur im **Heimnetz**, unterwegs keine Wiederholung. Q2 Liegender Tobie beim Andocken unter „leiser“: offen. Q3 Liegender, stiller Tobie beendet den Kurz-Modus **nicht**, nur Abspielen. Q4 Abziehen im Kurz-Modus: **Frist läuft weiter**. Das EGM ruht, bis `docs/egm/ein-aus/` steht. | `docs/egm/start-am-lader/resolve_teil1.md:3-15` |
| **Startschleife (größte Unbekannte)** | Fährt die Box mit Strom herunter und der PiSugar startet pegelabhängig neu, läuft sie in einer Schleife (Start, 120 s, aus, ~2,5 min). Flankenabhängig wäre sie aus. Nicht belegt. Notnagel im Entwurf: Schleifenbremse (`ende.json`). Messung 1 am Muster. | `docs/egm/start-am-lader/design_draft.md:28-29`, `:233-250`, `:442-455`; `docs/egm/ladestation/software_folgen.md:43-46` |
| **CUJ 20: Tobie liegt beim Start** | Nach echtem Einschalten (auch Strom weg, leerer Akku) spielt ein liegender Tobie sofort am Zeiger; nach Dienst-Neustart nie von selbst (Entscheidung G). Soll-Zeit „bereit“ ist am Pi zu messen. | `docs/designs/box-software.md:919-934` |
| **Startzeit** | Schätzung 20 bis 30 s bis Rückmeldung; Messung 3 am Muster entscheidet auch über S11 (Frühstart-Ring). | `docs/egm/ladestation/resolve.md:101`; `docs/egm/start-am-lader/design_draft.md:448` |
| **Hardware-Annahmen** | Eine USB-C-Buchse am Ladeeingang des PiSugar, Ladesockel ohne Elektronik (R9: USB-C-Stecker im Sockel). ESP32-S3 am Pi-USB; Abfragetakt 200 ms. Laufzeit-Annahmen im Plan siehe 1.6. | `docs/egm/ladestation/resolve.md:111-124`; `firmware/tobibox-reader/include/timing.h:9`; `docs/plan/stueckliste-und-psp.md:374-385` |

---

## 8. Mögliche Grundkonzepte (keine Bewertung, Tobias entscheidet)

Zeitangaben „bis zum Ton“ sind ab Auslöser (Tobie aufgelegt / Taste) gerechnet. Zahlen sind **[Schätzung]**, außer anders vermerkt; Grundlage Abschnitte 1 bis 5. Laufzeit = wie lange der Zustand den vollen Akku leert.

| # | Grundkonzept | Wartezeit bis Ton | Leistung im Wartezustand | Laufzeit im Wartezustand | Nötige Hardware-Änderung | Risiken |
|---|---|---|---|---|---|---|
| **A** | **Immer kalt starten:** Nach kurzer Frist (z. B. 1 bis 2 min) oder sofort nach Ende herunterfahren. Start per **PiSugar-Taste** (Kind drückt) und/oder Strom anlegen. | 15 bis 30 s ab Tastendruck (Stock-Image, Messung fehlt); mit getrimmtem System vielleicht 10 bis 15 s. Dazu Anti-Mistouch: „kurz, dann lang“ oder Anti-Mistouch aus | PiSugar-Ruhe: ≤ 1 mA ohne Hibernate [Herstellerangabe], Hibernate-Wert unbekannt | rechnerisch ≥ 208 Tage; praktisch Wochen bis Monate (Selbstentladung) | keine; evtl. Anti-Mistouch ausschalten | Wartezeit für das Kind; zwei Handgriffe (Taste, Tobie); Startschleife bei „Einschalten bei Strom“ (Messung 1); SD-Karte bei jedem Aus/Ein beansprucht |
| **B** | **Standby mit Pi an, nach X min aus** (heute: X = 20 min, Entscheidung O). | ≈ 0 s (Dienst läuft, Tobie wird wie heute erkannt) | 1,35 bis 1,75 W (Gegenrechnung); Plan 1,1 bis 1,3 W | 8,6 bis 13,6 h bis leer; jede Sitzung kostet 20 min × ~1,5 W ≈ 0,5 Wh (≈ 3 % des Akkus) | keine | Akku-leer, wenn die Box vergessen wird (bis 20 min); Ring/ESP32 ziehen im Leerlauf mit; der Plan geht davon aus, dass sie morgens leer ist, wenn sie nicht abschaltet (`stueckliste-und-psp.md:382-383`) |
| **B2** | **Standby sparsam:** wie B, aber im Leerlauf WLAN aus, Ring-Strom aus, ESP32 langsamer abfragen/Takt senken. | ≈ 0 s bis wenige s (WLAN-Wiederaufbau, falls beim Wecken nötig, nicht gemessen) | 0,9 bis 1,3 W (grob) | 11 bis 17 h | Schalter für Ring-Strom (MOSFET); Software für WLAN/Takt/Abfragerate | Sync, HA, Tailscale in der Zeit nicht erreichbar; längere Abfrage = Auflege-Verzögerung (`docs/timing.md`: Auflegezeit unter 1 s) |
| **C** | **ESP32 wacht, Tobie weckt den Pi** (PN5180 im LPCD, ESP32 im Deep-Sleep, ESP32 drückt den PiSugar-Taster). | Tobie auflegen → LPCD-Intervall (bis 1 s, ESPuino: ~1 s) + ESP32-Aufwachen + Taster-Impulse + Kaltstart: **15 bis 35 s** | Wächter 0,2 bis 0,8 mA + PiSugar-Ruhe (≤ 1 mA) | rechnerisch ~125 bis 400 Tage; praktisch Selbstentladung | Spannungsregler für den ESP32 an BAT (Pad 2); Schalter von BAT zu Pad 10 (und evtl. Pad 9); Diodenentkopplung zum Pi-USB; Firmware: LPCD, Deep-Sleep, PN5180 ≥ 4.0; ggf. Umbau der Stromversorgung des ESP32 | LPCD für Tonie (ISO 15693) unbelegt; Fehlweckungen durch Metall/Hand; Pad 2 als Stromquelle nicht freigegeben; zwei Stromquellen am ESP32 (Rückspeisung); LPCD-Aufwand von ESPuino selbst kritisch gesehen; die ersten Sekunden nach dem Auflegen ohne Rückmeldung (S11 Frühstart-Ring) |
| **D** | **Nachts aus, morgens per Wecker an:** RTC-Alarm, z. B. 07:00. Danach Konzept B (20 min Leerlauf) oder A. | 0 s, wenn die Box zur Weckzeit schon läuft; sonst wie A (Taste) | wie A/B | wie A | keine; Weckzeit setzen (`rtc_alarm_set`) und Uhr (`rtc_pi2rtc`) pflegen | Wecker läuft jeden Tag auch ohne Bedarf; Alarm nur Stunde/Minute/Sekunde in UTC (Sommerzeit!); Server-Einstellung `auto_power_on` blockiert evtl. den Alarm; ob der Alarm nach dem Herunterfahren einschaltet und bestehen bleibt: am Muster prüfen; Wecken ohne Lader kostet Akku |
| **E** | **Wecker nachts am Lader für Sync** (wie `pisugar-wecker.md`): Box startet am Lader, synct, fährt herunter. | nicht relevant für die Bedienung | wie A | wie A | keine; Weckzeit setzen | Heim-WLAN/NAS müssen an sein; Start-Sync Wiederholung nur im Heimnetz (Q1); Startschleife |
| **F** | **Pi bleibt „gehalten“ (halt) mit 5 V, ESP32 weckt per GPIO3** (kein PiSugar-Aus). | ~15 bis 25 s (Firmware + Kernel + Dienst; kürzer als A, weil ohne PiSugar-Start-Sequenz) | ~85 mA × 5 V ≈ 0,43 W (Pi 3B, 2016; alte Firmware), `halt` über 500 mA | ~35 h bis leer (rechnerisch) | Verbindung ESP32-Pin → GPIO3 (SCL, Konflikt mit I²C zum PiSugar); PiSugar-Ausgang muss an bleiben | Schlechtere Standby-Laufzeit als C/A, kaum Gewinn an Wartezeit; SCL-Konflikt mit PiSugar-I²C |
| **G** | **Suspend / Schlafen auf dem Pi** | – | nicht verfügbar im Standard-Image; experimentelles s2idle spart ~0,34 W beim Pi 1 | – | – | USB-Teil schläft nicht mit; Weckweg über USB nicht belegt; nicht empfehlbar ohne eigene Kernelpflege |

Ergänzende Zahlen zu den Konzepten:

* **Break-even** (Schätzung, Bootstrom nicht gemessen): Ein Kaltstart (~25 s bei ~1,5 W) kostet etwa 0,01 Wh. Das ist der Verbrauch von ~30 s Leerlauf bei 1,3 W. Wer die Box länger als etwa eine Minute im Leerlauf laufen lässt, verbraucht mehr als ein Kaltstart kosten würde.
* **Tobie-Wechsel** in kurzer Folge (Folgen-Hörer) sprechen für kurze Frist ODER Pi-an; ein Kaltstart je Auflegen wäre bei Konzept C/A mit 15 bis 35 s Wartezeit verbunden.
* **Bedienschritte** vor dem ersten Ton: A: Taste (evtl. 2 Schritte) + Tobie; B: Tobie; C: Tobie; D: Tobie (morgens), nach Ablauf Taste.

---

## 9. Was nur am Muster messbar ist (Liste)

| # | Messung | Entscheidet |
|---|---|---|
| 1 | **Ruhestrom PiSugar 3 Plus im Aus-Zustand** (Hibernate an, Pi aus, kein Netzteil): µA über Stunden, auch bei kaltem Akku | Alle Konzepte mit „Pi aus“ (A, C, D, E) |
| 2 | **Leerlauf-Strom der ganzen Box** am Muster: mit/ohne WLAN, Ring dunkel (Ring-Ruhestrom!), ESP32 im 200-ms-Takt, MAX98357A im Shutdown | B, B2; Plan 1.5 |
| 3 | **Startzeit** Pi 3A+: Taste/Strom bis „bereit“, bis Ton; mit Standard-Image und nach Trimmen (Dienste, wait-online, cloud-init, Bluetooth) | A, C, D; S11 (Frühstart-Ring) |
| 4 | **Einschalten bei Strom** (Register 0x02, Bit 4): pegel- oder flankenabhängig; Verhalten nach Herunterfahren am Lader, nach Akkutausch/Reset | Startschleife, R8, A/E |
| 5 | **Wecker (RTC) nach Herunterfahren:** schaltet er ein; bleibt der Alarm; Wechselwirkung mit `auto_power_on` und mit Anti-Mistouch | D, E |
| 6 | **Taster-Pad 10:** Spannung, Strom, Pull-Widerstand; Dauer von „kurz, dann lang“; hält Anti-Mistouch-Einstellung nach Stromverlust | C und A (Anti-Mistouch aus) |
| 7 | **Pad 2 (BAT) als Quelle** für einen Wächter: wie viel Strom darf man entnehmen, Verhalten der Schutzschaltung | C |
| 8 | **LPCD mit Tonie hinter dem Deckel:** Schwelle, Feld-an-Zeit, Erkennung ja/nein, Fehlweckungen (Hand, Metall im Gehäuse), Ruhestrom mit SuperMini und PN5180 | C |
| 9 | **SuperMini:** Spannungsregler (LDO/Schaltregler), Power-LED/WS2812, Deep-Sleep-Strom der echten Platine | C, Abfragetakt in B |
| 10 | **Hauptknopf-Weg:** Gibt es einen `pisugar-server`-Befehl für Tasten, oder Shell-Befehl/GPIO (Bericht B2) | alle Konzepte mit Taste |
| 11 | **Bootstrom** und Kaltstart-Energie (Wh je Start) | Break-even A gegen B |
| 12 | **WLAN-Powersave und Wiederverbindungszeit** | B2 |

---

## 10. Quellenliste

**PiSugar**
* P1: PiSugar3 I²C Datasheet, https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-i2c (gelesen 10.11.2026; Seite meldet Register 0x02/0x03/0x20/0x40 usw.)
* P2: PiSugar3 Series (Pads, Taste, Elektrik), https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series
* P3: PiSugar-Wiki „PiSugar 3 Series“ (Funktionstabelle; nicht mehr gepflegt), https://github.com/PiSugar/PiSugar/wiki/PiSugar-3-Series
* P4: pisugar-power-manager-rs README, https://github.com/PiSugar/pisugar-power-manager-rs ; PiSugar Power Manager (Software), https://docs.pisugar.com/docs/product-wiki/battery/pisugar-power-manager
* P5: ShengKai234/google-calendar-api, Pull Request #23 (Wecken per RTC, `pisugar-poweroff`, `force_shutdown`; **nicht am Gerät geprüft, Aussage Dritter**), https://github.com/ShengKai234/google-calendar-api/pull/23 ; Quelle des Poweroff-Programms: https://raw.githubusercontent.com/PiSugar/pisugar-power-manager-rs/master/pisugar-poweroff/src/main.rs (3 s Countdown, 100 Versuche)
* P7: sugarpie (PyPI), https://pypi.org/project/sugarpie/
* P27: Tindie PiSugar 3 Plus, https://www.tindie.com/products/pisugar/pisugar-3-plus-battery-for-raspberry-pi-3b3b4b/ (Suchtreffer)
* P35: Issue #73 „PiSugar3 on Pi0-2W: On Power Restore loops“, https://github.com/PiSugar/pisugar-power-manager-rs/issues/73
* P36: Hackaday-Projekt Epson HX 2023, https://hackaday.io/project/191670-epson-hx-2023/log/220657-switches

**Pi und System**
* P6: The Register 03.07.2024, https://theregister.com/2024/07/03/kernel_tweaks_rapsberry_pi ; openSUSE Bug 1212877 (Suchtreffer); Patchwork-Serie von Stefan Wahren, https://patchwork.kernel.org/project/linux-arm-kernel/cover/20241024201837.79927-1-wahrenst@gmx.net/ (Suchtreffer, Zugriff blockiert)
* P15: https://raspi.tv/2018/how-much-power-does-raspberry-pi-3a-plus-use
* P16: Linux Format 12/2018 (Suchtreffer), https://www.pressreader.com/australia/linux-format/20181218/281612421488206
* P17: https://www.kompulsa.com/2019/02/06/comparing-the-raspberry-pi-3a-vs-the-3b-the-most-important-differences (Suchtreffer)
* P18: https://www.pidramble.com/wiki/benchmarks/power-consumption
* P19: https://forums.raspberrypi.com/viewtopic.php?t=208110
* P23: https://forums.raspberrypi.com/viewtopic.php?f=28&start=25&t=140088
* P24: https://raspberry.tips/en/raspberrypi-tutorials/raspberry-pi-power-consumption-update-2026-all-models-compared (Suchtreffer)
* P25: https://www.jeffgeerling.com/blog/2021/disabling-cores-reduce-pi-zero-2-ws-power-consumption-half/ ; https://www.cnx-software.com/2021/12/09/raspberry-pi-zero-2-w-power-consumption/ ; https://forums.raspberrypi.com/viewtopic.php?t=322478&start=75 (alle Suchtreffer)
* P26: Alpine-Mailingliste (Suchtreffer), https://lists.alpinelinux.org/~alpine/users/%3CCAD1Ag0ytC8yoOpadYtxwaMCG18u168x1fc_chrqW3wqrO4rayw%40mail.gmail.com%3E
* Wake-from-halt: https://tstellanova.github.io/docs/rpi-wake-from-halt-energy.html
* P20: https://kevinsaye.wordpress.com/2020/02/18/fast-booting-raspbian-on-a-pi-3-in-less-than-8-secon/
* P21: https://forums.raspberrypi.com/viewtopic.php?t=373247
* P22: https://furkantokac.com/rpi3-fast-boot-less-than-2-seconds/
* P31: https://forums.raspberrypi.com/viewtopic.php?p=2331366
* P32: https://forums.raspberrypi.com/viewtopic.php?t=313463
* P33: https://forums.raspberrypi.com/viewtopic.php?t=394400
* P34: https://forums.raspberrypi.com/viewtopic.php?t=184779 und Kevin Saye P20 (Suchtreffer für `boot_delay=0`, `quiet`)

**Bauteile**
* P10: NXP PN5180A0xx/C3,C4 Product data sheet Rev. 4.3 (30.10.2025), https://www.nxp.com/docs/en/data-sheet/PN5180A0XX_C3_C4.pdf (Tab. 1 Quick reference data, Abschnitt SWITCH_MODE, EEPROM-Tabelle; lokal ausgelesen)
* P11: Espressif ESP32-S3 Series Datasheet v2.2, https://documentation.espressif.com/esp32-s3_datasheet_en.pdf (Tab. 5-9, Tab. 5-10; lokal ausgelesen)
* P30: Maxim/Analog Devices MAX98357A/MAX98357B Datenblatt (Abschnitt Electrical Characteristics, SD_MODE and Shutdown Operation); Kopie https://www.makerguides.com/wp-content/uploads/2026/01/Datasheet_MAX98357A.pdf (lokal ausgelesen)
* P28: https://www.espboards.dev/esp32/esp32-s3-super-mini/
* P29: https://hubble.com/community/guides/esp32-deep-sleep-current-what-the-datasheet-says-vs-what-you-ll-actually-measure/ ; https://esp32.com/viewtopic.php?t=32177 (Suchtreffer)
* P14: https://memcpy.io/apa102-led-current-usage.html (APA102-2020, ein Muster, Multimeter in Reihe)
* PCM5102A: TI Datenblatt SLAS859 (Suchtreffer-Zusammenfassung), https://www.ti.com/product/PCM5102A/datasheet ; Adafruit MAX98357 Learn-Seite: https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp
* P12: ESPuino Pull-Request #50 „wake-up by just adding a card on the reader (PN5180 LPCD)“, https://github.com/biologist79/ESPuino/pull/50
* P13: ESPuino `src/RfidPn5180.cpp`, https://raw.githubusercontent.com/biologist79/ESPuino/master/src/RfidPn5180.cpp ; Forum „LPCD-Feature: Abhängig von Kartentyp?“, https://forum.espuino.de/t/lpcd-feature-abhaengig-von-kartentyp/379
* P37: ESPuino-Forum „PN5180 Deepsleep“, https://forum.espuino.de/t/pn5180-deepsleep/688
* P38: Hackieuino (ESPuino-Port für die ESP32-Toniebox), https://github.com/toniebox-reverse-engineering/Hackieuino

**Toniebox**
* P39: https://www.giga.de/tipp/toniebox-ausschalten-neustarten-so-gehts
* P40: Tonies-Support, https://support.tonies.com/hc/en-gb/articles/29036375070226-How-do-I-turn-the-Toniebox-off und https://support.tonies.com/hc/en-ca/articles/32957238819346-Can-I-manually-turn-off-my-Toniebox-2 (beide beim Abruf 403; Inhalt nur als Suchtreffer-Zusammenfassung)
* P41: https://www.monsterdealz.de/magazin/toniebox-2-vergleich
* P42: iFixit Toniebox Teardown, https://www.ifixit.com/Teardown/Toniebox+Teardown/106148
* P43: TI CC3200 Hibernate Application, https://processors.wiki.ti.com/index.php/CC3200_Hibernate_Application (Suchtreffer)

**Repo (alle Pfade unter `/home/user/Tobi_box/`)**
`CLAUDE.md`; `docs/plan/stueckliste-und-psp.md`; `docs/designs/box-software.md`; `docs/betrieb/pisugar-wecker.md`; `docs/egm/ladestation/resolve.md`; `docs/egm/ladestation/software_folgen.md`; `docs/egm/start-am-lader/design_draft.md`; `docs/egm/start-am-lader/resolve_teil1.md`; `docs/egm/software-prototyp/research_pn5180_esp32s3.md`; `box/src/tobibox/idle.py`; `box/src/tobibox/power.py`; `box/src/tobibox/config.py`; `firmware/tobibox-reader/include/timing.h`; `firmware/tobibox-reader/src/main.cpp`.
