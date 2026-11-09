# Design: Ladesockel Tobi Box (Kontakte)

* **Autor:** Tobias (Projektleitung: Claude als „Elefant“)
* **Datum:** 2026-11-09
* **Stand:** **Rev. 2**, nach Goldfisch-Review und Resolve. Vergleich mit
  induktivem Laden (Qi) in Abschnitt 9, Entscheidung offen.
* **Grundlage:** `concepts_brief.md` (D1–D6), `resolve.md` (R1–R4 und
  Übernahmen), `review_elektrik.md` (E1–E17), `review_mechanik.md` (M1–M21),
  `research_qi.md`, `docs/plan/stueckliste-und-psp.md` (Rev. 3.16),
  `docs/designs/box-software.md`
* **Rev. 1:** im Git-Verlauf dieser Datei (Commit „Draft vollständig“)

Werte mit **(R)** sind Richtwerte. Sie werden am Muster gemessen oder vom
Agent beim Platinenentwurf aus Datenblättern belegt. In eckigen Klammern steht,
welcher Befund eine Regel begründet.

---

## 1. Ziel und Anforderungen

Jede Box hat einen eigenen Sockel. Ein Kind stellt die Box ab, auch im
Dunkeln und in beliebiger Drehung, und sie lädt. Sonst passiert nichts: Die
Box wacht nicht auf, nichts leuchtet am Sockel, und kein Gegenstand auf dem
Sockel kann heiß werden.

| # | Anforderung | Herkunft |
|---|---|---|
| A1 | Box lädt in jeder der vier Drehlagen. | D2 |
| A2 | Kind dockt blind an: Die Box findet ohne Nachhelfen in die Lage, auch verdreht (bis 15°), schräg und mit Schwung aus 5–10 cm. | D1, M16 |
| A3 | Kind hebt die Box einhändig ab, der Sockel bleibt stehen. | D1, M11 |
| A4 | Ohne aufsitzende Box sind die Sockel-Pins spannungslos. Ein einzelner fremder Magnet ändert daran nichts. | Plan 1.4, E4 |
| A5 | Beim USB-C-Laden ist die Kontaktscheibe der Box spannungslos. | Punkt 7 |
| A6 | Kein Gegenstand auf den Pins wird heiß: Strom ist begrenzt, bei Übertemperatur wird abgeschaltet. Pin-Halter und Platine vertragen den ungünstigsten Fall. | E1, R1 |
| A7 | Andocken weckt die Box nicht, auch nicht bei leerem Akku, Flackern oder eingestecktem Netzteil mit aufsitzender Box. | Punkt 3, E9 |
| A8 | Ladestrom am Sockel ≥ 90 % des Ladestroms am USB-C, auch wenn die Box läuft. | E7 |
| A9 | Keine Magnete, Kleinteile oder Kontakte, die ein Kind herauslösen kann, auch nach einem Sturz. | Punkte 13–15, M14, M15 |
| A10 | Kein Metall und keine Zuleitung näher als 3 cm an der NFC-Antenne. | Punkt 10, M18 |
| A11 | Keine Anzeige am Sockel. | D6 |
| A12 | Kein Signal vom Sockel zur Box. Die Box erkennt „am Lader“ selbst über den PiSugar. | box-software.md |
| A13 | Verschüttete Flüssigkeit läuft ab und erreicht die Elektronik nicht. | M9, E10 |
| A14 | Kontakte halten ≥ 3 Jahre bei 6 Andockvorgängen am Tag (~6500 Zyklen). | M8 |

**Nicht Ziel:** Laderegelung im Sockel, Datenverbindung, Anzeige am Sockel,
ein gemeinsames Netzteil für beide Boxen, Kindertest vor der Abnahme (R4).

---

## 2. Aufbau im Überblick

```
 Steckdose          Sockel (eine Platine)                                Box
 ─────────          ───────────────────────────────────────────          ───────────────────────────
 Netzteil  ─USB-C─► Buchse ─► TVS ─► C ─► eFuse ─► 3 Mittel-Pins ═► Mittelfläche ─► #5398 A ─┐
 5,1 V/3 A          5,1 kΩ CC              ▲ EN (RC-Verzögerung)                              ├─► PiSugar 3 Plus
                                           │                          USB-C außen ─► #5398 B ┘
                         Reed 1 ── Reed 2 ─┘  (in Reihe, gegenüberliegende Ecken)
                    GND ──────────────────────── 3 Ring-Pins (länger) ═► Ring ─────── GND
```

