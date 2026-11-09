# Design: Ladesockel Tobi Box (Kontakte, feste Richtung)

* **Autor:** Tobias (Projektleitung: Claude als „Elefant“)
* **Datum:** 2026-11-09
* **Stand:** **Rev. 3** (billiger), nach R5/R6 in `resolve.md`
* **Grundlage:** `concepts_brief.md` (D1, D3–D6), `resolve.md` (R3–R6),
  `review_elektrik.md`, `review_mechanik.md`, `research_qi.md`,
  `docs/plan/stueckliste-und-psp.md` (Rev. 3.16), `docs/designs/box-software.md`
* **Frühere Stände:** Rev. 1 und Rev. 2 (jede Drehlage, eFuse-Platine) im
  Git-Verlauf dieser Datei

Werte mit **(R)** sind Richtwerte, gemessen oder geprüft wird am Muster. In
eckigen Klammern steht der Befund aus den Reviews, der eine Regel begründet.

---

## 1. Was sich gegenüber Rev. 2 ändert

| Rev. 2 | Rev. 3 | Warum |
|---|---|---|
| jede der vier Drehlagen | **eine feste Richtung**, Steg und Nut führen | R5: spart Hartgold-Scheibe, Zapfen, Toleranzkette |
| Kontaktscheibe Hartgold, 6 Pogo-Pins, konischer Zapfen | **fertiger Magnet-Pogo-Stecker** (4-polig, je 2 Pins parallel) | R5 |
| 4 Magnete in der Box | **2 Magnete** | nur eine Lage muss passen |
| eigene eFuse-Platine | **fertige Module**: Pololu #2810, PTC, USB-C-Breakout, kleine Lochrasterplatine | R6 |
| A6 voll erfüllt | **A6 mit bewusstem Restrisiko** (Abschnitt 4.4) | R6 |

Gleich bleiben: zwei Einzelsockel, je ein Markennetzteil (R3), keine LED am
Sockel, zwei Reeds in Reihe, Ablauf für Flüssigkeit, Tobias testet (R4).

---

## 2. Anforderungen

| # | Anforderung | Herkunft |
|---|---|---|
| A1 | Box lädt in **einer** festen Richtung. Falsch herum lädt sie nicht, und es passiert nichts. | R5 |
| A2 | Kind stellt die Box ab, die Mulde führt sie. Die richtige Richtung findet es am Bedienfeld vorne und am fühlbaren Einrasten. | D1 (eingeschränkt) |
| A3 | Kind hebt die Box einhändig ab, der Sockel bleibt stehen. | D1 |
| A4 | Ohne aufsitzende Box sind die Sockel-Pins spannungslos. Ein einzelner fremder Magnet ändert daran nichts. | E4 |
| A5 | Beim USB-C-Laden ist der Stecker der Box spannungslos. | Punkt 7 |
| A6 | Ein Metallteil auf den Pins wird nicht heiß, solange die Reeds offen sind. **Restrisiko:** sind beide Reeds durch fremde Magnete geschlossen, begrenzt nur PTC und Netzteil. | R6 |
| A7 | Andocken weckt die Box nicht. | Punkt 3, E9 |
| A8 | Ladestrom am Sockel ≥ 90 % des Ladestroms am USB-C. | E7 |
| A9 | Keine Magnete oder Kleinteile, die ein Kind herauslösen kann, auch nach einem Sturz. | Punkte 13–15 |
| A10 | Zuleitungen ≥ 3 cm von der NFC-Antenne. | Punkt 10, M18 |
| A11 | Keine Anzeige am Sockel. Ob die Box lädt, zeigt ihr LED-Ring (blau). | D6 |
| A12 | Kein Signal vom Sockel zur Box. | box-software.md |
| A13 | Verschüttete Flüssigkeit läuft ab. | M9 |

---

## 3. Aufbau

```
 Steckdose        Sockel                                                       Box
 ─────────        ─────────────────────────────────────────────────            ────────────────────────
 Netzteil ─USB-C─► Breakout ─► PTC ─► TVS, Elko ─► #2810 ─► Stecker 2× +5V ═══► Stecker ─► #5398 A ─┐
 5,1 V/3 A         5,1 kΩ CC                        ▲ ON                                            ├─► PiSugar
                                                    │ RC-Verzögerung              USB-C ─► #5398 B ─┘
                                  Reed 1 ── Reed 2 ─┘
                   GND ─────────────────────────────── Stecker 2× GND ═══► GND
```

### 3.1 Elektrik Sockel

