# Goldfisch-Review Stufe 9 — Umsetzungsreife

**Ziel:** `design_draft.md`, Abschnitt „Umsetzungsplan“ · **Maßstab:** EGM
implementation-readiness-standard · **Prüfer:** drei frische Agents
(Umsetzungsreife: Sonnet, technische Machbarkeit gegen echte Bibliotheken: Sonnet,
Stil: Haiku) · **Datum:** 2026-11-05

Gesamturteil: gut gegliedert, Abnahmen meist konkret. Scheitert aber an der
Regel „ein Agent muss nichts Wichtiges selbst entscheiden“: Schnittstellen und
Schemas entstehen erst beim Bauen, und zwei Sicherheitsziele (Lautstärke,
Update-Rückfall) sind technisch so nicht umsetzbar.

## Zusammengeführte Befunde und Vorschlag der Projektleitung

| # | Schwere | Befund | Vorschlag der Projektleitung |
|---|---|---|---|
| R1 | Blocker | Kern-Schnittstelle fehlt (Ereignis-/Befehlstypen, Aufrufmuster, Uhr, Player-Ereignisse); AP 1.2 braucht, was AP 1.3 definiert. | **Stufe 0 erweitern** um `docs/protocol/core-interface.md`: alle Ereignisse und Befehle mit Feldern, Aufruf `step(zustand, ereignis, jetzt) → (zustand, befehle)` je Teilautomat, Uhr als Parameter, Player-Ereignisse. |
| R2 | Blocker | Datenformate (`config.json`, `resume.json`, `unknown.json`, `serie.json`, `manifest.json`) und MQTT-Nachrichten ohne Felder und Beispiele. | **Stufe 0:** `docs/data-model.md` mit vollständigen Schemas + Beispiel-JSON; `docs/protocol/mqtt-v1.md` mit Themen, Nachrichten, QoS, retained, Ablaufzeit von Befehlen, Discovery-Namen. Goldfisch prüft Stufe 0 vor Stufe 1. |
| R3 | Blocker | `unknown.json`-Bestätigung hängt an MQTT (erst Stufe 3a); PUBACK kommt nur vom Broker, nicht von HA → Figur kann verloren gehen. | Schnittstelle „Ereignis-Ausgang mit Bestätigung“; Stufe 2 bestätigt über `tobibox sim`, Stufe 3a über MQTT: **Box veröffentlicht unbekannte Kennung dauerhaft je Kennung, HA bestätigt auf `…/ack`, erst dann löscht die Box** (ack-Thema kommt zurück, mit Grund). |
| R4 | Blocker | Liste der Vorleistungen von Tobias fehlt. | Tabelle „Von Tobias bereitzustellen“ je Stufe: verdrahteter Leser + echte `config.h` (Stufe 1), Homebrew-MPD am Mac, SSIDs, NAS-Pfad und Konten, HA mit Broker, Ablageort für Zugangsdaten, minisign-Schlüssel, Pi. |
| R5 | Blocker | „Harte Obergrenze in der MPD-Konfiguration“ gibt es nicht; MPD kennt keine Max-/Startlautstärke. | **Pi:** ALSA-`softvol` mit `max_dB` (`deploy/pi/asound.conf`) als harte Kappung + Startlautstärke vor MPD-Start per `ExecStartPost`/Dienst. **Mac:** nur die Klemmung im Dienst, offen so benannt. Test prüft Dienst-Klemmung; harte Kappung wird am Pi gemessen. |
| R6 | Blocker | Rückfall-Logik liegt in der Version, die ausfallen soll (Importfehler → nichts zählt); `Restart=`/`StartLimit*`/`OnFailure=` nicht festgelegt. | Kleines Wächter-Skript **außerhalb** von `releases/` (`/opt/tobibox/bin/guard.py`, kommt mit dem SD-Image, nie per Update ersetzt) als `ExecStartPre=`: zählt im Zustand `testing`, schaltet bei ≥ 3 zurück. Konkrete Werte für `Restart=on-failure`, `StartLimitBurst`, `StartLimitIntervalSec`, `OnFailure=`; Selbsttest-Frist über `Type=notify` + `TimeoutStartSec=300`. |
| R7 | Major | „ReplayGain nur dämpfend“ mit MPD/rsgain nicht garantierbar; rsgain ohne `-S` taggt alles neu → ständige Neuübertragung. | Aussage ändern: positiver Gain begrenzt durch Peak-Schutz (`replaygain_limit`) **und** die ALSA-Kappung (R5); `replaygain_preamp` 0, `replaygain_missing_preamp` −6 dB; rsgain Easy-Modus mit `-S`, Ziel −18 LUFS (ReplayGain-2.0-Bezug), Version fest; Container-Bild wird gebaut, QNAP-Architektur ist Vorleistung. |
| R8 | Major | PlatformIO: offizielle Plattform endet bei Core 2.0.17, 3.x nur über pioarduino; Flash-Größe SuperMini (4 MB); `native`-Build zieht Arduino-Code; Zeitkonstanten in gitignored `config.h`; Pfad zur Beispieldatei. | **pioarduino** mit festem Release; `board_upload.flash_size = 4MB` + Partitionstabelle; `native` mit `build_src_filter` nur auf `debounce`/`protocol` (ohne Arduino-Typen); Zeitkonstanten in eingechecktem `timing.h`, nur Pins/Passwort in `config.h`; Testdaten-Pfad fest. |
| R9 | Major | USB „nur CDC“ unklar; eigene USB-Kennung geht nur mit TinyUSB (dann kein Auto-Reset beim Flashen); Schreiben blockiert bis 100–250 ms, wenn niemand liest; DTR/RTS beim Öffnen. | **HWCDC (USB-Serial/JTAG) bleibt** (bequemes Flashen); stabiler Name über die Seriennummer des Chips: `/dev/serial/by-id/…Espressif…<Seriennummer>…` bzw. udev-Regel nach Seriennummer; `setTxTimeoutMs(0)` (Zeilen verwerfen statt blockieren); pyserial ohne DTR/RTS; Mac-Pfad per Suchmuster `cu.usbmodem*`. |
| R10 | Major | Zeitbudget: NTAG 176 ms Zyklusarbeit, RF-Befehle bis 500 ms, Abheben-Worst-Case ≈ 1,41 s; Messung über Protokoll misst nicht den hörbaren Ton; MPD-Puffer fehlen. | Budget mit Messwerten aus `uebergabe.md` neu rechnen; Messung am Ausgang (Mikrofon/Loopback) als Methode; MPD-Puffer fest (`audio_buffer_size`, `buffer_before_play` klein); Rückfallregel = „Arbeit pro Zyklus senken“ (zuletzt gelesenes Protokoll zuerst, kürzere Befehlszeitgrenze), dann Rückfrage an Tobias. |
| R11 | Major | MPD-Mechanismus für Folgenende/Pause/Resume offen; asyncio-Client, pyserial, paho-Threading, `tomli`. | Warteschlange enthält **nur die aktuelle Folge**; Folgenende → MPD stoppt, Dienst setzt Zeiger; Resume per `seek` direkt auf Position (kein 0:00-Blitzer). `mpd.asyncio.MPDClient`; pyserial in eigenem Thread mit Queue; `paho-mqtt ≥ 2` mit `loop_start` + `call_soon_threadsafe`; `tomllib` statt `tomli`. |
| R12 | Major | HA: Upload-Grenze 16 MiB → Streaming nötig; Panel-/Static-API; `manifest.json`-Pflichtfelder; pytest-HA an HA-/Python-Version gebunden; SMB-I/O im Executor. | Upload als Stream in Blöcken; `async_register_static_paths` + `panel_custom`; `manifest.json` mit `version`, `dependencies`; **HA-Version fest** (aktuelle stabile), eigene venv und eigener CI-Job; Datei-I/O über `async_add_executor_job`; Upload über Nabu Casa am Handy prüfen (Risiko). WebSocket-Befehle als Vertrag (Stufe 3a, vor 3.1/3.2). |
| R13 | Major | Sync: Transport/Konto offen (QNAP-SSH nur für Admins); „spielende Datei“-Mechanismus; `--partial-dir` im Medienordner; 20-%-Grenze ohne Zählung. | **rsync-Daemon auf dem QNAP mit `read only = yes`** über Tailscale; `--exclude` der spielenden Datei; `--partial-dir` außerhalb des Medienordners auf demselben Dateisystem; Löschgrenze per `--dry-run --itemize-changes` vorab gezählt. |
| R14 | Major | Ordnung/Umfang: AP 1.2 überladen, Dateien fehlen; Zeiger-Logik erst Stufe 2, aber CUJ 2 braucht sie; Testmedien; `sim.py` + Steuerweg (IPC) erst 3.3, aber `tobibox sim` schon Stufe 2; parallele APs ändern `core.py`. | AP 1.2 teilen (1.2a Kern/Protokoll/Leser, 1.2b Speicher/Bibliothek/Konfig/Protokoll/CLI); **Zeiger-Logik nach Stufe 1** vorziehen; Testmedien erzeugt der Test selbst (`box/tests/fixtures/`); `sim.py` mit Unix-Socket + JSON-Zeilen in **Stufe 2** anlegen, später erweitern; je Stufe ein Integrations-AP, das Änderungen an `core.py` zusammenführt. |
| R15 | Major | Firmware-Spezifikation dünn (Entpreller-Zustände, Fehlercodes, HB-Felder, Regex). | In `reader-v1.md` (Stufe 0): Entpreller-Zustandstabelle, vollständige Fehlercodes und HB-Felder, Kennungs-Regex (14443: 8/14/20 Hex, 15693: 16 Hex). |
| R16 | Major | Selbsttest-/Update-Details: minisign im CI, Test-Schlüssel, Manifest-Schema, Abhängigkeiten als `pip --target` + `PYTHONPATH`, Python-Version Pi OS. | Übernehmen; Abhängigkeiten nur reines Python (in AP 3.5 geprüft), `pip install --target`, Python-Minor-Version = Pi OS Bookworm (3.11). |
| R17 | Nit | journald `SyncIntervalSec` (bis 5 min Verlust); `python-systemd` ist C-Code; DRM-Prüfung mit `ffprobe` unzuverlässig; Mosquitto-ACL über `customize`; Tonie-Satz „schreibt nichts“ ungenau. | `SyncIntervalSec=30s`; JSON nach stdout → journald; DRM: Codec-Name (`drms`) bzw. 1-s-Probedekodierung; ACL-Weg laut Add-on-Doku; Satz: „hebt den Privacy-Modus auf, bis eine Toniebox ihn wieder setzt; schreibt keine Nutzdaten“, Testfall „gesperrt → offen“. |
| R18 | Major | Stil: Abnahmen als Satzketten, AP-Nummern 3.5/3.6 vertauscht, uneinheitliche AP-Form, unscharfe Aussagen. | Abnahmen als Listen; Nummern neu; jedes AP als Überschrift mit Modell, „Ergebnis“, Tabelle; restliche Stil-Vorschläge übernehmen. |

