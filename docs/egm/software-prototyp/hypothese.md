# Software-Prototyp Tobi Box — Arbeitshypothese

* **Autor:** Tobias (mit Projektleitung)
* **Datum:** 2026-11-05
* **Status:** Hypothese für den Goldfisch-Brainstorm (EGM), noch kein Design

## Ziel

Die komplette Software der Tobi Box als Prototyp bauen, **bevor** die Box
gebaut ist. Der Prototyp soll sich genau so verhalten wie die fertige Box,
damit an der Box selbst nicht mehr programmiert und gesucht werden muss.

Er läuft zuerst auf einem **Mac** (Phoniebox V3 in Docker) und später
**unverändert** auf dem Raspberry Pi 3 Model A+ der Box.

## Vorhandene Hardware

- ESP32-S3 SuperMini mit PN5180, zusammengesteckt, am Mac per USB
- Ein Tonie-Testsketch läuft darauf (`firmware/tonie_test/`): liest
  NTAG215-Karten (ISO 14443A) und Tonies (ICODE SLIX-L, ISO 15693),
  entsperrt Tonies im Privacy-Modus mit einem eigenen Passwort.
- Noch **kein** Pi, kein PiSugar, kein Verstärker/Lautsprecher.

## Abläufe, die der Prototyp können muss (alle in der ersten Fassung)

1. Eigenen Tonie auflegen → das zugeordnete Hörspiel startet.
2. Abheben → Pause.
3. Denselben Tonie wieder auflegen → weiter an derselben Stelle (Resume).
4. Anderen Tonie auflegen → dessen Hörspiel startet von vorn
   bzw. bei einer Serie die nächste ungehörte Folge.
5. NTAG-Karte auflegen → wie ein Tonie.
6. Gesperrter Tonie (Passwort unbekannt) → Überraschungs-Hörspiel.
7. Unbekannter, lesbarer Tonie → Überraschungs-Hörspiel, danach einer Serie
   zuordenbar (Weg A und B aus `docs/plan/stueckliste-und-psp.md`,
   Abschnitt „Figuren zuordnen“).
8. Figur am Rand oder kurz verrutscht → kein Stottern, kein falsches Hörspiel.

## Architektur (Annahmen)

- **Leser:** Die Firmware auf dem ESP32-S3 meldet Ereignisse als Textzeilen
  über die USB-Serielle Schnittstelle (z. B. „aufgelegt <Kennung>“,
  „abgehoben“, „gesperrter Tonie“). Keine USB-Tastatur mehr.
  UID-Entprellung (2–3× gleich gelesen) in der Firmware.
- **Phoniebox V3** (feste Version, z. B. v3.6.0) als Basis. Ein eigenes
  **Leser-Modul** in V3 liest die serielle Schnittstelle.
  - Am Mac: Docker kann nicht auf USB-Geräte zugreifen → eine kleine
    **Brücke** auf dem Mac liest die Serielle und reicht die Zeilen an den
    Container weiter (z. B. über TCP).
  - Am Pi: das Leser-Modul liest die Serielle direkt.
- **Eigene Plugins** in V3: Resume, Figuren-Zuordnung, Überraschungs-Ordner.
- **Oberfläche:** ausschließlich **Home Assistant**, von unterwegs über
  Nabu Casa erreichbar. Die Box selbst wird nicht ins Internet geöffnet.
  Zuordnungen, Status (Akku, läuft gerade, Sync-Stand) werden zwischen Box
  und Home Assistant abgeglichen, sobald die Box online ist. Eine unterwegs
  am Handy gemachte Zuordnung kommt an, wenn die Box wieder online ist.
  Beide Boxen erhalten dieselben Zuordnungen.
- **Hörspiele:** mp3 auf einem NAS. Jede Box bekommt **alles** (Speicher ist
  kein Thema). Die Box holt die Dateien selbst direkt vom NAS, **nur im
  Heim-WLAN**. Home Assistant stößt an und zeigt den Stand, ist aber nicht
  im Datenweg. Fällt Home Assistant aus, spielt und synchronisiert die Box
  trotzdem.
- **Software-Updates** (Phoniebox + eigene Plugins + Konfiguration): nur
  **manuell angestoßen**, nur **daheim beim Laden**, mit **Selbsttest** nach
  dem Update und **Rückfall** auf die alte Version. Die Phoniebox-Version
  wird nur bewusst angehoben.
- **WLAN:** bekannte Netze sind das Heimnetz und Tobias' Handy-Hotspot. Die
  Box verbindet sich mit beiden wie mit einem normalen WLAN. **Kein eigener
  Hotspot** der Box. Ohne bekanntes Netz läuft sie offline.
- Was am Mac nicht echt geht (WLAN-Wechsel, Laden/Dock, Stromausfall der
  SD-Karte), wird im Prototyp über Schalter nachgespielt; dieselbe Logik
  läuft später am Pi.

## Bauen in Stufen

1. Leser (Firmware + Leser-Modul + Brücke) und Abspielen: Abläufe 1, 2, 5, 6, 8
2. Resume und Figuren-Zuordnung: Abläufe 3, 4, 7
3. Home Assistant, Medien-Sync, WLAN-Verhalten, Software-Update

## Bewusst nicht im Prototyp

LED-Ring, PiSugar/Akku-Hardware, Tasten/Encoder, Kopfhörer, Leise-Zeiten —
das hängt an Hardware, die noch fehlt. (Ihre Software-Seite kann später
simuliert werden.)

## Referenzen

- Projektplan Rev. 3.7: `docs/plan/stueckliste-und-psp.md`
- Übergabe / Stand Tonie-Test: `docs/plan/uebergabe.md`
- Recherche Phoniebox V3 (Leser, Abheben, Plugins, Docker):
  `docs/egm/software-prototyp/research_phoniebox_v3.md`
- Recherche PN5180-Bibliothek und ESP32-S3 USB:
  `docs/egm/software-prototyp/research_pn5180_esp32s3.md`
- Vorhandene Firmware: `firmware/tonie_test/tonie_test.ino`,
  `firmware/tonie_test/config.example.h`
