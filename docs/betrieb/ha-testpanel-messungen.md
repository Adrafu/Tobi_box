# Testpanel und Messungen auf deinem Home Assistant (Paket A0b)

Bevor die neue Seite gebaut wird, messen wir auf deinem echten Home Assistant
(QNAP-NAS, zu Hause und über Tailscale, Companion-App am Handy), was geht und
wie schnell es ist. Dafür gibt es ein kleines Testpanel. Die Ergebnisse
bestimmen die Grenzen in `docs/protocol/ha-websocket-v1.md`, Abschnitt 14.10,
und die Hörkopie im Design (11.4.7).

Wir gehen die Messungen später **gemeinsam im Chat** durch, ein Schritt nach
dem anderen. Diese Anleitung ist die Grundlage dafür.

## So erscheint das Testpanel

1. Den Ordner `homeassistant/custom_components/tobibox` aus dem Repo in den
   Ordner `custom_components` deines Home Assistant kopieren (ersetzt die alte
   Fassung).
2. Home Assistant **neu starten** (Einstellungen, System, oben rechts
   „Neu starten“). Python-Teile laden erst nach dem Neustart.
3. Im Browser oder in der Companion-App die Adresse `/tobibox-neu` öffnen
   (z. B. `http://<dein-HA>:8123/tobibox-neu`), oder in der Seitenleiste auf
   „Tobi Box (Test)“ tippen. Das Panel sehen nur Administratoren. Die alte Seite
   „Tobi Box“ bleibt, wie sie ist.
4. Sieht du das Panel nicht: Browser-Cache leeren oder in der Companion-App
   „Frontend-Cache zurücksetzen“ (Einstellungen, Companion-App, Fehlersuche).

Das Panel zeigt sieben Abschnitte (a bis g). Es speichert nichts in deiner
Bibliothek. Zum Abschalten steht in `const.py` `TESTPANEL = False`.

**Wichtig:** Die Audio-Adresse ist 24 Stunden gültig. Gib sie nicht weiter.

## Messung 1: Companion-App (iOS und Android)

*Abschnitte b, c, d des Panels.*

1. In der Companion-App `/tobibox-neu` öffnen.
2. **Safe Area (d):** Lies die vier Werte ab (oben, rechts, unten, links). Dreh
   das Handy einmal quer und lies noch einmal.
3. **Tastatur (c):** Tipp in das Textfeld. Schau, ob die Tastatur das Feld
   verdeckt und ob die Seite mitrutscht.
4. **Foto (b):** Tipp auf „Datei auswählen“ und nimm ein Foto aus der
   Mediathek, danach ein neues mit der Kamera.
5. **Reiter unten:** Prüf, ob unten etwas vom Handy überdeckt wird (Home-Balken
   bei iPhone, Navigationsleiste bei Android).

**Du solltest sehen:** Werte in Pixeln bei d; das Foto als Vorschau unter b;
die Tastatur öffnet sich.
**Melde:** Gerät und Betriebssystem, die vier Safe-Area-Werte, ob Tastatur oder
Balken etwas verdecken, ob die Foto-Auswahl Kamera und Mediathek anbietet.

## Messung 2: Abspielen bei gesperrtem Bildschirm und Ordner-Folge

*Abschnitt a.*

1. Wähle eine Serie und eine Folge. Es startet kein Ton von selbst: Tipp auf
   die Wiedergabe, falls nötig.
2. **Kurz:** Spiel eine Folge von etwa 5 Minuten. Sperr den Bildschirm, warte
   eine Minute, entsperr. Hörst du dazwischen etwas? Zeigt der Sperrbildschirm
   die Medien-Steuerung (Titel, Pause, ±30 s)?
3. **Lang:** Das Gleiche mit einer Folge von über einer Stunde (Hörbuch), der
   Bildschirm bleibt 10 Minuten gesperrt.
4. **Ordner-Folge:** Wähl eine Folge mit mehreren Tracks. Spring mit
   „+30 s“ kurz vor das Ende des ersten Tracks und warte. Der nächste Track
   soll von selbst starten. Das Panel schreibt „Trackwechsel: Lücke … ms“.
   Mach das einmal bei **offenem Bildschirm** und einmal bei **gesperrtem**.

**Du solltest sehen:** Zeit und Dauer laufen mit; „Start nach … ms“ nach dem
Antippen.
**Melde:** je Fall (5 min, über 1 h, Ordner) und je Gerät: spielt weiter,
ja oder nein; Medien-Steuerung am Sperrbildschirm ja oder nein; bei
Trackwechsel die Lücke in ms und ob er gesperrt klappte.

## Messung 3: ffmpeg auf deinem Home Assistant

*Abschnitt f.*

1. Wähle oben in a eine Folge (am besten 10 Minuten oder länger).
2. Tipp auf „ffmpeg messen“. Es läuft bis etwa eine Minute, bei langsamer
   Hardware länger (Grenze 15 Minuten).
3. Mach es noch einmal ohne gewählte Folge: dann kommen nur Version und
   Encoder.

**Du solltest sehen:** die erste Zeile von `ffmpeg -version`, die Quelle
(„ffmpeg-Integration“ oder „PATH“), die Liste der AAC-Encoder und
„Umwandeln: ok, … s für … s Audio, Faktor … x Echtzeit“.
**Melde:** Version, ob ein AAC-Encoder in der Liste steht, Sekunden, Audio-
Sekunden und den Faktor. (Steht „ffmpeg wurde nicht gefunden“: das ist auch
ein Ergebnis, bitte so melden.)

