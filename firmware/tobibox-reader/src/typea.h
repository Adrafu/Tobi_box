// Aktivierung ISO 14443A (NTAG) mit eigener Pruefung der Antworten.
//
// Ersetzt activateTypeA()/readCardSerial() der PN5180-Bibliothek (Commit
// 69ec032), die weder Fehlerbits in RX_STATUS noch die Laenge der Antworten
// noch das BCC der Kennung pruefen und nach dem Select das SAK lesen, ohne
// zu wissen, ob das Tag geantwortet hat. Eine gestoerte Antikollisions-Antwort
// konnte so als falsche Kennung durchgehen.
//
// Die Schrittfolge der Chip-Befehle ist die der Bibliothek. Abweichungen:
//   1. Nach REQA, nach jeder Antikollision und nach jedem Select wird
//      RX_STATUS gelesen und geprueft (Anzahl Bytes, Fehlerbits).
//   2. Vor dem Lesen des SAK wartet die Firmware 5 ms, wie die Bibliothek
//      es vor der Antikollisions-Antwort tut (sonst koennte RX_STATUS noch 0
//      zeigen).
//   3. Die zweite Antikollision wartet ebenfalls 5 ms.
// Die Schrittfolge steht im Test test_typea (Ablaufprotokoll); ein Eingriff
// in die Reihenfolge faellt dort auf.
//
// Die Vorlage arbeitet auf einem "Chip" mit den Operationen unten. Auf dem
// ESP32 ist das ein Adapter um PN5180ISO14443 (reader.cpp), im Test ein Fake.
// Keine Arduino-Typen.
#pragma once

#include <cstdint>
#include <cstdio>
#include <cstring>

#include "classify.h"
#include "debounce.h"

