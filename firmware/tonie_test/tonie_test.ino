#include <dummy.h>

// Tobi Box – Tonie-Test (Etappe 2)
//
// Liest abwechselnd NTAG-Karten (ISO 14443A) und Tonies/ICODE-Tags
// (ISO 15693) mit einem PN5180 und meldet jede Figur über USB.
// Ablauf pro Abfrage, angelehnt an ESPuino:
//   1. ISO 14443A: Karte vorhanden?            -> NTAG
//   2. ISO 15693: Inventory                    -> Tag ohne Privacy-Modus
//   3. Keine Antwort: Zufallszahl abfragen     -> Tag im Privacy-Modus vorhanden
//   4. Privacy-Modus mit Passwort aufheben, erneut Inventory
//        klappt  -> Kennung (Tonie entsperrt)
//        klappt nicht -> "Tonie erkannt, gesperrt"
// Zwischen den Abfragen ist das HF-Feld aus (Strom sparen).
// Als USB-Tastatur: Code beim Auflegen, Wiederholung alle KEYBOARD_REPEAT_MS,
// REMOVED_CODE beim Abheben. So erkennt Phoniebox auch das Abnehmen.
//
// Bibliothek: https://github.com/tueddy/PN5180-Library (LGPL-2.1)
// Board: ESP32S3 Dev Module, "USB CDC On Boot: Enabled".
// Einstellungen in config.h.

#include <SPI.h>
#include <PN5180.h>
#include <PN5180ISO14443.h>
#include <PN5180ISO15693.h>
#include "config.h"

#if OUTPUT_AS_KEYBOARD
#include "USB.h"
#include "USBHIDKeyboard.h"
USBHIDKeyboard Keyboard;
#endif

PN5180ISO14443 nfc14443(PIN_NSS, PIN_BUSY, PIN_RST);
PN5180ISO15693 nfc15693(PIN_NSS, PIN_BUSY, PIN_RST);

static const uint8_t privacyPassword[4] = TONIE_PRIVACY_PASSWORD;

enum class Kind : uint8_t {
  None,            // nichts gefunden
  Ntag,            // ISO 14443A, z. B. NTAG215-Karte
  Vicinity,        // ISO 15693 ohne Privacy-Modus
  VicinityUnlocked,// ISO 15693, Privacy-Modus mit Passwort aufgehoben
  VicinityLocked   // ISO 15693 im Privacy-Modus, Passwort passt nicht
};

struct Reading {
  Kind kind = Kind::None;
  uint8_t uid[10] = {0};   // immer MSB zuerst, so wie Tonie-IDs geschrieben werden
  uint8_t len = 0;
};

// Zustand für Auflegen/Entfernen
static Reading current;
static bool present = false;
static uint32_t lastSeenMs = 0;
static uint32_t lastKeySendMs = 0;

// Statistik für Reichweiten- und Stromtest
static uint32_t statAttempts = 0, statHits = 0, statFieldMs = 0, statStartMs = 0;

// ---------------------------------------------------------------- Hilfen

static const char* kindName(Kind k) {
  switch (k) {
    case Kind::Ntag:             return "NTAG / ISO 14443A";
    case Kind::Vicinity:         return "ISO 15693, offen";
    case Kind::VicinityUnlocked: return "ISO 15693, entsperrt";
    case Kind::VicinityLocked:   return "ISO 15693, gesperrt";
    default:                     return "-";
  }
}

static bool isTonie(const Reading& r) {
  // Tonie-Kennungen beginnen mit E0 04 03 (NXP SLIX-L)
  return r.len == 8 && r.uid[0] == 0xE0 && r.uid[1] == 0x04 && r.uid[2] == 0x03;
}

static void printHex(const uint8_t* b, uint8_t n) {
  for (uint8_t i = 0; i < n; i++) {
    if (b[i] < 0x10) Serial.print('0');
    Serial.print(b[i], HEX);
    if (i + 1 < n) Serial.print(' ');
  }
}

