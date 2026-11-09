// Native Tests der NTAG-Aktivierung (typea.h) mit einem Fake-Chip:
// Ablaufprotokoll der Chip-Befehle (Reihenfolge), BCC, Fehlerbits, Laengen,
// SAK, 4- und 7-Byte-Kennung.
#include <unity.h>

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>

#include "typea.h"

using namespace tobibox;

void setUp() {}
void tearDown() {}

// Antwort des "Tags" auf einen Befehl (Schluessel: erste zwei Bytes, bei REQA eines).
struct Reply {
  std::vector<uint8_t> data;
  uint32_t rxExtra = 0;       // zusaetzliche Bits in RX_STATUS (Fehlerbits)
  bool useLen = false;        // Anzahl Bytes erzwingen (statt data.size())
  uint32_t forcedLen = 0;
};

class FakeChip {
 public:
  std::string trace;  // Ablaufprotokoll, durch Leerzeichen getrennt
  std::map<int, Reply> replies;
  bool failSend = false;
  int failOp = -1;  // n-ter Befehl scheitert (0-basiert), -1 = keiner
  int ops = 0;
  uint32_t now = 0;
  int waitCalls = 0;
  bool neverWait = false;

  bool loadRfConfig() { return op("load"); }
  void rfOn() { log("rfon"); }
  void delayMs(uint32_t ms) {
    now += ms;
    log("delay" + std::to_string(ms));
  }
  uint32_t nowMs() { return now; }
  bool cryptoOff() { return op("crypto0"); }
  bool crcRx(bool on) { return op(on ? "rxcrc1" : "rxcrc0"); }
  bool crcTx(bool on) { return op(on ? "txcrc1" : "txcrc0"); }
  bool idle() { return op("idle"); }
  bool transceive() { return op("trx"); }
  bool inWaitTransmit() {
    log("wait");
    waitCalls++;
    return !neverWait;
  }
  bool clearIrq() { return op("clr"); }
  bool send(const uint8_t* d, int n, uint8_t bits) {
    (void)bits;
    log("send" + hex(d[0]) + (n > 1 ? hex(d[1]) : std::string()));
    if (failSend) return false;
    key_ = n == 1 ? d[0] : (d[0] << 8 | d[1]);
    return true;
  }
  uint32_t rxStatus() {
    log("rx");
    auto it = replies.find(key_);
    if (it == replies.end()) return 0;
    const Reply& r = it->second;
    const uint32_t len = r.useLen ? r.forcedLen : static_cast<uint32_t>(r.data.size());
    return len | r.rxExtra;
  }
  bool read(int n, uint8_t* buf) {
    log("read" + std::to_string(n));
    auto it = replies.find(key_);
    memset(buf, 0, static_cast<size_t>(n));
    if (it != replies.end())
      memcpy(buf, it->second.data.data(), std::min<size_t>(static_cast<size_t>(n), it->second.data.size()));
    return true;
  }

 private:
  static std::string hex(uint8_t v) {
    char b[4];
    snprintf(b, sizeof b, "%02x", v);
    return b;
  }
  void log(const std::string& s) {
    if (!trace.empty()) trace += ' ';
    trace += s;
  }
  bool op(const char* name) {
    log(name);
    return ops++ != failOp;
  }
  int key_ = 0;
};

static std::vector<uint8_t> withBcc(const uint8_t* four) {
  std::vector<uint8_t> v(four, four + 4);
  v.push_back(static_cast<uint8_t>(four[0] ^ four[1] ^ four[2] ^ four[3]));
  return v;
}

// Tag mit 4-Byte-Kennung.
static void setup4(FakeChip& c, const uint8_t uid[4]) {
  c.replies[0x26] = {{0x44, 0x00}, 0, false, 0};
  c.replies[0x9320] = {withBcc(uid), 0, false, 0};
  c.replies[0x9370] = {{0x00}, 0, false, 0};  // SAK
}

// Tag mit 7-Byte-Kennung.
static void setup7(FakeChip& c, const uint8_t uid[7]) {
  const uint8_t l1[4] = {0x88, uid[0], uid[1], uid[2]};
  c.replies[0x26] = {{0x44, 0x00}, 0, false, 0};
  c.replies[0x9320] = {withBcc(l1), 0, false, 0};
  c.replies[0x9370] = {{0x04}, 0, false, 0};
  c.replies[0x9520] = {withBcc(uid + 3), 0, false, 0};
  c.replies[0x9570] = {{0x00}, 0, false, 0};
}

static const uint8_t UID4[4] = {0x04, 0x12, 0x34, 0x56};
static const uint8_t UID7[7] = {0x04, 0x52, 0x2a, 0x1b, 0xc3, 0x71, 0x80};

