# Ein- und Ausschalten: Brainstorm (EGM Schritt 1, läuft)

Anlass (10.11.): Tobias will das ganze Ein- und Ausschalten neu durchdenken. Ziel: **Akkulaufzeit
maximieren, gleichzeitig möglichst viel Komfort und möglichst wenig Handgriffe, bevor es spielt.**
Das EGM „Start am Lader“ (`docs/egm/start-am-lader/`) ruht so lange; seine Antworten
(`resolve_teil1.md`) und die Ladestations-Entscheidungen S1–S11 sind Eingaben für dieses Thema.
Fakten: `research.md` (im selben Ordner, in Arbeit).

## Antworten von Tobias (10.11.)

| Frage | Antwort |
|---|---|
| Nutzung | Mehrmals täglich kurz; zum Einschlafen am Abend; unterwegs; steht oft, aber nicht meistens am Sockel im Kinderzimmer. |
| Wartezeit vom Auflegen (Box aus) bis zum Ton | **Unter 3 s, wie eine Toniebox.** |
| Tobie weckt die ausgeschaltete Box (ohne Knopf) | **Ja, wenn machbar.** Hardware-Änderung ist in Ordnung. |
| Ladetakt | **Steht jede Nacht am Sockel.** Laufzeit pro Tag zählt, Wochen im Schrank sind egal. |

## Erste Folgerungen der Projektleitung (noch nicht mit Tobias abgestimmt)

- Unter 3 s geht nur, wenn der Pi schon läuft. Ein kalter Start dauert sicher länger (Zahlen in `research.md`).
  Also braucht es einen **Bereitschaftszustand** (Pi an, so sparsam wie möglich) und eine Regel, wann die
  Box von dort ganz ausgeht.
- **Am Sockel kostet Bereitschaft keinen Akku.** Die Box kann dort ohne Frist bereit bleiben.
- **Ohne Sockel** zählt das Tagesbudget: Ein voller Akku (~15 Wh nutzbar) muss Hören plus Bereitschaft
  bis zum Abend tragen, weil jede Nacht geladen wird.
- Nach „ganz aus“ soll ein aufgelegter Tobie die Box wecken (NFC-Leser bleibt sparsam wach). Dann
  dauert es länger als 3 s; wie lange, entscheidet die Startzeit.

## Antworten Runde 2 (10.11., nach `research.md`)

| Frage | Antwort |
|---|---|
| Am Sockel | **Immer bereit, auch nachts.** |
| Bereitschaft ohne Sockel | **10 min** nach dem letzten Hören, dann ganz aus. |
| Tobie weckt die Box | **Am Breadboard ausprobieren.** Klappt es nicht, weckt der Hauptknopf. |
| Schalter (MOSFET) für Ring und Leser | **Gleich einplanen.** (Hinweis Projektleitung: Für den Leser geht das nicht, er muss Tobies spüren; siehe `concepts_brief.md` E2.) |
| Neuer Wunsch | **Startup-Sound:** sofortige Rückmeldung beim Hochfahren (`concepts_brief.md` E7). |
