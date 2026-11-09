# Gesprochene Testmedien

Vier Serien mit `serie.json` (IDs fest): `test-serie` (5e1a0c7d9b31), `lange-serie` (7b3f2a6e8c14),
`track-test` (9d4c1e5a2f68), `ueberraschung` (e2a8b6d0c397). Format: MP3, mono, 48 kbit/s.

- **Stimme:** Piper mit `de_DE-thorsten-medium` (Thorsten-Voice, **CC0**), siehe `box/sounds/sprache/README.md`.
- **Erzeugen:** `python box/tools/make_sprache.py` (im Container).
- Eigene Ordner in diesem Verzeichnis bleiben durch `.gitignore` lokal.
- **Lautheit (Entscheidung J, 09.11.):** Alle Dateien liegen bei -18 LUFS (Zielwert von `rsgain`) und tragen
  ReplayGain-Tags (`REPLAYGAIN_TRACK_GAIN`, `REPLAYGAIN_TRACK_PEAK`). Ohne Tags dämpft MPD um 6 dB.
  Messung: `python box/tools/lautheit.py --ordner box/medien-sprache`; Werte in `box/lautheit.json`.
  Eigene Dateien mit `python box/tools/lautheit.py --normalisiere DATEI` angleichen.
