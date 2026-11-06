# Mac-Prototyp: aufsetzen und vorführen

Diese Anleitung richtet den Prototyp der Tobi Box auf einem Mac ein. Du
brauchst dafür keine Vorkenntnisse im Projekt. Die Schritte bauen aufeinander,
bitte in der angegebenen Reihenfolge machen.

**Hinweis:** Ist `tobiboxd` nach Schritt 2 nicht gefunden, fehlt der Dienst im
Repo. Dann zuerst `git pull` ausführen und die Installation (Schritt 2)
wiederholen.

## Was du brauchst

- Einen Mac mit Terminal und Internetzugang
- Den ESP32-S3 SuperMini mit PN5180, verdrahtet nach den Pins in `config.h`
- Ein USB-**Datenkabel** (reine Ladekabel zeigen keine Verbindung)
- Figuren zum Testen: Tonies, darunter einen gesperrten, und eine NFC-Karte
- Das Tonie-Passwort. Es kommt nur in die lokale Datei `config.h`, nie ins Repo

Alle Befehle laufen im Terminal. `~/Tobi_box` ist der Ordner, in den du das
Repo geklont hast. Liegt er woanders, passe die Pfade an.

## 1. Homebrew-Pakete installieren

Homebrew muss installiert sein (Prüfen: `brew --version`).

```
brew install mpd python@3.11 platformio
```

Prüfen:

```
mpd --version
python3.11 --version
```

## 2. Python-Umgebung für den Dienst

```
cd ~/Tobi_box
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e "box[test]"
```

Prüfen: `tobibox --version` zeigt `tobibox 0.1.0`, `tobiboxd --version` zeigt
`tobiboxd 0.1.0`.

Bei jedem neuen Terminal zuerst `cd ~/Tobi_box` und `source .venv/bin/activate`.

## 3. Firmware bauen und flashen

Die Schritte stehen in `firmware/tobibox-reader/README.md`. Dort gibt es:

- Abschnitt „Bauen“: `include/config.h` aus der Vorlage anlegen und dein
  Tonie-Passwort eintragen (`TONIE_PRIVACY_PASSWORD`).
- Abschnitt „Flashen am Mac“: den SuperMini mit `pio` flashen.

Prüfen mit dem Serial-Monitor aus dem Abschnitt „Serielle Ausgabe ansehen“:
Gib `PING` ein und drücke Enter. Der Leser antwortet mit einer `HELLO`-Zeile.
Lege eine Figur auf: Es erscheint eine `PLACED`-Zeile mit `uid=`. Diese
Kennung brauchst du in Schritt 6.2. Beende den Monitor mit `Ctrl+C`, danach
ist der USB-Port wieder frei. Nur ein Programm kann den Port gleichzeitig nutzen.

## 4. MPD einrichten und starten

MPD spielt die Audiodateien ab. Die Vorlage `box/config/mpd.mac.example.conf`
ist für den Mac gedacht.

**4.1 Ordner und Konfiguration anlegen**

```
mkdir -p ~/tobibox-mpd/playlists
cp ~/Tobi_box/box/config/mpd.mac.example.conf ~/tobibox-mpd/mpd.conf
sed -i '' "s#DEIN_NAME#$(basename "$HOME")#g" ~/tobibox-mpd/mpd.conf
```

Prüfen: `grep Users ~/tobibox-mpd/mpd.conf` zeigt deinen Benutzernamen in allen
Pfaden. Liegt das Repo nicht unter `~/Tobi_box`, ändere außerdem die Zeile
`music_directory` auf den Ordner `box/medien-beispiel` in deinem Repo.

**4.2 Homebrew-Dienst abschalten**

Startet Homebrew MPD schon als Dienst, stoppe ihn, damit nur eine
MPD-Instanz läuft:

```
brew services stop mpd
```

**4.3 MPD starten**

In einem eigenen Terminal-Fenster, das offen bleibt:

