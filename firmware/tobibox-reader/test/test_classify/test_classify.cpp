// Native Tests der Antwort-Einordnung (classify.h): Rahmenpruefung der
// Inventory-Antwort, feste Abbildung des Fehlerflags, Entsperren nach Vorgabe,
// Pruefungen fuer ISO 14443A.
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
  b[2] ^= 0x01;  // genau ein Bit: 0x42 -> 0x43
  TEST_ASSERT_EQUAL_HEX8(0x43, b[2]);
  TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::BadCrc);
}

void test_frame_with_three_wrong_bits_is_rejected_by_crc() {
  uint8_t b[INV_MAX_LEN];
  size_t n = buildFrame(b, true);
  b[2] ^= 0x4c;  // drei Bits: 0x42 -> 0x0e, wie im Fehlerfall
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

void test_frame_length_detail_names_the_length() {
  uint8_t b[INV_MAX_LEN];
  buildFrame(b, false);
  char d[64];
  describeFrame(FrameCheck::BadLength, 11, b, d, sizeof d);
  TEST_ASSERT_EQUAL_STRING("inventory length=11", d);
  // auch eine zu lange Antwort nennt ihre Laenge
  describeFrame(FrameCheck::BadLength, 300, b, d, sizeof d);
  TEST_ASSERT_EQUAL_STRING("inventory length=300", d);
}

// Echtes Fehlerflag des Tags (Laenge 2 ohne CRC, Laenge 4 mit CRC).
static size_t buildTagError(uint8_t* buf, uint8_t code, bool withCrc) {
  memset(buf, 0, INV_MAX_LEN);
  buf[0] = 0x01;
  buf[1] = code;
  if (!withCrc) return 2;
  const uint16_t crc = static_cast<uint16_t>(~crc16Iso15693(buf, 2));
  buf[2] = static_cast<uint8_t>(crc & 0xff);
  buf[3] = static_cast<uint8_t>(crc >> 8);
  return 4;
}

void test_frame_tag_error_flag_maps_to_fixed_code() {
  uint8_t b[INV_MAX_LEN];
  for (int withCrc = 0; withCrc <= 1; withCrc++) {
    // Codes 0x01 und 0xA0 (benutzerdefiniert): fest RC_TAG_ERROR, nie der rohe Code
    const uint8_t codes[] = {0x01, 0x02, 0x10, 0xA0, 0xFF};
    for (uint8_t code : codes) {
      const size_t n = buildTagError(b, code, withCrc);
      TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::TagError);
      TEST_ASSERT_EQUAL(RC_TAG_ERROR, frameToRc(FrameCheck::TagError, b));
    }
    // Code 0x0F ("unbekannt") wie in der Bibliothek ein Fehler
    size_t n = buildTagError(b, 0x0F, withCrc);
    TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::TagError);
    TEST_ASSERT_EQUAL(RC_UNKNOWN_ERROR, frameToRc(FrameCheck::TagError, b));
    // Code 0x00 ist kein Fehlercode: nie RC_OK (das waere eine leere Kennung)
    n = buildTagError(b, 0x00, withCrc);
    TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::TagError);
    TEST_ASSERT_EQUAL(RC_UNKNOWN_ERROR, frameToRc(FrameCheck::TagError, b));
  }
}

void test_tag_error_codes_keep_unlock_behaviour() {
  uint8_t b[INV_MAX_LEN];
  // erstes Inventory: Fehlerflag -> weiter zum Entsperrversuch (wie bisher)
  buildTagError(b, 0x01, false);
  TEST_ASSERT_TRUE(classifyResponse(frameToRc(FrameCheck::TagError, b)) == RespClass::Nothing);
  // zweites Inventory nach dem Entsperren: Fehlerflag -> gesperrt (wie bisher)
  TEST_ASSERT_TRUE(classifyReinventory(frameToRc(FrameCheck::TagError, b)) == UnlockClass::Locked);
  // 0x0F und 0x00 sind Fehler in beiden Faellen
  buildTagError(b, 0x0F, false);
  TEST_ASSERT_TRUE(classifyResponse(frameToRc(FrameCheck::TagError, b)) == RespClass::Error);
  TEST_ASSERT_TRUE(classifyReinventory(frameToRc(FrameCheck::TagError, b)) == UnlockClass::Error);
}

void test_tag_error_frame_with_bad_crc_is_rejected() {
  uint8_t b[INV_MAX_LEN];
  size_t n = buildTagError(b, 0x01, true);
  b[1] ^= 0x01;
  TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::BadCrc);
}

void test_error_flag_in_full_frame_is_rejected_not_taken_as_tag_error() {
  uint8_t b[INV_MAX_LEN];
  for (int withCrc = 0; withCrc <= 1; withCrc++) {
    size_t n = buildFrame(b, false);
    b[0] = 0x01;  // Fehlerflag, DSFID 0x00 wie bei einem Tonie
    if (withCrc) {
      const uint16_t crc = static_cast<uint16_t>(~crc16Iso15693(b, 10));
      b[10] = static_cast<uint8_t>(crc & 0xff);
      b[11] = static_cast<uint8_t>(crc >> 8);
      n = 12;
    }
    TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::BadFlags);
    // Fall aus dem Review: darf nie RC_OK werden (Kennung waere nur Nullen)
    TEST_ASSERT_EQUAL(RC_UNKNOWN_ERROR, frameToRc(FrameCheck::BadFlags, b));
  }
}

