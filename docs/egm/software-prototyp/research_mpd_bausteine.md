# Research: Bausteine rund um MPD (Stand 2026-11-05)

Ziel: Gibt es fertige Projekte oder Bibliotheken, die Teile unseres Prototyps
abdecken (MPD-Steuerung, NFC-Karten auf Ordner, Resume pro Serie, MQTT/HA)?

Legende: **[V]** auf der Seite geprueft. **[S]** nur aus Suchtreffer-Ausschnitt,
nicht geoeffnet. **[N]** nicht verifiziert (Seite nicht abrufbar oder Datum fehlt).

## Vergleichstabelle

| # | Projekt | URL | Sprache | Letzte Aktivitaet | Resume pro Serie | NFC/Serial | MQTT/HA | Pflege |
|---|---|---|---|---|---|---|---|---|
| 1 | python-mpd2 | https://github.com/Mic92/python-mpd2 | Python | PyPI: 3.1.1 am 13.01.2024, Vorgaenger 3.1.0 am 28.04.2023 [V] | n/a (Bibliothek) | n/a | n/a | Unklar. Keine Commit-Daten sichtbar [N] |
| 2 | Phoniebox / RPi-Jukebox-RFID | https://github.com/MiczFlor/RPi-Jukebox-RFID | Python (v3), PHP-Webapp | Stand v3.6.0, develop aktiv, 2.499 Commits [V] | **Nein** in v3.6.0. Nur "zweiter Swipe" setzt fort (siehe `research_phoniebox_v3.md`, Abschn. 8) [V] | RFID: USB, RC522, PN532; serieller Leser per Plugin moeglich [V] | MQTT ja, HA nicht namentlich [V] | Aktiv [V] |
| 3 | TonUINO-TNG | https://github.com/tonuino/TonUINO-TNG | Arduino (Sprache nicht angezeigt) [N] | Changelog 3.4.0 vom 27.10.2026 [V] | Nur Track, nicht Position; pro Ordner unklar [V] | RFID per MFRC522, Serial-Konsole (WRITECARD) [V] | Nein [V] | Aktiv [V] |
| 4 | TonUINO-Forks (xfjx, AlexanderWillner, code723) | z. B. https://github.com/AlexanderWillner/TonUINO | Arduino | nicht geprueft [N] | nicht geprueft | MFRC522 + DFPlayer [S] | nein [S] | [N] |
| 5 | TeddyCloud | https://github.com/toniebox-reverse-engineering/teddycloud | C | Docker-Tag 0.7.0 als neuestes genannt, Datum [N] | n/a | n/a (Toniebox-Cloud-Ersatz, kein Player) [V] | MQTT + HA-Integration [V] | Aktiv, GPL-2.0 [V] |
| 6 | luniebox | https://git.bstly.de/Lurkars/luniebox | Python 49,5 %, OpenSCAD | letzter Commit 13.03.2022 [V] | nicht genannt [V] | RC522 per SPI; serielle Leser nicht genannt [V] | nein [V] | **Eingeschlafen** (seit 2022 keine Commits auf der Seite) |
| 7 | rpi-jukebox (J. Lightsmith) | https://github.com/jeremylightsmith/rpi-jukebox | nicht angegeben | keine Daten [N] | nein [V] | USB-Mifare-Leser [V] | nein [V] | [N] |
| 8 | rfid-audio-raspberry (ceigel) | https://github.com/ceigel/rfid-audio-raspberry | Python [S] | Seite 404 [N] | Karte -> Ordner als Playlist [S] | MFRC522 SPI [S] | [N] | [N] |
| 9 | rfid-jukebox (scheleaap) | https://github.com/scheleaap/rfid-jukebox | Scala (vermutet) | keine Commit-Daten [N] | nicht genannt | MFRC522 SPI [V] | nein | [N]. Backend ist **Mopidy**, nicht MPD [V] |
| 10 | myMPD | https://github.com/jcorporation/myMPD | C (Backend), JS (Frontend) | Release v26.1.2, 31. Okt. (Jahr auf Seite nicht genannt) [V] | n/a (Web-UI) | n/a | nein | Aktiv, GPL-3.0 [V] |
| 11 | ympd (notandy) | https://github.com/notandy/ympd | C | Copyright 2013-2014, kein Commit-Datum [V]. Fork steveww archiviert 16.12.2021 [S] | n/a (Web-UI) | n/a | nein | **Fraglich** [N] |
| 12 | Home Assistant MPD-Integration | https://www.home-assistant.io/integrations/mpd/ | (HA-Core) | offizielle Doku [S] | n/a | n/a | HA-seitig, per UI einrichtbar [S] | Aktiv (HA-Core) |

