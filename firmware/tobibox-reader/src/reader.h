// Leser (Hardware): ein Abfragezyklus liefert genau ein Ergebnis
// (nichts / uid / gesperrt / fehler). Nur auf dem ESP32 gebaut.
#pragma once

#include <Arduino.h>
#include <PN5180ISO14443.h>
#include <PN5180ISO15693.h>

#include "config.h"
#include "debounce.h"

namespace tobibox {

class Reader {
 public:
  Reader();

  // Einmalig: SPI starten, Befehls-Zeitgrenze setzen.
  void beginBus();

  // PN5180 zuruecksetzen und pruefen (Produktversion lesen). Bei Erfolg wird
  // version als "<major>.<minor>" der PN5180-Firmware gesetzt. Bei Misserfolg
  // false; version bleibt "unknown".
  bool probe(char* version, size_t cap);

  // Ein Abfragezyklus. Danach ist das HF-Feld aus.
  Reading poll();

 private:
  Reading readIso14443();
  Reading readIso15693();
  Reading pollProtocols();

  PN5180ISO14443 nfc14443_;
  PN5180ISO15693 nfc15693_;
  bool lastWasNtag_ = false;  // zuletzt gelesenes Protokoll zuerst abfragen
};

}  // namespace tobibox