## Messung 4: Springen auf dem NAS-Pfad

*Abschnitt a.*

1. Spiel eine lange Datei (Hörbuch, möglichst `.m4a` oder `.m4b` und eine
   `.mp3`).
2. Spring mit der Zeitleiste in die Mitte, dann ans Ende, dann zurück. Spring
   auch mit „−30 s“ und „+30 s“.
3. Miss mit der Uhr, wie lange es von deinem Tippen bis zum Ton dauert.

**Du solltest sehen:** Der Ton kommt nach dem Sprung ohne langes Warten. Das
Panel zeigt Zeit und Dauer.
**Melde:** Dateiart und Länge, Wartezeit nach dem Sprung (Sekunden), ob es zu
Hause und über Tailscale verschieden ist, ob bei `.m4a` der Start langsam ist.

## Messung 5: Upload über Nabu Casa (und zu Hause)

*Abschnitt e.* Die Datei wird gesendet, **gezählt und weggeworfen**. Nichts wird
gespeichert.

1. Eine Datei mit **20 MiB** wählen, „Senden“ tippen, Zeit und MB/s ablesen.
2. Das Gleiche mit **150 MiB**, dann **500 MiB**, dann **2 GiB**.
3. Erst zu Hause im WLAN, dann über Nabu Casa (von außen) oder Tailscale.
   Bei 2 GiB den Bildschirm anlassen. Hat es bei Nabu Casa eine Grenze, bricht
   es ab oder zeigt einen HTTP-Fehler.

Tipp: Die Dateien kannst du am Mac mit `mkfile 20m test20.bin` (Mac) anlegen,
am Handy nimm ein Video passender Größe. Die Endung ist egal.

**Du solltest sehen:** „… MB in … s = … MB/s“ und „Server zählte … Bytes
(passt)“.
**Melde:** je Größe und Weg: Sekunden, MB/s und ob „passt“ dasteht; bei
Abbruch: nach wie vielen Sekunden und die Meldung.

## Messung 6: Formate auf iPhone und Mac-Safari

*Abschnitt g.*

1. Auf dem iPhone (Safari, dann Companion-App) und auf dem Mac in Safari
   `/tobibox-neu` öffnen. Wo es geht, auch in Chrome am Mac und am
   Android-Handy.
2. Lies im Abschnitt g die Zeilen ab: mp3, m4a/aac, m4b, flac, ogg/vorbis, opus,
   wav. Mögliche Werte: „probably“ (ja), „maybe“ (vielleicht), „nein“.
3. Spiel, wenn du eine hast, je eine Datei der Formate ab, besonders flac,
   ogg und opus.

**Melde:** Gerät und Browser, die sieben Zeilen, und welche Datei wirklich
gespielt hat.

## Tabelle für die Messwerte

Trag die Werte hier (oder im Chat) ein. Die Ergebnisse kommen danach nach
`docs/plan/`.

| Nr. | Gerät / Weg | Messung | Wert | Auffälligkeit |
|---|---|---|---|---|
| 1 | iPhone | Safe Area oben / unten (px) | | |
| 1 | iPhone | Tastatur verdeckt Feld? | | |
| 1 | Android | Safe Area oben / unten (px) | | |
| 1 | Android | Tastatur verdeckt Feld? | | |
| 2 | iPhone | 5 min, gesperrt: spielt weiter? | | |
| 2 | iPhone | über 1 h, gesperrt: spielt weiter? | | |
| 2 | iPhone | Trackwechsel offen / gesperrt (ms) | | |
| 2 | Android | 5 min, gesperrt: spielt weiter? | | |
| 2 | Android | über 1 h, gesperrt: spielt weiter? | | |
| 2 | Android | Trackwechsel offen / gesperrt (ms) | | |
| 3 | HA | ffmpeg-Version | | |
| 3 | HA | AAC-Encoder vorhanden? | | |
| 3 | HA | 10 min Audio: Sekunden / Faktor | | |
| 4 | zu Hause | Sprung mp3 / m4a (s) | | |
| 4 | Tailscale | Sprung mp3 / m4a (s) | | |
| 5 | zu Hause | 20 MiB (s / MB/s) | | |
| 5 | zu Hause | 150 MiB (s / MB/s) | | |
| 5 | zu Hause | 500 MiB (s / MB/s) | | |
| 5 | zu Hause | 2 GiB (s / MB/s) | | |
| 5 | Nabu Casa | 20 MiB (s / MB/s) | | |
| 5 | Nabu Casa | 150 MiB (s / MB/s) | | |
| 5 | Nabu Casa | 500 MiB (s / MB/s) | | |
| 5 | Nabu Casa | 2 GiB (s / MB/s) | | |
| 6 | iPhone Safari | mp3 / m4a / m4b / flac / ogg / opus / wav | | |
| 6 | Mac Safari | mp3 / m4a / m4b / flac / ogg / opus / wav | | |

## Wenn etwas nicht geht

- **Panel fehlt:** HA nach dem Kopieren neu gestartet? Als Administrator
  angemeldet? In den Protokollen (Einstellungen, System, Protokolle) nach
  „tobibox“ suchen.
- **Bibliothek bleibt leer:** Ist die Integration „Tobi Box“ eingerichtet und
  der Medien-Pfad erreichbar (NAS an)?
- **Ton startet nicht:** In der Companion-App auf iOS muss das erste Abspielen
  oft selbst angetippt werden. Das Panel sagt dann „play() abgelehnt“.
  Das ist ein Messwert.
