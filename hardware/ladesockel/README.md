# Druckmuster Ladesockel, Variante 4a „hoher Kragen“

Zweck: Führung, Stecken und Abheben mit einem echten USB-C-Kabel testen, **bevor** die
Box konstruiert ist. Keine Elektronik außer dem Breakout als Passprobe.

Datei: `druckmuster_fuehrung.scad` (OpenSCAD). Alle Maße stehen als Parameter oben in der
Datei. Auswahl mit
`teil = "sockel" | "boxboden" | "halter" | "kragenprobe" | "alle"`.
Zum Ansehen gibt es zusätzlich `"baugruppe0"` und `"baugruppe90"` (Schnitt in y = 0,
Sockel und Boxboden in Endlage, Stecker und Halter eingesetzt).
STL erzeugen: `openscad -D 'teil="sockel"' -o sockel.stl druckmuster_fuehrung.scad`.
STL gehören nicht ins Repo.

## Was sich gegenüber der Rippen-Version ändert

- **Weg:** Rippen im Sockel, Nuten im Boxboden und alle Asserts dazu.
- **Neu: Kragen** im Sockel, fest mit der Mulde gedruckt, rechteckig und konisch,
  länglich (lange Seite in x): unten 36 × 18, oben 30 × 12, 14 hoch. Oben ein Schacht
  12 × 7, in dem der Stecker steht.
- **Stecker:** Die Metallspitze liegt 2 mm unter der Kragenoberkante (Höhe 12). Der
  TPU-Halter erlaubt ±0,5 mm seitlich. Der Flansch liegt auf einer **festen Schulter**
  im Sockel: Die Steckkraft (bis 20 N) drückt nicht in den TPU. Der Kragen schwimmt nicht.
- **Tasche im Boxboden:** konisch, passend zum Kragen mit `spiel` = 0,5 je Seite:
  Öffnung 37 × 19, oben 31 × 13, 14 tief. Kein zusätzlicher Einlauf an der Öffnung, der
  würde bei 90° die Auflage auffressen.
- **Buchsen-Zapfen** (11 × 6) hängt vom Taschendach nach unten. Die Buchsen-Öffnung liegt
  5,5 mm über der Boxbodenfläche, der Zapfen ragt nicht über die Bodenfläche hinaus. Er
  taucht in den Schacht ein (Feinführung ±0,5).
- **Lage bei 90° und 270°:** Die Tasche passt nicht über den Kragen. Die Box liegt auf
  zwei Auflagen von je 5,5 × 12 mm, 14 mm über der Normallage.
- **Kabelrinne für unterwegs:** 14 breit, 8 tief, von der Tasche bis zur Rückkante.
- **Gewichtsraum** für ca. 1 kg Stahl (Parameter `gewicht_soll`), dafür ist das Unterteil
  höher (`unterteil_h` = 22).
- **Option `befestigung = true`:** zwei Schraubenlöcher mit Senkung hinten im Muldenboden.
- **Neues Teil `kragenprobe`:** Kragen mit Halter-Aufnahme plus Gegenstück mit Tasche und
  Zapfen. 0° und 90° lassen sich in einer Stunde ausprobieren.

## Druckreihenfolge

1. **`kragenprobe`** (PETG, ca. 2 h). Zusammenstecken in 0° und 90°, Spiel prüfen.
2. **`halter`** (TPU 95A, ca. 40 min). Stecker einpressen, in die Kragenprobe setzen.
3. **Messschritt Abzugskraft** (siehe unten), erst danach entscheiden, ob der Sockel
   Befestigung braucht.
4. **`sockel`** (PETG, ca. 18 h, ca. 340 g ohne Stahl).
5. **`boxboden`** (PETG, ca. 4 bis 5 h, ca. 65 g, Stützen nur für den Zapfen).

| Teil | Material | Ausrichtung | Zeit (0,2 mm, 15 %) | Anmerkung |
|---|---|---|---|---|
| `kragenprobe` | PETG | flach; das Gegenstück ist schon gedreht (Zapfen oben) | ca. 2 h | zuerst drucken |
| `halter` | TPU 95A | Flansch unten | ca. 40 min | langsam (20 mm/s), Direct Drive |
| `sockel` | PETG | Boden unten, ohne Stützen | ca. 18 h | Pause für Stahl bei z = 17,8 |
| `boxboden` | PETG | Unterseite unten | ca. 4 bis 5 h | Stützen im Taschen-Mittelteil für den Zapfen, sonst keine |

Zeiten sind Schätzungen, aus dem Volumen gegenüber der Rippen-Version hochgerechnet
(Sockel 517 cm³ statt 456 cm³, Boxboden 80 cm³ statt 124 cm³).

