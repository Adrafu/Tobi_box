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

`sox` brauchst du nur für die Messung in 11.7 (`rec`, `sox`).

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

   Beispiel: `place 04a1b2c3d4e5f6 ntag`, dann `remove`.

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
   (printf 'setvol 30\nadd "serie-a/folge-01.wav"\nplay\n'; sleep 1) | nc localhost 6600
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
      (Die Folgen von `serie-a` und `meine-testserie` dauern nur 3 s. Für 20 s Spielzeit legst du
      die lange Folge aus Schritt 12.1 an und ordnest den Tobie `lange-serie` zu.)
- [ ] Dienst mit `Ctrl+C` beenden und neu starten (Schritt 7). Tobie auflegen. Die Folge
      läuft an der gespeicherten Stelle weiter, mit 3 s Rücksprung (`spielt` mit
      `position_s` etwa 3 s unter dem gespeicherten Wert).
- [ ] **Dienst-Neustart bei liegendem Tobie** (Entscheidung G, 06.11.): Folge spielt, der
      Tobie bleibt liegen. Dienst mit `Ctrl+C` beenden und neu starten. Im Protokoll steht
      `start` mit Ergebnis `dienst_neustart` und später `dienst_neustart` mit
      `pausiert`. Es startet **keine Wiedergabe** von selbst (nur das Startgeräusch des Dienstes), auch nach 10 s nicht. Zum Weiterspielen
      den Tobie abheben und wieder auflegen. Dann läuft er an der gespeicherten Stelle weiter.
      (Der Hauptknopf, der am Pi dasselbe tut, fehlt am Mac.)
      - *Mit dem Fake-Leser:* `place <kennung> ntag`, Folge spielt, **kein**
        `remove`. (Ein gesperrter Tonie mit `lock` hat keine Kennung; für ihn gilt dieser Schritt
        noch nicht, er startet nach dem Neustart die Überraschung.) Den Dienst mit `Ctrl+C` beenden und neu starten, den Fake-Leser laufen
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
mkdir -p ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test
cp ~/Tobi_box/box/medien-beispiel/serie-a/folge-0*.wav ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/
mv ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/folge-01.wav ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/01.wav
mv ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/folge-02.wav ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/02.wav
mv ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/folge-03.wav ~/Tobi_box/box/medien-beispiel/meine-testserie/cd-test/03.wav
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
    "KENNUNG_EINZELN": { "ziel": { "typ": "folge", "serie": "meine-testserie", "folge": "folge-02.wav" } },
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
      `folge` `folge-02.wav`, `art` `folge`). Am Ende der Folge pausiert die Box (Protokoll:
      `pausieren` mit Grund `folgenende`), obwohl der Tobie noch liegt. Tobie abheben und wieder
      auflegen: Die Folge spielt **von vorn**. Die Serie `meine-testserie` startet dabei nicht
      bei der nächsten Folge.
