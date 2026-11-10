# Design: Ladesockel Tobi Box (USB-C-Stecker, hoher Kragen)

* **Autor:** Tobias (Projektleitung: Claude als „Elefant“)
* **Datum:** 2026-11-10
* **Stand:** **Rev. 5**, nach Review der Rev. 4 (`review_rev4.md`) und
  Resolve H1–H5 (`resolve.md`)
* **Grundlage:** `concepts_brief.md`, `resolve.md` (R3, R4, R7–R10, H1–H5),
  `software_folgen.md`, `hardware/ladesockel/` (Druckmuster),
  `docs/plan/stueckliste-und-psp.md` (Rev. 3.16), `docs/designs/box-software.md`
* **Frühere Stände:** Rev. 1 bis 4 im Git-Verlauf dieser Datei

Werte mit **(R)** sind Richtwerte. Das Druckmuster und Messungen am echten
Stecker legen sie fest. In eckigen Klammern steht der Review-Befund.

---

## 1. Idee

Der Sockel ist eine Mulde. In ihrer Mitte steht ein länglicher, konischer
**Kragen**. In einem Schacht darin sitzt der USB-C-Stecker des
Netzteilkabels, seine Spitze 2 mm unter der Kragenkante. Die Box hat unten
eine passende **Tasche**. In der Tasche hängt ein kurzer **Zapfen**, und in
dem sitzt die einzige USB-C-Buchse der Box. Beim Abstellen führt der Kragen
die Tasche, der Zapfen taucht in den Schacht, und der Stecker steckt.
Unterwegs lädt die Box an derselben Buchse mit einem gewinkelten Kabel.

- **Kein Metall erreicht die Kontakte:** Sie liegen im Stecker, und der
  Stecker liegt im Schacht.
- **Keine Elektronik im Sockel, keine Magnete in der Box.**

## 2. Entscheidungen, auf denen das aufbaut

| # | Inhalt |
|---|---|
| D1, D4, D6 | Kinder docken selbst an, zwei Einzelsockel, keine LED am Sockel |
| R3 | Zwei neue Markennetzteile (Raspberry Pi 15 W, 5,1 V/3 A, festes Kabel) |
| R4 | Tobias testet allein |
| R8 | Andocken weckt die Box kurz: Ton und LED-Ring zeigen Laden und Ladestand |
| R9 | USB-C-Stecker im Sockel |
| R10 | Eine USB-C-Buchse im Boden, auch für unterwegs. Kein Pololu #5398 |
| H1 | Abzugskraft messen, danach Gewicht oder Befestigung |
| H2 | Hoher Kragen statt Rippen (4a) |
| H4 | Offene Steckermündung akzeptiert wie bei jedem USB-C-Kabel |
| H5 | Buchse fest und robust eingebaut, nicht tauschbar |

---

## 3. Anforderungen

| # | Anforderung | Herkunft |
|---|---|---|
| A1 | Box lädt bei 0° und 180°. Bei 90° und 270° liegt sie stabil auf dem Kragen, der Stecker bleibt frei. | R9, H2 |
| A2 | Kragen und Mulde führen die Box ohne Zielen. Der Kragen führt ≥ 6 mm, bevor der Stecker die Buchse berührt. | D1 |
| A3 | Kind hebt die Box einhändig ab, der Sockel bleibt stehen. | H1 |
| A4 | Seitliches Hebeln an der steckenden Box stützen Kragen und Tasche ab, nicht der Stecker. | R9 |
| A5 | Unterwegs lädt die Box mit gewinkeltem Kabel in der Kabelrinne und steht dabei aufrecht. | R10 |
| A6 | Kein Metallteil in der Mulde erreicht die Kontakte. | G1 |
| A7 | Andocken weckt die Box kurz (Ablauf in Abschnitt 6). | R8 |
| A8 | Ladestrom am Sockel wie am Kabel (±10 %). | E7 |
| A9 | Keine Kleinteile, auch nicht nach einem Bruch. | Punkte 14–15, H15 |
| A10 | Flüssigkeit in der Mulde läuft ab. | M9 |
| A11 | Keine Anzeige am Sockel. | D6 |
| A12 | Das Netzteilkabel ist kurz geführt, keine lose Schlaufe im Kinderbereich. | H14 |

