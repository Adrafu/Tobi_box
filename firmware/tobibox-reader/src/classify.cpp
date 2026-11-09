#include "classify.h"

#include <cstdio>

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

static bool allZero(const uint8_t* p, size_t n) {
  for (size_t i = 0; i < n; i++)
    if (p[i] != 0) return false;
  return true;
}

FrameCheck checkInventoryFrame(uint32_t rx_status, const uint8_t* buf) {
  if (rx_status & RX_ERROR_BITS) return FrameCheck::RxError;
  const size_t len = rx_status & RX_LEN_MASK;
  // Fehlerantwort des Tags: Flags (Bit 0 gesetzt) + Fehlercode, ggf. + CRC.
  if ((len == 2 || len == 4) && (buf[0] & 0x01)) {
    if (len == 4 && crc16Iso15693(buf, len) != ISO15693_CRC_RESIDUE) return FrameCheck::BadCrc;
    return FrameCheck::TagError;
  }
  if (len != INV_LEN_NO_CRC && len != INV_LEN_WITH_CRC) return FrameCheck::BadLength;
  if (len == INV_LEN_WITH_CRC && crc16Iso15693(buf, len) != ISO15693_CRC_RESIDUE)
    return FrameCheck::BadCrc;
  if (buf[0] & 0x01) return FrameCheck::BadFlags;  // nur bei Verfaelschung moeglich
  if (allZero(buf + 2, 8)) return FrameCheck::ZeroUid;
  return FrameCheck::Ok;
}

int frameToRc(FrameCheck check, const uint8_t* buf) {
  switch (check) {
    case FrameCheck::Ok: return RC_OK;
    case FrameCheck::TagError:
      if (buf[1] == 0x00 || buf[1] == RC_UNKNOWN_ERROR) return RC_UNKNOWN_ERROR;
      return RC_TAG_ERROR;
    default: return RC_UNKNOWN_ERROR;
  }
}

void describeFrame(FrameCheck check, uint32_t rx_status, const uint8_t* buf, char* out, size_t cap) {
  if (cap == 0) return;
  const unsigned len = static_cast<unsigned>(rx_status & RX_LEN_MASK);
  switch (check) {
    case FrameCheck::Ok: snprintf(out, cap, "inventory ok"); break;
    case FrameCheck::TagError: snprintf(out, cap, "inventory tag error code=%u", buf[1]); break;
    case FrameCheck::BadFlags: snprintf(out, cap, "inventory flags length=%u", len); break;
    case FrameCheck::ZeroUid: snprintf(out, cap, "inventory uid zero"); break;
    case FrameCheck::RxError: snprintf(out, cap, "inventory rx error bit"); break;
    case FrameCheck::BadLength: snprintf(out, cap, "inventory length=%u", len); break;
    case FrameCheck::BadCrc: snprintf(out, cap, "inventory crc length=%u", len); break;
  }
}

TypeAFrame checkTypeAFrame(uint32_t rx_status, size_t expected) {
  const size_t len = rx_status & RX_LEN_MASK;
  if (len == 0) return TypeAFrame::Nothing;
  if (rx_status & RX_ERROR_BITS) return TypeAFrame::RxError;
  if (len != expected) return TypeAFrame::BadLength;
  return TypeAFrame::Ok;
}

bool typeABccValid(const uint8_t* five) {
  return static_cast<uint8_t>(five[0] ^ five[1] ^ five[2] ^ five[3]) == five[4];
}

bool typeASakConsistent(uint8_t first, uint8_t sak) {
  return (first == 0x88) == ((sak & 0x04) != 0);
}

bool typeAUidPlausible(const uint8_t* uid, size_t len) {
  if (len != 4 && len != 7) return false;
  if (uid[0] == 0x00) return false;
  bool someData = false;  // wie die Bibliothek: ausser dem ersten Byte nicht nur 0x00/0xFF
  for (size_t i = 1; i < len; i++)
    if (uid[i] != 0x00 && uid[i] != 0xFF) someData = true;
  if (!someData) return false;
  if (len == 7) {
    const uint8_t* t = uid + 3;  // die vier Bytes der Ebene 2
    if (allZero(t, 4)) return false;
    if (t[0] == 0xFF && t[1] == 0xFF && t[2] == 0xFF && t[3] == 0xFF) return false;
  }
  return true;
}

}  // namespace tobibox
