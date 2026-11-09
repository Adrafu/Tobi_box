#include "classify.h"

namespace tobibox {

RespClass classifyResponse(int rc) {
  if (rc == RC_OK) return RespClass::Ok;
  if (rc == RC_UNKNOWN_ERROR) return RespClass::Error;
  return RespClass::Nothing;  // RC_NO_CARD und Fehlerflag des Tags
}

UnlockClass classifyUnlock(int rc, bool tag_still_answers) {
  if (rc == RC_OK) return UnlockClass::Proceed;
  if (rc == RC_NO_CARD) return tag_still_answers ? UnlockClass::Locked : UnlockClass::Nothing;
  if (rc == RC_UNKNOWN_ERROR) return UnlockClass::Error;
  return UnlockClass::Locked;  // positiver Fehlercode des Tags: Passwort abgelehnt
}

UnlockClass classifyReinventory(int rc) {
  if (rc == RC_OK) return UnlockClass::Proceed;
  if (rc == RC_NO_CARD) return UnlockClass::Nothing;
  if (rc == RC_UNKNOWN_ERROR) return UnlockClass::Error;
  return UnlockClass::Locked;
}

Health classifyHealth(uint32_t value) {
  if (value == HEALTH_SENTINEL) return Health::Timeout;
  if (value == 0xFFFFFFFFUL) return Health::NoResponse;
  return Health::Ok;
}

uint16_t crc16Iso15693(const uint8_t* data, size_t len) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < len; i++) {
    crc ^= data[i];
    for (int b = 0; b < 8; b++) crc = (crc & 1) ? static_cast<uint16_t>((crc >> 1) ^ 0x8408) : static_cast<uint16_t>(crc >> 1);
  }
  return crc;  // ohne abschliessendes Invertieren
}

FrameCheck checkInventoryFrame(uint32_t rx_status, const uint8_t* buf) {
  if (rx_status & RX_ERROR_BITS) return FrameCheck::RxError;
  const size_t len = rx_status & RX_LEN_MASK;
  // Fehlerantwort des Tags: Flags (Bit 0 gesetzt) + Fehlercode, ggf. + CRC.
  // Sie bleibt "nichts", wie vor dieser Pruefung (classifyResponse).
  if ((len == 2 || len == 4) && (buf[0] & 0x01)) {
    if (len == 4 && crc16Iso15693(buf, len) != ISO15693_CRC_RESIDUE) return FrameCheck::BadCrc;
    return FrameCheck::TagError;
  }
  if (len != INV_LEN_NO_CRC && len != INV_LEN_WITH_CRC) return FrameCheck::BadLength;
  if (len == INV_LEN_WITH_CRC && crc16Iso15693(buf, len) != ISO15693_CRC_RESIDUE)
    return FrameCheck::BadCrc;
  if (buf[0] & 0x01) return FrameCheck::TagError;  // nur bei Verfaelschung moeglich
  return FrameCheck::Ok;
}

}  // namespace tobibox
