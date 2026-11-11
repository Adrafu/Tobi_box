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
brew install mpd python@3.11 sox
```

`sox` brauchst du für die Messung in 11.7 (`rec`, `sox`) und für die Töne am Mac (`play`, siehe Abschnitt „Sprach-Töne und gesprochene Testmedien“).

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
pip install platformio==6.1.19
```

PlatformIO gehört in diese Python-3.11-Umgebung, **nicht** über Homebrew: Das
Homebrew-Paket nutzt die neueste Python-Version, und die Firmware-Plattform
(pioarduino) unterstützt nur Python 3.10 bis 3.14. Prüfen: `which pio` zeigt
`~/Tobi_box/.venv/bin/pio`.

Prüfen: `tobibox --version` zeigt `tobibox 0.1.0`, `tobiboxd --version` zeigt
`tobiboxd 0.1.0`.

Bei jedem neuen Terminal zuerst `cd ~/Tobi_box` und `source .venv/bin/activate`.

## 3. Firmware bauen und flashen

Die Schritte stehen in `firmware/tobibox-reader/README.md`. Alle `pio run`- und
`pio test`-Befehle laufen im Ordner `~/Tobi_box/firmware/tobibox-reader`
(`cd ~/Tobi_box/firmware/tobibox-reader`). Dort gibt es:

- Abschnitt „Bauen“: `include/config.h` aus der Vorlage anlegen und dein
  Tonie-Passwort eintragen (`TONIE_PRIVACY_PASSWORD`). Am einfachsten im
  Editor: `open -e include/config.h`. Den Wert findest du in deiner alten
  Datei `~/Documents/Arduino/tonie_test/config.h`. Tipp für zsh: Zeilen mit
  `#` nicht ins Terminal kopieren, zsh liest sie nicht als Kommentar.
- Abschnitt „Flashen am Mac“: den SuperMini mit `pio` flashen.

Prüfen mit dem Serial-Monitor aus dem Abschnitt „Serielle Ausgabe ansehen“:
Gib `PING` ein und drücke Enter. Der Leser antwortet mit einer `HELLO`-Zeile.
Lege eine Figur auf: Es erscheint eine `PLACED`-Zeile mit `uid=`. Diese
Kennung brauchst du in Schritt 6.2. Ein gesperrter Tonie liefert nur `LOCKED`,
ohne `uid`: Dort gibt es keine Kennung zu notieren, und er braucht auch keinen Eintrag
in `config.json` (er spielt die Überraschungs-Serie von selbst). Beende den Monitor mit `Ctrl+C`, danach
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
`music_directory` auf den Ordner `box/medien-sprache` in deinem Repo (die Vorlage zeigt darauf; zum
Zurückstellen auf die Piepser siehe den Abschnitt „Sprach-Töne und gesprochene Testmedien“).

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
Die Warnung „`buffer_before_play` is deprecated“ ist harmlos. Mit der Vorlage
erscheint sie nicht mehr (die Zeile ist entfernt, der Standardwert von MPD ist derselbe
Wert, 10 %). Hast du eine ältere Kopie von `mpd.conf`, kannst du die Zeile
`buffer_before_play` löschen.

**4.4 Prüfen**

Hinweis: `nc` unter macOS beendet sich, sobald die Eingabe zu Ende ist, und
zeigt dann die Antwort von MPD nicht. Deshalb steht in allen Befehlen
`sleep 1` vor dem Ende.

Im zweiten Terminal:

```
(printf 'status\n'; sleep 1) | nc localhost 6600
```

Die erste Zeile lautet `OK MPD 0.2…`. Danach liest du die Beispielserien in
die Datenbank von MPD ein:

```
(printf 'update\n'; sleep 1) | nc localhost 6600
```

## 5. Testserie anlegen

Der Ordner `box/medien-sprache/` enthält schon vier gesprochene Serien: `test-serie` (drei
Folgen), `lange-serie` (zwei Folgen zu 90 s), `track-test` (eine Folge aus drei Tracks) und
`ueberraschung`. Genaueres steht im Abschnitt „Sprach-Töne und gesprochene Testmedien“ vor Abschnitt 12.
Für eigene Tests legst du eine neue Serie an:

```
mkdir ~/Tobi_box/box/medien-sprache/meine-testserie
cp ~/Tobi_box/box/medien-sprache/test-serie/folge-0*.mp3 ~/Tobi_box/box/medien-sprache/meine-testserie/
```

Ohne `serie.json` gilt der Ordnername als Serien-ID (`meine-testserie`). Die
Folgen spielen in natürlicher Reihenfolge (`folge-01` vor `folge-02`).

Wichtig: Der Ordner `box/medien-sprache/` dient nur zum Testen. Eigene Ordner dort bleiben lokal
(`.gitignore`). Füge die
Testdateien nicht mit `git add` hinzu. Prüfe vor jedem Commit mit `git status`.

Danach MPD die neue Serie bekannt machen:

```
(printf 'update\n'; sleep 1) | nc localhost 6600
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
  "schema_version": 2,
  "revision": 1,
  "liste_id": "0000000000000000",
  "zuordnungen": {
    "DEINE_KENNUNG": { "ziel": { "typ": "serie", "serie": "meine-testserie" } }
  },
  "leise_zeiten": { "fenster": [] },
  "gute_nacht": { "timer_min": 30, "ausblenden_s": 60 }
}
JSON
```

Seit `schema_version` 2 braucht **jeder** Eintrag die Form
`"KENNUNG": { "ziel": { … } }`. Die flache Form ohne `ziel` gibt es nur in
`schema_version` 1. Für die NFC-Karte fügst du einen zweiten Eintrag mit der
Kennung der Karte hinzu. Eine Figur mit Zuordnung zu `ueberraschung` brauchst du nicht: Der
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

- [ ] Figur mittig auflegen. Folge 1 startet innerhalb von etwa 1 s (bei `meine-testserie`: „Test-Serie, Folge eins.“).
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

- [ ] Gesperrten Tonie auflegen. Die Überraschung spielt („Überraschung! Das ist die Überraschungs-Serie.“, etwa 4 s).
- [ ] Im Protokoll steht eine Zeile `zugeordnet` mit `ergebnis` `ueberraschung`
      (die Serien-ID im Protokoll ist die zufällige ID der Serie, nicht der Name):
      `grep '"ereignis":"zugeordnet"' ~/Tobi_box/box/var/log/tobibox.log | tail -1`.
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
- [ ] Im Protokoll steht der Alarm des Wächters als WARNING-Zeile mit
      `meldung` `Leser-Ausfall: …` (`baustein` `reader`), danach die INFO-Zeile
      `ereignis` `leser_verbunden`, wenn der Leser sich wieder meldet:
      `grep -E 'Leser-Ausfall|leser_verbunden' ~/Tobi_box/box/var/log/tobibox.log`.
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

   Beispiel: `place 045e1a0c7d9b31 ntag`, dann `remove`.

Die CUJ-Prüfungen 1, 2, 5, 6 und 13 funktionieren damit gleich. **CUJ 8 lässt sich
mit dem Fake-Leser nicht prüfen:** Die Toleranz von 1,1 s steckt in der Firmware
(Entprellung), der Fake-Leser meldet jedes `remove` sofort. CUJ 8 geht nur mit dem
echten Leser. Für CUJ 13 beendest du den Fake-Leser mit `quit` und startest ihn
neu, mit **demselben** `--link`. Der Dienst erkennt das wie ein Kabelziehen:
WARNING `Leser-Ausfall: …`, später INFO `leser_verbunden`.

Auf `PING` antwortet der Fake-Leser wie die Firmware: `HELLO`, `seq` zurück auf 0
und, wenn gerade ein Tobie „liegt“ (`place` oder `lock` ohne `remove`), dessen
`PLACED` (oder `LOCKED`) noch einmal mit `seq=0`.

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

