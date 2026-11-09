# Zeitmessung: Auflegen und Abheben bis zum Ton

Stand: 06.11.2026 (AP 1.6, Stufe 1). Hier steht, wie die Zeitgrenzen aus Ziel 2
gemessen werden, welche Werte sie haben dürfen und was gemessen wurde.
Die Rechnung steht im Design (`docs/designs/box-software.md`, Baustein 1,
„Zeitbudget“). Die Ergebnisse am Mac trägt Tobias in Abschnitt 5 ein.

**Grenzen:** Auflegen bis zum ersten Ton **unter 1,0 s**. Abheben bis zur Pause
**unter 1,5 s**. Lücken bis 1,0 s führen zu **keiner** Pause.

Die Grenze gilt für einen **bekannten Tobie**, bei dem kein Ton kommt. Seit Entscheidung L (09.11.) startet
das Hörspiel nach einem Ton erst, wenn der Ton zu Ende ist (unbekannter Tobie, Lernmodus-Ende, Status-Karte); dort
gehört die Dauer des Tons nicht zur Messung. Beim bekannten Tobie ändert sich nichts.

## 1. Was gemessen wird

Gemessen wird am **Ausgang**: Mikrofon vor dem Lautsprecher. Das Ereignisprotokoll
allein misst nur den `play`-Befehl, nicht den Ton.

| Messpunkt | Quelle |
|---|---|
| Tobie berührt das Gehäuse (Klack beim Aufsetzen) | Aufnahme (nur mit `--klick`) |
| `aufgelegt` (die Zeile `PLACED` oder `LOCKED` ist im Dienst) | Protokoll, Baustein `reader` |
| `abspielen` (Befehl `Abspielen` geht an MPD) | Protokoll, Baustein `app` |
| erster Ton über der Schwelle | Aufnahme |
| `abgehoben` (Zeile `REMOVED` ist im Dienst) | Protokoll, Baustein `reader` |
| `pausieren` (Befehl geht an MPD) | Protokoll, Baustein `app` |
| Ton aus (Stille von 150 ms beginnt) | Aufnahme |

Die Protokollzeilen `aufgelegt`, `entprellt`, `abgehoben`, `abspielen`,
`abspielen_fertig`, `pausieren` und `pausieren_fertig` stehen auf Ebene INFO und
tragen die Vorgangs-ID. `abspielen_fertig` und `pausieren_fertig` haben im Feld
`dauer_ms`, wie lange MPD für den Befehl brauchte.

Die Uhr der Protokollzeilen und der Aufnahme ist beim Mac dieselbe Wanduhr. Die
Abstände zwischen zwei Protokollzeilen rechnet das Werkzeug mit der monotonen
Uhr (Feld `mono`), sie springt nie.

**Abheben** hat einen Anteil, den das Protokoll nicht sieht: Die Firmware meldet
`REMOVED` erst `REMOVE_AFTER_MS` = 1100 ms nach der letzten gültigen Lesung, am Ende
des nächsten Zyklus (bis 200 ms). Das Werkzeug misst ab `abgehoben`. Die Summe ist

    Abheben gesamt = 1100 ms + bis 200 ms (Zyklus) + Messwert „abgehoben → Ton aus“

## 2. Messen am Mac

**Vorbereitung (einmal)**

```
brew install sox
mkdir -p ~/Tobi_box/box/medien-sprache/messung
sox -n -r 44100 -c 1 ~/Tobi_box/box/medien-sprache/messung/dauerton.wav synth 60 sine 440 vol 0.5
```

Der Dauerton ist die Folge für die Messung: Hörspiele haben Pausen, die das
Werkzeug sonst als „Ton aus“ liest. Die vollständige Serie `messung` (Ordner, `serie.json`, Eintrag in
`config.json`) steht in `docs/betrieb/mac-prototyp.md`, Abschnitt 11.7. Ordne ihr zwei Tobies zu: eine NTAG-Karte und einen Tonie. Eine zweite Zuordnung
auf die Überraschungs-Serie ist nicht nötig: Der gesperrte Tonie spielt sie von selbst.
Die Ebene `ebene = "INFO"` ist in `tobibox.mac.example.toml` schon gesetzt.
Der Mac soll still sein. Das Mikrofon steht 10 bis 20 cm vor dem Lautsprecher
(Mac-Lautsprecher oder externer), die Systemlautstärke bleibt während der Messung gleich.

