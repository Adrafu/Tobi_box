# Recherche: Phoniebox V3 (future3) und Leser-Anschluss fuer ESP32/PN5180

Stand: 2026-11-05. Quellcode gelesen aus `future3/main` (= Tag v3.6.0, Commit 4fa84fd, 2026-03-04) und `future3/develop` (0d9d70f, 2026-08-05).
Permalink-Basis: `B = https://github.com/MiczFlor/RPi-Jukebox-RFID/blob/v3.6.0/`
Markierung: **[V]** im Quellcode verifiziert, **[I]** abgeleitet/unverifiziert.

## 1. Repo / Branch / OS
- V3 liegt NICHT auf `develop`/`master` (das ist V2.x), sondern auf `future3/main` (stabil) und `future3/develop` (Pre-Release). Neuester stabiler Tag: **v3.6.0** (daneben `v3.7.0-alpha`). [V] (`git ls-remote`; README.md Z.52 nennt beide Branches)
- Install-Doku `future3/main`: Empfehlung "Raspberry Pi OS (Legacy, 32-bit) Lite", ARMv7-Modelle (Pi 2/3/Zero 2) empfohlen. [V] `B documentation/builders/installation.md` Z.6-12 (Pi 3 A+ ist 64-bit-faehig, aber 32-bit Legacy ist der dokumentierte Pfad).
- Achtung: `future3/develop` empfiehlt bereits "Raspberry Pi OS Lite - Trixie" (64 bit, 32 bit "should also work"). [V] https://github.com/MiczFlor/RPi-Jukebox-RFID/blob/future3/develop/documentation/builders/installation.md Z.10 und Z.17. Bestaetigung "Legacy 32-bit Lite" fuer Stable: ja.
- develop baut den Player gerade um (`components/player/{coordinator,backends,plugin}.py` neben `playermpd/` als Kompat-Stub). RFID-Teil ist identisch zu v3.6.0 (nur neues Modul `mfrc522_i2c`). [V] `diff -rq`.
- Hinweis: Pi 3 A+ hat nur 512 MB RAM; die Doku nennt Installationsdauer 20-60 min. [V] installation.md Z.~125.

## 2. RFID-Architektur
- Hauptschleife: `ReaderRunner(threading.Thread).run()` je Leser, `B src/jukebox/components/rfid/reader/__init__.py` Z.138-237. Start der Threads in `finalize()` Z.240-257. [V]
- Interface (`B src/jukebox/components/rfid/readerbase.py` Z.7-45): Klasse `ReaderClass(ReaderBaseClass)` mit `__init__(reader_cfg_key)`, `read_card() -> str`, `cleanup()`, `stop()`; Context-Manager + Iterator (`__next__` ruft `read_card`). [V]
  - `read_card` darf blockieren oder nach Timeout `''` zurueckgeben (Schleife ignoriert leere IDs, Z.229-231). Bei `stop()` muss es zurueckkehren (`''`) oder `StopIteration` werfen (Kommentar Z.159). Template: `.../hardware/template_new_reader/template_new_reader.py` Z.113-125. [V]
  - **Es gibt keinen "Karte entfernt"-Rueckgabewert.** Das Interface kennt nur "Karte X gesehen" (String). [V]
- Registrierung/Auswahl: Verzeichnis-Konvention `components/rfid/hardware/<name>/<name>.py` + `description.py` (`DESCRIPTION`); das Konfig-Tool findet unbekannte Verzeichnisse automatisch (`configure/__init__.py` Z.150-161), `ReaderRunner` laedt per `importlib` `components.rfid.hardware.<module>.<module>` (Z.99-103). Config `shared/settings/rfid.yaml`, Pfad aus `jukebox.yaml: rfid.reader_config` (`resources/default-settings/jukebox.default.yaml` Z.104-106); erzeugt durch `src/jukebox/run_register_rfid_reader.py`. [V]
- rfid.yaml-Struktur (Doku `B documentation/developers/rfid/basics.md` Z.47-59; Defaults vom Tool `configure/__init__.py` Z.~205-213):
```yaml
rfid:
  readers:
    read_00:
      module: generic_usb
      config: {device_name: ..., ...}
      same_id_delay: 1.0
      log_ignored_cards: false
      place_not_swipe:
        enabled: false
        card_removal_action: {alias: pause}
```
- Plugin-Reihenfolge `jukebox.yaml: modules.named` (`rfid: rfid.reader`, `cards: rfid.cards`) Z.5-21. [V]

