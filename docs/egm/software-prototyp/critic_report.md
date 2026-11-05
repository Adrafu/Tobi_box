# Goldfisch-Review Stufe 7 — Kritik (Architektur, Struktur, Stil)

**Ziel:** `design_draft.md`, fachlicher Teil (bis „Detailed Implementation“) ·
**Maßstab:** EGM feature-spec-standard · **Prüfer:** drei frische Agents
(Architektur/Risiko: Sonnet, Struktur: Sonnet, Stil: Haiku) · **Datum:** 2026-11-05

## Zusammengeführte Befunde

| # | Schwere | Thema | Quelle | Kurzfassung |
|---|---|---|---|---|
| K1 | Blocker | Lautstärke-Grenze | Architektur 1, Struktur 2 | Grenze nur im Python-Dienst; MPD-Startlautstärke, Dienstabsturz, ReplayGain-Anhebung, Kopfhörerwechsel offen; mehrere Grenzen ohne Besitzer. |
| K2 | Blocker | Update-Rückfall | Architektur 2, Struktur 8 | Zähler zählt normale Neustarts; Verweis-Umschaltung nicht atomar beschrieben; neue Schemas nach Rückfall unlesbar; Abhängigkeiten auf dem Pi offen; pytest auf der Box widerspricht „schlank“. |
| K3 | Major | Kern-Zustandsautomat | Struktur 1, 12 | Zustände, Übergänge, Vorrang (stumm / Gute Nacht / Lernmodus / Leerlauf / Abheben beim Ausblenden) nicht festgelegt; Gefahr eines Gott-Moduls; Zusammenbau-Punkt fehlt. |
| K4 | Major | Uhrzeit | Architektur 4, Struktur 3 | Leise-Zeiten brauchen richtige Zeit; nach leerem Akku ohne Netz falsch; PiSugar-RTC nicht eingeplant; Dauern sollen monotone Uhr nutzen. |
| K5 | Major | Revisionsregel | Architektur 3, Struktur 4 | „Nur höher“ blockiert nach HA-Wiederherstellung dauerhaft; kein Rückweg Box → HA; Export ohne Ort und Takt. |
| K6 | Major | Lernmodus verteilt | Struktur 6 | Wer misst 2 min, welche Box lernt, Befehle retained?, `unknown.json` ohne Bestätigung. |
| K7 | Major | Leser-Neustart | Struktur 7 | `seq` beginnt bei 0; Abheben während Unterbrechung; Karenz für Pause bei Wächter-Alarm fehlt. |
| K8 | Major | Resume-Zeiger und Dateiänderungen | Struktur 5 | Zeiger auf gelöschte/umbenannte Folge; „jüngere Kopie“ undefiniert; zwei Schreiber auf der Freigabe. |
| K9 | Major | Sicherheit | Architektur 7, 8; Struktur 9 | MQTT ohne Konten/Themenrechte (Update-Befehl!); Update-Paket ohne Echtheitsprüfung; HA hat Schreibrecht auf `releases/`. |
| K10 | Major | Abschalten vs. Sync/Update | Architektur 9 | Nach 20 min Leerlauf aus → kein Sync, kein Update; Regel fehlt. |
| K11 | Major | Pi-Budgets | Architektur 10, 11 | RAM-, Boot- und Zeitbudget unbelegt; Entsperrzeit fehlt in der Rechnung; „Figur liegt beim Start“ fehlt; was, wenn Messung die Grenze reißt? |
| K12 | Major | SD-Karte | Architektur 5 | Schreibbudget, Log-Obergrenze, Resume nur bei Änderung; Kriterium für Read-only-Overlay. |
| K13 | Major | Medien-Sync | Architektur 6 | `--delete` ungeklärt (leere Quelle leert Box), Platzprüfung, Test „Auflegen während Sync“. |
| K14 | Major | Dokumentstruktur | Struktur 10, 11 | Regeln mehrfach an verschiedenen Stellen; HA-Abschnitte überlappen; Überschriften gemischt; „Offene Architektur-Entscheidungen“ sind entschieden. |
| K15 | Major | Risiko-Tabelle | Struktur 9 | Spalten Auswirkung und Gegenmaßnahme fehlen; Sicherheits- und Skalierungsrisiken fehlen. |
| K16 | Major | Stil | Stil 1–11 | Absolute Aussagen kalibrieren („kein Zustand geht verloren“, „sicher“, „nichts erreichbar“), fehlende Begriffe (Lernmodus, Obergrenze, Status-Karte, Gute-Nacht-Karte, Leise-Zeiten, Netz-Klasse, SSID, Hotspot, ReplayGain, rsync, Lit), Problem-Satz messbar machen, Non-Goals-Einstieg. |
| K17 | Nit | Kleinkram | Architektur 12, Stil 12 | Firmware-Datei nicht veröffentlichen (Passwort auslesbar); neutraler Hinweis zum Entsperren geborgter Figuren; Tailscale-Schlüsselablauf; Alternativen „SD von Hand füllen“, Syncthing; ESPHome-Grund präzisieren; Wortwahl. |

Rohtexte der drei Prüfer: siehe unten.

## Vorschlag der Projektleitung

