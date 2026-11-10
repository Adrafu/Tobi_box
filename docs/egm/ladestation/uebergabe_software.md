# Übergabe: Box-Software für die Ladestation

Prompt für eine neue Sitzung (Stand 10.11.2026). Zum Einfügen in den neuen
Chat.

---

Du hilfst Tobias bei der Tobi Box: zwei baugleiche, mobile NFC-Audioboxen für
seine Zwillinge (Raspberry Pi 3A+, PiSugar 3 Plus, PN5180 an ESP32-S3, eigene
Box-Software in Python auf MPD, Home Assistant als Oberfläche). Sprich Deutsch,
einfach und direkt.

**Thema dieser Sitzung:** Die Entscheidungen zur Ladestation (Andocken weckt
die Box, eine USB-C-Buchse für Sockel und unterwegs, Software-Entscheidungen
S1–S11) in das Software-Design und die Verträge einarbeiten. Danach setzen
Agents den Code um. Vorgehen nach dem Elephant-Goldfish-Model aus `CLAUDE.md`.
Ordner für die EGM-Dokumente: `docs/egm/start-am-lader/`.

## Wo die Informationen liegen

Alle Dateien liegen auf dem Branch **`claude/ladestation-dock`** (noch nicht
gemergt). Hole ihn zuerst: `git fetch origin claude/ladestation-dock`. Lies
von dort aus, und arbeite auf deinem eigenen Sitzungs-Branch, der von diesem
Branch abzweigt.

Lies in dieser Reihenfolge:

1. `CLAUDE.md`: Rollen (Koordinator schreibt keinen Code, Agents mit dem
   billigsten passenden Modell), EGM-Vorgehen, Regeln. **Verträge in
   `docs/protocol/` und `docs/data-model.md` ändern Agents nicht
   eigenmächtig.** Hier hat Tobias entschieden. Die Änderung läuft als Entwurf
   mit Goldfisch-Review, danach gibt Tobias sie frei.
