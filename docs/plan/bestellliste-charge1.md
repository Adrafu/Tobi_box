# Bestellliste Charge 1 — Pi-Probelauf und Breadboard

Stand 07.11.2026 · Grundlage: Plan Rev. 3.9 (Stückliste 1.1/1.2, PSP 1.2.1)

Zweck: Alles für den Pi-Probelauf (Software auf dem echten Pi, harte
Lautstärke-Grenze über ALSA, Zeit bis zum Ton am Lautsprecher) und den
Breadboard-Aufbau der kritischen Teile. **Nur ein Satz** (Muster), Box 2 kommt
später. Preise sind Richtwerte aus der Stückliste, vor dem Bestellen prüfen.

Schon vorhanden: 2× PN5180, 2× ESP32-S3 SuperMini (Bestellung 12.10.).

## Muss

| # | Teil | Stk | ca. € | Wofür |
|---|---|---|---|---|
| 1 | Raspberry Pi 3 Model A+ (Header vorbestückt) | 1 | 31 | Rechner der Box, Pi-Probelauf |
| 2 | microSD 64 GB, A1, **High Endurance** | 1 | 12 | System + Medien |
| 3 | Netzteil 5 V / 2,5 A mit **Micro-USB** (offizielles Pi-Netzteil) | 1 | 10 | Pi ohne PiSugar betreiben |
| 4 | Kühlkörper, selbstklebend | 1 | 2 | Pi |
| 5 | USB-Kabel **USB-C auf USB-A**, kurz (Daten, kein reines Ladekabel) | 1 | 3 | ESP32-S3 an den Pi (der 3A+ hat nur USB-A) |
| 6 | MAX98357A I²S-Verstärker, 3 W mono | 1 | 6 | Ton am Pi, ALSA-Grenze, Messung |
| 7 | Visaton FRS 8, 4 Ω, 80 mm | 1 | 12 | Lautsprecher für Probelauf und Klangprobe |
| 8 | Elko 1000 µF, ≥ 10 V | 1 | 1 | Puffer am Verstärker |
| 9 | PiSugar 3 Plus, 5000 mAh | 1 | 50 | Passung, Akkustart, Laufzeitmessung (3.1.1, 3.1.3) |
| 10 | Breadboard + Dupont-Kabel (m/m, m/w), falls nicht vorhanden | 1 Satz | 10 | Breadboard-Aufbau |
| 11 | NTAG215-Karten | 20–50 | 10–20 | Karten zum Testen und für die Kinder |

**Summe Muss: ca. 150–160 €**

## Sinnvoll (wenn ohnehin bestellt wird)

| # | Teil | Stk | ca. € | Wofür |
|---|---|---|---|---|
| 12 | SparkFun LuMini LED-Ring 2″, 40× APA102-2020 | 1 | 17 | LED-Ring am Breadboard (PSP 1.2.1) |
| 13 | Pegelwandler 74AHCT125 | 1 | 1 | APA102 an 3,3-V-GPIOs |
| 14 | Rückstellbare Sicherung (PTC) 1,1 A | 1 | 1 | 5-V-Pfad des Rings |
| 15 | PCM5102A-DAC + 3,5-mm-Buchse mit Schaltkontakt | 1 Satz | 7 | Kopfhörerpfad prüfen (3.2.6) |
| 16 | Arcade-Button 24 mm | 3 | 8 | Haupt, Vor, Zurück am Breadboard |
| 17 | Rotary Encoder KY-040 | 1 | 5 | Lautstärke am Breadboard |

**Summe sinnvoll: ca. 40 €**

## Bewusst noch nicht

- Akku/PiSugar für Box 2 (Akkus altern im Regal, Charge 3).
- Pololu-Ideal-Dioden, USB-C-Buchse, Pogo-Pins, Magnete, Dock-Teile (Charge 2,
  nach Breadboard).
- Gehäusematerial (nach CAD).

## Hinweise

- Hat dein Mac keinen SD-Schlitz, brauchst du zusätzlich einen USB-SD-Kartenleser.
- Für den ersten Probelauf reicht das Netzteil (3); der PiSugar kommt danach
  auf den Pi, zuerst Passung und Start vom Akku prüfen.
- Nach Ankunft: Pi OS Lite (Bookworm, 32 Bit) aufspielen — Anleitung kommt mit
  dem Arbeitspaket „Pi-Installation“ (AP P.1).
