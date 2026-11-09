// Entpreller (reine Logik, keine Hardware, keine Arduino-Typen).
// Zustandstabelle: docs/protocol/reader-v1.md, Abschnitt 9.
#pragma once

#include <cstddef>
#include <cstdint>

namespace tobibox {

enum class UidType : uint8_t { Ntag, Iso15693 };

// Fehlercodes eines Abfragezyklus (reader-v1.md, Abschnitt 7).
enum class CycleError : uint8_t {
  Pn5180NoResponse = 0,
  Pn5180Timeout,
  BadResponse,
  UidInvalid,
};
constexpr size_t CYCLE_ERROR_COUNT = 4;

constexpr size_t MAX_UID_BYTES = 10;

// Ergebnis eines Abfragezyklus: genau eines von vier.
struct Reading {
  enum class Kind : uint8_t { Nothing, Uid, Locked, Error };
  Kind kind = Kind::Nothing;
  UidType type = UidType::Ntag;        // nur bei Kind::Uid
  uint8_t len = 0;                     // nur bei Kind::Uid
  uint8_t uid[MAX_UID_BYTES] = {0};    // MSB zuerst (kanonisch)
  CycleError error = CycleError::Pn5180NoResponse;  // nur bei Kind::Error
  const char* detail = nullptr;        // nur bei Kind::Error, optional

  static Reading nothing() { return Reading(); }
  static Reading locked() {
    Reading r;
    r.kind = Kind::Locked;
    return r;
  }
  static Reading failure(CycleError e, const char* detail = nullptr) {
    Reading r;
    r.kind = Kind::Error;
    r.error = e;
    r.detail = detail;
    return r;
  }
  static Reading tag(UidType t, const uint8_t* bytes, size_t n);
  bool valid() const { return kind == Kind::Uid || kind == Kind::Locked; }
};

// Identität einer Figur: "gesperrt" oder eine Kennung. Der Typ zählt beim
// Vergleich nicht (reader-v1.md, Abschnitt "Identität").
struct Identity {
  bool locked = false;
  UidType type = UidType::Ntag;
  uint8_t len = 0;
  uint8_t uid[MAX_UID_BYTES] = {0};

  static Identity from(const Reading& r);
  bool operator==(const Identity& o) const;
  bool operator!=(const Identity& o) const { return !(*this == o); }
};

struct DebounceParams {
  uint32_t confirm_reads;   // aus dem leeren Zustand
  uint32_t change_reads;    // Wechsel bei liegendem Tobie (>= confirm_reads)
  uint32_t remove_after_ms;
  uint32_t error_hold_ms;
  DebounceParams();  // Standardwerte aus timing.h
  // Reihenfolge wie die Felder. change = 0: gleich confirm (wie vor CHANGE_CONFIRM_READS).
  DebounceParams(uint32_t confirm, uint32_t change, uint32_t remove_after, uint32_t error_hold)
      : confirm_reads(confirm),
        change_reads(change == 0 ? confirm : change),
        remove_after_ms(remove_after),
        error_hold_ms(error_hold) {}
};

// Ausgabe je Eingabe: null bis zwei Ereignisse, erst Entfernt, dann
// Platziert/Gesperrt.
struct DebounceResult {
  bool removed = false;
  enum class Placement : uint8_t { None, Placed, Locked };
  Placement placement = Placement::None;
  Identity placed;         // gültig, wenn placement != None
  bool rejected = false;   // Zählung "rejected +1" für diesen Zyklus
};

class Debouncer {
 public:
  explicit Debouncer(const DebounceParams& params = DebounceParams());

  // Ein Abfragezyklus. t: ms, monoton, 32 Bit, darf überlaufen (Differenzen
  // vorzeichenlos modulo 2^32).
  DebounceResult update(const Reading& reading, uint32_t t);

  // Zustand LIEGT (Figur ist gemeldet).
  bool present() const { return state_ == State::Lies; }
  // Liegende Identität; nur gültig, wenn present().
  const Identity& current() const { return lying_; }

 private:
  enum class State : uint8_t { Empty, Checking, Lies };

  DebounceParams p_;
  State state_ = State::Empty;
  Identity candidate_;           // K
  uint32_t candidate_n_ = 0;     // n
  Identity lying_;               // L
  uint32_t last_ = 0;            // Zeit der letzten Lesung von L
  bool only_errors_ = true;      // nur_fehler
  bool has_challenger_ = false;  // H vorhanden
  Identity challenger_;
  uint32_t challenger_n_ = 0;    // hn
};

}  // namespace tobibox
