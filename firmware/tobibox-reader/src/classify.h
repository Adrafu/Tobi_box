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
constexpr int RC_TAG_ERROR = 0x01;      // Fehlerflag des Tags (fest, siehe frameToRc)

// Antwort auf Inventory / Zufallszahl.
//   Ok      : Tag hat geantwortet.
//   Nothing : keine Antwort, oder das Tag setzt sein Fehlerflag (z. B. "nicht
//             unterstuetzt"): wie in tonie_test als "nichts" behandelt.
//             Ausnahme: Fehlercode 0x0F ("unbekannt") der Tags gilt wie in der
//             Bibliothek als Fehler (frameToRc bildet ihn auf RC_UNKNOWN_ERROR ab).
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
// RX_STATUS (Datenblatt PN5180 Rev. 3.0 vom 07.10.2016, Tabelle 83
// "RX_STATUS_REG"; die Revisionen C3/C4 wurden nicht verglichen): Bit 16
// Datenintegritaet (falsche CRC oder Paritaet), Bit 17 Protokollfehler, Bit 18
// Kollision. Bits 8..0: Anzahl Bytes.
constexpr uint32_t RX_ERROR_BITS = 0x00070000UL;
constexpr uint32_t RX_LEN_MASK = 0x000001FFUL;
// Antwort: Flags, DSFID, 8 Byte Kennung = 10 Byte, wenn der Chip die CRC
// entfernt hat; 12 Byte, wenn er sie mitliefert. Welche Laenge der Chip am
// Geraet wirklich meldet, ist noch nicht gemessen (Befund B1). Beide Laengen
// werden deshalb angenommen, jede andere ist ein Fehler:
//   Laenge 12: Die CRC wird hier selbst geprueft.
//   Laenge 10: Der Chip kann die CRC nur entfernen, wenn die Empfangs-CRC
//     (RX_CRC_ENABLE) aktiv ist; dann hat er sie selbst geprueft und meldet
//     eine falsche CRC als Fehlerbit 16. Auf dieses Bit verlassen wir uns.
//     Ohne aktive Empfangs-CRC kaeme die CRC als Daten, also Laenge 12.
//   Alles andere (zum Beispiel 11): ERR bad_response mit der Laenge im Detail.
constexpr size_t INV_LEN_NO_CRC = 10;
constexpr size_t INV_LEN_WITH_CRC = 12;
constexpr size_t INV_MAX_LEN = 16;

enum class FrameCheck : uint8_t {
  Ok,         // Rahmen sauber, Kennung in buf[2..9]
  TagError,   // echtes Fehlerflag des Tags (Laenge 2 oder 4, CRC stimmt), Code in buf[1]
  BadFlags,   // Fehlerflag im Rahmen mit Laenge 10/12: nur durch Verfaelschung moeglich
  ZeroUid,    // Kennung nur aus Nullen: nie gueltig
  RxError,    // Fehlerbit in RX_STATUS (CRC, Protokoll, Kollision)
  BadLength,  // Laenge weder 10 noch 12 Byte (und kein Fehlerflag-Rahmen)
  BadCrc,     // CRC16 stimmt nicht (nur bei Laenge 12, oder Laenge 4 mit Fehlerflag)
};
// rx_status: Wert des Registers RX_STATUS. buf: gelesene Bytes (Laenge laut
// rx_status), mindestens INV_MAX_LEN gross.
FrameCheck checkInventoryFrame(uint32_t rx_status, const uint8_t* buf);

// Abbildung auf ISO15693ErrorCode-Werte. Eine Kennung kommt nur bei Ok:
//   Ok        -> RC_OK
//   TagError  -> RC_TAG_ERROR (fest, nie der rohe Code; positiv wie bisher, also
//                nach dem Entsperren weiter "gesperrt"). Ausnahme: Code 0x00
//                (kein gueltiger Fehlercode) und 0x0F ("unbekannt", wie in der
//                Bibliothek) -> RC_UNKNOWN_ERROR.
//   alle anderen -> RC_UNKNOWN_ERROR (fehler)
// Nie RC_OK ohne Kennung, nie RC_NO_CARD fuer einen Rahmen.
int frameToRc(FrameCheck check, const uint8_t* buf);

// Text fuer das Feld detail der ERR-Zeile, z. B. "inventory length=11".
// Schreibt nach out (immer nullterminiert, wenn cap > 0).
void describeFrame(FrameCheck check, uint32_t rx_status, const uint8_t* buf, char* out, size_t cap);

// ------------------------------------------------------------ ISO 14443A (NTAG)
// Reine Pruefungen fuer die Antworten der Aktivierung (typea.h).
// Fehlerbits wie bei ISO 15693 (RX_ERROR_BITS), bei Paritaet ohne Empfangs-CRC
// ist Bit 16 die Paritaetspruefung des Chips.
enum class TypeAFrame : uint8_t {
  Ok,
  Nothing,    // nichts empfangen (0 Byte): keine Karte
  RxError,    // Fehlerbit in RX_STATUS (Paritaet/CRC, Protokoll, Kollision)
  BadLength,  // andere Anzahl Bytes als erwartet
};
// expected: erwartete Anzahl Bytes (REQA: 2, Antikollision: 5 mit BCC,
// Select: 1 = SAK, die CRC entfernt der Chip bei aktiver Empfangs-CRC).
TypeAFrame checkTypeAFrame(uint32_t rx_status, size_t expected);

// BCC: XOR der vier Kennungs-Bytes muss dem fuenften Byte gleichen. Gilt je
// Cascade-Ebene (Ebene 1 eines 7-Byte-Tags beginnt mit 0x88 und zaehlt mit).
bool typeABccValid(const uint8_t* five);

// SAK nach dem Select: Bit 3 (0x04) heisst "Kennung noch nicht vollstaendig".
// first: erstes Byte der gelesenen 4 Byte dieser Ebene (0x88 = Cascade Tag).
// Stimmig, wenn genau dann 0x88 vorn steht, wenn Bit 3 gesetzt ist.
bool typeASakConsistent(uint8_t first, uint8_t sak);

// Wie readCardSerial() der Bibliothek: offensichtlich ungueltige Kennungen
// (erstes Byte 0x00, nur 0x00/0xFF, ATQA 0xFFFF) gelten als "keine Karte".
bool typeAUidPlausible(const uint8_t* uid, size_t len);

// ISO 15693 CRC16 (CRC-16/X-25: Polynom 0x8408 gespiegelt, Start 0xFFFF).
// Ueber einen Rahmen inklusive seiner CRC-Bytes ergibt sich ISO15693_CRC_RESIDUE
// (Rest ohne das abschliessende Invertieren).
constexpr uint16_t ISO15693_CRC_RESIDUE = 0xF0B8;
uint16_t crc16Iso15693(const uint8_t* data, size_t len);

// Ein Zyklus, der so lange dauerte, hatte eine Zeitgrenze des Chips.
constexpr uint32_t CYCLE_TIMEOUT_SUSPECT_MS = 450;
inline bool cycleLooksTimedOut(uint32_t elapsed_ms) { return elapsed_ms >= CYCLE_TIMEOUT_SUSPECT_MS; }

}  // namespace tobibox