| # | Lösung |
|---|---|
| K1 | Eine Regel im Kern: **wirksame Grenze = Minimum aller aktiven Grenzen** (global, Leise-Fenster, Kopfhörer, Gute-Nacht-Ausblenden); nie darüber. Zweite Sicherung außerhalb des Dienstes: MPD startet mit fester Startlautstärke, Ausgabe hat eine harte Obergrenze in der MPD/ALSA-Konfiguration; ReplayGain mit `replaygain_limit` (keine Anhebung über Clipping). Der Dienst setzt beim Start zuerst die Lautstärke. Kopfhörerwechsel: erst Grenze setzen, dann Ausgang schalten. Test: ReplayGain + Grenze überschreitet nie den Grenzwert. Messung am Verstärker in Stufe 4. |
| K2 | Zähler nur im Zustand `testing`; Umschalten des Verweises atomar (neuer Verweis, dann umbenennen); vor dem Update Sicherung der Zustandsdateien, beim Rückfall zurückspielen; Schemas nur abwärtskompatibel erweitern. Abhängigkeiten kommen **fertig gebaut im Paket** (kein Bauen auf dem Pi). **Selbsttest ohne pytest**: eingebaute Prüfroutine (Dienst, `HELLO`, Dateien, MPD, Testton, plus ein fest eingebauter Kurzablauf „Auflegen → Play → Abheben → Pause“ gegen den Kern). Rückfall-Logik als kleine Python-Funktion mit Test. |
| K3 | Neuer Abschnitt **„Kern-Zustände“**: vier Teilautomaten (Wiedergabe-Sitzung, Lernmodus, Ruhe-Regeln = Leise/Gute Nacht, Strom/Leerlauf), Tabelle Zustand × Ereignis → Befehl, **Vorrang**: Herunterfahren/Update > stumm > Gute-Nacht-Ende > Lernmodus > Wiedergabe. Uhr wird eingespeist. `app.py` ist der einzige Zusammenbau-Punkt; Abhängigkeiten zeigen nur zum Kern. |
| K4 | Zeitquelle: PiSugar-RTC beim Start, NTP bei Netz. Zeit nicht vertrauenswürdig → strengste Leise-Wirkung des Tages bis die Zeit stimmt, Hinweis an HA. Alle Dauern mit monotoner Uhr. |
| K5 | Revision **plus Listen-ID** (zufällig je HA-Speicher). Neue Listen-ID → Box übernimmt unabhängig von der Revision. HA-Aktion „an alle Boxen erzwingen“. Box meldet abgelehnte Listen. Export automatisch nach jeder Änderung auf das NAS; Import aus einer Box-Kopie als HA-Aktion. |
| K6 | Lernmodus gehört der Box (Frist auf der Box); Befehl an genau eine Box, nicht dauerhaft, mit Ablaufzeit. Unbekannte Kennungen erst nach Bestätigung durch HA löschen; HA führt beide Boxen zusammen (gleiche Kennung = ein Eintrag). |
| K7 | `HELLO` setzt `seq` zurück und versetzt den Kern in „Leser-Zustand unbekannt“; Wächter-Alarm → Pause nach 1,5 s; kommt danach dieselbe Kennung, läuft es an derselben Stelle weiter (Resume), sonst normales Auflegen. |
| K8 | Zeiger auf fehlende Folge → nächste vorhandene Folge in der Reihenfolge, Position 0, protokolliert; leere Serie → Fehlerton. `serie.json` bekommt `angelegt_am`; „jünger“ = späteres `angelegt_am`. Parallel-Schreiben als Risiko. |
| K9 | MQTT-Konto je Box mit Themenrechten (Box liest `mappings`, schreibt nur eigene Themen); Update-Paket **signiert** (Schlüssel bei Tobias, Prüfschlüssel auf der Box); `releases/` für HA nur lesbar. |
| K10 | **Vorschlag:** Am Lader schaltet die Box erst ab, wenn Sync und Update fertig sind; während Sync, Update und Lernmodus nie. Beim Start am Lader prüft sie den Sync. Später (Stufe 4) nächtliches Wecken über den PiSugar-Wecker am Lader. |
| K11 | Soll-Werte für den Pi-Probelauf: Speicher, Start bis „bereit“, Auflegen unter Last (Sync läuft). Entsperrzeit in die Rechnung. Neuer Ablauf „Figur liegt schon beim Start“ (spielt, sobald bereit). Reißt die Messung 1,0 s: erst Abfragezyklus auf 150 ms, dann Rückfrage an Tobias. |
| K12 | Schreibbudget angeben; Resume nur bei Änderung, höchstens alle 30 s; Logs mit fester Obergrenze; Read-only-Overlay, sobald der erste SD-Fehler auftritt. |
| K13 | `--delete` ja, mit Schutz: Abbruch, wenn die Quelle fehlt, leer ist oder mehr als 20 % löschen würde; Platzprüfung vorab; Test „Auflegen während Sync“ in Stufe 3. |
| K14 | Je Regel ein Stammplatz, sonst nur Verweise; „Home Assistant“ in Baustein 4 zusammenführen; Überschriften einheitlich deutsch; entschiedene D1–D4 in „Entscheidungen“. |
| K15 | Risiko-Tabelle um Auswirkung und Gegenmaßnahme erweitern, Sicherheits- und Skalierungsrisiken aufnehmen. |
| K16 | Alle Stil-Vorschläge übernehmen. |
| K17 | Übernehmen. |

---

## Rohtext Architektur & Risiko (Sonnet)

Review Feature-Teil (Zeile 1 bis 832) von design_draft.md, Linse Architektur und Risiko, hostile. Die Punkte aus zoom_out_report.md und comprehension_report.md habe ich nicht wiederholt. Ich habe nichts geschrieben oder geändert.

Gesamturteil: Die Logik rund um Leser, Entprellen und Resume ist solide. Der teure Teil ist unterschätzt: ein MQTT-Broker auf dem HA-Gerät, Tailscale, rsync, eigene HA-Integration mit Web-Seite, Lautheits-Container und Update-Mechanik. Das sind sechs bis sieben bewegliche Teile für zwei Kinderboxen. Der Normalbetrieb "ohne Netz" ist gut abgesichert. Die Randfälle (Akku leer, Dauer-Leerlauf, Broker-Ausfall) sind es nicht.

**1. Blocker. Kinderohren (Ziel 10): Die Obergrenze hängt an einer einzigen Software-Schicht, und der Fehlerfall ist offen.**
Betrifft: Ziel 10, Baustein "player", D6, CUJ 15, CUJ 17.
- Die Lautstärke-Obergrenze sitzt nur im Python-Dienst (`player`). Nichts sagt, was bei einem Dienstabsturz oder Neustart passiert.
- MPD behält seine letzte Lautstärke selbst. Beim Start steht sie auf dem alten Wert oder auf MPD-Default (oft 100 %). "Startlautstärke" ist in Ziel 10 genannt, im Technical Plan aber nirgends umgesetzt.
- ReplayGain (D6) kann Lautheit anheben. Bei Dateien mit positivem Gain und Preamp kann ein Titel lauter werden als das Limit. Die Obergrenze liegt vermutlich auf der MPD-Mixer-Lautstärke. Das ist nicht geklärt und steht nicht im Dokument.
- Beim Kopfhörer-Wechsel (CUJ 17) gibt es ein Zeitfenster, in dem Lautsprecher-Limit und Kopfhörer-Limit nicht zusammenpassen.
- Der Stufe-1-Stand hat noch keinen Verstärker. Das Limit ist also nur softwareseitig prüfbar.
- Empfehlung:
  - Hartes Limit auch außerhalb des Dienstes festlegen: MPD-Startwert per `mpd.conf`/ALSA-Softvol/`max_volume`, oder ein ALSA-Limit.
  - Der Dienst setzt beim Start zuerst die Lautstärke, bevor irgendetwas spielt.
  - Ein pytest-Test: "ReplayGain plus Limit überschreitet nie X dB am Ausgang".
  - Eine Hardware-Abnahme mit Messung am Verstärker (Stufe 4).

**2. Blocker. Update-Rückfall: Das Fehlerbild "Dienst startet, ist aber kaputt" und der SD-Schreibpfad sind nicht abgedeckt.**
Betrifft: Abschnitt "Update", Ziel 7, CUJ 10.
- Der Rückfall greift bei Zähler ≥ 3, `OnFailure` oder `testing` älter als 5 min. Dazu fehlt die Unterscheidung zwischen Dienst und Gerät.
- Ein Neustart-Zähler per `ExecStartPre` zählt auch normale Neustarts, etwa wenn Leerlauf-Abschaltung, Akku-leer und Strom-Aus dreimal hintereinander kommen. Das kann ein fälschlicher Rückfall im Zustand `testing` werden.
- Nicht beschrieben:
  - Wie der Selbsttest "Testton spielt" und "Leser meldet HELLO" prüft, wenn kein Leser dran ist oder die Box im Gehäuse steckt.
  - Was passiert, wenn der Strom während `current`-Umstellen ausfällt. Ist der Verweis atomar (`ln -sfn` plus `mv`)? Das Dokument sagt es nur für JSON-Dateien.
  - Was passiert, wenn ein Update die Schema-Version der Zustandsdateien ändert und dann zurückgerollt wird. Die alte Version liest das neue Schema nicht, die Sicherung wird nicht erwähnt.
