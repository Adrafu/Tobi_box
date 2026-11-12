# A0: Vertragsänderungen für die HA-Oberfläche, Stufe A (zur Freigabe, 12.11.)

Geändert (Entwurf, nichts committet): `docs/protocol/ha-websocket-v1.md` (Eintrag „Änderung 12.11.“, 2.1 ersetzt, neu 2.4, 3.12, 14; 5, 7, 8 angepasst) und `docs/data-model.md` (Eintrag, `serie.json`, 5a, Cover-Namen, `hoerkopien/`, Papierkorb). Version bleibt 1. Stufe B und C stehen nur als je ein Satz „geplant“ drin. Code und Tests sind unberührt.

## 1. Was sich ändert

**A-1 Alltag**
- Rechte in drei Stufen: *lesen*, *alltag* (alle HA-Benutzer), *admin*. Alltag darf jetzt zuordnen, anlernen, umbenennen, in den Papierkorb legen, hochladen, Art ändern. Leeren, Zusammenführen, Sync, Liste ausrollen, Reihenfolge, Eingang entfernen bleiben Admin.
- Schutz für Nicht-Admins: `erwartet_ziel` Pflicht, nur bekannte Tobies, Mengengrenzen (u. a. 16 GiB Upload je Stunde), Überraschungs-Serie nur Admin, Mitteilung an Admins bei Papierkorb mit Tobies oder mehr als 3 Einträgen je Stunde, „Letzte Stunde zurückholen“, 10 frühere Stände der Liste.
- Upload bis **2 GiB** je Datei, Reserve 2 GiB; Wunsch beim Hochladen (`ziel`, `art`, `name`) und `gruppe_anzahl`: der Eingang wartet auf alle Dateien einer Gruppe (höchstens 30 Minuten).
- Bibliothek: Art, Einzeltitel, Suche, Filter, Blättern, neuer Befehl für Folgen und Lieder; Cover (Foto vom Handy, Cover aus Tags, Pillow); Anzeigenamen der Boxen; Cover kommen nicht auf die Boxen (einzige Box-Änderung).

**A-2 Reinhören:** Audio-Ansicht mit Anmeldung oder signiertem Link (24 Stunden), Befehl `audio/bereit` (fragt vor jedem Start), Hörstelle je Benutzer (nur die eigene), Dauer.

**A-3 Hörkopien und Kapitel:** Kopie (AAC, 96 kbit/s) auf dem NAS neben `medien/`, neu Einsortiertes sofort, Bestand beim ersten Reinhören; harte Grenzen; Kapitelliste; „Anders einsortieren“ (nur falls der Rückweg machbar ist).

Neu insgesamt: 10 Befehle (Nr. 37 bis 46), 6 Fähigkeiten, 8 Fehlercodes, 25 Ausgabefelder, 16 optionale Eingabefelder, Store `tobibox.medieninfo` (abgeleitete Werte, nicht in `serie.json`, damit der `stand` ruhig bleibt).

## 2. Nicht rückwärtskompatibel (steht so im Änderungseintrag)

1. **Rechte gelockert:** 15 Befehle und der Upload gingen nur als Admin, jetzt für alle angemeldeten Benutzer (Runde 6). Gilt im Backend ab A1, auch vor dem Öffnen der Seite (A17).
2. **Rechte verschärft:** `konfig/export_lesen` und das Feld `ereignisse` von `boxen/list` waren für alle lesbar, jetzt nur Admin (U26).
3. **W-19 entfällt** (Upload nur Admin).
4. **Neue Pflicht für Nicht-Admins** (`erwartet_ziel`, kein `sofort`, kein `lesezeichen_tage`); die Zeitzone in `einstellungen/set` wird ignoriert statt gespeichert.
5. **Upload-Grenze 2 GiB, Reserve 2 GiB**; ein bestehender Eintrag mit 500 MiB wird angehoben.
6. **`stand`** rechnet nur noch über Name, Folgenliste und `anzeige`/`nummer`/`datum`/`pruefen`.

## 3. Vorläufige Zahlen („nach Messung A0b“)

Dauerdeckel 48 Stunden · Zeitgrenze je Hörkopie 60 Minuten · `-t` Zugabe 5 s · `-fs` 12 KB/s × 1,2 · Plausibilität Faktor 50 · Schlange 20 Dateien / 50 GB · Kontingent `hoerkopien/` 100 GB · eine Datei zugleich · eine vorgezogene Datei je Benutzer · Wartezeit-Schätzung 15 bis 30 × Echtzeit. Alle stehen als benannte Konstanten in Vertrag W, 14.10. Beschlossen sind dagegen u. a. 2 GiB, 24-Stunden-Link, 6 Audio-Verbindungen.

## 4. Gegen Tests und Code geprüft (nichts geändert)