---

## Rohtext Umsetzungsreife (Sonnet)

REVIEW Implementation Readiness, Umsetzungsplan (Zeilen 1230-1596 von design_draft.md). Ergebnis: 15 Befunde (4 Blocker, 7 Major, 4 Nit). Ich habe nur gelesen, nichts geändert. Zeilennummern beziehen sich auf design_draft.md.

**Blocker**

1. **Blocker. AP 1.2, AP 1.3, Stufe 0 (1253-1264, 1284-1315). Die Schnittstellen zwischen Kern, Player und App fehlen.**
   - Stufe 0 liefert nur das Zeilenprotokoll (`reader-v1.md`). Die Typen in `events.py` (Ereignisse und Befehle des Kerns) schreibt AP 1.2 selbst.
   - Der Plan sagt nur "Katalog aller Quellen" (1289). Es gibt keine Feldliste, keine Signaturen und kein Muster, wie der Kern aufgerufen wird (z. B. `core.handle(event) -> list[Command]`).
   - Zeit-Eingang: Gibt es ein Tick-Ereignis, oder übergibt man `now`?
   - Wie `app.py` Befehle ausführt, ist offen. Die Typen für Player-Ereignisse legt AP 1.3 fest (655, 1311), aber `core` und `session` in AP 1.2 brauchen "Folge zu Ende" schon. Das ist ein Ordnungsproblem: AP 1.2 benutzt etwas, das AP 1.3 erst definiert.
   - Das verstößt gegen die Zero-Decision-Regel. Gleichzeitig verbietet der Plan, die Verträge eigenmächtig zu ändern (1242).
   - Empfehlung: In Stufe 0 eine Datei `docs/protocol/core-interface.md` (oder ein Abschnitt in `docs/data-model.md`) ergänzen. Sie enthält alle Ereignis- und Befehlstypen mit Feldern, die Kernsignatur und die Player-Ereignisse. Alternativ kommt `events.py` als Stufe-0-Artefakt von der Projektleitung.

2. **Blocker. Datenformate fehlen (Baustein 3 und Baustein 4, AP 1.2, 1304).**
   - `config.json`, `resume.json` und `unknown.json` haben keine Feldnamen, keine Verschachtelung und keine Beispiele. Für `serie.json` gibt es nur eine Aufzählung der Felder in Baustein 4 (928-932), aber keine Typen oder Beispiele.
   - Offen ist z. B.: Wie ist `uid → Eintrag` verschachtelt, und wie heißen die Felder für Aktion, Leise-Zeiten und Gute-Nacht-Dauer? Steht der Zeiger als `{folge, position_s}` oder in Millisekunden? Was bedeutet der "Zähler" in `resume.json`?
   - Das Schema ist die Schnittstelle zwischen Box (AP 1.2/2.x/3.3) und HA (AP 3.1) und zwischen Firmware-Tests und Kern. `docs/data-model.md` entsteht erst in AP 1.2 und wächst "mit jedem AP". Mit dieser Regel entscheidet der erste Implementierer das Schema allein.
   - Empfehlung: `docs/data-model.md` mit den vollständigen Schemas und Beispiel-JSON als Stufe-0-Vertrag festlegen. Die Schemas für `config.json` (inkl. Leise-Zeiten und Gute Nacht), `resume.json` und `unknown.json` brauchen sie ab Stufe 1 bzw. 2.
   - Dasselbe gilt für das MQTT-Payload-Format (`tobibox/config`, `event`, `cmd` mit Ablaufzeit, Status, Discovery-Namen). Es steht nur als Themenliste in Baustein 4 (977-990). Es wird in AP 2.2 (Befehls-Ablaufzeit) und in AP 3.1 und 3.3 gebraucht, also von zwei APs gleichzeitig. Empfehlung: `docs/protocol/mqtt-v1.md` als Vertrag in Stufe 0.

3. **Blocker. AP 2.2, Stufe 2 (1352-1358). `unknown.json` und der Lernmodus hängen an MQTT, das erst in Stufe 3a gebaut wird.**
   - "Eintrag erst nach Bestätigung des Brokers löschen" ist in Stufe 2 nicht testbar. `ha.py` entsteht erst in AP 3.3.
   - Der Plan sagt nicht, ob AP 2.2 eine Schnittstelle plus Fake-Broker baut oder einen Platzhalter mit sofortigem Löschen.
   - Auch die "Ablaufzeit des Befehls" ist ohne das cmd-Payload-Format (siehe Befund 2) nicht implementierbar.
   - Empfehlung: Eine Schnittstelle `EventSink.send(event) -> ack` festlegen. In Stufe 2 liefert `sim` ein Dummy-Ack aus der CLI, in 3a ersetzt `ha.py` es. Oder `unknown.json` in Stufe 2 ohne Bestätigungslogik bauen und das Löschen explizit nach AP 3.3 verschieben.