- Auch offen: pip auf dem Pi 3A+ mit 512 MB RAM und SD-Karte (Kompilierung von Abhängigkeiten, "AP 3.5 entscheidet"). Eine Schlüsselentscheidung wird so in ein AP verschoben.
- Empfehlung: Vor Stufe 3 festlegen, dass Abhängigkeiten als fertige Wheels im Paket liegen. Den Zähler nur beim `testing`-Zustand zählen lassen. Das Rollback-Schema (Rückwärtskompatibilität der Zustandsdateien oder gesicherte Kopie je Update) im Dokument benennen.

**3. Major. Ein Ausfall von HA, MQTT-Broker oder Tailscale kippt die Fernwartung. Es gibt keine Wiederherstellung für Zuordnungen und Folgenreihenfolge.**
Betrifft: Entscheidungen D1/D2/D3, Baustein 4, Datenmodell.
- Single Point of Failure: HA ist einziger Schreiber, einziger Speicher der Zuordnungen und Quelle für Serie-IDs. Fällt der HA-Speicher aus oder wird ein Backup unbrauchbar, gibt es kein Rückholen aus den Boxen. `mappings.json` liegt zwar auf der Box, aber das Dokument sagt nicht, dass man daraus HA wiederherstellen kann ("Export als Datei" wird nur genannt, ohne Takt oder Ort).
- Die Revisionsregel "nur höher" ist eine Falle. Nach einer HA-Neuinstallation oder einem Restore aus einem alten Backup startet die Revision wieder niedrig. Beide Boxen ignorieren dann dauerhaft die richtige Liste. Gleiches gilt bei zwei HA-Instanzen (Test und Produktion).
- Empfehlung:
  - Revision zusätzlich mit einer Listen-ID (UUID) und einem Zeitstempel kennzeichnen. Oder explizit definieren, wie man einen "Revisions-Reset" in HA auslöst.
  - Export automatisch ablegen (z. B. beim Speichern auf das NAS).
  - Einen Weg schreiben, `mappings.json` einer Box nach HA zu importieren.

**4. Major. Kein Plan für Zeit und Uhr auf dem Pi.**
Betrifft: Datenmodell, Ereignisprotokoll, Leise-Zeiten (CUJ 15), Papierkorb (30 Tage), Update (5 min), Zeitquelle im Log.
- Der Pi 3A+ hat keine Echtzeituhr. Der PiSugar 3 Plus hat eine RTC, aber das Dokument sagt nicht, dass `power` sie nutzt, und nicht, wer sie beim Boot ins System schreibt. Die Stückliste nennt "RTC als Zeitquelle" (Zeile 7).
- Ohne gültige Zeit ist CUJ 15 (Leise-Zeiten) falsch: Nach einem leeren Akku und einem Start ohne Netz kann die Box um 03:00 oder 12:00 irrtümlich "stumm" sein oder eben nicht stumm. Das ist ein kindersicherheitsrelevanter Fall (Nachts laut) und ein Zuverlässigkeitsfall (tagsüber stumm).
- Auch NTP-Sprünge nach dem Hotspot-Verbinden verwirren Timer (Gute-Nacht, Leerlauf 20 min, Resume alle 30 s) und Logsortierung.
- Empfehlung: Ein Verhalten bei "Zeit nicht vertrauenswürdig" festlegen (z. B. Leise-Zeiten fallen auf die vorsichtigere Obergrenze zurück). Monotone Uhr für alle Dauern verwenden. Das Ganze in `power` oder `net` als eigener Prüfpunkt führen.

**5. Major. SD-Verschleiß und Stromausfall: Das Versprechen "kein Zustand geht kaputt" ist zu stark.**
Betrifft: Ziel 5, Datenmodell, Risiko-Tabelle, Stückliste Punkt 22 (Read-only-Root zurückgestellt).
- Resume wird alle 30 s mit fsync geschrieben. Bei 2 h Wiedergabe pro Tag sind das rund 240 Schreibvorgänge mit fsync pro Tag und Box, plus Logrotation, plus journald dauerhaft. Das ist nicht dramatisch, aber ohne Zahl nicht belegt.
- `atomar + fsync + .bak` schützt die Datei, nicht das Dateisystem. Auf einer billigen SD-Karte bei Stromverlust kann ext4 trotzdem beschädigt werden. Der Plan hat den Read-only-Root zurückgestellt, im Dokument steht aber nur "Stromausfall-Test" als Prüfung.
- Das Ereignisprotokoll "übersteht Stromausfall", aber rotierende JSON-Logs und dauerhaftes journald auf derselben SD erhöhen die Schreiblast. Es gibt keine Größengrenze (Dateianzahl/Größe) im Dokument.
- Empfehlung: Schreibbudget angeben (Schreibvorgänge pro Tag und Obergrenze Log-Volumen). Resume im Takt auf Änderung der Position schreiben, nicht blind alle 30 s. Eine Partition oder ein Verzeichnis für Zustandsdaten mit `commit=`/`noatime`. Kriterium festlegen, wann der Read-only-Overlay doch kommt (z. B. erster SD-Fehler).

**6. Major. rsync-Sync und Akku/CPU auf dem Pi 3A+ sind unbelegt.**
Betrifft: Abschnitt "Netz, Sync, Strom", CUJ 9, D5, D6.
- Im Hotspot gilt "erlaubt, wenn Lader dran oder Akku > 50 %". Es gibt keine Abschätzung des Datenvolumens. FLAC ist laut D5 etwa 5× größer als mp3. Ein Hörspiel kann hunderte MB sein; über den Handy-Hotspot geht das auf das Datenvolumen von Tobias' Mobilfunkvertrag. Das steht nirgends.
- Der Pi 3A+ hat nur 2,4/5-GHz-WLAN auf einem Chip mit gemeinsam genutztem USB-Bus. rsync über Tailscale (WireGuard in Userspace oder Kernel?) belastet die CPU. `nice`/`ionice` wird erwähnt; ob dadurch das Abspielen (Ziel 2, 1,0 s) hält, ist nicht belegt.
- Stufe 0 bis 1 misst Auflegen und Abheben, aber ein Test "Auflegen während Sync läuft" fehlt. Er gehört in die Abnahme.
- Es gibt keine Obergrenze für den Speicher auf der SD: Was passiert bei voller Karte? Der Sync müsste vorab prüfen und ablehnen. Das Dokument sagt nur, HA zeige den belegten Platz.
- Der Sync ist spiegelnd (`rsync`), aber es ist offen, ob Löschungen auf dem NAS auch auf der Box löschen (`--delete`). Wenn ja: Gefahr, dass eine kaputte oder leere NAS-Freigabe (NAS-Neustart, Mount fehlt) die Box leert. Wenn nein: Die Box läuft irgendwann voll.
- Empfehlung: `--delete` ausdrücklich entscheiden und mit Schutzregel versehen (nicht löschen, wenn die Quelle leer oder zu klein ist). Datenvolumen-Schätzung und Speicherprüfung vor dem Sync. Messfall "Sync läuft parallel zum Auflegen" in Stufe 3.