**Ablauf**

1. MPD starten (Schritt 4 in `docs/betrieb/mac-prototyp.md`), das alte Protokoll
   wegräumen: `mv box/var/log/tobibox.log* /tmp/` (sonst stehen alte Läufe in der Auswertung).
2. Aufnahme starten und **still sein**: `rec -r 44100 -c 1 ~/aufnahme.wav`
   (oder QuickTime „Neue Audioaufnahme“, dann später
   `afconvert -f WAVE -d LEI16 aufnahme.m4a aufnahme.wav`).
3. **Danach** den Dienst starten (`tobiboxd --config …`). Sein Startgeräusch ist die
   Marke, mit der Protokoll und Aufnahme zusammenpassen (`--sync-start`).
4. Je Tobie mindestens 20 Mal: aufsetzen **mit hörbarem Klack** (nicht sanft ablegen),
   etwa 3 s spielen lassen, abheben, 3 s warten. Danach dasselbe mit dem
   gesperrten Tonie (am besten beim ersten Auflegen, solange er noch gesperrt ist).
5. Aufnahme mit `Ctrl+C` beenden, Dienst beenden.
6. Auswerten (im Repo-Ordner, Python-Umgebung aktiv):

```
python box/tools/measure_audio_latency.py box/var/log/tobibox.log* \
    --wav ~/aufnahme.wav --sync-start --klick
```

Andere Wege, Protokoll und Aufnahme abzugleichen (`--wav-start`, `--wav-ende`,
`--sync ZEIT=SEKUNDEN`, `--wav-start auto`): `--help`. Der Fehler des
Abgleichs beträgt etwa 0,1 s (`--sync-start`) bis 0,2 s (`--wav-start auto`);
er verschiebt alle Werte gemeinsam. Dessen Größe sieht man an den Abheben-Werten, die nie
negativ sein dürfen. `--json` gibt das Ergebnis maschinenlesbar aus; der Status ist
3, wenn ein Wert über der Grenze liegt.

**Ausgabe je Vorgang.** Beim Auflegen: `Befehl` (Millisekunden von `aufgelegt` bis
`abspielen`), `Ton` (von `aufgelegt` bis zum ersten Ton), `Klack` (vom Klack bis
`aufgelegt`, das ist der Anteil der Firmware) und `Gesamt` (vom Klack bis zum ersten Ton).
Beim Abheben: `Befehl` bis `pausieren`, `Ton` bis „Ton aus“.
Die Spalte `Gesamt` ist die Zahl für Ziel 2.

**Zeiten der Firmware einzeln.** Der Klack zeigt nur die Summe aus Warten auf den
Zyklus, erster Lesung, Entprellen und Übertragung. Die Teile:

- *Erste Lesung:* `cycle_ms` in der `HB`-Zeile (Serial-Monitor,
  `pio device monitor -b 115200`, Dienst vorher beenden), während der Tobie liegt.
  Erwartet: NTAG-Karte etwa 176 ms, offener Tonie etwa 58 ms.
- *Entsperren (Tonie):* Differenz des Klack-Medians eines noch gesperrten Tonies
  (erstes Auflegen) zum Klack-Median eines offenen Tonies. Erwartet etwa 79 ms
  (137 ms gesperrt minus 58 ms offen). Ein Tonie bleibt nach dem Entsperren offen;
  es gibt also nur wenige Messungen.
- *Warten auf den Zyklus:* Streuung der Klack-Werte (Maximum minus Minimum) bei einer
  NTAG-Karte. Sie liegt unter dem Zyklus von 200 ms.
- *Entprellen:* fest ein Zyklus (`CONFIRM_READS` = 2, also die zweite Lesung 200 ms
  nach der ersten); keine eigene Messung. Nur ein **Wechsel** bei liegendem Tobie
  braucht drei Lesungen (`CHANGE_CONFIRM_READS` = 3, also 400 ms nach der ersten);
  das gehört nicht zur Auflegezeit. Zeigt Klack mehr als die Summe aus
  Streuung, Lesung und 200 ms, steht hier der Grund.
- *Übertragung:* USB-CDC am Mac; der Wert steckt im Klack. Im Container: Abschnitt 4.