---

## 4. Mechanik

Das Koordinatensystem: x quer (links–rechts), y nach hinten, Höhen über dem
Mulden-Boden. Die lange Seite von Kragen und Tasche liegt in x.

### 4.1 Maße (R)

| Teil | Maß |
|---|---|
| Mulde | 124 × 124 mm innen, Wände 60°, 20 mm hoch, 2° Gefälle zur Rinne mit 4 Ablaufbohrungen |
| Kragen (fest mit der Mulde gedruckt) | unten 36 × 18, oben 30 × 12, 14 hoch |
| Schacht im Kragen | 12 × 7, Steckerspitze bei 12 (2 mm unter der Kante) |
| Tasche in der Box | Öffnung 37 × 19, oben 31 × 13, 14 tief |
| Buchsen-Zapfen in der Tasche | 11 × 6, Buchsenöffnung 5,5 mm über der Bodenfläche, ragt nicht über die Bodenfläche |
| Kabelrinne in der Box | aus der Tasche gerade nach hinten bis zur Rückkante, 14 breit, 8 tief |

### 4.2 Was die Maße leisten

| Lage | Ergebnis |
|---|---|
| 0° / 180° | Tasche über Kragen, Zapfen im Schacht (±0,5 mm), Stecker steckt voll (Spitze 12 − Öffnung 5,5 = 6,5 mm Stecklänge) |
| Führung vor Kontakt | Kragenhöhe 14 − 6,5 = **7,5 mm** Führung, bevor der Stecker die Buchse berührt |
| 90° / 270° | Die Tasche ist 19 mm breit, der Kragen oben 30 mm lang. Die Box liegt 14 mm hoch auf zwei Auflagen von je **5,5 × 12 mm**. Die Zapfen-Unterseite liegt bei 19,5, die Steckerspitze bei 12, also **7,5 mm frei** |
| Box auf dem Tisch | flacher Boden, Zapfen und Buchse liegen innen |

Das Druckmuster rechnet das mit Asserts nach (`hardware/ladesockel/`).

### 4.3 Stecker im Sockel [H6, H7]

- Das feste Kabel des Netzteils kommt von hinten in den Sockel. Der Stecker
  sitzt in einem **TPU-Halter** unter dem Schacht.
- Der Halter lässt **±0,5 mm seitlich** Spiel, damit der Zapfen den Stecker
  ausrichtet. **Axial liegt er auf einer festen Schulter.** Die Steckkraft
  von 5–20 N geht in den Sockel, nicht in den TPU.
- Der Kragen ist fest. Er nimmt die seitlichen Kräfte auf (A4).
- **Bruch:** Ein beschädigter Stecker wird mit dem Netzteil getauscht (~10 €).
  Ein Ersatz-Netzteil liegt bereit. Den Tausch macht Tobias, Werkzeug: Torx.

### 4.4 Sockel

- Außen ~155 × 155 mm, Höhe ~35 mm (R).
- **Halt (H1):** Zuerst die Abzugskraft des echten Steckers mit einer
  Federwaage messen (T0).
  - Unter ~8 N reicht ~1 kg Stahl im Boden.
  - Darüber wird der Sockel mit Klebepads (3M Dual Lock) oder zwei
    Schrauben am Möbel befestigt.
  - Das Druckmuster hat beide Optionen.
- **Kabel (H14):** im Sockel mit Zugentlastung geklemmt. Hinten kommt es kurz
  heraus und läuft am Möbel entlang zur Steckdose. Überlänge wird im Sockel
  aufgewickelt. Elternhinweis: Steckdose außer Reichweite.
- Boden mit Torx verschraubt, eingeklebte TPU-Füße.

### 4.5 Box-Boden

- Tasche, Zapfen und Kabelrinne wie in 4.1.
- **Buchse fest und robust (H5):** Das Sink-Breakout mit 5,1 kΩ an CC1/CC2
  ist im Zapfen verschraubt, die Buchse rundum gestützt. Es ist nicht
  vergossen, aber verklebt. Getauscht wird nur bei geöffneter Box.
