# Resolve Ladestation (09.11.2026)

Befunde aus `review_elektrik.md` (E1–E17) und `review_mechanik.md` (M1–M21),
mit Tobias durchgegangen. Grundlage für Rev. 2 von `design_draft.md`.

## Entscheidungen von Tobias

| # | Frage | Entscheidung | Befunde |
|---|---|---|---|
| R1 | Kurzschlussschutz bei Fremdmagnet + Metallteil | **Eigene Sockel-Platine mit eFuse** (z. B. TPS25947: Stromgrenze ~2,7 A, Übertemperatur-Abschaltung, Softstart). Vom Hersteller bestückt, kein SMD-Löten. Pogo-Pins direkt auf der Platine (FR4, hitzefest). Gleiche Bestellung wie die Kontaktscheiben. Dazu in jedem Fall **zwei Reeds in Reihe** an gegenüberliegenden Ecken. **Ersetzt D7** (fertige Module). | E1, E2, E4, E6, M20 |
| R2 | Material der Kontaktscheibe | **Leiterplatte mit Hartgold** (dicke Goldschicht wie bei Steckkontakten). Zyklentest prüft. | M8, E10 |
| R3 | Netzteile | **Zwei neue Markennetzteile** USB-C 5 V/3 A, CE, Schutzklasse II, mit C-auf-C-Kabel. Typ wird im Design festgelegt, T6 wird genau damit gemacht. | E3, E13 |
| R4 | Wer testet | **Nur Tobias**, mit den verschärften Vorgaben aus dem Review (Drehversatz, Schräglage, Aufsetzen mit Schwung). Kein Kindertest vor der Abnahme. | M16 |

### Vorrecherche zu R1 (Haiku, 09.11.)

Kein fertiges Modul passt sauber. TPS25947EVM: Daten passen (0,5–6 A per
Jumper, Übertemperatur, Latch- oder Auto-Retry-Variante, Enable aktiv high mit
~1,2 V Schwelle, Softstart über dV/dt-Kondensator), aber große Testplatine
ohne Pogo-Anschluss, Preis offen. FlexTrip (Tindie, ~20 €): Stufen und Enable
nicht dokumentiert. TPS25200-Modul: Grenze 2,9 A, Eingang nur bis 5 V, Reset
per Taster. Adafruit, Pololu, SparkFun: nichts Passendes.

## Ohne Rückfrage übernommen (Korrekturen)

