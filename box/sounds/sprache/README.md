# Gesprochene Box-Töne

Zweiter Satz Töne neben den Melodie-Tönen in `box/sounds/`. Dieselben Dateinamen, dazu
die Prüfpunkt-Töne der Status-Karte (`pruef_<punkt>_ok`, `pruef_<punkt>_fehler`,
`pruef_leser_simulation`). Auswahl in der TOML-Konfiguration: `[toene] ordner = "../sounds/sprache"`.

- **Stimme:** Piper (`piper-tts`, GPL-3.0, nur Werkzeug) mit der deutschen Stimme
  `de_DE-thorsten-medium` aus `rhasspy/piper-voices` (Hugging Face).
- **Lizenz der Stimme:** Thorsten-Voice von Thorsten Müller, **CC0** (gemeinfrei).
  Quelle: <https://github.com/Thorsten-Voice/Thorsten-Voice>. Die erzeugten Dateien sind frei nutzbar.
- **Format:** WAV, mono, 16 Bit, 22050 Hz (wie die Melodie-Töne).
- **Erzeugen:** `python box/tools/make_sprache.py` (im Container; Texte stehen als Tabelle im Skript).
  Ersatz ohne Piper: `--engine espeak` (`espeak-ng`, Stimme `de`).
- Dieselben Texte und Stimme erzeugen auch `box/medien-sprache/`.
- **Lautheit (Entscheidung J, 09.11.):** Jeder Satz liegt bei -18 LUFS (Zielwert von ReplayGain 2.0 und
  `rsgain`), gemessen mit `box/tools/lautheit.py`; Werte und Prüfsummen in `box/lautheit.json`.
- **`hinweis.wav`** (Entscheidung T, 10.11.): kein gesprochener Text. Die Datei ist byte-gleich mit `box/sounds/hinweis.wav` (weicher Zweiklang 660 Hz dann 880 Hz, etwa 0,4 s, -18 LUFS; seit 11.11., vorher 0,1 s und bei der Mac-Abnahme nicht hörbar); `make_sprache.py` kopiert sie (`TOENE_OHNE_SPRACHE`). Pegelregel `hinweis_pegel` unverändert.
- **`lader.wav`** (Ein/Aus, 10.11.): „Strom ist da.“ Der Ton beim Andocken der laufenden Box; er spielt mit dem leisen Pegel von `hinweis` und nie in Leise-Zeiten. Einzeln mit den Funktionen von `make_sprache.py` erzeugt (Piper `de_DE-thorsten-medium`, -18,0 LUFS).
- **`akku_warnung.wav`** (Entscheidung Z, zweite Stufe, 11.11.): „Mein Akku wird leer. Bitte bald laden.“ Die einmalige Warnung bei 10 % Akku ohne Strom; das Hörspiel läuft danach weiter. Normaler Ton-Pegel (Grenze gilt, unter „leiser“ begrenzt), unter „stumm“ spielt der Hinweiston. Einzeln mit den Funktionen von `make_sprache.py` erzeugt (Piper `de_DE-thorsten-medium`, -18,0 LUFS, 2,3 s, mit 0,15 s Vorlauf).
- **`gute_nacht.wav`** (Entscheidung R, 10.11.): „Gute Nacht! Ich spiele noch ein bisschen.“ Die Durchsage beim Auflegen der Gute-Nacht-Karte; normaler Ton-Pegel (Grenze gilt, unter „leiser“ begrenzt), unter „stumm“ keine Durchsage. Einzeln mit den Funktionen von `make_sprache.py` erzeugt (Piper `de_DE-thorsten-medium`, -18,0 LUFS, 1,9 s).

**Vorlauf (11.11.):** Alle Töne beginnen mit 0,15 s Stille (`VORLAUF_S` in `tools/make_sounds.py`, auch von `make_sprache.py` genutzt), weil die Tonausgabe am Mac den Anfang verschluckt (bei `lader` fehlte das „S“). Die Stille am Ende kommt weiter aus `pad 0 0.15` im `kommando` der Mac-Konfiguration.