**Bestehende Tests, die nach der Vertragsänderung anders erwarten müssen**
- `test_websocket_api.py`: `test_schreibende_befehle_nur_fuer_administratoren` (14 von 22 Zeilen werden Alltag: `serie/rename`, `folge/delete`, `medien/pruefen`, `neue_tobies/verwerfen`, `zuordnung/set`, `zuordnung/remove`, `lernmodus/*`, `serie/delete`, `folge/rename`, `folge/verschieben`, `einsortierung/bestaetigen`, `eingang/sortieren`); `LESE_BEFEHLE` mit `konfig/export_lesen` (jetzt Admin); `test_hello` (Liste der Fähigkeiten, bei `upload_max_bytes` nur falls die Anhebung auch den Wert 500 der Testeinrichtung trifft); `test_serien_list_und_serie_get` (Schlüsselmengen sind Gleichheit, neue Felder brechen sie).
- `test_v11_erweiterungen.py`: `f[-5:] == NEUE_FAEHIGKEITEN` (neue Fähigkeiten stehen am Ende).
- `test_upload.py`: `test_nur_administratoren` (Nicht-Admin bekommt 200); `test_platzpruefung_vorab` (Reserve 2 GiB, 500 MiB freier Platz reichen nicht mehr); `vorgaben == {"serie_id", "gruppe"}` bricht, wenn neue Schlüssel immer mitgeschrieben werden (ohne Wunsch unverändert lassen).
- `frontend/panel.test.mjs`: „Alle Fehlercodes des Vertrags (Abschnitt 7) haben einen deutschen Text“ liest die Tabelle; die 8 neuen Codes haben in der alten Seite keinen Text. Das widerspricht dem Satz „Rev. 5 ändert keinen bestehenden Test“.
- Unverändert bleiben `test_init.py` (bis A17), `test_services.py`, `test_quiet_settings.py`, `test_texte.py`, `test_media.py` (Stand), `test_ffprobe.py`, `test_eingang.py`.

**Was dem heutigen Code widerspricht (nur Liste)**
- `websocket_api.py`: nur `admin=bool` statt dreier Stufen; alle Befehle der Alltags-Spalte haben `admin=True`; keine neuen Befehle; kein `erwartet_revision`, `text`, `neu`, `limit`.
- `http.py`: `@require_admin` am Upload; `_lies_feld` liest 200 Bytes; Reserve fest 100 MiB, laufende Uploads werden nicht abgezogen; keine Cover- und Audio-Ansicht.
- `const.py`/`hub.py`: Vorgabe 500 MiB, Reserve 100 MiB, `FAEHIGKEITEN`, `grenzen`, `HTTP_STATUS` ohne die 8 neuen Codes (`test_texte` verlangt zu jedem einen Text in `strings.json`).
- `hub.py`: `boxen/list` liefert `ereignisse` an alle; kein `anzeige`, kein `box_anzeigen`.
- `media.py`: `stand` rechnet über das ganze `folgen_info`; keine Felder `art`, `einzeln`, Cover, Dauer; `bekannt` kennt sie nicht (sie bleiben aber in `extra` erhalten).
- `eingang.py`: `vorgaben` nur `serie_id`/`gruppe`; feste Sammelzeit 20 s, kein `gruppe_anzahl`; `sofort` für jeden Aufrufer.
- `ffprobe.py` ohne `-show_chapters`; `manifest.json` ohne Pillow; `box/src/tobibox/sync.py` ohne Cover-Ausschluss; kein Store `tobibox.medieninfo`/`hoerstellen`, kein Ordner `hoerkopien/`.

## 5. Ergänzungen über das Design hinaus (bitte mit freigeben)

Das Design ließ vier Stellen offen, ich habe so gefüllt: (a) „Frühere Stände“: optionale Eingabe `stand` bei `konfig/export_lesen` und `konfig/aus_export`, Fähigkeit `konfig_staende`; (b) Papierkorb-Eintrag bekommt `geloescht_von` (für „gelöscht von …“); (c) Eingangs-Eintrag bekommt `pruefen` (Summe der Ergebnisse); (d) fehlendes `erwartet_ziel` bei Nicht-Admin antwortet `unauthorized`. Dazu: `papierkorb/restore_letzte_stunde` ohne eigene Fähigkeit.

## 6. Offener Punkt, den nur du entscheidest

**Dürfen die genannten Tests angepasst werden?** CLAUDE.md und Design sagen: Verträge und bestehende Tests ändert ein Agent nur nach deiner Entscheidung. Ohne Anpassung bricht A1 sofort mehrere Tests (Abschnitt 4). Vorschlag: Ja, im jeweiligen Paket (A1, A3d, A5), Änderungen einzeln im Diff sichtbar, die 121 Tests der alten Seite bleiben bis auf die Fehlercodes-Prüfung unverändert (diese liest dann nur Codes bis 11.11. oder erwartet den Standardtext).