- [ ] **Mehrere Tracks:** Tobie `KENNUNG_CD` auflegen. Die drei Tracks spielen nacheinander
      **ohne Pause** (die Piepsfolgen mit einem, zwei und drei Tönen; im Protokoll `track_wechsel`).
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
      Die Serie liegt im Ordner `box/medien-beispiel/messung/` (nicht committen):

      ```
      mkdir -p ~/Tobi_box/box/medien-beispiel/messung
      sox -n -r 44100 -c 1 ~/Tobi_box/box/medien-beispiel/messung/dauerton.wav synth 60 sine 440 vol 0.5
      cat > ~/Tobi_box/box/medien-beispiel/messung/serie.json <<'JSON'
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
der Serie `lange-serie`, in 12.3 der Serie `serie-a` zugeordnet), `<UID-NEU>` (in 12.5 noch nie
zugeordnet), `<UID-NEU-2>` (noch nie zugeordnet, für den Folgen-Lernlauf in 12.6) und die
Karte `<UID-KARTE>`.

**Serien-ID statt Ordnername.** Bei `--serie` gehört die **ID** aus der Datei `serie.json`
der Serie, nicht der Ordnername. Die Beispielserie `serie-a` hat die ID `a1b2c3d4e5f6`; die
Überraschungs-Serie hat `c07d2e91a45b`. Die Serie `lange-serie` aus 12.1 hat keine `serie.json`,
dort gilt der Ordnername als ID (Schritt 5). Eine unbekannte ID nimmt `tobibox sim` an
(`{"ok": true}`), aber der Tobie spielt dann die Überraschung, und im Protokoll steht eine
WARNING-Zeile `serie_fehlt`. Die ID liest du so nach:

```bash
grep '"id"' ~/Tobi_box/box/medien-beispiel/serie-a/serie.json
```

**Zu den Tönen.** Die Töne und ihre Dauer: Startgeräusch (`start`, 0,5 s), `lernen_beginn` und `lernen_ende` (je 0,5 s),
`unbekannt` (0,4 s), `hinweis` (0,1 s), `pruef_ok` (0,1 s, hoch) und `pruef_fehler`
(0,4 s, tief). Wer sie im Protokoll sehen will: In `box/config/tobibox.toml` die Zeile
`ebene = "INFO"` auf `ebene = "DEBUG"` setzen und den Dienst neu starten. Dann steht bei
jedem Ton eine Zeile mit `"ereignis":"ton"` und dem Namen im Feld `ton`.

### 12.1 Vorbereitung

Für 12.2 und 12.4 braucht es eine **lange** Folge. Die Folgen von `serie-a` dauern nur 3 s,
und der Rücksprung von 3 s wäre dort nicht zu sehen. Lege eine Serie mit einer Folge von
60 s an (ein gleichmäßiger Ton) und mache sie MPD bekannt. Python-Umgebung aktiv (Schritt 2):

```bash
mkdir -p ~/Tobi_box/box/medien-beispiel/lange-serie
python - <<'PY'
import math, os, struct, wave
pfad = os.path.expanduser("~/Tobi_box/box/medien-beispiel/lange-serie/folge-01.wav")
with wave.open(pfad, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
    w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 440 * i / 22050))) for i in range(22050 * 60)))
PY
(printf 'update\n'; sleep 1) | nc localhost 6600
```

Die Datei gehört nicht ins Repo (nicht mit `git add` hinzufügen). Dann Dienst starten:

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
tobibox sim card <UID> --serie lange-serie
```

- [ ] Lege `<UID>` auf. Nach etwa 10 s hebst du den Tobie ab.
      **Was du hörst:** Einen gleichmäßigen Ton (die lange Folge). Beim Abheben wird die Stelle
      gespeichert; im Protokoll steht `zeiger_gespeichert` mit `position_s` von etwa 10.
- [ ] Beende den Dienst mit `Ctrl+C` und starte ihn neu (Befehl aus Schritt 12.1, nur die
      Zeile `tobiboxd …`). Lege `<UID>` danach auf.
      **Was du hörst:** Die Folge läuft weiter, etwa 3 s vor der gespeicherten Stelle. Im Protokoll
      liegt `position_s` von `spielt` rund 3 s unter dem Wert vom Abheben (also etwa 7).

### 12.3 Pause nach jeder Folge

Jetzt die Serie `serie-a` (Folgen `folge-01.wav` bis `folge-03.wav`, je 3 s lang). Ordne `<UID>`
neu zu. Hebe den Tobie vorher ab, falls er liegt:

```bash
tobibox sim card <UID> --serie a1b2c3d4e5f6
```

Eine Serie beginnt bei der Folge, bei der sie zuletzt stand. Hast du `serie-a` früher schon gespielt,
beginnt sie nicht bei Folge 1; lies die Reihenfolge unten dann ab dieser Folge.

