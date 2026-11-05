# Tobi Box — Übergabe für neuen Chat

Stand: 05.11.2026 · für Fortsetzung in einem frischen Chat (gerne neuestes Modell)

Dieses Dokument ist selbsttragend: ein neuer Chat kann damit nahtlos weitermachen,
ohne den bisherigen Verlauf zu kennen.

---

## 1. Projekt in einem Satz

NFC-Audiobox im Toniebox-Stil für Tobias' Zwillinge — **zwei baugleiche, mobile
Boxen**, reines Audiogerät (der frühere TV-Teil ist abgetrennt). **Echte
Tonie-Figuren** dienen als Schlüssel für **eigene Hörspiele vom eigenen Server**;
die Original-Tonie-Inhalte sind egal. Auch von Freunden geborgte Figuren sollen
etwas abspielen, damit die Kinder nicht enttäuscht sind.

## 2. Hardware — gesetzt

- **Rechner:** Raspberry Pi 3 Model A+ (die Pi Zero 2 W war ausverkauft; passt
  ohne Umbau auf den PiSugar 3 Plus).
- **NFC-Leser:** **PN5180** für **beide** Boxen. Begründung: echte Tonies nutzen
  ISO 15693 (NXP ICODE SLIX-L), das kann nur der PN5180; er liest zusätzlich die
  eigenen NTAG215-Karten (ISO 14443A). **Der RC522 entfällt endgültig** (kein
  ISO 15693).
- **Leser-Anbindung:** PN5180 → ESP32-S3 SuperMini, der sich am Pi als
  **USB-Tastatur** ausgibt. Phoniebox V3 unterstützt USB-Leser nativ, kein
  eigenes Lese-Plugin nötig. Lib: tueddy/PN5180 (auf ESP32-S3 erprobt, ESPuino).
- **Software-Basis:** Phoniebox V3 + eigene Plugins.
- Weiteres: Akkubetrieb (mobil: Auto, Wohnwagen, unterwegs), Kopfhörer per Klinke,
  Einschalten mit einem Druck, **kein Mikrofon / keine Aufnahme**.

## 3. Tonie-Hardwaretest (Etappe 2) — Stand

Testaufbau am Tisch: PN5180 + ESP32-S3, Sketch `~/Documents/Arduino/tonie_test/`
auf dem Mac. Passwort zum Entsperren der Privacy-Mode-Tonies liegt in `config.h`
auf dem Mac (nicht in geteilten Dokumenten).

**Bestätigt:**
- PN5180 liest NTAG-Karte (~176 ms) und Tonies zuverlässig.
- Privacy-Mode: gesperrter Tonie wird als „irgendein Tonie" erkannt (→
  Überraschungs-Hörspiel). Mit dem Passwort entsperrt → **stabile UID**
  (beginnt mit `E0 04 03`). Einmal entsperrt bleibt er offen, bis eine echte
  Toniebox ihn wieder sperrt (harmlos).
- Lesezeiten: ~176 ms Karte, ~137 ms gesperrter Tonie, ~58 ms offener Tonie.
- **Firmware-Fixes:** doppeltes `RF_ON` entfernt (war fixe 500 ms Verlust) →
  Feld-an von 73 % auf ~53 % gesenkt; `sameCard()` vergleicht per UID → kein
  doppeltes „AUFGELEGT" beim Übergang entsperrt→offen.
- **Test 5 (Durchlesen durch 2 mm): BESTANDEN.** Zentriert 100 % Treffer, 58 ms,
  Feld nur 15,9 % an (2 mm Schaumstoff als PETG-Ersatz, RF-technisch gleichwertig).
- **MagSafe-Gegenprobe:** Tonie durch eine SP-Connect-MagSafe-Hülle → ebenfalls
  **100 % ohne messbaren Verlust**, weil der Magnetring ein freies Zentrum hat
  und die Kopplung durch die Mitte läuft.

