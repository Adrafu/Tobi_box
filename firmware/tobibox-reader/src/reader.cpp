// Ein Abfragezyklus 14443A / 15693 / Entsperren nach Vorbild
// firmware/tonie_test/tonie_test.ino.
#include "reader.h"

#include <string.h>

#include "timing.h"

namespace tobibox {

namespace {
const uint8_t privacyPassword[4] = TONIE_PRIVACY_PASSWORD;
char errDetail[40];
}  // namespace

Reader::Reader()
    : nfc14443_(PIN_NSS, PIN_BUSY, PIN_RST), nfc15693_(PIN_NSS, PIN_BUSY, PIN_RST) {}

void Reader::beginBus() {
  nfc14443_.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_NSS);
  nfc15693_.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_NSS);
  nfc14443_.commandTimeout = PN5180_CMD_TIMEOUT_MS;
  nfc15693_.commandTimeout = PN5180_CMD_TIMEOUT_MS;
}

bool Reader::probe(char* version, size_t cap) {
  snprintf(version, cap, "unknown");
  nfc14443_.reset();
  uint8_t v[2] = {0xFF, 0xFF};
  nfc14443_.readEEprom(PRODUCT_VERSION, v, 2);
  if (v[1] == 0xFF) return false;
  uint8_t fw[2] = {0xFF, 0xFF};
  if (nfc14443_.readEEprom(FIRMWARE_VERSION, fw, 2) && fw[1] != 0xFF)
    snprintf(version, cap, "%u.%u", fw[1], fw[0]);
  return true;
}

Reading Reader::readIso14443() {
  nfc14443_.reset();
  // Kein setupRF(): readCardSerial() laedt die Konfiguration und schaltet das
  // Feld selbst ein (ein zweites RF_ON wartet fest 500 ms, siehe tonie_test).
  uint8_t buf[10] = {0};
  int8_t n = nfc14443_.readCardSerial(buf);
  if (n <= 0) return Reading::nothing();
  if (n == 4 || n == 7 || n == 10) return Reading::tag(UidType::Ntag, buf, static_cast<size_t>(n));
  snprintf(errDetail, sizeof errDetail, "iso14443a uid length %d", n);
  return Reading::failure(CycleError::UidInvalid, errDetail);
}

Reading Reader::readIso15693() {
  uint8_t uid[8] = {0};
  nfc15693_.reset();
  nfc15693_.setupRF();

  nfc15693_.clearIRQStatus(0xffffffff);  // alte IRQ-Flags wuerden Phantomkarten melden
  if (nfc15693_.getInventory(uid) == ISO15693_EC_OK) {
    uint8_t msb[8];
    for (uint8_t i = 0; i < 8; i++) msb[i] = uid[7 - i];  // ISO 15693: LSB zuerst -> umdrehen
    return Reading::tag(UidType::Iso15693, msb, 8);
  }

  // Keine Antwort auf Inventory: liegt ein Tag im Privacy-Modus auf?
  uint8_t rnd[2] = {0};
  ISO15693ErrorCode rc = nfc15693_.getRandomNumber(rnd);
  if (rc == EC_NO_CARD) return Reading::nothing();
  if (rc != ISO15693_EC_OK)
    return Reading::failure(CycleError::BadResponse, "random number request failed");

  rc = nfc15693_.disablePrivacyMode(privacyPassword);
  nfc15693_.clearIRQStatus(0xffffffff);
  if (rc == ISO15693_EC_OK && nfc15693_.getInventory(uid) == ISO15693_EC_OK) {
    uint8_t msb[8];
    for (uint8_t i = 0; i < 8; i++) msb[i] = uid[7 - i];
    return Reading::tag(UidType::Iso15693, msb, 8);
  }
  return Reading::locked();  // Figur erkannt, Kennung unbekannt
}

Reading Reader::pollProtocols() {
  // Zuletzt gelesenes Protokoll zuerst (spart Zeit, Zeitbudget im Design).
  if (lastWasNtag_) {
    Reading r = readIso14443();
    if (r.kind != Reading::Kind::Nothing) return r;
    return readIso15693();
  }
  Reading r = readIso15693();
  if (r.kind != Reading::Kind::Nothing) return r;
  return readIso14443();
}

Reading Reader::poll() {
  Reading r = pollProtocols();
  if (r.kind == Reading::Kind::Uid) lastWasNtag_ = (r.type == UidType::Ntag);

  // Gesundheitsprobe: Bei "nichts" pruefen, ob der Chip ueberhaupt antwortet.
  // Sonst waere ein toter PN5180 von einem leeren Feld nicht zu unterscheiden.
  if (r.kind == Reading::Kind::Nothing) {
    uint32_t irq = 0;
    if (!nfc15693_.readRegister(IRQ_STATUS, &irq)) {
      r = Reading::failure(CycleError::Pn5180Timeout, "busy timeout reading irq status");
    } else if (irq == 0xFFFFFFFFUL) {
      r = Reading::failure(CycleError::Pn5180NoResponse, "spi returned 0xFFFFFFFF");
    }
  }

  // HF-Feld aus bis zum naechsten Zyklus. Scheitert das, ist es ein Timeout.
  if (!nfc15693_.setRF_off() && r.kind != Reading::Kind::Error && r.kind != Reading::Kind::Uid &&
      r.kind != Reading::Kind::Locked) {
    r = Reading::failure(CycleError::Pn5180Timeout, "setRF_off failed");
  }
  return r;
}

}  // namespace tobibox
