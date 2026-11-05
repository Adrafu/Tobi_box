// Tobi Box – Zeitkonstanten der Firmware tobibox-reader.
// Eingecheckt, ohne Geheimnisse; Tests und CI brauchen keine config.h.
// Die Namen sind verbindlich (docs/protocol/reader-v1.md, Abschnitt 10).
#pragma once

#include <cstdint>

// Abfragezyklus, Beginn zu Beginn.
constexpr uint32_t POLL_PERIOD_MS = 200;
// Gleiche Lesungen in Folge für PLACED, LOCKED und Wechsel
// (3, falls die Messung in Stufe 1 zeigt, dass 2 nicht reichen).
constexpr uint32_t CONFIRM_READS = 2;
// REMOVED nach so langer Zeit ohne gültige Lesung der liegenden Figur,
// wenn dazwischen ein "nichts" oder eine fremde Lesung kam.
constexpr uint32_t REMOVE_AFTER_MS = 1100;
// REMOVED bei ununterbrochenen Lesefehlern erst nach so langer Zeit seit der
// letzten gültigen Lesung.
constexpr uint32_t ERROR_HOLD_MS = 5000;
// Abstand der HB-Zeilen.
constexpr uint32_t HEARTBEAT_INTERVAL_MS = 2000;
// Mindestabstand gleicher ERR-Codes.
constexpr uint32_t ERR_MIN_INTERVAL_MS = 2000;
// Abstand der Startversuche, wenn der PN5180 nicht antwortet.
constexpr uint32_t PN5180_INIT_RETRY_MS = 5000;
// Zeitgrenze je PN5180-Befehl (in tonie_test: COMMAND_TIMEOUT_MS).
constexpr uint32_t PN5180_CMD_TIMEOUT_MS = 30;

static_assert(REMOVE_AFTER_MS > 5 * POLL_PERIOD_MS,
              "REMOVE_AFTER_MS muss groesser als 5 x POLL_PERIOD_MS sein");
static_assert(ERROR_HOLD_MS >= REMOVE_AFTER_MS,
              "ERROR_HOLD_MS muss >= REMOVE_AFTER_MS sein");
