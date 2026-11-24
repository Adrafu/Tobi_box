# Bestellliste Charge 1 — Pi-Probelauf und Breadboard

Stand 24.11.2026 · Grundlage: Plan Rev. 3.23 (Stückliste 1.1/1.2, PSP 1.2.1),
Hardware-Prüfung 3.21 · ersetzt die Liste vom 07.11.

Zweck: alles für den Pi-Probelauf und den Breadboard-Aufbau (3.2), damit danach
das CAD starten kann. **Nur ein Satz** (Muster). Lieferung nach Österreich,
möglichst wenig Gesamtkosten.

Schon vorhanden: 2× PN5180, 2× ESP32-S3 SuperMini, **1× Raspberry Pi 3 Model B+**
(bei Tobias daheim, bisher mit HiFiBerry; für den Probelauf kommt der HiFiBerry
ab, an I²S hängt dann der MAX98357A).

Preise: Recherche vom 24.11. auf den Shopseiten, brutto. Mit „ungeprüft“
markierte Werte bitte im Warenkorb nachsehen. Die Versandkosten von Reichelt,
Berrybase und Digikey stehen erst im Warenkorb fest.

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

## Shop 1: Berrybase.at

| # | Teil | Stk | € | Wofür |
|---|---|---|---|---|
| 2 | SanDisk High Endurance microSD 64 GB | 1 | 28,90 | System und Medien |
| 3 | Offizielles Pi-Netzteil 5,1 V / 2,5 A Micro-USB, **nur falls keins da ist** | 1 | 7,90 | Pi ohne PiSugar |
| 4 | Adafruit MAX98357A I²S-Verstärker 3 W | 1 | 5,90 | Ton |
| 5 | SN74AHCT125N (DIP-14) | 1 | 0,54 | Pegelwandler LED-Ring |
| 6 | Mini Arcade Button 24 mm (AB24OL, Farbe wählen) | 3 | 2,70 | Haupt, Vor, Zurück |
| 7 | Elko 1000 µF 25 V | 1 | 0,21 | Puffer am Verstärker |
| 8 | Dupont-Kabelset 40 Stk., 20 cm (DUPK-SET-20) | 1 | 4,90 | Breadboard |
| 9 | NTAG215-Aufkleber, 10 Stk. | 3 | 14,97 | Testkarten |
| 10 | Neodym-Magnet 10 × 3 mm (8 × 3 nicht lieferbar) | 4 | 2,80 | Nachtest Deckel-Magnet |
| 11 | USB-Tester UNI-T UT658A (USB-A) | 1 | 8,90 | Test 7 Strom (optional) |
| 12 | Kühlkörper für den Pi, selbstklebend | 1 | ~2 (ungeprüft) | Pi |

**Summe ca. 81 € plus Versand** (gratis erst ab 200 €). Ohne USB-Tester ca. 72 €,
ohne Netzteil weitere 8 € weniger.

## Shop 2: Reichelt.at

| # | Teil | Artikel | € | Wofür |
|---|---|---|---|---|
| 13 | Visaton FRS 8, 4 Ω | VIS FRS 8-4 | 13,73 | Lautsprecher |
| 14 | Drehgeber KY-040 | DEBO ENCODER | 2,17 | Lautstärke |
| 15 | PTC-Sicherung 1,1 A | PTC FUSB110F | 0,90 | 5-V-Pfad Ring |
| 16 | Steckbrett-Set 830 Kontakte | BREADBOARD SET1 | 7,46 | Breadboard |
| 17 | Sortiment LEDs und Widerstände | S93 | 5,03 | Teiler Hauptknopf, SD_MODE |

**Summe ca. 29 € plus Versand** (ungeprüft, vermutlich um 6 €).

## Shop 3: Tinytronics (NL)

| # | Teil | Stk | € | Wofür |
|---|---|---|---|---|
| 18 | PiSugar 3 Plus, 5000 mAh | 2 | 102,00 | Box 1 (Laufzeitmessung) und Box 2 |

Versand nach Österreich 11,50 € (ohne NL-Steuer, eventuell bis 13,92 €), einmal
für beide. **Summe ca. 114–116 €.** Lieferzeit laut Quellen bis 2–4 Wochen.
Den zweiten Akku bei etwa 50 % Ladung kühl lagern (Entscheidung Tobias 24.11.).

## Shop 4: Digikey.at

| # | Teil | € | Wofür |
|---|---|---|---|
| 19 | SparkFun LuMini LED Ring 2″, 40× APA102-2020, **COM-14966** | 20,72 | LED-Ring |

Versand: gratis erst ab 75 € (auf der Seite gesehen, 24.11.), darunter etwa 18 €
(ungeprüft). **Summe ca. 39 €.** Ein Sammeln bis 75 € lohnt sich hier nicht.

## Gesamt

| Shop | ca. € |
|---|---|
| Berrybase.at | 81 + Versand |
| Reichelt.at | 29 + ~6 |
| Tinytronics (2 PiSugar) | 114–116 |
| Digikey.at | 39 |
| **Summe** | **ca. 270 € plus Versand Berrybase** |

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