- Die Zuleitung läuft zum Ladeeingang des PiSugar (Lötpads oder
  USB-C-Eingang des PiSugar, am Muster festlegen) [H10], ≥ 3 cm von der
  NFC-Antenne entfernt.
- **Schmutz (H9):** Die Tasche zeigt nach unten, Krümel fallen eher heraus als
  hinein. Elternhinweis: Tasche und Schacht gelegentlich auspinseln.

### 4.6 Flüssigkeit

- Der Kragen steht 14 mm hoch. Der Mulden-Boden läuft zur Rinne ab.
- Wasser im Schacht oder im Stecker trocknet wie bei jedem USB-C-Kabel (H4).
- T7 prüft das, auch die Spannung am nassen Stecker.

---

## 5. Elektrik

```
 Steckdose          Sockel                               Box
 Netzteil 5,1 V/3 A ─ festes Kabel ─► Stecker im Schacht ═► Buchse im Zapfen ─► PiSugar 3 Plus
 (Raspberry Pi 15 W)                  (TPU-Halter)           (5,1 kΩ an CC)
                                                             unterwegs: gewinkeltes Kabel
```

- Im Sockel gibt es keine Elektronik.
- Das Netzteil schaltet bei USB-C erst ein, wenn es die 5,1 kΩ der Box sieht.
  Ob das Pi-Netzteil das tut, misst T0 (Spannung am freien Stecker). Für die
  Entscheidung H4 ist das egal, für die Doku nicht.
- Rückspeisung: Ob an der Buchse bei Akkubetrieb Spannung liegt, misst T8 an
  der Box [H10].

---

## 6. Software (Kurzfassung)

Die vollständige Analyse steht in `software_folgen.md`. Die 11 Entscheidungen
dort sind noch offen, die Verträge unverändert.

- **Startgrund:** Die Box erkennt ihn nicht sicher. Der Ablauf gilt deshalb bei
  jedem Start mit Strom am Eingang.
- **Ablauf „Start am Lader“:**
  1. Rückmeldung (Ton, Ring mit Ladestand).
  2. Sync prüfen, nur im Heimnetz.
  3. Kurzer Zähler (Vorschlag 120 s) statt 20 min.
  4. Tobie, Hauptknopf, Abziehen oder ein HA-Befehl beenden den Kurz-Modus.
- **Nachts:** kein Ton, Ring gedimmt.
- **Unterwegs:** Jede Powerbank weckt die Box. Kein Sync über den Hotspot.
- **Falsch herum abgestellt [H12]:** Die Box lädt nicht und wacht nicht auf.
  Vorschlag für die Software-Runde: HA meldet abends, wenn eine Box nicht am
  Lader ist.
- **Zuerst am Muster prüfen:** Gerät die Box am Sockel in eine Startschleife,
  wenn sie herunterfährt, während Strom anliegt?

---

## 7. Tests (Tobias, R4)

| # | Test | Bestanden, wenn |
|---|---|---|
| T0 | Vorab am echten Netzteil: Abzugskraft des Steckers (Federwaage), Spannung am freien Stecker, Maße von Stecker und Buchse | Werte notiert. Daraus folgen Gewicht oder Befestigung und die Maße im Druckmuster |
| T1 | Kragenprobe, dann Druckmuster: Box 50× abstellen, auch schräg (5–10°), verdreht (bis 15°), mit Versatz, aus 5–10 cm fallen lassen | Bei 0°/180° steckt sie jedes Mal ohne Kraft. Bei 90°/270° liegt sie stabil auf dem Kragen, der Stecker bleibt frei |
| T2 | Hebeln: steckende Box seitlich mit 20, 40, 60 N kippen, in alle Richtungen. Danach bis zum Versagen an einem Muster | Bis 60 N nichts beschädigt. Beim Versagen bricht zuerst der Stecker oder Halter im Sockel, nie die Buchse, und es entstehen keine Kleinteile (Prüfzylinder) [H13, H15] |
| T3 | Abheben einhändig, senkrecht und schräg; dynamisch (ruckartig) | Sockel bleibt stehen |
| T4 | Ladestrom Sockel gegen Kabel | ±10 % |
| T5 | Wecken (R8): Andocken bei Box aus, Box an, leerem Akku, Leise-Zeit; Herunterfahren am Sockel | Rückmeldung wie in Abschnitt 6, keine Startschleife |
| T6 | Münze, Löffel, Alufolie in der Mulde, dann Box abstellen; Draht und Nadel in den Schacht | Nichts wird warm. Die Box steckt nicht oder lädt normal |
| T7 | Wasser und Saft in die Mulde und den Schacht, trocknen lassen | Läuft ab, danach normaler Betrieb. Spannung am nassen Stecker notiert |
| T8 | Unterwegs: Winkelkabel in der Rinne, Zug mit 20 N in alle Richtungen, auch ruckartig; Box hängt kurz am Kabel. Spannung an der Buchse bei Akkubetrieb | Box steht, Buchse unbeschädigt. Keine Rückspeisung |
| T9 | 2000× stecken | Steckkraft und Kontakt unverändert, T3 danach wiederholen |
| T10 | Sturz der Box aus 1 m (PSP 4.3.2) | Buchse und Zapfen fest, nichts lose |