**7. Major. MQTT-Broker in HA, mit Revisions-Nachricht als "dauerhaft" (retained): Verlust und Reihenfolge nicht beschrieben.**
Betrifft: Abschnitt Home Assistant, Baustein 4 (`tobibox/mappings`).
- Eine retained Nachricht wird beim HA-Neustart oder bei einem Broker-Update nur erhalten, wenn der Broker persistiert. Das ist beim HA-Add-on (Mosquitto) Standard, aber nicht zugesichert. Ein Broker-Wechsel oder -Reset löscht sie.
- Bei zwei Boxen mit möglicherweise unterschiedlicher Verbindungszeit gilt: Eine Box verpasst Zwischenstände, aber da immer die ganze Liste kommt, ist das unkritisch. Das ist gut, aber nicht erwähnt.
- Offen: Größe der Nachricht (ganze Liste mit allen Kennungen), Maximalgröße des Brokers, und was passiert, wenn die Liste groß wird.
- Offen: Authentifizierung/ACL des Brokers. Wer darf auf `tobibox/mappings` veröffentlichen? Wer das kann, kann bei beiden Boxen eine fremde Figur auf beliebige Audio-Aktionen legen oder `cmd` (Update!) auslösen. Update über `tobibox/<box>/cmd` ist ein Fernsteuerungsweg. Das Dokument sagt zu Broker-Konten und Topic-ACL nichts, obwohl Tailscale-ACL erwähnt wird.
- Empfehlung: Broker-Benutzer je Box mit Topic-Rechten (Box darf nur `tobibox/<box>/…` schreiben, `mappings` nur lesen). Das Update-Kommando muss zusätzlich die Bedingungen prüfen (ist so beschrieben) und das Paket auf Integrität prüfen (siehe Punkt 8).

**8. Major. Update-Paket ohne Echtheitsprüfung (Lieferkette).**
Betrifft: Abschnitt "Update", Ziel 7.
- Das Paket liegt auf dem NAS (`tobibox/releases/`) und wird von der Box geladen und ausgeführt (Code!). Dem Dokument fehlt eine Prüfsumme oder Signatur im Manifest und der Hinweis, wer auf `releases/` schreiben darf. HA hat Schreibrecht auf die Medienfreigabe. Die Freigabe wird in HA eingebunden. Ein kompromittiertes HA oder Add-on kann damit Code auf beide Boxen bringen.
- Zugleich nehmen die Boxen Medien-Dateien vom NAS an. Eine manipulierte Audiodatei trifft auf den MPD-Parser (FLAC/Opus/Ogg). Das ist kein unrealistisches Risiko, aber auf Hobby-Niveau klein.
- Empfehlung: Mindestens SHA-256 im `manifest.json`, und die Prüfsumme kommt über einen anderen Weg (MQTT-Befehl aus HA, nicht vom NAS). Besser: signiertes Manifest mit einem öffentlichen Schlüssel auf der Box. `releases/` nur für Tobias (nicht für HA) beschreibbar.

**9. Major. Leerlauf-Abschaltung, Gute-Nacht und Hardware-Aus verhindern die Fernwartung und den Sync ("Tobias legt Update an, Box ist aus").**
Betrifft: CUJ 16, CUJ 9, CUJ 10, CUJ 12.
- Nach 20 min Leerlauf fährt die Box herunter. Dann gibt es nie ein Hintergrund-Sync, kein Resume-Melden und keinen Update-Weg, es sei denn, Tobias schaltet sie ein und wartet. Das Dokument legt nicht fest, wann der Sync läuft: "zeitgesteuert" in CUJ 9 setzt eine laufende Box voraus. Ohne Weckfunktion (PiSugar-RTC-Alarm) wird das nie passieren.
- Das ist ein Widerspruch zwischen CUJ 9/10 ("Box daheim, am Lader") und CUJ 16. Ein Sync-Fenster nach dem Hochfahren (z. B. Sync beim Start, solange keine Figur liegt) oder eine "nicht abschalten, wenn Sync/Update läuft"-Regel fehlt im Text.
- Empfehlung: Eine Regel für "Abschalten verboten während Sync/Update/Lernmodus". Beim Start am Lader automatisch Sync prüfen. Entscheiden, ob der RTC-Alarm für Aufwachen genutzt wird.

**10. Major. Pi 3A+ mit 512 MB RAM und alle Dienste: kein Speicher- und Startzeit-Budget.**
Betrifft: Baustein 3, Mac-und-Pi-Tabelle, Ziel 2 und 4.
- Auf dem Pi laufen gleichzeitig MPD, Python/asyncio mit `paho-mqtt`, `python-mpd2`, `pyserial`, Tailscale, NetworkManager, pisugar-server, rsync (bei Sync) und ggf. pytest-Selbsttest. Kein RAM-Budget, keine Messung geplant. Das "Zeitbudget" (300 ms Dienst und MPD-Start) gilt nur für warme Pfade.
- Kaltstart nach leerem Akku: Bootzeit des Pi 3A+ bis "Box bereit" fehlt. Das ist für ein Kleinkind relevant (Figur liegt, nichts passiert 40 s). CUJ 3 verspricht Resume "auch nach leerem Akku", nennt aber keine Zeit und kein Verhalten für "Figur liegt schon beim Hochfahren".
- Die MPD-Bibliothek wird nach jedem Sync neu eingelesen. Bei vielen Dateien belastet das SD und CPU. Das Dokument nennt keine Größenordnung der Sammlung (Anzahl Titel).
- Der Selbsttest führt "Unit-Tests des Kerns" aus. Das setzt pytest (und Abhängigkeiten) auf dem Pi voraus und kostet RAM beim Update. Das widerspricht dem schlanken Ziel.
- Empfehlung: RAM- und Boot-Budget als Messpunkt in den Pi-Probelauf aufnehmen (Soll-Werte festlegen). Das Verhalten "Figur liegt beim Start" als CUJ oder Zusatz zu CUJ 3 beschreiben. Selbsttest ohne pytest, mit einer kleinen eingebauten Prüfroutine.

