// Einordnung von Antworten des PN5180 / der Tags (reine Logik, keine Arduino-Typen).
// Die Werte entsprechen ISO15693ErrorCode der PN5180-Bibliothek (reader.cpp prueft
// das mit static_assert).
#pragma once

#include <cstdint>

namespace tobibox {

constexpr int RC_OK = 0;
constexpr int RC_NO_CARD = -1;          // Bibliothek: keine Antwort / Zeitgrenze
constexpr int RC_UNKNOWN_ERROR = 0x0f;  // Bibliothek: readData scheiterte (Uebertragung)

// Antwort auf Inventory / Zufallszahl.
//   Ok      : Tag hat geantwortet.
//   Nothing : keine Antwort, oder das Tag setzt sein Fehlerflag (z. B. "nicht
//             unterstuetzt"): wie in tonie_test als "nichts" behandelt.
//   Error   : Uebertragungs-/Chipfehler (unbekannter Fehler) -> fehler(bad_response).
enum class RespClass : uint8_t { Ok, Nothing, Error };
RespClass classifyResponse(int rc);

// Ergebnis von disablePrivacyMode().
//   Proceed : Passwort angenommen, zweites Inventory folgt.
//   Nothing : Tag ist weg (keine Karte).
//   Error   : Uebertragungsfehler -> fehler(bad_response).
//   Locked  : Tag ist da und lehnt das Passwort ab.
// tag_still_answers: nur bei rc == RC_NO_CARD ausgewertet. Ein SLIX2 antwortet auf
// ein falsches Passwort gar nicht; deshalb entscheidet eine erneute Zufallszahl-
// Abfrage: antwortet das Tag noch, wurde das Passwort abgelehnt (gesperrt), sonst
// ist keine Figur mehr da.
enum class UnlockClass : uint8_t { Proceed, Nothing, Error, Locked };
UnlockClass classifyUnlock(int rc, bool tag_still_answers);

// Zweites Inventory nach erfolgreichem Entsperren. Proceed = Kennung gelesen.
UnlockClass classifyReinventory(int rc);

// Gesundheitsprobe: readRegister() meldet immer true. Der Wert war vorher mit
// dem Platzhalter belegt:
//   unveraendert -> Befehl lief in die Zeitgrenze (pn5180_timeout)
//   0xFFFFFFFF   -> SPI liefert nur Einsen (pn5180_no_response)
constexpr uint32_t HEALTH_SENTINEL = 0xA5A5A5A5UL;
enum class Health : uint8_t { Ok, Timeout, NoResponse };
Health classifyHealth(uint32_t value);

// Ein Zyklus, der so lange dauerte, hatte eine Zeitgrenze des Chips.
constexpr uint32_t CYCLE_TIMEOUT_SUSPECT_MS = 450;
inline bool cycleLooksTimedOut(uint32_t elapsed_ms) { return elapsed_ms >= CYCLE_TIMEOUT_SUSPECT_MS; }

}  // namespace tobibox