2. `docs/egm/ladestation/software_folgen.md`: **die Hauptquelle.**
   - Abschnitt 1–6: Analyse (Startgrund, Ablauf, Leise-Zeiten, unterwegs, Wegfall #5398)
   - Abschnitt 7: Tabelle aller betroffenen Stellen (14 Vertragsstellen, 8 in
     `box-software.md`, 5 im Plan)
   - Abschnitt 9: Arbeitspakete
   - **Abschnitt 10: Entscheidungen S1–S11 von Tobias**
3. `docs/egm/ladestation/resolve.md`: Hardware-Entscheidungen, vor allem
   **R8** (Andocken weckt kurz) und **R10** (nur eine USB-C-Buchse im Boden,
   kein Pololu #5398, unterwegs mit gewinkeltem Kabel)
4. `docs/egm/ladestation/design_draft.md` (Rev. 5): Abschnitt 6 (Software,
   Kurzfassung), Abschnitt 7 (Test T5 Wecken und Startschleife)
5. `docs/plan/stueckliste-und-psp.md`:
   - Rev. 3.16 in der Änderungsliste
   - Punkt 3 (überholt durch R8)
   - PSP 5.6.5 und 5.6.8 (neu)
   - Entscheidungstabelle: Zeilen „Ladestation …“, „Eine USB-C-Buchse …“, „Start am Lader, Software …“
6. `docs/designs/box-software.md`: das angenommene Design. Oben steht der
   Hinweis „Ausstehend (10.11.)“.
   - Betroffen: CUJ 10 (Update), CUJ 16 (Leerlauf), CUJ 20 (liegender Tobie beim Start)
   - Tabelle „Strom / Leerlauf“, Netz-Regel (Hotspot), LED-Zustände, Töne, Leise-Zeiten, PiSugar-Wecker
7. Verträge:
   - `docs/protocol/core-interface.md` (`LaderGeaendert`, `SyncStarten(grund="start_lader")`, Zeile `idle.py`, Bedingungen `HaUpdateAnstossen`)
   - `docs/protocol/mqtt-v1.md` (Feld `lader`, Befehle)
   - `docs/protocol/ha-websocket-v1.md` (falls HA-Seite „Update vormerken“ zeigt)
   - `docs/data-model.md` (Töne, Konfiguration)
8. Code `box/src/tobibox/`: `power.py`, `idle.py`, `led.py`, `sounds.py`,
   `quiet.py`, `sync.py`, `syncregel.py`, `app.py` und die Tests in
   `box/tests/`. HA-Integration: `homeassistant/custom_components/tobibox/`.

## Die Entscheidungen in Kürze (Details in `software_folgen.md`, Abschnitt 10)

- **R8:** Andocken weckt die Box. Am PiSugar wird „Einschalten bei Strom am
  Eingang“ aktiviert.
- **R10:** Eine USB-C-Buchse im Boden für Sockel **und** unterwegs. Jede
  Powerbank weckt die Box und gilt als „Lader“.
- **S1:** Jeder Start mit Strom am Eingang gilt als „Start am Lader“. Ohne
  Merker, denn den Startgrund kann die Box nicht sicher erkennen.
- **S2:** Danach kommen Rückmeldung (Ton, Ring mit Ladestand) und Sync-Prüfung,
  dann ein **Kurz-Zähler von 120 s** statt 20 min. Ein laufender Sync hält wach.
- **S3:** Tobie auflegen, Hauptknopf kurz oder ein HA-Befehl beenden den
  Kurz-Modus. Danach gilt die normale 20-min-Regel. Weiter, Zurück und der
  Drehregler beenden ihn nicht.
- **S4:** Ein liegender Tobie spielt beim Start wie bisher (CUJ 20 unverändert).
- **S5:** In den Leise-Zeiten („leiser“ und „stumm“) kein Ton. Der Ring ist
  gedimmt (~5 % bzw. ~3 %), das Lauflicht beim Start ist nachts aus.
- **S6:** **Update vormerken.** HA merkt „Update beim nächsten Andocken“ vor.
  Die Box holt es beim nächsten Start am Lader, wenn die bisherigen
  Bedingungen gelten (daheim, am Lader, spielt nicht). **Dafür ist eine
  Vertragsänderung nötig** (neuer Befehl oder neues Feld).
- **S7:** Der Start-Sync läuft **auch über den Handy-Hotspot**. Die
  Hotspot-Regel bleibt unverändert: Ist ein Lader dran, ist Medien-Sync
  erlaubt. Tobias nimmt mobile Daten im Auto in Kauf.
- **S8:** Dockt die laufende Box an, prüft sie den Sync ebenfalls, einmal je
  Andocken und 10 s entprellt.
- **S9:** Spielt gerade ein Hörspiel, kommt die Rückmeldung nur über den
  Ring, ohne Ton.
- **S10:** Kein Taster im Box-Boden, der Sockel und Kabel unterscheidet.
- **S11:** Ob der Ring schon in den ersten Startsekunden leuchtet
  (Frühstart-Ring), wird erst nach einer Messung am Muster entschieden.

## Bekannte Lücken im Code (aus der Analyse)

- `power.py` fragt den Lader nur alle 10 s ab.
- `Bereit` löst nachts ein helles Lauflicht aus.
- Der Start-Sync kann scheitern, solange das WLAN noch nicht steht
  (`netz_weg`).
- `idle.py` kennt keinen Kurz-Modus.
- `led.py` zeigt den Ladestand bei `LaderGeaendert` bereits an. `idle.py` löst
  `SyncStarten("start_lader")` bereits aus.

## Offen und am Muster zu messen (nicht in dieser Sitzung lösbar)

- **Größtes Risiko:** Gerät die Box am Sockel in eine Startschleife, wenn sie
  herunterfährt, während Strom anliegt? Plan B im Design vorsehen.
- Startzeit des Pi 3A+ bis zur Rückmeldung (für S11).
- Meldet `battery_power_plugged` des pisugar-server an der einzigen Buchse
  weiter `true`?

## Vorgehen

1. Kurzer Stand und Rückfragen an Tobias, nur wenn etwas unklar ist. Die
   Entscheidungen sind gefallen.
2. Entwurf der Änderungen an `box-software.md` und an den Verträgen als
   `docs/egm/start-am-lader/design_draft.md`, mit Markierung „(Start am Lader,
   10.11.)“.
3. Goldfisch-Review durch frische Agents. Report im selben Ordner.
4. Resolve mit Tobias, dann Design und Verträge ändern und in `docs/plan/`
   vermerken.
5. Erst danach setzen Agents den Code um, mit Tests.

Regeln:
- Du bist Koordinator und schreibst keinen Code.
- Nichts bestellen.
- Commits nur auf deinen eigenen Sitzungs-Branch.
- Das Tonie-Passwort nie committen.