```
mpd --no-daemon ~/tobibox-mpd/mpd.conf
```

Beenden mit `Ctrl+C`. MPD meldet im Fenster Fehler, wenn ein Pfad fehlt.

**4.4 Prüfen**

Im zweiten Terminal:

```
printf 'status\nclose\n' | nc localhost 6600
```

Die erste Zeile lautet `OK MPD 0.2…`. Danach liest du die Beispielserien in
die Datenbank von MPD ein:

```
printf 'update\nclose\n' | nc localhost 6600
```

## 5. Testserie anlegen

Der Ordner `box/medien-beispiel/` enthält schon zwei Serien: `serie-a` (drei
Folgen mit einem, zwei und drei Pieptönen) und `ueberraschung` (ein langer
Ton). Für eigene Tests legst du eine neue Serie an:

```
mkdir ~/Tobi_box/box/medien-beispiel/meine-testserie
cp ~/Tobi_box/box/medien-beispiel/serie-a/folge-0*.wav ~/Tobi_box/box/medien-beispiel/meine-testserie/
```

Ohne `serie.json` gilt der Ordnername als Serien-ID (`meine-testserie`). Die
Folgen spielen in natürlicher Reihenfolge (`folge-01` vor `folge-02`).

Wichtig: Der Ordner `box/medien-beispiel/` dient nur zum Testen. Füge die
Testdateien nicht mit `git add` hinzu. Prüfe vor jedem Commit mit `git status`.

Danach MPD die neue Serie bekannt machen:

```
printf 'update\nclose\n' | nc localhost 6600
```

## 6. Konfiguration und Zuordnung

**6.1 Konfigurationsdatei**

```
cp ~/Tobi_box/box/config/tobibox.mac.example.toml ~/Tobi_box/box/config/tobibox.toml
```

Die Kopie `tobibox.toml` steht in `.gitignore`. Sie bleibt lokal.

Prüfen:

```
tobibox status --config ~/Tobi_box/box/config/tobibox.toml
```

Die Zeile `Medien:` zeigt `ok` und die Anzahl der Serien. Die Zeile
`Protokoll:` zeigt, wohin das Ereignisprotokoll geschrieben wird.

**6.2 Zuordnung: Figur zu Serie**

Die Figur braucht eine Zuordnung zur Serie. Die Kennung (`uid=`) kommt aus
Schritt 3. Lege die Datei `box/var/config.json` an. Ersetze dabei
`DEINE_KENNUNG` durch die Kennung aus `PLACED` (Kleinbuchstaben, ohne
Leerzeichen):

```
mkdir -p ~/Tobi_box/box/var
cat > ~/Tobi_box/box/var/config.json <<'JSON'
{
  "schema_version": 1,
  "revision": 1,
  "liste_id": "0000000000000000",
  "zuordnungen": {
    "DEINE_KENNUNG": { "typ": "serie", "serie": "meine-testserie" }
  },
  "leise_zeiten": { "fenster": [] },
  "gute_nacht": { "timer_min": 30, "ausblenden_s": 60 }
}
JSON
```

Für die NFC-Karte fügst du einen zweiten Eintrag mit der Kennung der Karte
hinzu. Eine Figur mit Zuordnung zu `ueberraschung` brauchst du nicht: Der
gesperrte Tonie spielt die Überraschungs-Serie von selbst.

Nach jeder Änderung an `config.json` den Dienst neu starten.

## 7. Dienst starten

Vorher prüfen: MPD läuft (Schritt 4.4) und der Serial-Monitor ist beendet.

```
tobiboxd --config ~/Tobi_box/box/config/tobibox.toml
```

Beenden mit `Ctrl+C`. Das Ereignisprotokoll schaust du im zweiten Terminal an:

```
tail -f ~/Tobi_box/box/var/log/tobibox.log
```

Jede Zeile ist ein JSON-Eintrag. Mit `grep` findest du einzelne Ereignisse,
zum Beispiel:

