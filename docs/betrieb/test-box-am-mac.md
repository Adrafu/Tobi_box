# Test-Box am Mac (Abnahme „Gehört“, B6)

Die echte Box-Software läuft am Mac als zusätzliche Box `boxsim` und spricht mit dem echten Home Assistant (Entscheidung R4,
`docs/egm/stufe-b/resolve.md`). Das Werkzeug `box/tools/gehoert_szenario.py` füllt ihren Puffer `gehoert.json` mit Hördaten
über Wochen. Beim Verbinden macht die Box den Handshake, sendet die Zeilen und löscht sie nach der Quittung, genau wie eine Box,
die lange offline war. Alle Befehle laufen im Ordner `~/Tobi_box/box` mit `source ../.venv/bin/activate`.

Nichts davon enthält echte Namen, Adressen oder Passwörter. Die Platzhalter ersetzt du nur in deiner lokalen Kopie.

## 1. Einmal einrichten

1. **Konto im Mosquitto** (Tobias): Konto `boxsim` mit den Rechten wie `box1` (`docs/betrieb/mqtt-konten.md`, Abschnitt 3, `box1` durch
   `boxsim` ersetzen). Das Passwort mit `openssl rand -hex 16` erzeugen.
2. **Konfiguration kopieren** und den Broker eintragen:

   ```
   cp config/boxsim.example.toml config/boxsim.toml
   open -e config/boxsim.toml        # host = "<Name oder Tailscale-Adresse des Brokers>" ersetzen
   ```

   `config/boxsim.toml` steht in `box/.gitignore`. Die Datei enthält **kein** Passwort.
3. **Passwort** nur in der Shell (nie in eine Datei im Repo, nie in den Befehl tippen):

   ```
   read -s TOBIBOXSIM_MQTT_PASSWORT && export TOBIBOXSIM_MQTT_PASSWORT
   ```

   Oder eine Datei `config/boxsim.pw` (eine Zeile, `chmod 600`, gitignoriert) und in der Konfiguration `passwort_datei = "boxsim.pw"`
   statt `passwort_umgebung`.
4. MPD läuft wie im Prototyp (`mac-prototyp.md`, Abschnitt 4). Ein laufender Prototyp-Dienst (`tobiboxd`) wird vorher gestoppt: Beide
   würden denselben MPD steuern. Die Test-Box nutzt einen **eigenen Datenordner** `box/var/boxsim/`.
5. **Test-Box in der HA-Integration hinzufügen** (Tobias): Name `boxsim`, Anzeigename „Test-Box“.

Prüfen: `tobibox status --config config/boxsim.toml` zeigt Medien und Protokollziel ohne Fehler.

## 2. Hördaten einspielen (Box gestoppt)

Erst ansehen, dann schreiben (`--trocken` schreibt nichts):

```
python tools/gehoert_szenario.py --konfig config/boxsim.toml --tage 40 --seed 1 --trocken
python tools/gehoert_szenario.py --konfig config/boxsim.toml --tage 40 --seed 1
```

Die Ausgabe nennt Zeilen, Hörzeit, Zeitraum, Enden und Hörzeit je Serie. Gleicher `--seed` und gleiches `--jetzt` ergeben dieselbe Datei.
Ohne `--ueberschreiben` weigert sich das Werkzeug, eine Datei mit Daten zu ersetzen, und auch, solange die Test-Box läuft (`sim.sock`).

| `--szenario` | Was entsteht |
|---|---|
| `alltag` | Hören morgens, nachmittags, abends; weiter oder von vorn, mal bis zum Ende, mal abgebrochen; Folgenwechsel; die Box wird oft ausgeschaltet (neue `boot_id`) |
| `wiederholen` | dieselbe Folge an drei Abenden je 3 bis 5 Mal hintereinander bis zum Ende |
| `hoerbuch` | ein Hörbuch in Portionen über mehrere Abende; der letzte Abend endet am Ende der Folge („fertig“ über die Portionen) |
| `neustart` | Neustart der Box-Software mitten im Hören (`dienst_ende`) und ein Absturz (`abbruch`) |
| `strom_weg` | Strom weg: `abbruch` im nächsten Gerätestart, bis zu 2 Minuten Hörzeit fehlen |
| `ueberlauf` | mehr als 500 kurze Sitzungen an einem Tag: die ältesten Zeilen fallen weg, die Technik-Zeile „verworfen“ zeigt es |
| `offline` | die letzten Tage unterwegs: jedes Mal frisch eingeschaltet (viele `boot_id`), nie verbunden |
| `uhr_nie_gut` | Gerätestarts mit falscher Uhr (`zeit_ok = false`, Datum unbekannt) und einer mit später guter Uhr |

