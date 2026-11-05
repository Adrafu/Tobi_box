// Native Tests der Protokoll-Ausgabe gegen docs/protocol/reader-v1-examples.txt.
//
// Die Beispieldatei wird zur Laufzeit gelesen (kein erzeugter Header). Pfad vom
// Projektordner firmware/tobibox-reader/ aus: ../../docs/protocol/reader-v1-examples.txt.
// "pio test -e native" startet das Testprogramm im Projektordner; als Rueckfall
// wird der Pfad auch relativ zu dieser Quelldatei (__FILE__) versucht.
#include <unity.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "protocol.h"
#include "timing.h"

using namespace tobibox;
using std::string;
using std::vector;

void setUp() {}
void tearDown() {}

// ------------------------------------------------------------ Hilfen

static vector<string> loadExamples() {
  const string rel = "../../docs/protocol/reader-v1-examples.txt";
  string src = __FILE__;
  string from_file;
  size_t slash = src.find_last_of("/\\");
  if (slash != string::npos) from_file = src.substr(0, slash) + "/../../" + rel;
  const string candidates[] = {rel, from_file};
  for (const string& p : candidates) {
    if (p.empty()) continue;
    std::ifstream f(p, std::ios::binary);
    if (!f) continue;
    vector<string> lines;
    string l;
    while (std::getline(f, l)) {
      if (!l.empty() && l.back() == '\r') l.pop_back();
      lines.push_back(l);
    }
    return lines;
  }
  TEST_FAIL_MESSAGE("reader-v1-examples.txt nicht gefunden");
  return {};
}

static vector<string> split(const string& s, char sep) {
  vector<string> out;
  string cur;
  for (char c : s) {
    if (c == sep) {
      out.push_back(cur);
      cur.clear();
    } else {
      cur += c;
    }
  }
  out.push_back(cur);
  return out;
}