- Prüfen: `(printf 'status\n'; sleep 1) | nc localhost 6600`.
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
   (printf 'setvol 30\nadd "test-serie/folge-01.mp3"\nplay\n'; sleep 1) | nc localhost 6600
   ```

   Hörst du die Stimme „Test-Serie, Folge eins.“ nicht, liegt es an Mac oder MPD, nicht an der Box.
   Ist es zu leise, prüfe `start` und `max` in `box/config/tobibox.toml`.

**Der Leser meldet sich nicht mehr (z. B. nach dem Ruhezustand des Macs)**

- Der Ring blinkt gelb und langsam. Im Protokoll (`tobibox.log`) steht `hello_timeout`.
- Abhilfe: USB-Kabel des Lesers ab- und wieder anstecken.
- Halte keinen seriellen Monitor (`pio device monitor`) parallel offen. Nur ein Programm kann den Port nutzen.

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
      (Alle `pio`-Befehle laufen in diesem Ordner. `native` braucht einen C++-Compiler:
      einmalig `xcode-select --install`.)
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
Ohne Hardware (Fake-Leser, Abschnitt 9): `quit` und den Fake-Leser mit demselben `--link`
neu starten ersetzt das Kabelziehen. Der Alarm ist die WARNING-Zeile `Leser-Ausfall: …`,
die Rückkehr die INFO-Zeile `leser_verbunden`.

- [ ] **Kurze Unterbrechung (etwa 1 bis 2 s):** Kabel ziehen, nach 1 bis 2 s stecken.
      Das Protokoll zeigt den Alarm (WARNING, `meldung` `Leser-Ausfall: …`) und die
      Wiederverbindung (INFO, `ereignis` `leser_verbunden`, jeweils `baustein` `reader`). Die Wiedergabe läuft ohne Neustart weiter. Es erscheint kein zweites
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
      (Die Folgen von `test-serie` und `meine-testserie` dauern nur gut 5 s. Für 20 s Spielzeit ordnest du
      den Tobie der Serie `lange-serie` zu, Serien-ID `7b3f2a6e8c14`; du hörst „Folge eins, Sekunde zwanzig“.)
- [ ] Dienst mit `Ctrl+C` beenden und neu starten (Schritt 7). Tobie auflegen. Die Folge
      läuft an der gespeicherten Stelle weiter, mit 3 s Rücksprung (`spielt` mit
      `position_s` etwa 3 s unter dem gespeicherten Wert).
- [ ] **Dienst-Neustart bei liegendem Tobie** (Entscheidung G, 06.11.): Folge spielt, der
      Tobie bleibt liegen. Dienst mit `Ctrl+C` beenden und neu starten. Im Protokoll steht
      `start` mit Ergebnis `dienst_neustart` und später `dienst_neustart` mit
      `pausiert`. Es startet **keine Wiedergabe** von selbst (nur das Startgeräusch des Dienstes), auch nach 10 s nicht. Zum Weiterspielen
      den Tobie abheben und wieder auflegen. Dann läuft er an der gespeicherten Stelle weiter.
      (Der Hauptknopf, der am Pi dasselbe tut, fehlt am Mac.)
      - *Mit dem Fake-Leser:* `place <kennung> ntag` (oder `lock`), Folge spielt, **kein**
        `remove`. Den Dienst mit `Ctrl+C` beenden und neu starten, den Fake-Leser laufen
        lassen (gleicher `--link`). Der Dienst sendet `PING`, der Fake-Leser antwortet mit
        `HELLO` und meldet den liegenden Tobie erneut mit `seq=0`, genau wie die Firmware.
        Prüfen: `grep dienst_neustart ~/Tobi_box/box/var/log/tobibox.log | tail -n 2`.
      - *Mit dem echten Leser:* Tobie liegen lassen, Dienst beenden und neu starten, sonst
        dasselbe. (Der Serial-Monitor muss beendet sein.)
- [ ] Gegenprobe „echtes Einschalten“ (CUJ 20): Dienst mit `Ctrl+C` beenden, **danach** den Mac
      neu starten (oder `rm ~/Tobi_box/box/var/lauf.json`; vor dem Beenden würde der Dienst die
      Datei wieder anlegen). Der Tobie bleibt auf dem Leser liegen. Dienst starten: Der Tobie
      spielt **sofort von selbst**, ohne Abheben, an der gespeicherten Stelle. Im Protokoll steht
      `start` mit Ergebnis `ok`, kein `dienst_neustart`. Mit dem Fake-Leser geht nur der Weg
      über `rm`, denn nach einem Neustart des Macs läuft der Fake-Leser nicht mehr.

### 11.5 Tobie auf eine einzelne Folge und Tobie mit mehreren Tracks

Dazu zwei Zuordnungen in `box/var/config.json` und ein Ordner mit Tracks:

```
mkdir -p ~/Tobi_box/box/medien-sprache/meine-testserie/cd-test
cp ~/Tobi_box/box/medien-sprache/test-serie/folge-0*.mp3 ~/Tobi_box/box/medien-sprache/meine-testserie/cd-test/
mv ~/Tobi_box/box/medien-sprache/meine-testserie/cd-test/folge-01.mp3 ~/Tobi_box/box/medien-sprache/meine-testserie/cd-test/01.mp3
mv ~/Tobi_box/box/medien-sprache/meine-testserie/cd-test/folge-02.mp3 ~/Tobi_box/box/medien-sprache/meine-testserie/cd-test/02.mp3
mv ~/Tobi_box/box/medien-sprache/meine-testserie/cd-test/folge-03.mp3 ~/Tobi_box/box/medien-sprache/meine-testserie/cd-test/03.mp3
(printf 'update\n'; sleep 1) | nc localhost 6600
```

Die `config.json` hat `schema_version` 2. **Jeder** Eintrag steht in der Form
`"KENNUNG": { "ziel": { … } }`; die flache Form ohne `ziel` gibt es nur in
`schema_version` 1. `typ` ist `serie`, `folge` (mit `serie` und `folge`) oder `aktion`.
Ein vollständiges Beispiel mit einer Serie, einer einzelnen Folge und einer Folge mit
Tracks („KENNUNG_…“ durch deine drei Kennungen ersetzen):

```
{
  "schema_version": 2,
  "revision": 2,
  "liste_id": "0000000000000000",
  "zuordnungen": {
    "KENNUNG_SERIE":   { "ziel": { "typ": "serie", "serie": "meine-testserie" } },
    "KENNUNG_EINZELN": { "ziel": { "typ": "folge", "serie": "meine-testserie", "folge": "folge-02.mp3" } },
    "KENNUNG_CD":      { "ziel": { "typ": "folge", "serie": "meine-testserie", "folge": "cd-test" } }
  },
  "leise_zeiten": { "fenster": [] },
  "gute_nacht": { "timer_min": 30, "ausblenden_s": 60 }
}
```

Danach den Dienst neu starten. Bei Fehlern im Dienst: Im Protokoll nach `datei_defekt`
suchen (`grep datei_defekt ~/Tobi_box/box/var/log/tobibox.log`). Die kaputte Datei liegt
dann als `box/var/config.json.defekt` daneben; das Feld `grund` sagt, was nicht stimmt.

- [ ] **Einzelne Folge:** Tobie auflegen. Genau diese Folge spielt (`spielt` mit
      `folge` `folge-02.mp3`, `art` `folge`). Am Ende der Folge pausiert die Box (Protokoll:
      `pausieren` mit Grund `folgenende`), obwohl der Tobie noch liegt. Tobie abheben und wieder
      auflegen: Die Folge spielt **von vorn**. Die Serie `meine-testserie` startet dabei nicht
      bei der nächsten Folge.
- [ ] **Mehrere Tracks:** Tobie `KENNUNG_CD` auflegen. Die drei Tracks spielen nacheinander
      **ohne Pause** (die gesprochenen Folgen „Test-Serie, Folge eins“, „…zwei“, „…drei“; im Protokoll `track_wechsel`).
      Erst nach dem dritten Track pausiert die Box (`folgenende`). Wieder auflegen: von vorn
      beim ersten Track.
- [ ] Während Track 2 den Tobie abheben und wieder auflegen: weiter in Track 2 an
      der gespeicherten Stelle.

### 11.6 Die Klemmung der Lautstärke im Dienst, auch beim Start

- [ ] Die Tests sind grün: `cd ~/Tobi_box/box && pytest -q -k "grenze or klemmen or startlaut"`.
- [ ] Am Mac: In `box/config/tobibox.toml` `max = 20` und `start = 20` setzen, Dienst neu starten,
      Tobie auflegen. `(printf 'status\n'; sleep 1) | nc localhost 6600 | grep volume` zeigt
      `volume: 20` oder weniger, nie mehr. (Die harte Kappe auf ALSA-Ebene gehört zum
      Pi-Probelauf.) Danach die Werte wieder zurücksetzen.

### 11.7 Messung für `docs/timing.md`

Die Messung braucht die Aufnahme am Ausgang. Methode und Befehle: `docs/timing.md`, Abschnitt 2.

- [ ] Dauerton anlegen und der Serie `messung` zuordnen (Abschnitt 2, „Vorbereitung“).
      Die Serie liegt im Ordner `box/medien-sprache/messung/` (nicht committen):

      ```
      mkdir -p ~/Tobi_box/box/medien-sprache/messung
      sox -n -r 44100 -c 1 ~/Tobi_box/box/medien-sprache/messung/dauerton.wav synth 60 sine 440 vol 0.5
      cat > ~/Tobi_box/box/medien-sprache/messung/serie.json <<'JSON'
      {
        "schema_version": 1,
        "id": "messung",
        "name": "Messung",
        "typ": "normal",
        "folgen": ["dauerton.wav"],
        "angelegt_am": "2026-11-06T09:00:00Z"
      }
      JSON
      (printf 'update\n'; sleep 1) | nc localhost 6600
      ```

      In `box/var/config.json` die Einträge für die NTAG-Karte und den Tonie auf diese
      Serie setzen (Schema 2, Kennungen aus Schritt 3) und den Dienst neu starten:

      ```
      "KENNUNG_KARTE": { "ziel": { "typ": "serie", "serie": "messung" } },
      "KENNUNG_TONIE": { "ziel": { "typ": "serie", "serie": "messung" } }
      ```
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

## Sprach-Töne und gesprochene Testmedien

Damit du jederzeit hörst, was die Box tut, gibt es einen zweiten Satz Töne und Testmedien mit
Stimme. Die Piepser in `box/sounds/` bleiben unverändert; die endgültigen Töne entscheidest du später.
Alles ist mit der freien Stimme „Thorsten“ (CC0) erzeugt, siehe `box/sounds/sprache/README.md`.

**Die Serien** in `box/medien-sprache/`:

| Ordner | Serien-ID | Inhalt |
|---|---|---|
| `test-serie` | `5e1a0c7d9b31` | 3 Folgen, je „Test-Serie, Folge eins.“ (zwei, drei), danach 4 s Stille |
| `lange-serie` | `7b3f2a6e8c14` | 2 Folgen zu je 90 s: „Lange Serie, Folge eins.“, dann alle 5 s „Folge eins, Sekunde fünf“, „…zehn“ bis „…fünfundachtzig“, dazu ein leiser Ton. Für den Rücksprung (3 s) und die 15-s-Regel (Entscheidung I) |
| `track-test` | `9d4c1e5a2f68` | 1 Folge (`folge-01`) aus 3 Tracks, je 8 s: „Track eins von drei.“, „…zwei…“, „…drei…“ |
| `ueberraschung` | `e2a8b6d0c397` | „Überraschung! Das ist die Überraschungs-Serie.“ (4 s), Typ `ueberraschung` |

**Umstellen** in deiner eigenen `box/config/tobibox.toml` (zwei Zeilen):

```toml
medien = "../medien-sprache"          # im Abschnitt [pfade]
ordner = "../sounds/sprache"          # im Abschnitt [toene]
```

Die Vorlage `tobibox.mac.example.toml` hat das schon. Ändere zusätzlich `music_directory` in
`~/tobibox-mpd/mpd.conf` auf `.../Tobi_box/box/medien-sprache` (die Vorlage `mpd.mac.example.conf` zeigt darauf),
starte MPD neu und lass die Datenbank neu einlesen: `(printf 'update\n'; sleep 1) | nc localhost 6600`.
Zurück zu Piepsern und Beispielmedien: `medien = "../medien-beispiel"`, die Zeile `ordner` in `[toene]`
löschen (oder auf `../sounds` setzen) und `music_directory` wieder auf `medien-beispiel`.

**Was mit deinen Zuordnungen passiert.** Die Serien-IDs sind neu. Deine `config.json` zeigt auf
`meine-testserie` und auf eine Serie `lang` mit deiner eigenen Datei `zaehlen.mp3` in `box/medien-beispiel/lang`.
Die gibt es im neuen Ordner nicht; solche Tobies spielen dann die Überraschung. Zwei Wege:

- Ordne mit `tobibox sim card <UID> --serie <ID>` neu zu (IDs in der Tabelle), oder
- kopiere deine Serien in den neuen Ordner, z. B. `cp -R ~/Tobi_box/box/medien-beispiel/lang ~/Tobi_box/box/medien-sprache/`
  (und `meine-testserie` ebenso), dann `update` an MPD. Eigene Ordner in `box/medien-sprache/` bleiben
  durch `.gitignore` lokal; versioniert sind nur die vier erzeugten Serien.

**Die Status-Karte** nennt jeden Prüfpunkt: „Leser in Ordnung.“ (in der Simulation „Leser: Simulation.“),
„Medien in Ordnung.“, „Netz: Fehler.“, „Speicher in Ordnung.“. Fehlt in einem Tonordner die Datei eines
Prüfpunkts, spielt die Box den allgemeinen Ton `pruef_ok` oder `pruef_fehler`.

Die vier Ansagen der Status-Karte spielen als **eine** Datei mit einem einzigen `afplay` und je 0,15 s
Stille dazwischen (09.11.). Vorher startete jede Ansage einen eigenen `afplay`-Prozess; der Start kostet am Mac
Zeit. Wie lange `afplay` wirklich braucht, steht im Protokoll: Die Zeile `ton gespielt` (Stufe DEBUG) nennt
`prozess_ms`. Ist das deutlich länger als die Dauer der Ansage, ist der Rest der Start und das Ende von
`afplay`.

**Töne und Pausen am Mac (Messung 09.11.).** Mit `afplay` vergehen bei einer Ansage von 1,2 s insgesamt
2,2 s, also rund 1 s Leerlauf je Ton. Mit `play` aus sox (`brew install sox`) sind es nur etwa 0,15 s.
`play` schneidet aber das Ende ab: Das letzte „f“ in „Leg den neuen Tobie auf.“ fehlt. Deshalb steht in
`tobibox.mac.example.toml` `kommando = ["play", "-q", "{datei}", "pad", "0", "0.15"]`: `pad 0 0.15`
hängt 0,15 s Stille an, dann ist die Ansage vollständig. Willst du wieder `afplay`, lösche diese Zeile.

**Bluetooth-Kopfhörer (AirPods):** Dort schneidet der Mac oft den Anfang ab. Dann im Abschnitt `[toene]` deiner lokalen `box/config/tobibox.toml` mehr Stille vorne geben: `kommando = ["play", "-q", "{datei}", "pad", "0.5", "0.15"]`. Die erste Zahl nach `pad` ist die Stille vorn in Sekunden.
Auf dem Pi nutzt die Box `aplay`, dort wird dieses Problem nicht erwartet. Das messen wir beim Pi-Probelauf.

Die Töne kommen aus `box/tools/make_sprache.py`; neu erzeugen geht nur im Container, nicht am Mac.

## Lautstärke der Töne und des Hörspiels (Entscheidung J, 09.11.)

**Was neu ist.** Die Ansagen und Töne der Box sind jetzt so laut wie das Hörspiel. Vorher spielten
sie mit einem festen Pegel und waren viel lauter als das Hörspiel bei Startlautstärke 20. Jetzt
folgt jeder Ton der aktuellen Lautstärke: Drehst du leiser, wird auch die Ansage leiser. Die Grenzen
(`max`, `kopfhoerer`, „leiser“-Zeiten) gelten für Töne wie für das Hörspiel. Ganz still wird ein
Ton nicht: Er spielt mindestens mit Lautstärke 10. Der Hinweiston bleibt leiser als die Lautstärke
(Vorgabe 15, nie darüber, außer durch dieses Minimum).

**Warum es vorher so war.** MPD setzt die Lautstärke nicht linear um. Mit `mixer_type "software"`
(so steht es in `mpd.mac.example.conf`) gilt `Verstärkung = (exp(p / 25) − 1) / (exp(4) − 1)`. Das ist
ein Wert pro Prozent, nicht „halb so laut bei 50“:

| Lautstärke | 10 | 20 (Start) | 30 | 40 (Maximum) | 50 | 70 | 100 |
|---|---|---|---|---|---|---|---|
| Pegel gegenüber der Datei | −41 dB | −33 dB | −27 dB | −23 dB | −18 dB | −11 dB | 0 dB |

Bei 20 ist das Hörspiel also gut 30 dB unter der Datei, ein Ton mit dem alten Pegel 40 (linear) nur
8 dB. Das ist der große Unterschied. Die Box rechnet Töne jetzt mit derselben Kurve, damit gleiche
Lautstärke auch gleich laut klingt. Wer das Hörspiel lauter will, dreht auf oder erhöht `start`
und `max` in `box/config/tobibox.toml` (zum Beispiel `start = 40`, `max = 60`). Die Kurve für den
Pi ist anders (ALSA-`softvol`); sie steht in der Konfiguration (`[toene] kennlinie`), am Mac
änderst du nichts.

**Was du am Mac tun musst.**

- `git pull`, dann den Dienst neu starten. Die neuen Töne und Testmedien liegen im Repo. Die
  MPD-Konfiguration bleibt unverändert (Software-Mixer, `replaygain "track"`). Nach dem Neuladen der
  Medien einmal `(printf 'update\n'; sleep 1) | nc localhost 6600`.
- Wenn du `ton_pegel` in der `config.json` hast: Das Feld ist ohne Wirkung und darf stehen bleiben.

**Gleiche Lautheit.** Die Töne in `box/sounds/`, `box/sounds/sprache/` und die gesprochenen Testmedien
in `box/medien-sprache/` liegen jetzt alle bei −18 LUFS. Das ist der Wert, auf den `rsgain` auf dem NAS
später die echten Hörspiele bringt. Die Testmedien tragen dazu ReplayGain-Tags; ohne Tags würde MPD sie
um 6 dB dämpfen (`replaygain_missing_preamp`).

**Eigene Dateien am Mac.** Ein eigenes Hörspiel wie dein `zaehlen.mp3` hat keine ReplayGain-Tags.
MPD dämpft es dann um 6 dB und lässt seinen eigenen Pegel stehen. Es kann deshalb leiser oder lauter
sein als die Testmedien oder die Ansagen. Das ist am Mac gewollt so; **auf der Box gleicht `rsgain` das
aus** (Design, D6). Willst du am Mac denselben Pegel, mach eine normalisierte Kopie. Du brauchst
`ffmpeg` (`brew install ffmpeg`):

```bash
python3 ~/Tobi_box/box/tools/lautheit.py --normalisiere ~/Tobi_box/box/medien-sprache/lang/zaehlen.mp3
```

Das schreibt `zaehlen-normalisiert.mp3` neben die Datei (−18 LUFS, mit ReplayGain-Tags). Das
Original bleibt. Zum Hören nimm die Kopie und führe danach `update` bei MPD aus. Den Pegel einer
Datei misst `python3 ~/Tobi_box/box/tools/lautheit.py DATEI`. Bei sehr dynamischen Dateien kann der
Pegel knapp unter −18 bleiben (ein Limiter schützt vor Übersteuern); der Rest steht im Tag.

## 12. Abnahme Stufe 2

Diese Liste führt jeden Punkt von „Abnahme Stufe 2“ aus `docs/designs/box-software.md`
in konkrete Schritte über. Alle Punkte aus Abschnitt 11 gelten weiter; hier steht nur, was
dazukommt. Du brauchst den laufenden Dienst (Schritt 7) und den echten Leser. Vermerke Datum
und Ergebnis neben jedem Haken.

Die Befehle `tobibox sim …` sprechen mit dem laufenden Dienst über `sim.sock`. Läuft der Dienst
nicht, melden sie „Dienst nicht erreichbar“ (Exit-Code 3). Im zweiten Terminal einmal die
Konfiguration festlegen, dann gelten die Befehle unten ohne `--config`:

```bash
export TOBIBOX_CONFIG=~/Tobi_box/box/config/tobibox.toml
```

Die Kennung eines Tobies steht im Protokoll. Nach dem Auflegen des Tobies holst du die letzte
Kennung so (Platzhalter `<UID>`, `<UID-NEU>` usw. durch deine echten Werte ersetzen):

```bash
grep -o '"uid":"[^"]*"' ~/Tobi_box/box/var/log/tobibox.log | tail -n 1
```

Für die Tests brauchst du drei Tobies und eine NTAG-Karte: `<UID>` (wird in 12.2 und 12.4
der Serie `lange-serie`, in 12.3 der Serie `test-serie` zugeordnet), `<UID-NEU>` (in 12.5 noch nie
zugeordnet), `<UID-NEU-2>` (noch nie zugeordnet, für den Folgen-Lernlauf in 12.6) und die
Karte `<UID-KARTE>`.

**Serien-ID statt Ordnername.** Bei `--serie` gehört die **ID** aus der Datei `serie.json`
der Serie, nicht der Ordnername. Die IDs der gesprochenen Serien stehen im Abschnitt „Sprach-Töne und gesprochene Testmedien“:
`test-serie` hat `5e1a0c7d9b31`, `lange-serie` `7b3f2a6e8c14`, `track-test` `9d4c1e5a2f68` und die
Überraschungs-Serie `e2a8b6d0c397`. Eine unbekannte ID (oder Folge) lehnt `tobibox sim` ab
(Exit-Code 2); die Meldung nennt die vorhandenen Serien-IDs mit ihrem Anzeigenamen. Die ID liest du so nach:

```bash
grep '"id"' ~/Tobi_box/box/medien-sprache/test-serie/serie.json
```

**Zu den Tönen.** Mit `[toene] ordner = "../sounds/sprache"` sagt die Box, was sie tut:
`start` „Tobi Box ist bereit.“, `unbekannt` „Diesen Tobie kenne ich noch nicht. Hier ist eine
Überraschung.“, `lernen_beginn` „Lernmodus an. Leg den neuen Tobie auf.“, `lernen_ende`
„Lernmodus beendet.“, `fehler` „Da ist etwas schiefgegangen.“, `hinweis` ein kurzer, leiser Klang ohne Sprache (Entscheidung T, 10.11.).
Mit den Piepsern (`box/sounds/`) gilt: `start` (0,5 s), `lernen_beginn` und `lernen_ende` (je 0,5 s),
`unbekannt` (0,4 s), `hinweis` (0,1 s), `pruef_ok` (0,1 s, hoch) und `pruef_fehler` (0,4 s, tief).
Wer die Töne im Protokoll sehen will: In `box/config/tobibox.toml` die Zeile
`ebene = "INFO"` auf `ebene = "DEBUG"` setzen und den Dienst neu starten. Dann steht bei
jedem Ton eine Zeile mit `"ereignis":"ton"` und dem Namen im Feld `ton`.

### 12.1 Vorbereitung

Die lange Folge, die du für 12.2 und 12.4 brauchst, liegt fertig im Repo: die Serie `lange-serie`
(ID `7b3f2a6e8c14`, zwei Folgen zu je 90 s). Du musst nichts anlegen. Stelle nur sicher, dass
`music_directory` in `mpd.conf` und `medien` in `tobibox.toml` auf `box/medien-sprache` zeigen
(Abschnitt „Sprach-Töne und gesprochene Testmedien“) und dass MPD die Dateien kennt:

```bash
(printf 'update\n'; sleep 1) | nc localhost 6600
```

Dann Dienst starten:

```bash
cd ~/Tobi_box && git pull
tobiboxd --config ~/Tobi_box/box/config/tobibox.toml
```

- [ ] Der Dienst startet mit dem Startgeräusch. Im Protokoll steht eine Zeile `start`.
      **Was du sehen/hören solltest:** Das Startgeräusch, dann Stille. Im zweiten Terminal
      liefert `tobibox status` die Zeile `Dienst: läuft (Status vom Dienst über sim.sock)`.

### 12.2 Resume über einen Neustart des Dienstes

Ordne den Tobie `<UID>` der langen Serie zu:

```bash
tobibox sim card <UID> --serie 7b3f2a6e8c14
```

- [ ] Lege `<UID>` auf. Nach etwa 10 s hebst du den Tobie ab.
      **Was du hörst:** „Lange Serie, Folge eins.“, dann alle 5 s „Folge eins, Sekunde fünf“,
      „Folge eins, Sekunde zehn“ und dazu einen leisen, gleichmäßigen Ton. Beim Abheben wird die Stelle
      gespeichert; im Protokoll steht `zeiger_gespeichert` mit `position_s` von etwa 10.
- [ ] Beende den Dienst mit `Ctrl+C` und starte ihn neu (Befehl aus Schritt 12.1, nur die
      Zeile `tobiboxd …`). Lege `<UID>` danach auf.
      **Was du hörst:** Die Folge läuft weiter, etwa 3 s vor der gespeicherten Stelle: Du hörst
      nach etwa 3 s „Folge eins, Sekunde zehn“ noch einmal (du hattest sie beim Abheben gerade gehört).
      Im Protokoll liegt `position_s` von `spielt` rund 3 s unter dem Wert vom Abheben (also etwa 7).

      **Hinweis (Entscheidung I, 09.11.):** Hebe nicht in den letzten 15 s der Folge ab. Fehlen
      beim Auflegen weniger als 15 s bis zum Ende, gilt die Folge als fertig gehört: Ein Tobie für
      eine einzelne Folge beginnt von vorn, ein Tobie für eine Serie spielt die nächste Folge. Im
      Protokoll steht dann eine Zeile `rest_regel` mit `rest_s`. Die lange Folge dauert 90 s: Hebst du
      nach „Folge eins, Sekunde achtzig“ ab, beginnt ein Tobie für diese Folge beim Auflegen von vorn
      („Lange Serie, Folge eins.“), eine Serie spielt „Lange Serie, Folge zwei.“. Folgen unter 60 s sind
      ausgenommen; die Folgen von `test-serie` in 12.3 (gut 5 s) sind davon nicht berührt.

### 12.3 Pause nach jeder Folge

Jetzt die Serie `test-serie` (Folgen `folge-01.mp3` bis `folge-03.mp3`, je gut 5 s lang). Ordne `<UID>`
neu zu. Hebe den Tobie vorher ab, falls er liegt:

```bash
tobibox sim card <UID> --serie 5e1a0c7d9b31
```

Eine Serie beginnt bei der Folge, bei der sie zuletzt stand. Hast du `test-serie` früher schon gespielt,
beginnt sie nicht bei Folge 1; lies die Reihenfolge unten dann ab dieser Folge.

- [ ] Lege `<UID>` auf und lass ihn liegen. Die Folge spielt bis zum Ende.
      **Was du hörst:** „Test-Serie, Folge eins.“, danach etwa 4 s Stille. Im Protokoll steht `pausieren` mit
      Grund `folgenende`. Der Tobie liegt noch, die Box startet nichts von selbst (warte 10 s).

```bash
grep '"ereignis":"pausieren"' ~/Tobi_box/box/var/log/tobibox.log | tail -n 1
```

      Die Zeile enthält `"grund":"folgenende"`.

- [ ] Hebe `<UID>` ab und lege ihn wieder auf.
      **Was du hörst:** „Test-Serie, Folge zwei.“, von vorn.
- [ ] Lass Folge 2 zu Ende laufen. Die Box pausiert. Hebe `<UID>` ab und lege ihn wieder auf.
      **Was du hörst:** „Test-Serie, Folge drei.“
- [ ] Lass Folge 3 zu Ende laufen. Die Box pausiert. Hebe `<UID>` ab und lege ihn wieder auf.
      **Was du hörst:** „Test-Serie, Folge eins.“ wieder. Nach der letzten Folge steht der Zeiger auf Folge 1.

### 12.4 CUJ 20: Tobie liegt beim Start des Dienstes

Hier gibt es zwei Fälle, die du auseinanderhalten musst. Der Dienst erkennt sie am Marker
`~/Tobi_box/box/var/lauf.json` (Entscheidung G, 06.11.). Darin steht die Kennung des letzten
Starts des Geräts (`boot_id`) und der Tobie, der zuletzt auflag:

- **Dienst-Neustart** (Update, Absturz, `Ctrl+C` und neu starten): Die Kennung des Starts ist
  gleich. Ein liegender Tobie startet **nicht** von selbst. Die Box bleibt pausiert.
- **Einschalten** (Mac neu gestartet, Akku leer, Strom weg): Die Kennung ist neu oder der Marker
  fehlt. Ein liegender Tobie spielt **sofort**, ohne Abheben.

Ordne `<UID>` wieder der langen Serie zu (hebe den Tobie vorher ab):

```bash
tobibox sim card <UID> --serie 7b3f2a6e8c14
```

- [ ] **Dienst-Neustart:** Lege `<UID>` auf, die lange Folge spielt. Warte etwa 10 s. Beende den
      Dienst mit `Ctrl+C`. Der Tobie liegt dabei weiter auf dem Leser. Starte den Dienst neu
      (Zeile `tobiboxd …` aus Schritt 12.1).
      **Was du hörst:** Nur das Startgeräusch des Dienstes. Danach bleibt es still, auch nach
      10 s. Im Protokoll stehen `start` mit Ergebnis `dienst_neustart` und danach
      `dienst_neustart` mit Ergebnis `pausiert`.

```bash
grep dienst_neustart ~/Tobi_box/box/var/log/tobibox.log | tail -n 2
```

- [ ] Den Hauptknopf gibt es am Mac nicht; seit AP 4.8 ersetzt ihn `tobibox sim key haupt`. Hier zum Üben:
      Hebe `<UID>` ab und lege ihn wieder auf.
      **Was du hörst:** Die Folge läuft an der gespeicherten Stelle weiter (3 s Rücksprung): Die zuletzt
      gehörte Sekundenansage kommt bald noch einmal (die Box springt 3 s zurück).
- [ ] **Einschalten:** Der Tobie liegt weiter auf dem Leser. Beende den Dienst mit `Ctrl+C`. Erst
      danach löschst du den Marker. (Würdest du ihn vorher löschen, schriebe der Dienst ihn beim
      Beenden wieder.) Das ersetzt das Ausschalten des Macs:

```bash
rm ~/Tobi_box/box/var/lauf.json
```

      Starte den Dienst wieder (Zeile `tobiboxd …` aus Schritt 12.1).
      **Was du hörst:** Das Startgeräusch, und gleich danach (sobald es zu Ende ist) spielt die Folge **von selbst**,
      ohne dass du den Tobie abhebst, an der gespeicherten Stelle. Im Protokoll steht `start`
      mit Ergebnis `ok`, **kein** `dienst_neustart`, und `spielt`:

```bash
grep -E '"ereignis":"(start|dienst_neustart|spielt)"' ~/Tobi_box/box/var/log/tobibox.log | tail -n 3
```

      Echtes Einschalten (den Mac neu starten und den Dienst danach starten) hat dieselbe Wirkung,
      weil sich die Kennung des Starts ändert. Dabei muss der Tobie auf dem Leser liegen bleiben.

### 12.5 Unbekannter Tobie: Überraschung, Meldung, Bestätigung

Hebe vorher einen Tobie ab, falls einer liegt.

- [ ] Lege `<UID-NEU>` auf (ein Tobie, den du noch nie zugeordnet hast).
      **Was du hörst:** Zuerst „Diesen Tobie kenne ich noch nicht. Hier ist eine Überraschung.“ (`unbekannt`), **bis
      zum Ende**, und erst danach „Überraschung! Das ist die Überraschungs-Serie.“ (`ueberraschung`, 4 s). Die beiden
      überlappen sich nie (Entscheidung L, 09.11.: Es spielen nie zwei Sachen gleichzeitig). Im Protokoll hat die
      Zeile `zugeordnet` das Ergebnis `ueberraschung`; die Zeile `abspielen` mit Ergebnis `wartet_auf_toene` zeigt, dass
      der Start auf das Ende des Tons wartete.
- [ ] Hebe `<UID-NEU>` ab, **während** der Ton `unbekannt` noch spricht (lege ihn auf und nimm ihn nach etwa 1 s wieder
      weg). **Was du hörst:** Der Ton spricht zu Ende, danach bleibt es still. Die Überraschung startet nicht.
      Im Protokoll steht `abspielen` mit Ergebnis `verworfen`, wenn der Start schon auf den Ton wartete (der Befehl
      zum Abheben hat ihn verworfen), und der Tobie steht als „unbekannt“ in `unknown.json`.
- [ ] Prüfe den Status:

```bash
tobibox status
```

      **Was du siehst:** Die Zeile `Meldungen: <UID-NEU> (unbekannt, 1x) warten auf Bestätigung`.
      Die Datei `~/Tobi_box/box/var/unknown.json` enthält den Eintrag.
- [ ] Bestätige die Meldung:

```bash
tobibox sim ack <UID-NEU>
```

      **Was du siehst:** `{"ok": true}`, Exit-Code 0. Danach zeigt `tobibox status` die Zeile
      `Meldungen: keine offen (unknown.json)`. Ein Neustart des Dienstes vor der Bestätigung löscht
      den Eintrag nicht.

### 12.6 Lernmodus

Der Lernmodus startet mit einem Ton. Die Box nimmt den Befehl an, und ab da hast du 2 Minuten,
um den Tobie aufzulegen. Ein Tobie, der schon liegt, wird nicht erneut gemeldet: Hebe ihn
vorher ab. Die Option `--ttl` (Vorgabe 60 s) ist nur die Lebensdauer des Befehls bis zur
Annahme: Kommt der Befehl innerhalb dieser Zeit an, nimmt die Box ihn an. Die 2 Minuten
beginnen mit der Annahme und hängen nicht von `--ttl` ab. Ein kleiner Wert wie `--ttl 5` verkürzt
den Lernmodus also nicht. Nach 2 Minuten ohne Tobie endet er von selbst
(Protokoll: `lernmodus_ende` mit Ergebnis `frist`).

**Die Töne im Lernmodus.** Es gibt genau zwei: `lernen_beginn` beim Start und `lernen_ende`
beim Ende. `lernen_ende` kommt bei jedem Ende: Tobie aufgelegt (gelernt oder abgelehnt), Abbruch
und Fristablauf. Ob gelernt oder abgelehnt wurde, hörst du also nicht am Ende-Ton, sondern nur
an dem, was der Tobie danach spielt, und im Protokoll. Die Box wartet nach dem Auflegen **still** auf
den HA-Ersatz (Entscheidung H, 07.11.): Sie spielt weder die Überraschung noch den Ton
`unbekannt`, auch nicht bei einem neuen Tobie. Sobald die Zuordnung da ist (beim HA-Ersatz
Bruchteile einer Sekunde), startet das Lernziel sofort. Wird der Tobie abgelehnt, oder kommt
10 Sekunden lang keine Antwort, verhält sich die Box wie bei einem normalen Auflegen (ein
bekannter Tobie spielt sein Ziel, ein neuer die Überraschung mit dem Ton `unbekannt` und steht danach wieder
als „unbekannt“ in `unknown.json`).
Abheben beendet das Warten. Während des Wartens bewirken Hauptknopf, Vor und Zurück nichts; die
Lautstärke wirkt.

**Nacheinander, nie gleichzeitig (Entscheidung L, 09.11.).** Kommen Ton und Hörspiel aus demselben Anlass,
spielt immer **zuerst der Ton bis zum Ende, dann das Hörspiel**. Das gilt auch hier: Nach dem Auflegen hörst du
erst `lernen_ende` ganz, dann startet das Lernziel (oder, bei einem Tobie ohne Zuordnung, nach dem Ton `unbekannt` die
Überraschung). Vorher überlappte sich das (zum Beispiel „Lernmodus beendet.“ mit „Test-Serie, Folge drei.“).
Ein Ton, der kommt, während ein Hörspiel schon läuft (zum Beispiel der Hinweiston bei Vor am letzten Track
eines Folgen-Tobies), hält das Hörspiel kurz an und setzt es danach **an genau derselben Stelle** fort, ohne den
3-s-Rücksprung. Das zählt nicht als Pause: Es wird kein Zeiger gespeichert, und der Status zeigt „spielt“.

**a) Serie lernen**

```bash
tobibox sim learn --serie 5e1a0c7d9b31
```

- [ ] Du siehst `{"ok": true}` und hörst einen Ton. `tobibox status` zeigt `Lernmodus: an`.
      Lege `<UID-NEU>` auf (hebe ihn vorher ab, falls er liegt).
      **Was du hörst:** Nur ein kurzer Ton (`lernen_ende`), **kein** `unbekannt` und keine
      Überraschung dazwischen; dann, sobald der Ton zu Ende ist (nie gleichzeitig), spielt der Tobie die Serie `test-serie` an dem Zeiger, an dem die Serie steht (nach 12.3
      Folge 1 oder 2). Im Protokoll steht eine Zeile mit Baustein `ha_ersatz`, Ereignis
      `zuordnung` und Ergebnis `ok`.

```bash
grep -A5 '"<UID-NEU>"' ~/Tobi_box/box/var/config.json
```

- [ ] Die Ausgabe zeigt `"typ": "serie"` und `"serie": "5e1a0c7d9b31"`. `tobibox status` zeigt
      keine offene Meldung mehr; der HA-Ersatz bestätigt den Lernlauf selbst.

**b) Einzelne Folge lernen**

```bash
tobibox sim learn --serie 5e1a0c7d9b31 --folge folge-02.mp3
```

- [ ] Lege `<UID-NEU-2>` auf.
      **Was du hörst:** Wie in a) (nur `lernen_ende`, keine Überraschung; die Folge beginnt erst nach dem Ton), dann nur die Folge `folge-02.mp3` („Test-Serie, Folge zwei.“). Die Serie spielt
      danach nicht weiter.
- [ ] Prüfe mit `grep -A5 '"<UID-NEU-2>"' ~/Tobi_box/box/var/config.json`: `"typ": "folge"`,
      `"folge": "folge-02.mp3"`.

**c) Abbruch**

```bash
tobibox sim learn --serie 5e1a0c7d9b31
tobibox sim learn-abort
```

- [ ] Du siehst zweimal `{"ok": true}` und hörst zwei Töne (`lernen_beginn`, dann `lernen_ende`).
      `tobibox status` zeigt `Lernmodus: aus`. Auch ein Tobie, den du danach auflegst, ändert
      `config.json` nicht.

**d) Bestehende Zuordnung: nur mit `--ueberschreiben`**

```bash
tobibox sim learn --serie 5e1a0c7d9b31 --folge folge-03.mp3
```

- [ ] Hebe `<UID-NEU>` ab und lege ihn wieder auf (er ist schon zugeordnet). Der Befehl selbst
      ist angenommen; die Ablehnung zeigt sich erst beim Auflegen.
      **Was du hörst:** Erst den Ende-Ton `lernen_ende` ganz, dann (sobald der HA-Ersatz abgelehnt hat,
      also sofort) spielt seine bisherige Serie, ohne den Ton `unbekannt` (Entscheidung H, 07.11.). Der Ton
      und die Serie überlappen sich nicht (Entscheidung L, 09.11.).
      Die Ablehnung steht nur im Protokoll.
      **Was du siehst:** Im Protokoll eine WARNING-Zeile mit Baustein `ha_ersatz`, Ereignis
      `zuordnung`, Ergebnis `abgelehnt`, Grund `schon_zugeordnet` und dem Hinweis
      „schon zugeordnet und bleibt, wie er ist“. `config.json` bleibt bei `test-serie`.

```bash
grep '"ereignis":"zuordnung"' ~/Tobi_box/box/var/log/tobibox.log | tail -n 1
```

```bash
tobibox sim learn --serie 5e1a0c7d9b31 --folge folge-03.mp3 --ueberschreiben
```

- [ ] Hebe `<UID-NEU>` ab und lege ihn wieder auf.
      **Was du hörst:** Den Ende-Ton „Lernmodus beendet.“ bis zum Ende, danach erst die Folge `folge-03.mp3`
      („Test-Serie, Folge drei.“); nicht gleichzeitig (Entscheidung L, 09.11.).
      `grep -A5 '"<UID-NEU>"' ~/Tobi_box/box/var/config.json` zeigt `"folge": "folge-03.mp3"`.

### 12.7 Status-Karte

Notiere vorher die Zuordnung der NTAG-Karte, damit du sie in Schritt 12.8 zurücksetzen kannst.
Ist die Karte noch nie zugeordnet, gibt der Befehl nichts aus, und es gibt nichts zurückzusetzen:

```bash
grep -A5 '"<UID-KARTE>"' ~/Tobi_box/box/var/config.json
```

Ordne die Karte als Aktion zu (hebe die Karte vorher ab, falls sie liegt):

```bash
tobibox sim card <UID-KARTE> --aktion status
```

- [ ] Du siehst `{"ok": true}`, Exit-Code 0. Lege die Karte auf.
      **Was du hörst:** Vier Sätze in dieser Reihenfolge: „Leser: Simulation.“ (am echten Leser:
      „Leser in Ordnung.“), „Medien in Ordnung.“, „Netz: Fehler.“, „Speicher in Ordnung.“
      Es startet keine Wiedergabe. Mit den Piepsern hörst du stattdessen hoch (in Ordnung) oder
      tief (Fehler): hoch, hoch, **tief**, hoch.
- [ ] **Netz ist in Stufe 2 immer tief.** Der Prüfpunkt Netz verlangt ein Netz (Heim oder Hotspot)
      und einen verbundenen Broker. Den Broker gibt es erst mit MQTT (Stufe 3a). „Netz: Fehler.“ (mit Piepsern der
      tiefe Ton) ist also richtig.
- [ ] Prüfe mit `tobibox status`: Die Zeile `Status-Karte:` zeigt `leser ok, medien ok, netz FEHLER,
      speicher ok`. Darunter steht `netz: offline, Broker nicht verbunden`.

### 12.8 Karte zurück auf die Folge

Setze die Karte auf die Zuordnung zurück, die du in Schritt 12.7 notiert hast. Das Beispiel
ist die Folge `folge-02.mp3` aus `test-serie` (hebe die Karte vorher ab):

```bash
tobibox sim card <UID-KARTE> --serie 5e1a0c7d9b31 --folge folge-02.mp3
```

- [ ] Lege die Karte auf.
      **Was du hörst:** „Test-Serie, Folge zwei.“ von vorn.

## Simulations-Oberfläche im Browser (AP 4.9)

Eine kleine Seite im Browser, mit der du alle Eingaben der fertigen Box per Mausklick simulierst: Tasten, Drehregler,
Kopfhörer, Ladegerät, Akku, Netz und Tobies. Sie zeigt dazu, was die Box gerade tut. Die Seite ist ein weiterer Client
von `sim.sock`, genau wie `tobibox sim`. Sie ersetzt nichts: Ein echter NFC-Leser funktioniert parallel weiter, und die
Box selbst ändert sich durch die Seite nicht.

### Starten

Der Dienst läuft (Abschnitt 7). In einem zweiten Terminal:

```bash
cd ~/Tobi_box && source .venv/bin/activate
tobibox gui
```

`tobibox gui` öffnet `http://127.0.0.1:8765` im Browser. Beenden mit `Ctrl+C`. Der Server hört nur auf dem eigenen Mac
(`127.0.0.1`), nicht im Netz. Der Dienst muss beim Start der Seite noch nicht laufen: Die Seite zeigt „Dienst nicht
erreichbar“ und verbindet sich von selbst. Mit `--port 9000` wählst du einen anderen Port, mit `--kein-browser` öffnet
sich kein Browserfenster. Wie bei `tobibox status` gilt die Konfiguration aus `--config`, `$TOBIBOX_CONFIG` oder
`./tobibox.toml`.

