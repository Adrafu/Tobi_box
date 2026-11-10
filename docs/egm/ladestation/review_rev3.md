# Review Rev. 3 Ladestation (Goldfisch)

* **Gegenstand:** `design_draft.md` (Rev. 3, 09.11.)
* **Gelesen:** Draft, `resolve.md`, `concepts_brief.md`, `review_elektrik.md`,
  `review_mechanik.md`, `research_qi.md`, `stueckliste-und-psp.md` (Punkte 10, 11,
  Stückliste 1.1/1.2, Entscheidungen), Stichworte in `box-software.md`
* **Web:** Pololu-Produktseite #2810 (ON-Pin: "ab etwa 1 V ein", Steuersignal wirkt
  nur bei Schieber "off", sonst keine Angaben zu Eingangswiderstand, Hysterese,
  Einschaltflanke). Rechnungen sind eigene.

## 1. Kurzurteil

Die Reed-Logik (höchstens ein Reed bei 90/180/270°) stimmt. Alles andere, was
Rev. 3 als "doppelt gesichert" und "ebenso schnell aus" verspricht, hält der
Nachrechnung nicht stand. Das RC-Glied schaltet sicher ein, aber nicht schnell
aus (etwa 1 s statt 0,3 s). Das Restrisiko R6 ist falsch zugeschnitten: Der
wahrscheinlichere Fall ist nicht "zwei Fremdmagnete", sondern die eigene Box
über einem vom Stecker-Magneten festgehaltenen Stahlteil. T6 (Widerstände,
Kriterium "Last < 60 °C", Rückfall eFuse) prüft den gefährlichen Bereich
nicht, und die eFuse aus Rev. 2 würde ihn auch nicht abdecken. Die Führung hat
0,5 mm Fangbereich in einer und 2 mm Spiel in der anderen Richtung bei 1,5 mm
Magnet-Fangbereich. Vor Bestellung der Teile sind G1 bis G4 zu klären.

## 2. Nachrechnungen (Grundlage der Befunde)

**Reeds.** Box-Magnete bei (+35/+35) und (-35/+35), Reeds an denselben Stellen.
Drehung um 90° (x,y)->(-y,x): Magnet A (35,35) -> (-35,35) = Reed 2, Magnet B
(-35,35) -> (-35,-35) = kein Reed. 270°: Magnet B -> (35,35) = Reed 1, Magnet A
-> (35,-35) = kein Reed. 180°: beide Magnete auf (-35,-35) und (35,-35), kein
Reed. Ergebnis: höchstens ein Reed. Die Aussage stimmt. Sie gilt aber nur für
exakt diese Drehungen. Mulden-Spiel (±2 mm) ändert daran nichts.

**RC am ON-Pin.** Reeds zu: Teiler 100k/100k, ON-Endwert 2,5 V (5 V Quelle),
Thévenin-R 50 kΩ, C 10 µF, tau_ein = 0,5 s. ON erreicht 1 V nach
t = 0,5·ln(1/(1-0,4)) = 0,26 s. Einschalten sicher (2,5 fach über Schwelle),
auch bei 5,25 V und Reed-Kontaktwiderstand. Wäre die echte Schwelle 1,65 V
(Pololu sagt nur "etwa 1 V"), sind es 0,54 s. Reeds offen: Die obere 100k ist
getrennt, C entlädt nur über die untere 100k: tau_aus = 1 s. Von 2,5 V auf
1 V: t = 1·ln(2,5) = 0,92 s. Der Draft sagt "ebenso schnell". Das ist um den
Faktor 3 bis 4 falsch.

**Verlustleistung am Fremdmetall (R6).** Quelle 5,1 V, Netzteil-Grenze 3 A.
Widerstand R über Plus/Masse: R = 1 Ω: Quelle limitiert, ~9 W. R = 1,7 Ω: 3 A,
15 W. R = 2 Ω: 2,55 A, 13 W. R = 3 Ω: 1,7 A, 8,7 W. R = 5 Ω: 1 A, 5 W. Der
Strom liegt ab etwa 2 Ω unter dem normalen Ladestrom (2,5 A). Weder PTC noch
Netzteil noch eine eFuse mit 2,7 A Grenze erkennen das. Der Draft nennt
"mehrere Watt", real sind bis ~15 W möglich.

