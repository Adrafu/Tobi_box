// Ein Abfragezyklus 14443A / 15693 / Entsperren nach Vorbild
// firmware/tonie_test/tonie_test.ino.
#include "reader.h"

#include <string.h>

#include "classify.h"
#include "timing.h"
#include "typea.h"

namespace tobibox {

static_assert(RC_OK == ISO15693_EC_OK && RC_NO_CARD == EC_NO_CARD &&
                  RC_UNKNOWN_ERROR == ISO15693_EC_UNKNOWN_ERROR,
              "classify.h passt nicht zu ISO15693ErrorCode");

namespace {
const uint8_t privacyPassword[4] = TONIE_PRIVACY_PASSWORD;
char invDetail[48];   // Grund der letzten Inventory-Antwort (describeFrame)
char ntagDetail[48];  // Grund der letzten verworfenen NTAG-Antwort

// Chip-Operationen fuer typea.h, jede eine Zeile auf die Bibliothek.
class Chip14443 {
 public:
  explicit Chip14443(PN5180ISO14443& n) : n_(n) {}
  bool loadRfConfig() { return n_.loadRFConfig(0x00, 0x80); }
  void rfOn() { n_.setRF_on(); }  // Ergebnis ignoriert, wie in activateTypeA()
  void delayMs(uint32_t ms) { delay(ms); }
  uint32_t nowMs() { return millis(); }
  bool cryptoOff() { return n_.writeRegisterWithAndMask(SYSTEM_CONFIG, 0xFFFFFFBF); }
  bool crcRx(bool on) {
    return on ? n_.writeRegisterWithOrMask(CRC_RX_CONFIG, 0x01)
              : n_.writeRegisterWithAndMask(CRC_RX_CONFIG, 0xFFFFFFFE);
  }
  bool crcTx(bool on) {
    return on ? n_.writeRegisterWithOrMask(CRC_TX_CONFIG, 0x01)
              : n_.writeRegisterWithAndMask(CRC_TX_CONFIG, 0xFFFFFFFE);
  }
  bool idle() { return n_.writeRegisterWithAndMask(SYSTEM_CONFIG, 0xFFFFFFF8); }
  bool transceive() { return n_.writeRegisterWithOrMask(SYSTEM_CONFIG, 0x00000003); }
  bool inWaitTransmit() { return n_.getTransceiveState() == PN5180_TS_WaitTransmit; }
  bool clearIrq() { return n_.clearIRQStatus(0xffffffff); }
  bool send(const uint8_t* d, int n, uint8_t bits) { return n_.sendData(d, n, bits); }
  uint32_t rxStatus() {
    uint32_t v = 0;
    n_.readRegister(RX_STATUS, &v);
    return v;
  }
  bool read(int n, uint8_t* buf) { return n_.readData(n, buf); }