static int hexVal(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

// Escapes der Beispieldatei: \r, \xNN, \\ .
static string unescape(const string& s) {
  string out;
  for (size_t i = 0; i < s.size(); i++) {
    if (s[i] == '\\' && i + 1 < s.size()) {
      if (s[i + 1] == 'r') {
        out += '\r';
        i++;
      } else if (s[i + 1] == '\\') {
        out += '\\';
        i++;
      } else if (s[i + 1] == 'x' && i + 3 < s.size() + 0 && hexVal(s[i + 2]) >= 0 &&
                 hexVal(s[i + 3]) >= 0) {
        out += static_cast<char>(hexVal(s[i + 2]) * 16 + hexVal(s[i + 3]));
        i += 3;
      } else {
        out += s[i];
      }
    } else {
      out += s[i];
    }
  }
  return out;
}

static vector<uint8_t> hexBytes(const string& h) {
  vector<uint8_t> b;
  for (size_t i = 0; i + 1 < h.size(); i += 2)
    b.push_back(static_cast<uint8_t>(hexVal(h[i]) * 16 + hexVal(h[i + 1])));
  return b;
}

static string joinFields(const ParsedLine& p) {
  string s = "zeile=" + p.type;
  for (const auto& f : p.fields) s += "|" + f.first + "=" + f.second;
  return s;
}

static const char* fieldOf(const ParsedLine& p, const char* key) {
  for (const auto& f : p.fields)
    if (f.first == key) return f.second.c_str();
  return "";
}

static uint32_t u32(const char* s) { return static_cast<uint32_t>(strtoull(s, nullptr, 10)); }

// Formatiert eine Zeile byte-genau aus den geparsten Feldwerten.
static string formatFrom(const ParsedLine& p) {
  char buf[LINE_BUF_SIZE];
  size_t n = 0;
  if (p.type == "HELLO") {
    HelloInfo h;
    h.fw = fieldOf(p, "fw");
    h.build = fieldOf(p, "build");
    h.pn5180 = fieldOf(p, "pn5180");
    n = formatHello(buf, sizeof buf, h);
  } else if (p.type == "PLACED") {
    vector<uint8_t> uid = hexBytes(fieldOf(p, "uid"));
    UidType t = string(fieldOf(p, "type")) == "ntag" ? UidType::Ntag : UidType::Iso15693;
    n = formatPlaced(buf, sizeof buf, t, uid.data(), uid.size(), u32(fieldOf(p, "seq")));
  } else if (p.type == "LOCKED") {
    n = formatLocked(buf, sizeof buf, u32(fieldOf(p, "seq")));
  } else if (p.type == "REMOVED") {
    n = formatRemoved(buf, sizeof buf, u32(fieldOf(p, "seq")));
  } else if (p.type == "HB") {
    HbFields hb;
    hb.up = u32(fieldOf(p, "up"));
    hb.present = static_cast<uint8_t>(u32(fieldOf(p, "present")));
    hb.polls = u32(fieldOf(p, "polls"));
    hb.hits = u32(fieldOf(p, "hits"));
    hb.rejected = u32(fieldOf(p, "rejected"));
    hb.errors = u32(fieldOf(p, "errors"));
    hb.cycle_ms = static_cast<uint16_t>(u32(fieldOf(p, "cycle_ms")));
    n = formatHb(buf, sizeof buf, hb);
  } else if (p.type == "ERR") {
    n = formatErr(buf, sizeof buf, fieldOf(p, "code"), fieldOf(p, "detail"));
  }
  return string(buf, n);
}

struct Failures {
  vector<string> list;
  int cases = 0;
  void add(const string& m) { list.push_back(m); }
  void finish(const char* what) {
    printf("%s: %d Faelle, %d Fehler\n", what, cases, static_cast<int>(list.size()));
    if (!list.empty()) {
      string all;
      for (size_t i = 0; i < list.size() && i < 5; i++) all += list[i] + "\n";
      printf("%s", all.c_str());
      TEST_FAIL_MESSAGE("Beispielfaelle fehlgeschlagen (Details oben)");
    }
    TEST_ASSERT_TRUE_MESSAGE(cases > 0, "keine Beispielfaelle gefunden");
  }
};

// ------------------------------------------------------------ Abschnitt 1

static void runSection1(const char* kind, bool formatterCheck, const char* label) {
  Failures f;
  for (const string& line : loadExamples()) {
    vector<string> parts = split(line, '|');
    if (parts.size() < 2 || parts[0] != kind) continue;
    f.cases++;
    string zeile = unescape(parts[1]);
    ParsedLine p;
    ParseReason r = parseReaderLine(zeile, &p);
    if (r != ParseReason::Ok) {
      f.add("Parser lehnt ab (" + string(parseReasonName(r)) + "): " + line);
      continue;
    }
    string expect = "zeile=" + parts[2].substr(6);
    for (size_t i = 3; i < parts.size(); i++) expect += "|" + parts[i];
    if (joinFields(p) != expect) {
      f.add("Parser-Felder: " + joinFields(p) + " statt " + expect);
      continue;
    }
    if (formatterCheck) {
      string out = formatFrom(p);
      if (out != zeile) f.add("Formatierer: '" + out + "' statt '" + zeile + "'");
    }
  }
  f.finish(label);
}

void test_section1_ok_parse_and_format() { runSection1("OK", true, "Abschnitt 1a (OK)"); }
void test_section1_okn_parse() { runSection1("OKN", false, "Abschnitt 1b (OKN)"); }

void test_section1_err_parse() {
  Failures f;
  for (const string& line : loadExamples()) {
    vector<string> parts = split(line, '|');
    if (parts.size() != 3 || parts[0] != "ERR") continue;
    f.cases++;
    string zeile = unescape(parts[1]);
    ParsedLine p;
    ParseReason r = parseReaderLine(zeile, &p);
    if (string(parseReasonName(r)) != parts[2])
      f.add("Grund " + string(parseReasonName(r)) + " statt " + parts[2] + ": " + line.substr(0, 90));
  }
  f.finish("Abschnitt 1c (ERR)");
}

// ------------------------------------------------------------ Abschnitt 2

struct VecSink : LineSink {
  vector<string> lines;
  void writeLine(const char* line, size_t len) override { lines.emplace_back(line, len); }
};

static HelloInfo testHello() {
  HelloInfo h;
  h.fw = "1.0.0";
  h.build = "a1b2c3d";
  h.pn5180 = "4.2";
  return h;
}

void test_section2_commands() {
  Failures f;
  for (const string& line : loadExamples()) {
    vector<string> parts = split(line, '|');
    if (parts.size() != 3 || (parts[0] != "CMDOK" && parts[0] != "CMDERR")) continue;
    f.cases++;
    string cmd = unescape(parts[1]);
    CommandResult r = parseCommand(cmd.data(), cmd.size());
    VecSink sink;
    Protocol proto(sink, testHello());
    proto.onCommandLine(cmd.data(), cmd.size());
    if (parts[0] == "CMDOK") {
      if (r != CommandResult::Ping) f.add("kein PING: " + line);
      if (sink.lines.size() != 1 || sink.lines[0].rfind("HELLO proto=1 ", 0) != 0)
        f.add("PING ohne HELLO: " + line);
    } else {
      const string& why = parts[2];
      CommandResult want = why == "empty_line"   ? CommandResult::EmptyLine
                           : why == "too_long"   ? CommandResult::TooLong
                           : why == "not_ascii"  ? CommandResult::NotAscii
                                                 : CommandResult::BadCommand;
      if (r != want) f.add("falscher Grund: " + line.substr(0, 90));
      if (why == "empty_line") {
        if (!sink.lines.empty()) f.add("leere Zeile muss still bleiben");
      } else if (sink.lines.size() != 1 ||
                 sink.lines[0].rfind("ERR code=bad_command detail=", 0) != 0) {
        f.add("keine bad_command-Antwort: " + line.substr(0, 90));
      } else if (parseReaderLine(sink.lines[0], nullptr) != ParseReason::Ok) {
        f.add("Antwort ungueltig: " + sink.lines[0]);
      }
    }
  }
  f.finish("Abschnitt 2 (Befehle)");
}

void test_line_assembler() {
  LineAssembler a;
  auto feedStr = [&](const string& s) {
    LineAssembler::Event e = LineAssembler::Event::None;
    for (char c : s) e = a.feed(c);
    return e;
  };
  TEST_ASSERT_TRUE(feedStr("PING\n") == LineAssembler::Event::Line);
  TEST_ASSERT_EQUAL_STRING("PING", a.line());
  TEST_ASSERT_TRUE(feedStr("PING\r\n") == LineAssembler::Event::Line);
  TEST_ASSERT_EQUAL_UINT32(5, a.length());
  TEST_ASSERT_TRUE(parseCommand(a.line(), a.length()) == CommandResult::Ping);
  // 200 Zeichen sind erlaubt, 201 nicht; danach arbeitet der Sammler normal weiter.
  TEST_ASSERT_TRUE(feedStr(string(200, 'A') + "\n") == LineAssembler::Event::Line);
  TEST_ASSERT_TRUE(parseCommand(a.line(), a.length()) == CommandResult::BadCommand);
  feedStr(string(201, 'A'));
  TEST_ASSERT_TRUE(a.feed('\n') == LineAssembler::Event::Line);
  TEST_ASSERT_TRUE(parseCommand(a.line(), a.length()) == CommandResult::TooLong);
  TEST_ASSERT_TRUE(feedStr(string(5000, 'B') + "\n") == LineAssembler::Event::TooLong);
  TEST_ASSERT_TRUE(feedStr("PING\n") == LineAssembler::Event::Line);
  TEST_ASSERT_EQUAL_STRING("PING", a.line());
}

// ------------------------------------------------------------ Abschnitt 3

static bool wildcardMatch(const string& pat, const string& act) {
  size_t i = 0, j = 0;
  while (i < pat.size()) {
    if (pat[i] == '*') {
      i++;
      // '*' steht fuer einen ganzen Feldwert: bis zum naechsten Leerzeichen
      // (oder bis zum Ende, wenn das Muster hier endet, z. B. detail=*).
      if (i >= pat.size()) {
        if (j >= act.size()) return false;  // Feldwert darf nicht leer sein
        return true;
      }
      size_t start = j;
      while (j < act.size() && act[j] != pat[i]) j++;
      if (j == start) return false;
    } else {
      if (j >= act.size() || act[j] != pat[i]) return false;
      i++;
      j++;
    }
  }
  return j == act.size();
}

static CycleError errorFromName(const string& n, bool* ok) {
  *ok = true;
  if (n == "pn5180_no_response") return CycleError::Pn5180NoResponse;
  if (n == "pn5180_timeout") return CycleError::Pn5180Timeout;
  if (n == "bad_response") return CycleError::BadResponse;
  if (n == "uid_invalid") return CycleError::UidInvalid;
  *ok = false;
  return CycleError::Pn5180NoResponse;
}

struct Sequence {
  string name;
  DebounceParams params;
  vector<vector<string>> steps;  // t, eingabe, ausgabe
  string count;
};

static string runSequence(const Sequence& s, int* stepCount) {
  VecSink sink;
  Protocol proto(sink, testHello(), s.params);
  proto.start(0);
  sink.lines.clear();  // HELLO beim Start gehoert nicht zu den Schritten
  for (const auto& st : s.steps) {
    (*stepCount)++;
    const uint32_t t = static_cast<uint32_t>(strtoull(st[0].c_str(), nullptr, 10));
    const string& in = st[1];
    sink.lines.clear();
    if (in == "PING") {
      proto.onCommandLine("PING", 4);
    } else if (in == "nichts") {
      proto.onCycle(Reading::nothing(), t, 50);
    } else if (in == "gesperrt") {
      proto.onCycle(Reading::locked(), t, 50);
    } else if (in.rfind("uid:", 0) == 0) {
      vector<string> p = split(in, ':');
      vector<uint8_t> b = hexBytes(p[2]);
      proto.onCycle(Reading::tag(p[1] == "ntag" ? UidType::Ntag : UidType::Iso15693, b.data(),
                                 b.size()),
                    t, 50);
    } else if (in.rfind("fehler:", 0) == 0) {
      bool ok;
      CycleError e = errorFromName(in.substr(7), &ok);
      if (!ok) return "unbekannter Fehlercode in " + in;
      proto.onCycle(Reading::failure(e), t, 50);
    } else {
      return "unbekannte Eingabe " + in;
    }
    // erwartete Ausgabe
    vector<string> want;
    if (st[2] != "-") want = split(st[2], ';');
    if (want.size() != sink.lines.size()) {
      string got;
      for (auto& l : sink.lines) got += "[" + l + "]";
      return "t=" + st[0] + " " + in + ": erwartet " + st[2] + " erhalten " + got;
    }
    for (size_t i = 0; i < want.size(); i++) {
      if (!wildcardMatch(want[i], sink.lines[i]))
        return "t=" + st[0] + " " + in + ": erwartet '" + want[i] + "' erhalten '" +
               sink.lines[i] + "'";
      if (parseReaderLine(sink.lines[i], nullptr) != ParseReason::Ok)
        return "t=" + st[0] + ": Zeile vom Parser abgelehnt: " + sink.lines[i];
    }
  }
  // COUNT
  vector<string> c = split(s.count, '|');
  std::map<string, string> kv;
  for (size_t i = 1; i < c.size(); i++) {
    size_t eq = c[i].find('=');
    kv[c[i].substr(0, eq)] = c[i].substr(eq + 1);
  }
  const Counters& k = proto.counters();
  auto check = [&](const char* key, uint32_t got) -> string {
    if (u32(kv[key].c_str()) != got)
      return string(key) + " erwartet " + kv[key] + " erhalten " + std::to_string(got);
    return "";
  };
  string e;
  if ((e = check("polls", k.polls)).size()) return e;
  if ((e = check("hits", k.hits)).size()) return e;
  if ((e = check("rejected", k.rejected)).size()) return e;
  if ((e = check("errors", k.errors)).size()) return e;
  if ((e = check("present", proto.present() ? 1 : 0)).size()) return e;
  // Die Zaehler muessen die Regeln aus dem Vertrag einhalten.
  if (k.hits + k.errors > k.polls) return "hits + errors > polls";
  if (k.rejected > k.hits) return "rejected > hits";
  return "";
}

void test_section3_sequences() {
  Failures f;
  int steps = 0;
  Sequence cur;
  bool open = false;
  for (const string& line : loadExamples()) {
    if (line.empty() || line[0] == '#') continue;
    vector<string> p = split(line, '|');
    if (p[0] == "SEQ") {
      cur = Sequence();
      cur.name = p[1];
      open = true;
    } else if (p[0] == "PARAM" && open) {
      cur.params = DebounceParams(u32(p[1].substr(p[1].find('=') + 1).c_str()),
                                  u32(p[2].substr(p[2].find('=') + 1).c_str()),
                                  u32(p[3].substr(p[3].find('=') + 1).c_str()));
    } else if (p[0] == "STEP" && open) {
      cur.steps.push_back({p[1], p[2], p[3]});
    } else if (p[0] == "COUNT" && open) {
      cur.count = line;
    } else if (p[0] == "END" && open) {
      f.cases++;
      string e = runSequence(cur, &steps);
      if (!e.empty()) f.add("Ablauf '" + cur.name + "': " + e);
      open = false;
    }
  }
  printf("Abschnitt 3: %d Schritte\n", steps);
  f.finish("Abschnitt 3 (Ablaeufe)");
}

// ------------------------------------------------------------ Ergaenzende Faelle

void test_heartbeat_timing_and_fields() {
  VecSink sink;
  Protocol proto(sink, testHello());
  proto.start(1000);
  TEST_ASSERT_EQUAL_UINT32(1, sink.lines.size());
  proto.tick(2999, 1999);  // noch nicht faellig
  TEST_ASSERT_EQUAL_UINT32(1, sink.lines.size());
  proto.tick(3000, 2000);
  TEST_ASSERT_EQUAL_UINT32(2, sink.lines.size());
  TEST_ASSERT_EQUAL_STRING("HB up=2 present=0 polls=0 hits=0 rejected=0 errors=0 cycle_ms=0",
                           sink.lines[1].c_str());
  proto.onCycle(Reading::nothing(), 3100, 70000);  // cycle_ms wird auf 65535 begrenzt
  proto.tick(5000, 4000);
  TEST_ASSERT_EQUAL_STRING("HB up=4 present=0 polls=1 hits=0 rejected=0 errors=0 cycle_ms=65535",
                           sink.lines[2].c_str());
  // up aus 64-Bit-Zeit: laeuft nicht nach 2^32 ms ueber
  proto.tick(7000, 6000ULL + 4294967296ULL);
  TEST_ASSERT_TRUE(sink.lines[3].rfind("HB up=4294973 ", 0) == 0);
  // Zeitueberlauf der 32-Bit-Uhr: naechster HB 2000 ms spaeter, auch ueber 2^32
  VecSink s2;
  Protocol p2(s2, testHello());
  p2.start(4294966296U);  // 1000 ms vor dem Ueberlauf
  p2.tick(4294966296U + 1999U, 1999);
  TEST_ASSERT_EQUAL_UINT32(1, s2.lines.size());
  p2.tick(4294966296U + 2000U, 2000);  // = 1000 nach Ueberlauf
  TEST_ASSERT_EQUAL_UINT32(2, s2.lines.size());
}

void test_init_failure_counts_and_rate_limit() {
  VecSink sink;
  Protocol proto(sink, testHello());
  proto.start(0);
  proto.onInitFailure(0);
  proto.onInitFailure(1000);
  proto.onInitFailure(2000);
  TEST_ASSERT_EQUAL_UINT32(3, sink.lines.size());  // HELLO + 2 ERR
  TEST_ASSERT_TRUE(sink.lines[1].rfind("ERR code=pn5180_no_response detail=", 0) == 0);
  TEST_ASSERT_EQUAL_UINT32(3, proto.counters().errors);
  TEST_ASSERT_EQUAL_UINT32(0, proto.counters().polls);  // kein Zyklus
}

void test_err_detail_sanitized() {
  char buf[LINE_BUF_SIZE];
  size_t n = formatErr(buf, sizeof buf, "internal", "a|b;c\tdé");
  TEST_ASSERT_EQUAL_STRING("ERR code=internal detail=a_b_c_d__", buf);
  TEST_ASSERT_EQUAL_UINT32(strlen(buf), n);
  n = formatErr(buf, sizeof buf, "internal", string(200, 'x').c_str());
  TEST_ASSERT_EQUAL_UINT32(strlen("ERR code=internal detail=") + 80, n);
  formatErr(buf, sizeof buf, "internal", "");
  TEST_ASSERT_EQUAL_STRING("ERR code=internal detail=n/a", buf);
}

void test_every_line_within_limit() {
  char buf[LINE_BUF_SIZE];
  uint8_t uid[10] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff};
  TEST_ASSERT_TRUE(formatPlaced(buf, sizeof buf, UidType::Ntag, uid, 10, 4294967295U) <=
                   MAX_LINE_CHARS);
  HbFields hb = {4294967295U, 4294967295U, 4294967295U, 4294967295U, 4294967295U, 1, 65535};
  TEST_ASSERT_TRUE(formatHb(buf, sizeof buf, hb) <= MAX_LINE_CHARS);
}