```
grep '"ereignis":"spielt"' ~/Tobi_box/box/var/log/tobibox.log
```

## 8. Vorführung der CUJs

Die Abläufe (CUJs) stehen in `docs/designs/box-software.md`, Abschnitt
„Abläufe (CUJs)“. Jede Prüfung unten braucht den laufenden Dienst (Schritt 7).

### CUJ 1: Bekannte Figur auflegen

So prüfst du es:

- [ ] Figur mittig auflegen. Folge 1 (ein Piepton) startet, innerhalb von etwa 1 s.
- [ ] Im Protokoll stehen vier Einträge mit derselben `vorgang`-Kennung:
      `aufgelegt`, `entprellt`, `zugeordnet`, `spielt`.
- [ ] Beim ersten Auflegen beginnt die Serie bei Folge 1.

### CUJ 2: Abheben

So prüfst du es:

- [ ] Während die Serie spielt, Figur abnehmen. Die Wiedergabe pausiert,
      innerhalb von etwa 1 s.
- [ ] Im Protokoll steht `abgehoben`, danach `zeiger_gespeichert` mit Folge und Position.
- [ ] Zeigertest: Dienst mit `Ctrl+C` beenden, wieder starten, Figur auflegen.
      Die Folge läuft an der gespeicherten Stelle weiter.

### CUJ 5: NFC-Karte

Voraussetzung: Die Karte hat einen Eintrag in `config.json` (Schritt 6.2).

So prüfst du es:

- [ ] Karte mittig auflegen. Das Verhalten ist gleich wie bei CUJ 1.
- [ ] Karte abnehmen. Das Verhalten ist gleich wie bei CUJ 2.

### CUJ 6: Gesperrter Tonie

Voraussetzung: Ein Tonie, dessen Passwort nicht zu deinem passt.

So prüfst du es:

- [ ] Gesperrten Tonie auflegen. Der lange Überraschungs-Ton (etwa 2 s) spielt.
- [ ] Im Protokoll steht ein Eintrag zur Überraschungs-Serie (`ueberraschung`).
- [ ] Figur für unter 1 s abheben und sofort wieder auflegen. Der Ton läuft
      weiter und fängt nicht von vorn an.

### CUJ 8: Figur verrutscht

So prüfst du es:

- [ ] Eine Folge spielt. Figur leicht verschieben, oder für unter 1 s abheben
      und wieder auflegen.
- [ ] Die Wiedergabe pausiert nicht und startet nicht neu.
- [ ] Im Protokoll fehlt `abgehoben` für diesen Vorgang.

### CUJ 13: Leser fällt aus und kommt wieder

So prüfst du es:

- [ ] Während eine Folge spielt, das USB-Kabel vom SuperMini ziehen und nach
      etwa 5 s wieder stecken.
- [ ] Im Protokoll stehen Einträge des Lesers (`baustein` `reader`): Verlust,
      dann Wiederverbindung.
- [ ] Die Figur liegt noch, die Folge läuft weiter, ohne Neustart.
- [ ] Zweiter Versuch: Während das Kabel gezogen ist, Figur abheben. Nach dem
      Wiedereinstecken pausiert die Box spätestens 3,1 s nach dem Alarm, den
      der Wächter im Protokoll meldet (Karenz 3,0 s laut Vertrag).

## 9. Vorführung ohne Hardware: Fake-Leser

Das Skript `box/tools/fake_reader.py` spielt einen Leser nach. Du brauchst
dafür keinen SuperMini.

1. Terminal 1: Fake-Leser starten.

   ```
   cd ~/Tobi_box
   source .venv/bin/activate
   python box/tools/fake_reader.py --link /tmp/tobibox-fake/ttyACM0
   ```

2. In `box/config/tobibox.toml` die Zeile `geraet` auf den Symlink setzen:

   ```
   geraet = "/tmp/tobibox-fake/ttyACM0"
   ```