### Was die Seite zeigt und kann

- **LED-Ring:** 40 Punkte aus dem Ring-Zustand des Dienstes (läuft, Pause, Akku, unbekannte Karte, Aufwachen; nach Plan 5.5.2, dazu
  Lernmodus und Gute Nacht). Der Umschalter an der Karte wählt die Darstellung (die Wahl merkt sich der Browser):
  **echt** (Vorgabe) zeichnet jede LED mit ihrer wirksamen Helligkeit relativ zum Deckel (25 % = volle Farbe, Wahrnehmungskurve
  (h/25)^(1/2,2)) auf dunklem Grund, sodass Atmen, Pulsieren, Ein-/Ausblenden und Überblendungen zu sehen sind; **Farben voll**
  zeigt die Farbe normiert mit voller Deckkraft. Die echte Helligkeit der Box (höchstens 25 %) steht in beiden Fällen als Zahl und im
  Helligkeitsbalken, die Marke im Balken ist der Deckel. Der Ring wird etwa alle 100 ms geholt (`/api/ring`), der Rest der Seite alle 300 ms. Dieselbe Zeile steht im Terminal des Dienstes, und das Protokoll nennt jeden Wechsel (`led`/`ring`).
  Solange der Dienst keinen Ring meldet, steht dort ein grauer Ring mit „Ring noch nicht verdrahtet“.