- Plus liegt erst an, wenn **beide** Reeds die Box sehen und die Verzögerung
  abgelaufen ist.
- Die eFuse begrenzt den Strom, schaltet bei Überstrom und Übertemperatur ab
  und fährt die Spannung sanft hoch.
- Masse liegt dauerhaft am Ring. Ohne Plus fließt kein Strom.

---

## 3. Kontaktbild

### 3.1 Kontaktscheibe in der Box (R2)

Runde Leiterplatte, **Hartgold**, ohne Bauteile, von innen eingesetzt.

```
   Kontaktscheibe (von unten)           Maße (R)
        ╭───────────╮                   Mittelfläche (+5 V)   r 0–6 mm   (Ø 12)
      ╱   Ring GND    ╲                 Spalt                 r 6–10 mm
     │    ╭─────╮      │                Ring (GND)            r 10–16 mm (Ø 32)
     │    │ +5V │      │                Flansch innen         Ø 38 mm, 1,6 mm
     │    ╰─────╯      │                Lötpads hinten        2× für Litze 0,5 mm²
      ╲               ╱
        ╰───────────╯
```

### 3.2 Pins im Sockel

| Pins | Lage | Funktion |
|---|---|---|
| 3 Mittel-Pins | auf Kreis r = 2,5 mm, 120° | +5 V, teilen sich den Strom [E8] |
| 3 Ring-Pins | auf Kreis r = 13 mm, 120° | GND, **0,3 mm länger** als die Mittel-Pins: Masse kontaktiert zuerst und trennt zuletzt [E5] |

- Pin-Typ: gefederter Pogo-Pin mit **≥ 1,5 mm Hub**, Dauerstrom ≥ 2 A und
  Federkraft am Arbeitspunkt aus dem Datenblatt. Den Typ wählt der
  Platinen-Agent. Die Pins werden **auf die Sockel-Platine gelötet** [M15].
- Drei Pins je Pol stehen auch bei leichter Schräglage sicher auf.

### 3.3 Toleranzrechnung Kontakt [M6, E14]

Zentrierung am Kontakt: ±1,0 mm (aus 4.2). Pin-Kopf Ø 1,5 mm (R).

| Prüfung | Rechnung | Abstand |
|---|---|---|
| Mittel-Pin bleibt auf der Mittelfläche | 2,5 + 1,0 + 0,75 = 4,25 < 6 | 1,75 mm Reserve |
| Mittel-Pin berührt nie den Ring | 4,25 < 10 | 5,75 mm |
| Ring-Pin bleibt auf dem Ring (innen) | 13 − 1,0 − 0,75 = 11,25 > 10 | 1,25 mm Reserve |
| Ring-Pin bleibt auf dem Ring (außen) | 13 + 1,0 + 0,75 = 14,75 < 16 | 1,25 mm Reserve |
| Ring-Pin berührt nie die Mitte | 11,25 > 6 | 5,25 mm |

Kein Pin kann Plus und Masse gleichzeitig berühren. Das gilt auch beim
schrägen Aufsetzen, solange die Box im Fangkegel ist (4.2).

---

## 4. Mechanik

Maße für einen Würfel mit 120 mm Kante. Sie werden an der **gedruckten Box
nachgemessen**, bevor der Sockel gedruckt wird [M3].

### 4.1 Höhenkette [M2]

Bezugsebene ist die **Auflagefläche**: Die Box liegt mit ihrem PETG-Boden auf
dem flachen Mulden-Boden auf. Die TPU-Ecken tragen nicht, die Mulde hat in den
Ecken Freistiche.

| Maß | Wert (R) | Toleranz Druck |
|---|---|---|
| Kontaktscheibe über Auflage (Tiefe der Tasche) | 4,5 mm | ±0,2 |
| Zapfen über Auflage | 4,0 mm | ±0,2 |
| Spitze Mittel-Pin frei über Auflage | 5,25 mm | ±0,1 |
| Spitze Ring-Pin frei über Auflage | 5,55 mm | ±0,1 |
| Einfederung Mittel-Pin im Endstand | 0,75 mm (Bereich 0,45–1,05) | — |
| Einfederung Ring-Pin im Endstand | 1,05 mm (Bereich 0,75–1,35) | — |

