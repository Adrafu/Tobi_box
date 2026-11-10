# Design: Ladesockel Tobi Box (USB-C-Stecker im Sockel)

* **Autor:** Tobias (Projektleitung: Claude als „Elefant“)
* **Datum:** 2026-11-10
* **Stand:** **Rev. 4**, nach Review der Rev. 3 und den Entscheidungen R7–R9
  in `resolve.md`
* **Grundlage:** `concepts_brief.md`, `resolve.md`, `review_rev3.md`,
  `research_qi.md`, `docs/plan/stueckliste-und-psp.md` (Rev. 3.16),
  `docs/designs/box-software.md`
* **Frühere Stände:** Rev. 1 bis Rev. 3 im Git-Verlauf dieser Datei

Werte mit **(R)** sind Richtwerte, ein Druckmuster und das CAD klären sie.

---

## 1. Idee in einem Satz

Der Sockel ist eine Mulde, in deren Mitte ein USB-C-Stecker nach oben steht,
wie bei einem Handy-Dock. Die Box hat unten eine USB-C-Buchse und wird darauf
gesteckt.

**Warum (Review G1):** Bei offenen Kontakten kann Metall zwischen Box und Sockel
Plus und Masse überbrücken, und keine elektrische Erkennung bemerkt das, weil
die Box ja aufsitzt. Beim USB-C-Stecker liegen die Kontakte im Inneren des
Steckers. Münze, Löffel und Klammer erreichen sie nicht. Das ist dasselbe
Schutzprinzip wie bei jedem USB-C-Kabel, das auf dem Boden liegt.

## 2. Was gegenüber Rev. 3 wegfällt

| Rev. 3 | Rev. 4 |
|---|---|
| Magnet-Pogo-Stecker, offene Pins | USB-C-Stecker, Kontakte geschützt im Stecker |
| 2 Reeds, Pololu #2810, PTC, TVS, RC-Glied, Lochraster | **keine Elektronik im Sockel** |
| 2 Magnete in der Box | **keine Magnete** für den Sockel (Punkt 13 entschärft) |
| Restrisiko Metall auf den Pins | entfällt |
| neues Risiko | **Stecker oder Buchse brechen, wenn ein Kind die Box seitlich hebelt** (Abschnitt 5) |

---

## 3. Anforderungen