4. **Blocker. Externe Voraussetzungen für Tobias fehlen als Liste (Stufe 1, 3a, 3b).**
   - Der Go/No-Go (1410-1422) nennt nur Tailscale, den Broker, die NAS-Rechte und das minisign-Schlüsselpaar. Es fehlen:
     - ESP32-Hardware verdrahtet (Pins laut `config.h`), plus das echte Tonie-Passwort in der lokalen `config.h`. Ohne beides läuft AP 1.1 nicht gegen Hardware. Die Abnahme Stufe 1 setzt Tobias' Figuren voraus.
     - Der Mac mit Homebrew-MPD.
     - Eine HA-Testinstanz mit MQTT-Broker für die Entwicklung von AP 3.1 und 3.2. Die Tests laufen im Container (`pytest-homeassistant-custom-component`), die Abnahme am Handy braucht eine echte Instanz.
     - Der Name des Heim-WLANs und des Hotspots (SSIDs) für `net.py`.
     - Der NAS-Pfad und die Konten für rsync.
     - Ein Platz, wo Tobias die Zugangsdaten ablegt (`tobibox.toml`, MQTT-Passwörter).
   - Empfehlung: Eine Tabelle "Vorab von Tobias bereitzustellen" je Stufe aufnehmen, mit Frist.

**Major**

5. **Major. AP 1.1 (1268-1281). Die Firmware-Spezifikation ist zu dünn für die Zero-Decision-Regel.**
   - Es gibt keine Zustandstabelle für den Entpreller. `debounce.h/.cpp` wird nur durch Zeitkonstanten beschrieben, nicht durch Zustände.
   - Zu klären sind: Verhalten bei `fehler(code)` mitten in der Entprellung, das Verhältnis von "gesperrt liegt" zu "uid liegt", die Fehlercodes (`ERR code=…` beschreibt nur Beispiele, Zeile 628) und die Feld-Definitionen von `HB` (`hits`/`rejected`/`polls`). Die Spalte "Inhalt und Grund" nennt keine Schnittstellensignatur der Module.
   - Außerdem fehlt die USB-Kennung, die `99-tobibox-reader.rules` braucht (VID/PID, Produktstring). Ob die Firmware sie setzen kann, ist offen.
   - `README.md`, `main.cpp` und `reader.cpp` sind nicht mit Hardware testbar. Das ist hinnehmbar, die Abnahme am Mac deckt es ab. Der Plan sagt aber nicht, was im Container für `reader.cpp` gebaut wird (nur `esp32s3`-Build in CI).
   - Empfehlung: Die Entpreller-Zustandstabelle in `reader-v1.md` oder als Baustein-1-Tabelle aufnehmen, analog zur Sitzungstabelle. Fehlercodes und HB-Felder vollständig definieren.

6. **Major. AP 1.2 (1284-1305). Das AP ist überladen, und Dateien fehlen in der Liste.**
   - In einem AP stehen Kern, vier Teilautomaten-Hüllen, Protokoll, Reader, Store, Library, Config, Eventlog, CLI, fake_reader, Unit-Tests und Integrationstests. Es ist als Sonnet-AP schwer abnehmbar.
   - Nicht aufgelistet sind `box/src/tobibox/__init__.py`, `box/src/tobibox/__main__.py` bzw. der Einstiegspunkt, `box/tests/conftest.py`, die Testkonfiguration und die Teilautomaten `learn.py`, `quiet.py`, `bedtime.py`, `idle.py`.
   - Die Regel "Dateien außerhalb der Liste" gilt für die Schreibliste in Phase 5; fehlende Dateien kann der Agent nur eigenmächtig anlegen. Das widerspricht der Standard-Forderung nach einer exakten Dateiliste.
   - `core.py` verbindet vier Teilautomaten, von denen in Stufe 1 nur `session` existiert. Wie `core` die später folgenden `learn`, `quiet`, `bedtime`, `idle` einhängt (Plug-in-Schnittstelle), ist nicht festgelegt. Das ist eine Architekturentscheidung, die AP 4.x und 2.2 beeinflusst.
   - Empfehlung: AP 1.2 in 1.2a (events, core, session, volume, clock, protocol, reader, Unit-Tests) und 1.2b (store, library, config, eventlog, cli, fake_reader) teilen. Die Teilautomaten-Schnittstelle (z. B. `step(state, event, now) -> (state, commands)`) festlegen und die vollständige Dateiliste angeben.

7. **Major. AP 1.2 und AP 1.3 (1302-1303, 1311-1315). Test-Spezifikation und Ordnung.**
   - Die CUJ-Tests 1, 2, 5, 6, 8 und 13 brauchen die Wirkung von `PLACED` auf einen Zeiger und eine Serie (CUJ 1: "Folge 1 startet"). Zeiger-Logik und `resume.json` kommen aber erst in AP 2.1. Welche Resume-Logik gilt in Stufe 1: immer Folge 1? Das ist nicht gesagt.
   - Der Test `test_player_mpd.py` braucht ein echtes MPD und eine Audio-Ausgabe im Container. Dafür fehlen Angaben: Wie wird MPD gestartet (eigener `mpd.conf` für Tests, Null-Ausgabe)? Welche Testdateien (aus `box/medien-beispiel/` in AP 1.4, also später)? Damit gibt es eine Ordnungsabhängigkeit AP 1.3 → AP 1.4. Alternativ erzeugt der Test sie selbst; das steht nicht da.
   - Es gibt keine erwartete Test-Matrix (konkrete Eingabe/Ergebnis-Zeilen) für CUJ 6, 8 und 13. Der Plan verweist nur auf "Tabellen" aus Kern-Zuständen. Für CUJ 8 (verfälschte Kennung) ist das Verhalten der Firmware, nicht des Dienstes, maßgeblich; wie der Dienst-Test das nachstellt, ist unklar.
   - Empfehlung: Testmedien für Container-Tests als eigene Datei in AP 1.3 (`box/tests/fixtures/`) aufführen und Stufe-1-Resume-Verhalten festlegen (siehe Befund 8).

8. **Major. Ordnungsfehler Stufe 1/2 (1291, 1346-1350).** `session.py` und `core.py` werden in AP 1.2 gebaut und in AP 2.1 wieder geändert, ebenso `store.py` und `app.py`. Das Resume-Verhalten aus der Sitzungstabelle ("Zeiger laden") ist in Stufe 1 nicht definiert, obwohl der Test CUJ 2 ("Zeiger gespeichert") es voraussetzt. CUJ 3 und 4 sind aber erst Stufe 2. Empfehlung: Die Zeigerlogik (Laden, Speichern, 3 s Rücksprung, Regeln aus Zeilen 885-897) in Stufe 1 vorziehen, oder die Stufe-1-CUJ-Tests ausdrücklich auf "Zeiger noch nicht gespeichert" beschränken.

9. **Major. Stufe 3a (1426-1481). Die HA-Tests haben unklare Abnahmekriterien.**
   - Der Plan legt für `websocket_api.py` weder Nachrichtentypen noch Antwortformate fest. Das ist die Schnittstelle zwischen AP 3.1 (Backend) und AP 3.2 (Frontend, `tobibox-panel.js`) und wird parallel gebaut (vgl. 1185-1187).
   - Lit-Frontend: Es gibt keinen Build, keine Testumgebung und keine Browser-Tests. Die Seite ist im Container nicht prüfbar, die Abnahme ist nur "Vorführung am Handy".
   - Wie `ffprobe` im HA-Container verfügbar ist, ist nicht geklärt (HA OS hat es meist, aber unsicher), ebenso der Zugriff auf die NAS-Freigabe aus der Integration (Pfad-Mount) und wie die Tests das NAS simulieren.
   - Empfehlung: WebSocket-Befehle (Name, Eingabe, Ausgabe) in einem Vertrag festhalten. Für die Seite Mindest-Test-Kriterien festlegen (z. B. JS-Modul lädt, WebSocket-Aufrufe gegen Mock). Verfügbarkeit von `ffprobe` und der Mount als Voraussetzung nennen.

