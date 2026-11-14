# Messungen mit dem HA-Testpanel (A0b), 12.11.

Testpanel `/tobibox-test`, Anleitung `docs/betrieb/ha-testpanel-messungen.md`. Home Assistant läuft auf dem QNAP-NAS.
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
| 5 | Upload über LTE und Nabu Casa | 3,4 MB in 1,9 s; 159,8 MB in 116 s (11,5 Mbit/s); **551,5 MB in 529 s (8,7 Mbit/s)**, Bytezahl stimmt jeweils | Nabu Casa nimmt über 500 MiB an; 2 GiB nicht gemessen (keine so große Datei am Handy), Grenze 2 GiB bleibt |
| 6 | Formate (iPhone, iOS 27) | mp3, m4a/aac, m4b, flac, wav: ja; ogg/vorbis und opus: „probably“ | Hörkopien am iPhone kaum nötig; Mac-Safari noch offen |
| 7 (14.11.) | Bewegung h1: View Transition | API da, aber die Elemente im Shadow-DOM von HA werden nicht erfasst: nur Überblenden, kein Flug | bestätigt R17-1: Cover-Flug per FLIP, nie `startViewTransition` |
| 7 (14.11.) | Bewegung h2: FLIP mit Feder | fliegt hin und zurück, 510 ms (Soll 500), bleibt zwischen Start und Ziel; Ecken stimmen erst, wenn `border-radius` gegen die Skala je Achse ausgeglichen mitläuft (sonst springen sie am Ende) | A6m/A8m: FLIP-Hilfsfunktion rechnet die Ecken mit; Prüfung: Flug bleibt zwischen Start und Ziel, Ecken im letzten Frame = Ziel |
| 7 (14.11.) | Bewegung h3: Feder mit `linear()` | geht, 510 ms, überschwingt 1,4 px | – |
| 7 (14.11.) | Bewegung h4: iOS-Blatt-Effekt | geht und lässt sich wegwischen, wenn (a) nur der sichtbare Inhalt verkleinert wird (Drehpunkt Mitte des sichtbaren Teils, `clip-path`) und das Blatt **nicht** darin steckt, und (b) das Blatt beim `showModal()` schon am Ziel steht, der Fokus ohne Scrollen gesetzt wird und der Dialog `overflow: clip` hat; sonst scrollt das iPhone zum ×-Knopf und das Blatt springt (163 px) | A6m: Blatt-Aufbau genau so; Prüfung: Blatt kommt von unten ohne Sprung. Kopfleiste von HA schrumpft nicht mit (hingenommen) |
| 7 (14.11.) | Android | nicht gemessen (Tobias: vorerst weglassen) | – |

Messung 7 (14.11.) mit iPhone in der HA-App 2026.10.3, nach zwei Korrekturen am Testpanel (Commits `9508c42`, `82d8034`).

Offen: Formate in Safari am Mac; Upload 2 GiB (bei Gelegenheit vom Mac).