**11. Major. Die Zeitbudget-Rechnung ist knapp und geht von Idealwerten aus.**
Betrifft: Baustein 1 "Zeitbudget", Ziel 2.
- Auflegen: 200 + 2 × 200 + 10 + 300 ms gleich 910 ms bei Grenze 1000 ms. Das ist im Worst Case ein Puffer von etwa 90 ms. Jede Verlängerung des Zyklus (Ziel 150 ms, aber "≤ 200 ms") oder das Entsperren eines Tonie (mehrere Befehle auf dem PN5180) kippt die Grenze. Die Entsperrzeit wird gar nicht eingerechnet.
- Der 300-ms-Wert für "Dienst und MPD-Start" ist unbelegt. Bei gleichzeitiger Last (Sync, Pi 3A+ SD) kann `play` länger dauern. Zusätzlich die MPD-Pufferung beim ersten Dekodieren großer FLAC-Dateien.
- Das Dokument schafft Abhilfe durch "Stufe 1 misst das nach", legt aber nicht fest, was passiert, wenn die Messung die Grenze reißt: Ziel lockern oder Zyklus ändern? Die Blockerfolge ist unklar.
- Empfehlung: Entsperrzeit einrechnen und ein Fallback festlegen (z. B. Ziel 1,0 s auf 1,5 s lockern, oder 1 Lesung statt 2 für bekannte Kennungen). Messung unter Last (Sync, Log-Rotation) als Abnahmekriterium.

**12. Nit. Fehlende Betriebsangaben und kleine Unstimmigkeiten.**
Betrifft: verschiedene Abschnitte.
- Das Tonie-Passwort ist in der Firmware-`config.h`. Wer das ESP32 per USB am Pi hat, kann es mit `esptool` auslesen (kein Flash-Verschlüsseln erwähnt). Für ein Hobby-Projekt hinnehmbar, aber ein Satz dazu (Firmware-Binary nicht veröffentlichen) fehlt.
- Das Passwort ist gleichzeitig in Ziel und Risiko nur als "Entsperrung klappt nicht" geführt; die rechtliche/ethische Seite (Umgehen des Privacy-Modus fremder Tonies, "geborgte Figuren") wird nicht erwähnt. Kein Blocker, aber Tobias sollte wissen, dass das Dokument es nicht behandelt.
- Die Revisions-Begriffe "Revision" und "Plan-Revision" sind sauber getrennt. Aber `seq` (Protokoll) und Revision haben beide Zählerfunktion; bei ESP32-Neustart beginnt `seq` bei null. Es steht nicht da, dass der Box-Dienst `seq`-Lücken nach `HELLO` zurücksetzen muss.
- Die Alternativen-Liste hat zwei "Abgelehnt von der Projektleitung/vom Autor" ohne Verweis auf Gründe in einer Quelle (ESPHome, Lautheit). Der Standard verlangt konkrete technische Gründe; hier sind es meist Kurzsätze. Für ESPHome fehlt der Beleg ("vermutlich").
- Alternative "Nur lokale Medien auf der Box ohne Sync (SD manuell füllen)" und "Syncthing statt rsync" fehlen. Für ein Einmannprojekt mit zwei Boxen ist die Handarbeit-Variante die Konkurrenz, die den Aufwand von Stufe 3 (Tailscale, Sync, Seite, Container) am schärfsten infrage stellt. Sie sollte mit einer Begründung widerlegt werden.
- Tailscale-Schlüsselablauf: Ein abgelaufener Node-Key (Standard 180 Tage) lässt die Boxen unbemerkt vom Netz fallen. Gegenmittel (Key-Expiry aus, ACL-Tag) steht nicht im Dokument.

Reihenfolge zur Bearbeitung: 1 und 2 vor Stufe 1 bzw. Stufe 3 klären. 3, 4, 7, 8, 9 lassen sich im Design mit wenigen Sätzen schließen. 5, 6, 10, 11 gehören als Messpunkte in den Pi-Probelauf mit festen Soll-Werten.

## Rohtext Struktur (Sonnet)