Bei 1,5 mm Hub bleibt jeder Pin in jedem Fall im Arbeitsbereich. Der Zapfen
(4,0) endet 0,5 mm unter der Scheibe (4,5) und stößt nie an.

### 4.2 Zentrierung in zwei Stufen [M3, M4, M5]

```
Schnitt Sockel mit Box (seitlich, nicht maßstäblich)

     │ Box │                                         │ Box │
     │     └────╲         ┌Scheibe┐         ╱────────┘     │   ← Tasche konisch
     │           ╲________│_______│________╱                │
 ╲   └────────────╲   o  ●●●  o  ╱───────────────────────┘   ╱  ← Mulde 60°, durchgehend
  ╲    2 mm Spiel   ╲____________╱  Zapfen konisch 45°        ╱
   ╲_______________________________________________________╱   ← Auflage, 2° Gefälle nach außen
   │ Rinne + Ablauf │  Platine (dicht unter dem Zapfen)  │ Rinne │
   │  Gewicht 300–400 g        Reed 1 / Reed 2 in den Ecken     │
   └────────────────────────────────────────────────────────────┘
```

1. **Grob: Mulde.** Innenmaß am Boden 124 × 124 mm, also 2 mm Spiel je Seite.
   Die Wände laufen **durchgehend schräg** mit 60° bis oben, ohne senkrechte
   Führungswand, 20 mm hoch. Öffnung oben ~147 × 147 mm. Bei 2 mm Spiel und
   ohne parallele Wand klemmt die Box auch bei 15° Drehversatz nicht. Die
   Gleitflächen sind glatt gedruckt (feine Schicht, Oberseite). Die echte
   TPU-Ecke wird vorher auf einer 60°-Probe getestet, ob sie rutscht [M4].
2. **Fein: konischer Zapfen.** Zapfen Ø 40 mm am Fuß, Ø 32 mm oben, 4 mm hoch
   (45°). Die Tasche der Box ist ebenso konisch: Ø 42 mm an der Bodenfläche,
   Ø 34 mm in 4 mm Tiefe. **Fangbereich ±4 mm**, größer als das Mulden-Spiel
   (±2 mm). Die Box wird also immer vom Kegel geführt. Endspiel ±1 mm.

### 4.3 Sockel

- Außenmaß ~155 × 155 mm, Höhe ~35 mm (15 mm Unterteil + 20 mm Mulde) (R).
- **Gewicht 300–400 g** im Unterteil (Stahlscheiben, eingeklebt, verdeckt)
  [M11, M19]. Ziel: Abheben schräg mit Klemmen hebt den Sockel nicht an,
  Seitenstoß kippt ihn nicht.
- Vier TPU-Füße mit Zapfen, eingeklebt [M15].
- **Ablauf [M9, E10]:** Der Mulden-Boden fällt mit 2° vom Zapfen nach außen in
  eine umlaufende Rinne. Vier Bohrungen führen aus der Rinne nach unten ins
  Freie, außerhalb des Elektronikfachs.
- **Elektronikfach dicht:** Die Platine sitzt unter dem Zapfen. Zwischen
  Platine und Zapfen-Unterseite liegt eine Silikondichtung. Die Pins ragen
  durch eng gebohrte Löcher im Zapfen.
- USB-C-Buchse sitzt auf der Platine an der Rückwand, versenkt. Das Kabel des
  Netzteils hat eine Zugentlastung im Gehäuse, Kabelzug geht nicht auf die
  Buchse.
- Unterseite mit Torx verschraubt (Punkt 15).

### 4.4 Box-Boden

- Konische Tasche in der Mitte (4.2), Kontaktscheibe am Grund, von innen
  eingesetzt. Der Flansch (Ø 38 mm) liegt innen am Boden an und ist mit Epoxy
  verklebt. Von außen kann man sie nicht herausdrücken oder -ziehen [M15].
- **Münze:** Eine 2-€-Münze passt in die Tasche und kann Mitte und Ring
  berühren. Das ist unkritisch, weil die Box-Seite spannungslos ist (A5). Der
  Satz aus Rev. 1, dass keine Münze die Kontakte erreicht, war falsch [M7].
- Zuleitung von der Scheibe zum #5398 am Boden und an der Rückwand entlang,
  ≥ 3 cm von der Antennenebene [M18].
