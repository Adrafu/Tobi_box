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
- **`lader.wav`** (Ein/Aus, 10.11.): „Strom ist da.“ Der Ton beim Andocken der laufenden Box; er spielt mit dem leisen Pegel von `hinweis` und nie in Leise-Zeiten. Einzeln mit den Funktionen von `make_sprache.py` erzeugt (Piper `de_DE-thorsten-medium`, -18,0 LUFS).
- **`gute_nacht.wav`** (Entscheidung R, 10.11.): „Gute Nacht! Ich spiele noch ein bisschen.“ Die Durchsage beim Auflegen der Gute-Nacht-Karte; normaler Ton-Pegel (Grenze gilt, unter „leiser“ begrenzt), unter „stumm“ keine Durchsage. Einzeln mit den Funktionen von `make_sprache.py` erzeugt (Piper `de_DE-thorsten-medium`, -18,0 LUFS, 1,9 s).