 private:
  PN5180ISO14443& n_;
};
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

// Inventory (ein Slot, Flags 0x26) mit eigener Pruefung der Antwort. Die
// Bibliothek-Funktion getInventory() wertet RX_STATUS nur fuer die Laenge aus:
// Fehlerbits (CRC, Protokoll, Kollision) werden uebergangen, die Laenge wird
// nicht geprueft, und ein zu kurzer Rahmen liefert alte Bytes aus einem
// gemeinsamen Puffer. Hier: eigener Puffer, Fehlerbits, Laenge und CRC
// (classify.cpp, checkInventoryFrame).
// Rueckgabe wie ISO15693ErrorCode; Verwerfen als RC_UNKNOWN_ERROR (-> fehler).
// Nur bei RC_OK steht eine Kennung in uid (8 Byte, LSB zuerst, nie nur Nullen).
//
// Wie die Bibliothek (PN5180ISO15693.cpp, getInventory/issueISO15693Command):
// scheitert sendData(), ist das "nichts" (RC_NO_CARD), und nach readData() wird
// RX_SOF_DET noch einmal geprueft; fehlt es, ist der Rahmen "nichts".
int Reader::inventoryChecked(uint8_t* uid) {
  static const uint8_t inventory[] = {0x26, 0x01, 0x00};
  memset(uid, 0, 8);
  errDetail_ = "inventory transfer error";
  if (!nfc15693_.sendData(inventory, sizeof inventory)) return RC_NO_CARD;
  delay(10);
  uint32_t irq = nfc15693_.getIRQStatus();
  if (!(irq & RX_SOF_DET_IRQ_STAT)) return RC_NO_CARD;
  const uint32_t waitStart = millis();
  while (!(irq & RX_IRQ_STAT)) {
    irq = nfc15693_.getIRQStatus();
    delay(1);
    if (millis() - waitStart > nfc15693_.commandTimeout) return RC_NO_CARD;
  }
  uint32_t rxStatus = 0;
  nfc15693_.readRegister(RX_STATUS, &rxStatus);
  const size_t len = rxStatus & RX_LEN_MASK;
  uint8_t buf[INV_MAX_LEN] = {0};  // frisch: keine alten Bytes
  if (len > INV_MAX_LEN) {
    nfc15693_.clearIRQStatus(0xffffffff);
    describeFrame(FrameCheck::BadLength, rxStatus, buf, invDetail, sizeof invDetail);
    errDetail_ = invDetail;
    return RC_UNKNOWN_ERROR;
  }
  if (len > 0 && !nfc15693_.readData(static_cast<int>(len), buf)) return RC_UNKNOWN_ERROR;
  irq = nfc15693_.getIRQStatus();
  if (!(irq & RX_SOF_DET_IRQ_STAT)) {  // wie die Bibliothek: Rahmen ohne SOF ist "nichts"
    nfc15693_.clearIRQStatus(TX_IRQ_STAT | IDLE_IRQ_STAT);
    return RC_NO_CARD;
  }
  nfc15693_.clearIRQStatus(RX_SOF_DET_IRQ_STAT | IDLE_IRQ_STAT | TX_IRQ_STAT | RX_IRQ_STAT);
  const FrameCheck check = checkInventoryFrame(rxStatus, buf);
  describeFrame(check, rxStatus, buf, invDetail, sizeof invDetail);
  errDetail_ = invDetail;
  const int rc = frameToRc(check, buf);
  if (rc == RC_OK) {
    memcpy(uid, buf + 2, 8);
    if (!firstInvLenSeen_) {  // fuer die einmalige DBG-Zeile (main.cpp)
      firstInvLenSeen_ = true;
      firstInvLen_ = static_cast<uint8_t>(len);
      firstInvLenPending_ = true;
    }
  }
  return rc;
}

bool Reader::takeFirstInventoryLen(uint8_t* len) {
  if (!firstInvLenPending_) return false;
  firstInvLenPending_ = false;
  *len = firstInvLen_;
  return true;
}

Reading Reader::readIso14443() {
  nfc14443_.reset();
  // Kein setupRF(): die Aktivierung laedt die Konfiguration und schaltet das
  // Feld selbst ein (ein zweites RF_ON wartet fest 500 ms, siehe tonie_test).
  // Eigener Pfad statt readCardSerial(): prueft Fehlerbits, Laengen, BCC und SAK
  // (typea.h).
  Chip14443 chip(nfc14443_);
  const TypeAResult res = activateTypeAChecked(chip);
  switch (res.kind) {
    case TypeAResult::Kind::Uid: return Reading::tag(UidType::Ntag, res.uid, res.len);
    case TypeAResult::Kind::Error:
      snprintf(ntagDetail, sizeof ntagDetail, "%s", res.detail);
      return Reading::failure(res.error, ntagDetail);
    case TypeAResult::Kind::Nothing: break;
  }
  // Die Bibliothek meldet Zeitgrenzen (setRF_on, BUSY) nicht getrennt von
  // "keine Karte"; ein so langer Zyklus war aber keine leere Antwort.
  if (cycleLooksTimedOut(millis() - cycleStart_))
    return Reading::failure(CycleError::Pn5180Timeout, "iso14443a read exceeded time limit");
  return Reading::nothing();
}

Reading Reader::readIso15693() {
  uint8_t uid[8] = {0};
  nfc15693_.reset();
  if (!nfc15693_.setupRF())
    return Reading::failure(CycleError::Pn5180Timeout, "rf field did not start");

  nfc15693_.clearIRQStatus(0xffffffff);  // alte IRQ-Flags wuerden Phantomkarten melden
  int rc = inventoryChecked(uid);
  if (rc == RC_OK) {
    uint8_t msb[8];
    for (uint8_t i = 0; i < 8; i++) msb[i] = uid[7 - i];  // ISO 15693: LSB zuerst -> umdrehen
    return Reading::tag(UidType::Iso15693, msb, 8);
  }
  if (classifyResponse(rc) == RespClass::Error)
    return Reading::failure(CycleError::BadResponse, errDetail_);

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

  rc = inventoryChecked(uid);
  switch (classifyReinventory(rc)) {
    case UnlockClass::Proceed: {
      uint8_t msb[8];
      for (uint8_t i = 0; i < 8; i++) msb[i] = uid[7 - i];
      return Reading::tag(UidType::Iso15693, msb, 8);
    }
    case UnlockClass::Nothing: return Reading::nothing();
    case UnlockClass::Error:
      return Reading::failure(CycleError::BadResponse, errDetail_);
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