**Geometrie auf dem Steg.** Steg 3 mm hoch an der Rückseite, Box kippt nach
vorn auf die Vorderkante (Schwerpunkt vor dem Steg). Bei Steg bei y = +50 und
Vorderkante bei y = -60 ist der Boden bei y = 0 etwa 1,6 mm und bei y = +35
etwa 2,6 mm über dem Mulden-Boden. Der Stecker (Mitte) hat dann ~1,6 mm
Abstand, innerhalb des Fangbereichs von "≥ 1,5 mm". Die Reeds hinten sind
nur 2,6 mm höher als im Endstand.

**Stückliste.** Summe der Zeilen: 20+15+10+4+5+15-2-10+10+6 = 73. Stimmt.
Plan 1.2: 22 + 8 = 30. Stimmt. Der Magnetabzug stimmt nicht (siehe G14).

## 3. Befunde

| Nr. | Schwere | Abschnitt | Befund | Vorschlag |
|---|---|---|---|---|
| G1 | Blocker | 4.4, A6, T6 | R6 beschreibt den falschen Fall. Die Magnete im Sockel-Stecker ziehen Stahl an die Pins: Büroklammer, Heftklammer, Stahlschraube, Euro-Cent-Münzen (1, 2, 5 Cent sind Stahl mit Kupfer). Das Teil klebt dann auf den Pins und schließt Plus und Masse. Setzt das Kind jetzt die **eigene Box** auf (kein Fremdmagnet nötig), hebt das Teil die Box 1 bis 2 mm an. Die Reeds haben Reserve (Faktor 1,5, M1/M13) und schließen trotzdem. Ergebnis: Kurzschluss auf Netzteil/PTC, ohne jede "Zwei-Fremdmagnete-Koinzidenz". R6 nennt nur die seltene Koinzidenz und nennt die Stecker-Magnete nicht als Ursache. Rev. 2 hatte dieses Problem nicht (keine Magnete an den Pins). | R6 neu schreiben: Eintrittsbedingung ist "ferromagnetisches Teil auf den Pins + normale Box". Neuer Test: Stahl-Cent, Büroklammer, Heftklammer auf die Pins legen, Box aufsetzen, Reeds und Temperatur beobachten. Gegenmaßnahmen: Pin-Feld unter einer Abdeckung/Kragen, der Teile von den Pins fernhält, oder Stecker ohne offen liegende Magnete über den Pins, oder Reed erst bei Box ganz unten (kein Reserve-Faktor 1,5). Entscheidung R6 mit Tobias neu treffen, weil die Grundlage falsch ist. |
| G2 | Blocker | 3.1 ON-Pin, 4.4 | Das RC-Glied schaltet **nicht** "ebenso schnell" aus, sondern nach ~0,9 s (tau_aus = 1 s, siehe Rechnung). Folgen: (a) Beim Abheben liegen die Pins ~1 s unter Spannung, ohne Box. A4 gilt nur im Stand. (b) Der Kontakt trennt unter Volllast, nicht lastfrei (E5 aus dem Elektrik-Review wird vom RC-Glied nicht gelöst, sondern verstärkt). Bei 5 V entsteht kein Lichtbogen, aber Spannungsspitzen aus der Zuleitungsinduktivität gehen auf die Pins und den TVS. (c) "Prellen fällt in diese Zeit" gilt für Ein und Aus, aber 1 s ist für Prellen unnötig lang. | Aus-Zeit getrennt auslegen: Diode (Schottky, Kathode zur ON-Seite) parallel zur oberen 100k würde das Entladen nicht beschleunigen; besser Entladung über eigene kleine Strecke: Reed schaltet gegen ein zweites Widerstandsnetz, oder C kleiner (1 µF: tau_ein 50 ms, tau_aus 100 ms). Zahlen im Draft korrigieren (0,26 s ein, 0,9 s aus) und Pololu-Schwelle (1 V "etwa", keine Hysterese angegeben) am Muster messen. T-Test: Oszilloskop beim Aufsetzen und Abheben unter Last (fehlt, siehe G11). |
| G3 | Blocker | 4.4, T6 | T6 und sein Rückfall taugen nicht. (a) Widerstände 0,2 bis 3 Ω bei bis zu 15 W: Kriterium "Last < 60 °C" ist für den Widerstand selbst unerreichbar (Drahtwiderstand wird deutlich heißer). Gemeint sein kann nur das Material am Stecker. (b) Ein Widerstand erwärmt nicht die Stecker-Pins wie ein Metallteil mit schlechtem Kontakt an der Pin-Spitze. Der Test bildet den Heizpunkt nicht ab. (c) 60 °C ist für PETG/Epoxy (Erweichen ab ~70 bis 80 °C) und Kinderhände ein brauchbarer Wert, aber nur, wenn er am heißesten Punkt direkt an der Stelle der Wärme gemessen wird (Thermoelement am Pin-Halter). (d) Rückfall "eFuse-Platine aus Rev. 2" schützt hier nicht: Stromgrenze ~2,7 A, der Gefahrenbereich ab ~2 Ω liegt darunter. Nur die Übertemperaturabschaltung des Chips greift, und die misst die Chip-, nicht die Pin-Temperatur. T6 liefert also keinen Weg zu einem sicheren Zustand. | T6 ändern: echtes Metall (Stahlwolle, Büroklammer, Stahl-Cent) und Widerstände, Thermoelement am Pin-Halter und Gehäuse (nicht am Widerstand), Netzteil-Verhalten (Hiccup/Rasten) dokumentieren. Pass-Kriterium Temperatur am Gehäuse/Pin-Halter. Rückfall neu definieren: Temperaturfühler (NTC) am Pin-Halter mit Abschaltung, oder Strom <= Ladestrom nicht unterscheidbar akzeptieren und das offen benennen. |
| G4 | wichtig | 4.1 Steg/Nut, 4.2, T4 | Die Führung hält nicht, was sie verspricht. (a) Nut 5 mm, Steg 4 mm: nur ±0,5 mm Fangbereich quer zum Steg. Die Mulde lässt ±2 mm. Bei 3D-Druck-Toleranz (±0,2 je Teil) liegt das Kind oft auf dem Steg, obwohl es richtig herum steht. Die Box muss 1,5 mm über den abgerundeten Steg rutschen, ohne Fase an der Nut und mit TPU/PETG-Reibung. (b) Längs zum Steg ist das Spiel ±2 mm (Nutlänge nicht genannt), der Stecker fängt aber nur ≥ 1,5 mm. Die eigene Regel aus M3/Resolve ("Mulden-Spiel nie größer als Fangbereich") ist verletzt. Beim Stecker mit kleinen Pads (2 mm) reicht das nicht für Kontakt. (c) Auf dem Steg kippt die Box (Rechnung oben): Stecker ~1,6 mm entfernt, Reeds fast geschlossen, Pins stehen vor. Es kann ein Zustand "Box falsch, Reeds zu, Pins unter Spannung 0,6 mm unter der Box" entstehen. T4 misst nur "falsch herum, 0 V" und "richtig herum lädt". Nicht getestet: richtig herum, aber 1 bis 2 mm quer versetzt auf dem Steg. | Nut breiter (7 bis 8 mm) mit 45°-Fasen, Steg oben schmaler. Nutende als Anschlag (Länge 62 bis 64 mm) für die Längsrichtung. Mulden-Spiel auf ≤ Fangbereich ODER Fangbereich ≥ Spiel. T4 um "richtig herum, versetzt auf dem Steg: lädt oder 0 V?" erweitern, und 0 V an den Pins bei jedem Kipp-Zustand messen. |
| G5 | wichtig | 4.1, A9, A1 | Steg bricht: Festigkeit ist kein Problem (Rippe 3×4×60 mm, gedruckt, Biege-/Schubkraft deutlich über 100 N). Die Gefahr ist anders: (a) Ist der Steg ein eingeklebtes/geschraubtes Teil, löst er sich. (b) Bricht er ab oder wird abgefeilt, liegt die Box in jeder Lage plan. Dann schützen nur noch die Reeds (Elektrik bleibt sicher, aber das Kind lädt dann auch falsch herum, wenn der Stecker es zulässt). (c) Die Nut (4 mm tief) im Box-Boden sammelt Dreck und schwächt den Boden. Ihre Lage zu Magnet-Taschen (y = +35, ø 8, Abdeckung 1,2 mm) und PiSugar ist nicht gezeichnet. | Steg und Mulden-Boden aus einem Druck (kein Klebeteil). Bruchstück-Größe prüfen (A9). In T12 einen Schlag/Zug gegen den Steg und einen Test "Nut voll Krümel, Box sinkt trotzdem". Nutlage und Bodenstärke vor Freigabe in einer Maßzeichnung belegen (offen Punkt 4). |
| G6 | wichtig | 4.2 | "Ein einzelner fremder Magnet schließt nie beide Reeds, sie liegen 70 mm auseinander" ist falsch für lange Magnete. Magnetbausteine (z. B. Magna-Tiles 76 mm, Playmags 74 mm) haben Magnete an den Kanten, Kühlschrank-Magnetleisten und Magnetstreifen sind 100 bis 150 mm lang, Handy-/Tablet-Magnethüllen ebenso. Ein Teil dieser Art, das flach in der Mulde hinten liegt, trifft beide Reeds. Auch zwei Tobies in der Mulde (je ~35 mm Mitte) sind denkbar. Rev. 2 hatte die Reeds an gegenüberliegenden Ecken (99 mm), Rev. 3 an benachbarten (70 mm). Das ist nicht benannt. | Reeds diagonal setzen (99 mm) und Magnete diagonal, dann gilt bei 90° und 270° weiterhin "höchstens einer" (nachrechnen). Fremdmagnetliste in T1 um Magna-Tile, Magnetleiste, MagSafe-Hülle und zwei Tobies erweitern. Aussage im Draft ändern. |
| G7 | wichtig | 3.2, A4, T0 | Magnet-Pogo-Stecker: (a) Stecker-Magnete ziehen Stahl und Eisenstaub an die Pins (siehe G1). Stahlstaub/Späne überbrücken 2,5 mm Pitch. (b) Reed-Störung: Stecker-Mitte zu den Reeds sind es sqrt(35²+35²) = 49,5 mm, nicht "≥ 40 mm" als Messung, aber ausreichend. Offen bleibt Feld aus dem Steg-Bereich und Wechselwirkung mit den Box-Magneten (8×3 neodym) auf den Stecker-Magneten in 35 mm Entfernung (Verkippen, Ausrichtung). (c) Fangbereich: ≥ 1,5 mm gegen Mulden-Spiel ±2 mm (G4). (d) Verpolung "durch Magnetpolung": Bei 2+2 Pins in Reihe muss das Magnet-Muster so kodiert sein, dass eine 180°-Drehung abstößt. Das ist beim Typ ungeprüft. T0 testet es nicht. (e) Pins unterschiedlicher Länge fehlen (Masse zuerst aus Rev. 2). | T0 um Verpolung (180°-Mating von Hand), Stahlteile (Cent, Klammer) und Abstand zu den Reeds (Reed-Test mit Stecker-Paar daneben) erweitern. Typ nur mit codierter Magnetpolung wählen. |
| G8 | wichtig | 3.1 PTC/TVS/Elko | PTC: Halte ≥ 1,3 × gemessener Ladestrom. Bei 2,5 A Ladestrom sind das 3,3 A Halte, Auslöse ~6,5 A, Netzteil liefert 3 A. Der PTC löst bei Überlast nie aus und schützt nichts außer der Verdrahtung, bei 3 A Netzteil kann er auch nichts abschalten. Er kostet 0,1 bis 0,25 V (E7) und senkt A8. Streiche ihn aus der Schutzkette oder benenne ihn nicht als Schutz. TVS P6KE6V8A: Sperrspannung ~5,5 V, bei 5,25 V schon Leckstrom im 100 µA bis 1 mA Bereich, klemmt erst bei ~10,5 V, das ist für PiSugar-Eingang knapp; Elko 100 µF nach PTC OK. Der Kommentar "Schottky am Ausgang" aus E6 fehlt. | PTC-Rolle im Draft klarstellen (kein Hauptschutz). TVS mit niedrigerer Klemmung (z. B. SMAJ5.0A) wählen oder Leckstrom messen. Schottky-Entscheidung (ja/nein) festhalten. |
| G9 | wichtig | A11, 4.1, 5, T3/T4 | Widerspruch bei der Rückmeldung: A7 und T3 verlangen "Box bleibt aus und lädt". T4 und A11/4.1 verlangen "LED-Ring zeigt blau". Der Ring läuft nur, wenn der Pi läuft (CUJ 18: "Die Box läuft"). Eine ausgeschaltete Box hat keinen Ring. Das Kind (blind, im Dunkeln, D1) bekommt bei falsch herum **und** bei richtig herum, solange die Box aus ist, keine Rückmeldung. A2 sagt nur "Klack". Kein Hinweis am Sockel (D6). T4 ist so nicht bestehbar. | A11/T4 klären: Wie erfährt das Kind bei ausgeschalteter Box, dass sie lädt (z. B. PiSugar-Ladeanzeige-LED an der Box, falls erreichbar; Klack allein)? T4-Kriterium auf "Ladestrom messbar, PiSugar meldet Lader" umstellen. Die Konsequenz (Kind weiß nicht, ob Box lädt) offen als Verlust von Rev. 2 benennen. |
| G10 | wichtig | 1, 4.1 | Nicht benannte Verluste von Rev. 2 auf Rev. 3: (1) Blindes Andocken in jeder Drehlage (D1/D2) ist weg. A2 sagt "eingeschränkt", aber nicht, dass das Kind ohne Rückmeldung falsch ablegen kann (G9). (2) Reeds von gegenüberliegenden zu benachbarten Ecken (G6). (3) Masse-zuerst und längere Ring-Pins (E5). (4) Konischer Zapfen mit Fangbereich und Regel "Spiel ≤ Fangbereich" (M3). (5) Softstart/Strombegrenzung/Übertemperatur der eFuse (nur teilweise genannt); der #2810 hat keinen Softstart, das RC-Glied verzögert nur. (6) Höhenkette, Auflage auf festen PETG-Anschlägen (M2) wird nirgends mehr gerechnet; jetzt Steg und TPU-Ecken. (7) Dichtung der Pins, Reinigungshinweis (M9, M21) nur teilweise. | Tabelle in Abschnitt 1 um eine Spalte "Verloren" ergänzen. |
| G11 | wichtig | 6 | Tests aus dem Resolve fielen in Rev. 3 ohne Erwähnung weg oder wurden schwächer: Prellen/Spitzen mit Oszilloskop beim Aufsetzen und Abheben (E17, M20), Drehversatz 0/5/10/15° und Aufsetzen aus 5 bis 10 cm (M16, T4 hat nur "Versatz und leichte Schräglage"), Sockel auf schrägem/weichem Untergrund (M10), Zyklen ≥ 500 (T11 jetzt 300), T9 "bis Beharrung ≥ 3 h" (jetzt "leer -> voll"). T4 verlangt "20× richtig", das ist kein Kleinkind-Szenario (R4 akzeptiert, aber A2 behauptet Kindertauglichkeit). | Tests aus dem Resolve übernehmen oder bewusst streichen und in 6 vermerken. T11 auf ≥ 500 Zyklen. |
| G12 | wichtig | 3.3, 4.3 | Magnete und Stahl: Neodym 8×3 mm in der Box (zwei) und Stahlscheiben im Sockel-Boden (200 bis 300 g, "wenn T5 es verlangt"). Zieht ein Box-Magnet auf Stahl, ist die Haltekraft deutlich höher als die genannten "50 bis 100 g" des Stecker-Magneten (ein 8×3 N35 hält an Stahl Größenordnung 1 kg, durch 3 bis 4 mm Material noch mehrere hundert Gramm). A3 (einhändig abheben) und M11 sind gefährdet. Außerdem können Stahlscheiben die Reeds abschirmen (M13). Lage der Scheiben ist nicht festgelegt. | Stahlscheiben nur außerhalb der Magnet- und Reed-Bereiche oder Messing/Blei verwenden. T5 mit Federwaage (Kriterium wie M11). |
| G13 | Hinweis | 5 | Auto-Power-On: Quelle fehlt weiter, Bericht #168 belegt Starten beim Laden. Die Aussage "bleibt aus" in A7 ist damit eine Annahme. Das ist benannt (T3), aber T3 hat kein Fallback, wenn das Wecken auftritt (kein Plan B im Design). | Plan B nennen (Softwareseitig sofort wieder abschalten? PiSugar-Konfig?). |
| G14 | Hinweis | 7, 7.1 | Stückliste: Summe 73 stimmt, Mehrkosten 43 € stimmen rechnerisch. Prüfen: (a) Magnete: Plan 1.1 hat 4 Stück für 4 € pro Box. Zwei weniger je Box sind -2 € je Box, also -4 € für zwei Boxen, nicht -2. (b) Stecker: 5 Paare à 3 € sind zu niedrig, wenn Mill-Max/Promax/ATTEND (~6 $) dabei sind; Versand aus DigiKey/Farnell/Pololu nach AT (je 10 bis 20 €) und Einfuhr fehlen ganz. (c) T6 braucht Leistungswiderstände 10 bis 25 W (0,2 bis 3 Ω), Thermoelement, ggf. Netzteil für den schlechten Fall: nicht in der Liste. (d) Abweichungen 7.1: Plan Punkt 11 und PSP 3.5.2 (Load-Switch mit Reed-Erkennung, jetzt mit RC), Plan-Zeile 80 bis 82 ("zentriert wird über Mulde und Zapfen") sind veraltet und fehlen in der Liste. Stückliste 1.1 "Neodym (Zentrierung)" wird zu "Reed-Auslöser". | Stückliste und 7.1 ergänzen. |

