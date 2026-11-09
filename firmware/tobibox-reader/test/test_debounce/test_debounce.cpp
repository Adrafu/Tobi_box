// Native Tests des Entprellers (reader-v1.md, Abschnitt 9) mit Standardwerten
// aus timing.h: 2-gleich-Regel, 1,0-s-Luecke, 1,1-s-Abheben, Figurwechsel,
// verfaelschte Kennung am Rand, gesperrter Tonie, "gesperrt -> offen",
// fehler(code) mitten in der Entpreller-Folge, Fehlerfolgen, Zeitueberlauf.
#include <unity.h>

#include <cstdint>

#include "debounce.h"
#include "timing.h"

using namespace tobibox;

void setUp() {}
void tearDown() {}

static const uint8_t A[4] = {0x04, 0xa1, 0xb2, 0xc3};
static const uint8_t A_FLIP[4] = {0x04, 0xa1, 0xb2, 0xc4};
static const uint8_t B[4] = {0x04, 0xff, 0xee, 0xdd};
static const uint8_t TONIE[8] = {0xe0, 0x04, 0x03, 0x12, 0x34, 0x56, 0x78, 0xab};

static Reading ntag(const uint8_t* u) { return Reading::tag(UidType::Ntag, u, 4); }
static Reading tonie() { return Reading::tag(UidType::Iso15693, TONIE, 8); }
static Reading err() { return Reading::failure(CycleError::Pn5180Timeout); }

// Zaehlt die Ereignisse eines Ablaufs.
struct Rec {
  int removed = 0, placed = 0, locked = 0, rejected = 0;
  DebounceResult last;
  DebounceResult step(Debouncer& d, const Reading& r, uint32_t t) {
    DebounceResult x = d.update(r, t);
    removed += x.removed;
    placed += x.placement == DebounceResult::Placement::Placed;
    locked += x.placement == DebounceResult::Placement::Locked;
    rejected += x.rejected;
    last = x;
    return x;
  }
};

void test_defaults_come_from_timing_h() {
  DebounceParams p;
  TEST_ASSERT_EQUAL_UINT32(CONFIRM_READS, p.confirm_reads);
  TEST_ASSERT_EQUAL_UINT32(CHANGE_CONFIRM_READS, p.change_reads);
  TEST_ASSERT_EQUAL_UINT32(1100, p.remove_after_ms);
  TEST_ASSERT_EQUAL_UINT32(5000, p.error_hold_ms);
  TEST_ASSERT_EQUAL_UINT32(200, POLL_PERIOD_MS);
}

void test_two_equal_reads_needed() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  TEST_ASSERT_EQUAL(0, r.placed);
  TEST_ASSERT_FALSE(d.present());
  r.step(d, ntag(A), 200);
  TEST_ASSERT_EQUAL(1, r.placed);
  TEST_ASSERT_TRUE(d.present());
  TEST_ASSERT_TRUE(r.last.placed.len == 4 && r.last.placed.uid[3] == 0xc3);
  r.step(d, ntag(A), 400);  // keine Wiederholung
  TEST_ASSERT_EQUAL(1, r.placed);
}

void test_gap_breaks_confirmation() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, Reading::nothing(), 200);
  r.step(d, ntag(A), 400);
  TEST_ASSERT_EQUAL(0, r.placed);
  r.step(d, ntag(A), 600);
  TEST_ASSERT_EQUAL(1, r.placed);
}

void test_gap_of_1000ms_is_bridged() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);
  for (uint32_t t = 400; t <= 1000; t += 200) r.step(d, Reading::nothing(), t);
  r.step(d, ntag(A), 1200);  // 1000 ms Luecke
  TEST_ASSERT_EQUAL(0, r.removed);
  TEST_ASSERT_TRUE(d.present());
}

void test_removed_at_1100ms_without_valid_read() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);  // last = 200
  for (uint32_t t = 400; t <= 1200; t += 200) r.step(d, Reading::nothing(), t);
  TEST_ASSERT_EQUAL(0, r.removed);  // 1000 ms seit der letzten Lesung
  r.step(d, Reading::nothing(), 1400);  // 1200 ms >= 1100
  TEST_ASSERT_EQUAL(1, r.removed);
  TEST_ASSERT_FALSE(d.present());
}