// Kennung als Ziffernfolge. Ziffern sind auf jedem Tastaturlayout gleich,
// Buchstaben (Hex) würden auf deutschem Layout teils vertauscht ankommen.
static String decimalCode(const Reading& r) {
  if (r.kind == Kind::VicinityLocked) return String(UNKNOWN_TONIE_CODE);
  uint64_t v = 0;
  for (uint8_t i = 0; i < r.len && i < 8; i++) v = (v << 8) | r.uid[i];
  char buf[24];
  snprintf(buf, sizeof(buf), "%llu", (unsigned long long)v);
  return String(buf);
}

static bool sameCard(const Reading& a, const Reading& b) {
  // Gleiche Kennung = gleiche Figur, auch wenn sie einmal "entsperrt" und
  // danach "offen" gemeldet wird. Gesperrte Tonies haben keine Kennung.
  if (a.len == 0 || b.len == 0) return a.kind == b.kind && a.len == b.len;
  if (a.len != b.len) return false;
  return memcmp(a.uid, b.uid, a.len) == 0;
}

// ---------------------------------------------------------------- Lesen

static Reading readIso14443() {
  Reading r;
  nfc14443.reset();
  // Kein setupRF() hier: readCardSerial() lädt die Konfiguration und schaltet
  // das Feld selbst ein. Ein zweites RF_ON bei schon aktivem Feld wartet in der
  // Bibliothek fest 500 ms auf eine Meldung, die nie kommt.
  uint8_t buf[10] = {0};
  int8_t n = nfc14443.readCardSerial(buf);
  if (n >= 4 && n <= 10) {
    r.kind = Kind::Ntag;
    r.len = n;
    memcpy(r.uid, buf, n);   // ISO 14443A liefert die UID bereits MSB zuerst
  }
  return r;
}

static void storeVicinityUid(Reading& r, const uint8_t* uidLsbFirst) {
  // ISO 15693 überträgt die UID LSB zuerst -> für die Anzeige umdrehen
  r.len = 8;
  for (uint8_t i = 0; i < 8; i++) r.uid[i] = uidLsbFirst[7 - i];
}

static Reading readIso15693() {
  Reading r;
  uint8_t uid[8] = {0};

  nfc15693.reset();
  nfc15693.setupRF();

  nfc15693.clearIRQStatus(0xffffffff);   // alte IRQ-Flags würden Phantomkarten melden
  if (nfc15693.getInventory(uid) == ISO15693_EC_OK) {
    r.kind = Kind::Vicinity;
    storeVicinityUid(r, uid);
    return r;
  }

  // Keine Antwort auf Inventory: Liegt ein Tag im Privacy-Modus auf?
  // Im Privacy-Modus antwortet der Chip nur noch auf die Zufallszahl-Abfrage.
  uint8_t rnd[2] = {0};
  if (nfc15693.getRandomNumber(rnd) != ISO15693_EC_OK) {
    return r;   // nichts da
  }

  // Ja: mit Passwort entsperren und erneut lesen
  ISO15693ErrorCode rc = nfc15693.disablePrivacyMode(privacyPassword);
  nfc15693.clearIRQStatus(0xffffffff);
  if (rc == ISO15693_EC_OK && nfc15693.getInventory(uid) == ISO15693_EC_OK) {
    r.kind = Kind::VicinityUnlocked;
    storeVicinityUid(r, uid);
  } else {
    r.kind = Kind::VicinityLocked;   // Figur erkannt, Kennung unbekannt
  }
  return r;
}

static Reading pollOnce() {
  // Liegt schon etwas auf, zuerst das zuletzt erkannte Protokoll prüfen
  if (present && current.kind == Kind::Ntag) {
    Reading r = readIso14443();
    if (r.kind != Kind::None) return r;
    return readIso15693();
  }
  Reading r = readIso15693();
  if (r.kind != Kind::None) return r;
  return readIso14443();
}

// ---------------------------------------------------------------- Ausgabe

static void typeCode(const String& code) {
#if OUTPUT_AS_KEYBOARD
  Keyboard.print(code);
  Keyboard.write(KEY_RETURN);
#else
  (void)code;
#endif
  lastKeySendMs = millis();
}

