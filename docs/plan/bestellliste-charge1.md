# Bestellliste Charge 1 — Pi-Probelauf und Breadboard

Stand 09.11.2026 · Grundlage: Plan Rev. 3.9 (Stückliste 1.1/1.2, PSP 1.2.1)

Zweck: Alles für den Pi-Probelauf (Software auf dem echten Pi, harte
Lautstärke-Grenze über ALSA, Zeit bis zum Ton am Lautsprecher) und den
Breadboard-Aufbau der kritischen Teile. **Nur ein Satz** (Muster), Box 2 kommt
später. Ausnahmen: die Arcade-Knöpfe (kosten fast nichts, reichen für beide
Boxen) und die Box-2-Teile bei DigiKey, die nicht altern und den
DigiKey-Versand sparen (LED-Ring, DAC, Verstärker, Sicherung).

Schon vorhanden: 2× PN5180, 2× ESP32-S3 SuperMini (Bestellung 12.10.).

## Entscheidungen (09.11.)

- Lieferung nach **Österreich**. So wenig Shops und so günstig wie möglich,
  **alles auf einmal** (Muss und Sinnvoll, nichts auf Charge 2 verschoben).
- Gehäusefarben: Box 1 Mivolve PETG Blue (Hellblau), Box 2 Königsblau,
  Ecken schwarzes TPU. Farbprobe als 3D-Ansicht (Artefakt „Tobi Box Farbprobe“).
- Knopffarben: **Rot, Blau, Weiß**. Hauptknopf rot, Vor/Zurück blau oder weiß
  (Entscheidung am Muster).
- LED-Sprache wie in 2.2.2: spielt = grünes Atmen, Pause = bernstein,
  unbekannter Tobie = magenta blinkend, Aufwachen = weißes Lauflicht,
  Akku = Füllstand grün/gelb/rot, am Lader blau.

## Einkaufsliste je Shop