## 4. Offene Fragen an den Autor

1. Ist R6 ausdrücklich für den Fall "Stahlteil auf den Pins + eigene Box"
   akzeptiert (G1), oder nur für "zwei Fremdmagnete"? Das sind zwei verschiedene
   Wahrscheinlichkeiten.
2. Wo genau liegt der Steg (y-Koordinate), wie lang ist die Nut, wie dick ist
   der Box-Boden? Ohne diese Maße sind G4/G5 nicht abschließend prüfbar.
3. Wie viel Stromaufnahme (T2) wird erwartet? Davon hängen PTC-Wert und Sinn
   des PTC ab (G8).
4. Soll die Box bei Kontakt mit dem Dock ausgeschaltet bleiben? Wenn ja, wie
   erfährt das Kind, dass sie lädt (G9)?
5. Welchen Rückfall gibt es, wenn T6 (richtig gemessen) durchfällt, wenn die
   eFuse den Bereich 1 bis 2,7 A nicht abdeckt?
6. Welche Schwelle und welche Hysterese hat der ON-Pin des #2810 wirklich?
   Pololu nennt nur "etwa 1 V". Wird das am Muster gemessen, bevor die
   RC-Werte feststehen?
7. Sind die Reeds bewusst benachbart statt diagonal? Warum wurde die Rev.-2-Lage
   verworfen?