3. Terminal 2: Dienst starten (Schritt 7).

4. Im Terminal 1 Befehle eingeben, jeweils mit Enter:

   | Befehl | Wirkung |
   |---|---|
   | `place <kennung> ntag` | Figur oder Karte liegt auf |
   | `lock` | gesperrter Tonie liegt auf |
   | `remove` | Figur ist weg |
   | `quit` | Fake-Leser beenden |

   Beispiel: `place 04a1b2c3d4e5f6 ntag`, dann `remove`.

Die CUJ-Prüfungen oben funktionieren damit gleich. Für CUJ 8 schickst du
`remove` und direkt danach `place` (innerhalb von 1 s). Für CUJ 13 beendest du
den Fake-Leser mit `quit` und startest ihn neu. Der Dienst erkennt das wie
ein Kabelziehen.

Nach dem Üben die Zeile `geraet` in `box/config/tobibox.toml` wieder auf
`/dev/cu.usbmodem*` setzen.

## 10. Fehlersuche

**Der Serial-Port wird nicht gefunden (`/dev/cu.usbmodem*`)**

- Prüfen: `ls /dev/cu.usbmodem*`. Ist die Ausgabe leer, steckt das Kabel nicht
  oder es ist ein reines Ladekabel.
- `pio device list` zeigt alle angeschlossenen Geräte mit ihrem Port.
- Liegt die Firmware nicht drauf, flashe sie nach dem Abschnitt „Flashen am
  Mac“ im Firmware-README. Klappt das nicht, halte beim Einstecken die BOOT-Taste.
- Passen mehrere Geräte auf das Muster, nimmt der Dienst den ersten in
  sortierter Reihenfolge. Zieh die anderen ab.

**Der Port ist belegt (`Resource busy`)**

Der Serial-Monitor (`pio device monitor`) hat den Port noch offen. Mit
`Ctrl+C` beenden, dann den Dienst starten.

**MPD läuft nicht**

- Prüfen: `printf 'status\nclose\n' | nc localhost 6600`.
  Kommt `Connection refused`, läuft MPD nicht.
- Schritt 4.3 wiederholen. Im MPD-Fenster stehen Fehlermeldungen.
- Ein Blick ins Log hilft: `tail ~/tobibox-mpd/mpd.log`.
- Läuft ein Homebrew-Dienst, `brew services stop mpd` und dann Schritt 4.3.

**Kein Ton, obwohl das Protokoll `spielt` zeigt**

1. Systemlautstärke des Macs prüfen und das Ausgabegerät in den
   Systemeinstellungen (Ton) kontrollieren.
2. Steht im MPD-Log `Failed to open` oder `No such file`, stimmt
   `music_directory` in `~/tobibox-mpd/mpd.conf` nicht. Schritt 4.1 prüfen.
3. MPD direkt testen, ohne Box:

   ```
   printf 'setvol 30\nadd "serie-a/folge-01.wav"\nplay\nclose\n' | nc localhost 6600
   ```

   Hörst du den Piepton nicht, liegt es an Mac oder MPD, nicht an der Box.
   Ist es zu leise, prüfe `start` und `max` in `box/config/tobibox.toml`.

## 11. Abnahme Stufe 1

Diese Liste führt jeden Punkt von „Abnahme Stufe 1“ aus `docs/designs/box-software.md`
(Umsetzungsplan, Stufe 1) in konkrete Schritte über. Du brauchst den laufenden Dienst
(Schritt 7), den echten Leser und die Tobies aus der Liste oben. Die Prüfungen aus
Abschnitt 8 bleiben unverändert; hier steht, was dazukommt und was sich nach den
Verträgen geändert hat. Vermerke Datum und Ergebnis neben jedem Haken.

