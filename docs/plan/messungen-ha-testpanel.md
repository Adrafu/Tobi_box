# Messungen mit dem HA-Testpanel (A0b), 12.11.

Testpanel `/tobibox-neu`, Anleitung `docs/betrieb/ha-testpanel-messungen.md`. Home Assistant läuft auf dem QNAP-NAS.
Gemessen von Tobias mit iPhone 16 Pro (iOS 27) in der HA-Companion-App, unterwegs über LTE und Nabu Casa.

| Nr. | Messung | Ergebnis | Folge für den Bau |
|---|---|---|---|
| 1 | Companion-App: Tastatur | passt, Feld bleibt sichtbar | – |
| 1 | Companion-App: Foto | Galerie geht; Kamera bleibt schwarz (vermutlich fehlende Kamera-Erlaubnis der HA-App) | Cover über Galerie reicht; Hinweis in der Anleitung |
| 1 | Safe Area | Testpanel zeigt keine Werte (Fehler im Panel); Screenshots: oben kein Überlappen, quer liegt der Home-Balken unten über dem Inhalt | neue Seite: unten `env(safe-area-inset-bottom)` für die Reiter (wie geplant) |
| 2 | Abspielen gesperrt | läuft weiter; Sperrbildschirm zeigt Titel, Fortschritt, Pause, ±10 s (iOS nimmt 10 s statt 30 s) | `mediaSession` reicht; ±10 s am Sperrbildschirm hinnehmen |
| 2 | Trackwechsel gesperrt (Ordner-Folge, 18 Tracks) | klappt von selbst, Lücke 822 ms | nächsten Track vorab signieren, um die Lücke zu kürzen |
| 3 | ffmpeg auf dem QNAP | ffmpeg 8.1.3 über die HA-ffmpeg-Integration, Encoder `aac`; 600 s Audio in 15,0 s = **40× Echtzeit** | Zeitgrenze Hörkopie **90 min** (deckt 48 h Dauerdeckel bei 40×); Wartezeit-Schätzung 40× |
| 4 | Springen auf dem NAS-Pfad | ±30 s und Regler funktionieren | – |
| 5 | Upload über LTE und Nabu Casa | 3,4 MB in 1,9 s; **159,8 MB in 116 s (11,5 Mbit/s)**, Bytezahl stimmt | Nabu Casa nimmt mindestens 160 MB; 500 MiB und 2 GiB noch offen |
| 6 | Formate (iPhone, iOS 27) | mp3, m4a/aac, m4b, flac, wav: ja; ogg/vorbis und opus: „probably“ | Hörkopien am iPhone kaum nötig; Mac-Safari noch offen |

Offen: Upload 500 MiB und 2 GiB über Nabu Casa (im WLAN, über die Nabu-Casa-Adresse), Formate in Safari am Mac.