void test_exactly_at_threshold_removes() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 100);  // last = 100
  r.step(d, Reading::nothing(), 1199);
  TEST_ASSERT_EQUAL(0, r.removed);
  r.step(d, Reading::nothing(), 1200);  // genau 1100
  TEST_ASSERT_EQUAL(1, r.removed);
}

void test_gap_over_threshold_with_same_figure_is_new_placement() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);
  r.step(d, Reading::nothing(), 400);
  r.step(d, ntag(A), 1400);  // Luecke 1200 ms: Zeitregel zuerst
  TEST_ASSERT_EQUAL(1, r.removed);
  TEST_ASSERT_EQUAL(1, r.placed);  // noch nicht neu bestaetigt
  r.step(d, ntag(A), 1600);
  TEST_ASSERT_EQUAL(2, r.placed);
}

void test_figure_change_needs_three_equal_reads() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);
  r.step(d, ntag(B), 400);
  r.step(d, ntag(B), 600);
  TEST_ASSERT_EQUAL(0, r.removed);  // zwei gleiche Lesungen reichen beim Wechsel nicht
  DebounceResult x = r.step(d, ntag(B), 800);
  TEST_ASSERT_TRUE(x.removed);
  TEST_ASSERT_TRUE(x.placement == DebounceResult::Placement::Placed);
  TEST_ASSERT_EQUAL(0xff, x.placed.uid[1]);
  TEST_ASSERT_EQUAL(3, r.rejected);
}

// Gemessener Fall: derselbe verfaelschte Wert in zwei Zyklen nacheinander
// (Tonie am Rand). Beim Auflegen aus dem leeren Zustand zaehlt weiter 2; beim
// Wechsel muss eine dritte gleiche Lesung kommen, die nie kam.
void test_repeated_corruption_twice_is_no_change() {
  static const uint8_t GOOD[8] = {0xe0, 0x04, 0x03, 0x50, 0x1b, 0xea, 0x7e, 0x42};
  static const uint8_t BAD[8] = {0xe0, 0x04, 0x03, 0x50, 0x1b, 0xea, 0x7e, 0x0e};
  Debouncer d;
  Rec r;
  r.step(d, Reading::tag(UidType::Iso15693, GOOD, 8), 0);
  r.step(d, Reading::tag(UidType::Iso15693, GOOD, 8), 200);
  r.step(d, Reading::tag(UidType::Iso15693, BAD, 8), 400);
  r.step(d, Reading::tag(UidType::Iso15693, BAD, 8), 600);
  r.step(d, Reading::tag(UidType::Iso15693, GOOD, 8), 800);
  r.step(d, Reading::tag(UidType::Iso15693, GOOD, 8), 1000);
  TEST_ASSERT_EQUAL(1, r.placed);
  TEST_ASSERT_EQUAL(0, r.removed);
  TEST_ASSERT_TRUE(d.present());
  TEST_ASSERT_EQUAL(0x42, d.current().uid[7]);
}

// Ein Lesefehler mitten im Liegen ist weder REMOVED noch ein Wechsel.
void test_read_error_while_lying_keeps_figure() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);
  r.step(d, err(), 400);
  r.step(d, ntag(A), 600);
  r.step(d, ntag(B), 800);   // Herausforderer 1
  r.step(d, err(), 1000);    // Fehler loescht den Herausforderer
  r.step(d, ntag(B), 1200);  // wieder 1
  r.step(d, ntag(B), 1400);  // 2
  r.step(d, ntag(A), 1600);
  TEST_ASSERT_EQUAL(1, r.placed);
  TEST_ASSERT_EQUAL(0, r.removed);
  TEST_ASSERT_TRUE(d.present());
}

void test_corrupted_uid_at_the_edge_is_ignored() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);
  r.step(d, ntag(A_FLIP), 400);
  r.step(d, ntag(A), 600);
  r.step(d, ntag(A_FLIP), 800);
  r.step(d, ntag(A), 1000);
  TEST_ASSERT_EQUAL(1, r.placed);
  TEST_ASSERT_EQUAL(0, r.removed);
  TEST_ASSERT_EQUAL(2, r.rejected);
  TEST_ASSERT_TRUE(d.present());
}

void test_corrupted_uid_before_confirmation_restarts_count() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A_FLIP), 200);
  r.step(d, ntag(A), 400);
  TEST_ASSERT_EQUAL(0, r.placed);
  r.step(d, ntag(A), 600);
  TEST_ASSERT_EQUAL(1, r.placed);
  TEST_ASSERT_EQUAL(2, r.rejected);
}

