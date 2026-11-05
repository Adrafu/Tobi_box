// Ein Abfragezyklus 14443A / 15693 / Entsperren nach Vorbild
// firmware/tonie_test/tonie_test.ino.
#include "reader.h"

#include <string.h>

#include "classify.h"
#include "timing.h"

namespace tobibox {

static_assert(RC_OK == ISO15693_EC_OK && RC_NO_CARD == EC_NO_CARD &&
                  RC_UNKNOWN_ERROR == ISO15693_EC_UNKNOWN_ERROR,
              "classify.h passt nicht zu ISO15693ErrorCode");

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
  if (v[1] == 0xFF || v[1] == 0x00) return false;
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
  if (n <= 0) {
    // Die Bibliothek meldet Zeitgrenzen (setRF_on, BUSY) nicht getrennt von
    // "keine Karte"; ein so langer Zyklus war aber keine leere Antwort.
    if (cycleLooksTimedOut(millis() - cycleStart_))
      return Reading::failure(CycleError::Pn5180Timeout, "iso14443a read exceeded time limit");
    return Reading::nothing();
  }
  if (n == 4 || n == 7 || n == 10) return Reading::tag(UidType::Ntag, buf, static_cast<size_t>(n));
  snprintf(errDetail, sizeof errDetail, "iso14443a uid length %d", n);
  return Reading::failure(CycleError::UidInvalid, errDetail);
}

Reading Reader::readIso15693() {
  uint8_t uid[8] = {0};
  nfc15693_.reset();
  if (!nfc15693_.setupRF())
    return Reading::failure(CycleError::Pn5180Timeout, "rf field did not start");

  nfc15693_.clearIRQStatus(0xffffffff);  // alte IRQ-Flags wuerden Phantomkarten melden
  ISO15693ErrorCode rc = nfc15693_.getInventory(uid);
  if (rc == ISO15693_EC_OK) {
    uint8_t msb[8];
    for (uint8_t i = 0; i < 8; i++) msb[i] = uid[7 - i];  // ISO 15693: LSB zuerst -> umdrehen
    return Reading::tag(UidType::Iso15693, msb, 8);
  }
  if (classifyResponse(rc) == RespClass::Error)
    return Reading::failure(CycleError::BadResponse, "inventory transfer error");

  // Keine Antwort auf Inventory: liegt ein Tag im Privacy-Modus auf?
  uint8_t rnd[2] = {0};
  rc = nfc15693_.getRandomNumber(rnd);
  switch (classifyResponse(rc)) {
    case RespClass::Nothing: return Reading::nothing();
    case RespClass::Error:
      return Reading::failure(CycleError::BadResponse, "random number transfer error");
    case RespClass::Ok: break;
  }

  rc = nfc15693_.disablePrivacyMode(privacyPassword);
  nfc15693_.clearIRQStatus(0xffffffff);
  // Ein SLIX2 schweigt bei falschem Passwort: erst eine erneute Zufallszahl
  // entscheidet, ob "keine Karte" heisst "Tag weg" oder "Passwort abgelehnt".
  bool stillAnswers = false;
  if (rc == EC_NO_CARD) {
    uint8_t rnd2[2] = {0};
    stillAnswers = nfc15693_.getRandomNumber(rnd2) == ISO15693_EC_OK;
  }
  switch (classifyUnlock(rc, stillAnswers)) {
    case UnlockClass::Nothing: return Reading::nothing();
    case UnlockClass::Error:
      return Reading::failure(CycleError::BadResponse, "unlock transfer error");
    case UnlockClass::Locked: return Reading::locked();
    case UnlockClass::Proceed: break;
  }

  rc = nfc15693_.getInventory(uid);
  switch (classifyReinventory(rc)) {
    case UnlockClass::Proceed: {
      uint8_t msb[8];
      for (uint8_t i = 0; i < 8; i++) msb[i] = uid[7 - i];
      return Reading::tag(UidType::Iso15693, msb, 8);
    }
    case UnlockClass::Nothing: return Reading::nothing();
    case UnlockClass::Error:
      return Reading::failure(CycleError::BadResponse, "inventory transfer error");
    case UnlockClass::Locked: break;
  }
  return Reading::locked();  // Figur erkannt, Kennung unbekannt
}

Reading Reader::pollProtocols() {
  // Zuletzt gelesenes Protokoll zuerst (spart Zeit, Zeitbudget im Design).
  Reading r;
  if (lastWasNtag_) {
    r = readIso14443();
  } else {
    r = readIso15693();
  }
  if (r.kind != Reading::Kind::Nothing) return r;
  // Hat schon das erste Protokoll an eine Zeitgrenze gestossen, kein zweites
  // anfangen (der Zyklus bliebe sonst weit ueber der Hoechstdauer des Vertrags).
  if (cycleLooksTimedOut(millis() - cycleStart_))
    return Reading::failure(CycleError::Pn5180Timeout, "first protocol exceeded time limit");
  return lastWasNtag_ ? readIso15693() : readIso14443();
}

Reading Reader::poll() {
  cycleStart_ = millis();
  Reading r = pollProtocols();
  if (r.kind == Reading::Kind::Uid) lastWasNtag_ = (r.type == UidType::Ntag);

  // Gesundheitsprobe: Bei "nichts" pruefen, ob der Chip ueberhaupt antwortet.
  // readRegister() meldet immer true; deshalb ein Platzhalter vorab: bleibt er
  // stehen, lief der Befehl in die Zeitgrenze, kommen nur Einsen, ist der SPI tot.
  if (r.kind == Reading::Kind::Nothing) {
    uint32_t irq = HEALTH_SENTINEL;
    nfc15693_.readRegister(IRQ_STATUS, &irq);
    switch (classifyHealth(irq)) {
      case Health::Timeout:
        r = Reading::failure(CycleError::Pn5180Timeout, "busy timeout reading irq status");
        break;
      case Health::NoResponse:
        r = Reading::failure(CycleError::Pn5180NoResponse, "spi returned 0xFFFFFFFF");
        break;
      case Health::Ok: break;
    }
  }

  // HF-Feld aus bis zum naechsten Zyklus. Nach einem Chip-Fehler entfaellt das:
  // setRF_off() wartete bis zu 500 ms weiter, der naechste Zyklus beginnt ohnehin
  // mit reset(). Scheitert es sonst, ist es ein Timeout.
  const bool chipFailed = r.kind == Reading::Kind::Error &&
                          (r.error == CycleError::Pn5180Timeout ||
                           r.error == CycleError::Pn5180NoResponse);
  if (!chipFailed && !nfc15693_.setRF_off() && r.kind == Reading::Kind::Nothing) {
    r = Reading::failure(CycleError::Pn5180Timeout, "setRF_off failed");
  }
  return r;
}

}  // namespace tobibox