| Teil | Vorgabe |
|---|---|
| USB-C-Breakout | nur 5 V, 5,1 kΩ an CC1/CC2 (wie in der Box) |
| PTC, bedrahtet | Haltestrom ≥ 1,3 × gemessener Ladestrom (T2), z. B. 2,5 A Halte (R) [E2] |
| TVS bedrahtet (z. B. P6KE6V8A) und Elko 100 µF | am Eingang des #2810 [E6] |
| Pololu #2810 | Load-Switch. **Schieber auf „off“ und verklebt**, rote LED abgelötet [E12, A11] |
| ON-Pin | Reed 1 und Reed 2 in Reihe von 5 V über 100 kΩ an ON, 100 kΩ von ON nach GND, 10 µF von ON nach GND. Damit schaltet der #2810 etwa 0,2–0,3 s nach dem Andocken ein und ebenso schnell wieder aus. Prellen der Kontakte fällt in diese Zeit [M1, E5] (R) |
| Aufbau | kleine Lochrasterplatine, nur bedrahtete Teile, Tobias lötet |

### 3.2 Magnet-Pogo-Stecker (R5)

Fertiges Paar: Federhälfte im Sockel, flache Hälfte in der Box. Die Magnete im
Stecker ziehen die Hälften auf den letzten Millimetern zusammen und richten sie
aus.

**Anforderungen an den Stecker** (Typ wird am Muster gewählt, siehe T0):

- 4-polig, je 2 Pins parallel für Plus und Masse. Je Pin ≥ 1,5 A Dauerstrom
  laut Datenblatt.
- Magnete im Gehäuse eingeschlossen, nicht offen.
- Vergoldet, ≥ 10.000 Steckzyklen laut Hersteller.
- Verpolsicher durch die Magnetpolung (ein falsch gedrehter Stecker stößt ab).
  Das ist eine zweite Sicherung neben der festen Richtung.
- Federweg ≥ 1 mm, Fangbereich der Magnete ≥ 1,5 mm (R).

**Kandidaten aus der Recherche (09.11.), alle unvollständig belegt:**
Promax NF6266 (2 A je Pin, 10.000 Zyklen, 3-A-Variante soll es geben),
Mill-Max Maxnetic 878 (9 A je Pin in freier Luft), Multicomp Pro MP011967/68
(Farnell, 2 A), ATTEND 303D (DigiKey, ~6 $). Dazu billige 4-polige Paare von
AliExpress als Vergleich.

**Einbau:**
- Sockel: Federhälfte im Mulden-Boden, Pins stehen so weit vor, wie der
  Stecker es vorsieht. Von unten eingesetzt, mit Epoxy vergossen, dicht zum
  Elektronikfach.
- Box: flache Hälfte bündig im Boden, von innen eingesetzt und vergossen. Von
  außen nicht herausziehbar [M15].
- **Abweichung von PSP 3.5.3 („Kontakte 3–4 mm versenkt“):** Die Pins im
  Sockel stehen vor, die Pads der Box sind bündig. Das ist vertretbar, weil
  beide Seiten ohne aufsitzende Box spannungslos sind (A4, A5).

### 3.3 Box

- Stecker: Plus → #5398 Eingang A, Masse → GND. USB-C → Eingang B
  (unverändert). 20-mΩ-Jumper am #5398 überbrückt [E7].
- Zwei Magnete 8×3 mm im Boden, eingeschlossen (≥ 1,2 mm PETG) und eingeklebt.
- Zuleitung am Boden und an der Rückwand entlang, ≥ 3 cm von der Antenne.

---

## 4. Mechanik

### 4.1 Mulde und Führung

- Innenmaß am Boden 124 × 124 mm (2 mm Spiel je Seite). Wände durchgehend 60°
  schräg, 20 mm hoch, ohne senkrechte Führungswand [M5]. Die Box liegt mit
  ihrem PETG-Boden auf, Freistiche für die TPU-Ecken [M2].
- **Steg und Nut:** Auf dem Mulden-Boden verläuft hinten ein Steg
  (60 × 4 × 3 mm, oben gerundet). Die Box hat hinten im Boden die passende Nut
  (5 mm breit, 4 mm tief).
  - In der richtigen Richtung sinkt die Box ganz ab. Der Stecker schließt,
    beide Reeds schließen.
  - Falsch gedreht liegt die Box auf dem Steg, 3 mm zu hoch. Der Stecker
    trifft nicht, mindestens ein Reed bleibt offen. Es passiert nichts.
- **Wie das Kind die Richtung findet:** Das Bedienfeld zeigt nach vorne zum
  Kind. Richtig herum sinkt die Box ab und rastet mit einem leichten Klack der
  Stecker-Magnete ein, der LED-Ring zeigt blau. Ob Kinder das ohne Hilfe
  schaffen, zeigt der Alltag. Kindertests vor der Abnahme gibt es keine (R4).

