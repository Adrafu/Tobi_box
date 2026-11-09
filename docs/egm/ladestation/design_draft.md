# Design: Ladestation (Dock) Tobi Box

* **Autor:** Tobias (Projektleitung: Claude als „Elefant“)
* **Datum:** 2026-11-09
* **Stand:** Draft vollständig (Abschnitte 1–8), bereit für Goldfisch-Review
* **Grundlage:** `docs/egm/ladestation/concepts_brief.md` (Entscheidungen
  D1–D7), `docs/plan/stueckliste-und-psp.md`, `docs/designs/box-software.md`

Werte mit **(R)** sind Richtwerte und werden am Muster gemessen oder geprüft.

---

## 1. Ziel und Anforderungen

Jede Box hat einen eigenen Sockel. Ein Kind stellt die Box ab, auch im
Dunkeln und in beliebiger Drehung, und sie lädt. Sonst passiert nichts: Die
Box wacht nicht auf, nichts leuchtet am Sockel.

| # | Anforderung | Herkunft |
|---|---|---|
| A1 | Box lädt in jeder der vier Drehlagen. | D2 |
| A2 | Kind dockt blind an: Die Box findet über einen Fangtrichter selbst in Lage. | D1 |
| A3 | Kind hebt die Box einhändig ab, der Sockel bleibt stehen. | D1 |
| A4 | Ohne aufsitzende Box sind die Sockel-Kontakte spannungslos. | Plan 1.4 |
| A5 | Beim USB-C-Laden sind die Box-Kontakte spannungslos. | Punkt 7 |
| A6 | Münze oder Löffel auf Sockel oder Box richtet nichts an, auch nicht, wenn ein fremder Magnet den Reed auslöst. | PSP 3.5.4, 8.3.4 |
| A7 | Andocken weckt die Box nicht. | Punkt 3, PSP 8.2.4 |
| A8 | Je Sockel genug Strom, dass eine leere, laufende Box (Sync, Musik) noch lädt. | PSP 8.4.5 |
| A9 | Keine Magnete, Kleinteile oder Kontakte, die ein Kind herauslösen kann. | Punkte 13–15 |
| A10 | Kein Metall näher als 2–3 cm an der NFC-Antenne. | Punkt 10 |
| A11 | Keine Anzeige am Sockel. | D6 |
| A12 | Kein Signal vom Sockel zur Box. Die Box erkennt „am Lader“ selbst über den PiSugar. | box-software.md |

**Nicht Ziel:** Laderegelung im Sockel, Datenverbindung, Ladeanzeige am
Sockel, ein gemeinsames Netzteil für beide Boxen.

---

## 2. Aufbau im Überblick

```
 Steckdose                Sockel                              Box
 ─────────               ─────────────────────────────────    ──────────────────────
 USB-C-NT ──USB-C──► Breakout ─► PTC ─► Load-Switch ─► Mittel-Pin ═► Mittelfläche ─► #5398 Eing. A ─┐
 5 V / 3 A          (5,1 kΩ CC)          #2810   ▲                                                ├─► PiSugar 3 Plus
                                                 │ ON                       USB-C außen ─► #5398 Eing. B ┘
                                   Reed ◄─ Magnet der Box
                     GND ───────────────────────────── Ring-Pins ══► Ring ───────── GND
```

- Der Sockel schaltet Plus erst ein, wenn der Reed den Magneten der Box sieht.
- Die Box nimmt den Strom über die Ideal-Diode #5398. Der PiSugar lädt.
- Masse liegt dauerhaft am Ring. Das ist ungefährlich, weil ohne Plus kein
  Strom fließt.

---

## 3. Kontaktbild und Zentrierung

### 3.1 Kontaktbild (D2, D3)

