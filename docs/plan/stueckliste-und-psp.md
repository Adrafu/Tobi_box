# Tobi Box — Stückliste & Projektstrukturplan

Rev. 3.7 · 05.11.2026 · Pi 3 Model A+ · Phoniebox V3 als Basis · zwei baugleiche, mobile Boxen

**Änderungen gegenüber Rev. 2**
- Software-Basis: Phoniebox V3 + eigene Plugins statt Eigenbau
- Mobil-Betrieb: Laden unterwegs per USB-C, Offline als Normalfall, RTC als Zeitquelle
- Akku-Fehler korrigiert: PiSugar 3 Plus ist für Pi 3B/4B gebaut, Passung an der Zero muss verifiziert werden
- Komplette Review eingearbeitet (Teil 0)
- **3.1:** Kopfhörer per Klinkenbuchse ergänzt, offene Entscheidungen getroffen
- **3.2:** Pi 3 Model A+ statt Pi Zero 2 W, weil die Zero ausverkauft ist. Passt ohne Umbau auf den PiSugar 3 Plus
- **3.3:** Tonie-Figuren als Schlüssel: Testset (PN5180 + ESP32-S3) und Weiche in 3.1.5, der RC522 bleibt Rückfallebene
- **3.4:** Review: Plan mit Bestellliste abgeglichen (Pololu-Ideal-Diode, 40-LED-Ring, USB-C-Breakout), fünf technische Lücken geschlossen (Teil 0, Punkte 26–30), Kosten neu
- **3.5:** Tonie-Test läuft: Karte und Tonie werden gelesen, eigenes Passwort entsperrt die Figur. Neu: Plugin Figuren-Zuordnung (5.10), neue Tonies mit einem Tipp am Handy einer Serie zuordnen
- **3.6:** Entscheidung 04.11.: Echte Tonies sind Pflicht, deshalb ist der **PN5180 gesetzt**. Der RC522 entfällt als Rückfallebene (kann kein ISO 15693). Der Deckel-Test entscheidet nur noch die Deckelstärke, nicht mehr den Leser. Stückliste, Pinplan und kritischer Pfad entsprechend bereinigt
- **3.7:** Deckel-Test Teil 1 (05.11.): **Test 5 bestanden** — durch 2 mm liest der PN5180 zentriert 100 % (58 ms, Feld nur 15,9 % an). MagSafe-Hülle als Gegenprobe liest ebenfalls 100 %, weil der Magnetring ein freies Zentrum hat. Drei Design-Regeln abgeleitet (Zentrierung über der Antenne, kein Vollmetall/Magnet über der Antennenmitte, UID-Entprellung in der Firmware). Offen bleiben Test 5b (Stahlscheibe mittig) und Test 6 (max. Distanz)

---

# Teil 0 — Review

## Kritisch

**1. PiSugar-Passung** — erledigt in 3.2: Pi 3 Model A+ statt Zero 2 W, der PiSugar 3 Plus
passt mit allen vier Löchern. Preis: höherer Ruheverbrauch, siehe 1.5.

**2. Resume** — Phoniebox V3 hat keines, wird eigenes Plugin nach Toniebox-Logik (5.4).

**3. Andocken darf nicht wecken** — Auto-Power-On aus (5.6.5), Test in 8.2.4.

## Hardware

**4. Hauptknopf braucht keinen GPIO.** Der PiSugar führt bei Einfach-, Doppel-
und Langdruck frei wählbare Shell-Befehle aus. Damit: Einfach = Play/Pause per
Phoniebox-RPC, Lang = Position sichern + Herunterfahren (`soft_poweroff_shell`).
Der Arcade-Knopf wird parallel zum Bordtaster des PiSugar gelötet.

**5. Pop-Unterdrückung macht der Kernel.** Das Overlay `max98357a` steuert
SD_MODE selbst (Default GPIO 4) und schaltet den Verstärker stumm, solange kein
Stream läuft. Eigener Open-Drain-Code entfällt. Haken: Der Treiber zieht SD_MODE
hart auf High = nur linker Kanal → **Downmix auf Mono in Software**, sonst geht
bei Stereo-Hörspielen der rechte Kanal verloren.

**6. APA102 brauchen einen Pegelwandler.** Bei 5 V Versorgung liegt die
High-Schwelle bei ~3,5 V, der Pi liefert 3,3 V. Funktioniert oft, aber nicht
zuverlässig. 74AHCT125 dazwischen, ~1 €.

**7. Zwei Ladeeingänge brauchen Entkopplung.** Pogo und USB-C hängen am selben
Ladeeingang. Ohne Diode liegen beim USB-C-Laden 5 V an den offenen
Pogo-Kontakten **der Box** — dieselbe Kurzschlussgefahr, die wir im Dock gerade
beseitigt haben. Lösung: Pololu Power-ORing-Modul #5398 mit zwei Ideal-Dioden,
beide Eingänge entkoppelt, ein Ausgang zum PiSugar. (Rev. 3.3 nannte den
LM66100, ein SMD-Chip ohne Platine; der Pololu ist die praktikable Form.)

**8. Stromspitzen.** Der bestellte LuMini-Ring hat **40** APA102, auf Vollweiß
~2,4 A. Deshalb drei Maßnahmen: Helligkeit im Plugin fest auf ~25 % deckeln
(~0,6 A), rückstellbare Sicherung 1,1 A im 5-V-Pfad des Rings, 470–1000 µF
Pufferelko am Verstärker (Bass-Spitzen ~1 A).

