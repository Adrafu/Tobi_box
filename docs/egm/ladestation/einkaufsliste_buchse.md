# Einkaufsliste: USB-C-Buchse für den Mustertest

Stand: 10.11.2026. Nur Recherche, nichts bestellt.

**Ziel:** 2–3 billige USB-C-Buchsen-Kandidaten, die Tobias kauft, misst und danach entscheidet.

**Anforderungen (aus der Aufgabe):**
- Platine höchstens ca. 11 mm breit (Einbau in 11 × 5 mm innen, Zapfen außen 13 × 7 mm)
- 5 V, bis 3 A, nur Strom
- Pflicht: 5,1 kΩ an CC1 und CC2 gegen GND (bestückt oder mit Lötpads)
- Lieferung nach Österreich

**Kennzeichnung:** „Seite" = steht auf der Produktseite. „Schätzung" = nicht verifiziert, bitte messen oder nachfragen.

## Kandidaten-Tabelle

| Kandidat | Link | Maße | CC-Widerstand | Befestigung | Preis | Händler | Lieferzeit |
|---|---|---|---|---|---|---|---|
| A: USB-C female 6-Pin Breakout 3A, Art. 41036209 | [electrokit.com](https://www.electrokit.com/en/breakout-board-usb-c-6-pins-3A) | Nicht angegeben (Zeichnung als PDF verlinkt). Seite: 2,54-mm-Raster. Schätzung: nicht gesichert | Seite: „3 A … as configured by the two 5.1 kΩ resistors", Bestückung nicht eindeutig genannt. Ist bestückt oder nur Pads: **unklar, messen** | Lötpins 2,54 mm, Befestigung unklar | 19 SEK inkl. 25 % MwSt. (Seite) | Electrokit (SE) | 1–3 Werktage (Seite). **Versand nach AT nicht bestätigt** |
| B: Null-C, USB-C female Breakout, 5 V / 1,5 A | [tindie.com](https://www.tindie.com/products/nullstalgia/mini-usb-c-5v-breakout-null-c) | ca. 13 × 12,8 × 4,3 mm (Seite, „may vary"). **Zu breit für 11 mm** | Seite: einzelne 5,1-kΩ-Widerstände nach GND an CC1 und CC2. Bestückung nicht genannt | Lötpads | ca. 4 USD für 1–2 Stück, Staffel bis 2,00 USD ab 15 Stück (Seite, Währung vermutlich USD) | Tindie, USA | **Ausverkauft** (seit 08.04.2026, Benachrichtigung möglich). Versand nach AT nicht angegeben |
| C: USB-C 6-Pin Female SMD-Buchse, „power DIY" | [scccltd.com](https://scccltd.com/products/6-pin-type-c-female-receptacle-smd-power-diy.oembed) | Nicht angegeben. Schätzung: Pins SMD, 4 Befestigungsbeine THT | Keine Widerstände auf der Buchse. Seite empfiehlt 5,1 kΩ von CC1 oder CC2 nach GND. **Müsste man selbst auf die Platine setzen** | Vier THT-Beine zum Einlöten | 10,0 HKD (Seite) | SCCC Ltd., Hongkong | Auf Lager (Seite). **Versand nach AT nicht angegeben** |

**Ausgeschlossen (zu groß oder nicht passend):**
- Zaitronics „USB-C Breakout Board 6 Pin" (zaitronics.com.au): 20,4 × 14,2 × 5 mm, beide 5,1-kΩ-Widerstände bestückt, aber zu groß. Außerdem derzeit „Unavailable", Lieferung aus Australien.
- Botland, Adafruit 5978 (botland.de): 24,1 × 14,3 mm, nur ein 5,1-kΩ-Widerstand (CC1), Lagerstatus auf der Seite widersprüchlich. Zu groß.
- SparkFun USB-C Breakout BOB-23055 (Berrybase, 5,50 €): Maße und Widerstände nicht geprüft. Pinleiste 0,1 Zoll. Nicht als Kandidat aufgenommen, weil die Größe fehlt.

**Wichtiger Befund:** In den Recherche-Treffern gibt es **keine bestätigte Platine mit 5,1 kΩ an CC1 und CC2, die höchstens 11 mm breit ist**. Die gefundenen Breakouts sind 13 bis 24 mm groß. Die Kandidaten A und C sind die einzigen, die als Ausgangspunkt für einen Test mit kleinem Platinenlayout taugen. Wenn die Maße nicht passen, braucht es eine eigene kleine Platine mit der Buchse und zwei 0805-Widerständen 5,1 kΩ.

**Hinweis zu Anforderungen:** Ein USB-C-Buchsen-Produkt mit „2 Pin" und 5,1 kΩ wurde nicht gefunden. An CC liegt ein Signalpin, und ein 2-Draht-Anschluss mit nur VBUS und GND liefert ohne CC-Widerstand keine Spannung. Der Kandidat „USB-C 2-pin with resistor" aus der Aufgabe ist deshalb nicht in die Liste aufgenommen. Die Panel-Mount-Wasserdicht-Buchsen mit Mutter (4 Drähte) lieferten keine verifizierte Angabe zu Drahtzahl und Gewinde. Diese Variante ist nicht bestätigt.

## Empfehlung

1. **Electrokit Art. 41036209**, 3 Stück (19 SEK je Stück). Zuerst Lieferung nach Österreich bei Electrokit prüfen, dann Maße mit der Schieblehre messen. Das ist der einzige Treffer, der bestückte 5,1-kΩ-Widerstände nennt.
2. **SCCC 6-Pin SMD-Buchse**, 3 Stück (10 HKD je Stück, grob ca. 1 € (Umrechnung geschätzt)). Dazu **10 Stück 5,1-kΩ-Widerstände in 0805** (Eckstein oder Reichelt, Preis nicht geprüft). Die Widerstände nach dem Muster an CC1 und CC2 löten. Versand nach AT prüfen.
3. **Reserve:** Null-C (Tindie), nur wenn es wieder verfügbar ist und die 13 mm Breite zum Messen passt. Sonst weglassen.

Bestellmenge: je 3–5 Stück. Die Preise sind so klein, dass ein Rest kein Problem ist.

## Messanleitung

1. **Körpermaße:** Breite, Tiefe und Länge jedes Kandidaten mit der Schieblehre messen. Bei Kandidat C auch die Höhe und den Abstand der Befestigungsbeine notieren.
2. **CC-Widerstand:** Buchse vom Netz trennen. Multimeter auf Widerstand. Zwischen CC1 und GND messen, dann zwischen CC2 und GND. Soll: 5,1 kΩ (±5 %, also etwa 4,85 bis 5,36 kΩ). Bei Kandidat C den Widerstand selbst aufgelötet messen.
3. **5-V-Test:** Mit einem USB-C-Netzteil, das PD-Ausgang und 5 V / 3 A hat, eine USB-C-Leitung an die Buchse stecken. Ohne Last messen: VBUS gegen GND, Soll ca. 5,0 V. Mit einer Last von ca. 1 A (z. B. ein Widerstand oder ein USB-Verbraucher) nochmal messen. Spannung soll nicht unter etwa 4,8 V fallen.
4. **Ergebnisse notieren** (Breite, Tiefe, Länge, Widerstand CC1 und CC2, Spannung bei Last).

**Parameter für das Druckmuster:** Die Werte gehören in `hardware/ladesockel/druckmuster_fuehrung.scad` in die Parameter `buchse_b` (Breite), `buchse_t` (Tiefe) und `buchse_l` (Länge). Die Zuordnung bitte gegen die Kommentare in der Datei prüfen, bevor die Werte eingetragen werden. Diese Datei wurde für diese Recherche nicht geändert.

## Quellen

- [Electrokit, Art. 41036209](https://www.electrokit.com/en/breakout-board-usb-c-6-pins-3A)
- [Tindie, Null-C](https://www.tindie.com/products/nullstalgia/mini-usb-c-5v-breakout-null-c)
- [SCCC Ltd., 6-Pin Type-C SMD](https://scccltd.com/products/6-pin-type-c-female-receptacle-smd-power-diy.oembed)
- [Zaitronics, USB-C Breakout 6 Pin](https://zaitronics.com.au/products/usb-c-breakout-board-6-pin)
- [Botland, Adafruit 5978](https://botland.de/kontaktplattenzubehor/25268-usb-typ-c-steckmodul-stecker-fur-kontaktplatine-adafruit-5978-5904422386405.html)
- [Berrybase.at, SparkFun USB-C Breakout](https://www.berrybase.at/en/sparkfun-usb-c-breakout) (Suchtreffer, nicht geöffnet)