| Thema | Übernahme | Befunde |
|---|---|---|
| Reihenfolge Pin-Kontakt vor Strom | Elektrisch statt über die Geometrie: Einschaltverzögerung 0,1–0,5 s nach Reed-Schluss (Enable der eFuse über RC), dazu Softstart der eFuse. Reed sitzt im Endstand mit Reserve (Abstand ≤ 1/1,5 des Schaltabstands). „Restabstand“ wird definiert (Magnet–Reed). | M1, E5, E6 |
| Masse zuerst | Ring-Pins (GND) länger als der Mittel-Pin: GND schließt zuerst, trennt zuletzt. | E5 |
| Strom am Mittel-Pin | 2–3 Pins parallel in der Mitte, Mittelfläche entsprechend größer, Pin mit belegtem Dauerstrom aus dem Datenblatt. | E8 |
| Schutzbauteile | Eingangs-Kondensator und TVS-Diode auf der Sockel-Platine. | E6 |
| Spannungsbudget | Tabelle je Stufe in 4.4. 20-mΩ-Jumper am #5398 überbrücken. Kriterium statt fester 4,75 V: Ladestrom am Sockel ≥ 90 % des Ladestroms am USB-C. | E7, E16 |
| Höhenkette und Federweg | Pins mit ≥ 1,5 mm Hub, Arbeitspunkt ~50 % Hub. Höhenkette Min/Max rechnen. Box liegt auf festen PETG-Anschlägen im Sockel auf, nicht auf den TPU-Ecken. Federkraft aus dem Datenblatt. | M2 |
| Zentrierung | Hauptzentrierung über **konischen Zapfen** mit großem Fangbereich und Fase an der Tasche. Mulde mit mehr Spiel (2–3 mm je Seite) und durchgehender Schräge ohne parallele Führungswand; Schräge steiler (≥ 55–60°) oder glatte Gleitflächen, mit echter TPU-Ecke messen. Toleranzkette: Mulden-Spiel nie größer als der Fangbereich des Zapfens. Höhen konsistent. | M3, M4, M5 |
| Maße | Kontaktscheibe, Tasche, Zapfen und Pin-Kreis einmal durchgerechnet und als Zeichnung/Tabelle. | M6, E14 |
| Münze in der Tasche | Satz „Münze erreicht die Kontakte nicht“ gestrichen. Stege in der Tasche prüfen, damit keine Münze flach aufliegt. Box-Seite bleibt durch #5398 spannungslos. | M7 |
| Flüssigkeit und Schmutz | Ablauf und Gefälle in der Mulde, Elektronikfach dicht getrennt, Pins mit Dichtung. Reinigungshinweis für Eltern. | M9, E10, M21 |
| Halt und Standfestigkeit | Gewicht im Sockelboden einplanen (~300–400 g), Kabelzug mit Zugentlastung, messbare Kriterien für Abheben und Stoß. Software-Hinweis: „am Lader“ entprellen. | M10, M11, M19 |
| Magnete | Lage 20–25 mm von den Kanten in der PETG-Bodenplatte, nicht in den TPU-Ecken. Abdeckung ≥ 1,2 mm. Reed-Lage und seitlicher Versatz im Test. | M12, M13 |
| Kleinteile | Pogo-Pins auf der Platine gelötet, Platine verschraubt. Kontaktscheibe mit Flansch und Epoxy. Füße mit Zapfen und Kleber. Zugtests. | M15 |
| Schieber #2810 | entfällt mit R1. | E12 |
| Wecken | Quelle zu Auto-Power-On belegen (docs.pisugar.com). T3 erweitert: leerer Akku, laufende Box ab- und aufsetzen, Netzteil mit aufsitzender Box einstecken, Flackern, nach Akkutausch/Reset. | E9 |
| Leitungsführung | Zuleitung Scheibe → #5398 entlang Boden/Rückwand, ≥ 3 cm von der Antennenebene. | M18 |
| Tests | T1 mit Schalt- und Rückfallabstand, Reed-Lage, Versatz und Fremdmagnet-Liste (Tonie, Magnetbaustein, Handyhülle, Kühlschrankmagnet, zweite Box). T6 als Widerstandsreihe 0,2–3 Ω, Temperatur am Pin-Halter < 60 °C. T7 mit Last 1 kΩ, T8 mit Strommessung beider Quellen und Umschalten unter Last. Neu: Prellen/Spitzen (Oszilloskop), Flüssigkeit, Zyklen ≥ 500, Sturz und Magnet-Zugtest, Drehversatz 0–15°, Schräglage, Aufsetzen aus 5–10 cm, weicher und schräger Untergrund, Seitenstoß. T9 im geschlossenen Sockel bis Beharrung an allen Messstellen. | E11, E15, E17, M14, M16 |
| Stückliste | ergänzt: USB-C-Kabel, Sockel-Platine (Bestückung), Reeds 2×, Kleber, Gewicht, Dichtung, Schrauben; Pogo-Pins in der Budgetzeile. Punkt 11 im Plan umformulieren. | M17 |

## Nächster Schritt

Rev. 2 von `design_draft.md` mit R1–R4 und den Übernahmen. Danach ein zweiter
kurzer Goldfisch-Durchgang nur auf die geänderten Abschnitte. Die
Sockel-Platine (Schaltplan, Layout) entsteht erst nach Annahme des Designs, als
Auftrag an einen Sonnet-Agent.
