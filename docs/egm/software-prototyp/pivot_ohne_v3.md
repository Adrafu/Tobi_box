# Richtungswechsel: Box-Software ohne Phoniebox V3?

* **Datum:** 2026-11-05
* **Status:** Vorschlag der Projektleitung, zur Goldfisch-Prüfung
* **Kontext:** `concepts_brief.md` (gleicher Ordner) mit allen Entscheidungen
  bis Runde 1; Recherchen `research_phoniebox_v3.md`,
  `research_pn5180_esp32s3.md`; Plan `docs/plan/stueckliste-und-psp.md`.

## Frage

Nach den Entscheidungen in `concepts_brief.md` übernehmen eigene Bausteine
fast alles, wofür Phoniebox V3 gewählt wurde:

| Aufgabe | Zuständig nach `concepts_brief.md` |
|---|---|
| Leser, Auflegen/Abheben | eigene Firmware + eigenes Leser-Modul; V3-Abhebe-Erkennung wird abgeschaltet |
| Resume, Serien, nächste Folge, Überraschung, Zuordnung Weg A/B | eigener Kern (Python-Paket ohne V3) |
| Bedienoberfläche | Home Assistant (V3-Web-UI ungenutzt) |
| Medien-Sync, WLAN-Regeln, Update mit Selbsttest/Rückfall | eigener Code |
| Abspielen | MPD (V3 steuert MPD nur) |

Von V3 blieben: MPD-Steuerung, Lautstärke-Grenzen, Gute-Nacht-Timer, später
GPIO-Tasten/Encoder, MQTT, Installationsskripte (Audio-Overlay usw.).

## Vorschlag

V3 weglassen. Eine eigene, schlanke Box-Software (Python) steuert MPD direkt
(z. B. python-mpd2), liest den ESP32 direkt per pyserial, spricht per MQTT mit
Home Assistant, später gpiozero für Tasten/Encoder.

Erwartete Vorteile:
- Am Mac läuft dasselbe Programm mit nativem MPD (Homebrew), **ohne Docker
  und ohne Brücke**; die Serielle wird direkt gelesen. Mac und Pi
  unterscheiden sich nur in Konfiguration (Gerätepfad, Audio-Ausgabe von MPD).
- Keine Kopplung an eine instabile Plugin-Schnittstelle (V3 `future3/develop`
  baut den Player um).
- Weniger Speicher und Prozesse auf dem Pi 3A+ (512 MB).

Erwartete Nachteile:
- Mehr eigener Code: Lautstärke-Grenzen, Timer, Tasten, Leerlauf-Abschaltung,
  Installationsskript für Pi OS + Audio-Overlay.
- Keine Gemeinschaft, keine V3-Weboberfläche als Notweg.
- Der Plan Rev. 3.7 hatte V3 gewählt, um Eigenbau zu vermeiden.

## Zusätzlicher Punkt: Weg zum NAS von unterwegs

Tobias will über den Handy-Hotspot **alles** abgleichen, auch neue Folgen
(kein Datenlimit). Das NAS ist ein **QNAP** mit Herstellercloud
(myQNAPcloud). Nabu Casa leitet nur zu Home Assistant weiter, nicht zum NAS.
Optionen: myQNAPcloud (NAS aus dem Internet erreichbar), VPN (QNAP QVPN mit
WireGuard, oder Tailscale auf NAS und Box), oder Medien nur im Heimnetz.
Die Projektleitung neigt zu VPN, weil ein aus dem Internet erreichbares NAS
ein bekanntes Angriffsziel ist.

## Was geprüft werden soll

- Trägt der Vorschlag, oder gibt es starke Gründe, bei V3 zu bleiben?
- Welche V3-Funktionen würden wir unterschätzen (Aufwand, Fehlerquellen)?
- Gibt es fertige Bausteine, die den Eigenbau kleiner machen?
- Welcher Weg zum NAS von unterwegs ist für zwei Kinderboxen vernünftig?