// ------------------------------------------------------------ Nachtraege (Review)

static const uint8_t NTAG_A[4] = {0x04, 0xa1, 0xb2, 0xc3};

static void placeA(Protocol& proto, uint32_t t) {
  proto.onCycle(Reading::tag(UidType::Ntag, NTAG_A, 4), t, 10);
  proto.onCycle(Reading::tag(UidType::Ntag, NTAG_A, 4), t + 200, 10);
}

void test_err_detail_trim() {
  char buf[LINE_BUF_SIZE];
  formatErr(buf, sizeof buf, "internal", "   ");
  TEST_ASSERT_EQUAL_STRING("ERR code=internal detail=n/a", buf);
  formatErr(buf, sizeof buf, "internal", "  ab c  ");
  TEST_ASSERT_EQUAL_STRING("ERR code=internal detail=ab c", buf);
  // 79 Zeichen, dann ein Leerzeichen an Stelle 80 und Text danach: nach dem
  // Kuerzen auf 80 bleibt am Ende ein Leerzeichen, das entfernt wird.
  string d = string(79, 'x') + " tail";
  formatErr(buf, sizeof buf, "internal", d.c_str());
  TEST_ASSERT_EQUAL_STRING(("ERR code=internal detail=" + string(79, 'x')).c_str(), buf);
  // 80 Leerzeichen und danach Text: nach dem Kuerzen nur Leerzeichen -> n/a
  d = string(80, ' ') + "text";
  formatErr(buf, sizeof buf, "internal", d.c_str());
  TEST_ASSERT_EQUAL_STRING("ERR code=internal detail=n/a", buf);
  formatErr(buf, sizeof buf, "internal", nullptr);
  TEST_ASSERT_EQUAL_STRING("ERR code=internal detail=n/a", buf);
}

