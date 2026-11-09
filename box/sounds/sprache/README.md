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
