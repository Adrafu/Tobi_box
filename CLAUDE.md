# Tobi Box — Arbeitsregeln

Zwei baugleiche, mobile NFC-Audioboxen (Raspberry Pi 3A+, eigene
Box-Software auf MPD, PN5180 an ESP32-S3). Projektplan und Stand: `docs/plan/`.

## Rollen

- **Projektleiter / Koordinator (Haupt-Session, „Elefant“):** behält den
  Überblick, führt Entscheidungen und Design-Dokumente, schreibt **keinen Code**.
- **Umsetzung:** jeder Code wird an Agents vergeben, immer mit dem
  **billigsten passenden Modell**:
  - Haiku: Recherche, Zusammenfassen, Boilerplate, einfache Tests, Doku-Abgleich
  - Sonnet: Firmware, Plugin-Logik, Tests mit Hardware-Bezug, Code-Reviews
  - Opus: nur, wenn Sonnet nachweislich nicht reicht
- **Tobias:** entscheidet Trade-offs, testet an der echten Hardware.

## Vorgehen: Elephant-Goldfish-Model (Google, EGM)

1. Brainstorm: offene Rückfragen, bis Problem und Grenzen klar sind →
   `docs/egm/<thema>/concepts_brief.md`
2. Draft: Design-Dokument abschnittsweise → `docs/egm/<thema>/design_draft.md`
3. Review durch **Goldfische**: frische Agents ohne Gesprächsverlauf, sie
   sehen nur das Dokument und die darin referenzierten Dateien → Report im
   selben Ordner
4. Resolve: Befunde mit Tobias durchgehen, Entscheidungen festhalten
5. Erst dann Umsetzung durch Agents, angenommene Designs nach `docs/designs/`

EGM artifact directory: docs/egm

## Aktueller Stand

- Angenommenes Design der Box-Software: `docs/designs/box-software.md`
  (Entstehung und Reviews: `docs/egm/software-prototyp/`).
- Verträge (Stufe 0): `docs/protocol/`, `docs/data-model.md`. Agents ändern
  sie nicht eigenmächtig.

## Regeln

- Das Tonie-Passwort wird **nie** committet. Firmware liest es aus
  `config.h` (gitignored), im Repo liegt nur `config.example.h`.
- Entscheidungen und Revisionsstand gehören in `docs/plan/`, nicht nur in den Chat.
- **Abnahmen und Tests mit Tobias** (am Mac, Breadboard, Pi) gehen wir **gemeinsam im Chat Schritt für
  Schritt** durch: ein Schritt mit Befehlen und dem, was er sehen oder hören soll; Tobias meldet das
  Ergebnis; erst dann der nächste Schritt. Keine ganze Liste zum Selbst-Abarbeiten schicken. Die
  Anleitungen in `docs/betrieb/` bleiben die Grundlage.
- Sprache der Dokumente: Deutsch, einfach und direkt.
- Begriff (Entscheidung F, 05.11.): Tonies und NFC-Karten zusammen heißen **Tobie** (Mehrzahl Tobies), in Dokumenten und Texten für Eltern. Im Code heißt ein Tobie aus historischen Gründen `figur`.