- **Tasten:** Hauptknopf kurz, Hauptknopf lang, Zurück, Vor.
- **Drehregler:** „− Raste“ und „+ Raste“ (eine Raste sind 2 Prozentpunkte), dazu die Lautstärke und die wirksame Grenze.
- **Schalter:** Kopfhörer eingesteckt, zwei Strom-Haken (je Quelle einer: „Strom am Eingang (pisugar-server)“ und „Strom am Eingang (Leser …)“), Akku 0 bis 100 %, Netz (Heim, Hotspot, Offline; nie die echten
  Namen deiner WLANs).
- **Tobies:** alle zugeordneten Tobies aus `config.json` mit Name (Feld `name`, sonst die Kennung) und Ziel, je mit
  „auflegen“ und „abheben“. Dazu „Unbekannter Tobie (neue Zufallskennung)“ und „Gesperrter Tonie“. Die Marke „simuliert“
  oder „echt“ sagt, ob der liegende Tobie von der Seite oder vom Leser kommt.
- **Uhr:** zeigt die Wanduhr des Dienstes (Ortszeit des Browsers). Ein Feld für Datum und Uhrzeit mit „Uhr stellen“ (`sim time <ISO>`),
  „echte Uhr“ (`sim time now`) und die Schnellknöpfe „heute 20:00“ und „heute 22:00“ für die Leise-Zeiten. Die Uhrzeit ohne Zone gilt als
  Ortszeit des Browsers und geht mit deren Offset an den Dienst. Wie die anderen Eingänge ist die Karte grau, wenn die Quelle nicht `sim` ist.
- **Lernmodus und Meldungen:** Serie und Folge wählen, „Lernmodus starten“ (`sim learn`), „Abbrechen“ (`sim learn-abort`),
  „bestätigen“ für jede offene Meldung (`sim ack`).
- **Zustand:** Serie, Folge, Track, Position, Sitzung, Lautstärke und Grenze, Ruhe, Gute Nacht, Netz, Akku, letzter Fehler
  und die letzten Protokollzeilen (nur bei `[protokoll] ziel = "datei"`).

Eingänge, die der Dienst noch nicht kennt, sind grau mit dem Hinweis „in der Box noch nicht verdrahtet“ (siehe Tabelle
unten). Sie bekommen später ohne Änderung der Seite Leben.

**Nur Eingänge mit Quelle `sim` (seit Rev. 3.17, Befund B9).** Die Seite und `tobibox sim` bedienen nur Eingänge, deren Quelle in
`tobibox.toml` `sim` ist: Tasten und Regler (`[tasten] quelle`), Kopfhörer (`[kopfhoerer] quelle`), Ladegerät und Akku (`[strom]`
fehlt oder `quelle = "sim"`), Netz (`[netz]` fehlt oder `quelle = "sim"`), Uhrzeit (`sim time`: nur, wenn `[netz]` und `[strom]` nicht
an echter Hardware hängen und die Systemuhr nicht von NTP abhängt) und der HA-Ersatz (`learn`, `ack`, `card`: nur ohne `[mqtt]`).
Auf dem Pi ist das Standard: Dort antwortet `sim` auf diese Eingänge mit `{"ok": false, "fehler": "quelle_nicht_sim"}`, und die Seite
graut die Knöpfe aus. Wer am Pi trotzdem simulieren will, setzt `[sim] erlauben = true`. Die Tobies (`tobie_auflegen` usw.) bleiben
immer erlaubt, damit ein echter Leser am Mac parallel weiterläuft.

### Wie die Tobies funktionieren (simulierter Leser)

Die Seite spielt den Leser. Ihre Ereignisse sind genau die des echten Lesers (`core-interface.md`, 3.1 und Abschnitt 9):

- Jedes „auflegen“ sendet `Aufgelegt` (oder `Gesperrt`) mit einer **neuen Vorgangs-ID** (8 Zeichen `[0-9a-f]`, zufällig)
  und einer fortlaufenden `seq`.
- Liegt schon ein simulierter Tobie und du legst einen anderen auf, kommt wie beim echten Leser erst `Abgehoben`
  (mit der alten ID), dann `Aufgelegt` (mit neuer ID).
- Legst du **denselben** Tobie noch einmal auf, während er liegt, passiert nichts (`"hinweis": "liegt_schon"`). Das ist
  die Wiedermeldung aus 9.1 und das Entprellen: Ein Tobie liegt oder er liegt nicht.
- „abheben“ sendet `Abgehoben` mit der ID des Auflegens. Ohne simulierten Tobie lehnt `sim` es ab
  (`kein_simulierter_tobie`): Die Seite hebt nie einen Tobie ab, der auf dem echten Leser liegt.
- Liegt ein echter Tobie und du legst einen simulierten auf, ist das ein Tobie-Wechsel wie am echten Leser. Der Leser
  merkt davon nichts und meldet erst bei seinem nächsten Auflegen wieder.
- **Der Leser darf parallel zur Simulation laufen.** Solange ein simulierter Tobie liegt, ignoriert der Dienst alles, was der
  echte Leser über „nichts da“ sagt: Herzschlag ohne Tobie, `HELLO` nach einer Neuverbindung, Leser-Ausfall und ein
  `Abgehoben`. Der simulierte Tobie bleibt liegen, bis du ihn abhebst. Legst du einen **echten** Tobie auf den Leser,
  gilt der echte (wie ein Wechsel), und die Simulation hat danach nichts mehr aufgelegt. Hebst du ihn wieder ab, gilt der
  Leser wie ohne Simulation. Ohne simulierten Tobie ändert sich nichts: Dann zählt der Leser allein (CUJ 13, Entscheidung K).
  Das filtert die Schale (`app.py`); der Kern bleibt rein und kennt die Herkunft eines Ereignisses nicht.

### Die Socket-Befehle (Format seit AP 4.9)

Jede Zeile auf `sim.sock` ist ein JSON-Objekt mit dem Schlüssel `befehl` und wird mit einer JSON-Zeile beantwortet:
`{"ok": true, …}` oder `{"ok": false, "fehler": "…"}`. Die Namen sind fest; AP 4.8 und AP 3.7 ändern sie nicht (AP 4.8 ergänzt nur `zeit`).