void test_heartbeat_catch_up_after_missed_intervals() {
  VecSink sink;
  Protocol proto(sink, testHello());
  proto.start(0);
  // 21 s ohne tick(): genau ein HB, kein Stau von zehn Zeilen
  proto.tick(21000, 21000);
  TEST_ASSERT_EQUAL_UINT32(2, sink.lines.size());
  proto.tick(22999, 22999);  // 2000 ms nach dem verspaeteten HB noch nicht
  TEST_ASSERT_EQUAL_UINT32(2, sink.lines.size());
  proto.tick(23000, 23000);
  TEST_ASSERT_EQUAL_UINT32(3, sink.lines.size());
  // knapp ueber zwei Intervalle verspaetet: ein HB, danach wieder im Takt
  VecSink s2;
  Protocol p2(s2, testHello());
  p2.start(0);
  p2.tick(4500, 4500);
  TEST_ASSERT_EQUAL_UINT32(2, s2.lines.size());
  p2.tick(6499, 6499);
  TEST_ASSERT_EQUAL_UINT32(2, s2.lines.size());
  p2.tick(6500, 6500);
  TEST_ASSERT_EQUAL_UINT32(3, s2.lines.size());
}

void test_up_from_64bit_base() {
  VecSink sink;
  Protocol proto(sink, testHello());
  proto.start(0);
  proto.tick(2000, 100000000000ULL);  // 1e11 ms, laeuft als 32-Bit-ms laengst ueber
  TEST_ASSERT_TRUE(sink.lines[1].rfind("HB up=100000000 ", 0) == 0);
  proto.tick(4000, 4294967295000ULL);
  TEST_ASSERT_TRUE(sink.lines[2].rfind("HB up=4294967295 ", 0) == 0);
}