Preise vom 09.11.2026 inkl. MwSt., auf den Shopseiten geprüft (Conrad: aus
Tobias' Warenkorb). Einzige Ausnahme: die Conrad-Versandkosten stammen aus
Shop-Vergleichsseiten, weil conrad.at keine automatischen Abrufe zulässt.

### 1. Conrad.at — ca. 55 €

Der Warenkorb von Tobias ohne die drei Joy-it-Knöpfe (die kommen günstiger von
Berrybase). Pi 3A+ und Visaton FRS 8 gibt es bei Berrybase nicht.

| # | Teil | Conrad-Nr. | Stk | Preis | Summe |
|---|---|---|---|---|---|
| 1 | Raspberry Pi 3 A+ (Header ist beim Original-3A+ vorbestückt) | 1886407-62 | 1 | 31,99 | 31,99 |
| 7 | Visaton FRS 8, **4 Ω**, 8 cm | 300293-62 | 1 | 15,99 | 15,99 |
| 8 | Elko Panasonic 1000 µF / 10 V (2 als Reserve) | 1475911-62 | 3 | 0,90 | 2,70 |
| 4 | Kühlkörper-Set TRU COMPONENTS | 2901841-62 | 1 | 1,49 | 1,49 |
| 17 | Drehregler Joy-it KY-040 | 1695709-62 | 1 | 2,79 | 2,79 |
| | | | | **Summe** | **54,96** |

Versand: 6,99 €, kostenlos ab 69 € (laut Vergleichsportalen).

### 2. Berrybase.at — ca. 74 €

| # | Teil | Stk | Preis | Summe | Link |
|---|---|---|---|---|---|
| 2 | microSD SanDisk **High Endurance** 64 GB + Adapter | 1 | 28,90 | 28,90 | [Link](https://www.berrybase.at/sandisk-high-endurance-microsdxc-uhs-i-u3-speicherkarte-adapter-64gb) |
| 3 | Offizielles Pi-Netzteil **Micro-USB** 5,1 V / 2,5 A, EU (RPIMNT25W) | 1 | 7,90 | 7,90 | [Link](https://www.berrybase.at/offizielles-raspberry-pi-micro-usb-netzteil-5-1v-2-5a-eu-weiss) |
| 5 | Kabel USB-A auf USB-C, USB 2.0 (Daten), 1 m | 1 | 1,60 | 1,60 | [Link](https://www.berrybase.at/blackcotton-usb-a-usb-c-kabel-usb-2.0-schwarz-1-0m) |
| 6 | Adafruit MAX98357A I²S-Verstärker (ADA3006) | 1 | 5,90 | 5,90 | [Link](https://www.berrybase.at/adafruit-i2s-3w-class-d-verstaerker-breakout-max98357a) |
| 10 | Breadboard 830 Kontakte (BB-830P) | 1 | 1,90 | 1,90 | [Link](https://www.berrybase.at/breadboard-mit-830-kontakten) |
| 10 | Dupont-Kabel-Set, je ein 40er-Strang f/f, m/m, f/m, 20 cm | 1 | 4,90 | 4,90 | [Link](https://www.berrybase.at/40pin-jumper-dupont-kabel-set-je-1x-f-f-m-m-f-m-20cm) |
| 11 | NTAG215-Tags, 25 mm, weiß, 10 Stück (Scheiben) | 3 | 4,60 | 13,80 | [Link](https://www.berrybase.at/rfid-nfc-tags-ntag215-25mm-weiss-10-stueck) |
| 13 | Pegelwandler SN74AHCT125N, DIP-14 | 1 | 0,54 | 0,54 | [Link](https://www.berrybase.at/sn74ahct125n-quad-level-shifter-dil-14) |
| 16 | Mini Arcade Button 24 mm (AB24OL-S), **rot** | 2 | 0,90 | 1,80 | [Link](https://www.berrybase.at/detail/019234a4ff067048937fd43f5c724e9e) |
| 16 | Mini Arcade Button 24 mm, **blau** | 4 | 0,90 | 3,60 | wie oben, Farbe wählen |
| 16 | Mini Arcade Button 24 mm, **weiß** | 4 | 0,90 | 3,60 | wie oben, Farbe wählen |
| | | | | **74,44** | |

Versand: DHL 5,95 €, kostenlos ab 200 €.

microSD: 28,90 € ist der Marktpreis. Andere Shops verlangen gerade mehr
(Coolblue 34,90 €, MediaMarkt.at 44,59 €). Die 32-GB-Variante kostet bei
Berrybase 26,90 €, lohnt also nicht.

Knöpfe: Einbauloch 23,5 mm, passt zu den 24 mm der Stückliste. Die Menge
reicht für beide Boxen (2× Haupt rot, Vor/Zurück wahlweise blau oder weiß).

### 3. Tinytronics (NL) — ca. 65 €

| # | Teil | Stk | Preis | Link |
|---|---|---|---|---|
| 9 | **PiSugar 3 Plus**, 5000 mAh (nicht PiSugar 3, nicht 2 Plus, nicht S) | 1 | 51,00 | [Link](https://www.tinytronics.nl/nl/power/powerbanks-en-batterijmodules/pisugar-3-plus-ups-batterij-module-voor-raspberry-pi) |

Versand nach Österreich: 11,50 € ohne MwSt. (ca. 13,80 € mit MwSt.), laut
[Bezorginformatie](https://www.tinytronics.nl/nl/bezorginformatie). Lager:
10+ Stück in Eindhoven. In keinem österreichischen Shop gefunden.

### 4. DigiKey.at — 61,19 €, versandkostenfrei

Teile, die weder Conrad noch Berrybase lieferbar hat. Dazu die Teile für
Box 2, die nicht altern (LED-Ring, DAC, Verstärker). Damit kommt die
Bestellung über 50 € und der Versand (sonst 18 €) entfällt. Die Box-2-Teile
kosten 32,33 €, also nur gut 14 € mehr als der Versand allein.

| # | Teil | Hersteller-Nr. | Stk | Preis | Summe | Lager | Link |
|---|---|---|---|---|---|---|---|
| 12 | SparkFun LuMini LED-Ring 2″, 40× APA102-2020 (1× Box 2) | COM-14966 | 2 | 20,72 | 41,44 | 44 | [Link](https://www.digikey.at/de/products/detail/sparkfun-electronics/14966/9856840) |
| 15 | Adafruit PCM5102 I²S-DAC, Line-Ausgang (1× Box 2) | 6250 | 2 | 5,27 | 10,54 | 448 | [Link](https://www.digikey.at/de/products/detail/adafruit-industries-llc/6250/26249971) |
| 6 | Adafruit MAX98357A I²S-Verstärker (für Box 2) | 3006 | 1 | 6,34 | 6,34 | 1600 | [Link](https://www.digikey.at/de/products/detail/adafruit-industries-llc/3006/6058477) |
| 15 | Adafruit TRRS-Klinkenbuchse 3,5 mm mit **Schaltkontakten** | 5764 | 1 | 1,86 | 1,86 | 325 | [Link](https://www.digikey.at/de/products/detail/adafruit-industries-llc/5764/20370626) |
| 14 | Rückstellbare Sicherung Bourns MF-R110 (1,1 A halten, 30 V, bedrahtet; 1× Box 2) | MF-R110 | 2 | 0,50 | 1,01 | 9932 | [Link](https://www.digikey.at/de/products/detail/bourns-inc/MF-R110/259970) |
| | | | | | **61,19** | | |

Warenwert netto 50,99 €, also auch über der Grenze, falls DigiKey netto
rechnet. Versand nach Österreich: kostenlos ab 50 €, sonst 18 €.
Den Pi 3A+ führt DigiKey nicht mehr (0 Stück, „nicht für neue Designs“).

Zur Buchse: Die zwei Schaltkontakte sind ohne Stecker mit links/rechts
verbunden und offen, wenn ein Stecker steckt. Damit geht „Stecker erkannt“
an GPIO 26 (Punkt 28).

## Summe

| Shop | Ware | Versand |
|---|---|---|
| Conrad.at | 54,96 € | 6,99 € |
| Berrybase.at | 74,44 € | 5,95 € |
| Tinytronics | 51,00 € | ca. 13,80 € |
| DigiKey.at | 61,19 € (davon 32,33 € für Box 2) | 0,00 € |
| **Gesamt** | **241,59 €** | **26,74 €** |

**Alles zusammen: ca. 268 €.** Ohne die Box-2-Teile wären es ca. 254 €
(mit 18 € DigiKey-Versand), die Box-2-Teile kosten also effektiv nur ca. 14 €.

## Hinweise zur Bestellung

- **NTAG215:** Die Berrybase-Tags sind 25-mm-Scheiben, keine Karten im
  Scheckkartenformat. Für Tests und als Tobie zum Bekleben gut.
- Hat dein Mac keinen SD-Schlitz, brauchst du zusätzlich einen
  USB-SD-Kartenleser.
- Die Preise ändern sich. Weicht ein Preis im Warenkorb deutlich ab, Bescheid
  geben, dann suche ich eine Alternative.

## Bewusst noch nicht

- Akku/PiSugar für Box 2 (Akkus altern im Regal, Charge 3).
- Pololu-Ideal-Dioden, USB-C-Buchse, Pogo-Pins, Magnete, Dock-Teile (Charge 2,
  nach Breadboard).
- Gehäusematerial (nach CAD).

## Hinweise

- Für den ersten Probelauf reicht das Netzteil (3); der PiSugar kommt danach
  auf den Pi, zuerst Passung und Start vom Akku prüfen.
- Nach Ankunft: Pi OS Lite (Bookworm, 32 Bit) aufspielen — Anleitung kommt mit
  dem Arbeitspaket „Pi-Installation“ (AP P.1).