10. **Major. AP 3.3 und Stufe 4 (1446-1456, 1523-1530). Der gemeinsame Treiber `sim.py` ist nicht spezifiziert.**
    - Wie liefert `sim` "Tastatur/Terminal"-Eingänge an einen asynchronen Dienst? `tobibox sim power …` ist ein CLI-Befehl (separater Prozess?), während `sim.py` im Dienstprozess laufen müsste. Der IPC-Weg ist offen (Unix-Socket, Datei, stdin?).
    - Das Gleiche gilt für das Tool in AP 2.2 (`tobibox sim learn …`, 1355) und AP 2.3: Es existiert also schon vor `sim.py` (AP 3.3) ein Sim-Befehl. Das ist ein Ordnungsfehler, weil AP 3.3 den "gemeinsamen" Treiber erst später anlegt.
    - Die Tabelle in Baustein 3 (663) behauptet, `power` komme ab Stufe 3a, die Netzklassen-Logik bleibt unklar (AP 3.3 `net.py`).
    - Empfehlung: `sim.py` und den IPC-Mechanismus (z. B. Unix-Socket `~/tobibox/sim.sock` mit JSON-Zeilen) früh festlegen, in Stufe 2 anlegen (AP 2.2) und später nur erweitern.

11. **Major. AP 3.4 (1459-1465). Der Sync ist nicht ohne NAS/Tailscale testbar, und Einzelheiten fehlen.**
    - Genannt sind Tests "mit lokalem rsync-Ziel", das deckt Tailscale und SSH-Konto nicht ab. Auch `test_cuj09` ("Auflegen während Sync", Latenz unter Last) lässt sich im Container nur ohne reale CPU- und IO-Last nachstellen. Die Zeitgrenze ist dort nicht aussagekräftig; das gehört in den Pi-Probelauf.
    - Offen sind: das rsync-Aufrufmuster (Quelle, SSH-Schlüssel, Port), "spielende Datei nie ersetzen" (wie wird sie erkannt, über MPD `currentsong`, und wie wird die Datei vom Sync ausgenommen: `--exclude`?), und das Verhalten bei Abbruch.
    - Der Plan erwähnt auch nicht, wo die rsync-Zeitsteuerung ("zeitgesteuert") herkommt (Timer im Dienst, systemd-Timer?).
    - Empfehlung: rsync-Kommandozeile, Konto, Zeitplan und Erkennung der laufenden Datei festlegen. Die Latenz-Abnahme ausdrücklich in den Pi-Probelauf verschieben, im Container nur den Test, dass Kern-Ereignisse während des Syncs weiterlaufen.

**Nit / weitere Lücken**

12. **Major. AP 3.5 (1488-1501). Mehrere Update-Details bleiben offen.**
    - `test_update.py` prüft die Signatur mit `minisign`. Im Container muss `minisign` installiert sein, und es braucht ein Test-Schlüsselpaar. Das ist weder im Plan noch in AP 1.5 (CI) erwähnt.
    - Die systemd-Drop-ins (`rollback.conf`, `OnFailure=`, Zähler) sind im Container nicht ausführbar. Wie wird der Zähler gehalten (Datei? Wer schreibt ihn bei jedem Start: `ExecStartPre`)? Das ist offen. Das Ergebnis der Prüfung "Dienst beendet sich nach 5 min" ist per Unit-Test mit simulierter Uhr prüfbar, die systemd-Verdrahtung aber nicht (nur im Pi-Probelauf).
    - Die Manifest-Felder stehen in Zeile 1041 ("Version, Protokoll-Version, …"), aber ohne JSON-Schema.
    - Die Reihenfolge ist ungünstig: `selftest.py` wird in AP 2.3 gebaut und in 3.5 erweitert, der Update-Selbsttest "HELLO mit passender Protokoll-Version" braucht aber den Leser-Treiber (aus AP 1.2). Die Reihenfolge ist also gültig, aber Stufe 3b hängt von Stufe 3a nur wegen des Schlüsselpaars ab. Das AP 3.5 prüft "reines Python" (1043), nennt aber keine Methode und kein Ergebnisdokument.

13. **Nit. Pi-Probelauf, AP P.1 (1378-1408).** Das Aufsetzen auf einem echten Pi ist im Container nicht testbar. Das ist unvermeidlich, aber `install.sh` hat keine Abnahmekriterien außer "Prüfliste". `docs/betrieb/pi-probelauf.md` ist Haiku-Doku, soll aber die Prüfliste mit Soll-Werten (Tabelle 1393-1402) und Messmethoden enthalten. Die Messmethoden (wie wird "Auflegen unter Sync" gemessen, welches Werkzeug) fehlen. Außerdem fehlt die Vorbedingung "Pi 3A+ ist bestellt, Image-Auswahl (Pi OS Lite 64/32 Bit)" als Entscheidung. Die Soll-Werte sind nur ein Vorschlag, nicht bestätigt (1390): Tobias muss sie vor dem Start des AP festlegen.

14. **Nit. AP 1.5 (1326-1331).** Die CI nennt weder Python-Version noch Runner-Image. "pytest (mit MPD)" braucht `apt install mpd` im Workflow. Es fehlt `.github/workflows/` für die HA-Tests (`homeassistant/tests/`, ab AP 3.1) und die Änderung der CI in späteren Stufen. Die `.gitignore` enthält bereits `config.h` und `.pio/`; AP 1.5 darf also nur ergänzen. `docs/timing.md` (Stufe 1) taucht in keiner AP-Dateiliste auf, ebenso die Dokumente `docs/plan/` für den Plan-Nachzug (1521) und die Artefakte `docs/designs/box-software.md`.

15. **Nit. Dateilisten uneinheitlich.** Mehrere APs sind nur als Fließtext beschrieben (2.1, 2.2, 3.2, 3.6, 3.7, 4.x-Teile) und nennen keine Testdateinamen (z. B. "CUJ-Tests 3, 4 und 20" ohne Pfad, "Stromausfall-Test" ohne Datei). `core.py`/`session.py` werden in mindestens fünf APs geändert (1.2, 2.1, 2.3, 4.2, 4.4), das Kollisionsrisiko ist hoch bei parallelen Agents (4.1-4.4 sollen parallel laufen, 1531-1534). Empfehlung: Für parallele APs festlegen, wer `core.py` zusammenführt, oder die Integration von Eingängen ins `core` in ein eigenes AP bündeln.

**Gesamtbild:** Der Plan ist gut gegliedert, und die Abnahmen sind meist konkret. Er scheitert aber an der Zero-Decision-Regel bei den Schnittstellen und Schemas (Befunde 1-3, 5, 9, 10), weil diese erst während der Implementierung entstehen. Empfohlen: Stufe 0 um `core-interface`, `data-model.md` (Schemas) und `mqtt-v1.md` erweitern und diese vor Stufe 1 vom Goldfisch prüfen lassen. Dazu kommen die Liste der Vorleistungen für Tobias (Befund 4) und die Teilung von AP 1.2.

## Rohtext Technische Machbarkeit (Sonnet)