---

## 8. Stückliste (beide Sockel und Boxen, R)

| Teil | Stk | ca. € |
|---|---|---|
| Netzteil Raspberry Pi 15 W USB-C, festes Kabel | 2 (+1 Ersatz) | 20 (+10) |
| USB-C-Sink-Breakout mit 5,1 kΩ für die Buchse | 2 (+1) | 9 |
| Gewinkeltes USB-C-Kabel für unterwegs (Abgangsrichtung zur Rinne passend) | 2 | 10 |
| Stahl ~1 kg je Sockel **oder** 3M Dual Lock / Schrauben | — | 6 |
| PETG und TPU (Druck), Schrauben, Kleber | — | 12 |
| Federwaage 0–50 N für T0, T2, T3 (falls nicht vorhanden) | 1 | 8 |
| entfällt: Pogo-Pins (Stückliste 1.1, 5 € je Box) | — | −10 |
| entfällt: Neodym-Magnete (Stückliste 1.1, 4 € je Box) | — | −8 |
| entfällt: Pololu #5398 (7 € je Box), USB-C-Breakout + Pigtail (4 € je Box) | — | −22 |
| **Summe** | | **~25 (mit Ersatzteilen ~35)** |

Im Plan stehen 30 € (Stückliste 1.2).

### 8.1 Abweichungen vom Plan (nach Annahme nachtragen)

| Stelle | Neu |
|---|---|
| Punkt 3, PSP 5.6.5, 8.2.4 | Andocken weckt kurz (R8, in 3.16 vermerkt) |
| Punkt 7, PSP 3.2.5, 3.6, 4.2.7 | eine Buchse im Boden, kein #5398, keine TPU-Lasche (R10, in 3.16 vermerkt) |
| Punkt 11, Abschnitt 1.4 | keine Reeds, kein Load-Switch |
| Punkt 13, PSP 4.7.1 | keine Magnete für den Sockel |
| Stückliste 1.1 | Pogo-Pins, Magnete, #5398, Breakout+Pigtail raus; Sink-Breakout rein |
| Stückliste 1.2 | „Dual-Ladestation“ und „Load-Switch + Reed“ → zwei Sockel nach Rev. 5 |
| PSP 3.5.1–3.5.4 | Verpolschutz durch USB-C; Kontakte im Stecker; Münztest bleibt (T6) |
| PSP 3.5 neu | Messung T0, Kragenprobe und Druckmuster (T1, T2) |
| PSP 4.1 | Maßkonzept Box-Boden: Tasche 14 tief, Zapfen, Kabelrinne |
| PSP 4.3.2 | Sturztest prüft auch Buchse und Zapfen (T10) |
| PSP 4.4 | „Ladesockel (2×)“ |
| PSP 5.6.8 (neu) | Start am Lader, offen |

---

## 9. Offen

1. T0 messen (Abzugskraft, Spannung am freien Stecker, Maße).
2. Kragenprobe drucken (T1), dann Druckmuster und Hebeltest (T2).
3. Anschluss der Buchse am PiSugar (Lötpads oder Eingang) am Muster festlegen.
4. 11 Software-Entscheidungen in `software_folgen.md`.
5. Maße der echten Box (CAD) übernehmen: Tasche, Zapfen und Akku-Abstand.
