# Bestellliste Charge 1 — Pi-Probelauf und Breadboard

Stand 24.11.2026 · Grundlage: Plan Rev. 3.23 (Stückliste 1.1/1.2, PSP 1.2.1),
Hardware-Prüfung 3.21 · ersetzt die Liste vom 07.11.

Zweck: alles für den Pi-Probelauf und den Breadboard-Aufbau (3.2), damit danach
das CAD starten kann. **Nur ein Satz** (Muster). Lieferung nach Österreich,
möglichst wenig Gesamtkosten.

Schon vorhanden: 2× PN5180, 2× ESP32-S3 SuperMini.

Preise: Recherche vom 24.11. auf den Shopseiten, brutto. Mit „ungeprüft“
markierte Werte bitte im Warenkorb nachsehen. Die Versandkosten von Reichelt,
Berrybase und Digikey stehen erst im Warenkorb fest.

## Wichtig: Der Pi 3 A+ ist zurzeit nicht lieferbar

Berrybase, Reichelt und Welectron sind ausverkauft, Kiwi (NL) erwartet Nachschub
erst am 26.03.2027, Tinytronics führt ihn nicht mehr, Pimoroni nur Vorbestellung
ohne Termin.

**Vorschlag:** Für Probelauf und Breadboard einen **Pi 3 Model B+** nehmen
(Berrybase.at 42,90 €, lieferbar). Gleicher Chip, gleiches SD-Image, gleiche
Micro-USB-Versorgung; der PiSugar 3 Plus ist laut Hersteller für den 3B+
gemacht. Nachteile: größer (85 × 56 statt 65 × 56 mm) und braucht durch LAN
und USB-Hub etwas mehr Strom. Welcher Pi in die fertigen Boxen kommt, ist damit
noch nicht entschieden; das klären wir vor dem CAD.

Nicht sinnvoll: Pi Zero 2 W (für den Zero gibt es keinen PiSugar mit 5000 mAh,
nur 1200 mAh, rund 3 h Laufzeit) und Pi 4 (teurer, mehr Strom).

## Shop 1: Berrybase.at

| # | Teil | Stk | € | Wofür |
|---|---|---|---|---|
| 1 | Raspberry Pi 3 Model B+ | 1 | 42,90 | Probelauf (statt 3 A+) |
| 2 | SanDisk High Endurance microSD 64 GB | 1 | 28,90 | System und Medien |
| 3 | Offizielles Pi-Netzteil 5,1 V / 2,5 A Micro-USB | 1 | 7,90 | Pi ohne PiSugar |
| 4 | Adafruit MAX98357A I²S-Verstärker 3 W | 1 | 5,90 | Ton |
| 5 | SN74AHCT125N (DIP-14) | 1 | 0,54 | Pegelwandler LED-Ring |
| 6 | Mini Arcade Button 24 mm (AB24OL, Farbe wählen) | 3 | 2,70 | Haupt, Vor, Zurück |
| 7 | Elko 1000 µF 25 V | 1 | 0,21 | Puffer am Verstärker |
| 8 | Dupont-Kabelset 40 Stk., 20 cm (DUPK-SET-20) | 1 | 4,90 | Breadboard |
| 9 | NTAG215-Aufkleber, 10 Stk. | 3 | 14,97 | Testkarten |
| 10 | Neodym-Magnet 10 × 3 mm (8 × 3 nicht lieferbar) | 4 | 2,80 | Nachtest Deckel-Magnet |
| 11 | USB-Tester UNI-T UT658A (USB-A) | 1 | 8,90 | Test 7 Strom (optional) |
| 12 | Kühlkörper für den Pi, selbstklebend | 1 | ~2 (ungeprüft) | Pi |

**Summe ca. 123 € plus Versand** (gratis erst ab 200 €). Ohne USB-Tester ca. 114 €.

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

| # | Teil | € | Wofür |
|---|---|---|---|
| 18 | PiSugar 3 Plus, 5000 mAh | 51,00 | Akku, Laufzeitmessung |

Versand nach Österreich 11,50 € (ohne NL-Steuer, eventuell bis 13,92 €).
**Summe ca. 63–65 €.** Lieferzeit laut Quellen bis 2–4 Wochen.

## Shop 4: Digikey.at

| # | Teil | € | Wofür |
|---|---|---|---|
| 19 | SparkFun LuMini LED Ring 2″, 40× APA102-2020, **COM-14966** | 20,72 | LED-Ring |

Versand: unter 50 € etwa 18 € (ungeprüft), ab 50 € gratis. **Summe ca. 39 €.**

**Spartipp:** Gleich den Ring für Box 2 mitnehmen (2 × 20,72 = 41,44 €) und
den zweiten Verstärker MAX98357A sowie zwei 74AHCT125 ebenfalls bei Digikey
kaufen, dann über 50 € und gratis. Kostet etwa 16 € mehr als der eine Ring mit
Versand, aber die Teile für Box 2 sind dann schon da (keine Akkus, die altern).

## Gesamt

| Shop | ca. € |
|---|---|
| Berrybase.at | 123 + Versand |
| Reichelt.at | 29 + ~6 |
| Tinytronics | 63–65 |
| Digikey.at | 39 (mit Spartipp ~55, dafür Teile für Box 2) |
| **Summe** | **ca. 260 € plus Versand Berrybase** |

## Bewusst noch nicht

- **PCM5102A-DAC und Klinkenbuchse mit Schaltkontakten** (Kopfhörerpfad 3.2.6):
  der DAC ist zurzeit nirgends lieferbar gefunden, die Buchse hängt daran.
  Kommt mit Charge 2.
- Akku/PiSugar für Box 2 (Akkus altern im Regal, Charge 3).
- Ideal-Dioden, USB-C-Buchse, Dock-Teile (nach Breadboard und Ladestation Rev. 6).
- Gehäusematerial (nach CAD).

## Hinweise

- Ein **USB-C-auf-USB-A-Datenkabel** (ESP32-S3 an den Pi) ist nicht auf der
  Liste; ein vorhandenes reicht, wenn es Daten überträgt.
- Hat der Mac keinen SD-Schlitz, braucht es einen USB-SD-Kartenleser.
- Der PiSugar kommt erst nach dem ersten Probelauf mit Netzteil auf den Pi.