**Zum Protokoll.** Seit AP 1.6 schreibt der Dienst die Kette vollständig: `aufgelegt`,
`entprellt`, `zugeordnet`, `spielt`, `abspielen`, `abspielen_fertig` beim Auflegen und
`abgehoben`, `pausieren`, `pausieren_fertig`, `zeiger_gespeichert` beim Abheben, alle
mit derselben `vorgang`-Kennung. Praktisch zum Mitlesen:

```
tail -f ~/Tobi_box/box/var/log/tobibox.log | grep -E '"(aufgelegt|entprellt|zugeordnet|spielt|abspielen|abgehoben|pausieren|zeiger_gespeichert)"'
```

### 11.1 Alle Tests grün

- [ ] Im Repo, Python-Umgebung aktiv: `cd ~/Tobi_box/box && pytest -q`. Alles grün,
      auch die CUJ-Tests unter `box/tests/cuj/` (Dateien `test_cuj01` bis `test_cuj20`).
      Ohne MPD im Pfad werden die MPD-Tests übersprungen; `mpd --version` muss laufen.
- [ ] Firmware: `cd ~/Tobi_box/firmware/tobibox-reader && pio test -e native`. Alles grün.
- [ ] Die CI auf GitHub für den Stand ist grün.

### 11.2 CUJ 1, 2, 5, 6, 8 und 13 mit echtem Leser

- [ ] Führe die Prüfungen aus Abschnitt 8 der Reihe nach vor (CUJ 1, 2, 5, 6, 8, 13).
- [ ] Zusätzlich bei CUJ 1: Die Zeilen `aufgelegt`, `entprellt`, `zugeordnet`, `spielt`
      haben dieselbe `vorgang`-Kennung, und `aufgelegt` steht vor `abspielen`.
- [ ] Zusätzlich bei CUJ 6: Die Zeile `zugeordnet` hat `ergebnis` `ueberraschung`.
      Es entsteht keine Zeile mit „unbekannt“ und kein Eintrag in `box/var/unknown.json`.
- [ ] Zusätzlich bei CUJ 8: Auch ein Tobie, der nur am Rand aufliegt oder ein wenig
      gedreht wird, erzeugt keine Pause. Eine kurze Lücke (Tobie 0,8 s und 1,0 s
      anheben und wieder hinlegen, je 10 Mal) darf keine Zeile `abgehoben` erzeugen
      (`grep -c '"ereignis":"abgehoben"' ~/Tobi_box/box/var/log/tobibox.log`
      vor und nach den 20 Versuchen vergleichen).

**Frist bei CUJ 13.** Es gilt
der Vertrag (`core-interface.md`, 9.1): Die Karenzzeit ist **3,0 s**, die Pause kommt
**spätestens 3,1 s** nach dem Alarm oder dem `HELLO` (bewusste Ausnahme von der 1,5-s-Regel).
Der Dienst hört den Ausfall nur am fehlenden Herzschlag (Alarm nach bis zu 5 s) oder an der
getrennten Verbindung (Alarm sofort).

### 11.3 Leser-Neustart (USB-Kabel ziehen und stecken)

Eine Folge spielt, der Tobie liegt. Terminal mit `tail -f` offen lassen.

- [ ] **Kurze Unterbrechung (etwa 1 bis 2 s):** Kabel ziehen, nach 1 bis 2 s stecken.
      Das Protokoll zeigt den Verlust und die Wiederverbindung des Lesers (`baustein`
      `reader`). Die Wiedergabe läuft ohne Neustart weiter. Es erscheint kein zweites
      `abspielen` und die `vorgang`-Kennung des Tobies bleibt dieselbe, auch wenn die Firmware
      wieder bei `seq=0` beginnt.
- [ ] **Lange Unterbrechung (etwa 5 s):** Kabel ziehen, nach 5 s stecken. Die Box pausiert
      bei Ablauf der Frist (etwa 3 s nach dem Ziehen, `pausieren` mit Grund `leser_unbekannt`),
      der Zeiger ist gespeichert (`zeiger_gespeichert`). Nach dem Stecken startet **nichts
      von selbst**, auch wenn der Tobie noch liegt. Zum Weiterspielen den Tobie abheben und
      wieder auflegen.
