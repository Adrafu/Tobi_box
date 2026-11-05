# Goldfisch-Brainstorm — Rohbefunde

Ziel: `hypothese.md`. Sechs Goldfische, je ein Blickwinkel, ohne Gesprächsverlauf.
Zusammenfassung und Bewertung: `concepts_brief.md`.

## UX & Bedienung (comprehension, Haiku)

1. Blocker — Ort der Zuordnung unklar: Plan sagt „Handy-Seite der Box, nur lokal“, Hypothese sagt „nur HA“. Weg A/B je Ort (daheim/unterwegs) festlegen.
2. Blocker — Kind-Rückmeldung für Abläufe 6, 7, 8 undefiniert; am Mac nicht abnehmbar. Je Ablauf ein benanntes Ereignis + Rückmeldung (Ton) + sichtbares Log.
3. Major — Lernmodus (Weg B) überschreibt still, wenn ein Kind eine bekannte Figur auflegt. Bestätigung mit Kennung + Serie, Überschreiben bekannter Figur nur mit Bestätigung, Lernmodus hörbar.
4. Major — Keine Korrektur: „Figur lösen“, „Serie zurücksetzen“, Fortschritt anzeigen fehlen.
5. Major — Ereignisformat nur Beispiele, kein Fehlerkatalog; tote Brücke = „keine Figur“. Versioniertes Format, Fehlerkatalog, Heartbeat.
6. Major — Simulations-Schalter (WLAN, Dock, Strom) und durchgehendes Ereignis-Log (gelesen → entprellt → weitergeleitet → gespielt) nicht festgelegt.
7. Major — Konfliktregel beim Abgleich zweier Boxen fehlt; Sync-Status (synchron/ausstehend/Konflikt) in HA.
8. Major — Ordner-/Namensregel für Serien auf dem NAS fehlt; fehlende/leere Serie melden.
9. Major — Update: Auslöser, Ergebnis, Verhalten während Benutzung undefiniert.
10. Nit — Gerätepfad, Brückenadresse, Schalter als Konfiguration; Mac→Pi ein dokumentierter Schritt.

## Beobachtbarkeit & Fehlersuche (codebase_details, Haiku)

1. Blocker — Kein Gesundheitskanal über alle Schichten; „spielt nicht“ ist nicht eingrenzbar. Heartbeat je Schicht (Name, Version, Laufzeit, letzte Aktion, letzter Fehler), offline lesbar.
2. Blocker — Logs auf tmpfs (Plan 5.1.5) sind nach Stromausfall weg. Kleiner persistenter Ringpuffer nur bei Zustandswechsel/Fehler + Marke „sauber heruntergefahren“. Keine Geheimnisse im Log.
3. Blocker — Lesefehler sind still (Firmware meldet PN5180-Fehler als „nichts da“). Fehler getrennt zählen; Leser-Modul/Brücke loggen Gerätewegfall und verbinden sich selbst neu.
4. Major — Vorgangs-ID je Auflegen über die ganze Kette (Lesung → Entprellung → Zuordnung → Aktion → Wiedergabe).
5. Major — Entprellung im Feld nicht überprüfbar; Zähler (Abfragen, Treffer, verworfen, Fehler, Lesezeit) in Heartbeat.
6. Major — Verbindungszustand der Brücke/des Moduls sichtbar; `/dev/serial/by-id`; Test mit socat-pty.
7. Major — Update-Journal (alte/neue Versionen, Selbsttest, Rückfall-Grund, Build-ID der Firmware).
8. Major — Sync-Stand und Konflikte protokollieren; letzter erfolgreicher Sync sichtbar.
9. Major — Fehlerklassen mit eindeutigem Ton; Status-Admin-Karte (Leser, Netz, Medien) ohne Handy/HA.
10. Nit — Einheitliches Log-Schema (Zeit + Zeitquelle, Schicht, Ereignis, Vorgangs-ID), Simuliertes als „SIM“ markiert.

## Wartbarkeit (structural, Sonnet)