- Pflegehinweis für Eltern: Tasche gelegentlich auswischen, vor allem nach
  Teppich [M21].

### 4.5 Magnete und Reeds

- **Box:** vier Magnete 8×3 mm auf den Diagonalen, je 35 mm von der Mitte in
  x und y, also ~25 mm von den Kanten, in der PETG-Bodenplatte und nicht in
  den TPU-Ecken [M12]. Abdeckung ≥ 1,2 mm PETG, beim Druck eingeschlossen und
  zusätzlich eingeklebt. Die Polung ist egal, Reeds reagieren auf beide Pole.
- **Sockel:** zwei gekapselte Reeds an zwei gegenüberliegenden Diagonal-Punkten
  (+35/+35 und −35/−35 mm), in Reihe geschaltet [E4]. Die Box hat in jeder
  Drehlage an beiden Punkten einen Magneten. Ein einzelner fremder Magnet
  (Tonie, Magnetbaustein, Handyhülle) erreicht nie beide, sie liegen ~99 mm
  auseinander.
- **Abstand Magnet–Reed im Endstand** („Restabstand“, gemessen von
  Magnet-Unterseite bis Reed-Mitte): ~4–5 mm (1,2 Abdeckung + 2 Mulden-Boden
  + Gehäuse Reed) (R). Der Reed muss bei **≥ 1,5 × diesem Abstand** sicher
  schließen, also bei ≥ 7 mm (R) [M1]. Ob er liegend längs, quer oder um eine
  halbe Reed-Länge versetzt am besten schaltet, klärt T1 [M13].
- Kein Gegenstück im Sockel. Die Box hält durch ihr Gewicht. Die Federkraft
  der sechs Pins am Arbeitspunkt muss laut Datenblatt deutlich unter dem
  Box-Gewicht liegen. Prüfung in T4.

---

## 5. Elektrik

### 5.1 Sockel-Platine (R1)

Eine Platine je Sockel, **vom Hersteller bestückt**. Tobias lötet nur die zwei
Reed-Leitungen an. Den Schaltplan und das Layout macht nach der Annahme ein
Agent (Sonnet). Dies sind die Vorgaben:

| Block | Vorgabe | Befund |
|---|---|---|
| USB-C-Buchse | nur 5 V, 5,1 kΩ an CC1 und CC2 | E3 |
| Eingangsschutz | TVS-Diode für 5 V, Elko 47–100 µF | E6 |
| eFuse | z. B. TI TPS25947 oder gleichwertig. Stromgrenze fest auf ~2,7 A (nach Messung M2 nachstellbar über einen Widerstand), **Übertemperatur-Abschaltung**, Softstart über dV/dt-Kondensator (~5–10 ms), **Latch-Variante**: nach einem Fehler bleibt sie aus, bis die Box abgehoben wird (EN geht auf Low) | E1, E2, E6 |
| Freigabe (EN) | Reed 1 und Reed 2 in Reihe von 5 V nach EN. RC-Verzögerung 0,1–0,5 s (z. B. 100 kΩ und 2,2 µF), Pulldown an EN | M1, E5, E6, M10 |
| Pins | 3 Mittel-Pins an den eFuse-Ausgang, 3 Ring-Pins an GND, direkt gelötet | E8, M15 |
| Leiterbahnen | für 3 A ausgelegt, kurze Wege, Masseflächen | E7 |
| Keine LED | auch keine Status-LED auf der Platine | A11 |

**Ablauf beim Andocken:** Die Box rutscht in den Kegel. Masse-Pins berühren
zuerst den Ring, dann die Mittel-Pins die Mitte. Beide Reeds schließen. Nach
der RC-Verzögerung gibt EN frei, die eFuse fährt sanft hoch. Prellen der Pins
fällt in die Verzögerung, es fließt noch kein Strom.

**Ablauf beim Abheben:** Die Mittel-Pins verlieren den Kontakt, der Ladestrom
reißt ab. Bei 5 V und ~2 A ist das unkritisch, der Softstart verhindert
wiederholte Stöße beim Wackeln. Der Masse-Kontakt trennt zuletzt. Dann
öffnen die Reeds, EN geht auf Low, eine verriegelte eFuse wird zurückgesetzt.