- [ ] **Zweites Mal mit Abheben während der Unterbrechung:** Folge spielt, Kabel ziehen,
      Tobie abheben, Kabel nach etwa 2 s stecken. Die Box pausiert spätestens 3,1 s nach dem
      Ziehen (Frist, `pausieren` mit Grund `leser_unbekannt`) oder, wenn die Firmware
      vorher ihren ersten Herzschlag mit `present=0` sendet, sofort dabei (Grund `abgehoben`).
      Der Zeiger ist gespeichert, es spielt nichts weiter. Tobie wieder auflegen: Die Folge
      läuft 3 s vor der gespeicherten Stelle weiter.

### 11.4 Abheben, Dienst neu starten, wieder auflegen (Zeigerlogik)

- [ ] Folge spielt etwa 20 s. Tobie abheben. `zeiger_gespeichert` steht im Protokoll.
- [ ] Dienst mit `Ctrl+C` beenden und neu starten (Schritt 7). Tobie auflegen. Die Folge
      läuft an der gespeicherten Stelle weiter, mit 3 s Rücksprung (`spielt` mit
      `position_s` etwa 3 s unter dem gespeicherten Wert).
- [ ] **Dienst-Neustart bei liegendem Tobie** (Entscheidung G, 06.11.): Folge spielt, der
      Tobie bleibt liegen. Dienst mit `Ctrl+C` beenden und neu starten. Im Protokoll steht
      `start` mit Ergebnis `dienst_neustart` und später `dienst_neustart` mit
      `pausiert`. Es startet **keine Wiedergabe** von selbst (nur das Startgeräusch des Dienstes), auch nach 10 s nicht. Zum Weiterspielen
      den Tobie abheben und wieder auflegen. Dann läuft er an der gespeicherten Stelle weiter.
      (Der Hauptknopf, der am Pi dasselbe tut, fehlt am Mac.)
- [ ] Gegenprobe „echtes Einschalten“: Dienst beenden, den Mac neu starten (oder
      `rm ~/Tobi_box/box/var/lauf.json`), Tobie liegen lassen, Dienst starten, Tobie
      abheben und auflegen. Der Tobie spielt sofort.

### 11.5 Tobie auf eine einzelne Folge und Tobie mit mehreren Tracks

Dazu zwei Zuordnungen in `box/var/config.json` (Version 2, Eintrag `ziel`; die alten
Einträge ohne `ziel` bleiben gültig) und ein Ordner mit Tracks:

```
mkdir -p ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test
cp ~/Tobi_box/box/medien-beispiel/serie-a/folge-0*.wav ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/
mv ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/folge-01.wav ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/01.wav
mv ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/folge-02.wav ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/02.wav
mv ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/folge-03.wav ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/03.wav
printf 'update\nclose\n' | nc localhost 6600
```

`config.json` (`schema_version` 2; „TOBIE_EINZELN“ und „TOBIE_CD“ durch zwei Kennungen
ersetzen, dazu die vorhandenen Einträge übernehmen):

```
"TOBIE_EINZELN": { "ziel": { "typ": "folge", "serie": "meine-testserie", "folge": "folge-02.wav" } },
"TOBIE_CD":      { "ziel": { "typ": "folge", "serie": "meine-testserie", "folge": "cd-test" } }
```

Danach den Dienst neu starten.

- [ ] **Einzelne Folge:** Tobie auflegen. Genau diese Folge spielt (`spielt` mit
      `folge` `folge-02.wav`, `art` `folge`). Am Ende der Folge pausiert die Box (Protokoll:
      `pausieren` mit Grund `folgenende`), obwohl der Tobie noch liegt. Tobie abheben und wieder
      auflegen: Die Folge spielt **von vorn**. Die Serie `meine-testserie` startet dabei nicht
      bei der nächsten Folge.
