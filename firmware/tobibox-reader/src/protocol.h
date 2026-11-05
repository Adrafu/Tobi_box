// Protokoll-Ausgabe der Firmware (reader-v1): formatiert Zeilen, zählt seq und
// die Herzschlag-Zähler, parst Befehle. Keine Arduino-Typen.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

#include "debounce.h"

namespace tobibox {

constexpr size_t MAX_LINE_CHARS = 200;   // ohne Zeilenende
constexpr size_t LINE_BUF_SIZE = 256;    // Puffer für eine Zeile samt Endemarke
constexpr size_t MAX_DETAIL_CHARS = 80;

// ------------------------------------------------------------ Formatierer
// Alle schreiben nach buf (ohne \n), liefern die Länge und enden mit '\0'.

struct HelloInfo {
  const char* fw = "0.0.0";
  const char* build = "unknown";
  const char* pn5180 = "unknown";
};

struct HbFields {
  uint32_t up, polls, hits, rejected, errors;
  uint8_t present;
  uint16_t cycle_ms;
};

// tonie ist 1 genau dann, wenn type=iso15693 und die Kennung mit e00403 beginnt.
bool isTonieUid(UidType type, const uint8_t* uid, size_t len);

size_t formatHello(char* buf, size_t cap, const HelloInfo& h);
size_t formatPlaced(char* buf, size_t cap, UidType type, const uint8_t* uid, size_t len,
                    uint32_t seq);
size_t formatLocked(char* buf, size_t cap, uint32_t seq);
size_t formatRemoved(char* buf, size_t cap, uint32_t seq);
size_t formatHb(char* buf, size_t cap, const HbFields& hb);
// detail wird bereinigt: unzulässige Zeichen (und '|' ';') werden '_', auf
// 80 Zeichen gekürzt, leer wird "n/a".
size_t formatErr(char* buf, size_t cap, const char* code, const char* detail);

const char* cycleErrorCode(CycleError e);

// ------------------------------------------------------------ Befehle (Box-Dienst -> Leser)

enum class CommandResult : uint8_t { Ping, EmptyLine, TooLong, NotAscii, BadCommand };
// line ohne \n; ein einzelnes \r am Ende wird entfernt.
CommandResult parseCommand(const char* line, size_t len);

// Sammelt Bytes zu Zeilen. Zeilen über 200 Zeichen werden bis zum nächsten \n
// verworfen und als TooLong gemeldet.
class LineAssembler {
 public:
  enum class Event : uint8_t { None, Line, TooLong };
  // Liefert Line, wenn ein \n ankam; die Zeile ist dann in line()/length().
  Event feed(char c);
  const char* line() const { return buf_; }
  size_t length() const { return len_; }

 private:
  char buf_[MAX_LINE_CHARS + 3] = {0};  // 200 Zeichen + CR + Endemarke
  size_t len_ = 0;
  bool overflow_ = false;
  bool done_ = false;
};

// ------------------------------------------------------------ Referenz-Parser
// Prüft Zeilen vom Leser nach reader-v1.md (Abschnitte 2, 3, 4, 11). Die Firmware
// braucht ihn nicht zur Laufzeit; er prüft die Formatierer gegen die
// Beispieldatei und dient als Gegenprobe zum Parser des Box-Dienstes.

enum class ParseReason : uint8_t {
  Ok,
  EmptyLine,
  TooLong,
  NotAscii,
  UnknownType,
  BadSyntax,
  DuplicateKey,
  MissingField,
  BadValue,
  BadUid,
  UidTypeMismatch,
};
const char* parseReasonName(ParseReason r);

struct ParsedLine {
  std::string type;
  std::vector<std::pair<std::string, std::string>> fields;  // bekannte Felder, Tabellenreihenfolge
};
ParseReason parseReaderLine(const std::string& line, ParsedLine* out);

// ------------------------------------------------------------ Protokoll-Ausgabe

class LineSink {
 public:
  virtual ~LineSink() {}
  // Eine Zeile ohne \n, nullterminiert.
  virtual void writeLine(const char* line, size_t len) = 0;
};

struct Counters {
  uint32_t polls = 0, hits = 0, rejected = 0, errors = 0;
  uint16_t cycle_ms = 0;
};

class Protocol {
 public:
  Protocol(LineSink& sink, const HelloInfo& hello,
           const DebounceParams& params = DebounceParams());

  // Beim Start: HELLO, seq beginnt bei 0; die erste HB kommt
  // HEARTBEAT_INTERVAL_MS später.
  void start(uint32_t now_ms);

  // Ein abgeschlossener Abfragezyklus. t: Zeit am Ende der Arbeit des Zyklus,
  // work_ms: Dauer der Arbeit.
  void onCycle(const Reading& reading, uint32_t t, uint32_t work_ms);

  // Fehlgeschlagener PN5180-Start: errors+1, ERR pn5180_no_response (mit
  // Ratenbegrenzung), kein Zyklus.
  void onInitFailure(uint32_t t, const char* detail = nullptr);

  // Zeile "PING": HELLO, seq=0, liegende Figur sofort erneut melden.
  void onPing();

  // Eine empfangene Zeile (ohne \n). Antwortet bei ungültigen Zeilen mit
  // ERR bad_command (außer leerer Zeile).
  void onCommandLine(const char* line, size_t len);
  void onLineTooLong();

  // Interner Fehler der Firmware (ERR internal, ratenbegrenzt wie die Zyklusfehler).
  void onInternalError(uint32_t t, const char* detail);

  // Herzschlag: ruft main regelmäßig auf. up_ms: Zeit seit Start (64 Bit).
  void tick(uint32_t now_ms, uint64_t up_ms);

  bool present() const { return deb_.present(); }
  uint32_t nextSeq() const { return seq_; }
  const Counters& counters() const { return c_; }

 private:
  void emit(const char* line, size_t len) { sink_.writeLine(line, len); }
  void emitDebounce(const DebounceResult& r);
  void emitPlacement(const Identity& id, bool locked);
  void emitErrRateLimited(size_t slot, const char* code, const char* detail, uint32_t t);
  void emitHello();

  LineSink& sink_;
  HelloInfo hello_;
  Debouncer deb_;
  uint32_t seq_ = 0;
  Counters c_;
  uint32_t last_hb_ = 0;
  bool started_ = false;
  static constexpr size_t ERR_SLOTS = CYCLE_ERROR_COUNT + 1;  // + internal
  bool err_seen_[ERR_SLOTS] = {false};
  uint32_t err_last_[ERR_SLOTS] = {0};
};

}  // namespace tobibox
