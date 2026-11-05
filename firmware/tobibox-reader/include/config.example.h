// Tobi Box – tobibox-reader: Pins und Passwort.
// Kopieren nach include/config.h (gitignored) und dort das eigene Passwort
// eintragen. config.h wird NIE committet. Zeitkonstanten stehen in timing.h.
#pragma once

// ---------------------------------------------------------------
// Verdrahtung ESP32-S3 SuperMini -> PN5180
// (GPIO-Nummern, nicht Pin-Positionen auf der Platine)
// ---------------------------------------------------------------
#define PIN_SCK    12
#define PIN_MISO   13
#define PIN_MOSI   11
#define PIN_NSS    10
#define PIN_BUSY    9
#define PIN_RST     8

// ---------------------------------------------------------------
// Privacy-Passwort für ICODE-SLIX-Tags, 4 Byte.
// Platzhalter. Das echte Passwort nur in config.h eintragen, nie committen.
// Mit dem Platzhalter lassen sich Tonies nicht entsperren (sie melden LOCKED).
// ---------------------------------------------------------------
#define TONIE_PRIVACY_PASSWORD { 0x00, 0x00, 0x00, 0x00 }