## 3. Place-not-swipe / Kartenentfernung
Es gibt KEIN Entfernen-Ereignis vom Leser. Entfernung = "ID kommt laenger als 1 s nicht mehr" (Watchdog-Thread). [V]

Watchdog `CardRemovalTimerClass.run` (reader/__init__.py Z.73-88):
```python
while True:
    time.sleep(0.2)
    self.trigger.wait(1)          # bricht sofort ab, wenn trigger gesetzt
    if self.trigger.is_set(): has_timed_out = False
    else:
        if not has_timed_out: self.timeout_action()   # = card_removal_action
        has_timed_out = True
```
Hauptschleife (Z.158-235), Kern:
```python
for card_id in reader:
    if card_id:
        if valid_for_removal_action and self._timer_thread is not None and card_id == previous_id:
            self._timer_thread.trigger.set()                  # Z.171-172  Karte noch da
        if card_id != previous_id or (time.time() - previous_time) >= self._cfg_same_id_delay:   # Z.173
            ... Aktion ausfuehren, ggf. trigger.set() (Z.206-208)
        previous_time = time.time()                           # Z.228, bei JEDEM Read
    self._cancel.wait(timeout=0.2)                            # Z.233
    if self._timer_thread is not None: self._timer_thread.trigger.clear()   # Z.234-235
```
Config-Schluessel (Z.106-121, Doku basics.md Z.71-88):
- `same_id_delay` (Default 1.0 s): gleiche ID wird nur dann erneut als Aktion ausgefuehrt, wenn seit dem LETZTEN Read (nicht seit der letzten Aktion, siehe Z.228) mind. so viele Sekunden vergangen sind. Verhindert Prellen/Retrigger bei aufliegender Karte.
- `place_not_swipe.enabled`: startet den Watchdog; ohne `card_removal_action` wird die Option abgeschaltet (Z.118-121).
- `place_not_swipe.card_removal_action`: ein globaler RPC-Befehl (Standard `alias: pause`), gleich fuer alle Karten. Pro Karte abschaltbar mit `ignore_card_removal_action: true` in cards.yaml (Z.206). Nur "Entfernen" existiert als Event; "Auflegen" ist die normale Kartenaktion.
- `ignore_same_id_delay` (pro Karte): setzt `previous_id=''`, Karte feuert bei jedem Read (z.B. Lauter-Karte) und hat dann keine Removal-Aktion (Z.197-206).
- Zeitverhalten [I, aus Code gerechnet]: Entfernung wird ca. 1,0-1,4 s nach dem letzten gelesenen UID gemeldet (sleep 0,2 + wait 1 s). Neu-Auflegen derselben Karte nach >= 1 s Pause loest wieder die Kartenaktion aus.
- Bekannte Einschraenkung: Issue #2324 "place_not_swipe: Buttons may resume audio without a card present" (offen). https://github.com/MiczFlor/RPi-Jukebox-RFID/issues/2324
- Bug-Hinweis: `alias`-Voreinstellung `ignore_card_removal_action: True` in `rpc_command_alias.py` (z.B. `pause`, Z.45-50) wird von der Schleife NICHT ausgewertet; sie liest nur `card_entry.get(...)` aus cards.yaml (Z.206). [V]

