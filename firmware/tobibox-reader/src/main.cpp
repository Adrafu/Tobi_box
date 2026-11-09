// Tobi Box – tobibox-reader: Leser -> Entpreller -> Protokoll (reader-v1).
// Auf die USB-Serielle gehen nur Protokollzeilen (docs/protocol/reader-v1.md).
#include <Arduino.h>
#include <esp_timer.h>

#include "protocol.h"
#include "reader.h"
#include "timing.h"

#ifndef FW_VERSION
#define FW_VERSION "1.0.0"
#endif
#ifndef BUILD_GIT
#define BUILD_GIT "unknown"
#endif

using namespace tobibox;

namespace {

// Schreibt jede Zeile mit einem einzigen write(); bei setTxTimeoutMs(0) wird
// verworfen, wenn niemand liest (zeigt sich als Luecke in seq).
class SerialSink : public LineSink {
 public:
  void writeLine(const char* line, size_t len) override {
    char buf[LINE_BUF_SIZE + 1];
    if (len > LINE_BUF_SIZE - 1) len = LINE_BUF_SIZE - 1;
    memcpy(buf, line, len);
    buf[len] = '\n';
    Serial.write(reinterpret_cast<const uint8_t*>(buf), len + 1);
  }
};

SerialSink sink;
Reader reader;
char pnVersion[16] = "unknown";
Protocol* protocol = nullptr;
LineAssembler assembler;

bool readerReady = false;
uint32_t nextInitTry = 0;
uint32_t nextPoll = 0;

// Millisekunden seit dem Start, 64 Bit (laeuft praktisch nie ueber).
inline uint64_t uptimeMs() { return static_cast<uint64_t>(esp_timer_get_time()) / 1000ULL; }

inline bool due(uint32_t now, uint32_t when) { return static_cast<int32_t>(now - when) >= 0; }

void serviceInput() {
  while (Serial.available() > 0) {
    int c = Serial.read();
    if (c < 0) break;
    switch (assembler.feed(static_cast<char>(c))) {
      case LineAssembler::Event::Line: protocol->onCommandLine(assembler.line(), assembler.length()); break;
      case LineAssembler::Event::TooLong: protocol->onLineTooLong(); break;
      case LineAssembler::Event::None: break;
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);  // nie blockieren, wenn niemand liest (HWCDC)

  reader.beginBus();
  readerReady = reader.probe(pnVersion, sizeof pnVersion);

  HelloInfo hello;
  hello.fw = FW_VERSION;
  hello.build = BUILD_GIT;
  hello.pn5180 = pnVersion;
  static Protocol proto(sink, hello);
  protocol = &proto;

  const uint32_t now = millis();
  proto.start(now);
  if (!readerReady) {
    proto.onInitFailure(now, "product version unreadable or 0xFF");
    nextInitTry = now + PN5180_INIT_RETRY_MS;
  }
  nextPoll = now;
}

void loop() {
  const uint32_t now = millis();
  serviceInput();

  if (!readerReady) {
    // Startversuch wiederholen; Herzschlaege laufen weiter (present=0).
    if (due(now, nextInitTry)) {
      // Schreibt die Version in pnVersion, auf die HelloInfo zeigt: spaetere
      // HELLO-Zeilen (PING) tragen die echte Version.
      if (reader.probe(pnVersion, sizeof pnVersion)) {
        readerReady = true;
        nextPoll = now;
      } else {
        protocol->onInitFailure(millis(), "product version unreadable or 0xFF");
        nextInitTry = now + PN5180_INIT_RETRY_MS;
      }
    }
  } else if (due(now, nextPoll)) {
    const uint32_t t0 = now;
    const Reading r = reader.poll();
    const uint32_t t1 = millis();
    // Einmalig nach dem Start: Laenge der ersten gueltigen Inventory-Antwort
    // (10 oder 12 laut classify.h). Zeile "DBG inv_len=<n>", vom Dienst ignoriert.
    uint8_t invLen = 0;
    if (reader.takeFirstInventoryLen(&invLen)) protocol->onDebug("inv_len", invLen);
    protocol->onCycle(r, t1, t1 - t0);
    nextPoll = t0 + POLL_PERIOD_MS;  // Beginn zu Beginn; war die Arbeit laenger, sofort weiter
  }

  protocol->tick(millis(), uptimeMs());
  delay(1);
}
