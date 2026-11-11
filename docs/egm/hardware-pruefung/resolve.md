# Hardware-Prüfung: Resolve (11.11.)

Grundlage: `review.md` (28 Befunde, Goldfisch-Prüfung mit Fable). Entscheidungen von Tobias mit **(Tobias)**,
Festlegungen der Projektleitung mit **(PL)**.

## Entscheidungen von Tobias

| # | Befund | Entscheidung |
|---|---|---|
| HW1 | H4 Ring beim Hören | **(Tobias)** Beim Start oder Wechsel kurz sichtbar grün, **nach 10 s schwaches Glühen** (ca. 3 %, weiter atmend). Strom am echten Ring trotzdem messen, Laufzeit-Tabelle 1.5 neu rechnen. |
| HW2 | H5, H6 Platine und ESP32-Pins | **(Tobias)** **Kleine Träger-Platine, vom Hersteller bestückt** (Regler, Spannungswächter, Sicherung, PhotoMOS für Pad 10, Lastschalter Ring, Weiche, Teiler, Steckplatz SuperMini und PN5180-Kabel; dazu die Buchsen-Platine des Sockels aus H15). Erst nach den Messungen 1 bis 5 aus `review.md`. Damit sind auch die Unterseiten-Pads der SuperMini sauber erreichbar. |
| HW3 | H16 Tonie-Halt | **(Tobias)** **Magnet im Deckel wie im Original** (Toniebox: Magnete im Deckel und in den Füßen der Figuren). Folge: **Der Hall-Schalter entfällt** (ersetzt R6 aus `docs/egm/ein-aus/resolve.md`); Tonies wecken die ausgeschaltete Box nur noch über NFC-Lauschen (LPCD), Karten ebenso. Test 5b wird auf „Magnet in der Antennenmitte“ umgestellt (stört er Leser und LPCD?). |
| HW4 | H3 Kippen am Sockel | **(Tobias)** **Nur gerades Abheben.** Der Sockel bekommt eine breite, feste Auflage, die Kippen verhindert; der Stecker trägt nie das Hebelmoment. Kragenprobe mit Kippen nach vorn und hinten (20/40/60 N) muss zeigen, dass der Stecker nicht belastet wird. |
| HW5 | H10 Einschalten | **(Tobias)** **Ein kurzer Druck.** Anti-Mistouch aus; der Dienst prüft und setzt die PiSugar-Einstellungen bei jedem Start (sie fallen nach einem Reset zurück). Hauptknopf am Pi-GPIO nur über Teiler. |
| HW6 | H12 Akku am Sockel | **(Tobias)** **Ladegrenze ca. 80 %** (PiSugar-Ladeschutz, Register 0x20 Bit 7, vom Dienst bei jedem Start gesetzt). Temperaturmessung beim Laden im geschlossenen Gehäuse bleibt Pflicht. Laufzeit-Budget unterwegs mit 80 % rechnen. |
| HW7 | H1 Tiefentladung | **(Tobias)** **Ja:** Ein Spannungswächter schaltet den ESP32-Wächter bei ca. 3,2–3,3 V ab (Wiedereinschalten ab ca. 3,5 V). Danach weckt nur noch Strom am Eingang. Sicherung am BAT-Abgriff. |
| HW8 | Abschnitt C, Auto | **(Tobias)** **Beim Start durch Strom spielt ein liegender Tobie nicht.** Startet die Box, weil Strom kommt (Sockel, Kabel, Auto, Powerbank), bleibt sie still bereit, auch mit liegendem Tobie (pausiert, Hauptknopf oder neu auflegen startet). Beim Einschalten per Knopf spielt er sofort (CUJ 20). **Ändert** die Bestätigung vom 11.11. „bei jedem Einschalten“ (Plan 3.20). Schritt 1: Start mit Strom am Eingang gilt als Start durch Strom (S1); ab Schritt 2 liefert der ESP32 den Weckgrund. |
| HW9 | H9, H22 Kopfhörer | **(Tobias)** **Stereo am Kopfhörer.** Der Datenstrom bleibt stereo, der Verstärker mischt selbst (L+R)/2 über den SD_MODE-Widerstand; die Software-Mono-Mischung entfällt. Schaltung (Buchse mit getrennten Schaltkontakten, SD_MODE, Meldung an GPIO 26) im Schaltplan lösen; Kopfhörer-Modell und Pegelmessung folgen. |

## Festlegungen der Projektleitung

| # | Befund | Festlegung |
|---|---|---|
| P-HW1 | H2, H20 `STROM_IN` | Messung Ladeeingang (Pad 8 im Akkubetrieb, Abklingen, Leerlaufspannung, schwache Quellen) gehört ins Tor T1. Entladewiderstand ~10 kΩ und TVS-Diode an der Buchse vorsehen. |
| P-HW2 | H7 Weiche | Schaltung mit einem Signal: Weiche-Chip aus der geschalteten Ring-Schiene versorgen, Vorgabe „Pi“, ESP32 übersteuert nur beim Lauflicht; Freigabe des Ring-Schalters „ESP32 oder Pi-GPIO“, damit der Pi den Leser-Fehler zeigen kann. |
| P-HW3 | H8 Wecken | Durch HW3 entfällt der Hall-Schalter; EXT1 (alle aktiv high) reicht. |
| P-HW4 | H11 5-V-Verteilung | Verstärker, DAC und Ring sternförmig am 5-V-Ausgang des PiSugar, nicht am Pi-Header; ein Massepunkt. M11 erweitern. |
| P-HW5 | H13, H23 | M7 auch im Tiefschlaf; Flash-Weg festschreiben; Firmware-Watchdog an; Reset-Leitung Pi → EN des ESP32 auf der Träger-Platine. |
| P-HW6 | H14, H15 Sockel | Buchsen-Platine von innen mit Schulter; Stecktiefe als eigener Parameter; T0 misst Kontakt bei 0/0,5/1,0/1,5 mm. Ladestations-Entwurf auf Rev. 6 bringen (H26). |
| P-HW7 | H17, H19, H21, H24, H27, H28 | In die gemeinsame Messreihenfolge aus `review.md` übernehmen. |
| P-HW8 | H18, H25 | Plan bereinigen (entfallene Teile, Pinplan Pi, Platzhalter der Beispielkonfig), Ring am Pi auf SPI0 prüfen. |

## Nächste Schritte

1. Plan nachziehen (Rev. 3.21): Entscheidungen HW1–HW9, bereinigte Stückliste, Messreihenfolge.
2. Software sofort: HW1 (Ring beim Hören), HW8 (Start durch Strom), HW5/HW6 (PiSugar-Einstellungen bei jedem Start, Teil der Pi-Anbindung), HW9 (Mono-Mischung in Software abschalten, sobald die Hardware steht).
3. Nach den Messungen 1–5: Schaltplan und Träger-Platine (EGM-Schritt mit Goldfisch-Review).