| Befehl | Felder | Wirkung (Ereignis) | Heute |
|---|---|---|---|
| `taste` | `taste`: `hauptknopf_kurz`, `hauptknopf_lang`, `weiter`, `zurueck` | `Hauptknopf("kurz")`, `Hauptknopf("lang")`, `Weiter`, `Zurueck` | wirkt seit AP 4.8 (`tobibox sim key haupt\|haupt-lang\|vor\|zurueck`); `hauptknopf_lang` fährt herunter (am Mac nur protokolliert) |
| `regler` | `delta`: ganze Zahl, nicht 0, höchstens 20 in Betrag (Prozentpunkte) | `LautstaerkeDrehen(delta)` über `Bedienung` wie der echte Drehregler (seit B14: „lauter“ über der Grenze sendet nichts, der Wunsch bleibt) | wirkt (der Kern klemmt an der Grenze); `tobibox sim knob +N\|-N` dreht N Rasten zu je 2 Prozentpunkten (höchstens 10) |
| `kopfhoerer` | `steckt`: `true` oder `false` | `Kopfhoerer(steckt)` | wirkt (Grenze und Ausgang der Sitzung); `tobibox sim headphones on\|off`. Mit `[kopfhoerer] quelle = "sim"` (Vorgabe) stellt `sim` den simulierten Schaltkontakt, und die `Buchse` meldet; bei `gpio` kommt der Stecker von der echten Buchse |
| `zeit` | `iso`: Zeitpunkt in ISO 8601 (ohne Zone: Ortszeit des Rechners) oder `null` | stellt die Wanduhr des Dienstes (kein Ereignis); Antwort `{"ok": true, "wall": …}` | wirkt seit AP 4.8 (`tobibox sim time <ISO>\|now`), für die Leise-Zeiten. Die Uhr läuft von dort weiter, Timer und Fristen bleiben unberührt |
| `strom` | `lader`: bool und/oder `akku`: 0 bis 100; optional `quelle`: `pisugar` (Vorgabe) oder `leser` (nur mit `lader`, Ein/Aus Schritt 1: wie die Zeile `LADER`, Vorrang bei Widerspruch; `tobibox sim power --charger on --source leser`) | `LaderGeaendert` (mit `quelle`), `AkkuStand` | wirkt seit AP 3.7 (`tobibox sim power --charger on\|off --battery N`); mit `[strom] quelle = "sim"` stellt `sim` den Treiber ein und `power` meldet, sonst gibt `sim` die Ereignisse selbst aus |
| `netz` | `klasse`: `home`, `hotspot`, `offline` | `NetzKlasse(klasse)` | wirkt seit AP 3.7 (`tobibox sim net home\|hotspot\|offline`); mit `[netz] quelle = "sim"` setzt `sim` das simulierte WLAN (Namen aus `heim_ssid`/`hotspot_ssid`, sonst `sim-heim`/`sim-hotspot`) und `net` klassifiziert, sonst gibt `sim` das Ereignis selbst aus |
| `tobie_auflegen` | `uid` (Kennung wie in `config.json`) oder `"zufall": true` | `Aufgelegt` (vorher `Abgehoben`, wenn schon einer liegt); Antwort mit `uid` und `vorgang` | wirkt |
| `tobie_gesperrt` | – | `Gesperrt` (vorher `Abgehoben`, wenn schon einer liegt) | wirkt |
| `tobie_abheben` | – | `Abgehoben` mit der ID des simulierten Tobies | wirkt |
| `anzeige` | – | kein Ereignis; Antwort: `status` (Status-JSON), `offen`, `anzeige` (Lautstärke, Grenze, Position, Kopfhörer, Ruhe, Gute Nacht, liegender Tobie `figur`, `ring`), `verdrahtet`, `simuliert` | wirkt |
| `learn`, `learn_abort`, `ack`, `card`, `status` | wie bisher (siehe `tobibox sim`) | wie bisher | wirkt |

Regeln:

- Ist die Quelle des Eingangs nicht `sim` (und `[sim] erlauben` nicht gesetzt), lautet die Antwort `{"ok": false, "fehler": "quelle_nicht_sim"}`
  und es entsteht kein Ereignis. Die Antwort auf `anzeige` nennt das Feld `quelle_sim` (Eingang → `true`/`false`; Namen wie in `verdrahtet`
  und `zeit`, `ha`), daran graut die Seite die Knöpfe aus (B9).
- `zeit` nimmt nur Jahre von 2000 bis 2100 an; alles andere (und jeder Fehler beim Umrechnen) ist `{"ok": false, "fehler": "iso ungueltig"}`
  (B8). Die Verbindung bleibt offen; ein unerwarteter Fehler wird mit `{"ok": false, "fehler": "intern"}` beantwortet.
- Ungültige Felder lehnt `sim` immer mit `{"ok": false, "fehler": "<Feld> ungueltig"}` ab, auch wenn der Eingang noch
  nicht verdrahtet ist. Danach erst kommt die Prüfung der Verdrahtung.
- Ist ein Eingang noch nicht verdrahtet, lautet die Antwort `{"ok": false, "fehler": "noch_nicht_verdrahtet"}`, und es
  entsteht kein Ereignis. Die Tabelle `VERDRAHTET` in `box/src/tobibox/sim.py` hält fest, welche Eingänge wirken; AP 3.7 hat
  `strom` und `netz` auf `True` gesetzt, AP 4.8 den Rest (heute sind alle `True`). Die Antwort auf `anzeige` nennt sie im Feld `verdrahtet`, daran graut die Seite
  die Knöpfe aus.
- `anzeige.anzeige.figur` ist der Tobie, den der Kern als liegend kennt (`uid` oder `null` bei gesperrt, `vorgang`, `art`).
  Gleicht seine `vorgang` dem Feld `simuliert.vorgang`, kommt er von der Seite („simuliert“), sonst vom Leser („echt“).
- `anzeige.anzeige.ring`: `null` oder `{"farben": [...40 Farben...], "helligkeit": <0 bis 100>}`; eine Farbe ist `"#rrggbb"`
  oder `[r, g, b]`. Das Feld füllt der Dienst seit AP 4.8 aus `led`; dazu kommen `zustand`, `deckel` (25) und `leds` (dieselben Farben wie `farben`).
- `tobibox gui` leitet nur diese Befehle weiter: `taste`, `regler`, `kopfhoerer`, `strom`, `netz`, `tobie_auflegen`,
  `tobie_gesperrt`, `tobie_abheben`, `learn`, `learn_abort`, `ack`. `card` und `status` bleiben bei `tobibox sim`.

### Die HTTP-Schnittstelle der Seite

| Aufruf | Antwort |
|---|---|
| `GET /` | die Seite |
| `GET /api/anzeige` | alles für die Anzeige: `dienst` (`laeuft`, `nicht_erreichbar`, `keine_berechtigung`), `status`, `anzeige`, `offen`, `verdrahtet`, `simuliert`, `tobies`, `serien`, `protokoll` |
| `POST /api/befehl` | Körper: eine Zeile wie oben (`Content-Type: application/json`); Antwort: die Antwort des Dienstes. Nicht erlaubter Befehl: 400; Dienst nicht erreichbar: 503 |

Die Seite fragt `/api/anzeige` alle 300 ms. Der Server prüft `Host` und `Origin`, damit keine fremde Webseite in deinem
Browser Tobies auflegen kann.

## 13. Abnahme Stufe 3a und 4

Diese Liste führt die Punkte von „Abnahme Stufe 3a“ und „Abnahme Stufe 4“ aus `docs/designs/box-software.md`
in konkrete Schritte über, soweit sie am Mac ohne NAS, ohne Home Assistant und ohne Pi gehen: Tasten und
Drehregler (CUJ 19), Kopfhörer (CUJ 17), Gute Nacht (CUJ 14), Leise-Zeiten (CUJ 15), Lesezeichen mit Ablauf
(Entscheidung N), Netz und Akku, Herunterfahren und Leerlauf (CUJ 16, Entscheidung O) und der LED-Ring (CUJ 18).
Alle Punkte aus Abschnitt 11 und 12 gelten weiter. Vermerke Datum und Ergebnis neben jedem Haken.

Du bedienst die Box fast nur über die Simulations-Oberfläche (Abschnitt „Simulations-Oberfläche im Browser“)
und `tobibox sim …`. Beide sprechen mit dem Dienst über `sim.sock`. Der Dienst weiß dabei nicht, dass die
Eingaben simuliert sind: Er verhält sich wie am Pi, nur das Herunterfahren wird am Mac bloß protokolliert.

**Drei Terminals.** A: der Dienst (`tobiboxd`). B: die Oberfläche (`tobibox gui`, Browser auf
`http://127.0.0.1:8765`). C: Befehle und Protokoll. In jedem Terminal einmal `cd ~/Tobi_box && source .venv/bin/activate`.
In Terminal C (und B) außerdem:

```bash
export TOBIBOX_CONFIG=~/Tobi_box/box/config/tobibox.toml
LOG=~/Tobi_box/box/var/log/tobibox.log
```

Ab hier steht `"$LOG"` für das Protokoll. In einem neuen Terminal beide Zeilen wiederholen.

**Wie du Schritte schneller machst.** Die Karte **Uhr** in der Oberfläche (oder `tobibox sim time`) stellt nur die **Wanduhr** (für Leise-Zeiten und Lesezeichen).
Timer und Fristen laufen auf der monotonen Uhr und lassen sich nicht vorspulen: der Gute-Nacht-Timer, das Ausblenden
und der Leerlauf von 10 Minuten (ohne Strom, seit Ein/Aus Schritt 1). Dafür gibt es zwei Auswege: In 13.1 stellst du den Gute-Nacht-Timer auf 1 Minute und das
Ausblenden auf 5 Sekunden, und in 13.8 gibt es einen Kurzstart mit 30 Sekunden Leerlauf.

**Die Tobies in diesem Abschnitt.** Du brauchst keine echten Tobies. In der Oberfläche legst du simulierte auf
(Karte „Tobies“, Knopf „auflegen“ und „abheben“). Ich nenne sie so, die Kennungen sind erfunden und stören
deine echten Tobies nicht:

| Name | Kennung | Ziel |
|---|---|---|
| Lange Serie | `04130001` | Serie `lange-serie` (ID `7b3f2a6e8c14`), Folgen zu je 90 s |
| Track-Tobie | `04130002` | Folge `folge-01` der Serie `track-test` (ID `9d4c1e5a2f68`), drei Tracks zu je 8 s |
| Gute-Nacht-Karte | `04130003` | Aktion `gute_nacht` |

**Der echte Leser darf mitlaufen.** Liegt nichts auf ihm, meldet er „nichts liegt“. Das hebt einen simulierten Tobie
**nicht** ab: Er bleibt liegen, bis du ihn in der Oberfläche abhebst oder ein echter Tobie auf dem Leser erkannt wird (dann
gilt der echte). Du lässt die Zeile `geraet` also unverändert. Ist **kein** Leser angeschlossen, stellst du `geraet = "sim"` ein
(13.1); dann zeigt die Status-Karte den Leser als „simulation“. Willst du mit einem echten Tobie prüfen, legst du ihn statt
„auflegen“ auf den Leser, nachdem du ihn mit `tobibox sim card <UID> --serie <ID>` zugeordnet hast.

**Nach einem Neustart des Dienstes** gilt Entscheidung G (wie 12.4): Lag beim Beenden ein Tobie auf, startet derselbe Tobie beim
ersten Auflegen **nicht** von selbst (Protokoll `dienst_neustart`, Sitzung „pausiert“). Dann Hauptknopf kurz drücken.

### 13.1 Vorbereitung

**Stand holen und installieren.** Seit Stufe 3a hängt der Dienst von `paho-mqtt` ab, die Installation muss also noch einmal laufen:

```bash
cd ~/Tobi_box && git pull
source .venv/bin/activate
pip install -e "box[test]"
tobibox --version
```

- [ ] `tobibox --version` zeigt `tobibox 0.1.0`. `tobibox sim -h` nennt unter anderem `power`, `net`, `key`, `knob`, `headphones` und `time`.

**Konfiguration.** Änderungen an `~/Tobi_box/box/config/tobibox.toml`. Der erste Befehl legt eine Sicherung
`tobibox.toml.vor-13` an (zum Zurückkehren, 13.11) und stellt die Protokollstufe auf `DEBUG`
(damit die Töne und der Leerlauf-Zähler im Protokoll stehen). Der echte Leser darf angeschlossen bleiben, die Zeile `geraet`
bleibt, wie sie ist:

```bash
cd ~/Tobi_box/box/config
sed -i.vor-13 -e 's|^ebene = "INFO"|ebene = "DEBUG"|' tobibox.toml
grep -n '^\[' tobibox.toml
```

Ist **kein** Leser angeschlossen, stelle zusätzlich `geraet = "sim"` ein
(`sed -i -e 's|^geraet = .*|geraet = "sim"|' tobibox.toml`); sonst meldet der Dienst dauernd einen Leser-Ausfall.

Die letzte Zeile listet die Abschnitte, die schon aktiv sind. `[strom]` und `[netz]` (beide mit `quelle = "sim"`) stehen in der
Beispieldatei `tobibox.mac.example.toml` schon drin; ohne sie gäbe es weder einen Tiefstand-Alarm noch eine Netz-Klasse im Dienst.
Stehen sie in **deiner** `tobibox.toml` (angelegt aus einer älteren Beispieldatei) **noch nicht** dabei, hänge sie an:

```bash
cat >> ~/Tobi_box/box/config/tobibox.toml <<'EOF'

[strom]
quelle = "sim"

[netz]
quelle = "sim"
EOF
```

`[sim] erlauben = true` brauchst du am Mac **nicht**: Alle Eingänge haben die Quelle `sim` (Vorgabe), also bedient die
Oberfläche sie ohne diese Zeile. Siehst du später einen grauen Knopf oder die Antwort `quelle_nicht_sim`, hat ein Eingang eine andere
Quelle; erst dann hilft die Zeile (Abschnitt „Nur Eingänge mit Quelle `sim`“). Für `[uhr]` gilt dasselbe: Am Mac ist die Systemuhr immer sicher.

**Gute-Nacht-Zeiten und Hilfsskript.** Die Einstellungen für Gute Nacht und die Leise-Zeiten kommen in Stufe 3a aus Home
Assistant. Ohne HA schreibst du sie in `config.json`. Mit Home Assistant geht es anders, siehe „Mit Home Assistant statt Hilfsskript“ nach 13.10. Ohne HA dafür ein kleines Hilfsskript, das **nicht im Repo** liegt
(`~/tobibox-mpd/config13.py`). Es ändert nur `gute_nacht` und `leise_zeiten`, legt vorher eine Sicherung
`config.json.vor-13` an und arbeitet nur, wenn der Dienst **nicht** läuft:

```bash
mkdir -p ~/tobibox-mpd
cat > ~/tobibox-mpd/config13.py <<'PY'
import json, os, sys

modus = sys.argv[1] if len(sys.argv) > 1 else ""
if modus not in ("test", "leise", "normal"):
    sys.exit("Aufruf: python3 config13.py test|leise|normal")
ordner = os.path.expanduser("~/Tobi_box/box/var")
if os.path.exists(os.path.join(ordner, "sim.sock")):
    sys.exit("Der Dienst läuft noch. Erst mit Ctrl+C beenden.")
pfad = os.path.join(ordner, "config.json")
sicherung = pfad + ".vor-13"
with open(pfad, encoding="utf-8") as f:
    k = json.load(f)
if not os.path.exists(sicherung):
    with open(sicherung, "w", encoding="utf-8") as f:
        json.dump(k, f, indent=2, ensure_ascii=False)
        f.write("\n")
if modus == "normal":  # zurück auf den Stand vor Abschnitt 13
    with open(sicherung, encoding="utf-8") as f:
        alt = json.load(f)
    k["gute_nacht"], k["leise_zeiten"] = alt["gute_nacht"], alt["leise_zeiten"]
else:
    k["gute_nacht"] = {"timer_min": 1, "ausblenden_s": 5}  # Timer 1 Minute, Ausblenden 5 Sekunden
    fenster = []
    if modus == "leise":
        fenster = [
            {"id": "abend", "tage": [1, 2, 3, 4, 5, 6, 7], "von": "19:30", "bis": "21:00", "wirkung": "leiser", "grenze": 15},
            {"id": "nacht", "tage": [1, 2, 3, 4, 5, 6, 7], "von": "21:00", "bis": "06:30", "wirkung": "stumm"},
        ]
    k["leise_zeiten"] = {"zeitzone": "Europe/Berlin", "fenster": fenster}
with open(pfad, "w", encoding="utf-8") as f:
    json.dump(k, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("config.json:", modus, "- Gute Nacht", k["gute_nacht"], "- Leise-Fenster:", len(k["leise_zeiten"]["fenster"]))
PY
python3 ~/tobibox-mpd/config13.py test
```

- [ ] Die letzte Zeile meldet `config.json: test - Gute Nacht {'timer_min': 1, 'ausblenden_s': 5} - Leise-Fenster: 0`.
      (Meldet es „Der Dienst läuft noch“, beende den Dienst. Gibt es `config.json` noch nicht, hast du Abschnitt 6 übersprungen.)

**Dienst und Oberfläche starten.** MPD läuft (Schritt 4.4). Terminal A:

```bash
tobiboxd --config ~/Tobi_box/box/config/tobibox.toml
```

Terminal B:

```bash
tobibox gui
```

- [ ] Im Browser steht oben „Dienst läuft“. **Was du hörst:** „Tobi Box ist bereit.“ **Was du siehst:** Der Ring läuft 2 s als weißes
      Lauflicht (Aufwachen), danach ist er aus (nichts liegt). Alle Knöpfe sind bedienbar, keiner ist grau.
- [ ] Terminal C: `tobibox status` zeigt in der Zeile `HA:` auch `Netz: offline; Akku: unbekannt, Lader unbekannt`.

Jetzt die drei Tobies zuordnen (Terminal C). Die Antwort ist jedes Mal `{"ok": true}`:

```bash
tobibox sim card 04130001 --serie 7b3f2a6e8c14
tobibox sim card 04130002 --serie 9d4c1e5a2f68 --folge folge-01
tobibox sim card 04130003 --aktion gute_nacht
```

- [ ] In der Oberfläche stehen die drei Kennungen in der Karte „Tobies“, mit den Zielen „Lange Serie“,
      „Track-Test, Folge folge-01“ und „Gute-Nacht-Karte“.

### 13.2 Tasten und Drehregler (CUJ 19)

Die Tasten sind in der Oberfläche die Knöpfe der Karte „Tasten“, am Terminal `tobibox sim key haupt|vor|zurueck`.
Der Drehregler ist „− Raste“ und „+ Raste“ (je 2 Prozentpunkte) oder `tobibox sim knob +N|-N`. Die Lautstärke siehst du
in der Karte „Drehregler“ und am MPD:

```bash
(printf 'status\n'; sleep 1) | nc localhost 6600 | grep volume
```

**Hauptknopf kurz.** Lege `04130001` („Lange Serie“) auf.

- [ ] **Was du hörst:** „Lange Serie, Folge …“, danach die Ansage der Sekunden. **Was du siehst:** Sitzung „spielt“, der Ring
      atmet grün.
- [ ] „Hauptknopf kurz“ (oder `tobibox sim key haupt`): Die Wiedergabe hält an, Sitzung „pausiert“, der Ring ist bernstein und geht nach 10 s aus.
      Noch einmal drücken: Es läuft etwa 3 s vor der Stelle weiter, an der es hielt (Rücksprung wie in 12.2).
      Im Protokoll stehen zwei Zeilen mit `Hauptknopf`:

```bash
grep -E '"ereignis":"(Hauptknopf|Weiter|Zurueck)"' "$LOG" | tail -n 4
```

**Vor und Zurück.** Hebe `04130001` ab („abheben“) und lege `04130002` („Track-Tobie“) auf.

- [ ] **Was du hörst:** „Track eins von drei.“ In der Karte „Was gerade läuft“ steht „Track 1“.
- [ ] „Vor »“ (oder `tobibox sim key vor`): „Track zwei von drei.“ Noch einmal: „Track drei von drei.“
- [ ] Ein drittes „Vor“ am letzten Track eines Folgen-Tobies tut nichts außer dem leisen Hinweiston (nur ein Klang, keine Sprache). Der Track läuft weiter. Im Protokoll: `grep '"ton":"hinweis"' "$LOG" | tail -n 1`.
- [ ] „Zurück“, **nachdem** der Track mehr als 3 s gelaufen ist: Der Track beginnt von vorn („Track drei von drei.“).
      „Zurück“ innerhalb der ersten 3 s eines Tracks: der vorige Track („Track zwei von drei.“). Im ersten Track beginnt „Zurück“ immer diesen Track von vorn.

**Drehregler und Grenze.** Hebe den Track-Tobie ab, lege `04130001` auf. Die Lautstärke beginnt bei 20, die Grenze ist 40
(`max` in `[lautstaerke]`).

- [ ] „+ Raste“ zwei Mal: Die Lautstärke steigt auf 24. Der MPD-Befehl oben zeigt `volume: 24`.
- [ ] `tobibox sim knob +10` zwei Mal (je 20 Prozentpunkte): Die Lautstärke bleibt bei **40**, der Grenze, nicht darüber. Noch ein
      `tobibox sim knob +5`: bleibt 40. Danach „− Raste“: sofort **38**, nicht tiefer. Das „Lauter“ über der Grenze merkt sich die Box nicht.
- [ ] `tobibox sim knob -10`: Die Lautstärke sinkt um 20 Punkte. Der Ring zeigt weiter Grün; er ändert sich bei der Lautstärke nicht.

**Hauptknopf lang** fährt die Box herunter und kommt in 13.8.

### 13.3 Kopfhörer (CUJ 17)

`04130001` spielt. Drehe zuerst an die Grenze: `tobibox sim knob +10`, zwei Mal (Lautstärke 40). Die Kopfhörer-Grenze ist
`kopfhoerer = 30` in `[lautstaerke]`.

- [ ] Kreuze in der Oberfläche „Kopfhörer eingesteckt“ an (oder `tobibox sim headphones on`). **Was du siehst:** Die Lautstärke fällt
      sofort auf 30, unter „Wirksame Grenze“ steht `30 % (global 40 %, kopfhoerer 30 %)`, und der MPD-Befehl aus 13.2 zeigt
      `volume: 30`. Die Wiedergabe läuft weiter.
- [ ] „+ Raste“: Die Lautstärke bleibt bei 30.
- [ ] Nimm den Haken wieder weg (`tobibox sim headphones off`): Die Lautstärke geht zurück auf **40**, den Wunsch von vorher.
- [ ] Im Protokoll stehen der Stecker und der Ausgang. Am Mac hat der Ausgangswechsel keine Wirkung (die Zeile sagt es):

```bash
grep -E '"baustein":"(headphones|player)","ereignis":"(kopfhoerer|ausgang)"' "$LOG" | tail -n 4
```

      **Was du siehst:** `kopfhoerer` mit Ergebnis `steckt` und `ausgang` mit Ergebnis `ohne_wirkung` (`"ausgang":"kopfhoerer"`), später
      `gezogen` und `"ausgang":"lautsprecher"`.

**Entscheidung P (Kontakt nicht lesbar).** Das lässt sich am Mac nicht nachstellen: Der simulierte Kontakt ist immer lesbar. Siehe 13.12.

### 13.4 Gute Nacht (CUJ 14)

Timer 1 Minute, Ausblenden 5 Sekunden (13.1). Die Folge soll beim Start der Gute-Nacht-Karte mindestens 70 s vor sich haben,
darum beginnst du den Track neu.

- [ ] Lege `04130001` auf, warte 5 s und drücke „Zurück“ (der Track beginnt von vorn). Hebe den Tobie ab (Pause).
- [ ] Lege die Gute-Nacht-Karte `04130003` auf.
      **Was du siehst:** Keine Wiedergabe (die Karte startet nur den Timer). In der Karte „Zustand“ steht „Gute Nacht: Timer läuft“.
- [ ] Hebe die Karte ab und lege `04130001` wieder auf.
      **Was du hörst/siehst:** Die Folge läuft weiter. Der Ring glimmt warm orange und dunkel (nicht grün).
- [ ] Nach etwa 60 s beginnt das Ausblenden: Die Lautstärke sinkt 5 s lang (in „Wirksame Grenze“ erscheint `gute_nacht` mit fallendem
      Wert, in „Zustand“ steht „Gute Nacht: blendet aus“), dann hält die Wiedergabe an. Sitzung „pausiert“, „Gute Nacht: aus“, der Ring ist
      bernstein und geht nach 10 s aus. Die Lautstärke steht wieder auf dem Wert von vorher.

```bash
grep -E '"baustein":"bedtime"' "$LOG" | tail -n 4
grep '"ereignis":"zeiger_gespeichert"' "$LOG" | tail -n 1
```

      **Was du siehst:** `gute_nacht` mit den Ergebnissen `gestartet` (`timer_min` 1), `ausblenden_beginnt` (`dauer_s` 5) und `ende`. Danach ein
      `zeiger_gespeichert` mit Grund `pause`.
- [ ] Lege den Tobie ab und wieder auf: Die Folge geht an der gespeicherten Stelle weiter.

### 13.5 Leise-Zeiten: leiser und stumm (CUJ 15)

Die Fenster stehen in `config.json` und lesen sich beim Start. Dienst in Terminal A beenden (`Ctrl+C`), dann in Terminal C:

```bash
python3 ~/tobibox-mpd/config13.py leise
```

Es gibt zwei Fenster, jeden Tag: 19:30 bis 21:00 „leiser“ mit Grenze 15 und 21:00 bis 06:30 „stumm“. Dienst wieder starten (Zeile
`tobiboxd …` aus 13.1). Lege `04130001` auf (Hauptknopf kurz, falls er nur pausiert) und drehe auf etwa 30 (`tobibox sim knob +5`).
Die Uhrzeit stellst du zuerst in der Karte **Uhr** (Feld für Datum und Uhrzeit, dann „Uhr stellen“). Zweiter Weg: der Befehl `tobibox sim time` (ISO 8601 mit Zone; im November gilt `+01:00`):

```bash
tobibox sim time 2026-11-10T19:45:00+01:00
```

- [ ] Die Antwort enthält `"ok": true` und eine Zahl `wall`. **Was du hörst/siehst:** Innerhalb weniger Sekunden sinkt die Lautstärke weich (3 s)
      auf 15. „Ruhe: leiser“, „Wirksame Grenze: 15 %“ mit `leise_zeit 15`.

Zuerst die Karte Uhr (10.11.2026, 22:00, „Uhr stellen“). Zweiter Weg:

```bash
tobibox sim time 2026-11-10T22:00:00+01:00
```

- [ ] **Was du hörst/siehst:** Die Lautstärke wird weich ausgeblendet, dann hält die Wiedergabe an. „Ruhe: stumm“, Sitzung „gehalten (stumm)“.
      Der Ring leuchtet ganz dunkel rot und geht nach 5 s aus (Pause wegen „stumm“).
- [ ] Hebe den Tobie ab und lege ihn wieder auf. **Was du hörst:** Nur ein kurzer, leiser Klang (keine Sprache), keine Wiedergabe. Der Ring leuchtet dabei kurz ganz dunkel rot.
- [ ] Zum Ende des Fensters stellst du in der Karte Uhr 11.11.2026, 07:00 („Uhr stellen“). Zweiter Weg:

```bash
tobibox sim time 2026-11-11T07:00:00+01:00
```

      **Was du siehst:** „Ruhe: normal“. Es startet **nichts** von selbst (Entscheidung B): Der Tobie muss erneut aufgelegt werden.

```bash
grep -E '"baustein":"quiet"' "$LOG" | tail -n 4
```

      **Was du siehst:** `ruhe` mit den Ergebnissen `leiser` (`"grenze":15`), `stumm` und `normal`.
- [ ] Setze die echte Uhr zurück: in der Karte Uhr „echte Uhr“, zweiter Weg `tobibox sim time now` (Antwort `"wall": null`).

Wichtig: Die Fenster gelten jetzt auch für die echte Uhrzeit. **Beende den Dienst und nimm sie sofort wieder heraus**, sonst bist du
abends plötzlich „stumm“:

```bash
python3 ~/tobibox-mpd/config13.py test
```

Dienst neu starten.

### 13.6 Lesezeichen mit Ablauf (Entscheidung N)

Ein Zeiger, der länger als `lesezeichen_tage` (Vorgabe 14) nicht benutzt wurde, beginnt die Folge beim Fortsetzen wieder von vorn. Dafür
stellst du die Wanduhr vor, in der Karte Uhr oder mit dem Befehl. Eine kleine Hilfsfunktion liefert den Zeitpunkt in N Tagen (Terminal C):

```bash
tage() { python3 -c "from datetime import datetime, timedelta; print((datetime.now() + timedelta(days=$1)).isoformat(timespec='seconds'))"; }
```

Hebe zuerst alles ab und lege `04130001` auf. Drücke „Hauptknopf kurz“, falls die Box nur „pausiert“ steht, und danach „Zurück“ (die Folge
beginnt von vorn). Lass sie etwa 30 s laufen (bis „Folge …, Sekunde fünfundzwanzig“) und hebe ab. Dabei wird der Zeiger mit Datum gespeichert.
(Hebst du in den letzten 15 s der Folge ab, greift stattdessen die Restregel aus 12.2.)

- [ ] **13 Tage:** Lass dir mit `tage 13` den Zeitpunkt ausgeben und stelle ihn in der Karte Uhr („Uhr stellen“). Zweiter Weg: `tobibox sim time "$(tage 13)"`. Dann `04130001` auflegen. **Was du hörst:** Die Folge läuft an der gespeicherten Stelle weiter,
      etwa bei „Sekunde zwanzig“ bis „fünfundzwanzig“ (3 s Rücksprung). Im Protokoll steht **keine** neue Zeile `lesezeichen_abgelaufen`.