Structural-Goldfish-Review (Stufe 7, Lens: Struktur, Kopplung, Zustandsautomaten, Wartbarkeit)
Geprüft: design_draft.md, Zeilen 1–832 (bis vor „## Detailed Implementation“). Standard: feature-spec-standard.md. Ich habe nur dieses Feature-Teil gelesen. Der Detailteil (ab Z. 833) nennt `core.py` nur als „Zustandsautomat“ (Z. 888), eine Zustandstabelle habe ich per Stichwortsuche dort nicht gefunden.

1. **Major — Baustein 3, `core` (Z. 506, 519–528) und CUJ 1–19: Der zentrale Zustandsautomat ist nicht spezifiziert.**
   Der Kern soll alle CUJs abbilden: Auflegen, Wechsel, gesperrt, Lernmodus, Gute Nacht, Leise-Zeiten, Leerlauf, Kopfhörer, Tasten, Update-Bedingung, Akku. Das Dokument nennt aber weder Zustände noch Übergänge noch Vorrangregeln. Beispiele für ungeklärte Kombinationen:
   - Leise-Zeit „stumm“ trifft auf Lernmodus: Wird gelernt, aber nicht gespielt?
   - Gute-Nacht-Timer läuft, und es wird eine andere Figur aufgelegt.
   - Leerlauf-Abschaltung trifft auf Lernmodus oder Sync.
   - Die Figur wird während des Ausblendens abgehoben.
   - Stumm-Fenster beginnt, während eine Figur liegt.
   Ohne Zustandstabelle entscheidet jeder Agent diese Fälle anders. Das Ergebnis ist ein wachsender `if`-Haufen, den die pytest-Tabellen nicht abdecken.
   Empfehlung: Vor der Umsetzung ein Abschnitt „Kern-Zustände“ mit Zustandsdiagramm oder Tabelle (Zustand × Ereignis → Befehl, neuer Zustand). Dazu eine feste Prioritätsliste der Übersteuerungen (Stumm > Gute Nacht > Figur …). Den Kern in 3–4 kleine, einzeln testbare Teilautomaten zerlegen: Wiedergabe-Sitzung, Lernmodus, Zeit-/Ruhe-Richtlinie, Strom-/Leerlauf-Richtlinie. Ein zusammengesteckter Kern ohne diese Aufteilung wird zum Gott-Modul.

2. **Major — Baustein 3 Modultabelle, `player`/Lautstärke, Ziel 10, CUJ 14/15/17/19: Lautstärke-Obergrenze hat mehrere Quellen und keinen Besitzer.**
   Wirksam sind mindestens: globale Obergrenze, Startlautstärke, Leise-Fenster mit eigener Grenze, Kopfhörer-Limit, Drehregler, Gute-Nacht-Ausblenden, ReplayGain (D6). Das Dokument sagt nur, `player` setze „Lautstärke mit Obergrenze“. Es sagt nicht, wer die effektive Grenze berechnet (Minimum aller aktiven Grenzen?). Auch offen: ob ein Ausblenden/Absenken eine Grenze verletzen darf und was beim Wechsel Kopfhörer ↔ Lautsprecher passiert (CUJ 17 sagt „Lautsprecher schaltet ab“). Das ist ein Kinderschutz-Ziel, deshalb wiegt die Lücke schwer.
   Empfehlung: Eine reine Funktion `effective_volume_limit(context)` im Kern, die alle Quellen zusammenführt. Der Player setzt sie nur durch und klemmt als letzte Sicherung. Die Regel „Minimum gewinnt, nie darüber“ ins Dokument schreiben.

3. **Major — CUJ 15, CUJ 14, Fehlersuche Z. 688–690, Mac/Pi-Tabelle: Uhrzeit-Abhängigkeit ohne Fallback.**
   Leise-Zeiten brauchen eine korrekte Wanduhr. Der Pi 3A+ hat laut Plan keine RTC (das Dokument nennt „RTC“ nur als mögliche Zeitquelle im Log). Nach leerem Akku oder Stromausfall und ohne Netz zeigt die Uhr eine falsche Zeit. Dann können Stumm-Fenster in der Nacht wirkungslos sein (fail-open), oder Tagesbetrieb wird fälschlich stumm. Die „Zeitquelle“ im Log zeigt das nur an, schützt aber nicht. Außerdem fehlt im Kern-Vertrag eine injizierte Uhr: „Zeitgeber“ ist als Ereignisquelle genannt, die Uhr als Eingang aber nicht.
   Empfehlung: Regel festlegen, z. B. „Zeitquelle nicht synchronisiert → strengste Leise-Wirkung oder letzte bekannte Obergrenze, plus Hinweis an HA“. Den Kern nur mit injizierter Uhr bauen (Zeit kommt als Parameter, wie schon bei `debounce`).

4. **Major — Home Assistant, Revisionsregel (Z. 577–581), `mappings.json` (Z. 537): „nur höher übernehmen“ ist nicht rücksetzbar.**
   Wird die HA-Integration neu installiert oder aus einer Sicherung wiederhergestellt, oder ein `.storage`-Eintrag geht verloren, startet die Revisionszählung niedriger. Beide Boxen ignorieren dann die korrekte Liste dauerhaft. Die Box verwirft solche Nachrichten still. Im Dokument ist kein Weg vorgesehen, das zu erkennen oder zu beheben (Szenarien „HA-Restore“ und „Revision ging verloren“ fehlen auch in den Risiken).
   Empfehlung: Eine Epoche/Generation (z. B. zufällige Speicher-ID) zusätzlich zur Revision, oder eine HA-Aktion „Liste erzwingen“ (Box übernimmt unabhängig von der Revision). Die Box meldet „abgelehnte Revision“ als Sensor/Ereignis an HA.

5. **Major — Datenmodell (Z. 535–565), Baustein 4 (Z. 597–609), D2: Resume-Zeiger und `serie.json` koppeln sich über Dateinamen ohne Regeln für Änderungen.**
   `resume.json` verweist auf Folgen per Dateiname. Nicht festgelegt ist, was geschieht, wenn:
   - die Datei umbenannt oder gelöscht wird (die Seite löscht Folgen),
   - sie aus der Liste verschwindet,
   - die Reihenfolge geändert wird, während der Zeiger auf „nächste ungehörte“ steht,
   - die Serie geleert wird, die Serien-ID neu vergeben wird (Duplikat-Regel, „jüngere Kopie“), oder
   - die Serie in der Box-Kopie noch nicht angekommen ist.
   „Jüngere Kopie“ ist nicht definiert (mtime? Erkennungszeitpunkt?) und auf SMB unzuverlässig. Dazu laufen zwei Schreiber (HA-Integration und PC-Upload „am HA vorbei“) auf derselben Freigabe ohne Sperrmechanismus. `serie.json` wird „atomar“ geschrieben, aber über einen Netzwerkspeicher ist das nur bedingt zusichert.
   Empfehlung: Eine Regelzeile „Zeiger auf fehlende Folge → Folge davor/Folge 1, Position 0, Ereignis protokollieren“. „Jünger“ präzise definieren (z. B. `created_at` in `serie.json`). Bekannte Einschränkung des Parallel-Schreibens als Risiko eintragen.

6. **Major — CUJ 7b, Baustein 4 MQTT (Z. 625–629), Baustein 3 `ha`: Lernmodus ist ein verteilter Zustand ohne klaren Besitzer.**
   HA startet („cmd“), die Box hat die 2-min-Frist, HA fragt vor dem Überschreiben nach. Offen sind:
   - Wer misst die 2 min, HA oder die Box? Bei Box-offline bleibt ein nicht-persistenter `cmd` evtl. hängen. Ist er „retained“, startet er später unerwartet.
   - Welche der zwei Boxen lernt? Zwei Boxen melden gleiche unbekannte Figuren (Weg A), ohne Dedup-Regel.
   - Was passiert, wenn die Figur während der Rückfrage abgehoben wird?
   Ähnlich ist `unknown.json` „an HA, dann leeren“ ohne Bestätigung (Ack) ein At-most-once-Verfahren: bei Verbindungsabbruch gehen Meldungen verloren.
   Empfehlung: Lernmodus als expliziten Teilautomat der Box mit Frist auf der Box. Befehle mit Box-ID, nicht retained, mit Ablaufzeit. `unknown`-Einträge erst nach Bestätigung durch HA löschen.

7. **Major — CUJ 13 und Protokoll v1 (Z. 478–498): Zustandsabgleich nach Leser-Neustart fehlt.**
   Nach Neustart des ESP32 beginnt `seq` bei 0 (Lückenerkennung bricht), und die Firmware meldet `HELLO`, danach evtl. erneut `PLACED` für die liegende Figur. Der Kern muss „gleiche Figur wie vorher“ von „neues Auflegen“ unterscheiden, sonst startet die Serie neu (CUJ 13 verlangt das Gegenteil). Außerdem: Wird die Figur während der Verbindungsunterbrechung abgehoben, bleibt der Kern im Zustand „liegt“ und spielt weiter, weil kein `REMOVED` ankommt. Der Zeitpunkt, ab dem der Wächter „unbekannt“ als „weg“ wertet, ist nicht festgelegt.
   Empfehlung: Festschreiben: `HELLO` setzt `seq` neu und löst im Kern „Zustand unbekannt“ aus. Danach Abgleich über `PLACED`/`present=`. Eine Karenzzeit für Pause bei Wächter-Alarm definieren. Das `seq`-Zurücksetzen im Protokoll dokumentieren.

8. **Major — Update (Z. 651–681): Rückfall kennt nur Code, nicht die Zustandsdateien.**
   Das Paket enthält Schema-Versionen. Die neue Version kann `mappings.json`/`resume.json` in einem neuen Schema schreiben. Der Rückfall stellt `current` zurück, aber die ältere Version kann die neuen Dateien eventuell nicht lesen. Das „Sichern der Zustandsdateien“ wird erwähnt, ein Rückspielen beim Rückfall aber nicht. Außerdem verteilt sich der Mechanismus auf `ExecStartPre`-Zähler, `OnFailure=`, einen systemd-Timer und eine Zustandsdatei: vier Teile, die schwer als Ganzes zu testen sind. Der Zähler zählt jeden Start mit, auch einen normalen Neustart durch das Fehlverhalten einer Leser-Neuverbindung. Der Selbsttest führt Unit-Tests auf der Box aus, das heißt, pytest und Testcode gehören in jedes Release.
   Empfehlung: Regel „Schemaänderungen nur abwärtskompatibel lesbar oder Rückspielen der gesicherten Dateien beim Rückfall“. Die Rückfall-Logik als eine kleine, einzeln testbare Python-Funktion plus ein Test mit simuliertem systemd. Die Bedingung „3 Starts“ klar auf die Testphase begrenzen.

9. **Major — Risiken (Z. 210–221) und Standard „Risks & Limits“: Tabelle ohne Gegenmaßnahmen, Sicherheitsrisiken fehlen.**
   Die Tabelle hat nur „Wann geprüft“ und keine Mitigation. Fehlen:
   - MQTT ohne Authentifizierung/Transportverschlüsselung über Tailscale,
   - der HA-HTTP-Upload-Endpunkt (Z. 624) als Angriffsfläche,
   - Tailscale-ACL-Fehlkonfiguration,
   - das Schreibrecht von HA auf das NAS,
   - Skalierungsgrenzen (SD-Platz, Pi 3A+ mit 512 MB RAM gegen MPD-DB und rsync).
   Der Standard verlangt Fehlermodi, Sicherheit und Gegenmaßnahmen.
   Empfehlung: Spalten „Auswirkung“ und „Gegenmaßnahme“ ergänzen und die genannten Risiken aufnehmen.

10. **Major — Dokumentstruktur (Gesamtgliederung, Z. 159–221, 713–733, 566–584 vs. 585–628): Gleiche Inhalte stehen mehrfach, Quelle der Wahrheit unklar.**
    - Die Reihenfolge-Regel steht in Entscheidungen (Z. 175–177), Datenmodell (Z. 543–546), Baustein 4 (Z. 598–599) und D2 (Z. 722–730).
    - Die D2-Zweitregeln (Ordner ohne `serie.json`, doppelte ID) stehen in D2 und im Datenmodell.
    - Die Revisionsregel und die MQTT-Themen sind auf „Home Assistant“ und „Baustein 4“ verteilt, die Aufgabe des Schreibers „einziger Schreiber“ steht an zwei Stellen.
    - Die Zeitgrenzen stehen in Ziel 2, CUJ 1/2/8 und Baustein 1.
    Mit mehreren KI-Agenten über Jahre driften solche Kopien auseinander.
    Empfehlung: Je Regel einen Stammplatz festlegen (Datenmodell bzw. Baustein 4), alle anderen Stellen verweisen nur darauf. „Offene Architektur-Entscheidungen“ enthält nur noch entschiedene Punkte und gehört umbenannt (z. B. „Entscheidungen D1–D3, Begründung“) oder in „Entscheidungen“ zusammengelegt.

11. **Nit — Heading-Hierarchie und Nummerierung (Baustein 1–4, Z. 429–733):**
    - Nur Baustein 1, 2, 3 und 4 sind nummeriert. Die ebenfalls bausteinartigen Abschnitte „Home Assistant“, „Netz, Sync, Strom“, „Update“, „Fehlersuche“, „Mac und Pi“ sind es nicht.
    - „Home Assistant“ (Z. 566) steht vor „Baustein 4 — HA-Integration“ und überschneidet sich inhaltlich.
    - Das Architekturdiagramm nennt `sync`/`update`/`ha` als Teile des Dienstes (Baustein 3), die Beschreibung steht aber in eigenen Abschnitten außerhalb.
    - Sprachmischung der H2-Überschriften (Overview, The Problem, Goals, Technical Plan, Alternatives Considered, Open Questions vs. Begriffe, Ausgangslage, Entscheidungen, Risiken).
    - „Technical Plan (Architecture)“ ist H2, „Datenmodell und Dateien“ ist H3 ohne Bausteinnummer, obwohl es Baustein 3 und 4 überspannt.
    Empfehlung: Nummerierung vereinheitlichen oder auf Bausteine nur für Komponenten beschränken. „Home Assistant“ in Baustein 4 integrieren oder als „Schnittstelle Box ↔ HA“ klar von der Integration trennen. Sprache der Überschriften vereinheitlichen.

12. **Nit — Modultabelle (Z. 502–517): Abhängigkeitsrichtung und Wurzel des Programms fehlen.**
    Es gibt keinen Zusammenbau-Punkt („composition root“, `main`/`app`), der Reader, Core, Player, HA und Hardware-Treiber verdrahtet. Die Ereignisquellen im Satz zum Kern (Leser, Player, HA, Zeitgeber) lassen Hardware-Module (Tasten, Kopfhörer), Netz/Strom, Sync und Update als Ereignisquellen aus, obwohl die CUJs sie brauchen. `events.py` hat zwar „einen Eigentümer“, aber noch keinen vollständigen Katalog. Ebenso passt „Selbsttest führt Unit-Tests des Kerns aus“ nicht zur Aussage, dass Testcode auf die Box gehört (siehe 8).
    Empfehlung: Eine kurze Regel „Abhängigkeiten zeigen nur nach innen zu `events`/`core`; nur `app.py` kennt alle Module“. Im Ereigniskatalog alle Quellen auflisten.

Hinweis zur Alternatives-Regel (Nit, nicht in der Zahl): „ESPHome mit PN5180“ (Z. 767–770) begründet nur mit „vermutlich“; ein konkreter technischer Grund (ESPHome-Komponente kann kein ISO 15693-Passwort-Unlock) wäre belegbarer.

## Rohtext Stil (Haiku)

REVIEW: Style Goldfish. Ziel: /home/user/Tobi_box/docs/egm/software-prototyp/design_draft.md, Zeilen 1 bis 832 (bis vor „## Detailed Implementation“, Zeile 833). Keine Blocker. 11 Major, 1 Nit-Sammelpunkt. Sortiert nach Schwere.

1. **Major — Zeilen 45-46 (Begriff „Entsperren / gesperrter Tonie“)**
   Befund: „Tonies sind im Privacy-Modus“ verallgemeinert. CUJ 6 (Zeile 268: „Ein Tonie im Privacy-Modus“) und Baustein 1 (Zeile 454) sagen, dass nur manche Tonies betroffen sind. Der Satz widerspricht dem Rest des Dokuments.
   Rewrite: „Manche Tonies sind im Privacy-Modus. Sie antworten erst, nachdem die Box sie mit dem Passwort entsperrt hat. Mehr im Abschnitt „Baustein 1“.“

2. **Major — Zeilen 125-127 (Ziel 5, Stromausfall)**
   Befund: „Kein Zustand geht durch Stromausfall verloren oder kaputt“ ist absolut und widerspricht im selben Satz „höchstens der letzte Resume-Stand … darf fehlen“. Die Aussage ist nicht prüfbar. Befund ist CALIBRATE.
   Rewrite: „Bei Stromausfall geht höchstens der letzte Resume-Stand (≤ 30 s Wiedergabe) verloren. Alle Zustandsdateien werden atomar geschrieben und beim Start geprüft.“

3. **Major — Zeilen 130-131 (Ziel 7, „Updates sind sicher“)**
   Befund: „sicher“ ist ein Werturteil ohne Maßstab. Der Nutzen steckt schon im Rest des Satzes. Befund ist DROP für das Adjektiv.
   Rewrite: „**Updates sind geprüft:** nur manuell aus HA, nur daheim am Lader, mit Selbsttest. Schlägt er fehl, läuft beim nächsten Start wieder die alte Version.“

4. **Major — Zeilen 424-425 (Netz-Abschnitt)**
   Befund: „nichts ist aus dem Internet erreichbar“ ist eine absolute Behauptung. Der Tailscale-Zugang ist laut Risiken (Zeile 218) noch nicht eingerichtet, also nicht belegt. Befund ist CALIBRATE.
   Rewrite: „Die Box öffnet keinen Port ins Internet. Zugriff von außen läuft nur über HA (Nabu Casa) und Tailscale.“

5. **Major — Zeile 713 (Überschrift „Offene Architektur-Entscheidungen (für Tobias)“), Verweis in Zeilen 161-162**
   Befund: Die Überschrift sagt „offen“. Alle drei Einträge (D1 bis D3) sind mit „Entschieden“ markiert. Leser suchen dort falsche Informationen. Der Verweis in Zeile 161-162 führt in die Irre.
   Rewrite: Überschrift „Architektur-Entscheidungen D1 bis D3 (mit Begründung)“. Verweis in Zeile 161-162 entsprechend anpassen.

6. **Major — Zeilen 769-770 („ESPHome mit PN5180“)**
   Befund: „Tonie-Entsperrung fehlt vermutlich“ ist eine ungeprüfte Vermutung ohne Entscheidung für den Leser. Befund ist CALIBRATE.
   Rewrite: „**Abgelehnt von der Projektleitung:** Für ESPHome ist die Tonie-Entsperrung nicht geprüft. Die eigene Firmware ist mit `firmware/tonie_test/` erprobt.“

7. **Major — Zeilen 742-747 („Phoniebox V3 als Basis“)**
   Befund: „in wenigen Jahren nicht mehr frisch installierbar“ ist eine Prognose ohne Quelle, als Tatsache formuliert. „instabile Plugin-Schnittstelle“ ist ein Werturteil. Der Satz „Bestätigung nach dem ersten Pi-Lauf“ ist unklar. Befund ist CALIBRATE.
   Rewrite: „… V3 bliebe nur als MPD-Steuerung mit einer Plugin-Schnittstelle ohne Stabilitätszusage und einem eingefrorenen Versionsstand. Ob er künftig nicht mehr installierbar ist, ist nicht geprüft.“ Letzter Satz: „Die Entscheidung wird nach dem ersten Pi-Lauf überprüft.“

8. **Major — Abschnitt „Begriffe“ (Zeilen 30-71), fehlende Begriffe**
   Befund: Mehrere Begriffe werden verwendet, aber nicht erklärt. Die Regel lautet „Begriffe einmal erklären“. Fehlen: Lernmodus (Zeile 285), Lautstärke-Obergrenze (Zeile 139), Status-Admin-Karte (Zeile 322), Gute-Nacht-Karte (Zeile 342), Leise-Zeiten (Zeile 351), Netz-Klasse und SSID (Zeilen 632-634), Hotspot (Zeile 147), ReplayGain und rsync (Zeilen 186-192, 644), Lit (Zeile 622).
   Rewrite: Je Begriff eine Zeile in „Begriffe“ ergänzen, z. B.: „*   **Lernmodus:** HA-Modus, in dem die nächste aufgelegte Figur für 2 min der gewählten Serie zugeordnet wird.“ Und: „*   **Netz-Klasse:** `home`, `hotspot` oder `offline`; siehe „Netz, Sync, Strom“.“

9. **Major — Zeilen 75-78 („The Problem“)**
   Befund: „Die Box muss sich genau so verhalten, wie er es sich vorstellt“ ist subjektiv und nicht messbar. Die Ziele sind an anderer Stelle prüfbar (CUJs ab Zeile 223).
   Rewrite: „Die Box muss alle Abläufe aus den CUJs erfüllen, auch mit geborgten Figuren, unterwegs ohne Netz und nach einem leeren Akku.“

10. **Major — Zeilen 144-145 (Abschnitt „Non-Goals“)**
   Befund: Der erste Satz des Abschnitts sagt „Hardware-Funktionen … gehören zum Umfang“. Ein Nicht-Ziel-Abschnitt darf das nicht als Einstieg haben. Der Widerspruch verwirrt den Leser beim Abgrenzen des Umfangs.
   Rewrite: „Nicht im Umfang sind: …“ und den Hinweis auf Hardware-Funktionen als eigenen, nachgestellten Satz setzen: „Hardware-Funktionen gehören dagegen zum Umfang (Ziel 9, Stufe 4).“

11. **Major — Zeile 299 (CUJ 8) gegen Zeilen 445-446 (Baustein 1)**
   Befund: CUJ 8 nennt „2–3× gleich gelesen“. Baustein 1 legt 2 Lesungen fest, mit 3 als möglichem Fall. Die Spanne lässt dem Leser keine Entscheidung. Befund ist CALIBRATE.
   Rewrite: „Erst wenn eine neue Kennung in Folge gleich gelesen wurde (Anzahl: siehe Baustein 1), gilt sie.“

12. **Nit — Zeilen 15, 84-86, 88, 106-107, 306, 813, 830 (Wortwahl und Konsistenz)**
   Befund: Mehrere Wörter sind wertend oder ungenau.
   - Zeile 15: „komplette Software“. Rewrite: „die gesamte Software“.
   - Zeile 85-86: „Fast alles, was die Box besonders macht“. Rewrite: „Die meisten Funktionen der Box wären eigener Code.“
   - Zeile 88: „schlanke Box-Software“. Rewrite: „eigene Box-Software“.
   - Zeile 106: „Neu ist alles in diesem Dokument“. Rewrite: „Neu sind die Firmware …, der Box-Dienst …“ (Aufzählung).
   - Zeile 306: „halbe Dateien sind nie abspielbar“. Rewrite: „Dateien mit unvollständiger Übertragung sind nie abspielbar.“
   - Zeile 813: „Abgelehnt vom Autor“. Autor ist laut Kopfzeile Tobias. Rewrite: „Abgelehnt von Tobias“.
   - Zeile 830: „Nicht möglich“. Rewrite: „Mit dem Chip allein nicht möglich“.
   - Zeile 38 und 271: „Überraschungs-Ordner“ für dieselbe Sache wie Zeile 39 „Serie“. Begriffe gleich benennen (Vorschlag: „Überraschungs-Serie“ überall).

Zusätzlich offen (kein eigener Punkt, weil Lesbarkeit und Scope bereits erfasst): Der Begriff „Stand“ bedeutet an mehreren Stellen den Zeiger (Zeile 245, 255), an anderen den Zustand (Zeile 663). Vorschlag: „Zeiger“ für den gespeicherten Resume-Stand verwenden und „Stand“ nicht mehr für ihn nutzen.