### 4.2 Reeds und Magnete

- Zwei gekapselte Reeds unter dem Mulden-Boden, beide **hinten** bei
  (+35/+35) und (−35/+35) mm, in Reihe.
- Die zwei Box-Magnete sitzen an denselben Stellen.
- Bei 90°, 180° oder 270° Drehung liegt höchstens ein Box-Magnet über einem
  Reed, die Reihe bleibt offen. Zusammen mit dem Steg ist das doppelt
  gesichert.
- Ein einzelner fremder Magnet schließt nie beide Reeds, sie liegen 70 mm
  auseinander.
- Die Magnete im Stecker sitzen in der Mitte, ≥ 40 mm von den Reeds entfernt,
  und lösen sie nicht aus (Schätzung aus der Recherche, T1 prüft).
- Der Reed muss im Endstand mit Reserve schließen: Schaltabstand
  ≥ 1,5 × Abstand Magnet–Reed (R) [M1, M13].

### 4.3 Sockel

- Außen ~155 × 155 mm, Höhe ~35 mm (R).
- Gewicht 200–300 g im Boden (Stahlscheiben), wenn T5 es verlangt. Der Halt
  der Stecker-Magnete ist klein (Größenordnung 50–100 g), die Box hebt sich
  leicht ab.
- Mulden-Boden mit 2° Gefälle zu einer Rinne, 4 Ablaufbohrungen ins Freie.
  Elektronikfach getrennt und dicht.
- USB-C-Kabel des Netzteils hinten, mit Zugentlastung im Gehäuse.
- Boden mit Torx verschraubt, vier eingeklebte TPU-Füße.

### 4.4 Restrisiko (R6, bewusst akzeptiert)

Gefährlich wird es nur, wenn alles gleichzeitig zutrifft: Zwei fremde Magnete
liegen genau über beiden Reeds (70 mm auseinander, in der Mulde), dazu liegt
ein Metallteil mit schlechtem Kontakt quer über Plus- und Masse-Pins.

Dann begrenzt nur der PTC oder das Netzteil. Ein Übergangswiderstand von
1–2 Ω kann mehrere Watt Wärme erzeugen, ohne dass beide auslösen [E1].

T6 misst genau diesen Fall. Liegt die Temperatur am Stecker oder an der Last
über 60 °C, kommt die eFuse-Platine aus Rev. 2 zurück.

---

## 5. Wecken und Software