void test_err_rate_limit_near_wrap() {
  VecSink sink;
  Protocol proto(sink, testHello());
  proto.start(0);
  const Reading e = Reading::failure(CycleError::Pn5180Timeout, "x");
  const uint32_t t0 = 4294967000U;
  proto.onCycle(e, t0, 5);
  TEST_ASSERT_EQUAL_UINT32(2, sink.lines.size());
  proto.onCycle(e, t0 + 1999U, 5);  // = 1702 nach dem Ueberlauf: unterdrueckt
  TEST_ASSERT_EQUAL_UINT32(2, sink.lines.size());
  TEST_ASSERT_EQUAL_UINT32(2, proto.counters().errors);  // zaehlt trotzdem
  proto.onCycle(e, t0 + 2000U, 5);  // genau 2000: wird geschrieben
  TEST_ASSERT_EQUAL_UINT32(3, sink.lines.size());
  proto.onCycle(e, t0 + 3999U, 5);
  TEST_ASSERT_EQUAL_UINT32(3, sink.lines.size());
  // anderer Code hat eigene Grenze
  proto.onCycle(Reading::failure(CycleError::BadResponse, "y"), t0 + 4000U, 5);
  TEST_ASSERT_EQUAL_UINT32(4, sink.lines.size());
}

void test_seq_overflow() {
  VecSink sink;
  Protocol proto(sink, testHello());
  proto.start(0);
  proto.setSeqForTest(4294967295U);
  sink.lines.clear();
  placeA(proto, 0);
  TEST_ASSERT_EQUAL_UINT32(1, sink.lines.size());
  TEST_ASSERT_TRUE(sink.lines[0].rfind("PLACED uid=04a1b2c3 type=ntag tonie=0 seq=4294967295", 0) == 0);
  TEST_ASSERT_EQUAL_UINT32(0, proto.nextSeq());
  proto.onCycle(Reading::nothing(), 400, 5);
  proto.onCycle(Reading::nothing(), 1400, 5);  // 1200 ms seit der letzten Lesung
  TEST_ASSERT_EQUAL_UINT32(2, sink.lines.size());
  TEST_ASSERT_EQUAL_STRING("REMOVED seq=0", sink.lines[1].c_str());
  ParsedLine pl;
  TEST_ASSERT_TRUE(parseReaderLine(sink.lines[1], &pl) == ParseReason::Ok);
}