**Ungünstigster Fall (A6):** Zwei fremde Magnete an beiden Reed-Punkten und
ein Löffel mit 1–2 Ω über Mitte und Ring. Die eFuse begrenzt auf 2,7 A und
schaltet bei Übertemperatur ab. Die Pins sitzen in FR4, nicht in PETG.
T6 prüft das als Widerstandsreihe.

### 5.2 Netzteile (R3)

Zwei neue Markennetzteile, USB-C, 5 V/3 A, CE, Schutzklasse II, mit **fest
angeschlossenem Kabel**. Vorschlag: offizielles Raspberry-Pi-Netzteil 15 W
(5,1 V/3 A). Die 5,1 V helfen beim Spannungsbudget. T6 wird mit genau diesem
Typ gemacht. Keine No-Name-Netzteile [E3, E13].

### 5.3 Box

- Kontaktscheibe: Mitte → #5398 Eingang A, Ring → GND.
- USB-C außen → #5398 Eingang B (unverändert, PSP 3.2.5).
- **20-mΩ-Ausgleichswiderstand am #5398 per Jumper überbrückt** [E7, E16].
- Ausgang #5398 → Ladeeingang PiSugar 3 Plus.
- Sind beide Quellen dran, trägt die mit der höheren Spannung mehr Last. Das
  ist so gewollt, keine Quelle hat Vorrang [E16].

### 5.4 Spannungsbudget [E7]

Bei 2,5 A (R):

| Stufe | Abfall (R) | Spannung danach |
|---|---|---|
| Netzteil (Leerlauf 5,1 V, unter Last) | — | 5,05 V |
| Kabel 1,5 m, hin und zurück | 0,15 V | 4,90 V |
| eFuse + Platine | 0,08 V | 4,82 V |
| Pins (3 parallel je Pol) und Scheibe | 0,05 V | 4,77 V |
| Litze in der Box | 0,04 V | 4,73 V |
| #5398 (ohne Ausgleichswiderstand) | 0,03 V | **~4,70 V am PiSugar** |

Ob der PiSugar damit vollen Ladestrom zieht, ist offen. Kriterium A8: Ladestrom
am Sockel ≥ 90 % des Ladestroms am USB-C. T2 vergleicht beides direkt.

### 5.5 Wecken (A7) [E9]

Der PiSugar weckt bei Strom am Eingang nur, wenn Auto-Power-On aktiv ist. Es
bleibt aus (PSP 5.6.5). Die Quelle dazu ist noch zu belegen (docs.pisugar.com,
Recherche-Agent vor der Bestellung). Die Einstellung wird nach einem Akkutausch
oder Reset des PiSugar neu geprüft (Hinweis für PSP 9.4). T3 prüft die
Sonderfälle.

### 5.6 Hinweis an die Box-Software

Der Sockel flackert nicht, weil EN entprellt ist. Trotzdem soll die Software
„am Lader“ entprellen, etwa mit 10 s, bevor sie Sync oder Update startet
[M10]. Das ist kein Vertragsthema. Es wird bei AP Strom/Leerlauf (`idle.py`,
`power.py`) als Prüfpunkt vermerkt, Verträge bleiben unverändert.

---

## 6. Tests

Alle Tests macht Tobias (R4). Messungen im geschlossenen Sockel bei
Raumtemperatur ≥ 25 °C, wenn nicht anders gesagt.