```
Box-Boden (von unten)          Sockel (von oben)

   ┌─────────────────┐          ┌─────────────────┐
   │ M             M │          │ m             m │
   │     ╭─────╮     │          │        o        │
   │    ╱ Ring  ╲    │          │                 │
   │   │   (●)   │   │          │  o     ●     o  │
   │    ╲ GND   ╱    │          │                 │
   │     ╰─────╯     │          │        o        │
   │ M             M │          │ m             m │
   └─────────────────┘          └─────────────────┘
   ● Mittelfläche = +5 V        ● Mittel-Pin = +5 V
   Ring = GND                   o Ring-Pins = GND
   M = Magnete                  m = Gegenstück, Reed unter einem
```

- **Box:** runde Kontaktscheibe, Mittelfläche Ø 10 mm (R), Spalt 4 mm (R),
  Ring 5 mm breit (R). Außendurchmesser damit ~28 mm.
- **Sockel:** 1 Mittel-Pin (+5 V), 3 Ring-Pins (GND) im 120°-Abstand auf dem
  Ringradius. Drei Pins stehen auch bei leichter Schräglage sicher auf.
- **Plus in der Mitte:** Die Mittelfläche ist klein und tief im Boden, ein
  Finger oder eine flache Münze erreicht sie schwerer als den Ring.
- **Strom:** Mittel-Pin trägt allein den Plus-Strom. Daher einen Pogo-Pin mit
  ≥ 3 A Dauerstrom wählen, oder zwei eng nebeneinander in der Mitte (R).

### 3.2 Zentrierung in zwei Stufen

1. **Grob: Fangtrichter.** Die Mulde im Sockel ist quadratisch wie der Würfel,
   mit 45°-Schrägen nach außen. Ein Kind stellt die Box irgendwo in die Nähe,
   sie rutscht hinein. Spiel am Grund ~1 mm je Seite (R).
2. **Fein: Zentrierzapfen.** Auf dem Sockelboden sitzt ein runder Zapfen, in
   dem die Pins stecken. Die Box hat unten eine passende runde Tasche, 3–4 mm
   tief, an deren Grund die Kontaktscheibe liegt. Der Zapfen zentriert die
   Kontakte auf ±0,5 mm (R).

Die Tasche erfüllt zugleich „Kontakte 3–4 mm versenkt“ (PSP 3.5.3). Eine
flach liegende Münze erreicht die Box-Kontakte nicht. Steht die Box auf dem
Tisch, ruht sie auf dem Rand, nicht auf der Scheibe.

### 3.3 Herstellung der Kontaktscheibe (offen)

| Variante | Vorteil | Nachteil |
|---|---|---|
| Runde Leiterplatte, ENIG-vergoldet, ohne Bauteile | maßhaltig, korrosionsfest, 2 Lötpads hinten | Bestellung mit Wartezeit, ~10–15 € mit Versand für 5 Stück (R) |
| Messing (Scheibe + Ring, eingeklebt) | sofort, im Baumarkt | Ring schwer genau zu fertigen, Messing läuft an |

Vorschlag: Leiterplatte, zusammen mit anderen Teilen bestellen. Entscheidung
Tobias.

---

## 4. Elektrik

### 4.1 Sockel

Je Sockel, alles fertige Module (D7):

| Teil | Aufgabe | Auswahl |
|---|---|---|
| USB-C-Breakout mit 5,1 kΩ an CC1/CC2 | holt 5 V aus dem USB-C-Netzteil | wie in der Box (Stückliste 1.1) |
| PTC (rückstellbare Sicherung) | zweite Schutzschicht nach dem Netzteil | Haltestrom nach Messung PiSugar, Vorschlag 2,5 A Halte-, ~5 A Auslösestrom (R) |
| Pololu #2810 | Load-Switch, schaltet Plus | 3 A Dauerstrom, ON-Pin > 1 V = ein |
| Reed-Kontakt, gekapselt, Schließer | gibt ON frei, wenn Box-Magnet da ist | Typ nach Abstandstest |
| Widerstand 100 kΩ (R) | zieht ON auf GND, wenn Reed offen | Pflicht: Ein eigener Pulldown ist im Datenblatt nicht genannt |
| Pogo-Pins | 1× Mitte, 3× Ring | ≥ 3 A Mitte, ≥ 1 A Ring |

