# Tobi Box in Home Assistant: Integration `tobibox`

Die Integration ist der **einzige Schreiber** für Zuordnungen und `serie.json` (Design D1, D2). Sie

*   speichert die Zuordnungen (Tobies → Serie, Folge oder Aktion, mit Namen) mit **einer** Revision und
    **einer** Listen-ID im HA-Speicher und verteilt sie über MQTT an die Boxen (`tobibox/config`),
*   exportiert die Konfiguration nach jeder Änderung auf das NAS (`tobibox/export/config.json`),
*   verwaltet die Medien auf der NAS-Freigabe (Serien, Folgen, Papierkorb) und sortiert Neues aus dem
    **Eingang** nach den Tags ein (Entscheidung M),
*   nimmt Uploads vom Handy in den Eingang an,
*   bietet die Seite „Tobi Box“ unter `/tobibox` (Element `tobibox-app.js`, Ordner `custom_components/tobibox/frontend/`), das Testpanel unter `/tobibox-test` und HA-Aktionen. Die alte Komponente `tobibox-panel.js` hat keinen eigenen Seitenleisten-Eintrag; sie ist in „Technik“ eingebettet.

Verträge (die Integration ändert sie nicht): `docs/protocol/ha-websocket-v1.md` (Vertrag W, Seite ↔ Backend),
`docs/protocol/mqtt-v1.md` (Box ↔ HA), `docs/data-model.md`.

## Die Seite „Tobi Box“

*   **Adresse:** `/tobibox`. Bis Tobias Teil A-1 abgenommen hat, sieht nur ein Administrator die Seite in der
    Seitenleiste (`panel_custom` mit `require_admin=True` in `__init__.py`). Das blendet die Seite nur aus; geschützt
    ist sie durch die Befehle selbst (siehe „Aktionen und Rechte“).
*   **Reiter:** Start, Bibliothek, Tobies, Geräte (`REITER` in `tobibox-app.js`, Beschriftungen in `texte.js`). Am Handy
    stehen sie unten (Panel unter 700 px Breite), auf dem Tablet oben (700 bis unter 1100 px), ab 1100 px als Seitenleiste.
*   **Technik:** Das runde Werkzeug-Symbol im Kopf öffnet „Technik“. Es ist nur für Administratoren da; Nicht-Administratoren
    sehen dort den Satz „Dieser Bereich ist nur für Administratoren“. Technik hat sechs Unterseiten: Boxen, Speicher und
    Netz, Liste und Sicherung, Tobies, Meldungen, Einstellungen. Die alte Komponente läuft dort eingebettet.
*   **Abends:** Gute Nacht und Leise-Zeiten stehen unter „Geräte“, unten im Abschnitt „Abends“ (Routen `#abends` und `#mehr`
    führen auf `#geraete`).
*   **Rechte:** Drei Stufen (Vertrag W, Abschnitt 2.1):
    *   **lesen:** jeder angemeldete HA-Benutzer,
    *   **alltag:** jeder angemeldete HA-Benutzer, mit den Schutzregeln aus 2.4 (zum Beispiel Papierkorb mit Mitteilung),
    *   **admin:** nur Administratoren, zum Beispiel Papierkorb leeren, Liste neu ausrollen, Lernmodus, „Cover neu suchen“.
    Die Stufe steht am Befehl als `recht=` (`websocket_api.py`).
*   **Boxen mit Namen:** Die Anzeigenamen stellst du in den Optionen der Integration ein, Feld „Namen der Boxen“,
    Schreibweise `box1=Box 1, box2=Box 2` (Vor dem Gleichheitszeichen steht der Box-Name, danach der Anzeigename, bis
    40 Zeichen). Ohne Eintrag gilt der Name, den die Box selbst meldet.
*   **Hochladen:** Das Backend nimmt Dateien bis 2 GiB an (`upload_max_mib`, Vorgabe 2048 MiB, in den Optionen änderbar).
    Die Seite zum Hochladen (Knopf „+“) kommt mit Teil A-1c; heute zeigt sie noch den leeren Platz.
*   **Cover:** Das Backend holt und liefert Cover (Befehl `cover/neu_suchen` nur für Administratoren, Bild hochladen
    für alle). Eigene Cover per Foto in der Seite kommen mit Teil A-1c.
*   **Tobies und Warteschlange:** Der Reiter „Tobies“ zeigt das Regal aller Tobies und die Kachel „+ Neuer Tobie“. Dort
    lässt sich ein Tobie auch vormerken („Später auflegen“): die Warteschlange ordnet ihn an, sobald er auf einer Box
    liegt (Vertrag W, Abschnitt 3.13, Befehle 47 bis 49, Recht `alltag`). Die Anleitung dafür steht in
    `docs/betrieb/ha-seite-alltag.md` (Abschnitt „Tobies“). Der Lernmodus mit Countdown bleibt Administratoren vorbehalten
    (unter „Technik“).

Stand: Teile A-1a (Lesen und Abends) und A-1b (Tobies). Was dort fehlt, steht oben beim jeweiligen Punkt.

## Vorlage: Mitteilung aufs Handy bei einem neuen Tobie

