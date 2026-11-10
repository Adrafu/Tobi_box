# Druckmuster Ladesockel, Variante 4a „hoher Kragen“

Zweck: Führung, Stecken und Abheben mit einem echten USB-C-Kabel testen, **bevor** die
Box konstruiert ist. Keine Elektronik außer dem Breakout als Passprobe.

Datei: `druckmuster_fuehrung.scad` (OpenSCAD). Alle Maße stehen als Parameter oben in der
Datei. Auswahl mit
`teil = "sockel" | "boxboden" | "halter" | "kragenprobe" | "alle"`.
Zum Ansehen gibt es zusätzlich `"baugruppe0"` und `"baugruppe90"` (Schnitt in y = 0,
Sockel und Boxboden in Endlage, Stecker und Halter eingesetzt; `baugruppe90` zeigt die Box
so gekippt, wie sie bei 90° wirklich liegt). `"kippcheck"` ist ein Prüfteil: Schnittmenge aus
Sockel und gekippter Box, muss leer sein (STL ohne Dreiecke).
STL erzeugen: `openscad -D 'teil="sockel"' -o sockel.stl druckmuster_fuehrung.scad`.
STL gehören nicht ins Repo.

## Änderungen vom 10.11. (Entscheidungen Tobias)

- **Zapfen 13 × 7** (vorher 11 × 6), damit gängige kleine USB-C-Buchsen und Platinen
  hineinpassen. Schacht im Kragen 14 × 8, Feinführung bleibt ±0,5.
- **Kragen und Tasche wachsen mit:** Kragen unten 38 × 20, oben 32 × 14 (Höhe weiter 14),
  Tasche mit `spiel` unten 39 × 21, oben 33 × 15.
- **Buchseneinsatz** ist ein austauschbares Modul (`buchseneinsatz()`) mit den Parametern
  `buchse_b`, `buchse_t`, `buchse_l`. Befestigung mit `buchse_befest = "kleben"` oder
  `"schrauben"` (2 × M2, Bohrung 1,7 quer durch die Zapfenwand). Das Breakout im Taschendach
  entfällt. **Erst die gekaufte Buchse messen, dann die Parameter setzen** (siehe unten).
- **Litzenführung** Ø 4 (`litze_d`) vom Buchsenraum senkrecht durchs Taschendach ins
  Box-Innere. Das Taschendach ist jetzt `dach_h` = 4 dick (vorher eine 27 mm hohe Stütze).
- **Kabelrinne nach hinten (+y)**, nicht mehr in x. Der Schalter `rinne_achse` ist weg.
- **Bei 90° und 270° kippelt die Box, das ist gewollt:** Die Rinne frisst die eine
  Kragen-Auflage, die Box liegt nur auf der anderen und kippt zur Rinnenseite, bis die
  Bodenkante den Mulden-Boden berührt. So merkt man, dass sie falsch steht. Der Zapfen
  bleibt dabei weit genug über der Steckerspitze (Rechnung unten).
- **Rinne 18 statt 14 breit** (nicht angeordnet, aus der Rechnung): Bei 14 liegt die
  Rinnenkante an der schrägen Kragenwand an und stützt die Box zusätzlich, dann kippelt sie
  nicht mehr wie gerechnet. Die Rinne muss breiter sein als der Kragen an der Stelle, an der
  er eintaucht (assert „Rinne zu schmal fuer den Kragen“).
- **Asserts:** Der Auflage-Assert ist ersetzt durch (a) Rinne kreuzt bei 0°/180° keine
  Führungsfläche und (b) Zapfen ≥ 3 mm über der Steckerspitze bei maximaler Kippung.
  Neues Prüfteil `kippcheck`, TPU-Ecken sind in den Ansichten sichtbar.

## Was sich gegenüber der Rippen-Version ändert