- Auto-Power-On am PiSugar bleibt aus (PSP 5.6.5). Die Quelle dazu wird vor
  der Bestellung belegt. Ein Erfahrungsbericht mit Qi zeigt, dass ein PiSugar
  beim Laden den Pi starten kann (`research_qi.md`, #168). T3 prüft das
  besonders.
- Hinweis an die Box-Software: „am Lader“ etwa 10 s entprellen, bevor Sync oder
  Update starten [M10]. Kein Vertragsthema, Prüfpunkt bei AP Strom/Leerlauf.

---

## 6. Tests

Alle durch Tobias (R4), im geschlossenen Sockel bei ≥ 25 °C Raumtemperatur.

| # | Test | Bestanden, wenn |
|---|---|---|
| T0 | Stecker-Auswahl: 2–3 Typen kaufen. Je Typ Strom 2,7 A für 1 h über 2+2 Pins, Temperatur, Fangbereich, Haltekraft | ein Typ bleibt < 50 °C, fängt ≥ 1,5 mm, Magnete fest im Gehäuse |
| T1 | Reeds: Schalt- und Rückfallabstand; Box in 0/90/180/270°; Fremdmagnete (Tonie, Magnetbaustein, Handyhülle) einzeln; Stecker-Magnet neben einem Reed | Nur bei 0° beide geschlossen. Kein einzelner Fremdmagnet, kein Stecker-Magnet schaltet frei |
| T2 | Ladestrom Sockel gegen USB-C, Box aus und Box läuft. Spannung am PiSugar | A8 erfüllt. Daraus folgt der PTC-Wert |
| T3 | Wecken: 20× andocken bei Box aus; leerer Akku; Netzteil einstecken mit aufsitzender Box; wackeln | Box bleibt aus und lädt |
| T4 | Andocken: richtig herum 20× mit Versatz und leichter Schräglage; falsch herum in allen drei Lagen | richtig: lädt jedes Mal, LED-Ring blau. Falsch: liegt auf dem Steg, 0 V an den Pins |
| T5 | Abheben einhändig, auch schräg; Seitenstoß | Sockel hebt sich nicht und kippt nicht |
| T6 | Kurzschluss: ohne Box Münze, Löffel, Alufolie auf den Pins. Dann beide Reeds mit Magneten schließen, Widerstände 0,2 / 0,5 / 1 / 2 / 3 Ω über Plus und Masse, je 5 min, den heißesten Wert 1 h | Ohne Magnete 0 V. Mit Magneten: Stecker, Last und Module < 60 °C. Sonst eFuse-Platine aus Rev. 2 |
| T7 | Box am USB-C: Spannung am Box-Stecker mit 1 kΩ Last | < 0,1 V |
| T8 | USB-C und Sockel gleichzeitig, eine Quelle unter Last abziehen | kein Neustart, keine Rückspeisung |
| T9 | Wärme: Laden leer → voll, Messung an #2810, PTC, Stecker | alles < 50 °C |
| T10 | Krümel, Wasser, Saft in die Mulde und auf den Stecker; Box auf Teppich, dann andocken | Wasser läuft ab, Elektronikfach trocken, Stecker mit einem Wisch sauber |
| T11 | 300× andocken, Kontaktwiderstand Anfang und Ende | Anstieg < 50 % |
| T12 | Sturz der Box aus 1 m (PSP 4.3.2), Zug an Stecker und Füßen | nichts lose, kein Magnet zugänglich |

---

## 7. Stückliste (beide Sockel und Boxen, R)

| Teil | Stk | ca. € |
|---|---|---|
| Netzteil Raspberry Pi 15 W USB-C (5,1 V/3 A, Kabel fest) | 2 | 20 |
| Magnet-Pogo-Stecker 4-polig, Paare (2 für den Einbau, 2–3 Typen für T0) | 5 | 15 |
| Pololu #2810 | 2 | 10 |
| USB-C-Breakout mit 5,1 kΩ an CC | 2 | 4 |
| PTC, TVS, Elko, Widerstände, 10 µF, Lochraster | — | 5 |
| Reed-Kontakt gekapselt (4 Einbau, 2 Ersatztyp für T1) | 6 | 15 |
| Neodym-Magnete 8×3 mm (schon in Stückliste 1.1, jetzt 2 statt 4 je Box) | — | −2 |
| entfällt: Pogo-Pins in der Box (Stückliste 1.1) | — | −10 |
| Stahlscheiben, Epoxy, Schrauben, Füße, Litze | — | 10 |
| PETG und TPU (Druck) | — | 6 |
| **Summe** | | **~73** |

Im Plan stehen 30 € (Stückliste 1.2). **Mehrkosten ~43 €** (Rev. 2: ~95 €).

### 7.1 Abweichungen vom Plan (nach Annahme in `docs/plan/` nachtragen)

| Stelle | Neu |
|---|---|
| Stückliste 1.1 „Pogo-Pins 2-polig“ | flache Hälfte des Magnet-Steckers in der Box |
| Stückliste 1.1 „Neodym-Magnete 4 Stk“ | 2 Stück |
| Stückliste 1.2 „Dual-Ladestation“, „Load-Switch + Reed“ | zwei Sockel nach dieser Rev. 3 |
| PSP 3.5.1 Verpolschutz | feste Richtung (Steg/Nut) und Magnetpolung des Steckers |
| PSP 3.5.3 Kontakte versenkt | Pins im Sockel stehen vor, Pads der Box bündig, beide ohne Box spannungslos |
| PSP 3.5 neu | 3.5.5 Stecker-Auswahl (T0) |
| PSP 3.1 neu | Ladestrom-Messung (T2) |

---

## 8. Vergleich

| | Rev. 2 | **Rev. 3** | Qi |
|---|---|---|---|
| Drehlage | jede | eine, mit Führung | jede (Mulde: 4) |
| Kurzschlussschutz | eFuse, voll | PTC und Netzteil, Restrisiko | Fremdmetall-Erkennung im Pad |
| Eigene Platine | ja | nein | nein |
| Bauzeit bis Muster | Entwurf + 2–3 Wochen | sofort nach Bestellung | sofort |
| Kosten (R) | ~125 € | **~73 €** | ~40–60 € |
| Status | Rückfall, falls T6 durchfällt | **Vorschlag** | verworfen (Wärme am Akku, Aufwachen) |

## 9. Offen bis zur Bestellung

1. Stecker-Typen für T0 auswählen (Agent sucht 2–3 lieferbare 4-polige Paare
   mit Datenblatt).
2. Reed-Typ (gekapselt) für T1.
3. Quelle zum Weckverhalten des PiSugar.
4. Box-Maße nachmessen, dann Mulde, Steg und Nut festlegen.