Die Integration liefert für einen neuen Tobie **kein** Ereignis auf dem HA-Bus und **keine** Entität. Sie sendet das
Thema `neue_tobies` nur an offene Seiten der Oberfläche (`hub.py`, `emit`, Vertrag W, Abschnitt 4). Die Vorlage baut
deshalb auf dem MQTT-Thema auf, das die Box selbst veröffentlicht: `tobibox/<box>/unknown/<uid>` mit `art` = `unbekannt`
(`docs/protocol/mqtt-v1.md`, Abschnitt 3.5). Die Integration liest dasselbe Thema (`mqtt.py`, `_on_unknown`). Die Vorlage
ist keine neue Funktion (Design 7.1); du legst sie in HA selbst an, zum Beispiel über „Einstellungen → Automationen &
Szenen → Automation erstellen → Aus YAML“.

```yaml
alias: Neuer Tobie → Mitteilung aufs Handy
description: Schickt eine Mitteilung, wenn eine Box einen unbekannten Tobie meldet.
mode: queued
max: 10
triggers:
  - trigger: mqtt
    topic: tobibox/+/unknown/+
conditions:
  - condition: template
    value_template: >-
      {{ trigger.payload | length > 0
         and trigger.payload_json.art == 'unbekannt'
         and trigger.payload_json.anzahl == 1 }}
actions:
  - action: notify.mobile_app_<geraet>
    data:
      title: Neuer Tobie
      message: Tippe, um ihn einzuordnen.
      data:
        url: /tobibox
```

*   `notify.mobile_app_<geraet>` ersetzt du durch den Namen deines Handys. Ihn findest du unter „Entwicklerwerkzeuge“,
    Reiter „Aktionen“, wenn du nach `mobile_app` suchst.
*   `data: url: /tobibox` soll beim Tippen auf die Mitteilung die Seite öffnen. Ob das auf deinem Handy so klappt, ist
    noch nicht getestet; bitte beim ersten Mal prüfen.
*   Das Thema ist **retained**: Eine Kennung, die noch nicht bestätigt ist, kommt nach einem HA-Neustart erneut. Die
    Bedingung `anzahl == 1` verhindert, dass jede weitere Meldung derselben Kennung eine neue Mitteilung auslöst.
*   Die Vorlage erkennt jeden unbekannten Tobie, auch den, den die Warteschlange gleich zuordnet. Die Box meldet ihn ja
    trotzdem.
*   Die Verbindung zu MQTT ist dieselbe, die die Integration nutzt. Die Rechte dafür richtet `docs/betrieb/mqtt-konten.md` ein.

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
*   `homeassistant/tests/frontend/` enthält die JavaScript-Tests der Seite (`*.test.mjs`). Sie laufen mit eigenem Aufruf, nicht mit `pytest`.
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
    2048 MiB = 2 GiB; später in den Optionen änderbar). Die Anzeigenamen der Boxen (`box1=Box 1, box2=Box 2`) trägst
    du danach in den Optionen der Integration ein.
3.  In der Seitenleiste erscheint „Tobi Box“ (bis zur Abnahme von Teil A-1 nur für Administratoren).
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
| `websocket_api.py`, `http.py` | die Befehle von Vertrag W (Abschnitt 3), Upload im Strom mit `asyncio.shield` |
| `services.py`, `services.yaml` | HA-Aktionen (rufen dieselben Funktionen); **alle nur für Administratoren** (Abschnitt „Aktionen und Rechte“) |
| `strings.json`, `translations/de.json` | alle Texte (gleicher Inhalt) |
| `testpanel.py`, `tobibox-testpanel.js` | Testpanel `/tobibox-test` (nur Administratoren; Schalter `TESTPANEL` in `const.py`) |
| `frontend/tobibox-app.js`, `frontend/seiten/`, `frontend/bausteine.js`, `frontend/texte.js` | Seite „Tobi Box“: Gerüst, Reiter und Routen; je Reiter eine Seite (`seiten/index.js`); Bausteine; alle Texte der Oberfläche |
| `frontend/tobibox-panel.js` | die alte Komponente, eingebettet in „Technik“ |

## Aktionen und Rechte

Alle HA-Aktionen der Integration (`tobibox.zuordnen`, `serie_loeschen`, `papierkorb_leeren`, `liste_neu_ausrollen`,
`sync_anstossen` und die übrigen) ändern etwas oder lösen etwas aus. Sie sind mit `async_register_admin_service`
angemeldet: **nur Administratoren** dürfen sie aufrufen; ein Benutzer ohne Adminrechte (auch ein Wandtablet-Konto)
bekommt `Unauthorized`. Aufrufe ohne Benutzer (Automationen, Skripte, System) bleiben erlaubt, denn HA prüft die
Rechte nur, wenn ein Benutzer den Aufruf auslöst. Es gibt keine lesende Aktion; Lesen geht nur über die
WebSocket-Befehle. Dort gilt die dreistufige Regel aus Vertrag W, Abschnitt 2.1 (lesen, alltag, admin): Die Alltagsbefehle
(zum Beispiel umbenennen, Art ändern, in den Papierkorb legen, Zuordnen, Upload) dürfen alle angemeldeten Benutzer nutzen.
Der Upload braucht keinen Administrator mehr (W-19 ist entfallen); er prüft nur die Anmeldung.

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
