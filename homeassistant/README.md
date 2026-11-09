# Tobi Box in Home Assistant: Integration `tobibox`

Die Integration ist der **einzige Schreiber** für Zuordnungen und `serie.json` (Design D1, D2). Sie

*   speichert die Zuordnungen (Tobies → Serie, Folge oder Aktion, mit Namen) mit **einer** Revision und
    **einer** Listen-ID im HA-Speicher und verteilt sie über MQTT an die Boxen (`tobibox/config`),
*   exportiert die Konfiguration nach jeder Änderung auf das NAS (`tobibox/export/config.json`),
*   verwaltet die Medien auf der NAS-Freigabe (Serien, Folgen, Papierkorb) und sortiert Neues aus dem
    **Eingang** nach den Tags ein (Entscheidung M),
*   nimmt Uploads vom Handy in den Eingang an,
*   bietet die Seite „Tobi Box“ (Ordner `custom_components/tobibox/frontend/`, AP 3.2) und HA-Aktionen.

Verträge (die Integration ändert sie nicht): `docs/protocol/ha-websocket-v1.md` (Vertrag W, Seite ↔ Backend),
`docs/protocol/mqtt-v1.md` (Box ↔ HA), `docs/data-model.md`.

## Getestete Versionen

| Was | Version | Bemerkung |
|---|---|---|
| Home Assistant (Tests) | **2026.10.4** | Siehe unten: Für 2026.11.x gibt es noch kein passendes Test-Paket. |
| Home Assistant (Ziel) | 2026.11.x (2026.11.0 erschien am 04.11.2026) | Die Module der Integration laden dort und alle benutzten HA-Funktionen haben dieselbe Form; die Tests laufen dort aber noch nicht. |
| `pytest-homeassistant-custom-component` | **0.13.375** | pinnt genau `homeassistant==2026.10.4` |
| Python | **3.14.6** (HA 2026.11 verlangt ≥ 3.14.2) | |
| Mosquitto-Add-on | 7.1.3 | Vorlagen unter `mosquitto/` |
| `ffmpeg` / `ffprobe` | 6.1.1 (Testrechner) | HA OS bringt beide mit |

**Warum nicht 2026.11.x?** Das Testpaket pinnt je Ausgabe genau eine HA-Version. Die neueste Ausgabe (0.13.375,
vom 25.10.) pinnt 2026.10.4. HA 2026.11.0 hat sich im Kern geändert (`httpx` wird durch `httpx2` ersetzt,
Hilfsfunktionen des Testpakets fehlen), das alte Testpaket lässt sich damit nicht mischen (geprüft). Sobald es
eine Ausgabe gibt, die `homeassistant==2026.11.x` pinnt, ersetzt man die beiden Zeilen in
`requirements-test.txt` (und `home-assistant-frontend==20261028.4`, so verlangt es HA 2026.11.0) und lässt die
Tests laufen.

## Tests ausführen

```bash
uv python install 3.14
uv venv --python 3.14 venv-ha
uv pip install --python venv-ha/bin/python -r homeassistant/requirements-test.txt
# ffmpeg und ffprobe müssen im PATH liegen; mosquitto und mosquitto_passwd sind optional (sonst wird der ACL-Test übersprungen)
venv-ha/bin/pytest -q homeassistant/tests
```

*   Dauer: etwa 2 Minuten. Alle Tests erzeugen ihre Audiodateien selbst mit `ffmpeg` (Tags über `-metadata`);
    echte Hörspiele kommen nie ins Repo.
*   `homeassistant/tests/frontend/` gehört AP 3.2 (JavaScript, eigener Aufruf) und wird hier nicht angefasst.
*   `pytest.ini` setzt `pythonpath = .` (damit `custom_components/tobibox` gefunden wird) und `asyncio_mode = auto`.

## Installation in Home Assistant (Tobias)

Voraussetzungen:

1.  HA 2026.11.x mit der **MQTT-Integration** und dem **Mosquitto-Add-on** 7.1.3; die Konten und Rechte der Boxen
    richtet `docs/betrieb/mqtt-konten.md` ein (Vorlagen: `mosquitto/acl.conf.example`,
    `mosquitto/accesscontrollist.example`, `mosquitto/mosquitto-addon.example.yaml`).