## 4. Generic USB Reader (`generic_usb`)
Quelle: `B src/jukebox/components/rfid/hardware/generic_usb/generic_usb.py`
- Basis: `evdev`, kein pyserial. `read_card()` blockiert in `while self._keep_running: select(..., 0.2)` bis `KEY_ENTER` kommt, dann `return card_uid[:-1]` (Z.184-215). [V]
- Doku: **"place-capable: typically no"** (`B documentation/developers/rfid/genericusb.md` Z.3) und basics.md Z.27 "not all USB readers are place-capable". Der Grund ist nur, dass uebliche Leser die ID einmal senden; der Code verbietet Wiederholung nicht. [V]
- 500-ms-Wiederholung, Ablauf im Code [V/I]:
  1. Erster UID: Karte bekannt -> Aktion `play_card`, Watchdog getriggert.
  2. Wiederholte UIDs alle 0,5 s: `card_id == previous_id`, Luecke 0,5 s < `same_id_delay` 1,0 -> KEIN Retrigger, aber `trigger.set()` (Z.171) und `previous_time` wird aufgefrischt. Watchdog bleibt ruhig.
  3. Aufhoeren zu senden -> Watchdog ruft nach ca. 1-1,4 s `card_removal_action` (pause).
  => **Der Trick funktioniert ohne jeden "removed"-Code**, genau wie beim RDM6300, der die ID dauernd sendet. Ein "removed"-Code ist ueberfluessig.
- Wuerde man einen "removed"-Code senden: er ist fuer V3 nur eine weitere Karten-ID. In cards.yaml als `alias: pause` eingetragen -> pausiert sofort, aber startet zugleich einen Removal-Timer (kein `ignore_card_removal_action` gesetzt) -> zweites `pause` nach ~1 s (harmlos, idempotent). Ohne Eintrag: "Unknown card", wird nur publiziert. [V/I]
- Risiko Wiederholung: Luecke >= 1 s mitten im Auflegen (PN5180-Lesefehler) -> Watchdog pausiert, danach naechste UID loest `play_card` erneut aus -> Second-Swipe `toggle` (Default) setzt fort; kurzes Aussetzen hoerbar. Race: kommt UID kurz vor dem Watchdog-Timeout mit Luecke >= 1,0 s, kann `toggle` pausieren und der Watchdog danach nochmals pausieren => Musik bleibt trotz aufliegender Karte pausiert bis zum naechsten Retrigger. [I] Daher Firmware: Wiederholung eher 250-300 ms, Lesefehler tolerieren (z.B. 2-3 verpasste Reads ueberbruecken, erst dann aufhoeren zu senden).
- **Fallstricke des HID-Wegs im Code [V]:**
  - Feste Tastentabelle `self.keys` (Z.131), deutsches QWERTZ-Layout, nur Ziffern + Kleinbuchstaben: Z und Y vertauscht (Linux-Keycode 21 = KEY_Y -> 'z', 44 -> 'y'); alles andere (Shift, Minus, Leertaste, Grossbuchstaben via Shift) wird zu `'X'`. UID daher als **Kleinbuchstaben-Hex ohne Trennzeichen** tippen; Enter (Code 28) wird als 'X' angehaengt und per `[:-1]` abgeschnitten. Ein Praefix wie `REMOVED` waere nicht lesbar umsetzbar; nur `a-f`, `0-9`.
  - Geraet wird nicht per `grab()` exklusiv genommen -> Tastendruecke gehen zusaetzlich an die Linux-Konsole (tty1/getty) [I]; bei Wiederholung alle 0,5 s Log-Spam/Login-Prompt-Muell moeglich.
  - Geraetefindung ueber `device_name` (+ `device_phys`), muss ein "Keyboard" (Tasten ESC..D) sein (Z.48-71, 156-170). Fehlt das Geraet beim Start, wirft `__init__` `FileNotFoundError` (Z.170); `ReaderRunner.run` faengt das nicht ab (Z.143) -> Leser-Thread stirbt bis zum Service-Neustart. [V]
  - Benutzer muss in Gruppe `input` sein (genericusb.md Z.9-14). [V]