**9. I²C-Konflikt aus Rev. 1 ist erledigt.** Am I²C sitzt nur noch der PiSugar.
Der Leser (PN5180) hängt über den ESP32-S3 am USB.

**10. Metall weg vom Kartenfeld.** Lautsprecherkorb und Schrauben verstimmen die
NFC-Antenne, Mindestabstand ~2–3 cm. Ausnahme ist der Halt für Tonie-Figuren
(4.2.9): Der Tonie bringt seinen Magneten im Sockel ohnehin direkt an die
Antenne. Ob eine Stahlscheibe in der Feldmitte das Lesen stört, klärt Test 5b
des Tonie-Tests. Stört sie, hält die Figur nur über die Mulde im Deckel.

**11. Dock-Erkennung ohne dritten Pin.** Reed-Kontakt im Dock, ausgelöst vom
Zentriermagnet der Box. Spart einen Pogo-Pin.

**12. UART freihalten.** GPIO 14/15 als serielle Konsole — bei einem Gerät ohne
Bildschirm der einzige Weg, Bootprobleme zu sehen.

## Kindersicherheit (neu)

**13. Neodym-Magnete sind verschluckt lebensgefährlich** — zwei Magnete ziehen
sich durch die Darmwand an. Vollständig eingeschlossen und eingeklebt, auch
nach einem Sturz nicht zugänglich.

**14. Abziehbare Kleinteile:** Encoderknopf mit Madenschraube + Kleber,
Tastenkappen eingeklebt, USB-C-Abdeckung als angedruckte TPU-Lasche statt
loser Stöpsel.

**15. Akku und Gehäuse:** Zelle mechanisch geschützt, kein Druck von außen.
Gehäuse nur mit Werkzeug zu öffnen (Torx statt Clips).

## Software

**16. Betriebssystem:** Phoniebox empfiehlt Pi OS **Legacy 32-bit Lite** — nicht
64-bit wie in meinem früheren Stack. Folgen, sonst kämpfst du gegen die
Installationsskripte.

**17. Was V3 fertig mitbringt** — wird Konfiguration statt Code: USB-NFC-Leser,
Place-not-Swipe mit Aktion beim Abheben, GPIO-Tasten und Encoder, Max- und
Startlautstärke, Idle-Shutdown, Sleep-Timer mit Lautstärkeabsenkung (= die
Gute-Nacht-Karte), MQTT, Karten anlernen in der Web-UI.

**18. Was V3 nicht hat:** Resume, Upload über die Web-UI, Akku-Anbindung an den
PiSugar, LED-Ringe. Upload übernimmt unser Sync-Ordner, der Rest wird Plugin.

**19. WLAN-Powersave:** V3 schaltet beim Start den WLAN-Stromsparmodus ab
(Reaktionszeit). Rev. 2 wollte ihn einschalten → messen statt annehmen.

**20. Auto-Hotspot:** V3 öffnet ohne bekanntes WLAN einen eigenen Hotspot.
Unterwegs heißt das Dauerfunk. Standard aus, per Admin-Karte einschaltbar.

**21. Bibliotheks-Scan beim Start:** V3 aktualisiert die MPD-Bibliothek beim
Booten. Bei großer Sammlung verlängert das die Zeit bis zum ersten Ton →
messen; falls nötig nur nach dem Sync scannen.

**22. Read-only Root zurückgestellt.** Mit dem PiSugar (sauberes Herunterfahren
bei Tiefstand und Langdruck) fällt der Hauptgrund weg. Basis: High-Endurance-SD,
Logs auf tmpfs, atomares Schreiben im Resume-Plugin, SD-Image als Backup.
Overlay erst, wenn in der Praxis Probleme auftreten.

**23. Kopfhörer brauchen eigene Hardware.** Standen im PSP ohne Buchse und ohne
Ausgang. Entschieden in 3.1: Klinkenbuchse mit zweitem DAC, siehe 1.4.

## Planung

**24. Akkus nicht auf Vorrat kaufen.** LiPos altern auch im Regal. Charge 1 nur
Muster für den kritischen Pfad, Akkus für Box 2 erst kurz vor deren Bau.

**25. Phase 6 schrumpft deutlich.** Die eigene Web-UI entfällt, V3 deckt
Kartenverwaltung und Wiedergabe ab.

## Neu in Rev. 3.4 — Lücken aus der Review

**26. Abheben erkennen über den USB-Leser.** Ein USB-Leser tippt die Kennung einmal
und schweigt dann. Phoniebox weiß so nicht, wann die Figur weg ist, und genau das
brauchen „Abheben = Pause" und das Resume-Plugin. Lösung in der ESP32-Firmware:
Solange die Figur liegt, wird die Kennung alle ~500 ms wiederholt, beim Abheben
tippt der Leser einen eigenen Abhebe-Code, den Phoniebox auf „Pause" legt. Das
Testprogramm macht das seit 3.4. Zu prüfen in 5.3.5: V3 muss wiederholte gleiche
Kennungen vom USB-Leser so behandeln wie vom RC522.

**27. Zwei DACs am I²S, nur ein Overlay.** Das Overlay `max98357a` meldet die
Soundkarte an. Der PCM5102A bekommt **kein** eigenes Overlay, sonst streiten zwei
Treiber um dieselbe I²S-Schnittstelle. Er läuft passiv mit: BCLK, LRCLK und DATA
parallel, SCK auf GND (interne PLL), FMT auf I²S. → 3.2.6