void test_removed_and_err_same_step() {
  VecSink sink;
  Protocol proto(sink, testHello());
  proto.start(0);
  placeA(proto, 0);  // PLACED seq=0, letzte Lesung bei 200
  proto.onCycle(Reading::nothing(), 400, 5);
  sink.lines.clear();
  // 1300 ms Luecke und ein Fehlerzyklus: REMOVED (Entpreller) vor ERR (Regel 6)
  proto.onCycle(Reading::failure(CycleError::Pn5180Timeout, "rf field did not start"), 1500, 5);
  TEST_ASSERT_EQUAL_UINT32(2, sink.lines.size());
  TEST_ASSERT_EQUAL_STRING("REMOVED seq=1", sink.lines[0].c_str());
  TEST_ASSERT_EQUAL_STRING("ERR code=pn5180_timeout detail=rf field did not start",
                           sink.lines[1].c_str());
  TEST_ASSERT_EQUAL_UINT32(1, proto.counters().errors);
}

void test_line_assembler_200_plus_cr() {
  LineAssembler a;
  LineAssembler::Event e = LineAssembler::Event::None;
  for (char c : string(200, 'A') + "\r\n") e = a.feed(c);
  TEST_ASSERT_TRUE(e == LineAssembler::Event::Line);
  TEST_ASSERT_EQUAL_UINT32(201, a.length());
  // CR wird entfernt, 200 Zeichen sind erlaubt: unbekannter Befehl, nicht zu lang
  TEST_ASSERT_TRUE(parseCommand(a.line(), a.length()) == CommandResult::BadCommand);
  // 201 Zeichen plus CR sind zu lang
  for (char c : string(201, 'A') + "\r\n") e = a.feed(c);
  TEST_ASSERT_TRUE(e == LineAssembler::Event::TooLong);
}