- [ ] Zurück in die Gegenwart und abheben: in der Karte Uhr „echte Uhr“ (zweiter Weg `tobibox sim time now`), dann „abheben“ (so trägt der Zeiger wieder das echte Datum).
- [ ] **15 Tage:** Lass dir mit `tage 15` den Zeitpunkt ausgeben und stelle ihn in der Karte Uhr. Zweiter Weg: `tobibox sim time "$(tage 15)"`. Dann `04130001` auflegen. **Was du hörst:** Dieselbe Folge beginnt von vorn
      („Lange Serie, Folge …“, ohne 3 s Rücksprung). Die Serie springt nicht zurück auf Folge eins.

```bash
grep '"ereignis":"lesezeichen_abgelaufen"' "$LOG" | tail -n 1
```

      **Was du siehst:** `ergebnis` `von_vorn`, `alter_tage` 15.0, `tage` 14.
- [ ] Karte Uhr „echte Uhr“ (zweiter Weg `tobibox sim time now`). Die Uhr läuft wieder echt.

`lesezeichen_tage` selbst (0 bis 365, 0 = läuft nie ab) stellt in Stufe 3a Home Assistant ein; am Mac steht es nicht in `config.json`, es gilt die Vorgabe 14.

### 13.7 Netz und Akku (Anzeigen)

**Netz-Klasse.** Terminal C:

```bash
tobibox sim net home
tobibox status
```

- [ ] `tobibox status` zeigt `Netz: home` (in der Zeile `Leser:` und in der Zeile `HA:`). In der Oberfläche steht in „Zustand“: „Netz: Heim“.
      Dasselbe mit `tobibox sim net hotspot` („Hotspot“) und `tobibox sim net offline` („offline“). Die Knöpfe „Heim“, „Hotspot“ und „Offline“ in der Karte „Schalter“ tun das Gleiche.

```bash
grep -E '"baustein":"net"' "$LOG" | tail -n 3
```

      **Was du siehst:** `netz_klasse` mit dem neuen Ergebnis und dem Feld `vorher`. Die WLAN-Namen sind erfunden (`sim-heim`, `sim-hotspot`).
- [ ] Die Status-Karte meldet „Netz: Fehler“ auch bei `home`: Der Prüfpunkt braucht außerdem einen verbundenen Broker (13.10).

**Vorsicht bei der Messung.** Die erste Strom-Messung nach dem Start gibt keine Rückmeldung. Andocken und Abziehen sind 10 s entprellt (Sperre): Zwischen Haken weg und Haken an mindestens 10 s warten.

**Akku und Lader.** Sobald sich der **Lader** ändert, zeigt der Ring den Akkustand 5 s lang (der Schieber „Akku“ allein zeigt nichts). Hängt Strom an und ist der Akku nicht voll, bleibt danach ein blauer Füllstand stehen (Anstecken: zweimal schnell pulsieren, dann langsam pulsierend).
Alle Befehle antworten `{"ok": true}`:

```bash
tobibox sim power --charger on --battery 60
tobibox sim power --charger off --battery 80
tobibox sim power --charger on --battery 40
tobibox sim power --charger off
tobibox sim power --charger on --battery 15
tobibox sim power --charger off
```

- [ ] Beim ersten Befehl füllt sich der Ring blau (Lader dran) zu 60 %: 24 von 40 Punkten. Beim zweiten grün (über 50 %), 32 Punkte.
      Beim dritten blau, 16 Punkte; beim vierten (nur Lader ab, Akku bleibt 40) gelb, 16 Punkte. Beim fünften blau, beim sechsten rot (unter 20 %), 6 Punkte.
      Bei Lader ab ist die Anzeige nach 5 s wieder weg; bei Lader dran bleibt der blaue Füllstand stehen. In der Oberfläche steht in „Zustand“ der Akku, zum Beispiel „Akku: 15 %“; „, am Lader“ steht nur bei Lader dran.
- [ ] `tobibox status` zeigt in der Zeile `HA:` den Akku: `Akku: 15 %, nicht am Lader` oder `Akku: 15 %, am Lader`.

**Sync-Regel ohne NAS (optional).** Einen echten Sync gibt es am Mac nicht. Die Regel „kein Sync ohne Netz“ kannst du aber sehen. Beende den
Dienst, hänge diesen Abschnitt an `tobibox.toml` an (Platzhalter-Name, kein Zugang) und starte neu:

```bash
cat >> ~/Tobi_box/box/config/tobibox.toml <<'EOF'

[sync]
host = "qnap.example.ts.net"
EOF
```

Dann `tobibox sim net offline` und `tobibox sim power --charger on --battery 70`.

- [ ] `tobibox status` zeigt `Sync: idle, zuletzt …: abgebrochen (regel)`. Im Protokoll: `grep '"baustein":"sync"' "$LOG" | tail -n 1` mit `netz` offline, `lader` true, `akku` 70.
- [ ] Entferne die Zeilen `[sync]` und `host = …` wieder aus der Datei, sonst versucht der Dienst bei Heimnetz und Lader einen echten Sync zu dem Platzhalter-Namen.
      Dienst neu starten.

### 13.8 Herunterfahren und Leerlauf (CUJ 16, Entscheidung O)

Am Mac fährt nichts wirklich herunter. Der Dienst protokolliert es, hält die Wiedergabe an, löscht den Marker `lauf.json` und
kehrt nach 10 s in den normalen Zustand zurück (Zeile `simulation_zurueck`), damit die Simulation benutzbar bleibt. In der
Oberfläche steht in dieser Zeit in „Zustand“ die Sitzung „fährt herunter“, der Ring ist aus.

**a) Hauptknopf lang.** Lege `04130001` auf und lass ihn spielen.

- [ ] „Hauptknopf lang“ (oder `tobibox sim key haupt-lang`). **Was du hörst/siehst:** Die Wiedergabe hält sofort an, der Ring geht aus,
      die Sitzung steht auf „fährt herunter“. Nach etwa 10 s ist die Box wieder „pausiert“, der Ring leuchtet kurz bernstein (der Tobie liegt noch) und geht nach 10 s aus.

```bash
grep '"ereignis":"herunterfahren"' "$LOG" | tail -n 5
```

      **Was du siehst:** In dieser Reihenfolge `angefordert` (Baustein `idle`, `"grund":"hauptknopf"`), `angefordert` (Baustein `app`), `simuliert` (Baustein `power`),
      `simuliert` (Baustein `idle`, `rueckkehr_in_s` 10.0) und nach 10 s `simulation_zurueck`. Der Marker `~/Tobi_box/box/var/lauf.json` wird beim
      Herunterfahren gelöscht und nach der Rückkehr neu geschrieben.
- [ ] Drücke „Hauptknopf kurz“: Die Folge geht an der gespeicherten Stelle weiter.

**b) Akku-Tiefstand und `akku_leer`.** Die Grenze ist `tiefstand_prozent = 5` (nicht am Lader). Lade vorher kurz auf einen guten Wert:

```bash
tobibox sim power --charger off --battery 80
tobibox sim power --battery 4
```

- [ ] **Was du hörst:** „Mein Akku ist fast leer. Ich gehe gleich aus.“ (`akku_leer`). Danach geht es wie in a): Wiedergabe aus, Ring aus.
      **Was du siehst:** Der Ring pulsiert rot (Akku-Tiefstand) und **bleibt** nach den 10 s rot pulsierend, solange der Akku so niedrig und nicht am Lader ist.
      Nach etwa einer Minute meldet der Dienst den Tiefstand noch einmal (Ton, Herunterfahren, 10 s).

```bash
grep -E '"ereignis":"akku_tiefstand"|"ton":"akku_leer"' "$LOG" | tail -n 3
```

- [ ] `tobibox sim power --charger on`: Das rote Pulsieren endet, der Ring zeigt jetzt den Ladestand blau (solange Strom anliegt und der Akku nicht voll ist).
      Setze danach den Akku wieder hoch: `tobibox sim power --battery 80`.

**c) Leerlauf nach 10 Minuten ohne Strom, auch mit liegendem Tobie (Entscheidung O; Ein/Aus Schritt 1).** Der Zähler läuft ab dem Moment, an dem **nichts spielt**,
auch wenn ein Tobie liegt, **und kein Strom am Eingang anliegt**. Stelle vorher den Strom aus: `tobibox sim power --charger off` (ohne Wert gilt der Strom 60 s nach dem Start als „kein Strom“). Mit Strom (`--charger on`) schaltet die Box nie ab (14). Taste, Drehregler und Kopfhörer setzen ihn zurück; `tobibox status`, `sim net` und `sim power` nicht.

- [ ] Lege `04130001` auf und drücke „Hauptknopf kurz“ (Pause, der Tobie liegt). Rühre danach **nichts** an. Der Ring leuchtet bernstein und geht nach 10 s aus
      (Pause bei liegendem Tobie, auch im Leerlauf). Im Protokoll steht `leerlauf` mit Ergebnis `zaehler_gestartet`, `frist_s` 600.0.
- [ ] Nach 10 Minuten: `herunterfahren` mit Ergebnis `angefordert` und `"grund":"leerlauf"`, danach wie in a).
      Auch ohne Tobie gilt es: 10 Minuten nach dem Abziehen des Stroms (oder 11 Minuten nach dem Start des Dienstes, wenn nie ein Strom-Wert kam) steht dieselbe Zeile im Protokoll, wenn du nichts bedienst.

```bash
grep -E '"baustein":"idle","ereignis":"(leerlauf|herunterfahren)"' "$LOG" | tail -n 4
```

**Kurzstart: 30 Sekunden statt 10 Minuten** (danach `tobibox sim power --charger off`, sonst zählt der Zähler erst nach 60 s). Beende den Dienst und starte ihn so (setzt die Frist nur für diesen Lauf, am Code ändert sich nichts):

```bash
python -c "import sys, tobibox.idle as i, tobibox.app as a; i.LEERLAUF_S = 30.0; sys.exit(a.main(['--config', '$TOBIBOX_CONFIG']))"
```

- [ ] Wie oben mit liegendem Tobie, nach 30 s statt 10 min. Im Protokoll steht `frist_s` 30.0.
- [ ] **Lernmodus hält die Abschaltung auf:** `tobibox sim learn --serie 5e1a0c7d9b31` direkt nach dem Start. Nach 30 s steht `leerlauf` mit Ergebnis
      `wartet` und `"lernmodus":true`; nichts fährt herunter. `tobibox sim learn-abort`: Der Zähler beginnt neu.

Beende den Kurzstart mit `Ctrl+C` und starte danach wieder den normalen Dienst (`tobiboxd …` aus 13.1).

### 13.9 LED-Ring ansehen (CUJ 18)

Der Ring ist oben links in der Oberfläche. Die Punkte zeigen die Farbe **voll** (damit du sie siehst); die echte Helligkeit (höchstens
25 %) steht darunter als Zahl und im Balken. Dieselbe Zeile steht im Terminal A, und das Protokoll nennt jeden Wechsel:

```bash
grep '"ereignis":"ring"' "$LOG" | tail -n 8
```

Gehe die Zustände der Reihe nach durch, schau jeweils 5 bis 10 s hin und trage deine Meinung in die Tabelle unten ein.
Farben, Muster und Zeiten stehen als benannte Konstanten oben in `box/src/tobibox/led.py` (Stand: Entscheidungen U und V vom 10.11., Ergänzungen vom 11.11.; du prüfst sie an der Ansicht). Du änderst sie nicht
selbst; „ändern zu …“ geht als Auftrag an die Projektleitung.

- [ ] **Aufwachen** (weißes Lauflicht, 2 s, volle Helligkeit): beim Start des Dienstes, und wenn du bei leerer Box einen Tobie auflegst (erst abheben, dann „auflegen“).
- [ ] **Läuft** (grünes Atmen, 12 bis 25 %, 6 s): `04130001` spielt.
- [ ] **Pause** (bernstein, 10 %, nach 10 s aus): „Hauptknopf kurz“. Der Ring geht nach 10 s aus, auch wenn der Tobie noch liegt.
- [ ] **Akku** (Füllstand, grün, gelb oder rot; 15 %, 5 s bei Lader ab): `tobibox sim power --charger on --battery 60` und `--charger off`. **Laden** (blauer Füllstand, dauerhaft bei Strom; Anstecken zweimal schnell pulsierend): beim ersten Befehl oben.
- [ ] **Akku-Tiefstand** (rot pulsierend, weich, ca. 1,5 s): `tobibox sim power --charger off --battery 4`. Danach `--charger on`.
- [ ] **Lernmodus** (blaues Atmen, 3 s, 8 bis 25 %): `tobibox sim learn --serie 5e1a0c7d9b31` bei leerer Box, danach `tobibox sim learn-abort`.
- [ ] **Gute Nacht** (warmes Orange, Glimmen, 4 s, 3 bis 8 %): wie in 13.4. Beim Ausblenden wird es schwächer.
- [ ] **Stumm** (ganz dunkel rot, nach 5 s aus): wie in 13.5, Zeit auf 22:00 stellen. Vergleiche mit der bernsteinen Pause (10 %).
- [ ] **Unbekannte Karte** (magenta blinkend, 1 s): Knopf „Unbekannter Tobie“ in der Oberfläche. Der Ring blinkt 1 s magenta (zwei Blinker),
      danach zeigt er den normalen Zustand: grünes Atmen, denn die Überraschung spielt. Liegt vorher nichts auf der Box, läuft erst das
      Lauflicht des Aufwachens (2 s) und danach blinkt der Ring. Bei einer **Leser-Unterbrechung** (bis zu 3 s nach einem
      Leser-Ausfall, während ein Tobie spielt; Abschnitt 11.3, USB-Kabel ziehen) blinkt der Ring dagegen **gelb und langsam** (Periode 2 s; Entscheidung V, 10.11.; Ergänzung 11.11.).
- [ ] **Aus** (schwarz): leere Box oder Herunterfahren.

| Zustand | Stand heute | gefällt | ändern zu … |
|---|---|---|---|
| Läuft | grün, Atmen 12 bis 25 %, 6 s | | |
| Pause | bernstein, 10 %, nach 10 s aus | | |
| Unbekannte Karte (unbekannter Tobie aufgelegt) | magenta, 1 s blinkend (zwei Blinker), danach normaler Zustand | | |
| Leser-Unterbrechung | gelb, langsames Blinken (2-s-Periode), bis zu 3 s (Entscheidung V, 10.11.; Ergänzung 11.11.) | | |
| Aufwachen | weißes Lauflicht, 2 s | | |
| Akku (Füllstand) | grün über 50 %, gelb über 20 %, sonst rot; 15 %, 5 s bei Lader ab | | |
| Laden | blauer Füllstand, dauerhaft bei Strom bis der Akku voll ist; Anstecken zweimal schnell pulsierend, dann langsam pulsierend; voll: langsam ausblenden | | |
| Akku-Tiefstand | rot pulsierend, weich, ca. 1,5 s | | |
| Lernmodus | blau (0, 70, 255), Atmen 3 s, 8 bis 25 % | | |
| Gute Nacht | warmes Orange, Glimmen 4 s, 3 bis 8 %, wird beim Ausblenden schwächer | | |
| Stumm | ganz dunkel rot, nach 5 s aus | | |
| Wechsel zwischen Zuständen | alle weich überblendet (ca. 0,5 s) | | |