// Schrittfolge: wie activateTypeA() der Bibliothek (Commit 69ec032), dazu die
// markierten Ergaenzungen. Aendert jemand die Reihenfolge, schlaegt dieser Test fehl.
static const char* GOLDEN_4 =
    "load rfon delay10 crypto0 rxcrc0 txcrc0 idle trx wait clr "
    "send26 delay10 rx read2 "                       // rx: neu (Laenge ATQA)
    "wait clr "
    "send9320 delay5 rx read5 "                      // rx: wie rxBytesReceived() der Bibliothek
    "rxcrc1 txcrc1 "
    "send9370 delay5 rx read1";                      // delay5, rx: neu (Laenge und Fehlerbits SAK)

static const char* GOLDEN_7_TAIL =
    " rxcrc0 txcrc0 send9520 delay5 rx read5 "       // delay5, rx: neu
    "rxcrc1 txcrc1 send9570 delay5 rx read1";        // delay5, rx: neu

void test_four_byte_uid_and_command_order() {
  FakeChip c;
  setup4(c, UID4);
  TypeAResult r = activateTypeAChecked(c);
  TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Uid);
  TEST_ASSERT_EQUAL(4, r.len);
  TEST_ASSERT_EQUAL_HEX8_ARRAY(UID4, r.uid, 4);
  TEST_ASSERT_EQUAL_STRING(GOLDEN_4, c.trace.c_str());
}

void test_seven_byte_uid_and_command_order() {
  FakeChip c;
  setup7(c, UID7);
  TypeAResult r = activateTypeAChecked(c);
  TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Uid);
  TEST_ASSERT_EQUAL(7, r.len);
  TEST_ASSERT_EQUAL_HEX8_ARRAY(UID7, r.uid, 7);
  TEST_ASSERT_EQUAL_STRING((std::string(GOLDEN_4) + GOLDEN_7_TAIL).c_str(), c.trace.c_str());
}

void test_empty_field_is_nothing_and_stops_early() {
  FakeChip c;  // keine Antworten
  TypeAResult r = activateTypeAChecked(c);
  TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Nothing);
  TEST_ASSERT_EQUAL_STRING("load rfon delay10 crypto0 rxcrc0 txcrc0 idle trx wait clr send26 delay10 rx",
                           c.trace.c_str());
}

void test_chip_command_failure_is_nothing() {
  for (int n = 0; n < 6; n++) {  // load, crypto, rxcrc, txcrc, idle, trx
    FakeChip c;
    setup4(c, UID4);
    c.failOp = n;
    TypeAResult r = activateTypeAChecked(c);
    TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Nothing);
  }
  FakeChip c;
  setup4(c, UID4);
  c.failSend = true;
  TEST_ASSERT_TRUE(activateTypeAChecked(c).kind == TypeAResult::Kind::Nothing);
}

void test_wait_transmit_timeout_is_nothing() {
  FakeChip c;
  setup4(c, UID4);
  c.neverWait = true;
  // Das erste "wait" (vor REQA) scheitert gleich: Nothing
  TEST_ASSERT_TRUE(activateTypeAChecked(c).kind == TypeAResult::Kind::Nothing);
}

void test_bad_bcc_level1_is_error() {
  for (int i = 0; i < 5; i++) {
    FakeChip c;
    setup4(c, UID4);
    c.replies[0x9320].data[i] ^= 0x10;  // ein Byte oder das BCC verfaelscht
    TypeAResult r = activateTypeAChecked(c);
    TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Error);
    TEST_ASSERT_TRUE(r.error == CycleError::BadResponse);
    TEST_ASSERT_EQUAL_STRING("anticoll1 bcc", r.detail);
    // Es darf kein Select gesendet worden sein
    TEST_ASSERT_TRUE(c.trace.find("send9370") == std::string::npos);
  }
}

void test_bad_bcc_level2_is_error() {
  FakeChip c;
  setup7(c, UID7);
  c.replies[0x9520].data[2] ^= 0x01;
  TypeAResult r = activateTypeAChecked(c);
  TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Error);
  TEST_ASSERT_EQUAL_STRING("anticoll2 bcc", r.detail);
  TEST_ASSERT_TRUE(c.trace.find("send9570") == std::string::npos);
}