**28. Lautsprecher stummschalten bei Kopfhörern.** Den Buchsenkontakt direkt an
SD_MODE zu hängen wäre ein Kurzschluss gegen den Treiber-GPIO. Sauber: 1 kΩ in
Serie zwischen GPIO 4 und SD_MODE, der Buchsenkontakt zieht SD_MODE auf GND. Den
Lautsprecherstrom über den Buchsenkontakt zu führen geht nicht, dafür ist der
Kontakt nicht gebaut. → 3.2.6

**29. Magnet im Kartenfeld vs. Punkt 10.** Widerspruch benannt und auf Test 5b
verschoben, siehe Punkt 10.

**30. PiSugar-Knopf doppelt belegt.** „Lang drücken = herunterfahren" gibt es
zweimal: als Tastenereignis in pisugar-server und als Soft-Poweroff der Firmware.
Welche Dauer was auslöst und ob der PiSugar 3 Plus Lötpunkte für einen externen
Taster hat, ließ sich in der Doku nicht nachlesen. → 3.2.4 am Muster klären.

## Tonie-Figuren (Rev. 3.3, Stand 3.4)

Ziel: Original-Tonies als Schlüssel für eigene Inhalte nutzen. Die Tonie-Inhalte
selbst spielen keine Rolle.

- **Chip:** NXP ICODE SLIX-L nach ISO 15693. Der RC522 kann das nicht, der PN5180
  schon, und er liest auch unsere NTAG215-Karten.