- [ ] Lege `<UID>` auf und lass ihn liegen. Die Folge spielt bis zum Ende.
      **Was du hörst:** Folge 1 (ein Piepton), danach Stille. Im Protokoll steht `pausieren` mit
      Grund `folgenende`. Der Tobie liegt noch, die Box startet nichts von selbst (warte 10 s).

```bash
grep '"ereignis":"pausieren"' ~/Tobi_box/box/var/log/tobibox.log | tail -n 1
```

      Die Zeile enthält `"grund":"folgenende"`.

- [ ] Hebe `<UID>` ab und lege ihn wieder auf.
      **Was du hörst:** Folge 2 (zwei Pieptöne), von vorn.
- [ ] Lass Folge 2 zu Ende laufen. Die Box pausiert. Hebe `<UID>` ab und lege ihn wieder auf.
      **Was du hörst:** Folge 3 (drei Pieptöne).
- [ ] Lass Folge 3 zu Ende laufen. Die Box pausiert. Hebe `<UID>` ab und lege ihn wieder auf.
      **Was du hörst:** Folge 1 wieder. Nach der letzten Folge steht der Zeiger auf Folge 1.

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
tobibox sim card <UID> --serie lange-serie
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

- [ ] Den Hauptknopf gibt es am Mac nicht, und `tobibox sim` hat dafür keinen Befehl. Ersatz:
      Hebe `<UID>` ab und lege ihn wieder auf.
      **Was du hörst:** Die Folge läuft an der gespeicherten Stelle weiter (3 s Rücksprung).
- [ ] **Einschalten:** Der Tobie liegt weiter auf dem Leser. Beende den Dienst mit `Ctrl+C`. Erst
      danach löschst du den Marker. (Würdest du ihn vorher löschen, schriebe der Dienst ihn beim
      Beenden wieder.) Das ersetzt das Ausschalten des Macs:

```bash
rm ~/Tobi_box/box/var/lauf.json
```

      Starte den Dienst wieder (Zeile `tobiboxd …` aus Schritt 12.1).
      **Was du hörst:** Das Startgeräusch, und gleich danach spielt die Folge **von selbst**,
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
      **Was du hörst:** Zuerst ein kurzer Ton (`unbekannt`), dann der lange Ton der
      Überraschungs-Serie `ueberraschung` (2 s). Im Protokoll hat die Zeile `zugeordnet` das
      Ergebnis `ueberraschung`.
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
an dem, was der Tobie danach spielt, und im Protokoll. Legst du einen **neuen** Tobie auf, kommt
zusätzlich der kurze Ton `unbekannt` (fast gleichzeitig mit dem Ende-Ton), weil die Box ihn erst
als unbekannt behandelt. Dann wechselt sie auf das Lernziel.

**a) Serie lernen**

```bash
tobibox sim learn --serie a1b2c3d4e5f6
```

- [ ] Du siehst `{"ok": true}` und hörst einen Ton. `tobibox status` zeigt `Lernmodus: an`.
      Lege `<UID-NEU>` auf (hebe ihn vorher ab, falls er liegt).
      **Was du hörst:** Zwei kurze Töne fast gleichzeitig (`unbekannt` und `lernen_ende`), dann
      spielt der Tobie die Serie `serie-a` an dem Zeiger, an dem die Serie steht (nach 12.3
      Folge 1 oder 2). Im Protokoll steht eine Zeile mit Baustein `ha_ersatz`, Ereignis
      `zuordnung` und Ergebnis `ok`.

```bash
grep -A5 '"<UID-NEU>"' ~/Tobi_box/box/var/config.json
```

- [ ] Die Ausgabe zeigt `"typ": "serie"` und `"serie": "a1b2c3d4e5f6"`. `tobibox status` zeigt
      keine offene Meldung mehr; der HA-Ersatz bestätigt den Lernlauf selbst.

**b) Einzelne Folge lernen**

```bash
tobibox sim learn --serie a1b2c3d4e5f6 --folge folge-02.wav
```

