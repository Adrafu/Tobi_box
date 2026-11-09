// Native Tests der Antwort-Einordnung (classify.h): Fehlerflag des Tags ist
// "nichts", nur Uebertragungsfehler sind "fehler", Entsperren nach Vorgabe.
#include <unity.h>

#include <cstring>

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

// Hilfen: Inventory-Rahmen bauen (Flags 0x00, DSFID 0x00, Kennung LSB zuerst).
static const uint8_t INV_UID_LSB[8] = {0x42, 0x7e, 0xea, 0x1b, 0x50, 0x03, 0x04, 0xe0};

static size_t buildFrame(uint8_t* buf, bool withCrc) {
  memset(buf, 0, INV_MAX_LEN);
  buf[0] = 0x00;
  buf[1] = 0x00;
  memcpy(buf + 2, INV_UID_LSB, 8);
  if (!withCrc) return 10;
  const uint16_t crc = static_cast<uint16_t>(~crc16Iso15693(buf, 10));  // gesendet wird invertiert
  buf[10] = static_cast<uint8_t>(crc & 0xff);
  buf[11] = static_cast<uint8_t>(crc >> 8);
  return 12;
}

void test_crc16_known_value() {
  // Pruefwert von CRC-16/X-25 ("123456789" -> 0x906E nach dem Invertieren).
  const uint8_t s[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
  TEST_ASSERT_EQUAL_HEX16(0x906E, static_cast<uint16_t>(~crc16Iso15693(s, sizeof s)));
}

void test_frame_clean_without_and_with_crc() {
  uint8_t b[INV_MAX_LEN];
  size_t n = buildFrame(b, false);
  TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::Ok);
  n = buildFrame(b, true);
  TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::Ok);
}

void test_frame_with_one_wrong_bit_is_rejected_by_crc() {
  uint8_t b[INV_MAX_LEN];
  size_t n = buildFrame(b, true);
  b[2] ^= 0x4c;  // 0x42 -> 0x0e, wie im Fehlerfall
  TEST_ASSERT_EQUAL_HEX8(0x0e, b[2]);
  TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::BadCrc);
}

void test_frame_with_rx_error_bits_is_rejected() {
  uint8_t b[INV_MAX_LEN];
  const size_t n = buildFrame(b, false);
  // 16: Datenintegritaet (CRC), 17: Protokollfehler, 18: Kollision
  for (uint32_t bit = 16; bit <= 18; bit++)
    TEST_ASSERT_TRUE(checkInventoryFrame(n | (1UL << bit), b) == FrameCheck::RxError);
  // Kollisionsposition (Bit 19 bis 25) allein ist kein Fehlerbit
  TEST_ASSERT_TRUE(checkInventoryFrame(n | (1UL << 20), b) == FrameCheck::Ok);
}

void test_frame_wrong_length_is_rejected() {
  uint8_t b[INV_MAX_LEN];
  buildFrame(b, false);
  const size_t bad[] = {0, 1, 3, 5, 9, 11, 13, 16};
  for (size_t n : bad) TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::BadLength);
}

void test_frame_tag_error_flag_stays_nothing() {
  uint8_t b[INV_MAX_LEN] = {0x01, 0x0f};  // Fehlerflag, Code "unbekannt"
  TEST_ASSERT_TRUE(checkInventoryFrame(2, b) == FrameCheck::TagError);
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
  RUN_TEST(test_crc16_known_value);
  RUN_TEST(test_frame_clean_without_and_with_crc);
  RUN_TEST(test_frame_with_one_wrong_bit_is_rejected_by_crc);
  RUN_TEST(test_frame_with_rx_error_bits_is_rejected);
  RUN_TEST(test_frame_wrong_length_is_rejected);
  RUN_TEST(test_frame_tag_error_flag_stays_nothing);
  RUN_TEST(test_health_classes);
  RUN_TEST(test_cycle_timeout_threshold);
  return UNITY_END();
}
