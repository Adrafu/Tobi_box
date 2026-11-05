# Goldfisch-Prüfung „ohne V3“ — Rohbefunde

Ziel: `pivot_ohne_v3.md`. Zwei Goldfische ohne Gesprächsverlauf.

## Wartbarkeit (structural, Sonnet)

Urteil: (a) eigene Python-App auf MPD ist über Jahre tragfähiger, wenn der Umfang schriftlich begrenzt wird. Die Hauptlast (Kern, Update/Rückfall, NAS-Weg) ist bei (a) und (b) gleich.

1. Blocker — NAS nie direkt aus dem Internet (QNAP: Qlocker, DeadBolt). VPN mit einem Peer pro Box, ACL nur auf Medienordner, NAS-Konto nur lesend, Schlüssel pro Box widerrufbar; Betriebspflichten (Schlüssel erneuern, Zustand „VPN fehlt“). Tailscale (wenig Wartung, Drittanbieter) vs. QVPN/WireGuard (Port am Router, Handarbeit).
2. Blocker — Update/Rückfall ist die eigentliche Langzeitlast; Paket atomar, Wächter, SD-Image pro Box als Notweg ohne Netz; jährliches neues OS-Image statt „nie“.
3. Major — V3-Pin ist Einfrieren; ohne Spiegel (Fork, Wheel-Cache, Image) in 2–3 Jahren nicht mehr installierbar.
4. Major — Bei (a) liegt die Last in den Randfällen der nachgebauten Funktionen (Lautstärke, Timer, Leerlauf, MPD-Neustart, DB-Neuaufbau nach Sync, Installationsskript). Feste Liste nachbauen/entfällt, Tests gegen echtes MPD, MPD nur über ein dünnes Modul.
5. Major — Bei (b) drei Wahrheiten (`cards.yaml`, Kern, `music_player_status.json`).
6. Major — Ein-Personen-Projekt: Betriebshandbuch mit Wiederherstellung von Null, „was ist wo konfiguriert“, gepinnte Versionen.
7. Major — Box spielt vollständig ohne HA und Netz; MQTT-Themen mit Schema und Discovery; lokaler Notweg (Konfigdatei + SSH / Admin-Befehl).
8. Major — „Läuft am Mac“ darf keine Scheinsicherheit werden: Prüfliste am echten Pi, Konfig Mac/Pi ohne Codeverzweigung.
9. Major — Zwei Boxen: gleiches Paket, Version und Medienstand an HA, Kartentausch ≤ 30 min; Aufräumen alter Folgen.
10. Nit — Ausstiegskriterium in Zahlen fehlt.

## Contrarian / YAGNI (zoom_out, Sonnet)

Urteil: „V3 weglassen“ überlebt, aber nur in kleinster Form und erst am Pi endgültig bestätigt.

1. Blocker — Entscheidung fällt vor dem Pi; V3-Installskripte sind am Pi erprobt (Audio-Overlay, Boot, WLAN-Powersave). Kern ohnehin V3-frei bauen; Pi jetzt bestellen; V3-Skripte am Pi höchstens als Vorlage.
2. Blocker — Jeder V3-Berührungspunkt ist ein Adapter = Eigenbau, schlechter testbar. Kern-Schnittstelle zum Player: `play(folder, position)`, `pause()`, `volume(n)` über python-mpd2.
3. Major — Unterschätzte V3-Funktionen (Max-/Startlautstärke, Gute-Nacht-Timer, Idle-Shutdown, Encoder, MQTT, Installskript, WLAN-Powersave). Nur bauen, was die Stufe braucht; paho-mqtt statt Eigenbau.
4. Major — Das YAGNI-Problem ist der Umfang (Update-Wächter, Puffer, Admin-Karte, Szenario-Framework), nicht V3. Update klein: neues Verzeichnis, Selbsttest, Symlink, systemd `OnFailure=` / Boot-Zähler; SD-Image vor dem ersten Update.
5. Major — Notweg ohne HA: SSH + Kommando `tobibox status`, oder fertige MPD-Weboberfläche (myMPD/ympd, unverifiziert).
6. Major — NAS: QNAP selbst riet 2022 nach DeadBolt (QSA-22-24) von Port-Forwarding ab. Empfehlung Tailscale (offizielle QNAP-App), ACL nur NAS-Medien; nicht myQNAPcloud, nicht QVPN (offener UDP-Port).
7. Major — Hotspot-Abgleich ohne Zahl: rsync `--bwlimit`/`--max-size`, nur am Lader oder über Akku-Schwelle.
8. Major — Hauptgewinn: Mac ohne Docker und ohne Brücke; ein Transport, nur der Gerätepfad unterscheidet sich. Leser-Ausfall am Mac mit socat-pty testen.
9. Major — Vorhandene MPD-Jukebox-Projekte nicht geprüft; kurze Recherche (Haiku) mit Tabelle. Resume = MPD `seek`, Kern klein halten.
10. Nit — Speicher- und „instabile Schnittstelle“-Argument sind schwach (Pin friert ein); Hauptgrund ist: Kern und Leser sind ohnehin eigen, der Adapter wäre Zusatzcode.