| # | Test | Bestanden, wenn | Befund / PSP |
|---|---|---|---|
| T1 | Reed: Schalt- und Rückfallabstand, Lage (längs, quer, versetzt), seitlicher Versatz ±2 mm, Drehung 0–15°. Dann Fremdmagnete einzeln an jedem Reed-Punkt: Tonie, Magnetbaustein, Handyhülle, Kühlschrankmagnet, zweite Box daneben | Schließt im Endstand mit Faktor ≥ 1,5 Reserve in allen Lagen. Kein einzelner Fremdmagnet schaltet frei | M1, M13, E4, E17 / 3.5.2 |
| T2 | Ladestrom am Sockel gegen USB-C: Akku leer, Box aus (M1) und Box läuft mit Sync und Musik (M2). Spannung am PiSugar-Eingang (M3) | A8 erfüllt. Aus M2 folgt die endgültige Stromgrenze der eFuse | E7 / 3.1 |
| T3 | Wecken: 20× andocken in allen Lagen bei Box aus; bei leerem Akku; Netzteil einstecken mit aufsitzender Box; Box wackeln (Flackern); nach PiSugar-Reset | Box bleibt jedes Mal aus und lädt | E9 / 8.2.4 |
| T4 | Andocken wie ein Kind: Drehversatz 0/5/10/15°, Schräglage 5–10°, aus 5–10 cm fallen lassen, je 20× | Lädt jedes Mal ohne Nachhelfen, sitzt ohne Wackeln (< 1 mm), Pins im Arbeitsbereich | M2, M3, M5, M16 |
| T5 | Abheben: senkrecht und schräg mit Federwaage. Seitenstoß gegen die Box | Klemmkraft < 0,5 × Sockelgewicht. Sockel kippt nicht und rutscht < 1 cm | M11, M19 |
| T6 | Kurzschluss: Sockel ohne Box mit Münze, Löffel, Alufolie (0 V an den Pins). Dann beide Reeds mit Magneten schließen und Widerstände 0,2 / 0,5 / 1 / 2 / 3 Ω über Mitte und Ring, je 5 min, den heißesten Wert 1 h | Ohne Magnete 0 V. Mit Magneten: Pin-Halter, Platine und Last < 60 °C, eFuse begrenzt oder schaltet ab, nach Abheben der Magnete wieder normal | E1, E2, E3, E17 / 3.5.4, 8.3.4 |
| T7 | Box am USB-C: Spannung an der Scheibe mit 1 kΩ Last, bei 5,25 V am USB-C. Münze und Büroklammer in die Tasche | < 0,1 V, nichts passiert | E11, M7 / 8.4.5 |
| T8 | USB-C und Sockel gleichzeitig: Strom aus beiden Quellen messen, eine Quelle unter Last abziehen | Keine Rückspeisung, kein Neustart der Box | E11, E16 / 8.4.5 |
| T9 | Wärme: Laden leer → voll, geschlossener Sockel, Messung an eFuse, Mittel-Pins, Pin-Halter, Buchse, bis die Temperatur steht (≥ 3 h) | alles < 50 °C | E15 |
| T10 | Schmutz und Flüssigkeit: Krümel und Sand auf dem Zapfen. 20 ml Wasser, Apfelsaft und Salzwasser in die Mulde und einen Tropfen in die Tasche, dann andocken. Box 10× auf Teppich stellen, dann andocken | Lädt oder lässt sich mit einem Wisch reinigen. Kein Wasser im Elektronikfach. Nach 24 h kein Korrosionsbild | M9, E10, M21 / 8.3.2 |
| T11 | Zyklen: 500× andocken, auch schräg. Kontaktwiderstand am Anfang und Ende | Anstieg < 50 %, Gold nicht durchgerieben | M8 |
| T12 | Spitzen: Spannung am eFuse-Eingang und am PiSugar beim Andocken und Abheben unter Last (Oszilloskop oder Messgerät mit Spitzenwert) | keine Spitze > 6 V, kein Abbruch | E6, M20 |
| T13 | Kleinteile und Sturz: Box aus 1 m auf Fliese (PSP 4.3.2), dann Magnetabdeckung prüfen. Zug an Kontaktscheibe von außen (≥ 50 N) und an den Füßen | nichts lose, nichts zugänglich | M14, M15 / 4.7.1 |
| T14 | Untergrund: Sockel auf 5° Schräge, auf Kissen, auf Bettdecke | lädt, Box rutscht nicht heraus | M10 |

---

## 7. Stückliste

### 7.1 Beide Sockel zusammen (R)

| Teil | Stk | ca. € |
|---|---|---|
| Netzteil Raspberry Pi 15 W USB-C (5,1 V/3 A, Kabel fest) | 2 | 20 |
| Sockel-Platine, bestückt (eFuse, USB-C, TVS, C, R), Mindestmenge 5, mit Versand | 5 | 40 |
| Pogo-Pins (6 je Sockel, Typ vom Platinen-Agent) | 12 | 12 |
| Reed-Kontakt, gekapselt, Schließer | 4 | 12 |
| Stahlscheiben als Gewicht (je ~350 g) | — | 4 |
| Silikondichtung, Epoxy, Schrauben, Litze | — | 8 |
| PETG und TPU (Druck) | — | 8 |
| **Summe Sockel** | | **~104** |

### 7.2 Beide Boxen zusammen (R)