**Drei Design-Regeln aus Test 5 (wichtig fürs CAD + Firmware):**
1. **Figur mittig über der Antenne** — der Sweet Spot ist schmal, daneben 0 %.
   CAD: Auflagefläche exakt über die Antennenmitte legen.
2. **Kein Vollmetall / kein Magnet direkt über der Antennenmitte** (killt das
   Feld). Ein **Magnetring mit freiem Zentrum** wäre ok, falls man die Figur
   magnetisch zentrieren will.
3. **UID-Entprellung in der Firmware:** Eine UID erst als Auslöser akzeptieren,
   wenn sie **2–3× identisch** gelesen wurde (CRC prüfen, falls die Lib das Flag
   liefert). Am äußersten Rand kippte einmal ein Byte der UID; zentriert ist sie
   bombenfest. Schützt davor, dass ein Randfehler die falsche Folge startet.

**Noch offen (nächste Tests):**
- **Test 5b:** M8-Stahlscheibe mittig direkt über die Antenne, Tonie drauf →
  erwarteter Einbruch, bestätigt die Metall-Regel. 1 min, `STATISTIK`.
- **Test 6:** Tonie mit Bierdeckeln (~1,5 mm) hochstapeln bis Leseabriss → max.
  Lesedistanz in mm notieren.
- **Test 7:** Stromaufnahme mit USB-Messgerät bei `POLL_INTERVAL_MS` 300/500/1000.
- Ergebnis 5b/6 → **finale Deckelstärke fürs CAD**.

## 4. Figuren einer Geschichte zuordnen — Konsequenz

**Eine automatische Erkennung der Figur ist nicht möglich.** Die Kennung (UID) ist
eine Seriennummer pro Exemplar; welche Figur das ist, steht nicht auf dem Chip,
und es gibt keine nutzbare öffentliche Liste „Kennung → Figur". Deshalb wird jede
Figur **einmal pro Exemplar manuell zugeordnet**, so einfach wie möglich — über
**Plugin 5.10 (Figuren-Zuordnung)**:

- **Weg A — erst auflegen, dann tippen:** Unbekannte Figur auflegen →
  Überraschungs-Ordner spielt sofort, LED zeigt „neue Figur" → auf der Handy-Seite
  die Serie antippen → gespeichert, Box wechselt sofort.
- **Weg B — erst tippen, dann auflegen:** Am Handy „Jetzt kommt ein neuer Tonie"
  + Serie wählen → Box wartet 2 min im Lernmodus → nächste aufgelegte Figur wird
  dieser Serie zugeordnet.
- Serie = Ordner mit Folgen; Resume (Plugin 5.4) gilt wie bei Karten.
  Zuordnungen werden zwischen beiden Boxen abgeglichen. Gesperrter Tonie ohne
  Kennung → immer Überraschungs-Ordner. Unterwegs ohne WLAN gilt Weg A, die
  Zuordnung folgt zu Hause.

## 5. Dokumente (aktueller Stand)

- `tobi-box-stueckliste-und-psp.md` — **Rev 3.7**, Hauptplan: Review, Stückliste,
  Pinplan, Plugins, Testkatalog, kritischer Pfad.
- `tobi-box-psp-baum.html` — **Rev 3.7**, PSP visuell.
- Laufkarte + Bestellliste — als Artefakte gepflegt (Rev 3.6/3.7).
- Firmware-Testsketch — `~/Documents/Arduino/tonie_test/` auf dem Mac (inkl.
  `config.h` mit Passwort).

## 6. Nächste Schritte

1. **Test 5b + 6** durchführen → Deckelstärke festlegen.
2. **Test 7** (Strom) → Laufzeit/Poll-Intervall festzurren.
3. **CAD** mit zentrierter Figuren-Auflage exakt über der Antenne, kein Metall
   in der Feldmitte.
4. **Box 1** nach Plan Rev 3.x aufbauen.
5. **Phoniebox-Plugins** schreiben: Resume (5.4), LED-Ring (5.5), PiSugar,
   Leise-Zeiten, Figuren-Zuordnung (5.10) inkl. **UID-Entprellung**.
