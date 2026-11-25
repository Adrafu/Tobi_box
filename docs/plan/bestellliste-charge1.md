# Bestellliste Charge 1 — Pi-Probelauf und Breadboard

Stand 25.11.2026 · Grundlage: Plan Rev. 3.23 (Stückliste 1.1/1.2, PSP 1.2.1),
Hardware-Prüfung 3.21 · ersetzt die Liste vom 07.11.

Zweck: alles für den Pi-Probelauf und den Breadboard-Aufbau (3.2), damit danach
das CAD starten kann. **Nur ein Satz** (Muster). Lieferung nach Österreich,
möglichst wenig Gesamtkosten.

Schon vorhanden: 2× PN5180, 2× ESP32-S3 SuperMini, **1× Raspberry Pi 3 Model B+**
(bei Tobias daheim, bisher mit HiFiBerry; für den Probelauf kommt der HiFiBerry
ab, an I²S hängt dann der MAX98357A).

Preise: Recherche vom 24. und 25.11. auf den Shopseiten, brutto. Mit „ungeprüft“
markierte Werte bitte im Warenkorb nachsehen. Die Versandkosten von Mouser
stehen erst im Warenkorb fest.

## Wichtig: Der Pi 3 A+ ist zurzeit nicht lieferbar

Berrybase, Reichelt und Welectron sind ausverkauft, Kiwi (NL) erwartet Nachschub
erst am 26.03.2027, Tinytronics führt ihn nicht mehr, Pimoroni nur Vorbestellung
ohne Termin.

**Entscheidung 24.11.:** Für Probelauf und Breadboard nimmt Tobias seinen
vorhandenen **Pi 3 Model B+**, es wird kein Pi gekauft. Gleicher Chip, gleiches SD-Image, gleiche
Micro-USB-Versorgung; der PiSugar 3 Plus ist laut Hersteller für den 3B+
gemacht. Nachteile: größer (85 × 56 statt 65 × 56 mm) und braucht durch LAN
und USB-Hub etwas mehr Strom. Die fertigen Boxen bekommen weiter den **Pi 3 A+**
(Entscheidung Tobias 24.11.); zwei Stück werden gekauft, sobald er wieder zu
normalem Preis lieferbar ist.

Nicht sinnvoll: Pi Zero 2 W (für den Zero gibt es keinen PiSugar mit 5000 mAh,
nur 1200 mAh, rund 3 h Laufzeit) und Pi 4 (teurer, mehr Strom).

## Shop 1: Reichelt.at (Hauptbestellung)

Wunsch Tobias (25.11.): möglichst viel bei Reichelt. Geprüft am 25.11. auf
reichelt.at, Preise brutto inkl. 20 % MwSt., alles ab Lager. Suche im Shop mit
dem Bestellcode.

| # | Teil | Bestellcode | Stk | € | Wofür |
|---|---|---|---|---|---|
| 1 | SanDisk High Endurance microSD 64 GB | SDSQQNR064GGN6IA | 1 | 27,99 | System und Medien (begrenzte Stückzahl) |
| 2 | Offizielles Pi-Netzteil 5,1 V / 2,5 A Micro-USB, **nur falls keins da ist** | RPI PS 12.5EU WT | 1 | 7,92 | Pi ohne PiSugar |
| 3 | Kühlkörper-Set für den Pi | RPI COOL BK | 1 | 1,16 | Pi |
| 4 | Visaton FRS 8, 4 Ω | VIS FRS 8-4 | 1 | 13,73 | Lautsprecher |
| 5 | Drehgeber KY-040 | DEBO ENCODER | 1 | 2,17 | Lautstärke |
| 6 | Micro-Arcade-Taster weiß, Bohrung 23,5 mm | ARC BUTTON MC WH | 3 | 5,61 | Haupt, Vor, Zurück |
| 7 | PTC-Sicherung 1,1 A | PTC FUSB110F | 1 | 0,90 | 5-V-Pfad Ring |
| 8 | Elko 1000 µF 25 V | RAD FC 1.000/25 | 1 | 0,57 | Puffer am Verstärker |
| 9 | Steckbrett-Set 830 Kontakte | BREADBOARD SET1 | 1 | 7,46 | Breadboard |
| 10 | Jumperkabel 40 Stk. Buchse/Buchse 20 cm | DEBO KABELSET12 | 1 | 1,61 | Breadboard |
| 11 | Jumperkabel 40 Stk. Stecker/Buchse 15 cm | DEBO KABELSET10 | 1 | 1,87 | Breadboard |
| 12 | Sortiment LEDs und Widerstände | S93 | 1 | 5,03 | Teiler Hauptknopf, SD_MODE |
| 13 | NTAG215-Aufkleber, 10 Stk. | BERRYBASE 125451 | 3 | 14,97 | Testkarten |