**Lücken (CUJ 8).** Spielt ein Tobie, Tobie 10 Mal für etwa 0,8 s und 10 Mal für 1,0 s
abheben und sofort wieder auflegen. Im Protokoll darf keine Zeile `abgehoben`
stehen (`grep '"ereignis":"abgehoben"' box/var/log/tobibox.log`), und es darf keine
Pause entstehen. Ein Wert über 1,0 s ist kein Fehler: Dann kommt `REMOVED` nach 1,1 s
zu Recht.

**Selten, aber merken:** Einzelne Befehle des PN5180 können im Fehlerfall bis 500 ms
blockieren (`setRF_on`). Die `HB`-Zeile zeigt das in `cycle_ms`. Steht dort öfter
mehr als 200, in die Spalte „Bemerkung“ eintragen, wie oft.

## 3. Soll-Werte (Zeitbudget aus dem Design)

Zyklus 200 ms, Messwerte aus `docs/plan/uebergabe.md`. Auflegen einer NTAG-Karte im
schlechtesten Fall:

| Schritt | Soll (höchstens) |
|---|---|
| Warten auf den Zyklus | 200 ms |
| Erste Lesung (Arbeit im Zyklus) | 176 ms |
| Entprellen: zweite Lesung, ein weiterer Zyklus | 200 ms |
| Übertragung der Zeile | 10 ms |
| Dienst: Zuordnung, Zeiger laden, Befehl | 50 ms |
| MPD: Start, `seek` und Ausgabepuffer, bis zum Ton | 300 ms |
| **Summe** | **936 ms, Grenze 1000 ms** |

Auflegen eines Tonies: gleiche Rechnung mit 137 ms (gesperrt, die Entsperrzeit steckt
darin) bzw. 58 ms (offen) statt 176 ms.

Abheben:

| Schritt | Soll (höchstens) |
|---|---|
| Lücke bis `REMOVED` (`REMOVE_AFTER_MS`) | 1100 ms |
| Warten bis zum Ende des Zyklus | 200 ms |
| Übertragung der Zeile | 10 ms |
| Pausenbefehl bis Ton aus | 100 ms |
| **Summe** | **1410 ms, Grenze 1500 ms (Reserve etwa 90 ms)** |

Lücken: Aussetzer bis 1,0 s liegen unter der Schwelle von 1,1 s und führen zu keinem
`REMOVED`.

MPD-Puffer (feste Startwerte): `audio_buffer_size` 1024 KiB, `buffer_before_play`
nicht gesetzt (MPD-Vorgabe, die Option ist in MPD 0.23 veraltet), ALSA-`buffer_time` 100000 µs. Die Messung justiert sie.

## 4. Werte ohne Hardware (Container)

Gemessen mit `box/tools/measure_service_latency.py --n 20` am 06.11.2026: echte `App`,
echtes MPD (Null-Ausgabe) und `fake_reader` am Pseudo-Terminal, im Container
dieser Entwicklungsumgebung, ohne Last. **Das sind Container-Werte**, keine Werte vom Mac
oder Pi: Es gibt keinen USB, keine PN5180 und keinen Ton. Sie zeigen nur, dass der Dienst
selbst sein Budget (50 ms) um ein Vielfaches unterschreitet. MPD wird bis `state: play`
abgefragt (alle 5 ms), die Auflösung ist also etwa 5 ms.

| Schritt | min | Median | max |
|---|---|---|---|
| Zeile geschrieben → `aufgelegt` im Protokoll (Pseudo-Terminal, Lesen, Prüfen) | 0,4 ms | 0,6 ms | 1,3 ms |
| `aufgelegt` → `abspielen` (Zuordnung, Zeiger laden, Befehl) | 0,9 ms | 1,1 ms | 2,1 ms |
| `abspielen` → MPD `play` (Befehl ausführen, 1 Titel laden, `seek`, Start) | 4,1 ms | 5,5 ms | 6,3 ms |
| **Zeile geschrieben → MPD `play` (Summe)** | 5,8 ms | 7,3 ms | 8,3 ms |
| Zeile geschrieben → `abgehoben` | 0,4 ms | 0,5 ms | 1,0 ms |
| `abgehoben` → `pausieren` (Befehl) | 0,5 ms | 0,8 ms | 1,3 ms |
| `pausieren` → MPD `pause` | 4,4 ms | 6,1 ms | 6,8 ms |
| **Zeile geschrieben → MPD `pause` (Summe)** | 5,8 ms | 7,4 ms | 8,4 ms |

Auf dem Pi (3A+, unter Sync-Last) werden diese Werte größer. Das prüft der Pi-Probelauf.