Vorgabe: `alltag,wiederholen,hoerbuch,neustart,strom_weg,offline`. Mehrere: `--szenario hoerbuch,ueberlauf`. Alle: `--szenario alle`.
Der Überlauf nimmt die ältesten Zeilen mit, darum steht er nicht in der Vorgabe. Weitere Schalter: `--tage`, `--zeitzone`, `--jetzt <ISO>`,
`--medien <Ordner>`, `--virtuelle-dauer <s>`, `--serien <datei.json>`, `--anzahl-serien <n>`.

**Serien aus der echten HA (`--serien`).** HA nimmt die Dauer aus seiner Medieninfo und kennt die Testserien aus `medien-sprache` nicht. Für sinnvolle
Zahlen gibt es darum `--serien <datei.json>` (ersetzt `--medien`). Die Datei enthält eine Liste, die die Projektleitung aus der echten HA
erzeugt (Platzhalter hier):

```json
[{"serie_id": "aaaa00000001", "name": "Serie Eins",
  "folgen": [{"name": "folge-01.mp3", "dauer_s": 1500}, {"name": "folge-02.mp3", "dauer_s": 1620}]}]
```

`name` der Folge ist der Name wie in `mqtt-v1.md` (Dateiname oder Ordnername), `dauer_s` eine ganze Zahl > 0. Das Werkzeug nimmt genau diese
Serien, Folgen und **echten** Dauern (keine virtuelle Dauer), wählt nach `--seed` deterministisch höchstens `--anzahl-serien` (Vorgabe 12) davon aus
und verteilt die Szenarien darauf. Das Hörbuch ist die längste Folge der Auswahl (sie kommt im Alltag nicht vor).
Beispiel: `python tools/gehoert_szenario.py --konfig config/boxsim.toml --serien ha-serien.json --anzahl-serien 12 --seed 1`.
Eine Beispieldatei mit Platzhaltern: `box/tests/fixtures/serien_beispiel.json`. Die echte Datei gehört nicht ins Repo.

**Ohne `--serien`: Serien und Folgen** stammen aus dem Medienordner der Konfiguration (`medien-sprache`), damit Namen und Serien-IDs zu dem passen, was
Home Assistant kennt. Dauern unter 5 Minuten (die Testmedien dauern Sekunden) ersetzt das Werkzeug durch 25 Minuten und mehr, sonst zeigen
Diagramme nichts. Die Zeile trägt diese Länge als `folge_dauer_s`. Serien, die Home Assistant nicht kennt, erscheinen dort als „unbekannt“.

## 3. Starten, beobachten, stoppen

```
tobiboxd --config config/boxsim.toml
```

Das Fenster bleibt offen. Im Protokoll (`box/var/boxsim/log/tobibox.log`) erscheinen `gehoert`/`ha` (Verbinden, Quittung):

```
grep -E '"(gehoert|ha)"' var/boxsim/log/tobibox.log | tail
```

Erwartet: Die Box verbindet sich, meldet `gehoert_wartet = true`, HA antwortet mit einer Quittung, die Box sendet die Zeilen (höchstens
20 je Nachricht), HA quittiert sie, und `var/boxsim/gehoert.json` hat danach `"zeilen": []`. Ein Neustart der Box sendet nichts mehr.

Live hören und einen Tobie auflegen (ohne Leser): `tobibox gui --config config/boxsim.toml` (Browser, nur localhost) oder
`tobibox sim --config config/boxsim.toml …` (oder einmal `export TOBIBOX_CONFIG=$PWD/config/boxsim.toml`, dann ohne `--config`;
`mac-prototyp.md`, Abschnitt 12). Netz weg und wieder da: `tobibox sim net offline`, danach `tobibox sim net home`.

**Stoppen:** `Ctrl+C` im Fenster. Die Box schließt die offene Sitzung ab (`dienst_ende`) und schreibt `gehoert.json` vor dem Ende.

## 4. Aufräumen nach der Abnahme

1. Test-Box stoppen (`Ctrl+C`).
2. Daten der Test-Box in Home Assistant löschen (Quelle `box:boxsim`, Technik-Bereich der Seite „Gehört“), **bevor** die Box aus der
   Integration entfernt wird.
3. Lokale Daten weg: `rm -rf var/boxsim`. Nur die Test-Box ist betroffen, `var/` des Prototyps bleibt.
4. Test-Box aus der Integration entfernen und das Konto `boxsim` im Mosquitto löschen (Tobias).
5. `config/boxsim.toml` (und `boxsim.pw`) löschen; `unset TOBIBOXSIM_MQTT_PASSWORT`.