- **Weg:** Rippen im Sockel, Nuten im Boxboden und alle Asserts dazu.
- **Neu: Kragen** im Sockel, fest mit der Mulde gedruckt, rechteckig und konisch,
  länglich (lange Seite in x): unten 38 × 20, oben 32 × 14, 14 hoch. Oben ein Schacht
  14 × 8, in dem der Stecker steht.
- **Stecker:** Die Metallspitze liegt 2 mm unter der Kragenoberkante (Höhe 12). Der
  TPU-Halter erlaubt ±0,5 mm seitlich. Der Flansch liegt auf einer **festen Schulter**
  im Sockel: Die Steckkraft (bis 20 N) drückt nicht in den TPU. Der Kragen schwimmt nicht.
- **Tasche im Boxboden:** konisch, passend zum Kragen mit `spiel` = 0,5 je Seite:
  Öffnung 39 × 21, oben 33 × 15, 14 tief. Kein zusätzlicher Einlauf an der Öffnung, der
  würde bei 90° die Auflage auffressen.
- **Buchsen-Zapfen** (13 × 7) hängt vom Taschendach nach unten. Die Buchsen-Öffnung liegt
  5,5 mm über der Boxbodenfläche, der Zapfen ragt nicht über die Bodenfläche hinaus. Er
  taucht in den Schacht ein (Feinführung ±0,5).
- **Lage bei 90° und 270°:** Die Tasche passt nicht über den Kragen. Die Box liegt mit dem
  Tasche-Rand auf der Kragen-Oberkante (Auflage 5,5 mm breit, 14 mm über der Normallage), die
  zweite Auflage fehlt wegen der Rinne: Die Box kippelt (siehe Änderungen).
- **Kabelrinne für unterwegs:** 18 breit, 8 tief, von der Tasche (ab y = 4) bis zur
  Rückkante, nach hinten (+y).
- **Gewichtsraum** für ca. 1 kg Stahl (Parameter `gewicht_soll`), dafür ist das Unterteil
  höher (`unterteil_h` = 22).
- **Option `befestigung = true`:** zwei Schraubenlöcher mit Senkung hinten im Muldenboden.
- **Neues Teil `kragenprobe`:** Kragen mit Halter-Aufnahme plus Gegenstück mit Tasche und
  Zapfen. 0° und 90° lassen sich in einer Stunde ausprobieren.

## Druckreihenfolge

1. **`kragenprobe`** (PETG, ca. 2,5 h). Zusammenstecken in 0° und 90°, Spiel prüfen.
   Die Probe hat keine Rinne: Das Kippeln bei 90° ist nur am fertigen Boxboden zu spüren.
2. **`halter`** (TPU 95A, ca. 40 min). Stecker einpressen, in die Kragenprobe setzen.
3. **Messschritt Abzugskraft** (siehe unten), erst danach entscheiden, ob der Sockel
   Befestigung braucht.
4. **`sockel`** (PETG, ca. 18 h, ca. 340 g ohne Stahl).
5. **`boxboden`** (PETG, ca. 4 bis 4,5 h, ca. 60 g, Stützen nur für den Zapfen).

| Teil | Material | Ausrichtung | Zeit (0,2 mm, 15 %) | Anmerkung |
|---|---|---|---|---|
| `kragenprobe` | PETG | flach; das Gegenstück ist schon gedreht (Zapfen oben) | ca. 2,5 h | zuerst drucken |
| `halter` | TPU 95A | Flansch unten | ca. 40 min | langsam (20 mm/s), Direct Drive |
| `sockel` | PETG | Boden unten, ohne Stützen | ca. 18 h | Pause für Stahl bei z = 17,8 |
| `boxboden` | PETG | Unterseite unten | ca. 4 bis 4,5 h | Stützen im Taschen-Mittelteil für den Zapfen, sonst keine |

Zeiten sind Schätzungen, aus dem Volumen hochgerechnet, Stand 10.11. gegenüber der Fassung
davor: Kragenprobe 34,9 cm³ statt 29,2 cm³ (2 h → ca. 2,5 h), Sockel 518,8 cm³ statt
517,3 cm³, Boxboden 73,8 cm³ statt 80,0 cm³.