void test_hello_after_start_retry() {
  char version[16] = "unknown";
  HelloInfo h = testHello();
  h.pn5180 = version;  // wie in main.cpp: zeigt auf den Puffer, den probe() fuellt
  VecSink sink;
  Protocol proto(sink, h);
  proto.start(0);
  TEST_ASSERT_EQUAL_STRING("HELLO proto=1 fw=1.0.0 build=a1b2c3d pn5180=unknown",
                           sink.lines[0].c_str());
  proto.onInitFailure(0);
  proto.onInitFailure(5000);
  snprintf(version, sizeof version, "4.2");  // erfolgreicher Wiederholversuch
  sink.lines.clear();
  proto.onCommandLine("PING", 4);
  TEST_ASSERT_EQUAL_UINT32(1, sink.lines.size());
  TEST_ASSERT_EQUAL_STRING("HELLO proto=1 fw=1.0.0 build=a1b2c3d pn5180=4.2", sink.lines[0].c_str());
  TEST_ASSERT_EQUAL_UINT32(2, proto.counters().errors);
  TEST_ASSERT_EQUAL_UINT32(0, proto.counters().polls);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_section1_ok_parse_and_format);
  RUN_TEST(test_section1_okn_parse);
  RUN_TEST(test_section1_err_parse);
  RUN_TEST(test_section2_commands);
  RUN_TEST(test_line_assembler);
  RUN_TEST(test_section3_sequences);
  RUN_TEST(test_heartbeat_timing_and_fields);
  RUN_TEST(test_init_failure_counts_and_rate_limit);
  RUN_TEST(test_err_detail_sanitized);
  RUN_TEST(test_every_line_within_limit);
  RUN_TEST(test_err_detail_trim);
  RUN_TEST(test_heartbeat_catch_up_after_missed_intervals);
  RUN_TEST(test_up_from_64bit_base);
  RUN_TEST(test_err_rate_limit_near_wrap);
  RUN_TEST(test_seq_overflow);
  RUN_TEST(test_removed_and_err_same_step);
  RUN_TEST(test_line_assembler_200_plus_cr);
  RUN_TEST(test_hello_after_start_retry);
  return UNITY_END();
}