| Teil | Stk | ca. € |
|---|---|---|
| Kontaktscheibe, Leiterplatte Hartgold, Mindestmenge 5, mit Versand | 5 | 30 |
| Neodym-Magnete 8×3 mm (schon in Stückliste 1.1) | 8 | — |
| entfällt: Pogo-Pins in der Box (Stückliste 1.1) | — | −10 |
| **Summe Boxen** | | **~20** |

**Gesamt Ladesockel (Kontakte): ~125 €**. Im Plan stehen 30 €
(„Dual-Ladestation“ 22 € + „Load-Switch + Reed“ 8 €). **Mehrkosten ~95 €.**

### 7.3 Abweichungen vom Plan (nach Annahme in `docs/plan/` nachtragen)

| Stelle im Plan | Bisher | Neu |
|---|---|---|
| Stückliste 1.1 „Pogo-Pins 2-polig“ (5 €) | Pins in der Box | Kontaktscheibe Hartgold in der Box |
| Stückliste 1.2 „Dual-Ladestation“, „Load-Switch + Reed“ (30 €) | ein Dock | zwei Sockel mit Platine, ~125 € gesamt |
| Punkt 11 | ein Reed, Zentriermagnet | zwei Reeds in Reihe, Magnete nur für die Reeds (in 3.16 vermerkt) |
| PSP 3.5.2 | Load-Switch mit Reed | eFuse-Platine mit zwei Reeds |
| PSP 3.5 (neu) | — | 3.5.5 Sockel-Platine entwerfen und bestellen (Agent) |
| PSP 3.1 (neu) | — | Ladestrom-Messung M1–M3 |
| PSP 4.4 | Dual-Ladestation | Ladesockel 2× (in 3.16 vermerkt) |
| PSP 9.4 | — | Auto-Power-On nach Akkutausch prüfen |

---

## 8. Offen bis zur Bestellung

1. Quelle zum Weckverhalten des PiSugar (5.5).
2. Ladestrom des PiSugar (T2) → endgültige Stromgrenze.
3. Reed-Typ nach T1 (Muster mit zwei, drei Typen).
4. Pogo-Pin-Typ und eFuse-Typ: Der Platinen-Agent wählt sie und belegt sie
   aus Datenblättern.
5. Box-Maße nachmessen, dann Mulde und Zapfen festlegen.
6. Farbe des Sockels.

---

## 9. Vergleich mit induktivem Laden (Qi)

Grundlage: `research_qi.md`. Bei Qi stünde ein fertiges Qi-Ladepad in einer
gedruckten Mulde. Im Box-Boden säße ein Qi-Empfänger mit 5 V/1 A, der an
Eingang A des #5398 hängt.

| | **Kontakte (dieses Design)** | **Qi** |
|---|---|---|
| Offene Kontakte | ja, abgesichert durch 2 Reeds und eFuse | keine |
| Münze, Löffel, Fremdmagnet | gelöst durch eigene Platine | Fremdmetall-Erkennung im Pad (Norm), in der Praxis nicht belegt |
| Jede Drehlage, blind | Mulde, Kegel, Toleranzrechnung | von selbst. Mulde zentriert auf wenige mm, kein Zapfen |
| Magnete in der Box | 4 | keine |
| Eigene Platine | ja, mit Entwurf, Bestellung und 2–3 Wochen Wartezeit | nein |
| Ladestrom | bis ~2,7 A, so schnell wie USB-C | ~1 A, über Nacht voll; läuft die Box, lädt sie wenig |
| Wärme | an Pins und eFuse im Sockel | im Box-Boden, nah am Akku, Ferritplatte nötig |
| Hauptrisiko | Aufwand und Toleranzen | „Pumpen“: Empfänger und PiSugar-Ladechip kommen nicht miteinander aus |
| Flüssigkeit, Verschleiß | Ablauf, Dichtung, Hartgold, Zyklentest | kein Thema |
| Tests | 14 | ~5 (Pumpen, Wärme, Fremdmetall, Versatz, Wecken) |
| Kosten beide Boxen (R) | **~125 €** | **~40–60 €** |
| Bis zur ersten Ladung | Platinenentwurf, Bestellung, Druck | Pad und Empfänger kaufen, Billigtest |

**Empfehlung der Projektleitung:** zuerst den Qi-Billigtest machen
(`research_qi.md`, ~1 h, ~15 €). Besteht er, ist Qi in Kosten, Aufwand und
Kindersicherheit klar vorn. Fällt er durch, gilt dieses Design.