- **Zapfen drucken:** Der Zapfen hängt in der Luft, solange der Boxboden mit der Unterseite
  nach unten liegt. Tree-Stützen nur im Bereich der Tasche zulassen. Wand um den
  Buchsenraum ist mit den Vorgabewerten ca. 1,85 mm (x) und 1,7 mm (y): vier Umfänge bei
  0,4 mm Düse. Die Litzenbohrung Ø 4 ist senkrecht, braucht keine Stützen.
- **Sockel-Gewicht:** zwei Hohlräume (je 50 × 100 × 16 mm). Druck bei z = 17,8 mm
  pausieren, Stahlscheiben einlegen (Stapel höchstens 15,6 mm), weiterdrucken. Die
  Rechnung im SCAD (Füllgrad 0,85) ergibt ca. 1040 g Platz, Soll 1000 g.
- **Kabel:** Stecker von oben durch den Kragen in die Halter-Aufnahme setzen, Kabel durch
  die Bohrung in den Kanal an der Unterseite führen (Klemmzone 0,5 mm schmaler als das
  Kabel), Kabelbinder durch die zwei Schlitze. Unterseite mit Filz oder Gummi abkleben.
  Die vier Ablaufbohrungen enden an der Unterseite, dafür Gummifüße setzen.
- **Halter:** Der Flansch (2,25 mm Überstand je Seite) muss zum Einsetzen leicht
  verformt werden. Geht das nicht, `flansch_ueber` verkleinern.
- **Boxboden:** Mit Gewicht auf ca. 0,8 kg beschweren. Die Ecken-Aussparungen
  (18 × 18 × 2 mm) nehmen TPU-Ecken auf. Ohne TPU-Ecken `ecke_unter = 0` setzen.

## Vorher messen (Messschieber)

Das Netzteil-Kabel (Raspberry Pi 15 W) ist festgelegt, der Stecker bestimmt den Halter.

| Parameter | Vorgabe | Was messen |
|---|---|---|
| `stecker_b` / `stecker_d` | 12,5 / 6,5 | Umspritzkörper, Breite und Dicke |
| `stecker_l` | 20 | Umspritzkörper, Länge bis zur Metallschale |
| `stecker_schale` | 6,7 | Metallschale, Länge. Muss ≥ Stecklänge 6,5 sein |
| `schale_b` / `schale_d` | 8,4 / 2,6 | Metallschale, Breite und Dicke (nur Ansicht) |
| `kabel_d` | 4,0 | Kabeldurchmesser |
| `buchse_b` / `buchse_t` / `buchse_l` | 9,0 / 3,3 / 7,4 (Richtwerte) | **gekaufte** Buchse samt Platine, siehe Messschritt Buchse |
| `winkel_b` / `winkel_h` / `winkel_l` | 12 / 6 / 20 | gewinkelter USB-C-Stecker: Breite, Höhe unter der Buchse, Länge |

## Messschritt: Buchse

Die Werte `buchse_*` sind Richtwerte für eine kleine USB-C-Buchse. **Erst die gekaufte
Buchse messen, dann die Parameter setzen**, dann erst `boxboden` und `kragenprobe` drucken:

1. Buchse mit allem, was in den Zapfen soll (Gehäuse, Lötfahnen, ggf. Platine), mit dem
   Messschieber messen: Breite `buchse_b` (lange Seite der Öffnung), Dicke `buchse_t`
   (kurze Seite der Öffnung), Länge `buchse_l` (Einbautiefe ab der Öffnung bis zum
   hintersten Teil).
2. Der Zapfen ist 13 × 7. Mit `buchse_spiel` = 0,15 je Seite bleibt bei 9,0 × 3,3 eine Wand
   von 1,85 mm (x) und 1,7 mm (y). Die Asserts verlangen mindestens `zapfen_wand_min` = 1,2.
   Passt die Buchse nicht, kleineres Modell kaufen oder `zapfen_*` und `schacht_*` anpassen
   (Feinführung ±0,5 beibehalten, Kragen und Tasche wachsen dann mit).