namespace tobibox {

struct TypeAResult {
  enum class Kind : uint8_t {
    Nothing,  // keine Karte, oder ein Chip-Befehl scheiterte (wie die Bibliothek)
    Uid,      // sichere Kennung in uid[0..len-1], MSB zuerst
    Error,    // Antwort verworfen (Fehlerbit, Laenge, BCC, SAK); error + detail gesetzt
  };
  Kind kind = Kind::Nothing;
  uint8_t len = 0;
  uint8_t uid[MAX_UID_BYTES] = {0};
  CycleError error = CycleError::BadResponse;  // nur bei Kind::Error
  char detail[40] = "";                        // nur bei Kind::Error
};

// Chip-Operationen (Zuordnung zur Bibliothek in Klammern):
//   bool loadRfConfig()                 loadRFConfig(0x00, 0x80)
//   void rfOn()                         setRF_on() (Ergebnis wird ignoriert)
//   void delayMs(uint32_t)              delay()
//   uint32_t nowMs()                    millis()
//   bool cryptoOff()                    SYSTEM_CONFIG und 0xFFFFFFBF
//   bool crcRx(bool on)                 CRC_RX_CONFIG Bit 0
//   bool crcTx(bool on)                 CRC_TX_CONFIG Bit 0
//   bool idle()                         SYSTEM_CONFIG und 0xFFFFFFF8
//   bool transceive()                   SYSTEM_CONFIG oder 0x00000003
//   bool inWaitTransmit()               getTransceiveState() == WaitTransmit
//   bool clearIrq()                     clearIRQStatus(0xFFFFFFFF)
//   bool send(const uint8_t*, int n, uint8_t validBits)   sendData()
//   uint32_t rxStatus()                 readRegister(RX_STATUS)
//   bool read(int n, uint8_t* buf)      readData()
namespace typea_detail {

template <class R>
void fail(R& r, const char* what, unsigned n, bool withNumber) {
  r.kind = TypeAResult::Kind::Error;
  r.error = CycleError::BadResponse;
  if (withNumber)
    snprintf(r.detail, sizeof r.detail, "%s length=%u", what, n);
  else
    snprintf(r.detail, sizeof r.detail, "%s", what);
}

}  // namespace typea_detail

// Prueft die Antwort des letzten Befehls. true = weiter; sonst steht in r das
// Ergebnis (Nothing oder Error).
template <class Chip>
bool typeaCheckRx(Chip& c, size_t expected, const char* what, TypeAResult& r) {
  const uint32_t rx = c.rxStatus();
  switch (checkTypeAFrame(rx, expected)) {
    case TypeAFrame::Ok: return true;
    case TypeAFrame::Nothing: r.kind = TypeAResult::Kind::Nothing; return false;
    case TypeAFrame::RxError: {
      char what_bit[32];
      snprintf(what_bit, sizeof what_bit, "%s rx error bit", what);
      typea_detail::fail(r, what_bit, 0, false);
      return false;
    }
    case TypeAFrame::BadLength:
      typea_detail::fail(r, what, static_cast<unsigned>(rx & RX_LEN_MASK), true);
      return false;
  }
  return false;
}

template <class Chip>
TypeAResult activateTypeAChecked(Chip& c) {
  TypeAResult r;  // Nothing
  uint8_t cmd[7] = {0};
  uint8_t atqa[2] = {0};
  uint8_t sak = 0;

  if (!c.loadRfConfig()) return r;
  c.rfOn();
  c.delayMs(10);  // HF-Feld hochfahren
  if (!c.cryptoOff()) return r;
  if (!c.crcRx(false)) return r;
  if (!c.crcTx(false)) return r;
  if (!c.idle()) return r;
  if (!c.transceive()) return r;
  if (!c.inWaitTransmit()) return r;
  c.clearIrq();

  // REQA, 7 Bit
  cmd[0] = 0x26;
  if (!c.send(cmd, 1, 0x07)) return r;
  c.delayMs(10);
  if (!typeaCheckRx(c, 2, "reqa", r)) return r;
  if (!c.read(2, atqa)) return r;

  const uint32_t waitStart = c.nowMs();
  while (!c.inWaitTransmit()) {
    c.delayMs(1);
    if (c.nowMs() - waitStart > 200) return r;
  }
  c.clearIrq();

  // Antikollision Ebene 1
  cmd[0] = 0x93;
  cmd[1] = 0x20;
  if (!c.send(cmd, 2, 0x00)) return r;
  c.delayMs(5);
  if (!typeaCheckRx(c, 5, "anticoll1", r)) return r;
  if (!c.read(5, cmd + 2)) return r;
  if (!typeABccValid(cmd + 2)) {
    typea_detail::fail(r, "anticoll1 bcc", 0, false);
    return r;
  }
  uint8_t level1[4];
  memcpy(level1, cmd + 2, 4);

  if (!c.crcRx(true)) return r;
  if (!c.crcTx(true)) return r;

  // Select Ebene 1 (Kennung und BCC stehen schon in cmd[2..6])
  cmd[0] = 0x93;
  cmd[1] = 0x70;
  if (!c.send(cmd, 7, 0x00)) return r;
  c.delayMs(5);
  if (!typeaCheckRx(c, 1, "select1", r)) return r;
  if (!c.read(1, &sak)) return r;
  if (!typeASakConsistent(level1[0], sak)) {
    typea_detail::fail(r, "sak1 cascade mismatch", 0, false);
    return r;
  }

  if ((sak & 0x04) == 0) {
    memcpy(r.uid, level1, 4);
    r.len = 4;
  } else {
    // 7 Byte: Ebene 1 ist 0x88 (Cascade Tag) + drei Kennungs-Bytes
    if (!c.crcRx(false)) return r;
    if (!c.crcTx(false)) return r;
    cmd[0] = 0x95;
    cmd[1] = 0x20;
    if (!c.send(cmd, 2, 0x00)) return r;
    c.delayMs(5);
    if (!typeaCheckRx(c, 5, "anticoll2", r)) return r;
    if (!c.read(5, cmd + 2)) return r;
    if (!typeABccValid(cmd + 2)) {
      typea_detail::fail(r, "anticoll2 bcc", 0, false);
      return r;
    }
    uint8_t level2[4];
    memcpy(level2, cmd + 2, 4);
    if (!c.crcRx(true)) return r;
    if (!c.crcTx(true)) return r;
    cmd[0] = 0x95;
    cmd[1] = 0x70;
    if (!c.send(cmd, 7, 0x00)) return r;
    c.delayMs(5);
    if (!typeaCheckRx(c, 1, "select2", r)) return r;
    if (!c.read(1, &sak)) return r;
    if (sak & 0x04) {
      // Kennung mit 10 Byte (dritte Ebene): nicht unterstuetzt
      r.kind = TypeAResult::Kind::Error;
      r.error = CycleError::UidInvalid;
      snprintf(r.detail, sizeof r.detail, "uid longer than 7 byte");
      return r;
    }
    memcpy(r.uid, level1 + 1, 3);
    memcpy(r.uid + 3, level2, 4);
    r.len = 7;
  }

  // Wie readCardSerial(): offensichtlich ungueltige Kennungen sind "keine Karte".
  if ((atqa[0] == 0xFF && atqa[1] == 0xFF) || !typeAUidPlausible(r.uid, r.len)) {
    r = TypeAResult();
    return r;
  }
  r.kind = TypeAResult::Kind::Uid;
  return r;
}

}  // namespace tobibox