void test_challenger_must_be_consecutive() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);
  r.step(d, ntag(B), 400);
  r.step(d, Reading::nothing(), 600);  // loescht den Herausforderer
  r.step(d, ntag(B), 800);
  r.step(d, ntag(A), 1000);
  TEST_ASSERT_EQUAL(0, r.removed);
  TEST_ASSERT_EQUAL(1, r.placed);
}

void test_locked_tonie_is_a_stable_state() {
  Debouncer d;
  Rec r;
  r.step(d, Reading::locked(), 0);
  TEST_ASSERT_EQUAL(0, r.locked);
  DebounceResult x = r.step(d, Reading::locked(), 200);
  TEST_ASSERT_TRUE(x.placement == DebounceResult::Placement::Locked);
  TEST_ASSERT_TRUE(d.present());
  r.step(d, Reading::locked(), 400);
  TEST_ASSERT_EQUAL(1, r.locked);
  for (uint32_t t = 600; t <= 1600; t += 200) r.step(d, Reading::nothing(), t);
  TEST_ASSERT_EQUAL(1, r.removed);  // gleiche Abhebe-Regel wie bei einer Kennung
  TEST_ASSERT_FALSE(d.present());
}

void test_locked_then_open_is_a_change() {
  Debouncer d;
  Rec r;
  r.step(d, Reading::locked(), 0);
  r.step(d, Reading::locked(), 200);
  r.step(d, tonie(), 400);
  r.step(d, tonie(), 600);
  TEST_ASSERT_EQUAL(0, r.removed);
  DebounceResult x = r.step(d, tonie(), 800);
  TEST_ASSERT_TRUE(x.removed);
  TEST_ASSERT_TRUE(x.placement == DebounceResult::Placement::Placed);
  TEST_ASSERT_EQUAL(8, x.placed.len);
}

void test_open_then_locked_is_a_change() {
  Debouncer d;
  Rec r;
  r.step(d, tonie(), 0);
  r.step(d, tonie(), 200);
  r.step(d, Reading::locked(), 400);
  r.step(d, Reading::locked(), 600);
  DebounceResult x = r.step(d, Reading::locked(), 800);
  TEST_ASSERT_TRUE(x.removed);
  TEST_ASSERT_TRUE(x.placement == DebounceResult::Placement::Locked);
}

void test_same_uid_unlocked_or_open_is_the_same_figure() {
  Debouncer d;
  Rec r;
  r.step(d, tonie(), 0);
  r.step(d, tonie(), 200);
  // gleiche Kennung, anderer Typ-Eintrag: gleiche Identitaet (Typ zaehlt nicht)
  r.step(d, Reading::tag(UidType::Ntag, TONIE, 8), 400);
  TEST_ASSERT_EQUAL(0, r.rejected);
  TEST_ASSERT_EQUAL(1, r.placed);
}

void test_error_in_checking_discards_candidate() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, err(), 200);
  r.step(d, ntag(A), 400);
  TEST_ASSERT_EQUAL(0, r.placed);
  r.step(d, ntag(A), 600);
  TEST_ASSERT_EQUAL(1, r.placed);
}

void test_error_when_empty_does_nothing() {
  Debouncer d;
  Rec r;
  r.step(d, err(), 0);
  TEST_ASSERT_FALSE(d.present());
  TEST_ASSERT_EQUAL(0, r.removed + r.placed + r.locked);
}

void test_errors_alone_hold_the_figure_for_5s() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);  // last = 200
  for (uint32_t t = 400; t <= 5100; t += 100) r.step(d, err(), t);
  TEST_ASSERT_EQUAL(0, r.removed);  // 4900 ms Fehler
  r.step(d, err(), 5200);          // 5000 ms
  TEST_ASSERT_EQUAL(1, r.removed);
  TEST_ASSERT_FALSE(d.present());
}

void test_nothing_between_errors_restores_the_1100ms_rule() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);
  r.step(d, err(), 400);
  r.step(d, err(), 800);
  r.step(d, Reading::nothing(), 1000);
  r.step(d, err(), 1200);
  TEST_ASSERT_EQUAL(0, r.removed);
  r.step(d, err(), 1300);  // 1100 ms seit der letzten gueltigen Lesung
  TEST_ASSERT_EQUAL(1, r.removed);
}