3. `buchse_l` muss mindestens die Stecklänge (6,5) haben und mit Decke unter das Taschendach
   passen (assert meldet es). Die Litzen gehen oben durch die Ø-4-Bohrung (`litze_d`).
4. Befestigung wählen: `buchse_befest = "kleben"` (Zweikomponenten-Kleber oder Sekundenkleber
   im Buchsenraum) oder `"schrauben"` (zwei Bohrungen Ø 1,7 für M2 quer durch die +y-Wand,
   bei x = ±`schr_dx`, Höhe `schr_z` über der Öffnung; nur sinnvoll, wenn die Buchse oder
   Platine Löcher dafür hat, sonst passen `schr_dx` und `schr_z`, oder kleben).

## Folgen von Messwerten

Ändert sich ein Maß, stimmen Steckerspitze, Halter-Schulter und Tasche nach. Die
`assert`-Zeilen melden, wenn die Rechnung nicht mehr aufgeht.

## Messschritt: Abzugskraft

Mit dem gedruckten Halter und der Kragenprobe, **bevor** der Sockel gedruckt wird:

1. Stecker in die Buchse stecken (Breakout im Gegenstück), Gegenstück senkrecht nach oben
   abziehen. Federwaage am Gegenstück, Wert ablesen (mehrmals, Mittel).
2. Liegt die Abzugskraft unter ca. 8 N, hebt der Sockel (1 kg, ca. 10 N) nicht mit ab.
   Nichts weiter nötig.
3. Liegt sie **über ca. 8 N**, den Sockel am Möbel befestigen: Klebepads (3M Dual Lock)
   unter dem Sockel, oder `befestigung = true` setzen und mit zwei Schrauben festschrauben
   (Löcher hinten im Muldenboden bei x = ±32, y = +56, Senkung unter der Box).
4. Zusätzlich Ziel für einhändiges Abheben der Box: < 20 N.

## Testen

1. **Kragenprobe** zusammenstecken: Kragen in Tasche, Halter in den Kragen, Zapfen im
   Schacht. Soll leicht gehen. Sonst `spiel` anpassen (je Seite, Vorgabe 0,5).
2. **Führung:** Box 50 × aufsetzen, schräg, verdreht, mit Versatz. 0° und 180° müssen
   voll stecken. 90° und 270°: Box kippelt (liegt nur auf einer Auflage und einer Bodenkante),
   die Spitze bleibt frei. Das ist gewollt.
3. **Hebeln:** Federwaage seitlich oben an der Box, 20, 40, 60 N. Stecker, Halter und
   Schulter prüfen.
4. **Unterwegs:** gewinkelten USB-C-Stecker in die Buchse stecken, Kabel durch die
   Kabelrinne führen, Box auf den Tisch stellen. Federwaage 20 N am Kabel.

## Rechenergebnisse (Asserts halten, OpenSCAD 2021.01)

| Größe | Soll | Ergebnis |
|---|---|---|
| (a) Rinne beginnt hinter Zapfen/Schacht (y) | ≥ 4,0 | 4,0 |
| (a) Rest der Tasche-Hinterwand neben der Rinne, je Seite | ≥ 6 | 8,8 oben an der Rinne, 9,5 an der Bodenfläche |
| (a) Durchgehendes Wandband über der Rinne | ≥ 4 | 6 (14 − 8) |
| (b) Kippwinkel bei 90°/270° | | 12,8° (Kante, Boden steigt nach hinten) |
| (b) Zapfen-Unterkante über Steckerspitze, maximal gekippt | ≥ 3 | 4,46 |
| Zapfen-Unterseite über Steckerspitze bei 90° flach | ≥ 5 | 7,5 |
| Kragen taucht in die Rinne (senkrecht zur Bodenfläche) | ≤ 8 − 1 | 5,9 |
| Rinne halbe Breite gegen Kragen auf dieser Höhe | ≥ 8,29 + 0,3 | 9 gegen 8,29 |
| Eingriff des Kragens, bevor die Spitze die Buchse berührt | ≥ 6 | 7,5 (14 − (12 − 5,5)) |
| Zapfen taucht bei Kontakt schon in den Schacht | ≥ 1 | 2 |
| Stecklänge 0°/180° | | 6,5 |
| Unterkante Winkelstecker unter der Bodenfläche | | −0,5, siehe unten |
| Gewichtsraum | ≥ 1000 g | ca. 1040 g |

