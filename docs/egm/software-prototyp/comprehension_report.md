# Goldfisch-Review Stufe 6 — Verständlichkeit

**Ziel:** `design_draft.md` · **Prüfer:** frischer Agent (Haiku), hat nur dieses Dokument gelesen · **Datum:** 2026-11-05

Geprüft: gesamte Datei (Zeilen 1-926). Nur diese Datei gelesen. Die Zeilenangaben beziehen sich auf die Datei.

### What this proposes

Ein eigener Box-Dienst (Python, asyncio) auf einem Rechner in der Box (zuerst Mac, dann Raspberry Pi 3A+) spielt pro NFC-Figur eine Serie aus lokalen mp3-Dateien über MPD ab. Eine ESP32-S3-Firmware liest die Figuren mit einem PN5180, entprellt die Lesungen und meldet „liegt auf / weg“ über ein Textprotokoll (Protokoll v1). Der Dienst merkt sich pro Serie den Stand (Resume). Zuordnungen von Figuren zu Serien liegen in einer eigenen Home-Assistant-Integration und werden per MQTT an die Boxen verteilt. Medien kommen per rsync vom NAS über Tailscale. Updates laufen als Paket mit Selbsttest und Rückfall. Hardware-Funktionen werden mit Simulation gebaut. Die Arbeit ist in vier Stufen mit Arbeitspaketen (AP) gegliedert.

### How the existing system works, per this document

Das Dokument beschreibt kaum ein laufendes System. Der Ausgangspunkt wird nur benannt: die Planung Rev. 3.7 mit Phoniebox V3 (verworfen), `firmware/tonie_test/` als unveränderte Referenz für Lese- und Entsperr-Abläufe, und ein HA-Konfigurationsordner im Repo. Was heute auf der Box oder in HA tatsächlich läuft, erfährt man aus dem Dokument nicht. Die Paraphrase des Ist-Zustands ist deshalb nur teilweise möglich.

### Findings

1. **Blocker**. Reihenfolge der Folgen widerspricht sich. Zeile 112-114 und 441-442 sagen, die Reihenfolge steht in `serie.json` (`folgen` als Liste). Zeile 390-391 sagt dagegen: Folgen sind „sortiert nach Dateiname (natürliche Sortierung)“. Zeile 445 und 714 nennen die Reihenfolge wieder, ohne die Quelle zu nennen. Ein Leser kann nicht sagen, nach welcher Regel die Box spielt. Empfehlung: eine einzige Regel festlegen (z. B. `serie.json` gewinnt, Dateiname nur ohne `serie.json`) und in Zeile 390-391 und 714 angleichen.

2. **Major**. Zentrale Begriffe werden verwendet, bevor sie erklärt werden, und der Begriffsblock ist unvollständig. Der Block „Begriffe“ (Zeile 148-149) definiert nur Figur, Serie und Überraschungs-Ordner. „Kennung“ wird ab Zeile 202 benutzt, aber erst ab Zeile 341 erklärt. „Resume“ steht ab Zeile 64, wird aber erst in Zeile 401-404 definiert. Auch „Stand“, „Zuordnung“, „Zeiger“, „Vorgangs-ID“ (Zeile 158, 519), „Entpreller“ und „Herzschlag“ fehlen im Begriffsblock. Die Vorgangs-ID wird nie erzeugt oder beschrieben. Empfehlung: Begriffsblock um diese Begriffe ergänzen, mit einem Satz zu Herkunft und Zweck (bei der Vorgangs-ID also: wer erzeugt sie, wann, aus welchem Wert).

3. **Major**. „Entsperren“ und das Passwort sind nicht erklärt. Zeile 18-19 sagt nur „entsperrt Tonies“. Zeile 192 nennt „unser Passwort“, Zeile 303 „Passwort aus config.h, wie bisher“. Der Leser erfährt nicht, was entsperren technisch heißt, welcher Schritt scheitert und zu `LOCKED` führt, oder warum ein Passwort nötig ist. „Wie bisher“ (Zeile 303) verweist auf eine Vorgeschichte, die das Dokument nicht enthält. Empfehlung: einen Absatz „Gesperrter Tonie“ mit Ablauf (Lesen, Authentifizieren, Ergebnis) ergänzen.