2.  Die NAS-Freigabe ist in HA eingebunden (z. B. `/media/tobibox`) und HA darf schreiben. Auf dem NAS liegen
    nebeneinander `medien/`, `eingang/`, `export/` und `releases/` (der Ordner `eingang/` ist neu: Tobias legt
    ihn an, AP 3.5). **`eingang/` muss auf demselben Dateisystem wie `medien/` liegen**, denn das Einsortieren ist
    ein Umbenennen.
3.  `ffprobe` und `ffmpeg` im HA (HA OS hat sie). Fehlt `ffprobe`, bleibt der Eingang liegen
    („Prüfung nicht möglich“).

Schritte:

1.  Den Ordner `homeassistant/custom_components/tobibox/` nach `<HA-Konfiguration>/custom_components/tobibox/`
    kopieren (samt `frontend/`) und HA neu starten.
2.  Einstellungen → Geräte & Dienste → Integration hinzufügen → „Tobi Box“. Angaben: Pfad zum Ordner `medien`,
    die Box-Namen (wie `box_id` in `tobibox.toml`, z. B. `box1, box2`), größte Datei beim Upload (Vorgabe
    500 MiB; später in den Optionen änderbar).
3.  In der Seitenleiste erscheint „Tobi Box“ (nur für Administratoren).
4.  Beim ersten Start legt die Integration eine neue Liste an (Revision 1) und veröffentlicht sie. Startet HA
    später mit **leerem Speicher** oder ist der Export auf dem NAS **neuer**, veröffentlicht die Integration
    nichts, bis Tobias auf der Seite entschieden hat („aus dem Export holen“ oder „Liste neu ausrollen“,
    Vertrag W, Abschnitt 13).

## Aufbau

| Datei | Inhalt |
|---|---|
| `__init__.py` | Einrichtung, Seite über `panel_custom` (`require_admin=True`), statische Dateien über `async_register_static_paths` |
| `config_flow.py` | Einrichtung und Optionen |
| `hub.py` | gemeinsamer Zustand: Abos der Seite, Export, Start-Prüfung, Zuordnungen, `anfrage_id` |
| `store.py` | Konfiguration im HA-Speicher, Prüfung wie auf der Box, Export lesen/schreiben |
| `media.py` | `serie.json`, Prüfung der Freigabe, Serien/Folgen ändern, Papierkorb mit `meta.json` |
| `eingang.py` | Eingang: Tags, Gruppieren, Serie bestimmen, Prüfsummen, Einsortieren |
| `ffprobe.py` | `ffprobe` gehärtet (Liste von Argumenten, `-protocol_whitelist file`, erzwungenes Format, 30 s, 1 GiB) |
| `namen.py` | Namensregeln (SMB), natürliche Sortierung, Tag-Werte, Folgen-Nummer |
| `mqtt.py`, `lernmodus.py` | MQTT-Schicht, Lernmodus mit Rückfrage und `persistent_notification` |
| `websocket_api.py`, `http.py` | die 32 Befehle von Vertrag W, Upload im Strom mit `asyncio.shield` |
| `services.py`, `services.yaml` | HA-Aktionen (rufen dieselben Funktionen) |
| `strings.json`, `translations/de.json` | alle Texte (gleicher Inhalt) |

## Abweichungen und Auslegungen (gemeldet an die Projektleitung)

*   `ffprobe` kennt `-nostdin` nicht (nur `ffmpeg`): Statt dessen wird die Standardeingabe geschlossen.
*   Einzeldatei ohne Album: Anzeigename = Dateiname ohne Endung (T4), nicht der Ordnername.
*   Fehlt `disc`, gilt die CD-Nummer aus dem Albumnamen (`(CD 2)`), sonst 1.
*   Eine Textdatei mit Audio-Endung (kein NUL-Byte, fast nur Text) ist „falsches Format“ (415), eine defekte
    Binärdatei nur eine Warnung `nicht_lesbar`.
*   Der Gerätename `CON` als Serien-Ordner wird `CON_` (ein führendes `_` würde ihn zum reservierten Ordner machen).
*   Das Feld `lesezeichen_tage` (Entscheidung N) steht in der Konfiguration (Vorgabe 14, 0 bis 365), wird
    veröffentlicht, exportiert und aus dem Export zurückgeholt. Es gibt keine Bedienung dafür.
*   Ereignisse des Themas `lernmodus` tragen `art="zustand"` (der Vertrag nennt keine Arten).
*   Ein Ordner ohne `serie.json` bekommt die ID = Ordnername (`data-model.md`, Abschnitt 5), damit Zeiger und
    Zuordnungen erhalten bleiben.