- [ ] **Mehrere Tracks:** Tobie `TOBIE_CD` auflegen. Die drei Tracks spielen nacheinander
      **ohne Pause** (die Piepsfolgen mit einem, zwei und drei Tönen; im Protokoll `track_wechsel`).
      Erst nach dem dritten Track pausiert die Box (`folgenende`). Wieder auflegen: von vorn
      beim ersten Track.
- [ ] Während Track 2 den Tobie abheben und wieder auflegen: weiter in Track 2 an
      der gespeicherten Stelle.

### 11.6 Die Klemmung der Lautstärke im Dienst, auch beim Start

- [ ] Die Tests sind grün: `cd ~/Tobi_box/box && pytest -q -k "grenze or klemmen or startlaut"`.
- [ ] Am Mac: In `box/config/tobibox.toml` `max = 20` und `start = 20` setzen, Dienst neu starten,
      Tobie auflegen. `printf 'status\nclose\n' | nc localhost 6600 | grep volume` zeigt
      `volume: 20` oder weniger, nie mehr. (Die harte Kappe auf ALSA-Ebene gehört zum
      Pi-Probelauf.) Danach die Werte wieder zurücksetzen.

### 11.7 Messung für `docs/timing.md`

Die Messung braucht die Aufnahme am Ausgang. Methode und Befehle: `docs/timing.md`, Abschnitt 2.

- [ ] Dauerton anlegen und der Serie `messung` zuordnen (Abschnitt 2, „Vorbereitung“).
- [ ] Altes Protokoll wegräumen: `mv ~/Tobi_box/box/var/log/tobibox.log* /tmp/`.
- [ ] Aufnahme starten und still sein: `rec -r 44100 -c 1 ~/aufnahme.wav`
      (oder QuickTime, dann `afconvert -f WAVE -d LEI16 aufnahme.m4a aufnahme.wav`).
- [ ] Danach den Dienst starten. Das Startgeräusch ist die Marke für den Abgleich.
- [ ] Je Tobie (NTAG-Karte, offener Tonie, gesperrter Tonie) mindestens 20 Mal mit hörbarem Klack
      aufsetzen, etwa 3 s spielen lassen, abheben, 3 s warten. Dazu die 20 Lücken aus 11.2.
- [ ] Aufnahme und Dienst beenden. Auswerten:
      `python ~/Tobi_box/box/tools/measure_audio_latency.py ~/Tobi_box/box/var/log/tobibox.log* --wav ~/aufnahme.wav --sync-start --klick`
- [ ] Die Werte in die Tabelle in `docs/timing.md`, Abschnitt 5, eintragen: je einen Messwert
      für Warten auf den Zyklus, erste Lesung, Entprellen, Entsperren (Tonie), Übertragung,
      Dienst und MPD-Start bis zum Ton am Ausgang. Dazu die Firmware-Zeiten aus der `HB`-Zeile
      (`cycle_ms`, Serial-Monitor, Dienst vorher beenden).

### 11.8 Grenzen eingehalten

- [ ] **Auflegen:** Spalte `Gesamt` (Klack bis erster Ton) unter 1000 ms, für Karte, offenen
      und gesperrten Tonie. Das Werkzeug meldet „ÜBER GRENZE“ und beendet sich mit Status 3,
      wenn nicht.
- [ ] **Abheben:** 1100 ms + Zyklus (bis 200 ms) + Messwert `abgehoben` → Ton aus unter 1500 ms.
- [ ] **Lücken** bis 1,0 s: keine Pause (11.2).
- [ ] Wird eine Grenze überschritten, gilt die Rückfallregel (`docs/timing.md`, Abschnitt 6):
      erst die Arbeit pro Zyklus senken, dann Rückfrage an Tobias wegen 1,2 s. Keine stille Änderung
      von Ziel 2.