4. **Major**. Ohne gespeicherten Stand bleibt unklar, was „nicht gehörte Folge“ heißt. CUJ 4 (Zeile 179-182) sagt, ohne Stand beginne Serie B „bei der nächsten noch nicht gehörten Folge“. Das Datenmodell (Zeile 386-387, 401-404) speichert je Serie nur einen Zeiger (Folge und Position). Es gibt keinen Speicher, welche Folgen gehört wurden. Der Leser kann nicht entscheiden, ob „ungehört“ von Folge 1 an gilt oder etwas anderes bedeutet. Empfehlung: die Regel mit dem gespeicherten Feld erklären oder den Zustand „ungehört“ einführen.

5. **Major**. Die Zeitgrenzen sind behauptet, aber nicht hergeleitet. Zeile 54-57 und CUJ 1 (Zeile 156) fordern Ton ≤ 1,0 s und Pause ≤ 1,5 s. Zeile 315-316 sagt „REMOVED nach 1,1 s“ und daraus „Pause ≤ 1,5 s“. Der Abfragezyklus (≤ 200 ms), die 2–3 gleichen Lesungen (Zeile 223, 313-314), Übertragung und MPD-Start werden nicht zusammengerechnet. Die Rechnung steht nur indirekt in `docs/timing.md`, das nicht Teil des Dokuments ist. Empfehlung: eine kurze Summenrechnung je Grenze (Lesen + Entprellen + Übertragen + MPD) in den Text.

6. **Major**. Der Rückfall nach einem fehlgeschlagenen Update ist vage. Zeile 506-510 nennt „Start-/Boot-Zähler und `OnFailure=`“, sagt aber nicht, wie gezählt wird, wer die „5 min“ misst und woher der nächste Start weiß, dass die neue Version nicht „ok“ wurde. Die Zustände `testing`, `ok`, `failed` (Zeile 500-505, 844) werden erst in der Detailebene genannt. Der Leser kann den Mechanismus nicht nachvollziehen. Empfehlung: den Ablauf Schritt für Schritt schreiben, mit Auslöser, Zähler und Entscheidung.

7. **Major**. Projekt- und Prozessbegriffe sind ohne Erklärung. „Goldfisch“ (Zeile 38, 660, 806) ist der Name des Review-Verfahrens, aber nie erklärt. „AP“ wird ab Zeile 359 benutzt und erst in der Detailebene (Zeile 660) definiert. „Stufe 0–4“ taucht ab Zeile 74 und 105 auf, wird aber erst ab Zeile 674 als Lieferphasen beschrieben. Empfehlung: einen kurzen Absatz „Begriffe der Umsetzung“ (AP, Stufe, Goldfisch, Abnahme) am Anfang ergänzen.

8. **Major**. Externe Referenzen sind ohne Inhalt oder Link genannt. „Plan 7.2“ (Zeile 131), „Plan 5.5.2“ (Zeile 871, Zustände des LED-Rings, ohne die der Ring nicht implementierbar ist), „Plan 5.7“ (Zeile 906), „Rev. 3.7“ (Zeile 37), „Rev. 3.9“ (Zeile 860), „PSP-Punkte“ und `psp-baum.html` (Zeile 923), `research_tonie_erkennung.md` (Zeile 90), `pivot_ohne_v3.md` (Zeile 566), `concepts_brief.md` und `docs/plan/`. Ein Leser ohne diese Dokumente kann mehrere Regeln nicht prüfen. Empfehlung: pro Referenz ein Satz mit dem Inhalt, der gebraucht wird, und einen Pfad oder Link.

9. **Major**. Funktionen der Stufe 4 haben kein beschriebenes Verhalten. „Leise-Zeiten“ (AP 4.5, Zeile 902-906) kommen in den Entscheidungen und CUJs nicht vor und werden nicht erklärt: Was passiert in einer Leise-Zeit? Die Gute-Nacht-Karte (Zeile 116-117, 909-914) hat keinen CUJ, nur einen Testnamen mit „Timer, Ausblenden“. Leerlauf nach 20 min (Zeile 890) und das Kopfhörer-Limit (Zeile 897-899) sind nur Dateizeilen. Zeile 93-94 schließt Funktionen „ohne Plan oder CUJ“ aus, diese stehen aber nicht in den CUJs. Empfehlung: je Funktion einen CUJ mit Given/When/Then oder einen Verhaltenssatz ergänzen.