**Review Stufe 9, Linse „technische Details gegen echten Code und Bibliotheken“** (Ziel: `/home/user/Tobi_box/docs/egm/software-prototyp/design_draft.md`, ab „## Umsetzungsplan“)

Geprüft gegen `firmware/tonie_test/`, `research_pn5180_esp32s3.md`, `research_mpd_bausteine.md`, `docs/plan/uebergabe.md`, `stueckliste-und-psp.md`, die PN5180-Bibliothek und arduino-esp32. Webquellen sind unten verlinkt. Nichts wurde ausgeführt oder geschrieben. Aussagen, die ich nur aus eigenem Wissen kenne, sind als „unverifiziert“ markiert.

## Blocker

**1. Die „harte Obergrenze“ der Lautstärke in der MPD-Konfiguration gibt es nicht (Ziel 10, AP 1.3, 1.4, P.1)**
- Der Plan verlangt in `deploy/pi/mpd.conf`, `mpd.mac.example.conf` und im Test `test_player_mpd.py` eine „feste Startlautstärke“ und eine „harte Obergrenze“.
- Das MPD-Handbuch kennt weder eine Maximal- noch eine Startlautstärke. `mixer_type` kennt nur `hardware`, `software`, `null` und `none`. `hardware` ist laut Handbuch nur für ALSA, OSS und PulseAudio belegt, also nicht auf dem Mac.
- Ein Software-Mixer bei 100 % ist volle Digitalskala. Nach einem Dienst-Absturz bleibt MPD auf dem zuletzt gesetzten Wert, ohne Deckel.
- Eine echte Kappung geht nur in ALSA, etwa mit `softvol` und `max_dB` in `asound.conf`. Diese Datei steht in keiner Dateiliste. Auf dem Mac gibt es keine Entsprechung.
- Der Test im Container mit echtem MPD kann die Grenze deshalb nicht prüfen. Das Abnahmekriterium „auch nach Absturz des Dienstes“ ist so nicht erfüllbar.
- Empfehlung:
  - Den Mechanismus festlegen: ALSA-`softvol` mit `max_dB` auf dem Pi, plus ein `ExecStartPre` oder `ExecStartPost` im MPD-Dienst, der die Startlautstärke setzt.
  - `deploy/pi/asound.conf` in die Dateiliste aufnehmen.
  - Für den Mac ehrlich schreiben, dass dort nur die Dienst-Klemmung gilt.
- Quelle: [MPD-Handbuch](https://mpd.readthedocs.io/en/latest/user.html).

**2. Der Rückfall liegt in der Release, die ausfallen soll (Update, AP 3.5, `rollback.conf`)**
- Der Startzähler und die Entscheidungsfunktion „bleiben oder zurück“ sind „eine kleine Python-Funktion“. Der Zähler zählt in der Zustandsdatei, und der Dienst läuft aus `current/`.
- Hat die neue Version einen Importfehler, wird nichts gezählt und nichts zurückgestellt. Das ist genau der Fall, den der Rückfall abdecken soll.
- `OnFailure=` greift außerdem nur, wenn die Unit nach `failed` geht. Mit `Restart=on-failure` oder `Restart=always` aus `tobiboxd.service` kommt sie dorthin erst über das `StartLimit`. Dessen Standardwerte sind 5 Starts in 10 s.
- Die Reihenfolge von `Restart`, `StartLimitBurst`, `StartLimitIntervalSec` und `OnFailure=` ist nicht festgelegt.
- Empfehlung:
  - Zähler und Entscheidung in ein kleines Skript außerhalb von `releases/` legen, zum Beispiel `/opt/tobibox/bin/guard.py`. Es kommt mit dem SD-Image und wird nie per Update ersetzt.
  - Es läuft als `ExecStartPre=`, erhöht den Zähler und stellt bei Zähler ≥ 3 den Verweis zurück.
  - Die Werte von `Restart=` und `StartLimit*` und die Zielunit von `OnFailure=` konkret festlegen.
  - Die 5-min-Frist des Selbsttests über `TimeoutStartSec` mit `Type=notify` abbilden, oder den Weg benennen.

## Major

**3. „ReplayGain nur dämpfend“ ist mit diesen Mitteln nicht garantierbar (D6, „Lautstärke“, AP 3.8, `test_replaygain_config.py`)**
- `replaygain_preamp` 0 verhindert keine positiven Tag-Werte. MPD wendet positiven Gain an und begrenzt nur über `replaygain_limit` per Peak-Tag. Das Handbuch sagt nichts zu „nur dämpfend“.
- rsgain hat keine „Max-Gain ≤ 0 dB“-Einstellung. `-m` ist der Peak-Level für den Clipping-Schutz, `-c` wählt den Clip-Modus. Ein „konservativer Ziel-Pegel“ macht sehr leise Dateien trotzdem positiv. Der Test „Max-Gain ≤ 0 dB“ prüft damit nichts Existierendes.
- Läuft der 15-min-Zeitplan ohne `-S` (`--skip-existing`), werden alle Dateien immer wieder neu getaggt und von rsync erneut übertragen. Das widerspricht der Annahme „einmal nachübertragen“ im Risiko „Drei Schreiber“. Ob `-S` im Easy-Modus liegt, hängt von der Version ab.
- Empfehlung:
  - Die Behauptung ändern in „positiver Gain begrenzt durch Peak-Schutz und durch die softvol-Kappung aus Befund 1“.
  - Falls wirklich nur Dämpfung gewollt ist, `replaygain_missing_preamp` und `replaygain_preamp` negativ setzen und den Ziel-Pegel mit Messwerten begründen.
  - rsgain-Aufruf und Version festschreiben, mit `-S`.
  - Eine Container-Basis festlegen: Es gibt kein offizielles rsgain-Image, es muss gebaut werden, und die QNAP-CPU-Architektur ist offen.
- Quellen: [MPD-Handbuch](https://mpd.readthedocs.io/en/latest/user.html), [rsgain-Manpage](https://www.mankier.com/1/rsgain).

**4. PlatformIO-Pinning und Board sind unterbestimmt (AP 1.1, `platformio.ini`)**
- Die Recherche stützt sich auf arduino-esp32 v3.x, zum Beispiel `USBHIDKeyboard` und die `HWCDC`-Interna. Die offizielle PlatformIO-Plattform `espressif32` endet bei Arduino-Core 2.0.17. Für 3.x braucht es das Fork [pioarduino](https://community.platformio.org/t/esp32-arduino-core-3-x-and-platformio-status/42008). Das ist eine Abhängigkeits-Entscheidung, die der Plan dem Implementierer überlässt.
- Der SuperMini hat 4 MB Flash (laut Recherche). Das Board `esp32-s3-devkitc-1` ist meines Wissens auf 8 MB voreingestellt (unverifiziert). `board_upload.flash_size` und die Partitionstabelle müssen explizit gesetzt werden, sonst droht ein Bootloop.
- Für die `native`-Umgebung braucht es `build_src_filter` oder `test_build_src`. Sonst zieht `pio test` `main.cpp` und `reader.cpp` mit `Arduino.h` und `PN5180.h` in den Hostbuild. `debounce.cpp` und `protocol.cpp` müssen frei von Arduino-Typen wie `String` bleiben.
- Die Zeitkonstanten stehen laut Baustein 1 in `config.h`. Die ist gitignored, und CI hat nur `config.example.h`. Die Tests und der CI-Build brauchen entweder einen Schritt `cp config.example.h config.h` oder eine eingecheckte `timing.h`. Empfehlung: Zeitkonstanten aus `config.h` herauslösen.
- `test_protocol` liest `docs/protocol/reader-v1-examples.txt` außerhalb des PlatformIO-Projekts. Der Pfad (`../../docs/...`, Arbeitsverzeichnis von `pio test`) ist nicht festgelegt.

**5. USB-Modus „nur CDC“ ist nicht eindeutig, und die Recherche empfiehlt hier das Falsche (Baustein 1, AP 1.1, P.1 `99-tobibox-reader.rules`)**
- Mit HWCDC (`ARDUINO_USB_MODE=1`, USB-Serial/JTAG) sind VID, PID und Produktstring fest. Sie lassen sich nicht ändern. Die Regel „eigene USB-Kennung aus der Firmware“ und der Pfad `/dev/serial/by-id/…tobibox…` gehen damit nicht.
- Eigene Kennung geht nur im TinyUSB-Modus mit `USB.VID`, `USB.PID`, `USB.productName` und `USB.manufacturerName`. Dann braucht es `-DARDUINO_USB_MODE=0 -DARDUINO_USB_CDC_ON_BOOT=1`. Die Recherche (§4) empfiehlt für HID+CDC `CDC_ON_BOOT=0` und `USBSerial`. Für „nur CDC“ ist das falsch.
- Im TinyUSB-Modus gibt es kein Auto-Reset beim Flashen (BOOT und RST von Hand), und ein hängender Sketch lässt sich schlechter retten.
- Die Schreibzugriffe blockieren, wenn der Host nicht liest. Im Quellcode ist `tx_timeout_ms` bei HWCDC 100 ms (`HWCDC.cpp:130`) und bei USBCDC 250 ms (`USBCDC.cpp:105`). Läuft `tobiboxd` nicht oder startet neu, hängt jede `HB`-Zeile und das Entprell-Timing bis zu 100 bis 250 ms. Bei HWCDC sind es bis zu 20 Timeouts in Folge (`HWCDC.cpp:732`). Empfehlung: `setTxTimeoutMs(0)` oder eine Tx-Pufferstrategie festlegen.
- pyserial setzt beim Öffnen DTR und RTS. Bei USB-Serial/JTAG kann das einen Reset auslösen (unverifiziert). Vorgeben: `dsrdtr=False, rtscts=False` und DTR/RTS vor dem Öffnen auf False.
- Am Mac ändert sich der `/dev/cu.usbmodem…`-Name je nach Port. `tobibox.mac.toml` braucht deshalb einen Glob oder Auto-Suche.

**6. QoS 1 und „Broker hat bestätigt“ reichen für „HA hat die Figur“ nicht (CUJ 7a, `unknown.json`, AP 2.2, 3.3)**
- Ein PUBACK kommt vom Broker, nicht von HA. HA abonniert normalerweise ohne persistente Sitzung. Sind HA oder die Integration beim Eintreffen offline oder werden gerade neu gestartet, sendet der Broker die Nachricht nicht nachträglich zu.
- Die Box löscht den Eintrag trotzdem, die neue Figur geht verloren.
- Empfehlung:
  - Entweder die Box veröffentlicht `event` als retained auf einem Topic je Kennung und HA bestätigt per `…/ack`, und erst dann löscht die Box.
  - Oder die Integration abonniert mit einer persistenten Sitzung und festem `client_id`. Die HA-MQTT-Schicht erlaubt das nur eingeschränkt, das ist zu prüfen.
- Das Ereignis „abgelehnte Liste“ ist davon gleichermaßen betroffen.

**7. Das Zeitbudget (Ziel 2) ist mit den vorliegenden Messwerten und der Messmethode nicht sicher**
- `uebergabe.md` nennt für eine NTAG-Karte 176 ms Lesezeit, für einen gesperrten Tonie 137 ms und für einen offenen Tonie 58 ms. Die Lesezeit der NTAG-Karte schließt den vorgeschalteten 15693-Fehlversuch ein, denn `pollOnce` probiert bei nichts Aufliegendem zuerst ISO 15693.
- Ein „Abfragezyklus 150 ms“ als Rückfallregel (Baustein 1) ist damit für den ersten Treffer physikalisch nicht erreichbar, solange 176 ms Arbeit im Zyklus stecken. Außerdem kann die Bibliothek `setRF_on` und `setRF_off` bis zu 500 ms blockieren (`PN5180.cpp:595ff`, `628ff`). `reset()` braucht mindestens 6 ms plus Hochlaufwartezeit.
- Die Worst-Case-Rechnung beim Abheben ist knapp: REMOVED wird erst am Ende des Zyklus nach den 1,1 s ausgewertet, also bis 1,1 s + 1 Zyklus (0,2 s) = 1,3 s. Dazu kommen die Übertragung und der Pausenbefehl von bis zu 100 ms. Das ergibt rund 1,41 s gegen 1,5 s. „≈ 1,3 s“ im Plan ist optimistisch.
- Die Messung „über das Ereignisprotokoll“ misst höchstens das MPD-`play`-Kommando, nicht den hörbaren Ton. MPD-ALSA-Puffer (Standard `buffer_time` 500 ms laut meiner Kenntnis, unverifiziert), CoreAudio-Puffer und `buffer_before_play` fehlen im Budget.
- Empfehlung:
  - Die Messung mit dem Audio-Ausgang festlegen, etwa Schleife auf dem Ausgang oder Mikrofonmessung am Pi.
  - Einen konkreten MPD-Wert für `audio_buffer_size`, `buffer_time` und `buffer_before_play` angeben.
  - Die Rückfallregel in „Zyklus-Arbeitszeit reduzieren“ umformulieren, zum Beispiel das 15693-vor-14443-Reihenfolge-Caching nach Typ des zuletzt Gelesenen.

**8. Beim Folgenende, bei „Pause nach jeder Folge“ und beim Resume ist der MPD-Mechanismus nicht festgelegt (AP 1.3, 2.1)**
- Der Plan sagt nur „Ereignis ‚Folge zu Ende‘“. Es fehlt, wie die Warteschlange aufgebaut wird.
- Lädt man die ganze Serie, spielt MPD die nächste Folge sofort an, bevor der Dienst pausieren kann. Das ergibt einen hörbaren Aussetzer, und die Entscheidung A wird verletzt. Mit `single oneshot` (MPD ≥ 0.21) geht MPD nach der Folge in `stop`, nicht in `pause`. Der Zustand „Position 0 der nächsten Folge“ muss dann selbst gesetzt werden.
- Ein `play` gefolgt von `seekcur` spielt kurz von 0:00. Alternativ `seek <songpos> <time>`, wobei Verhalten und Latenz zu messen sind.
- Der Dienst läuft mit `asyncio`, aber `python-mpd2` hat zwei Clients: einen blockierenden und `mpd.asyncio.MPDClient`. Welcher gilt, steht nicht da.
- Weitere offene Entscheidungen im Abhängigkeitssatz von `pyproject.toml`:
  - pyserial unter asyncio braucht `pyserial-asyncio` oder einen Thread.
  - `paho-mqtt` ≥ 2.0 verlangt `callback_api_version`. Der Plan nennt keine Version.
  - paho läuft in einem eigenen Thread (`loop_start`) und braucht die Brücke `call_soon_threadsafe`.
  - `tomli` ist ab Python 3.11 durch `tomllib` überflüssig.

**9. HA-Upload und Integrations-API: mehrere Stolpersteine (AP 3.1, 3.2, Baustein 4)**
- Der HA-HTTP-Server hat `client_max_size` 16 MiB (`MAX_CLIENT_SIZE`, meine Kenntnis, unverifiziert). Hörspielfolgen sind als mp3 oft 30 bis 60 MB, als FLAC deutlich mehr.
  - Der Endpunkt muss `request.multipart()` im Stream in Blöcken auf die NAS-Datei schreiben, nicht `request.post()`.
  - Ob Nabu Casa Remote UI große Uploads durchlässt, ist zu prüfen.
- Statische Dateien für das Panel: `hass.http.register_static_path` ist veraltet (meines Wissens ersetzt durch `async_register_static_paths` mit `StaticPathConfig`). Das Panel wird über `panel_custom.async_register_panel` registriert. Das gehört in die Beschreibung von `__init__.py`. `manifest.json` braucht zwingend `version`, außerdem `dependencies` mit `mqtt`, `http`, `panel_custom`, `websocket_api`.
- `pytest-homeassistant-custom-component` ist an eine bestimmte HA-Version und deren Python-Version gebunden (HA ≥ 2025.2 verlangt Python 3.13, meine Kenntnis). Der Box-Dienst läuft auf dem Pi mit Python ≥ 3.11. Beide Testsuiten brauchen getrennte venvs und eine getrennte CI-Matrix. `ci.yml` ist in AP 1.5 definiert und wird in Stufe 3a nicht ergänzt.
- Die Dateien werden über eine in HA eingehängte Netzwerkfreigabe geschrieben. Dort fehlen Angaben zu `fsync` und Rename-Semantik der SMB-Freigabe. Blockierende Datei-I/O gehört in `hass.async_add_executor_job`.

**10. Sync: Transport, Lesekonto und „spielende Datei nie ersetzen“ sind nicht festgelegt (AP 3.4, AP 3.6)**
- Welcher rsync-Weg läuft über Tailscale zum QNAP? SSH-rsync bräuchte auf QNAP ein SSH-Konto, und QNAP erlaubt SSH nur für Admin-Gruppen, also ein Konto ohne Read-only-Garantie. Ein rsync-Daemon mit `read only = yes` passt zum Plan „NAS-Konto nur lesend“. Der Plan sagt nichts dazu.
- „Nie ersetzen“ lässt sich mit `--exclude=<spielende Datei>` umsetzen. Das schützt dann auch vor `--delete`. Der Mechanismus fehlt im Plan. Technisch sind Ersetzen und Löschen per Rename für den laufenden Dekoder unkritisch, weil die geöffnete Datei bleibt. Das Risiko liegt eher bei einer Datei, die erst nach dem Start des Titels aktualisiert wird.
- `--partial-dir` und `--delay-updates` liegen standardmäßig im Zielordner. MPD indexiert versteckte Ordner meines Wissens mit (unverifiziert), also halbe Dateien im Datenbestand. Empfehlung: `--partial-dir` auf einen absoluten Pfad am selben Dateisystem außerhalb von `music_directory`, oder `.mpdignore`.
- Die 20-%-Löschgrenze braucht eine Zählung vorab, etwa mit `--dry-run --itemize-changes` und Auswertung. Der Plan sagt nicht, wie sie ermittelt wird.

## Nit

**11. Das Protokoll „übersteht einen Stromausfall“ nur eingeschränkt (Ziel 6, `journald-tobibox.conf`)**
- journald schreibt nach `SyncIntervalSec` (Standard 5 min) auf die Platte, nur Einträge ab `crit` sofort (meine Kenntnis, unverifiziert). Bis zu 5 min Protokoll sind bei Stromausfall weg. Kürzeres `SyncIntervalSec` bedeutet mehr SD-Schreibvorgänge, was das Schreibbudget berührt. Der Plan sollte den Wert nennen.
- `JournalHandler` aus `python-systemd` ist eine C-Erweiterung und passt nicht zu „auf dem Pi wird nichts gebaut“. Einfacher: JSON-Zeilen nach stdout mit `StandardOutput=journal`.
- Gleiches Thema bei der Paketierung: „fertig gebaute Abhängigkeiten“ funktionieren nur als `pip install --target` mit `PYTHONPATH`, nicht als venv (nicht verschiebbar). Im Plan fehlt `ExecStart` mit `PYTHONPATH`, und die Python-Minor-Version von Pi OS (Bookworm: 3.11) muss mit der des Build-Rechners übereinstimmen.

**12. Der DRM-Check mit `ffprobe` (D5, `media.py`) erkennt iTunes-DRM vermutlich nicht**
- `ffprobe` öffnet geschützte `.m4p`-Container meist erfolgreich und meldet nur einen Codec `drms`, der sich nicht dekodieren lässt (unverifiziert). Empfehlung: Codec-Name auswerten oder einen Probe-Dekodierlauf (`ffmpeg -t 1 -f null`) vorschreiben.
- `ffprobe` ist in HA OS im Core-Container vorhanden, in HA Container oder Core nicht zwingend. Die Annahme sollte dokumentiert werden.

**13. Mosquitto-ACL: machbar, aber der Weg im Plan stimmt nicht (AP 3.1, `acl.example`, `mqtt-konten.md`)**
- Laut Add-on-Doku geht es nur über `customize.active: true` und `/share/mosquitto/acl.conf` mit `acl_file` und einer Datei mit `topic readwrite …` je Benutzer. Die Benutzer `homeassistant` und `addons` brauchen unbeschränkten Zugriff.
- Konten laufen als HA-Benutzer oder über die `logins`-Option. Die Box-Konten sollten kein HA-Admin sein.
- Das Beispiel muss diese Dateien und Pfade nennen, nicht nur „acl.example“.
- Quelle: [Mosquitto-Add-on-Doku](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md).

**14. Dateiliste-Lücken (Standard „exakte Pfade“)**
- Bei `test_debounce/`, `test_protocol/`, `box/tests/unit/` und `box/tests/cuj/test_cujXX_*.py` stehen Verzeichnisse oder Platzhalter-Globs statt konkreter Dateinamen.
- Fehlen: `deploy/pi/asound.conf` (Befund 1), `box/src/tobibox/__init__.py`, `homeassistant/hacs.json` oder Vergleichbares, `box/tests/conftest.py`, die Wartung von `.github/workflows/ci.yml` in Stufe 3a, und `firmware/tobibox-reader/test/*` als Unity-Einstiegsdateien.
- Die Modultabelle nennt `learn.py`, `idle.py`, `led.py`, `controls.py` usw. im Pfad `box/src/tobibox/`. Die Datei `core.py` wird in AP 1.2 angelegt und in 2.1, 2.3 und 4.2 geändert. Das verlangt eine Reihenfolge der APs innerhalb einer Stufe, die nirgends steht.

**15. Aussagen zum Tonie-Chip (Baustein 1) stimmen so nicht ganz**
- „Schreibt nichts auf die Figur“: `disablePrivacyMode` ändert den Zustand des Chips dauerhaft. `uebergabe.md` hält fest: „Einmal entsperrt bleibt er offen, bis eine echte Toniebox ihn wieder sperrt.“ Der Satz im Plan ist ungenau. Richtig wäre: Die Box schreibt keine Nutzdaten, hebt aber den Privacy-Modus auf, bis eine Toniebox ihn wieder setzt.
- Folge für Debouncer und Tests: Nur das erste Auflegen eines Tonies läuft über den Entsperrweg. Danach antwortet er wie ein offener Chip, und die Testfälle für „gesperrt → uid“ brauchen diesen Übergang.
- Die Recherche weist darauf hin, dass die Bibliothek für SLIX2 geschrieben ist und der Befehlssatz für SLIX-L unbestätigt ist. Der Plan stützt das auf den Test vom 04.11. (`uebergabe.md`), das ist also gedeckt. Der Satz „Tonies enthalten SLIX-L“ im Plan bleibt aber ohne Datenblatt-Beleg.
- Das Kennungs-Regex ist nicht angegeben. NTAG-UIDs haben 4, 7 oder 10 Bytes (8, 14 oder 20 Hex-Zeichen), ISO 15693 hat 16. Der Plan sagt nur „prüft (Regex)“, die Regel für 14443 fehlt.

## Kurzfazit
Die Blocker 1 und 2 betreffen Sicherheitsziele (Kinderohren, Update-Rückfall) und lassen sich mit dem jetzigen Wortlaut nicht umsetzen. Befunde 3 bis 10 sind Entscheidungen, die der Plan dem Implementierer überlässt. Das widerspricht der Zero-Decision-Regel.

Quellen: [MPD-Handbuch](https://mpd.readthedocs.io/en/latest/user.html), [Mosquitto-Add-on](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md), [PlatformIO und Arduino-Core 3.x](https://community.platformio.org/t/esp32-arduino-core-3-x-and-platformio-status/42008), [rsgain-Manpage](https://www.mankier.com/1/rsgain).

## Rohtext Stil (Haiku)

## Style-Goldfisch: Review „## Umsetzungsplan“ (Zeilen 1230–1596)

Geprüft: `/home/user/Tobi_box/docs/egm/software-prototyp/design_draft.md`, nur der Abschnitt Umsetzungsplan. Zur Kontrolle gelesen: Begriffe (Zeilen 30–111) sowie die Stellen, auf die der Abschnitt verweist (CUJ-Liste Zeile 306, Baustein 1 Zeitbudget Zeile 589, Rückfallregel Zeile 604, Abschnitt „Update“ Zeile 1034, V3-Entscheidung Zeilen 1121–1156).

**1. Major | Zeilen 1333–1342, 1370–1374, 1475–1481, 1517–1521, 1581–1587 | Abnahmen als Satzketten mit Semikolons**
Rationale: Jede Abnahme ist ein Satz mit vier bis sechs Teilprüfungen, getrennt durch Semikolons. Der Leser kann nicht sehen, welche Punkte einzeln bestanden sein müssen. In Zeile 1339–1342 ist zudem nicht klar, welcher Wert zu welchem Schritt gehört: fünf Schritte (Lesen, Entprellen, Entsperren, Übertragen, MPD-Start) stehen drei Werten gegenüber.
Umschreibung (Abnahme Stufe 1):
- Alle CUJ-Tests und übrigen Tests sind grün.
- Tobias führt am Mac mit echtem Leser CUJ 1, 2, 5, 6, 8, 13 vor, darunter einen Leser-Neustart (USB-Kabel bei spielender Figur ziehen und stecken; ebenso mit Abheben während der Unterbrechung).
- Die Lautstärke-Grenze wirkt, auch beim Start und nach einem Dienst-Absturz.
- Der Test „Grenze wird nie überschritten“ ist grün.
- Das Ereignisprotokoll zeigt die Zeitgrenzen eingehalten.
- `docs/timing.md` enthält die Messung. Soll-Werte je Schritt: Die Zuordnung der drei Werte (1,0 s / 1,5 s / 1,0 s) zu den fünf Schritten ist vorher festzulegen.
Gleiches Muster für die anderen Abnahmen.

**2. Major | Zeilen 1268, 1346, 1440, 1467, 1488 | Nummerierung und Format der APs uneinheitlich**
Rationale: AP 3.5 steht in Stufe 3b (Zeile 1488), AP 3.6 in Stufe 3a (Zeile 1467). Die Reihenfolge 3.1–3.4, 3.6, dann 3.5 ist für einen neuen Leser verwirrend. Die APs haben außerdem drei Formen: fett als Titel mit Tabelle (1.1, 1.2), fett mit Fließtext in einem Absatz (2.1, 2.2) und fett mit Fließtext ohne Tabelle (3.2, 3.5).
Umschreibung: AP 3.5 (Tailscale und NAS) vor 3b setzen und Update auf 3.5 ff. nach Stufe 3a folgen lassen, oder Update als AP 3.5 in 3a belassen und Nummern durchgehend setzen. Jeder AP als Überschrift `#### AP x.y <Name> (<Modell>)`, darunter eine Zeile „Ergebnis:“ und eine Tabelle oder Liste.

**3. Major | Zeile 1244 | „Jedes AP ergänzt `docs/data-model.md`“ stimmt nicht**
Rationale: Die APs 1.4, 1.5, 3.2, 3.6, 3.7, 3.8, 4.1–4.6 und P.1 ändern kein Schema. Die Regel ist zu allgemein und widerspricht den Tabellen.
Umschreibung: „Jedes AP, das ein Schema einführt oder ändert, ergänzt `docs/data-model.md` um dieses Schema und die Regeln aus Stufe 0.“

**4. Major | Zeilen 1247–1248 | „Module zeigen nur nach innen zu `events` und `core`“**
Rationale: „nach innen“ ist keine Angabe, die sich prüfen lässt. Gemeint ist offenbar ein Import-Verbot. Ein Agent kann danach nicht eindeutig umsetzen.
Umschreibung: „Module importieren nur `events` und `core`. Nur `app.py` importiert alle Module (Baustein 3).“

**5. Major | Zeilen 1527–1529 | Stufe-4-Einleitung nennt nur die APs 4.1–4.4**
Rationale: AP 4.5 (Leise-Zeiten) und AP 4.6 (Gute-Nacht-Karte) fehlen im Satz „Die APs 4.1–4.4 bleiben getrennt (parallel baubar)“. Ein Leser weiß nicht, ob sie parallel laufen dürfen.
Umschreibung: „Die APs 4.1–4.6 sind getrennt voneinander baubar. Jeder trägt nur seinen Eingang in `sim.py` ein.“

**6. Major | Zeilen 1398–1405 | Soll-Werte-Tabelle: Zeile „Temperatur, Stromausfall-Test“ und Rückfall-Satz**
Rationale: Die Zeile enthält zwei Messpunkte, aber nur einen Soll-Wert, und der gilt nur für den Stromausfall-Test. „Temperatur“ hat keinen Soll-Wert, obwohl die Tabelle als Messpunkt geführt wird. Der Satz „(Abfragezyklus 150 ms, dann Rückfrage an Tobias …)“ nennt die Reihenfolge nicht eindeutig.
Umschreibung: Zwei Zeilen: „Temperatur | Soll-Wert fehlt: Zahl nennen oder als „nur protokollieren“ kennzeichnen“ und „Stromausfall-Test | Dateien nach hartem Ausschalten lesbar“. Rückfall-Satz: „Werden Werte verfehlt, gilt die Rückfallregel aus Baustein 1. Zuerst: Abfragezyklus auf 150 ms setzen. Bleibt ein Wert verfehlt, fragt die Projektleitung Tobias, ob 1,2 s akzeptabel sind.“

**7. Major | Zeile 1408 | „damit ist der Wegfall von V3 endgültig bestätigt“ (CALIBRATE)**
Rationale: Der Pi-Probelauf belegt den Pi-Betrieb ohne V3 zu einem Zeitpunkt. „Endgültig“ übertreibt die Aussage. Die V3-Entscheidung steht in „Abgewogene Alternativen“ (Zeilen 1121–1156), nicht im Probelauf.
Umschreibung: „Bei bestandenem Probelauf bestätigt er den Verzicht auf V3 (Begründung: „Abgewogene Alternativen“).“

**8. Major | Zeilen 1467–1473 | AP 3.6: ein Satz mit neun Punkten in Klammern**
Rationale: Der Satz hat neun Prüf- und Einrichtungspunkte, verschachtelt in Klammern, dazu eine Nebensatz-Anfügung („Dazu die Prüfung …“). Für einen Haiku-Agenten ist das schwer zu verfolgen.
Umschreibung: Liste:
- Datei `docs/betrieb/tailscale-nas.md` mit den Schritten für QNAP-App, HA-Add-on, Box-Schlüssel, ACL, Nur-Lese-Konto.
- Rechte für HA: volles Schreibrecht auf `medien/`, `export/`, `releases/`.
- Schlüsselablauf der Box-Knoten abschalten; Schlüssel sperren.
- Optional: Assistenten-Skript für die Schritte, die nur Tobias machen kann.
- Prüfung: Die ACL sperrt andere Ziele.

**9. Major | Zeile 1513 (AP 3.8) und Zeilen 1552–1553 (AP 4.3) | Unklare Aussagen**
Rationale: AP 3.8: „konservativer Ziel-Pegel“ ist nicht messbar; es fehlt ein Zahlenwert oder ein Verweis auf die Stelle, die ihn festlegt. AP 4.3: „am Lader erst nach Sync und Update“ lässt offen, ob am Lader abgeschaltet wird oder nicht.
Umschreibung AP 3.8: „Ziel-Pegel: <Wert in LUFS oder dB> (Festlegung durch Tobias, siehe D6)“. Umschreibung AP 4.3: „Am Lader wird nicht abgeschaltet, solange Sync oder Update laufen. Ist keines aktiv, gilt die 20-min-Regel.“ Die Projektleitung bestätigt diese Regel mit Tobias, bevor das AP startet.

**10. Nit | mehrere Zeilen | Wortwahl, Verweise, Begriffe**
- Zeile 1395: „Benutzter Arbeitsspeicher“ → „Belegter Arbeitsspeicher“.
- Zeile 1341: „Reißt sie die Grenze“ → „Überschreitet sie die Grenze“.
- Zeile 1489: „Weist nach, dass …“ hat kein Subjekt → „Ergebnis: Das Paket enthält die fertig gebauten Abhängigkeiten; auf dem Pi wird nichts gebaut.“
- Zeile 1418: „die Voraussetzungen bereit sind“ → „die Voraussetzungen sind erfüllt“.
- Zeile 1476: „Mac-Box“ → „Box am Mac“.
- Zeile 1504: „Wiederherstellung von Null“ → „Wiederherstellung aus dem Nichts“ oder „Neuinstallation“.
- Zeilen 1282–1283: doppelte Leerzeile.
- Zeile 1240: „siehe „Update““ ohne Ort → „siehe Abschnitt „Update“ (Zeile 1034)“.
- Zeilen 1509, 1535, 1569: „Plan 7.2“, „Plan 5.5.2“, „Plan 5.7“ sind Verweise auf einen Plan, der nicht benannt ist. Der Name des Dokuments muss beim ersten Verweis stehen (z. B. „Projektplan, Abschnitt 5.5.2“).
- Begriffe (Zeilen 30–111): CUJ, Baustein und Teilautomat stehen nicht in „Begriffe“, werden aber im Abschnitt verwendet. Sie sind im Dokument an anderer Stelle erklärt (CUJ Zeile 306, Baustein Zeile 524). Nach der Projektregel gehören sie in „Begriffe“.
- Zeilen 234–235 vs. 1234–1235: „Haiku = günstiger, Sonnet = stärker“ wiederholt die Begriffe-Erklärung. Die Doppelung streichen oder kürzen.
- Abnahme Stufe 2 (Zeile 1370–1374) wiederholt die Regel „Folge zu Ende bei liegender Figur“ aus AP 2.1 (Zeile 1349–1350) wörtlich. Eine Fassung genügt; die andere verweist darauf.