**Kippen bei 90° (Rechnung im SCAD, `echo` gibt sie aus):** Drehpunkt ist der Tasche-Rand
(+x, 10,5 mm von der Mitte) auf der Kragen-Oberkante, 14 mm über z0. Von dort bis zur
Außenkante der Box sind 70,5 mm entlang der Bodenfläche. Der Mulden-Boden steigt nach hinten
mit 2°. Die gerade Boxkante berührt ihn zuerst bei y = 40 (dort beginnt der Freistich), das
gibt 12,8°. Die TPU-Ecke im Freistich würde erst bei 13,2° anliegen. Bei 12,8° liegt die
Zapfen-Unterkante (tiefste Kante, x = −3,5) 16,46 mm über z0, die Steckerspitze bei 12:
Rest-Abstand 4,46 mm, Vorgabe ≥ 3. Kragenhöhe und Steckerspitze mussten nicht geändert
werden. `kippcheck` bestätigt die Rechnung geometrisch: keine Überschneidung von Sockel und
gekippter Box.

## Was die Datei annimmt, und offene Punkte

- **Bezugsebene `z0`:** Alle Höhen der Aufgabe gelten ab der Boxbodenfläche in
  Normallage. Sie liegt `sitz_h` = 3 mm über dem Mulden-Boden in der Mitte, weil der
  Mulden-Boden 2° Gefälle hat (hinten 2,1 mm höher). Bei 0 mm würde die Box hinten
  aufsetzen. Der Kragen steht damit 17 mm über dem Mulden-Boden.
- **Kabelrinne nach hinten (y), Kippeln bei 90° gewollt:** Die Rinne frisst die zweite
  Kragen-Auflage, die Box liegt nur auf einer und kippt, bis die Bodenkante am Mulden-Boden
  anliegt. Rest-Abstand Zapfen zu Steckerspitze dabei 4,46 mm. Annahme der Rechnung:
  Die Box taucht frei in die Rinne ein, deshalb ist die Rinne 18 breit (assert).
  Ändert sich Rinne, Kragen, Mulde oder `ecke_unter`, rechnet das SCAD den Winkel neu.
- **Winkelstecker 0,5 mm unter der Bodenfläche:** Körper 6 hoch unter der Buchsen-Öffnung
  bei 5,5 ergibt −0,5. Der Assert prüft deshalb gegen die TPU-Ecken (`ecke_unter` = 2),
  auf denen die Box auf dem Tisch steht. Ohne TPU-Ecken schlägt er an.
- **Buchse:** `buchse_b/t/l` sind Richtwerte (8,94 × 3,26 × 7,35 war das alte Breakout).
  Vor dem Druck die gekaufte Buchse messen. Die Schrauben-Variante ist eine Annahme
  (Bohrungen quer durch die +y-Wand), `buchseneinsatz()` bei anderer Bauform anpassen.
- Feinführung Zapfen/Schacht ±0,5 plus `spiel` Kragen/Tasche 0,5: Beide Toleranzen
  addieren sich bei ungünstiger Lage. Der Halter (±0,5) fängt den Rest.
- Die Mulden-Wände sind 60°, der Boden hat 2° Gefälle nach vorne (−y), Rinne und vier
  Ablaufbohrungen liegen vorne.