## 5. Eigenes Leser-Modul (USB-seriell, Zeilenprotokoll)
Einfachste Vorlage: `rdm6300_serial` (`B .../hardware/rdm6300_serial/rdm6300_serial.py`, Z.84-158, serieller Leser mit pyserial, Timeout-Read) plus `template_new_reader`. [V]
Noetig:
- Verzeichnis `src/jukebox/components/rfid/hardware/tobi_serial/` mit `tobi_serial.py` (Klasse `ReaderClass`), `description.py` (`DESCRIPTION = '...'`, <= 40 Zeichen), optional `requirements.txt` (`pyserial`), `setup.inc.sh` (hier nicht noetig; RDM6300 braucht es nur wegen UART).
- `ReaderClass.__init__(reader_cfg_key)`: Logger, `super().__init__(reader_cfg_key, description, logger)`, Config via `cfg.getn('rfid','readers',key,'config')` (`with cfg:`), `serial.Serial(device, baud, timeout=0.1-0.2)`, `self._keep_running=True`.
- `read_card()`: `readline()`; bei Timeout `''`; Zeile `ON <uid>` -> `return uid`; `OFF` -> internen Zustand loeschen; bei `_keep_running False` -> `''`/`StopIteration`. `cleanup()` schliesst Port, `stop()` setzt Flag.
- Optional `query_customization() -> dict` fuer das Konfig-Tool (Default z.B. `{'device': '/dev/ttyACM0', 'baudrate': 115200}`).
- Registrierung: nur Namenskonvention (Auto-Discovery, Abschnitt 2) und Eintrag `module: tobi_serial` in rfid.yaml. Kein Code-Eingriff in V3. [V]
- Abhaengigkeit: **pyserial ist nicht in `requirements.txt` des Kerns**, nur in `rdm6300_serial/requirements.txt` (grep); wird vom Konfig-Tool per `pip install -r requirements.txt` im Leser-Verzeichnis installiert (`configure/__init__.py` Z.16-46) oder manuell. [V]
- Wichtig: Auch ein serielles Modul kann "OFF" nicht an V3 melden (siehe Interface). Zwei Varianten: (a) Modul gibt zwischen `ON` und `OFF` zyklisch (z.B. alle 300 ms) die letzte UID zurueck, damit V3-Watchdog arbeitet -> Entfernen nach ca. 1-1,4 s; (b) Modul ruft bei `OFF` selbst `plugs.call_ignore_errors('player','ctrl','pause')` (sofort, aber Eingriff am Watchdog vorbei). [I]
- Vorteile ggue. HID: keine Tastaturtabelle/Layout-Probleme, beliebige UID-Formate, keine Konsolen-Einstreuung, Rueckkanal (LED/Buzzer) moeglich, Geraet ueber `/dev/serial/by-id`. [I]
- Nachteil: Code im V3-Checkout (Updates per git koennen kollidieren; untracked Verzeichnis sollte `git pull` ueberleben [I]), eigenes Modul wartungspflichtig; kein Test im Upstream-CI.

## 6. Kartendatenbank
- Datei `shared/settings/cards.yaml` (`jukebox.yaml: rfid.card_database`), Doku `B documentation/builders/card-database.md`. [V]
- Format: Karten-ID als **String-Schluessel** -> RPC-Befehl (`alias`/`package+plugin+method`, `args` Liste, `kwargs`) + optional `ignore_card_removal_action`, `ignore_same_id_delay`:
```yaml
'04a1b2c3':
  alias: play_card
  args: [KinderFolder1]
```
  Beispiele: `resources/default-settings/cards.example.yaml`. [V]
- Aliase (`B src/jukebox/components/rpc_command_alias.py` Z.13-137): `play_card`, `play_album`, `play_single`, `play_folder`, `play`, `pause`, `next_song`, `prev_song`, `toggle`, `shuffle`, `repeat`, `set_volume`, `change_volume`, `shutdown`, `reboot`, `timer_shutdown`, ... `play_card` = `player.ctrl.play_card(folder)` (mit Second-Swipe-Logik), `play_folder` startet immer neu. [V]
- Registrierung per Web-UI: Karte auflegen -> Leser publiziert `rfid.card_id` (reader/__init__.py Z.130, 193, 225) -> `src/webapp/src/components/Cards/register.js` zeigt die ID, ruft RPC `cards.register_card` (`src/webapp/src/commands/index.js` Z.42-45). Auch unbekannte Karten werden publiziert (Z.222-225). Python-API `cards.register_card/list_cards/delete_card` in `.../rfid/cards/__init__.py` Z.34-135. [V]
- Bug: `register_card` schreibt bei `kwargs` den Wert von `args` (Z.121). [V]