| # | Anforderung | Herkunft |
|---|---|---|
| A1 | Box lädt in zwei Lagen (0° und 180°, USB-C ist drehbar). In 90° und 270° setzt sie nicht auf dem Stecker auf. | R9 |
| A2 | Die Mulde führt die Box so genau, dass der Stecker ohne Zielen in die Buchse findet. | D1 |
| A3 | Kind hebt die Box einhändig ab, der Sockel bleibt stehen, obwohl der Stecker hält. | D1 |
| A4 | Seitliches Hebeln an der aufgesteckten Box bricht weder Buchse noch Stecker. Wenn doch, bricht das billige, tauschbare Teil im Sockel, nie die Buchse in der Box. | R9, neu |
| A5 | Beim USB-C-Laden unterwegs liegt an der Boden-Buchse keine Spannung (#5398 bleibt). | Punkt 7 |
| A6 | Kein Metallteil kann Plus und Masse überbrücken. | G1 |
| A7 | **Andocken weckt die Box kurz**: Ton und LED-Ring zeigen einige Sekunden Laden und Ladestand. | R8 |
| A8 | Ladestrom am Sockel wie am USB-C-Kabel. | E7 |
| A9 | Keine Kleinteile, die ein Kind herauslösen kann. | Punkte 14–15 |
| A10 | Flüssigkeit in der Mulde läuft ab und erreicht den Stecker nicht. | M9 |
| A11 | Keine Anzeige am Sockel. | D6 |

---

## 4. Aufbau

```
 Steckdose          Sockel                                   Box
 ─────────          ───────────────────────────              ───────────────────────────────
 Netzteil 5,1 V/3 A ─ festes Kabel ─► USB-C-Stecker ═══════► USB-C-Buchse unten ─► #5398 A ─┐
 (Raspberry Pi 15 W)  durch den Sockel   (schwimmend          (5,1 kΩ an CC)                  ├─► PiSugar
                                          gelagert)           USB-C seitlich ─────► #5398 B ─┘
```

### 4.1 Sockel

- **Kein eigener Elektronik-Teil.** Das fest angeschlossene Kabel des
  Netzteils (Raspberry Pi 15 W, R3) läuft hinten in den Sockel. Sein Stecker
  steht in der Mitte der Mulde nach oben.
- **Schwimmende Lagerung:** Der Stecker sitzt in einem TPU-Halter, der ±1 mm
  seitlich und einige Grad Kippen erlaubt (R). Kleine Ungenauigkeiten nimmt
  der Halter auf, nicht der Stecker.
- **Sollbruchstelle im Sockel:** Bricht etwas, dann der Stecker oder der
  TPU-Halter. Tausch = neues Netzteil (~10 €) oder neuer Halter, ohne die Box
  zu öffnen.
- **Kabelführung:** Das Kabel ist im Sockel mit Zugentlastung geklemmt. Zug am
  Kabel geht nie auf den Stecker.

### 4.2 Box

- **USB-C-Buchse unten**, auf einem kleinen Sink-Breakout mit 5,1 kΩ an CC1
  und CC2. Das Breakout ist mit dem Box-Boden verschraubt und umgossen, die
  Buchse von einer Wand im Boden umfasst. Die Buchse muss stärker sein als der
  Stecker im Sockel (A4).
- Buchse → #5398 Eingang A. Die seitliche USB-C-Buchse für unterwegs → Eingang
  B. Unverändert gegenüber dem Plan, nur der Eingang A kommt jetzt von einer
  Buchse statt von Pogo-Pins.
- Zuleitung ≥ 3 cm von der NFC-Antenne (Punkt 10).
- **Keine Magnete** für den Sockel.

### 4.3 Wecken und Rückmeldung (R8)

- Am PiSugar wird „Einschalten bei Strom am Eingang“ aktiviert.
- Nach dem Start am Lader: Ton (nachts nicht, Leise-Zeiten), LED-Ring zeigt
  einige Sekunden Laden und Ladestand, Sync prüfen, ohne Wiedergabe zügig
  wieder herunterfahren.
- Rückmeldung nach ~20–30 s (Startzeit des Pi 3A+, am Muster messen).
- Läuft die Box schon beim Andocken, kommt die Rückmeldung sofort.
- Das ist Arbeit für das Box-Software-Design (eigenes Thema). Die Verträge
  bleiben unverändert, bis Tobias dort entscheidet.

---

## 5. Mechanik: Führung und Hebelschutz

Hier liegt das Risiko dieser Variante. Ein USB-C-Stecker verträgt kaum
seitliche Kraft. Kleinkinder setzen schräg auf und ziehen schief ab.

### 5.1 Drei Stufen Führung

```
Schnitt (seitlich, nicht maßstäblich)

  ╲                                                   ╱   ← 1. Mulde, 60°, 2 mm Spiel
   ╲    Box                                           ╱
    ╲   ┌──────┐      ┌──Buchse──┐      ┌──────┐    ╱
     ╲  │ Nut  │      │  Tasche  │      │ Nut  │   ╱
      ╲_│Rippe │______│ ▲Stecker │______│Rippe │__╱     ← 2. Rippen + Nuten (nur 0°/180°)
        └──────┘      └─Kragen───┘      └──────┘          3. konischer Kragen + Tasche
   │ Kabel mit Zugentlastung, Gewicht im Boden             │
   └──────────────────────────────────────────────────────┘
```

1. **Mulde (grob):** 124 × 124 mm, Wände 60°, ±2 mm Spiel, wie Rev. 3.
2. **Rippen und Nuten (Lage):** Zwei Rippen vorne und hinten auf dem
   Mulden-Boden, parallel zur langen Seite des Steckers. In der Box liegen
   passende Nuten mit Fase.
   - Bei 0° und 180° sinkt die Box ab. Das ist symmetrisch, und USB-C ist
     drehbar.
   - Bei 90° und 270° liegt die Box auf den Rippen auf. Die Rippen sind
     **höher als die Steckerspitze**, die Box berührt den Stecker nicht.
3. **Kragen und Tasche (fein):** Der Stecker steht in einem konischen,
   rechteckigen Kragen. Die Box hat um die Buchse eine passende konische
   Tasche. Der Kragen fängt ±3 mm und führt auf ±0,3 mm, **bevor** der
   Stecker die Buchse berührt (R).

### 5.2 Hebelschutz

- **Tiefe Führung:** Rippen und Kragen greifen schon 5–8 mm vor dem Stecken.
  Wird die steckende Box seitlich gedrückt, stützen Kragen und Rippen die
  Kraft ab, nicht der Stecker (R).
- **Schwimmender Halter:** Er gibt bei Überlast nach, statt dass der Stecker
  bricht.
- **Steckkraft:** Ein USB-C-Stecker hält mit etwa 8–20 N (Richtwert der Norm,
  am Muster messen). Das Gewicht der Box reicht zum Stecken. Beim Abheben muss
  das Kind diese Kraft überwinden. **Der Sockel muss deshalb deutlich schwerer
  sein** (Gewicht ≥ 1 kg im Boden, R) oder rutschfest stehen. Sonst hebt er
  mit ab (A3).

### 5.3 Flüssigkeit

Der Kragen steht erhöht. Der Mulden-Boden fällt zur Rinne mit Ablauf hin ab.
Im Stecker kann sich trotzdem Feuchtigkeit sammeln. Das ist dasselbe wie bei
jedem USB-C-Kabel. T7 prüft es.

---

## 6. Tests (Tobias, R4)

| # | Test | Bestanden, wenn |
|---|---|---|
| T1 | Druckmuster der Führung ohne Elektronik: Box 50× aufsetzen, auch schräg, verdreht, mit Versatz, aus 5–10 cm | Bei 0°/180° steckt sie jedes Mal, ohne Kraft. Bei 90°/270° liegt sie auf den Rippen, der Stecker bleibt frei |
| T2 | Hebeltest: steckende Box seitlich mit 20, 40, 60 N kippen (Federwaage), in alle Richtungen | nichts bricht, Stecker sitzt danach normal |
| T3 | Abheben einhändig, senkrecht und schräg, Abzugskraft messen | Sockel hebt sich nicht, Kraft < 20 N (R) |
| T4 | Ladestrom Sockel gegen Kabel an der Seitenbuchse | gleich (±10 %) |
| T5 | Wecken (R8): Andocken bei Box aus, bei laufender Box, bei leerem Akku; Leise-Zeit | Ton/Ring wie in 4.3, nachts kein Ton |
| T6 | Münze, Löffel, Klammer, Alufolie in Mulde und auf den Stecker, dann Box aufsetzen | nichts wird warm, Box steckt nicht oder lädt normal |
| T7 | Wasser, Saft in die Mulde, Krümel auf den Kragen | läuft ab, Stecker trocknet, kein Fehler. Kragen mit einem Wisch sauber |
| T8 | USB-C seitlich und Sockel gleichzeitig, eine Quelle abziehen | kein Neustart, keine Rückspeisung |
| T9 | Zyklen: 500× stecken (USB-C ist für ≥ 10.000 ausgelegt) | Steckkraft und Kontakt unverändert |
| T10 | Sturz der Box aus 1 m (PSP 4.3.2), danach Boden-Buchse prüfen | Buchse fest, kein Teil lose |

---

## 7. Stückliste (beide Sockel und Boxen, R)

| Teil | Stk | ca. € |
|---|---|---|
| Netzteil Raspberry Pi 15 W USB-C, festes Kabel (eines Ersatz bei Bruch) | 2 (+1) | 20 (+10) |
| USB-C-Sink-Breakout mit 5,1 kΩ für die Boden-Buchse | 2 | 6 |
| Gewicht im Sockel (Stahl, ≥ 1 kg je Sockel) | — | 6 |
| TPU-Halter, Füße, Druck PETG/TPU | — | 8 |
| Schrauben, Epoxy, Litze | — | 5 |
| entfällt: Pogo-Pins in der Box (Stückliste 1.1) | — | −10 |
| entfällt: Neodym-Magnete für die Zentrierung (Stückliste 1.1, 2× 4 Stk) | — | −8 |
| **Summe** | | **~27 (mit Ersatz-Netzteil ~37)** |

Im Plan stehen 30 € (Stückliste 1.2). **Die Rev. 4 bleibt im Budget.**

### 7.1 Abweichungen vom Plan (nach Annahme in `docs/plan/` nachtragen)

| Stelle | Neu |
|---|---|
| Punkt 11 (Reed) | entfällt, kein Reed |
| Abschnitt 1.4 „Load-Switch im Dock, Ideal-Diode in der Box“ | Load-Switch entfällt, Ideal-Diode bleibt |
| Punkt 13 / PSP 4.7.1 | keine Magnete für den Sockel |
| Stückliste 1.1 „Pogo-Pins“, „Neodym-Magnete“ | Boden-USB-C-Buchse, keine Magnete |
| Stückliste 1.2 | zwei Sockel nach Rev. 4 |
| PSP 3.5.1–3.5.4 | Verpolschutz durch USB-C; kein Load-Switch; Kontakte im Stecker; Münztest bleibt (T6) |
| PSP 3.5 neu | Druckmuster der Führung (T1), Hebeltest (T2) |
| Punkt 3, PSP 5.6.5, 8.2.4 | Andocken weckt kurz (R8, schon in 3.16 vermerkt) |

---

## 8. Offen

1. Druckmuster der Führung (T1, T2) vor allem anderen: Es entscheidet, ob B
   kindertauglich ist. Fällt T2 durch, ist der Rückfall „versenkte
   Federkontakte“ (Variante A aus dem Resolve).
2. Maße von Kragen, Tasche, Rippen und Nuten erst nach CAD der Box.
3. PiSugar-Einstellung „Einschalten bei Strom am Eingang“ am Muster
   bestätigen.
4. Box-Software für R8: Ablauf nach Start am Lader, Leise-Zeiten, Abschalten.