void test_zero_uid_is_never_valid() {
  uint8_t b[INV_MAX_LEN];
  for (int withCrc = 0; withCrc <= 1; withCrc++) {
    size_t n = buildFrame(b, false);
    memset(b + 2, 0, 8);
    if (withCrc) {
      const uint16_t crc = static_cast<uint16_t>(~crc16Iso15693(b, 10));
      b[10] = static_cast<uint8_t>(crc & 0xff);
      b[11] = static_cast<uint8_t>(crc >> 8);
      n = 12;
    }
    TEST_ASSERT_TRUE(checkInventoryFrame(n, b) == FrameCheck::ZeroUid);
    TEST_ASSERT_EQUAL(RC_UNKNOWN_ERROR, frameToRc(FrameCheck::ZeroUid, b));
  }
}

void test_frame_to_rc_ok_only_for_ok() {
  uint8_t b[INV_MAX_LEN] = {0};
  TEST_ASSERT_EQUAL(RC_OK, frameToRc(FrameCheck::Ok, b));
  const FrameCheck bad[] = {FrameCheck::BadFlags, FrameCheck::ZeroUid, FrameCheck::RxError,
                            FrameCheck::BadLength, FrameCheck::BadCrc};
  for (FrameCheck c : bad) TEST_ASSERT_EQUAL(RC_UNKNOWN_ERROR, frameToRc(c, b));
}

// ---- ISO 14443A

void test_typea_frame_check() {
  TEST_ASSERT_TRUE(checkTypeAFrame(0, 5) == TypeAFrame::Nothing);
  // auch mit gesetztem Fehlerbit: nichts empfangen heisst keine Karte
  TEST_ASSERT_TRUE(checkTypeAFrame(1UL << 16, 5) == TypeAFrame::Nothing);
  TEST_ASSERT_TRUE(checkTypeAFrame(5, 5) == TypeAFrame::Ok);
  for (uint32_t bit = 16; bit <= 18; bit++)
    TEST_ASSERT_TRUE(checkTypeAFrame(5 | (1UL << bit), 5) == TypeAFrame::RxError);
  TEST_ASSERT_TRUE(checkTypeAFrame(4, 5) == TypeAFrame::BadLength);
  TEST_ASSERT_TRUE(checkTypeAFrame(6, 5) == TypeAFrame::BadLength);
  TEST_ASSERT_TRUE(checkTypeAFrame(2, 1) == TypeAFrame::BadLength);
}

void test_typea_bcc() {
  const uint8_t four[5] = {0x12, 0x34, 0x56, 0x78, 0x12 ^ 0x34 ^ 0x56 ^ 0x78};
  TEST_ASSERT_TRUE(typeABccValid(four));
  // 7-Byte-Tag, Ebene 1: 0x88 zaehlt mit
  const uint8_t cascade[5] = {0x88, 0x04, 0x11, 0x22, 0x88 ^ 0x04 ^ 0x11 ^ 0x22};
  TEST_ASSERT_TRUE(typeABccValid(cascade));
  for (int i = 0; i < 5; i++) {
    uint8_t b[5];
    memcpy(b, four, 5);
    b[i] ^= 0x10;
    TEST_ASSERT_FALSE(typeABccValid(b));
  }
}

void test_typea_sak_consistency() {
  TEST_ASSERT_TRUE(typeASakConsistent(0x04, 0x00));   // 4 Byte, fertig
  TEST_ASSERT_TRUE(typeASakConsistent(0x88, 0x04));   // 7 Byte, Ebene 2 folgt
  TEST_ASSERT_FALSE(typeASakConsistent(0x88, 0x00));  // 0x88 ohne Cascade-Bit
  TEST_ASSERT_FALSE(typeASakConsistent(0x04, 0x04));  // Cascade-Bit ohne 0x88
  TEST_ASSERT_TRUE(typeASakConsistent(0x04, 0x20));   // ISO 14443-4 ist kein Problem
}

void test_typea_uid_plausible() {
  const uint8_t ok4[4] = {0x04, 0x12, 0x34, 0x56};
  TEST_ASSERT_TRUE(typeAUidPlausible(ok4, 4));
  const uint8_t zero4[4] = {0x00, 0x12, 0x34, 0x56};
  TEST_ASSERT_FALSE(typeAUidPlausible(zero4, 4));
  const uint8_t flat4[4] = {0x04, 0x00, 0xFF, 0x00};
  TEST_ASSERT_FALSE(typeAUidPlausible(flat4, 4));
  const uint8_t ok7[7] = {0x04, 0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc};
  TEST_ASSERT_TRUE(typeAUidPlausible(ok7, 7));
  const uint8_t zeroTail[7] = {0x04, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00};
  TEST_ASSERT_FALSE(typeAUidPlausible(zeroTail, 7));
  TEST_ASSERT_FALSE(typeAUidPlausible(ok4, 5));
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
  RUN_TEST(test_frame_with_three_wrong_bits_is_rejected_by_crc);
  RUN_TEST(test_frame_with_rx_error_bits_is_rejected);
  RUN_TEST(test_frame_wrong_length_is_rejected);
  RUN_TEST(test_frame_length_detail_names_the_length);
  RUN_TEST(test_frame_tag_error_flag_maps_to_fixed_code);
  RUN_TEST(test_tag_error_codes_keep_unlock_behaviour);
  RUN_TEST(test_tag_error_frame_with_bad_crc_is_rejected);
  RUN_TEST(test_error_flag_in_full_frame_is_rejected_not_taken_as_tag_error);
  RUN_TEST(test_zero_uid_is_never_valid);
  RUN_TEST(test_frame_to_rc_ok_only_for_ok);
  RUN_TEST(test_typea_frame_check);
  RUN_TEST(test_typea_bcc);
  RUN_TEST(test_typea_sak_consistency);
  RUN_TEST(test_typea_uid_plausible);
  RUN_TEST(test_health_classes);
  RUN_TEST(test_cycle_timeout_threshold);
  return UNITY_END();
}