- **Privacy-Modus:** Eine Toniebox setzt den Chip in den Privacy-Modus. Danach
  antwortet er nur noch auf die Zufallszahl-Abfrage (= „ein Tonie liegt auf")
  und gibt seine Kennung erst nach dem Passwort frei. Das Passwort ist für alle
  Tonies gleich, sonst könnte keine Toniebox fremde Figuren erkennen; es ist
  nicht offiziell veröffentlicht. Handy-Vortest 15.10.: gebrauchter Tonie
  antwortet dem iPhone nicht, Privacy-Modus bestätigt.
- **Ohne Passwort:** Box erkennt „irgendein Tonie" und spielt ein
  Überraschungs-Hörspiel. **Mit Passwort:** jede Figur einzeln, auch geborgte.
- **Reichweite:** Der Chip sitzt etwa 2 cm über dem Sockel. Der Leser muss rund
  2,5 cm durch den Deckel reichen.
- **Anbindung:** PN5180 an einem ESP32-S3 SuperMini, der sich am Pi als
  USB-Tastatur ausgibt. Phoniebox V3 unterstützt USB-Leser bereits, ein eigenes
  Plugin entfällt. Die PN5180-Bibliothek von tueddy ist auf ESP32 und ESP32-S3
  erprobt (ESPuino).
- **Strom:** ~0,1–0,2 W mehr mit Abfrage in Intervallen, also 30–60 min weniger
  Laufzeit. Dauerhaft eingeschaltetes Feld wäre fast 1 W und ist tabu.
- **Kosten bei Erfolg:** praktisch null. Das Testset wurde gleich doppelt bestellt
  und reicht für beide Boxen; je Box kommt nur ein USB-Kabel (3 €) dazu, der
  RC522 (3 €) entfällt.
- **Leser gesetzt (04.11.):** Echte Tonies sind Pflicht, nur der PN5180 kann
  ISO 15693. Damit ist der Leser für beide Boxen entschieden, der RC522 entfällt.
  Der Deckel-Test (5/5b/6) entscheidet nicht mehr *ob* PN5180, sondern nur noch
  die Deckelstärke über der Antenne. Scheitert die Reichweite, wird der Deckel
  dünner oder der Chip näher an den Leser gesetzt — kein Leserwechsel.
- **Stand 04.11.:** NTAG-Karte 176 ms, gesperrter Tonie ohne Passwort erkannt,
  mit eigenem Passwort entsperrt (UID beginnt mit E0 04 03), ohne Deckel 100 %
  Treffer. Einmal entsperrt bleibt der Tonie offen, bis eine Toniebox ihn wieder
  sperrt.
- **Stand 05.11. (Test 5 bestanden):** Durch 2 mm (Schaumstoff als PETG-Ersatz,
  RF-technisch gleichwertig) liest der PN5180 zentriert 100 %, 58 ms Lesezeit,
  Feld nur 15,9 % an. Gegenprobe durch eine MagSafe-Handyhülle: ebenfalls 100 %
  ohne messbaren Verlust, weil der Magnetring ein freies Zentrum hat und die
  Kopplung durch die Mitte läuft. Firmware-Fixes bestätigt (doppeltes RF_ON
  entfernt → Feld-an von 73 auf 53 % gesenkt; sameCard vergleicht per UID, kein
  doppeltes AUFGELEGT beim Übergang entsperrt→offen). Offen: Test 5b
  (Stahlscheibe mittig), Test 6 (max. Distanz) und Strom (Test 7).
- **Drei Design-Regeln aus Test 5:**
  1. Figur muss **mittig über der Antenne** sitzen — der Sweet Spot ist schmal,
     daneben gab es 0 % Treffer. CAD: Auflagefläche exakt über die Antennenmitte.
  2. **Kein Vollmetall und kein Magnet direkt über der Antennenmitte** (killt das
     Feld). Ein Magnetring mit freiem Zentrum wäre ok, falls magnetische
     Zentrierung der Figur gewünscht ist.
  3. **UID-Entprellung in der Firmware:** Eine UID erst als Auslöser akzeptieren,
     wenn sie 2–3× identisch gelesen wurde (CRC prüfen, falls die Lib das Flag
     liefert). Am äußersten Rand kippte einmal ein Byte der UID; zentriert ist
     sie stabil. Verhindert, dass ein Randfehler die falsche Folge startet.
- **Keine automatische Erkennung der Figur:** Die Kennung ist eine Seriennummer
  pro Exemplar. Welche Figur das ist, steht nicht auf dem Chip, und eine
  öffentliche Liste „Kennung → Figur" gibt es nicht. Zuordnung deshalb einmal
  pro Exemplar, so einfach wie möglich (siehe unten).

## Figuren zuordnen (Rev. 3.5)

Ziel: Eine neue Figur ist nach einem Tipp am Handy einer Serie zugeordnet,
ohne Weboberfläche und ohne Codes. Die Kinder müssen nie warten.

**Weg A — erst auflegen, dann tippen**
1. Unbekannte Figur liegt auf → Überraschungs-Ordner spielt sofort, LED-Ring
   zeigt „neue Figur".
2. Handy-Seite der Box zeigt „Neue Figur erkannt" und die Serien-Ordner.
3. Ein Tipp auf die Serie → Zuordnung gespeichert, Box wechselt sofort auf die
   Serie.

**Weg B — erst tippen, dann auflegen**
1. Auf der Handy-Seite „Jetzt kommt ein neuer Tonie" tippen und die Serie wählen.
2. Die Box wartet 2 min im Lernmodus, LED-Ring zeigt das an.
3. Die nächste aufgelegte Figur wird dieser Serie zugeordnet und spielt sofort.
   Auch eine schon bekannte Figur wird dabei neu belegt, so lassen sich Fehler
   korrigieren. Abbrechen jederzeit auf der Handy-Seite.

**Regeln**
- Serie = Ordner mit Folgen. Die Box spielt bei jeder Figur der Serie die
  nächste noch nicht gehörte Folge, Resume (5.4) gilt wie bei Karten.
- Gesperrter Tonie ohne Kennung (Passwort fehlt): nicht zuordenbar, immer
  Überraschungs-Ordner.
- Zuordnungen werden zwischen beiden Boxen abgeglichen (6.3), eine geborgte
  Figur muss nur einmal angelernt werden.
- Handy-Seite nur im lokalen Netz (6.6). Unterwegs ohne WLAN gilt Weg A mit
  Überraschungs-Ordner, die Zuordnung folgt zu Hause.
- Funktioniert genauso für neue NFC-Karten.

---

# Teil 1 — Stückliste

Preise sind Richtwerte (AT/DE) und vor dem Bestellen zu prüfen.

## 1.1 Pro Box

| Gruppe | Bauteil | Stk | ca. € |
|---|---|---|---|
| Rechner | Raspberry Pi 3 Model A+ (Header vorbestückt) | 1 | 31 |
| Rechner | Kühlkörper, selbstklebend | 1 | 2 |
| Speicher | microSD 64 GB, A1 High Endurance | 1 | 12 |
| Audio | MAX98357A I²S-Verstärker, 3 W mono | 1 | 6 |
| Audio | Visaton FRS 8, 4 Ω, 80 mm Breitbänder | 1 | 12 |
| Audio | Akustikgewebe | — | 4 |
| Audio | Dichtband + Dichtmasse Audiokammer | — | 3 |
| NFC | USB-Kabel ESP32-S3 → Pi (Leser PN5180 + ESP32-S3 siehe 1.2) | 1 | 3 |
| Strom | PiSugar 3 Plus, 5000 mAh | 1 | 50 |
| Strom | Pololu Power-ORing Ideal-Dioden-Paar #5398 | 1 | 7 |
| Strom | Pufferelko 1000 µF am Verstärker | 1 | 1 |
| Strom | USB-C-Breakout-Buchse mit 5,1 kΩ an CC + USB-C-Pigtail | 1 Satz | 4 |
| Bedienung | Arcade-Button 24 mm (Haupt, Vor, Zurück) | 3 | 8 |
| Bedienung | Rotary Encoder KY-040 + Alu-Knopf | 1 | 5 |
| Anzeige | SparkFun LuMini LED-Ring 2″, 40× APA102-2020 | 1 | 17 |
| Anzeige | Rückstellbare Sicherung (PTC) 1,1 A für den Ring | 1 | 1 |
| Anzeige | Pegelwandler 74AHCT125 | 1 | 1 |
| Kopfhörer | PCM5102A-DAC + 3,5-mm-Buchse mit Schaltkontakt + Widerstände | 1 Satz | 7 |
| Laden | Pogo-Pins 2-polig, gefedert | 1 Satz | 5 |
| Laden | Neodym-Magnete 8×3 mm (Zentrierung) | 4 | 4 |
| Gehäuse | PETG-Filament (anteilig) | — | 10 |
| Gehäuse | TPU-Ecken + USB-C-Lasche (Druck) | — | 3 |
| Gehäuse | M2.5 Gewindeeinsätze + Torx-Schrauben | — | 8 |
| Verkabelung | JST-Kabel, Litze, Schrumpfschlauch | — | 10 |

**Summe pro Box: ~214 €**

## 1.2 Gemeinsam / einmalig

| Posten | ca. € |
|---|---|
| NTAG215 Karten, 50 Stk. | 20 |
| Dual-Ladestation (Netzteil 5 V/4 A, Buchse, Druckteil) | 22 |
| Load-Switch + Reed-Kontakt je Ladeplatz | 8 |
| NFC-Leser beide Boxen: 2× PN5180 + 2× ESP32-S3 SuperMini (bestellt 12.10.) | 26 |
| Reserveteile (Pi 3A+, SD, PN5180, ESP32-S3, MAX98357A) | 55 |
| Verbrauchsmaterial (Lötzinn, Flussmittel, Kleber) | 15 |

## 1.3 Gesamt

| Posten | ca. € |
|---|---|
| 2× Box | 428 |
| Gemeinsam | 146 |
| **Gesamtprojekt** | **~575** |

Es bleibt bei ~575 €: Die NFC-Leser (PN5180 + ESP32-S3) sind für beide Boxen
schon da und ersetzen den RC522, je Box kommt nur ein USB-Kabel dazu.

## 1.4 Begründungen

**PiSugar 3 Plus statt PiSugar 3.** Die Zero-Variante hat 1200 mAh: ~4,4 Wh,
nach Wandlerverlusten ~3,8 Wh. Bei ~1,2 W im Betrieb sind das ~3 h. Der 3 Plus
mit 5000 mAh liefert ~15 Wh nutzbar, also 10 h und mehr. Seit 3.2 sitzt er mit
allen vier Löchern auf dem Pi 3A+.

**Pi 3 Model A+ statt Pi Zero 2 W.** Die Zero 2 W ist wegen eines Engpasses bei
Chip-Substraten bis auf Weiteres ausverkauft. Der 3A+ nutzt dieselbe
Chipfamilie, Raspberry Pi OS, Phoniebox, Overlays und Pinbelegung bleiben
gleich. Er braucht im Leerlauf etwa doppelt so viel Strom und kostet ~31 €
statt ~21 €. Kommt die Zero 2 W zurück, läuft dasselbe SD-Image darauf.

**PN5180 als Leser (statt RC522/PN532).** Einziger der drei, der ISO 15693 und
damit echte Tonies liest, und er liest die NTAG215-Karten mit. Er hängt über
einen ESP32-S3 am USB und meldet sich als Tastatur, V3 braucht dafür kein
eigenes Plugin. Reichweite durch den Deckel ≤ ~2 mm über der Antenne anpeilen.

**APA102 statt WS2812.** WS2812 brauchen exaktes Timing über PWM, PCM oder SPI.
PWM und PCM kollidieren mit I²S. APA102 laufen per Bit-Bang auf beliebigen
GPIOs. **Nicht auf SPI0** — APA102 ignorieren Chip-Select und würden jede
NFC-Abfrage als LED-Daten lesen.

**Load-Switch im Dock, Ideal-Diode in der Box.** Beide Seiten der Ladekontakte
sind nur dann spannungsführend, wenn die Box tatsächlich aufsitzt.

**Kein DIY-Laderegler.** Spart ~45 €, kostet aber sauberes Herunterfahren, RTC
und Akkustand.

**Mono ist Absicht.** Ein Würfel im Raum profitiert nicht von Stereo. Durch das
SD_MODE-Verhalten des Treibers ist Mono-Downmix ohnehin Pflicht.

**Kopfhörer über einen zweiten DAC.** Der PCM5102A hängt parallel an denselben
I²S-Leitungen wie der Verstärker, beide empfangen dasselbe Signal. Der
Schaltkontakt der Buchse schaltet den Lautsprecher in Hardware stumm und meldet
„Stecker drin" an einen GPIO. Weil die Lautstärke für beide Ausgänge dieselbe
digitale Größe ist, wird doppelt begrenzt: ein Widerstandsteiler an der Buchse
als fester Hardware-Deckel, darunter ein eigenes Software-Limit. Hält das
Plugin nicht, bleibt der Deckel. Ob der PCM5102A 32-Ω-Kopfhörer sauber treibt,
wird am Breadboard geprüft (3.2.6).

## 1.5 Laufzeit

| Zustand | Leistung | Laufzeit (5000 mAh) |
|---|---|---|
| Wiedergabe, mittlere Lautstärke | ~1,6–1,9 W | ~8–9 h |
| Leerlauf mit WLAN | ~1,1–1,3 W | ~11–13 h |
| Aus (PiSugar-Ruhestrom) | gering | Wochen |

Auto-Shutdown nach ~20 min Inaktivität bleibt Pflicht — eine über Nacht
laufende Box ist morgens leer. Werte gelten für den Pi 3A+ und sind Schätzungen,
3.1.3 misst sie. Den Prozessor herunterzutakten bringt etwas zurück. Mit dem
PN5180-Weg kommen ~0,1–0,2 W dazu, also 30–60 min weniger.

---

# Teil 2 — Pinbelegung (Entwurf)

Am Breadboard verifizieren, bevor gelötet wird (3.1.4).

| Funktion | GPIO | Pin |
|---|---|---|
| PiSugar 5 V / GND (Pogo von unten) | — | 2, 4, 6, 9 |
| PiSugar I²C SDA | 2 | 3 |
| PiSugar I²C SCL | 3 | 5 |
| Verstärker SD_MODE (Overlay-Default) | 4 | 7 |
| Taste Vor | 5 | 29 |
| Taste Zurück | 6 | 31 |
| RC522 SDA/CS (SPI0 CE0) | 8 | 24 |
| RC522 MISO | 9 | 21 |
| RC522 MOSI | 10 | 19 |
| RC522 SCK | 11 | 23 |
| UART TX / RX — Debug, frei halten | 14 / 15 | 8 / 10 |
| Encoder A | 17 | 11 |
| I²S BCLK | 18 | 12 |
| I²S LRCLK | 19 | 35 |
| I²S DOUT | 21 | 40 |
| Encoder Taster | 22 | 15 |
| APA102 Daten (über 74AHCT125) | 23 | 16 |
| APA102 Takt (über 74AHCT125) | 24 | 18 |
| RC522 RST | 25 | 22 |
| Kopfhörer: Stecker erkannt | 26 | 37 |
| Encoder B | 27 | 13 |
| Hauptknopf | — | am PiSugar-Taster, nicht am Pi |

Der PCM5102A hängt parallel an GPIO 18 / 19 / 21.
Frei: GPIO 7, 12, 13, 16. GPIO 20 (I²S DIN) bewusst ungenutzt lassen.
Entschieden: Der Leser (PN5180) hängt am USB. Die oben gelisteten RC522-SPI-Pins entfallen und bleiben frei.

---

# Teil 3 — Software-Aufteilung

| Funktion | Quelle |
|---|---|
| Karte auflegen → Ordner spielt, Abheben → Pause | V3, Konfiguration |
| Karten anlernen über Web-UI | V3 |
| Vor / Zurück / Lautstärke-Encoder | V3, GPIO-Konfiguration |
| Max- und Startlautstärke | V3, Konfiguration |
| Idle-Shutdown | V3, Konfiguration |
| Gute-Nacht-Karte (Timer mit Ausblenden) | V3, Konfiguration |
| MQTT an Home Assistant | V3, Konfiguration |
| **Resume nach Toniebox-Logik + 10-s-Karenz** | Plugin |
| **LED-Ring APA102** | Plugin |
| **PiSugar: Akkustand, Tastenereignisse, Shutdown** | Plugin + pisugar-server |
| **Leise-Zeiten** | Plugin |
| **Kopfhörer-Limit bei eingestecktem Stecker** | Plugin + Hardware-Deckel |
| Tonie-Figuren erkennen | PN5180 an ESP32-S3, in V3 als USB-Leser (gesetzt) |
| **Figuren zuordnen per Handy (Weg A und B)** | Plugin + eigene Handy-Seite |
| Medien-Sync vom Server | rsync, systemd-Timer |
| Uhrzeit offline | pisugar-server (`rtc_rtc2pi`) |
| Pop-Unterdrückung | Kernel-Overlay `max98357a` |

---

# Teil 4 — Projektstrukturplan

▲ = kritischer Pfad · **NEU** = seit Rev. 2 hinzugekommen

## 1 Projektsteuerung

- **1.1 Plan & Meilensteine**
  - 1.1.1 Phasenplan mit Abnahmekriterien
  - 1.1.2 Meilensteine: Muster verifiziert / Box 1 abgenommen / Box 2 fertig
- **1.2 Beschaffung**
  - 1.2.1 Charge 1: nur Muster für den kritischen Pfad (PN5180 + ESP32-S3, PiSugar 3 Plus, Pi 3A+, LED-Ring)
  - 1.2.2 Charge 2: Rest Box 1 + Reserve
  - 1.2.3 Charge 3: Box 2 — Akku erst kurz vor dem Bau **NEU**
  - 1.2.4 Wareneingang & Bauteilprüfung
- **1.3 Dokumentation**
  - 1.3.1 Schaltplan & Pinbelegung
  - 1.3.2 Aufbauanleitung mit Fotos
  - 1.3.3 Wartungsanleitung
- **1.4 Risikoliste & offene Entscheidungen**

## 2 Anforderungen & Konzept

- **2.1 Feature-Freeze**
- **2.2 Bedienkonzept Kind**
  - 2.2.1 Tastenbelegung inkl. PiSugar-Ereignisse (einfach / lang)
  - 2.2.2 LED-Sprache: Farben und Muster
  - 2.2.3 Audio-Feedback: Start, Fehler, unbekannte Karte, Akku leer
  - 2.2.4 Aufwachsound
- **2.3 Datenmodell** ▲
  - 2.3.1 Kartenmapping im V3-Format, für beide Boxen identisch
  - 2.3.2 Resume-Zustand nach Toniebox-Logik
  - 2.3.3 Profil & Limits je Box
- **2.4 Identität je Kind** — Farbe, Name, Startsound
- **2.5 Kindersicherheit** **NEU**
  - 2.5.1 Kleinteile und Magnete unzugänglich
  - 2.5.2 Akku mechanisch geschützt
  - 2.5.3 Gehäuse nur mit Werkzeug zu öffnen

## 3 Hardware

- **3.1 Bauteilverifikation** ▲
  - 3.1.1 Pi 3A+ auf dem PiSugar 3 Plus: Start vom Akku, I²C-Verbindung **NEU**
  - 3.1.2 Leser-Reichweite (PN5180) durch Materialstärke, bestimmt die Deckelstärke
  - 3.1.3 Laufzeit unter Nutzung und Leerlauf messen, bei Bedarf heruntertakten
  - 3.1.4 Pinbelegung final (Entwurf Teil 2)
  - 3.1.5 Tonie-Test: PN5180 + ESP32-S3, Privacy-Modus, Reichweite 2,5 cm **NEU**
- **3.2 Breadboard-Aufbau**
  - 3.2.1 Audiokette mit Overlay `max98357a`, Boot-Pop prüfen
  - 3.2.2 Leser: PN5180 + ESP32-S3 am USB
  - 3.2.3 Taster, Encoder, APA102 über Pegelwandler
  - 3.2.4 Hauptknopf parallel zum PiSugar-Taster; Lötpunkte, Ereignisse kurz/lang und Soft-Poweroff am Muster klären **NEU**
  - 3.2.5 Power-Path: Pololu-Modul, Pogo und USB-C auf getrennte Eingänge **NEU**
  - 3.2.6 Kopfhörerpfad: PCM5102A passiv ohne Overlay (SCK auf GND), SD_MODE über 1 kΩ, Pegel-Deckel **NEU**
- **3.3 Verdrahtungsplan & Kabelbaum** — inkl. Pufferelko am Verstärker
- **3.4 Löten & Endmontage**
- **3.5 Ladekontakte & Dock**
  - 3.5.1 Verpolschutz
  - 3.5.2 Load-Switch mit Reed-Erkennung
  - 3.5.3 Kontakte 3–4 mm versenkt
  - 3.5.4 Kurzschlusstest mit Münze und Löffel — an Dock **und** Box
- **3.6 Laden unterwegs: USB-C nach außen** **NEU**

## 4 Gehäuse & Mechanik

- **4.1 Maßkonzept**
  - 4.1.1 Innenraumaufteilung
  - 4.1.2 Mindestabstand Metall ↔ NFC-Antenne **NEU**
- **4.2 CAD-Konstruktion**
  - 4.2.1 Unterteil mit Träger: Pi 3A+ auf PiSugar 3 Plus
  - 4.2.2 Oberteil mit Kartenfeld
  - 4.2.3 Lautsprechergitter
  - 4.2.4 Bedienfeld
  - 4.2.5 LED-Diffusor
  - 4.2.6 Trennwand Audio- / Elektronikkammer
  - 4.2.7 USB-C-Durchführung mit TPU-Lasche **NEU**
  - 4.2.8 Klinkenbuchse versenkt, geschützt vor Krümeln **NEU**
  - 4.2.9 Bei Tonie-Unterstützung: Magnet oder Stahlscheibe für die Figuren **NEU**
- **4.3 Druck & Iterationen**
  - 4.3.1 Passung Gewindeeinsätze
  - 4.3.2 Sturztest mit TPU-Ecken
- **4.4 Dual-Ladestation**
- **4.5 Audiokammer abdichten**
  - 4.5.1 Volumen 0,5–0,8 l festlegen
  - 4.5.2 Treiber mit Dichtband
  - 4.5.3 Kabeldurchführung verkleben
  - 4.5.4 Dämmung & Klangprobe
- **4.6 Wärmeabfuhr Elektronikkammer**
  - 4.6.1 Kühlkörper auf dem Pi
  - 4.6.2 Konvektionsspalte an Tastern
  - 4.6.3 Temperatur unter Last messen
- **4.7 Kleinteile sichern** **NEU**
  - 4.7.1 Magnete verkapselt und eingeklebt
  - 4.7.2 Encoderknopf verschraubt, Kappen eingeklebt

## 5 Software Box — Phoniebox V3 + Plugins

- **5.1 Basissystem**
  - 5.1.1 Pi OS Legacy 32-bit Lite + Phoniebox V3 stable
  - 5.1.2 WLAN, SSH, Hostname je Box
  - 5.1.3 Warten auf Netzwerk beim Boot deaktivieren **NEU**
  - 5.1.4 Uhrzeit: RTC beim Boot, NTP bei Netz **NEU**
  - 5.1.5 Schreiblast: Logs auf tmpfs, noatime, kein Swap
- **5.2 Audio**
  - 5.2.1 Overlay `max98357a` mit SD_MODE-Steuerung
  - 5.2.2 Downmix auf Mono **NEU**
  - 5.2.3 Max- und Startlautstärke
  - 5.2.4 ReplayGain
  - 5.2.5 Kopfhörer-Limit bei eingestecktem Stecker **NEU**
- **5.3 NFC**
  - 5.3.1 Leser in V3 einrichten (PN5180 als USB-Leser)
  - 5.3.2 Place-not-Swipe mit Pause beim Abheben
  - 5.3.3 Admin-Karten (Hotspot, Akkustand) **NEU**
  - 5.3.4 Tonie-Kennungen wie Karten anlernen **NEU**
  - 5.3.5 Abheben über USB-Leser: Wiederholung alle 500 ms, Abhebe-Code auf „Pause" **NEU**
- **5.4 Plugin Resume** ▲
  - 5.4.1 Eine Position, gebunden an die zuletzt gespielte Karte
  - 5.4.2 Verwerfen bei Kartenwechsel
  - 5.4.3 Karenzzeit ~10 s beim Abheben
  - 5.4.4 Atomar schreiben, übersteht Neustart
- **5.5 Plugin LED-Ring**
  - 5.5.1 APA102-Treiber per Bit-Bang
  - 5.5.2 Zustände: läuft, Pause, Akku, unbekannte Karte, Aufwachen
  - 5.5.3 Helligkeitsdeckel fest ~25 % (40 LEDs)
- **5.6 Plugin PiSugar & Energie**
  - 5.6.1 Akkustand an V3 und LED-Ring
  - 5.6.2 Tastenereignisse → Phoniebox-RPC
  - 5.6.3 Idle-Shutdown nach ~20 min (V3)
  - 5.6.4 Shutdown bei Tiefstand
  - 5.6.5 Auto-Power-On aus, Anti-Mistouch aus **NEU**
  - 5.6.6 WLAN-Powersave messen und entscheiden
  - 5.6.7 Auto-Hotspot aus, per Admin-Karte an **NEU**
- **5.7 Plugin Leise-Zeiten**
- **5.8 Gute-Nacht-Karte** — V3-Timer mit Ausblenden
- **5.9 HA-Anbindung**
  - 5.9.1 MQTT aus V3
  - 5.9.2 Status und Protokoll offline puffern **NEU**
- **5.10 Plugin Figuren-Zuordnung** **NEU 3.5**
  - 5.10.1 Unbekannte Kennung → Überraschungs-Ordner + Meldung „neue Figur"
  - 5.10.2 Handy-Seite: Serienliste, Zuordnen mit einem Tipp (Weg A)
  - 5.10.3 Lernmodus „Jetzt kommt ein neuer Tonie", 2 min, auch Umbelegen (Weg B)
  - 5.10.4 Serie → nächste ungehörte Folge, Zusammenspiel mit Resume
  - 5.10.5 LED-Zustände „neue Figur" und „Lernmodus"
  - 5.10.6 Zuordnungen speichern und an 6.3 übergeben

## 6 Verwaltung & Sync

- **6.1 V3-Web-UI** — Karten anlernen, Wiedergabe
- **6.2 Medien-Sync vom Server**
  - 6.2.1 rsync nur im Heim-WLAN
  - 6.2.2 Bibliotheks-Scan nach dem Sync statt bei jedem Boot
- **6.3 Kartenmapping zwischen beiden Boxen abgleichen** — inkl. Figuren-Zuordnungen aus 5.10
- **6.4 Hörprotokoll & Statistik** — in HA
- **6.5 Backup** — SD-Image + Konfiguration
- **6.6 Zugriffsschutz** — nur lokales Netz

## 7 Inhalte & Karten

- **7.1 Bibliothek aufbauen, sortieren**
- **7.2 Lautheitsangleich über alle Titel**
- **7.3 Kartendesign**
  - 7.3.1 Motive & Bebilderung
  - 7.3.2 Druck & Laminierung
  - 7.3.3 Haltbarkeit: Speichel, Biegung, Sonne
- **7.4 Sonderkarten**
  - 7.4.1 Shuffle, Gute Nacht
  - 7.4.2 Oma-Karte über Sync-Ordner
  - 7.4.3 Admin-Karten für Eltern **NEU**
- **7.5 Kartenaufbewahrung**

## 8 Integration & Test

- **8.1 Funktionstest gegen die Anforderungsliste**
- **8.2 Energie**
  - 8.2.1 Dauertest unter Nutzung, Ziel 8 h
  - 8.2.2 Leerlauf und Auto-Shutdown
  - 8.2.3 Zeit vom Knopfdruck bis zum ersten Ton
  - 8.2.4 Andocken weckt die Box nicht **NEU**
- **8.3 Kindertauglichkeit**
  - 8.3.1 Sturztest
  - 8.3.2 Flüssigkeiten & Krümel
  - 8.3.3 Lautstärke in dB
  - 8.3.4 Ladekontakte kurzschlussfest
  - 8.3.5 Zugtest an Knopf und Kappen **NEU**
  - 8.3.6 Kopfhörerpegel in dB, auch bei abgestürztem Plugin **NEU**
- **8.4 Fehlerfälle**
  - 8.4.1 Unterwegs ohne WLAN: Start, Wiedergabe, Uhrzeit
  - 8.4.2 Stromverlust beim Schreiben
  - 8.4.3 Unbekannte oder defekte Karte
  - 8.4.4 LED-Flackern bei NFC-Abfrage
  - 8.4.5 Laden über USB-C und Pogo gleichzeitig **NEU**
  - 8.4.6 Lernmodus: Kind legt währenddessen eigene Figur auf, Zeitablauf, Abbruch **NEU 3.5**
- **8.5 Abnahme Box 1**

## 9 Serie & Betrieb

- **9.1 Box 2 bauen** — mit Erkenntnissen aus Box 1
- **9.2 Image klonen, individualisieren**
- **9.3 Einführung bei den Kindern**
- **9.4 Wartung**
  - 9.4.1 SD-Backup
  - 9.4.2 Akkutausch
  - 9.4.3 Phoniebox-Updates gegen eigene Plugins testen **NEU**
- **9.5 Ersatzteillager**

---

## Kritischer Pfad

1. **3.1.5 Tonie-Test** — Leser ist entschieden (PN5180). Offen bleibt die
   Reichweite durch den Deckel (Test 5/5b/6) und der Strom (Test 7); sie
   bestimmen Deckelstärke und Laufzeit. Läuft parallel zu 3.1.1 und 3.1.3.
2. **3.1.3 Laufzeit** — mit dem Pi 3A+ wird das 8-h-Ziel knapp. Reicht es nicht:
   heruntertakten, sonst für Box 2 auf die Zero 2 W warten.
3. **3.1.2 Leser-Reichweite** — bestimmt die Wandstärke im Kartenfeld.
4. **3.1.4 Pinbelegung** — vor dem Löten kollisionsfrei festlegen.
5. **2.3 / 5.4 Resume-Datenmodell** — das größte eigene Software-Stück.

CAD (4.2) startet erst, wenn 3.2 auf dem Breadboard läuft.

## Entscheidungen (12.10.2026, ergänzt 17.10. und 04.11.)

| Frage | Entscheidung |
|---|---|
| Kopfhörer | Klinkenbuchse mit zweitem DAC |
| Einschalten | Ein Druck, Anti-Mistouch aus |
| Read-only Root | Zurückgestellt, erst bei Problemen |
| Ohne bekanntes WLAN | Kein Hotspot, per Admin-Karte einschaltbar |
| Tonie-Figuren | Pflicht. PN5180 gesetzt (04.11.), RC522 entfällt |
| Abheben am USB-Leser | Firmware wiederholt die Kennung, Abhebe-Code → Pause |
| Zweiter DAC | Passiv am I²S, kein eigenes Overlay |
| Neue Figuren zuordnen (04.11.) | Einmal pro Exemplar per Handy, Weg A und B, keine automatische Erkennung |

## Bewusst nicht enthalten

Mikrofon · Sync zwischen zwei Boxen · TV-Steuerung (eigenes Projekt) ·
Streaming-Dienste (in V3 ohnehin noch nicht vorhanden)
