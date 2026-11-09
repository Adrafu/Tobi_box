// Entpreller nach docs/protocol/reader-v1.md, Abschnitt 9. Keine Hardware,
// keine Arduino-Typen; die Zeit kommt als uint32_t in ms.
#include "debounce.h"

#include <cstring>

#include "timing.h"

namespace tobibox {

Reading Reading::tag(UidType t, const uint8_t* bytes, size_t n) {
  Reading r;
  r.kind = Kind::Uid;
  r.type = t;
  r.len = static_cast<uint8_t>(n > MAX_UID_BYTES ? MAX_UID_BYTES : n);
  std::memcpy(r.uid, bytes, r.len);
  return r;
}

Identity Identity::from(const Reading& r) {
  Identity id;
  if (r.kind == Reading::Kind::Locked) {
    id.locked = true;
  } else if (r.kind == Reading::Kind::Uid) {
    id.type = r.type;
    id.len = r.len;
    std::memcpy(id.uid, r.uid, r.len);
  }
  return id;
}

bool Identity::operator==(const Identity& o) const {
  if (locked != o.locked) return false;
  if (locked) return true;
  return len == o.len && std::memcmp(uid, o.uid, len) == 0;
}

DebounceParams::DebounceParams()
    : confirm_reads(CONFIRM_READS),
      change_reads(CHANGE_CONFIRM_READS),
      remove_after_ms(REMOVE_AFTER_MS),
      error_hold_ms(ERROR_HOLD_MS) {}

Debouncer::Debouncer(const DebounceParams& params) : p_(params) {
  if (p_.confirm_reads < 1) p_.confirm_reads = 1;
  if (p_.change_reads < p_.confirm_reads) p_.change_reads = p_.confirm_reads;
}

DebounceResult Debouncer::update(const Reading& in, uint32_t t) {
  DebounceResult out;

  // Schritt 0: Zeitregel (nur im Zustand LIEGT).
  if (state_ == State::Lies) {
    const uint32_t g = only_errors_ ? p_.error_hold_ms : p_.remove_after_ms;
    if (static_cast<uint32_t>(t - last_) >= g) {
      out.removed = true;
      state_ = State::Empty;
      has_challenger_ = false;
    }
  }

  const bool valid = in.valid();
  const uint32_t N = p_.confirm_reads;
  const uint32_t C = p_.change_reads;  // nur im Zustand LIEGT (Wechsel)
  const Identity x = valid ? Identity::from(in) : Identity();

  auto place = [&](const Identity& id) {
    out.placement = id.locked ? DebounceResult::Placement::Locked
                              : DebounceResult::Placement::Placed;
    out.placed = id;
    state_ = State::Lies;
    lying_ = id;
    last_ = t;
    only_errors_ = true;
    has_challenger_ = false;
  };

  // Schritt 1: Übergänge.
  switch (state_) {
    case State::Empty:
      if (!valid) break;  // Zeilen 1 und 2
      if (N >= 2) {       // Zeile 3
        state_ = State::Checking;
        candidate_ = x;
        candidate_n_ = 1;
      } else {            // Zeile 4
        place(x);
      }
      break;

    case State::Checking:
      if (!valid) {  // Zeilen 5 und 6
        state_ = State::Empty;
        break;
      }
      if (x == candidate_) {
        if (candidate_n_ + 1 < N) {  // Zeile 7
          candidate_n_++;
        } else {                     // Zeile 8
          place(x);
        }
      } else {  // Zeile 9
        candidate_ = x;
        candidate_n_ = 1;
        out.rejected = true;
      }
      break;

    case State::Lies:
      if (in.kind == Reading::Kind::Nothing) {  // Zeile 10
        has_challenger_ = false;
        only_errors_ = false;
      } else if (in.kind == Reading::Kind::Error) {  // Zeile 11
        has_challenger_ = false;
      } else if (x == lying_) {  // Zeile 12
        last_ = t;
        only_errors_ = true;
        has_challenger_ = false;
      } else {  // Zeilen 13 bis 15
        out.rejected = true;
        const bool same_challenger = has_challenger_ && x == challenger_;
        if (C == 1 || (same_challenger && challenger_n_ + 1 >= C)) {  // Zeile 15
          out.removed = true;
          place(x);
        } else if (same_challenger) {  // Zeile 14
          challenger_n_++;
          only_errors_ = false;
        } else {  // Zeile 13
          challenger_ = x;
          challenger_n_ = 1;
          has_challenger_ = true;
          only_errors_ = false;
        }
      }
      break;
  }
  return out;
}

}  // namespace tobibox