- [ ] Lege `<UID-NEU-2>` auf.
      **Was du hörst:** Wie in a), dann nur die Folge `folge-02.wav` (zwei Pieptöne). Die Serie spielt
      danach nicht weiter.
- [ ] Prüfe mit `grep -A5 '"<UID-NEU-2>"' ~/Tobi_box/box/var/config.json`: `"typ": "folge"`,
      `"folge": "folge-02.wav"`.

**c) Abbruch**

```bash
tobibox sim learn --serie a1b2c3d4e5f6
tobibox sim learn-abort
```

- [ ] Du siehst zweimal `{"ok": true}` und hörst zwei Töne (`lernen_beginn`, dann `lernen_ende`).
      `tobibox status` zeigt `Lernmodus: aus`. Auch ein Tobie, den du danach auflegst, ändert
      `config.json` nicht.

**d) Bestehende Zuordnung: nur mit `--ueberschreiben`**

```bash
tobibox sim learn --serie a1b2c3d4e5f6 --folge folge-03.wav
```

- [ ] Hebe `<UID-NEU>` ab und lege ihn wieder auf (er ist schon zugeordnet). Der Befehl selbst
      ist angenommen; die Ablehnung zeigt sich erst beim Auflegen.
      **Was du hörst:** Dasselbe wie bei jedem bekannten Tobie: seine Serie spielt weiter, dazu
      der Ende-Ton `lernen_ende`. Der Ton ist derselbe wie beim erfolgreichen Lernen (ohne den
      Ton `unbekannt`). Die Ablehnung steht nur im Protokoll.
      **Was du siehst:** Im Protokoll eine WARNING-Zeile mit Baustein `ha_ersatz`, Ereignis
      `zuordnung`, Ergebnis `abgelehnt`, Grund `schon_zugeordnet` und dem Hinweis
      „schon zugeordnet und bleibt, wie er ist“. `config.json` bleibt bei `serie-a`.

```bash
grep '"ereignis":"zuordnung"' ~/Tobi_box/box/var/log/tobibox.log | tail -n 1
```

```bash
tobibox sim learn --serie a1b2c3d4e5f6 --folge folge-03.wav --ueberschreiben
```

- [ ] Hebe `<UID-NEU>` ab und lege ihn wieder auf.
      **Was du hörst:** Den Ende-Ton, dann die Folge `folge-03.wav` (drei Pieptöne).
      `grep -A5 '"<UID-NEU>"' ~/Tobi_box/box/var/config.json` zeigt `"folge": "folge-03.wav"`.

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
      **Was du hörst:** Vier Töne in dieser Reihenfolge: Leser, Medien, Netz, Speicher. Jeder Ton ist
      kurz und hoch (in Ordnung) oder tief (Fehler). Erwartet: hoch, hoch, **tief**, hoch.
      Es startet keine Wiedergabe.
- [ ] **Netz ist in Stufe 2 immer tief.** Der Prüfpunkt Netz verlangt ein Netz (Heim oder Hotspot)
      und einen verbundenen Broker. Den Broker gibt es erst mit MQTT (Stufe 3a). Der tiefe Ton ist
      also richtig.
- [ ] Prüfe mit `tobibox status`: Die Zeile `Status-Karte:` zeigt `leser ok, medien ok, netz FEHLER,
      speicher ok`. Darunter steht `netz: offline, Broker nicht verbunden`.

### 12.8 Karte zurück auf die Folge

Setze die Karte auf die Zuordnung zurück, die du in Schritt 12.7 notiert hast. Das Beispiel
ist die Folge `folge-02.wav` aus `serie-a` (hebe die Karte vorher ab):

```bash
tobibox sim card <UID-KARTE> --serie a1b2c3d4e5f6 --folge folge-02.wav
```

- [ ] Lege die Karte auf.
      **Was du hörst:** Folge 2 (zwei Pieptöne) von vorn.