void test_error_clears_challenger_but_keeps_last() {
  Debouncer d;
  Rec r;
  r.step(d, ntag(A), 0);
  r.step(d, ntag(A), 200);
  r.step(d, ntag(B), 400);
  r.step(d, err(), 600);
  r.step(d, ntag(B), 800);
  TEST_ASSERT_EQUAL(0, r.removed);
  // fremde Lesung machte nur_fehler falsch: 1100 ms ab last=200
  r.step(d, Reading::nothing(), 1300);
  TEST_ASSERT_EQUAL(1, r.removed);
}

void test_confirm_reads_1_and_3() {
  {
    Debouncer d(DebounceParams(1, 0, 1100, 5000));
    Rec r;
    DebounceResult x = r.step(d, ntag(A), 0);
    TEST_ASSERT_TRUE(x.placement == DebounceResult::Placement::Placed);
    x = r.step(d, ntag(B), 200);
    TEST_ASSERT_TRUE(x.removed);
    TEST_ASSERT_TRUE(x.placement == DebounceResult::Placement::Placed);
    TEST_ASSERT_EQUAL(1, r.rejected);
  }
  {
    Debouncer d(DebounceParams(3, 0, 1100, 5000));
    Rec r;
    r.step(d, ntag(A), 0);
    r.step(d, ntag(A), 200);
    TEST_ASSERT_EQUAL(0, r.placed);
    r.step(d, ntag(A), 400);
    TEST_ASSERT_EQUAL(1, r.placed);
    r.step(d, ntag(B), 600);
    r.step(d, ntag(B), 800);
    TEST_ASSERT_EQUAL(0, r.removed);
    r.step(d, ntag(B), 1000);
    TEST_ASSERT_EQUAL(1, r.removed);
    TEST_ASSERT_EQUAL(2, r.placed);
  }
}

void test_time_wraparound() {
  Debouncer d;
  Rec r;
  const uint32_t t0 = 4294966896U;  // 400 ms vor dem Ueberlauf
  r.step(d, ntag(A), t0);
  r.step(d, ntag(A), t0 + 200);  // last = 4294967096
  uint32_t t = t0 + 400;         // = 0 nach Ueberlauf
  for (int i = 0; i < 5; i++, t += 200) r.step(d, Reading::nothing(), t);
  TEST_ASSERT_EQUAL(0, r.removed);  // t = 800: 1000 ms Luecke
  r.step(d, Reading::nothing(), t);  // t = 1000: 1200 ms
  TEST_ASSERT_EQUAL(1, r.removed);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_defaults_come_from_timing_h);
  RUN_TEST(test_two_equal_reads_needed);
  RUN_TEST(test_gap_breaks_confirmation);
  RUN_TEST(test_gap_of_1000ms_is_bridged);
  RUN_TEST(test_removed_at_1100ms_without_valid_read);
  RUN_TEST(test_exactly_at_threshold_removes);
  RUN_TEST(test_gap_over_threshold_with_same_figure_is_new_placement);
  RUN_TEST(test_figure_change_needs_three_equal_reads);
  RUN_TEST(test_repeated_corruption_twice_is_no_change);
  RUN_TEST(test_read_error_while_lying_keeps_figure);
  RUN_TEST(test_corrupted_uid_at_the_edge_is_ignored);
  RUN_TEST(test_corrupted_uid_before_confirmation_restarts_count);
  RUN_TEST(test_challenger_must_be_consecutive);
  RUN_TEST(test_locked_tonie_is_a_stable_state);
  RUN_TEST(test_locked_then_open_is_a_change);
  RUN_TEST(test_open_then_locked_is_a_change);
  RUN_TEST(test_same_uid_unlocked_or_open_is_the_same_figure);
  RUN_TEST(test_error_in_checking_discards_candidate);
  RUN_TEST(test_error_when_empty_does_nothing);
  RUN_TEST(test_errors_alone_hold_the_figure_for_5s);
  RUN_TEST(test_nothing_between_errors_restores_the_1100ms_rule);
  RUN_TEST(test_error_clears_challenger_but_keeps_last);
  RUN_TEST(test_confirm_reads_1_and_3);
  RUN_TEST(test_time_wraparound);
  return UNITY_END();
}
