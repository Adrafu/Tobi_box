// Tobi Box – Tonie-Test (Etappe 2)
// Einstellungen. Nur diese Datei anpassen, tonie_test.ino bleibt unverändert.
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
// Voreingestellt ist das Werkspasswort von NXP. Damit lassen sich
// Tonies, die schon auf einer Toniebox standen, nicht entsperren.
// Für Tonies hier das eigene Passwort eintragen.
// ---------------------------------------------------------------
#define TONIE_PRIVACY_PASSWORD { 0x00, 0x00, 0x00, 0x00 }  // eigenes Passwort nur in config.h eintragen, nie committen

// ---------------------------------------------------------------
// Abfrage und Strom
// ---------------------------------------------------------------
// Pause zwischen zwei Abfragen. In der Pause ist das HF-Feld aus.
// 0 = Feld praktisch dauernd an (nur zum Vergleich beim Strommessen).
#define POLL_INTERVAL_MS     300
// So lange darf eine Karte "fehlen", bevor sie als entfernt gilt.
#define REMOVE_DEBOUNCE_MS   700
// Alle x ms eine Statistik ausgeben (Trefferquote für den Reichweitentest).
#define STATS_INTERVAL_MS   5000
// Zeitlimit pro PN5180-Befehl in ms (Bibliothek: 500, ESPuino: 100).
#define COMMAND_TIMEOUT_MS    30

// ---------------------------------------------------------------
// Ausgabe als USB-Tastatur (für Phoniebox, später)
// 0 = nur serielle Ausgabe, 1 = zusätzlich Ziffern + Enter tippen.
// Für 1 in der Arduino-IDE "USB Mode: USB-OTG (TinyUSB)" wählen.
// ---------------------------------------------------------------
#define OUTPUT_AS_KEYBOARD   0
// Code, der für einen erkannten, aber gesperrten Tonie getippt wird.
// In Phoniebox auf den Überraschungs-Ordner legen.
#define UNKNOWN_TONIE_CODE   "9999999999"
// Solange eine Karte liegt, wird ihr Code in diesem Abstand wiederholt,
// damit Phoniebox weiß, dass sie noch da ist (wie beim RC522).
#define KEYBOARD_REPEAT_MS   500
// Code beim Abheben. In Phoniebox auf "Pause" legen.
#define REMOVED_CODE         "0000000000"