## 5. Ergebnisse am Mac (Tobias trägt ein)

Eine Zeile je Schritt, ein Wert je Schritt (Median und Höchstwert über mindestens
20 Vorgänge). Die Spalte „Container“ ist Abschnitt 4 und ersetzt die Messung am Mac nicht.

| Schritt | Soll | Wert am Mac (Median / Höchstwert) | Container (Median / Höchstwert) | Bemerkung |
|---|---|---|---|---|
| Warten auf den Zyklus (Streuung des Klack) | ≤ 200 ms | | – | |
| Erste Lesung (`cycle_ms`, NTAG-Karte) | ≤ 176 ms | | – | |
| Erste Lesung (`cycle_ms`, offener Tonie) | ≤ 58 ms | | – | |
| Entprellen (zweite Lesung) | ≤ 200 ms | | – | |
| Entsperren (Tonie, gesperrt minus offen) | ≤ 79 ms | | – | |
| Übertragung der Zeile (USB-CDC; im Klack enthalten) | < 10 ms | | 0,6 / 1,3 ms (Pseudo-Terminal) | |
| Dienst: `aufgelegt` → `abspielen` | ≤ 50 ms | | 1,1 / 2,1 ms | |
| MPD-Start bis Ton am Ausgang (`abspielen` → Ton) | ≤ 300 ms | | 5,5 / 6,3 ms bis `play` (ohne Ton) | |
| **Auflegen gesamt, NTAG-Karte (Klack → Ton)** | **< 1000 ms** | | – | |
| **Auflegen gesamt, offener Tonie** | **< 1000 ms** | | – | |
| **Auflegen gesamt, gesperrter Tonie** | **< 1000 ms** | | – | |
| Abheben: `abgehoben` → Ton aus | ≤ 100 ms | | 6,1 / 6,8 ms bis `pause` (ohne Ton) | |
| **Abheben gesamt (1100 + Zyklus + Messwert)** | **< 1500 ms** | | – | |
| Lücken 0,8 s und 1,0 s: Pausen in 20 Versuchen | 0 | | – | |
| Zyklen mit mehr als 200 ms (`cycle_ms` in `HB`) | selten | | – | |

Messung am: ______ · Mac-Modell: ______ · Ausgabe (Lautsprecher/Kopfhörer): ______ ·
Version `tobiboxd`: ______ · Firmware (`HELLO fw=`/`build=`): ______

## 6. Wenn eine Grenze überschritten wird

Die Rückfallregel steht im Design (Baustein 1). Ziel 2 wird **nicht** stillschweigend
geändert. Reihenfolge:

1. **Arbeit pro Zyklus senken.** Das zuletzt gelesene Protokoll (14443A oder 15693)
   zuerst abfragen, die Befehlszeitgrenze für RF-Befehle kürzen
   (`PN5180_CMD_TIMEOUT_MS` in `firmware/tobibox-reader/include/timing.h`). Danach neu messen.
2. **Rückfrage an Tobias**, ob 1,2 s beim Auflegen akzeptabel sind. Erst nach seiner
   Entscheidung ändert sich das Ziel (in `docs/plan/` festhalten).

Wo die Zeit stecken kann, wenn die Summe zu groß ist:

| Auffällig | Hinweis | Maßnahme |
|---|---|---|
| `Klack` über 600 ms | Firmware: Zyklus, Lesung oder Entprellen | Rückfallregel 1; `CONFIRM_READS` bleibt 2 (3 würde 200 ms zufügen) |
| `Befehl` über 50 ms | Dienst (Zuordnung, Zeiger laden, Speicherplatte) | Protokoll `abspielen_fertig.dauer_ms` und Platte prüfen |
| `Ton` minus `Befehl` über 300 ms | MPD-Puffer, Ausgabe | `audio_buffer_size` kleiner, `buffer_time` kleiner; wieder messen |
| Abheben über 1,5 s | `REMOVE_AFTER_MS` plus Zyklus plus Pause | Zyklus kürzer (Rückfallregel 1); `REMOVE_AFTER_MS` nur mit Tobias ändern (Lücken-Grenze 1,0 s) |
| Lücken lösen eine Pause aus | Lesungen setzen länger als 1,1 s aus | Anlage und Antenne prüfen (Tobie mittig); `ERR`-Zeilen im Protokoll ansehen |
