// Native Tests der Antwort-Einordnung (classify.h): Fehlerflag des Tags ist
// "nichts", nur Uebertragungsfehler sind "fehler", Entsperren nach Vorgabe.
#include <unity.h>

#include "classify.h"

using namespace tobibox;

void setUp() {}
void tearDown() {}

void test_response_classes() {
  TEST_ASSERT_TRUE(classifyResponse(RC_OK) == RespClass::Ok);
  TEST_ASSERT_TRUE(classifyResponse(RC_NO_CARD) == RespClass::Nothing);
  // Fehlerflag des Tags (nicht unterstuetzt, nicht erkannt, Option, Block, benutzerdefiniert)
  const int tagErrors[] = {0x01, 0x02, 0x03, 0x10, 0x11, 0x12, 0x13, 0x14, 0xA0};
  for (int rc : tagErrors) TEST_ASSERT_TRUE(classifyResponse(rc) == RespClass::Nothing);
  TEST_ASSERT_TRUE(classifyResponse(RC_UNKNOWN_ERROR) == RespClass::Error);
}

void test_unlock_classes() {
  TEST_ASSERT_TRUE(classifyUnlock(RC_OK, false) == UnlockClass::Proceed);
  // keine Karte: Tag weg -> nichts; schweigt das Tag nur beim Passwort -> gesperrt
  TEST_ASSERT_TRUE(classifyUnlock(RC_NO_CARD, false) == UnlockClass::Nothing);
  TEST_ASSERT_TRUE(classifyUnlock(RC_NO_CARD, true) == UnlockClass::Locked);
  // positiver Fehlercode des Tags: Passwort abgelehnt
  TEST_ASSERT_TRUE(classifyUnlock(0x01, false) == UnlockClass::Locked);
  TEST_ASSERT_TRUE(classifyUnlock(0xA0, false) == UnlockClass::Locked);
  TEST_ASSERT_TRUE(classifyUnlock(RC_UNKNOWN_ERROR, false) == UnlockClass::Error);
  TEST_ASSERT_TRUE(classifyUnlock(RC_UNKNOWN_ERROR, true) == UnlockClass::Error);
}

void test_reinventory_classes() {
  TEST_ASSERT_TRUE(classifyReinventory(RC_OK) == UnlockClass::Proceed);
  TEST_ASSERT_TRUE(classifyReinventory(RC_NO_CARD) == UnlockClass::Nothing);
  TEST_ASSERT_TRUE(classifyReinventory(0x02) == UnlockClass::Locked);
  TEST_ASSERT_TRUE(classifyReinventory(RC_UNKNOWN_ERROR) == UnlockClass::Error);
}

void test_health_classes() {
  TEST_ASSERT_TRUE(classifyHealth(HEALTH_SENTINEL) == Health::Timeout);
  TEST_ASSERT_TRUE(classifyHealth(0xFFFFFFFFUL) == Health::NoResponse);
  TEST_ASSERT_TRUE(classifyHealth(0) == Health::Ok);
  TEST_ASSERT_TRUE(classifyHealth(0x00000040UL) == Health::Ok);
}

void test_cycle_timeout_threshold() {
  TEST_ASSERT_FALSE(cycleLooksTimedOut(449));
  TEST_ASSERT_TRUE(cycleLooksTimedOut(450));
  TEST_ASSERT_TRUE(cycleLooksTimedOut(900));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_response_classes);
  RUN_TEST(test_unlock_classes);
  RUN_TEST(test_reinventory_classes);
  RUN_TEST(test_health_classes);
  RUN_TEST(test_cycle_timeout_threshold);
  return UNITY_END();
}