**Schaltung Reed:** Reed zwischen 5 V (nach dem PTC) und ON-Pin des #2810,
100 kΩ von ON nach GND. Reed zu → ON = 5 V → Schalter ein. Reed offen → ON auf
GND → aus. Schieber des #2810 fest auf „off“, dann steuert nur der ON-Pin.

**Pololu #2810 (Recherche 09.11., Produktseite, kein PDF-Datenblatt):**
- ON-Pin: > ~1 V = ein, offen oder Low = aus, bis 30 V unabhängig von VIN.
  5 V dauerhaft liegen innerhalb der Angabe.
- Betrieb 1,8–16 V, 3 A Dauerstrom bei 12 V und 22 °C in ruhender Luft. Für
  5 V ist kein eigener Wert angegeben (R).
- Kein Softstart angegeben. Rote LED auf der Platine leuchtet im EIN-Zustand.
- Vor dem Einbau am Schaltplan prüfen: Schieberstellung und Pulldown
  (https://www.pololu.com/file/0J888/mini-mosfet-slide-switch-schematic-diagram.pdf).
- Die Varianten #2811 (erst ab 4,5 V, 2 A) und Taster-Varianten passen nicht.

**Ruhestrom ohne Box:** Load-Switch aus, Reed offen. Es fließt nur der
Ruhestrom von Netzteil und #2810. Die rote LED des #2810 sitzt verdeckt im
Sockel und leuchtet nur bei aufsitzender Box. Sie verstößt damit nicht gegen
A11, kostet aber Strom (~1 mA) und wird abgelötet.

### 4.2 Box

- Kontaktscheibe: Mitte → Eingang A des #5398, Ring → GND.
- USB-C außen → Eingang B des #5398 (unverändert, PSP 3.2.5).
- Ausgang #5398 → Ladeeingang PiSugar 3 Plus.
- Der #5398 sperrt rückwärts: Beim USB-C-Laden liegen an der Kontaktscheibe
  0 V (A5). Prüfung am Muster mit Multimeter (PSP 8.4.5).
- Nichts weiter an der Box. Die Software erkennt „am Lader“ über den PiSugar
  (A12).

### 4.3 Reihenfolge beim Andocken und Abheben

**Andocken:** Der Reed muss erst schließen, wenn die Pins schon auf der Scheibe
aufsitzen. Sonst liegt Plus schon an, bevor die Pins Kontakt haben, und
der erste Kontakt kann funken. Bei 5 V ist das harmlos, aber es nutzt die
Oberflächen ab. Daher Reed-Lage und -Abstand so wählen, dass er erst bei
≤ 2 mm Restabstand schließt (R, Abstandstest).

**Abheben:** Die Pins verlieren den Kontakt, bevor der Reed öffnet. Der
Ladestrom reißt an den Pins ab. Bei 5 V und ~2 A ist das unkritisch (R). Der
PiSugar wechselt auf Akku, die Box läuft weiter.

**Wecken (A7):** Strom am Ladeeingang weckt den PiSugar 3 Plus nur, wenn
Auto-Power-On an ist. Es bleibt aus (PSP 5.6.5). Test PSP 8.2.4.

### 4.4 Strombedarf (A8)

Das Ergebnis der Recherche reicht nicht. Messung am Muster (neu, gehört zu
PSP 3.1):

| Messung | Zustand | Erwartung (R) |
|---|---|---|
| M1 | Akku leer, Box aus, am USB-C-Netzteil | Ladestrom PiSugar, vermutlich 1,5–2,5 A |
| M2 | Akku leer, Box läuft (Sync + Musik laut) | M1 + 0,4–0,6 A |
| M3 | Spannung am PiSugar-Eingang bei M2, über Pogo und #5398 | ≥ 4,75 V (R) |

Ein USB-C-Netzteil mit 3 A je Sockel reicht, wenn M2 ≤ 2,7 A. Der PTC-Wert
folgt aus M2.

---

## 5. Magnete und Reed

### 5.1 Magnete in der Box

- Vier Neodym-Magnete 8×3 mm in den vier Ecken des Box-Bodens, im
  90°-Raster um die Mitte. Damit sitzt in jeder Drehlage ein Magnet über
  derselben Sockel-Ecke (A1).
- Alle mit gleicher Polung nach unten (Nordpol unten).
- Voll eingeschlossen: Beim Druck in eine Tasche gelegt, Druckpause, mit
  ≥ 1 mm PETG überdruckt, zusätzlich eingeklebt (Punkt 13, PSP 4.7.1).
- Abstand zur NFC-Antenne oben: ~10 cm (A10).

### 5.2 Gegenstück im Sockel: keins (Vorschlag)

Der Plan nennt die Magnete „Zentriermagnete“. Die Zentrierung übernehmen jetzt
Fangtrichter und Zapfen (3.2). Die Magnete werden nur noch für den Reed
gebraucht.

| Variante | Für | Gegen |
|---|---|---|
| **Kein Gegenstück (Vorschlag)** | billigster Weg; A3 (einhändig abheben) ist sicher erfüllt; kein Magnet im Sockel, der den Reed dauernd auslöst | Box hält nur durch ihr Gewicht |
| Stahlscheiben in 3 Ecken, Reed in der 4. | Box rastet spürbar ein | Stahl darf nicht über dem Reed liegen; Haltekraft muss klein bleiben (A3) |
| Gegenmagnete | stärkstes Einrasten | Ein Magnet im Sockel löst den Reed dauernd aus. Er muss also weit weg vom Reed sitzen, was in jeder Drehlage schwer geht. Zusätzlich lose Magnete im Sockel (Punkt 13) |

**Gewicht gegen Federkraft:** Vier Pogo-Pins drücken mit je ~70 g (R), also
~0,3 kg. Die Box wiegt geschätzt 0,6–0,9 kg (Akku, Lautsprecher, PETG) (R).
Sie bleibt also aufsitzen. Prüfung am Muster (T4). Hebt die Federkraft die Box
an oder sitzt sie wackelig, kommen Stahlscheiben in drei Ecken dazu.

### 5.3 Reed-Kontakt

- Sitzt unter dem Boden einer Sockel-Ecke, genau unter der Position eines
  Box-Magneten.
- **Gekapselte Bauform** (Kunststoff-umspritzt), kein nacktes Glasröhrchen.
  Typ nach Abstandstest T1. Kandidaten recherchiert ein Agent vor der
  Bestellung.
- **Wenig empfindlich wählen:** Der Reed soll erst bei ≤ 2 mm Restabstand
  schließen (4.3). Das hilft auch gegen fremde Magnete: Ein Tonie-Sockel oder
  ein Kühlschrankmagnet muss dann direkt in der Ecke liegen.
- Die Bodendicke über dem Reed ist der Stellhebel: dicker = später schalten.
- **Alternative Hall-Schalter** (z. B. DRV5032): keine bewegten Teile,
  aber ständiger Ruhestrom und ein weiteres Modul. Nur, wenn kein Reed
  zuverlässig schaltet.

### 5.4 Fremdmagnet (A6)

Ein fremder Magnet in der richtigen Ecke schaltet Plus an den Mittel-Pin.
Schlimmster Fall: Gleichzeitig liegt ein Löffel quer über Mittel- und
Ring-Pin. Dann fließt Kurzschlussstrom, bis das Netzteil abschaltet (USB-C-
Netzteile haben Überstromschutz) oder der PTC auslöst. Bei 5 V gibt es keine
Gefahr durch Berührung, nur Wärme am Löffel und an den Pins. Test T6 prüft,
dass dabei nichts heiß wird. Fällt T6 durch, kommt die eFuse-Platine (D7).

---

## 6. Mechanik

Maße sind Richtwerte für einen Würfel mit 120 mm Kante. Sie folgen dem
Box-CAD, das es noch nicht gibt. Vor allem die TPU-Ecken der Box bestimmen das
Innenmaß des Trichters.

### 6.1 Sockel

```
Schnitt durch den Sockel (seitlich)

        ╲                                       ╱   ← Fangschräge 45°
         ╲_____________________________________╱
         │                                     │    ← Führungswand ~15 mm
         │            ┌─o──●──o─┐              │    ← Zapfen Ø ~26 mm, 3 mm hoch,
         │____________│_________│______________│      Pins ragen ~1 mm heraus
         │  Elektronik: Breakout, PTC, #2810    │    ← Boden 12–15 mm
         │  Reed unter einer Ecke               │
         └──────────────────────────────────────┘
          Füße TPU            USB-C hinten ►
```

- **Innenmaß am Grund:** Box + 1 mm je Seite, also ~122 × 122 mm (R).
- **Fangschräge:** 45°, ~8 mm hoch. Öffnung oben ~138 mm. Eine Box, die
  bis ~8 mm daneben aufgesetzt wird, rutscht hinein (A2).
- **Außenmaß:** ~150 × 150 mm, Höhe ~30 mm (R).
- **Zapfen:** Ø ~26 mm, 3 mm hoch, oben 1 mm angefast. Er sitzt in der Mitte
  und trägt die vier Pogo-Pins. Krümel fallen vom Zapfen auf den Boden.
- **USB-C-Buchse:** hinten, versenkt, Breakout verschraubt. Kabelzug wirkt auf
  das Gehäuse, nicht auf die Lötstellen.
- **Unterseite:** Deckel mit Torx-Schrauben (Punkt 15), vier TPU-Füße, rutschfest.
- **Abheben (A3):** Nichts hält die Box fest (5.2). Der Sockel bleibt stehen,
  auch wenn das Kind schräg zieht. Bei leichtem Sockel ggf. Gewicht im Boden (R).
- **Farbe:** offen (schwarz, oder passend zur Box).

### 6.2 Box-Boden

- Runde Tasche in der Mitte: Ø ~27 mm, 3,5 mm tief, Rand angefast. Passt mit
  ~0,5 mm Spiel über den Zapfen.
- Kontaktscheibe am Grund der Tasche. Sie wird von innen eingesetzt, die
  Kontakte zeigen nach außen. Von außen kann man sie nicht herausziehen
  (Punkt 14). Leitungen von hinten an Mitte und Ring gelötet, zum #5398 und
  GND.
- Vier Magnettaschen in den Ecken (5.1).
- Die Box steht auf dem Tisch auf ihrem Rand und den TPU-Ecken, nie auf der
  Kontaktscheibe.

---

## 7. Tests

| # | Test | Bestanden, wenn | PSP |
|---|---|---|---|
| T1 | Reed-Abstand mit 8×3-mm-Magnet durch die geplante Bodendicke | Schließt erst bei ≤ 2 mm Restabstand, öffnet sicher beim Abheben | 3.5.2 |
| T2 | Strom M1–M3 (4.4) | M2 ≤ 2,7 A, Spannung am PiSugar ≥ 4,75 V | 3.1 (neu) |
| T3 | Andocken weckt nicht: 20× aufsetzen, alle vier Lagen, Box aus | Box bleibt aus, lädt | 8.2.4 |
| T4 | Blind andocken: 20× mit geschlossenen Augen, alle vier Lagen | Jedes Mal Laden (PiSugar meldet Lader), Box sitzt fest | neu |
| T5 | Einhändig abheben, auch schräg | Sockel bleibt stehen, nichts klemmt | neu |
| T6 | Sockel ohne Box: Münze, Löffel, Alufolie auf den Pins. Dann Fremdmagnet in der Reed-Ecke und Löffel über Mitte und Ring, 5 min | Ohne Magnet 0 V an den Pins. Mit Magnet: Netzteil oder PTC schaltet ab, Löffel und Pins < 50 °C, danach normal | 3.5.4, 8.3.4 |
| T7 | Box am USB-C: Kontaktscheibe messen, Münze in die Tasche | 0 V an der Scheibe, nichts passiert | 3.5.4, 8.4.5 |
| T8 | USB-C und Sockel gleichzeitig | Box lädt, keine Rückspeisung in eine der Quellen | 8.4.5 |
| T9 | Volle Ladung leer → voll am Sockel | #2810, PTC, Pins < 50 °C | neu |
| T10 | Krümel (Brösel, Sand) auf dem Zapfen, dann andocken | Lädt weiter oder lässt sich mit einem Wisch reinigen | 8.3.2 |

---

## 8. Stückliste und Abweichungen vom Plan

### 8.1 Je Sockel (2×)

| Teil | Stk | ca. € (R) |
|---|---|---|
| USB-C-Netzteil 5 V / 3 A (entfällt, wenn vorhanden) | 1 | 12 |
| USB-C-Breakout mit 5,1 kΩ an CC | 1 | 2 |
| Pololu #2810 Mini MOSFET Slide Switch LV | 1 | 5 |
| PTC, Wert nach T2 | 1 | 1 |
| Reed-Kontakt, gekapselt, Schließer | 1 | 3 |
| Widerstand 100 kΩ, Litze, Schrumpfschlauch | — | 1 |
| Pogo-Pins (1 Mitte ≥ 3 A, 3 Ring) | 4 | 4 |
| PETG + TPU-Füße (Druck), Torx-Schrauben | — | 4 |
| **Summe je Sockel** | | **~32 (ohne Netzteil ~20)** |

### 8.2 Je Box zusätzlich

| Teil | Stk | ca. € (R) |
|---|---|---|
| Kontaktscheibe (runde Leiterplatte, ENIG), anteilig mit Versand | 1 | 3 |
| Neodym-Magnete 8×3 mm (schon in 1.1) | 4 | — |

### 8.3 Abweichungen vom Plan (nach dem Resolve in `docs/plan/` nachtragen)

| Stelle im Plan | Bisher | Neu |
|---|---|---|
| Stückliste 1.1 „Pogo-Pins 2-polig, gefedert“ (5 €) | Pogo-Pins in der Box | Kontaktscheibe in der Box (~3 €), Pogo-Pins wandern in den Sockel |
| Stückliste 1.2 „Dual-Ladestation (Netzteil 5 V/4 A, Buchse, Druckteil)“ (22 €) und „Load-Switch + Reed-Kontakt je Ladeplatz“ (8 €) | ein Dock, ein Netzteil, ~30 € | zwei Einzelsockel mit je eigenem USB-C-Netzteil, ~40 € ohne bzw. ~64 € mit neuen Netzteilen |
| Punkt 11 „Zentriermagnet“ | Magnet zentriert und löst den Reed aus | Zentrierung über Trichter und Zapfen; Magnete nur für den Reed |
| PSP 3.5.1 Verpolschutz | offen | durch die Form: Plus Mitte, Masse Ring |
| PSP 4.4 „Dual-Ladestation“ | ein Teil | „Ladesockel“ (2×) |
| PSP 3.1 | — | neu: Strommessung M1–M3 am PiSugar 3 Plus |
| Gesamtbudget | ~575 € | +10 bis +35 €, je nach vorhandenen Netzteilen |

### 8.4 Offen für den Resolve

1. Kontaktscheibe: Leiterplatte oder Messing (3.3).
2. Gegenstück im Sockel: keins oder Stahlscheiben (5.2), nach T4.
3. Reed-Typ nach T1.
4. PTC-Wert nach T2.
5. Farbe des Sockels.
6. Vorhandene USB-C-Netzteile nutzen?
