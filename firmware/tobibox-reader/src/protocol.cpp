// Protokoll-Ausgabe, Befehls-Parser und Referenz-Zeilenparser nach
// docs/protocol/reader-v1.md. Keine Arduino-Typen; Zeit als uint32_t in ms.
#include "protocol.h"

#include <cstdio>
#include <cstring>

#include "timing.h"

namespace tobibox {

namespace {

const char HEX_DIGITS[] = "0123456789abcdef";

size_t hexString(char* out, const uint8_t* bytes, size_t n) {
  for (size_t i = 0; i < n; i++) {
    out[2 * i] = HEX_DIGITS[bytes[i] >> 4];
    out[2 * i + 1] = HEX_DIGITS[bytes[i] & 0x0f];
  }
  out[2 * n] = '\0';
  return 2 * n;
}

size_t finish(int n, size_t cap) {
  if (n < 0) return 0;
  return static_cast<size_t>(n) < cap ? static_cast<size_t>(n) : (cap ? cap - 1 : 0);
}

}  // namespace

// ------------------------------------------------------------ Formatierer

bool isTonieUid(UidType type, const uint8_t* uid, size_t len) {
  return type == UidType::Iso15693 && len == 8 && uid[0] == 0xe0 && uid[1] == 0x04 &&
         uid[2] == 0x03;
}

size_t formatHello(char* buf, size_t cap, const HelloInfo& h) {
  return finish(std::snprintf(buf, cap, "HELLO proto=1 fw=%s build=%s pn5180=%s", h.fw, h.build,
                              h.pn5180),
                cap);
}

size_t formatPlaced(char* buf, size_t cap, UidType type, const uint8_t* uid, size_t len,
                    uint32_t seq) {
  char hex[2 * MAX_UID_BYTES + 1];
  hexString(hex, uid, len > MAX_UID_BYTES ? MAX_UID_BYTES : len);
  return finish(std::snprintf(buf, cap, "PLACED uid=%s type=%s tonie=%d seq=%lu", hex,
                              type == UidType::Ntag ? "ntag" : "iso15693",
                              isTonieUid(type, uid, len) ? 1 : 0,
                              static_cast<unsigned long>(seq)),
                cap);
}

size_t formatLocked(char* buf, size_t cap, uint32_t seq) {
  return finish(std::snprintf(buf, cap, "LOCKED seq=%lu", static_cast<unsigned long>(seq)), cap);
}

size_t formatRemoved(char* buf, size_t cap, uint32_t seq) {
  return finish(std::snprintf(buf, cap, "REMOVED seq=%lu", static_cast<unsigned long>(seq)), cap);
}

size_t formatHb(char* buf, size_t cap, const HbFields& hb) {
  return finish(
      std::snprintf(buf, cap,
                    "HB up=%lu present=%d polls=%lu hits=%lu rejected=%lu errors=%lu cycle_ms=%u",
                    static_cast<unsigned long>(hb.up), hb.present ? 1 : 0,
                    static_cast<unsigned long>(hb.polls), static_cast<unsigned long>(hb.hits),
                    static_cast<unsigned long>(hb.rejected),
                    static_cast<unsigned long>(hb.errors), static_cast<unsigned>(hb.cycle_ms)),
      cap);
}

size_t formatErr(char* buf, size_t cap, const char* code, const char* detail) {
  char d[MAX_DETAIL_CHARS + 1];
  size_t n = 0;
  if (detail) {
    for (; detail[n] && n < MAX_DETAIL_CHARS; n++) {
      unsigned char c = static_cast<unsigned char>(detail[n]);
      d[n] = (c < 0x20 || c > 0x7e || c == '|' || c == ';') ? '_' : static_cast<char>(c);
    }
  }
  // Nach dem Kuerzen Leerzeichen an beiden Enden entfernen; leer wird "n/a".
  size_t b = 0;
  while (b < n && d[b] == ' ') b++;
  while (n > b && d[n - 1] == ' ') n--;
  if (n == b) {
    std::strcpy(d, "n/a");
  } else {
    std::memmove(d, d + b, n - b);
    d[n - b] = '\0';
  }
  return finish(std::snprintf(buf, cap, "ERR code=%s detail=%s", code, d), cap);
}

const char* cycleErrorCode(CycleError e) {
  switch (e) {
    case CycleError::Pn5180NoResponse: return "pn5180_no_response";
    case CycleError::Pn5180Timeout: return "pn5180_timeout";
    case CycleError::BadResponse: return "bad_response";
    case CycleError::UidInvalid: return "uid_invalid";
  }
  return "internal";
}

static const char* defaultDetail(CycleError e) {
  switch (e) {
    case CycleError::Pn5180NoResponse: return "pn5180 does not respond";
    case CycleError::Pn5180Timeout: return "pn5180 command timeout";
    case CycleError::BadResponse: return "unusable response";
    case CycleError::UidInvalid: return "iso14443a uid length invalid";
  }
  return "error";
}

// ------------------------------------------------------------ Befehle

CommandResult parseCommand(const char* line, size_t len) {
  if (len > 0 && line[len - 1] == '\r') len--;
  if (len == 0) return CommandResult::EmptyLine;
  if (len > MAX_LINE_CHARS) return CommandResult::TooLong;
  for (size_t i = 0; i < len; i++) {
    unsigned char c = static_cast<unsigned char>(line[i]);
    if (c < 0x20 || c > 0x7e) return CommandResult::NotAscii;
  }
  if (len == 4 && std::memcmp(line, "PING", 4) == 0) return CommandResult::Ping;
  return CommandResult::BadCommand;
}

LineAssembler::Event LineAssembler::feed(char c) {
  if (done_) {
    len_ = 0;
    done_ = false;
  }
  if (c == '\n') {
    done_ = true;
    if (overflow_) {
      overflow_ = false;
      return Event::TooLong;
    }
    buf_[len_] = '\0';
    return Event::Line;
  }
  // Platz für 200 Zeichen plus ein CR; alles darüber ist zu lang.
  if (len_ < MAX_LINE_CHARS + 1) {
    buf_[len_++] = c;
  } else {
    overflow_ = true;
  }
  return Event::None;
}

// ------------------------------------------------------------ Referenz-Parser

const char* parseReasonName(ParseReason r) {
  switch (r) {
    case ParseReason::Ok: return "ok";
    case ParseReason::EmptyLine: return "empty_line";
    case ParseReason::TooLong: return "too_long";
    case ParseReason::NotAscii: return "not_ascii";
    case ParseReason::UnknownType: return "unknown_type";
    case ParseReason::BadSyntax: return "bad_syntax";
    case ParseReason::DuplicateKey: return "duplicate_key";
    case ParseReason::MissingField: return "missing_field";
    case ParseReason::BadValue: return "bad_value";
    case ParseReason::BadUid: return "bad_uid";
    case ParseReason::UidTypeMismatch: return "uid_type_mismatch";
  }
  return "?";
}

namespace {

using std::string;

bool isDigit(char c) { return c >= '0' && c <= '9'; }
bool isLower(char c) { return c >= 'a' && c <= 'z'; }
bool isHexLower(char c) { return isDigit(c) || (c >= 'a' && c <= 'f'); }

// uint32: "0" oder [1-9][0-9]*, höchstens 10 Stellen, <= 4294967295.
bool parseUint(const string& s, uint64_t* out, uint64_t max = 4294967295ULL) {
  if (s.empty() || s.size() > 10) return false;
  if (s.size() > 1 && s[0] == '0') return false;
  uint64_t v = 0;
  for (char c : s) {
    if (!isDigit(c)) return false;
    v = v * 10 + static_cast<uint64_t>(c - '0');
  }
  if (v > max) return false;
  if (out) *out = v;
  return true;
}

bool validFw(const string& s) {
  if (s.size() > 24) return false;
  size_t p = 0;
  for (int part = 0; part < 3; part++) {
    size_t start = p;
    while (p < s.size() && isDigit(s[p])) p++;
    if (!parseUint(s.substr(start, p - start), nullptr)) return false;
    if (part < 2) {
      if (p >= s.size() || s[p] != '.') return false;
      p++;
    }
  }
  if (p == s.size()) return true;
  if (s[p] != '-' || p + 1 >= s.size()) return false;
  for (size_t i = p + 1; i < s.size(); i++) {
    char c = s[i];
    if (!(isDigit(c) || isLower(c) || (c >= 'A' && c <= 'Z') || c == '.')) return false;
  }
  return true;
}

bool validBuild(const string& s) {
  if (s == "unknown") return true;
  size_t n = s.size();
  if (n > 6 && s.compare(n - 6, 6, "-dirty") == 0) n -= 6;
  if (n < 7 || n > 12) return false;
  for (size_t i = 0; i < n; i++)
    if (!isHexLower(s[i])) return false;
  return true;
}

bool validPn5180(const string& s) {
  if (s == "unknown") return true;
  size_t dot = s.find('.');
  if (dot == string::npos) return false;
  return parseUint(s.substr(0, dot), nullptr) && parseUint(s.substr(dot + 1), nullptr);
}

bool validUidRegex(const string& s) {
  const size_t n = s.size();
  if (n != 8 && n != 14 && n != 20 && n != 16) return false;
  for (char c : s)
    if (!isHexLower(c)) return false;
  return true;
}

bool validCode(const string& s) {
  if (s.empty() || s.size() > 32 || !isLower(s[0])) return false;
  for (char c : s)
    if (!(isLower(c) || isDigit(c) || c == '_')) return false;
  return true;
}

struct LineSpec {
  const char* type;
  std::vector<const char*> keys;
};

const LineSpec* findSpec(const string& type) {
  static const LineSpec specs[] = {
      {"HELLO", {"proto", "fw", "build", "pn5180"}},
      {"PLACED", {"uid", "type", "tonie", "seq"}},
      {"LOCKED", {"seq"}},
      {"REMOVED", {"seq"}},
      {"HB", {"up", "present", "polls", "hits", "rejected", "errors", "cycle_ms"}},
      {"ERR", {"code", "detail"}},
  };
  for (const auto& s : specs)
    if (type == s.type) return &s;
  return nullptr;
}

// Prüft den Wert eines bekannten Feldes. Liefert Ok, BadValue oder BadUid.
ParseReason checkValue(const string& type, const string& key, const string& v) {
  uint64_t n = 0;
  bool ok = true;
  if (key == "proto") {
    ok = parseUint(v, &n) && n >= 1;
  } else if (key == "fw") {
    ok = validFw(v);
  } else if (key == "build") {
    ok = validBuild(v);
  } else if (key == "pn5180") {
    ok = validPn5180(v);
  } else if (key == "uid") {
    return validUidRegex(v) ? ParseReason::Ok : ParseReason::BadUid;
  } else if (key == "type") {
    ok = (v == "ntag" || v == "iso15693");
  } else if (key == "tonie" || key == "present") {
    ok = (v == "0" || v == "1");
  } else if (key == "cycle_ms") {
    ok = parseUint(v, nullptr, 65535);
  } else if (key == "code") {
    ok = validCode(v);
  } else if (key == "detail") {
    ok = v.size() >= 1 && v.size() <= MAX_DETAIL_CHARS && v.find('|') == string::npos &&
         v.find(';') == string::npos;
  } else {
    (void)type;
    ok = parseUint(v, nullptr);  // seq up polls hits rejected errors
  }
  return ok ? ParseReason::Ok : ParseReason::BadValue;
}

}  // namespace

ParseReason parseReaderLine(const std::string& raw, ParsedLine* out) {
  string line = raw;
  if (!line.empty() && line.back() == '\r') line.pop_back();
  if (line.empty()) return ParseReason::EmptyLine;
  if (line.size() > MAX_LINE_CHARS) return ParseReason::TooLong;
  for (char ch : line) {
    unsigned char c = static_cast<unsigned char>(ch);
    if (c < 0x20 || c > 0x7e) return ParseReason::NotAscii;
  }
  if (line[0] == ' ') return ParseReason::BadSyntax;

  size_t sp = line.find(' ');
  const string type = line.substr(0, sp);
  const LineSpec* spec = findSpec(type);
  if (!spec) return ParseReason::UnknownType;

  // Syntax: Wörter durch genau ein Leerzeichen, kein Leerzeichen am Ende.
  if (line.back() == ' ') return ParseReason::BadSyntax;
  std::vector<std::pair<string, string>> kv;
  size_t pos = (sp == string::npos) ? line.size() : sp + 1;
  while (pos < line.size()) {
    size_t end = line.find(' ', pos);
    const bool is_err = (type == "ERR");
    string word = line.substr(pos, end == string::npos ? string::npos : end - pos);
    if (word.empty()) return ParseReason::BadSyntax;  // doppeltes Leerzeichen
    size_t eq = word.find('=');
    if (eq == string::npos || eq == 0) return ParseReason::BadSyntax;
    string key = word.substr(0, eq);
    if (!isLower(key[0])) return ParseReason::BadSyntax;
    for (char c : key)
      if (!(isLower(c) || isDigit(c) || c == '_')) return ParseReason::BadSyntax;
    string value;
    if (is_err && key == "detail") {
      value = line.substr(pos + eq + 1);  // Rest der Zeile
      end = string::npos;
    } else {
      value = word.substr(eq + 1);
    }
    if (value.empty()) return ParseReason::BadSyntax;
    kv.emplace_back(key, value);
    if (end == string::npos) break;
    pos = end + 1;
  }

  for (size_t i = 0; i < kv.size(); i++)
    for (size_t j = i + 1; j < kv.size(); j++)
      if (kv[i].first == kv[j].first) return ParseReason::DuplicateKey;

  ParsedLine result;
  result.type = type;
  for (const char* k : spec->keys) {
    bool found = false;
    for (const auto& p : kv) {
      if (p.first == k) {
        result.fields.emplace_back(p.first, p.second);
        found = true;
        break;
      }
    }
    if (!found) return ParseReason::MissingField;
  }

  for (const auto& f : result.fields) {
    ParseReason r = checkValue(type, f.first, f.second);
    if (r != ParseReason::Ok) return r;
  }

  if (type == "PLACED") {
    const string &uid = result.fields[0].second, &t = result.fields[1].second,
                 &tonie = result.fields[2].second;
    bool ok;
    if (t == "ntag") {
      ok = (uid.size() == 8 || uid.size() == 14 || uid.size() == 20) && tonie == "0";
    } else {
      const bool prefix = uid.compare(0, 6, "e00403") == 0;
      ok = uid.size() == 16 && tonie == (prefix ? "1" : "0");
    }
    if (!ok) return ParseReason::UidTypeMismatch;
  }

  if (out) *out = result;
  return ParseReason::Ok;
}

// ------------------------------------------------------------ Protokoll-Ausgabe

Protocol::Protocol(LineSink& sink, const HelloInfo& hello, const DebounceParams& params)
    : sink_(sink), hello_(hello), deb_(params) {}

void Protocol::emitHello() {
  char buf[LINE_BUF_SIZE];
  emit(buf, formatHello(buf, sizeof buf, hello_));
}

void Protocol::start(uint32_t now_ms) {
  seq_ = 0;
  last_hb_ = now_ms;
  started_ = true;
  emitHello();
}

void Protocol::emitPlacement(const Identity& id, bool locked) {
  char buf[LINE_BUF_SIZE];
  if (locked) {
    emit(buf, formatLocked(buf, sizeof buf, seq_++));
    emit(buf, formatErr(buf, sizeof buf, "unlock_failed", "privacy mode active, password rejected"));
  } else {
    emit(buf, formatPlaced(buf, sizeof buf, id.type, id.uid, id.len, seq_++));
  }
}

void Protocol::emitDebounce(const DebounceResult& r) {
  char buf[LINE_BUF_SIZE];
  if (r.removed) emit(buf, formatRemoved(buf, sizeof buf, seq_++));
  if (r.placement == DebounceResult::Placement::Placed) emitPlacement(r.placed, false);
  if (r.placement == DebounceResult::Placement::Locked) emitPlacement(r.placed, true);
}

void Protocol::emitErrRateLimited(size_t slot, const char* code, const char* detail, uint32_t t) {
  if (err_seen_[slot] && static_cast<uint32_t>(t - err_last_[slot]) < ERR_MIN_INTERVAL_MS) return;
  err_seen_[slot] = true;
  err_last_[slot] = t;
  char buf[LINE_BUF_SIZE];
  emit(buf, formatErr(buf, sizeof buf, code, detail));
}

void Protocol::onCycle(const Reading& reading, uint32_t t, uint32_t work_ms) {
  c_.polls++;
  c_.cycle_ms = static_cast<uint16_t>(work_ms > 65535 ? 65535 : work_ms);
  if (reading.valid()) c_.hits++;
  const DebounceResult r = deb_.update(reading, t);
  if (r.rejected) c_.rejected++;
  emitDebounce(r);  // erst die Zeilen des Entprellers ...
  if (reading.kind == Reading::Kind::Error) {  // ... dann die ERR-Zeile des Fehlerzyklus
    c_.errors++;
    emitErrRateLimited(static_cast<size_t>(reading.error), cycleErrorCode(reading.error),
                       reading.detail ? reading.detail : defaultDetail(reading.error), t);
  }
}

void Protocol::onInitFailure(uint32_t t, const char* detail) {
  c_.errors++;
  emitErrRateLimited(static_cast<size_t>(CycleError::Pn5180NoResponse), "pn5180_no_response",
                     detail ? detail : "pn5180 init failed", t);
}

void Protocol::onPing() {
  seq_ = 0;
  emitHello();
  if (deb_.present()) {
    const Identity& id = deb_.current();
    emitPlacement(id, id.locked);
  }
}

void Protocol::onCommandLine(const char* line, size_t len) {
  const char* detail = nullptr;
  switch (parseCommand(line, len)) {
    case CommandResult::Ping: onPing(); return;
    case CommandResult::EmptyLine: return;
    case CommandResult::TooLong: detail = "line too long"; break;
    case CommandResult::NotAscii: detail = "non-ascii character"; break;
    case CommandResult::BadCommand: detail = "unknown command"; break;
  }
  char buf[LINE_BUF_SIZE];
  emit(buf, formatErr(buf, sizeof buf, "bad_command", detail));
}

void Protocol::onLineTooLong() {
  char buf[LINE_BUF_SIZE];
  emit(buf, formatErr(buf, sizeof buf, "bad_command", "line too long"));
}

void Protocol::tick(uint32_t now_ms, uint64_t up_ms) {
  if (!started_) return;
  if (static_cast<uint32_t>(now_ms - last_hb_) < HEARTBEAT_INTERVAL_MS) return;
  last_hb_ += HEARTBEAT_INTERVAL_MS;
  if (static_cast<uint32_t>(now_ms - last_hb_) >= HEARTBEAT_INTERVAL_MS) last_hb_ = now_ms;
  HbFields hb;
  hb.up = static_cast<uint32_t>(up_ms / 1000);  // läuft erst nach 2^32 s über
  hb.present = deb_.present() ? 1 : 0;
  hb.polls = c_.polls;
  hb.hits = c_.hits;
  hb.rejected = c_.rejected;
  hb.errors = c_.errors;
  hb.cycle_ms = c_.cycle_ms;
  char buf[LINE_BUF_SIZE];
  emit(buf, formatHb(buf, sizeof buf, hb));
}

}  // namespace tobibox