1. Blocker — V3 hat keine stabile Plugin-API, `future3/develop` baut den Player um. Eigener V3-freier Kern + dünner V3-Adapter mit Liste der Berührungspunkte; Version per Commit pinnen.
2. Blocker — Verteilter Zustand mit Offline-Schreiben (Box 1, Box 2, HA). Eine Quelle der Wahrheit je Datenart; Resume strikt pro Box lokal; Schema-Version; Konfliktregel; keine Zwei-Wege-Replikation.
3. Major — Serielles Protokoll als Vertrag spezifizieren (Version, Heartbeat, Fehlerzeilen, maschinenlesbare Tokens, Golden-Lines-Testdatei), Rückkanal reservieren.
4. Major — Brücke = anderer Transport als am Pi; Leser-Modul mit einer Eingabeschnittstelle, Transport per Konfiguration; Simulation an denselben Schnittstellen wie echte Hardware.
5. Major — Update ist selten laufender, kritischer Pfad; Release-Paket mit Manifest, Rückfall per Symlink, Kompatibilitätsmatrix Firmware/Protokoll/Schema.
6. Major — HA als einzige Oberfläche: Box bietet versionierte Schnittstelle (MQTT/REST), HA nur Client; Notweg ohne HA; HA-Konfiguration als Datei im Repo.
7. Major — Eigenes Domänenmodell (Kennung, Figur, Serie, Folge, Wiedergabestand), UID-Normalisierung an einer Stelle; „Figur → Serie → nächste Folge“ passt nicht zu V3 „Karte → Ordner“.
8. Major — Firmware-Build reproduzierbar (PlatformIO mit festen Versionen), Flash-Anleitung, Passwort sicher verwahren; Entprell-Logik als reine Funktion testbar.
9. Major — Medien-Sync: rsync + Manifest, Zugangsdaten in Konfiguration, Verhalten bei verschwundenen Folgen.
10. Major — Abläufe 1–8 als ausführbare Szenarien (Zeilen rein, Player-Zustand raus); alle Zeitkonstanten an einer Stelle, nur eine Stelle entprellt.
11. Nit — Log-Puffer beim Laden abholbar, SSH im Heimnetz als Standardweg.
12. Nit — Pi nativ oder Docker? Pi 3A+ (512 MB) mit drei Containern knapp; Unterschiede Mac/Pi als geprüfte Liste.

## Contrarian / YAGNI (zoom_out, Sonnet)

1. Blocker — „Verhält sich exakt wie die Box“ ist am Mac nicht erreichbar (Docker, Brücke, Audio über TCP, Schalter). Ziel auf „Logik testbar“ zurücknehmen; früh einen echten Pi als Zielplattform.
2. Blocker — Widerspruch Leser: Übergabe sagt HID, Hypothese seriell, Recherche empfiehlt HID. Begründung fehlt. Vorschlag: Stufe 1 mit HID.
3. Major — ESPuino (ESP32 als kompletter Player) nicht nachweislich geprüft; Muster wiederverwenden.
4. Major — Box↔HA-Sync ist ein verteiltes System. Vorschlag: Wahrheit in einer Datei auf dem NAS, einseitiger Fluss; HA nur lesend.
5. Major — HA als einzige Oberfläche ohne Not; V3-Web-UI + V3-MQTT nutzen.
6. Major — Update mit Selbsttest/Rückfall YAGNI; `git pull` + Tag, SD-Backup, 20-Zeilen-Selbsttest.
7. Major — NAS-Sync: rsync/Syncthing + systemd-Timer, HA nicht im Ablauf.
8. Major — Ablauf 7 (Weg A/B) hängt an Stufe 3; zuerst Minimalform.
9. Major — Resume: kleiner Hook auf `play_card_callbacks` + JSON {Ordner: Titel, Sekunde}; „nächste ungehörte Folge“ getrennt halten.
10. Major — Brücke ist ein dritter Codepfad; Alternativen: V3 nativ, socat-pty, Linux-VM mit USB-Durchreichung.
11. Nit — Ablauf 6 ist auf Software-Seite gleich Ablauf 7.
12. Nit — ESPHome als Alternative (unverifiziert), nicht empfohlen.