## 7. Plugin-System und RPC
- Plugin = Python-Paket, per `jukebox.yaml: modules.named` (Name -> Paket) geladen; `jukebox.plugs` (`B src/jukebox/jukebox/plugs.py`): `@plugs.register` (Funktion/Klasse), `@plugs.tag` (Methoden), `@plugs.initialize`, `@plugs.finalize`, `@plugs.atexit`, `plugs.call_ignore_errors(package, plugin, method, args, kwargs)` (Modul-Doku Z.1-70, Z.449-520, 744). [V]
- Beispiel-Plugin mit Hooks: `B src/jukebox/components/synchronisation/rfidcards/__init__.py` Z.55-98: `components.rfid.reader.rfid_card_detect_callbacks.register(fn)` (Signatur `fn(card_id, RfidCardDetectState)`; Zustaende received/isRegistered/isUnkown, reader/__init__.py Z.24-56) und `components.playermpd.play_card_callbacks.register(fn)` (firstSwipe/secondSwipe, `playcontentcallback.py` Z.8-37). Weiteres Beispiel: `components/gpio/gpioz/plugin/connectivity.py` Z.71. [V]
- **Es gibt keinen Callback fuer "Karte entfernt"**; nur die Aktion `card_removal_action` (beliebiger RPC-Befehl, auch `package/plugin/method` eines eigenen Plugins). Ein eigenes Plugin kann so als Removal-Hook dienen. [V]
- Player-Zustand: Status wird alle 250 ms ueber Publisher `playerstatus` gesendet (`playermpd/__init__.py` Z.275-306). [V]
- Externe Steuerung: ZeroMQ REQ/REP, JSON (an jsonrpc angelehnt), TCP 5555 und WebSocket 5556; Events (PUB) auf TCP 5558 / WebSocket 5557 (`jukebox.default.yaml` Z.95-103; `jukebox/rpc/server.py` Z.8-83). CLI: `src/jukebox/run_rpc_tool.py`, C-Client `src/cli_client/pbc` (cli-client.md). Beispiel Aufruf: `./pbc -p host -o shutdown`. [V]

## 8. Resume
**Nein, kein eingebautes per-Ordner-/per-Karte-Resume in v3.6.0.** [V]
- `documentation/developers/status.md` Z.109: "[ ] Resume: Save and restore position" (offen).
- `playermpd/__init__.py`: `RESUME` wird fest auf "OFF" gesetzt (Z.293); die Methode `resume()` (Z.533-539) wird nirgends aufgerufen (grep); `last_played_folder` wird beim Start geleert (Z.219); `play_folder` macht `clear()`, fuellt neu, `play()` -> immer ab Titel 1 (Z.615-648).
- Was funktioniert: gleiche Karte erneut auflegen, solange derselbe Ordner zuletzt lief -> "Second Swipe" -> Default `second_swipe_action: toggle` (`jukebox.default.yaml` Z.82-85) -> `mpd.pause()`-Toggle setzt an der Pausenstelle fort (`play_card` Z.541-579). Ordnerwechsel dazwischen (oder Neustart) -> naechster Start ab Anfang. Positionsdaten (ELAPSED, CURRENTSONGPOS je Ordner) werden zwar in `music_player_status.json` gefuehrt (Z.283-296), aber nicht zum Fortsetzen genutzt. Eigenes Resume muss als Plugin/Erweiterung gebaut werden. [V/I]
- develop: Player-Backends umgebaut (`components/player/coordinator.py` Z.215 `resume()` delegiert nur), Doc-Kommentar identisch -> keine Aenderung sichtbar. [V]