static void announce(const Reading& r, uint32_t ms) {
  Serial.print(F("AUFGELEGT  "));
  Serial.print(kindName(r.kind));
  if (r.len) {
    Serial.print(F("  UID "));
    printHex(r.uid, r.len);
  }
  if (isTonie(r)) Serial.print(F("  (Tonie)"));
  if (r.kind == Kind::VicinityLocked) Serial.print(F("  -> Tonie erkannt, Passwort passt nicht"));
  Serial.print(F("  Code "));
  Serial.print(decimalCode(r));
  Serial.print(F("  Lesezeit "));
  Serial.print(ms);
  Serial.println(F(" ms"));
  typeCode(decimalCode(r));
}

static void printStats() {
  uint32_t span = millis() - statStartMs;
  if (statAttempts == 0 || span == 0) return;
  Serial.print(F("STATISTIK  Abfragen "));
  Serial.print(statAttempts);
  Serial.print(F("  Treffer "));
  Serial.print(statHits);
  Serial.print(F(" ("));
  Serial.print(100.0f * statHits / statAttempts, 0);
  Serial.print(F(" %)  Feld an "));
  Serial.print(100.0f * statFieldMs / span, 1);
  Serial.println(F(" % der Zeit"));
  statAttempts = statHits = statFieldMs = 0;
  statStartMs = millis();
}

// ---------------------------------------------------------------- Setup/Loop

void setup() {
  Serial.begin(115200);
#if OUTPUT_AS_KEYBOARD
  Keyboard.begin();
  USB.begin();
#endif
  delay(1500);   // Zeit, um den seriellen Monitor zu öffnen
  Serial.println(F("\nTobi Box – Tonie-Test"));

  nfc14443.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_NSS);
  nfc15693.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_NSS);
  nfc14443.commandTimeout = COMMAND_TIMEOUT_MS;
  nfc15693.commandTimeout = COMMAND_TIMEOUT_MS;
  nfc14443.reset();

  uint8_t v[2] = {0};
  nfc14443.readEEprom(PRODUCT_VERSION, v, 2);
  if (v[1] == 0xFF) {
    Serial.println(F("FEHLER: PN5180 antwortet nicht. Verdrahtung und 5 V prüfen."));
    while (true) delay(1000);
  }
  Serial.print(F("PN5180 Produkt "));  Serial.print(v[1]); Serial.print('.'); Serial.println(v[0]);
  nfc14443.readEEprom(FIRMWARE_VERSION, v, 2);
  Serial.print(F("PN5180 Firmware ")); Serial.print(v[1]); Serial.print('.'); Serial.print(v[0]);
  Serial.println(v[1] >= 4 ? F("  (Stromsparmodus LPCD möglich)") : F("  (LPCD erst ab Firmware 4.0)"));
  Serial.print(F("Abfrage alle ")); Serial.print(POLL_INTERVAL_MS); Serial.println(F(" ms. Karte oder Figur auflegen."));

  statStartMs = millis();
}

void loop() {
  uint32_t t0 = millis();
  Reading r = pollOnce();
  uint32_t dt = millis() - t0;

  nfc15693.setRF_off();   // Feld aus bis zur nächsten Abfrage
  statAttempts++;
  statFieldMs += dt;

  if (r.kind != Kind::None) {
    statHits++;
    lastSeenMs = millis();
    if (!present || !sameCard(r, current)) {
      current = r;
      present = true;
      announce(r, dt);
    } else if (millis() - lastKeySendMs >= KEYBOARD_REPEAT_MS) {
      typeCode(decimalCode(current));   // "liegt noch" an Phoniebox melden
    }
  } else if (present && millis() - lastSeenMs > REMOVE_DEBOUNCE_MS) {
    present = false;
    Serial.print(F("ENTFERNT   "));
    Serial.println(kindName(current.kind));
    typeCode(String(REMOVED_CODE));
    current = Reading();
  }

  if (millis() - statStartMs >= STATS_INTERVAL_MS) printStats();
  if (POLL_INTERVAL_MS > 0) delay(POLL_INTERVAL_MS);
}
