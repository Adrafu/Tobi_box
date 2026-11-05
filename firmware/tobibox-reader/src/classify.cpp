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

}  // namespace tobibox