## 9. Entwicklung ohne Pi
- Docker: `docker/docker-compose.yml` mit Containern `mpd`, `jukebox`, `webapp` (Web-UI auf http://localhost:3000, RPC 5555/5556, Pub 5557). Anleitung `B documentation/developers/docker.md` (Mac/Win/Linux, libzmq selbst bauen, Pulseaudio ueber TCP am Host, `docker/config/jukebox.overrides.yaml: playermpd.host: mpd`). [V]
- Gemockt/nicht verfuegbar: GPIO (Mock-Pins moeglich, `documentation/builders/gpio.md`), Temperatur etc. Doku sagt ausdruecklich: RFID/GPIO-Plugins werfen im Container Fehler, "ignorieren" (docker.md, Abschnitt `jukebox` container); fehlt rfid.yaml, wird eine leere erzeugt (reader/__init__.py Z.244-249). [V]
- Mock-Leser: `fake_reader_gui` (Tk-GUI, Buttons "Place card"/Single-place, "place-capable: yes", `mock_reader.md`; benoetigt Display + `ttkthemes`) - im Headless-Container nur mit X11-Weiterleitung nutzbar, besser lokal im venv. Kein headless Dummy-/Tastatur-Leser im Upstream. [V]
- Fuer Kartenlogik im Container: (a) eigenes triviales Modul (FIFO/TCP/pty als Quelle, auch das eigene `tobi_serial` gegen `socat`-pty), (b) `generic_usb` laeuft auch auf Linux-Desktop (`development-environment.md`: "USB RFID Readers will work"; im Container Device durchreichen, docker.md "Testing evdev devices"), (c) Karten ohne Leser per RPC ausloesen (`player.ctrl.play_card`). Unit-Tests: `test/` (cfghandler, evdev, gpioz). [V/I]

## 10. Issues/Diskussionen
- #2324 (offen) place_not_swipe resumt per Taste ohne Karte: https://github.com/MiczFlor/RPi-Jukebox-RFID/issues/2324
- #2405 (zu) RC522 Karten nicht erkannt (rfid.yaml mit place_not_swipe): https://github.com/MiczFlor/RPi-Jukebox-RFID/issues/2405
- #1695 (zu) falscher Keyword fuer Card Removal Action: https://github.com/MiczFlor/RPi-Jukebox-RFID/issues/1695
- #684 (zu) Pause/Stop bei Kartenentfernung: https://github.com/MiczFlor/RPi-Jukebox-RFID/issues/684
- V2-Hintergrund: USB-Leser senden die ID nur einmal, Workaround war GPIO-Hack: https://github.com/MiczFlor/RPi-Jukebox-RFID/wiki/Stop-on-removal-with-USB-RFID-Reader ; Diskussion https://github.com/MiczFlor/RPi-Jukebox-RFID/discussions/1616
- Kein Issue gefunden, das genau "USB-Leser mit Wiederholung" in V3 behandelt. Issues nur per Websuche/Fetch gelesen, nicht per API. [unverifiziert]

## Empfehlung fuer den Leser-Anschluss
Beide Wege brauchen im Kern dasselbe Prinzip: **V3 erkennt Entfernen nur ueber das Ausbleiben wiederholter IDs** (Watchdog 1 s, Abschnitt 3). Ein spezieller "removed"-Code ist weder noetig noch hilfreich; er wuerde nur einen zweiten `pause` ausloesen. Der HID-Weg funktioniert also grundsaetzlich mit `generic_usb` + `place_not_swipe.enabled: true` + `card_removal_action: {alias: pause}`, wenn die Firmware die UID alle 250-300 ms als **Kleinbuchstaben-Hex ohne Sonderzeichen** + Enter tippt, `same_id_delay` bei 1,0 bleibt und Lesefehler ueberbrueckt werden.
Die Nachteile von HID sind real: feste QWERTZ-Tabelle mit 'X'-Ersatz (Z.131), kein `grab()` (Konsolen-Einstreuung [I]), Leser-Thread stirbt ohne Geraet beim Start, kein Rueckkanal. Ein serielles Modul (~60 Zeilen nach RDM6300-Vorbild) behebt diese Punkte, kostet aber eigenen Code im V3-Baum und muss ebenfalls zyklisch IDs liefern (oder pause direkt aufrufen).
Pragmatisch: zuerst HID (null Python-Code, sofort testbar mit echtem `generic_usb`), Firmware so schreiben, dass sie auch ein `ON <uid>`/`OFF`-Protokoll ueber USB-CDC koennte; wechseln auf serielles Modul, sobald Konsolen-Einstreuung, Layout-Probleme oder gewuenschtes Feedback (LED/Ton) stoeren. Resume ueber Ordnerwechsel hinweg fehlt in beiden Faellen (Abschnitt 8) und braucht ein eigenes Plugin.