### 13.10 Optional: mit Mosquitto

Nicht Pflicht für die Abnahme. Du siehst, dass der Dienst den Broker erreicht und was er meldet. Home Assistant gibt es dabei nicht.

```bash
brew install mosquitto
cat > ~/tobibox-mpd/mosquitto.conf <<'EOF'
listener 1883 127.0.0.1
allow_anonymous true
EOF
mosquitto -c ~/tobibox-mpd/mosquitto.conf
```

Der Broker läuft in einem eigenen Terminal und nimmt nur Verbindungen von diesem Mac an. Beende den Dienst und hänge das an `tobibox.toml` an
(`box_id` ist der Box-Name; ein Passwort gibt es hier nicht und gehört auch nie in eine Beispieldatei):

```bash
cat >> ~/Tobi_box/box/config/tobibox.toml <<'EOF'

[mqtt]
box_id = "box1"
host = "127.0.0.1"
port = 1883
anzeigename = "Mac-Test"
EOF
```

Starte den Dienst neu.

- [ ] `tobibox status` zeigt `HA: verbunden` und in der Zeile darunter `netz: …, Broker verbunden`.
- [ ] Mit `tobibox sim net home` zeigt die Status-Karte `netz ok`: `tobibox status` zeigt `Status-Karte: leser ok, medien ok, netz ok, speicher ok`.
- [ ] In einem weiteren Terminal: `mosquitto_sub -h 127.0.0.1 -t 'tobibox/#' -v`. Du siehst `tobibox/box1/online online` und `tobibox/box1/status` mit
      dem Zustand der Box als JSON (`zustand`, `netz`, `akku_prozent`, `speicher_frei_mb` …).
- [ ] Mit `[mqtt]` übernimmt Home Assistant den Lernmodus und die Zuordnung. `tobibox sim learn`, `ack` und `card` antworten darum mit
      `quelle_nicht_sim`, und „Lernmodus starten“ in der Oberfläche meldet „Dieser Eingang ist gesperrt …“. Das ist richtig. Entferne den Abschnitt `[mqtt]`
      wieder und beende den Broker.

### Mit Home Assistant statt Hilfsskript

Läuft Home Assistant mit dem Mosquitto-Add-on (Anleitung `docs/betrieb/mqtt-konten.md`), kommen Gute Nacht, Leise-Zeiten und Zuordnungen aus der HA-Seite „Tobi Box“. Das Hilfsskript aus 13.1 brauchst du dann nicht.

- **Vorher sichern:** `cp ~/Tobi_box/box/var/config.json ~/Tobi_box/box/var/config.json.vor-ha`
- Beim **ersten Verbinden** mit `[mqtt]` übernimmt die Box die Liste aus HA. Die ist neu und leer, deine alten Zuordnungen aus `config.json` stehen dort nicht. Dafür ist die Sicherung da.
- **Testserien auf das NAS** kopieren (Ordner `tobibox/medien/`), damit HA sie kennt.
- Einen **unbekannten simulierten Tobie** legst du in der Oberfläche mit „Unbekannter Tobie (neue Zufallskennung)“ auf. HA ordnet ihn zu.
- **Zurück:** Dienst beenden, dann `mv ~/Tobi_box/box/var/config.json.vor-ha ~/Tobi_box/box/var/config.json`.

### 13.11 Aufräumen

Dienst, Oberfläche und (falls gestartet) Broker beenden (`Ctrl+C`). Dann die Gute-Nacht-Zeiten und Leise-Zeiten auf den Stand vor Abschnitt 13
zurücksetzen und, wenn du willst, die Konfiguration:

```bash
python3 ~/tobibox-mpd/config13.py normal
mv ~/Tobi_box/box/config/tobibox.toml.vor-13 ~/Tobi_box/box/config/tobibox.toml
```

- [ ] Die Zeile `config.json: normal - Gute Nacht {...}` zeigt wieder deine alten Werte (Vorgabe 30 min, 60 s).
- [ ] `tobibox.toml` ist wieder der Stand vor 13 (`mv` oben). Willst du `DEBUG` behalten, lass die Datei so. Hast du in 13.1 `geraet = "sim"`
      eingestellt (kein Leser angeschlossen), stelle die Zeile `geraet` zurück auf `/dev/cu.usbmodem*` (oder was vorher stand); sonst ist nichts zu tun.
      `[strom]` und `[netz]` mit `quelle = "sim"` dürfen bleiben. Die drei erfundenen Tobies bleiben in `config.json`; sie stören nicht.

### 13.12 Was erst am Pi geprüft wird

Das geht am Mac nicht oder nicht aussagekräftig. Es gehört in den Pi-Probelauf:

- Der Hauptknopf über die Taste des PiSugar (welcher Befehl und welche Antwort `taste_befehl` braucht, oder ein Knopf direkt am GPIO, Befund B2).
- Echte GPIO-Eingänge: Vor, Zurück, Drehregler (Pins, Richtung, Prellen) und der Hauptknopf, falls er am GPIO hängt.
- Der Schaltkontakt der Kopfhörer-Buchse: Pin, Pegel, Pull-up (`aktiv_niedrig`) und das Lesen mit `gpiozero`, im Rückfall mit `gpioget` (Befund B4).
- Entscheidung P: nicht lesbarer Kontakt gilt als „Kopfhörer steckt“ (Grenze 30), samt Hinweis an HA.
- Der Ausgangswechsel zwischen Lautsprecher und Kopfhörer in ALSA (am Mac ohne Wirkung) und die Kennlinie der Töne (`alsa_softvol`).
- Das echte Herunterfahren: Rechte und Rückgabecode des Abschaltkommandos mit dem Dienstbenutzer, die Frist von 60 s und was die Box danach tut.
- Der Akkustand, der Lader und der Tiefstand vom PiSugar; der Ton `akku_leer` am echten Lautsprecher.
- Die Uhrzeit: NTP-Synchronisierung (Befund B15), die RTC des PiSugar und das Verhalten bei unsicherer Uhr (kleinste „leiser“-Grenze, nie „stumm“).
- Die echte Netz-Klasse über NetworkManager (Heim, Hotspot, offline), die Erreichbarkeit des NAS und ein echter Sync, samt Sync-Check beim Andocken (die Wiederholung des Start-Syncs gibt es seit Ein/Aus Schritt 1 nicht mehr).
- Der PiSugar-Wecker (Aufwachen zum Sync).
- Der echte LED-Ring (APA102): wie hell er im Gehäuse wirkt, die Farben im Raum und der Deckel von 25 %.
- Die Verbindung zu Home Assistant über Tailscale und MQTT mit Konto und Passwort.

## 14. Abnahme Ein/Aus, Schritt 1

Ein- und Ausschalten, Schritt 1 (Design `docs/designs/box-software.md`, CUJ 16 und 21 bis 25; Verträge `docs/protocol/core-interface.md`, Abschnitt 9, Punkt 9):
10 min Frist nur ohne Strom, am Strom immer bereit, zwei Strom-Quellen (PiSugar und Leser), Ton `lader` beim Andocken, früher Start-Ton mit Marke.
Alles geht am Mac in der Simulation; das Wecken durch Tobie, Magnet und Strom (Schritt 2) gehört nicht dazu. Die Befehle sind im Container ausprobiert
(Dienst mit `ziel = "datei"`, Protokollstufe `DEBUG`); die Zeilen im Protokoll sehen am Mac genauso aus. Du brauchst die Terminals und `LOG` wie in Abschnitt 13.

**Vorbereitung.** Der Dienst braucht `[strom]` und `[netz]` mit `quelle = "sim"` und Protokollstufe `DEBUG` (13.1). Für den frühen Start-Ton gibt es am Mac kein `/run/tobibox`;
nimm ein eigenes Verzeichnis und setze es in **beiden** Terminals (Dienst und Frühdienst):

```bash
mkdir -p /tmp/tobibox-marken
rm -f /tmp/tobibox-marken/fruehton
export TOBIBOX_MARKEN=/tmp/tobibox-marken
```

**Wichtig:** Rückmeldungen beim Andocken und Abziehen gibt es erst **10 s nach „bereit“** (Sperre `LADER_SPERRE_S`). Warte nach dem Start des Dienstes mindestens 12 s, bevor du Strom schaltest. Die erste Strom-Messung nach dem Start gibt keine Rückmeldung. Zwischen zwei Strom-Schritten mindestens 10 s warten.

### 14.1 Frist nur ohne Strom (CUJ 16, 23, 24)

- [ ] Starte den Dienst mit dem Kurzstart aus 13.8 (Frist 30 s). Warte 12 s, dann `tobibox sim power --charger on`. **Was du siehst:** Im Protokoll `leerlauf` / `zaehler_verworfen` mit
      `"grund":"strom"`. Warte 2 Minuten: **nichts** fährt herunter, es steht keine Zeile `herunterfahren`.
- [ ] `tobibox sim power --charger off`. **Was du siehst:** `strom` / `abziehen`, dann `leerlauf` / `zaehler_gestartet` mit `frist_s` 30.0 und 30 s später `herunterfahren` / `angefordert` mit `"grund":"leerlauf"`.
      Die Frist beginnt **ab dem Abziehen**, nicht ab dem letzten Spielen.
- [ ] Bedienung setzt den Zähler zurück: nach `--charger off` nach 20 s „Vor“ drücken (`tobibox sim key vor`): Das Herunterfahren kommt erst 30 s danach.

```bash
grep -E '"baustein":"idle","ereignis":"(strom|leerlauf|herunterfahren)"' "$LOG" | tail -n 8
```

### 14.2 Zwei Quellen, Vorrang Leser (CUJ 23)

- [ ] `tobibox sim power --charger off`, dann `tobibox sim power --charger on --source leser` (der Leser sieht Strom, der PiSugar nicht). **Was du siehst:** `strom` / `widerspruch_beginnt`
      (nur DEBUG), nach 5 s `widerspruch` als WARNING (einmal). Die Box gilt als „am Strom“ und fährt nie herunter. `tobibox status` zeigt „am Lader“.
- [ ] Mit einem falschen Leser: `python box/tools/fake_reader.py --link /tmp/tobibox-fake/ttyACM0 --strom aus` (Firmware mit `caps=strom`), `geraet` auf diesen Link, Dienst starten.
      In der Eingabe des falschen Lesers `power on` und `power off`: Der Dienst verhält sich wie oben (Wert der Zeile `LADER`). `tobibox status` zeigt die Firmware `1.1.0`.
- [ ] Leser-Ausfall (falschen Leser beenden): Der Wert des Lesers gilt nicht mehr, es gilt wieder der PiSugar-Wert (Protokoll `strom` / `leser_wert_verfallen`).

### 14.3 Andocken und Abziehen (CUJ 25)

Zwischen zwei Strom-Schritten mindestens 10 s warten (Entprellung, siehe oben).

- [ ] Strom aus, Box im Leerlauf, mehr als 10 s nach „bereit“. `tobibox sim power --charger on`. **Was du hörst/siehst:** der kurze Ton „Strom ist da.“ (`lader`, leise wie der Hinweiston) und der Ring pulsiert
      zweimal schnell blau und zeigt danach den Ladestand dauerhaft blau. Im Protokoll `strom` / `andocken`, `ton` mit `"ton":"lader"`. Ein Sync wird einmal geprüft (`start_sync` / `angefordert`).
- [ ] `tobibox sim power --charger off`: Ring 5 s Akku, **kein** Ton, kein Sync (`strom` / `abziehen`).
- [ ] Wackelkontakt: dreimal schnell `--charger on` / `--charger off` im Wechsel: höchstens **eine** Rückmeldung (die übrigen Zeilen `rueckmeldung_gesperrt`), der Zähler folgt trotzdem dem Wert.
- [ ] Spielt ein Tobie (`04130001`): `--charger on` zeigt den Ring nur 3 s, **kein** Ton.
- [ ] In einem Leise-Fenster („leiser“ oder „stumm“, 13.5) oder im Lernmodus: **kein** Ton, aber der Ring (Helligkeit 5 % unter „leiser“, 3 % unter „stumm“; danach bleibt der blaue Ladestand, nachts ruhig auf der kleinsten Stufe).

### 14.4 Früher Start-Ton und Marke (CUJ 21)

Der Frühdienst läuft am Mac von Hand. Reihenfolge wie am Pi: erst `python -m tobibox.fruehton`, dann der Dienst.

Am Mac bleibt die Boot-Kennung gleich. Ein Dienst, der normal beendet und neu gestartet wird, gilt als **Dienst-Neustart** und spielt den Start-Ton selbst (Protokoll `fruehton`, Ergebnis `neustart`). Um ein echtes Einschalten nachzustellen, löschst du vorher:

```bash
rm -f ~/Tobi_box/box/var/lauf.json
rm -f "$TOBIBOX_MARKEN/fruehton"
```

- [ ] Dienst **nicht** laufen lassen. Die beiden `rm`-Zeilen oben, dann `python -m tobibox.fruehton --config "$TOBIBOX_CONFIG"` (Ton über das Kommando aus `[toene]`). **Was du hörst:** „Tobi Box ist bereit.“ in der Lautstärke eines
      gewöhnlichen Tons. `cat "$TOBIBOX_MARKEN/fruehton"` zeigt `fertig`.
- [ ] Dienst starten. **Was du hörst:** **keinen** zweiten Start-Ton. Im Protokoll `app` / `fruehton` mit Ergebnis `fertig` und `bereit`; die Marke ist weg.
- [ ] Ohne Frühdienst (Marke entfernen: `rm -f "$TOBIBOX_MARKEN/fruehton"`, Dienst neu starten): der Dienst spielt den Start-Ton selbst; danach steht `uebernommen` in der Marke, und ein
      später gestarteter `python -m tobibox.fruehton` spielt **nicht** (Ausgabe `kein_ton`).
- [ ] Unter „stumm“ (13.5, Uhr in das Fenster stellen): `python -m tobibox.fruehton` bleibt still (Marke `keiner`), und der Dienst spielt auch keinen Hinweiston.
      Unter „leiser“ klingt der Ton mit der Grenze des Fensters. Ein `systemctl restart`-Ersatz (Dienst beenden und neu starten) spielt den Start-Ton aus dem Kern und ignoriert die Marke.

### 14.5 Messung der Bootzeit (nur am Pi)

`python box/tools/measure_boot.py --log <Protokolldatei>` rechnet aus Protokoll, `systemd-analyze` und `systemctl show tobibox-fruehton.service` die Zeiten ab 5 V am Pi und nennt, ob das Soll gehalten ist
(Frühton höchstens 5 s, *Bereit* höchstens 8,5 s). Am Mac gibt es nur das Protokoll; die Messung gehört in den Pi-Probelauf (`docs/timing.md`, „Aus → Hörspiel“).