void test_rx_error_bits_are_errors_at_every_step() {
  const struct { int key; const char* detail; } steps[] = {
      {0x26, "reqa rx error bit"},
      {0x9320, "anticoll1 rx error bit"},
      {0x9370, "select1 rx error bit"},
  };
  for (const auto& st : steps) {
    for (uint32_t bit = 16; bit <= 18; bit++) {
      FakeChip c;
      setup4(c, UID4);
      c.replies[st.key].rxExtra = 1UL << bit;
      TypeAResult r = activateTypeAChecked(c);
      TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Error);
      TEST_ASSERT_EQUAL_STRING(st.detail, r.detail);
    }
  }
  FakeChip c;
  setup7(c, UID7);
  c.replies[0x9520].rxExtra = 1UL << 16;
  TEST_ASSERT_EQUAL_STRING("anticoll2 rx error bit", activateTypeAChecked(c).detail);
  FakeChip d;
  setup7(d, UID7);
  d.replies[0x9570].rxExtra = 1UL << 17;
  TEST_ASSERT_EQUAL_STRING("select2 rx error bit", activateTypeAChecked(d).detail);
}

void test_wrong_length_is_error_with_length() {
  FakeChip c;
  setup4(c, UID4);
  c.replies[0x9320].useLen = true;
  c.replies[0x9320].forcedLen = 4;
  TypeAResult r = activateTypeAChecked(c);
  TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Error);
  TEST_ASSERT_EQUAL_STRING("anticoll1 length=4", r.detail);

  FakeChip d;
  setup4(d, UID4);
  d.replies[0x9370].useLen = true;
  d.replies[0x9370].forcedLen = 3;  // SAK plus CRC kaeme als 3: sichtbar, nicht stumm
  TEST_ASSERT_EQUAL_STRING("select1 length=3", activateTypeAChecked(d).detail);

  FakeChip e;
  setup4(e, UID4);
  e.replies[0x26].useLen = true;
  e.replies[0x26].forcedLen = 1;
  TEST_ASSERT_EQUAL_STRING("reqa length=1", activateTypeAChecked(e).detail);
}

void test_no_sak_answer_is_nothing_not_a_uid() {
  FakeChip c;
  setup4(c, UID4);
  c.replies[0x9370].data.clear();  // Tag hat das Select nicht beantwortet
  TypeAResult r = activateTypeAChecked(c);
  TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Nothing);
  TEST_ASSERT_EQUAL(0, r.len);
}

void test_sak_must_match_cascade_tag() {
  FakeChip c;
  setup4(c, UID4);
  c.replies[0x9370].data[0] = 0x04;  // Cascade-Bit, aber Kennung beginnt nicht mit 0x88
  TypeAResult r = activateTypeAChecked(c);
  TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Error);
  TEST_ASSERT_EQUAL_STRING("sak1 cascade mismatch", r.detail);

  FakeChip d;
  const uint8_t ct4[4] = {0x88, 0x12, 0x34, 0x56};
  setup4(d, ct4);  // 0x88 vorn, aber SAK ohne Cascade-Bit
  TEST_ASSERT_TRUE(activateTypeAChecked(d).kind == TypeAResult::Kind::Error);
}

void test_ten_byte_uid_is_rejected_as_uid_invalid() {
  FakeChip c;
  setup7(c, UID7);
  c.replies[0x9570].data[0] = 0x04;  // auch nach Ebene 2 nicht fertig
  TypeAResult r = activateTypeAChecked(c);
  TEST_ASSERT_TRUE(r.kind == TypeAResult::Kind::Error);
  TEST_ASSERT_TRUE(r.error == CycleError::UidInvalid);
}

void test_implausible_uids_are_nothing_like_the_library() {
  FakeChip c;
  const uint8_t zero0[4] = {0x00, 0x12, 0x34, 0x56};
  setup4(c, zero0);
  TEST_ASSERT_TRUE(activateTypeAChecked(c).kind == TypeAResult::Kind::Nothing);
  FakeChip d;
  setup4(d, UID4);
  d.replies[0x26].data = {0xFF, 0xFF};
  TEST_ASSERT_TRUE(activateTypeAChecked(d).kind == TypeAResult::Kind::Nothing);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_four_byte_uid_and_command_order);
  RUN_TEST(test_seven_byte_uid_and_command_order);
  RUN_TEST(test_empty_field_is_nothing_and_stops_early);
  RUN_TEST(test_chip_command_failure_is_nothing);
  RUN_TEST(test_wait_transmit_timeout_is_nothing);
  RUN_TEST(test_bad_bcc_level1_is_error);
  RUN_TEST(test_bad_bcc_level2_is_error);
  RUN_TEST(test_rx_error_bits_are_errors_at_every_step);
  RUN_TEST(test_wrong_length_is_error_with_length);
  RUN_TEST(test_no_sak_answer_is_nothing_not_a_uid);
  RUN_TEST(test_sak_must_match_cascade_tag);
  RUN_TEST(test_ten_byte_uid_is_rejected_as_uid_invalid);
  RUN_TEST(test_implausible_uids_are_nothing_like_the_library);
  return UNITY_END();
}
