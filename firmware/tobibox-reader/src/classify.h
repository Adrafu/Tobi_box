// Einordnung von Antworten des PN5180 / der Tags (reine Logik, keine Arduino-Typen).
// Die Werte entsprechen ISO15693ErrorCode der PN5180-Bibliothek (reader.cpp prueft
// das mit static_assert).
#pragma once

#include <cstddef>
#include <cstdint>

namespace tobibox {

constexpr int RC_OK = 0;
constexpr int RC_NO_CARD = -1;          // Bibliothek: keine Antwort / Zeitgrenze
constexpr int RC_UNKNOWN_ERROR = 0x0f;  // Bibliothek: readData scheiterte (Uebertragung)

// Antwort auf Inventory / Zufallszahl.
//   Ok      : Tag hat geantwortet.
//   Nothing : keine Antwort, oder das Tag setzt sein Fehlerflag (z. B. "nicht
//             unterstuetzt"): wie in tonie_test als "nichts" behandelt.
//   Error   : Uebertragungs-/Chipfehler (unbekannter Fehler) -> fehler(bad_response).
enum class RespClass : uint8_t { Ok, Nothing, Error };
RespClass classifyResponse(int rc);

// Ergebnis von disablePrivacyMode().
//   Proceed : Passwort angenommen, zweites Inventory folgt.
//   Nothing : Tag ist weg (keine Karte).
//   Error   : Uebertragungsfehler -> fehler(bad_response).
//   Locked  : Tag ist da und lehnt das Passwort ab.
// tag_still_answers: nur bei rc == RC_NO_CARD ausgewertet. Ein SLIX2 antwortet auf
// ein falsches Passwort gar nicht; deshalb entscheidet eine erneute Zufallszahl-
// Abfrage: antwortet das Tag noch, wurde das Passwort abgelehnt (gesperrt), sonst
// ist keine Figur mehr da.
enum class UnlockClass : uint8_t { Proceed, Nothing, Error, Locked };
UnlockClass classifyUnlock(int rc, bool tag_still_answers);

// Zweites Inventory nach erfolgreichem Entsperren. Proceed = Kennung gelesen.
UnlockClass classifyReinventory(int rc);

// Gesundheitsprobe: readRegister() meldet immer true. Der Wert war vorher mit
// dem Platzhalter belegt:
//   unveraendert -> Befehl lief in die Zeitgrenze (pn5180_timeout)
//   0xFFFFFFFF   -> SPI liefert nur Einsen (pn5180_no_response)
constexpr uint32_t HEALTH_SENTINEL = 0xA5A5A5A5UL;
enum class Health : uint8_t { Ok, Timeout, NoResponse };
Health classifyHealth(uint32_t value);

// Pruefung der Inventory-Antwort (Rahmen) vor dem Auslesen der Kennung.
// Die Bibliothek (tueddy) wertet weder die Fehlerbits in RX_STATUS noch die
// Laenge aus und gibt einen gemeinsamen Puffer zurueck; die Firmware prueft
// den Rahmen deshalb selbst (reader.cpp, inventoryChecked()).
//
// RX_STATUS (Datenblatt PN5180, Tabelle 93): Bit 16 Datenintegritaet (falsche
// CRC), Bit 17 Protokollfehler, Bit 18 Kollision. Bits 8..0: Anzahl Bytes.
constexpr uint32_t RX_ERROR_BITS = 0x00070000UL;
constexpr uint32_t RX_LEN_MASK = 0x000001FFUL;
// Antwort: Flags, DSFID, 8 Byte Kennung = 10 Byte. Zaehlt der Chip die CRC mit,
// sind es 12 Byte; dann wird die CRC hier geprueft.
constexpr size_t INV_LEN_NO_CRC = 10;
constexpr size_t INV_LEN_WITH_CRC = 12;
constexpr size_t INV_MAX_LEN = 16;

enum class FrameCheck : uint8_t {
  Ok,         // Rahmen sauber, Kennung in buf[2..9]
  TagError,   // Antwort-Flag "Fehler" des Tags gesetzt (Code in buf[1])
  RxError,    // Fehlerbit in RX_STATUS (CRC, Protokoll, Kollision)
  BadLength,  // Laenge weder 10 noch 12 Byte
  BadCrc,     // CRC16 stimmt nicht (nur bei Laenge 12)
};
// rx_status: Wert des Registers RX_STATUS. buf: gelesene Bytes (Laenge laut
// rx_status), mindestens INV_MAX_LEN gross.
FrameCheck checkInventoryFrame(uint32_t rx_status, const uint8_t* buf);

// ISO 15693 CRC16 (CRC-16/X-25: Polynom 0x8408 gespiegelt, Start 0xFFFF).
// Ueber einen Rahmen inklusive seiner CRC-Bytes ergibt sich ISO15693_CRC_RESIDUE
// (Rest ohne das abschliessende Invertieren).
constexpr uint16_t ISO15693_CRC_RESIDUE = 0xF0B8;
uint16_t crc16Iso15693(const uint8_t* data, size_t len);

// Ein Zyklus, der so lange dauerte, hatte eine Zeitgrenze des Chips.
constexpr uint32_t CYCLE_TIMEOUT_SUSPECT_MS = 450;
inline bool cycleLooksTimedOut(uint32_t elapsed_ms) { return elapsed_ms >= CYCLE_TIMEOUT_SUSPECT_MS; }

}  // namespace tobibox