10. **Major**. Externe Dienste sind nicht erklärt. Tailscale ist zentral (Diagramm Zeile 281, Zeile 292 „immer über Tailscale“, Risiko Zeile 141, Zeile 473), wird aber nie beschrieben. Der Leser erfährt nicht, dass es ein privates VPN ist, und „ACL“ (Zeile 638, 852) fehlt. Nabu Casa (Zeile 89, 289, 453) ist ebenfalls nur ein Name. PiSugar (Zeile 72, 884) ist eine Akku-Platine. MQTT-Discovery (Zeile 413) und `pytest-homeassistant-custom-component` (Zeile 823) sind ohne Erklärung. Empfehlung: je Dienst ein Satz Zweck und Link.

11. **Major**. Der Stand des Ausgangssystems fehlt, obwohl die Paraphrase ihn verlangt. Was auf der Box läuft, was in HA schon existiert und welche Teile neu sind, steht nicht im Dokument. Das Dokument verweist auf `firmware/tonie_test/` und `homeassistant/`, beschreibt deren Inhalt aber nicht. Empfehlung: einen Abschnitt „Ausgangslage“ mit Ist-Zustand und Abgrenzung (neu, geändert, unverändert) ergänzen.

12. **Major**. Offene Fragen verweisen auf Inhalte, die im Dokument fehlen. Zeile 126-128 sagt zu Q2 (Audio-Rückmeldungen): „Klärt der Abschnitt Technical Plan“. Dort stehen aber nur Status-Tonfolge und Platzhalter-Töne, keine Liste der Töne. Die Nummern Q1–Q6 und „ehem. Q3/Q5/Q6“ (Zeile 108, 115-117, 130) sind nur mit `concepts_brief.md` verständlich. Empfehlung: Q2 in den Technical Plan übernehmen oder als offen markieren; alte Nummern durch Titel ersetzen.

13. **Nit**. Die Medienverwaltung widerspricht sich bei Bildern. Zeile 108-109 sagt „keine Bilder“. Zeile 553 spricht von einer ID-Datei mit „später Bild“. Das `serie.json`-Schema (Zeile 440-442) hat kein Bildfeld. Empfehlung: „später“ streichen oder das Feld als Platzhalter im Schema zeigen.

14. **Nit**. Zwei kleinere Unklarheiten in CUJ und Zuständigkeit. CUJ 3 heißt „Dieselbe Figur wieder auflegen“ (Zeile 167), im Given/When steht aber „eine Figur dieser Serie“ (Zeile 169). Zeile 709 sagt, `events.py` enthält die Ereignis- und Befehlstypen, Zeile 710 und 369-370 sagen, `core.py` lege sie fest. Empfehlung: Titel an den Given/When-Text anpassen und eine Datei als Eigentümer der Typen nennen.

15. **Nit**. Sprache und Begriffe, die beim Lesen stolpern lassen. „Revision“ bedeutet an verschiedenen Stellen Plan-Revision (Zeile 37, 860), Zuordnungs-Revision (Zeile 385, 421) und Revisionsregel. „Hardware-Funktionen sind kein Nicht-Ziel mehr“ (Zeile 81) ist eine doppelte Verneinung. „Herzschlag-Wächter (5 s)“ (Zeile 712) passt zum Takt von 2 s (Zeile 337), das wird nicht erklärt. „Zeitquelle“ (Zeile 519) bleibt offen, und die Modellnamen Sonnet, Haiku, Opus (Zeile 660) sind nur für Projektbeteiligte verständlich.

### Gesamturteil

Das Dokument ist für die Feature-Ebene (Zeile 1-655) gut gegliedert. Der Leser versteht Ziel, Nicht-Ziele, Entscheidungen und Journeys. Die Lücken liegen in der Begriffsführung, in der fehlenden Herleitung der Zeitgrenzen, im widersprüchlichen Folgen-Reihenfolge-Regel (Finding 1, Blocker), im vagen Rückfall-Mechanismus und in den Stufe-4-Funktionen ohne Verhalten. Vor einer Freigabe sollten mindestens Finding 1 und die Begriffe (Finding 2, 7) behoben werden.
