# Druckmuster Ladesockel (Rev. 4): Führung, Stecken, Hebeln

Zweck: Tests T1, T2, T3 und T8 aus `docs/egm/ladestation/design_draft.md`
mit einem echten USB-C-Kabel, **bevor** die Box konstruiert ist. Keine Elektronik.

Datei: `druckmuster_fuehrung.scad` (OpenSCAD). Alle Maße stehen als Parameter
oben in der Datei. Auswahl mit `teil = "sockel" | "boxboden" | "halter" | "kragenprobe" | "alle"`.
STL erzeugen: `openscad -D 'teil="sockel"' -o sockel.stl druckmuster_fuehrung.scad`.
STL gehören nicht ins Repo.

## Erst am echten Stecker messen (Messschieber)

Das Netzteil-Kabel (Raspberry Pi 15 W) ist festgelegt, der Stecker bestimmt den Halter.

| Parameter | Vorgabe | Was messen |
|---|---|---|
| `stecker_b` | 12,5 | Umspritzkörper, Breite |
| `stecker_d` | 6,5 | Umspritzkörper, Dicke |
| `stecker_l` | 20 | Umspritzkörper, Länge bis zur Metallschale |
| `stecker_schale` | 6,7 | Metallschale, Länge (Steckerspitze bis Körper) |
| `kabel_d` | 4,0 | Kabeldurchmesser |
| `pcb_b`, `pcb_h`, `loch_dx` | 15, 12, 5,5 | Breakout-Platine, Lochabstand (Schraubloch Ø) |
| `rec_b/d/l` | 8,94 / 3,26 / 7,35 | Buchse des Breakouts |

Ändert sich ein Maß, stimmen Steckerspitze, Rippenhöhe und Tasche automatisch
nach. Die `assert`-Zeilen oben melden, wenn die Rechnung nicht mehr aufgeht
(z. B. Rippen zu niedrig, Eingriff unter 5 mm).

## Teile, Material, Zeit (grobe Schätzung, 0,2 mm Schicht, 15 % Füllung)

| Teil | Material | Ausrichtung | Zeit | Anmerkung |
|---|---|---|---|---|
| `kragenprobe` | PETG | flach, Boden unten | ca. 1,5 h | **zuerst drucken**, prüft Kragen/Tasche und Halter |
| `halter` | **TPU 95A** | Flansch unten | ca. 40 min | langsam drucken (20 mm/s), Direct Drive |
| `sockel` | PETG | Boden unten, ohne Stützen | ca. 16 h, ~300 g | siehe Gewicht |
| `boxboden` | PETG | Unterseite unten, ohne Stützen | ca. 6 h, ~100 g | Nuten und Tasche sind überbrückt |

- **Sockel-Gewicht:** Zwei Hohlräume (je 46 × 100 × 9 mm) im Unterteil. Druck bei
  z = 10,8 mm pausieren, Stahlscheiben einlegen (Stapel höchstens 8,6 mm hoch,
  insgesamt ca. 0,65 kg), weiterdrucken. Ziel Sockel gesamt ≥ 1 kg. Die Hohlräume
  sind danach zu, nichts kann sich lösen.
- **Kabel:** Stecker von oben durch den Kragen in die Halter-Aufnahme legen, das Kabel
  nach unten durch die Bohrung in den Kanal an der Unterseite drücken (Klemmzone
  ist 0,5 mm schmaler als das Kabel), einen Kabelbinder durch die zwei Schlitze
  ziehen. Unterseite mit Filz oder Gummiplatte abkleben (deckt auch den Kanal).
  Die vier Ablaufbohrungen enden an der Unterseite, dafür Gummifüße (3 mm) setzen.
- **Halter:** Der TPU-Flansch muss zum Einsetzen in den Kragen leicht verformt werden
  (1,25 mm Überstand je Seite). Geht das nicht, `flansch_ueber` verkleinern.
- **Boxboden:** Mit Gewicht auf ca. 0,8 kg beschweren (Stahl, Sand im Beutel).
  Breakout mit der Buchse nach unten an der Platinenwand verschrauben (`schraube = "M2"` oder `"M2.5"`).
  Die Ecken-Aussparungen (18 × 18 × 2 mm) nehmen TPU-Ecken auf. Ohne TPU-Ecken
  bleibt die Box 2 mm tiefer, dann `ecke_unter = 0` setzen.

## Testen

1. **Kragenprobe** zusammenstecken: Kragen in Tasche, Halter in den Kragen. Soll leicht
   gehen, ohne zu klemmen. Sonst `spiel` anpassen (je Seite, Vorgabe 0,4).
2. **T1 Führung:** Box 50 × aufsetzen, schräg, verdreht, mit Versatz. 0° und 180° müssen
   stecken. Bei 90° und 270° liegt der Boxboden auf den Rippen, der Stecker bleibt
   mindestens 2 mm frei (Spalt von der Seite prüfen).
3. **T2 Hebeln:** Federwaage seitlich oben an der Box, 20, 40, 60 N, alle Richtungen.
   Stecker und Halter prüfen.
4. **T3 Abheben:** einhändig, senkrecht und schräg. Abzugskraft messen (Ziel < 20 N). Der Sockel darf nicht mit abheben.
5. **T8 Unterwegs:** gewinkelten USB-C-Stecker in die Buchse stecken, Kabel durch die
   Kabelrinne nach hinten führen, Box auf den Tisch stellen. Federwaage 20 N am Kabel.

## Was die Datei annimmt

- Rippen laufen in x. Die **Kabelrinne** läuft vom Kragen aus nach hinten (+y) bis zur
  Rückkante des Boxbodens. Sie kreuzt die hintere Nut. Das ist die Auslegung der Aufgabe, im
  Entwurf ist die Lage der Rinne nur beschrieben.
- Die Rippen müssen hoch sein (ca. 27 mm über Mulden-Mitte), weil der Stecker mit Halter
  ca. 25 mm hoch steht. Sie ragen über den Muldenrand. Kürzerer Stecker oder tieferer
  Halter senken die Rippen.
- Das Breakout steht senkrecht, die Buchse sitzt an der Unterkante und öffnet nach unten.
  Hat dein Breakout eine andere Bauform, ist `platinenraum()` anzupassen.
- Die Mulden-Wände sind 60°, der Boden hat 2° Gefälle nach vorne (-y), die Rinne mit den
  vier Ablaufbohrungen liegt vorne.

## Prüfstand dieser Fassung

OpenSCAD 2021.01 (per `apt-get install openscad` installiert). Alle vier Teile
rendern ohne Fehler zu STL, die `assert`-Zeilen halten.