- **Zapfen drucken:** Der Zapfen hängt in der Luft, solange der Boxboden mit der Unterseite
  nach unten liegt. Tree-Stützen nur im Bereich der Tasche zulassen. Wand um die Buchse
  ist ca. 0,7 mm (x) und 1,1 mm (y): zwei Umfänge bei 0,4 mm Düse.
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
| `rec_b` / `rec_d` / `rec_l` | 8,94 / 3,26 / 7,35 | Buchse des Breakouts |
| `pcb_b`, `pcb_h`, `pcb_t`, `loch_dx` | 15, 12, 1,6, 5,5 | Breakout-Platine und Lochabstand |
| `winkel_b` / `winkel_h` / `winkel_l` | 12 / 6 / 20 | gewinkelter USB-C-Stecker: Breite, Höhe unter der Buchse, Länge |

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
   voll stecken. 90° und 270°: Box liegt auf den zwei Auflagen, die Spitze bleibt frei.
3. **Hebeln:** Federwaage seitlich oben an der Box, 20, 40, 60 N. Stecker, Halter und
   Schulter prüfen.
4. **Unterwegs:** gewinkelten USB-C-Stecker in die Buchse stecken, Kabel durch die
   Kabelrinne führen, Box auf den Tisch stellen. Federwaage 20 N am Kabel.

## Rechenergebnisse (Asserts halten, OpenSCAD 2021.01)

| Größe | Soll | Ergebnis |
|---|---|---|
| Auflage je Seite bei 90° | ≥ 4 | 5,5 (je 5,5 × 12) |
| Zapfen-Unterseite über Steckerspitze bei 90° | ≥ 5 | 7,5 (14 + 5,5 − 12) |
| Eingriff des Kragens, bevor die Spitze die Buchse berührt | ≥ 6 | 7,5 (14 − (12 − 5,5)) |
| Zapfen taucht bei Kontakt schon in den Schacht | ≥ 1 | 2 |
| Stecklänge 0°/180° | | 6,5 |
| Unterkante Winkelstecker unter der Bodenfläche | | −0,5, siehe unten |
| Gewichtsraum | ≥ 1000 g | ca. 1040 g |

## Was die Datei annimmt, und offene Punkte

- **Bezugsebene `z0`:** Alle Höhen der Aufgabe gelten ab der Boxbodenfläche in
  Normallage. Sie liegt `sitz_h` = 3 mm über dem Mulden-Boden in der Mitte, weil der
  Mulden-Boden 2° Gefälle hat (hinten 2,1 mm höher). Bei 0 mm würde die Box hinten
  aufsetzen. Der Kragen steht damit 17 mm über dem Mulden-Boden.
- **Kabelrinne in x statt y:** Die Rinne (14) ist breiter als die Kragenoberkante (12).
  Läuft sie wie in der Aufgabe nach hinten (y), liegt sie bei 90° quer über einer Auflage
  und frisst sie, die Box läge nur auf einer. Deshalb läuft sie standardmäßig in x
  (`rinne_achse = "x"`) und lässt beide Auflagen frei. Mit `rinne_achse = "y"` schlägt der
  Assert an. **Entscheidung bei Tobias.**
- **Winkelstecker 0,5 mm unter der Bodenfläche:** Körper 6 hoch unter der Buchsen-Öffnung
  bei 5,5 ergibt −0,5. Der Assert prüft deshalb gegen die TPU-Ecken (`ecke_unter` = 2),
  auf denen die Box auf dem Tisch steht. Ohne TPU-Ecken schlägt er an.
- **Breakout passt nicht in den Zapfen:** Die Platine (15 breit) ist breiter als der Zapfen
  (11) und sitzt deshalb im Taschendach, Unterkante auf Höhe 14. Die Buchse (7,35 lang,
  Öffnung bei 5,5) reicht damit nicht bis zur Platine. Für die Kragenprobe egal, für die
  echte Box offen: Platine unten auf < 9,5 mm kürzen, oder Einbaubuchse mit Litzen.
  Schraublöcher und Platinenschlitz sind eine Annahme, `platinenraum()` bei anderer
  Bauform anpassen.
- Feinführung Zapfen/Schacht ±0,5 plus `spiel` Kragen/Tasche 0,5: Beide Toleranzen
  addieren sich bei ungünstiger Lage. Der Halter (±0,5) fängt den Rest.
- Die Mulden-Wände sind 60°, der Boden hat 2° Gefälle nach vorne (−y), Rinne und vier
  Ablaufbohrungen liegen vorne.