**Summe ca. 91 € plus Versand** (DPD 6,95 €; eine Gratis-Grenze ist nicht
ausgewiesen). Ohne Netzteil ca. 83 €.

Hinweis zu #6: Die Taster sind die Micro-Ausführung statt der Mini-Taster von
Berrybase. Für das Breadboard reicht das; welche Taster in die Box kommen,
entscheidet das CAD.

## Shop 2: Mouser.at

Den Ring kauft Tobias bei Mouser (25.11.). Dazu kommen die zwei Teile, die
Reichelt nicht hat. Mouser blockt automatische Abrufe, darum sind die Nummern
und Preise **ungeprüft**; bitte im Warenkorb nachsehen.

| # | Teil | Mouser-Nr. | € | Wofür |
|---|---|---|---|---|
| 14 | SparkFun LuMini LED Ring 2″, 40× APA102-2020, **COM-14966** | 474-COM-14966 | ~21 | LED-Ring |
| 15 | Adafruit MAX98357A I²S-Verstärker (Adafruit 3006) | wohl 485-3006 | ~7 | Ton |
| 16 | SN74AHCT125N (DIP-14, nicht die SMD-Ausführung) | wohl 595-SN74AHCT125N | ~0,60 | Pegelwandler LED-Ring |

**Summe ca. 29 € plus Versand** (gratis laut Hilfeseite erst ab etwa 75 €).

## Shop 3: Tinytronics (NL)

| # | Teil | Stk | € | Wofür |
|---|---|---|---|---|
| 17 | PiSugar 3 Plus, 5000 mAh | 2 | 102,00 | Box 1 (Laufzeitmessung) und Box 2 |

Versand nach Österreich 11,50 € (ohne NL-Steuer, eventuell bis 13,92 €), einmal
für beide. **Summe ca. 114–116 €.** Lieferzeit laut Quellen bis 2–4 Wochen.
Den zweiten Akku bei etwa 50 % Ladung kühl lagern (Entscheidung Tobias 24.11.).
Reichelt führt den PiSugar nicht.

## Gesamt

| Shop | ca. € |
|---|---|
| Reichelt.at | 91 + 6,95 |
| Mouser.at | 29 + Versand |
| Tinytronics (2 PiSugar) | 114–116 |
| **Summe** | **ca. 241 € plus Versand Mouser** |

Berrybase entfällt damit ganz.

## Nicht bei Reichelt, später oder anders

- **Neodym-Magnete 10 × 3 mm** (Nachtest Deckel-Magnet): Reichelt hat keine.
  Ein vorhandener kleiner Neodym-Magnet reicht für den Test; sonst mit Charge 2.
- **USB-Tester** (Test 7, Strom und Laufzeit): Reichelt hat keinen passenden.
  Optional, z. B. UNI-T UT658A bei Berrybase (8,90 €) mit Charge 2.

## Bewusst noch nicht

- **PCM5102A-DAC und Klinkenbuchse mit Schaltkontakten** (Kopfhörerpfad 3.2.6):
  der DAC ist zurzeit nirgends lieferbar gefunden, die Buchse hängt daran.
  Kommt mit Charge 2.
- Ideal-Dioden, USB-C-Buchse, Dock-Teile (nach Breadboard und Ladestation Rev. 6).
- Gehäusematerial (nach CAD).

## Hinweise

- Ein **USB-C-auf-USB-A-Datenkabel** (ESP32-S3 an den Pi) ist nicht auf der
  Liste; ein vorhandenes reicht, wenn es Daten überträgt.
- Hat der Mac keinen SD-Schlitz, braucht es einen USB-SD-Kartenleser.
- Der PiSugar kommt erst nach dem ersten Probelauf mit Netzteil auf den Pi.