Zusatz: MQTT-zu-MPD-Bruecken (nicht einzeln geprueft, nur Suchtreffer [S]):
- chaosdorf/mpd-mqtt-gateway (Python, eher einseitig, Seite 404 [N])
- claes/mpd-mqtt (Go, zweiseitig, 8 Commits, keine Lizenz sichtbar [V])
- mqttmpd auf PyPI (Python, einfacher MQTT-Controller [S])
- rocus/mpd2mqtt, empi89/mqtt2mpd (Node.js-PoC) [S]

## Einzelbewertung kurz

- **python-mpd2:** Die Bibliothek, die wir ohnehin nutzen wollen. LGPL-3.0, Python >= 3.6.
  Das letzte PyPI-Release ist von 2024. Das ist kein Problem fuer eine stabile
  Client-Bibliothek, aber wir sollten es vor dem Start pruefen und ggf. pinnen.
- **Phoniebox (MiczFlor):** Am naechsten an unserem Ziel. MIT-Lizenz, MQTT, RFID-Plugins,
  MPD-Backend. Fehlt aber genau das, was wir brauchen: Resume ueber Ordnerwechsel
  (v3.6.0 setzt Resume fest auf OFF, siehe `research_phoniebox_v3.md`). Die Plugin-Architektur
  ist als Vorlage brauchbar, der Code nicht direkt.
- **TonUINO-TNG:** Gute Vorlage fuer Karten-zu-Ordner-Zuordnung und Admin-Karten, aber
  Arduino/DFPlayer, kein MPD, kein Pi. Resume nur pro Track.
- **TeddyCloud:** Ein Server, der die Toniebox-Cloud ersetzt. Kein Player, keine Relevanz
  fuer unseren Prototyp. Nicht uebernehmen.
- **luniebox:** Pi-basiert, aber seit 2022 ohne Commits. RC522 statt PN5180. Als Referenz
  hoechstens fuer das Systemd-Setup.
- **rpi-jukebox, rfid-audio-raspberry, rfid-jukebox:** Kleine Einzelprojekte, teils
  nicht verifizierbar, teils Mopidy statt MPD. Keine Resume-Logik belegt.
- **myMPD:** Aktiv gepflegt, MPD-Sticker-Unterstuetzung, Jukebox-Modus. Gut als
  Notfall-Web-UI neben unserem Dienst.
- **ympd:** Alt (Copyright 2013-2014), Fork-Lage unuebersichtlich. Nur bei Bedarf.
- **Home Assistant MPD-Integration:** Offiziell, kann Playlisten laden (`play_media`),
  kann aber keine Playlisten bearbeiten. Laut Doku auch mit Mopidy-MPD nutzbar.
- **MQTT-Bruecken:** Alle klein und teils ohne Lizenz oder Pflegeangabe. Eine eigene
  MQTT-Anbindung in unserem Dienst ist vermutlich weniger Aufwand als eine Bruecke
  einzubinden.

## Was fehlt im Markt (Befund)

- Kein geprueftes Projekt kombiniert: MPD + serieller ESP32-Leser (PN5180) + Resume
  pro Serie + MQTT. Die naechsten Kandidaten (Phoniebox, luniebox) erfuellen jeweils
  nur Teile davon.
- Der ESP32-Teil (PN5180, serielles Protokoll) ist in keinem der geprueften Projekte
  vorhanden. Unser serielles Protokoll muessen wir selbst definieren.
- Das Resume-Verhalten ist der eigentliche Eigenbau-Teil. Phoniebox hat es nicht.

## Was wir wiederverwenden koennen

1. **python-mpd2** als MPD-Client. Vor Start Release und Python-Version auf dem Pi pruefen
   (Pi 3A+ laeuft mit Raspberry Pi OS, Python 3.11 ist dort ueblich [N]).
2. **myMPD** als Notfall-Web-UI auf dem Pi, ohne eigenen Code.
3. **Home Assistant MPD-Integration** fuer Anzeige und Grundsteuerung in HA. Die eigentliche
   Logik (Resume, naechste Folge) bleibt bei uns; HA sieht nur den Zustand.
4. **Phoniebox-Plugin-Muster** (MIT) als Architekturvorlage fuer den Karten-Event-Weg.
   Code nur uebernehmen, nach Lizenzhinweis.
5. **TonUINO-TNG** als UX-Vorlage fuer Karten-Anlernen und Admin-Karte. Keine Code-Uebernahme.
6. **Nicht uebernehmen:** TeddyCloud (falsche Klasse), luniebox (veraltet), Mopidy-basierte
   Projekte (falscher Backend).

## Offene Punkte (nicht verifiziert)

- Aktueller Stand von python-mpd2 nach 2024 (GitHub-Seite ohne Datum).
- Pflegezustand von ympd, ceigel/rfid-audio-raspberry, chaosdorf/mpd-mqtt-gateway
  (Seiten nicht abrufbar bzw. ohne Datum).
- Ob luniebox intern MPD nutzt (nur Suchtreffer-Angabe, nicht im Seiteninhalt bestaetigt).
- Jahr des myMPD-Releases v26.1.2 (Seite zeigt nur "31 Oct").
